"""tablas._css - generacion del CSS de AgGrid.

Una funcion por zona. _css_base() concatena las demas y es lo que consumen
los renderizadores.

Regla del proyecto (arquitectura.md #2): los estilos de los paneles del
sidebar van SIEMPRE acotados por panel (data-active-panel), porque Columnas
y Pivote comparten el componente interno y un selector desnudo afecta a los
dos.
"""

from tema import (
    ACENTO, ACENTO_FUERTE, ACENTO_TEXTO, ACENTO_TEXTO_OSCURO, BLANCO, EXIT_HOVER, GRIS_BORDE, GRIS_FONDO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE, ICON_MUTED, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, LAVANDA_FOCO, LAVANDA_FONDO, LAVANDA_MEDIO, LAVANDA_SELECCION, SCROLL_THUMB, TEXTO_PRINCIPAL,
)


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
        # `:not(.ag-hidden)` NO es decoracion: AG Grid deja el panel de
        # paginacion SIEMPRE en el DOM y lo tapa con la clase `ag-hidden`
        # cuando la tabla no pagina. El `display: flex !important` de aca
        # pisaba esa senial, asi que los grids sin paginacion mostraban una
        # barra de 44px con los numeros VACIOS ("to of ... Page of ...").
        # Reportado con captura el 2026-08-21 sobre Documentos SUNAT; le
        # pasaba igual al top de Inventario y al ranking de Volatilidad,
        # que comparten este mismo `_css_grid`. Las tablas que SI paginan
        # (tablas/compras.py, tablas/desktop.py) no llevan `ag-hidden`, asi
        # que siguen viendo la regla intacta.
        ".ag-paging-panel:not(.ag-hidden)": {
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
        # Modo pivote: sus listas (grupos de filas, valores, etiquetas) deben
        # poder deslizarse; sin esto la lista queda cortada sin scrollbar.
        ".ag-side-bar[data-active-panel='pivotePanel'] .ag-column-panel": {
            "overflow-y": "auto !important",
        },
        ".ag-column-drop-vertical": {
            "min-height": "0 !important",
            "flex": "1 1 auto !important",
        },
        ".ag-column-drop-vertical-list": {
            "overflow-y": "auto !important",
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
            "padding": "6px 14px !important",
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
def _css_franjas_sidebar():
    """Franjas lavanda del sidebar (arriba y abajo), a juego con la cabecera
    y la fila de totales de la tabla. Válidas para las 3 pestañas.

    CLAVE: AG Grid mantiene los 3 tool-panels montados y oculta los inactivos
    con la clase `.ag-hidden` (display:none). El selector de estas reglas debe
    llevar `:not(.ag-hidden)` para NO des-ocultar los paneles inactivos (que si
    no aparecerían los tres uno al costado del otro)."""
    return {
        # ── Franja SUPERIOR ──────────────────────────────────────────────
        # Modo pivote: su propio panel de toggle (ya lleva la banda nativa).
        ".ag-pivot-mode-panel": {
            "background-color": f"{LAVANDA_FONDO} !important",
            "border-bottom": f"1px solid {ACENTO} !important",
            "min-height": "36px !important",
            "padding": "0 12px !important",
            "display": "flex !important",
            "align-items": "center !important",
        },
        ".ag-pivot-mode-panel .ag-label": {
            "color": f"{ACENTO_TEXTO_OSCURO} !important",
            "font-size": "11px !important",
            "font-weight": "500 !important",
        },
        # Columnas y Filtros: banda ::before sintética (no tienen pivot-panel).
        # En Columnas se evita duplicar si por algún reporte SÍ mostrara el
        # toggle de pivote (:not(:has(.ag-pivot-mode-panel))).
        ".ag-side-bar[data-active-panel='columns'] .ag-tool-panel-wrapper"
        ":not(.ag-hidden):not(:has(.ag-pivot-mode-panel))::before,"
        ".ag-side-bar[data-active-panel='filters'] .ag-tool-panel-wrapper"
        ":not(.ag-hidden)::before": {
            "content": "'' !important",
            "display": "block !important",
            "height": "36px !important",
            "flex-shrink": "0 !important",
            "background-color": f"{LAVANDA_FONDO} !important",
            "border-bottom": f"1px solid {ACENTO} !important",
        },

        # ── Franja INFERIOR ──────────────────────────────────────────────
        # El wrapper del panel VISIBLE pasa a columna flex para poder anclar
        # la franja al fondo con margin-top:auto. `:not(.ag-hidden)` evita que
        # el display:flex reactive los paneles ocultos.
        ".ag-side-bar .ag-tool-panel-wrapper:not(.ag-hidden)": {
            "display": "flex !important",
            "flex-direction": "column !important",
            "height": "100% !important",
        },
        ".ag-side-bar .ag-tool-panel-wrapper:not(.ag-hidden)::after": {
            "content": "'' !important",
            "display": "block !important",
            "height": "34px !important",
            "flex-shrink": "0 !important",
            "margin-top": "auto !important",
            "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
            "border-top": f"2px solid {ACENTO} !important",
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
