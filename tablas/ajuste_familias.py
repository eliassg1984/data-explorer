"""tablas.ajuste_familias - las grillas de Ajuste › Cascada: el RESUMEN de
las familias del corte (una fila por familia, clic para enfocar) y los dos
DESGLOSES de la familia en foco (por área y por corte).

Nacieron el 2026-09-16, cuando la vista dejó de ser una tarjeta por familia
con cuatro dibujos del mismo saldo. Se pidió «datos intuitivos, no
interpretación», y a 283px de ancho por familia un gráfico no entra y un
número sí: el resumen pasó a ser una tabla, y lo que antes eran cinco
tarjetas son cinco filas que se comparan hacia abajo. Ver regla #441.

CADA COLUMNA DICE DE DÓNDE SALE, en el tooltip de su cabecera. No es
adorno: la tabla la leen contadores y jefes de almacén, que reconocen los
indicadores por su nombre estándar y desconfían de un número sin respaldo.
Las fuentes están verificadas, no citadas de memoria (regla #441).

EL LOOK Y LA FILA MARCADA son los de Compras › Semanal
(`tablas/compras_semanal.py`), no una copia: la familia en foco la marca el
dato `__sel`, con el mismo look que una fila seleccionada (regla #440).

LA KEY NO LLEVA EL FOCO, y por una razón: éstas se ordenan —clic en la
cabecera—, así que los montos viajan como número y el formato lo pone un
`valueFormatter`. Una key con el foco estrenaría grilla en cada clic y le
borraría al usuario el orden que acaba de elegir. (Semanal la llevaba y
dejó de hacerlo el 2026-09-19, cuando sus tablas también pasaron a
ordenarse: ver regla #471.) Como el foco de esta vista sólo lo cambia
esta misma grilla, la key lleva los DATOS (corte, familias, áreas) y no el
foco: una selección que vuelve es la vigente, y coincide con el foco
después del primer rerun. El precio es el de la regla #410 —una grilla que
conserva su key conserva el alto que reportó—, y lo paga el llamador atando
el alto del iframe.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, TEXTO_PRINCIPAL
from tablas._config import _parchar_iconos
# `_css`, `_AL_MONTAR` y `_CLASE_SEL` son privados de Semanal y se toman de
# ahí a propósito: la marca de la fila en foco, el ajuste de columnas al
# ancho y el look son UNA decisión, y dos copias se separan al primer
# retoque (el mismo motivo por el que Semanal toma `_css_look` de
# Volatilidad).
from tablas.compras_semanal import _AL_MONTAR
from tablas.compras_semanal import REGLAS_FILA as _REGLAS_FILA
from tablas.compras_semanal import JS_FILA_TOTAL as _JS_FILA_TOTAL
from tablas.compras_semanal import _css as _css_semanal
from tablas.compras_volatilidad import ALTO_FILA

# ── De dónde sale cada columna ──────────────────────────────────────────
# Lo que dice el tooltip de cada cabecera. Verificado el 2026-09-16:
#   · varianza neta / absoluta: práctica de conteo cíclico (inventoryops.com,
#     «Inventory Accuracy Measurement»; racklify.com, «Cycle Count Variance»)
#   · exactitud del registro (IRA): APICS Dictionary, 14.ª ed. (ASCM)
#   · análisis ABC: H. Ford Dickie, «ABC Inventory Analysis Shoots for
#     Dollars, not Pennies», Factory Management and Maintenance, jul. 1951
FUENTES = {
    "falto": "Suma de los ajustes negativos del corte.",
    "sobro": "Suma de los ajustes positivos del corte.",
    "total": ("Varianza absoluta: faltó y sobró sumados sin signo, sin que "
              "se compensen. Es la medida que recomienda la práctica de "
              "conteo cíclico para evaluar exactitud."),
    "saldo": ("Varianza neta: faltó y sobró con su signo. Se compensan entre "
              "sí, por eso esconde errores."),
    "n80": ("Cuántos productos explican el 80 % de «Faltó + sobró». Análisis "
            "ABC (Pareto): H. Ford Dickie, General Electric, 1951."),
    "exact": ("Exactitud del registro de inventario (IRA, APICS Dictionary): "
              "de las líneas con stock, cuántas cerraron sin diferencia. "
              "Tolerancia: {tol}. No cuenta las líneas en cero y cero."),
    "lineas": "Líneas con stock que cerraron con diferencia.",
    "areas": "Áreas con al menos una línea con stock en ese corte.",
    "valorizado": ("Valor del stock contado en el corte, a precio de "
                   "kardex. Es la escala contra la que se leen los "
                   "ajustes: un descuadre de S/ 30.000 pesa distinto sobre "
                   "S/ 2 millones que sobre S/ 50.000."),
}

# ── Formatos (el número viaja crudo para que la columna se ordene) ───────
_JS_SOLES = JsCode(
    "function(p){ if (p.value==null) return '';"
    " var v = Math.round(p.value);"
    " return (v < 0 ? '−' : '') + 'S/ ' + Math.abs(v).toLocaleString('es-PE'); }")
_JS_SALDO = JsCode(
    "function(p){ if (p.value==null) return '';"
    " var v = Math.round(p.value); if (v === 0) return 'S/ 0';"
    " return (v < 0 ? '−' : '+') + 'S/ ' + Math.abs(v).toLocaleString('es-PE'); }")
_JS_PCT = JsCode(
    "function(p){ if (p.value==null) return '–';"
    " return p.value.toLocaleString('es-PE',"
    " {minimumFractionDigits:1, maximumFractionDigits:1}) + ' %'; }")
# «4 de 12»: el número de productos del 80 % solo no dice si son muchos o
# pocos. El «de» sale de un campo oculto; la celda se ordena por el primero.
_JS_DE = JsCode(
    "function(p){ if (p.value==null) return '–';"
    " var n = p.data && p.data.__de; return n ? p.value + ' de ' + n : String(p.value); }")
# «−96.0 UND»: la cantidad con la unidad de Kardex al lado. La unidad viaja
# en un campo oculto para que la celda se siga ordenando por el número. La
# fila TOTAL no trae cantidad: sumar kilos con litros no da una unidad.
# DEBAJO DE 1, HASTA TRES DECIMALES (los del Kardex): con uno solo, 26 g
# salían «−0.0 KILOS» al lado de un monto, y 40 g de pimentón a S/ 569/kg,
# «0.0 KILOS · S/ 23». Medido desde junio 2026: 491 de 6.983 ajustes y 152
# de 6.005 stocks contados con valor se leían como cero. Regla #506.
_JS_CANTIDAD = JsCode(
    "function(p){ if (p.value==null || (p.node && p.node.rowPinned)) return '';"
    " var v = p.value; var u = (p.data && p.data.__um) || '';"
    " var a = Math.abs(v); var d = (a > 0 && a < 1) ? 3 : 1;"
    " return (v < 0 ? '−' : '') + a.toLocaleString('es-PE',"
    " {minimumFractionDigits:1, maximumFractionDigits:d}) + (u ? ' ' + u : ''); }")
_JS_ENTERO = JsCode(
    "function(p){ return p.value==null ? '' : Math.round(p.value).toLocaleString('es-PE'); }")


def _color(hex_):
    return JsCode(f"function(p){{ return {{'color':'{hex_}'}}; }}")


_JS_COLOR_SALDO = JsCode(
    "function(p){ if (p.value==null || Math.round(p.value)===0)"
    f" return {{'color':'{TEXTO_PRINCIPAL}'}};"
    f" return {{'color': p.value < 0 ? '{AJUSTE_NEG_TEXTO}' : '{AJUSTE_POS_TEXTO}',"
    " 'fontWeight':'600'};}")


def _barra_valor_style(pct_field, color_barra, color_texto):
    """cellStyle de una celda de monto CON barra de severidad detrás: la
    misma técnica de gradiente que `tablas/desktop.py::_pct_bar_style` (sin
    cellRenderer, que acá se ve como texto escapado — regla #25). El largo
    lo trae la fila en un campo oculto (`pct_field`, 0-100) para no meter
    datos dentro del `JsCode` (regla #226). El número va a la derecha; la
    barra crece desde la izquierda. Lo usa el detalle del Mapa de calor,
    regla #483."""
    return JsCode(f"""
        function(p){{
            var st = {{ color: '{color_texto}', fontWeight: '600',
                        textAlign: 'right', paddingRight: '10px' }};
            if (p.value == null || (p.node && p.node.rowPinned)) return st;
            var pct = (p.data && p.data['{pct_field}']) || 0;
            st.backgroundImage = 'linear-gradient(to right, {color_barra} 0%, '
                + '{color_barra} ' + pct + '%, transparent ' + pct + '%, '
                + 'transparent 100%)';
            st.backgroundRepeat = 'no-repeat';
            st.backgroundSize = '100% 68%';
            st.backgroundPosition = 'left center';
            return st;
        }}
    """)

# LA MARCA DE LA FILA EN FOCO VA POR `rowClassRules`, NO POR `getRowClass`.
# Ésta conserva su key, y AG Grid documenta que las clases de `getRowClass`
# se AGREGAN al refrescar la fila pero no se QUITAN: medido, después del
# primer clic quedaban marcadas la familia vieja y la nueva. `rowClassRules`
# evalúa la regla en cada refresco y quita la clase cuando deja de cumplirse.
# La regla vive en `tablas/compras_semanal.py` desde el 2026-09-19, cuando
# Semanal también dejó de estrenar grilla en cada clic para que sus tablas
# se pudieran ordenar (#471): una sola regla para las dos marcas.


# La fila TOTAL (`_JS_FILA_TOTAL`) vivía acá hasta el 2026-09-17: se mudó a
# `tablas/compras_semanal.py` cuando Semanal sumó la suya (regla #454), junto
# con la regla de `.ag-floating-bottom` que `_css_semanal()` ya trae.


def _grid_base(tp):
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    for _c in tp.columns:
        if _c.startswith("__"):
            gb.configure_column(_c, hide=True)
    return gb


def _col_monto(gb, campo, titulo, tooltip, formato=_JS_SOLES, estilo=None,
               ancho=112, **kw):
    # 112: «−S/ 115,657» mide ~88px a 13px, más los 8+8 de padding.
    gb.configure_column(campo, header_name=titulo, type=["numericColumn"],
                        valueFormatter=formato, cellStyle=estilo,
                        headerTooltip=tooltip, width=ancho, minWidth=ancho,
                        suppressSizeToFit=True, **kw)


def _css(movil=False):
    css = _css_semanal()
    # La cabecera de una columna ordenable muestra la flecha: sin aire, en
    # 112px el rótulo «Faltó + sobró» y la flecha se pisan.
    css[".ag-header-cell-label"] = {"gap": "4px"}
    # (La regla de `.ag-floating-bottom` —una sola línea sobre la fila TOTAL,
    # #364— llega con `_css_semanal()` desde el 2026-09-17.)
    if movil:
        # EN EL CELULAR LA BARRA HORIZONTAL VUELVE. Semanal la esconde porque
        # sus columnas entran en media tarjeta de escritorio; éstas suman
        # 868px de mínimo y en 293px de iframe (medido a 375 de ancho) se
        # veían tres de siete columnas, sin forma de llegar a las otras.
        css[".ag-body-horizontal-scroll"] = {"display": "flex !important"}
    return css


# Lo que agrega la barra horizontal al alto de la grilla en el celular.
ALTO_BARRA_MOVIL = 10


def _col_nombre(gb, campo, titulo, movil, ancho_movil=128):
    """La columna del nombre. En el celular va FIJA a la izquierda y angosta:
    al deslizar los números, el nombre de la fila no se va de la vista."""
    if movil:
        gb.configure_column(campo, header_name=titulo, pinned="left",
                            width=ancho_movil, minWidth=ancho_movil,
                            tooltipField=campo, suppressSizeToFit=True)
    else:
        gb.configure_column(campo, header_name=titulo, minWidth=180,
                            flex=1, tooltipField=campo)


def renderizar_familias_ajuste(tp, total, altura, key, tolerancia,
                               movil=False, con_valorizado=False):
    """Una fila por FAMILIA del corte, con la fila TOTAL fija abajo.

    `tp` trae `familia`, `falto`, `sobro`, `total`, `saldo`, `n80`,
    `exact` y las ocultas `__de` (productos con diferencia, el «de» de la
    columna del 80 %) y `__sel` (True en la familia que muestra el
    detalle). `total` es el dict de la fila fija, con las mismas claves.
    `tolerancia` es el texto que la cabecera de «Exactitud» declara.
    `con_valorizado=True` agrega la columna «Valorizado total» (soles, en
    `tp["valorizado"]`), que va DESPUÉS de Saldo — el llamador la pone en
    esa posición del df porque el orden de columnas lo decide
    `from_dataframe`, no `configure_column`.

    Devuelve la familia de la fila seleccionada, o None. Es la selección
    VIGENTE (la key no cambia con el foco, ver el docstring del módulo): el
    llamador la compara contra el foco y sólo actúa si difiere."""
    gb = _grid_base(tp)
    _col_nombre(gb, "familia", "Familia", movil)
    _col_monto(gb, "falto", "Faltó", FUENTES["falto"],
               estilo=_color(AJUSTE_NEG_TEXTO))
    _col_monto(gb, "sobro", "Sobró", FUENTES["sobro"],
               estilo=_color(AJUSTE_POS_TEXTO))
    # La columna que ordena de entrada: es el tamaño del descuadre, y la
    # vista abre en la familia que más descuadró.
    _col_monto(gb, "total", "Faltó + sobró", FUENTES["total"], ancho=124,
               estilo=JsCode("function(p){ return {'fontWeight':'700'}; }"),
               sort="desc")
    _col_monto(gb, "saldo", "Saldo", FUENTES["saldo"], formato=_JS_SALDO,
               estilo=_JS_COLOR_SALDO)
    if con_valorizado:
        # Neutra (no es un descuadre): número de la casa, sin rojo/verde.
        _col_monto(gb, "valorizado", "Valorizado total", FUENTES["valorizado"],
                   ancho=132, estilo=_color(TEXTO_PRINCIPAL))
    gb.configure_column("n80", header_name="Productos 80 %",
                        type=["numericColumn"], valueFormatter=_JS_DE,
                        headerTooltip=FUENTES["n80"], width=124, minWidth=124,
                        suppressSizeToFit=True)
    gb.configure_column("exact", header_name="Exactitud",
                        type=["numericColumn"], valueFormatter=_JS_PCT,
                        headerTooltip=FUENTES["exact"].format(tol=tolerancia),
                        width=104, minWidth=104, suppressSizeToFit=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=_REGLAS_FILA,
        getRowStyle=_JS_FILA_TOTAL, pinnedBottomRowData=[total],
        onGridReady=_AL_MONTAR)
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(movil), allow_unsafe_jscode=True, key=key,
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        # `__crudo` y no la columna visible: ésa pasó por `nombre_propio` y
        # ya no es la clave con la que se filtra el parquet.
        fila = sel.iloc[0]
        return str(fila["__crudo"] if "__crudo" in fila else fila["familia"])
    return None


def renderizar_desglose_ajuste(tp, columnas, altura, key, movil=False,
                               total=None, barra=None):
    """Un desglose de la familia en foco: sus líneas, sus áreas o sus
    cortes. Se lee y se ordena; no se clickea.

    `columnas` son tuplas `(campo, título, clase)` o `(campo, título, clase,
    orden)`, donde clase es `"nombre"`, `"texto"`, `"falto"`, `"sobro"`,
    `"total"`, `"saldo"`, `"cantidad"` o `"entero"` — lo que decide formato,
    color y el tooltip de la cabecera — y `orden` («asc»/«desc») es el orden
    con que abre. `total` es el dict de la fila TOTAL fija, si la lleva.

    `barra=(campo, color_barra, color_texto)` dibuja una barra de severidad
    detrás de ese campo (soles), con el largo en la columna oculta
    `tp["__barpct"]` (0-100, la pone el llamador). Anula la clase de esa
    columna. Lo usa el detalle del Mapa de calor (regla #483); la Cascada no
    lo pasa, así que sus desgloses quedan sin barra."""
    # EL ORDEN DE LAS COLUMNAS LO DECIDE EL DATAFRAME, no `configure_column`:
    # `GridOptionsBuilder.from_dataframe` arma las columnas en el orden del
    # df y configurarlas después no las mueve. Medido: pedidas Cantidad ·
    # Valor, salían Valor · Cantidad.
    _orden = [c[0] for c in columnas]
    tp = tp[_orden + [c for c in tp.columns if c not in _orden]]
    gb = _grid_base(tp)
    for col in columnas:
        campo, titulo, clase = col[:3]
        orden = {"sort": col[3]} if len(col) > 3 else {}
        if barra is not None and campo == barra[0]:
            _col_monto(gb, campo, titulo, FUENTES.get(clase, ""),
                       estilo=_barra_valor_style("__barpct", barra[1],
                                                 barra[2]),
                       ancho=132, **orden)
        elif clase == "nombre":
            _col_nombre(gb, campo, titulo, movil)
        elif clase == "texto":
            gb.configure_column(campo, header_name=titulo, width=132,
                                minWidth=132, tooltipField=campo,
                                suppressSizeToFit=True)
        elif clase == "cantidad":
            gb.configure_column(campo, header_name=titulo,
                                type=["numericColumn"],
                                valueFormatter=_JS_CANTIDAD, width=118,
                                minWidth=118, suppressSizeToFit=True, **orden)
        elif clase == "falto":
            _col_monto(gb, campo, titulo, FUENTES["falto"],
                       estilo=_color(AJUSTE_NEG_TEXTO), **orden)
        elif clase == "sobro":
            _col_monto(gb, campo, titulo, FUENTES["sobro"],
                       estilo=_color(AJUSTE_POS_TEXTO), **orden)
        elif clase == "total":
            _col_monto(gb, campo, titulo, FUENTES["total"], ancho=124,
                       estilo=JsCode(
                           "function(p){ return {'fontWeight':'700'}; }"))
        elif clase == "saldo":
            _col_monto(gb, campo, titulo, FUENTES["saldo"],
                       formato=_JS_SALDO, estilo=_JS_COLOR_SALDO)
        else:
            gb.configure_column(campo, header_name=titulo,
                                type=["numericColumn"],
                                valueFormatter=_JS_ENTERO,
                                headerTooltip=FUENTES.get(campo, ""),
                                width=120, minWidth=120,
                                suppressSizeToFit=True)
    _extra = ({"getRowStyle": _JS_FILA_TOTAL, "pinnedBottomRowData": [total]}
              if total else {})
    gb.configure_grid_options(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=_REGLAS_FILA,
        onGridReady=_AL_MONTAR, **_extra)
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(movil), allow_unsafe_jscode=True, key=key,
    )
