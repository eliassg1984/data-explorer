"""
graficos.ajuste — dashboard de gráficos de Ajuste de Inventario.

Evolución temporal, comparativa mensual, cascada (waterfall), mapa de calor y
distribución, con panel de análisis. Punto de entrada público:
renderizar_graficos_ajuste(). Los helpers de infraestructura (cards, layout,
resolución de columnas, motor genérico) vienen de graficos.base.
"""

import datetime as _dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, GRIS_BORDE, GRIS_FONDO,
    PALETA_SERIES, SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _card, _layout, _render_rail, _resolver, _slug, _wrap_cat,
    renderizar_graficos_genericos,
)


# Rail derecho de Ajuste (mismo componente compartido que Compras). El id
# (izquierda) es el string que consume el dispatch de gráficos; el label
# (derecha) es lo que se pinta en el botón. "Tabla" es un item más del rail
# (misma idea que Compras): al elegirlo se renderiza la tabla AgGrid vía el
# callback `tabla_cb` que inyecta app.py.
_AJUSTE_RAIL_CATEGORIAS = (
    ("Composición", (("Cascada",        "Cascada"),
                     ("Mapa de calor",  "Mapa de calor"),
                     ("Distribución",   "Distribución"))),
    ("Tiempo",      (("Evolución",           "Evolución"),
                     ("Comparativa mensual", "Comparativa"))),
    ("Datos",       (("Tabla",          "Tabla"),)),
)


def _layout_aj(**overrides):
    """`_layout` con el look del estándar del rail (igual que Compras).

    Solo cambia dos cosas respecto al `_layout` genérico para que los gráficos
    de Ajuste combinen con la tarjeta como en Compras:
      · plot_bgcolor TRANSPARENTE — funde con el fondo de la tarjeta en vez de
        pintar una caja blanca dentro.
      · grilla del eje X oculta (Compras solo conserva la del eje Y).
    La paleta ya es común (PALETA_SERIES). El color SEMÁNTICO de cada gráfico
    (verde/rojo del waterfall, colorscale del mapa de calor, etc.) se conserva:
    es propio del tipo de gráfico, no del tema. No se toca el `_layout`
    compartido para no restilizar Ventas/Inventario/Receta."""
    lay = _layout(**overrides)
    lay["plot_bgcolor"] = "rgba(0,0,0,0)"
    _xaxis = dict(lay.get("xaxis", {}))
    _xaxis["showgrid"] = False
    lay["xaxis"] = _xaxis
    return lay


def _graf_evolucion_ajuste(df, col_fecha, col_familia, col_ajuste_val, col_valorizado):
    """Serie temporal con range-selector + range-slider + eje dual opcional."""
    if not col_fecha:
        st.info("Sin columna de fecha — no se puede graficar la evolución.")
        return

    df = df.copy()
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
    df = df.dropna(subset=[col_fecha]).sort_values(col_fecha)
    if df.empty:
        st.info("Sin fechas válidas en el rango seleccionado.")
        return

    fig = go.Figure()

    if col_familia and col_familia in df.columns:
        for i, fam in enumerate(sorted(df[col_familia].dropna().unique())):
            df_fam = (df[df[col_familia] == fam]
                      .groupby(col_fecha, as_index=False)[col_ajuste_val].sum()
                      .sort_values(col_fecha))
            color = PALETA_SERIES[i % len(PALETA_SERIES)]
            fig.add_trace(go.Scatter(
                x=df_fam[col_fecha], y=df_fam[col_ajuste_val],
                name=str(fam), mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=6, symbol="circle"),
                hovertemplate=(
                    f"<b>{fam}</b><br>"
                    "Fecha: %{x|%d/%m/%Y}<br>"
                    "Ajuste: <b>S/ %{y:,.2f}</b><extra></extra>"
                ),
            ))
    else:
        agg = (df.groupby(col_fecha, as_index=False)[col_ajuste_val]
               .sum().sort_values(col_fecha))
        fig.add_trace(go.Scatter(
            x=agg[col_fecha], y=agg[col_ajuste_val],
            name="Ajuste valorizado", mode="lines+markers",
            line=dict(color=SERIE_PRINCIPAL, width=2.5),
            fill="tozeroy", fillcolor="rgba(108,92,231,0.10)",
            hovertemplate="Fecha: %{x|%d/%m/%Y}<br>Ajuste: <b>S/ %{y:,.2f}</b><extra></extra>",
        ))

    fig.add_hline(
        y=0, line_dash="dot", line_color="#ef4444", line_width=1.5,
        annotation_text="Equilibrio (0)",
        annotation_font_color="#ef4444",
        annotation_position="top right",
    )

    fig.update_layout(**_layout_aj(
        xaxis=dict(
            gridcolor=GRIS_BORDE,
            rangeselector=dict(
                buttons=[
                    dict(count=1,  label="1M",  step="month", stepmode="backward"),
                    dict(count=3,  label="3M",  step="month", stepmode="backward"),
                    dict(count=6,  label="6M",  step="month", stepmode="backward"),
                    dict(step="all", label="Todo"),
                ],
                bgcolor=GRIS_FONDO, activecolor=ACENTO,
                font=dict(size=12),
            ),
            rangeslider=dict(visible=True, thickness=0.06, bgcolor=GRIS_FONDO),
            type="date",
        ),
        yaxis=dict(gridcolor=GRIS_BORDE, tickprefix="S/ ", tickformat=",.2f"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    ))

    with _card("evolucion", "Evolución temporal"):
        st.plotly_chart(fig, use_container_width=True)

    if col_valorizado and col_valorizado in df.columns:
        with st.expander("📊 Comparativa: ajuste vs valorizado total (eje dual)"):
            agg2 = (df.groupby(col_fecha, as_index=False)
                    .agg(ajuste=(col_ajuste_val, "sum"), val=(col_valorizado, "sum"))
                    .sort_values(col_fecha))

            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            fig2.add_trace(go.Bar(
                x=agg2[col_fecha], y=agg2["ajuste"],
                name="Ajuste valorizado",
                marker_color=[SERIE_PRINCIPAL if v >= 0 else "#ef4444"
                              for v in agg2["ajuste"]],
                hovertemplate="Ajuste: S/ %{y:,.2f}<extra></extra>",
            ), secondary_y=False)
            fig2.add_trace(go.Scatter(
                x=agg2[col_fecha], y=agg2["val"],
                name="Valorizado total",
                mode="lines+markers",
                line=dict(color="#16a34a", width=2.5),
                hovertemplate="Valorizado: S/ %{y:,.2f}<extra></extra>",
            ), secondary_y=True)

            fig2.update_layout(**_layout_aj(
                title="Ajuste vs Valorizado total",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.05, x=0),
            ))
            fig2.update_yaxes(
                tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE,
                title_text="Ajuste valorizado", secondary_y=False,
            )
            fig2.update_yaxes(
                tickprefix="S/ ", tickformat=",.2f",
                title_text="Valorizado total", secondary_y=True,
            )
            with _card("evolucion_dual"):
                st.plotly_chart(fig2, use_container_width=True)


def _graf_comparativa_mensual(df, col_fecha, col_ajuste_val):
    """Comparativa mensual: barras de ajuste neto por mes.

    Pensada para la pestaña Histórico: da una lectura rápida de qué meses
    tuvieron sobrante o faltante neto sin necesidad de leer la línea."""
    if not col_fecha:
        st.info("Sin columna de fecha para la comparativa mensual.")
        return

    d = df.copy()
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=[col_fecha])
    if d.empty:
        st.info("Sin fechas válidas para la comparativa mensual.")
        return

    d["_mes"] = d[col_fecha].dt.to_period("M").dt.to_timestamp()
    agg = d.groupby("_mes", as_index=False)[col_ajuste_val].sum().sort_values("_mes")

    fig = go.Figure(go.Bar(
        x=agg["_mes"], y=agg[col_ajuste_val],
        marker_color=[SERIE_PRINCIPAL if v >= 0 else "#ef4444"
                      for v in agg[col_ajuste_val]],
        text=[f"S/ {v:,.0f}" for v in agg[col_ajuste_val]],
        textposition="outside",
        hovertemplate="%{x|%b %Y}<br><b>S/ %{y:,.2f}</b><extra></extra>",
    ))
    fig.update_layout(**_layout_aj(
        xaxis=dict(dtick="M1", tickformat="%b %Y", gridcolor=GRIS_BORDE),
        yaxis=dict(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE),
        showlegend=False, height=360,
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=GRIS_BORDE, line_width=1)

    with _card("comparativa", "Comparativa mensual"):
        evento = st.plotly_chart(
            fig,
            use_container_width=True,
            key="comparativa_mensual",
            on_select="rerun",
            selection_mode="points",
        )

    # ── Drill-down: clic en un mes → filas de ese mes ────────────────────
    sel = evento.get("selection", {}) if evento else {}
    puntos = sel.get("points", [])
    if puntos:
        mes_clic = pd.to_datetime(puntos[0].get("x"))
        detalle = d[d["_mes"] == mes_clic.replace(day=1)].drop(columns=["_mes"])
        if not detalle.empty:
            st.markdown(
                f"**Detalle de {mes_clic:%B %Y}** — {len(detalle)} filas · "
                f"ajuste neto S/ {detalle[col_ajuste_val].sum():,.2f}"
            )
            st.dataframe(detalle, use_container_width=True)


def _graf_waterfall_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto=None, col_valorizado=None,
                           col_cantidad=None):
    """Cascada (Waterfall) por familia/área — SOLO el gráfico.

    Los análisis complementarios (Faltantes, Sobrantes, Extremos, etc.) que
    antes vivían aquí como 8 tabs se movieron a `_panel_analisis_ajuste`,
    que renderiza el contenedor derecho de la vista Gráficos de Ajuste.

    `col_producto`, `col_valorizado` y `col_cantidad` se mantienen en la
    firma por compatibilidad (test_graficos.py y llamadas existentes las
    pasan); ya no se usan aquí.
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para el gráfico de cascada.")
        return

    # ── Controles de exclusión (arriba del card) ───────────────────────
    # Errores manuales en la data (ej. un producto con faltante enorme)
    # pueden dominar la cascada. El usuario puede excluir por top N o por
    # producto puntual; el filtro se aplica al df antes de calcular agg.
    excluidos = set()
    if col_producto and col_producto in df.columns:
        _prod_s = df[col_producto].astype(str)
        # Ranking global por |ajuste| — el "top faltantes+sobrantes".
        _rank = (df.groupby(col_producto, as_index=False)[col_ajuste_val]
                 .sum())
        _rank["_abs"] = _rank[col_ajuste_val].abs()
        _rank = _rank.sort_values("_abs", ascending=False)
        _prods_ranked = _rank[col_producto].astype(str).tolist()
        _todos_prods = sorted(_prod_s.dropna().unique().tolist())

        # Los dos controles viven dentro de un popover: se usan para corregir
        # errores de captura, no en cada análisis, así que no merecen ocupar
        # ancho fijo arriba del gráfico. El badge del label muestra cuántos
        # productos quedan excluidos aunque el popover esté cerrado.
        #
        # El count se lee de session_state ANTES de dibujar los widgets: el
        # label se arma arriba, pero las keys son las mismas de adentro, así
        # que tras el primer rerun el número ya es el correcto (mismo patrón
        # que los chips de filtro en app.py).
        _n_top = int(st.session_state.get("ajuste_cascada_excl_top") or 0)
        _n_man = len(st.session_state.get("ajuste_cascada_excl_manual") or [])
        _n_prev = len(set(_prods_ranked[:_n_top]) |
                      set(st.session_state.get("ajuste_cascada_excl_manual")
                          or []))
        _lbl = ":material/filter_alt_off: Excluir productos"
        if _n_prev:
            _lbl += f" :violet-badge[{_n_prev}]"

        # use_container_width=False: el popover toma solo su ancho natural
        # y no deja un rectangulo vacio al costado (antes vivia en un
        # st.columns([1,3]) y el otro 75% quedaba en blanco).
        with st.popover(_lbl, use_container_width=False):
                _top_ex = st.select_slider(
                    "Excluir el top N por |ajuste|",
                    options=[0, 1, 3, 5, 8, 10],
                    value=0, key="ajuste_cascada_excl_top",
                    format_func=lambda n: "Ninguno" if n == 0 else f"Top {n}",
                    help="Quita los N productos de mayor ajuste absoluto — "
                         "sirve cuando un error de captura domina la cascada.",
                )
                _top_ex = int(_top_ex or 0)
                _manual = st.multiselect(
                    "…o elegir productos puntuales", _todos_prods,
                    key="ajuste_cascada_excl_manual",
                    placeholder="Buscar producto…",
                )

        if _top_ex > 0:
            excluidos.update(_prods_ranked[:_top_ex])
        excluidos.update(str(p) for p in _manual)

        if excluidos:
            df = df[~df[col_producto].astype(str).isin(excluidos)]

    agg = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
           .sum().sort_values(col_ajuste_val))
    if agg.empty:
        st.info("No queda nada para graficar después de las exclusiones.")
        return
    total = float(agg[col_ajuste_val].sum())

    # Peso relativo (sobre suma de |valores|): siempre suma 100%, no se
    # confunde con signos mezclados (una barra + y varias -). El signo lo
    # comunica el color de la barra.
    abs_sum = float(agg[col_ajuste_val].abs().sum()) or 1.0
    pesos = [abs(v) / abs_sum * 100 for v in agg[col_ajuste_val]]

    def _fmt_pct(p):
        if p < 0.5:
            return "<1%"
        return f"{p:.0f}%"

    text_barras = [
        f"S/ {v:,.0f}<br>"
        f"<span style='font-size:10px;opacity:0.65'>{_fmt_pct(p)}</span>"
        for v, p in zip(agg[col_ajuste_val], pesos)
    ] + [f"<b>S/ {total:,.0f}</b>"]

    # Insight automático: si un item concentra mucho, decirlo en el título.
    top_peso = max(pesos) if pesos else 0.0
    top_idx = pesos.index(top_peso) if pesos else None
    top_nombre = (str(agg[grp_col].iloc[top_idx]).upper()
                  if top_idx is not None else "")
    if top_peso >= 60:
        insight = f"{top_nombre} concentra el {top_peso:.0f}% del ajuste"
    elif top_peso >= 40:
        insight = f"{top_nombre} explica el {top_peso:.0f}% del ajuste"
    else:
        insight = None

    title_html = f"Cascada de ajuste valorizado por {grp_col}"
    if insight:
        title_html += (f"<br><span style='font-size:12px;font-weight:400;"
                       f"color:#8a8a8a'>{insight}</span>")

    # Tooltip enriquecido: al hover sobre una familia, top 10 de sus
    # productos por |ajuste|. Requiere col_producto; si no está, tooltip
    # queda como antes (solo peso).
    _tops_por_fam = {}
    if col_producto and col_producto in df.columns:
        for _fam in agg[grp_col].tolist():
            _sub = df[df[grp_col].astype(str) == str(_fam)]
            if _sub.empty:
                _tops_por_fam[str(_fam)] = ""
                continue
            _t = (_sub.groupby(col_producto, as_index=False)[col_ajuste_val]
                  .sum())
            _t["_abs"] = _t[col_ajuste_val].abs()
            _t = _t.sort_values("_abs", ascending=False).head(10)
            _lines = []
            for i, (_, row) in enumerate(_t.iterrows(), 1):
                _nom = str(row[col_producto])
                if len(_nom) > 32:
                    _nom = _nom[:29] + "…"
                _lines.append(f"{i}. {_nom} — S/ {row[col_ajuste_val]:,.0f}")
            _tops_por_fam[str(_fam)] = "<br>".join(_lines)

    _cd = []
    for _fam, _p in zip(agg[grp_col].tolist(), pesos):
        _cd.append([_p, _tops_por_fam.get(str(_fam), "")])
    _cd.append([100.0, ""])  # TOTAL

    _hover_familias = ("<b>%{x}</b><br>S/ %{y:,.2f}"
                       "<br>Peso: %{customdata[0]:.1f}%")
    if col_producto and col_producto in df.columns:
        _hover_familias += ("<br>─────────────<br>"
                            "<b>Top productos</b><br>%{customdata[1]}")
    _hover_familias += "<extra></extra>"

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(agg) + ["total"],
        x=agg[grp_col].tolist() + ["TOTAL"],
        y=agg[col_ajuste_val].tolist() + [None],
        text=text_barras,
        textposition="outside",
        connector=dict(line=dict(color="#9aa0a6", width=1.5, dash="solid")),
        increasing=dict(marker=dict(color="rgba(108,92,231,0.85)")),
        decreasing=dict(marker=dict(color="rgba(239,68,68,0.85)")),
        totals=dict(marker=dict(color="#374151")),
        customdata=_cd,
        hovertemplate=_hover_familias,
    ))
    fig.update_layout(**_layout_aj(
        title=title_html,
        xaxis=dict(tickangle=-35, gridcolor=GRIS_BORDE),
        yaxis=dict(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE),
        showlegend=False, height=380, waterfallgap=0.5,
    ))
    _xcats = agg[grp_col].tolist() + ["TOTAL"]
    fig.update_xaxes(tickmode="array", tickvals=_xcats,
                     ticktext=_wrap_cat(_xcats))

    # ── Drill: clic en una familia → top-N de productos abajo ─────────────
    # Categorías clickeables (todas menos "TOTAL"). El foco vive en
    # session_state; clic en la misma barra que ya está en foco lo apaga
    # (toggle), igual que el drill de Proveedor en Compras.
    _cats_clic = agg[grp_col].astype(str).tolist()
    _focus_key = "ajuste_cascada_focus"
    focus = st.session_state.get(_focus_key)
    if focus not in _cats_clic:
        focus = None
        st.session_state[_focus_key] = None

    with _card("cascada", "Cascada por familia"):
        # Layout responsivo: sin foco la cascada ocupa todo el ancho;
        # con foco se abre un panel derecho con el drill (60/40 aprox).
        if focus:
            col_g, col_d = st.columns([1.55, 1])
        else:
            col_g, col_d = st.container(), None

        with col_g:
            # Key incluye el foco: al cambiar de foco (o volver a None) la
            # key cambia y Streamlit RECREA el widget desde cero, limpiando
            # la selection persistente. Sin esto la selection sobrevive al
            # rerun y provoca un toggle infinito (parpadeo).
            evt = st.plotly_chart(
                fig, use_container_width=True,
                key=f"ajuste_cascada_chart_{focus or 'none'}",
                on_select="rerun", selection_mode="points",
            )
        # Extraer punto clicado (tolerante a formato).
        _pt = None
        try:
            _sel = getattr(evt, "selection", None) or (
                evt.get("selection") if isinstance(evt, dict) else None)
            _pts = (_sel or {}).get("points", [])
            _pt = _pts[0] if _pts else None
        except Exception:
            _pt = None
        if _pt is not None:
            _x = _pt.get("x")
            if _x is not None and str(_x) != "TOTAL":
                _clicked = str(_x)
                # Toggle: mismo → apagar; distinto → cambiar foco.
                _new = None if _clicked == focus else _clicked
                if _new != focus:
                    st.session_state[_focus_key] = _new
                    st.rerun()

        # ── Panel de drill (solo si hay foco) — a la derecha ───────────
        if focus and col_d is not None:
            _det = df[df[grp_col].astype(str) == focus]
            # Dimensión a mostrar: producto si existe, si no la otra
            # (área/familia). Nombre humano para el header.
            dim = col_producto or (col_area if grp_col == col_familia
                                   else col_familia)
            dim_lbl = "producto" if dim == col_producto else str(dim).lower()

            with col_d:
                hdr_l, hdr_r = st.columns([4, 1])
                with hdr_l:
                    _total_focus = float(
                        df[df[grp_col].astype(str) == focus][col_ajuste_val].sum()
                    )
                    _color_total = "#A32D2D" if _total_focus < 0 else "#0F6E56"
                    st.markdown(
                        f"**{focus}**<br>"
                        f"<span style='font-size:11px;color:#8a8a8a'>"
                        f"top {dim_lbl}s · faltante total "
                        f"<span style='color:{_color_total};font-weight:500'>"
                        f"S/ {_total_focus:,.0f}</span></span>",
                        unsafe_allow_html=True,
                    )
                with hdr_r:
                    if st.button("✕", key="ajuste_cascada_cerrar",
                                 use_container_width=True,
                                 help="Cerrar el drill"):
                        st.session_state[_focus_key] = None
                        st.rerun()
                topn = st.pills(
                    "Top", [5, 10, 20], default=10,
                    key="ajuste_cascada_topn",
                    label_visibility="collapsed",
                    format_func=lambda n: f"Top {n}",
                ) or 10

                if not dim or dim not in _det.columns:
                    st.info("No hay una columna adecuada para desglosar "
                            "esta familia.")
                else:
                    _sub = (_det.groupby(dim, as_index=False)[col_ajuste_val]
                            .sum())
                    _sub["_abs"] = _sub[col_ajuste_val].abs()
                    _sub = _sub.sort_values("_abs", ascending=False).head(int(topn))
                    if _sub.empty or _sub["_abs"].sum() == 0:
                        st.info("Sin datos para el drill de esta familia.")
                    else:
                        # Barras horizontales, mayor arriba, color por signo.
                        _sub = _sub.sort_values(col_ajuste_val, ascending=True)
                        _colors = ["rgba(108,92,231,0.85)"
                                   if v >= 0 else "rgba(239,68,68,0.85)"
                                   for v in _sub[col_ajuste_val]]
                        # Truncar nombres largos para el panel angosto.
                        _y_labels = [(str(n)[:34] + "…") if len(str(n)) > 35
                                     else str(n)
                                     for n in _sub[dim].tolist()]
                        fig_d = go.Figure(go.Bar(
                            x=_sub[col_ajuste_val].tolist(),
                            y=_y_labels,
                            orientation="h",
                            marker=dict(color=_colors),
                            text=[f"S/ {v:,.0f}" for v in _sub[col_ajuste_val]],
                            # textposition='auto': Plotly pone el label
                            # dentro cuando la barra es grande y fuera
                            # cuando es chica. Con 'outside' + cliponaxis
                            # las barras largas dibujaban el label encima
                            # del eje X.
                            textposition="auto",
                            insidetextanchor="end",
                            hovertemplate=("%{y}<br><b>S/ %{x:,.2f}</b>"
                                           "<extra></extra>"),
                        ))
                        fig_d.update_layout(**_layout_aj(
                            # title_text='': evita el literal "undefined" que
                            # sale al pasar title=None en algunas versiones
                            # de Plotly.
                            title_text="",
                            xaxis=dict(tickprefix="S/ ", tickformat=",.0f",
                                       gridcolor=GRIS_BORDE, zeroline=True,
                                       zerolinecolor=GRIS_BORDE,
                                       # nticks=4: evita "-15,000 -10,000
                                       # -5,000 0" apretados y superpuestos.
                                       nticks=4),
                            # showticklabels=True: _layout oculta el Y por
                            # default; aquí Y son NOMBRES de producto, no
                            # valores — hay que forzarlos.
                            yaxis=dict(gridcolor=GRIS_BORDE,
                                       showticklabels=True,
                                       automargin=True,
                                       tickfont=dict(size=10)),
                            showlegend=False,
                            # Altura proporcional al nº de barras: cada fila
                            # recibe ~26px fijos (antes 380px repartidos entre
                            # todas → filas altas y barras gordas con top 5).
                            # Con filas cortas, barra y hueco se achican juntos.
                            height=max(180, 26 * len(_sub) + 60),
                            bargap=0.35,
                            margin=dict(l=4, r=12, t=10, b=10),
                        ))
                        st.plotly_chart(
                            fig_d, use_container_width=True,
                            key=f"ajuste_cascada_drill_{_slug(focus)}",
                        )
        else:
            st.caption("💡 Clic en una barra para ver su top "
                       "de productos.")


def _panel_analisis_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto, col_valorizado, col_cantidad,
                           ambito):
    """Panel derecho: UNA mini-tabla analítica a la vez, en pestañas.

    Vive dentro del contenedor blanco derecho de la vista Gráficos de
    Ajuste. Usa st.tabs (8 pestañas); si no caben en el ancho, Streamlit
    aplica scroll horizontal automáticamente. Para añadir un mini-gráfico
    nuevo: sumar el nombre a `tab_names` y su bloque `with tabs[i]:`.

    Las 8 vistas responden a preguntas distintas del mismo df activo:
      0. Faltantes por familia (top 5 negativos)
      1. Sobrantes por familia (top 5 positivos)
      2. Productos críticos (top 10 negativos, nivel producto)
      3. Ranking por área (+ % sobre |total|)
      4. Resumen de familia (N productos, ajuste, % s/ valorizado)
      5. Movimientos extremos (top+bottom en una tabla)
      6. Ranking por valorizado
      7. Ranking por cantidad (unidades)

    `ambito` se mantiene en la firma por si más adelante se usa para
    diferenciar contenido entre «Del periodo» e «Histórico»; hoy no lo
    necesita (las pestañas son las mismas para ambos).
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita familia o área para el panel analítico.")
        return

    agg = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
           .sum().sort_values(col_ajuste_val))

    tab_names = [
        "Faltantes",
        "Sobrantes",
        "Críticos",
        "Por área",
        "Resumen",
        "Extremos",
        "Valorizado",
        "Cantidad",
    ]
    tabs = st.tabs(tab_names)

    def _fmt_soles(df_, col):
        df_ = df_.copy()
        df_[col] = df_[col].map(lambda v: f"S/ {v:,.2f}")
        return df_

    def _fmt_int(df_, col):
        df_ = df_.copy()
        df_[col] = df_[col].map(lambda v: f"{int(v):,}")
        return df_

    # 0 — Faltantes por familia
    with tabs[0]:
        st.caption("Top 5 faltantes")
        neg = agg.nsmallest(5, col_ajuste_val)[[grp_col, col_ajuste_val]]
        st.dataframe(_fmt_soles(neg, col_ajuste_val),
                     hide_index=True, use_container_width=True)

    # 1 — Sobrantes por familia
    with tabs[1]:
        st.caption("Top 5 sobrantes")
        pos = agg.nlargest(5, col_ajuste_val)[[grp_col, col_ajuste_val]]
        st.dataframe(_fmt_soles(pos, col_ajuste_val),
                     hide_index=True, use_container_width=True)

    # 2 — Productos críticos (top 10 negativos, nivel producto)
    with tabs[2]:
        if col_producto and col_producto in df.columns:
            st.caption("Top 10 productos más negativos")
            cols_p = [col_producto, col_ajuste_val]
            if grp_col in df.columns and grp_col not in cols_p:
                cols_p.insert(1, grp_col)
            prod_agg = (df.groupby(cols_p[:-1], as_index=False)[col_ajuste_val]
                          .sum()
                          .nsmallest(10, col_ajuste_val))
            st.dataframe(_fmt_soles(prod_agg, col_ajuste_val),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No hay columna de producto en el reporte.")

    # 3 — Ranking por área
    with tabs[3]:
        if col_area and col_area in df.columns:
            area_agg = (df.groupby(col_area, as_index=False)[col_ajuste_val]
                          .sum()
                          .sort_values(col_ajuste_val))
            _total_abs = abs(area_agg[col_ajuste_val]).sum() or 1
            area_agg["% |total|"] = (
                abs(area_agg[col_ajuste_val]) / _total_abs * 100
            ).round(1)
            area_agg["% |total|"] = area_agg["% |total|"].map(lambda v: f"{v:.1f}%")
            st.dataframe(_fmt_soles(area_agg, col_ajuste_val),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No hay columna de área en el reporte.")

    # 4 — Resumen familia (todas las familias, N productos + ajuste + %)
    with tabs[4]:
        if col_producto and col_producto in df.columns:
            resumen = (df.groupby(grp_col)
                         .agg(**{
                             "N° productos": (col_producto, "nunique"),
                             col_ajuste_val: (col_ajuste_val, "sum"),
                         })
                         .reset_index())
        else:
            resumen = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
                         .sum())
        resumen = resumen.reindex(
            resumen[col_ajuste_val].abs().sort_values(ascending=False).index
        )
        if col_valorizado and col_valorizado in df.columns:
            val_por_fam = df.groupby(grp_col)[col_valorizado].sum()
            resumen["% s/ valorizado"] = resumen.apply(
                lambda r: (r[col_ajuste_val] / val_por_fam.get(r[grp_col], 1) * 100)
                          if val_por_fam.get(r[grp_col], 0) else 0,
                axis=1,
            ).round(2).map(lambda v: f"{v:+.2f}%")
        st.dataframe(_fmt_soles(resumen, col_ajuste_val),
                     hide_index=True, use_container_width=True)

    # 5 — Movimientos extremos (5 más rojos + 5 más verdes en una tabla)
    with tabs[5]:
        neg5 = agg.nsmallest(5, col_ajuste_val)
        pos5 = agg.nlargest(5, col_ajuste_val)[::-1]  # descendente
        sep = pd.DataFrame({grp_col: ["———"], col_ajuste_val: [0.0]})
        extremos = pd.concat([neg5, sep, pos5], ignore_index=True)
        extremos[col_ajuste_val] = extremos[col_ajuste_val].map(
            lambda v: "" if v == 0 else f"S/ {v:,.2f}"
        )
        st.dataframe(extremos[[grp_col, col_ajuste_val]],
                     hide_index=True, use_container_width=True)

    # 6 — Ranking por valorizado (familias ordenadas por valorizado total)
    with tabs[6]:
        if col_valorizado and col_valorizado in df.columns:
            val_agg = (df.groupby(grp_col, as_index=False)[col_valorizado]
                         .sum()
                         .sort_values(col_valorizado, ascending=False))
            st.dataframe(_fmt_soles(val_agg, col_valorizado),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No hay columna de valorizado en el reporte.")

    # 7 — Ranking por cantidad (ajuste en unidades, no en soles)
    with tabs[7]:
        if col_cantidad and col_cantidad in df.columns:
            cant_agg = (df.groupby(grp_col, as_index=False)[col_cantidad]
                          .sum()
                          .sort_values(col_cantidad))
            st.dataframe(_fmt_int(cant_agg, col_cantidad),
                         hide_index=True, use_container_width=True)
        else:
            st.caption(
                "No se encontró la columna de cantidad de ajuste "
                "(se buscó 'AJUSTE', 'CANTIDAD AJUSTE')."
            )


def _graf_heatmap_ajuste(df, col_familia, col_area, col_ajuste_val):
    """Mapa de calor familia × área con escala divergente centrada en cero."""
    if not col_familia or not col_area:
        st.info("Se necesitan columnas de familia y área para el mapa de calor.")
        return

    pivot = df.pivot_table(
        index=col_familia, columns=col_area,
        values=col_ajuste_val, aggfunc="sum", fill_value=0,
    )
    text_mat = [[f"S/ {v:,.0f}" for v in row] for row in pivot.values]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        text=text_mat,
        texttemplate="%{text}",
        textfont=dict(size=10, color=TEXTO_PRINCIPAL),
        colorscale=[
            [0.0,  "#ef4444"],
            [0.45, "#fff7ed"],
            [0.5,  GRIS_FONDO],
            [0.55, "#f0fdf4"],
            [1.0,  "#16a34a"],
        ],
        zmid=0,
        colorbar=dict(title="Ajuste S/", tickformat=",.0f"),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Área: <b>%{x}</b><br>"
            "Ajuste: <b>S/ %{z:,.2f}</b><extra></extra>"
        ),
    ))
    fig.update_layout(**_layout_aj(
        title="Mapa de calor: ajuste valorizado por Familia × Área",
        xaxis=dict(tickangle=-30, side="bottom", gridcolor=GRIS_BORDE),
        yaxis=dict(autorange="reversed", gridcolor=GRIS_BORDE, showticklabels=True),
        # Evita que una lista larga de familias convierta el gráfico en una
        # sección más alta que la ventana.
        height=min(400, max(320, len(pivot.index) * 32 + 100)),
    ))
    _xcats = [str(c) for c in pivot.columns.tolist()]
    fig.update_xaxes(tickmode="array", tickvals=_xcats,
                     ticktext=_wrap_cat(_xcats))

    with _card("heatmap", "Mapa de calor"):
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Tabla pivot Familia × Área"):
        st.dataframe(
            pivot.style
                 .format("S/ {:,.2f}")
                 .background_gradient(
                     cmap="RdYlGn", axis=None,
                     vmin=float(pivot.values.min()),
                     vmax=float(pivot.values.max()),
                 ),
            use_container_width=True,
        )


def _graf_distribucion_ajuste(df, col_familia, col_area, col_ajuste_val, col_producto):
    """Box plot con outliers visibles + histograma con líneas estadísticas."""
    col_izq, col_der = st.columns(2)
    grp = col_familia or col_area

    with col_izq:
        if grp and grp in df.columns:
            fig = px.box(
                df, x=grp, y=col_ajuste_val, color=grp,
                color_discrete_sequence=PALETA_SERIES,
                title=f"Distribución del ajuste por {grp}",
                points="outliers",
                labels={col_ajuste_val: "Ajuste S/", grp: ""},
            )
            fig.add_hline(y=0, line_dash="dash", line_color="#ef4444",
                          annotation_text="Cero", annotation_position="top right")
            fig.update_layout(**_layout_aj(
                showlegend=False,
                xaxis=dict(tickangle=-30, gridcolor=GRIS_BORDE),
                yaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
            ))
            fig.update_traces(hovertemplate="%{x}<br>S/ %{y:,.2f}<extra></extra>")
            _xcats = list(pd.unique(df[grp].astype(str)))
            fig.update_xaxes(tickmode="array", tickvals=_xcats,
                             ticktext=_wrap_cat(_xcats))
        else:
            fig = px.histogram(
                df, x=col_ajuste_val, nbins=30,
                title="Distribución de ajustes valorizados",
                color_discrete_sequence=[SERIE_PRINCIPAL],
            )
            fig.add_vline(x=0, line_dash="dash", line_color="#ef4444",
                          annotation_text="Cero")
            fig.update_layout(**_layout_aj(
                xaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
                yaxis=dict(gridcolor=GRIS_BORDE),
            ))
        with _card("dist_grupo", "Distribución por grupo"):
            st.plotly_chart(fig, use_container_width=True)

    with col_der:
        media   = float(df[col_ajuste_val].mean())
        mediana = float(df[col_ajuste_val].median())

        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=df[col_ajuste_val], nbinsx=30,
            name="Frecuencia",
            marker_color=SERIE_PRINCIPAL, opacity=0.75,
            hovertemplate="Valor: S/ %{x:,.2f}<br>Frecuencia: %{y}<extra></extra>",
        ))
        fig2.add_vline(x=0, line_dash="solid", line_color="#ef4444", line_width=2,
                       annotation_text="Cero", annotation_font_color="#ef4444")
        fig2.add_vline(x=media, line_dash="dot", line_color="#f97316",
                       annotation_text=f"Media S/ {media:,.0f}",
                       annotation_font_color="#f97316",
                       annotation_position="top left")
        fig2.add_vline(x=mediana, line_dash="dash", line_color="#16a34a",
                       annotation_text=f"Mediana S/ {mediana:,.0f}",
                       annotation_font_color="#16a34a")
        fig2.update_layout(**_layout_aj(
            title="Histograma de frecuencias",
            xaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE,
                       title="Ajuste Valorizado"),
            yaxis=dict(title="Frecuencia", gridcolor=GRIS_BORDE),
            hovermode="x",
        ))
        with _card("dist_hist", "Histograma"):
            st.plotly_chart(fig2, use_container_width=True)

    if col_producto and col_producto in df.columns:
        umbral = float(df[col_ajuste_val].quantile(0.05))
        outliers = df[df[col_ajuste_val] <= umbral].copy()
        if not outliers.empty:
            st.markdown(
                f"**⚠️ Productos en el 5% inferior del ajuste "
                f"(< S/ {umbral:,.2f})**"
            )
            cols_tabla = [col_producto, col_ajuste_val]
            for c in (grp,):
                if c and c in outliers.columns and c not in cols_tabla:
                    cols_tabla.append(c)
            out_df = (outliers[cols_tabla]
                      .sort_values(col_ajuste_val)
                      .head(10)
                      .copy())
            out_df[col_ajuste_val] = out_df[col_ajuste_val].map(
                lambda v: f"S/ {v:,.2f}"
            )
            st.dataframe(out_df, hide_index=True, use_container_width=True)


def renderizar_graficos_ajuste(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """
    Gráficos de Ajuste de Inventario — layout con rail derecho (estándar).

    Estructura:
      · Filtros Área y Familia como st.multiselect (dropdowns colapsados),
        FUERA del contenedor grande. Cada uno con su propio label.
      · El segmented «Del periodo / Histórico» y su auto-detección por
        rango viven ahora en `app.py` (fila superior, junto al widget de
        fecha). Esta función solo LEE el ámbito desde:
            st.session_state["ajuste_graf_ambito"]
        Si por algún motivo no está seteado (p. ej. se llama fuera de la
        vista Ajuste), cae a «Del periodo».
      · Contenedor IZQUIERDO (grande): chips de tipo de gráfico arriba
        (Cascada / Mapa de calor / Distribución  ó  Evolución /
        Comparativa mensual) SIN iconos, y el gráfico elegido debajo.
      · Contenedor DERECHO: `_panel_analisis_ajuste` renderiza pestañas
        (st.tabs) con una mini-tabla a la vez.
      · «Del periodo»  → usa df_f (respeta el rango aplicado).
      · «Histórico»    → usa df_full acotado al AÑO ACTUAL.

    Nota: df_full es opcional; si no se pasa, se usa df_f también para
    Histórico (compatibilidad con llamadas antiguas).
    """
    col_fecha      = _resolver(df_f, ["FECHA APERTURA INVENTARIO", "FECHA", "MES"])
    col_familia    = _resolver(df_f, ["FAMILIA", "Nombre Familia", "NOMBRE FAMILIA"])
    col_area       = _resolver(df_f, ["AREA", "Nombre Area", "NOMBRE AREA"])
    col_ajuste_val = _resolver(df_f, ["AJUSTE VALORIZADO", "AJUSTEVALORIZADO"])
    col_valorizado = _resolver(df_f, ["VALORIZADO TOTAL", "VALORIZADO", "VALORIZADOTOTAL"])
    col_producto   = _resolver(df_f, ["NOMBRE PRODUCTO", "PRODUCTO", "DESCRIPCION"])
    col_cantidad   = _resolver(df_f, ["AJUSTE", "CANTIDAD AJUSTE", "CANTIDAD"])

    if not col_ajuste_val:
        st.warning(
            "No se encontró la columna de ajuste valorizado. "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Rail derecho (selector de gráfico + "Tabla") ─────────────────────
    # Reemplaza a las pills Gráficos/Tabla (que app.py ya no dibuja para
    # Ajuste) y a las pills de tipo de gráfico que vivían dentro de la
    # tarjeta. Mismo componente compartido que Compras.
    graf = _render_rail(_AJUSTE_RAIL_CATEGORIAS, "ajuste_graf_tipo",
                        btn_prefix="aj_rail_btn_")

    # "Tabla" = item del rail: se delega en el callback que inyecta app.py
    # (renderiza sus 4 chips propios + la AgGrid). El rail ya quedó dibujado
    # arriba, así que el usuario puede volver a un gráfico. Corta acá para no
    # dibujar los chips/gráficos de la vista Gráficos.
    if graf == "Tabla":
        if tabla_cb is not None:
            tabla_cb()
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    # ── Ámbito: se lee de session_state; app.py es la fuente de verdad ───
    # Todas las visualizaciones respetan el rango de fecha seleccionado.
    # Se eliminó el selector «Del periodo / Histórico».
    ambito = "actual"

    # ── FILTROS FUERA DEL CONTENEDOR: Área y Familia (popover desplegable) ─
    # Cada filtro es un botón compacto (chip) que al hacer clic abre un
    # popover con pills multi-selección adentro. Cuando está cerrado NO
    # ocupa espacio vertical. El label del botón muestra cuántos ítems
    # están seleccionados (o "Área" / "Familia" si no hay filtro activo).
    # DISEÑO UNIFICADO: los chips van en la FRANJA blanca superior
    # (mismo contenedor y CSS fijo que los chips de la vista Tabla,
    # que no se renderizan en Gráficos, así que no hay colisión).
    area_sel, fam_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        col_ff_area, col_ff_fam, _ = st.columns([1, 1, 4])
        with col_ff_area:
            if col_area and col_area in df_f.columns:
                areas = sorted(df_f[col_area].dropna()
                               .astype(str).unique().tolist())
                if areas:
                    _n_area = len(st.session_state.get("ajuste_graf_filtro_area") or [])
                    _lbl_area = f":material/filter_alt: Área :violet-badge[{_n_area}]" if _n_area else ":material/filter_alt: Área"
                    with st.popover(_lbl_area, use_container_width=True):
                        area_sel = st.pills(
                            "Área",
                            areas,
                            selection_mode="multi",
                            key="ajuste_graf_filtro_area",
                            label_visibility="collapsed",
                        ) or []
        with col_ff_fam:
            if col_familia and col_familia in df_f.columns:
                familias = sorted(df_f[col_familia].dropna()
                                  .astype(str).unique().tolist())
                if familias:
                    _n_fam = len(st.session_state.get("ajuste_graf_filtro_familia") or [])
                    _lbl_fam = f":material/category: Familia :violet-badge[{_n_fam}]" if _n_fam else ":material/category: Familia"
                    with st.popover(_lbl_fam, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia",
                            familias,
                            selection_mode="multi",
                            key="ajuste_graf_filtro_familia",
                            label_visibility="collapsed",
                        ) or []


    # ── Datos según ámbito ───────────────────────────────────────────────
    if ambito == "Histórico":
        base = df_full if df_full is not None else df_f
        anio_actual = _dt.date.today().year
        if col_fecha and col_fecha in base.columns:
            _f = pd.to_datetime(base[col_fecha], errors="coerce")
            base = base[_f.dt.year == anio_actual]
        d = base
        st.caption(
            f"📆 Vista histórica del año {anio_actual}. "
            "El rango de fechas del popover no aplica aquí."
        )
    else:
        d = df_f

    # ── Aplicar filtros externos de Área y Familia ───────────────────────
    if area_sel and col_area and col_area in d.columns:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_familia and col_familia in d.columns:
        d = d[d[col_familia].astype(str).isin(fam_sel)]

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # ── LAYOUT APILADO (estándar rail): gráfico principal ARRIBA, panel de
    #    análisis ABAJO. El tipo de gráfico ya lo eligió el rail (`graf`); las
    #    pills de tipo que vivían dentro de la tarjeta se eliminaron. Las keys
    #    siguen empezando con "ajuste_graf_card_" para heredar su CSS.
    _card_izq = st.container(
        border=True, key=f"ajuste_graf_card_izq_{_slug(ambito)}",
    )
    with _card_izq:
        # Render del gráfico elegido en el rail (solo uno por rerun)
        if graf == "Evolución":
            _graf_evolucion_ajuste(d, col_fecha, col_familia,
                                   col_ajuste_val, col_valorizado)
        elif graf == "Comparativa mensual":
            _graf_comparativa_mensual(d, col_fecha, col_ajuste_val)
        elif graf == "Cascada":
            _graf_waterfall_ajuste(d, col_familia, col_area, col_ajuste_val,
                                   col_producto=col_producto,
                                   col_valorizado=col_valorizado,
                                   col_cantidad=col_cantidad)
        elif graf == "Mapa de calor":
            _graf_heatmap_ajuste(d, col_familia, col_area, col_ajuste_val)
        elif graf == "Distribución":
            _graf_distribucion_ajuste(d, col_familia, col_area,
                                      col_ajuste_val, col_producto)

    _card_der = st.container(
        border=True, key=f"ajuste_graf_card_der_{_slug(ambito)}",
    )
    with _card_der:
        _panel_analisis_ajuste(
            d, col_familia, col_area, col_ajuste_val,
            col_producto, col_valorizado, col_cantidad, ambito,
        )
