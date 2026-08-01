"""graficos.compras.cantidad - drill de Cantidad por producto.

Top N de productos por cantidad comprada, con su precio unitario.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO
from graficos.base import PALETA_CALLAI, _compras_layout, _compras_truncar


@st.fragment
def _compras_cantidad_producto(d, col_prod, col_cant, col_valor, col_punit, col_fecha):
    """Cantidad/Valor de compra por producto, agrupable por Semana/Mes/Año.

    Controles: granularidad (Semana/Mes/Año), vista (Agrupado/Apilado),
    magnitud (Cantidad/Valor S/), y foco (Top 8 o un producto). Muestra 3
    KPIs del rango (valor total, precio promedio ponderado, cantidad total).
    Vive en su @st.fragment: cambiar un control solo redibuja esto.
    """
    if not (col_prod and col_fecha and (col_cant or col_valor)):
        st.info("Faltan columnas (Producto, Fecha y Cantidad o Valor) "
                "para este gráfico.")
        return

    # ── Controles ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.1, 2])
    with c1:
        gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                        default="Mes", key="compras_cant_gran") or "Mes"
    with c2:
        vista = st.pills("Vista", ["Agrupado", "Apilado"],
                         default="Agrupado", key="compras_cant_vista") or "Agrupado"
    with c3:
        _meas = []
        if col_cant:
            _meas.append("Cantidad")
        if col_valor:
            _meas.append("Valor S/")
        meas = st.pills("Medir", _meas, default=_meas[0],
                        key="compras_cant_meas") or _meas[0]
    with c4:
        prods = sorted(d[col_prod].dropna().astype(str).unique().tolist())
        foco = st.selectbox("Producto", ["Top 8 productos"] + prods,
                            key="compras_cant_prod")

    # ── Preparación de datos ────────────────────────────────────────────
    fe = pd.to_datetime(d[col_fecha], errors="coerce")
    val = (pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
           if col_valor else pd.Series(0.0, index=d.index))
    cant = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
            if col_cant else pd.Series(0.0, index=d.index))

    if gran == "Semana":
        iso = fe.dt.isocalendar()
        per = (iso["year"].astype("Int64").astype(str) + "-S"
               + iso["week"].astype("Int64").astype(str).str.zfill(2))
    elif gran == "Año":
        per = fe.dt.year.astype("Int64").astype(str)
    else:  # Mes
        per = fe.dt.to_period("M").astype(str)

    base = pd.DataFrame({
        "per": per.values, "prod": d[col_prod].astype(str).values,
        "cant": cant.values, "val": val.values,
    })
    base["m"] = base["cant"] if meas == "Cantidad" else base["val"]
    base = base[base["per"].notna() & (base["per"] != "<NA>")]
    if base.empty:
        st.info("Sin datos en el rango seleccionado.")
        return

    # ── Foco: Top 8 o un producto ───────────────────────────────────────
    if foco == "Top 8 productos":
        orden = base.groupby("prod")["m"].sum().nlargest(8).index.tolist()
        scope = base[base["prod"].isin(orden)]
        multi = True
    else:
        orden = [foco]
        scope = base[base["prod"] == foco]
        multi = False
    if scope.empty:
        st.info("Sin datos para el producto seleccionado.")
        return

    # ── KPIs del rango (sobre el foco mostrado) ─────────────────────────
    k_val = float(scope["val"].sum())
    k_cant = float(scope["cant"].sum())
    k_pp = (k_val / k_cant) if k_cant else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Valor total comprado", f"S/ {k_val:,.0f}")
    m2.metric("🏷️ Precio promedio", f"S/ {k_pp:,.2f}")
    m3.metric("📦 Cantidad total", f"{k_cant:,.0f}")

    # ── Barras por periodo ──────────────────────────────────────────────
    periodos = sorted(scope["per"].unique())
    es_valor = (meas == "Valor S/")
    _pref = "S/ " if es_valor else ""
    _tpl = "S/ %{y:,.0f}" if es_valor else "%{y:,.0f}"

    fig = go.Figure()
    if multi:
        for i, p in enumerate(orden):
            s = (scope[scope["prod"] == p].groupby("per")["m"].sum()
                 .reindex(periodos, fill_value=0))
            fig.add_bar(x=periodos, y=s.values,
                        name=_compras_truncar(p, 22),
                        marker_color=PALETA_CALLAI[i % len(PALETA_CALLAI)],
                        hovertemplate="%{fullData.name}<br>%{x}<br>"
                                      + _tpl + "<extra></extra>")
        fig.update_layout(barmode="stack" if vista == "Apilado" else "group")
    else:
        s = scope.groupby("per")["m"].sum().reindex(periodos, fill_value=0)
        fig.add_bar(x=periodos, y=s.values, name=foco, marker_color=ACENTO,
                    text=[f"{_pref}{v:,.0f}" for v in s.values],
                    textposition="outside", cliponaxis=False,
                    hovertemplate="%{x}<br>" + _tpl + "<extra></extra>")

    _compras_layout(fig, alto=440)
    fig.update_layout(
        title=f"{meas} de compra por {gran.lower()}"
              + ("" if multi else f" — {_compras_truncar(foco, 40)}"),
        yaxis=dict(tickprefix=_pref, tickformat=",.0f"),
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10)),
    )
    fig.update_xaxes(type="category", tickangle=-45)
    st.plotly_chart(fig, use_container_width=True, key="compras_g_cant_prod")
