"""
Estilos globales de la app: CSS, tamaños de fuente e inyección del tema.

ÍNDICE (buscar el header exacto con Ctrl+F)
-------------------------------------------
    L  112  PALETA DE COLORES — variables :root del tema CallAI
    L  170  HEADER NATIVO + ESPACIO SUPERIOR
    L  197  IFRAMES INVISIBLES (por defecto)
    L  211  PANEL DE RENDIMIENTO DEL NAVEGADOR (excepción iframe)
    L  225  BOTÓN PARA EXPANDIR EL SIDEBAR
    L  234  ESTILOS BASE — tipografía, fondos, layout raíz
    L  274  INPUTS Y BOTONES
    L  313  EXPANDER
    L  328  CAPTION Y ALERTAS
    L  354  SIDEBAR NAV
    L  373  AGGRID — ancho completo
    L  383  CONTROL DE TAMAÑO EN SIDEBAR
    L  389  MÓVIL — LAYOUT GENERAL
    L  469  SELECTOR DE VISTA (Tabla / Gráficos) — pestañas ghost
    L  565  PESTAÑAS DE TIPO DE GRÁFICO (fila pegada al tope del gráfico)
    L  606  BOTÓN FILTROS (popover)
    L  624  FILA SUPERIOR DE AJUSTE DE INVENTARIO — franja blanca sticky
    L  684  CHIPS DE FILTRO EN LA FRANJA BLANCA — Área / Familia / etc.
    L  793  FECHA EN EL HEADER — trigger del popover (atajos + calendario)
    L  866  CALENDARIO DESPLEGABLE (BaseWeb)
    L  887  OCULTAR TOOLBARS NATIVAS DE STREAMLIT
    L  907  POSICIÓN DEL TOAST (st.toast)
    L  917  AVISO DE REFRESCO EN CURSO
    L  930  CARDS DE GRÁFICOS — contenedor blanco (ajuste_graf_card_*)
    L 1043  TARJETAS DEL DRILL DE PROVEEDOR (compras_prov_card_*)
    L 1074  FRANJA INFERIOR FIJA — cierre visual del área de contenido
    L 1129  MÓVIL — overrides @media (SIEMPRE al final; no mover)

Al mover secciones, ACTUALIZAR estos números. Los @media al final NO se
tocan de posición: van al fondo para que ninguna regla desktop las pise.

Convención de keys — CRÍTICO para evitar solapes
------------------------------------------------
Un elemento visual = UNA key que es dueña de su estilo.

- La key dueña vive en un `st.container(key="…")` que envuelve al elemento.
- Los WIDGETS (`st.date_input`, `st.pills`, `st.selectbox`) NO se estilan
  por su propia key — se envuelven en un container con key propia y se
  estila el container. Ese container es el único bloque CSS que existe.
- Antes de agregar CSS para un elemento nuevo: `grep -n <key-prefix>`
  aquí; si ya hay otro bloque estilándolo, consolidar en UNO — no dejar
  dos rutas de estilado para el mismo elemento (misma especificidad +
  ambos `!important` = gana el que aparezca ÚLTIMO en el archivo, y eso
  es un bug esperando a pasar).

Excepciones conocidas (widgets estilados por su propia key, legado):
- `[class*="st-key-vistatabs_"]` — pestañas Tabla/Gráficos (bloque L 426).
  A consolidar la próxima vez que se toque ese bloque.

Sobre los `!important` (hoy hay ~450)
-------------------------------------
Casi todos son `!important` LEGÍTIMOS, no deuda: los usamos para ganarle
en especificidad a las clases internas que Streamlit inyecta. Reducir el
número por sí solo no aporta nada. Lo que sí importa:

- Cuando una regla ANULA algo que Python declaró (ej. `st.container(border=
  True)` cuyo borde tapas con `border: none !important`), documentar el
  POR QUÉ arriba de la regla. Un `!important` sin comentario adyacente
  es aceptable; uno que contradice al código Python NO.
- Cuando un cambio de diseño hace innecesario un bloque, borrarlo — no
  dejarlo "por si acaso". Los parches olvidados generan bugs futuros
  (ver commit de bordes del drill Proveedor 2026-07-25, y solape de
  `fch_franja_` vs `fecha_ajuste_pill` 2026-07-26).

Sobre st.pills (importante para futuros cambios de estilo)
----------------------------------------------------------
En la versión actual de Streamlit, st.pills renderiza este DOM:

    div[data-testid="stButtonGroup"]  (con role="radiogroup")
        └── button[role="radio"]      (uno por opción)
                └── atributo `data-selected` SOLO cuando está activo

Por eso todos los selectores del "selector de vista" apuntan a
stButtonGroup / button[role="radio"] / [data-selected].
NO usar [data-testid="stPills"] ni `label` — no existen en este DOM.
Si Streamlit cambia el DOM en una actualización, verificar con DevTools
qué atributo marca el botón activo y actualizar SOLO el bloque
"SELECTOR DE VISTA" (hay uno único, buscar ese título).
"""

import streamlit as st


# ===========================================================================
# MAPEO DE TAMAÑOS DE FUENTE
# ===========================================================================

TAM_FUENTE = {
    "Pequeño": 12,
    "Mediano": 14,
    "Grande": 17,
    "Muy grande": 20
}


# ===========================================================================
# CSS GLOBAL (CACHEADO)
# ===========================================================================

@st.cache_data
def get_css():
    """Retorna el CSS como string (cacheado para no reinyectar)."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&display=swap');

    /* ============ PALETA DE COLORES — TEMA CALLAI (Lavender Indigo) ============ */
    :root {
        --bg-primary: #f6f6f8;      /* lienzo general */
        --bg-secondary: #ffffff;
        --bg-sidebar: #ffffff;      /* sidebar blanco estilo CallAI */
        --bg-card: #ffffff;
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
        --cab-nivel1-top: 30px;
        --cab-nivel2-top: 52px;   /* legacy: ya no hay nivel 2 en la banda */
        --cab-offset-contenido: 58px;

        /* ==================================================================
           BARRA INFERIOR DE NAVEGACIÓN EN MÓVIL (bottom nav)
           Debe coincidir con NAV_MOVIL_ALTO en navegacion.py (60px).
           ================================================================== */
        --nav-movil-alto: 60px;
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

    /* =================================================================== */
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

    /* =================================================================== */
    /* SECCIONES DE COMPRAS — RAIL VERTICAL (borde derecho, apilado)         */
    /* Variante 2: cabecera neutra "Compras / Gráficos" arriba + secciones    */
    /* agrupadas por categoría (Dimensión, Precios, Cantidad, Más). Cada     */
    /* ítem es un st.button con dot a la izquierda; el activo se marca con   */
    /* type="primary" (accent-light + barra izquierda accent). El contenedor  */
    /* solo existe en Compras: este CSS no afecta otros reportes.            */
    /* =================================================================== */
    .st-key-compras_tabs_row {
        position: fixed !important;
        /* Rail arranca a la altura de la tarjeta (por debajo de la topbar de
           Streamlit + la fila de chips/fecha), no desde el borde superior. */
        top: 60px !important;
        right: 15px !important;            /* despega del scrollbar del navegador */
        bottom: 0 !important;
        height: calc(100vh - 60px) !important;
        z-index: 900 !important;
        width: 84px !important;
        overflow-x: hidden !important;
        overflow-y: auto !important;
        margin: 0 !important;
        padding: 8px 0 16px 0 !important;
        background: var(--bg-card, #ffffff) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;    /* mismas esquinas que la tarjeta */
        box-shadow: none !important;       /* sin sombra: integrada al borde */
        scrollbar-width: none !important;
    }
    .st-key-compras_tabs_row::-webkit-scrollbar { display: none !important; }

    /* Reserva el ancho de la franja solo en Compras (no toca otros reportes):
       el :has() detecta el rail dentro del contenedor principal. */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row),
    .block-container:has(.st-key-compras_tabs_row) {
        padding-right: 153px !important;   /* rail 116 + 22px de aire + 15px offset del rail */
    }

    /* Cabecera del rail — icono + "Compras / Gráficos" */
    .st-key-compras_tabs_row .rail-header {
        background: var(--surface-1, #f6f7f9) !important;
        border-bottom: 0.5px solid var(--border) !important;
        padding: 10px 10px 8px !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        margin: 0 0 6px 0 !important;
    }
    .st-key-compras_tabs_row .rail-header .rail-icon {
        display: inline-flex !important;
        align-items: center !important;
        color: var(--accent, #6c5ce7) !important;
        flex-shrink: 0 !important;
    }
    .st-key-compras_tabs_row .rail-header .rail-icon svg {
        display: block !important;
    }
    .st-key-compras_tabs_row .rail-header .rail-texts {
        display: flex !important;
        flex-direction: column !important;
        gap: 1px !important;
        min-width: 0 !important;
    }
    .st-key-compras_tabs_row .rail-header .rail-title {
        font-size: 10.5px !important;
        font-weight: 500 !important;
        color: var(--text-primary, #18181d) !important;
        line-height: 1.2 !important;
    }
    .st-key-compras_tabs_row .rail-header .rail-sub {
        font-size: 9px !important;
        color: var(--text-muted, #a2a2ad) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        line-height: 1.2 !important;
    }

    /* Badge de categoría + separador entre secciones */
    .st-key-compras_tabs_row .rail-cat-badge {
        font-size: 8.5px !important;
        font-weight: 600 !important;
        color: var(--text-muted, #a2a2ad) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        padding: 4px 10px 1px !important;
    }
    .st-key-compras_tabs_row .rail-sep {
        height: 0.5px !important;
        background: var(--border, #e6e6ea) !important;
        margin: 2px 8px !important;
    }

    /* Subir las TARJETAS (no los chips fijos): recupera el hueco que dejó la
       antigua barra horizontal de pestañas y la franja blanca. Se aplica
       solo a los contenedores que sí viven en el flujo del dashboard de
       Compras. Ahora que la franja es transparente el gap se ve mas, por
       eso -100 en vez de -60. */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-compras_prov_drill_wrap,
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-ajuste_graf_card_izq_compras,
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-ajuste_graf_card_der_compras {
        margin-top: -68px !important;
    }

/* En Compras la franja blanca superior YA NO EXISTE — el ::before se
       vuelve transparente (sin fondo, sin border-bottom, sin shadow) para
       que los chips Familia/Subfamilia y la fecha floten directo sobre el
       fondo gris del canvas. Scopeado con :has, no afecta a otros reportes. */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row) .st-key-fila_ajuste_top::before {
        background: transparent !important;
        border-bottom: none !important;
        box-shadow: none !important;
        height: 34px !important;
        right: 84px !important;    /* que la franja no invada el rail derecho */
    }
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row) .st-key-fila_ajuste_top {
        padding-top: 2px !important;
    }

    .st-key-graf_tipo_chips {
        margin: 0 !important;
        overflow: visible !important;
        border-bottom: none !important;
        padding: 0 !important;
    }
    /* NUCLEAR: cero margin/padding/gap en TODO descendiente del rail excepto
       el <button> y el texto. Especificidad reforzada duplicando la clase del
       contenedor (.st-key-graf_tipo_chips.st-key-graf_tipo_chips) para ganarle
       a cualquier regla base de Streamlit con clase única + !important. */
    .st-key-graf_tipo_chips.st-key-graf_tipo_chips
        *:not(button):not(p):not(span):not(.rail-cat-badge):not(.rail-sep) {
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
        row-gap: 0 !important;
        min-height: 0 !important;
        min-width: 0 !important;
    }
    /* El wrapper directo del rail también: sin gap entre hijos (categorías +
       botones). Streamlit lo aplica al stVerticalBlock, pero el div raíz
       .st-key-graf_tipo_chips también puede tener display:flex con gap. */
    .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        row-gap: 0 !important;
    }
    /* Cada ítem del rail: botón estilo lista, sin borde ni fondo por defecto.
       Un dot a la izquierda (::before) precede al texto. border-left:3px
       transparent reservado en base = el texto no se corre cuando pasa a
       activo (activo reemplaza el transparent por accent). */
    .st-key-graf_tipo_chips [data-testid="stButton"] > button,
    .st-key-graf_tipo_chips .stButton > button {
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
        width: 100% !important;
        min-height: 0 !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
        padding: 1px 10px 1px 7px !important;   /* 7 + border 3 = 10 alineado */
        gap: 0 !important;
        color: var(--text-secondary, #71717a) !important;
        font-weight: 400 !important;
        box-shadow: none !important;
        position: relative !important;
        transition: background 0.12s !important;
    }
    /* Viñeta eliminada — la barra izquierda de acento (border-left activo)
       ya marca el ítem seleccionado; el dot sumaba ruido sin agregar info. */
    .st-key-graf_tipo_chips [data-testid="stButton"] > button::before,
    .st-key-graf_tipo_chips .stButton > button::before {
        display: none !important;
    }
    /* Wrappers del label — NO expandirse (si crecen con flex:1 el texto queda
       flotando al centro del hueco sobrante). Streamlit mete un <div emotion>
       intermedio entre el <button> y el stMarkdownContainer, con display:flex
       y justify-content:center por default → hay que aplanar TODOS los div
       descendientes del botón. */
    .st-key-graf_tipo_chips [data-testid="stButton"] > button > div,
    .st-key-graf_tipo_chips .stButton > button > div,
    .st-key-graf_tipo_chips [data-testid="stButton"] > button [data-testid="stMarkdownContainer"],
    .st-key-graf_tipo_chips .stButton > button [data-testid="stMarkdownContainer"] {
        display: block !important;             /* deja al <p> tomar su ancho */
        flex: 0 1 auto !important;
        width: auto !important;
        max-width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] > button p,
    .st-key-graf_tipo_chips .stButton > button p {
        margin: 0 !important;
        padding: 0 !important;
        display: block !important;
        font-size: 11px !important;
        line-height: 1.15 !important;
        white-space: normal !important;
        text-align: left !important;
        font-weight: inherit !important;
        color: inherit !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] > button:hover,
    .st-key-graf_tipo_chips .stButton > button:hover {
        background: var(--accent-tint, #f0edfe) !important;   /* hover suave */
        color: var(--accent-deep, #4938b8) !important;
    }
    /* Activo: kind="primary" del st.button */
    .st-key-graf_tipo_chips [data-testid="stButton"] > button[kind="primary"],
    .st-key-graf_tipo_chips .stButton > button[kind="primary"] {
        background: var(--accent-light, #e7e3fb) !important;   /* activo saturado */
        color: var(--accent-deep, #4938b8) !important;
        font-weight: 500 !important;
        border-left-color: var(--accent, #6c5ce7) !important;  /* pinta el reservado */
    }

    /* =================================================================== */
    /* BOTÓN FILTROS (popover) — a juego, grande y con contorno índigo      */
    /* =================================================================== */
    [data-testid="stPopover"] button {
        min-width: 180px !important;
        padding: 14px 26px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 999px !important;
        transition: all .15s ease !important;
    }
    [data-testid="stPopover"] button:hover {
        border-color: var(--accent-hover) !important;
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }

    /* =================================================================== */
    /* FILA SUPERIOR DE AJUSTE DE INVENTARIO                                */
    /* =================================================================== */
    /* FRANJA BLANCA SUPERIOR — banda de borde a borde tras título + fecha. */
    .st-key-fila_ajuste_top {
        position: sticky !important;
        top: var(--cab-nivel1-top) !important;
        z-index: 20 !important;
        margin-bottom: 0 !important;
        padding-top: 7px !important;
        padding-bottom: 0 !important;
        margin-top: calc(-1 * var(--cab-offset-contenido)) !important;
    }
    .st-key-fila_ajuste_top::before {
        content: "" !important;
        position: fixed !important;
        top: 0 !important;
        bottom: auto !important;
        left: 90px !important;      /* comienza inmediatamente tras el rail */
        right: 0 !important;
        height: var(--cab-altura) !important;
        background: #ffffff !important;
        border-bottom: 1px solid var(--border) !important;
        box-shadow: 0 2px 4px rgba(16, 16, 20, 0.04) !important;
        z-index: 0 !important;
    }
    .st-key-fila_ajuste_top > * {
        position: relative !important;
        z-index: 1 !important;
    }
    .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 8px !important;
    }
    .st-key-fila_ajuste_top [data-testid="stColumn"],
    .st-key-fila_ajuste_top [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
    }

    /* Pestañas Gráficos/Tabla DENTRO de la franja (col_titulo): anular el
       margin-top de 6px que las bajaba cuando vivían en su banda propia. */
    .st-key-fila_ajuste_top [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] {
        margin: 0 !important;
    }
    .st-key-fila_ajuste_top [class*="st-key-vistatabs_"] {
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Pestañas Gráficos/Tabla — ya NO fijas en la franja: ahora fluyen justo
       encima del canvas (se renderizan en app.py antes de _render_contenido).
       Quedan pegadas al borde superior del primer contenedor del contenido. */
    .st-key-ajuste_tabs_top {
        position: relative !important;
        z-index: 5 !important;
        margin: 2px 0 6px 0 !important;
        padding: 0 !important;
    }

    /* ================================================================== */
    /* CHIPS DE FILTRO EN LA FRANJA BLANCA — Área / Familia / Ajuste /     */
    /* Ajuste valor.  Nivel 2, a la derecha del selector de vista.         */
    /* ================================================================== */
    /* Filtros Familia / Subfamilia en el NIVEL 1: pegados a la IZQUIERDA,
       alineados con el borde izquierdo de la TARJETA (no del rail). El
       block-container tiene padding-left ~60px encima del rail (90px),
       de ahi los ~154px. La fecha se ancla al lado derecho (más abajo). */
    .st-key-chips_ajuste_tabla {
        position: fixed !important;
        top: 6px !important;
        left: 154px !important;
        right: auto !important;
        width: auto !important;
        max-width: calc(100vw - 154px - 380px) !important;   /* deja aire para la fecha derecha */
        z-index: 23 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] {
        gap: 8px !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stColumn"],
    .st-key-chips_ajuste_tabla [data-testid="column"] {
        width: auto !important;
        flex: 0 1 auto !important;
        min-width: 0 !important;
    }
    /* Opción A: cuadrado lavanda con icono + badge morado. Ancho automático
       para que el badge del count quepa sin recortar; esquinas 4px. */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        min-width: 0 !important;
        width: auto !important;
        min-height: 28px !important;
        height: 28px !important;
        padding: 3px 10px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        background: var(--accent-tint) !important;
        border: 1px solid var(--border-lavender) !important;
        border-radius: 4px !important;
        color: var(--accent-deep) !important;
        overflow: hidden !important;
        gap: 6px !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button p {
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
        font-size: 15px !important;
    }
    /* Badge del count (Streamlit :violet-badge[N] dentro del label) */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button [data-testid="stBadge"] {
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 3px !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        padding: 1px 6px !important;
        line-height: 1.4 !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button:hover {
        background: var(--accent-light) !important;
        border-color: var(--accent) !important;
    }
    /* Estado ACTIVO (hay un filtro aplicado): fondo lleno en vez del tono
       tenue de reposo, para diferenciarlo a simple vista. */
    .st-key-chips_ajuste_tabla [class*="st-key-chipwrap_"][class*="_on"] [data-testid="stPopover"] button {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #ffffff !important;
    }
    .st-key-chips_ajuste_tabla [class*="st-key-chipwrap_"][class*="_on"] [data-testid="stPopover"] button:hover {
        background: var(--accent-deep) !important;
        border-color: var(--accent-deep) !important;
    }
    /* Pantallas chicas: si no caben junto a las pestañas, bajan a su línea */
    @media (max-width: 900px) {
        .st-key-chips_ajuste_tabla {
            position: static !important;
            width: auto !important;
            max-width: none !important;
            margin: 6px 0 0 0 !important;
        }
    }

    /* Título del reporte, fijo en el nivel 1 de la franja */
    .titulo-ajuste-reporte {
        position: fixed !important;
        top: 6px !important;
        left: calc(90px + 1rem) !important;
        z-index: 22 !important;
        margin: 0 !important;
        color: var(--text-primary) !important;
        font-family: 'Corbel', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        text-transform: uppercase !important;
        font-size: 27px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        letter-spacing: 0.01em !important;
        transform: none !important;
    }

    /* Chip pill del título del reporte */
    .chip-titulo-reporte {
        display: inline-flex;
        align-items: center;
        background: var(--accent-tint);
        color: var(--accent-deep);
        border-radius: 999px;
        padding: 8px 18px;
        font-size: 15px;
        font-weight: 500;
        line-height: 1;
        white-space: nowrap;
        letter-spacing: 0.01em;
    }

    /* =================================================================== */
    /* FECHA EN EL HEADER — texto del rango a la DERECHA de la franja,      */
    /* alineado con el borde derecho de la tarjeta (padding-right: 138px    */
    /* en Compras). Es el TRIGGER de un popover: atajos + calendario.       */
    /* =================================================================== */
.st-key-fecha_ajuste_pill {
    position: fixed !important;
    top: 8px !important;
    left: auto !important;
    right: 138px !important;        /* alineada con el borde derecho de la tarjeta */
    width: fit-content !important;
    z-index: 23 !important;
    margin: 0 !important;
}

    /* Trigger: anula la regla GLOBAL de pill (BOTÓN FILTROS, arriba) SOLO
       aquí → texto sobre tinte violeta claro (gradient que sube desde
       la base) + barra sólida 2px acento pegada al borde INFERIOR de
       la franja. Se lee como "pestaña activa" muy sutil. min-height =
       --cab-altura - top(8px) + box-sizing border-box → el border
       aterriza justo en el borde de la franja en todos los reportes. */
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
        box-sizing: border-box !important;
        min-width: 0 !important;
        padding: 0 18px !important;
        border: none !important;
        border-bottom: 3px solid #534AB7 !important;
        border-radius: 6px 6px 0 0 !important;
        background: linear-gradient(to top,
            #C7C0F5 0%, rgba(199,192,245,0) 78%) !important;
        box-shadow: none !important;
        color: #1B1745 !important;
        font-weight: 800 !important;
        font-size: 22px !important;
        letter-spacing: -0.01em !important;
        line-height: 1.15 !important;
        white-space: nowrap !important;
        min-height: calc(var(--cab-altura) - 8px) !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    /* Icono material (calendar_month) del popover: color acento + tamano */
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
        color: #534AB7 !important;
        font-size: 22px !important;
    }
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button:hover {
        border: none !important;
        border-bottom: 2px solid #534AB7 !important;
        background: linear-gradient(to top,
            #DED9FA 0%, rgba(222,217,250,0) 70%) !important;
        color: var(--accent-deep) !important;
    }
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button[aria-expanded="true"] {
        border-bottom: 2px solid #26215C !important;
        background: linear-gradient(to top,
            #DED9FA 0%, rgba(222,217,250,0) 75%) !important;
    }
    /* En Compras la franja es MAS BAJA (34px, no 50px) — el ::before
       la sobreescribe directamente pero --cab-altura sigue en 50.
       Aquí re-alineamos el underline al borde real de esa franja. */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
        min-height: 26px !important;   /* 34px franja - 8px top */
    }

    /* ================================================================== */
    /* COMPRAS: fecha a la IZQUIERDA (alineada con la tarjeta) y chips     */
    /* Familia/Subfamilia al CENTRO con fondo blanco.                      */
    /* Scopeado con :has(.st-key-compras_tabs_row) → no afecta otros       */
    /* reportes.                                                           */
    /* ================================================================== */
    /* Solo cambia la POSICIÓN: fecha alineada con el borde izquierdo de la
       tarjeta (block-container padding-left ~16px sobre el rail 90px + aire). */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-fecha_ajuste_pill {
        left: 175px !important;
        right: auto !important;
    }

    /* Chips Familia/Subfamilia CENTRADOS en el ancho de la tarjeta
       (154px izquierda ↔ 131px derecha por el rail 116 + 15). */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-chips_ajuste_tabla {
        left: calc((154px + (100vw - 131px)) / 2) !important;
        right: auto !important;
        transform: translateX(-50%) !important;
        max-width: calc(100vw - 154px - 131px - 380px) !important;
    }
    /* Fondo blanco (en vez del tinte lavanda) + más espacio interno a la
       derecha (chip más ancho y con aire tras el texto/badge). */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        background: #ffffff !important;
        min-width: 230px !important;   /* ≈ ancho del widget de fecha */
        padding-right: 22px !important;
        justify-content: flex-start !important;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-chips_ajuste_tabla [data-testid="stPopover"] button:hover {
        background: var(--accent-tint, #EEEDFE) !important;
    }

    /* Panel del popover: se renderiza en un portal (fuera del contenedor),
       así que lo scopeamos por el contenedor keyed interno con :has(). */
    [data-testid="stPopoverBody"]:has(.st-key-fecha_panel) {
        min-width: 380px !important;
    }
    /* Botones de atajo: compactos, alineados a la izquierda. */
    .st-key-fecha_panel [data-testid="stColumn"]:first-child button {
        min-width: 0 !important;
        padding: 6px 10px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }

    .ultima-actualizacion {
        margin: 0 !important;
        color: var(--text-muted) !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        text-align: right !important;
        white-space: nowrap !important;
    }

    /* =================================================================== */
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
    div[data-baseweb="popover"]:has(div[data-baseweb="calendar"]) [data-baseweb="select"] {
        display: none !important;
    }
    div[data-baseweb="popover"]:has(div[data-baseweb="calendar"]) div[data-baseweb="calendar"] + div {
        display: none !important;
    }

    /* =================================================================== */
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
    /* POSICIÓN DEL TOAST (st.toast) — junto al rail (RAIL_ANCHO=90px+10)   */
    /* =================================================================== */
    div[data-testid="stToastContainer"] {
        left: 100px !important;
        right: auto !important;
        bottom: 16px !important;
        top: auto !important;
    }

    /* =================================================================== */
    /* AVISO DE REFRESCO EN CURSO — flotante junto al botón del rail        */
    /* =================================================================== */
    .st-key-aviso_refresco {
        position: fixed !important;
        left: 100px !important;
        bottom: 16px !important;
        max-width: 320px !important;
        z-index: 999997 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
        border-radius: 8px !important;
    }

    /* =================================================================== */
    /* CARDS DE GRÁFICOS — contenedor blanco con bordes redondeados         */
    /* =================================================================== */
    .chart-card {
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.25rem 1.5rem 0.75rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
        position: relative;
        padding-bottom: 2.5rem;  /* espacio para el pie */
    }

    .chart-card-title {
        position: absolute;
        left: 0; right: 0; bottom: 0;
        font-size: 11px;
        font-weight: 600;
        color: var(--accent);
        background: var(--accent-tint, #EEEDFE);
        border-top: 1px solid var(--accent, #7F77DD);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 8px 1.5rem;
        margin: 0;
        line-height: 1;
        border-bottom-left-radius: inherit;
        border-bottom-right-radius: inherit;
    }

    /* Cabecera de _card(titulo_arriba=True): título arriba + divisoria.
       Solo se emite en las tarjetas de Compras que lo piden; el resto
       de dashboards conserva su título al pie (.chart-card-pie). */
    .chart-card-hdr {
        margin: 0 0 0.55rem;
        padding: 0.1rem 0 0.5rem;
        border-bottom: 1px solid var(--border);
        font-size: 13px;
        font-weight: 600;
        line-height: 1.35;
        color: var(--accent-deep);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .streamlit-expanderContent .chart-card {
        border: none !important;
        box-shadow: none !important;
        padding: 0.25rem 0 0 !important;
    }

    /* ============================================================
       CARDS EXTERIORES DE LOS DASHBOARDS DE GRÁFICOS

       Convención en Python: `st.container(border=True, key="ajuste_graf_
       card_...")` para envolver cada dashboard. Aquí en CSS reemplazamos
       ese borde por un look plano (fondo blanco + radius grande + sombra
       tenue) y anulamos también los bordes internos que _card() añade a
       los paneles hijos (para no doble-marcar).

       Efecto neto: el usuario ve UNA card grande sin líneas internas,
       no una malla de cajas anidadas.

       EXCEPCIÓN (dashboard de Compras / drill Proveedor):
       Ahí SÍ queremos ver cada bloque bordeado (gráfico, paneles A/B,
       tabla) — el usuario lo pidió así (2026-07-25). Por eso el
       container externo de ese caso se declara SIN `border=True` en
       graficos/compras.py, y cada bloque interno lleva su propio
       `border=True`. Así las reglas de abajo no le aplican (no hay
       nada que anular).

       Al modificar: pensar primero si el cambio afecta a los cards
       "clásicos" (Familia/Evolución) o a los del drill Proveedor.
       ============================================================ */
    div[class*="st-key-ajuste_graf_card_"] {
        background: var(--surface-2, #ffffff) !important;
        border: none !important;                    /* look plano: sin borde de Streamlit */
        border-radius: 20px !important;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);  /* sombra tenue reemplaza al borde */
    }
    /* Anula el borde que Streamlit pinta en el hijo directo del container
       (stVerticalBlockBorderWrapper) cuando border=True está activo. */
    div[class*="st-key-ajuste_graf_card_"] > div {
        border: none !important;
    }
    /* Cards internos (Paneles A/B via `_card()`): dejar transparentes para
       que no se doble-marquen dentro del contenedor externo. */
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"],
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"] > div,
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"]
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* Chips de tipo de gráfico dentro de la tarjeta (también st.pills →
       stButtonGroup). Conservan forma de píldora redonda para
       diferenciarse del selector de vista. */
    div[class*="st-key-ajuste_graf_card_izq_"] [data-testid="stButtonGroup"] {
        gap: 8px !important;
        flex-wrap: wrap !important;
        margin-bottom: 8px !important;
    }
    div[class*="st-key-ajuste_graf_card_izq_"] [data-testid="stButtonGroup"] button {
        min-height: 36px !important;
        padding: 8px 14px !important;
        font-size: 13px !important;
        border-radius: 999px !important;
    }

    /* =================================================================== */
    /* TARJETAS DEL DRILL DE PROVEEDOR (Compras)                             */
    /*                                                                       */
    /* Convención independiente de `ajuste_graf_card_*`: el drill de         */
    /* Proveedor NO usa un wrapper blanco único, sino 3 bloques separados    */
    /* por el gris del app. Cada bloque declara su key con prefijo           */
    /* `compras_prov_card_` y esta regla les pinta el fondo blanco propio.   */
    /*                                                                       */
    /* No tocar sin revisar `_compras_proveedor_drill` en graficos/compras.py*/
    /* =================================================================== */
    div[class*="st-key-compras_prov_card_"] {
        background: var(--surface-2, #ffffff) !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
    }
    /* Anula el borde interno que Streamlit pinta cuando border=True. */
    div[class*="st-key-compras_prov_card_"] > div {
        border: none !important;
    }
    /* Cards internos (Paneles A/B via `_card()`): transparentes para
       no doble-marcar dentro de la tarjeta blanca del bloque. */
    div[class*="st-key-compras_prov_card_"] [class*="st-key-chartcard_"],
    div[class*="st-key-compras_prov_card_"] [class*="st-key-chartcard_"] > div,
    div[class*="st-key-compras_prov_card_"] [class*="st-key-chartcard_"]
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* =================================================================== */
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

    /* =================================================================== */
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

    </style>
    """


def inject_css():
    """Inyecta el CSS cacheado en la app."""
    st.markdown(get_css(), unsafe_allow_html=True)
