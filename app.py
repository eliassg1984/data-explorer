import streamlit as st
import pandas as pd
import numpy as np
import random

st.set_page_config(page_title="Data Explorer", page_icon="📊", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# ── Datos de ejemplo ───────────────────────────────────────────
@st.cache_data
def generar_datos(nombre):
    random.seed(42)
    np.random.seed(42)
    n = 500
    if nombre == "Ventas":
        return pd.DataFrame({
            "fecha":      pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
            "producto":   np.random.choice(["Laptop", "Mouse", "Teclado", "Monitor", "Auriculares"], n),
            "categoria":  np.random.choice(["Electrónica", "Accesorios", "Audio"], n),
            "region":     np.random.choice(["Lima", "Arequipa", "Cusco", "Trujillo"], n),
            "monto":      np.round(np.random.uniform(50, 3000, n), 2),
            "unidades":   np.random.randint(1, 20, n),
            "descuento":  np.round(np.random.uniform(0, 0.3, n), 2),
        })
    elif nombre == "Clientes":
        return pd.DataFrame({
            "cliente_id": range(1, n+1),
            "nombre":     [f"Cliente {i}" for i in range(1, n+1)],
            "ciudad":     np.random.choice(["Lima", "Arequipa", "Cusco", "Trujillo", "Piura"], n),
            "segmento":   np.random.choice(["Premium", "Estándar", "Básico"], n),
            "edad":       np.random.randint(18, 70, n),
            "compras":    np.random.randint(1, 50, n),
            "gasto_total":np.round(np.random.uniform(100, 15000, n), 2),
        })
    elif nombre == "Productos":
        return pd.DataFrame({
            "sku":        [f"SKU-{i:04d}" for i in range(1, n+1)],
            "nombre":     [f"Producto {i}" for i in range(1, n+1)],
            "categoria":  np.random.choice(["Electrónica", "Accesorios", "Audio", "Gaming"], n),
            "precio":     np.round(np.random.uniform(10, 2000, n), 2),
            "stock":      np.random.randint(0, 500, n),
            "proveedor":  np.random.choice(["ProvA", "ProvB", "ProvC"], n),
            "rating":     np.round(np.random.uniform(1, 5, n), 1),
        })
    elif nombre == "Pedidos":
        return pd.DataFrame({
            "pedido_id":  range(1001, 1001+n),
            "estado":     np.random.choice(["Entregado", "Pendiente", "Cancelado", "En camino"], n),
            "ciudad":     np.random.choice(["Lima", "Arequipa", "Cusco"], n),
            "canal":      np.random.choice(["Web", "App", "Tienda"], n),
            "total":      np.round(np.random.uniform(30, 5000, n), 2),
            "items":      np.random.randint(1, 10, n),
            "dias_entrega": np.random.randint(1, 15, n),
        })
    else:
        return pd.DataFrame({
            "almacen":    np.random.choice(["Lima Norte", "Lima Sur", "Callao"], n),
            "producto":   np.random.choice(["Laptop", "Mouse", "Teclado", "Monitor"], n),
            "stock":      np.random.randint(0, 1000, n),
            "minimo":     np.random.randint(10, 50, n),
            "costo":      np.round(np.random.uniform(20, 1500, n), 2),
            "ultima_entrada": pd.date_range("2024-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
        })

ARCHIVOS = ["Ventas", "Clientes", "Productos", "Pedidos", "Inventario"]

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Data Explorer")
    st.caption("🟡 Modo demo — datos de ejemplo")
    nombre_archivo = st.selectbox("Archivo", ARCHIVOS)
    st.divider()

    df_raw = generar_datos(nombre_archivo)
    todas_cols = df_raw.columns.tolist()
    cols_num   = df_raw.select_dtypes(include="number").columns.tolist()
    cols_cat   = df_raw.select_dtypes(exclude="number").columns.tolist()

    st.markdown("**Filtros**")
    filtros = {}
    for col in cols_cat[:4]:
        vals = sorted(df_raw[col].dropna().unique().tolist())
        if len(vals) <= 20:
            sel = st.multiselect(col, vals, default=[], key=f"f_{col}")
            if sel:
                filtros[col] = sel
    for col in cols_num[:2]:
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

# ── Filtros ────────────────────────────────────────────────────
def aplicar_filtros(df, filtros):
    for col, val in filtros.items():
        if isinstance(val, list):
            df = df[df[col].isin(val)]
        elif isinstance(val, tuple):
            df = df[(df[col] >= val[0]) & (df[col] <= val[1])]
    return df

df_filtrado = aplicar_filtros(df_raw.copy(), filtros)

# ── Header ─────────────────────────────────────────────────────
st.markdown(f"## {nombre_archivo}")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Filas totales",    f"{len(df_raw):,}")
m2.metric("Filas filtradas",  f"{len(df_filtrado):,}")
m3.metric("Columnas",         f"{len(todas_cols)}")
m4.metric("Cols. numéricas",  f"{len(cols_num)}")
st.divider()

tab1, tab2, tab3 = st.tabs(["📋 Datos", "🔢 Tabla dinámica", "📈 Gráfico"])

# ── TAB 1 ──────────────────────────────────────────────────────
with tab1:
    buscar   = st.text_input("🔍 Buscar", placeholder="Escribe para filtrar...")
    cols_vis = st.multiselect("Columnas visibles", todas_cols, default=todas_cols)
    df_vista = df_filtrado[cols_vis] if cols_vis else df_filtrado
    if buscar:
        mask = df_vista.apply(lambda c: c.astype(str).str.contains(buscar, case=False, na=False))
        df_vista = df_vista[mask.any(axis=1)]
    st.dataframe(df_vista, use_container_width=True, height=460)
    st.caption(f"{len(df_vista):,} filas")

# ── TAB 2 ──────────────────────────────────────────────────────
with tab2:
    if not col_grupo:
        st.info("👈 Selecciona columnas para **Agrupar por** en el panel izquierdo.")
    else:
        if agg_func == "COUNT":
            df_pivot = df_filtrado.groupby(col_grupo).size().reset_index(name="COUNT")
        else:
            if col_valor == "— ninguna —":
                st.warning("Selecciona una columna de valor.")
                st.stop()
            agg_map = {"SUM": "sum", "AVG": "mean", "MIN": "min", "MAX": "max"}
            df_pivot = (df_filtrado.groupby(col_grupo)[col_valor]
                        .agg(agg_map[agg_func]).reset_index()
                        .rename(columns={col_valor: f"{agg_func}({col_valor})"}))
        if col_orden != "— ninguna —" and col_orden in df_pivot.columns:
            df_pivot = df_pivot.sort_values(col_orden, ascending=orden_asc)
        st.dataframe(df_pivot, use_container_width=True, height=420)
        st.caption(f"{len(df_pivot):,} grupos")

# ── TAB 3 ──────────────────────────────────────────────────────
with tab3:
    g1, g2, g3 = st.columns(3)
    tipo_g = g1.selectbox("Tipo", ["Barras", "Línea", "Área", "Dispersión"])
    eje_x  = g2.selectbox("Eje X", ["— ninguna —"] + todas_cols)
    eje_y  = g3.multiselect("Eje Y", cols_num, default=cols_num[:1])
    max_f  = st.slider("Máx. filas", 100, len(df_filtrado), min(500, len(df_filtrado)), 50)

    if eje_x == "— ninguna —" or not eje_y:
        st.info("👆 Selecciona Eje X y al menos una columna para Eje Y.")
    else:
        df_g = df_filtrado[[eje_x] + eje_y].dropna().head(max_f).set_index(eje_x)
        if tipo_g == "Barras":   st.bar_chart(df_g, use_container_width=True, height=420)
        elif tipo_g == "Línea":  st.line_chart(df_g, use_container_width=True, height=420)
        elif tipo_g == "Área":   st.area_chart(df_g, use_container_width=True, height=420)
        elif tipo_g == "Dispersión":
            if len(eje_y) >= 2:
                st.scatter_chart(df_g, x=eje_y[0], y=eje_y[1], use_container_width=True, height=420)
            else:
                st.info("Para dispersión selecciona al menos 2 columnas en Eje Y.")
        st.caption(f"{min(max_f, len(df_filtrado)):,} filas graficadas")
