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
    /* SELECTOR DE VISTA — tabs subrayados (underline), Estilo 1.           */
    /* Se aplica al st.radio horizontal envuelto en un contenedor con key   */
    /* "vistatabs_<reporte>" (clase .st-key-vistatabs_...).                 */
    /* =================================================================== */

    /* Fila de opciones: separación entre tabs + línea inferior guía */
    [class*="st-key-vistatabs_"] [role="radiogroup"] {
        gap: 26px !important;
        border-bottom: 1px solid var(--border) !important;
        margin-bottom: 0.4rem !important;
        padding: 0 0 0 16px !important;   /* ← antes: padding: 0 */
    }

    /* Ocultar el círculo del radio nativo */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label > div:first-child {
        display: none !important;
    }

    /* Cada opción = un tab (texto + subrayado en hover/activo) */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label {
        padding: 9px 2px !important;
        margin: 0 !important;
        cursor: pointer !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1px !important;   /* solapa la línea guía */
        transition: color .15s ease, border-color .15s ease !important;
    }

    /* Texto del tab en reposo (inactivo) */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label p {
        font-size: 16px !important;          /* antes: 14px */
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        margin: 0 !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
    }

    /* Hover: insinúa el subrayado */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:hover {
        border-bottom-color: var(--focus-lavender) !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:hover p {
        color: var(--accent-deep) !important;
    }

    /* Tab ACTIVO — Streamlit marca el label seleccionado con aria-checked */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:has(input:checked) {
        border-bottom-color: var(--accent) !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:has(input:checked) p {
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
    }

    /* Icono Material hereda el color del tab (gris inactivo / índigo activo) */
    [class*="st-key-vistatabs_"] [role="radiogroup"] label [data-testid="stIconMaterial"] {
        font-size: 19px !important;        /* antes: 17px */
        color: inherit !important;
        vertical-align: -3px;
    }

    /* =================================================================== */
    /* BOTÓN FILTROS (popover) — a juego, grande y con contorno índigo        */
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
    /* FILA SUPERIOR DE AJUSTE DE INVENTARIO — chip a la izquierda          */
    /* =================================================================== */
    .st-key-fila_ajuste_top {
        margin-top: -16px !important;          /* NUEVO: reduce el espacio superior */
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
    /* PILL LAVANDA — date_input de Ajuste de Inventario                   */
    /* =================================================================== */

    /* Ancho ajustado al texto de la fecha */
    .st-key-fch_ajuste_inline [data-baseweb="input"] {
        width: auto !important;
        min-width: 0 !important;
    }

    /* La caja del input = PILL lavanda, alineada a la derecha */
    .st-key-fch_ajuste_inline .stDateInput > div > div {
        background: var(--accent-tint) !important;
        border: 1px solid var(--border-lavender) !important;
        border-radius: 999px !important;
        box-shadow: none !important;
        padding: 0 12px !important;              /* ← simétrico, sin hueco del icono */
        min-height: 34px !important;
        height: 34px !important;
        width: fit-content !important;
        margin: 0 0 0 auto !important;           /* ← alineada a la DERECHA */
        overflow: visible !important;            /* permite que el icono viva fuera */
        position: relative !important;
        transition: background .15s ease, border-color .15s ease !important;
    }

    /* Texto de la fecha centrado y con tamaño justo */
    .st-key-fch_ajuste_inline .stDateInput input {
        color: var(--accent-deep) !important;
        font-weight: 500 !important;
        font-size: 12.5px !important;
        background: transparent !important;
        text-align: center !important;
        padding: 0 !important;
        width: 155px !important;                       /* ancho justo para el rango */
    }
    .st-key-fch_ajuste_inline .stDateInput input::placeholder {
        color: var(--accent) !important;
        opacity: 0.7 !important;
    }

    /* Hover: lavanda un punto más vivo */
    .st-key-fch_ajuste_inline .stDateInput > div > div:hover,
    .st-key-fch_ajuste_inline .stDateInput > div > div:focus-within {
        background: var(--accent-light) !important;
        border-color: var(--accent) !important;
    }

    /* ── Icono calendario gris pegado a la PÍLDORA (izquierda) ── */
    .st-key-fch_ajuste_inline .stDateInput::before {
        display: none !important;                /* desactiva el anterior */
    }
    .st-key-fch_ajuste_inline .stDateInput > div > div::before {
        content: "";
        position: absolute;
        left: -25px; top: 50%;                   /* 25px = 18px de icono + 7px de aire */
        width: 18px; height: 18px;
        transform: translateY(-50%);
        background-color: var(--icon-muted);
        -webkit-mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M16 3v4M8 3v4M4 11h16"/></svg>') center / contain no-repeat;
                mask: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="5" width="16" height="16" rx="2"/><path d="M16 3v4M8 3v4M4 11h16"/></svg>') center / contain no-repeat;
        pointer-events: none;
    }

    /* =================================================================== */
    /* CALENDARIO DESPLEGABLE (BaseWeb) — marco suave, sin presets         */
    /* =================================================================== */

    /* Marco del calendario: redondeado, con sombra y tipografía de la app */
    div[data-baseweb="calendar"] {
        border-radius: 12px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10) !important;
        font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Esquinas redondeadas en cada día */
    div[data-baseweb="calendar"] [role="gridcell"] > div {
        border-radius: 8px !important;
    }

    /* Flechas de navegación (‹ ›) en índigo */
    div[data-baseweb="calendar"] button svg {
        fill: var(--accent) !important;
    }

    /* Ocultar el selector de presets "CHOOSE A DATE RANGE / None" */
    div[data-baseweb="popover"]:has(div[data-baseweb="calendar"]) [data-baseweb="select"] {
        display: none !important;
    }
    div[data-baseweb="popover"]:has(div[data-baseweb="calendar"]) div[data-baseweb="calendar"] + div {
        display: none !important;
    }

    /* =================================================================== */
    /* OCULTAR TOOLBARS NATIVAS DE STREAMLIT                               */
    /* =================================================================== */
    /* Toolbar general (lápiz, GitHub, menú ⋮) */
    [data-testid="stToolbar"],
    [data-testid="stMainMenu"],
    [data-testid="stAppDeployButton"],
    [data-testid="stStatusWidget"] {
        display: none !important;
    }

    /* Toolbar flotante sobre AgGrid (fullscreen nativo de Streamlit) */
    [class*="st-key-grid_"] [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* =================================================================== */
    /* POSICIÓN DEL TOAST (st.toast) — cerca del botón de refresco del rail */
    /* Confirmado vía DevTools: data-testid="stToastContainer" es el contenedor
       raíz que React Aria posiciona en pantalla (data-react-aria-top-layer).
       Por defecto Streamlit lo pone abajo a la DERECHA. Lo movemos abajo a la
       IZQUIERDA, junto al rail (RAIL_ANCHO=90px en navegacion.py + 10px de aire).
       Si cambias RAIL_ANCHO allá, actualiza el "left" aquí. */
    /* =================================================================== */
    div[data-testid="stToastContainer"] {
        left: 100px !important;
        right: auto !important;
        bottom: 16px !important;
        top: auto !important;
    }
    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
