"""tablas.ventas_resumen - las grillas de la zona de abajo de «Tendencia
diaria de venta» (graficos/ventas_resumen.py).

Nacieron el 2026-09-24, a pedido, mirando la vista junto a «Compras por
período»: «le falta la similitud respecto a interactuar con las tablas de
abajo, o sea que se acorte; las tablas de abajo no se parecen en estilo».
Hasta ese día la zona de abajo eran dos `st.dataframe` FUERA de la tarjeta,
debajo de una figura que no cambiaba de alto. Ahora es la de Compras:

  · «Resumen» — una fila por DÍA (una por barra), con la venta, su % de la
    vista, una columna por canal, los clientes, el ticket y la variación.
    Un clic en una fila abre su Detalle, igual que un clic en su barra.
  · «Detalle» — los PEDIDOS del día en foco a la izquierda y, al costado,
    los platos del elegido (`movimientos_periodo.renderizar_lineas_mov`,
    que es la grilla de líneas de Compras con la cantidad sin decimales de
    más).

El look, los formatos, la fila TOTAL fija, la fila marcada por
`rowClassRules` y el `onGridReady` son los de `tablas/compras_semanal.py`:
tablas gemelas con dos looks no se leen como la misma cosa (regla #404).
Lo único al revés es el COLOR de la variación: en Ventas subir es la buena
noticia (verde), en Compras gastar más es rojo. Regla #516.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import ERROR, EXITO, GRIS_TEXTO
from tablas._config import _parchar_iconos
# Privados de allá, a propósito: son el look y los formatos de las grillas de
# «Compra por período», que éstas calcan. Mismo criterio que
# `tablas/movimientos_periodo.py`.
from tablas.compras_semanal import (
    _AL_CAMBIAR_FILAS, _AL_MONTAR, _JS_COMPACTO, _JS_ENTERO, _JS_PARTE,
    _JS_SOLES, _JS_VARIACION, _TOOLTIP_FAMILIA, _con_total, _css, REGLAS_FILA,
)
from tablas.compras_volatilidad import ALTO_FILA
from tablas.movimientos_periodo import _JS_FECHA_HORA

_JS_HORA = JsCode(
    "function(p){ var v = p.value;"
    " if (typeof v !== 'string' || v.length < 16 || v.charAt(4) !== '-')"
    " return v == null ? '' : String(v);"
    " return v.slice(11, 16); }")
"""«2026-09-22 14:24» → «14:24», cuando todas las filas son del mismo día."""

_STYLE_VARIACION_VENTA = JsCode("""
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
   .replace("__SUBE__", EXITO).replace("__BAJA__", ERROR))
"""`compras_semanal._STYLE_VARIACION` con los colores al revés: verde si se
vendió más que el día anterior. Es el mismo color de la etiqueta de la
barra (`ventas_resumen._renglones_barra`)."""

_JS_TICKET = JsCode(
    "function(p){ var v = p.value; if (v == null) return '—';"
    " if (typeof v !== 'number') return String(v);"
    " return 'S/ ' + v.toLocaleString('es-PE',"
    " {minimumFractionDigits: 2, maximumFractionDigits: 2}); }")


def renderizar_dias_venta(tp, altura, key, rotulo_periodo="Día", canales=(),
                          vol_label=None, total=None):
    """Una fila por DÍA del gráfico, en el orden del eje.

    `tp` trae `periodo` (el día, ya legible: «Mié 03/09»), los números
    crudos `valor`, `parte` (0-1), una columna por canal (`canales` son
    `(columna, rótulo)` en el orden de la pila), `pax` y `ticket` si hay
    volumen (`vol_label` es su rótulo: «Clientes» o «Pedidos») y la
    `variacion` en % (o vacía), más cuatro ocultas: `__vtxt` (qué escribir
    sin porcentaje), `__nota` (por qué no lo hay), `__clave` (la clave del
    período, la del eje) y `__sel` (el período en foco). `rotulo_periodo`
    es la cabecera de la primera columna: la granularidad.

    Sin `initialSort`: la tabla es el gráfico escrito y abre en su orden.
    Devuelve la `__clave` de la fila SELECCIONADA, o None — un clic en una
    fila abre su Detalle, como en Movimientos. Es la selección VIGENTE; el
    llamador estrena la grilla (su key) cada vez que actúa sobre ella."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    # Anchos con la cuenta de Compras (`compras_semanal._COLS_ANCHA`): el
    # peor dato a 13px, más 8+8 de padding y los ~14 de la flecha de
    # ordenar. «Día» es la única que se estira.
    gb.configure_column("periodo", header_name=rotulo_periodo, minWidth=110,
                        tooltipField="periodo")
    gb.configure_column("valor", header_name="Venta", type=["numericColumn"],
                        valueFormatter=_JS_SOLES,
                        headerTooltip="Venta del día",
                        width=120, minWidth=120, suppressSizeToFit=True)
    gb.configure_column("parte", header_name="% del total",
                        type=["numericColumn"], valueFormatter=_JS_PARTE,
                        headerTooltip="Cuánto pesa este día en el total de "
                                      "la vista (el de la fila de arriba)",
                        width=104, minWidth=104, suppressSizeToFit=True)
    # Los canales, con el formato compacto de las familias de Compras: el
    # valor exacto y su % de la barra van al tooltip de la celda.
    for _col, _rot in canales:
        gb.configure_column(_col, header_name=_rot, type=["numericColumn"],
                            valueFormatter=_JS_COMPACTO,
                            tooltipValueGetter=_TOOLTIP_FAMILIA,
                            headerTooltip=f"{_rot} · venta de ese canal en "
                                          "cada día",
                            width=104, minWidth=94, suppressSizeToFit=True)
    if vol_label:
        gb.configure_column("pax", header_name=vol_label,
                            type=["numericColumn"], valueFormatter=_JS_ENTERO,
                            width=92, minWidth=92, suppressSizeToFit=True)
        gb.configure_column("ticket", header_name="Ticket",
                            type=["numericColumn"], valueFormatter=_JS_TICKET,
                            headerTooltip=f"Venta ÷ {vol_label.lower()} del "
                                          "día",
                            width=100, minWidth=100, suppressSizeToFit=True)
    gb.configure_column("variacion", header_name="Variación",
                        type=["numericColumn"], valueFormatter=_JS_VARIACION,
                        cellStyle=_STYLE_VARIACION_VENTA,
                        tooltipField="__nota",
                        headerTooltip="Variación contra la barra ANTERIOR "
                                      "del gráfico. Un período que el rango "
                                      "corta dice «parcial»",
                        width=104, minWidth=104, suppressSizeToFit=True)
    for oculta in ("__vtxt", "__nota", "__clave", "__sel"):
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
        custom_css=_css(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty and "__clave" in sel.columns:
        return str(sel.iloc[0]["__clave"])
    return None


def renderizar_pedidos_venta(tp, altura, key, ver_canal=False,
                             ver_mesero=True, solo_hora=True, total=None):
    """Una fila por PEDIDO del día en foco.

    `tp` trae `hora` (fecha y hora en ISO, que ordena bien como texto; la
    celda dice sólo la hora con `solo_hora`, o «03/09 14:16»), `mesero`, `canal`,
    `pax`, `platos` (líneas del pedido) y `valor` —números crudos: el
    formato lo pone la grilla— más dos ocultas: `__ped` (la clave del
    pedido, lo que devuelve) y `__sel` (el que muestra la tabla de al lado).

    `ver_canal` en False con un solo canal en la vista: una columna que dice
    «En el Local» en cada fila es ruido (regla #239).

    Devuelve el `__ped` de la fila SELECCIONADA, o None — la selección
    vigente: el llamador la compara contra el pedido que ya muestra."""
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("hora", header_name="Hora" if solo_hora else "Registro",
                        valueFormatter=_JS_HORA if solo_hora else _JS_FECHA_HORA,
                        tooltipField="__doc",
                        headerTooltip="Hora del comprobante. Su número, en "
                                      "el tooltip de la celda",
                        width=72 if solo_hora else 104,
                        minWidth=72 if solo_hora else 104,
                        suppressSizeToFit=True)
    gb.configure_column("mesero", header_name="Mesero", hide=not ver_mesero,
                        width=130, minWidth=80, tooltipField="mesero")
    gb.configure_column("canal", header_name="Canal", hide=not ver_canal,
                        width=100, minWidth=80, tooltipField="canal")
    gb.configure_column("pax", header_name="Pax", type=["numericColumn"],
                        valueFormatter=_JS_ENTERO,
                        width=60, minWidth=60, suppressSizeToFit=True)
    gb.configure_column("platos", header_name="Platos",
                        type=["numericColumn"], valueFormatter=_JS_ENTERO,
                        headerTooltip="Líneas del pedido: un plato es una "
                                      "línea, con su cantidad",
                        width=76, minWidth=76, suppressSizeToFit=True)
    # `initialSort` y no `sort` (regla #471): st_aggrid le vuelve a pasar
    # las `columnDefs` en cada corrida y `sort` pisaría el orden elegido.
    gb.configure_column("valor", header_name="Venta", type=["numericColumn"],
                        valueFormatter=_JS_SOLES, initialSort="desc",
                        # 120: «S/ 35,730.90» del total de una semana, a
                        # 13px, más el padding y la flecha de ordenar.
                        width=120, minWidth=120, suppressSizeToFit=True)
    for oculta in ("__doc", "__ped", "__sel"):
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
        custom_css=_css(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__ped"])
    return None
