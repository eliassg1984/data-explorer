"""tablas.movimientos_periodo - las tres grillas de «Requerimientos por
período» (graficos/movimientos_periodo.py).

La tarjeta es la gemela de «Compra por período» (graficos/compras/
semanal.py), y su zona de abajo también: «Resumen» —una fila por barra— y
«Detalle» —los requerimientos del período en foco y, al costado, las líneas
del elegido—. No son las mismas grillas de Compras porque sus columnas son
otras:

  · el Resumen cuenta REQUERIMIENTOS y ÁREAS donde el de Compras cuenta
    documentos y desglosa familias, y suma la columna Estado;
  · la lista de requerimientos lleva la HORA del registro, el código y el
    área, y marca los anulados;
  · las líneas son las mismas cuatro columnas de Compras, pero la cantidad
    lleva los decimales que tiene (`_JS_CANT_REQ`): una cocina pide gramos.

Lo que sí comparten con Compras es todo lo demás, y viene de allá: el look
(`_css`), los formatos de celda, la fila TOTAL fija, la fila marcada por
`rowClassRules` y el `onGridReady` que ajusta las columnas (reglas #440,
#441 y #471). Dos tarjetas gemelas con dos looks de tabla no se leerían
como la misma cosa (regla #404).

EL ESTADO SE ESCRIBE SÓLO CUANDO ES LA EXCEPCIÓN (regla #239): el 97 % de
los requerimientos está procesado, así que una columna que dijera
«Procesado» en cada fila taparía a las que no. En el Resumen las filas sin
novedad llevan un «✓» gris; en la lista, el anulado se lee en la celda del
valor —su monto pasa al tooltip: suele ser chico, y la mitad llega con
cantidad 0— y su fila entera va apagada. Ver `arquitectura.md` regla #508.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import ADVERTENCIA_TEXTO, ERROR, GRIS_TEXTO_SUAVE
from tablas._config import _parchar_iconos
# Privados de allá, y a propósito: son el look y los formatos de las
# grillas de «Compra por período», que esta tarjeta calca. Mismo criterio
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

_JS_VALOR_REQ = JsCode(
    "function(p){ var d = p.data || {};"
    " if (d.__estado === 'anulado') return 'Anulado';"
    " var v = p.value; if (v == null) return '—';"
    " if (typeof v !== 'number') return String(v);"
    " return (v < 0 ? '−' : '') + 'S/ ' + Math.abs(v).toLocaleString("
    "'es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }")
"""El valorizado del requerimiento, o «Anulado» en su lugar.

El anulado viaja con su valor (a menudo 0) para que la columna se siga
ordenando, y el monto se lee en el tooltip (`_TIP_VALOR_REQ`): lo que cambia
es sólo lo que se ESCRIBE. En la fila TOTAL fija el valor llega ya
formateado como texto y se devuelve tal cual."""

_JS_CANT_REQ = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'number' || isNaN(v))"
    "   return v == null ? (p.node && p.node.rowPinned ? '' : '—')"
    "                    : String(v);"
    " var dec = Math.abs(v) < 1 ? 3 : 2;"
    " return v.toLocaleString('es-PE', {minimumFractionDigits: 0,"
    "                                   maximumFractionDigits: dec}); }")
"""Cantidad con los decimales que TIENE: «144», «16.5», «0.04», «0.026».

No el `_JS_CANTIDAD` de las líneas de Compras (un decimal fijo): un
requerimiento de cocina pide gramos, y con un decimal «40 g de pimentón»
sale «0.0» al lado de un valor — la misma trampa que la regla #506 midió en
Ajuste. Debajo de 1, hasta tres decimales, como el Kardex."""

_TIP_VALOR_REQ = JsCode(
    "function(p){ var d = p.data || {}, v = p.value;"
    " var s = typeof v === 'number' ? 'S/ ' + v.toLocaleString('es-PE',"
    "   {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '';"
    " if (d.__estado === 'anulado') return 'Anulado · ' + s"
    "   + ' · no suma en la barra ni en los totales';"
    " if (d.__estado === 'sin procesar') return 'Sin procesar (estado"
    " Generado): todavía no se procesó';"
    " return ''; }")
"""El tooltip de la celda del valor: el MONTO del anulado —que la celda no
escribe— y por qué no suma, o qué quiere decir «sin procesar»."""

REGLAS_FILA_REQ = {
    **REGLAS_FILA,
    "mp-anulado": JsCode(
        "function(p){ return !!(p.data && p.data.__estado === 'anulado'); }"),
    "mp-sinproc": JsCode(
        "function(p){ return !!(p.data && p.data.__estado === 'sin procesar');"
        " }"),
}
"""La fila marcada de Compras (`__sel`) más las dos excepciones de estado.

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


def _css_req():
    """El look de Compras más los colores de estado de estas dos grillas."""
    css = _css()
    css[".ag-row.mp-anulado .ag-cell"] = {
        "color": f"{GRIS_TEXTO_SUAVE} !important"}
    css[".ag-row.mp-anulado .ag-cell[col-id='valor']"] = {
        "color": f"{ERROR} !important", "font-weight": "600 !important"}
    css[".ag-row.mp-sinproc .ag-cell[col-id='valor']"] = {
        "color": f"{ADVERTENCIA_TEXTO} !important",
        "font-weight": "600 !important"}
    css[".ag-cell.mp-e-ok"] = {"color": f"{GRIS_TEXTO_SUAVE} !important"}
    css[".ag-cell.mp-e-anul"] = {
        "color": f"{ERROR} !important", "font-weight": "600 !important"}
    css[".ag-cell.mp-e-sinp"] = {
        "color": f"{ADVERTENCIA_TEXTO} !important",
        "font-weight": "600 !important"}
    return css


def renderizar_periodos_req(tp, altura, key, rotulo_periodo="Período",
                            ver_variacion=True, total=None):
    """Una fila por BARRA del gráfico, en el orden del eje.

    `tp` trae `periodo` (el nombre de la barra, ya legible), los números
    crudos `reqs`, `lineas`, `areas`, `valor`, `parte` (0-1) y `variacion`
    (en %, o vacía), el texto `estado`, y seis ocultas: `__vtxt` (qué
    escribir cuando no hay porcentaje), `__nota` (por qué no lo hay),
    `__anota` (qué áreas pidieron: el tooltip de «Áreas»), `__eclase` (el
    color del estado), `__clave` (la clave del período, la del eje) y
    `__sel` (la barra en foco).

    SIN `initialSort`, como el Resumen de Compras: las filas abren en el
    orden del EJE porque la tabla es el gráfico escrito. Se ordenan igual con
    un clic en la cabecera, que no cuesta ninguna corrida.

    Devuelve la `__clave` de la fila SELECCIONADA, o None: un clic en una
    fila abre su Detalle, igual que un clic en su barra. Como con la lista
    de requerimientos, es la selección VIGENTE; el llamador estrena la
    grilla (su key) cada vez que actúa sobre ella."""
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
    gb.configure_column("reqs", header_name="Requerimientos",
                        type=["numericColumn"], valueFormatter=_JS_ENTERO,
                        headerTooltip="Requerimientos del período. No cuenta "
                                      "los anulados ni los que vienen sin "
                                      "ítems",
                        width=132, minWidth=132, suppressSizeToFit=True)
    gb.configure_column("lineas", header_name="Líneas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        headerTooltip="Líneas de esos requerimientos: un "
                                      "producto pedido es una línea",
                        width=82, minWidth=82, suppressSizeToFit=True)
    gb.configure_column("areas", header_name="Áreas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO, tooltipField="__anota",
                        headerTooltip="Cuántas áreas pidieron en el período. "
                                      "Cuáles, en el tooltip de la celda",
                        width=78, minWidth=78, suppressSizeToFit=True)
    gb.configure_column("valor", header_name="Valorizado",
                        type=["numericColumn"],
                        valueFormatter=_JS_VALOR_REQ,
                        headerTooltip="Valorizado requerido del período",
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
        custom_css=_css_req(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty and "__clave" in sel.columns:
        return str(sel.iloc[0]["__clave"])
    return None


def renderizar_requerimientos(tp, altura, key, total=None):
    """Una fila por REQUERIMIENTO del período en foco.

    `tp` trae `registro` (fecha y hora en ISO, «2026-09-22 14:24»),
    `codigo`, `area`, `lineas` y `valor` —números crudos: el formato lo pone
    la grilla, para que se ordenen— más tres ocultas: `__estado` («», o
    «anulado» / «sin procesar»), `__req` (el código, que es lo que devuelve)
    y `__sel` (True en el que muestra la tabla de al lado).

    Los anulados SE LISTAN, apagados y con «Anulado» donde iría el valor:
    quien abre el detalle de un período con «3 anulados» en el Resumen
    tiene que poder ver cuáles fueron. No suman en la fila TOTAL, que es la
    misma cuenta que la barra.

    Devuelve el `__req` de la fila SELECCIONADA, o None — la selección
    vigente, no un clic de esta vuelta: el llamador la compara contra el
    requerimiento que ya muestra (`compras_semanal`, regla #471)."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    # 104: «22/09 14:24» mide ~74px a 13px, más el padding y la flecha.
    gb.configure_column("registro", header_name="Registro",
                        valueFormatter=_JS_FECHA_HORA,
                        headerTooltip="Fecha y hora de registro del "
                                      "requerimiento",
                        width=104, minWidth=104, suppressSizeToFit=True)
    # 104: «2609000407» —diez dígitos, los cuatro primeros son año y mes—
    # mide ~72px.
    gb.configure_column("codigo", header_name="Código",
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_column("area", header_name="Área", width=140, minWidth=80,
                        tooltipField="area")
    gb.configure_column("lineas", header_name="Líneas", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        width=76, minWidth=76, suppressSizeToFit=True)
    # `initialSort` y no `sort`, por la regla #471: st_aggrid le vuelve a
    # pasar las `columnDefs` en cada corrida y `sort` pisaría el orden que
    # haya elegido el usuario.
    gb.configure_column("valor", header_name="Valorizado",
                        type=["numericColumn"], valueFormatter=_JS_VALOR_REQ,
                        tooltipValueGetter=_TIP_VALOR_REQ, initialSort="desc",
                        width=120, minWidth=120, suppressSizeToFit=True)
    for oculta in ("__estado", "__req", "__sel"):
        gb.configure_column(oculta, hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=REGLAS_FILA_REQ,
        onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_req(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__req"])
    return None


def renderizar_lineas_req(tp, altura, key, total=None):
    """Las líneas de UN requerimiento: `prod` y los números crudos `cant`,
    `punit` y `valor` —el formato lo pone la grilla, para que se ordenen—.
    Sin selección: se lee, no se clickea. `total` es la fila TOTAL fija.

    Es `compras_semanal.renderizar_lineas_semanal` con otra cantidad (ver
    `_JS_CANT_REQ`). Sin fecha, código ni área, a propósito: son los mismos
    en todas las filas y ya los dice la fila marcada de al lado."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("prod", header_name="Producto", width=180,
                        minWidth=100, tooltipField="prod")
    gb.configure_column("cant", header_name="Cantidad", type=["numericColumn"],
                        valueFormatter=_JS_CANT_REQ,
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
        custom_css=_css_req(), allow_unsafe_jscode=True, key=key, update_on=[],
    )
