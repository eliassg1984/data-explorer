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
la validación de `pct_costo` del Mix importada. Acá el histórico se fecha
por el comprobante y se divide entre el neto completo: no usa la base del
Mix ajustada por devolución del banco y venta sin costo.

Dos modos en UNA tarjeta, y no dos tarjetas: la carta completa y la banda de
los combos no entran juntas en una pantalla de laptop, y una tarjeta con
barra propia no va (`CLAUDE.md` § Alturas).

LA TABLA PRIMERO, Y EL PLATO DEBAJO (regla #657, opción B del boceto
https://claude.ai/artifact/JFkrxwH2wCipPTGQey1TJ5). Del 2026-09-29 al
2026-10-15 el producto elegido iba AL COSTADO de la tabla (regla #570), y
para que cupiera la tabla escondía la mitad de sus columnas detrás de «Más
columnas». Desde la #657 la tabla va a todo el ancho con TODAS —lo vendido
en el rango con su venta neta, su % y lo vendido sin costo incluidos—, las
tres que dicen qué producto es quedan fijas al deslizarla de costado, y la
ficha del elegido baja: la receta como árbol, con sus recetas base y la
fecha en que se guardó cada una (`simulador_plato.receta_lectura`), y la
evolución del costo con lo vendido de cada mes, los cambios de sus recetas
base (`simulador_receta.marcas_plato`, del log del Almacén) y los días en
que se vendió a un costo imposible (`simulador_receta.picos_plato`). La
tarjeta no tiene techo: la página baja, como en Compras › Producto.

UN SELECTOR DE FECHA manda sobre lo vendido —las cuatro columnas del rango
y lo que la evolución resalta—: el panel de las tarjetas de Compras
(`base.selector_fecha_tarjeta`), con su ctx propio (`_ctx_fecha`) porque
Recetas no tiene fecha en la franja. Abre en «Últimos 3 meses».

`st.dataframe` y no AgGrid: es una tabla de sólo lectura, y cada AgGrid
cuesta 1,28 MB y más de un segundo de navegador (regla #540). Composición
usaba AgGrid sólo para el clic en una fila; `st.dataframe` lo hace con
`selection_mode="single-row-required"` (ver `_key_tabla`).
"""

import datetime
import math
from pathlib import Path
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import simulador_receta as sr
from cortes import MESES_ABR_ES
from data import _cargar_cacheable, cargar, secrets_disponibles, sello_datos
from estado_rango import atajos_tarjeta, clave_rango
from graficos import alturas
from graficos.base import (_card, _compras_layout, _resolver,
                           rango_tarjeta, selector_fecha_tarjeta,
                           una_vez_por_corrida)
from graficos.recetas_comun import divisor_neto
from graficos.recetaventa import (
    _dib_sankey_insumo_costo, _dib_torta_costo_utilidad, _receta_original,
    columnas_receta,
)
from graficos.simulador_plato import (receta_lectura,
                                      simular_plato)
from graficos.ventas_mix import pct_costo
from tema import (ACENTO, ACENTO_TEXTO, ADVERTENCIA, ADVERTENCIA_TEXTO, ERROR,
                  GRIS_CUADRICULA, GRIS_TEXTO, LAVANDA_BORDE, LAVANDA_FILA,
                  LAVANDA_FOCO)
from utils import _norm

ARCHIVO = "cartacosteada.parquet"

VER = ("Carta completa", "Combos")
"""El desplegable «Ver» del renglón del título (regla #574)."""

OFERTA_TODA = "Toda la carta"
OFERTAS = ("Carta impresa", "Carta no impresa")
"""Los valores de «Tipo de Oferta» de la consulta (regla #571), que son
también las opciones de su desplegable, detrás de «Toda la carta». Sin la
columna —un parquet de antes de la regla— el desplegable no se dibuja."""

SUBTITULO = "Costo actual de carta y % de costo sobre el precio neto de Salón"
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

CANALES = (("En el Local", "SALON"), ("Delivery", "DELIVERY"),
           ("Para Llevar", "LLEVAR"), ("Rappi", "RAPPI"), ("Pedidos Ya", "5"))
"""Los canales de venta del POS (`INFOREST.DBO.TCANALVENTA`), en su orden, y
el sufijo de sus columnas en `cartacosteada.parquet` (regla #696). El nombre
es el `CANAL VENTA` de ventas.parquet: así se cruza lo vendido. Desde julio
de 2026 casi todo es «En el Local»; Rappi, un 1 %; Delivery no se usa."""

DIAS_VENDIDOS = 90
"""Los días de lo vendido de «¿Y si sube un insumo?» (`recetas_alza.py`),
hasta el último día con venta. La Carta elige los suyos con su fecha."""

CATEGORIA_FECHA = "carta"
"""La categoría del rango de la tarjeta: su clave es
`rango_cat_Recetas_carta` (`estado_rango.clave_rango`)."""

ATAJO_INICIAL = "m3"
"""Con qué abre la fecha: los últimos 3 meses hasta el último día con venta
—los 90 días que medía «Vendidos» hasta la regla #657, con nombre de
atajo—."""

_K_SOLO_VEND = "rec_carta_solo_vend"
"""«Sólo vendidos en el rango»: 320 de 605 productos activos no se
vendieron en 90 días (medido el 2026-10-15). Arranca apagado: la carta
entera."""

_K_FICHA_VISTA = "rec_carta_ficha_vista"
"""Qué muestra el lado derecho de la ficha: la evolución (por defecto), la
dona, el Sankey o los porcionados del plato."""

_K_PORC = "rec_carta_porc_sel"
"""El porcionado elegido en «Porcionados» de la ficha."""

PROPORCION_FICHA = (1.45, 1)
"""La receta | la evolución, en la ficha de debajo de la tabla: la del
boceto. A 1323px el árbol mide ~650 y deja ~450 al gráfico."""

_SIN_FECHA = pd.Timestamp("1900-01-01")
"""Una fecha que falta. `st.dataframe` pinta «None» en un vacío aunque el
Styler diga otra cosa (regla #529), así que va esta y se escribe «—»: la
columna sigue siendo de fechas, y ordenar por ella ordena por fecha."""

_K_FOCO = "rec_carta_foco"
"""El código del producto elegido. Sólo lo escribe un clic: sin clic, o
con el elegido fuera del filtro, la ficha sigue a la primera fila."""


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
    activo = (_texto(d, c["ITEM VENT ACT"]).str.upper() == "ACTIV"
              if c["ITEM VENT ACT"] else pd.Series(True, index=d.index))
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
    t["Activo"] = activo.loc[d.index].astype(bool)
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
    # LOS CINCO CANALES (regla #696): el POS guarda un precio y un costo por
    # canal (`P.VENTA <canal>`, `COSTO <canal>`). Hoy el costo es el mismo en
    # los cinco y el precio no (Rappi, Para Llevar…), así que el % cambia.
    # Precio de S/ 1 o menos en un canal: el producto no se vende por él.
    for i, (_nombre, sufijo) in enumerate(CANALES):
        p = _num(d, _resolver(df, [f"P.VENTA {sufijo}"]))
        k = _num(d, _resolver(df, [f"COSTO {sufijo}"]))
        t[f"Precio{i}"] = p.where(p > _PRECIO_CENTINELA, 0.0).fillna(0.0).astype(float)
        t[f"Costo{i}"] = k.where(k > 0, 0.0).fillna(0.0).astype(float)
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


def con_ventas(t, agg, dias=DIAS_VENDIDOS, rango=None):
    """`t` con lo vendido de cada producto en los últimos `dias` días del
    resumen de Ventas (`definicion_venta.por_producto_dia`): Vendidos
    (unidades), VendidoNeto, SinCostoNeto (lo vendido sin costo) y
    PctVendido (costo ÷ neto de lo vendido, en %; 0 si no hay costo o no se
    vendió, que se escribe «—»).

    La ventana termina en el último día con venta del resumen, no hoy: el
    parquet llega de la madrugada. Con `rango` (`(ini, fin)`, fechas, los
    dos incluidos) manda ése: es el de la fecha de la tarjeta (regla #657).
    Devuelve `(t, (ini, fin))`, o `(t, None)` sin resumen. Pura."""
    t = t.copy()
    if agg is None or agg.empty:
        for col in ("Vendidos", "VendidoNeto", "SinCostoNeto", "PctVendido",
                    "CostoVendido"):
            t[col] = 0.0
        return t, None
    dia = pd.to_datetime(agg["dia"])
    if rango is not None:
        ini, fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    else:
        fin = dia.max().normalize()
        ini = fin - pd.Timedelta(days=dias - 1)
    u = agg[(dia >= ini) & (dia < fin + pd.Timedelta(days=1))]
    s = u.groupby("producto")[["unidades", "neto", "costo",
                               "neto_sin_costo"]].sum()
    s.index = s.index.astype(str).str.strip()
    cod = t["Cod"].astype(str)
    t["Vendidos"] = cod.map(s["unidades"]).fillna(0.0).astype(float)
    t["VendidoNeto"] = cod.map(s["neto"]).fillna(0.0).astype(float)
    t["SinCostoNeto"] = cod.map(s["neto_sin_costo"]).fillna(0.0).astype(float)
    t["CostoVendido"] = cod.map(s["costo"]).fillna(0.0).astype(float)
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


COLUMNAS_RANGO = ("Vendidos", "VendidoNeto", "PctVendido", "SinCostoNeto")
"""Las columnas que mide la fecha de la tarjeta (regla #657)."""


def columnas_carta(con_ventas_=True, movil=False):
    """Las columnas de la tabla de la carta, en orden: TODAS desde la regla
    #657 —antes la mitad iba detrás de «Más columnas» para que el producto
    cupiera al costado—. Primero lo que ubica al producto —Grupo, Subgrupo y
    su nombre—, después lo que cuesta hoy, lo vendido en el rango, los
    precios y lo que lo describe. `movil`: en un teléfono la tabla no entra
    nunca entera y el nombre va PRIMERO, que es como se sabe qué fila es
    (con Grupo y Subgrupo delante, en 306px no se veía). Pura."""
    cols = ["Grupo", "Subgrupo", "Producto", "Pct", "Margen"]
    if movil:
        cols = ["Producto", "Grupo", "Subgrupo", "Pct", "Margen"]
    if con_ventas_:
        cols += list(COLUMNAS_RANGO)
    cols += ["Precio", "Neto", "Costo", "Tipo", "Oferta", "Actualizado",
             "UltimaVenta"]
    return cols


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


def meses_del_rango(meses, rango):
    """Qué meses de `meses` (Periods) tocan el rango `(ini, fin)`. Pura."""
    if rango is None:
        return [False] * len(meses)
    a = pd.Period(pd.Timestamp(rango[0]), freq="M")
    b = pd.Period(pd.Timestamp(rango[1]), freq="M")
    return [a <= m <= b for m in meses]


def _hover_mes(r):
    partes = [f"<b>{_etiqueta_mes(r['mes'])}</b>"]
    if pd.notna(r["costo_unit"]):
        partes.append(f"S/ {r['costo_unit']:,.2f} por unidad al vender")
    else:
        partes.append("vendido sin costo")
    partes.append(f"{r['unidades']:,.0f} vendidos")
    if pd.notna(r["pct"]):
        partes.append(f"al {r['pct']:.1f} % de costo")
    if r["neto_sin_costo"] > 0:
        partes.append(f"S/ {r['neto_sin_costo']:,.0f} sin costo")
    return "<br>".join(partes)


def _dib_evolucion(f, agg, rango, marcas=(), picos=(), auditoria=(),
                   alto=alturas.CARTA_EVOLUCION):
    """La evolución del costo del plato (regla #657): por mes, lo vendido en
    barras (las del rango, más fuertes) y el costo por unidad con que se
    vendió en una línea —la foto del POS en cada pedido, regla #557—; el
    costo de HOY punteado; ▼ arriba en los meses en que se editó una de sus
    recetas base (`marcas`, del log del Almacén), ◆ en los que se cambió el
    factor, la unidad o el precio de uno de sus artículos o el descargo del
    plato (`auditoria`, de la auditoría del POS, regla #658) y un círculo
    rojo en los picos (`picos`). El rango de la fecha, sombreado."""
    g = costo_mensual(agg, f["Cod"])
    if g.empty:
        st.info("No se vendió desde enero de 2025, que es desde cuando hay "
                "ventas en la app: no hay costo al vender que mostrar.")
        return
    etq = [_etiqueta_mes(p) for p in g["mes"]]
    en = meses_del_rango(list(g["mes"]), rango)
    sin = g["neto_sin_costo"] > 0
    pos = {m: i for i, m in enumerate(g["mes"])}

    fig = go.Figure(go.Bar(
        x=etq, y=g["unidades"], name="Vendidos",
        marker=dict(color=[LAVANDA_FOCO if e else LAVANDA_BORDE for e in en]),
        # `hovertext` y no `text`: en una barra, `text` se escribe ADENTRO.
        hovertext=[_hover_mes(r) for _, r in g.iterrows()],
        hovertemplate="%{hovertext}<extra></extra>"))
    # El rango, sombreado detrás: en un eje de categorías la posición de
    # cada mes es su índice, y la franja va de medio mes antes a medio
    # después.
    if any(en):
        i0 = en.index(True)
        i1 = len(en) - 1 - en[::-1].index(True)
        fig.add_vrect(x0=i0 - 0.5, x1=i1 + 0.5, fillcolor=LAVANDA_FILA,
                      line_width=0, layer="below")
    _compras_layout(fig, alto=alto)
    paso = max(1, math.ceil(len(etq) / 8))
    fig.update_layout(showlegend=False, bargap=0.35,
                      margin=dict(l=6, r=8, t=24, b=6))
    fig.update_xaxes(type="category", tickangle=0, tickfont=dict(size=10),
                     tickvals=etq[::paso], ticktext=etq[::paso],
                     fixedrange=True)
    tope_u = float(g["unidades"].max() or 1.0)
    fig.update_yaxes(showticklabels=False, fixedrange=True,
                     range=[0, tope_u * 2.4], showgrid=False)

    # El costo va en un eje APARTE, creado después de los `update_*axes`
    # (que tocan todos los ejes que existan, CLAUDE.md § Plotly) y al lado
    # izquierdo: las barras son la escala de abajo y no llevan números.
    cu = g["costo_unit"]
    tope = float(np.nanmax([cu.max() if cu.notna().any() else 0.0,
                            f["Costo"] or 0.0,
                            *[p["pico"] for p in picos]] or [1.0])) or 1.0
    fig.add_trace(go.Scatter(
        x=etq, y=cu, mode="lines+markers", connectgaps=False, yaxis="y2",
        line=dict(color=ACENTO, width=2),
        # Un mes con algo vendido sin costo, en ámbar (regla #556).
        marker=dict(size=7, color=[ADVERTENCIA if s else ACENTO for s in sin]),
        text=[_hover_mes(r) for _, r in g.iterrows()],
        hovertemplate="%{text}<extra></extra>"))
    if not f["SinCosto"]:
        fig.add_trace(go.Scatter(
            x=[etq[0], etq[-1]], y=[float(f["Costo"])] * 2, mode="lines",
            yaxis="y2", line=dict(color=GRIS_TEXTO, width=1, dash="dot"),
            hovertemplate=f"Hoy: S/ {f['Costo']:,.2f}<extra></extra>"))
        fig.add_annotation(x=etq[0], y=float(f["Costo"]), yref="y2",
                           text=f"hoy S/ {f['Costo']:,.2f}", showarrow=False,
                           xanchor="left", yanchor="bottom",
                           font=dict(size=10, color=GRIS_TEXTO))
    # Los picos: un círculo rojo en su mes, a la altura del costo del pico.
    pk = [p for p in picos if pd.Period(p["ini"], freq="M") in pos]
    if pk:
        fig.add_trace(go.Scatter(
            x=[etq[pos[pd.Period(p["ini"], freq="M")]] for p in pk],
            y=[p["pico"] for p in pk], mode="markers", yaxis="y2",
            marker=dict(size=13, color="rgba(0,0,0,0)",
                        line=dict(width=2, color=ERROR)),
            text=[_texto_pico(p) for p in pk],
            hovertemplate="%{text}<extra></extra>"))
    # Las ediciones de sus recetas base: ▼ arriba de todo, una por mes.
    mk = {}
    for m in marcas:
        per = pd.Period(pd.Timestamp(m["t"]), freq="M")
        if per in pos:
            mk.setdefault(per, []).append(m)
    if mk:
        fig.add_trace(go.Scatter(
            x=[etq[pos[p]] for p in mk], y=[tope * 1.18] * len(mk),
            mode="markers", yaxis="y2",
            marker=dict(symbol="triangle-down", size=10, color=ACENTO_TEXTO),
            text=["<br>".join(_texto_marca(m) for m in ms[:4])
                  + (f"<br>y {len(ms) - 4} más" if len(ms) > 4 else "")
                  for ms in mk.values()],
            hovertemplate="%{text}<extra></extra>"))
    # Los cambios de la auditoría: ◆ debajo de los ▼, una por mes.
    ma = {}
    for c in auditoria:
        per = pd.Period(pd.Timestamp(c["t"]), freq="M")
        if per in pos:
            ma.setdefault(per, []).append(c)
    if ma:
        fig.add_trace(go.Scatter(
            x=[etq[pos[p]] for p in ma], y=[tope * 1.08] * len(ma),
            mode="markers", yaxis="y2",
            marker=dict(symbol="diamond", size=9, color=ADVERTENCIA),
            text=["<br>".join(_texto_cambio(c) for c in cs[:4])
                  + (f"<br>y {len(cs) - 4} más" if len(cs) > 4 else "")
                  for cs in ma.values()],
            hovertemplate="%{text}<extra></extra>"))
    fig.update_layout(
        hoverlabel=dict(align="left"),
        yaxis2=dict(overlaying="y", side="left", showticklabels=True,
                    tickprefix="S/ ", tickformat=",.2f" if tope < 20 else ",.0f",
                    tickfont=dict(size=10), automargin=True, fixedrange=True,
                    range=[0, tope * 1.28], showgrid=True,
                    gridcolor=GRIS_CUADRICULA, zeroline=False))
    st.plotly_chart(fig, use_container_width=True,
                    key=f"rec_carta_evo_{f['Cod']}",
                    config={"displaylogo": False, "displayModeBar": False})

    con = g[cu.notna()]
    pie = []
    if len(con) >= 2:
        a, b = con.iloc[0], con.iloc[-1]
        var = (b["costo_unit"] / a["costo_unit"] - 1) * 100 if a["costo_unit"] else 0.0
        pie.append(f"De S/ {a['costo_unit']:,.2f} ({_etiqueta_mes(a['mes'])}) a "
                   f"S/ {b['costo_unit']:,.2f} ({_etiqueta_mes(b['mes'])}): "
                   f"{'+' if var >= 0 else '−'}{abs(var):.1f} %, el costo que "
                   "guardó el POS al vender.")
    if any(en):
        pie.append("Sombreado: el rango de la fecha.")
    if f["Tipo"] == "Combo" and (g["mes"] < _COMBO_ANTES).any():
        pie.append("Hasta setiembre de 2025 el POS registró los platos de los "
                   "combos entre 8 y 32 % más baratos que sueltos.")
    if pie:
        st.caption(" ".join(pie))


def _texto_marca(m):
    signo = "+" if m["esp"] >= 0 else "−"
    quien = f" · {m['usr']}" if m.get("usr") else ""
    otros = m.get("n", 1) - 1
    mas = (f" (y {otros} {'cambio' if otros == 1 else 'cambios'} más)"
           if otros > 0 else "")
    return (f"▼ {pd.Timestamp(m['t']):%d/%m/%y}{quien} · {escape(m['base'])}: "
            f"{escape(m['txt'])}{mas} → {signo}S/ {abs(m['esp']):,.2f} por plato")


def _texto_cambio(c):
    """Un cambio de la auditoría del POS, en una línea (regla #658)."""
    quien = f" · {c['usr']}" if c.get("usr") else ""
    veces = (f" (×{c['veces']:,.0f} si su receta no cambió)"
             if c.get("veces") and c["veces"] >= 2 else "")
    return (f"◆ {pd.Timestamp(c['t']):%d/%m/%y}{quien} · {escape(c['nombre'])}: "
            f"{escape(c['txt'])}{veces}")


def _texto_pico(p):
    dias = (f"{p['ini']:%d/%m/%y}" if p["ini"] == p["fin"]
            else f"del {p['ini']:%d/%m} al {p['fin']:%d/%m/%y}")
    t = (f"<b>Pico {dias}</b><br>S/ {p['pico']:,.2f} por unidad (lo habitual, "
         f"S/ {p['normal']:,.2f})<br>{p['unid']:,.0f} vendidos: "
         f"S/ {p['exceso']:,.0f} de costo de más")
    if p.get("causa"):
        t += "<br>" + escape(p["causa"])
    return t


def _lista_en_rango(marcas, picos, rango, auditoria=()):
    """Debajo del gráfico, con palabras: lo que movió el costo EN el rango —
    las ediciones de sus recetas base, los cambios de sus artículos en la
    auditoría del POS y los picos con su posible causa—."""
    if rango is None:
        return
    a = pd.Timestamp(rango[0])
    b = pd.Timestamp(rango[1]) + pd.Timedelta(days=1)
    ms = [m for m in marcas if a <= pd.Timestamp(m["t"]) < b]
    cs = [c for c in auditoria if a <= pd.Timestamp(c["t"]) < b]
    ps = [p for p in picos if a <= p["ini"] < b]
    if not (ms or cs or ps):
        return
    filas = []
    for m in ms[-6:][::-1]:
        filas.append(f'<li class="rec-evo-marca">{_texto_marca(m)}</li>')
    for c in cs[-6:][::-1]:
        filas.append(f'<li class="rec-evo-cambio">{_texto_cambio(c)}</li>')
    for p in ps[::-1]:
        dias = (f"{p['ini']:%d/%m}" if p["ini"] == p["fin"]
                else f"{p['ini']:%d/%m}–{p['fin']:%d/%m}")
        causa = f" {escape(p['causa'])}" if p.get("causa") else ""
        filas.append(f'<li class="rec-evo-pico">● {dias}: S/ {p["pico"]:,.2f} por '
                     f'unidad (lo habitual, S/ {p["normal"]:,.2f}), S/ '
                     f'{p["exceso"]:,.0f} de más.{causa}</li>')
    extra = (f'<li class="rec-evo-marca">y {len(ms) - 6} ediciones más</li>'
             if len(ms) > 6 else "")
    if len(cs) > 6:
        extra += f'<li class="rec-evo-cambio">y {len(cs) - 6} cambios más</li>'
    st.markdown(f'<ul class="rec-evo-lista">{"".join(filas)}{extra}</ul>',
                unsafe_allow_html=True)


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


def ultimo_porcionamiento(df_po, cod):
    """El porcionamiento más nuevo del que salió `cod`: `doc`, `fecha`,
    `cod_de` (el código de lo que se porcionó) y, si se puede medir, si el
    peso por unidad de ESTE corte quedó fuera de lo habitual — la marca
    «Peso por unidad raro» de Movimientos › Para revisar (regla #647), con
    `kgu` (su peso por unidad) y `hab` (lo habitual). Importa: el corte
    entra al Almacén al precio que le dio ese peso, y la receta lo hereda.
    None si no hay porcionamientos. Pura."""
    if df_po is None or df_po.empty:
        return None
    c = {k: _resolver(df_po, [k]) for k in (
        "COD PORC", "COD PROD FINAL", "FEC REGIST", "COD PROD INIC",
        "UNID PROD INIC", "PROD FINAL RESULT", "CANT A PORCIONAR",
        "CANT MERMA", "CANT RESULT", "PESO RESULT")}
    if not (c["COD PROD FINAL"] and c["FEC REGIST"]):
        return None
    d = df_po[df_po[c["COD PROD FINAL"]].astype(str).str.strip() == str(cod).strip()]
    if d.empty:
        return None
    d = (d.assign(_f=pd.to_datetime(d[c["FEC REGIST"]], errors="coerce"))
         .sort_values("_f", kind="stable"))
    ult = d.iloc[-1]
    out = {"doc": str(ult[c["COD PORC"]]).strip() if c["COD PORC"] else "",
           "fecha": ult["_f"],
           "cod_de": (str(ult[c["COD PROD INIC"]]).strip()
                      if c["COD PROD INIC"] else ""),
           "raro": False, "kgu": float("nan"), "hab": float("nan")}
    if not all(c[k] for k in ("COD PROD INIC", "CANT RESULT", "PESO RESULT",
                              "CANT A PORCIONAR", "CANT MERMA")):
        return out
    try:
        from graficos.movimientos_merma import (
            en_kilos, fuera_de_lo_habitual, gramos_del_nombre,
            habitual_previo)
    except ImportError:
        # Un `graficos` viejo en Cloud hasta el «Reboot app» (regla #357):
        # sin la marca, no sin la vista.
        return out
    q = pd.to_numeric(d[c["CANT RESULT"]], errors="coerce")
    w = pd.to_numeric(d[c["PESO RESULT"]], errors="coerce")
    d = d.assign(_kgu=w / q)[(q > 0) & (w > 0)]
    if d.empty or d.index[-1] != ult.name:
        return out
    hab = habitual_previo(d["_kgu"], d[c["COD PROD INIC"]].astype(str).str.strip())
    gramos = pd.Series(float("nan"), index=d.index)
    if c["PROD FINAL RESULT"] and c["UNID PROD INIC"]:
        gramos = gramos_del_nombre(d[c["PROD FINAL RESULT"]]).where(
            en_kilos(d[c["UNID PROD INIC"]]))
    raro = fuera_de_lo_habitual(d["_kgu"], hab, gramos)
    i = d.index[-1]
    # Como en «Para revisar»: si con el peso habitual la merma sale
    # imposible, lo habitual no le sirve a ese porcionamiento.
    cant = pd.to_numeric(ult[c["CANT A PORCIONAR"]], errors="coerce")
    merma = pd.to_numeric(ult[c["CANT MERMA"]], errors="coerce")
    corr = ((merma + w[i] - q[i] * hab[i]) / cant
            if cant and cant > 0 else float("nan"))
    out.update(kgu=float(d.at[i, "_kgu"]), hab=float(hab[i]),
               raro=bool(raro[i]) and bool(0 <= corr < 1))
    return out


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


def _cant(v, unid):
    return f"{v:,.3f}".rstrip("0").rstrip(".") + (f" {unid.lower()}" if unid else "")


def _reciente(df_po, fecha, dias=30):
    """Si `fecha` cae en los últimos `dias` días con porcionamientos: el
    rango con que abre «Para revisar». Un salto a uno más viejo llegaría a
    una lista que no lo tiene."""
    c = _resolver(df_po, ["FEC REGIST"])
    if not c or pd.isna(fecha):
        return False
    tope = pd.to_datetime(df_po[c], errors="coerce").max()
    return bool(fecha >= tope.normalize() - pd.Timedelta(days=dias - 1))


def _saltar_a_movimientos(destino, ult, cod):
    """Deja escrito a dónde se va y pide la corrida COMPLETA que cambia de
    reporte: el botón vive en el fragment de la sección, y una corrida de
    fragment no vuelve a elegir reporte (regla #647). Con un `graficos`
    viejo en Cloud (regla #357), no hace nada."""
    try:
        import navegacion
        from graficos import movimientos_merma as mm
        if destino == "rev":
            mm.ir_a_revisar(ult["doc"])
            vista = mm.VISTA_REV
        else:
            mm.ir_al_corte(ult["cod_de"], cod)
            vista = mm.VISTA_REND
        navegacion._ir_a_vista("Movimientos", mm.RAIL_MOVIMIENTOS, vista)
    except (ImportError, AttributeError):
        return
    st.rerun(scope="app")


def _tabla_porcionamientos(po, actual, ult=None):
    """Los últimos porcionamientos del insumo abierto (regla #574). No se
    clica: el producto de origen es de otro porcionamiento o de una compra,
    y el costo se lee acá. El más nuevo va en rojo si su peso por unidad
    quedó fuera de lo habitual (`ultimo_porcionamiento`, regla #647).
    Los formatos van en el Styler, no en `column_config`: con un Styler,
    el que manda es el Styler."""
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
    raro = bool(ult and ult["raro"] and po["Fecha"].iloc[0] == ult["fecha"])
    sty = (v.style.format({"Merma": "{:.0f}%", "Costo u.": "S/ {:,.2f}"})
           .apply(lambda r: ([f"color: {ERROR}; font-weight: 600"] * len(r)
                             if raro and r.name == 0 else [""] * len(r)),
                  axis=1))
    st.dataframe(sty, hide_index=True, row_height=27,
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
                     "Merma": st.column_config.Column(
                         width=50,
                         help="Merma del porcionamiento, sobre lo porcionado"),
                     "Costo u.": st.column_config.Column(
                         width=66,
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
        return ventas()


_K_SIM_ABIERTO = "rec_carta_sim_abierto"
"""El código del plato cuyo simulador está abierto (regla #656). Lo escribe
el botón «Simular» y lo borra cualquier cierre de la modal: sin borrarlo, la
corrida siguiente —un clic en la tabla— la volvería a abrir."""


def _abrir_simulador(cod):
    st.session_state[_K_SIM_ABIERTO] = cod


def _cerrar_simulador():
    st.session_state[_K_SIM_ABIERTO] = None


def _modal_simulador(cod, nombre, precio, df_rv):
    """El simulador del plato en una modal ancha (`st.dialog`), como la ficha
    de Documentos SUNAT (regla #587): la página queda detrás y la ✕, Esc o un
    clic afuera la cierran. El título va por plato, así que el decorador se
    aplica acá. `una_vez_por_corrida` porque una modal es un fragment, y ésta
    se llama dentro del de `seccion_perezosa` (regla #456)."""
    def _contenido():
        with st.container(key="rec_sim_modal"):
            simular_plato(cod, nombre, precio, df_rv)

    una_vez_por_corrida(st.dialog(f"Simular · {nombre}", width="large",
                                  on_dismiss=_cerrar_simulador)(_contenido))()


# ─── La fecha de la tarjeta (regla #657) ──────────────────────────────────
def ctx_fecha(agg, hoy=None):
    """El `ctx` del panel de fecha de la tarjeta: Recetas no tiene fecha en
    la franja (`app.py` no publica uno), así que se arma acá con los topes de
    lo VENDIDO —primer y último día con venta— y su default, los últimos 3
    meses. Con el mismo dict el botón escribe y la vista lee: la clave es
    `estado_rango.clave_rango("Recetas", False, "carta")`. None sin ventas.
    Pura salvo por la fecha de hoy."""
    if agg is None or agg.empty or "dia" not in agg.columns:
        return None
    dias = pd.to_datetime(agg["dia"], errors="coerce").dropna()
    if dias.empty:
        return None
    fmin, fmax = dias.min().date(), dias.max().date()
    hoy = hoy or datetime.date.today()
    defecto = next((r for c, _n, _g, r in atajos_tarjeta(min(fmax, hoy), (fmin, fmax))
                    if c == ATAJO_INICIAL), (fmin, fmax))
    return {"k_rango": clave_rango("Recetas", False, CATEGORIA_FECHA),
            "fecha_min": fmin, "fecha_max": fmax, "reporte": "Recetas",
            "usa_carga_rango": False, "hoy": hoy, "rango_default": defecto,
            "rango_default_cat": {CATEGORIA_FECHA: defecto}}


# ─── El log de las recetas base (regla #657) ──────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def _ediciones_cacheable(sello_m, sello_d, sello_rb, version=sr.VERSION):
    """Las ediciones de las recetas base (`simulador_receta.ediciones_base`):
    ~6 s sobre el log entero, por eso en caché por los tres sellos."""
    mlog = _cargar_cacheable(sr.ARCHIVO_LOG, sello_m)
    dlog = _cargar_cacheable(sr.ARCHIVO_LOG_DET, sello_d)
    return sr.ediciones_base(mlog, dlog, cargar("recetabase.parquet"))


def ediciones_bases():
    """Las ediciones de las recetas base, o None si el log no está en R2 —
    faltan las filas `recetabaselog` y `recetabaselogdet` del Sheet—, no hay
    secrets (modo demo) o la lectura falla: la vista sigue sin las marcas.
    Se pregunta el sello ANTES de leer: `data.cargar` de un parquet que no
    existe pinta un error en pantalla."""
    if not secrets_disponibles():
        return None
    s_m, s_d = sello_datos(sr.ARCHIVO_LOG), sello_datos(sr.ARCHIVO_LOG_DET)
    if not (s_m and s_d):
        return None
    try:
        return _ediciones_cacheable(s_m, s_d, sello_datos("recetabase.parquet"))
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def _auditoria_cacheable(sello, version=sr.VERSION):
    """La auditoría limpia (`simulador_receta.cambios_auditoria`): ~1,5 s
    sobre las ~4.200 filas, en caché por su sello."""
    return sr.cambios_auditoria(_cargar_cacheable(sr.ARCHIVO_AUDITORIA, sello))


def cambios_auditoria():
    """Los cambios de la auditoría del POS (regla #658), o None si la fila
    `auditoriacostos` del Sheet todavía no llegó a R2, no hay secrets o la
    lectura falla: la ficha sigue sin ellos. El sello, ANTES de leer, por lo
    mismo que `ediciones_bases`."""
    if not secrets_disponibles():
        return None
    sello = sello_datos(sr.ARCHIVO_AUDITORIA)
    if not sello:
        return None
    try:
        return _auditoria_cacheable(sello)
    except Exception:
        return None


# ─── La ficha del plato elegido (regla #657) ──────────────────────────────
def _receta_para_sankey(df_rv, cod):
    """La receta del parquet, como la lee el Sankey (Insumo, Costo…)."""
    c = columnas_receta(df_rv)
    if df_rv is None or not c["cod"]:
        return None
    return _receta_original(df_rv, str(cod), c["cod"], c["ins"], c["cant"],
                            c["total"], c["cod_ins"], c["factor"])


def _porcionados(nodos):
    """Los cortes porcionados del árbol, cada uno una vez: `{cod: nodo}`."""
    acc = {}

    def bajar(n):
        if n.get("hijos"):
            for h in n["hijos"]:
                bajar(h)
        elif n.get("porc"):
            acc.setdefault(n["cod"], n)
    for n in nodos:
        bajar(n)
    return acc


def _vista_porcionados(porcs, df_po):
    """Los últimos porcionamientos de un corte del plato (regla #574), con
    los saltos a Movimientos (regla #647). Elegido en un desplegable: en el
    árbol, un corte no se clica."""
    cods = list(porcs)
    if st.session_state.get(_K_PORC) not in cods:
        st.session_state[_K_PORC] = cods[0]
    with st.container(horizontal=True, vertical_alignment="center",
                      key="rec_carta_base_hdr"):
        with st.container(key="rec_carta_det_modo", width="content"):
            cod = st.selectbox("Corte", cods, key=_K_PORC,
                               label_visibility="collapsed", width=230,
                               format_func=lambda c: porcs[c]["ins"])
        po = porcionamientos_de(df_po, cod)
        ult = ultimo_porcionamiento(df_po, cod) if not po.empty else None
        if ult and ult["cod_de"]:
            if st.button("Ver curva", key="rec_carta_base_curva",
                         help="La curva de su precio, porcionamiento por "
                              "porcionamiento, y qué la movió —el insumo, la "
                              "merma o el gramaje—, en Movimientos › "
                              "Rendimiento."):
                _saltar_a_movimientos("rend", ult, cod)
            if ult["raro"] and _reciente(df_po, ult["fecha"]):
                if st.button(
                        "Revisar", key="rec_carta_base_revisar",
                        help=f"PO-{ult['doc']} ({ult['fecha']:%d/%m/%y}) le "
                             f"asignó {ult['kgu']:,.3f} por unidad y lo "
                             f"habitual es {ult['hab']:,.3f}: su costo, y el "
                             "de esta receta, pueden estar mal. Verlo en "
                             "Movimientos › Para revisar."):
                    _saltar_a_movimientos("rev", ult, cod)
    n = porcs[cod]
    actual = {"costo": float(n["costo"]),
              "escala": float(n["cant"]) / float(n["factor"] or 1.0)}
    _tabla_porcionamientos(po, actual, ult)


def _cabecera_ficha(f):
    """El renglón del nombre de la ficha de abajo: el plato y de dónde es.
    Las cifras, los canales y «Simular» van en la ficha de la pieza, al
    costado de la lista (regla #696)."""
    ruta_txt = " › ".join(x for x in (f["Grupo"], f["Subgrupo"]) if x)
    with st.container(horizontal=True, vertical_alignment="center",
                      key="rec_carta_plato_hdr"):
        st.markdown(
            f'<p class="chart-card-hdr">{escape(str(f["Producto"]))} '
            f'<span class="rec-ficha-ruta">{escape(ruta_txt)} · '
            f'{escape(f["Tipo"])} · receta y evolución</span></p>',
            unsafe_allow_html=True)


def _ficha(f, df_rv, agg, rango, porcionamientos=None):
    """Debajo de la tabla (regla #657): el plato elegido. A la izquierda su
    receta como árbol —o lo que descarga, si no tiene—; a la derecha la
    evolución de su costo, la dona Costo/Utilidad, el Sankey o sus
    porcionados. «Simular» abre la modal de la regla #656."""
    cod, nombre = str(f["Cod"]), str(f["Producto"])
    es_receta = f["Tipo"] == "Receta"
    df_po = porcionamientos() if callable(porcionamientos) else porcionamientos
    with st.container(key="rec_carta_plato"):
        _cabecera_ficha(f)
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
                f'<p class="rec-ficha-aviso">S/ {sin_costo_neto:,.0f} de lo '
                f'vendido en el rango entró al FoodCost con costo 0: {causa}, '
                'y así queda guardado.</p>', unsafe_allow_html=True)
        if es_receta and st.session_state.get(_K_SIM_ABIERTO) == cod:
            _modal_simulador(cod, nombre, float(f["Precio"]), df_rv)
        nodos = []
        # columnas-internas: la receta | su evolución, adentro de la ficha
        # del plato (regla #657); no parte la página.
        c_rec, c_evo = st.columns(list(PROPORCION_FICHA), gap="medium")
        with c_rec:
            if es_receta:
                with st.container(key="rec_carta_arbol"):
                    nodos = receta_lectura(cod, df_rv)
            else:
                _descarga(f)
        ediciones = ediciones_bases() if nodos else None
        # Sin las que no movieron el plato ni un céntimo: un ▼ que dice
        # «+S/ 0,00» es ruido.
        marcas = [m for m in (sr.marcas_plato(nodos, ediciones) if ediciones else [])
                  if abs(m["esp"]) >= 0.01]
        cambios = cambios_auditoria()
        picos = sr.picos_plato(agg, cod, nodos, df_po, cambios=cambios)
        auditoria = sr.cambios_del_plato(cambios, nodos, cod)
        porcs = _porcionados(nodos)
        with c_evo:
            with st.container(key="rec_carta_evo"):
                opciones = ["Evolución", "Costo / Utilidad", "Sankey"]
                if porcs and df_po is not None:
                    opciones.append("Porcionados")
                if st.session_state.get(_K_FICHA_VISTA) not in opciones:
                    st.session_state[_K_FICHA_VISTA] = opciones[0]
                # NO `st.tabs`: dibuja todas y esconde las otras, y un gráfico
                # escondido mide 0 (regla #500).
                vista = st.segmented_control(
                    "Vista", opciones, key=_K_FICHA_VISTA,
                    label_visibility="collapsed") or opciones[0]
                if vista == "Evolución":
                    _dib_evolucion(f, agg, rango, marcas, picos, auditoria)
                    _lista_en_rango(marcas, picos, rango, auditoria)
                    faltan = []
                    if es_receta and ediciones is None:
                        faltan.append("las ediciones de sus recetas base (filas "
                                      "«recetabaselog» y «recetabaselogdet»)")
                    if cambios is None:
                        faltan.append("los cambios de factor y unidad de la "
                                      "auditoría del POS (fila «auditoriacostos»)")
                    if faltan:
                        st.caption("Sin " + " ni ".join(faltan) + ": todavía "
                                   "no están en R2. Se agregan en el Sheet.")
                elif vista == "Sankey":
                    r = _receta_para_sankey(df_rv, cod) if es_receta else None
                    if r is None:
                        st.info("Sin receta no hay Sankey: el Sankey reparte "
                                "el costo entre los insumos de la receta.")
                    else:
                        _dib_sankey_insumo_costo(r, nombre, cod,
                                                 alto=alturas.CARTA_EVOLUCION)
                elif vista == "Porcionados":
                    _vista_porcionados(porcs, df_po)
                elif f["SinCosto"]:
                    # Sin costo, la dona dibujaría «0 % de costo» y toda la
                    # porción como utilidad: una cifra que no existe.
                    st.info("Sin costo cargado: no hay cómo repartir el "
                            "precio entre costo y utilidad.")
                else:
                    _dib_torta_costo_utilidad(f["Neto"], f["Costo"], f["Pct"],
                                              cod, alto=alturas.CARTA_EVOLUCION)


# ─── La pieza propia (regla #696) ─────────────────────────────────────────
_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "carta_costeada",
    css=(_AQUI / "carta_costeada.css").read_text(encoding="utf-8"),
    # El Excel (`libro`, `bajar`) vive en `_xlsx.js`, compartido con
    # «Consistencia de datos»: se antepone, y queda en el mismo módulo.
    js=(_AQUI / "_xlsx.js").read_text(encoding="utf-8")
    + (_AQUI / "carta_costeada.js").read_text(encoding="utf-8"),
)

_K_PIEZA = "rec_carta_pieza"

AYUDA = ("% costo = costo de HOY (receta × precio de hoy) ÷ precio neto del "
         "canal (precio ÷ 1,235, como el sistema). Margen = neto − costo. "
         "«Vendido» = el costo que guardó el POS en cada pedido del rango ÷ su "
         "venta neta, por la fecha del comprobante y con las notas de crédito "
         "restando: puede no ser el de hoy, e incluye lo vendido sin costo. "
         "En los combos, el costo lo calcula la consulta del Sheet con las "
         "cantidades de su ficha (mirá «Combos»). Para conciliar con "
         "Inforest: Ventas › Venta por Periodo › Cuadre.")


_BANDA = ["Minimo", "Promedio", "Esperado", "Maximo", "Real90", "Vendidos90"]
"""La banda de un combo, en el orden en que la pieza la muestra (regla #548):
lo que vale con cada forma de elegir, y lo servido de verdad en 90 días."""


def ventas_por_canal(otros, rango):
    """{código: {índice de canal: [unidades, neto, costo]}} de lo vendido en
    el rango por los canales que NO son «En el Local»
    (`data.venta_por_canal_dia`); el principal sale restando del total.
    Pura."""
    if otros is None or otros.empty or rango is None:
        return {}
    dia = pd.to_datetime(otros["dia"])
    ini, fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    u = otros[(dia >= ini) & (dia < fin + pd.Timedelta(days=1))]
    idx = {n: i for i, (n, _) in enumerate(CANALES)}
    u = u[u["canal"].isin(idx)]
    if u.empty:
        return {}
    g = u.groupby(["producto", "canal"], as_index=False)[["unidades", "neto", "costo"]].sum()
    out = {}
    for r in g.itertuples(index=False):
        out.setdefault(str(r.producto).strip(), {})[str(idx[r.canal])] = [
            round(float(r.unidades), 3), round(float(r.neto), 2), round(float(r.costo), 2)]
    return out


def _f(v, dec=4):
    return round(float(v), dec) if pd.notna(v) else 0.0


def _iso(v):
    return "" if pd.isna(v) or v <= _SIN_FECHA else f"{v:%Y-%m-%d}"


def armar_pieza(t, rango, por_canal, sel, n_sin_precio=0):
    """Lo que recibe la pieza: una fila por producto —con los inactivos y
    la venta interna, que la pieza esconde de entrada— con sus cinco
    canales, lo vendido en el rango y, en los combos, su banda. Pura: la
    lee el test.

    Fila: [código, grupo, subgrupo, producto, tipo, activo, oferta (1
    impresa, 0 no impresa, −1 sin dato), descarga, receta guardada, última
    venta, [precio por canal], [costo por canal], vendidos, venta neta,
    costo vendido, vendido sin costo, combo o None, {canal: [unidades,
    neto, costo]} fuera de «En el Local»]."""
    filas = []
    for r in t.itertuples(index=False):
        combo = None
        if r.Tipo == "Combo":
            combo = [r.TipoCombo, r.Metodo, *(_f(getattr(r, c), 2) for c in _BANDA)]
        oferta = {OFERTAS[0]: 1, OFERTAS[1]: 0}.get(r.Oferta, -1)
        filas.append([
            str(r.Cod), r.Grupo, r.Subgrupo, r.Producto, r.Tipo, int(bool(r.Activo)),
            oferta, r.Descarga, _iso(getattr(r, "Actualizado", pd.NaT)), _iso(r.UltimaVenta),
            [_f(getattr(r, f"Precio{i}"), 2) for i in range(len(CANALES))],
            [_f(getattr(r, f"Costo{i}")) for i in range(len(CANALES))],
            _f(getattr(r, "Vendidos", 0.0), 3), _f(getattr(r, "VendidoNeto", 0.0), 2),
            _f(getattr(r, "CostoVendido", 0.0), 2), _f(getattr(r, "SinCostoNeto", 0.0), 2),
            combo, por_canal.get(str(r.Cod).strip()),
        ])
    usados = [0.0] * len(CANALES)
    for f in filas:
        otros = f[17] or {}
        for k, (u, _n, _c) in otros.items():
            usados[int(k)] += u
        usados[0] += f[12] - sum(u for u, _n, _c in otros.values())
    return {
        "filas": filas,
        "canales": [[n, round(u)] for (n, _), u in zip(CANALES, usados)],
        "divisor": divisor_neto(),
        "rango": (f"{rango[0]:%d/%m/%Y} – {rango[1]:%d/%m/%Y}" if rango else ""),
        "sel": sel, "sin_precio": int(n_sin_precio),
        "umbrales": [_UMBRAL_COSTO_OK, _UMBRAL_COSTO_WARN],
        "grupo_vi": GRUPO_VENTA_INTERNA, "ayuda": AYUDA,
    }


def render_carta_costeada(df, df_rv=None, ventas=None, df_rb=None,
                          porcionamientos=None, ventas_canal=None):
    """La vista entera (regla #696): UNA tarjeta con la PIEZA PROPIA
    —indicadores, filtros, la lista y la ficha del elegido con sus cinco
    canales— y, debajo, la receta y la evolución del elegido (regla #657).
    `df` es `cartacosteada.parquet` (o None si no se pudo cargar); `df_rv`,
    recetaventa.parquet (las recetas y su fecha); `ventas`, lo vendido por
    producto y día, o la FUNCIÓN que lo carga (`data.venta_por_producto_dia`,
    regla #573); `ventas_canal`, lo vendido fuera de «En el Local» o la
    función que lo carga (`data.venta_por_canal_dia`); `df_rb`, por la firma
    del dispatcher; `porcionamientos`, el parquet o la función que lo carga
    (regla #574).

    Todo lo que se elige en la lista —canal, grupo, tipo, buscar, orden, el
    Excel— lo resuelve el navegador: la pieza recibe la carta entera (con
    inactivos y venta interna) y no pide una corrida. Sólo elegir un
    producto o «Simular» vuelven a Python, que dibuja la ficha de abajo."""
    ss = st.session_state
    with st.container(border=True, key="rec_card_carta"):
        cab = st.container(horizontal=True, gap="small",
                           vertical_alignment="center", key="rec_carta_cab")
        with cab:
            st.markdown('<p class="chart-card-hdr">Costo de Carta</p>',
                        unsafe_allow_html=True)
        if df is None or df.empty:
            st.info("Todavía no hay datos de la carta costeada "
                    f"({ARCHIVO}). Se genera con la consulta «cartacosteada» del "
                    "Sheet: aparece después del próximo refresco.")
            return

        carta, n_sin_precio = preparar(df, incluir_inactivos=True)
        fechas = fechas_de_receta(df_rv)
        carta["Actualizado"] = pd.to_datetime(
            carta["Cod"].map(fechas), errors="coerce").fillna(_SIN_FECHA)
        agg = _lo_vendido(ventas)
        ctx = ctx_fecha(agg)
        if ctx is not None:
            with cab:
                with st.container(key="rec_carta_cab_fecha", width="content"):
                    selector_fecha_tarjeta("rec_carta_f", None,
                                           categoria=CATEGORIA_FECHA, ctx=ctx)
        rango = rango_tarjeta(CATEGORIA_FECHA, ctx) if ctx is not None else None
        carta, rango = con_ventas(carta, agg, rango=rango)
        otros = ventas_canal() if callable(ventas_canal) else ventas_canal
        por_canal = ventas_por_canal(otros, rango)

        # El elegido: el último clic; si no, lo más vendido de la carta activa.
        visibles = carta[carta["Activo"]
                         & (carta["Grupo"].str.casefold() != GRUPO_VENTA_INTERNA.casefold())]
        sel = ss.get(_K_FOCO)
        if sel not in set(carta["Cod"]):
            base = visibles if not visibles.empty else carta
            sel = str(base.sort_values("VendidoNeto", ascending=False)["Cod"].iloc[0])

        def _al_elegir():
            v = (ss.get(_K_PIEZA) or {}).get("elegir")
            if v:
                ss[_K_FOCO] = str(v)

        def _al_simular():
            v = (ss.get(_K_PIEZA) or {}).get("simular")
            if v:
                ss[_K_FOCO] = str(v)
                _abrir_simulador(str(v))

        _PIEZA(key=_K_PIEZA, data=armar_pieza(carta, rango, por_canal, sel, n_sin_precio),
               on_elegir_change=_al_elegir, on_simular_change=_al_simular,
               width="stretch")
        f = carta[carta["Cod"] == sel]
        if not f.empty:
            _ficha(f.iloc[0], df_rv, agg, rango, porcionamientos)
