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
    # Un atajo cancela cualquier primer clic pendiente del calendario: si no,
    # ese clic viejo se combinaría con el próximo y daría un rango absurdo.
    st.session_state[clave_borrador(clave)] = None
    if usa_carga_rango and reporte is not None:
        st.session_state[f"rango_carga_ok_{reporte}"] = rango


def clave_borrador(clave):
    """Clave del BORRADOR del calendario doble (1er clic pendiente).

    El calendario propio necesita recordar la fecha del primer clic mientras
    espera el segundo. Ese estado NO va en la clave del rango: dejarlo ahí
    pondría a la app en "selección a medias" (rango de 1 fecha) y el loader
    y los gráficos verían un rango incompleto entre clic y clic. El borrador
    es estado local del calendario; el rango real solo se escribe cuando ya
    hay dos fechas.
    """
    return f"cal_borrador_{clave}"


def aplicar_clic_dia(clave, dia, reporte=None, usa_carga_rango=False):
    """Callback `on_click` de un día del calendario doble.

    Máquina de dos clics:
      1er clic  → guarda `dia` en el borrador; el rango NO se toca.
      2do clic  → escribe el rango ordenado (min, max) y limpia el borrador.

    Como `aplicar_atajo`, corre ANTES del rerun, así el resto del script ve
    el valor nuevo. Es el otro punto autorizado a escribir la clave del
    rango (junto a `asegurar_rango` y `aplicar_atajo`).
    """
    k_draft = clave_borrador(clave)
    pendiente = st.session_state.get(k_draft)

    if pendiente is None:
        st.session_state[k_draft] = dia
        return

    rango = (min(pendiente, dia), max(pendiente, dia))
    st.session_state[k_draft] = None
    st.session_state[clave] = rango
    if usa_carga_rango and reporte is not None:
        st.session_state[f"rango_carga_ok_{reporte}"] = rango


def limpiar_borrador(clave):
    """Descarta un primer clic pendiente (lo usan los atajos)."""
    st.session_state[clave_borrador(clave)] = None


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
