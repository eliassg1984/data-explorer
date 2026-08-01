"""estilos._10_vista - Selector de vista Tabla/Graficos (pestanas con subrayado, 'Opcion C'). Ver la nota sobre el DOM de st.pills en el docstring del paquete.

Extraido de estilos.py (lineas 468-563 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* SELECTOR DE VISTA (Tabla / Gráficos) — ÚNICO BLOQUE — OPCIÓN C       */
    /*                                                                      */
    /* Estilo "botones ghost":                                              */
    /*   · Contenedor: sin fondo, sin borde.                                */
    /*   · Inactivo:   transparente, texto gris secundario.                 */
    /*   · Hover:      tinte lavanda suave (accent-tint).                   */
    /*   · ACTIVO:     fondo índigo sólido (accent) + texto blanco.         */
    /*                                                                      */
    /* DOM real de st.pills (confirmado con DevTools, ver docstring):       */
    /*   [data-testid="stButtonGroup"] > button[role="radio"]               */
    /*   El activo lleva el atributo `data-selected` (a secas).             */
    /*                                                                      */
    /* Cubre los DOS contextos donde vive el selector:                      */
    /*   · .st-key-ajuste_tabs_top      → franja fija de Ajuste             */
    /*   · [class*="st-key-vistatabs_"] → resto de reportes                 */
    /* Para añadir otro contexto, sumar su selector a cada regla.           */
    /* =================================================================== */

    /* --- Contenedor del grupo --- */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"],
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] {
        display: flex !important;
        width: 100% !important;
        gap: 4px !important;
        margin: 6px 0 0 !important;
        padding: 0 !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 1px solid var(--border) !important;   /* línea base de pestañas */
        border-radius: 0 !important;
        flex-wrap: nowrap !important;
        align-items: flex-end !important;
    }

    /* --- Botón base (estado inactivo): PESTAÑA (subrayado, sin píldora) --- */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"],
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] {
        min-height: 38px !important;
        padding: 8px 16px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        margin-bottom: -1px !important;   /* el subrayado tapa la línea base */
        background: transparent !important;
        color: var(--text-secondary) !important;
        box-shadow: none !important;
        cursor: pointer !important;
        transition: color .15s ease, border-color .15s ease !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"] p,
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] p {
        font-size: 14px !important;
        font-weight: 500 !important;
        color: inherit !important;
        margin: 0 !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"] [data-testid="stIconMaterial"],
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] [data-testid="stIconMaterial"] {
        font-size: 18px !important;
        color: inherit !important;
    }

    /* --- Hover sobre pestaña inactiva --- */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"]:hover:not([data-selected]),
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"]:hover:not([data-selected]) {
        background: transparent !important;
        color: var(--accent-deep) !important;
        border-bottom-color: var(--border-lavender) !important;
    }

    /* --- Botón ACTIVO (data-selected) --- */
    /* Se replica la estructura del selector nativo de Streamlit
       (button[data-selected]:not([data-disabled])) para igualar o superar
       su especificidad y que nuestro estilo gane. */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]),
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]) {
        background: transparent !important;                        /* sin píldora */
        border: none !important;
        border-bottom: 2px solid var(--accent) !important;        /* PESTAÑA activa */
        box-shadow: none !important;
        color: var(--accent-deep) !important;
    }
    /* Texto e icono internos en color de acento (pestaña activa) */
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]) *,
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]) * {
        color: var(--accent-deep) !important;
    }
    .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]):hover,
    [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"][data-selected]:not([data-disabled]):hover {
        background: transparent !important;
        border-bottom-color: var(--accent-hover) !important;
    }
"""
