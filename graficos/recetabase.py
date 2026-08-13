"""
graficos.recetabase — dashboard de gráficos de Receta Base.

Cada fila de recetabase.parquet es un INSUMO de una receta base (una
subpreparación: salsas, masas, mise en place — no un plato vendido):
    RB NOMBRE · INSUMO · CANT · CST SUBT INS
    (receta base)  (insumo)  (cant.)   (costo del insumo en la receta)

Mismo esqueleto de BOM que Receta Venta (plato→insumos), por eso este
módulo es una capa FINA sobre `graficos.recetas_comun`: resuelve las
columnas reales de recetabase.parquet y llama a los 5 gráficos compartidos
(Sankey, Composición, Ranking, Insumos clave, Panorama de compras). Receta
Base y Receta Venta comparten ítem de nav ("Recetas") y un chip Base/Venta
arriba del rail — ver `_chip_fuente` en recetas_comun.py y
`arquitectura.md` § Unificación Recetas.

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

from graficos.base import _render_rail, _resolver, renderizar_graficos_genericos
from graficos.recetas_comun import (
    _chip_fuente, _composicion_contenedor, _items_clave, _panorama_compras,
    _ranking_contenedores, _sankey_contenedor,
)

_RAIL_CATEGORIAS = (
    ("Vista", (("Sankey por receta",         "Sankey"),
               ("Composición de la receta",  "Composición"),
               ("Ranking de recetas",        "Ranking"),
               ("Insumos clave",             "Insumos"),
               ("Panorama de compras",       "Panorama"))),
    ("Datos", (("Tabla", "Tabla"),)),
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
        state_key_rail="rb_graf_tipo",
        nombre_vista_sankey="Sankey por receta",
        col_contenedor_out="Receta base",
        etiqueta_contenedor_plural="recetas base activas",
        etiqueta_selectbox_jump="Ver el flujo completo de una receta",
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

    graf = _render_rail(_RAIL_CATEGORIAS, "rb_graf_tipo", btn_prefix="rb_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            tabla_cb(df_f)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    # ── Métrica del ancho/valor: Costo o Cantidad ─────────────────────────
    metricas = []
    if col_total:
        metricas.append("Costo (S/)")
    if col_cant:
        metricas.append("Cantidad")

    c_met, c_rb = st.columns([1, 2])
    with c_met:
        metrica = st.radio("Medir por", metricas, horizontal=True,
                           key="rb_metrica")
    es_soles = (metrica == "Costo (S/)")
    col_valor = col_total if es_soles else col_cant

    # ── Selector de receta base (compartido por Sankey y Composición) ────
    # Default: la de mayor costo, para que la primera vista sea rica.
    recetas = sorted(df_f[col_rb].dropna().astype(str).unique().tolist())
    totales = df_f.groupby(col_rb)[col_valor].sum()
    receta_rica = str(totales.idxmax()) if not totales.empty else (recetas[0] if recetas else "")
    idx_def = recetas.index(receta_rica) if receta_rica in recetas else 0

    # Mismo patrón que Receta Venta: `with c_rb:` se entra SIEMPRE (el if va
    # adentro) para que Streamlit "visite" la posición en todos los runs y
    # no deje un selectbox huérfano al cambiar de vista (arquitectura.md,
    # nota de graficos/recetaventa.py).
    contenedor = None
    with c_rb:
        if graf in ("Sankey por receta", "Composición de la receta"):
            contenedor = st.selectbox("Receta base", recetas, index=idx_def,
                                      key="rb_contenedor_sel")

    with st.container(border=True, key="rb_graf_card"):
        # Sub-container con key que VARÍA POR VISTA: fuerza un remount
        # limpio en vez de acumular widgets de la vista anterior debajo de
        # la nueva (mismo motivo que Receta Venta).
        with st.container(key=f"rb_graf_body_{graf.lower().replace(' ', '_')}"):
            if graf == "Sankey por receta":
                _sankey_contenedor(df_f, col_rb, col_ins, col_valor, contenedor,
                                   es_soles, card_key="rb_sankey")
            elif graf == "Composición de la receta":
                _composicion_contenedor(df_f, col_rb, col_ins, col_valor, contenedor,
                                        es_soles, card_key="rb_dona")
            elif graf == "Ranking de recetas":
                _ranking_contenedores(df_f, col_rb, col_valor, es_soles,
                                      key_topn="rb_ranking_topn",
                                      card_key="rb_ranking",
                                      titulo_card="Recetas base por costo total")
            elif graf == "Insumos clave":
                _items_clave(df_f, col_rb, col_ins, col_valor, es_soles,
                            card_key="rb_insumos",
                            titulo_card="Insumos de mayor costo total",
                            etiqueta_item="Insumo",
                            etiqueta_contenedor_plural="recetas base",
                            expander_titulo="📋 Tabla: insumos por costo y n.º de recetas")
            elif graf == "Panorama de compras":
                _panorama_compras_base(df_f, es_soles)
