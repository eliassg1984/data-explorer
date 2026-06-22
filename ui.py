"""
Panel de Reportes v2.0 - Punto de entrada principal (OPTIMIZADO).
"""

import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px

from utils import buscar_columna, buscar_columna_fecha, resolver_columnas
from data import REPORTES, cargar, secrets_disponibles
from ui import (
    TAM_FUENTE, inject_css, inject_error_overlay,
    renderizar_aggrid_desktop, renderizar_aggrid_movil,
    renderizar_graficos, inject_element_inspector
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

# Overlay de errores JS en pantalla (diagnóstico sin abrir la consola/F12).
inject_error_overlay()

# Inspector de elementos — muestra nombre/key al pasar el cursor (?inspector=1 o Alt+I).
inject_element_inspector()


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

        // ── Navegación a prueba de sandbox ──────────────────────────────
        // El iframe de components.html está en un sandbox SIN
        // 'allow-top-navigation', así que llamar win.location.assign() desde
        // aquí lo BLOQUEA el navegador (ese era el motivo real de que los
        // iconos no cambiaran de reporte). Solución: inyectar un <script> en
        // el documento padre para definir las funciones de navegación EN SU
        // PROPIO realm (no sandboxed); desde los handlers solo las llamamos.
        if (!doc.getElementById('rail-nav-fns')) {{
            var navScript = doc.createElement('script');
            navScript.id = 'rail-nav-fns';
            navScript.textContent =
                "window.__navReporte=function(n){{try{{var u=new URL(window.location.href);u.searchParams.set('reporte',n);u.searchParams.delete('refresh');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Navegacion bloqueada (sandbox?): '+e.message);}}}};" +
                "window.__refreshReporte=function(){{try{{var u=new URL(window.location.href);u.searchParams.set('refresh','1');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Refresco bloqueado (sandbox?): '+e.message);}}}};";
            doc.head.appendChild(navScript);
        }}

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
                win.__refreshReporte();
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
                        // Navega vía la función del realm padre (esquiva el
                        // sandbox). El nombre del reporte se pasa tal cual:
                        // URLSearchParams ya lo codifica una vez (sin esto, el
                        // doble-encode rompía los nombres con espacios).
                        win.__navReporte(n);
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

        // ── Navegación a prueba de sandbox (mismo motivo que en el rail) ──
        if (!doc.getElementById('rail-nav-fns')) {{
            var navScript = doc.createElement('script');
            navScript.id = 'rail-nav-fns';
            navScript.textContent =
                "window.__navReporte=function(n){{try{{var u=new URL(window.location.href);u.searchParams.set('reporte',n);u.searchParams.delete('refresh');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Navegacion bloqueada (sandbox?): '+e.message);}}}};" +
                "window.__refreshReporte=function(){{try{{var u=new URL(window.location.href);u.searchParams.set('refresh','1');window.location.assign(u.toString());}}catch(e){{if(window.__logErr)window.__logErr('Refresco bloqueado (sandbox?): '+e.message);}}}};";
            doc.head.appendChild(navScript);
        }}

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
                background: transparent;       /* franja invisible: sin fondo */
                border-bottom: none;           /* y sin borde inferior */
                display: flex;
                align-items: center;
                gap: 14px;
                padding: 0 18px;
                z-index: 999998;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                pointer-events: none;          /* deja pasar el clic al contenido */
            }}
            #top-bar .tb-titulo {{
                font-weight: 600;
                font-size: 14px;
                color: #1e3a5f;
                white-space: nowrap;
                transform: translateY(8px);    /* el título, un poco más abajo */
            }}
            /* Separador oculto: sin la franja no tiene sentido que flote */
            #top-bar .tb-sep {{
                display: none;
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
                pointer-events: auto;   /* el botón sí recibe clics */
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
                return;
            }}
            var bar = doc.createElement('div');
            bar.id = 'top-bar';

            // El título superior se eliminó a pedido. La franja se conserva
            // únicamente para alojar el botón de actualizar (importante en
            // móvil, donde el rail de iconos está oculto).
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
                win.__refreshReporte();
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
reporte = params.get("reporte", None)
# Validación: si el reporte de la URL no existe en REPORTES (por ejemplo, una
# URL antigua mal codificada o un nombre escrito a mano), usar el primero por
# defecto en lugar de provocar un KeyError más abajo en `REPORTES[reporte]`.
if not reporte or reporte not in REPORTES:
    reporte = list(REPORTES.keys())[0]   # primer reporte como defecto

if params.get("refresh"):
    st.cache_data.clear()
    # Quitar SOLO el flag de refresco y conservar el reporte seleccionado.
    # (Antes se hacía st.query_params.clear(), que borraba también `reporte`
    #  y siempre devolvía al usuario al primer reporte tras refrescar.)
    if "refresh" in st.query_params:
        del st.query_params["refresh"]
    st.rerun()

# Inyectar el rail de iconos (igual que antes) + la franja superior delgada
inject_icon_rail(REPORTES, reporte)
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
# SELECTOR DE COLUMNAS (MODIFICADO PARA MOSTRAR 4 COLUMNAS AL INICIO)
# ===========================================================================
usa_vista_movil = st.session_state.forzar_movil
tiene_config_movil = "columnas_movil" in cfg

if not usa_vista_movil:
    # ── ENVIAMOS TODAS LAS COLUMNAS, PERO MOSTRAMOS SOLO 4 EN EL INVENTARIO ──
    cols_mostrar = todas_cols  # Envía TODAS las columnas al backend de AgGrid
    
    if reporte == "Inventario Valorizado":
        # Columnas que arrancan visibles. Usamos buscar_columna (coincidencia
        # flexible: ignora mayúsculas, espacios y acentos) en lugar de comparar
        # el texto EXACTO. Antes, si el nombre real difería aunque fuera en una
        # mayúscula (p. ej. "Stock al Dia" vs "Stock al dia"), la coincidencia
        # exacta fallaba, cols_visibles quedaba vacío y la tabla salía en blanco.
        columnas_iniciales = ["Nombre Producto", "Stock al Dia", "Nombre Area", "Valorizado total"]
        cols_visibles = []
        for _c in columnas_iniciales:
            _real = buscar_columna(df_f, _c)
            if _real and _real not in cols_visibles:
                cols_visibles.append(_real)
    else:
        # Para el resto de reportes, usa la lógica automática de columnas sugeridas
        cols_visibles = sugeridas
else:
    # (Esto solo aplica para móvil)
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
# CONTENIDO PRINCIPAL — segmented_control para Inventario Valorizado,
#                       tabs clásicas para el resto de reportes
# ===========================================================================
font_px = TAM_FUENTE.get(st.session_state.tabla_tam, 14)


def _render_tabla():
    """Renderiza la tabla AgGrid (desktop o móvil) con los parámetros actuales."""
    if usa_vista_movil and tiene_config_movil:
        st.caption("📱 Vista móvil • Desliza para más columnas • Mantén presionado para menú")
        columnas_fijas = cfg.get("columnas_fijas_movil", 2)
        df_grid_movil = df_f[cols_mostrar]
        renderizar_aggrid_movil(df_grid_movil, columnas_fijas, reporte, font_px)
    else:
        cols_finales = list(cols_mostrar)
        if grupos_sel:
            for c in grupos_sel:
                if c not in cols_finales:
                    cols_finales.append(c)
        df_grid = df_f[cols_finales]
        renderizar_aggrid_desktop(
            df_grid, grupos_sel, cols_mostrar, reporte, font_px,
            cols_visibles=cols_visibles,
        )


if reporte == "Inventario Valorizado":
    # ── Título grande alineado con la tabla (elemento Streamlit nativo,
    #    visible con F12 y perfectamente alineado con el contenido) ──
    st.markdown(
        '<p style="font-size:22px;font-weight:700;color:#1e293b;'
        'margin:0 0 0.6rem 0;line-height:1.2;">Inventario Valorizado</p>',
        unsafe_allow_html=True,
    )
    # ── Botones segmentados (acento rojo via config.toml primaryColor) ──
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

else:
    # ── Tabs clásicas para todos los demás reportes ──
    tab_tabla, tab_graficos = st.tabs(["📋 Tabla", "📊 Gráficos"])

    with tab_tabla:
        _render_tabla()

    with tab_graficos:
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
