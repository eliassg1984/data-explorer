"""
Tablas AgGrid (vista desktop y móvil) con formato financiero, totales
al pie, panel lateral de columnas y barra de paginación.
También incluye la tabla de Compras basada en st.data_editor.
"""

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils import _norm, buscar_columna, buscar_columna_fecha, LOCALE_ES
from inyecciones import inject_grid_health_check, inject_pagination_v2, inject_maximize_aggrid, inject_dynamic_grid_height
from perf import perf
from tema import (
    ACENTO, ACENTO_FUERTE, ACENTO_TEXTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA_FONDO, ADVERTENCIA_TEXTO, BLANCO, CELDA_ALERTA_FONDO, CELDA_ALERTA_TEXTO, CELDA_NEG_FONDO, CELDA_POS_TEXTO, DANGER_TEXT, ERROR_FONDO, EXIT_HOVER, GRIS_BORDE, GRIS_FONDO, GRIS_FONDO_CABECERA, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE, ICON_MUTED, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FILA, LAVANDA_FILA_ALT, LAVANDA_FOCO, LAVANDA_FONDO, LAVANDA_MEDIO, LAVANDA_SELECCION, SCROLL_THUMB, TEXTO_PRINCIPAL,
)


# ===========================================================================
# FUNCIONES AUXILIARES
# ===========================================================================

# Palabras que en español van en minúscula dentro de un título
# (salvo si son la primera palabra).
_MINUS_TITULO = {"de", "del", "la", "el", "los", "las", "y", "o",
                 "al", "en", "a", "con", "por", "para", "un", "una"}

def _titulo_es(texto):
    """Convierte 'STOCK AL CIERRE' → 'Stock al Cierre' (modo Nombre Propio)."""
    palabras = str(texto).strip().lower().split()
    return " ".join(
        p if (i > 0 and p in _MINUS_TITULO) else p.capitalize()
        for i, p in enumerate(palabras)
    )


# ===========================================================================
# FUNCIÓN: AGGRID DESKTOP — con formato financiero y diseño mejorado
# ===========================================================================

# ── 1 ───────────────────────────────────────────────────────────────
def _css_grid(font_px):
    """CSS del propio grid: guías de tab, root-wrapper, cabecera, filas,
    celda, fila fijada, paginación y barra de estado."""
    return {
        ".ag-tab-guard-top, .ag-tab-guard-bottom": {
            "caret-color": "transparent !important",
            "outline": "none !important",
            "border": "none !important",
            "opacity": "0 !important",
        },
        ".ag-root-wrapper": {
            "background-color": f"{BLANCO}",
            "border": f"1px solid {GRIS_BORDE}",
            "border-radius": "12px !important",
            "overflow": "hidden !important",
            "box-shadow": "0 1px 3px rgba(16,16,20,0.05)",
            "width": "100% !important",
        },
        ".ag-header": {
            "background-color": f"{LAVANDA_FONDO} !important",
            "border-bottom": f"1px solid {ACENTO} !important",
        },
        ".ag-header-cell": {
            "background-color": f"{LAVANDA_FONDO} !important",
        },
        ".ag-header-cell-text": {
            "color": f"{ACENTO_TEXTO_OSCURO} !important",
            "font-weight": "500",
            "font-size": f"{font_px}px",
            "letter-spacing": "normal",
            "text-transform": "none",
        },
        ".ag-header-icon": {
            "color": f"{GRIS_TEXTO_SUAVE} !important",
        },
        ".ag-row": {
            "border-bottom": f"1px solid {GRIS_LINEA}",
            "color": f"{TEXTO_PRINCIPAL}",
        },
        ".ag-row-even": {"background-color": f"{BLANCO}"},
        ".ag-row-odd": {"background-color": f"{GRIS_FONDO}"},
        ".ag-row-hover": {"background-color": f"{LAVANDA_FONDO} !important"},
        ".ag-cell": {"color": f"{EXIT_HOVER}", "font-size": f"{font_px}px"},
        ".ag-row-pinned": {
            "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
            "font-weight": "700 !important",
            "border-top": f"2px solid {ACENTO} !important",
            "color": f"{ACENTO_TEXTO_OSCURO} !important",
            "font-size": f"{font_px + 1}px !important",
        },
        ".ag-paging-panel": {
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "space-between !important",
            "color": f"{ICON_MUTED}",
            "background-color": f"{GRIS_FONDO}",
            "border-top": f"1px solid {GRIS_BORDE}",
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
            "color": f"{ICON_MUTED} !important",
            "font-size": "12px !important",
            "margin-right": "6px !important",
        },
        ".ag-paging-panel .ag-paging-page-size select, "
        ".ag-paging-panel .ag-paging-page-size .ag-select": {
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "6px !important",
            "background": f"{BLANCO} !important",
            "color": f"{TEXTO_PRINCIPAL} !important",
            "font-size": "12px !important",
            "padding": "2px 6px !important",
        },
        ".ag-paging-button": {
            "width": "28px !important",
            "height": "28px !important",
            "border": f"1px solid {GRIS_BORDE} !important",
            "background": f"{BLANCO} !important",
            "border-radius": "6px !important",
            "color": f"{GRIS_TEXTO} !important",
            "font-size": "13px !important",
            "cursor": "pointer !important",
            "display": "flex !important",
            "align-items": "center !important",
            "justify-content": "center !important",
            "margin": "0 2px !important",
            "transition": "all 0.15s ease !important",
        },
        ".ag-paging-button:hover:not(.ag-disabled)": {
            "background": f"{LAVANDA_FONDO} !important",
            "border-color": f"{LAVANDA_FOCO} !important",
            "color": f"{ACENTO_FUERTE} !important",
        },
        ".ag-paging-button.ag-disabled": {
            "color": f"{SCROLL_THUMB} !important",
            "border-color": f"{GRIS_LINEA} !important",
            "background": f"{GRIS_FONDO} !important",
            "cursor": "default !important",
        },
        ".ag-paging-row-summary-panel": {
            "color": f"{ICON_MUTED} !important",
            "font-size": "12px !important",
            "margin-left": "auto !important",
        },
        ".ag-paging-row-summary-panel-number": {
            "color": f"{TEXTO_PRINCIPAL} !important",
            "font-weight": "600 !important",
        },
        ".ag-status-bar": {
            "background-color": f"{GRIS_FONDO} !important",
            "border-top": f"1px solid {GRIS_BORDE} !important",
            "color": f"{GRIS_TEXTO} !important",
            "padding": "4px 16px !important",
            "font-size": "12px !important",
            "min-height": "0 !important",
        },
        ".ag-status-name-value": {
            "color": f"{GRIS_TEXTO} !important",
            "font-size": "12px !important",
        },
        ".ag-status-name-value-value": {
            "color": f"{TEXTO_PRINCIPAL} !important",
            "font-weight": "600 !important",
        },
    }


# ── 2 ───────────────────────────────────────────────────────────────
def _css_sidebar_marco():
    """Armazón genérico del sidebar — igual sea cual sea la pestaña abierta."""
    return {
        ".ag-side-bar": {
            "background-color": f"{BLANCO}",
            "border-left": f"1px solid {GRIS_BORDE} !important",
            "border-top-right-radius": "10px !important",
            "border-bottom-right-radius": "10px !important",
            "border-bottom": f"1px solid {GRIS_BORDE} !important",
        },
        ".ag-side-bar .ag-side-buttons": {
            "border-right": f"1px solid {GRIS_BORDE} !important",
        },
        ".ag-side-button": {
            "background-color": f"{GRIS_FONDO} !important",
            "border": "none !important",
            "border-bottom": f"1px solid {GRIS_BORDE} !important",
            "color": f"{GRIS_TEXTO} !important",
        },
        ".ag-side-button:hover": {
            "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
            "color": f"{ACENTO_FUERTE} !important",
        },
        ".ag-side-button.ag-selected": {
            "background-color": f"{ACENTO_FUERTE} !important",
            "color": f"{BLANCO} !important",
            "box-shadow": f"inset 0 0 0 1px {ACENTO}",
        },
        ".ag-tool-panel-wrapper": {
            "background-color": f"{BLANCO} !important",
            "border": "none !important",
        },
    }


# ── 3 ───────────────────────────────────────────────────────────────
def _css_panel_columnas():
    """Pestaña Columnas: pastillas, interruptor toggle, cabecera y buscador."""
    return {
        # Reglas que estaban en la zona marco (Bloque C original)
        ".ag-column-select-panel": {
            "padding": "10px !important",
            "background-color": f"{BLANCO} !important",
        },
        ".ag-column-tool-panel .ag-column-panel": {
            "border": "none !important",
        },
        ".ag-column-tool-panel .ag-column-select-all": {
            "padding": "10px 0 !important",
            "border-bottom": f"1px solid {GRIS_BORDE} !important",
        },
        ".ag-column-panel .ag-header-cell-text": {
            "color": f"{TEXTO_PRINCIPAL} !important",
            "font-weight": "600 !important",
        },
        # Bloque D original (PANEL COLUMNS acotado)
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-list": {
            "padding": "4px 0 8px !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column": {
            "display": "flex !important",
            "align-items": "center !important",
            "background": f"{GRIS_FONDO} !important",
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "999px !important",
            "padding": "10px 14px !important",
            "height": "auto !important",
            "box-sizing": "border-box !important",
            "margin": "7px 10px !important",
            "transition": "background .15s ease, border-color .15s ease !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column:hover": {
            "background": f"{LAVANDA_FONDO} !important",
            "border-color": f"{LAVANDA_BORDE} !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column:has(.ag-checked)": {
            "background": f"{LAVANDA_FONDO} !important",
            "border-color": f"{LAVANDA_BORDE} !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column:has(.ag-checked) .ag-column-select-column-label": {
            "color": f"{ACENTO_TEXTO} !important",
            "font-weight": "500 !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column-label": {
            "order": "-1 !important",
            "margin-right": "auto !important",
            "color": f"{GRIS_TEXTO} !important",
            "font-size": "13px !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column .ag-drag-handle": {
            "display": "none !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column .ag-checkbox-input-wrapper": {
            "width": "36px !important",
            "height": "20px !important",
            "border-radius": "999px !important",
            "background": f"{GRIS_BORDE} !important",
            "border": "none !important",
            "box-shadow": "none !important",
            "position": "relative !important",
            "transition": "background .15s ease !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column .ag-checkbox-input-wrapper::after": {
            "content": "'' !important",
            "position": "absolute !important",
            "top": "2px !important",
            "left": "2px !important",
            "width": "16px !important",
            "height": "16px !important",
            "border-radius": "50% !important",
            "background": f"{BLANCO} !important",
            "color": "transparent !important",
            "box-shadow": "0 1px 2px rgba(0,0,0,0.25) !important",
            "transition": "left .15s ease !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column .ag-checkbox-input-wrapper.ag-checked": {
            "background": f"{ACENTO_FUERTE} !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column .ag-checkbox-input-wrapper.ag-checked::after": {
            "content": "'' !important",
            "left": "18px !important",
        },
        ".ag-side-bar[data-active-panel='columns'] .ag-column-select-column .ag-checkbox-input": {
            "cursor": "pointer !important",
        },
        # Bloque H original (tipografía y buscador)
        ".ag-column-select-header": {
            "padding": "10px 12px !important",
            "border-bottom": f"1px solid {GRIS_BORDE} !important",
        },
        ".ag-column-select-header-filter-wrapper .ag-input-field-input": {
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "8px !important",
            "font-size": "12.5px !important",
            "padding": "6px 10px !important",
        },
        ".ag-column-select-header-filter-wrapper .ag-input-field-input:focus": {
            "border-color": f"{LAVANDA_FOCO} !important",
            "box-shadow": f"0 0 0 2px {LAVANDA_FONDO} !important",
            "outline": "none !important",
        },
    }


# ── 4 ───────────────────────────────────────────────────────────────
def _css_panel_filtros():
    """Pestaña Filtros: pastillas colapsadas + interior expandido (buscador, lista, checkboxes)."""
    return {
        # Regla que estaba en la zona marco (Bloque C original)
        ".ag-filter-toolpanel-body": {
            "padding": "10px !important",
            "background-color": f"{BLANCO} !important",
        },
        # Bloque G original (Panel FILTROS)
        ".ag-filter-toolpanel": {
            "border": "none !important",
            "margin": "0 !important",
        },
        ".ag-filter-toolpanel-search": {
            "padding": "10px 12px !important",
            "border-bottom": f"1px solid {GRIS_BORDE} !important",
        },
        ".ag-filter-toolpanel-search .ag-input-field-input": {
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "8px !important",
            "font-size": "12.5px !important",
            "padding": "6px 10px !important",
            "color": f"{GRIS_TEXTO_MEDIO} !important",
        },
        ".ag-filter-toolpanel-search .ag-input-field-input:focus": {
            "border-color": f"{LAVANDA_FOCO} !important",
            "box-shadow": f"0 0 0 2px {LAVANDA_FONDO} !important",
            "outline": "none !important",
        },
        ".ag-filter-toolpanel-group-title-bar": {
            "background": f"{GRIS_FONDO} !important",
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "999px !important",
            "padding": "10px 14px !important",
            "margin": "7px 10px !important",
            "transition": "background .15s ease, border-color .15s ease !important",
        },
        ".ag-filter-toolpanel-group-title-bar:hover": {
            "background": f"{LAVANDA_FONDO} !important",
            "border-color": f"{LAVANDA_BORDE} !important",
        },
        ".ag-filter-toolpanel-group-title": {
            "color": f"{GRIS_TEXTO} !important",
            "font-size": "13px !important",
            "font-weight": "500 !important",
        },
        ".ag-filter-toolpanel-group-title-bar-icon .ag-icon, "
        ".ag-filter-toolpanel-group-title-bar .ag-icon": {
            "color": f"{GRIS_TEXTO_SUAVE} !important",
        },
        ".ag-filter-toolpanel-instance-header": {
            "background": "transparent !important",
            "border": "none !important",
            "padding": "6px 12px !important",
            "margin": "0 !important",
        },
        ".ag-filter-toolpanel-instance-header-text": {
            "color": f"{GRIS_TEXTO} !important",
            "font-size": "12.5px !important",
            "font-weight": "500 !important",
        },
        ".ag-filter-toolpanel-instance-body": {
            "background": f"{LAVANDA_SELECCION} !important",
            "border": f"1px solid {LAVANDA_BORDE} !important",
            "border-radius": "10px !important",
            "padding": "8px !important",
            "margin": "0 10px 6px !important",
            "--ag-checkbox-checked-color": f"{ACENTO_FUERTE} !important",
        },
        ".ag-filter-toolpanel-instance-body .ag-mini-filter": {
            "margin": "2px 0 6px !important",
        },
        ".ag-filter-toolpanel-instance-body .ag-mini-filter .ag-input-field-input": {
            "background": f"{BLANCO} !important",
            "border": f"1px solid {GRIS_BORDE} !important",
            "border-radius": "8px !important",
            "font-size": "12.5px !important",
            "padding": "6px 10px !important",
        },
        ".ag-filter-toolpanel-instance-body .ag-set-filter-list, "
        ".ag-filter-toolpanel-instance-body .ag-virtual-list-viewport": {
            "background": "transparent !important",
        },
        ".ag-filter-toolpanel-instance-body .ag-set-filter-item .ag-label": {
            "color": f"{GRIS_TEXTO_MEDIO} !important",
            "font-size": "12.5px !important",
        },
        ".ag-filter-toolpanel-instance-body .ag-checkbox-input-wrapper.ag-checked": {
            "color": f"{ACENTO_FUERTE} !important",
        },
    }


# ── 5 ───────────────────────────────────────────────────────────────
def _css_panel_pivote():
    """Pestaña Modo pivote: chips de Grupos de filas / Valores."""
    return {
        # Regla que oculta la lista de columnas en el panel de pivote
        ".ag-side-bar[data-active-panel='pivotePanel'] .ag-column-select": {
            "display": "none !important",
        },
        # Bloque F original (Pivote MODERNO PLANO)
        ".ag-column-drop-vertical-title-bar": {
            "padding": "14px 14px 8px !important",
        },
        ".ag-column-drop-vertical-title": {
            "color": f"{GRIS_TEXTO_SUAVE} !important",
            "font-size": "11px !important",
            "font-weight": "600 !important",
            "text-transform": "uppercase !important",
            "letter-spacing": "0.07em !important",
        },
        ".ag-column-drop-vertical": {
            "background": "transparent !important",
            "flex": "0 0 auto !important",
        },
        ".ag-column-drop-vertical + .ag-column-drop-vertical": {
            "border-top": f"1px solid {GRIS_LINEA} !important",
            "margin-top": "14px !important",
        },
        ".ag-column-drop-vertical-list": {
            "margin": "4px 14px 18px !important",
            "border": f"1.5px dashed {LAVANDA_BORDE} !important",
            "border-radius": "10px !important",
            "background": f"{LAVANDA_SELECCION} !important",
            "padding": "8px !important",
            "min-height": "52px !important",
        },
        ".ag-column-drop-empty-message": {
            "color": f"{LAVANDA_MEDIO} !important",
            "font-size": "12px !important",
            "text-align": "center !important",
        },
        ".ag-column-drop-vertical-cell": {
            "background": f"{LAVANDA_FONDO} !important",
            "border": f"1px solid {LAVANDA_BORDE} !important",
            "border-radius": "999px !important",
            "padding": "10px 14px !important",
            "margin": "7px 8px !important",
            "font-size": "13px !important",
            "color": f"{ACENTO_TEXTO} !important",
            "transition": "background .15s ease, border-color .15s ease !important",
        },
        ".ag-column-drop-vertical-cell:hover": {
            "background": f"{LAVANDA_SELECCION} !important",
        },
        ".ag-column-drop-vertical-cell .ag-icon": {
            "color": f"{LAVANDA_MEDIO} !important",
        },
        ".ag-column-drop-vertical-cell-text": {
            "font-size": "13px !important",
        },
        ".ag-column-drop-cell-button": {
            "color": f"{GRIS_TEXTO_SUAVE} !important",
        },
        ".ag-column-drop-cell-button:hover": {
            "color": f"{ACENTO_FUERTE} !important",
        },
    }


def _css_base(font_px):
    """CSS del grid AgGrid (dict custom_css), ensamblado por secciones.
    Cada sección vive en su propia función (ver arriba)."""
    css = {}
    css.update(_css_grid(font_px))
    css.update(_css_sidebar_marco())
    css.update(_css_panel_columnas())
    css.update(_css_panel_filtros())
    css.update(_css_panel_pivote())
    return css


# ── Resto de funciones auxiliares sin cambios ──────────────────────
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
                if (params.node.rowPinned === 'bottom') {{
                    return {{ fontWeight:'700', backgroundColor:'{LAVANDA_CABECERA_GRUPO}', color:'{ACENTO_TEXTO_OSCURO}',
                             borderTop:'2px solid {ACENTO}', fontSize:'13px' }};
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
                if (params.node.rowPinned === 'bottom') {{
                    return {{ fontWeight:'700', backgroundColor:'{LAVANDA_CABECERA_GRUPO}', color:'{ACENTO_TEXTO_OSCURO}',
                              borderTop:'2px solid {ACENTO}', fontSize:'13px' }};
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
                if (params.node.rowPinned === 'bottom') {{
                    return {{ fontWeight:'700', backgroundColor:'{LAVANDA_CABECERA_GRUPO}', color:'{ACENTO_TEXTO_OSCURO}',
                             borderTop:'2px solid {ACENTO}', fontSize:'13px' }};
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
    fila_totales = _fila_totales(df_grid, cols_valor, cols_precio, cols_stock, primera_col)

    get_row_style = _estilo_fila(col_stock, df_grid, es_inventario, quitar_fondos)
    _sidebar_cfg = _config_sidebar(mostrar_pivot, es_ajuste)

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

                    window.clearTimeout(window.__ajusteFitTimer);
                    window.__ajusteFitTimer = window.setTimeout(function() {
                        try { params.api.sizeColumnsToFit(); } catch(e) {}
                    }, 150);
                } catch(e) {}
            }
        """)

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

        for _c in df_grid.columns:
            gb.configure_column(_c, headerName=_titulo_es(_c))

        opciones_grid["pivotMode"] = True
        opciones_grid["groupDefaultExpanded"] = 0

    gb.configure_grid_options(**opciones_grid)
    if es_salidas:
        gb.configure_pagination(enabled=False)
    else:
        gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=50)
    grid_options = gb.build()

    custom_css = _css_base(font_px)

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
            "border-top": f"2px solid {ACENTO} !important",
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

        custom_css[
            ".ag-side-bar[data-active-panel='columns'], "
            ".ag-side-bar[data-active-panel='pivotePanel']"
        ] = {"--ag-list-item-height": "62px !important"}

        custom_css[
            ".ag-side-bar[data-active-panel='columns'] .ag-virtual-list-item, "
            ".ag-side-bar[data-active-panel='pivotePanel'] .ag-virtual-list-item"
        ] = {
            "height": "62px !important",
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
            "border-top": f"2px solid {GRIS_TEXTO} !important",
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
            height=(850 if es_requerimientos else 600),
            theme=tema_grid, custom_css=custom_css,
            fit_columns_on_grid_load=True, allow_unsafe_jscode=True,
            enable_enterprise_modules=True, key=f"grid_{reporte}",
        )

    inject_grid_health_check()

    if reporte in REPORTES_ESTILO_INVENTARIO:
        inject_pagination_v2()

    if es_requerimientos or es_ajuste:
        inject_maximize_aggrid()
        inject_dynamic_grid_height(offset_px=220)

    if es_ajuste:
        from inyecciones import inject_fix_column_panel_ajuste
        inject_fix_column_panel_ajuste()


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
        ".ag-root-wrapper": {"background-color": f"{BLANCO}", "border": f"1px solid {GRIS_BORDE}", "border-radius": "8px", "width": "100% !important"},
        ".ag-header": {"background-color": f"{GRIS_LINEA}", "border-bottom": f"2px solid {ACENTO}"},
        ".ag-header-cell-text": {"color": f"{TEXTO_PRINCIPAL}", "font-weight": "700", "font-size": f"{font_px}px"},
        ".ag-row": {"color": f"{EXIT_HOVER}", "border-color": f"{GRIS_BORDE}"},
        ".ag-row-even": {"background-color": f"{BLANCO}"},
        ".ag-row-odd": {"background-color": f"{GRIS_FONDO}"},
        ".ag-row-hover": {"background-color": f"{LAVANDA_FONDO} !important"},
        ".ag-cell": {"color": f"{EXIT_HOVER}", "font-size": f"{font_px}px"},
        ".ag-paging-panel": {"color": f"{ICON_MUTED}", "background-color": f"{GRIS_FONDO}", "border-top": f"1px solid {GRIS_BORDE}", "font-size": "0.75rem"},
        ".ag-menu": {"background-color": f"{BLANCO}", "color": f"{TEXTO_PRINCIPAL}", "border": f"1px solid {GRIS_BORDE}"},
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
            f"<div style='background:{LAVANDA_CABECERA_GRUPO};border-top:2px solid {ACENTO};"
            "border-radius:0 0 8px 8px;padding:6px 12px;"
            f"font-size:13px;font-weight:700;color:{ACENTO_TEXTO_OSCURO};'>"
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
