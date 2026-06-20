"""
Panel de Reportes v2.0 - Punto de entrada principal (OPTIMIZADO).
"""

import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
from streamlit_option_menu import option_menu

from utils import buscar_columna, buscar_columna_fecha, resolver_columnas
from data import REPORTES, cargar
from ui import (
    TAM_FUENTE, inject_css,
    renderizar_aggrid_desktop, renderizar_aggrid_movil,
    renderizar_graficos
)


# ===========================================================================
# CONFIGURACIÓN INICIAL
# ===========================================================================

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

@st.cache_data
def init_app():
    """Inicializa el CSS global (cacheado)."""
    inject_css()

init_app()


# ===========================================================================
# BARRA LATERAL DE ICONOS (RAIL)
# ===========================================================================

def inject_icon_rail(reportes, reporte_activo):
    """
    Inyecta una barra lateral estrecha con iconos de navegación.
    Oculta el sidebar nativo de Streamlit.
    """
    reportes_js = json.dumps({k: v["icono"] for k, v in reportes.items()})
    activo_js = json.dumps(reporte_activo)

    html = f"""
    <style>
    /* Ocultar el sidebar nativo de Streamlit */
    section[data-testid="stSidebar"] {{
        display: none !important;
    }}
    /* Ajustar el área principal para que empiece después de la barra */
    .stApp {{
        margin-left: 64px !important;
    }}
    /* Nuestra barra personalizada */
    #icon-rail {{
        position: fixed;
        top: 0;
        left: 0;
        width: 64px;
        height: 100vh;
        background: #1e3a5f;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding-top: 1rem;
        z-index: 999999;
        box-shadow: 2px 0 8px rgba(0,0,0,0.15);
    }}
    .rail-icon {{
        width: 48px;
        height: 48px;
        margin: 6px 0;
        border-radius: 12px;
        background: transparent;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        color: #cbd5e1;
        cursor: pointer;
        transition: background 0.2s, color 0.2s;
        position: relative;
    }}
    .rail-icon:hover {{
        background: #2563eb;
        color: white;
    }}
    .rail-icon.active {{
        background: #3b82f6;
        color: white;
        box-shadow: 0 0 0 2px #93c5fd;
    }}
    /* Tooltip que aparece al pasar el ratón */
    .rail-icon::after {{
        content: attr(data-tooltip);
        position: absolute;
        left: 100%;
        top: 50%;
        transform: translateY(-50%);
        background: #1e293b;
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        white-space: nowrap;
        font-size: 13px;
        margin-left: 10px;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s;
        z-index: 100;
    }}
    .rail-icon:hover::after {{
        opacity: 1;
    }}
    /* Espacio flexible para empujar los botones inferiores */
    .rail-spacer {{
        flex: 1;
    }}
    .rail-btn {{
        width: 48px;
        height: 48px;
        margin: 6px 0;
        border-radius: 12px;
        background: transparent;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        color: #cbd5e1;
        cursor: pointer;
        transition: background 0.2s, color 0.2s;
    }}
    .rail-btn:hover {{
        background: #2563eb;
        color: white;
    }}
    /* Responsive: en móvil ocultar la barra y restaurar el margen */
    @media (max-width: 768px) {{
        #icon-rail {{
            display: none !important;
        }}
        .stApp {{
            margin-left: 0 !important;
        }}
    }}
    </style>
    <div id="icon-rail">
        <div id="rail-icons"></div>
        <div class="rail-spacer"></div>
        <div class="rail-btn" id="refresh-btn" title="Actualizar datos">🔄</div>
    </div>
    <script>
    const reportes = {reportes_js};
    const activo = {activo_js};
    const container = document.getElementById('rail-icons');

    for (const [nombre, icono] of Object.entries(reportes)) {{
        const div = document.createElement('div');
        div.className = 'rail-icon' + (nombre === activo ? ' active' : '');
        div.setAttribute('data-tooltip', nombre);
        div.innerHTML = icono;
        div.onclick = () => {{
            const url = new URL(window.parent.location.href);
            url.searchParams.set('reporte', encodeURIComponent(nombre));
            // Eliminar el parámetro de refresco para no activarlo de nuevo
            url.searchParams.delete('refresh');
            window.parent.location.href = url.toString();
        }};
        container.appendChild(div);
    }}

    // Botón de actualizar: añade ?refresh=1 y recarga
    document.getElementById('refresh-btn').onclick = () => {{
        const url = new URL(window.parent.location.href);
        url.searchParams.set('refresh', '1');
        window.parent.location.href = url.toString();
    }};
    </script>
    """
    components.html(html, height=0, scrolling=False)


# ===========================================================================
# LEER REPORTE DESDE LA URL Y APLICAR REFRESCO
# ===========================================================================

params = st.query_params
reporte_url = params.get("reporte", None)
if reporte_url:
    reporte = reporte_url
else:
    reporte = list(REPORTES.keys())[0]   # primer reporte como defecto

# Si se pulsó el botón de actualizar (refresh=1), limpiar caché y recargar
if params.get("refresh"):
    st.cache_data.clear()
    # Limpiar el parámetro para evitar bucle y recargar
    st.query_params.clear()
    st.rerun()

# Inyectar la barra de iconos (después de leer los params, antes de dibujar nada)
inject_icon_rail(REPORTES, reporte)

cfg = REPORTES[reporte]


# ===========================================================================
# INICIALIZAR ESTADOS DE CONFIGURACIÓN DE VISTA
# ===========================================================================
if 'forzar_movil' not in st.session_state:
    st.session_state.forzar_movil = False
if 'tabla_tam' not in st.session_state:
    st.session_state.tabla_tam = "Mediano"


# ===========================================================================
# CARGAR DATOS
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

@st.cache_data
def get_columnas_sugeridas(df_f, col_fecha, cat_cols, col_busc, cfg):
    todas_cols = df_f.columns.tolist()
    if "columnas" in cfg:
        sugeridas, faltan_cols = resolver_columnas(df_f, cfg["columnas"])
    else:
        faltan_cols = []
        sugeridas = []
        for c in [col_fecha] + cat_cols + ([col_busc] if col_busc else []):
            if c and c not in sugeridas:
                sugeridas.append(c)
        for c in todas_cols:
            if c not in sugeridas:
                sugeridas.append(c)
    return sugeridas, faltan_cols, todas_cols

sugeridas, faltan_cols, todas_cols = get_columnas_sugeridas(
    df_f, col_fecha, cat_cols, col_busc, cfg
)

if "agrupar" in cfg:
    cols_agrupar, _ = resolver_columnas(df_f, cfg["agrupar"])
else:
    cols_agrupar = [c for c in cat_cols if c]


# ===========================================================================
# CONTROLES DE FILTRO (AHORA EN LA PÁGINA PRINCIPAL)
# ===========================================================================
with st.expander("🔍 Filtros", expanded=True):
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
                        @st.cache_data
                        def get_opciones_cat(df, col):
                            return sorted(df[col].dropna().unique().tolist(), key=lambda x: str(x))

                        opts = get_opciones_cat(df, col)
                        sel = st.multiselect(
                            f"📂 {col}", opts, placeholder="Todos",
                            key=f"cat_{reporte}{col}{i}_{j}"
                        )
                        if sel:
                            df_f = df_f[df_f[col].isin(sel)]

                    elif tipo == "busc":
                        @st.cache_data
                        def get_opciones_busc(df, col):
                            return sorted(df[col].dropna().astype(str).unique().tolist(), key=lambda x: x.lower())

                        opts_prod = get_opciones_busc(df_f, col)
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
# CONFIGURACIÓN DE VISTA
# ===========================================================================
with st.expander("⚙️ Configuración de vista", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.forzar_movil = st.checkbox(
            "Forzar vista móvil",
            value=st.session_state.forzar_movil,
            help="Activar para probar la vista optimizada para celular",
        )
    with col2:
        st.session_state.tabla_tam = st.select_slider(
            "Tamaño de letra",
            options=list(TAM_FUENTE.keys()),
            value=st.session_state.tabla_tam,
            help="Ajusta el tamaño de fuente de la tabla",
        )


# ===========================================================================
# AVISOS DE COLUMNAS FALTANTES
# ===========================================================================
if faltantes_aviso:
    st.caption("⚠️ No se encontraron: " + ", ".join(faltantes_aviso))
if "columnas" in cfg and faltan_cols:
    st.caption("⚠️ Columnas no encontradas: " + ", ".join(faltan_cols))


# ===========================================================================
# SELECTOR DE COLUMNAS
# ===========================================================================
usa_vista_movil = st.session_state.forzar_movil
tiene_config_movil = "columnas_movil" in cfg

if not usa_vista_movil:
    with st.expander("⚙️ Columnas visibles"):
        cols_mostrar = st.multiselect(
            "Seleccionar columnas", todas_cols,
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
font_px = TAM_FUENTE.get(st.session_state.tabla_tam, 14)

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
