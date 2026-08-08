"""tablas.movil - vista de tabla para movil.

Version reducida: menos columnas, columnas fijas a la izquierda y sin panel
lateral.
"""

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils import _norm, buscar_columna, LOCALE_ES
from inyecciones import inject_grid_health_check, inject_pagination_v2, inject_maximize_aggrid, inject_dynamic_grid_height, inject_fix_column_panel_ajuste
from tema import (
    ACENTO, ACENTO_FUERTE, ACENTO_TEXTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA_FONDO, ADVERTENCIA_TEXTO, BLANCO, CELDA_ALERTA_FONDO, CELDA_ALERTA_TEXTO, CELDA_NEG_FONDO, CELDA_POS_TEXTO, DANGER_TEXT, ERROR_FONDO, EXIT_HOVER, GRIS_BORDE, GRIS_FONDO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE, ICON_MUTED, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FILA, LAVANDA_FILA_ALT, LAVANDA_FOCO, LAVANDA_FONDO, LAVANDA_MEDIO, LAVANDA_SELECCION, SCROLL_THUMB, TEXTO_PRINCIPAL,
)


def renderizar_aggrid_movil(df_grid, columnas_fijas, reporte, font_px=14):
    """Renderiza la tabla AgGrid optimizada para vista móvil."""
    envolver_cabeceras = (reporte == "Inventario Valorizado")

    gb = GridOptionsBuilder.from_dataframe(df_grid)
    _opciones_col_def = dict(
        resizable=True, sortable=True, filter=True,
        editable=False, groupable=False, enableRowGroup=False,
        enablePivot=False, menuTabs=["filterMenuTab", "generalMenuTab", "columnsMenuTab"],
    )
    if envolver_cabeceras:
        _opciones_col_def["wrapHeaderText"] = True
        _opciones_col_def["autoHeaderHeight"] = True
    gb.configure_default_column(**_opciones_col_def)

    for i, col in enumerate(df_grid.columns):
        if i < columnas_fijas:
            gb.configure_column(col, pinned="left")
        if pd.api.types.is_numeric_dtype(df_grid[col]):
            af = "avg" if ("precio" in _norm(col) or "promedio" in _norm(col)) else "sum"
            gb.configure_column(col, aggFunc=af, type=["numericColumn"],
                                valueFormatter="x == null ? '' : x.toLocaleString()")

    row_h = max(28, min(60, font_px + 12))
    header_h = max(30, min(62, font_px + 14))

    opciones_grid = {
        "localeText": LOCALE_ES,
        "suppressColumnVirtualisation": True,
        "rowHeight": row_h,
        "headerHeight": header_h,
        "animateRows": False,
        "sideBar": False,
        "suppressContextMenu": False,
        "pagination": True,
        "paginationAutoPageSize": False,
        "paginationPageSize": 25,
    }

    if envolver_cabeceras:
        opciones_grid["headerHeight"] = int(font_px * 2 + 14)

    gb.configure_grid_options(**opciones_grid)
    grid_options = gb.build()

    custom_css = {
        ".ag-root-wrapper": {"background-color": f"{BLANCO}", "border": f"1px solid {GRIS_BORDE}", "border-radius": "8px", "width": "100% !important"},
        ".ag-header": {"background-color": f"{GRIS_LINEA}", "border-bottom": f"2px solid {ACENTO}"},
        ".ag-header-cell-text": {"color": f"{TEXTO_PRINCIPAL}", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": f"{EXIT_HOVER}", "border-color": f"{GRIS_BORDE}"},
        ".ag-row-even": {"background-color": f"{BLANCO}"},
        ".ag-row-odd": {"background-color": f"{GRIS_FONDO}"},
        ".ag-row-hover": {"background-color": f"{LAVANDA_FONDO} !important"},
        ".ag-cell": {"color": f"{EXIT_HOVER}", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {"color": f"{ICON_MUTED}", "background-color": f"{GRIS_FONDO}", "border-top": f"1px solid {GRIS_BORDE}", "font-size": "0.75rem"},
        ".ag-menu": {"background-color": f"{BLANCO}", "color": f"{TEXTO_PRINCIPAL}", "border": f"1px solid {GRIS_BORDE}"},
        ".ag-pinned-left-header": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
        ".ag-pinned-left-cols-container": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
    }

    if envolver_cabeceras:
        custom_css[".ag-header-cell-text"].update({
            "white-space": "normal !important",
            "overflow": "visible !important",
            "text-overflow": "clip !important",
            "line-height": "1.25 !important",
            "overflow-wrap": "break-word",
            "word-break": "normal",
            "display": "flex",
            "align-items": "center",
            "text-align": "center",
        })
        custom_css[".ag-header-cell-label"] = {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "align-items": "center",
        }

    AgGrid(
        df_grid.head(3000), gridOptions=grid_options, height=380,
        theme="balham", custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_movil_{reporte}",
    )

    # Sin cambios: móvil usa paginación nativa, usa_pagination_v2=False (default)
    inject_grid_health_check()
