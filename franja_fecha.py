"""franja_fecha - el pill de fecha de la franja superior, y su panel.

Vivia embebido en `app.py` (126 lineas dentro de `with col_fecha_top:`).
Se saco a este modulo el 2026-08-21 para poder dibujarlo en OTRO sitio sin
duplicarlo: el drill de Documentos SUNAT lo quiere DENTRO de su tarjeta,
porque ahi la fecha no es contexto global sino EL filtro de la tabla.
Desde el 2026-10-11 esa tarjeta usa el panel de las demas
(`selector_fecha_tarjeta`, regla #633): hoy `render()` lo llama solo la
franja de `app.py`, en los reportes que no eligen la fecha por vista.

POR QUE HUBO QUE MOVER LA LLAMADA Y NO COPIAR EL WIDGET
------------------------------------------------------
El `st.date_input` de aca usa como KEY la clave canonica del rango
(`clave_rango(...)`). O sea el widget NO es una copia del estado: ES el
estado. De ahi que no se pueda tener dos:

  · Dos widgets no pueden compartir key en Streamlit.
  · Y escribir esa clave desde afuera despues de instanciar el widget tira
    `StreamlitAPIException`.

Asi que "mover la fecha" sólo puede significar mover la LLAMADA. Este
modulo existe para que la misma llamada se pueda hacer desde dos sitios,
uno por render — nunca los dos a la vez.

EL CONTEXTO SE PUBLICA, NO SE PASA POR PARAMETRO
------------------------------------------------
El panel necesita valores que solo `app.py` conoce (bounds de la data, la
clave del rango, los defaults...). Enhebrarlos
por la firma del dispatcher hasta el drill serian tres capas de
parametros que ninguna otra vista usa. En su lugar `app.py` los PUBLICA
con `publicar()` y quien dibuje llama a `render()` — el mismo patron que
ya usa `graficos.base.publicar_contexto_ia()` para el asistente.
"""

import streamlit as st

from estado_rango import atajos_rango, aplicar_atajo
from cortes import MESES_ABR_ES

_CLAVE_CTX = "_franja_fecha_ctx"

# La lista de meses de todo el repo (regla #241). Hasta el 2026-10-08 había
# acá una propia que decía «sep» mientras las tablas decían «set»; el panel
# nuevo del selector de fecha (regla #616) dejó a la vista las dos a la vez.
_MESES_ES = MESES_ABR_ES


def fmt_rango_es(ini, fin):
    """Label en español de un rango de fechas. ABREVIADO a propósito.

    Nace como el label del pill de la franja (de ahí el acoplamiento de
    ancho que explica el párrafo de abajo) y se PROMUEVE a público
    2026-08-25 para que el detalle de fecha del popover de escala del
    Ranking de Proveedores (`proveedor.py`) lo reuse en vez de reinventar
    el mismo formato en dos lugares — mismo criterio que `contexto()`.

    Hasta 2026-08-09 devolvía el mes completo y el año en los dos extremos
    ("1 Agosto 2026 - 5 Agosto 2026", hasta 37 caracteres). El pill ahora
    tiene ANCHO FIJO (estilos/_50_fecha.py, bloque min-width:901px) porque
    los chips se anclan justo a su derecha con un left: en px — y un left
    fijo solo funciona si el ancho del vecino es predecible. Con mes
    abreviado y el año una sola vez cuando coincide, el peor caso
    ("30 sep 2025 – 31 dic 2026") entra en los 210px del pill; con el
    formato viejo no entraba y el texto se cortaba con ellipsis.
    Si se vuelve al formato largo hay que volver a centrar los chips o
    ensanchar el pill — no es solo cosmético. Esa restricción es SOLO del
    pill de la franja: un llamador nuevo (sin vecino anclado en px) puede
    reusar la función sin heredar el problema."""
    if ini == fin:
        return f"{ini.day} {_MESES_ES[ini.month - 1]} {ini.year}"
    if ini.year == fin.year:
        return (f"{ini.day} {_MESES_ES[ini.month - 1]} – "
                f"{fin.day} {_MESES_ES[fin.month - 1]} {fin.year}")
    return (f"{ini.day} {_MESES_ES[ini.month - 1]} {ini.year} – "
            f"{fin.day} {_MESES_ES[fin.month - 1]} {fin.year}")


def publicar(**ctx):
    """`app.py` deja aca todo lo que el panel necesita para dibujarse."""
    st.session_state[_CLAVE_CTX] = ctx


def hay_contexto():
    return _CLAVE_CTX in st.session_state


def contexto():
    """El mismo dict que arma `publicar()`, para quien quiera dibujar SUS
    propios atajos en otro lugar (2026-08-23: Compras > Proveedor, dentro
    de la tarjeta de Ranking) sin reimplementar `atajos_rango()`/
    `aplicar_atajo()` a mano ni duplicar el contexto. `None` si `app.py`
    todavía no publicó (no debería pasar dentro de un reporte real, pero
    mejor `None` explícito que un KeyError críptico)."""
    return st.session_state.get(_CLAVE_CTX)


def render():
    """Dibuja el pill + su panel con el contexto publicado.

    Se llama UNA sola vez por render, desde `app.py` (franja) o desde el
    drill que se lo quede. Llamarlo dos veces = dos widgets con la misma
    key = excepcion de Streamlit, que es exactamente la red de seguridad
    que queremos.
    """
    ctx = st.session_state.get(_CLAVE_CTX)
    if not ctx:
        return
    _k_rango_franja = ctx["k_rango"]
    fecha_min_full = ctx["fecha_min"]
    fecha_max_full = ctx["fecha_max"]
    reporte = ctx["reporte"]
    _usa_carga_rango = ctx["usa_carga_rango"]
    _hoy = ctx["hoy"]

    # El estado ya quedó sembrado y recortado por asegurar_rango()
    # arriba (una sola vez, antes del widget). Aquí solo se LEE.
    # El texto del rango es el TRIGGER de un panel (Opción B):
    # atajos rápidos a la izquierda + calendario manual a la
    # derecha. El date_input, los atajos y el label leen/escriben
    # la MISMA clave → no pueden desincronizarse.
    _rango_actual = st.session_state.get(_k_rango_franja)
    # Hasta el 2026-10-11 el label decía el CORTE cuando había uno elegido
    # («Corte 1-4 ago»): la franja tenía los modos Rango / Corte / Varios
    # para Ajuste. Ajuste pasó a una sesión por vista (regla #632) y los
    # modos se borraron (regla #635).
    if (isinstance(_rango_actual, (tuple, list))
            and len(_rango_actual) == 2 and all(_rango_actual)):
        _label_fecha = fmt_rango_es(_rango_actual[0], _rango_actual[1])
    else:
        _label_fecha = "Seleccionar rango"

    # Atajos válidos para la data actual (los calcula el dueño único).
    _atajos = atajos_rango(_hoy, (fecha_min_full, fecha_max_full))

    with st.container(key="fecha_ajuste_pill"):
        with st.popover(_label_fecha, use_container_width=False,
                        icon=":material/calendar_month:"):
            # Contenedor keyed → permite scopear el ancho del panel
            # por CSS aunque el popover se renderice en un portal.
            with st.container(key="fecha_panel"):
                _c_izq, _c_cal = st.columns([1, 1.5])
                with _c_izq:
                    st.caption("Atajos")
                    for _ca, _et, _rg in _atajos:
                        st.button(
                            _et, use_container_width=True,
                            key=f"atajo_{reporte}_{_ca}".replace(" ", "_"),
                            on_click=aplicar_atajo,
                            args=(_k_rango_franja, _rg, reporte,
                                  _usa_carga_rango),
                        )
                with _c_cal:
                    st.caption("Rango manual")
                    st.date_input(
                        "Rango a Evaluar",
                        min_value=fecha_min_full,
                        max_value=fecha_max_full,
                        format="DD/MM/YYYY",
                        key=_k_rango_franja,
                        label_visibility="collapsed",
                    )
