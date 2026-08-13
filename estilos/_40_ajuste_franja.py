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
    .st-key-fila_ajuste_top::before {
        content: "" !important;
        position: fixed !important;
        top: 0 !important;
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
        height: var(--cab-altura) !important;
        border-radius: 0 !important;   /* toca los dos bordes: sin esquinas */
        /* Tinte lavanda translúcido en vez del blanco al 62%: el cristal
           esmerilado sobre canvas blanco era invisible (reportado con
           captura — "no la veo muy bien"). El color sale de --accent-tint
           (paleta única, ver CLAUDE.md § Colores) y color-mix le pone el
           alfa; el blur sigue haciendo falta porque la barra es fixed y el
           contenido pasa POR DEBAJO al scrollear. */
        background: color-mix(in srgb, var(--accent-tint) 88%, transparent) !important;
        backdrop-filter: blur(14px) saturate(1.6) !important;
        -webkit-backdrop-filter: blur(14px) saturate(1.6) !important;
        border: none !important;
        border-bottom: 2px solid var(--border-lavender) !important;
        box-shadow: 0 4px 14px rgba(16, 16, 20, 0.06) !important;
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
            height: 46px !important;
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
    /* CHIPS DE FILTRO EN LA FRANJA BLANCA — Área / Familia / Ajuste /     */
    /* Ajuste valor.  Nivel 2, a la derecha del selector de vista.         */
    /* ================================================================== */
    /* Filtros Familia / Subfamilia en el NIVEL 1: pegados a la IZQUIERDA,
       alineados con el borde izquierdo de la TARJETA (no del rail). El
       block-container tiene padding-left ~60px encima del rail (90px),
       de ahi los ~154px. La fecha se ancla al lado derecho (más abajo). */
    .st-key-chips_ajuste_tabla {
        position: fixed !important;
        top: 8px !important;
        left: 154px !important;
        right: auto !important;
        width: auto !important;
        max-width: calc(100vw - 154px - 380px) !important;   /* deja aire para la fecha derecha */
        z-index: 23 !important;
        margin: 0 !important;
        padding: 0 !important;
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
    /* Pantallas chicas: si no caben junto a las pestañas, bajan a su línea */
    @media (max-width: 900px) {
        .st-key-chips_ajuste_tabla {
            position: static !important;
            width: auto !important;
            max-width: none !important;
            margin: 6px 0 0 0 !important;
        }
    }
"""
