"""graficos.ajuste._comun - helpers compartidos del dashboard de Ajuste.

Layout propio del rail, formato de fechas de corte y calculo de periodos.
Lo que usan dos o mas vistas del dashboard; nada de esto dibuja nada por
si solo.

Los "cortes" NO son calendario fijo: son rachas de fechas consecutivas
(ver cortes.py en la raiz), porque un inventario se abre y se cierra en
dias sueltos. De ahi que tengan su propio calculo en vez de reusar
_periodo_serie de compras.

El calculo de cortes YA NO VIVE ACA: subio a `cortes.py` (raiz) el
2026-08-09, cuando el corte paso a ser tambien un modo del calendario de
la franja (app.py, generico a los 8 reportes). Este modulo lo reexporta
con los nombres privados de siempre para no tocar a sus consumidores.
"""


import pandas as pd

# Reexports del modulo de raiz. NO son imports muertos: los consumen
#   _MESES_ABR_ES      -> _pivote.py (cabeceras de mes) y _fmt_corte de acá
#   _cortes_por_racha  -> _heatmap.py (slider de corte) y _periodo_pivote_ajuste
#   _etiqueta_corte / _CORTE_MAX_SALTO_DIAS -> nadie hoy, pero son la pareja
#     del mismo concepto y separarlos obliga a recordar dos rutas de import.
# Sin el noqa + este comentario, `ruff check --fix` los borra y rompe a sus
# importadores (ver arquitectura.md regla #53).
from cortes import (  # noqa: F401
    CORTE_MAX_SALTO_DIAS as _CORTE_MAX_SALTO_DIAS,
    MESES_ABR_ES as _MESES_ABR_ES,
    cortes_por_racha as _cortes_por_racha,
    etiqueta_corte as _etiqueta_corte,
)
from graficos.base import (
    _layout,
)
# _periodo_serie vive en graficos/compras/_comun.py; se reusa desde acá vía
# graficos.compras (que ya la re-exporta para test_graficos.py) en vez de
# duplicar el cálculo de granularidad Semana/Mes (Corte tiene su propio
# cálculo, ver _cortes_por_racha: no es calendario fijo, son rachas).
from graficos.compras import _periodo_serie


def _layout_aj(**overrides):
    """`_layout` con el look del estándar del rail (igual que Compras).

    Solo cambia dos cosas respecto al `_layout` genérico para que los gráficos
    de Ajuste combinen con la tarjeta como en Compras:
      · plot_bgcolor TRANSPARENTE — funde con el fondo de la tarjeta en vez de
        pintar una caja blanca dentro.
      · grilla del eje X oculta (Compras solo conserva la del eje Y).
    La paleta ya es común (PALETA_SERIES). El color SEMÁNTICO de cada gráfico
    (verde/rojo del waterfall, colorscale del mapa de calor, etc.) se conserva:
    es propio del tipo de gráfico, no del tema. No se toca el `_layout`
    compartido para no restilizar Ventas/Inventario/Receta."""
    lay = _layout(**overrides)
    lay["plot_bgcolor"] = "rgba(0,0,0,0)"
    _xaxis = dict(lay.get("xaxis", {}))
    _xaxis["showgrid"] = False
    lay["xaxis"] = _xaxis
    return lay


def _fmt_corte(fecha):
    """'02-ago' en vez de '02-Aug' — strftime('%b') usa el locale del
    sistema (inglés en Streamlit Cloud), y esta app es en español."""
    _ts = pd.Timestamp(fecha)
    return f"{_ts.day:02d}-{_MESES_ABR_ES[_ts.month - 1]}"


def _periodo_pivote_ajuste(fechas, gran):
    """Clave ordenable + etiqueta corta de periodo para la tabla dinámica
    de Ajuste, en las 3 granularidades del selector (Corte/Semana/Mes).
    Corte agrupa por rachas de días (`_cortes_por_racha`); Semana/Mes
    reusan `_periodo_serie` (graficos/compras/_comun.py, re-exportada vía
    graficos.compras — "reusar desde ahí, no duplicar" per
    arquitectura.md) para la clave, con etiqueta propia porque acá el mes
    va abreviado en español (_MESES_ABR_ES)."""
    if gran == "Corte":
        return _cortes_por_racha(fechas)
    clave = _periodo_serie(fechas, gran)
    if gran == "Semana":
        etiqueta = "S" + fechas.dt.isocalendar().week.astype(str).str.zfill(2)
    else:
        etiqueta = fechas.dt.month.map(lambda m: _MESES_ABR_ES[m - 1])
    return clave, etiqueta
