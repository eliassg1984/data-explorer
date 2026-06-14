import duckdb
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Data Explorer",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #0f1117; }
    [data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #1e2535; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #e2e8f0; }
    h1 { color: #f8fafc !important; font-size: 1.6rem !important; font-weight: 700 !important; }
    h2, h3 { color: #cbd5e1 !important; font-weight: 600 !important; }
    label { color: #94a3b8 !important; font-size: 0.78rem !important; text-transform: uppercase; }
    [data-testid="metric-container"] { background: #161b27; border: 1px solid #1e2535; border-radius: 10px; padding: 14px 18px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #38bdf8 !important; font-size: 1.6rem !important; font-weight: 700; }
    span[data-baseweb="tag"] { background: #1e3a5f !important; color: #7dd3fc !important; }
    .stButton > button { background: #1e3a5f !important; color: #7dd3fc !important; border: 1px solid #2563eb !important; border-radius: 6px !important; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    conn.execute(f"""
        CREATE SECRET r2_secret (
            TYPE r2,
            KEY_ID      '{st.secrets["R2_KEY_ID"]}',
            SECRET      '{st.secrets["R2_SECRET"]}',
            ACCOUNT_ID  '{st.secrets["R2_ACCOUNT_ID"]}'
        );
    """)
    return conn

BUCKET = st.secrets.get("R2_BUCKET", "tu-bucket")

ARCHIVOS = {
    "Archivo 1": f"r2://{BUCKET}/archivo1.parquet",
    "Archivo 2": f"r2://{BUCKET}/archivo2.parquet",
    "Archivo 3": f"r2://{BUCKET}/archivo3.parquet",
    "Archivo 4": f"r2://{BUCKET}/archivo4.parquet",
    "Archivo 5": f"r2://{BUCKET}/archivo5.parquet",
}

@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos(ruta: str) -> pd.DataFrame:
    conn = get_conn()
    return conn.execute(f"SELECT * FROM read_parquet('{ruta}')").df()

with st.sidebar:
    st.markdown("### 📊 Data Explorer")
    nombre_archivo = st.selectbox("Archivo", list(ARCHIVOS.keys()))
    ruta_archivo   = ARCHIVOS[nombre_archivo]
    st.divider()

    with st.spinner("Cargando datos..."):
        try:
            df_raw = cargar_datos(ruta_archivo)
            carga_ok = True
        except Exception as e:
            st.error(f"Error: {e}")
            carga_ok = False

    if carga_ok:
        todas_cols = df_raw.columns.tolist()
        cols_num   = df_raw.select_dtypes(include="number").columns.tolist()
        cols_cat   = df_raw.select_dtypes(exclude="number").columns.tolist()

        st.markdown("**Filtros**")
        filtros = {}
        for col in cols_cat[:5]:
            vals = sorted(df_raw[col].dropna().unique().tolist())
            if len(vals) <= 50:
                sel = st.multiselect(col, vals, default=[], key=f"f_{col}")
                if sel:
                    filtros[col] = sel
        for col in cols_num[:3]:
            mn, mx = float(df_raw[col].min()), float(df_raw[col].max())
            if mn < mx:
                rango = st.slider(col, mn, mx, (mn, mx), key=f"r_{col}")
                filtros[col] = rango

        st.divider()
        st.markdown("**Tabla dinámica**")
        col_grupo = st.multiselect("Agrupar por", cols_cat, key="grupo")
        col_valor = st.selectbox("Columna de valor", ["— ninguna —"] + cols_num, key="valor")
        agg_func  = st.selectbox("Agregación", ["SUM", "COUNT", "AVG", "MIN", "MAX"], key="agg")
        col_orden = st.selectbox("Ordenar por", ["— ninguna —"] + todas_cols, key="orden")
        orden_asc = st.toggle("Ascendente", value=False)

if not carga_ok:
    st.stop()

def aplicar_filtros(df, filtros):
    for col, val in filtros.items():
        if isinstance(val, list):
            df = df[df[col].isin(val)]
        elif isinstance(val, tuple):
            df = df[(df[col] >= val[0]) & (df[col] <= val[1])]
    return df

df_filtrado = aplicar_filtros(df_raw.copy(), filtros)

st.markdown(f"## {nombre_archivo}")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Filas totales",      f"{len(df_raw):,}")
m2.metric("Filas filtradas",    f"{len(df_filtrado):,}")
m3.metric("Columnas",           f"{len(todas_cols)}")
m4.metric("Cols. numéricas",    f"{len(cols_num)}")
st.divider()

tab1, tab2, tab3 = st.tabs(["📋 Datos", "🔢 Tabla dinámica", "📈 Gráfico"])

with tab1:
    buscar   = st.text_input("🔍 Buscar", placeholder="Escribe para filtrar...")
    cols_vis = st.multiselect("Columnas visibles", todas_cols, default=todas_cols)
    df_vista = df_filtrado[cols_vis] if cols_vis else df_filtrado
    if buscar:
        mask = df_vista.apply(lambda c: c.astype(str).str.contains(buscar, case=False, na=False))
        df_vista = df_vista[mask.any(axis=1)]
    st.dataframe(df_vista, use_container_width=True, height=480)
    st.caption(f"{len(df_vista):,} filas")

with tab2:
    if not col_grupo:
        st.info("👈 Selecciona columnas para Agrupar por en el panel izquierdo.")
    else:
        if agg_func == "COUNT":
            df_pivot = df_filtrado.groupby(col_grupo).size().reset_index(name="COUNT")
        else:
            agg_map = {"SUM": "sum", "AVG": "mean", "MIN": "min", "MAX": "max"}
            df_pivot = (df_filtrado.groupby(col_grupo)[col_valor]
                        .agg(agg_map[agg_func]).reset_index()
                        .rename(columns={col_valor: f"{agg_func}({col_valor})"}))
        if col_orden != "— ninguna —" and col_orden in df_pivot.columns:
            df_pivot = df_pivot.sort_values(col_orden, ascending=orden_asc)
        st.dataframe(df_pivot, use_container_width=True, height=420)
        st.caption(f"{len(df_pivot):,} grupos")

with tab3:
    g1, g2, g3 = st.columns(3)
    tipo_g = g1.selectbox("Tipo", ["Barras", "Línea", "Área", "Dispersión"])
    eje_x  = g2.selectbox("Eje X", ["— ninguna —"] + todas_cols)
    eje_y  = g3.multiselect("Eje Y", cols_num, default=cols_num[:1])
    max_f  = st.slider("Máx. filas", 100, min(5000, len(df_filtrado)), min(1000, len(df_filtrado)), 100)

    if eje_x == "— ninguna —" or not eje_y:
        st.info("👆 Selecciona Eje X y Eje Y.")
    else:
        df_g = df_filtrado[[eje_x] + eje_y].dropna().head(max_f).set_index(eje_x)
        if tipo_g == "Barras":   st.bar_chart(df_g, use_container_width=True, height=420)
        elif tipo_g == "Línea":  st.line_chart(df_g, use_container_width=True, height=420)
        elif tipo_g == "Área":   st.area_chart(df_g, use_container_width=True, height=420)
        elif tipo_g == "Dispersión" and len(eje_y) >= 2:
            st.scatter_chart(df_g, x=eje_y[0], y=eje_y[1], use_container_width=True, height=420)
        st.caption(f"{min(max_f, len(df_filtrado)):,} filas graficadas")
