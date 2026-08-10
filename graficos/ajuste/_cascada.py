"""graficos.ajuste._cascada - vista Cascada (waterfall) por familia/area.

OJO: NO es un grafico Plotly. Es una TABLA de filas construida con
st.columns + HTML en st.markdown, con una columna de barras flotantes
que encadenan la cascada (ver arquitectura.md reglas #8 y #10). Se hizo
asi porque go.Waterfall no permite el nivel de control de etiquetas,
badges y drill por fila que pedia esta vista.
"""


import pandas as pd
import streamlit as st

from tema import (
    ACENTO, GRIS_BORDE, GRIS_FONDO,
    TEXTO_PRINCIPAL,
    BLANCO, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_FONDO, LAVANDA_SELECCION,
    AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO,
    AJUSTE_CRIT_FONDO, AJUSTE_CRIT_TEXTO, AJUSTE_CRIT_BORDE,
    AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO, AJUSTE_ALERTA_BORDE,
    AJUSTE_SOB_FONDO, AJUSTE_SOB_BORDE,
)
from graficos.base import (
    _card, _slug,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).


def _graf_waterfall_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto=None, col_valorizado=None,
                           col_cantidad=None, df_full=None, col_fecha=None,
                           col_unidad=None):
    """Cascada (Waterfall) por familia/área — SOLO el gráfico.

    `col_unidad` es la unidad de Kardex por producto (Kg, Und, Lt...) — se
    usa solo en el texto de las barras del drill; si no se resuelve, la
    barra muestra la cantidad sin sufijo (nunca el genérico "und").
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para el gráfico de cascada.")
        return

    agg = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
           .sum().sort_values(col_ajuste_val))
    if agg.empty:
        st.info("No hay datos para graficar en el rango seleccionado.")
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
    /* Buscador de Faltantes/Sobrantes en el drill (2026-08-08, a pedido):
       reemplaza el título fijo -- filtra los productos de esa zona en vez
       de solo etiquetarla. data-testid="stTextInputRootElement" es la caja
       real (fondo gris + borde 8px de radio); el <input> de adentro ya
       viene transparente y sin borde en esta versión de Streamlit, así que
       hay que aplanar la caja, no el <input>, o el look sigue siendo el de
       un campo de formulario normal en vez de un filete minimalista. */
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] {{
        height: auto !important; background: transparent !important;
        border: none !important; border-radius: 0 !important;
        border-bottom: 1px solid {GRIS_BORDE} !important;
        transition: border-color .12s ease; }}
    div[class*="st-key-ajcas_buscar_neg_"] [data-testid="stTextInputRootElement"]:focus-within {{
        border-bottom-color: {AJUSTE_NEG_TEXTO} !important; }}
    div[class*="st-key-ajcas_buscar_pos_"] [data-testid="stTextInputRootElement"]:focus-within {{
        border-bottom-color: {AJUSTE_POS_TEXTO} !important; }}
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] input {{
        height: auto !important; padding: 2px 2px 4px 2px !important;
        font-size: 11.5px !important; color: {TEXTO_PRINCIPAL} !important; }}
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] input::placeholder {{
        color: {GRIS_TEXTO_SUAVE} !important; opacity: 1 !important; }}
    /* Scroll propio por columna (Faltantes / Sobrantes) en vez de dejar
       crecer la tarjeta con hasta 30 filas -- a pedido, 2026-08-08.
       Scrollbar invisible por defecto (thumb transparente): aparece
       recién al pasar el cursor por la lista, no queda prendida todo
       el tiempo. No hay forma 100% CSS de mostrarla SOLO mientras se
       arrastra (necesitaría JS, y st.markdown no lo ejecuta -- ver
       CLAUDE.md); hover es la aproximación más cercana sin JS, y en la
       práctica coincide: para scrollear con mouse/trackpad el cursor
       ya tiene que estar encima. */
    .ajcas-lista-scroll {{
        max-height: 300px; overflow-y: auto;
        scrollbar-width: thin; scrollbar-color: transparent transparent;
        transition: scrollbar-color .15s ease; }}
    .ajcas-lista-scroll:hover {{
        scrollbar-color: {GRIS_TEXTO_SUAVE} transparent; }}
    .ajcas-lista-scroll::-webkit-scrollbar {{ width: 5px; }}
    .ajcas-lista-scroll::-webkit-scrollbar-track {{ background: transparent; }}
    .ajcas-lista-scroll::-webkit-scrollbar-thumb {{
        background: transparent; border-radius: 999px;
        transition: background-color .15s ease; }}
    .ajcas-lista-scroll:hover::-webkit-scrollbar-thumb {{
        background: {GRIS_TEXTO_SUAVE}; }}
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
        background: {LAVANDA_FONDO} !important; }}
    div[class*="st-key-ajcas_fila_"][class*="_on"]:hover {{
        background: {LAVANDA_FONDO} !important; }}
    /* ── Panel de drill (Faltantes/Sobrantes): sin caja propia (ni fondo
       ni borde alrededor), solo indentado — a pedido (2026-08-08) se
       saca el filete lavanda a la izquierda que antes "colgaba" del
       acento de la fila con foco (y el inset box-shadow de esa fila,
       arriba). margin-top negativo achica el row-gap:6px +
       margin-bottom:4px de la fila (10px de base) a un espacio chico
       (~2px), sin llegar al solape que usaba la variante fusionada —
       acá no hay bordes que calzar. */
    div[class*="st-key-ajcas_panel_drill"] {{
        background: transparent !important;
        border: none !important;
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
       título suba sin desalinearse de los KPIs: los dos viven en el
       mismo stHorizontalBlock, así que mover la card los sube juntos.
       Acotado a chartcard_cascada — el resto de las cards de gráficos
       conserva su padding.
       El aire se recorta primero ACÁ y no en el padding de las
       columnas de título/KPIs: tocarlo ahí las desalineaba entre sí
       (verificado midiendo rects). Título y KPIs van en 2 columnas
       iguales, cada una resetea su padding-top a 0 por separado.

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
    /* Cabecera oculta hasta pasar el cursor por la tabla (2026-08-08, a
       pedido -- "opción 1" de las 6 propuestas: sobre TODA la tabla, no
       fila por fila).
       Reveal por OPACITY+VISIBILITY, no por tamaño (cambiado 2026-08-09,
       a pedido). La v1 animaba max-height 0->24px + padding-bottom
       0->7px: aparecer/desaparecer corría la primera fila de la tabla
       hacia abajo/arriba -- "empuja las filas, mismo comportamiento que
       el mockup aprobado" era lo QUERIDO en ese momento, pero en uso se
       sintió como que la tabla saltaba y se pidió lo contrario: reservar
       el espacio siempre, sin desplazar nada de abajo. Ahora el <div>
       ocupa su alto real (padding-bottom:7px inline, sin tocar desde
       acá) todo el tiempo, oculto o visible -- cero reflow en las filas
       de abajo. Mismo patrón que .ajcas-tip-txt más arriba: opacity Y
       visibility (no opacity sola), para que el texto oculto no quede
       seleccionable ni en el tab order. El fade-out sigue siendo suave
       pese a animar `visibility` (propiedad discreta): por la regla de
       CSS Transitions para `visibility`, al OCULTAR el valor se queda en
       "visible" hasta el 100% de la transición (recién ahí salta a
       hidden), y al MOSTRAR salta a "visible" en el 0% -- nunca se
       "apaga" de golpe en la dirección que se anima con opacity. */
    .ajcas-head {{
        opacity: 0; visibility: hidden;
        transition: opacity .14s ease, visibility .14s ease; }}
    div[class*="st-key-chartcard_cascada"]:hover .ajcas-head,
    div[class*="st-key-chartcard_cascada"]:active .ajcas-head {{
        opacity: 1; visibility: visible; }}
    </style>""", unsafe_allow_html=True)

    with _card("cascada"):
        # ── Título + KPIs (antes vivían en la fila TOTAL de la tabla)
        #    Título a la izquierda, KPIs a la derecha en 2 columnas
        #    iguales (hasta 2026-08-09 había una tercera columna al medio
        #    con el popover "Excluir productos", quitado a pedido — ver
        #    git log si hace falta volver). Los KPIs van cada uno en su
        #    propia cápsula tonalizada por signo, no como texto plano
        #    separado por "|" — así se distinguen del título de un
        #    vistazo en lugar de leerse como una sola frase.────────

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

        _col_titulo, _col_kpis = st.columns(2)
        with _col_titulo:
            st.markdown(
                f"<div style='display:flex;align-items:center;"
                f"padding:0 0 14px 0'>{_titulo_html}</div>",
                unsafe_allow_html=True)
        with _col_kpis:
            # margin-top negativo: el padding-top de esta fila ya esta en 0
            # (igual que el título, ver comentario "Aire sobre el título"
            # arriba), asi que para subir SOLO los KPIs un poco mas no
            # queda otro knob que despegarlos con margen negativo — a
            # pedido, se acepta el desalineo extra con el título.
            st.markdown(
                f"<div style='display:flex;align-items:center;"
                f"justify-content:flex-end;flex-wrap:wrap;gap:12px;"
                f"margin-top:-4px;padding:0 0 14px 0'>"
                f"{_kpi_neto_html}{_kpi_pct_html}</div>",
                unsafe_allow_html=True)

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
                                    _t += f" · {_r[col_cantidad]:,.1f}"
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

                        _TOPN_DRILL = 30

                        def _buscador_lista(placeholder, key):
                            """Buscador minimalista que reemplaza el título
                            fijo (Faltantes/Sobrantes) a pedido. Filtra
                            _agg_dim ANTES del top _TOPN_DRILL, no la lista
                            ya recortada -- si no, un producto fuera del top
                            actual no aparecería nunca por más que calzara
                            con la búsqueda."""
                            return st.text_input(
                                placeholder, key=key, placeholder=placeholder,
                                label_visibility="collapsed",
                            ).strip().lower()

                        _pa, _pb = st.columns(2)
                        with _pa:
                            _q_neg = _buscador_lista(
                                "Buscar en faltantes…",
                                f"ajcas_buscar_neg_{_slug(focus_cat)}")
                            _neg_pool = _agg_dim[_agg_dim[col_ajuste_val] < 0]
                            if _q_neg:
                                _neg_pool = _neg_pool[_neg_pool[dim].astype(str)
                                    .str.lower().str.contains(_q_neg, regex=False)]
                            # ascending=True: el más negativo (mayor
                            # magnitud) primero en el DataFrame -> primero
                            # en el HTML -> arriba de la lista.
                            _neg = (_neg_pool.nsmallest(_TOPN_DRILL, col_ajuste_val)
                                    .sort_values(col_ajuste_val, ascending=True))
                            if _neg.empty:
                                st.caption("Sin coincidencias." if _q_neg else
                                          "Sin faltantes en esta familia.")
                            else:
                                st.markdown(
                                    f"<div class='ajcas-lista-scroll'>"
                                    f"{_filas_split_html(_neg, AJUSTE_NEG)}</div>",
                                    unsafe_allow_html=True)
                        with _pb:
                            _q_pos = _buscador_lista(
                                "Buscar en sobrantes…",
                                f"ajcas_buscar_pos_{_slug(focus_cat)}")
                            _pos_pool = _agg_dim[_agg_dim[col_ajuste_val] > 0]
                            if _q_pos:
                                _pos_pool = _pos_pool[_pos_pool[dim].astype(str)
                                    .str.lower().str.contains(_q_pos, regex=False)]
                            _pos = (_pos_pool.nlargest(_TOPN_DRILL, col_ajuste_val)
                                    .sort_values(col_ajuste_val, ascending=False))
                            if _pos.empty:
                                st.caption("Sin coincidencias." if _q_pos else
                                          "Sin sobrantes en esta familia.")
                            else:
                                st.markdown(
                                    f"<div class='ajcas-lista-scroll'>"
                                    f"{_filas_split_html(_pos, AJUSTE_POS)}</div>",
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
