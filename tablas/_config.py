"""tablas._config - helpers de configuracion de la grilla.

Formato de celdas y filas, configuracion del sidebar, fila de totales al pie
y normalizacion de titulos en espanol.
"""

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from tema import (
    ACENTO, ACENTO_FUERTE, ACENTO_TEXTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA_FONDO, ADVERTENCIA_TEXTO, BLANCO, CELDA_ALERTA_FONDO, CELDA_ALERTA_TEXTO, CELDA_NEG_FONDO, CELDA_POS_TEXTO, DANGER_TEXT, ERROR_FONDO, EXIT_HOVER, GRIS_BORDE, GRIS_FONDO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE, ICON_MUTED, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FILA, LAVANDA_FILA_ALT, LAVANDA_FOCO, LAVANDA_FONDO, LAVANDA_MEDIO, LAVANDA_SELECCION, SCROLL_THUMB, TEXTO_PRINCIPAL,
)


_MINUS_TITULO = {"de", "del", "la", "el", "los", "las", "y", "o",
                 "al", "en", "a", "con", "por", "para", "un", "una"}
def _titulo_es(texto):
    """Convierte 'STOCK AL CIERRE' → 'Stock al Cierre' (modo Nombre Propio)."""
    palabras = str(texto).strip().lower().split()
    return " ".join(
        p if (i > 0 and p in _MINUS_TITULO) else p.capitalize()
        for i, p in enumerate(palabras)
    )
def _estilos_celda(max_valorizado):
    # ... (código sin modificar)
    """Estilos JsCode de celda del grid (mono, stock, valorizado y sus
    variantes planas). Solo dependen de max_valorizado. Extraído de
    renderizar_aggrid_desktop en la Fase 3."""
    mono_style = JsCode("""
        function(params) {
            return { fontFamily: "'Courier New', Courier, monospace" };
        }
    """)

    stock_cell_style = JsCode(f"""
        function(params) {{
            if (params.value === null || params.value === undefined) return {{}};
            if (params.node && params.node.rowPinned) {{
                return {{ fontWeight: '700', color: '{ACENTO_TEXTO_OSCURO}' }};
            }}
            var v = Number(params.value);
            var base = {{
                fontFamily: "'Courier New', Courier, monospace",
                fontWeight: '700',
                textAlign: 'right',
                padding: '2px 10px'
            }};
            if (v < 0) {{
                return Object.assign({{}}, base, {{
                    backgroundColor: '{ERROR_FONDO}',
                    color: '{DANGER_TEXT}',
                    borderRadius: '20px'
                }});
            }}
            if (v === 0) {{
                return Object.assign({{}}, base, {{
                    backgroundColor: '{ADVERTENCIA_FONDO}',
                    color: '{ADVERTENCIA_TEXTO}',
                    borderRadius: '20px'
                }});
            }}
            if (v < 10) {{
                return Object.assign({{}}, base, {{
                    backgroundColor: '{CELDA_ALERTA_FONDO}',
                    color: '{CELDA_ALERTA_TEXTO}',
                    borderRadius: '20px'
                }});
            }}
            return Object.assign({{}}, base, {{ color: '{CELDA_POS_TEXTO}' }});
        }}
    """)

    stock_cell_style_plano = JsCode(f"""
        function(params) {{
            if (params.value === null || params.value === undefined) return {{}};
            if (params.node && params.node.rowPinned) {{
                return {{ fontWeight: '700', color: '{ACENTO_TEXTO_OSCURO}' }};
            }}
            return {{
                fontFamily: "'Courier New', Courier, monospace",
                fontWeight: '700',
                textAlign: 'right',
                padding: '2px 10px',
                color: '{TEXTO_PRINCIPAL}'
            }};
        }}
    """)

    valorizado_bar_style = JsCode(f"""
        function(params) {{
            var base = {{
                fontFamily: "'Courier New', Courier, monospace",
                color: '{ACENTO_TEXTO_OSCURO}',
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
                backgroundImage: 'linear-gradient(to right, {LAVANDA_BORDE} 0%, {LAVANDA_BORDE} ' + pct + '%, transparent ' + pct + '%, transparent 100%)',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '100% 80%',
                backgroundPosition: 'left center'
            }});
        }}
    """)

    valorizado_plano = JsCode(f"""
        function(params) {{
            var base = {{
                fontFamily: "'Courier New', Courier, monospace",
                color: '{ACENTO_TEXTO_OSCURO}',
                fontWeight: '600',
                textAlign: 'right',
                paddingRight: '12px'
            }};
            if (params.node && (params.node.group || params.node.rowPinned)) {{
                return Object.assign({{}}, base, {{ fontWeight: '800' }});
            }}
            return base;
        }}
    """)
    return (mono_style, stock_cell_style, stock_cell_style_plano,
            valorizado_bar_style, valorizado_plano)
def _estilo_fila(col_stock, df_grid, es_inventario, quitar_fondos):
    """Devuelve el JsCode getRowStyle según el reporte: inventario (grupos
    coloreados), stock con semáforo, o fila total simple. Extraído de
    renderizar_aggrid_desktop en la Fase 3."""
    if col_stock and col_stock in df_grid.columns and es_inventario:
        get_row_style = JsCode(f"""
            function(params) {{
                if (params.node.rowPinned) {{
                    return {{ fontWeight:'700', backgroundColor:'{LAVANDA_CABECERA_GRUPO}', color:'{ACENTO_TEXTO_OSCURO}',
                             borderBottom:'2px solid {ACENTO}', fontSize:'13px' }};
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
    elif col_stock and col_stock in df_grid.columns and not quitar_fondos:
        _sf = str(col_stock).replace("\\", "\\\\").replace('"', '\\"')
        get_row_style = JsCode(f"""
            function(params) {{
                if (params.node.rowPinned) {{
                    return {{ fontWeight:'700', backgroundColor:'{LAVANDA_CABECERA_GRUPO}', color:'{ACENTO_TEXTO_OSCURO}',
                              borderBottom:'2px solid {ACENTO}', fontSize:'13px' }};
                }}
                if (params.node.group || !params.data) return null;
                var s = params.data["{_sf}"];
                if (s === null || s === undefined || s === '') return null;
                var v = Number(s);
                if (isNaN(v)) return null;
                if (v === 0) return {{ backgroundColor:'{CELDA_NEG_FONDO}' }};
                if (v < 10)  return {{ backgroundColor:'{ADVERTENCIA_FONDO}' }};
                return null;
            }}
        """)
    else:
        get_row_style = JsCode(f"""
            function(params) {{
                if (params.node.rowPinned) {{
                    return {{ fontWeight:'700', backgroundColor:'{LAVANDA_CABECERA_GRUPO}', color:'{ACENTO_TEXTO_OSCURO}',
                             borderBottom:'2px solid {ACENTO}', fontSize:'13px' }};
                }}
            }}
        """)
    return get_row_style
def _config_sidebar(mostrar_pivot, es_ajuste):
    """Arma la configuración del sidebar de AgGrid: paneles Columnas,
    Filtros y (solo en Ajuste) Modo pivote. Devuelve el dict sideBar.
    Extraído de renderizar_aggrid_desktop en la Fase 3."""
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

    if True:
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
    return _sidebar_cfg
def _fila_totales(df_grid, cols_valor, cols_precio, cols_stock, primera_col):
    """Calcula la fila de totales al pie: suma para valor/stock, promedio
    para precio, "▶ TOTAL" en la primera columna. Devuelve el dict.
    Extraído de renderizar_aggrid_desktop en la Fase 3."""
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
    return fila_totales
