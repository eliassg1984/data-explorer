"""graficos.compras._comun - helpers compartidos por los drills de Compras.

Cosas chicas que usan dos o mas drills: deteccion de movil, lectura de
la seleccion de un plotly_chart, mini barras horizontales y etiquetas de
periodo segun granularidad.

Y la GRILLA (`COLUMNAS_DRILL` / `GAP_DRILL`): la proporcion con la que parte
en dos una fila de un drill. Vive aca y no en cada modulo porque el eje
vertical tiene que caer en el mismo sitio en TODAS las filas de una vista.
"""

import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, TEXTO_PRINCIPAL
from graficos.base import _compras_truncar, _slug
# REEXPORT, no import muerto: `_es_movil` vivía definida acá y se movió a
# graficos/base.py (2026-08-07, ver su docstring) porque graficos/ajuste.py
# la necesitó también. Este import la reexpone bajo el mismo nombre, así que
# proveedor.py y compras/__init__.py siguen haciendo
# `from graficos.compras._comun import _es_movil` sin enterarse. Este módulo
# NO la usa, de ahí el noqa: sin él, `ruff --fix` la borraría y rompería a
# sus dos consumidores.
from graficos.base import _es_movil  # noqa: F401
from graficos import alturas


# ===========================================================================
# LA GRILLA: UNA SOLA PROPORCIÓN POR VISTA
# ===========================================================================
# Hermana de `tema.py` (dueño del color) y `alturas.py` (dueño del alto): el
# EJE VERTICAL de una vista tampoco puede escribirse a mano en cada fila.
#
# POR QUÉ EXISTE (2026-08-21). El drill de Proveedor tenía dos filas de dos
# columnas y cada una partía en un sitio distinto: la de arriba con
# `st.columns([1.6, 1])` (61.5%) y la de abajo con `st.columns(2)` (50%). Con
# ~1750px de ancho útil eso son ~200px de salto — el canal gris que baja entre
# las columnas se cortaba a media página y la vista dejaba de leerse como una
# grilla. No lo cazaba nada: los dos números son correctos por separado.
#
# La regla: la proporción que parte una FILA de un drill sale de acá. Las
# subdivisiones DENTRO de una tarjeta (el chart y su pila de KPIs, una
# botonera) son otra cosa y siguen siendo literales — se marcan con un
# comentario `# columnas-internas: <por qué>` y `test_graficos.py` las
# distingue por esa marca.
COLUMNAS_DRILL = [1.6, 1]
"""Proporción izq./der. de una fila de dos columnas en un drill de Compras.

1.6/1 y no 1/1: la columna izquierda lleva siempre la tabla con nombres
largos (proveedores, productos) y la derecha un panel de apoyo. La grilla de
4 métricas del Panel B ya colapsa sola a 2x2 en anchos chicos
(`@container (max-width: 380px)` en `_css_proveedor.py`), así que angostarla
es seguro."""

GAP_DRILL = "small"
"""Gap entre las columnas de un drill. Va con `COLUMNAS_DRILL`: si las dos
filas parten en el mismo sitio pero con gaps distintos, el canal gris cambia
de ancho a media página y el salto se ve igual."""


def _first_point(evt):
    """Primer punto de una selección de st.plotly_chart(on_select=...).
    Devuelve el dict del punto o None (tolerante a formatos/errores)."""
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        pts = (sel or {}).get("points", [])
        return pts[0] if pts else None
    except Exception:
        return None


def _compras_mini_barras(serie, titulo, fmt="S/ {:,.0f}", alto=alturas.APOYO):
    """Mini gráfico de barras horizontales top-N (mayor arriba)."""
    if serie is None or serie.empty:
        st.info("Sin datos para este top.")
        return
    d = serie.sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=d.values,
        y=[_compras_truncar(i) for i in d.index],
        orientation="h",
        marker=dict(color=ACENTO, opacity=0.85),
        text=[fmt.format(v) for v in d.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=alto,
        margin=dict(l=4, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True,
                    key=f"compras_mini_{_slug(titulo)}")


def _periodo_serie(fe, gran):
    """Serie de etiquetas de periodo (ordenables) según granularidad."""
    if gran == "Día":
        return fe.dt.strftime("%Y-%m-%d")
    if gran == "Semana":
        iso = fe.dt.isocalendar()
        return (iso["year"].astype("Int64").astype(str) + "-S"
                + iso["week"].astype("Int64").astype(str).str.zfill(2))
    if gran == "Año":
        return fe.dt.year.astype("Int64").astype(str)
    return fe.dt.to_period("M").astype(str)  # Mes
