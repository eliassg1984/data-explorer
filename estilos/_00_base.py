"""estilos._00_base - Fundaciones: @import de la fuente, paleta :root, geometria de la cabecera fija, ocultado del chrome de Streamlit y resets globales de widgets. Todo lo demas asume que esto ya se aplico.

Extraido de estilos.py (lineas 109-467 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

    /* ============ PALETA DE COLORES — TEMA CALLAI (Lavender Indigo) ============ */
    :root {
        --bg-primary: #faf9fb;      /* lienzo general (casi blanco, tinte lavanda) */
        --bg-secondary: #ffffff;
        --bg-sidebar: #ffffff;      /* sidebar blanco estilo CallAI */
        --bg-card: #ffffff;
        /* Tarjeta TENUE: el mismo gris que el lienzo, usado al revés.
           En el resto de la app la página es --bg-primary y las tarjetas
           blancas; en Compras la página quedó blanca (ver _50_fecha.py) y
           las tarjetas se separan con este gris. Es un alias a propósito y
           no un hex nuevo: la relación entre los dos tonos ya está probada
           en todos los demás reportes, sólo que invertida. Retocar el tinte
           de Compras = cambiar esta línea. */
        --bg-card-tenue: var(--bg-primary);
        --bg-hover: #f0edfe;        /* hover lavanda suave */
        --text-primary: #18181d;    /* casi negro */
        --text-secondary: #71717a;
        --text-muted: #a2a2ad;
        --accent: #6c5ce7;          /* Lavender Indigo */
        --accent-hover: #5a4ad9;
        --accent-deep: #4938b8;
        --accent-light: #e7e3fb;    /* lavanda 100 */
        --accent-tint: #f0edfe;     /* lavanda 50 */
        --border: #e6e6eb;
        --success: #16a34a;
        --success-bg: #f0fdf4;
        --warning: #f97316;
        --warning-bg: #fff7ed;
        --warning-border: #fdba74;
        --warning-text: #c2410c;
        --danger: #ef4444;
        --danger-bg: #fee2e2;
        --danger-border: #fca5a5;
        --danger-text: #991b1b;
        /* Espejo CSS de PALETA_SERIES[1] y [2] de tema.py — las usan las
           líneas %Δ pax / %Δ ticket del comparativo de Ventas, y el
           cuadradito-checkbox de su panel "Detalle" tiene que coincidir.
           Si cambia PALETA_SERIES, cambiar acá también (regla #1). */
        --serie-pax: #22b8d4;
        --serie-ticket: #e85ba8;
        --border-lavender: #d4cdf7; /* borde lavanda de pastillas/inputs */
        --icon-muted: #85858f;
        --focus-lavender: #b9aff2;  /* borde de foco/selección */
        --line-soft: #f1f1f4;
        --exit-hover: #52525c;
        --scroll-thumb: #d6d6dd;
        --shadow: 0 1px 3px rgba(16, 16, 20, 0.05), 0 1px 2px rgba(16, 16, 20, 0.04);
        --shadow-md: 0 4px 6px rgba(16, 16, 20, 0.05), 0 2px 4px rgba(16, 16, 20, 0.03);

        /* ==================================================================
           GEOMETRÍA DE LA CABECERA FIJA — AJUSTE DE INVENTARIO
           Única fuente de verdad de la franja blanca superior. Todos los
           elementos fijados (banda, pestañas, chips) y la compensación del
           contenido derivan de estas variables. NUNCA escribir estos px
           sueltos en otras reglas; consumir siempre la variable.
           Mapa completo de knobs: ver arquitectura.md § Cabecera fija.
           ================================================================== */
        /* Franja de UN SOLO NIVEL (título + filtros + fecha). Los tabs
           Gráficos/Tabla salieron de la banda al canvas, así que la altura
           baja de 104px (2 niveles) a ~50px (1 nivel). Ajustable en preview. */
        --cab-altura: 50px;
        /* 30px hasta el 2026-08-18. La franja ya no arranca en el borde de
           la ventana: encima de ella vive la barra de navegación superior,
           así que su anclaje se corre --nav-top-alto (30 + 40 = 70). */
        /* 2026-08-31: 70 -> 108, los 38px de la franja de reportes. */
        --cab-nivel1-top: 108px;
        --cab-nivel2-top: 52px;   /* legacy: ya no hay nivel 2 en la banda */
        /* 58px hasta el 2026-08-14. Medido en el navegador: la franja ocupa
           de y=8 a y=37 (29px reales de controles) y la tarjeta arrancaba en
           y=74 — o sea 37px de AIRE MUERTO entre el último chip y el borde
           de la tarjeta. Con 44 la franja no se mueve (su `margin-top` es
           `-1 * esta variable`, así que se compensa sola) y la tarjeta sube
           14px. Queda un respiro de ~21px entre chips y tarjeta.
           Si se toca: `_CAB_OFFSET` en graficos/alturas.py cuenta lo mismo y
           test_graficos.py falla si se desincronizan.
           2026-08-18: 40 -> 80. El rail de navegación dejó de ser una columna
           izquierda y pasó a ser la barra superior (--nav-top-alto): sus 40px
           ya no salen del ANCHO sino del ALTO, y el contenido tiene que
           arrancar debajo de la barra Y de la franja. Va LITERAL y no
           calc(var(--nav-top-alto) + 40px) a propósito: test_graficos.py lee
           esta variable con un regex de `\\d+px` para cotejar el cromo de CSS
           contra el de graficos/alturas.py, y un calc() lo dejaría ciego. */
        /* 2026-08-31: 80 -> 118. La franja de reportes (--franja-rep-alto,
           38px) se suma al cromo de arriba, asi que el contenido arranca 38px
           mas abajo y el presupuesto vertical baja otro tanto. Va LITERAL y
           no `calc(80px + var(--franja-rep-alto))` por lo que dice el parrafo
           de arriba: test_graficos.py lee esta variable con un regex de
           `\d+px` para cotejarla contra graficos/alturas.py, y un calc() lo
           dejaria ciego. Si se cambia el alto de la franja, este numero y el
           `_CAB_OFFSET` de alturas.py se cambian a mano, los dos. */
        --cab-offset-contenido: 118px;

        /* ==================================================================
           PRESUPUESTO VERTICAL — cuánto mide "una pantalla" de contenido
           Única fuente de verdad del cromo fijo que hay por ENCIMA y por
           DEBAJO de las tarjetas. Nació el 2026-08-13, cuando se midió que
           19 de 24 vistas no entraban en un laptop de 1366x768.

           --alto-util es lo que queda para la tarjeta. Se usa para ENMARCAR
           (tarjeta de una pantalla exacta con scroll interno); el alto de
           las FIGURAS no sale de aquí sino de graficos/alturas.py, porque
           Plotly no llena su contenedor y sólo obedece a fig.layout.height
           — está medido y explicado en el docstring de ese módulo.

           Los dos ficheros tienen que decir lo mismo: los sumandos de aquí
           son los mismos que CROMO en graficos/alturas.py, y test_graficos
           falla si se desincronizan. NUNCA escribir estos px sueltos.
           ================================================================== */
        --franja-inf-alto: 42px;      /* la franja blanca fija de abajo */
        /* 66px hasta el 2026-08-14, contra una franja que mide 42: 24px de
           reserva que no cubría nada. Con 48 quedan 6px de aire entre el
           borde de la tarjeta y la franja. */
        --franja-inf-reserva: 48px;   /* lo que reserva el block-container */
        /* 16px hasta el 2026-08-15. Medido: la franja termina en y=36 y la
           tarjeta arrancaba en 60 — 24px de hueco para una barra que el
           usuario quiere «casi rozando». Con 8 quedan 4px de aire y el alto
           útil gana 16 (el margen cuenta arriba Y abajo). */
        --margen-tarjeta: 8px;        /* margen de bloque de Streamlit, arriba y abajo */
        --alto-util: calc(100dvh - var(--cab-offset-contenido)
                                 - var(--franja-inf-reserva)
                                 - var(--margen-tarjeta) * 2);

        /* ==================================================================
           BARRA DE NAVEGACIÓN ENTRE REPORTES — arriba en escritorio, abajo
           en móvil. Son la MISMA fila de botones (`nav_rail`), reacomodada.

           --nav-top-alto es el alto de la barra superior en escritorio, y la
           distancia que TODO lo que estaba anclado al borde de arriba se
           corre hacia abajo: la franja de fecha/chips, sus controles fijos y
           el rail derecho de vistas. Nadie escribe esos 40px sueltos: se
           consume la variable con calc().

           En móvil vale 0 (la barra se va abajo, ver _99_movil.py), y así
           todos esos calc() vuelven solos a los valores de siempre.
           ================================================================== */
        --nav-top-alto: 40px;
        /* LA FRANJA DE REPORTES (2026-08-31, a pedido). Va arriba de todo,
           por encima de las dos bandas que ya existian, y desplaza a TODO el
           cromo fijo que se ancla al borde superior de la ventana. Por eso
           es una variable y no un 38 suelto: son ocho `top` en cinco
           ficheros los que la suman. En movil vale 0 (`_99_movil.py`), igual
           que --nav-top-alto: alla la navegacion es la barra de abajo.
           38px ~= 1cm a 96dpi, que fue el pedido literal. */
        --franja-rep-alto: 38px;

        /* Barra inferior de navegación en móvil (bottom nav).
           Debe coincidir con NAV_MOVIL_ALTO en navegacion.py (60px). */
        --nav-movil-alto: 60px;

        /* ==================================================================
           ANCHO DEL RAIL DERECHO — única fuente de verdad (2026-08-15)
           Hasta entonces estos números vivían escritos a mano en sitios que
           se derivaban entre sí: el `left` de la franja inferior, el
           `padding-right` del contenido, y los anclajes `right` de la fecha,
           los chips y los atajos. Cambiar uno sin los otros dejaba la franja
           superior flotando sobre el vacío — es la regla #17, la parte más
           frágil de este CSS.

           Ahora son variables y todo lo demás las deriva con calc(), así
           que un cambio de ancho lo siguen solos todos los anclajes que
           dependen de él.

           2026-08-18: el rail IZQUIERDO (navegación) ya no existe —es la
           barra superior, --nav-top-alto— así que --rail-izq-w y
           --rail-izq-full se retiraron. Lo que reservaba en ancho (90px) lo
           recuperó el contenido: los anclajes `left` de la franja se
           recalcularon restando esos 90px (_40_ajuste_franja.py,
           _50_fecha.py) y la franja inferior arranca en 0.

           2026-08-26: se retira el PLEGADO ("eliminemos esto y que las
           filas de los reportes del rail suban"). Hasta acá --rail-der-w
           tenía dos estados —desplegado (--rail-der-full) y plegado
           (--rail-min)— que redefinía `estilos/_25_rails_pestillo.py`
           (borrado con `pestillos.py`, que era el único módulo que los
           escribía). Sin pestillo no hay un tercer estado que fijar: el
           rail vale SIEMPRE su ancho desplegado, así que las dos variables
           se funden en una sola.

             OJO con el nombre: desde 2026-08-18 el rail de vistas vive
             a la IZQUIERDA (ocupó el sitio que dejó el rail de
             navegación al pasar a franja superior). El `der` de estas
             variables es histórico; se conservó para no repartir un
             renombre por varios ficheros y un test en el mismo commit
             que mueve el layout. Lo que sí es cierto hoy: son el ancho y
             la reserva del RAIL DE VISTAS, del lado que esté.

             --rail-der-w    ancho del rail de vistas. Fijo (2026-08-26):
                             ya no hay un plegado que lo achique.
             --rail-der-res  lo que el CONTENIDO le reserva al rail derecho.
                             Derivado, no escrito: ancho + los 15px que lo
                             despegan del borde + 54px de aire hasta la
                             tarjeta (84 + 15 + 54 = 153, el valor histórico).
           ================================================================== */
        /* 2026-08-23 (arquitectura.md regla #174): 84px -> 270px como
           default ÚNICO, y se borra la excepción `:has(.st-key-app_reporte_
           compras)` que vivía acá (pisaba esta misma variable a 270px SOLO
           para Compras). Tenía sentido hasta el 2026-08-22: este rail
           dibujaba VISTAS, contenido que variaba por reporte —angosto en
           casi todos, una lista icono+nombre+chevron sólo en Compras—. Con
           la inversión Reportes↔Vistas (regla #170) el rail pasó a dibujar
           siempre REPORTES: la MISMA lista de 6 ítems (icono+nombre+KPI,
           regla #171), sin importar cuál esté activo. La excepción quedó
           pisando el reporte equivocado: cualquiera menos Compras se
           quedaba en 84px, muy angosto para "S/ -56.3k" o el nombre más
           largo, con un salto visible de 270→84px al navegar. Verificado en
           vivo (preview local, datos reales): con la excepción, Compras
           medía 270px y Ajuste de Inventario/Ventas medían 84px sobre el
           mismo `.st-key-compras_tabs_row`; con el default único los tres
           dan 270px. El valor 270px en sí (antes 230px) se sigue debiendo
           al pedido del 2026-08-22 — ver regla #169 para esa parte.
           2026-08-23 (2): 270px -> 350px, a pedido ("los veo muy
           delgados") entendido como ancho — junto con el texto/ícono de
           los ítems, ver estilos/_20_compras_rail.py y
           navegacion.py::_CSS_KPIS.
           2026-08-23 (3): 350px -> 280px. El pedido "delgados" era sobre
           el LARGO VERTICAL de cada fila, no el ancho — el ancho vuelve
           cerca del original (270px) y el alto de fila sube por el
           padding vertical del botón (_20_compras_rail.py). El texto/
           ícono (2) se queda: ese sí era el pedido correcto. */
        --rail-der-w: 280px;
        /* 2026-08-25: el canal entre el rail y las tarjetas baja de 54px
           a 24px, a pedido ("pierdo mucho espacio"). Los sumandos dicen lo
           que son: 19px es el `left` del rail (_20_compras_rail.py) y 24px
           el canal visible. Antes eran 15+54 = 69, con el 15 sin
           corresponderse ya con ese `left` — el rail terminaba en x=299 y
           las tarjetas arrancaban en 349. Ahora arrancan en 323 y el
           contenido gana 26px de ancho. */
        --rail-der-res: calc(var(--rail-der-w) + 19px + 24px);
    }

    /* ============ HEADER NATIVO + ESPACIO SUPERIOR ============ */
    header[data-testid="stHeader"],
    .stAppHeader {
        background: transparent !important;
        border-bottom: none !important;
        box-shadow: none !important;
        height: 0 !important;
        min-height: 0 !important;
    }

    /* PADDING SUPERIOR — DEFAULT GLOBAL (nivel 1 de 3).
       Jerarquía documentada en ARQUITECTURA.md:
         1) Este default global (1.5rem).
         2) Override POR SECCIÓN en navegacion.py (p.ej. _CSS_AJUSTE, 0.85rem).
         3) Override MÓVIL en el @media (max-width: 768px) de este fichero. */
    .stMainBlockContainer,
    [data-testid="stMainBlockContainer"],
    .block-container {
        padding-top: 1.5rem !important;
    }

    [data-testid="stSidebarHeader"] {
        height: 2rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* ============ IFRAMES INVISIBLES (por defecto) ============ */
    [data-testid="stIFrame"] {
        height: 0 !important;
        min-height: 0 !important;
        display: block !important;
    }
    [data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    /* ============ EXCEPCIÓN: PANEL DE RENDIMIENTO DEL NAVEGADOR ============ */
    .st-key-perf_browser_expander [data-testid="stIFrame"] {
        height: 300px !important;
        min-height: 300px !important;
        display: block !important;
    }
    .st-key-perf_browser_expander [data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {
        height: auto !important;
        min-height: 300px !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: visible !important;
        display: block !important;
    }


    /* ============ BOTÓN PARA EXPANDIR EL SIDEBAR ============ */
    [data-testid*="SidebarCollaps"],
    [data-testid="collapsedControl"],
    [data-testid*="xpandSidebar"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }

    /* ============ ESTILOS BASE ============ */
    [data-testid="stAppViewContainer"] {
        background: var(--bg-primary);
    }

    /* html/body de fondo: hasta el 2026-08-18 `.stApp` llevaba un
       `margin-left` del ancho del rail, así que esa columna quedaba FUERA de
       su caja y sin el background de stAppViewContainer. Ya no hay rail
       lateral (es la barra superior), pero el fondo se mantiene: sigue
       cubriendo cualquier borde que quede fuera de la caja de .stApp.
       Ver arquitectura.md — nav_rail. */
    html, body {
        background: var(--bg-primary) !important;
    }

    h1 {
        margin-bottom: 0.2rem !important;
        padding-top: 0 !important;
        color: var(--text-primary) !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] {
        background: var(--bg-sidebar);
        border-right: 1px solid var(--border);
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-primary);
    }

    h2, h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    h4 {
        color: var(--accent) !important;
        font-weight: 600 !important;
    }

    label {
        color: var(--text-secondary) !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        font-weight: 600 !important;
    }

    /* ============ INPUTS Y BOTONES ============ */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stDateInput > div > div {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }

    .stSelectbox > div > div:hover,
    .stMultiSelect > div > div:hover {
        border-color: var(--accent) !important;
    }

    button[kind="secondary"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }

    button[kind="secondary"]:hover {
        background: var(--bg-hover) !important;
        border-color: var(--accent) !important;
    }

    button[kind="primary"] {
        background: var(--accent) !important;
        border: none !important;
        color: white !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(108, 92, 231, 0.28) !important;
    }

    button[kind="primary"]:hover {
        background: var(--accent-hover) !important;
    }

    /* ============ EXPANDER ============ */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }

    /* ============ CAPTION Y ALERTAS ============ */
    .stCaption {
        color: var(--text-muted) !important;
    }

    .stWarning {
        background: var(--warning-bg) !important;
        border: 1px solid var(--warning-border) !important;
        color: var(--warning-text) !important;
        border-radius: 8px !important;
    }

    .stInfo {
        background: var(--accent-light) !important;
        border: 1px solid var(--focus-lavender) !important;
        color: var(--accent-deep) !important;
        border-radius: 8px !important;
    }

    .stError {
        background: var(--danger-bg) !important;
        border: 1px solid var(--danger-border) !important;
        color: var(--danger-text) !important;
        border-radius: 8px !important;
    }

    /* ============ SIDEBAR NAV ============ */
    [data-testid="stSidebar"] .nav-link {
        background: var(--bg-secondary) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] .nav-link:hover {
        background: var(--bg-hover) !important;
        color: var(--accent-hover) !important;
        border-color: var(--focus-lavender) !important;
    }

    [data-testid="stSidebar"] .nav-link-selected {
        background: var(--accent) !important;
        color: var(--bg-secondary) !important;
        border-color: var(--accent) !important;
    }

    /* ============ AGGRID - ANCHO COMPLETO ============ */
    .ag-root-wrapper {
        width: 100% !important;
        max-width: 100% !important;
    }

    .ag-body-viewport {
        overflow-x: auto !important;
    }

    /* ============ CONTROL DE TAMAÑO EN SIDEBAR ============ */
    [data-testid="stSidebar"] .stSlider {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* ============ MÓVIL — LAYOUT GENERAL ============ */
    @media screen and (max-width: 768px) {
        header[data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
            border-bottom: none !important;
        }

        [data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }

        [data-testid="stMain"] {
            padding: 0.5rem 0.5rem !important;
            margin-top: 0 !important;
        }

        .block-container,
        .stMainBlockContainer {
            padding: 0.5rem !important;
            margin-top: 0 !important;
            gap: 0 !important;
        }

        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        [data-testid="stSidebar"] {
            max-height: 100vh;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            -webkit-overflow-scrolling: touch;
            background: var(--bg-sidebar) !important;
            width: 100% !important;
            max-width: 100% !important;
        }

        [data-testid="stSidebarUserContent"] {
            padding: 12px 8px !important;
        }

        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stExpandSidebarButton"] button,
        [data-testid="collapsedControl"] button {
            width: 44px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 8px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }

        h1 {
            font-size: 1.3rem !important;
            margin-top: 0 !important;
            padding-top: 0.5rem !important;
        }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 1rem !important; }
        label { font-size: 0.7rem !important; }

        .stApp { padding: 0 !important; }

        button {
            min-height: 44px !important;
            padding: 10px 16px !important;
            font-size: 0.9rem !important;
        }
    }

    /* Marker del reporte activo (ver app.py + arquitectura.md regla #16):
       el div vive dentro de un stElementContainer que Streamlit envuelve;
       el div en si ya tiene display:none pero el wrapper del elemento sigue
       ocupando margin/padding vertical. Aca colapsamos el stElementContainer
       entero cuando su unico proposito es contener el marker. */
    [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] [class*="st-key-app_reporte_"]) {
        display: none !important;
    }
"""
