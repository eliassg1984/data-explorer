"""tablas.compras_semanal - las grillas de la zona de abajo de «Compra por
período» (graficos/compras/semanal.py), que desde el 2026-09-19 tiene DOS
modos y tres grillas:

  · «Detalle» — los DOCUMENTOS del período en foco a la izquierda y, al
    costado, las LÍNEAS del documento elegido.
  · «Resumen» — UNA grilla con una fila por BARRA del gráfico
    (`renderizar_periodos_semanal`), más su fila TOTAL.

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
como la misma cosa (regla #404).

LAS DOS SE ORDENAN desde el 2026-09-19, a pedido («que ambas tablas tengan
opciones de ordenar por columnas»), con clic en la cabecera. Hasta ese día
las celdas llegaban YA FORMATEADAS desde el drill, como texto, y un
«S/ 4,425.14» ordenado como texto queda debajo de «S/ 443.00». Ahora el
número y la fecha viajan crudos —la fecha en ISO, que ordena bien como
texto— y el formato lo pone un `valueFormatter`, igual que en
`tablas/ajuste_familias.py`. Ordenar no manda nada a Python (`update_on`
sólo escucha la selección): es gratis.

LA FILA MARCADA NO ES LA SELECCIÓN DE AG GRID: es una clase de fila que sale
de `__sel`, un dato que viaja en la fila, con el mismo look que una fila
seleccionada. Así la grilla no puede contradecir al estado del drill, que
también lo cambia un clic en el GRÁFICO.

Y LA KEY YA NO LLEVA EL DOCUMENTO ELEGIDO (2026-09-19). La llevaba para que
cada clic estrenara grilla, y eso borraba en cada clic el orden que el
usuario acababa de elegir. La arma el drill con lo que cambia las FILAS
(período, filtros, rango, clic en el gráfico) y no con la fila elegida:

  · la marca va por `rowClassRules` y no por `getRowClass`, que al
    refrescar una fila agrega clases pero no las quita (regla #441: con la
    key estable quedaban DOS filas marcadas);
  · lo que devuelve es la selección VIGENTE, no un clic de esta vuelta: el
    drill la compara contra la compra que ya muestra y sólo actúa si
    difiere.

Ver reglas #440 y #471.

2026-09-17 — FILA TOTAL FIJA en las dos (regla #454): `total=` es el dict de
esa fila, ya formateado como el resto. Va por `pinnedBottomRowData`, con la
paleta de cierre de las tablas-ranking (`JS_FILA_TOTAL`), y no participa de
la selección: las filas fijas no son parte del modelo de filas y AG Grid no
las selecciona (lo dice su documentación de «Row Pinning»; no se probó a
mano), así que un clic en el total no debería devolver nada — la fila no
trae `__compra` ni `__sel`.

2026-09-19 — LA TERCERA GRILLA, «Resumen» (regla #476). A pedido: «podemos
alternar esa zona donde aparecen estas dos tarjetas abajo, con una donde
aparezca la información de las columnas pero por fila; si en el gráfico
muestra 20 columnas, debe mostrar 20 filas, más su total». Es el GRÁFICO
escrito como tabla: una fila por barra, en el mismo orden del eje, con lo
que dice su etiqueta (total, documentos, variación) más el % del total de
la vista y las líneas. Comparte el look, los formatos y la fila TOTAL con
sus dos hermanas — es la misma zona de la misma tarjeta.

2026-09-20 — Y UNA COLUMNA POR FAMILIA, las mismas que las tarjetas de KPI
de la cabecera y con su mismo formato compacto (`_JS_COMPACTO`): es lo que
las hace entrar al lado de las otras seis. La fila TOTAL dice además con
qué grano están agrupadas las filas («Total · 5 semanas»), y el rango que
cubren lo dice el caption de la fila de modo. Misma regla #476.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, ERROR, EXITO, GRIS_TEXTO, LAVANDA_CHIP,
    LAVANDA_FONDO,
)
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

REGLAS_FILA = {_CLASE_SEL: JsCode(
    "function(p){ return !!(p.data && p.data.__sel); }")}
"""La fila del documento que muestra la tabla de al lado. Ver «LA FILA
MARCADA NO ES LA SELECCIÓN DE AG GRID» en el docstring del módulo.

`rowClassRules` y no `getRowClass`: con la key estable la fila se REFRESCA
en vez de estrenarse, y `getRowClass` agrega clases al refrescar pero no las
quita (regla #441). La usa también `tablas/ajuste_familias.py`, que fue el
que lo midió: una sola regla para las dos marcas."""

# ── Formatos: el dato viaja crudo para que la columna se ORDENE ─────────
# Los cuatro dejan pasar tal cual lo que no es del tipo esperado: la fila
# TOTAL fija llega ya formateada como texto («Total», «564», «S/ 74,972.27»)
# y no se ordena (las filas fijas no son parte del modelo de filas).
_JS_FECHA = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'string' || v.length < 10 || v.charAt(4) !== '-')"
    " return v == null ? '' : String(v);"
    " return v.slice(8, 10) + '/' + v.slice(5, 7) + '/' + v.slice(0, 4); }")
"""«2026-09-01» → «01/09/2026». La fecha viaja en ISO porque ISO ordenado
como texto ES el orden de las fechas; «01/09» ordenado como texto no."""

_JS_ENTERO = JsCode(
    "function(p){ var v = p.value; if (typeof v !== 'number')"
    " return v == null ? '' : String(v);"
    " return Math.round(v).toLocaleString('es-PE'); }")

_JS_CANTIDAD = JsCode(
    "function(p){ var v = p.value; if (typeof v !== 'number')"
    " return v == null ? '' : String(v);"
    " return v.toLocaleString('es-PE',"
    " {minimumFractionDigits: 1, maximumFractionDigits: 1}); }")

_JS_SOLES = JsCode(
    "function(p){ var v = p.value; if (v == null) return '—';"
    " if (typeof v !== 'number') return String(v);"
    " return (v < 0 ? '−' : '') + 'S/ ' + Math.abs(v).toLocaleString('es-PE',"
    " {minimumFractionDigits: 2, maximumFractionDigits: 2}); }")
"""«S/ 4,425.14», con dos decimales como el resto de Semanal (`es-PE` agrupa
con coma y separa decimales con punto, igual que el `:,.2f` de Python). Un
valor vacío —el precio unitario que no vino— es «—»."""

_JS_PARTE = JsCode(
    "function(p){ var v = p.value; if (typeof v !== 'number')"
    " return v == null ? '' : String(v);"
    " return (v * 100).toLocaleString('es-PE',"
    " {minimumFractionDigits: 1, maximumFractionDigits: 1}) + '%'; }")
"""La fracción del total, de 0 a 1, escrita «12.3%».

UN decimal y no cero, al revés que las tarjetas de KPI de la cabecera: acá
la columna se lee HACIA ABAJO contra un total de 100%, y con enteros veinte
filas redondeadas suman 98 o 103 — un error de redondeo que en una columna
se lee como una cuenta mal hecha."""

_JS_COMPACTO = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'number') return v == null ? '' : String(v);"
    " if (v === 0) return '\u2014';"
    " var m = Math.abs(v);"
    " if (m >= 1000000) return 'S/ ' + (v / 1000000).toFixed(1) + 'M';"
    " if (m >= 1000) return 'S/ ' + (v / 1000).toFixed(1) + 'k';"
    " return 'S/ ' + v.toFixed(0); }")
"""«S/ 126.7k»: el formato de `utils.fmt_k`, escrito en JS.

LO COMPACTO NO ES CAPRICHO, es lo que hace que las columnas de familia
entren: con el formato de `_JS_SOLES` cada una pediría 118px y cinco se
comerían 590 de los 1.204 de la tarjeta, dejando la columna del período en
106 — menos de lo que mide «17–23 ago 2026». Y es el MISMO formato de las
tarjetas de KPI de la cabecera, que son las mismas familias: la tabla
escribe los números como la fila de arriba. El valor exacto y su % van en
el tooltip de la celda.

Un cero es «—» y no «S/ 0»: una familia sin compras en ese período no es un
monto, es una ausencia, y veinte filas de «S/ 0» tapan a las que sí."""

_TOOLTIP_FAMILIA = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'number' || v === 0) return '';"
    " var t = p.data ? p.data.valor : null;"
    " var s = 'S/ ' + v.toLocaleString('es-PE',"
    " {minimumFractionDigits: 2, maximumFractionDigits: 2});"
    " if (typeof t === 'number' && t) {"
    "   s += ' \u00b7 ' + (v / t * 100).toFixed(1) + '% de la barra'; }"
    " return s; }")
"""El valor exacto de la celda compacta, y cuánto pesa en SU barra.

Contra `data.valor` —el total de la fila— y no contra el de la vista: esa
otra cuenta ya la da la columna «% del total». En la fila TOTAL fija,
`valor` llega como texto ya formateado, y de ahí el `typeof`: ahí el
tooltip se calla en vez de mentir un porcentaje."""

# El semáforo de la variación, en el mismo idioma que la etiqueta de la
# barra (`semanal._fmt_variacion`): un decimal por debajo del 10%, ninguno
# arriba, el menos tipográfico, y el color de COSTO —rojo si se compró más,
# verde si menos—. Escrito con `replace` y no con un f-string por las llaves
# de JavaScript, igual que `compras_vs_ano_pasado._style_costo`.
_JS_VARIACION = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'number') {"
    "   var t = p.data ? p.data.__vtxt : null;"
    "   return t == null ? '\\u2014' : t; }"
    " var dec = Math.abs(v) < 10 ? 1 : 0;"
    " var a = Math.abs(v);"
    " if (Number(a.toFixed(dec)) === 0) return '0%';"
    " return (v > 0 ? '+' : '\\u2212') + a.toFixed(dec) + '%'; }")
"""«+8.2%», «−3.0%», y lo que el drill haya dejado en `__vtxt` («parcial»)
cuando no hay porcentaje que escribir. El «—» es el último recurso: una
fila sin valor Y sin motivo."""

_STYLE_VARIACION = JsCode("""
    function(p){
        if (p.node && p.node.rowPinned) return null;
        var base = {textAlign: 'right'};
        var v = p.value;
        if (typeof v !== 'number') {
            base.color = '__GRIS__'; base.fontStyle = 'italic'; return base;
        }
        var dec = Math.abs(v) < 10 ? 1 : 0;
        if (Number(Math.abs(v).toFixed(dec)) === 0) {
            base.color = '__GRIS__'; return base;
        }
        base.color = v > 0 ? '__SUBE__' : '__BAJA__';
        base.fontWeight = '600';
        return base;
    }
""".replace("__GRIS__", GRIS_TEXTO)
   .replace("__SUBE__", ERROR).replace("__BAJA__", EXITO))
"""El color de la variación. `null` en la fila fija: si devolviera un color
le ganaría al `getRowStyle` del TOTAL y esa celda saldría de otro color que
sus vecinas (el total no lleva variación — sumar porcentajes de períodos
distintos no mide nada)."""

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

_AL_CAMBIAR_FILAS = JsCode("""
    function(params) {
        try {
            var api = params.api, sel = null;
            api.forEachNode(function (n) { if (n.data && n.data.__sel) sel = n; });
            var marca = sel ? String(sel.data.periodo) : null;
            if (marca === window.__semPerMarca) return;
            window.__semPerMarca = marca;
            if (sel) api.ensureNodeVisible(sel, 'middle');
        } catch (e) {}
    }
""")
"""Lleva a la vista la fila marcada CUANDO CAMBIA la marca, y sólo entonces.

Hace falta en la grilla de Resumen y no en sus hermanas porque ésta NO se
estrena con cada clic: su key no lleva el foco (para no perder el orden que
el usuario eligió, regla #471), así que `onGridReady` —donde las otras
resuelven esto— no vuelve a correr. Sin esto, tocar una barra de un día que
cae en la fila 11 de 30 marca una fila que no está en pantalla, y el gesto
se lee como que no pasó nada.

EL GUARD NO ES DECORATIVO: `rowDataUpdated` se dispara en CADA corrida del
fragment, porque Python le vuelve a pasar las filas aunque no hayan
cambiado. Sin comparar contra la marca anterior, cualquier rerun le
arrastraría el scroll al usuario. `window` es el del iframe de ESTA grilla,
así que la marca no se mezcla con la de ninguna otra."""


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
    # La cabecera de una columna ordenable muestra la flecha: sin aire, el
    # rótulo y la flecha se pisan (el mismo arreglo que `ajuste_familias`).
    css[".ag-header-cell-label"] = {"gap": "4px"}
    return css


def renderizar_documentos_semanal(tp, altura, key, ver_fecha=True,
                                  ver_doc=True, total=None):
    """Una fila por COMPRA del período en foco.

    `tp` trae `fecha` (texto ISO), `doc`, `prov`, `lineas` y `valor`
    (números crudos: el formato lo pone la grilla, para que se ordenen), más
    dos ocultas: `__compra` (la clave de la compra, la misma de
    `semanal.py`) y `__sel` (True en la que muestra la tabla de al lado).

    `ver_fecha` en False cuando todas las filas son del mismo día («Por
    documento» lista las compras del día de la barra): una columna que repite
    la misma fecha en cada fila no dice nada, y el día ya lo dice el caption
    (regla #239). `ver_doc` en False sin columna de documento (el demo).
    `total` es la fila TOTAL fija (ver el docstring del módulo), o None.

    Devuelve la `__compra` de la fila SELECCIONADA, o None. Es la selección
    vigente y no un clic de esta vuelta (la key no cambia con la fila
    elegida, ver el docstring del módulo): el llamador la compara contra la
    compra que ya muestra."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    # Los anchos de las columnas ordenables suman la flecha (12px) y su aire
    # (4px) al rótulo: «Fecha» pasó de 86 a 94 y «Líneas» de 62 a 76.
    gb.configure_column("fecha", header_name="Fecha", hide=not ver_fecha,
                        valueFormatter=_JS_FECHA,
                        width=94, minWidth=94, suppressSizeToFit=True)
    # 104: los 87px de «FF01-00012345» a 13px más los 8+8 de padding — la
    # misma cuenta que la columna de Volatilidad.
    gb.configure_column("doc", header_name="Documento", hide=not ver_doc,
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("prov", header_name="Proveedor", width=140,
                        minWidth=80, tooltipField="prov")
    gb.configure_column("lineas", header_name="Líneas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        width=76, minWidth=76, suppressSizeToFit=True)
    # 112: «S/ 123,456.78» mide ~86px a 13px, más el padding y la flecha.
    # Abre ordenada por acá, que es el orden en que el drill ya las
    # mandaba: la flecha dice por qué columna está ordenada antes de que
    # nadie toque nada.
    #
    # `initialSort` y NO `sort`, y es lo que hace que el orden sobreviva al
    # clic. st_aggrid le vuelve a pasar las `columnDefs` a la grilla en cada
    # corrida aunque la key no cambie, y AG Grid re-aplica `sort` cada vez
    # que las recibe: medido el 2026-09-19, ordenar por Proveedor y
    # clickear un documento devolvía la tabla a Valor ↓. `initialSort` sólo
    # cuenta cuando la columna se crea (regla #471).
    gb.configure_column("valor", header_name="Valor", type=["numericColumn"],
                        valueFormatter=_JS_SOLES, initialSort="desc",
                        width=112, minWidth=112, suppressSizeToFit=True)
    gb.configure_column("__compra", hide=True)
    gb.configure_column("__sel", hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=REGLAS_FILA,
        onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # cuadrados negros en Chrome < 120: arquitectura.md #159

    # `update_on` sólo la selección: el default de st_aggrid suma
    # `sortChanged`, y cada clic en una cabecera costaría una corrida entera
    # del fragment (3-6 s en Cloud) para reordenar algo que el navegador ya
    # reordenó.
    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__compra"])
    return None


def renderizar_lineas_semanal(tp, altura, key, total=None):
    """Las líneas de UN documento: `prod` y los números crudos `cant`,
    `punit` (vacío si no vino) y `valor` — el formato lo pone la grilla,
    para que se ordenen. Sin selección: se lee, no se clickea. `total` es
    la fila TOTAL fija, o None.

    Sin fecha, documento ni proveedor, a propósito: son los mismos en todas
    las filas y ya los dice la fila marcada de al lado."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("prod", header_name="Producto", width=180,
                        minWidth=100, tooltipField="prod")
    gb.configure_column("cant", header_name="Cantidad", type=["numericColumn"],
                        valueFormatter=_JS_CANTIDAD,
                        width=98, minWidth=98, suppressSizeToFit=True)
    gb.configure_column("punit", header_name="P. unit.", type=["numericColumn"],
                        valueFormatter=_JS_SOLES,
                        width=100, minWidth=100, suppressSizeToFit=True)
    gb.configure_column("valor", header_name="Valor", type=["numericColumn"],
                        valueFormatter=_JS_SOLES, initialSort="desc",
                        width=112, minWidth=112, suppressSizeToFit=True)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        # Sin selección un clic no hace nada, pero AG Grid igual le dibuja el
        # recuadro de foco a la celda (lo mismo que en Volatilidad).
        suppressCellFocus=True, onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    # Sin `update_on`: no hay nada que esta grilla le tenga que decir a
    # Python — ni la selección, que no tiene, ni el orden.
    AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(), allow_unsafe_jscode=True, key=key, update_on=[],
    )



def renderizar_periodos_semanal(tp, altura, key, rotulo_periodo="Período",
                                ver_docs=True, ver_variacion=True,
                                familias=(), total=None):
    """Una fila por BARRA del gráfico, en el orden del eje.

    `tp` trae `periodo` (el nombre de la barra, ya legible), los números
    crudos `valor`, `parte` (0-1), `docs` y `lineas`, la `variacion` en %
    (o vacía) y tres ocultas: `__vtxt` (qué escribir cuando no hay
    porcentaje — «parcial»), `__nota` (el tooltip que dice por qué) y
    `__sel` (True en la barra que el gráfico tiene en foco).

    `rotulo_periodo` es el encabezado de la primera columna: lo pone el
    drill porque depende de la granularidad («Período» en Día/Semana/Mes/
    Año, «Documento» cuando cada barra es una compra).

    `ver_docs` y `ver_variacion` en False donde esa columna no dice nada
    (regla #239): en «Por documento» cada barra ES un documento, así que
    la cuenta da 1 en TODAS las filas, y la variación sólo la escribe el
    gráfico en Día, Semana y Mes — una columna entera de «—» es ruido. Lo
    que no se pierde es el TOTAL de las dos: sigue en la fila fija y en el
    caption de la fila de modo.

    `familias` son las columnas del desglose, como `(columna, rótulo)` y en
    el orden en que van: las arma el drill con las MISMAS familias que las
    tarjetas de KPI de la cabecera (las cuatro mayores y «N más»), y viene
    vacío cuando la vista tiene una sola familia. Van al final, después de
    la variación: primero lo que dice la etiqueta de la barra, después de
    qué está hecha.

    SIN `initialSort`, a diferencia de sus dos hermanas: las filas abren en
    el orden del EJE —que es el del `tp` que manda el drill— porque la
    tabla es el gráfico escrito. Las columnas se ordenan igual con un clic
    en la cabecera, que no cuesta ninguna corrida (`update_on=[]`).

    No devuelve nada: se lee, no se clickea. El foco lo sigue moviendo el
    clic en la barra, que es de donde salen estas filas."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    # La única que se estira: el resto mide lo que dice su peor dato (ver
    # los anchos de las hermanas, misma cuenta a 13px + 8+8 de padding + la
    # flecha de ordenar).
    gb.configure_column("periodo", header_name=rotulo_periodo, minWidth=180,
                        tooltipField="periodo")
    gb.configure_column("valor", header_name="Valorizado",
                        type=["numericColumn"], valueFormatter=_JS_SOLES,
                        width=130, minWidth=130, suppressSizeToFit=True)
    gb.configure_column("parte", header_name="% del total",
                        type=["numericColumn"], valueFormatter=_JS_PARTE,
                        headerTooltip="Cuánto pesa esta barra en el total "
                                      "de la vista (el de la cabecera)",
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("docs", header_name="Documentos",
                        hide=not ver_docs,
                        type=["numericColumn"], valueFormatter=_JS_ENTERO,
                        width=106, minWidth=106, suppressSizeToFit=True)
    gb.configure_column("lineas", header_name="Líneas",
                        type=["numericColumn"], valueFormatter=_JS_ENTERO,
                        width=82, minWidth=82, suppressSizeToFit=True)
    gb.configure_column("variacion", header_name="Variación",
                        hide=not ver_variacion, type=["numericColumn"],
                        valueFormatter=_JS_VARIACION,
                        cellStyle=_STYLE_VARIACION, tooltipField="__nota",
                        headerTooltip="Contra la barra ANTERIOR del "
                                      "gráfico, no contra el período "
                                      "anterior del calendario",
                        width=104, minWidth=104, suppressSizeToFit=True)
    # Las de familia, al final. 94px: «S/ 126.7k» mide ~60 a 13px, más los
    # 8+8 de padding y los 16 de la flecha de ordenar. El rótulo que no
    # entra se corta con «…» y sale entero en el tooltip de la cabecera —
    # la misma solución que las tarjetas de KPI, que tampoco pueden
    # escribir «Vinos y espumantes» en su ancho.
    for _col, _rotulo in familias:
        gb.configure_column(_col, header_name=_rotulo,
                            type=["numericColumn"],
                            valueFormatter=_JS_COMPACTO,
                            tooltipValueGetter=_TOOLTIP_FAMILIA,
                            headerTooltip=f"{_rotulo} · valorizado de compra "
                                          "de esa familia en cada barra",
                            width=94, minWidth=94, suppressSizeToFit=True)
    for oculta in ("__vtxt", "__nota", "__sel"):
        gb.configure_column(oculta, hide=True)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        # Sin selección: un clic no hace nada, pero AG Grid igual le dibuja
        # el recuadro de foco a la celda (lo mismo que en las hermanas).
        suppressCellFocus=True, rowClassRules=REGLAS_FILA,
        onGridReady=_AL_MONTAR, onRowDataUpdated=_AL_CAMBIAR_FILAS), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(), allow_unsafe_jscode=True, key=key, update_on=[],
    )
