"""tablas.compras_semanal - las dos grillas del detalle de «Compra por
período» (graficos/compras/semanal.py): los DOCUMENTOS del período en foco
a la izquierda y, al costado, las LÍNEAS del documento elegido.

Nacieron el 2026-09-14, a pedido: «que la tabla de abajo se divida en dos,
una que muestre el documento, y al hacer clic muestre en otra tabla del
costado el detalle; creo que tiene que ser aggrid». Hasta ese día era UN
`st.dataframe` con todas las líneas del período mezcladas —una semana
mediana son 267 líneas de 96 documentos—, y la columna «Documento», que
cambiaba casi en cada fila, era la única forma de saber de dónde salía cada
una. Partida, la de la izquierda contesta «qué compré esta semana» con una
fila por compra, y la de la derecha «qué había en esa compra».

EL LOOK es el de las grillas de Volatilidad (`_css_look`, filas de
`ALTO_FILA`): su tabla de compras de la semana es la misma pregunta, y dos
tablas de compras con dos looks distintos en la misma página no se leen
como la misma cosa (regla #404). Las celdas llegan YA FORMATEADAS desde el
drill, como allá: ninguna de las dos se ordena, así que no hace falta que
el monto viaje como número.

LA FILA MARCADA NO ES LA SELECCIÓN DE AG GRID. La key de la grilla de
documentos lleva el documento elegido (la arma el drill), así que cada
cambio estrena grilla y ésta nace SIN selección: lo que se ve marcado es
una clase de fila que sale de `__sel`, un dato que viaja en la fila, con el
mismo look que una fila seleccionada. Dos cosas que salen de eso:

  · la grilla no puede contradecir al estado del drill, que también lo
    cambia un clic en el GRÁFICO (un punto de la serie es una compra);
  · cualquier selección que devuelva es un clic de verdad, nunca un resto
    de la corrida anterior — no hace falta recordar qué devolvió antes.

Ver regla #440.

2026-09-17 — FILA TOTAL FIJA en las dos (regla #454): `total=` es el dict de
esa fila, ya formateado como el resto. Va por `pinnedBottomRowData`, con la
paleta de cierre de las tablas-ranking (`JS_FILA_TOTAL`), y no participa de
la selección: las filas fijas no son parte del modelo de filas y AG Grid no
las selecciona (lo dice su documentación de «Row Pinning»; no se probó a
mano), así que un clic en el total no debería devolver nada — la fila no
trae `__compra` ni `__sel`.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import ACENTO, ACENTO_TEXTO_OSCURO, LAVANDA_CHIP, LAVANDA_FONDO
from tablas._config import _parchar_iconos
from tablas._css import _css_grid
# `_css_look` es privado de allá pero lo comparten ya TRES grillas —el
# ranking de Volatilidad, sus compras de la semana y estas dos—: el look de
# las tablas de compras es uno solo y vive en un solo sitio.
from tablas.compras_volatilidad import ALTO_FILA, _css_look

CROMO = 32 + 2
"""Alto de estas grillas que NO son filas: la cabecera (32) y los bordes (2),
los mismos de `compras_volatilidad.CROMO_SEMANA`. Sin barra horizontal: las
columnas se reparten el ancho de su mitad de la tarjeta."""

_PAD_X_CELDA = "8px"
"""Padding horizontal de celdas y cabeceras, el de las compras de la semana
de Volatilidad: el del tema material son 16 por lado, y en media tarjeta
cinco columnas se comerían 160px de aire."""

_CLASE_SEL = "sem-doc-sel"

_CLASE_FILA = JsCode(
    "function(p){ return p.data && p.data.__sel ? '" + _CLASE_SEL + "' : ''; }")
"""La fila del documento que muestra la tabla de al lado. Ver «LA FILA
MARCADA NO ES LA SELECCIÓN DE AG GRID» en el docstring del módulo."""

_AL_MONTAR = JsCode("""
    function(params) {
        var api = params.api;
        var ajustar = function () {
            try { api.sizeColumnsToFit(); } catch (e) {}
        };
        try {
            var caja = document.getElementById('gridContainer');
            if (caja && window.ResizeObserver) {
                new ResizeObserver(ajustar).observe(caja);
            }
        } catch (e) {}
        try { api.addEventListener('displayedColumnsChanged', ajustar); } catch (e) {}
        ajustar();
        // La fila marcada, A LA VISTA: la grilla se estrena en cada cambio de
        // documento (su key lo lleva), así que nace arriba de todo — y en una
        // semana de 90 compras la que se acaba de clickear puede ser la 40.
        setTimeout(function () {
            try {
                api.forEachNode(function (n) {
                    if (n.data && n.data.__sel) api.ensureNodeVisible(n, 'middle');
                });
            } catch (e) {}
        }, 0);
    }
""")
"""`sizeColumnsToFit` con un `ResizeObserver`, por lo mismo que
`compras_volatilidad._AL_MONTAR_SEMANA` (`colDef.flex` se congela si la
grilla se monta fuera de pantalla, y ésta vive en una `seccion_perezosa`),
más llevar a la vista la fila marcada. `ensureNodeVisible` y no una
selección: seleccionar desde acá mandaría un valor de vuelta a Python y
costaría una corrida entera del fragment por nada."""


JS_FILA_TOTAL = JsCode(
    "function(p){ if(p.node.rowPinned){ return {"
    f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
    f"'color':'{ACENTO_TEXTO_OSCURO}'"
    "}; } }")
"""La fila TOTAL con la paleta de cierre de las tablas-ranking
(`drill_tablas.tabla_ranking`). Vive acá y no en `ajuste_familias.py`, que
la tenía primero, por el mismo motivo que `_css`: ese módulo ya toma el look
de éste, y dos copias de la fila de cierre se separan al primer retoque."""


def _con_total(opciones, total):
    """Suma la fila TOTAL a `configure_grid_options`, si hay."""
    if total is not None:
        opciones.update(getRowStyle=JS_FILA_TOTAL, pinnedBottomRowData=[total])
    return opciones


def _css():
    """El CSS de las dos grillas: el look de Volatilidad más lo propio."""
    css = _css_look(_css_grid(13, cebra=False, cabecera_neutra=True))
    css[".ag-row .ag-cell, .ag-header-row .ag-header-cell"] = {
        "padding-left": f"{_PAD_X_CELDA} !important",
        "padding-right": f"{_PAD_X_CELDA} !important",
    }
    # Mismo par que en Volatilidad: el iframe lo estira `estilos/_80_cards.py`
    # y el div de adentro va acá, que es lo único que entra al iframe.
    css["#gridContainer"] = {"width": "100% !important"}
    # Sin el canal HORIZONTAL (medido en Volatilidad: Chrome lo dibuja aunque
    # no haya nada que deslizar y le roba el alto a la última fila). El
    # VERTICAL se queda: una semana trae hasta ~120 compras y la barra es lo
    # que dice que hay más abajo.
    css[".ag-body-horizontal-scroll"] = {"display": "none !important"}
    # La fila marcada y la recién clickeada, con el mismo look: la segunda es
    # la selección de AG Grid, que dura lo que tarda la corrida en estrenar
    # la grilla con la primera. La raya de 3px es la de la tabla de «Vs año
    # pasado» (`.ag-row-selected` de `tablas/compras_vs_ano_pasado.py`).
    _marca = {
        "background-color": f"{LAVANDA_FONDO} !important",
        "box-shadow": f"inset 3px 0 0 0 {ACENTO} !important",
    }
    css[f".ag-row.{_CLASE_SEL}"] = _marca
    css[".ag-row.ag-row-selected"] = _marca
    # UNA SOLA LÍNEA SOBRE LA FILA TOTAL: el tema le pone 1px gris a su
    # contenedor y ese píxel sale del alto de la fila (medido en
    # `ajuste_familias.py`, que la tenía primero: la fila terminaba 1px por
    # debajo de la grilla, recortada). Regla #364.
    css[".ag-floating-bottom"] = {"border-top": "none !important"}
    return css


def renderizar_documentos_semanal(tp, altura, key, ver_fecha=True,
                                  ver_doc=True, total=None):
    """Una fila por COMPRA del período en foco.

    `tp` trae `fecha`, `doc`, `prov`, `lineas` y `valor` ya formateados como
    texto, más dos ocultas: `__compra` (la clave de la compra, la misma de
    `semanal.py`) y `__sel` (True en la que muestra la tabla de al lado).

    `ver_fecha` en False cuando todas las filas son del mismo día («Por
    documento» lista las compras del día de la barra): una columna que repite
    la misma fecha en cada fila no dice nada, y el día ya lo dice el caption
    (regla #239). `ver_doc` en False sin columna de documento (el demo).
    `total` es la fila TOTAL fija (ver el docstring del módulo), o None.

    Devuelve la `__compra` de la fila clickeada, o None. Como la grilla nace
    sin selección (ver el docstring del módulo), un valor es siempre un clic
    de esta vuelta."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=False, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("fecha", header_name="Fecha", hide=not ver_fecha,
                        width=86, minWidth=86, suppressSizeToFit=True)
    # 104: los 87px de «FF01-00012345» a 13px más los 8+8 de padding — la
    # misma cuenta que la columna de Volatilidad.
    gb.configure_column("doc", header_name="Documento", hide=not ver_doc,
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("prov", header_name="Proveedor", width=140,
                        minWidth=80, tooltipField="prov")
    gb.configure_column("lineas", header_name="Líneas", type=["numericColumn"],
                        width=62, minWidth=62, suppressSizeToFit=True)
    # 104: «S/ 123,456.78» mide ~86px a 13px, más el padding.
    gb.configure_column("valor", header_name="Valor", type=["numericColumn"],
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("__compra", hide=True)
    gb.configure_column("__sel", hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, getRowClass=_CLASE_FILA,
        onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # cuadrados negros en Chrome < 120: arquitectura.md #159

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(), allow_unsafe_jscode=True, key=key,
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__compra"])
    return None


def renderizar_lineas_semanal(tp, altura, key, total=None):
    """Las líneas de UN documento: `prod`, `cant`, `punit` y `valor`, ya
    formateadas. Sin selección: se lee, no se clickea. `total` es la fila
    TOTAL fija, o None.

    Sin fecha, documento ni proveedor, a propósito: son los mismos en todas
    las filas y ya los dice la fila marcada de al lado."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=False, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("prod", header_name="Producto", width=180,
                        minWidth=100, tooltipField="prod")
    gb.configure_column("cant", header_name="Cantidad", type=["numericColumn"],
                        width=86, minWidth=86, suppressSizeToFit=True)
    gb.configure_column("punit", header_name="P. unit.", type=["numericColumn"],
                        width=96, minWidth=96, suppressSizeToFit=True)
    gb.configure_column("valor", header_name="Valor", type=["numericColumn"],
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        # Sin selección un clic no hace nada, pero AG Grid igual le dibuja el
        # recuadro de foco a la celda (lo mismo que en Volatilidad).
        suppressCellFocus=True, onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(), allow_unsafe_jscode=True, key=key,
    )
