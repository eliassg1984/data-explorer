"""graficos.ajuste._heatmap - la matriz Familia × Área de Ajuste.

UNA vista desde el 2026-09-18: una TABLA con la barra dentro de la celda,
clickeable en los dos modos (Ajuste Valorizado y Valorizado Total). Hasta
ese día eran tres vistas del mismo pivot —Mapa (celdas pintadas), Flujo
(Sankey) y Tabla— y se retiraron las dos primeras a pedido, después de
compararlas: la tabla dice lo mismo con una barra, que se compara mejor
que un color; es sobria donde el mapa rojo/verde se leía «muy colorido»;
y mide la mitad de alto. Lo único que le faltaba era el clic del mapa, y
lo heredó. Regla #468.

El módulo conserva su nombre (`_heatmap.py`, `_graf_heatmap_ajuste`, las
keys `hm_*` y la sección `aj_sec_heatmap`): es lo que citan el rail, el
CSS y las reglas #42, #58 y #66.

CÓMO SE HACE CLICKEABLE UNA TABLA SIN JS. `st.markdown` no ejecuta
`<script>`, así que una celda de un `<table>` no tiene cómo avisar un
clic. La tabla es una grilla de `st.columns` y cada celda con registros
es un `st.button` real —el patrón que nació en el Mapa, regla #66—. La
barra no puede ser un `<div>` adentro del botón (su label es texto): es
el `::before` del botón, con el largo y el color en variables CSS por
key.
"""


import pandas as pd
import plotly.colors as pc
import streamlit as st

from utils import _norm
from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS,
    AJUSTE_POS_TEXTO, BLANCO, ESCALA_CONTINUA, GRIS_BORDE,
    GRIS_TEXTO_SUAVE, LAVANDA_CABECERA_GRUPO, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _card, _es_movil,
)
# Los tres filtros propios (corte · familia · área) son los MISMOS que
# los de la Cascada, misma pieza y mismo default de familias: viven en
# `_comun.py` desde el 2026-09-15 justamente porque son dos vistas.
from graficos.ajuste._comun import (
    css_filtros_vista, estado_filtros_vista, render_filtros_vista,
)
# Los helpers de alto/key de las grillas viven en `_cascada` (no hay ciclo:
# `_cascada` no importa este módulo, y `__init__` importa `_cascada` antes).
# El detalle del Mapa de calor usa las MISMAS grillas de desglose que la
# Cascada, con una barra de severidad detrás del monto (regla #483).
from graficos.ajuste._cascada import _alto_grilla, _atar_alto, _clave
from tablas.ajuste_familias import renderizar_desglose_ajuste


# LAS TRES CLAVES DE ESTA VISTA, distintas de las de la Cascada a
# propósito: rango/filtro por TARJETA, no compartidos (misma idea que el
# rango por tarjeta de Compras, arquitectura.md regla #363). Cambiar de
# familia en la Cascada no tiene por qué mover esta tabla.
_K_CORTE = "hm_corte"
_K_FAMILIA = "hm_filtro_familia"
_K_AREA = "hm_filtro_area"
# UNA KEY POR CONTROL: `st.popover` no emite `st-key-*` propio, así que sin
# su contenedor el inspector y el modo diseño resuelven hacia arriba hasta
# la tarjeta entera. Es también el scope del CSS del trigger (#431).
_K_CTRL = ("hm_ctrl_fecha", "hm_ctrl_familia", "hm_ctrl_area")
# La celda en foco, `(familia, área)` o None. Es la misma clave que usaba
# el Mapa: un foco guardado de antes sigue valiendo.
_K_FOCO = "hm_ajuste_focus"

# CON QUÉ CELDA ABRE LA VISTA (a pedido, 2026-09-21): el detalle de
# ALIMENTOS × Almacén Central ya desplegado. Se emparejan por texto
# NORMALIZADO contra las filas/columnas presentes —el parquet trae la
# familia en mayúsculas y el área SIN tilde ("ALMACEN CENTRAL", igual que
# `inventario.py::ABRE_EN_AREA`)—, no por el literal, para que un cambio de
# formato del maestro no rompa el default en silencio.
_FAM_INICIAL = "Alimentos"
_AREA_INICIAL = "Almacén Central"

# El azul de Valorizado Total sale de la MISMA escala con que el mapa
# pintaba ese modo (`ESCALA_CONTINUA`), no de un hex nuevo: es el color que
# se pidió conservar. 0.65 para la barra —a 35 % de opacidad, como las de
# Ajuste— y 0.9 para el número, que sobre blanco tiene que leerse.
_AZUL_BARRA, _AZUL_TEXTO = pc.sample_colorscale(ESCALA_CONTINUA, [0.65, 0.9])

# Alto de una fila de la tabla, en px. Lo comparten el botón de una celda
# de dato y el `<div>` de una de Total: si difieren, la fila se escalona.
_ALTO_CELDA = 24


def _rgb(color):
    """`#rrggbb` o `rgb(r, g, b)` -> (r, g, b)."""
    if color.startswith("#"):
        _h = color.lstrip("#")
        return tuple(int(_h[i:i + 2], 16) for i in (0, 2, 4))
    _dentro = color[color.index("(") + 1:color.index(")")]
    return tuple(int(float(_n)) for _n in _dentro.split(","))


def _rgba(color, alfa=0.35):
    _r, _g, _b = _rgb(color)
    return f"rgba({_r},{_g},{_b},{alfa})"


def _paleta(v, modo_val):
    """(color de la barra, color del número) de una celda.

    Ajuste: la pareja terracota/salvia de la casa, por SIGNO — la misma de
    la Cascada, y no ERROR/EXITO, que a tope eran lo «muy colorido» que
    se reportó del mapa. Valorizado Total: azul. Ahí no hay signo, y el
    verde que llevaba la tabla vieja en ese modo decía «sobrante» de algo
    que no lo es."""
    if modo_val:
        return _AZUL_BARRA, _AZUL_TEXTO
    if v < 0:
        return AJUSTE_NEG, AJUSTE_NEG_TEXTO
    return AJUSTE_POS, AJUSTE_POS_TEXTO


def _pct(v, max_abs):
    """Largo de la barra, en % de la celda. Piso de 4 para que un monto
    chico no desaparezca: cuánto es lo dice el número."""
    return max(abs(v) / (max_abs or 1.0) * 100, 4)


def _alternar_foco(celda):
    """Callback del clic. Corre ANTES de la corrida, así que la tabla ya se
    dibuja con el foco nuevo y no hace falta el `st.rerun()` que llevaba el
    Mapa — que, dentro del fragment de la sección, era una corrida de la
    app ENTERA por cada clic."""
    st.session_state[_K_FOCO] = (
        None if st.session_state.get(_K_FOCO) == celda else celda)


def _foco_inicial(fams, areas, n_reg):
    """`(familia, área)` con que ABRE la vista, o None si no está disponible.

    ALIMENTOS × Almacén Central (`_FAM_INICIAL`/`_AREA_INICIAL`) emparejadas
    por texto normalizado contra las filas y columnas presentes de la tabla,
    sólo si esa celda tiene registros que desglosar —una celda sin registros
    no abre nada—. Sin match (otro corte, la familia filtrada fuera), None:
    la vista arranca sin detalle, igual que antes de sembrar el foco."""
    _fam = next((f for f in fams if _norm(f) == _norm(_FAM_INICIAL)), None)
    _area = next((a for a in areas if _norm(a) == _norm(_AREA_INICIAL)), None)
    if _fam is not None and _area is not None and n_reg.get((_fam, _area), 0):
        return (_fam, _area)
    return None


def _celda_total_html(v, max_abs, modo_val):
    """Una celda de la columna o de la fila Total: lavanda, con su barra.

    Es un `<div>` y no un botón: un agregado no abre detalle (en el Mapa
    tampoco), porque no tiene UN ranking de productos que mostrar."""
    _bar, _txt = _paleta(v, modo_val)
    _barra = "" if abs(v) < 0.5 else (
        f"<div style='position:absolute;left:0;top:2px;bottom:2px;"
        f"width:{_pct(v, max_abs):.1f}%;background:{_rgba(_bar)};"
        f"border-radius:4px'></div>")
    return (
        f"<div style='background:{LAVANDA_CABECERA_GRUPO};"
        f"border-radius:6px;padding:0 3px'>"
        f"<div style='position:relative;height:{_ALTO_CELDA}px'>{_barra}"
        f"<div style='position:relative;line-height:{_ALTO_CELDA}px;"
        f"padding-left:6px;font-size:11px;font-weight:600;color:{_txt};"
        f"font-variant-numeric:tabular-nums;white-space:nowrap'>"
        f"S/ {v:,.0f}</div></div></div>"
    )


def _tendencias(df, df_full, col_fecha, col_familia, col_area, col_metrica):
    """`{(familia, área): texto}` con la tendencia de los últimos cortes,
    para el `help=` de cada celda.

    Mira `df_full` y no sólo el corte elegido —mismo espíritu que el delta
    de la Cascada: cómo veníamos llegando—, acotado a 120 días hacia atrás
    para no pivotear el historial entero en cada rerun. Es texto plano
    (sparkline de caracteres Unicode): el `help=` de un botón no pinta
    HTML."""
    _bloques = "▁▂▃▄▅▆▇█"
    _n_cortes = 7
    _spark = {}
    if not (col_fecha and df_full is not None
            and col_fecha in df_full.columns):
        return _spark
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
    if _dfe.empty:
        return _spark
    _piv_t = _dfe.pivot_table(
        index=[col_familia, col_area], columns=col_fecha,
        values=col_metrica, aggfunc="sum", fill_value=0.0,
    )
    _cortes_cols = sorted(_piv_t.columns)[-_n_cortes:]
    for _key in _piv_t.index:
        _vals = [float(_piv_t.loc[_key, c]) for c in _cortes_cols]
        if len(_vals) < 2:
            continue
        _lo, _hi = min(_vals), max(_vals)
        _rng = (_hi - _lo) or 1.0
        _linea = "".join(
            _bloques[min(7, int((v - _lo) / _rng * 8))] for v in _vals)
        _flecha = "▲" if _vals[-1] >= _vals[-2] else "▼"
        _spark[_key] = f" · Tendencia ({len(_vals)} cortes): {_linea} {_flecha}"
    return _spark


def _graf_heatmap_ajuste(df, col_familia, col_area, col_ajuste_val,
                         col_producto=None, col_fecha=None, df_full=None,
                         col_valorizado=None,
                         col_cantidad=None, col_unidad=None):
    """Tabla familia × área — modo Ajuste (signado) o Valorizado Total
    (siempre positivo), elegido con un `st.pills` al tope. Cada celda con
    registros abre, al clic, el detalle de sus productos debajo de la
    tarjeta; otro clic en la misma lo cierra.

    Lo que dice la tabla (regla #468):
      · UNA escala para todas las celdas de dato. La tabla vieja escalaba
        cada columna contra su propio máximo, y en Valorizado Total
        Producción S/ 5,533 tenía la barra tan larga como Almacén central
        S/ 21,100: una barra que no se puede comparar con la de al lado no
        es una barra. La columna y la fila Total llevan cada una la suya,
        porque son otra magnitud.
      · Fila Total abajo: el total por área y el general, que el Mapa
        tenía y la tabla no.
      · Filas por |total de familia|, de mayor a menor: arriba lo que pesa.

    FILTROS PROPIOS (2026-09-15, a pedido: "los tres filtros de fecha,
    familia y área, así como está el reporte de ajuste por familia"). Son
    los mismos de la Cascada: `_comun.estado_filtros_vista` los resuelve y
    `render_filtros_vista` los dibuja, así que abren igual — último corte,
    las cinco familias de `FAMILIAS_DE_ENTRADA`, todas las áreas que
    movieron algo. `df` llega SIN los chips Área/Familia de arriba de la
    pila (los sigue usando Distribución) — filtrar por los dos lados dejaba
    la vista mostrando la intersección de dos compartimentos con uno solo
    visible.
    """
    if not col_familia or not col_area:
        st.info("Se necesitan columnas de familia y área para esta tabla.")
        return

    st.markdown(f"<style>{css_filtros_vista('hm_ctrl_', 'hm_corte_')}</style>",
                unsafe_allow_html=True)

    # ── ESTADO PRIMERO, WIDGETS DESPUES ──────────────────────────────────
    # El corte sale de `df_full` y no del `df` que llega recortado por la
    # franja: con el df recortado, elegir un corte dejaría la lista con ese
    # único corte y no habría forma de volver a los otros. Ver el docstring
    # de `estado_filtros_vista`.
    _est = estado_filtros_vista(
        df, df_full, col_fecha, col_familia, col_area, col_ajuste_val,
        k_corte=_K_CORTE, k_familia=_K_FAMILIA, k_area=_K_AREA)
    df = _est["d"]

    # ── Los tres filtros + Modo, en UNA fila. Hasta el 2026-09-18 la fila
    #    llevaba también el selector de Vista (Mapa/Flujo/Tabla) y los
    #    anchos estaban medidos al píxel para que entraran los cinco a
    #    1024px (el Modo pide 256 y envuelve a dos líneas si no los tiene).
    #    Sin la Vista sobran ~200px: a 1024 las columnas salen 156 / 156 /
    #    156 / 342. La cuarta columna existe aunque no haya Modo, para que
    #    los triggers no se estiren a un tercio de la fila cada uno. ───────
    _hay_valorizado = bool(col_valorizado and col_valorizado in df.columns)
    # columnas-internas: los tres filtros + Modo, en fila
    _cols_ctrl = st.columns([1.0, 1.0, 1.0, 2.2])
    render_filtros_vista(
        [_c.container(key=_k) for _c, _k in zip(_cols_ctrl, _K_CTRL)], _est)

    _modo_val = False
    if _hay_valorizado:
        with _cols_ctrl[3]:
            _modo = st.pills(
                "Modo mapa de calor", ["Ajuste Valorizado", "Valorizado Total"],
                default="Ajuste Valorizado", key="hm_ajuste_modo",
                label_visibility="collapsed",
            ) or "Ajuste Valorizado"
            _modo_val = (_modo == "Valorizado Total")
    col_metrica = col_valorizado if _modo_val else col_ajuste_val

    # El aviso de vacío va DESPUÉS de los controles, nunca antes: si no,
    # un filtro que deja la vista sin filas se lleva puesto el control que
    # lo deshace — el callejón sin salida de la Cascada.
    if df is None or df.empty:
        st.info("No hay datos para esta tabla con estos filtros.")
        return

    pivot = df.pivot_table(
        index=col_familia, columns=col_area,
        values=col_metrica, aggfunc="sum", fill_value=0,
    )
    if pivot.empty:
        st.info("No hay datos para esta tabla en el rango seleccionado.")
        return
    # Qué celdas tienen registros: una celda en 0 CON registros (faltantes
    # y sobrantes que se cancelan) abre su detalle; una sin registros no
    # tiene nada que abrir y va vacía, sin botón.
    _n_reg = df.groupby([col_familia, col_area]).size()

    _areas = pivot.columns.tolist()
    _tot_fam = pivot.sum(axis=1)
    _tot_fam = _tot_fam.reindex(_tot_fam.abs().sort_values(ascending=False).index)
    _fams = _tot_fam.index.tolist()
    _tot_area = pivot.sum(axis=0)
    _tot_gral = float(pivot.values.sum())
    _max_celda = float(abs(pivot.values).max()) or 1.0
    _max_tot_fam = float(_tot_fam.abs().max()) or 1.0
    _max_tot_area = float(_tot_area.abs().max()) or 1.0

    _titulo_metrica = "Valorizado Total" if _modo_val else "Ajuste Valorizado"
    _spark = _tendencias(df, df_full, col_fecha, col_familia, col_area,
                         col_metrica)

    # ── FOCO INICIAL: la vista abre con el detalle de ALIMENTOS × Almacén
    #    Central ya desplegado. La AUSENCIA de la clave —no su valor None—
    #    es la marca de "nadie tocó todavía": el callback SIEMPRE la escribe
    #    (una celda o None), así que cerrar el detalle la deja en None y no
    #    se re-siembra. Es el mismo distingo de dos "sin foco" que el
    #    `_tocado` del foco sembrado de «Vs año pasado» (CLAUDE.md), acá con
    #    la presencia de la clave de testigo —que se puede porque este foco
    #    ES el estado, no el espejo de una grilla de AG Grid—. Se siembra una
    #    sola vez, igual que las familias por defecto (`sembrar_seleccion`).
    if _K_FOCO not in st.session_state:
        st.session_state[_K_FOCO] = _foco_inicial(_fams, _areas, _n_reg)

    _foco = st.session_state.get(_K_FOCO)
    if _foco is not None and (_foco[0] not in _fams or _foco[1] not in _areas):
        _foco = None
        st.session_state[_K_FOCO] = None

    # ── CSS de la grilla. Tiene que leerse como TABLA y no como una pila
    #    de tarjetas: sin el gap de 16px de Streamlit —ni entre filas ni
    #    entre columnas— y con las líneas del cuadriculado puestas a mano
    #    (el `<table>` de markdown de la tabla vieja las traía del CSS
    #    interno de Streamlit; una grilla de `st.columns` no trae ninguna).
    #    La columna de nombres va a ancho FIJO y las de dato con un piso:
    #    sin piso, `st.columns` las encoge hasta que el monto envuelve a
    #    dos líneas y la fila se escalona. Lo que no entra se scrollea en X
    #    (`overflow-x`), como hacía el Mapa. ───────────────────────────────
    _css = [
        f'.st-key-hm_tabla[class*="stVerticalBlock"] {{ gap: 0 !important; '
        f'overflow-x: auto !important; border: 1px solid {GRIS_BORDE}; '
        f'border-bottom: none; }}',
        f'.st-key-hm_tabla [data-testid="stHorizontalBlock"] {{ gap: 0 '
        f'!important; flex-wrap: nowrap !important; border-bottom: 1px '
        f'solid {GRIS_BORDE}; }}',
        '.st-key-hm_tabla [data-testid="stColumn"] { padding: 2px 4px '
        '!important; }',
        # EL CORTE DE LA FILA TOTAL. Streamlit le pone `margin-bottom:
        # -16px` a todo `stMarkdownContainer` (compensa el margen de su
        # `<p>`), así que un `<div>` de 24px en markdown cuenta como 8. Una
        # fila de botones no lo nota —el botón manda—, pero la fila Total
        # es TODA markdown: medía 13px con 26 de contenido, y el
        # `overflow-x: auto` de la grilla (que vuelve `auto` también el eje
        # Y) recortaba lo que sobraba. Era el mismo corte que se reportó
        # del Mapa, con captura. Es la #162 mordiendo por tercera vez;
        # medido 2026-09-18, regla #468.
        '.st-key-hm_tabla [data-testid="stMarkdownContainer"] { '
        'margin-bottom: 0 !important; }',
        '.st-key-hm_tabla [data-testid="stHorizontalBlock"] '
        '> [data-testid="stColumn"]:first-child { flex: 0 0 170px '
        '!important; max-width: 170px !important; min-width: 170px '
        '!important; }',
        f'.st-key-hm_tabla [data-testid="stHorizontalBlock"] '
        f'> [data-testid="stColumn"]:not(:first-child) {{ flex: 1 0 88px '
        f'!important; min-width: 88px !important; border-left: 1px solid '
        f'{GRIS_BORDE}; }}',
        # El botón de una celda de dato: transparente, del alto de la fila,
        # con el monto a la izquierda. La barra es su `::before` —con el
        # largo y el color que le pone cada celda en `--hm-pct` y
        # `--hm-barra`— y el texto va por encima (`z-index`).
        f'.st-key-hm_tabla button {{ position: relative !important; '
        f'overflow: hidden !important; background: transparent !important; '
        f'border: 1px solid transparent !important; border-radius: 4px '
        f'!important; box-shadow: none !important; min-height: '
        f'{_ALTO_CELDA}px !important; height: {_ALTO_CELDA}px !important; '
        f'padding: 0 6px !important; justify-content: flex-start '
        f'!important; }}',
        f'.st-key-hm_tabla button:hover {{ border-color: {ACENTO} '
        f'!important; background: transparent !important; }}',
        '.st-key-hm_tabla button::before { content: ""; position: absolute; '
        'left: 0; top: 2px; bottom: 2px; width: var(--hm-pct, 0%); '
        'background: var(--hm-barra, transparent); border-radius: 4px; }',
        '.st-key-hm_tabla button > div { position: relative; z-index: 1; }',
        # El texto del botón vive en un <p> con su propio font-size (regla
        # #68): sin esto las celdas salen en los 14px de Streamlit.
        # El monto va a la IZQUIERDA, donde arranca su barra. El
        # `justify-content` del botón no alcanza: el <div> del label ocupa
        # todo el ancho y el <p> centraba adentro.
        '.st-key-hm_tabla button p { font-size: 11px !important; '
        'font-weight: 600 !important; line-height: 1 !important; margin: 0 '
        '!important; color: inherit !important; text-align: left '
        '!important; white-space: nowrap; '
        'font-variant-numeric: tabular-nums; }',
        # `estilos/_00_base.py` pone la fuente del proyecto SIN !important y
        # el CSS de markdown de Streamlit le gana: los nombres y los Total
        # (markdown) salían en Source Sans y los montos (botones) no.
        '.st-key-chartcard_heatmap * { font-family: "DM Sans", "Inter", '
        '-apple-system, BlinkMacSystemFont, sans-serif !important; }',
    ]

    def _rotulo(texto, color, peso=500, tam=11.5, titulo=""):
        _t = f" title='{titulo}'" if titulo else ""
        return (
            f"<div style='font-size:{tam}px;font-weight:{peso};color:{color};"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
            f"line-height:{_ALTO_CELDA}px;padding-left:4px'{_t}>{texto}</div>")

    with _card("heatmap", f"{_titulo_metrica} por familia y área"):
        with st.container(key="hm_tabla"):
            # Cabecera: los nombres de área no son clickeables.
            # columnas-internas: nombre + una por área + Total (anchos por CSS)
            _cols_h = st.columns(len(_areas) + 2, vertical_alignment="center")
            with _cols_h[0]:
                # Un `<div>`, no un "&nbsp;" pelado: eso es un `<p>`, con
                # su margen de 16px, y la cabecera medía 47 en vez de 29.
                st.markdown(_rotulo("&nbsp;", GRIS_TEXTO_SUAVE),
                            unsafe_allow_html=True)
            for _j, _area in enumerate(_areas):
                with _cols_h[_j + 1]:
                    st.markdown(_rotulo(_area, GRIS_TEXTO_SUAVE, 600, 10,
                                        _area), unsafe_allow_html=True)
            with _cols_h[-1]:
                st.markdown(_rotulo("Total", ACENTO_TEXTO_OSCURO, 700, 10),
                            unsafe_allow_html=True)

            for _i, _fam in enumerate(_fams):
                # columnas-internas: nombre + una por área + Total (anchos por CSS)
                _cols_r = st.columns(len(_areas) + 2,
                                     vertical_alignment="center")
                with _cols_r[0]:
                    st.markdown(_rotulo(_fam, TEXTO_PRINCIPAL, titulo=_fam),
                                unsafe_allow_html=True)
                for _j, _area in enumerate(_areas):
                    with _cols_r[_j + 1]:
                        if not _n_reg.get((_fam, _area), 0):
                            st.markdown(
                                f"<div style='height:{_ALTO_CELDA}px'></div>",
                                unsafe_allow_html=True)
                            continue
                        _v = float(pivot.loc[_fam, _area])
                        _cero = abs(_v) < 0.5
                        _key = f"hm_tb_{_i}_{_j}"
                        _bar, _txt = _paleta(_v, _modo_val)
                        _es_foco = (_foco == (_fam, _area))
                        _css.append(
                            f'.st-key-hm_tabla .st-key-{_key} button {{ '
                            f'--hm-pct: {0 if _cero else _pct(_v, _max_celda):.1f}%; '
                            f'--hm-barra: {_rgba(_bar)}; color: {_txt} '
                            f'!important;'
                            # 2px y no 1.5: con pantalla de densidad 1 el
                            # navegador redondea a 1, y el foco se confundía
                            # con el borde del :hover (medido).
                            + (f' border: 2px solid {ACENTO} !important;'
                               if _es_foco else '')
                            + ' }')
                        # En cero no hay nada que leer (reportado sobre el
                        # Mapa, 2026-08-09): la celda sigue clickeable, sólo
                        # se le vacía la etiqueta.
                        st.button(
                            " " if _cero else f"S/ {_v:,.0f}", key=_key,
                            help=(f"{_fam} × {_area}: S/ {_v:,.0f}"
                                  + _spark.get((_fam, _area), "")),
                            on_click=_alternar_foco, args=((_fam, _area),),
                            width="stretch")
                with _cols_r[-1]:
                    st.markdown(
                        _celda_total_html(float(_tot_fam.loc[_fam]),
                                          _max_tot_fam, _modo_val),
                        unsafe_allow_html=True)

            # Fila Total: por área y el general, no clickeables.
            # columnas-internas: nombre + una por área + Total (anchos por CSS)
            _cols_t = st.columns(len(_areas) + 2, vertical_alignment="center")
            with _cols_t[0]:
                st.markdown(_rotulo("Total", ACENTO_TEXTO_OSCURO, 700),
                            unsafe_allow_html=True)
            for _j, _area in enumerate(_areas):
                with _cols_t[_j + 1]:
                    st.markdown(
                        _celda_total_html(float(_tot_area.loc[_area]),
                                          _max_tot_area, _modo_val),
                        unsafe_allow_html=True)
            with _cols_t[-1]:
                st.markdown(
                    f"<div style='background:{ACENTO};"
                    f"border-radius:6px;height:{_ALTO_CELDA}px;"
                    f"line-height:{_ALTO_CELDA}px;padding-left:9px;"
                    f"font-size:11px;font-weight:700;color:{BLANCO};"
                    f"font-variant-numeric:tabular-nums;white-space:nowrap'>"
                    f"S/ {_tot_gral:,.0f}</div>",
                    unsafe_allow_html=True)

            # CSS de todas las celdas en UN solo bloque (Streamlit emite un
            # <style> por st.markdown: más liviano que uno por celda).
            st.markdown(f"<style>{''.join(_css)}</style>",
                        unsafe_allow_html=True)

    if _foco is not None:
        _detalle_celda(df, pivot, _foco, col_familia, col_area, col_producto,
                       col_metrica, col_cantidad, col_unidad, _modo_val)


def _detalle_celda(df, pivot, foco, col_familia, col_area, col_producto,
                   col_metrica, col_cantidad, col_unidad, modo_val):
    """El detalle de la celda en foco, debajo de la tarjeta: encabezado
    (familia × área, monto, registros) y el ranking de sus productos —
    Faltantes | Sobrantes en Ajuste, un solo Top en Valorizado Total, que
    no tiene signo que separar. Con los colores de la tabla: el detalle es
    la continuación del clic, no otra vista."""
    _fam_sel, _area_sel = foco
    _val_sel = float(pivot.loc[_fam_sel, _area_sel])
    _det = df[
        (df[col_familia].astype(str) == str(_fam_sel)) &
        (df[col_area].astype(str) == str(_area_sel))
    ]

    _color_total = _paleta(_val_sel, modo_val)[1]
    st.markdown(
        f"**{_fam_sel}** × **{_area_sel}** · "
        f"<span style='color:{_color_total};font-weight:600'>"
        f"S/ {_val_sel:,.0f}</span> · "
        f"{len(_det)} registros",
        unsafe_allow_html=True,
    )

    if not (col_producto and col_producto in _det.columns):
        st.caption("No hay columna de producto para desglosar.")
        return

    # cantidad/unidad al lado del monto — mismo criterio que ya usa el
    # drill de la Cascada (_filas_split_html): sum() para cantidad, "first"
    # para unidad (constante por producto, no hay nada que sumar).
    _has_cant = bool(col_cantidad and col_cantidad in _det.columns)
    _has_um = bool(col_unidad and col_unidad in _det.columns)
    _agg = {col_metrica: "sum"}
    if _has_cant:
        _agg[col_cantidad] = "sum"
    if _has_um:
        _agg[col_unidad] = "first"
    _sub_prod = _det.groupby(col_producto, as_index=False).agg(_agg)
    _sub_prod["_abs"] = _sub_prod[col_metrica].abs()
    _sub_prod = _sub_prod.sort_values("_abs", ascending=False).head(30)

    # UNA GRILLA POR LADO, como la Cascada (regla #483): antes eran listas
    # HTML con barritas; ahora son las MISMAS AgGrid de desglose
    # (`renderizar_desglose_ajuste`), con una barra de severidad detrás del
    # monto. «Se vea como tabla, similar a la de la Cascada, pero con barra
    # de color para la severidad» (a pedido, 2026-09-21).
    def _tp_lado(_df_d):
        """DataFrame de una grilla de desglose: producto · (cantidad) ·
        valor. `__barpct` es el largo de la barra, 0-100 contra el máximo
        absoluto del lado, con piso de 4 para que un monto chico no
        desaparezca (mismo criterio que las celdas de la tabla, `_pct`).
        `__um` viaja oculta para que `Cantidad` muestre la unidad y siga
        ordenando por el número."""
        tp = pd.DataFrame({
            "producto": _df_d[col_producto].astype(str),
            "valor": pd.to_numeric(_df_d[col_metrica],
                                   errors="coerce").fillna(0.0),
        })
        if _has_cant:
            tp["cantidad"] = pd.to_numeric(_df_d[col_cantidad],
                                           errors="coerce").fillna(0.0)
            _um = (_df_d[col_unidad].astype(str).str.strip() if _has_um
                   else pd.Series("", index=_df_d.index))
            tp["__um"] = _um.mask(_um.str.lower().isin(("nan", "none")),
                                  "").values
        _mx = float(tp["valor"].abs().max()) or 1.0
        tp["__barpct"] = (tp["valor"].abs() / _mx * 100).clip(lower=4)
        tp["__sel"] = False
        return tp

    def _cols():
        _c = [("producto", "Producto", "nombre")]
        if _has_cant:
            _c.append(("cantidad", "Cantidad", "cantidad"))
        _c.append(("valor", "Valor", "total"))
        return _c

    def _titulo(texto, color):
        st.markdown(
            f"<div style='font-size:9px;font-weight:600;"
            f"color:{color};letter-spacing:.08em;"
            f"text-transform:uppercase;margin:4px 0 2px 0'>"
            f"{texto}</div>",
            unsafe_allow_html=True,
        )

    def _grilla(_df_d, lado, color_barra, color_texto):
        tp = _tp_lado(_df_d)
        _key = "hm_det_" + lado + "_" + _clave(
            _fam_sel, _area_sel, col_metrica, len(tp))
        _alto = _alto_grilla(min(8, max(1, len(tp))))
        _atar_alto(_key, _alto)
        renderizar_desglose_ajuste(
            tp, _cols(), _alto, _key, movil=_es_movil(),
            barra=("valor", _rgba(color_barra), color_texto))

    if modo_val:
        _titulo("Top productos", _AZUL_TEXTO)
        _grilla(_sub_prod, "top", _AZUL_BARRA, _AZUL_TEXTO)
        return

    _neg = _sub_prod[_sub_prod[col_metrica] < 0].sort_values(
        col_metrica, ascending=True)
    _pos = _sub_prod[_sub_prod[col_metrica] > 0].sort_values(
        col_metrica, ascending=False)

    # columnas-internas: Faltantes | Sobrantes, mitad y mitad
    _pa, _pb = st.columns(2)
    with _pa:
        _titulo("Faltantes", AJUSTE_NEG_TEXTO)
        if _neg.empty:
            st.caption("Sin faltantes.")
        else:
            _grilla(_neg, "neg", AJUSTE_NEG, AJUSTE_NEG_TEXTO)
    with _pb:
        _titulo("Sobrantes", AJUSTE_POS_TEXTO)
        if _pos.empty:
            st.caption("Sin sobrantes.")
        else:
            _grilla(_pos, "pos", AJUSTE_POS, AJUSTE_POS_TEXTO)
