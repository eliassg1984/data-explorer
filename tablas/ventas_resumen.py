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

2026-09-24 (2) — EL RESUMEN ES LA «B» DEL MOCKUP (regla #518): nueve
columnas (los cuatro precios, % de costo, pax, ticket y la variación) y una
franja que se despliega en el navegador al hacer clic en la fila, con los
canales, propinas, descuentos, cortesías y el costo. «Ver pedidos» en la
franja abre el Detalle.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import (
    ACENTO, ACENTO_TEXTO, ADVERTENCIA_BORDE, ADVERTENCIA_FONDO,
    ADVERTENCIA_TEXTO, BLANCO, ERROR, ERROR_FONDO, EXITO, GRIS_BORDE,
    GRIS_TEXTO, GRIS_TEXTO_MEDIO, LAVANDA_BORDE, LAVANDA_FONDO,
    PALETA_SERIES, TEXTO_PRINCIPAL,
)
from tablas._config import _parchar_iconos
# Privados de allá, a propósito: son el look y los formatos de las grillas de
# «Compra por período», que éstas calcan. Mismo criterio que
# `tablas/movimientos_periodo.py`.
from tablas.compras_semanal import (
    _AL_CAMBIAR_FILAS, _AL_MONTAR, _JS_ENTERO, _JS_SOLES, _JS_VARIACION,
    _con_total, _css, REGLAS_FILA,
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


_JS_SOLES0 = JsCode(
    "function(p){ var v = p.value; if (v == null) return '—';"
    " if (typeof v !== 'number') return String(v);"
    " return (v < 0 ? '−' : '') + 'S/ ' + Math.round(Math.abs(v))"
    ".toLocaleString('es-PE'); }")
"""«S/ 14,807», sin céntimos: con cuatro columnas de soles (Carta, Venta,
Neto, Costo) los dos decimales costaban 24px cada una, y en una fila de
día los céntimos no dicen nada. El total fijo llega ya escrito."""

_FORMATOS = {"soles0": _JS_SOLES0, "soles": _JS_SOLES, "entero": _JS_ENTERO}
"""Los formatos simples de una columna de subvista (ver `columnas` en
`renderizar_dias_venta`)."""

# ── Celda con valor + nota (la variación al lado del número) ───────────────
# Un solo componente para todas las celdas compuestas (regla #226: un JsCode,
# no uno por columna). Lee de la fila, que Python ya dejó escrita:
#   __t_<col>   el texto principal          __c_<col>  su clase
#   __v_<col>   la nota chica (variación)   __vc_<col> su clase
#   __b_<col>   una bandera («revisar»)
#   __w_<col>   la barrita (0-1)            __wc_<col> su tono
# La fila TOTAL fija no trae esos campos y cae al valor tal cual.
_R_CELDA = JsCode("""
class CeldaVenta {
    init(p) {
        var d = p.data || {}, c = p.colDef.field;
        this.e = document.createElement('span');
        var t = d['__t_' + c];
        var a = document.createElement('span');
        // La fila TOTAL fija manda su valor YA escrito: en una columna que
        // AG Grid infiere numérica, `valueFormatted` de un texto sale
        // «Invalid Number». El texto va tal cual.
        a.textContent = (t != null) ? t
            : (typeof p.value === 'string') ? p.value
            : (p.valueFormatted != null ? p.valueFormatted
               : (p.value == null ? '' : String(p.value)));
        if (d['__c_' + c]) a.className = d['__c_' + c];
        // La BARRITA de comparación (regla #519): el valor contra el mayor
        // de la columna, pintado de fondo de la celda. Deja comparar un
        // período con los demás sin leer los números.
        var w = d['__w_' + c];
        if (w != null) {
            a.className += ' vr-bar ' + (d['__wc_' + c] || '');
            a.style.setProperty('--w',
                (Math.max(0, Math.min(1, w)) * 100).toFixed(1) + '%');
        }
        this.e.appendChild(a);
        if (d['__v_' + c]) {
            var v = document.createElement('span');
            v.textContent = d['__v_' + c];
            v.className = 'vr-nota ' + (d['__vc_' + c] || '');
            this.e.appendChild(v);
        }
        if (d['__b_' + c]) {
            var b = document.createElement('span');
            b.textContent = d['__b_' + c];
            b.className = 'vr-bandera';
            this.e.appendChild(b);
        }
    }
    getGui() { return this.e; }
    refresh() { return false; }
}
""")

# ── La franja que se despliega debajo de un día ─────────────────────────────
# Es una FILA DE ANCHO COMPLETO (Full Width Rows, AG Grid Community) que se
# agrega y se quita en el navegador con una transacción: abrir un día no le
# cuesta ninguna corrida a Python. El contenido lo escribe Python en
# `__html` —texto que arma él mismo, con los nombres escapados— y viaja
# como dato de la fila (regla #226: nunca datos adentro de un JsCode).
# El botón «Ver pedidos» SELECCIONA la fila del día: eso sí llega a Python
# (`update_on=["selectionChanged"]`) y abre el Detalle.
_R_FRANJA = JsCode("""
class FranjaVenta {
    init(p) {
        var e = document.createElement('div');
        e.className = 'vr-franja';
        e.innerHTML = (p.data && p.data.__html) || '';
        var boton = e.querySelector('.vr-ver');
        if (boton) {
            boton.addEventListener('click', function (ev) {
                ev.stopPropagation();
                var n = p.api.getRowNode(p.data.__padre);
                if (n) n.setSelected(true, true);
            });
        }
        this.e = e;
        // El alto sale del contenido: los bloques se reacomodan con el ancho
        // (a 1366 van en una línea, más angosto en dos) y un alto fijo
        // cortaría o dejaría aire.
        setTimeout(function () {
            try {
                var h = Math.ceil(e.scrollHeight) + 2;
                if (Math.abs((p.node.rowHeight || 0) - h) > 1) {
                    p.node.setRowHeight(h);
                    p.api.onRowHeightChanged();
                }
            } catch (x) {}
        }, 0);
    }
    getGui() { return this.e; }
    refresh() { return false; }
}
""")

_AL_CLIC_DIA = JsCode("""
function(e) {
    var d = e.data, api = e.api;
    if (!d || d.__detalle || (e.node && e.node.rowPinned)) return;
    var id = d.__id + '__det', yaEstaba = !!api.getRowNode(id);
    var quitar = [], marcadas = [];
    api.forEachNode(function (n) {
        if (!n.data) return;
        if (n.data.__detalle) quitar.push(n.data);
        if (n.data.__abierta) { n.data.__abierta = false; marcadas.push(n); }
    });
    if (quitar.length) api.applyTransaction({remove: quitar});
    if (!yaEstaba) {
        // La franja copia los números del día: si el usuario ordenó por una
        // columna, cae pegada a su día y no en otro lado de la tabla.
        var det = Object.assign({}, d, {__id: id, __detalle: true,
                                        __padre: d.__id, __sel: false});
        api.applyTransaction({add: [det], addIndex: e.rowIndex + 1});
        d.__abierta = true; marcadas.push(e.node);
        setTimeout(function () {
            var n = api.getRowNode(id);
            if (n) api.ensureNodeVisible(n, 'bottom');
        }, 30);
    }
    if (marcadas.length) api.redrawRows({rowNodes: marcadas});
}
""")

_REGLAS_DIA = {**REGLAS_FILA, "vr-abierta": JsCode(
    "function(p){ return !!(p.data && p.data.__abierta); }")}


def _css_dias():
    """El look de Compras más la franja y las notas de variación."""
    css = _css()
    css[".ag-row.vr-abierta"] = {
        "background-color": f"{LAVANDA_FONDO} !important",
        "box-shadow": f"inset 3px 0 0 0 {ACENTO} !important"}
    css[".vr-nota"] = {"font-size": "11px", "margin-left": "5px"}
    _barra = "linear-gradient(to left, {c} var(--w), transparent var(--w))"
    css[".vr-bar"] = {"display": "inline-block", "min-width": "58px",
                      "padding": "0 4px", "border-radius": "3px",
                      "text-align": "right", "line-height": "18px",
                      "background": _barra.format(c=LAVANDA_BORDE)}
    css[".vr-bar.vr-bar-cian"] = {
        "background": _barra.format(c=PALETA_SERIES[1] + "59")}
    css[".vr-bar.vr-bar-ambar"] = {
        "background": _barra.format(c=ADVERTENCIA_BORDE)}
    css[".vr-bar.vr-bar-roja"] = {"background": _barra.format(c=ERROR_FONDO),
                                  "box-shadow": f"inset 0 0 0 1px {ERROR}"}
    css[".vr-sube"] = {"color": f"{EXITO} !important", "font-weight": "600"}
    css[".vr-baja"] = {"color": f"{ERROR} !important", "font-weight": "600"}
    css[".vr-neutro"] = {"color": f"{GRIS_TEXTO} !important"}
    css[".vr-alto"] = {"color": f"{ADVERTENCIA_TEXTO} !important",
                       "font-weight": "600"}
    css[".vr-roto"] = {"color": f"{ERROR} !important", "font-weight": "700"}
    css[".vr-bandera"] = {
        "font-size": "10px", "font-weight": "700", "margin-left": "5px",
        "padding": "0 6px", "border-radius": "8px", "line-height": "16px",
        "background": ERROR_FONDO, "color": ERROR}
    css[".vr-franja"] = {
        "display": "grid", "gap": "6px", "padding": "6px 12px 6px 28px",
        "grid-template-columns": "repeat(auto-fit, minmax(170px, 1fr))",
        "white-space": "normal", "line-height": "1.35",
        "border-bottom": f"1px solid {GRIS_BORDE}", "background": BLANCO,
        "font-size": "12.5px", "color": TEXTO_PRINCIPAL,
        "font-variant-numeric": "tabular-nums"}
    css[".vr-b"] = {"border": f"1px solid {GRIS_BORDE}", "border-radius": "8px",
                    "padding": "4px 8px", "display": "flex",
                    "flex-direction": "column", "gap": "1px", "min-width": "0"}
    css[".vr-b.vr-aviso"] = {"border-color": ADVERTENCIA_BORDE,
                             "background": ADVERTENCIA_FONDO}
    css[".vr-h"] = {"font-size": "10px", "font-weight": "600",
                    "letter-spacing": ".06em", "text-transform": "uppercase",
                    "color": GRIS_TEXTO}
    css[".vr-cab"] = {"display": "flex", "gap": "8px",
                      "align-items": "baseline", "white-space": "nowrap"}
    css[".vr-g"] = {"font-size": "14px", "font-weight": "700",
                    "line-height": "1.25"}
    # Los canales, un renglón por canal: el bloque ocupa DOS columnas de la
    # franja para que «● En el Local S/ 19,252 · 98% −0.6 pp +106%» entre
    # en una línea (medido: en una sola columna, 217px, partía en cuatro y
    # la franja llegaba a 172px dentro de una grilla de 191).
    css[".vr-b.vr-ancho"] = {"grid-column": "span 2"}
    css[".vr-f"] = {"font-size": "11.5px", "color": GRIS_TEXTO_MEDIO}
    css[".vr-canal"] = {"display": "flex", "gap": "6px", "white-space": "nowrap",
                        "align-items": "baseline", "font-size": "12.5px"}
    css[".vr-canal i"] = {"display": "inline-block", "width": "8px",
                          "height": "8px", "border-radius": "2px"}
    css[".vr-canal b"] = {"font-weight": "600", "flex": "1 1 auto",
                          "min-width": "0", "overflow": "hidden",
                          "text-overflow": "ellipsis", "white-space": "nowrap"}
    css[".vr-pie"] = {"grid-column": "1 / -1", "display": "flex",
                      "flex-wrap": "wrap", "gap": "4px 14px",
                      "align-items": "baseline"}
    css[".vr-revisar"] = {"font-size": "12px", "font-weight": "600",
                          "color": ERROR}
    css[".vr-ver"] = {"font": "inherit", "font-size": "12px",
                      "font-weight": "600", "color": ACENTO_TEXTO,
                      "background": "none", "border": "0", "padding": "0",
                      "cursor": "pointer"}
    css[".vr-ver:hover"] = {"text-decoration": "underline"}
    return css


def renderizar_dias_venta(tp, altura, key, columnas, rotulo_periodo="Día",
                          total=None):
    """Una fila por barra del gráfico, en el orden del eje: la opción «B» del
    mockup (2026-09-24, regla #518).

    Nueve columnas —Día, Carta, Venta, Neto, Costo, % costo, Pax, Ticket y la
    variación de la venta— y el resto (canales, propinas, descuentos,
    cortesías y el detalle del costo) en una FRANJA que se despliega al
    hacer clic en la fila, sin pasar por Python.

    `tp` trae `periodo`, los números crudos `carta`, `valor`, `neto`,
    `costo`, `pcosto`, `pax`, `ticket` y `variacion` —los que el parquet no
    trae pueden faltar y su columna no se dibuja—, más las ocultas: `__id`
    (la clave del período, que es también `__clave`), `__html` (la franja),
    `__vtxt`, `__nota`, `__sel` y los `__t_/__v_/__c_/__vc_/__b_` de las
    celdas compuestas (ver `_R_CELDA`).

    `columnas` es la SUBVISTA (2026-09-24, regla #519): `(campo, rótulo,
    tipo, ancho, tooltip)` en el orden en que se ven, con `tipo` uno de
    «soles0», «soles», «entero», «celda» (`_R_CELDA`), «var» (la variación
    de la venta) o «texto» (la única que se estira). Lo que no está en la
    lista viaja oculto.

    Devuelve la `__clave` de la fila SELECCIONADA, o None: la selección la
    hace sólo el botón «Ver pedidos» de la franja (el clic en la fila la
    despliega), y el llamador abre el Detalle."""
    # El ORDEN de las columnas es el del DataFrame, no el de las llamadas a
    # `configure_column`: sin reordenar, «Venta» salía después de «Costo».
    _orden = ["periodo"] + [c[0] for c in columnas if c[0] in tp.columns]
    tp = tp[_orden + [c for c in tp.columns if c not in _orden]]
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("periodo", header_name=rotulo_periodo, minWidth=120,
                        tooltipField="__tip", cellRenderer=_R_CELDA)
    visibles = {"periodo"}
    for campo, rotulo, tipo, ancho, tip in columnas:
        if campo not in tp.columns:
            continue
        visibles.add(campo)
        kw = dict(header_name=rotulo, headerTooltip=tip)
        if tipo == "texto":
            # La única que se estira: un nombre de plato no tiene ancho fijo.
            kw.update(minWidth=ancho, tooltipField=campo)
        else:
            kw.update(type=["numericColumn"], width=ancho, minWidth=ancho,
                      suppressSizeToFit=True)
            if tipo == "celda":
                kw["cellRenderer"] = _R_CELDA
            elif tipo == "var":
                kw.update(valueFormatter=_JS_VARIACION,
                          cellStyle=_STYLE_VARIACION_VENTA,
                          tooltipField="__nota")
            else:
                kw["valueFormatter"] = _FORMATOS[tipo]
        gb.configure_column(campo, **kw)
    # Lo que la subvista no muestra viaja igual (la franja y el orden lo
    # usan), oculto.
    for col in tp.columns:
        if col not in visibles:
            gb.configure_column(col, hide=True)
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=_REGLAS_DIA,
        # El clic en la fila DESPLIEGA, no selecciona: la selección es el
        # pedido de abrir el Detalle, y la hace el botón de la franja.
        suppressRowClickSelection=True,
        getRowId=JsCode("function(p){ return String(p.data.__id); }"),
        isFullWidthRow=JsCode(
            "function(p){ return !!(p.rowNode && p.rowNode.data"
            " && p.rowNode.data.__detalle); }"),
        fullWidthCellRenderer=_R_FRANJA,
        onRowClicked=_AL_CLIC_DIA,
        onGridReady=_AL_MONTAR, onRowDataUpdated=_AL_CAMBIAR_FILAS), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css_dias(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty and "__clave" in sel.columns:
        return str(sel.iloc[0]["__clave"])
    return None


# Clic en una fila = elegirla o SOLTARLA. `rowPinned` afuera: la fila Total
# no es un pedido.
_JS_ALTERNAR = JsCode(
    "function(e){ if (e.node.rowPinned) return;"
    " e.node.setSelected(!e.node.isSelected(), true); }")


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
    vigente: el llamador la compara contra el pedido que ya muestra.

    EL CLIC ALTERNA (regla #525): un segundo clic en el pedido elegido lo
    suelta, y la tabla de al lado vuelve a los platos del período entero.
    AG Grid por sí solo no deselecciona al reclickear (pide Ctrl+clic, que
    nadie descubre): la selección la maneja `_JS_ALTERNAR`, el mismo
    handler del ranking de Proveedor (`compras/proveedor.py`)."""
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
    for _legado in ("rowMultiSelectWithClick", "suppressRowDeselection",
                    "suppressRowClickSelection", "groupSelectsChildren",
                    "groupSelectsFiltered"):
        grid_options.pop(_legado, None)
    grid_options["rowSelection"] = {"mode": "singleRow", "checkboxes": False,
                                    "enableClickSelection": False}
    grid_options["onRowClicked"] = _JS_ALTERNAR

    resp = AgGrid(
        tp, gridOptions=grid_options, height=altura, theme="material",
        custom_css=_css(), allow_unsafe_jscode=True, key=key,
        update_on=["selectionChanged"],
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__ped"])
    return None
