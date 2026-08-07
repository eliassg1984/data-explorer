"""tablas.ajuste_pivote - grilla AgGrid de la tabla dinámica "Por fecha" de
Ajuste de Inventario (graficos/ajuste.py::_tabla_pivote_fecha_ajuste).

Árbol de filas nativo (rowGroup: Familia > Subfamilia > Producto) + una
columna por periodo con Ajuste Valorizado (grande) y Ajuste (chico, debajo)
combinados en la misma celda. El df ya llega pre-pivoteado en ancho desde
graficos/ajuste.py (una fila por Familia+Subfamilia+Producto, columnas
ajv_i/aj_i por periodo, ocultas) — por cada periodo se agrega una columna
SINTÉTICA (colId propio, sin field) cuyo `valueGetter` arma un objeto
{ajv, aj} por fila hoja y cuyo `aggFunc` propio (JS, no el "sum" nativo)
suma ambos números al agrupar. Un solo valor por celda (el objeto), un solo
cellRenderer lee las dos partes — sin cruzar a una columna hermana en
tiempo de render, que era el diseño original y se descartó recién: la API
para leer OTRA columna desde un cellRenderer cambió de nombre entre
versiones de AG Grid (`api.getValue` ya no existe en la que trae este
proyecto; ver arquitectura.md) y el valueGetter+aggFunc combinados no
dependen de esa API en absoluto.

No usa pivotMode ni el "Modo pivote" nativo: ese pivotearía UNA columna
elegida por el usuario, no dos números fijos por Python. El panel "Modo
pivote" queda AFUERA del sidebar a propósito — arrastrar algo ahí rompería
la relación fija entre columnas hoja y su período.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils import LOCALE_ES
from inyecciones import (
    inject_grid_health_check, inject_maximize_aggrid,
    inject_dynamic_grid_height, inject_fix_column_panel_ajuste,
)
from perf import perf
from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, BLANCO, CELDA_POS_TEXTO, DANGER_TEXT,
    GRIS_TEXTO, GRIS_TEXTO_SUAVE, ICON_MUTED, LAVANDA_BORDE,
    LAVANDA_CABECERA_GRUPO, LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from tablas._css import _css_base, _css_franjas_sidebar

_COL_TOTAL_ID = "periodo_total"


def _value_getter_periodo(field_ajv, field_aj):
    """Arma el objeto {ajv, aj} de UNA fila hoja a partir de sus dos
    columnas fuente (ocultas). Solo corre para filas hoja: params.data
    existe ahí y no en filas de grupo, que en cambio usan `aggFunc`."""
    aj_expr = f"params.data['{field_aj}']" if field_aj else "null"
    return JsCode(f"""
        function(params) {{
            if (!params.data) return null;
            return {{ ajv: params.data['{field_ajv}'], aj: {aj_expr} }};
        }}
    """)


def _agg_func_combinado():
    """Suma ajv/aj de todos los hijos (hoja o subgrupo) al agrupar.
    `params.values` trae un {ajv, aj} por hijo -- mismo objeto que
    devuelve el valueGetter, la agregación no necesita leer nada más."""
    return JsCode("""
        function(params) {
            var t = { ajv: 0, aj: 0 };
            (params.values || []).forEach(function(v) {
                if (v) {
                    t.ajv += Number(v.ajv) || 0;
                    t.aj += Number(v.aj) || 0;
                }
            });
            return t;
        }
    """)


def _comparator_combinado():
    """Ordena por ajv -- el valor de la celda es un objeto, así que el
    comparador default (string/</>) no serviría."""
    return JsCode("""
        function(a, b) {
            var av = a ? (Number(a.ajv) || 0) : 0;
            var bv = b ? (Number(b.ajv) || 0) : 0;
            return av - bv;
        }
    """)


def _filter_value_getter(field_ajv):
    """El filtro numérico de AG Grid necesita un número, no el objeto
    {ajv, aj} -- filtra por Ajuste Valorizado (la métrica visible)."""
    return JsCode(f"""
        function(params) {{
            return params.data ? params.data['{field_ajv}'] : null;
        }}
    """)


def _cell_renderer_combinado(es_total=False):
    """Celda compacta: Ajuste Valorizado arriba (grande), Ajuste debajo
    (chico, gris) si es distinto de cero. En la columna Total el número de
    arriba va siempre en acento (no por signo) -- se lee como cierre de
    fila, no como bueno/malo."""
    color_expr = (f"'{ACENTO_TEXTO_OSCURO}'" if es_total else
                  f"(ajv > 0 ? '{CELDA_POS_TEXTO}' : (ajv < 0 ? '{DANGER_TEXT}' : '{GRIS_TEXTO}'))")
    peso = "600" if es_total else "500"
    # Componente "vanilla" (init/getGui), NO una función simple que
    # devuelve string/Node: st_aggrid usa ag-grid-react, y ahí una función
    # de cellRenderer que devuelve un STRING no se trata como innerHTML
    # (se ve el HTML escapado, como texto) y devolver un HTMLElement
    # directo revienta con "Minified React error #31" (objeto no válido
    # como hijo de React). La interfaz Component (init construye
    # this.eGui, getGui lo devuelve) es la que ag-grid-react sabe montar
    # sin pasar por su propio árbol de React -- confirmado en vivo con
    # _test_pivote_aislado.py antes de aplicar esto en toda la tabla.
    return JsCode(f"""
        class CeldaPeriodoAjuste {{
            init(params) {{
                var v = params.value;
                var eWrap = document.createElement('div');
                if (v && v.ajv !== null && v.ajv !== undefined) {{
                    var ajv = Number(v.ajv) || 0;
                    var color = {color_expr};
                    var sign = ajv > 0 ? '+' : (ajv < 0 ? '\\u2212' : '');
                    var txt = sign + 'S/ ' + Math.abs(ajv).toLocaleString('es-PE', {{maximumFractionDigits: 0}});
                    var eMain = document.createElement('div');
                    eMain.style.color = color;
                    eMain.style.fontWeight = '{peso}';
                    eMain.style.fontVariantNumeric = 'tabular-nums';
                    eMain.textContent = txt;
                    eWrap.appendChild(eMain);
                    var aj = v.aj;
                    if (aj !== null && aj !== undefined && Number(aj) !== 0) {{
                        var an = Number(aj);
                        var asign = an > 0 ? '+' : '\\u2212';
                        var eSub = document.createElement('div');
                        eSub.style.color = '{GRIS_TEXTO_SUAVE}';
                        eSub.style.fontSize = '10px';
                        eSub.style.fontVariantNumeric = 'tabular-nums';
                        eSub.textContent = asign + Math.abs(an).toLocaleString('es-PE');
                        eWrap.appendChild(eSub);
                    }}
                }}
                this.eGui = eWrap;
            }}
            getGui() {{ return this.eGui; }}
            refresh(params) {{ return false; }}
        }}
    """)


def _col_periodo(col_id, headerName, field_ajv, field_aj, es_total=False,
                 minWidth=92, pinned=None):
    d = {
        "colId": col_id, "headerName": headerName,
        "type": ["numericColumn"], "minWidth": minWidth,
        "sortable": True, "resizable": True, "filter": "agNumberColumnFilter",
        "valueGetter": _value_getter_periodo(field_ajv, field_aj),
        "aggFunc": _agg_func_combinado(),
        "comparator": _comparator_combinado(),
        "filterValueGetter": _filter_value_getter(field_ajv),
        "cellRenderer": _cell_renderer_combinado(es_total=es_total),
    }
    if pinned:
        d["pinned"] = pinned
    return d


def renderizar_aggrid_pivote_ajuste(df_wide, periodos, col_familia,
                                     col_subfamilia, col_producto,
                                     font_px: int = 13):
    """`df_wide`: una fila por Familia+Subfamilia+Producto, más las
    columnas de `periodos` (lista de dicts field_ajv/field_aj/label, en
    orden cronológico) y tot_ajv/tot_aj. Arma el grid: filas agrupadas
    nativas + una columna sintética por periodo con celda compacta."""
    gb = GridOptionsBuilder.from_dataframe(df_wide)
    gb.configure_default_column(
        resizable=True, sortable=True, filter=True, editable=False,
        enableRowGroup=False, enablePivot=False, enableValue=False,
        minWidth=90,
    )

    # Producto NO es rowGroup: si lo fuera, cada producto formaría su
    # propio grupo de un solo hijo (una fila más para expandir, sin
    # información nueva). Familia/Subfamilia agrupan; Producto queda como
    # la columna que autoGroupColumnDef muestra en la fila HOJA (ver más
    # abajo) -- el árbol termina en el producto, no un nivel después.
    _grupos = [c for c in (col_familia, col_subfamilia) if c]
    for i, c in enumerate(_grupos):
        gb.configure_column(c, rowGroup=True, rowGroupIndex=i, hide=True)
    # Producto va como columna PROPIA (no vía autoGroupColumnDef.field):
    # con groupDisplayType="groupRows" las filas de GRUPO son de ancho
    # completo (no pintan columnas individuales) y las filas HOJA no
    # terminaron mostrando el auto-group column en absoluto -- verificado
    # en vivo con _test_pivote_aislado.py (quedaba en blanco). Una columna
    # normal pinneada a la izquierda sí se ve en toda fila hoja.
    gb.configure_column(col_producto, hide=False, pinned="left",
                        headerName="Producto", minWidth=180)

    _tiene_aj = any(p["field_aj"] for p in periodos)

    # Las columnas fuente (ajv_i/aj_i/tot_ajv/tot_aj) quedan ocultas: solo
    # alimentan el valueGetter de su columna sintética, no se muestran
    # directas ni participan del aggFunc nativo de AG Grid.
    for p in periodos:
        gb.configure_column(p["field_ajv"], hide=True)
        if p["field_aj"]:
            gb.configure_column(p["field_aj"], hide=True)
    gb.configure_column("tot_ajv", hide=True)
    if _tiene_aj:
        gb.configure_column("tot_aj", hide=True)

    # Devuelve un elemento DOM (ver nota en _cell_renderer_combinado sobre
    # por qué hace falta el componente init/getGui en vez de una función
    # que devuelve string o Node.
    group_inner_renderer = JsCode(f"""
        class NombreGrupoAjuste {{
            init(params) {{
                if (!params.node || !params.node.group) {{
                    this.eGui = document.createElement('span');
                    this.eGui.textContent = params.value == null ? '' : params.value;
                    return;
                }}
                var nombre = (params.value == null ? '' : params.value);
                var n = params.node.allChildrenCount;
                var extra = '';
                var tot = params.node.aggData ? params.node.aggData['{_COL_TOTAL_ID}'] : null;
                if (tot && tot.ajv != null) {{
                    var v = Number(tot.ajv);
                    if (!isNaN(v)) {{
                        extra = ' \\u00b7 S/ ' + v.toLocaleString('es-PE', {{maximumFractionDigits: 0}});
                    }}
                }}
                var eWrap = document.createElement('span');
                var eName = document.createElement('span');
                eName.style.fontWeight = '600';
                eName.style.color = '{TEXTO_PRINCIPAL}';
                eName.textContent = nombre;
                var eMeta = document.createElement('span');
                eMeta.style.color = '{ICON_MUTED}';
                eMeta.style.fontWeight = '400';
                eMeta.textContent = ' (' + n + ')' + extra;
                eWrap.appendChild(eName);
                eWrap.appendChild(eMeta);
                this.eGui = eWrap;
            }}
            getGui() {{ return this.eGui; }}
            refresh(params) {{ return false; }}
        }}
    """)

    get_row_style = JsCode(f"""
        function(params) {{
            if (params.node.rowPinned) {{
                return {{ fontWeight:'700', backgroundColor:'{LAVANDA_CABECERA_GRUPO}',
                         color:'{ACENTO_TEXTO_OSCURO}', borderTop:'2px solid {ACENTO}',
                         fontSize:'13px' }};
            }}
            if (params.node.group) {{
                var nivel = params.node.level;
                if (nivel === 0) return {{ backgroundColor:'{LAVANDA_BORDE}', fontWeight:'600' }};
                if (nivel === 1) return {{ backgroundColor:'{LAVANDA_CABECERA_GRUPO}', fontWeight:'600' }};
                return {{ backgroundColor:'{LAVANDA_FONDO}', fontWeight:'500' }};
            }}
            return {{ backgroundColor:'{BLANCO}' }};
        }}
    """)

    # Fila de totales calculada en Python (mismo espíritu que
    # tablas/_config.py::_fila_totales) en vez de "grandTotalRow" nativo:
    # ese modo solo está probado en este repo junto a pivotMode=True
    # (Requerimientos, tablas/desktop.py), y acá pivotMode queda apagado.
    # pinnedBottomRowData es el mecanismo ya usado en el resto de la app
    # para fijar una fila de cierre sin pelear con el árbol de grupos. El
    # dict lleva las columnas FUENTE (ajv_i/aj_i/tot_ajv/tot_aj): el
    # valueGetter de cada columna sintética las lee igual que en una fila
    # hoja normal (una fila pinneada también tiene `params.data`).
    # "TOTAL GENERAL" va en el campo de col_producto porque las filas
    # pinneadas no participan del rowGroup: se muestran vía
    # autoGroupColumnDef.field (el mismo que usan las filas hoja), no vía
    # la clave de grupo de Familia/Subfamilia.
    fila_total = {col_producto: "TOTAL GENERAL"}
    for p in periodos:
        fila_total[p["field_ajv"]] = round(float(df_wide[p["field_ajv"]].sum()), 2)
        if p["field_aj"]:
            fila_total[p["field_aj"]] = round(float(df_wide[p["field_aj"]].sum()), 2)
    fila_total["tot_ajv"] = round(float(df_wide["tot_ajv"].sum()), 2)
    if _tiene_aj:
        fila_total["tot_aj"] = round(float(df_wide["tot_aj"].sum()), 2)

    _sidebar_cfg = {
        "toolPanels": [
            {
                "id": "columns", "labelDefault": "Columnas",
                "labelKey": "columns", "iconKey": "columns",
                "toolPanel": "agColumnsToolPanel",
                "toolPanelParams": {
                    "suppressRowGroups": True, "suppressValues": True,
                    "suppressPivots": True, "suppressPivotMode": True,
                    "suppressColumnExpandAll": True,
                },
            },
            {
                "id": "filters", "labelDefault": "Filtros",
                "labelKey": "filters", "iconKey": "filter",
                "toolPanel": "agFiltersToolPanel",
            },
        ],
        "defaultToolPanel": "",
        "position": "right",
    }

    gb.configure_grid_options(
        autoGroupColumnDef={
            "headerName": "Familia / Subfamilia / Producto",
            # `field` decide qué se ve en filas HOJA (y filas pinneadas) --
            # las de GRUPO (Familia/Subfamilia) muestran su propia clave
            # sin importar `field`, vía groupRowRendererParams de arriba.
            # col_producto porque la hoja de este árbol es el producto.
            "field": col_producto,
            "pinned": "left", "minWidth": 220,
        },
        # groupDisplayType="groupRows" pinta la fila de grupo con un
        # renderer de ancho completo aparte (agGroupRowRenderer) -- el
        # innerRenderer va acá, NO en autoGroupColumnDef.cellRendererParams
        # (eso solo aplicaría con groupDisplayType="singleColumn"). Mismo
        # mecanismo que tablas/desktop.py::opciones_grid["groupRowRendererParams"].
        groupRowRendererParams={"innerRenderer": group_inner_renderer},
        groupDisplayType="groupRows",
        groupDefaultExpanded=0,
        localeText=LOCALE_ES,
        sideBar=_sidebar_cfg,
        rowHeight=max(30, font_px + 18),
        headerHeight=int(font_px * 2 + 10),
        getRowStyle=get_row_style,
        suppressAggFuncInHeader=True,
        pivotMode=False,
        pinnedBottomRowData=[fila_total],
        # window.__agApiPivoteAjuste: mismo espíritu que window.__agApi de
        # tablas/desktop.py (arquitectura.md regla #33) -- deja inspeccionar
        # el estado real del grid (nodos, expand/collapse, aggData) desde la
        # consola sin adivinar por el DOM.
        onGridReady=JsCode(
            "function(params){ window.__agApiPivoteAjuste = params.api; }"),
        onGridSizeChanged=JsCode(
            "function(params){ params.api.sizeColumnsToFit(); }"),
        onToolPanelVisibleChanged=JsCode("""
            function(params) {
                try {
                    var open = (params.api && params.api.getOpenedToolPanel)
                        ? params.api.getOpenedToolPanel() : null;
                    var sb = document.querySelector('.ag-side-bar');
                    if (sb) sb.setAttribute('data-active-panel', open || '');
                } catch(e) {}
            }
        """),
    )
    grid_options = gb.build()

    # Columnas sintéticas (sin field propio): se agregan directo al dict ya
    # construido porque GridOptionsBuilder.configure_column exige que la
    # columna ya exista como field del dataframe (ver arquitectura.md
    # regla #26) -- estas no tienen field, viven de valueGetter + aggFunc.
    for i, p in enumerate(periodos):
        grid_options["columnDefs"].append(_col_periodo(
            f"periodo_{i}", p["label"], p["field_ajv"], p["field_aj"],
        ))
    grid_options["columnDefs"].append(_col_periodo(
        _COL_TOTAL_ID, "Total", "tot_ajv", "tot_aj" if _tiene_aj else None,
        es_total=True, minWidth=110, pinned="right",
    ))

    custom_css = _css_base(font_px)
    custom_css.update(_css_franjas_sidebar())
    custom_css[".ag-row-pinned"] = {
        "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
        "border-top": f"2px solid {ACENTO} !important",
        "color": f"{ACENTO_TEXTO_OSCURO} !important",
    }

    perf.set_df_info(df_wide, label="AgGrid (Ajuste pivote fecha)")
    with perf.phase("AgGrid render"):
        AgGrid(
            df_wide, gridOptions=grid_options, height=520,
            theme="material", custom_css=custom_css,
            fit_columns_on_grid_load=True, allow_unsafe_jscode=True,
            enable_enterprise_modules=True, key="grid_ajuste_pivote_fecha",
        )

    inject_grid_health_check(usa_pagination_v2=False)
    inject_maximize_aggrid()
    inject_dynamic_grid_height(offset_px=260, min_px=320)
    inject_fix_column_panel_ajuste()
