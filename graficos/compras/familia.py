"""graficos.compras.familia - drill de Familia.

Familia -> Subfamilia -> productos, con barras en el tiempo arriba y
paneles de composicion y top N abajo. El clic navega de nivel.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, GRIS_BORDE, SERIE_PRINCIPAL
from graficos.base import PALETA_CALLAI, _card, _compras_layout, _compras_truncar
from graficos.compras._comun import (_first_point, _periodo_serie)


@st.fragment
def _compras_familia_drill(d, col_fam, col_subfam, col_prod, col_valor,
                           col_cant, col_fecha):
    """Dashboard de Familia con drill-down (reemplaza la barra simple).

    - Granularidad Semana/Mes/Año, vista Apilado/Agrupado, medida Valor/Cantidad.
    - Drill: Familia (selectbox) → sus Subfamilias en el tiempo; Subfamilia
      (selectbox) refina el Top N de productos.
    - Paneles: composición (Familias o Subfamilias) + Top N productos.
    Series apiladas se limitan a Top 6 + «Otros» para no saturar.
    """
    if not (col_fam and col_fecha and col_valor):
        st.info("Faltan columnas (Familia, Fecha, Valor) para este gráfico.")
        return

    # ── Controles ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                        default="Mes", key="compras_fam_gran") or "Mes"
    with c2:
        vista = st.pills("Vista", ["Apilado", "Agrupado"],
                         default="Apilado", key="compras_fam_vista") or "Apilado"
    with c3:
        _meas = ["Valor S/"] + (["Cantidad"] if col_cant else [])
        meas = st.pills("Medir", _meas, default="Valor S/",
                        key="compras_fam_meas") or "Valor S/"
    with c4:
        topn = st.pills("Top", [5, 10, 20], default=10,
                        key="compras_fam_topn") or 10

    es_valor = (meas == "Valor S/")
    fe = pd.to_datetime(d[col_fecha], errors="coerce")

    valor_s = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    cant_s = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
              if col_cant else pd.Series(0.0, index=d.index))
    base = pd.DataFrame({
        "per": _periodo_serie(fe, gran).values,
        "fam": d[col_fam].astype(str).values,
        "sub": (d[col_subfam].astype(str).values if col_subfam else "—"),
        "prod": (d[col_prod].astype(str).values if col_prod else "—"),
        "valor": valor_s.values,
        "cant": cant_s.values,
    })
    base["m"] = base["valor"] if es_valor else base["cant"]
    base = base[base["per"].notna() & (base["per"] != "<NA>")]
    if base.empty or base["m"].sum() == 0:
        st.info("Sin datos en el rango seleccionado.")
        return

    def _fmt(v):
        return f"S/ {v:,.0f}" if es_valor else f"{v:,.0f}"

    # ── Estado de drill (por clic en las barras) + navegación ───────────
    fams_all = sorted(base["fam"].dropna().unique().tolist())
    focus_fam = st.session_state.get("compras_fam_focus")
    focus_sub = st.session_state.get("compras_fam_subfocus")
    if focus_fam not in fams_all:
        focus_fam, focus_sub = None, None

    desglose = "Total familia"
    nav = st.columns([1.1, 1.5, 1.4, 3])
    with nav[0]:
        if st.button("↩ Todas", key="cf_bc_all", use_container_width=True,
                     disabled=(focus_fam is None)):
            st.session_state["compras_fam_focus"] = None
            st.session_state["compras_fam_subfocus"] = None
            st.rerun()
    with nav[1]:
        if focus_fam is not None and st.button(
                f"↩ {_compras_truncar(focus_fam, 18)}", key="cf_bc_fam",
                use_container_width=True, disabled=(focus_sub is None)):
            st.session_state["compras_fam_subfocus"] = None
            st.rerun()
    with nav[2]:
        # Al elegir una familia NO se desglosa solo: el usuario decide si
        # expandir a subfamilias en el gráfico del tiempo.
        if focus_fam is not None and col_subfam:
            desglose = st.pills("Desglose", ["Total familia", "Por subfamilia"],
                                default="Total familia", key="compras_fam_desglose",
                                label_visibility="collapsed") or "Total familia"
    with nav[3]:
        _ruta = ("Todas" + (f" › {focus_fam}" if focus_fam else "")
                 + (f" › {focus_sub}" if focus_sub else ""))
        st.caption(f"📂 {_ruta}  ·  clic en las barras para bajar de nivel")

    # ── Barras en el tiempo (serie = familia o subfamilia) ──────────────
    if focus_fam is None:
        tb, serie_col, titulo_ser = base, "fam", "familia"
    elif desglose == "Por subfamilia":
        tb, serie_col, titulo_ser = base[base["fam"] == focus_fam], "sub", "subfamilia"
    else:
        tb, serie_col, titulo_ser = base[base["fam"] == focus_fam], "fam", "familia"

    tot_ser = tb.groupby(serie_col)["m"].sum().sort_values(ascending=False)
    top_ser = tot_ser.head(6).index.tolist()
    tb = tb.copy()
    tb["serie"] = tb[serie_col].where(tb[serie_col].isin(top_ser), "Otros")
    g = tb.groupby(["per", "serie"], as_index=False)["m"].sum()
    periodos = sorted(g["per"].unique())
    orden = top_ser + (["Otros"] if (tb["serie"] == "Otros").any() else [])

    _pref = "S/ " if es_valor else ""
    _tpl = ("S/ %{y:,.0f}" if es_valor else "%{y:,.0f}")
    fig = go.Figure()
    for i, s in enumerate(orden):
        ss = (g[g["serie"] == s].set_index("per")["m"]
              .reindex(periodos, fill_value=0))
        color = (GRIS_BORDE if s == "Otros"
                 else PALETA_CALLAI[i % len(PALETA_CALLAI)])
        fig.add_bar(x=periodos, y=ss.values, name=_compras_truncar(s, 22),
                    marker_color=color,
                    hovertemplate="%{fullData.name}<br>%{x}<br>"
                                  + _tpl + "<extra></extra>")
    _compras_layout(fig, alto=380)
    _mn = "Valor" if es_valor else "Cantidad"
    fig.update_layout(
        title=f"{_mn} de compra por {gran.lower()} y {titulo_ser}"
              + ("" if focus_fam is None else f" — {_compras_truncar(focus_fam, 32)}"),
        barmode="stack" if vista == "Apilado" else "group",
        yaxis=dict(tickprefix=_pref, tickformat=",.0f"),
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10)))
    fig.update_xaxes(type="category", tickangle=-45)
    # Muchos periodos → rangeslider para deslizar horizontal + ventana inicial
    # (últimos ~12). El usuario arrastra el slider para ver periodos anteriores.
    if len(periodos) > 12:
        fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.07),
                         range=[len(periodos) - 12.5, len(periodos) - 0.5])

    # Clic en el gráfico:
    #  · en "Todas": clic en una familia → baja a esa familia (drill).
    #  · dentro de una familia: clic en una columna → filtra los paneles a ese
    #    periodo. `key` incluye el foco para limpiar la selección al navegar.
    _rst = st.session_state.get("compras_fam_time_rst", 0)
    _tkey = f"compras_g_fam_time_{focus_fam}_{focus_sub}_{gran}_{_rst}"
    _evt = st.plotly_chart(fig, use_container_width=True, key=_tkey,
                           on_select="rerun", selection_mode="points")
    _p = _first_point(_evt)
    periodo_sel = None
    if _p is not None:
        if focus_fam is None:
            _cn = _p.get("curve_number")
            if _cn is not None and 0 <= _cn < len(orden) and orden[_cn] != "Otros":
                st.session_state["compras_fam_focus"] = orden[_cn]
                st.session_state["compras_fam_subfocus"] = None
                st.session_state["compras_fam_time_rst"] = 0
                st.rerun()
        else:
            periodo_sel = _p.get("x")

    if periodo_sel is not None:
        cinfo, cbtn = st.columns([4, 1])
        cinfo.caption(f"📍 Paneles abajo filtrados al bloque **{periodo_sel}**. "
                      "Clic en otra columna para cambiar.")
        if cbtn.button("Ver todo el rango", key="compras_fam_verrango",
                       use_container_width=True):
            st.session_state["compras_fam_time_rst"] = _rst + 1
            st.rerun()
        base_b = base[base["per"] == periodo_sel]
    else:
        base_b = base

    # ── Panel composición (clic en una barra → baja de nivel) ───────────
    pc, pt = st.columns(2)
    with pc:
        if focus_fam is None:
            comp = base_b.groupby("fam")["m"].sum().sort_values()
            ctitulo = "Valorizado por Familia" if es_valor else "Cantidad por Familia"
        else:
            comp = (base_b[base_b["fam"] == focus_fam]
                    .groupby("sub")["m"].sum().sort_values())
            ctitulo = f"Subfamilias de {_compras_truncar(focus_fam, 26)}"
        comp_cats = list(comp.index)
        with _card("fam_comp", ctitulo, titulo_arriba=True):
            if comp.empty:
                st.info("Sin datos.")
            else:
                _cc = [SERIE_PRINCIPAL if (focus_sub and c == focus_sub) else ACENTO
                       for c in comp_cats]
                figc = go.Figure(go.Bar(
                    x=comp.values, y=[_compras_truncar(i, 26) for i in comp_cats],
                    orientation="h", marker_color=_cc,
                    text=[_fmt(v) for v in comp.values],
                    textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}<br>" + _tpl.replace("y", "x") + "<extra></extra>"))
                _compras_layout(figc, alto=max(240, 32 * len(comp) + 80))
                figc.update_layout(xaxis=dict(tickprefix=_pref, tickformat=",.0f"),
                                   margin=dict(l=10, r=70, t=10, b=10))
                _ckey = f"compras_g_fam_comp_{focus_fam}_{focus_sub}_{_rst}"
                _cevt = st.plotly_chart(figc, use_container_width=True, key=_ckey,
                                        on_select="rerun", selection_mode="points")
                _cp = _first_point(_cevt)
                if _cp is not None:
                    _idx = _cp.get("point_number")
                    if _idx is None:
                        _idx = _cp.get("point_index")
                    if _idx is not None and 0 <= _idx < len(comp_cats):
                        _cat = comp_cats[_idx]
                        if focus_fam is None:
                            st.session_state["compras_fam_focus"] = _cat
                            st.session_state["compras_fam_subfocus"] = None
                            st.rerun()
                        else:
                            st.session_state["compras_fam_subfocus"] = (
                                None if focus_sub == _cat else _cat)
                            st.rerun()
                st.caption("👆 Clic en una barra para "
                           + ("bajar a sus subfamilias."
                              if focus_fam is None else
                              "filtrar el Top de productos a esa subfamilia "
                              "(clic de nuevo para quitar)."))

    # ── Panel Top N productos (muestra Valor S/ + Cantidad) ─────────────
    with pt:
        scope = base_b
        if focus_fam is not None:
            scope = scope[scope["fam"] == focus_fam]
        if focus_sub is not None:
            scope = scope[scope["sub"] == focus_sub]
        _amb = (focus_sub or focus_fam or "todas las familias")
        with _card("fam_top", f"Top {topn} productos · {_compras_truncar(_amb, 24)}",
                   titulo_arriba=True):
            agg = scope.groupby("prod").agg(
                valor=("valor", "sum"), cant=("cant", "sum"), m=("m", "sum"))
            agg = agg.nlargest(topn, "m").sort_values("m")
            if agg.empty:
                st.info("Sin datos de productos.")
            else:
                _txt = [f"S/ {v:,.0f}" + (f"  ·  {c:,.0f} u" if col_cant else "")
                        for v, c in zip(agg["valor"], agg["cant"])]
                figt = go.Figure(go.Bar(
                    x=agg["m"].values, y=[_compras_truncar(i, 28) for i in agg.index],
                    orientation="h", marker_color=SERIE_PRINCIPAL,
                    text=_txt, textposition="outside", cliponaxis=False,
                    customdata=np.stack([agg["valor"].values, agg["cant"].values], axis=-1),
                    hovertemplate="%{y}<br>S/ %{customdata[0]:,.0f} · "
                                  "%{customdata[1]:,.0f} u<extra></extra>"))
                _compras_layout(figt, alto=max(240, 32 * len(agg) + 80))
                figt.update_layout(xaxis=dict(tickprefix=_pref, tickformat=",.0f"),
                                   margin=dict(l=10, r=120, t=10, b=10))
                st.plotly_chart(figt, use_container_width=True, key="compras_g_fam_top")
