"""
pestillos — el estado de los dos rails plegables, con un solo dueño.

La app tiene dos rails fijos: el de NAVEGACIÓN a la izquierda
(`navegacion.py`, key `nav_rail`) y el de VISTAS a la derecha
(`graficos/base.py::_render_rail`, key `compras_tabs_row`). Entre los dos
se comen ~240px de ancho que la tarjeta principal no puede usar. Este
módulo es el interruptor: guarda si cada uno está plegado, dibuja su
pestillo y deja en el DOM el marcador que el CSS necesita para verlo.

Mismo patrón que `estado_rango.py` con el eje temporal: el estado tiene UN
dueño y nadie escribe sus claves de `session_state` por fuera.

CÓMO FUNCIONA — y por qué el plegado es CSS y no Python
-------------------------------------------------------
El pestillo NO deja de renderizar los botones del rail: los esconde con
CSS. Es deliberado, y es la regla de siempre en este proyecto: *un widget
que deja de renderizarse pierde su estado* (ver CLAUDE.md § Streamlit).
Si al plegar dejáramos de dibujar los `st.button` del rail, Streamlit
olvidaría la vista seleccionada y al desplegar volveríamos a la primera.

Y el reparto de trabajo entre Python y CSS es el mismo que el de los altos
(`graficos/alturas.py` § LA RESTA NO SE HACE ACÁ, regla #117): Python solo
dice *plegado sí/no*; el ancho, las restas y el reflujo los hace el
navegador, que es el único que conoce el viewport real.

DOS GESTOS, DOS COMPORTAMIENTOS
-------------------------------
    Cursor sobre la lengüeta → VISTAZO: el rail se despliega SUPERPUESTO
                               sobre la tarjeta. Es `:hover` puro, sin
                               rerun, y no mueve nada de sitio.
    Clic en el pestillo      → FIJA: el rail se pliega/despliega de verdad
                               y la tarjeta se ensancha o se encoge.

Es el patrón de VS Code / Notion: mirar es gratis, mover cuesta un clic.

EL MARCADOR
-----------
`marcar()` emite un `<style class="rail-izq-plegado">` VACÍO. No lleva
reglas: es una bandera para que el CSS de `estilos/_25_rails_pestillo.py`
la encuentre con `:has()` y redefina `--rail-izq-w`. Se eligió un `<style>`
y no un `<div>` porque su contenedor lo esconde una regla que ya existía
(`navegacion.py`, "colapsar los contenedores invisibles"), así que el
marcador no aporta ni un píxel de alto al bloque donde caiga.
"""

import streamlit as st

IZQ = "izq"
DER = "der"

_CLAVE = {IZQ: "_rail_izq_plegado", DER: "_rail_der_plegado"}


def plegado(lado):
    """True si ese rail está plegado (fijado por el pestillo)."""
    return bool(st.session_state.get(_CLAVE[lado], False))


def _alternar(lado):
    """Callback del pestillo: corre ANTES del rerun, así el marcador y el
    CSS salen ya en el render de este mismo clic (sin doble render)."""
    st.session_state[_CLAVE[lado]] = not plegado(lado)


def marcar(lado):
    """Deja el marcador invisible en el DOM si ese rail está plegado.

    Se llama en CADA render (no lleva guard de "inyectar una sola vez":
    esos desaparecen en el rerun siguiente — regla #59)."""
    if plegado(lado):
        st.markdown(f'<style class="rail-{lado}-plegado"></style>',
                    unsafe_allow_html=True)


def pestillo(lado, key):
    """Dibuja el pestillo del rail. Va DENTRO del contenedor del rail, así
    al plegarse queda él como única cosa visible (la lengüeta).

    El chevron apunta a dónde va a ir el rail si lo pulsas, no a dónde
    está: plegado el izquierdo, apunta a la derecha (= "sácame")."""
    abierto = not plegado(lado)
    if lado == IZQ:
        icono = "chevron_left" if abierto else "chevron_right"
    else:
        icono = "chevron_right" if abierto else "chevron_left"
    st.button(
        f":material/{icono}:",
        key=key,
        help=("Plegar el panel" if abierto else "Fijar el panel abierto"),
        on_click=_alternar,
        args=(lado,),
    )
