"""graficos.ajuste._heatmap - vista Mapa de calor.

Tiene DOS modos (ver arquitectura.md regla #42) y TRES vistas — Mapa,
Flujo (Sankey) y Tabla — sobre el mismo corte seleccionado (regla #58).

Mapa NO es un trace de Plotly (regla #66): es una grilla de `st.button`,
una celda de dato real cada uno, coloreada con `plotly.colors.
sample_colorscale` + CSS por key. `go.Heatmap` rasteriza a PNG (sin rect
por celda en el DOM — verificado inspeccionando el SVG en vivo) así que
no había forma de redondear cada celda por separado, solo el contorno
general; un `st.button` real ya viene redondeado por la regla global de
`estilos/_00_base.py`, gratis. El click-drill usa el mismo patrón
botón + `session_state` + `st.rerun()` que ya usa el chevron de cada
fila en la Cascada, en vez de `on_select` (regla #11: no confiable para
trazas que no sean Bar/Scatter).
"""


import pandas as pd
import plotly.colors as pc
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
    _card, _slug,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.ajuste._comun import _cortes_por_racha, _layout_aj
# El mapa de calor tiene selector de corte PROPIO: consulta el estado de la
# franja para cederle el eje cuando el calendario ya fijó uno (ver abajo).
# "visual" es la categoría de rango a la que pertenece el mapa de calor en
# el rail (graficos.ajuste.categoria_rango_ajuste) — está fija acá porque
# este módulo ES una vista visual; no hay caso en que se renderice bajo la
# categoría "tiempo".
from estado_rango import clave_corte, corte_vigente


def _graf_heatmap_ajuste(df, col_familia, col_area, col_ajuste_val,
                         col_producto=None, col_fecha=None, df_full=None,
                         col_valorizado=None, area_sel=None, fam_sel=None,
                         col_cantidad=None, col_unidad=None):
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
    `df` pasa a ser el de ese corte para las tres vistas. Ese slider
    DESAPARECE si el calendario de la franja ya fijó un corte (modo
    Cortes): ahí el corte lo eligió el usuario arriba y `df` llega
    filtrado — un eje, un dueño. Flujo (Sankey) y
    Tabla (grilla HTML con barra-en-celda) son vistas alternativas del
    MISMO pivot, sin click-drill propio — todo lo de arriba (top-3,
    totales, hover, click-drill) sigue siendo exclusivo de Mapa.
    """
    if not col_familia or not col_area:
        st.info("Se necesitan columnas de familia y área para el mapa de calor.")
        return

    # ── Precalcular QUÉ controles van a mostrarse, antes de dibujar
    #    ninguno — hace falta saberlo para decidir cuántas columnas pedir
    #    (ver bloque de una sola fila más abajo). Ninguno de los dos
    #    todavía renderiza nada. ─────────────────────────────────────────
    _hay_valorizado = bool(col_valorizado and col_valorizado in df.columns)

    # `df_full` NO trae aplicados los chips Área/Familia de la franja
    # superior (esos filtran `d` -> `df` en __init__.py, no df_full) —
    # reaplicarlos ACÁ, mismo criterio exacto que ya usa
    # `_tabla_pivote_fecha_ajuste` para el mismo problema ("Por fecha de
    # corte" también parte de df_full). Sin este reaplicado, cambiar de
    # corte pisaba los chips en silencio: el usuario filtraba Área/
    # Familia y el mapa/flujo/tabla del corte volvían a mostrar TODO.
    #
    # UN EJE, UN DUEÑO: si el calendario de la franja ya fijó un corte
    # (modo Cortes, ver estado_rango.py), este slider no se dibuja y todo
    # el bloque de abajo se saltea. Dos controles del MISMO concepto no se
    # pisan el estado —cada uno tiene su clave— pero muestran cortes
    # distintos a la vez y el usuario no tiene cómo saber cuál manda. Con
    # el corte global activo `df` ya viene filtrado por app.py: acá solo
    # hay que no volver a filtrarlo (y ahorrarse el copy() de df_full).
    # Este slider SOLO se dibuja cuando el corte global está apagado (ver
    # arriba) — es decir, exactamente cuando el pill de la franja muestra
    # un RANGO ("1 ago - 5 ago"), no un corte puntual. No hay ningún otro
    # lugar en pantalla que diga cuál de los últimos 8 cortes quedó
    # elegido: la burbuja nativa de st.select_slider flota ARRIBA de la
    # barra y solo es visible mientras se arrastra. Por eso, debajo del
    # slider, una etiqueta fija con el corte activo (reportado 2026-08-09
    # comparando contra el mockup original).
    _corte_global = corte_vigente(clave_corte("Ajuste de Inventario",
                                              categoria="visual"))
    _dff = None
    _cortes = None
    if _corte_global is None and col_fecha and df_full is not None \
            and col_fecha in df_full.columns:
        _dff = df_full.copy()
        _dff[col_fecha] = pd.to_datetime(_dff[col_fecha], errors="coerce")
        _dff = _dff.dropna(subset=[col_fecha])
        if area_sel and col_area and col_area in _dff.columns:
            _dff = _dff[_dff[col_area].astype(str).isin(area_sel)]
        if fam_sel and col_familia and col_familia in _dff.columns:
            _dff = _dff[_dff[col_familia].astype(str).isin(fam_sel)]
        if not _dff.empty:
            _fmax_corte = _dff[col_fecha].max()
            _dff = _dff[_dff[col_fecha] >= _fmax_corte - pd.Timedelta(days=180)]
        if not _dff.empty:
            _corte_clave, _corte_etq = _cortes_por_racha(_dff[col_fecha])
            _dff = _dff.assign(_corte_clave=_corte_clave, _corte_etq=_corte_etq)
            _cortes_tmp = (_dff[["_corte_clave", "_corte_etq"]].drop_duplicates()
                          .sort_values("_corte_clave").tail(8))
            if len(_cortes_tmp) >= 2:
                _cortes = _cortes_tmp
    _hay_corte = _cortes is not None

    # ── Modo / Corte / Vista en UNA fila — antes cada uno vivía en su
    #    propio st.pills/slider de ancho completo, apilados con el
    #    espaciado default de Streamlit entre elementos: ocupaba como un
    #    tercio de la tarjeta en vertical (reportado 2026-08-09). Mismo
    #    truco que ya usan los chips Área/Familia de arriba (__init__.py):
    #    st.columns en vez de un elemento por fila. Columnas condicionales
    #    — sin col_valorizado no hay Modo, sin ≥2 cortes no hay slider —
    #    consumidas en orden con un iterador para no escribir la
    #    combinatoria de 2×2 a mano. ─────────────────────────────────────
    _anchos = ([1.3] if _hay_valorizado else []) + \
        ([1.5] if _hay_corte else []) + [1.0]
    _cols_ctrl = iter(st.columns(_anchos))

    _modo_val = False
    if _hay_valorizado:
        with next(_cols_ctrl):
            _modo = st.pills(
                "Modo mapa de calor", ["Ajuste Valorizado", "Valorizado Total"],
                default="Ajuste Valorizado", key="hm_ajuste_modo",
                label_visibility="collapsed",
            ) or "Ajuste Valorizado"
            _modo_val = (_modo == "Valorizado Total")
    col_metrica = col_valorizado if _modo_val else col_ajuste_val

    if _hay_corte:
        with next(_cols_ctrl):
            _opciones_corte = _cortes["_corte_etq"].tolist()
            _etq_sel = st.select_slider(
                "Corte", options=_opciones_corte,
                value=_opciones_corte[-1],
                key="hm_ajuste_corte", label_visibility="collapsed",
            )
            st.markdown(
                f"<div style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
                f"text-align:center;margin-top:-8px'>Corte: "
                f"<b style='color:{TEXTO_PRINCIPAL}'>{_etq_sel}</b></div>",
                unsafe_allow_html=True,
            )
            _clave_sel = _cortes.loc[
                _cortes["_corte_etq"] == _etq_sel, "_corte_clave"
            ].iloc[0]
            df = _dff[_dff["_corte_clave"] == _clave_sel].drop(
                columns=["_corte_clave", "_corte_etq"])

    with next(_cols_ctrl):
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
        # margin l/r generoso: Plotly ubica las etiquetas de nodo AFUERA del
        # diagrama solo si el margen les deja lugar -- con poco margen (10px,
        # el valor anterior) no entran y las escribe encima de las cintas de
        # color, ilegibles sobre fondo saturado (reportado con captura,
        # 2026-08-09). 140px alcanza para el nombre mas largo de familia o
        # area a la fuente default de Sankey (~12px).
        fig_sk.update_layout(**_layout_aj(
            height=min(560, max(280, (_n + _m) * 22 + 110)),
            margin=dict(l=140, r=140, t=20, b=10),
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

    # ── Top 3 por signo (mismo criterio que _badge_for en la Cascada: manda
    #    el valor absoluto) — decide qué celdas quedan a color pleno y
    #    cuáles se atenúan. ───────────────────────────────────────────────
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
    #    completo en cada rerun. Antes alimentaba un hovertemplate de
    #    Plotly (HTML, `<br>`); ahora va al `help=` de un `st.button`
    #    (texto plano) — mismo cálculo, separador " · " en vez de `<br>`. ──
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
                    f" · Tendencia ({len(_vals)} cortes): {_spark} {_flecha}"
                )

    _TITULO_HM = f"Mapa {_titulo_metrica}"

    # ── Colorscale: divergente centrada en cero para Ajuste (el signo
    #    importa: faltante/sobrante) vs secuencial anclada en cero para
    #    Valorizado Total (magnitud, nunca negativo) — misma definición
    #    que antes, solo que ahora la consume `sample_colorscale` en vez
    #    de un trace `go.Heatmap` (ver docstring del módulo, regla #66). ──
    if _modo_val:
        _colorscale_hm = ESCALA_CONTINUA
        _zmin_hm, _zmax_hm = 0.0, _vmax
    else:
        _colorscale_hm = [
            [0.00, ERROR],
            [0.35, ERROR_FONDO],
            [0.50, LAVANDA_SELECCION],
            [0.65, EXITO_FONDO],
            [1.00, EXITO],
        ]
        _zmin_hm, _zmax_hm = -_vmax, _vmax

    def _rgb_de(rgb_str):
        # sample_colorscale devuelve siempre "rgb(r, g, b)" (colortype
        # default) -- partir por los separadores es más liviano que traer
        # `re` solo para esto.
        _inner = rgb_str[rgb_str.index("(") + 1:rgb_str.index(")")]
        return tuple(int(_n) for _n in _inner.split(","))

    def _hex_a_rgb(_hex):
        _h = _hex.lstrip("#")
        return tuple(int(_h[i:i + 2], 16) for i in (0, 2, 4))

    def _color_celda(v, atenuar):
        _t = (v - _zmin_hm) / ((_zmax_hm - _zmin_hm) or 1.0)
        _t = max(0.0, min(1.0, _t))
        _rgb = _rgb_de(pc.sample_colorscale(_colorscale_hm, [_t])[0])
        if not atenuar:
            return _rgb
        # Atenuado = mezcla hacia LAVANDA_SELECCION -- mismo tono que usaba
        # el trace semitransparente de "apagado" de la versión Plotly,
        # ahora resuelto de una vez en el color final de fondo (sin
        # necesidad de una segunda capa). alpha=0.5 -> a mitad de camino.
        _dr, _dg, _db = _hex_a_rgb(LAVANDA_SELECCION)
        return tuple(round(c * 0.5 + d * 0.5) for c, d in zip(_rgb, (_dr, _dg, _db)))

    def _color_total_hm(v):
        if _modo_val:
            return ACENTO_TEXTO_OSCURO
        return DANGER_TEXT if v < 0 else CELDA_POS_TEXTO

    def _celda_html(_bg_rgb, _fg, _texto, _borde):
        # Mismo padding/min-height/box-sizing que el botón real de la
        # celda de dato (más abajo) -- son divs, no <button>, así que sin
        # esto el min-height:40px nativo del botón los deja más ALTOS que
        # el total/gran total y el grid se ve escalonado (reportado
        # 2026-08-09). display:flex + align-items centra el texto como lo
        # hacía el padding vertical de sobra en la versión anterior.
        _r, _g, _b = _bg_rgb
        return (
            f"<div style='background:rgb({_r},{_g},{_b});border:{_borde};"
            f"border-radius:8px;padding:4px 2px;text-align:center;"
            f"font-size:11px;font-weight:600;color:{_fg};"
            f"font-variant-numeric:tabular-nums;white-space:nowrap;"
            f"overflow:hidden;text-overflow:ellipsis;min-height:40px;"
            f"box-sizing:border-box;display:flex;align-items:center;"
            f"justify-content:center'>{_texto}</div>"
        )

    # ── Click-drill: qué celda tiene el foco. Reemplaza el `on_select` de
    #    Plotly (regla #11: `go.Heatmap` no es seleccionable) por el mismo
    #    patrón botón + session_state + rerun que ya usa el chevron de cada
    #    fila en la Cascada — más simple y, a diferencia de `on_select`,
    #    100% confiable (es un st.button real, no una traza). ─────────────
    _focus_key = "hm_ajuste_focus"
    _focus = st.session_state.get(_focus_key)
    if _focus is not None and (
            _focus[0] not in _fams or _focus[1] not in _areas):
        _focus = None
        st.session_state[_focus_key] = None

    _anchos_grid = [1.7] + [1.0] * _m + [1.1]
    _css_celdas = []

    with _card("heatmap", _TITULO_HM):
        # Cabecera: nombres de área, sin botón (no son clickeables).
        _cols_h = st.columns(_anchos_grid)
        with _cols_h[0]:
            st.markdown("&nbsp;", unsafe_allow_html=True)
        for _j, _area in enumerate(_areas):
            with _cols_h[_j + 1]:
                st.markdown(
                    f"<div style='font-size:9.5px;font-weight:500;"
                    f"color:{GRIS_TEXTO};text-align:center;"
                    f"line-height:1.2;padding-bottom:4px'>{_area}</div>",
                    unsafe_allow_html=True,
                )
        with _cols_h[-1]:
            st.markdown(
                f"<div style='font-size:9.5px;font-weight:700;"
                f"color:{ACENTO_TEXTO_OSCURO};text-align:center;"
                f"padding-bottom:4px'>TOTAL</div>",
                unsafe_allow_html=True,
            )

        # Una fila por familia — nombre + un st.button real por CADA celda
        # (incluidas las de valor 0: antes quedaban en blanco, pero el
        # go.Heatmap original también las coloreaba — el fondo por CSS
        # scoped a su key, ver más abajo — no hay motivo para esconderlas)
        # + total.
        for _i, _fam in enumerate(_fams):
            _cols_r = st.columns(_anchos_grid)
            with _cols_r[0]:
                st.markdown(
                    f"<div style='font-size:11px;font-weight:500;"
                    f"color:{TEXTO_PRINCIPAL};white-space:nowrap;"
                    f"overflow:hidden;text-overflow:ellipsis;"
                    f"text-align:right;padding-top:9px;padding-right:8px'"
                    f" title='{_fam}'>{_fam}</div>",
                    unsafe_allow_html=True,
                )
            for _j, _area in enumerate(_areas):
                _v = float(pivot.values[_i][_j])
                if abs(_v) < 0.5:
                    _v = 0.0  # evita el "S/ -0" de :.0f sobre p.ej. -0.3
                with _cols_r[_j + 1]:
                    _key = f"hm_cell_{_i}_{_j}"
                    _es_top = (_i, _j) in _top_set
                    _bg_rgb = _color_celda(_v, atenuar=not _es_top)
                    _luma = (0.299 * _bg_rgb[0] + 0.587 * _bg_rgb[1]
                             + 0.114 * _bg_rgb[2])
                    _fg = (BLANCO if (_es_top and _luma < 150)
                          else (GRIS_TEXTO_MEDIO if _es_top else GRIS_TEXTO_SUAVE))
                    _es_foco = (_focus == (_fam, _area))
                    if _es_foco:
                        _borde = f"2px solid {ACENTO}"
                    elif _es_top:
                        _color_anillo = (ACENTO if _modo_val
                                        else (EXITO if _v > 0 else ERROR))
                        _borde = f"2px solid {_color_anillo}"
                    else:
                        _borde = "1px solid transparent"
                    _r, _g, _b = _bg_rgb
                    _css_celdas.append(
                        f'.st-key-{_key} button {{ background:'
                        f'rgb({_r},{_g},{_b}) !important; color:{_fg} '
                        f'!important; border:{_borde} !important; '
                        f'font-size:11px !important; font-weight:600 '
                        f'!important; padding:4px 2px !important; '
                        f'font-variant-numeric:tabular-nums !important; }}'
                    )
                    _tip = f"{_fam} × {_area}: S/ {_v:,.0f}"
                    _tip += _spark_map.get((_fam, _area), "")
                    # En cero no hay nada que leer -- el color ya dice
                    # "neutro" y el número sobra (reportado 2026-08-09). La
                    # celda sigue coloreada y clickeable (regla de arriba),
                    # solo se le vacía la etiqueta visible.
                    _label = " " if _v == 0 else f"S/ {_v:,.0f}"
                    if st.button(_label, key=_key, help=_tip,
                                use_container_width=True):
                        st.session_state[_focus_key] = (
                            None if _es_foco else (_fam, _area))
                        st.rerun()
            with _cols_r[-1]:
                _vt = float(_row_tot.iloc[_i])
                st.markdown(
                    _celda_html(_hex_a_rgb(LAVANDA_CABECERA_GRUPO), _color_total_hm(_vt),
                               f"S/ {_vt:,.0f}", "none"),
                    unsafe_allow_html=True,
                )

        # Fila TOTAL — mismo tono lavanda que la columna, celdas no
        # clickeables (clic en el resumen nunca abrió detalle de producto).
        _cols_tot = st.columns(_anchos_grid)
        with _cols_tot[0]:
            st.markdown(
                f"<div style='font-size:11px;font-weight:700;"
                f"color:{ACENTO_TEXTO_OSCURO};text-align:right;"
                f"padding-top:9px;padding-right:8px'>TOTAL</div>",
                unsafe_allow_html=True,
            )
        for _j, _area in enumerate(_areas):
            with _cols_tot[_j + 1]:
                _vt = float(_col_tot.iloc[_j])
                st.markdown(
                    _celda_html(_hex_a_rgb(LAVANDA_CABECERA_GRUPO), _color_total_hm(_vt),
                               f"S/ {_vt:,.0f}", "none"),
                    unsafe_allow_html=True,
                )
        with _cols_tot[-1]:
            st.markdown(
                _celda_html(_hex_a_rgb(ACENTO), "#ffffff",
                           f"S/ {_grand_tot:,.0f}", "none"),
                unsafe_allow_html=True,
            )

        # CSS de todas las celdas con dato en UN solo bloque (streamlit
        # emite un <style> por st.markdown -- más liviano que uno por
        # celda). border-radius no hace falta pedirlo: button[kind=
        # "secondary"] ya lo trae en 8px por la regla global de
        # estilos/_00_base.py — es justo lo que un st.button da gratis y
        # go.Heatmap no podía dar (ver docstring del módulo). El color
        # SÍ hace falta por celda: es continuo, no hay paleta fija de
        # unas pocas clases como en la Cascada.
        if _css_celdas:
            st.markdown(f"<style>{''.join(_css_celdas)}</style>",
                       unsafe_allow_html=True)

        # Leyenda: gradiente CSS con los mismos 5 stops que ya usa
        # _color_celda -- reemplaza la colorbar nativa que traía
        # go.Heatmap (perdida al dejar de usar esa traza).
        _leyenda_izq = "Faltante" if not _modo_val else "S/ 0"
        _leyenda_der = "Sobrante" if not _modo_val else f"S/ {_vmax:,.0f}"
        _stops_css = ",".join(
            pc.sample_colorscale(_colorscale_hm, [k / 4])[0] for k in range(5)
        )
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;"
            f"margin-top:10px'>"
            f"<span style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
            f"white-space:nowrap'>{_leyenda_izq}</span>"
            f"<div style='flex:1;max-width:220px;height:6px;"
            f"border-radius:999px;background:linear-gradient(to right,"
            f"{_stops_css})'></div>"
            f"<span style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
            f"white-space:nowrap'>{_leyenda_der}</span></div>",
            unsafe_allow_html=True,
        )

    if _focus is not None:
        _fam_sel, _area_sel = _focus
        _val_sel = float(pivot.loc[_fam_sel, _area_sel])

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
                # cantidad/unidad al lado del monto — mismo criterio que ya
                # usa el drill de la Cascada (_filas_split_html): sum() para
                # cantidad, "first" para unidad (constante por producto, no
                # hay nada que sumar). _has_cant/_has_um en False si no
                # llegó la columna: el drill se comporta como antes.
                _has_cant = bool(col_cantidad and col_cantidad in _det.columns)
                _has_um = bool(col_unidad and col_unidad in _det.columns)
                _agg_map_hm = {col_metrica: "sum"}
                if _has_cant:
                    _agg_map_hm[col_cantidad] = "sum"
                if _has_um:
                    _agg_map_hm[col_unidad] = "first"
                _sub_prod = _det.groupby(col_producto, as_index=False).agg(_agg_map_hm)
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
                        _t = f"S/ {_r[col_metrica]:,.0f}"
                        if _has_cant:
                            _t += f" · {_r[col_cantidad]:,.1f}"
                            _um = (str(_r[col_unidad]).strip()
                                   if _has_um else "")
                            if _um and _um.lower() != "nan":
                                _t += f" {_um}"
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
                            f"{_t}</div></div>")
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
