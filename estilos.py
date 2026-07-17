"""
Estilos globales de la app: CSS, tamaños de fuente e inyección del tema.
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
        --success: #16a34a;         /* verde tipo badge "Outbound" */
        --success-bg: #f0fdf4;
        --warning: #f97316;         /* naranja tipo badge "Inbound" */
        --warning-bg: #fff7ed;
        --warning-border: #fdba74;  /* borde de alerta de advertencia */
        --warning-text: #c2410c;    /* texto sobre fondo de advertencia */
        --danger: #ef4444;
        --danger-bg: #fee2e2;       /* fondo de alerta de error */
        --danger-border: #fca5a5;   /* borde de alerta de error */
        --danger-text: #991b1b;     /* texto rojo oscuro de error */
        --border-lavender: #d4cdf7; /* borde lavanda de pastillas/inputs */
        --icon-muted: #85858f;      /* gris neutro de iconos (calendario) */
        --focus-lavender: #b9aff2;  /* borde de foco/selección */
        --line-soft: #f1f1f4;       /* línea divisoria muy suave (= GRIS_LINEA) */
        --exit-hover: #52525c;      /* hover del botón salir de pantalla completa */
        --scroll-thumb: #d6d6dd;    /* pulgar de scrollbar en paneles */
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
        --cab-nivel2-top: 40px;
        --cab-offset-contenido: 112px;

        /* ==================================================================
           BARRA INFERIOR DE NAVEGACIÓN EN MÓVIL (bottom nav)
           Debe coincidir con NAV_MOVIL_ALTO en navegacion.py (60px). Todos
           los elementos fijos del pie en móvil (franja ::after, footer de
           actualización, toasts) se apoyan sobre esta altura.
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
         2) Override POR SECCIÓN en navegacion.py (p.ej. _CSS_AJUSTE, 0.85rem),
            que gana a propósito vía prefijo `html body`.
         3) Override MÓVIL en el @media (max-width: 768px) de este fichero.
       Si quieres cambiar el espacio de UNA sección, NO toques esto:
       edita su bloque en navegacion.py. */
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
    /* Estos iframes son para componentes auxiliares (overlay de errores,
       inspector de elementos, toggle del sidebar, etc.) y deben
       permanecer ocultos. */
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
    /* Este iframe SÍ debe mostrarse (perf.render_browser_panel).
       El expander tiene la key "perf_browser_expander", que genera una clase
       .st-key-perf_browser_expander en el contenedor padre.
       Usamos esa clase para seleccionar el iframe dentro de él. */
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
    }

    [data-testid="stSidebar"] { 
        background: var(--bg-sidebar); 
        border-right: 1px solid var(--border); 
    }

    html, body, [class*="css"] { 
        font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
        color: var(--text-primary); 
    }

    h1 { 
        color: var(--text-primary) !important; 
        font-size: 1.6rem !important; 
        font-weight: 700 !important; 
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

    /* ============ SIDEBAR ============ */
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

    /* ============ MÓVIL ============ */
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
        
        [data-testid="stSidebar"] { 
            width: 100% !important;
            max-width: 100% !important;
        }
    }

    /* =================================================================== */
    /* SELECTOR DE VISTA — botones ghost (Opción C)                        */
    /* La vista activa se llena con el color acento; la inactiva es plana. */
    /* =================================================================== */
    [class*="st-key-vistatabs_"] [role="radiogroup"],
    .st-key-ajuste_tabs_top [role="radiogroup"] {
        display: inline-flex !important;
        width: fit-content !important;
        gap: 4px !important;
        margin: 8px 0 0 !important;
        padding: 0 !important;
        background: transparent !important;   /* ← sin fondo lavanda */
        border: none !important;              /* ← sin borde contenedor */
        border-radius: 0 !important;
    }

    /* Streamlit renderiza cada opción como un radio real. Se conserva para
       accesibilidad y clic, pero se oculta su indicador circular. */
    [class*="st-key-vistatabs_"] [role="radiogroup"] [data-baseweb="radio"],
    .st-key-ajuste_tabs_top [role="radiogroup"] [data-baseweb="radio"] {
        display: none !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] input[type="radio"],
    .st-key-ajuste_tabs_top [role="radiogroup"] input[type="radio"] {
        appearance: none !important;
        -webkit-appearance: none !important;
        opacity: 0 !important;
        position: absolute !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
    }
    /* Indicador visual que renderiza Streamlit alrededor del radio. */
    [class*="st-key-vistatabs_"] [role="radiogroup"] .st-emotion-cache-pabt4k,
    .st-key-ajuste_tabs_top [role="radiogroup"] .st-emotion-cache-pabt4k,
    [class*="st-key-vistatabs_"] [role="radiogroup"] .st-emotion-cache-mzkh7q,
    .st-key-ajuste_tabs_top [role="radiogroup"] .st-emotion-cache-mzkh7q {
        display: none !important;
    }
    /* Variante inactiva: el indicador puede usar otra clase de Emotion.
       Es el primer div inmediatamente después del radio dentro del label. */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label > input[type="radio"] + div,
    .st-key-ajuste_tabs_top [role="radiogroup"] label > input[type="radio"] + div {
        display: none !important;
    }

    /* Cada opción = un botón ghost */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label,
    .st-key-ajuste_tabs_top [role="radiogroup"] label {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 7px 16px !important;
        border: none !important;
        border-radius: 8px !important;        /* ← esquinas suaves, no píldora */
        background: transparent !important;   /* ← inactivo: plano */
        cursor: pointer !important;
        transition: color .15s ease, background .15s ease !important;
    }

    /* Texto e icono inactivos (gris secundario) */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label p,
    .st-key-ajuste_tabs_top [role="radiogroup"] label p {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        margin: 0 !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label [data-testid="stIconMaterial"],
    .st-key-ajuste_tabs_top [role="radiogroup"] label [data-testid="stIconMaterial"] {
        font-size: 16px !important;
        color: inherit !important;
        vertical-align: -2px;
    }

    /* Hover en la opción inactiva: leve tinte lavanda */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:hover,
    .st-key-ajuste_tabs_top [role="radiogroup"] label:hover {
        background: var(--accent-tint) !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:hover p,
    .st-key-ajuste_tabs_top [role="radiogroup"] label:hover p {
        color: var(--accent-deep) !important;
    }

    /* ACTIVO: fondo índigo sólido, texto blanco */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:has(input:checked),
    .st-key-ajuste_tabs_top [role="radiogroup"] label:has(input:checked) {
        background: var(--accent) !important;
        box-shadow: none !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:has(input:checked) p,
    .st-key-ajuste_tabs_top [role="radiogroup"] label:has(input:checked) p {
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:has(input:checked) [data-testid="stIconMaterial"],
    .st-key-ajuste_tabs_top [role="radiogroup"] label:has(input:checked) [data-testid="stIconMaterial"] {
        color: #ffffff !important;
    }

    /* Píldoras del selector Tabla / Gráficos: mayor área táctil y aire. */
    .st-key-ajuste_tabs_top [data-testid="stPills"] {
        gap: 10px !important;
        padding: 5px !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stPills"] button {
        min-height: 42px !important;
        padding: 10px 20px !important;
        font-size: 15px !important;
        border-radius: 999px !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stPills"] button [data-testid="stIconMaterial"] {
        font-size: 18px !important;
    }

    /* Las cinco vistas del gráfico viven dentro de su tarjeta y se acomodan
       en varias líneas antes de forzar scroll horizontal. */
    div[class*="st-key-ajuste_graf_card_izq_"] [data-testid="stPills"] {
        gap: 8px !important;
        flex-wrap: wrap !important;
        margin-bottom: 8px !important;
    }
    div[class*="st-key-ajuste_graf_card_izq_"] [data-testid="stPills"] button {
        min-height: 36px !important;
        padding: 8px 14px !important;
        font-size: 13px !important;
        border-radius: 999px !important;
    }

    /* Franja inferior fija: cierra visualmente el área de contenido. */
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

    /* Texto "Última actualización" anclado a la franja inferior fija.
       El fondo lo aporta .stApp::after; este contenedor solo coloca el texto
       encima (z-index mayor) alineado a la derecha. */
    .st-key-footer_actualizacion {
        position: fixed !important;
        left: 90px !important;      /* coincide con el rail, igual que ::after */
        right: 0 !important;
        bottom: 0 !important;
        height: 42px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        padding: 0 24px !important;
        margin: 0 !important;
        z-index: 999991 !important; /* por encima de .stApp::after (999990) */
        pointer-events: none !important;
    }
    .st-key-footer_actualizacion .ultima-actualizacion {
        margin: 0 !important;
        font-size: 12px !important;
        color: var(--text-muted, #9aa0a6) !important;
        white-space: nowrap !important;
    }
    @media (max-width: 768px) {
        .st-key-footer_actualizacion {
            left: 0 !important;
            padding: 0 12px !important;
            /* NUEVO: se apoya SOBRE la barra inferior de navegación y
               adopta la altura móvil de la franja (34px, igual que
               .stApp::after en móvil) para que texto y fondo coincidan. */
            bottom: var(--nav-movil-alto) !important;
            height: 34px !important;
        }
    }

    @media screen and (max-width: 768px) {
        .st-key-ajuste_tabs_top [data-testid="stPills"] {
            gap: 6px !important;
        }
        .st-key-ajuste_tabs_top [data-testid="stPills"] button {
            min-height: 40px !important;
            padding: 9px 14px !important;
            font-size: 14px !important;
        }
        .stApp::after {
            left: 0 !important;
            height: 34px !important;
            /* NUEVO: la franja blanca inferior sube y se apoya sobre la
               barra de navegación móvil (60px) en vez de pegarse al borde. */
            bottom: var(--nav-movil-alto) !important;
        }
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        .block-container {
            /* NUEVO: antes 52px. Ahora reserva barra nav (60) + franja (34)
               + 10 de aire para que la última fila de la tabla no quede
               tapada por los elementos fijos del pie. */
            padding-bottom: 104px !important;
        }
    }

    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
