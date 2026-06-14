import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

# --- Estilo oscuro tipo dashboard ---
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #1e2535; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #e2e8f0; }
h1 { color: #f8fafc !important; font-size: 1.6rem !important; font-weight: 700 !important; }
h2, h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
label { color: #94a3b8 !important; font-size: 0.78rem !important; text-transform: uppercase; }
[data-testid="metric-container"] { background: #161b27; border: 1px solid #1e2535; border-radius: 10px; padding: 14px 18px; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #38bdf8 !important; }
</style>
""", unsafe_allow_html=True)

# --- Conexión a R2 ---
@st.cache_resource
def get_conn():
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

con = get_conn()
BUCKET = st.secrets["R2_BUCKET"]

REPORTES = {
    "Ajuste de Inventario":   "ajusteinventario.parquet",
    "Compras":                "compras.parquet",
    "Inventario Valorizado":  "inventariovalorizado.parquet",
    "Receta Base":            "recetabase.parquet",
    "Receta Venta":           "recetaventa.parquet",
}

@st.cache_data(ttl=3600)
def cargar(archivo):
    url = f"s3://{BUCKET}/{archivo}"
    return con.execute(f"SELECT * FROM read_parquet('{url}')").df()

# --- Interfaz ---
st.title("📊 Panel de Reportes")

reporte = st.sidebar.selectbox("Reporte", list(REPORTES.keys()))
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()
    st.rerun()

df = cargar(REPORTES[reporte])

st.subheader(reporte)
st.caption(f"{len(df):,} filas · {len(df.columns)} columnas")

st.dat
