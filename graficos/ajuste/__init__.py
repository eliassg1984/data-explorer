"""graficos.ajuste - dashboard de graficos de Ajuste de Inventario.

Era un ajuste.py de 2.607 lineas; desde el 2026-08-08 es un PAQUETE, con
el mismo criterio que graficos/compras/: una vista por modulo. Se partio
porque es el fichero con MAS churn del repo con diferencia (80 de los
ultimos 200 commits, 2,7x el siguiente) y sus dos funciones mayores
—cascada y mapa de calor— eran el 60% del archivo.

    _comun.py            layout del rail, fechas de corte, periodos
    _evolucion.py        categoria Tiempo: serie temporal + comparativa
    _pivote.py           tabla "Por fecha de corte"
    _cascada.py          vista Cascada (la mas grande)
    _heatmap.py          vista Mapa de calor
    _distribucion.py     vista Distribucion

Este __init__ se queda con lo que define el dashboard como tal: la
config del rail, a que categoria de rango pertenece cada item, y el
punto de entrada publico renderizar_graficos_ajuste().

La API publica NO cambio: `from graficos.ajuste import
categoria_rango_ajuste, renderizar_graficos_ajuste` sigue igual.
"""

import datetime as _dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA, GRIS_BORDE, GRIS_FONDO,
    PALETA_SERIES, SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
    BLANCO, CELDA_POS_TEXTO,
    DANGER_TEXT, ERROR, ERROR_FONDO, ESCALA_CONTINUA, EXITO, EXITO_FONDO,
    GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_CABECERA_GRUPO, LAVANDA_FONDO, LAVANDA_SELECCION,
    AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO,
    AJUSTE_CRIT_FONDO, AJUSTE_CRIT_TEXTO, AJUSTE_CRIT_BORDE,
    AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO, AJUSTE_ALERTA_BORDE,
    AJUSTE_SOB_FONDO, AJUSTE_SOB_BORDE,
)
from graficos.base import (
    _card, _es_movil, _layout, _render_rail, _resolver, _slug, _wrap_cat,
    renderizar_graficos_genericos,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.compras import _periodo_serie

# Re-exports de las vistas. El entry point de abajo las llama, y
# test_graficos.py las prueba una por una como `_aj._graf_*` — por eso
# entran al namespace del paquete y no solo al del modulo que las define.
from graficos.ajuste._comun import _fmt_corte, _layout_aj  # noqa: F401
from graficos.ajuste._evolucion import (  # noqa: F401
    _graf_comparativa_mensual, _graf_evolucion_ajuste,
)
from graficos.ajuste._pivote import _tabla_pivote_fecha_ajuste  # noqa: F401
from graficos.ajuste._cascada import _graf_waterfall_ajuste  # noqa: F401
from graficos.ajuste._heatmap import _graf_heatmap_ajuste  # noqa: F401
from graficos.ajuste._distribucion import _graf_distribucion_ajuste  # noqa: F401


# Rail derecho de Ajuste (mismo componente compartido que Compras). El id
# (izquierda) es el string que consume el dispatch de gráficos; el label
# (derecha) es lo que se pinta en el botón. "Tabla" es un item más del rail
# (misma idea que Compras): al elegirlo se renderiza la tabla AgGrid vía el
# callback `tabla_cb` que inyecta app.py.
_AJUSTE_RAIL_CATEGORIAS = (
    ("Visual", (("Cascada",        "Cascada"),
                     ("Mapa de calor",  "Mapa de calor"),
                     ("Distribución",   "Distribución"))),
    ("Tiempo",      (("Evolución",           "Evolución"),
                     ("Comparativa mensual", "Comparativa"),
                     ("Por fecha de corte",  "Por fecha"))),
    ("Datos",       (("Tabla",          "Tabla"),)),
)


def categoria_rango_ajuste(graf_id):
    """A qué categoría de rango de fecha pertenece un item del rail de
    Ajuste: "tiempo" (Evolución/Comparativa — necesitan varios meses o un
    año para decir algo) o "visual" (Cascada/Mapa de calor/Distribución/
    Tabla — snapshot de un período, tiene sentido acotado a un mes).

    `app.py` usa esto para decidir qué clave de `session_state` lee/escribe
    la franja de fecha (`ajuste_rango_aplicado_visual` vs `_tiempo`, ver
    `estado_rango.clave_rango`) — así cada categoría recuerda su propio
    rango sin pisar al otro. Única fuente de verdad: `_AJUSTE_RAIL_CATEGORIAS`
    de arriba; si se agrega un item nuevo al rail, esto no hay que tocarlo."""
    for cat_nombre, items in _AJUSTE_RAIL_CATEGORIAS:
        if cat_nombre == "Tiempo" and any(oid == graf_id for oid, _ in items):
            return "tiempo"
    return "visual"


def renderizar_graficos_ajuste(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """
    Gráficos de Ajuste de Inventario — layout con rail derecho (estándar).
    """
    col_fecha      = _resolver(df_f, ["FECHA APERTURA INVENTARIO", "FECHA", "MES"])
    col_familia    = _resolver(df_f, ["FAMILIA", "Nombre Familia", "NOMBRE FAMILIA"])
    col_area       = _resolver(df_f, ["AREA", "Nombre Area", "NOMBRE AREA"])
    col_ajuste_val = _resolver(df_f, ["AJUSTE VALORIZADO", "AJUSTEVALORIZADO"])
    col_valorizado = _resolver(df_f, ["VALORIZADO TOTAL", "VALORIZADO", "VALORIZADOTOTAL"])
    col_producto   = _resolver(df_f, ["NOMBRE PRODUCTO", "PRODUCTO", "DESCRIPCION"])
    col_codigo     = _resolver(df_f, ["CODIGO PRODUCTO", "Codigo Producto", "COD PRODUCTO"])
    col_cantidad   = _resolver(df_f, ["AJUSTE", "CANTIDAD AJUSTE", "CANTIDAD"])
    # Misma lista de candidatos que graficos/compras/__init__.py::col_um —
    # la unidad real de Kardex (Kg, Und, Lt...), no un sufijo inventado.
    col_unidad     = _resolver(df_f, ["Unidad de Ingreso", "Unidad_de_ingreso",
                                      "Unidad Ingreso", "Unidad Kardex", "Unidad_medida",
                                      "Unidad medida", "Unidad de medida", "Unidad_compra",
                                      "Unidad compra", "Unidad", "UM", "Und"])

    if not col_ajuste_val:
        st.warning(
            "No se encontró la columna de ajuste valorizado. "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    graf = _render_rail(_AJUSTE_RAIL_CATEGORIAS, "ajuste_graf_tipo",
                        btn_prefix="aj_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            # Ajuste no tiene chips propios: pasa su df tal cual y app.py le
            # aplica los genéricos de la franja. La FIRMA es la misma para
            # todos los dashboards — ver graficos/__init__.py.
            tabla_cb(df_f)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    ambito = "actual"

    area_sel, fam_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        col_ff_area, col_ff_fam, _ = st.columns([1, 1, 4])
        with col_ff_area:
            if col_area and col_area in df_f.columns:
                areas = sorted(df_f[col_area].dropna()
                               .astype(str).unique().tolist())
                if areas:
                    _n_area = len(st.session_state.get("ajuste_graf_filtro_area") or [])
                    _lbl_area = f":material/filter_alt: Área :violet-badge[{_n_area}]" if _n_area else ":material/filter_alt: Área"
                    with st.popover(_lbl_area, use_container_width=True):
                        area_sel = st.pills(
                            "Área",
                            areas,
                            selection_mode="multi",
                            key="ajuste_graf_filtro_area",
                            label_visibility="collapsed",
                        ) or []
        with col_ff_fam:
            if col_familia and col_familia in df_f.columns:
                familias = sorted(df_f[col_familia].dropna()
                                  .astype(str).unique().tolist())
                if familias:
                    _n_fam = len(st.session_state.get("ajuste_graf_filtro_familia") or [])
                    _lbl_fam = f":material/category: Familia :violet-badge[{_n_fam}]" if _n_fam else ":material/category: Familia"
                    with st.popover(_lbl_fam, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia",
                            familias,
                            selection_mode="multi",
                            key="ajuste_graf_filtro_familia",
                            label_visibility="collapsed",
                        ) or []

    if ambito == "Histórico":
        base = df_full if df_full is not None else df_f
        anio_actual = _dt.date.today().year
        if col_fecha and col_fecha in base.columns:
            _f = pd.to_datetime(base[col_fecha], errors="coerce")
            base = base[_f.dt.year == anio_actual]
        d = base
        st.caption(
            f"📆 Vista histórica del año {anio_actual}. "
            "El rango de fechas del popover no aplica aquí."
        )
    else:
        d = df_f

    if area_sel and col_area and col_area in d.columns:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_familia and col_familia in d.columns:
        d = d[d[col_familia].astype(str).isin(fam_sel)]

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _card_izq = st.container(
        border=True, key=f"ajuste_graf_card_izq_{_slug(ambito)}",
    )
    with _card_izq:
        if graf == "Evolución":
            _graf_evolucion_ajuste(d, col_fecha, col_familia,
                                   col_ajuste_val, col_valorizado)
        elif graf == "Comparativa mensual":
            _graf_comparativa_mensual(d, col_fecha, col_ajuste_val)
        elif graf == "Cascada":
            _graf_waterfall_ajuste(d, col_familia, col_area, col_ajuste_val,
                                   col_producto=col_producto,
                                   col_valorizado=col_valorizado,
                                   col_cantidad=col_cantidad,
                                   df_full=df_full, col_fecha=col_fecha,
                                   col_unidad=col_unidad)
        elif graf == "Mapa de calor":
            _graf_heatmap_ajuste(d, col_familia, col_area, col_ajuste_val,
                                 col_producto=col_producto,
                                 col_fecha=col_fecha, df_full=df_full,
                                 col_valorizado=col_valorizado,
                                 area_sel=area_sel, fam_sel=fam_sel,
                                 col_cantidad=col_cantidad,
                                 col_unidad=col_unidad)
        elif graf == "Distribución":
            _graf_distribucion_ajuste(d, col_familia, col_area,
                                      col_ajuste_val, col_producto,
                                      col_codigo=col_codigo,
                                      col_cantidad=col_cantidad,
                                      col_fecha=col_fecha,
                                      col_unidad=col_unidad)
        elif graf == "Por fecha de corte":
            _tabla_pivote_fecha_ajuste(
                df_full if df_full is not None else d,
                col_familia, col_ajuste_val, col_producto, col_cantidad,
                col_fecha, col_area=col_area, area_sel=area_sel,
                fam_sel=fam_sel,
            )
