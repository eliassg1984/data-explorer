"""
Tablas AgGrid (vista desktop y móvil) con formato financiero, totales
al pie, panel lateral de columnas y barra de paginación.
"""

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils import _norm, buscar_columna, LOCALE_ES
from inyecciones import inject_grid_health_check, inject_pagination_v2


# ===========================================================================
# FUNCIÓN: AGGRID DESKTOP — con formato financiero y diseño mejorado
# ===========================================================================

def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px=14, cols_visibles=None):
    """Renderiza la tabla AgGrid en vista desktop con formato financiero y diseño premium.

    cols_visibles: lista de columnas que arrancan VISIBLES. El resto se oculta
    por defecto y el usuario las activa desde la barra lateral (panel "Columnas").
    Si es None, se muestran todas.
    """

    # Envolver cabeceras en varias líneas (white-space: normal) SOLO para este
    # reporte. El resto de tablas mantiene la cabecera en una sola línea.
    envolver_cabeceras = (reporte == "Inventario Valorizado")

    # Quitar fondos de color (píldoras de stock, filas teñidas y barra del
    # valorizado) SOLO en este reporte. Se conserva todo el formato y la función.
    quitar_fondos = (reporte == "Inventario Valorizado")

    # Variaciones E y F SOLO para este reporte:
    #   E → agrupación en fila completa (groupDisplayType="groupRows")
    #   F → tema Material (Google design) con cabecera clara y acento rojo
    # Ambas son puramente visuales/de disposición: NO tocan totales, formato S/,
    # panel lateral, barra de estado, ni ninguna otra funcionalidad del grid.
    es_inventario = (reporte == "Inventario Valorizado")

    # ─────────────────────────────────────────────────────────────────
    # REORDENAR COLUMNAS (Producto, Stock, Precio, Valorizado)
    # ─────────────────────────────────────────────────────────────────
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

    # Máximo del valorizado para escalar las barras de datos
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
        # wrapHeaderText  → el texto de la cabecera salta de línea.
        # autoHeaderHeight → el alto de la cabecera se ajusta automáticamente.
        _opciones_col_def["wrapHeaderText"] = True
        _opciones_col_def["autoHeaderHeight"] = True
    gb.configure_default_column(**_opciones_col_def)

    # ── Fuente mono para columnas numéricas genéricas ──
    mono_style = JsCode("""
        function(params) {
            return { fontFamily: "'Courier New', Courier, monospace" };
        }
    """)

    # ── PÍLDORAS DE COLOR PARA EL STOCK (no mancha la fila entera) ──
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
            // Stock negativo (rojo)
            if (v < 0) {
                return Object.assign({}, base, { 
                    backgroundColor: '#fee2e2', 
                    color: '#991b1b', 
                    borderRadius: '20px' 
                });
            }
            // Stock en 0 (amarillo)
            if (v === 0) {
                return Object.assign({}, base, { 
                    backgroundColor: '#fef3c7', 
                    color: '#92400e', 
                    borderRadius: '20px' 
                });
            }
            // Stock bajo < 10 (naranja)
            if (v < 10) {
                return Object.assign({}, base, { 
                    backgroundColor: '#ffedd5', 
                    color: '#9a3412', 
                    borderRadius: '20px' 
                });
            }
            // Stock normal (verde oscuro)
            return Object.assign({}, base, { color: '#065f46' });
        }
    """)

    # ── Versión PLANA del stock: sin fondos de color, conserva mono/negrita/
    #    alineación a la derecha (solo cambia el color → texto oscuro neutro). ──
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

    # ── BARRA DE DATOS GRUESA PARA EL VALORIZADO ──
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

    # ── Versión PLANA del valorizado: sin barra de datos, conserva mono/negrita/
    #    alineación a la derecha y el formato S/ (solo se quita el fondo). ──
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

    # Elegimos el estilo con o sin fondos de color según el reporte.
    _stock_style = stock_cell_style_plano if quitar_fondos else stock_cell_style
    _valor_style = valorizado_plano       if quitar_fondos else valorizado_bar_style

    # ── Formateo por tipo de columna ──
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

    # ── Fijar columna Producto a la izquierda (más ancha para evitar cortes) ──
    if col_producto and col_producto in df_grid.columns and col_producto not in grupos_sel:
        gb.configure_column(col_producto, pinned="left", minWidth=300)

    # ── Columnas ocultas por defecto ──
    if cols_visibles is not None:
        visibles_norm = {_norm(c) for c in cols_visibles}
        # Salvaguarda: si NINGUNA columna del grid coincide con la lista de
        # "visibles", no ocultamos nada. Ocultarlas todas dejaría la tabla
        # completamente en blanco (cabecera vacía incluida). En ese caso es
        # preferible mostrar todas las columnas.
        hay_match = any(_norm(c) in visibles_norm for c in df_grid.columns)
        if hay_match:
            for c in df_grid.columns:
                if c in grupos_sel:
                    continue
                if _norm(c) not in visibles_norm:
                    gb.configure_column(c, hide=True)

    row_h    = max(28, min(60, font_px + 12))
    header_h = max(30, min(62, font_px + 14))

    # ── Fila de totales al pie ──
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

    # ── Estilo de fila para el semáforo (totales y alertas) ──
    # Si quitar_fondos está activo, NO se aplican los tintes por fila (rosa/
    # crema); se usa la rama de abajo, que solo estiliza la fila de totales.
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
    elif es_inventario:
        # Fila de totales en paleta azul (igual que el resto de reportes).
        get_row_style = JsCode("""
            function(params) {
                if (params.node.rowPinned === 'bottom') {
                    return { fontWeight:'700', backgroundColor:'#dbeafe', color:'#1e3a5f',
                             borderTop:'2px solid #3b82f6', fontSize:'13px' };
                }
            }
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

    # ── Configuración general del Grid ──
    opciones_grid = {
        "autoGroupColumnDef": {"minWidth": 200},
        "localeText": LOCALE_ES,
        "suppressSizeToFit": True,            # <--- CLAVE: evita que el grid se encoja y rompa el borde
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Columnas",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                    "toolPanelParams": {
                        "suppressRowGroups": True,
                        "suppressValues": True,
                        "suppressPivots": True,
                        "suppressPivotMode": True,
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
        "pinnedBottomRowData": [fila_totales],
        "cellSelection": True,
        "tooltipShowDelay": 300,
        # Barra de estado eliminada a pedido (la franja inferior "Filas: N").
        "getRowStyle": get_row_style,
        # Eliminamos los 'sizeColumnsToFit' para que las columnas no se encojan
        "onGridSizeChanged": JsCode("function(params) { /* No auto-fit */ }"),
        "onFirstDataRendered": JsCode("function(params) { /* No auto-fit */ }"),
    }

    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c in df_grid.columns:
                gb.configure_column(c, rowGroup=True, hide=True)

        if es_inventario:
            # ── Variación E: grupos en FILA COMPLETA (groupRows) ──
            # En vez de columnas de grupo, cada grupo es una fila ancha con su
            # nombre, el conteo de hijos y el subtotal del valorizado.
            # La fila de totales (pinnedBottom) y las agregaciones del resto de
            # columnas siguen funcionando igual.
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
                        return '<span style="font-weight:600;color:#1e293b">' + nombre +
                               '</span> <span style="color:#64748b;font-weight:400">(' +
                               n + ')' + extra + '</span>';
                    }}
                """)
            }
        else:
            opciones_grid["groupDisplayType"] = "multipleColumns"

        opciones_grid["groupDefaultExpanded"] = 0
        opciones_grid["pivotMode"] = False
    else:
        opciones_grid["pivotMode"] = False

    if envolver_cabeceras:
        # Reservamos altura para 2 líneas de cabecera. (autoHeaderHeight la
        # ajusta sola si el navegador lo soporta; si no, este alto fijo basta.)
        opciones_grid["headerHeight"] = int(font_px * 2.5 + 20)

    gb.configure_grid_options(**opciones_grid)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    # ── CSS personalizado (CON EL PANEL LATERAL ESTILIZADO) ──
    custom_css = {
        ".ag-root-wrapper": {
            "background-color": "#ffffff",
            "border": "1px solid #0f172a",          # Borde azul petróleo oscuro
            "border-radius": "10px !important",     # Redondeo elegante
            "overflow": "hidden !important",        # CLAVE: Cierra el marco perfectamente
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
        # ── Opción A Minimalista: paginación limpia en una sola franja ──
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
        # Selector de tamaño de página
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
        # Botones de navegación: estilo pill
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
        # Texto "X a Y de Z"
        ".ag-paging-row-summary-panel": {
            "color": "#64748b !important",
            "font-size": "12px !important",
            "margin-left": "auto !important",
        },
        ".ag-paging-row-summary-panel-number": {
            "color": "#1e293b !important",
            "font-weight": "600 !important",
        },
        # Status bar limpia, sin el fondo morado/rayado de AgGrid
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
        # ========== ESTILOS PARA EL PANEL LATERAL DE COLUMNAS (CORREGIDO) ==========
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
        # ── Borde del panel de filtros — igual que la tabla (balham) ──
        # Para Inventario Valorizado se sobreescribe más abajo con azul.
        ".ag-filter-toolpanel": {
            "border": "1px solid #0f172a !important",
            "border-radius": "8px !important",
            "margin": "8px !important",
            "overflow": "hidden !important",
        },

        # ================================================================
        # PANEL DE COLUMNAS COMO INTERRUPTORES (Opción B)
        # Cada columna es una fila con: etiqueta a la izquierda + toggle a
        # la derecha. El checkbox nativo de AgGrid se "disfraza" de switch.
        # ================================================================
        # Fila de cada columna: aire, divisor fino y etiqueta a la izquierda.
        ".ag-column-select-column": {
            "display": "flex !important",
            "align-items": "center !important",
            "padding": "10px 12px !important",
            "border-bottom": "0.5px solid #f1f5f9 !important",
        },
        # La etiqueta va primero (order -1) y empuja el toggle a la derecha.
        ".ag-column-select-column-label": {
            "order": "-1 !important",
            "margin-right": "auto !important",
            "color": "#475569 !important",
            "font-size": "12.5px !important",
        },
        # Resaltar la columna activa (navegadores con :has()).
        ".ag-column-select-column:has(.ag-checked) .ag-column-select-column-label": {
            "color": "#1e293b !important",
            "font-weight": "500 !important",
        },
        # Ocultamos la manijita de arrastre para un look limpio
        # (igual puedes reordenar arrastrando las cabeceras de la tabla).
        ".ag-column-select-column .ag-drag-handle": {
            "display": "none !important",
        },
        # ── El checkbox convertido en riel del interruptor ──
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
        # ── La perilla blanca (reemplaza el check del icono) ──
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
        # ── Estado encendido: riel azul + perilla a la derecha ──
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked": {
            "background": "#2563eb !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked::after": {
            "content": "'' !important",
            "left": "18px !important",
        },
        # El input transparente sigue cubriendo el switch para poder clicar.
        ".ag-column-select-column .ag-checkbox-input": {
            "cursor": "pointer !important",
        },
    }

    # ── Cabeceras envueltas en varias líneas (solo Inventario Valorizado) ──
    if envolver_cabeceras:
        # OJO: el tema Balham trae 'white-space: nowrap' con más especificidad,
        # por eso aquí va con !important; si no, gana el tema y sale «…».
        custom_css[".ag-header-cell-text"].update({
            "white-space": "normal !important",   # fuerza el salto de línea
            "overflow": "visible !important",     # quita el recorte
            "text-overflow": "clip !important",   # elimina los puntos «…»
            "line-height": "1.2 !important",
            "word-break": "break-word",
        })
        # El contenedor del texto también debe permitir varias líneas.
        custom_css[".ag-header-cell-label"] = {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "align-items": "center",
        }

    # ── Inventario Valorizado: tema Material con cabecera clara y acento AZUL ──
    # Reemplaza el subrayado rojo de marca por el azul de la paleta principal,
    # manteniendo todo el formato S/, totales, panel lateral y barra de estado.
    tema_grid = "balham"
    if es_inventario:
        tema_grid = "material"
        custom_css[".ag-root-wrapper"].update({
            "background-color": "#f8fafc !important",   # mismo fondo que la página
            "border": "none !important",                # sin borde
            "box-shadow": "none !important",            # sin sombra
            "border-radius": "4px !important",          # conserva el redondeo suave (opcional, si lo quieres quitar pon 0px)
        })
        custom_css[".ag-header"].update({
            "background-color": "#ffffff !important",
            "border-bottom": "2px solid #3b82f6 !important",   # azul en lugar de rojo
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
            "background-color": "#dbeafe !important",          # azul claro en lugar de rosado
            "border-top": "2px solid #3b82f6 !important",      # azul en lugar de rojo
            "color": "#1e3a5f !important",                     # azul oscuro en lugar de rojo oscuro
        })

        # ── Scrollbar azul personalizada (solo Inventario Valorizado) ──
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar"] = {
            "width": "8px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-track"] = {
            "background": "#e2e8f0",
            "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb"] = {
            "background": "#3b82f6",
            "border-radius": "4px",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb:hover"] = {
            "background": "#2563eb",
        }

        # ── Opción 3: panel lateral como TARJETA DESPEGADA (solo Inventario) ──
        # En vez de una franja pegada al borde de la tabla, el panel se separa
        # con un espacio a la izquierda y tiene su propio borde redondeado,
        # un tono claro y una sombra suave. `overflow: hidden` en el panel hace
        # que el contenido (pestañas y lista) se recorte a las esquinas
        # redondeadas. Los márgenes lo despegan de la tabla y de la paginación.
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
        # Franja de pestañas con un tono un poco más marcado que el cuerpo.
        custom_css[".ag-side-bar .ag-side-buttons"].update({
            "background-color": "#eef2f7 !important",
            "border-bottom": "1px solid #dbe2ec !important",
        })

        # ── Borde azul para el área de datos (solo Inventario Valorizado) ──
        custom_css[".ag-root"] = {
            "border": "2px solid #3b82f6",
            "border-radius": "6px",
        }

        # ── Borde del panel de filtros en azul (a juego con la tabla) ──
        custom_css[".ag-filter-toolpanel"].update({
            "border": "1px solid #3b82f6 !important",
            "border-radius": "8px !important",
            "margin": "8px !important",
            "overflow": "hidden !important",
        })

    AgGrid(
        df_grid.head(5000), gridOptions=grid_options, height=600,
        theme=tema_grid, custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_{reporte}",
    )

    inject_grid_health_check()

    # Barra de paginación v2 (números + salto) SOLO para Inventario Valorizado.
    if reporte == "Inventario Valorizado":
        inject_pagination_v2()


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

    AgGrid(
        df_grid.head(3000), gridOptions=grid_options, height=380,
        theme="balham", custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_movil_{reporte}",
    )

    inject_grid_health_check()
