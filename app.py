"""
Panel de Reportes v2.0 - Punto de entrada principal (OPTIMIZADO).
"""

import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_option_menu import option_menu

from utils import buscar_columna, buscar_columna_fecha, resolver_columnas
from data import REPORTES, cargar
from ui import (
    TAM_FUENTE, inject_css, inject_sidebar_toggle,
    renderizar_aggrid_desktop, renderizar_aggrid_movil,
    renderizar_graficos
)


# ===========================================================================
# CONFIGURACIÓN INICIAL (cacheada - solo se ejecuta una vez)
# ===========================================================================

@st.cache_data
def init_app():
    """Inicializa la configuración de la app (cacheado)."""
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
    # Inyectar CSS y botón flotante (solo una vez)
    inject_css()
    inject_sidebar_toggle()

# Ejecutar inicialización
init_app()


# ===========================================================================
# FUNCIONES AUXILIARES CACHEABLES
# ===========================================================================

@st.cache_data
def get_columnas_sugeridas(df_f, col_fecha, cat_cols, col_busc, cfg):
    """Calcula las columnas sugeridas (cacheado)."""
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
    
    return sugeridas, faltan_cols, todas_cols


@st.cache_data
def get_opciones_filtro(df_f, col, tipo="cat"):
    """Obtiene opciones de filtro (cacheado)."""
    if tipo == "cat":
        return sorted(df_f[col].dropna().unique().tolist(), key=lambda x: str(x))
    elif tipo == "busc":
        return sorted(df_f[col].dropna().astype(str).unique().tolist(), key=lambda x: x.lower())
    return []


# ===========================================================================
# INTERFAZ PRINCIPAL
# ===========================================================================
st.title("📊 Panel de Reportes")


# ===========================================================================
# SIDEBAR
# ===========================================================================
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
        default_index=2,
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
    
    # ============ INICIALIZAR ESTADOS (solo si no existen) ============
    if 'forzar_movil' not in st.session_state:
        st.session_state.forzar_movil = False
    if 'tabla_tam' not in st.session_state:
        st.session_state.tabla_tam = "Mediano"
    
    # ============ CONTROLES DE VISTA ============
    with st.expander("🔧 Configuración de vista", expanded=False):
        st.markdown("### 📱 Modo de visualización")
        st.session_state.forzar_movil = st.checkbox(
            "Forzar vista móvil",
            value=st.session_state.forzar_movil,
            help="Activar para probar la vista optimizada para celular",
        )
        
        st.markdown("### 🔤 Tamaño de texto")
        st.session_state.tabla_tam = st.select_slider(
            "Tamaño de letra en tablas",
            options=list(TAM_FUENTE.keys()),
            value=st.session_state.tabla_tam,
            help="Ajusta el tamaño de fuente de la tabla de datos",
        )
        
        # Vista previa del tamaño seleccionado
        px_size = TAM_FUENTE[st.session_state.tabla_tam]
        st.markdown(f"""
        <div style="
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 8px;
            font-size: {px_size}px;
            color: #334155;
            text-align: center;
            transition: all 0.3s ease;
        ">
            👁️ Texto de ejemplo a <b>{px_size}px</b>
        </div>
        """, unsafe_allow_html=True)

cfg = REPORTES[reporte]


# ===========================================================================
# CARGAR DATOS (ya usa @st.cache_data en data.py)
# ===========================================================================
df = cargar(cfg["archivo"])
if df is None or df.empty:
    st.warning("No se pudieron cargar los datos o el archivo está vacío.")
    st.stop()

st.subheader(reporte)


# ===========================================================================
# DETERMINAR COLUMNAS
# ===========================================================================
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


# ===========================================================================
# PROCESAMIENTO
# ===========================================================================
df_f = df.copy()
if col_fecha:
    df_f[col_fecha] = pd.to_datetime(df_f[col_fecha], errors="coerce")

# Usar función cacheada para columnas sugeridas
sugeridas, faltan_cols, todas_cols = get_columnas_sugeridas(
    df_f, col_fecha, cat_cols, col_busc, cfg
)

if "agrupar" in cfg:
    cols_agrupar, _ = resolver_columnas(df_f, cfg["agrupar"])
else:
    cols_agrupar = [c for c in cat_cols if c]


# ===========================================================================
# CONTROLES DE FILTRO (optimizado con opciones cacheadas)
# ===========================================================================
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
    MAX_COLS_POR_FILA = 4
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
                        format="DD/MM/YYYY", key=f"fch_{reporte}{i}{j}",
                    )
                    if isinstance(rango, (tuple, list)) and len(rango) == 2:
                        ini, fin = rango
                        df_f = df_f[(df_f[col].dt.date >= ini) & (df_f[col].dt.date <= fin)]
                
                elif tipo == "cat":
                    opts = get_opciones_filtro(df_f, col, "cat")
                    sel = st.multiselect(
                        f"📂 {col}", opts, placeholder="Todos",
                        key=f"cat_{reporte}{col}{i}_{j}"
                    )
                    if sel:
                        df_f = df_f[df_f[col].isin(sel)]
                
                elif tipo == "busc":
                    opts_prod = get_opciones_filtro(df_f, col, "busc")
                    sel_prod = st.multiselect(
                        f"🔎 {col}", opts_prod, placeholder="Buscar…",
                        key=f"busc_{reporte}{i}{j}"
                    )
                    if sel_prod:
                        df_f = df_f[df_f[col].astype(str).isin(sel_prod)]
                
                elif tipo == "grp":
                    grupos_sel = st.multiselect(
                        "📊 Agrupar por", cols_agrupar, default=[],
                        key=f"grp_{reporte}{i}{j}", placeholder="Sin agrupar"
                    )


# ===========================================================================
# AVISOS
# ===========================================================================
if faltantes_aviso:
    st.caption("⚠️ No se encontraron: " + ", ".join(faltantes_aviso))
if "columnas" in cfg and faltan_cols:
    st.caption("⚠️ Columnas no encontradas: " + ", ".join(faltan_cols))


# ===========================================================================
# SELECTOR DE COLUMNAS
# ===========================================================================
usa_vista_movil = st.session_state.get('forzar_movil', False)
tiene_config_movil = "columnas_movil" in cfg

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


# ===========================================================================
# CONTADOR
# ===========================================================================
if len(df_f) != len(df):
    st.caption(f"📊 Mostrando {len(df_f):,} de {len(df):,} filas (filtrado)")
else:
    st.caption(f"📊 Total: {len(df_f):,} filas")

if df_f.empty:
    st.warning("Ningún registro coincide con los filtros.")
    st.stop()


# ===========================================================================
# RENDERIZAR TABLA
# ===========================================================================
font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam", "Mediano"), 14)

if usa_vista_movil and tiene_config_movil:
    st.caption("📱 Vista móvil • Desliza para más columnas • Mantén presionado para menú")
    columnas_fijas = cfg.get("columnas_fijas_movil", 2)
    df_grid_movil = df_f[cols_mostrar]
    renderizar_aggrid_movil(df_grid_movil, columnas_fijas, reporte, font_px)
else:
    cols_finales = list(cols_mostrar)
    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c not in cols_finales:
                cols_finales.append(c)
    df_grid = df_f[cols_finales]
    renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px)


# ===========================================================================
# DASHBOARD DE GRÁFICOS
# ===========================================================================
st.markdown("---")

if reporte == "Inventario Valorizado":
    st.subheader("📊 Dashboard de Análisis")
    renderizar_graficos(df_f, es_movil=usa_vista_movil)
else:
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
