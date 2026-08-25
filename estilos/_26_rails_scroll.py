"""Intercambio de rails al hacer scroll (2026-08-24).

La columna izquierda muestra DOS cosas distintas segun donde estes:

  · arriba de todo  -> el rail de REPORTES (`compras_tabs_row`): Compras,
    Movimientos, Recetas, Ajuste...
  · al bajar        -> el rail de VISTAS (`nav_rail_lateral`): Proveedor,
    Producto, Vs ano pasado...

El razonamiento: los nombres de reporte son navegacion de PRIMER nivel y
solo hacen falta al llegar. Una vez que estas leyendo un reporte, lo que
queres a mano es moverte entre SUS vistas, no saltar a otro reporte. Asi
que la columna cambia de trabajo a medida que bajas.

EL DISPARADOR: UNA CLASE QUE PONE JS
-----------------------------------
`graficos/base.py::_render_rail` monta un `components.html` de alto 0 con
un `IntersectionObserver`: pone `rails-scrolled` en el <html> del documento
PADRE mientras el ancla del dashboard este EN PANTALLA. Todo el CSS de
abajo cuelga de esa clase.

En Compras el ancla es el drill de Producto, o sea que la columna cambia
justo cuando aparecen los graficos de la segunda mitad. No es un umbral en
px a proposito: el alto del primer drill cambia con los datos.

Por que no `st.markdown` con `<script>`: no lo ejecuta (ver CLAUDE.md).
`components.html` SI, porque es un iframe de verdad — el inspector del
proyecto ya se apoya en eso.

Por que no animaciones por scroll (`animation-timeline`), que serian CSS
puro y fue el primer intento: la `ScrollTimeline` queda INACTIVA. Medido
el 2026-08-24 en Chrome 148 — el soporte esta, y una timeline declarada
DESPUES de que la pagina asienta funciona; pero la que se declara con el
CSS inicial se crea cuando `stMain` todavia no scrollea y no se reactiva
sola cuando el contenido crece. `currentTime` se queda en null para
siempre. Si algun dia eso se arregla en el motor, volver a CSS puro es
sacar el gancho y colgar las mismas reglas de un `animation-range`.

Otros dos detalles que conviene no volver a pisar:

  1. QUIEN SCROLLEA no es la ventana sino `[data-testid="stMain"]`. La
     ventana no scrollea nunca (el layout es de alto fijo). El listener va
     en fase de CAPTURA sobre el documento, porque `scroll` no burbujea.

  2. La franja horizontal tiene su `top/left/width` fijados con
     `!important` en `navegacion.py::_CSS_FRANJA_VISTAS`, asi que no se la
     puede "mover" a la columna con CSS. Por eso hay un SEGUNDO rail
     vertical (`_render_rail`) y lo unico que cambia es cual se ve.

Un modulo de `estilos/` NUNCA lleva `<style>` propio: `_00_base` abre la
etiqueta y `_99_movil` la cierra, y todo lo del medio va pelado. Un
`<style>` anidado es sintaxis invalida y el parser DESCARTA ese modulo y
TODOS los siguientes — se perdieron los estilos moviles enteros hasta que
se encontro. Paso aca el 2026-08-24.

Solo escritorio: en movil el cromo es otro (nav inferior propia, ver
`_99_movil.py`) y ahi la columna izquierda no existe. Mismo breakpoint que
el resto del proyecto.
"""

# Duracion del cruce. Corta a proposito: es un intercambio, no un efecto.
_TRANS = "160ms"

CSS = f"""
@media screen and (min-width: 769px) {{

    /* ── El gancho ────────────────────────────────────────────────────
       `graficos/base.py::_render_rail` monta un `components.html` que
       pone/saca la clase `rails-scrolled` en el <html> del documento
       padre segun el scroll de `stMain`. Todo lo de aca abajo cuelga de
       esa clase. */

    /* El rail de REPORTES se va. */
    .st-key-compras_tabs_row {{
        transition: opacity {_TRANS} linear;
    }}
    :root.rails-scrolled .st-key-compras_tabs_row {{
        opacity: 0;
        pointer-events: none;
    }}

    /* ── El rail de VISTAS entra ──────────────────────────────────────
       GEOMETRIA ACOPLADA: estos cuatro valores son los mismos que
       `estilos/_20_compras_rail.py` le da a `.st-key-compras_tabs_row`,
       porque los dos ocupan EL MISMO hueco y el cambio tiene que verse
       como que la columna cambio de contenido, no como que se movio. Si
       alla se corre el rail, aca hay que correrlo igual. */
    .st-key-nav_rail_lateral {{
        position: fixed !important;
        top: calc(var(--nav-top-alto) - 2px) !important;
        left: 19px !important;                        /* == _20_compras_rail.py */
        width: var(--rail-der-w) !important;          /* nombre historico: es el IZQUIERDO */
        max-height: calc(100vh - var(--nav-top-alto) - 8px) !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        scrollbar-width: none !important;
        z-index: 901 !important;                      /* 1 por encima del de reportes (900) */
        margin: 0 !important;
        padding: 8px 0 16px 0 !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: none !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 0 !important;
        /* ── DEGRADACION SEGURA ───────────────────────────────────────
           Estado de reposo OCULTO, y sin `!important` a proposito: una
           animacion le gana a una declaracion normal, asi que cuando la
           timeline esta activa manda el keyframe, y cuando NO lo esta
           manda esto.
           Hace falta porque la timeline no siempre arranca: si se declara
           mientras `stMain` todavia no scrollea, queda inactiva y no se
           reactiva sola (medido 2026-08-24; una timeline declarada DESPUES
           de que la pagina asiente si activa). Sin este reposo, la
           inactividad dejaba el rail lateral a opacidad 1 ENCIMA del de
           Reportes: los dos visibles, superpuestos. Con esto, el peor caso
           es que la funcion no ocurra y la pantalla se vea como siempre. */
        opacity: 0;
        pointer-events: none;
        transition: opacity {_TRANS} linear;
    }}
    .st-key-nav_rail_lateral::-webkit-scrollbar {{ display: none !important; }}

    :root.rails-scrolled .st-key-nav_rail_lateral {{
        opacity: 1;
        pointer-events: auto;
    }}

    /* ── Los items del lateral ────────────────────────────────────────
       `navegacion.py` estila `.st-key-nav_rail` con clase EXACTA, asi que
       nada de aquello alcanza a `nav_rail_lateral`: su aspecto se define
       entero aca. Es un menu vertical, no una fila de tabs, asi que el
       activo se marca con una barra a la IZQUIERDA (no un subrayado). */
    .st-key-nav_rail_lateral [data-testid="stVerticalBlock"] {{
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        width: 100% !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stElementContainer"],
    .st-key-nav_rail_lateral [data-testid="stButton"] {{
        width: 100% !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button {{
        width: 100% !important;
        justify-content: flex-start !important;
        text-align: left !important;
        margin: 0 !important;
        padding: 7px 14px !important;
        border: none !important;
        border-radius: 0 !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
        box-shadow: none !important;
        font-weight: 400 !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button:hover {{
        background: var(--accent-tint) !important;
        color: var(--accent) !important;
    }}
    /* El ITEM EN PANTALLA. La clase la pone el scrollspy de
       `base.py::_render_rail`, no `type="primary"`: lo que se marca es
       donde ESTAS, no el ultimo clic. Los botones se dibujan todos
       `secondary` justamente para que no haya dos marcas discutiendo.
       Barra por `inset` y no por `border-left`: no participa del box
       model, asi que el texto no se corre al activarse — mismo recurso
       que el subrayado de la franja horizontal. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla {{
        background: transparent !important;
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
        box-shadow: inset 3px 0 0 0 var(--accent) !important;
    }}
    /* El icono material del item. Hereda el color del boton (o sea que
       sigue solo al estado activo/reposo/hover) y va un punto mas chico que
       el del rail de Reportes, que tiene el icono ARRIBA del texto y puede
       permitirselo mas grande; aca van en linea. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stIconMaterial"] {{
        font-size: 17px !important;
        margin-right: 9px !important;
        color: inherit !important;
        flex: 0 0 auto !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button p {{
        margin: 0 !important;
        font-size: .82rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }}
}}

/* El contenedor del gancho no pinta nada: es un iframe de alto 0 que solo
   existe para correr el JS. Va FUERA de los @media —en los dos anchos— y no
   dentro del de escritorio, que fue el primer intento: en movil quedaba un
   contenedor de 327px de ancho en el flujo. Mide 0 de alto, asi que no se
   veia; se encontro midiendo, no mirando. */
.st-key-rail_scroll_hook {{
    display: none !important;
}}

/* En movil no hay columna izquierda: el lateral no se dibuja nunca. El
   rail de vistas sigue siendo la franja de arriba, como hasta ahora. */
@media screen and (max-width: 768px) {{
    .st-key-nav_rail_lateral {{ display: none; }}
}}
"""
