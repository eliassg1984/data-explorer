"""
graficos.carta_costeada — Recetas y Costos › «Carta costeada» (2026-09-26).

Toda la carta del POS, un producto de venta por fila (INFOREST.TPRODUCTO),
con su % de costo sobre el precio neto de Salón — INCLUIDOS los combos, que
el POS no costea (su `nInsumo` es 0). El costo de un combo lo calcula la
consulta del Sheet `cartacosteada` (→ `cartacosteada.parquet`), en el
servidor y al refrescar, así que abrir la vista no hace ninguna cuenta:

    FIJO                  todo fijo: la suma de sus platos
    ESPERADO 90 DIAS      a elegir, con 10 o más vendidos en 90 días: cada
                          opción pesada por lo que eligieron los clientes
    ESPERADO HISTORICO    igual, con TODO su historial (menos de 10 en 90 d)
    PROMEDIO SIN VENTAS   nunca vendido: el promedio de cada grupo

Siempre con la cantidad de la FICHA (`TCOMBO.nCantidad`) y el costo de HOY
de cada plato (`TPRODUCTO.nInsumo`); el mínimo, el máximo, el promedio y el
costo real de lo servido en 90 días (`CPEDIDO`) viajan en sus columnas. El
porqué de cada decisión, en `arquitectura.md` regla #548.

Dos modos en UNA tarjeta, y no dos tarjetas: la carta completa y la banda de
los combos no entran juntas en una pantalla de laptop, y una tarjeta con
barra propia no va (`CLAUDE.md` § Alturas).

`st.dataframe` y no AgGrid: es una tabla de sólo lectura, y cada AgGrid
cuesta 1,28 MB y más de un segundo de navegador (regla #540).
"""

import numpy as np
import pandas as pd
import streamlit as st

from graficos import alturas
from graficos.base import _resolver
from graficos.recetas_comun import divisor_neto
from graficos.recetaventa import _UMBRAL_COSTO_OK, _UMBRAL_COSTO_WARN
from tema import ADVERTENCIA_TEXTO, ERROR
from utils import _norm

ARCHIVO = "cartacosteada.parquet"

VER = ("Carta completa", "Combos")
TIPOS = ("Todos", "Receta", "Directo", "Combo", "Sin costo")

# `TIPO DESC` de la consulta → cómo se dice en la tabla. Lo que no esté acá
# (el 'VACIO' de un `tDescargo` vacío, o un nulo) es «Sin enlace».
_TIPO = {"RECETA": "Receta", "DIRECTO": "Directo", "COMBO": "Combo",
         "NO APLICA": "No aplica"}

METODOS = {
    "FIJO": "Fijo: suma de sus platos",
    "ESPERADO 90 DIAS": "Esperado · últimos 90 días",
    "ESPERADO HISTORICO": "Esperado · todo su historial",
    "PROMEDIO SIN VENTAS": "Promedio · sin ventas",
}

_PRECIO_CENTINELA = 1.0
"""Un precio de Salón de S/ 1 o menos no es un precio: son cortesías, vales
y No Show con precios «redondos» de mentira, que disparan el % de costo a
millones. El mismo corte que Composición (regla #205)."""


def _num(df, col):
    if not col:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _texto(df, col):
    if not col:
        return pd.Series("", index=df.index, dtype=object)
    return df[col].astype("string").fillna("").str.strip().astype(object)


def preparar(df, incluir_inactivos=False):
    """El parquet → una fila por producto con lo que muestra la vista.

    Devuelve `(carta, n_sin_precio)`: `carta` trae Grupo, Subgrupo,
    Producto, Tipo, Precio, Neto, Costo, Pct (en %, 0 si no hay costo),
    SinCosto, UltimaVenta y, para los combos, Metodo y la banda (Minimo,
    Promedio, Esperado, Maximo, Real90, Vendidos90). Pura: sin Streamlit."""
    c = {n: _resolver(df, [n]) for n in (
        "GRUPO", "SUBGRUPO", "COD PLATO", "ITEM VENT", "ITEM VENT ACT",
        "P.VENTA SALON", "COSTO SALON", "TIPO DESC", "TIPO COMBO",
        "METODO COSTO", "COSTO MINIMO", "COSTO MAXIMO", "COSTO PROMEDIO",
        "COSTO ESPERADO", "COSTO REAL 90 DIAS", "COMBOS VENDIDOS 90 DIAS",
        "ULTIMA VENT")}
    d = df
    if not incluir_inactivos and c["ITEM VENT ACT"]:
        d = d[_texto(d, c["ITEM VENT ACT"]).str.upper() == "ACTIV"]
    precio = _num(d, c["P.VENTA SALON"])
    n_sin_precio = int((precio.fillna(0) <= _PRECIO_CENTINELA).sum())
    d = d[precio > _PRECIO_CENTINELA]
    precio = precio[precio > _PRECIO_CENTINELA]

    t = pd.DataFrame(index=d.index)
    t["Cod"] = _texto(d, c["COD PLATO"])
    t["Grupo"] = _texto(d, c["GRUPO"])
    t["Subgrupo"] = _texto(d, c["SUBGRUPO"])
    t["Producto"] = _texto(d, c["ITEM VENT"])
    es_combo = _texto(d, c["TIPO COMBO"]) != ""
    tipo = _texto(d, c["TIPO DESC"]).str.upper().map(_TIPO).fillna("Sin enlace")
    t["Tipo"] = tipo.where(~es_combo, "Combo")
    t["Precio"] = precio.astype(float)
    # El neto como lo calcula el sistema (÷ 1,235 hoy), el MISMO divisor de
    # Composición y Nueva receta (`recetas_comun.divisor_neto`, regla #514).
    # El % se recalcula acá con él y no se lee de `%COSTO SALON`: así
    # «P. neto», «Costo» y «% costo» de una fila cuadran entre sí siempre.
    t["Neto"] = t["Precio"] / divisor_neto()
    costo = _num(d, c["COSTO SALON"])
    t["SinCosto"] = costo.isna() | (costo <= 0)
    t["Costo"] = costo.where(~t["SinCosto"], 0.0).astype(float)
    # Sin costo cargado va 0 y se escribe «—»: un vacío en `st.dataframe`
    # se pinta «None» aunque el Styler diga otra cosa (regla #529).
    t["Pct"] = (t["Costo"] / t["Neto"] * 100).where(~t["SinCosto"], 0.0)

    t["Metodo"] = _texto(d, c["METODO COSTO"]).str.upper().map(METODOS).fillna("")
    t["TipoCombo"] = _texto(d, c["TIPO COMBO"]).str.upper().map(
        {"TODO FIJO": "Todo fijo", "A ELEGIR": "A elegir"}).fillna("")
    for nuevo, col in (("Minimo", "COSTO MINIMO"), ("Promedio", "COSTO PROMEDIO"),
                       ("Esperado", "COSTO ESPERADO"), ("Maximo", "COSTO MAXIMO"),
                       ("Real90", "COSTO REAL 90 DIAS"),
                       ("Vendidos90", "COMBOS VENDIDOS 90 DIAS")):
        t[nuevo] = _num(d, c[col]).fillna(0.0).astype(float)

    uv = pd.to_datetime(d[c["ULTIMA VENT"]], errors="coerce") if c["ULTIMA VENT"] \
        else pd.Series(pd.NaT, index=d.index)
    # Por si el parquet trae todavía el 01/01/1900 de un ISNULL(fecha, ''):
    # la consulta nueva ya lo manda vacío, pero un parquet viejo no.
    uv = uv.where(uv >= pd.Timestamp("2000-01-01"))
    t["UltimaVenta"] = uv.dt.strftime("%d/%m/%Y").fillna("")
    t = t.sort_values(["Pct", "Producto"], ascending=[False, True])
    return t.reset_index(drop=True), n_sin_precio


def filtrar(t, grupo="Todos", tipo="Todos", buscar=""):
    """Los tres filtros de la fila de controles. Pura."""
    if grupo and grupo != "Todos":
        t = t[t["Grupo"] == grupo]
    if tipo == "Sin costo":
        t = t[t["SinCosto"]]
    elif tipo and tipo != "Todos":
        t = t[t["Tipo"] == tipo]
    q = _norm(buscar or "").strip()
    if q:
        t = t[t["Producto"].map(_norm).str.contains(q, regex=False)]
    return t


def resumen(t, que="productos"):
    """La línea de números de arriba de la tabla (`que`: cómo se llaman las
    filas — «productos» en la carta, «combos» en su modo). El % de costo va en
    MEDIANA y no en promedio: con precios de S/ 3 al lado de S/ 400, un
    promedio de porcentajes lo mueven los baratos (la #199: un ratio no se
    promedia)."""
    if t.empty:
        return "Sin productos con este filtro."
    con = t[~t["SinCosto"]]
    partes = [f"**{len(t):,}** {que}"]
    if len(con):
        partes.append(f"% de costo mediano **{con['Pct'].median():.1f} %**")
        n_alto = int((con["Pct"] > _UMBRAL_COSTO_WARN).sum())
        partes.append(f"**{n_alto}** sobre {_UMBRAL_COSTO_WARN} %")
    n_sin = int(t["SinCosto"].sum())
    if n_sin:
        partes.append(f"**{n_sin}** sin costo cargado")
    n_combo = int((t["Tipo"] == "Combo").sum())
    if n_combo and que != "combos":
        partes.append(f"**{n_combo}** combos")
    return " · ".join(partes)


def _estilo_pct(v):
    """El semáforo de Composición (30 / 35 %), en el color del texto."""
    if not v:
        return ""
    if v > _UMBRAL_COSTO_WARN:
        return f"color: {ERROR}; font-weight: 700"
    if v > _UMBRAL_COSTO_OK:
        return f"color: {ADVERTENCIA_TEXTO}; font-weight: 600"
    return ""


def _soles(v):
    return f"S/ {v:,.2f}" if v else "—"


def _pct(v):
    return f"{v:.1f} %" if v else "—"


def _alto(n_filas):
    """El alto de la tabla: el de sus filas hasta el tope de
    `alturas.CARTA_COSTEADA`. Con cinco combos, una tabla de doce filas era
    media tarjeta de filas vacías. Filas de 27 y una cabecera de 35 más los
    bordes (medido: con la cabecera contada como una fila más, a la última
    le faltaban 7px y salía cortada)."""
    return alturas.por_filas(n_filas, px_fila=27, extra=38, minimo=0,
                             rol=alturas.CARTA_COSTEADA)


def _tabla_carta(t):
    v = t[["Grupo", "Subgrupo", "Producto", "Pct", "Precio", "Neto", "Costo",
           "Tipo", "UltimaVenta"]].rename(columns={
               "Pct": "% costo", "Precio": "P. venta", "Neto": "P. neto",
               "UltimaVenta": "Última venta"})
    sty = (v.style
           .format(_pct, subset=["% costo"])
           .format(_soles, subset=["P. venta", "P. neto", "Costo"])
           .map(_estilo_pct, subset=["% costo"]))
    cfg = {
        "Producto": st.column_config.TextColumn(pinned=True, width=220),
        "Grupo": st.column_config.TextColumn(width=120),
        "Subgrupo": st.column_config.TextColumn(width=130),
        "% costo": st.column_config.Column(
            width=72, help="Costo ÷ precio neto de Salón (sin IGV ni recargo). "
                           "«—»: sin costo cargado en el POS."),
        "P. venta": st.column_config.Column(width=82, help="Precio de Salón, con impuestos"),
        "P. neto": st.column_config.Column(width=82, help="Precio de Salón ÷ 1,235, como el sistema"),
        "Costo": st.column_config.Column(
            width=82, help="Costo de hoy. En un combo, el que calcula la consulta: "
                           "mirá «Combos» para ver cómo."),
        "Tipo": st.column_config.TextColumn(
            width=90, help="Con qué descarga del almacén: receta, artículo directo, "
                           "combo, no aplica o sin enlace"),
        "Última venta": st.column_config.TextColumn(width=96),
    }
    st.dataframe(sty, key="rec_carta_tabla", hide_index=True, row_height=27,
                 height=_alto(len(v)), column_config=cfg)


def _tabla_combos(t):
    v = t[["Producto", "TipoCombo", "Metodo", "Costo", "Pct", "Minimo",
           "Promedio", "Esperado", "Maximo", "Real90", "Vendidos90"]].rename(
        columns={"Producto": "Combo", "TipoCombo": "Tipo",
                 "Metodo": "Cómo se costeó", "Costo": "Costo usado",
                 "Pct": "% costo", "Minimo": "Mínimo", "Maximo": "Máximo",
                 "Real90": "Real 90 días", "Vendidos90": "Vendidos 90 días"})
    montos = ["Costo usado", "Mínimo", "Promedio", "Esperado", "Máximo",
              "Real 90 días"]
    sty = (v.style
           .format(_pct, subset=["% costo"])
           .format(_soles, subset=montos)
           .format(lambda x: f"{x:,.0f}" if x else "—", subset=["Vendidos 90 días"])
           .map(_estilo_pct, subset=["% costo"]))
    cfg = {
        "Combo": st.column_config.TextColumn(pinned=True, width=210),
        "Tipo": st.column_config.TextColumn(width=78),
        "Cómo se costeó": st.column_config.TextColumn(width=186),
        "Costo usado": st.column_config.Column(
            width=84, help="El que usa el % de costo y la carta completa"),
        "% costo": st.column_config.Column(width=66),
        "Mínimo": st.column_config.Column(
            width=76, help="Los fijos + la opción más barata de cada grupo"),
        "Promedio": st.column_config.Column(
            width=76, help="Los fijos + el promedio de las opciones de cada grupo"),
        "Esperado": st.column_config.Column(
            width=76, help="Los fijos + cada opción pesada por lo que eligieron "
                           "los clientes. «—»: nunca se vendió"),
        "Máximo": st.column_config.Column(
            width=76, help="Los fijos + la opción más cara de cada grupo"),
        "Real 90 días": st.column_config.Column(
            width=84, help="Lo que costó de verdad lo servido en los últimos 90 "
                           "días, con el costo de cada día (CPEDIDO)"),
        "Vendidos 90 días": st.column_config.Column(width=104),
    }
    st.dataframe(sty, key="rec_carta_combos", hide_index=True, row_height=27,
                 height=_alto(len(v)), column_config=cfg)


def render_carta_costeada(df):
    """La tarjeta de la vista. `df` es `cartacosteada.parquet` entero (o
    None si no se pudo cargar)."""
    st.markdown('<p class="chart-card-hdr">Carta costeada · % de costo sobre '
                'el precio neto de Salón, combos incluidos</p>',
                unsafe_allow_html=True)
    if df is None or df.empty:
        st.info("Todavía no hay datos de la carta costeada "
                f"({ARCHIVO}). Se genera con la consulta «cartacosteada» del "
                "Sheet: aparece después del próximo refresco.")
        return

    ss = st.session_state
    inactivos = bool(ss.get("rec_carta_inactivos", False))
    carta, n_sin_precio = preparar(df, incluir_inactivos=inactivos)
    grupos = ["Todos"] + sorted(g for g in carta["Grupo"].unique() if g)

    # columnas-internas: la fila de controles de la tarjeta (qué ver, grupo,
    # tipo, buscador e inactivos); no parte la página en dos.
    c_ver, c_grupo, c_tipo, c_buscar, c_inact = st.columns(
        [1.5, 1.3, 1.1, 1.6, 1.0], vertical_alignment="center")
    with c_ver:
        ver = st.segmented_control("Ver", VER, default=VER[0],
                                   key="rec_carta_ver",
                                   label_visibility="collapsed") or VER[0]
    with c_grupo:
        if ss.get("rec_carta_grupo") not in grupos:
            ss["rec_carta_grupo"] = "Todos"
        grupo = st.selectbox("Grupo", grupos, key="rec_carta_grupo",
                             label_visibility="collapsed")
    with c_tipo:
        # En «Combos» el tipo ya está elegido: se apaga en vez de esconderse,
        # para no perder lo elegido al volver (un widget que no se dibuja
        # pierde su estado).
        tipo = st.selectbox("Tipo", TIPOS, key="rec_carta_tipo",
                            label_visibility="collapsed",
                            disabled=(ver == "Combos"))
    with c_buscar:
        buscar = st.text_input("Buscar", key="rec_carta_buscar",
                               placeholder="Buscar producto",
                               label_visibility="collapsed")
    with c_inact:
        st.toggle("Inactivos", key="rec_carta_inactivos",
                  help="Sumar los productos que el POS tiene inactivos")

    if ver == "Combos":
        t = filtrar(carta, grupo, "Combo", buscar)
        st.markdown(resumen(t, "combos"))
        if t.empty:
            st.info("No hay combos con este filtro.")
            return
        _tabla_combos(t)
        st.caption(
            "Todo con la cantidad de la ficha y el costo de HOY de cada plato. "
            "Esperado: cada opción pesada por lo que eligieron los clientes — "
            "en 90 días si hubo 10 o más vendidos, si no con todo su historial; "
            "un grupo sin elecciones cuenta su promedio. Real: lo servido en 90 "
            "días, al costo de cada día.")
        return

    t = filtrar(carta, grupo, tipo, buscar)
    st.markdown(resumen(t))
    if t.empty:
        st.info("Ningún producto con este filtro.")
        return
    _tabla_carta(t)
    pie = (f"Ordenada por % de costo. Semáforo: sobre {_UMBRAL_COSTO_OK} % en "
           f"ámbar, sobre {_UMBRAL_COSTO_WARN} % en rojo.")
    if n_sin_precio:
        pie += (f" {n_sin_precio} sin precio de Salón (S/ 1 o menos) no se "
                "muestran.")
    st.caption(pie)
