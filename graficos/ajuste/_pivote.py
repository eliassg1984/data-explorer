"""graficos.ajuste._pivote - la vista «Detalle por producto» de Ajuste.

Arma la matriz Familia/Subfamilia/Producto x periodo y la renderiza. Los
periodos salen de `_evolucion.periodos_ajuste`, la MISMA cuenta que usa la
serie de Evolucion: que la tabla y el grafico partan el tiempo con dos
cuentas distintas es justo lo que la fusion del 2026-09-23 vino a evitar
(regla #501). El mismo dia la tabla dejo de vivir debajo de la serie y
paso a ser su propio item del rail, con su propio grano (regla #504).

Hasta esa fecha era la vista suelta «Por fecha de corte», con el año en
curso FIJO (ignoraba el rango de la franja) y los doce meses Ene..Dic
siempre dibujados. El año fijo existia porque la categoria Tiempo abria
con el MES en curso, y una tabla por periodos con un solo mes no dice
nada; ahora la categoria abre en los ultimos 12 meses y la tabla sigue al
rango como todo lo demas.
"""

import pandas as pd
import streamlit as st

from tema import GRIS_TEXTO, TEXTO_PRINCIPAL
from graficos.base import _resolver
from graficos.ajuste._comun import css_filtros_vista, filtro_area_en_titulo
from graficos.ajuste._evolucion import GRANOS, periodos_ajuste


def _armar_tabla_pivote_ajuste(d, orden, col_familia, col_subfamilia,
                                col_producto, col_ajuste, col_ajuste_val):
    """Pre-pivotea a un dataframe WIDE (una fila por Familia+Subfamilia+
    Producto, columnas numéricas ajv_i/aj_i por periodo) para que
    tablas.ajuste_pivote lo renderice con rowGroup nativo de AG Grid: el
    árbol Familia > Subfamilia > Producto y sus totales por nivel salen
    del propio grid (aggFunc="sum"), no hay que armarlos a mano.

    `d` trae la columna `_clave` y `orden` la lista de periodos en el orden
    en que se dibujan (ver `_evolucion.periodos_ajuste`), incluidos los
    meses sin conteo: la columna sale vacía, que es lo que pasó."""
    if orden.empty:
        return None, []

    grupo_cols = [col_familia] + (
        [col_subfamilia] if col_subfamilia else []) + [col_producto]
    piv_ajv = d.pivot_table(index=grupo_cols, columns="_clave",
                            values=col_ajuste_val, aggfunc="sum",
                            fill_value=0.0)
    _tiene_aj = bool(col_ajuste and col_ajuste in d.columns)
    piv_aj = (d.pivot_table(index=grupo_cols, columns="_clave",
                            values=col_ajuste, aggfunc="sum", fill_value=0.0)
              if _tiene_aj else None)

    wide = pd.DataFrame(index=piv_ajv.index)
    periodos = []
    for i, fila in orden.reset_index(drop=True).iterrows():
        clave_i = fila["_clave"]
        f_ajv = f"ajv_{i}"
        wide[f_ajv] = piv_ajv[clave_i] if clave_i in piv_ajv.columns else 0.0
        f_aj = None
        if _tiene_aj:
            f_aj = f"aj_{i}"
            wide[f_aj] = piv_aj[clave_i] if clave_i in piv_aj.columns else 0.0
        periodos.append({"field_ajv": f_ajv, "field_aj": f_aj,
                         "label": fila["etq"], "anio": int(fila["anio"]),
                         "clave": clave_i})

    wide["tot_ajv"] = wide[[p["field_ajv"] for p in periodos]].sum(axis=1)
    if _tiene_aj:
        wide["tot_aj"] = wide[[p["field_aj"] for p in periodos]].sum(axis=1)
    return wide.reset_index(), periodos


def _tabla_pivote_fecha_ajuste(d, orden, col_familia, col_ajuste_val,
                                col_producto, col_ajuste):
    """Tabla dinámica de Ajuste — AgGrid real (no HTML a mano): Familia >
    Subfamilia > Producto como árbol nativo (expandir/colapsar de AG Grid),
    una columna por periodo con Ajuste Valorizado + Ajuste combinados en una
    celda compacta (tablas/ajuste_pivote.py).

    `d` y `orden` salen de `_evolucion.periodos_ajuste`: mismo rango (el de
    la franja) y mismos chips que la serie de Evolución."""
    if not (col_familia and col_producto and col_ajuste_val):
        st.info("Se necesita familia, producto y ajuste valorizado "
                "para la tabla dinámica.")
        return

    col_subfamilia = _resolver(d, ["Subfamilia", "Nombre Subfamilia"])
    _req = [col_familia, col_producto] + (
        [col_subfamilia] if col_subfamilia and col_subfamilia in d.columns
        else [])
    d = d.dropna(subset=_req)
    if d.empty:
        st.info("Sin datos para la tabla dinámica en este rango.")
        return

    _sub = (col_subfamilia
            if col_subfamilia and col_subfamilia in d.columns else None)
    wide, periodos = _armar_tabla_pivote_ajuste(
        d, orden, col_familia, _sub, col_producto, col_ajuste, col_ajuste_val,
    )
    if wide is None or wide.empty:
        st.info("Sin datos para la tabla dinámica en este rango.")
        return

    from tablas import renderizar_aggrid_pivote_ajuste
    renderizar_aggrid_pivote_ajuste(
        wide, periodos, col_familia, _sub, col_producto,
    )


# Grano propio de esta vista: desde que la tabla es su propia vista ya no
# lo comparte con la serie (regla #504).
_K_GRAN_DETALLE = "ajuste_det_gran"
# Y área propia, en la fila del título como Evolución (regla #505).
_K_AREA_DETALLE = "ajuste_det_filtro_area"


def vista_detalle_ajuste(d, col_fecha, col_familia, col_area, col_ajuste_val,
                         col_producto, col_cantidad):
    """«Detalle por producto»: la tabla pivote en su propia tarjeta, con su
    área y su selector Corte / Semana / Mes en la cabecera. Misma categoría
    del rail que Evolución, así que el mismo rango de la franja y la misma
    Familia del compartimento de arriba."""
    if not col_fecha or col_fecha not in d.columns:
        st.info("Sin columna de fecha: no se puede armar el detalle.")
        return
    st.markdown(f"<style>{css_filtros_vista('ajdet_ctrl_', 'ajdet_corte_')}"
                "</style>", unsafe_allow_html=True)
    with st.container(border=True, key="ajuste_graf_card_izq_detalle"):
        c_tit, c_area, c_gran = st.columns(
            [3, 0.95, 1.1],  # columnas-internas: titulo | area | grano
            vertical_alignment="center")
        with c_gran:
            gran = st.segmented_control(
                "Agrupar columnas por", GRANOS, default="Mes",
                key=_K_GRAN_DETALLE, label_visibility="collapsed",
                help="Una columna por período. «Corte» es cada sesión de "
                     "inventario.",
            ) or "Mes"
        d = filtro_area_en_titulo(c_area, d, col_area, col_ajuste_val,
                                  _K_AREA_DETALLE, "ajdet_ctrl_area")
        with c_tit:
            st.markdown(
                f"<div style='font-size:14px;font-weight:600;"
                f"color:{TEXTO_PRINCIPAL};line-height:1.3'>Detalle por producto"
                f"<span style='font-weight:400;color:{GRIS_TEXTO};"
                f"font-size:12px'> · S/ arriba, cantidad abajo</span></div>",
                unsafe_allow_html=True,
            )
        dp, orden = periodos_ajuste(d, col_fecha, gran)
        if orden.empty:
            st.info("Sin fechas válidas en el rango seleccionado.")
            return
        _tabla_pivote_fecha_ajuste(dp, orden, col_familia, col_ajuste_val,
                                   col_producto, col_cantidad)
