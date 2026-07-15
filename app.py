"""
Panel de Reportes v2.0 - Punto de entrada principal (OPTIMIZADO).
"""

import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

from utils import buscar_columna, buscar_columna_fecha, resolver_columnas
from data import REPORTES, cargar, cargar_rango, secrets_disponibles, hay_dato_nuevo
from estilos import TAM_FUENTE, inject_css
from inyecciones import inject_error_overlay, inject_element_inspector
from tablas import renderizar_aggrid_desktop, renderizar_aggrid_movil, renderizar_tabla_compras, renderizar_aggrid_compras
from graficos import renderizar_graficos, renderizar_graficos_reporte
from navegacion import inject_navegacion
from perf import perf                                                       # ⚡ PERF

ZONA_PERU = ZoneInfo("America/Lima")  # UTC-5 fijo, sin horario de verano


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

    perf.render_panel(expanded=True)                                        # ⚡ PERF
    perf.render_browser_panel()                                             # ⚡ PERF browser


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
        _hoy_c = datetime.date.today()
        _k_rango = f"rango_carga_{reporte}"
        if _k_rango not in st.session_state:
            st.session_state[_k_rango] = (_hoy_c.replace(day=1), _hoy_c)
        _r_ini, _r_fin = st.session_state[_k_rango]
        df = cargar_rango(cfg["archivo"], _col_rango, _r_ini, _r_fin)
    else:
        df = cargar(cfg["archivo"])
if df is None or df.empty:
    st.warning("No se pudieron cargar los datos o el archivo está vacío.")
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

_hoy = datetime.date.today()
fecha_ini_default = _hoy.replace(day=1)   # 01 del mes actual
fecha_fin_default = _hoy                  # hoy

es_ajuste = (reporte == "Ajuste de Inventario")

controles = []
for cc in cat_cols:
    controles.append(("cat", cc))
if col_busc:
    controles.append(("busc", col_busc))
if cols_agrupar:
    controles.append(("grp", None))
if fecha_min_full is not None and reporte != "Requerimientos" and not es_ajuste:
    controles.append(("fecha", col_fecha))

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
if es_ajuste:
    # Rango aplicado (auto): al primer acceso usa 01-del-mes → hoy.
    # Se inicializa ANTES de dibujar el date_input para que el widget
    # arranque con el valor correcto.
    if col_fecha and fecha_min_full is not None:
        if "ajuste_rango_aplicado" not in st.session_state:
            _ini_def = max(fecha_ini_default, fecha_min_full)
            _fin_def = min(fecha_fin_default, fecha_max_full)
            if _ini_def > _fin_def:
                _ini_def, _fin_def = fecha_min_full, fecha_max_full
            st.session_state["ajuste_rango_aplicado"] = (_ini_def, _fin_def)

    # Franja superior: título (izquierda) + fecha (derecha, extremo opuesto).
    _fila_top = st.container(key="fila_ajuste_top")
    with _fila_top:
        col_titulo, col_fecha_top = st.columns(
            [3, 1.15], vertical_alignment="center",
        )
        with col_titulo:
            st.markdown(
                f'<div class="chip-titulo-reporte">{reporte}</div>',
                unsafe_allow_html=True,
            )
        with col_fecha_top:
            if col_fecha and fecha_min_full is not None:
                with st.container(key="fecha_ajuste_pill"):
                    _ini_apl, _fin_apl = st.session_state["ajuste_rango_aplicado"]
                    rango_aj = st.date_input(
                        "Rango a Evaluar",
                        value=(_ini_apl, _fin_apl),
                        min_value=fecha_min_full,
                        max_value=fecha_max_full,
                        format="DD/MM/YYYY",
                        key="fch_ajuste_inline",
                        label_visibility="collapsed",
                    )
                # Cambio de rango → rerun completo para refiltrar df_f
                if (isinstance(rango_aj, (tuple, list)) and len(rango_aj) == 2
                        and tuple(rango_aj) != st.session_state["ajuste_rango_aplicado"]):
                    st.session_state["ajuste_rango_aplicado"] = tuple(rango_aj)
                    st.rerun(scope="app")

    # Aplicar el rango al DataFrame (usa el valor ya guardado en session_state)
    if col_fecha and fecha_min_full is not None:
        _ini_apl, _fin_apl = st.session_state["ajuste_rango_aplicado"]
        df_f = df_f[
            (df_f[col_fecha].dt.date >= _ini_apl) &
            (df_f[col_fecha].dt.date <= _fin_apl)
        ]
perf.end_phase("Ajuste top row")                                            # ⚡ PERF

# ── POPOVER (solo se muestra si hay controles que mostrar) ──
perf.start_phase("Popover + filtros")                                       # ⚡ PERF
if controles:
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

        if reporte not in ("Compras", "Salidas", "Ajuste de Inventario"):
            st.divider()
            st.session_state.tabla_tam = st.select_slider(
            "🔠 Tamaño de letra",
            options=list(TAM_FUENTE.keys()),
            value=st.session_state.tabla_tam,
            help="Ajusta el tamaño de fuente de la tabla",
        )
perf.end_phase("Popover + filtros")                                         # ⚡ PERF


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
    st.markdown(
        '<p style="font-size:22px;font-weight:700;color:#18181d;'
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
    _lbl = f"{etiqueta} · {_n}" if _n else etiqueta
    with st.popover(_lbl, use_container_width=True):
        sel = st.pills(
            etiqueta, valores, selection_mode="multi",
            key=key, label_visibility="collapsed",
        ) or []
    if sel:
        df_in = df_in[df_in[col].astype(str).isin(sel)]
    return df_in, sel


def _chip_numerico(df_in, col, key, etiqueta):
    """Chip-popover single-select para una columna numérica.
    Opciones: Todos / Faltantes (<0) / Sobrantes (>0) / Top 10 / Top 20.
    Top N = filas de mayor magnitud (|valor|). Devuelve el df filtrado."""
    if not col or col not in df_in.columns:
        return df_in
    opciones = ["Todos", "Faltantes", "Sobrantes", "Top 10", "Top 20"]
    _prev = st.session_state.get(key) or "Todos"
    _lbl = etiqueta if _prev == "Todos" else f"{etiqueta} · {_prev}"
    with st.popover(_lbl, use_container_width=True):
        sel = st.pills(
            etiqueta, opciones, default="Todos",
            key=key, label_visibility="collapsed",
        ) or "Todos"
    serie = pd.to_numeric(df_in[col], errors="coerce")
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
        c1, c2, c3, c4, _ = st.columns([1, 1, 1, 1.2, 2])
        with c1:
            df_in, _ = _chip_categorico(df_in, col_area,
                                        "ajuste_tabla_filtro_area", "Área")
        with c2:
            df_in, _ = _chip_categorico(df_in, col_fam,
                                        "ajuste_tabla_filtro_familia", "Familia")
        with c3:
            df_in = _chip_numerico(df_in, col_aj,
                                   "ajuste_tabla_filtro_ajuste", "Ajuste")
        with c4:
            df_in = _chip_numerico(df_in, col_ajval,
                                   "ajuste_tabla_filtro_ajusteval", "Ajuste Valor.")
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
    _opciones = {"Tabla": ":material/table_rows: Tabla",
             "Gráficos": ":material/monitoring: Gráficos"}
    with st.container(key=f"vistatabs_{reporte}"):
        vista = st.radio(
            "Vista",
            options=list(_opciones.keys()),
            format_func=lambda o: _opciones[o],
            horizontal=True,
            label_visibility="collapsed",
            key=f"vista_seg_{reporte}",
        )
    return vista or "Tabla"


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
        vista = _selector_vista()
        if vista == "Tabla":
            renderizar_aggrid_compras(df_f, font_px)
        else:
            renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df)

    # ── INVENTARIO VALORIZADO ────────────────────────────────────────────────
    elif reporte == "Inventario Valorizado":
        st.markdown(
            '<p style="font-size:22px;font-weight:700;color:#18181d;'
            'margin:0 0 0.6rem 0;line-height:1.2;">Inventario Valorizado</p>',
            unsafe_allow_html=True,
        )
        vista = _selector_vista()
        if vista == "Tabla":
            _render_tabla()
        else:
            renderizar_graficos(df_f, es_movil=usa_vista_movil)

    # ── SALIDAS ──────────────────────────────────────────────────────────────
    elif reporte == "Salidas":
        vista = _selector_vista()

        if vista == "Tabla":
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

                _render_kpis_salidas(df_f)

                cols_finales = list(cols_sel)
                if grupos_sel:
                    for c in grupos_sel:
                        if c not in cols_finales:
                            cols_finales.append(c)

                _aviso_rapido_aggrid(df_f[cols_finales])
                renderizar_aggrid_desktop(
                    df_f[cols_finales], grupos_sel, cols_sel, reporte, int(zoom),
                    cols_visibles=None,
                )
        else:
            renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df)

    # ── REQUERIMIENTOS ───────────────────────────────────────────────────────
    elif reporte == "Requerimientos":
        _render_requerimientos(df_f, col_fecha, grupos_sel, cols_mostrar, font_px, cfg)

    # ── RESTO DE REPORTES (incluye Ajuste de Inventario) ────────────────────
    else:
        if not es_ajuste:
            st.markdown(
                f'<p style="font-size:22px;font-weight:700;color:#18181d;'
                f'margin:0 0 0.2rem 0;line-height:1.2;">{reporte}</p>'
                f'<hr style="border:none;border-top:2px solid #6c5ce7;margin:0 0 0.8rem 0;">',
                unsafe_allow_html=True,
            )
            vista = _selector_vista()
        else:
            # ── Ajuste de Inventario — cabecera completa DENTRO del fragment ─
            #
            # Toda la lógica de layout (tabs + segmented) vive aquí para que
            # el fragment sea autónomo. La fecha se ha movido a la franja
            # superior (fuera del fragmento) para que siempre esté visible.

            # 1) Auto-detectar ámbito (Del periodo / Histórico) según rango.
            _auto_ambito = _calcular_ajuste_ambito_auto()
            if "ajuste_graf_ambito" not in st.session_state:
                st.session_state["ajuste_graf_ambito"] = _auto_ambito
            _rango_actual = st.session_state.get("ajuste_rango_aplicado")
            if _rango_actual != st.session_state.get("_ajuste_rango_prev_ambito"):
                st.session_state["ajuste_graf_ambito"] = _auto_ambito
                st.session_state["_ajuste_rango_prev_ambito"] = _rango_actual

            # 2) Layout de la fila superior: leer vista desde session_state.
            _vista_actual = st.session_state.get(f"vista_seg_{reporte}", "Tabla")
            _mostrar_segmented = (_vista_actual == "Gráficos")

            if _mostrar_segmented:
                col_tabs, col_seg = st.columns(
                    [4, 1.2], vertical_alignment="bottom",
                )
                with col_tabs:
                    vista = _selector_vista()
                with col_seg:
                    with st.container(key="ajuste_ambito_pill"):
                        st.segmented_control(
                            "Ámbito",
                            ["Del periodo", "Histórico"],
                            key="ajuste_graf_ambito",
                            label_visibility="collapsed",
                        )
            else:
                vista = _selector_vista()

        if vista == "Tabla":
            if es_ajuste:
                df_tabla = _filtros_chips_ajuste_tabla(df_f)
                if df_tabla.empty:
                    st.info("Ningún registro coincide con los filtros seleccionados.")
                else:
                    _render_tabla(df_tabla)
            else:
                _render_tabla()
        else:
            renderizar_graficos_reporte(df_f, reporte, cfg, df_full=df)

    perf.fragment_end("_render_contenido")                                  # ⚡ PERF


# ── Llamada al fragment ──────────────────────────────────────────────────────
_render_contenido()

perf.end()                                                                  # ⚡ PERF
