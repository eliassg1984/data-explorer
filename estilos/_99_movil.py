"""estilos._99_movil - SIEMPRE AL FINAL. Overrides moviles de Ajuste, Compras, navegación y franjas fijas. Va ultimo a proposito: si sube de posicion, las reglas de escritorio lo pisan.

Extraido de estilos.py (lineas 1554-1694 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    .st-key-nav_menu_movil { display: none !important; }
    /* =================================================================== */
    /* MÓVIL — AJUSTE DE INVENTARIO Y ELEMENTOS FIJOS                       */
    /* Bloque de Ajuste: agrupa los overrides móviles de la sección         */
    /* Ajuste + selector de vista + franjas fijas. Va al final para que no  */
    /* lo pisen los estilos de escritorio definidos arriba.                 */
    /* =================================================================== */
    @media screen and (max-width: 768px) {
        /* LA BARRA DE NAVEGACIÓN NO ESTÁ ARRIBA: en móvil `nav_rail` se va
           al pie de la pantalla (bottom nav, navegacion.py). Poniendo la
           variable en 0 vuelven solos a su sitio los seis `calc()` que en
           escritorio corren cosas hacia abajo por la franja: la banda
           blanca (_40_ajuste_franja), el pill de fecha, los chips, el
           stepper de cortes —borrado el 2026-10-11, #635— y el título
           de Ventas (_50_fecha), y el rail
           derecho de vistas (_20_compras_rail). Sin esto, cada uno tendría
           que repetir su override acá. */
        :root {
            --nav-top-alto: 0px;
            /* La franja de reportes es de escritorio: aca los reportes
               viven en la barra inferior. Ver _00_base.py. */
            --franja-rep-alto: 0px;
            /* Y lo que reserva en reposo, que es lo que suman los offsets
               del cromo (_00_base.py). Sin esto el rail y su cabecera
               bajarian 12px por una franja que aca no existe. */
            --franja-rep-reserva: 0px;
            /* El padding-top del contenido (`navegacion.py::_CSS_AJUSTE`) es
               GLOBAL y cuelga de esta variable. El 2026-09-13 bajo de 76 a 52
               en `_00_base.py` por la franja de reportes, que aca no existe:
               sin esto el contenido de movil subia 24px contra el pill de
               fecha y la banda, que reservan su propio sitio. Queda como
               estaba. */
            --cab-offset-contenido: 76px;
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
            /* El default (_40_ajuste_franja.py) alinea left:170px/right:163px
               con el borde real de la tarjeta del gráfico en desktop (rail
               90px + padding-left 80px de Streamlit / padding-right 153px
               del rail). En móvil no hay rail izquierdo (nav es barra
               inferior) ni esa tarjeta con la que alinearse igual — la
               fecha queda sola a la izquierda, sin chips al lado (ver más
               abajo) — así que la franja vuelve a ir de borde a borde,
               como antes del 2026-08-06. */
            right: 0 !important;
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
        /* Pill SÓLIDO acento. Fue el mismo que en escritorio hasta el
           2026-08-09, cuando el de escritorio pasó a outline (blanco +
           borde) porque era el único bloque relleno entre chips y
           segmentados outline. Acá se dejó sólido A PROPÓSITO: en móvil
           el pill está SOLO en la barra — no hay chips outline al lado
           con los que desentonar — y el relleno da mejor lectura de
           "esto se toca". Si algún día móvil suma chips a la barra,
           revisar esta divergencia. Ver _50_fecha.py, bloque
           min-width:901px. Antes móvil se quedaba con el look "pestaña"
           de la regla base — degradado violeta + barra inferior de 3px —
           porque aquel bloque nunca cruzó el breakpoint. Se replica acá en
           vez de bajar el min-width porque las medidas cambian: en
           escritorio el pill mide 28px para emparejar con los chips
           vecinos; en móvil no hay chips al lado, así que originalmente
           iba mas alto (34px) para el touch target.
           2026-08-06: top bajado de 8px -> 5px -> 1px -> 0 ("dejalo
           pegado", a pedido, en varias pasadas) — pegado al borde
           superior real de la franja (el ::before de fila_ajuste_top
           arranca en top:0), ya no centrado (antes 8+8 parejo). Despues
           "mas delgado" a pedido: min-height 34px -> 30px (mismo motivo
           de touch target, pero ya no tan holgado). Si en algun momento
           hace falta volver a agrandar el area de toque, subir esto, no
           el padding (es 0 arriba/abajo a proposito).
           OJO: esta sección va ÚLTIMA en _SECCIONES, así que con la misma
           especificidad que la regla base ya le gana; no hace falta el
           truco de clase duplicada (.st-key-X.st-key-X) que usa el bloque
           de escritorio. Los estados :hover / [aria-expanded] también
           tienen que redefinirse — si no, la base los devuelve al
           degradado apenas se tocan. */
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
            min-height: 30px !important;
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

        /* Popovers: no crear scroll lateral */
        [data-testid="stPopover"] button {
            min-width: 0 !important;
            max-width: 100% !important;
        }

        /* La franja de REPORTES no existe en móvil: allá los reportes
           viven en la barra inferior (`navegacion.py::nav_movil`), y una
           segunda lista de los mismos nombres arriba sería la duplicación
           que en escritorio justamente NO es (allá el rail se va al
           scrollear; la barra inferior de móvil no se va nunca).
           `--franja-rep-alto` ya vale 0 acá, así que nada quedó corrido:
           esto sólo saca la franja de la pantalla. */
        .st-key-nav_franja_rep { display: none !important; }

        /* Chips pegados a la franja (el margen de 6px es para tablet) */
        .st-key-chips_ajuste_tabla {
            margin: 2px 0 0 0 !important;
            z-index: auto !important;
            /* 2026-08-31: el filete, el fondo y el radio son del
               COMPARTIMENTO de la franja de escritorio — dividen la franja
               en dos zonas. Acá el control vuelve al flujo del documento y
               no divide nada: sin esto se veía como una media tarjeta
               blanca suelta arriba del contenido. Misma idea que el
               `position: static` que ya recibe. */
            border-left: none !important;
            border-radius: 0 !important;
            background: transparent !important;
            height: auto !important;
            padding: 0 !important;
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

        /* ===== Familia × Área (Ajuste): la tabla SIGUE siendo tabla =====
           Misma trampa que tenía la vieja fila de la Cascada: el bloque
           de arriba de este archivo pone `flex-direction: column` a TODO
           stHorizontalBlock en móvil, y cada fila de la tabla es un
           st.columns() — sin esto las celdas de una fila se apilan una
           debajo de otra y la tabla pasa a ser una lista vertical (lo
           reportado sobre el Mapa el 2026-08-10: ~10.000px de alto medido
           en 375px). La grilla ya trae `overflow-x: auto` desde
           _heatmap.py, así que al mantener la fila en `row` el desborde se
           navega con scroll horizontal. Los anchos de columna (170px la
           de familia, 88px las de dato) los fija _heatmap.py y ganan por
           especificidad: acá sólo se corrige la DIRECCIÓN. Regla #468. */
        .st-key-hm_tabla [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
        }

        /* El sello de «Última actualización» se apoya sobre la barra nav
           móvil, y el contenido tiene que terminar por encima de él.

           Acá NO se mudó arriba como en escritorio: en móvil la franja de
           REPORTES no existe (`.st-key-nav_franja_rep { display:none }`,
           más arriba en este mismo fichero), así que el sello se queda
           donde estaba — sólo que ahora flota sobre el lienzo en vez de
           sobre una franja blanca, que se eliminó el 2026-09-08 junto con
           su `.stApp::after`.

           94 = barra nav (60) + los ~18 del sello (vive en `bottom:68px`,
           ver `inyecciones/varios.py::inject_sello_actualizacion`) + 16 de
           aire. Eran 104 cuando el sumando del medio era la franja de
           34px. */
        [data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        .block-container {
            padding-bottom: 94px !important;
        }
    }

    /* Compras en teléfono y tablet angosta. También cubre el teléfono
       girado: 769–900px no debe volver al cromo fijo de escritorio. */
    @media screen and (max-width: 900px) {
        :root:has(.st-key-app_reporte_compras) {
            --nav-top-alto: 0px;
            --franja-rep-alto: 0px;
            --franja-rep-reserva: 0px;
        }
        html body [data-testid="stAppViewContainer"][data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras)
            [data-testid="stMainBlockContainer"] {
            padding: 12px 12px calc(96px + env(safe-area-inset-bottom)) !important;
            max-width: 100% !important;
        }
        html body [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras)
            [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
            gap: 6px !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras) [data-testid="stMain"] {
            scroll-snap-type: none !important;
            scroll-padding-top: 0 !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras) [class*="st-key-compras_sec_"] {
            min-height: 0 !important;
        }
        [data-testid="stLayoutWrapper"]:has(> .st-key-rail_rotulo_rep),
        [data-testid="stLayoutWrapper"]:has(> .st-key-rail_pestillo_plegado),
        [data-testid="stLayoutWrapper"]:has(> .st-key-rail_pestillo_abierto),
        [data-testid="stLayoutWrapper"]:has(> .st-key-nav_franja_rep),
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras)
            [data-testid="stLayoutWrapper"]:has(> .st-key-fila_ajuste_top) {
            display: none !important;
        }
        .st-key-nav_menu_movil {
            display: block !important;
            width: auto !important;
            flex: 0 0 auto !important;
        }
        .st-key-nav_menu_movil [data-testid="stPopoverButton"] {
            min-height: 44px !important;
            min-width: 110px !important;
            padding: 8px 14px !important;
            font-size: 14px !important;
        }
        [data-testid="stPopoverBody"]:has(.navmovil-panel) {
            width: min(360px, calc(100vw - 24px)) !important;
            max-height: 70dvh !important;
            overflow-y: auto !important;
        }
        [class*="st-key-navmovil_"] [data-testid="stButton"] button {
            min-height: 44px !important;
            justify-content: flex-start !important;
        }
        .st-key-compras_tabs_row {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 12px !important;
            overflow: visible !important;
            border: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            width: 100% !important;
            background: transparent !important;
        }
        .st-key-compras_tabs_row > [data-testid="stLayoutWrapper"],
        .st-key-compras_tabs_row > [data-testid="stVerticalBlock"] {
            flex: 0 0 auto !important;
            width: auto !important;
        }
        .st-key-graf_tipo_chips.st-key-graf_tipo_chips { display: none !important; }
        .st-key-rail_refresh {
            position: static !important;
            width: auto !important;
            height: auto !important;
            margin: 0 !important;
        }
        .st-key-rail_refresh button {
            min-height: 44px !important;
            padding: 8px 12px !important;
        }
        .st-key-nav_franja_kpis {
            position: static !important;
            height: auto !important;
            min-height: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
            z-index: auto !important;
            opacity: 1 !important;
            visibility: visible !important;
        }
        .st-key-nav_franja_kpis .franja-kpis {
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            gap: 8px !important;
            white-space: normal !important;
        }
        .st-key-nav_franja_kpis .franjakpi-nom {
            grid-column: 1 / -1;
            padding: 4px 48px 6px 0;
            font-size: 22px !important;
        }
        .st-key-nav_franja_kpis .franjakpi-sep { display: none !important; }
        .st-key-nav_franja_kpis .franjakpi-par {
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--bg-card);
            gap: 4px !important;
        }
        .st-key-nav_franja_kpis .franjakpi-rot { font-size: 11px !important; letter-spacing: normal !important; color: var(--text-secondary) !important; }
        .st-key-nav_franja_kpis .franjakpi-val { font-size: 18px !important; }
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras) .st-key-fila_ajuste_top { display: none !important; }
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras) .st-key-nav_franja_rep { display: none !important; }
        .st-key-cp_sem_fecha {
            position: static !important;
            width: 100% !important;
            margin: 0 !important;
        }
        .st-key-cp_sem_fecha button[data-testid="stPopoverButton"] {
            min-height: 44px !important;
            max-width: 100% !important;
            padding: 8px 12px !important;
            font-size: 13px !important;
            white-space: normal !important;
        }
        .st-key-ajuste_graf_card_izq_sem {
            padding: 12px !important;
            border-radius: 16px !important;
            gap: 10px !important;
        }
        /* Navegación de vistas y actualización comparten un pie opaco;
           el gráfico termina antes y el fullscreen tiene su propio sitio. */
        html body .st-key-nav_rail {
            position: fixed !important;
            display: flex !important;
            flex-direction: row !important;
            top: auto !important;
            bottom: calc(24px + env(safe-area-inset-bottom)) !important;
            left: 56px !important;
            right: 0 !important;
            width: calc(100% - 56px) !important;
            height: 56px !important;
            min-height: 56px !important;
            padding: 4px !important;
            border: 0 !important;
            border-radius: 0 !important;
            background: var(--bg-card) !important;
            box-shadow: var(--shadow-md) !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            z-index: 1000000 !important;
        }
        html body .st-key-nav_rail [data-testid="stElementContainer"],
        html body .st-key-nav_rail [data-testid="stButton"] {
            width: auto !important;
            flex: 0 0 auto !important;
        }
        html body .st-key-nav_rail [data-testid="stButton"] button {
            width: auto !important;
            min-height: 44px !important;
            height: 44px !important;
            padding: 0 14px !important;
            border-radius: 10px !important;
        }
        html body .st-key-nav_rail [data-testid="stButton"] button p { font-size: 13px !important; }
        html body #sello-actualizacion {
            display: flex !important;
            top: auto !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            width: 100% !important;
            height: calc(24px + env(safe-area-inset-bottom)) !important;
            padding: 3px 12px calc(3px + env(safe-area-inset-bottom)) !important;
            border: 0 !important;
            border-radius: 0 !important;
            background: var(--bg-card) !important;
            font-size: 10px !important;
        }
        html body #app-fs-btn {
            display: block !important;
            left: 0 !important;
            bottom: calc(24px + env(safe-area-inset-bottom)) !important;
            width: 56px !important;
            height: 56px !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
    }
    @media screen and (min-width: 600px) and (max-width: 900px) and (max-height: 500px) {
        .st-key-nav_franja_kpis .franja-kpis { grid-template-columns: repeat(4, minmax(0, 1fr)) !important; }
        .st-key-nav_franja_kpis .franjakpi-par { padding: 6px 10px; }
    }
    /* Misma geometría móvil en todos los reportes. Las fechas y filtros
       nativos conservan su estado y pasan al flujo antes de las piezas. */
    @media screen and (max-width: 900px) {
        :root {
            --nav-top-alto: 0px;
            --franja-rep-alto: 0px;
            --franja-rep-reserva: 0px;
        }
        html body [data-testid="stAppViewContainer"][data-testid="stAppViewContainer"][data-testid="stAppViewContainer"]
            [data-testid="stMainBlockContainer"] {
            padding: 12px 12px calc(96px + env(safe-area-inset-bottom)) !important;
            max-width: 100% !important;
        }
        html body [data-testid="stAppViewContainer"] [data-testid="stMain"] {
            scroll-snap-type: none !important;
            scroll-padding-top: 0 !important;
        }
        html body [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap: 8px !important; }
        [class*="st-key-"][class*="_sec_"]:not([class*="st-key-pila_go_"]) { min-height: 0 !important; }
        html body .st-key-fila_ajuste_top {
            position: static !important; height: auto !important; min-height: 0 !important;
            margin: 0 !important; padding: 0 !important;
        }
        .st-key-fila_ajuste_top::before { display: none !important; }
        html body .st-key-fecha_ajuste_pill {
            position: static !important; top: auto !important; left: auto !important;
            right: auto !important; width: auto !important; margin: 0 !important;
        }
        .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 8px !important; }
        html body .st-key-chips_ajuste_tabla { position: static !important; height: auto !important; margin: 0 !important; }
        html body :is(.st-key-vt_periodo_fecha, .st-key-cp_vol_fecha, .st-key-vt_mes_fecha,
            .st-key-vt_ctl_nativa_fecha, .st-key-cp_docs_nativa_fecha,
            .st-key-ajdet_fecha_nativa, .st-key-mov_pporc_nativa_fecha,
            .st-key-stock_mov_cab_fecha, .st-key-merma_revision_fecha,
            .st-key-rec_carta_cab_fecha, .st-key-rec_alza_cab_fecha, .st-key-rec_cambios_cab_fecha,
            [class*="_nativa_fecha"]) {
            position: static !important; top: auto !important; left: auto !important;
            right: auto !important; width: 100% !important; height: auto !important;
            min-height: 0 !important; margin: 0 0 8px !important;
        }
        html body [data-testid="stAppViewContainer"] [data-testid="stPopoverButton"],
        html body [data-testid="stAppViewContainer"] [data-testid="stButton"] button {
            min-height: 44px !important; height: auto !important;
            max-width: 100% !important;
        }
        html body [data-testid="stAppViewContainer"] [data-testid="stPopoverButton"] {
            padding: 8px 12px !important; font-size: 14px !important;
        }
        .st-key-fila_ajuste_top .franja-titulo-app { position: static !important; }
        :is(.st-key-rec_carta_cab, .st-key-rec_alza_cab, .st-key-rec_cambios_cab,
            .st-key-vt_mix_cab, .st-key-vt_hora_cab) {
            flex-wrap: wrap !important; gap: 8px !important;
        }
        :is(.st-key-rec_carta_cab, .st-key-rec_alza_cab, .st-key-rec_cambios_cab,
            .st-key-vt_mix_cab, .st-key-vt_hora_cab)
            > :is([data-testid="stLayoutWrapper"], [data-testid="stElementContainer"]) {
            flex: 1 1 100% !important; width: 100% !important; min-width: 0 !important;
        }
        /* Movimientos por Tipo (regla #747): el título y el reloj se apilan,
           pero ‹ mes › sigue en su renglón. Apilado, el ancho del desplegable
           (200px) pasaba a ser su ALTO: un hueco de 160px entre las flechas. */
        html body .st-key-stock_mov_cab_periodo {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
        }
        .pila-hueco { min-height: 240px; }
    }
    </style>"""
