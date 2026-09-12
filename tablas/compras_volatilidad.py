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
    ACENTO, CELDA_POS_TEXTO, ERROR, ERROR_FONDO, ERROR_TEXTO, EXITO,
    EXITO_FONDO, GRIS_TEXTO, LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from tablas._config import _parchar_iconos
from tablas._css import _css_grid

# EL REPARTO: un ancho DECLARADO por columna, que AG Grid escala para
# llenar la grilla respetando cada `minWidth`. O sea que esto es una
# PROPORCION, no pixeles: 120 contra los 80 de «Volatilidad» y los 150 de
# «Insumo». Quien lo dispara es `_AL_MONTAR`, mas abajo.
#
# 98 -> 120 el 2026-09-12, con el piso: un ancho declarado POR DEBAJO de su
# `minWidth` hace que AG Grid arranque la columna en el piso y reparta el
# resto con una proporcion que ya no es la escrita aca.
_ANCHO_COL_SEMANA = 120
_ANCHO_COL_VOL = 80
"""Peso de «Volatilidad» en el reparto. Bajo de 92 a 80 el 2026-09-07: es la
unica columna cuyo contenido no crece con el ancho de la ventana -- «12402.5»
mide ~46px y la cabecera 66 -- asi que lo que se le saque va a las siete
semanas, que son las que estaban apretadas."""

_MIN_ANCHO_COL_SEMANA = 120
"""Piso de una columna-semana, y la cuenta que lo fija.

Lo manda el RENGLON de la celda: el % y, AL COSTADO, los dos cierres
(«+562%  2.88 → 19.07»). 34px del % en el peor caso (cinco glifos a
`_TAM_DELTA`) + 5 de `_GAP_PRECIOS` + 69 de los dos precios en el peor caso
real del parquet + los 12 de cromo horizontal — 4+4 de `_PAD_X_SEMANA` y 2+2
del borde transparente que separa una pastilla de la siguiente.

Historia, porque cada valor lo fijo una forma distinta de la celda:
48 cuando era solo el %; 81 el 2026-09-07, con los precios DEBAJO del % (el
ancho lo mandaba la segunda linea sola); 120 el 2026-09-12, con los precios
al costado, a pedido y sobre una maqueta a escala. Ese mismo dia la grilla
paso a ocupar el ANCHO ENTERO de la tarjeta (antes era la columna izquierda
de la fila, 587px), y es lo que hace posible este piso: con 587px cuatro
columnas de 120 no entraban (150 + 4x120 + 78 + 17 = 725) y salia scroll
horizontal. La alternativa —dibujar los precios "solo donde entran"— ya se
probo dos veces y las dos fallaron por lo mismo: el ancho real no se sabe
mientras la celda se construye (ver `_RENDER_DELTA`).

NO ES COSMETICO. Con la columna en 46px y un formato de siete glifos (51px)
el `overflow: hidden` de la celda se comia el principio del numero:
"+176.9%" se leia "76.9%" — un recorte que no parece un recorte, parece OTRO
NUMERO. Si la grilla se angosta tanto que ni los pisos entran, AG Grid saca
scroll horizontal: feo, pero visible."""

_ANCHO_COL_INSUMO = 150
"""Ancho declarado de «Insumo», que ademas va `pinned` y con el mismo valor
de piso.

El piso NO es un techo, y aca decia lo contrario hasta el 2026-09-12: que
con `width == minWidth` "el reparto no le da ni le saca nada". Le saca no,
pero le DA: `sizeColumnsToFit` escala tambien a la columna fijada, y con la
grilla a todo el ancho de la tarjeta (1231px a 1400 de ventana) «Insumo»
mide 257, medido. Es lo que conviene — con el ancho sobrado, el nombre
entero de 34 caracteres entra sin tooltip —, pero es una consecuencia del
reparto proporcional, no algo que este numero impida.

Era 170 y bajo a 150 el 2026-09-07, cuando la grilla media 587px y los 20px
eran los que le faltaban a las columnas-semana para llegar a su piso."""

_MIN_ANCHO_COL_VOL = 78
"""Piso de la columna «Volatilidad». No lo tenia, y con el drill al lado del
ranking (2026-09-07) AG Grid la escalaba hasta 46px: la cabecera salia como
una torre de letras («Vol / atil / ida / d») y el valor como «1...». Es la
columna que le da nombre a la vista, asi que es la ultima que puede ceder.

78 = 66 del texto «Volatilidad» a 11px + los 12 del padding de `_PAD_X_COL`.
El valor mas grande que hay hoy en el parquet, «12402.5», mide ~46."""

# Alto de fila: UN renglon, el % y los dos precios al costado. 13.8px de
# texto (12px a line-height 1.15); el resto es el aire de la celda y los 3+3
# del borde que separa una pastilla de la de la fila siguiente.
#
# 40 -> 30 el 2026-09-12, al pasar los precios de DEBAJO del % a su costado
# (a pedido, sobre una maqueta a escala). Estuvo en 40 desde el 2026-09-07
# porque la celda tenia dos lineas; cada 10px por fila son ~2 filas mas en el
# mismo alto de grilla (`alturas.RANKING_CON_DRILL`).
ALTO_FILA = 30
_TAM_PRECIOS = "9.5px"
_GAP_PRECIOS = "5px"
"""Aire entre el % y los dos precios que van a su costado. Entra en la
cuenta de `_MIN_ANCHO_COL_SEMANA`."""

_TAM_DELTA = "12px"
"""Cuerpo del % en las columnas-semana, un punto por debajo del resto de la
grilla (13px). Es lo que hace que los cinco glifos del peor caso entren en
`_MIN_ANCHO_COL_SEMANA` -- 34px contra los 37 que medirian a 13px."""

# SIN DECIMAL, y no es una decision de gusto: es la unica forma de que el
# peor caso entre en la columna. Con un decimal, "+176.9%" mide 51px y la
# columna real son 46 -- el `overflow: hidden` de la celda se comia el
# principio y la grilla mostraba "76.9%" (reportado con captura el
# 2026-09-07). Sin el, cinco glifos, 34px, y la cifra exacta a un hover de
# distancia en el tooltip.
#
# El decimal ademas era falsa precision para lo que esta tabla hace: es un
# ESCANER -- se lee de un golpe para encontrar que insumo se movio y cuando.
# El precio exacto de las dos semanas vive en el tooltip, y el detalle en el
# candlestick de al lado.
#
# Sin signo cuando redondea a cero: un "+0%" dice "subio" con un numero que
# dice "no cambio". Mismo umbral que `_EPS_CERO`, que por eso subio de 0.05
# a 0.5 el mismo dia -- lo que se VE "0%" tiene que ser exactamente lo que
# se dibuja como "aca no paso nada", o la tabla se contradice sola pintando
# de rojo una celda que dice cero.
_FMT_PCT = JsCode("""
    function(params) {
        if (params.value === null || params.value === undefined) return '';
        var v = Number(params.value);
        if (Math.abs(v) < 0.5) return '0%';
        // A PARTIR DE MIL POR CIENTO, MULTIPLICADOR. "+12282%" son siete
        // caracteres en una columna de 48px: no entra. "x124" son cuatro,
        // y ademas se lee mejor -- nadie procesa doce mil por ciento como
        // otra cosa que "se multiplico por". Los dos precios exactos
        // siguen en el tooltip. Solo hacia arriba: una baja no puede pasar
        // de -100%.
        if (v >= 1000) return '×' + (1 + v / 100).toFixed(0);
        var sign = v > 0 ? '+' : '−';
        return sign + Math.abs(v).toFixed(0) + '%';
    }
""")

_FMT_1DEC = JsCode("""
    function(params) {
        return params.value == null ? '' : Number(params.value).toFixed(1);
    }
""")

# Un cambio que redondea a "0%" es RUIDO: ocupa el mismo ancho que un
# +12% y compite por la mirada en una tabla donde lo que importan son los
# saltos. Se dibuja mas chico (y mas claro) para que la fila se lea como
# "aca no paso nada" sin sacar el dato. El umbral es el del formateo
# (`toFixed(0)`), no uno propio: lo que se ve "0%" es exactamente lo que se
# achica -- si no, la tabla mostraria dos ceros de tamanos distintos, o
# peor, una pastilla roja con un cero adentro.
_EPS_CERO = 0.5
_TAM_CERO = "10.5px"

# El padding horizontal de la celda, propio de las columnas-semana. El del
# tema material son 15px POR LADO, o sea 30 de los 48 que mide la columna:
# no quedaria sitio ni para tres glifos.
#
# 6 -> 4 el 2026-09-07: los 2px que faltaban para que la pastilla pudiera
# separarse de su vecina sin robarle ancho al numero. Ver `_STYLE_DELTA`.
#
# Va en el `cellStyle` y no en el `custom_css` del grid a proposito: ahi
# seria `.ag-cell` a secas y le apretaria tambien al nombre del insumo,
# que no lo pidio. Es el aviso de CLAUDE.md sobre reglas colgadas del
# contenedor, en su version AgGrid.
_PAD_X_SEMANA = "0 4px"

_PAD_X_COL = "6px"
"""Padding horizontal de la CABECERA de las columnas angostas, y la mitad
del arreglo del 2026-09-07.

El tema `material` de AG Grid le pone 16px POR LADO a `.ag-header-cell`. En
una columna de 50px eso deja **18px** para el rótulo — medido, no estimado —
y a 18px "Ago" se parte en "Ag"+"o" y "Volatilidad" se vuelve una torre de
cuatro letras. La celda no tenía el problema porque su `cellStyle` ya bajaba
el padding a 6 (`_PAD_X_SEMANA`); la cabecera se había quedado atrás.

Con 6px el rótulo pasa de 18 a 38px y entra en un renglón. Va por
`headerClass` y no por `.ag-header-cell` a secas para no tocar «Insumo», que
sí tiene ancho de sobra y cuyo rótulo quedaría desalineado contra su propia
celda (que conserva el padding del tema)."""

_TAM_HDR_SEMANA = "11px"
"""Cabecera de columna angosta, más chica que el cuerpo (13px). Es lo que
hace que «Volatilidad» entre en un renglón dentro de 66px."""

_STYLE_DELTA = JsCode(f"""
    function(params) {{
        // El borde TRANSPARENTE es el canal entre columnas. Sin el, la
        // pastilla de cada celda llega hasta el borde y las de dos semanas
        // seguidas se tocan: la fila se lee como una banda de color en vez
        // de como siete celdas. Con `background-clip: padding-box` el color
        // se pinta solo dentro del padding, asi que 2px por lado abren el
        // canal horizontal y 3px arriba y abajo lo abren entre filas --
        // sale una pastilla, no un bloque.
        //
        // El borde y no un margen: `.ag-cell` esta posicionada en absoluto
        // con su ancho puesto a mano, y un margen la desalinearia de su
        // cabecera. El borde lo absorbe el `box-sizing: border-box` que ya
        // trae AG Grid.
        // En LONGHANDS, no `border: '3px 2px solid transparent'`: el
        // atajo de CSS no acepta dos anchos, asi que la declaracion entera
        // se descarta en silencio y la celda se queda con el borde de 1px
        // del tema. Medido: `getComputedStyle(celda).borderTopWidth` daba
        // 1px con el atajo puesto.
        var base = {{padding: '{_PAD_X_SEMANA}',
                     fontSize: '{_TAM_DELTA}',
                     borderWidth: '3px 2px',
                     borderStyle: 'solid',
                     borderColor: 'transparent',
                     backgroundClip: 'padding-box'}};
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

# LOS DOS PRECIOS, AL COSTADO DEL %: sin ellos la celda dice cuanto se movio
# y no desde donde -- "+12%" sobre 8.50 y sobre 85.00 son la misma celda, y la
# decision de compra no es la misma. Ademas son el precio INICIAL y el FINAL
# de la ventana leidos en la grilla: el `prev` de la primera columna y el
# `cur` de la ultima.
#
# AL COSTADO Y NO DEBAJO desde el 2026-09-12, a pedido y sobre una maqueta a
# escala con cuatro variantes de color. El % va PRIMERO (lo que se escanea)
# y los precios en el TONO OSCURO de su mismo semaforo — `ERROR_TEXTO` si
# subio, `CELDA_POS_TEXTO` si bajo —, sin la opacidad de antes: con los dos
# en el mismo renglon, lo que los separa tiene que ser el color, no el
# renglon. Se probaron gris y lavanda: el gris los despegaba de su celda y
# el lavanda competia con la barra de «Volatilidad», que es del mismo tono.
#
# SI NO ENTRA, SE CORTAN LOS PRECIOS, NUNCA EL %: el % no encoge
# (`flex: none`) y los precios llevan `min-width: 0` + ellipsis. Sin eso, un
# renglon alineado a la derecha que no entra se recorta por la IZQUIERDA —
# el `overflow: hidden` de la celda se come el principio del %, que es el
# modo de fallo que documenta `_MIN_ANCHO_COL_SEMANA` («+176.9%» leido
# «76.9%»).
#
# SIN GUARD DE ANCHO, y esa es la diferencia con las dos versiones
# anteriores. La linea se dibujaba "solo donde entra", midiendo la celda: la
# primera vez con `col.getActualWidth()` (devuelve el ancho DECLARADO, no el
# real) y la segunda con `p.eGridCell.clientWidth` dentro de un
# `requestAnimationFrame` (una CARRERA: segun cuando corriera el frame veia
# 98 o 46, asi que la linea salia recortada o no salia, sin que nada
# cambiara en el codigo). La conclusion, medida dos veces: **un cellRenderer
# no sabe cuanto mide su celda mientras se construye.**
#
# Asi que el ancho se garantiza ANTES, desde Python: `_MIN_ANCHO_COL_SEMANA`
# es el piso que la linea necesita y `MAX_SEMANAS` esta elegido para que ese
# piso entre siempre. Sin medicion en el navegador no hay carrera posible.
#
# `class` con `init`/`getGui` y no una funcion que devuelva HTML: en
# `st_aggrid` el atajo vanilla no pinta (se ve como texto escapado, o
# revienta con React #31). Ver `arquitectura.md` regla #25.
#
# El indice de la semana entra por `cellRendererParams` y NO interpolado en
# el codigo: asi es UN solo `JsCode` para las columnas en vez de uno por
# columna, y el coste de `JsCode.__init__` es cuadratico en el largo del
# texto (regla #226). Los precios se leen de `params.data`, que es la misma
# fila -- no hace falta `api.getValue`, que en esta version de AG Grid no
# existe.
_RENDER_DELTA = JsCode("""
class DeltaCelda {
    init(p) {
        this.eGui = document.createElement('div');
        var g = this.eGui.style;
        g.display = 'flex';
        g.alignItems = 'center';
        g.justifyContent = 'flex-end';
        g.height = '100%';
        // El renglon va en su PROPIA caja: la celda centra en vertical y
        // adentro el % y los precios se alinean por la linea de base — son
        // dos tallas distintas y lo que se ve alineado es el texto, no el
        // centro de sus cajas.
        var fila = document.createElement('div');
        fila.style.display = 'flex';
        fila.style.alignItems = 'baseline';
        fila.style.gap = '__GAP__';
        fila.style.lineHeight = '1.15';
        fila.style.minWidth = '0';
        fila.style.maxWidth = '100%';
        this.eGui.appendChild(fila);
        var a = document.createElement('span');
        a.textContent = p.valueFormatted == null ? '' : p.valueFormatted;
        // Sin `nowrap` un valor largo se parte en dos renglones DENTRO de
        // la fila y desborda por abajo, encima de su vecina.
        a.style.whiteSpace = 'nowrap';
        a.style.flex = 'none';
        fila.appendChild(a);
        if (p.value == null || Math.abs(Number(p.value)) < __EPS__) return;
        var d = p.data || {};
        var prev = d['__prev_' + p.idx];
        var cur = d['__cur_' + p.idx];
        if (prev == null || cur == null) return;
        var v = Number(p.value);
        var b = document.createElement('span');
        b.textContent = this.num(prev) + ' → ' + this.num(cur);
        b.style.fontSize = '__TAM__';
        b.style.fontWeight = '400';
        // El tono OSCURO del mismo semaforo de la pastilla; debajo de 1% la
        // pastilla no se pinta (ver `_STYLE_DELTA`) y los precios van en el
        // gris de su texto.
        b.style.color = Math.abs(v) < 1 ? '__GRIS__'
                      : (v > 0 ? '__SUBE__' : '__BAJA__');
        // Que un precio mas ancho de lo previsto FALLE VISIBLE en vez de
        // cortarse por la mitad: "169.41" recortado a "169.4" no parece un
        // recorte, parece otro precio. El peor caso del parquet entra en el
        // piso de la columna, asi que esto es un cinturon, no el mecanismo.
        b.style.minWidth = '0';
        b.style.overflow = 'hidden';
        b.style.textOverflow = 'ellipsis';
        b.style.whiteSpace = 'nowrap';
        fila.appendChild(b);
    }
    num(v) {
        // A partir de mil, sin decimales: "1,234.56 -> 1,299.00" mide ~95px
        // y no hay columna que lo aguante; "1,235 -> 1,299" son ~62. Debajo
        // de mil los centimos son el dato (un insumo de S/ 8.50).
        var dec = Math.abs(v) >= 1000 ? 0 : 2;
        return Number(v).toLocaleString('es-PE',
            {minimumFractionDigits: dec, maximumFractionDigits: dec});
    }
    getGui() { return this.eGui; }
}
""".replace("__EPS__", str(_EPS_CERO)).replace("__TAM__", _TAM_PRECIOS)
   .replace("__GAP__", _GAP_PRECIOS).replace("__GRIS__", GRIS_TEXTO)
   .replace("__SUBE__", ERROR_TEXTO).replace("__BAJA__", CELDA_POS_TEXTO))
"""La celda de una semana: el % y, si hubo movimiento, el cierre anterior y
el nuevo a su costado.

Sin simbolo de moneda a proposito, y no es una suposicion de las que
advierte la regla #240: el drill filtra `TIPO_MONEDA` a soles antes de
calcular nada, asi que la columna no puede traer otra cosa. El "S/" lo ponen
el tooltip y la tarjeta de al lado, donde hay ancho."""


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


_CLASE_HDR_COMPACTA = "vol-hdr-compacta"
"""Clase que llevan las cabeceras de las columnas angostas (las 7 semanas y
Volatilidad). El CSS que la acompaña se arma en `renderizar_ranking_volatilidad`
y viaja por `custom_css`, o sea DENTRO del iframe del grid: no hay forma de
que se escape a otra tabla."""


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
                fontWeight: '600',
                // El mismo padding que las celdas-semana, y por el mismo
                // motivo: con los 15px por lado del tema, en una columna
                // angosta «111.2» salia «1...». Ver `_PAD_X_SEMANA`.
                padding: '{_PAD_X_SEMANA}'
            }};
        }}
    """)


_AL_MONTAR = JsCode("""
    function(params) {
        try {
            var caja = document.getElementById('gridContainer');
            if (!caja || !window.ResizeObserver) return;
            new ResizeObserver(function () {
                try { params.api.sizeColumnsToFit(); } catch (e) {}
            }).observe(caja);
        } catch (e) {}
    }
""")
"""Re-reparte las columnas cada vez que cambia el ANCHO de la grilla.

Tres mecanismos se probaron para esto el 2026-09-07 y dos no sirven, asi que
conviene dejar por que:

  * `autoSizeStrategy: fitGridWidth` (lo que pone `GridOptionsBuilder` por
    defecto) reparte UNA vez, en `onFirstDataRendered`. Plegar el rail de la
    izquierda ensancha la columna de Streamlit de 587 a 731px sin volver a
    montar la grilla: se quedaba repartida a 587, con ~160px de vacio a la
    derecha -- la mitad del "las columnas se ven apretadas" que reporto el
    usuario. Al reves (desplegar el rail) el sobrante se vuelve scroll
    horizontal.
  * `colDef.flex` reparte solo en cada resize, que es exactamente lo que
    hace falta, PERO se calcula al montar y si el cuerpo mide 0 se queda en
    el ancho por defecto (200px) para siempre. Esta vista es una
    `seccion_perezosa`, o sea que se construye fuera de pantalla: dos
    renders del mismo codigo dieron 48.6px y 200px de columna segun donde
    estuviera el scroll.
  * `onGridSizeChanged` no llega: st_aggrid registra SU PROPIO listener del
    evento (`this.state.api.addEventListener("gridSizeChanged", ...)`, en el
    bundle del componente) y, a diferencia de lo que hace con `onGridReady`,
    no llama al del usuario.

Queda `onGridReady`, que el componente SI reenvia (`let {onGridReady: o} =
this.state.gridOptions; o && o(e)`), y desde ahi un `ResizeObserver` sobre
`#gridContainer` -- el div que st_aggrid dibuja dentro del iframe y que
`estilos/_80_cards.py` + el `custom_css` de mas abajo estiran al ancho real
de la columna. `sizeColumnsToFit` respeta los `minWidth`, asi que el reparto
nunca baja de los pisos; si ni los pisos entran, sale scroll horizontal.

LO QUE ESTA MEDIDO Y LO QUE NO, que es justo la clase de cosa que despues
nadie recuerda: que este `onGridReady` CORRE y deja el observer puesto se
comprobo en el navegador (una marca en el DOM del iframe). Que el observer
DISPARE no se pudo comprobar ahi: en la sesion instrumentada el documento
del iframe no estaba corriendo sus pasos de render -- ni `ResizeObserver` ni
`window.onresize` entregaban nada, tampoco al cambiar el tamano de la
ventana entera, que es sintoma del navegador automatizado y no de Streamlit
(AG Grid usa el mismo mecanismo para su propio relayout). O sea: el reparto
AL MONTAR esta verificado a 587 y a 731px; el re-reparto tardio, no.

Si algun dia se ve que no re-reparte en un navegador de verdad, el plan B
medido es un `setInterval` que compare `clientWidth`: los timers si corren."""


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
    gb.configure_column("Insumo", pinned="left", width=_ANCHO_COL_INSUMO,
                        minWidth=_ANCHO_COL_INSUMO,
                        tooltipValueGetter=_TOOLTIP_INSUMO)
    gb.configure_column("__insumo_full", hide=True)

    for i, (col, prev_label, hdr) in enumerate(zip(cols_sem, labels_prev,
                                                   headers)):
        gb.configure_column(
            col, header_name=hdr, type=["numericColumn"],
            width=_ANCHO_COL_SEMANA, minWidth=_MIN_ANCHO_COL_SEMANA,
            headerClass=_CLASE_HDR_COMPACTA,
            valueFormatter=_FMT_PCT, cellStyle=_STYLE_DELTA,
            cellRenderer=_RENDER_DELTA, cellRendererParams={"idx": i},
            tooltipValueGetter=_tooltip_delta(i, prev_label, col),
        )
        gb.configure_column(f"__prev_{i}", hide=True)
        gb.configure_column(f"__cur_{i}", hide=True)

    max_vol = (max((float(v) for v in tv["Volatilidad"]), default=0.0) or 1.0)
    gb.configure_column("Volatilidad", type=["numericColumn"], width=_ANCHO_COL_VOL,
                        minWidth=_MIN_ANCHO_COL_VOL,
                        headerClass=_CLASE_HDR_COMPACTA,
                        valueFormatter=_FMT_1DEC, cellStyle=_style_vol(max_vol))

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(rowHeight=ALTO_FILA, headerHeight=32,
                              tooltipShowDelay=200,
                              onGridReady=_AL_MONTAR,
                              # NUEVE columnas: virtualizarlas no ahorra nada
                              # y sí deja fuera del DOM a la última cuando el
                              # ancho cambia después del primer render
                              # (medido el 2026-09-07: la cabecera
                              # «Volatilidad» estaba y sus celdas no).
                              suppressColumnVirtualisation=True)
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # cuadrados negros en Chrome < 120: arquitectura.md #159

    # SIN RAYADO (2026-09-12, a pedido): las filas van todas en blanco. Lo
    # que separa una fila de la siguiente ya lo hacen la linea de `.ag-row`
    # y el borde transparente de 3px de cada pastilla; el gris alternado
    # competia con el rojo/verde claro de las pastillas.
    custom_css = dict(_css_grid(13, cebra=False))
    # La cabecera de las columnas angostas: menos padding y menos cuerpo que
    # el resto de la grilla. Ver `_PAD_X_COL` para la medición.
    custom_css[f".{_CLASE_HDR_COMPACTA}"] = {
        "padding-left": f"{_PAD_X_COL} !important",
        "padding-right": f"{_PAD_X_COL} !important",
    }
    custom_css[f".{_CLASE_HDR_COMPACTA} .ag-header-cell-text"] = {
        "font-size": f"{_TAM_HDR_SEMANA} !important",
    }
    # QUE LA GRILLA OCUPE SU COLUMNA, no el ancho que tenía al renderizarse.
    # Ver `_REPARTIR_ANCHO`: `#gridContainer` es el div que st_aggrid dibuja
    # DENTRO del iframe con el ancho de Python escrito a mano (`width:
    # 587px`). El gemelo de afuera —el iframe mismo— lo estira
    # `estilos/_80_cards.py`, que es el único CSS que llega al documento de
    # la app; éste viaja en `custom_css`, o sea dentro del iframe.
    custom_css["#gridContainer"] = {"width": "100% !important"}
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
