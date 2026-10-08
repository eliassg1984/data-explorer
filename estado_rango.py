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
    - `categoria` → una clave POR CATEGORÍA de gráfico. La usan DOS
      reportes, y por motivos distintos:
        · Ajuste de Inventario, con "visual" o "tiempo" (ver
          graficos.ajuste.categoria_rango_ajuste): Cascada/Mapa de calor/
          Distribución/Tabla funcionan mejor acotados a un período,
          mientras Evolución/Comparativa necesitan varios meses o un año —
          antes compartían una sola clave y se pisaban el rango entre sí.
        · Compras, con una categoría por SECCIÓN de su pila (ver
          graficos.compras.CATEGORIA_SEC): ahí la categoría no agrupa
          gráficos parecidos, separa TARJETAS. Cada una trae su propio
          selector de fecha en la cabecera y hasta el 2026-09-08 los cinco
          escribían esta misma clave sin categoría, así que mover la fecha
          en una movía las otras cuatro. Ver regla #363.
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
        # LA CLAVE LLEVA EL REPORTE desde el 2026-09-08, y ese cambio se
        # hizo justo cuando llegó el segundo reporte con categorías
        # (Compras). Antes era `ajuste_rango_aplicado_{categoria}` y no
        # colisionaba sólo porque el único usuario era Ajuste Y `app.py`
        # limpiaba esas dos claves al cambiar de reporte — esa limpieza ya
        # no hace falta y se retiró con este cambio.
        return f"rango_cat_{reporte}_{categoria}"
    return f"rango_franja_{reporte}"


def clave_eco(clave):
    """La clave ESPEJO de `clave`: una copia que Streamlit no recolecta.

    La clave del rango es también la KEY de un `st.date_input`, y Streamlit
    se lleva el estado de un widget que deja de renderizarse. Mientras el
    pill vivía en la franja siempre había alguien dibujándolo; desde que
    Compras no lo dibuja arriba (2026-09-06) el único render que lo instancia
    es la tarjeta de Documentos SUNAT, así que al salir de esa vista la clave
    queda huérfana y la recolección se la lleva con el rango que el usuario
    acababa de elegir.

    El espejo es una clave normal —nadie la recolecta— y se restaura ANTES de
    sembrar el default. Ver regla #332."""
    return f"{clave}__eco"


def restaurar_eco(clave):
    """Devuelve el rango desde el espejo si la clave quedó huérfana, y
    refresca el espejo con lo que haya vigente. Idempotente.

    Se llama en DOS sitios y no es duplicación: `app.py` lo hace en cada
    rerun completo, y `documentos_sunat.py` otra vez antes de leer el rango
    —porque el rail de Compras es un `@st.fragment` y un clic suyo NO
    re-ejecuta `app.py`, así que entre salir de la vista y volver a ella
    nadie pasa por la restauración de arriba. Sin esto la tarjeta volvía
    mostrando «Elegí una fecha…» con el calendario que ella misma dibuja
    justo encima (regla #115 otra vez).

    Escribe la clave de un widget ANTES de instanciarlo, que es el patrón
    sancionado (mismo que `aplicar_corte`): hacerlo DESPUÉS es un error de
    Streamlit.
    """
    eco = clave_eco(clave)
    if clave not in st.session_state and eco in st.session_state:
        st.session_state[clave] = st.session_state[eco]
    if clave in st.session_state:
        st.session_state[eco] = st.session_state[clave]
    return st.session_state.get(clave)


def _recortar_media(clave, cur, bounds):
    """Una media selección se queda a medias, pero dentro de bounds.

    La ARIDAD se respeta a propósito (regla #196: `st.date_input` en modo
    rango commitea una tupla de un elemento apenas se hace el primer clic,
    y ése es el estado normal de "quiero ver un día"). Lo que sí se toca
    es el VALOR, porque los bounds pueden ENCOGERSE entre un render y el
    siguiente: Compras > Documentos SUNAT abre el calendario hasta HOY
    —le pregunta al SIRE en vivo— y el resto de las vistas de Compras
    vuelve al tope del parquet. Elegir hoy ahí y cambiar de vista dejaba
    en `session_state` una fecha por encima del `max_value` del widget, y
    Streamlit no la recorta: tira `StreamlitAPIException` y se cae la
    página entera. Ver `arquitectura.md` regla #197.
    """
    if not (bounds and all(bounds)
            and isinstance(cur, (tuple, list)) and len(cur) == 1 and cur[0]):
        return cur
    min_b, max_b = bounds
    d = min(max(cur[0], min_b), max_b)
    if d == cur[0]:
        return cur
    st.session_state[clave] = (d,)
    return (d,)


def asegurar_rango(clave, default, bounds=None, reporte=None,
                   usa_carga_rango=False):
    """Punto ÚNICO para sembrar/normalizar el rango. Idempotente.

    1. Si `clave` no existe en session_state, la siembra con `default`.
    2. Si se pasan `bounds` (min, max) válidos, recorta el valor a ese
       intervalo (clamp monótono: preserva ini ≤ fin).
    3. Mantiene el espejo `rango_carga_ok_{reporte}` para reportes por rango
       (lo consume el loader cuando el usuario deja una selección a medias).

    Devuelve la tupla (ini, fin) vigente. Una selección a medias (1 sola
    fecha mientras el usuario elige la 2ª) se respeta COMO TAL —no se
    convierte en rango— pero igual se recorta a bounds: ver
    `_recortar_media`.
    """
    if clave not in st.session_state:
        st.session_state[clave] = tuple(default)

    cur = st.session_state.get(clave)
    if not (isinstance(cur, (tuple, list)) and len(cur) == 2 and all(cur)):
        return _recortar_media(clave, cur, bounds)

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


# ===========================================================================
# LOS ATAJOS DEL SELECTOR DE FECHA DE UNA TARJETA (2026-10-08, regla #616)
# ===========================================================================
# Los del panel de `graficos/panel_fecha.py`, la «opción A» que eligió el
# usuario sobre un mockup: escritos enteros y agrupados por lo que significan.
# Se distinguen de `atajos_rango` (los de la píldora de la franja) en el ANCLA:
# cuentan hasta el ÚLTIMO DÍA CON DATOS, no hasta hoy. Con el ancla en hoy,
# «Últimos 30 días» daba del 9 set al 7 oct (29 días de datos) y la tarjeta
# abría en «8 sep – 7 oct», que no era ningún atajo: nada podía decir cuál
# estaba puesto. Con este ancla, la tarjeta ABRE en un atajo con nombre — las
# de un mes en «Últimos 30 días» y el reporte de Compras en «Últimos 12
# meses» (`app.py` toma los dos de acá).
#
# (clave, nombre, grupo), en el orden en que se muestran.
ATAJOS_TARJETA = (
    ("semana", "Esta semana", "En curso"),
    ("mes", "Este mes", "En curso"),
    ("anio", "Este año", "En curso"),
    ("d30", "Últimos 30 días", "Hacia atrás"),
    ("m3", "Últimos 3 meses", "Hacia atrás"),
    ("m12", "Últimos 12 meses", "Hacia atrás"),
    ("mes_ant", "Mes pasado", "Completos"),
    ("anio_ant", "Año pasado", "Completos"),
    ("todo", "Todo el histórico", "Completos"),
)


def meses_atras(d, n):
    """`d` corrido `n` meses atrás, con el día recortado al último del mes
    (31 mar → 28 feb). Es la cuenta de `pd.DateOffset(months=n)`, la que usa
    `graficos/periodo.py::ventana`: «Últimos 12 meses» tiene que dar lo
    mismo que la ventana de 12 meses con que abre Compras."""
    t = d.year * 12 + (d.month - 1) - n
    y, m = divmod(t, 12)
    m += 1
    return datetime.date(y, m, min(d.day, _fin_de_mes(datetime.date(y, m, 1)).day))


def atajos_tarjeta(ancla, bounds):
    """`[(clave, nombre, grupo, (ini, fin))]` anclados a `ancla`, el último
    día con datos, y recortados a `bounds`. Se descarta el que no toca los
    datos (el año pasado de un parquet que empieza este año).

    Los «hacia atrás» terminan en el ancla y arrancan el día siguiente al de
    hace N: 30 días son 30 días con el ancla adentro. Los «en curso» van del
    1 (o del lunes) al ancla. Los «completos», el período entero."""
    if not (bounds and all(bounds)) or ancla is None:
        return []
    min_b, max_b = bounds
    if min_b > max_b:
        return []
    ancla = min(max(ancla, min_b), max_b)
    un_dia = datetime.timedelta(days=1)
    ini_mes = ancla.replace(day=1)
    fin_mes_ant = ini_mes - un_dia
    crudos = {
        "semana": (ancla - datetime.timedelta(days=ancla.weekday()), ancla),
        "mes": (ini_mes, ancla),
        "anio": (datetime.date(ancla.year, 1, 1), ancla),
        "d30": (ancla - datetime.timedelta(days=29), ancla),
        "m3": (meses_atras(ancla, 3) + un_dia, ancla),
        "m12": (meses_atras(ancla, 12) + un_dia, ancla),
        "mes_ant": (fin_mes_ant.replace(day=1), fin_mes_ant),
        "anio_ant": (datetime.date(ancla.year - 1, 1, 1),
                     datetime.date(ancla.year - 1, 12, 31)),
        "todo": (min_b, max_b),
    }
    salida = []
    for clave, nombre, grupo in ATAJOS_TARJETA:
        ini, fin = crudos[clave]
        if fin < min_b or ini > max_b:
            continue
        salida.append((clave, nombre, grupo, (max(ini, min_b), min(fin, max_b))))
    return salida


def atajo_de(rango, atajos):
    """La clave del atajo que es EXACTAMENTE `rango`, o None. Si dos
    coinciden (el lunes 1, «Esta semana» y «Este mes» son el mismo día), el
    primero en el orden de `ATAJOS_TARJETA`."""
    if not (isinstance(rango, (tuple, list)) and len(rango) == 2 and all(rango)):
        return None
    par = (min(rango), max(rango))
    for clave, _nombre, _grupo, r in atajos:
        if r == par:
            return clave
    return None


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
    rango por categoría (Ajuste por categoría del rail, Compras por sección
    de la pila), el corte se separa igual. Si no espejara, cambiar de item
    del rail dejaría vivo un corte que ya no corresponde al rango que se
    está mostrando — el mismo bug de desync que motivó este módulo, con
    otro nombre.

    El reporte va adentro de la clave por el mismo motivo que en
    `clave_rango`, y desde el mismo día: dos reportes con categorías se
    pisarían.

    A diferencia de `clave_rango` no distingue `usa_carga_rango`: el corte
    nunca decide QUÉ se descarga de R2 (para eso ya escribió el rango),
    solo estrecha lo que ya está en memoria.
    """
    if categoria:
        return f"corte_cat_{reporte}_{categoria}"
    return f"corte_franja_{reporte}"


def clave_modo(clave_c):
    """Clave del selector Rango/Cortes, DERIVADA de la del corte.

    Derivada y no construida aparte a propósito: así los tres estados
    (rango, corte, modo) comparten una sola partición. Con claves armadas
    por separado se podría llegar a "modo = Cortes" apuntando al corte de
    otra categoría, y eso no lo detecta nada.
    """
    return f"modo_{clave_c}"


MODOS_FECHA = ("Rango", "Corte", "Varios")
"""Los tres modos del eje temporal. Los tres nombran QUÉ unidad de tiempo
se elige, no qué pasa después — de ahí que sean sustantivos:
  · Rango  — un intervalo (ini, fin). El de siempre.
  · Corte  — UNA sesión de inventario; el clic en la lista reemplaza.
  · Varios — VARIAS sesiones; el clic alterna (agrega/saca).

"Varios" se llamó "Comparar" hasta 2026-08-10 y era un nombre MENTIROSO:
no compara nada, SUMA. Los días de las sesiones elegidas se unen en un
solo conjunto y todo lo que se ve abajo (mapa, cascada, tabla) es el
total de ese conjunto — no hay una vista lado a lado por ningún lado.
Tampoco "Acumulado", que en inventario se lee como total corrido desde
una fecha (YTD) cuando acá la selección es arbitraria: se puede elegir
marzo y agosto salteando el medio.

Corte y Varios comparten estado: son el mismo conjunto de días, con
distinto gesto de selección. Por eso pasar de uno a otro no pierde nada."""


def modo_fecha(clave_c):
    """Modo vigente (uno de `MODOS_FECHA`). Default Rango: un reporte que
    nunca abrió el panel se comporta como siempre.

    Valida contra `MODOS_FECHA` y no devuelve lo que haya guardado tal
    cual: una sesión abierta desde ANTES de un renombre de modo trae un
    valor que ya no existe, y `st.segmented_control` con un `default` que
    no está entre sus opciones no falla — arranca sin nada seleccionado y
    el panel queda mudo. Cayendo a "Rango" el peor caso es el
    comportamiento de siempre."""
    _m = st.session_state.get(clave_modo(clave_c), "Rango")
    return _m if _m in MODOS_FECHA else "Rango"


def modo_por_cortes(clave_c):
    """True si el modo vigente filtra por cortes (Corte o Varios).
    Existe para que nadie escriba la comparación a mano y se olvide de uno
    de los dos — que es como se cuelan los bugs de "funciona en Corte pero
    no en Varios"."""
    return modo_fecha(clave_c) in ("Corte", "Varios")


def corte_vigente(clave_c):
    """La SELECCIÓN de cortes que hay que APLICAR, o None.

    Devuelve None si el modo es Rango aunque haya una selección guardada:
    se conserva (volver a Corte/Comparar la restaura) pero no filtra. Es
    la única función que debe consultarse para decidir el filtro — leer la
    clave a mano se saltea justamente esta condición.
    """
    if not modo_por_cortes(clave_c):
        return None
    return st.session_state.get(clave_c)


def _fusionar(cortes_sel):
    """Une N cortes en UN estado con la misma FORMA que tenía uno solo.

    Esta es la pieza que hace que la selección múltiple no cueste nada río
    abajo: `dias` es la UNIÓN de los días de todos los cortes elegidos, y
    el filtro (`df[fecha].isin(dias)`) no distingue si vienen de uno o de
    cinco. `ini`/`fin` son los extremos del conjunto, que es lo que
    necesita el rango espejo — y por eso el rango de una selección de 2
    cortes abarca también el hueco entre ellos, mientras que los datos NO:
    exactamente la diferencia que justifica el modo.
    """
    _dias = sorted({d for c in cortes_sel for d in c["dias"]})
    _claves = [c["clave"] for c in cortes_sel]
    if len(cortes_sel) == 1:
        _etiqueta = cortes_sel[0]["etiqueta_anio"]
    else:
        _etiqueta = (f"{len(cortes_sel)} cortes · "
                     f"{cortes_sel[0]['etiqueta']} … "
                     f"{cortes_sel[-1]['etiqueta_anio']}")
    return {
        "claves": _claves,
        "etiqueta": _etiqueta,
        "dias": _dias,
        "ini": _dias[0],
        "fin": _dias[-1],
        "n_dias": len(_dias),
        "n_cortes": len(_claves),
    }


def aplicar_corte(clave_r, clave_c, corte, reporte=None, usa_carga_rango=False):
    """Callback `on_click` que fija UN corte, reemplazando la selección.
    Lo usan el clic normal de la lista y el stepper ‹ ›.

    Corre antes del rerun, así que el `date_input` ve el rango nuevo al
    instanciarse (misma mecánica que `aplicar_atajo`, y por el mismo
    motivo: escribir la clave de un widget ya instanciado es un error de
    Streamlit).
    """
    _fijar_seleccion(clave_r, clave_c, [corte], reporte, usa_carga_rango)


def alternar_corte(clave_r, clave_c, corte, todos, reporte=None,
                   usa_carga_rango=False):
    """Callback `on_click` del modo Comparar: agrega o saca `corte` de la
    selección.

    `todos` es la lista COMPLETA de cortes disponibles y hace falta para
    reconstruir la selección en orden cronológico — el estado guarda solo
    las claves, no los cortes enteros, así que sin la lista no se puede
    recomponer `dias`.

    Nunca deja la selección vacía: sacar el último elemento se ignora. Una
    selección vacía filtraría CERO filas y la pantalla quedaría en blanco
    sin explicación; para ver todo está el modo Rango.
    """
    _sel = set(st.session_state.get(clave_c, {}).get("claves", []))
    if corte["clave"] in _sel:
        if len(_sel) == 1:
            return
        _sel.discard(corte["clave"])
    else:
        _sel.add(corte["clave"])
    _fijar_seleccion(clave_r, clave_c,
                     [c for c in todos if c["clave"] in _sel],
                     reporte, usa_carga_rango)


def _fijar_seleccion(clave_r, clave_c, cortes_sel, reporte, usa_carga_rango):
    """Escribe los TRES estados de una vez. Punto único: si el corte se
    escribiera sin el rango, el `date_input`, el label y el loader de R2
    seguirían mostrando el rango viejo (ver el invariante del módulo)."""
    if not cortes_sel:
        return
    _estado = _fusionar(cortes_sel)
    st.session_state[clave_c] = _estado
    # Si ya estamos en Comparar hay que QUEDARSE ahí: forzar "Corte" en
    # cada alternar_corte sacaría al usuario del modo en el que está
    # armando la selección, a mitad de armarla.
    if not modo_por_cortes(clave_c):
        st.session_state[clave_modo(clave_c)] = "Corte"
    aplicar_atajo(clave_r, (_estado["ini"], _estado["fin"]),
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
