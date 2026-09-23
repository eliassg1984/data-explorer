"""graficos.ajuste._pivote - la tabla pivote de la vista Evolucion.

Arma la matriz Familia/Subfamilia/Producto x periodo y la renderiza. Los
periodos NO se calculan aca: llegan hechos desde `_evolucion.py`
(`periodos_ajuste`), los MISMOS que dibuja la serie de arriba — que la
tabla y el grafico partan el tiempo con dos cuentas distintas es justo lo
que la fusion del 2026-09-23 vino a evitar (regla #501).

Hasta esa fecha era la vista suelta «Por fecha de corte», con el año en
curso FIJO (ignoraba el rango de la franja) y los doce meses Ene..Dic
siempre dibujados. El año fijo existia porque la categoria Tiempo abria
con el MES en curso, y una tabla por periodos con un solo mes no dice
nada; ahora la categoria abre en los ultimos 12 meses y la tabla sigue al
rango como todo lo demas.
"""

import pandas as pd
import streamlit as st

from graficos.base import _resolver


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
                                col_producto, col_ajuste, foco=None):
    """Tabla dinámica de Ajuste — AgGrid real (no HTML a mano): Familia >
    Subfamilia > Producto como árbol nativo (expandir/colapsar de AG Grid),
    una columna por periodo con Ajuste Valorizado + Ajuste combinados en una
    celda compacta (tablas/ajuste_pivote.py).

    `d` y `orden` salen de `_evolucion.periodos_ajuste`: mismo rango (el de
    la franja), mismos chips y mismos periodos que la serie de arriba.
    `foco` es la `_clave` del periodo que se marcó con un clic en la serie:
    su columna sale resaltada y la grilla la trae a la vista."""
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
        wide, periodos, col_familia, _sub, col_producto, foco=foco,
    )
