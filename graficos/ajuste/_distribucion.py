"""graficos.ajuste._distribucion - vista Distribucion.

Caja por familia cuando hay columna de familia; histograma cuando no
(esa rama `else` casi nunca se ejerce a mano, de ahi que
test_graficos.py la cubra con un df minimo a proposito).
"""


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tema import (
    ADVERTENCIA, GRIS_BORDE, SERIE_PRINCIPAL, ERROR, EXITO, GRIS_TEXTO_SUAVE,
)
from graficos.base import (
    _card, _wrap_cat,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.ajuste._comun import _fmt_corte, _layout_aj


def _graf_distribucion_ajuste(df, col_familia, col_area, col_ajuste_val, col_producto,
                              col_codigo=None, col_cantidad=None, col_fecha=None,
                              col_unidad=None):
    """Vista con toggle (Distribución / Histograma, `st.pills`) — cada una a
    ANCHO COMPLETO. Antes vivían a medias en `st.columns(2)`; esa mitad de
    ancho apretaba tanto el strip (categorías largas, se solapaban) como el
    histograma (bins finos, difíciles de leer). Ambas ramas excluyen los
    ajustes en cero.

    **Distribución** = strip plot coloreado (faltante/sobrante) por
    familia/área; si no hay columna de grupo, cae a un histograma de
    ajustes (fallback raro, cubierto por test_graficos.py con un df
    mínimo). Las dos variantes ponen el AJUSTE (S/) en el eje VERTICAL a
    propósito — es la métrica, va como "altura"; el eje horizontal es la
    categoría (grupo) o, en el fallback, la frecuencia del bin. Por eso el
    fallback usa `px.histogram(..., y=col_ajuste_val)` (no `x=`) y
    `add_hline` (no `add_vline`) para la línea de Cero — invertir sin
    cambiar los dos junto con el `xaxis`/`yaxis` del layout deja el
    histograma con el valor acostado.

    Con >50% de productos en S/ 0 (lo normal en un inventario), un boxplot
    colapsa q1=mediana=q3 en una línea invisible y solo deja ver puntos
    sueltos sin caja, y un histograma amontona todo en un pico que tapa las
    líneas de media/mediana/cero. Filtrar el cero antes de graficar es lo
    que deja ver la distribución real; el conteo de productos sin ajuste se
    muestra aparte como texto, no se pierde.

    Con `col_producto` resuelto, el hover se enriquece (vía `custom_data`)
    con código/área/cantidad/fecha, y clic + selección (caja o lazo, barra
    del gráfico) arma una tabla de detalle abajo — mismo patrón
    `on_select="rerun"` que ya usa `_graf_comparativa_mensual`. Las keys de
    ambos charts son estáticas a propósito: la selección solo pinta la
    tabla de abajo, no realimenta el propio gráfico, así que no aplica la
    trampa de key dinámica de arquitectura.md (selección con toggle
    infinito) — y tampoco la del toggle de vista: alternar
    Distribución/Histograma no reprocesa la selección del otro, porque el
    que no está activo ni siquiera se construye en ese rerun.

    Cuando la selección está activa (`_hay_prod`/`_hay_prod_hist`), dos
    cosas que Plotly NO trae por default y hacían que nadie usara esto:
    `dragmode="select"` explícito — sin él el modo activo es "pan" y
    arrastrar corre la vista en vez de seleccionar (así se llega fácil a
    "solo veo una familia", ver arquitectura.md) — y `config` con la barra
    recortada a 4-5 botones relevantes en vez de los 10 de default, con
    `displayModeBar=True` (no el "hover" default: visible siempre, no solo
    para quien ya sabía que estaba ahí). Sin `col_producto` la selección
    está apagada (`on_select="ignore"`) y la barra se oculta entera — no
    hay nada que seleccionar, mostrarla sería un botón muerto.

    El histograma tiene el mismo click→tabla, pero SIN custom_data sobre el
    propio `go.Histogram`: es una traza agregada (barras = bins, no filas)
    y `on_select` sobre ella es territorio no verificado — mismo riesgo que
    `go.Heatmap` (regla #11 de arquitectura.md, selección que nunca llega,
    sin error). Se reutiliza esa solución: overlay de `go.Scatter`
    invisible (opacity=0), un punto por bin a media altura, con el rango
    `[lo, hi]` de ese bin en `customdata`. El click/drag selecciona el
    punto invisible, no la barra; el rango de su customdata filtra `df_nz`
    directo en pandas."""
    grp = col_familia or col_area

    n_total = len(df)
    df_nz = df[df[col_ajuste_val] != 0]
    n_nz = len(df_nz)

    if df_nz.empty:
        st.info("Ningún producto tuvo ajuste distinto de cero en este rango.")
        return

    _vista = st.pills(
        "Vista distribución", ["Distribución", "Histograma"],
        default="Distribución", key="ajuste_dist_vista",
        label_visibility="collapsed",
    ) or "Distribución"

    if _vista == "Distribución":
        _es_strip = bool(grp and grp in df_nz.columns)
        _hay_prod = _es_strip and bool(col_producto and col_producto in df_nz.columns)
        _cap_dist = f"{n_nz} de {n_total} productos con diferencia"
        if _hay_prod:
            _cap_dist += " · arrastrá para seleccionar y ver el detalle abajo"
        st.caption(_cap_dist)

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
                # Sin esto el dragmode por default de Plotly es "pan": arrastrar
                # sobre el gráfico corre la vista en vez de seleccionar. "select"
                # lo deja listo para usar sin tocar ningún botón de la barra —
                # clic selecciona un punto, arrastre selecciona una caja.
                fig.update_layout(dragmode="select")
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
            # value en Y (vertical) a propósito, igual que el strip de arriba
            # — ver docstring. `y=` en vez de `x=` es lo que voltea px.histogram.
            fig = px.histogram(
                df_nz, y=col_ajuste_val, nbins=30,
                title="Distribución de ajustes valorizados",
                color_discrete_sequence=[SERIE_PRINCIPAL],
            )
            fig.add_hline(y=0, line_dash="dash", line_color="#ef4444",
                          annotation_text="Cero")
            fig.update_layout(**_layout_aj(
                yaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
                xaxis=dict(gridcolor=GRIS_BORDE),
            ))

        # Barra de Plotly recortada a lo que este gráfico realmente usa — con
        # los 10 botones de default (zoom/pan/lasso/autoscale/reset/...) nadie
        # sabe cuál toca, y el modo activo por default ("pan") hace que
        # arrastrar corra la vista en vez de seleccionar (fácil terminar
        # viendo una sola familia y creer que el resto no tiene datos).
        # displayModeBar=True en vez de "hover" (el default): que se vea
        # siempre, sin que el usuario tenga que saber que ahí hay algo para
        # pasar el mouse por encima.
        _cfg_strip = {"displaylogo": False}
        if _hay_prod:
            _cfg_strip["displayModeBar"] = True
            _cfg_strip["modeBarButtonsToRemove"] = [
                "zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d",
            ]
        else:
            _cfg_strip["displayModeBar"] = False

        with _card("dist_grupo", "Distribución por grupo"):
            _evento_dist = st.plotly_chart(
                fig, use_container_width=True, key="ajuste_dist_strip",
                on_select="rerun" if _hay_prod else "ignore",
                selection_mode=["points", "box", "lasso"],
                config=_cfg_strip,
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

    else:  # "Histograma"
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

        _hay_prod_hist = bool(col_producto and col_producto in df_nz.columns)
        _cap = f"{n_total - n_nz} productos en cero, excluidos del cálculo"
        if n_fuera:
            _cap += f" · {n_fuera} outliers fuera de este rango"
        if _hay_prod_hist:
            _cap += " · arrastrá para seleccionar y ver el detalle abajo"
        st.caption(_cap)

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
        if _hay_prod_hist:
            # Mismo motivo que en el strip de arriba: sin esto el drag por
            # default es "pan" y arrastrar sobre los bins no selecciona nada.
            fig2.update_layout(dragmode="select")

        # Mismo recorte de barra que el strip — acá directo sin lasso: la
        # selección corre sobre el overlay de Scatter invisible (ver
        # docstring), no sobre las barras, y selection_mode de abajo no
        # incluye "lasso" para este chart (el rango [lo, hi] por customdata
        # solo tiene sentido como caja, un lazo no define un intervalo).
        _cfg_hist = {"displaylogo": False}
        if _hay_prod_hist:
            _cfg_hist["displayModeBar"] = True
            _cfg_hist["modeBarButtonsToRemove"] = [
                "zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d",
                "lasso2d",
            ]
        else:
            _cfg_hist["displayModeBar"] = False

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
                config=_cfg_hist,
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
