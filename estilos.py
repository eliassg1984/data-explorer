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
    /* ============ PALETA DE COLORES ============ */
    :root {
        --bg-primary: #f8fafc;
        --bg-secondary: #ffffff;
        --bg-sidebar: #f1f5f9;
        --bg-card: #ffffff;
        --bg-hover: #e2e8f0;
        --text-primary: #1e293b;
        --text-secondary: #475569;
        --text-muted: #94a3b8;
        --accent: #3b82f6;
        --accent-hover: #2563eb;
        --accent-light: #dbeafe;
        --border: #e2e8f0;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
        --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.05), 0 2px 4px rgba(0, 0, 0, 0.03);
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

    [data-testid="stDecoration"] {
        display: none !important;
    }

    [data-testid="stToolbar"] {
        display: none !important;
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
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
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
        border-radius: 4px !important;
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
        background: #fef3c7 !important;
        border: 1px solid #fcd34d !important;
        color: #92400e !important;
        border-radius: 8px !important;
    }

    .stInfo {
        background: var(--accent-light) !important;
        border: 1px solid #93c5fd !important;
        color: #1e40af !important;
        border-radius: 8px !important;
    }

    .stError {
        background: #fee2e2 !important;
        border: 1px solid #fca5a5 !important;
        color: #991b1b !important;
        border-radius: 8px !important;
    }

    /* ============ SIDEBAR ============ */
    [data-testid="stSidebar"] .nav-link {
        background: #ffffff !important;
        color: #475569 !important;
        border: 1px solid #e2e8f0 !important;
    }

    [data-testid="stSidebar"] .nav-link:hover {
        background: #eff6ff !important;
        color: #2563eb !important;
        border-color: #93c5fd !important;
    }

    [data-testid="stSidebar"] .nav-link-selected {
        background: #3b82f6 !important;
        color: #ffffff !important;
        border-color: #3b82f6 !important;
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
    /* BOTONES TABLA / GRÁFICOS (segmented_control) — Opción 2 GRANDE azul  */
    /* =================================================================== */
    /* Separación entre los dos botones (cubrimos las variantes de Streamlit) */
    [data-testid="stSegmentedControl"] [data-baseweb="button-group"],
    [data-testid="stSegmentedControl"] [role="radiogroup"],
    [data-testid="stSegmentedControl"] [role="group"],
    [data-testid="stSegmentedControl"] > div,
    [data-testid="stButtonGroup"] > div {
        gap: 16px !important;
    }
    /* Base de cada botón — apuntamos por contenedor Y por kind del botón,    */
    /* así cae en alguna combinación según tu versión de Streamlit.          */
    [data-testid="stSegmentedControl"] button,
    [data-testid="stButtonGroup"] button,
    button[data-testid^="stBaseButton-segmented_control"],
    button[kind^="segmented_control"] {
        min-width: 190px !important;          /* MÁS GRANDE: ancho */
        padding: 14px 30px !important;        /* MÁS GRANDE: alto */
        margin: 0 !important;                 /* quita el -1px que los pega */
        font-size: 15px !important;
        font-weight: 600 !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 999px !important;      /* pill completo en ambos */
        transition: all .15s ease !important;
    }
    /* Icono Material un poco más grande dentro del botón */
    [data-testid="stSegmentedControl"] button [data-testid="stIconMaterial"],
    [data-testid="stSegmentedControl"] button p,
    button[kind^="segmented_control"] [data-testid="stIconMaterial"] {
        font-size: 20px !important;
    }
    /* ESTADO ACTIVO — Streamlit lo marca con kind="...Active"               */
    [data-testid="stSegmentedControl"] button[kind*="Active"],
    button[data-testid$="segmented_controlActive"],
    button[kind="segmented_controlActive"],
    [data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: #eff6ff !important;
        color: #1e40af !important;
        border-color: #2563eb !important;
    }
    [data-testid="stSegmentedControl"] button[kind*="Active"] p,
    button[kind="segmented_controlActive"] p {
        color: #1e40af !important;
    }
    [data-testid="stSegmentedControl"] button:hover,
    button[kind^="segmented_control"]:hover {
        border-color: #93c5fd !important;
    }

    /* =================================================================== */
    /* BOTÓN FILTROS (popover) — a juego, grande y con contorno azul        */
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
        border-color: #2563eb !important;
        background: #eff6ff !important;
        color: #1e40af !important;
    }

    /* =================================================================== */
    /* BOTÓN "EXTRAER DATOS" — Ajuste de Inventario: esquinas cuadradas     */
    /* =================================================================== */
    .st-key-btn_extraer_ajuste button {
        border-radius: 4px !important;
    }

    /* =================================================================== */
    /* FILA SUPERIOR DE AJUSTE DE INVENTARIO — alinea verticalmente al      */
    /* mismo nivel el título, el botón "Extraer datos" y el selector de     */
    /* fecha (sin importar la altura natural de cada bloque).               */
    /* =================================================================== */
    .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    .st-key-fila_ajuste_top [data-testid="stColumn"],
    .st-key-fila_ajuste_top [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
    }
    .st-key-btn_extraer_ajuste {
        width: 100% !important;
    }

    /* =================================================================== */
    /* FILTRO DE FECHA — AJUSTE DE INVENTARIO (label al costado, contenedor */
    /* angosto en lugar de uno largo y la etiqueta encima)                  */
    /* Solo afecta al date_input con key="fch_ajuste_inline"                */
    /* =================================================================== */

    /* Contenedor: label + input en fila, alineados al centro */
    .st-key-fch_ajuste_inline {
        max-width: none !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 10px !important;
    }

    /* Etiqueta — "Rango a Evaluar" al costado, sin mayúsculas forzadas,
       sin ocupar una fila propia arriba del input. */
    .st-key-fch_ajuste_inline label {
        font-size: 0.72rem !important;
        letter-spacing: 0.02em !important;
        text-transform: none !important;
        font-weight: 600 !important;
        color: var(--text-muted) !important;
        margin-bottom: 0 !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
    }

    /* El bloque que Streamlit genera para label+widget también en fila */
    .st-key-fch_ajuste_inline > div {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        gap: 10px !important;
        width: auto !important;
    }

    /* Contenedor del widget en sí: ancho ajustado al texto de la fecha,
       ya no ocupa todo el ancho disponible de la columna. */
    .st-key-fch_ajuste_inline [data-baseweb="input"] {
        width: 190px !important;
        min-width: 190px !important;
    }

    /* La caja del input = tarjeta con borde de acento a la izquierda */
    .st-key-fch_ajuste_inline .stDateInput > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-left: 3px solid var(--accent) !important;
        border-radius: 10px !important;
        box-shadow: var(--shadow) !important;
        transition: border-color .15s ease, box-shadow .15s ease !important;
        width: 190px !important;
        min-width: 190px !important;
    }

    /* Hover / foco: acento más vivo y sombra algo más marcada */
    .st-key-fch_ajuste_inline .stDateInput > div > div:hover,
    .st-key-fch_ajuste_inline .stDateInput > div > div:focus-within {
        border-color: var(--accent) !important;
        border-left-color: var(--accent-hover) !important;
        box-shadow: var(--shadow-md) !important;
    }

    /* Ícono de calendario nativo en azul */
    .st-key-fch_ajuste_inline .stDateInput svg {
        color: var(--accent) !important;
        fill: var(--accent) !important;
    }

    /* =================================================================== */
    /* CALENDARIO DESPLEGABLE (BaseWeb) — Opción 1: marco suave, sin presets */
    /* IMPORTANTE: el color azul de los días y del relleno del rango lo da   */
    /* primaryColor en .streamlit/config.toml. Aquí solo pulimos el marco y  */
    /* ocultamos el bloque "CHOOSE A DATE RANGE / None".                     */
    /* =================================================================== */

    /* Marco del calendario: redondeado, con sombra y tipografía de la app */
    div[data-baseweb="calendar"] {
        border-radius: 12px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Esquinas redondeadas en cada día */
    div[data-baseweb="calendar"] [role="gridcell"] > div {
        border-radius: 8px !important;
    }

    /* Flechas de navegación (‹ ›) en azul */
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
    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
