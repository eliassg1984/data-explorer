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

CSS = """
    @media (min-width: 901px) {
    :root:has(.st-key-compras_tabs_row),
    :root:has(.st-key-compras_tabs_row) body,
    :root:has(.st-key-compras_tabs_row) [data-testid="stAppViewContainer"] {
        background: var(--marco-fondo) !important;
    }
    :root {
        --marco-der: calc(var(--marco-hoja) + 8px);
        /* En la hoja la tarjeta no lleva margen: esos 16px son de contenido. */
        --margen-tarjeta: 0px;
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
        margin: var(--marco-hoja) var(--marco-hoja) var(--marco-hoja)
                var(--rail-reserva) !important;
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
    /* #796: el renglón de «Ver» de Stock es el nivel 2 de Costo de Carta: sin el
       título (está en la franja), las perspectivas subrayadas y una raya de borde
       a borde debajo. La pieza pone a la derecha «Detalle» y «Cómo se calcula». */
    .st-key-persp_stock .persp-tit { display: none; }
    .st-key-persp_stock.st-key-persp_stock {
        border-bottom: 1px solid var(--border);
        margin-left: -18px !important;
        margin-right: -18px !important;
        padding: 0 18px;
    }
    .st-key-persp_stock.st-key-persp_stock [data-testid="stButtonGroup"] {
        background: none;
        padding: 0;
        gap: 18px !important;
    }
    .st-key-persp_stock.st-key-persp_stock [data-testid="stButtonGroup"] button {
        border-bottom: 2px solid transparent !important;
        padding: 0 !important;
        margin-right: 18px !important;
        height: 32px !important;
        min-height: 32px !important;
    }
    .st-key-persp_stock.st-key-persp_stock [data-testid="stButtonGroup"] button[aria-checked="true"],
    .st-key-persp_stock.st-key-persp_stock [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
        background: transparent !important;
        box-shadow: none;
        border-bottom-color: var(--accent) !important;
    }
    .st-key-persp_stock.st-key-persp_stock [data-testid="stButtonGroup"] button[aria-checked="true"] p,
    .st-key-persp_stock.st-key-persp_stock [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] p {
        color: var(--text-primary) !important;
    }
    /* #799: lo mismo en Evolución (Serie | Tabla dinámica), desde el renglón de «Ver»: #796 — de Costo de Carta: sin el
       rótulo «Ver», las perspectivas subrayadas y una raya de borde
       a borde debajo. La pieza pone a la derecha «Detalle» y «Cómo se calcula». */
    .st-key-persp_tiempo .persp-rot { display: none; }
    .st-key-persp_tiempo.st-key-persp_tiempo {
        border-bottom: 1px solid var(--border);
        margin-left: -18px !important;
        margin-right: -18px !important;
        padding: 0 18px;
    }
    .st-key-persp_tiempo.st-key-persp_tiempo [data-testid="stButtonGroup"] {
        background: none;
        padding: 0;
        gap: 18px !important;
    }
    .st-key-persp_tiempo.st-key-persp_tiempo [data-testid="stButtonGroup"] button {
        border: 0 !important;
        border-radius: 0 !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
        padding: 0 !important;
        margin-right: 18px !important;
        height: 32px !important;
        min-height: 32px !important;
    }
    .st-key-persp_tiempo.st-key-persp_tiempo [data-testid="stButtonGroup"] button[aria-checked="true"],
    .st-key-persp_tiempo.st-key-persp_tiempo [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] {
        background: transparent !important;
        box-shadow: none;
        border-bottom-color: var(--accent) !important;
    }
    .st-key-persp_tiempo.st-key-persp_tiempo [data-testid="stButtonGroup"] button[aria-checked="true"] p,
    .st-key-persp_tiempo.st-key-persp_tiempo [data-testid="stButtonGroup"] button[kind="segmented_controlActive"] p {
        color: var(--text-primary) !important;
    }
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
        top: var(--marco-hoja) !important;
        right: var(--marco-hoja) !important;
        border-radius: var(--marco-radio) var(--marco-radio) 0 0 !important;
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
    .st-key-rail_refresh {
        top: calc(var(--marco-hoja) + (var(--franja-rep-alto) - 30px) / 2) !important;
        right: calc(var(--marco-der) + var(--barra-f)) !important;
    }
    #sello-actualizacion {
        top: calc(var(--marco-hoja) + (var(--franja-rep-alto) - 30px) / 2) !important;
        right: calc(var(--marco-der) + var(--barra-f) + 96px + 8px
                    + var(--barra-fecha)) !important;
    }
    .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
        top: calc(var(--marco-hoja) + (var(--franja-rep-alto) - 30px) / 2) !important;
        right: var(--marco-der) !important;
        border-left: none !important;
        background: transparent !important;
    }
    .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill {
        top: calc(var(--marco-hoja) + (var(--franja-rep-alto) - 30px) / 2) !important;
        right: calc(var(--marco-der) + var(--barra-f) + 96px + 8px) !important;
    }
    .st-key-rail_refresh button,
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
    .st-key-rail_refresh button:hover,
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
"""
