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

from graficos.movil import css_movil, js_movil
import datetime
import re

import numpy as np
from pathlib import Path

import pandas as pd
import streamlit as st

import simulador_receta as sr
from cortes import MESES_ABR_ES
from data import _cargar_cacheable, cargar, secrets_disponibles, sello_datos
from estado_rango import atajos_tarjeta, clave_rango
from graficos import alturas
from graficos.base import (_resolver,
                           rango_tarjeta, selector_fecha_tarjeta,
                           una_vez_por_corrida)
from graficos.recetas_comun import divisor_neto
from graficos.simulador_plato import armar_arbol, simular_plato
from graficos.ventas_mix import pct_costo
from tema import (ADVERTENCIA_TEXTO, ERROR)
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


def _texto_marca(m):
    """Una edición de una receta base, en una línea de texto llano (la pieza
    la escapa)."""
    signo = "+" if m["esp"] >= 0 else "−"
    quien = f" · {m['usr']}" if m.get("usr") else ""
    otros = m.get("n", 1) - 1
    mas = (f" (y {otros} {'cambio' if otros == 1 else 'cambios'} más)"
           if otros > 0 else "")
    return (f"{pd.Timestamp(m['t']):%d/%m/%y}{quien} · {m['base']}: "
            f"{m['txt']}{mas} → {signo}S/ {abs(m['esp']):,.2f} por plato")


def _texto_cambio(c):
    """Un cambio de la auditoría del POS, en una línea (regla #658)."""
    quien = f" · {c['usr']}" if c.get("usr") else ""
    veces = (f" (×{c['veces']:,.0f} si su receta no cambió)"
             if c.get("veces") and c["veces"] >= 2 else "")
    return (f"{pd.Timestamp(c['t']):%d/%m/%y}{quien} · {c['nombre']}: "
            f"{c['txt']}{veces}")


def _texto_pico(p):
    dias = (f"el {p['ini']:%d/%m/%y}" if p["ini"] == p["fin"]
            else f"del {p['ini']:%d/%m} al {p['fin']:%d/%m/%y}")
    t = (f"Pico {dias}: S/ {p['pico']:,.2f} por plato (lo habitual, "
         f"S/ {p['normal']:,.2f}), {p['unid']:,.0f} vendidos, "
         f"S/ {p['exceso']:,.0f} de costo de más.")
    if p.get("causa"):
        t += " " + str(p["causa"])
    return t


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
    «Peso por unidad raro» de Producción › Para revisar (regla #647), con
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


def _reciente(df_po, fecha, dias=30):
    """Si `fecha` cae en los últimos `dias` días con porcionamientos: el
    rango con que abre «Para revisar». Un salto a uno más viejo llegaría a
    una lista que no lo tiene."""
    c = _resolver(df_po, ["FEC REGIST"])
    if not c or pd.isna(fecha):
        return False
    tope = pd.to_datetime(df_po[c], errors="coerce").max()
    return bool(fecha >= tope.normalize() - pd.Timedelta(days=dias - 1))


def _preparar_salto(destino, ult, cod):
    """Deja escrito a dónde se va (regla #647): Producción › Rendimiento en
    el corte (`rend`) o Para revisar en su porcionamiento (`rev`). El salto
    lo hace la corrida COMPLETA que pide quien llama: la ficha vive en el
    fragment de la sección, y una corrida de fragment no vuelve a elegir
    reporte. Con un `graficos` viejo en Cloud (regla #357), no hace nada y
    devuelve False."""
    try:
        import navegacion
        from graficos import movimientos_merma as mm
        from navegacion_retorno import capturar_origen
        capturar_origen()
        if destino == "rev":
            mm.ir_a_revisar(ult["doc"])
            vista = mm.VISTA_REV
        else:
            mm.ir_al_corte(ult["cod_de"], cod)
            # Rendimiento es una perspectiva de «Porcionamientos» (#712).
            st.session_state[mm.K_PERSP_PORC] = mm.PERSPECTIVAS_PORC[1][0]
            vista = mm.VISTA_PORC
        navegacion._ir_a_vista(mm.REPORTE_MERMA, mm.RAIL_PRODUCCION, vista)
    except (ImportError, AttributeError):
        return False
    return True


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


def _modal_simulador(cod, nombre, precio, df_rv, estado=None):
    """El simulador del plato en una modal ancha (`st.dialog`), como la ficha
    de Documentos SUNAT (regla #587): la página queda detrás y la ✕, Esc o un
    clic afuera la cierran. El título va por plato, así que el decorador se
    aplica acá. `una_vez_por_corrida` porque una modal es un fragment, y ésta
    se llama dentro del de `seccion_perezosa` (regla #456)."""
    def _contenido():
        with st.container(key="rec_sim_modal"):
            simular_plato(cod, nombre, precio, df_rv, estado=estado)

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


# ─── La ficha del plato elegido: una pieza propia (regla #744) ────────────
# Debajo de la lista, el plato elegido: cabecera con «Simular» y «Copiar
# receta a Nuevo Costeo», cinco indicadores, «Qué mueve el costo de hoy»,
# la receta como lista con barras y, al costado, Evolución | Costo y
# utilidad | Reparto del precio | Porcionados. Hasta esa regla eran el árbol
# de `simulador_plato` en modo lectura, una figura de Plotly, la dona, el
# Sankey de `recetaventa` y un `st.dataframe` con un desplegable (#657). Las
# cuentas siguen acá (`costo_mensual`, `porcionamientos_de`,
# `ultimo_porcionamiento`, las marcas y los picos de `simulador_receta`):
# `armar_ficha` las junta y la pieza sólo las dibuja.
_PREFIJO = re.compile(r"^\s*(\([A-Za-z]{1,3}\)|RP-ST)\s*")
"""El «(P)», «(Rs)», «(L)» o «RP-ST» con que el Almacén empieza el nombre de
un artículo producido: en la lista lo dice la ficha de color."""

DIAS_HABITUAL = 30
"""Los días ANTERIORES al último porcionamiento de un corte que cuentan
para su precio habitual."""

UMBRAL_HABITUAL = 0.10
"""Desde cuánto se aparta el último porcionamiento de lo habitual para que
«Qué mueve el costo de hoy» lo diga."""

PESO_MINIMO = 0.15
"""Cuánto del costo del plato tiene que pesar esa línea para que lo diga."""


def _limpio(nombre):
    return _PREFIJO.sub("", str(nombre or "")).strip()


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


def filas_receta(nodos):
    """El árbol aplanado en el orden en que se lee, cada línea UNA fila:
    [id, padre (−1 arriba), nivel, nombre, ficha («Rs» receta base, «P»
    corte porcionado, «»), cantidad, unidad, costo en el plato, cuántas
    líneas cuelgan, código, fecha de la receta base, ruta (la del
    simulador: «0.2.1»)]. Pura."""
    out = []

    def bajar(n, par, nivel, ruta):
        i = len(out)
        hijos = n.get("hijos") or []
        ficha = ("Rs" if hijos else "P" if sr.es_porcionado(n) else "")
        out.append([i, par, nivel, _limpio(n.get("ins")), ficha,
                    round(float(n.get("cant") or 0), 6), str(n.get("unid") or ""),
                    round(float(n.get("costo") or 0), 6), len(hijos), str(n.get("cod") or ""),
                    str((n.get("base") or {}).get("fecha") or ""), ruta])
        for j, h in enumerate(hijos):
            bajar(h, i, nivel + 1, f"{ruta}.{j}")
    for k, n in enumerate(nodos):
        bajar(n, -1, 0, str(k))
    return out


def habitual_corte(po, dias=DIAS_HABITUAL):
    """Lo habitual de un corte: los porcionamientos de los `dias` días
    ANTERIORES al último (`po`, de `porcionamientos_de`, del más nuevo al
    más viejo), con su costo por unidad ponderado por lo que salió de cada
    uno. {costo, n, salio} o None si no hubo ninguno. Pura."""
    if po is None or len(po) < 2:
        return None
    ult = po["Fecha"].iloc[0]
    if pd.isna(ult):
        return None
    prev = po.iloc[1:]
    prev = prev[(prev["Fecha"] >= ult - pd.Timedelta(days=dias))
                & (prev["Salio"] > 0) & (prev["Costo"] > 0)]
    if prev.empty:
        return None
    salio = float(prev["Salio"].sum())
    return {"costo": float((prev["Salio"] * prev["Costo"]).sum() / salio),
            "n": int(len(prev)), "salio": salio}


def que_mueve(filas, cortes, costo, neto):
    """«Qué mueve el costo de hoy»: la línea de arriba que más pesa, si es un
    corte porcionado que pesa al menos `PESO_MINIMO` del plato, la receta
    tiene el precio de su ÚLTIMO porcionamiento y ese se aparta de lo
    habitual (`habitual_corte`) en `UMBRAL_HABITUAL` o más. Con lo que el
    plato costaría y su % al precio habitual. None si no. Pura."""
    if not filas or not costo or costo <= 0:
        return None
    arriba = [f for f in filas if f[1] == -1]
    top = max(arriba, key=lambda f: f[7])
    c = cortes.get(top[9]) if top[4] == "P" else None
    if not c or not c.get("hab") or top[7] / costo < PESO_MINIMO:
        return None
    ult, hab = c["filas"][0], c["hab"]["costo"]
    unit = top[7] / top[5] if top[5] else 0.0
    if not (ult[7] and abs(unit - ult[7]) <= max(0.01, 0.01 * ult[7])):
        return None
    if abs(ult[7] / hab - 1) < UMBRAL_HABITUAL:
        return None
    plato = costo - top[7] + hab * top[5]
    return {"id": top[0], "cod": top[9], "nombre": top[3], "pct": top[7] / costo * 100,
            "ult": ult[7], "fecha": ult[0], "doc": (c.get("ult") or {}).get("doc", ""),
            "de": ult[1], "merma": ult[6], "de_porc": bool(c.get("de_porc")),
            "hab": hab, "n": c["hab"]["n"], "unid": c["u"],
            "plato": plato, "pct_hab": plato / neto * 100 if neto else None,
            "ruta": top[11], "P": c.get("P_hab")}


def _iso_dia(v):
    return "" if v is None or pd.isna(v) else f"{pd.Timestamp(v):%Y-%m-%d}"


def cortes_del_plato(nodos, df_po, n=_N_PORC):
    """Los porcionamientos de cada corte del plato (regla #574) para la
    pieza: {cod: {n (nombre), u (unidad del corte), unit (lo que la receta
    le pone por unidad), filas ([fecha, desde, porcionado, unidad, salió,
    unidad, merma %, costo por unidad], del más nuevo), ult (el documento,
    su origen y la marca de «Para revisar»), hab (`habitual_corte`), de_porc
    (si lo de origen es a su vez un corte) y P_hab (el precio de origen con
    que el simulador lo deja en lo habitual)}}. Pura."""
    if df_po is None or getattr(df_po, "empty", True):
        return {}
    origen = codigos_porcionados(df_po)
    out = {}
    for cod, nodo in _porcionados(nodos).items():
        todos = porcionamientos_de(df_po, cod, n=max(n, 60))
        if todos.empty:
            continue
        po = todos.head(n)
        ult = ultimo_porcionamiento(df_po, cod) or {}
        hab = habitual_corte(todos)
        p = nodo.get("porc") or {}
        P_hab = None
        if hab and p.get("peso"):
            P_hab = hab["costo"] * (1 - float(p.get("merma") or 0) / 100) / float(p["peso"])
        out[cod] = {
            "n": _limpio(nodo.get("ins")), "u": str(po["UnidFin"].iloc[0] or nodo.get("unid") or ""),
            "unit": float(nodo["costo"]) / float(nodo["cant"] or 1.0),
            "filas": [[_iso_dia(r.Fecha), _limpio(r.De), round(float(r.Porcionado), 3), r.UnidIni,
                       round(float(r.Salio), 3), r.UnidFin, round(float(r.Merma), 2),
                       round(float(r.Costo), 4)] for r in po.itertuples(index=False)],
            "ult": {"doc": ult.get("doc", ""), "fecha": _iso_dia(ult.get("fecha")),
                    "cod_de": ult.get("cod_de", ""), "raro": bool(ult.get("raro")),
                    "kgu": _f(ult.get("kgu", float("nan"))), "hab": _f(ult.get("hab", float("nan"))),
                    "reciente": bool(ult.get("fecha") is not None
                                     and _reciente(df_po, ult.get("fecha")))},
            "hab": hab, "de_porc": str(ult.get("cod_de", "")) in origen,
            "P_hab": round(P_hab, 6) if P_hab else None,
        }
    return out


def _mensual(agg, cod):
    g = costo_mensual(agg, cod)
    return [[f"{r.mes.year}-{r.mes.month:02d}", _f(r.unidades, 3),
             _f(r.costo_unit) if pd.notna(r.costo_unit) else None, _f(r.neto, 2),
             _f(r.pct, 2) if pd.notna(r.pct) else None, _f(r.neto_sin_costo, 2)]
            for r in g.itertuples(index=False)]


def armar_ficha(f, nodos, agg, rango, marcas=(), picos=(), auditoria=(), cortes=None,
                faltan=()):
    """Lo que recibe la pieza de la ficha: el plato con sus cifras de la
    Carta, la receta aplanada (`filas_receta`), lo vendido mes a mes
    (`costo_mensual`), las marcas, los cambios de la auditoría y los picos
    como texto, los porcionamientos de cada corte (`cortes_del_plato`) y
    «Qué mueve el costo de hoy» (`que_mueve`). Pura: la lee el test."""
    cortes = cortes or {}
    filas = filas_receta(nodos)
    costo = _f(f["Costo"])
    neto = _f(f["Neto"])
    sin_neto = _f(f.get("SinCostoNeto", 0.0), 2)
    combo = None
    if f["Tipo"] == "Combo":
        combo = {"tipo": str(f.get("TipoCombo") or ""), "metodo": str(f.get("Metodo") or ""),
                 "banda": [["Mínimo", _f(f.get("Minimo"), 2)], ["Promedio", _f(f.get("Promedio"), 2)],
                           ["Esperado", _f(f.get("Esperado"), 2)], ["Máximo", _f(f.get("Maximo"), 2)],
                           ["Real 90 días", _f(f.get("Real90"), 2)]]}
    return {
        "plato": {
            "cod": str(f["Cod"]), "nombre": str(f["Producto"]),
            "ruta": " › ".join(x for x in (f["Grupo"], f["Subgrupo"]) if x),
            "tipo": str(f["Tipo"]), "precio": _f(f["Precio"], 2), "neto": neto,
            "costo": costo, "sin_costo": bool(f["SinCosto"]),
            "vend": _f(f.get("Vendidos", 0.0), 3), "vneto": _f(f.get("VendidoNeto", 0.0), 2),
            "vcosto": _f(f.get("CostoVendido", 0.0), 2), "sin_neto": sin_neto,
            "sin_causa": ("el POS no le tiene costo" if f["SinCosto"] else
                          "se vendió antes de que el POS se lo cargara") if sin_neto > 0 else "",
            "receta": _iso(f.get("Actualizado", pd.NaT)), "descarga": str(f.get("Descarga") or ""),
            "combo": combo,
        },
        "filas": filas,
        "meses": _mensual(agg, f["Cod"]),
        "rango": [_iso_dia(rango[0]), _iso_dia(rango[1])] if rango else None,
        "marcas": [{"t": _iso_dia(m["t"]), "x": _texto_marca(m)} for m in marcas],
        "cambios": [{"t": _iso_dia(c["t"]), "x": _texto_cambio(c)} for c in auditoria],
        "picos": [{"ini": _iso_dia(p["ini"]), "fin": _iso_dia(p["fin"]), "pico": _f(p["pico"]),
                   "x": _texto_pico(p)} for p in picos],
        "cortes": cortes,
        "q": que_mueve(filas, cortes, costo, neto),
        "divisor": divisor_neto(),
        "umbrales": [_UMBRAL_COSTO_OK, _UMBRAL_COSTO_WARN],
        "combo_antes": f"{_COMBO_ANTES.year}-{_COMBO_ANTES.month:02d}",
        "faltan": list(faltan),
    }


_K_SIM_SEMILLA = "rec_carta_sim_semilla"
"""Con qué abre el simulador: {cod, estado} de «Simular con S/ …» (el precio
habitual de un corte). «Simular» a secas la borra."""


def _a_nuevo_costeo(cod):
    """«Copiar receta a Nuevo Costeo»: importa el plato en «Modificar» como
    lo hace su botón «Importar» y pide el salto a esa vista (una corrida
    completa: la Carta es un fragment). Con un `formulario_receta` viejo en
    Cloud (regla #357), no hace nada."""
    try:
        import navegacion
        import formulario_receta as fr
        from navegacion_retorno import capturar_origen
        capturar_origen()
        st.session_state["form_receta_modificar_que"] = "plato"
        fr._importar(str(cod))
        st.session_state["form_receta_modo"] = "Modificar"
        navegacion._ir_a_vista("Recetas", "rec_graf_tipo", "Nueva receta")
        st.session_state["_rec_cambios_ir"] = 1
    except (ImportError, AttributeError):
        return


def _datos_ficha(f, df_rv, agg, rango, df_po=None):
    """Lo de la ficha del elegido que sólo sabe Python (reglas #744 y #746):
    la receta con sus precios, lo vendido mes a mes, las marcas, los picos y
    los porcionamientos de sus cortes (`armar_ficha`). Viaja en la MISMA
    pieza que la lista, en `ficha`, y la ficha del costado lo dibuja en sus
    pestañas. Si «Simular» quedó abierto para este plato, abre la modal de
    la regla #656."""
    ss = st.session_state
    cod, nombre = str(f["Cod"]), str(f["Producto"])
    es_receta = f["Tipo"] == "Receta"
    if es_receta and ss.get(_K_SIM_ABIERTO) == cod:
        semilla = ss.get(_K_SIM_SEMILLA) or {}
        _modal_simulador(cod, nombre, float(f["Precio"]), df_rv,
                         semilla.get("estado") if semilla.get("cod") == cod else None)
    nodos = []
    if es_receta:
        with st.spinner("Armando la receta con sus precios…"):
            nodos = armar_arbol(df_rv, cod)
    ediciones = ediciones_bases() if nodos else None
    # Sin las que no movieron el plato ni un céntimo: un ▼ que dice
    # «+S/ 0,00» es ruido.
    marcas = [m for m in (sr.marcas_plato(nodos, ediciones) if ediciones else [])
              if abs(m["esp"]) >= 0.01]
    cambios = cambios_auditoria()
    picos = sr.picos_plato(agg, cod, nodos, df_po, cambios=cambios)
    auditoria = sr.cambios_del_plato(cambios, nodos, cod)
    faltan = []
    if es_receta and ediciones is None:
        faltan.append("las ediciones de sus recetas base (filas «recetabaselog» y "
                      "«recetabaselogdet»)")
    if cambios is None:
        faltan.append("los cambios de factor y unidad de la auditoría del POS (fila "
                      "«auditoriacostos»)")
    return armar_ficha(f, nodos, agg, rango, marcas, picos, auditoria,
                       cortes_del_plato(nodos, df_po), faltan)


# ─── La pieza propia (reglas #696 y #746) ─────────────────────────────────
_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "carta_costeada",
    # La ficha del costado dibuja la receta y la evolución con las clases
    # `fp-*` de `ficha_plato.css`: van en la misma hoja, después.
    css=css_movil((_AQUI / "carta_costeada.css").read_text(encoding="utf-8")
                  + (_AQUI / "ficha_plato.css").read_text(encoding="utf-8")),
    # El Excel (`libro`, `bajar`) vive en `_xlsx.js`, compartido con
    # «Consistencia de datos», y la ficha del plato (`FichaPlato`) en
    # `ficha_plato.js`: se anteponen, y quedan en el mismo módulo.
    js=js_movil((_AQUI / "_xlsx.js").read_text(encoding="utf-8")
    + (_AQUI / "ficha_plato.js").read_text(encoding="utf-8")
    + (_AQUI / "carta_costeada.js").read_text(encoding="utf-8")),
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
    """La vista entera (reglas #696 y #746): UNA tarjeta, UNA pieza propia
    —filtros, indicadores, la lista y, al costado, la ficha del elegido con
    Resumen | Receta | Evolución | Canales—. `df` es `cartacosteada.parquet`
    (o None si no se pudo cargar); `df_rv`, recetaventa.parquet (las recetas
    y su fecha); `ventas`, lo vendido por producto y día, o la FUNCIÓN que lo
    carga (`data.venta_por_producto_dia`, regla #573); `ventas_canal`, lo
    vendido fuera de «En el Local» o la función que lo carga
    (`data.venta_por_canal_dia`); `df_rb`, por la firma del dispatcher;
    `porcionamientos`, el parquet o la función que lo carga (regla #574).

    Todo lo que se elige en la lista —canal, grupo, tipo, buscar, orden,
    columnas, el Excel— lo resuelve el navegador: la pieza recibe la carta
    entera (con inactivos y venta interna) y no pide una corrida. Elegir un
    producto pide su ficha (`_datos_ficha`), que viaja en la misma pieza; la
    ficha cambia en el navegador en el momento y espera la receta y la
    evolución con su aviso. También vuelven «Simular», «Ver cambios»,
    «Copiar receta a Nuevo Costeo» y los saltos a Producción."""
    ss = st.session_state
    if ss.pop("_rec_cambios_ir", None):
        # «Ver cambios» pidió el salto a otra sección: una corrida completa,
        # porque esta vista es un fragment.
        st.rerun(scope="app")
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

        codigos = set(carta["Cod"])
        df_po = porcionamientos() if callable(porcionamientos) else porcionamientos

        def _valor(k):
            return (ss.get(_K_PIEZA) or {}).get(k)

        def _cod(v):
            """El código que manda el navegador, si es uno de la carta."""
            c = v.get("cod") if isinstance(v, dict) else v
            return str(c) if c is not None and str(c) in codigos else None

        def _al_elegir():
            c = _cod(_valor("elegir"))
            if c:
                ss[_K_FOCO] = c

        def _al_simular():
            # Desde la ficha: «Simular» a secas o «Simular con S/ …», que la
            # siembra con el precio habitual de un corte (`estado`).
            v = _valor("simular")
            c = _cod(v)
            if c:
                ss[_K_FOCO] = c
                estado = v.get("estado") if isinstance(v, dict) else None
                ss[_K_SIM_SEMILLA] = {"cod": c, "estado": estado}
                _abrir_simulador(c)

        def _al_cambios():
            # «Ver cambios» (regla #707): adentro, por el import circular
            # (recetas_cambios lee de acá la auditoría y el log).
            c = _cod(_valor("cambios"))
            if c:
                from graficos.recetas_cambios import ir_desde_carta
                ir_desde_carta(c)

        def _al_nuevo():
            c = _cod(_valor("nuevo_costeo"))
            if c:
                _a_nuevo_costeo(c)

        def _al_produccion():
            v = _valor("produccion") or {}
            corte = str(v.get("cod") or "") if isinstance(v, dict) else ""
            ult = ultimo_porcionamiento(df_po, corte) if corte else None
            if ult and v.get("destino") in ("rend", "rev") and _preparar_salto(v["destino"], ult, corte):
                ss["_rec_cambios_ir"] = 1

        datos = armar_pieza(carta, rango, por_canal, sel, n_sin_precio)
        f = carta[carta["Cod"] == sel]
        datos["ficha"] = _datos_ficha(f.iloc[0], df_rv, agg, rango, df_po) if not f.empty else None
        _PIEZA(key=_K_PIEZA, data=datos,
               on_elegir_change=_al_elegir, on_simular_change=_al_simular,
               on_cambios_change=_al_cambios, on_nuevo_costeo_change=_al_nuevo,
               on_produccion_change=_al_produccion, width="stretch")
