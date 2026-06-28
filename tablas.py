"""
Tablas AgGrid (vista desktop y móvil) con formato financiero, totales
al pie, panel lateral de columnas y barra de paginación.
También incluye la tabla de Compras basada en st.data_editor.
"""

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils import _norm, buscar_columna, buscar_columna_fecha, LOCALE_ES
from inyecciones import inject_grid_health_check, inject_pagination_v2, inject_maximize_aggrid


# ===========================================================================
# FUNCIÓN: AGGRID DESKTOP — con formato financiero y diseño mejorado
# ===========================================================================

def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px=14, cols_visibles=None):
    """Renderiza la tabla AgGrid en vista desktop con formato financiero y diseño premium.

    cols_visibles: lista de columnas que arrancan VISIBLES. El resto se oculta
    por defecto y el usuario las activa desde la barra lateral (panel "Columnas").
    Si es None, se muestran todas.
    """

    envolver_cabeceras = (reporte == "Inventario Valorizado")
    quitar_fondos = (reporte == "Inventario Valorizado")
    es_inventario = (reporte == "Inventario Valorizado")
    es_salidas = (reporte == "Salidas")
    es_requerimientos = (reporte == "Requerimientos")
    es_pivotable = reporte in ("Requerimientos", "Ajuste de Inventario")

    # ───────────────────────────────────────────────────────────────────
    # REORDENAR COLUMNAS (Producto, Stock, Precio, Valorizado)
    # ───────────────────────────────────────────────────────────────────
    col_producto   = buscar_columna(df_grid, "Nombre Producto", "producto", "descripcion")
    col_stock      = buscar_columna(df_grid, "Stock al dia", "Stock al Dia", "stock")
    col_precio_ord = buscar_columna(df_grid, "Precio Promedio", "precio promedio", "precio")
    col_valorizado = buscar_columna(df_grid, "Valorizado total", "valorizado")

    prioridad = []
    for c in (col_producto, col_stock, col_precio_ord, col_valorizado):
        if c and c in df_grid.columns and c not in prioridad:
            prioridad.append(c)
    if prioridad:
        resto = [c for c in df_grid.columns if c not in prioridad]
        df_grid = df_grid[prioridad + resto]

    max_valorizado = 1.0
    if col_valorizado and col_valorizado in df_grid.columns:
        try:
            m = float(df_grid[col_valorizado].max())
            if m > 0:
                max_valorizado = m
        except Exception:
            pass

    gb = GridOptionsBuilder.from_dataframe(df_grid)
    _opciones_col_def = dict(
        resizable=True, filter=True, sortable=True,
        editable=False, enableRowGroup=True,
        enablePivot=True, enableValue=True,
        minWidth=100,
        tooltipValueGetter=JsCode("function(params){ return params.value; }"),
    )
    if envolver_cabeceras:
        _opciones_col_def["wrapHeaderText"] = True
        _opciones_col_def["autoHeaderHeight"] = True
    gb.configure_default_column(**_opciones_col_def)

    mono_style = JsCode("""
        function(params) {
            return { fontFamily: "'Courier New', Courier, monospace" };
        }
    """)

    stock_cell_style = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined) return {};
            if (params.node && params.node.rowPinned) {
                return { fontWeight: '700', color: '#1e3a5f' };
            }
            var v = Number(params.value);
            var base = {
                fontFamily: "'Courier New', Courier, monospace",
                fontWeight: '700',
                textAlign: 'right',
                padding: '2px 10px'
            };
            if (v < 0) {
                return Object.assign({}, base, {
                    backgroundColor: '#fee2e2',
                    color: '#991b1b',
                    borderRadius: '20px'
                });
            }
            if (v === 0) {
                return Object.assign({}, base, {
                    backgroundColor: '#fef3c7',
                    color: '#92400e',
                    borderRadius: '20px'
                });
            }
            if (v < 10) {
                return Object.assign({}, base, {
                    backgroundColor: '#ffedd5',
                    color: '#9a3412',
                    borderRadius: '20px'
                });
            }
            return Object.assign({}, base, { color: '#065f46' });
        }
    """)

    stock_cell_style_plano = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined) return {};
            if (params.node && params.node.rowPinned) {
                return { fontWeight: '700', color: '#1e3a5f' };
            }
            return {
                fontFamily: "'Courier New', Courier, monospace",
                fontWeight: '700',
                textAlign: 'right',
                padding: '2px 10px',
                color: '#1e293b'
            };
        }
    """)

    valorizado_bar_style = JsCode(f"""
        function(params) {{
            var base = {{
                fontFamily: "'Courier New', Courier, monospace",
                color: '#1e3a5f',
                fontWeight: '600',
                textAlign: 'right',
                paddingRight: '12px'
            }};
            if (params.value === null || params.value === undefined) {{
                return base;
            }}
            if (params.node && (params.node.group || params.node.rowPinned)) {{
                return Object.assign({{}}, base, {{ fontWeight: '800' }});
            }}
            var maxv = {max_valorizado};
            var num = Number(params.value);
            if (isNaN(num)) return base;
            var pct = maxv > 0 ? Math.max(0, Math.min(100, (num / maxv) * 100)) : 0;
            return Object.assign({{}}, base, {{
                backgroundImage: 'linear-gradient(to right, #bfdbfe 0%, #bfdbfe ' + pct + '%, transparent ' + pct + '%, transparent 100%)',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '100% 80%',
                backgroundPosition: 'left center'
            }});
        }}
    """)

    valorizado_plano = JsCode("""
        function(params) {
            var base = {
                fontFamily: "'Courier New', Courier, monospace",
                color: '#1e3a5f',
                fontWeight: '600',
                textAlign: 'right',
                paddingRight: '12px'
            };
            if (params.node && (params.node.group || params.node.rowPinned)) {
                return Object.assign({}, base, { fontWeight: '800' });
            }
            return base;
        }
    """)

    _stock_style = stock_cell_style_plano if quitar_fondos else stock_cell_style
    _valor_style = valorizado_plano       if quitar_fondos else valorizado_bar_style

    for c in df_grid.columns:
        if not pd.api.types.is_numeric_dtype(df_grid[c]):
            continue

        gb.configure_column(c, filter="agNumberColumnFilter")

        norm_c        = _norm(c)
        es_stock      = "stock" in norm_c
        es_valorizado = "valorizado" in norm_c
        es_precio     = any(k in norm_c for k in ("precio", "promedio", "unitario", "costo"))
        es_valor      = any(k in norm_c for k in ("valorizado", "total", "importe", "monto"))

        if es_stock:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                cellStyle=_stock_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 0, maximumFractionDigits: 0 });
                    }
                """),
            )
        elif es_valorizado:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                minWidth=170,
                cellStyle=_valor_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """),
            )
        elif es_precio:
            gb.configure_column(
                c, aggFunc="avg", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """),
            )
        elif es_valor:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """),
            )
        else:
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 0, maximumFractionDigits: 2 });
                    }
                """),
            )

    if col_producto and col_producto in df_grid.columns and col_producto not in grupos_sel:
        gb.configure_column(col_producto, pinned="left", minWidth=300)

    # ── Requerimientos: configuración especial de columnas de fecha y periodo ──
    if es_requerimientos:
        for c in df_grid.columns:
            _n = _norm(c)
            es_fecha = (pd.api.types.is_datetime64_any_dtype(df_grid[c])
                        or "fecha" in _n or "date" in _n)
            if es_fecha and _n not in ("mes", "ano", "anio"):
                gb.configure_column(c, filter=False, suppressFiltersToolPanel=True)

        col_mes = buscar_columna(df_grid, "Mes")
        col_ano = buscar_columna(df_grid, "Año", "Ano", "Anio")

        if col_mes and col_mes in df_grid.columns:
            valores_mes = sorted(
                [v for v in df_grid[col_mes].dropna().astype(str).unique().tolist() if v != ""]
            )
            gb.configure_column(
                col_mes,
                filter="agSetColumnFilter",
                filterParams={
                    "values": valores_mes,
                    "suppressSorting": False,
                    "suppressMiniFilter": False,
                },
            )

        if col_ano and col_ano in df_grid.columns:
            valores_ano = sorted(
                [v for v in df_grid[col_ano].dropna().astype(str).unique().tolist() if v != ""]
            )
            gb.configure_column(
                col_ano,
                filter="agSetColumnFilter",
                filterParams={
                    "values": valores_ano,
                    "suppressSorting": False,
                    "suppressMiniFilter": False,
                },
            )

    if cols_visibles is not None:
        visibles_norm = {_norm(c) for c in cols_visibles}
        hay_match = any(_norm(c) in visibles_norm for c in df_grid.columns)
        if hay_match:
            for c in df_grid.columns:
                if c in grupos_sel:
                    continue
                if _norm(c) not in visibles_norm:
                    gb.configure_column(c, hide=True)

    row_h    = max(28, min(60, font_px + 12))
    header_h = max(30, min(62, font_px + 14))
    if es_requerimientos:
        row_h = 22

    cols_valor  = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and
                   any(k in _norm(c) for k in ("valorizado", "total", "importe", "monto"))]
    cols_precio = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and
                   any(k in _norm(c) for k in ("precio", "promedio", "unitario", "costo"))]
    cols_stock  = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and "stock" in _norm(c)]

    primera_col = list(df_grid.columns)[0] if len(df_grid.columns) > 0 else None
    fila_totales = {}
    for c in df_grid.columns:
        if c in cols_valor:
            fila_totales[c] = round(float(df_grid[c].sum()), 2)
        elif c in cols_precio:
            fila_totales[c] = round(float(df_grid[c].mean()), 2)
        elif c in cols_stock:
            fila_totales[c] = round(float(df_grid[c].sum()), 0)
        elif c == primera_col:
            fila_totales[c] = "▶ TOTAL"
        else:
            fila_totales[c] = None

    if col_stock and col_stock in df_grid.columns and not quitar_fondos:
        _sf = str(col_stock).replace("\\", "\\\\").replace('"', '\\"')
        get_row_style = JsCode(f"""
            function(params) {{
                if (params.node.rowPinned === 'bottom') {{
                    return {{ fontWeight:'700', backgroundColor:'#dbeafe', color:'#1e3a5f',
                              borderTop:'2px solid #3b82f6', fontSize:'13px' }};
                }}
                if (params.node.group || !params.data) return null;
                var s = params.data["{_sf}"];
                if (s === null || s === undefined || s === '') return null;
                var v = Number(s);
                if (isNaN(v)) return null;
                if (v === 0) return {{ backgroundColor:'#fef2f2' }};
                if (v < 10)  return {{ backgroundColor:'#fffbeb' }};
                return null;
            }}
        """)
    else:
        get_row_style = JsCode("""
            function(params) {
                if (params.node.rowPinned === 'bottom') {
                    return { fontWeight:'700', backgroundColor:'#dbeafe', color:'#1e3a5f',
                             borderTop:'2px solid #3b82f6', fontSize:'13px' };
                }
            }
        """)

    opciones_grid = {
        "autoGroupColumnDef": {"minWidth": 200},
        "localeText": LOCALE_ES,
        "suppressSizeToFit": True,
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Columnas",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                    "toolPanelParams": {
                        "suppressRowGroups": not es_pivotable,
                        "suppressValues": not es_pivotable,
                        "suppressPivots": not es_pivotable,
                        "suppressPivotMode": not es_pivotable,
                        "suppressColumnFilter": False,
                        "suppressColumnSelectAll": False,
                        "suppressColumnExpandAll": True,
                    },
                },
                {
                    "id": "filters",
                    "labelDefault": "Filtros",
                    "labelKey": "filters",
                    "iconKey": "filter",
                    "toolPanel": "agFiltersToolPanel",
                },
            ],
            "defaultToolPanel": "columns",
            "position": "right",
        },
        "rowHeight": row_h,
        "headerHeight": header_h,
        "cellSelection": True,
        "tooltipShowDelay": 300,
        "getRowStyle": get_row_style,
        "onGridSizeChanged": JsCode("function(params) { /* No auto-fit */ }"),
        "onFirstDataRendered": JsCode("function(params) { /* No auto-fit */ }"),
    }

    if not es_pivotable:
        opciones_grid["pinnedBottomRowData"] = [fila_totales]
    else:
        opciones_grid["grandTotalRow"] = "bottom"

    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c in df_grid.columns:
                gb.configure_column(c, rowGroup=True, hide=True)

        if es_inventario:
            opciones_grid["groupDisplayType"] = "groupRows"

            _col_val_js = ""
            if col_valorizado and col_valorizado in df_grid.columns:
                _col_val_js = str(col_valorizado).replace("\\", "\\\\").replace('"', '\\"')

            opciones_grid["groupRowRendererParams"] = {
                "innerRenderer": JsCode(f"""
                    function(params) {{
                        if (!params.node || !params.node.group) return params.value;
                        var nombre = (params.value == null ? '' : params.value);
                        var n = params.node.allChildrenCount;
                        var extra = '';
                        var colVal = "{_col_val_js}";
                        if (colVal && params.node.aggData &&
                            params.node.aggData[colVal] !== null &&
                            params.node.aggData[colVal] !== undefined) {{
                            var v = Number(params.node.aggData[colVal]);
                            if (!isNaN(v)) {{
                                extra = ' · S/ ' + v.toLocaleString('es-PE', {{
                                    minimumFractionDigits: 2, maximumFractionDigits: 2 }});
                            }}
                        }}

                        var container = document.createElement('div');
                        container.style.display = 'flex';
                        container.style.alignItems = 'center';
                        container.style.gap = '4px';

                        var spanNombre = document.createElement('span');
                        spanNombre.textContent = nombre;
                        spanNombre.style.fontWeight = '600';
                        spanNombre.style.color = '#1e293b';

                        var spanExtra = document.createElement('span');
                        spanExtra.textContent = '(' + n + ')' + extra;
                        spanExtra.style.color = '#64748b';
                        spanExtra.style.fontWeight = '400';

                        container.appendChild(spanNombre);
                        container.appendChild(spanExtra);

                        return container;
                    }}
                """)
            }
        else:
            opciones_grid["groupDisplayType"] = "multipleColumns"

        opciones_grid["groupDefaultExpanded"] = 0
        opciones_grid["pivotMode"] = es_requerimientos
    else:
        opciones_grid["pivotMode"] = es_requerimientos

    if envolver_cabeceras:
        opciones_grid["headerHeight"] = int(font_px * 2.5 + 20)

    if es_salidas:
        opciones_grid["sideBar"] = False

    gb.configure_grid_options(**opciones_grid)
    if es_salidas:
        gb.configure_pagination(enabled=False)
    else:
        gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    custom_css = {
        ".ag-root-wrapper": {
            "background-color": "#ffffff",
            "border": "1px solid #0f172a",
            "border-radius": "10px !important",
            "overflow": "hidden !important",
            "box-shadow": "0 4px 12px rgba(0,0,0,0.06)",
            "width": "100% !important",
        },
        ".ag-header": {
            "background-color": "#0f172a !important",
            "border-bottom": "none !important",
        },
        ".ag-header-cell": {
            "background-color": "#0f172a !important",
        },
        ".ag-header-cell-text": {
            "color": "#f8fafc !important",
            "font-weight": "700",
            "font-size": f"{font_px}px",
            "letter-spacing": "0.03em",
            "text-transform": "uppercase",
        },
        ".ag-header-icon": {
            "color": "#93c5fd !important",
        },
        ".ag-row": {
            "border-bottom": "1px solid #f1f5f9",
            "color": "#1e293b",
        },
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},
        ".ag-row-pinned": {
            "background-color": "#dbeafe !important",
            "font-weight": "700 !important",
            "border-top": "2px solid #3b82f6 !important",
            "color": "#1e3a5f !important",
            "font-size": f"{font_px + 1}px !important",
        },
        ".ag-paging-panel": {
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "space-between !important",
            "color": "#64748b",
            "background-color": "#f8fafc",
            "border-top": "1px solid #e2e8f0",
            "padding": "8px 16px !important",
            "border-bottom-left-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "font-size": "12px !important",
            "min-height": "44px !important",
        },
        ".ag-paging-panel .ag-paging-page-size": {
            "order": "-1 !important",
            "margin-right": "auto !important",
        },
        ".ag-paging-panel .ag-paging-page-size .ag-label": {
            "color": "#64748b !important",
            "font-size": "12px !important",
            "margin-right": "6px !important",
        },
        ".ag-paging-panel .ag-paging-page-size select, "
        ".ag-paging-panel .ag-paging-page-size .ag-select": {
            "border": "1px solid #e2e8f0 !important",
            "border-radius": "6px !important",
            "background": "#ffffff !important",
            "color": "#1e293b !important",
            "font-size": "12px !important",
            "padding": "2px 6px !important",
        },
        ".ag-paging-button": {
            "width": "28px !important",
            "height": "28px !important",
            "border": "1px solid #e2e8f0 !important",
            "background": "#ffffff !important",
            "border-radius": "6px !important",
            "color": "#475569 !important",
            "font-size": "13px !important",
            "cursor": "pointer !important",
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "center !important",
            "margin": "0 2px !important",
            "transition": "all 0.15s ease !important",
        },
        ".ag-paging-button:hover:not(.ag-disabled)": {
            "background": "#eff6ff !important",
            "border-color": "#93c5fd !important",
            "color": "#2563eb !important",
        },
        ".ag-paging-button.ag-disabled": {
            "color": "#cbd5e1 !important",
            "border-color": "#f1f5f9 !important",
            "background": "#f8fafc !important",
            "cursor": "default !important",
        },
        ".ag-paging-row-summary-panel": {
            "color": "#64748b !important",
            "font-size": "12px !important",
            "margin-left": "auto !important",
        },
        ".ag-paging-row-summary-panel-number": {
            "color": "#1e293b !important",
            "font-weight": "600 !important",
        },
        ".ag-status-bar": {
            "background-color": "#f8fafc !important",
            "border-top": "1px solid #e2e8f0 !important",
            "color": "#475569 !important",
            "padding": "4px 16px !important",
            "font-size": "12px !important",
            "min-height": "0 !important",
        },
        ".ag-status-name-value": {
            "color": "#475569 !important",
            "font-size": "12px !important",
        },
        ".ag-status-name-value-value": {
            "color": "#1e293b !important",
            "font-weight": "600 !important",
        },
        ".ag-side-bar": {
            "background-color": "#ffffff",
            "border-left": "1px solid #e2e8f0 !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "border-bottom": "1px solid #0f172a !important",
        },
        ".ag-side-bar .ag-side-buttons": {
            "border-right": "1px solid #e2e8f0 !important",
        },
        ".ag-side-button": {
            "background-color": "#f8fafc !important",
            "border": "none !important",
            "border-bottom": "1px solid #e2e8f0 !important",
            "color": "#475569 !important",
        },
        ".ag-side-button:hover": {
            "background-color": "#dbeafe !important",
            "color": "#2563eb !important",
        },
        ".ag-side-button.ag-selected": {
            "background-color": "#2563eb !important",
            "color": "#ffffff !important",
            "box-shadow": "inset 0 0 0 1px #3b82f6",
        },
        ".ag-tool-panel-wrapper": {
            "background-color": "#ffffff !important",
            "border": "none !important",
        },
        ".ag-column-select-panel": {
            "padding": "10px !important",
            "background-color": "#ffffff !important",
        },
        ".ag-column-tool-panel .ag-column-panel": {
            "border": "none !important",
        },
        ".ag-column-tool-panel .ag-column-select-all": {
            "padding": "10px 0 !important",
            "border-bottom": "1px solid #e2e8f0 !important",
        },
        ".ag-column-panel .ag-header-cell-text": {
            "color": "#1e293b !important",
            "font-weight": "600 !important",
        },
        ".ag-filter-toolpanel-body": {
            "padding": "10px !important",
            "background-color": "#ffffff !important",
        },
        ".ag-filter-toolpanel": {
            "border": "1px solid #0f172a !important",
            "border-radius": "8px !important",
            "margin": "8px !important",
            "overflow": "hidden !important",
        },
        ".ag-column-select-column": {
            "display": "flex !important",
            "align-items": "center !important",
            "padding": "10px 12px !important",
            "border-bottom": "0.5px solid #f1f5f9 !important",
        },
        ".ag-column-select-column-label": {
            "order": "-1 !important",
            "margin-right": "auto !important",
            "color": "#475569 !important",
            "font-size": "12.5px !important",
        },
        ".ag-column-select-column:has(.ag-checked) .ag-column-select-column-label": {
            "color": "#1e293b !important",
            "font-weight": "500 !important",
        },
        ".ag-column-select-column .ag-drag-handle": {
            "display": "none !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper": {
            "width": "36px !important",
            "height": "20px !important",
            "border-radius": "999px !important",
            "background": "#e2e8f0 !important",
            "border": "none !important",
            "box-shadow": "none !important",
            "position": "relative !important",
            "transition": "background .15s ease !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper::after": {
            "content": "'' !important",
            "position": "absolute !important",
            "top": "2px !important",
            "left": "2px !important",
            "width": "16px !important",
            "height": "16px !important",
            "border-radius": "50% !important",
            "background": "#ffffff !important",
            "color": "transparent !important",
            "box-shadow": "0 1px 2px rgba(0,0,0,0.25) !important",
            "transition": "left .15s ease !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked": {
            "background": "#2563eb !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked::after": {
            "content": "'' !important",
            "left": "18px !important",
        },
        ".ag-column-select-column .ag-checkbox-input": {
            "cursor": "pointer !important",
        },
    }

    if envolver_cabeceras:
        custom_css[".ag-header-cell-text"].update({
            "white-space": "normal !important",
            "overflow": "visible !important",
            "text-overflow": "clip !important",
            "line-height": "1.2 !important",
            "word-break": "break-word",
        })
        custom_css[".ag-header-cell-label"] = {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "align-items": "center",
        }

    tema_grid = "balham"
    if es_inventario:
        tema_grid = "material"
        custom_css[".ag-root-wrapper"].update({
            "background-color": "#f8fafc !important",
            "border": "none !important",
            "box-shadow": "none !important",
            "border-radius": "4px !important",
        })
        custom_css[".ag-header"].update({
            "background-color": "#ffffff !important",
            "border-bottom": "2px solid #3b82f6 !important",
        })
        custom_css[".ag-tool-panel-horizontal-resize"] = {
            "width": "8px !important",
            "background-color": "#e2e8f0",
            "cursor": "col-resize",
        }
        custom_css[".ag-header-cell"].update({
            "background-color": "#ffffff !important",
        })
        custom_css[".ag-header-cell-text"].update({
            "color": "#5f6368 !important",
            "font-weight": "600",
            "letter-spacing": "0.05em",
            "text-transform": "uppercase",
        })
        custom_css[".ag-header-icon"].update({
            "color": "#9aa0a6 !important",
        })
        custom_css[".ag-row-pinned"].update({
            "background-color": "#dbeafe !important",
            "border-top": "2px solid #3b82f6 !important",
            "color": "#1e3a5f !important",
        })
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar"] = {"width": "8px"}
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-track"] = {
            "background": "#e2e8f0", "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb"] = {
            "background": "#3b82f6", "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb:hover"] = {
            "background": "#2563eb",
        }
        custom_css[".ag-side-bar"].update({
            "background-color": "#f6f8fb !important",
            "border": "1px solid #dbe2ec !important",
            "border-left": "1px solid #dbe2ec !important",
            "border-bottom": "1px solid #dbe2ec !important",
            "border-radius": "10px !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "box-shadow": "0 4px 14px rgba(15,23,42,0.08) !important",
            "margin": "4px 6px 6px 12px !important",
            "overflow": "hidden !important",
        })
        custom_css[".ag-side-bar .ag-side-buttons"].update({
            "background-color": "#eef2f7 !important",
            "border-bottom": "1px solid #dbe2ec !important",
        })
        custom_css[".ag-root"] = {
            "border": "2px solid #3b82f6",
            "border-radius": "6px",
        }
        custom_css[".ag-filter-toolpanel"].update({
            "border": "1px solid #3b82f6 !important",
            "border-radius": "8px !important",
            "margin": "8px !important",
            "overflow": "hidden !important",
        })

    # ── Requerimientos: paleta "Pizarra" (slate) ──────────────────────────
    if es_requerimientos:
        custom_css[".ag-side-button.ag-selected"] = {
            "background-color": "#334155 !important",
            "color": "#f8fafc !important",
            "box-shadow": "inset 0 0 0 1px #475569",
        }
        custom_css[".ag-side-button:hover"] = {
            "background-color": "#e2e8f0 !important",
            "color": "#1e293b !important",
        }
        custom_css[".ag-header-icon"] = {"color": "#94a3b8 !important"}
        custom_css[".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked"] = {
            "background": "#475569 !important",
        }
        custom_css[".ag-row-pinned"] = {
            "background-color": "#e2e8f0 !important",
            "font-weight": "700 !important",
            "border-top": "2px solid #475569 !important",
            "color": "#0f172a !important",
            "font-size": f"{font_px + 1}px !important",
        }
        custom_css[".ag-row-hover"] = {"background-color": "#f1f5f9 !important"}
        custom_css[".ag-paging-button:hover:not(.ag-disabled)"] = {
            "background": "#e2e8f0 !important",
            "border-color": "#94a3b8 !important",
            "color": "#334155 !important",
        }
        custom_css[".ag-header-group-cell"] = {"background-color": "#0f172a !important"}
        custom_css[".ag-header-group-cell-label"] = {"color": "#f8fafc !important"}
        custom_css[".ag-header-group-text"] = {
            "color": "#f8fafc !important",
            "font-weight": "500 !important",
        }
        custom_css[".ag-header-group-cell .ag-icon"] = {"color": "#94a3b8 !important"}
        custom_css[".ag-theme-balham"] = {"--ag-list-item-height": "22px !important"}
        custom_css[".ag-column-select-column-label"] = {
            "font-size": f"{max(11, font_px - 1)}px !important",
            "line-height": "1.15 !important",
        }
        custom_css[".ag-column-select-column .ag-checkbox-input-wrapper"] = {
            "transform": "scale(0.85)",
        }
        custom_css[".ag-column-select-column .ag-toggle-button-input-wrapper"] = {
            "transform": "scale(0.85)",
        }
        custom_css[".ag-column-drop-vertical"] = {
            "min-height": "38px !important",
            "padding-top": "2px !important",
            "padding-bottom": "2px !important",
        }
        custom_css[".ag-column-drop-vertical-title-bar"] = {
            "padding": "4px 6px !important",
        }
        custom_css[".ag-column-drop-vertical-empty-message"] = {
            "padding": "4px 8px !important",
            "font-size": "11px !important",
        }
        custom_css[".ag-column-drop-vertical-cell"] = {
            "margin": "2px 4px !important",
        }
        custom_css[".ag-column-select-header"] = {
            "padding-top": "4px !important",
            "padding-bottom": "4px !important",
        }

    # ── Límite de filas con aviso al usuario ──────────────────────────────
    LIMITE_FILAS = 50_000
    if len(df_grid) > LIMITE_FILAS:
        st.warning(
            f"⚠️ Mostrando {LIMITE_FILAS:,} de {len(df_grid):,} filas. "
            "Usa los filtros para acotar los resultados y ver todos los datos."
        )
        df_grid = df_grid.head(LIMITE_FILAS)

    AgGrid(
        df_grid, gridOptions=grid_options,
        height=900,
        theme=tema_grid, custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_{reporte}",
    )

    inject_grid_health_check()

    # ── Post-render: inyecciones específicas por reporte ──────────────────
    inject_pagination_v2()

    if es_requerimientos:
        inject_maximize_aggrid()


# ===========================================================================
# FUNCIÓN: AGGRID MÓVIL (ANCHO COMPLETO)
# ===========================================================================

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
        opciones_grid["headerHeight"] = int(font_px * 2.5 + 20)

    gb.configure_grid_options(**opciones_grid)
    grid_options = gb.build()

    custom_css = {
        ".ag-root-wrapper": {"background-color": "#ffffff", "border": "1px solid #e2e8f0", "border-radius": "8px", "width": "100% !important"},
        ".ag-header": {"background-color": "#f1f5f9", "border-bottom": "2px solid #3b82f6"},
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {"color": "#64748b", "background-color": "#f8fafc", "border-top": "1px solid #e2e8f0", "font-size": "0.75rem"},
        ".ag-menu": {"background-color": "#ffffff", "color": "#1e293b", "border": "1px solid #e2e8f0"},
        ".ag-pinned-left-header": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
        ".ag-pinned-left-cols-container": {"box-shadow": "3px 0 8px rgba(0,0,0,0.08)"},
    }

    if envolver_cabeceras:
        custom_css[".ag-header-cell-text"].update({
            "white-space": "normal !important",
            "overflow": "visible !important",
            "text-overflow": "clip !important",
            "line-height": "1.2 !important",
            "word-break": "break-word",
        })
        custom_css[".ag-header-cell-label"] = {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "align-items": "center",
        }

    # ── Límite de filas con aviso al usuario (móvil) ──────────────────────
    LIMITE_FILAS = 20_000
    if len(df_grid) > LIMITE_FILAS:
        st.warning(
            f"⚠️ Mostrando {LIMITE_FILAS:,} de {len(df_grid):,} filas. "
            "Usa los filtros para ver todos los datos."
        )
        df_grid = df_grid.head(LIMITE_FILAS)

    AgGrid(
        df_grid, gridOptions=grid_options, height=380,
        theme="balham", custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_movil_{reporte}",
    )

    inject_grid_health_check()


# ===========================================================================
# FUNCIÓN: TABLA DE COMPRAS — st.data_editor
# ===========================================================================

def _es_moneda(nombre: str) -> bool:
    """True si la columna parece un importe en soles."""
    n = _norm(nombre)
    return any(k in n for k in ("importe", "total", "monto", "precio", "costo", "unitario"))


def _es_cantidad(nombre: str) -> bool:
    """True si la columna parece una cantidad."""
    n = _norm(nombre)
    return any(k in n for k in ("cantidad", "qty", "unidades", "stock"))


def _configurar_columnas_compras(df: pd.DataFrame) -> dict:
    """Devuelve column_config para st.data_editor según tipo y nombre de columna."""
    config = {}
    col_fecha = buscar_columna_fecha(df)

    for col in df.columns:
        dtype = df[col].dtype

        if col == col_fecha or pd.api.types.is_datetime64_any_dtype(dtype):
            config[col] = st.column_config.DateColumn(
                col, format="DD/MM/YYYY", width="medium",
            )
        elif pd.api.types.is_numeric_dtype(dtype) and _es_moneda(col):
            config[col] = st.column_config.NumberColumn(
                col, format="S/ %.2f", step=0.01, width="medium",
            )
        elif pd.api.types.is_numeric_dtype(dtype) and _es_cantidad(col):
            config[col] = st.column_config.NumberColumn(
                col, format="%d", step=1, width="small",
            )
        elif pd.api.types.is_numeric_dtype(dtype):
            config[col] = st.column_config.NumberColumn(
                col, format="%.2f", width="small",
            )
        else:
            config[col] = st.column_config.TextColumn(col, width="medium")

    return config


def _totales_html_compras(df: pd.DataFrame) -> str:
    """Genera el HTML de la fila de totales para Compras."""
    partes = ["▶ TOTAL &nbsp;&nbsp;"]
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        val = df[col].sum()
        if _es_moneda(col):
            partes.append(f"<span style='margin-right:24px'>{col}: <b>S/ {val:,.2f}</b></span>")
        elif _es_cantidad(col):
            partes.append(f"<span style='margin-right:24px'>{col}: <b>{int(val):,}</b></span>")
        else:
            partes.append(f"<span style='margin-right:24px'>{col}: <b>{val:,.2f}</b></span>")
    return "".join(partes)


def renderizar_tabla_compras(df: pd.DataFrame, grupos_sel: list = None):
    """
    Renderiza la tabla del reporte de Compras usando st.data_editor.
    """
    if df.empty:
        st.warning("No hay datos para mostrar con los filtros actuales.")
        return

    grupos_sel = grupos_sel or []

    if grupos_sel:
        cols_num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if cols_num:
            df_view = df.groupby(grupos_sel, as_index=False).agg(
                {c: "sum" for c in cols_num}
            )
        else:
            df_view = df[grupos_sel].drop_duplicates()
        st.caption(f"Agrupado por: {', '.join(grupos_sel)}")
    else:
        df_view = df.copy()

    cols_importe = [c for c in df_view.columns
                    if pd.api.types.is_numeric_dtype(df_view[c]) and _es_moneda(c)]
    cols_cant    = [c for c in df_view.columns
                    if pd.api.types.is_numeric_dtype(df_view[c]) and _es_cantidad(c)]

    n_kpi = min(4, 1 + len(cols_importe[:2]) + len(cols_cant[:1]))
    kpi_cols = st.columns(n_kpi)
    idx = 0
    kpi_cols[idx].metric("📄 Registros", f"{len(df_view):,}")
    idx += 1
    for c in cols_importe[:2]:
        if idx >= n_kpi:
            break
        kpi_cols[idx].metric(f"💰 {c}", f"S/ {df_view[c].sum():,.2f}")
        idx += 1
    for c in cols_cant[:1]:
        if idx >= n_kpi:
            break
        kpi_cols[idx].metric(f"📦 {c}", f"{int(df_view[c].sum()):,}")
        idx += 1

    st.markdown("#### 📋 Detalle de Compras")

    df_editado = st.data_editor(
        df_view,
        column_config=_configurar_columnas_compras(df_view),
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        height=520,
        key="data_editor_compras",
    )

    cols_num_view = [c for c in df_view.columns if pd.api.types.is_numeric_dtype(df_view[c])]
    if cols_num_view:
        st.markdown(
            "<div style='background:#dbeafe;border-top:2px solid #3b82f6;"
            "border-radius:0 0 8px 8px;padding:6px 12px;"
            "font-size:13px;font-weight:700;color:#1e3a5f;'>"
            + _totales_html_compras(df_editado)
            + "</div>",
            unsafe_allow_html=True,
        )

    st.download_button(
        label="⬇️ Exportar a CSV",
        data=df_editado.to_csv(index=False).encode("utf-8-sig"),
        file_name="compras_export.csv",
        mime="text/csv",
        key="btn_export_compras",
    )
