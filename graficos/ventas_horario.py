"""
graficos.ventas_horario — vista «Análisis por hora» del dashboard de Ventas
(id «Mapa por hora»): a qué hora y qué día se vende, qué se vende a cada
hora y cómo rinden los horarios que el usuario arma (las FRANJAS).

DESDE EL 2026-10-22 ES UNA PIEZA PROPIA (regla #704): `ventas_horario.js` +
`.css` (`st.components.v2`), sobre el boceto 4 aprobado
(https://claude.ai/artifact/McRvFx5rdn1tKz8xfzrWeq). Reemplazó al mapa de
Plotly con sus modos Patrones / Comparar / Franjas, la ficha de la hora en
Python y «A medida» (reglas #529-#531, #536, #551, #555, #610, #627), y se
llevó sus cinco módulos.

DOS TARJETAS, UNA PIEZA
    · «Análisis por hora»: el renglón del título con el botón de fecha
      (Python, como el resto de las tarjetas) y debajo la pieza: dos
      pestañas —«Cuándo se vende» (el mapa) y «Qué se vende a cada hora»
      (platos, grupos o áreas)—, los indicadores y, al costado, el detalle
      de lo elegido.
    · «Comparación de franjas»: las franjas que se arrastraron en el mapa o
      se armaron a mano, con Cifras, Qué se vendió y Día por día.

    Son dos montajes del MISMO componente: el de la segunda tarjeta manda
    sólo `parte: "franjas"` y el `sello`, y el navegador le presta los
    datos y el estado del primero (`window.__vhHora`, ver el `.js`). Así los
    pedidos viajan una vez, y una franja arrastrada arriba aparece abajo sin
    una corrida.

QUÉ VIAJA Y QUÉ NO
    Python manda los PEDIDOS y sus LÍNEAS del rango, de las 13 semanas
    anteriores (lo normal son 8, «Otro período» llega a 13) y del mismo
    rango 364 días antes (el año pasado, regla #659). Todo lo demás —canal,
    ámbito, hora del pedido o del cobro, eventos, venta interna, qué se
    mide, contra qué se compara, las franjas— lo resuelve el navegador sin
    una corrida. Vuelve a Python sólo la fecha (el botón de siempre).

    `armar` es puro y es la referencia del formato: `CAMPOS_P` y
    `CAMPOS_L` dicen en qué posición va cada cosa, y el `.js` las lee en esas
    mismas posiciones (el test lo vigila).

LAS CUENTAS QUE NO SE PUEDEN HACER EN EL NAVEGADOR
    · Personas: una vez por pedido, y la nota de crédito RESTA
      (`definicion_venta.pax_por`).
    · Tiempo en la mesa: de la apertura al último cobro; más de 6 horas o
      negativo es un olvido del POS, no una mesa (va vacío).
    · Local: el pedido es del salón (`En el Local`). Una MESA es un pedido
      del local con personas; Rappi y Delivery no tienen mesa.

    La venta llega como la suma todo Ventas: `filtrar_cb` (los chips de
    «Filtros», un ítem una vez y sólo venta, regla #524), y cada pedido se
    ubica por la hora en que se ABRIÓ (regla #530) — se carga por esa misma
    fecha (regla #552).
"""

from graficos.movil import css_movil, js_movil
import datetime as _dt
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import cortes
import definicion_venta as dv
from data import REPORTES, cargar_rango, rango_fechas, sello_datos, venta_por_turno
from graficos.base import (_resolver, ctx_rango_propio, rango_tarjeta,
                           selector_fecha_tarjeta)
from graficos.ventas_comparativo import GRUPOS_RAROS

VERSION = 1
"""Versión del formato de `armar`: va en la clave de lo guardado en la sesión.
Tocar qué viaja (o cómo se cuenta) es subirla."""

CATEGORIA = "vt_hora"
"""El rango PROPIO de la vista (`rango_cat_Ventas_vt_hora`, regla #531):
mover esta fecha no toca la de arriba ni recarga el parquet del reporte."""

SEMANAS_ATRAS = 13
"""Cuánto antes del rango se carga: lo normal mira 8 semanas y «Otro
período» ofrece 3, 8 y 13."""

DIAS_AP = 364
"""El año pasado es 364 días antes, el mismo día de la semana (regla #659)."""

MAX_MIN_MESA = 360
"""Un pedido abierto más de 6 horas es un olvido del POS, no una mesa."""

CANAL_LOCAL = "En el Local"

CAMPOS_P = ("dia", "abre", "canal", "pax", "dur", "dia_cobro", "cobro", "local")
"""Un pedido, en ESTE orden: el día (índice en `dias`) y el minuto en que se
abrió, el canal (índice en `canales`), las personas (o None), los minutos en
la mesa (o None), el día y el minuto del último cobro, y 1 si es del local."""

CAMPOS_L = ("ped", "prod", "cant", "venta", "desc", "tdesc")
"""Una línea, en ESTE orden: el pedido (posición en `P`), el producto
(índice en `prods`), la cantidad, la venta, el descuento y el tipo de
descuento (índice en `tdesc`)."""

_K_PIEZA = "vh_pieza"
_K_PIEZA_FRANJAS = "vh_pieza_franjas"
_K_CACHE = "_vh_payload"
_K_IR = "_vh_ir"
"""El salto desde «Análisis de platos» (`ventas_platos._ir_a_hora`): el
plato que la pieza abre en «Qué se vende a cada hora»."""

_PIEZA = st.components.v2.component(
    "ventas_horario",
    css=css_movil((Path(__file__).parent / "ventas_horario.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent / "ventas_horario.js").read_text(encoding="utf-8")),
)

_TILDES_AREA = {"Pasteleria": "Pastelería", "Frios": "Fríos"}
"""El POS escribe las áreas en mayúsculas y sin tilde; se nombran como el
resto de la carta. Un área que no esté acá sale sólo con la mayúscula."""


def nombre_area(s):
    """«CARNES Y PESCADOS» → «Carnes y pescados»; vacío → «Sin área»."""
    s = s.astype("object")
    s = s.where(s.notna(), "").astype(str).str.strip()
    s = s.str.capitalize().replace(_TILDES_AREA)
    return s.mask(s == "", "Sin área")


# ===========================================================================
# LOS DATOS
# ===========================================================================

def ventanas(ini, fin, primero=None, ultimo=None):
    """Los tramos de fechas que se cargan, cronológicos y sin pisarse: el
    rango con sus 13 semanas anteriores, y el mismo rango 364 días antes.
    Recortados a lo que tiene el parquet (`primero`, `ultimo`): un tramo que
    queda afuera no se pide, y el navegador sabe que ahí no hay con qué
    comparar."""
    tramos = [(ini - _dt.timedelta(days=7 * SEMANAS_ATRAS), fin),
              (ini - _dt.timedelta(days=DIAS_AP), fin - _dt.timedelta(days=DIAS_AP))]
    out = []
    for a, b in sorted(tramos):
        if primero:
            a = max(a, primero)
        if ultimo:
            b = min(b, ultimo)
        if a > b:
            continue
        if out and a <= out[-1][1] + _dt.timedelta(days=1):
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def columnas(df):
    """Los nombres reales de las columnas que usa `armar` (None si falta)."""
    return {
        "abre": _resolver(df, ["Fecha Registro Pedido"]),
        "cobro": _resolver(df, ["Fecha Emision"]),
        "fecha": _resolver(df, ["Fec Reg Documento", "Fecha"]),
        "venta": _resolver(df, ["Venta Item Ddocumento", "Venta"]),
        "pax": _resolver(df, ["Cant Pax", "Pax"]),
        "ped": _resolver(df, ["Llave Local Pedido", "Codigo Pedido Ddocumento",
                              "Pedido"]),
        "cant": _resolver(df, ["Cantidad Item Ddocumento", "Cantidad"]),
        "canal": _resolver(df, ["Canal Venta", "Canal_Venta", "Canal"]),
        "grupo": _resolver(df, ["Grupo"]),
        "sub": _resolver(df, ["Sub Grupo", "Sub_Grupo", "Subgrupo"]),
        "prod": _resolver(df, ["Nomb Item Venta", "Producto", "Plato"]),
        "area": _resolver(df, ["Area Produccion"]),
        "desc": _resolver(df, ["Descuento Item Ddocumento", "Descuento"]),
        "tdesc": _resolver(df, ["Nombre Descuento"]),
    }


def _txt(df, col, vacio=""):
    if not col:
        return pd.Series(vacio, index=df.index, dtype="object")
    s = df[col].astype("object")
    return s.where(s.notna(), vacio).astype(str).str.strip().replace("", vacio)


def _num(df, col):
    if not col:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def _minuto(t):
    return (t.dt.hour * 60 + t.dt.minute).astype("int64")


def armar(df, ini, fin, tramos, ultimo=None):
    """Lo que viaja a la pieza (ver el docstring del módulo), o None si no
    hay ventas con hora. `df` ya viene filtrado como el resto de Ventas;
    `tramos` son las `ventanas` que se cargaron."""
    if df is None or df.empty:
        return None
    c = columnas(df)
    c_t = c["abre"] or c["fecha"]
    if not c_t or not c["venta"]:
        return None
    abre = pd.to_datetime(df[c_t], errors="coerce")
    cobro = pd.to_datetime(df[c["cobro"]], errors="coerce") if c["cobro"] else abre
    t = pd.DataFrame({
        "ped": (df[c["ped"]].astype(str) if c["ped"]
                else pd.Series(np.arange(len(df)).astype(str), index=df.index)),
        "abre": abre, "cobro": cobro.fillna(abre),
        "canal": _txt(df, c["canal"]),
        "grupo": _txt(df, c["grupo"], "(sin grupo)"),
        "sub": _txt(df, c["sub"], "(sin subgrupo)"),
        "prod": _txt(df, c["prod"], "(sin nombre)"),
        "area": (nombre_area(df[c["area"]]) if c["area"]
                 else pd.Series("Sin área", index=df.index)),
        "venta": _num(df, c["venta"]), "cant": _num(df, c["cant"]),
        "desc": _num(df, c["desc"]), "tdesc": _txt(df, c["tdesc"]),
        "pax": (pd.to_numeric(df[c["pax"]], errors="coerce") if c["pax"]
                else pd.Series(np.nan, index=df.index)),
    })
    _c_doc = dv.columna(df, dv.LLAVE_DOC)
    t["doc"] = df[_c_doc].astype(str).values if _c_doc else ""
    t = t[t["abre"].notna()]
    if t.empty:
        return None

    # ── Los pedidos ──────────────────────────────────────────────────────
    g = t.groupby("ped", sort=False)
    pe = pd.DataFrame({"abre": g["abre"].min(), "cobro": g["cobro"].max(),
                       "canal": g["canal"].first()})
    tp = t.dropna(subset=["pax"]).assign(_por=lambda x: x["ped"])
    if tp.empty:
        pax = pd.Series(dtype=float)
    else:
        pax = dv.pax_por(tp, "ped", "pax", doc="doc" if tp["doc"].ne("").any()
                         else None, por="_por")
    pe["pax"] = pax.reindex(pe.index).clip(lower=0)
    dur = (pe["cobro"] - pe["abre"]).dt.total_seconds() / 60
    pe["dur"] = dur.where((dur >= 0) & (dur <= MAX_MIN_MESA)).round(0)
    # Sin columna de canal (el demo) todo es del local.
    pe["local"] = (pe["canal"].eq(CANAL_LOCAL) | pe["canal"].eq("")).astype(int)
    pe = pe.sort_values("abre", kind="stable")
    pos = {p: i for i, p in enumerate(pe.index)}

    dias_abre = pe["abre"].dt.strftime("%Y-%m-%d")
    dias_cobro = pe["cobro"].dt.strftime("%Y-%m-%d")
    dias = sorted(set(dias_abre) | set(dias_cobro))
    di = {d: i for i, d in enumerate(dias)}
    canales = sorted(set(pe["canal"]), key=lambda x: (x != CANAL_LOCAL, x))
    ci = {k: i for i, k in enumerate(canales)}
    P = [[di[da], int(ma), ci[ca], None if pd.isna(px) else int(round(px)),
          None if pd.isna(du) else int(du), di[dc], int(mc), int(lo)]
         for da, ma, ca, px, du, dc, mc, lo in zip(
             dias_abre, _minuto(pe["abre"]), pe["canal"], pe["pax"],
             pe["dur"], dias_cobro, _minuto(pe["cobro"]), pe["local"])]

    # ── Las líneas ───────────────────────────────────────────────────────
    # Un producto se nombra con el grupo, subgrupo y área de su venta más
    # reciente.
    prods = (t.sort_values("abre", kind="stable")
             .drop_duplicates("prod", keep="last")[["prod", "grupo", "sub", "area"]]
             .sort_values("prod").reset_index(drop=True))
    pri = {p: i for i, p in enumerate(prods["prod"])}
    tdescs = sorted(set(t["tdesc"]))
    ti = {k: i for i, k in enumerate(tdescs)}
    lin = t.groupby(["ped", "prod", "tdesc"], as_index=False, sort=False)[
        ["cant", "venta", "desc"]].sum()
    lin = lin[(lin["venta"].abs() > 0.004) | (lin["cant"].abs() > 0.004)]
    L = [[pos[p], pri[x], round(float(q), 2), round(float(v), 2),
          round(float(ds), 2), ti[tt]]
         for p, x, tt, q, v, ds in zip(lin["ped"], lin["prod"], lin["tdesc"],
                                       lin["cant"], lin["venta"], lin["desc"])]

    anios = {d.year for a, b in tramos for d in (a, b)} | {ini.year, fin.year}
    fer = sorted({pd.Timestamp(f).strftime("%Y-%m-%d") for a in anios
                  for f in cortes.feriados_peru(a)})
    return {
        "v": VERSION,
        "rango": [ini.isoformat(), fin.isoformat()],
        "ultimo": (ultimo or fin).isoformat(),
        "ventanas": [[a.isoformat(), b.isoformat()] for a, b in tramos],
        "dias": dias, "canales": canales, "tdesc": tdescs,
        "prods": prods.values.tolist(), "P": P, "L": L, "feriados": fer,
        "grupos_raros": list(GRUPOS_RAROS),
    }


def _cargar(tramos, filtrar_cb, d):
    """Los tramos, de R2, por la fecha del PEDIDO (regla #552) y filtrados
    como el resto de Ventas. Sin R2 (el demo) o sin esa columna, el df de la
    vista."""
    cfg = REPORTES.get("Ventas", {})
    archivo = cfg.get("archivo", "ventas.parquet")
    col = _resolver(d, ["Fecha Registro Pedido"]) or cfg.get(
        "carga_por_rango", "FEC REG DOCUMENTO")
    partes = []
    for a, b in tramos:
        df = cargar_rango(archivo, col, a, b)
        if df is not None and not df.empty:
            partes.append(filtrar_cb(df) if filtrar_cb is not None else df)
    if not partes:
        return d
    return pd.concat(partes, ignore_index=True) if len(partes) > 1 else partes[0]


def _clave(rng, firma):
    """Qué identifica lo armado: el rango, los chips, la versión del parquet
    y del formato, y si Ventas fecha por turno (regla #593)."""
    txt = repr((rng, firma, sello_datos("ventas.parquet"), VERSION,
                venta_por_turno()))
    return hashlib.sha1(txt.encode("utf-8")).hexdigest()[:16]


# ===========================================================================
# LA VISTA
# ===========================================================================

def _ventas_horario(d, col_venta=None, col_fecha=None, col_pax=None,
                    col_pedido=None, col_prod=None, col_cant=None,
                    col_fam=None, col_sub=None, filtrar_cb=None, firma=None):
    """«Análisis por hora»: las dos tarjetas (ver el docstring del módulo).
    `d` es el df de la vista; `filtrar_cb`, lo que se le aplica a lo que la
    vista trae aparte de R2 (el `_filtrar_items` de `ventas.py`); `firma`,
    los chips de «Filtros», para reconocer lo ya armado."""
    ss = st.session_state
    cfg = REPORTES.get("Ventas", {})
    _fe = pd.to_datetime(d[col_fecha], errors="coerce").dropna() if (
        col_fecha and col_fecha in d.columns) else pd.Series(dtype="datetime64[ns]")
    lim = rango_fechas(cfg.get("archivo", "ventas.parquet"),
                       cfg.get("carga_por_rango", "FEC REG DOCUMENTO"))
    ancla = lim[1] if lim else (_fe.max().date() if not _fe.empty
                                else _dt.date.today())
    primero = lim[0] if lim else None

    ctx = ctx_rango_propio()
    ss.pop("vh_fecha_cambio", None)
    rng = (rango_tarjeta(CATEGORIA, ctx) if ctx else None) or (
        ancla - _dt.timedelta(days=29), ancla)
    rng = (rng[0], min(rng[1], ancla))

    with st.container(border=True, key="ajuste_graf_card_izq_ventas_hora"):
        with st.container(horizontal=True, gap="small",
                          vertical_alignment="center", key="vt_hora_cab"):
            st.markdown('<p class="chart-card-hdr">Análisis por hora</p>',
                        unsafe_allow_html=True)
            with st.container(key="vt_hora_cab_fecha", width="content"):
                if ctx:
                    # «vt_horaf»: el selector arma SUS keys con ese prefijo.
                    selector_fecha_tarjeta("vt_horaf", "vh_fecha_cambio",
                                           categoria=CATEGORIA, ctx=ctx)
                else:
                    st.caption(f"{rng[0]:%d/%m/%Y} – {rng[1]:%d/%m/%Y}")

        clave = _clave(rng, firma)
        guardado = ss.get(_K_CACHE)
        if guardado and guardado[0] == clave:
            datos = guardado[1]
        else:
            tramos = ventanas(rng[0], rng[1], primero, ancla)
            with st.spinner("Trayendo los pedidos del período…"):
                datos = armar(_cargar(tramos, filtrar_cb, d), rng[0], rng[1],
                              tramos, ancla)
            if datos is not None:
                datos["sello"] = clave
            ss[_K_CACHE] = (clave, datos)
        if datos is None:
            st.info("Sin ventas con hora en el rango elegido.")
            return
        ir = ss.pop(_K_IR, None)
        _PIEZA(key=_K_PIEZA,
               data={**datos, "parte": "horas",
                     "ir": {"item": ir, "n": _dt.datetime.now().timestamp()}
                     if ir else None},
               width="stretch")

    with st.container(border=True, key="ajuste_graf_card_izq_ventas_franjas"):
        st.markdown('<p class="chart-card-hdr vh-tit-franjas">Comparación de '
                    'franjas</p>', unsafe_allow_html=True)
        _PIEZA(key=_K_PIEZA_FRANJAS,
               data={"parte": "franjas", "sello": datos["sello"]},
               width="stretch")
