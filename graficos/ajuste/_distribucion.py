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
    con código/área/cantidad/fecha, y la selección (caja o lazo en el strip,
    clic en la barra del histograma) arma una tabla de detalle abajo — mismo patrón
    `on_select="rerun"` que ya usa `_graf_comparativa_mensual`. Las keys de
    ambos charts son estáticas a propósito: la selección solo pinta la
    tabla de abajo, no realimenta el propio gráfico, así que no aplica la
    trampa de key dinámica de arquitectura.md (selección con toggle
    infinito) — y tampoco la del toggle de vista: alternar
    Distribución/Histograma no reprocesa la selección del otro, porque el
    que no está activo ni siquiera se construye en ese rerun.

    Cuando la selección está activa en el strip (`_hay_prod`), dos cosas
    que Plotly NO trae por default y hacían que nadie usara esto:
    `dragmode="select"` explícito — sin él el modo activo es "pan" y
    arrastrar corre la vista en vez de seleccionar (así se llega fácil a
    "solo veo una familia", ver arquitectura.md) — y `config` con la barra
    recortada a los botones relevantes en vez de los 10 de default, con
    `displayModeBar=True` (no el "hover" default: visible siempre, no solo
    para quien ya sabía que estaba ahí). Sin `col_producto` la selección
    está apagada (`on_select="ignore"`) y la barra se oculta entera — no
    hay nada que seleccionar, mostrarla sería un botón muerto.

    Con `dragmode="select"` un clic SUELTO no selecciona nada: Streamlit
    pone `clickmode="event"` (sin "select") mientras el modo sea select o
    lazo, así que clic y caja no conviven (regla #388). En el strip se
    acepta: el hover ya dice qué producto es cada punto, y el gesto que
    suma es la caja. El histograma va al revés y abre en modo CLIC: una
    barra es un bin que el hover no desglosa, y clic + shift+clic cubre
    cualquier tramo de sus 30 bins.

    La selección del histograma se lee del propio `go.Histogram`: se
    selecciona solo (verificado el 2026-09-12, Plotly 3.6) y cada barra
    devuelve en `point_indices` las filas de `d_hist` que cuenta — exacto,
    sin rehacer el binning en pandas. Hasta esa fecha llevaba un overlay de
    `go.Scatter` invisible por analogía con el Heatmap (reglas #11 y #44),
    con `hoverinfo="skip"`, que no recibió nunca un clic."""
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
                # lo deja listo para usar sin tocar ningún botón de la barra.
                # El precio: en este modo un clic suelto NO selecciona (ver
                # docstring y arquitectura.md #388) — el gesto es la caja.
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
            _cap += (" · clic en una barra para ver sus productos abajo"
                     " (shift+clic suma otras)")
        st.caption(_cap)

        _n_bins = 30
        _paso = (p_hi - p_lo) / _n_bins

        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=d_hist[col_ajuste_val],
            xbins=dict(start=p_lo, end=p_hi, size=_paso),
            name="Frecuencia",
            marker_color=SERIE_PRINCIPAL, opacity=0.75,
            hovertemplate="Valor: S/ %{x:,.2f}<br>Frecuencia: %{y}<extra></extra>",
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
            # Modo CLIC, a propósito NO "select" como el strip: en select
            # Streamlit apaga la selección por clic y la barra clickeada no
            # llegaba nunca a la tabla (regla #388). En "pan" Streamlit pone
            # clickmode="event+select", y los ejes fijos dejan quieto el
            # arrastre, que si no correría los bins fuera de la vista.
            fig2.update_layout(dragmode="pan")
            fig2.update_xaxes(fixedrange=True)
            fig2.update_yaxes(fixedrange=True)

        # Sin barra de Plotly: con los ejes fijos no hay zoom ni paneo que
        # ofrecer, y la caja NO se ofrece a propósito — quien la eligiera
        # quedaría sin forma de volver al clic (con los dos ejes fijos Plotly
        # tampoco dibuja el botón de pan), y shift+clic ya cubre un tramo.
        _cfg_hist = {"displaylogo": False, "displayModeBar": False}

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
                selection_mode="points",
                config=_cfg_hist,
            )

        if _hay_prod_hist:
            # `point_indices` junta las filas de TODAS las barras elegidas:
            # posiciones en `d_hist`, que es el `x` de la traza. No se usa el
            # `bin_number` de cada punto: Plotly recorta los bins vacíos de
            # los bordes y lo numera desde el primero con datos, no desde p_lo.
            _sel = ((_evento_hist or {}).get("selection", {}) or {})
            _idx = sorted({int(i) for i in (_sel.get("point_indices") or [])
                           if 0 <= int(i) < len(d_hist)})
            _sel_hist = d_hist.iloc[_idx]
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
