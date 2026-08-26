"""tablas._config - helpers de configuracion de la grilla.

Formato de celdas y filas, configuracion del sidebar, fila de totales al pie
y normalizacion de titulos en espanol.
"""

import re
import unicodedata

import pandas as pd
from st_aggrid import JsCode
from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, BLANCO, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FONDO, TEXTO_PRINCIPAL,
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
def _config_sidebar():
    """Config del sidebar de AgGrid: 3 paneles a la derecha, ninguno abierto.

      · Columnas    solo mostrar/ocultar (arrastrar a grupos/valores/pivote
                    se hace desde el panel "Modo pivote", no desde aquí)
      · Filtros     el panel de filtros nativo
      · Modo pivote grupos de filas, valores y etiquetas de columna

    Sin parámetros: hasta el 2026-08-08 recibía `mostrar_pivot` y
    `es_ajuste`, pero los DOS llamadores (desktop.py y compras.py) pasaban
    siempre True, así que cada expresión booleana de abajo tenía un único
    resultado posible y el panel de pivote colgaba de un `if True:`. Se
    dejaron los valores resueltos, que es lo que realmente se rendería.
    Si vuelve a hacer falta un sidebar distinto por reporte, parametrizar
    de nuevo desde el llamador — pero con un condicional que sí varíe."""
    return {
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
                    "suppressColumnFilter": True,
                    "suppressColumnSelectAll": True,
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
            {
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
            },
        ],
        "defaultToolPanel": "",   # ninguno abierto al cargar
        "position": "right",
    }
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


# ============================================================================
# Parche de iconos para navegadores viejos (arquitectura.md regla #159)
# ============================================================================
# AG Grid 34 (la Theming API) dibuja TODOS sus iconos igual: un cuadrado de
# `background-color: currentcolor` del tamaño del icono, recortado con
# `mask-image: url("data:image/svg+xml,...")`. No emite la variante
# `-webkit-mask-image` -- en el bundle de st_aggrid hay 192 `mask-image` y
# CERO `-webkit-mask-image` (sí está `-webkit-mask-size`, que solo no sirve).
#
# Chrome y Edge entienden `mask-image` sin prefijo recién desde la 120
# (diciembre 2023). En una versión anterior el navegador DESCARTA esa
# declaración, el recorte nunca se aplica y queda el cuadrado entero pintado:
# el usuario ve un RECTÁNGULO NEGRO en cada chevron de grupo, en cada icono de
# cabecera y en cada botón del sidebar. Windows 7/8.1 se quedaron en Chrome
# 109, así que "que actualicen el navegador" no siempre es una opción.
#
# El parche no trae los SVG de vuelta: copia las reglas que el propio tema ya
# puso en su <style> y las reemite con el prefijo. Por eso no envejece si
# st_aggrid sube de versión. En un navegador moderno no hace absolutamente
# nada: `CSS.supports` corta en la primera línea.
_JS_ICONOS_MASK = r"""
function(params) {
    try {
        if (window.CSS && CSS.supports && CSS.supports('mask-image','none')) return;
        var d = document;
        if (d.getElementById('ag-parche-mask')) return;
        var css = '';
        var hojas = d.querySelectorAll('style');
        for (var i = 0; i < hojas.length; i++) {
            var t = hojas[i].textContent || '';
            if (t.indexOf('.ag-icon-') < 0 || t.indexOf('mask-image') < 0) continue;
            var reglas = t.match(/[^{}]+\{[^{}]*mask-image[^{}]*\}/g) || [];
            for (var j = 0; j < reglas.length; j++) {
                css += reglas[j].replace(/([{;])\s*mask-image\s*:/g, '$1-webkit-mask-image:');
            }
        }
        if (!css) return;
        var e = d.createElement('style');
        e.id = 'ag-parche-mask';
        e.textContent = css;
        d.head.appendChild(e);
    } catch (err) {}
}
"""

# No hay un hook fijo porque cada renderizador ya usa los suyos: desktop.py
# ocupa onGridReady Y onFirstDataRendered, compras.py solo el segundo y
# ajuste_pivote.py solo el primero. Los tres disparan después de que el tema
# inyectó su <style>, que es lo único que el parche necesita.
_HOOKS_PARCHE = ("onGridReady", "onFirstDataRendered", "onModelUpdated")


_MARCA_JSCODE = "::JSCODE::"


def _codigo_de(js):
    """El JS crudo de un `JsCode`, sin los centinelas de `st_aggrid`.

    `JsCode("function(p){}")` guarda `"::JSCODE::function(p){}::JSCODE::"`:
    los centinelas le avisan al front cuáles strings del JSON hay que
    evaluar. Para COMPONER dos handlers hace falta el código pelado."""
    bruto = getattr(js, "js_code", js)
    if isinstance(bruto, str) and bruto.startswith(_MARCA_JSCODE):
        return bruto[len(_MARCA_JSCODE):-len(_MARCA_JSCODE)]
    return str(bruto)


def _parchar_iconos(grid_options):
    """Engancha el parche de iconos a la grilla, sí o sí.

    Se llama con el dict YA construido (`gb.build()`), no antes: así ve los
    handlers que el renderizador realmente declaró.

    Primero busca un hook LIBRE, que es el camino barato. Si no queda
    ninguno, ENVUELVE el primero en vez de reventar — que es lo que hacía
    hasta el 2026-08-26, con un `RuntimeError` que llegó a producción:
    `tablas/desktop.py` (el renderizador genérico, el que usan los reportes
    sin tabla propia) declara los TRES hooks de `_HOOKS_PARCHE`, así que su
    tabla tiraba traceback en vez de dibujarse. El comentario de arriba
    todavía decía "desktop.py ocupa onGridReady Y onFirstDataRendered": el
    tercero se sumó después y nadie volvió acá.

    Envolver es además más robusto que seguir agregando eventos a la lista:
    no depende de que quede alguno sin usar. Cada mitad va en su propio
    `try` para que un handler que falle no se lleve puesto al otro."""
    for hook in _HOOKS_PARCHE:
        if hook not in grid_options:
            grid_options[hook] = JsCode(_JS_ICONOS_MASK)
            return grid_options

    hook = _HOOKS_PARCHE[0]
    grid_options[hook] = JsCode(
        "function(params) {\n"
        f"  try {{ ({_codigo_de(grid_options[hook])})(params); }} catch (e) {{}}\n"
        f"  try {{ ({_JS_ICONOS_MASK})(params); }} catch (e) {{}}\n"
        "}"
    )
    return grid_options
