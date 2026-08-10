"""
estado_rango — DUEÑO ÚNICO del rango de fechas de la franja superior.

Por qué existe
--------------
El rango vive en `st.session_state` y lo consumen TRES cosas a la vez:
  1. el `st.date_input` de la franja,
  2. el overlay de texto en español que flota sobre él,
  3. (en reportes con `carga_por_rango`) el loader que descarga de R2.

Cuando ese estado se inicializaba y recortaba desde varios puntos sueltos
del script, las escrituras se pisaban según el orden de ejecución
arriba-abajo de Streamlit y aparecían DESYNCS (overlay ≠ calendario ≠
datos). Ver la memoria `streamlit-widget-value-cacheado`.

Regla de oro
------------
NADIE escribe la clave del rango fuera de este módulo. Todo pasa por:
  · `clave_rango(...)`   → decide QUÉ clave usa este reporte.
  · `asegurar_rango(...)` → siembra el default e/o recorta a bounds.
El widget usa `key=clave_rango(...)`; Streamlit sincroniza solo. Como el
widget y el overlay leen la MISMA clave, no pueden divergir.

Invariante de orden
-------------------
`asegurar_rango(..., bounds=...)` debe llamarse SIEMPRE **antes** de dibujar
el widget en ESTE render — nunca después. Un recorte posterior al render se
vería recién en el siguiente rerun (un render de retraso = desync visible).

Los dos modos del eje temporal
------------------------------
Desde 2026-08-09 la franja sabe filtrar de DOS formas y este módulo es el
dueño de las dos:

  · Rango  → un intervalo `(ini, fin)`.  Clave: `clave_rango(...)`.
  · Cortes → el CONJUNTO exacto de días de una sesión de inventario, que
             no tiene por qué ser contiguo (ver `cortes.py`).
             Clave: `clave_corte(...)`.

Cuál de los dos manda lo dice `clave_modo(clave_corte)` — una clave
derivada de la del corte, así la partición (por reporte / por categoría)
es LA MISMA para los tres estados y no hay forma de que el modo apunte a
un corte de otra categoría.

Invariante del modo Cortes
--------------------------
`aplicar_corte` escribe SIEMPRE el corte **y** el rango. El rango no es
redundante: lo leen el `st.date_input`, el label de la píldora y el loader
de R2, y ninguno de los tres sabe qué es un corte. El corte es un
estrechamiento ADICIONAL sobre ese rango, no un reemplazo del estado.
"""

import datetime

import streamlit as st


def clave_rango(reporte, usa_carga_rango, categoria=None):
    """Clave canónica de session_state para el rango de `reporte`.

    - carga_por_rango → misma clave que el loader R2 (`rango_carga_*`), así
      el date-picker controla directamente qué se descarga.
    - `categoria` → una clave POR CATEGORÍA de gráfico. Hoy solo lo usa
      Ajuste de Inventario, con "visual" o "tiempo" (ver
      graficos.ajuste.categoria_rango_ajuste): Cascada/Mapa de calor/
      Distribución/Tabla funcionan mejor acotados a un período, mientras
      Evolución/Comparativa necesitan varios meses o un año — antes
      compartían una sola clave y se pisaban el rango entre sí.
    - resto → clave de filtro local.

    Hasta el 2026-08-08 esta función recibía TAMBIÉN un `es_ajuste`, que
    era redundante: `categoria_rango_ajuste()` nunca devuelve None, así
    que la categoría llegaba no-nula exactamente cuando el flag era True.
    Peor que redundante, permitía estados contradictorios que nada
    detectaba (es_ajuste=True con categoria=None, o al revés). Ahora la
    categoría es el único discriminante: si viene, hay clave por
    categoría; si no, no la hay.
    """
    if usa_carga_rango:
        return f"rango_carga_{reporte}"
    if categoria:
        # OJO: esta clave NO lleva el reporte. Hoy no colisiona porque solo
        # Ajuste usa categorías Y app.py limpia estas claves al cambiar de
        # reporte. Si un segundo reporte adopta rango por categoría, hay que
        # meter `reporte` en la clave — y entonces esa limpieza sobra.
        return f"ajuste_rango_aplicado_{categoria}"
    return f"rango_franja_{reporte}"


def asegurar_rango(clave, default, bounds=None, reporte=None,
                   usa_carga_rango=False):
    """Punto ÚNICO para sembrar/normalizar el rango. Idempotente.

    1. Si `clave` no existe en session_state, la siembra con `default`.
    2. Si se pasan `bounds` (min, max) válidos, recorta el valor a ese
       intervalo (clamp monótono: preserva ini ≤ fin).
    3. Mantiene el espejo `rango_carga_ok_{reporte}` para reportes por rango
       (lo consume el loader cuando el usuario deja una selección a medias).

    Devuelve la tupla (ini, fin) vigente. Si el estado es una selección a
    medias (1 sola fecha mientras el usuario elige la 2ª), la respeta y la
    devuelve tal cual, sin recortar.
    """
    if clave not in st.session_state:
        st.session_state[clave] = tuple(default)

    cur = st.session_state.get(clave)
    if not (isinstance(cur, (tuple, list)) and len(cur) == 2 and all(cur)):
        return cur  # selección a medias: no tocar

    ini, fin = cur
    if bounds and all(bounds):
        min_b, max_b = bounds
        ini = min(max(ini, min_b), max_b)
        fin = min(max(fin, min_b), max_b)

    nuevo = (ini, fin)
    if nuevo != tuple(cur):
        st.session_state[clave] = nuevo
        if usa_carga_rango and reporte is not None:
            st.session_state[f"rango_carga_ok_{reporte}"] = nuevo
    return nuevo


def _fin_de_mes(d):
    """Último día del mes de `d`."""
    if d.month == 12:
        return d.replace(day=31)
    return d.replace(month=d.month + 1, day=1) - datetime.timedelta(days=1)


def atajos_rango(hoy, bounds):
    """Lista de atajos `(clave, etiqueta, (ini, fin))` válidos para la data.

    - Atajos relativos (semana / mes / últimos 30 días / año) anclados a
      `hoy` y recortados a `bounds` = (min, max).
    - Un chip por cada año presente en la data (además del actual).
    - Se DESCARTA todo atajo cuyo rango original no intersecta `bounds`
      (evita ofrecer "Este mes" cuando colapsaría a un día suelto del borde
      porque la data no llega hasta hoy). El overlay/calendario siguen
      leyendo la misma clave → el atajo no puede desincronizar nada.
    """
    if not (bounds and all(bounds)):
        return []
    min_b, max_b = bounds

    lunes = hoy - datetime.timedelta(days=hoy.weekday())
    crudos = [
        ("todo", "Todo", (min_b, max_b)),
        ("semana", "Esta semana", (lunes, lunes + datetime.timedelta(days=6))),
        ("mes", "Este mes", (hoy.replace(day=1), _fin_de_mes(hoy))),
        ("d30", "Últimos 30 días",
         (hoy - datetime.timedelta(days=29), hoy)),
        ("anio", "Este año",
         (datetime.date(hoy.year, 1, 1), datetime.date(hoy.year, 12, 31))),
    ]
    for y in range(max_b.year, min_b.year - 1, -1):
        if y == hoy.year:
            continue
        crudos.append((f"y{y}", str(y),
                       (datetime.date(y, 1, 1), datetime.date(y, 12, 31))))

    salida = []
    for clave, etiqueta, (ini, fin) in crudos:
        if fin < min_b or ini > max_b:      # no intersecta la data → fuera
            continue
        ci = min(max(ini, min_b), max_b)
        cf = min(max(fin, min_b), max_b)
        salida.append((clave, etiqueta, (ci, cf)))
    return salida


def aplicar_atajo(clave, rango, reporte=None, usa_carga_rango=False):
    """Callback `on_click` que fija el rango desde un atajo.

    Al correr ANTES del rerun, el date_input (que usa `clave`) ve el valor
    nuevo al instanciarse — sin el error "no se puede modificar un widget ya
    instanciado". Enrutar SIEMPRE por aquí: es el ÚNICO punto (junto a
    `asegurar_rango`) autorizado a escribir la clave del rango.
    """
    rango = tuple(rango)
    st.session_state[clave] = rango
    if usa_carga_rango and reporte is not None:
        st.session_state[f"rango_carga_ok_{reporte}"] = rango


# ===========================================================================
# MODO CORTES — el eje temporal como CONJUNTO de días, no como intervalo
# ===========================================================================

def clave_corte(reporte, categoria=None):
    """Clave de session_state del corte activo de `reporte`.

    Espeja EXACTAMENTE la partición de `clave_rango`: si el reporte separa
    rango por categoría (hoy solo Ajuste, visual/tiempo), el corte se
    separa igual. Si no espejara, cambiar de item del rail dejaría vivo un
    corte que ya no corresponde al rango que se está mostrando — el mismo
    bug de desync que motivó este módulo, con otro nombre.

    A diferencia de `clave_rango` no distingue `usa_carga_rango`: el corte
    nunca decide QUÉ se descarga de R2 (para eso ya escribió el rango),
    solo estrecha lo que ya está en memoria.
    """
    if categoria:
        return f"ajuste_corte_aplicado_{categoria}"
    return f"corte_franja_{reporte}"


def clave_modo(clave_c):
    """Clave del selector Rango/Cortes, DERIVADA de la del corte.

    Derivada y no construida aparte a propósito: así los tres estados
    (rango, corte, modo) comparten una sola partición. Con claves armadas
    por separado se podría llegar a "modo = Cortes" apuntando al corte de
    otra categoría, y eso no lo detecta nada.
    """
    return f"modo_{clave_c}"


def modo_fecha(clave_c):
    """Modo vigente ("Rango" | "Cortes"). Default Rango: un reporte que
    nunca abrió el panel se comporta como siempre."""
    return st.session_state.get(clave_modo(clave_c), "Rango")


def corte_vigente(clave_c):
    """El corte que hay que APLICAR, o None.

    Devuelve None si el modo es Rango aunque haya un corte guardado: el
    corte se conserva (volver a Cortes lo restaura) pero no filtra. Es la
    única función que debe consultarse para decidir el filtro — leer la
    clave del corte a mano se saltea justamente esta condición.
    """
    if modo_fecha(clave_c) != "Cortes":
        return None
    return st.session_state.get(clave_c)


def aplicar_corte(clave_r, clave_c, corte, reporte=None, usa_carga_rango=False):
    """Callback `on_click` que fija un corte. Escribe los TRES estados.

    Corre antes del rerun, así que el `date_input` ve el rango nuevo al
    instanciarse (misma mecánica que `aplicar_atajo`, y por el mismo
    motivo: escribir la clave de un widget ya instanciado es un error de
    Streamlit).

    `corte` es un dict de `cortes.cortes_disponibles`. Se guarda una copia
    plana con los días como lista — `session_state` sobrevive al rerun,
    pero una tupla dentro de un dict cacheado por `lru_cache` es la misma
    referencia que usa el módulo de cálculo, y no conviene compartirla.
    """
    # Misma FORMA que un corte recién calculado (incluido `n_dias`): así
    # `cortes.corte_contiguo` y cualquier helper futuro funcionan igual
    # sobre el corte guardado que sobre el de la lista, sin ramas.
    st.session_state[clave_c] = {
        "clave": corte["clave"],
        "etiqueta": corte["etiqueta"],
        "dias": list(corte["dias"]),
        "ini": corte["ini"],
        "fin": corte["fin"],
        "n_dias": corte["n_dias"],
    }
    st.session_state[clave_modo(clave_c)] = "Cortes"
    aplicar_atajo(clave_r, (corte["ini"], corte["fin"]),
                  reporte=reporte, usa_carga_rango=usa_carga_rango)


def volver_a_rango(clave_c):
    """Callback del `date_input`: tocar el calendario a mano vuelve a modo
    Rango.

    Sin esto quedaba el estado contradictorio "el usuario elige 1-31 de
    agosto y la app sigue mostrando los 3 días del corte" — el rango se
    movía pero el corte, más estrecho, seguía mandando. El corte NO se
    borra: se desactiva. Volver a la pestaña Cortes lo recupera.
    """
    st.session_state[clave_modo(clave_c)] = "Rango"


def debug_estado_rango():
    """Vuelca a la UI todas las claves de session_state del eje temporal
    (rango, corte y modo). Para diagnosticar desyncs en Cloud sin
    adivinar: llamar bajo `if st.query_params.get("debug"):`. Muestra la
    VERDAD del estado, que es contra lo que hay que contrastar el overlay
    y el calendario.

    Incluye corte/modo desde que el eje tiene dos modos: ver un rango
    correcto y datos que no le corresponden es EL síntoma de un corte
    activo que no se esperaba, y sin estas claves a la vista se diagnostica
    como un bug del rango.

    Los valores booleanos quedan fuera: "corte" también aparece en la key
    de cada BOTÓN de la lista de cortes (`corte_<reporte>_corte_042`), y
    Streamlit guarda el estado de cada botón como bool. Con 12 cortes eso
    enterraba las 3 claves que importan bajo 12 líneas de `=False`. El
    estado del eje nunca es un bool (tupla, dict o string), así que el
    filtro por tipo separa señal de ruido sin depender de los nombres."""
    claves = sorted(k for k in st.session_state
                    if any(t in k.lower() for t in ("rango", "corte", "modo_"))
                    and not isinstance(st.session_state[k], bool))
    if claves:
        st.caption(
            "🔍 eje temporal · "
            + " · ".join(f"{k}={st.session_state[k]}" for k in claves)
        )
