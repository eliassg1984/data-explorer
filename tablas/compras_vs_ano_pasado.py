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

    SIN FONDO DE CELDA desde el 2026-09-12 (regla #390): el semáforo va en
    la LETRA, y cada recurso en la columna donde rinde — la barrita de
    magnitud en «Δ S/» (cuánto), la flecha en «Δ %» (hacia dónde), y la
    negrita con el tono oscuro sólo en las filas que pasan
    `_UMBRAL_ALARMA_PCT`. Con pastillas en tres columnas la tabla era una
    colcha y el color dejó de avisar nada.

Selección de fila SIN checkbox y por CONTENIDO (`__item_full`), mismo
criterio que `tablas/compras_volatilidad.py`: el buscador de arriba filtra
la lista sin que un índice viejo pueda desalinearse contra la fila nueva
(arquitectura.md regla #130).
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tema import (
    ACENTO, CELDA_POS_TEXTO, ERROR, ERROR_BORDE, ERROR_TEXTO, EXITO,
    EXITO_BORDE, GRIS_TEXTO, TEXTO_PRINCIPAL,
)
from tablas._config import _parchar_iconos
from tablas._css import _css_grid

# Anchos FIJOS: el contenido de estas celdas es siempre corto ("S/ 12,340",
# "+18.2%") y no depende del dato, así que no hay nada que auto-ajustar.
# Mismo criterio (y misma razón) que `_ANCHO_COL_SEMANA` en
# tablas/compras_volatilidad.py: con auto-fit, una cabecera larga estira su
# columna y en una tarjeta angosta dejan de entrar todas.
#
# El % pasó de 88 a 100 el 2026-09-08, al sumarse los subtítulos de
# cabecera: su celda es la más angosta y "÷ año pasado" pide 62px contra los
# 56 que deja un ancho de 88 (medido en el navegador; la cabecera de AG Grid
# se come 32px de padding por celda). Medir contra el ancho DECLARADO y no
# contra el de pantalla no es exceso de celo: AG Grid estira las columnas
# para llenar la grilla, así que la de 88 se veía en 97 y el recorte no
# aparecía hasta que la tarjeta se angostara — regla #349.
_ANCHO_SOLES = 112
_ANCHO_PCT = 100

# ── Subtítulo de cabecera: la REFERENCIA de cada cuenta ────────────────────
# "Este año" / "Año pasado" NO son años calendario: son la ventana elegida
# arriba (por defecto, 12 meses móviles que terminan en el último mes con
# compras). Sin el rango, la cabecera se lee como "2026" contra "2025" y el
# número no coincide con esa cuenta — reportado el 2026-09-08. Por eso el
# rango de cada lado viaja como dato (`rango_act`/`rango_aa`): lo sabe el
# drill, que es el que filtró la ventana, no esta función.
#
# Los de las columnas de diferencia sí son fijos: dicen contra qué se mide
# cada una, que es lo que el tooltip explica en largo. Los dos efectos se
# nombran por lo que dejan QUIETO —el precio se mide a igual cantidad y la
# cantidad a igual precio—, que es la forma corta de la fórmula del
# docstring y la razón de que sumen el Δ exacto.
_SUB_HDR = {
    "Δ S/": "este − pasado",
    "Δ %": "÷ año pasado",
    "Efecto precio": "a igual cantidad",
    "Efecto cantidad": "a igual precio",
}
_SUB_FONT_PX = 10

_ALTO_SUB_HDR = 13
"""Lo que el subtítulo le suma a la cabecera (px).

Acoplado a `extra=` de `alturas.por_filas()` en el drill, igual que
`_ALTO_FILA`: el marco de la grilla se calcula en Python sumando cromo +
filas, así que una cabecera más alta que no se cuente ahí se come una fila
de las que se ven. Medido en el navegador, no estimado."""

_FMT_SOLES = JsCode("""
    function(params) {
        if (params.value === null || params.value === undefined) return '';
        var v = Number(params.value);
        var sign = v < 0 ? '\\u2212' : '';
        return sign + 'S/ ' + Math.abs(v).toLocaleString('es-PE',
            { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }
""")

# La FLECHA ocupa el lugar del signo, no se suma a él: «▴20.6%» mide lo
# mismo que «+20.6%», y la columna ya está medida contra su cabecera
# (ver `_ANCHO_PCT`). Un ítem sin año pasado no tiene % —dividiría por
# cero—: dice «nuevo», que es lo que el Δ S/ de al lado está contando.
_FMT_PCT = JsCode("""
    function(params) {
        if (params.value === null || params.value === undefined)
            return params.data && params.data['Este año'] ? 'nuevo' : '';
        var v = Number(params.value);
        if (Math.abs(v) < 0.05) return '0.0%';
        return (v > 0 ? '\\u25B4' : '\\u25BE') + Math.abs(v).toFixed(1) + '%';
    }
""")

_UMBRAL_ALARMA_PCT = 30
"""Desde qué |Δ %| una fila es ALARMA: negrita, tono oscuro y barra fuerte en
«Δ S/» y «Δ %». Debajo, el mismo semáforo pero en peso normal y tono claro.

Es de la FILA y no de cada celda: «Δ S/» no tiene un umbral propio que
tenga sentido para todos los ítems (S/ 900 es mucho en sal y nada en
carne), y el % sí. Mismo criterio que la barra de Volatilidad, con otro
número: allá los saltos semanales de ±50% son lo común."""

# El semáforo de COSTO (ver docstring) en la LETRA: positivo = rojo. Un
# solo cuerpo para las tres columnas que lo llevan; lo que cambia entre
# ellas es si la fila puede ser alarma y si lleva barra, y eso lo dicen
# las dos banderas que se interpolan en `_style_costo`.
_JS_COSTO = """
    function(params) {
        var base = {fontFamily: "'Courier New',Courier,monospace",
                    textAlign: 'right', paddingRight: '10px'};
        if (params.value === null || params.value === undefined) {
            base.color = '__GRIS__'; return base;
        }
        var v = Number(params.value);
        if (Math.abs(v) < 0.5) { base.color = '__GRIS__'; return base; }
        var d = params.data || {};
        var pct = d['Δ %'];
        var alarma = __ALARMA__ && pct !== null && pct !== undefined
                     && Math.abs(Number(pct)) >= __UMBRAL__;
        var sube = v > 0;
        base.color = alarma ? (sube ? '__SUBE_OSC__' : '__BAJA_OSC__')
                            : (sube ? '__SUBE__' : '__BAJA__');
        base.fontWeight = alarma ? '700' : '500';
        if (__BARRA__) {
            // La barrita de magnitud: una raya de 3px al pie de la celda,
            // alineada a la derecha como el número, larga en proporción al
            // mayor |Δ S/| de la tabla (`__bar`, 0-100, lo calcula Python).
            // Es un fondo y no un elemento: así no hace falta un
            // cellRenderer, y el `background-origin: content-box` la deja
            // terminando donde termina el número y no en el borde.
            var c = alarma ? (sube ? '__SUBE__' : '__BAJA__')
                           : (sube ? '__SUBE_BAR__' : '__BAJA_BAR__');
            var w = Math.max(4, Math.round(Number(d['__bar']) || 0));
            base.backgroundImage = 'linear-gradient(' + c + ',' + c + ')';
            base.backgroundSize = w + '% 3px';
            base.backgroundRepeat = 'no-repeat';
            base.backgroundPosition = 'right bottom 2px';
            base.backgroundOrigin = 'content-box';
        }
        return base;
    }
"""


def _style_costo(alarma, barra):
    return JsCode(
        _JS_COSTO.replace("__ALARMA__", "true" if alarma else "false")
        .replace("__BARRA__", "true" if barra else "false")
        .replace("__UMBRAL__", str(_UMBRAL_ALARMA_PCT))
        .replace("__GRIS__", GRIS_TEXTO)
        .replace("__SUBE_OSC__", ERROR_TEXTO).replace("__BAJA_OSC__", CELDA_POS_TEXTO)
        .replace("__SUBE_BAR__", ERROR_BORDE).replace("__BAJA_BAR__", EXITO_BORDE)
        .replace("__SUBE__", ERROR).replace("__BAJA__", EXITO))


_STYLE_DELTA_SOLES = _style_costo(alarma=True, barra=True)
_STYLE_DELTA_PCT = _style_costo(alarma=True, barra=False)
_STYLE_EF_PRECIO = _style_costo(alarma=False, barra=False)
"""El efecto precio lleva el color y nada más: la alarma de la fila ya la
dicen «Δ S/» y «Δ %», y una tercera negrita en la misma fila vuelve a ser
ruido."""

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
                                     font_px=13, rango_act=None,
                                     rango_aa=None):
    """Grilla del detalle ítem por ítem. `tv` trae, en este orden:

        Item, __item_full, Este año, Año pasado, Δ S/, Δ %,
        Efecto precio, Efecto cantidad,
        __cant, __cant_aa, __p, __p_aa, __um, __n   (todas ocultas)

    `etiqueta_item` es el encabezado de la primera columna ("Producto",
    "Familia"…): la fija el agrupador que eligió el usuario, así que no
    puede escribirse acá.

    `rango_act`/`rango_aa` son los rangos de meses que cubre cada lado
    ("oct 25 – sep 26"), y van de subtítulo en su cabecera. Los calcula el
    drill sobre la ventana ENTERA, no sobre `tv`: con el buscador filtrando,
    las filas que sobreviven pueden no tocar todos los meses y la cabecera
    diría un rango más corto que el de la cuenta.

    Devuelve el `__item_full` de la fila clickeada en ESTA corrida, o None.
    """
    # El largo de la barrita de «Δ S/» viaja como DATO de la fila y no como
    # un máximo metido en el JsCode (regla #226). Relativo a la tabla que se
    # VE: con el buscador filtrando, la barra más larga es la del ítem mayor
    # entre los que quedan.
    _mx = float(tv["Δ S/"].abs().max() or 0) if len(tv) else 0.0
    tv = tv.assign(__bar=(tv["Δ S/"].abs() / _mx * 100) if _mx else 0.0)

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
        ("Efecto precio",   _STYLE_EF_PRECIO, _TOOLTIP_EF_PRECIO),
        ("Efecto cantidad", _STYLE_NUM,       _TOOLTIP_EF_CANT),
        ("Δ S/",            _STYLE_DELTA_SOLES, None),
    ):
        gb.configure_column(col, type=["numericColumn"], width=_ANCHO_SOLES,
                            valueFormatter=_FMT_SOLES, cellStyle=style,
                            **({"tooltipValueGetter": tip} if tip else {}))
    gb.configure_column("Δ %", type=["numericColumn"], width=_ANCHO_PCT,
                        valueFormatter=_FMT_PCT, cellStyle=_STYLE_DELTA_PCT)

    for oculta in ("__item_full", "__cant", "__cant_aa", "__p", "__p_aa",
                   "__um", "__n", "__bar"):
        gb.configure_column(oculta, hide=True)

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(rowHeight=_ALTO_FILA, headerHeight=34,
                              tooltipShowDelay=200)
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md regla #159

    custom_css = dict(_css_grid(font_px, cabecera_neutra=True))
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

    # ── El subtítulo de cada cabecera (ver `_SUB_HDR`) ────────────────────
    # Va por CSS y no pegado al `header_name` porque AG Grid ESCAPA el texto
    # de la cabecera y lo pinta con una sola tipografía: "Este año oct 25 –
    # sep 26" saldría del mismo tamaño y peso que el título, wrappeando por
    # donde le tocara. La otra salida sería un `headerComponent` propio, y
    # ése obliga a reimplementar a mano el clic de ordenar y su flecha —
    # esta tabla se ordena, así que se pagaría una función por un renglón.
    #
    # El pseudo cuelga de `.ag-header-cell-label` (el flex que lleva título
    # + flecha de orden) y no de `.ag-header-cell-text`: ahí adentro
    # quedaría AL LADO de la flecha en vez de debajo de las dos cosas.
    # `flex-wrap` + `flex: 0 0 100%` es lo que le da renglón propio; el
    # `align-content` evita que las dos líneas se peguen al borde de arriba
    # cuando la cabecera crece.
    subtitulos = dict(_SUB_HDR)
    if rango_act:
        subtitulos["Este año"] = rango_act
    if rango_aa:
        subtitulos["Año pasado"] = rango_aa
    for _col, _txt in subtitulos.items():
        _sel = f'.ag-header-cell[col-id="{_col}"] .ag-header-cell-label'
        custom_css[_sel] = {
            "flex-wrap": "wrap !important",
            "align-content": "center !important",
        }
        custom_css[f"{_sel}::after"] = {
            "content": f"'{_txt}'",
            "flex": "0 0 100%",
            "text-align": "right",
            "font-size": f"{_SUB_FONT_PX}px",
            "font-weight": "400",
            "line-height": f"{_ALTO_SUB_HDR}px",
            "color": f"{GRIS_TEXTO}",
            "letter-spacing": "normal",
            "text-transform": "none",
            # `nowrap` + elipsis y no wrap a dos líneas: el subtítulo entra
            # con holgura en el ancho DECLARADO de cada columna (medido:
            # entre 6 y 21px de sobra), pero AG Grid escala las columnas
            # para llenar la grilla y en un contenedor más angosto que la
            # suma de los anchos las achica — regla #349. Ahí el subtítulo
            # se corta con "…" en vez de empujar la cabecera a un tercer
            # renglón, que descuadraría el marco calculado en Python.
            "white-space": "nowrap",
            "overflow": "hidden",
            "text-overflow": "ellipsis",
        }

    resp = AgGrid(
        tv, gridOptions=grid_options, height=altura, theme="material",
        custom_css=custom_css, allow_unsafe_jscode=True, key=key,
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__item_full"])
    return None
