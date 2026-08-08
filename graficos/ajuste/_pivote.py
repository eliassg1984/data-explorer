"""graficos.ajuste._pivote - tabla pivote "Por fecha de corte".

Arma la matriz Familia/Subfamilia/Producto x periodo y la renderiza.
El periodo puede ser un corte real (racha de fechas consecutivas) o un
mes/semana; el calculo vive en _comun.
"""

import datetime as _dt

import pandas as pd
import streamlit as st

from tema import (
    TEXTO_PRINCIPAL,
)
from graficos.base import (
    _card, _resolver,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.ajuste._comun import _MESES_ABR_ES, _periodo_pivote_ajuste


def _armar_tabla_pivote_ajuste(df, col_familia, col_subfamilia, col_producto,
                                col_fecha, col_ajuste, col_ajuste_val, gran,
                                anio_actual):
    """Pre-pivotea a un dataframe WIDE (una fila por Familia+Subfamilia+
    Producto, columnas numéricas ajv_i/aj_i por periodo) para que
    tablas.ajuste_pivote lo renderice con rowGroup nativo de AG Grid: el
    árbol Familia > Subfamilia > Producto y sus totales por nivel salen
    del propio grid (aggFunc="sum"), no hay que armarlos a mano como en la
    versión HTML anterior.

    Con granularidad "Mes" arma las 12 columnas del año FIJAS (Ene..Dic)
    aunque los meses futuros no tengan filas todavía, para que la forma de
    la tabla no cambie mes a mes. Con "Semana"/"Corte" solo las columnas
    que ya tienen datos — a diferencia de la versión anterior (tope de 6
    cortes por el ancho fijo en %), acá el scroll horizontal nativo de AG
    Grid banca bastantes más columnas sin achicarlas."""
    clave, etiqueta = _periodo_pivote_ajuste(df[col_fecha], gran)
    d = df.assign(_clave=clave, _etq=etiqueta)

    if gran == "Mes":
        orden = pd.DataFrame({
            "_clave": [f"{anio_actual}-{m:02d}" for m in range(1, 13)],
            "_etq": [_MESES_ABR_ES[m - 1] for m in range(1, 13)],
        })
    else:
        orden = (d[["_clave", "_etq"]].drop_duplicates()
                 .sort_values("_clave").reset_index(drop=True))
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
    for i, fila in orden.iterrows():
        clave_i, etq_i = fila["_clave"], fila["_etq"]
        f_ajv = f"ajv_{i}"
        wide[f_ajv] = piv_ajv[clave_i] if clave_i in piv_ajv.columns else 0.0
        f_aj = None
        if _tiene_aj:
            f_aj = f"aj_{i}"
            wide[f_aj] = piv_aj[clave_i] if clave_i in piv_aj.columns else 0.0
        periodos.append({"field_ajv": f_ajv, "field_aj": f_aj, "label": etq_i})

    wide["tot_ajv"] = wide[[p["field_ajv"] for p in periodos]].sum(axis=1)
    if _tiene_aj:
        wide["tot_aj"] = wide[[p["field_aj"] for p in periodos]].sum(axis=1)
    return wide.reset_index(), periodos


def _tabla_pivote_fecha_ajuste(df, col_familia, col_ajuste_val, col_producto,
                                col_ajuste, col_fecha, col_area=None,
                                area_sel=None, fam_sel=None):
    """Tabla dinámica de Ajuste — AgGrid real (no HTML a mano): Familia >
    Subfamilia > Producto como árbol nativo (expandir/colapsar de AG Grid),
    columnas por periodo (Corte/Semana/Mes) con Ajuste Valorizado + Ajuste
    combinados en una celda compacta (tablas/ajuste_pivote.py). "Corte"
    reemplaza a un antiguo "Día" calendario: agrupa por rachas de días con
    movimiento (`_cortes_por_racha`) porque una sesión real de conteo
    puede durar varios días, no necesariamente uno solo.

    Ignora a propósito el rango de fecha de la franja superior: siempre
    parte del año EN CURSO completo, con el mismo patrón que la rama
    "Histórico" de renderizar_graficos_ajuste (unas líneas más abajo) —
    el pedido fue "mostrar por defecto toda la información del año en
    curso" sin depender de qué rango haya elegido el usuario para
    Evolución/Comparativa (categoría de rango compartida, ver
    categoria_rango_ajuste). Por eso recibe `df` SIN filtrar por fecha
    (df_full, no el `d` ya acotado por la franja superior); los chips de
    Área/Familia sí se reaplican acá porque son propios de esta vista.

    Ya no arma el árbol a mano ni compara cada columna con la anterior: la
    flecha de tendencia de la versión vieja se pierde a propósito — un
    pivote de verdad agrega por columna, no compara vecinas (ver
    arquitectura.md, reemplazo de la regla #25)."""
    if not (col_familia and col_fecha and col_producto and col_ajuste_val):
        st.info("Se necesita familia, fecha, producto y ajuste valorizado "
                "para la tabla dinámica.")
        return

    col_subfamilia = _resolver(df, ["Subfamilia", "Nombre Subfamilia"])
    anio_actual = _dt.date.today().year

    d = df.copy()
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d[d[col_fecha].dt.year == anio_actual]
    if area_sel and col_area and col_area in d.columns:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_familia and col_familia in d.columns:
        d = d[d[col_familia].astype(str).isin(fam_sel)]

    _req = [col_fecha, col_familia, col_producto] + (
        [col_subfamilia] if col_subfamilia and col_subfamilia in d.columns
        else [])
    d = d.dropna(subset=_req)

    with _card("pivote_fecha"):
        st.markdown(
            f"<div style='font-size:14px;font-weight:500;"
            f"color:{TEXTO_PRINCIPAL};margin-bottom:2px'>"
            f"Ajuste por fecha — año {anio_actual}</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"Año {anio_actual} completo — no depende del rango de fecha "
            f"de arriba. Los periodos futuros aparecen vacíos."
        )
        gran = st.pills("Agrupar columnas por", ["Corte", "Semana", "Mes"],
                        default="Mes", key="ajuste_pivote_gran") or "Mes"

        if d.empty:
            st.info(f"Sin datos de {anio_actual} para la tabla dinámica.")
            return

        _sub = (col_subfamilia
                if col_subfamilia and col_subfamilia in d.columns else None)
        wide, periodos = _armar_tabla_pivote_ajuste(
            d, col_familia, _sub, col_producto, col_fecha, col_ajuste,
            col_ajuste_val, gran, anio_actual,
        )
        if wide is None or wide.empty:
            st.info(f"Sin datos de {anio_actual} para la tabla dinámica.")
            return

        from tablas import renderizar_aggrid_pivote_ajuste
        renderizar_aggrid_pivote_ajuste(
            wide, periodos, col_familia, _sub, col_producto,
            anio=anio_actual,
        )
