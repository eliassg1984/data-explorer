"""La cabecera de Documentos SUNAT, la misma en las cuatro vistas (regla #762).

Hasta ese día la tarjeta abría con selectores anchos sin rótulo («Todos»), las
vistas sólo se veían al pasar el cursor por el menú y el aviso del Control
quedaba suelto, afuera de la tarjeta. A pedido, como en el boceto:

  · Primera fila: las vistas, el aviso del Control y la fecha.
  · Segunda fila: los filtros, cada uno diciendo qué es, y sus botones.

Las pestañas escriben el mismo `state_key` que el rail (`K_VISTA`): son otra
puerta a la misma vista, no un estado aparte. El CSS vive en `estilos/_30_filtros.py`.
"""
import streamlit as st

from . import _sunat_vistas as sv

_SLUG = {sv.VISTA_CRUCE: "cruce", sv.VISTA_PROV: "prov", sv.VISTA_DOCS: "docs", sv.VISTA_CONTROL: "control"}
_MES_TXT = {"Todos": "todos", "Mes presentado": "presentado", "Mes abierto": "abierto"}


def _ir(vista):
    st.session_state[sv.K_VISTA] = vista


def _aviso(vista):
    """El botón del Control: quien mira un total se entera de lo que le falta."""
    import sunat_control

    from .sunat_control_pieza import texto_aviso
    t = texto_aviso(sunat_control.leer_control())
    if not t:
        return
    clave = "sunat_sello_grave" if t[1] else "sunat_sello_ok" if t[0].startswith("✓") else "sunat_sello_ojo"
    # En «Control» ya se está viendo: el aviso no lleva a ningún lado.
    st.button(t[0], key=clave, type="tertiary", disabled=vista == sv.VISTA_CONTROL,
              on_click=_ir, args=(sv.VISTA_CONTROL,), help="Abre el control con SUNAT")


def fila_vistas(vista, fecha=None):
    """Las vistas, el aviso y, si la vista la usa, la fecha."""
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="sunat_cab_fila1"):
        with st.container(horizontal=True, vertical_alignment="center", gap=None, key="sunat_cab_vistas"):
            for v in sv.VISTAS:
                st.button(v, key=f"sunat_tab_{_SLUG[v]}", type="primary" if v == vista else "secondary",
                          on_click=_ir, args=(v,))
        _aviso(vista)
        if fecha:
            with st.container(key="sunat_cab_fecha"):
                fecha()


def selector_mes(opciones, ayuda):
    """«Mes en SUNAT: todos». El valor del widget es el de siempre."""
    return st.selectbox("Mes en SUNAT", list(opciones), key="sunat_mes_sunat", label_visibility="collapsed", help=ayuda,
                        format_func=lambda x: f"Mes en SUNAT: {_MES_TXT.get(x, x)}")
