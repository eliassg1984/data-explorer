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
# ESCALA — el mismo rango, elegido como PERÍODOS en vez de como dos fechas
# ===========================================================================
# 2026-08-25, a pedido ("el selector de rango de una tabla dinámica de
# Excel... en realidad me interesaba por los días"). La Escala de tiempo de
# Excel es un riel de períodos con DOS tiradores y un selector de
# granularidad arriba (AÑOS / TRIMESTRES / MESES / DÍAS). No es un
# calendario: no dibuja la grilla del mes ni deja saltar a un día suelto, y
# por eso es barato — es un slider sobre una lista.
#
# Estas tres funciones son la TRADUCCIÓN entre ese gesto y la clave canónica
# del rango; ninguna escribe nada. La escritura sigue pasando por
# `aplicar_atajo`, que es el dueño único (ver la "Regla de oro" del módulo).
# Son puras y las fija `test_graficos.py`.
#
# Viven acá y no en `graficos/periodo.py` aunque el nombre tiente: `periodo`
# es la ventana RELATIVA de una tarjeta ("últimos 12 meses", anclada al
# último día con datos) y a propósito NO toca el estado global. Esto es lo
# contrario — un rango absoluto que reemplaza al de la franja, igual que un
# atajo. De ahí que quede al lado de `atajos_rango`.

ESCALAS = ("Días", "Meses", "Años")


def escala_periodos(escala, bounds):
    """Los períodos de `escala` que cubren `bounds`, como fecha de ARRANQUE.

    Devuelve `date`s y no etiquetas a propósito: el slider guarda lo que se
    le pasa, y volver de "ago 26" a un mes real obligaría a parsear texto en
    español. Cómo se lee se decide al DIBUJAR (`format_func`), que es el
    único lugar donde importa.

    Total sobre las tres escalas, pero en la app sólo la llaman "Meses" y
    "Años" —36 y 3 elementos en un histórico típico—. "Días" serían ~970 y
    un riel de 970 paradas en 250px da 4 días por píxel: ahí no se puede
    elegir una fecha. Esa escala se dibuja con un `st.slider` de fechas, que
    es continuo y afina con las flechas del teclado. Ver
    `graficos/base.py::selector_escala`.
    """
    if not (bounds and all(bounds)):
        return []
    min_b, max_b = bounds
    if min_b > max_b:
        return []
    if escala == "Años":
        return [datetime.date(y, 1, 1)
                for y in range(min_b.year, max_b.year + 1)]
    if escala == "Meses":
        salida, cur = [], min_b.replace(day=1)
        while cur <= max_b:
            salida.append(cur)
            cur = _fin_de_mes(cur) + datetime.timedelta(days=1)
        return salida
    return [min_b + datetime.timedelta(days=i)
            for i in range((max_b - min_b).days + 1)]


def escala_a_rango(escala, desde, hasta, bounds=None):
    """`(ini, fin)` real que cubre de `desde` a `hasta`, ambos INCLUSIVE.

    Los dos argumentos son fechas de arranque de período (lo que devuelve
    `escala_periodos`), así que el extremo derecho hay que EXPANDIRLO: en
    escala de Meses, "hasta agosto" termina el 31 de agosto y no el 1.
    Olvidarse de eso es el bug clásico de un filtro por mes — se pierden 30
    días de datos y el total sale bajo sin que nada avise.

    El recorte a `bounds` no es cosmético y espeja el de `atajos_rango`: en
    escala de Años, "2026" pide hasta el 31-dic, pero los datos terminan el
    25-ago. Sin recortar, el rango declara cuatro meses que no existen y el
    eje de cualquier evolución dibuja el vacío.
    """
    if desde > hasta:
        desde, hasta = hasta, desde
    if escala == "Años":
        ini = datetime.date(desde.year, 1, 1)
        fin = datetime.date(hasta.year, 12, 31)
    elif escala == "Meses":
        ini = desde.replace(day=1)
        fin = _fin_de_mes(hasta)
    else:
        ini, fin = desde, hasta
    if bounds and all(bounds):
        min_b, max_b = bounds
        ini = min(max(ini, min_b), max_b)
        fin = min(max(fin, min_b), max_b)
    return (ini, fin)


def escala_desde_rango(escala, rango, bounds):
    """La vuelta de `escala_a_rango`: el par de períodos que muestra `rango`.

    Sirve para SEMBRAR el riel en cada render desde la clave canónica. Sin
    esto, cambiar la fecha por el calendario de la franja dejaría el riel
    quieto en su último valor — dos controles del mismo dato diciendo cosas
    distintas, que es exactamente la desincronización que este módulo existe
    para evitar (ver la memoria `streamlit-widget-value-cacheado`).

    Redondea hacia AFUERA, igual que Excel: en escala de Meses, del 5 al 23
    de agosto se ve como "agosto" entero. Eso NO reescribe el rango —el
    riel sólo escribe cuando el usuario mueve un tirador—, así que cambiar
    de granularidad y volver recupera el rango exacto.
    """
    periodos = escala_periodos(escala, bounds)
    if not periodos:
        return None
    if not (rango and len(rango) == 2 and all(rango)):
        return (periodos[0], periodos[-1])
    ini, fin = min(rango), max(rango)
    # El período que CONTIENE cada extremo = el último arranque que no lo
    # pasa. Con `bounds` recortando la lista, un extremo que cae fuera se
    # apoya en el borde en vez de quedar sin período.
    izq = [p for p in periodos if p <= ini]
    der = [p for p in periodos if p <= fin]
    return (izq[-1] if izq else periodos[0],
            der[-1] if der else periodos[0])


def ventana_mes(ancla, bounds):
    """La ventana VISIBLE del riel de Días: el mes de `ancla`, en `bounds`.

    Existe porque en escala de Días el riel NO puede abarcar el histórico
    entero: ~970 días en 250px son 4 días por píxel y ahí no se elige una
    fecha (el mismo motivo por el que `escala_periodos` no dibuja Días).
    A pedido, 2026-08-26, con la captura del selector de fecha de Excel al
    lado: su nivel "DÍAS" rotula UN mes arriba ("AGO 2026"), muestra sólo
    los días de ese mes, y para ir a otro están las flechas.

    Recorta a `bounds` por lo mismo que `escala_a_rango`: ofrecer el 25 al
    31 de agosto cuando la data termina el 24 es dibujar vacío.

    GARANTIZA DOS DÍAS DISTINTOS. Un `st.slider` con `min_value ==
    max_value` no tiene riel donde moverse, y el caso pasa de verdad
    cuando el mes del ancla se recorta a un solo día (la data arranca un
    31, o termina un 1). Ahí se toma prestado el día vecino que `bounds`
    permita; quien llama ya garantizó que `bounds` abarca dos días o más,
    así que siempre hay uno de los dos lados libre.
    """
    if not (bounds and all(bounds)) or bounds[0] >= bounds[1]:
        return None
    min_b, max_b = bounds
    ancla = min(max(ancla, min_b), max_b)
    ini = min(max(ancla.replace(day=1), min_b), max_b)
    fin = min(max(_fin_de_mes(ancla), min_b), max_b)
    if ini >= fin:
        if fin > min_b:
            ini = fin - datetime.timedelta(days=1)
        else:
            fin = ini + datetime.timedelta(days=1)
    return (ini, fin)


def ventana_ano(ancla, bounds):
    """La ventana VISIBLE del riel de Meses: el año de `ancla`, en `bounds`.

    Gemela de `ventana_mes`, y por la segunda mitad del mismo pedido
    (2026-08-26): "me gusta en la visualización de día, pero también en la
    de mes, debe mostrar inicialmente solo lo del año en curso". El riel de
    Meses abría con TODOS los meses del histórico —44 paradas de ene-23 a
    ago-26 en 250px— y elegir marzo de 2025 era apuntar a una de esas 44.

    GARANTIZA DOS MESES DISTINTOS, por el mismo motivo que su gemela
    garantiza dos días: un `st.select_slider` con una sola parada no tiene
    riel donde moverse. Pasa cuando el año del ancla se recorta a un solo
    mes (la data arranca en diciembre, o termina en enero). Ahí se toma
    prestado el mes vecino que `bounds` permita.
    """
    if not (bounds and all(bounds)) or bounds[0] >= bounds[1]:
        return None
    min_b, max_b = bounds
    ancla = min(max(ancla, min_b), max_b)
    ini = min(max(datetime.date(ancla.year, 1, 1), min_b), max_b)
    fin = min(max(datetime.date(ancla.year, 12, 31), min_b), max_b)
    if len(escala_periodos("Meses", (ini, fin))) < 2:
        _prev = ini.replace(day=1) - datetime.timedelta(days=1)
        if _prev >= min_b:
            ini = max(min_b, _prev.replace(day=1))
        else:
            fin = min(max_b, _fin_de_mes(_fin_de_mes(fin)
                                         + datetime.timedelta(days=1)))
    return (ini, fin)


def ventana_decada(ancla, bounds):
    """La ventana VISIBLE del riel de Años: la década de `ancla`, en `bounds`.

    Tercera de la familia (`ventana_mes` → `ventana_ano` → ésta), a pedido
    2026-08-26: "cuando es años, también debe seguir la lógica de mostrar
    sólo años". Con el histórico de hoy —cuatro años— el riel se ve igual
    que antes, porque la década recortada a los datos ES el histórico; lo
    que cambia es que deja de crecer sin techo cuando la data crezca, y
    que las tres escalas pasan a explicarse con la misma frase.

    RECORTA A LOS DATOS, y por eso la cabecera dice "2023-2026" y no
    "2020-2029": el mismo criterio que `escala_periodos` aplica al año del
    borde — no prometer períodos que no tienen nada adentro.

    GARANTIZA DOS AÑOS DISTINTOS *si `bounds` da para eso*. Si toda la data
    vive en un solo año, la escala de Años tiene una sola parada la mires
    como la mires: eso no lo arregla ninguna ventana, y ya era así antes.
    """
    if not (bounds and all(bounds)) or bounds[0] >= bounds[1]:
        return None
    min_b, max_b = bounds
    ancla = min(max(ancla, min_b), max_b)
    _d0 = ancla.year - ancla.year % 10
    ini = min(max(datetime.date(_d0, 1, 1), min_b), max_b)
    fin = min(max(datetime.date(_d0 + 9, 12, 31), min_b), max_b)
    if len(escala_periodos("Años", (ini, fin))) < 2:
        if datetime.date(ini.year - 1, 12, 31) >= min_b:
            ini = max(min_b, datetime.date(ini.year - 1, 1, 1))
        else:
            fin = min(max_b, datetime.date(fin.year + 1, 12, 31))
    return (ini, fin)


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
