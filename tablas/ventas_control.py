"""tablas.ventas_control - la grilla de detalle de Ventas › «Control de
pedidos» (graficos/ventas_control.py, regla #594).

Una lista: los platos anulados, las transferencias, los tiempos por tamaño
de grupo o las mesas. Con el look, los formatos y la fila TOTAL fija de las
grillas del Resumen (`tablas/ventas_resumen.py`), que son las de «Compras
por período»: tablas gemelas con dos looks no se leen como la misma cosa
(regla #404). Se lee, no se clickea.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from tablas._config import _parchar_iconos
from tablas.compras_semanal import (
    _AL_MONTAR, _JS_ENTERO, _JS_SOLES, _con_total, _css, REGLAS_FILA,
)
from tablas.compras_volatilidad import ALTO_FILA
from tablas.movimientos_periodo import _JS_FECHA_HORA
from tablas.ventas_resumen import _JS_SOLES0

_JS_MINUTOS = JsCode(
    "function(p){ var v = p.value; if (typeof v === 'string') return v;"
    " if (v == null || isNaN(v)) return '—';"
    " var m = Math.round(v); if (m < 60) return m + ' min';"
    " var h = Math.floor(m / 60), r = m % 60;"
    " return h + ' h ' + (r < 10 ? '0' : '') + r; }")
"""«45 min», «1 h 33»: una duración en minutos. Viaja como número para que
la columna se ordene."""

_FORMATOS = {"soles": _JS_SOLES, "soles0": _JS_SOLES0, "entero": _JS_ENTERO,
             "hora": _JS_FECHA_HORA, "minutos": _JS_MINUTOS}


def renderizar_lista(tp, altura, key, columnas, total=None):
    """Una lista de sólo lectura con el look de las grillas de Ventas.

    `columnas`: `(campo, rótulo, tipo, ancho, tooltip)` en el orden en que
    se ven, con `tipo` uno de «texto» (se estira), «soles», «soles0»,
    «entero», «hora» (ISO «2026-09-22 14:24», que ordena bien como texto) o
    «minutos». Lo que no está en la lista viaja oculto. `total` es la fila
    TOTAL fija, con sus valores ya escritos."""
    _orden = [c[0] for c in columnas if c[0] in tp.columns]
    tp = tp[_orden + [c for c in tp.columns if c not in _orden]]
    gb = GridOptionsBuilder.from_dataframe(tp)
    gb.configure_default_column(
        resizable=False, sortable=True, filter=False, editable=False,
        suppressMovable=True, wrapHeaderText=False, autoHeaderHeight=False,
    )
    visibles = set()
    for campo, rotulo, tipo, ancho, tip in columnas:
        if campo not in tp.columns:
            continue
        visibles.add(campo)
        kw = dict(header_name=rotulo, headerTooltip=tip)
        if tipo == "texto":
            # Su ayuda es ella misma, salvo que la fila traiga una propia en
            # `__tip_<campo>` (de qué pedido a cuál, en una transferencia).
            _tip = f"__tip_{campo}"
            kw.update(minWidth=ancho,
                      tooltipField=_tip if _tip in tp.columns else campo)
        else:
            kw.update(width=ancho, minWidth=ancho, suppressSizeToFit=True,
                      valueFormatter=_FORMATOS[tipo])
            if tipo != "hora":
                kw["type"] = ["numericColumn"]
        gb.configure_column(campo, **kw)
    for col in tp.columns:
        if col not in visibles:
            gb.configure_column(col, hide=True)
    gb.configure_grid_options(**_con_total(dict(
        rowHeight=ALTO_FILA, headerHeight=32, tooltipShowDelay=200,
        suppressCellFocus=True, rowClassRules=REGLAS_FILA,
        onGridReady=_AL_MONTAR), total))
    grid_options = gb.build()
    _parchar_iconos(grid_options)  # arquitectura.md #159
    AgGrid(tp, gridOptions=grid_options, height=altura, theme="material",
           custom_css=_css(), allow_unsafe_jscode=True, key=key,
           update_on=[])
