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
    BLANCO, CELDA_ALERTA_FONDO, CELDA_ALERTA_TEXTO, CELDA_POS_TEXTO,
    DANGER_TEXT, ERROR, ERROR_FONDO, EXITO, EXITO_FONDO,
    GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_FONDO, LAVANDA_SELECCION,
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
    ("Visual", (("Cascada",        "Cascada"),
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
                           col_cantidad=None, df_full=None, col_fecha=None,
                           col_unidad=None):
    """Cascada (Waterfall) por familia/área — SOLO el gráfico.

    Los análisis complementarios (Faltantes, Sobrantes, Extremos, etc.) que
    antes vivían aquí como 8 tabs se movieron a `_panel_analisis_ajuste`,
    que renderiza el contenedor derecho de la vista Gráficos de Ajuste.

    `col_unidad` es la unidad de Kardex por producto (Kg, Und, Lt...) — se
    usa solo en el texto de las barras del drill; si no se resuelve, la
    barra muestra la cantidad sin sufijo (nunca el genérico "und").
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para el gráfico de cascada.")
        return

    # ── Preparar lista de productos para el popover de exclusión ──────────
    # (Se calcula aquí, antes del card, porque _lbl lo necesita para el badge)
    excluidos = set()
    if col_producto and col_producto in df.columns:
        _prod_s = df[col_producto].astype(str)
        _rank = (df.groupby(col_producto, as_index=False)[col_ajuste_val]
                 .sum())
        _rank["_abs"] = _rank[col_ajuste_val].abs()
        _rank = _rank.sort_values("_abs", ascending=False)
        _prods_ranked = _rank[col_producto].astype(str).tolist()
        _todos_prods = sorted(_prod_s.dropna().unique().tolist())

        _n_top = int(st.session_state.get("ajuste_cascada_excl_top") or 0)
        _n_prev = len(set(_prods_ranked[:_n_top]) |
                      set(st.session_state.get("ajuste_cascada_excl_manual")
                          or []))
        _lbl = ":material/filter_alt_off: Excluir productos"
        if _n_prev:
            _lbl += f" :violet-badge[{_n_prev}]"

        # Aplicar exclusiones al df (leyendo el estado ya comprometido)
        if _n_top > 0:
            excluidos.update(_prods_ranked[:_n_top])
        _manual_prev = st.session_state.get("ajuste_cascada_excl_manual") or []
        excluidos.update(str(p) for p in _manual_prev)

        if excluidos:
            df = df[~df[col_producto].astype(str).isin(excluidos)]
    else:
        _todos_prods = []
        _lbl = ":material/filter_alt_off: Excluir productos"

    agg = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
           .sum().sort_values(col_ajuste_val))
    if agg.empty:
        st.info("No queda nada para graficar después de las exclusiones.")
        return
    total = float(agg[col_ajuste_val].sum())

    abs_sum = float(agg[col_ajuste_val].abs().sum()) or 1.0
    pesos = [abs(v) / abs_sum * 100 for v in agg[col_ajuste_val]]

    # ── Enriquecimiento por familia ────────────────────────────────────────
    # Solo el conteo de SKUs: alimenta el "N SKUs" de la fila TOTAL. El
    # producto top y la concentración top3 se sacaron del subtítulo por
    # ruido visual — no se calculan más.
    _n_skus = {}
    if col_producto and col_producto in df.columns:
        for _fam in agg[grp_col].tolist():
            _s = df[df[grp_col].astype(str) == str(_fam)]
            _n_skus[str(_fam)] = int(_s[col_producto].nunique())

    # "S/ val" = ajuste de la familia sobre SU PROPIO valorizado.
    # "% total" = el mismo ajuste sobre el valorizado TOTAL (todas las
    # familias) — son bases distintas a propósito, no van a coincidir.
    _pct_val = {}
    _pct_val_total = {}
    _kpi_pct_total = None
    if col_valorizado and col_valorizado in df.columns:
        _vv = df.groupby(grp_col)[col_valorizado].sum()
        _base_tot = float(df[col_valorizado].sum() or 0)
        for _fam in agg[grp_col].tolist():
            _cv = float(agg[agg[grp_col] == _fam][col_ajuste_val].iloc[0])
            _base = float(_vv.get(_fam, 0) or 0)
            if abs(_base) > 1e-6:
                _pct_val[str(_fam)] = _cv / _base * 100
            if abs(_base_tot) > 1e-6:
                _pct_val_total[str(_fam)] = _cv / _base_tot * 100
        if abs(_base_tot) > 1e-6:
            _kpi_pct_total = total / _base_tot * 100

    _delta = {}
    if (df_full is not None and col_fecha
            and col_fecha in df.columns and col_fecha in df_full.columns):
        _f = pd.to_datetime(df[col_fecha], errors="coerce").dropna()
        if not _f.empty:
            _fmin, _fmax = _f.min(), _f.max()
            _dur = _fmax - _fmin
            _pmax = _fmin - pd.Timedelta(days=1)
            _pmin = _pmax - _dur
            _dp = df_full.copy()
            _dp[col_fecha] = pd.to_datetime(_dp[col_fecha], errors="coerce")
            _dp = _dp[(_dp[col_fecha] >= _pmin) & (_dp[col_fecha] <= _pmax)]
            if not _dp.empty and grp_col in _dp.columns:
                _pa = _dp.groupby(grp_col)[col_ajuste_val].sum().to_dict()
                for _fam in agg[grp_col].tolist():
                    _pv = float(_pa.get(_fam, 0))
                    _cv = float(agg[agg[grp_col] == _fam]
                                [col_ajuste_val].iloc[0])
                    if abs(_pv) > 1e-6:
                        _pctm = (abs(_cv) - abs(_pv)) / abs(_pv) * 100
                        _dir = "down" if _pctm > 0 else "up"
                        _delta[str(_fam)] = (_dir, abs(_pctm))

    def _badge_for(peso, val):
        if val >= 0:
            return ("▲ SOBRANTE", CELDA_POS_TEXTO, EXITO_FONDO)
        if peso >= 40:
            return ("⚠ CRÍTICO", DANGER_TEXT, ERROR_FONDO)
        if peso >= 20:
            return ("● ALERTA", CELDA_ALERTA_TEXTO, CELDA_ALERTA_FONDO)
        if peso >= 5:
            return ("● MENOR", GRIS_TEXTO, GRIS_FONDO)
        return ("✓ OK", GRIS_TEXTO, GRIS_FONDO)

    def _severidad_slug(peso, val):
        """Mismos umbrales que _badge_for, pero como slug para la key del
        `st.container` de la fila — así el CSS le pinta un matiz de fondo
        acorde a la severidad (ver bloque <style> más abajo)."""
        if val >= 0:
            return "sobrante"
        if peso >= 40:
            return "critico"
        if peso >= 20:
            return "alerta"
        if peso >= 5:
            return "menor"
        return "ok"

    # ── Cascada como TABLA de filas (sin fila TOTAL: sus datos viven en
    #    los KPIs junto al título, no en una fila más) ─────────────────────
    _filas = []
    _run = 0.0
    for _i in range(len(agg)):
        _v = float(agg[col_ajuste_val].iloc[_i])
        _filas.append({"cat": str(agg[grp_col].iloc[_i]), "val": _v,
                       "lo": _run, "hi": _run + _v, "peso": float(pesos[_i])})
        _run += _v

    _bordes = [0.0] + [f["lo"] for f in _filas] + [f["hi"] for f in _filas]
    _dmin, _dmax = min(_bordes), max(_bordes)
    _span = (_dmax - _dmin) or 1.0

    for _idx, _f in enumerate(_filas):
        _lo, _hi = min(_f["lo"], _f["hi"]), max(_f["lo"], _f["hi"])
        _f["left_pct"] = (_lo - _dmin) / _span * 100
        _f["w_pct"] = max((_hi - _lo) / _span * 100, 0.4)
        _f["conn_pct"] = (((_filas[_idx - 1]["hi"] - _dmin) / _span * 100)
                          if _idx > 0 else None)

    def _tono(v):
        return ((CELDA_POS_TEXTO, EXITO) if v > 0
                else (DANGER_TEXT, ERROR))

    def _celda_familia(f):
        # Nombre + "X% del total" en la misma línea (no apilado abajo) —
        # el nombre cede espacio primero si no entra.
        _nom = f["cat"]
        if len(_nom) > 30:
            _nom = _nom[:29] + "…"
        _peso_txt = ("&lt;1%" if f["peso"] < 0.5 else f"{f['peso']:.0f}%")
        return (f"<div style='display:flex;align-items:baseline;gap:6px;"
                f"overflow:hidden'>"
                f"<span style='font-weight:500;color:{TEXTO_PRINCIPAL};"
                f"font-size:12.5px;white-space:nowrap;overflow:hidden;"
                f"text-overflow:ellipsis;min-width:0;flex:0 1 auto'>{_nom}</span>"
                f"<span style='font-size:10.5px;color:{GRIS_TEXTO_SUAVE};"
                f"white-space:nowrap;flex-shrink:0'>{_peso_txt} del total</span>"
                f"</div>")

    def _celda_monto(f):
        _col = _tono(f["val"])[0]
        _sig = "+" if f["val"] > 0 else "−"
        _html = (f"<div style='color:{_col};font-weight:600;font-size:13px;"
                 f"font-variant-numeric:tabular-nums;line-height:1.2;"
                 f"letter-spacing:-0.01em'>"
                 f"{_sig}S/ {abs(f['val']):,.0f}</div>")
        _dl = _delta.get(f["cat"])
        if _dl:
            _dir, _dpct = _dl
            _arrow = "▲" if _dir == "down" else "▼"
            _dcol = DANGER_TEXT if _dir == "down" else CELDA_POS_TEXTO
            _html += (f"<div style='font-size:9.5px;color:{_dcol};"
                      f"line-height:1.35;margin-top:2px;"
                      f"font-variant-numeric:tabular-nums'>"
                      f"<span style='font-size:7px;vertical-align:1px'>"
                      f"{_arrow}</span> {_dpct:.0f}% vs ant.</div>")
        return _html

    def _celda_barra(f):
        _bg = _tono(f["val"])[1]
        _conn = ""
        if f["conn_pct"] is not None:
            _conn = (f"<div style='position:absolute;"
                     f"left:{f['conn_pct']:.2f}%;top:3px;bottom:3px;"
                     f"width:1px;background:{GRIS_BORDE}'></div>")
        return (f"<div style='position:relative;height:22px;width:100%'>"
                f"<div style='position:absolute;left:0;right:0;top:50%;"
                f"transform:translateY(-50%);height:9px;"
                f"background:{GRIS_FONDO};border-radius:999px'></div>{_conn}"
                f"<div style='position:absolute;left:{f['left_pct']:.2f}%;"
                f"width:{f['w_pct']:.2f}%;top:50%;"
                f"transform:translateY(-50%);"
                f"height:9px;background:{_bg};border-radius:999px'>"
                f"</div></div>")

    def _celda_pct(valores):
        """Fábrica: misma pinta de celda-%, distinta fuente de datos
        (S/ val = base propia de la familia; % total = base valorizado
        total). Evita duplicar el HTML dos veces."""
        def _fn(f):
            _pv = valores.get(f["cat"])
            if _pv is None:
                return (f"<div style='font-size:11.5px;color:{GRIS_BORDE};"
                        f"text-align:right'>—</div>")
            _col = _tono(_pv)[0]
            return (f"<div style='font-size:11.5px;color:{_col};"
                    f"text-align:right;font-weight:500;"
                    f"font-variant-numeric:tabular-nums'>{_pv:+.1f}%</div>")
        return _fn

    _celda_pctval = _celda_pct(_pct_val)
    _celda_pcttotal = _celda_pct(_pct_val_total)

    def _celda_badge(f):
        _txt, _fg, _bg = _badge_for(f["peso"], f["val"])
        _txt = _txt.split(" ", 1)[-1]
        _txt = _txt if _txt == "OK" else _txt.capitalize()
        return (f"<div style='text-align:right'><span style='display:inline-"
                f"block;padding:2.5px 8px;border-radius:999px;font-size:9.5px;"
                f"font-weight:600;letter-spacing:0.02em;background:{_bg};"
                f"color:{_fg};white-space:nowrap'>{_txt}</span></div>")

    # ── Drill: clic en una familia → top-N de productos abajo ─────────────
    _cats_clic = agg[grp_col].astype(str).tolist()
    _focus_key = "ajuste_cascada_focus"
    focus = st.session_state.get(_focus_key)
    if focus not in _cats_clic:
        focus = None
        st.session_state[_focus_key] = None

    def _hex_rgba(hexcolor, alpha):
        """hex de tema.py -> rgba() con transparencia — para el matiz de
        fondo de las filas no se puede usar el fondo sólido del badge
        (ERROR_FONDO etc.), queda muy fuerte para una fila entera."""
        h = hexcolor.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    _tint_critico = _hex_rgba(ERROR, 0.06)
    _tint_alerta = _hex_rgba(CELDA_ALERTA_TEXTO, 0.07)
    _tint_sobrante = _hex_rgba(EXITO, 0.055)

    st.markdown(f"""<style>
    /* Popover "Excluir productos": achica el boton que la regla global de
       estilos/_30_filtros.py deja en 180px de ancho y 15px de fuente. */
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] button {{
        min-width: 0 !important; padding: 2px 10px !important;
        font-size: 11px !important; font-weight: 400 !important;
        min-height: 0 !important; height: 26px !important;
        line-height: 1 !important;
        border-width: 1px !important; color: {GRIS_TEXTO} !important; }}
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] button div,
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] button span
        {{ line-height: 1 !important; }}
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] button p
        {{ font-size: 11px !important; }}
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] button
        [data-testid="stIconMaterial"]
        {{ font-size: 13px !important; width: 13px !important;
          height: 13px !important; }}
    /* Pills "Top N" del drill (una para Faltantes, otra para Sobrantes —
       keys ajuste_cascada_topn_neg/_pos, por eso el match es por prefijo).
       La version default de st.pills queda grande (hereda el tamano de
       fuente global); se achica solo este par de keys. */
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"] {{
        gap: 4px !important; justify-content: flex-end !important; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"] button[role="radio"] {{
        min-width: 0 !important; padding: 1px 10px !important;
        min-height: 0 !important; height: 24px !important;
        line-height: 1 !important; border-width: 1px !important; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"] button[role="radio"] p {{
        font-size: 11px !important; line-height: 1 !important; margin: 0 !important; }}
    /* ── Filas de la tabla: tarjetas con matiz por severidad, no líneas
       divisorias ─────────────────────────────────────────────────────── */
    div[class*="st-key-ajcas_fila_"] {{
        margin: 0 -6px 4px -6px; padding: 3px 6px;
        border-radius: 8px;
        transition: background .12s ease; }}
    div[class*="st-key-ajcas_fila_"][class*="_critico"] {{
        background: {_tint_critico} !important; }}
    div[class*="st-key-ajcas_fila_"][class*="_alerta"] {{
        background: {_tint_alerta} !important; }}
    div[class*="st-key-ajcas_fila_"][class*="_sobrante"] {{
        background: {_tint_sobrante} !important; }}
    div[class*="st-key-ajcas_fila_"][class*="_menor"],
    div[class*="st-key-ajcas_fila_"][class*="_ok"] {{
        background: {GRIS_FONDO} !important; }}
    div[class*="st-key-ajcas_fila_"]:hover {{
        background: {LAVANDA_SELECCION} !important; }}
    div[class*="st-key-ajcas_fila_"][class*="_on"] {{
        background: {LAVANDA_FONDO} !important;
        box-shadow: inset 2px 0 0 {ACENTO}; }}
    div[class*="st-key-ajcas_fila_"][class*="_on"]:hover {{
        background: {LAVANDA_FONDO} !important; }}
    div[class*="st-key-ajcas_fila_"] div[data-testid="stVerticalBlock"]
        {{ gap: 0 !important; }}
    div[class*="st-key-ajcas_fila_"] div[data-testid="stHorizontalBlock"]
        {{ gap: 0.4rem !important; min-height: 40px; }}
    div[class*="st-key-ajcas_fila_"] p {{ margin: 0 !important; }}
    div[class*="st-key-ajcas_fila_"] [data-testid="stMarkdownContainer"]
        {{ display: flex; flex-direction: column; justify-content: center;
          min-height: 36px; }}
    /* ── Chevron del gutter ────────────────────────────────────────── */
    div[class*="st-key-ajcas_btn_"] button {{
        border: none !important; background: transparent !important;
        color: {GRIS_TEXTO_SUAVE} !important; padding: 0 !important;
        min-height: 34px !important; font-size: 18px !important;
        transition: color .12s ease, transform .12s ease !important; }}
    div[class*="st-key-ajcas_btn_"] button:hover {{
        color: {ACENTO} !important; background: transparent !important;
        transform: scale(1.25); }}
    div[class*="st-key-ajcas_btn_"] button[kind="primary"] {{
        color: {ACENTO} !important; }}
    </style>""", unsafe_allow_html=True)

    with _card("cascada"):
        # ── Título + totales (antes vivían en la fila TOTAL de la tabla)
        #    como texto simple en la misma línea — sin cajas, para no
        #    competir en peso visual con el título. Popover de exclusión
        #    a la derecha. ──────────────────────────────────────────────
        def _kpi_sep(txt="|"):
            return f"<span style='color:{GRIS_BORDE};padding:0 2px'>{txt}</span>"

        _kpis = (f"<span style='font-size:13px;font-weight:500;"
                 f"color:{GRIS_TEXTO_MEDIO};white-space:nowrap'>"
                 f"Ajuste valorizado por {grp_col.lower()}</span>")
        _kpis += _kpi_sep()
        _kpis += (f"<span style='color:{GRIS_TEXTO_SUAVE}'>"
                  f"{len(agg)} {grp_col.lower()}s</span>")
        if _n_skus:
            _kpis += _kpi_sep("·")
            _kpis += (f"<span style='color:{GRIS_TEXTO_SUAVE}'>"
                      f"{sum(_n_skus.values()):,} SKUs</span>")
        _sig_tot = "+" if total > 0 else "−"
        _col_tot = _tono(total)[0]
        _kpis += _kpi_sep()
        _kpis += (f"<span style='color:{GRIS_TEXTO_SUAVE}'>neto</span> "
                  f"<span style='color:{_col_tot};font-weight:600;"
                  f"font-variant-numeric:tabular-nums'>"
                  f"{_sig_tot}S/ {abs(total):,.0f}</span>")
        if _kpi_pct_total is not None:
            _col_pct = _tono(_kpi_pct_total)[0]
            _kpis += _kpi_sep("·")
            _kpis += (f"<span style='color:{_col_pct};font-weight:600;"
                      f"font-variant-numeric:tabular-nums'>"
                      f"{_kpi_pct_total:+.1f}%</span>"
                      f"<span style='color:{GRIS_TEXTO_SUAVE}'> s/ total</span>")

        _col_titulo, _col_excl = st.columns([6, 1])
        with _col_titulo:
            st.markdown(
                f"<div style='display:flex;align-items:baseline;"
                f"flex-wrap:wrap;gap:8px;padding:2px 0 10px 0;"
                f"font-size:11.5px'>{_kpis}</div>",
                unsafe_allow_html=True)
        with _col_excl:
            if col_producto and col_producto in df.columns:
                with st.container(key="ajcas_excl_wrap"), \
                        st.popover(_lbl, use_container_width=False):
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

        # Cabecera de la tabla
        st.markdown(
            f"<div style='display:flex;font-size:9px;color:{GRIS_TEXTO_SUAVE};"
            f"text-transform:uppercase;letter-spacing:.08em;font-weight:600;"
            f"padding:0 0 7px 0;border-bottom:1px solid {GRIS_BORDE}'>"
            f"<div style='width:4%'></div>"
            f"<div style='width:26%'>Familia</div>"
            f"<div style='width:13%'>Ajuste</div>"
            f"<div style='width:22%'>Cascada acumulada</div>"
            f"<div style='width:11%;text-align:right'>s/ val</div>"
            f"<div style='width:11%;text-align:right'>% total</div>"
            f"<div style='width:13%;text-align:right'>Estado</div>"
            f"</div>", unsafe_allow_html=True)

        def _render_drill(focus_cat):
            """Panel de drill: se llama inline, justo debajo de la fila
            de la familia clickeada (no al final de la tabla)."""
            col_d = st.container(border=True, key="ajcas_panel_drill")
            _det = df[df[grp_col].astype(str) == focus_cat]
            dim = col_producto or (col_area if grp_col == col_familia
                                   else col_familia)

            # Sin título/subtítulo/botón "cerrar": el panel vive pegado a la
            # fila con foco, que ya muestra familia + monto. Cerrar es el
            # mismo chevron (▾) que lo abrió.
            with col_d:
                if not dim or dim not in _det.columns:
                    st.info("No hay una columna adecuada para desglosar "
                            "esta familia.")
                else:
                    _has_cant = bool(col_cantidad
                                     and col_cantidad in _det.columns)
                    _has_area = bool(col_area and col_area in _det.columns
                                     and col_area != dim
                                     and col_area != grp_col)
                    _has_um = bool(col_unidad and col_unidad in _det.columns
                                   and col_unidad != dim)
                    _agg_map = {col_ajuste_val: "sum"}
                    if _has_cant:
                        _agg_map[col_cantidad] = "sum"
                    if _has_um:
                        _agg_map[col_unidad] = "first"
                    _agg_dim = _det.groupby(dim, as_index=False).agg(_agg_map)
                    if _has_area:
                        # "first" mostraba el área de la primera fila del
                        # producto, sin importar si ahí el ajuste era 0 —
                        # con varias áreas por producto (Almacén Central,
                        # Producción, Pruebas...) etiquetaba con la que no
                        # tenía nada de movimiento. Se toma el área de la
                        # fila con mayor |ajuste| para ese producto, que es
                        # la que realmente explica el monto mostrado.
                        _area_top = (
                            _det[[dim, col_area, col_ajuste_val]]
                            .assign(_abs=lambda x: x[col_ajuste_val].abs())
                            .sort_values("_abs", ascending=False)
                            .drop_duplicates(subset=[dim])[[dim, col_area]]
                        )
                        _agg_dim = _agg_dim.merge(_area_top, on=dim, how="left")

                    if (_agg_dim.empty
                            or _agg_dim[col_ajuste_val].abs().sum() == 0):
                        st.info("Sin datos para el drill de esta familia.")
                    else:
                        def _filas_split_html(_df, color_bar):
                            """Mini barras de progreso (riel + relleno), no
                            un gráfico Plotly — mismo patrón que la columna
                            Cascada acumulada de la tabla principal. El
                            relleno normaliza contra el mayor |ajuste| de
                            ESTE sub-listado (no del total de la familia)."""
                            _max_abs = float(
                                _df[col_ajuste_val].abs().max()) or 1.0
                            _filas_html = []
                            for _, _r in _df.iterrows():
                                _nom = str(_r[dim])
                                if len(_nom) > 32:
                                    _nom = _nom[:31] + "…"
                                _sub = (
                                    f"<div style='font-size:8.5px;"
                                    f"color:{GRIS_TEXTO_SUAVE};white-space:"
                                    f"nowrap;overflow:hidden;text-overflow:"
                                    f"ellipsis'>{_r[col_area]}</div>"
                                    if _has_area else "")
                                _pct = max(
                                    abs(float(_r[col_ajuste_val]))
                                    / _max_abs * 100, 3)
                                _t = f"S/ {_r[col_ajuste_val]:,.0f}"
                                if _has_cant:
                                    _t += f" · {int(_r[col_cantidad]):,}"
                                    _um = (str(_r[col_unidad]).strip()
                                           if _has_um else "")
                                    if _um and _um.lower() != "nan":
                                        _t += f" {_um}"
                                _tcol = _tono(float(_r[col_ajuste_val]))[0]
                                _filas_html.append(
                                    f"<div style='display:flex;"
                                    f"align-items:center;gap:8px;"
                                    f"padding:3px 0'>"
                                    f"<div style='width:38%;min-width:0;"
                                    f"flex-shrink:0;overflow:hidden'>"
                                    f"<div style='font-size:10.5px;"
                                    f"color:{TEXTO_PRINCIPAL};white-space:"
                                    f"nowrap;overflow:hidden;text-overflow:"
                                    f"ellipsis'>{_nom}</div>{_sub}</div>"
                                    f"<div style='flex:1;position:relative;"
                                    f"height:16px;min-width:0'>"
                                    f"<div style='position:absolute;left:0;"
                                    f"right:0;top:50%;transform:"
                                    f"translateY(-50%);height:7px;"
                                    f"background:{GRIS_FONDO};"
                                    f"border-radius:999px'></div>"
                                    f"<div style='position:absolute;left:0;"
                                    f"width:{_pct:.1f}%;top:50%;transform:"
                                    f"translateY(-50%);height:7px;"
                                    f"background:{color_bar};"
                                    f"border-radius:999px'></div></div>"
                                    f"<div style='flex-shrink:0;"
                                    f"text-align:right;font-size:10px;"
                                    f"font-weight:600;color:{_tcol};"
                                    f"font-variant-numeric:tabular-nums;"
                                    f"white-space:nowrap'>{_t}</div>"
                                    f"</div>")
                            return "".join(_filas_html)

                        def _header_split(txt, color, key):
                            """Título de la columna + su propio Top N, en la
                            misma fila — Faltantes y Sobrantes ya no
                            comparten un único selector."""
                            _hl, _hr = st.columns(
                                [1, 1], vertical_alignment="center")
                            with _hl:
                                st.markdown(
                                    f"<div style='font-size:9px;font-weight:600;"
                                    f"color:{color};letter-spacing:.08em;"
                                    f"text-transform:uppercase'>{txt}</div>",
                                    unsafe_allow_html=True,
                                )
                            with _hr:
                                return st.pills(
                                    "Top", [5, 10, 20], default=10, key=key,
                                    label_visibility="collapsed",
                                    format_func=lambda n: f"Top {n}",
                                ) or 10

                        _pa, _pb = st.columns(2)
                        with _pa:
                            _topn_neg = _header_split(
                                "Faltantes", DANGER_TEXT,
                                "ajuste_cascada_topn_neg")
                            # ascending=True: el más negativo (mayor
                            # magnitud) primero en el DataFrame -> primero
                            # en el HTML -> arriba de la lista.
                            _neg = (_agg_dim[_agg_dim[col_ajuste_val] < 0]
                                    .nsmallest(int(_topn_neg), col_ajuste_val)
                                    .sort_values(col_ajuste_val, ascending=True))
                            if _neg.empty:
                                st.caption("Sin faltantes en esta familia.")
                            else:
                                st.markdown(_filas_split_html(_neg, ERROR),
                                           unsafe_allow_html=True)
                        with _pb:
                            _topn_pos = _header_split(
                                "Sobrantes", CELDA_POS_TEXTO,
                                "ajuste_cascada_topn_pos")
                            _pos = (_agg_dim[_agg_dim[col_ajuste_val] > 0]
                                    .nlargest(int(_topn_pos), col_ajuste_val)
                                    .sort_values(col_ajuste_val, ascending=False))
                            if _pos.empty:
                                st.caption("Sin sobrantes en esta familia.")
                            else:
                                st.markdown(_filas_split_html(_pos, EXITO),
                                           unsafe_allow_html=True)

        # Una fila por familia. El drill de la familia clickeada se
        # inserta justo debajo de su fila (no al final de la tabla).
        for _f in _filas:
            _es_foco = _f["cat"] == focus
            _sev = _severidad_slug(_f["peso"], _f["val"])
            with st.container(
                    key=f"ajcas_fila_{_slug(_f['cat'])}_{_sev}"
                        + ("_on" if _es_foco else "")):
                _c = st.columns([0.04, 0.26, 0.13, 0.22, 0.11, 0.11, 0.13])
                with _c[0]:
                    if st.button(
                        "▾" if _es_foco else "▸",
                        key=f"ajcas_btn_{_slug(_f['cat'])}",
                        help=("Cerrar el detalle" if _es_foco
                              else f"Ver productos de {_f['cat']}"),
                        type="primary" if _es_foco else "secondary",
                    ):
                        st.session_state[_focus_key] = (
                            None if _es_foco else _f["cat"])
                        st.rerun()
                for _col, _fn in zip(_c[1:], (_celda_familia, _celda_monto,
                                              _celda_barra, _celda_pctval,
                                              _celda_pcttotal, _celda_badge)):
                    with _col:
                        st.markdown(_fn(_f), unsafe_allow_html=True)

            if _es_foco:
                _render_drill(_f["cat"])

        # Leyenda
        def _punto(color, txt):
            return (f"<span style='display:inline-flex;align-items:center;"
                    f"gap:5px'><span style='display:inline-block;width:8px;"
                    f"height:8px;border-radius:999px;background:{color}'>"
                    f"</span>{txt}</span>")
        st.markdown(
            f"<div style='display:flex;gap:16px;flex-wrap:wrap;"
            f"font-size:9.5px;color:{GRIS_TEXTO_SUAVE};margin-top:10px'>"
            + _punto(ERROR, "Faltante") + _punto(EXITO, "Sobrante")
            + f"<span style='color:{GRIS_BORDE}'>|</span>"
              f"<span>Cada barra arranca donde terminó la anterior</span>"
              f"</div>", unsafe_allow_html=True)


def _panel_analisis_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto, col_valorizado, col_cantidad,
                           ambito):
    """Panel derecho: UNA mini-tabla analítica a la vez, en pestañas."""
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

    with tabs[0]:
        st.caption("Top 5 faltantes")
        neg = agg.nsmallest(5, col_ajuste_val)[[grp_col, col_ajuste_val]]
        st.dataframe(_fmt_soles(neg, col_ajuste_val),
                     hide_index=True, use_container_width=True)

    with tabs[1]:
        st.caption("Top 5 sobrantes")
        pos = agg.nlargest(5, col_ajuste_val)[[grp_col, col_ajuste_val]]
        st.dataframe(_fmt_soles(pos, col_ajuste_val),
                     hide_index=True, use_container_width=True)

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

    with tabs[5]:
        neg5 = agg.nsmallest(5, col_ajuste_val)
        pos5 = agg.nlargest(5, col_ajuste_val)[::-1]
        sep = pd.DataFrame({grp_col: ["———"], col_ajuste_val: [0.0]})
        extremos = pd.concat([neg5, sep, pos5], ignore_index=True)
        extremos[col_ajuste_val] = extremos[col_ajuste_val].map(
            lambda v: "" if v == 0 else f"S/ {v:,.2f}"
        )
        st.dataframe(extremos[[grp_col, col_ajuste_val]],
                     hide_index=True, use_container_width=True)

    with tabs[6]:
        if col_valorizado and col_valorizado in df.columns:
            val_agg = (df.groupby(grp_col, as_index=False)[col_valorizado]
                         .sum()
                         .sort_values(col_valorizado, ascending=False))
            st.dataframe(_fmt_soles(val_agg, col_valorizado),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No hay columna de valorizado en el reporte.")

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


def _graf_heatmap_ajuste(df, col_familia, col_area, col_ajuste_val,
                         col_producto=None):
    """Mapa de calor familia × área con escala divergente centrada en cero."""
    if not col_familia or not col_area:
        st.info("Se necesitan columnas de familia y área para el mapa de calor.")
        return

    pivot = df.pivot_table(
        index=col_familia, columns=col_area,
        values=col_ajuste_val, aggfunc="sum", fill_value=0,
    )
    _vmax = float(abs(pivot.values).max()) or 1.0

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        xgap=3, ygap=3,
        colorscale=[
            [0.00, ERROR],
            [0.35, ERROR_FONDO],
            [0.50, BLANCO],
            [0.65, EXITO_FONDO],
            [1.00, EXITO],
        ],
        zmin=-_vmax, zmax=_vmax, zmid=0,
        colorbar=dict(
            title=dict(text="Ajuste S/", font=dict(size=10,
                                                   color=GRIS_TEXTO)),
            tickformat=",.0f", tickfont=dict(size=9, color=GRIS_TEXTO_SUAVE),
            thickness=8, len=0.75, outlinewidth=0,
            ticks="outside", ticklen=3, tickcolor=GRIS_BORDE,
        ),
        hoverinfo="skip",
    ))

    _pts_x, _pts_y, _pts_cd = [], [], []
    for _i, _fam in enumerate(pivot.index.tolist()):
        for _j, _area in enumerate(pivot.columns.tolist()):
            _pts_x.append(_area)
            _pts_y.append(_fam)
            _pts_cd.append([float(pivot.values[_i][_j])])

    fig.add_trace(go.Scatter(
        x=_pts_x, y=_pts_y, mode="markers",
        marker=dict(size=28, opacity=0, color=ACENTO),
        customdata=_pts_cd,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Área: <b>%{x}</b><br>"
            "Ajuste: <b>S/ %{customdata[0]:,.2f}</b><extra></extra>"
        ),
        showlegend=False,
    ))

    _anns_hm = []
    for _i, _fam in enumerate(pivot.index.tolist()):
        for _j, _area in enumerate(pivot.columns.tolist()):
            _v = float(pivot.values[_i][_j])
            if abs(_v) < 0.5:
                continue
            _int = abs(_v) / _vmax
            _fg = BLANCO if _int > 0.55 else GRIS_TEXTO_MEDIO
            _anns_hm.append(dict(
                x=_area, y=_fam, xref="x", yref="y",
                text=f"S/ {_v:,.0f}", showarrow=False,
                font=dict(size=9.5, color=_fg,
                          family="ui-monospace, monospace"),
            ))

    fig.update_layout(**_layout_aj(
        title_text="",
        xaxis=dict(tickangle=0, side="top", gridcolor=GRIS_BORDE,
                   showgrid=False, ticks="",
                   tickfont=dict(size=10, color=GRIS_TEXTO)),
        yaxis=dict(autorange="reversed", gridcolor=GRIS_BORDE,
                   showgrid=False, ticks="", showticklabels=True,
                   tickfont=dict(size=10, color=GRIS_TEXTO_MEDIO)),
        height=min(560, max(240, len(pivot.index) * 38 + 110)),
        margin=dict(l=10, r=10, t=50, b=20),
        annotations=_anns_hm,
        hovermode="closest",
    ))
    fig.update_layout(plot_bgcolor=GRIS_BORDE)
    _xcats = [str(c) for c in pivot.columns.tolist()]
    fig.update_xaxes(tickmode="array", tickvals=_xcats,
                     ticktext=_wrap_cat(_xcats))

    _peor_v = float(pivot.values.min())
    _sub_hm = ""
    if _peor_v < 0:
        _pos = pivot.values.argmin()
        _pf = pivot.index[_pos // len(pivot.columns)]
        _pa = pivot.columns[_pos % len(pivot.columns)]
        _sub_hm = (f"<span style='font-size:11px;color:{GRIS_TEXTO_SUAVE}'>"
                   f"Mayor faltante: <b style='color:{DANGER_TEXT}'>{_pf}</b>"
                   f" en <b style='color:{DANGER_TEXT}'>{_pa}</b> · "
                   f"S/ {_peor_v:,.0f}</span>")

    with _card("heatmap"):
        if _sub_hm:
            st.markdown(f"<div style='margin:-4px 0 6px 0'>{_sub_hm}</div>",
                        unsafe_allow_html=True)
        _hm_evt = st.plotly_chart(
            fig, use_container_width=True,
            key="heatmap_ajuste",
            on_select="rerun", selection_mode="points",
        )

    _hm_punto = None
    try:
        _sel = getattr(_hm_evt, "selection", None) or (
            _hm_evt.get("selection") if isinstance(_hm_evt, dict) else None)
        _pts = (_sel or {}).get("points", [])
        _hm_punto = _pts[0] if _pts else None
    except Exception:
        _hm_punto = None

    if _hm_punto is not None:
        _fam_sel = _hm_punto.get("y")
        _area_sel = _hm_punto.get("x")
        _val_sel = 0.0
        try:
            _val_sel = float(pivot.loc[_fam_sel, _area_sel])
        except Exception:
            _cd_evt = _hm_punto.get("customdata")
            if isinstance(_cd_evt, (list, tuple)) and _cd_evt:
                _val_sel = float(_cd_evt[0])

        if _fam_sel and _area_sel:
            _det = df[
                (df[col_familia].astype(str) == str(_fam_sel)) &
                (df[col_area].astype(str) == str(_area_sel))
            ]

            _color_total = (DANGER_TEXT if (_val_sel or 0) < 0
                            else CELDA_POS_TEXTO)
            st.markdown(
                f"**{_fam_sel}** × **{_area_sel}** · "
                f"<span style='color:{_color_total};font-weight:600'>"
                f"S/ {(_val_sel or 0):,.0f}</span> · "
                f"{len(_det)} registros",
                unsafe_allow_html=True,
            )

            if col_producto and col_producto in _det.columns:
                _topn = st.pills(
                    "Top", [5, 10, 20], default=10,
                    key="hm_drill_topn",
                    label_visibility="collapsed",
                    format_func=lambda n: f"Top {n}",
                ) or 10

                _sub_prod = (
                    _det.groupby(col_producto, as_index=False)[col_ajuste_val]
                    .sum()
                )
                _sub_prod["_abs"] = _sub_prod[col_ajuste_val].abs()
                _sub_prod = _sub_prod.sort_values(
                    "_abs", ascending=False).head(int(_topn))

                # ascending: True para negativos (el mas negativo primero
                # -> arriba en el HTML), False para positivos (el mayor
                # primero) -- el HTML renderiza top-a-bottom en el orden
                # del DataFrame, al reves de como Plotly ubicaba las
                # categorias en un bar horizontal.
                _neg = _sub_prod[_sub_prod[col_ajuste_val] < 0].sort_values(
                    col_ajuste_val, ascending=True)
                _pos = _sub_prod[_sub_prod[col_ajuste_val] > 0].sort_values(
                    col_ajuste_val, ascending=False)

                def _filas_drill_html(_df_d, _color_bar):
                    """Mini barras de progreso (riel + relleno) — mismo
                    patron que la columna Cascada acumulada, en vez de un
                    grafico Plotly de barras gruesas."""
                    if _df_d.empty:
                        return ""
                    _max_abs = float(
                        _df_d[col_ajuste_val].abs().max()) or 1.0
                    _filas_html = []
                    for _, _r in _df_d.iterrows():
                        _nom = str(_r[col_producto])
                        if len(_nom) > 32:
                            _nom = _nom[:31] + "…"
                        _pct = max(
                            abs(float(_r[col_ajuste_val])) / _max_abs * 100,
                            3)
                        _tcol = (DANGER_TEXT if _r[col_ajuste_val] < 0
                                 else CELDA_POS_TEXTO)
                        _filas_html.append(
                            f"<div style='display:flex;align-items:center;"
                            f"gap:8px;padding:3px 0'>"
                            f"<div style='width:38%;min-width:0;"
                            f"flex-shrink:0;overflow:hidden'>"
                            f"<div style='font-size:10.5px;"
                            f"color:{TEXTO_PRINCIPAL};white-space:nowrap;"
                            f"overflow:hidden;text-overflow:ellipsis'>"
                            f"{_nom}</div></div>"
                            f"<div style='flex:1;position:relative;"
                            f"height:16px;min-width:0'>"
                            f"<div style='position:absolute;left:0;"
                            f"right:0;top:50%;transform:translateY(-50%);"
                            f"height:7px;background:{GRIS_FONDO};"
                            f"border-radius:999px'></div>"
                            f"<div style='position:absolute;left:0;"
                            f"width:{_pct:.1f}%;top:50%;transform:"
                            f"translateY(-50%);height:7px;"
                            f"background:{_color_bar};"
                            f"border-radius:999px'></div></div>"
                            f"<div style='flex-shrink:0;text-align:right;"
                            f"font-size:10px;font-weight:600;"
                            f"color:{_tcol};font-variant-numeric:"
                            f"tabular-nums;white-space:nowrap'>"
                            f"S/ {_r[col_ajuste_val]:,.0f}</div></div>")
                    return "".join(_filas_html)

                _pa, _pb = st.columns(2)
                with _pa:
                    st.markdown(
                        f"<div style='font-size:9px;font-weight:600;"
                        f"color:{DANGER_TEXT};letter-spacing:.08em;"
                        f"text-transform:uppercase;margin:4px 0 -8px 0'>"
                        f"Faltantes</div>",
                        unsafe_allow_html=True,
                    )
                    if _neg.empty:
                        st.caption("Sin faltantes.")
                    else:
                        st.markdown(_filas_drill_html(_neg, ERROR),
                                   unsafe_allow_html=True)
                with _pb:
                    st.markdown(
                        f"<div style='font-size:9px;font-weight:600;"
                        f"color:{CELDA_POS_TEXTO};letter-spacing:.08em;"
                        f"text-transform:uppercase;margin:4px 0 -8px 0'>"
                        f"Sobrantes</div>",
                        unsafe_allow_html=True,
                    )
                    if _pos.empty:
                        st.caption("Sin sobrantes.")
                    else:
                        st.markdown(_filas_drill_html(_pos, EXITO),
                                   unsafe_allow_html=True)
            else:
                st.caption("No hay columna de producto para desglosar.")


def _graf_distribucion_ajuste(df, col_familia, col_area, col_ajuste_val, col_producto):
    """Strip plot coloreado (faltante/sobrante) + histograma, ambos excluyendo
    los ajustes en cero.

    Con >50% de productos en S/ 0 (lo normal en un inventario), un boxplot
    colapsa q1=mediana=q3 en una línea invisible y solo deja ver puntos
    sueltos sin caja, y un histograma amontona todo en un pico que tapa las
    líneas de media/mediana/cero. Filtrar el cero antes de graficar es lo
    que deja ver la distribución real; el conteo de productos sin ajuste se
    muestra aparte como texto, no se pierde."""
    col_izq, col_der = st.columns(2)
    grp = col_familia or col_area

    n_total = len(df)
    df_nz = df[df[col_ajuste_val] != 0]
    n_nz = len(df_nz)

    if df_nz.empty:
        st.info("Ningún producto tuvo ajuste distinto de cero en este rango.")
        return

    with col_izq:
        st.caption(f"{n_nz} de {n_total} productos con diferencia")
        if grp and grp in df_nz.columns:
            d = df_nz.copy()
            d["_signo"] = d[col_ajuste_val].lt(0).map(
                {True: "Faltante", False: "Sobrante"})
            fig = px.strip(
                d, x=grp, y=col_ajuste_val, color="_signo",
                color_discrete_map={"Faltante": ERROR, "Sobrante": EXITO},
                title=f"Distribución del ajuste por {grp}",
                labels={col_ajuste_val: "Ajuste S/", grp: "", "_signo": ""},
            )
            fig.add_hline(y=0, line_dash="dot", line_color=GRIS_TEXTO_SUAVE,
                          annotation_text="Cero", annotation_position="top right")
            fig.update_layout(**_layout_aj(
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1, title=None),
                xaxis=dict(tickangle=-30, gridcolor=GRIS_BORDE),
                yaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
            ))
            fig.update_traces(marker=dict(size=7),
                              hovertemplate="%{x}<br>S/ %{y:,.2f}<extra></extra>")
            _xcats = list(pd.unique(d[grp].astype(str)))
            fig.update_xaxes(tickmode="array", tickvals=_xcats,
                             ticktext=_wrap_cat(_xcats))
        else:
            fig = px.histogram(
                df_nz, x=col_ajuste_val, nbins=30,
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
        st.caption(f"{n_total - n_nz} productos en cero, excluidos del cálculo")
        media   = float(df_nz[col_ajuste_val].mean())
        mediana = float(df_nz[col_ajuste_val].median())

        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=df_nz[col_ajuste_val], nbinsx=30,
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
    """
    col_fecha      = _resolver(df_f, ["FECHA APERTURA INVENTARIO", "FECHA", "MES"])
    col_familia    = _resolver(df_f, ["FAMILIA", "Nombre Familia", "NOMBRE FAMILIA"])
    col_area       = _resolver(df_f, ["AREA", "Nombre Area", "NOMBRE AREA"])
    col_ajuste_val = _resolver(df_f, ["AJUSTE VALORIZADO", "AJUSTEVALORIZADO"])
    col_valorizado = _resolver(df_f, ["VALORIZADO TOTAL", "VALORIZADO", "VALORIZADOTOTAL"])
    col_producto   = _resolver(df_f, ["NOMBRE PRODUCTO", "PRODUCTO", "DESCRIPCION"])
    col_cantidad   = _resolver(df_f, ["AJUSTE", "CANTIDAD AJUSTE", "CANTIDAD"])
    # Misma lista de candidatos que graficos/compras/__init__.py::col_um —
    # la unidad real de Kardex (Kg, Und, Lt...), no un sufijo inventado.
    col_unidad     = _resolver(df_f, ["Unidad de Ingreso", "Unidad_de_ingreso",
                                      "Unidad Ingreso", "Unidad Kardex", "Unidad_medida",
                                      "Unidad medida", "Unidad de medida", "Unidad_compra",
                                      "Unidad compra", "Unidad", "UM", "Und"])

    if not col_ajuste_val:
        st.warning(
            "No se encontró la columna de ajuste valorizado. "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    graf = _render_rail(_AJUSTE_RAIL_CATEGORIAS, "ajuste_graf_tipo",
                        btn_prefix="aj_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            tabla_cb()
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    ambito = "actual"

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

    if area_sel and col_area and col_area in d.columns:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_familia and col_familia in d.columns:
        d = d[d[col_familia].astype(str).isin(fam_sel)]

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _card_izq = st.container(
        border=True, key=f"ajuste_graf_card_izq_{_slug(ambito)}",
    )
    with _card_izq:
        if graf == "Evolución":
            _graf_evolucion_ajuste(d, col_fecha, col_familia,
                                   col_ajuste_val, col_valorizado)
        elif graf == "Comparativa mensual":
            _graf_comparativa_mensual(d, col_fecha, col_ajuste_val)
        elif graf == "Cascada":
            _graf_waterfall_ajuste(d, col_familia, col_area, col_ajuste_val,
                                   col_producto=col_producto,
                                   col_valorizado=col_valorizado,
                                   col_cantidad=col_cantidad,
                                   df_full=df_full, col_fecha=col_fecha,
                                   col_unidad=col_unidad)
        elif graf == "Mapa de calor":
            _graf_heatmap_ajuste(d, col_familia, col_area, col_ajuste_val,
                                 col_producto=col_producto)
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
