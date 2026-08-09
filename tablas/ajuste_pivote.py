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


def _ancho_header_periodo(label, minimo=92, base=85, por_caracter=7.5):
    """Ancho mínimo a partir del largo de la etiqueta. "ene"/"S01" entran
    en el mínimo de siempre, pero Corte trae etiquetas bien más largas
    ("15-16 ene", "30 jul - 2 ago") que un mínimo fijo pensado para 3
    caracteres no alcanzaba a mostrar completas -- se veían cortadas
    ("1...") aunque el dato entero cupiera en la celda de abajo.

    `base`/`por_caracter` NO son una estimación a ojo (la primera versión
    lo era -- 58 + 7px/car -- y con muchas columnas de Corte reales seguía
    cortando: 9/10 headers truncados, verificado con
    _test_pivote_aislado.py). Estos números salen de medir en vivo
    `scrollWidth` del label vs. el ancho real de columna en varias
    etiquetas: los tres iconos de cabecera (orden/filtro/menú) comen
    ~72px fijos sea cual sea el texto, no ~58px. base=85/por_caracter=7.5
    deja margen sobre esa medición (72px de chrome + ~6.3px/car de texto
    medidos) para no quedar otra vez al borde exacto."""
    return max(minimo, base + len(str(label)) * por_caracter)


def _col_periodo(col_id, headerName, field_ajv, field_aj, es_total=False,
                 minWidth=None, pinned=None):
    d = {
        "colId": col_id, "headerName": headerName,
        "headerTooltip": headerName,
        "type": ["numericColumn"],
        "minWidth": minWidth if minWidth is not None else _ancho_header_periodo(headerName),
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
                                     font_px: int = 13, anio=None):
    """`df_wide`: una fila por Familia+Subfamilia+Producto, más las
    columnas de `periodos` (lista de dicts field_ajv/field_aj/label, en
    orden cronológico) y tot_ajv/tot_aj. Arma el grid: filas agrupadas
    nativas + una columna sintética por periodo con celda compacta.

    `anio` (opcional): la vista siempre acota a UN año (ver
    graficos/ajuste.py::_tabla_pivote_fecha_ajuste), así que en vez de
    repetirlo en cada cabecera de periodo ("ene 2026", "feb 2026"...) va
    UNA sola vez como grupo de columna por encima de Día/Semana/Mes --
    Total queda afuera del grupo, es un cierre de fila, no parte del año."""
    gb = GridOptionsBuilder.from_dataframe(df_wide)
    gb.configure_default_column(
        resizable=True, sortable=True, filter=True, editable=False,
        enableRowGroup=False, enablePivot=False, enableValue=False,
        minWidth=90,
    )

    # Producto NO es rowGroup: si lo fuera, cada producto formaría su
    # propio grupo de un solo hijo (una fila más para expandir, sin
    # información nueva). Familia/Subfamilia agrupan; Producto queda
    # oculto como columna propia -- lo muestra autoGroupColumnDef.field
    # en la fila HOJA (ver más abajo), el árbol termina en el producto,
    # no un nivel después.
    _grupos = [c for c in (col_familia, col_subfamilia) if c]
    for i, c in enumerate(_grupos):
        gb.configure_column(c, rowGroup=True, rowGroupIndex=i, hide=True)
    gb.configure_column(col_producto, hide=True)

    _tiene_aj = any(p["field_aj"] for p in periodos)

    # Las columnas fuente (ajv_i/aj_i/tot_ajv/tot_aj) quedan ocultas: solo
    # alimentan el valueGetter de su columna sintética, no se muestran
    # directas ni participan del aggFunc nativo de AG Grid. `hide=True` las
    # saca de la GRILLA pero no de los paneles laterales -- Columnas Y
    # Filtros listan TODO colId con field, oculto o no, y como nunca
    # reciben header_name muestran su nombre crudo ("ajv_0", "aj_1"...).
    # Sin suppress*ToolPanel ambos paneles se llenan de pastillas sin
    # sentido para el usuario (ver arquitectura.md regla #57).
    _kw_oculta = {"hide": True, "suppressColumnsToolPanel": True,
                  "suppressFiltersToolPanel": True}
    for p in periodos:
        gb.configure_column(p["field_ajv"], **_kw_oculta)
        if p["field_aj"]:
            gb.configure_column(p["field_aj"], **_kw_oculta)
    gb.configure_column("tot_ajv", **_kw_oculta)
    if _tiene_aj:
        gb.configure_column("tot_aj", **_kw_oculta)

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
            # sin importar `field`. col_producto porque la hoja de este
            # árbol es el producto.
            "field": col_producto,
            "pinned": "left", "minWidth": 220,
            # SIN groupDisplayType="groupRows" (default = "singleColumn"):
            # las filas de grupo dejan de ser de ancho completo y cada
            # columna de periodo se renderiza también para ellas --
            # subtotal por Familia/Subfamilia en cada corte/semana/mes, no
            # solo el total de la fila. El innerRenderer va ACÁ (no en
            # groupRowRendererParams, que es lo que aplicaría en modo
            # "groupRows" -- ver arquitectura.md regla #25) porque ahora el
            # grupo se pinta con el cell renderer normal de esta columna,
            # no con un renderer de ancho completo aparte.
            # suppressCount: agGroupCellRenderer (el wrapper nativo que da
            # el ícono expandir/colapsar) agrega SU PROPIO "(n)" por
            # defecto -- sin esto queda duplicado con el "(n)" que ya
            # arma group_inner_renderer a mano ("ALIMENTOS (3) · S/ 215(3)").
            "cellRendererParams": {"innerRenderer": group_inner_renderer,
                                   "suppressCount": True},
        },
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
    _cols_periodo = [
        _col_periodo(f"periodo_{i}", p["label"], p["field_ajv"], p["field_aj"])
        for i, p in enumerate(periodos)
    ]
    if anio:
        # El año va UNA vez como grupo de columna (no repetido en cada
        # cabecera) -- Total queda afuera, no es parte del año, es el
        # cierre de la fila.
        grid_options["columnDefs"].append({
            "groupId": f"anio_{anio}", "headerName": str(anio),
            "children": _cols_periodo,
        })
    else:
        grid_options["columnDefs"].extend(_cols_periodo)
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
    # _css_grid ya estila .ag-header-cell (la fila de Día/Semana/Mes) en
    # lavanda -- acá no había fila de GRUPO hasta agregar `anio`, así que
    # nadie la había estilado todavía. Un tono más (LAVANDA_CABECERA_GRUPO,
    # el mismo que ya usan las filas de grupo del árbol) la distingue de
    # la fila de abajo sin desentonar.
    custom_css[".ag-header-group-cell"] = {
        "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
        "border-bottom": f"1px solid {LAVANDA_BORDE} !important",
    }
    custom_css[".ag-header-group-cell-label"] = {
        "color": f"{ACENTO_TEXTO_OSCURO} !important",
        "font-weight": "600",
        "justify-content": "center",
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
