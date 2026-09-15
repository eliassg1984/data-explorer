"""graficos.ajuste._cascada - vista Cascada: UNA TARJETA POR FAMILIA.

OJO: NO es un grafico Plotly. Son tarjetas de Streamlit con HTML adentro.

HISTORIA, porque explica la forma. Hasta el 2026-09-14 esto era una TABLA
de filas (st.columns + HTML) con una columna de barras encadenadas que
dibujaban una cascada de verdad: cada barra arrancaba donde terminaba la
anterior. Se rehizo por tres cosas medidas en la app corriendo:

  1. El chevron que abria el drill media 16 x 36 px dentro de una fila de
     1081 x 46 -- el 1,16 % de la superficie. La fila ENTERA se pintaba de
     lavanda al pasar el mouse (o sea, prometia ser clickeable) pero el
     cursor seguia siendo flecha y el 98,84 % no hacia nada. Reportado como
     "hago clic y a veces no pasa nada". Ver arquitectura.md regla #421.
  2. Los tres tintes de renglon por severidad (critico/alerta/sobrante)
     estaban al 8-9 % de opacidad: compuestos sobre el blanco de la card
     daban #FCF4F4, #F7F3EE y #F4F8F5. Indistinguibles entre si. El color
     no era poco intuitivo: no llegaba a verse. Ver regla #422.
  3. El tinte, la pastilla de Estado, el "65 % del total" y el largo de la
     barra codificaban TODOS el mismo numero (el peso de la familia en el
     ajuste total). Cuatro canales para una variable, mientras el dato que
     si alarma -- cuanto se fue contra el stock que la familia tiene --
     vivia en una columna sin rotulo, como "-177.9 %".

La cascada encadenada no sobrevive a la particion en tarjetas: encadenar
exige un eje continuo compartido. La reemplaza una barra desde el CERO, con
el cero en el mismo sitio horizontal en todas las tarjetas, asi que los
largos se siguen comparando de un vistazo. El orden entre familias era
arbitrario igual (se ordenaba por valor con signo), asi que el acumulado no
contaba ninguna historia.

DISPOSICION: protagonista + riel. La familia con foco ocupa el bloque
grande con sus faltantes y sobrantes; el resto queda como mini-tarjetas
apiladas al costado. Se eligio sobre "va primero" porque el lugar del
protagonista NO se mueve -- solo cambia lo que tiene adentro -- y con
reruns de 3-6s un reordenamiento de seis tarjetas sin animacion se lee como
que la pagina se rompio. Animarlo no es opcion: cada rerun crea nodos DOM
nuevos y `st.markdown` no ejecuta <script>. Ver regla #423.
"""


import streamlit as st

from tema import (
    ACENTO, GRIS_BORDE, GRIS_FONDO,
    TEXTO_PRINCIPAL,
    BLANCO, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_SELECCION,
    AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO,
)
from graficos.base import (
    _slug,
)
# Los tres filtros propios (corte · familia · área) viven en `_comun.py`
# desde el 2026-09-15: el Mapa de calor pidió los mismos, y dos copias de
# "con qué abre la vista" se desincronizan a la primera corrección.
from graficos.ajuste._comun import (
    FAMILIAS_DE_ENTRADA, css_filtros_vista, estado_filtros_vista,
    render_filtros_vista,
)


_TOPN_DRILL = 30
# Cuantos cortes entran en el minigrafico de cada mini del riel. Seis
# columnas en ~180px dan ~28px cada una: se ven de reojo y todavia
# cuentan una historia. Con doce quedan de 13px y se vuelven ruido.
_N_HISTORIAL = 6
# LAS MEDIDAS DEL MINIGRAFICO VIVEN ACA, no sueltas en dos sitios: las usa
# `_minigraf_cortes` para dibujarlo Y `_css` para recortar el boton grande
# de la mini justo por encima de el (la zona del grafico es del boton
# chico, ver #439). Si se desincronizan, el boton grande se come el hover
# del grafico o deja una franja muerta: el bug se ve como "a veces no
# aparece la etiqueta".
_ALTO_GRAF = 34        # el grafico en si (17px de columna a cada lado)
_ALTO_ROTULOS = 11     # la fila con el primer y el ultimo corte
_PAD_MINI = 9          # padding inferior de la minitarjeta (ver `_css`)
_ZONA_GRAF = 7 + _ALTO_GRAF + 2 + _ALTO_ROTULOS + _PAD_MINI
_K_FOCO = "ajuste_cascada_focus"
_K_AREA = "ajcas_filtro_area"
_K_FAMILIA = "ajcas_filtro_familia"
# El corte de ESTA vista. No usa `estado_rango.clave_corte`, que es el
# estado de la FRANJA del reporte: ahi el corte lo comparten las cuatro
# vistas de la categoria "visual" y ademas arrastra el rango, que es la key
# de un `st.date_input`. Aca la vista se filtra sola desde `df_full`, asi
# que le alcanza con recordar que clave de corte eligio. Ver regla #427.
_K_CORTE = "ajcas_corte"

# UNA KEY POR CONTROL. `st.popover` no emite `st-key-*` propio: el inspector
# y el modo diseno resuelven hacia arriba hasta el `st-key-*` mas cercano,
# que sin esto era la tarjeta ENTERA. Medido: fijar el trigger de fecha
# (240x27) pineaba `ajcas_card_ctrl` (286x235), asi que "mover" agarraba la
# tarjeta con los tres filtros y el neto adentro. Con su contenedor propio,
# cada filtro se fija y se estila por separado. Ver arquitectura.md #431.
_K_CTRL = ("ajcas_ctrl_fecha", "ajcas_ctrl_familia", "ajcas_ctrl_area")


def _tono(v):
    return ((AJUSTE_POS_TEXTO, AJUSTE_POS) if v > 0
            else (AJUSTE_NEG_TEXTO, AJUSTE_NEG))


def _frase_ratio(val, base):
    """"falto 1,8x su stock" / "sobro 18 % de su stock", o None.

    Reemplaza a la pastilla Critico/Alerta/Menor/OK, que se calculaba con
    el PESO (la parte del ajuste total que explica la familia) y no con la
    gravedad -- por eso ENVASES Y EMBALAJES salia "OK" con -157,3 %: le
    falto vez y media su propio stock, pero como eran S/ 876 pesaba 3 %.

    Un multiplo se entiende; un "-177.9 %" se lee como error de calculo.
    Arriba de 100 % se dice en "x", abajo en porcentaje.
    """
    if not base or abs(base) < 1e-6:
        return None
    _pct = val / base * 100
    _verbo = "faltó" if val < 0 else "sobró"
    _m = abs(_pct) / 100
    if _m >= 1:
        return f"{_verbo} <b>{_m:.1f}×</b> su stock"
    return f"{_verbo} <b>{abs(_pct):.0f}%</b> de su stock"


def _barra_cero(val, esc):
    """Barra desde el cero central: izquierda falta, derecha sobra.

    `esc` es el semiancho en % (0-50) ya normalizado contra el mayor
    |ajuste| de las familias visibles, asi que el largo ES comparable entre
    tarjetas -- que es lo unico que la cascada encadenada hacia bien y que
    habia que no perder al partir en tarjetas.

    VOLVIO a tener una sola barra el 2026-09-15, unas horas despues de
    tener dos. La segunda era el corte anterior, en el mismo eje y con el
    mismo idioma visual, y se reporto tal cual: "el usuario ve dos barras
    de color, una de la cascada y la otra no logra identificar". La
    comparacion contra el corte pasado la dibuja ahora
    `_minigraf_cortes`, que es otra cosa a simple vista. Ver regla #437.
    """
    _col = _tono(val)[1]
    _lado = "right:50%" if val < 0 else "left:50%"
    return (
        f"<div style='position:relative;height:18px;margin:10px 0 4px'>"
        f"<div style='position:absolute;left:0;right:0;top:50%;height:1px;"
        f"background:{GRIS_FONDO}'></div>"
        f"<div style='position:absolute;top:0;bottom:0;left:50%;width:1px;"
        f"background:{GRIS_BORDE}'></div>"
        f"<div style='position:absolute;top:50%;transform:translateY(-50%);"
        f"{_lado};width:{max(esc, 0.4):.2f}%;height:11px;"
        f"border-radius:999px;background:{_col}'></div></div>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:9.5px;color:{GRIS_BORDE};letter-spacing:.04em'>"
        f"<span>falta</span><span>0</span><span>sobra</span></div>")


def _minigraf_cortes(serie, cortes=None):
    """Micro columnas por corte: la historia de la familia, de izquierda a
    derecha, con la de AHORA al final y a color pleno.

    Reemplaza a la segunda barra horizontal (ver `_barra_cero`). El
    problema de aquella no era el dato sino el IDIOMA: dos barras del
    mismo tipo, sobre el mismo eje y con la misma pareja de colores, y no
    habia como saber cual era cual sin una leyenda. Columnas verticales
    apoyadas en una linea de base se leen como tiempo -- no como "otro
    ajuste"-- y la de mas a la derecha se lee como "hoy" sin que nadie lo
    explique. Ver regla #437.

    ESCALA PROPIA DE LA FAMILIA, y es a proposito: aca lo que se mira es
    la FORMA (venia creciendo, se dio vuelta, es estable), no cuanto pesa
    contra las demas -- eso ya lo dice la barra de arriba, que si comparte
    escala con las otras tarjetas. Con una escala global, cada familia
    chica saldria plana y el minigrafico no diria nada. Es el otro lado de
    la #436: una escala la fija aquello que el grafico vino a comparar.

    Cada columna va del color de SU signo (faltante/sobrante), asi que un
    corte que se dio vuelta se ve como un salto de lado de la linea.

    TODAS A COLOR PLENO. Las pasadas estuvieron al 42% y despues al 55%
    para que la ultima resaltara, y se reporto lo que eso produce de
    verdad: "las barras se ven como palidas, como si estuviesen detras de
    algo". Cual es la de ahora ya lo dice el SITIO --es la de mas a la
    derecha-- y lo confirma el rotulo de esa punta, que va en negrita y
    mas oscuro. Apagar el 83% del grafico para marcar el 17% restante sale
    carisimo. Ver regla #439.

    Con `cortes` (los dicts de `estado_filtros_vista`) cada columna lleva
    su `title` --el tooltip nativo del navegador, sin JS-- y debajo van
    los rotulos de las PUNTAS, primero y ultimo. Solo las puntas: un
    rotulo de fecha mide ~30px contra los 18 de una columna, y seis
    seguidos se pisan. El detalle corte por corte de las minitarjetas lo
    da `_detalle_cortes`, porque ahi el tooltip nativo no llega (el boton
    tapa la tarjeta entera, #421).
    """
    if not serie or len(serie) < 2:
        return ""
    _mx = max(abs(_v) for _v in serie) or 1.0
    _cols = []
    for _i, _v in enumerate(serie):
        _h = max(abs(_v) / _mx * 15.0, 2.0)
        _c = _tono(_v)[1] if abs(_v) > 1e-9 else GRIS_BORDE
        _pos = "bottom:17px" if _v >= 0 else "top:17px"
        _tit = ""
        if cortes and _i < len(cortes):
            _sg = "+" if _v > 0 else ("−" if _v < 0 else "")
            _tit = (f" title='{cortes[_i]['etiqueta_anio']}: "
                    f"{_sg}S/ {abs(_v):,.0f}'")
        # COLUMNA ANGOSTA CON AIRE AL LADO, no seis bloques pegados que se
        # reparten el ancho. Con `flex:1` daban 27px de ancho por 3-11 de
        # alto: a esa proporcion se leen como guiones, no como un grafico
        # de columnas. 18px de ancho contra 15 de alto ya es una columna, y
        # el `space-between` del contenedor reparte lo que sobra en aire.
        _cols.append(
            f"<div style='position:relative;flex:0 1 18px;"
            f"height:{_ALTO_GRAF}px'{_tit}>"
            f"<div style='position:absolute;{_pos};left:0;right:0;"
            f"height:{_h:.1f}px;background:{_c};"
            f"border-radius:2px'></div></div>")
    # La linea de base es `absolute`, o sea que NO es un flex item (queda
    # fuera del flujo) y las columnas no le ceden ancho.
    #
    # `max-width` para que el grafico se vea IGUAL en la mini y en la
    # protagonista: sin tope, en una tarjeta de 360px las seis columnas
    # quedan separadas 50px y se leen como puntos sueltos.
    _graf = (
        f"<div style='position:relative;display:flex;max-width:210px;"
        f"justify-content:space-between;height:{_ALTO_GRAF}px;"
        f"margin-top:7px'>"
        f"<div style='position:absolute;left:0;right:0;top:17px;height:1px;"
        f"background:{GRIS_FONDO}'></div>{''.join(_cols)}</div>")
    if not cortes:
        return _graf
    # El rotulo de la DERECHA va en negrita y mas oscuro: es el unico
    # acento que marca cual es "ahora", ahora que las columnas no se
    # apagan. `line-height` explicito porque de este alto sale `_ZONA_GRAF`
    # y de ahi el recorte del boton grande.
    return _graf + (
        f"<div style='display:flex;max-width:210px;"
        f"justify-content:space-between;font-size:9px;"
        f"line-height:{_ALTO_ROTULOS}px;color:{GRIS_TEXTO_SUAVE};"
        f"margin-top:2px'>"
        f"<span>{cortes[0]['etiqueta']}</span>"
        f"<span style='color:{GRIS_TEXTO};font-weight:600'>"
        f"{cortes[-1]['etiqueta']}</span></div>")


def _detalle_cortes(serie, cortes):
    """El panel corte-por-corte que la minitarjeta muestra al pasar el
    mouse. Se abre y se cierra con CSS puro (ver `_css`), sin JS.

    Existe porque adentro de una mini el tooltip nativo NO llega: el boton
    que la hace clickeable esta por encima con `inset: 0` (#421), asi que
    ningun hijo recibe el hover ni puede mostrar su `title`. Lo que si
    pasa es que el contenedor de la tarjeta se pone `:hover` igual --el
    boton es su descendiente--, y de ese `:hover` cuelga este panel.

    Reportado como "casi no se ve ese grafico de barras... solamente se
    ven como barras pero sin mas detalle".
    """
    if not serie or not cortes or len(serie) < 2:
        return ""
    _filas = []
    for _v, _c in zip(serie, cortes):
        _sg = "+" if _v > 0 else ("−" if _v < 0 else "")
        _col = _tono(_v)[0] if abs(_v) > 1e-9 else GRIS_TEXTO_SUAVE
        _filas.append(
            f"<div style='display:flex;justify-content:space-between;"
            f"gap:14px;white-space:nowrap;line-height:1.55'>"
            f"<span style='color:{GRIS_TEXTO}'>{_c['etiqueta_anio']}</span>"
            f"<span style='color:{_col};font-weight:600;"
            f"font-variant-numeric:tabular-nums'>"
            f"{_sg}S/ {abs(_v):,.0f}</span></div>")
    return (
        f"<div class='ajcas-detalle'>"
        f"<div style='font-size:9px;color:{GRIS_TEXTO_SUAVE};"
        f"text-transform:uppercase;letter-spacing:.07em;font-weight:600;"
        f"margin-bottom:4px'>Últimos {len(serie)} cortes</div>"
        f"{''.join(_filas)}</div>")


def _delta_corte(val, val_prev):
    """El texto de la diferencia contra el corte anterior, o None.

    SIN COLOR PROPIO, y es a proposito: en esta tarjeta el color ya
    significa faltante/sobrante, y darle una segunda lectura ("mejoro" /
    "empeoro") es el error que documenta la #423 -- varios canales
    codificando variables distintas en el mismo sitio. El chip dice
    DIRECCION y MAGNITUD; de que lado esta lo sigue diciendo la barra.

    La flecha es sobre el TAMAÑO del ajuste, no sobre el valor con signo:
    un faltante que va de -1.000 a -5.000 sale "▲ 400%" (el faltante
    crecio), que es como se lee en voz alta. Por eso el cambio de signo no
    se dice en %, que ahi no querria decir nada: se dice en palabras.

    Arriba del 999% el porcentaje deja de leerse como numero y pasa a
    "×N" -- mismo criterio que `_frase_ratio`, donde un "-177.9 %" se leia
    como error de calculo.
    """
    if val_prev is None:
        return None
    if abs(val_prev) < 0.5:
        return "nuevo"
    if (val < 0) != (val_prev < 0):
        return "pasó a sobrar" if val > 0 else "pasó a faltar"
    _pct = (abs(val) - abs(val_prev)) / abs(val_prev) * 100
    if abs(_pct) < 0.5:
        return "igual"
    _f = "▲" if _pct > 0 else "▼"
    if abs(_pct) >= 999:
        return f"{_f} ×{abs(val) / abs(val_prev):.0f}"
    return f"{_f} {abs(_pct):.0f}%"


def _css():
    _CSS_FILTROS = css_filtros_vista("ajcas_ctrl_", "ajcas_corte_")
    return f"""<style>
    /* ── Buscador de Faltantes/Sobrantes (2026-08-08, a pedido): reemplaza
       el titulo fijo -- filtra los productos de esa zona en vez de solo
       etiquetarla. data-testid="stTextInputRootElement" es la caja real;
       hay que aplanar la caja, no el <input>. */
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] {{
        height: auto !important; background: transparent !important;
        border: none !important; border-radius: 0 !important;
        border-bottom: 1px solid {GRIS_BORDE} !important;
        transition: border-color .12s ease; }}
    div[class*="st-key-ajcas_buscar_neg_"] [data-testid="stTextInputRootElement"]:focus-within {{
        border-bottom-color: {AJUSTE_NEG_TEXTO} !important; }}
    div[class*="st-key-ajcas_buscar_pos_"] [data-testid="stTextInputRootElement"]:focus-within {{
        border-bottom-color: {AJUSTE_POS_TEXTO} !important; }}
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] input {{
        height: auto !important; padding: 2px 2px 4px 2px !important;
        font-size: 11.5px !important; color: {TEXTO_PRINCIPAL} !important; }}
    div[class*="st-key-ajcas_buscar_"] [data-testid="stTextInputRootElement"] input::placeholder {{
        color: {GRIS_TEXTO_SUAVE} !important; opacity: 1 !important; }}
    /* Scroll propio por columna, con scrollbar invisible hasta el hover.
       No hay forma 100% CSS de mostrarla solo mientras se arrastra
       (necesitaria JS, y st.markdown no lo ejecuta). */
    .ajcas-lista-scroll {{
        max-height: 260px; overflow-y: auto;
        scrollbar-width: thin; scrollbar-color: transparent transparent;
        transition: scrollbar-color .15s ease; }}
    .ajcas-lista-scroll:hover {{
        scrollbar-color: {GRIS_TEXTO_SUAVE} transparent; }}
    .ajcas-lista-scroll::-webkit-scrollbar {{ width: 5px; }}
    .ajcas-lista-scroll::-webkit-scrollbar-track {{ background: transparent; }}
    .ajcas-lista-scroll::-webkit-scrollbar-thumb {{
        background: transparent; border-radius: 999px;
        transition: background-color .15s ease; }}
    .ajcas-lista-scroll:hover::-webkit-scrollbar-thumb {{
        background: {GRIS_TEXTO_SUAVE}; }}

    /* ── SUBIR LA VISTA ───────────────────────────────────────────────
       Medido en la app: el contenido arrancaba en y=148 con el cromo fijo
       de arriba (`nav_franja_rep`) terminando en y=36. De esos 148, 52 son
       el `padding-top` del `stMainBlockContainer` y los otros 96 son
       `row-gap` PURO: el bloque principal tiene `row-gap: 16px` y antes
       del contenido hay SEIS hijos `display:flex` de ALTURA CERO — el rail
       y la nav, que pintan con `position: fixed`. Un hijo de altura cero
       no ocupa alto pero si cobra el gap.

       -96px es exactamente esa suma, asi que la tarjeta queda en y=52: al
       ras del padding del contenedor, 16px debajo de la franja.

       MARGIN Y NO TRANSFORM, y no es estetica. El modo diseno propone
       `transform: translate(...)` porque es lo que puede animar en vivo,
       pero (a) un transform mueve el pixel y deja el hueco, asi que las
       tarjetas de familia no subirian con la cabecera, y (b) un transform
       en un ancestro CAPTURA a sus hijos `fixed` (regla #156, la que
       motivo rayos_x.js) — y esta vista tiene el popover de Filtros
       adentro, que se posiciona fixed. El margin negativo si mueve el
       hueco y no crea contenedor de bloque nuevo.

       Va en la SECCION y no en la tarjeta de cabecera para que suba la
       vista entera; puesto en la cabecera, subiria ella sola y dejaria el
       agujero abajo.

       -108px deja la tarjeta en y=40, a 4px de la franja. Es el PISO: la
       franja es `position: fixed` y opaca, asi que cualquier valor mayor
       mete la tarjeta DEBAJO de ella. Los 96 de la cuenta de arriba son lo
       que sobra por el gap; los 12 extra se los come al `padding-top: 52`
       del contenedor, que existe justo para despejar esa franja.
       Ver arquitectura.md regla #426. */
    div[class*="st-key-aj_sec_cascada"] {{
        margin-top: -108px !important; }}

    /* ── LOS TRES CONTROLES, EN LA FILA DEL TITULO ────────────────────
       Se pidio "3 filtros minimalistas en la misma altura que el titulo
       interno, no afuera", y con eso se fue la tarjeta de cabecera que
       tenia el titulo del reporte, el compartimento de filtros y los KPIs
       (`ajcas_cab`, borrada 2026-09-15). Ahora la tarjeta protagonista ES
       la cabecera.

       Las reglas del trigger y de la lista de cortes las escribe
       `_comun.css_filtros_vista`, scopeadas al prefijo de key de ESTA
       vista -- el Mapa de calor usa las mismas con el suyo. El scope es
       `ajcas_ctrl_` (los tres contenedores propios) y no la tarjeta
       entera: mismo alcance, y asi el helper recibe un solo prefijo. */
    {_CSS_FILTROS}

    /* ── EL NETO, abajo de la zona 2 ──────────────────────────────────
       Hasta el 2026-09-15 era una ficha punteada arriba del riel. Ahora
       vive debajo de los tres controles, y el filete de arriba es lo que
       separa lo que se TOCA de lo que se LEE: son las dos naturalezas que
       comparten la zona. Alineado a la derecha para que su borde coincida
       con el de la tarjeta y no flote en el medio. */
    div[class*="st-key-ajcas_total"] {{
        border-top: 1px solid {GRIS_FONDO};
        margin-top: 5px; padding-top: 7px; }}
    div[class*="st-key-ajcas_total"] p {{ margin: 0 !important; }}

    /* ── MINI-TARJETA DEL RIEL ────────────────────────────────────────
       EL BOTON CUBRE LA TARJETA ENTERA. Es el fix del pestillo de 16x36:
       el contenedor pasa a `relative`, el stElementContainer del boton a
       `static` (asi el absolute ancla en la tarjeta y no en el), y el
       <button> se estira a inset:0 por encima del HTML. Verificado en la
       app: 100 % de la superficie clickeable, el texto se sigue viendo
       debajo. Coste conocido: el texto deja de ser seleccionable.
       Ver arquitectura.md regla #421. */
    div[class*="st-key-ajcas_mini_"] {{
        position: relative !important;
        border: 1px solid {GRIS_BORDE}; border-radius: 12px;
        padding: 9px 11px; margin-bottom: 8px; cursor: pointer;
        background: {BLANCO};
        transition: border-color .12s ease, background .12s ease; }}
    div[class*="st-key-ajcas_mini_"]:hover {{
        border-color: {ACENTO}; background: {LAVANDA_SELECCION}; }}
    div[class*="st-key-ajcas_btnmini_"] {{ position: static !important; }}
    div[class*="st-key-ajcas_btnmini_"] button {{
        position: absolute !important; inset: 0 !important;
        min-height: 0 !important; padding: 0 !important;
        border: none !important; background: transparent !important;
        color: transparent !important; box-shadow: none !important;
        overflow: hidden !important; white-space: nowrap !important;
        z-index: 3 !important; border-radius: 12px !important; }}
    div[class*="st-key-ajcas_btnmini_"] button:hover,
    div[class*="st-key-ajcas_btnmini_"] button:focus {{
        background: transparent !important; color: transparent !important;
        border: none !important; box-shadow: none !important; }}
    div[class*="st-key-ajcas_btnmini_"] button:focus-visible {{
        outline: 2px solid {ACENTO} !important; outline-offset: 1px; }}
    /* LOS DOS BOTONES SE REPARTEN LA TARJETA, sin hueco ni solape: el
       chico se queda con la franja del minigrafico (`_ZONA_GRAF`, que
       sale de las mismas medidas con que se dibuja) y el grande con todo
       lo de arriba. El recorte del grande va condicionado a que el chico
       EXISTA: una familia sin historial no dibuja minigrafico, y ahi el
       grande tiene que seguir cubriendo la tarjeta entera. */
    div[class*="st-key-ajcas_btnmini_g_"] button {{
        top: auto !important; height: {_ZONA_GRAF}px !important; }}
    div[class*="st-key-ajcas_mini_"]:has(
        div[class*="st-key-ajcas_btnmini_g_"])
        div[class*="st-key-ajcas_btnmini_"]:not(
        [class*="st-key-ajcas_btnmini_g_"]) button {{
        bottom: {_ZONA_GRAF}px !important; }}
    div[class*="st-key-ajcas_mini_"] [data-testid="stMarkdownContainer"] p {{
        margin: 0 !important; }}

    /* ── EL PANEL DE DETALLE DE LA MINI ───────────────────────────────
       Se abre con el `:hover` de la TARJETA, no con el suyo: adentro de
       una mini el boton esta por encima con `inset: 0` (#421) y ningun
       hijo recibe el hover. El contenedor si lo recibe, porque el boton
       es su descendiente y `:hover` sube por los ancestros.

       `pointer-events: none` no es un detalle: sin eso el panel se mete
       entre el cursor y el boton, y la mitad de la tarjeta deja de ser
       clickeable justo cuando el usuario ya la tiene apuntada.

       Va a la IZQUIERDA (`right: 100%`) porque el riel es la columna de
       mas a la derecha de la pagina: abierto hacia afuera se saldria de
       la ventana. */
    div[class*="st-key-ajcas_mini_"] .ajcas-detalle {{
        position: absolute; right: calc(100% + 10px); top: -6px;
        min-width: 158px; padding: 9px 11px;
        font-size: 10.5px; text-align: left;
        background: {BLANCO}; border: 1px solid {GRIS_BORDE};
        border-radius: 10px; box-shadow: 0 8px 22px rgba(0,0,0,.12);
        opacity: 0; visibility: hidden; transform: translateX(6px);
        transition: opacity .12s ease, transform .12s ease,
                    visibility .12s ease;
        pointer-events: none; z-index: 20; }}
    /* ABRE SOBRE EL MINIGRAFICO, NO SOBRE LA TARJETA. Se pidio asi, y el
       unico elemento que puede recibir el hover ahi es el boton chico que
       cubre esa zona -- todo lo demas esta debajo de un boton. Como el
       panel es hermano ANTERIOR del boton en el DOM, no hay combinador
       que vaya para atras: lo resuelve `:has()` desde la tarjeta, que el
       repo ya usa en `estilos/_80_cards.py`. Donde `:has()` no exista, el
       panel simplemente no abre; no rompe nada. */
    div[class*="st-key-ajcas_mini_"]:has(
        div[class*="st-key-ajcas_btnmini_g_"] button:hover) .ajcas-detalle {{
        opacity: 1; visibility: visible; transform: none; }}

    /* ── TARJETA PROTAGONISTA ─────────────────────────────────────────
       Blanca como la cabecera y las minis: `var(--bg-card)`, no un
       `#ffffff` suelto (regla #1 — el color sale de la paleta). Sin esto
       quedaba con fondo transparente entre dos superficies blancas.

       MISMO BORDE QUE LAS MINIS, y eso corrige una decision mia. Llevaba
       `2px solid ACENTO` para marcar el foco, contra el `1px solid
       GRIS_BORDE` de las minis: reportado como «la tarjeta protagonista se
       ve con un borde distinto al de la minitarjeta», y era correcto —
       diferian en grosor (2 vs 1), color (acento vs gris) Y radio (12 vs
       10), o sea tres idiomas en la misma fila.

       El acento ahi era redundante: la protagonista ya se distingue por
       medir 4x y tener el drill adentro. El foco no necesita un anillo,
       necesita ser evidente, y lo es. El acento se reserva para el HOVER
       de las minis, que si es una senal que hace falta (esas SI son
       clickeables y hay que decirlo). */
    div[class*="st-key-ajcas_card_"] {{
        background: var(--bg-card) !important;
        border: 1px solid {GRIS_BORDE} !important;
        border-radius: 12px !important;
        padding: 15px 18px 16px 18px !important; }}

    /* LA TARJETA DE CONTROLES, APRETADA. Se pidio bajarla a 160px desde el
       modo diseno; medido, su contenido son 227 y con `height: 160` el
       bloque del neto se DERRAMA 50px fuera (la tarjeta tiene `overflow:
       visible`, asi que no recorta: queda flotando sobre la de abajo).
       227 no era un piso puesto a mano, es lo que mide lo que hay dentro.

       Lo que si se puede es apretar el aire. Los tres controles apilados
       heredaban el `gap` por defecto de Streamlit (16px) y el padding de
       la familia de tarjetas esta pensado para una tarjeta grande.
       Ver arquitectura.md regla #433. */
    div[class*="st-key-ajcas_card_ctrl"] {{
        padding: 11px 14px 12px 14px !important;
        gap: 4px !important; }}

    /* El CUERPO que las contiene es transparente y solo aporta el hueco.
       Mismo idioma que `compras_vap_cuerpo` (#420): las tarjetas son las
       superficies, el cuerpo es el aire entre ellas. */
    div[class*="st-key-ajcas_cuerpo"] {{
        background: transparent !important; border: none !important;
        gap: 12px !important; }}
    div[class*="st-key-ajcas_cuerpo"] > div {{ border: none !important; }}

    /* CADA TARJETA MIDE SU CONTENIDO, y eso REVIERTE lo que esta misma
       regla hacia hasta el 2026-09-15 por la tarde.
       
       Habia un piso `flex: 1 1 auto` sobre las dos de arriba, replicando
       la #145 ("dos tarjetas de la misma fila miden lo mismo") con el
       prefijo propio. Lo puse por iniciativa mia, no a pedido; se saca a
       pedido, con el CSS del modo diseno pegado: `height: 174px` sobre la
       de familia.
       
       Medido: el alto NATURAL de la de familia es 162px y el de la de
       controles 227 -- el piso estiraba la primera 65px de aire. No se
       clava el 174 del preview (12px por encima del contenido, o sea
       vacio al fondo, y se romperia si un nombre de familia envuelve a
       dos renglones): sin piso, cada una pide lo suyo y sigue andando.
       
       El precio, aceptado: la fila queda con un escalon de 65px. */

    </style>"""


def _graf_waterfall_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto=None, col_valorizado=None,
                           col_cantidad=None, df_full=None, col_fecha=None,
                           col_unidad=None):
    """Cascada por familia: una tarjeta por familia, sin franja de cabecera.

    La tarjeta protagonista ES la cabecera: en la fila de su titulo viven
    los tres controles (corte, familia, area). No hay tarjeta de cabecera
    desde el 2026-09-15 -- ver arquitectura.md regla #427.

    `df` llega SIN los chips del reporte y la vista se filtra sola desde
    `df_full`: corte propio, area y familia propias. El Mapa de calor hace
    lo mismo desde el 2026-09-15 y con la misma pieza compartida
    (`_comun.estado_filtros_vista`); los chips de arriba de la pila siguen
    gobernando Distribucion.

    `col_unidad` es la unidad de Kardex por producto (Kg, Und, Lt...) -- se
    usa solo en el texto de las barras del drill; si no se resuelve, la
    barra muestra la cantidad sin sufijo (nunca el generico "und").
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para la cascada.")
        return

    st.markdown(_css(), unsafe_allow_html=True)

    # ── ESTADO PRIMERO, WIDGETS DESPUES ──────────────────────────────────
    # Los tres controles viven en la fila del TITULO de la tarjeta
    # protagonista, y ese titulo es el nombre de la familia con foco -- que
    # sale de aplicar esos mismos filtros. Huevo y gallina. Lo rompe
    # `estado_filtros_vista`, que lee `session_state` sin dibujar nada
    # (ver su docstring: corte sobre `df_full`, areas del corte, familia
    # sembrada con FAMILIAS_DE_ENTRADA).
    _est = estado_filtros_vista(
        df, df_full, col_fecha, col_familia, col_area, col_ajuste_val,
        k_corte=_K_CORTE, k_familia=_K_FAMILIA, k_area=_K_AREA,
        familias=FAMILIAS_DE_ENTRADA, historial=_N_HISTORIAL)
    d = _est["d"]

    agg = d.groupby(grp_col, as_index=False)[col_ajuste_val].sum()
    if not agg.empty:
        agg["_abs"] = agg[col_ajuste_val].abs()
        agg = agg[agg["_abs"] > 0].sort_values("_abs", ascending=False)

    def _controles(cols):
        """Los tres popovers, uno por columna: corte · familia · area.

        Reciben las columnas ya creadas y no las crean ellos porque el
        llamador decide en que zona van: en Streamlit la posicion la da el
        orden en que se CREA el contenedor, no el orden en que se escribe
        en el.
        """
        render_filtros_vista(cols, _est)

    if agg.empty:
        # Sin datos la tarjeta se dibuja IGUAL. Si no, desaparecerian los
        # tres controles y no habria forma de deshacer el filtro que la
        # dejo vacia -- un callejon sin salida.
        with st.container(key="ajcas_cuerpo"):
            # columnas-internas: tarjeta de la familia vs. de controles
            _z1, _z2 = st.columns([0.69, 1])
            with _z1:
                with st.container(border=True, key="ajcas_card_familia"):
                    st.markdown(
                        f"<div style='font-size:16px;font-weight:600;"
                        f"color:{GRIS_TEXTO_SUAVE}'>Sin datos</div>",
                        unsafe_allow_html=True)
                    st.caption("Ninguna familia tiene ajuste con "
                               "estos filtros.")
            with _z2:
                with st.container(border=True, key="ajcas_card_ctrl"):
                    # columnas-internas: los tres filtros, en fila
                    _cf = st.columns(3, gap="small")
                    _controles([c.container(key=k)
                                for c, k in zip(_cf, _K_CTRL)])
        return

    # ── Datos por familia ────────────────────────────────────────────────
    _base_tot = 0.0
    _vv = None
    if col_valorizado and col_valorizado in d.columns:
        _base_tot = float(d[col_valorizado].sum() or 0)
        _vv = d.groupby(grp_col)[col_valorizado].sum()
    _total = float(agg[col_ajuste_val].sum())
    _abs_sum = float(agg["_abs"].sum()) or 1.0

    # El ajuste de cada familia en los ultimos `_N_HISTORIAL` cortes, del
    # mas viejo al elegido. `d_historial` ya viene filtrado igual que `d`
    # (misma area, misma familia): compararlo con otro filtro seria
    # comparar dos cosas distintas. Una familia que falta en un corte no
    # movio nada entonces, que es un 0 y no un "no se" -- de ahi el
    # `fill_value` y el `reindex`, que ademas fija el ORDEN: sin el, las
    # columnas saldrian alfabeticas por clave y el minigrafico dejaria de
    # ser una linea de tiempo.
    _hist = _est["historial_cortes"]
    _d_hist = _est["d_historial"]
    _serie = {}
    if _d_hist is not None and not _d_hist.empty and grp_col in _d_hist.columns:
        _piv = (_d_hist.groupby([grp_col, "_corte_clave"])[col_ajuste_val]
                .sum().unstack(fill_value=0.0)
                .reindex(columns=[_c["clave"] for _c in _hist],
                         fill_value=0.0))
        _serie = {str(_k): [float(_x) for _x in _fila]
                  for _k, _fila in zip(_piv.index, _piv.values)}

    # LA ESCALA ES LA DE HOY, y eso REVIERTE mi primer intento del mismo
    # dia. Habia metido los valores del corte anterior en el maximo, para
    # que la barra de antes no se saliera del semiancho. Medido en la app
    # con datos reales: el maximo saltaba de 6.072 a ~28.500 -- un corte
    # pasado con un faltante enorme-- y con el las barras de HOY quedaban
    # en 1 y 4 pixeles de 135. La barra que hay que poder leer es la de
    # ahora; la de antes es el contexto. Lo que se hace con la que no
    # entra es TOPARLA y que se note (`_barra_cero`), no achicar todo.
    _max_abs = float(agg["_abs"].max()) or 1.0

    _fams = []
    for _i in range(len(agg)):
        _nom = str(agg[grp_col].iloc[_i])
        _v = float(agg[col_ajuste_val].iloc[_i])
        _bse = float(_vv.get(_nom, 0) or 0) if _vv is not None else 0.0
        _ser = _serie.get(_nom)
        _fams.append({
            "cat": _nom, "val": _v, "base": _bse,
            "peso": abs(_v) / _abs_sum * 100,
            "esc": abs(_v) / _max_abs * 50,
            "serie": _ser,
            "cortes": _hist if _ser else None,
            # El chip compara contra el corte anterior, que es la anteultima
            # columna del minigrafico -- el mismo numero, dicho exacto.
            "prev": _ser[-2] if _ser and len(_ser) > 1 else None,
            "tt": (_v / _base_tot * 100) if abs(_base_tot) > 1e-6 else None,
        })

    _nombres = [f["cat"] for f in _fams]
    foco = st.session_state.get(_K_FOCO)
    if foco not in _nombres:
        # Sin foco valido, manda la familia que mas pesa. La vista nunca
        # queda sin protagonista: un riel solo no dice nada.
        foco = _nombres[0]
        st.session_state[_K_FOCO] = foco

    _act = [f for f in _fams if f["cat"] == foco][0]
    _resto = [f for f in _fams if f["cat"] != foco]

    # columnas-internas: protagonista vs. riel de las demás familias
    _c_pro, _c_riel = st.columns([3.2, 1])

    with _c_pro:
        # TRES TARJETAS, no tres zonas de una (2026-09-15, a pedido:
        # primero se pidieron zonas y despues "dividelo en 3 tarjetas").
        # El cuerpo es transparente y solo aporta el hueco de 12px, igual
        # que `compras_vap_cuerpo` (#420).
        #
        #   familia | controles + neto
        #   ------- detalle, a todo el ancho -------
        #
        # El detalle va SOLO y entero: dos listas de 30 productos en media
        # tarjeta no se leen.
        with st.container(key="ajcas_cuerpo"):
            # columnas-internas: tarjeta de la familia vs. de controles
            # PROPORCION, no ancho fijo. Se pidio dos veces por el modo
            # diseno: primero ~510 a 1555px de viewport, despues 363 a
            # ~1330. Un ancho en px seria correcto en la pantalla donde se
            # arrastro y falso en cualquier otra, asi que lo que se guarda
            # es la razon entre las dos columnas.
            #
            # La cuenta de la ultima: a 1330px la fila mide 906 con 16 de
            # hueco, o sea 890 repartibles; 363/890 = 0.408, y una razon
            # x/(x+1) que de 0.408 es x = 0.69. (El 0.67 de la primera
            # pasada salio de medir la fila en un screenshot: daba 921 y
            # son 906, o sea 8px cortos. Medir el DOM, no la imagen.)
            #
            # Y el espacio que suelta la izquierda se lo queda la derecha.
            # El preview del modo diseno mostraba ~80px de hueco muerto
            # entre las dos porque achica SOLO el elemento fijado y no
            # reacomoda a su hermano: su vista previa de un cambio de
            # proporcion siempre miente por ese lado.
            _z1, _z2 = st.columns([0.69, 1])
            with _z1:
                with st.container(border=True, key="ajcas_card_familia"):
                    _peso = ("&lt;1%" if _act["peso"] < 0.5
                             else f"{_act['peso']:.0f}%")
                    st.markdown(
                        f"<div style='display:flex;align-items:baseline;"
                        f"gap:8px;flex-wrap:wrap'>"
                        f"<span style='font-size:16px;font-weight:600;"
                        f"color:{TEXTO_PRINCIPAL};letter-spacing:-.01em'>"
                        f"{_act['cat']}</span>"
                        f"<span style='font-size:10.5px;"
                        f"color:{GRIS_TEXTO_SUAVE}'>"
                        f"{_peso} del ajuste del período</span></div>",
                        unsafe_allow_html=True)
                    _render_zona_familia(_act)
            with _z2:
                with st.container(border=True, key="ajcas_card_ctrl"):
                    # EN FILA, y eso REVIERTE la decision de unas horas
                    # antes. Cuando se apilaron, la tarjeta medía ~260 y
                    # tres popovers de `min-width: 180` se PISABAN (#430).
                    # Ahora mide 528: con el min-width neutralizado entran
                    # tres columnas de ~156 y el texto mas largo ("todas
                    # las areas") pide ~124. Ver regla #434.
                    # columnas-internas: los tres filtros, en fila
                    _cf = st.columns(3, gap="small")
                    _controles([c.container(key=k)
                                for c, k in zip(_cf, _K_CTRL)])
                    _render_total(_total, _base_tot, len(_fams),
                                  len(_est["historial_cortes"]))
            with st.container(border=True, key="ajcas_card_drill"):
                _drill(_act["cat"], d, grp_col, col_ajuste_val, col_producto,
                       col_area, col_cantidad, col_unidad)

    with _c_riel:
        # El neto ya NO vive aca: se mudo a la zona 2. Sin esa ficha las
        # minis suben y la primera queda al ras de la tarjeta grande.
        for _f in _resto:
            _render_mini(_f)


def _render_total(total, base, n_familias, n_cortes=0):
    """ZONA 2, abajo: el neto del período, debajo de los tres controles.

    No es de la familia con foco sino de TODAS -- es el contexto contra el
    que se lee el monto grande de la zona 1. Y por eso son DOS TOTALES
    DISTINTOS en la misma fila: el rotulo "Neto del período" de aca y el
    "% del ajuste del período" de alla son lo unico que los separa. Con
    una sola familia filtrada los dos numeros coinciden, que es cuando la
    etiqueta tiene que trabajar.

    Alineado a la derecha y con un filete arriba que lo despega de los
    controles: arriba se toca, abajo se lee.

    `n_cortes` es la LEYENDA del minigráfico de las minis, y vive acá y no
    en cada minitarjeta por lo mismo que la #238: un rótulo idéntico
    repetido en las seis tarjetas es ruido, y el sitio donde se lee el
    contexto de la vista entera es éste. Tampoco puede ir como `title` del
    minigráfico: el botón de la mini cubre la tarjeta completa (#421), así
    que nada de adentro recibe el hover.
    """
    _col = _tono(total)[0]
    _sig = "+" if total > 0 else "−"
    _pct = ""
    if abs(base) > 1e-6:
        _p = total / base * 100
        _pct = f"{_p:+.1f}% s/ total · "
    with st.container(key="ajcas_total"):
        st.markdown(
            f"<div style='text-align:right'>"
            f"<div style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
            f"text-transform:uppercase;letter-spacing:.07em;"
            f"font-weight:600'>Neto del período</div>"
            f"<div style='font-size:22px;font-weight:700;color:{_col};"
            f"font-variant-numeric:tabular-nums;letter-spacing:-.02em;"
            f"line-height:1.2;margin-top:1px'>"
            f"{_sig}S/ {abs(total):,.0f}</div>"
            f"<div style='font-size:10.5px;color:{GRIS_TEXTO}'>"
            f"{_pct}{n_familias} "
            f"{'familia' if n_familias == 1 else 'familias'}</div>"
            + (f"<div style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
               f"margin-top:3px'>minigráfico = últimos {n_cortes} cortes, "
               f"el último es éste</div>"
               if n_cortes > 1 else "")
            + "</div>",
            unsafe_allow_html=True)


def _render_mini(f):
    """Una familia del riel: nombre, monto, diferencia y barras del cero.

    El boton va ADENTRO del mismo contenedor que el HTML y el CSS lo estira
    a toda la tarjeta (ver `_css`). Label de un espacio: el texto se
    esconde con `color: transparent` porque un label vacio deja el boton
    sin caja que estirar.

    La comparacion contra el corte anterior (2026-09-15) son dos piezas
    que dicen lo mismo de dos maneras y por eso van juntas: el chip con la
    diferencia en % a la derecha del monto -- el numero exacto-- y el
    minigrafico de los ultimos cortes al pie, que es la forma. Con un solo
    corte en el historial las dos desaparecen y la minitarjeta vuelve a
    ser la de antes.
    """
    _col = _tono(f["val"])[0]
    _sig = "+" if f["val"] > 0 else "−"
    _chip = _delta_corte(f["val"], f.get("prev"))
    with st.container(key=f"ajcas_mini_{_slug(f['cat'])}"):
        st.markdown(
            f"<div style='font-size:11px;font-weight:600;"
            f"color:{GRIS_TEXTO_MEDIO};white-space:nowrap;overflow:hidden;"
            f"text-overflow:ellipsis'>{f['cat']}</div>"
            f"<div style='display:flex;align-items:baseline;gap:6px;"
            f"justify-content:space-between;margin-top:1px'>"
            f"<span style='font-size:14px;font-weight:600;color:{_col};"
            f"font-variant-numeric:tabular-nums;letter-spacing:-.02em;"
            # EL MONTO NO SE ENCOGE Y EL CHIP SI. Sin esto, un chip largo
            # ("pasó a sobrar") le come el ancho al monto y "+S/ 1,489"
            # se parte en dos renglones -- visto al angostar la mini.
            f"white-space:nowrap;flex:0 0 auto'>"
            f"{_sig}S/ {abs(f['val']):,.0f}</span>"
            + (f"<span style='font-size:9.5px;font-weight:600;"
               f"color:{GRIS_TEXTO};white-space:nowrap;min-width:0;"
               f"overflow:hidden;text-overflow:ellipsis'>{_chip}</span>"
               if _chip else "")
            + f"</div>"
            f"{_barra_cero(f['val'], f['esc'])}"
            f"{_minigraf_cortes(f.get('serie'), f.get('cortes'))}"
            f"{_detalle_cortes(f.get('serie'), f.get('cortes'))}",
            unsafe_allow_html=True)
        # EL LABEL ES EL NOMBRE ACCESIBLE, y por eso no es " ".
        # El boton se esconde con `color: transparent` (ver `_css`), no
        # vaciandolo: medido, con label " " y `help=` el nombre accesible
        # salia VACIO -- el boton recibe foco con Tab y un lector de
        # pantalla anunciaba "boton" a secas. `help=` no lo arregla: monta
        # un tooltip aparte (dos capas de DOM) que ademas, con el overlay
        # cubriendo la tarjeta entera, aparecia al pasar el mouse por
        # cualquier punto de ella. Ver arquitectura.md regla #428.
        if st.button(f"Ver el detalle de {f['cat']}",
                     key=f"ajcas_btnmini_{_slug(f['cat'])}"):
            st.session_state[_K_FOCO] = f["cat"]
            st.rerun()
        # SEGUNDO BOTON, sobre la zona del minigrafico, y hace lo MISMO que
        # el de arriba. No esta para clickear distinto: esta para que esa
        # zona tenga un elemento propio al que preguntarle `:hover`.
        #
        # Se pidio que el panel de detalle abriera solo sobre el grafico y
        # no en toda la tarjeta. El camino corto --recortar el boton
        # grande y dejar que el hover lo reciba el div del grafico-- deja
        # una franja de 63px que se ilumina y no responde al clic, que es
        # exactamente el bug de la #421. Con dos botones la tarjeta sigue
        # siendo clickeable entera y el hover queda acotado. Ver #439.
        if f.get("serie") and st.button(
                f"Ver el detalle de {f['cat']} — últimos cortes",
                key=f"ajcas_btnmini_g_{_slug(f['cat'])}"):
            st.session_state[_K_FOCO] = f["cat"]
            st.rerun()


def _render_zona_familia(f):
    """ZONA 1: el monto grande de la familia con foco, su barra y su pie.

    NO dibuja el nombre ni el drill. El nombre lo pone el llamador (abre la
    zona) y el drill es la ZONA 3, que va a todo el ancho de la tarjeta y
    por lo tanto fuera de esta columna.

    Lleva el MISMO chip y el MISMO minigrafico que las minis desde el
    2026-09-15 (a pedido). No es simetria porque si: sin esto, hacer clic
    en una mini para ver el detalle de una familia HACIA DESAPARECER su
    comparacion -- la informacion se iba justo cuando el usuario pedia
    mas. Aca el tooltip nativo de cada columna si funciona, porque esta
    tarjeta no tiene el boton-overlay que tapa a las minis (#421).
    """
    _col = _tono(f["val"])[0]
    _sig = "+" if f["val"] > 0 else "−"
    _chip = _delta_corte(f["val"], f.get("prev"))
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:10px;"
        f"flex-wrap:wrap;margin-top:4px'>"
        f"<span style='font-size:36px;font-weight:600;color:{_col};"
        f"font-variant-numeric:tabular-nums;letter-spacing:-.03em;"
        f"line-height:1.15'>{_sig}S/ {abs(f['val']):,.0f}</span>"
        + (f"<span style='font-size:11px;font-weight:600;"
           f"color:{GRIS_TEXTO};white-space:nowrap'>{_chip} "
           f"<span style='font-weight:400;color:{GRIS_TEXTO_SUAVE}'>"
           f"vs. corte anterior</span></span>" if _chip else "")
        + f"</div>"
        f"{_barra_cero(f['val'], f['esc'])}"
        f"{_minigraf_cortes(f.get('serie'), f.get('cortes'))}",
        unsafe_allow_html=True)

    _pie = []
    if f["tt"] is not None:
        _pie.append(f"<span style='color:{GRIS_TEXTO}'>"
                    f"{f['tt']:+.1f}% del inventario del período</span>")
    _fr = _frase_ratio(f["val"], f["base"])
    if _fr:
        _pie.append(f"<span style='color:{_col};font-weight:500'>{_fr}</span>")
    if _pie:
        st.markdown(
            f"<div style='font-size:12px;margin-top:8px;display:flex;"
            f"gap:14px;flex-wrap:wrap'>{' · '.join(_pie)}</div>",
            unsafe_allow_html=True)


def _drill(focus_cat, d, grp_col, col_ajuste_val, col_producto, col_area,
           col_cantidad, col_unidad):
    """Faltantes y sobrantes de la familia con foco, en dos columnas."""
    _det = d[d[grp_col].astype(str) == focus_cat]
    dim = col_producto or (col_area if grp_col != col_area else None)
    if not dim or dim not in _det.columns:
        return

    _has_cant = bool(col_cantidad and col_cantidad in _det.columns)
    _has_area = bool(col_area and col_area in _det.columns
                     and col_area != dim and col_area != grp_col)
    _has_um = bool(col_unidad and col_unidad in _det.columns
                   and col_unidad != dim)
    _agg_map = {col_ajuste_val: "sum"}
    if _has_cant:
        _agg_map[col_cantidad] = "sum"
    if _has_um:
        _agg_map[col_unidad] = "first"
    _agg_dim = _det.groupby(dim, as_index=False).agg(_agg_map)
    if _has_area:
        # "first" mostraba el área de la primera fila del producto, sin
        # importar si ahí el ajuste era 0 — con varias áreas por producto
        # etiquetaba con la que no tenía movimiento. Se toma el área de la
        # fila con mayor |ajuste|, que es la que explica el monto mostrado.
        _area_top = (_det[[dim, col_area, col_ajuste_val]]
                     .assign(_abs=lambda x: x[col_ajuste_val].abs())
                     .sort_values("_abs", ascending=False)
                     .drop_duplicates(subset=[dim])[[dim, col_area]])
        _agg_dim = _agg_dim.merge(_area_top, on=dim, how="left")

    if _agg_dim.empty or _agg_dim[col_ajuste_val].abs().sum() == 0:
        return

    def _filas_html(_df, color_bar):
        """Mini barras de progreso (riel + relleno), no un gráfico Plotly.
        El relleno normaliza contra el mayor |ajuste| de ESTE sub-listado
        (no del total de la familia)."""
        _max_abs = float(_df[col_ajuste_val].abs().max()) or 1.0
        _out = []
        for _, _r in _df.iterrows():
            _nom = str(_r[dim])
            if len(_nom) > 32:
                _nom = _nom[:31] + "…"
            _sub = (f"<div style='font-size:9.5px;color:{GRIS_TEXTO_SUAVE};"
                    f"white-space:nowrap;overflow:hidden;"
                    f"text-overflow:ellipsis'>{_r[col_area]}</div>"
                    if _has_area else "")
            _pct = max(abs(float(_r[col_ajuste_val])) / _max_abs * 100, 3)
            _t = f"S/ {_r[col_ajuste_val]:,.0f}"
            if _has_cant:
                _t += f" · {_r[col_cantidad]:,.1f}"
                _um = str(_r[col_unidad]).strip() if _has_um else ""
                if _um and _um.lower() != "nan":
                    _t += f" {_um}"
            _tcol = _tono(float(_r[col_ajuste_val]))[0]
            _out.append(
                f"<div style='display:flex;align-items:center;gap:8px;"
                f"padding:3px 0'>"
                f"<div style='width:38%;min-width:0;flex-shrink:0;"
                f"overflow:hidden'>"
                f"<div style='font-size:11.5px;color:{TEXTO_PRINCIPAL};"
                f"white-space:nowrap;overflow:hidden;"
                f"text-overflow:ellipsis'>{_nom}</div>{_sub}</div>"
                f"<div style='flex:1;position:relative;height:16px;"
                f"min-width:0'>"
                f"<div style='position:absolute;left:0;right:0;top:50%;"
                f"transform:translateY(-50%);height:7px;"
                f"background:{GRIS_FONDO};border-radius:999px'></div>"
                f"<div style='position:absolute;left:0;width:{_pct:.1f}%;"
                f"top:50%;transform:translateY(-50%);height:7px;"
                f"background:{color_bar};border-radius:999px'></div></div>"
                f"<div style='flex-shrink:0;text-align:right;font-size:11px;"
                f"font-weight:600;color:{_tcol};"
                f"font-variant-numeric:tabular-nums;white-space:nowrap'>"
                f"{_t}</div></div>")
        return "".join(_out)

    def _buscador(placeholder, key):
        """Filtra _agg_dim ANTES del top _TOPN_DRILL, no la lista ya
        recortada -- si no, un producto fuera del top actual no aparecería
        nunca por más que calzara con la búsqueda."""
        return st.text_input(placeholder, key=key, placeholder=placeholder,
                             label_visibility="collapsed").strip().lower()

    _pa, _pb = st.columns(2)  # columnas-internas: faltantes vs. sobrantes
    with _pa:
        _q = _buscador("Buscar en faltantes…",
                       f"ajcas_buscar_neg_{_slug(focus_cat)}")
        _pool = _agg_dim[_agg_dim[col_ajuste_val] < 0]
        if _q:
            _pool = _pool[_pool[dim].astype(str).str.lower()
                          .str.contains(_q, regex=False)]
        # ascending=True: el más negativo primero en el DataFrame -> primero
        # en el HTML -> arriba de la lista.
        _neg = (_pool.nsmallest(_TOPN_DRILL, col_ajuste_val)
                .sort_values(col_ajuste_val, ascending=True))
        if _neg.empty:
            st.caption("Sin coincidencias." if _q
                       else "Sin faltantes en esta familia.")
        else:
            st.markdown(f"<div class='ajcas-lista-scroll'>"
                        f"{_filas_html(_neg, AJUSTE_NEG)}</div>",
                        unsafe_allow_html=True)
    with _pb:
        _q = _buscador("Buscar en sobrantes…",
                       f"ajcas_buscar_pos_{_slug(focus_cat)}")
        _pool = _agg_dim[_agg_dim[col_ajuste_val] > 0]
        if _q:
            _pool = _pool[_pool[dim].astype(str).str.lower()
                          .str.contains(_q, regex=False)]
        _pos = (_pool.nlargest(_TOPN_DRILL, col_ajuste_val)
                .sort_values(col_ajuste_val, ascending=False))
        if _pos.empty:
            st.caption("Sin coincidencias." if _q
                       else "Sin sobrantes en esta familia.")
        else:
            st.markdown(f"<div class='ajcas-lista-scroll'>"
                        f"{_filas_html(_pos, AJUSTE_POS)}</div>",
                        unsafe_allow_html=True)
