"""tablas.desktop - vista de tabla principal (escritorio).

La mas completa: formato financiero, totales al pie, panel lateral de
columnas, paginacion y maximizado.
"""

import hashlib
import json

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils import _norm, buscar_columna, LOCALE_ES
from inyecciones import inject_grid_health_check, inject_pagination_v2, inject_maximize_aggrid, inject_dynamic_grid_height, inject_fix_column_panel_ajuste, inject_alinear_cabecera_ajuste, inject_filtros_grid
from perf import perf
from tema import (
    ACENTO, ACENTO_FUERTE, ACENTO_TEXTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA_FONDO, ADVERTENCIA_TEXTO, BLANCO, CELDA_ALERTA_FONDO, CELDA_ALERTA_TEXTO, CELDA_NEG_FONDO, CELDA_POS_TEXTO, DANGER_TEXT, ERROR_FONDO, EXIT_HOVER, GRIS_BORDE, GRIS_FONDO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE, ICON_MUTED, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FILA, LAVANDA_FILA_ALT, LAVANDA_FOCO, LAVANDA_FONDO, LAVANDA_MEDIO, LAVANDA_SELECCION, SCROLL_THUMB, TEXTO_PRINCIPAL,
)
from tablas._config import _config_sidebar, _estilo_fila, _estilos_celda, _fila_totales, _titulo_es
from tablas._css import _css_base, _css_franjas_sidebar


# Alto de cada fila de las listas virtuales de los paneles laterales
# (Columnas / Modo pivote). La pastilla mide 34px (padding 6px + borde 1px +
# label de 13px con nowrap) y los 4px restantes son la separación.
# Este número lo comparten TRES cosas y tienen que coincidir o el scroll se
# rompe: la variable --ag-list-item-height (con la que AG Grid virtualiza),
# la altura del .ag-virtual-list-item en el DOM, y nada más — desde
# 2026-08-05 ya no hay JS reposicionando ítems (ver arquitectura.md #29).
_ALTO_FILA_PANEL = 38


def renderizar_aggrid_desktop(df_grid, grupos_sel, cols_mostrar, reporte, font_px=14,
                              cols_visibles=None, df_totales=None, filtros_grid=None):
    """Renderiza la tabla AgGrid en vista desktop con formato financiero y diseño premium.

    cols_visibles: lista de columnas que arrancan VISIBLES. El resto se oculta
    por defecto y el usuario las activa desde la barra lateral (panel "Columnas").
    Si es None, se muestran todas.

    filtros_grid: filterModel de AG Grid (dict) para aplicar EN EL NAVEGADOR en
        vez de filtrar el DataFrame en Python. Cuando viene, `df_grid` llega SIN
        filtrar por esos criterios y el filtro se manda por el puente
        (`inject_filtros_grid`). Es 5-6x mas rapido porque no cambia la
        identidad de las filas y AG Grid no reagrupa (arquitectura.md #33/#34).
        Si es None, comportamiento clasico: se dibuja lo que venga en df_grid.

    df_totales: DataFrame a usar SOLO para la fila de totales. Va de la mano de
        `filtros_grid`: como df_grid llega sin filtrar, el total se calcula
        aparte sobre el df que Python si filtro. Asi la fila de totales sigue
        siendo `pinnedTopRowData` con su estilo de siempre y muestra el total
        de lo filtrado, igual que antes del cambio. Si es None, se usa df_grid.
    """

    # DISEÑO UNIFICADO: todos los reportes usan el estilo plano de Ajuste
    # (cabeceras envueltas, sin fondos semáforo por valor). es_inventario
    # sigue acotado: controla colores de grupo y panel pivote.
    envolver_cabeceras = True
    quitar_fondos = True
    # DISEÑO UNIFICADO: todos los grids desktop reciben el tratamiento
    # completo de Ajuste (grupos coloreados, paginación v2, panel lateral
    # con Modo pivote, maximizar y altura dinámica).
    es_inventario = True
    es_salidas = (reporte == "Salidas")
    es_requerimientos = (reporte == "Requerimientos")
    es_ajuste = (reporte == "Ajuste de Inventario")

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

    (mono_style, stock_cell_style, stock_cell_style_plano,
     valorizado_bar_style, valorizado_plano) = _estilos_celda(max_valorizado)

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
    # Con filtros_grid, df_grid viene SIN filtrar (el filtro lo aplica el
    # navegador), asi que el total se calcula sobre el df que Python si filtro.
    _df_tot = df_totales if df_totales is not None else df_grid
    fila_totales = _fila_totales(_df_tot, cols_valor, cols_precio, cols_stock, primera_col)

    get_row_style = _estilo_fila(col_stock, df_grid, es_inventario, quitar_fondos)
    _sidebar_cfg = _config_sidebar(mostrar_pivot=True, es_ajuste=True)

    _reporte_js = str(reporte).replace("\\", "\\\\").replace('"', '\\"')

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
        # ── Filtro EXTERNO: el que aplican los chips ─────────────────────
        # Se usa filtro externo y NO un filterModel por columna porque las
        # columnas de los chips (AREA, FAMILIA) son rowGroup + hide: AG Grid
        # DESCARTA el modelo de un set filter en ese caso -- verificado
        # llamando setFilterModel a mano, getFilterModel devuelve {}.
        # De paso el filtro externo COMPONE con los filtros propios de la
        # grilla en vez de reemplazarlos, que es lo que haria setFilterModel.
        # El spec lo deja `inject_filtros_grid` en window.__filtroExterno.
        "isExternalFilterPresent": JsCode("""
            function() {
                var s = window.__filtroExterno;
                return !!(s && Object.keys(s).length);
            }
        """),
        "doesExternalFilterPass": JsCode("""
            function(node) {
                var s = window.__filtroExterno;
                if (!s || !node.data) return true;
                for (var col in s) {
                    var c = s[col], v = node.data[col];
                    if (c.tipo === 'set') {
                        if (c.valores.indexOf(String(v)) === -1) return false;
                    } else if (c.tipo === 'num') {
                        var n = Number(v);
                        if (isNaN(n)) return false;
                        if (c.op === 'ne' && n === c.valor) return false;
                        if (c.op === 'lt' && !(n <  c.valor)) return false;
                        if (c.op === 'gt' && !(n >  c.valor)) return false;
                    } else if (c.tipo === 'abs_gte') {
                        var a = Math.abs(Number(v));
                        if (isNaN(a) || a < c.valor) return false;
                    }
                }
                return true;
            }
        """),
        "onGridSizeChanged": JsCode("function(params) { params.api.sizeColumnsToFit(); }"),
        "onGridReady": JsCode(f"""
            function(params) {{
                // Handle de la API para diagnostico. Sin esto NO se puede
                // medir nada de AG Grid desde afuera: la api vive en el state
                // de React y no hay otra via de acceso. Con esto, desde la
                // consola del padre:
                //   var f = [...document.querySelectorAll('iframe')]
                //             .find(x => (x.title||'').includes('agGrid'));
                //   f.contentWindow.__agApi.setGridOption('rowData', d)
                // Es lo que permitio medir el costo por interaccion
                // (arquitectura.md #33). Vive dentro del iframe del grid.
                try {{ window.__agApi = params.api; }} catch(e) {{}}

                // Puente de filtros: escucha los modelos que manda
                // inject_filtros_grid y los aplica SIN que cambien los datos.
                // Ver arquitectura.md #34 y el docstring de esa inyeccion.
                try {{
                    if (!window.__filtrosCh) {{
                        window.__filtrosCh = new BroadcastChannel('_filtros_grid');
                        window.__filtrosCh.onmessage = function(ev) {{
                            var m = ev.data;
                            if (!m || m.tipo !== 'aplicar') return;
                            try {{
                                // Un sello ya aplicado se acusa igual (para que
                                // el emisor deje de reintentar) pero NO se
                                // vuelve a aplicar: setFilterModel cuesta
                                // ~130 ms y la mayoria de los reruns no cambian
                                // los filtros.
                                if (window.__ultimoSello !== m.sello) {{
                                    window.__filtroExterno = m.modelo || {{}};
                                    window.__agApi.onFilterChanged();
                                    window.__ultimoSello = m.sello;
                                }}
                                var ack = new BroadcastChannel('_filtros_grid_ack');
                                ack.postMessage({{sello: m.sello}});
                                ack.close();
                            }} catch(e) {{}}
                        }};
                    }}
                }} catch(e) {{}}
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
        # Totales ANCLADOS ARRIBA (bajo el encabezado): siempre visibles,
        # sin importar cuántas filas haya ni el alto del grid.
        opciones_grid["pinnedTopRowData"] = [fila_totales]
    else:
        opciones_grid["grandTotalRow"] = "bottom"

    agrupar_on = bool(grupos_sel)
    if agrupar_on:
        for c in grupos_sel:
            if c in df_grid.columns:
                gb.configure_column(c, rowGroup=True, hide=True)

        if es_inventario:
            opciones_grid["groupDisplayType"] = "groupRows"
            opciones_grid["onColumnPivotModeChanged"] = JsCode("""
                function(params) {
                    try {
                        var pivotOn = params.api.isPivotMode
                            ? params.api.isPivotMode() : false;
                        params.api.setGridOption(
                            'groupDisplayType',
                            pivotOn ? 'multipleColumns' : 'groupRows'
                        );
                    } catch (e) {}
                }
            """)

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
                        return '<span style="font-weight:600;color:{TEXTO_PRINCIPAL}">' + nombre +
                               '</span> <span style="color:{ICON_MUTED};font-weight:400">(' +
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

    # DISEÑO UNIFICADO: el atributo data-active-panel (del que dependen
    # TODOS los estilos de pastillas/toggles del sidebar) se marca en
    # todos los reportes, no solo en Ajuste. Esto sí es universal a
    # propósito (a diferencia del bloque de agrupación/pivote de abajo).
    opciones_grid["onToolPanelVisibleChanged"] = JsCode("""
        function(params) {
            try {
                var open = (params.api && params.api.getOpenedToolPanel)
                    ? params.api.getOpenedToolPanel() : null;
                var sb = document.querySelector('.ag-side-bar');
                if (sb) sb.setAttribute('data-active-panel', open || '');

                window.clearTimeout(window.__ajusteFitTimer);
                window.__ajusteFitTimer = window.setTimeout(function() {
                    try { params.api.sizeColumnsToFit(); } catch(e) {}
                }, 150);
            } catch(e) {}
        }
    """)

    # Agrupación + pivote por defecto: SOLO Ajuste — su "cascada" vive de
    # esto (Familia > Subfamilia > Producto agrupados, Precio/Stock/Ajuste
    # como values). Hasta 2026-08-07 vivía en un `if True:` que lo aplicaba
    # a TODOS los reportes (arquitectura.md #40): con pivotMode=True forzado
    # y 0 rowGroups reales en reportes cuyas columnas no matchean estos
    # nombres, AG Grid colapsaba la grilla entera (Ventas: 0 columnas/0
    # filas mostradas; Inventario Valorizado: 1 sola fila agregada). Grep
    # `es_ajuste` antes de volver a ensanchar este bloque.
    if es_ajuste:
        _grupos_ini = []
        for _term in ("Familia", "Subfamilia", "Producto", "Unidad Medida", "Area"):
            _rc = buscar_columna(df_grid, _term)
            if _rc and _rc in df_grid.columns and _rc not in _grupos_ini:
                _grupos_ini.append(_rc)
        for _i, _c in enumerate(_grupos_ini):
            gb.configure_column(_c, rowGroup=True, rowGroupIndex=_i, hide=True)

        _valores_ini = []
        for _term, _af in (
            ("Precio Promedio",   "avg"),
            ("Stock al Cierre",   "sum"),
            ("Stock Declarado",   "sum"),
            ("Ajuste",            "sum"),
            ("Ajuste Valorizado", "sum"),
        ):
            _rc = buscar_columna(df_grid, _term)
            if _rc and _rc in df_grid.columns and _rc not in _valores_ini:
                gb.configure_column(_rc, aggFunc=_af, enableValue=True)
                _valores_ini.append(_rc)

        for _c in df_grid.columns:
            if (pd.api.types.is_numeric_dtype(df_grid[_c])
                    and _c not in _valores_ini and _c not in _grupos_ini):
                gb.configure_column(_c, aggFunc=None)

        opciones_grid["pivotMode"] = True
        opciones_grid["groupDefaultExpanded"] = 0

    # ── Quitar del panel de Filtros las columnas que se manejan con chips
    # externos ── universal: cualquier reporte cuyos chips filtren Área/
    # Familia/Ajuste, no solo Ajuste de Inventario (Inventario Valorizado y
    # Salidas también filtran Área/Familia por chip — ver REPORTES en data.py).
    col_area = buscar_columna(df_grid, "Nombre Area", "Area", "AREA")
    col_fam = buscar_columna(df_grid, "Nombre Familia", "Familia", "FAMILIA")
    col_aj = buscar_columna(df_grid, "Ajuste", "AJUSTE")
    col_ajval = buscar_columna(df_grid, "Ajuste Valorizado", "AJUSTE VALORIZADO")
    for _c in df_grid.columns:
        if _c in (col_area, col_fam, col_aj, col_ajval):
            # suppressFiltersToolPanel las esconde del panel "Filtros"
            # PERO el filtro sigue funcionando: es lo que permite que el
            # puente les aplique un filterModel sin que aparezcan dos
            # controles para lo mismo (el chip y la pastilla del panel).
            gb.configure_column(_c, suppressFiltersToolPanel=True)

    # Cabeceras en "Nombre Propio": VA ÚLTIMO A PROPÓSITO (universal). El
    # configure_column de st_aggrid reconstruye el colDef con
    # headerName = nombre del campo cuando no se le pasa header_name,
    # así que CUALQUIER configure_column posterior pisa el título en
    # español. Estaba antes del loop de suppressFiltersToolPanel y por
    # eso AJUSTE / AJUSTE VALORIZADO / AREA / FAMILIA salían en
    # MAYÚSCULAS mientras el resto salía capitalizado.
    for _c in df_grid.columns:
        gb.configure_column(_c, headerName=_titulo_es(_c))

    gb.configure_grid_options(**opciones_grid)
    if es_salidas:
        gb.configure_pagination(enabled=False)
    else:
        gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    custom_css = _css_base(font_px)

    # Totales anclados ARRIBA en este grid: el acento separador va DEBAJO
    # de la fila total (la base trae border-top, pensado para pie de tabla,
    # que Compras sigue usando).
    custom_css[".ag-row-pinned"].update({
        "border-top": "none !important",
        "border-bottom": f"2px solid {ACENTO} !important",
    })

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
        custom_css[".ag-row-even"] = {"background-color": f"{BLANCO} !important"}
        custom_css[".ag-row-odd"] = {"background-color": f"{BLANCO} !important"}

        custom_css[".ag-root-wrapper"].update({
            "background-color": "transparent !important",
            "border": "none !important",
            "border-radius": "0 !important",
            "box-shadow": "none !important",
            "overflow": "visible !important",
        })
        custom_css[".ag-root-wrapper-body"] = {
            "background": "transparent !important",
            "overflow": "visible !important",
        }
        custom_css[".ag-root"] = {
            "background-color": f"{BLANCO} !important",
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "12px !important",
            "box-shadow": ("0 1px 2px rgba(16,16,20,0.05), "
                           "0 4px 14px rgba(16,16,20,0.07) !important"),
            "overflow": "hidden !important",
        }
        custom_css["html, body"] = {"background": "transparent !important"}

        custom_css[".ag-header"].update({
            "background-color": f"{LAVANDA_FONDO} !important",
            "border-bottom": f"1px solid {ACENTO} !important",
        })
        custom_css[".ag-header-cell"].update({
            "background-color": f"{LAVANDA_FONDO} !important",
        })
        custom_css[".ag-header-cell-text"].update({
            "color": f"{ACENTO_TEXTO_OSCURO} !important",
            "font-weight": "500",
            "letter-spacing": "normal",
            "text-transform": "none",
        })
        custom_css[".ag-header-icon"].update({
            "color": f"{GRIS_TEXTO_SUAVE} !important",
        })
        custom_css[".ag-row-pinned"].update({
            "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
            "border-top": "none !important",
            "border-bottom": f"2px solid {ACENTO} !important",
            "color": f"{ACENTO_TEXTO_OSCURO} !important",
        })

        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar"] = {"width": "11px"}
        custom_css[".ag-body-horizontal-scroll::-webkit-scrollbar"] = {"height": "11px"}
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-track"] = {"background": "transparent"}
        custom_css[".ag-body-horizontal-scroll::-webkit-scrollbar-track"] = {"background": "transparent"}
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb"] = {
            "background": "transparent", "border-radius": "8px",
            "border": "3px solid transparent", "background-clip": "padding-box",
        }
        custom_css[".ag-body-horizontal-scroll::-webkit-scrollbar-thumb"] = {
            "background": "transparent", "border-radius": "8px",
            "border": "3px solid transparent", "background-clip": "padding-box",
        }
        custom_css[".ag-body-vertical-scroll:hover::-webkit-scrollbar-thumb"] = {
            "background": f"{SCROLL_THUMB}", "background-clip": "padding-box",
        }
        custom_css[".ag-body-horizontal-scroll:hover::-webkit-scrollbar-thumb"] = {
            "background": f"{SCROLL_THUMB}", "background-clip": "padding-box",
        }
        custom_css[".ag-body-vertical-scroll::-webkit-scrollbar-thumb:hover"] = {
            "background": f"{LAVANDA_FOCO}", "background-clip": "padding-box",
        }
        custom_css[".ag-body-horizontal-scroll::-webkit-scrollbar-thumb:hover"] = {
            "background": f"{LAVANDA_FOCO}", "background-clip": "padding-box",
        }
        custom_css[".ag-body-horizontal-scroll::-webkit-scrollbar-corner"] = {
            "background": "transparent",
        }

        custom_css[".ag-side-bar"].update({
            "background-color": f"{LAVANDA_FILA} !important",
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-left": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "12px !important",
            "box-shadow": ("0 1px 2px rgba(16,16,20,0.05), "
                           "0 4px 14px rgba(16,16,20,0.07) !important"),
            "margin": "0 0 0 14px !important",
            "overflow": "hidden !important",
        })
        custom_css[".ag-side-bar .ag-side-buttons"].update({
            "background-color": f"{LAVANDA_FILA_ALT} !important",
            "border-bottom": f"1px solid {GRIS_BORDE} !important",
        })

        # Franjas lavanda del sidebar (superior + inferior), en las 3 pestañas.
        # Selectores con :not(.ag-hidden) para no des-ocultar los paneles
        # inactivos (bug de "paneles uno al costado del otro").
        custom_css.update(_css_franjas_sidebar())

        # Alto de fila de las listas virtuales (panel Columnas / Modo pivote).
        #
        # EL SELECTOR IMPORTA. AG Grid no lee esta variable del elemento que
        # uno esperaría: cuelga un div `.ag-measurement-container` del div de
        # TEMA (`ag-theme-params-N`, hermano/padre del .ag-root-wrapper) y lee
        # ahí. Puesta en `.ag-side-bar` no la ve; en `.ag-root-wrapper`
        # tampoco. El nombre lleva un sufijo numérico generado por instancia,
        # así que se matchea por prefijo.
        # Tampoco sirve ponerla en html/body: el div de tema DECLARA la
        # variable (`:where(.ag-theme-params-N){--ag-list-item-height:…}`) y
        # una declaración propia le gana a lo heredado, sea cual sea la
        # especificidad del ancestro. Hay que pisarla en ese mismo elemento
        # (`[class*=...]` tiene especificidad 0,1,0 y `:where()` tiene 0,0,0).
        #
        # Las pastillas son de alto FIJO (label con nowrap + ellipsis), así
        # que un valor uniforme es correcto.
        custom_css['[class*="ag-theme-params-"]'] = {
            "--ag-list-item-height": f"{_ALTO_FILA_PANEL}px",
        }

        custom_css[
            ".ag-side-bar[data-active-panel='columns'] .ag-virtual-list-item, "
            ".ag-side-bar[data-active-panel='pivotePanel'] .ag-virtual-list-item"
        ] = {
            "height": f"{_ALTO_FILA_PANEL}px !important",
            "overflow": "visible !important",
        }

        custom_css[
            ".ag-side-bar[data-active-panel='columns'] .ag-virtual-list-container, "
            ".ag-side-bar[data-active-panel='pivotePanel'] .ag-virtual-list-container"
        ] = {
            "overflow": "visible !important",
        }

    if es_requerimientos:
        custom_css[".ag-side-button.ag-selected"] = {
            "background-color": f"{EXIT_HOVER} !important",
            "color": f"{GRIS_FONDO} !important",
            "box-shadow": f"inset 0 0 0 1px {GRIS_TEXTO}",
        }
        custom_css[".ag-side-button:hover"] = {
            "background-color": f"{GRIS_BORDE} !important",
            "color": f"{TEXTO_PRINCIPAL} !important",
        }
        custom_css[".ag-header-icon"] = {"color": f"{GRIS_TEXTO_SUAVE} !important"}
        custom_css[".ag-column-select-column .ag-checkbox-input-wrapper.ag-checked"] = {
            "background": f"{GRIS_TEXTO} !important",
        }
        custom_css[".ag-row-pinned"] = {
            "background-color": f"{GRIS_BORDE} !important",
            "font-weight": "700 !important",
            "border-bottom": f"2px solid {GRIS_TEXTO} !important",
            "color": "#101014 !important",
            "font-size": f"{font_px + 1}px !important",
        }
        custom_css[".ag-row-hover"] = {"background-color": f"{GRIS_LINEA} !important"}
        custom_css[".ag-paging-button:hover:not(.ag-disabled)"] = {
            "background": f"{GRIS_BORDE} !important",
            "border-color": f"{GRIS_TEXTO_SUAVE} !important",
            "color": f"{EXIT_HOVER} !important",
        }
        custom_css[".ag-header-group-cell"] = {"background-color": f"{LAVANDA_CABECERA_GRUPO} !important"}
        custom_css[".ag-header-group-cell-label"] = {"color": f"{ACENTO_TEXTO_OSCURO} !important"}
        custom_css[".ag-header-group-text"] = {
            "color": f"{ACENTO_TEXTO_OSCURO} !important",
            "font-weight": "600 !important",
        }
        custom_css[".ag-header-group-cell .ag-icon"] = {"color": f"{ACENTO} !important"}
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
        custom_css[".ag-column-select-header"] = {
            "padding-top": "4px !important",
            "padding-bottom": "4px !important",
        }

    perf.set_df_info(df_grid, label=f"AgGrid ({reporte})")
    with perf.phase("AgGrid render"):
        AgGrid(
            df_grid, gridOptions=grid_options,
            # Respaldo compacto: la inyección ajusta este valor al alto real
            # de la ventana, pero no deja un bloque vacío excesivo si falla.
            height=(620 if es_requerimientos else 420),
            theme=tema_grid, custom_css=custom_css,
            fit_columns_on_grid_load=True, allow_unsafe_jscode=True,
            enable_enterprise_modules=True, key=f"grid_{reporte}",
        )

    # ── CAMBIO 1: pasa usa_pagination_v2 según el reporte ─────────────────
    inject_grid_health_check(usa_pagination_v2=True)

    inject_pagination_v2()
    inject_maximize_aggrid()
    inject_dynamic_grid_height(offset_px=260, min_px=320)
    inject_fix_column_panel_ajuste()
    inject_alinear_cabecera_ajuste()

    if filtros_grid is not None:
        # El sello identifica al modelo: si no cambio respecto del rerun
        # anterior el grid lo acusa pero no lo re-aplica (setFilterModel cuesta
        # ~130 ms y casi ningun rerun cambia los filtros).
        _sello = hashlib.md5(
            json.dumps(filtros_grid, sort_keys=True).encode()
        ).hexdigest()[:12]
        inject_filtros_grid(filtros_grid, _sello)
