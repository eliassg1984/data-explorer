"""graficos.compras.vs_ano_pasado - drill "Vs año pasado" de Compras.

Unifica los dos drills que existían antes en categorías separadas del rail
("Precios › Vs año pasado" y "Cantidad › Vs año pasado") en una sola
pantalla con un selector Precio/Cantidad — mismo espíritu que
`graficos/compras/producto.py`, que ya unificó Precio/Cantidad/Valor de
otro trío de drills viejos en uno solo.

Precio y Cantidad NO comparten granularidad ni lógica a propósito — son
las mismas dos vistas de antes, solo reunidas bajo un selector y un
producto en común:

  · Precio: línea de precio REAL por compra (un producto, granularidad
    diaria — cada punto es una compra real), contra el precio del año
    pasado ("Precio_unit_ano_anterior", punteado).
  · Cantidad: barras de cantidad por MES (un producto, o "(Todos)" para
    sumar todo el rango filtrado), contra la cantidad del año pasado
    ("Cantidad_ano_anterior").

"(Todos)" solo tiene sentido en Cantidad (sumar cantidad de todos los
productos es una magnitud real; promediar o sumar PRECIO de productos
distintos no lo es) — por eso el selector de producto lo oculta en modo
Precio. Si el usuario tenía "(Todos)" elegido y cambia a Precio, el
selector cae al primero de la lista en vez de fallar (Streamlit revienta
si el valor en session_state ya no está en `options`).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, GRIS_BORDE, GRIS_TEXTO
from graficos.base import _card, _compras_layout, _compras_truncar, _resolver
from graficos import alturas

_CSS_SELECTOR_TEXTO = f"""
<style>
.st-key-compras_vap_modo [data-testid="stButtonGroup"] {{
    gap: 10px !important;
}}
.st-key-compras_vap_modo [data-testid="stButtonGroup"] button[role="radio"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1px 0 !important;
    min-height: 0 !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
}}
.st-key-compras_vap_modo [data-testid="stButtonGroup"] button[role="radio"][data-selected] {{
    color: {ACENTO} !important;
    font-weight: 600 !important;
}}
</style>
"""


def _render_precio(d, col_prod, col_punit, col_fecha, prod_sel):
    _col_pu_aa = _resolver(d, ["Precio_unit_ano_anterior", "Precio unit ano anterior",
                               "Precio_unit_ano_a nterior"])
    dd = d[d[col_prod].astype(str) == prod_sel]
    _fe = pd.to_datetime(dd[col_fecha], errors="coerce")
    _pu = pd.to_numeric(dd[col_punit], errors="coerce")
    base = pd.DataFrame({"fecha": _fe, "pu": _pu})
    if _col_pu_aa:
        base["pu_aa"] = pd.to_numeric(dd[_col_pu_aa], errors="coerce")
    base = base.dropna(subset=["fecha", "pu"]).sort_values("fecha")
    if base.empty:
        st.info("Sin compras de ese producto en el rango.")
        return

    fig = go.Figure()
    fig.add_scatter(
        x=base["fecha"], y=base["pu"], mode="lines+markers",
        name="Precio por compra",
        line=dict(color=ACENTO, width=2.2),
        marker=dict(size=7),
        hovertemplate="%{x|%d/%m/%Y}: S/ %{y:,.2f}<extra>Compra</extra>",
    )
    _sub = ""
    if _col_pu_aa and base.get("pu_aa") is not None and base["pu_aa"].notna().any():
        fig.add_scatter(
            x=base["fecha"], y=base["pu_aa"], mode="lines",
            name="Precio año pasado",
            line=dict(color="#9aa0a6", width=2, dash="dot"),
            hovertemplate="%{x|%d/%m/%Y}: S/ %{y:,.2f}<extra>Año pasado</extra>",
        )
        _m_act = base["pu"].mean()
        _m_aa = base["pu_aa"].mean()
        if _m_aa and _m_aa > 0:
            _var = (_m_act - _m_aa) / _m_aa * 100
            _sub = f" · variación promedio {_var:+.1f}% vs año pasado"
    else:
        st.caption("Este producto no tiene precio del año pasado registrado.")
    _compras_layout(fig, alto=alturas.PROTAGONISTA)
    fig.update_layout(
        title=_compras_truncar(prod_sel, 48) + _sub,
        xaxis_title=None, yaxis_title=None,
        legend=dict(orientation="h", y=-0.18, x=0),
    )
    st.plotly_chart(fig, use_container_width=True, key="compras_g_vap_precio")


def _render_cantidad(d, col_prod, col_cant, col_fecha, prod_sel):
    _col_cant_aa = _resolver(d, ["Cantidad_ano_anterior", "Cantidad ano anterior"])
    dd = d if prod_sel == "(Todos)" else d[d[col_prod].astype(str) == prod_sel]
    _fe = pd.to_datetime(dd[col_fecha], errors="coerce")
    _mm = _fe.dt.to_period("M").astype(str)
    _cn = pd.to_numeric(dd[col_cant], errors="coerce").fillna(0)
    base = pd.DataFrame({"mes": _mm, "Este año": _cn})
    if _col_cant_aa:
        base["Año pasado"] = pd.to_numeric(dd[_col_cant_aa], errors="coerce").fillna(0)
    g = base.groupby("mes").sum().sort_index()
    if g.empty:
        st.info("Sin datos en el rango.")
        return

    fig = go.Figure()
    if "Año pasado" in g.columns:
        fig.add_bar(x=g.index, y=g["Año pasado"], name="Año pasado",
                    marker=dict(color=GRIS_BORDE))
    fig.add_bar(x=g.index, y=g["Este año"], name="Este año",
                marker=dict(color=ACENTO))
    _compras_layout(fig, alto=alturas.PROTAGONISTA)
    _tt = ("Cantidad comprada por mes: este año vs año pasado"
           if prod_sel == "(Todos)" else
           _compras_truncar(prod_sel, 40) + " — cantidad mensual vs año pasado")
    fig.update_layout(title=_tt, barmode="group",
                      legend=dict(orientation="h", y=-0.18, x=0))
    fig.update_xaxes(type="category")
    fig.update_traces(
        hovertemplate="%{fullData.name}<br>%{x}: %{y:,.1f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True, key="compras_g_vap_cantidad")


@st.fragment
def _compras_vs_ano_pasado_drill(d, col_prod, col_punit, col_cant, col_fecha, col_valor):
    """Precio o Cantidad (selector "Ver") de un producto en común, cada uno
    contra su serie del año pasado."""
    if not (col_prod and col_fecha and col_valor):
        st.info("Faltan columnas (Producto, Fecha o Valor) para este gráfico.")
        return

    st.markdown(_CSS_SELECTOR_TEXTO, unsafe_allow_html=True)

    with _card("compras_vap", "Vs año pasado", titulo_arriba=True):
        with st.container(key="compras_vap_modo"):
            modo = st.pills("Ver", ["Precio", "Cantidad"], default="Precio",
                            key="compras_vap_modo_pills",
                            label_visibility="collapsed") or "Precio"

        _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
        _tops = _valor.groupby(d[col_prod].astype(str)).sum().nlargest(30).index.tolist()
        # "(Todos)" solo en Cantidad — ver docstring del módulo.
        _opciones_prod = (["(Todos)"] + _tops) if modo == "Cantidad" else _tops
        if not _opciones_prod:
            st.info("Sin productos con compras en el rango.")
            return
        if st.session_state.get("compras_vap_prod") not in _opciones_prod:
            st.session_state["compras_vap_prod"] = _opciones_prod[0]

        _cp, _ = st.columns([1.4, 1.6])
        with _cp:
            prod_sel = st.selectbox("Producto", _opciones_prod, key="compras_vap_prod")

        if modo == "Precio" and col_punit:
            _render_precio(d, col_prod, col_punit, col_fecha, prod_sel)
        elif modo == "Cantidad" and col_cant:
            _render_cantidad(d, col_prod, col_cant, col_fecha, prod_sel)
        else:
            st.info(f"Falta la columna de {'Precio unitario' if modo == 'Precio' else 'Cantidad'} "
                   "para este gráfico.")
