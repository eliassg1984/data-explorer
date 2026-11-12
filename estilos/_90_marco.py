"""estilos._90_marco - El marco de la app desde 901px: hoja blanca sobre lavanda.

Regla #764. Elegido sobre el boceto de Mix (combinación C6 + estilo S4,
https://claude.ai/artifact/TdTgy73p7FFQPWHspUs8LR): la franja siempre a la
vista, y lo que se lee —la franja y el contenido— en UNA hoja blanca entera; el
lavanda queda alrededor, con la columna de áreas sin caja propia.

Qué es la hoja: `.stMain`, el que scrollea, con margen. Así recorta lo que pasa
por debajo con sus esquinas, y lo fijo (la columna, la franja, los controles)
sigue ubicándose contra la ventana: por eso la franja y sus controles suman
`--marco-hoja` a su `top` y a su `right`.

Sólo con la columna dibujada (`:root:has(.st-key-compras_tabs_row)`): la pantalla
de entrada no tiene nada a la izquierda y quedaría corrida.

Va casi al final de `_SECCIONES`: gana a las reglas de las tarjetas (`_80_cards`)
y sólo el celular (`_99_movil`) viene después. Las variables viven en
`_00_base.py` y el presupuesto de alto en `graficos/alturas.py`.
"""

from pathlib import Path

CSS = """
    @media (min-width: 901px) {
    :root:has(.st-key-compras_tabs_row),
    :root:has(.st-key-compras_tabs_row) body,
    :root:has(.st-key-compras_tabs_row) [data-testid="stAppViewContainer"] {
        background: var(--marco-fondo) !important;
    }
    :root {
        /* #850: el aire de los COSTADOS de la hoja, aparte del de arriba y abajo
           (`--marco-hoja`). Hasta ese día la hoja arrancaba pegada a la columna
           (12 px del rótulo más ancho, «Producción») y terminaba a 8 px de la
           ventana; con 8 más a la izquierda y 16 a la derecha quedan 20 y 16,
           que se ven parejos porque la columna no tiene caja. La ruta usa los
           mismos dos bordes. Boceto: https://claude.ai/artifact/GJg6RzAE6guZHhVrxddnji */
        --marco-izq: 8px;
        --marco-lado: 16px;
        --marco-der: calc(var(--marco-lado) + 8px);
        /* En la hoja la tarjeta no lleva margen: esos 16px son de contenido. */
        --margen-tarjeta: 0px;
        /* #826: cada hoja termina a 24 px del borde de abajo —estos 16 más
           los 8 de la ventana— y se le ven las cuatro esquinas: el remate de
           Documentos SUNAT, que el usuario prefirió porque da aire abajo. En
           la #825 eran 8, como a los costados, y casi no se distinguía de un
           corte. Las tarjetas toman su alto de esta cuenta y se acortan solas. */
        --aire-inferior: 16px;
    }
    /* Las dos vistas sin pila miden lo mismo que una sección de la pila: sin
       esto, la hoja terminaba donde terminaba el contenido (en Documentos
       SUNAT, unos 30 px antes; en Costos, según el mes). */
    .st-key-compras_sunat_drill_wrap,
    .st-key-ajuste_graf_card_izq_costos {
        min-height: var(--pila-seccion-min) !important;
    }
    /* Stock: su franja de «Ver» ocupa 46 px con el gap, y la regla general de
       las perspectivas (`_80_cards.py`, 44 px) le gana al 40 que pedía para sí:
       la hoja se pasaba 2 px del borde (medido, #825). */
    .st-key-inv_sec_persp_stock.st-key-inv_sec_persp_stock {
        --persp-alto: 46px;
    }
    /* `clip` y no el `hidden` de Streamlit: al saltar a una vista, el navegador
       también scrollea a los antepasados que puede, y éste se corría 52px y
       dejaba la hoja por encima de la ventana. */
    [data-testid="stAppViewContainer"] {
        overflow: clip !important;
    }

    /* ── LA HOJA ───────────────────────────────────────────────────────── */
    :root:has(.st-key-compras_tabs_row) .stMain {
        flex: 1 1 auto !important;
        width: auto !important;
        min-width: 0 !important;
        height: calc(100dvh - var(--marco-hoja) * 2) !important;
        margin: var(--marco-hoja) var(--marco-lado) var(--marco-hoja)
                calc(var(--rail-reserva) + var(--marco-izq)) !important;
        background: var(--bg-card) !important;
        border-radius: var(--marco-radio) !important;
        box-shadow: var(--marco-sombra) !important;
    }
    /* El margen de `.stMain` ya deja lugar a la columna: lo que reservaba el
       contenedor (`--rail-der-res`) acá sobra, y el aire lo pone cada tarjeta. */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row),
    .block-container:has(.st-key-compras_tabs_row) {
        padding-left: 0 !important;
        padding-right: 0 !important;
    }

    /* La fila de la fecha es de cromo fijo: en el flujo sólo cobra el `gap`. Su
       jalón de `_40_ajuste_franja.py` (−`--cab-offset-contenido`) valía 20 y daba
       casi lo mismo; con 44 subía 21px la primera tarjeta, debajo de la franja. */
    .st-key-fila_ajuste_top {
        padding-top: 0 !important;
        margin-top: -16px !important;
    }
    /* «Ver …» arranca donde arranca la tarjeta de abajo. */
    [class*="st-key-persp_"] {
        padding-left: 18px !important;
    }
    /* Documentos SUNAT: sus cuatro vistas ya están en la franja, ahora visible.
       En el celular tampoco van: están en la barra de abajo (regla #762). */
    .st-key-sunat_cab_vistas {
        display: none !important;
    }

    /* ── LAS TARJETAS SON PARTE DE LA HOJA ─────────────────────────────── */
    div[class*="st-key-ajuste_graf_card_"],
    div[class*="st-key-compras_prov_card_"],
    div[class*="st-key-compras_prod_card_"],
    div[class*="st-key-compras_vol_card_"],
    div[class*="st-key-compras_vap_card_"],
    div[class*="st-key-sunat_card_"],
    .st-key-rec_card_revisar,
    .st-key-rec_card_costo_rb,
    .st-key-rec_card_alza,
    .st-key-rec_card_cambios,
    .st-key-form_receta_card_receta {
        border-radius: 0 !important;
        box-shadow: none !important;
    }

    /* El botón de fecha de cada tarjeta, relleno como los de la franja. */
    [class*="_escala"]:not([class*="_panel"]) button {
        border: none !important;
        background: var(--marco-control) !important;
        box-shadow: none !important;
    }
    [class*="_escala"]:not([class*="_panel"]) button:hover {
        border: none !important;
        background: var(--accent-tint) !important;
    }
    /* Mix: la línea bajo el título no está en el boceto. */
    .st-key-vt_mix_cab {
        border-bottom: none !important;
    }
    .st-key-vt_mix_cab .chart-card-hdr {
        font-size: 16px !important;
        font-weight: 700 !important;
    }
    /* Las perspectivas de Stock, Evolución y Movimientos comparten
       graficos/pestanas.css; allí vive también su geometría compacta. */
    /* #805: Por tipo · «De conteo a conteo | Fechas del calendario» cuenta lo mismo
       con otro reloj: un ajuste, en la caja gris (#795), y no dos botones con borde. */
    .st-key-stock_mov_cab_reloj [data-testid="stButtonGroup"] {
        background: var(--rail-fondo);
        border-radius: 8px;
        padding: 2px;
        gap: 2px !important;
        width: fit-content;
    }
    .st-key-stock_mov_cab_reloj [data-testid="stButtonGroup"] button {
        border: 0 !important;
        border-radius: 6px !important;
        background: transparent !important;
        min-height: 26px !important;
        height: 26px !important;
        padding: 0 10px !important;
    }
    .st-key-stock_mov_cab_reloj [data-testid="stButtonGroup"] button[aria-checked="true"],
    .st-key-stock_mov_cab_reloj [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
        background: var(--bg-card) !important;
        box-shadow: var(--shadow);
    }
    /* #807: «Filtros» con la forma de «Refrescar», su vecino: pastilla gris, sin el
       subrayado índigo, que en esta app quiere decir «pestaña elegida». Lo activo lo
       dice la cuenta. */
    .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        background: var(--rail-fondo) !important;
        border: 0 !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        padding: 0 10px !important;
    }
    .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla [data-testid="stPopover"] button:hover {
        background: var(--bg-hover) !important;
    }
    .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla [data-testid="stPopover"] button p {
        color: var(--text-primary) !important;
        font-size: 12.5px !important;
    }
    /* La familia de «Filtros» dicha donde aplica (Ajuste › Evolución y Tabla dinámica). */
    /* El filtro de familias de Evolución y de la Tabla dinámica, dentro de su
       tarjeta (#823): un control más de la fila del título, de 30 px. */
    .st-key-famvista_ajuste_evo_filtro_familia [data-testid="stPopover"] button,
    .st-key-famvista_ajuste_det_filtro_familia [data-testid="stPopover"] button {
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 12px !important;
        border: none !important;
        border-radius: 999px !important;
        background: var(--rail-fondo) !important;
        color: var(--text-primary) !important;
        font-size: 12.5px !important;
        box-shadow: none !important;
    }
    .st-key-famvista_ajuste_evo_filtro_familia [data-testid="stPopover"] button p,
    .st-key-famvista_ajuste_det_filtro_familia [data-testid="stPopover"] button p {
        font-size: 12.5px !important;
    }
    /* Mix sin su fecha (#807): el renglón queda para los controles de la pieza. */
    .vt-mix-hueco { height: 36px; }
    /* El −1rem de Streamlit bajo un markdown lo descentraba de la fecha. */
    .st-key-vt_mix_cab [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }

    /* ── LA COLUMNA: SIN CAJA, ÍCONOS FINOS ────────────────────────────── */
    .st-key-compras_tabs_row {
        /* El fondo es el mismo de la página y no `transparent`: oculta, la
           columna asoma ENCIMA de la hoja. */
        background: var(--marco-fondo) !important;
        border-right: none !important;
    }
    .st-key-rail_rotulo_rep {
        border-bottom: none !important;
    }
    .st-key-compras_tabs_row [data-testid="stIconMaterial"],
    .st-key-rail_vis_visible [data-testid="stIconMaterial"],
    .st-key-rail_pestillo_abierto [data-testid="stIconMaterial"],
    .st-key-rail_pestillo_plegado [data-testid="stIconMaterial"] {
        font-variation-settings: 'wght' 300;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] button {
        color: var(--accent-deep) !important;
    }
    :root:has(.st-key-rail_pestillo_plegado) .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"] [data-testid="stIconMaterial"] {
        background: var(--bg-card) !important;
        box-shadow: var(--marco-activo) !important;
    }
    :root:has(.st-key-rail_pestillo_abierto) .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"] {
        background: var(--bg-card) !important;
        box-shadow: var(--marco-activo) !important;
    }

    /* ── LA FRANJA: EL BORDE DE ARRIBA DE LA HOJA ──────────────────────── */
    .st-key-nav_franja_rep {
        top: var(--franja-arriba, var(--marco-hoja)) !important;
        left: calc(var(--rail-reserva) + var(--marco-izq)) !important;
        right: var(--marco-lado) !important;
        border-radius: var(--marco-radio) var(--marco-radio) 0 0 !important;
    }
    /* El botón del asistente vive debajo de la franja, a 15 px de la ventana: los
       7 px que la hoja le dejaba adentro. Con el costado de la #850 asomaba 1 px. */
    .st-key-ai_float_wrap {
        right: calc(var(--marco-lado) + 7px) !important;
    }
    .st-key-nav_franja_idx [data-testid="stButton"] button.vista-en-pantalla {
        background: var(--marco-control) !important;
        color: var(--text-primary) !important;
        box-shadow: none !important;
        border-radius: 7px !important;
    }
    .st-key-nav_franja_idx [data-testid="stButton"] button:hover {
        background: var(--marco-control) !important;
    }

    /* Sus controles: rellenos, sin borde, y corridos lo que la hoja se aparta
       de la ventana. `--marco-der` es el borde derecho de la hoja más su aire.
       Los selectores con la clase repetida son los de `_50_fecha.py`. */
    /* #822: Refrescar baja al PIE DEL RAIL, encima del pestillo y con su mismo
       centro (`--icono-x`), como un ícono de 32 px. Lo que decía la franja
       —«Datos al 04/11 · 03:00» y el botón con su texto— pasa a su nombre al
       pasar el cursor: `--sello-tip`, que escribe `inject_sello_actualizacion`
       en <html>. La señal permanente del dato atrasado, que era el sello en
       ámbar, es ahora un punto ámbar en el ícono (más el aviso de arriba de la
       vista, que no cambia). La franja se queda con la ruta y lo de la vista:
       ya no reserva nada para Refrescar ni para la hora (`--barra-act`,
       `--barra-sello`). Abajo de 901 px sigue donde estaba. */
    :root {
        --barra-act: 0px;
        --barra-sello: 0px !important;
    }
    #sello-actualizacion {
        display: none !important;
    }
    .st-key-rail_refresh {
        position: fixed !important;
        top: auto !important;
        right: auto !important;
        bottom: 52px !important;
        left: calc(var(--icono-x) - 16px) !important;
        width: 32px !important;
        height: 32px !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: 1000013 !important;
    }
    .st-key-rail_refresh button {
        position: relative !important;
        width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        justify-content: center !important;
        border: none !important;
        border-radius: 8px !important;
        background: transparent !important;
        box-shadow: none !important;
        color: var(--text-secondary) !important;
        overflow: visible !important;
    }
    .st-key-rail_refresh button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    /* Sólo el ícono: el texto «Refrescar» queda para el nombre al cursor. */
    .st-key-rail_refresh button p {
        font-size: 0 !important;
        gap: 0 !important;
    }
    .st-key-rail_refresh button p span[role="img"] {
        font-size: 20px !important;
    }
    .st-key-rail_refresh button::after {
        content: "Refrescar\\A" var(--sello-tip, "");
        position: absolute;
        top: 50%;
        left: calc(100% + 10px);
        /* Los ítems del rail le ponen `right` y `bottom` a su `::after` (su
           nombre debajo del ícono): sin anularlos, la caja medía 18x10 px. */
        right: auto;
        bottom: auto;
        width: max-content;
        height: auto;
        transform: translateY(-50%);
        padding: 5px 9px;
        border-radius: 5px;
        background: var(--text-primary);
        color: var(--bg-card);
        font-size: 12px;
        font-weight: 500;
        line-height: 1.35;
        white-space: pre;
        text-align: left;
        opacity: 0;
        pointer-events: none;
        transition: opacity .12s;
        z-index: 1000020;
    }
    .st-key-rail_refresh button:hover::after,
    .st-key-rail_refresh button:focus-visible::after {
        opacity: 1;
        transition-delay: .4s;
    }
    :root:has(#sello-actualizacion.sello-viejo) .st-key-rail_refresh button::before {
        content: "";
        position: absolute;
        top: 5px;
        right: 5px;
        bottom: auto;
        left: auto;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--warning);
        box-shadow: 0 0 0 2px var(--bg-primary);
    }
    #sello-actualizacion {
        top: calc(var(--franja-arriba, var(--marco-hoja)) + (var(--franja-rep-alto) - 30px) / 2) !important;
        right: calc(var(--marco-der) + var(--barra-f) + var(--barra-act, 0px)
                    + var(--barra-fecha)) !important;
    }
    .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
        top: calc(var(--franja-arriba, var(--marco-hoja)) + (var(--franja-rep-alto) - 30px) / 2) !important;
        right: var(--marco-der) !important;
        border-left: none !important;
        background: transparent !important;
    }
    .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill {
        top: calc(var(--franja-arriba, var(--marco-hoja)) + (var(--franja-rep-alto) - 30px) / 2) !important;
        right: calc(var(--marco-der) + var(--barra-f) + var(--barra-act, 0px)) !important;
    }
    .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla [data-testid="stPopover"] button,
    .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
        height: 30px !important;
        min-height: 30px !important;
        border: none !important;
        border-radius: 8px !important;
        background: var(--marco-control) !important;
        box-shadow: none !important;
        color: var(--text-primary) !important;
        font-weight: 400 !important;
    }
    .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla [data-testid="stPopover"] button:hover,
    .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill [data-testid="stPopover"] button:hover {
        border: none !important;
        background: var(--accent-tint) !important;
    }
    }

    /* #776: el marco de la opción B en TODA la app (en la #775 era sólo de
       Costo de Carta, y al bajar a Alza la franja cambiaba de color). La
       navegación —área, vistas, hora del dato, Refrescar— queda sobre el
       lavanda y cada vista es su propia hoja blanca, que empieza debajo de
       la franja. Las vistas de la pila se reconocen como en el encaje de
       `_27_pila.py`, por el infijo `_sec_` de su key; Costos y Documentos
       SUNAT no tienen pila y nombran su contenedor. Sin `:has()` (#469). */
    @media (min-width: 901px) {
    :root:has(.st-key-compras_tabs_row) .stMain {
        background: var(--marco-fondo) !important;
        box-shadow: none !important;
        border-radius: 0 !important;
    }
    .st-key-nav_franja_rep {
        background: var(--marco-fondo) !important;
        border-bottom: none !important;
    }
    .st-key-nav_franja_idx [data-testid="stButton"] button.vista-en-pantalla {
        background: var(--accent-deep) !important;
        color: var(--bg-card) !important;
        border-radius: 18px !important;
    }
    [class*="st-key-"][class*="_sec_"]:not([class*="st-key-pila_go_"]),
    .st-key-compras_sunat_drill_wrap,
    .st-key-ajuste_graf_card_izq_costos {
        background: var(--bg-card) !important;
        border-radius: var(--marco-radio) !important;
        box-shadow: var(--marco-sombra) !important;
        /* Las tarjetas de adentro también son blancas y cuadradas: sin el
           recorte tapan las esquinas. `clip` y no `hidden`: no crea un
           scroll propio, y los `sticky` siguen pegándose a la página. */
        overflow: clip !important;
    }
    /* Una sección dentro de otra (las perspectivas) no es otra hoja. */
    [class*="_sec_"] [class*="st-key-"][class*="_sec_"] {
        background: transparent !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        overflow: visible !important;
    }
    /* La tarjeta de Costo de Carta era la hoja de la #775: ahora lo es su
       sección, como en las demás. */
    .st-key-rec_card_carta {
        border-radius: 0 !important;
        box-shadow: none !important;
    }
    }
    .st-key-rec_card_carta,
    .st-key-rec_card_alza,
    .st-key-rec_card_costo_rb,
    .st-key-rec_card_cambios,
    .st-key-rec_card_revisar {
        position: relative !important;
        padding: 0 !important;
        gap: 0 !important;
        overflow: visible !important;
    }
    /* El calendario conserva su componente, estado y callbacks. Su fila
       nativa se coloca sobre el hueco que mide la pieza
       (carta_costeada.js, recetas_alza.js #779, recetas_cambios.js #781). */
    .st-key-rec_carta_cab,
    .st-key-rec_alza_cab,
    .st-key-rec_cambios_cab {
        position: absolute !important;
        top: 46px;
        left: 24px;
        width: max-content !important;
        max-width: calc(100% - 24px) !important;
        z-index: 5;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        gap: 0 !important;
    }
    .st-key-rec_carta_cab_fecha,
    .st-key-rec_alza_cab_fecha,
    .st-key-rec_cambios_cab_fecha {
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-rec_carta_f_escala button,
    .st-key-rec_alza_f_escala button,
    .st-key-rec_cambios_f_escala button {
        height: 30px !important;
        min-height: 30px !important;
        background: var(--marco-control) !important;
        border: none !important;
        box-shadow: none !important;
        font-weight: 400 !important;
        font-size: 13px !important;
        /* Un ancho fijo de 200 px cortaba «Últimos 3 meses · 2 ago – 1
           nov» contra el borde (#779): el botón toma el de su texto
           (`max-content`: con `auto` Streamlit lo deja en el 100 % de una
           caja de 200), y la pieza mide el hueco con ese ancho. */
        width: max-content !important;
        min-width: 200px !important;
        padding: 0 14px !important;
    }
    /* La rayita separaba el título de la fecha; el título ya no está. */
    .st-key-rec_carta_cab_fecha::after,
    .st-key-rec_alza_cab_fecha::after,
    .st-key-rec_cambios_cab_fecha::after {
        display: none !important;
    }
    /* #781: Nuevo Costeo en el lenguaje de Costo de Carta. El modo (Receta
       de venta | Combo | Modificar | Guardadas) es el nivel 2: pestañas con
       subrayado y línea de borde a borde, a la izquierda; ya no hay título
       al lado (la vista se nombra en la franja). Va acá y no en _80_cards:
       gana a sus reglas del control de pista gris. */
    .st-key-form_receta_card_receta {
        padding: 0 24px 16px !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        gap: 12px !important;
    }
    .st-key-form_receta_modo {
        width: calc(100% + 48px) !important;
        max-width: none !important;
        margin: 0 -24px !important;
        padding: 0 24px !important;
        border-bottom: 1px solid var(--border);
    }
    /* El escritorio usa las carpetas compartidas; móvil conserva su fila. */
    @media (max-width: 900px) {
    .st-key-form_receta_modo [data-testid="stButtonGroup"] {
        justify-content: flex-start !important;
    }
    .st-key-form_receta_modo [data-testid="stButtonGroup"] > div {
        gap: 20px !important;
        padding: 0 !important;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
    }
    .st-key-form_receta_modo [data-testid="stButtonGroup"] button {
        min-height: 36px !important;
        padding: 0 !important;
        margin-bottom: -1px !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        color: var(--text-secondary) !important;
    }
    /* El elegido lo dice `aria-checked`: en esta versión de Streamlit el
       botón no lleva `kind`, y la regla de `_80_cards` con
       `kind="segmented_controlActive"` no lo marcaba. */
    .st-key-form_receta_modo [data-testid="stButtonGroup"] button[aria-checked="true"] {
        border-bottom-color: var(--accent) !important;
        color: var(--text-primary) !important;
    }
    .st-key-form_receta_modo [data-testid="stButtonGroup"] button[aria-checked="true"] p {
        font-weight: 600 !important;
    }
    .st-key-form_receta_modo [data-testid="stButtonGroup"] button p {
        font-size: 14px !important;
    }

    }

    /* Cada fecha de Ajuste conserva su widget y sigue a la vista del rail. */
    @media (min-width: 901px) {
        [data-ajuste-vista] {
            --ajuste-fecha-top: calc(var(--franja-arriba, var(--marco-hoja, 8px)) + (var(--franja-rep-alto, 44px) - 30px) / 2);
            --ajuste-fecha-right: calc(var(--marco-der, 16px) + 6px);
        }
        [data-ajuste-vista] .st-key-aj_sec_persp_cierre {
            --ajuste-cierre-fecha-display: none;
        }
        [data-ajuste-vista="aj_sec_persp_cierre"] .st-key-aj_sec_persp_cierre {
            --ajuste-cierre-fecha-display: inline-flex;
            --ajuste-cierre-fecha-pos: fixed;
        }
        [data-ajuste-vista] :is(.st-key-ajses_dif_fila, .st-key-ajf_evo_fila, .st-key-ajf_det_fila, .st-key-ajf_exp_fila) {
            display: none !important;
        }
        [data-ajuste-vista="aj_sec_diferencias"] .st-key-ajses_dif_fila,
        [data-ajuste-vista="aj_sec_persp_tiempo"] :is(.st-key-ajf_evo_fila, .st-key-ajf_det_fila),
        [data-ajuste-vista="aj_sec_explorar"] .st-key-ajf_exp_fila {
            display: flex !important;
            position: fixed !important;
            top: var(--ajuste-fecha-top) !important;
            right: var(--ajuste-fecha-right) !important;
            width: max-content !important;
            z-index: 1000012 !important;
        }
        [data-ajuste-vista] :is(.st-key-ajses_dif_fila, .st-key-ajf_evo_fila, .st-key-ajf_det_fila, .st-key-ajf_exp_fila)
            [data-testid="stPopover"] button[data-testid="stPopoverButton"] {
            height: 30px !important;
            min-height: 30px !important;
            border-radius: 8px !important;
            box-shadow: none !important;
            color: var(--text-primary) !important;
        }
    }

    /* Cabeceras de Compras con el alto y el margen de Ajuste › Diferencias. */
    [class*="st-key-cp_con_filtro_"] {
        --cp-alto-pestanas: 40px;
        --cp-margen-pestanas: 8px;
    }
    /* Un popover de familia y subfamilia por tarjeta de Compras. */
    [class*="st-key-cp_filtro_vista_"] {
        padding-inline: 10px;
    }
    [class*="st-key-cp_filtro_vista_"] button[data-testid="stPopoverButton"] {
        width: max-content !important;
        min-width: 32px !important;
        min-height: 32px !important;
        padding: 0 7px !important;
        border: 0 !important;
        border-radius: 8px !important;
        background: var(--rail-fondo) !important;
        color: var(--text-secondary) !important;
    }
    [class*="st-key-cp_filtro_vista_"] button[data-testid="stPopoverButton"]:is(:hover, [aria-expanded="true"]) {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    [class*="st-key-cp_filtro_vista_"] button[data-testid="stPopoverButton"] p > span[role="img"] {
        font-size: 18px;
    }
    [class*="st-key-cp_filtro_vista_"] button[data-testid="stPopoverButton"] [data-testid="stIconMaterial"] {
        display: none !important;
    }
    [class*="st-key-cp_panel_filtro_"] {
        width: min(300px, calc(100vw - 64px)) !important;
        max-height: min(420px, 65vh);
        overflow-y: auto;
        overscroll-behavior: contain;
    }
    [class*="st-key-cp_grupo_filtro_"] {
        border-top: 1px solid var(--line-soft);
        padding-top: 6px;
    }
    [class*="st-key-cp_grupo_filtro_"] [data-testid="stCheckbox"] {
        min-height: 34px;
        display: flex;
        align-items: center;
    }
    [class*="st-key-cp_grupo_filtro_"] [data-testid="stCheckbox"] p {
        font-size: 13px;
        text-transform: none !important;
    }
    [class*="st-key-cp_grupo_filtro_"] [data-testid="stButton"] button {
        min-height: 24px;
        padding: 0 8px;
        border: 0;
        border-radius: 8px;
        background: var(--rail-fondo);
    }
    [class*="st-key-cp_grupo_filtro_"] [data-testid="stButton"] button p {
        font-size: 12px;
    }
    @media (max-width: 900px) {
        [class*="st-key-cp_filtro_vista_"] button[data-testid="stPopoverButton"] {
            min-height: 44px !important;
            min-width: 44px !important;
        }
    }
    @media (min-width: 901px) {
        [class*="st-key-cp_con_filtro_"] {
            --cp-reserva-filtro: 56px;
            position: relative;
        }
        /* Período dibuja su filtro adentro, como ficha al lado de «Más
           filtros» (#843): no tiene ⚙ y no le reserva el hueco. */
        .st-key-cp_con_filtro_semanal {
            --cp-reserva-filtro: 0px;
        }
        [class*="st-key-cp_filtro_vista_"] {
            position: absolute !important;
            top: calc(var(--cp-margen-pestanas) + var(--cp-alto-pestanas) / 2);
            right: 18px;
            transform: translateY(-50%);
            width: max-content !important;
            padding: 0;
            z-index: 8;
        }
        [data-compras-vista] {
            --barra-f: 0px;
        }
    }

    /* Movimientos › Req. y salidas (#845, opción D): la fecha de Salidas y de
       Requerimientos sube a la ruta, como en Compras, a la izquierda de
       Filtros; dice además cómo se cuenta («· al cierre»). En la banda de las
       carpetas, donde estaba, ahora van los indicadores. Las vistas por área
       conservan su fecha en el título de su cuadro. */
    @media (min-width: 901px) {
        [data-mov-vista="mov_sec_persp_lados"] :is(.st-key-mov_f_req_periodo_escala, .st-key-mov_f_sal_periodo_escala) {
            display: flex !important;
            position: fixed !important;
            inset: calc(var(--franja-arriba, var(--marco-hoja, 8px)) + (var(--franja-rep-alto, 44px) - 30px) / 2)
                calc(var(--marco-der, 16px) + var(--barra-f, 120px) + var(--barra-act, 0px)) auto auto !important;
            width: max-content !important;
            z-index: 1000012 !important;
        }
        [data-mov-vista="mov_sec_persp_lados"] :is(.st-key-mov_per_nativa_fecha, .st-key-mov_psal_nativa_fecha) {
            z-index: auto !important;
        }
        [data-mov-vista="mov_sec_persp_lados"] :is(.st-key-mov_f_req_periodo_escala, .st-key-mov_f_sal_periodo_escala)
            button[data-testid="stPopoverButton"] {
            height: 30px !important;
            min-height: 30px !important;
            border-radius: 15px !important;
            background: var(--marco-control) !important;
            box-shadow: none !important;
            color: var(--text-primary) !important;
        }
        [data-mov-vista="mov_sec_persp_lados"] :is(.st-key-mov_f_req_periodo_escala, .st-key-mov_f_sal_periodo_escala)
            button[data-testid="stPopoverButton"] p {
            font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 13px !important;
        }
    }

    /* Compras conserva los popovers y rangos de cada vista. Sólo el de la
       sección en pantalla sube a la franja, a la izquierda de Filtros. */
    @media (min-width: 901px) {
        [data-compras-vista] :is(
            .st-key-cp_sem_escala, .st-key-cp_rank_escala, .st-key-cp_prod_escala,
            .st-key-cp_vol_escala, .st-key-cp_vap_f_escala, .st-key-cp_docs_escala
        ),
        [data-compras-vista] .st-key-compras_sec_tabla .st-key-tabla_fila_hdr {
            display: none !important;
        }
        [data-compras-vista="compras_sec_semanal"] .st-key-cp_sem_escala,
        [data-compras-vista="compras_sec_proveedor"] .st-key-cp_rank_escala,
        [data-compras-vista="compras_sec_producto"] .st-key-cp_prod_escala,
        [data-compras-vista="compras_sec_volatilidad"] .st-key-cp_vol_escala,
        [data-compras-vista="compras_sec_vs_ano_pasado"] .st-key-cp_vap_f_escala,
        [data-compras-vista="compras_sec_documentos"] .st-key-cp_docs_escala,
        [data-compras-vista="compras_sec_tabla"] .st-key-compras_sec_tabla .st-key-tabla_fila_hdr {
            display: flex !important;
            position: fixed !important;
            inset: calc(var(--franja-arriba, var(--marco-hoja, 8px)) + (var(--franja-rep-alto, 44px) - 30px) / 2)
                calc(var(--marco-der, 16px) + var(--barra-f, 120px) + var(--barra-act, 0px)) auto auto !important;
            width: max-content !important;
            visibility: visible !important;
            z-index: 1000012 !important;
        }
        /* Los anclajes nativos no deben encerrar el popover en la capa de
           la tarjeta. En Proveedor el anclaje sigue alojando su filtro. */
        [data-compras-vista] :is(
            .st-key-cp_sem_fecha, .st-key-cp_prov_nativa_fecha, .st-key-cp_prod_nativa_fecha,
            .st-key-cp_vol_fecha, .st-key-cp_vap_nativa_fecha, .st-key-cp_docs_nativa_fecha
        ) {
            z-index: auto !important;
        }
        [data-compras-vista] .st-key-cp_prov_nativa_fecha .st-key-cp_prov_pop_float {
            position: relative;
            z-index: 5;
        }
        [data-compras-vista] :is(.lugar-fecha, .cp-lugar, .vap-lugar, .dc-lugar),
        [data-compras-vista] .st-key-compras_sec_producto .lf-lugar {
            display: none !important;
        }
        [data-compras-vista] .cpp .cab {
            padding-right: 0;
        }
        [data-compras-vista] .st-key-cp_vol_pieza_wrap {
            --cp-fecha-slot: none;
        }
        [data-compras-vista] :is(
            .st-key-cp_sem_escala, .st-key-cp_rank_escala, .st-key-cp_prod_escala,
            .st-key-cp_vol_escala, .st-key-cp_vap_f_escala, .st-key-cp_docs_escala
        ) button[data-testid="stPopoverButton"] {
            height: 30px !important;
            min-height: 30px !important;
            border-radius: 8px !important;
            background: var(--marco-control) !important;
            box-shadow: none !important;
            color: var(--text-primary) !important;
        }
        [data-compras-vista] :is(
            .st-key-cp_sem_escala, .st-key-cp_rank_escala, .st-key-cp_prod_escala,
            .st-key-cp_vol_escala, .st-key-cp_vap_f_escala, .st-key-cp_docs_escala
        ) button[data-testid="stPopoverButton"]:hover {
            background: var(--accent-tint) !important;
        }
    }

    /* ── LA RUTA CON SU MENÚ (2026-11-04, regla #817) ────────────────────
       La franja dice «Inventario › Ajuste › Diferencias ▾»; las vistas del
       área van en un menú que abre `_SCRIPT_CAPAS` (`<html data-franja-menu>`):
       una columna por reporte, cada vista con su línea de qué muestra. Son
       los botones de siempre (`nav_franja_idx`), así que el temporizador los
       sigue marcando. Sólo desde 901px: más abajo la franja es otra. */
    .st-key-nav_franja_idx .st-key-nav_franja_secciones { display: none !important; }
    @media (min-width: 901px) {
        .franja-ruta {
            display: inline-flex; align-items: center; gap: 8px;
            margin-left: 10px; cursor: pointer; white-space: nowrap;
            /* La letra de la app, dicha acá (#844): la ruta se dibuja con un
               `st.markdown`, y su contenedor trae «Source Sans», la de
               Streamlit. Medido: el área salía en Source Sans 600, más fina y
               más chica que el resto de la página, que va en DM Sans. */
            font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .franja-ruta .fr-sep { color: var(--text-muted); }
        .franja-ruta .fr-grupo { font-size: 13px; color: var(--text-secondary); }
        .franja-ruta .fr-grupo:empty, .franja-ruta .fr-grupo:empty + .fr-sep2 { display: none; }
        .franja-ruta .fr-vista {
            display: inline-flex; align-items: center; gap: 8px; height: 32px;
            padding: 0 7px; border-radius: 7px; background: transparent;
            color: var(--text-primary); font-size: 13px; font-weight: 500;
        }
        .franja-ruta .fr-vista i { font-style: normal; font-size: 12px; opacity: .8; }
        .franja-ruta:not([data-franja-compacta]):hover .fr-vista,
        .franja-ruta:focus-visible .fr-vista { background: var(--accent-tint); }
        /* Cerrada: el menú no está. */
        .st-key-nav_franja_rep .st-key-nav_franja_idx { display: none !important; }
        /* La franja recorta lo que se le sale (`overflow: hidden`): abierta, no. */
        :root[data-franja-menu] .st-key-nav_franja_rep { overflow: visible !important; }
        /* Abierta: el panel bajo la ruta, una columna por reporte. */
        :root[data-franja-menu] .st-key-nav_franja_rep .st-key-nav_franja_idx {
            display: flex !important;
            position: absolute !important;
            top: calc(100% - 4px) !important;
            left: var(--fr-x, 160px) !important;
            z-index: 1100 !important;
            flex: none !important;
            width: auto !important;
            max-width: calc(100vw - var(--fr-x, 160px) - 40px) !important;
            height: auto !important;
            overflow: visible !important;
            align-items: flex-start !important;
            gap: 14px !important;
            margin: 0 !important;
            padding: 14px !important;
            background: var(--bg-card) !important;
            border-radius: 14px !important;
            box-shadow: 0 14px 36px color-mix(in srgb, var(--text-primary) 18%, transparent) !important;
        }
        .st-key-nav_franja_idx [class*="st-key-nav_franja_g"] {
            display: flex !important; flex-direction: column !important;
            gap: 0 !important; width: 230px !important; flex: none !important;
        }
        .st-key-nav_franja_idx [class*="st-key-nav_franja_g"] [data-testid="stElementContainer"],
        .st-key-nav_franja_idx [class*="st-key-nav_franja_g"] [data-testid="stButton"] { width: 100% !important; }
        .st-key-nav_franja_idx .franja-miembro {
            display: block; font-size: 12px; color: var(--text-muted);
            padding: 0 10px 6px;
        }
        .st-key-nav_franja_idx .franja-desc {
            display: block; font-size: 12px; line-height: 1.3; color: var(--text-secondary);
            padding: 0 10px 8px; margin-top: -2px; white-space: normal;
        }
        .st-key-nav_franja_idx [data-testid="stButton"] button {
            width: 100% !important; justify-content: flex-start !important;
            height: auto !important; min-height: 28px !important;
            padding: 4px 10px 0 !important; border-radius: 8px 8px 0 0 !important;
            color: var(--text-primary) !important; background: transparent !important;
        }
        .st-key-nav_franja_idx [data-testid="stButton"] button p {
            font-size: 13px !important; font-weight: 600 !important;
            text-align: left !important; width: 100% !important;
        }
        .st-key-nav_franja_idx [data-testid="stButton"] button > div,
        .st-key-nav_franja_idx [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {
            justify-content: flex-start !important; text-align: left !important; width: 100% !important;
        }
        .st-key-nav_franja_idx [data-testid="stButton"] button:hover {
            background: var(--accent-tint) !important; color: var(--accent-deep) !important;
        }
        .st-key-nav_franja_idx [data-testid="stButton"] button.vista-en-pantalla {
            background: var(--accent-tint) !important; color: var(--accent-deep) !important;
            box-shadow: none !important; border-radius: 8px 8px 0 0 !important;
        }

        /* Ruta integrada en todos los reportes: grupo discreto, vista en tinta
           y lavanda al interactuar. Conserva los destinos nativos. */
        /* Los niveles reservan el mismo ancho y las flechas su propio sitio.
           El área puede crecer para que sus 17px no recorten nombres largos. */
        .barra-ctx[data-barra-compacta] {
            --franja-nivel-ancho: 120px;
            gap: 0;
        }
        .barra-ctx[data-barra-compacta] .barra-reporte {
            display: inline-flex; align-items: center; justify-content: center;
            gap: 10px; width: max-content; min-width: var(--franja-nivel-ancho); flex: 0 0 auto;
            box-sizing: border-box; padding: 0 7px;
        }
        .barra-ctx[data-barra-compacta] .barra-nom {
            flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis;
        }
        .franja-ruta[data-franja-compacta] { cursor: default; gap: 0; margin-left: 0; }
        .franja-ruta[data-franja-compacta] .fr-sep {
            width: 24px; flex: 0 0 24px; text-align: center;
        }
        .franja-ruta[data-franja-compacta] button {
            display: inline-flex; align-items: center; justify-content: center; gap: 7px;
            box-sizing: border-box; width: var(--franja-nivel-ancho); flex: 0 0 var(--franja-nivel-ancho);
            height: 30px; padding: 0 7px; border-radius: 7px;
            border: 0; background: transparent;
            color: var(--text-primary); font: inherit; font-size: 13px;
            font-weight: 500; cursor: pointer;
        }
        .franja-ruta[data-franja-compacta] :is(.fr-grupo, .fr-txt) {
            min-width: 0; overflow: hidden; text-overflow: ellipsis;
        }
        .franja-ruta[data-franja-compacta] :is(i, .barra-ico) { flex-shrink: 0; }
        .franja-ruta[data-franja-compacta] .fr-grupo-boton { font-weight: 400; }
        .franja-ruta[data-franja-compacta] .fr-grupo { color: var(--text-secondary); }
        .franja-ruta[data-franja-nombre] { margin-left: 0; }
        .franja-ruta[data-franja-nombre] .fr-grupo-boton {
            width: max-content; min-width: var(--franja-nivel-ancho); flex: 0 0 auto;
        }
        /* Cuando el área abre su menú, el nombre vive en este botón y no
           en .barra-nom: conserva la misma presentación en ambas rutas. */
        .franja-ruta[data-franja-nombre] .fr-grupo {
            border-radius: 0; padding: 0;
            color: var(--text-primary); font-size: 17px; font-weight: 600;
        }
        .franja-ruta[data-franja-compacta] i { font-style: normal; font-size: 12px; color: var(--text-secondary); }
        .franja-ruta[data-franja-compacta] button:hover,
        .franja-ruta[data-franja-compacta] button[aria-expanded="true"] {
            background: var(--accent-tint);
            color: var(--accent-deep);
        }
        :root[data-franja-menu^="ruta-"] .st-key-nav_franja_rep .st-key-nav_franja_idx {
            display: block !important;
            box-sizing: border-box !important;
            width: 196px !important;
            padding: 5px !important;
            border-radius: 9px !important;
            border: 1px solid var(--border);
            max-height: calc(100dvh - 96px) !important;
            overflow-y: auto !important;
            box-shadow: 0 8px 24px color-mix(in srgb, var(--text-primary) 12%, transparent) !important;
        }
        :root[data-franja-menu^="ruta-"] .st-key-nav_franja_idx [class*="st-key-nav_franja_g"] {
            display: none !important;
        }
        :root[data-franja-menu="ruta-vistas"] .st-key-nav_franja_idx [data-franja-columna] {
            display: flex !important;
            width: 100% !important;
        }
        :root[data-franja-menu="ruta-vistas"] .st-key-nav_franja_idx .franja-miembro {
            display: none !important;
        }
        :root[data-franja-menu="ruta-secciones"] .st-key-nav_franja_idx .st-key-nav_franja_secciones {
            display: block !important;
        }
        .st-key-nav_franja_idx .st-key-nav_franja_secciones [data-testid="stMarkdownContainer"] {
            width: 100% !important;
        }
        .st-key-nav_franja_idx [data-testid="stMarkdownContainer"] .franja-secciones {
            display: grid !important;
        }
        :root[data-franja-menu="ruta-vistas"] .st-key-nav_franja_idx [data-testid="stButton"] button,
        .st-key-nav_franja_idx .franja-seccion {
            width: 100% !important; min-height: 32px !important;
            padding: 5px 28px 5px 9px !important; border-radius: 6px !important;
            position: relative;
        }
        :root[data-franja-menu="ruta-vistas"] .st-key-nav_franja_idx [data-testid="stButton"] button p {
            font-weight: 400 !important;
        }
        .st-key-nav_franja_idx .franja-seccion[aria-current="true"]::after,
        :root[data-franja-menu="ruta-vistas"] .st-key-nav_franja_idx button.vista-en-pantalla::after {
            content: "✓"; position: absolute; right: 9px; color: var(--accent-deep);
        }
        .st-key-nav_franja_idx .franja-seccion {
            display: block; border: 0; text-align: left; cursor: pointer;
            font-family: inherit; font-size: 13px; font-weight: 500;
            color: var(--text-primary); background: transparent;
        }
        .st-key-nav_franja_idx .franja-seccion:hover,
        .st-key-nav_franja_idx .franja-seccion[aria-current="true"] {
            color: var(--accent-deep); background: var(--accent-tint);
        }

        /* ── LA RUTA EN UNA PÍLDORA DE BORDE A BORDE (regla #841) ──────────
           A pedido, sobre el boceto https://claude.ai/artifact/7v7WufpmWibLs4s6TDQx54.
           Una píldora blanca con los MISMOS bordes que la hoja de abajo: la
           franja ya mide eso (de `--rail-reserva` + `--marco-izq` a `--marco-lado`, #850), así que
           la píldora es su `::before` y no hay que medir nada. Lo de la
           derecha —la fecha, Filtros— son controles fijos que dibuja cada
           reporte con su key; quedan ADENTRO porque la píldora los rodea, sin
           moverlos. `z-index: -1` dentro de la franja, que ya es un contexto
           de apilamiento (fija con z-index): pinta sobre su fondo y debajo de
           la ruta. 36 px centrada en la franja: los controles de 30 quedan con
           3 px arriba y abajo, y la hoja empieza 4 px más abajo. */
        .st-key-nav_franja_rep::before {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            top: calc((var(--franja-rep-alto) - 36px) / 2);
            height: 36px;
            border-radius: 18px;
            background: var(--bg-card);
            box-shadow: var(--marco-sombra);
            z-index: -1;
            pointer-events: none;
        }
        /* Los controles de adentro también en cápsula: con 8 px de radio, su
           esquina chocaba con la curva de la píldora a 8 px del borde. */
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill [data-testid="stPopover"] button,
        .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla [data-testid="stPopover"] button,
        [data-compras-vista] :is(
            .st-key-cp_sem_escala, .st-key-cp_rank_escala, .st-key-cp_prod_escala,
            .st-key-cp_vol_escala, .st-key-cp_vap_f_escala, .st-key-cp_docs_escala
        ) button[data-testid="stPopoverButton"] {
            border-radius: 15px !important;
        }
        /* …y con la letra de la ruta, que va en la misma píldora (#844): el
           botón de Streamlit trae «Source Sans», y la fecha salía en otra
           letra que «Compras › Período». */
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill [data-testid="stPopover"] button p,
        [data-compras-vista] :is(
            .st-key-cp_sem_escala, .st-key-cp_rank_escala, .st-key-cp_prod_escala,
            .st-key-cp_vol_escala, .st-key-cp_vap_f_escala, .st-key-cp_docs_escala
        ) button[data-testid="stPopoverButton"] p {
            font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        /* La ruta mide lo que su texto: «Compras › Período ▾». Desde la
           6c136f58 cada nivel reservaba 120 px con el texto centrado, para que
           la ruta no cambiara de largo entre reportes; dentro de la píldora
           eso dejaba ~100 px entre «Ventas» y «Venta» y no se leía como una
           ruta. El primer nivel arranca siempre en el mismo x. */
        .barra-ctx[data-barra-compacta] .barra-reporte {
            min-width: 0;
            justify-content: flex-start;
            padding: 0 6px 0 0;
        }
        .franja-ruta[data-franja-compacta] .fr-sep {
            width: 20px;
            flex: 0 0 20px;
        }
        .franja-ruta[data-franja-compacta] button,
        .franja-ruta[data-franja-nombre] .fr-grupo-boton {
            width: max-content;
            min-width: 0;
            flex: 0 0 auto;
            padding: 0 8px;
            border-radius: 15px;
        }
        .franja-ruta[data-franja-nombre] .fr-grupo-boton {
            margin-left: -8px;
        }
        /* #842: la letra del boceto. El área iba en 17 px y la vista en 13:
           ahora los dos niveles en 13, el área en negrita (600) y la vista
           en 500, como cualquier ruta. */
        .st-key-nav_franja_rep .barra-nom,
        .franja-ruta[data-franja-nombre] .fr-grupo {
            font-size: 13px;
            font-weight: 600;
        }
        .franja-ruta[data-franja-compacta] .fr-vista {
            font-weight: 500;
            color: var(--text-primary);
        }
    }
    /* ── #851: LA FRANJA ES LA BARRA DE LA APP, Y LAS VISTAS ESTÁN A LA VISTA ──
       A pedido, sobre el boceto https://claude.ai/artifact/MhVrH9AW34qFidWQ3Kk8cC
       («Barra alineada»). Desde 901px:
       - La píldora de la #841 pasa a ser una barra blanca de borde a borde, sin
         esquinas ni sombra, con una línea fina abajo: el marco de la app. Es el
         MISMO `::before`, estirado hasta la ventana por los dos costados; la
         franja va encima de la columna (z-index) para que la cruce. Sube 12 px
         (`--franja-arriba`, que también usan los controles fijos de la franja):
         todo lo de la barra queda centrado en y = 26, el botón de ocultar la
         columna incluido.
       - La ruta deja el menú de vistas: «Compras ▾» (el menú de reportes del
         área) y, al lado, las vistas del reporte en pantalla, en pastillas. Son
         los botones de `nav_franja_idx` —los de siempre, con sus keys—: se
         muestra sólo la columna del reporte en pantalla (`franja-activo`, de
         `navegacion.py`), en fila. El menú de reportes cuelga aparte.
       - «Compras» empieza en el mismo borde que el contenido de la hoja (106 px con
         la columna plegada).
       Lo que abre una capa no se mueve al abrirse (#465): abrir «Compras ▾» no
       toca las pastillas. */
    @media (min-width: 901px) {
        :root { --franja-arriba: -4px; }
        /* La franja ya no recorta (la barra se le sale a los costados): recorta la
           fila de vistas, que es lo único que podría no entrar. */
        :root .st-key-nav_franja_rep.st-key-nav_franja_rep {
            overflow: visible !important;
            background: transparent !important;
            border-radius: 0 !important;
        }
        .st-key-nav_franja_rep.st-key-nav_franja_rep {
            z-index: 1000011 !important;
            width: auto !important;
            max-width: none !important;
            flex-direction: row !important;
            align-items: center !important;
            flex-wrap: nowrap !important;
            gap: 0 !important;
            /* La franja empieza donde la hoja: «Compras» en el borde de su contenido
               (106 px plegada, 274 fijada, 50 oculta). */
            padding-left: 18px !important;
        }
        .st-key-nav_franja_rep.st-key-nav_franja_rep::before {
            left: calc(-1 * (var(--rail-reserva) + var(--marco-izq)));
            right: calc(-1 * var(--marco-lado));
            top: 0;
            height: 100%;
            border-radius: 0;
            /* La línea de abajo y, debajo de ella, el lavanda hasta la hoja: lo que
               asoma por encima de la hoja (los controles de Stock, `top: -40px`)
               quedaba debajo de la franja, que antes llegaba hasta ahí. */
            box-shadow: 0 1px 0 var(--ctl-linea),
                        0 calc(var(--marco-hoja) - var(--franja-arriba)) 0 var(--marco-fondo);
        }
        .st-key-nav_franja_rep > [data-testid="stElementContainer"]:first-child {
            width: auto !important; flex: none !important;
        }
        /* Lo fijo que vive en la barra va encima de ella: la fecha de la franja
           (Ventas) y «Filtros» nacían en 1000000 y 1000002, debajo. La fecha, además,
           vive dentro de `fila_ajuste_top` (sticky, 1000002), que la limita. */
        :root .st-key-fila_ajuste_top.st-key-fila_ajuste_top.st-key-fila_ajuste_top,
        :root .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill,
        :root .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla,
        :root #sello-actualizacion {
            z-index: 1000012 !important;
        }
        .st-key-rail_vis_visible.st-key-rail_vis_visible,
        .st-key-rail_vis_oculto.st-key-rail_vis_oculto {
            top: calc(var(--franja-arriba) + (var(--franja-rep-alto) - 32px) / 2) !important;
        }
        /* «Compras ▾» a la izquierda de su caja, no centrado: el texto marca el borde. */
        .barra-ctx[data-barra-compacta] .barra-reporte,
        .franja-ruta[data-franja-nombre] .fr-grupo-boton {
            justify-content: flex-start; min-width: 0; padding-left: 0; margin-left: 0;
        }
        .st-key-nav_franja_rep .fr-grupo { font-weight: 500 !important; }
        .franja-ruta[data-franja-compacta] :is(.fr-vista, .fr-sep-vista) { display: none !important; }

        /* Las vistas: la columna del reporte en pantalla, en fila. */
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx.st-key-nav_franja_idx {
            display: flex !important;
            position: static !important;
            flex: 0 1 auto !important;
            width: auto !important;
            min-width: 0 !important;
            max-width: none !important;
            height: auto !important;
            max-height: none !important;
            margin: 0 0 0 8px !important;
            padding: 2px !important;
            gap: 0 !important;
            align-items: center !important;
            overflow: hidden !important;
            background: none !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        /* Las cajas de Streamlit alrededor de cada columna no ocupan lugar: así la
           fila es sólo la del reporte en pantalla y el menú de reportes cuelga aparte. */
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx > [data-testid="stLayoutWrapper"] {
            display: contents !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [class*="st-key-nav_franja_g"]:not(:has(.franja-activo)) {
            display: none !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [class*="st-key-nav_franja_g"]:has(.franja-activo) {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 2px !important;
            width: auto !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [class*="st-key-nav_franja_g"] > [data-testid="stElementContainer"]:first-child {
            display: none !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [class*="st-key-nav_franja_g"] :is([data-testid="stElementContainer"], [data-testid="stButton"]) {
            width: auto !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [data-testid="stButton"] button {
            width: auto !important; height: 28px !important; min-height: 28px !important;
            padding: 0 10px !important; border: 0 !important; border-radius: 14px !important;
            background: transparent !important; color: var(--ctl-texto-2) !important;
            box-shadow: none !important; justify-content: center !important;
            font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            font-size: 13px !important; font-weight: 500 !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [data-testid="stButton"] button p {
            font-size: 13px !important; font-weight: 500 !important; color: inherit !important;
            font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            white-space: nowrap !important;
        }
        /* La fecha, en 13 px como la ruta (era 14, la de Streamlit). */
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill [data-testid="stPopover"] button p,
        [data-compras-vista] :is(
            .st-key-cp_sem_escala, .st-key-cp_rank_escala, .st-key-cp_prod_escala,
            .st-key-cp_vol_escala, .st-key-cp_vap_f_escala, .st-key-cp_docs_escala
        ) button[data-testid="stPopoverButton"] p {
            font-size: 13px !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [data-testid="stButton"] button:hover {
            background: var(--ctl-gris) !important; color: var(--text-primary) !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [data-testid="stButton"] button.vista-en-pantalla {
            background: var(--accent-deep) !important; color: var(--bg-card) !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx [data-testid="stButton"] button.vista-en-pantalla p {
            font-weight: 600 !important;
        }
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx button.vista-en-pantalla::after {
            content: none !important;
        }
        /* El menú de reportes del área («Compras ▾»): cuelga de la barra, aparte. */
        :root .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx .st-key-nav_franja_secciones {
            display: none !important;
        }
        :root[data-franja-menu="ruta-secciones"] .st-key-nav_franja_rep .st-key-nav_franja_idx.st-key-nav_franja_idx .st-key-nav_franja_secciones {
            display: block !important;
            position: absolute !important;
            top: calc(100% - 4px) !important;
            left: var(--fr-x, 160px) !important;
            z-index: 1100 !important;
            box-sizing: border-box !important;
            width: 196px !important;
            padding: 5px !important;
            border-radius: 9px !important;
            border: 1px solid var(--border);
            background: var(--bg-card) !important;
            box-shadow: 0 8px 24px color-mix(in srgb, var(--text-primary) 12%, transparent) !important;
        }
    }
    @media (max-width: 900px) {
        html body .st-key-aj_tiempo_cabecera {
            gap: 8px !important; align-items: stretch !important;
            padding-bottom: 8px; border-bottom: 1px solid var(--border);
        }
        html body .st-key-aj_tiempo_cabecera > [data-testid="stLayoutWrapper"] {
            width: 100% !important; flex: 0 0 auto !important;
        }
        html body .st-key-ajevo_controles {
            flex-direction: row !important; justify-content: space-between !important;
            align-items: center !important; gap: 8px !important; width: 100% !important;
        }
    }
"""

# La misma presentación y tipografía entran en los shadow roots mediante css_movil().
CSS += "\n" + (Path(__file__).parent.parent / "graficos" / "pestanas.css").read_text(encoding="utf-8")
