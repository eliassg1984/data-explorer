"""estilos._90_franja_inferior - Franja inferior fija que cierra el area de contenido, mas el texto de 'Ultima actualizacion' anclado a ella.

Extraido de estilos.py (lineas 1499-1553 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* FRANJA INFERIOR FIJA — cierra visualmente el área de contenido       */
    /* =================================================================== */
    .stApp::after {
        content: "" !important;
        position: fixed !important;
        left: 90px !important; /* coincide con el ancho del rail */
        right: 0 !important;
        bottom: 0 !important;
        height: 42px !important;
        background: #ffffff !important;
        border-top: 1px solid var(--border) !important;
        box-shadow: 0 -2px 4px rgba(16, 16, 20, 0.04) !important;
        pointer-events: none !important;
        z-index: 999990 !important;
    }
    [data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    .block-container {
        padding-bottom: 66px !important;
    }

    /* Texto "Última actualización" anclado a la franja inferior fija */
    .st-key-footer_actualizacion {
        position: fixed !important;
        left: 90px !important;
        right: 0 !important;
        bottom: 0 !important;
        height: 42px !important;
        display: flex !important;
        align-items: center !important;
        /* A la IZQUIERDA de la franja: la esquina derecha la ocupa el botón
           'Manage app' de Streamlit Cloud y tapaba el texto. */
        justify-content: flex-start !important;
        padding: 0 24px !important;
        margin: 0 !important;
        z-index: 999991 !important; /* por encima de .stApp::after */
        pointer-events: none !important;
        /* El bloque vertical de Streamlit es columna con gap: en fila y sin
           separaciones el texto queda centrado DENTRO de la franja de 42px
           (antes desbordaba por debajo del viewport). */
        flex-direction: row !important;
        gap: 0 !important;
    }
    .st-key-footer_actualizacion > div {
        height: auto !important;
        margin: 0 !important;
    }
    .st-key-footer_actualizacion .ultima-actualizacion {
        margin: 0 !important;
        font-size: 12px !important;
        color: var(--text-muted, #9aa0a6) !important;
        white-space: nowrap !important;
    }
"""
