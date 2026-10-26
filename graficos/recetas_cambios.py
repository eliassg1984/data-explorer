"""graficos.recetas_cambios — «Cambios en recetas», en Recetas (reglas #671
y #707).

Qué cambió en las recetas y en los precios de venta, quién lo cambió y
cuánto movió el costo. Nació el 2026-10-19 como «Cambios Recetas Base»
(«¿puedes identificar qué cantidad o ítem cambió en un mes?»); desde el
2026-10-22 junta TRES fuentes, a pedido, y es una pieza propia
(`recetas_cambios.js` + `.css`) sobre el boceto aprobado
(https://claude.ai/artifact/GUZqHk1LzTiEbX58EBogAZ):

  · RECETAS BASE — `simulador_receta.ediciones_base`, la misma cuenta que
    dibuja los ▼ en la ficha de Costo Carta (regla #657), leída del log del
    Almacén (`recetabaselog` / `recetabaselogdet`: cada fila es la receta
    como estaba ANTES de un guardado). Verificado contra el SQL: en 1.349 de
    1.352 guardados la cadena no salta ninguno. Una EDICIÓN junta los
    guardados a menos de dos horas, y el costo va con los precios de ANTES.
  · RECETAS DE PLATO — el POS no las guarda: salen de las FOTOS diarias de
    `recetaventa.parquet` (`historial_recetas.py`, regla #705), foto contra
    foto (`historial_recetas.ediciones_plato`). La fecha es la del último
    guardado de la receta si cae entre las dos fotos; si no, la de la foto
    (`aprox`).
  · PRECIOS DE VENTA — la auditoría del POS (`INFSEGURIDAD.MMOVIMIENTO`,
    campos «Precio Venta Canal 1..5»), por la fila `auditoriacostos` del
    Sheet, que es la de la ficha de Costo Carta (#658) con esos cinco campos
    de más (`simulador_receta.consulta_sheet_auditoria`). Mientras la fila
    no los traiga, salen de las fotos, sin hora ni usuario. Un producto que
    NACE con su precio no es un cambio (decisión del usuario).

Python arma una lista de cambios del rango de la tarjeta (`armar`) y la
pieza resuelve todo lo demás —pestañas, indicadores, buscar, usuario, la
lista, la ficha y el historial— sin volver a Python. Vuelve sólo cuando se
elige otro rango (es el botón de fecha, de Streamlit). El salto desde la
ficha de Costo de Carta («Ver cambios») deja el plato en `K_PLATO`
(`ir_desde_carta`) y la pieza abre filtrada en él.
"""

from graficos.movil import css_movil, js_movil
import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import data
import historial_recetas as hr
import simulador_receta as sr
from estado_rango import atajos_tarjeta, clave_rango
from graficos.base import rango_tarjeta, selector_fecha_tarjeta
from graficos.carta_costeada import ARCHIVO as ARCHIVO_CARTA, cambios_auditoria, ediciones_bases
from graficos.recetas_comun import divisor_neto

CATEGORIA_FECHA = "cambios_rb"
ATAJO_INICIAL = "d30"
"""Abre en los últimos 30 días: «como mínimo un mes» (regla #616)."""

GRANDE_PCT = 0.5
GRANDE_SOLES = 5.0
"""«Cambio grande de costo»: la edición mueve el costo de la receta ±50 % y
al menos S/ 5. Es para MIRAR, no un error: el 07/10/2026 el «Tomate criollo
limpio» quitó el tomate y sumó 1.200 g de arúgula —de S/ 10,50 a 100,08—,
pero el mismo umbral marca la Milanesa de lomo, que cambió el corte a
propósito."""

JUNTAR_PRECIOS = pd.Timedelta(hours=2)
"""Los cambios de precio del mismo producto a menos de dos horas son UNO:
se cambia canal por canal, y a veces se corrige un minuto después."""

CANALES = ("En el Local", "Delivery", "Para Llevar", "Rappi", "Pedidos Ya")
_COSTO_CARTA = ("COSTO SALON", "COSTO DELIVERY", "COSTO LLEVAR", "COSTO RAPPI", "COSTO 5")
_PRECIO_CARTA = ("P.VENTA SALON", "P.VENTA DELIVERY", "P.VENTA LLEVAR", "P.VENTA RAPPI", "P.VENTA 5")
_NETO_CARTA = ("P.NET SALON", "P.NET DELIV", "P.NET LLEVAR", "P. NET RAPPI", "P. NET 5")

K_PLATO = "rec_cambios_plato"
"""El plato que pidió «Ver cambios» en Costo de Carta: {cod, n}."""

_PIEZA = st.components.v2.component(
    "recetas_cambios",
    css=css_movil((Path(__file__).parent / "recetas_cambios.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent / "recetas_cambios.js").read_text(encoding="utf-8")),
)
_K_PIEZA = "rec_cambios_pieza"


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


def lineas(ed, nombres=None, tipo=None, insumos=None):
    """Las líneas de una edición de receta base: [(insumo, tipo, antes,
    después, soles)], filtradas por tipo y por nombre de insumo si vienen."""
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
    (`carta_costeada.ctx_fecha`): Recetas no publica uno. `eds` es
    cualquier lista de dicts con su `t`. Va del primer cambio a HOY —un día
    sin cambios también es un dato— y abre en los últimos 30 días. None sin
    cambios."""
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


def precios_auditoria(cambios):
    """Los cambios de precio de venta de la auditoría del POS, ya limpios por
    `simulador_receta.cambios_auditoria`: [{t, usr, cod, canales}], con
    `canales` = [(canal, antes, después)]. Junta los guardados del mismo
    producto a menos de `JUNTAR_PRECIOS` (el «antes» del primero, el
    «después» del último) y descarta el canal que volvió a donde estaba.
    Un producto que nace con su precio no llega: `cambios_auditoria` saca lo
    que tenía el ANTES vacío. Pura."""
    if cambios is None or len(cambios) == 0:
        return []
    abiertos, out = {}, []
    for r in cambios.sort_values("t", kind="stable").itertuples(index=False):
        if r.pantalla != sr.PANTALLA_PLATO:
            continue
        cs = {CANALES[int(c[-1]) - 1]: (sr._numero(a), sr._numero(b))
              for c, (a, b) in r.campos.items() if c in sr.CAMPOS_PRECIO_VENTA}
        if not cs:
            continue
        previo = abiertos.get(r.cod)
        if previo is not None and r.t - previo["t"] <= JUNTAR_PRECIOS:
            for canal, (a, b) in cs.items():
                previo["_c"][canal] = (previo["_c"].get(canal, (a, b))[0], b)
            previo["t"], previo["usr"] = r.t, r.usr or previo["usr"]
            continue
        nuevo = {"t": r.t, "usr": r.usr, "cod": r.cod, "_c": dict(cs)}
        abiertos[r.cod] = nuevo
        out.append(nuevo)
    for x in out:
        c = x.pop("_c")
        x["canales"] = [(k, *c[k]) for k in CANALES
                        if k in c and not (pd.isna(c[k][0]) and pd.isna(c[k][1]))
                        and not abs((c[k][0] or 0) - (c[k][1] or 0)) < 1e-9]
    return [x for x in out if x["canales"]]


def _lima(t):
    t = pd.Timestamp(t)
    return t.tz_convert("America/Lima").tz_localize(None) if t.tzinfo else t


def fecha_plato(ed, t_antes, t_despues):
    """Cuándo pasó una edición de receta de plato: el último guardado de la
    receta si cae entre las dos fotos —es la hora de verdad—; si no, la hora
    de la foto nueva, marcada `aprox` (dos ediciones entre dos fotos, o una
    receta quitada, que ya no tiene fecha). (t, aprox)."""
    f = ed.get("fmodif")
    if f is not None and not pd.isna(f) and t_antes < pd.Timestamp(f) <= t_despues:
        return pd.Timestamp(f), False
    return t_despues, True


# ─── Lo que lleva la pieza ──────────────────────────────────────────────────
def _iso(t):
    return pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M")


def _r(v, d=4):
    return None if v is None or pd.isna(v) else round(float(v), d)


def _carta_por_cod(carta):
    """{código: (nombre, grupo › subgrupo, [costo, precio, neto] por canal)}
    de la carta costeada: la tiene TODO producto de venta, con receta o
    sin. Un costo de cero o vacío es «sin costo» (Propina, vales, anticipos)."""
    if carta is None or carta.empty or "COD PLATO" not in carta.columns:
        return {}
    out = {}
    num = lambda r, c: pd.to_numeric(r.get(c), errors="coerce")  # noqa: E731
    for r in carta.to_dict("records"):
        canales = [[_r(num(r, c)), _r(num(r, p), 2), _r(num(r, n))]
                   for c, p, n in zip(_COSTO_CARTA, _PRECIO_CARTA, _NETO_CARTA)]
        out[str(r["COD PLATO"]).strip()] = (
            str(r.get("ITEM VENT") or "").strip(),
            " › ".join(str(r.get(c) or "").strip() for c in ("GRUPO", "SUBGRUPO") if r.get(c)),
            canales)
    return out


def _platos_hoy(df_rv, df_rb):
    """{código de plato: [nombre, receta, [códigos de receta base]]} de la
    receta de HOY: con eso la pieza sabe qué cambios le tocan a un plato (los
    suyos, los de su receta y los de las recetas base que lleva directo)."""
    if df_rv is None or df_rv.empty:
        return {}
    c_plato, c_nom = _col(df_rv, "COD PLATO"), _col(df_rv, "NOMB PLATO")
    c_rv, c_ins = _col(df_rv, "COD RV"), _col(df_rv, "COD INS")
    if not all((c_plato, c_nom, c_rv, c_ins)):
        return {}
    rb_de = {}
    c_prod, c_rb = _col(df_rb, "COD PROD RB"), _col(df_rb, "COD RB")
    if c_prod and c_rb:
        rb_de = dict(zip(df_rb[c_prod].astype(str).str.strip(), df_rb[c_rb].astype(str).str.strip()))
    out = {}
    for p, n, rv, ins in zip(df_rv[c_plato].astype(str).str.strip(), df_rv[c_nom].astype(str),
                             df_rv[c_rv].astype(str).str.strip(), df_rv[c_ins].astype(str).str.strip()):
        x = out.setdefault(p, [n.strip(), rv, []])
        if ins in rb_de and rb_de[ins] not in x[2]:
            x[2].append(rb_de[ins])
    return out


def _item_base(e, nombres, df_rv, df_rb):
    cod = codigo_actual(e, df_rb)
    platos, _bases = usos(cod, df_rv, df_rb)
    c_ins, c_plato = _col(df_rv, "COD INS"), _col(df_rv, "COD PLATO")
    cods = (sorted(set(df_rv.loc[df_rv[c_ins].astype(str).str.strip() == cod, c_plato].astype(str).str.strip()))
            if c_ins and c_plato else [])
    return {"tipo": "base", "k": f"rb:{str(e.get('rb') or cod).strip()}", "t": _iso(e["t"]),
            "usr": e["usr"] or "", "nombre": e["nombre"], "grupo": "", "cods": cods,
            "lineas": [[n, _r(a), _r(d), "", _r(s)] for n, _t, a, d, s in lineas(e, nombres)],
            "antes": _r(e.get("antes")), "despues": _r(e.get("despues")), "delta": _r(e["delta"]),
            "guardados": int(e.get("guardados", 1)), "usos": platos, "grande": es_grande(e)}


def _item_plato(e, t, aprox, desde, carta):
    platos = []
    for c in e["platos"]:
        nom, _g, canales = carta.get(c, (c, "", [[None, None, None]]))
        costo, precio, neto = canales[0]
        platos.append([c, nom, precio, costo, neto])
    grupo = carta.get(e["platos"][0], ("", "", None))[1] if e["platos"] else ""
    return {"tipo": "plato", "k": f"rv:{e['rv']}", "t": _iso(t), "usr": "" if aprox else (e["usr"] or ""),
            "nombre": e["nombre"] or e["rv"], "grupo": grupo, "cods": e["platos"],
            "lineas": [[ins or cod, _r(a), _r(d), u or "", _r(s)] for cod, ins, a, d, u, s in e["lineas"]],
            "antes": _r(e["antes"]), "despues": _r(e["despues"]), "delta": _r(e["delta"]),
            "nueva": e["nueva"], "quitada": e["quitada"], "aprox": aprox, "desde": _iso(desde),
            "platos": platos, "grande": es_grande(e)}


def _item_precio(cod, t, usr, canales, carta):
    nom, grupo, por_canal = carta.get(cod, (cod, "", [[None, None, None]] * len(CANALES)))
    filas = []
    for canal, a, d in canales:
        costo, _p, _n = por_canal[CANALES.index(canal)]
        filas.append([canal, _r(a, 2), _r(d, 2), costo])
    sin_costo = not any((x[0] or 0) > 0 for x in por_canal)
    return {"tipo": "precio", "k": f"pl:{cod}", "t": _iso(t), "usr": usr or "", "nombre": nom or cod,
            "grupo": grupo, "cods": [cod], "canales": filas, "sinCosto": sin_costo}


def armar(ini, fin, eds, precios, pares, carta, df_rv, df_rb, nombres):
    """La lista de cambios del rango [ini, fin], del más nuevo al más viejo.
    `precios`: los de `precios_auditoria`, o None si la auditoría no los
    trae (entonces salen de las fotos). `pares`: [(t_antes, t_despues,
    {"ediciones", "precios"})], uno por par de fotos seguidas (horas de
    Lima). Pura: la lee el test."""
    dentro = lambda t: ini <= pd.Timestamp(t).date() <= fin  # noqa: E731
    items = [_item_base(e, nombres, df_rv, df_rb) for e in filtrar(eds or [], ini, fin)]
    for t_a, t_d, par in pares:
        for e in par["ediciones"]:
            t, aprox = fecha_plato(e, t_a, t_d)
            if dentro(t):
                items.append(_item_plato(e, t, aprox, t_a, carta))
        if precios is None and dentro(t_d):
            for cod, cs in par["precios"].items():
                items.append(_item_precio(cod, t_d, "", cs, carta))
    for p in precios or []:
        if dentro(p["t"]):
            items.append(_item_precio(p["cod"], p["t"], p["usr"], p["canales"], carta))
    items.sort(key=lambda x: x["t"], reverse=True)
    for i, x in enumerate(items):
        x["id"] = i
    return items


# ─── Las fotos: lo que se lee de R2 ─────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def _lista_fotos():
    """[(hora de Lima, clave)] de las fotos de `recetaventa.parquet`, de la
    más vieja a la más nueva. Diez minutos: una foto nueva sale como mucho
    una vez por día."""
    s3 = data.get_s3_cliente()
    return [(_lima(t), c) for t, c in hr.fotos(s3, st.secrets["R2_BUCKET"])]


@st.cache_data(persist="disk", show_spinner=False, max_entries=800)
def _par_cacheable(clave_a, clave_d, version=hr.VERSION):
    """Lo que cambió entre dos fotos. Una foto no cambia NUNCA (su nombre es
    la versión del parquet que copió), así que las dos claves son el sello
    de la caché y puede vivir en disco sin caducar: cada par se compara una
    sola vez. `version` va en la clave por si cambia la cuenta."""
    s3, bucket = data.get_s3_cliente(), st.secrets["R2_BUCKET"]
    a, d = hr.leer_foto(s3, bucket, clave_a), hr.leer_foto(s3, bucket, clave_d)
    return {"ediciones": hr.ediciones_plato(a, d), "precios": hr.precios_de_fotos(a, d)}


def _pares(ini):
    """Los pares de fotos seguidas cuya foto nueva es del rango o posterior.
    Una foto que no se pudo leer no deja la vista sin las demás."""
    if not data.secrets_disponibles():
        return [], []
    try:
        fotos = _lista_fotos()
    except Exception:
        return [], []
    pares = []
    for (t_a, c_a), (t_d, c_d) in zip(fotos, fotos[1:]):
        if t_d.date() < ini:
            continue
        try:
            pares.append((t_a, t_d, _par_cacheable(c_a, c_d)))
        except Exception:
            continue
    return fotos, pares


def ir_desde_carta(cod):
    """«Ver cambios» en la ficha de Costo de Carta: deja el plato para que la
    pieza abra filtrada en él y pide el salto a esta sección, con una
    corrida completa (la Carta es otro fragment)."""
    try:
        import navegacion
        from navegacion_retorno import capturar_origen
        capturar_origen()
        n = st.session_state.get("_rec_cambios_n", 0) + 1
        st.session_state["_rec_cambios_n"] = n
        st.session_state[K_PLATO] = {"cod": str(cod), "n": n}
        navegacion._ir_a_vista("Recetas", "rec_graf_tipo", "Cambios en recetas base")
        st.session_state["_rec_cambios_ir"] = 1
    except (ImportError, AttributeError):
        return


# ─── La vista ───────────────────────────────────────────────────────────────
def render_cambios_recetas_base(df_rv=None, df_rb=None):
    """La vista. `df_rv` y `df_rb`: recetaventa y recetabase de hoy, para
    nombrar los insumos, decir dónde se usa cada receta y qué le toca a cada
    plato."""
    with st.container(border=True, key="rec_card_cambios"):
        cab = st.container(horizontal=True, gap="small",
                           vertical_alignment="center", key="rec_cambios_cab")
        with cab:
            st.markdown('<p class="chart-card-hdr">Cambios en recetas</p>',
                        unsafe_allow_html=True)
        with st.spinner("Leyendo los cambios de las recetas y los precios…"):
            eds = ediciones_bases() or []
            aud = cambios_auditoria()
            precios = precios_auditoria(aud)
            # Sin ningún «Precio Venta Canal» en la auditoría, la fila del
            # Sheet todavía no los trae: los precios salen de las fotos.
            hay_precios = aud is not None and len(aud) > 0 and any(
                c in sr.CAMPOS_PRECIO_VENTA for cs in aud["campos"] for c in cs)
            if not hay_precios:
                precios = None
            try:
                fotos = _lista_fotos() if data.secrets_disponibles() else []
            except Exception:
                fotos = []
        fechas = ([{"t": e["t"]} for e in eds] + [{"t": p["t"]} for p in precios or []]
                  + [{"t": t} for t, _c in fotos])
        ctx = ctx_fecha(fechas)
        if ctx is None:
            st.info("Todavía no hay cambios que mostrar: faltan el historial de las recetas "
                    "base (filas «recetabaselog» y «recetabaselogdet» del Sheet), la "
                    "auditoría (fila «auditoriacostos») y las fotos de las recetas de venta.")
            return
        with cab:
            with st.container(key="rec_cambios_cab_fecha", width="content"):
                selector_fecha_tarjeta("rec_cambios_f", None,
                                       categoria=CATEGORIA_FECHA, ctx=ctx)
        ini, fin = rango_tarjeta(CATEGORIA_FECHA, ctx)
        with st.spinner("Comparando las fotos de las recetas de venta…"):
            fotos, pares = _pares(ini)
        carta = _carta_por_cod(data.cargar(ARCHIVO_CARTA))
        items = armar(ini, fin, eds, precios, pares, carta, df_rv, df_rb,
                      nombres_insumos(df_rv, df_rb))
        # Se lee UNA vez: la pieza ya montada se queda con el filtro, y la que
        # se monte después (volver a la vista) abre sin él. El nombre, de la
        # carta: un directo (la Entraña) no está en las recetas.
        foco = st.session_state.pop(K_PLATO, None)
        if foco:
            foco = {**foco, "nombre": carta.get(foco["cod"], (foco["cod"],))[0]}
        _PIEZA(key=_K_PIEZA, width="stretch", data={
            "items": items, "platos": _platos_hoy(df_rv, df_rb),
            "foco": foco,
            "fotos": {"n": len(fotos), "primera": _iso(fotos[0][0]) if fotos else None},
            "preciosDeFotos": precios is None,
            "rango": [ini.isoformat(), fin.isoformat()],
            "grande": [GRANDE_PCT, GRANDE_SOLES], "divisor": divisor_neto(),
        })
