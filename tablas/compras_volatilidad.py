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
    ACENTO, ACENTO_TEXTO_OSCURO, BLANCO, CELDA_POS_TEXTO, ERROR, ERROR_TEXTO,
    EXITO, GRIS_BORDE, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO,
    TEXTO_PRINCIPAL,
)
from tablas._config import _parchar_iconos
from tablas._css import _css_grid

# EL REPARTO. Sólo las columnas-semana se reparten: «Insumo» y «Volatilidad»
# llevan `suppressSizeToFit` y miden lo que dicen sus constantes. Con pocas
# semanas (una ventana corta) las columnas-semana se estiran hasta llenar la
# grilla; con muchas —la historia de 12m son ~52— quedan en su piso y la
# grilla se desliza. Quien lo dispara es `_AL_MONTAR`, más abajo.
#
# 98 -> 120 el 2026-09-12, con el piso: un ancho declarado POR DEBAJO de su
# `minWidth` hace que AG Grid arranque la columna en el piso y reparta el
# resto con una proporción que ya no es la escrita acá.
_ANCHO_COL_SEMANA = 120
_ANCHO_COL_VOL = 104
"""Ancho FIJO de «Volatilidad», fijada a la derecha. Lo manda su cabecera de
dos renglones: el período de abajo («10 Ago – 13 Set», ~80px a 10px) más
los 12 del padding de `_PAD_X_COL`, con aire. El número más grande que hay
hoy en el parquet, «12402.5», mide ~46.

Era un PESO en el reparto (80, con piso de 78) mientras la columna era la
última de la grilla y competía por el ancho con las semanas. Desde el
2026-09-12 va fijada y oculta por defecto: no compite con nadie."""

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

_ANCHO_COL_INSUMO = 240
"""Ancho FIJO de «Insumo» (`suppressSizeToFit`), fijada a la izquierda. 240
son los 34 caracteres a los que `volatilidad.py` trunca el nombre, a 13px,
más el espacio de las flechas ‹ › de la cabecera; el nombre entero sigue en
el tooltip.

El piso NO es un techo, y acá decía lo contrario hasta el 2026-09-12: que
con `width == minWidth` "el reparto no le da ni le saca nada". Le saca no,
pero le DA: `sizeColumnsToFit` escala también a la columna fijada, y con la
grilla a todo el ancho de la tarjeta «Insumo» llegó a medir 257. Lo que la
frena es `suppressSizeToFit` (o `maxWidth`), no su piso — y hace falta
frenarla desde que la grilla se desliza: con ~52 semanas el reparto no
entra y `sizeColumnsToFit` la bajaría a su piso.

Era 170 y bajó a 150 el 2026-09-07, cuando la grilla medía 587px."""

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
        // La FLECHA en el lugar del signo (2026-09-12, regla #390): con
        // la celda sin fondo, la dirección tiene que decirse con algo más
        // que el color, y sumarla AL LADO del signo son dos glifos más en
        // una columna medida al píxel (`_MIN_ANCHO_COL_SEMANA`).
        var sign = v > 0 ? '\\u25B4' : '\\u25BE';
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

_TAM_FLECHA = "8px"
"""La flecha ▴/▾ que hace de signo del % (regla #390). A este cuerpo mide
8px, lo mismo que el «+» que reemplazó: «▴107%» a peso 600 son 36px, igual
que «+107%» antes. Ver el comentario en `_RENDER_DELTA`."""

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

_UMBRAL_ALARMA = 50
"""Desde qué |%| semanal una celda es ALARMA: negrita, tono oscuro y una raya
de 3px al pie, larga en proporción al salto (topada en `_TOPE_BARRA`).
Debajo, el semáforo en la letra y nada más.

Es LA señal de la tabla desde el 2026-09-12 (regla #390): con pastilla en
cada celda que se movía, casi toda la grilla iba pintada y el color dejó de
separar un +562% de un −8%. La barra aparece SÓLO pasando el umbral: acá
la barra es la alarma, no una medida de todas las celdas. En esta tabla
±50% en una semana pasa, así que el umbral es más alto que el ±30% de
«Vs año pasado»."""

_TOPE_BARRA = 150
"""El % en el que la raya de alarma llena la celda. Sin tope, un +562% la
llena y un +63% queda en una muesca: los dos son alarma y tienen que
leerse como tal."""

_STYLE_DELTA = JsCode(f"""
    function(params) {{
        // El borde TRANSPARENTE era el canal entre pastillas, cuando la
        // celda llevaba fondo (hasta el 2026-09-12). Se queda porque es
        // parte del ancho que mide `_MIN_ANCHO_COL_SEMANA` —sacarlo mueve
        // la cuenta— y porque la raya de alarma cuelga del mismo recuadro.
        //
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
        var sube = v > 0;
        if (Math.abs(v) < {_UMBRAL_ALARMA}) return Object.assign(base, {{
            color: sube ? '{ERROR}' : '{EXITO}', fontWeight: '500'}});
        // La raya: un fondo y no un elemento, igual que la barra de
        // «Volatilidad» (`_style_vol`). Alineada a la DERECHA como el
        // número, y con `background-origin: content-box` termina donde
        // termina el texto, no contra el borde de la celda.
        var c = sube ? '{ERROR}' : '{EXITO}';
        var w = Math.max(8, Math.round(Math.min(Math.abs(v), {_TOPE_BARRA})
                                       / {_TOPE_BARRA} * 100));
        return Object.assign(base, {{
            color: sube ? '{ERROR_TEXTO}' : '{CELDA_POS_TEXTO}',
            // 600 y no 700: es el peso que tenía la pastilla, y el que
            // entra en la cuenta de `_MIN_ANCHO_COL_SEMANA` — a 700
            // «107%» mide 3px más.
            fontWeight: '600',
            backgroundImage: 'linear-gradient(' + c + ',' + c + ')',
            backgroundSize: w + '% 3px',
            backgroundRepeat: 'no-repeat',
            backgroundPosition: 'right bottom 1px',
            backgroundOrigin: 'content-box'}});
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
# y los precios en GRIS.
#
# El gris ya se había probado y descartado ese mismo día: «los despegaba de
# su celda» — pero la celda era una PASTILLA de color, y un gris adentro de
# una pastilla roja se lee como otra cosa. Desde que la celda va sin fondo
# (regla #390) no hay pastilla de la que despegarse, y el tono del semáforo
# en los precios duplicaba el rojo del % al lado: dos rojos por celda en
# una tabla a la que se le estaba sacando color.
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
        var txt = p.valueFormatted == null ? '' : String(p.valueFormatted);
        // La flecha que `_FMT_PCT` pone en el lugar del signo va en su
        // PROPIO span, más chica: al cuerpo del % mide 11px contra los 8
        // del «+» que reemplaza, y con eso el par de precios del peor caso
        // dejaba de entrar en `_MIN_ANCHO_COL_SEMANA` (medido: «108.84» se
        // cortaba en «108.…»). A `_TAM_FLECHA` mide 8 y la cuenta de la
        // columna queda como estaba.
        var c0 = txt.charAt(0);
        if (c0 === '\\u25B4' || c0 === '\\u25BE') {
            var fl = document.createElement('span');
            fl.textContent = c0;
            fl.style.fontSize = '__TAM_FLECHA__';
            fl.style.verticalAlign = '1px';
            a.appendChild(fl);
            a.appendChild(document.createTextNode(txt.slice(1)));
        } else {
            a.textContent = txt;
        }
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
        var b = document.createElement('span');
        b.textContent = this.num(prev) + ' → ' + this.num(cur);
        b.style.fontSize = '__TAM__';
        b.style.fontWeight = '400';
        b.style.color = '__GRIS__';
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
   .replace("__TAM_FLECHA__", _TAM_FLECHA))
"""La celda de una semana: el % y, si hubo movimiento, el cierre anterior y
el nuevo a su costado.

Sin simbolo de moneda a proposito, y no es una suposicion de las que
advierte la regla #240: el drill filtra `TIPO_MONEDA` a soles antes de
calcular nada, asi que la columna no puede traer otra cosa. El "S/" lo ponen
el tooltip y la tarjeta de al lado, donde hay ancho."""


_TOOLTIP_INSUMO = JsCode(
    "function(params){ return params.data ? params.data['__tip_insumo'] : ''; }")
"""El nombre entero y, debajo, el puntaje con su puesto y su período. Es la
forma de CONSULTAR la volatilidad con la columna oculta (2026-09-12). El
texto lo arma Python y viaja en la fila (`__tip_insumo`), no en el código:
datos adentro de un `JsCode` es la regla #226."""


_TOOLTIP_DELTA = JsCode("""
    function(params) {
        var cp = params.colDef.cellRendererParams || {};
        var d = params.data || {};
        var prev = d['__prev_' + cp.idx];
        var cur = d['__cur_' + cp.idx];
        if (prev == null || cur == null) return '';
        var fmt = function(v) {
            return 'S/ ' + Number(v).toLocaleString('es-PE',
                {minimumFractionDigits: 2, maximumFractionDigits: 2});
        };
        return cp.lp + ': ' + fmt(prev) + ' \\u2192 ' + cp.lc + ': ' + fmt(cur);
    }
""")
"""Cierre de la semana ANTERIOR → cierre de ESTA semana: las dos cifras que
explican el % de la celda (el delta es cierre a cierre, no apertura/cierre
de la MISMA semana -- eso lo muestra el candlestick de abajo).

UNO SOLO para todas las columnas desde el 2026-09-12: los rótulos de las dos
semanas llegan por `cellRendererParams` (`lp`/`lc`), igual que el índice.
Era una fábrica que interpolaba los rótulos en el código, un `JsCode` por
columna; con la historia a la vista son ~52 columnas y cada una habría
viajado con su copia de la función."""


_CLASE_HDR_COMPACTA = "vol-hdr-compacta"
"""Clase que llevan las cabeceras de las columnas-semana y de Volatilidad. El
CSS que la acompaña se arma en `renderizar_ranking_volatilidad` y viaja por
`custom_css`, o sea DENTRO del iframe del grid: no hay forma de que se
escape a otra tabla."""

_CLASE_HDR_MIDE = "vol-hdr-mide"
"""Cabecera de las columnas-semana que SUMAN el puntaje de «Volatilidad» (las
últimas cuatro). Van resaltadas —una raya oscura arriba y el rótulo en
negrita; hasta la regla #390 era además un fondo lavanda más lleno— para
que se distingan de la historia que se ve al deslizar
(2026-09-12, a pedido, después de «¿de dónde sale el 10 Ago?»). Qué columna
lleva la marca lo decide `volatilidad.py` (`mide` en `cols_sem`)."""

_PASO_NAV = 4
"""Cuántas semanas corre cada flecha ‹ › de la cabecera de «Insumo». Cuatro
es lo que se lee de un vistazo en la grilla a todo el ancho (entran ~8), así
que cada clic deja a la vista la mitad de lo que se veía: se sabe de dónde
se viene."""

_HDR_INSUMO = JsCode("""
class HdrInsumo {
    init(p) {
        this.p = p;
        var g = this.eGui = document.createElement('div');
        g.style.display = 'flex';
        g.style.alignItems = 'center';
        g.style.gap = '2px';
        g.style.width = '100%';
        var t = document.createElement('span');
        t.className = 'ag-header-cell-text';
        t.textContent = p.displayName;
        t.style.flex = '1 1 auto';
        g.appendChild(t);
        var self = this;
        [['\\u2039', -1, 'Semanas anteriores'],
         ['\\u203a', 1, 'Semanas siguientes']].forEach(function (b) {
            var e = document.createElement('button');
            e.type = 'button';
            e.className = 'vol-nav';
            e.textContent = b[0];
            e.title = b[2];
            e.addEventListener('click', function (ev) {
                ev.stopPropagation();
                self.mover(b[1]);
            });
            g.appendChild(e);
        });
    }
    mover(dir) {
        var api = this.p.api;
        var cols = api.getAllDisplayedColumns().filter(function (c) {
            return !c.getPinned();
        });
        if (!cols.length) return;
        var r = api.getHorizontalPixelRange();
        var i;
        if (dir < 0) {
            i = cols.findIndex(function (c) { return c.getLeft() >= r.left - 1; });
            if (i < 0) i = 0;
            api.ensureColumnVisible(cols[Math.max(0, i - __PASO__)], 'start');
        } else {
            i = cols.findIndex(function (c) {
                return c.getLeft() + c.getActualWidth() > r.right + 1;
            });
            if (i < 0) return;
            api.ensureColumnVisible(
                cols[Math.min(cols.length - 1, i + __PASO__ - 1)], 'end');
        }
    }
    getGui() { return this.eGui; }
}
""".replace("__PASO__", str(_PASO_NAV)))
"""La cabecera de «Insumo», con las flechas para recorrer las semanas.

Viven ACÁ y no en la cabecera de la tarjeta (donde las mostraba la maqueta
del 2026-09-12) porque tienen que mover el scroll de la grilla, y la grilla
corre en un iframe: un botón de Streamlit sólo puede pedir un rerun, que
tarda segundos y vuelve a montar la vista. Desde la cabecera de una columna
las flechas tienen `params.api` a mano y el movimiento es instantáneo.

`ensureColumnVisible` y no `scrollBy` sobre el viewport: AG Grid sincroniza
tres contenedores (cabecera, cuerpo y la barra horizontal) y mover sólo uno
los desfasa. `getHorizontalPixelRange` dice qué tramo está a la vista.

`class` con `init`/`getGui` por lo mismo que `_RENDER_DELTA` (regla #25)."""

_HDR_VOL = JsCode("""
class HdrVol {
    init(p) {
        var g = this.eGui = document.createElement('div');
        g.style.display = 'flex';
        g.style.flexDirection = 'column';
        g.style.alignItems = 'flex-end';
        g.style.justifyContent = 'center';
        g.style.width = '100%';
        g.style.lineHeight = '1.15';
        var a = document.createElement('span');
        a.className = 'ag-header-cell-text';
        a.textContent = p.displayName;
        var b = document.createElement('span');
        b.className = 'vol-hdr-periodo';
        b.textContent = p.periodo || '';
        g.appendChild(a);
        g.appendChild(b);
    }
    getGui() { return this.eGui; }
}
""")
"""«Volatilidad» y, debajo, el período que mide (2026-09-12, a pedido: «un
texto en la columna volatilidad que diga el tiempo sobre el que está
calculado»). Hace falta desde que la grilla se desliza hacia atrás: las
semanas viejas quedan a la vista pero NO entran en el número, y sin el
período escrito la columna parecería resumir todo lo que se ve.

Un componente y no `wrapHeaderText`: el partido del texto lo decidiría el
ancho, y «Volatilidad 10 Ago» / «– 13 Set» corta el período por la mitad.
El período llega por `headerComponentParams`, no interpolado."""


def _style_vol(max_vol):
    """La barra de volatilidad, FINA: el número sobre blanco y una raya de
    3px abajo, larga en proporción al máximo de la tabla.

    Hasta el 2026-09-12 era un degradé de `ACENTO` que pintaba la celda
    entera, con el número en gris oscuro encima — en los primeros puestos,
    los que más importan, la barra llenaba la celda y el número casi no se
    leía («ese color que oscurece el número», pedido con captura). Se
    maquetaron tres variantes y se eligió ésta."""
    return JsCode(f"""
        function(params) {{
            if (params.value === null || params.value === undefined) return {{}};
            var pct = Math.round(Number(params.value) / {max_vol} * 100);
            return {{
                backgroundColor: '{BLANCO}',
                backgroundImage: 'linear-gradient(90deg, {ACENTO} ' + pct
                    + '%, {GRIS_LINEA} ' + pct + '%)',
                backgroundSize: '100% 3px',
                backgroundRepeat: 'no-repeat',
                backgroundPosition: '0 calc(100% - 5px)',
                backgroundOrigin: 'content-box',
                color: '{ACENTO_TEXTO_OSCURO}',
                fontWeight: '600',
                padding: '0 {_PAD_X_COL}'
            }};
        }}
    """)


_AL_MONTAR = JsCode("""
    function(params) {
        var api = params.api;
        var centro = function () {
            return api.getAllDisplayedColumns().filter(
                function (c) { return !c.getPinned(); });
        };
        var alFinal = function () {
            try {
                var cols = centro();
                if (cols.length) api.ensureColumnVisible(cols[cols.length - 1], 'end');
            } catch (e) {}
        };
        var flechas = function () {
            try {
                var vp = document.querySelector('.ag-center-cols-viewport');
                var sobra = !!vp && vp.scrollWidth > vp.clientWidth + 1;
                document.body.classList.toggle('vol-sin-scroll', !sobra);
            } catch (e) {}
        };
        var ajustar = function () {
            try { api.sizeColumnsToFit(); } catch (e) {}
            setTimeout(flechas, 0);
            setTimeout(flechas, 250);
        };
        var firma = function () {
            return centro().map(function (c) { return c.getColId(); }).join('|');
        };
        var ultima = firma();
        try {
            var caja = document.getElementById('gridContainer');
            if (caja && window.ResizeObserver) {
                var primera = true;
                new ResizeObserver(function () {
                    ajustar();
                    if (primera) { primera = false; alFinal(); }
                }).observe(caja);
            }
        } catch (e) {}
        try {
            api.addEventListener('displayedColumnsChanged', function () {
                ajustar();
                var f = firma();
                if (f !== ultima) { ultima = f; setTimeout(alFinal, 0); }
            });
        } catch (e) {}
        setTimeout(alFinal, 0);
    }
""")
"""Al montar: re-reparte las columnas cada vez que cambia el ANCHO de la
grilla o su JUEGO DE COLUMNAS, la abre en la semana MÁS RECIENTE, y esconde
las flechas ‹ › cuando todas las semanas entran.

LAS COLUMNAS CAMBIAN SIN VOLVER A MONTAR, y eso lo destapó una captura del
usuario (2026-09-12): en «Rango», cuatro columnas-semana de 120px y ~470px
vacíos a la derecha. La grilla se había montado con la ventana de 12m (53
columnas, que no entran y quedan en su piso); al pasar a Rango, st_aggrid le
cambia las columnas a la MISMA grilla —la key no cambia— y el ancho del
contenedor no se mueve, así que el `ResizeObserver` no tenía de qué
enterarse. Por eso ahora también escucha `displayedColumnsChanged`, que se
engancha con `api.addEventListener` (el `onXxx` de `gridOptions` no está
garantizado: ver `onGridSizeChanged`, abajo).

Y en ese mismo evento, si cambió QUÉ semanas hay (la `firma` son los ids
de las columnas del centro), vuelve a la más reciente — si no, al pasar de
Rango a 12m se abría en la más vieja. Prender o apagar «Volatilidad» no
cambia la firma (va fijada, no es del centro), así que no le roba al
usuario la semana a la que había ido.

LAS FLECHAS se esconden con una clase en el `<body>` del iframe y no
tocando los botones: la cabecera de «Insumo» se vuelve a construir cuando
cambian las columnas, y un estilo puesto al botón viejo se perdería con él.

LO PRIMERO, y por qué es `onGridReady`. Tres mecanismos se probaron el
2026-09-07 y dos no sirven:

  * `autoSizeStrategy: fitGridWidth` (lo que pone `GridOptionsBuilder` por
    defecto) reparte UNA vez, en `onFirstDataRendered`. Plegar el rail de la
    izquierda ensancha la columna de Streamlit sin volver a montar la
    grilla: se quedaba repartida al ancho viejo.
  * `colDef.flex` reparte solo en cada resize, PERO se calcula al montar y
    si el cuerpo mide 0 se queda en el ancho por defecto (200px) para
    siempre. Esta vista es una `seccion_perezosa`: se construye fuera de
    pantalla.
  * `onGridSizeChanged` no llega: st_aggrid registra SU PROPIO listener del
    evento y, a diferencia de lo que hace con `onGridReady`, no llama al del
    usuario.

Queda `onGridReady`, que el componente SI reenvia, y desde ahi un
`ResizeObserver` sobre `#gridContainer`. `sizeColumnsToFit` respeta los
`minWidth` y no toca las columnas con `suppressSizeToFit` («Insumo» y
«Volatilidad»): con pocas semanas éstas se estiran hasta llenar; con
muchas, quedan en su piso y sale scroll horizontal, que es el mecanismo
para ir hacia atrás."""


CROMO_GRID = 32 + 4 + 15
"""Alto de la grilla que NO son filas: la cabecera (32), los bordes (4) y la
barra de scroll horizontal (15), que desde el 2026-09-12 está siempre — la
grilla recorre toda la ventana de la tarjeta. Sin sumarla, la barra se come
media fila de la última línea visible. Es el `extra` de `por_filas` en el
llamador."""


def renderizar_ranking_volatilidad(tv, cols_sem, altura, key, ver_vol=False,
                                   periodo_vol="", n_sem=None):
    """`tv`: columnas Insumo, __insumo_full (oculta, nombre sin truncar),
    __tip_insumo (oculta, el tooltip del nombre), una columna FLOAT por
    semana, __prev_i/__cur_i por semana (ocultas, cierre anterior/actual --
    alimentan la celda y el tooltip) y Volatilidad.

    `cols_sem` es una lista pareada con esas columnas-semana, un dict por
    columna: `col` (el nombre en `tv`, único), `hdr` (el rótulo de la
    cabecera), `lp`/`lc` (los rótulos de la semana anterior y de ésta, para
    el tooltip). El nombre es otro texto que el rótulo a propósito: con más
    de un año a la vista dos rótulos pueden repetirse, y el nombre es la
    clave del DataFrame.

    `ver_vol` muestra la columna «Volatilidad» (fijada a la derecha, con
    `periodo_vol` debajo del título); oculta es el default desde el
    2026-09-12. `n_sem` son las semanas que mide el puntaje, para el tooltip
    de la cabecera.

    Devuelve el nombre completo del insumo de la fila clickeada en ESTA
    corrida (`__insumo_full`), o None si no hubo clic."""
    gb = GridOptionsBuilder.from_dataframe(tv)
    # SIN `wrapHeaderText`/`autoHeaderHeight` desde el 2026-09-12: con 120px
    # por columna-semana los rótulos entran en un renglón, y la cabecera de
    # dos líneas de «Volatilidad» la dibuja su propio componente. Así el
    # alto de la cabecera es SIEMPRE `headerHeight`, que es lo que cuenta
    # `CROMO_GRID`.
    gb.configure_default_column(
        resizable=False, sortable=False, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    gb.configure_column("Insumo", pinned="left", width=_ANCHO_COL_INSUMO,
                        minWidth=_ANCHO_COL_INSUMO, suppressSizeToFit=True,
                        tooltipValueGetter=_TOOLTIP_INSUMO,
                        headerComponent=_HDR_INSUMO)
    gb.configure_column("__insumo_full", hide=True)
    gb.configure_column("__tip_insumo", hide=True)

    # Las columnas-semana comparten TODO su código por un `columnType`: el
    # renderer, el formato, el estilo y el tooltip viajan una vez en
    # `columnTypes` y no una por columna (con 12m son ~52). Cada columna
    # sólo lleva lo suyo, que es dato: el rótulo y sus `cellRendererParams`.
    for i, c in enumerate(cols_sem):
        gb.configure_column(
            c["col"], header_name=c["hdr"], type=["numericColumn", "semana"],
            cellRendererParams={"idx": i, "lp": c["lp"], "lc": c["lc"]},
            # La `headerClass` de la columna PISA a la del `columnType`, así
            # que la compacta va repetida en la lista.
            headerClass=([_CLASE_HDR_COMPACTA, _CLASE_HDR_MIDE] if c.get("mide")
                         else _CLASE_HDR_COMPACTA),
            headerTooltip=c.get("tip"),
        )
        gb.configure_column(f"__prev_{i}", hide=True)
        gb.configure_column(f"__cur_{i}", hide=True)

    max_vol = (max((float(v) for v in tv["Volatilidad"]), default=0.0) or 1.0)
    gb.configure_column(
        "Volatilidad", type=["numericColumn"], pinned="right",
        hide=not ver_vol, width=_ANCHO_COL_VOL, minWidth=_ANCHO_COL_VOL,
        suppressSizeToFit=True, headerClass=_CLASE_HDR_COMPACTA,
        headerComponent=_HDR_VOL,
        headerComponentParams={"periodo": periodo_vol},
        headerTooltip=(f"Suma de las variaciones % semanales de las últimas "
                       f"{n_sem} semanas ({periodo_vol}). Las semanas "
                       "anteriores que se ven al deslizar no entran en este "
                       "número." if n_sem else None),
        valueFormatter=_FMT_1DEC, cellStyle=_style_vol(max_vol))

    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        onGridReady=_AL_MONTAR,
        columnTypes={"semana": {
            "width": _ANCHO_COL_SEMANA, "minWidth": _MIN_ANCHO_COL_SEMANA,
            "headerClass": _CLASE_HDR_COMPACTA,
            "valueFormatter": _FMT_PCT, "cellStyle": _STYLE_DELTA,
            "cellRenderer": _RENDER_DELTA, "tooltipValueGetter": _TOOLTIP_DELTA,
        }},
        # La barra horizontal SIEMPRE, aunque las semanas entren: así el alto
        # de la grilla no depende de cuántas semanas trae la ventana, y
        # `CROMO_GRID` no miente cuando la ventana es corta.
        alwaysShowHorizontalScroll=True,
        # Sin virtualizar columnas, y ya no por la razón de antes (que la
        # última, «Volatilidad», quedaba fuera del DOM al cambiar el ancho:
        # hoy va fijada a la derecha y las fijadas se dibujan siempre). Es
        # que las flechas y la apertura en la semana más reciente saltan
        # lejos, y una columna virtualizada aparece vacía un instante al
        # llegar. Con 12m son ~52 columnas x las ~17 filas que AG Grid
        # dibuja (7 a la vista + su búfer): cabe de sobra.
        suppressColumnVirtualisation=True)
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # cuadrados negros en Chrome < 120: arquitectura.md #159

    # SIN RAYADO (2026-09-12, a pedido): las filas van todas en blanco. Lo
    # que separa una fila de la siguiente ya lo hacen la linea de `.ag-row`
    # y el borde transparente de 3px de cada pastilla; el gris alternado
    # competia con el rojo/verde claro de las pastillas.
    custom_css = dict(_css_grid(13, cebra=False, cabecera_neutra=True))
    # La cabecera de las columnas angostas: menos padding y menos cuerpo que
    # el resto de la grilla. Ver `_PAD_X_COL` para la medición.
    custom_css[f".{_CLASE_HDR_COMPACTA}"] = {
        "padding-left": f"{_PAD_X_COL} !important",
        "padding-right": f"{_PAD_X_COL} !important",
    }
    custom_css[f".{_CLASE_HDR_COMPACTA} .ag-header-cell-text"] = {
        "font-size": f"{_TAM_HDR_SEMANA} !important",
    }
    # Las semanas que MIDEN: una raya oscura arriba, como una pestaña, y el
    # rótulo en negrita. Hasta el 2026-09-12 eran además un fondo lavanda
    # más lleno sobre la cabecera lavanda; con la cabecera neutra (regla
    # #390) la marca se quedó con lo que no es color. `.ag-header-cell.clase`
    # y con `!important` porque `_css_grid` pinta TODAS las cabeceras así.
    custom_css[f".ag-header-cell.{_CLASE_HDR_MIDE}"] = {
        "box-shadow": f"inset 0 2px 0 {GRIS_TEXTO_MEDIO} !important",
    }
    custom_css[f".{_CLASE_HDR_MIDE} .ag-header-cell-text"] = {
        "font-weight": "600 !important",
        "color": f"{TEXTO_PRINCIPAL} !important",
    }
    # El período, debajo de «Volatilidad»: más chico y en gris, es la nota
    # al pie del título, no un segundo título.
    custom_css[".vol-hdr-periodo"] = {
        "font-size": "10px",
        "font-weight": "400",
        "color": f"{GRIS_TEXTO}",
        "white-space": "nowrap",
    }
    # Las flechas de la cabecera de «Insumo»: botones mínimos con el color
    # del texto de la cabecera, sin marco hasta el hover.
    #
    # CON `!important`, y no por costumbre: sin él, en la app publicada se
    # veían como dos cajas grises con borde (captura del 2026-09-12) — el
    # estilo de `<button>` del tema o del navegador les ganaba a estas
    # reglas, que viajan en `custom_css` sin prioridad garantizada.
    custom_css[".vol-nav"] = {
        "border": "1px solid transparent !important",
        "background": "transparent !important",
        "box-shadow": "none !important",
        "color": f"{GRIS_TEXTO_MEDIO} !important",
        "border-radius": "6px !important",
        "width": "22px !important",
        "height": "22px !important",
        "padding": "0 !important",
        "font-size": "16px !important",
        "line-height": "18px !important",
        "cursor": "pointer",
    }
    custom_css[".vol-nav:hover"] = {
        "background": f"{BLANCO} !important",
        "border-color": f"{GRIS_BORDE} !important",
    }
    # Sin nada que deslizar, sin flechas (la clase la pone `_AL_MONTAR`).
    custom_css[".vol-sin-scroll .vol-nav"] = {
        "visibility": "hidden !important",
    }
    # QUE LA GRILLA OCUPE SU COLUMNA, no el ancho que tenía al renderizarse.
    # `#gridContainer` es el div que st_aggrid dibuja DENTRO del iframe con el
    # ancho de Python escrito a mano. El gemelo de afuera —el iframe mismo— lo
    # estira `estilos/_80_cards.py`, que es el único CSS que llega al
    # documento de la app; éste viaja en `custom_css`, o sea dentro del iframe.
    custom_css["#gridContainer"] = {"width": "100% !important"}
    custom_css[".ag-tooltip"] = {
        "background-color": f"{TEXTO_PRINCIPAL} !important",
        "color": "#ffffff !important",
        "border": "none !important",
        "border-radius": "6px !important",
        "padding": "6px 10px !important",
        "font-size": "12px !important",
        "box-shadow": "0 6px 20px rgba(0,0,0,0.25) !important",
        # El tooltip del nombre son dos renglones (nombre / puntaje): sin
        # esto el salto de línea se colapsa en un espacio.
        "white-space": "pre-line !important",
    }

    resp = AgGrid(
        tv, gridOptions=grid_options, height=altura, theme="material",
        custom_css=custom_css, allow_unsafe_jscode=True, key=key,
    )
    sel = resp.selected_rows
    if sel is not None and not sel.empty:
        return str(sel.iloc[0]["__insumo_full"])
    return None
