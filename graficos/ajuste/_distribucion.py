"""graficos.ajuste._distribucion - vista Distribucion.

La fila de encabezado (título · modo · familia, 2026-09-22) lleva el modo
como `st.selectbox` y la familia como `st.popover`, los dos "líneas
desplegables" con el trigger minimalista de Cascada/Mapa (`css_filtros_vista`)
en vez de botoneras. El modo tiene TRES valores, cada uno responde otra
pregunta:
  · Distribucion — strip por familia (caja/lazo -> detalle). ¿Como se
    reparten los desvios dentro de cada familia?
  · Histograma — frecuencia del ajuste valorizado. ¿Que FORMA tiene la
    distribucion (apretada al cero, colas gordas)?
  · Valor (Pareto) — barras por producto ordenadas por soles de faltante +
    linea de % acumulado (2026-09-22). ¿DONDE esta la plata y que corregir
    primero? Con miles de items de distinto precio/cantidad, el histograma
    cuenta ITEMS (una barra alta cerca del cero = muchos desvios chicos,
    poca plata); el Pareto los ordena por PLATA. El soles es el comun
    denominador que hace comparables items de escalas distintas.

Cuando no hay columna de familia el modo Distribucion cae a un histograma
(esa rama `else` casi nunca se ejerce a mano, de ahi que test_graficos.py la
cubra con un df minimo a proposito).
"""


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tema import (
    ACENTO, ADVERTENCIA, GRIS_BORDE, GRIS_TEXTO_MEDIO, SERIE_PRINCIPAL,
    ERROR, EXITO, GRIS_TEXTO_SUAVE, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import (
    _card, _wrap_cat, filtro_pills, sembrar_seleccion,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
# FAMILIAS_DE_ENTRADA: la MISMA semilla de Cascada y Mapa de calor (constante
# única — "alimentos, bebidas, vinos y embalajes"), para que las tres vistas
# del bloque Visual abran con el mismo recorte de familias.
from graficos.ajuste._comun import (
    FAMILIAS_DE_ENTRADA, css_filtros_vista, _fmt_corte, _layout_aj,
)


# Alto de la figura, más largo que el default (APOYO=380) a pedido
# (2026-09-22). `con_franja` reserva la fila de encabezado (título + los dos
# desplegables) y topa en PROTAGONISTA (430), el máximo que entra en una
# tarjeta de una pantalla. NO es un literal: sale de `alturas` (regla del
# presupuesto vertical), así que `test_graficos.py` no lo marca.
_ALTO_FIG = alturas.con_franja(alturas.PROTAGONISTA, alturas.FRANJA_UNA_LINEA)

# ── Modo AMPLIAR: la figura se agranda y la tarjeta se hace deslizable ──
# (2026-09-22, a pedido: «que esté dentro de una tarjeta y pueda ser
# deslizable para ver otros grupos o ampliar»). El alto sale de `alturas`
# (regla del presupuesto vertical); los ANCHOS de acá NO son altos, así que
# `test_graficos.py` no los toca. Son px por unidad del eje X en modo ampliado:
# el ancho total de la figura es `_EJE_PX + n * px`, y la tarjeta scrollea en
# horizontal lo que no entra. Distribución e Histograma parten la fila con la
# tabla a la derecha, así que su gráfico es MÁS ANGOSTO y se desliza para ver
# los lados YA en modo normal (px `_NORM`); Ampliar sólo lo agranda más
# (px `_AMP`). El Pareto va a ancho completo: sólo desliza al ampliar. Ver
# regla #494.
_EJE_PX = 60           # ancho reservado para el eje Y y su rótulo
_PX_STRIP_NORM = 150   # px por familia en el strip normal (columna izquierda)
_PX_STRIP_AMP = 260    # px por familia en el strip ampliado
_PX_PARETO_NORM = 120  # px por barra en el Pareto normal (columna izquierda)
_PX_PARETO_AMP = 210   # px por barra en el Pareto ampliado
_PX_BIN_NORM = 30      # px por bin (30) en el histograma normal
_PX_BIN_AMP = 46       # px por bin (30) en el histograma ampliado

# CSS del encabezado: el título de la vista y el aplanado del selectbox de
# modo a "línea" (para que combine con el trigger minimalista del popover de
# familia, que lo pone `css_filtros_vista`). Se inyecta cada render, sin
# guard de "una sola vez" (regla #59).
_CSS_ENCABEZADO = f"""
    .ajdist-titulo {{ font-size: 15px; font-weight: 500;
        color: {TEXTO_PRINCIPAL}; line-height: 2.2;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    /* El `st.selectbox` de modo es un `react-aria-ComboBox` (Streamlit
       reciente), NO un baseweb select: se aplana su control a una "línea"
       —sin borde ni fondo— para que combine con el trigger minimalista del
       popover de familia. Verificado el selector en el navegador. */
    div[class*="st-key-ajuste_dist_vista"] .react-aria-ComboBox > div {{
        border-color: transparent !important; background: transparent !important;
        box-shadow: none !important; min-height: 0 !important; }}
    div[class*="st-key-ajuste_dist_vista"] .react-aria-ComboBox input {{
        font-size: 11.5px !important; }}
"""


def _forzar_ancho(card_slug, ancho):
    """Fuerza el ancho en px de una figura Plotly de esta vista, en modo
    Ampliar. NO se puede por `fig.layout.width`: `st.plotly_chart` lo pisa con
    el ancho del contenedor (verificado en el navegador — Streamlit sólo
    respeta `fig.layout.height`, no el width; misma familia que la cabecera de
    `alturas.py`). Lo que SÍ funciona es agrandar el CONTENEDOR con CSS: el
    ResizeObserver de Streamlit ve el nuevo ancho y redimensiona la figura, y
    el `overflow-x:auto` de la tarjeta deja deslizar lo que sobra. Se inyecta
    cada render, sin guard (regla #59). Ver regla #494."""
    st.markdown(
        f"<style>"
        f"div[class*='st-key-chartcard_{card_slug}'] [data-testid='stPlotlyChart'],"
        f"div[class*='st-key-chartcard_{card_slug}'] [data-testid='stFullScreenFrame']"
        f"{{width:{int(ancho)}px !important;}}</style>",
        unsafe_allow_html=True)


_PARETO_TOP_N = 8


def _pareto_datos(df, col_ajuste_val, col_producto, top_n=_PARETO_TOP_N):
    """Agrega el ajuste NETO por producto, se queda con los FALTANTES
    (neto < 0), ordena por magnitud y agrupa la cola en «Otros (N)».

    El grano del df es la LÍNEA (producto × área); sumar sus líneas por
    producto es legítimo porque `AJUSTE VALORIZADO` es un valor por línea
    (a diferencia de las columnas *_ANO_ANTERIOR, que vienen repetidas por
    grupo — CLAUDE.md). Los valores salen como MAGNITUD positiva del
    faltante, en soles, para que la barra y el acumulado crezcan hacia
    arriba. Devuelve `(etiquetas, valores, acumulado, pct, pct_acum)`, todo
    en el mismo orden; listas vacías si no hay ningún faltante.

    «Sólo faltantes» es el default a pedido (2026-09-22): la pregunta es
    dónde se PIERDE plata. Un producto con sobrante neto no entra."""
    if not col_producto or col_producto not in df.columns:
        return [], [], [], [], []
    g = df.groupby(col_producto)[col_ajuste_val].sum()
    falt = g[g < 0]
    if falt.empty:
        return [], [], [], [], []
    mags = (-falt).sort_values(ascending=False)
    top = mags.iloc[:top_n]
    resto = mags.iloc[top_n:]
    etiquetas = [str(p) for p in top.index]
    valores = [float(v) for v in top.values]
    if len(resto) > 0:
        etiquetas.append(f"Otros ({len(resto)})")
        valores.append(float(resto.sum()))
    total = sum(valores) or 1.0
    acum, run = [], 0.0
    for v in valores:
        run += v
        acum.append(run)
    pct = [v / total * 100 for v in valores]
    pct_acum = [a / total * 100 for a in acum]
    return etiquetas, valores, acum, pct, pct_acum


def _fig_pareto_ajuste(df, col_ajuste_val, col_producto, top_n=_PARETO_TOP_N,
                       height=_ALTO_FIG):
    """Pareto del faltante: barras por producto (soles) + línea de acumulado.

    UN SOLO eje Y, en soles (la plata es lo que se pregunta): las barras son
    el faltante de cada producto y la línea es el acumulado corriendo hacia
    el total. El % vive en el hover y en la línea de referencia del 80% — no
    en un segundo eje (evita el eje doble y el choque de `_LAYOUT_BASE` con
    dos `yaxis`). Los nombres van horizontales y partidos con `_wrap_cat`
    porque `_layout` fuerza `tickangle=0` (regla #325). Devuelve None si no
    hay faltante que mostrar."""
    etiquetas, valores, acum, pct, pct_acum = _pareto_datos(
        df, col_ajuste_val, col_producto, top_n)
    if not etiquetas:
        return None
    colores = [ERROR] * len(valores)
    if etiquetas[-1].startswith("Otros"):
        colores[-1] = GRIS_TEXTO_MEDIO
    fig = go.Figure()
    fig.add_bar(
        x=etiquetas, y=valores, marker_color=colores, name="Faltante",
        customdata=[[p] for p in pct],
        hovertemplate="<b>%{x}</b><br>Faltante: S/ %{y:,.2f}"
                      "<br>%{customdata[0]:.1f}% del faltante total<extra></extra>")
    fig.add_scatter(
        x=etiquetas, y=acum, name="Acumulado", mode="lines+markers",
        line=dict(color=ACENTO, width=2), marker=dict(size=6),
        customdata=[[pa] for pa in pct_acum],
        hovertemplate="Acumulado: S/ %{y:,.2f}"
                      "<br>%{customdata[0]:.1f}% del faltante<extra></extra>")
    total = acum[-1] if acum else 0.0
    fig.add_hline(y=0.8 * total, line_dash="dash", line_color=GRIS_TEXTO_SUAVE,
                  annotation_text="80% del faltante",
                  annotation_position="top left")
    fig.update_layout(**_layout_aj(
        height=height,
        showlegend=False,
        yaxis=dict(showticklabels=True, tickprefix="S/ ", tickformat=",.0f",
                   gridcolor=GRIS_BORDE),
    ))
    fig.update_xaxes(tickmode="array", tickvals=etiquetas,
                     ticktext=_wrap_cat(etiquetas))
    return fig


def _pareto_valor(df_nz, col_ajuste_val, col_producto, col_area,
                  col_cantidad=None, col_fecha=None, col_unidad=None,
                  alto=_ALTO_FIG, amp=False):
    """Modo «Valor (Pareto)»: dibuja la figura en su tarjeta (a la izquierda) y
    DEVUELVE `(caption, DataFrame)` del detalle al clic —para la tarjeta de la
    derecha— o None.

    Clic en la barra de un producto -> el detalle son sus líneas (por área).
    La key es ESTÁTICA a propósito: la selección sólo pinta la tabla, no
    realimenta la figura, así que no aplica la trampa de la key dinámica
    (regla #399). Y abre en modo CLIC (`dragmode="pan"` + ejes fijos): en
    «select» Streamlit apaga el clic suelto y la barra no llegaría a la tabla
    (regla #388). La barra «Otros» no abre detalle: es la cola. Igual que el
    strip/histograma, se fuerza el ancho SIEMPRE para que la figura se deslice
    dentro de su columna (ver `_forzar_ancho`)."""
    _hay_prod = bool(col_producto and col_producto in df_nz.columns)
    fig = (_fig_pareto_ajuste(df_nz, col_ajuste_val, col_producto, height=alto)
           if _hay_prod else None)
    if fig is None:
        st.info("Ningún producto quedó con faltante neto en este rango.")
        return None
    st.caption("Productos ordenados por soles de faltante · la línea marca el "
               "% acumulado · clic en una barra para ver sus áreas a la derecha"
               " · deslizá para ver los lados")
    fig.update_layout(dragmode="pan")
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    _n = len(fig.data[0].x) if fig.data else 1
    _forzar_ancho("dist_pareto", _EJE_PX + max(_n, 1) * (
        _PX_PARETO_AMP if amp else _PX_PARETO_NORM))
    with _card("dist_pareto", ""):
        _ev = st.plotly_chart(
            fig, use_container_width=True, key="ajuste_dist_pareto",
            on_select="rerun", selection_mode="points",
            config={"displaylogo": False, "displayModeBar": False})
    _pts = ((_ev or {}).get("selection", {}) or {}).get("points", [])
    _prods = [p.get("x") for p in _pts
              if p.get("x") and not str(p.get("x")).startswith("Otros")]
    if not _prods:
        return None
    _sel = df_nz[df_nz[col_producto].astype(str).isin([str(x) for x in _prods])]
    if _sel.empty:
        return None
    _det = pd.DataFrame({"Producto": _sel[col_producto].astype(str)})
    if col_area and col_area in _sel.columns:
        _det["Área"] = _sel[col_area].astype(str)
    _det["Ajuste S/"] = _sel[col_ajuste_val]
    if col_cantidad and col_cantidad in _sel.columns:
        _det["Cantidad"] = _sel[col_cantidad]
    if col_fecha and col_fecha in _sel.columns:
        _f = pd.to_datetime(_sel[col_fecha], errors="coerce")
        _det["Corte"] = _f.map(lambda x: _fmt_corte(x) if pd.notna(x) else "")
    _det = _det.sort_values("Ajuste S/")
    _tot = float(_det["Ajuste S/"].sum())
    _fmt = _det.copy()
    _fmt["Ajuste S/"] = _fmt["Ajuste S/"].map(lambda v: f"S/ {v:,.2f}")
    return (f"{len(_det)} líneas · ajuste neto S/ {_tot:,.2f}", _fmt)


def _graf_distribucion_ajuste(df, col_familia, col_area, col_ajuste_val, col_producto,
                              col_codigo=None, col_cantidad=None, col_fecha=None,
                              col_unidad=None, df_full=None):
    """Tres modos (Distribución / Histograma / Valor (Pareto)), elegidos en
    el `st.selectbox` de la fila de encabezado, cada uno a ANCHO COMPLETO.
    Antes vivían a medias en `st.columns(2)`; esa mitad de ancho apretaba
    tanto el strip (categorías largas, se solapaban) como el histograma (bins
    finos, difíciles de leer). Las tres ramas excluyen los ajustes en cero.

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
    # ── FILA DE ENCABEZADO: título · modo · familia, todo en una línea ──
    # (2026-09-22, a pedido). El modo y la familia dejaron de ser botoneras y
    # pasaron a "líneas desplegables": el modo es un `st.selectbox`; la
    # familia, un `st.popover` con las pills adentro. Los dos con el trigger
    # minimalista de Cascada/Mapa (`css_filtros_vista`), así que el rótulo ES
    # el valor vigente. El título vive en esta fila —los gráficos ya no llevan
    # `title=`— y la figura de abajo gana alto (`_ALTO_FIG`).
    # Estado de AMPLIAR: sube el alto de la figura a `alturas.AMPLIADO`, que
    # supera una pantalla a propósito (ver `alturas`, regla #494). Sin card
    # envolvente que la clampee, la tarjeta crece y la página scrollea.
    _amp = bool(st.session_state.get("ajuste_dist_ampliar", False))
    _alto = alturas.AMPLIADO if _amp else _ALTO_FIG

    # DOS TARJETAS PROPIAS —gráfico (`chartcard_dist_*`) | tablas
    # (`ajdist_card_tablas`)—, con el look de la Cascada: blancas, borde gris,
    # radio 12, el color de la paleta (regla #1). Es la MISMA regla que el Mapa
    # de calor scopea a sus keys (regla #493): el borde va sobre la tarjeta y su
    # hijo directo a `none` para no doblar la línea. Ya NO hay card envolvente
    # (`ajuste_graf_card_izq_distribucion` se fue del dispatcher), así que
    # tampoco el clamp de una pantalla: lo que no entra lo scrollea la página,
    # como Cascada/Mapa de calor. El gráfico scrollea en X porque la figura se
    # fuerza más ancha que su tarjeta (`_forzar_ancho`). Ver regla #494.
    _css_cards = (
        'div[class*="st-key-chartcard_dist_grupo"],'
        'div[class*="st-key-chartcard_dist_hist"],'
        'div[class*="st-key-chartcard_dist_pareto"],'
        'div[class*="st-key-ajdist_card_tablas"]{'
        'background:var(--bg-card) !important;'
        f'border:1px solid {GRIS_BORDE} !important;'
        'border-radius:12px !important;padding:10px 14px 12px 14px !important;}'
        'div[class*="st-key-chartcard_dist_grupo"]>div,'
        'div[class*="st-key-chartcard_dist_hist"]>div,'
        'div[class*="st-key-chartcard_dist_pareto"]>div,'
        'div[class*="st-key-ajdist_card_tablas"]>div{border:none !important;}'
        'div[class*="st-key-chartcard_dist_grupo"],'
        'div[class*="st-key-chartcard_dist_hist"],'
        'div[class*="st-key-chartcard_dist_pareto"]{overflow-x:auto;}'
    )
    st.markdown(f"<style>{css_filtros_vista('ajdist_ctrl_', 'ajdist_nolist_')}"
                f"{_CSS_ENCABEZADO}{_css_cards}</style>", unsafe_allow_html=True)

    # Semilla y opciones de familia. Del parquet ENTERO (`df_full`) para que
    # la lista no cambie con el rango; la siembra sólo prende las que existen.
    # Con filtro propio, la vista NO pasa por los chips Área/Familia de arriba
    # (recibe `d_sin_chips`): filtrar dos veces daría la intersección de dos
    # compartimentos con uno solo visible (regla #425).
    _tiene_fam = bool(col_familia and col_familia in df.columns)
    _opc_fam = []
    if _tiene_fam:
        _src_fam = (df_full if (df_full is not None
                                and col_familia in df_full.columns) else df)
        _opc_fam = sorted(_src_fam[col_familia].dropna().astype(str).unique().tolist())
        sembrar_seleccion(pd.DataFrame({col_familia: _opc_fam}), col_familia,
                          "ajuste_dist_filtro_familia", list(FAMILIAS_DE_ENTRADA))

    _c_tit, _c_modo, _c_fam, _c_amp = st.columns([3, 1.4, 1.5, 1.15],
                                                 vertical_alignment="center")
    with _c_amp:
        st.toggle(
            "Ampliar", key="ajuste_dist_ampliar",
            help="Agranda el gráfico y hace la tarjeta deslizable, para ver los "
                 "grupos con más aire. La tarjeta deja de caber en una pantalla "
                 "mientras esté ampliada.")
    with _c_modo:
        _vista = st.selectbox(
            "Vista", ["Distribución", "Histograma", "Valor (Pareto)"],
            key="ajuste_dist_vista", label_visibility="collapsed",
        ) or "Distribución"
    # El rótulo del popover ES la selección vigente (lag de un rerun, igual
    # que Cascada). El widget vive DENTRO del popover con el patrón #467-safe
    # de `filtro_pills` (`seleccion_en_panel`), y filtra `df` en la misma
    # pasada leyendo `session_state`, esté el panel abierto o cerrado.
    with _c_fam.container(key="ajdist_ctrl_familia"):
        _sel = [f for f in (st.session_state.get("ajuste_dist_filtro_familia")
                            or []) if f in _opc_fam]
        _et = ("todas las familias" if not _sel
               else f"{len(_sel)} familias" if len(_sel) > 1 else _sel[0].lower())
        with st.popover(f":material/category: {_et}", use_container_width=True):
            if _tiene_fam:
                df, _ = filtro_pills(df, col_familia, "ajuste_dist_filtro_familia",
                                     "Familia", valores=_opc_fam or None)
    with _c_tit:
        _TITULO = {"Distribución": "Distribución del ajuste",
                   "Histograma": "Histograma de frecuencias",
                   "Valor (Pareto)": "Dónde se concentra el faltante"}.get(_vista, "")
        st.markdown(f'<div class="ajdist-titulo">{_TITULO}</div>',
                    unsafe_allow_html=True)

    grp = col_familia or col_area

    n_total = len(df)
    df_nz = df[df[col_ajuste_val] != 0]
    n_nz = len(df_nz)

    if df_nz.empty:
        st.info("Ningún producto tuvo ajuste distinto de cero en este rango.")
        return

    # ── LAYOUT: gráfico en SU tarjeta a la IZQUIERDA, tablas en SU tarjeta a
    # la DERECHA — los TRES modos (2026-09-22, a pedido: «que el gráfico en sus
    # tres modos figuren en su propia tarjeta y las tablas en una tarjeta, a la
    # derecha»). El gráfico —más angosto por la tabla— se DESLIZA en horizontal
    # para ver las familias/bins/barras de los lados (ancho forzado por CSS, no
    # por `fig.layout.width`, que Streamlit pisa — ver `_forzar_ancho`). A la
    # derecha van APILADAS la tabla del detalle de la selección (arriba) y la
    # del «5% inferior» (abajo, sólo Distribución/Histograma; el Pareto ya ES un
    # ranking). Ver regla #494.
    _col_g, _col_t = st.columns([1.45, 1], gap="medium")
    _detalle = None  # (caption, DataFrame) de la selección → columna derecha
    _es_pareto = _vista == "Valor (Pareto)"

    with _col_g:
        if _vista == "Distribución":
            _es_strip = bool(grp and grp in df_nz.columns)
            _hay_prod = _es_strip and bool(col_producto and col_producto in df_nz.columns)
            _cap_dist = f"{n_nz} de {n_total} productos con diferencia"
            if _hay_prod:
                _cap_dist += " · arrastrá para seleccionar (detalle a la derecha)"
            _cap_dist += " · deslizá para ver los lados"
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
                    labels={col_ajuste_val: "Ajuste S/", grp: "", "_signo": ""},
                    custom_data=_cd_cols,
                )
                fig.add_hline(y=0, line_dash="dot", line_color=GRIS_TEXTO_SUAVE,
                              annotation_text="Cero", annotation_position="top right")
                fig.update_layout(**_layout_aj(
                    height=_alto,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="right", x=1, title=None),
                    xaxis=dict(tickangle=-30, gridcolor=GRIS_BORDE),
                    yaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
                ))
                if _hay_prod:
                    # Sin esto el dragmode por default de Plotly es "pan":
                    # arrastrar sobre el gráfico corre la vista en vez de
                    # seleccionar. "select" lo deja listo sin tocar la barra. El
                    # precio: un clic suelto NO selecciona (arquitectura.md #388).
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
                # Ancho forzado SIEMPRE (no sólo al ampliar): en la columna
                # izquierda el gráfico es más angosto y tiene que deslizarse
                # para ver todas las familias.
                _px_fam = _PX_STRIP_AMP if _amp else _PX_STRIP_NORM
                _ancho_dist = _EJE_PX + max(len(_xcats), 1) * _px_fam
            else:
                # value en Y (vertical) a propósito, igual que el strip de arriba
                # — ver docstring. `y=` en vez de `x=` es lo que voltea px.histogram.
                fig = px.histogram(
                    df_nz, y=col_ajuste_val, nbins=30,
                    color_discrete_sequence=[SERIE_PRINCIPAL],
                )
                fig.add_hline(y=0, line_dash="dash", line_color="#ef4444",
                              annotation_text="Cero")
                fig.update_layout(**_layout_aj(
                    height=_alto,
                    yaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
                    xaxis=dict(gridcolor=GRIS_BORDE),
                ))
                _ancho_dist = _EJE_PX + 30 * (_PX_BIN_AMP if _amp else _PX_BIN_NORM)

            # Barra de Plotly recortada a lo que este gráfico realmente usa —
            # con los 10 botones de default nadie sabe cuál toca, y el modo
            # "pan" hace que arrastrar corra la vista en vez de seleccionar.
            _cfg_strip = {"displaylogo": False}
            if _hay_prod:
                _cfg_strip["displayModeBar"] = True
                _cfg_strip["modeBarButtonsToRemove"] = [
                    "zoom2d", "pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d",
                ]
            else:
                _cfg_strip["displayModeBar"] = False

            _forzar_ancho("dist_grupo", _ancho_dist)
            with _card("dist_grupo", ""):
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
                    _det_fmt = _det.copy()
                    _det_fmt["Ajuste S/"] = _det_fmt["Ajuste S/"].map(
                        lambda v: f"S/ {v:,.2f}")
                    _detalle = (
                        f"{len(_det)} seleccionados · ajuste neto S/ {_total:,.2f}",
                        _det_fmt)

        elif _vista == "Histograma":
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
                _cap += (" · clic en una barra para ver sus productos a la derecha"
                         " (shift+clic suma otras)")
            _cap += " · deslizá para ver los lados"
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
                height=_alto,
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

            _cfg_hist = {"displaylogo": False, "displayModeBar": False}

            _forzar_ancho("dist_hist", _EJE_PX + _n_bins * (
                _PX_BIN_AMP if _amp else _PX_BIN_NORM))
            with _card("dist_hist", ""):
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
                # `bin_number`: Plotly recorta los bins vacíos de los bordes y lo
                # numera desde el primero con datos, no desde p_lo.
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
                    _det2_fmt = _det2.copy()
                    _det2_fmt["Ajuste S/"] = _det2_fmt["Ajuste S/"].map(
                        lambda v: f"S/ {v:,.2f}")
                    _detalle = (
                        f"{len(_det2)} seleccionados · ajuste neto S/ {_total2:,.2f}",
                        _det2_fmt)

        else:  # "Valor (Pareto)"
            _detalle = _pareto_valor(
                df_nz, col_ajuste_val, col_producto, col_area,
                col_cantidad=col_cantidad, col_fecha=col_fecha,
                col_unidad=col_unidad, alto=_alto, amp=_amp)

    # ── COLUMNA DERECHA, EN SU TARJETA: detalle de la selección (arriba) +
    # «5% inferior» (abajo), apiladas. El «5% inferior» acompaña a Distribución
    # e Histograma; en el Pareto sobra —la vista YA es el ranking de faltantes.
    # Si no hay nada que mostrar (Pareto sin clic, o sin selección y sin
    # outliers), la tarjeta lleva una línea de ayuda para no quedar vacía. ──
    with _col_t:
        with st.container(border=True, key="ajdist_card_tablas"):
            _hay_tabla = False
            if _detalle is not None:
                st.caption(_detalle[0])
                st.dataframe(_detalle[1], hide_index=True,
                             use_container_width=True)
                _hay_tabla = True
            if not _es_pareto and col_producto and col_producto in df.columns:
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
                    _hay_tabla = True
            if not _hay_tabla:
                st.caption("Seleccioná en el gráfico para ver el detalle acá.")
