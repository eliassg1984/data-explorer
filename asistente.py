"""asistente.py — Asistente flotante de IA (Groq / Llama 3.1) con búsqueda web.

Diseño:
- st.popover como burbuja flotante en la esquina inferior derecha
  (fijado con CSS position:fixed en el container ai_float_wrap).
- @st.fragment: al enviar un mensaje, solo re-ejecuta el asistente
  — la tabla, gráficos y filtros del reporte NO se recargan.
- Cliente Groq (Llama 3.1 8B) para sintetizar respuestas. La key vive en
  st.secrets['GROQ_API_KEY'] y NUNCA sale al navegador.
- Búsqueda web vía Tavily (opcional). Requiere st.secrets['TAVILY_API_KEY'].
  Se activa: (a) automáticamente si detectamos palabras clave de "precio /
  actual / esta semana / mercado / cotización / ..."; o (b) manualmente con
  el toggle 🌐. Los resultados frescos se adjuntan al prompt de Llama para
  que la respuesta cite datos reales. Sin Tavily key, el asistente sigue
  funcionando (solo pierde búsqueda web).
- Contexto del reporte: se adjunta un resumen del df filtrado del reporte
  activo (totales, top 5 por familia, etc.) como bloque separado.
"""

from __future__ import annotations

import streamlit as st

from tema import ACENTO, ACENTO_FUERTE, BLANCO

_MODELO = "llama-3.1-8b-instant"
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
    "puede estar desactualizado) y cita las fuentes al final como "
    "[Fuente: título del sitio]."
)


# ─── Estado ────────────────────────────────────────────────────────────────
def _init_estado():
    if "ai_historial" not in st.session_state:
        st.session_state["ai_historial"] = []
    st.session_state.setdefault("ai_web_toggle", False)


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


# ─── Llamada a Groq (API estilo OpenAI) ────────────────────────────────────
def _llamar_groq(pregunta: str, contexto: str, contexto_web: str = "") -> str:
    try:
        from groq import Groq
    except ImportError:
        return ("⚠️ Falta la librería `groq`. Añade `groq` a requirements.txt "
                "y redeploya.")

    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        return ("⚠️ Falta la clave `GROQ_API_KEY` en Secrets de Streamlit "
                "Cloud. Consíguela gratis en https://console.groq.com")

    cliente = Groq(api_key=api_key)

    # Construir mensajes: system + historial + nuevo prompt con contextos.
    # Orden: contexto del reporte (interno) → contexto web (externo) → pregunta.
    bloques = []
    if contexto:
        bloques.append(f"[Contexto del reporte activo]\n{contexto}")
    if contexto_web:
        bloques.append(contexto_web)
    bloques.append(pregunta)
    prompt_con_ctx = "\n\n".join(bloques)

    historial = st.session_state["ai_historial"][-_MAX_HISTORIAL:]
    mensajes = [{"role": "system", "content": _SYSTEM_PROMPT}]
    mensajes.extend(historial)
    mensajes.append({"role": "user", "content": prompt_con_ctx})

    try:
        resp = cliente.chat.completions.create(
            model=_MODELO,
            messages=mensajes,
            max_tokens=_MAX_TOKENS_RESP,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error al contactar Groq: {str(e)[:250]}"


# ─── CSS del wrapper flotante ──────────────────────────────────────────────
def _inject_css():
    if st.session_state.get("_ai_css_inyectado"):
        return
    st.session_state["_ai_css_inyectado"] = True
    st.markdown(f"""
    <style>
    /* Wrapper que aloja el popover del asistente — fijado abajo-derecha. */
    .st-key-ai_float_wrap {{
        position: fixed !important;
        bottom: 24px !important;
        right: 24px !important;
        z-index: 999990 !important;
        width: auto !important;
    }}
    /* El trigger del popover: burbuja circular con el color de marca. */
    .st-key-ai_float_wrap [data-testid="stPopover"] > div > button {{
        border-radius: 999px !important;
        min-height: 52px !important;
        padding: 0 18px !important;
        background: {ACENTO} !important;
        color: {BLANCO} !important;
        border: none !important;
        box-shadow: 0 4px 16px rgba(108,92,231,0.35) !important;
        font-weight: 600 !important;
    }}
    .st-key-ai_float_wrap [data-testid="stPopover"] > div > button:hover {{
        background: {ACENTO_FUERTE} !important;
        transform: translateY(-1px);
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
        with st.popover("💬 Asistente", use_container_width=False):
            st.markdown(
                f'<div class="ai-header">'
                f'<div class="ai-title">Asistente IA · {reporte or "General"}</div>'
                f'<div class="ai-sub">Precios · Compras · Inventario</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            historial = st.session_state.get("ai_historial", [])

            with st.container():
                st.markdown('<div class="ai-msg-scroll">', unsafe_allow_html=True)
                if not historial:
                    st.caption("Hola 👋 Pregunta sobre precios de mercado, "
                               "proveedores o pide un análisis del reporte "
                               "que tienes abierto.")
                for msg in historial:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                st.markdown('</div>', unsafe_allow_html=True)

            # Toggle de búsqueda web — visible siempre para que el usuario
            # sepa que la opción existe. Persiste en session_state.
            st.toggle(
                "🌐 Buscar en web (precios, mercado)",
                key="ai_web_toggle",
                help=("Si está activo, cada pregunta consulta Tavily para "
                      "traer datos frescos. Si está apagado, buscamos solo "
                      "cuando detectamos palabras como 'precio', 'actual', "
                      "'esta semana', etc."),
            )

            # Chips de sugerencias (solo si aún no hay historial)
            if not historial:
                c1, c2 = st.columns(2)
                sugerencias = [
                    ("🐔 Precio pollo hoy",
                     "¿Cuál es el precio de mercado del pollo en Lima hoy?"),
                    ("📊 Analizar reporte",
                     "Analiza el reporte activo y dame los puntos más importantes."),
                    ("💡 Bajar foodcost",
                     "Dame 3 ideas concretas para reducir foodcost."),
                    ("🥩 Cotización res",
                     "¿Cuánto cuesta el kilo de carne de res esta semana en Lima?"),
                ]
                prefill = None
                for i, (etq, prompt) in enumerate(sugerencias):
                    col = c1 if i % 2 == 0 else c2
                    if col.button(etq, key=f"ai_sug_{i}",
                                  use_container_width=True):
                        prefill = prompt
                if prefill:
                    _procesar_mensaje(prefill, contexto)
                    st.rerun(scope="fragment")

            pregunta = st.chat_input("Escribe tu pregunta…",
                                     key="ai_chat_input")
            if pregunta:
                _procesar_mensaje(pregunta, contexto)
                st.rerun(scope="fragment")


def _procesar_mensaje(pregunta: str, contexto: str):
    st.session_state["ai_historial"].append(
        {"role": "user", "content": pregunta})

    # ¿Buscamos en web? Toggle manual O heurística automática.
    forzar_web = st.session_state.get("ai_web_toggle", False)
    debe_buscar = forzar_web or _necesita_busqueda_web(pregunta)
    contexto_web = ""
    web_status = ""  # nota informativa para agregar arriba de la respuesta

    if debe_buscar:
        with st.spinner("🌐 Buscando en la web…"):
            web = _buscar_web(pregunta)
        if web is None:
            # No hay TAVILY_API_KEY o falló la petición. Seguimos sin web y
            # avisamos discretamente al usuario (una sola vez por sesión).
            if not st.session_state.get("_ai_aviso_tavily_mostrado"):
                st.session_state["_ai_aviso_tavily_mostrado"] = True
                web_status = ("_(Búsqueda web no disponible: configura "
                              "`TAVILY_API_KEY` en Secrets para activarla.)_\n\n")
        else:
            contexto_web = _formatear_contexto_web(web)

    with st.spinner("Pensando…"):
        respuesta = _llamar_groq(pregunta, contexto, contexto_web)

    st.session_state["ai_historial"].append(
        {"role": "assistant", "content": web_status + respuesta})


# ─── API pública ───────────────────────────────────────────────────────────
def inject_asistente(reporte_activo: str = "", df_contexto=None) -> None:
    """Inyecta el asistente flotante. Llama al final de app.py."""
    _init_estado()
    _inject_css()
    contexto = _resumir_df(reporte_activo, df_contexto)
    _asistente_fragment(reporte_activo, contexto)
