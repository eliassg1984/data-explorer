"""
graficos.salidas — dashboard de Salidas. Layout unificado con chips en franja
blanca + rail derecho (mismo patrón que graficos/inventario.py).

Columnas reales de salidas.parquet (confirmadas 2026-08-04, ver data.py):
    Nombre Producto, Fecha registro, Cant Salida, Valor Neto, Tipo Descargo,
    Sub Almacen, Nombre Familia.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO
from graficos.base import (
    PALETA_CALLAI, _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos,
)
from graficos.compras import _periodo_serie

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py). "Cruce" (Subalmacén × Tipo descargo) responde a la
# pregunta que la tabla sola no contesta bien: qué tipos de descargo
# predominan en cada subalmacén.
_SALIDAS_RAIL_CATEGORIAS = (
    ("Vista", (("Evolución",         "Evolución"),
               ("Subalmacén",        "Subalmacén"),
               ("Tipo descargo",     "Tipo descargo"),
               ("Cruce",             "Subalm. × tipo"),
               ("Top productos",     "Top productos"))),
    ("Datos", (("Tabla", "Tabla"),)),
)


def renderizar_graficos_salidas(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Salidas: KPIs + evolución temporal (con granularidad
    Día/Semana/Mes/Año) + composición por subalmacén y tipo de descargo.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py). Se le
    pasa `d` — el df ya filtrado por los chips propios (Sub Almacén/
    Familia) y por la métrica elegida — igual que Ventas/Inventario, para
    no tener un estado de filtros distinto entre Tabla y gráficos."""
    col_fecha = _resolver(df_f, ["Fecha registro", "Fecha_registro", "FECHA REGISTRO"])
    col_prod  = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_sub   = _resolver(df_f, ["Sub Almacen", "SUB ALMACEN", "Subalmacen", "Sub Almacén"])
    col_fam   = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_tipo  = _resolver(df_f, ["Tipo Descargo", "TIPO DESCARGO", "Tipo de Descargo"])
    col_cant  = _resolver(df_f, ["Cant Salida", "CANT SALIDA", "Cantidad Salida"])
    col_val   = _resolver(df_f, ["Valor Neto", "VALOR NETO", "Valorizado"])

    if not col_val and not col_cant:
        st.warning("No se encontraron las columnas de cantidad/valor de salida. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Sub Almacén / Familia como chips en la franja ─────────────
    # Métrica fija en "Valorizado" (2026-08-07): el toggle Valorizado/
    # Cantidad se sacó de la franja a pedido — Salidas siempre reporta en
    # soles. `col_cant` queda como fallback silencioso solo si algún día
    # faltara la columna de valor (mismo criterio que el resto del archivo:
    # no romper si el parquet cambia), pero no hay UI para elegir Cantidad.
    sub_sel, fam_sel = [], []
    metrica = "Valorizado" if col_val else "Cantidad"
    with st.container(key="chips_ajuste_tabla"):
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if col_sub:
                subs = sorted(df_f[col_sub].dropna().astype(str).unique().tolist())
                if subs:
                    _n = len(st.session_state.get("sal_graf_filtro_sub") or [])
                    _lbl = (f":material/filter_alt: Sub Almacén :violet-badge[{_n}]"
                            if _n else ":material/filter_alt: Sub Almacén")
                    with st.popover(_lbl, use_container_width=True):
                        sub_sel = st.pills(
                            "Sub Almacén", subs, selection_mode="multi",
                            key="sal_graf_filtro_sub",
                            label_visibility="collapsed",
                        ) or []
        with c2:
            if col_fam:
                fams = sorted(df_f[col_fam].dropna().astype(str).unique().tolist())
                if fams:
                    _n = len(st.session_state.get("sal_graf_filtro_fam") or [])
                    _lbl = (f":material/category: Familia :violet-badge[{_n}]"
                            if _n else ":material/category: Familia")
                    with st.popover(_lbl, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia", fams, selection_mode="multi",
                            key="sal_graf_filtro_fam",
                            label_visibility="collapsed",
                        ) or []

    d = df_f
    if sub_sel and col_sub:
        d = d[d[col_sub].astype(str).isin(sub_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Salidas", d,
                         {"Sub Almacén": sub_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    es_valor = (metrica == "Valorizado")
    col_metrica = col_val if es_valor else col_cant
    _met = pd.to_numeric(d[col_metrica], errors="coerce").fillna(0)
    _fmt_pref = "S/ " if es_valor else ""
    _fmt_num = ",.2f" if es_valor else ",.0f"
    _hover_m = "%{fullData.name}<br>%{x}: " + _fmt_pref + "%{y:" + _fmt_num + "}<extra></extra>"

    # ── KPIs (calculados sobre `d`, ya filtrado por los chips) ────────────
    kpis = st.columns(3)
    kpis[0].metric("📄 Registros", f"{len(d):,}")
    if col_cant:
        kpis[1].metric("📦 Cantidad total",
                       f"{pd.to_numeric(d[col_cant], errors='coerce').fillna(0).sum():,.0f}")
    if col_val:
        kpis[2].metric("💰 Valorizado total",
                       f"S/ {pd.to_numeric(d[col_val], errors='coerce').fillna(0).sum():,.2f}")

    graf = _render_rail(_SALIDAS_RAIL_CATEGORIAS, "sal_graf_tipo",
                        btn_prefix="sal_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            tabla_cb(d)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    with st.container(border=True, key="ajuste_graf_card_izq_sal"):
        if graf == "Evolución" and col_fecha:
            _fe = pd.to_datetime(d[col_fecha], errors="coerce")
            cg1, _sp = st.columns([1.4, 3.6])
            with cg1:
                gran = st.pills(
                    "Agrupar por", ["Día", "Semana", "Mes", "Año"],
                    default="Mes", key="sal_graf_gran",
                    label_visibility="collapsed",
                ) or "Mes"
            per = _periodo_serie(_fe, gran)
            if col_tipo:
                g = (pd.DataFrame({"per": per, "tipo": d[col_tipo].astype(str), "m": _met})
                     .dropna(subset=["per"])
                     .groupby(["per", "tipo"], as_index=False)["m"].sum())
                orden = sorted(g["per"].unique())
                fig = px.bar(g, x="per", y="m", color="tipo",
                             category_orders={"per": orden})
                fig.update_layout(barmode="stack")
            else:
                g = (pd.DataFrame({"per": per, "m": _met})
                     .dropna(subset=["per"]).groupby("per", as_index=False)["m"].sum())
                fig = px.bar(g, x="per", y="m")
            _compras_layout(fig, alto=520)
            fig.update_layout(
                title=f"Evolución de {metrica.lower()} por tipo de descargo ({gran.lower()})"
                      if col_tipo else f"Evolución de {metrica.lower()} ({gran.lower()})",
                xaxis_title=None, yaxis_title=None,
                legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=10)),
            )
            fig.update_xaxes(type="category")
            fig.update_traces(hovertemplate=_hover_m)
            st.plotly_chart(fig, use_container_width=True, key="sal_g_evolucion")

        elif graf == "Subalmacén" and col_sub:
            serie = _met.groupby(d[col_sub].astype(str)).sum().sort_values(ascending=True)
            if serie.empty:
                st.info("Sin datos.")
            else:
                _fmt = "S/ {:,.0f}" if es_valor else "{:,.0f}"
                fig = go.Figure(go.Bar(
                    x=serie.values,
                    y=[_compras_truncar(i, 28) for i in serie.index],
                    orientation="h",
                    marker=dict(color=ACENTO, opacity=0.85),
                    text=[_fmt.format(v) for v in serie.values],
                    textposition="outside", cliponaxis=False,
                ))
                _compras_layout(fig, alto=480)
                fig.update_layout(title=f"{metrica} por subalmacén")
                fig.update_xaxes(visible=False)
                st.plotly_chart(fig, use_container_width=True, key="sal_g_subalmacen")

        elif graf == "Tipo descargo" and col_tipo:
            serie = _met.groupby(d[col_tipo].astype(str)).sum().sort_values(ascending=False)
            if serie.empty:
                st.info("Sin datos.")
            else:
                fig = go.Figure(go.Pie(
                    labels=serie.index, values=serie.values, hole=0.45,
                    marker=dict(colors=PALETA_CALLAI * 4),
                    textinfo="label+percent",
                    hovertemplate=("%{label}<br>" + _fmt_pref
                                   + "%{value:" + _fmt_num + "} (%{percent})<extra></extra>"),
                ))
                _compras_layout(fig, alto=480)
                fig.update_layout(
                    title=f"Participación de {metrica.lower()} por tipo de descargo",
                    showlegend=False)
                st.plotly_chart(fig, use_container_width=True, key="sal_g_tipo")

        elif graf == "Cruce" and col_sub and col_tipo:
            g = (pd.DataFrame({"sub": d[col_sub].astype(str),
                               "tipo": d[col_tipo].astype(str), "m": _met})
                 .groupby(["sub", "tipo"], as_index=False)["m"].sum())
            orden = (g.groupby("sub")["m"].sum()
                     .sort_values(ascending=False).index.tolist())
            fig = px.bar(g, x="sub", y="m", color="tipo",
                         category_orders={"sub": orden})
            _compras_layout(fig, alto=520)
            fig.update_layout(
                title=f"{metrica} por subalmacén, desglosado por tipo de descargo",
                barmode="stack", xaxis_title=None, yaxis_title=None,
                legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=10)),
            )
            fig.update_traces(hovertemplate=_hover_m)
            st.plotly_chart(fig, use_container_width=True, key="sal_g_cruce")

        elif graf == "Top productos" and col_prod:
            serie = _met.groupby(d[col_prod].astype(str)).sum().nlargest(10).sort_values()
            if serie.empty:
                st.info("Sin datos.")
            else:
                _fmt = "S/ {:,.0f}" if es_valor else "{:,.0f}"
                fig = go.Figure(go.Bar(
                    x=serie.values,
                    y=[_compras_truncar(i, 34) for i in serie.index],
                    orientation="h",
                    marker=dict(color=ACENTO, opacity=0.85),
                    text=[_fmt.format(v) for v in serie.values],
                    textposition="outside", cliponaxis=False,
                ))
                _compras_layout(fig, alto=480)
                fig.update_layout(title=f"Top 10 productos por {metrica.lower()}")
                fig.update_xaxes(visible=False)
                st.plotly_chart(fig, use_container_width=True, key="sal_g_top_productos")

        else:
            st.info("No hay columnas suficientes para este gráfico.")
