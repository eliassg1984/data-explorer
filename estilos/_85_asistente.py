"""estilos._85_asistente - Asistente IA: el ícono-trigger de la franja
superior y el PANEL de chat que abre (rediseñado 2026-08-09).

Por qué el CSS vive ACÁ y no en asistente.py
--------------------------------------------
Vivía inline en `asistente.py::_inject_css()`, con un guard
`if st.session_state["_ai_css_inyectado"]: return` para "inyectar una sola
vez". Eso era un BUG: Streamlit reconstruye el árbol de elementos con lo que
el script emite en CADA rerun, así que un `st.markdown` que no se vuelve a
llamar no queda de la vez anterior — se BORRA. El ícono perdía todo su estilo
al cambiar de reporte (ver arquitectura.md regla #59).

Moviéndolo acá el bug se vuelve estructuralmente imposible: `inject_css()`
(estilos/__init__.py) se llama sin condición en cada rerun desde app.py:74.
De paso los colores dejan de venir de f-strings de `tema.py` y salen de las
variables `:root` de _00_base.py, como pide CLAUDE.md § Colores.

Geometría del trigger
---------------------
Ícono de 30px fijo arriba a la derecha, en la misma banda que la fecha y los
chips, para los 8 reportes y los 3 anchos. `top` = (alto_franja - 30) / 2:
8px con la franja de 46px (desktop >=901px), 10px con la de 50px (default:
tablet 769-900px y móvil <=768px). Ver _40_ajuste_franja.py::before.

El panel se renderiza en un PORTAL (`stPopoverBody`), fuera del contenedor
del trigger — por eso se scopea con `:has(.st-key-ai_panel)`, el container
keyed que `asistente.py` dibuja adentro. Mismo truco que `fecha_panel` en
_50_fecha.py.
"""

CSS = """    /* =================================================================== */
    /* ASISTENTE IA — TRIGGER (ícono en la franja superior)                  */
    /* =================================================================== */
    .st-key-ai_float_wrap {
        position: fixed !important;
        top: 10px !important;
        right: 15px !important;
        z-index: 999990 !important;
        width: auto !important;
    }
    @media (min-width: 901px) {
        .st-key-ai_float_wrap { top: 8px !important; }
    }
    /* Selector DESCENDIENTE (` button`, no `> div > button`): con hijo directo
       se rompía al agregar `help=` al popover, que anida el botón un nivel
       más hondo. Ver arquitectura.md regla #59.
       `min-width: 0` es obligatorio: hay una regla global
       [data-testid="stPopover"] button { min-width: 180px !important } para
       los popovers de filtros que le gana al width. Ver regla #30. */
    .st-key-ai_float_wrap [data-testid="stPopover"] button {
        min-width: 0 !important;
        width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(108, 92, 231, 0.35) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.12s, background 0.12s !important;
    }
    .st-key-ai_float_wrap [data-testid="stPopover"] button p {
        margin: 0 !important;
        font-size: 15px !important;
        line-height: 1 !important;
    }
    .st-key-ai_float_wrap [data-testid="stPopover"] button:hover {
        background: var(--accent-hover) !important;
        transform: scale(1.08) !important;
    }
    /* La flecha expand_more no aporta en un botón-ícono. */
    .st-key-ai_float_wrap [data-testid="stPopoverButton"] [aria-hidden="true"] {
        display: none !important;
    }

    /* =================================================================== */
    /* ASISTENTE IA — PANEL DE CHAT (portal; scopeado por .st-key-ai_panel) */
    /* =================================================================== */
    /* Ancho: el panel viejo iba 360-420px y el chat quedaba apretado (las
       tablas que ahora devuelve el modelo necesitan aire). 460px en
       escritorio, y en móvil se limita al viewport para no crear scroll
       lateral. */
    [data-testid="stPopoverBody"]:has(.st-key-ai_panel) {
        min-width: 460px !important;
        max-width: 460px !important;
        padding: 0 !important;
    }
    @media (max-width: 560px) {
        [data-testid="stPopoverBody"]:has(.st-key-ai_panel) {
            min-width: min(460px, 92vw) !important;
            max-width: 92vw !important;
        }
    }

    /* Cabecera: reemplaza el bloque violeta SÓLIDO del diseño viejo, que
       pesaba demasiado para lo que es (un título) y comía el alto útil del
       panel. Ahora es una banda de tinte lavanda con borde inferior — mismo
       lenguaje que la franja superior de la app. */
    .ai-hdr {
        display: flex;
        align-items: center;
        gap: 9px;
        padding: 11px 14px;
        margin: 0 0 2px 0;
        background: var(--accent-tint);
        border-bottom: 1px solid var(--border-lavender);
    }
    .ai-hdr-dot {
        flex: 0 0 26px;
        width: 26px; height: 26px;
        border-radius: 50%;
        background: var(--accent);
        color: #ffffff;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
    }
    .ai-hdr-txt { min-width: 0; line-height: 1.25; }
    .ai-hdr-ttl {
        font-size: 13px;
        font-weight: 600;
        color: var(--accent-deep);
    }
    .ai-hdr-sub {
        font-size: 10.5px;
        font-weight: 500;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Zona de mensajes con scroll propio. El alto es fijo para que el
       chat_input no se vaya bajando de la pantalla a medida que crece la
       conversación (el popover no scrollea solo). */
    .st-key-ai_scroll {
        max-height: 46vh !important;
        overflow-y: auto !important;
        padding: 2px 12px 0 12px !important;
    }
    .st-key-ai_scroll::-webkit-scrollbar { width: 6px; }
    .st-key-ai_scroll::-webkit-scrollbar-thumb {
        background: var(--scroll-thumb);
        border-radius: 3px;
    }
    /* Burbujas más compactas que el default de st.chat_message: el panel es
       angosto y el avatar + padding de Streamlit se comían el ancho del
       texto. */
    .st-key-ai_scroll [data-testid="stChatMessage"] {
        padding: 6px 2px !important;
        background: transparent !important;
        gap: 8px !important;
    }
    .st-key-ai_scroll [data-testid="stChatMessage"] p,
    .st-key-ai_scroll [data-testid="stChatMessage"] li {
        font-size: 13px !important;
        line-height: 1.5 !important;
    }
    /* Tablas markdown (el modelo ahora responde rankings en tabla): que
       quepan y scrolleen solas en vez de desbordar el panel. */
    .st-key-ai_scroll [data-testid="stChatMessage"] table {
        display: block !important;
        overflow-x: auto !important;
        width: 100% !important;
        font-size: 11.5px !important;
        border-collapse: collapse !important;
    }
    .st-key-ai_scroll [data-testid="stChatMessage"] th,
    .st-key-ai_scroll [data-testid="stChatMessage"] td {
        padding: 3px 7px !important;
        border: 1px solid var(--border) !important;
        white-space: nowrap !important;
    }
    .st-key-ai_scroll [data-testid="stChatMessage"] th {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }

    /* Chips de sugerencia (solo cuando no hay conversación). Son el arranque
       del asistente: sin ellos el usuario no descubre que ahora puede
       preguntar por SUS datos y sigue preguntando cosas genéricas.
       Scopeado a la key PROPIA de los botones, no al contenedor, para no
       pisar widgets que se agreguen después (CLAUDE.md § grep estilos/). */
    div[class*="st-key-ai_sug_"] button {
        min-width: 0 !important;
        width: 100% !important;
        min-height: 0 !important;
        padding: 7px 10px !important;
        border: 1px solid var(--border-lavender) !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        box-shadow: none !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }
    div[class*="st-key-ai_sug_"] button p {
        font-size: 11.5px !important;
        font-weight: 500 !important;
        line-height: 1.3 !important;
        color: var(--accent-deep) !important;
        white-space: normal !important;
        text-align: left !important;
        margin: 0 !important;
    }
    div[class*="st-key-ai_sug_"] button:hover {
        background: var(--accent-tint) !important;
        border-color: var(--accent) !important;
    }

    /* "Ver consulta SQL": el expander que muestra lo que el modelo ejecutó.
       Es la pieza de CONFIANZA del rediseño — el usuario puede auditar de
       dónde salió cada cifra. Va discreto para no competir con la respuesta. */
    .st-key-ai_scroll [data-testid="stExpander"] {
        border: none !important;
        background: transparent !important;
        margin: 2px 0 0 0 !important;
    }
    .st-key-ai_scroll [data-testid="stExpander"] summary {
        padding: 2px 0 !important;
        font-size: 10.5px !important;
        color: var(--text-muted) !important;
    }
    .st-key-ai_scroll [data-testid="stExpander"] summary:hover {
        color: var(--accent) !important;
    }
    .st-key-ai_scroll [data-testid="stExpander"] code {
        font-size: 10.5px !important;
        line-height: 1.4 !important;
    }

    /* Pie: input de chat + acción de limpiar. */
    .st-key-ai_pie {
        padding: 4px 12px 10px 12px !important;
        border-top: 1px solid var(--line-soft) !important;
    }
    .st-key-ai_pie [data-testid="stChatInput"] textarea {
        font-size: 13px !important;
    }
    /* "Limpiar": texto chico, no un botón con peso — es una acción
       secundaria. Acotado a su key propia. */
    .st-key-ai_reset button {
        min-width: 0 !important;
        min-height: 0 !important;
        padding: 1px 6px !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    .st-key-ai_reset button p {
        font-size: 10.5px !important;
        font-weight: 500 !important;
        color: var(--text-muted) !important;
        margin: 0 !important;
    }
    .st-key-ai_reset button:hover p { color: var(--danger) !important; }

    /* Aviso de "estoy consultando tus datos": el spinner nativo de Streamlit
       dentro del panel angosto se veía suelto. */
    .st-key-ai_scroll [data-testid="stSpinner"] p {
        font-size: 11.5px !important;
        color: var(--text-secondary) !important;
    }
"""
