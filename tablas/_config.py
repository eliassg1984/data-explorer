"""tablas._config - helpers de configuracion de la grilla.

Formato de celdas y filas, configuracion del sidebar, fila de totales al pie
y normalizacion de titulos en espanol.
"""

import re
import unicodedata

import pandas as pd
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
def _estilos_celda():
    """Estilos JsCode de celda del grid: (mono, stock, valorizado).

    Sin parámetros ni estado: son tres constantes JsCode. Hasta el
    2026-08-08 devolvía 5 estilos y recibía `max_valorizado`, porque
    existían las variantes "con fondo" (semáforo rojo/naranja según el
    valor del stock, barra de gradiente proporcional en el valorizado).
    El DISEÑO UNIFICADO las dejó sin usar — el llamador elegía siempre
    las planas — así que salieron junto con el parámetro que solo ellas
    necesitaban."""
    mono_style = JsCode("""
        function(params) {
            return { fontFamily: "'Courier New', Courier, monospace" };
        }
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
    return mono_style, stock_cell_style_plano, valorizado_plano
def _estilo_fila(col_stock, df_grid):
    """JsCode getRowStyle: fila de totales + niveles de grupo coloreados
    si el grid tiene columna de stock; si no, solo la fila de totales.

    La tercera rama (semáforo de fondo por valor de stock) se borró el
    2026-08-08: era inalcanzable por partida doble — su guarda pedía
    `not quitar_fondos`, que el llamador fijaba siempre a True, y aunque
    no lo hiciera, la primera rama ya capturaba la misma condición."""
    if col_stock and col_stock in df_grid.columns:
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
# Columnas numéricas que NO se suman en la fila de totales: son códigos o
# partes de fecha, sumarlas da un número sin sentido.
#
# La comparación es por PALABRA COMPLETA del nombre, no por "contiene": con
# substring, "Cantidad" matchea "id" y "Tamaño" matchea "ano", y se perdían
# totales legítimos.
_NO_SUMABLE = frozenset({
    "codigo", "cod", "id", "nro", "numero", "num",
    "ano", "anio", "mes", "dia",
})
_SEPARADOR_PALABRAS = re.compile(r"[^0-9A-Za-z]+")


def _no_sumable(col):
    """True si la columna es un identificador o una parte de fecha.

    Los acentos se quitan ANTES de partir en palabras: el separador es
    `[^0-9A-Za-z]+`, así que sobre el texto crudo "Año" se partiría en
    ("A", "o") y nunca matchearía "ano"."""
    texto = (unicodedata.normalize("NFKD", str(col))
             .encode("ascii", "ignore").decode())
    palabras = {p.lower() for p in _SEPARADOR_PALABRAS.split(texto) if p}
    return bool(palabras & _NO_SUMABLE)


def _fila_totales(df_grid, cols_valor, cols_precio, cols_stock, primera_col):
    """Calcula la fila de totales al pie: suma para valor/stock, promedio
    para precio, "▶ TOTAL" en la primera columna. Devuelve el dict.
    Extraído de renderizar_aggrid_desktop en la Fase 3.

    OJO — las tres listas que recibe se arman por PALABRA CLAVE del nombre
    (valorizado/total/…, precio/promedio/…, stock). Una columna numérica que
    no cae en ninguna se sumaba como None y dejaba el total en blanco: era el
    caso de "AJUSTE" en Ajuste de Inventario, justo la métrica del reporte.
    Por eso el default de una numérica es SUMAR, y la lista negra
    (_NO_SUMABLE) es la que decide qué no tiene sentido sumar."""
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
        elif pd.api.types.is_numeric_dtype(df_grid[c]) and not _no_sumable(c):
            fila_totales[c] = round(float(df_grid[c].sum()), 2)
        else:
            fila_totales[c] = None
    return fila_totales
