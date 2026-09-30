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

DESDE EL 2026-09-28 ES LA ÚNICA VISTA DE LA CARTA (regla #556). Absorbió a
«Composición del plato», cuya tabla era ésta misma filtrada a los platos con
receta (425 de 425 con el mismo precio, costo y %): un clic en un producto
abre su receta con el simulador, la dona Costo/Utilidad y el Sankey
(`graficos/recetaventa.py`) — AL COSTADO de la tabla desde el 2026-09-29
(regla #570), y debajo hasta ese día. Y «Costeo Receta Venta», que sumaba el mismo
costo por plato sin descartar los inactivos, se quitó. La regla que ordena
las dos mitades:

    esta vista = la carta de HOY    receta × precio de hoy, precio de lista
    Ventas     = lo que PASÓ        el costo con que se vendió cada plato

De Ventas trae sólo lo que hace falta para decidir sobre la carta —cuánto
se vendió en 90 días y a qué % de costo—, con la definición de venta de
siempre (`data.venta_por_producto_dia`, que llama a `definicion_venta`) y
el `pct_costo` del Mix importado: una cifra de Ventas se ve igual acá.

Dos modos en UNA tarjeta, y no dos tarjetas: la carta completa y la banda de
los combos no entran juntas en una pantalla de laptop, y una tarjeta con
barra propia no va (`CLAUDE.md` § Alturas).

UNA tarjeta blanca, como las de los otros reportes, con la tabla a la
izquierda y el producto elegido a la derecha (regla #570). Para que el
producto quepa al costado, la tabla muestra por defecto sólo lo que la
identifica y lo que cuesta —Grupo, Subgrupo, Producto, % de costo y los
tres montos— y el interruptor «Más columnas» suma Margen, Vendidos, Tipo,
Actualizado y Última venta; con ellas la tabla se desliza de costado, con
las tres primeras fijas.

`st.dataframe` y no AgGrid: es una tabla de sólo lectura, y cada AgGrid
cuesta 1,28 MB y más de un segundo de navegador (regla #540). Composición
usaba AgGrid sólo para el clic en una fila; `st.dataframe` lo hace con
`selection_mode="single-row-required"` (ver `_key_tabla`).
"""

import hashlib
import math
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cortes import MESES_ABR_ES
from graficos import alturas
from graficos.base import _card, _compras_layout, _es_movil, _resolver
from graficos.recetas_comun import divisor_neto
from graficos.recetaventa import (
    _dib_sankey_insumo_costo, _dib_torta_costo_utilidad, receta_del_plato,
)
from graficos.ventas_mix import pct_costo
from tema import (ACENTO, ADVERTENCIA, ADVERTENCIA_TEXTO, ERROR, GRIS_TEXTO,
                  LAVANDA_FONDO)
from utils import _norm

ARCHIVO = "cartacosteada.parquet"

VER = ("Carta completa", "Combos")
VER_OFERTA = ("Completa", "Impresa", "No impresa", "Combos")
"""Las opciones de «Ver» cuando la consulta trae «Tipo de Oferta» (regla
#571): la carta entera, la impresa, la que no y los combos. Sin la columna
—un parquet de antes de la regla— quedan las dos de siempre. «Carta» se cae
del rótulo porque ya lo dice el título de la tarjeta, y con él las cuatro
no entraban en la fila de controles a 1366px (medido: 362px sin él)."""

OFERTAS = {"Impresa": "Carta impresa", "No impresa": "Carta no impresa"}
"""Opción de «Ver» → valor de «Tipo de Oferta» que filtra."""
TIPOS = ("Todos", "Receta", "Directo", "Combo", "Sin enlace", "No aplica",
         "Sin costo")

# `TIPO DESC` de la consulta → cómo se dice en la tabla. Lo que no esté acá
# (el 'SIN ENLACE' o 'VACIO' de un `tDescargo` vacío, o un nulo) es «Sin
# enlace».
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
millones. El mismo corte que tenía Composición (regla #205)."""

# El semáforo del % de costo: el mismo criterio que `formulario_receta.py`
# usa para juzgar una receta nueva (🟢/🟠/🔴). Vivía en `recetaventa.py`,
# para la barra de la tabla de Composición, hasta que esa tabla se fue.
_UMBRAL_COSTO_OK = 30
_UMBRAL_COSTO_WARN = 35

GRUPO_VENTA_INTERNA = "Venta Interna"
"""Los productos «(Cst)»: 22 que se venden a precio de costo, y 17 de los
18 que pasan el 100 % (medido el 2026-09-28). Arrancan fuera, con un
interruptor, a pedido: encabezaban la tabla sin decir nada de la carta."""

DIAS_VENDIDOS = 90
"""La ventana de «Vendidos»: 90 días hasta el último día con venta."""

MIN_VENDIDOS = 10
"""Cuántas ventas en la ventana hacen que un % alto importe (el resumen)."""

_SIN_FECHA = pd.Timestamp("1900-01-01")
"""Una fecha que falta. `st.dataframe` pinta «None» en un vacío aunque el
Styler diga otra cosa (regla #529), así que va esta y se escribe «—»: la
columna sigue siendo de fechas, y ordenar por ella ordena por fecha."""

_K_FOCO = "rec_carta_foco"
"""El código del producto elegido. Sólo lo escribe un clic: sin clic, o
con el elegido fuera del filtro, el panel sigue a la primera fila."""

_K_MAS = "rec_carta_mas_cols"
"""El interruptor «Más columnas» (regla #570): arranca apagado."""

PROPORCION = (0.635, 0.365)
"""Tabla | producto elegido. Con las columnas de siempre la tabla mide
736px (38 de la casilla de selección, 696 de columnas y el borde) y a
1366×768 con la columna del rail plegada le tocan ~750: el panel se queda
con ~430, lo que ya tenía la dona al lado de la receta."""


def _num(df, col):
    if not col:
        return pd.Series(np.nan, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _texto(df, col):
    if not col:
        return pd.Series("", index=df.index, dtype=object)
    return df[col].astype("string").fillna("").str.strip().astype(object)


def _fecha(serie):
    """Fechas limpias: el 01/01/1900 de un `ISNULL(fecha, '')` viejo y lo que
    no se entiende pasan a `_SIN_FECHA`."""
    f = pd.to_datetime(serie, errors="coerce")
    return f.where(f >= pd.Timestamp("2000-01-01"), _SIN_FECHA).fillna(_SIN_FECHA)


def preparar(df, incluir_inactivos=False):
    """El parquet → una fila por producto con lo que muestra la vista.

    Devuelve `(carta, n_sin_precio)`: `carta` trae Cod, Grupo, Subgrupo,
    Producto, Tipo, Precio, Neto, Costo, Pct (en %, 0 si no hay costo),
    Margen (neto − costo, 0 sin costo), SinCosto, Descarga (qué artículo o
    receta descarga), UltimaVenta (fecha, `_SIN_FECHA` si nunca) y, para
    los combos, Metodo y la banda (Minimo, Promedio, Esperado, Maximo,
    Real90, Vendidos90). Pura: sin Streamlit."""
    c = {n: _resolver(df, [n]) for n in (
        "GRUPO", "SUBGRUPO", "COD PLATO", "ITEM VENT", "ITEM VENT ACT",
        "P.VENTA SALON", "COSTO SALON", "TIPO DESC", "NOMB DESC", "TIPO COMBO",
        "METODO COSTO", "COSTO MINIMO", "COSTO MAXIMO", "COSTO PROMEDIO",
        "COSTO ESPERADO", "COSTO REAL 90 DIAS", "COMBOS VENDIDOS 90 DIAS",
        "ULTIMA VENT")}
    # «Tipo de Oferta» (regla #571): la consulta del Sheet la arma con
    # `INFOREST.DBO.TPRODUCTO.nBoton` —del 1 al 19, «Carta impresa»; 0 o
    # vacío, «Carta no impresa»—. Es un atributo del PRODUCTO, y por eso vive
    # en esta consulta, una fila por producto, y no en la de ventas.
    c["OFERTA"] = _resolver(df, ["Tipo de Oferta", "TIPO OFERTA"])
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
    t["Descarga"] = _texto(d, c["NOMB DESC"])
    t["Precio"] = precio.astype(float)
    # El neto como lo calcula el sistema (÷ 1,235 hoy), el MISMO divisor de
    # Nueva receta (`recetas_comun.divisor_neto`, regla #514). El % se
    # recalcula acá con él y no se lee de `%COSTO SALON`: así «P. neto»,
    # «Costo», «Margen» y «% costo» de una fila cuadran entre sí siempre.
    t["Neto"] = t["Precio"] / divisor_neto()
    costo = _num(d, c["COSTO SALON"])
    t["SinCosto"] = costo.isna() | (costo <= 0)
    t["Costo"] = costo.where(~t["SinCosto"], 0.0).astype(float)
    # Sin costo cargado va 0 y se escribe «—»: un vacío en `st.dataframe`
    # se pinta «None» aunque el Styler diga otra cosa (regla #529).
    t["Pct"] = (t["Costo"] / t["Neto"] * 100).where(~t["SinCosto"], 0.0)
    # Lo que deja cada unidad: el eje de rentabilidad de la ingeniería de
    # menú (Kasavana y Smith, «Menu Engineering», 1982), el mismo que usa
    # Ventas › Ingeniería de menú. Un 65 % en un vino de S/ 1.700 deja
    # S/ 484; un 16 % en un expreso, S/ 6.
    t["Margen"] = (t["Neto"] - t["Costo"]).where(~t["SinCosto"], 0.0)

    t["Metodo"] = _texto(d, c["METODO COSTO"]).str.upper().map(METODOS).fillna("")
    t["TipoCombo"] = _texto(d, c["TIPO COMBO"]).str.upper().map(
        {"TODO FIJO": "Todo fijo", "A ELEGIR": "A elegir"}).fillna("")
    for nuevo, col in (("Minimo", "COSTO MINIMO"), ("Promedio", "COSTO PROMEDIO"),
                       ("Esperado", "COSTO ESPERADO"), ("Maximo", "COSTO MAXIMO"),
                       ("Real90", "COSTO REAL 90 DIAS"),
                       ("Vendidos90", "COMBOS VENDIDOS 90 DIAS")):
        t[nuevo] = _num(d, c[col]).fillna(0.0).astype(float)

    uv = d[c["ULTIMA VENT"]] if c["ULTIMA VENT"] else pd.Series(pd.NaT, index=d.index)
    # Por si el parquet trae todavía el 01/01/1900 de un ISNULL(fecha, ''):
    # la consulta nueva ya lo manda vacío, pero un parquet viejo no.
    t["UltimaVenta"] = _fecha(uv)
    # Vacío sin la columna, o con un nBoton fuera de 0-19 (la consulta lo
    # deja nulo a propósito, para que se note).
    t["Oferta"] = _texto(d, c["OFERTA"]).str.upper().map(
        {v.upper(): v for v in OFERTAS.values()}).fillna("")
    t = t.sort_values(["Pct", "Producto"], ascending=[False, True])
    return t.reset_index(drop=True), n_sin_precio


def fechas_de_receta(df_rv):
    """{COD PLATO: última modificación de su receta} de recetaventa.parquet.

    `FECH MODIF` es un atributo del PLATO repetido en cada insumo (un valor
    por `COD PLATO` en los 850, regla #253). Es la columna «Actualizado»
    que tenía Composición: la que delata una receta que nadie revisa (59
    platos activos sin tocar desde 2024 o antes, 26 desde 2022)."""
    if df_rv is None or df_rv.empty:
        return {}
    c_cod = _resolver(df_rv, ["COD PLATO", "Cod Plato"])
    c_fm = _resolver(df_rv, ["FECH MODIF", "Fech Modif", "Fecha Modif"])
    if not (c_cod and c_fm):
        return {}
    f = pd.to_datetime(df_rv[c_fm], errors="coerce")
    s = pd.Series(f.to_numpy(), index=df_rv[c_cod].astype(str).str.strip())
    s = s[~s.index.duplicated()].dropna()
    return s.to_dict()


def con_ventas(t, agg, dias=DIAS_VENDIDOS):
    """`t` con lo vendido de cada producto en los últimos `dias` días del
    resumen de Ventas (`definicion_venta.por_producto_dia`): Vendidos
    (unidades), VendidoNeto, SinCostoNeto (lo vendido sin costo) y
    PctVendido (costo ÷ neto de lo vendido, en %; 0 si no hay costo o no se
    vendió, que se escribe «—»).

    La ventana termina en el último día con venta del resumen, no hoy: el
    parquet llega de la madrugada. Devuelve `(t, (ini, fin))`, o
    `(t, None)` sin resumen. Pura."""
    t = t.copy()
    if agg is None or agg.empty:
        for col in ("Vendidos", "VendidoNeto", "SinCostoNeto", "PctVendido"):
            t[col] = 0.0
        return t, None
    dia = pd.to_datetime(agg["dia"])
    fin = dia.max().normalize()
    ini = fin - pd.Timedelta(days=dias - 1)
    u = agg[dia >= ini]
    s = u.groupby("producto")[["unidades", "neto", "costo",
                               "neto_sin_costo"]].sum()
    s.index = s.index.astype(str).str.strip()
    cod = t["Cod"].astype(str)
    t["Vendidos"] = cod.map(s["unidades"]).fillna(0.0).astype(float)
    t["VendidoNeto"] = cod.map(s["neto"]).fillna(0.0).astype(float)
    t["SinCostoNeto"] = cod.map(s["neto_sin_costo"]).fillna(0.0).astype(float)
    # `pct_costo` del Mix: NaN sin costo o con un neto de centavos (#547).
    pv = pct_costo(cod.map(s["costo"]).fillna(0.0), t["VendidoNeto"]) * 100
    t["PctVendido"] = pv.fillna(0.0).astype(float)
    return t, (ini.date(), fin.date())


def filtrar(t, grupo="Todos", tipo="Todos", buscar="", venta_interna=False,
            oferta=None):
    """Los filtros de la fila de controles. `venta_interna`: si entran los
    productos del grupo Venta Interna (arrancan fuera); `oferta`: «Carta
    impresa» o «Carta no impresa», o None para toda la carta. Pura."""
    if oferta:
        t = t[t["Oferta"] == oferta]
    if not venta_interna:
        t = t[t["Grupo"].str.casefold() != GRUPO_VENTA_INTERNA.casefold()]
    if grupo and grupo != "Todos":
        t = t[t["Grupo"] == grupo]
    if tipo == "Sin costo":
        t = t[t["SinCosto"]]
        # Sin costo no hay % por el que ordenar: arriba, lo que MÁS se
        # vende — es la lista para corregir en el POS (las aguas Munay,
        # 2.474 unidades sin costo en 90 días al 2026-09-28).
        if "Vendidos" in t.columns:
            t = t.sort_values(["Vendidos", "Producto"], ascending=[False, True])
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
    promedia). Con lo vendido a mano, dice cuántos de los caros y de los sin
    costo se VENDEN: de los que pasan el 35 %, la mitad no se vendió en 90
    días."""
    if t.empty:
        return "Sin productos con este filtro."
    vende = "Vendidos" in t.columns
    con = t[~t["SinCosto"]]
    partes = [f"**{len(t):,}** {que[:-1] if len(t) == 1 else que}"]
    if len(con):
        partes.append(f"% de costo mediano **{con['Pct'].median():.1f} %**")
        alto = con[con["Pct"] > _UMBRAL_COSTO_WARN]
        texto = f"**{len(alto)}** sobre {_UMBRAL_COSTO_WARN} %"
        if vende and len(alto):
            n = int((alto["Vendidos"] >= MIN_VENDIDOS).sum())
            texto += f" (**{n}** con {MIN_VENDIDOS} o más ventas en {DIAS_VENDIDOS} días)"
        partes.append(texto)
    n_sin = int(t["SinCosto"].sum())
    if n_sin:
        texto = f"**{n_sin}** sin costo cargado"
        if vende:
            n = int((t["SinCosto"] & (t["Vendidos"] > 0)).sum())
            if n:
                texto += f" (**{n}** se venden)"
        partes.append(texto)
    if "Oferta" in t.columns and que != "combos":
        n_imp = int((t["Oferta"] == OFERTAS["Impresa"]).sum())
        if 0 < n_imp < len(t):
            partes.append(f"**{n_imp}** en la carta impresa")
    n_combo = int((t["Tipo"] == "Combo").sum())
    if n_combo and que != "combos":
        partes.append(f"**{n_combo}** combos")
    return " · ".join(partes)


def _estilo_pct(v):
    """El semáforo (30 / 35 %), en el color del texto."""
    if not v:
        return ""
    if v > _UMBRAL_COSTO_WARN:
        return f"color: {ERROR}; font-weight: 700"
    if v > _UMBRAL_COSTO_OK:
        return f"color: {ADVERTENCIA_TEXTO}; font-weight: 600"
    return ""


def _estilo_margen(v):
    return f"color: {ERROR}; font-weight: 700" if v < 0 else ""


def _soles(v):
    if not v:
        return "—"
    return f"S/ {v:,.2f}" if v > 0 else f"−S/ {abs(v):,.2f}"


def _pct(v):
    return f"{v:.1f} %" if v else "—"


def _unidades(v):
    return f"{v:,.0f}" if v else "—"


def _dia(v):
    if pd.isna(v) or v <= _SIN_FECHA:
        return "—"
    return v.strftime("%d/%m/%Y")


def _alto(n_filas):
    """El alto de la tabla: el de sus filas hasta el tope de
    `alturas.CARTA_COSTEADA`. Con cinco combos, una tabla de doce filas era
    media tarjeta de filas vacías. Filas de 27 y una cabecera de 35 más los
    bordes (medido: con la cabecera contada como una fila más, a la última
    le faltaban 7px y salía cortada)."""
    return alturas.por_filas(n_filas, px_fila=27, extra=38, minimo=0,
                             rol=alturas.CARTA_COSTEADA)


# ─── La fila elegida ───────────────────────────────────────────────────────
# La selección es un ESTADO («este es el producto en foco»), no un evento:
# releerla en cada corrida da lo mismo, así que no hace falta el contador en
# la key de «Análisis de platos» (regla #399), que estrena la tabla con cada
# clic y con eso le borraba al usuario el orden que había elegido en ella
# (medido: ordenada por «Actualizado», un clic la devolvía al % de costo).
#
# Lo que sí hay que cuidar: Streamlit identifica la tabla SÓLO por su key
# (`key_as_main_identity` en `elements/arrow.py`), no por sus datos, así que
# con otro filtro la fila 3 seguiría elegida y sería otro producto. Por eso
# la key lleva la FIRMA de la lista de códigos: mientras la lista no cambie
# (clics, orden por cabecera) la tabla es la misma; si cambia, es otra, y
# `selection_default` la estrena con el producto en foco marcado.
# `single-row-required`: siempre hay uno elegido, el que muestra el panel.
def _key_tabla(base, codigos):
    firma = hashlib.md5("|".join(codigos).encode("utf-8")).hexdigest()[:12]
    return f"{base}_{firma}"


def _fila_elegida(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _leer_eleccion(base):
    """El producto que la tabla `base` tenía elegido en la corrida anterior,
    al foco. Se lee ANTES de dibujar: la tabla nueva sale con él marcado."""
    ss = st.session_state
    key = ss.get(f"_{base}_key")
    codigos = ss.get(f"_{base}_codigos") or []
    fila = _fila_elegida(ss.get(key)) if key else None
    if fila is not None and 0 <= fila < len(codigos):
        ss[_K_FOCO] = codigos[fila]


def _dibujar_tabla(base, sty, pos_foco, codigos, alto, cfg):
    ss = st.session_state
    key = _key_tabla(base, codigos)
    ss[f"_{base}_key"] = key
    ss[f"_{base}_codigos"] = codigos
    st.dataframe(sty, key=key, on_select="rerun",
                 selection_mode="single-row-required",
                 selection_default={"selection": {"rows": [pos_foco]}},
                 hide_index=True, row_height=27, height=alto,
                 column_config=cfg)


def _pintar_foco(pos):
    """La fila elegida, con fondo lavanda: la marca nativa de la selección es
    una casilla chica a la izquierda, y el panel queda debajo de la tabla."""
    def _fila(r):
        return [f"background-color: {LAVANDA_FONDO}" if r.name == pos else ""
                ] * len(r)
    return _fila


def columnas_carta(mas=False, con_ventas_=True, movil=False):
    """Las columnas de la tabla de la carta, en orden (regla #570). Primero
    lo que ubica al producto —Grupo, Subgrupo y su nombre—, después lo que
    cuesta. `mas`: el interruptor «Más columnas», que suma Margen y Vendidos
    junto al % y Tipo y las dos fechas al final. `movil`: en un teléfono la
    tabla no entra nunca entera y el nombre va PRIMERO, que es como se sabe
    qué fila es (con Grupo y Subgrupo delante, en 306px no se veía). Pura."""
    cols = ["Grupo", "Subgrupo", "Producto", "Pct"]
    if movil:
        cols = ["Producto", "Grupo", "Subgrupo", "Pct"]
    if mas:
        cols.append("Margen")
        if con_ventas_:
            cols.append("Vendidos")
    cols += ["Precio", "Neto", "Costo"]
    if mas:
        cols += ["Tipo", "Actualizado", "UltimaVenta"]
    return cols


def _tabla_carta(t, pos_foco, rango, mas=False):
    movil = _es_movil()
    cols = columnas_carta(mas, rango is not None, movil)
    col_vend = f"Vendidos {DIAS_VENDIDOS} d"
    v = t[cols].rename(columns={
        "Pct": "% costo", "Precio": "P. venta", "Neto": "P. neto",
        "UltimaVenta": "Última venta", "Vendidos": col_vend})
    sty = (v.style
           .format(_pct, subset=["% costo"])
           .format(_soles, subset=[c for c in ("P. venta", "P. neto", "Costo",
                                               "Margen") if c in v.columns])
           .map(_estilo_pct, subset=["% costo"])
           .apply(_pintar_foco(pos_foco), axis=1))
    if "Margen" in v.columns:
        sty = sty.map(_estilo_margen, subset=["Margen"])
    if "Actualizado" in v.columns:
        sty = sty.format(_dia, subset=["Actualizado", "Última venta"])
    if col_vend in v.columns:
        sty = sty.format(_unidades, subset=[col_vend])
    # Con «Más columnas» la tabla no entra en su mitad y se desliza de
    # costado: las tres que dicen QUÉ producto es quedan fijas. Fijas SÓLO
    # entonces: Streamlit lleva las fijas a la izquierda —fijar sólo el
    # nombre lo pondría delante del grupo— y las pinta en gris. En el
    # teléfono, sólo el nombre, que ya va primero: las tres no entran.
    fija = bool(mas) and not movil
    vendidos_help = (f"Unidades vendidas en los últimos {DIAS_VENDIDOS} días "
                     "hasta el último día con venta")
    if rango is not None:
        vendidos_help += f": del {rango[0]:%d/%m/%Y} al {rango[1]:%d/%m/%Y}"
    cfg = {
        "Grupo": st.column_config.TextColumn(pinned=fija, width=100),
        "Subgrupo": st.column_config.TextColumn(pinned=fija, width=114),
        "Producto": st.column_config.TextColumn(pinned=fija or movil, width=190),
        "% costo": st.column_config.Column(
            width=64, help="Costo ÷ precio neto de Salón (sin IGV ni recargo). "
                           "«—»: sin costo cargado en el POS."),
        "Margen": st.column_config.Column(
            width=78, help="Lo que deja cada unidad: precio neto − costo"),
        col_vend: st.column_config.Column(
            width=100, help=vendidos_help + ". Con la definición de venta de "
                                           "Ventas; el dato llega de madrugada."),
        "P. venta": st.column_config.Column(width=76, help="Precio de Salón, con impuestos"),
        "P. neto": st.column_config.Column(width=76, help="Precio de Salón ÷ 1,235, como el sistema"),
        "Costo": st.column_config.Column(
            width=76, help="Costo de hoy. En un combo, el que calcula la consulta: "
                           "mirá «Combos» para ver cómo."),
        "Tipo": st.column_config.TextColumn(
            width=82, help="Con qué descarga del almacén: receta, artículo directo, "
                           "combo, no aplica o sin enlace"),
        "Actualizado": st.column_config.Column(
            width=88, help="Última modificación de la receta en el POS"),
        "Última venta": st.column_config.Column(width=88),
    }
    _dibujar_tabla("rec_carta_tabla", sty, pos_foco, list(t["Cod"]),
                   _alto(len(v)), cfg)


_BANDA = ["Minimo", "Promedio", "Esperado", "Maximo", "Real90", "Vendidos90"]
"""Las columnas de la banda de un combo, que en la tabla suma «Más
columnas»: la banda del combo elegido ya está al costado, en su panel."""


def _tabla_combos(t, pos_foco, mas=False):
    cols = ["Producto", "TipoCombo", "Metodo", "Costo", "Pct"]
    if mas:
        cols += _BANDA
    v = t[cols].rename(
        columns={"Producto": "Combo", "TipoCombo": "Tipo",
                 "Metodo": "Cómo se costeó", "Costo": "Costo usado",
                 "Pct": "% costo", "Minimo": "Mínimo", "Maximo": "Máximo",
                 "Real90": "Real 90 días", "Vendidos90": "Vendidos (consulta)"})
    montos = [c for c in ("Costo usado", "Mínimo", "Promedio", "Esperado",
                          "Máximo", "Real 90 días") if c in v.columns]
    sty = (v.style
           .format(_pct, subset=["% costo"])
           .format(_soles, subset=montos)
           .map(_estilo_pct, subset=["% costo"])
           .apply(_pintar_foco(pos_foco), axis=1))
    if "Vendidos (consulta)" in v.columns:
        sty = sty.format(_unidades, subset=["Vendidos (consulta)"])
    cfg = {
        # Fija sólo con la banda a la vista, como las de la carta: una
        # columna fija se pinta en gris, y sin desliz no hace falta.
        "Combo": st.column_config.TextColumn(pinned=bool(mas), width=210),
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
        # NO es el «Vendidos» de la carta, y por eso se llama distinto: éste
        # lo cuenta la consulta del Sheet al refrescar, en SUS 90 días, para
        # elegir el método; aquél sale de Ventas con la definición de venta
        # y termina en el último día con venta. Medido el 2026-09-28: la
        # Degustación Sapiens, 70 acá y 60 allá.
        "Vendidos (consulta)": st.column_config.Column(
            width=118, help="Los que contó la consulta del Sheet en 90 días "
                            "para elegir el método (10 o más: «Esperado · "
                            "últimos 90 días»). Lo vendido según Ventas está "
                            "en el panel del combo elegido."),
    }
    _dibujar_tabla("rec_carta_combos", sty, pos_foco, list(t["Cod"]),
                   _alto(len(v)), cfg)


# ─── El panel del producto elegido ────────────────────────────────────────
def kpis_producto(f, rango):
    """La línea de números del producto elegido, en markdown. `f` es su fila
    de la carta (con lo vendido, si hay `rango`). Pura."""
    partes = []
    if f["SinCosto"]:
        partes.append("**sin costo** cargado en el POS")
    else:
        partes.append(f"% de carta **{f['Pct']:.1f} %**")
        partes.append(f"margen **{_soles(f['Margen'])}** por unidad")
    if rango is not None:
        n = float(f.get("Vendidos", 0.0))
        if n:
            txt = f"en {DIAS_VENDIDOS} días: **{n:,.0f}** vendidos"
            if f.get("PctVendido", 0.0):
                txt += f", al **{f['PctVendido']:.1f} %** de costo"
            partes.append(txt)
        else:
            partes.append(f"sin ventas en {DIAS_VENDIDOS} días")
    act = f.get("Actualizado", _SIN_FECHA)
    if f["Tipo"] == "Receta" and pd.notna(act) and act > _SIN_FECHA:
        partes.append(f"receta actualizada el **{_dia(act)}**")
    return " · ".join(partes)


def _descarga(f):
    """Lo que va en el lugar de la receta cuando el producto no tiene una."""
    with _card("rec_carta_descarga", "Qué descarga del almacén"):
        if f["Tipo"] == "Directo":
            art = f["Descarga"] or "(sin nombre)"
            st.markdown(f"Se descarga **directo** del almacén: "
                        f"**{escape(art)}**. Su costo es el del artículo.")
            if f["SinCosto"]:
                st.warning("El artículo no tiene costo en el POS: la venta de "
                           "este producto entra al FoodCost en cero.")
        elif f["Tipo"] == "Combo":
            st.markdown(f"**Combo {f['TipoCombo'].lower() or ''}** · "
                        f"{escape(f['Metodo'] or 'sin método')}")
            banda = pd.DataFrame({
                "": ["Mínimo", "Promedio", "Esperado", "Máximo",
                     "Real 90 días"],
                "Costo": [f["Minimo"], f["Promedio"], f["Esperado"],
                          f["Maximo"], f["Real90"]],
            })
            st.dataframe(banda.style.format(_soles, subset=["Costo"]),
                         hide_index=True, row_height=27,
                         height=alturas.por_filas(5, px_fila=27, extra=38,
                                                  minimo=0, rol=alturas.MINI))
            st.caption("El POS no costea los combos: la banda la calcula la "
                       "consulta del Sheet (regla #548).")
        elif f["Tipo"] == "No aplica":
            st.markdown("Su descargo está en **«No aplica»**: el POS no "
                        "descarga nada del almacén al venderlo, así que no "
                        "tiene costo.")
        else:
            st.markdown("**Sin enlace**: no está enlazado a una receta ni a "
                        "un artículo, así que el POS no descarga nada al "
                        "venderlo y no tiene costo.")


# ─── El costo en el tiempo (regla #557) ───────────────────────────────────
# La tercera pestaña del panel: con qué costo se vendió el producto, mes a
# mes. No es otra cuenta del costo: es la FOTO que el POS guarda en cada
# pedido (`DPEDIDO.nInsumo`, o lo servido de `CPEDIDO` en un combo) —la
# receta al precio promedio del almacén de ese momento—, que
# `definicion_venta.por_producto_dia` suma por día. Va en soles por unidad y
# no en %: el IGV de restaurantes pasó de 18 a 10 % a mitad de 2025 y el %
# sobre el neto bajó ~2 puntos sin que cambiara ningún costo.
_COMBO_ANTES = pd.Period("2025-10", freq="M")
"""Hasta setiembre de 2025 el POS registró los platos de un combo con un
costo entre 8 y 32 % menor que el mismo plato suelto el mismo día (medido
el 2026-09-26 contra `CPEDIDO`, sin explicación); desde octubre, igual."""


def costo_mensual(agg, cod):
    """El costo por unidad con que se vendió `cod`, mes a mes: Σ costo ÷ Σ
    unidades que traen costo. Con las unidades, el neto, el neto vendido sin
    costo y el % al que se vendió (el `pct_costo` del Mix) de cada mes. Un mes
    vendido entero sin costo queda con el costo por unidad vacío: sin costo
    no hay costo por unidad que mostrar. Pura."""
    cols = ["mes", "unidades", "neto", "costo", "unidades_costeadas",
            "neto_sin_costo", "costo_unit", "pct"]
    if agg is None or agg.empty:
        return pd.DataFrame(columns=cols)
    a = agg[agg["producto"].astype(str).str.strip() == str(cod).strip()]
    if a.empty:
        return pd.DataFrame(columns=cols)
    a = a.assign(mes=pd.to_datetime(a["dia"]).dt.to_period("M"))
    g = a.groupby("mes", as_index=False)[
        ["unidades", "neto", "costo", "unidades_costeadas",
         "neto_sin_costo"]].sum()
    g = g[(g["unidades"] > 0) | (g["neto_sin_costo"] > 0)]
    g["costo_unit"] = g["costo"] / g["unidades_costeadas"].where(
        g["unidades_costeadas"] > 0)
    g["pct"] = pct_costo(g["costo"], g["neto"]) * 100
    return g.reset_index(drop=True)[cols]


def _etiqueta_mes(p):
    return f"{MESES_ABR_ES[p.month - 1]} {p.year % 100:02d}"


def _dib_costo_en_el_tiempo(f, agg):
    """La línea del costo por unidad al vender y, punteado, el de hoy."""
    g = costo_mensual(agg, f["Cod"])
    if g.empty:
        st.info("No se vendió desde enero de 2025, que es desde cuando hay "
                "ventas en la app: no hay costo al vender que mostrar.")
        return
    etq = [_etiqueta_mes(p) for p in g["mes"]]
    sin = g["neto_sin_costo"] > 0

    def _hover(r):
        partes = [f"<b>{_etiqueta_mes(r['mes'])}</b>"]
        if pd.notna(r["costo_unit"]):
            partes.append(f"S/ {r['costo_unit']:,.2f} por unidad")
        else:
            partes.append("vendido sin costo")
        partes.append(f"{r['unidades']:,.0f} vendidos")
        if pd.notna(r["pct"]):
            partes.append(f"al {r['pct']:.1f} % de costo")
        if r["neto_sin_costo"] > 0:
            partes.append(f"S/ {r['neto_sin_costo']:,.0f} sin costo")
        return "<br>".join(partes)

    fig = go.Figure(go.Scatter(
        x=etq, y=g["costo_unit"], mode="lines+markers", connectgaps=False,
        line=dict(color=ACENTO, width=2),
        # Un mes con algo vendido sin costo va en ámbar: su costo por unidad
        # es el de las unidades que SÍ lo traen, pero en el FoodCost de ese
        # mes hay neto con costo 0 (regla #556).
        marker=dict(size=7, color=[ADVERTENCIA if s else ACENTO for s in sin]),
        text=[_hover(r) for _, r in g.iterrows()],
        hovertemplate="%{text}<extra></extra>"))
    # Los meses vendidos ENTEROS sin costo no tienen punto en la línea: se
    # marcan abajo, para que el hueco diga por qué es un hueco.
    vacios = g["costo_unit"].isna()
    minimo = float(g["costo_unit"].min()) if g["costo_unit"].notna().any() else 0.0
    if vacios.any():
        fig.add_trace(go.Scatter(
            x=[e for e, v in zip(etq, vacios) if v],
            y=[minimo] * int(vacios.sum()), mode="markers",
            marker=dict(symbol="x-thin", size=9, color=ADVERTENCIA,
                        line=dict(width=2, color=ADVERTENCIA)),
            text=[_hover(r) for _, r in g[vacios].iterrows()],
            hovertemplate="%{text}<extra></extra>"))
    if not f["SinCosto"]:
        fig.add_hline(y=float(f["Costo"]), line=dict(color=GRIS_TEXTO, width=1,
                                                     dash="dot"),
                      annotation_text=f"hoy S/ {f['Costo']:,.2f}",
                      annotation_position="top left",
                      annotation_font=dict(size=10, color=GRIS_TEXTO))
    _compras_layout(fig, alto=alturas.MINI)
    # Un rótulo cada tanto: veinte meses en 430px se pisan (y girados comen
    # alto). Categorías SIEMPRE: «ene 25» en un eje sin tipo lo decide
    # Plotly (#448).
    paso = max(1, math.ceil(len(etq) / 7))
    tope = float(np.nanmax([g["costo_unit"].max(), f["Costo"] or 0.0]))
    fig.update_layout(showlegend=False, margin=dict(l=6, r=8, t=20, b=6))
    fig.update_xaxes(type="category", tickangle=0, tickfont=dict(size=10),
                     tickvals=etq[::paso], ticktext=etq[::paso],
                     fixedrange=True)
    fig.update_yaxes(showticklabels=True, tickprefix="S/ ",
                     tickformat=",.2f" if tope < 20 else ",.0f",
                     tickfont=dict(size=10), automargin=True, fixedrange=True,
                     rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True,
                    key=f"rec_carta_tiempo_{f['Cod']}",
                    config={"displaylogo": False, "displayModeBar": False})

    con = g[g["costo_unit"].notna()]
    if len(con) >= 2:
        a, b = con.iloc[0], con.iloc[-1]
        var = (b["costo_unit"] / a["costo_unit"] - 1) * 100 if a["costo_unit"] else 0.0
        st.caption(f"De S/ {a['costo_unit']:,.2f} ({_etiqueta_mes(a['mes'])}) a "
                   f"S/ {b['costo_unit']:,.2f} ({_etiqueta_mes(b['mes'])}): "
                   f"{'+' if var >= 0 else '−'}{abs(var):.1f} %. El costo que "
                   "guardó el POS al vender, por unidad.")
    if vacios.any():
        n = int(vacios.sum())
        st.caption(f"✕ {n} {'mes vendido' if n == 1 else 'meses vendidos'} "
                   "sin costo: no hay costo por unidad que dibujar.")
    if f["Tipo"] == "Combo" and (g["mes"] < _COMBO_ANTES).any():
        st.caption("Hasta setiembre de 2025 el POS registró los platos de los "
                   "combos entre 8 y 32 % más baratos que sueltos: esa parte "
                   "de la línea sale baja.")


def _panel(f, df_rv, rango, ventas=None):
    """Al costado de la tabla (regla #570): el producto elegido, su línea
    de números, su receta (o lo que descarga) y, debajo, la dona / el Sankey
    / su costo en el tiempo. Lo que era la parte de abajo de «Composición»
    (regla #556), más el costo con que se vendió (regla #557).

    La receta y el gráfico van UNO ARRIBA DEL OTRO y no lado a lado, como
    iban cuando el panel ocupaba el ancho entero: en ~440px no entran dos, y
    los dos se leen juntos — el simulador edita la receta y la dona y el
    Sankey siguen al borrador."""
    cod, nombre = str(f["Cod"]), str(f["Producto"])
    with st.container(key="rec_carta_plato"):
        ruta = " › ".join(x for x in (f["Grupo"], f["Subgrupo"]) if x)
        st.markdown(f'<p class="chart-card-hdr">{escape(nombre)} · '
                    f'{escape(ruta)} · {escape(f["Tipo"])}</p>',
                    unsafe_allow_html=True)
        st.markdown(kpis_producto(f, rango))
        sin_costo_neto = float(f.get("SinCostoNeto", 0.0))
        if sin_costo_neto > 0:
            # Dos historias distintas con el mismo número: el que HOY no
            # tiene costo (las aguas Munay, en «No aplica») y el que se
            # vendió antes de que se lo cargaran (los platos nuevos de
            # julio). El costo con que se vende es una foto: en los dos casos
            # ese neto quedó en el FoodCost con costo 0 (regla #556).
            causa = ("el POS no le tiene costo" if f["SinCosto"] else
                     "se vendió antes de que el POS se lo cargara")
            st.markdown(
                f'<p style="color:{ADVERTENCIA_TEXTO};margin:0">'
                f'S/ {sin_costo_neto:,.0f} de lo vendido en {DIAS_VENDIDOS} '
                f'días entró al FoodCost con costo 0: {causa}, y así queda '
                f'guardado.</p>', unsafe_allow_html=True)
        if f["Tipo"] == "Receta":
            r, costo_sim = receta_del_plato(df_rv, cod, nombre)
        else:
            r, costo_sim = None, None
            _descarga(f)
        with _card("rec_carta_mini"):
            # NO `st.tabs`: dibuja las dos pestañas y esconde la otra, y
            # un `plotly_events` escondido mide 0 y alterna su alto sin
            # fin — trababa la página entera (regla #500).
            vista = st.segmented_control(
                "Vista", ["Costo / Utilidad", "Sankey", "En el tiempo"],
                default="Costo / Utilidad", key="rec_carta_mini_vista",
                label_visibility="collapsed")
            if vista == "En el tiempo":
                _dib_costo_en_el_tiempo(f, ventas)
            elif vista == "Sankey":
                if r is None:
                    st.info("Sin receta no hay Sankey: el Sankey reparte "
                            "el costo entre los insumos de la receta.")
                else:
                    _dib_sankey_insumo_costo(r, nombre, cod,
                                             costo_sim is not None)
            elif f["SinCosto"] and costo_sim is None:
                # Sin costo, la dona dibujaría «0 % de costo» y toda la
                # porción como utilidad: una cifra que no existe.
                st.info("Sin costo cargado: no hay cómo repartir el "
                        "precio entre costo y utilidad.")
            else:
                _dib_torta_costo_utilidad(f["Neto"], f["Costo"], f["Pct"],
                                          cod, costo_sim)


# ─── La vista ─────────────────────────────────────────────────────────────
def render_carta_costeada(df, df_rv=None, ventas=None):
    """La vista entera: UNA tarjeta con la carta a la izquierda y el
    producto elegido a la derecha (regla #570). `df` es
    `cartacosteada.parquet` (o None si no se pudo cargar); `df_rv`,
    recetaventa.parquet (las recetas y su fecha); `ventas`, lo vendido por
    producto y día (`data.venta_por_producto_dia`), o None."""
    ss = st.session_state
    # LO ELEGIDO, ANTES DE DIBUJAR NADA: la tabla nueva sale con eso marcado.
    _leer_eleccion("rec_carta_tabla")
    _leer_eleccion("rec_carta_combos")

    with st.container(border=True, key="rec_card_carta"):
        st.markdown('<p class="chart-card-hdr">Carta costeada · % de costo sobre '
                    'el precio neto de Salón, combos incluidos</p>',
                    unsafe_allow_html=True)
        if df is None or df.empty:
            st.info("Todavía no hay datos de la carta costeada "
                    f"({ARCHIVO}). Se genera con la consulta «cartacosteada» del "
                    "Sheet: aparece después del próximo refresco.")
            return

        inactivos = bool(ss.get("rec_carta_inactivos", False))
        vi = bool(ss.get("rec_carta_vi", False))
        carta, n_sin_precio = preparar(df, incluir_inactivos=inactivos)
        fechas = fechas_de_receta(df_rv)
        carta["Actualizado"] = pd.to_datetime(
            carta["Cod"].map(fechas), errors="coerce").fillna(_SIN_FECHA)
        carta, rango = con_ventas(carta, ventas)
        grupos = ["Todos"] + sorted(
            g for g in carta["Grupo"].unique()
            if g and (vi or g.casefold() != GRUPO_VENTA_INTERNA.casefold()))

        # Las cuatro opciones de «Ver» sólo si la consulta ya trae «Tipo de
        # Oferta»; si lo elegido no está entre las de ahora (otro juego de
        # rótulos), se BORRA y el control vuelve a su default: escribirle
        # otro valor, con un `default=` puesto, es un aviso de Streamlit.
        hay_oferta = bool((carta["Oferta"] != "").any())
        opciones_ver = VER_OFERTA if hay_oferta else VER
        if ss.get("rec_carta_ver") not in (None, *opciones_ver):
            ss.pop("rec_carta_ver")
        # columnas-internas: la fila de controles de la tarjeta (qué ver,
        # grupo, tipo, buscador y los dos interruptores); no parte la página.
        # Con cuatro opciones «Ver» pide 362px (medido: 93 + 83 + 102 + 84;
        # con 357, «Combos» bajaba a un segundo renglón) y se los ceden el
        # grupo, el tipo y el buscador. A 1366px con el rail plegado, la
        # fila tiene 1122px sin los huecos: esto suma 1114.
        anchos = ([372, 156, 130, 150, 140, 166] if hay_oferta
                  else [1.5, 1.25, 1.1, 1.5, 0.95, 1.1])
        c_ver, c_grupo, c_tipo, c_buscar, c_inact, c_vi = st.columns(
            anchos, vertical_alignment="center")
        with c_ver:
            ver = st.segmented_control(
                "Ver", opciones_ver, default=opciones_ver[0],
                key="rec_carta_ver",
                label_visibility="collapsed") or opciones_ver[0]
        with c_grupo:
            if ss.get("rec_carta_grupo") not in grupos:
                ss["rec_carta_grupo"] = "Todos"
            grupo = st.selectbox("Grupo", grupos, key="rec_carta_grupo",
                                 label_visibility="collapsed")
        with c_tipo:
            # En «Combos» el tipo ya está elegido: se apaga en vez de
            # esconderse, para no perder lo elegido al volver (un widget que
            # no se dibuja pierde su estado).
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
        with c_vi:
            st.toggle("Venta interna", key="rec_carta_vi",
                      help="Sumar los productos «(Cst)» de Venta Interna, que se "
                           "venden a precio de costo y por eso pasan el 100 %")

        if ver == "Combos":
            t = filtrar(carta, grupo, "Combo", buscar, venta_interna=vi)
            st.markdown(resumen(t, "combos"))
            vacio = "No hay combos con este filtro."
        else:
            t = filtrar(carta, grupo, tipo, buscar, venta_interna=vi,
                        oferta=OFERTAS.get(ver))
            st.markdown(resumen(t))
            vacio = "Ningún producto con este filtro."
        if t.empty:
            st.info(vacio)
            return
        t = t.reset_index(drop=True)
        pos = t.index[t["Cod"] == ss.get(_K_FOCO)]
        pos = int(pos[0]) if len(pos) else 0

        # columnas-internas: la tabla y, AL COSTADO, el producto elegido
        # (regla #570); es la tarjeta de la vista, no parte la página.
        c_tabla, c_panel = st.columns(list(PROPORCION), gap="medium")
        with c_tabla:
            # «Más columnas» va ARRIBA DE LA TABLA y no en la fila de
            # controles: es de la tabla, y en esa fila no entraba un séptimo
            # control a 1366px (medido: «Carta completa | Combos» se partía
            # en dos renglones y «Inactivos» se cortaba). A la IZQUIERDA: a
            # la derecha lo tapa la barrita de íconos que `st.dataframe`
            # asoma sobre su esquina al pasar el cursor. El renglón que suma
            # lo paga la columna de la tabla, que es la más baja.
            with st.container(key="rec_carta_mas_fila"):
                mas = st.toggle(
                    "Más columnas", key=_K_MAS,
                    help="En la carta: Margen, Vendidos (90 días), Tipo, "
                         "Actualizado y Última venta. En Combos: la banda de "
                         "costos (mínimo, promedio, esperado, máximo y real). "
                         "La tabla se desliza de costado; el producto elegido "
                         "sigue al lado.")
            if ver == "Combos":
                _tabla_combos(t, pos, mas)
                st.caption(
                    "Todo con la cantidad de la ficha y el costo de HOY de cada "
                    "plato. Esperado: cada opción pesada por lo que eligieron los "
                    "clientes — en 90 días si hubo 10 o más vendidos, si no con "
                    "todo su historial; un grupo sin elecciones cuenta su "
                    "promedio. Real: lo servido en 90 días, al costo de cada día. "
                    "Clic en un combo para ver su detalle.")
            else:
                _tabla_carta(t, pos, rango, mas)
                orden = ("lo vendido en 90 días" if tipo == "Sin costo"
                         else "% de costo")
                pie = (f"Ordenada por {orden}. Semáforo: sobre {_UMBRAL_COSTO_OK} % "
                       f"en ámbar, sobre {_UMBRAL_COSTO_WARN} % en rojo. Clic en "
                       "un producto para ver su receta.")
                if ver in OFERTAS:
                    pie += (" Carta impresa: los productos con botón del 1 al "
                            "19 en el POS («Tipo de Oferta» de la consulta).")
                if n_sin_precio:
                    pie += (f" {n_sin_precio} sin precio de Salón (S/ 1 o menos) "
                            "no se muestran.")
                if rango is not None:
                    # «¿Vendidos cuándo?» (preguntado el 2026-09-29): la
                    # ventana termina en el último día con venta, no hoy.
                    pie += (f" Lo vendido es de los últimos {DIAS_VENDIDOS} días "
                            f"con datos: del {rango[0]:%d/%m} al "
                            f"{rango[1]:%d/%m/%Y}.")
                else:
                    pie += " No se pudieron leer las ventas: sin «Vendidos»."
                st.caption(pie)
        with c_panel:
            _panel(t.iloc[pos], df_rv, rango, ventas)
