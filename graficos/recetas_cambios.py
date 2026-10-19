"""graficos.recetas_cambios — «Cambios Recetas Base», en Recetas (regla #671).

Qué insumo o qué cantidad cambió en cada receta base, quién lo cambió y
cuánto movió su costo. A pedido (2026-10-19): «¿puedes identificar qué
cantidad o ítem cambió en un mes?».

La cuenta NO es nueva: es `simulador_receta.ediciones_base`, la misma que
dibuja los ▼ en la ficha de Costo Carta (regla #657), leída del log del
Almacén (`recetabaselog` / `recetabaselogdet`, cada fila = la receta como
estaba ANTES de un guardado; la de después es el guardado siguiente o la
receta de hoy). Verificado contra el SQL el mismo día: en 1.349 de 1.352
guardados la cabecera siguiente dice que el guardado anterior fue ése, o
sea que la cadena no salta ninguno; y el costo de cada foto es Σ cantidad
× precio de sus líneas en 1.350.

Una EDICIÓN junta los guardados de la misma receta a menos de dos horas
(`JUNTAR_GUARDADOS`), igual que en Costo Carta. El costo antes y después
va con los precios de ANTES: así una suba de precios del mes no se lee
como un cambio de receta.

Sólo recetas base: las recetas de PLATO no tienen log en el POS.

La tarjeta es lista | ficha (`COLUMNAS_DRILL_FICHA`, como Proveedor y
Producto de Compras): a la izquierda las ediciones del rango, a la derecha
la elegida — sus líneas antes y después, dónde se usa hoy la receta y su
historial entero.
"""

import datetime
import hashlib
from html import escape

import pandas as pd
import streamlit as st

from estado_rango import atajos_tarjeta, clave_rango
from graficos.base import rango_tarjeta, seleccion_multiple, selector_fecha_tarjeta
from graficos.carta_costeada import ediciones_bases
from graficos.compras._comun import COLUMNAS_DRILL_FICHA
from tema import LAVANDA_FONDO

CATEGORIA_FECHA = "cambios_rb"
ATAJO_INICIAL = "d30"
"""Abre en los últimos 30 días: «como mínimo un mes» (regla #616)."""

TIPOS = ("Agregado", "Quitado", "Cantidad")
_OPC_TIPO = ("Todo", "Agregados", "Quitados", "Cantidad")
_TIPO_DE_OPC = {"Agregados": "Agregado", "Quitados": "Quitado", "Cantidad": "Cantidad"}

GRANDE_PCT = 0.5
GRANDE_SOLES = 5.0
"""«Cambio grande de costo»: la edición mueve el costo de la receta ±50 % y
al menos S/ 5. Es para MIRAR, no un error: el 07/10/2026 el «Tomate criollo
limpio» quitó el tomate y sumó 1.200 g de arúgula —de S/ 10,50 a 100,08—,
pero el mismo umbral marca la Milanesa de lomo, que cambió el corte a
propósito."""

_K_REC = "rec_cambios_receta"
_K_INS = "rec_cambios_insumo"
_K_USR = "rec_cambios_usuario"
_K_TIPO = "rec_cambios_tipo"
_K_FOCO = "rec_cambios_foco"


# ─── Las cuentas (puras) ────────────────────────────────────────────────────
def tipo_de_cambio(antes, despues):
    """«Agregado», «Quitado» o «Cantidad». `ediciones_base` escribe 0 en el
    lado donde el insumo no estaba."""
    if not antes:
        return "Agregado"
    if not despues:
        return "Quitado"
    return "Cantidad"


def es_grande(ed):
    d, a = ed["delta"], ed.get("antes") or 0.0
    return abs(d) >= GRANDE_SOLES and (a <= 0 or abs(d) / a >= GRANDE_PCT)


def id_edicion(ed):
    return f'{ed.get("rb", ed["cod_prod"])}|{pd.Timestamp(ed["t"]):%Y-%m-%d %H:%M:%S}'


def lineas(ed, nombres=None, tipo=None, insumos=None):
    """Las líneas de una edición: [(insumo, tipo, antes, después, soles)],
    filtradas por tipo y por nombre de insumo si vienen."""
    nombres = nombres or {}
    out = []
    for cod, nom, qa, qd, soles in ed["cambios"]:
        t = tipo_de_cambio(qa, qd)
        n = nombres.get(cod) or nom
        if tipo and t != tipo:
            continue
        if insumos and n not in insumos:
            continue
        out.append((n, t, qa if qa else None, qd if qd else None, soles))
    return out


def filtrar(eds, ini, fin, recetas=(), insumos=(), usuarios=(), tipo=None,
            nombres=None):
    """Las ediciones del rango [ini, fin] (fechas) que cumplen los filtros,
    de la más nueva a la más vieja. Con un filtro de insumo o de tipo, una
    edición entra si le queda alguna línea."""
    out = []
    for e in eds:
        d = pd.Timestamp(e["t"]).date()
        if not (ini <= d <= fin):
            continue
        if recetas and e["nombre"] not in recetas:
            continue
        if usuarios and e["usr"] not in usuarios:
            continue
        if (tipo or insumos) and not lineas(e, nombres, tipo, insumos):
            continue
        out.append(e)
    return sorted(out, key=lambda e: e["t"], reverse=True)


def _col(df, nombre):
    """La columna `nombre` sin mirar mayúsculas: recetaventa trae «NOMB
    PLATO» en R2 y «Nomb Plato» en los datos de prueba."""
    if df is None:
        return None
    return next((c for c in df.columns if str(c).strip().casefold() == nombre.casefold()), None)


def codigo_actual(ed, df_rb):
    """El código de producto que la receta base tiene HOY. El del log puede
    ser otro: la «Marca Chorizo Criollo» pasó de 0002395 a 0003964, y con el
    viejo no la llevaba ningún plato."""
    c_rb, c_prod = _col(df_rb, "COD RB"), _col(df_rb, "COD PROD RB")
    if c_rb and c_prod and ed.get("rb") is not None:
        m = df_rb[c_rb].astype(str).str.strip() == str(ed["rb"]).strip()
        if m.any():
            return str(df_rb.loc[m, c_prod].iloc[0]).strip()
    return str(ed["cod_prod"]).strip()


def usos(cod_prod, df_rv, df_rb):
    """(platos, recetas base) que llevan HOY la receta de código de producto
    `cod_prod`, por nombre y sin repetir."""
    def _de(df, c_cod, c_nom):
        c_cod, c_nom = _col(df, c_cod), _col(df, c_nom)
        if not (c_cod and c_nom):
            return []
        m = df[c_cod].astype(str).str.strip() == str(cod_prod).strip()
        return sorted(set(df.loc[m, c_nom].astype(str).str.strip()) - {""})
    return _de(df_rv, "COD INS", "Nomb Plato"), _de(df_rb, "COD INS RB", "RB NOMBRE")


def nombres_insumos(df_rv, df_rb):
    """{código: nombre} de los insumos, de las dos recetas: `ediciones_base`
    nombra sólo con recetabase, y un insumo que salió de todas las recetas
    base quedaba con su código."""
    nom = {}
    for df, c_cod, c_nom in ((df_rb, "COD INS RB", "INSUMO"), (df_rv, "COD INS", "INS RV")):
        c_cod, c_nom = _col(df, c_cod), _col(df, c_nom)
        if c_cod and c_nom:
            for c, n in zip(df[c_cod].astype(str).str.strip(),
                            df[c_nom].astype(str).str.strip()):
                if n:
                    nom.setdefault(c, n)
    return nom


def ctx_fecha(eds, hoy=None):
    """El `ctx` del panel de fecha de la tarjeta, como el de Costo Carta
    (`carta_costeada.ctx_fecha`): Recetas no publica uno. Va de la primera
    edición a HOY —un día sin ediciones también es un dato— y abre en los
    últimos 30 días. None sin ediciones."""
    if not eds:
        return None
    hoy = hoy or datetime.date.today()
    fmin = min(pd.Timestamp(e["t"]).date() for e in eds)
    fmax = max(hoy, max(pd.Timestamp(e["t"]).date() for e in eds))
    defecto = next((r for c, _n, _g, r in atajos_tarjeta(fmax, (fmin, fmax))
                    if c == ATAJO_INICIAL), (fmin, fmax))
    return {"k_rango": clave_rango("Recetas", False, CATEGORIA_FECHA),
            "fecha_min": fmin, "fecha_max": fmax, "reporte": "Recetas",
            "usa_carga_rango": False, "hoy": hoy, "rango_default": defecto,
            "rango_default_cat": {CATEGORIA_FECHA: defecto}}


# ─── La vista ───────────────────────────────────────────────────────────────
def _soles(v, signo=False):
    if v is None or pd.isna(v):
        return "—"
    prefijo = ("+" if v > 0 else "−" if v < 0 else "") if signo else ("−" if v < 0 else "")
    return f"{prefijo}S/ {abs(v):,.2f}"


def _signo(v, dec=0):
    """«+73 %» / «−18 %», con el menos tipográfico de los soles."""
    return f"{'+' if v > 0 else '−' if v < 0 else ''}{abs(v):.{dec}f} %"


def _pct(ed):
    a = ed.get("antes") or 0.0
    return ed["delta"] / a if a > 0 else None


def _kpi(titulo, valor, pie=""):
    return (f'<div class="rec-alza-kpi"><small>{escape(titulo)}</small>'
            f'<b>{escape(str(valor))}</b><span>{escape(pie)}</span></div>')


def _key_tabla(ids):
    """La key de la lista lleva la firma de las filas: la selección de un
    `st.dataframe` es de la KEY, no de sus datos (regla #556)."""
    return "rec_cambios_lista_" + hashlib.md5("|".join(ids).encode()).hexdigest()[:12]


def _leer_foco(ids_previos):
    """La edición elegida en la corrida anterior, leída ANTES de dibujar."""
    ss = st.session_state
    key = ss.get("_rec_cambios_key")
    try:
        filas = ss[key]["selection"]["rows"] if key in ss else []
    except Exception:
        filas = []
    if filas and 0 <= filas[0] < len(ids_previos):
        ss[_K_FOCO] = ids_previos[filas[0]]


def _lista(L, nombres, tipo, insumos):
    ids = [id_edicion(e) for e in L]
    _leer_foco(st.session_state.get("_rec_cambios_ids") or [])
    foco = st.session_state.get(_K_FOCO)
    pos = ids.index(foco) if foco in ids else 0
    st.session_state[_K_FOCO] = ids[pos]
    df = pd.DataFrame({
        "Fecha": [pd.Timestamp(e["t"]).to_pydatetime() for e in L],
        "Receta base": [("● " if es_grande(e) else "") + e["nombre"] for e in L],
        "Usuario": [e["usr"] or "—" for e in L],
        "Líneas": [len(lineas(e, nombres, tipo, insumos)) for e in L],
        "Δ costo": [e["delta"] for e in L],
        "Δ %": [(_pct(e) or 0.0) * 100 if _pct(e) is not None else float("inf") for e in L],
    })

    def _fila(r):
        return [f"background-color: {LAVANDA_FONDO}" if r.name == pos else ""] * len(r)

    sty = (df.style.apply(_fila, axis=1)
           .format({"Δ costo": lambda v: _soles(v, True),
                    "Δ %": lambda v: "nueva" if v == float("inf") else _signo(v)}))
    key = _key_tabla(ids)
    st.session_state["_rec_cambios_key"] = key
    st.session_state["_rec_cambios_ids"] = ids
    st.dataframe(
        sty, key=key, on_select="rerun", selection_mode="single-row-required",
        selection_default={"selection": {"rows": [pos]}},
        hide_index=True, row_height=27, height=min(36 + 27 * len(df), 600),
        column_config={
            "Fecha": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm", width=110),
            "Receta base": st.column_config.TextColumn(
                help="● = cambio grande de costo (±50 % y ±S/ 5): conviene mirarlo"),
            "Usuario": st.column_config.TextColumn(width=90),
            "Líneas": st.column_config.NumberColumn(width=56),
            "Δ costo": st.column_config.Column(
                width=96, help="Cuánto cambió el costo de la receta, con los precios de antes"),
            "Δ %": st.column_config.Column(width=64),
        })
    return L[pos]


def _ficha(e, eds, nombres, tipo, insumos, df_rv, df_rb):
    t = pd.Timestamp(e["t"])
    p = _pct(e)
    st.markdown(
        f'<p class="chart-card-hdr" style="margin-bottom:2px">{escape(e["nombre"])}</p>'
        f'<p class="rec-cambios-meta">Editada el {t:%d/%m/%Y} a las {t:%H:%M} por '
        f'<b>{escape(e["usr"] or "—")}</b> · {e.get("guardados", 1)} guardado'
        f'{"s" if e.get("guardados", 1) != 1 else ""}</p>',
        unsafe_allow_html=True)
    if es_grande(e):
        st.markdown(
            f'<div class="rec-cambios-aviso">Cambio grande de costo: la receta pasó de '
            f'{_soles(e["antes"])} a {_soles(e["despues"])}'
            f'{f" ({_signo(p * 100)})" if p is not None else ""}. Conviene revisar que no '
            f'sea un error de digitación.</div>', unsafe_allow_html=True)
    clase = "sube" if e["delta"] > 0 else "baja"
    st.markdown(
        '<div class="rec-cambios-costos">'
        f'<div><small>Costo antes</small><b>{_soles(e["antes"])}</b></div>'
        f'<div><small>Costo después</small><b>{_soles(e["despues"])}</b></div>'
        f'<span class="rec-cambios-chip {clase}">{_soles(e["delta"], True)}'
        f'{f" · {_signo(p * 100, 1)}" if p is not None else ""}</span></div>',
        unsafe_allow_html=True)

    ls = lineas(e, nombres, tipo, insumos)
    tabla = pd.DataFrame(ls, columns=["Insumo", "Cambio", "Antes", "Después", "Δ costo"])
    # Un vacío en `st.dataframe` se pinta «None» (regla #529): el lado que no
    # existe va en texto, ya escrito.
    for c in ("Antes", "Después"):
        tabla[c] = [("—" if v is None else f"{v:,.3f}".rstrip("0").rstrip("."))
                    for v in tabla[c]]
    tabla["Δ costo"] = [_soles(v, True) for v in tabla["Δ costo"]]
    st.dataframe(tabla, hide_index=True, row_height=27,
                 height=min(36 + 27 * max(len(tabla), 1), 330),
                 column_config={"Cambio": st.column_config.TextColumn(width=84),
                                "Antes": st.column_config.TextColumn(width=80),
                                "Después": st.column_config.TextColumn(width=80),
                                "Δ costo": st.column_config.TextColumn(width=96)})

    platos, bases = usos(codigo_actual(e, df_rb), df_rv, df_rb)
    chips = ([f'<span>{escape(x)}</span>' for x in platos]
             + [f'<span class="base" title="Receta base">{escape(x)}</span>' for x in bases])
    rot = f'{len(platos)} plato{"s" if len(platos) != 1 else ""}'
    if bases:
        rot += f' y {len(bases)} receta{"s" if len(bases) != 1 else ""} base'
    st.markdown(
        f'<p class="rec-cambios-sub">Dónde se usa hoy · {rot}</p>'
        f'<div class="rec-cambios-usos">{"".join(chips) or "<span>Ninguna receta la usa hoy</span>"}</div>',
        unsafe_allow_html=True)

    hist = sorted((x for x in eds if x.get("rb") == e.get("rb")),
                  key=lambda x: x["t"], reverse=True)
    filas = "".join(
        f'<div class="{"on" if id_edicion(x) == id_edicion(e) else ""}">'
        f'<span>{pd.Timestamp(x["t"]):%d/%m/%y}</span><span>{escape(x["usr"] or "—")}</span>'
        f'<span>{len(x["cambios"])} línea{"s" if len(x["cambios"]) != 1 else ""}</span>'
        f'<span class="{"sube" if x["delta"] > 0 else "baja"}">{_soles(x["delta"], True)}</span></div>'
        for x in hist)
    st.markdown(
        f'<p class="rec-cambios-sub">Historial de esta receta · {len(hist)} '
        f'edicion{"es" if len(hist) != 1 else ""}</p>'
        f'<div class="rec-cambios-hist">{filas}</div>', unsafe_allow_html=True)


def render_cambios_recetas_base(df_rv=None, df_rb=None):
    """La vista. `df_rv` y `df_rb`: recetaventa y recetabase, para nombrar
    los insumos y decir dónde se usa cada receta."""
    with st.container(border=True, key="rec_card_cambios"):
        cab = st.container(horizontal=True, gap="small",
                           vertical_alignment="center", key="rec_cambios_cab")
        with cab:
            st.markdown('<p class="chart-card-hdr">Cambios en recetas base</p>',
                        unsafe_allow_html=True)
        with st.spinner("Leyendo el historial de las recetas base…"):
            eds = ediciones_bases()
        if not eds:
            st.info("Todavía no está el historial de las recetas base en los datos "
                    "(filas «recetabaselog» y «recetabaselogdet» del Sheet).")
            return
        nombres = nombres_insumos(df_rv, df_rb)
        ctx = ctx_fecha(eds)
        with cab:
            with st.container(key="rec_cambios_cab_fecha", width="content"):
                selector_fecha_tarjeta("rec_cambios_f", None,
                                       categoria=CATEGORIA_FECHA, ctx=ctx)
        ini, fin = rango_tarjeta(CATEGORIA_FECHA, ctx)
        del_rango = filtrar(eds, ini, fin)

        # Las opciones salen del RANGO: lo elegido que se queda afuera al
        # angostar la fecha se conserva y la lista sale vacía (regla #625).
        recetas, ops_rec = seleccion_multiple(
            _K_REC, sorted({e["nombre"] for e in del_rango}), conservar=True)
        insumos, ops_ins = seleccion_multiple(
            _K_INS, sorted({n for e in del_rango for n, *_ in lineas(e, nombres)}),
            conservar=True)
        usuarios, ops_usr = seleccion_multiple(
            _K_USR, sorted({e["usr"] for e in del_rango if e["usr"]}), conservar=True)
        with cab:
            with st.container(key="rec_cambios_cab_receta", width="content"):
                st.multiselect("Receta", ops_rec, key=_K_REC, width=210,
                               placeholder="Todas las recetas",
                               label_visibility="collapsed")
            with st.container(key="rec_cambios_cab_insumo", width="content"):
                st.multiselect("Insumo", ops_ins, key=_K_INS, width=190,
                               placeholder="Todos los insumos",
                               label_visibility="collapsed")
            with st.container(key="rec_cambios_cab_usuario", width="content"):
                st.multiselect("Usuario", ops_usr, key=_K_USR, width=130,
                               placeholder="Todos", label_visibility="collapsed")
            with st.container(key="rec_cambios_cab_tipo", width="content"):
                opc = st.segmented_control("Qué cambió", _OPC_TIPO, key=_K_TIPO,
                                           default="Todo",
                                           label_visibility="collapsed")
        tipo = _TIPO_DE_OPC.get(opc or "Todo")

        L = filtrar(eds, ini, fin, recetas, insumos, usuarios, tipo, nombres)
        n_lin = {t: sum(1 for e in L for _n, tt, *_ in lineas(e, nombres, tipo, insumos)
                        if tt == t) for t in TIPOS}
        st.markdown(
            '<div class="rec-alza-kpis rec-cambios-kpis">'
            + _kpi("Ediciones", len(L), f'{sum(e.get("guardados", 1) for e in L)} guardados')
            + _kpi("Recetas base", len({e.get("rb") for e in L}),
                   ", ".join(sorted({e["usr"] for e in L if e["usr"]})))
            + _kpi("Líneas cambiadas", sum(n_lin.values()),
                   f'{n_lin["Agregado"]} agreg. · {n_lin["Quitado"]} quit. · '
                   f'{n_lin["Cantidad"]} cant.')
            + _kpi("Cambio grande de costo", sum(1 for e in L if es_grande(e)),
                   "±50 % y ±S/ 5")
            + '</div>', unsafe_allow_html=True)

        if not L:
            st.info("Ninguna edición de receta base con esta fecha y estos filtros.")
            return
        izq, der = st.columns(COLUMNAS_DRILL_FICHA, gap="medium")
        with izq:
            e = _lista(L, nombres, tipo, insumos)
        with der:
            with st.container(key="rec_cambios_ficha"):
                _ficha(e, eds, nombres, tipo, insumos, df_rv, df_rb)
