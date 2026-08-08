"""tablas.compras - tablas propias del reporte de Compras.

Una sola funcion publica: renderizar_aggrid_compras, que consume el drill de
Compras (ver graficos/compras/).

Aca vivia tambien renderizar_tabla_compras, una segunda tabla AgGrid en modo
pivote que quedo sin llamadores tras el refactor de 2026-08-01. Se borro el
2026-08-08 (estaba "a la espera de decision" desde entonces). Si hace falta
una tabla pivote de Compras otra vez, recuperarla del historial de git antes
de reescribirla.
"""

import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils import _norm, buscar_columna, LOCALE_ES
from inyecciones import inject_grid_health_check, inject_pagination_v2, inject_maximize_aggrid, inject_dynamic_grid_height, inject_fix_column_panel_ajuste
from perf import perf
from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, BLANCO, GRIS_BORDE, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FILA, LAVANDA_FILA_ALT, LAVANDA_FONDO,
)
from tablas._config import _config_sidebar, _titulo_es
from tablas._css import _css_base, _css_franjas_sidebar


def renderizar_aggrid_compras(df_grid: pd.DataFrame, font_px: int = 14):
    gb = GridOptionsBuilder.from_dataframe(df_grid)
    gb.configure_default_column(
        resizable=True, filter=True, sortable=True, editable=False,
        enableRowGroup=True, enablePivot=True, enableValue=True,
        minWidth=100, wrapHeaderText=True, autoHeaderHeight=True,
        tooltipValueGetter=JsCode("function(params){ return params.value; }"),
    )

    _fmt_soles = JsCode("""
        function(params) {
            if (params.value == null) return '';
            return 'S/ ' + Number(params.value).toLocaleString('es-PE',
                { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    """)
    _fmt_num = JsCode("""
        function(params) {
            if (params.value == null) return '';
            return Number(params.value).toLocaleString('es-PE',
                { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    """)
    _mono = JsCode("""
        function(params) {
            return {
                fontFamily: "'Courier New',Courier,monospace",
                textAlign: 'right', paddingRight: '12px'
            };
        }
    """)
    _val_style = JsCode(
        "function(params) {"
        "    return {"
        "        fontFamily: \"'Courier New',Courier,monospace\","
        "        color: '" + ACENTO_TEXTO_OSCURO + "',"
        "        fontWeight: '600',"
        "        textAlign: 'right',"
        "        paddingRight: '12px'"
        "    };"
        "}"
    )

    for c in df_grid.columns:
        if not pd.api.types.is_numeric_dtype(df_grid[c]):
            continue
        n = _norm(c)
        gb.configure_column(c, filter="agNumberColumnFilter")
        if any(k in n for k in ("importe", "total", "monto", "subtotal")):
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                                cellStyle=_val_style, valueFormatter=_fmt_soles, minWidth=160)
        elif any(k in n for k in ("precio", "costo", "unitario", "promedio")):
            gb.configure_column(c, aggFunc="avg", type=["numericColumn"],
                                cellStyle=_mono, valueFormatter=_fmt_soles)
        elif any(k in n for k in ("cantidad", "qty", "unidades")):
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                                cellStyle=_mono, valueFormatter=_fmt_num)
        else:
            gb.configure_column(c, aggFunc="sum", type=["numericColumn"],
                                cellStyle=_mono, valueFormatter=_fmt_num)

    _candidatos_grp = [
        ("Proveedor", "Nombre Proveedor", "Razon Social"),
        ("Nombre Area", "Area", "Almacen"),
        ("Nombre Familia", "Familia"),
        ("Nombre Subfamilia", "Subfamilia"),
        ("Nombre Producto", "Producto", "Descripcion"),
        ("Unidad Medida", "Unidad Kardex", "Unidad"),
    ]
    _grupos_ini = []
    for cands in _candidatos_grp:
        _rc = buscar_columna(df_grid, *cands)
        if _rc and _rc in df_grid.columns and _rc not in _grupos_ini:
            gb.configure_column(_rc, rowGroup=True,
                                rowGroupIndex=len(_grupos_ini), hide=True)
            _grupos_ini.append(_rc)

    for cands, af in [
        (("Importe Total", "Total", "Monto", "Subtotal"), "sum"),
        (("Cantidad", "Qty", "Unidades"), "sum"),
        (("Precio Unitario", "Precio Promedio", "Precio"), "avg"),
    ]:
        _rc = buscar_columna(df_grid, *cands)
        if _rc and _rc in df_grid.columns:
            gb.configure_column(_rc, aggFunc=af, enableValue=True)

    for c in df_grid.columns:
        gb.configure_column(c, headerName=_titulo_es(c))

    get_row_style = JsCode(
        "function(params) {"
        "    if (params.node.rowPinned === 'bottom') {"
        "        return { fontWeight:'700',"
        "                 backgroundColor:'" + LAVANDA_CABECERA_GRUPO + "',"
        "                 color:'" + ACENTO_TEXTO_OSCURO + "',"
        "                 borderTop:'2px solid " + ACENTO + "',"
        "                 fontSize:'13px' };"
        "    }"
        "    if (params.node.group) {"
        "        var nivel = params.node.level;"
        "        if (nivel === 0) return { backgroundColor:'" + LAVANDA_BORDE + "', fontWeight:'600' };"
        "        if (nivel === 1) return { backgroundColor:'" + LAVANDA_CABECERA_GRUPO + "', fontWeight:'600' };"
        "        return { backgroundColor:'" + LAVANDA_FONDO + "', fontWeight:'500' };"
        "    }"
        "    return { backgroundColor:'" + BLANCO + "' };"
        "}"
    )

    _sidebar_cfg = _config_sidebar()

    gb.configure_grid_options(
        autoGroupColumnDef={"minWidth": 220},
        localeText=LOCALE_ES,
        sideBar=_sidebar_cfg,
        rowHeight=max(28, min(60, font_px + 12)),
        headerHeight=int(font_px * 2 + 14),
        cellSelection=True,
        tooltipShowDelay=300,
        getRowStyle=get_row_style,
        suppressAggFuncInHeader=True,
        onGridSizeChanged=JsCode(
            "function(params){ params.api.sizeColumnsToFit(); }"),
        onFirstDataRendered=JsCode(
            "function(params){ params.api.autoSizeAllColumns(); }"),
        onToolPanelVisibleChanged=JsCode(
            "function(params){"
            "    try{"
            "        var open=(params.api&&params.api.getOpenedToolPanel)"
            "            ?params.api.getOpenedToolPanel():null;"
            "        var sb=document.querySelector('.ag-side-bar');"
            "        if(sb)sb.setAttribute('data-active-panel',open||'');"
            "        window.clearTimeout(window.__comprasFitTimer);"
            "        window.__comprasFitTimer=window.setTimeout(function(){"
            "            try{params.api.sizeColumnsToFit();}catch(e){}"
            "        },150);"
            "    }catch(e){}"
            "}"
        ),
        pivotMode=True,
        groupDefaultExpanded=0,
    )
    gb.configure_pagination(
        enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    custom_css = _css_base(font_px)
    custom_css[".ag-row-even"] = {"background-color": BLANCO + " !important"}
    custom_css[".ag-row-odd"]  = {"background-color": BLANCO + " !important"}
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
        "background-color": BLANCO + " !important",
        "border": "1px solid " + GRIS_BORDE + " !important",
        "border-radius": "12px !important",
        "box-shadow": "0 1px 2px rgba(16,16,20,0.05),0 4px 14px rgba(16,16,20,0.07) !important",
        "overflow": "hidden !important",
    }
    custom_css["html, body"] = {"background": "transparent !important"}
    custom_css[".ag-header"].update({
        "background-color": LAVANDA_FONDO + " !important",
        "border-bottom": "1px solid " + ACENTO + " !important",
    })
    custom_css[".ag-header-cell"].update({
        "background-color": LAVANDA_FONDO + " !important",
    })
    custom_css[".ag-header-cell-text"].update({
        "color": ACENTO_TEXTO_OSCURO + " !important",
        "font-weight": "500",
        "white-space": "normal !important",
        "overflow": "visible !important",
        "text-overflow": "clip !important",
        "line-height": "1.25 !important",
        "overflow-wrap": "break-word",
        "display": "flex",
        "align-items": "center",
        "text-align": "center",
    })
    custom_css[".ag-header-cell-label"] = {
        "white-space": "normal !important",
        "overflow": "visible !important",
        "align-items": "center",
    }
    custom_css[".ag-row-pinned"].update({
        "background-color": LAVANDA_CABECERA_GRUPO + " !important",
        "border-top": "2px solid " + ACENTO + " !important",
        "color": ACENTO_TEXTO_OSCURO + " !important",
    })
    custom_css[".ag-side-bar"].update({
        "background-color": LAVANDA_FILA + " !important",
        "border": "1px solid " + GRIS_BORDE + " !important",
        "border-radius": "12px !important",
        "box-shadow": "0 1px 2px rgba(16,16,20,0.05),0 4px 14px rgba(16,16,20,0.07) !important",
        "margin": "0 0 0 14px !important",
        "overflow": "hidden !important",
    })
    custom_css[".ag-side-bar .ag-side-buttons"].update({
        "background-color": LAVANDA_FILA_ALT + " !important",
        "border-bottom": "1px solid " + GRIS_BORDE + " !important",
    })

    # Franjas lavanda del sidebar (superior + inferior), en las 3 pestañas.
    # Selectores con :not(.ag-hidden) para no des-ocultar los paneles
    # inactivos (bug de "paneles uno al costado del otro").
    custom_css.update(_css_franjas_sidebar())

    custom_css[
        ".ag-side-bar[data-active-panel='columns'],"
        ".ag-side-bar[data-active-panel='pivotePanel']"
    ] = {"--ag-list-item-height": "62px !important"}
    custom_css[
        ".ag-side-bar[data-active-panel='columns'] .ag-virtual-list-item,"
        ".ag-side-bar[data-active-panel='pivotePanel'] .ag-virtual-list-item"
    ] = {"height": "62px !important", "overflow": "visible !important"}
    custom_css[
        ".ag-side-bar[data-active-panel='columns'] .ag-virtual-list-container,"
        ".ag-side-bar[data-active-panel='pivotePanel'] .ag-virtual-list-container"
    ] = {"overflow": "visible !important"}

    perf.set_df_info(df_grid, label="AgGrid (Compras)")
    with perf.phase("AgGrid render"):
        AgGrid(
            df_grid, gridOptions=grid_options, height=600,
            theme="material", custom_css=custom_css,
            fit_columns_on_grid_load=True, allow_unsafe_jscode=True,
            enable_enterprise_modules=True, key="grid_Compras",
        )

    # ── CAMBIO 2: usa_pagination_v2=True en renderizar_aggrid_compras ─────
    inject_grid_health_check(usa_pagination_v2=True)
    inject_pagination_v2()
    inject_maximize_aggrid()
    inject_dynamic_grid_height(offset_px=260, min_px=320)
    inject_fix_column_panel_ajuste()
