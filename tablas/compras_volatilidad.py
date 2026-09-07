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
# contenido de cada celda-semana es corto y ACOTADO, así que no hace falta
# ganchar el ancho al texto de la cabecera -- eso fue justo el bug
# reportado (autoSizeStrategy="fitGridWidth" estiraba las columnas para
# llenar el ancho disponible, y en una tarjeta ancha solo entraban 3 de
# 8). Con ancho fijo y sin auto-fit, la cabecera larga ("29 Jun - 5 Jul")
# envuelve a dos líneas (wrapHeaderText/autoHeaderHeight ya activos) en
# vez de ensanchar la columna.
#
# 84 -> 98 el 2026-09-06, al bajar la segunda línea con los dos precios.
# OJO CON LO QUE ESTE NÚMERO ES: NO es el ancho final. Medido en el
# navegador (viewport 1358, rail puesto) el grid recibe 850px y los
# reparte -- «Insumo» se queda con su `minWidth` y el resto se escala
# proporcionalmente, así que 170/98/92 sale en pantalla como 175/85/80.
# O sea que acá se elige el REPARTO, no los píxeles: subir esto le saca a
# «Volatilidad», no al scroll. Lo que de verdad le hizo sitio a la segunda
# línea fue el padding de la celda (ver `_PAD_X_SEMANA`).
_ANCHO_COL_SEMANA = 98
_ANCHO_COL_VOL = 92

# Alto de fila: DOS lineas donde hubo variacion (el % arriba, los dos
# precios abajo). Sale de la suma medida -- 13px de la primera linea y 9.5
# de la segunda, las dos a `line-height: 1.15`, son 26px de texto -- mas el
# aire de la celda. No se usa `getRowHeight` para dejar en 30 las filas sin
# segunda linea (el truco de `documentos_sunat.py`, donde 291 de 326 filas
# no la tienen) porque aca es al reves: la tabla esta ORDENADA por
# volatilidad, asi que una fila sin ninguna variacion es la excepcion y
# alternar dos altos en una grilla de 7 columnas se lee como un temblor.
ALTO_FILA = 40
_TAM_PRECIOS = "9.5px"

# Sin signo cuando redondea a cero: un "+0.0%" dice "subio" con un
# numero que dice "no cambio". Mismo umbral que `_EPS_CERO`.
_FMT_PCT = JsCode("""
    function(params) {
        if (params.value === null || params.value === undefined) return '';
        var v = Number(params.value);
        if (Math.abs(v) < 0.05) return '0.0%';
        var sign = v > 0 ? '+' : '\\u2212';
        return sign + Math.abs(v).toFixed(1) + '%';
    }
""")

_FMT_1DEC = JsCode("""
    function(params) {
        return params.value == null ? '' : Number(params.value).toFixed(1);
    }
""")

# Un cambio que redondea a "0.0%" es RUIDO: ocupa el mismo ancho que un
# +12.4% y compite por la mirada en una tabla donde lo que importa son los
# saltos. Se dibuja mas chico (y mas claro) para que la fila se lea como
# "aca no paso nada" sin sacar el dato. El umbral es el del formateo
# (`toFixed(1)`), no uno propio: lo que se ve "0.0%" es exactamente lo que
# se achica -- si no, la tabla mostraria dos ceros de tamanos distintos.
_EPS_CERO = 0.05
_TAM_CERO = "11px"

# El padding horizontal de la celda, propio de las columnas-semana. El del
# tema material son 15px POR LADO, o sea 30 de los 85 que mide la columna:
# quedaban 55px útiles y la segunda línea de precios mide entre 56 y 69.
# Medido antes de tocar nada -- 46 de las 65 celdas con dos líneas salían
# recortadas, y el corte no se ve como un error, se ve como un precio
# distinto ("110.17 → 169.4"). Con 6px quedan 73 útiles contra los 69 del
# peor caso real (S/ 169.41, el precio más alto del rango medido).
#
# Va en el `cellStyle` y no en el `custom_css` del grid a propósito: ahí
# sería `.ag-cell` a secas y le apretaría también al nombre del insumo,
# que no lo pidió. Es el aviso de CLAUDE.md sobre reglas colgadas del
# contenedor, en su versión AgGrid.
_PAD_X_SEMANA = "0 6px"

_MIN_ANCHO_PRECIOS = 81
"""Ancho REAL de columna a partir del cual la celda dibuja su segunda línea.

69 del peor caso medido ("S/ 169.41", el precio más alto del rango) + los 12
de `_PAD_X_SEMANA`. Debajo de eso la línea no se dibuja en vez de recortarse:
ver el comentario dentro de `_RENDER_DELTA`.

No es el `width` declarado sino `getActualWidth()`, que es otra cosa — AG Grid
escala las columnas para llenar el grid, así que el ancho de esta columna
depende del ancho de la ventana. Medido el 2026-09-07 con el drill al lado:
~55px en una ventana de 1440, ~81 en una de 1800, ~139 en una de 2560. O sea
que la línea aparece sola cuando hay monitor para ella."""

_STYLE_DELTA = JsCode(f"""
    function(params) {{
        var base = {{padding: '{_PAD_X_SEMANA}'}};
        if (params.value === null || params.value === undefined) {{
            return Object.assign(base, {{color: '#c9c9d1'}});
        }}
        var v = Number(params.value);
        if (Math.abs(v) < {_EPS_CERO}) {{
            return Object.assign(base, {{color: '#c9c9d1',
                                         fontSize: '{_TAM_CERO}'}});
        }}
        if (Math.abs(v) < 1) return Object.assign(base, {{color: '{GRIS_TEXTO}'}});
        if (v > 0) return Object.assign(base, {{
            backgroundColor: '{ERROR_FONDO}', color: '{ERROR}',
            fontWeight: '600', borderRadius: '6px'}});
        return Object.assign(base, {{
            backgroundColor: '{EXITO_FONDO}', color: '{EXITO}',
            fontWeight: '600', borderRadius: '6px'}});
    }}
""")

# LOS DOS PRECIOS, DEBAJO DEL %: sin ellos la celda dice cuanto se movio y
# no desde donde -- "+12.4%" sobre 8.50 y sobre 85.00 son la misma celda, y
# la decision de compra no es la misma. Estaban en el tooltip desde que la
# tabla es AgGrid; a pedido (2026-09-06) pasan a estar VISIBLES, que es lo
# unico que se puede leer de un golpe de vista sobre la grilla entera.
#
# Solo donde HAY variacion, y con el mismo umbral que decide el resto
# (`_EPS_CERO`): en una celda que dice "0.0%" los dos precios serian el
# mismo numero repetido. Es la misma doctrina que la segunda linea de
# `documentos_sunat.py::_JS_IMPORTE` -- aparece cuando dice algo.
#
# `class` con `init`/`getGui` y no una funcion que devuelva HTML: en
# `st_aggrid` el atajo vanilla no pinta (se ve como texto escapado, o
# revienta con React #31). Ver `arquitectura.md` regla #25.
#
# El indice de la semana entra por `cellRendererParams` y NO interpolado en
# el codigo: asi es UN solo `JsCode` para las siete columnas en vez de
# siete, y el coste de `JsCode.__init__` es cuadratico en el largo del
# texto (regla #226). Los precios se leen de `params.data`, que es la
# misma fila -- no hace falta `api.getValue`, que en esta version de AG
# Grid no existe.
_RENDER_DELTA = JsCode("""
class DeltaCelda {
    init(p) {
        this.eGui = document.createElement('div');
        var g = this.eGui.style;
        g.display = 'flex';
        g.flexDirection = 'column';
        g.alignItems = 'flex-end';
        g.justifyContent = 'center';
        g.lineHeight = '1.15';
        g.height = '100%';
        var a = document.createElement('div');
        a.textContent = p.valueFormatted == null ? '' : p.valueFormatted;
        this.eGui.appendChild(a);
        if (p.value == null || Math.abs(Number(p.value)) < __EPS__) return;
        var d = p.data || {};
        var prev = d['__prev_' + p.idx];
        var cur = d['__cur_' + p.idx];
        if (prev == null || cur == null) return;
        var b = document.createElement('div');
        b.textContent = this.num(prev) + '\u2009\u2192\u2009' + this.num(cur);
        b.style.fontSize = '__TAM__';
        b.style.fontWeight = '400';
        b.style.opacity = '0.78';
        // Que un precio mas ancho de lo previsto FALLE VISIBLE. Sin esto
        // el `overflow: hidden` de la celda corta el texto por la mitad y
        // "169.41" se lee "169.4", que no parece un recorte: parece otro
        // precio. Medido el 2026-09-06 sobre el parquet real, el peor caso
        // entra con 2px de sobra -- o sea que el margen es real pero flaco.
        b.style.maxWidth = '100%';
        b.style.overflow = 'hidden';
        b.style.textOverflow = 'ellipsis';
        b.style.whiteSpace = 'nowrap';
        // SOLO DONDE ENTRA. Con el drill al lado del ranking (2026-09-07)
        // la columna-semana pasa de ~85px a ~50, y ahi "110.17 -> 169.41"
        // no cabe: el `text-overflow` de arriba lo cortaria en
        // "110.17 -> 16..." y un precio recortado no parece un recorte,
        // parece otro precio. Los dos numeros siguen en el tooltip, que es
        // de donde vinieron hasta el 2026-09-06.
        //
        // SE MIDE DESPUES DEL LAYOUT, y eso es el arreglo de un intento
        // fallido del mismo dia: `p.column.getActualWidth()` leido aca
        // devuelve el ancho DECLARADO (98), porque AG Grid escala las
        // columnas para llenar el grid DESPUES de construir las celdas.
        // El guard daba verde siempre y la linea salia igual, recortada.
        // `p.eGridCell.clientWidth` dentro de un rAF ya ve el ancho real.
        //
        // Se agrega DENTRO del rAF en vez de agregarlo y esconderlo: asi
        // no hay un frame con el texto puesto. Sin `eGridCell` (no deberia
        // pasar) se dibuja, que es el comportamiento de antes.
        var caja = this.eGui;
        requestAnimationFrame(function () {
            var w = p.eGridCell ? p.eGridCell.clientWidth : 0;
            if (!w || w >= __MINANCHO__) caja.appendChild(b);
        });
    }
    num(v) {
        return Number(v).toLocaleString('es-PE',
            {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
    getGui() { return this.eGui; }
}
""".replace("__EPS__", str(_EPS_CERO)).replace("__TAM__", _TAM_PRECIOS)
   .replace("__MINANCHO__", str(_MIN_ANCHO_PRECIOS)))
"""La celda de una semana: el % arriba y, si hubo movimiento, el cierre
anterior y el nuevo debajo.

Sin simbolo de moneda a proposito, y no es una suposicion de las que
advierte la regla #240: el drill filtra `TIPO_MONEDA` a soles antes de
calcular nada, asi que la columna no puede traer otra cosa. El "S/" lo
ponen el tooltip y la tarjeta de abajo, donde hay ancho; aca son 20px
repetidos siete veces por fila para decir lo mismo."""


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


def renderizar_ranking_volatilidad(tv, cols_sem, labels_prev, headers, altura,
                                   key):
    """`tv`: columnas Insumo, __insumo_full (oculta, nombre sin truncar),
    una columna FLOAT por semana (nombrada con su etiqueta de fecha,
    p.ej. "15-21 Jun"), __prev_i/__cur_i por semana (ocultas, precio de
    cierre anterior/actual -- alimentan el tooltip) y Volatilidad.
    `cols_sem`, `labels_prev` y `headers` van pareados por índice:
    `labels_prev[i]` es la etiqueta de la semana ANTERIOR a `cols_sem[i]`, y
    `headers[i]` el rótulo CORTO que se dibuja en la cabecera.

    El rótulo de la cabecera es otro texto que el nombre de la columna a
    propósito: el nombre tiene que ser único (es la clave del DataFrame y la
    del tooltip) y el rótulo tiene que entrar en ~50px. Ver
    `volatilidad.py::_vol_fmt_semana_corta`.

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

    for i, (col, prev_label, hdr) in enumerate(zip(cols_sem, labels_prev,
                                                   headers)):
        gb.configure_column(
            col, header_name=hdr, type=["numericColumn"],
            width=_ANCHO_COL_SEMANA,
            valueFormatter=_FMT_PCT, cellStyle=_STYLE_DELTA,
            cellRenderer=_RENDER_DELTA, cellRendererParams={"idx": i},
            tooltipValueGetter=_tooltip_delta(i, prev_label, col),
        )
        gb.configure_column(f"__prev_{i}", hide=True)
        gb.configure_column(f"__cur_{i}", hide=True)

    max_vol = (max((float(v) for v in tv["Volatilidad"]), default=0.0) or 1.0)
    gb.configure_column("Volatilidad", type=["numericColumn"], width=_ANCHO_COL_VOL,
                        valueFormatter=_FMT_1DEC, cellStyle=_style_vol(max_vol))

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(rowHeight=ALTO_FILA, headerHeight=32,
                              tooltipShowDelay=200)
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
