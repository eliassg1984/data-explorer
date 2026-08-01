"""estilos._99_movil - SIEMPRE AL FINAL. Unico @media que agrupa los overrides moviles de Ajuste, selector de vista y franjas fijas. Va ultimo a proposito: si sube de posicion, las reglas de escritorio lo pisan.

Extraido de estilos.py (lineas 1554-1694 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* MÓVIL — AJUSTE DE INVENTARIO Y ELEMENTOS FIJOS                       */
    /* ÚNICO @media final: agrupa todos los overrides móviles de la sección */
    /* Ajuste + selector de vista + franjas fijas. Va al final para que no  */
    /* lo pisen los estilos de escritorio definidos arriba.                 */
    /* =================================================================== */
    @media screen and (max-width: 768px) {
        /* Encabezado de Ajuste: sin rail a la izquierda (nav es barra
           inferior en móvil), los anclajes left pasan de 90px+margen a 12px. */
        .titulo-ajuste-reporte {
            transform: none !important;
            font-size: 1.3rem !important;
            left: 12px !important;
            /* No pisarse con la pill de fecha fija de la derecha */
            max-width: calc(100vw - 220px) !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
        }
        .st-key-ajuste_tabs_top {
            transform: none !important;
            position: relative !important;
            left: auto !important;
            margin: 2px 0 6px 0 !important;
        }
        /* COLAPSAR el hueco fantasma de la franja: en móvil TODO su
           contenido visible (título, pestañas, fecha) es position:fixed,
           así que su altura en el flujo es espacio muerto — y al apilarse
           las columnas en vertical, ese hueco crece. Se anula la altura y
           el margin-top negativo (que compensaba al padding del contenedor)
           para que el contenido arranque justo bajo la franja fija. */
        .st-key-fila_ajuste_top {
            position: static !important;
            height: 0 !important;
            min-height: 0 !important;
            padding: 0 !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        /* ORDEN DE APILAMIENTO al scrollear (verificado en el DOM real):
           banda blanca (15) TAPA al contenido que sube; los hijos de la
           franja (título/pestañas/fecha, 16) quedan encima de la banda.
           Los chips vuelven a z auto: su z:23 de escritorio aplica aunque
           estén static, porque son flex items — y los ponía sobre la banda. */
        .st-key-fila_ajuste_top::before {
            left: 0 !important;
            z-index: 15 !important;
        }
        .st-key-fila_ajuste_top > * {
            z-index: 16 !important;
        }
        .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] {
            gap: 4px !important;
            align-items: stretch !important;
        }

        /* Fecha como texto: en móvil se ancla a la izquierda tras la
           esquina superior (no hay nav-rail: la barra de nav vive abajo). */
        .st-key-fecha_ajuste_pill {
            position: fixed !important;
            top: 8px !important;
            left: 12px !important;
            right: auto !important;
            margin: 0 !important;
            z-index: 23 !important;
        }
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
            font-size: 13px !important;
        }
        /* Panel a ancho de pantalla en móvil (menos el margen). */
        [data-testid="stPopoverBody"]:has(.st-key-fecha_panel) {
            min-width: min(380px, 92vw) !important;
        }

        /* Selector de vista: mantiene Opción C, más compacto para tocar */
        .st-key-ajuste_tabs_top [data-testid="stButtonGroup"],
        [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] {
            gap: 4px !important;
        }
        .st-key-ajuste_tabs_top [data-testid="stButtonGroup"] button[role="radio"],
        [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] button[role="radio"] {
            min-height: 40px !important;
            padding: 9px 14px !important;
            font-size: 13px !important;
        }

        /* Popovers: no crear scroll lateral */
        [data-testid="stPopover"] button {
            min-width: 0 !important;
            max-width: 100% !important;
        }

        /* Chips pegados a la franja (el margen de 6px es para tablet) */
        .st-key-chips_ajuste_tabla {
            margin: 2px 0 0 0 !important;
            z-index: auto !important;
        }

        /* Avisos: sobre la barra inferior de navegación */
        div[data-testid="stToastContainer"],
        .st-key-aviso_refresco {
            left: 12px !important;
            right: 12px !important;
            max-width: none !important;
            bottom: calc(var(--nav-movil-alto) + 44px) !important;
        }

        /* Chips de Ajuste: 2×2 en móvil en lugar de 4 apilados */
        .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 8px !important;
        }
        .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 1 1 calc(50% - 8px) !important;
            min-width: calc(50% - 8px) !important;
            width: calc(50% - 8px) !important;
        }

        /* Franja inferior + footer: se apoyan sobre la barra nav móvil */
        .stApp::after {
            left: 0 !important;
            height: 34px !important;
            bottom: var(--nav-movil-alto) !important;
        }
        .st-key-footer_actualizacion {
            left: 0 !important;
            padding: 0 12px !important;
            bottom: var(--nav-movil-alto) !important;
            height: 34px !important;
        }
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        .block-container {
            /* Reserva: barra nav (60) + franja (34) + 10 de aire */
            padding-bottom: 104px !important;
        }
    }

    </style>"""
