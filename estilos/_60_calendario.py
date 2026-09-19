"""estilos._60_calendario - Calendario desplegable de BaseWeb y sus botones de atajo.

Extraido de estilos.py (lineas 1281-1301 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* CALENDARIO DESPLEGABLE (BaseWeb) — marco suave, sin presets          */
    /* =================================================================== */
    div[data-baseweb="calendar"] {
        border-radius: 12px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10) !important;
        font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    div[data-baseweb="calendar"] [role="gridcell"] > div {
        border-radius: 8px !important;
    }
    div[data-baseweb="calendar"] button svg {
        fill: var(--accent) !important;
    }
    /* Sin `:has()` desde el 2026-09-18. Antes se subía al popover que
       CONTIENE un calendario y se bajaba de nuevo; un atributo adentro de un
       `:has()` hace que cada elemento que un rerun inserta recalcule los
       estilos de la página entera (regla #469). No hace falta subir: BaseWeb
       dibuja los presets (`renderQuickSelect`, el único `select` de ese
       popover) ADENTRO de la raíz `data-baseweb="calendar"` — leído en el
       bundle de Streamlit, no supuesto. */
    div[data-baseweb="calendar"] [data-baseweb="select"] {
        display: none !important;
    }
    div[data-baseweb="popover"] div[data-baseweb="calendar"] + div {
        display: none !important;
    }
"""
