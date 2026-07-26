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

import streamlit as st


def clave_rango(reporte, usa_carga_rango, es_ajuste):
    """Clave canónica de session_state para el rango de `reporte`.

    - carga_por_rango → misma clave que el loader R2 (`rango_carga_*`), así
      el date-picker controla directamente qué se descarga.
    - Ajuste de Inventario → clave histórica que graficos.py también lee.
    - resto → clave de filtro local.
    """
    if usa_carga_rango:
        return f"rango_carga_{reporte}"
    if es_ajuste:
        return "ajuste_rango_aplicado"
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
