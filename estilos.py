"""
Estilos globales de la app: CSS, tamaños de fuente e inyección del tema.

NOTA SOBRE st.pills (importante para futuros cambios de estilo):
En la versión actual de Streamlit, st.pills renderiza este DOM:

    div[data-testid="stButtonGroup"]  (con role="radiogroup")
        └── button[role="radio"]      (uno por opción)
                └── atributo `data-selected` SOLO cuando está activo

Por eso todos los selectores del "selector de vista" apuntan a
stButtonGroup / button[role="radio"] / [data-selected].
NO usar [data-testid="stPills"] ni `label` — no existen en este DOM.
Si Streamlit cambia el DOM en una actualización, verificar con DevTools
qué atributo marca el botón activo y actualizar SOLO el bloque
"SELECTOR DE VISTA" (hay uno único, buscar ese título).
"""

import streamlit as st


# ===========================================================================
# MAPEO DE TAMAÑOS DE FUENTE
# ===========================================================================

TAM_FUENTE = {
    "Pequeño": 12,
    "Mediano": 14,
    "Grande": 17,
    "Muy grande": 20
}


# ===========================================================================
# CSS GLOBAL (CACHEADO)
# ===========================================================================

@st.cache_data
def get_css():
    """Retorna el CSS como string (cacheado para no reinyectar)."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

    /* ============ PALETA DE COLORES — TEMA CALLAI (Lavender Indigo) ============ */
    :root {
        --bg-primary: #f6f6f8;      /* lienzo general */
        --bg-secondary: #ffffff;
        --bg-sidebar: #ffffff;      /* sidebar blanco estilo CallAI */
        --bg-card: #ffffff;
        --bg-hover: #f0edfe;        /* hover lavanda suave */
        --text-primary: #18181d;    /* casi negro */
        --text-secondary: #71717a;
        --text-muted: #a2a2ad;
        --accent: #6c5ce7;          /* Lavender Indigo */
        --accent-hover: #5a4ad9;
        --accent-deep: #4938b8;
        --accent-light: #e7e3fb;    /* lavanda 100 */
        --accent-tint: #f0edfe;     /* lavanda 50 */
        --border: #e6e6eb;
        --success: #16a34a;
        --success-bg: #f0fdf4;
        --warning: #f97316;
        --warning-bg: #fff7ed;
        --warning-border: #fdba74;
        --warning-text: #c2410c;
        --danger: #ef4444;
        --danger-bg: #fee2e2;
        --danger-border: #fca5a5;
        --danger-text: #991b1b;
        --border-lavender: #d4cdf7; /* borde lavanda de pastillas/inputs */
        --icon-muted: #85858f;
        --focus-lavender: #b9aff2;  /* borde de foco/selección */
        --line-soft: #f1f1f4;
        --exit-hover: #52525c;
        --scroll-thumb: #d6d6dd;
        --shadow: 0 1px 3px rgba(16, 16, 20, 0.05), 0 1px 2px rgba(16, 16, 20, 0.04);
        --shadow-md: 0 4px 6px rgba(16, 16, 20, 0.05), 0 2px 4px rgba(16, 16, 20, 0.03);

        /* ==================================================================
           GEOMETRÍA DE LA CABECERA FIJA — AJUSTE DE INVENTARIO
           Única fuente de verdad de la franja blanca superior. Todos los
           elementos fijados (banda, pestañas, chips) y la compensación del
           contenido derivan de estas variables. NUNCA escribir estos px
           sueltos en otras reglas; consumir siempre la variable.
           Mapa completo de knobs: ver arquitectura.md § Cabecera fija.
           ================================================================== */
        --cab-altura: 104px;
        --cab-nivel1-top: 30px;
        --cab-nivel2-top: 52px;
        --cab-offset-contenido: 112px;

        /* ==================================================================
           BARRA INFERIOR DE NAVEGACIÓN EN MÓVIL (bottom nav)
           Debe coincidir con NAV_MOVIL_ALTO en navegacion.py (60px).
           ================================================================== */
        --nav-movil-alto: 60px;
    }

    /* ============ HEADER NATIVO + ESPACIO SUPERIOR ============ */
    header[data-testid="stHeader"],
    .stAppHeader {
        background: transparent !important;
        border-bottom: none !important;
        box-shadow: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    /* PADDING SUPERIOR — DEFAULT GLOBAL (nivel 1 de 3).
       Jerarquía documentada en ARQUITECTURA.md:
         1) Este default global (1.5rem).
         2) Override POR SECCIÓN en navegacion.py (p.ej. _CSS_AJUSTE, 0.85rem).
         3) Override MÓVIL en el @media (max-width: 768px) de este fichero. */
    .stMainBlockContainer,
    [data-testid="stMainBlockContainer"],
    .block-container {
        padding-top: 1.5rem !important;
    }

    [data-testid="stSidebarHeader"] {
        height: 2rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* ============ IFRAMES INVISIBLES (por defecto) ============ */
    [data-testid="stIFrame"] {
        height: 0 !important;
        min-height: 0 !important;
        display: block !important;
    }
    [data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    /* ============ EXCEPCIÓN: PANEL DE RENDIMIENTO DEL NAVEGADOR ============ */
    .st-key-perf_browser_expander [data-testid="stIFrame"] {
        height: 300px !important;
        min-height: 300px !important;
        display: block !important;
    }
    .st-key-perf_browser_expander [data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {
        height: auto !important;
        min-height: 300px !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
    }

    /* ============ BOTÓN PARA EXPANDIR EL SIDEBAR ============ */
    [data-testid*="SidebarCollaps"],
    [data-testid="collapsedControl"],
    [data-testid*="xpandSidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    /* ============ ESTILOS BASE ============ */
    [data-testid="stAppViewContainer"] {
        background: var(--bg-primary);
    }

    h1 {
        margin-bottom: 0.2rem !important;
        padding-top: 0 !important;
        color: var(--text-primary) !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] {
        background: var(--bg-sidebar);
        border-right: 1px solid var(--border);
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-primary);
    }

    h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    h4 {
        color: var(--accent) !important;
        font-weight: 600 !important;
    }

    label {
        color: var(--text-secondary) !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        font-weight: 600 !important;
    }

    /* ============ INPUTS Y BOTONES ============ */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stDateInput > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }

    .stSelectbox > div > div:hover,
    .stMultiSelect > div > div:hover {
        border-color: var(--accent) !important;
    }

    button[kind="secondary"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }

    button[kind="secondary"]:hover {
        background: var(--bg-hover) !important;
        border-color: var(--accent) !important;
    }

    button[kind="primary"] {
        background: var(--accent) !important;
        border: none !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(108, 92, 231, 0.28) !important;
    }

    button[kind="primary"]:hover {
        background: var(--accent-hover) !important;
    }

    /* ============ EXPANDER ============ */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }

    /* ============ CAPTION Y ALERTAS ============ */
    .stCaption {
        color: var(--text-muted) !important;
    }

    .stWarning {
        background: var(--warning-bg) !important;
        border: 1px solid var(--warning-border) !important;
        color: var(--warning-text) !important;
        border-radius: 8px !important;
    }

    .stInfo {
        background: var(--accent-light) !important;
        border: 1px solid var(--focus-lavender) !important;
        color: var(--accent-deep) !important;
        border-radius: 8px !important;
    }

    .stError {
        background: var(--danger-bg) !important;
        border: 1px solid var(--danger-border) !important;
        color: var(--danger-text) !important;
        border-radius: 8px !important;
    }

    /* ============ SIDEBAR NAV ============ */
    [data-testid="stSidebar"] .nav-link {
        background: var(--bg-secondary) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] .nav-link:hover {
        background: var(--bg-hover) !important;
        color: var(--accent-hover) !important;
        border-color: var(--focus-lavender) !important;
    }

    [data-testid="stSidebar"] .nav-link-selected {
        background: var(--accent) !important;
        color: var(--bg-secondary) !important;
        border-color: var(--accent) !important;
    }

    /* ============ AGGRID - ANCHO COMPLETO ============ */
    .ag-root-wrapper {
        width: 100% !important;
        max-width: 100% !important;
    }

    .ag-body-viewport {
        overflow-x: auto !important;
    }

    /* ============ CONTROL DE TAMAÑO EN SIDEBAR ============ */
    [data-testid="stSidebar"] .stSlider {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* ============ MÓVIL — LAYOUT GENERAL ============ */
    @media screen and (max-width: 768px) {
        header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
            border-bottom: none !important;
        }

        [data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }

        [data-testid="stMain"] {
            padding: 0.5rem 0.5rem !important;
            margin-top: 0 !important;
        }

        .block-container,
        .stMainBlockContainer {
            padding: 0.5rem !important;
            margin-top: 0 !important;
            gap: 0 !important;
        }

        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        [data-testid="stSidebar"] {
            max-height: 100vh;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            -webkit-overflow-scrolling: touch;
            background: var(--bg-sidebar) !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        [data-testid="stSidebarUserContent"] {
            padding: 12px 8px !important;
        }

        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stExpandSidebarButton"] button,
        [data-testid="collapsedControl"] button {
            width: 44px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 8px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        h1 {
            font-size: 1.3rem !important;
            margin-top: 0 !important;
            padding-top: 0.5rem !important;
        }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 1rem !important; }
        label { font-size: 0.7rem !important; }

        .stApp { padding: 0 !important; }

        button {
            min-height: 44px !important;
            padding: 10px 16px !important;
            font-size: 0.9rem !important;
        }
    }

    /* =================================================================== */
    /* SELECTOR DE VISTA (Tabla / Gráficos) — ÚNICO BLOQUE — OPCIÓN C       */
    /*                                                                      */
    /* Estilo "botones ghost":                                              */
    /*   · Contenedor: sin fondo, sin borde.                                */
    /*   · Inactivo:   transparente, texto gris secundario.                 */
    /*   · Hover:      tinte lavanda suave (accent-tint).                   */
    /*   · ACTIVO:     fondo índigo sólido (accent) + texto blanco.         */
    /*                                                                      */
    /* DOM real de st.pills (confirmado con DevTools, ver docstring):       */
    /*   [data-testid="stButtonGroup"] > button[role="radio"]               */
    /*   El activo lleva el atributo `data-selected` (a secas).             */
    /*                                                                      */
    /* Cubre los DOS contextos donde vive el selector:                      */
    /*   · .st-key-ajuste_tabs_top      → franja fija de Ajuste             */
    /*   · [class*="st-key-vistatabs_"] → resto de reportes                 */
    /* Para añadir otro contexto, sumar su selector a cada regla.           */
    /* =================================================================== */

    /* --- Contenedor del grupo --- */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"],
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] {
        display: inline-flex !important;
        width: fit-content !important;
        gap: 4px !important;
        margin: 8px 0 0 !important;
        padding: 0 !important;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        flex-wrap: nowrap !important;
    }

    /* --- Botón base (estado inactivo) --- */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"],
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] {
        min-height: 42px !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        border: none !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
        box-shadow: none !important;
        cursor: pointer !important;
        transition: color .15s ease, background .15s ease !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"] p,
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] p {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: inherit !important;
        margin: 0 !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"] [data-testid="stIconMaterial"],
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] [data-testid="stIconMaterial"] {
        font-size: 18px !important;
        color: inherit !important;
    }

    /* --- Hover sobre botón inactivo --- */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"]:hover:not([data-selected]),
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"]:hover:not([data-selected]) {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }

    /* --- Botón ACTIVO (data-selected) --- */
    /* Se replica la estructura del selector nativo de Streamlit
       (button[data-selected]:not([data-disabled])) para igualar o superar
       su especificidad y que nuestro estilo gane. */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]),
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]) {
        background: var(--accent) !important;      /* índigo SÓLIDO */
        border: none !important;
        box-shadow: none !important;
        color: #ffffff !important;
    }
    /* Texto e icono internos en blanco, gane quien gane la cascada */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]) *,
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]) * {
        color: #ffffff !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]):hover,
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]):hover {
        background: var(--accent-hover) !important;
    }

    /* =================================================================== */
    /* BOTÓN FILTROS (popover) — a juego, grande y con contorno índigo      */
    /* =================================================================== */
    [data-testid="stPopover"] button {
        min-width: 180px !important;
        padding: 14px 26px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 999px !important;
        transition: all .15s ease !important;
    }
    [data-testid="stPopover"] button:hover {
        border-color: var(--accent-hover) !important;
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }

    /* =================================================================== */
    /* FILA SUPERIOR DE AJUSTE DE INVENTARIO                                */
    /* =================================================================== */
    /* FRANJA BLANCA SUPERIOR — banda de borde a borde tras título + fecha. */
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
        left: 90px !important;      /* comienza inmediatamente tras el rail */
        right: 0 !important;
        height: var(--cab-altura) !important;
        background: #ffffff !important;
        border-bottom: 1px solid var(--border) !important;
        box-shadow: 0 2px 4px rgba(16, 16, 20, 0.04) !important;
        z-index: 0 !important;
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

    /* Contenedor del selector de vista, fijado en el nivel 2 de la franja */
    .st-key-ajuste_tabs_top {
        position: fixed !important;
        top: var(--cab-nivel2-top) !important;
        left: calc(90px + 4rem) !important;
        z-index: 22 !important;
        transform: none !important;
        margin: 0 !important;
    }

    /* ================================================================== */
    /* CHIPS DE FILTRO EN LA FRANJA BLANCA — Área / Familia / Ajuste /     */
    /* Ajuste valor.  Nivel 2, a la derecha del selector de vista.         */
    /* ================================================================== */
    /* Sub-paso 2 del rediseño: los filtros suben al NIVEL 1 (fila del
       título), a la izquierda del widget de fecha. El offset derecho deja
       ~260px para la píldora de fecha (01/.. – ../..). Ajustable si roza. */
    .st-key-chips_ajuste_tabla {
        position: fixed !important;
        top: 6px !important;
        right: 280px !important;
        left: auto !important;
        width: auto !important;
        max-width: calc(100vw - 90px - 620px) !important;
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
    /* Ancho uniforme (en vez de ajustarse al largo de cada texto) + tono
       lavanda que los resalta levemente, a juego con el resto de la webapp. */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        min-width: 0 !important;
        width: 132px !important;
        min-height: 26px !important;
        height: 26px !important;
        padding: 3px 10px !important;
        font-size: 12px !important;
        background: var(--accent-tint) !important;
        border: 1px solid var(--border-lavender) !important;
        color: var(--accent-deep) !important;
        overflow: hidden !important;
        gap: 4px !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button p {
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
        font-size: 14px !important;
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

    /* Título del reporte, fijo en el nivel 1 de la franja */
    .titulo-ajuste-reporte {
        position: fixed !important;
        top: 6px !important;
        left: calc(90px + 1rem) !important;
        z-index: 22 !important;
        margin: 0 !important;
        color: var(--text-primary) !important;
        font-family: 'Corbel', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        text-transform: uppercase !important;
        font-size: 27px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        letter-spacing: 0.01em !important;
        transform: none !important;
    }

    /* Chip pill del título del reporte */
    .chip-titulo-reporte {
        display: inline-flex;
        align-items: center;
        background: var(--accent-tint);
        color: var(--accent-deep);
        border-radius: 999px;
        padding: 8px 18px;
        font-size: 15px;
        font-weight: 500;
        line-height: 1;
        white-space: nowrap;
        letter-spacing: 0.01em;
    }

    /* =================================================================== */
    /* PILL LAVANDA — date_input de Ajuste de Inventario                    */
    /* Fijado en la esquina superior derecha de la franja blanca.           */
    /* CAMBIO: position:fixed + top/right explícitos reemplazan el          */
    /* margin:auto anterior (que solo funcionaba en flujo normal).          */
    /* =================================================================== */
.st-key-fecha_ajuste_pill {
    position: fixed !important;
    top: 6px !important;
    right: 16px !important;
    left: auto !important;          /* nada lo ancla a la izquierda */
    width: fit-content !important;  /* la caja se encoge al input   */
    z-index: 23 !important;
    margin: 0 !important;
}

    [class*="st-key-fch_franja_"] [data-baseweb="input"] {
        width: auto !important;
        min-width: 0 !important;
    }

    /* CAMBIO: margin:0 (antes era "0 24px 0 auto") — el posicionamiento
       ahora lo controla el padre fixed, no el margen automático.
       Forma RECTANGULAR (esquinas suaves) y fondo blanco: se distingue de
       las cápsulas lavanda de filtro, que son píldoras con fondo tenue. */
    [class*="st-key-fch_franja_"] .stDateInput > div > div {
        background: #ffffff !important;
        border: 1.5px solid var(--accent) !important;
        border-radius: 8px !important;
        box-shadow: var(--shadow) !important;
        padding: 0 12px !important;
        min-height: 34px !important;
        height: 34px !important;
        width: fit-content !important;
        margin: 0 !important;
        overflow: visible !important;
        position: relative !important;
        transition: background .15s ease, border-color .15s ease !important;
    }

    .ultima-actualizacion {
        margin: 0 !important;
        color: var(--text-muted) !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        text-align: right !important;
        white-space: nowrap !important;
    }

    [class*="st-key-fch_franja_"] .stDateInput input {
        color: var(--accent-deep) !important;
        font-weight: 500 !important;
        font-size: 12.5px !important;
        background: transparent !important;
        text-align: center !important;
        padding: 0 !important;
        width: 155px !important;
    }
    [class*="st-key-fch_franja_"] .stDateInput input::placeholder {
        color: var(--accent) !important;
        opacity: 0.7 !important;
    }

    [class*="st-key-fch_franja_"] .stDateInput > div > div:hover,
    [class*="st-key-fch_franja_"] .stDateInput > div > div:focus-within {
        background: var(--accent-tint) !important;
        border-color: var(--accent-deep) !important;
    }

    [class*="st-key-fch_franja_"] .stDateInput > div > div::before {
        display: none !important;
    }

    /* =================================================================== */
    /* CALENDARIO DESPLEGABLE (BaseWeb) — marco suave, sin presets          */
    /* =================================================================== */
    div[data-baseweb="calendar"] {
        border-radius: 12px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10) !important;
        font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    div[data-baseweb="calendar"] [role="gridcell"] > div {
        border-radius: 8px !important;
    }
    div[data-baseweb="calendar"] button svg {
        fill: var(--accent) !important;
    }
    div[data-baseweb="popover"]:has(div[data-baseweb="calendar"]) [data-baseweb="select"] {
        display: none !important;
    }
    div[data-baseweb="popover"]:has(div[data-baseweb="calendar"]) div[data-baseweb="calendar"] + div {
        display: none !important;
    }

    /* =================================================================== */
    /* OCULTAR TOOLBARS NATIVAS DE STREAMLIT                                */
    /* =================================================================== */
    [data-testid="stToolbar"],
    [data-testid="stMainMenu"],
    [data-testid="stAppDeployButton"],
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    /* Botón "Manage app" de Streamlit Community Cloud (abajo a la derecha;
       en móvil tapa la barra de navegación inferior). Las clases van con
       hash y cambian entre versiones, por eso el selector por substring. */
    [data-testid="manage-app-button"],
    div[class*="viewerBadge"] {
        display: none !important;
    }
    [class*="st-key-grid_"] [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* =================================================================== */
    /* POSICIÓN DEL TOAST (st.toast) — junto al rail (RAIL_ANCHO=90px+10)   */
    /* =================================================================== */
    div[data-testid="stToastContainer"] {
        left: 100px !important;
        right: auto !important;
        bottom: 16px !important;
        top: auto !important;
    }

    /* =================================================================== */
    /* AVISO DE REFRESCO EN CURSO — flotante junto al botón del rail        */
    /* =================================================================== */
    .st-key-aviso_refresco {
        position: fixed !important;
        left: 100px !important;
        bottom: 16px !important;
        max-width: 320px !important;
        z-index: 999997 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
        border-radius: 8px !important;
    }

    /* =================================================================== */
    /* CARDS DE GRÁFICOS — contenedor blanco con bordes redondeados         */
    /* =================================================================== */
    .chart-card {
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.25rem 1.5rem 0.75rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
        position: relative;
        padding-bottom: 2.5rem;  /* espacio para el pie */
    }

    .chart-card-title {
        position: absolute;
        left: 0; right: 0; bottom: 0;
        font-size: 11px;
        font-weight: 600;
        color: var(--accent);
        background: var(--accent-tint, #EEEDFE);
        border-top: 1px solid var(--accent, #7F77DD);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 8px 1.5rem;
        margin: 0;
        line-height: 1;
        border-bottom-left-radius: inherit;
        border-bottom-right-radius: inherit;
    }

    .streamlit-expanderContent .chart-card {
        border: none !important;
        box-shadow: none !important;
        padding: 0.25rem 0 0 !important;
    }

    div[class*="st-key-ajuste_graf_card_"] {
        background: var(--surface-2, #ffffff) !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
    }
    div[class*="st-key-ajuste_graf_card_"] > div {
        border: none !important;
    }
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"],
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"] > div,
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"]
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* Chips de tipo de gráfico dentro de la tarjeta (también st.pills →
       stButtonGroup). Conservan forma de píldora redonda para
       diferenciarse del selector de vista. */
    div[class*="st-key-ajuste_graf_card_izq_"] [data-testid="stButtonGroup"] {
        gap: 8px !important;
        flex-wrap: wrap !important;
        margin-bottom: 8px !important;
    }
    div[class*="st-key-ajuste_graf_card_izq_"] [data-testid="stButtonGroup"] button {
        min-height: 36px !important;
        padding: 8px 14px !important;
        font-size: 13px !important;
        border-radius: 999px !important;
    }

    /* =================================================================== */
    /* FRANJA INFERIOR FIJA — cierra visualmente el área de contenido       */
    /* =================================================================== */
    .stApp::after {
        content: "" !important;
        position: fixed !important;
        left: 90px !important; /* coincide con el ancho del rail */
        right: 0 !important;
        bottom: 0 !important;
        height: 42px !important;
        background: #ffffff !important;
        border-top: 1px solid var(--border) !important;
        box-shadow: 0 -2px 4px rgba(16, 16, 20, 0.04) !important;
        pointer-events: none !important;
        z-index: 999990 !important;
    }
    [data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    .block-container {
        padding-bottom: 66px !important;
    }

    /* Texto "Última actualización" anclado a la franja inferior fija */
    .st-key-footer_actualizacion {
        position: fixed !important;
        left: 90px !important;
        right: 0 !important;
        bottom: 0 !important;
        height: 42px !important;
        display: flex !important;
        align-items: center !important;
        /* A la IZQUIERDA de la franja: la esquina derecha la ocupa el botón
           'Manage app' de Streamlit Cloud y tapaba el texto. */
        justify-content: flex-start !important;
        padding: 0 24px !important;
        margin: 0 !important;
        z-index: 999991 !important; /* por encima de .stApp::after */
        pointer-events: none !important;
        /* El bloque vertical de Streamlit es columna con gap: en fila y sin
           separaciones el texto queda centrado DENTRO de la franja de 42px
           (antes desbordaba por debajo del viewport). */
        flex-direction: row !important;
        gap: 0 !important;
    }
    .st-key-footer_actualizacion > div {
        height: auto !important;
        margin: 0 !important;
    }
    .st-key-footer_actualizacion .ultima-actualizacion {
        margin: 0 !important;
        font-size: 12px !important;
        color: var(--text-muted, #9aa0a6) !important;
        white-space: nowrap !important;
    }

    /* =================================================================== */
    /* MÓVIL — AJUSTE DE INVENTARIO Y ELEMENTOS FIJOS                       */
    /* ÚNICO @media final: agrupa todos los overrides móviles de la sección */
    /* Ajuste + selector de vista + franjas fijas. Va al final para que no  */
    /* lo pisen los estilos de escritorio definidos arriba.                 */
    /* =================================================================== */
    @media screen and (max-width: 768px) {
        /* Encabezado de Ajuste: sin rail a la izquierda (nav es barra
           inferior en móvil), los anclajes left pasan de 90px+margen a 12px. */
        .titulo-ajuste-reporte {
            transform: none !important;
            font-size: 1.3rem !important;
            left: 12px !important;
            /* No pisarse con la pill de fecha fija de la derecha */
            max-width: calc(100vw - 220px) !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
        }
        .st-key-ajuste_tabs_top {
            transform: none !important;
            left: 12px !important;
        }
        /* COLAPSAR el hueco fantasma de la franja: en móvil TODO su
           contenido visible (título, pestañas, fecha) es position:fixed,
           así que su altura en el flujo es espacio muerto — y al apilarse
           las columnas en vertical, ese hueco crece. Se anula la altura y
           el margin-top negativo (que compensaba al padding del contenedor)
           para que el contenido arranque justo bajo la franja fija. */
        .st-key-fila_ajuste_top {
            position: static !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        /* ORDEN DE APILAMIENTO al scrollear (verificado en el DOM real):
           banda blanca (15) TAPA al contenido que sube; los hijos de la
           franja (título/pestañas/fecha, 16) quedan encima de la banda.
           Los chips vuelven a z auto: su z:23 de escritorio aplica aunque
           estén static, porque son flex items — y los ponía sobre la banda. */
        .st-key-fila_ajuste_top::before {
            left: 0 !important;
            z-index: 15 !important;
        }
        .st-key-fila_ajuste_top > * {
            z-index: 16 !important;
        }
        .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] {
            gap: 4px !important;
            align-items: stretch !important;
        }

        /* La pill de fecha se mantiene FIJA también en móvil (anclada
           arriba a la derecha, dentro de la franja blanca) para que no
           se desplace con el scroll. El título lleva max-width con
           ellipsis (arriba) para que no se pisen en pantallas angostas. */
        .st-key-fecha_ajuste_pill {
            position: fixed !important;
            top: 6px !important;
            right: 8px !important;
            left: auto !important;
            margin: 0 !important;
            z-index: 23 !important;
        }
        [class*="st-key-fch_franja_"] .stDateInput input {
            width: 140px !important;
            font-size: 11.5px !important;
        }

        /* Selector de vista: mantiene Opción C, más compacto para tocar */
        .st-key-ajuste_tabs_top [data-testid="stButtonGroup"],
        [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] {
            gap: 4px !important;
        }
        .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"],
        [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] {
            min-height: 40px !important;
            padding: 9px 14px !important;
            font-size: 13px !important;
        }

        /* Popovers: no crear scroll lateral */
        [data-testid="stPopover"] button {
            min-width: 0 !important;
            max-width: 100% !important;
        }

        /* Chips pegados a la franja (el margen de 6px es para tablet) */
        .st-key-chips_ajuste_tabla {
            margin: 2px 0 0 0 !important;
            z-index: auto !important;
        }

        /* Avisos: sobre la barra inferior de navegación */
        div[data-testid="stToastContainer"],
        .st-key-aviso_refresco {
            left: 12px !important;
            right: 12px !important;
            max-width: none !important;
            bottom: calc(var(--nav-movil-alto) + 44px) !important;
        }

        /* Chips de Ajuste: 2×2 en móvil en lugar de 4 apilados */
        .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 1 1 calc(50% - 8px) !important;
            min-width: calc(50% - 8px) !important;
            width: calc(50% - 8px) !important;
        }

        /* Franja inferior + footer: se apoyan sobre la barra nav móvil */
        .stApp::after {
            left: 0 !important;
            height: 34px !important;
            bottom: var(--nav-movil-alto) !important;
        }
        .st-key-footer_actualizacion {
            left: 0 !important;
            padding: 0 12px !important;
            bottom: var(--nav-movil-alto) !important;
            height: 34px !important;
        }
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        .block-container {
            /* Reserva: barra nav (60) + franja (34) + 10 de aire */
            padding-bottom: 104px !important;
        }
    }

    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
