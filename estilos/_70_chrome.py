"""estilos._70_chrome - Chrome de Streamlit: toolbars nativas ocultas, posicion del toast y aviso flotante de refresco en curso.

Extraido de estilos.py (lineas 1302-1344 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* OCULTAR TOOLBARS NATIVAS DE STREAMLIT                                */
    /* =================================================================== */
    [data-testid="stToolbar"],
    [data-testid="stMainMenu"],
    [data-testid="stAppDeployButton"],
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    /* Botón "Manage app" de Streamlit Community Cloud (abajo a la derecha;
       en móvil tapa la barra de navegación inferior). Las clases van con
       hash y cambian entre versiones, por eso el selector por substring. */
    [data-testid="manage-app-button"],
    div[class*="viewerBadge"] {
        display: none !important;
    }
    [class*="st-key-grid_"] [data-testid="stElementToolbar"] {
        display: none !important;
    }

    /* =================================================================== */
    /* POSICIÓN DEL TOAST (st.toast) — abajo a la izquierda                 */
    /* 2026-08-18: 100px -> 16px. Los 100 eran el ancho del rail izquierdo  */
    /* (90) + 10 de aire, para que el toast no le cayera encima. El rail    */
    /* es hoy la franja superior, así que esa esquina quedó libre y el      */
    /* toast se pega al borde como cualquier otro.                          */
    /* =================================================================== */
    div[data-testid="stToastContainer"] {
        left: 16px !important;
        right: auto !important;
        bottom: 16px !important;
        top: auto !important;
    }

    /* =================================================================== */
    /* AVISO DE REFRESCO EN CURSO — flotante abajo a la izquierda           */
    /* Mismo `left` que el toast, por el mismo motivo (ver arriba).         */
    /* =================================================================== */
    .st-key-aviso_refresco {
        position: fixed !important;
        left: 16px !important;
        bottom: 16px !important;
        max-width: 320px !important;
        z-index: 999997 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
        border-radius: 8px !important;
    }
"""
