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
    GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
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
                           col_cantidad=None, df_full=None, col_fecha=None):
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
        _n_prev = len(set(_prods_ranked[:_n_top]) |
                      set(st.session_state.get("ajuste_cascada_excl_manual")
                          or []))
        _lbl = ":material/filter_alt_off: Excluir productos"
        if _n_prev:
            _lbl += f" :violet-badge[{_n_prev}]"

        # use_container_width=False: el popover toma solo su ancho natural
        # y no deja un rectangulo vacio al costado (antes vivia en un
        # st.columns([1,3]) y el otro 75% quedaba en blanco).
        #
        # El wrapper con key existe SOLO para poder acotar el CSS: hay una
        # regla global sin acotar en estilos/_30_filtros.py
        # (`[data-testid="stPopover"] button`) que le impone 180px de ancho
        # minimo y 14px/26px de padding a TODOS los popovers. Este control
        # es secundario (corrige errores de captura, no se usa en cada
        # analisis), asi que se lo achica aca en vez de tocar el global.
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

    # Insight automático: si un item concentra mucho, decirlo en el subtítulo.
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

    # ── Enriquecimientos por familia (para las celdas de la tabla) ─────
    # n_skus, top producto (nombre + monto + % que aporta a la familia),
    # y delta vs periodo anterior (mismo tamaño de ventana, inmediatamente
    # antes). El delta requiere df_full + col_fecha; si no vienen, se omite.
    _n_skus = {}
    _top_prod = {}  # fam -> (nombre_truncado, valor, pct_familia)
    _conc3 = {}     # fam -> % que concentran los 3 productos mayores
    if col_producto and col_producto in df.columns:
        for _fam in agg[grp_col].tolist():
            _s = df[df[grp_col].astype(str) == str(_fam)]
            _n_skus[str(_fam)] = int(_s[col_producto].nunique())
            _tp = (_s.groupby(col_producto, as_index=False)[col_ajuste_val]
                   .sum())
            _tp["_abs"] = _tp[col_ajuste_val].abs()
            _tp = _tp.sort_values("_abs", ascending=False)
            _abs_fam = float(_tp["_abs"].sum())
            if _abs_fam > 1e-9 and len(_tp) > 3:
                _conc3[str(_fam)] = (float(_tp["_abs"].head(3).sum())
                                     / _abs_fam * 100)
            if not _tp.empty:
                _nom = str(_tp[col_producto].iloc[0])
                if len(_nom) > 24:
                    _nom = _nom[:23] + "…"
                _val = float(_tp[col_ajuste_val].iloc[0])
                _pctf = (float(_tp["_abs"].iloc[0]) / _abs_fam * 100
                         if _abs_fam > 1e-9 else 0.0)
                _top_prod[str(_fam)] = (_nom, _val, _pctf)

    # % del ajuste sobre el valorizado de la propia familia — responde
    # "¿es grave PARA ESTA familia?", que el % del total no contesta.
    _pct_val = {}
    if col_valorizado and col_valorizado in df.columns:
        _vv = df.groupby(grp_col)[col_valorizado].sum()
        for _fam in agg[grp_col].tolist():
            _base = float(_vv.get(_fam, 0) or 0)
            if abs(_base) > 1e-6:
                _cv = float(agg[agg[grp_col] == _fam][col_ajuste_val].iloc[0])
                _pct_val[str(_fam)] = _cv / _base * 100
        # La fila TOTAL usa el valorizado de TODO el df, no la suma de los
        # % por familia (que no es un promedio válido: cada uno tiene base
        # distinta).
        _base_tot = float(df[col_valorizado].sum() or 0)
        if abs(_base_tot) > 1e-6:
            _pct_val["TOTAL"] = total / _base_tot * 100

    _delta = {}  # fam -> ("up"/"down", pct_magnitud)
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

    # Semáforo por familia — umbrales sobre |peso| (% de |total ajuste|)
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

    # ── Cascada como TABLA de filas ────────────────────────────────────
    # Una cascada horizontal ES una tabla con barras flotantes: cada barra
    # arranca donde terminó la de arriba. Renderizarla como tabla (en vez de
    # como go.Waterfall) resuelve de raíz el solapamiento de etiquetas que
    # tenía la versión vertical: cada dato vive en su propia celda, no
    # compite por el mismo tramo de eje.
    #
    # Geometría acumulada: para cada familia el par (lo, hi) marca dónde
    # empieza y termina su barra en el eje de valores. `_dmin/_dmax` fijan
    # el dominio para poder expresar todo en % (responsive, sin píxeles).
    _filas = []
    _run = 0.0
    for _i in range(len(agg)):
        _v = float(agg[col_ajuste_val].iloc[_i])
        _filas.append({"cat": str(agg[grp_col].iloc[_i]), "val": _v,
                       "lo": _run, "hi": _run + _v, "peso": float(pesos[_i]),
                       "total": False})
        _run += _v
    _filas.append({"cat": "TOTAL", "val": total,
                   "lo": min(0.0, total), "hi": max(0.0, total),
                   "peso": 100.0, "total": True})

    _bordes = [0.0] + [f["lo"] for f in _filas] + [f["hi"] for f in _filas]
    _dmin, _dmax = min(_bordes), max(_bordes)
    _span = (_dmax - _dmin) or 1.0

    for _idx, _f in enumerate(_filas):
        _lo, _hi = min(_f["lo"], _f["hi"]), max(_f["lo"], _f["hi"])
        _f["left_pct"] = (_lo - _dmin) / _span * 100
        _f["w_pct"] = max((_hi - _lo) / _span * 100, 0.4)  # mínimo visible
        # Conector: línea vertical fina donde terminó la barra anterior.
        _f["conn_pct"] = (((_filas[_idx - 1]["hi"] - _dmin) / _span * 100)
                          if _idx > 0 and not _f["total"] else None)

    # Colores semánticos de la tabla, todos desde tema.py (regla #1: nunca
    # un #hex suelto). `_tono` devuelve el par (texto, barra) según el signo.
    def _tono(v):
        return ((CELDA_POS_TEXTO, EXITO) if v > 0
                else (DANGER_TEXT, ERROR))

    def _celda_familia(f):
        """Primera columna: nombre + línea de contexto (TOP, SKUs, top3)."""
        _nom = f["cat"]
        if len(_nom) > 30:
            _nom = _nom[:29] + "…"
        _piezas = []
        _tp = _top_prod.get(f["cat"])
        if _tp and not f["total"]:
            _tnom, _tval, _tpct = _tp
            _tcol = _tono(f["val"])[0]
            _piezas.append(
                f"<span style='color:{GRIS_TEXTO_MEDIO}'>{_tnom.upper()}</span>"
                f" <span style='color:{_tcol};font-weight:500'>"
                f"{_tpct:.0f}%</span>")
        _n = (sum(_n_skus.values()) if (f["total"] and _n_skus)
              else _n_skus.get(f["cat"]))
        if _n:
            _piezas.append(f"{_n} SKU" + ("s" if _n != 1 else ""))
        _c3 = _conc3.get(f["cat"])
        if _c3 is not None and not f["total"]:
            _piezas.append(f"top3 {_c3:.0f}%")
        _peso_txt = ("&lt;1%" if (not f["total"] and f["peso"] < 0.5)
                     else f"{f['peso']:.0f}%")
        if f["total"]:
            _piezas.insert(0, f"{len(agg)} familias")
        else:
            _piezas.insert(0, f"<b style='font-weight:500'>{_peso_txt}</b>"
                              f" del total")
        # Separador fino en vez de "·": menos ruido entre piezas.
        _sep = f"<span style='color:{GRIS_BORDE};padding:0 5px'>|</span>"
        _sub = _sep.join(_piezas)
        _peso_nom = "600" if f["total"] else "500"
        _ls = "0.02em" if f["total"] else "0"
        return (f"<div style='font-weight:{_peso_nom};color:{TEXTO_PRINCIPAL};"
                f"font-size:12.5px;line-height:1.2;letter-spacing:{_ls};"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>"
                f"{_nom}</div>"
                f"<div style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
                f"line-height:1.35;margin-top:2px;white-space:nowrap;"
                f"overflow:hidden;text-overflow:ellipsis'>{_sub}</div>")

    def _celda_monto(f):
        """Segunda columna: monto y delta vs periodo anterior."""
        _col = GRIS_TEXTO_MEDIO if f["total"] else _tono(f["val"])[0]
        _sig = "+" if f["val"] > 0 else "−"      # menos tipográfico, no guion
        _html = (f"<div style='color:{_col};font-weight:600;font-size:13px;"
                 f"font-variant-numeric:tabular-nums;line-height:1.2;"
                 f"letter-spacing:-0.01em'>"
                 f"{_sig}S/ {abs(f['val']):,.0f}</div>")
        _dl = _delta.get(f["cat"])
        if _dl and not f["total"]:
            _dir, _dpct = _dl
            _arrow = "▲" if _dir == "down" else "▼"   # ▲ = empeora
            _dcol = DANGER_TEXT if _dir == "down" else CELDA_POS_TEXTO
            _html += (f"<div style='font-size:9.5px;color:{_dcol};"
                      f"line-height:1.35;margin-top:2px;"
                      f"font-variant-numeric:tabular-nums'>"
                      f"<span style='font-size:7px;vertical-align:1px'>"
                      f"{_arrow}</span> {_dpct:.0f}% vs ant.</div>")
        return _html

    def _celda_barra(f):
        """Tercera columna: la barra flotante + su conector."""
        _bg = GRIS_TEXTO_MEDIO if f["total"] else _tono(f["val"])[1]
        _alto = 12 if f["total"] else 9
        _conn = ""
        if f["conn_pct"] is not None:
            _conn = (f"<div style='position:absolute;"
                     f"left:{f['conn_pct']:.2f}%;top:3px;bottom:3px;"
                     f"width:1px;background:{GRIS_BORDE}'></div>")
        # El carril (fondo tenue de punta a punta) hace que la barra se lea
        # como posicionada DENTRO de una escala, no flotando en el vacío.
        return (f"<div style='position:relative;height:22px;width:100%'>"
                f"<div style='position:absolute;left:0;right:0;top:50%;"
                f"transform:translateY(-50%);height:{_alto}px;"
                f"background:{GRIS_FONDO};border-radius:999px'></div>{_conn}"
                f"<div style='position:absolute;left:{f['left_pct']:.2f}%;"
                f"width:{f['w_pct']:.2f}%;top:50%;"
                f"transform:translateY(-50%);"
                f"height:{_alto}px;background:{_bg};border-radius:999px'>"
                f"</div></div>")

    def _celda_pctval(f):
        """Cuarta columna: % del ajuste sobre el valorizado de la familia."""
        _pv = _pct_val.get(f["cat"])
        if _pv is None:
            return (f"<div style='font-size:11.5px;color:{GRIS_BORDE};"
                    f"text-align:right'>—</div>")
        _col = _tono(_pv)[0]
        return (f"<div style='font-size:11.5px;color:{_col};text-align:right;"
                f"font-weight:500;font-variant-numeric:tabular-nums'>"
                f"{_pv:+.1f}%</div>")

    def _celda_badge(f):
        """Quinta columna: el semáforo."""
        if f["total"]:
            _txt, _fg, _bg = "Total", GRIS_TEXTO, GRIS_FONDO
        else:
            _txt, _fg, _bg = _badge_for(f["peso"], f["val"])
            # _badge_for devuelve "⚠ CRÍTICO"; en la tabla el símbolo sobra
            # (el color ya lo dice) y va en capitalize — salvo "OK", que
            # .capitalize() convertiría en "Ok".
            _txt = _txt.split(" ", 1)[-1]
            _txt = _txt if _txt == "OK" else _txt.capitalize()
        return (f"<div style='text-align:right'><span style='display:inline-"
                f"block;padding:2.5px 8px;border-radius:999px;font-size:9.5px;"
                f"font-weight:600;letter-spacing:0.02em;background:{_bg};"
                f"color:{_fg};white-space:nowrap'>{_txt}</span></div>")

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

    # CSS de la tabla. Vive acá (y no en estilos/) porque está scopeado a
    # las keys de esta tabla, mismo criterio que el CSS del drill de
    # Proveedor en Compras. Comprime el gap vertical que Streamlit mete
    # entre st.columns y hace que el botón del gutter parezca una celda.
    st.markdown(f"""<style>
    /* Popover "Excluir productos": achica el boton que la regla global de
       estilos/_30_filtros.py deja en 180px de ancho y 15px de fuente. */
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] button {{
        min-width: 0 !important; padding: 2px 10px !important;
        font-size: 11px !important; font-weight: 400 !important;
        /* min-height propio: Streamlit fija 40px y es lo que mantenia el
           boton alto aun con el padding y la fuente ya reducidos. */
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
    /* ── Filas de la tabla ─────────────────────────────────────────── */
    div[class*="st-key-ajcas_fila_"] {{
        border-bottom: 1px solid {GRIS_LINEA};
        /* El padding negativo compensa el gap del gutter para que el
           resaltado de hover llegue al borde de la tarjeta. */
        margin: 0 -6px; padding: 0 6px;
        border-radius: 6px;
        transition: background .12s ease; }}
    div[class*="st-key-ajcas_fila_"]:hover {{ background: {LAVANDA_SELECCION}; }}
    /* Fila en foco: fondo lavanda + barra de acento a la izquierda. El
       sufijo _on en la key es el mismo patron que usan los chipwrap_*_on
       de estilos/_40_ajuste_franja.py. */
    div[class*="st-key-ajcas_fila_"][class*="_on"] {{
        background: {LAVANDA_FONDO};
        box-shadow: inset 2px 0 0 {ACENTO}; }}
    div[class*="st-key-ajcas_fila_"][class*="_on"]:hover {{
        background: {LAVANDA_FONDO}; }}
    /* Fila TOTAL: cierra la tabla, no participa del hover. */
    div[class*="st-key-ajcas_fila_total"] {{
        border-bottom: none; border-top: 1.5px solid {GRIS_BORDE};
        margin-top: 2px; background: transparent !important;
        box-shadow: none !important; }}
    div[class*="st-key-ajcas_fila_"] div[data-testid="stVerticalBlock"]
        {{ gap: 0 !important; }}
    /* OJO: nada de `align-items: center` acá. Con center las columnas
       dejan de estirarse y colapsan a ~6px con 30px de contenido adentro
       (overflow visible => las filas se pisan entre sí). El alto lo fija
       min-height y el centrado vertical va DENTRO de cada celda, abajo. */
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
        min-height: 26px !important; font-size: 11px !important;
        transition: color .12s ease, transform .12s ease !important; }}
    div[class*="st-key-ajcas_btn_"] button:hover {{
        color: {ACENTO} !important; background: transparent !important;
        transform: scale(1.25); }}
    div[class*="st-key-ajcas_btn_"] button[kind="primary"] {{
        color: {ACENTO} !important; }}
    </style>""", unsafe_allow_html=True)

    with _card("cascada", "Cascada por familia"):
        # Encabezado: título + insight a la izquierda, resumen a la derecha.
        _n_falt = int((agg[col_ajuste_val] < 0).sum())
        _col_neto = DANGER_TEXT if total < 0 else CELDA_POS_TEXTO
        _resumen = (f"{len(agg)} {grp_col.lower()}s"
                    f"<span style='color:{GRIS_BORDE};padding:0 6px'>|</span>"
                    f"{_n_falt} con faltante"
                    f"<span style='color:{GRIS_BORDE};padding:0 6px'>|</span>"
                    f"neto <span style='color:{_col_neto};font-weight:600;"
                    f"font-variant-numeric:tabular-nums'>"
                    f"S/ {total:,.0f}</span>")
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:12px'>"
            f"<span style='font-size:14px;font-weight:600;"
            f"color:{TEXTO_PRINCIPAL};letter-spacing:-0.01em'>"
            f"Ajuste valorizado por {grp_col.lower()}"
            + (f"<span style='font-size:11px;font-weight:400;"
               f"color:{GRIS_TEXTO_SUAVE}'> — {insight}</span>"
               if insight else "")
            + f"</span>"
              f"<span style='font-size:11px;color:{GRIS_TEXTO_SUAVE}'>"
              f"{_resumen}</span>"
              f"</div>", unsafe_allow_html=True)

        # Cabecera de la tabla
        st.markdown(
            f"<div style='display:flex;font-size:9px;color:{GRIS_TEXTO_SUAVE};"
            f"text-transform:uppercase;letter-spacing:.08em;font-weight:600;"
            f"padding:0 0 7px 0;border-bottom:1px solid {GRIS_BORDE}'>"
            f"<div style='width:4%'></div>"
            f"<div style='width:30%'>Familia</div>"
            f"<div style='width:17%'>Ajuste</div>"
            f"<div style='width:28%'>Cascada acumulada</div>"
            f"<div style='width:10%;text-align:right'>s/ val</div>"
            f"<div style='width:11%;text-align:right'>Estado</div>"
            f"</div>", unsafe_allow_html=True)

        # Una fila por familia. El gutter izquierdo lleva el botón que
        # prende/apaga el foco — una tabla HTML no emite eventos de clic,
        # así que el disparador tiene que ser un widget de Streamlit.
        for _f in _filas:
            _es_foco = (not _f["total"]) and _f["cat"] == focus
            # Sufijo _on en la key = fila resaltada (patrón chipwrap_*_on).
            with st.container(
                    key=f"ajcas_fila_{_slug(_f['cat'])}"
                        + ("_on" if _es_foco else "")):
                _c = st.columns([0.04, 0.30, 0.17, 0.28, 0.10, 0.11])
                with _c[0]:
                    if not _f["total"]:
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
                                              _celda_badge)):
                    with _col:
                        st.markdown(_fn(_f), unsafe_allow_html=True)

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
            + _punto(GRIS_TEXTO_MEDIO, "Total neto")
            + f"<span style='color:{GRIS_BORDE}'>|</span>"
              f"<span>Cada barra arranca donde terminó la anterior</span>"
              f"</div>", unsafe_allow_html=True)

        # ── Panel de drill (solo si hay foco) — DEBAJO de la tabla ─────
        # Mismo patrón que `_paneles_card()` del drill de Proveedor en
        # Compras: el panel no existe sin foco, y el mismo control que lo
        # abrió lo cierra.
        if focus:
            # Instance id: se incrementa cada vez que el panel pasa de
            # cerrado a abierto y se anexa a las keys de los charts. Sin
            # esto Streamlit reusa los nodos DOM, Plotly no re-mide el
            # ancho del contenedor y el gráfico sale vacío. Mismo bug (y
            # misma solución) que en el drill de Proveedor de Compras.
            if not st.session_state.get("ajcas_panel_prev", False):
                st.session_state["ajcas_panel_inst"] = (
                    st.session_state.get("ajcas_panel_inst", 0) + 1)
            st.session_state["ajcas_panel_prev"] = True
            _inst = st.session_state.get("ajcas_panel_inst", 0)

            col_d = st.container(border=True, key="ajcas_panel_drill")
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
                    _color_total = (DANGER_TEXT if _total_focus < 0
                                    else CELDA_POS_TEXTO)
                    st.markdown(
                        f"**{focus}**<br>"
                        f"<span style='font-size:11px;color:{GRIS_TEXTO_SUAVE}'>"
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
                    # Trae área y cantidad al agrupado si están disponibles,
                    # para poder mostrarlos junto al producto/monto.
                    # `first` asume 1 área por producto (cierto en esta data);
                    # si el drill vino desde área, el subtítulo de área sería
                    # redundante y se omite.
                    _has_cant = bool(col_cantidad
                                     and col_cantidad in _det.columns)
                    _has_area = bool(col_area and col_area in _det.columns
                                     and col_area != dim
                                     and col_area != grp_col)
                    _agg_map = {col_ajuste_val: "sum"}
                    if _has_cant:
                        _agg_map[col_cantidad] = "sum"
                    if _has_area:
                        _agg_map[col_area] = "first"
                    _sub = _det.groupby(dim, as_index=False).agg(_agg_map)
                    _sub["_abs"] = _sub[col_ajuste_val].abs()
                    _sub = _sub.sort_values(
                        "_abs", ascending=False).head(int(topn))
                    if _sub.empty or _sub["_abs"].sum() == 0:
                        st.info("Sin datos para el drill de esta familia.")
                    else:
                        # Split: sobrantes arriba (verde), faltantes abajo
                        # (rojo). Cada bloque con su propio eje X — mata la
                        # comparación cruzada de escala pero rescata a los
                        # sobrantes chicos de ser todos "pills" idénticos
                        # cuando conviven con faltantes grandes.
                        _pos = _sub[_sub[col_ajuste_val] > 0].sort_values(
                            col_ajuste_val, ascending=True)
                        _neg = _sub[_sub[col_ajuste_val] < 0].sort_values(
                            col_ajuste_val, ascending=False)

                        def _fig_split(_df, color_bar):
                            _labels = []
                            _texts = []
                            for _, _r in _df.iterrows():
                                _nom = str(_r[dim])
                                if len(_nom) > 34:
                                    _nom = _nom[:34] + "…"
                                if _has_area:
                                    _labels.append(
                                        f"{_nom}<br>"
                                        f"<span style='font-size:9px;"
                                        f"color:{GRIS_TEXTO_SUAVE}'>"
                                        f"{_r[col_area]}</span>"
                                    )
                                else:
                                    _labels.append(_nom)
                                _t = f"S/ {_r[col_ajuste_val]:,.0f}"
                                if _has_cant:
                                    _t += f" · {int(_r[col_cantidad]):,} und"
                                _texts.append(_t)
                            _fig = go.Figure(go.Bar(
                                x=_df[col_ajuste_val].tolist(),
                                y=_labels, orientation="h",
                                marker=dict(color=color_bar, cornerradius=4),
                                text=_texts,
                                textposition="auto",
                                insidetextanchor="end",
                                hovertemplate=("%{y}<br>"
                                               "<b>S/ %{x:,.2f}</b>"
                                               "<extra></extra>"),
                            ))
                            _fig.update_layout(**_layout_aj(
                                title_text="",
                                xaxis=dict(tickprefix="S/ ",
                                           tickformat=",.0f",
                                           gridcolor=GRIS_BORDE,
                                           zeroline=True,
                                           zerolinecolor=GRIS_BORDE,
                                           nticks=4),
                                yaxis=dict(gridcolor=GRIS_BORDE,
                                           showticklabels=True,
                                           automargin=True,
                                           tickfont=dict(size=10)),
                                showlegend=False,
                                # Filas ~36px para el label de 2 líneas
                                # (producto + área). Si no hay área, sigue
                                # cómodo.
                                height=max(140, 36 * len(_df) + 40),
                                bargap=0.35,
                                margin=dict(l=4, r=12, t=6, b=10),
                            ))
                            return _fig

                        # Al vivir abajo (y no en un panel al 40%), el drill
                        # tiene todo el ancho: faltantes y sobrantes van
                        # lado a lado en vez de apilados.
                        _pa, _pb = st.columns(2)
                        def _titulo_split(txt, color):
                            st.markdown(
                                f"<div style='font-size:9px;font-weight:600;"
                                f"color:{color};letter-spacing:.08em;"
                                f"text-transform:uppercase;"
                                f"margin:4px 0 -8px 0'>{txt}</div>",
                                unsafe_allow_html=True,
                            )

                        with _pa:
                            _titulo_split("Faltantes", DANGER_TEXT)
                            if _neg.empty:
                                st.caption("Sin faltantes en esta familia.")
                            else:
                                st.plotly_chart(
                                    _fig_split(_neg, ERROR),
                                    use_container_width=True,
                                    key=("ajuste_cascada_drill_neg_"
                                         f"{_slug(focus)}_{_inst}"),
                                )
                        with _pb:
                            _titulo_split("Sobrantes", CELDA_POS_TEXTO)
                            if _pos.empty:
                                st.caption("Sin sobrantes en esta familia.")
                            else:
                                st.plotly_chart(
                                    _fig_split(_pos, EXITO),
                                    use_container_width=True,
                                    key=("ajuste_cascada_drill_pos_"
                                         f"{_slug(focus)}_{_inst}"),
                                )
        else:
            st.session_state["ajcas_panel_prev"] = False
            st.caption("💡 Usá el ▸ de cada fila para ver sus productos.")


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
    # Escala simétrica: el 0 queda SIEMPRE en el centro del degradado, así
    # un faltante y un sobrante del mismo tamaño se ven igual de intensos.
    # Sin esto, zmid solo centra el color pero el rango sigue sesgado al
    # lado que tenga el extremo mayor.
    _vmax = float(abs(pivot.values).max()) or 1.0

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        # xgap/ygap: separa las celdas en baldosas. Sin esto el mapa se lee
        # como un bloque continuo y cuesta seguir filas y columnas.
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
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Área: <b>%{x}</b><br>"
            "Ajuste: <b>S/ %{z:,.2f}</b><extra></extra>"
        ),
    ))

    # Valores dentro de cada celda como ANNOTATIONS, no como `texttemplate`:
    # `textfont` es una sola config para toda la traza, así que el texto
    # oscuro quedaba ilegible sobre las celdas saturadas de los extremos.
    # Con annotations el color se decide celda por celda según intensidad.
    _anns_hm = []
    for _i, _fam in enumerate(pivot.index.tolist()):
        for _j, _area in enumerate(pivot.columns.tolist()):
            _v = float(pivot.values[_i][_j])
            # Los ceros se omiten: son la mayoría y solo agregan ruido.
            if abs(_v) < 0.5:
                continue
            _int = abs(_v) / _vmax
            _fg = BLANCO if _int > 0.55 else GRIS_TEXTO_MEDIO
            _anns_hm.append(dict(
                x=_area, y=_fam, xref="x", yref="y",
                text=f"{_v:,.0f}", showarrow=False,
                font=dict(size=9.5, color=_fg,
                          family="ui-monospace, monospace"),
            ))

    fig.update_layout(**_layout_aj(
        title_text="",   # el título ya lo pone la tarjeta
        xaxis=dict(tickangle=0, side="top", gridcolor=GRIS_BORDE,
                   showgrid=False, ticks="",
                   tickfont=dict(size=10, color=GRIS_TEXTO)),
        yaxis=dict(autorange="reversed", gridcolor=GRIS_BORDE,
                   showgrid=False, ticks="", showticklabels=True,
                   tickfont=dict(size=10, color=GRIS_TEXTO_MEDIO)),
        # Alto por fila en vez de tope fijo: con el tope de 400px las
        # celdas se aplastaban cuando había muchas familias.
        height=min(560, max(240, len(pivot.index) * 38 + 110)),
        margin=dict(l=10, r=10, t=50, b=20),
        annotations=_anns_hm,
    ))
    # plot_bgcolor pinta lo que se ve POR DEBAJO de las celdas — es decir,
    # los gaps de xgap/ygap. `_layout_aj` lo fuerza transparente (queda el
    # blanco de la tarjeta y la grilla desaparecía: celda blanca sobre gap
    # blanco). Con un gris tenue los gaps se leen como líneas de grilla.
    fig.update_layout(plot_bgcolor=GRIS_BORDE)
    _xcats = [str(c) for c in pivot.columns.tolist()]
    fig.update_xaxes(tickmode="array", tickvals=_xcats,
                     ticktext=_wrap_cat(_xcats))

    # Subtítulo con la peor combinación: el dato que se busca en un mapa de
    # calor es "dónde está el punto rojo", y decirlo evita rastrearlo a ojo.
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

    with _card("heatmap", "Mapa de calor"):
        if _sub_hm:
            st.markdown(f"<div style='margin:-4px 0 6px 0'>{_sub_hm}</div>",
                        unsafe_allow_html=True)
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
                                   col_cantidad=col_cantidad,
                                   df_full=df_full, col_fecha=col_fecha)
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
