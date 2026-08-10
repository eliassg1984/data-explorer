"""asistente.py — Asistente IA del reporte activo (Groq) con acceso REAL a los datos.

Arquitectura
------------
- **Trigger:** botón-ÍCONO de 30px (💬) fijo arriba a la derecha de la franja
  superior, igual en los 8 reportes y los 3 anchos. Su CSS vive en
  `estilos/_85_asistente.py` (NO acá — ver regla #59: un `st.markdown` de
  estilos con guard "una sola vez" desaparece en el rerun siguiente).
- **@st.fragment:** al preguntar solo se re-ejecuta el asistente; la tabla,
  los gráficos y los filtros del reporte NO se recargan.
- **Herramientas (tool calling):** el modelo NO recibe un resumen y adivina —
  consulta. `asistente_datos.py` expone dos herramientas:
    · `consultar_datos(sql)` → DuckDB sobre el DataFrame en memoria.
    · `buscar_web(query)`    → Tavily, con la query que el modelo reescribe.
  El bucle de rondas vive en `_resolver_turno()`.
- **Contexto:** el df que ve el modelo es el POST-CHIPS que publica cada
  dashboard vía `graficos.base.publicar_contexto_ia` (ver
  `_df_efectivo()`), no el `df_f` de app.py — que está filtrado por fecha
  pero no por Área/Familia.

Por qué tool calling y no un resumen más grande (medido, 2026-08-09)
-------------------------------------------------------------------
El asistente veía 7 líneas del df: totales y el top 5 de UNA categórica, sin
los nombres de las columnas. No podía responder "qué producto tuvo más
merma" — no por tonto, por ciego. Con las herramientas responde cualquier
cosa que se pueda expresar en SQL, sobre 10k-230k filas, en ~3s y sin costo
de R2 (DuckDB consulta el df de pandas en memoria).

Se probaron 4 modelos de Groq sobre datos reales (ver arquitectura.md #61):
los 4 soportan tool calling, los 4 citaron bien las columnas con espacios y
ninguno falló un SQL. Los dos riesgos reales, que este módulo mitiga en el
system prompt:
  · **Semántica:** 3 de 4 respondieron "los 5 productos con más merma" con un
    ORDER BY sobre filas CRUDAS (= los 5 movimientos, no los 5 productos).
    De ahí la REGLA 2 del prompt.
  · **Aritmética en prosa:** `llama-3.3-70b` listó 5 cifras que suman −28.907
    y afirmó que el total era −30.070. De ahí la REGLA 3.

Sobre el modelo: `gpt-oss-120b` se queda porque es gratis, responde en ~3s y
tool calling le funciona. Los 4 modelos fallaban en LO MISMO, así que el
modelo no era el cuello de botella — el prompt y las herramientas sí.
"""

from __future__ import annotations

import json

import streamlit as st

from asistente_datos import (
    HERRAMIENTAS,
    ejecutar_sql,
    esquema_para_prompt,
    resumen_para_prompt,
)

_MODELO = "openai/gpt-oss-120b"   # ver docstring: elegido tras medir 4 candidatos
_MAX_HISTORIAL = 12          # pares user/assistant a conservar en el prompt
_MAX_TOKENS_RESP = 2000      # era 800: cortaba las respuestas con tabla
# 8 y no 5: con 5 una pregunta MIXTA ("mi merma de lomo, ¿cuánto es a precio
# de mercado hoy?") se quedaba sin rondas justo antes de responder — gastaba
# 3 consultas ubicando el producto, 1 búsqueda web y ya no le quedaba turno
# para el cálculo final (verificado 2026-08-09). Cada ronda extra solo cuesta
# si el modelo la usa, así que el tope alto no encarece las preguntas simples,
# que siguen resolviéndose en 1.
_MAX_RONDAS = 8

# Búsqueda web (Tavily)
_TAVILY_URL = "https://api.tavily.com/search"
_TAVILY_TIMEOUT = 12
_TAVILY_MAX_RESULTS = 5

_SYSTEM_PROMPT = """Eres el analista de datos de un restaurante en Perú. Trabajas \
DENTRO de su app de reportes y tienes acceso a los datos que el usuario está \
viendo en pantalla ahora mismo.

HOY ES {hoy} (año {anio}). Tu conocimiento interno está desactualizado: al \
buscar en la web usa SIEMPRE el año {anio}, nunca uno anterior, y no des por \
buenos precios "actuales" que recuerdes de tu entrenamiento.

Tienes una tabla DuckDB llamada `datos` con EXACTAMENTE las filas visibles en \
pantalla (rango de fechas y filtros ya aplicados). Su esquema:

{esquema}

Estado actual de la pantalla:
{resumen}

REGLAS QUE NO SE NEGOCIAN
1. Los nombres de columna llevan ESPACIOS: enciérralos siempre en comillas \
dobles en el SQL ("AJUSTE VALORIZADO"). Sin comillas la consulta falla.
2. Cuando pregunten por "productos", "áreas", "familias" o "proveedores", \
AGREGA con GROUP BY + SUM antes de ordenar. Un producto aparece en muchas \
filas: un ORDER BY sobre filas crudas devuelve los MOVIMIENTOS más grandes, \
no los productos — y eso responde otra pregunta.
3. NUNCA hagas aritmética por tu cuenta. Si hace falta un total, un promedio \
o una diferencia, pídeselo al SQL (SUM, AVG). Sumar cifras en prosa produce \
errores que el usuario no puede detectar.
4. Toda cifra que menciones tiene que venir de una consulta de este turno. Si \
no consultaste, no inventes: consulta.
5. Si la pregunta es sobre precios de mercado, proveedores o cualquier cosa \
que NO esté en `datos`, usa buscar_web. Para lo que sí está en `datos`, NO \
busques en la web.

CÓMO INTERPRETAR ESTE NEGOCIO
· Moneda: soles peruanos (S/).
· AJUSTE / AJUSTE VALORIZADO negativo = MERMA (falta stock frente a lo \
declarado). Positivo = sobrante.
· Lo accionable suele ser la merma concentrada: pocos productos o un área \
que se repite.

CÓMO RESPONDER
· En español, directo y corto. Cifras en formato S/ 1,234.56.
· CONSERVA EL SIGNO tal como sale del SQL. Una merma es NEGATIVA y se escribe \
S/ -4,864.29, nunca S/ 4,864.29 "porque ya dije que es merma". Quitarle el \
signo a una pérdida cambia el sentido del número.
· Rankings en tabla markdown; lo demás en viñetas.
· Cierra con UNA línea de interpretación accionable, no un resumen de lo que \
ya dijiste.
· No pegues URLs ni listas de fuentes: los enlaces se muestran aparte."""


# ─── Estado ────────────────────────────────────────────────────────────────
def _init_estado():
    st.session_state.setdefault("ai_historial", [])
    st.session_state.setdefault("ai_pending", None)


# ─── Contexto de datos ─────────────────────────────────────────────────────
def _df_efectivo(reporte: str, df_fallback):
    """El df que el modelo debe ver: post-chips si el dashboard lo publicó.

    `graficos.base.publicar_contexto_ia` lo deja en session_state junto al
    nombre del reporte. Se valida ese nombre: si no coincide con el reporte
    activo, el contexto es de una vista anterior (p.ej. el usuario cambió a
    un reporte cuyo dashboard no publica) y se cae al df_f de app.py. Sin ese
    chequeo un contexto viejo sobrevive y responde con datos del reporte
    equivocado, en silencio.
    """
    ctx = st.session_state.get("_ia_contexto") or {}
    if ctx.get("reporte") == reporte and ctx.get("df") is not None:
        return ctx["df"], ctx.get("filtros") or {}
    return df_fallback, {}


# ─── Búsqueda web (Tavily) ─────────────────────────────────────────────────
def _buscar_web(query: str) -> dict:
    """Busca en Tavily. Nunca lanza: devuelve un dict que el modelo pueda leer."""
    try:
        api_key = st.secrets["TAVILY_API_KEY"]
    except (KeyError, FileNotFoundError):
        return {"ok": False,
                "error": ("Búsqueda web no configurada (falta TAVILY_API_KEY). "
                          "Responde con lo que sepas y acláralo.")}
    import requests
    try:
        r = requests.post(_TAVILY_URL, timeout=_TAVILY_TIMEOUT, json={
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",   # era "basic": los precios locales
                                          # aparecen en páginas que basic no abre
            "max_results": _TAVILY_MAX_RESULTS,
            "include_answer": True,
        })
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"ok": False, "error": f"La búsqueda web falló: {type(e).__name__}"}

    resultados = [
        {"titulo": (x.get("title") or "")[:120],
         "contenido": (x.get("content") or "")[:500],
         "url": x.get("url", "")}
        for x in data.get("results", []) if x.get("url")
    ]
    return {"ok": True, "resumen": data.get("answer") or "",
            "resultados": resultados}


# ─── Bucle de herramientas ─────────────────────────────────────────────────
def _cliente():
    from groq import Groq
    return Groq(api_key=st.secrets["GROQ_API_KEY"])


def _despachar(nombre: str, argumentos: dict, df) -> tuple[dict, dict | None]:
    """Ejecuta una herramienta. Devuelve (resultado_para_el_modelo, rastro_ui).

    El `rastro_ui` es lo que se le muestra al usuario (el SQL ejecutado, las
    fuentes web). Va aparte del resultado porque el modelo no necesita saber
    cómo se pinta, y la UI no necesita el JSON entero de filas.
    """
    if nombre == "consultar_datos":
        sql = argumentos.get("sql", "")
        res = ejecutar_sql(df, sql)
        rastro = {"tipo": "sql", "sql": res.get("sql") or sql,
                  "ok": res.get("ok", False),
                  "filas": res.get("filas_devueltas"),
                  "error": res.get("error")}
        return res, rastro

    if nombre == "buscar_web":
        query = argumentos.get("query", "")
        res = _buscar_web(query)
        rastro = {"tipo": "web", "query": query, "ok": res.get("ok", False),
                  "fuentes": [(r["titulo"], r["url"])
                              for r in res.get("resultados", [])]}
        return res, rastro

    return {"ok": False, "error": f"Herramienta desconocida: {nombre}"}, None


def _hoy_peru():
    """Fecha de hoy en Lima. El modelo NO la sabe: sin esto escribía queries
    web con el año de su entrenamiento ("precio lomo fino Lima 2024" en pleno
    2026) y devolvía precios viejos como si fueran de hoy."""
    import datetime
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo("America/Lima")).date()


def _mensajes_base(pregunta: str, df, reporte: str, filtros: dict) -> list[dict]:
    hoy = _hoy_peru()
    sistema = _SYSTEM_PROMPT.format(
        hoy=hoy.strftime("%d/%m/%Y"), anio=hoy.year,
        esquema=esquema_para_prompt(df),
        resumen=resumen_para_prompt(df, reporte, filtros),
    )
    msgs = [{"role": "system", "content": sistema}]
    # Solo role/content del historial: se descartan claves propias de la UI
    # (rastro, fuentes) que la API rechazaría.
    for m in st.session_state["ai_historial"][-_MAX_HISTORIAL:]:
        msgs.append({"role": m["role"], "content": m["content"]})
    msgs.append({"role": "user", "content": pregunta})
    return msgs


def _resolver_turno(pregunta: str, df, reporte: str, filtros: dict,
                    on_paso=None) -> dict:
    """Corre el turno completo: rondas de herramientas + respuesta final.

    Devuelve {"texto": str, "rastros": [...]}. No lanza nunca: cualquier
    fallo vuelve como texto legible — el asistente es accesorio y no puede
    tumbar el reporte (mismo criterio que el try/except de app.py).

    `on_paso(rastro)` se llama en vivo por cada herramienta ejecutada, para
    que la UI muestre "consultando…" mientras pasa, en vez de congelarse.
    """
    try:
        cli = _cliente()
    except (KeyError, FileNotFoundError):
        return {"texto": ("⚠️ Falta la clave `GROQ_API_KEY` en los Secrets. "
                          "Consíguela gratis en https://console.groq.com"),
                "rastros": []}
    except ImportError:
        return {"texto": ("⚠️ Falta la librería `groq` en el servidor "
                          "(`requirements.txt`)."), "rastros": []}

    msgs = _mensajes_base(pregunta, df, reporte, filtros)
    rastros = []

    for _ in range(_MAX_RONDAS):
        try:
            r = cli.chat.completions.create(
                model=_MODELO, messages=msgs, tools=HERRAMIENTAS,
                tool_choice="auto", temperature=0.2,
                max_tokens=_MAX_TOKENS_RESP,
            )
        except Exception as e:
            return {"texto": f"⚠️ Error al contactar Groq: {str(e)[:240]}",
                    "rastros": rastros}

        msg = r.choices[0].message
        llamadas = msg.tool_calls or []

        if not llamadas:
            return {"texto": (msg.content or "").strip(), "rastros": rastros}

        # Re-inyectar el turno del asistente TAL CUAL (con sus tool_calls):
        # si se omite, la API rechaza los mensajes 'tool' que vienen después
        # por no tener a qué llamada responder.
        msgs.append({
            "role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name,
                                         "arguments": tc.function.arguments}}
                           for tc in llamadas],
        })

        for tc in llamadas:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            resultado, rastro = _despachar(tc.function.name, args, df)
            if rastro:
                rastros.append(rastro)
                if on_paso:
                    on_paso(rastro)
            msgs.append({"role": "tool", "tool_call_id": tc.id,
                         "content": json.dumps(resultado, ensure_ascii=False,
                                               default=str)[:6000]})

    return {"texto": ("No pude cerrar la respuesta: la consulta dio demasiadas "
                      "vueltas. Prueba con una pregunta más concreta."),
            "rastros": rastros}


# ─── Piezas de UI ──────────────────────────────────────────────────────────
def _sugerencias(reporte: str) -> list[str]:
    """Preguntas de arranque, por reporte.

    No son decorativas: sin ellas el usuario no descubre que el asistente
    ahora puede responder sobre SUS datos y sigue preguntando cosas genéricas
    (que es justo lo que hacía cuando solo veía un resumen de 7 líneas).
    """
    por_reporte = {
        "Ajuste de Inventario": [
            "¿Qué 5 productos concentran más merma valorizada?",
            "¿Qué área tiene la peor merma y cuánto pesa del total?",
            "¿Hay productos con sobrante que compensen la merma?",
        ],
        "Compras": [
            "¿A qué proveedor le compro más y cuánto?",
            "¿Qué familia se llevó más gasto este período?",
            "¿Algún producto subió de precio contra el promedio?",
        ],
        "Inventario Valorizado": [
            "¿Qué área concentra más valor inmovilizado?",
            "¿Cuáles son los 10 productos de mayor valorizado?",
            "¿Hay stock en cero con valorizado distinto de cero?",
        ],
        "Ventas": [
            "¿Cuáles son mis 10 platos más vendidos?",
            "¿Qué canal deja más ingreso?",
            "¿Qué grupo cayó respecto al resto?",
        ],
        "Salidas": [
            "¿Qué sub almacén saca más valorizado?",
            "¿Cuáles son los 10 productos con más salidas?",
            "¿Qué tipo de descargo pesa más?",
        ],
    }
    return por_reporte.get(reporte, [
        "Resume lo que estoy viendo en 3 puntos.",
        "¿Cuál es el total y cómo se reparte?",
        "¿Qué es lo más raro de estos datos?",
    ])


def _pintar_rastros(rastros: list[dict], clave: str) -> None:
    """Muestra QUÉ ejecutó el modelo. Es la pieza de confianza del panel:
    el usuario puede auditar de dónde salió cada cifra."""
    sqls = [r for r in rastros if r.get("tipo") == "sql"]
    webs = [r for r in rastros if r.get("tipo") == "web"]

    if sqls:
        etiqueta = ("🔍 Ver consulta" if len(sqls) == 1
                    else f"🔍 Ver {len(sqls)} consultas")
        with st.expander(etiqueta):
            for r in sqls:
                if r.get("ok"):
                    st.caption(f"{r.get('filas', 0)} filas")
                else:
                    st.caption(f"⚠️ {r.get('error', 'falló')}")
                st.code(r.get("sql", ""), language="sql")

    fuentes, vistos = [], set()
    for r in webs:
        for titulo, url in r.get("fuentes") or []:
            if url and url not in vistos:
                vistos.add(url)
                fuentes.append(f"[{(titulo or url)[:34]}]({url})")
    if fuentes:
        st.caption("🔗 " + " · ".join(fuentes[:4]))


def _pintar_mensaje(msg: dict, idx: int) -> None:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("rastros"):
            _pintar_rastros(msg["rastros"], f"hist_{idx}")


def _encolar(pregunta: str) -> None:
    """Callback de los chips de sugerencia: deja la pregunta pendiente."""
    st.session_state["ai_pending"] = pregunta


# ─── Fragment del asistente ────────────────────────────────────────────────
@st.fragment
def _asistente_fragment(reporte: str, df, filtros: dict):
    with st.container(key="ai_float_wrap"):
        with st.popover("💬", use_container_width=False):
            # Container keyed: el popover se renderiza en un portal, así que
            # el CSS del panel se scopea con :has(.st-key-ai_panel).
            with st.container(key="ai_panel"):
                n_filas = 0 if df is None else len(df)
                st.markdown(
                    '<div class="ai-hdr">'
                    '<div class="ai-hdr-dot">✦</div>'
                    '<div class="ai-hdr-txt">'
                    '<div class="ai-hdr-ttl">Analista de datos</div>'
                    f'<div class="ai-hdr-sub">{reporte or "General"} · '
                    f'{n_filas:,} filas</div>'
                    '</div></div>',
                    unsafe_allow_html=True,
                )

                historial = st.session_state.get("ai_historial", [])
                pendiente = st.session_state.get("ai_pending")

                with st.container(key="ai_scroll"):
                    if not historial and not pendiente:
                        st.caption(
                            "Pregúntame sobre los datos que tienes en "
                            "pantalla — consulto la tabla de verdad, no "
                            "adivino. También busco precios de mercado."
                        )
                        for i, sug in enumerate(_sugerencias(reporte)):
                            st.button(sug, key=f"ai_sug_{i}",
                                      use_container_width=True,
                                      on_click=_encolar, args=(sug,))

                    for i, msg in enumerate(historial):
                        _pintar_mensaje(msg, i)

                    if pendiente:
                        with st.chat_message("user"):
                            st.markdown(pendiente)
                        with st.chat_message("assistant"):
                            hueco = st.empty()
                            with hueco:
                                st.caption("Consultando tus datos…")

                            def _aviso(rastro):
                                # Feedback en vivo: sin esto el panel se ve
                                # congelado durante las rondas de SQL.
                                texto = ("Consultando tus datos…"
                                         if rastro.get("tipo") == "sql"
                                         else "Buscando en la web…")
                                hueco.caption(texto)

                            out = _resolver_turno(pendiente, df, reporte,
                                                  filtros, on_paso=_aviso)
                            hueco.empty()
                            st.markdown(out["texto"])
                            if out["rastros"]:
                                _pintar_rastros(out["rastros"], "vivo")

                        st.session_state["ai_historial"].append(
                            {"role": "user", "content": pendiente})
                        st.session_state["ai_historial"].append(
                            {"role": "assistant", "content": out["texto"],
                             "rastros": out["rastros"]})
                        st.session_state["ai_pending"] = None
                        # Rerun OBLIGATORIO, no cosmético: este render dibujó
                        # los chips de sugerencia (historial estaba vacío al
                        # entrar) y Streamlit NO los borra cuando el render
                        # siguiente produce menos elementos en ese slot —
                        # quedaban 2 de 3 chips colgando bajo la respuesta
                        # (verificado en el preview). Al re-ejecutar, el
                        # fragment se dibuja desde el historial ya persistido:
                        # sin chips y sin pendiente. No hay riesgo de bucle
                        # (ai_pending ya es None) ni llamada extra al modelo.
                        # El diseño viejo evitaba este rerun porque usaba
                        # st.write_stream y el rerun se habría comido la
                        # respuesta transmitida; hoy la respuesta se pinta de
                        # una con st.markdown, así que el rerun es inocuo.
                        st.rerun(scope="fragment")

                with st.container(key="ai_pie"):
                    pregunta = st.chat_input("Pregunta sobre estos datos…",
                                             key="ai_chat_input")
                    if historial:
                        if st.button("Limpiar conversación", key="ai_reset"):
                            st.session_state["ai_historial"] = []
                            st.session_state["ai_pending"] = None
                            st.rerun(scope="fragment")

                if pregunta and not pendiente:
                    st.session_state["ai_pending"] = pregunta
                    st.rerun(scope="fragment")


# ─── API pública ───────────────────────────────────────────────────────────
def inject_asistente(reporte_activo: str = "", df_contexto=None) -> None:
    """Inyecta el asistente. Llamar al final de app.py (después del contenido:
    los dashboards publican su df post-chips durante su propio render)."""
    _init_estado()
    df, filtros = _df_efectivo(reporte_activo, df_contexto)
    _asistente_fragment(reporte_activo, df, filtros)
