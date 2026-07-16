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
    /* FRANJA BLANCA SUPERIOR — banda de borde a borde tras título + fecha.
       El ::before se desborda a los lados (-8rem) y se recorta a la altura
       del área de contenido con `overflow-x: clip` en stMain (ver _CSS_AJUSTE
       en navegacion.py). Así la banda llega del rail al borde derecho sin
       depender del padding lateral del block-container. */
    .st-key-fila_ajuste_top {
        position: relative !important;
        margin-top: 0 !important;
        margin-bottom: 18px !important;
        padding-top: 7px !important;
        padding-bottom: 0 !important;
    }
    .st-key-fila_ajuste_top::before {
        content: "" !important;
        position: absolute !important;
        top: -15px !important;      /* prolonga la franja hasta el borde superior */
        /* La banda termina antes del selector de vista. */
        bottom: 80px !important;
        left: -8rem !important;     /* desborde generoso: se recorta en el rail */
        right: -8rem !important;    /* desborde generoso: se recorta en el borde */
        background: #ffffff !important;
        border-bottom: 1px solid var(--border) !important;
        box-shadow: 0 2px 4px rgba(16, 16, 20, 0.04) !important;
        z-index: 0 !important;
    }
    /* Título y fecha por ENCIMA de la banda */
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

    /* Opción 2: segunda fila de pestañas subrayadas en la franja blanca. */
    .st-key-ajuste_tabs_top [role="radiogroup"] {
        gap: 26px !important;
        border-bottom: 1px solid var(--border) !important;
        margin: 6px 0 0 0 !important;
        padding: 0 0 0 16px !important;
    }
    /* El radio nativo no forma parte del diseño de pestañas. */
    .st-key-ajuste_tabs_top [role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    .st-key-ajuste_tabs_top {
        position: relative !important;
        transform: translateY(-30px);
    }
    .st-key-ajuste_tabs_top [role="radiogroup"] label {
        min-width: 0 !important;
        justify-content: flex-start !important;
        padding: 6px 2px !important;
        margin: 0 !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
        margin-bottom: -1px !important;
    }
    .st-key-ajuste_tabs_top [role="radiogroup"] label p {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
    }
    .st-key-ajuste_tabs_top [role="radiogroup"] label:hover {
        border-bottom-color: var(--focus-lavender) !important;
    }
    .st-key-ajuste_tabs_top [role="radiogroup"] label:hover p {
        color: var(--accent-deep) !important;
    }
    .st-key-ajuste_tabs_top [role="radiogroup"] label [data-testid="stIconMaterial"] {
        font-size: 16px !important;
        color: inherit !important;
        vertical-align: -2px;
    }
    .st-key-ajuste_tabs_top [role="radiogroup"] label:has(input:checked) {
        background: transparent !important;
        border-bottom-color: var(--accent) !important;
    }
    .st-key-ajuste_tabs_top [role="radiogroup"] label:has(input:checked) p {
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
    }

    /* Título limpio: conserva jerarquía sin convertirlo en una píldora. */
    .titulo-ajuste-reporte {
        margin: 0 !important;
        color: var(--text-primary) !important;
        font-size: 22px !important;
        font-weight: 650 !important;
        line-height: 1.25 !important;
        letter-spacing: -0.01em !important;
        transform: translate(-70px, -30px);
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

    /* La caja del input = PILL lavanda, alineada a la derecha con aire */
    .st-key-fch_ajuste_inline .stDateInput > div > div {
        background: var(--accent-tint) !important;
        border: 1px solid var(--border-lavender) !important;
        border-radius: 999px !important;
        box-shadow: none !important;
        padding: 0 12px !important;
        min-height: 34px !important;
        height: 34px !important;
        width: fit-content !important;
        margin: 0 24px 0 auto !important;           /* ← derecha con 24px de aire */
        overflow: visible !important;
        position: relative !important;
        transition: background .15s ease, border-color .15s ease !important;
    }

    /* Marca de actualización del parquet, alineada sobre el rango de fechas. */
    .ultima-actualizacion {
        margin: 0 24px 4px auto !important;
        color: var(--text-muted) !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        text-align: right !important;
        white-space: nowrap !important;
    }

    /* Texto de la fecha centrado y con tamaño justo */
    .st-key-fch_ajuste_inline .stDateInput input {
        color: var(--accent-deep) !important;
        font-weight: 500 !important;
        font-size: 12.5px !important;
        background: transparent !important;
        text-align: center !important;
        padding: 0 !important;
        width: 155px !important;
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

    /* Icono de calendario retirado (antes vivía a la izquierda de la píldora) */
    .st-key-fch_ajuste_inline .stDateInput > div > div::before {
        display: none !important;
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

    /* =================================================================== */
    /* AVISO DE REFRESCO EN CURSO — reposicionado junto al botón del rail   */
    /* Contenedor con key "aviso_refresco" (app.py::_vigilar_refresco).     */
    /* Por defecto se dibuja arriba, ancho completo; lo anclamos como       */
    /* elemento flotante cerca del botón de refrescar (abajo del rail).     */
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
    /* Uso en graficos.py: _chart_card() / _chart_card_close()              */
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

    /* Título opcional dentro del card — pie en banda lavanda, pegado abajo */
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
    /* El card dentro de un expander no necesita doble borde */
    .streamlit-expanderContent .chart-card {
        border: none !important;
        box-shadow: none !important;
        padding: 0.25rem 0 0 !important;
    }

    /* Contenedores de gráficos de Ajuste — sin borde, esquinas amplias.
       El key incluye el ámbito (Del periodo / Histórico) + izq/der, por
       eso el prefijo con [class*=...] cubre los 4 casos.
       border:none pisa el borde que st.container(border=True) pone. */
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

    /* Gráfico de Ajuste: el marco interno lo crea _card(), no Plotly. */
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"],
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"] > div,
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"]
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* =================================================================== */
    /* CHIPS DE FILTRO EXTERNOS — Tabla de Ajuste de Inventario            */
    /* =================================================================== */
    .st-key-chips_ajuste_tabla { margin-bottom: 10px !important; }
    .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] {
        gap: 8px !important;
        align-items: center !important;
    }
    /* Anula el min-width:180px global para que quepan 4 chips en fila */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        min-width: 0 !important;
        width: 100% !important;
        padding: 8px 14px !important;
        font-size: 13px !important;
    }

    /* =================================================================== */
    /* AJUSTES FINALES PARA MÓVIL                                           */
    /* Se dejan al final para que no los pisen los estilos específicos de   */
    /* Ajuste de Inventario definidos arriba.                               */
    /* =================================================================== */
    @media screen and (max-width: 768px) {
        /* El encabezado de Ajuste usa desplazamientos de escritorio para
           alinearse con el rail. En móvil el rail no existe. */
        .titulo-ajuste-reporte {
            transform: none !important;
            font-size: 1.3rem !important;
        }
        .st-key-ajuste_tabs_top {
            transform: none !important;
        }
        .st-key-fila_ajuste_top {
            margin-bottom: 12px !important;
        }
        .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] {
            gap: 4px !important;
            align-items: stretch !important;
        }
        .st-key-fch_ajuste_inline .stDateInput > div > div,
        .ultima-actualizacion {
            margin-right: 0 !important;
        }

        /* Los controles anchos de escritorio no deben crear scroll lateral. */
        [data-testid="stPopover"] button {
            min-width: 0 !important;
            max-width: 100% !important;
        }

        /* Los avisos estaban anclados junto al rail de escritorio (90 px). */
        div[data-testid="stToastContainer"],
        .st-key-aviso_refresco {
            left: 12px !important;
            right: 12px !important;
            max-width: none !important;
        }
    }
    /* =================================================================== */
    /* SELECTOR DE VISTA — estilo segmentado                                */
    /* Reemplaza los radios tipo subrayado por una píldora alineada con los  */
    /* filtros y el estado activo de la barra lateral.                       */
    /* =================================================================== */
    [class*="st-key-vistatabs_"] [role="radiogroup"],
    .st-key-ajuste_tabs_top [role="radiogroup"] {
        display: inline-flex !important;
        width: fit-content !important;
        gap: 4px !important;
        margin: 8px 0 0 !important;
        padding: 4px !important;
        background: var(--accent-tint) !important;
        border: 1px solid var(--border-lavender) !important;
        border-radius: 999px !important;
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
    [class*="st-key-vistatabs_"] [role="radiogroup"] label,
    .st-key-ajuste_tabs_top [role="radiogroup"] label {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-width: 0 !important;
        margin: 0 !important;
        padding: 8px 14px !important;
        border: 1px solid transparent !important;
        border-radius: 999px !important;
        background: transparent !important;
        transition: color .15s ease, background .15s ease, box-shadow .15s ease !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:hover,
    .st-key-ajuste_tabs_top [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, .55) !important;
        border-color: transparent !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:has(input:checked),
    .st-key-ajuste_tabs_top [role="radiogroup"] label:has(input:checked) {
        background: #ffffff !important;
        border-color: rgba(108, 92, 231, .12) !important;
        box-shadow: 0 1px 3px rgba(73, 56, 184, .14) !important;
    }
    [class*="st-key-vistatabs_"] [role="radiogroup"] label:has(input:checked) p,
    .st-key-ajuste_tabs_top [role="radiogroup"] label:has(input:checked) p {
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
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
    @media screen and (max-width: 768px) {
        .st-key-ajuste_tabs_top [data-testid="stPills"] {
            gap: 6px !important;
        }
        .st-key-ajuste_tabs_top [data-testid="stPills"] button {
            min-height: 40px !important;
            padding: 9px 14px !important;
            font-size: 14px !important;
        }
    }

    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
