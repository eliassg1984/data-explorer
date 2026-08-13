"""
graficos.recetaventa — dashboard de gráficos de Receta Venta.

Cada fila de recetaventa.parquet es un ÍTEM de un plato:
    Nomb Plato · Item Rv · Cantidad · Total
    (plato)      (insumo)  (cant.)    (costo del insumo en el plato)

Este módulo es la capa FINA de Receta Venta: resuelve las columnas reales
del parquet y llama a los 5 gráficos compartidos de `graficos.recetas_comun`
(Sankey, Composición, Ranking, Ingredientes clave, Panorama de compras) —
cada uno vive ahí UNA sola vez, junto con la versión de `recetabase.py` (el
mismo tipo de dato: un BOM plato→insumos vs. receta base→insumos). Desde
2026-08-13 Receta Base y Receta Venta comparten ítem de nav ("Recetas") y
un chip Base/Venta arriba del rail — ver `_chip_fuente` en recetas_comun.py
y `arquitectura.md` § Unificación Recetas.

Punto de entrada público: renderizar_graficos_recetaventa().
"""

import streamlit as st

from graficos.base import _render_rail, _resolver, renderizar_graficos_genericos
from graficos.recetas_comun import (
    _chip_fuente, _composicion_contenedor, _items_clave, _panorama_compras,
    _ranking_contenedores, _sankey_contenedor,
)

_RAIL_CATEGORIAS = (
    ("Vista", (("Sankey por plato",        "Sankey"),
               ("Composición del plato",   "Composición"),
               ("Ranking de platos",       "Ranking"),
               ("Ingredientes clave",      "Ingredientes"),
               ("Panorama de compras",     "Panorama"))),
    ("Datos", (("Tabla", "Tabla"),)),
)


def _panorama_compras_venta(df_f, es_soles):
    _panorama_compras(
        df_f, es_soles, key_prefix="rv",
        col_cod_ins_cand=["COD INS", "Cod Ins"],
        col_contenedor_cand=["Nomb Plato", "Nombre Plato", "PLATO", "Plato"],
        col_valor_cand=["Total", "TOTAL", "Importe", "Costo Total"],
        col_cant_cand=["Cantidad", "CANTIDAD", "Cant"],
        col_activo_contenedor_cand=["ITEM VENTA ACTIVO", "Item Venta Activo"],
        col_activo_item_cand=["INS ACTIVO", "Ins Activo"],
        etiqueta_otros_contenedor="Otros platos",
        titulo_card="Productos comprados → platos que los usan",
        state_key_rail="rv_graf_tipo",
        nombre_vista_sankey="Sankey por plato",
        col_contenedor_out="Plato",
        etiqueta_contenedor_plural="platos activos",
        etiqueta_selectbox_jump="Ver el flujo completo de un plato",
    )


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_recetaventa(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Receta Venta. df_full se ignora (catálogo sin fecha).

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py), llamado
    SIN args — igual que Ajuste: este dashboard no tiene chips propios de
    filtro (a diferencia de Ventas/Inventario), así que la Tabla usa los
    filtros genéricos que ya arma app.py."""
    _chip_fuente("Receta Venta")

    col_plato = _resolver(df_f, ["Nomb Plato", "Nombre Plato", "PLATO", "Plato"])
    col_item = _resolver(df_f, ["Item Rv", "Item RV", "ITEM RV", "Item",
                                "Nombre Item", "Insumo", "Ingrediente",
                                "Nombre Producto"])
    col_total = _resolver(df_f, ["Total", "TOTAL", "Importe", "Costo Total",
                                 "Total Costo", "Valorizado"])
    col_cant = _resolver(df_f, ["Cantidad", "CANTIDAD", "Cant"])

    # Necesitamos plato + ítem + al menos una métrica numérica.
    if not col_plato or not col_item or not (col_total or col_cant):
        st.warning(
            "No se reconocieron las columnas de Receta Venta (se buscó "
            "«Nomb Plato», «Item Rv», «Total», «Cantidad»). "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    graf = _render_rail(_RAIL_CATEGORIAS, "rv_graf_tipo", btn_prefix="rv_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            # Sin chips propios (como Ajuste): pasa su df tal cual.
            tabla_cb(df_f)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    # ── Métrica del ancho/valor: Total (costo) o Cantidad ────────────────
    metricas = []
    if col_total:
        metricas.append("Costo (S/)")
    if col_cant:
        metricas.append("Cantidad")

    c_met, c_plato = st.columns([1, 2])
    with c_met:
        metrica = st.radio("Medir por", metricas, horizontal=True,
                           key="rv_metrica")
    es_soles = (metrica == "Costo (S/)")
    col_valor = col_total if es_soles else col_cant

    # ── Selector de plato (compartido por Sankey y Composición) ──────────
    # Default: el plato de mayor costo, para que la primera vista sea rica.
    platos = sorted(df_f[col_plato].dropna().astype(str).unique().tolist())
    totales = df_f.groupby(col_plato)[col_valor].sum()
    plato_rico = str(totales.idxmax()) if not totales.empty else (platos[0] if platos else "")
    idx_def = platos.index(plato_rico) if plato_rico in platos else 0

    # El selector de plato solo aparece para las vistas por plato — pero
    # `with c_plato:` se entra SIEMPRE (el if va adentro, no afuera). Si el
    # if envuelve el `with`, en los runs donde no aplica Streamlit nunca
    # "visita" esa posición del árbol y no la limpia: el selectbox de la
    # vista anterior queda pegado (visto en vivo 2026-08-09 cambiando de
    # Sankey a Ranking — el combo "Plato" seguía ahí, funcional pero
    # huérfano). Entrar siempre y decidir adentro fuerza a Streamlit a
    # registrar la posición vacía y limpiarla.
    plato = None
    with c_plato:
        if graf in ("Sankey por plato", "Composición del plato"):
            plato = st.selectbox("Plato", platos, index=idx_def, key="rv_plato_sel")

    with st.container(border=True, key="rv_graf_card"):
        # Mismo problema, mismo motivo: sub-container CON KEY QUE VARÍA POR
        # VISTA (no un key fijo) para que cambiar de rail fuerce un remount
        # limpio en vez de acumular widgets de la vista anterior debajo de
        # la nueva (le pasó a _panorama_compras: sus selectbox de drill
        # aparecían también en Ranking). Mismo espíritu que el contador de
        # remount de arquitectura.md regla #9, aplicado al nombre del graf
        # en vez de a un contador de aperturas.
        with st.container(key=f"rv_graf_body_{graf.lower().replace(' ', '_')}"):
            if graf == "Sankey por plato":
                _sankey_contenedor(df_f, col_plato, col_item, col_valor, plato,
                                   es_soles, card_key="rv_sankey")
            elif graf == "Composición del plato":
                _composicion_contenedor(df_f, col_plato, col_item, col_valor, plato,
                                        es_soles, card_key="rv_dona")
            elif graf == "Ranking de platos":
                _ranking_contenedores(df_f, col_plato, col_valor, es_soles,
                                      key_topn="rv_ranking_topn",
                                      card_key="rv_ranking",
                                      titulo_card="Platos por costo total")
            elif graf == "Ingredientes clave":
                _items_clave(df_f, col_plato, col_item, col_valor, es_soles,
                            card_key="rv_ingredientes",
                            titulo_card="Ingredientes de mayor costo total",
                            etiqueta_item="Ingrediente",
                            etiqueta_contenedor_plural="platos",
                            expander_titulo="📋 Tabla: ingredientes por costo y n.º de platos")
            elif graf == "Panorama de compras":
                _panorama_compras_venta(df_f, es_soles)
