"""tablas.movimientos_periodo - las grillas de las tarjetas «por período»
de Movimientos (graficos/movimientos_periodo.py): la de requerimientos, la
de salidas y la de porcionamientos, que son la misma tarjeta con tres lados.

Porcionamientos (2026-09-24, regla #510) tiene sus propias tres grillas
—`renderizar_periodos_porc`, `renderizar_porcionamientos_mov` y
`renderizar_cortes_mov`— porque cuenta otras cosas: lo porcionado, la
merma y su %, y los CORTES de un porcionamiento en vez de las líneas de un
documento. El look y los formatos son los de abajo.

Las tarjetas son gemelas de «Compra por período» (graficos/compras/
semanal.py), y su zona de abajo también: «Resumen» —una fila por barra— y
«Detalle» —los documentos del período en foco y, al costado, las líneas del
elegido—. No son las mismas grillas de Compras porque sus columnas son
otras:

  · el Resumen cuenta DOCUMENTOS (requerimientos o salidas) y ÁREAS donde el
    de Compras cuenta comprobantes y desglosa familias, y suma la columna
    Estado;
  · la lista de documentos lleva la HORA del registro, el código, el área
    —y en salidas el tipo de descargo— y marca los que no suman;
  · las líneas son las mismas cuatro columnas de Compras, pero la cantidad
    lleva los decimales que tiene (`_JS_CANT_MOV`): una cocina pide gramos.

Lo que sí comparten con Compras es todo lo demás, y viene de allá: el look
(`_css`), los formatos de celda, la fila TOTAL fija, la fila marcada por
`rowClassRules` y el `onGridReady` que ajusta las columnas (reglas #440,
#441 y #471). Tarjetas gemelas con dos looks de tabla no se leerían como la
misma cosa (regla #404).

EL ESTADO SE ESCRIBE SÓLO CUANDO ES LA EXCEPCIÓN (regla #239): el 97-98 %
de los documentos está procesado, así que una columna que dijera
«Procesado» en cada fila taparía a los que no. En el Resumen las filas sin
novedad llevan un «✓» gris; en la lista, lo que no suma se lee en la celda
del valor («Anulado», «Sin procesar», «Sin ítems») —el monto del anulado
pasa al tooltip— y su fila va apagada. Ver `arquitectura.md` reglas #508 y
#509.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import ADVERTENCIA_TEXTO, ERROR, GRIS_TEXTO_SUAVE
from tablas._config import _parchar_iconos
# Privados de allá, y a propósito: son el look y los formatos de las
# grillas de «Compra por período», que estas tarjetas calcan. Mismo criterio
# con el que aquel módulo toma `_css_look` de Volatilidad.
from tablas.compras_semanal import (
    _AL_CAMBIAR_FILAS, _AL_MONTAR, _JS_ENTERO, _JS_PARTE, _JS_SOLES,
    _JS_VARIACION, _STYLE_VARIACION, _con_total, _css, REGLAS_FILA,
)
from tablas.compras_volatilidad import ALTO_FILA

ESTADO_OK = "✓"
"""Lo que dice la columna Estado del Resumen cuando no hay novedad."""

_JS_FECHA_HORA = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'string' || v.length < 16 || v.charAt(4) !== '-')"
    " return v == null ? '' : String(v);"
    " return v.slice(8, 10) + '/' + v.slice(5, 7) + ' ' + v.slice(11, 16); }")
"""«2026-09-22 14:24» → «22/09 14:24». Viaja en ISO por lo mismo que la
fecha de Compras (`compras_semanal._JS_FECHA`): ordenado como texto ES el
orden del tiempo. Sin el año: todas las filas son del mismo período, y el
período lo dice el caption."""

_JS_VALOR_MOV = JsCode(
    "function(p){ var d = p.data || {};"
    " if (d.__elbl) return d.__elbl;"
    " var v = p.value; if (v == null) return '—';"
    " if (typeof v !== 'number') return String(v);"
    " return (v < 0 ? '−' : '') + 'S/ ' + Math.abs(v).toLocaleString("
    "'es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }")
"""El valorizado del documento, o lo que lo reemplaza cuando no suma.

`__elbl` lo escribe Python —«Anulado» o «Anulada» según el lado, «Sin
procesar», «Sin ítems»— y la celda lo muestra EN LUGAR del monto. El valor
viaja igual, para que la columna se siga ordenando, y el del anulado se lee
en el tooltip (`_TIP_VALOR_MOV`). En la fila TOTAL fija el valor llega ya
formateado como texto y se devuelve tal cual."""

_JS_CANT_MOV = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'number' || isNaN(v))"
    "   return v == null ? (p.node && p.node.rowPinned ? '' : '—')"
    "                    : String(v);"
    " var dec = Math.abs(v) < 1 ? 3 : 2;"
    " return v.toLocaleString('es-PE', {minimumFractionDigits: 0,"
    "                                   maximumFractionDigits: dec}); }")
"""Cantidad con los decimales que TIENE: «144», «16.5», «0.04», «0.026».

No el `_JS_CANTIDAD` de las líneas de Compras (un decimal fijo): un pedido
de cocina es de gramos, y con un decimal «40 g de pimentón» sale «0.0» al
lado de un valor — la misma trampa que la regla #506 midió en Ajuste.
Debajo de 1, hasta tres decimales, como el Kardex."""

_TIP_VALOR_MOV = JsCode(
    "function(p){ var d = p.data || {}, v = p.value;"
    " var s = typeof v === 'number' ? 'S/ ' + v.toLocaleString('es-PE',"
    "   {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '';"
    " if (d.__estado === 'anulado') return d.__elbl + ' · ' + s"
    "   + ' · no suma en la barra ni en los totales';"
    " if (d.__estado === 'sin procesar') return 'Sin procesar (estado"
    " Generado): todavía no se procesó'"
    "   + (d.lineas ? '' : ', así que no tiene ítems ni suma');"
    " if (d.__estado === 'sin ítems') return 'Sin ítems: viene sin"
    " producto, cantidad ni valor, así que no suma';"
    " return ''; }")
"""El tooltip de la celda del valor: el MONTO del anulado —que la celda no
escribe— y por qué no suma, o qué quiere decir «sin procesar» y «sin
ítems»."""

REGLAS_FILA_MOV = {
    **REGLAS_FILA,
    "mp-anulado": JsCode(
        "function(p){ return !!(p.data && p.data.__estado === 'anulado'); }"),
    "mp-sinitems": JsCode(
        "function(p){ return !!(p.data && p.data.__estado === 'sin ítems');"
        " }"),
    "mp-sinproc": JsCode(
        "function(p){ return !!(p.data && p.data.__estado === 'sin procesar');"
        " }"),
}
"""La fila marcada de Compras (`__sel`) más las tres excepciones de estado.

`rowClassRules` y no `getRowClass`, por la regla #441: la grilla conserva su
key mientras no cambie el período, y `getRowClass` no QUITA las clases al
refrescar una fila."""

REGLAS_ESTADO = {
    f"mp-e-{_c}": JsCode(
        f"function(p){{ return !!(p.data && p.data.__eclase === '{_c}'); }}")
    for _c in ("ok", "anul", "sinp")
}
"""El color de la columna Estado del Resumen, por clase y no por
`cellStyle`: un estilo inline que se deja de devolver NO se borra al
refrescar la celda, una clase de `cellClassRules` sí."""


def _css_mov():
    """El look de Compras más los colores de estado de estas grillas."""
    css = _css()
    css[".ag-row.mp-anulado .ag-cell, .ag-row.mp-sinitems .ag-cell"] = {
        "color": f"{GRIS_TEXTO_SUAVE} !important"}
    css[".ag-row.mp-anulado .ag-cell[col-id='valor']"] = {
        "color": f"{ERROR} !important", "font-weight": "600 !important"}
    css[".ag-row.mp-sinproc .ag-cell[col-id='valor']"] = {
        "color": f"{ADVERTENCIA_TEXTO} !important",
        "font-weight": "600 !important"}
    css[".ag-row.mp-sinitems .ag-cell[col-id='valor']"] = {
        "font-style": "italic !important"}
    css[".ag-cell.mp-e-ok"] = {"color": f"{GRIS_TEXTO_SUAVE} !important"}
    css[".ag-cell.mp-e-anul"] = {
        "color": f"{ERROR} !important", "font-weight": "600 !important"}
    css[".ag-cell.mp-e-sinp"] = {
        "color": f"{ADVERTENCIA_TEXTO} !important",
        "font-weight": "600 !important"}
    return css


def renderizar_periodos_mov(tp, altura, key, rotulo_periodo="Período",
                            rotulo_docs="Requerimientos", ver_variacion=True,
                            total=None):
    """Una fila por BARRA del gráfico, en el orden del eje.

    `tp` trae `periodo` (el nombre de la barra, ya legible), los números
    crudos `docs`, `lineas`, `areas`, `valor`, `parte` (0-1) y `variacion`
    (en %, o vacía), el texto `estado`, y seis ocultas: `__vtxt` (qué
    escribir cuando no hay porcentaje), `__nota` (por qué no lo hay),
    `__anota` (qué áreas: el tooltip de «Áreas»), `__eclase` (el color del
    estado), `__clave` (la clave del período, la del eje) y `__sel` (la
    barra en foco). `rotulo_docs` es la cabecera de la cuenta de documentos
    —«Requerimientos» o «Salidas»—.

    SIN `initialSort`, como el Resumen de Compras: las filas abren en el
    orden del EJE porque la tabla es el gráfico escrito. Se ordenan igual con
    un clic en la cabecera, que no cuesta ninguna corrida.

    Devuelve la `__clave` de la fila SELECCIONADA, o None: un clic en una
    fila abre su Detalle, igual que un clic en su barra. Es la selección
    VIGENTE; el llamador estrena la grilla (su key) cada vez que actúa sobre
    ella."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    # Los anchos, con la cuenta de Compras (`compras_semanal._COLS_ANCHA`):
    # lo que mide el peor dato a 13px, más 8+8 de padding y los ~14 de la
    # flecha de ordenar. «Período» es la única que se estira.
    gb.configure_column("periodo", header_name=rotulo_periodo, minWidth=180,
                        tooltipField="periodo")
    gb.configure_column("docs", header_name=rotulo_docs,
                        type=["numericColumn"], valueFormatter=_JS_ENTERO,
                        headerTooltip=f"{rotulo_docs} del período. No cuenta "
                                      "los anulados ni los que vienen sin "
                                      "ítems",
                        width=132, minWidth=132, suppressSizeToFit=True)
    gb.configure_column("lineas", header_name="Líneas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        headerTooltip="Líneas de esos documentos: un "
                                      "producto es una línea",
                        width=82, minWidth=82, suppressSizeToFit=True)
    gb.configure_column("areas", header_name="Áreas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO, tooltipField="__anota",
                        headerTooltip="Cuántas áreas hay en el período. "
                                      "Cuáles, en el tooltip de la celda",
                        width=78, minWidth=78, suppressSizeToFit=True)
    gb.configure_column("valor", header_name="Valorizado",
                        type=["numericColumn"], valueFormatter=_JS_VALOR_MOV,
                        headerTooltip="Valorizado del período",
                        width=130, minWidth=130, suppressSizeToFit=True)
    gb.configure_column("parte", header_name="% del total",
                        type=["numericColumn"], valueFormatter=_JS_PARTE,
                        headerTooltip="Cuánto pesa esta barra en el total "
                                      "de la vista",
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("variacion", header_name="Variación",
                        hide=not ver_variacion, type=["numericColumn"],
                        valueFormatter=_JS_VARIACION,
                        cellStyle=_STYLE_VARIACION, tooltipField="__nota",
                        headerTooltip="Variación contra la barra ANTERIOR "
                                      "del gráfico, no contra el período "
                                      "anterior del calendario",
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("estado", header_name="Estado",
                        cellClassRules=REGLAS_ESTADO,
                        headerTooltip="Sólo se escribe la excepción: "
                                      "anulados o sin procesar. «✓» es que "
                                      "todos se procesaron",
                        width=170, minWidth=120)
    for oculta in ("__vtxt", "__nota", "__anota", "__eclase", "__clave",
                   "__sel"):
        if oculta in tp.columns:
            gb.configure_column(oculta, hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=REGLAS_FILA,
        onGridReady=_AL_MONTAR, onRowDataUpdated=_AL_CAMBIAR_FILAS), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    # `update_on` sólo la selección, como la lista de documentos de Compras:
    # ordenar no le tiene que costar una corrida a nadie.
    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_mov(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty and "__clave" in sel.columns:
        return str(sel.iloc[0]["__clave"])
    return None


def renderizar_documentos_mov(tp, altura, key, rotulo_tipo="", total=None):
    """Una fila por DOCUMENTO del período en foco.

    `tp` trae `registro` (fecha y hora en ISO, «2026-09-22 14:24»),
    `codigo`, `area`, `tipo`, `lineas` y `valor` —números crudos: el formato
    lo pone la grilla, para que se ordenen— más cuatro ocultas: `__estado`
    («», «anulado», «sin procesar» o «sin ítems»), `__elbl` (lo que la
    celda del valor escribe en lugar del monto), `__doc` (el código, que es
    lo que devuelve) y `__sel` (True en el que muestra la tabla de al lado).

    La columna `tipo` —el tipo de descargo de las salidas— se ve sólo con
    `rotulo_tipo`: los requerimientos no lo tienen, y una columna vacía en
    cada fila sería ruido (regla #239).

    Se LISTAN también los que no suman, apagados: quien abre un período con
    «3 anuladas» en el Resumen tiene que poder ver cuáles fueron. La fila
    TOTAL suma sólo los que suman, que es la misma cuenta que la barra.

    Devuelve el `__doc` de la fila SELECCIONADA, o None — la selección
    vigente, no un clic de esta vuelta: el llamador la compara contra el
    documento que ya muestra (`compras_semanal`, regla #471)."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    # 100: «22/09 14:24» mide ~74px a 13px, más el padding y la flecha.
    gb.configure_column("registro", header_name="Registro",
                        valueFormatter=_JS_FECHA_HORA,
                        headerTooltip="Fecha y hora de registro",
                        width=100, minWidth=100, suppressSizeToFit=True)
    # 100: «2609000407» —diez dígitos, los cuatro primeros son año y mes—
    # mide ~72px.
    gb.configure_column("codigo", header_name="Código",
                        width=100, minWidth=100, suppressSizeToFit=True)
    gb.configure_column("area", header_name="Área", width=130, minWidth=80,
                        tooltipField="area")
    gb.configure_column("tipo", header_name=rotulo_tipo or "Tipo",
                        hide=not rotulo_tipo, width=120, minWidth=80,
                        tooltipField="tipo")
    gb.configure_column("lineas", header_name="Líneas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        width=72, minWidth=72, suppressSizeToFit=True)
    # `initialSort` y no `sort`, por la regla #471: st_aggrid le vuelve a
    # pasar las `columnDefs` en cada corrida y `sort` pisaría el orden que
    # haya elegido el usuario.
    gb.configure_column("valor", header_name="Valorizado",
                        type=["numericColumn"], valueFormatter=_JS_VALOR_MOV,
                        tooltipValueGetter=_TIP_VALOR_MOV, initialSort="desc",
                        width=116, minWidth=116, suppressSizeToFit=True)
    for oculta in ("__estado", "__elbl", "__doc", "__sel"):
        gb.configure_column(oculta, hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=REGLAS_FILA_MOV,
        onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_mov(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__doc"])
    return None


def _js_cant_con(campo_unidad):
    """La cantidad de `_JS_CANT_MOV` con su unidad al lado, leída de una
    columna oculta de la fila («21 kg», «25 und»). El número viaja crudo
    para que la columna se ordene por número y no como texto."""
    return JsCode(
        "function(p){ var v = p.value;"
        " if (typeof v !== 'number' || isNaN(v))"
        "   return v == null ? (p.node && p.node.rowPinned ? '' : '—')"
        "                    : String(v);"
        f" var u = p.data && p.data['{campo_unidad}'] ? ' ' + p.data['{campo_unidad}'] : '';"
        " return v.toLocaleString('es-PE', {minimumFractionDigits: 0,"
        "                                   maximumFractionDigits: 3}) + u; }")


_JS_CANT_UNID = _js_cant_con("__unid")
_JS_PESO_UNID = _js_cant_con("__unid_ini")

_JS_DIA = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'string' || v.length < 10 || v.charAt(4) !== '-')"
    " return v == null ? '' : String(v);"
    " return v.slice(8, 10) + '/' + v.slice(5, 7); }")
_TIP_DIA_HORA = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'string' || v.length < 16) return '';"
    " return v.slice(8, 10) + '/' + v.slice(5, 7) + '/' + v.slice(0, 4)"
    " + ' ' + v.slice(11, 16); }")
"""La lista de porcionamientos escribe sólo el DÍA («14/09») y deja la hora
al tooltip: con siete columnas, tres de ellas nombres, la hora le quitaba al
producto el ancho que necesita (medido a 1366px: «Magret De P…»). El valor
sigue en ISO para que la columna se ordene por el tiempo."""


def renderizar_periodos_porc(tp, altura, key, rotulo_periodo="Período",
                             ver_variacion=True, total=None):
    """El Resumen de PORCIONAMIENTOS: una fila por barra, en el orden del eje.

    `tp` trae `periodo`, los números crudos `docs` (porcionamientos),
    `cortes`, `areas`, `costo` (lo porcionado), `valor` (la merma: la
    barra), `pm` (merma ÷ porcionado, 0-1), `parte` (0-1) y `variacion`, y
    las ocultas de `renderizar_periodos_mov` salvo `__eclase`: no hay
    columna Estado, la consulta trae sólo procesados (regla #510).

    Devuelve la `__clave` de la fila seleccionada, o None — el mismo
    contrato que `renderizar_periodos_mov`."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("periodo", header_name=rotulo_periodo, minWidth=160,
                        tooltipField="periodo")
    gb.configure_column("docs", header_name="Porc.", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        headerTooltip="Porcionamientos del período",
                        width=80, minWidth=80, suppressSizeToFit=True)
    gb.configure_column("cortes", header_name="Cortes", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        headerTooltip="Productos que salieron de esos "
                                      "porcionamientos",
                        width=82, minWidth=82, suppressSizeToFit=True)
    gb.configure_column("areas", header_name="Áreas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO, tooltipField="__anota",
                        headerTooltip="Cuántas áreas porcionaron. Cuáles, en "
                                      "el tooltip de la celda",
                        width=78, minWidth=78, suppressSizeToFit=True)
    gb.configure_column("costo", header_name="Porcionado",
                        type=["numericColumn"], valueFormatter=_JS_SOLES,
                        headerTooltip="Costo de lo que entró a porcionar",
                        width=124, minWidth=124, suppressSizeToFit=True)
    gb.configure_column("valor", header_name="Merma",
                        type=["numericColumn"], valueFormatter=_JS_SOLES,
                        headerTooltip="Merma en soles: la parte de lo "
                                      "porcionado que se perdió",
                        width=116, minWidth=116, suppressSizeToFit=True)
    gb.configure_column("pm", header_name="% merma", type=["numericColumn"],
                        valueFormatter=_JS_PARTE,
                        headerTooltip="Merma ÷ lo porcionado, en soles",
                        width=94, minWidth=94, suppressSizeToFit=True)
    gb.configure_column("parte", header_name="% del total",
                        type=["numericColumn"], valueFormatter=_JS_PARTE,
                        headerTooltip="Cuánto pesa esta barra en la merma "
                                      "de la vista",
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("variacion", header_name="Variación",
                        hide=not ver_variacion, type=["numericColumn"],
                        valueFormatter=_JS_VARIACION,
                        cellStyle=_STYLE_VARIACION, tooltipField="__nota",
                        headerTooltip="Variación de la merma contra la barra "
                                      "ANTERIOR del gráfico, no contra el "
                                      "período anterior del calendario",
                        width=104, minWidth=104, suppressSizeToFit=True)
    for oculta in ("__vtxt", "__nota", "__anota", "__clave", "__sel"):
        if oculta in tp.columns:
            gb.configure_column(oculta, hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=REGLAS_FILA,
        onGridReady=_AL_MONTAR, onRowDataUpdated=_AL_CAMBIAR_FILAS), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_mov(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty and "__clave" in sel.columns:
        return str(sel.iloc[0]["__clave"])
    return None


def renderizar_porcionamientos_mov(tp, altura, key, total=None):
    """Una fila por PORCIONAMIENTO del período en foco.

    `tp` trae `registro` (ISO, con hora), `prod` (el producto inicial),
    `area`, `tipo` (el usuario), los números crudos `cant`, `pm` (0-1) y
    `valor` (la merma en soles), y tres ocultas: `__unid` (la unidad de la
    cantidad, ya corta), `__doc` (el código, que es lo que devuelve) y
    `__sel`. Abre ordenada por merma, de mayor a menor.

    Devuelve el `__doc` de la fila seleccionada, o None: la selección
    vigente, como `renderizar_documentos_mov`."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("registro", header_name="Fecha",
                        valueFormatter=_JS_DIA,
                        tooltipValueGetter=_TIP_DIA_HORA,
                        headerTooltip="Día de registro (la hora, en el "
                                      "tooltip)",
                        width=74, minWidth=74, suppressSizeToFit=True)
    gb.configure_column("prod", header_name="Producto inicial", width=220,
                        minWidth=110, tooltipField="prod")
    gb.configure_column("area", header_name="Área", width=96, minWidth=70,
                        tooltipField="area")
    gb.configure_column("tipo", header_name="Usuario", width=90, minWidth=70,
                        tooltipField="tipo")
    gb.configure_column("cant", header_name="Cantidad", type=["numericColumn"],
                        valueFormatter=_JS_CANT_UNID,
                        headerTooltip="Lo que entró a porcionar, en la unidad "
                                      "del producto",
                        width=96, minWidth=96, suppressSizeToFit=True)
    gb.configure_column("pm", header_name="% merma", type=["numericColumn"],
                        valueFormatter=_JS_PARTE,
                        headerTooltip="Merma ÷ lo que entró",
                        width=86, minWidth=86, suppressSizeToFit=True)
    # `initialSort`, no `sort` (regla #471): el orden que elija el usuario
    # sobrevive a que st_aggrid le vuelva a pasar las columnas.
    gb.configure_column("valor", header_name="Merma", type=["numericColumn"],
                        valueFormatter=_JS_SOLES, initialSort="desc",
                        headerTooltip="Merma en soles",
                        width=104, minWidth=104, suppressSizeToFit=True)
    for oculta in ("__unid", "__doc", "__sel"):
        gb.configure_column(oculta, hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=REGLAS_FILA,
        onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_mov(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__doc"])
    return None


def renderizar_cortes_mov(tp, altura, key, total=None):
    """Los CORTES de un porcionamiento: `fin` (el producto que salió) y los
    números crudos `cant` (en su unidad, `__unid`), `peso` (en la del
    producto inicial, `__unid_ini`: sumado es lo aprovechado), `pprom` y
    `valor`. Sin selección: se lee, no se clickea."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("fin", header_name="Producto final", width=180,
                        minWidth=100, tooltipField="fin")
    gb.configure_column("cant", header_name="Cantidad", type=["numericColumn"],
                        valueFormatter=_JS_CANT_UNID,
                        width=96, minWidth=96, suppressSizeToFit=True)
    gb.configure_column("peso", header_name="Peso", type=["numericColumn"],
                        valueFormatter=_JS_PESO_UNID,
                        headerTooltip="Lo que se llevó este corte, en la "
                                      "unidad del producto inicial",
                        width=90, minWidth=90, suppressSizeToFit=True)
    gb.configure_column("pprom", header_name="P. prom.", type=["numericColumn"],
                        valueFormatter=_JS_SOLES,
                        headerTooltip="Costo por unidad del corte: incluye "
                                      "su parte de la merma",
                        width=96, minWidth=96, suppressSizeToFit=True)
    gb.configure_column("valor", header_name="Valor", type=["numericColumn"],
                        valueFormatter=_JS_SOLES, initialSort="desc",
                        width=108, minWidth=108, suppressSizeToFit=True)
    for oculta in ("__unid", "__unid_ini"):
        gb.configure_column(oculta, hide=True)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_mov(), allow_unsafe_jscode=True, key=key, update_on=[],
    )


def renderizar_lineas_mov(tp, altura, key, total=None):
    """Las líneas de UN documento: `prod` y los números crudos `cant`,
    `punit` y `valor` —el formato lo pone la grilla, para que se ordenen—.
    Sin selección: se lee, no se clickea. `total` es la fila TOTAL fija.

    Es `compras_semanal.renderizar_lineas_semanal` con otra cantidad (ver
    `_JS_CANT_MOV`). Sin fecha, código ni área, a propósito: son los mismos
    en todas las filas y ya los dice la fila marcada de al lado."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("prod", header_name="Producto", width=180,
                        minWidth=100, tooltipField="prod")
    gb.configure_column("cant", header_name="Cantidad", type=["numericColumn"],
                        valueFormatter=_JS_CANT_MOV,
                        width=98, minWidth=98, suppressSizeToFit=True)
    gb.configure_column("punit", header_name="P. unit.", type=["numericColumn"],
                        valueFormatter=_JS_SOLES,
                        width=100, minWidth=100, suppressSizeToFit=True)
    gb.configure_column("valor", header_name="Valor", type=["numericColumn"],
                        valueFormatter=_JS_SOLES, initialSort="desc",
                        width=112, minWidth=112, suppressSizeToFit=True)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    # Sin `update_on`: no hay nada que esta grilla le tenga que decir a
    # Python — ni la selección, que no tiene, ni el orden.
    AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_mov(), allow_unsafe_jscode=True, key=key, update_on=[],
    )
