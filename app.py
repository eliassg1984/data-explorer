"""
Panel de Reportes v2.0 - Punto de entrada principal (OPTIMIZADO).
"""

import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px

from utils import buscar_columna, buscar_columna_fecha, resolver_columnas
from data import REPORTES, cargar
from ui import (
    TAM_FUENTE, inject_css,
    renderizar_aggrid_desktop, renderizar_aggrid_movil,
    renderizar_graficos
)


# ===========================================================================
# MAPEO DE ICONOS A EMOJIS (para la barra lateral)
# ===========================================================================
ICONO_A_EMOJI = {
    "sliders": "🎚️",
    "cart": "🛒",
    "boxes": "📦",
    "clipboard-data": "📋",
    "receipt": "🧾",
    "cash-coin": "💰",
    "box-arrow-up": "📤",
    "card-checklist": "📝",
}


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
# BARRA LATERAL DE ICONOS (RAIL) – INYECTADA DIRECTAMENTE EN LA PÁGINA
# ===========================================================================

def inject_icon_rail(reportes, reporte_activo):
    """
    Inyecta una barra lateral fija con emojis como iconos.
    Oculta el sidebar nativo y ajusta el margen del contenido.
    """
    reportes_emoji = {}
    for nombre, info in reportes.items():
        icono_txt = info.get("icono", "❓")
        reportes_emoji[nombre] = ICONO_A_EMOJI.get(icono_txt, "❓")

    reportes_js = json.dumps(reportes_emoji)
    activo_js = json.dumps(reporte_activo)

    html = f"""
    <script>
    (function() {{
        var doc = window.parent.document;
        var win = window.parent;

        // ── Inyectar estilos solo una vez (evitar duplicados) ──
        if (!doc.getElementById('icon-rail-styles')) {{
            var estilos = doc.createElement('style');
            estilos.id = 'icon-rail-styles';
            estilos.textContent = `
                section[data-testid="stSidebar"] {{
                    display: none !important;
                }}
                .stApp {{
                    margin-left: 64px !important;
                }}
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
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    overflow: visible;
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
                    overflow: visible;
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
                .rail-icon::after {{
                    content: attr(data-tooltip);
                    position: fixed;
                    left: 72px;
                    background: #1e293b;
                    color: white;
                    padding: 4px 10px;
                    border-radius: 6px;
                    white-space: nowrap;
                    font-size: 13px;
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.15s;
                    z-index: 9999999;
                    transform: translateY(-50%);
                    margin-top: 0;
                }}
                .rail-icon:hover::after {{
                    opacity: 1;
                }}
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
                @media (max-width: 768px) {{
                    #icon-rail {{ display: none !important; }}
                    .stApp {{ margin-left: 0 !important; }}
                }}
            `;
            doc.head.appendChild(estilos);
        }}

        // ── Construir el rail DOM (una sola vez; guardado en win.__iconRail) ──
        function construirRail() {{
            var rail = doc.createElement('div');
            rail.id = 'icon-rail';

            var iconsContainer = doc.createElement('div');
            iconsContainer.id = 'rail-icons';
            rail.appendChild(iconsContainer);

            var spacer = doc.createElement('div');
            spacer.className = 'rail-spacer';
            rail.appendChild(spacer);

            var refreshBtn = doc.createElement('div');
            refreshBtn.className = 'rail-btn';
            refreshBtn.title = 'Actualizar datos';
            refreshBtn.innerHTML = '🔄';
            refreshBtn.onclick = function() {{
                var url = new URL(win.location.href);
                url.searchParams.set('refresh', '1');
                win.location.assign(url.toString());
            }};
            rail.appendChild(refreshBtn);

            // Llenar iconos
            var reportes = {reportes_js};
            var activo = {activo_js};
            for (var nombre in reportes) {{
                var emoji = reportes[nombre];
                var div = doc.createElement('div');
                div.className = 'rail-icon' + (nombre === activo ? ' active' : '');
                div.setAttribute('data-tooltip', nombre);
                div.innerHTML = emoji;
                div.onclick = (function(n) {{
                    return function(e) {{
                        e.stopPropagation();
                        var url = new URL(win.location.href);
                        url.searchParams.set('reporte', encodeURIComponent(n));
                        url.searchParams.delete('refresh');
                        win.location.assign(url.toString());
                    }};
                }})(nombre);
                iconsContainer.appendChild(div);
            }}

            win.__iconRail = rail;
            return rail;
        }}

        // ── Anclar el rail al body; re-anclarlo si Streamlit lo desconecta ──
        function anclarRail() {{
            var existente = doc.getElementById('icon-rail');
            if (existente && existente.parentNode === doc.body) {{
                return; // ya está bien anclado
            }}
            if (existente) {{
                existente.parentNode.removeChild(existente);
            }}
            var rail = win.__iconRail || construirRail();
            doc.body.appendChild(rail);
        }}

        anclarRail();

        // Intervalo corto (500 ms) para sobrevivir rerenders de Streamlit
        if (!win.__iconRailInterval) {{
            win.__iconRailInterval = setInterval(anclarRail, 500);
        }}
    }})();
    </script>
    """
    components.html(html, height=0, scrolling=False)


# ===========================================================================
# FRANJA SUPERIOR DELGADA — se inyecta JUNTO al rail de iconos, no lo reemplaza
# ===========================================================================

def inject_top_bar(reporte_activo):
    """
    Inyecta una franja superior delgada y fija.
    Convive con el rail vertical de iconos (deja 64px libres a la izquierda
    en desktop; en móvil ocupa todo el ancho porque el rail se oculta).
    """
    titulo_js = json.dumps(reporte_activo)

    html = f"""
    <script>
    (function() {{
        var doc = window.parent.document;
        var win = window.parent;

        var estilos = doc.createElement('style');
        estilos.textContent = `
            /* Deja espacio para la franja superior (además del rail) */
            .stApp {{
                padding-top: 48px !important;
            }}
            #top-bar {{
                position: fixed;
                top: 0;
                left: 64px;
                right: 0;
                height: 48px;
                background: #eff6ff;
                border-bottom: 1px solid #bfdbfe;
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 0 18px;
                z-index: 999998;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            }}
            #top-bar .tb-titulo {{
                font-weight: 600;
                font-size: 14px;
                color: #1e3a5f;
                white-space: nowrap;
            }}
            #top-bar .tb-sep {{
                width: 1px;
                height: 18px;
                background: #bfdbfe;
            }}
            #top-bar .tb-spacer {{
                flex: 1;
            }}
            #top-bar .tb-btn {{
                width: 30px;
                height: 30px;
                border-radius: 8px;
                border: none;
                background: transparent;
                color: #2563eb;
                font-size: 16px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.15s;
            }}
            #top-bar .tb-btn:hover {{
                background: #dbeafe;
            }}
            @media (max-width: 768px) {{
                #top-bar {{
                    left: 0 !important;
                }}
            }}
        `;
        doc.head.appendChild(estilos);

        function crearBarra() {{
            if (doc.getElementById('top-bar')) {{
                var t = doc.querySelector('#top-bar .tb-titulo');
                if (t) t.textContent = {titulo_js};
                return;
            }}
            var bar = doc.createElement('div');
            bar.id = 'top-bar';

            var titulo = doc.createElement('span');
            titulo.className = 'tb-titulo';
            titulo.textContent = {titulo_js};
            bar.appendChild(titulo);

            var sep = doc.createElement('div');
            sep.className = 'tb-sep';
            bar.appendChild(sep);

            var spacer = doc.createElement('div');
            spacer.className = 'tb-spacer';
            bar.appendChild(spacer);

            var refreshBtn = doc.createElement('button');
            refreshBtn.className = 'tb-btn';
            refreshBtn.title = 'Actualizar datos';
            refreshBtn.innerHTML = '&#x21bb;';
            refreshBtn.onclick = function() {{
                var url = new URL(win.location.href);
                url.searchParams.set('refresh', '1');
                win.location.assign(url.toString());
            }};
            bar.appendChild(refreshBtn);

            doc.body.appendChild(bar);
        }}

        crearBarra();
        setInterval(crearBarra, 2000);
    }})();
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

if params.get("refresh"):
    st.cache_data.clear()
    st.query_params.clear()
    st.rerun()

# Inyectar el rail de iconos (igual que antes) + la franja superior delgada
inject_icon_rail(REPORTES, reporte)
inject_top_bar(reporte)

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

# El título del reporte ya se muestra en la franja superior (top-bar)


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
# CONTROLES DE FILTRO — st.popover (panel flotante, no empuja el contenido)
# ===========================================================================

# Rango COMPLETO de fechas, calculado una sola vez (estable; no depende
# del orden en que se apliquen los demás filtros).
fecha_min_full = fecha_max_full = None
if col_fecha and df_f[col_fecha].notna().any():
    fecha_min_full = df_f[col_fecha].min().date()
    fecha_max_full = df_f[col_fecha].max().date()

# Orden de los controles: categorías / buscador / agrupar PRIMERO y la
# FECHA al final. Así, al abrirse el calendario (overlay ancho) se despliega
# sobre espacio vacío en lugar de tapar los demás filtros.
controles = []
for cc in cat_cols:
    controles.append(("cat", cc))
if col_busc:
    controles.append(("busc", col_busc))
if cols_agrupar:
    controles.append(("grp", None))
if fecha_min_full is not None:
    controles.append(("fecha", col_fecha))

grupos_sel = []

# Clave única y estable por control, basada en su índice absoluto.
# (Antes el conteo usaba un paso de 4 y el render un paso de 2, así que las
#  claves no coincidían y el badge "N activos" se calculaba mal.)
def _key(prefijo, idx):
    return f"{prefijo}_{reporte}_{idx}"

# Leer valores actuales del session_state para mostrar badge en el botón
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
    # Una sola columna → el calendario de fecha no invade columnas vecinas.
    for idx, (tipo, col) in enumerate(controles):
        if tipo == "cat":
            @st.cache_data
            def get_opciones_cat(df, col):
                return sorted(df[col].dropna().unique().tolist(), key=lambda x: str(x))

            opts = get_opciones_cat(df, col)
            sel = st.multiselect(
                f"📂 {col}", opts, placeholder="Todos",
                key=_key("cat", idx),
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

    # ── Tamaño de letra de la tabla (integrado en Filtros) ──
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
# SELECTOR DE COLUMNAS
# ===========================================================================
usa_vista_movil = st.session_state.forzar_movil
tiene_config_movil = "columnas_movil" in cfg

if not usa_vista_movil:
    # Sin selector externo: TODAS las columnas van al grid y se eligen
    # desde la barra lateral nativa de AgGrid (panel "Columnas").
    cols_mostrar  = todas_cols   # universo completo disponible en la tabla
    cols_visibles = sugeridas    # las que arrancan visibles
else:
    cols_mostrar_movil, _ = resolver_columnas(df_f, cfg["columnas_movil"])
    if not cols_mostrar_movil:
        cols_mostrar_movil = sugeridas[:5]
    cols_mostrar  = cols_mostrar_movil
    cols_visibles = cols_mostrar_movil


# ===========================================================================
# VERIFICACIÓN DE DATOS VACÍOS
# (El contador de filas se eliminó a pedido; se conserva el aviso de vacío.)
# ===========================================================================
if df_f.empty:
    st.warning("Ningún registro coincide con los filtros.")
    st.stop()


# ===========================================================================
# CONTENIDO PRINCIPAL EN PESTAÑAS — tabla y gráficos sin necesidad de scroll
# ===========================================================================
font_px = TAM_FUENTE.get(st.session_state.tabla_tam, 14)

tab_tabla, tab_graficos = st.tabs(["📋 Tabla", "📊 Gráficos"])

with tab_tabla:
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
        renderizar_aggrid_desktop(
            df_grid, grupos_sel, cols_mostrar, reporte, font_px,
            cols_visibles=cols_visibles,
        )

with tab_graficos:
    if reporte == "Inventario Valorizado":
        renderizar_graficos(df_f, es_movil=usa_vista_movil)
    else:
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
