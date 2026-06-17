import unicodedata
import pandas as pd
import streamlit as st
import duckdb
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# CSS GLOBAL - TEMA CLARO MODERNO
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

/* Inputs y selectores */
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

/* Botones */
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

/* Expander */
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

/* Caption */
.stCaption {
    color: var(--text-muted) !important;
}

/* Warning */
.stWarning {
    background: #fef3c7 !important;
    border: 1px solid #fcd34d !important;
    color: #92400e !important;
    border-radius: 8px !important;
}

/* Info */
.stInfo {
    background: var(--accent-light) !important;
    border: 1px solid #93c5fd !important;
    color: #1e40af !important;
    border-radius: 8px !important;
}

/* Error */
.stError {
    background: #fee2e2 !important;
    border: 1px solid #fca5a5 !important;
    color: #991b1b !important;
    border-radius: 8px !important;
}

/* ============ ESTILOS MÓVIL (pantallas ≤ 768px) ============ */
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
    
    .js-plotly-plot { max-height: 300px !important; }
}

/* ============ TABLA MÓVIL CON SCROLL - TEMA CLARO ============ */
.tabla-scroll-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    max-width: 100%;
    border-radius: 12px;
    border: 1px solid var(--border);
    position: relative;
    margin: 12px 0;
    box-shadow: var(--shadow-md);
    background: var(--bg-card);
}

.tabla-scroll-wrapper {
    min-width: 100%;
    display: inline-block;
}

.tabla-scroll-indicator {
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    background: linear-gradient(90deg, transparent, rgba(248, 250, 252, 0.9));
    padding: 20px 15px;
    pointer-events: none;
    z-index: 10;
    transition: opacity 0.3s;
}

.tabla-scroll-indicator::after {
    content: "👉";
    font-size: 1.5rem;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
}

.tabla-movil {
    border-collapse: collapse;
    width: auto;
    min-width: 100%;
    font-size: 0.85rem;
}

.tabla-movil th {
    background: #f1f5f9;
    color: #1e293b;
    font-weight: 700;
    padding: 14px 18px;
    text-align: left;
    border-bottom: 2px solid #3b82f6;
    white-space: nowrap;
    position: sticky;
    top: 0;
    z-index: 5;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.tabla-movil th.col-fija {
    position: sticky;
    left: 0;
    background: #f1f5f9;
    z-index: 10;
    box-shadow: 3px 0 8px rgba(0, 0, 0, 0.06);
}

.tabla-movil td.col-fija {
    position: sticky;
    left: 0;
    background: inherit;
    z-index: 5;
    box-shadow: 3px 0 8px rgba(0, 0, 0, 0.06);
    font-weight: 500;
}

.tabla-movil td {
    padding: 14px 18px;
    border-bottom: 1px solid #e2e8f0;
    white-space: nowrap;
    color: #334155;
}

.tabla-movil tr {
    transition: background-color 0.15s;
}

.tabla-movil tr:hover td {
    background-color: #eff6ff !important;
}

.tabla-movil tr:nth-child(even) td {
    background-color: #ffffff;
}

.tabla-movil tr:nth-child(odd) td {
    background-color: #f8fafc;
}

.tabla-movil .num-col {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

/* Badges */
.badge-area {
    display: inline-block;
    background: #dbeafe;
    color: #1e40af;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    white-space: nowrap;
    font-weight: 500;
}

.badge-familia {
    display: inline-block;
    background: #e0e7ff;
    color: #3730a3;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    white-space: nowrap;
    font-weight: 500;
}

.badge-subfamilia {
    display: inline-block;
    background: #f1f5f9;
    color: #475569;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    white-space: nowrap;
}

/* Estados de stock */
.stock-bajo {
    color: #dc2626 !important;
    font-weight: 700;
    background: #fef2f2;
    padding: 2px 8px;
    border-radius: 6px;
}

.stock-normal {
    color: #059669 !important;
    font-weight: 600;
}

.stock-alto {
    color: #0891b2 !important;
    font-weight: 600;
}

/* Valorizado */
.valor-destacado {
    color: #059669 !important;
    font-weight: 700;
}

/* Swipe hint */
.swipe-hint {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 10px;
    color: #64748b;
    font-size: 0.8rem;
    background: #f1f5f9;
    border-radius: 10px;
    margin-bottom: 12px;
    border: 1px solid #e2e8f0;
}

@keyframes swipe-animation {
    0%, 100% { transform: translateX(0); }
    50% { transform: translateX(10px); }
}

.swipe-icon {
    animation: swipe-animation 1.5s infinite;
    font-size: 1.2rem;
}

/* Estilos para el sidebar option_menu */
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
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Utilidades: detectar columnas sin importar mayusculas/acentos/espacios
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
    """Devuelve (encontradas_reales, faltantes) a partir de una lista de nombres."""
    encontradas, faltantes = [], []
    for n in nombres:
        real = buscar_columna(df, n)
        if real and real not in encontradas:
            encontradas.append(real)
        elif not real:
            faltantes.append(n)
    return encontradas, faltantes


# ---------------------------------------------------------------------------
# Traducción de la interfaz de AgGrid al español
# ---------------------------------------------------------------------------
LOCALE_ES = {
    # Menú de columna
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
    "addToValues": "Agregar ${variable} a valores",
    "removeFromValues": "Quitar ${variable} de valores",
    "addToLabels": "Agregar ${variable} a etiquetas",
    "removeFromLabels": "Quitar ${variable} de etiquetas",
    "resetColumns": "Restablecer columnas",
    "expandAll": "Expandir todos los grupos",
    "collapseAll": "Colapsar todos los grupos",
    "copy": "Copiar",
    "copyWithHeaders": "Copiar con encabezados",
    "copyWithGroupHeaders": "Copiar con encabezados de grupo",
    "ctrlC": "Ctrl+C",
    "paste": "Pegar",
    "ctrlV": "Ctrl+V",
    "export": "Exportar",
    "csvExport": "Exportar a CSV",
    "excelExport": "Exportar a Excel",
    "chooseColumns": "Elegir columnas",
    "columnChooser": "Elegir columnas",
    # Panel lateral
    "columns": "Columnas",
    "filters": "Filtros",
    "pivotMode": "Modo dinámico",
    "groups": "Grupos de filas",
    "rowGroupColumnsEmptyMessage": "Arrastra aquí para agrupar por filas",
    "values": "Valores",
    "valueColumnsEmptyMessage": "Arrastra aquí para agregar",
    "pivots": "Etiquetas de columna",
    "pivotColumnsEmptyMessage": "Arrastra aquí para etiquetas de columna",
    # Filtros
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
    "lessThanOrEqual": "Menor o igual que",
    "greaterThanOrEqual": "Mayor o igual que",
    "inRange": "En rango",
    "andCondition": "Y",
    "orCondition": "O",
    # Paginación
    "page": "Página",
    "to": "a",
    "of": "de",
    "more": "más",
    "nextPage": "Página siguiente",
    "lastPage": "Última página",
    "firstPage": "Primera página",
    "previousPage": "Página anterior",
    "pageSizeSelectorLabel": "Tamaño de página:",
    # Agregaciones
    "sum": "Suma",
    "min": "Mín",
    "max": "Máx",
    "none": "Ninguno",
    "count": "Conteo",
    "avg": "Promedio",
    "average": "Promedio",
    "first": "Primero",
    "last": "Último",
    "group": "Grupo",
    # Estados
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
# Configuracion por reporte.
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
        "columnas_fijas_movil": [
            "Nombre Producto",
            "Stock al dia",
            "Precio Promedio",
            "Valorizado total",
        ],
        "columnas_scroll_movil": [
            "Codigo Producto",
            "Nombre Area",
            "Nombre Familia",
            "Nombre Subfamilia",
            "Unidad Kardex",
        ],
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
# FUNCIÓN PARA RENDERIZAR TABLA MÓVIL CON SCROLL
# ---------------------------------------------------------------------------
def renderizar_tabla_movil(df_f, columnas_ordenadas, columnas_fijas_reales):
    """Renderiza tabla optimizada para móvil con columnas fijas y scroll horizontal."""
    
    FILAS_POR_PAGINA = 20
    total_filas = len(df_f)
    total_paginas = max(1, (total_filas + FILAS_POR_PAGINA - 1) // FILAS_POR_PAGINA)
    
    # Control de paginación
    if 'pagina_actual' not in st.session_state:
        st.session_state.pagina_actual = 1
    
    if 'reporte_anterior' not in st.session_state:
        st.session_state.reporte_anterior = None
    if st.session_state.reporte_anterior != reporte:
        st.session_state.pagina_actual = 1
        st.session_state.reporte_anterior = reporte
    
    # Indicador de swipe
    st.markdown("""
    <div class="swipe-hint">
        <span>👈 Desliza para ver más columnas</span>
        <span class="swipe-icon">👆</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Controles de paginación
    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
    with col1:
        if st.button("◀", disabled=st.session_state.pagina_actual == 1, key="btn_prev"):
            st.session_state.pagina_actual -= 1
            st.rerun()
    with col2:
        if st.button("▶", disabled=st.session_state.pagina_actual == total_paginas, key="btn_next"):
            st.session_state.pagina_actual += 1
            st.rerun()
    with col3:
        st.caption(f"Pág. {st.session_state.pagina_actual} de {total_paginas} • {total_filas} productos")
    with col4:
        st.caption(f"{FILAS_POR_PAGINA} por pág.")
    
    # Obtener datos de la página actual
    inicio = (st.session_state.pagina_actual - 1) * FILAS_POR_PAGINA
    fin = min(inicio + FILAS_POR_PAGINA, total_filas)
    df_pagina = df_f.iloc[inicio:fin]
    
    # Construir HTML de la tabla
    html_tabla = '<div class="tabla-scroll-container"><div class="tabla-scroll-wrapper"><table class="tabla-movil">'
    
    # Encabezados
    html_tabla += '<thead><tr>'
    for col in columnas_ordenadas:
        es_fija = col in columnas_fijas_reales
        clase_fija = 'col-fija' if es_fija else ''
        clase_num = 'num-col' if pd.api.types.is_numeric_dtype(df_pagina[col]) else ''
        html_tabla += f'<th class="{clase_fija} {clase_num}">{col}</th>'
    html_tabla += '</tr></thead><tbody>'
    
    # Filas de datos
    for idx, row in df_pagina.iterrows():
        html_tabla += '<tr>'
        for col in columnas_ordenadas:
            valor = row[col]
            es_fija = col in columnas_fijas_reales
            clase_fija = 'col-fija' if es_fija else ''
            
            # Formatear según tipo de columna
            if pd.isna(valor):
                valor_str = '<span style="color: #94a3b8;">—</span>'
                clase_extra = ''
            elif "valorizado" in _norm(col):
                valor_str = f'S/ <strong>{valor:,.2f}</strong>'
                clase_extra = 'num-col valor-destacado'
            elif "precio" in _norm(col) or "promedio" in _norm(col):
                valor_str = f'S/ {valor:,.2f}'
                clase_extra = 'num-col'
            elif "stock" in _norm(col):
                if isinstance(valor, (int, float)):
                    if valor < 10:
                        valor_str = f'<span class="stock-bajo">{valor:,.0f}</span>'
                    elif valor > 100:
                        valor_str = f'<span class="stock-alto">{valor:,.0f}</span>'
                    else:
                        valor_str = f'<span class="stock-normal">{valor:,.0f}</span>'
                else:
                    valor_str = str(valor)
                clase_extra = 'num-col'
            elif "area" in _norm(col):
                valor_str = f'<span class="badge-area">{valor}</span>'
                clase_extra = ''
            elif "familia" in _norm(col):
                valor_str = f'<span class="badge-familia">{valor}</span>'
                clase_extra = ''
            elif "subfamilia" in _norm(col):
                valor_str = f'<span class="badge-subfamilia">{valor}</span>'
                clase_extra = ''
            elif "fecha" in _norm(col) and pd.api.types.is_datetime64_any_dtype(df_pagina[col]):
                valor_str = valor.strftime('%d/%m/%Y')
                clase_extra = ''
            elif pd.api.types.is_numeric_dtype(df_pagina[col]):
                if valor == int(valor):
                    valor_str = f'{valor:,.0f}'
                else:
                    valor_str = f'{valor:,.2f}'
                clase_extra = 'num-col'
            else:
                valor_str = str(valor)
                clase_extra = ''
            
            html_tabla += f'<td class="{clase_fija} {clase_extra}">{valor_str}</td>'
        html_tabla += '</tr>'
    
    html_tabla += '</tbody></table>'
    html_tabla += '<div class="tabla-scroll-indicator" id="scroll-indicator"></div>'
    html_tabla += '</div></div>'
    
    # Renderizar
    st.markdown(html_tabla, unsafe_allow_html=True)
    
    # Script para ocultar indicador al llegar al final del scroll
    st.markdown("""
    <script>
    (function() {
        const container = document.querySelector('.tabla-scroll-container');
        const indicator = document.getElementById('scroll-indicator');
        
        if (container && indicator) {
            function checkScroll() {
                const maxScroll = container.scrollWidth - container.clientWidth;
                if (container.scrollLeft >= maxScroll - 10) {
                    indicator.style.opacity = '0';
                } else {
                    indicator.style.opacity = '1';
                }
            }
            
            container.addEventListener('scroll', checkScroll);
            setTimeout(checkScroll, 500);
        }
    })();
    </script>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# FUNCIÓN PARA RENDERIZAR TABLA DESKTOP (AgGrid) - Tema claro
# ---------------------------------------------------------------------------
def renderizar_tabla_desktop(df_grid, grupos_sel, cols_mostrar):
    """Renderiza tabla AgGrid para escritorio con tema claro."""
    
    gb = GridOptionsBuilder.from_dataframe(df_grid)
    gb.configure_default_column(
        resizable=True,
        filter=True,
        sortable=True,
        editable=False,
        groupable=True,
        enableRowGroup=True,
        enablePivot=True,
        enableValue=True,
    )
    
    # Agregaciones
    for c in df_grid.columns:
        if pd.api.types.is_numeric_dtype(df_grid[c]):
            af = "avg" if ("precio" in _norm(c) or "promedio" in _norm(c)) else "sum"
            gb.configure_column(
                c,
                aggFunc=af,
                type=["numericColumn"],
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
        opciones_grid["groupMultiAutoColumn"] = True
        opciones_grid["pivotMode"] = False
    else:
        opciones_grid["pivotMode"] = False
    
    gb.configure_side_bar()
    gb.configure_grid_options(**opciones_grid)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()
    
    # Tema claro para AgGrid
    custom_css = {
        ".ag-root-wrapper": {
            "background-color": "#ffffff",
            "border": "1px solid #e2e8f0",
            "border-radius": "8px",
        },
        ".ag-header": {
            "background-color": "#f1f5f9",
            "border-bottom": "2px solid #3b82f6",
        },
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155"},
        ".ag-group-value": {"color": "#1e293b", "font-weight": "600"},
        ".ag-paging-panel": {
            "color": "#64748b",
            "background-color": "#f8fafc",
            "border-top": "1px solid #e2e8f0",
        },
        ".ag-side-bar": {
            "background-color": "#f8fafc",
            "border-color": "#e2e8f0",
        },
        ".ag-status-bar": {"background-color": "#f8fafc"},
        ".ag-menu": {
            "background-color": "#ffffff",
            "color": "#1e293b",
            "border": "1px solid #e2e8f0",
        },
        ".ag-tabs-header": {"background-color": "#f1f5f9"},
    }
    
    visibles = len(cols_mostrar) - (len([c for c in grupos_sel if c in cols_mostrar]) if agrupar_on else 0)
    ajustar = visibles <= 6
    
    AgGrid(
        df_grid.head(5000),
        gridOptions=grid_options,
        height=470,
        theme="balham",
        custom_css=custom_css,
        fit_columns_on_grid_load=ajustar,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        key=f"grid_{reporte}",
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
        default_index=0,
        styles={
            "container": {"padding": "4px", "background-color": "#f1f5f9"},
            "menu-title": {
                "color": "#475569",
                "font-size": "13px",
                "text-transform": "uppercase",
                "letter-spacing": "1px",
                "font-weight": "700",
            },
            "icon": {"color": "#3b82f6", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px",
                "color": "#475569",
                "background-color": "#ffffff",
                "margin": "5px 0",
                "border-radius": "8px",
                "--hover-color": "#eff6ff",
                "border": "1px solid #e2e8f0",
            },
            "nav-link-selected": {
                "background-color": "#3b82f6",
                "color": "#ffffff",
                "border": "1px solid #3b82f6",
            },
        },
    )
    
    st.markdown("---")
    
    # Toggle para vista móvil
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
# DETERMINAR COLUMNAS DE FILTRO
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
# PROCESAMIENTO DE DATOS
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
                        "📅 Fecha",
                        value=(fmin, fmax),
                        min_value=fmin,
                        max_value=fmax,
                        format="DD/MM/YYYY",
                        key=f"fch_{reporte}_{i}_{j}",
                    )
                    if isinstance(rango, (tuple, list)) and len(rango) == 2:
                        ini, fin = rango
                        df_f = df_f[(df_f[col].dt.date >= ini) & (df_f[col].dt.date <= fin)]
                
                elif tipo == "cat":
                    opts = sorted(df_f[col].dropna().unique().tolist(), key=lambda x: str(x))
                    sel = st.multiselect(
                        f"📂 {col}",
                        opts,
                        placeholder="Todos",
                        key=f"cat_{reporte}_{col}_{i}_{j}",
                    )
                    if sel:
                        df_f = df_f[df_f[col].isin(sel)]
                
                elif tipo == "busc":
                    opts_prod = sorted(
                        df_f[col].dropna().astype(str).unique().tolist(),
                        key=lambda x: x.lower(),
                    )
                    sel_prod = st.multiselect(
                        f"🔎 {col}",
                        opts_prod,
                        placeholder="Buscar… (vacío = todos)",
                        key=f"busc_{reporte}_{i}_{j}",
                    )
                    if sel_prod:
                        df_f = df_f[df_f[col].astype(str).isin(sel_prod)]
                
                elif tipo == "grp":
                    grupos_sel = st.multiselect(
                        "📊 Agrupar por",
                        cols_agrupar,
                        default=[],
                        key=f"grp_{reporte}_{i}_{j}",
                        placeholder="Sin agrupar",
                    )

# ---------------------------------------------------------------------------
# AVISOS Y SELECTOR DE COLUMNAS
# ---------------------------------------------------------------------------
if faltantes_aviso:
    st.caption("⚠️ No se encontraron estas columnas: " + ", ".join(faltantes_aviso) + ".")
if "columnas" in cfg and faltan_cols:
    st.caption("⚠️ Columnas no encontradas: " + ", ".join(faltan_cols))

with st.expander("⚙️ Configuración de columnas"):
    cols_mostrar = st.multiselect(
        "Seleccionar columnas visibles",
        todas_cols,
        default=sugeridas,
        key=f"cols_{reporte}",
        label_visibility="collapsed",
        placeholder="Selecciona columnas",
    )

if not cols_mostrar:
    cols_mostrar = sugeridas

# ---------------------------------------------------------------------------
# CONTADOR
# ---------------------------------------------------------------------------
if len(df_f) != len(df):
    st.caption(f"📊 Mostrando {len(df_f):,} de {len(df):,} filas (filtrado)")
else:
    st.caption(f"📊 Total: {len(df_f):,} filas")

if df_f.empty:
    st.warning("Ningún registro coincide con los filtros seleccionados.")
    st.stop()

# ---------------------------------------------------------------------------
# MODO VISTA
# ---------------------------------------------------------------------------
usa_vista_movil = st.session_state.get('forzar_movil', False)
tiene_config_movil = (
    "columnas_fijas_movil" in cfg and 
    "columnas_scroll_movil" in cfg
)
usa_vista_movil = usa_vista_movil or tiene_config_movil

# ---------------------------------------------------------------------------
# RENDERIZAR TABLA
# ---------------------------------------------------------------------------
if usa_vista_movil and tiene_config_movil:
    # VISTA MÓVIL
    columnas_fijas_reales = []
    for col in cfg["columnas_fijas_movil"]:
        real = buscar_columna(df_f, col)
        if real and real not in columnas_fijas_reales:
            columnas_fijas_reales.append(real)
    
    columnas_scroll_reales = []
    for col in cfg["columnas_scroll_movil"]:
        real = buscar_columna(df_f, col)
        if real and real not in columnas_scroll_reales:
            columnas_scroll_reales.append(real)
    
    columnas_ordenadas = columnas_fijas_reales + columnas_scroll_reales
    
    if not columnas_ordenadas:
        columnas_ordenadas = todas_cols
        columnas_fijas_reales = todas_cols[:min(3, len(todas_cols))]
    
    df_tabla = df_f[columnas_ordenadas]
    renderizar_tabla_movil(df_tabla, columnas_ordenadas, columnas_fijas_reales)

else:
    # VISTA DESKTOP
    cols_finales = list(cols_mostrar)
    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c not in cols_finales:
                cols_finales.append(c)
    
    df_grid = df_f[cols_finales]
    renderizar_tabla_desktop(df_grid, grupos_sel, cols_mostrar)

# ---------------------------------------------------------------------------
# GRÁFICO DE BARRAS - Tema claro
# ---------------------------------------------------------------------------
st.markdown("---")
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
        datos = (
            df_f.groupby(eje_x)[eje_y].sum()
            .reset_index()
            .sort_values(eje_y, ascending=False)
            .head(20)
        )
        
        fig = px.bar(
            datos,
            x=eje_x,
            y=eje_y,
            title=f"{eje_y} por {eje_x} (top 20)",
            color_discrete_sequence=["#3b82f6"],
        )
        
        fig.update_layout(
            paper_bgcolor="#f8fafc",
            plot_bgcolor="#ffffff",
            font_color="#1e293b",
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_tickangle=-45,
            height=400,
            dragmode=False,
            xaxis=dict(gridcolor="#e2e8f0"),
            yaxis=dict(gridcolor="#e2e8f0"),
        )
        
        fig.update_traces(marker_line_color="#2563eb", marker_line_width=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📋 Ver datos del gráfico"):
            st.dataframe(datos, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error generando gráfico: {str(e)}")
else:
    st.info("No hay suficientes columnas numéricas y de texto para generar gráficos.")
