import unicodedata
import pandas as pd
import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_option_menu import option_menu

st.set_page_config(
    page_title="Reportes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Panel de Reportes v2.0 - Inventario & Compras"
    }
)

# ---------------------------------------------------------------------------
# CSS GLOBAL - Tema claro moderno + Header personalizado
# ---------------------------------------------------------------------------
st.markdown("""
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

/* ============ OCULTAR HEADER NATIVO ============ */
header[data-testid="stHeader"] {
    display: none !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

[data-testid="stToolbar"] {
    display: none !important;
}

/* ============ BARRA SUPERIOR PERSONALIZADA ============ */
.custom-top-bar {
    background: #ffffff;
    padding: 12px 20px;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: var(--shadow);
    position: sticky;
    top: 0;
    z-index: 100;
}

.custom-top-bar .brand {
    font-size: 1.2rem;
    font-weight: 700;
    color: #1e293b;
    display: flex;
    align-items: center;
    gap: 8px;
}

.custom-top-bar .menu-btn {
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    cursor: pointer;
    font-size: 1.2rem;
    color: #475569;
    transition: all 0.2s;
}

.custom-top-bar .menu-btn:hover {
    background: #e2e8f0;
    color: #1e293b;
}

.custom-top-bar .version {
    font-size: 0.75rem;
    color: #94a3b8;
    background: #f1f5f9;
    padding: 4px 10px;
    border-radius: 20px;
}

/* ============ ESTILOS BASE ============ */
[data-testid="stAppViewContainer"] { 
    background: var(--bg-primary); 
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

/* ============ METRIC CARDS ============ */
.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
    box-shadow: var(--shadow);
}

.metric-card .metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1e293b;
}

.metric-card .metric-label {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    font-weight: 600;
}

.metric-card .metric-delta {
    font-size: 0.8rem;
    margin-top: 4px;
}

.metric-card .metric-delta.positive { color: #10b981; }
.metric-card .metric-delta.negative { color: #ef4444; }
.metric-card .metric-delta.warning { color: #f59e0b; }

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

/* ============ MÓVIL ============ */
@media screen and (max-width: 768px) {
    h1 { font-size: 1.3rem !important; }
    h2 { font-size: 1.1rem !important; }
    h3 { font-size: 1rem !important; }
    label { font-size: 0.7rem !important; }
    
    .stApp { padding: 0.5rem !important; }
    .block-container { padding: 1rem 0.5rem !important; }
    
    button { 
        min-height: 44px !important; 
        padding: 10px 16px !important;
        font-size: 0.9rem !important;
    }
    
    [data-testid="stSidebar"] { 
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .metric-card .metric-value {
        font-size: 1.2rem;
    }
}
</style>

<!-- BARRA SUPERIOR PERSONALIZADA -->
<div class="custom-top-bar">
    <button class="menu-btn" onclick="
        const sidebar = parent.document.querySelector('[data-testid=stSidebar]');
        if(sidebar) sidebar.style.display = sidebar.style.display === 'none' ? 'flex' : 'none';
    ">☰</button>
    <div class="brand">📊 Panel de Reportes</div>
    <div class="version">v2.0</div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower().replace(" ", "").replace("_", "").replace("-", "")


def buscar_columna(df, *candidatos):
    norm_map = {_norm(c): c for c in df.columns}
    for cand in candidatos:
        if _norm(cand) in norm_map:
            return norm_map[_norm(cand)]
    return None


def buscar_columna_fecha(df):
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
    for c in df.columns:
        if "fecha" in _norm(c) or "date" in _norm(c):
            return c
    return None


def resolver_columnas(df, nombres):
    encontradas, faltantes = [], []
    for n in nombres:
        real = buscar_columna(df, n)
        if real and real not in encontradas:
            encontradas.append(real)
        elif not real:
            faltantes.append(n)
    return encontradas, faltantes


# ---------------------------------------------------------------------------
# Traducción AgGrid
# ---------------------------------------------------------------------------
LOCALE_ES = {
    "sortAscending": "Ordenar ascendente",
    "sortDescending": "Ordenar descendente",
    "sortUnSort": "Quitar orden",
    "pinColumn": "Fijar columna",
    "pinLeft": "Fijar a la izquierda",
    "pinRight": "Fijar a la derecha",
    "noPin": "No fijar",
    "valueAggregation": "Agregación de valores",
    "autosizeThisColumn": "Autoajustar esta columna",
    "autosizeAllColumns": "Autoajustar todas las columnas",
    "groupBy": "Agrupar por",
    "ungroupBy": "Desagrupar por",
    "resetColumns": "Restablecer columnas",
    "expandAll": "Expandir todos los grupos",
    "collapseAll": "Colapsar todos los grupos",
    "copy": "Copiar",
    "copyWithHeaders": "Copiar con encabezados",
    "ctrlC": "Ctrl+C",
    "paste": "Pegar",
    "ctrlV": "Ctrl+V",
    "export": "Exportar",
    "csvExport": "Exportar a CSV",
    "excelExport": "Exportar a Excel",
    "chooseColumns": "Elegir columnas",
    "columnChooser": "Elegir columnas",
    "columns": "Columnas",
    "filters": "Filtros",
    "searchOoo": "Buscar…",
    "filterOoo": "Filtrar…",
    "blanks": "(En blanco)",
    "selectAll": "(Seleccionar todo)",
    "applyFilter": "Aplicar",
    "resetFilter": "Restablecer",
    "clearFilter": "Limpiar",
    "cancelFilter": "Cancelar",
    "equals": "Igual a",
    "notEqual": "Distinto de",
    "contains": "Contiene",
    "notContains": "No contiene",
    "startsWith": "Empieza con",
    "endsWith": "Termina con",
    "blank": "En blanco",
    "notBlank": "No en blanco",
    "lessThan": "Menor que",
    "greaterThan": "Mayor que",
    "inRange": "En rango",
    "page": "Página",
    "to": "a",
    "of": "de",
    "more": "más",
    "nextPage": "Página siguiente",
    "lastPage": "Última página",
    "firstPage": "Primera página",
    "previousPage": "Página anterior",
    "pageSizeSelectorLabel": "Tamaño de página:",
    "sum": "Suma",
    "min": "Mín",
    "max": "Máx",
    "none": "Ninguno",
    "count": "Conteo",
    "avg": "Promedio",
    "loadingOoo": "Cargando…",
    "noRowsToShow": "No hay datos para mostrar",
    "totalRows": "Total de filas",
    "totalAndFilteredRows": "Filas",
}


@st.cache_resource
def get_conn():
    try:
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"""
            SET s3_endpoint='{st.secrets["R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com';
            SET s3_access_key_id='{st.secrets["R2_ACCESS_KEY"]}';
            SET s3_secret_access_key='{st.secrets["R2_SECRET_KEY"]}';
            SET s3_region='auto';
            SET s3_url_style='path';
        """)
        return con
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        st.stop()


con = get_conn()
BUCKET = st.secrets["R2_BUCKET"]

# ---------------------------------------------------------------------------
# Configuración por reporte
# ---------------------------------------------------------------------------
REPORTES = {
    "Ajuste de Inventario": {
        "archivo": "ajusteinventario.parquet",
        "icono": "sliders",
    },
    "Compras": {
        "archivo": "compras.parquet",
        "icono": "cart",
    },
    "Inventario Valorizado": {
        "archivo": "inventariovalorizado.parquet",
        "icono": "boxes",
        "columnas": [
            "Nombre Area", "Nombre Familia", "Nombre Subfamilia",
            "Codigo Producto", "Nombre Producto", "Unidad Kardex",
            "Stock al dia", "Precio Promedio", "Valorizado total",
        ],
        "filtros_cat": ["Nombre Area", "Nombre Familia"],
        "buscador": "Nombre Producto",
        "fecha": None,
        "agrupar": ["Nombre Area", "Nombre Familia", "Nombre Subfamilia"],
        "columnas_movil": [
            "Nombre Producto", "Stock al dia", "Precio Promedio",
            "Valorizado total", "Nombre Area",
        ],
        "columnas_fijas_movil": 2,
    },
    "Receta Base": {
        "archivo": "recetabase.parquet",
        "icono": "clipboard-data",
    },
    "Receta Venta": {
        "archivo": "recetaventa.parquet",
        "icono": "receipt",
    },
}


@st.cache_data(ttl=3600)
def cargar(archivo):
    try:
        url = f"s3://{BUCKET}/{archivo}"
        return con.execute(f"SELECT * FROM read_parquet('{url}')").df()
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None


# ---------------------------------------------------------------------------
# Función: AgGrid Desktop
# ---------------------------------------------------------------------------
def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte):
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
    
    opciones_grid = {
        "autoGroupColumnDef": {"minWidth": 200},
        "localeText": LOCALE_ES,
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
        ".ag-root-wrapper": {"background-color": "#ffffff", "border": "1px solid #e2e8f0", "border-radius": "8px"},
        ".ag-header": {"background-color": "#f1f5f9", "border-bottom": "2px solid #3b82f6"},
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155"},
        ".ag-paging-panel": {"color": "#64748b", "background-color": "#f8fafc", "border-top": "1px solid #e2e8f0"},
        ".ag-side-bar": {"background-color": "#f8fafc", "border-color": "#e2e8f0"},
        ".ag-menu": {"background-color": "#ffffff", "color": "#1e293b", "border": "1px solid #e2e8f0"},
    }
    
    visibles = len(cols_mostrar) - (len([c for c in grupos_sel if c in cols_mostrar]) if agrupar_on else 0)
    ajustar = visibles <= 6
    
    AgGrid(
        df_grid.head(5000), gridOptions=grid_options, height=470,
        theme="balham", custom_css=custom_css,
        fit_columns_on_grid_load=ajustar, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_{reporte}",
    )


# ---------------------------------------------------------------------------
# Función: AgGrid Móvil
# ---------------------------------------------------------------------------
def renderizar_aggrid_movil(df_grid, columnas_fijas, reporte):
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
    
    opciones_grid = {
        "localeText": LOCALE_ES,
        "suppressColumnVirtualisation": True,
        "rowHeight": 44,
        "headerHeight": 40,
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
        ".ag-root-wrapper": {"background-color": "#ffffff", "border": "1px solid #e2e8f0", "border-radius": "8px"},
        ".ag-header": {"background-color": "#f1f5f9", "border-bottom": "2px solid #3b82f6"},
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155"},
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


# ---------------------------------------------------------------------------
# Función: Dashboard de gráficos
# ---------------------------------------------------------------------------
def renderizar_graficos(df_f, es_movil=False):
    """Renderiza todos los gráficos del dashboard."""
    
    # Columnas necesarias
    col_area = buscar_columna(df_f, "Nombre Area", "area")
    col_familia = buscar_columna(df_f, "Nombre Familia", "familia")
    col_producto = buscar_columna(df_f, "Nombre Producto", "producto")
    col_stock = buscar_columna(df_f, "Stock al dia", "stock")
    col_precio = buscar_columna(df_f, "Precio Promedio", "precio promedio")
    col_valorizado = buscar_columna(df_f, "Valorizado total", "valorizado")
    
    if not all([col_area, col_producto, col_stock, col_precio, col_valorizado]):
        st.info("Faltan columnas necesarias para los gráficos.")
        return
    
    # ============ KPIs ============
    total_val = df_f[col_valorizado].sum()
    total_prod = len(df_f[col_producto].unique())
    stock_bajo = len(df_f[df_f[col_stock] < 10])
    stock_cero = len(df_f[df_f[col_stock] == 0])
    areas = len(df_f[col_area].unique()) if col_area else 0
    precio_prom = df_f[col_precio].mean()
    
    # Mostrar KPIs
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
            st.metric("📦 Productos", total_prod, delta=f"{areas} áreas")
        with col3:
            st.metric("⚠️ Stock Bajo (<10)", stock_bajo, delta=f"{stock_cero} sin stock", delta_color="inverse")
        with col4:
            st.metric("💵 Precio Prom.", f"S/ {precio_prom:,.2f}")
        with col5:
            rotacion = total_val / total_prod if total_prod > 0 else 0
            st.metric("📊 Valor/Prod", f"S/ {rotacion:,.0f}")
    
    # ============ GRÁFICOS ============
    if es_movil:
        # MÓVIL: Mostrar en tabs + expanders para no saturar
        tab1, tab2 = st.tabs(["🗺️ Mapa", "📊 Análisis"])
        
        with tab1:
            # Treemap (más visual)
            if col_area and col_familia:
                fig_tree = px.treemap(
                    df_f,
                    path=[col_area, col_familia],
                    values=col_valorizado,
                    color=col_valorizado,
                    color_continuous_scale='blues',
                    title='Valorización por Área y Familia'
                )
                fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=350)
                st.plotly_chart(fig_tree, use_container_width=True)
            else:
                st.info("Se necesita Área y Familia para el treemap")
            
            # Top 10 en expander
            with st.expander("🏆 Top 10 Productos"):
                top_10 = df_f.nlargest(10, col_valorizado)
                fig_top = px.bar(
                    top_10, x=col_valorizado, y=col_producto,
                    orientation='h', color=col_stock,
                    color_continuous_scale=['#ef4444', '#f59e0b', '#10b981'],
                    title='Top 10 por Valorización',
                    text=col_valorizado
                )
                fig_top.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                fig_top.update_layout(height=350)
                st.plotly_chart(fig_top, use_container_width=True)
        
        with tab2:
            # Scatter plot
            fig_scatter = px.scatter(
                df_f, x=col_precio, y=col_stock,
                size=col_valorizado, color=col_area if col_area else None,
                hover_name=col_producto,
                title='Precio vs Stock (tamaño = valorizado)',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_scatter.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="Stock mínimo")
            fig_scatter.update_layout(height=350)
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Sunburst en expander
            if col_area:
                with st.expander("☀️ Distribución Jerárquica"):
                    fig_sun = px.sunburst(
                        df_f,
                        path=[col_area, col_familia] if col_familia else [col_area],
                        values=col_valorizado,
                        color=col_valorizado,
                        color_continuous_scale='blues',
                        title='Distribución Jerárquica del Valor'
                    )
                    fig_sun.update_layout(height=350)
                    st.plotly_chart(fig_sun, use_container_width=True)
            
            # Distribución de precios
            with st.expander("📈 Distribución de Precios"):
                fig_hist = px.histogram(
                    df_f, x=col_precio,
                    nbins=20,
                    title='Distribución de Precios Promedio',
                    color_discrete_sequence=['#3b82f6']
                )
                fig_hist.update_layout(height=300)
                st.plotly_chart(fig_hist, use_container_width=True)
    
    else:
        # DESKTOP: Tabs con múltiples gráficos
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗺️ Mapa de Valor", "📊 Análisis Precio/Stock",
            "🏆 Top Productos", "📈 Distribución"
        ])
        
        with tab1:
            col_a, col_b = st.columns(2)
            
            with col_a:
                if col_area and col_familia:
                    fig_tree = px.treemap(
                        df_f,
                        path=[col_area, col_familia],
                        values=col_valorizado,
                        color=col_valorizado,
                        color_continuous_scale='blues',
                        title='Valorización por Área y Familia'
                    )
                    fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig_tree, use_container_width=True)
                else:
                    st.info("Se necesita Área y Familia")
            
            with col_b:
                if col_area:
                    fig_sun = px.sunburst(
                        df_f,
                        path=[col_area, col_familia] if col_familia else [col_area],
                        values=col_valorizado,
                        color=col_valorizado,
                        color_continuous_scale='blues',
                        title='Distribución Jerárquica'
                    )
                    fig_sun.update_layout(margin=dict(l=10, r=10, t=30, b=10))
                    st.plotly_chart(fig_sun, use_container_width=True)
        
        with tab2:
            fig_scatter = px.scatter(
                df_f, x=col_precio, y=col_stock,
                size=col_valorizado, color=col_area if col_area else None,
                hover_name=col_producto,
                title='Relación Precio vs Stock (tamaño = valorizado)',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_scatter.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="Stock mínimo (10)")
            fig_scatter.add_vline(x=df_f[col_precio].mean(), line_dash="dash", line_color="blue",
                                  annotation_text=f"Precio prom. (S/ {df_f[col_precio].mean():.2f})")
            fig_scatter.update_layout(height=450)
            st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Tabla de outliers
            with st.expander("🔍 Productos con stock bajo y alto valor"):
                outliers = df_f[(df_f[col_stock] < 10) & (df_f[col_valorizado] > df_f[col_valorizado].median())]
                if not outliers.empty:
                    st.warning(f"⚠️ {len(outliers)} productos con stock bajo y alto valor")
                    st.dataframe(
                        outliers[[col_producto, col_area, col_stock, col_valorizado]]
                        .sort_values(col_valorizado, ascending=False)
                        .head(10),
                        use_container_width=True
                    )
        
        with tab3:
            col_a, col_b = st.columns(2)
            
            with col_a:
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
            
            with col_b:
                # Ranking por área
                if col_area:
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
        
        with tab4:
            col_a, col_b = st.columns(2)
            
            with col_a:
                fig_box = px.box(
                    df_f, x=col_area if col_area else None, y=col_precio,
                    color=col_area if col_area else None,
                    title='Distribución de Precios por Área',
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig_box.update_layout(height=400)
                st.plotly_chart(fig_box, use_container_width=True)
            
            with col_b:
                fig_hist = px.histogram(
                    df_f, x=col_precio, nbins=30,
                    title='Distribución de Precios',
                    color_discrete_sequence=['#3b82f6']
                )
                fig_hist.update_layout(height=400)
                st.plotly_chart(fig_hist, use_container_width=True)
            
            # Tabla de resumen
            with st.expander("📋 Resumen por Área"):
                if col_area:
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


# ===========================================================================
# INTERFAZ PRINCIPAL
# ===========================================================================
st.title("📊 Panel de Reportes")

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    reporte = option_menu(
        menu_title="Seleccionar Reporte",
        options=list(REPORTES.keys()),
        icons=[v["icono"] for v in REPORTES.values()],
        menu_icon="bar-chart-fill",
        default_index=2,  # Inventario Valorizado por defecto
        styles={
            "container": {"padding": "4px", "background-color": "#f1f5f9"},
            "menu-title": {
                "color": "#475569", "font-size": "13px",
                "text-transform": "uppercase", "letter-spacing": "1px", "font-weight": "700",
            },
            "icon": {"color": "#3b82f6", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px", "color": "#475569",
                "background-color": "#ffffff", "margin": "5px 0",
                "border-radius": "8px", "--hover-color": "#eff6ff",
                "border": "1px solid #e2e8f0",
            },
            "nav-link-selected": {
                "background-color": "#3b82f6", "color": "#ffffff",
                "border": "1px solid #3b82f6",
            },
        },
    )
    
    st.markdown("---")
    
    with st.expander("🔧 Modo vista"):
        if 'forzar_movil' not in st.session_state:
            st.session_state.forzar_movil = False
        st.session_state.forzar_movil = st.checkbox(
            "Forzar vista móvil",
            value=st.session_state.forzar_movil,
            help="Activar para probar la vista optimizada para celular",
        )

cfg = REPORTES[reporte]

# ---------------------------------------------------------------------------
# CARGAR DATOS
# ---------------------------------------------------------------------------
df = cargar(cfg["archivo"])
if df is None or df.empty:
    st.warning("No se pudieron cargar los datos o el archivo está vacío.")
    st.stop()

st.subheader(reporte)

# ---------------------------------------------------------------------------
# DETERMINAR COLUMNAS
# ---------------------------------------------------------------------------
if "fecha" in cfg:
    col_fecha = buscar_columna(df, cfg["fecha"]) if cfg["fecha"] else None
else:
    col_fecha = buscar_columna_fecha(df)

if "filtros_cat" in cfg:
    cat_cols, faltan_cat = resolver_columnas(df, cfg["filtros_cat"])
else:
    cat_cols = [c for c in [
        buscar_columna(df, "area", "área"),
        buscar_columna(df, "familia"),
        buscar_columna(df, "subfamilia", "sub familia"),
    ] if c]
    faltan_cat = []

if "buscador" in cfg and cfg["buscador"]:
    col_busc = buscar_columna(df, cfg["buscador"])
else:
    col_busc = None

faltantes_aviso = list(faltan_cat)
if "buscador" in cfg and cfg["buscador"] and not col_busc:
    faltantes_aviso.append(cfg["buscador"])

# ---------------------------------------------------------------------------
# PROCESAMIENTO
# ---------------------------------------------------------------------------
df_f = df.copy()
if col_fecha:
    df_f[col_fecha] = pd.to_datetime(df_f[col_fecha], errors="coerce")

todas_cols = df_f.columns.tolist()

if "columnas" in cfg:
    sugeridas, faltan_cols = resolver_columnas(df_f, cfg["columnas"])
else:
    faltan_cols = []
    sugeridas = []
    for c in [col_fecha] + cat_cols + ([col_busc] if col_busc else []):
        if c and c not in sugeridas:
            sugeridas.append(c)
    for c in df_f.select_dtypes("number").columns.tolist():
        if c not in sugeridas:
            sugeridas.append(c)
        if len(sugeridas) >= 8:
            break
    if not sugeridas:
        sugeridas = todas_cols[:8]
    sugeridas = sugeridas[:8]

if "agrupar" in cfg:
    cols_agrupar, _ = resolver_columnas(df_f, cfg["agrupar"])
else:
    cols_agrupar = [c for c in cat_cols if c]

# ---------------------------------------------------------------------------
# CONTROLES DE FILTRO
# ---------------------------------------------------------------------------
controles = []
if col_fecha and df_f[col_fecha].notna().any():
    controles.append(("fecha", col_fecha))
for cc in cat_cols:
    controles.append(("cat", cc))
if col_busc:
    controles.append(("busc", col_busc))
if cols_agrupar:
    controles.append(("grp", None))

grupos_sel = []

if controles:
    MAX_COLS_POR_FILA = 2
    for i in range(0, len(controles), MAX_COLS_POR_FILA):
        fila_controles = controles[i:i+MAX_COLS_POR_FILA]
        cols_ui = st.columns(len(fila_controles))
        
        for j, (tipo, col) in enumerate(fila_controles):
            with cols_ui[j]:
                if tipo == "fecha":
                    fmin = df_f[col].min().date()
                    fmax = df_f[col].max().date()
                    rango = st.date_input(
                        "📅 Fecha", value=(fmin, fmax),
                        min_value=fmin, max_value=fmax,
                        format="DD/MM/YYYY", key=f"fch_{reporte}_{i}_{j}",
                    )
                    if isinstance(rango, (tuple, list)) and len(rango) == 2:
                        ini, fin = rango
                        df_f = df_f[(df_f[col].dt.date >= ini) & (df_f[col].dt.date <= fin)]
                elif tipo == "cat":
                    opts = sorted(df_f[col].dropna().unique().tolist(), key=lambda x: str(x))
                    sel = st.multiselect(f"📂 {col}", opts, placeholder="Todos", key=f"cat_{reporte}_{col}_{i}_{j}")
                    if sel:
                        df_f = df_f[df_f[col].isin(sel)]
                elif tipo == "busc":
                    opts_prod = sorted(df_f[col].dropna().astype(str).unique().tolist(), key=lambda x: x.lower())
                    sel_prod = st.multiselect(f"🔎 {col}", opts_prod, placeholder="Buscar…", key=f"busc_{reporte}_{i}_{j}")
                    if sel_prod:
                        df_f = df_f[df_f[col].astype(str).isin(sel_prod)]
                elif tipo == "grp":
                    grupos_sel = st.multiselect("📊 Agrupar por", cols_agrupar, default=[], key=f"grp_{reporte}_{i}_{j}", placeholder="Sin agrupar")

# ---------------------------------------------------------------------------
# AVISOS
# ---------------------------------------------------------------------------
if faltantes_aviso:
    st.caption("⚠️ No se encontraron: " + ", ".join(faltantes_aviso))
if "columnas" in cfg and faltan_cols:
    st.caption("⚠️ Columnas no encontradas: " + ", ".join(faltan_cols))

# ---------------------------------------------------------------------------
# SELECTOR DE COLUMNAS
# ---------------------------------------------------------------------------
usa_vista_movil = st.session_state.get('forzar_movil', False)
tiene_config_movil = "columnas_movil" in cfg
usa_vista_movil = usa_vista_movil or tiene_config_movil

if not usa_vista_movil:
    with st.expander("⚙️ Configuración de columnas"):
        cols_mostrar = st.multiselect(
            "Seleccionar columnas visibles", todas_cols,
            default=sugeridas, key=f"cols_{reporte}",
            label_visibility="collapsed", placeholder="Selecciona columnas",
        )
    if not cols_mostrar:
        cols_mostrar = sugeridas
else:
    cols_mostrar_movil, _ = resolver_columnas(df_f, cfg["columnas_movil"])
    if not cols_mostrar_movil:
        cols_mostrar_movil = sugeridas[:5]
    cols_mostrar = cols_mostrar_movil

# ---------------------------------------------------------------------------
# CONTADOR
# ---------------------------------------------------------------------------
if len(df_f) != len(df):
    st.caption(f"📊 Mostrando {len(df_f):,} de {len(df):,} filas (filtrado)")
else:
    st.caption(f"📊 Total: {len(df_f):,} filas")

if df_f.empty:
    st.warning("Ningún registro coincide con los filtros.")
    st.stop()

# ---------------------------------------------------------------------------
# RENDERIZAR TABLA
# ---------------------------------------------------------------------------
if usa_vista_movil and tiene_config_movil:
    st.caption("📱 Vista móvil • Desliza para más columnas • Mantén presionado para menú")
    columnas_fijas = cfg.get("columnas_fijas_movil", 2)
    df_grid_movil = df_f[cols_mostrar]
    renderizar_aggrid_movil(df_grid_movil, columnas_fijas, reporte)
else:
    cols_finales = list(cols_mostrar)
    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c not in cols_finales:
                cols_finales.append(c)
    df_grid = df_f[cols_finales]
    renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte)

# ---------------------------------------------------------------------------
# DASHBOARD DE GRÁFICOS
# ---------------------------------------------------------------------------
st.markdown("---")

# Solo mostrar gráficos avanzados para Inventario Valorizado
if reporte == "Inventario Valorizado":
    st.subheader("📊 Dashboard de Análisis")
    renderizar_graficos(df_f, es_movil=usa_vista_movil)
else:
    # Gráfico simple para otros reportes
    st.subheader("📈 Visualización")
    cols_num = df_f.select_dtypes("number").columns.tolist()
    cols_txt = df_f.select_dtypes(["object", "string"]).columns.tolist()
    
    if cols_num and cols_txt:
        col1, col2 = st.columns(2)
        with col1:
            eje_x = st.selectbox("Agrupar por", cols_txt, key=f"ejex_{reporte}")
        with col2:
            eje_y = st.selectbox("Métrica (suma)", cols_num, key=f"ejey_{reporte}")
        
        try:
            datos = df_f.groupby(eje_x)[eje_y].sum().reset_index().sort_values(eje_y, ascending=False).head(20)
            fig = px.bar(datos, x=eje_x, y=eje_y,
                         title=f"{eje_y} por {eje_x} (top 20)",
                         color_discrete_sequence=["#3b82f6"])
            fig.update_layout(
                paper_bgcolor="#f8fafc", plot_bgcolor="#ffffff",
                font_color="#1e293b", margin=dict(l=20, r=20, t=40, b=20),
                xaxis_tickangle=-45, height=400,
                xaxis=dict(gridcolor="#e2e8f0"), yaxis=dict(gridcolor="#e2e8f0"),
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {str(e)}")
    else:
        st.info("No hay suficientes columnas para generar gráficos.")
