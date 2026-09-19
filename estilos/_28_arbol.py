"""estilos._28_arbol — El rail en ÁRBOL y la franja de contexto (2026-09-19).

La «opción 5» del prototipo, elegida por el usuario, y la regla #472. Desde
901px el cromo de la app se reparte como en cualquier app con barra lateral:

  · AL COSTADO, A DÓNDE IR. Una columna siempre visible con los reportes y,
    anidadas bajo el activo, sus vistas. No cambia de contenido al bajar.
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
poner en un mismo contenedor, así que el anidado es de GEOMETRÍA:

  · la fila del reporte activo se estira lo que miden sus vistas
    (`--arbol-activa`, que `navegacion.py` le pone sólo a esa fila);
  · el contenedor de las vistas se ubica en ese hueco: debajo de la fila
    número `--arbol-idx` (también de `navegacion.py`);
  · cuánto mide el hueco sale de `--arbol-n` y `--arbol-seps` (filas y
    separadores de la lista, los publica `_render_rail`) por los altos de
    fila de acá. Por eso los altos son `height` y no `min-height`, y por eso
    nada de adentro puede tener margen propio: un píxel de más en una fila
    se acumula y la última vista se monta sobre el reporte siguiente.

PLEGADO, ASOMADO Y FIJADO
-------------------------
  · PLEGADO (el default): la columna es una tira de íconos de
    `--rail-plegado-w` y el contenido le reserva sólo eso.
  · ASOMADO: con el cursor en la columna (`<html data-capa-col>`, lo marca
    `navegacion.py::_SCRIPT_CAPAS` con la lista `DISPARADORES_COLUMNA`) el
    árbol se despliega a `--rail-der-w` ENCIMA del contenido, con sombra, y
    el contenido no se mueve. Entra con una pausa de 180ms para que cruzar la
    columna camino a otra cosa no la abra.
  · FIJADO: el pestillo (`rail_pestillo_abierto`) lo deja desplegado y ahí
    sí el contenido le reserva su ancho (`_00_base.py`, `--rail-reserva`).

Y LO QUE ABRE UNA CAPA NO PUEDE MOVERSE AL ABRIRSE (#465): los íconos de los
reportes, el pestillo y los de las vistas están en la MISMA x en los tres
estados (su centro en `--rail-plegado-w / 2`). Desplegar sólo agrega a la
derecha — el texto, los KPIs, la línea guía —; lo que está bajo el cursor
queda donde estaba.

COMO SE VERIFICA
----------------
Con el navegador automatizado las transiciones no avanzan (#353): para medir
anchos hay que apagarlas antes (`* { transition: none !important }` desde la
consola). Y ojo con MEDIR MIENTRAS LA APP CORRE: con un rerun en curso la
columna devolvía 1366px de ancho —su valor de antes de la transición— con la
regla aplicando perfecto; medir con el indicador de «corriendo» apagado. El hueco del árbol se verifica midiendo que el borde de abajo del
contenedor de vistas coincida con el de la fila activa, en los 6 reportes.
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

    /* DEFENSA ANTI-TOOLTIP-FANTASMA en las VISTAS (2026-09-19): desde que
       llevan su KPI en `help=` (`base.py::_render_rail`), Streamlit envuelve
       el botón con el tooltip y deja una COPIA suelta en el mismo `stButton`,
       la trampa de la regla #164. El que lleva el tooltip es siempre el
       primero; sin `help=` hay un solo `div` y esto no elige nada. Sin
       `@media`: la copia aparece en cualquier ancho. */
    .st-key-nav_rail_lateral [data-testid="stButton"] > div + div {
        display: none !important;
    }

    @media screen and (min-width: 901px) {

    /* ── Los altos del árbol ─────────────────────────────────────────── */
    :root {
        --fila-rep: 36px;
        --fila-vis: 30px;
        --sep-vis: 13px;             /* 1px de línea + 6 de aire arriba y abajo */
        --arbol-cab: 6px;            /* aire entre la cabecera y el primer reporte */
        --arbol-alto: calc(var(--arbol-n, 0) * var(--fila-vis)
                           + var(--arbol-seps, 0) * var(--sep-vis)
                           + min(8px, var(--arbol-n, 0) * 8px));
        --icono-x: calc(var(--rail-plegado-w) / 2);   /* centro de todo ícono de la columna */
    }
    /* Pantallas bajas: Ventas son 6 reportes + 11 vistas, y a 36/30 el
       árbol pide 610px. Con esto entra en ~540. */
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
    /* Las vistas: mismo ancho que la columna en los tres estados, ubicadas
       en el hueco de la fila activa (ver el docstring). */
    .st-key-nav_rail_lateral {
        position: fixed !important;
        top: calc(var(--franja-rep-alto) + var(--arbol-cab)
                  + (var(--arbol-idx, 0) + 1) * var(--fila-rep)) !important;
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
        overflow: hidden !important;
        opacity: 1 !important;
        visibility: visible !important;
        clip-path: none !important;
        pointer-events: auto !important;
        z-index: 1000011 !important;
        transition: width 160ms cubic-bezier(.4, 0, .2, 1) !important;
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
       Los dos sólo agregan a la derecha. */
    :root:has(.st-key-rail_pestillo_abierto) :is(.st-key-compras_tabs_row,
        .st-key-nav_rail_lateral, .st-key-rail_rotulo_rep),
    :root[data-capa-col] :is(.st-key-compras_tabs_row,
        .st-key-nav_rail_lateral, .st-key-rail_rotulo_rep) {
        width: var(--rail-der-w) !important;
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
    .st-key-graf_tipo_chips [class*="st-key-navitem_"] {
        height: calc(var(--fila-rep) + var(--arbol-activa, 0) * var(--arbol-alto)) !important;
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
    /* El ícono de un REPORTE es el grande de la columna: 21px y del color
       del texto principal de la fila. El de una VISTA mide 15 y va apagado
       (más abajo) — plegada la columna, esa diferencia de tamaño y de tono
       es lo único que dice quién cuelga de quién. */
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
    /* El activo, plegado: la píldora lavanda es lo único que lo distingue
       en una tira de íconos. */
    .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"] {
        background: var(--accent-light) !important;
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
        border-left: none !important;
    }
    /* Desplegado, el activo es la RAÍZ de sus vistas: texto fuerte e ícono
       en acento, sin relleno — el relleno queda para la vista en pantalla. */
    :root:has(.st-key-rail_pestillo_abierto) .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"],
    :root[data-capa-col] .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"] {
        background: transparent !important;
        color: var(--text-primary) !important;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"] [data-testid="stIconMaterial"],
    :root[data-capa-col] .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"] [data-testid="stIconMaterial"] {
        color: var(--accent) !important;
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

    /* ══ LAS VISTAS, ANIDADAS ═══════════════════════════════════════════ */
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
    /* La cabecera del rail de vistas era para cuando esta lista reemplazaba
       a la de reportes al bajar; en el árbol el reporte está justo arriba. */
    .st-key-nav_rail_lateral .rail-cab {
        display: none !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button {
        height: var(--fila-vis) !important;
        min-height: 0 !important;
        width: calc(100% - 12px) !important;
        margin: 0 6px !important;
        /* SANGRADAS: el ícono de una vista cae 10px a la derecha del de su
           reporte, colgando de la línea guía. Plegada la columna es el
           gesto que dice «esto es hijo de aquello»; desplegada, el ícono se
           apaga y la sangría la toma el nombre. */
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
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stIconMaterial"] {
        font-size: 15px !important;
        width: 15px !important;
        margin: 0 !important;
        color: var(--text-muted) !important;
        flex: 0 0 auto !important;
        transition: opacity 120ms linear;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button:hover [data-testid="stIconMaterial"],
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla [data-testid="stIconMaterial"] {
        color: inherit !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button p {
        margin: 0 !important;
        font-size: 13px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {
        opacity: 0;
        transition: opacity 120ms linear, margin 160ms linear;
    }
    .st-key-nav_rail_lateral [data-testid="stButton"] button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    /* La vista EN PANTALLA la marca el temporizador de `_render_rail` con
       una clase; plegado es una píldora tenue bajo el ícono. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla {
        background: var(--accent-tint) !important;
        color: var(--accent) !important;
        box-shadow: none !important;
    }
    .st-key-nav_rail_lateral .nav-rail-lat-sep {
        height: 1px !important;
        margin: 6px 16px !important;
        border: none !important;
        background: var(--border) !important;
    }
    /* Desplegado: el ícono se apaga, el nombre entra con 8px de sangría y
       una línea guía cuelga del ícono del reporte padre. */
    /* La línea guía cuelga del ícono del reporte padre y se ve SIEMPRE —
       plegada es la otra mitad de la sangría. */
    .st-key-nav_rail_lateral::before {
        content: "";
        position: absolute;
        left: calc(var(--icono-x) - 1px);
        top: 2px;
        bottom: 6px;
        width: 1px;
        background: var(--border);
        pointer-events: none;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stIconMaterial"],
    :root[data-capa-col] .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stIconMaterial"] {
        opacity: 0;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stMarkdownContainer"],
    :root[data-capa-col] .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {
        opacity: 1;
        margin-left: 8px !important;
        transition-delay: 120ms;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla,
    :root[data-capa-col] .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla {
        background: var(--accent-light) !important;
        color: var(--accent-deep) !important;
        font-weight: 500 !important;
    }
    /* La barra de la vista en pantalla, montada sobre la línea guía. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla::before {
        content: "";
        position: absolute;
        left: calc(var(--icono-x) - 6px - 1px + 10px);
        top: 6px;
        bottom: 6px;
        width: 2px;
        border-radius: 2px;
        background: var(--accent);
        opacity: 0;
        pointer-events: none;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla::before,
    :root[data-capa-col] .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla::before {
        opacity: 1;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-nav_rail_lateral .nav-rail-lat-sep,
    :root[data-capa-col] .st-key-nav_rail_lateral .nav-rail-lat-sep {
        margin-left: calc(var(--icono-x) + 16px) !important;
    }
    /* El punto del semáforo: centrado en la fila, contra el borde derecho. */
    .st-key-nav_rail_lateral button::after {
        top: calc(50% - 3px);
        right: 8px;
    }

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
       versiones de Streamlit. */
    [data-testid="stLayoutWrapper"]:has(> .st-key-rail_rotulo_rep),
    [data-testid="stLayoutWrapper"]:has(> .st-key-rail_pestillo_abierto),
    [data-testid="stLayoutWrapper"]:has(> .st-key-rail_pestillo_plegado),
    [data-testid="stLayoutWrapper"]:has(> .st-key-nav_franja_rep),
    [data-testid="stLayoutWrapper"]:has(> .st-key-nav_franja_kpis),
    [data-testid="stLayoutWrapper"]:has(> .st-key-compras_tabs_row),
    [data-testid="stLayoutWrapper"]:has(> .st-key-fila_ajuste_top) {
        display: contents !important;
    }
       Los jalones que compensaban esos 96px se borraron de donde vivían
       (`_20_compras_rail.py` y `_40_ajuste_franja.py`): anularlos desde acá
       habría dejado dos reglas discutiendo por el mismo margen.

    /* Una sección a la que se llega por código (`base.py::scroll_a_seccion`,
       `scrollIntoView`) se detiene DEBAJO de la franja, no detrás. Las
       secciones de la pila comparten el infijo `_sec_` en su key. */
    [class*="_sec_"] {
        scroll-margin-top: calc(var(--franja-rep-reserva) + 8px);
    }

    }
"""
