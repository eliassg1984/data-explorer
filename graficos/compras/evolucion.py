"""graficos.compras.evolucion - evolucion de proveedores en el tiempo.

Serie temporal por proveedor, tabla de top productos y drill a que otros
proveedores vendieron el mismo producto.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO
from graficos.base import PALETA_CALLAI, _compras_layout, _compras_truncar


@st.fragment
def _compras_evolucion_proveedores(d, col_prov, col_prod, col_cant,
                                    col_valor, col_punit, col_fecha):
    """Dashboard rediseñado de evolución de compras por proveedor.

    Layout exacto del mockup:
      · Fila de controles: Agrupar por (Día/Semana/Mes/Año) + Métrica
        (dropdown) + Selector de proveedores con búsqueda (máx. 5).
      · Gráfico principal: barras agrupadas con range-slider inferior.
      · Panel de detalle del proveedor seleccionado (clic en leyenda o barra):
        - KPIs (Total Compras, % Participación, Órdenes, Productos, Última compra)
        - Mini sparkline de evolución
        - Tabla "Top productos comprados" con % participación (clic → drill)
      · Tabla "Otros proveedores que también vendieron X producto"
        con barras de progreso y % participación.
      · Consejo al pie.
    """
    if not (col_prov and col_valor and col_fecha):
        st.info("Faltan columnas (Proveedor, Valor, Fecha) para este gráfico.")
        return

    # ── Preparar datos base ───────────────────────────────────────────────
    _fe = pd.to_datetime(d[col_fecha], errors="coerce")
    _vv = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    _cn = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0) if col_cant
           else pd.Series(0.0, index=d.index))
    base = pd.DataFrame({
        "prov":  d[col_prov].astype(str).values,
        "prod":  (d[col_prod].astype(str).values if col_prod else "—"),
        "cant":  _cn.values,
        "valor": _vv.values,
        "punit": (pd.to_numeric(d[col_punit], errors="coerce").values
                  if col_punit else np.nan),
        "fecha": _fe.values,
    })
    base = base[base["prov"].notna() & (base["prov"] != "nan")]
    if base.empty or base["valor"].sum() == 0:
        st.info("Sin datos en el rango seleccionado.")
        return

    _tot_all = float(base["valor"].sum()) or 1.0
    _todos_provs = (base.groupby("prov")["valor"].sum()
                    .sort_values(ascending=False).index.tolist())

    # ── Fila 1: controles ─────────────────────────────────────────────────
    cc1, cc2, cc3 = st.columns([1.4, 1.4, 3.2])
    with cc1:
        gran = st.pills(
            "Agrupar por", ["Día", "Semana", "Mes", "Año"],
            default="Mes", key="evo_prov_gran",
            label_visibility="collapsed",
        ) or "Mes"
    with cc2:
        _meas_opts = ["Total Compras (S/)"] + (["Cantidad"] if col_cant else [])
        meas = st.selectbox(
            "Métrica", _meas_opts,
            key="evo_prov_meas", label_visibility="collapsed",
        )
    with cc3:
        # Multiselect con búsqueda, máx. 5 proveedores
        _prev_sel = st.session_state.get("evo_prov_sel") or []
        # Garantizar que los previamente seleccionados sigan en las opciones
        _valid_prev = [p for p in _prev_sel if p in _todos_provs]
        _default_provs = _valid_prev if _valid_prev else _todos_provs[:3]
        prov_sel = st.multiselect(
            "Seleccionar proveedores (máx. 5)",
            _todos_provs,
            default=_default_provs,
            max_selections=5,
            key="evo_prov_sel",
            label_visibility="collapsed",
            placeholder="Buscar proveedor...",
        ) or _todos_provs[:3]

    es_valor = (meas == "Total Compras (S/)")

    # ── Calcular periodos según granularidad ──────────────────────────────
    fe_s = pd.to_datetime(base["fecha"], errors="coerce")
    if gran == "Día":
        base["per"] = fe_s.dt.date.astype(str)
    elif gran == "Semana":
        _iso = fe_s.dt.isocalendar()
        base["per"] = (_iso["year"].astype("Int64").astype(str) + "-S"
                       + _iso["week"].astype("Int64").astype(str).str.zfill(2))
    elif gran == "Año":
        base["per"] = fe_s.dt.year.astype("Int64").astype(str)
    else:  # Mes
        base["per"] = fe_s.dt.to_period("M").astype(str)

    base["m"] = base["valor"] if es_valor else base["cant"]
    base_f = base[base["prov"].isin(prov_sel)].copy()
    base_f = base_f[base_f["per"].notna() & (base_f["per"] != "<NA>")]

    if base_f.empty:
        st.info("Sin datos para los proveedores seleccionados.")
        return

    periodos = sorted(base_f["per"].unique())

    # ── Gráfico principal: barras agrupadas + range-slider ─────────────────
    fig_main = go.Figure()
    for i, prov in enumerate(prov_sel):
        grp = base_f[base_f["prov"] == prov].groupby("per")["m"].sum().reindex(
            periodos, fill_value=0)
        fig_main.add_bar(
            x=periodos, y=grp.values,
            name=_compras_truncar(prov, 32),
            marker_color=PALETA_CALLAI[i % len(PALETA_CALLAI)],
            hovertemplate=(
                "<b>" + _compras_truncar(prov, 32) + "</b><br>"
                + "%{x}<br>"
                + ("S/ %{y:,.0f}" if es_valor else "%{y:,.0f}")
                + "<extra></extra>"
            ),
        )

    _pref_y = "S/ " if es_valor else ""
    _compras_layout(fig_main, alto=420)
    fig_main.update_layout(
        barmode="group",
        xaxis=dict(
            type="category",
            tickangle=-30,
            rangeslider=dict(
                visible=True,
                thickness=0.10,
                bgcolor="#f0edfe",
                bordercolor="#6c5ce7",
                borderwidth=1,
            ),
        ),
        yaxis=dict(tickprefix=_pref_y, tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(size=11)),
        hovermode="x unified",
        margin=dict(l=10, r=10, t=10, b=70),
    )

    # Mostrar 12 periodos iniciales si hay más
    if len(periodos) > 12:
        fig_main.update_xaxes(
            range=[len(periodos) - 12.5, len(periodos) - 0.5]
        )

    st.plotly_chart(fig_main, use_container_width=True, key="evo_prov_main_chart")
    st.caption("Arrastra la barra inferior para desplazarte en el tiempo  ⓘ")

    # ── Estado de foco (proveedor + producto) ─────────────────────────────
    prov_focus = st.session_state.get("evo_prov_focus")
    prod_focus = st.session_state.get("evo_prov_prodfocus")

    # Si el proveedor en foco ya no está en la selección, resetear
    if prov_focus not in prov_sel:
        prov_focus = prov_sel[0] if prov_sel else None
        prod_focus = None
        st.session_state["evo_prov_focus"] = prov_focus
        st.session_state["evo_prov_prodfocus"] = None

    # Selector de proveedor activo (chips debajo del gráfico)
    if len(prov_sel) > 1:
        _sel_prov = st.pills(
            "Proveedor activo",
            prov_sel,
            format_func=lambda p: _compras_truncar(p, 28),
            default=prov_focus,
            key="evo_prov_chips",
            label_visibility="collapsed",
        )
        if _sel_prov and _sel_prov != prov_focus:
            st.session_state["evo_prov_focus"] = _sel_prov
            st.session_state["evo_prov_prodfocus"] = None
            st.rerun()
    else:
        prov_focus = prov_sel[0]
        st.session_state["evo_prov_focus"] = prov_focus

    prov_focus = st.session_state.get("evo_prov_focus") or (prov_sel[0] if prov_sel else None)
    if not prov_focus:
        return

    # ── Panel de detalle del proveedor ────────────────────────────────────
    st.divider()
    sub_prov = base[base["prov"] == prov_focus]

    # Calcular KPIs del proveedor
    _total_prov    = float(sub_prov["valor"].sum())
    _pct_part      = _total_prov / _tot_all * 100
    _num_ordenes   = int(sub_prov.shape[0]) if not col_cant else int(
        pd.to_numeric(sub_prov["cant"], errors="coerce").count())
    _num_productos = int(sub_prov["prod"].nunique()) if col_prod else 0
    _ultima_fecha  = "—"
    if col_fecha:
        _uf = pd.to_datetime(sub_prov["fecha"], errors="coerce").dropna()
        if not _uf.empty:
            _ultima_fecha = _uf.max().strftime("%d/%m/%Y")

    # Rango para el número top (1 = mayor proveedor)
    _rank = next((i + 1 for i, p in enumerate(_todos_provs) if p == prov_focus), None)
    _rank_badge = f"Top {_rank}" if _rank and _rank <= 10 else ""

    col_det_izq, col_det_der = st.columns([1.1, 1])

    with col_det_izq:
        # Cabecera del proveedor
        st.markdown(
            f"**Detalle del proveedor seleccionado**\n\n"
            f"### {prov_focus}"
            + (f" &nbsp; <span style='background:#6c5ce7;color:#fff;"
               f"border-radius:999px;padding:2px 10px;font-size:12px;"
               f"font-weight:600'>{_rank_badge}</span>" if _rank_badge else ""),
            unsafe_allow_html=True,
        )

        # KPIs en fila
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Compras", f"S/ {_total_prov:,.0f}")
        k2.metric("% Participación", f"{_pct_part:.1f}%")
        k3.metric("Órdenes de compra", f"{_num_ordenes:,}")
        k4.metric("Productos", f"{_num_productos:,}")
        k5.metric("Última compra", _ultima_fecha)

        # Mini sparkline de evolución del proveedor (área)
        if col_fecha:
            _sp = sub_prov.copy()
            _sp["mes"] = pd.to_datetime(
                _sp["fecha"], errors="coerce").dt.to_period("M").astype(str)
            _sp_g = (_sp[_sp["mes"].notna() & (_sp["mes"] != "<NA>")]
                     .groupby("mes", as_index=False)["valor"].sum()
                     .sort_values("mes"))
            if len(_sp_g) >= 2:
                st.markdown("**Evolución de compras del proveedor**")
                fig_sp = go.Figure(go.Scatter(
                    x=_sp_g["mes"], y=_sp_g["valor"],
                    mode="lines+markers",
                    line=dict(color=ACENTO, width=2),
                    marker=dict(size=5),
                    fill="tozeroy",
                    fillcolor="rgba(108,92,231,0.10)",
                    hovertemplate="%{x}: S/ %{y:,.0f}<extra></extra>",
                ))
                _compras_layout(fig_sp, alto=180)
                fig_sp.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(type="category", tickangle=-30,
                               tickfont=dict(size=10)),
                    yaxis=dict(tickprefix="S/ ", tickformat=",.0f",
                               tickfont=dict(size=10)),
                    showlegend=False,
                )
                st.plotly_chart(fig_sp, use_container_width=True,
                                key="evo_prov_sparkline")

    with col_det_der:
        # Tabla top productos del proveedor
        if col_prod:
            st.markdown("**Top productos comprados a este proveedor**")
            _top_prod = (sub_prov.groupby("prod", as_index=False)["valor"]
                         .sum()
                         .sort_values("valor", ascending=False)
                         .head(8))
            _tot_prov = float(_top_prod["valor"].sum()) or 1.0

            # Construir tabla estilizada con % participación
            filas_prod = []
            for rk, row in enumerate(_top_prod.itertuples(), 1):
                _p_pct = row.valor / _tot_prov * 100
                filas_prod.append({
                    "#": rk,
                    "Producto": _compras_truncar(row.prod, 30),
                    "Total Compras (S/)": f"S/ {row.valor:,.0f}",
                    "% Participación": f"{_p_pct:.1f}%",
                    "_prod_raw": row.prod,
                })

            # Mostrar como dataframe con click para drill
            df_prod_tbl = pd.DataFrame(filas_prod)[
                ["#", "Producto", "Total Compras (S/)", "% Participación"]
            ]
            st.dataframe(
                df_prod_tbl,
                hide_index=True,
                use_container_width=True,
                height=min(320, 60 + 35 * len(df_prod_tbl)),
            )

            # Selector de producto para drill-down
            _prods_lista = [r["_prod_raw"] for r in filas_prod]
            _lbl_drill = "Haz clic en un producto para ver a qué otros proveedores se les compró"
            _prod_drill = st.selectbox(
                _lbl_drill,
                ["(ninguno)"] + _prods_lista,
                format_func=lambda p: "— selecciona un producto —" if p == "(ninguno)"
                            else _compras_truncar(p, 40),
                key="evo_prov_proddrill",
                label_visibility="visible",
            )
            if _prod_drill and _prod_drill != "(ninguno)":
                st.session_state["evo_prov_prodfocus"] = _prod_drill
            prod_focus = st.session_state.get("evo_prov_prodfocus")

    # ── Tabla "Otros proveedores que también vendieron X" ─────────────────
    if prod_focus and prod_focus != "(ninguno)" and col_prod:
        st.divider()
        st.markdown(
            f"**Otros proveedores que también vendieron: "
            f"<span style='color:#6c5ce7'>{_compras_truncar(prod_focus, 50)}</span>**",
            unsafe_allow_html=True,
        )
        sub_prod = base[base["prod"] == prod_focus].copy()
        _otros = (sub_prod.groupby("prov", as_index=False)["valor"]
                  .sum()
                  .sort_values("valor", ascending=False))
        _tot_prod = float(_otros["valor"].sum()) or 1.0

        if _otros.empty:
            st.info("Sin datos de otros proveedores para ese producto.")
        else:
            # Barras de progreso inline + valores
            _filas_otros = []
            for row in _otros.itertuples():
                _pct = row.valor / _tot_prod * 100
                _filas_otros.append({
                    "Proveedor": _compras_truncar(row.prov, 36),
                    "Total Compras (S/)": f"S/ {row.valor:,.0f}",
                    "% Participación": f"{_pct:.1f}%",
                    "_valor": row.valor,
                    "_pct": _pct,
                })

            # Mostrar con barras de progreso usando plotly horizontal
            fig_otros = go.Figure()
            for i, row in enumerate(reversed(_filas_otros)):
                fig_otros.add_bar(
                    x=[row["_valor"]],
                    y=[_compras_truncar(row["Proveedor"], 36)],
                    orientation="h",
                    marker_color=(ACENTO if row["Proveedor"]
                                  == _compras_truncar(prov_focus, 36) else "#a0aec0"),
                    text=[f"S/ {row['_valor']:,.0f}   {row['_pct']:.1f}%"],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="%{y}: S/ %{x:,.0f}<extra></extra>",
                )
            _compras_layout(fig_otros, alto=max(180, 38 * len(_filas_otros) + 60))
            fig_otros.update_layout(
                showlegend=False,
                barmode="overlay",
                xaxis=dict(visible=False),
                margin=dict(l=10, r=130, t=10, b=10),
            )
            st.plotly_chart(fig_otros, use_container_width=True,
                            key="evo_prov_otros_chart")

    # ── Consejo al pie ────────────────────────────────────────────────────
    st.info(
        "💡 **Consejo:** Utiliza los filtros superiores para analizar "
        "por familia, subfamilia o rango de fechas.",
        icon=None,
    )
