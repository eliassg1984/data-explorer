"""asistente.py — Asistente flotante de IA (Groq / GPT-OSS 120B) con búsqueda web.

Diseño:
- st.popover flotante (position:fixed sobre el container ai_float_wrap):
  botón-ÍCONO (sin texto, solo 💬) fijo en la esquina superior derecha de
  la franja superior — misma banda que la fecha/chips, para TODOS los
  reportes y anchos. Hasta el 2026-08-09 era un tab de texto pegado al
  borde derecho (o la cabecera del rail de Compras/Ajuste si había rail) —
  a pedido, se simplificó a un único ícono en la franja, sin la rama por
  breakpoint/rail que tenía el diseño anterior. Ver arquitectura.md
  regla #59.
- @st.fragment: al enviar un mensaje, solo re-ejecuta el asistente
  — la tabla, gráficos y filtros del reporte NO se recargan.
- Cliente Groq (GPT-OSS 120B) para sintetizar respuestas. La key vive en
  st.secrets['GROQ_API_KEY'] y NUNCA sale al navegador. Nota: el modelo
  anterior (llama-3.1-8b-instant) fue deprecado por Groq el 2026-06-17.
- Búsqueda web vía Tavily (opcional). Requiere st.secrets['TAVILY_API_KEY'].
  Activa POR DEFECTO (toggle 🌐 encendido): cada pregunta trae datos frescos.
  El usuario puede apagarla para preguntas solo del reporte. Con el toggle
  apagado seguimos buscando si detectamos palabras clave ("precio", "actual",
  "esta semana", "mercado"…). Los enlaces a las fuentes se muestran como
  chips clicables bajo la respuesta. Sin Tavily key, el asistente sigue
  funcionando (solo pierde búsqueda web).
- Respuestas en STREAMING (token a token) con st.write_stream: la respuesta
  aparece viva, no de golpe.
- Contexto del reporte: se adjunta un resumen del df filtrado del reporte
  activo (totales, top 5 por familia, etc.) como bloque separado.
"""

from __future__ import annotations

import streamlit as st

from tema import ACENTO, ACENTO_FUERTE, BLANCO

_MODELO = "openai/gpt-oss-120b"   # reemplaza a llama-3.1-8b-instant (deprecado 2026-06-17)
_MAX_HISTORIAL = 20           # pares user/assistant a conservar
_MAX_TOKENS_RESP = 800

# Búsqueda web (Tavily)
_TAVILY_URL = "https://api.tavily.com/search"
_TAVILY_TIMEOUT = 12          # segundos — Tavily es rápido, con margen
_TAVILY_MAX_RESULTS = 5

# Heurística: cuándo la pregunta huele a "necesito datos frescos de la web".
# Match sobre texto ya normalizado (sin acentos, minúsculas). Palabras
# comunes pero específicas — mejor pecar de conservador (los falsos positivos
# gastan cuota de Tavily; el toggle manual cubre los falsos negativos).
_KEYWORDS_WEB = (
    "precio", "precios", "cuanto cuesta", "cuanto sale", "cotizacion",
    "vale", "tarifa",
    "hoy", "ahora", "actual", "esta semana", "este mes", "reciente",
    "ultima", "ultimo", "ultimas", "ultimos",
    "mercado", "tendencia", "inflacion",
    "proveedor", "proveedores",
)

_SYSTEM_PROMPT = (
    "Eres un asistente para restaurantes en Perú especializado en compras, "
    "precios de mercado, inventario y foodcost. Contexto: la app muestra "
    "reportes de Ajuste de Inventario, Compras, Inventario Valorizado, Receta "
    "Base, Receta Venta, Ventas, Salidas y Requerimientos. Precios en soles "
    "peruanos (S/). Estilo: conciso, directo, en español, con viñetas cuando "
    "listes. Si estimas precios, aclara que son aproximados y sugiere "
    "verificar con proveedor. Si el usuario adjunta 'Contexto del reporte', "
    "úsalo para responder con datos reales. Si el usuario adjunta 'Resultados "
    "de la web', prioriza ESA información sobre tu conocimiento previo (que "
    "puede estar desactualizado). No incluyas URLs ni una lista de fuentes "
    "al final: los enlaces a las fuentes se muestran aparte automáticamente."
)


# ─── Estado ────────────────────────────────────────────────────────────────
def _init_estado():
    if "ai_historial" not in st.session_state:
        st.session_state["ai_historial"] = []
    # Búsqueda web ENCENDIDA por defecto (el usuario puede apagarla).
    st.session_state.setdefault("ai_web_toggle", True)
    # Pregunta a la espera de respuesta (para el render en streaming).
    st.session_state.setdefault("ai_pending", None)


# ─── Búsqueda web (Tavily) ─────────────────────────────────────────────────
def _normalizar(s: str) -> str:
    """Minúsculas + sin acentos, para comparar keywords."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                   if not unicodedata.combining(c))


def _necesita_busqueda_web(pregunta: str) -> bool:
    """Heurística: ¿la pregunta pide datos frescos que Llama no tiene?"""
    txt = _normalizar(pregunta)
    return any(kw in txt for kw in _KEYWORDS_WEB)


def _buscar_web(query: str) -> dict | None:
    """Llama a Tavily y devuelve dict {'answer': str, 'sources': [(title, url)]}
    o None si no hay key o la búsqueda falla. La app sigue funcionando sin web."""
    try:
        api_key = st.secrets["TAVILY_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None

    import requests
    # Contextualizar la búsqueda a Perú y sesgar hacia precios locales
    query_local = f"{query} Perú Lima" if "peru" not in _normalizar(query) else query
    try:
        r = requests.post(_TAVILY_URL, timeout=_TAVILY_TIMEOUT, json={
            "api_key": api_key,
            "query": query_local,
            "search_depth": "basic",
            "max_results": _TAVILY_MAX_RESULTS,
            "include_answer": True,   # Tavily sintetiza una respuesta corta
        })
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None

    sources = [(x.get("title") or x.get("url", "")[:60], x.get("url", ""))
               for x in data.get("results", []) if x.get("url")]
    return {"answer": data.get("answer") or "", "sources": sources,
            "raw": data.get("results", [])}


def _formatear_contexto_web(web: dict) -> str:
    """Convierte el resultado de Tavily en un bloque de texto para el prompt."""
    if not web:
        return ""
    partes = ["[Resultados de la web — datos frescos, priorizar sobre memoria]"]
    if web.get("answer"):
        partes.append(f"Resumen: {web['answer']}")
    for i, r in enumerate(web.get("raw", [])[:_TAVILY_MAX_RESULTS], 1):
        titulo = r.get("title", "")[:80]
        contenido = (r.get("content", "") or "")[:400]
        url = r.get("url", "")
        partes.append(f"\n[{i}] {titulo}\n{contenido}\nFuente: {url}")
    return "\n".join(partes)


# ─── Resumen del df para dar contexto ──────────────────────────────────────
def _resumir_df(reporte: str, df) -> str:
    if df is None or getattr(df, "empty", True):
        return f"Reporte activo: {reporte or 'ninguno'}. Sin datos filtrados."
    try:
        lineas = [
            f"Reporte activo: {reporte or '—'}",
            f"Filas: {len(df):,} · Columnas: {df.shape[1]}",
        ]
        cols_num = df.select_dtypes("number").columns.tolist()

        for kw_list, etiqueta in (
            (("valorizado", "importe", "total", "monto"), "Valor total"),
            (("stock",), "Stock total"),
        ):
            for c in cols_num:
                if any(k in c.lower() for k in kw_list):
                    try:
                        lineas.append(f"{etiqueta} ({c}): S/ {df[c].sum():,.2f}")
                    except Exception:
                        pass
                    break

        for c in cols_num:
            if "precio" in c.lower():
                try:
                    lineas.append(f"Precio promedio ({c}): S/ {df[c].mean():,.2f}")
                except Exception:
                    pass
                break

        for cat in ("Nombre Familia", "FAMILIA", "Nombre Area", "AREA",
                    "Nombre Producto", "NOMBRE PRODUCTO"):
            if cat in df.columns and cols_num:
                col_v = next(
                    (c for c in cols_num
                     if any(k in c.lower()
                            for k in ("valorizado", "importe", "total", "monto"))),
                    None,
                )
                if col_v:
                    top = (df.groupby(cat)[col_v].sum()
                             .sort_values(ascending=False).head(5))
                    lineas.append(f"\nTop 5 por {cat}:")
                    for nombre, val in top.items():
                        lineas.append(f"  · {nombre}: S/ {val:,.2f}")
                break

        return "\n".join(lineas)
    except Exception:
        return f"Reporte activo: {reporte or '—'} (resumen no disponible)."


# ─── Llamada a Groq (API estilo OpenAI) — streaming ────────────────────────
def _construir_mensajes(pregunta: str, contexto: str,
                        contexto_web: str = "") -> list[dict]:
    """Arma la lista de mensajes: system + historial + prompt con contextos.
    Orden del prompt: contexto del reporte (interno) → web (externo) → pregunta.
    """
    bloques = []
    if contexto:
        bloques.append(f"[Contexto del reporte activo]\n{contexto}")
    if contexto_web:
        bloques.append(contexto_web)
    bloques.append(pregunta)
    prompt_con_ctx = "\n\n".join(bloques)

    mensajes = [{"role": "system", "content": _SYSTEM_PROMPT}]
    # Historial previo (la pregunta actual aún NO está en el log). Nos quedamos
    # solo con role/content — descartamos claves extra como 'sources'/'aviso'.
    for m in st.session_state["ai_historial"][-_MAX_HISTORIAL:]:
        mensajes.append({"role": m["role"], "content": m["content"]})
    mensajes.append({"role": "user", "content": prompt_con_ctx})
    return mensajes


def _stream_groq(pregunta: str, contexto: str, contexto_web: str = ""):
    """Generador: cede la respuesta de Groq token a token (para st.write_stream).
    Nunca lanza — ante cualquier fallo cede un mensaje de error legible."""
    try:
        from groq import Groq
    except ImportError:
        yield ("⚠️ Falta la librería `groq`. Añade `groq` a requirements.txt "
               "y redeploya.")
        return
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        yield ("⚠️ Falta la clave `GROQ_API_KEY` en Secrets de Streamlit "
               "Cloud. Consíguela gratis en https://console.groq.com")
        return

    mensajes = _construir_mensajes(pregunta, contexto, contexto_web)
    try:
        stream = Groq(api_key=api_key).chat.completions.create(
            model=_MODELO,
            messages=mensajes,
            max_tokens=_MAX_TOKENS_RESP,
            temperature=0.4,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        yield f"⚠️ Error al contactar Groq: {str(e)[:250]}"


def _render_fuentes(sources) -> None:
    """Pinta las fuentes web como enlaces clicables (dedup por URL, máx 4)."""
    vistos, links = set(), []
    for title, url in sources or []:
        if not url or url in vistos:
            continue
        vistos.add(url)
        etiqueta = (title or url)[:38]
        links.append(f"[{etiqueta}]({url})")
        if len(links) >= 4:
            break
    if links:
        st.caption("🔗 Fuentes: " + " · ".join(links))


# ─── CSS del wrapper flotante ──────────────────────────────────────────────
def _inject_css():
    # SIN guard de "solo una vez": Streamlit reconstruye el árbol de
    # elementos a partir de lo que el script emite EN CADA rerun — un
    # st.markdown que no se vuelve a llamar no "queda" de la vez anterior,
    # se BORRA. Con el guard `if _ai_css_inyectado: return` de acá, el
    # <style> con .st-key-ai_float_wrap se inyectaba en el primer render y
    # desaparecía en el siguiente rerun (cambiar de reporte, tocar un
    # filtro, cualquier interacción): el botón volvía al popover DEFAULT de
    # Streamlit (pill blanca 180px) en vez del ícono, siempre fuera de la
    # franja superior. Mismo patrón que ya usa sin guard estilos/__init__.py
    # ::inject_css() (llamado sin condición en cada rerun, app.py:74) — ver
    # arquitectura.md regla #59.
    st.markdown(f"""
    <style>
    /* Wrapper del asistente — ÍCONO fijo en la esquina superior derecha de
       la FRANJA SUPERIOR (misma banda que fecha/chips, ver
       _40_ajuste_franja.py y _50_fecha.py), para TODOS los reportes y
       anchos — ya no depende de si hay rail (:has(.st-key-compras_tabs_row))
       ni de breakpoints de rail. right:15px = mismo eje que el rail de
       Compras/Ajuste cuando lo hay (_20_compras_rail.py); en los reportes
       sin rail (R. Base, Requerimientos) el ícono flota igual, con el mismo
       margen. Nunca choca con el rail: el rail arranca en top:66px
       (.st-key-compras_tabs_row) y este ícono vive en la banda 0-46/50px de
       arriba. top:8/10px centra el ícono de 30px en la franja — la fórmula
       es (alto_franja - 30) / 2: 8px cuando la franja mide 46px (desktop,
       @media 901px de abajo), 10px cuando mide 50px (default, que cubre
       tablet 769-900px y móvil <=768px — ver _40_ajuste_franja.py::before).
       Ver arquitectura.md regla #59. */
    .st-key-ai_float_wrap {{
        position: fixed !important;
        top: 10px !important;
        right: 15px !important;
        z-index: 999990 !important;
        width: auto !important;
    }}
    @media (min-width: 901px) {{
        .st-key-ai_float_wrap {{
            top: 8px !important;
        }}
    }}
    /* Trigger: círculo de 30px, solo ícono (💬, sin texto "Asistente") —
       mismo alto que los chips/pill vecinos de la franja (28-30px). El
       min-width:0 es necesario: sin él gana la regla global
       [data-testid="stPopover"] button {{ min-width: 180px !important }}
       (pensada para los popovers de filtros) — este mismo elemento ya la
       pisó una vez reposicionado como cabecera del rail, ver arquitectura.md
       regla #30. Selector DESCENDIENTE (` button`, sin `> div >`): la
       versión anterior con hijo directo se rompió al agregar `help=` al
       popover (agrega un stTooltipIcon que anida el botón un nivel más
       hondo) — un descendiente cualquiera es más resistente a estos
       cambios de anidado, y acá adentro solo hay un botón posible. */
    .st-key-ai_float_wrap [data-testid="stPopover"] button {{
        min-width: 0 !important;
        width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        background: {ACENTO} !important;
        color: {BLANCO} !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(108,92,231,0.35) !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    .st-key-ai_float_wrap [data-testid="stPopover"] button p {{
        margin: 0 !important;
        font-size: 15px !important;
        line-height: 1 !important;
    }}
    .st-key-ai_float_wrap [data-testid="stPopover"] button:hover {{
        background: {ACENTO_FUERTE} !important;
        transform: scale(1.08);
    }}
    /* Ocultar la flecha expand_more — no aporta en un botón-ícono. */
    .st-key-ai_float_wrap [data-testid="stPopoverButton"] [aria-hidden="true"] {{
        display: none !important;
    }}
    /* Interior del popover: un poco más ancho para el chat. */
    div[data-testid="stPopoverBody"] {{
        min-width: 360px !important;
        max-width: 420px !important;
    }}
    /* Cabecera del panel del asistente */
    .ai-header {{
        margin: -8px -8px 8px -8px;
        padding: 10px 14px;
        background: {ACENTO};
        color: {BLANCO};
        border-radius: 8px 8px 0 0;
    }}
    .ai-header .ai-title {{ font-weight: 600; font-size: 14px; }}
    .ai-header .ai-sub   {{ font-size: 11px; opacity: 0.85; }}
    .ai-msg-scroll {{
        max-height: 340px;
        overflow-y: auto;
        padding-right: 4px;
    }}
    </style>
    """, unsafe_allow_html=True)


# ─── Fragment del asistente ────────────────────────────────────────────────
@st.fragment
def _asistente_fragment(reporte: str, contexto: str):
    with st.container(key="ai_float_wrap"):
        # Sin help=: agrega un stTooltipIcon/stTooltipHoverTarget que RENDERIZA
        # EL BOTÓN DOS VECES a distinta profundidad (verificado en vivo con
        # outerHTML) — con eso el selector de _inject_css() puede dejar de
        # matchear la copia visible y el botón vuelve al estilo DEFAULT (pill
        # blanca, 180px, chevron) en vez del círculo de 30px. El selector ya
        # es un descendiente (no `> div >`) para no depender de esto, pero
        # evitamos help= igual: no aporta nada aquí (el panel ya se explica
        # solo) y es una rama menos que romper. Ver arquitectura.md regla #59.
        with st.popover("💬", use_container_width=False):
            st.markdown(
                f'<div class="ai-header">'
                f'<div class="ai-title">Asistente IA · {reporte or "General"}</div>'
                f'<div class="ai-sub">Precios · Compras · Inventario</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            historial = st.session_state.get("ai_historial", [])
            pendiente = st.session_state.get("ai_pending")

            st.markdown('<div class="ai-msg-scroll">', unsafe_allow_html=True)
            if not historial and not pendiente:
                st.caption("Hola 👋 Pregúntame por precios de mercado, "
                           "proveedores o pídeme que analice el reporte que "
                           "tienes abierto. 🌐 La búsqueda web está activa.")

            # Historial ya resuelto.
            for msg in historial:
                with st.chat_message(msg["role"]):
                    if msg.get("aviso"):
                        st.caption("⚠️ " + msg["aviso"])
                    st.write(msg["content"])
                    if msg.get("sources"):
                        _render_fuentes(msg["sources"])

            # Turno pendiente: pinta la pregunta y transmite la respuesta EN VIVO.
            if pendiente:
                with st.chat_message("user"):
                    st.write(pendiente)
                with st.chat_message("assistant"):
                    contexto_web, sources, aviso = "", [], ""
                    # ¿Buscamos en web? Toggle manual O heurística automática.
                    forzar_web = st.session_state.get("ai_web_toggle", True)
                    if forzar_web or _necesita_busqueda_web(pendiente):
                        with st.spinner("🌐 Buscando en la web…"):
                            web = _buscar_web(pendiente)
                        if web is None:
                            # Sin TAVILY_API_KEY o falló: seguimos sin web y
                            # avisamos una sola vez por sesión.
                            if not st.session_state.get("_ai_aviso_tavily_mostrado"):
                                st.session_state["_ai_aviso_tavily_mostrado"] = True
                                aviso = ("Búsqueda web no disponible: configura "
                                         "`TAVILY_API_KEY` en Secrets para activarla.")
                        else:
                            contexto_web = _formatear_contexto_web(web)
                            sources = web.get("sources", [])
                    if aviso:
                        st.caption("⚠️ " + aviso)
                    respuesta = st.write_stream(
                        _stream_groq(pendiente, contexto, contexto_web))
                    if sources:
                        _render_fuentes(sources)

                # Persistimos el turno (con fuentes/aviso para el replay) y
                # limpiamos el pendiente. No hacemos rerun: lo ya pintado queda.
                st.session_state["ai_historial"].append(
                    {"role": "user", "content": pendiente})
                st.session_state["ai_historial"].append(
                    {"role": "assistant", "content": respuesta,
                     "sources": sources, "aviso": aviso})
                st.session_state["ai_pending"] = None
                historial = st.session_state["ai_historial"]
            st.markdown('</div>', unsafe_allow_html=True)

            # Controles: toggle de web (izq) + limpiar conversación (der).
            col_web, col_reset = st.columns([3, 2])
            with col_web:
                st.toggle(
                    "🌐 Buscar en web",
                    key="ai_web_toggle",
                    help=("Activa: cada pregunta consulta la web (Tavily) para "
                          "traer precios y datos frescos. Apágala para preguntas "
                          "solo del reporte y responder más rápido."),
                )
            with col_reset:
                if historial and st.button("🗑️ Limpiar", key="ai_reset",
                                           use_container_width=True):
                    st.session_state["ai_historial"] = []
                    st.session_state["ai_pending"] = None
                    st.rerun(scope="fragment")

            pregunta = st.chat_input("Escribe tu pregunta…", key="ai_chat_input")
            if pregunta and not pendiente:
                st.session_state["ai_pending"] = pregunta
                st.rerun(scope="fragment")


# ─── API pública ───────────────────────────────────────────────────────────
def inject_asistente(reporte_activo: str = "", df_contexto=None) -> None:
    """Inyecta el asistente flotante. Llama al final de app.py."""
    _init_estado()
    _inject_css()
    contexto = _resumir_df(reporte_activo, df_contexto)
    _asistente_fragment(reporte_activo, contexto)
