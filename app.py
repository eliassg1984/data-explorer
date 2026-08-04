"""
Panel de Reportes v2.0 - Punto de entrada principal (OPTIMIZADO).
"""

import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from utils import buscar_columna, buscar_columna_fecha, resolver_columnas
from data import (
    REPORTES, cargar, cargar_rango, rango_fechas, secrets_disponibles,
    hay_dato_nuevo, fecha_ultima_actualizacion,
)
from estilos import TAM_FUENTE, inject_css
from estado_rango import (
    clave_rango, asegurar_rango, debug_estado_rango,
    atajos_rango, aplicar_atajo,
)
from inyecciones import inject_error_overlay, inject_element_inspector, inject_footer_actualizacion, inject_calendario_es, inject_fullscreen_app
from tablas import renderizar_aggrid_desktop, renderizar_aggrid_movil, renderizar_aggrid_compras
from graficos import renderizar_graficos_reporte, render_vista_pills
from asistente import inject_asistente
from navegacion import inject_navegacion
from perf import perf                                                       # ⚡ PERF

ZONA_PERU = ZoneInfo("America/Lima")  # UTC-5 fijo, sin horario de verano

_MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _fmt_rango_es(ini, fin):
    if ini == fin:
        return f"{ini.day} {_MESES_ES[ini.month - 1]} {ini.year}"
    return (f"{ini.day} {_MESES_ES[ini.month - 1]} {ini.year} - "
            f"{fin.day} {_MESES_ES[fin.month - 1]} {fin.year}")


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

inject_css()
inject_error_overlay()
inject_element_inspector()
inject_calendario_es()
inject_fullscreen_app()   # botón ⛶ pantalla completa (móvil)

perf.start()                                                                # ⚡ PERF


# ===========================================================================
# VIGILANCIA DE REFRESCO (fragmento)
# ===========================================================================

@st.fragment(run_every=4)
def _vigilar_refresco(archivo, clave_estado):
    """Revisa cada 4s si R2 ya tiene el parquet actualizado. Mientras
    espera, muestra un aviso visible (no un toast que desaparece)."""
    info = st.session_state.get(clave_estado)
    if not info:
        return  # ya se resolvió en otra ejecución

    transcurrido = (datetime.datetime.now(ZONA_PERU) - info["inicio"]).total_seconds()

    if hay_dato_nuevo(archivo, info["baseline"]):
        cargar.clear(archivo)
        st.session_state.pop(clave_estado, None)
        st.toast(f"✅ «{info['reporte']}» actualizado.", icon="✅")
        st.rerun(scope="app")
        return

    if transcurrido > 120:
        with st.container(key="aviso_refresco"):
            st.warning(
                f"⏳ La actualización de «{info['reporte']}» está tardando más de lo "
                "usual. Los datos mostrados podrían no ser los más recientes.",
                icon="⚠️",
            )
        return

    # Periodo de gracia: si el job termina antes de este umbral, el usuario
    # nunca ve el aviso — solo un salto directo de tabla vieja a tabla nueva.
    GRACIA_SEGUNDOS = 8
    if transcurrido < GRACIA_SEGUNDOS:
        return

    with st.container(key="aviso_refresco"):
        st.info(
            f"🔄 Actualizando datos de «{info['reporte']}»... (puede tardar unos segundos)",
            icon="🔄",
        )


# ===========================================================================
# LEER REPORTE DESDE LA URL Y APLICAR REFRESCO
# ===========================================================================

params = st.query_params
reporte = params.get("reporte", None)

if st.session_state.get("_nav_reporte"):
    reporte = st.session_state.pop("_nav_reporte")
    st.query_params["reporte"] = reporte

if not reporte or reporte not in REPORTES:
    reporte = list(REPORTES.keys())[0]

# ── REFRESCO GLOBAL POR URL (?refresh=1) ──
if params.get("refresh"):
    st.cache_data.clear()
    if "refresh" in st.query_params:
        del st.query_params["refresh"]
    st.rerun()

inject_navegacion(REPORTES, reporte, mostrar_inspector=bool(st.query_params.get("debug")))

cfg = REPORTES[reporte]

# Marker de reporte activo en el DOM. Div vacio con la clase que Streamlit
# usaria para st.container(key="..."), inyectado via st.markdown para no
# ocupar altura. El CSS lo usa con :has() para scopear reglas a un reporte
# especifico. Nace porque muchas keys "de compras" son en realidad de
# componentes compartidos (compras_tabs_row del rail, chips_ajuste_tabla,
# fila_ajuste_top): scopear con :has(.st-key-compras_tabs_row) se pensaba
# como "solo Compras" pero tambien matcheaba en Ajuste y otros reportes que
# usan el mismo rail. Ver arquitectura.md regla #16.
_reporte_slug = reporte.lower().replace(" ", "_")
st.markdown(
    f'<div class="st-key-app_reporte_{_reporte_slug}" style="display:none"></div>',
    unsafe_allow_html=True,
)

# ── VIGILAR REFRESCO PENDIENTE ──
# Se llama SIEMPRE (aunque no haya nada pendiente todavía): así el fragment
# queda montado desde el principio, escuchando solo con su propio run_every=4.
# Motivo: el botón de refresco vive en SU PROPIO fragment (navegacion.py), así
# que su clic ya NO dispara un rerun completo de app.py. Si esta llamada
# siguiera condicionada a "ya hay algo pendiente", este bloque nunca volvería
# a evaluarse tras el clic y _vigilar_refresco jamás se enteraría del refresco
# solicitado. _vigilar_refresco ya hace `if not info: return` internamente,
# así que llamarlo sin condición es seguro y no hace nada hasta que sí hay
# un refresco pendiente para ese archivo.
_archivo_actual = cfg.get("archivo")
if _archivo_actual:
    _vigilar_refresco(_archivo_actual, f"_refresco_pendiente_{_archivo_actual}")


# ===========================================================================
# LIMPIAR ESTADO AL CAMBIAR DE REPORTE
# ===========================================================================
if st.session_state.get("_reporte_anterior") != reporte:
    st.session_state["_reporte_anterior"] = reporte
    st.session_state.pop("ajuste_rango_aplicado", None)


# ===========================================================================
# AVISO DE MODO DEMO + PANEL DE DIAGNÓSTICO (?debug=1)
# ===========================================================================
modo_demo = not secrets_disponibles()
if modo_demo:
    st.caption("🧪 MODO DEMO — datos de ejemplo (no hay conexión a R2). "
               "Configura los secrets R2_* para usar datos reales.")

if st.query_params.get("diagnostico"):
    import sys
    from importlib.metadata import version, PackageNotFoundError

    def _ver(paquete):
        try:
            return version(paquete)
        except PackageNotFoundError:
            return "?"

    with st.expander("🔧 Diagnóstico de entorno", expanded=False):
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

    perf.render_panel(expanded=False)                                       # ⚡ PERF
    perf.render_browser_panel(expanded=False)                               # ⚡ PERF browser


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
    perf.end()                                                              # ⚡ PERF
    st.stop()


# ===========================================================================
# CARGAR DATOS
# ===========================================================================
with perf.phase("cargar()"):                                                # ⚡ PERF
    _col_rango = cfg.get("carga_por_rango")
    if _col_rango:
        # El date-picker de la franja (más abajo) usa esta MISMA clave, así que
        # al cambiar el rango Streamlit lo re-commitea antes del siguiente
        # rerun y aquí se recarga desde R2 con el nuevo rango. Default liviano:
        # 01-del-mes → hoy (no baja las 100k+ filas salvo que el usuario amplíe).
        _hoy_c = datetime.date.today()
        # Dueño único del estado (ver estado_rango.py). Aquí aún no conocemos
        # los bounds del parquet (se calculan tras cargar), así que solo
        # SEMBRAMOS el default; el recorte a bounds ocurre más abajo.
        _k_rango = clave_rango(reporte, usa_carga_rango=True, es_ajuste=False)
        _k_rango_ok = f"rango_carga_ok_{reporte}"   # último rango 2-tupla válido
        asegurar_rango(_k_rango, default=(_hoy_c.replace(day=1), _hoy_c))
        _rc = st.session_state.get(_k_rango)
        if isinstance(_rc, (tuple, list)) and len(_rc) == 2 and all(_rc):
            _r_ini, _r_fin = _rc
            st.session_state[_k_rango_ok] = (_r_ini, _r_fin)
        else:
            # Selección de rango a medias (1 fecha): reusar el último válido,
            # sin tocar la clave del widget (evita resetear el picker).
            _r_ini, _r_fin = st.session_state.get(
                _k_rango_ok, (_hoy_c.replace(day=1), _hoy_c))
        df = cargar_rango(cfg["archivo"], _col_rango, _r_ini, _r_fin)
    else:
        df = cargar(cfg["archivo"])
if df is None or df.empty:
    # Ya no es un estado "pegajoso": el fallo de lectura no se cachea (ver
    # data.py::cargar), así que reintentar realmente vuelve a golpear R2.
    st.warning("No se pudieron cargar los datos o el archivo está vacío. "
               "Reintentá en unos segundos (F5).")
    perf.end()                                                              # ⚡ PERF
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
with perf.phase("df.copy() + to_datetime"):                                 # ⚡ PERF
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
    cols_agrupar = [c for c in [
        buscar_columna(df_f, "area", "área"),
        buscar_columna(df_f, "familia"),
        buscar_columna(df_f, "subfamilia", "sub familia"),
    ] if c]


# ===========================================================================
# CONTROLES DE FILTRO — st.popover
# ===========================================================================

fecha_min_full = fecha_max_full = None
if col_fecha and df_f[col_fecha].notna().any():
    fecha_min_full = df_f[col_fecha].min().date()
    fecha_max_full = df_f[col_fecha].max().date()

# Reportes con carga por rango (Ventas): los límites del date-picker deben ser
# el rango COMPLETO del parquet (no solo lo ya cargado), para poder ampliar a
# cualquier fecha histórica. Se obtiene con un MIN/MAX barato en DuckDB.
_usa_carga_rango = bool(cfg.get("carga_por_rango"))
if _usa_carga_rango and col_fecha:
    _rf = rango_fechas(cfg["archivo"], cfg["carga_por_rango"])
    if _rf:
        fecha_min_full, fecha_max_full = _rf
        # Ya conocemos los bounds reales del parquet: el DUEÑO ÚNICO recorta
        # el rango guardado a [min, max] (el default 01-mes→hoy puede exceder
        # el máximo real si la data no llega hasta hoy → date_input fallaría).
        asegurar_rango(
            clave_rango(reporte, usa_carga_rango=True, es_ajuste=False),
            default=(fecha_min_full, fecha_max_full),
            bounds=(fecha_min_full, fecha_max_full),
            reporte=reporte, usa_carga_rango=True,
        )

_hoy = datetime.date.today()
fecha_ini_default = _hoy.replace(day=1)   # 01 del mes actual
fecha_fin_default = _hoy                  # hoy

es_ajuste = (reporte == "Ajuste de Inventario")

# Vista por defecto al abrir un reporte: "Gráficos" para todos, salvo los
# reportes de consulta (recetas), que arrancan en "Tabla".
REPORTES_INICIO_TABLA = ("Receta Base", "Receta Venta")
_vista_default = "Tabla" if reporte in REPORTES_INICIO_TABLA else "Gráficos"

controles = []
# (los filtros categóricos ahora son chips en la franja; la fecha, la pill)
if col_busc:
    controles.append(("busc", col_busc))
if cols_agrupar:
    controles.append(("grp", None))

grupos_sel = []


@st.cache_data
def get_opciones_filtro(_df, _col):
    """Retorna las opciones únicas de una columna, ordenadas."""
    return sorted(_df[_col].dropna().unique().tolist(), key=lambda x: str(x))


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

# ── TÍTULO + WIDGET DE FECHA EN LA FRANJA SUPERIOR (solo Ajuste de Inventario) ──
perf.start_phase("Ajuste top row")                                          # ⚡ PERF
# DISEÑO UNIFICADO: la franja fija (título + fecha + pestañas) aplica a
# TODOS los reportes. El rango de fecha vive en una clave por reporte
# Clave del rango de la franja — vía DUEÑO ÚNICO (ver estado_rango.py).
_k_rango_franja = clave_rango(reporte, _usa_carga_rango, es_ajuste)
_franja_con_fecha = bool(col_fecha) and fecha_min_full is not None
if True:
    # INVARIANTE: sembrar el default Y recortar a bounds AQUÍ, justo antes de
    # dibujar el widget en este mismo render. Nunca clampear después del
    # widget (se vería un render tarde → desync overlay/calendario/datos).
    # Para carga_por_rango es idempotente con el recorte de arriba; para el
    # resto de reportes ésta es su única inicialización/recorte.
    if _franja_con_fecha:
        asegurar_rango(
            _k_rango_franja,
            default=(fecha_ini_default, fecha_fin_default),
            bounds=(fecha_min_full, fecha_max_full),
            reporte=reporte, usa_carga_rango=_usa_carga_rango,
        )

    # Evitar NameError antes de la franja superior
    _fecha_actualizacion = None

    # Franja superior: título (izquierda) + fecha (derecha, extremo opuesto).
    _fila_top = st.container(key="fila_ajuste_top")
    with _fila_top:
        col_titulo, col_fecha_top = st.columns(
            [3, 1.15], vertical_alignment="center",
        )
        with col_titulo:
            # Título oculto por pedido: en su lugar van las pestañas
            # Gráficos/Tabla (misma key vista_seg_<reporte> → mismo estado).
            # Requerimientos no las tiene. Compras, Ajuste, Ventas e
            # Inventario Valorizado usan el RAIL derecho (la "Tabla" es un
            # item del rail), así que tampoco dibujan estas pills.
            if reporte not in ("Requerimientos", "Compras",
                               "Ajuste de Inventario", "Ventas",
                               "Inventario Valorizado"):
                render_vista_pills(reporte, default=_vista_default)
        with col_fecha_top:
            if _franja_con_fecha:
                try:
                    _fecha_actualizacion = fecha_ultima_actualizacion(
                        cfg.get("archivo")
                    )
                except Exception:
                    _fecha_actualizacion = None

                if isinstance(_fecha_actualizacion, datetime.datetime):
                    if _fecha_actualizacion.tzinfo is not None:
                        _fecha_actualizacion = _fecha_actualizacion.astimezone(ZONA_PERU)
                # El estado ya quedó sembrado y recortado por asegurar_rango()
                # arriba (una sola vez, antes del widget). Aquí solo se LEE.
                # El texto del rango es el TRIGGER de un panel (Opción B):
                # atajos rápidos a la izquierda + calendario manual a la
                # derecha. El date_input, los atajos y el label leen/escriben
                # la MISMA clave → no pueden desincronizarse.
                _rango_actual = st.session_state.get(_k_rango_franja)
                if (isinstance(_rango_actual, (tuple, list))
                        and len(_rango_actual) == 2 and all(_rango_actual)):
                    _label_fecha = _fmt_rango_es(_rango_actual[0], _rango_actual[1])
                else:
                    _label_fecha = "Seleccionar rango"

                # Atajos válidos para la data actual (los calcula el dueño único).
                _atajos = atajos_rango(_hoy, (fecha_min_full, fecha_max_full))

                with st.container(key="fecha_ajuste_pill"):
                    with st.popover(_label_fecha, use_container_width=False,
                                    icon=":material/calendar_month:"):
                        # Contenedor keyed → permite scopear el ancho del panel
                        # por CSS aunque el popover se renderice en un portal.
                        with st.container(key="fecha_panel"):
                            _c_atajos, _c_cal = st.columns([1, 1.5])
                            with _c_atajos:
                                st.caption("Atajos")
                                for _ca, _et, _rg in _atajos:
                                    st.button(
                                        _et, use_container_width=True,
                                        key=f"atajo_{reporte}_{_ca}".replace(" ", "_"),
                                        on_click=aplicar_atajo,
                                        args=(_k_rango_franja, _rg, reporte,
                                              _usa_carga_rango),
                                    )
                            with _c_cal:
                                st.caption("Rango manual")
                                st.date_input(
                                    "Rango a Evaluar",
                                    min_value=fecha_min_full,
                                    max_value=fecha_max_full,
                                    format="DD/MM/YYYY",
                                    key=_k_rango_franja,
                                    label_visibility="collapsed",
                                )

        # Las pestañas Gráficos/Tabla se movieron FUERA de la franja, a una
        # banda pegada al borde superior del canvas (ver más abajo, justo
        # antes de _render_contenido). Así la franja queda de un solo nivel.

    # ── Texto de actualización FUERA de la franja sticky ──
    # Así su position:fixed vive en el contexto raíz y no es tapado
    # por .stApp::after (fila_ajuste_top crea un stacking context propio
    # por su sticky + z-index).
    if isinstance(_fecha_actualizacion, datetime.datetime):
        inject_footer_actualizacion(
            "Última actualización: "
            + _fecha_actualizacion.strftime("%d/%m/%Y · %H:%M")
        )

    # Aplicar el rango al DataFrame (usa el valor ya guardado en session_state).
    # En carga_por_rango el widget puede dejar una tupla de 1 elemento mientras
    # el usuario elige la 2ª fecha: en ese caso no se filtra (se muestra lo ya
    # cargado) hasta que el rango quede completo.
    if _franja_con_fecha:
        _rango_apl = st.session_state.get(_k_rango_franja)
        if isinstance(_rango_apl, (tuple, list)) and len(_rango_apl) == 2 and all(_rango_apl):
            _ini_apl, _fin_apl = _rango_apl
            df_f = df_f[
                (df_f[col_fecha].dt.date >= _ini_apl) &
                (df_f[col_fecha].dt.date <= _fin_apl)
            ]
perf.end_phase("Ajuste top row")                                            # ⚡ PERF

# (El popover de filtros fue retirado: los filtros viven en la franja.)


# ===========================================================================
# AVISOS DE COLUMNAS FALTANTES
# ===========================================================================
if st.query_params.get("debug"):
    if faltantes_aviso:
        st.caption("⚠️ No se encontraron: " + ", ".join(faltantes_aviso))
    if "columnas" in cfg and faltan_cols:
        st.caption("⚠️ Columnas no encontradas: " + ", ".join(faltan_cols))
    # Verdad del estado del rango (contrastar contra overlay y calendario si
    # se sospecha un desync). Aparece solo con ?diagnostico=1 en la URL para
    # que la app se vea como produccion mientras se usa el inspector (?debug=1).
    if st.query_params.get("diagnostico"):
        debug_estado_rango()


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
    elif reporte == "Ajuste de Inventario":
        columnas_iniciales = ["Producto", "Precio Promedio", "Stock al Cierre",
                              "Stock Declarado", "Ajuste", "Ajuste Valorizado"]
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
# VERIFICACIÓN DE DATOS VACÍOS (sin _esperando_extraccion)
# ===========================================================================
if df_f.empty:
    st.warning("Ningún registro coincide con los filtros.")
    perf.end()                                                              # ⚡ PERF
    st.stop()


# ===========================================================================
# CONTENIDO PRINCIPAL
# ===========================================================================
font_px = TAM_FUENTE.get(st.session_state.tabla_tam, 14)


def _aviso_rapido_aggrid(df_data):
    """Si hay columnas duplicadas, muestra un aviso corto."""
    duplicadas = df_data.columns[df_data.columns.duplicated()].unique().tolist()
    if duplicadas:
        nombres = ", ".join(f"«{d}»" for d in duplicadas)
        st.warning(
            f"⚠️ Columnas duplicadas: {nombres}. "
            "Esto puede dejar la tabla en blanco."
        )


def _render_requerimientos(df_data, col_fecha_ref, grupos_sel, cols_mostrar, font_px, cfg):
    """Renderiza el reporte de Requerimientos con tabla dinámica."""
    df_piv = df_data.copy()

    for _c in df_piv.columns:
        _n = str(_c).lower()
        if "fecha" in _n or "date" in _n or pd.api.types.is_datetime64_any_dtype(df_piv[_c]):
            df_piv[_c] = pd.to_datetime(df_piv[_c], errors="coerce")

    _col_freg = buscar_columna(df_piv, "Fecha Registro", "fecha registro") or col_fecha_ref

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


    # (El filtro de fecha propio fue retirado: la pill de la franja ya
    #  filtra df_data por rango antes de llegar aquí.)
    tiene_config_movil = "columnas_movil" in cfg
    if usa_vista_movil and tiene_config_movil:
        st.caption("📱 Vista móvil")
        renderizar_aggrid_movil(
            df_piv[cols_mostrar], cfg.get("columnas_fijas_movil", 2), "Requerimientos", font_px,
        )
    else:
        _aviso_rapido_aggrid(df_piv)
        renderizar_aggrid_desktop(
            df_piv,
            grupos_sel,
            list(df_piv.columns),
            "Requerimientos",
            font_px,
            cols_visibles=None,
        )


def _es_moneda(nombre):
    n = str(nombre).lower()
    return any(k in n for k in ("importe", "total", "monto", "precio", "costo", "unitario"))

def _es_cantidad(nombre):
    n = str(nombre).lower()
    return any(k in n for k in ("cantidad", "unidades", "qty", "stock"))


# ===========================================================================
# CHIPS DE FILTRO EXTERNOS — Tabla de Ajuste de Inventario
# ===========================================================================
def _chip_categorico(df_in, col, key, etiqueta):
    """Chip-popover multiselección para una columna categórica.
    Devuelve (df_filtrado, seleccion)."""
    if not col or col not in df_in.columns:
        return df_in, []
    valores = sorted(df_in[col].dropna().astype(str).unique().tolist())
    if not valores:
        return df_in, []
    _n = len(st.session_state.get(key) or [])
    _lbl = f":material/filter_alt: {etiqueta} :violet-badge[{_n}]" if _n else f":material/filter_alt: {etiqueta}"
    _estado = "on" if _n else "off"
    with st.container(key=f"chipwrap_{key}_{_estado}"):
        with st.popover(_lbl, use_container_width=True):
            sel = st.pills(
                etiqueta, valores, selection_mode="multi",
                key=key, label_visibility="collapsed",
            ) or []
    if sel:
        df_in = df_in[df_in[col].astype(str).isin(sel)]
    return df_in, sel


def _chip_numerico(df_in, col, key, etiqueta, opciones=None):
    """Chip-popover single-select para una columna numérica.
    Opciones: Todos / Con ajuste (≠0) / Faltantes (<0) / Sobrantes (>0)
    / Top 10 / Top 20. Top N = filas de mayor magnitud (|valor|)."""
    if not col or col not in df_in.columns:
        return df_in
    if opciones is None:
        opciones = ["Todos", "Faltantes", "Sobrantes", "Top 10", "Top 20"]
    _prev = st.session_state.get(key) or "Todos"
    _lbl = f":material/filter_alt: {etiqueta}" if _prev == "Todos" else f":material/filter_alt: {etiqueta} · {_prev}"
    _estado = "off" if _prev == "Todos" else "on"
    with st.container(key=f"chipwrap_{key}_{_estado}"):
        with st.popover(_lbl, use_container_width=True):
            sel = st.pills(
                etiqueta, opciones, default="Todos",
                key=key, label_visibility="collapsed",
            ) or "Todos"
    serie = pd.to_numeric(df_in[col], errors="coerce")
    if sel == "Con ajuste":
        return df_in[serie.fillna(0) != 0]
    if sel == "Faltantes":
        return df_in[serie < 0]
    if sel == "Sobrantes":
        return df_in[serie > 0]
    if sel in ("Top 10", "Top 20"):
        n = 10 if sel == "Top 10" else 20
        idx = serie.abs().sort_values(ascending=False).head(n).index
        return df_in.loc[idx]
    return df_in


def _filtros_chips_ajuste_tabla(df_in):
    """Fila de chips-cápsula ARRIBA de la tabla de Ajuste. Filtra df_in en
    Python (Área, Familia, Ajuste, Ajuste Valorizado) y devuelve el df."""
    col_area  = buscar_columna(df_in, "Nombre Area", "Area", "AREA")
    col_fam   = buscar_columna(df_in, "Nombre Familia", "Familia", "FAMILIA")
    col_aj    = buscar_columna(df_in, "Ajuste", "AJUSTE", "Cantidad Ajuste")
    col_ajval = buscar_columna(df_in, "Ajuste Valorizado", "AJUSTE VALORIZADO")

    with st.container(key="chips_ajuste_tabla"):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
        with c1:
            df_in, _ = _chip_categorico(df_in, col_area,
                                        "ajuste_tabla_filtro_area", "Área")
        with c2:
            df_in, _ = _chip_categorico(df_in, col_fam,
                                        "ajuste_tabla_filtro_familia", "Familia")
        with c3:
            df_in = _chip_numerico(
                df_in, col_aj,
                "ajuste_tabla_filtro_ajuste", "Ajuste",
                opciones=["Todos", "Con ajuste", "Faltantes",
                          "Sobrantes", "Top 10", "Top 20"],
            )
        with c4:
            df_in = _chip_numerico(df_in, col_ajval,
                                   "ajuste_tabla_filtro_ajusteval", "Ajuste Valor.")
    return df_in


def _filtros_chips_franja(df_in):
    """Chips de filtro de la franja para el reporte activo: Ajuste usa sus
    4 chips propios; el resto muestra sus filtros categóricos (cfg) como
    cápsulas equivalentes."""
    if es_ajuste:
        return _filtros_chips_ajuste_tabla(df_in)
    if not cat_cols:
        return df_in
    with st.container(key="chips_ajuste_tabla"):
        _cols = st.columns([1] * len(cat_cols))
        for _cc, _col in zip(_cols, cat_cols):
            with _cc:
                df_in, _ = _chip_categorico(
                    df_in, _col,
                    f"chip_franja_{reporte.replace(' ', '_')}_{_col}", _col)
    return df_in


# ===========================================================================
# RENDERIZADO DE TABLA (con df opcional para los chips)
# ===========================================================================
def _render_tabla(df_data=None):
    """Renderiza la tabla AgGrid (desktop o móvil)."""
    _df = df_f if df_data is None else df_data
    if usa_vista_movil and tiene_config_movil:
        st.caption("📱 Vista móvil • Desliza para más columnas • Mantén presionado para menú")
        columnas_fijas = cfg.get("columnas_fijas_movil", 2)
        renderizar_aggrid_movil(_df[cols_mostrar], columnas_fijas, reporte, font_px)
    else:
        _aviso_rapido_aggrid(_df[cols_mostrar])
        cols_finales = list(cols_mostrar)
        if grupos_sel:
            for c in grupos_sel:
                if c not in cols_finales:
                    cols_finales.append(c)
        renderizar_aggrid_desktop(
            _df[cols_finales], grupos_sel, cols_mostrar, reporte, font_px,
            cols_visibles=cols_visibles,
        )


def _render_kpis_salidas(df_data):
    """Renderiza las métricas KPI para el reporte de Salidas."""
    cols_imp = [c for c in df_data.columns
                if pd.api.types.is_numeric_dtype(df_data[c]) and _es_moneda(c)]
    cols_cnt = [c for c in df_data.columns
                if pd.api.types.is_numeric_dtype(df_data[c]) and _es_cantidad(c)]
    n_kpi = min(4, 1 + len(cols_imp[:2]) + len(cols_cnt[:1]))
    kpis = st.columns(n_kpi)
    kpis[0].metric("📄 Registros", f"{len(df_data):,}")
    ki = 1
    for c in cols_imp[:2]:
        if ki >= n_kpi:
            break
        kpis[ki].metric(f"💰 {c}", f"S/ {df_data[c].sum():,.2f}")
        ki += 1
    for c in cols_cnt[:1]:
        if ki >= n_kpi:
            break
        kpis[ki].metric(f"📦 {c}", f"{int(df_data[c].sum()):,}")
        ki += 1


# ===========================================================================
# SELECTOR DE VISTA (Tabla / Gráficos) — tabs subrayados (underline)
# ===========================================================================
def _selector_vista():
    """Muestra un radio horizontal estilizado como tabs subrayados y devuelve
    la opción elegida ('Tabla' o 'Gráficos'). El CSS que lo convierte en tabs
    vive en estilos.py (bloque '.st-key-vistatabs_...')."""
    _opciones = {"Gráficos": ":material/monitoring: Gráficos",
             "Tabla": ":material/table_rows: Tabla"}
    with st.container(key=f"vistatabs_{reporte}"):
        vista = st.pills(
            "Vista",
            options=list(_opciones.keys()),
            format_func=lambda o: _opciones[o],
            default="Gráficos",
            label_visibility="collapsed",
            key=f"vista_seg_{reporte}",
        )
    return vista or "Gráficos"


# ===========================================================================
# AJUSTE DE INVENTARIO — auto-detección de ámbito Del periodo / Histórico
# ===========================================================================
# Regla: si el rango aplicado cae dentro del MISMO mes calendario, el ámbito
# por defecto es «Del periodo»; si cruza meses, «Histórico». La detección se
# calcula ANTES de renderizar el segmented para que el widget se dibuje con
# el valor correcto ya en session_state. El usuario puede sobreescribirlo
# manualmente después; solo se fuerza cuando cambia el rango entre reruns.
#
# El ámbito lo LEE `graficos.py` desde `st.session_state["ajuste_graf_ambito"]`,
# nunca lo escribe. Fuente única de verdad: este bloque.
def _calcular_ajuste_ambito_auto():
    """Devuelve el ámbito que corresponde al rango actual del popover."""
    _rango = st.session_state.get("ajuste_rango_aplicado")
    if isinstance(_rango, (tuple, list)) and len(_rango) == 2:
        _ini, _fin = _rango
        if _ini.year == _fin.year and _ini.month == _fin.month:
            return "Del periodo"
        return "Histórico"
    return "Del periodo"


# ===========================================================================
# FRAGMENT GENÉRICO — aisla el contenido principal de cada reporte
# ===========================================================================
@st.fragment
def _render_contenido():
    perf.fragment_start("_render_contenido")                                # ⚡ PERF

    # ── COMPRAS ─────────────────────────────────────────────────────────────
    if reporte == "Compras":
        # Compras no usa G/T en la franja: la Tabla es una opción más dentro
        # del selector de tipo de gráfico (ver graficos/compras/). Los chips
        # Familia/Subfamilia viven dentro de compras.py y se aplican por igual
        # a los gráficos y a la Tabla.
        renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df)

    # ── REQUERIMIENTOS ───────────────────────────────────────────────────────
    elif reporte == "Requerimientos":
        _render_requerimientos(df_f, col_fecha, grupos_sel, cols_mostrar, font_px, cfg)

    # ── AJUSTE DE INVENTARIO — layout con rail derecho (como Compras) ───────
    elif reporte == "Ajuste de Inventario":
        # Sin pills Gráficos/Tabla: el rail (dentro de graficos/ajuste.py) es
        # el selector, y "Tabla" es un item más. La tabla la sabe armar app.py
        # (usa cols_mostrar/font_px/etc.), así que se inyecta como callback:
        # el rail decide CUÁNDO mostrarla, app.py CÓMO.
        def _ajuste_tabla_cb():
            df_tabla = _filtros_chips_franja(df_f)
            if df_tabla.empty:
                st.info("Ningún registro coincide con los filtros seleccionados.")
            else:
                _render_tabla(df_tabla)

        renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df,
                                    tabla_cb=_ajuste_tabla_cb)

    # ── VENTAS — layout con rail derecho (como Ajuste) ──────────────────────
    elif reporte == "Ventas":
        # A diferencia de Ajuste, Ventas filtra su propio df ANTES de llegar
        # acá (chips Grupo/Sub Grupo/Canal/Servicio, dentro de
        # graficos/ventas.py) — el callback recibe `d` YA filtrado y solo
        # tiene que dibujar la tabla con él, para no tener un segundo estado
        # de filtros independiente del de los gráficos.
        def _ventas_tabla_cb(d):
            if d.empty:
                st.info("Ningún registro coincide con los filtros seleccionados.")
            else:
                _render_tabla(d)

        renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df,
                                    tabla_cb=_ventas_tabla_cb)

    # ── INVENTARIO VALORIZADO — layout con rail derecho (como Ventas) ───────
    elif reporte == "Inventario Valorizado":
        # Mismo patrón que Ventas: el callback recibe `d`, ya filtrado por
        # los chips propios (Área/Familia, dentro de graficos/inventario.py).
        def _inventario_tabla_cb(d):
            if d.empty:
                st.info("Ningún registro coincide con los filtros seleccionados.")
            else:
                _render_tabla(d)

        renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df,
                                    tabla_cb=_inventario_tabla_cb)

    # ── RESTO DE REPORTES (Salidas, R. Base, R. Venta, …) ────────────────────
    else:
        vista = st.session_state.get(f"vista_seg_{reporte}", _vista_default) or _vista_default
        if vista == "Tabla":
            df_tabla = _filtros_chips_franja(df_f)
            if df_tabla.empty:
                st.info("Ningún registro coincide con los filtros seleccionados.")
            else:
                _render_tabla(df_tabla)
        else:
            renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df)

    perf.fragment_end("_render_contenido")                                  # ⚡ PERF


# ── Pestañas Gráficos/Tabla ──────────────────────────────────────────────────
# Ahora viven DENTRO de la franja superior (col_titulo, más arriba), en el
# hueco que dejó el título. Requerimientos no tiene pestañas; Compras dibuja
# su propio G/T dentro de la fila de pestañas de tipo (graficos.py).

# ── Llamada al fragment ──────────────────────────────────────────────────────
_render_contenido()

# ── Asistente flotante IA (burbuja abajo-derecha) ────────────────────────────
try:
    inject_asistente(reporte_activo=reporte, df_contexto=df_f)
except Exception:
    # Si algo falla en el asistente, la app principal sigue funcionando.
    pass

perf.end()                                                                  # ⚡ PERF
