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
`graficos/base.py::_render_rail` monta un iframe de alto 0 con un
temporizador que mide geometria: pone `rails-scrolled` en el <html> del
documento PADRE cuando la seccion mas visible ya no es la PRIMERA de la
pila. Todo el CSS de abajo cuelga de esa clase.

O sea que la columna cambia en cuanto dejas atras la primera vista, sin
umbrales en px — el alto de cada seccion cambia con los datos.

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

    /* Y su RÓTULO con él: la tarjeta cambia de contenido, así que el
       "Reportes" de arriba tiene que cambiar a "Vistas" en el mismo gesto.
       Si sólo cruzaran los railes, el rótulo mentiría justo mientras dura
       el cruce — que es cuando se lo mira. Geometría de los dos en
       `estilos/_20_compras_rail.py`. */
    .st-key-rail_rotulo_rep {{
        transition: opacity {_TRANS} linear;
    }}
    :root.rails-scrolled .st-key-rail_rotulo_rep {{
        opacity: 0;
    }}

    /* ── El rail de VISTAS entra ──────────────────────────────────────
       GEOMETRIA ACOPLADA: estos cuatro valores son los mismos que
       `estilos/_20_compras_rail.py` le da a `.st-key-compras_tabs_row`,
       porque los dos ocupan EL MISMO hueco y el cambio tiene que verse
       como que la columna cambio de contenido, no como que se movio. Si
       alla se corre el rail, aca hay que correrlo igual.

       2026-08-26: `top` a `0` y `max-height` sin el termino
       `- var(--nav-top-alto)` — mismo cambio y mismo motivo que
       `_20_compras_rail.py` (ver el comentario largo ahi). Se repite acá
       en vez de derivarlo con una variable compartida porque las CUATRO
       propiedades son literales duplicados a proposito desde que nacio
       este rail (2026-08-24) — es el precio ya asumido de la geometria
       acoplada, no algo nuevo de este cambio.

       2026-08-31: `top` a `47px`, `max-height` recupera ese termino y
       `border-radius` a 0 — la cuarta vuelta de la serie, explicada
       entera en `_20_compras_rail.py`. */
    .st-key-nav_rail_lateral {{
        position: fixed !important;
        top: 47px !important;                         /* == _20_compras_rail.py */
        left: 19px !important;                        /* == _20_compras_rail.py */
        width: var(--rail-der-w) !important;          /* nombre historico: es el IZQUIERDO */
        max-height: calc(100vh - 47px - 8px) !important;   /* == _20_compras_rail.py */
        overflow-y: auto !important;
        overflow-x: hidden !important;
        scrollbar-width: none !important;
        z-index: 901 !important;                      /* 1 por encima del de reportes (900) */
        margin: 0 !important;
        padding: 8px 0 16px 0 !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;                  /* == _20_compras_rail.py */
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

    /* Reposo OCULTO y sin `!important`, por el mismo motivo que el rail que
       encabeza (ver "DEGRADACION SEGURA" acá arriba): si el gancho no llega
       a montarse, el peor caso es que no pase nada — no dos rótulos
       superpuestos. */
    .st-key-rail_rotulo_vis {{
        opacity: 0;
        transition: opacity {_TRANS} linear;
    }}
    :root.rails-scrolled .st-key-rail_rotulo_vis {{
        opacity: 1;
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
        /* min-height y no height: el texto tiene que poder centrarse
           verticalmente adentro (align-items:center), no solo caber. Con
           height a secas el label quedaba pegado arriba del hueco. */
        min-height: 62px !important;              /* == navitem_ de Reportes, medido */
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
        margin: 0 !important;
        padding: 0 14px !important;
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
    /* 2026-08-26, a pedido ("estar pegados a la izquierda, como el rail de
       reportes"): Streamlit mete un `div` interno entre el `<button>` y el
       `stMarkdownContainer` con `display:flex; justify-content:center` por
       default -- el MISMO wrapper que ya documenta y aplana
       `_20_compras_rail.py` para Reportes ("hay que aplanar TODOS los div
       descendientes del botón"), pero acá nunca se había hecho porque este
       rail nació sin ícono (sólo texto) y el centrado no se notaba con una
       sola palabra corta.
       Medido el bug real: con ícono + label, ese wrapper (250px) centraba
       su contenido (96px) empujando el ícono a 91px del borde izquierdo del
       botón — "Producto" arrancaba casi a mitad de fila en vez de pegado a
       la izquierda. `display:block` deja que el contenido tome su propio
       ancho en vez de estirarse a ocupar la fila entera para luego
       centrarse en ella. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button > div,
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {{
        display: block !important;
        width: auto !important;
        max-width: 100% !important;
    }}
    /* El ITEM EN PANTALLA. La clase la pone el scrollspy de
       `base.py::_render_rail`, no `type="primary"`: lo que se marca es
       donde ESTAS, no el ultimo clic. Los botones se dibujan todos
       `secondary` justamente para que no haya dos marcas discutiendo.
       Barra por `inset` y no por `border-left`: no participa del box
       model, asi que el texto no se corre al activarse — mismo recurso
       que el subrayado de la franja horizontal. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla {{
        /* Mismo `--accent-light` que el activo del rail de Reportes
           (`_20_compras_rail.py`): las dos columnas ocupan el MISMO hueco y
           se turnan, asi que marcar distinto se leeria como dos componentes
           en vez de uno que cambio de contenido. */
        background: var(--accent-light) !important;
        color: var(--accent-deep) !important;
        box-shadow: inset 3px 0 0 0 var(--accent) !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla p {{
        font-weight: 500 !important;
    }}
    /* ── CABECERA: el reporte que estas viendo ────────────────────────
       Esta columna reemplaza a la lista de Reportes al bajar, y con ella se
       iba el nombre del reporte. La cabecera lo devuelve con sus KPIs —
       mismo patron que las fichas de MSN Dinero, que encabezan su rail con
       la entidad y debajo listan sus secciones.
       El separador es un `border-bottom` y no un `<hr>`: no agrega un nodo
       que despues haya que espaciar. */
    .st-key-nav_rail_lateral .rail-cab {{
        /* MISMO ALTO que un item de vista (62px medidos, 2026-08-25, a
           pedido). Se consigue con los interlineados de abajo, no con un
           `height`: las tres lineas traian el line-height por defecto
           (21+22+19 = 62 solo de texto) y el bloque se iba a 80px. */
        padding: 2px 14px 10px 14px !important;
        margin-bottom: 8px !important;
        border-bottom: 1px solid var(--border) !important;
    }}
    .st-key-nav_rail_lateral .rail-cab-nom {{
        /* 1rem = 16px, el MISMO cuerpo que los items de vista de abajo
           (2026-08-25, a pedido: "se ve muy grande"). Lo que la separa como
           cabecera es el peso y el hairline de abajo, no el tamaño — con
           16.8px se leia como otro nivel de jerarquia y competia con el
           contenido. */
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        line-height: 1.2 !important;
    }}
    /* Los KPIs en su propio renglon, chicos y apagados: son contexto, no el
       titulo. Mismo criterio que el segundo renglon de los items de
       Reportes (`navegacion.py::_CSS_KPIS`). */
    .st-key-nav_rail_lateral .rail-cab-kpi {{
        /* `block` y no `inline-block`: un inline-block se sienta sobre una
           linea de texto y arrastra el espacio de los descendentes — 10px
           fantasma que no aparecen en la suma de las piezas y hacian que el
           bloque midiera 71 en vez de 62 (medido 2026-08-25). Igual va en su
           propio renglon, asi que no se pierde nada. */
        display: block !important;
        font-size: .85rem !important;
        font-weight: 600 !important;
        color: var(--accent-deep) !important;
        line-height: 1.15 !important;
        margin-top: 1px !important;
    }}
    .st-key-nav_rail_lateral .rail-cab-kpi.kpi-neg {{
        color: var(--danger-text) !important;
    }}
    .st-key-nav_rail_lateral .rail-cab-kpi2 {{
        display: block !important;
        font-size: .74rem !important;
        color: var(--text-secondary) !important;
        line-height: 1.1 !important;
    }}

    /* El icono material del item. Hereda el color del boton (o sea que
       sigue solo al estado activo/reposo/hover) y va un punto mas chico que
       el del rail de Reportes, que tiene el icono ARRIBA del texto y puede
       permitirselo mas grande; aca van en linea. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stIconMaterial"] {{
        font-size: 19px !important;
        margin-right: 10px !important;
        color: inherit !important;
        flex: 0 0 auto !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button p {{
        margin: 0 !important;
        /* 1rem = 16px, el mismo cuerpo que los items del rail de Reportes
           (medido en el navegador). Venia en .82rem y se leia mas chica
           justo cuando la columna cambia de contenido, que es cuando el
           salto se nota. */
        font-size: 1rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }}
    /* ── HAIRLINE entre cada ítem ──────────────────────────────────────
       2026-08-26, a pedido ("tambien debe tener lineas que lo separan...
       como el rail de reportes"): mismo recurso que `.st-key-
       graf_tipo_chips > div` en `_20_compras_rail.py` — un hairline por
       ítem, apagado en el último. La diferencia de selector (`:has(...)`
       en vez de `> div`) es porque acá los ítems NO están envueltos en un
       `navitem_<slug>` propio (Reportes sí); el `stElementContainer` del
       propio `st.button` hace de unidad. `:has([data-testid="stButton"])`
       excluye a la cabecera (`.rail-cab`, un `st.markdown` sin botón) y al
       separador de "destino aparte" de abajo (tampoco tiene botón), que
       ya ponen su propia línea y no necesitan una segunda. */
    .st-key-nav_rail_lateral [data-testid="stElementContainer"]:has([data-testid="stButton"]) {{
        border-bottom: 1px solid var(--border) !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stElementContainer"]:has([data-testid="stButton"]):last-child {{
        border-bottom: none !important;
    }}
    /* ── SEPARADOR: scroll-to vs destino aparte ───────────────────────
       2026-08-26, a pedido ("el reporte de documentos sunat no aparece
       al hacer scroll"): no era un bug, era que el rail no avisaba que
       Documentos SUNAT es un DESTINO APARTE (`base.py::_render_rail` lo
       dibuja cuando la membresía a `secciones` cambia de un ítem al
       siguiente). Con el hairline de arriba ahora separando TODOS los
       ítems por igual, este separador extra es lo único que sigue
       marcando esa frontera como distinta — sin él, Documentos se leería
       como un ítem más de la pila. Mismo recurso que `.rail-cab`: un
       `border-top` en un div vacío, no un `<hr>` que después haya que
       espaciar. */
    .st-key-nav_rail_lateral .nav-rail-lat-sep {{
        border-top: 1px solid var(--border) !important;
        margin: 6px 14px !important;
    }}
}}

/* ── LOS ENVOLTORIOS NO APORTAN GAP ───────────────────────────────────
   Los CUATRO cromos fijos de la cabecera —la franja de vistas
   (`nav_rail`), los chips de Familia/Subfamilia (`chips_ajuste_tabla`), el
   rail lateral y el gancho— no dibujan NADA en el flujo: son
   `position: fixed`, verificado uno por uno. Pero Streamlit los envuelve en
   un `stLayoutWrapper` y el bloque vertical padre le da a cada uno sus 16px
   de `gap`. Cuatro envoltorios de alto 0 = 64px de aire empujando la
   primera tarjeta hacia abajo — medido 2026-08-25: la seccion arrancaba en
   y=176 con la franja terminando en 96.

   Los dos ultimos son cromo COMPARTIDO por los 9 reportes; se incluyen
   igual porque la condicion que los hace elegibles (contenido fuera del
   flujo) vale en todos, no solo en Compras.

   `display: contents` y no `display: none`: none BORRA el subarbol y con el
   el rail, que si tiene que dibujarse (sale del flujo por su
   `position: fixed`, no por estar oculto). `contents` hace desaparecer la
   CAJA del envoltorio dejando vivos a los hijos: sin caja no hay flex item,
   y sin flex item no hay gap. */
/* Por `data-testid` y NO por `.stLayoutWrapper`: el envoltorio lleva ese
   testid pero su `class` son hashes de emotion, que cambian entre versiones
   de Streamlit. Apuntar a la clase no matcheaba nada (primer intento). */
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-nav_rail_lateral"]),
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-rail_scroll_hook"]),
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-nav_rail"]),
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-chips_ajuste_tabla"]) {{
    display: contents !important;
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
