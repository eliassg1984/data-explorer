import streamlit as st
import duckdb
import plotly.express as px

st.set_page_config(page_title="Reportes", page_icon="📊", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0f1117; }
[data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #1e2535; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #e2e8f0; }
h1 { color: #f8fafc !important; font-size: 1.6rem !important; font-weight: 700 !important; }
h2, h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
label { color: #94a3b8 !important; font-size: 0.78rem !important; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

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

st.title("📊 Panel de Reportes")

reporte = st.sidebar.selectbox("Reporte", list(REPORTES.keys()))
if st.sidebar.button("🔄 Actualizar datos"):
    st.cache_data.clear()
    st.rerun()

df = cargar(REPORTES[reporte])

st.subheader(reporte)
st.caption(f"{len(df):,} filas · {len(df.columns)} columnas")

st.dataframe(df.head(1000), use_container_width=True, height=400)

cols_num = df.select_dtypes("number").columns.tolist()
cols_txt = df.select_dtypes(["object", "string"]).columns.tolist()
if cols_num and cols_txt:
    c1, c2 = st.columns(2)
    eje_x = c1.selectbox("Agrupar por", cols_txt)
    eje_y = c2.selectbox("Sumar", cols_num)
    datos = (df.groupby(eje_x)[eje_y].sum()
               .reset_index().sort_values(eje_y, ascending=False).head(20))
    fig = px.bar(datos, x=eje_x, y=eje_y, title=f"{eje_y} por {eje_x} (top 20)")
    fig.update_layout(paper_bgcolor="#0f1117", plot_bgcolor="#0f1117", font_color="#e2e8f0")
    st.plotly_chart(fig, use_container_width=True)
