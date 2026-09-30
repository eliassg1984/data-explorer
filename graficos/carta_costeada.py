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
from functools import partial
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
    _K_SIM_ON, AYUDA_SIMULAR, _dib_sankey_insumo_costo,
    _dib_torta_costo_utilidad, receta_del_plato,
)
from graficos.ventas_mix import pct_costo
from tema import (ACENTO, ADVERTENCIA, ADVERTENCIA_TEXTO, ERROR, GRIS_TEXTO,
                  LAVANDA_FONDO)
from utils import _norm

ARCHIVO = "cartacosteada.parquet"

VER = ("Carta completa", "Combos")
"""El desplegable «Ver» del renglón del título (regla #574)."""

OFERTA_TODA = "Toda la carta"
OFERTAS = ("Carta impresa", "Carta no impresa")
"""Los valores de «Tipo de Oferta» de la consulta (regla #571), que son
también las opciones de su desplegable, detrás de «Toda la carta». Sin la
columna —un parquet de antes de la regla— el desplegable no se dibuja."""

SUBTITULO = "% de costo sobre el precio neto de Salón, combos incluidos"
"""Lo que decía el título al lado del nombre; desde la regla #574 aparece
al pasar el cursor sobre «Carta costeada»."""

_K_VER = "rec_carta_vista"
_K_OFERTA = "rec_carta_oferta"
"""Keys nuevas y no las del `segmented_control` de antes (`rec_carta_ver`):
un desplegable que hereda un valor que no está entre sus opciones es un
error de Streamlit."""
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
"""La ventana de «Vendidos» por defecto: 90 días hasta el último día con
venta."""

VENTANAS_VENDIDOS = {"30 días": 30, "90 días": 90, "6 meses": 180,
                     "1 año": 365}
"""Las ventanas que se pueden elegir para «Vendidos» (regla #572). Terminan
todas en el último día con venta del resumen, no hoy."""

_K_VENTANA = "rec_carta_vend_ventana"
"""El selector de la ventana de «Vendidos». Se dibuja sólo con «Más
columnas» —es la columna que mide—, y con `persist_state="page"` conserva
lo elegido mientras está escondido."""

_K_VENTAS_OK = "rec_carta_ventas_ok"
"""Si en esta sesión ya se cargó lo vendido (regla #573). Desde entonces se
pide siempre: la segunda vez es la caché, y así el aviso de lo vendido sin
costo no aparece y desaparece según esté prendido «Más columnas»."""

_K_BASE = "rec_carta_base"
"""La receta base abierta en el panel: `{"plato", "ruta", "aviso", "gen"}`.
`ruta` es la lista de recetas base abiertas, de la del plato a la más
adentro; cada una `{"cod", "nombre", "escala", "costo", "es_base"}`. La
escriben los clics en las tablas (callbacks), antes de la corrida que
dibuja. `gen` va en la key de la tabla de la receta y la sube «✕»: cerrar
estrena la tabla, sin la fila marcada."""

_SIN_FECHA = pd.Timestamp("1900-01-01")
"""Una fecha que falta. `st.dataframe` pinta «None» en un vacío aunque el
Styler diga otra cosa (regla #529), así que va esta y se escribe «—»: la
columna sigue siendo de fechas, y ordenar por ella ordena por fecha."""

_K_FOCO = "rec_carta_foco"
"""El código del producto elegido. Sólo lo escribe un clic: sin clic, o
con el elegido fuera del filtro, el panel sigue a la primera fila."""

_K_MAS = "rec_carta_mas_cols"
"""El interruptor «Más columnas» (regla #570): arranca apagado."""

PROPORCION = (0.6, 0.4)
"""Tabla | producto elegido. Sin «P. neto» (regla #574) las columnas de
siempre miden 678px con la casilla de selección, y a 1323px de ancho —la
pantalla del usuario— le tocan ~688: el panel se queda con ~458, y los
nombres de la receta ganan 30px."""


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
        {v.upper(): v for v in OFERTAS}).fillna("")
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
    cols.append("Precio")
    if mas:
        # «P. neto» se esconde con las demás desde la regla #574: es el precio
        # ÷ 1,235, y el % de costo ya está calculado sobre él.
        cols.append("Neto")
    cols.append("Costo")
    if mas:
        cols += ["Tipo", "Actualizado", "UltimaVenta"]
    return cols


def _tabla_carta(t, pos_foco, rango, mas=False, dias=DIAS_VENDIDOS):
    movil = _es_movil()
    cols = columnas_carta(mas, rango is not None, movil)
    col_vend = f"Vendidos {dias} d"
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
    vendidos_help = (f"Unidades vendidas en los últimos {dias} días "
                     "hasta el último día con venta")
    if rango is not None:
        vendidos_help += f": del {rango[0]:%d/%m/%Y} al {rango[1]:%d/%m/%Y}"
    cfg = {
        "Grupo": st.column_config.TextColumn(pinned=fija, width=100),
        "Subgrupo": st.column_config.TextColumn(pinned=fija, width=114),
        "Producto": st.column_config.TextColumn(pinned=fija or movil, width=210),
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


def _dib_costo_en_el_tiempo(f, agg, alto=alturas.MINI):
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
    _compras_layout(fig, alto=alto)
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


# ─── Las recetas base (regla #572) ───────────────────────────────────────
# Un insumo de la receta de un plato es RECETA BASE cuando su código de
# almacén (`COD INS` de recetaventa) es el de un artículo con receta en
# recetabase (`COD PROD RB`, uno por receta base). La receta base guarda lo
# que lleva UNA unidad suya (un kilo de demiglace, una molleja cocida); el
# plato usa `CANTIDAD ÷ FACTOR` unidades (40 g ÷ 1.000 = 0,04 kg), y por eso
# su tabla sale proporcionada: los costos suman lo de esa línea de la receta
# (medido el 2026-09-30: 821 de 866 líneas, al 1 %; las otras las costea el
# precio promedio del almacén, que no es el de la receta).
def codigos_base(df_rb):
    """Los códigos de almacén que tienen receta base. Pura."""
    if df_rb is None or df_rb.empty:
        return frozenset()
    c = _resolver(df_rb, ["COD PROD RB"])
    if not c:
        return frozenset()
    return frozenset(df_rb[c].dropna().astype(str).str.strip())


def receta_base(df_rb, cod, escala=1.0, bases=frozenset()):
    """Los insumos de la receta base del artículo `cod`, proporcionados a
    `escala` unidades de ella: Cod, Insumo, Cantidad, Costo, %, Factor y
    EsBase (si ese insumo tiene, a su vez, receta base). Pura."""
    cols = ["Cod", "Insumo", "Cantidad", "Costo", "%", "Factor", "EsBase"]
    if df_rb is None or df_rb.empty:
        return pd.DataFrame(columns=cols)
    c = {n: _resolver(df_rb, [n]) for n in (
        "COD PROD RB", "COD INS RB", "INSUMO", "CANT", "FACTOR INS",
        "CST SUBT INS")}
    if not all(c.values()):
        return pd.DataFrame(columns=cols)
    d = df_rb[df_rb[c["COD PROD RB"]].astype(str).str.strip() == str(cod).strip()]
    d = d[d[c["COD INS RB"]].notna()]
    out = pd.DataFrame({
        "Cod": d[c["COD INS RB"]].astype(str).str.strip(),
        "Insumo": d[c["INSUMO"]].astype(str),
        "Cantidad": pd.to_numeric(d[c["CANT"]], errors="coerce").fillna(0.0) * escala,
        "Costo": pd.to_numeric(d[c["CST SUBT INS"]], errors="coerce").fillna(0.0) * escala,
        "Factor": pd.to_numeric(d[c["FACTOR INS"]], errors="coerce").fillna(0.0),
    })
    total = out["Costo"].sum() or 1.0
    out["%"] = out["Costo"] / total * 100
    out["EsBase"] = out["Cod"].isin(bases)
    return out.sort_values("Costo", ascending=False).reset_index(drop=True)[cols]


# ─── Los porcionamientos (regla #574) ─────────────────────────────────────
# Un insumo de la receta es PORCIONADO cuando sale de un porcionamiento: su
# código es un `COD PROD FINAL` de porcionamientos.parquet (93 insumos de
# recetas al 2026-09-30, 49 de ellos además con receta base). Su costo en la
# receta es el precio promedio del almacén, que en un porcionado suele ser
# el del ÚLTIMO porcionamiento: la Pesca del día, S/ 26,78 en la receta y en
# el porcionamiento del 26/09. El parquet trae una fila por CORTE con la
# cabecera repetida (regla #510): acá se lee la fila del corte pedido, una
# por porcionamiento.
_N_PORC = 8
"""Cuántos porcionamientos se muestran, del más nuevo al más viejo."""


def codigos_porcionados(df_po):
    """Los códigos de almacén que salen de algún porcionamiento. Pura."""
    if df_po is None or df_po.empty:
        return frozenset()
    c = _resolver(df_po, ["COD PROD FINAL"])
    if not c:
        return frozenset()
    return frozenset(df_po[c].dropna().astype(str).str.strip())


def porcionamientos_de(df_po, cod, n=_N_PORC):
    """Los últimos `n` porcionamientos de los que salió `cod`, del más nuevo
    al más viejo: Fecha, De (lo que se porcionó), Porcionado y UnidIni
    (cuánto), Salio y UnidFin (cuánto salió de ESTE corte), Merma (% de lo
    porcionado) y Costo (por unidad de este corte: lo que hereda la receta).
    Pura."""
    cols = ["Fecha", "De", "Porcionado", "UnidIni", "Salio", "UnidFin",
            "Merma", "Costo"]
    if df_po is None or df_po.empty:
        return pd.DataFrame(columns=cols)
    c = {k: _resolver(df_po, [k]) for k in (
        "COD PORC", "COD PROD FINAL", "FEC REGIST", "PROD INICIAL",
        "UNID PROD INIC", "CANT A PORCIONAR", "CANT MERMA", "CANT RESULT",
        "UNID PROD FIN", "PREC PROM PROD FIN")}
    if not (c["COD PROD FINAL"] and c["FEC REGIST"]):
        return pd.DataFrame(columns=cols)
    d = df_po[df_po[c["COD PROD FINAL"]].astype(str).str.strip() == str(cod).strip()]
    if c["COD PORC"]:
        d = d.drop_duplicates(subset=[c["COD PORC"]])
    d = d.assign(_f=pd.to_datetime(d[c["FEC REGIST"]], errors="coerce"))
    d = d.sort_values("_f", ascending=False, kind="stable").head(n)
    porc = _num(d, c["CANT A PORCIONAR"]).fillna(0.0)
    merma = _num(d, c["CANT MERMA"]).fillna(0.0)
    out = pd.DataFrame({
        "Fecha": d["_f"],
        "De": _texto(d, c["PROD INICIAL"]),
        "Porcionado": porc,
        "UnidIni": _texto(d, c["UNID PROD INIC"]),
        "Salio": _num(d, c["CANT RESULT"]).fillna(0.0),
        "UnidFin": _texto(d, c["UNID PROD FIN"]),
        "Merma": (merma / porc.where(porc > 0) * 100).fillna(0.0),
        "Costo": _num(d, c["PREC PROM PROD FIN"]).fillna(0.0),
    })
    return out.reset_index(drop=True)[cols]


def costo_de_origen(costo_unit, costo_base, costo_porc):
    """Si el costo por unidad de la receta sale de la receta base o del
    último porcionamiento: «base» o «porc», el que esté más cerca (uno solo
    si falta el otro). Es con qué abre el detalle de un insumo que tiene las
    dos cosas. Pura."""
    if costo_base is None and costo_porc is None:
        return None
    if costo_porc is None:
        return "base"
    if costo_base is None:
        return "porc"
    return ("base" if abs(costo_unit - costo_base) <= abs(costo_unit - costo_porc)
            else "porc")


def _escala(cantidad, factor):
    """Cuántas unidades de la receta base usa una línea: su cantidad (en la
    unidad de la receta) ÷ el factor a la unidad del kardex."""
    return float(cantidad) / float(factor) if factor and factor > 0 else float(cantidad)


def _filas_clic(r, bases, porcs=frozenset()):
    """Lo que un clic en la fila `i` de la tabla `r` necesita saber."""
    cods = r["Cod"] if "Cod" in r.columns else pd.Series("", index=r.index)
    facts = r["Factor"] if "Factor" in r.columns else pd.Series(0.0, index=r.index)
    return [{"cod": str(c), "nombre": str(n), "escala": _escala(q, fa),
             "costo": float(co), "es_base": str(c) in bases,
             "es_porc": str(c) in porcs}
            for c, n, q, fa, co in zip(cods, r["Insumo"], r["Cantidad"], facts,
                                       r["Costo"])]


def _abre(fila):
    """Si una fila se puede abrir: tiene receta base o sale de un
    porcionamiento."""
    return bool(fila.get("es_base") or fila.get("es_porc"))


def _al_elegir_en_receta(key, plato, filas):
    """Clic en la receta del plato: abre la receta base de esa fila, o la
    cierra si se soltó la fila o si el insumo no tiene."""
    fila = _fila_elegida(st.session_state.get(key))
    gen = (st.session_state.get(_K_BASE) or {}).get("gen", 0)
    estado = {"plato": plato, "ruta": [], "gen": gen}
    if fila is not None and 0 <= fila < len(filas):
        if _abre(filas[fila]):
            estado["ruta"] = [filas[fila]]
        else:
            estado["aviso"] = filas[fila]["nombre"]
    st.session_state[_K_BASE] = estado


def _al_elegir_en_base(key, plato, ruta, filas):
    """Clic en una receta base abierta: si esa fila también es receta base,
    se abre ella (un nivel más adentro)."""
    fila = _fila_elegida(st.session_state.get(key))
    if fila is not None and 0 <= fila < len(filas) and _abre(filas[fila]):
        e = st.session_state.get(_K_BASE) or {}
        st.session_state[_K_BASE] = {"plato": plato, "ruta": ruta + [filas[fila]],
                                     "gen": e.get("gen", 0)}


def _subir_base(plato):
    e = st.session_state.get(_K_BASE) or {}
    if e.get("plato") == plato:
        st.session_state[_K_BASE] = {"plato": plato, "gen": e.get("gen", 0),
                                     "ruta": list(e.get("ruta", []))[:-1]}


def _cerrar_base(plato):
    """«✕»: cierra la receta base y estrena la tabla de la receta. Soltar la
    fila también la cierra, pero la tabla que no tiene el foco se come el
    primer clic sobre una fila ya marcada (medido: después de tocar otro
    control, hacían falta dos)."""
    e = st.session_state.get(_K_BASE) or {}
    st.session_state[_K_BASE] = {"plato": plato, "ruta": [],
                                 "gen": e.get("gen", 0) + 1}


def _estado_base(plato):
    """El estado de la receta base abierta PARA ESTE PLATO. Si era de otro,
    se vacía: la tabla de la receta nace sin fila elegida, y dejarlo haría
    que al volver al plato apareciera abierta una receta base sin su fila."""
    e = st.session_state.get(_K_BASE) or {}
    if e.get("plato") != plato:
        e = {"plato": plato, "ruta": [], "gen": e.get("gen", 0)}
        st.session_state[_K_BASE] = e
    return e


_CFG_RECETA = {
    # Suman 396 + los 36 de la casilla de selección: el panel mide ~441 a
    # 1323px, la pantalla del usuario (regla #574; con los anchos
    # automáticos el número del «%» quedaba cortado contra el borde).
    # El «▸» se explica en la ayuda de la cabecera y no en un renglón
    # debajo de la tabla: eran 36px, y sin ellos la tarjeta entra en ~600
    # de alto (regla #574).
    "Insumo": st.column_config.TextColumn(
        width=176, help="▸ receta base o porcionado: clic en la fila para "
                        "ver de dónde sale su costo"),
    "Cantidad": st.column_config.NumberColumn(format="%.3f", width=64),
    "Costo": st.column_config.NumberColumn(format="S/ %.2f", width=66),
    "%": st.column_config.ProgressColumn(format="%.1f%%", min_value=0,
                                         max_value=100, width=90),
}


def _con_flecha(r, porcs=frozenset()):
    """La tabla a mostrar: «▸» delante de lo que se puede abrir —una receta
    base o un porcionado—. En una copia: el Sankey usa los nombres tal
    cual."""
    v = r[["Insumo", "Cantidad", "Costo", "%"]].copy()
    abre = r["EsBase"] if "EsBase" in r.columns else pd.Series(False, index=r.index)
    if "Cod" in r.columns:
        abre = abre | r["Cod"].isin(porcs)
    v["Insumo"] = np.where(abre, "▸ " + r["Insumo"], r["Insumo"])
    return v


def _tabla_receta(orig, plato, bases, porcs=frozenset()):
    """La receta del plato en lectura, clicable (reglas #572 y #574)."""
    r = orig.copy()
    r["EsBase"] = (r["Cod"].isin(bases) if "Cod" in r.columns
                   else pd.Series(False, index=r.index))
    filas = _filas_clic(r, bases, porcs)
    gen = _estado_base(plato).get("gen", 0)
    key = _key_tabla(f"rec_carta_rv_{plato}_{gen}",
                     [f"{x['cod']}:{x['nombre']}" for x in filas])
    st.dataframe(_con_flecha(r, porcs), key=key,
                 on_select=partial(_al_elegir_en_receta, key, plato, filas),
                 selection_mode="single-row", hide_index=True, row_height=27,
                 height=alturas.por_filas(len(r), px_fila=27, extra=38,
                                          minimo=0, rol=alturas.CARTA_RECETA),
                 column_config=_CFG_RECETA)
    e = _estado_base(plato)
    if e.get("aviso") and not e.get("ruta"):
        st.caption(f"«{e['aviso']}» es un insumo de compra: no tiene receta "
                   "base ni porcionamientos.")



_MODOS = ("Receta base", "Porcionamientos")


def _bloque_base(df_rb, df_po, plato, ruta, bases, porcs):
    """Debajo de la receta, en el lugar del gráfico: de dónde sale el costo
    del insumo abierto — su receta base, proporcionada a lo que lleva UN
    plato (regla #572), o sus últimos porcionamientos (regla #574). Va en el
    lugar del gráfico y con su mismo alto para que abrirla no estire la
    tarjeta."""
    actual = ruta[-1]
    rb = (receta_base(df_rb, actual["cod"], actual["escala"], bases)
          if actual.get("es_base") else None)
    po = (porcionamientos_de(df_po, actual["cod"])
          if actual.get("es_porc") else None)
    modos = [m for m, x in zip(_MODOS, (rb, po)) if x is not None]
    with st.container(key="rec_carta_base_caja"):
        with st.container(horizontal=True, vertical_alignment="center",
                          key="rec_carta_base_hdr"):
            # La ABIERTA primero: con el camino entero («A › B») el renglón
            # se cortaba en la de afuera y la que se estaba viendo no se
            # leía (medido en el segundo nivel). El camino va en el tooltip.
            migas = " › ".join(x["nombre"] for x in ruta)
            st.markdown(f'<p class="rec-base-tit" title="{escape(migas)}">'
                        f'{escape(actual["nombre"])}</p>',
                        unsafe_allow_html=True)
            if len(modos) > 1:
                # Las dos cosas (49 insumos): abre en la que explica el costo
                # de la receta — la más cercana a su costo por unidad.
                unit = actual["costo"] / actual["escala"] if actual["escala"] else 0.0
                c_base = float(rb["Costo"].sum()) / actual["escala"] if (
                    actual["escala"] and not rb.empty) else None
                c_porc = float(po["Costo"].iloc[0]) if not po.empty else None
                de = costo_de_origen(unit, c_base, c_porc)
                k_modo = f"rec_carta_det_modo_{actual['cod']}"
                if st.session_state.get(k_modo) not in modos:
                    st.session_state[k_modo] = (_MODOS[1] if de == "porc"
                                                else _MODOS[0])
                with st.container(key="rec_carta_det_modo", width="content"):
                    modo = st.selectbox("De dónde sale", modos, key=k_modo,
                                        label_visibility="collapsed", width=140)
            else:
                modo = modos[0]
            if len(ruta) > 1:
                st.button("↑ Subir", key="rec_carta_base_subir",
                          on_click=_subir_base, args=(plato,))
            st.button("✕", key="rec_carta_base_cerrar",
                      on_click=_cerrar_base, args=(plato,))
        if modo == _MODOS[1]:
            _tabla_porcionamientos(po, actual)
            return
        if rb.empty:
            st.info("La receta base no tiene insumos cargados.")
            return
        filas = _filas_clic(rb, bases, porcs)
        key = _key_tabla(f"rec_carta_rb_{plato}_" + "-".join(x["cod"] for x in ruta),
                         [f"{x['cod']}:{x['nombre']}" for x in filas])
        st.dataframe(_con_flecha(rb, porcs), key=key,
                     on_select=partial(_al_elegir_en_base, key, plato, ruta, filas),
                     selection_mode="single-row", hide_index=True, row_height=27,
                     height=alturas.por_filas(len(rb), px_fila=27, extra=38,
                                              minimo=0, rol=alturas.CARTA_RECETA),
                     column_config=_CFG_RECETA)
        total = float(rb["Costo"].sum())
        pie = f"Lo que lleva un plato: S/ {total:,.2f}"
        if abs(total - actual["costo"]) > max(0.01, 0.01 * abs(actual["costo"])):
            # Las líneas que no cuadran las costea el precio promedio del
            # almacén, no la receta (45 de 866 al 2026-09-30).
            pie += (f" (en la receta: S/ {actual['costo']:,.2f}, promedio del "
                    "almacén)")
        pie += "."
        if any(_abre(x) for x in filas):
            pie += " ▸ abre lo de adentro."
        st.caption(pie)


def _cant(v, unid):
    return f"{v:,.3f}".rstrip("0").rstrip(".") + (f" {unid.lower()}" if unid else "")


def _tabla_porcionamientos(po, actual):
    """Los últimos porcionamientos del insumo abierto (regla #574). No se
    clica: el producto de origen es de otro porcionamiento o de una compra,
    y el costo se lee acá."""
    if po.empty:
        st.info("No hay porcionamientos de este insumo en el parquet.")
        return
    v = pd.DataFrame({
        "Fecha": po["Fecha"].dt.strftime("%d/%m/%y"),
        "De": po["De"],
        "Porcionado": [_cant(q, u) for q, u in zip(po["Porcionado"], po["UnidIni"])],
        "Salió": [_cant(q, u) for q, u in zip(po["Salio"], po["UnidFin"])],
        "Merma": po["Merma"],
        "Costo u.": po["Costo"],
    })
    st.dataframe(v, hide_index=True, row_height=27,
                 height=alturas.por_filas(len(v), px_fila=27, extra=38,
                                          minimo=0, rol=alturas.CARTA_RECETA),
                 column_config={
                     # Suman 426: el panel mide ~431 a 1323px (con 438, la
                     # última columna quedaba cortada contra el borde).
                     "Fecha": st.column_config.TextColumn(width=60),
                     "De": st.column_config.TextColumn(
                         width=118, help="Lo que se porcionó"),
                     "Porcionado": st.column_config.TextColumn(width=70),
                     "Salió": st.column_config.TextColumn(
                         width=62, help="Lo que salió de este corte"),
                     "Merma": st.column_config.NumberColumn(
                         format="%.0f%%", width=50,
                         help="Merma del porcionamiento, sobre lo porcionado"),
                     "Costo u.": st.column_config.NumberColumn(
                         format="S/ %.2f", width=66,
                         help="Costo por unidad de este corte: el del producto "
                              "porcionado, repartido entre los cortes"),
                 })
    unit = actual["costo"] / actual["escala"] if actual["escala"] else 0.0
    ult = float(po["Costo"].iloc[0])
    fecha = po["Fecha"].iloc[0]
    # En UN renglón: con dos, abrirlo estiraba la tarjeta fuera de la
    # pantalla del usuario (medido a 1323×619).
    if ult and abs(unit - ult) <= max(0.01, 0.01 * ult):
        st.caption(f"Receta: S/ {unit:,.2f} c/u, el del último porcionamiento "
                   f"({fecha:%d/%m/%y}).")
    else:
        st.caption(f"Receta: S/ {unit:,.2f} c/u, promedio del almacén · último: "
                   f"S/ {ult:,.2f} ({fecha:%d/%m/%y}).")


def _lo_vendido(ventas):
    """Lo vendido por producto y día. `ventas` es el resumen ya cargado o la
    función que lo carga (`data.venta_por_producto_dia`): con la función, se
    llama acá, con un aviso — en frío es lo más lento de la vista (regla
    #573)."""
    if not callable(ventas):
        return ventas
    with st.spinner("Cargando lo vendido… la primera vez del día tarda"):
        agg = ventas()
    if agg is not None:
        st.session_state[_K_VENTAS_OK] = True
    return agg


def _panel(f, df_rv, dias, ventas=None, df_rb=None, porcionamientos=None):
    """Al costado de la tabla (regla #570): el producto elegido, su receta
    (o lo que descarga) y, debajo, la dona / el Sankey / su costo en el
    tiempo — o la receta base que se abrió con un clic en la receta (regla
    #572). Lo que era la parte de abajo de «Composición» (regla #556), más
    el costo con que se vendió (regla #557).

    Desde la #572 cabe en una pantalla de 1366×768: sin la línea de números
    del producto (a pedido), con «Simular» en el renglón del nombre y el
    gráfico de 200px."""
    cod, nombre = str(f["Cod"]), str(f["Producto"])
    es_receta = f["Tipo"] == "Receta"
    simulando = es_receta and bool(st.session_state.get(_K_SIM_ON))
    bases = codigos_base(df_rb)
    # Los porcionamientos, sólo si hay receta que marcar (regla #574): el
    # parquet es chico (12.368 filas) y lo comparte «Revisar recetas».
    df_po = (porcionamientos() if callable(porcionamientos) else porcionamientos) \
        if es_receta else None
    porcs = codigos_porcionados(df_po)
    with st.container(key="rec_carta_plato"):
        ruta_txt = " › ".join(x for x in (f["Grupo"], f["Subgrupo"]) if x)
        with st.container(horizontal=True, vertical_alignment="center",
                          key="rec_carta_plato_hdr"):
            st.markdown(f'<p class="chart-card-hdr">{escape(nombre)} · '
                        f'{escape(ruta_txt)} · {escape(f["Tipo"])}'
                        + (" · borrador, no se guarda" if simulando else "")
                        + '</p>', unsafe_allow_html=True)
            if es_receta:
                # Acá y no adentro de la receta: un renglón menos. Se dibuja
                # SIEMPRE que hay receta —un widget que no se dibuja pierde
                # su estado, y este decide si la tabla es un editor—.
                st.toggle("Simular", key=_K_SIM_ON, help=AYUDA_SIMULAR)
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
                f'S/ {sin_costo_neto:,.0f} de lo vendido en {dias} '
                f'días entró al FoodCost con costo 0: {causa}, y así queda '
                f'guardado.</p>', unsafe_allow_html=True)
        if es_receta:
            r, costo_sim = receta_del_plato(
                df_rv, cod, nombre, toggle=False, titulo=False,
                dibujar_lectura=partial(_tabla_receta, plato=cod, bases=bases,
                                        porcs=porcs))
        else:
            r, costo_sim = None, None
            _descarga(f)
        # Simulando, la tabla es un editor sin clic: nada abierto (y al
        # volver, la tabla de lectura nace sin fila elegida).
        e = _estado_base(cod)
        if simulando and e.get("ruta"):
            e = {"plato": cod, "ruta": []}
            st.session_state[_K_BASE] = e
        if e.get("ruta"):
            _bloque_base(df_rb, df_po, cod, e["ruta"], bases, porcs)
            return
        with _card("rec_carta_mini"):
            # NO `st.tabs`: dibuja las dos pestañas y esconde la otra, y
            # un `plotly_events` escondido mide 0 y alterna su alto sin
            # fin — trababa la página entera (regla #500). Y `persist_state`:
            # mientras hay una receta base abierta este control no se
            # dibuja, y al cerrarla vuelve como quedó.
            vista = st.segmented_control(
                "Vista", ["Costo / Utilidad", "Sankey", "En el tiempo"],
                default="Costo / Utilidad", key="rec_carta_mini_vista",
                label_visibility="collapsed", persist_state="page")
            alto = alturas.CARTA_FIG
            if vista == "En el tiempo":
                _dib_costo_en_el_tiempo(f, ventas, alto=alto)
            elif vista == "Sankey":
                if r is None:
                    st.info("Sin receta no hay Sankey: el Sankey reparte "
                            "el costo entre los insumos de la receta.")
                else:
                    _dib_sankey_insumo_costo(r, nombre, cod,
                                             costo_sim is not None, alto=alto)
            elif f["SinCosto"] and costo_sim is None:
                # Sin costo, la dona dibujaría «0 % de costo» y toda la
                # porción como utilidad: una cifra que no existe.
                st.info("Sin costo cargado: no hay cómo repartir el "
                        "precio entre costo y utilidad.")
            else:
                _dib_torta_costo_utilidad(f["Neto"], f["Costo"], f["Pct"],
                                          cod, costo_sim, alto=alto)


# ─── La vista ─────────────────────────────────────────────────────────────
def render_carta_costeada(df, df_rv=None, ventas=None, df_rb=None,
                          porcionamientos=None):
    """La vista entera: UNA tarjeta con la carta a la izquierda y el
    producto elegido a la derecha (regla #570). `df` es
    `cartacosteada.parquet` (o None si no se pudo cargar); `df_rv`,
    recetaventa.parquet (las recetas y su fecha); `ventas`, lo vendido por
    producto y día, o la FUNCIÓN que lo carga (`data.venta_por_producto_dia`,
    que es como lo pasa el dispatcher: regla #573), o None; `df_rb`,
    recetabase.parquet (para abrir una receta base), o None;
    `porcionamientos`, porcionamientos.parquet o la función que lo carga
    (regla #574), o None.

    Lo vendido se carga SÓLO si algo en pantalla lo usa: la columna
    «Vendidos» (con «Más columnas»), el filtro «Sin costo» (se ordena por
    lo vendido) o «En el tiempo». Es leer ventas.parquet casi entero —237.604
    filas y 96 MB; 10 s en frío en la laptop, bastante más en Cloud— y hasta
    el 2026-09-30 se pagaba al abrir la vista aunque la columna estuviera
    escondida.

    Desde la regla #574, a pedido, el título es sólo «Carta costeada» (lo
    demás, al pasar el cursor) y en SU renglón van los desplegables —qué
    ver, la oferta, grupo, tipo y el buscador—, con el estilo de la cabecera
    de Ventas › Por hora. Los tres interruptores bajaron al renglón de
    encima de la tabla."""
    ss = st.session_state
    # LO ELEGIDO, ANTES DE DIBUJAR NADA: la tabla nueva sale con eso marcado.
    _leer_eleccion("rec_carta_tabla")
    _leer_eleccion("rec_carta_combos")

    with st.container(border=True, key="rec_card_carta"):
        cab = st.container(horizontal=True, gap="small",
                           vertical_alignment="center", key="rec_carta_cab")
        with cab:
            st.markdown(f'<p class="chart-card-hdr rec-carta-tit" '
                        f'data-ayuda="{escape(SUBTITULO)}">Carta costeada</p>',
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
        # La ventana de «Vendidos» se lee ANTES de dibujar su selector, que va
        # más abajo, encima de la tabla: Streamlit ya dejó en el estado lo
        # que se eligió en el clic que disparó esta corrida.
        ventana = ss.get(_K_VENTANA)
        if ventana not in VENTANAS_VENDIDOS:
            ventana = "90 días"
        dias = VENTANAS_VENDIDOS[ventana]
        grupos = ["Todos"] + sorted(
            g for g in carta["Grupo"].unique()
            if g and (vi or g.casefold() != GRUPO_VENTA_INTERNA.casefold()))
        hay_oferta = bool((carta["Oferta"] != "").any())

        # EL RENGLÓN DEL TÍTULO (regla #574): desplegables sin caja, con un
        # subrayado —los de Ventas › Por hora—; el nombre de cada uno aparece
        # debajo al pasar el cursor. El ancho lo pone Python (`width=`). En
        # «Combos» la oferta y el tipo se apagan en vez de esconderse: un
        # widget que no se dibuja pierde su estado.
        with cab:
            with st.container(key="rec_carta_cab_ver", width="content"):
                ver = st.selectbox("Ver", VER, key=_K_VER,
                                   label_visibility="collapsed", width=128)
            oferta = None
            if hay_oferta:
                with st.container(key="rec_carta_cab_oferta", width="content"):
                    op = st.selectbox("Oferta", (OFERTA_TODA, *OFERTAS),
                                      key=_K_OFERTA, label_visibility="collapsed",
                                      width=140, disabled=(ver == "Combos"))
                oferta = op if op in OFERTAS else None
            with st.container(key="rec_carta_cab_grupo", width="content"):
                if ss.get("rec_carta_grupo") not in grupos:
                    ss["rec_carta_grupo"] = "Todos"
                grupo = st.selectbox("Grupo", grupos, key="rec_carta_grupo",
                                     label_visibility="collapsed", width=150,
                                     format_func=lambda g: ("Todos los grupos"
                                                            if g == "Todos" else g))
            with st.container(key="rec_carta_cab_tipo", width="content"):
                tipo = st.selectbox("Tipo", TIPOS, key="rec_carta_tipo",
                                    label_visibility="collapsed", width=138,
                                    disabled=(ver == "Combos"),
                                    format_func=lambda x: ("Todos los tipos"
                                                           if x == "Todos" else x))
            with st.container(key="rec_carta_cab_buscar", width="content"):
                buscar = st.text_input("Buscar", key="rec_carta_buscar",
                                       placeholder="Buscar producto",
                                       label_visibility="collapsed", width=170)

        # Lo vendido, sólo si algo lo muestra (ver el docstring). Todo se lee
        # del estado: los controles que lo piden ya se dibujaron o van más
        # abajo, y Streamlit dejó ahí lo del clic que disparó la corrida.
        pide_ventas = (bool(ss.get(_K_MAS)) or tipo == "Sin costo"
                       or ss.get("rec_carta_mini_vista") == "En el tiempo"
                       or bool(ss.get(_K_VENTAS_OK)))
        agg = _lo_vendido(ventas) if pide_ventas else None
        carta, rango = con_ventas(carta, agg, dias)

        # Sin la línea de números que iba acá (cuántos, mediana, cuántos
        # sobre el 35 %…): se quitó a pedido el 2026-09-30, con la del
        # producto, para que la tarjeta entre en una pantalla (regla #572).
        if ver == "Combos":
            t = filtrar(carta, grupo, "Combo", buscar, venta_interna=vi)
            vacio = "No hay combos con este filtro."
        else:
            t = filtrar(carta, grupo, tipo, buscar, venta_interna=vi,
                        oferta=oferta)
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
            # Encima de la tabla, lo que cambia QUÉ filas y columnas tiene:
            # los tres interruptores y, con «Más columnas», la ventana de
            # «Vendidos». A la IZQUIERDA: a la derecha lo taparía la barrita
            # de íconos que `st.dataframe` asoma sobre su esquina.
            with st.container(horizontal=True, vertical_alignment="center",
                              key="rec_carta_mas_fila"):
                mas = st.toggle(
                    "Más columnas", key=_K_MAS,
                    help="En la carta: Margen, Vendidos, P. neto, Tipo, "
                         "Actualizado y Última venta. En Combos: la banda de "
                         "costos (mínimo, promedio, esperado, máximo y real). "
                         "La tabla se desliza de costado; el producto elegido "
                         "sigue al lado.")
                st.toggle("Inactivos", key="rec_carta_inactivos",
                          help="Sumar los productos que el POS tiene inactivos")
                st.toggle("Venta interna", key="rec_carta_vi",
                          help="Sumar los productos «(Cst)» de Venta Interna, "
                               "que se venden a precio de costo y por eso pasan "
                               "el 100 %")
                if mas and ver != "Combos" and rango is not None:
                    with st.container(key="rec_carta_cab_vend", width="content"):
                        st.selectbox(
                            "Vendidos en", list(VENTANAS_VENDIDOS),
                            index=list(VENTANAS_VENDIDOS).index("90 días"),
                            format_func=lambda x: f"Vendidos en {x}",
                            key=_K_VENTANA, label_visibility="collapsed",
                            width=160, persist_state="page")
            if ver == "Combos":
                _tabla_combos(t, pos, mas)
                st.caption(
                    "Con la cantidad de la ficha y el costo de HOY de cada plato. "
                    "Esperado: cada opción pesada por lo que eligieron los "
                    "clientes; Real: lo servido en 90 días.")
            else:
                _tabla_carta(t, pos, rango, mas, dias)
                pie = (f"Ámbar sobre {_UMBRAL_COSTO_OK} %, rojo sobre "
                       f"{_UMBRAL_COSTO_WARN} %.")
                if tipo == "Sin costo":
                    pie = "Ordenada por lo vendido."
                if oferta:
                    pie += " Impresa: con botón del 1 al 19 en el POS."
                if n_sin_precio:
                    pie += (f" {n_sin_precio} sin precio de Salón (S/ 1 o menos) "
                            "no se muestran.")
                if rango is not None:
                    # «¿Vendidos cuándo?» (preguntado el 2026-09-29): la
                    # ventana termina en el último día con venta, no hoy.
                    # Con el año del inicio si no es el del fin: con «1 año»
                    # decía «del 29/09 al 28/09/2026».
                    desde = (f"{rango[0]:%d/%m}" if rango[0].year == rango[1].year
                             else f"{rango[0]:%d/%m/%Y}")
                    pie += f" Vendidos: del {desde} al {rango[1]:%d/%m/%Y}."
                elif pide_ventas:
                    pie += " No se pudieron leer las ventas: sin «Vendidos»."
                st.caption(pie)
        with c_panel:
            _panel(t.iloc[pos], df_rv, dias, agg, df_rb, porcionamientos)
