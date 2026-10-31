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
"""
