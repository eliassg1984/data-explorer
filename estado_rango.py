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
"""

import datetime

import streamlit as st


def clave_rango(reporte, usa_carga_rango, es_ajuste, categoria_ajuste=None):
    """Clave canónica de session_state para el rango de `reporte`.

    - carga_por_rango → misma clave que el loader R2 (`rango_carga_*`), así
      el date-picker controla directamente qué se descarga.
    - Ajuste de Inventario → una clave POR CATEGORÍA de gráfico
      ("visual" o "tiempo", ver graficos.ajuste.categoria_rango_ajuste).
      Cascada/Mapa de calor/Distribución/Tabla funcionan mejor acotados a
      un período; Evolución/Comparativa necesitan varios meses o un año —
      antes compartían una sola clave y se pisaban el rango entre sí.
      `categoria_ajuste=None` (categoría aún no resuelta, p.ej. primer
      render) cae en "visual" por ser la categoría por defecto del rail.
    - resto → clave de filtro local.
    """
    if usa_carga_rango:
        return f"rango_carga_{reporte}"
    if es_ajuste:
        return f"ajuste_rango_aplicado_{categoria_ajuste or 'visual'}"
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


def debug_estado_rango():
    """Vuelca a la UI todas las claves de session_state que contienen
    'rango'. Para diagnosticar desyncs en Cloud sin adivinar: llamar bajo
    `if st.query_params.get("debug"):`. Muestra la VERDAD del estado, que
    es contra lo que hay que contrastar el overlay y el calendario."""
    claves = sorted(k for k in st.session_state if "rango" in k.lower())
    if claves:
        st.caption(
            "🔍 rango · "
            + " · ".join(f"{k}={st.session_state[k]}" for k in claves)
        )
