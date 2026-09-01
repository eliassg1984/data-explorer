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
    compartimento_filtros, contar_filtros, filtro_pills,
    _card, _es_movil, _layout, _render_rail, _resolver, _slug, _wrap_cat,
    publicar_contexto_ia, renderizar_graficos_genericos, seccion_perezosa,
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


# ORDEN DE LAS PILAS — UNA POR CATEGORÍA DE RANGO, y eso no es capricho.
#
# El resto de los reportes apila TODAS sus vistas en una página que se lee
# bajando. Ajuste no puede: cada categoría del rail recuerda su PROPIO rango
# de fecha (`estado_rango.clave_rango(categoria=...)`, alimentada por
# `categoria_rango_ajuste` de abajo) porque Cascada/Mapa de calor/
# Distribución/Tabla se leen acotadas a un período y Evolución/Comparativa/
# Por fecha necesitan varios meses o un año. Antes compartían una sola clave
# y se pisaban el rango entre sí — apilar las siete juntas sería volver a
# ESE bug, con la página mostrando a la vez dos vistas que piden rangos
# distintos y una sola fecha activa para las dos.
#
# Así que cada categoría es su propia pila, y saltar de una a la otra sigue
# siendo una navegación de verdad: cambia el ítem del rail Y la clave del
# rango, que es exactamente lo que tiene que pasar. Adentro de cada
# categoría, en cambio, el rango SÍ es el mismo, así que apilar es seguro.
#
# `_render_rail` ya dibuja la línea que separa los ítems de la pila activa
# de los que son destino aparte (nació para Documentos SUNAT en Compras),
# así que la frontera entre categorías se ve sin agregar nada.
_PILA_VISUAL = (
    ("aj_sec_cascada",      "Cascada"),
    ("aj_sec_heatmap",      "Mapa de calor"),
    ("aj_sec_distribucion", "Distribución"),
    ("aj_sec_tabla",        "Tabla"),
)
_PILA_TIEMPO = (
    ("aj_sec_evolucion",   "Evolución"),
    ("aj_sec_comparativa", "Comparativa mensual"),
    ("aj_sec_porfecha",    "Por fecha de corte"),
)
_PILAS = {"visual": _PILA_VISUAL, "tiempo": _PILA_TIEMPO}


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

    # La pila que se APILA es la de la categoría del ítem activo; la otra
    # queda como destino aparte (el rail le dibuja la línea divisoria sola).
    # `categoria_rango_ajuste(None)` devuelve "visual", que es la categoría
    # por defecto y la misma que asume `app.py` al resolver la clave del
    # rango — las dos tienen que coincidir o la página mostraría una pila
    # filtrada por el rango de la otra.
    _cat = categoria_rango_ajuste(st.session_state.get("ajuste_graf_tipo"))
    _pila = _PILAS[_cat]
    # El valor de vuelta se ignora: con `secciones` el rail dejó de ELEGIR
    # contenido (la página dibuja la pila entera) y pasó a MARCAR dónde
    # estás. Quien decide QUÉ se apila es `_cat`, unas líneas arriba.
    _render_rail(_AJUSTE_RAIL_CATEGORIAS, "ajuste_graf_tipo",
                 btn_prefix="aj_rail_btn_", secciones=_pila)

    ambito = "actual"

    area_sel, fam_sel = [], []
    with compartimento_filtros(contar_filtros("ajuste_graf_filtro_area",
                                              "ajuste_graf_filtro_familia")):
        _, area_sel = filtro_pills(df_f, col_area,
                                   "ajuste_graf_filtro_area", "Área")
        _, fam_sel = filtro_pills(df_f, col_familia,
                                  "ajuste_graf_filtro_familia", "Familia")

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

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Ajuste de Inventario", d,
                         {"Área": area_sel, "Familia": fam_sel})

    # El "sin datos" ya NO corta la página entera. Con la pila hay varias
    # secciones y una sola de ellas es la Tabla, que antes se dibujaba
    # ANTES de este chequeo (volvía temprano, arriba) y por lo tanto seguía
    # funcionando con los chips vacíos. Cortar acá se la llevaría puesta.
    _vacio = d is None or d.empty

    def _en_tarjeta(slug, cuerpo):
        """Una sección de la pila, con su tarjeta y el aviso de vacío.

        La key conserva el prefijo `ajuste_graf_card_` a propósito: de él
        cuelga el CSS de tarjeta (el clamp de una pantalla en
        `estilos/_80_cards.py`). Lo que cambia es el sufijo, que antes era
        el ámbito —siempre "actual", o sea una sola key para las siete
        vistas, que nunca coexistían— y ahora es la vista: apiladas serían
        varios widgets con la MISMA key, que en Streamlit es una excepción.
        """
        with st.container(border=True, key=f"ajuste_graf_card_izq_{slug}"):
            if _vacio:
                st.info("No hay datos para los filtros seleccionados.")
            else:
                cuerpo()

    def _dib_cascada():
        _en_tarjeta("cascada", lambda: _graf_waterfall_ajuste(
            d, col_familia, col_area, col_ajuste_val,
            col_producto=col_producto, col_valorizado=col_valorizado,
            col_cantidad=col_cantidad, df_full=df_full, col_fecha=col_fecha,
            col_unidad=col_unidad))

    def _dib_heatmap():
        _en_tarjeta("heatmap", lambda: _graf_heatmap_ajuste(
            d, col_familia, col_area, col_ajuste_val,
            col_producto=col_producto, col_fecha=col_fecha, df_full=df_full,
            col_valorizado=col_valorizado, area_sel=area_sel,
            fam_sel=fam_sel, col_cantidad=col_cantidad,
            col_unidad=col_unidad))

    def _dib_distribucion():
        _en_tarjeta("distribucion", lambda: _graf_distribucion_ajuste(
            d, col_familia, col_area, col_ajuste_val, col_producto,
            col_codigo=col_codigo, col_cantidad=col_cantidad,
            col_fecha=col_fecha, col_unidad=col_unidad))

    def _dib_evolucion():
        _en_tarjeta("evolucion", lambda: _graf_evolucion_ajuste(
            d, col_fecha, col_familia, col_ajuste_val, col_valorizado))

    def _dib_comparativa():
        _en_tarjeta("comparativa", lambda: _graf_comparativa_mensual(
            d, col_fecha, col_ajuste_val))

    def _dib_porfecha():
        _en_tarjeta("porfecha", lambda: _tabla_pivote_fecha_ajuste(
            df_full if df_full is not None else d,
            col_familia, col_ajuste_val, col_producto, col_cantidad,
            col_fecha, col_area=col_area, area_sel=area_sel,
            fam_sel=fam_sel))

    def _dib_tabla():
        # `df_f` y no `d`: Ajuste no tiene chips propios para la Tabla —
        # pasa su df tal cual y app.py le aplica los genéricos de la franja.
        # La FIRMA es la misma para todos los dashboards, ver
        # graficos/__init__.py. Se conserva el comportamiento exacto que
        # tenía cuando la Tabla volvía temprano, antes de los chips.
        with st.container(border=True, key="ajuste_graf_card_izq_tabla"):
            if tabla_cb is not None:
                tabla_cb(df_f)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "aj_sec_cascada":      _dib_cascada,
        "aj_sec_heatmap":      _dib_heatmap,
        "aj_sec_distribucion": _dib_distribucion,
        "aj_sec_tabla":        _dib_tabla,
        "aj_sec_evolucion":    _dib_evolucion,
        "aj_sec_comparativa":  _dib_comparativa,
        "aj_sec_porfecha":     _dib_porfecha,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga, y tiene que sobrevivir a que el fragment de
    # adentro se re-dibuje (mismo bucle que Compras y Receta Base).
    for _i, (_clave, _vista) in enumerate(_pila):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
