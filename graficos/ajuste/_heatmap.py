"""graficos.ajuste._heatmap - vista Mapa de calor.

Tiene DOS modos (ver arquitectura.md regla #42) y TRES vistas — Mapa,
Flujo (Sankey) y Tabla — sobre el mismo corte seleccionado (regla #58).
En movil se renderiza a tamaño completo con scroll en vez de encogerse
hasta ser ilegible: el texto lo dibuja Plotly en el servidor, asi que no
hay media query que valga (ver graficos.base._es_movil).
"""


import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, GRIS_BORDE, GRIS_FONDO,
    TEXTO_PRINCIPAL,
    AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO,
    BLANCO, CELDA_POS_TEXTO,
    DANGER_TEXT, ERROR, ERROR_FONDO, ESCALA_CONTINUA, EXITO, EXITO_FONDO,
    GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_CABECERA_GRUPO, LAVANDA_SELECCION,
)
from graficos.base import (
    _card, _es_movil, _slug, _wrap_cat,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.ajuste._comun import _cortes_por_racha, _layout_aj


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

    Selector de Vista (Mapa / Flujo / Tabla, regla #58 de arquitectura.md):
    con `df_full` + `col_fecha` disponibles, un `st.select_slider` elige
    el CORTE real (no calendario — reusa `_cortes_por_racha`, la misma
    función que ya usa "Por fecha de corte") de los últimos ~8 con datos;
    `df` pasa a ser el de ese corte para las tres vistas. Flujo (Sankey) y
    Tabla (grilla HTML con barra-en-celda) son vistas alternativas del
    MISMO pivot, sin click-drill propio — todo lo de arriba (top-3,
    totales, hover, click-drill) sigue siendo exclusivo de Mapa.
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

    # ── Selector de corte — `df` llega acá acotado por la franja de fecha
    #    superior a "más o menos un mes" (categoría "visual", ver
    #    categoria_rango_ajuste): normalmente 1 o 2 cortes reales, no hay
    #    margen para animar nada. La fuente para el slider es `df_full`
    #    (mismo criterio que ya usa el sparkline de tendencia unas líneas
    #    más abajo), acotada a ~180 días para no pivotear el historial
    #    completo en cada rerun. Reusa `_cortes_por_racha` — la MISMA
    #    función que ya usa "Por fecha de corte" — en vez de inventar un
    #    agrupado por mes calendario. Sin `df_full`/`col_fecha`, o con
    #    menos de 2 cortes en la ventana, no se ofrece el slider y `df`
    #    sigue siendo el de siempre (se comporta exactamente como antes).
    if col_fecha and df_full is not None and col_fecha in df_full.columns:
        _dff = df_full.copy()
        _dff[col_fecha] = pd.to_datetime(_dff[col_fecha], errors="coerce")
        _dff = _dff.dropna(subset=[col_fecha])
        if not _dff.empty:
            _fmax_corte = _dff[col_fecha].max()
            _dff = _dff[_dff[col_fecha] >= _fmax_corte - pd.Timedelta(days=180)]
        if not _dff.empty:
            _corte_clave, _corte_etq = _cortes_por_racha(_dff[col_fecha])
            _dff = _dff.assign(_corte_clave=_corte_clave, _corte_etq=_corte_etq)
            _cortes = (_dff[["_corte_clave", "_corte_etq"]].drop_duplicates()
                       .sort_values("_corte_clave").tail(8))
            if len(_cortes) >= 2:
                _opciones_corte = _cortes["_corte_etq"].tolist()
                _etq_sel = st.select_slider(
                    "Corte", options=_opciones_corte,
                    value=_opciones_corte[-1],
                    key="hm_ajuste_corte", label_visibility="collapsed",
                )
                _clave_sel = _cortes.loc[
                    _cortes["_corte_etq"] == _etq_sel, "_corte_clave"
                ].iloc[0]
                df = _dff[_dff["_corte_clave"] == _clave_sel].drop(
                    columns=["_corte_clave", "_corte_etq"])

    # ── Selector de vista — Mapa (heatmap, todo lo de abajo) / Flujo
    #    (Sankey) / Tabla (grilla HTML) sobre el MISMO pivot del corte
    #    elegido arriba. Fila propia, separada del Modo: son dos ejes
    #    independientes (qué métrica vs. cómo mostrarla). ─────────────────
    _vista = st.pills(
        "Vista mapa de calor", ["Mapa", "Flujo", "Tabla"],
        default="Mapa", key="hm_ajuste_vista",
        label_visibility="collapsed",
    ) or "Mapa"

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

    _titulo_metrica = "Valorizado Total" if _modo_val else "Ajuste Valorizado"

    # ── Vista Flujo (Sankey) — misma matriz Familia×Área que el mapa,
    #    grosor de la cinta = magnitud, color = signo (pastel AJUSTE_NEG/
    #    AJUSTE_POS, la misma pareja que ya usa la Cascada — no ERROR/
    #    EXITO, muy saturados para un área grande). Nodos de familia
    #    tonalizados como la franja TOTAL del heatmap; nodos de área en
    #    gris neutro (mismo tipo -> mismo color en todo el dashboard).
    #    SIN click-drill: `on_select` sobre trazas no-Bar/Scatter no está
    #    verificado en este entorno (regla #11: ni siquiera go.Heatmap lo
    #    tenía sin el overlay de Scatter invisible; regla #44 deja
    #    constancia del mismo riesgo para go.Histogram) — Flujo se queda
    #    con hover rico y sin apostar a un click que no se pudo probar. ──
    if _vista == "Flujo":
        _sk_src, _sk_tgt, _sk_val, _sk_color, _sk_hover = [], [], [], [], []
        for _i, _fam in enumerate(_fams):
            for _j, _area in enumerate(_areas):
                _v = float(pivot.values[_i][_j])
                if abs(_v) < 0.5:
                    continue
                _sk_src.append(_i)
                _sk_tgt.append(_n + _j)
                _sk_val.append(abs(_v))
                _sk_color.append(AJUSTE_NEG if _v < 0 else AJUSTE_POS)
                _sk_hover.append(f"{_fam} → {_area}<br>S/ {_v:,.0f}")

        fig_sk = go.Figure(go.Sankey(
            node=dict(
                label=_fams + _areas, pad=14, thickness=14,
                color=([LAVANDA_CABECERA_GRUPO] * _n + [GRIS_FONDO] * _m),
                line=dict(color=GRIS_BORDE, width=0.5),
            ),
            link=dict(
                source=_sk_src, target=_sk_tgt, value=_sk_val,
                color=_sk_color, customdata=_sk_hover,
                hovertemplate="%{customdata}<extra></extra>",
            ),
        ))
        fig_sk.update_layout(**_layout_aj(
            height=min(560, max(280, (_n + _m) * 22 + 110)),
            margin=dict(l=10, r=10, t=20, b=10),
        ))
        with _card("heatmap", f"Flujo {_titulo_metrica}"):
            st.plotly_chart(fig_sk, use_container_width=True,
                            key="heatmap_ajuste_sankey")
        return

    # ── Vista Tabla — grilla HTML compacta (Familia × Área + columna
    #    Total), barra-riel-relleno en cada celda: mismo patrón que ya usa
    #    esta función para el ranking de productos del drill
    #    (`_filas_drill_html` más abajo), no una AgGrid nueva — un
    #    cellRenderer con barra-en-celda en AgGrid pide la interfaz de
    #    Component completa (regla #25), mucho más código que reusar un
    #    patrón ya probado en este mismo archivo. Filas ordenadas por
    #    |total familia| descendente; sin orden interactivo por columna en
    #    esta primera versión (pedirlo por clic necesita JS, que
    #    `st.markdown` no ejecuta, o un control Streamlit aparte que
    #    rerun-ea — se deja para más adelante si hace falta de verdad). ──
    if _vista == "Tabla":
        _row_tot_tb = pivot.sum(axis=1)
        _row_tot_tb = _row_tot_tb.reindex(
            _row_tot_tb.abs().sort_values(ascending=False).index)
        _col_max_tb = {_area: float(pivot[_area].abs().max()) or 1.0
                       for _area in _areas}
        _tot_max_tb = float(_row_tot_tb.abs().max()) or 1.0

        def _celda_tabla_html(_v, _max_abs):
            if abs(_v) < 0.5:
                return "<div style='height:20px'></div>"
            _pct = max(abs(_v) / _max_abs * 100, 5)
            _bg = AJUSTE_NEG if _v < 0 else AJUSTE_POS
            _tcol = AJUSTE_NEG_TEXTO if _v < 0 else AJUSTE_POS_TEXTO
            return (
                f"<div style='position:relative;height:20px'>"
                f"<div style='position:absolute;left:0;top:2px;bottom:2px;"
                f"width:{_pct:.1f}%;background:{_bg};opacity:.35;"
                f"border-radius:4px'></div>"
                f"<div style='position:relative;font-size:11px;"
                f"line-height:20px;padding-left:6px;color:{_tcol};"
                f"font-weight:600;font-variant-numeric:tabular-nums;"
                f"white-space:nowrap'>S/ {_v:,.0f}</div></div>"
            )

        _filas_tb_html = []
        for _fam in _row_tot_tb.index:
            _celdas_tb = "".join(
                f"<td style='padding:2px 6px'>"
                f"{_celda_tabla_html(float(pivot.loc[_fam, _area]), _col_max_tb[_area])}"
                f"</td>"
                for _area in _areas
            )
            _tot_tb = _celda_tabla_html(float(_row_tot_tb.loc[_fam]), _tot_max_tb)
            _nom_fam = str(_fam)
            _filas_tb_html.append(
                f"<tr><td style='padding:2px 8px;font-size:11.5px;"
                f"font-weight:500;color:{TEXTO_PRINCIPAL};white-space:nowrap'>"
                f"{_nom_fam}</td>{_celdas_tb}"
                f"<td style='padding:2px 6px;background:{LAVANDA_CABECERA_GRUPO};"
                f"border-radius:6px'>{_tot_tb}</td></tr>"
            )

        _head_tb = "".join(
            f"<th style='padding:0 6px 6px;font-size:10px;font-weight:600;"
            f"color:{GRIS_TEXTO_SUAVE};text-align:left;white-space:nowrap'>"
            f"{_area}</th>"
            for _area in _areas
        )
        _tabla_html = (
            f"<div style='overflow-x:auto'>"
            f"<table style='border-collapse:collapse;width:100%'>"
            f"<thead><tr><th></th>{_head_tb}"
            f"<th style='padding:0 6px 6px;font-size:10px;font-weight:600;"
            f"color:{ACENTO_TEXTO_OSCURO};text-align:left'>Total</th>"
            f"</tr></thead><tbody>{''.join(_filas_tb_html)}</tbody></table>"
            f"</div>"
        )
        with _card("heatmap", f"Tabla {_titulo_metrica}"):
            st.markdown(_tabla_html, unsafe_allow_html=True)
        return

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
        # :has(), no en la propia key) -- mismo motivo que el resto de
        # stickies de este archivo (arquitectura.md regla #25): puesto
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
                _sub_prod = (
                    _det.groupby(col_producto, as_index=False)[col_metrica]
                    .sum()
                )
                _sub_prod["_abs"] = _sub_prod[col_metrica].abs()
                _sub_prod = _sub_prod.sort_values(
                    "_abs", ascending=False).head(30)

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
