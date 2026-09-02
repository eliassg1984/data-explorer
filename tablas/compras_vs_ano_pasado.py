"""tablas.compras_vs_ano_pasado - la tabla de detalle del drill "Vs año
pasado" de Compras (graficos/compras/vs_ano_pasado.py).

Es la MISMA cuenta que el gráfico de arriba, abierta ítem por ítem: una
fila por producto (o familia/subfamilia, según el agrupador), con el gasto
de este año, el del año pasado y la diferencia PARTIDA EN DOS.

EL PUENTE PRECIO / CANTIDAD
    "Gastamos S/ 40k más que el año pasado" no es accionable: no dice si
    compramos más o si nos cobraron más caro. La diferencia se descompone
    exacto en dos sumandos, y esa es la columna que vale:

        Δ valor = (p − p_aa) · q     +     (q − q_aa) · p_aa
                  └── efecto precio ┘      └── efecto cantidad ┘

    Se comprueba desarrollando: q·p − p_aa·q + q·p_aa − q_aa·p_aa
    = valor − valor_aa. Cierra SIEMPRE, y por eso los precios de las dos
    puntas tienen que ser PONDERADOS (valor/cantidad) y no el promedio
    simple que trae el parquet en PRECIO_UNIT_ANO_ANTERIOR: con un promedio
    simple los dos sumandos no dan la diferencia y el puente miente por el
    resto.

    Los altas/bajas no tienen precio del otro lado (q_aa = 0 → p_aa no
    existe). Ahí el efecto es 100% cantidad: un producto que no comprabas
    el año pasado no te subió de precio, apareció. Lo resuelve
    `graficos/compras/vs_ano_pasado.py::_puente`, que es donde vive la
    cuenta; este módulo solo la pinta.

SEMÁFORO INVERTIDO, IGUAL QUE VOLATILIDAD
    El dato es un COSTO: "sube" es malo (rojo/ERROR) y "baja" es bueno
    (verde/EXITO), al revés de la convención bursátil. Aplica al Δ% y al
    efecto PRECIO, que son las dos columnas donde subir duele. El efecto
    CANTIDAD va en gris a propósito: comprar más no es malo — puede ser que
    el negocio creció — y pintarlo de rojo mandaría el mensaje contrario.

Selección de fila SIN checkbox y por CONTENIDO (`__item_full`), mismo
criterio que `tablas/compras_volatilidad.py`: el buscador de arriba filtra
la lista sin que un índice viejo pueda desalinearse contra la fila nueva
(arquitectura.md regla #130).
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import (
    ACENTO, ERROR, ERROR_FONDO, EXITO, EXITO_FONDO, GRIS_TEXTO,
    TEXTO_PRINCIPAL,
)
from tablas._config import _parchar_iconos
from tablas._css import _css_grid

# Anchos FIJOS: el contenido de estas celdas es siempre corto ("S/ 12,340",
# "+18.2%") y no depende del dato, así que no hay nada que auto-ajustar.
# Mismo criterio (y misma razón) que `_ANCHO_COL_SEMANA` en
# tablas/compras_volatilidad.py: con auto-fit, una cabecera larga estira su
# columna y en una tarjeta angosta dejan de entrar todas.
_ANCHO_SOLES = 112
_ANCHO_PCT = 88

_FMT_SOLES = JsCode("""
    function(params) {
        if (params.value === null || params.value === undefined) return '';
        var v = Number(params.value);
        var sign = v < 0 ? '\\u2212' : '';
        return sign + 'S/ ' + Math.abs(v).toLocaleString('es-PE',
            { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }
""")

_FMT_PCT = JsCode("""
    function(params) {
        if (params.value === null || params.value === undefined) return '';
        var v = Number(params.value);
        var sign = v >= 0 ? '+' : '\\u2212';
        return sign + Math.abs(v).toFixed(1) + '%';
    }
""")

# Semáforo de COSTO (ver docstring): positivo = rojo.
_STYLE_COSTO = JsCode(f"""
    function(params) {{
        var base = {{fontFamily: "'Courier New',Courier,monospace",
                     textAlign: 'right', paddingRight: '10px'}};
        if (params.value === null || params.value === undefined) return base;
        var v = Number(params.value);
        if (Math.abs(v) < 0.5) {{ base.color = '{GRIS_TEXTO}'; return base; }}
        if (v > 0) {{
            base.backgroundColor = '{ERROR_FONDO}'; base.color = '{ERROR}';
        }} else {{
            base.backgroundColor = '{EXITO_FONDO}'; base.color = '{EXITO}';
        }}
        base.fontWeight = '600';
        return base;
    }}
""")

# Neutro: cifras de contexto (el gasto de cada lado) y el efecto CANTIDAD.
_STYLE_NUM = JsCode(f"""
    function(params) {{
        return {{fontFamily: "'Courier New',Courier,monospace",
                 textAlign: 'right', paddingRight: '10px',
                 color: '{TEXTO_PRINCIPAL}'}};
    }}
""")

_STYLE_NUM_SUAVE = JsCode(f"""
    function(params) {{
        return {{fontFamily: "'Courier New',Courier,monospace",
                 textAlign: 'right', paddingRight: '10px',
                 color: '{GRIS_TEXTO}'}};
    }}
""")

_STYLE_ITEM = JsCode(f"""
    function(params) {{
        return {{color: '{TEXTO_PRINCIPAL}', fontWeight: '500'}};
    }}
""")

_TOOLTIP_ITEM = JsCode(
    "function(params){ return params.data ? params.data['__item_full'] : ''; }")

# Los tooltips llevan el DETALLE que no cabe en columnas propias: cantidad y
# precio ponderado de cada lado. Meterlos como columnas serían cuatro más y
# la tabla dejaría de leerse de un vistazo; en el tooltip están a un hover
# de distancia. Mismo recurso que el ranking de Volatilidad.
_JS_FMT = """
        var s = function(v) {
            if (v === null || v === undefined) return '—';
            return 'S/ ' + Number(v).toLocaleString('es-PE',
                { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        };
        var n = function(v) {
            if (v === null || v === undefined) return '—';
            return Number(v).toLocaleString('es-PE',
                { minimumFractionDigits: 0, maximumFractionDigits: 2 });
        };
"""

# `__p == null` marca una fila que NO es un producto (una familia, una
# subfamilia): ahí no hay cantidad ni precio que mostrar —sumarían kilos con
# litros y con servicios— y el tooltip dice cuántos productos hay detrás, que
# es lo único cierto de un grupo. Ver `_por_item` en el módulo del drill.
_TOOLTIP_ACT = JsCode("""
    function(params) {
        var d = params.data; if (!d) return '';
""" + _JS_FMT + """
        if (d['__p'] == null) return 'Suma de ' + d['__n'] + ' productos';
        return n(d['__cant']) + ' ' + (d['__um'] || '') +
               '  ·  precio prom. ' + s(d['__p']);
    }
""")

_TOOLTIP_AA = JsCode("""
    function(params) {
        var d = params.data; if (!d) return '';
""" + _JS_FMT + """
        if (d['__p'] == null) return 'Suma de ' + d['__n'] + ' productos';
        if (!d['__cant_aa']) return 'No se compró en el mismo período del año pasado';
        return n(d['__cant_aa']) + ' ' + (d['__um'] || '') +
               '  ·  precio prom. ' + s(d['__p_aa']);
    }
""")

_TOOLTIP_EF_PRECIO = JsCode("""
    function(params) {
        var d = params.data; if (!d) return '';
""" + _JS_FMT + """
        if (d['__p'] == null)
            return 'Suma del efecto precio de los ' + d['__n'] +
                   ' productos del grupo, cada uno con su propia unidad';
        if (!d['__cant_aa']) return 'Sin precio del año pasado: el ítem es nuevo';
        return 'Pagar ' + s(d['__p']) + ' en vez de ' + s(d['__p_aa']) +
               ' sobre ' + n(d['__cant']) + ' ' + (d['__um'] || '');
    }
""")

_TOOLTIP_EF_CANT = JsCode("""
    function(params) {
        var d = params.data; if (!d) return '';
""" + _JS_FMT + """
        if (d['__p'] == null)
            return 'Suma del efecto cantidad de los ' + d['__n'] +
                   ' productos del grupo';
        if (!d['__cant_aa']) return 'Ítem nuevo: todo el gasto es efecto cantidad';
        return 'Comprar ' + n(d['__cant']) + ' en vez de ' + n(d['__cant_aa']) +
               ' ' + (d['__um'] || '') + ' al precio del año pasado (' +
               s(d['__p_aa']) + ')';
    }
""")


_ALTO_FILA = 24
"""Alto de fila de la tabla de detalle.

24 y no 30 desde el 2026-09-02: en el mismo pedido, el marco de la tabla
bajó de 300 a 250 (`alturas.COMPACTO`) y con filas de 30 eso costaba fila y
media de las que se ven. A 24 entran las MISMAS ~8 filas en 50px menos —el
mismo número que ya usan los rankings de Proveedor y de Producto—, así que
el recorte no se paga con información.

Va acoplado a `por_filas(px_fila=…)` en `graficos/compras/vs_ano_pasado.py`:
son el mismo número contado dos veces (cuánto ocupa una fila / cuántas
entran). Si se cambia uno solo, el marco deja de coincidir con lo que las
filas ocupan."""


def renderizar_detalle_vs_ano_pasado(tv, etiqueta_item, altura, key,
                                     font_px=13):
    """Grilla del detalle ítem por ítem. `tv` trae, en este orden:

        Item, __item_full, Este año, Año pasado, Δ S/, Δ %,
        Efecto precio, Efecto cantidad,
        __cant, __cant_aa, __p, __p_aa, __um, __n   (todas ocultas)

    `etiqueta_item` es el encabezado de la primera columna ("Producto",
    "Familia"…): la fija el agrupador que eligió el usuario, así que no
    puede escribirse acá.

    Devuelve el `__item_full` de la fila clickeada en ESTA corrida, o None.
    """
    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=True, autoHeaderHeight=True,
    )
    gb.configure_column("Item", header_name=etiqueta_item, pinned="left",
                        minWidth=210, flex=1, cellStyle=_STYLE_ITEM,
                        tooltipValueGetter=_TOOLTIP_ITEM)

    for col, style, tip in (
        ("Este año",        _STYLE_NUM,       _TOOLTIP_ACT),
        ("Año pasado",      _STYLE_NUM_SUAVE, _TOOLTIP_AA),
        ("Efecto precio",   _STYLE_COSTO,     _TOOLTIP_EF_PRECIO),
        ("Efecto cantidad", _STYLE_NUM,       _TOOLTIP_EF_CANT),
        ("Δ S/",            _STYLE_COSTO,     None),
    ):
        gb.configure_column(col, type=["numericColumn"], width=_ANCHO_SOLES,
                            valueFormatter=_FMT_SOLES, cellStyle=style,
                            **({"tooltipValueGetter": tip} if tip else {}))
    gb.configure_column("Δ %", type=["numericColumn"], width=_ANCHO_PCT,
                        valueFormatter=_FMT_PCT, cellStyle=_STYLE_COSTO)

    for oculta in ("__item_full", "__cant", "__cant_aa", "__p", "__p_aa",
                   "__um", "__n"):
        gb.configure_column(oculta, hide=True)

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(rowHeight=_ALTO_FILA, headerHeight=34,
                              tooltipShowDelay=200)
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md regla #159

    custom_css = dict(_css_grid(font_px))
    custom_css[".ag-tooltip"] = {
        "background-color": f"{TEXTO_PRINCIPAL} !important",
        "color": "#ffffff !important",
        "border": "none !important",
        "border-radius": "6px !important",
        "padding": "6px 10px !important",
        "font-size": "12px !important",
        "max-width": "320px !important",
        "white-space": "normal !important",
        "box-shadow": "0 6px 20px rgba(0,0,0,0.25) !important",
    }
    custom_css[".ag-row-selected"] = {
        "box-shadow": f"inset 3px 0 0 0 {ACENTO} !important",
    }

    resp = AgGrid(
        tv, gridOptions=grid_options, height=altura, theme="material",
        custom_css=custom_css, allow_unsafe_jscode=True, key=key,
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__item_full"])
    return None
