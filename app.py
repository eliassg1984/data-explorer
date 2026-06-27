"""
Panel de Reportes v2.0 - Punto de entrada principal (OPTIMIZADO).
"""

import pandas as pd
import streamlit as st
import plotly.express as px

from utils import buscar_columna, buscar_columna_fecha, resolver_columnas
from data import REPORTES, cargar, secrets_disponibles
from estilos import TAM_FUENTE, inject_css
from inyecciones import inject_error_overlay, inject_element_inspector
from tablas import renderizar_aggrid_desktop, renderizar_aggrid_movil, renderizar_tabla_compras
from graficos import renderizar_graficos
from navegacion import inject_icon_rail, inject_top_bar


# ===========================================================================
# CONFIGURACIÓN INICIAL
# ===========================================================================

st.set_page_config(
    page_title="Reportes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
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

inject_error_overlay()
inject_element_inspector()


# ===========================================================================
# LEER REPORTE DESDE LA URL Y APLICAR REFRESCO
# ===========================================================================

params = st.query_params
reporte = params.get("reporte", None)
if not reporte or reporte not in REPORTES:
    reporte = list(REPORTES.keys())[0]

if params.get("refresh"):
    st.cache_data.clear()
    if "refresh" in st.query_params:
        del st.query_params["refresh"]
    st.rerun()

inject_icon_rail(REPORTES, reporte, mostrar_inspector=bool(st.query_params.get("debug")))
inject_top_bar(reporte)

cfg = REPORTES[reporte]


# ===========================================================================
# AVISO DE MODO DEMO + PANEL DE DIAGNÓSTICO (?debug=1)
# ===========================================================================
modo_demo = not secrets_disponibles()
if modo_demo:
    st.caption("🧪 MODO DEMO — datos de ejemplo (no hay conexión a R2). "
               "Configura los secrets R2_* para usar datos reales.")

if st.query_params.get("debug"):
    import sys
    from importlib.metadata import version, PackageNotFoundError

    def _ver(paquete):
        try:
            return version(paquete)
        except PackageNotFoundError:
            return "?"

    with st.expander("🔧 Diagnóstico de entorno", expanded=True):
        st.json({
            "python": sys.version.split()[0],
            "streamlit": _ver("streamlit"),
            "streamlit-aggrid": _ver("streamlit-aggrid"),
            "pandas": _ver("pandas"),
            "plotly": _ver("plotly"),
            "duckdb": _ver("duckdb"),
            "modo_demo": modo_demo,
            "reporte": reporte,
        })


# ===========================================================================
# INICIALIZAR ESTADOS DE CONFIGURACIÓN DE VISTA
# ===========================================================================
if 'forzar_movil' not in st.session_state:
    st.session_state.forzar_movil = False
if 'tabla_tam' not in st.session_state:
    st.session_state.tabla_tam = "Mediano"


# ===========================================================================
# INSPECTOR: herramienta de verificación de datos crudos
# ===========================================================================
if reporte == "Inspector" or cfg.get("tool"):
    from inspector import render_inspector
    render_inspector()
    st.stop()


# ===========================================================================
# CARGAR DATOS
# ===========================================================================
df = cargar(cfg["archivo"])
if df is None or df.empty:
    st.warning("No se pudieron cargar los datos o el archivo está vacío.")
    st.stop()


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
# CONTROLES DE FILTRO — st.popover
# ===========================================================================

fecha_min_full = fecha_max_full = None
if col_fecha and df_f[col_fecha].notna().any():
    fecha_min_full = df_f[col_fecha].min().date()
    fecha_max_full = df_f[col_fecha].max().date()

controles = []
for cc in cat_cols:
    controles.append(("cat", cc))
if col_busc:
    controles.append(("busc", col_busc))
if cols_agrupar:
    controles.append(("grp", None))
if fecha_min_full is not None and reporte != "Requerimientos":
    controles.append(("fecha", col_fecha))

grupos_sel = []


# ── PASO 1: función cacheada FUERA del loop ────────────────────────────
@st.cache_data
def get_opciones_filtro(_df, _col):
    """Retorna las opciones únicas de una columna, ordenadas."""
    return sorted(_df[_col].dropna().unique().tolist(), key=lambda x: str(x))
# ── FIN PASO 1 ──────────────────────────────────────────────────────────


def _key(prefijo, idx):
    return f"{prefijo}_{reporte}_{idx}"

def _contar_filtros_activos():
    n = 0
    for idx, (tipo, col) in enumerate(controles):
        if tipo == "fecha":
            val = st.session_state.get(_key("fch", idx))
            if isinstance(val, (tuple, list)) and len(val) == 2:
                if val[0] != fecha_min_full or val[1] != fecha_max_full:
                    n += 1
        elif tipo == "cat":
            if st.session_state.get(_key("cat", idx)):
                n += 1
        elif tipo == "busc":
            if st.session_state.get(_key("busc", idx)):
                n += 1
    return n

n_activos = _contar_filtros_activos()
label_btn = f"🔍 Filtros{'  ·  ' + str(n_activos) + ' activo' + ('s' if n_activos != 1 else '') if n_activos else ''}"

with st.popover(label_btn, use_container_width=False):
    for idx, (tipo, col) in enumerate(controles):
        if tipo == "cat":
            opts = get_opciones_filtro(df, col)
            sel = st.multiselect(
                f"📂 {col}", opts, placeholder="Todos",
                key=_key("cat", idx),
            )
            if sel:
                df_f = df_f[df_f[col].isin(sel)]

        elif tipo == "busc":
            opts_prod = get_opciones_filtro(df_f, col)
            sel_prod = st.multiselect(
                f"🔎 {col}", opts_prod, placeholder="Buscar…",
                key=_key("busc", idx),
            )
            if sel_prod:
                df_f = df_f[df_f[col].astype(str).isin(sel_prod)]

        elif tipo == "grp":
            grupos_sel = st.multiselect(
                "📊 Agrupar por", cols_agrupar, default=[],
                key=_key("grp", idx), placeholder="Sin agrupar",
            )

        elif tipo == "fecha":
            rango = st.date_input(
                "📅 Fecha", value=(fecha_min_full, fecha_max_full),
                min_value=fecha_min_full, max_value=fecha_max_full,
                format="DD/MM/YYYY", key=_key("fch", idx),
            )
            if isinstance(rango, (tuple, list)) and len(rango) == 2:
                ini, fin = rango
                df_f = df_f[(df_f[col].dt.date >= ini) & (df_f[col].dt.date <= fin)]

    # El slider de tamaño de letra solo aplica en reportes con AgGrid
    if reporte not in ("Compras", "Salidas"):
        st.divider()
        st.session_state.tabla_tam = st.select_slider(
            "🔠 Tamaño de letra",
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
# SELECTOR DE COLUMNAS (solo para reportes con AgGrid)
# ===========================================================================
usa_vista_movil = st.session_state.forzar_movil
tiene_config_movil = "columnas_movil" in cfg

if not usa_vista_movil:
    cols_mostrar = todas_cols

    if reporte == "Inventario Valorizado":
        columnas_iniciales = ["Nombre Producto", "Stock al Dia", "Nombre Area", "Valorizado total"]
        cols_visibles = []
        for _c in columnas_iniciales:
            _real = buscar_columna(df_f, _c)
            if _real and _real not in cols_visibles:
                cols_visibles.append(_real)
    else:
        cols_visibles = sugeridas
else:
    cols_mostrar_movil, _ = resolver_columnas(df_f, cfg.get("columnas_movil", []))
    if not cols_mostrar_movil:
        cols_mostrar_movil = sugeridas[:5]
    cols_mostrar  = cols_mostrar_movil
    cols_visibles = cols_mostrar_movil


# ===========================================================================
# VERIFICACIÓN DE DATOS VACÍOS
# ===========================================================================
if df_f.empty:
    st.warning("Ningún registro coincide con los filtros.")
    st.stop()


# ===========================================================================
# CONTENIDO PRINCIPAL
# ===========================================================================
font_px = TAM_FUENTE.get(st.session_state.tabla_tam, 14)


# ── PASO 3: gráficos genéricos en una sola función ──────────────────────
def _render_graficos_genericos(df_data, nombre_reporte):
    """Renderiza selectores + gráfico de barras top 20.
    Reemplaza el bloque que estaba copiado en Compras, Salidas y resto."""
    cols_num = df_data.select_dtypes("number").columns.tolist()
    cols_txt = df_data.select_dtypes(["object", "string"]).columns.tolist()

    if not cols_num or not cols_txt:
        st.info("No hay suficientes columnas para generar gráficos.")
        return

    col1, col2 = st.columns(2)
    with col1:
        eje_x = st.selectbox("Agrupar por", cols_txt, key=f"ejex_{nombre_reporte}")
    with col2:
        eje_y = st.selectbox("Métrica (suma)", cols_num, key=f"ejey_{nombre_reporte}")

    try:
        datos = (df_data.groupby(eje_x)[eje_y].sum()
                     .reset_index()
                     .sort_values(eje_y, ascending=False)
                     .head(20))
        fig = px.bar(datos, x=eje_x, y=eje_y,
                     title=f"{eje_y} por {eje_x} (top 20)",
                     color_discrete_sequence=["#3b82f6"])
        fig.update_layout(
            paper_bgcolor="#f8fafc", plot_bgcolor="#ffffff",
            font_color="#1e293b", margin=dict(l=20, r=20, t=40, b=20),
            xaxis_tickangle=-45, height=400,
            xaxis=dict(gridcolor="#e2e8f0"),
            yaxis=dict(gridcolor="#e2e8f0"),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {str(e)}")
# ── FIN PASO 3 ──────────────────────────────────────────────────────────


def _render_tabla():
    """Renderiza la tabla AgGrid (desktop o móvil)."""
    if usa_vista_movil and tiene_config_movil:
        st.caption("📱 Vista móvil • Desliza para más columnas • Mantén presionado para menú")
        columnas_fijas = cfg.get("columnas_fijas_movil", 2)
        renderizar_aggrid_movil(df_f[cols_mostrar], columnas_fijas, reporte, font_px)
    else:
        cols_finales = list(cols_mostrar)
        if grupos_sel:
            for c in grupos_sel:
                if c not in cols_finales:
                    cols_finales.append(c)
        renderizar_aggrid_desktop(
            df_f[cols_finales], grupos_sel, cols_mostrar, reporte, font_px,
            cols_visibles=cols_visibles,
        )


# ── COMPRAS: st.data_editor ──────────────────────────────────────────────────
if reporte == "Compras":
    tab_tabla, tab_graficos = st.tabs(["📋 Tabla", "📊 Gráficos"])

    with tab_tabla:
        renderizar_tabla_compras(df_f, grupos_sel=grupos_sel)

    with tab_graficos:
        _render_graficos_genericos(df_f, reporte)


# ── INVENTARIO VALORIZADO ────────────────────────────────────────────────────
elif reporte == "Inventario Valorizado":
    st.markdown(
        '<p style="font-size:22px;font-weight:700;color:#1e293b;'
        'margin:0 0 0.6rem 0;line-height:1.2;">Inventario Valorizado</p>',
        unsafe_allow_html=True,
    )
    _OPCIONES_VISTA = {"Tabla": ":material/table_chart:", "Gráficos": ":material/bar_chart:"}
    vista = st.segmented_control(
        "Vista",
        options=list(_OPCIONES_VISTA.keys()),
        format_func=lambda o: f"{_OPCIONES_VISTA[o]} {o}",
        default="Tabla",
        label_visibility="collapsed",
        key=f"vista_seg_{reporte}",
    )
    if vista is None:
        vista = "Tabla"
    if vista == "Tabla":
        _render_tabla()
    else:
        renderizar_graficos(df_f, es_movil=usa_vista_movil)


# ── SALIDAS ──────────────────────────────────────────────────────────────────
elif reporte == "Salidas":
    tab_tabla, tab_graficos = st.tabs(["📋 Tabla", "📊 Gráficos"])

    with tab_tabla:
        if usa_vista_movil and tiene_config_movil:
            st.caption("📱 Vista móvil • Desliza para más columnas")
            renderizar_aggrid_movil(
                df_f[cols_mostrar], cfg.get("columnas_fijas_movil", 2), reporte, font_px,
            )
        else:
            _k_cols = f"colsel_{reporte}"
            if _k_cols not in st.session_state:
                st.session_state[_k_cols] = list(todas_cols)
            _vigentes = [c for c in st.session_state[_k_cols] if c in todas_cols]
            st.session_state[_k_cols] = _vigentes or list(todas_cols)

            _k_zoom = f"zoom_{reporte}"
            if _k_zoom not in st.session_state:
                st.session_state[_k_zoom] = 14

            barra = st.columns([3, 3, 1.4])
            with barra[0]:
                with st.popover("🧰 Columnas", use_container_width=True):
                    st.caption("Mostrar u ocultar columnas")
                    cols_sel = st.multiselect(
                        "Columnas visibles", todas_cols,
                        key=_k_cols, label_visibility="collapsed",
                    )
            with barra[1]:
                zoom = st.select_slider(
                    "🔍 Zoom", options=[12, 14, 16, 18, 20, 22], key=_k_zoom,
                )
            with barra[2]:
                st.download_button(
                    "⬇️ CSV",
                    data=df_f.to_csv(index=False).encode("utf-8-sig"),
                    file_name="salidas_export.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key=f"export_{reporte}",
                )

            if not cols_sel:
                cols_sel = list(todas_cols)

            def _es_moneda_kpi(n):
                n = str(n).lower()
                return any(k in n for k in ("importe", "total", "monto", "precio", "costo"))

            def _es_cant_kpi(n):
                n = str(n).lower()
                return any(k in n for k in ("cantidad", "unidades", "qty"))

            cols_imp = [c for c in df_f.columns
                        if pd.api.types.is_numeric_dtype(df_f[c]) and _es_moneda_kpi(c)]
            cols_cnt = [c for c in df_f.columns
                        if pd.api.types.is_numeric_dtype(df_f[c]) and _es_cant_kpi(c)]
            n_kpi = min(4, 1 + len(cols_imp[:2]) + len(cols_cnt[:1]))
            kpis = st.columns(n_kpi)
            kpis[0].metric("📄 Registros", f"{len(df_f):,}")
            ki = 1
            for c in cols_imp[:2]:
                if ki >= n_kpi:
                    break
                kpis[ki].metric(f"💰 {c}", f"S/ {df_f[c].sum():,.2f}")
                ki += 1
            for c in cols_cnt[:1]:
                if ki >= n_kpi:
                    break
                kpis[ki].metric(f"📦 {c}", f"{int(df_f[c].sum()):,}")
                ki += 1

            cols_finales = list(cols_sel)
            if grupos_sel:
                for c in grupos_sel:
                    if c not in cols_finales:
                        cols_finales.append(c)
            renderizar_aggrid_desktop(
                df_f[cols_finales], grupos_sel, cols_sel, reporte, int(zoom),
                cols_visibles=None,
            )

    with tab_graficos:
        _render_graficos_genericos(df_f, reporte)


# ── REQUERIMIENTOS ───────────────────────────────────────────────────────────
elif reporte == "Requerimientos":
    st.markdown(
        '<p style="font-size:22px;font-weight:700;color:#1e293b;'
        'margin:0 0 0.6rem 0;line-height:1.2;">Requerimientos · Tabla dinámica</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "🧮 Tabla dinámica estilo Excel. En el panel derecho (pestaña "
        "**Columnas**) arrastra campos a **Grupos de filas**, **Valores** y "
        "**Etiquetas de columnas**. Para columnas por periodo legibles, usa los "
        "campos **Mes** o **Año** (ya calculados) en *Etiquetas de columnas*. "
        "El **filtro de fecha** está arriba de la tabla (rango desde / hasta)."
    )

    df_piv = df_f.copy()

    # Convierte a datetime todas las columnas que parezcan fechas
    for _c in df_piv.columns:
        _n = str(_c).lower()
        if "fecha" in _n or "date" in _n or pd.api.types.is_datetime64_any_dtype(df_piv[_c]):
            df_piv[_c] = pd.to_datetime(df_piv[_c], errors="coerce")

    # ── FIX: calcular Mes y Año ANTES del filtro de fecha ─────────────────
    _col_freg = buscar_columna(df_piv, "Fecha Registro", "fecha registro") or col_fecha

    if _col_freg and _col_freg in df_piv.columns:
        _fechas_full = pd.to_datetime(df_piv[_col_freg], errors="coerce")
        df_piv["Mes"] = (
            _fechas_full.dt.to_period("M")
            .astype(str)
            .str.replace("NaT", "", regex=False)
        )
        df_piv["Año"] = (
            _fechas_full.dt.year
            .astype("Int64")
            .astype(str)
            .str.replace("<NA>", "", regex=False)
        )

    # ── Filtro de fecha (recorta filas pero Mes/Año ya están calculados) ──
    cols_fecha_piv = [c for c in df_piv.columns
                      if pd.api.types.is_datetime64_any_dtype(df_piv[c])]

    if cols_fecha_piv:
        fc1, fc2 = st.columns([1, 2])
        with fc1:
            col_fecha_sel = st.selectbox(
                "📅 Filtrar por", cols_fecha_piv, key="req_fcol",
            )

        validos = df_piv[col_fecha_sel].dropna()
        if not validos.empty:
            fmin, fmax = validos.min().date(), validos.max().date()

            with fc2:
                rango = st.date_input(
                    "Rango (desde / hasta)",
                    value=(fmin, fmax),
                    min_value=fmin,
                    max_value=fmax,
                    format="DD/MM/YYYY",
                    key="req_frango",
                )

            if isinstance(rango, (tuple, list)) and len(rango) == 2:
                ini, fin = rango
                _m = (df_piv[col_fecha_sel].dt.date >= ini) & \
                     (df_piv[col_fecha_sel].dt.date <= fin)
                df_piv = df_piv[_m]

    # ── AgGrid ────────────────────────────────────────────────────────────
    if usa_vista_movil and tiene_config_movil:
        st.caption("📱 Vista móvil")
        renderizar_aggrid_movil(
            df_piv[cols_mostrar], cfg.get("columnas_fijas_movil", 2), reporte, font_px,
        )
    else:
        renderizar_aggrid_desktop(
            df_piv,
            grupos_sel,
            list(df_piv.columns),
            reporte,
            font_px,
            cols_visibles=None,
        )


# ── RESTO DE REPORTES ────────────────────────────────────────────────────────
else:
    tab_tabla, tab_graficos = st.tabs(["📋 Tabla", "📊 Gráficos"])

    with tab_tabla:
        _render_tabla()

    with tab_graficos:
        _render_graficos_genericos(df_f, reporte)
