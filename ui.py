"""
Interfaz de usuario: CSS, botón flotante, tablas AgGrid y gráficos (OPTIMIZADO).
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder

from utils import _norm, buscar_columna, LOCALE_ES

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

    /* >>> ESTE es el arreglo clave <<<
       El espacio vacío de arriba es el padding-top del contenedor principal.
       En Streamlit reciente el selector correcto es .stMainBlockContainer;
       el viejo .block-container ya no aplica, por eso no veías ningún cambio. */
    .stMainBlockContainer,
    [data-testid="stMainBlockContainer"],
    .block-container {
        padding-top: 1.5rem !important;
    }

    /* Sube también el contenido del sidebar (recorta la franja de la flecha «). */
    [data-testid="stSidebarHeader"] {
        height: 2rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* ============ COLAPSAR IFRAME VACÍO DEL BOTÓN FLOTANTE ============
       El botón ☰ se inyecta con components.html(height=0). Por el bug de
       Streamlit #12454, ese iframe (data-testid="stIFrame") reserva ~150px y
       deja una franja vacía arriba del contenido. Lo colapsamos a 0 SIN usar
       display:none, para que el script del botón siga ejecutándose.
       (AgGrid usa stCustomComponentV1, por eso la tabla NO se ve afectada.) */
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
        border-radius: 8px !important;
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
    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)


# ===========================================================================
# BOTÓN FLOTANTE PARA ABRIR/CERRAR EL SIDEBAR (CACHEADO)
# ===========================================================================

@st.cache_data
def get_sidebar_toggle_html():
    """Retorna el HTML del botón flotante (cacheado)."""
    return """
    <script>
    (function () {
        const doc = window.parent.document;
        const BTN_ID = 'mi-toggle-sidebar';

        function buscarControlNativo() {
            const sels = [
                '[data-testid="stSidebarCollapseButton"] button',
                '[data-testid="stSidebarCollapseButton"]',
                '[data-testid="stExpandSidebarButton"]',
                '[data-testid="collapsedControl"]',
                '[data-testid="stSidebarCollapsedControl"]',
                'button[kind="header"]',
                'section[data-testid="stSidebar"] button'
            ];
            for (const s of sels) {
                const el = doc.querySelector(s);
                if (el) return el;
            }
            return null;
        }

        function sidebarEstaAbierto() {
            const sb = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sb) return false;
            const rect = sb.getBoundingClientRect();
            // Si el sidebar está fuera de la pantalla hacia la izquierda, está colapsado
            return rect.left > -100;
        }

        function toggleSidebar() {
            // Primero intentar con el botón nativo (funciona en ambos estados)
            const nativo = buscarControlNativo();
            if (nativo) { nativo.click(); return; }

            // Fallback manual: manipular el sidebar directamente
            const sb = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sb) return;

            if (sidebarEstaAbierto()) {
                // Cerrar
                sb.style.transform = 'translateX(-110%)';
                sb.style.width = '0';
                sb.style.minWidth = '0';
                sb.style.overflow = 'hidden';
                sb.dataset.abierto = '';
            } else {
                // Abrir
                sb.style.transform = 'none';
                sb.style.width = '21rem';
                sb.style.minWidth = '21rem';
                sb.style.visibility = 'visible';
                sb.style.overflow = 'visible';
                sb.style.zIndex = '1000';
                sb.dataset.abierto = '1';
            }
        }

        function asegurarBoton() {
            if (doc.getElementById(BTN_ID)) return;
            const b = doc.createElement('button');
            b.id = BTN_ID;
            b.innerHTML = '☰';
            b.title = 'Abrir / cerrar menú';
            b.style.cssText = [
                'position:fixed', 'top:12px', 'left:12px', 'z-index:1000000',
                'width:44px', 'height:44px', 'border-radius:10px',
                'border:1px solid #2563eb', 'background:#3b82f6', 'color:#ffffff',
                'font-size:20px', 'line-height:1', 'cursor:pointer',
                'box-shadow:0 2px 8px rgba(0,0,0,0.2)', 'display:flex',
                'align-items:center', 'justify-content:center', 'padding:0'
            ].join(';');
            b.onclick = toggleSidebar;
            doc.body.appendChild(b);
        }

        asegurarBoton();
        setInterval(asegurarBoton, 1000);
    })();
    </script>
    """


def inject_sidebar_toggle():
    """Inyecta el botón flotante cacheado."""
    components.html(get_sidebar_toggle_html(), height=0)


# ===========================================================================
# FUNCIÓN: AGGRID DESKTOP (ANCHO COMPLETO)
# ===========================================================================

def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px=14):
    """Renderiza la tabla AgGrid en vista desktop."""
    gb = GridOptionsBuilder.from_dataframe(df_grid)
    gb.configure_default_column(
        resizable=True, filter=True, sortable=True,
        editable=False, groupable=True, enableRowGroup=True,
        enablePivot=True, enableValue=True,
    )
    
    for c in df_grid.columns:
        if pd.api.types.is_numeric_dtype(df_grid[c]):
            af = "avg" if ("precio" in _norm(c) or "promedio" in _norm(c)) else "sum"
            gb.configure_column(
                c, aggFunc=af, type=["numericColumn"],
                valueFormatter="x == null ? '' : x.toLocaleString()",
            )
    
    row_h = max(28, min(60, font_px + 12))
    header_h = max(30, min(62, font_px + 14))
    
    opciones_grid = {
        "autoGroupColumnDef": {"minWidth": 200},
        "localeText": LOCALE_ES,
        "rowHeight": row_h,
        "headerHeight": header_h,
    }
    
    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c in df_grid.columns:
                gb.configure_column(c, rowGroup=True, hide=True)
        opciones_grid["groupDisplayType"] = "multipleColumns"
        opciones_grid["groupDefaultExpanded"] = 0
        opciones_grid["pivotMode"] = False
    else:
        opciones_grid["pivotMode"] = False
    
    gb.configure_side_bar()
    gb.configure_grid_options(**opciones_grid)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()
    
    custom_css = {
        ".ag-root-wrapper": {"background-color": "#ffffff", "border": "1px solid #e2e8f0", "border-radius": "8px", "width": "100% !important"},
        ".ag-header": {"background-color": "#f1f5f9", "border-bottom": "2px solid #3b82f6"},
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {"color": "#64748b", "background-color": "#f8fafc", "border-top": "1px solid #e2e8f0"},
        ".ag-side-bar": {"background-color": "#f8fafc", "border-color": "#e2e8f0"},
        ".ag-menu": {"background-color": "#ffffff", "color": "#1e293b", "border": "1px solid #e2e8f0"},
    }
    
    ajustar = False
    
    AgGrid(
        df_grid.head(5000), gridOptions=grid_options, height=600,
        theme="balham", custom_css=custom_css,
        fit_columns_on_grid_load=ajustar, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_{reporte}",
    )


# ===========================================================================
# FUNCIÓN: AGGRID MÓVIL (ANCHO COMPLETO)
# ===========================================================================

def renderizar_aggrid_movil(df_grid, columnas_fijas, reporte, font_px=14):
    """Renderiza la tabla AgGrid optimizada para vista móvil."""
    gb = GridOptionsBuilder.from_dataframe(df_grid)
    gb.configure_default_column(
        resizable=True, sortable=True, filter=True,
        editable=False, groupable=False, enableRowGroup=False,
        enablePivot=False, menuTabs=["filterMenuTab", "generalMenuTab", "columnsMenuTab"],
    )
    
    for i, col in enumerate(df_grid.columns):
        if i < columnas_fijas:
            gb.configure_column(col, pinned="left")
        if pd.api.types.is_numeric_dtype(df_grid[col]):
            af = "avg" if ("precio" in _norm(col) or "promedio" in _norm(col)) else "sum"
            gb.configure_column(col, aggFunc=af, type=["numericColumn"],
                                valueFormatter="x == null ? '' : x.toLocaleString()")
    
    row_h = max(28, min(60, font_px + 12))
    header_h = max(30, min(62, font_px + 14))
    
    opciones_grid = {
        "localeText": LOCALE_ES,
        "suppressColumnVirtualisation": True,
        "rowHeight": row_h,
        "headerHeight": header_h,
        "animateRows": False,
        "sideBar": False,
        "statusBar": {"statusPanels": [{"statusPanel": "agTotalRowCountComponent", "align": "left"}]},
        "suppressContextMenu": False,
        "pagination": True,
        "paginationAutoPageSize": False,
        "paginationPageSize": 25,
    }
    
    gb.configure_grid_options(**opciones_grid)
    grid_options = gb.build()
    
    custom_css = {
        ".ag-root-wrapper": {"background-color": "#ffffff", "border": "1px solid #e2e8f0", "border-radius": "8px", "width": "100% !important"},
        ".ag-header": {"background-color": "#f1f5f9", "border-bottom": "2px solid #3b82f6"},
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {"color": "#64748b", "background-color": "#f8fafc", "border-top": "1px solid #e2e8f0", "font-size": "0.75rem"},
        ".ag-menu": {"background-color": "#ffffff", "color": "#1e293b", "border": "1px solid #e2e8f0"},
        ".ag-pinned-left-header": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
        ".ag-pinned-left-cols-container": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
    }
    
    AgGrid(
        df_grid.head(3000), gridOptions=grid_options, height=380,
        theme="balham", custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_movil_{reporte}",
    )


# ===========================================================================
# FUNCIÓN: DASHBOARD DE GRÁFICOS
# ===========================================================================

def renderizar_graficos(df_f, es_movil=False):
    """Renderiza todos los gráficos del dashboard."""
    
    col_area = buscar_columna(df_f, "Nombre Area", "area")
    col_familia = buscar_columna(df_f, "Nombre Familia", "familia")
    col_producto = buscar_columna(df_f, "Nombre Producto", "producto")
    col_stock = buscar_columna(df_f, "Stock al dia", "stock")
    col_precio = buscar_columna(df_f, "Precio Promedio", "precio promedio")
    col_valorizado = buscar_columna(df_f, "Valorizado total", "valorizado")
    
    if not col_producto or not col_stock or not col_precio or not col_valorizado:
        st.warning("Faltan columnas esenciales (Producto, Stock, Precio, Valorizado). No se pueden generar gráficos.")
        return
    
    total_val = df_f[col_valorizado].sum()
    total_prod = len(df_f[col_producto].unique())
    stock_bajo = len(df_f[df_f[col_stock] < 10])
    stock_cero = len(df_f[df_f[col_stock] == 0])
    areas = len(df_f[col_area].unique()) if col_area else 0
    precio_prom = df_f[col_precio].mean()
    
    if es_movil:
        cols_kpi = st.columns(2)
        with cols_kpi[0]:
            st.metric("💰 Total Valorizado", f"S/ {total_val:,.0f}")
        with cols_kpi[1]:
            st.metric("📦 Productos", total_prod)
        
        cols_kpi2 = st.columns(2)
        with cols_kpi2[0]:
            st.metric("⚠️ Stock Bajo", stock_bajo, delta=f"{stock_cero} sin stock", delta_color="inverse")
        with cols_kpi2[1]:
            st.metric("💵 Precio Prom.", f"S/ {precio_prom:,.2f}")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("💰 Total Valorizado", f"S/ {total_val:,.0f}")
        with col2:
            st.metric("📦 Productos", total_prod, delta=f"{areas} áreas" if areas else None)
        with col3:
            st.metric("⚠️ Stock Bajo (<10)", stock_bajo, delta=f"{stock_cero} sin stock", delta_color="inverse")
        with col4:
            st.metric("💵 Precio Prom.", f"S/ {precio_prom:,.2f}")
        with col5:
            rotacion = total_val / total_prod if total_prod > 0 else 0
            st.metric("📊 Valor/Prod", f"S/ {rotacion:,.0f}")
    
    def crear_scatter(df, col_precio, col_stock, col_valorizado, col_producto, col_area=None, height=450):
        fig = go.Figure()
        
        valores = df[col_valorizado].fillna(0).values
        max_val = max(valores.max(), 1)
        
        if col_area:
            for area in df[col_area].unique():
                df_area = df[df[col_area] == area].copy()
                if df_area.empty:
                    continue
                
                sizes = df_area[col_valorizado].fillna(0).values
                sizes_norm = np.clip((sizes / max_val) * 35 + 5, 5, 40)
                
                fig.add_trace(go.Scatter(
                    x=df_area[col_precio],
                    y=df_area[col_stock],
                    mode='markers',
                    name=str(area),
                    marker=dict(
                        size=sizes_norm,
                        opacity=0.7,
                        sizemode='diameter'
                    ),
                    text=df_area[col_producto],
                    hovertemplate='<b>%{text}</b><br>Precio: S/ %{x:,.2f}<br>Stock: %{y:,.0f}<extra></extra>'
                ))
        else:
            sizes = df[col_valorizado].fillna(0).values
            sizes_norm = np.clip((sizes / max_val) * 35 + 5, 5, 40)
            
            fig.add_trace(go.Scatter(
                x=df[col_precio],
                y=df[col_stock],
                mode='markers',
                name='Productos',
                marker=dict(
                    size=sizes_norm,
                    opacity=0.7,
                    color='#3b82f6',
                    sizemode='diameter'
                ),
                text=df[col_producto],
                hovertemplate='<b>%{text}</b><br>Precio: S/ %{x:,.2f}<br>Stock: %{y:,.0f}<extra></extra>'
            ))
        
        fig.add_hline(y=10, line_dash="dash", line_color="red", 
                     annotation_text="Stock mínimo")
        
        if not col_area and height >= 400:
            fig.add_vline(x=df[col_precio].mean(), line_dash="dash", 
                         line_color="blue",
                         annotation_text=f"Precio prom. (S/ {df[col_precio].mean():.2f})")
        
        fig.update_layout(
            title='Relación Precio vs Stock (tamaño = valorizado)',
            xaxis_title='Precio Promedio (S/)',
            yaxis_title='Stock',
            height=height,
            paper_bgcolor='#f8fafc',
            plot_bgcolor='#ffffff',
            showlegend=True if col_area else False
        )
        
        return fig
    
    if es_movil:
        tab1, tab2 = st.tabs(["🗺️ Mapa", "📊 Análisis"])
        
        with tab1:
            if col_area:
                try:
                    path = [col_area]
                    if col_familia:
                        path.append(col_familia)
                    
                    fig_tree = px.treemap(
                        df_f, path=path, values=col_valorizado,
                        color=col_valorizado, color_continuous_scale='blues',
                        title='Valorización por Área y Familia'
                    )
                    fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=350)
                    st.plotly_chart(fig_tree, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo generar el treemap: {str(e)}")
            else:
                st.info("Se necesita columna de Área para el treemap")
            
            with st.expander("🏆 Top 10 Productos"):
                try:
                    top_10 = df_f.nlargest(10, col_valorizado)
                    fig_top = px.bar(
                        top_10, x=col_valorizado, y=col_producto,
                        orientation='h',
                        title='Top 10 por Valorización',
                        text=col_valorizado,
                        color_discrete_sequence=['#3b82f6']
                    )
                    fig_top.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                    fig_top.update_layout(height=350)
                    st.plotly_chart(fig_top, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo generar el top 10: {str(e)}")
        
        with tab2:
            try:
                fig_scatter = crear_scatter(
                    df_f, col_precio, col_stock, col_valorizado, 
                    col_producto, col_area, height=350
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            except Exception as e:
                st.warning(f"No se pudo generar el scatter plot: {str(e)}")
            
            if col_area:
                with st.expander("☀️ Distribución Jerárquica"):
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_sun = px.sunburst(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale='blues',
                            title='Distribución Jerárquica del Valor'
                        )
                        fig_sun.update_layout(height=350)
                        st.plotly_chart(fig_sun, use_container_width=True)
                    except Exception as e:
                        st.warning(f"No se pudo generar el sunburst: {str(e)}")
            
            with st.expander("📈 Distribución de Precios"):
                try:
                    fig_hist = px.histogram(
                        df_f, x=col_precio, nbins=20,
                        title='Distribución de Precios Promedio',
                        color_discrete_sequence=['#3b82f6']
                    )
                    fig_hist.update_layout(height=300)
                    st.plotly_chart(fig_hist, use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo generar el histograma: {str(e)}")
    
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗺️ Mapa de Valor", "📊 Análisis Precio/Stock",
            "🏆 Top Productos", "📈 Distribución"
        ])
        
        with tab1:
            col_a, col_b = st.columns(2)
            
            with col_a:
                if col_area:
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_tree = px.treemap(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale='blues',
                            title='Valorización por Área y Familia'
                        )
                        fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10))
                        st.plotly_chart(fig_tree, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Error en treemap: {str(e)}")
                else:
                    st.info("Se necesita columna de Área")
            
            with col_b:
                if col_area:
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_sun = px.sunburst(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale='blues',
                            title='Distribución Jerárquica'
                        )
                        fig_sun.update_layout(margin=dict(l=10, r=10, t=30, b=10))
                        st.plotly_chart(fig_sun, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Error en sunburst: {str(e)}")
        
        with tab2:
            try:
                fig_scatter = crear_scatter(
                    df_f, col_precio, col_stock, col_valorizado, 
                    col_producto, col_area, height=450
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
            except Exception as e:
                st.warning(f"Error en scatter: {str(e)}")
            
            with st.expander("🔍 Productos con stock bajo y alto valor"):
                try:
                    outliers = df_f[(df_f[col_stock] < 10) & 
                                   (df_f[col_valorizado] > df_f[col_valorizado].median())]
                    if not outliers.empty:
                        st.warning(f"⚠️ {len(outliers)} productos con stock bajo y alto valor")
                        cols_out = [col_producto, col_stock, col_valorizado]
                        if col_area:
                            cols_out.insert(1, col_area)
                        st.dataframe(
                            outliers[cols_out].sort_values(col_valorizado, ascending=False).head(10),
                            use_container_width=True
                        )
                    else:
                        st.success("✅ No hay productos críticos")
                except Exception as e:
                    st.warning(f"Error en outliers: {str(e)}")
        
        with tab3:
            col_a, col_b = st.columns(2)
            
            with col_a:
                try:
                    top_15 = df_f.nlargest(15, col_valorizado)
                    fig_top = px.bar(
                        top_15, x=col_valorizado, y=col_producto,
                        orientation='h', color=col_stock,
                        color_continuous_scale=['#ef4444', '#f59e0b', '#10b981'],
                        title='Top 15 Productos (color = stock)',
                        text=col_valorizado
                    )
                    fig_top.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                    fig_top.update_layout(height=400)
                    st.plotly_chart(fig_top, use_container_width=True)
                except Exception as e:
                    st.warning(f"Error en top 15: {str(e)}")
            
            with col_b:
                if col_area:
                    try:
                        area_val = df_f.groupby(col_area)[col_valorizado].sum().reset_index()
                        area_val = area_val.sort_values(col_valorizado, ascending=True)
                        
                        fig_area = px.bar(
                            area_val, x=col_valorizado, y=col_area,
                            orientation='h', color=col_valorizado,
                            color_continuous_scale='blues',
                            title='Ranking por Área',
                            text=col_valorizado
                        )
                        fig_area.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                        fig_area.update_layout(height=400)
                        st.plotly_chart(fig_area, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Error en ranking: {str(e)}")
        
        with tab4:
            col_a, col_b = st.columns(2)
            
            with col_a:
                try:
                    if col_area:
                        fig_box = px.box(
                            df_f, x=col_area, y=col_precio,
                            color=col_area,
                            title='Distribución de Precios por Área',
                            color_discrete_sequence=px.colors.qualitative.Set2
                        )
                    else:
                        fig_box = px.box(
                            df_f, y=col_precio,
                            title='Distribución de Precios',
                            color_discrete_sequence=['#3b82f6']
                        )
                    fig_box.update_layout(height=400)
                    st.plotly_chart(fig_box, use_container_width=True)
                except Exception as e:
                    st.warning(f"Error en box plot: {str(e)}")
            
            with col_b:
                try:
                    fig_hist = px.histogram(
                        df_f, x=col_precio, nbins=30,
                        title='Distribución de Precios',
                        color_discrete_sequence=['#3b82f6']
                    )
                    fig_hist.update_layout(height=400)
                    st.plotly_chart(fig_hist, use_container_width=True)
                except Exception as e:
                    st.warning(f"Error en histograma: {str(e)}")
            
            with st.expander("📋 Resumen por Área"):
                if col_area:
                    try:
                        resumen = df_f.groupby(col_area).agg(
                            Productos=(col_producto, 'nunique'),
                            Stock_Promedio=(col_stock, 'mean'),
                            Precio_Promedio=(col_precio, 'mean'),
                            Valorizado_Total=(col_valorizado, 'sum')
                        ).reset_index()
                        resumen['% del Total'] = (resumen['Valorizado_Total'] / total_val * 100).round(1)
                        
                        st.dataframe(
                            resumen.style.format({
                                'Stock_Promedio': '{:,.0f}',
                                'Precio_Promedio': 'S/ {:.2f}',
                                'Valorizado_Total': 'S/ {:,.0f}',
                                '% del Total': '{:.1f}%'
                            }).background_gradient(subset=['Valorizado_Total'], cmap='Blues'),
                            use_container_width=True
                        )
                    except Exception as e:
                        st.warning(f"Error en resumen: {str(e)}")
