"""estilos._40_ajuste_franja - Franja superior "cristal esmerilado" (todos
los reportes) y los chips de filtro que viven en ella (Area / Familia /
Ajuste / lo que aplique por reporte).

Extraido de estilos.py (lineas 898-1083 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.

La franja fue transparente por DEFECTO entre 2026-08-04 y 2026-08-06 (antes
de eso solo lo era en Compras/Ajuste via overrides :has() — ver
arquitectura.md regla #16 y el commit que generalizo esto). Se cambio a
"cristal esmerilado" (blanco translucido + backdrop-filter: blur) el
2026-08-06: fecha_ajuste_pill y chips_ajuste_tabla son position:fixed SIN
fondo propio, asi que al hacer scroll quedaban flotando sobre lo que sea
que hubiera debajo (reportado con capturas — se veian "en el aire"). El
blur no necesita JS: al ser la franja position:fixed, el navegador
desenfoca en cada frame lo que este compuesto detras. Fallback en
navegadores sin backdrop-filter: el rgba(255,255,255,.62) de base ya deja
una banda translucida legible, sin blur pero sin romperse. Ver
arquitectura.md regla #17.

Compras tiene su PROPIO override adicional en estilos/_20_compras_rail.py
(achica la franja a 34px) porque ya tiene el rail derecho; el resto de
reportes usa --cab-altura (50px) tal cual. Ese override solo toca height —
el fondo lo hereda de la regla base de aca abajo, asi que Compras recibe
el cristal esmerilado sin duplicar nada.

2026-08-06, 2da vuelta (mismo dia): el cristal esmerilado gusto, pero era
de borde a borde (left:90px a right:0) y dejaba dos zonas SIEMPRE vacias
con fondo blanco encima — antes del pill de fecha (el titulo que viviria
ahi esta oculto por pedido) y despues del cluster de chips (que en
desktop vive centrado, no pegado al borde derecho). Paso de "franja" a
"tarjeta que cuelga del borde superior" con left/right aproximados
(centrado con chips_ajuste_tabla via calc(50vw - 300px)).

2026-08-06, 3ra vuelta (mismo dia): el aproximado no bastaba — se pidio
alinear la tarjeta con el CONTENEDOR DEL GRAFICO (.st-key-ajuste_graf_
card_izq_<reporte>), no con el cluster de chips. En vez de adivinar otro
numero, se midio en vivo (preview local, getBoundingClientRect +
getComputedStyle) el borde real de esa tarjeta en Compras y Ventas, en
2 anchos de viewport distintos: siempre left=170px (=90px rail + 80px,
el padding-left DEFAULT de Streamlit para .block-container — no es un
valor que este codigo fije a mano) y siempre right~163px (=153px de
padding-right, el mismo que reserva el rail de _20_compras_rail.py:41,
+ ~10px de margen exterior de Streamlit). Los dos son CONSTANTES fijas,
no dependen del viewport — por eso ahora es left:170px / right:163px en
vez de un calc(). Ver el comentario en el bloque CSS de mas abajo.

2026-08-07, 4ta vuelta: Compras tenia su propia franja de 34px (contra
los 50px del resto) para que fecha_ajuste_pill/chips_ajuste_tabla no
asomaran por el borde inferior (ver el commit del fix de overflow). Gusto
mas que el default de 50px, asi que se universalizo: los 8 reportes usan
34px en desktop (>=901px) ahora, y el override propio de Compras en
_20_compras_rail.py se elimino por quedar identico al default. Ver el
comentario junto al @media(min-width:901px) del bloque CSS de mas abajo
para el detalle (por que 34px va fijo y no se toco --cab-altura).

2026-08-09, 5ta vuelta: la tarjeta colgante volvio a ser BARRA de borde a
borde, ahora con cara propia. El cristal esmerilado (blanco al 62% sobre
un canvas blanco) era casi invisible — reportado con captura. Tres
cambios que van juntos:
  - left:90px / right:0 (antes 170/163): la barra ya no se alinea con la
    tarjeta del grafico, arranca donde termina el nav-rail izquierdo y
    llega al borde de la ventana. Es un cambio de CRITERIO, no un ajuste
    de pixeles: si vuelve a alinearse con la tarjeta hay que restaurar
    los dos numeros medidos de la 3ra vuelta (siguen documentados arriba).
  - fondo --accent-tint al 88% + border-bottom de 2px --border-lavender,
    sin borde en los otros 3 lados y sin border-radius.
  - 40px de alto en desktop (antes 34px), con top:6px en los elementos
    fijos que viven dentro (_50_fecha.py).
El CONTENIDO tambien se reagrupo en la misma vuelta: fecha y chips ya no
estan en extremos opuestos (fecha a la izquierda + chips centrados), van
pegados a la izquierda uno tras otro. Ver _50_fecha.py.
"""

CSS = """    /* =================================================================== */
    /* FILA SUPERIOR DE AJUSTE DE INVENTARIO                                */
    /* =================================================================== */
    /* FRANJA "CRISTAL ESMERILADO" — alineada con el CONTENEDOR DEL GRÁFICO  */
    /* (.st-key-ajuste_graf_card_izq_<reporte>), no con el rail ni con un    */
    /* centrado aproximado. left:170px / right:163px son el borde REAL de   */
    /* esa tarjeta, medido en vivo (preview local, getBoundingClientRect +  */
    /* getComputedStyle) en Compras y Ventas, en 2 anchos de viewport:       */
    /*   left  = 170px = 90px del rail + 80px de padding-left DEFAULT de    */
    /*           Streamlit en .block-container (Streamlit lo pone solo,     */
    /*           este código no lo fija — si Streamlit cambia ese default   */
    /*           en una actualización, hay que volver a medir).             */
    /*   right = 163px = 153px de padding-right (la misma reserva del rail  */
    /*           de compras_tabs_row, ver _20_compras_rail.py:41) + ~10px   */
    /*           de margen exterior de Streamlit.                           */
    /* Las esquinas de abajo se redondean (cuelga del borde superior, no    */
    /* border-radius arriba). Mobile define su PROPIO left/right (ver       */
    /* _99_movil.py): ahí no hay rail izquierdo ni tarjeta con la que       */
    /* alinearse de la misma forma. Ver docstring del módulo y              */
    /* arquitectura.md #17.                                                 */
    .st-key-fila_ajuste_top {
        position: sticky !important;
        top: var(--cab-nivel1-top) !important;
        z-index: 20 !important;
        margin-bottom: 0 !important;
        padding-top: 7px !important;
        padding-bottom: 0 !important;
        margin-top: calc(-1 * var(--cab-offset-contenido)) !important;
    }
    /* ── La banda le cede su columna al RAIL (2026-08-19) ──────────────
       Hasta hoy iba de borde a borde (left:0) y no chocaba con nada porque
       el rail arrancaba 66px más abajo, ya pasada la banda. Al subir el rail
       a la altura de los controles (_20_compras_rail.py) esa banda le
       cruzaría por detrás: el rail es una tarjeta blanca con borde, y se
       vería un rectángulo montado sobre la barra.
       Sólo se recorta donde el rail EXISTE (`:has`), que es el mismo
       criterio que usa la reserva de ancho: en Ventas / Inventario /
       Movimientos no hay rail y la banda sigue tocando los dos bordes.
       El `left` es la misma reserva que usa el contenido, así que la banda
       arranca donde arrancan la franja y las tarjetas — una sola línea
       izquierda para las tres capas (regla #137) — y sigue al rail cuando
       se pliega. */
    :root:has(.st-key-compras_tabs_row) .st-key-fila_ajuste_top::before {
        left: var(--rail-der-res) !important;
        /* Y el lado DERECHO cierra donde cierran las tarjetas (2026-08-25,
           a pedido). Venía de `right: 0`, o sea que la banda blanca se
           estiraba 90px más allá del contenido hasta el filo de la ventana
           y la franja se leía más ancha que todo lo que hay debajo.

           Los 90px son el margen real del contenido, medido: 80px es el
           `padding-right` por DEFECTO del block-container de Streamlit y
           10px lo que ese contenedor no llega a ocupar del viewport.
           Verificado a 1280 y a 1500 de ancho — da 90 en los dos, o sea que
           no depende del viewport y se puede anclar. Si algún día Streamlit
           cambia ese padding, este número lo sigue: se mide con
           `innerWidth - tarjeta.getBoundingClientRect().right`. */
        right: 90px !important;
    }

    .st-key-fila_ajuste_top::before {
        content: "" !important;
        /* 2026-08-18: top:0 -> var(--nav-top-alto). La franja ya no toca el
           borde de la ventana: encima vive la barra de navegación superior
           (navegacion.py). En móvil la variable vale 0 y la franja vuelve
           sola al tope, que es donde tiene que estar (allá la navegación
           está abajo). */
        position: fixed !important;
        /* 2026-08-25: de `var(--nav-top-alto)` a 0. La franja paso a tener
           DOS filas —titulo+filtros arriba, vistas abajo (`navegacion.py`)—
           y esta banda solo cubria la de abajo: la de arriba quedaba sin
           fondo y al scrollear se veia el contenido pasar POR DETRAS del
           titulo y los chips. */
        /* 2026-08-31: 0 -> la franja de reportes, que va por encima. */
        top: var(--franja-rep-alto) !important;
        bottom: auto !important;
        /* 2026-08-09: de tarjeta colgante (left:170/right:163, alineada con
           la tarjeta del gráfico) a BARRA de borde a borde. left:90px = el
           ancho del nav-rail izquierdo, así que la barra arranca justo donde
           termina el rail; right:0 llega al borde de la ventana. No choca
           con el rail DERECHO (compras_tabs_row) porque ese arranca en
           top:60px (_20_compras_rail.py:19) y la barra mide 40px. */
        /* 2026-08-12, 6ta vuelta: 90px -> 0. El fondo se extiende hasta el
           borde real de la ventana (queda tapado por el rail en su propio
           ancho, que pinta encima con z-index mayor) para que no quede un
           filo sin pintar a la izquierda del rail en ningún escenario de
           pintado. El control de fecha NO se movió — sigue anclado por su
           propio position:fixed en _50_fecha.py, ajeno a este left. */
        left: 0 !important;
        right: 0 !important;
        /* Las dos filas: la de vistas (`--nav-top-alto`) mas la banda de
           siempre (`--cab-altura`). Derivado, no un 90 suelto: si cualquiera
           de las dos cambia de alto, la banda las sigue. */
        height: calc(var(--nav-top-alto) + var(--cab-altura)) !important;
        border-radius: 0 !important;   /* toca los dos bordes: sin esquinas */
        /* 2026-08-15: de tinte lavanda a blanco --bg-card (mismo fondo que
           las tarjetas de gráfico), a pedido — el lavanda se leía como una
           franja de color aparte en vez de una superficie de la misma
           familia que el resto de la UI. El blur sigue haciendo falta
           porque la barra es fixed y el contenido pasa POR DEBAJO al
           scrollear. */
        /* OPACA Y DEL COLOR DEL LIENZO (2026-08-25, a pedido).
           Dos cambios en uno, y los dos importan:

           · OPACA. Estuvo al 88% con `color-mix` — "cristal esmerilado" —,
             y ese 12% dejaba ver la tabla y el grafico moviendose por
             detras del titulo y los chips al scrollear.
           · `--bg-primary` (el lienzo) y no `--bg-card` (blanco). Con
             blanco la franja se leia como una TARJETA mas, del mismo color
             que las de abajo; con el color del lienzo se lee como lo que
             es: fondo, no contenido. */
        background: var(--bg-primary) !important;
        /* Sin `backdrop-filter`: con el fondo ya opaco no se ve nada a
           traves, asi que el blur no aportaba nada y obligaba al navegador
           a componer esa capa aparte en cada scroll. Estaba puesto cuando
           la banda era translucida (ver arriba). */
        border: none !important;
        border-bottom: 2px solid var(--border-lavender) !important;
        z-index: 0 !important;
    }
    /* 2026-08-07: 34px (en vez de var(--cab-altura)=50px) para los 8
       reportes en desktop — Compras lo estrenó (necesitaba una franja más
       baja por su rail derecho), gustó más así, y se universalizó. Fijo en
       px y NO tocando la variable --cab-altura a propósito: esa variable
       también alimenta el pill "tab" de la franja 769-900px en
       _50_fecha.py (calc(var(--cab-altura) - 8px)), que no se tocó y sigue
       pensado para 50px — cambiar la variable en vez de este valor puntual
       lo hubiera roto de rebote. Acoplado con el top:3px de
       fecha_ajuste_pill/chips_ajuste_tabla en _50_fecha.py — no cambiar
       uno sin el otro. El override propio de Compras en
       _20_compras_rail.py se sacó porque ahora es idéntico al default.
       Ver arquitectura.md regla #17.
       2026-08-09: 34px -> 40px -> 46px. Con la barra tintada (ver el
       bloque de arriba) los 34px quedaban apretados: el tinte necesita
       aire arriba y abajo de los chips de 28px para leerse como superficie
       y no como subrayado.
       Los 40px duraron una pasada: daban 6px arriba pero solo 4px abajo,
       y se veia "metido a la fuerza" contra la linea inferior. El error
       fue calcular el top como (40 - 28) / 2 = 6 OLVIDANDO que el ::before
       es border-box, asi que el border-bottom de 2px se come alto por
       dentro: el aire de abajo es (alto - borde - 28 - top), no (alto -
       28 - top). Con 46px y top:8px queda 8px por lado, simetrico.
       LA FORMULA, para la proxima vez que se toque:
           top = (alto - borde_inferior - alto_del_control) / 2
       Los dos numeros siguen acoplados con el top:8px de
       fecha_ajuste_pill/chips_ajuste_tabla en _50_fecha.py. */
    @media (min-width: 901px) {
        .st-key-fila_ajuste_top::before {
            /* 46 era el alto de UNA fila. Desde que la franja tiene dos
               (titulo+filtros arriba, vistas abajo) hay que sumar la de
               vistas, o la de arriba queda sin fondo — que es como se
               descubrio: el contenido se veia pasar por detras del titulo.
               Este bloque pisaba al `calc()` de la regla base; se mantiene
               porque su 46 es una medida propia (ver la formula de arriba),
               no una copia. */
            /* Hasta el BORDE INFERIOR de la franja de vistas, derivado de
               su propio anclaje: ella vive en `--nav-top-alto + 8px` y mide
               `--nav-top-alto` (`navegacion.py`), asi que su base es la
               suma. Con `46 + --nav-top-alto` quedaba 2px corta y se colaba
               una linea de contenido bajo las pestanas (medido). */
            /* 2026-08-31: la franja de vistas se mudó a
               `var(--franja-rep-alto)`, así que su base —y el fondo que la
               respalda— es ahora esa suma. Misma derivación que antes, otro
               anclaje. Sin esto la banda seguía llegando a y=126 y su borde
               lavanda de 2px quedaba flotando 46px por debajo de la franja,
               solo, sin nada que separar (medido). */
            height: calc(var(--franja-rep-alto)
                         + var(--nav-top-alto)) !important;
            /* Y DEJA DE PINTAR (2026-08-31). Su fondo y su borde existían
               para respaldar las filas de la cabecera; hoy esas filas son
               dos franjas opacas y de borde a borde que se pintan solas.
               Con el `z-index` de su contenedor subido acá abajo, un fondo
               acá taparía a la franja de vistas — que es justo lo que la
               banda venía a respaldar. La caja se deja (algo la mide); lo
               que se apaga es la tinta. */
            background: transparent !important;
            border-bottom: none !important;
        }
        /* EL CONTENEDOR SUBE POR ENCIMA DE LAS FRANJAS.
           Es `position: sticky` con `z-index: 20`, y eso CREA UN CONTEXTO
           DE APILAMIENTO: todo lo que vive adentro queda topado en 20, por
           alto que sea su propio z-index. El pill de fecha se puso en
           1000000 para pasarle a la franja de vistas (999999) y seguía
           invisible — verificado con `elementFromPoint`, que devolvía el
           `nav_rail`. El z-index de un hijo no vale nada fuera del contexto
           de su padre; hay que levantar el contexto entero.
           Va acá y no en la regla base porque abajo de 901px las franjas no
           se apilan así y la banda todavía pinta. */
        .st-key-fila_ajuste_top {
            z-index: 1000000 !important;
            /* Y TRANSPARENTE AL PUNTERO. Subirlo por encima de las franjas
               resolvió el pintado pero le regaló los CLICS: su caja mide
               323..1190 x 48..166 (medido en Ajuste) y tapa la fila de
               vistas entera — los siete botones dejaron de responder,
               verificado uno por uno con `elementFromPoint`. El contenedor
               no dibuja nada propio (su banda quedó transparente acá
               arriba), así que no necesita recibir eventos; los hijos se
               los devuelven. */
            pointer-events: none !important;
        }
        .st-key-fila_ajuste_top > * {
            pointer-events: auto !important;
        }
    }
    .st-key-fila_ajuste_top > * {
        position: relative !important;
        z-index: 1 !important;
    }
    .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 8px !important;
    }
    .st-key-fila_ajuste_top [data-testid="stColumn"],
    .st-key-fila_ajuste_top [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
    }

    /* ================================================================== */
    /* RECETAS (Receta Base / Receta Venta) — sin franja, sin reserva      */
    /* ================================================================== */
    /* Los dos son catálogo (data.py: "fecha": None) y el título de la     */
    /* franja está oculto por pedido (app.py) — no queda nada adentro,     */
    /* solo la banda decorativa. A pedido (2026-08-24) se oculta ENTERA    */
    /* (:has() apaga el contenedor y con él su ::before, sin tocar Python) */
    /* y en desktop se recorta el padding-top que el contenido reserva     */
    /* para ella.                                                          */
    /* Ese padding-top vive en navegacion.py y es GLOBAL — los 8 reportes  */
    /* comparten --cab-offset-contenido, y test_graficos.py compara su     */
    /* valor literal contra graficos/alturas.py::_CAB_OFFSET. Por eso el   */
    /* recorte va ACÁ, scopeado con el mismo marker `app_reporte_<slug>`   */
    /* que ya usa Compras (_20_compras_rail.py), y pisa el padding-top     */
    /* directo — nunca la variable — para no desincronizar ese contrato    */
    /* en los reportes que sí usan la franja.                              */
    /* Solo desktop (min-width acá abajo): en móvil `_99_movil.py` ya deja */
    /* la franja en 0 de flujo para TODOS los reportes, y los 108px de     */
    /* padding-top de navegacion.py ahí reservan para otros fijos (pill de */
    /* fecha, banda) que comparten presupuesto — recortarlos a ciegas, sin */
    /* poder medir reporte por reporte, es más riesgo que la ganancia.     */
    [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_base) .st-key-fila_ajuste_top,
    [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_venta) .st-key-fila_ajuste_top {
        display: none !important;
    }
    @media (min-width: 769px) {
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_base) [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_base) .stMainBlockContainer,
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_base) .block-container,
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_venta) [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_venta) .stMainBlockContainer,
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_receta_venta) .block-container {
            /* --nav-top-alto (40px) despeja la barra de navegación fija;
               +8px es el mismo respiro que usan _50_fecha.py/_40_ajuste_
               franja.py para lo que ancla contra esa variable. */
            padding-top: calc(var(--nav-top-alto) + 8px) !important;
        }
    }

    /* ================================================================== */
    /* CHIPS DE FILTRO EN LA FRANJA BLANCA — Área / Familia / Ajuste /     */
    /* Ajuste valor.  Nivel 2, a la derecha del selector de vista.         */
    /* ================================================================== */
    /* Filtros Familia / Subfamilia en el NIVEL 1: pegados a la IZQUIERDA,
       alineados con el borde izquierdo de la TARJETA. Son los ~64px de
       padding-left que el block-container se pone solo.
       2026-08-18: 154 -> 64. Los 154 llevaban dentro los 90px que el rail
       izquierdo reservaba en ancho; ese rail es hoy la franja superior y no
       reserva nada, así que TODOS los `left` de la franja bajaron 90px
       (aquí y en _50_fecha.py). El `top` se corre --nav-top-alto por la
       misma razón, pero al revés: lo que perdió en ancho lo ganó en alto. */
    /* El COMPARTIMENTO de filtros. La geometria de verdad vive en
       `_50_fecha.py`, que repite el selector con la clase duplicada y va
       despues en `_SECCIONES`: es la que gana. Esta se deja alineada con
       aquella —no contradiciendola— para que leer una sola no engane. */
    .st-key-chips_ajuste_tabla {
        position: fixed !important;
        /* Sigue a su franja, que subió a tocar la de reportes. */
        top: var(--franja-rep-alto) !important;
        height: var(--nav-top-alto) !important;
        left: auto !important;
        right: 0 !important;   /* == el borde de la franja, hoy el de la ventana */
        width: auto !important;
        z-index: 1000000 !important;
        margin: 0 !important;
        padding: 0 16px !important;
        display: flex !important;
        align-items: center !important;
        border-left: 1px solid var(--border) !important;
        background: var(--bg-card) !important;
        border-radius: 0 10px 10px 0 !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] {
        gap: 8px !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stColumn"],
    .st-key-chips_ajuste_tabla [data-testid="column"] {
        width: auto !important;
        flex: 0 1 auto !important;
        min-width: 0 !important;
    }
    /* Opción A: cuadrado lavanda con icono + badge morado. Ancho automático
       para que el badge del count quepa sin recortar; esquinas 4px. */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        min-width: 0 !important;
        width: auto !important;
        min-height: 28px !important;
        height: 28px !important;
        padding: 3px 10px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        background: var(--accent-tint) !important;
        border: 1px solid var(--border-lavender) !important;
        border-radius: 4px !important;
        color: var(--accent-deep) !important;
        overflow: hidden !important;
        gap: 6px !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button p {
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
        font-size: 15px !important;
    }
    /* Badge del count (Streamlit :violet-badge[N] dentro del label) */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button [data-testid="stBadge"] {
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 3px !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        padding: 1px 6px !important;
        line-height: 1.4 !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button:hover {
        background: var(--accent-light) !important;
        border-color: var(--accent) !important;
    }

    /* ── PANEL DEL COMPARTIMENTO (2026-08-31) ──────────────────────────
       Los N filtros dejaron de ser N popovers en fila y viven adentro de
       UNO solo, apilados. Streamlit no anida popovers, asi que cada uno es
       una seccion plana: rotulo + pills (`graficos/base.py::filtro_pills`).

       El panel se renderiza en un PORTAL, fuera del contenedor keyed, asi
       que no se lo puede alcanzar por `.st-key-chips_ajuste_tabla`. Se
       scopea por lo unico que solo este panel tiene adentro: el rotulo.
       Mismo recurso que usa el panel de fecha con `:has(.st-key-fecha_panel)`
       unas lineas mas abajo en `_50_fecha.py`.

       El techo de 60vh no es decorativo: Ajuste y Ventas tienen CUATRO
       filtros y el de Familia puede traer decenas de pills — sin el, el
       panel se sale de la pantalla por abajo y las ultimas secciones quedan
       inalcanzables. */
    [data-testid="stPopoverBody"]:has(.filtro-rotulo) {
        min-width: 420px !important;
        max-height: 60vh !important;
        overflow-y: auto !important;
    }
    .filtro-rotulo {
        font-size: 11px !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        color: var(--text-muted) !important;
        margin: 14px 0 2px 0 !important;
    }
    /* El primero no lleva el aire de separacion: no separa de nada. */
    [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"]
        > [data-testid="stElementContainer"]:first-child .filtro-rotulo {
        margin-top: 0 !important;
    }
    /* Estado ACTIVO (hay un filtro aplicado): fondo lleno en vez del tono
       tenue de reposo, para diferenciarlo a simple vista. */
    .st-key-chips_ajuste_tabla [class*="st-key-chipwrap_"][class*="_on"] [data-testid="stPopover"] button {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #ffffff !important;
    }
    .st-key-chips_ajuste_tabla [class*="st-key-chipwrap_"][class*="_on"] [data-testid="stPopover"] button:hover {
        background: var(--accent-deep) !important;
        border-color: var(--accent-deep) !important;
    }
    /* ── EL PANEL de Familia/Subfamilia: "se pisan entre sí" ──────────────
       2026-08-26, a pedido. No eran los chips (esos ya miden 230px fijos,
       sea cual sea el filtro aplicado) — era el PANEL abierto. `st.pills`
       renderiza sus opciones en un `stButtonGroup` con `flex-wrap: nowrap`
       por default; sin límite de ancho, un panel con 8 opciones (Familia)
       se estira a 704px en UNA sola fila para que entren todas sin
       envolver. Medido: ese panel (517-1221px) tapaba ENTERO al chip de
       Subfamilia (755-985px), que queda debajo.
       Fix: capar el panel a un ancho manejable y dejar que las opciones
       ENVUELVAN en varias líneas — mismo patrón que ya usa el panel de
       escala del Ranking de Proveedores (`cp_rank_escala_panel`,
       `graficos/compras/_css_proveedor.py`), sólo que ahí el contenido ya
       venía angosto y acá hay que forzarlo. `stPopoverBody` es un PORTAL
       (fuera de `chips_ajuste_tabla`), así que se alcanza con `:has()`
       sobre la key del `st.pills` de adentro, no colgando del contenedor. */
    [data-testid="stPopoverBody"]:has(.st-key-compras_graf_filtro_fam),
    [data-testid="stPopoverBody"]:has(.st-key-compras_graf_filtro_sub) {
        width: 300px !important;
        max-width: 300px !important;
    }
    .st-key-compras_graf_filtro_fam [data-testid="stButtonGroup"],
    .st-key-compras_graf_filtro_sub [data-testid="stButtonGroup"] {
        flex-wrap: wrap !important;
        width: 100% !important;
    }
    /* Pantallas chicas: si no caben junto a las pestañas, bajan a su línea */
    @media (max-width: 900px) {
        .st-key-chips_ajuste_tabla {
            position: static !important;
            width: auto !important;
            max-width: none !important;
            margin: 6px 0 0 0 !important;
        }
    }

    /* =================================================================== */
    /* DOCUMENTOS SUNAT: SIN CHIPS DE FAMILIA/SUBFAMILIA                     */
    /*                                                                       */
    /* SUNAT no sabe de familias —eso es taxonomía nuestra, del maestro de   */
    /* productos— y su registro es por DOCUMENTO, no por línea de producto.  */
    /* Filtrar por familia ahí daría un total que no cuadra con ningún       */
    /* papel, así que ese drill IGNORA los chips (lo dice el docstring de    */
    /* graficos/compras/documentos_sunat.py). Hasta hoy los chips seguían    */
    /* dibujados igual: dos controles a la vista que no hacían nada.         */
    /*                                                                       */
    /* Se esconden con CSS y NO se dejan de renderizar en Python, por dos    */
    /* motivos distintos:                                                    */
    /*   1. Los chips se dibujan ANTES de que se sepa qué vista eligió el    */
    /*      rail (`_render_rail` corre después, y es quien resuelve el       */
    /*      deep-link `?vista=`). Saberlo antes obligaría a duplicar esa     */
    /*      resolución.                                                       */
    /*   2. Un widget que deja de renderizarse PIERDE su estado (CLAUDE.md). */
    /*      Escondiéndolo, la Familia que el usuario tenía elegida sigue     */
    /*      ahí al volver a Proveedor o Producto.                            */
    /*                                                                       */
    /* El pill de FECHA se queda: SUNAT sí lo usa — es el rango que consulta */
    /* al SIRE (`comprobantes_rango`), y sin él la vista no tiene qué pedir. */
    /* Pero el pill que usa NO es el de la franja compartida: `app.py` ya    */
    /* apaga `franja_fecha.render()` para esta vista (no se puede duplicar  */
    /* la key `fecha_ajuste_pill`) y SUNAT dibuja el SUYO propio, dentro de  */
    /* `st-key-sunat_card_izq` — confirmado en el DOM (2026-08-31): el pill  */
    /* real de esta vista NO es descendiente de `fila_ajuste_top`. Con eso,  */
    /* `fila_ajuste_top` queda sin un solo widget acá (mismo caso que Receta */
    /* Base/Venta, más abajo — "no queda nada adentro, solo la banda        */
    /* decorativa") y se esconde entero, franja incluida.                   */
    /* Marker: `compras_sunat_drill_wrap`, el contenedor que sólo existe     */
    /* cuando ese drill está en pantalla. Va desde `:root` porque los chips  */
    /* son `position: fixed` y viven fuera del wrapper.                      */
    /* =================================================================== */
    :root:has(.st-key-compras_sunat_drill_wrap) .st-key-chips_ajuste_tabla {
        display: none !important;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-compras_sunat_drill_wrap)
        .st-key-fila_ajuste_top {
        display: none !important;
    }
"""
