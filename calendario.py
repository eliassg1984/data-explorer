"""
calendario — calendario propio de DOS meses para el rango de la franja.

Por qué existe
--------------
`st.date_input` con rango dibuja UN solo mes y no hay CSS que lo desdoble:
es un componente React ya compilado que Streamlit trae hecho. Para mostrar
dos meses lado a lado hay que dibujar la grilla nosotros, con un `st.button`
por día.

Cómo se integra con el estado
-----------------------------
NO escribe `st.session_state` directamente: todo pasa por `estado_rango`
(ver su "Regla de oro"). El clic de un día llama a `aplicar_clic_dia` como
callback `on_click`, que implementa la máquina de dos clics y solo publica
el rango cuando ya hay dos fechas.

Dos restricciones que condicionan el diseño
-------------------------------------------
1. Streamlit admite UN solo nivel de anidado de `st.columns`. Este
   calendario se dibuja dentro de la columna derecha del popover, así que
   ya está en el nivel permitido: no se puede hacer `columns(2)` (un mes en
   cada una) y dentro `columns(7)` (los días). Por eso los dos meses
   comparten una fila de 15 columnas: 7 días + separador + 7 días.

2. Se dibuja una `st.columns` por SEMANA, no una sola para todo el mes.
   Apilar los días dentro de cada columna era más simple, pero cualquier
   diferencia de alto entre un botón y un hueco se acumulaba y las semanas
   terminaban desfasadas. Con una fila por semana, cada fila es su propio
   flex row y no puede desalinearse.

El gap de `st.columns` (1rem aun con `gap="small"`) se aprieta por CSS en
`estilos/_65_calendario_doble.py`: con 15 columnas se comía ~224px y los
números de dos dígitos se partían en dos líneas.
"""

import calendar as _cal
import datetime

import streamlit as st

from estado_rango import aplicar_clic_dia, clave_borrador
from graficos.compras._comun import _es_movil

_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
_DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]


def _sumar_meses(d, n):
    """`d` desplazado `n` meses, siempre al día 1."""
    total = (d.year * 12 + (d.month - 1)) + n
    return datetime.date(total // 12, total % 12 + 1, 1)


def _semanas(anio, mes):
    """Matriz de semanas del mes; 0 = celda vacía (lunes primero)."""
    return _cal.Calendar(firstweekday=0).monthdayscalendar(anio, mes)


def _rango_vigente(clave):
    """(ini, fin) del rango publicado, o (None, None) si está incompleto."""
    cur = st.session_state.get(clave)
    if isinstance(cur, (tuple, list)) and len(cur) == 2 and all(cur):
        return cur[0], cur[1]
    return None, None


def render_calendario_doble(clave, bounds, reporte=None,
                            usa_carga_rango=False, prefijo="cal",
                            meses=None):
    """Dibuja el calendario y devuelve el ancla (mes izquierdo).

    `clave` es la clave canónica del rango (de `estado_rango.clave_rango`).
    `bounds` = (min, max) de la data: los días fuera quedan deshabilitados.
    `meses` fuerza 1 ó 2 meses; por defecto 1 en móvil y 2 en desktop —
    dos meses son 14 columnas de días y en un teléfono quedan ilegibles.
    """
    if meses is None:
        meses = 1 if _es_movil() else 2
    dos = (meses >= 2)
    min_b, max_b = bounds if (bounds and all(bounds)) else (None, None)
    ini, fin = _rango_vigente(clave)
    pendiente = st.session_state.get(clave_borrador(clave))

    # Ancla = mes que se muestra a la IZQUIERDA. Arranca en el mes del
    # inicio del rango para que el usuario vea de entrada lo que ya eligió.
    k_ancla = f"{prefijo}_ancla_{clave}"
    if k_ancla not in st.session_state:
        base = ini or max_b or datetime.date.today()
        st.session_state[k_ancla] = base.replace(day=1)
    ancla = st.session_state[k_ancla]

    izq, der = ancla, _sumar_meses(ancla, 1)

    # ── Cabecera: navegación + nombres de los dos meses ──────────────────
    # Los límites de navegación se calculan contra los bounds de la data:
    # no tiene sentido pasear por meses sin datos.
    _ultimo = der if dos else izq
    _puede_atras = (min_b is None) or (izq > min_b.replace(day=1))
    _puede_adel = (max_b is None) or (_ultimo < max_b.replace(day=1))

    _hcols = [0.6, 4, 4, 0.6] if dos else [0.6, 4, 0.6]
    _h = st.columns(_hcols)
    with _h[0]:
        if st.button("‹", key=f"{prefijo}_prev_{clave}",
                     disabled=not _puede_atras, help="Mes anterior",
                     use_container_width=True):
            st.session_state[k_ancla] = _sumar_meses(ancla, -1)
            st.rerun()
    with _h[1]:
        st.markdown(
            f"<div class='cal-mes'>{_MESES[izq.month - 1]} {izq.year}</div>",
            unsafe_allow_html=True)
    if dos:
        with _h[2]:
            st.markdown(
                f"<div class='cal-mes'>{_MESES[der.month - 1]} "
                f"{der.year}</div>", unsafe_allow_html=True)
    with _h[-1]:
        if st.button("›", key=f"{prefijo}_next_{clave}",
                     disabled=not _puede_adel, help="Mes siguiente",
                     use_container_width=True):
            st.session_state[k_ancla] = _sumar_meses(ancla, 1)
            st.rerun()

    # ── Grilla, FILA POR FILA ────────────────────────────────────────────
    # Una `st.columns` por SEMANA, no una sola para todo el mes. Apilar los
    # días dentro de cada columna parecía más simple, pero cualquier
    # diferencia de alto entre un botón y un hueco se acumulaba y las
    # semanas terminaban desfasadas entre sí. Con una fila por semana, cada
    # fila es su propio flex row y no puede desalinearse.
    _spec = ([1] * 7 + [0.3] + [1] * 7) if dos else [1] * 7
    _off_der = 8

    hoy = datetime.date.today()
    sem_izq = _semanas(izq.year, izq.month)
    sem_der = _semanas(der.year, der.month) if dos else []

    def _celda(col, mes, dia):
        with col:
            if dia == 0:
                st.markdown("<div class='cal-hueco'></div>",
                            unsafe_allow_html=True)
                return
            fecha = datetime.date(mes.year, mes.month, dia)
            fuera = ((min_b is not None and fecha < min_b) or
                     (max_b is not None and fecha > max_b))

            # Estado → sufijo de key. El CSS pinta por sufijo, mismo
            # patrón que los chipwrap_*_on del proyecto.
            if pendiente is not None:
                extremo = (fecha == pendiente)
                dentro = False
            else:
                extremo = fecha in (ini, fin)
                dentro = bool(ini and fin and ini < fecha < fin)
            suf = "_sel" if extremo else ("_rng" if dentro else "")
            if fecha == hoy and not extremo:
                suf += "_hoy"

            st.button(
                str(dia),
                key=f"{prefijo}d_{clave}_{fecha.isoformat()}{suf}",
                disabled=fuera,
                use_container_width=True,
                on_click=aplicar_clic_dia,
                args=(clave, fecha, reporte, usa_carga_rango),
            )

    # Cabecera de días de la semana (su propia fila)
    _hd = st.columns(_spec, gap="small")
    for _off in ((0, _off_der) if dos else (0,)):
        for _j, _d in enumerate(_DIAS):
            with _hd[_off + _j]:
                st.markdown(f"<div class='cal-dow'>{_d}</div>",
                            unsafe_allow_html=True)

    # Los meses no tienen la misma cantidad de semanas: se itera al mayor y
    # el que se queda corto rellena con huecos.
    for _r in range(max(len(sem_izq), len(sem_der) if dos else 0)):
        _fila = st.columns(_spec, gap="small")
        _sem = sem_izq[_r] if _r < len(sem_izq) else [0] * 7
        for _j in range(7):
            _celda(_fila[_j], izq, _sem[_j])
        if dos:
            _sem2 = sem_der[_r] if _r < len(sem_der) else [0] * 7
            for _j in range(7):
                _celda(_fila[_off_der + _j], der, _sem2[_j])

    # Pista del estado de la selección: sin esto, tras el primer clic no hay
    # nada que explique por qué el rango todavía no cambió.
    if pendiente is not None:
        st.markdown(
            f"<div class='cal-pista'>Inicio "
            f"<b>{pendiente:%d/%m/%Y}</b> — elegí la fecha de fin</div>",
            unsafe_allow_html=True)
    elif ini and fin:
        st.markdown(
            f"<div class='cal-pista'>{ini:%d/%m/%Y} → {fin:%d/%m/%Y}</div>",
            unsafe_allow_html=True)

    return ancla
