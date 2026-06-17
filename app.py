import unicodedata
import pandas as pd
import streamlit as st
import duckdb
import plotly.express as px
from st_aggrid import AgGrid, GridOptionsBuilder
from streamlit_option_menu import option_menu

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

# CSS mejorado sin saltos de línea problemáticos
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
# Utilidades para detectar columnas sin importar mayusculas/acentos/espacios
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

# Cada reporte: archivo parquet + icono (nombres de Bootstrap Icons)
REPORTES = {
    "Ajuste de Inventario":  {"archivo": "ajusteinventario.parquet",     "icono": "sliders"},
    "Compras":               {"archivo": "compras.parquet",              "icono": "cart"},
    "Inventario Valorizado": {"archivo": "inventariovalorizado.parquet", "icono": "boxes"},
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

# --- Barra lateral: botonera con iconos y tema azul ---
with st.sidebar:
    reporte = option_menu(
        menu_title="Reporte",
        options=list(REPORTES.keys()),
        icons=[v["icono"] for v in REPORTES.values()],
        menu_icon="bar-chart-fill",
        default_index=0,
        styles={
            "container": {"padding": "4px", "background-color": "#0d1424"},
            "menu-title": {
                "color": "#60a5fa", "font-size": "13px",
                "text-transform": "uppercase", "letter-spacing": "1px",
            },
            "icon": {"color": "#60a5fa", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px", "color": "#cbd5e1",
                "background-color": "#111c33", "margin": "5px 0",
                "border-radius": "8px", "--hover-color": "#1e3a5f",
            },
            "nav-link-selected": {
                "background-color": "#2563eb", "color": "#ffffff",
            },
        },
    )

    if st.button("🔄 Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Cargar datos
df = cargar(REPORTES[reporte]["archivo"])
if df is None or df.empty:
    st.warning("No se pudieron cargar los datos o el archivo está vacío.")
    st.stop()

st.subheader(reporte)

# ---------------------------------------------------------------------------
# Filtros superiores (se muestran solo los que existan en el reporte)
# ---------------------------------------------------------------------------
df_f = df.copy()

col_fecha = buscar_columna_fecha(df_f)
col_familia = buscar_columna(df_f, "familia")
col_subfamilia = buscar_columna(df_f, "subfamilia", "sub familia")
col_area = buscar_columna(df_f, "area", "área")

# Si hay columna de fecha, la convertimos una sola vez
serie_fecha = None
if col_fecha:
    df_f[col_fecha] = pd.to_datetime(df_f[col_fecha], errors="coerce")
    serie_fecha = df_f[col_fecha]

filtros_presentes = [c for c in [col_fecha, col_familia, col_subfamilia, col_area] if c]

if filtros_presentes:
    st.markdown("#### Filtros")
    columnas = st.columns(len(filtros_presentes))
    idx = 0

    # --- Fecha ---
    if col_fecha and serie_fecha is not None and serie_fecha.notna().any():
        with columnas[idx]:
            fmin = serie_fecha.min().date()
            fmax = serie_fecha.max().date()
            rango = st.date_input(
                "📅 Fecha",
                value=(fmin, fmax),
                min_value=fmin,
                max_value=fmax,
                format="DD/MM/YYYY",
            )
            if isinstance(rango, (tuple, list)) and len(rango) == 2:
                ini, fin = rango
                df_f = df_f[(df_f[col_fecha].dt.date >= ini) &
                            (df_f[col_fecha].dt.date <= fin)]
        idx += 1

    # --- Familia ---
    if col_familia:
        with columnas[idx]:
            opts = sorted(df_f[col_familia].dropna().unique().tolist(),
                          key=lambda x: str(x))
            sel = st.multiselect("Familia", opts, placeholder="Todas")
            if sel:
                df_f = df_f[df_f[col_familia].isin(sel)]
        idx += 1

    # --- Subfamilia (opciones dependen de la familia elegida) ---
    if col_subfamilia:
        with columnas[idx]:
            opts = sorted(df_f[col_subfamilia].dropna().unique().tolist(),
                          key=lambda x: str(x))
            sel = st.multiselect("Subfamilia", opts, placeholder="Todas")
            if sel:
                df_f = df_f[df_f[col_subfamilia].isin(sel)]
        idx += 1

    # --- Área ---
    if col_area:
        with columnas[idx]:
            opts = sorted(df_f[col_area].dropna().unique().tolist(),
                          key=lambda x: str(x))
            sel = st.multiselect("Área", opts, placeholder="Todas")
            if sel:
                df_f = df_f[df_f[col_area].isin(sel)]
        idx += 1
else:
    st.caption("Este reporte no tiene columnas de fecha, familia, subfamilia o área para filtrar.")

# Información del reporte (ya filtrado)
if len(df_f) != len(df):
    st.caption(f"{len(df_f):,} de {len(df):,} filas (filtrado) · {len(df_f.columns)} columnas")
else:
    st.caption(f"{len(df_f):,} filas · {len(df_f.columns)} columnas")

if df_f.empty:
    st.warning("Ningún registro coincide con los filtros seleccionados.")
    st.stop()

# ---------------------------------------------------------------------------
# Tabla dinámica tipo Excel (AgGrid)
# Abre el panel lateral derecho de la tabla para agrupar, pivotear y sumar.
# Filtra y ordena desde el encabezado de cada columna.
# ---------------------------------------------------------------------------
st.caption("💡 Abre el panel lateral derecho de la tabla para agrupar, "
           "pivotear y sumar. Filtra y ordena desde cada encabezado.")

gb = GridOptionsBuilder.from_dataframe(df_f)
gb.configure_default_column(
    resizable=True,
    filter=True,
    sortable=True,
    editable=False,
    groupable=True,
    enableRowGroup=True,
    enablePivot=True,
    enableValue=True,
    aggFunc="sum",
)
gb.configure_side_bar()
gb.configure_grid_options(
    pivotMode=False,
    autoGroupColumnDef={"minWidth": 220},
)
gb.configure_pagination(enabled=True, paginationAutoPageSize=False,
                        paginationPageSize=50)
grid_options = gb.build()

AgGrid(
    df_f.head(5000),   # limite para no saturar el WebSocket (evita el error de conexion)
    gridOptions=grid_options,
    height=450,
    theme="balham",
    fit_columns_on_grid_load=False,
    allow_unsafe_jscode=True,
    enable_enterprise_modules=True,
    key="grid_reportes",
)

# ---------------------------------------------------------------------------
# Visualización (gráfico de barras) sobre los datos filtrados
# ---------------------------------------------------------------------------
cols_num = df_f.select_dtypes("number").columns.tolist()
cols_txt = df_f.select_dtypes(["object", "string"]).columns.tolist()
if cols_num and cols_txt:
    col1, col2 = st.columns(2)
    with col1:
        eje_x = st.selectbox("Agrupar por", cols_txt)
    with col2:
        eje_y = st.selectbox("Sumar", cols_num)

    try:
        datos = (df_f.groupby(eje_x)[eje_y].sum()
                     .reset_index()
                     .sort_values(eje_y, ascending=False)
                     .head(20))

        fig = px.bar(datos, x=eje_x, y=eje_y,
                     title=f"{eje_y} por {eje_x} (top 20)",
                     color_discrete_sequence=["#2563eb"])
        fig.update_layout(
            paper_bgcolor="#0f1117",
            plot_bgcolor="#0f1117",
            font_color="#e2e8f0"
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error generando gráfico: {str(e)}")
else:
    st.info("No hay suficientes columnas numéricas y de texto para generar gráficos.")
