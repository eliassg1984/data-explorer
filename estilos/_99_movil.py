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
            top: 0 !important;
            left: 12px !important;
            right: auto !important;
            margin: 0 !important;
            z-index: 23 !important;
        }
        /* MISMO pill sólido acento que en escritorio (_50_fecha.py, bloque
           min-width:901px). Antes móvil se quedaba con el look "pestaña"
           de la regla base — degradado violeta + barra inferior de 3px —
           porque aquel bloque nunca cruzó el breakpoint. Se replica acá en
           vez de bajar el min-width porque las medidas cambian: en
           escritorio el pill mide 28px para emparejar con los chips
           vecinos; en móvil no hay chips al lado y 28px queda chico para
           tocar, así que va 34px (altura real medida en vivo, coincide
           con el min-height — la primera medición tras el load dio 40px
           pero era transitoria, de una pasada de layout que aún no había
           asentado el tamaño final).
           2026-08-06: top bajado de 8px -> 5px -> 1px -> 0 ("dejalo
           pegado", a pedido, en varias pasadas) — pegado al borde
           superior real de la franja (el ::before de fila_ajuste_top
           arranca en top:0), ya no centrado (antes 8+8 parejo).
           OJO: esta sección va ÚLTIMA en _SECCIONES, así que con la misma
           especificidad que la regla base ya le gana; no hace falta el
           truco de clase duplicada (.st-key-X.st-key-X) que usa el bloque
           de escritorio. Los estados :hover / [aria-expanded] también
           tienen que redefinirse — si no, la base los devuelve al
           degradado apenas se tocan. */
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
            min-height: 34px !important;
            box-sizing: border-box !important;
            padding: 0 14px !important;
            border: none !important;
            border-radius: 999px !important;
            background: var(--accent) !important;
            box-shadow: none !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            letter-spacing: normal !important;
        }
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
            color: #ffffff !important;
            font-size: 15px !important;
        }
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button:hover {
            border: none !important;
            background: var(--accent-hover) !important;
            color: #ffffff !important;
        }
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button[aria-expanded="true"] {
            border: none !important;
            background: var(--accent-deep) !important;
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

        /* Cascada de Ajuste (graficos/ajuste.py): la fila de familia usa
           st.columns([gutter, familia, ajuste, barra, s/val, %total,
           estado]) — 6 columnas + gutter no entran en un teléfono. Se
           reordena a 2 líneas por nth-child (Streamlit no da una key
           propia a cada columna, hay que apuntar por posición):
             línea 1 → gutter · familia (crece) · estado (badge)
             línea 2 → ajuste · s/val · %total (33% cada uno)
           La barra "Cascada acumulada" (columna 4) se oculta entera: a
           este ancho una barra de ~15px no comunica nada, es ruido.
           OJO — Streamlit fija el ancho de cada columna con una clase
           emotion propia (`.st-emotion-cache-xxxx { flex-basis: calc(N%
           - 1rem) }`), y "width/flex-basis: auto !important" NO le gana
           (el contenido interno se sigue estirando al 100%). Hay que
           fijar `width` Y `min-width` Y `max-width` a un valor concreto
           (mismo patrón que ya usan los chips de arriba), nunca dejarlo
           en "auto". Verificado con getBoundingClientRect en 375px: sin
           esto, las 6 columnas caían cada una en su propia línea en vez
           de compartir 2.
           SEGUNDA TRAMPA — Streamlit ya cambia `flex-direction` de la
           fila a `column` en su propio responsive nativo por debajo de
           cierto ancho (apila los st.columns uno debajo del otro por
           defecto). `flex-wrap: wrap` sin forzar `flex-direction: row`
           envuelve en el eje vertical (columnas lado a lado si se pasan
           de ALTO), no en el horizontal — por eso cada item seguía
           cayendo en su propia línea aunque el ancho ya sobraba. */
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: wrap !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1) {
            order: 1 !important;
            flex: 0 0 28px !important;
            width: 28px !important; min-width: 28px !important; max-width: 28px !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {
            order: 2 !important;
            flex: 1 1 auto !important;
            width: auto !important; min-width: 90px !important; max-width: 55% !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(7),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(7) {
            order: 3 !important;
            flex: 0 0 76px !important;
            width: 76px !important; min-width: 76px !important; max-width: 76px !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
            display: none !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(5),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(5),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(6),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(6) {
            flex: 1 1 calc(33.33% - 6px) !important;
            width: calc(33.33% - 6px) !important;
            min-width: calc(33.33% - 6px) !important;
            max-width: calc(33.33% - 6px) !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) {
            order: 4 !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(5),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(5) {
            order: 5 !important;
        }
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(6),
        div[class*="st-key-ajcas_fila_"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(6) {
            order: 6 !important;
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
