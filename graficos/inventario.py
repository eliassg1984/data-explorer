"""
graficos.inventario — dashboard de Inventario Valorizado (v2). Layout unificado con chips en franja blanca + card con pills.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


from tema import ACENTO, TEXTO_PRINCIPAL
from graficos.base import (
    PALETA_CALLAI, _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos,
)

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py) — reemplaza el st.pills que vivia ANTES adentro del
# card izquierdo. El panel "mini-tops" (Mayor cantidad/Precio mas alto) NO
# es una opcion del rail: es un panel FIJO, siempre visible junto al grafico
# elegido (ver col_der mas abajo) — no es parte del selector de tipo.
_INVENTARIO_RAIL_CATEGORIAS = (
    ("Vista", (("Área y familia",            "Área y familia"),
               ("Torta familias",            "Torta"),
               ("Top por área (valor)",      "Top valor"),
               ("Top por área (cantidad)",   "Top cantidad"))),
    ("Datos", (("Tabla", "Tabla"),)),
)


def renderizar_graficos_inventario(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Inventario Valorizado: 4 gráficos + 2 mini-tops.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py). Se le
    pasa `d` — el df ya filtrado por los chips propios (Área/Familia) —
    igual que Ventas, para no tener un estado de filtros distinto entre
    Tabla y gráficos."""
    col_area  = _resolver(df_f, ["Nombre Area", "NOMBRE AREA", "Area"])
    col_fam   = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_prod  = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_cant  = _resolver(df_f, ["Stock al Dia", "Stock al dia", "STOCK AL DIA",
                                 "Cantidad", "Stock"])
    col_val   = _resolver(df_f, ["Valorizado total", "VALORIZADO TOTAL",
                                 "Valorizado"])
    col_punit = _resolver(df_f, ["Precio Promedio", "PRECIO PROMEDIO", "Precio"])

    if not col_val:
        st.warning("No se encontró la columna de valorizado. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Área / Familia como chips en la FRANJA blanca ────────────
    area_sel, fam_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if col_area:
                areas = sorted(df_f[col_area].dropna().astype(str).unique().tolist())
                if areas:
                    _n = len(st.session_state.get("inv_graf_filtro_area") or [])
                    _lbl = f":material/filter_alt: Área :violet-badge[{_n}]" if _n else ":material/filter_alt: Área"
                    with st.popover(_lbl, use_container_width=True):
                        area_sel = st.pills(
                            "Área", areas, selection_mode="multi",
                            key="inv_graf_filtro_area",
                            label_visibility="collapsed",
                        ) or []
        with c2:
            if col_fam:
                fams = sorted(df_f[col_fam].dropna().astype(str).unique().tolist())
                if fams:
                    _n = len(st.session_state.get("inv_graf_filtro_fam") or [])
                    _lbl = f":material/category: Familia :violet-badge[{_n}]" if _n else ":material/category: Familia"
                    with st.popover(_lbl, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia", fams, selection_mode="multi",
                            key="inv_graf_filtro_fam",
                            label_visibility="collapsed",
                        ) or []

    d = df_f
    if area_sel and col_area:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Inventario Valorizado", d,
                         {"Área": area_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _val  = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    _cant = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
             if col_cant else None)

    graf = _render_rail(_INVENTARIO_RAIL_CATEGORIAS, "inv_graf_tipo",
                        btn_prefix="inv_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            tabla_cb(d)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    col_izq, col_der = st.columns([1.7, 1])

    with col_izq:
        with st.container(border=True, key="ajuste_graf_card_izq_inv"):
            if graf == "Área y familia" and col_area and col_fam:
                g = (pd.DataFrame({"area": d[col_area].astype(str),
                                   "fam": d[col_fam].astype(str),
                                   "val": _val})
                     .groupby(["area", "fam"], as_index=False)["val"].sum())
                orden = (g.groupby("area")["val"].sum()
                         .sort_values(ascending=False).index.tolist())
                fig = px.bar(g, x="area", y="val", color="fam",
                             category_orders={"area": orden})
                _compras_layout(fig, alto=520)
                fig.update_layout(
                    title="Valorizado por área, desglosado por familia",
                    barmode="stack", xaxis_title=None, yaxis_title=None,
                    legend=dict(orientation="h", y=-0.25, x=0,
                                font=dict(size=10)),
                )
                fig.update_traces(
                    hovertemplate="%{fullData.name}<br>%{x}: S/ %{y:,.2f}<extra></extra>")
                st.plotly_chart(fig, use_container_width=True, key="inv_g_areafam")

            elif graf == "Torta familias" and col_fam:
                serie = (_val.groupby(d[col_fam].astype(str)).sum()
                         .sort_values(ascending=False))
                fig = go.Figure(go.Pie(
                    labels=serie.index, values=serie.values, hole=0.45,
                    marker=dict(colors=PALETA_CALLAI * 4),
                    textinfo="label+percent",
                    hovertemplate="%{label}<br>S/ %{value:,.2f} (%{percent})<extra></extra>",
                ))
                _compras_layout(fig, alto=520)
                fig.update_layout(title="Participación del valorizado por familia",
                                  showlegend=False)
                st.plotly_chart(fig, use_container_width=True, key="inv_g_torta")

            elif graf in ("Top por área (valor)", "Top por área (cantidad)") and col_area and col_prod:
                es_valor = (graf == "Top por área (valor)")
                if not es_valor and _cant is None:
                    st.info("No se encontró la columna de cantidad.")
                else:
                    areas = sorted(d[col_area].dropna().astype(str).unique().tolist())
                    _ca, _ = st.columns([1, 2])
                    with _ca:
                        area_top = st.selectbox("Área", areas, key="inv_graf_area_top")
                    dd = d[d[col_area].astype(str) == area_top]
                    met = (pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
                           if es_valor
                           else pd.to_numeric(dd[col_cant], errors="coerce").fillna(0))
                    serie = (met.groupby(dd[col_prod].astype(str)).sum()
                             .nlargest(10).sort_values())
                    if serie.empty:
                        st.info("Sin datos en esa área.")
                    else:
                        _fmt = "S/ {:,.0f}" if es_valor else "{:,.1f}"
                        fig = go.Figure(go.Bar(
                            x=serie.values,
                            y=[_compras_truncar(i, 34) for i in serie.index],
                            orientation="h",
                            marker=dict(color=ACENTO, opacity=0.85),
                            text=[_fmt.format(v) for v in serie.values],
                            textposition="outside", cliponaxis=False,
                        ))
                        _compras_layout(fig, alto=480)
                        _t = "valorizado" if es_valor else "cantidad"
                        fig.update_layout(
                            title=f"Top 10 productos por {_t} — {area_top}")
                        fig.update_xaxes(visible=False)
                        st.plotly_chart(fig, use_container_width=True,
                                        key=f"inv_g_top_{_t}")
            else:
                st.info("No hay columnas suficientes para este gráfico.")

    with col_der:
        with st.container(border=True, key="ajuste_graf_card_der_inv"):
            tabs = st.tabs(["Mayor cantidad", "Precio más alto"])
            with tabs[0]:
                if col_prod and _cant is not None and col_area:
                    g = (pd.DataFrame({"prod": d[col_prod].astype(str),
                                       "area": d[col_area].astype(str),
                                       "cant": _cant})
                         .groupby(["prod", "area"], as_index=False)["cant"].sum()
                         .nlargest(10, "cant").sort_values("cant"))
                    if g.empty:
                        st.info("Sin datos.")
                    else:
                        fig = go.Figure(go.Bar(
                            x=g["cant"],
                            y=[_compras_truncar(p_, 24) for p_ in g["prod"]],
                            orientation="h",
                            marker=dict(color=ACENTO, opacity=0.85),
                            text=[_compras_truncar(a_, 14) for a_ in g["area"]],
                            textposition="outside", cliponaxis=False,
                            customdata=g["area"],
                            hovertemplate=("%{y}<br>Área: %{customdata}"
                                           "<br>Cantidad: %{x:,.1f}<extra></extra>"),
                        ))
                        fig.update_layout(
                            height=400, margin=dict(l=4, r=60, t=10, b=10),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="DM Sans, sans-serif",
                                      color=TEXTO_PRINCIPAL, size=11),
                        )
                        fig.update_xaxes(visible=False)
                        st.plotly_chart(fig, use_container_width=True,
                                        key="inv_mini_cant")
                else:
                    st.info("Faltan columnas de cantidad o área.")
            with tabs[1]:
                if col_prod and col_punit and col_area:
                    _pu = pd.to_numeric(d[col_punit], errors="coerce")
                    g = (pd.DataFrame({"prod": d[col_prod].astype(str),
                                       "area": d[col_area].astype(str),
                                       "pu": _pu,
                                       "cant": (_cant if _cant is not None
                                                else pd.Series(0, index=d.index))})
                         .dropna(subset=["pu"])
                         .groupby(["prod", "area"], as_index=False)
                         .agg(pu=("pu", "mean"), cant=("cant", "sum"))
                         .nlargest(10, "pu").sort_values("pu"))
                    if g.empty:
                        st.info("Sin datos.")
                    else:
                        fig = go.Figure(go.Bar(
                            x=g["pu"],
                            y=[_compras_truncar(p_, 24) for p_ in g["prod"]],
                            orientation="h",
                            marker=dict(color=ACENTO, opacity=0.85),
                            text=[f"S/ {v:,.1f}" for v in g["pu"]],
                            textposition="outside", cliponaxis=False,
                            customdata=np.stack([g["area"], g["cant"]], axis=-1),
                            hovertemplate=("%{y}<br>Área: %{customdata[0]}"
                                           "<br>Precio: S/ %{x:,.2f}"
                                           "<br>Cantidad: %{customdata[1]:,.1f}"
                                           "<extra></extra>"),
                        ))
                        fig.update_layout(
                            height=400, margin=dict(l=4, r=60, t=10, b=10),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="DM Sans, sans-serif",
                                      color=TEXTO_PRINCIPAL, size=11),
                        )
                        fig.update_xaxes(visible=False)
                        st.plotly_chart(fig, use_container_width=True,
                                        key="inv_mini_precio")
                else:
                    st.info("Faltan columnas de precio o área.")
