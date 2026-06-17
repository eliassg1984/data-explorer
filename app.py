import unicodedata
import pandas as pd
import streamlit as st
import duckdb
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

# CSS
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #0d1424; border-right: 1px solid #1e3a5f; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #e2e8f0; }
h1 { color: #f8fafc !important; font-size: 1.6rem !important; font-weight: 700 !important; }
h2, h3 { color: #93c5fd !important; font-weight: 600 !important; }
h4 { color: #60a5fa !important; font-weight: 600 !important; }
label { color: #94a3b8 !important; font-size: 0.78rem !important; text-transform: uppercase; }
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
#   archivo / icono  -> obligatorios
#   columnas         -> columnas a mostrar por defecto (en ese orden)
#   filtros_cat      -> multiselects en cascada en la parte superior
#   buscador         -> columna con buscador multiple (tipo Excel)
#   fecha            -> columna de fecha (None = sin filtro de fecha)
#   agrupar          -> jerarquia para agrupar con +/- (tabla dinamica)
# Los reportes sin estas claves usan deteccion automatica.
# ---------------------------------------------------------------------------
REPORTES = {
    "Ajuste de Inventario":  {"archivo": "ajusteinventario.parquet",     "icono": "sliders"},
    "Compras":               {"archivo": "compras.parquet",              "icono": "cart"},
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
    },
    "Receta Base":           {"archivo": "recetabase.parquet",           "icono": "clipboard-data"},
    "Receta Venta":          {"archivo": "recetaventa.parquet",          "icono": "receipt"},
}


@st.cache_data(ttl=3600)
def cargar(archivo):
    try:
        url = f"s3://{BUCKET}/{archivo}"
        return con.execute(f"SELECT * FROM read_parquet('{url}')").df()
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None


# Interfaz principal
st.title("📊 Panel de Reportes")

with st.sidebar:
    reporte = option_menu(
        menu_title="Reporte",
        options=list(REPORTES.keys()),
        icons=[v["icono"] for v in REPORTES.values()],
        menu_icon="bar-chart-fill",
        default_index=0,
        styles={
            "container": {"padding": "4px", "background-color": "#0d1424"},
            "menu-title": {"color": "#60a5fa", "font-size": "13px",
                           "text-transform": "uppercase", "letter-spacing": "1px"},
            "icon": {"color": "#60a5fa", "font-size": "18px"},
            "nav-link": {"font-size": "14px", "color": "#cbd5e1",
                         "background-color": "#111c33", "margin": "5px 0",
                         "border-radius": "8px", "--hover-color": "#1e3a5f"},
            "nav-link-selected": {"background-color": "#2563eb", "color": "#ffffff"},
        },
    )
    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

cfg = REPORTES[reporte]

# Cargar datos
df = cargar(cfg["archivo"])
if df is None or df.empty:
    st.warning("No se pudieron cargar los datos o el archivo está vacío.")
    st.stop()

st.subheader(reporte)

# ---------------------------------------------------------------------------
# Determinar columnas de filtro (config explicita o deteccion automatica)
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

# Aviso si algun nombre configurado no se encontro
faltantes_aviso = list(faltan_cat)
if "buscador" in cfg and cfg["buscador"] and not col_busc:
    faltantes_aviso.append(cfg["buscador"])

# ---------------------------------------------------------------------------
# Filtros superiores
# ---------------------------------------------------------------------------
df_f = df.copy()
if col_fecha:
    df_f[col_fecha] = pd.to_datetime(df_f[col_fecha], errors="coerce")

st.markdown("#### Filtros")

# Fila 1: fecha + categoricos en cascada
fila1 = [c for c in ([col_fecha] if col_fecha else []) + cat_cols]
if fila1:
    columnas = st.columns(len(fila1))
    idx = 0

    if col_fecha and df_f[col_fecha].notna().any():
        with columnas[idx]:
            fmin = df_f[col_fecha].min().date()
            fmax = df_f[col_fecha].max().date()
            rango = st.date_input("📅 Fecha", value=(fmin, fmax),
                                  min_value=fmin, max_value=fmax,
                                  format="DD/MM/YYYY", key=f"fch_{reporte}")
            if isinstance(rango, (tuple, list)) and len(rango) == 2:
                ini, fin = rango
                df_f = df_f[(df_f[col_fecha].dt.date >= ini) &
                            (df_f[col_fecha].dt.date <= fin)]
        idx += 1

    for cc in cat_cols:
        with columnas[idx]:
            opts = sorted(df_f[cc].dropna().unique().tolist(), key=lambda x: str(x))
            sel = st.multiselect(cc, opts, placeholder="Todos", key=f"cat_{reporte}_{cc}")
            if sel:
                df_f = df_f[df_f[cc].isin(sel)]
        idx += 1

# Buscador de producto (multiple, tipo Excel). El multiselect ya filtra
# las sugerencias a medida que escribes, sin distinguir mayus/minus.
if col_busc:
    opts_prod = sorted(df_f[col_busc].dropna().astype(str).unique().tolist(),
                       key=lambda x: x.lower())
    sel_prod = st.multiselect(f"🔎 {col_busc}", opts_prod,
                              placeholder="Escribe para buscar… (vacío = todos)",
                              key=f"busc_{reporte}")
    if sel_prod:
        df_f = df_f[df_f[col_busc].astype(str).isin(sel_prod)]

if faltantes_aviso:
    st.caption("⚠️ No se encontraron estas columnas en el archivo: "
               + ", ".join(faltantes_aviso) + ". Revisa el nombre exacto.")

# Contador
if len(df_f) != len(df):
    st.caption(f"{len(df_f):,} de {len(df):,} filas (filtrado) · {len(df_f.columns)} columnas")
else:
    st.caption(f"{len(df_f):,} filas · {len(df_f.columns)} columnas")

if df_f.empty:
    st.warning("Ningún registro coincide con los filtros seleccionados.")
    st.stop()

# ---------------------------------------------------------------------------
# Columnas a mostrar (default por config) + opcion de agrupar con +/-
# ---------------------------------------------------------------------------
st.markdown("#### Tabla")

todas_cols = df_f.columns.tolist()

if "columnas" in cfg:
    sugeridas, faltan_cols = resolver_columnas(df_f, cfg["columnas"])
    if faltan_cols:
        st.caption("⚠️ Columnas configuradas no encontradas: " + ", ".join(faltan_cols))
else:
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

# Columnas para agrupar (jerarquia)
if "agrupar" in cfg:
    cols_agrupar, _ = resolver_columnas(df_f, cfg["agrupar"])
else:
    cols_agrupar = [c for c in cat_cols if c]

c_grp, c_cols = st.columns([2, 3])
with c_grp:
    grupos_sel = st.multiselect(
        "Agrupar por", cols_agrupar, default=[], key=f"grp_{reporte}",
        placeholder="Sin agrupar",
        help="Elige una o varias columnas. Cada una tendrá su propio +/- "
             "(como agrupar en Excel). Vacío = tabla plana.",
    )
with c_cols:
    cols_mostrar = st.multiselect("Columnas a mostrar", todas_cols, default=sugeridas,
                                  key=f"cols_{reporte}", placeholder="Selecciona columnas")
if not cols_mostrar:
    cols_mostrar = sugeridas

agrupar_on = bool(grupos_sel)

# Asegura que las columnas de agrupacion esten presentes para poder agrupar
cols_finales = list(cols_mostrar)
if agrupar_on:
    for c in grupos_sel:
        if c not in cols_finales:
            cols_finales.append(c)

df_grid = df_f[cols_finales]

st.caption("💡 Elige columnas en “Agrupar por” para la vista con +/-, o usa el panel "
           "derecho (Columns / Filters) para pivotear y sumar manualmente.")

# ---------------------------------------------------------------------------
# AgGrid
# ---------------------------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df_grid)
gb.configure_default_column(resizable=True, filter=True, sortable=True,
                            editable=False, groupable=True, enableRowGroup=True,
                            enablePivot=True, enableValue=True)

# Agregaciones: promedio para "precio/promedio", suma para el resto de numericos
for c in df_grid.columns:
    if pd.api.types.is_numeric_dtype(df_grid[c]):
        af = "avg" if ("precio" in _norm(c) or "promedio" in _norm(c)) else "sum"
        gb.configure_column(c, aggFunc=af, type=["numericColumn"],
                            valueFormatter="x == null ? '' : x.toLocaleString()")

opciones_grid = {"autoGroupColumnDef": {"minWidth": 200}, "localeText": LOCALE_ES}

if agrupar_on:
    for c in grupos_sel:
        if c in df_grid.columns:
            gb.configure_column(c, rowGroup=True, hide=True)
    # Una columna por cada campo agrupado, cada una con su propio +/- (estilo Excel)
    opciones_grid["groupDisplayType"] = "multipleColumns"
    opciones_grid["groupDefaultExpanded"] = 0      # arranca colapsado -> expandir con +
    opciones_grid["groupMultiAutoColumn"] = True   # respaldo si la version es antigua
    opciones_grid["pivotMode"] = False
else:
    opciones_grid["pivotMode"] = False

gb.configure_side_bar()
gb.configure_grid_options(**opciones_grid)
gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
grid_options = gb.build()

# Tema oscuro para la grilla (combina con el panel)
custom_css = {
    ".ag-root-wrapper": {"background-color": "#0d1424", "border": "1px solid #1e3a5f"},
    ".ag-header": {"background-color": "#111c33", "border-bottom": "1px solid #1e3a5f"},
    ".ag-header-cell-text": {"color": "#93c5fd", "font-weight": "600"},
    ".ag-row": {"color": "#e2e8f0", "border-color": "#1e2535"},
    ".ag-row-even": {"background-color": "#0f1117"},
    ".ag-row-odd": {"background-color": "#0d1424"},
    ".ag-row-hover": {"background-color": "#1e3a5f !important"},
    ".ag-cell": {"color": "#e2e8f0"},
    ".ag-group-value": {"color": "#e2e8f0"},
    ".ag-paging-panel": {"color": "#cbd5e1", "background-color": "#0d1424",
                         "border-top": "1px solid #1e3a5f"},
    ".ag-side-bar": {"background-color": "#0d1424", "border-color": "#1e3a5f"},
    ".ag-status-bar": {"background-color": "#0d1424"},
    ".ag-menu": {"background-color": "#111c33", "color": "#e2e8f0"},
}

# Ajusta al ancho si hay pocas columnas visibles
visibles = len(cols_mostrar) - (len([c for c in grupos_sel if c in cols_mostrar]) if agrupar_on else 0)
ajustar = visibles <= 8

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

# ---------------------------------------------------------------------------
# Grafico de barras sobre los datos filtrados
# ---------------------------------------------------------------------------
cols_num = df_f.select_dtypes("number").columns.tolist()
cols_txt = df_f.select_dtypes(["object", "string"]).columns.tolist()
if cols_num and cols_txt:
    col1, col2 = st.columns(2)
    with col1:
        eje_x = st.selectbox("Agrupar por", cols_txt, key=f"ejex_{reporte}")
    with col2:
        eje_y = st.selectbox("Sumar", cols_num, key=f"ejey_{reporte}")
    try:
        datos = (df_f.groupby(eje_x)[eje_y].sum()
                     .reset_index().sort_values(eje_y, ascending=False).head(20))
        fig = px.bar(datos, x=eje_x, y=eje_y, title=f"{eje_y} por {eje_x} (top 20)",
                     color_discrete_sequence=["#2563eb"])
        fig.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117",
                          font_color="#e2e8f0")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error generando gráfico: {str(e)}")
else:
    st.info("No hay suficientes columnas numéricas y de texto para generar gráficos.")
