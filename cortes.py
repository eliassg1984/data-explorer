"""
cortes — el CORTE como eje temporal propio (rachas de días de conteo).

Qué es un corte y por qué NO es un rango
----------------------------------------
Un corte es el CONJUNTO de días en que se ejecutó un mismo proceso de
inventario. Una sesión real se abre y se cierra en días sueltos: un fin
de semana de por medio, un área que se retoma dos días después. Por eso
"20-24 jul" puede ser {20, 21, 24} — y el 22 y el 23 traer ajustes
diarios que NO son de ese conteo.

De ahí la diferencia que decide todo el diseño del modo Cortes:

    rango  →  df[fecha].between(ini, fin)   INTERVALO — arrastra el 22 y 23
    corte  →  df[fecha].isin(dias)          CONJUNTO  — exacto

El widget de fecha de la franja sabe expresar las dos cosas (ver
`estado_rango.py`, que es el dueño del estado, y el modo Rango/Cortes en
`app.py`). Un `st.date_input` por sí solo NUNCA puede expresar la
segunda: solo sabe de intervalos.

Por qué vive en la raíz y no en graficos/ajuste/
-----------------------------------------------
Hasta 2026-08-09 esto era `graficos/ajuste/_comun.py`, donde solo lo
veían el mapa de calor y la tabla pivote. Al pasar el corte a ser un modo
del calendario de la franja — que es código genérico de `app.py`, común a
los 8 reportes — el cálculo subió acá: módulo de raíz, sin importar
streamlit ni graficos, para que lo puedan usar los dos lados sin ciclo de
imports. `graficos/ajuste/_comun.py` lo reexporta con los nombres
privados de siempre; sus consumidores no cambiaron una línea.
"""

import datetime
from functools import lru_cache

MESES_ABR_ES = ("ene", "feb", "mar", "abr", "may", "jun",
                "jul", "ago", "set", "oct", "nov", "dic")

DIAS_ABR_ES = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
"""Día de semana abreviado, indexado por `date.weekday()` (0 = lunes).

Gemela de `MESES_ABR_ES` y por el mismo motivo: Plotly rotula en INGLÉS si
no se le dice otra cosa (regla #241), y el proyecto ya tenía DOS listas de
meses en español. Ésta nació capitalizada y privada en
`graficos/ventas_comparativo.py` (`_DIAS_ES`); subió acá el 2026-09-08,
cuando el drill Semanal de Compras pidió la misma cosa. En minúscula, como
sus vecinas — quien quiera «Sáb» tiene `.capitalize()`."""

MESES_LARGOS_ES = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
                   "julio", "agosto", "setiembre", "octubre", "noviembre",
                   "diciembre")
"""Los mismos meses, enteros: «Del 8 de setiembre al 7 de octubre». Con
«setiembre» y no «septiembre» para que la abreviatura siga siendo «set».
Nació con el panel del selector de fecha de las tarjetas (2026-10-08,
`graficos/panel_fecha.py`, regla #616)."""

DIAS_LARGOS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes",
                  "sábado", "domingo")
"""Día de semana entero, indexado por `date.weekday()`. Ver `MESES_LARGOS_ES`."""

DIA_CIERRE_OPERATIVO = 7
"""Hasta qué día del mes un cierre de inventario es del mes ANTERIOR.

El Almacén fecha el cierre el día en que se abre en el sistema, y el de fin
de mes se abre en los primeros días del siguiente: el «cierre de septiembre»
lleva fecha de octubre. Lo dijo el usuario (2026-10-05). Regla #613.

Era 6 hasta el 2026-10-11, cuando el usuario definió el cierre de mes como
lo registrado «entre el día 1 hasta el día 7 inclusive» y las dos reglas
pasaron a ser una (regla #632). En los datos de ese día no cambió ninguna
cifra: nunca se había registrado un ajuste un día 7."""


def fecha_operativa(fechas, dia=DIA_CIERRE_OPERATIVO):
    """La fecha en su MES OPERATIVO: lo registrado del día 1 al `dia` pasa
    al último día del mes anterior, con su misma hora; lo demás queda igual.

    Restar tantos días como el día del mes cae justo en el último del mes
    anterior (3 oct − 3 días = 30 set), sin calcular cuántos días tiene.
    Recibe y devuelve una Series de pandas."""
    import pandas as pd
    f = pd.to_datetime(fechas, errors="coerce")
    temprano = f.dt.day <= dia
    return f.where(~temprano, f - pd.to_timedelta(f.dt.day, unit="D"))


def etiqueta_hora(h):
    """La hora como se dice, no como la guarda el reloj de la base: «7 pm» y
    no «19h» (pedido del usuario, 2026-08-14). El mediodía y la medianoche
    son los dos casos que se escriben mal solos: 12 pm y 12 am, nunca 0.

    Nació en `graficos/ventas_horario.py` (que la sigue reexportando como
    `_etiqueta_hora`); subió acá el 2026-09-26, cuando la pidió la ficha de
    la hora (`graficos/ventas_ficha_hora.py`), que no puede importar el
    módulo del mapa sin armar un ciclo."""
    h = int(h) % 24
    return f"{h % 12 or 12} {'am' if h < 12 else 'pm'}"

# ── FERIADOS NACIONALES DE PERÚ ────────────────────────────────────────────
# Vivían privados en `graficos/ventas_comparativo.py`, que fue el primero
# que los necesitó (una barra rara de un martes se explica sola si el martes
# era feriado). Subieron acá —módulo de raíz, sin streamlit ni graficos— por
# el mismo criterio que explica el docstring de arriba para los cortes: los
# pide un SEGUNDO consumidor de otro reporte (el drill Semanal de Compras,
# 2026-09-08) y el import directo entre dos módulos de reportes distintos es
# la forma de terminar en un ciclo. `ventas_comparativo` los reexporta con
# sus nombres privados de siempre; sus consumidores (y sus tests) no
# cambiaron una línea.
#
# OJO: es el calendario NACIONAL. No sabe de cierres propios del local,
# aniversarios ni feriados regionales — si eso hace falta, esto tiene que
# pasar a ser un dato mantenido por el negocio, no una constante acá.
FERIADOS_FIJOS_PE = (
    (1, 1),    # Año Nuevo
    (5, 1),    # Día del Trabajo
    (6, 29),   # San Pedro y San Pablo
    (7, 28),   # Fiestas Patrias
    (7, 29),   # Fiestas Patrias
    (8, 6),    # Batalla de Junín
    (8, 30),   # Santa Rosa de Lima
    (10, 8),   # Combate de Angamos
    (11, 1),   # Todos los Santos
    (12, 8),   # Inmaculada Concepción
    (12, 9),   # Batalla de Ayacucho
    (12, 25),  # Navidad
)


def pascua(anio):
    """Domingo de Pascua de `anio` (algoritmo gregoriano anónimo/Meeus).
    Hace falta para Jueves y Viernes Santo, los dos únicos feriados peruanos
    que cambian de fecha cada año — y los que mueven Semana Santa entre
    marzo y abril, distorsionando cualquier comparativo mensual."""
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lo = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lo) // 451
    mes, dia = divmod(h + lo - 7 * m + 114, 31)
    return datetime.date(anio, mes, dia + 1)


@lru_cache(maxsize=64)
def feriados_peru(anio):
    """`frozenset` de `date` con los feriados nacionales de Perú de `anio`:
    los fijos de FERIADOS_FIJOS_PE + Jueves y Viernes Santo.

    Cacheado porque se pregunta POR DÍA: el drill Semanal lo consulta una
    vez por cada día del rango dibujado, y recalcular Pascua 60 veces por
    render es trabajo regalado. El `frozenset` es lo que hace segura esa
    caché — un `set` mutable devuelto desde `lru_cache` es el mismo objeto
    para todos los llamadores, y al primero que le haga `|=` le ensucia el
    calendario a los demás."""
    fer = {datetime.date(anio, m, d) for m, d in FERIADOS_FIJOS_PE}
    p = pascua(anio)
    fer.add(p - datetime.timedelta(days=3))   # Jueves Santo
    fer.add(p - datetime.timedelta(days=2))   # Viernes Santo
    return frozenset(fer)


def feriados_entre(ini, fin):
    """Cuántos feriados nacionales caen en [ini, fin] (inclusive)."""
    fer = set()
    for a in range(ini.year, fin.year + 1):
        fer |= feriados_peru(a)
    return sum(1 for f in fer if ini <= f <= fin)


CORTE_MAX_SALTO_DIAS = 4
"""Una sesión de conteo real puede durar varios días NO estrictamente
seguidos (fin de semana de por medio, un área que se retoma dos días
después). Mientras el salto al día siguiente con movimiento sea ≤ a
esto, sigue siendo el MISMO corte; más que esto, arranca uno nuevo.
Número fijado a pedido explícito (no es un ajuste fino, es una regla de
negocio) — si cambia, es UNA constante."""


def etiqueta_corte(inicio, fin):
    """'1-4 ago' si el corte no cruza de mes; '30 jul - 2 ago' si cruza.
    Un corte de un solo día no muestra rango: '15 ago'."""
    _di, _mi = inicio.day, inicio.month
    _df, _mf = fin.day, fin.month
    if inicio == fin:
        return f"{_di} {MESES_ABR_ES[_mi - 1]}"
    if _mi == _mf:
        return f"{_di}-{_df} {MESES_ABR_ES[_mi - 1]}"
    return f"{_di} {MESES_ABR_ES[_mi - 1]} - {_df} {MESES_ABR_ES[_mf - 1]}"


def etiqueta_corte_anio(inicio, fin):
    """Como `etiqueta_corte` pero con el AÑO: '1-5 ago 2026'.

    Es una función APARTE y no un parámetro de `etiqueta_corte` porque las
    dos tienen consumidores con requisitos opuestos:
      · `etiqueta_corte` → cabeceras de la tabla pivote, donde el ancho de
        columna se calcula a partir del largo del label
        (tablas/ajuste_pivote.py::_ancho_header_periodo). Sumarle 5
        caracteres ahí vuelve a truncar los headers, que es un bug que ya
        se arregló una vez.
      · `etiqueta_corte_anio` → la lista del calendario y el label del
        pill, donde el año es lo que pidió el usuario para no confundir
        el mismo mes de dos años distintos.

    Si el corte cruza de año (raro pero posible: un conteo de fin de
    diciembre), el año va en LOS DOS extremos — '30 dic 2025 - 2 ene 2026'
    —, que es justo el caso donde omitirlo engaña.
    """
    if inicio.year != fin.year:
        return (f"{inicio.day} {MESES_ABR_ES[inicio.month - 1]} {inicio.year}"
                f" - {fin.day} {MESES_ABR_ES[fin.month - 1]} {fin.year}")
    return f"{etiqueta_corte(inicio, fin)} {fin.year}"


def _rachas(dias):
    """Parte una lista ORDENADA de `datetime.date` en rachas por el salto
    máximo. Núcleo compartido por `cortes_por_racha` (que necesita el mapa
    fecha→corte para una Series de pandas) y `cortes_disponibles` (que
    necesita la lista de cortes como objetos). Antes cada una tenía su
    propio bucle; el mismo bucle escrito dos veces es la forma más fácil
    de que la franja y el mapa de calor discrepen sobre dónde empieza un
    corte."""
    if not dias:
        return []
    grupos, actual = [], [dias[0]]
    for d in dias[1:]:
        if (d - actual[-1]).days > CORTE_MAX_SALTO_DIAS:
            grupos.append(actual)
            actual = [d]
        else:
            actual.append(d)
    grupos.append(actual)
    return grupos


def cortes_por_racha(fechas):
    """Agrupa una Series de fechas en "cortes" (ver `_rachas`).
    Reemplaza a "Día" -- una sesión de conteo real casi nunca es un solo
    día suelto, y agrupar por calendario partía una sesión de varios días
    en columnas sin relación entre sí.

    Devuelve (clave, etiqueta) igual que las demás granularidades, para
    que `_armar_tabla_pivote_ajuste` no necesite saber la diferencia -- a
    diferencia de Semana/Mes (donde cada fecha resuelve su clave sola),
    acá hace falta la lista COMPLETA de fechas únicas primero para saber
    dónde están los saltos, así que se arma un mapa fecha→(clave,
    etiqueta) y se aplica con `.map()`."""
    dias = fechas.dt.normalize()
    unicos = sorted(dias.dropna().unique())
    if not unicos:
        return dias.astype(str), dias.astype(str)

    # `_rachas` trabaja con `datetime.date` (es puro, sin pandas), pero el
    # mapa que consume `.map()` tiene que llevar como clave el valor
    # ORIGINAL de la Series: mapear con un tipo distinto devuelve NaN en
    # todas las filas sin avisar. `_orig` guarda esa correspondencia.
    # Convertir la Series entera a `date` con un lambda sería lo obvio y
    # es justo lo que no hay que hacer: son ~7x más lento que `.map()` con
    # dict, y esta línea corre en cada rerun de la tabla pivote.
    _orig = {_a_date(d): d for d in unicos}
    mapa_clave, mapa_etq = {}, {}
    for i, racha in enumerate(_rachas(sorted(_orig))):
        _clave = f"corte_{i:03d}"
        _etq = etiqueta_corte(racha[0], racha[-1])
        for d in racha:
            mapa_clave[_orig[d]] = _clave
            mapa_etq[_orig[d]] = _etq

    return dias.map(mapa_clave), dias.map(mapa_etq)


def _a_date(valor):
    """`datetime.date` puro desde lo que devuelva pandas/numpy. El estado
    del corte se guarda en session_state y se compara contra los bounds
    del `st.date_input`, que son `datetime.date`: un Timestamp o un
    numpy.datetime64 ahí adentro rompe la comparación en silencio."""
    if isinstance(valor, datetime.datetime):
        return valor.date()
    if isinstance(valor, datetime.date):
        return valor
    # numpy.datetime64 / pandas.Timestamp: ambos exponen .date() tras
    # pasar por astype('M8[D]').item() o .to_pydatetime(); el camino corto
    # que sirve para los dos es str → fromisoformat de los 10 primeros.
    return datetime.date.fromisoformat(str(valor)[:10])


@lru_cache(maxsize=32)
def _cortes_desde_dias(dias):
    """Núcleo cacheado de `cortes_disponibles`. Recibe una TUPLA de
    `datetime.date` (hashable) para que el resultado se reuse entre
    reruns de Streamlit sin recalcular las rachas en cada interacción de
    la franja. `lru_cache` y no `st.cache_data` a propósito: este módulo
    no importa streamlit (ver docstring)."""
    salida = []
    for i, racha in enumerate(_rachas(list(dias))):
        salida.append({
            "clave": f"corte_{i:03d}",
            "etiqueta": etiqueta_corte(racha[0], racha[-1]),
            "etiqueta_anio": etiqueta_corte_anio(racha[0], racha[-1]),
            "dias": tuple(racha),
            "ini": racha[0],
            "fin": racha[-1],
            "n_dias": len(racha),
        })
    return tuple(salida)


def cortes_disponibles(fechas, maximo=None):
    """Los cortes presentes en `fechas` (Series de pandas), del más
    antiguo al más nuevo, como dicts con clave/etiqueta/dias/ini/fin.

    `maximo` recorta a los N más RECIENTES (los últimos del listado): la
    franja ofrece un puñado, no los tres años del parquet.

    Devuelve una lista vacía si no hay fechas — quien llama decide si eso
    significa "no mostrar el modo Cortes".
    """
    if fechas is None or len(fechas) == 0:
        return []
    _unicos = fechas.dropna()
    if _unicos.empty:
        return []
    _dias = tuple(sorted({_a_date(d) for d in _unicos.dt.normalize().unique()}))
    _todos = _cortes_desde_dias(_dias)
    if maximo is not None and len(_todos) > maximo:
        _todos = _todos[-maximo:]
    return [dict(c) for c in _todos]


# ── LAS SESIONES DE INVENTARIO: cierres de mes y parciales (regla #632) ────
# Lo que eligen las vistas de Ajuste que miran UNA sesión (Por familia,
# Familia × Área, Distribución). Parten de las mismas rachas que los cortes
# y les agregan lo que el usuario definió el 2026-10-11: «el cierre de mes
# ocurre entre el día 1 hasta el día 7 inclusive, y uno parcial es fuera de
# esas fechas». De ahí dos cosas que una racha sola no sabe:
#
#   · QUÉ ES: una racha que toca del día 1 al 7 es el CIERRE del mes
#     anterior —el mismo corrimiento que `fecha_operativa`—; las demás son
#     PARCIALES.
#   · QUÉ SE JUNTA: los conteos del 1 al 7 de un mismo mes son UN cierre
#     aunque las rachas los separen. Setiembre 2026 se contó el 1 de
#     octubre (12 áreas) y Venta interna se recontó el 6: sin juntarlos, el
#     último «cierre» era el del 6, con un área y dos productos, y la vista
#     abría ahí.
#
# Medido sobre las 60 rachas de nov 2023 a oct 2026: 36 cierres, uno por mes
# sin huecos ni repetidos, y 22 parciales.


def _es_del_cierre(d):
    return d.day <= DIA_CIERRE_OPERATIVO


def _mes_anterior(d):
    return (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)


def _etiqueta_dias(rachas):
    """«1 oct», «1-5 ago», «1 y 6 oct», «29 abr - 1 may y 6 may»: las rachas
    de una sesión, juntando el mes cuando todas caen en el mismo."""
    partes = [etiqueta_corte(r[0], r[-1]) for r in rachas]
    if len(rachas) > 1 and all(r[0].month == r[-1].month == rachas[0][0].month
                               for r in rachas):
        mes = MESES_ABR_ES[rachas[0][0].month - 1]
        partes = [p.rsplit(" ", 1)[0] for p in partes]
        return " y ".join(partes) + f" {mes}"
    return " y ".join(partes)


@lru_cache(maxsize=32)
def _sesiones_desde_dias(dias):
    """Núcleo cacheado de `sesiones_inventario`, con el mismo criterio que
    `_cortes_desde_dias`: una TUPLA de fechas, hashable."""
    cierres, sesiones = {}, []
    for racha in _rachas(list(dias)):
        del_cierre = [d for d in racha if _es_del_cierre(d)]
        if del_cierre:
            mes = _mes_anterior(del_cierre[0])
            if mes in cierres:
                cierres[mes].append(racha)
                continue
            cierres[mes] = [racha]
            sesiones.append(("cierre", mes, cierres[mes]))
        else:
            sesiones.append(("parcial", (racha[0].year, racha[0].month), [racha]))
    salida = []
    for tipo, (y, m), rachas in sesiones:
        todos = tuple(sorted(d for r in rachas for d in r))
        ini, fin = todos[0], todos[-1]
        dias_txt = _etiqueta_dias(rachas)
        if tipo == "cierre":
            clave = f"cierre_{y}-{m:02d}"
            nombre = f"Cierre de {MESES_LARGOS_ES[m - 1]}"
            corto = f"Cierre {MESES_ABR_ES[m - 1]} {y}"
        else:
            clave = f"parcial_{ini.isoformat()}"
            nombre = f"Parcial · {dias_txt}"
            corto = f"Parcial {dias_txt} {fin.year}"
        salida.append({
            "clave": clave, "tipo": tipo, "mes": (y, m),
            "nombre": nombre, "corto": corto,
            "etiqueta": dias_txt, "etiqueta_anio": f"{dias_txt} {fin.year}",
            "dias": todos, "ini": ini, "fin": fin,
            "n_dias": len(todos), "juntas": len(rachas),
        })
    return tuple(salida)


def sesiones_inventario(fechas):
    """Las sesiones de inventario de `fechas` (Series de pandas), de la más
    vieja a la más nueva: cada una un dict con `clave` (estable: no depende
    de cuántas hay antes), `tipo` («cierre» o «parcial»), `mes` (el mes que
    cierra, o el de la sesión si es parcial), `nombre` («Cierre de
    setiembre», «Parcial · 15-17 set»), `corto` (el del botón), `etiqueta`
    / `etiqueta_anio` (sus días: «1 y 6 oct»), `dias`, `ini`, `fin`,
    `n_dias` y `juntas` (cuántos conteos se juntaron). Lista vacía sin
    fechas."""
    if fechas is None or len(fechas) == 0:
        return []
    _f = fechas.dropna()
    if _f.empty:
        return []
    _dias = tuple(sorted({_a_date(d) for d in _f.dt.normalize().unique()}))
    return [dict(s) for s in _sesiones_desde_dias(_dias)]


def ultimo_cierre(sesiones):
    """El último cierre de mes de la lista, o la última sesión si no hay
    ningún cierre (None sin sesiones). Con él abren las vistas por sesión:
    lo que se revisa es el cierre, no el recuento suelto que vino después."""
    for s in reversed(sesiones):
        if s["tipo"] == "cierre":
            return s
    return sesiones[-1] if sesiones else None


def corte_contiguo(corte):
    """True si el corte NO tiene huecos: sus días son un intervalo
    perfecto y filtrar por rango daría exactamente lo mismo que filtrar
    por conjunto. Lo usa la UI para no prometer una precisión que en ese
    corte puntual no aporta nada."""
    return corte["n_dias"] == (corte["fin"] - corte["ini"]).days + 1
