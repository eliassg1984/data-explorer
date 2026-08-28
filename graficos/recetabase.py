"""
graficos.recetabase — dashboard de gráficos de Receta Base.

Cada fila de recetabase.parquet es un INSUMO de una receta base (una
subpreparación: salsas, masas, mise en place — no un plato vendido):
    RB NOMBRE · INSUMO · CANT · CST SUBT INS
    (receta base)  (insumo)  (cant.)   (costo del insumo en la receta)

Mismo esqueleto de BOM que Receta Venta (plato→insumos), por eso este
módulo es una capa FINA sobre `graficos.recetas_comun`: resuelve las
columnas reales de recetabase.parquet y llama a los gráficos compartidos
(Ranking, Insumos clave, Panorama de compras). Receta Base y Receta Venta
comparten ítem de nav ("Recetas") y un chip Base/Venta arriba del rail —
ver `_chip_fuente` en recetas_comun.py y `arquitectura.md` § Unificación
Recetas.

Sankey y Composición se dieron de baja acá el 2026-08-28, a pedido. Eran
las DOS vistas de una receta elegida a mano, así que con ellas se fueron
las dos cosas que existían sólo para alimentarlas: el selectbox "Receta
base" y el botón "Abrir Sankey →" del Panorama, que se quedaba sin destino.
Receta Venta las conserva — su "Composición" ya era otra cosa (una tabla de
TODOS los platos, `recetaventa.py::_tabla_composicion_venta`). Ver
`arquitectura.md` regla #236.

Confirmado que Receta Base NO se cruza con Receta Venta (0% overlap
`COD RB` vs `COD INS`, memoria de proyecto
`esquema-real-compras-recetaventa`): son dos catálogos de insumos
independientes que cuelgan de `compras.COD_PRODUCTO` cada uno por su lado.

OJO — activo/inactivo en formato PROPIO: `RB ACT` viene como
"RB.ACTIV"/"RB.INACT" e `INS ACTIVO` (mismo nombre de columna que en
Receta Venta) viene como "INS.ACT"/"INS.INAC" — ninguno de los dos es
"ACTIV"/"INACTIV" como en Receta Venta. Ver `_activo()` en
recetas_comun.py, que normaliza los tres formatos.

Punto de entrada público: renderizar_graficos_recetabase().
"""

import streamlit as st

from graficos.base import (
    _render_rail, _resolver, renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.recetas_comun import (
    _chip_fuente, _items_clave, _panorama_compras, _ranking_contenedores,
)

_RAIL_CATEGORIAS = (
    ("Vista", (("Ranking de recetas",  "Ranking"),
               ("Insumos clave",       "Insumos"),
               ("Panorama de compras", "Panorama"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla. El motivo de que los dos datos vivan juntos está en el comentario
# largo de `graficos/compras/__init__.py::_PILA`: el scrollspy necesita
# saber qué botón encender por cada sección, y deducirlo del nombre se
# rompe en silencio en cuanto una etiqueta trae una tilde o una ñ.
#
# Acá ninguna vista queda AFUERA de la pila (a diferencia de Compras, que
# deja "Documentos SUNAT" como destino aparte porque se lleva prestado el
# selector de fecha).
_PILA = (
    ("rb_sec_ranking",     "Ranking de recetas"),
    ("rb_sec_insumos",     "Insumos clave"),
    ("rb_sec_panorama",    "Panorama de compras"),
    ("rb_sec_tabla",       "Tabla"),
)


def _panorama_compras_base(df_f, es_soles):
    _panorama_compras(
        df_f, es_soles, key_prefix="rb",
        col_cod_ins_cand=["COD INS RB", "Cod Ins Rb"],
        col_contenedor_cand=["RB NOMBRE", "Rb Nombre", "Nombre RB"],
        col_valor_cand=["CST SUBT INS", "Cst Subt Ins"],
        col_cant_cand=["CANT", "Cant"],
        col_activo_contenedor_cand=["RB ACT", "Rb Act"],
        col_activo_item_cand=["INS ACTIVO", "Ins Activo"],
        etiqueta_otros_contenedor="Otras recetas",
        titulo_card="Productos comprados → recetas base que los usan",
        col_contenedor_out="Receta base",
        etiqueta_contenedor_plural="recetas base activas",
        # Sin `nombre_vista_sankey`/`clave_seccion_sankey`: este dashboard ya
        # no tiene Sankey, así que `_panorama_compras` se saltea el drill que
        # existía SÓLO para saltar hasta él y deja el de insumo a lo ancho.
    )


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_recetabase(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Receta Base. df_full se ignora (catálogo sin fecha).

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py), llamado
    SIN args — igual que Receta Venta: sin chips propios de filtro, la
    Tabla usa los filtros genéricos que ya arma app.py."""
    _chip_fuente("Receta Base")

    col_rb = _resolver(df_f, ["RB NOMBRE", "Rb Nombre", "Nombre RB"])
    col_ins = _resolver(df_f, ["INSUMO", "Insumo"])
    col_total = _resolver(df_f, ["CST SUBT INS", "Cst Subt Ins", "Costo Subtotal Insumo"])
    col_cant = _resolver(df_f, ["CANT", "Cant", "Cantidad"])

    # Necesitamos receta base + insumo + al menos una métrica numérica.
    if not col_rb or not col_ins or not (col_total or col_cant):
        st.warning(
            "No se reconocieron las columnas de Receta Base (se buscó "
            "«RB NOMBRE», «INSUMO», «CST SUBT INS», «CANT»). "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # El rail ya no ELIGE contenido: con `secciones` pasa a MARCAR en cuál
    # estás y a scrollear al hacer clic (ver `base.py::_render_rail`). El
    # valor que devuelve se ignora — la página dibuja las cuatro siempre.
    _render_rail(_RAIL_CATEGORIAS, "rb_graf_tipo", btn_prefix="rb_rail_btn_",
                 secciones=_PILA)

    # ── Control COMPARTIDO por toda la página ─────────────────────────────
    # Va arriba de la pila, no adentro de una sección: la métrica manda
    # sobre las tres vistas de gráfico. Meterlo en una sección lo escondería
    # hasta que esa sección salga del esqueleto.
    #
    # Al lado vivía el selectbox "Receta base" (`rb_contenedor_sel`), que se
    # fue con Sankey y Composición: eran sus únicos lectores. Las tres
    # vistas que quedan miran TODAS las recetas a la vez, así que elegir una
    # acá no cambiaba nada de lo que hay abajo.
    metricas = []
    if col_total:
        metricas.append("Costo (S/)")
    if col_cant:
        metricas.append("Cantidad")

    metrica = st.radio("Medir por", metricas, horizontal=True,
                       key="rb_metrica")
    es_soles = (metrica == "Costo (S/)")
    col_valor = col_total if es_soles else col_cant

    # ── LA PILA, PEREZOSA ─────────────────────────────────────────────────
    # Cada sección arranca en esqueleto y se construye cuando te acercás
    # (`base.py::seccion_perezosa`). Cada una lleva además su PROPIA key de
    # tarjeta: antes TODAS compartían `rb_graf_card` porque nunca
    # coexistían — apiladas, eso serían N widgets con la misma key, que en
    # Streamlit es una excepción. Es la trampa que ya documentó Compras al
    # apilarse (Volatilidad y Semanal compartían la suya).
    def _dib_ranking():
        with st.container(border=True, key="rb_card_ranking"):
            _ranking_contenedores(df_f, col_rb, col_valor, es_soles,
                                  key_topn="rb_ranking_topn",
                                  card_key="rb_ranking",
                                  titulo_card="Recetas base por costo total")

    def _dib_insumos():
        with st.container(border=True, key="rb_card_insumos"):
            _items_clave(df_f, col_rb, col_ins, col_valor, es_soles,
                        card_key="rb_insumos",
                        titulo_card="Insumos de mayor costo total",
                        etiqueta_item="Insumo",
                        etiqueta_contenedor_plural="recetas base",
                        expander_titulo="📋 Tabla: insumos por costo y n.º de recetas")

    def _dib_panorama():
        with st.container(border=True, key="rb_card_panorama"):
            _panorama_compras_base(df_f, es_soles)

    def _dib_tabla():
        with st.container(border=True, key="rb_card_tabla"):
            if tabla_cb is not None:
                tabla_cb(df_f)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "rb_sec_ranking":     _dib_ranking,
        "rb_sec_insumos":     _dib_insumos,
        "rb_sec_panorama":    _dib_panorama,
        "rb_sec_tabla":       _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje (ver el mismo bucle en
    # `graficos/compras/__init__.py`).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
