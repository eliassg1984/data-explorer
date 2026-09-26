"""estilos._28_arbol — El rail en ÁRBOL y la franja de contexto (2026-09-19).

La «opción 5» del prototipo, elegida por el usuario, y la regla #472. Desde
901px el cromo de la app se reparte como en cualquier app con barra lateral:

  · AL COSTADO, A DÓNDE IR. Una columna siempre visible con los reportes y,
    debajo de todos, las vistas del activo (desde el 2026-09-26; hasta ese
    día colgaban de su reporte, ver abajo). No cambia de contenido al bajar.
  · ARRIBA, DÓNDE ESTÁS. Una franja de 44px con el reporte, la vista en
    pantalla y sus KPIs, y a la derecha la fecha, Filtros, la hora del dato y
    Actualizar. NO ESTÁ EN REPOSO (2026-09-19, a pedido): deja una tira de
    `--franja-rep-reserva` (12px) contra el borde de arriba y aparece —con
    sus controles— cuando el cursor la toca, igual que la columna. Por eso el
    contenido arranca en 20px (`--cab-offset-contenido`) y no en 52.

Hasta hoy las dos eran CAPAS que aparecían con el cursor (`_26_rails_scroll`),
la columna alternaba Reportes/Vistas con el scroll, y la franja repetía los
reportes para compensar ese cruce. Todo eso sigue vivo para el tramo de 769 a
900px; este módulo es sólo para 901px en adelante.

EL ÁRBOL SON DOS CONTENEDORES, NO UNO
-------------------------------------
Los reportes los dibuja `navegacion.py` ANTES del `@st.fragment` del
contenido (un clic tiene que recalcular `df_f`, ver su docstring) y las
vistas las dibuja `graficos/base.py::_render_rail` ADENTRO. No se pueden
poner en un mismo contenedor, así que el de las vistas se ubica por
GEOMETRÍA: debajo de la última fila de reportes, que `navegacion.py` cuenta
y publica como `--arbol-filas` (un grupo es una fila; el Inspector, cuando
se muestra, suma una).

Hasta el 2026-09-26 las vistas colgaban de SU reporte: la fila activa se
estiraba lo que ellas medían (`--arbol-activa`, `--arbol-n`,
`--arbol-seps`) y la lista se montaba en ese hueco. Costaba dos cosas, las
dos con la columna PLEGADA, que es como se la ve casi siempre: el hueco no
se podía cerrar —al desplegar, las vistas se habrían metido en el medio y
empujado a los reportes de abajo, ver #465 más abajo—, así que para que no
pareciera un error lo llenaba un punto por vista (#495), que «no comunica
mucho»; y los íconos de abajo cambiaban de altura con cada reporte — con
Compras activo, el de Ventas estaba en y=474, y al clickearlo saltaba a
230. Debajo de todos, cada ícono tiene su sitio fijo y la columna plegada
es sólo íconos. Es el esquema de Figma: arriba las páginas, abajo las capas
de la abierta. Regla #535.

PLEGADO, ASOMADO Y FIJADO
-------------------------
  · PLEGADO (el default): la columna es una tira de íconos de
    `--rail-plegado-w` y el contenido le reserva sólo eso. Las vistas no se
    ven.
  · ASOMADO: con el cursor en la columna (`<html data-capa-col>`, lo marca
    `navegacion.py::_SCRIPT_CAPAS` con la lista `DISPARADORES_COLUMNA`) el
    árbol se despliega a `--rail-der-w` ENCIMA del contenido, con sombra, y
    el contenido no se mueve. Entra con una pausa de 180ms para que cruzar la
    columna camino a otra cosa no la abra.
  · FIJADO: el pestillo (`rail_pestillo_abierto`) lo deja desplegado y ahí
    sí el contenido le reserva su ancho (`_00_base.py`, `--rail-reserva`).

Y LO QUE ABRE UNA CAPA NO PUEDE MOVERSE AL ABRIRSE (#465): los íconos de los
reportes y el pestillo están en la MISMA x en los tres estados (su centro en
`--rail-plegado-w / 2`). Desplegar sólo agrega a la derecha —el texto, los
KPIs— y ABAJO DE TODO —las vistas—; lo que está bajo el cursor queda donde
estaba. Por eso las vistas no pueden volver a colgar de su reporte con la
columna plegada cerrada sobre ellas: al desplegar se meterían entre los
reportes y el ícono que ibas a clickear se correría de debajo del cursor.

COMO SE VERIFICA
----------------
Con el navegador automatizado las transiciones no avanzan (#353): para medir
anchos hay que apagarlas antes (`* { transition: none !important }` desde la
consola). Y ojo con MEDIR MIENTRAS LA APP CORRE: con un rerun en curso la
columna devolvía 1366px de ancho —su valor de antes de la transición— con la
regla aplicando perfecto; medir con el indicador de «corriendo» apagado. La
lista se verifica midiendo que su tope quede debajo del borde de abajo de la
ÚLTIMA fila de reportes y que cada ícono de reporte mida la misma `top` sea
cual sea el activo. El estado desplegado se prueba con el PESTILLO: forzar
`data-capa-col` por consola no dura (regla #495).
"""

CSS = """
    /* ── Abajo de 901px no hay árbol: el pestillo no tiene qué plegar ────
       Entre 769 y 900 la columna sigue siendo la capa de siempre y en el
       celular es la tira de chips; en ninguna de las dos se pliega. La
       franja de contexto tampoco se ve: ahí la franja de reportes sigue
       siendo la botonera de siempre. `display: none` sobre la caja de
       adentro, no sobre su envoltorio: el envoltorio sigue cobrando el gap
       de la raíz igual que antes, así que la primera tarjeta no se mueve. */
    @media (max-width: 900px) {
        .st-key-rail_pestillo_abierto,
        .st-key-rail_pestillo_plegado {
            display: none !important;
        }
        .st-key-nav_franja_rep [data-testid="stElementContainer"]:has(.barra-ctx) {
            display: none !important;
        }
    }

    /* DEFENSA ANTI-TOOLTIP-FANTASMA en las VISTAS: se fue con el `help=`
       el 2026-09-21 (regla #482). Mientras el KPI viajó en `help=`
       (2026-09-19 a 2026-09-21) Streamlit envolvía el botón con su tooltip
       y dejaba una COPIA suelta en el mismo `stButton` —la trampa de la
       regla #164—, y hacía falta un `> div + div { display: none }`. Hoy
       los botones de la columna no llevan `help=`: hay un solo `div` y el
       selector no elegiría nada. Si algún día vuelve un `help=` acá, el
       ícono duplicado es lo primero que se ve. */

    @media screen and (min-width: 901px) {

    /* ── Los altos del árbol ─────────────────────────────────────────── */
    :root {
        --fila-rep: 36px;
        --fila-vis: 30px;
        /* El alto de fila con el que `_20_compras_rail.py` centra el punto
           de una vista. Acá la fila es la de una vista; entre 769 y 900px
           lo define `_26_rails_scroll.py` con el suyo. */
        --rail-fila-alto: var(--fila-vis);
        --arbol-cab: 6px;            /* aire entre la cabecera y el primer reporte */
        --icono-x: calc(var(--rail-plegado-w) / 2);   /* centro de todo ícono de la columna */
    }
    /* Pantallas bajas: Ventas son 6 reportes + 10 vistas, y a 36/30 la
       columna desplegada llega hasta y=619. Con esto, hasta y=565 (medido
       a 1366×768 y 1366×660, 2026-09-26, más los 6px que sumó el rótulo
       «Vistas de» al agrandarse ese mismo día). */
    @media (max-height: 700px) {
        :root {
            --fila-rep: 32px;
            --fila-vis: 27px;
        }
    }

    /* ══ LA COLUMNA ═════════════════════════════════════════════════════
       `compras_tabs_row` es el fondo y la zona de cursor de la columna
       ENTERA —de arriba abajo, no sólo donde hay filas—, así que pasar por
       el hueco de abajo también la despliega. */
    .st-key-compras_tabs_row {
        position: fixed !important;
        top: 0 !important;
        bottom: 0 !important;
        left: 0 !important;
        right: auto !important;
        width: var(--rail-plegado-w) !important;
        height: auto !important;
        max-height: none !important;
        margin: 0 !important;
        padding: calc(var(--franja-rep-alto) + var(--arbol-cab)) 0 12px 0 !important;
        box-sizing: border-box !important;
        border: none !important;
        border-right: 1px solid var(--border) !important;
        border-radius: 0 !important;
        background: var(--rail-fondo) !important;
        background-clip: border-box !important;
        box-shadow: none !important;
        overflow: hidden !important;
        opacity: 1 !important;
        visibility: visible !important;
        clip-path: none !important;
        pointer-events: auto !important;
        z-index: 1000010 !important;
        transition: width 160ms cubic-bezier(.4, 0, .2, 1),
                    box-shadow 160ms linear !important;
    }
    /* Las vistas: mismo ancho que la columna en los tres estados, debajo de
       la ÚLTIMA fila de reportes (ver el docstring). El 6 del `var()` es la
       cuenta de hoy: si esta regla llegara a Cloud antes que el
       `navegacion.py` que publica la variable (regla #357), la lista igual
       caería en su sitio en vez de encima del primer reporte. */
    .st-key-nav_rail_lateral {
        position: fixed !important;
        top: calc(var(--franja-rep-alto) + var(--arbol-cab)
                  + var(--arbol-filas, 6) * var(--fila-rep)) !important;
        bottom: auto !important;
        left: 0 !important;
        width: var(--rail-plegado-w) !important;
        height: auto !important;
        max-height: none !important;
        margin: 0 !important;
        padding: 2px 0 6px 0 !important;
        box-sizing: border-box !important;
        border: none !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        /* VISIBLE y no `hidden` desde el 2026-09-21 (regla #482): el panel
           del KPI de una vista sale por la derecha de la columna y un
           recorte acá se lo comía. Nada más se sale: el que clipea el
           nombre con la columna plegada es el `overflow: hidden` de cada
           `<button>`, no éste. */
        overflow: visible !important;
        /* PLEGADA LA COLUMNA, LA LISTA NO ESTÁ (2026-09-26, regla #535):
           ni se ve, ni recibe el cursor, ni el foco — `visibility` saca de
           las tres cosas, y el cursor cae en `compras_tabs_row`, que es la
           zona que despliega. `visibility` no interpola: se conmuta con el
           fundido. Al abrir entra con el ancho —con su misma pausa de 180ms
           si abre el cursor, ver ASOMADO más abajo—; al cerrar se esconde
           cuando terminó de apagarse. Sus hijos la heredan por la regla de
           `visibility: inherit` de más abajo. */
        opacity: 0 !important;
        visibility: hidden !important;
        clip-path: none !important;
        pointer-events: auto !important;
        z-index: 1000011 !important;
        transition: width 160ms cubic-bezier(.4, 0, .2, 1),
                    opacity 120ms linear,
                    visibility 0s linear 120ms !important;
    }
    /* La cabecera de la columna: el rótulo «Reportes». Recibe el cursor
       (está en `DISPARADORES_COLUMNA`) y su borde de abajo sigue la línea
       de la franja de al lado, así las dos cabeceras se leen como una. */
    .st-key-rail_rotulo_rep {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: var(--rail-plegado-w) !important;
        height: var(--franja-rep-alto) !important;
        margin: 0 !important;
        padding: 0 0 0 calc(var(--icono-x) + 22px) !important;
        box-sizing: border-box !important;
        border: none !important;
        border-bottom: 1px solid var(--border) !important;
        border-radius: 0 !important;
        background: transparent !important;
        overflow: hidden !important;
        justify-content: center !important;
        align-items: flex-start !important;
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
        z-index: 1000012 !important;
        transition: width 160ms cubic-bezier(.4, 0, .2, 1) !important;
    }
    .st-key-rail_rotulo_rep .rail-rotulo {
        display: block !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        white-space: nowrap !important;
        opacity: 0;
        transition: opacity 120ms linear;
    }
    /* El pestillo, arriba a la izquierda y QUIETO: su centro es el de los
       íconos de abajo, en los tres estados (ver el docstring). */
    .st-key-rail_pestillo_abierto,
    .st-key-rail_pestillo_plegado {
        position: fixed !important;
        top: calc((var(--franja-rep-alto) - 28px) / 2) !important;
        left: calc(var(--icono-x) - 14px) !important;
        width: 28px !important;
        height: 28px !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        z-index: 1000013 !important;
    }
    .st-key-rail_pestillo_abierto button,
    .st-key-rail_pestillo_plegado button {
        width: 28px !important;
        height: 28px !important;
        min-height: 28px !important;
        border: none !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
    }
    .st-key-rail_pestillo_abierto button:hover,
    .st-key-rail_pestillo_plegado button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }

    /* ── Desplegado: FIJADO o ASOMADO ───────────────────────────────────
       Fijado lo dice la key del pestillo; asomado, la marca del cursor.
       Los dos sólo agregan: a la derecha, y abajo de todo las vistas. */
    :root:has(.st-key-rail_pestillo_abierto) :is(.st-key-compras_tabs_row,
        .st-key-nav_rail_lateral, .st-key-rail_rotulo_rep),
    :root[data-capa-col] :is(.st-key-compras_tabs_row,
        .st-key-nav_rail_lateral, .st-key-rail_rotulo_rep) {
        width: var(--rail-der-w) !important;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-nav_rail_lateral,
    :root[data-capa-col] .st-key-nav_rail_lateral {
        opacity: 1 !important;
        visibility: visible !important;
        transition: width 160ms cubic-bezier(.4, 0, .2, 1),
                    opacity 120ms linear,
                    visibility 0s linear 0s !important;
    }
    /* Asomado encima del contenido: la sombra dice que está por ENCIMA, y
       la pausa de entrada (sólo al entrar: la salida usa la transición de
       reposo, sin pausa) evita que cruzar la columna la despliegue. */
    :root[data-capa-col]:has(.st-key-rail_pestillo_plegado) :is(.st-key-compras_tabs_row,
        .st-key-nav_rail_lateral, .st-key-rail_rotulo_rep) {
        transition-delay: 180ms !important;
    }
    :root[data-capa-col]:has(.st-key-rail_pestillo_plegado) .st-key-compras_tabs_row {
        box-shadow: var(--sombra-capa) !important;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-rail_rotulo_rep .rail-rotulo,
    :root[data-capa-col] .st-key-rail_rotulo_rep .rail-rotulo {
        opacity: 1;
        transition-delay: 120ms;
    }

    /* ══ LAS FILAS DE REPORTES ═════════════════════════════════════════ */
    .st-key-graf_tipo_chips > div {
        border-bottom: none !important;
    }
    /* Todas del mismo alto, la activa también: desde el 2026-09-26 ninguna
       se estira para alojar a sus vistas (van debajo de todas, #535), así
       que cada ícono tiene la misma `top` sea cual sea el reporte activo. */
    .st-key-graf_tipo_chips [class*="st-key-navitem_"] {
        height: var(--fila-rep) !important;
        flex: 0 0 auto !important;
        overflow: visible !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] button {
        height: var(--fila-rep) !important;
        min-height: 0 !important;
        width: calc(100% - 12px) !important;
        margin: 0 6px !important;
        /* El centro del ícono en `--icono-x` (34): 6 de margen + 20 de
           relleno + 8, la mitad de la caja de 16px en la que Streamlit mete
           al ícono (el glifo mide 20 y desborda 2 por lado, medido). Así el
           ícono no se mueve al desplegar. */
        padding: 0 10px 0 calc(var(--icono-x) - 14px) !important;
        gap: 10px !important;
        justify-content: flex-start !important;
        border: none !important;
        border-left: none !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
        overflow: hidden !important;
    }
    /* El ícono de un REPORTE, 21px y del color del texto de la fila. Es el
       único ícono que se ve en la columna: el de una vista no se dibuja
       (más abajo). */
    .st-key-graf_tipo_chips [data-testid="stButton"] button [data-testid="stIconMaterial"] {
        font-size: 21px !important;
        width: 21px !important;
        color: inherit !important;
        flex: 0 0 auto !important;
        margin: 0 !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] button p {
        font-size: 13.5px !important;
        white-space: nowrap !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {
        opacity: 0;
        transition: opacity 120ms linear;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    /* El activo: la píldora lavanda, plegada Y desplegada. Plegada es lo
       único que lo distingue en una tira de íconos; desplegada es lo que
       lo ata a la lista de abajo, que se titula con su nombre. Hasta el
       2026-09-26 desplegado iba sin relleno, porque era la RAÍZ de sus
       vistas —colgaban justo debajo— y el relleno quedaba para la vista en
       pantalla; con la lista al pie, sin él había que buscarlo (#535). */
    .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"] {
        background: var(--accent-light) !important;
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
        border-left: none !important;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-graf_tipo_chips [data-testid="stButton"] button [data-testid="stMarkdownContainer"],
    :root[data-capa-col] .st-key-graf_tipo_chips [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {
        opacity: 1;
        transition-delay: 120ms;
    }
    /* Los KPIs de cada reporte, en la esquina de su fila. El del ACTIVO no:
       ése está en la franja de arriba, con todos los suyos. Selectores con
       `compras_tabs_row` adelante porque `navegacion.py::_CSS_KPIS` se
       inyecta DESPUÉS que `estilos/` con la misma especificidad. */
    .st-key-compras_tabs_row .st-key-graf_tipo_chips .nav-kpis-valores {
        right: 14px !important;
        opacity: 0;
        transition: opacity 120ms linear;
    }
    .st-key-compras_tabs_row .st-key-graf_tipo_chips .nav-kpis-activo {
        display: none !important;
    }
    .st-key-compras_tabs_row .st-key-graf_tipo_chips .nav-kpis-primario {
        font-size: 12px !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        font-variant-numeric: tabular-nums;
    }
    .st-key-compras_tabs_row .st-key-graf_tipo_chips .nav-kpis-primario.kpi-neg {
        color: var(--danger-text) !important;
    }
    .st-key-compras_tabs_row .st-key-graf_tipo_chips .nav-kpis-secundario {
        display: none !important;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-compras_tabs_row .st-key-graf_tipo_chips .nav-kpis-valores,
    :root[data-capa-col] .st-key-compras_tabs_row .st-key-graf_tipo_chips .nav-kpis-valores {
        opacity: 1;
        transition-delay: 120ms;
    }

    /* ══ LAS VISTAS, AL PIE DE LOS REPORTES ═══════════════════════════════
       Sólo existen con la columna desplegada —plegada se esconde el
       contenedor entero, ver más arriba—, así que acá cada regla tiene UN
       estado. Hasta el 2026-09-26 cada una tenía dos: la plegada (el ícono
       de la vista, y desde el 2026-09-22 un punto por vista, regla #495) y
       su gemela desplegada, con `:root:has(.st-key-rail_pestillo_abierto)`
       y `:root[data-capa-col]` adelante. Regla #535.

       LOS HIJOS SIGUEN AL CONTENEDOR. `visibility` se hereda, pero
       Streamlit la re-declara en el wrapper que mete adentro de cada
       `stMarkdown` (una clase de emotion que no se puede nombrar): sin
       esto, con la lista escondida su rótulo se seguiría leyendo y
       encontrando con Ctrl+F. Es la regla «LOS HIJOS SIGUEN AL RAIL» que
       `_26_rails_scroll.py` pone entre 769 y 900px, y como aquélla es un
       descendiente amplio a propósito: tiene que alcanzar también a lo que
       se agregue después. */
    .st-key-nav_rail_lateral * {
        visibility: inherit;
    }
    .st-key-nav_rail_lateral [data-testid="stVerticalBlock"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        width: 100% !important;
    }
    .st-key-nav_rail_lateral [data-testid="stElementContainer"],
    .st-key-nav_rail_lateral [data-testid="stButton"],
    .st-key-nav_rail_lateral [data-testid="stMarkdown"],
    .st-key-nav_rail_lateral [data-testid="stMarkdownContainer"] {
        width: 100% !important;
        margin: 0 !important;
        border: none !important;
    }
    /* EL RÓTULO: «Vistas de <reporte>», con la línea que separa la lista de
       los reportes. Es la `.rail-cab` de `_render_rail` —entre 769 y 900px,
       la cabecera de la columna cuando cruza a Vistas— y acá dice de quién
       son las vistas, que en el árbol colgado lo decía la sangría. El texto
       va en la x del rótulo «Reportes» de arriba (`--icono-x` + 22px), pero
       NO con su peso: nació igual a él (12px, 500, gris) y se pidió «algo
       más notorio» el mismo día — aquél rotula la columna, éste titula la
       sección en la que estás. El nombre del reporte va en negrita y en el
       color de su píldora de arriba, que es lo que lo ata a ella sin tener
       que buscarla; «Vistas de», en gris y sin negrita, para que el ojo
       caiga en el nombre. «Vistas de» va en un `::before` y no en Python
       porque entre 769 y 900 la misma `.rail-cab-nom` es el nombre a
       secas. */
    .st-key-nav_rail_lateral .rail-cab {
        display: block !important;
        margin: 6px 16px 4px 16px !important;
        padding: 12px 0 4px calc(var(--icono-x) + 22px - 16px) !important;
        border-top: 1px solid var(--border) !important;
    }
    .st-key-nav_rail_lateral .rail-cab-nom {
        display: block !important;
        /* 13 y no 13.5 (el de los nombres de reporte): con 13.5, «Vistas
           de Ajuste de Inventario» pedía 178px de los 176 que hay y salía
           cortado con «…»; con 13 mide 167 (medido). */
        font-size: 13px !important;
        font-weight: 600 !important;
        line-height: 18px !important;
        color: var(--accent-deep) !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .st-key-nav_rail_lateral .rail-cab-nom::before {
        content: "Vistas de ";
        font-weight: 500;
        color: var(--text-secondary);
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button {
        height: var(--fila-vis) !important;
        min-height: 0 !important;
        width: calc(100% - 12px) !important;
        margin: 0 6px !important;
        /* SANGRADAS: el nombre de una vista empieza 18px más adentro que el
           de un reporte (x=68 contra 50, medido), así las dos listas se leen
           como dos niveles aunque ya no cuelguen una de la otra. La sangría
           la dan este relleno y la caja del ícono de la vista, que no se
           dibuja pero guarda su lugar (más abajo). */
        padding: 0 10px 0 calc(var(--icono-x) - 14px + 10px) !important;
        gap: 10px !important;
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        border: none !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
        box-shadow: none !important;
        font-weight: 400 !important;
        overflow: hidden !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button > div,
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {
        display: block !important;
        width: auto !important;
        max-width: 100% !important;
    }
    /* El ícono de la vista no se ve: chico y sin rótulo no decía qué vista
       era (2026-09-22, regla #495). Guarda su lugar —es parte de la sangría,
       y en su franja se monta la barra de la vista en pantalla—, así que va
       con `opacity` y no con `display`. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stIconMaterial"] {
        font-size: 15px !important;
        width: 15px !important;
        margin: 0 !important;
        flex: 0 0 auto !important;
        opacity: 0 !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button p {
        margin: 0 !important;
        font-size: 13px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {
        margin-left: 8px !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    /* La vista EN PANTALLA la marca el temporizador de `_render_rail` con
       una clase: la píldora, y una barra de acento delante del nombre. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla {
        background: var(--accent-light) !important;
        color: var(--accent-deep) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla::before {
        content: "";
        position: absolute;
        left: calc(var(--icono-x) - 6px - 1px + 10px);
        top: 6px;
        bottom: 6px;
        width: 2px;
        border-radius: 2px;
        background: var(--accent);
        pointer-events: none;
    }
    /* Entre la pila y un destino aparte (`_render_rail`), a la altura de
       los nombres. */
    .st-key-nav_rail_lateral .nav-rail-lat-sep {
        height: 1px !important;
        margin: 6px 16px 6px calc(var(--icono-x) + 16px) !important;
        border: none !important;
        background: var(--border) !important;
    }
    /* (El punto del KPI de cada vista, `railkpi_<slug>` —regla #482—, tenía
       acá su regla para esconderse con la columna plegada. Ya no la
       necesita: plegada se va con la lista entera.) */

    /* ══ LA FRANJA DE CONTEXTO ══════════════════════════════════════════
       Arranca donde termina lo que la columna reserva y va hasta el borde:
       asomado, el árbol la tapa por la izquierda como tapa a las tarjetas. */
    .st-key-nav_franja_rep {
        position: fixed !important;
        top: 0 !important;
        left: var(--rail-reserva) !important;
        right: 0 !important;
        width: auto !important;
        height: var(--franja-rep-alto) !important;
        min-height: var(--franja-rep-alto) !important;
        margin: 0 !important;
        padding: 0 var(--barra-der) 0 16px !important;
        box-sizing: border-box !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 0 !important;
        background: var(--bg-card) !important;
        border-bottom: 1px solid var(--border) !important;
        overflow: hidden !important;
        z-index: 1000001 !important;
        /* ── NO ESTÁ: APARECE CON EL CURSOR (2026-09-19, a pedido) ─────
           Mismo mecanismo que tenía antes del árbol y el mismo motivo para
           no usar `visibility: hidden`: un elemento que el navegador no
           hit-testea no puede estar `:hover` NUNCA, así que no tendría cómo
           volver. Se queda con `opacity: 0` y un `clip-path` que la recorta
           a la tira de `--franja-rep-reserva` — el recorte recorta también
           el hit-testing, así que en reposo sólo despiertan esos 12px de
           arriba y lo que quedó debajo (la primera tarjeta, que subió 32px)
           sigue recibiendo sus clics. El recorte se suelta AL INSTANTE al
           abrir y vuelve al FINAL del fundido de salida. */
        opacity: 0;
        clip-path: inset(0 0 calc(100% - var(--franja-rep-reserva)) 0);
        transition: opacity 160ms linear 220ms,
                    clip-path 0s linear 380ms;
    }
    :root[data-capa-cab] .st-key-nav_franja_rep {
        opacity: 1;
        clip-path: inset(0);
        /* Al ENTRAR no hay espera: aparecer tarde se siente roto. */
        transition: opacity 160ms linear,
                    clip-path 0s linear 0s;
    }
    /* Y LOS CONTROLES CON ELLA. Son fijos y viven fuera de la franja (cada
       uno lo dibuja un sitio distinto), así que no heredan su opacidad: se
       apagan y encienden con la misma marca. El pill de fecha va acotado a
       `fila_ajuste_top` — la misma key la usa Compras › Documentos SUNAT
       DENTRO de su tarjeta, donde no es cromo sino el filtro de la tabla
       (regla #457). El sello ya es `pointer-events: none`. */
    .st-key-chips_ajuste_tabla,
    .st-key-fila_ajuste_top .st-key-fecha_ajuste_pill,
    .st-key-fecha_corte_nav,
    .st-key-rail_refresh,
    #sello-actualizacion {
        opacity: 0;
        pointer-events: none;
        transition: opacity 160ms linear 220ms;
    }
    :root[data-capa-cab] :is(.st-key-chips_ajuste_tabla,
        .st-key-fila_ajuste_top .st-key-fecha_ajuste_pill,
        .st-key-fecha_corte_nav, .st-key-rail_refresh,
        #sello-actualizacion) {
        opacity: 1;
        pointer-events: auto;
        transition: opacity 160ms linear;
    }
    /* La botonera de reportes queda para 769-900px (ver el docstring de
       `navegacion.py`, «FRANJA DE REPORTES»). */
    .st-key-nav_franja_rep [data-testid="stButton"] {
        display: none !important;
    }
    .st-key-nav_franja_rep [data-testid="stElementContainer"]:has(.barra-ctx) {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
        height: 100% !important;
        display: flex !important;
        align-items: center !important;
    }
    .st-key-nav_franja_rep [data-testid="stMarkdown"],
    .st-key-nav_franja_rep [data-testid="stMarkdownContainer"],
    .st-key-nav_franja_rep [data-testid="stMarkdown"] > div {
        width: 100% !important;
        min-width: 0 !important;
        margin: 0 !important;
    }
    .barra-ctx {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
        height: var(--franja-rep-alto);
        white-space: nowrap;
        overflow: hidden;
    }
    .barra-ico {
        font-family: "Material Symbols Rounded";
        font-feature-settings: "liga";
        font-size: 20px;
        line-height: 1;
        color: var(--accent);
        flex: 0 0 auto;
    }
    .barra-nom {
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        flex: 0 0 auto;
    }
    /* La vista la escribe el temporizador; la flecha sólo existe con texto. */
    .barra-vista {
        font-size: 14px;
        color: var(--text-secondary);
        max-width: 240px;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 0 0 auto;
    }
    .barra-vista:not(:empty)::before {
        content: "›";
        margin-right: 8px;
        color: var(--text-muted);
    }
    /* Los KPIs: si no entran, se VAN enteros en vez de cortarse a la mitad.
       Es una fila con `wrap` y alto fijo: lo que no cabe baja a un segundo
       renglón que el `overflow` no deja ver. */
    .barra-kpis {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        column-gap: 18px;
        height: var(--franja-rep-alto);
        min-width: 0;
        flex: 0 1 auto;
        overflow: hidden;
        margin-left: 6px;
        padding-left: 16px;
        position: relative;
    }
    .barra-kpis::before {
        content: "";
        position: absolute;
        left: 0;
        top: 13px;
        bottom: 13px;
        width: 1px;
        background: var(--border);
    }
    .barra-kpi,
    .barra-par {
        height: var(--franja-rep-alto);
        display: flex;
        align-items: center;
        flex: 0 0 auto;
        font-variant-numeric: tabular-nums;
    }
    .barra-kpi-val {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-primary);
    }
    .barra-kpi-sec {
        font-size: 12px;
        color: var(--text-muted);
        margin-left: 6px;
    }
    .barra-par {
        flex-direction: column;
        align-items: flex-start;
        justify-content: center;
        line-height: 1.1;
        gap: 2px;
    }
    .barra-par-rot {
        font-style: normal;
        font-size: 9.5px;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--text-muted);
    }
    .barra-par-val {
        font-size: 13px;
        font-weight: 600;
        color: var(--accent-deep);
    }
    .barra-ctx .kpi-neg {
        color: var(--danger-text);
    }

    /* ── Lo que vive a la DERECHA de la franja ─────────────────────────
       Cuatro piezas fijas que ya existían (Filtros, Actualizar, la fecha y
       la hora del dato) y que se ubican con `right`, porque cada una la
       dibuja un sitio distinto. Van de derecha a izquierda, cada una a la
       izquierda de la anterior; lo que falta en un reporte no reserva nada:
         --barra-f      Filtros más 8 de aire, o el margen de 16 si no hay;
         --barra-fecha  el pill de la franja (210 + 8), si este reporte lo
                        dibuja ahí — Compras no (lo lleva cada tarjeta);
         --barra-corte  el stepper del corte (176 + 8), si hay uno;
         --barra-sello  lo que se le reserva a la hora del dato, que mide su
                        texto: con rótulo 230, sin él 110, oculta 0.
       `--barra-der` es la suma: el relleno derecho de la franja, para que el
       contexto de la izquierda se recorte ANTES de meterse abajo de ellas.
       Filtros, la fecha, el stepper y la hora viven en `_50_fecha.py`, junto
       a sus dueños; Actualizar, que es la acción de esta franja, acá abajo. */
    :root {
        --barra-f: 16px;
        --barra-fecha: 0px;
        --barra-corte: 0px;
        --barra-sello: 230px;
        --barra-der: calc(var(--barra-f) + 96px + 8px + var(--barra-fecha)
                          + var(--barra-corte) + var(--barra-sello) + 16px);
    }
    :root:has(.st-key-chips_ajuste_tabla) {
        --barra-f: calc(var(--filtros-ancho) + 8px);
    }
    :root:has(.st-key-chipwrap_filtros_on) {
        --barra-f: calc(var(--filtros-ancho-cuenta) + 8px);
    }
    :root:has(.st-key-fila_ajuste_top .st-key-fecha_ajuste_pill) {
        --barra-fecha: 218px;
    }
    @media (min-width: 1490px) {
        :root:has(.st-key-fecha_corte_nav) {
            --barra-corte: 184px;
        }
    }
    @media (max-width: 1499px) {
        :root { --barra-sello: 110px; }
    }
    @media (max-width: 1199px) {
        :root { --barra-sello: 0px; }
    }

    /* Actualizar: el primero desde la derecha después de Filtros, centrado
       en los 44. Su caja (96x30, fija) la declara `_20_compras_rail.py`. */
    .st-key-rail_refresh {
        top: calc((var(--franja-rep-alto) - 30px) / 2) !important;
        right: var(--barra-f) !important;
    }

    /* ══ LOS SEIS CONTENEDORES FANTASMA DEJAN DE COBRAR GAP ═════════════
       Entre el borde de arriba y la primera tarjeta hay seis bloques que no
       dibujan NADA en el flujo —el rótulo de la columna, el pestillo, la
       franja, los KPIs, el rail y la fila de la fecha: todos `position:
       fixed`— pero Streamlit los envuelve en un `stLayoutWrapper` y el
       bloque vertical le cobra a cada uno sus 16px de `gap`. Son 96px de
       aire, y hasta hoy cada reporte los compensaba con un jalón negativo
       propio, medido a mano y distinto en cada uno (-120 en Compras, -48 en
       las tarjetas, -68 en Inventario). Por eso unos abrían en y=20 y otros
       en y=68 con el mismo CSS.

       `display: contents` hace desaparecer la CAJA del envoltorio dejando
       vivos a los hijos: sin caja no hay flex item, y sin flex item no hay
       gap. Es el mismo recurso que `_26_rails_scroll.py` ya usa para los
       otros cuatro envoltorios de cromo fijo. Con los 96px fuera, los
       jalones sobran y se anulan acá abajo: la primera tarjeta arranca
       donde dice `--cab-offset-contenido` y en ningún lado hay un número
       medido a ojo.

       Por `data-testid` y NO por `.stLayoutWrapper`: el envoltorio lleva ese
       testid pero su `class` son hashes de emotion, que cambian entre
       versiones de Streamlit.

       Los jalones que compensaban esos 96px se borraron de donde vivían
       (`_20_compras_rail.py` y `_40_ajuste_franja.py`): anularlos desde acá
       habría dejado dos reglas discutiendo por el mismo margen. */
    [data-testid="stLayoutWrapper"]:has(> .st-key-rail_rotulo_rep),
    [data-testid="stLayoutWrapper"]:has(> .st-key-rail_pestillo_abierto),
    [data-testid="stLayoutWrapper"]:has(> .st-key-rail_pestillo_plegado),
    [data-testid="stLayoutWrapper"]:has(> .st-key-nav_franja_rep),
    [data-testid="stLayoutWrapper"]:has(> .st-key-nav_franja_kpis),
    [data-testid="stLayoutWrapper"]:has(> .st-key-compras_tabs_row),
    [data-testid="stLayoutWrapper"]:has(> .st-key-fila_ajuste_top) {
        display: contents !important;
    }

    /* Acá vivía `[class*="_sec_"] { scroll-margin-top: … }`, para que una
       sección a la que se llega por código (`base.py::scroll_a_seccion`) se
       detuviera debajo de la franja. NUNCA APLICÓ: el párrafo de «Los
       jalones…» había quedado FUERA del comentario de arriba, el navegador
       lo leyó como el principio de este selector y descartó la regla
       entera — del 2026-09-19 al 2026-09-25, regla #534. Lo que buscaba lo
       hace ahora el `scroll-padding-top` de `.stMain` (`_27_pila.py`), que
       es el tope donde encajan las vistas (regla #533). Arreglarla en vez
       de borrarla habría SUMADO su margen a ese padding. */

    }
"""
