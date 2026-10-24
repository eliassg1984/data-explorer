"""graficos.ajuste - dashboard de graficos de Ajuste de Inventario.

Era un ajuste.py de 2.607 lineas; desde el 2026-08-08 es un PAQUETE, con
el mismo criterio que graficos/compras/: una vista por modulo. Se partio
porque es el fichero con MAS churn del repo con diferencia (80 de los
ultimos 200 commits, 2,7x el siguiente) y sus dos funciones mayores
—cascada y mapa de calor— eran el 60% del archivo.

    _comun.py            layout del rail, fechas de corte, periodos
    _evolucion.py        Tiempo › Evolucion: serie + matriz, UNA pieza propia (#504/#692)
    _pivote.py           Tiempo › Detalle por producto: la tabla pivote (#504)
    _cascada.py          vista Cascada (la mas grande)
    _heatmap.py          vista "Mapa de calor" (hoy una tabla Familia x Area, #468)
    _pareto.py           el Pareto del detalle de Cascada y Mapa de calor (#677)
    _productos.py        la tabla de productos con areas desplegables (#677)
    _diferencias.py      vista Analisis de diferencias: por que no cuadra cada linea (#650)

Este __init__ se queda con lo que define el dashboard como tal: la
config del rail, su pila y el punto de entrada publico
renderizar_graficos_ajuste().

Desde el 2026-10-11 (regla #632) Ajuste no tiene fecha en la franja: cada
vista elige la suya —una sesion de inventario las tres de arriba, meses las
dos de abajo— y lee el parquet ENTERO. Con eso se fue
`categoria_rango_ajuste`, que repartia el rango de la franja entre las dos
categorias del rail, y las dos pilas se hicieron una.
"""

import datetime as _dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import kardex
from ._cierre import vista_cierre

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
    compartimento_filtros, contar_filtros, dibujar_perspectiva, filtro_pills,
    sembrar_seleccion,
    _card, _es_movil, _layout, _render_rail, _resolver, _slug, _wrap_cat,
    pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    renderizar_graficos_genericos, seccion_perezosa,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.compras import _periodo_serie

# Re-exports de las vistas. El entry point de abajo las llama, y
# test_graficos.py las prueba una por una como `_aj._graf_*` — por eso
# entran al namespace del paquete y no solo al del modulo que las define.
from graficos.ajuste._comun import (  # noqa: F401
    CLAVE_MES, FAMILIAS_DE_ENTRADA, MES_OPERATIVO, MES_REGISTRO, _fmt_corte,
    _layout_aj, mes_operativo_activo, recargar_si_cambio_mes,
)
from graficos.ajuste._evolucion import (  # noqa: F401
    datos_pieza, periodos_ajuste, serie_ajuste, vista_evolucion_ajuste,
)
from graficos.ajuste._pivote import (  # noqa: F401
    _armar_tabla_pivote_ajuste, vista_detalle_ajuste,
)
from graficos.ajuste._cascada import _graf_waterfall_ajuste  # noqa: F401
from graficos.ajuste._heatmap import _graf_heatmap_ajuste  # noqa: F401
# El Pareto vivía en la vista «Distribución de diferencias», que se quitó el
# 2026-10-19: hoy es una opción del detalle de Por familia y Familia × Área
# (regla #677). test_graficos.py lo prueba como `_aj._pareto_datos`.
from graficos.ajuste._pareto import (  # noqa: F401
    _fig_pareto_ajuste, _pareto_datos,
)
from graficos.ajuste._diferencias import vista_diferencias


# Rail derecho de Ajuste (mismo componente compartido que Compras). El id
# (izquierda) es el string que consume el dispatch de gráficos; el label
# (derecha) es lo que se pinta en el botón. "Tabla" es un item más del rail
# (misma idea que Compras): al elegirlo se renderiza la tabla AgGrid vía el
# callback `tabla_cb` que inyecta app.py. Oculta desde el 2026-09-23 junto
# con las de los demás reportes: `rail_sin_tablas` aquí y `pila_sin_tablas`
# en las dos pilas, siempre de a par (regla #507).
_AJUSTE_RAIL_CATEGORIAS = rail_sin_tablas((
    # Los RÓTULOS (segundo elemento) se renombraron el 2026-10-02 a pedido:
    # «Cascada» hace rato es una tabla de familias (#441) y «Mapa de calor»
    # una tabla Familia × Área (#468). Los IDS (primer elemento) no se tocan:
    # son la URL, las keys, el CSS y `_PILA_VISUAL`. Regla #584.
    #
    # Desde el 2026-10-23 (regla #712) las dos de arriba son UNA vista,
    # «Diferencias del cierre», y las dos del tiempo otra, «Evolución»: cada
    # una con dos perspectivas (`PERSPECTIVAS_CIERRE`, `PERSPECTIVAS_TIEMPO`)
    # que dibujan la vista de siempre. Etapa 5 de la navegación del boceto
    # del rail compacto (#708). Un `?vista=cascada` guardado cae en la
    # primera vista.
    # El id no empieza con «Diferencias»: el temporizador del rail busca los
    # botones con `[class*=…]`, y la key de «Diferencias» sería un prefijo
    # de ésta (lo ataja `test_graficos.py::_pruebas_pestanas_franja`).
    ("Visual", (("Ajuste del cierre", "Diferencias del cierre",
                 ":material/view_list:"),)),
    # «Distribución de diferencias» se fue el 2026-10-19: de sus tres modos
    # sólo el Pareto se podía analizar, y pasó al detalle de las dos de
    # arriba (regla #677).
    # Desde el 2026-09-23 «Comparativa mensual» y «Por fecha de corte» no
    # existen: miraban el mismo dato que Evolución y se fusionaron en ella
    # (#501). El mismo día la tabla volvió a salir de Evolución como vista
    # propia, porque no dependía de la serie (#504).
    # «Revisar» nació el 2026-10-13 con «Análisis de diferencias» (regla
    # #650): por qué falta o sobra cada producto en cada área, con la ficha
    # de la línea. Va entre las vistas de un conteo y las del tiempo porque
    # mira UNA sesión, como las de arriba.
    ("Revisar",     (("Diferencias", "Análisis de diferencias",
                      ":material/troubleshoot:"),)),
    ("Tiempo",      (("Evolución del ajuste", "Evolución", ":material/show_chart:"),)),
    ("Datos",       (("Tabla",          "Tabla",         ":material/table_rows:"),)),
))


# LA PILA — UNA SOLA desde el 2026-10-11 (regla #632).
#
# Hasta ese día eran dos, una por categoría del rail, porque cada categoría
# recordaba su PROPIO rango de la franja: Cascada/Mapa de calor/Distribución
# se leían en un período corto y Evolución en un año, y apiladas juntas
# habrían mostrado dos vistas que piden rangos distintos con una sola fecha
# activa (#220). Desde que cada vista elige su fecha —una sesión las tres de
# arriba, meses las dos de abajo— esa razón no existe y Ajuste se lee bajando
# como los demás reportes. Las categorías del rail quedan como grupos.
#
# Las PERSPECTIVAS (regla #712): (perspectiva, sección, id de la vista que
# era, su rótulo). Las secciones `aj_sec_cascada`, `aj_sec_heatmap`,
# `aj_sec_evolucion` y `aj_sec_detalle` siguen siendo las de siempre —su
# dibujante, sus keys—; en la pila están las que las contienen, con el
# `_sec_persp_` que le hace ceder a su tarjeta el alto de la franja.
K_PERSP_CIERRE, K_PERSP_TIEMPO = "_aj_persp_cierre", "_aj_persp_tiempo"
PERSPECTIVAS_CIERRE = (
    ("Por familia", "aj_sec_cascada", "Cascada", "Por familia"),
    ("Familia × Área", "aj_sec_heatmap", "Mapa de calor", "Familia × Área"),
)
PERSPECTIVAS_TIEMPO = (
    ("Serie", "aj_sec_evolucion", "Evolución", "Evolución"),
    ("Tabla dinámica", "aj_sec_detalle", "Detalle por producto", "Tabla dinámica"),
)
EJES_CIERRE = ((K_PERSP_CIERRE, "Ver", tuple(p[0] for p in PERSPECTIVAS_CIERRE)),)
EJES_TIEMPO = ((K_PERSP_TIEMPO, "Ver", tuple(p[0] for p in PERSPECTIVAS_TIEMPO)),)
_PILA = pila_sin_tablas((
    ("aj_sec_persp_cierre", "Ajuste del cierre"),
    ("aj_sec_diferencias",  "Diferencias"),
    ("aj_sec_persp_tiempo", "Evolución del ajuste"),
    ("aj_sec_tabla",        "Tabla"),
))


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
    col_cantidad   = _resolver(df_f, ["AJUSTE", "CANTIDAD AJUSTE", "CANTIDAD"])
    # Lo que registró el kardex por cada línea del cierre (regla #612). Sólo
    # existe si `data.cargar` encontró `ajustekardex.parquet` en R2.
    col_kardex     = _resolver(df_f, [kardex.COL_VALOR_KX])
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

    # El valor de vuelta se ignora: con `secciones` el rail dejó de ELEGIR
    # contenido (la página dibuja la pila entera) y pasó a MARCAR dónde
    # estás.
    _render_rail(_AJUSTE_RAIL_CATEGORIAS, "ajuste_graf_tipo",
                 btn_prefix="aj_rail_btn_", secciones=_PILA)

    # EL PARQUET ENTERO (regla #632). La franja de Ajuste ya no tiene fecha:
    # cada vista recorta lo suyo. `app.py` ya no filtra el `df_f` de este
    # reporte por rango, pero `df_full` es el nombre de lo que se quiere.
    if df_full is None:
        df_full = df_f

    ambito = "actual"

    # Los chips de arriba sólo los usa la categoría Tiempo (las vistas de
    # Visual traen sus filtros propios, #425), y abren con las MISMAS cinco
    # familias que ellas: sin COSTOS PRODUCCION. Si Cascada abre sin esa
    # familia y Evolución con ella, dos vistas del mismo reporte cuentan dos
    # totales distintos. Y es la familia de los castigos grandes: el 10 set
    # 2025 son -S/ 594k en 138 filas, que con un rango que lo incluya
    # aplastan la serie entera contra el cero. Es un default, no un piso
    # (#501).
    sembrar_seleccion(df_full, col_familia, "ajuste_graf_filtro_familia",
                      list(FAMILIAS_DE_ENTRADA))
    # SÓLO FAMILIA desde el 2026-09-23. El Área se mudó a la fila del título
    # de cada vista de Tiempo, a pedido («añadamos un filtro de áreas, en la
    # misma fila del título»), con su propia clave: Evolución y Detalle son
    # vistas independientes (#504) y un área elegida en una no tiene por qué
    # recortar la otra sin decirlo. Regla #505.
    area_sel, fam_sel = [], []
    # «Mes del cierre» vivía acá hasta el 2026-10-11: pasó al pie del panel
    # de meses de cada vista, que es el único lugar donde cambia algo
    # (`_comun._pie_mes_cierre`, regla #632).
    with compartimento_filtros(contar_filtros("ajuste_graf_filtro_familia")):
        _, fam_sel = filtro_pills(df_full, col_familia,
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
        d = df_full

    # Cascada y Mapa de calor NO pasan por estos chips: tienen
    # los suyos. Cascada y Mapa de calor traen la fila entera de tres (corte ·
    # Área acotada a las que movieron algo · Familia sembrada con cinco), la
    # misma pieza — `graficos.ajuste._comun.estado_filtros_vista`; la
    # estrenaron el 2026-09-14/15, a pedido. (Distribución, que
    # también, se quitó el 2026-10-19: regla #677.) Se guarda el df de acá, antes de recortar, porque
    # filtrar dos veces dejaría la vista mostrando la intersección de dos
    # compartimentos y sólo uno visible. De los chips de arriba hoy sólo
    # cuelgan Evolución y la tabla dinámica. Ver arquitectura.md regla #425.
    d_sin_chips = d

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
        """Cascada va SIN `_en_tarjeta`: dibuja sus propias tarjetas.

        Es la única sección de la pila que no entra en una card única —
        desde el 2026-09-16 son dos tarjetas, la tabla de familias y el
        detalle de la que está en foco (regla #441), así que envolverla
        daría una tarjeta alrededor de otras dos. El chequeo de vacío lo hace ella, después de aplicar sus
        propios filtros: el `_vacio` de acá mira el df de los chips de
        arriba, que la cascada ya no usa.
        """
        _graf_waterfall_ajuste(
            d_sin_chips, col_familia, col_area, col_ajuste_val,
            col_producto=col_producto, col_valorizado=col_valorizado,
            col_cantidad=col_cantidad, df_full=df_full, col_fecha=col_fecha,
            col_unidad=col_unidad)

    def _dib_heatmap():
        """Mapa de calor: dibuja sus PROPIAS tarjetas (la tabla arriba y los
        dos detalles abajo), como la Cascada — ya NO una card única alrededor
        (2026-09-22, a pedido: «la misma distribución de 3 tarjetas»). Por eso
        no usa `_en_tarjeta`, igual que `_dib_cascada`: envolverla daría una
        tarjeta alrededor de las tres. Y también como antes, su `_vacio` mira
        el df de los chips de arriba —que esta vista ya no usa—: con él un chip
        que deja `d` sin filas escondería el mapa ENTERO, sus tres filtros
        incluidos. La vista avisa sola cuando se queda sin datos; recibe
        `d_sin_chips`.
        """
        _graf_heatmap_ajuste(
            d_sin_chips, col_familia, col_area, col_ajuste_val,
            col_producto=col_producto, col_fecha=col_fecha,
            df_full=df_full, col_valorizado=col_valorizado,
            col_cantidad=col_cantidad, col_unidad=col_unidad)

    def _dib_diferencias():
        """Análisis de diferencias: su propia tarjeta, su sesión y su familia
        (regla #650). Recibe el parquet entero, como las de arriba: la cuenta
        la arma `data.diferencias_ajuste_sesion` con el kardex y las recetas."""
        vista_diferencias(df_full, col_fecha, col_familia, col_area,
                          col_ajuste_val, col_producto)

    def _dib_evolucion():
        """Evolución dibuja su propia tarjeta (serie + matriz, regla #692),
        así que no va en `_en_tarjeta`. Recibe `d`: el parquet entero con los
        chips; los meses los elige ella (regla #632). `df_full`, sin filtros,
        es para el consumo de «¿Es mucho?»."""
        if _vacio:
            with st.container(border=True, key="ajuste_graf_card_izq_evo_vacio"):
                st.info("No hay datos para los filtros seleccionados.")
            return
        vista_evolucion_ajuste(d, col_fecha, col_familia, col_area,
                               col_ajuste_val, col_valorizado,
                               col_kardex=col_kardex, d_full=df_full)
        recargar_si_cambio_mes()

    def _dib_detalle():
        """La tabla por producto, con su propio grano (#504). Mismo `d`."""
        if _vacio:
            with st.container(border=True, key="ajuste_graf_card_izq_det_vacio"):
                st.info("No hay datos para los filtros seleccionados.")
            return
        vista_detalle_ajuste(d, col_fecha, col_familia, col_area,
                             col_ajuste_val, col_producto, col_cantidad)
        recargar_si_cambio_mes()

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
        "aj_sec_persp_cierre": lambda: vista_cierre(df_full),
        "aj_sec_persp_tiempo": lambda: dibujar_perspectiva(
            "tiempo", EJES_TIEMPO, PERSPECTIVAS_TIEMPO, _DIBUJANTES),
        "aj_sec_cascada":      _dib_cascada,
        "aj_sec_heatmap":      _dib_heatmap,
        "aj_sec_diferencias":  _dib_diferencias,
        "aj_sec_tabla":        _dib_tabla,
        "aj_sec_evolucion":    _dib_evolucion,
        "aj_sec_detalle":      _dib_detalle,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga, y tiene que sobrevivir a que el fragment de
    # adentro se re-dibuje (mismo bucle que Compras y Receta Base).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
