"""
Tablas AgGrid (vista desktop y móvil) con formato financiero, totales
al pie, panel lateral de columnas y barra de paginación.

SALIDAS — Opción 3: pivot completo con AgGrid Enterprise
  • pivotMode: True  activa la tabla dinámica nativa de AgGrid
  • El usuario puede arrastrar columnas al área de Pivot, Fila y Valor
    directamente desde el panel lateral (sideBar habilitado)
  • Agregaciones disponibles: sum, avg, count, min, max
  • Totales de fila y columna activados (groupIncludeFooter / grandTotalRow)
"""

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils import _norm, buscar_columna, LOCALE_ES
from inyecciones import inject_grid_health_check, inject_pagination_v2


# ===========================================================================
# HELPER — reporte que usa pivot completo
# ===========================================================================

_REPORTES_PIVOT = {"Salidas"}


# ===========================================================================
# FUNCIÓN: AGGRID DESKTOP — con formato financiero y diseño mejorado
# ===========================================================================

def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px=14, cols_visibles=None):
    """Renderiza la tabla AgGrid en vista desktop.

    Para el reporte 'Salidas' activa el modo pivot completo de AgGrid
    Enterprise (Opción 3): el usuario puede arrastrar cualquier columna
    al área de Filas, Columnas o Valores desde el panel lateral, igual
    que en una tabla dinámica de Excel.

    cols_visibles: lista de columnas que arrancan VISIBLES en reportes
    normales. En modo pivot se ignora (AgGrid gestiona la visibilidad).
    """

    es_pivot = reporte in _REPORTES_PIVOT
    envolver_cabeceras = (reporte == "Inventario Valorizado")
    quitar_fondos      = (reporte == "Inventario Valorizado")
    es_inventario      = (reporte == "Inventario Valorizado")

    # ── Si es Salidas, delegamos al renderizador pivot ──────────────────
    if es_pivot:
        _renderizar_pivot_salidas(df_grid, reporte, font_px)
        return

    # ────────────────────────────────────────────────────────────────────
    # FLUJO NORMAL (todos los demás reportes)
    # ────────────────────────────────────────────────────────────────────

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
        _opciones_col_def["wrapHeaderText"]   = True
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
            if (v < 0)  return Object.assign({}, base, { backgroundColor: '#fee2e2', color: '#991b1b', borderRadius: '20px' });
            if (v === 0) return Object.assign({}, base, { backgroundColor: '#fef3c7', color: '#92400e', borderRadius: '20px' });
            if (v < 10) return Object.assign({}, base, { backgroundColor: '#ffedd5', color: '#9a3412', borderRadius: '20px' });
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
            if (params.value === null || params.value === undefined) return base;
            if (params.node && (params.node.group || params.node.rowPinned))
                return Object.assign({{}}, base, {{ fontWeight: '800' }});
            var maxv = {max_valorizado};
            var num  = Number(params.value);
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
            if (params.node && (params.node.group || params.node.rowPinned))
                return Object.assign({}, base, { fontWeight: '800' });
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
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                cellStyle=_stock_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 0, maximumFractionDigits: 0 });
                    }
                """))
        elif es_valorizado:
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"], minWidth=170,
                cellStyle=_valor_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """))
        elif es_precio:
            gb.configure_column(c, aggFunc="avg", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """))
        elif es_valor:
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    }
                """))
        else:
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                cellStyle=mono_style,
                valueFormatter=JsCode("""
                    function(params) {
                        if (params.value == null) return '';
                        return Number(params.value).toLocaleString('es-PE', {
                            minimumFractionDigits: 0, maximumFractionDigits: 2 });
                    }
                """))

    if col_producto and col_producto in df_grid.columns and col_producto not in grupos_sel:
        gb.configure_column(col_producto, pinned="left", minWidth=300)

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

    cols_valor  = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and
                   any(k in _norm(c) for k in ("valorizado", "total", "importe", "monto"))]
    cols_precio = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and
                   any(k in _norm(c) for k in ("precio", "promedio", "unitario", "costo"))]
    cols_stock  = [c for c in df_grid.columns
                   if pd.api.types.is_numeric_dtype(df_grid[c]) and "stock" in _norm(c)]

    primera_col  = list(df_grid.columns)[0] if len(df_grid.columns) > 0 else None
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
        "getRowStyle": get_row_style,
        "onGridSizeChanged": JsCode("function(params) { /* No auto-fit */ }"),
        "onFirstDataRendered": JsCode("function(params) { /* No auto-fit */ }"),
    }

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
        opciones_grid["headerHeight"] = int(font_px * 2.5 + 20)

    gb.configure_grid_options(**opciones_grid)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    custom_css = _get_custom_css_normal(font_px, es_inventario, envolver_cabeceras)

    AgGrid(
        df_grid.head(5000), gridOptions=grid_options, height=600,
        theme="material" if es_inventario else "balham",
        custom_css=custom_css,
        fit_columns_on_grid_load=False, allow_unsafe_jscode=True,
        enable_enterprise_modules=True, key=f"grid_{reporte}",
    )

    inject_grid_health_check()
    if reporte == "Inventario Valorizado":
        inject_pagination_v2()


# ===========================================================================
# FUNCIÓN PIVOT — exclusiva para el reporte Salidas
# ===========================================================================

def _renderizar_pivot_salidas(df_grid, reporte, font_px=14):
    """
    Tabla dinámica completa con AgGrid Enterprise para el reporte Salidas.

    Configuración inicial (el usuario puede cambiarla arrastrando columnas):
      • Filas   → Nombre Area  (si existe) o primera columna de texto
      • Columnas → Fecha (mes) o Nombre Familia
      • Valores  → Importe Total (suma)  +  Cantidad (suma)

    Funciones habilitadas:
      ✓ pivotMode: True          — modo pivot nativo de AgGrid
      ✓ Panel lateral expandido  — arrastra columnas entre Filas/Cols/Valores
      ✓ groupIncludeFooter       — subtotales por grupo de fila
      ✓ groupIncludeTotalFooter  — gran total al final
      ✓ suppressAggFuncInHeader  — cabeceras limpias sin "sum(Importe)"
      ✓ Formato S/ en columnas de importe
      ✓ Formato entero en columnas de cantidad
    """
    import streamlit as st

    st.caption(
        "📊 **Tabla dinámica** — arrastra columnas en el panel lateral "
        "(▶ Filas / ↔ Columnas / Σ Valores) para reorganizar la vista. "
        "También puedes cambiar la función de agregación (suma, promedio, conteo…)."
    )

    # ── Detectar columnas clave ──────────────────────────────────────────
    col_area     = buscar_columna(df_grid, "Nombre Area", "area")
    col_familia  = buscar_columna(df_grid, "Nombre Familia", "familia")
    col_producto = buscar_columna(df_grid, "Nombre Producto", "producto", "descripcion")
    col_fecha    = buscar_columna(df_grid, "Fecha", "fecha")
    col_cantidad = buscar_columna(df_grid, "Cantidad", "cantidad", "qty")
    col_importe  = buscar_columna(df_grid, "Importe Total", "importe", "total", "monto")
    col_precio   = buscar_columna(df_grid, "Precio Unitario", "precio unitario", "precio")

    # ── Si hay fecha, crear columna Mes (texto) para pivotar sobre ella ─
    col_mes = None
    if col_fecha:
        try:
            df_grid = df_grid.copy()
            df_grid[col_fecha] = pd.to_datetime(df_grid[col_fecha], errors="coerce")
            df_grid["__Mes__"] = df_grid[col_fecha].dt.strftime("%Y-%m")
            col_mes = "__Mes__"
        except Exception:
            pass

    row_h    = max(28, min(60, font_px + 12))
    header_h = max(36, min(72, font_px + 20))   # un poco más alto en pivot

    gb = GridOptionsBuilder.from_dataframe(df_grid)

    # ── Columnas por defecto: todo habilitado para pivot ────────────────
    gb.configure_default_column(
        resizable=True, sortable=True, filter=True,
        editable=False,
        enableRowGroup=True,   # puede ir a "Filas"
        enablePivot=True,      # puede ir a "Columnas"
        enableValue=True,      # puede ir a "Valores"
        minWidth=90,
    )

    # ── Configuración inicial: columnas de FILA ──────────────────────────
    # Area → fila principal; Familia → segunda fila (si existe)
    if col_area:
        gb.configure_column(col_area,    rowGroup=True, hide=True)
    if col_familia:
        gb.configure_column(col_familia, rowGroup=True, hide=True)

    # ── Configuración inicial: columna de PIVOT (cabecera dinámica) ──────
    # Usar Mes si existe; si no, Familia; si no, la primera col de texto
    col_pivot_inicial = col_mes or col_familia or col_area
    if not col_pivot_inicial:
        for c in df_grid.columns:
            if not pd.api.types.is_numeric_dtype(df_grid[c]) and c not in (col_area, col_familia):
                col_pivot_inicial = c
                break
    if col_pivot_inicial:
        gb.configure_column(col_pivot_inicial, pivot=True, hide=True)

    # ── Configuración inicial: columnas de VALOR ─────────────────────────
    fmt_importe = JsCode("""
        function(params) {
            if (params.value == null) return '';
            return 'S/ ' + Number(params.value).toLocaleString('es-PE', {
                minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    """)
    fmt_cantidad = JsCode("""
        function(params) {
            if (params.value == null) return '';
            return Number(params.value).toLocaleString('es-PE', {
                minimumFractionDigits: 0, maximumFractionDigits: 0 });
        }
    """)

    mono = JsCode("function(params){ return { fontFamily: \"'Courier New', Courier, monospace\" }; }")

    if col_importe:
        gb.configure_column(
            col_importe, aggFunc="sum", type=["numericColumn"],
            valueFormatter=fmt_importe, cellStyle=mono,
            filter="agNumberColumnFilter",
        )
    if col_cantidad:
        gb.configure_column(
            col_cantidad, aggFunc="sum", type=["numericColumn"],
            valueFormatter=fmt_cantidad, cellStyle=mono,
            filter="agNumberColumnFilter",
        )
    if col_precio:
        gb.configure_column(
            col_precio, aggFunc="avg", type=["numericColumn"],
            valueFormatter=fmt_importe, cellStyle=mono,
            filter="agNumberColumnFilter",
        )

    # Formateo genérico para otras numéricas
    for c in df_grid.columns:
        if not pd.api.types.is_numeric_dtype(df_grid[c]):
            continue
        if c in (col_importe or "", col_cantidad or "", col_precio or ""):
            continue
        norm_c = _norm(c)
        if any(k in norm_c for k in ("importe", "total", "monto", "valor")):
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                valueFormatter=fmt_importe, cellStyle=mono,
                filter="agNumberColumnFilter")
        else:
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                valueFormatter=fmt_cantidad, cellStyle=mono,
                filter="agNumberColumnFilter")

    # ── Opciones del grid en modo pivot ──────────────────────────────────
    opciones_grid = {
        "pivotMode": True,                      # ← CLAVE: activa tabla dinámica
        "suppressAggFuncInHeader": True,         # cabeceras sin "sum(Importe Total)"
        "groupIncludeFooter": True,              # subtotal por cada grupo de fila
        "groupIncludeTotalFooter": True,         # gran total al final
        "autoGroupColumnDef": {
            "headerName": "Agrupación",
            "minWidth": 220,
            "cellRendererParams": {"suppressCount": False},
            "pinned": "left",
        },
        "localeText": LOCALE_ES,
        "suppressSizeToFit": True,
        "rowHeight": row_h,
        "headerHeight": header_h,
        "pivotColumnGroupTotals": "after",       # total de columna al final de cada grupo
        "pivotRowTotals": "right",               # total de fila a la derecha
        "cellSelection": True,
        "tooltipShowDelay": 300,

        # Panel lateral completo en modo pivot: muestra las 4 zonas
        # (Columnas disponibles / Filas / Columnas del pivot / Valores)
        "sideBar": {
            "toolPanels": [
                {
                    "id": "columns",
                    "labelDefault": "Tabla dinámica",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                    "toolPanelParams": {
                        # En modo pivot queremos TODOS los controles visibles
                        "suppressRowGroups": False,
                        "suppressValues": False,
                        "suppressPivots": False,
                        "suppressPivotMode": False,   # muestra el toggle de pivot
                        "suppressColumnFilter": False,
                        "suppressColumnSelectAll": False,
                        "suppressColumnExpandAll": False,
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
            "defaultToolPanel": "columns",   # abre el panel de tabla dinámica por defecto
            "position": "right",
        },

        # Estilo de la fila de totales (pinnedBottom no aplica en pivot;
        # los totales los gestiona AgGrid con groupIncludeTotalFooter)
        "getRowStyle": JsCode("""
            function(params) {
                if (params.node.footer) {
                    var depth = params.node.level;
                    if (depth === -1 || params.node.rowPinned) {
                        return { fontWeight:'700', backgroundColor:'#dbeafe',
                                 color:'#1e3a5f', borderTop:'2px solid #3b82f6',
                                 fontSize:'13px' };
                    }
                    return { fontWeight:'600', backgroundColor:'#f0f7ff',
                             color:'#1e40af' };
                }
            }
        """),
    }

    gb.configure_grid_options(**opciones_grid)
    # En modo pivot la paginación no es recomendable (rompe los totales de grupo);
    # se usa scrolling virtual en su lugar.
    gb.configure_pagination(enabled=False)
    grid_options = gb.build()

    custom_css = _get_custom_css_pivot(font_px)

    AgGrid(
        df_grid.head(5000), gridOptions=grid_options,
        height=620,
        theme="material",
        custom_css=custom_css,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,   # REQUERIDO para pivotMode
        key=f"grid_pivot_{reporte}",
    )

    inject_grid_health_check()


# ===========================================================================
# CSS — tabla normal
# ===========================================================================

def _get_custom_css_normal(font_px, es_inventario, envolver_cabeceras):
    css = {
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
        ".ag-header-cell": {"background-color": "#0f172a !important"},
        ".ag-header-cell-text": {
            "color": "#f8fafc !important",
            "font-weight": "700",
            "font-size": f"{font_px}px",
            "letter-spacing": "0.03em",
            "text-transform": "uppercase",
        },
        ".ag-header-icon": {"color": "#93c5fd !important"},
        ".ag-row": {"border-bottom": "1px solid #f1f5f9", "color": "#1e293b"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd":  {"background-color": "#f8fafc"},
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
        ".ag-paging-button": {
            "width": "28px !important", "height": "28px !important",
            "border": "1px solid #e2e8f0 !important",
            "background": "#ffffff !important",
            "border-radius": "6px !important",
            "color": "#475569 !important",
            "cursor": "pointer !important",
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "center !important",
            "margin": "0 2px !important",
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
        },
        ".ag-status-bar": {
            "background-color": "#f8fafc !important",
            "border-top": "1px solid #e2e8f0 !important",
            "color": "#475569 !important",
            "font-size": "12px !important",
        },
        ".ag-side-bar": {
            "background-color": "#ffffff",
            "border-left": "1px solid #e2e8f0 !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
        },
        ".ag-side-button": {
            "background-color": "#f8fafc !important",
            "border-bottom": "1px solid #e2e8f0 !important",
            "color": "#475569 !important",
        },
        ".ag-side-button.ag-selected": {
            "background-color": "#2563eb !important",
            "color": "#ffffff !important",
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
        ".ag-column-select-column .ag-checkbox-input-wrapper": {
            "width": "36px !important", "height": "20px !important",
            "border-radius": "999px !important",
            "background": "#e2e8f0 !important",
            "border": "none !important",
            "position": "relative !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper::after": {
            "content": "'' !important",
            "position": "absolute !important",
            "top": "2px !important", "left": "2px !important",
            "width": "16px !important", "height": "16px !important",
            "border-radius": "50% !important",
            "background": "#ffffff !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked": {
            "background": "#2563eb !important",
        },
        ".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked::after": {
            "content": "'' !important", "left": "18px !important",
        },
    }

    if envolver_cabeceras:
        css[".ag-header-cell-text"].update({
            "white-space": "normal !important",
            "overflow": "visible !important",
            "text-overflow": "clip !important",
            "line-height": "1.2 !important",
            "word-break": "break-word",
        })
        css[".ag-header-cell-label"] = {
            "white-space": "normal !important",
            "overflow": "visible !important",
            "align-items": "center",
        }

    if es_inventario:
        css[".ag-root-wrapper"].update({
            "background-color": "#f8fafc !important",
            "border": "none !important",
            "box-shadow": "none !important",
        })
        css[".ag-header"].update({
            "background-color": "#ffffff !important",
            "border-bottom": "2px solid #3b82f6 !important",
        })
        css[".ag-header-cell"].update({"background-color": "#ffffff !important"})
        css[".ag-header-cell-text"].update({
            "color": "#5f6368 !important",
            "font-weight": "600",
        })

    return css


# ===========================================================================
# CSS — tabla pivot (Salidas)
# ===========================================================================

def _get_custom_css_pivot(font_px):
    """CSS para la tabla pivot de Salidas — tema claro con acento azul."""
    return {
        # Contenedor principal sin borde duro (el panel lateral lo extiende)
        ".ag-root-wrapper": {
            "background-color": "#f8fafc !important",
            "border": "1px solid #e2e8f0 !important",
            "border-radius": "10px !important",
            "overflow": "hidden !important",
            "box-shadow": "0 4px 16px rgba(0,0,0,0.06) !important",
            "width": "100% !important",
        },
        # Cabecera del grid (primera fila de columnas estáticas)
        ".ag-header": {
            "background-color": "#1e3a5f !important",
            "border-bottom": "2px solid #3b82f6 !important",
        },
        ".ag-header-cell": {
            "background-color": "#1e3a5f !important",
        },
        ".ag-header-cell-text": {
            "color": "#e2e8f0 !important",
            "font-weight": "700",
            "font-size": f"{font_px}px",
            "letter-spacing": "0.03em",
            "text-transform": "uppercase",
        },
        ".ag-header-icon": {"color": "#93c5fd !important"},

        # Cabeceras de los grupos de columna dinámicas (filas superiores del pivot)
        ".ag-column-group-header": {
            "background-color": "#1e40af !important",
            "border-bottom": "1px solid #3b82f6 !important",
        },
        ".ag-column-group-header-name": {
            "color": "#dbeafe !important",
            "font-weight": "700 !important",
            "font-size": f"{font_px}px !important",
            "text-transform": "uppercase !important",
        },

        # Filas de datos
        ".ag-row": {"border-bottom": "1px solid #f1f5f9", "color": "#1e293b"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd":  {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},

        # Fila de subtotal de grupo (footer)
        ".ag-row-footer": {
            "background-color": "#f0f7ff !important",
            "font-weight": "600 !important",
            "color": "#1e40af !important",
            "border-top": "1px solid #bfdbfe !important",
        },
        # Gran total (nivel -1)
        ".ag-row-footer.ag-row-level--1": {
            "background-color": "#dbeafe !important",
            "font-weight": "700 !important",
            "color": "#1e3a5f !important",
            "border-top": "2px solid #3b82f6 !important",
            "font-size": f"{font_px + 1}px !important",
        },

        # Columna de agrupación fijada a la izquierda
        ".ag-pinned-left-header": {
            "background-color": "#1e3a5f !important",
            "border-right": "2px solid #3b82f6 !important",
        },
        ".ag-pinned-left-cols-container": {
            "box-shadow": "3px 0 10px rgba(30,58,95,0.12) !important",
            "border-right": "1px solid #e2e8f0 !important",
        },

        # Panel lateral (tabla dinámica)
        ".ag-side-bar": {
            "background-color": "#f6f8fb !important",
            "border-left": "1px solid #dbe2ec !important",
            "border-radius": "0 10px 10px 0 !important",
            "box-shadow": "0 4px 14px rgba(15,23,42,0.08) !important",
        },
        ".ag-side-bar .ag-side-buttons": {
            "background-color": "#eef2f7 !important",
            "border-bottom": "1px solid #dbe2ec !important",
        },
        ".ag-side-button": {
            "background-color": "#f8fafc !important",
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
        },
        ".ag-tool-panel-wrapper": {
            "background-color": "#ffffff !important",
        },

        # Zonas arrastrables del panel (Filas / Columnas / Valores)
        ".ag-column-drop": {
            "background-color": "#f0f7ff !important",
            "border": "1px dashed #93c5fd !important",
            "border-radius": "6px !important",
            "margin": "4px !important",
            "min-height": "36px !important",
        },
        ".ag-column-drop-title": {
            "color": "#1e40af !important",
            "font-weight": "600 !important",
            "font-size": "11px !important",
            "text-transform": "uppercase !important",
            "letter-spacing": "0.05em !important",
        },
        ".ag-column-drop-cell": {
            "background-color": "#dbeafe !important",
            "border": "1px solid #93c5fd !important",
            "border-radius": "4px !important",
            "color": "#1e3a5f !important",
            "font-size": "11px !important",
        },
        ".ag-column-drop-cell:hover": {
            "background-color": "#bfdbfe !important",
        },

        # Toggle de modo pivot
        ".ag-pivot-mode-panel": {
            "background-color": "#eff6ff !important",
            "border-bottom": "1px solid #dbe2ec !important",
            "padding": "6px 10px !important",
        },
        ".ag-pivot-mode-select": {
            "color": "#1e3a5f !important",
            "font-weight": "600 !important",
            "font-size": "12px !important",
        },

        # Scrollbar
        ".ag-body-vertical-scroll::-webkit-scrollbar": {"width": "8px"},
        ".ag-body-vertical-scroll::-webkit-scrollbar-track": {
            "background": "#e2e8f0", "border-radius": "4px",
        },
        ".ag-body-vertical-scroll::-webkit-scrollbar-thumb": {
            "background": "#3b82f6", "border-radius": "4px",
        },
        ".ag-body-vertical-scroll::-webkit-scrollbar-thumb:hover": {
            "background": "#2563eb",
        },
    }


# ===========================================================================
# FUNCIÓN: AGGRID MÓVIL (ANCHO COMPLETO)
# ===========================================================================

def renderizar_aggrid_movil(df_grid, columnas_fijas, reporte, font_px=14):
    """Renderiza la tabla AgGrid optimizada para vista móvil.
    El modo pivot no se activa en móvil (demasiado estrecho para usarlo).
    """
    envolver_cabeceras = (reporte == "Inventario Valorizado")

    gb = GridOptionsBuilder.from_dataframe(df_grid)
    _opciones_col_def = dict(
        resizable=True, sortable=True, filter=True,
        editable=False, groupable=False, enableRowGroup=False,
        enablePivot=False,
        menuTabs=["filterMenuTab", "generalMenuTab", "columnsMenuTab"],
    )
    if envolver_cabeceras:
        _opciones_col_def["wrapHeaderText"]   = True
        _opciones_col_def["autoHeaderHeight"] = True
    gb.configure_default_column(**_opciones_col_def)

    for i, col in enumerate(df_grid.columns):
        if i < columnas_fijas:
            gb.configure_column(col, pinned="left")
        if pd.api.types.is_numeric_dtype(df_grid[col]):
            af = "avg" if ("precio" in _norm(col) or "promedio" in _norm(col)) else "sum"
            gb.configure_column(col, aggFunc=af, type=["numericColumn"],
                                valueFormatter="x == null ? '' : x.toLocaleString()")

    row_h    = max(28, min(60, font_px + 12))
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
        ".ag-root-wrapper": {
            "background-color": "#ffffff",
            "border": "1px solid #e2e8f0",
            "border-radius": "8px",
            "width": "100% !important",
        },
        ".ag-header": {"background-color": "#f1f5f9", "border-bottom": "2px solid #3b82f6"},
        ".ag-header-cell-text": {"color": "#1e293b", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": "#334155", "border-color": "#e2e8f0"},
        ".ag-row-even": {"background-color": "#ffffff"},
        ".ag-row-odd":  {"background-color": "#f8fafc"},
        ".ag-row-hover": {"background-color": "#eff6ff !important"},
        ".ag-cell": {"color": "#334155", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {
            "color": "#64748b",
            "background-color": "#f8fafc",
            "border-top": "1px solid #e2e8f0",
            "font-size": "0.75rem",
        },
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
