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
from perf import perf  # <--- NUEVO IMPORT PARA MEDICIÓN DE RENDIMIENTO


# ===========================================================================
# FUNCIÓN: AGGRID DESKTOP — con formato financiero y diseño mejorado
# ===========================================================================

def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px=14, cols_visibles=None):
    """Renderiza la tabla AgGrid en vista desktop con formato financiero y diseño premium.

    cols_visibles: lista de columnas que arrancan VISIBLES. El resto se oculta
    por defecto y el usuario las activa desde la barra lateral (panel "Columnas").
    Si es None, se muestran todas.
    """

    REPORTES_ESTILO_INVENTARIO = ("Inventario Valorizado", "Ajuste de Inventario")

    envolver_cabeceras = reporte in REPORTES_ESTILO_INVENTARIO
    quitar_fondos = reporte in REPORTES_ESTILO_INVENTARIO
    es_inventario = reporte in REPORTES_ESTILO_INVENTARIO
    es_salidas = (reporte == "Salidas")
    es_requerimientos = (reporte == "Requerimientos")
    es_ajuste = (reporte == "Ajuste de Inventario")

    mostrar_pivot = es_requerimientos or es_inventario

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
                return { fontWeight: '700', color: '#3b2e93' };
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
                    backgroundColor: '#fff7ed',
                    color: '#c2410c',
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
                return { fontWeight: '700', color: '#3b2e93' };
            }
            return {
                fontFamily: "'Courier New', Courier, monospace",
                fontWeight: '700',
                textAlign: 'right',
                padding: '2px 10px',
                color: '#18181d'
            };
        }
    """)

    valorizado_bar_style = JsCode(f"""
        function(params) {{
            var base = {{
                fontFamily: "'Courier New', Courier, monospace",
                color: '#3b2e93',
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
                backgroundImage: 'linear-gradient(to right, #d4cdf7 0%, #d4cdf7 ' + pct + '%, transparent ' + pct + '%, transparent 100%)',
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
                color: '#3b2e93',
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
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
            _decimales_generico = 2 if es_ajuste else 0
            gb.configure_column(
                c, aggFunc="sum", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode(f"""
                    function(params) {{
                        if (params.value == null) return '';
                        return Number(params.value).toLocaleString('es-PE', {{
                            minimumFractionDigits: {_decimales_generico}, maximumFractionDigits: 2 }});
                    }}
                """),
            )

    if col_producto and col_producto in df_grid.columns and col_producto not in grupos_sel:
        gb.configure_column(col_producto, pinned="left", minWidth=300)

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
            fila_totales[c] = round(float(df_grid[c].sum()), 2)
        elif c == primera_col:
            fila_totales[c] = "▶ TOTAL"
        else:
            fila_totales[c] = None

    if col_stock and col_stock in df_grid.columns and es_inventario:
        get_row_style = JsCode("""
            function(params) {
                if (params.node.rowPinned === 'bottom') {
                    return { fontWeight:'700', backgroundColor:'#e7e3fb', color:'#3b2e93',
                             borderTop:'2px solid #6c5ce7', fontSize:'13px' };
                }
                if (params.node.group) {
                    var nivel = params.node.level;
                    if (nivel === 0) return { backgroundColor:'#d4cdf7', fontWeight:'600' };
                    if (nivel === 1) return { backgroundColor:'#e7e3fb', fontWeight:'600' };
                    return { backgroundColor:'#f0edfe', fontWeight:'500' };
                }
                return { backgroundColor:'#ffffff' };
            }
        """)
    elif col_stock and col_stock in df_grid.columns and not quitar_fondos:
        _sf = str(col_stock).replace("\\", "\\\\").replace('"', '\\"')
        get_row_style = JsCode(f"""
            function(params) {{
                if (params.node.rowPinned === 'bottom') {{
                    return {{ fontWeight:'700', backgroundColor:'#e7e3fb', color:'#3b2e93',
                              borderTop:'2px solid #6c5ce7', fontSize:'13px' }};
                }}
                if (params.node.group || !params.data) return null;
                var s = params.data["{_sf}"];
                if (s === null || s === undefined || s === '') return null;
                var v = Number(s);
                if (isNaN(v)) return null;
                if (v === 0) return {{ backgroundColor:'#fef2f2' }};
                if (v < 10)  return {{ backgroundColor:'#fff7ed' }};
                return null;
            }}
        """)
    else:
        get_row_style = JsCode("""
            function(params) {
                if (params.node.rowPinned === 'bottom') {
                    return { fontWeight:'700', backgroundColor:'#e7e3fb', color:'#3b2e93',
                             borderTop:'2px solid #6c5ce7', fontSize:'13px' };
                }
            }
        """)

    _columns_panel = {
        "id": "columns",
        "labelDefault": "Columnas",
        "labelKey": "columns",
        "iconKey": "columns",
        "toolPanel": "agColumnsToolPanel",
        "toolPanelParams": {
            "suppressRowGroups": (not mostrar_pivot) or es_ajuste,
            "suppressValues":    (not mostrar_pivot) or es_ajuste,
            "suppressPivots":    (not mostrar_pivot) or es_ajuste,
            "suppressPivotMode": (not mostrar_pivot) or es_ajuste,
            "suppressColumnFilter": es_ajuste,
            "suppressColumnSelectAll": es_ajuste,
            "suppressColumnExpandAll": True,
        },
    }
    _filters_panel = {
        "id": "filters",
        "labelDefault": "Filtros",
        "labelKey": "filters",
        "iconKey": "filter",
        "toolPanel": "agFiltersToolPanel",
    }
    _tool_panels = [_columns_panel, _filters_panel]

    if es_ajuste:
        _tool_panels.append({
            "id": "pivotePanel",
            "labelDefault": "Modo pivote",
            "labelKey": "pivotePanel",
            "iconKey": "pivot",
            "toolPanel": "agColumnsToolPanel",
            "toolPanelParams": {
                "suppressRowGroups": False,
                "suppressValues": False,
                "suppressPivots": False,
                "suppressPivotMode": False,
                "suppressColumnFilter": True,
                "suppressColumnSelectAll": True,
                "suppressColumnExpandAll": True,
            },
        })

    _sidebar_cfg = {
        "toolPanels": _tool_panels,
        "defaultToolPanel": "" if es_ajuste else "columns",
        "position": "right",
    }

    # Nombre del reporte, sanitizado para insertarlo como string literal JS.
    _reporte_js = str(reporte).replace("\\", "\\\\").replace('"', '\\"')

    # NOTA SOBRE EL RELOJ USADO EN LOS EVENTOS DE PERFORMANCE:
    # Antes se usaba performance.now() a secas, que mide "ms desde que ESTE
    # iframe empezó a existir". Eso es inútil para comparar eventos entre
    # sí: si el iframe de AgGrid se recrea (cambias de reporte y vuelves,
    # etc.) el contador se reinicia, y si conviven varios grids (distintos
    # reportes) cada uno tiene su propio origen, así que mezclarlos en una
    # sola línea de tiempo da saltos sin sentido (ej. 4,542,776 ms seguido
    # de 244,370 ms).
    # Ahora usamos Date.now() - window.parent.performance.timeOrigin: el
    # timeOrigin de la ventana PRINCIPAL (la pestaña del navegador) es el
    # mismo sin importar cuántos iframes de AgGrid se creen o destruyan, así
    # que el número resultante es "ms desde que cargó la página" y es
    # comparable entre reportes y a través de remounts del grid.
    _js_ms_desde_carga = """
        (function() {
            try {
                var origen = (window.parent && window.parent.performance)
                    ? window.parent.performance.timeOrigin
                    : performance.timeOrigin;
                return Math.round(Date.now() - origen);
            } catch(e) { return Math.round(performance.now()); }
        })()
    """

    # =======================================================================
    # CONFIGURACIÓN DE OPCIONES DE AGGRID CON MEDICIÓN DE RENDIMIENTO
    # =======================================================================
    opciones_grid = {
        "autoGroupColumnDef": {"minWidth": 200},
        "localeText": LOCALE_ES,
        "sideBar": _sidebar_cfg,
        "rowHeight": row_h,
        "headerHeight": header_h,
        "cellSelection": True,
        "tooltipShowDelay": 300,
        "getRowStyle": get_row_style,
        "suppressAggFuncInHeader": True,
        # FIX columnas: onFirstDataRendered autoajusta cada columna a su
        # contenido real (no comprime en pantallas angostas). onGridSizeChanged
        # redistribuye si el usuario redimensiona la ventana.
        "onGridSizeChanged": JsCode("function(params) { params.api.sizeColumnsToFit(); }"),
        "onGridReady": JsCode(f"""
            function(params) {{
                try {{
                    var ms = {_js_ms_desde_carga};
                    var bc = new BroadcastChannel('_perf_aggrid');
                    bc.postMessage({{event:'gridReady', ms: ms, ts: Date.now(), reporte: "{_reporte_js}"}});
                    bc.close();
                }} catch(e) {{}}
            }}
        """),
        "onFirstDataRendered": JsCode(f"""
            function(params) {{
                params.api.autoSizeAllColumns();
                try {{
                    var ms = {_js_ms_desde_carga};
                    var rc = (params.api.getDisplayedRowCount) ? params.api.getDisplayedRowCount() : null;
                    var bc = new BroadcastChannel('_perf_aggrid');
                    bc.postMessage({{event:'firstDataRendered', ms: ms, rowCount: rc, ts: Date.now(), reporte: "{_reporte_js}"}});
                    bc.close();
                }} catch(e) {{}}
            }}
        """),
        # NUEVO: a diferencia de onGridReady/onFirstDataRendered (que solo
        # ocurren en el MONTAJE inicial del iframe), onModelUpdated se
        # dispara cada vez que cambian los datos mostrados: nuevo rowData,
        # filtro, orden, agrupación, paginación, etc. Por eso es el evento
        # correcto para medir "cada vez que la tabla se renderiza" en
        # reruns donde Streamlit reutiliza el mismo componente/iframe.
        # Se aplica un pequeño debounce para no saturar el canal cuando
        # ag-grid dispara varios onModelUpdated seguidos por el mismo
        # cambio (p.ej. set rowData + auto-size + sort interno).
        "onModelUpdated": JsCode(f"""
            function(params) {{
                try {{
                    window.clearTimeout(window.__pgv2ModelUpdTimer);
                    window.__pgv2ModelUpdTimer = window.setTimeout(function() {{
                        var ms = {_js_ms_desde_carga};
                        var rc = (params.api.getDisplayedRowCount) ? params.api.getDisplayedRowCount() : null;
                        var bc = new BroadcastChannel('_perf_aggrid');
                        bc.postMessage({{event:'modelUpdated', ms: ms, rowCount: rc, ts: Date.now(), reporte: "{_reporte_js}"}});
                        bc.close();
                    }}, 120);
                }} catch(e) {{}}
            }}
        """),
    }

    if not es_requerimientos:
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
                        return '<span style="font-weight:600;color:#18181d">' + nombre +
                               '</span> <span style="color:#85858f;font-weight:400">(' +
                               n + ')' + extra + '</span>';
                    }}
                """)
            }
        else:
            opciones_grid["groupDisplayType"] = "multipleColumns"

        opciones_grid["groupDefaultExpanded"] = 0
        opciones_grid["pivotMode"] = es_requerimientos
    else:
        opciones_grid["pivotMode"] = False

    if envolver_cabeceras:
        opciones_grid["headerHeight"] = int(font_px * 2 + 14)

    if es_salidas:
        opciones_grid["sideBar"] = False

    if es_ajuste:
        opciones_grid["onToolPanelVisibleChanged"] = JsCode("""
            function(params) {
                try {
                    var open = (params.api && params.api.getOpenedToolPanel)
                        ? params.api.getOpenedToolPanel() : null;
                    var sb = document.querySelector('.ag-side-bar');
                    if (sb) sb.setAttribute('data-active-panel', open || '');
                } catch(e) {}
            }
        """)

    gb.configure_grid_options(**opciones_grid)
    if es_salidas:
        gb.configure_pagination(enabled=False)
    else:
        gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    custom_css = {
        ".ag-root-wrapper": {
            "background-color": "#ffffff",
            "border": "1px solid #e6e6eb",
            "border-radius": "12px !important",
            "overflow": "hidden !important",
            "box-shadow": "0 1px 3px rgba(16,16,20,0.05)",
            "width": "100% !important",
        },
        # Cabecera clara estilo CallAI: banda gris suave con texto gris medio
        ".ag-header": {
            "background-color": "#f4f4f6 !important",
            "border-bottom": "1px solid #e6e6eb !important",
        },
        ".ag-header-cell": {
            "background-color": "#f4f4f6 !important",
        },
        ".ag-header-cell-text": {
            "color": "#71717a !important",
            "font-weight": "600",
            "font-size": f"{font_px}px",
            "letter-spacing": "0.03em",
            "text-transform": "uppercase",
        },
        ".ag-header-icon": {
            "color": "#a2a2ad !important",
        },
        ".ag-row": {
            "border-bottom": "1px solid #f1f1f4",
            "color": "#18181d",
        },
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f6f6f8"},
        ".ag-row-hover": {"background-color": "#f0edfe !important"},
        ".ag-cell": {"color": "#52525c", "font-size": f"{font_px}px"},
        ".ag-row-pinned": {
            "background-color": "#e7e3fb !important",
            "font-weight": "700 !important",
            "border-top": "2px solid #6c5ce7 !important",
            "color": "#3b2e93 !important",
            "font-size": f"{font_px + 1}px !important",
        },
        ".ag-paging-panel": {
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "space-between !important",
            "color": "#85858f",
            "background-color": "#f6f6f8",
            "border-top": "1px solid #e6e6eb",
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
            "color": "#85858f !important",
            "font-size": "12px !important",
            "margin-right": "6px !important",
        },
        ".ag-paging-panel .ag-paging-page-size select, "
        ".ag-paging-panel .ag-paging-page-size .ag-select": {
            "border": "1px solid #e6e6eb !important",
            "border-radius": "6px !important",
            "background": "#ffffff !important",
            "color": "#18181d !important",
            "font-size": "12px !important",
            "padding": "2px 6px !important",
        },
        ".ag-paging-button": {
            "width": "28px !important",
            "height": "28px !important",
            "border": "1px solid #e6e6eb !important",
            "background": "#ffffff !important",
            "border-radius": "6px !important",
            "color": "#71717a !important",
            "font-size": "13px !important",
            "cursor": "pointer !important",
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "center !important",
            "margin": "0 2px !important",
            "transition": "all 0.15s ease !important",
        },
        ".ag-paging-button:hover:not(.ag-disabled)": {
            "background": "#f0edfe !important",
            "border-color": "#b9aff2 !important",
            "color": "#5a4ad9 !important",
        },
        ".ag-paging-button.ag-disabled": {
            "color": "#d6d6dd !important",
            "border-color": "#f1f1f4 !important",
            "background": "#f6f6f8 !important",
            "cursor": "default !important",
        },
        ".ag-paging-row-summary-panel": {
            "color": "#85858f !important",
            "font-size": "12px !important",
            "margin-left": "auto !important",
        },
        ".ag-paging-row-summary-panel-number": {
            "color": "#18181d !important",
            "font-weight": "600 !important",
        },
        ".ag-status-bar": {
            "background-color": "#f6f6f8 !important",
            "border-top": "1px solid #e6e6eb !important",
            "color": "#71717a !important",
            "padding": "4px 16px !important",
            "font-size": "12px !important",
            "min-height": "0 !important",
        },
        ".ag-status-name-value": {
            "color": "#71717a !important",
            "font-size": "12px !important",
        },
        ".ag-status-name-value-value": {
            "color": "#18181d !important",
            "font-weight": "600 !important",
        },
        ".ag-side-bar": {
            "background-color": "#ffffff",
            "border-left": "1px solid #e6e6eb !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "border-bottom": "1px solid #e6e6eb !important",
        },
        ".ag-side-bar .ag-side-buttons": {
            "border-right": "1px solid #e6e6eb !important",
        },
        ".ag-side-button": {
            "background-color": "#f6f6f8 !important",
            "border": "none !important",
            "border-bottom": "1px solid #e6e6eb !important",
            "color": "#71717a !important",
        },
        ".ag-side-button:hover": {
            "background-color": "#e7e3fb !important",
            "color": "#5a4ad9 !important",
        },
        ".ag-side-button.ag-selected": {
            "background-color": "#5a4ad9 !important",
            "color": "#ffffff !important",
            "box-shadow": "inset 0 0 0 1px #6c5ce7",
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
            "border-bottom": "1px solid #e6e6eb !important",
        },
        ".ag-column-panel .ag-header-cell-text": {
            "color": "#18181d !important",
            "font-weight": "600 !important",
        },
        ".ag-filter-toolpanel-body": {
            "padding": "10px !important",
            "background-color": "#ffffff !important",
        },
        ".ag-filter-toolpanel": {
            "border": "1px solid #e6e6eb !important",
            "border-radius": "8px !important",
            "margin": "8px !important",
            "overflow": "hidden !important",
        },
        ".ag-column-select-column": {
            "display": "flex !important",
            "align-items": "center !important",
            "padding": "10px 12px !important",
            "border-bottom": "0.5px solid #f1f1f4 !important",
        },
        ".ag-column-select-column-label": {
            "order": "-1 !important",
            "margin-right": "auto !important",
            "color": "#71717a !important",
            "font-size": "12.5px !important",
        },
        ".ag-column-select-column:has(.ag-checked) .ag-column-select-column-label": {
            "color": "#18181d !important",
            "font-weight": "500 !important",
        },
        ".ag-column-select-column .ag-drag-handle": {
            "display": "none !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper": {
            "width": "36px !important",
            "height": "20px !important",
            "border-radius": "999px !important",
            "background": "#e6e6eb !important",
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
            "background": "#5a4ad9 !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked::after": {
            "content": "'' !important",
            "left": "18px !important",
        },
        ".ag-column-select-column .ag-checkbox-input": {
            "cursor": "pointer !important",
        },
        ".ag-side-bar[data-active-panel='pivotePanel'] .ag-column-select": {
            "display": "none !important",
        },

        # ── Panel modo pivote / drop zones (NUEVO ESTILIZADO) ──
        ".ag-pivot-mode-panel": {
            "padding": "10px 12px !important",
            "border-bottom": "1px solid #e6e6eb !important",
            "min-height": "0 !important",
        },
        ".ag-pivot-mode-select": {
            "color": "#4938b8 !important",
            "font-size": "13px !important",
            "font-weight": "600 !important",
        },
        # Títulos de sección (Grupos de filas / Valores)
        ".ag-column-drop-vertical-title-bar": {
            "padding": "10px 12px 4px !important",
        },
        ".ag-column-drop-vertical-title": {
            "color": "#a2a2ad !important",
            "font-size": "11px !important",
            "font-weight": "600 !important",
            "text-transform": "uppercase !important",
            "letter-spacing": "0.06em !important",
        },
        # Zona de arrastre (drop zone)
        ".ag-column-drop-vertical": {
            "background": "transparent !important",
        },
        ".ag-column-drop-vertical-list": {
            "margin": "4px 10px 10px !important",
            "border": "1.5px dashed #d4cdf7 !important",
            "border-radius": "10px !important",
            "background": "#f5f3fe !important",
            "padding": "8px !important",
        },
        ".ag-column-drop-empty-message": {
            "color": "#7a6de0 !important",
            "font-size": "12px !important",
            "text-align": "center !important",
        },
        # Pastillas de campos (Suma(...), Promedio(...))
        ".ag-column-drop-vertical-cell": {
            "background": "#f6f6f8 !important",
            "border": "1px solid #e6e6eb !important",
            "border-radius": "999px !important",
            "padding": "5px 12px !important",
            "margin": "3px 0 !important",
            "font-size": "12px !important",
            "color": "#3f3f46 !important",
        },
        ".ag-column-drop-vertical-cell:hover": {
            "background": "#f0edfe !important",
            "border-color": "#d4cdf7 !important",
        },
        ".ag-column-drop-vertical-cell-text": {
            "font-size": "12px !important",
        },
        ".ag-column-drop-cell-button": {
            "color": "#a2a2ad !important",
        },
        ".ag-column-drop-cell-button:hover": {
            "color": "#5a4ad9 !important",
        },
        # ── Fin del nuevo bloque ──
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

    tema_grid = "balham"
    if es_inventario:
        tema_grid = "material"
        custom_css[".ag-row-even"] = {"background-color": "#ffffff !important"}
        custom_css[".ag-row-odd"] = {"background-color": "#ffffff !important"}
        custom_css[".ag-root-wrapper"].update({
            "background-color": "#f6f6f8 !important",
            "border": "none !important",
            "box-shadow": "none !important",
            "border-radius": "4px !important",
        })
        custom_css[".ag-header"].update({
            "background-color": "#ffffff !important",
            "border-bottom": "2px solid #6c5ce7 !important",
        })
        custom_css[".ag-tool-panel-horizontal-resize"] = {
            "width": "8px !important",
            "background-color": "#e6e6eb",
            "cursor": "col-resize",
        }
        custom_css[".ag-header-cell"].update({
            "background-color": "#ffffff !important",
        })
        custom_css[".ag-header-cell-text"].update({
            "color": "#71717a !important",
            "font-weight": "600",
            "letter-spacing": "0.05em",
            "text-transform": "uppercase",
        })
        custom_css[".ag-header-icon"].update({
            "color": "#a2a2ad !important",
        })
        custom_css[".ag-row-pinned"].update({
            "background-color": "#e7e3fb !important",
            "border-top": "2px solid #6c5ce7 !important",
            "color": "#3b2e93 !important",
        })
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar"] = {"width": "8px"}
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-track"] = {
            "background": "#e6e6eb", "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb"] = {
            "background": "#6c5ce7", "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb:hover"] = {
            "background": "#5a4ad9",
        }
        custom_css[".ag-side-bar"].update({
            "background-color": "#f7f6fb !important",
            "border": "1px solid #e6e6eb !important",
            "border-left": "1px solid #e6e6eb !important",
            "border-bottom": "1px solid #e6e6eb !important",
            "border-radius": "10px !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "box-shadow": "0 4px 14px rgba(15,23,42,0.08) !important",
            "margin": "4px 6px 6px 12px !important",
            "overflow": "hidden !important",
        })
        custom_css[".ag-side-bar .ag-side-buttons"].update({
            "background-color": "#f2f0fb !important",
            "border-bottom": "1px solid #e6e6eb !important",
        })
        custom_css[".ag-root"] = {
            "border": "2px solid #6c5ce7",
            "border-radius": "6px",
        }
        custom_css[".ag-filter-toolpanel"].update({
            "border": "1px solid #6c5ce7 !important",
            "border-radius": "8px !important",
            "margin": "8px !important",
            "overflow": "hidden !important",
        })

    if es_requerimientos:
        custom_css[".ag-side-button.ag-selected"] = {
            "background-color": "#52525c !important",
            "color": "#f6f6f8 !important",
            "box-shadow": "inset 0 0 0 1px #71717a",
        }
        custom_css[".ag-side-button:hover"] = {
            "background-color": "#e6e6eb !important",
            "color": "#18181d !important",
        }
        custom_css[".ag-header-icon"] = {"color": "#a2a2ad !important"}
        custom_css[".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked"] = {
            "background": "#71717a !important",
        }
        custom_css[".ag-row-pinned"] = {
            "background-color": "#e6e6eb !important",
            "font-weight": "700 !important",
            "border-top": "2px solid #71717a !important",
            "color": "#101014 !important",
            "font-size": f"{font_px + 1}px !important",
        }
        custom_css[".ag-row-hover"] = {"background-color": "#f1f1f4 !important"}
        custom_css[".ag-paging-button:hover:not(.ag-disabled)"] = {
            "background": "#e6e6eb !important",
            "border-color": "#a2a2ad !important",
            "color": "#52525c !important",
        }
        # Cabecera de grupos: banda lavanda con texto índigo profundo (CallAI)
        custom_css[".ag-header-group-cell"] = {"background-color": "#e7e3fb !important"}
        custom_css[".ag-header-group-cell-label"] = {"color": "#3b2e93 !important"}
        custom_css[".ag-header-group-text"] = {
            "color": "#3b2e93 !important",
            "font-weight": "600 !important",
        }
        custom_css[".ag-header-group-cell .ag-icon"] = {"color": "#6c5ce7 !important"}
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

    # =======================================================================
    # MEDICIÓN DE RENDIMIENTO CON PERF
    # =======================================================================
    perf.set_df_info(df_grid, label=f"AgGrid ({reporte})")
    with perf.phase("AgGrid render"):
        AgGrid(
            df_grid, gridOptions=grid_options,
            height=(850 if es_requerimientos else 600),
            theme=tema_grid, custom_css=custom_css,
            fit_columns_on_grid_load=True, allow_unsafe_jscode=True,
            enable_enterprise_modules=True, key=f"grid_{reporte}",
        )

    inject_grid_health_check()

    if reporte in REPORTES_ESTILO_INVENTARIO:
        inject_pagination_v2()

    # === CAMBIO APLICADO: ahora también se inyecta para Ajuste de Inventario ===
    if es_requerimientos or es_ajuste:
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
        opciones_grid["headerHeight"] = int(font_px * 2 + 14)

    gb.configure_grid_options(**opciones_grid)
    grid_options = gb.build()

    custom_css = {
        ".ag-root-wrapper": {"background-color": "#ffffff", "border": "1px solid #e6e6eb", "border-radius": "8px", "width": "100% !important"},
        ".ag-header": {"background-color": "#f1f1f4", "border-bottom": "2px solid #6c5ce7"},
        ".ag-header-cell-text": {"color": "#18181d", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": "#52525c", "border-color": "#e6e6eb"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd": {"background-color": "#f6f6f8"},
        ".ag-row-hover": {"background-color": "#f0edfe !important"},
        ".ag-cell": {"color": "#52525c", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {"color": "#85858f", "background-color": "#f6f6f8", "border-top": "1px solid #e6e6eb", "font-size": "0.75rem"},
        ".ag-menu": {"background-color": "#ffffff", "color": "#18181d", "border": "1px solid #e6e6eb"},
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
            "<div style='background:#e7e3fb;border-top:2px solid #6c5ce7;"
            "border-radius:0 0 8px 8px;padding:6px 12px;"
            "font-size:13px;font-weight:700;color:#3b2e93;'>"
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
