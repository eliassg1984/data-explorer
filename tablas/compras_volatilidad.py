"""tablas.compras_volatilidad - grilla AgGrid del ranking de insumos por
volatilidad (graficos/compras/volatilidad.py::_compras_volatilidad_drill).

Reemplaza a la versión anterior en `pandas.Styler` + `st.dataframe`: esa
combinación pinta bien el semáforo y la barra de Volatilidad, pero
`st.dataframe` (grid en canvas) no tiene forma de mostrar un tooltip por
celda -- ver arquitectura.md regla #130. AgGrid sí, vía `tooltipValueGetter`
(mismo mecanismo que ya usa `tablas/compras.py`).

Selección de fila SIN checkbox: a diferencia de `st.dataframe` con
`selection_mode="single-row"` (que fuerza un checkbox nativo en el grid,
sin parámetro para sacarlo -- confirmado en el bundle de Streamlit), AG
Grid con `use_checkbox=False` (el default) selecciona con un clic en
cualquier parte de la fila, sin checkbox visible.

`.selected_rows` de st_aggrid devuelve la fila por CONTENIDO (un dict con
todas sus columnas, incluidas las ocultas), no por índice -- por eso el
buscador de arriba puede filtrar sin ningún truco de key dinámica: no hay
un índice de fila que se pueda desalinear contra la lista filtrada.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import (
    ACENTO, ERROR, ERROR_FONDO, EXITO, EXITO_FONDO, GRIS_TEXTO,
    LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from tablas._config import _parchar_iconos
from tablas._css import _css_grid

# Ancho FIJO (no por longitud de header, como ajuste_pivote.py): el
# contenido de cada celda-semana es siempre corto ("+223.3%"), así que no
# hace falta ganchar el ancho al texto de la cabecera -- eso fue justo el
# bug reportado (autoSizeStrategy="fitGridWidth" estiraba las columnas
# para llenar el ancho disponible, y en una tarjeta ancha solo entraban 3
# de 8). Con ancho fijo y sin auto-fit, la cabecera larga ("29 Jun - 5
# Jul") envuelve a dos líneas (wrapHeaderText/autoHeaderHeight ya
# activos) en vez de ensanchar la columna.
_ANCHO_COL_SEMANA = 84
_ANCHO_COL_VOL = 92

_FMT_PCT = JsCode("""
    function(params) {
        if (params.value === null || params.value === undefined) return '';
        var v = Number(params.value);
        var sign = v >= 0 ? '+' : '\\u2212';
        return sign + Math.abs(v).toFixed(1) + '%';
    }
""")

_FMT_1DEC = JsCode("""
    function(params) {
        return params.value == null ? '' : Number(params.value).toFixed(1);
    }
""")

_STYLE_DELTA = JsCode(f"""
    function(params) {{
        if (params.value === null || params.value === undefined) return {{color: '#c9c9d1'}};
        var v = Number(params.value);
        if (Math.abs(v) < 1) return {{color: '{GRIS_TEXTO}'}};
        if (v > 0) return {{backgroundColor: '{ERROR_FONDO}', color: '{ERROR}',
                            fontWeight: '600', borderRadius: '6px'}};
        return {{backgroundColor: '{EXITO_FONDO}', color: '{EXITO}',
                fontWeight: '600', borderRadius: '6px'}};
    }}
""")

_TOOLTIP_INSUMO = JsCode(
    "function(params){ return params.data ? params.data['__insumo_full'] : ''; }")


def _tooltip_delta(idx, label_prev, label_cur):
    """Cierre de la semana ANTERIOR → cierre de ESTA semana: las dos cifras
    que explican el % de la celda (el delta es cierre a cierre, no
    apertura/cierre de la MISMA semana -- eso ya lo muestra el candlestick
    de abajo al hacer clic en la fila)."""
    return JsCode(f"""
        function(params) {{
            var prev = params.data['__prev_{idx}'];
            var cur = params.data['__cur_{idx}'];
            if (prev == null || cur == null) return '';
            var fmt = function(v) {{
                return 'S/ ' + Number(v).toLocaleString('es-PE',
                    {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
            }};
            return '{label_prev}: ' + fmt(prev) + ' \\u2192 {label_cur}: ' + fmt(cur);
        }}
    """)


def _style_vol(max_vol):
    """Barra de volatilidad como gradiente CSS de dos colores, cortado en
    `pct`% -- mismo truco que el `_sty_vol_bar` de Styler que reemplaza,
    ahora como `cellStyle` (patrón ya usado por `ajuste_pivote.py`/
    `compras.py`, ver arquitectura.md)."""
    return JsCode(f"""
        function(params) {{
            if (params.value === null || params.value === undefined) return {{}};
            var pct = Math.round(Number(params.value) / {max_vol} * 100);
            return {{
                background: 'linear-gradient(90deg, {ACENTO} ' + pct + '%, {LAVANDA_FONDO} ' + pct + '%)',
                fontWeight: '600'
            }};
        }}
    """)


def renderizar_ranking_volatilidad(tv, cols_sem, labels_prev, altura, key):
    """`tv`: columnas Insumo, __insumo_full (oculta, nombre sin truncar),
    una columna FLOAT por semana (nombrada con su etiqueta de fecha,
    p.ej. "15-21 Jun"), __prev_i/__cur_i por semana (ocultas, precio de
    cierre anterior/actual -- alimentan el tooltip) y Volatilidad.
    `cols_sem` y `labels_prev` van pareados por índice: `labels_prev[i]`
    es la etiqueta de la semana ANTERIOR a `cols_sem[i]`.

    Devuelve el nombre completo del insumo de la fila clickeada en ESTA
    corrida (`__insumo_full`), o None si no hubo clic."""
    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(
        resizable=False, sortable=False, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=True, autoHeaderHeight=True,
    )
    gb.configure_column("Insumo", pinned="left", minWidth=170,
                        tooltipValueGetter=_TOOLTIP_INSUMO)
    gb.configure_column("__insumo_full", hide=True)

    for i, (col, prev_label) in enumerate(zip(cols_sem, labels_prev)):
        gb.configure_column(
            col, type=["numericColumn"], width=_ANCHO_COL_SEMANA,
            valueFormatter=_FMT_PCT, cellStyle=_STYLE_DELTA,
            tooltipValueGetter=_tooltip_delta(i, prev_label, col),
        )
        gb.configure_column(f"__prev_{i}", hide=True)
        gb.configure_column(f"__cur_{i}", hide=True)

    max_vol = (max((float(v) for v in tv["Volatilidad"]), default=0.0) or 1.0)
    gb.configure_column("Volatilidad", type=["numericColumn"], width=_ANCHO_COL_VOL,
                        valueFormatter=_FMT_1DEC, cellStyle=_style_vol(max_vol))

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(rowHeight=30, headerHeight=32, tooltipShowDelay=200)
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # cuadrados negros en Chrome < 120: arquitectura.md #159

    custom_css = dict(_css_grid(13))
    custom_css[".ag-tooltip"] = {
        "background-color": f"{TEXTO_PRINCIPAL} !important",
        "color": "#ffffff !important",
        "border": "none !important",
        "border-radius": "6px !important",
        "padding": "6px 10px !important",
        "font-size": "12px !important",
        "box-shadow": "0 6px 20px rgba(0,0,0,0.25) !important",
    }

    resp = AgGrid(
        tv, gridOptions=grid_options, height=altura, theme="material",
        custom_css=custom_css, allow_unsafe_jscode=True, key=key,
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__insumo_full"])
    return None
