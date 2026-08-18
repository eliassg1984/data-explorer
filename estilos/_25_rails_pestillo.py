"""estilos._25_rails_pestillo - El rail plegable de VISTAS: lengueta, plegado
fijo (clic) y vistazo por hover (superpuesto, sin rerun).

Va DESPUES de _20_compras_rail a proposito: varias reglas de aqui tienen
que ganarle a las suyas (el `width` del rail derecho, el `display:flex` de
graf_tipo_chips). El estado y los marcadores los pone `pestillos.py`.

Extraido de ningun sitio: nace con el pestillo (2026-08-15).

2026-08-18: hasta hoy habia DOS rails plegables. El izquierdo (navegacion)
paso a ser la franja horizontal superior (`navegacion.py`): una barra que
no le quita ancho a la tarjeta no tiene nada que recuperar plegandose, asi
que todo su bloque —lengueta, vistazo, pestana de acento montada en el
filo— se retiro junto con la variable --rail-izq-w. Queda solo el DERECHO.
"""

CSS = """    /* =================================================================== */
    /* RAIL PLEGABLE DE VISTAS — el pestillo                                 */
    /*                                                                      */
    /* Todo este bloque se activa por la PRESENCIA de un marcador que deja  */
    /* `pestillos.py::marcar()` en el DOM (`<style class="rail-der-plegado">`*/
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
       El `padding-right` del contenido y los anclajes `right` de la fecha,
       los chips y los atajos ya se derivan de esta variable (_00_base).
       Por eso plegar es UNA línea: la tarjeta se ensancha sola y no hay
       seis sitios que recordar (que era la regla #17, el fallo más
       repetido de este CSS). */
    :root:has(style.rail-der-plegado) { --rail-der-w: var(--rail-min); }

    /* ── 1b. NUNCA una `transition` sobre el `width` de este rail ───────
       Costó una hora el 2026-08-15 y merece quedar escrito, porque el
       síntoma no se parece en nada a la causa: el rail se quedaba clavado
       en su ancho PARA SIEMPRE (no "tardaba" — no llegaba nunca) mientras
       todo lo demás sí se movía. El padding del contenido y hasta el ancho
       de los botones de dentro del propio rail: todo correcto. Solo el
       ancho del rail, no.
       Se descartó una a una la lista de sospechosos: la variable valía
       24px medida SOBRE el elemento, la regla matcheaba (`e.matches()` →
       true) y sus otras declaraciones —`min-height`, `overflow`,
       `border-radius`— entraban perfectas. Ni siquiera un
       `width:24px !important` inline lo movía. Lo único distinto del
       `width` era tener transición: la transición arranca en el valor
       viejo, el rerun de Streamlit reconstruye el DOM a media animación y
       el valor se queda congelado en el fotograma inicial, inmune a
       cualquier cascada posterior. Se despertaba solo si se tocaba la
       variable a mano.
       Después pasó lo mismo con la SOMBRA del vistazo, que también estaba
       transicionada: al pasar el cursor el rail se abría —ancho, íconos,
       radio, todo— pero la sombra se quedaba en la de reposo. Misma causa,
       mismo desenlace. Por eso aquí no hay ni una `transition`: el rail
       abre y cierra de golpe, que además es lo que hacen los de VS Code y
       Notion.
       Si algún día se quiere animar el plegado, que sea con `transform`
       (no dispara layout y no se puede quedar a medias), nunca con `width`
       ni con nada que un rerun pueda pillar a media animación. */

    /* ── 2. RAIL DERECHO plegado: lengüeta pegada al borde ─────────────── */
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row {
        /* El ancho del PROPIO rail se declara aquí, aunque su módulo ya
           diga `width: var(--rail-der-w)` y la variable acabe de cambiar.
           No es redundante: medido el 2026-08-15, Chrome no vuelve a
           resolver ese `width` cuando la variable cambia por una regla
           condicionada con `:has()` — el rail se quedaba en su ancho
           mientras TODO lo demás que deriva de la misma variable sí se
           movía. Se recuperaba con solo tocar la variable a mano en la
           consola, así que es invalidación perezosa, no cascada.
           La regla práctica: lo que cambia por `:has()` se DECLARA en la
           regla del `:has()`. Heredar una variable sirve para lo que está
           lejos (el padding); para el elemento que la propia regla toca,
           ponlo directo. */
        width: var(--rail-min) !important;
        overflow: hidden !important;
        /* Sin esto la lengüeta mide lo que mide el pestillo (~34px de alto)
           y hay que cazarla con el cursor. 132px la vuelven una tira
           cómoda de apuntar, que es la mitad del gesto de "vistazo". */
        min-height: 132px !important;
    }
    /* Los ítems se ESCONDEN, no se dejan de dibujar: si no se renderizaran,
       Streamlit perdería el estado de sus botones (CLAUDE.md § Streamlit).
       Con `display:none` siguen existiendo. */
    :root:has(style.rail-der-plegado) .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
        display: none !important;
    }

    /* VISTAZO — cursor sobre la lengüeta. El rail es `position:fixed`, así
       que ensancharlo lo SUPERPONE sobre la tarjeta en vez de empujarla:
       mirar no mueve nada y no cuesta un rerun. La sombra es lo que dice
       "esto está flotando encima", no adherido. */
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row:hover {
        width: var(--rail-der-full) !important;
        box-shadow: -6px 0 22px rgba(16, 16, 20, 0.16) !important;
    }
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row:hover
        .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
        display: flex !important;
    }

    /* ── 3. EL PESTILLO ─────────────────────────────────────────────────
       Botón mínimo: chevron gris sobre nada. Se acota a su PROPIA key
       (regla #6): el rail estila todo lo que cuelgue de `graf_tipo_chips`,
       así que el pestillo se llama distinto y vive fuera de ese contenedor
       a propósito — si heredara esos estilos sería un ítem más de la
       lista. */
    .st-key-rail_pestillo {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
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
    .st-key-compras_tabs_row:hover .st-key-rail_pestillo button {
        opacity: 1 !important;
    }
    .st-key-rail_pestillo button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
        opacity: 1 !important;
    }
    .st-key-rail_pestillo button [data-testid="stIconMaterial"],
    .st-key-rail_pestillo button p > span {
        font-size: 18px !important;
        line-height: 1 !important;
    }
    .st-key-rail_pestillo button p {
        margin: 0 !important;
        line-height: 1 !important;
    }
    /* Plegado, el pestillo ES la lengüeta: se estira a lo alto para que
       toda la tira sea clicable, no solo 22px en la punta. */
    :root:has(style.rail-der-plegado) .st-key-rail_pestillo button {
        height: 116px !important;
        opacity: 0.8 !important;
    }
    :root:has(style.rail-der-plegado) .st-key-compras_tabs_row:hover .st-key-rail_pestillo button {
        height: 22px !important;
    }

    /* ── 4. MÓVIL — no hay pestillo ─────────────────────────────────────
       El rail ya se transforma en fila horizontal scrollable: no ocupa
       ancho, así que no hay nada que recuperar plegándolo. Además el
       "vistazo" por hover no existe en pantalla táctil. Se fuerza el
       estado desplegado por si el usuario dejó el rail plegado en
       escritorio y abre en el teléfono. */
    @media (max-width: 900px) {
        .st-key-rail_pestillo { display: none !important; }
        :root:has(style.rail-der-plegado) { --rail-der-w: var(--rail-der-full); }
        /* Hay que deshacer el `width` DIRECTO del punto 2, no solo la
           variable: si no, el rail plegado en escritorio llega al móvil
           convertido en una lengüeta de 24px. */
        :root:has(style.rail-der-plegado) .st-key-compras_tabs_row {
            width: 100% !important;
            min-height: 0 !important;
        }
        :root:has(style.rail-der-plegado) .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
            display: flex !important;
        }
    }
"""
