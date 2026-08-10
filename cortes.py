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


def corte_contiguo(corte):
    """True si el corte NO tiene huecos: sus días son un intervalo
    perfecto y filtrar por rango daría exactamente lo mismo que filtrar
    por conjunto. Lo usa la UI para no prometer una precisión que en ese
    corte puntual no aporta nada."""
    return corte["n_dias"] == (corte["fin"] - corte["ini"]).days + 1
