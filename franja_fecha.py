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
(Hasta la regla #783; desde ese día la franja dibuja el panel de las
tarjetas y ya no hay `date_input`, pero sigue siendo una sola llamada.)
El `st.date_input` de aca usaba como KEY la clave canonica del rango
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
    """Dibuja el botón de fecha de la franja y su panel con el contexto
    publicado.

    Se llama UNA sola vez por render, desde `app.py`. Llamarlo dos veces =
    dos widgets con la misma key = excepcion de Streamlit, que es
    exactamente la red de seguridad que queremos.

    EL MISMO PANEL QUE LAS TARJETAS (regla #783, a pedido: «en ventas, el
    calendario no es el mismo»). Hasta ese día la franja abría su panel
    viejo —seis atajos y un `date_input` con la clave del rango— y las
    tarjetas el de `graficos/panel_fecha.py` (#616): atajos agrupados, años
    en pestañas y meses como casilleros. Sin `categoria`, el panel escribe
    la clave de la franja (`ctx["k_rango"]`) con `aplicar_atajo` y su
    `usa_carga_rango`: Ventas recarga igual que antes. Como ya no hay un
    widget con esa clave, la mantiene viva el eco de `estado_rango`. El
    contenedor conserva su key, que es de donde cuelga su lugar en la
    franja (`_90_marco.py`).
    """
    ctx = st.session_state.get(_CLAVE_CTX)
    if not ctx:
        return
    # Adentro: `graficos.base` importa este módulo.
    from graficos.base import selector_fecha_tarjeta
    with st.container(key="fecha_ajuste_pill"):
        selector_fecha_tarjeta("franja_f", None, ctx=ctx)
