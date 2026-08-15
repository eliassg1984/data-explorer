"""estilos._25_rails_pestillo - Los dos rails plegables: lenguetas, plegado
fijo (clic) y vistazo por hover (superpuesto, sin rerun).

Va DESPUES de _20_compras_rail a proposito: varias reglas de aqui tienen
que ganarle a las suyas (el `width` del rail derecho, el `display:flex` de
graf_tipo_chips). El estado y los marcadores los pone `pestillos.py`.

Extraido de ningun sitio: nace con el pestillo (2026-08-15).
"""

CSS = """    /* =================================================================== */
    /* RAILS PLEGABLES — el pestillo                                        */
    /*                                                                      */
    /* Todo este bloque se activa por la PRESENCIA de un marcador que deja  */
    /* `pestillos.py::marcar()` en el DOM (`<style class="rail-izq-plegado">`*/
    /* vacío). Sin marcador no hay ni una regla activa, así que el aspecto  */
    /* de siempre es literalmente el mismo CSS de siempre.                  */
    /*                                                                      */
    /* Por qué un marcador y no una clase en el contenedor: Streamlit no    */
    /* deja poner clases propias en sus bloques. Lo que sí se puede es      */
    /* mirar el documento entero con :has() desde :root — el mismo truco    */
    /* que ya usan las secciones por reporte con `st-key-app_reporte_*`     */
    /* (regla #16).                                                         */
    /* =================================================================== */

    /* ── 1. PLEGAR = cambiar un ancho. Nada más. ────────────────────────
       El margen izquierdo de la app, el `left` de la franja inferior y del
       topbar, el `padding-right` del contenido y los anclajes `right` de la
       fecha/chips/atajos ya se derivan de estas dos variables (_00_base).
       Por eso plegar es UNA línea por rail: la tarjeta se ensancha sola y
       no hay seis sitios que recordar (que era la regla #17, el fallo más
       repetido de este CSS). */
    :root:has(style.rail-izq-plegado) { --rail-izq-w: var(--rail-min); }
    :root:has(style.rail-der-plegado) { --rail-der-w: var(--rail-min); }

    /* ── 1b. NUNCA una `transition` sobre el `width` de estos rails ─────
       Costó una hora el 2026-08-15 y merece quedar escrito, porque el
       síntoma no se parece en nada a la causa: el rail se quedaba clavado
       en 90px PARA SIEMPRE (no "tardaba" — no llegaba nunca) mientras todo
       lo demás sí se movía. El margen de la app, la franja inferior, el
       padding del contenido, y hasta el ancho de los botones de dentro del
       propio rail (`calc(var(--rail-izq-w) - 16px)`, que medía 8px): todo
       correcto. Solo el ancho del rail, no.
       Se descartó una a una la lista de sospechosos: la variable valía
       24px medida SOBRE el elemento, la regla matcheaba (`e.matches()` →
       true) y sus otras declaraciones —`min-height`, `overflow`,
       `border-radius`— entraban perfectas. Ni siquiera un
       `width:24px !important` inline lo movía. Lo único distinto del
       `width` era tener transición: la transición arranca en 90, el rerun
       de Streamlit reconstruye el DOM a media animación y el valor se queda
       congelado en el fotograma inicial, inmune a cualquier cascada
       posterior. Se despertaba solo si se tocaba la variable a mano.
       Después pasó lo mismo con la SOMBRA del vistazo, que también estaba
       transicionada: al pasar el cursor el rail se abría —ancho, íconos,
       radio, todo— pero la sombra se quedaba en la de reposo. Misma causa,
       mismo desenlace. Por eso aquí no hay ni una `transition`: los dos
       rails abren y cierran de golpe, que además es lo que hacen los de VS
       Code y Notion.
       Si algún día se quiere animar el plegado, que sea con `transform`
       (no dispara layout y no se puede quedar a medias), nunca con `width`
       ni con nada que un rerun pueda pillar a media animación. */

    /* ── 2. RAIL IZQUIERDO plegado: lengüeta pegada al borde ──────────── */
    :root:has(style.rail-izq-plegado) .st-key-nav_rail {
        /* El ancho del PROPIO rail se declara aquí, aunque `navegacion.py`
           ya diga `width: var(--rail-izq-w)` y la variable acabe de cambiar.
           No es redundante: medido el 2026-08-15, Chrome no vuelve a
           resolver ese `width` cuando la variable cambia por una regla
           condicionada con `:has()` — el rail se quedaba en 90px mientras
           TODO lo demás que deriva de la misma variable sí se movía (el
           margen de la app, la franja inferior, incluso el ancho de los
           botones de dentro del rail). Se recuperaba con solo tocar la
           variable a mano en la consola, así que es invalidación perezosa,
           no cascada.
           La regla práctica: lo que cambia por `:has()` se DECLARA en la
           regla del `:has()`. Heredar una variable sirve para lo que está
           lejos (el margen, el padding); para el elemento que la propia
           regla toca, ponlo directo. */
        width: var(--rail-min) !important;
        overflow: hidden !important;
        /* Sin esto la lengüeta mide lo que mide el pestillo (~34px de alto)
           y hay que cazarla con el cursor. 132px la vuelven una tira
           cómoda de apuntar, que es la mitad del gesto de "vistazo". */
        min-height: 132px !important;
        /* Pegada al filo de la ventana y redondeada solo del lado que se
           ve: deja de leerse como "una tarjeta chiquita" y pasa a leerse
           como "una pestaña de la que tirar". */
        border-radius: 0 14px 14px 0 !important;
    }
    /* Los ítems de navegación se ESCONDEN, no se dejan de dibujar: si no se
       renderizaran, Streamlit perdería el estado de sus botones (CLAUDE.md
       § Streamlit). Con `display:none` siguen existiendo. */
    :root:has(style.rail-izq-plegado) .st-key-nav_rail [class*="st-key-navbtn_"] {
        display: none !important;
    }
    :root:has(style.rail-izq-plegado) .st-key-nav_rail [data-testid="stVerticalBlock"] {
        justify-content: center !important;   /* el pestillo, centrado */
        overflow: hidden !important;
    }

    /* VISTAZO — cursor sobre la lengüeta. El rail es `position:fixed`, así
       que ensancharlo lo SUPERPONE sobre la tarjeta en vez de empujarla:
       mirar no mueve nada y no cuesta un rerun. La sombra es lo que dice
       "esto está flotando encima", no adherido. */
    :root:has(style.rail-izq-plegado) .st-key-nav_rail:hover {
        width: var(--rail-izq-full) !important;
        border-radius: 18px !important;
        box-shadow: 6px 0 22px rgba(16, 16, 20, 0.16) !important;
    }
    :root:has(style.rail-izq-plegado) .st-key-nav_rail:hover [class*="st-key-navbtn_"] {
        display: flex !important;
    }
    :root:has(style.rail-izq-plegado) .st-key-nav_rail:hover [data-testid="stVerticalBlock"] {
        justify-content: flex-start !important;
        overflow-y: auto !important;
    }

    /* ── 3. RAIL DERECHO plegado: misma idea, espejada ─────────────────── */
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row {
        width: var(--rail-min) !important;   /* directo, ver el punto 2 */
        overflow: hidden !important;
        min-height: 132px !important;
    }
    :root:has(style.rail-der-plegado) .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
        display: none !important;
    }
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row:hover {
        width: var(--rail-der-full) !important;
        box-shadow: -6px 0 22px rgba(16, 16, 20, 0.16) !important;
    }
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row:hover
        .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
        display: flex !important;
    }

    /* ── 4. LOS PESTILLOS ───────────────────────────────────────────────
       Botón mínimo: chevron gris sobre nada. Se acota a su PROPIA key
       (regla #6): el rail izquierdo estila `[class*="st-key-navbtn_"]` y el
       derecho estila todo lo que cuelgue de `graf_tipo_chips`, así que el
       pestillo se llama distinto y vive fuera de ese contenedor a
       propósito — si heredara esos estilos sería un ítem más de la lista. */
    .st-key-nav_pestillo,
    .st-key-rail_pestillo {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-nav_pestillo button,
    .st-key-rail_pestillo button {
        width: 100% !important;
        min-height: 0 !important;
        height: 22px !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        border-radius: 6px !important;
        background: transparent !important;
        color: var(--text-muted) !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        opacity: 0.45 !important;              /* discreto hasta que lo buscas */
    }
    .st-key-nav_rail:hover .st-key-nav_pestillo button,
    .st-key-compras_tabs_row:hover .st-key-rail_pestillo button {
        opacity: 1 !important;
    }
    .st-key-nav_pestillo button:hover,
    .st-key-rail_pestillo button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
        opacity: 1 !important;
    }
    .st-key-nav_pestillo button [data-testid="stIconMaterial"],
    .st-key-rail_pestillo button [data-testid="stIconMaterial"],
    .st-key-nav_pestillo button p > span,
    .st-key-rail_pestillo button p > span {
        font-size: 18px !important;
        line-height: 1 !important;
    }
    .st-key-nav_pestillo button p,
    .st-key-rail_pestillo button p {
        margin: 0 !important;
        line-height: 1 !important;
    }
    /* Plegado, el pestillo ES la lengüeta: se estira a lo alto para que
       toda la tira sea clicable, no solo 22px en la punta. */
    :root:has(style.rail-izq-plegado) .st-key-nav_pestillo button,
    :root:has(style.rail-der-plegado) .st-key-rail_pestillo button {
        height: 116px !important;
        opacity: 0.8 !important;
    }
    :root:has(style.rail-izq-plegado) .st-key-nav_rail:hover .st-key-nav_pestillo button,
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row:hover .st-key-rail_pestillo button {
        height: 22px !important;
    }

    /* ── 5. MÓVIL — no hay pestillo ─────────────────────────────────────
       Los dos rails ya se transforman en tiras horizontales (bottom nav el
       izquierdo, fila scrollable el derecho): no ocupan ancho, así que no
       hay nada que recuperar plegándolos. Además el "vistazo" por hover no
       existe en pantalla táctil. Se fuerza el estado desplegado por si el
       usuario dejó un rail plegado en escritorio y abre en el teléfono. */
    @media (max-width: 768px) {
        /* El selector largo NO es paranoia: `navegacion.py` estila
           `.st-key-nav_rail [data-testid="stElementContainer"]` con
           `display:flex !important`, y el contenedor del pestillo ES uno de
           esos (0,2,0 contra los 0,1,0 de su propia key). Un `@media` no
           suma especificidad, así que el pestillo seguía apareciendo en la
           barra inferior del móvil. Es la trampa de CLAUDE.md § "antes de
           agregar un widget dentro de una tarjeta, grep estilos/": la regla
           del CONTENEDOR captura al widget nuevo. */
        .st-key-nav_rail [data-testid="stElementContainer"].st-key-nav_pestillo {
            display: none !important;
        }
        :root:has(style.rail-izq-plegado) { --rail-izq-w: var(--rail-izq-full); }
        /* Hay que deshacer el `width` DIRECTO del punto 2, no solo la
           variable: si no, el rail plegado en escritorio llega al móvil
           convertido en una lengüeta de 24px encima de la barra inferior.
           El 100vw es el mismo que pone `navegacion.py` para la bottom nav
           — se repite porque el selector con `:has()` le gana en
           especificidad y sin repetirlo nadie lo devuelve a su sitio. */
        :root:has(style.rail-izq-plegado) .st-key-nav_rail {
            width: 100vw !important;
            min-height: 0 !important; overflow-x: auto !important;
            border-radius: 0 !important;
        }
        :root:has(style.rail-izq-plegado) .st-key-nav_rail [class*="st-key-navbtn_"] {
            display: flex !important;
        }
    }
    @media (max-width: 900px) {
        .st-key-rail_pestillo { display: none !important; }
        :root:has(style.rail-der-plegado) { --rail-der-w: var(--rail-der-full); }
        :root:has(style.rail-der-plegado) .st-key-compras_tabs_row {
            width: 100% !important;        /* ídem, ver el rail izquierdo */
            min-height: 0 !important;
        }
        :root:has(style.rail-der-plegado) .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
            display: flex !important;
        }
    }
"""
