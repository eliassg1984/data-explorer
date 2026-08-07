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
    ACENTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA, GRIS_BORDE, GRIS_FONDO,
    PALETA_SERIES, SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
    BLANCO, CELDA_ALERTA_FONDO, CELDA_ALERTA_TEXTO, CELDA_POS_TEXTO,
    DANGER_TEXT, ERROR, ERROR_FONDO, ESCALA_CONTINUA, EXITO, EXITO_FONDO,
    GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FONDO, LAVANDA_SELECCION,
    AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO,
    AJUSTE_CRIT_FONDO, AJUSTE_CRIT_TEXTO, AJUSTE_CRIT_BORDE,
    AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO, AJUSTE_ALERTA_BORDE,
    AJUSTE_SOB_FONDO, AJUSTE_SOB_BORDE,
)
from graficos.base import (
    _card, _es_movil, _layout, _render_rail, _resolver, _slug, _wrap_cat,
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
                     ("Comparativa mensual", "Comparativa"),
                     ("Por fecha de corte",  "Por fecha"))),
    ("Datos",       (("Tabla",          "Tabla"),)),
)


def categoria_rango_ajuste(graf_id):
    """A qué categoría de rango de fecha pertenece un item del rail de
    Ajuste: "tiempo" (Evolución/Comparativa — necesitan varios meses o un
    año para decir algo) o "visual" (Cascada/Mapa de calor/Distribución/
    Tabla — snapshot de un período, tiene sentido acotado a un mes).

    `app.py` usa esto para decidir qué clave de `session_state` lee/escribe
    la franja de fecha (`ajuste_rango_aplicado_visual` vs `_tiempo`, ver
    `estado_rango.clave_rango`) — así cada categoría recuerda su propio
    rango sin pisar al otro. Única fuente de verdad: `_AJUSTE_RAIL_CATEGORIAS`
    de arriba; si se agrega un item nuevo al rail, esto no hay que tocarlo."""
    for cat_nombre, items in _AJUSTE_RAIL_CATEGORIAS:
        if cat_nombre == "Tiempo" and any(oid == graf_id for oid, _ in items):
            return "tiempo"
    return "visual"


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


_MESES_ABR_ES = ("ene", "feb", "mar", "abr", "may", "jun",
                 "jul", "ago", "set", "oct", "nov", "dic")


def _fmt_corte(fecha):
    """'02-ago' en vez de '02-Aug' — strftime('%b') usa el locale del
    sistema (inglés en Streamlit Cloud), y esta app es en español."""
    _ts = pd.Timestamp(fecha)
    return f"{_ts.day:02d}-{_MESES_ABR_ES[_ts.month - 1]}"


def _graf_pivote_fecha_ajuste(df, col_familia, col_ajuste_val, col_producto,
                              col_cantidad, col_fecha):
    """Tabla dinámica: Familia > Subfamilia > Producto como filas
    expandibles, una fecha de corte por grupo de columnas (Ajuste
    Valorizado + Cantidad) con flecha + color de tendencia vs. el corte
    anterior.

    No usa el "Modo pivote" nativo de AG Grid (ver tablas/_config.py,
    pensado para Ajuste): ese pivotea UNA columna a elección del usuario,
    pero comparar cada columna contra su vecina por fila —el punto
    central de esta vista— necesitaría un cellRenderer JsCode a medida.
    Se pre-pivotea con pandas (`pivot_table`) y se renderiza HTML propio,
    mismo patrón que el resto de filas de este archivo."""
    if not (col_familia and col_fecha and col_producto and col_ajuste_val):
        st.info("Se necesita familia, fecha, producto y ajuste valorizado "
                "para la tabla dinámica.")
        return

    # Subfamilia no viene resuelta desde renderizar_graficos_ajuste (nadie
    # más la usa en este archivo) — mismos candidatos que
    # graficos/compras/__init__.py::col_subfam, para no reinventar nombres.
    col_subfamilia = _resolver(df, ["Subfamilia", "Nombre Subfamilia"])
    _has_sub = bool(col_subfamilia and col_subfamilia in df.columns)
    _has_cant = bool(col_cantidad and col_cantidad in df.columns)

    d = df.copy()
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors="coerce")
    _req = [col_fecha, col_familia, col_producto] + (
        [col_subfamilia] if _has_sub else [])
    d = d.dropna(subset=_req)
    if d.empty:
        st.info("Sin datos para la tabla dinámica en el rango seleccionado.")
        return

    _cortes_todos = sorted(d[col_fecha].dropna().unique())
    _MAX_CORTES = 6
    _recortado = len(_cortes_todos) > _MAX_CORTES
    _cortes = _cortes_todos[-_MAX_CORTES:] if _recortado else _cortes_todos
    if not _cortes:
        st.info("Sin fechas de corte en el rango seleccionado.")
        return
    # El Total de cada fila suma solo los cortes MOSTRADOS (no todo el
    # rango) -- así siempre cuadra con lo que se ve en pantalla.
    d = d[d[col_fecha].isin(_cortes)]

    def _pivotear(cols_grupo):
        _val = d.pivot_table(index=cols_grupo, columns=col_fecha,
                             values=col_ajuste_val, aggfunc="sum",
                             fill_value=0.0)
        _cant = (d.pivot_table(index=cols_grupo, columns=col_fecha,
                               values=col_cantidad, aggfunc="sum",
                               fill_value=0.0)
                 if _has_cant else None)
        return _val, _cant

    _cols_sub = [col_familia, col_subfamilia] if _has_sub else None
    _cols_prod = ([col_familia, col_subfamilia, col_producto] if _has_sub
                  else [col_familia, col_producto])

    _val_fam, _cant_fam = _pivotear([col_familia])
    _val_sub, _cant_sub = _pivotear(_cols_sub) if _has_sub else (None, None)
    _val_prod, _cant_prod = _pivotear(_cols_prod)

    _fams = _val_fam.sum(axis=1).sort_values().index.tolist()

    _exp_fam = st.session_state.setdefault("ajuste_pivote_exp_fam", set())
    _exp_sub = st.session_state.setdefault("ajuste_pivote_exp_sub", set())

    def _sig(v):
        return "+" if v > 0 else ("−" if v < 0 else "")

    def _col_signo(v):
        if v > 0:
            return CELDA_POS_TEXTO
        if v < 0:
            return DANGER_TEXT
        return GRIS_TEXTO

    def _celda_corte(v, v_prev, es_primero, cantidad):
        _col = _col_signo(v)
        _txt = f"{_sig(v)}S/ {abs(v):,.0f}"
        _flecha = ""
        if not es_primero and v != v_prev:
            _fcol, _fg = (EXITO, "▲") if v > v_prev else (ERROR, "▼")
            _flecha = (f"<span style='color:{_fcol};font-size:8px;"
                       f"margin-right:2px'>{_fg}</span>")
        _html = (f"<div style='color:{_col};font-weight:500;"
                 f"font-variant-numeric:tabular-nums'>{_flecha}{_txt}</div>")
        if cantidad is not None:
            _html += (f"<div style='color:{GRIS_TEXTO_SUAVE};font-size:"
                      f"9.5px;font-variant-numeric:tabular-nums'>"
                      f"{_sig(cantidad)}{abs(cantidad):,.0f}</div>")
        return _html

    _ancho_nombre = max(34 - (len(_cortes) * 1.5), 18)
    _ancho_corte = (100 - _ancho_nombre - 13) / len(_cortes)

    def _fila_html(nombre, indent_px, val_row, cant_row, tot_val, tot_cant,
                   negrita=False):
        _peso = "600" if negrita else "500"
        _piezas = [
            f"<div style='width:{_ancho_nombre}%;padding-left:{indent_px}px;"
            f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"
            f"font-weight:{_peso};color:{TEXTO_PRINCIPAL};font-size:12px'>"
            f"{nombre}</div>"
        ]
        for _i, _c in enumerate(_cortes):
            _v = float(val_row.get(_c, 0.0))
            _v_prev = float(val_row.get(_cortes[_i - 1], 0.0)) if _i > 0 else 0.0
            _cant = float(cant_row.get(_c, 0.0)) if cant_row is not None else None
            _piezas.append(
                f"<div style='width:{_ancho_corte}%;text-align:right'>"
                f"{_celda_corte(_v, _v_prev, _i == 0, _cant)}</div>"
            )
        _cant_tot_html = (
            f"<div style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
            f"font-weight:400'>{_sig(tot_cant)}{abs(tot_cant):,.0f}</div>"
            if tot_cant is not None else "")
        _piezas.append(
            f"<div style='width:13%;text-align:right;font-weight:600;"
            f"color:{ACENTO_TEXTO_OSCURO}'>{_sig(tot_val)}S/ "
            f"{abs(tot_val):,.0f}{_cant_tot_html}</div>"
        )
        return (f"<div style='display:flex;align-items:center;gap:4px;"
                f"padding:5px 0'>{''.join(_piezas)}</div>")

    # Cabecera pegajosa: se ancla justo debajo de la franja superior fija
    # (título + fecha), que ya ocupa de --cab-nivel1-top a +--cab-altura.
    # z-index por debajo de esa franja (20) para no taparla si algo se
    # solapa en el borde.
    #
    # OJO — el sticky va en el PADRE, no en `.st-key-ajpiv_header`: todo
    # `st.container(key=...)` queda envuelto por Streamlit en un
    # `stLayoutWrapper` invisible (sin key propia) que es hijo directo de
    # `stMain`/`stMainBlockContainer`/etc. Puesto en el propio div con key,
    # el sticky no engancha (se movía 1:1 con el scroll pese a que
    # `getComputedStyle` ya marcaba `position: sticky` — se verificó
    # scroll a scroll con getBoundingClientRect, no alcanza con leer el
    # estilo computado). Puesto en el wrapper vía `:has()`, sí engancha
    # -- confirmado con tres posiciones de scroll distintas quedando fijo
    # en el mismo top. Ver arquitectura.md regla #25 (sumar caso).
    st.markdown(f"""<style>
    div:has(> .st-key-ajpiv_header) {{
        position: sticky !important;
        top: calc(var(--cab-nivel1-top, 30px) + var(--cab-altura, 50px))
             !important;
        z-index: 5 !important;
        background: {BLANCO} !important;
    }}
    </style>""", unsafe_allow_html=True)

    with _card("pivote_fecha"):
        st.markdown(
            f"<div style='font-size:14px;font-weight:500;"
            f"color:{TEXTO_PRINCIPAL};margin-bottom:2px'>"
            f"Ajuste por fecha de corte</div>",
            unsafe_allow_html=True,
        )
        if _recortado:
            st.caption(
                f"Mostrando los últimos {_MAX_CORTES} cortes de "
                f"{len(_cortes_todos)} en el rango — acotá el rango de "
                f"fecha (arriba) para ver otros."
            )
        else:
            st.markdown("<div style='margin-bottom:8px'></div>",
                        unsafe_allow_html=True)

        _hdr = ["<div style='width:{}%'></div>".format(_ancho_nombre)]
        for _c in _cortes:
            _hdr.append(
                f"<div style='width:{_ancho_corte}%;text-align:right;"
                f"font-size:10px;color:{GRIS_TEXTO_SUAVE};font-weight:600;"
                f"text-transform:uppercase'>"
                f"{_fmt_corte(_c)}</div>"
            )
        _hdr.append(
            f"<div style='width:13%;text-align:right;font-size:10px;"
            f"color:{ACENTO_TEXTO_OSCURO};font-weight:600;"
            f"text-transform:uppercase'>Total</div>"
        )
        with st.container(key="ajpiv_header"):
            st.markdown(
                f"<div style='display:flex;gap:4px;padding:6px 0;"
                f"border-bottom:1px solid {GRIS_BORDE}'>"
                f"{''.join(_hdr)}</div>",
                unsafe_allow_html=True,
            )

        for _fam in _fams:
            _fam_abierta = _fam in _exp_fam
            _tot_fam_val = float(_val_fam.loc[_fam].sum())
            _tot_fam_cant = float(_cant_fam.loc[_fam].sum()) if _has_cant else None
            _c0, _c1 = st.columns([0.04, 0.96])
            with _c0:
                if st.button("▾" if _fam_abierta else "▸",
                            key=f"ajpiv_fam_{_slug(str(_fam))}",
                            help="Colapsar" if _fam_abierta else "Expandir"):
                    (_exp_fam.discard if _fam_abierta else _exp_fam.add)(_fam)
                    st.rerun()
            with _c1:
                st.markdown(
                    _fila_html(str(_fam), 0, _val_fam.loc[_fam],
                              _cant_fam.loc[_fam] if _has_cant else None,
                              _tot_fam_val, _tot_fam_cant, negrita=True),
                    unsafe_allow_html=True,
                )

            if not _fam_abierta:
                continue

            if not _has_sub:
                # Sin subfamilia: directo a top 10 productos de la familia.
                if _fam not in _val_prod.index.get_level_values(0):
                    continue
                _prods_fam = _val_prod.loc[[_fam]]
                _orden = _prods_fam.sum(axis=1).abs().sort_values(
                    ascending=False).head(10).index
                for _key in _orden:
                    _prod = _key[-1]
                    _tv = float(_val_prod.loc[_key].sum())
                    _tc = float(_cant_prod.loc[_key].sum()) if _has_cant else None
                    st.markdown(
                        _fila_html(str(_prod), 20, _val_prod.loc[_key],
                                  _cant_prod.loc[_key] if _has_cant else None,
                                  _tv, _tc),
                        unsafe_allow_html=True,
                    )
                continue

            if _fam not in _val_sub.index.get_level_values(0):
                continue
            _subs_fam = sorted(
                _val_sub.loc[_fam].index.tolist(),
                key=lambda s: _val_sub.loc[(_fam, s)].sum())

            for _sub in _subs_fam:
                _sub_key = f"{_fam}||{_sub}"
                _sub_abierta = _sub_key in _exp_sub
                _tot_sub_val = float(_val_sub.loc[(_fam, _sub)].sum())
                _tot_sub_cant = (float(_cant_sub.loc[(_fam, _sub)].sum())
                                if _has_cant else None)
                _sc0, _sc1 = st.columns([0.04, 0.96])
                with _sc0:
                    if st.button(
                            "▾" if _sub_abierta else "▸",
                            key=f"ajpiv_sub_{_slug(str(_fam))}_{_slug(str(_sub))}",
                            help="Colapsar" if _sub_abierta else "Ver productos"):
                        (_exp_sub.discard if _sub_abierta else _exp_sub.add)(_sub_key)
                        st.rerun()
                with _sc1:
                    st.markdown(
                        _fila_html(str(_sub), 20, _val_sub.loc[(_fam, _sub)],
                                  _cant_sub.loc[(_fam, _sub)] if _has_cant else None,
                                  _tot_sub_val, _tot_sub_cant),
                        unsafe_allow_html=True,
                    )

                if not _sub_abierta:
                    continue
                if (_fam, _sub) not in _val_prod.index.droplevel(-1):
                    continue
                _prods_sub = _val_prod.loc[(_fam, _sub)]
                _orden_p = _prods_sub.sum(axis=1).abs().sort_values(
                    ascending=False).head(10).index
                for _p in _orden_p:
                    _key = (_fam, _sub, _p)
                    _tv = float(_val_prod.loc[_key].sum())
                    _tc = float(_cant_prod.loc[_key].sum()) if _has_cant else None
                    st.markdown(
                        _fila_html(str(_p), 40, _val_prod.loc[_key],
                                  _cant_prod.loc[_key] if _has_cant else None,
                                  _tv, _tc),
                        unsafe_allow_html=True,
                    )

        _tot_gen_val = float(_val_fam.sum().sum())
        _tot_gen_cant = float(_cant_fam.sum().sum()) if _has_cant else None
        _tg0, _tg1 = st.columns([0.04, 0.96])
        with _tg1:
            st.markdown(
                _fila_html("TOTAL GENERAL", 0, _val_fam.sum(axis=0),
                          _cant_fam.sum(axis=0) if _has_cant else None,
                          _tot_gen_val, _tot_gen_cant, negrita=True),
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<div style='display:flex;gap:14px;flex-wrap:wrap;"
            f"font-size:9.5px;color:{GRIS_TEXTO_SUAVE};margin-top:10px'>"
            f"<span><span style='color:{EXITO}'>▲</span> mejoró</span>"
            f"<span><span style='color:{ERROR}'>▼</span> empeoró</span>"
            f"<span style='color:{GRIS_BORDE}'>|</span>"
            f"<span>vs. la fecha de corte anterior — el color del texto "
            f"es el signo (faltante/sobrante), independiente de la "
            f"flecha</span></div>",
            unsafe_allow_html=True,
        )


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
        """(texto, fg, bg, borde) — Menor/OK sin borde (gris neutro, como
        hoy); Crítico/Alerta/Sobrante llevan un borde fino pastel: con
        relleno tan claro, el borde es lo que evita que se pierdan contra
        el blanco de la card."""
        if val >= 0:
            return ("▲ SOBRANTE", AJUSTE_POS_TEXTO, AJUSTE_SOB_FONDO, AJUSTE_SOB_BORDE)
        if peso >= 40:
            return ("⚠ CRÍTICO", AJUSTE_CRIT_TEXTO, AJUSTE_CRIT_FONDO, AJUSTE_CRIT_BORDE)
        if peso >= 20:
            return ("● ALERTA", AJUSTE_ALERTA_TEXTO, AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_BORDE)
        if peso >= 5:
            return ("● MENOR", GRIS_TEXTO, GRIS_FONDO, None)
        return ("✓ OK", GRIS_TEXTO, GRIS_FONDO, None)

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
        return ((AJUSTE_POS_TEXTO, AJUSTE_POS) if v > 0
                else (AJUSTE_NEG_TEXTO, AJUSTE_NEG))

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
            _dcol = AJUSTE_NEG_TEXTO if _dir == "down" else AJUSTE_POS_TEXTO
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
        _txt, _fg, _bg, _bd = _badge_for(f["peso"], f["val"])
        _txt = _txt.split(" ", 1)[-1]
        _txt = _txt if _txt == "OK" else _txt.capitalize()
        _borde = f"border:1px solid {_bd};" if _bd else "border:1px solid transparent;"
        return (f"<div style='text-align:right'><span style='display:inline-"
                f"block;padding:1.5px 7px;border-radius:999px;font-size:9.5px;"
                f"font-weight:600;letter-spacing:0.02em;background:{_bg};"
                f"{_borde}color:{_fg};white-space:nowrap'>{_txt}</span></div>")

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
        (AJUSTE_CRIT_FONDO etc.), queda muy fuerte para una fila entera."""
        h = hexcolor.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    _tint_critico = _hex_rgba(AJUSTE_NEG, 0.08)
    _tint_alerta = _hex_rgba(AJUSTE_ALERTA_TEXTO, 0.09)
    _tint_sobrante = _hex_rgba(AJUSTE_POS, 0.08)

    def _tono_capsula(v):
        """(texto, fondo) para las cápsulas KPI del título — estilo "fondo
        sutil": mismo par texto/fondo que el badge de Estado equivalente
        (Sobrante/Crítico en _badge_for), pero SIN el borde del badge — acá
        la cápsula ya se distingue por vivir junto al título, no necesita
        el refuerzo del borde."""
        if v > 0:
            return (AJUSTE_POS_TEXTO, AJUSTE_SOB_FONDO)
        return (AJUSTE_NEG_TEXTO, AJUSTE_CRIT_FONDO)

    st.markdown(f"""<style>
    /* Popover "Excluir productos": achica el boton que la regla global de
       estilos/_30_filtros.py deja en 180px de ancho y 15px de fuente.
       El wrapper [data-testid="stPopover"] mide 33px aunque el boton mide
       26px: como el boton es inline-flex dentro de un div en block-flow,
       arma una linea de texto propia (strut) con el line-height heredado
       (1.6 por defecto) y le agrega ~7px "fantasma" arriba/abajo. Se
       resetea a 0 aqui, en el ancestro, para que el wrapper abrace el
       boton sin ese aire. white-space:nowrap evita que "Excluir
       productos" parta en 2 lineas si la columna [6,1] se angosta (eso
       si crecia el boton bastante mas alla de los 33px). */
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] {{
        line-height: 0; }}
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
        {{ font-size: 11px !important; white-space: nowrap !important; }}
    .st-key-ajcas_excl_wrap [data-testid="stPopover"] button
        [data-testid="stIconMaterial"]
        {{ font-size: 13px !important; width: 13px !important;
          height: 13px !important; }}
    /* Selector "Top N" del drill (una para Faltantes, otra para Sobrantes —
       keys ajuste_cascada_topn_neg/_pos, por eso el match es por prefijo).
       2026-08-06, a pedido ("que ya no sean cápsulas"): antes eran píldoras
       de 24px con borde+fondo, mucho más gruesas que el título de al lado
       (14px). Ahora es texto plano — sin fondo, sin borde — al mismo
       tamaño/peso que FALTANTES/SOBRANTES, separado por "·" (::before en
       vez de un separador real en el DOM, que Streamlit no deja insertar
       entre botones). El activo se marca solo con color + negrita. */
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"] {{
        gap: 3px !important; justify-content: flex-end !important; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"] button[role="radio"] {{
        min-width: 0 !important; padding: 0 3px !important;
        min-height: 0 !important; height: auto !important;
        line-height: 1 !important; border: none !important;
        background: transparent !important; box-shadow: none !important; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"]
        button[role="radio"]:not(:first-child)::before {{
        content: '·'; margin-right: 6px; color: {GRIS_TEXTO_SUAVE};
        font-size: 9px; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"] button[role="radio"] p {{
        font-size: 9px !important; font-weight: 600 !important;
        letter-spacing: .02em !important; line-height: 1 !important;
        margin: 0 !important; color: {GRIS_TEXTO_SUAVE} !important;
        transition: color .12s ease; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"]
        button[role="radio"]:hover p {{ color: {ACENTO} !important; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"]
        button[role="radio"][aria-checked="true"] {{
        background: transparent !important; border: none !important; }}
    div[class*="st-key-ajuste_cascada_topn_"] [data-testid="stButtonGroup"]
        button[role="radio"][aria-checked="true"] p {{
        color: {ACENTO_TEXTO_OSCURO} !important; font-weight: 800 !important; }}
    /* Mismo bug de arquitectura.md regla 33 en el título ("Faltantes" /
       "Sobrantes"): stMarkdownContainer trae margin-bottom:-16px nativo de
       Streamlit y el <div> raíz no tiene <p> que lo absorba. Acá no pisa a
       nadie (es el último elemento visible de su columna), pero sí rompe
       vertical_alignment="center": Streamlit centra la CAJA, que mide 16px
       menos de lo que el texto pinta, así que el título quedaba ~8px por
       debajo del centro real de la fila (verificado con
       getBoundingClientRect). Se cancela igual que .ajcas-head. */
    [data-testid="stMarkdownContainer"]:has(> .ajcas-topn-label) {{
        margin-bottom: 0 !important; }}
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
    /* ── Panel de drill (Faltantes/Sobrantes): "línea guía + indent" —
       sin caja propia (ni fondo ni borde alrededor). Un filete lavanda
       de 2px a la izquierda continúa el acento morado de la fila con
       foco, y el contenido queda indentado — mismo patrón visual que un
       hilo de comentarios o un árbol de archivos ("esto cuelga de la
       fila de arriba"). margin-top negativo achica el
       row-gap:6px + margin-bottom:4px de la fila (10px de base) a un
       espacio chico (~2px), sin llegar al solape que usaba la variante
       fusionada — acá no hay bordes que calzar. */
    div[class*="st-key-ajcas_panel_drill"] {{
        background: transparent !important;
        border: none !important;
        border-left: 2px solid {LAVANDA_BORDE} !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        margin: -8px 0 4px 3px !important;
        padding: 10px 8px 12px 20px !important; }}
    div[class*="st-key-ajcas_panel_drill"] > div {{
        border: none !important; }}
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
    /* ── Tooltip del título ────────────────────────────────────────────
       "Cada barra arranca donde terminó la anterior" vivía como leyenda
       fija al pie de la cascada, junto a los puntos Faltante/Sobrante.
       Ambos se sacaron: el color de las barras y los badges de Estado ya
       dicen faltante/sobrante, y la nota de la cascada acumulada es una
       aclaración de una sola vez — no merece ocupar una fila permanente.
       Ahora se muestra al pasar el cursor sobre el título.
       El texto va en un <span> anidado y NO en un data-* + content:
       attr(): el sanitizador de markdown de Streamlit no garantiza que
       sobrevivan los atributos custom, las clases sí (mismo patrón que
       .titulo-ajuste-reporte / .ultima-actualizacion).
       :active además de :hover → en táctil no hay hover; con esto el
       globo aparece mientras se mantiene el dedo sobre el título. */
    .ajcas-tip {{ position: relative; cursor: help; }}
    .ajcas-tip-i {{
        display: inline-flex; align-items: center; justify-content: center;
        width: 12px; height: 12px; margin-left: 5px;
        border: 1px solid {GRIS_BORDE}; border-radius: 999px;
        color: {GRIS_TEXTO_SUAVE}; font-size: 8.5px; font-weight: 700;
        font-style: italic; line-height: 1; vertical-align: 1px;
        transition: color .12s ease, border-color .12s ease; }}
    .ajcas-tip:hover .ajcas-tip-i, .ajcas-tip:active .ajcas-tip-i {{
        color: {ACENTO}; border-color: {ACENTO}; }}
    .ajcas-tip-txt {{
        position: absolute; left: 0; top: calc(100% + 7px); z-index: 40;
        padding: 6px 9px; border-radius: 7px;
        background: {TEXTO_PRINCIPAL}; color: {BLANCO};
        font-size: 10.5px; font-weight: 500; line-height: 1.35;
        white-space: nowrap; letter-spacing: 0.01em;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.16);
        opacity: 0; visibility: hidden; transform: translateY(-3px);
        pointer-events: none;
        transition: opacity .14s ease, transform .14s ease,
                    visibility .14s ease; }}
    .ajcas-tip:hover .ajcas-tip-txt, .ajcas-tip:active .ajcas-tip-txt {{
        opacity: 1; visibility: visible; transform: translateY(0); }}
    /* En pantallas angostas el globo no puede desbordar a la derecha. */
    @media (max-width: 768px) {{
        .ajcas-tip-txt {{ white-space: normal; width: min(240px, 70vw); }}
    }}
    /* ── Aire sobre el título ───────────────────────────────────────────
       Medido en el DOM: quedaban 18px entre el borde de la card y el
       título — 15px del padding-top que Streamlit le da por defecto a
       st.container(border=True) más 2px del div del título. Se recorta
       el padding SUPERIOR (los laterales siguen en 15px) para que el
       título suba sin desalinearse del popover "Excluir productos": los
       dos viven en el mismo stHorizontalBlock, así que mover la card los
       sube juntos. Acotado a chartcard_cascada — el resto de las cards
       de gráficos conserva su padding.
       El aire se recorta ACÁ y no en el padding del div del título: ese
       div vive solo en la columna izquierda, así que tocarlo movía el
       título 2px más que al popover y los descentraba entre sí
       (verificado midiendo ambos rects).

       row-gap: las filas de familia son hijas directas de este flex, así
       que lo que las separa es el gap del contenedor (16px por defecto
       en Streamlit) MÁS el margin-bottom de 4px de cada fila — 20px
       medidos. Con 6px quedan a 10px. Es un solo número para las tres
       separaciones de la card: título→cabecera 27→17, fila→fila 20→10,
       y la card baja de 214 a 184px (entran más familias sin
       scrollear). Si hay que separar SOLO las filas sin tocar el
       resto, el knob es el margin-bottom de st-key-ajcas_fila_, no
       este gap.

       cabecera→1ª fila NO sigue esa cuenta — ver el fix de .ajcas-head
       de abajo: con el gap en 16px (default) el numero daba 0 gap "por
       suerte"; al bajar a 6px paso a ser overlap negativo real. */
    div[class*="st-key-chartcard_cascada"] {{
        padding-top: 0px !important;
        row-gap: 6px !important; }}
    /* ── Cabecera de la tabla se comía la 1ª fila (regla nueva, ver
       arquitectura.md) ──────────────────────────────────────────────
       stMarkdownContainer trae de Streamlit un margin-bottom:-16px
       nativo (compensa el margin de un <p> normal, que aca no existe
       porque el HTML empieza con <div> y CommonMark lo trata como
       bloque HTML crudo, sin envolverlo en <p>). Ese -16px le resta
       16px a la altura que ve el flex padre (chartcard_cascada) para
       ESTE item -> el border-bottom del header (visualmente 22px de
       alto) queda pintado bien por debajo de donde el flex cree que
       termina el item, montado sobre la fila siguiente.
       Medido en vivo: stElementContainer quedaba en 6.4px de alto
       aunque el contenido pintaba 22.4px. Fix: cancelar el -16px nativo
       SOLO en el stMarkdownContainer que envuelve a .ajcas-head (la
       clase sobrevive al sanitizador, ver comentario junto al
       st.markdown de la cabecera). Sin esto, cualquier st.markdown con
       <div> como tag raiz (no <span>/<p>) en esta card puede pisar lo
       que venga despues. */
    [data-testid="stMarkdownContainer"]:has(> .ajcas-head) {{
        margin-bottom: 0 !important; }}
    </style>""", unsafe_allow_html=True)

    with _card("cascada"):
        # ── Título + KPIs (antes vivían en la fila TOTAL de la tabla)
        #    2026-08-07: alineados a la izquierda dentro de su columna
        #    (antes centrados, a pedido — ver git log si hace falta
        #    volver). Los KPIs van cada uno en su propia cápsula
        #    tonalizada por signo, no como texto plano separado por "|"
        #    — así se distinguen del título de un vistazo en lugar de
        #    leerse como una sola frase.────────

        # El título es además el disparador del tooltip que explica la
        # cascada acumulada (ver el bloque .ajcas-tip en el <style> de
        # arriba). white-space:nowrap va en el texto, NO en el .ajcas-tip:
        # si envolviera al globo, el override móvil que lo deja fluir en
        # varias líneas no tendría efecto.
        _titulo_html = (
            f"<span class='ajcas-tip' style='font-size:15.5px;"
            f"font-weight:600;color:{GRIS_TEXTO_MEDIO}'>"
            f"<span style='white-space:nowrap'>"
            f"Ajuste valorizado por {grp_col.lower()}</span>"
            f"<span class='ajcas-tip-i'>i</span>"
            f"<span class='ajcas-tip-txt'>Cada barra arranca donde "
            f"terminó la anterior</span></span>")

        def _capsula(fg, bg, contenido):
            """Estilo "fondo sutil": sin borde, esquinas 8px (no pill 999px)
            — se lee como un resaltado detrás de la cifra, no como una
            alerta. La etiqueta (neto / s·total) hereda `fg` a opacidad
            reducida en vez del gris genérico, para que quede claro que es
            parte de la misma cápsula."""
            return (f"<span style='display:inline-flex;align-items:"
                    f"baseline;gap:6px;background:{bg};border-radius:8px;"
                    f"padding:4px 10px;color:{fg}'>{contenido}</span>")

        _sig_tot = "+" if total > 0 else "−"
        _col_tot, _bg_tot = _tono_capsula(total)
        _kpi_neto_html = _capsula(_col_tot, _bg_tot, (
            f"<span style='font-size:11.5px;color:{_col_tot};opacity:.65'>"
            f"neto</span> <span style='font-size:15px;font-weight:700;"
            f"font-variant-numeric:tabular-nums'>"
            f"{_sig_tot}S/ {abs(total):,.0f}</span>"))

        _kpi_pct_html = ""
        if _kpi_pct_total is not None:
            _col_pct, _bg_pct = _tono_capsula(_kpi_pct_total)
            _kpi_pct_html = _capsula(_col_pct, _bg_pct, (
                f"<span style='font-size:15px;font-weight:700;"
                f"font-variant-numeric:tabular-nums'>"
                f"{_kpi_pct_total:+.1f}%</span> "
                f"<span style='font-size:11.5px;color:{_col_pct};opacity:.65'>"
                f"s/ total</span>"))

        _col_titulo, _col_excl = st.columns([6, 1])
        with _col_titulo:
            st.markdown(
                f"<div style='display:flex;align-items:center;"
                f"justify-content:flex-start;flex-wrap:wrap;gap:12px;"
                f"padding:6px 0 14px 0'>"
                f"{_titulo_html}{_kpi_neto_html}{_kpi_pct_html}</div>",
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
        # class="ajcas-head": necesaria para el fix de margen de abajo (ver
        # regla en el <style> de arriba / arquitectura.md) — sobrevive al
        # sanitizador de markdown igual que .ajcas-tip (linea ~909).
        st.markdown(
            f"<div class='ajcas-head' style='display:flex;font-size:9px;"
            f"color:{GRIS_TEXTO_SUAVE};"
            f"text-transform:uppercase;letter-spacing:.08em;font-weight:600;"
            f"padding:0 0 7px 0'>"
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
                                    f"<div style='font-size:9.5px;"
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
                                    f"<div style='font-size:11.5px;"
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
                                    f"text-align:right;font-size:11px;"
                                    f"font-weight:600;color:{_tcol};"
                                    f"font-variant-numeric:tabular-nums;"
                                    f"white-space:nowrap'>{_t}</div>"
                                    f"</div>")
                            return "".join(_filas_html)

                        def _header_split(txt, color, key):
                            """Título de la columna + su propio Top N, en la
                            misma fila — Faltantes y Sobrantes ya no
                            comparten un único selector.
                            class='ajcas-topn-label' en el título: sin ella
                            el título queda 8px MÁS ABAJO del centro real de
                            la fila (vertical_alignment="center" centra la
                            CAJA del stElementContainer, y esa caja mide 16px
                            menos de lo que el texto pinta — mismo bug que
                            arquitectura.md regla 33, el <div> raíz no tiene
                            <p> que absorba el margin-bottom:-16px nativo de
                            Streamlit). Se cancela ese margen apuntando a la
                            clase, igual que .ajcas-head."""
                            _hl, _hr = st.columns(
                                [1, 1], vertical_alignment="center")
                            with _hl:
                                st.markdown(
                                    f"<div class='ajcas-topn-label' "
                                    f"style='font-size:9px;font-weight:600;"
                                    f"color:{color};letter-spacing:.08em;"
                                    f"text-transform:uppercase'>{txt}</div>",
                                    unsafe_allow_html=True,
                                )
                            with _hr:
                                # format_func sin "Top": al lado del título
                                # ya dice Faltantes/Sobrantes, y sin cápsula
                                # alrededor "Top 5 Top 10 Top 20" se leía
                                # repetitivo — el número solo, separado por
                                # "·" (CSS ::before), alcanza. El label real
                                # ("Top") sigue viajando oculto para
                                # accesibilidad vía label_visibility.
                                return st.pills(
                                    "Top", [5, 10, 20], default=10, key=key,
                                    label_visibility="collapsed",
                                    format_func=lambda n: str(n),
                                ) or 10

                        _pa, _pb = st.columns(2)
                        with _pa:
                            _topn_neg = _header_split(
                                "Faltantes", AJUSTE_NEG_TEXTO,
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
                                st.markdown(_filas_split_html(_neg, AJUSTE_NEG),
                                           unsafe_allow_html=True)
                        with _pb:
                            _topn_pos = _header_split(
                                "Sobrantes", AJUSTE_POS_TEXTO,
                                "ajuste_cascada_topn_pos")
                            _pos = (_agg_dim[_agg_dim[col_ajuste_val] > 0]
                                    .nlargest(int(_topn_pos), col_ajuste_val)
                                    .sort_values(col_ajuste_val, ascending=False))
                            if _pos.empty:
                                st.caption("Sin sobrantes en esta familia.")
                            else:
                                st.markdown(_filas_split_html(_pos, AJUSTE_POS),
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

        # Sin leyenda al pie: los puntos Faltante/Sobrante eran redundantes
        # con el color de las barras y la columna Estado, y la nota de la
        # cascada acumulada pasó a ser el tooltip del título (.ajcas-tip).


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
                         col_producto=None, col_fecha=None, df_full=None,
                         col_valorizado=None):
    """Mapa de calor familia × área — modo Ajuste (signado, divergente) o
    Valorizado Total (siempre positivo, secuencial), elegido con un
    `st.pills` al tope del gráfico.

    Tres capas sobre el heatmap base — se combinan en el mismo trace / el
    mismo click-drill, no son gráficos aparte:
      · Totales al borde: fila/columna "TOTAL" agregadas al pivot como
        categorías extra con z=None (no participan del colorscale/_vmax:
        si entraran, un total podría superar a la celda individual más
        extrema y le robaría saturación al resto del mapa).
      · Top 3 resaltado: los 3 valores más fuertes de cada signo quedan a
        color (en modo Valorizado, sin negativos, son directamente los 3
        más altos); el resto de las celdas con dato se atenúa con un
        segundo trace Heatmap semitransparente encima (mismas categorías/
        xgap/ygap que el trace base -> calza celda a celda sin cuentas de
        píxeles).
      · Tendencia: el trace invisible de hover ya existía para el tooltip;
        ahora suma un sparkline de caracteres Unicode con los últimos
        cortes de `df_full` (hovertemplate sigue siendo texto plano, no
        hace falta JS). El click-drill, más rico, agrega un mini gráfico
        de líneas real en vez de pelear con el tooltip nativo.
    """
    if not col_familia or not col_area:
        st.info("Se necesitan columnas de familia y área para el mapa de calor.")
        return

    # ── Modo Ajuste Valorizado (signado) vs Valorizado Total (magnitud) —
    #    mismo heatmap, cambia la columna que se pivotea y todo lo que
    #    depende del signo más abajo (colorscale, franja TOTAL, leyenda
    #    móvil, drill). Sin col_valorizado en el df, ni se ofrece el
    #    selector: se comporta exactamente como antes. ─────────────────────
    _hay_valorizado = bool(col_valorizado and col_valorizado in df.columns)
    _modo_val = False
    if _hay_valorizado:
        _modo = st.pills(
            "Modo mapa de calor", ["Ajuste Valorizado", "Valorizado Total"],
            default="Ajuste Valorizado", key="hm_ajuste_modo",
            label_visibility="collapsed",
        ) or "Ajuste Valorizado"
        _modo_val = (_modo == "Valorizado Total")
    col_metrica = col_valorizado if _modo_val else col_ajuste_val

    pivot = df.pivot_table(
        index=col_familia, columns=col_area,
        values=col_metrica, aggfunc="sum", fill_value=0,
    )
    if pivot.empty:
        st.info("No hay datos para el mapa de calor en el rango seleccionado.")
        return
    _vmax = float(abs(pivot.values).max()) or 1.0
    _fams = pivot.index.tolist()
    _areas = pivot.columns.tolist()
    _n, _m = len(_fams), len(_areas)

    # ── Móvil: el heatmap NO se achica a como dé lugar (con 11 áreas + Total
    #    ilegible a cualquier tamaño de letra) — se renderiza a su ancho real
    #    y se scrollea, con la columna de familia fijada aparte en HTML (ver
    #    más abajo). Plotly dibuja en el servidor y no puede adaptarse al
    #    viewport real, así que la decisión se toma acá con el mismo
    #    _es_movil() que ya usa Compras para sus etiquetas de barra. ───────
    _movil = _es_movil()

    # ── Tamaño de fuente: en desktop se adapta al ancho (pocas áreas ->
    #    números grandes; las 11 reales -> se achica para no pisar la celda
    #    vecina). En móvil no hace falta adaptar nada -- cada columna ya
    #    tiene un ancho fijo generoso (ver _ancho_col_movil más abajo), así
    #    que el tamaño es plano. Mismo espíritu que la altura adaptada a _n
    #    más abajo. ───────────────────────────────────────────────────────
    if _movil:
        _cell_font, _tot_font, _grand_font = 11, 12, 12.5
    else:
        _cell_font = 12 if _m <= 6 else (11 if _m <= 9 else 9.5)
        _tot_font = _cell_font + 1
        _grand_font = _cell_font + 1.5

    # ── Top 3 por signo (mismo criterio que _badge_for en la Cascada: manda
    #    el valor absoluto) — decide qué celdas se resaltan y cuáles atenúa
    #    el trace de "apagado" de más abajo. ───────────────────────────────
    _celdas = [(i, j, float(pivot.values[i][j]))
               for i in range(_n) for j in range(_m)
               if abs(pivot.values[i][j]) >= 0.5]
    _top_pos = sorted((c for c in _celdas if c[2] > 0), key=lambda c: -c[2])[:3]
    _top_neg = sorted((c for c in _celdas if c[2] < 0), key=lambda c: c[2])[:3]
    _top_set = {(i, j) for i, j, _ in _top_pos + _top_neg}

    # ── Totales de fila/columna — mismo pivot, fuera de _vmax a propósito
    #    (ver docstring). ─────────────────────────────────────────────────
    _row_tot = pivot.sum(axis=1)
    _col_tot = pivot.sum(axis=0)
    _grand_tot = float(pivot.values.sum())

    # ── Tendencia por celda: últimos cortes de df_full (no solo el rango
    #    filtrado) — mismo espíritu que el delta de la Cascada, mirar más
    #    atrás que el rango activo para decir "cómo veníamos llegando". La
    #    columna de fecha ya está en el df (la usan Evolución y la tabla
    #    dinámica); esto es un groupby más, no una fuente de datos nueva.
    #    Acotado a 120 días hacia atrás para no pivotear el historial
    #    completo en cada rerun. ───────────────────────────────────────────
    _BLOQUES = "▁▂▃▄▅▆▇█"
    _N_CORTES = 7
    _spark_map = {}
    _piv_t = None
    if col_fecha and df_full is not None and col_fecha in df_full.columns:
        _dfe = df_full.copy()
        _dfe[col_fecha] = pd.to_datetime(_dfe[col_fecha], errors="coerce")
        _fmax = None
        if col_fecha in df.columns:
            _fserie = pd.to_datetime(df[col_fecha], errors="coerce").dropna()
            _fmax = _fserie.max() if not _fserie.empty else None
        if _fmax is not None:
            _dfe = _dfe[(_dfe[col_fecha] <= _fmax) &
                       (_dfe[col_fecha] >= _fmax - pd.Timedelta(days=120))]
        _dfe = _dfe.dropna(subset=[col_fecha, col_familia, col_area])
        if not _dfe.empty:
            _piv_t = _dfe.pivot_table(
                index=[col_familia, col_area], columns=col_fecha,
                values=col_metrica, aggfunc="sum", fill_value=0.0,
            )
            _cortes_cols = sorted(_piv_t.columns)[-_N_CORTES:]
            for _key in _piv_t.index:
                _vals = [float(_piv_t.loc[_key, c]) for c in _cortes_cols]
                if len(_vals) < 2:
                    continue
                _lo, _hi = min(_vals), max(_vals)
                _rng = (_hi - _lo) or 1.0
                _spark = "".join(
                    _BLOQUES[min(7, int((v - _lo) / _rng * 8))] for v in _vals
                )
                _flecha = "▲" if _vals[-1] >= _vals[-2] else "▼"
                _spark_map[_key] = (
                    f"<br>Tendencia ({len(_vals)} cortes): {_spark} {_flecha}"
                )

    # Título al pie del mapa. Uno solo para las dos vistas (escritorio usa
    # _card, móvil emite la clase a mano) para que no se despeguen.
    _TITULO_HM = "Mapa Valorizado Total" if _modo_val else "Mapa Ajuste Valorizado"

    # Separación entre celdas, en px. Es lo único que las despega entre sí, y
    # como se ve del color de plot_bgcolor (BLANCO), son LOS CANALES BLANCOS
    # que le dan aire a la grilla — la perilla para que respire más o menos.
    # Lo comparten el trace base y el de apagado: tienen que ser el mismo
    # número o el atenuado no calza con la celda que atenúa.
    _GAP = 6

    # ── z con borde "TOTAL" en None: mismo trace, la categoría extra al
    #    final de cada eje hace que Plotly le reserve un carril del mismo
    #    ancho que cualquier otra categoría — no hace falta un subplot
    #    aparte para alinear fila/columna de totales con la grilla. ───────
    _x_labels = _areas + ["TOTAL"]
    _y_labels = _fams + ["TOTAL"]
    _z_full = [row + [None] for row in pivot.values.tolist()]
    _z_full.append([None] * (_m + 1))

    # En móvil la colorbar se saca del gráfico (compite por un ancho que ya
    # es escaso) y se reemplaza por una leyenda HTML de 3 puntos, fija arriba
    # del área que se scrollea -- no tiene sentido que la referencia de color
    # se scrollee junto con los datos.
    # ── Colorscale: divergente centrada en cero para Ajuste (el signo
    #    importa: faltante/sobrante) vs secuencial anclada en cero para
    #    Valorizado Total (magnitud, nunca negativo) — ESCALA_CONTINUA es
    #    la misma escala que ya usan los mapas de calor de Compras
    #    (graficos/constructor.py) para "valor -> intensidad". ────────────
    if _modo_val:
        _colorscale_hm = ESCALA_CONTINUA
        _zmin_hm, _zmax_hm, _zmid_hm = 0.0, _vmax, None
        _colorbar_titulo = "Valorizado S/"
    else:
        _colorscale_hm = [
            [0.00, ERROR],
            [0.35, ERROR_FONDO],
            [0.50, LAVANDA_SELECCION],
            [0.65, EXITO_FONDO],
            [1.00, EXITO],
        ]
        _zmin_hm, _zmax_hm, _zmid_hm = -_vmax, _vmax, 0
        _colorbar_titulo = "Ajuste S/"

    fig = go.Figure(go.Heatmap(
        z=_z_full, x=_x_labels, y=_y_labels,
        xgap=_GAP, ygap=_GAP,
        colorscale=_colorscale_hm,
        zmin=_zmin_hm, zmax=_zmax_hm, zmid=_zmid_hm,
        showscale=not _movil,
        colorbar=dict(
            title=dict(text=_colorbar_titulo, font=dict(size=10,
                                                        color=GRIS_TEXTO)),
            tickformat=",.0f", tickfont=dict(size=9, color=GRIS_TEXTO_SUAVE),
            thickness=8, len=0.75, outlinewidth=0,
            ticks="outside", ticklen=3, tickcolor=GRIS_BORDE,
        ),
        hoverinfo="skip",
    ))

    # ── Trace de "apagado": Heatmap semitransparente encima de las celdas
    #    con dato que NO están en el top 3 — mismas categorías/gaps que el
    #    trace base (comparten eje -> Plotly las alinea por el nombre de la
    #    categoría, no hace falta calcular píxeles). Top 3 y celdas vacías
    #    quedan en None, sin tocar. Color lavanda (no gris plano) porque es
    #    el tono de "apagado" de la marca, el mismo que LAVANDA_FONDO/
    #    SELECCION, y no un gris genérico de planilla. Va semitransparente
    #    sobre el BLANCO del fondo, así que la celda atenuada sigue dejando
    #    ver de qué signo era. ───────────────────────────────────────────
    _z_dim = [[None] * _m for _ in range(_n)]
    for _i, _j, _v in _celdas:
        if (_i, _j) not in _top_set:
            _z_dim[_i][_j] = 1
    fig.add_trace(go.Heatmap(
        # MISMO _GAP que el trace base: si no coinciden, el rectangulo de
        # apagado no calza con la celda que atenua y se derrama sobre los
        # canales blancos.
        z=_z_dim, x=_areas, y=_fams, xgap=_GAP, ygap=_GAP,
        zmin=0, zmax=1,
        colorscale=[[0, "rgba(240,237,254,.8)"], [1, "rgba(240,237,254,.8)"]],
        showscale=False, hoverinfo="skip",
    ))

    _pts_x, _pts_y, _pts_cd = [], [], []
    for _i, _fam in enumerate(_fams):
        for _j, _area in enumerate(_areas):
            _val = float(pivot.values[_i][_j])
            _pts_x.append(_area)
            _pts_y.append(_fam)
            _pts_cd.append([_val, _spark_map.get((_fam, _area), "")])

    _hover_lbl = "Valorizado" if _modo_val else "Ajuste"
    fig.add_trace(go.Scatter(
        x=_pts_x, y=_pts_y, mode="markers",
        marker=dict(size=28, opacity=0, color=ACENTO),
        customdata=_pts_cd,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Área: <b>%{x}</b><br>"
            + _hover_lbl + ": <b>S/ %{customdata[0]:,.2f}</b>"
            "%{customdata[1]}"
            "<extra></extra>"
        ),
        showlegend=False,
    ))

    # ── Anotaciones de celdas con dato: top 3 a full color (blanco si el
    #    fondo queda oscuro), el resto en gris — el trace de apagado ya
    #    bajó el fondo, el texto tiene que acompañar o queda un número
    #    nítido sobre un fondo apagado (contradice el gesto). ─────────────
    _anns_hm = []
    for _i, _fam in enumerate(_fams):
        for _j, _area in enumerate(_areas):
            _v = float(pivot.values[_i][_j])
            if abs(_v) < 0.5:
                continue
            if (_i, _j) in _top_set:
                _int = abs(_v) / _vmax
                _fg = BLANCO if _int > 0.55 else GRIS_TEXTO_MEDIO
            else:
                _fg = GRIS_TEXTO_SUAVE
            _anns_hm.append(dict(
                x=_area, y=_fam, xref="x", yref="y",
                text=f"S/ {_v:,.0f}", showarrow=False,
                font=dict(size=_cell_font, color=_fg,
                          family="ui-monospace, monospace"),
            ))

    # ── Fila/columna TOTAL: negrita (el mini-lenguaje de anotaciones de
    #    Plotly soporta <b>) + una línea divisoria fina que las separa de
    #    los datos reales, sin decorar celda por celda. En modo Valorizado
    #    el total es casi siempre positivo — el semáforo rojo/verde ahí
    #    leería como "bueno/malo" cuando es solo una magnitud, así que ese
    #    modo usa el índigo de las cabeceras de grupo en su lugar. ────────
    def _color_total_hm(v):
        if _modo_val:
            return ACENTO_TEXTO_OSCURO
        return DANGER_TEXT if v < 0 else CELDA_POS_TEXTO

    for _i, _fam in enumerate(_fams):
        _v = float(_row_tot.iloc[_i])
        _anns_hm.append(dict(
            x="TOTAL", y=_fam, xref="x", yref="y",
            text=f"<b>S/ {_v:,.0f}</b>", showarrow=False,
            font=dict(size=_tot_font, color=_color_total_hm(_v), family="ui-monospace, monospace"),
        ))
    for _j, _area in enumerate(_areas):
        _v = float(_col_tot.iloc[_j])
        _anns_hm.append(dict(
            x=_area, y="TOTAL", xref="x", yref="y",
            text=f"<b>S/ {_v:,.0f}</b>", showarrow=False,
            font=dict(size=_tot_font, color=_color_total_hm(_v), family="ui-monospace, monospace"),
        ))
    _anns_hm.append(dict(
        x="TOTAL", y="TOTAL", xref="x", yref="y",
        text=f"<b>S/ {_grand_tot:,.0f}</b>", showarrow=False,
        font=dict(size=_grand_font, color=_color_total_hm(_grand_tot), family="ui-monospace, monospace"),
    ))

    # ── Filas/columnas fijas en px para móvil (_ROWPX/_TOPM/_BOTM/_COLPX) --
    # nombradas acá porque la columna de familia "aparte" (HTML, sticky) que
    # se arma más abajo tiene que calzar EXACTO con la altura de fila que ve
    # Plotly: mismo _ROWPX en los dos lados, sin el clamp min/max que usa el
    # alto de escritorio (con ese clamp una grilla chica dejaría de medir
    # _ROWPX por fila y la columna HTML se desalinearía). ────────────────────
    _ROWPX, _TOPM, _BOTM, _COLPX = 40, 50, 18, 64
    if _movil:
        # -16: medido en vivo con getBoundingClientRect(). El área de
        # trazado real (el rect de fondo del heatmap) sale 16px más alta
        # que "height - margin.t - margin.b" -- Plotly no respeta el
        # margen pedido al pixel (con t=50/b=18 el rect de fondo arrancaba
        # en y=42 y medía 16px más de lo esperado), y esos 16px "de más" se
        # reparten estirando las categorías existentes en vez de sumar una
        # fila -- por eso la fila TOTAL quedaba cada vez más lejos de su
        # label en HTML a medida que crecía el número de familias. Restar
        # acá compensa exactamente eso: con la resta, el rect de fondo mide
        # (_n+1)*_ROWPX de punta a punta, fila por fila, sin dato de por
        # medio. Si algún día cambia _layout_aj o la versión de Plotly,
        # volver a medir (no asumir que sigue siendo 16).
        _alto = (_n + 1) * _ROWPX + _TOPM + _BOTM - 16
        _ancho = (_m + 1) * _COLPX + 12
    else:
        _alto = min(560, max(240, (_n + 1) * 38 + 110))
        _ancho = None  # use_container_width=True gobierna el ancho

    fig.update_layout(**_layout_aj(
        title_text="",
        xaxis=dict(tickangle=0, side="top", gridcolor=GRIS_BORDE,
                   showgrid=False, ticks="",
                   tickfont=dict(size=11 if not _movil else 10.5, color=GRIS_TEXTO)),
        yaxis=dict(autorange="reversed", gridcolor=GRIS_BORDE,
                   showgrid=False, ticks="", showticklabels=not _movil,
                   tickfont=dict(size=11, color=GRIS_TEXTO_MEDIO)),
        width=_ancho,
        height=_alto,
        margin=dict(l=(10 if not _movil else 6), r=(10 if not _movil else 6),
                    t=_TOPM, b=_BOTM),
        annotations=_anns_hm,
        hovermode="closest",
    ))
    # plot_bgcolor BLANCO: es lo que se asoma por los xgap/ygap, o sea el
    # color de los canales entre celdas y del hueco donde no hay dato.
    #
    # Estuvo en LAVANDA_FONDO por marca, pero con las celdas ya tenidas de
    # lavanda (el 0.50 de la colorscale) y el trace de apagado tambien
    # lavanda, el conjunto quedaba lavanda sobre lavanda sobre lavanda: sin
    # un tono neutro que corte, la grilla se apelmazaba y se leia manchada.
    # El blanco NO es "menos marca": es lo que deja respirar al lavanda para
    # que se lea como color, y de paso hace resaltar la franja de totales.
    fig.update_layout(plot_bgcolor=BLANCO)
    # ── Franja de TOTALES ────────────────────────────────────────────────
    # Antes la fila/columna TOTAL solo se distinguía por una línea gris de
    # 1.5px: se leía como una celda más de la grilla. Ahora llevan fondo
    # propio en LAVANDA_CABECERA_GRUPO — el MISMO tono que la fila de
    # totales de la tabla AgGrid (tablas/desktop.py) — para que las dos
    # vistas del reporte hablen el mismo idioma visual, y un borde de
    # ACENTO como el de allá.
    #
    # El "espacio" sale del inset de 0.06 de categoría: la franja arranca
    # en _m-0.44 en vez de _m-0.5, así que entre el último dato y los
    # totales se asoma el plot_bgcolor como canaleta. Se hace con inset y
    # NO agregando una categoría vacía al eje, porque las anotaciones y el
    # trace de apagado indexan por posición de categoría — una categoría
    # fantasma correría todos esos índices.
    #
    # layer="below" las deja por debajo de los traces; las celdas TOTAL
    # tienen z=None, así que no hay nada del heatmap que las tape.
    _INSET = 0.44
    for _ejes, _pos in (
        (dict(xref="x", yref="paper"),
         dict(x0=_m - _INSET, x1=_m + 0.5, y0=0, y1=1)),
        (dict(xref="paper", yref="y"),
         dict(x0=0, x1=1, y0=_n - _INSET, y1=_n + 0.5)),
    ):
        fig.add_shape(type="rect", **_ejes, **_pos,
                      fillcolor=LAVANDA_CABECERA_GRUPO,
                      line=dict(width=0), layer="below")
    # Borde de acento en el canto de la franja (no en _m-0.5: va pegado a
    # la franja para que la canaleta quede del lado de los datos).
    fig.add_shape(type="line", xref="x", yref="paper",
                  x0=_m - _INSET, x1=_m - _INSET, y0=0, y1=1,
                  line=dict(color=ACENTO, width=2))
    fig.add_shape(type="line", xref="paper", yref="y",
                  x0=0, x1=1, y0=_n - _INSET, y1=_n - _INSET,
                  line=dict(color=ACENTO, width=2))
    # Anillo de foco en las celdas del top 3 — el trace de apagado bajó el
    # resto, esto hace que las que quedan arriba salten a la vista. En modo
    # Valorizado todas son positivas (no hay "top_neg"): el anillo va en el
    # acento de marca en vez del semáforo rojo/verde de Ajuste.
    for _i, _j, _v in _top_pos + _top_neg:
        _color_anillo = ACENTO if _modo_val else (EXITO if _v > 0 else ERROR)
        fig.add_shape(
            type="rect", xref="x", yref="y",
            x0=_j - 0.47, x1=_j + 0.47, y0=_i - 0.47, y1=_i + 0.47,
            line=dict(color=_color_anillo, width=2),
            fillcolor="rgba(0,0,0,0)", layer="above",
        )
    _xcats = [str(c) for c in _x_labels]
    fig.update_xaxes(tickmode="array", tickvals=_xcats,
                     ticktext=_wrap_cat(_xcats))
    if _movil:
        # automargin=True (forzado por graficos.base._layout para TODOS los
        # gráficos) recalcula el margen superior según el contenido real de
        # las etiquetas del eje X -- exactamente lo que NO puede pasar acá:
        # la columna de familia en HTML de más abajo asume un _TOPM/_ROWPX
        # fijos para calzar fila a fila con el heatmap. Con automargin
        # prendido, medido en vivo, el área de trazado terminaba 16px más
        # alta de lo esperado y la columna HTML se desalineaba de la fila
        # TOTAL para abajo. Se apaga SOLO en móvil (desktop no depende de
        # una alineación externa, así que conserva el comportamiento ya
        # probado) -- va DESPUÉS de _layout_aj porque esa función lo fuerza
        # a True incondicionalmente.
        fig.update_xaxes(automargin=False)

    # ── Bordes redondeados en TODO el mapa de calor (pedido 2026-08-07) ──
    # go.Heatmap no tiene un cornerradius como go.Bar, así que se redondea
    # por CSS en dos puntos del SVG que arma Plotly -- ambos son clases
    # FIJAS (el id numérico que las acompaña cambia en cada render, por eso
    # no se usa):
    #   · clipPath.plotclip -- el rect que recorta la imagen de datos
    #     (celdas + puntos de hover) al área de trazado. Redondearlo
    #     redondea las celdas mismas, no solo lo que se ve detrás.
    #   · .bglayer rect.bg -- el rect de plot_bgcolor que se asoma por los
    #     xgap/ygap entre celdas. Va con radio +8px (mismo margen que deja
    #     Plotly entre bg y plotclip, medido en vivo) para que los dos
    #     bordes queden concéntricos en vez de que el de afuera asome una
    #     esquina cuadrada detrás del redondeado de adentro.
    # Acotado a .st-key-heatmap_ajuste: "plotclip"/"bg" son clases
    # genéricas de Plotly y sin el prefijo redondearía TODOS los gráficos
    # de la app (misma regla que el resto del CSS del proyecto: acotar al
    # widget, nunca colgar del contenedor global).
    st.markdown("""<style>
    .st-key-heatmap_ajuste clipPath.plotclip rect {
        rx: 14px; ry: 14px;
    }
    .st-key-heatmap_ajuste .bglayer rect.bg {
        rx: 22px; ry: 22px;
    }
    </style>""", unsafe_allow_html=True)

    if _movil:
        # ── Columna de familia "aparte", en HTML, fija a la izquierda del
        #    contenedor que se scrollea horizontalmente. Plotly no tiene
        #    equivalente a position:sticky DENTRO de un mismo SVG -- no hay
        #    forma de dejar una franja fija mientras el resto del gráfico
        #    se desliza -- así que la columna de nombres se saca del
        #    heatmap (yaxis.showticklabels=False más arriba) y se arma acá
        #    al lado, calzada fila a fila con el mismo _ROWPX/_TOPM que usa
        #    el layout del gráfico. Si alguno de los dos cambia, el otro
        #    tiene que cambiar junto (por eso comparten las constantes en
        #    vez de números sueltos a cada lado). ─────────────────────────
        _ANCHO_LABELS = 84
        # -8px: medido en vivo con getBoundingClientRect() -- el bloque de
        # markdown de la columna de labels arranca 8px más abajo que el rect
        # de fondo del heatmap aunque los dos sean flex items hermanos con
        # align-items:flex-start (differencia de padding/margin nativo entre
        # stMarkdownContainer y el elemento de Plotly). Sin este ajuste, la
        # primera fila de nombres queda corrida respecto a la primera fila
        # de datos y el desfase se arrastra fila a fila.
        _rows_html = f"<div style='height:{_TOPM - 8}px'></div>"
        for _fam in _fams:
            _rows_html += (
                f"<div style='height:{_ROWPX}px;display:flex;"
                f"align-items:center;justify-content:flex-end;"
                f"padding-right:7px;font-size:10.5px;font-weight:500;"
                f"color:{GRIS_TEXTO_MEDIO};white-space:nowrap;"
                f"overflow:hidden;text-overflow:ellipsis'>{_fam}</div>"
            )
        # La etiqueta TOTAL lleva el MISMO fondo y borde que la franja de
        # totales del heatmap (ver la seccion "Franja de TOTALES"): en movil
        # esta columna es HTML aparte del grafico, asi que sin esto la franja
        # se cortaria justo donde empieza el nombre de la fila.
        _rows_html += (
            f"<div style='height:{_ROWPX}px;display:flex;"
            f"align-items:center;justify-content:flex-end;"
            f"padding-right:7px;font-size:11px;font-weight:700;"
            f"background:{LAVANDA_CABECERA_GRUPO};"
            f"border-top:2px solid {ACENTO};"
            f"color:{ACENTO_TEXTO_OSCURO}'>TOTAL</div>"
        )

        # El sticky va en el ANCESTRO stElementContainer del markdown (vía
        # :has(), no en la propia key) -- mismo motivo que el sticky header
        # de _graf_pivote_fecha_ajuste (arquitectura.md regla #25): puesto
        # directo en el div con key no engancha con el scroll.
        st.markdown(f"""<style>
        .st-key-hm_movil_scroll {{
            display: flex !important;
            flex-direction: row !important;
            align-items: flex-start !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            padding-bottom: 4px;
        }}
        div[data-testid="stElementContainer"]:has(.hm-movil-labels) {{
            position: sticky !important;
            left: 0 !important;
            z-index: 3 !important;
            flex: 0 0 auto !important;
            width: {_ANCHO_LABELS}px !important;
            background: {BLANCO} !important;
            box-shadow: 3px 0 6px -3px rgba(24,24,29,.12);
        }}
        .st-key-hm_movil_scroll .st-key-heatmap_ajuste {{
            flex: 0 0 auto !important;
            width: auto !important;
        }}
        </style>""", unsafe_allow_html=True)

        # Leyenda de signo (Faltante/Sobrante) solo tiene sentido en modo
        # Ajuste — en Valorizado Total todas las celdas son positivas.
        _leyenda_signo = "" if _modo_val else (
            f"<div style='display:flex;gap:12px;font-size:9.5px;"
            f"color:{GRIS_TEXTO};margin-bottom:8px'>"
            f"<span><span style='display:inline-block;width:8px;"
            f"height:8px;border-radius:2px;background:{ERROR};"
            f"margin-right:4px;vertical-align:-1px'></span>Faltante</span>"
            f"<span><span style='display:inline-block;width:8px;"
            f"height:8px;border-radius:2px;background:{EXITO};"
            f"margin-right:4px;vertical-align:-1px'></span>Sobrante</span>"
            f"</div>"
        )
        with _card("heatmap"):
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:5px;"
                f"font-size:10.5px;font-weight:600;"
                f"color:{ACENTO_TEXTO_OSCURO};margin-bottom:6px'>"
                f"Deslizá para ver las {_m} áreas &rarr;</div>"
                + _leyenda_signo,
                unsafe_allow_html=True,
            )
            with st.container(key="hm_movil_scroll"):
                st.markdown(f"<div class='hm-movil-labels'>{_rows_html}</div>",
                           unsafe_allow_html=True)
                _hm_evt = st.plotly_chart(
                    fig, use_container_width=False,
                    key="heatmap_ajuste",
                    on_select="rerun", selection_mode="points",
                    config={
                        "displayModeBar": True, "displaylogo": False,
                        "modeBarButtonsToRemove": [
                            "zoom2d", "pan2d", "select2d", "lasso2d",
                            "zoomIn2d", "zoomOut2d", "autoScale2d",
                            "resetScale2d", "toImage",
                        ],
                    },
                )
            # Mismo título al pie que en escritorio. Móvil no usa _card, así
            # que se emite la MISMA clase a mano para que se vean igual.
            st.markdown(f'<p class="chart-card-pie">{_TITULO_HM}</p>',
                        unsafe_allow_html=True)
    else:
        # El título va al PIE (default de _card): antes acá había un
        # st.caption explicando el resalte y la fila TOTAL. Se saca por
        # pedido -- el gráfico se explica solo y el texto largo competía
        # con la grilla.
        with _card("heatmap", _TITULO_HM):
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
        if _fam_sel == "TOTAL" or _area_sel == "TOTAL":
            # Clic en la fila/columna resumen: no es una combinación real
            # de familia × área, no hay detalle de producto que mostrar.
            _fam_sel = _area_sel = None
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

            _color_total = (ACENTO_TEXTO_OSCURO if _modo_val else
                           (DANGER_TEXT if (_val_sel or 0) < 0
                            else CELDA_POS_TEXTO))
            st.markdown(
                f"**{_fam_sel}** × **{_area_sel}** · "
                f"<span style='color:{_color_total};font-weight:600'>"
                f"S/ {(_val_sel or 0):,.0f}</span> · "
                f"{len(_det)} registros",
                unsafe_allow_html=True,
            )

            # ── Tendencia real (línea Plotly, no el sparkline de texto del
            #    hover) — reusa el _piv_t ya calculado arriba, sin volver a
            #    consultar df_full. Se omite si hay menos de 2 cortes o si
            #    la combinación no aparece en el historial (p. ej. recién
            #    empezó a tener ajustes esta semana). ───────────────────
            if _piv_t is not None:
                try:
                    _serie = _piv_t.loc[(_fam_sel, _area_sel)].sort_index()
                except KeyError:
                    _serie = None
                if _serie is not None and len(_serie) >= 2:
                    _serie = _serie.iloc[-24:]
                    _fig_t = go.Figure(go.Scatter(
                        x=_serie.index, y=_serie.values,
                        mode="lines+markers",
                        line=dict(color=ACENTO, width=2),
                        marker=dict(size=5),
                        fill="tozeroy", fillcolor="rgba(108,92,231,0.08)",
                        hovertemplate="%{x|%d/%m}<br>S/ %{y:,.0f}<extra></extra>",
                    ))
                    _fig_t.add_hline(y=0, line_dash="dot",
                                     line_color=GRIS_BORDE, line_width=1)
                    _fig_t.update_layout(
                        height=90, margin=dict(l=4, r=4, t=4, b=18),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        xaxis=dict(showgrid=False,
                                  tickfont=dict(size=8.5, color=GRIS_TEXTO_SUAVE)),
                        yaxis=dict(visible=False),
                    )
                    st.plotly_chart(_fig_t, use_container_width=True,
                                    config={"displayModeBar": False},
                                    key=f"hm_trend_{_slug(str(_fam_sel))}_"
                                        f"{_slug(str(_area_sel))}")

            if col_producto and col_producto in _det.columns:
                _topn = st.pills(
                    "Top", [5, 10, 20], default=10,
                    key="hm_drill_topn",
                    label_visibility="collapsed",
                    format_func=lambda n: f"Top {n}",
                ) or 10

                _sub_prod = (
                    _det.groupby(col_producto, as_index=False)[col_metrica]
                    .sum()
                )
                _sub_prod["_abs"] = _sub_prod[col_metrica].abs()
                _sub_prod = _sub_prod.sort_values(
                    "_abs", ascending=False).head(int(_topn))

                def _filas_drill_html(_df_d, _color_bar):
                    """Mini barras de progreso (riel + relleno) — mismo
                    patron que la columna Cascada acumulada, en vez de un
                    grafico Plotly de barras gruesas."""
                    if _df_d.empty:
                        return ""
                    _max_abs = float(
                        _df_d[col_metrica].abs().max()) or 1.0
                    _filas_html = []
                    for _, _r in _df_d.iterrows():
                        _nom = str(_r[col_producto])
                        if len(_nom) > 32:
                            _nom = _nom[:31] + "…"
                        _pct = max(
                            abs(float(_r[col_metrica])) / _max_abs * 100,
                            3)
                        _tcol = (ACENTO_TEXTO_OSCURO if _modo_val else
                                 (DANGER_TEXT if _r[col_metrica] < 0
                                  else CELDA_POS_TEXTO))
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
                            f"S/ {_r[col_metrica]:,.0f}</div></div>")
                    return "".join(_filas_html)

                if _modo_val:
                    # Sin signo que separar: un solo ranking, no el split
                    # Faltantes/Sobrantes de más abajo.
                    st.markdown(
                        f"<div style='font-size:9px;font-weight:600;"
                        f"color:{ACENTO_TEXTO_OSCURO};letter-spacing:.08em;"
                        f"text-transform:uppercase;margin:4px 0 -8px 0'>"
                        f"Top productos</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(_filas_drill_html(_sub_prod, ACENTO),
                               unsafe_allow_html=True)
                else:
                    # ascending: True para negativos (el mas negativo primero
                    # -> arriba en el HTML), False para positivos (el mayor
                    # primero) -- el HTML renderiza top-a-bottom en el orden
                    # del DataFrame, al reves de como Plotly ubicaba las
                    # categorias en un bar horizontal.
                    _neg = _sub_prod[_sub_prod[col_metrica] < 0].sort_values(
                        col_metrica, ascending=True)
                    _pos = _sub_prod[_sub_prod[col_metrica] > 0].sort_values(
                        col_metrica, ascending=False)

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


def _graf_distribucion_ajuste(df, col_familia, col_area, col_ajuste_val, col_producto,
                              col_codigo=None, col_cantidad=None, col_fecha=None,
                              col_unidad=None):
    """Strip plot coloreado (faltante/sobrante) + histograma, ambos excluyendo
    los ajustes en cero.

    Con >50% de productos en S/ 0 (lo normal en un inventario), un boxplot
    colapsa q1=mediana=q3 en una línea invisible y solo deja ver puntos
    sueltos sin caja, y un histograma amontona todo en un pico que tapa las
    líneas de media/mediana/cero. Filtrar el cero antes de graficar es lo
    que deja ver la distribución real; el conteo de productos sin ajuste se
    muestra aparte como texto, no se pierde.

    Con `col_producto` resuelto, el hover se enriquece (vía `custom_data`)
    con código/área/cantidad/fecha, y clic + selección (caja o lazo, barra
    del gráfico) arma una tabla de detalle abajo — mismo patrón
    `on_select="rerun"` que ya usa `_graf_comparativa_mensual`. La key del
    chart es estática a propósito: la selección solo pinta la tabla de
    abajo, no realimenta el propio gráfico, así que no aplica la trampa de
    key dinámica de arquitectura.md (selección con toggle infinito).

    El histograma (derecha) tiene el mismo click→tabla, pero SIN
    custom_data sobre el propio `go.Histogram`: es una traza agregada
    (barras = bins, no filas) y `on_select` sobre ella es territorio no
    verificado — mismo riesgo que `go.Heatmap` (regla #11 de
    arquitectura.md, selección que nunca llega, sin error). Se reutiliza
    esa solución: overlay de `go.Scatter` invisible (opacity=0), un punto
    por bin a media altura, con el rango `[lo, hi]` de ese bin en
    `customdata`. El click/drag selecciona el punto invisible, no la
    barra; el rango de su customdata filtra `df_nz` directo en pandas."""
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
        _es_strip = bool(grp and grp in df_nz.columns)
        _hay_prod = _es_strip and bool(col_producto and col_producto in df_nz.columns)

        if _es_strip:
            d = df_nz.copy()
            d["_signo"] = d[col_ajuste_val].lt(0).map(
                {True: "Faltante", False: "Sobrante"})

            _cd_cols = None
            if _hay_prod:
                def _col_o_vacia(col):
                    return (d[col].astype(str) if (col and col in d.columns)
                            else pd.Series([""] * len(d), index=d.index))

                d["_hover_prod"] = _col_o_vacia(col_producto)
                d["_hover_cod"] = _col_o_vacia(col_codigo)
                d["_hover_area"] = _col_o_vacia(col_area)
                d["_hover_cant"] = (d[col_cantidad] if
                                    (col_cantidad and col_cantidad in d.columns)
                                    else float("nan"))
                d["_hover_um"] = (
                    " " + d[col_unidad].fillna("").astype(str)
                    if (col_unidad and col_unidad in d.columns) else "")
                if col_fecha and col_fecha in d.columns:
                    _fecha_dt = pd.to_datetime(d[col_fecha], errors="coerce")
                    d["_hover_fecha"] = _fecha_dt.map(
                        lambda x: _fmt_corte(x) if pd.notna(x) else "")
                else:
                    d["_hover_fecha"] = ""
                _cd_cols = ["_hover_prod", "_hover_cod", "_hover_area",
                           "_hover_cant", "_hover_um", "_hover_fecha"]

            fig = px.strip(
                d, x=grp, y=col_ajuste_val, color="_signo",
                color_discrete_map={"Faltante": ERROR, "Sobrante": EXITO},
                title=f"Distribución del ajuste por {grp}",
                labels={col_ajuste_val: "Ajuste S/", grp: "", "_signo": ""},
                custom_data=_cd_cols,
            )
            fig.add_hline(y=0, line_dash="dot", line_color=GRIS_TEXTO_SUAVE,
                          annotation_text="Cero", annotation_position="top right")
            fig.update_layout(**_layout_aj(
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1, title=None),
                xaxis=dict(tickangle=-30, gridcolor=GRIS_BORDE),
                yaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
            ))
            if _hay_prod:
                _linea_ajuste = "Ajuste: <b>S/ %{y:,.2f}</b>"
                if col_cantidad and col_cantidad in d.columns:
                    _linea_ajuste += " (%{customdata[3]:+.1f}%{customdata[4]})"
                _hovertemplate = "<br>".join([
                    "<b>%{customdata[0]}</b>",
                    "%{customdata[1]} · %{x} · %{customdata[2]}",
                    _linea_ajuste,
                    "Corte: %{customdata[5]}",
                ]) + "<extra></extra>"
            else:
                _hovertemplate = "%{x}<br>S/ %{y:,.2f}<extra></extra>"
            fig.update_traces(marker=dict(size=7), hovertemplate=_hovertemplate)
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
            _evento_dist = st.plotly_chart(
                fig, use_container_width=True, key="ajuste_dist_strip",
                on_select="rerun" if _hay_prod else "ignore",
                selection_mode=["points", "box", "lasso"],
            )

        if _hay_prod:
            _puntos = ((_evento_dist or {}).get("selection", {}) or {}).get("points", [])
            if _puntos:
                _filas = []
                for _p in _puntos:
                    _cd = _p.get("customdata") or []
                    _filas.append({
                        "Producto": _cd[0] if len(_cd) > 0 else "",
                        grp: _p.get("x"),
                        "Ajuste S/": _p.get("y"),
                        "Cantidad": _cd[3] if len(_cd) > 3 else None,
                        "Corte": _cd[5] if len(_cd) > 5 else "",
                    })
                _det = pd.DataFrame(_filas).sort_values("Ajuste S/")
                _total = float(_det["Ajuste S/"].sum())
                st.caption(f"{len(_det)} seleccionados · ajuste neto S/ {_total:,.2f}")
                _det_fmt = _det.copy()
                _det_fmt["Ajuste S/"] = _det_fmt["Ajuste S/"].map(
                    lambda v: f"S/ {v:,.2f}")
                st.dataframe(_det_fmt, hide_index=True, use_container_width=True)

    with col_der:
        media   = float(df_nz[col_ajuste_val].mean())
        mediana = float(df_nz[col_ajuste_val].median())

        # Uno o dos ajustes puntuales muy grandes estiran el eje y aplastan
        # el grueso de la distribución (que vive cerca de cero) en 1-2
        # barras. Se acota la vista al percentil 1-99 (ampliado si hiciera
        # falta para no dejar fuera a la media o la mediana) y esos outliers
        # se cuentan aparte como texto — mismo criterio que el conteo de cero.
        p_lo, p_hi = df_nz[col_ajuste_val].quantile([0.01, 0.99])
        p_lo = min(p_lo, media, mediana, 0.0)
        p_hi = max(p_hi, media, mediana, 0.0)
        if p_hi <= p_lo:
            p_hi = p_lo + 1.0
        d_hist = df_nz[df_nz[col_ajuste_val].between(p_lo, p_hi)]
        n_fuera = n_nz - len(d_hist)

        _cap = f"{n_total - n_nz} productos en cero, excluidos del cálculo"
        if n_fuera:
            _cap += f" · {n_fuera} outliers fuera de este rango"
        st.caption(_cap)

        _hay_prod_hist = bool(col_producto and col_producto in df_nz.columns)
        _n_bins = 30
        _paso = (p_hi - p_lo) / _n_bins
        _bordes = [p_lo + i * _paso for i in range(_n_bins + 1)]

        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=d_hist[col_ajuste_val],
            xbins=dict(start=p_lo, end=p_hi, size=_paso),
            name="Frecuencia",
            marker_color=SERIE_PRINCIPAL, opacity=0.75,
            hovertemplate="Valor: S/ %{x:,.2f}<br>Frecuencia: %{y}<extra></extra>",
        ))
        if _hay_prod_hist:
            _bins_cat = pd.cut(d_hist[col_ajuste_val], bins=_bordes,
                               include_lowest=True)
            _conteo = (_bins_cat.value_counts(sort=False)
                       .reindex(_bins_cat.cat.categories, fill_value=0))
            fig2.add_trace(go.Scatter(
                x=[iv.mid for iv in _conteo.index],
                y=[c / 2 for c in _conteo.to_numpy()],
                mode="markers", marker=dict(size=20, opacity=0),
                customdata=[(iv.left, iv.right) for iv in _conteo.index],
                hoverinfo="skip", showlegend=False,
            ))
        fig2.add_vline(x=0, line_dash="solid", line_color=ERROR, line_width=2)
        fig2.add_vline(x=media, line_dash="dot", line_color=ADVERTENCIA, line_width=2)
        fig2.add_vline(x=mediana, line_dash="dash", line_color=EXITO, line_width=2)
        fig2.update_layout(**_layout_aj(
            title="Histograma de frecuencias",
            xaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE,
                       title="Ajuste Valorizado", range=[p_lo, p_hi]),
            yaxis=dict(title="Frecuencia", gridcolor=GRIS_BORDE),
            hovermode="closest",
            showlegend=False,
        ))
        with _card("dist_hist", "Histograma"):
            st.markdown(
                f"<div style='display:flex;gap:16px;font-size:11px;"
                f"font-weight:600;margin:0 0 4px 2px'>"
                f"<span style='color:{ERROR}'>● Cero</span>"
                f"<span style='color:{ADVERTENCIA}'>● Media S/ {media:,.0f}</span>"
                f"<span style='color:{EXITO}'>● Mediana S/ {mediana:,.0f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            _evento_hist = st.plotly_chart(
                fig2, use_container_width=True, key="ajuste_dist_hist",
                on_select="rerun" if _hay_prod_hist else "ignore",
                selection_mode=["points", "box"],
            )

        if _hay_prod_hist:
            _puntos_hist = ((_evento_hist or {}).get("selection", {}) or {}).get("points", [])
            _mask = pd.Series(False, index=df_nz.index)
            for _p in _puntos_hist:
                _cd = _p.get("customdata") or []
                if len(_cd) == 2:
                    _mask |= df_nz[col_ajuste_val].between(_cd[0], _cd[1])
            _sel_hist = df_nz[_mask]
            if not _sel_hist.empty:
                _det2 = pd.DataFrame({"Producto": _sel_hist[col_producto]})
                if grp and grp in _sel_hist.columns:
                    _det2[grp] = _sel_hist[grp]
                _det2["Ajuste S/"] = _sel_hist[col_ajuste_val]
                if col_cantidad and col_cantidad in _sel_hist.columns:
                    _det2["Cantidad"] = _sel_hist[col_cantidad]
                if col_fecha and col_fecha in _sel_hist.columns:
                    _fecha_dt2 = pd.to_datetime(_sel_hist[col_fecha], errors="coerce")
                    _det2["Corte"] = _fecha_dt2.map(
                        lambda x: _fmt_corte(x) if pd.notna(x) else "")
                _det2 = _det2.sort_values("Ajuste S/")
                _total2 = float(_det2["Ajuste S/"].sum())
                st.caption(f"{len(_det2)} seleccionados · ajuste neto S/ {_total2:,.2f}")
                _det2_fmt = _det2.copy()
                _det2_fmt["Ajuste S/"] = _det2_fmt["Ajuste S/"].map(
                    lambda v: f"S/ {v:,.2f}")
                st.dataframe(_det2_fmt, hide_index=True, use_container_width=True)

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
    col_codigo     = _resolver(df_f, ["CODIGO PRODUCTO", "Codigo Producto", "COD PRODUCTO"])
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
                                 col_producto=col_producto,
                                 col_fecha=col_fecha, df_full=df_full,
                                 col_valorizado=col_valorizado)
        elif graf == "Distribución":
            _graf_distribucion_ajuste(d, col_familia, col_area,
                                      col_ajuste_val, col_producto,
                                      col_codigo=col_codigo,
                                      col_cantidad=col_cantidad,
                                      col_fecha=col_fecha,
                                      col_unidad=col_unidad)
        elif graf == "Por fecha de corte":
            _graf_pivote_fecha_ajuste(d, col_familia, col_ajuste_val,
                                      col_producto, col_cantidad, col_fecha)

    _card_der = st.container(
        border=True, key=f"ajuste_graf_card_der_{_slug(ambito)}",
    )
    with _card_der:
        _panel_analisis_ajuste(
            d, col_familia, col_area, col_ajuste_val,
            col_producto, col_valorizado, col_cantidad, ambito,
        )
