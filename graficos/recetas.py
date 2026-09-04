"""
graficos.recetas — dashboard ÚNICO de Recetas (platos + recetas base).

Una sola página con las NUEVE vistas que hasta el 2026-09-04 vivían
repartidas en dos destinos que un chip alternaba (Receta base / Receta
venta). A pedido: «quiero que las visualizaciones de estos toggles figuren
todas juntas».

    Platos (recetaventa.parquet)       Composición del plato · Costeo Receta
                                       Venta · Ingredientes clave ·
                                       Panorama · Tabla
    Recetas base (recetabase.parquet)  Ranking · Insumos clave · Panorama ·
                                       Tabla

POR QUÉ ERAN DOS Y AHORA SON UNA. La separación se justificaba con una
medición equivocada: los docstrings de `recetabase.py`/`recetas_comun.py` y
la memoria de proyecto afirmaban «0% overlap, son dos catálogos
independientes» — pero eso se midió contra `recetabase.COD RB`, que es el
ID INTERNO de la receta base (5 dígitos, `00002`), no su código de
producto. La clave real es **`recetaventa.COD INS` ↔
`recetabase.COD PROD RB`** (7 dígitos, mismo espacio de numeración que
`compras.COD_PRODUCTO`): 401 códigos cruzan y los 401 NOMBRES coinciden
exacto en los dos lados (`INS RV` == `RB NOMBRE`, cero discrepancias).
Son 1.003 de 2.599 filas de recetaventa, en 334 de 828 platos. O sea que
una receta base no es la HERMANA de una receta de venta: es una PIEZA de
adentro (y con profundidad — 630 filas de recetabase apuntan a su vez a
otra receta base). Medido contra R2 real el 2026-09-04, ver
`arquitectura.md` regla #303.

Este módulo NO explota todavía ese enlace: sólo apila lo que ya existía.
El cruce Producto → Receta base → Plato queda para después.

DOS PARQUETS EN UNA PÁGINA. `app.py` carga UNO por reporte y lo pasa como
`df_f`; el segundo se carga acá con `data.cargar`, que es el patrón que ya
usa `recetas_comun.py::_cargar_flujo_compras` para traerse compras.parquet
desde otro dashboard. `df_f` es el de PLATOS (el reporte «Recetas» apunta a
recetaventa.parquet).

Las dos Tablas NO se dibujan igual, y no es un descuido:
  · la de platos va por `tabla_cb`, el callback que inyecta app.py — sabe
    de vista móvil, chips genéricos y aviso de columnas duplicadas;
  · la de recetas base llama a `renderizar_aggrid_desktop` directo, porque
    `tabla_cb` recorta con el `cols_mostrar` del reporte ACTIVO (ver
    `app.py::_render_tabla`) y pasarle el df de recetabase reventaría con
    un KeyError. Ver `_tabla_recetabase` abajo.

Punto de entrada público: renderizar_graficos_recetas().
"""

import streamlit as st

from data import cargar as _cargar_reporte
from estilos import TAM_FUENTE
from tablas import renderizar_aggrid_desktop
from graficos.base import (
    _render_rail, _resolver, renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.recetas_comun import _chip_fuente, _items_clave, _ranking_contenedores
from graficos.recetabase import _panorama_compras_base
from graficos.recetaventa import (
    _panorama_compras_venta, _tabla_composicion_venta, _tabla_costeo_venta,
)

# El rótulo del rail es CORTO a propósito: la franja de Vistas es
# horizontal y aplana las categorías a una sola fila (ver
# `base.py::_render_rail`), así que nueve items compiten por el ancho útil
# de una laptop (~1010px). El nombre largo vive en el id — que es lo que
# viaja en `?vista=` y lo que empareja con `_PILA`.
#
# El sufijo « · base» es el desambiguador: «Panorama de compras» y «Tabla»
# existían en los dos lados y al juntarlas quedaban dos items con el mismo
# nombre.
_RAIL_CATEGORIAS = (
    ("Platos", (("Composición del plato",              "Composición"),
                ("Costeo Receta Venta",                "Costeo"),
                ("Ingredientes clave",                 "Ingredientes"),
                ("Panorama de compras · platos",       "Panorama"),
                ("Tabla · platos",                     "Tabla"))),
    ("Recetas base", (("Ranking de recetas base",            "Ranking · base"),
                      ("Insumos clave · recetas base",       "Insumos · base"),
                      ("Panorama de compras · recetas base", "Panorama · base"),
                      ("Tabla · recetas base",               "Tabla · base"))),
)

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué, en `graficos/compras/__init__.py::_PILA`).
#
# Las cinco de platos van primero y las cuatro de recetas base después: se
# lee de lo vendible hacia sus componentes, que es el orden en que el
# usuario describió el dominio («los platos... formados por ingredientes e
# incluso recetas base»).
_PILA = (
    ("rec_sec_composicion",  "Composición del plato"),
    ("rec_sec_costeo",       "Costeo Receta Venta"),
    ("rec_sec_ingredientes", "Ingredientes clave"),
    ("rec_sec_panorama_rv",  "Panorama de compras · platos"),
    ("rec_sec_tabla_rv",     "Tabla · platos"),
    ("rec_sec_ranking_rb",   "Ranking de recetas base"),
    ("rec_sec_insumos_rb",   "Insumos clave · recetas base"),
    ("rec_sec_panorama_rb",  "Panorama de compras · recetas base"),
    ("rec_sec_tabla_rb",     "Tabla · recetas base"),
)


def _tabla_recetabase(df_rb):
    """La Tabla del parquet SECUNDARIO, sin pasar por `tabla_cb`.

    `app.py::_render_tabla` recorta con `_df[cols_mostrar]`, y `cols_mostrar`
    son las columnas del reporte ACTIVO (platos). Pasarle el df de recetas
    base por ahí lanzaría KeyError con las 25 columnas de recetabase.parquet.

    Reproduce lo que hacía el reporte «Receta Base» antes de la fusión: sin
    `columnas` ni `columnas_iniciales` en su cfg, `sugeridas` terminaba
    siendo TODAS las columnas en orden — o sea `cols_visibles=None`, que es
    justo el default de `renderizar_aggrid_desktop`."""
    cols = list(df_rb.columns)
    font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam"), 14)
    renderizar_aggrid_desktop(df_rb[cols], cols, "Receta Base", font_px)


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_recetas(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Recetas. `df_f` es recetaventa.parquet (PLATOS); las
    recetas base se cargan acá adentro. `df_full` se ignora (catálogo sin
    fecha).

    `tabla_cb`: callback que arma la Tabla de platos (inyectado por app.py),
    llamado con 1 argumento. La de recetas base va por `_tabla_recetabase`,
    ver el docstring del módulo."""
    # ── Columnas de PLATOS (recetaventa.parquet) ──────────────────────────
    col_plato = _resolver(df_f, ["Nomb Plato", "Nombre Plato", "PLATO", "Plato"])
    col_item = _resolver(df_f, ["Item Rv", "Item RV", "ITEM RV", "Item",
                                "Nombre Item", "Insumo", "Ingrediente",
                                "Nombre Producto"])
    col_total = _resolver(df_f, ["Total", "TOTAL", "Importe", "Costo Total",
                                 "Total Costo", "Valorizado"])
    col_cant = _resolver(df_f, ["Cantidad", "CANTIDAD", "Cant"])

    if not col_plato or not col_item or not (col_total or col_cant):
        st.warning(
            "No se reconocieron las columnas de Receta Venta (se buscó "
            "«Nomb Plato», «Item Rv», «Total», «Cantidad»). "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Columnas de RECETAS BASE (recetabase.parquet, cargado acá) ────────
    # Defensivo igual que `_cargar_flujo_compras`: si el parquet no está o
    # le faltan columnas, las cuatro secciones de recetas base avisan y el
    # resto de la página sigue funcionando.
    col_rb = col_ins = col_rb_valor = col_rb_total = None
    df_rb = _cargar_reporte("recetabase.parquet")
    if df_rb is None or df_rb.empty:
        df_rb = None
    else:
        col_rb = _resolver(df_rb, ["RB NOMBRE", "Rb Nombre", "Nombre RB"])
        col_ins = _resolver(df_rb, ["INSUMO", "Insumo"])
        col_rb_total = _resolver(df_rb, ["CST SUBT INS", "Cst Subt Ins",
                                         "Costo Subtotal Insumo"])
        col_rb_cant = _resolver(df_rb, ["CANT", "Cant", "Cantidad"])
        col_rb_valor = col_rb_total or col_rb_cant
        if not col_rb or not col_ins or not col_rb_valor:
            df_rb = None

    # El rail MARCA en cuál sección estás y scrollea; no elige contenido.
    _render_rail(_RAIL_CATEGORIAS, "rec_graf_tipo", btn_prefix="rec_rail_btn_",
                 secciones=_PILA)

    # El chip ya no separa Base/Venta — las dos están en esta página. Queda
    # como puente hacia «+ Nueva», que no es una vista sino el formulario de
    # alta (`formulario_receta.py`, `tool: True` en REPORTES).
    _chip_fuente(nombre_reporte)

    # Medir por: SIEMPRE costo, en las DOS mitades. Receta Venta ya no tenía
    # el radio (se sacó el 2026-08-30 a pedido: «por defecto siempre debe ser
    # por costo»); el `rb_metrica` que le quedaba a Receta Base se va con la
    # fusión, porque un control ARRIBA de la pila que sólo mueve 3 de las 9
    # secciones miente sobre su alcance — y meterlo adentro de una sección lo
    # escondería hasta que esa sección salga del esqueleto (CLAUDE.md § los
    # controles compartidos van arriba). Se conserva el fallback de siempre:
    # si no hubiera columna de costo, se mide en cantidad.
    es_soles = bool(col_total)
    col_valor = col_total if es_soles else col_cant
    rb_es_soles = bool(df_rb is not None and col_rb_valor == col_rb_total)

    # ── LA PILA, PEREZOSA ─────────────────────────────────────────────────
    # Cada sección con su PROPIA key de tarjeta: apiladas, compartir key es
    # una excepción de Streamlit.
    def _dib_composicion():
        with st.container(border=True, key="rec_card_composicion"):
            _tabla_composicion_venta(df_f)

    def _dib_costeo():
        with st.container(border=True, key="rec_card_costeo"):
            _tabla_costeo_venta(df_f, col_plato, col_valor, es_soles)

    def _dib_ingredientes():
        with st.container(border=True, key="rec_card_ingredientes"):
            _items_clave(df_f, col_plato, col_item, col_valor, es_soles,
                         card_key="rec_ingredientes",
                         titulo_card="Ingredientes de mayor costo total",
                         etiqueta_item="Ingrediente",
                         etiqueta_contenedor_plural="platos",
                         expander_titulo="📋 Tabla: ingredientes por costo y n.º de platos")

    def _dib_panorama_rv():
        with st.container(border=True, key="rec_card_panorama_rv"):
            _panorama_compras_venta(df_f, es_soles)

    def _dib_tabla_rv():
        with st.container(border=True, key="rec_card_tabla_rv"):
            if tabla_cb is not None:
                tabla_cb(df_f)
            else:
                st.info("La tabla no está disponible en este contexto.")

    def _sin_recetabase():
        st.info("No se pudieron cargar las recetas base "
                "(recetabase.parquet): esta sección queda vacía.")

    def _dib_ranking_rb():
        with st.container(border=True, key="rec_card_ranking_rb"):
            if df_rb is None:
                _sin_recetabase()
            else:
                _ranking_contenedores(df_rb, col_rb, col_rb_valor, rb_es_soles,
                                      key_topn="rec_ranking_rb_topn",
                                      card_key="rec_ranking_rb",
                                      titulo_card="Recetas base por costo total")

    def _dib_insumos_rb():
        with st.container(border=True, key="rec_card_insumos_rb"):
            if df_rb is None:
                _sin_recetabase()
            else:
                _items_clave(df_rb, col_rb, col_ins, col_rb_valor, rb_es_soles,
                             card_key="rec_insumos_rb",
                             titulo_card="Insumos de mayor costo total",
                             etiqueta_item="Insumo",
                             etiqueta_contenedor_plural="recetas base",
                             expander_titulo="📋 Tabla: insumos por costo y n.º de recetas")

    def _dib_panorama_rb():
        with st.container(border=True, key="rec_card_panorama_rb"):
            if df_rb is None:
                _sin_recetabase()
            else:
                _panorama_compras_base(df_rb, rb_es_soles)

    def _dib_tabla_rb():
        with st.container(border=True, key="rec_card_tabla_rb"):
            if df_rb is None:
                _sin_recetabase()
            else:
                _tabla_recetabase(df_rb)

    _DIBUJANTES = {
        "rec_sec_composicion":  _dib_composicion,
        "rec_sec_costeo":       _dib_costeo,
        "rec_sec_ingredientes": _dib_ingredientes,
        "rec_sec_panorama_rv":  _dib_panorama_rv,
        "rec_sec_tabla_rv":     _dib_tabla_rv,
        "rec_sec_ranking_rb":   _dib_ranking_rb,
        "rec_sec_insumos_rb":   _dib_insumos_rb,
        "rec_sec_panorama_rb":  _dib_panorama_rb,
        "rec_sec_tabla_rb":     _dib_tabla_rb,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje.
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
