"""Montaje de Control de pedidos. Fecha nativa, demás controles locales (#723)."""
from pathlib import Path

import streamlit as st

import data
from . import ventas_control as vc
from . import ventas_control_datos as datos

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component(
    'ventas_control',css=(_DIR/'ventas_control.css').read_text(encoding='utf-8'),
    js=(_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'ventas_control.js').read_text(encoding='utf-8'))


def renderizar(cortesias=frozenset(),canales=()):
    ss=st.session_state
    if ss.pop('vt_ctl_fecha_flag',False):
        vc.preservar_widgets(vc._KEYS_WIDGET_CTL)
        st.rerun(scope='app')
    ini,fin=vc._rango();turno=data.venta_por_turno()
    clave=(data.sello_datos(vc.ARCH_PEDIDOS),data.sello_datos(vc.ARCH_TRANSACCIONES),
           ini,fin,turno,tuple(sorted(canales)),tuple(sorted(cortesias)))
    cache=ss.get('_vt_ctl_pieza_cache')
    st.markdown('''<style>
    .st-key-vt_ctl_nativa{position:relative;gap:0!important}
    .st-key-vt_ctl_nativa_fecha{position:absolute;right:18px;top:12px;z-index:5;width:auto!important}
    .st-key-vt_ctl_nativa_fecha button[data-testid="stPopoverButton"]{
        height:25px!important;min-height:25px!important;min-width:0!important;
        padding:0 9px!important;border-radius:7px!important}
    .st-key-vt_ctl_nativa_fecha button[data-testid="stPopoverButton"] p{font-size:11px!important}
    .st-key-vt_ctl_nativa>[data-testid="stElementContainer"]{margin:0!important}
    </style>''',unsafe_allow_html=True)
    with st.container(key='vt_ctl_nativa'):
        with st.container(key='vt_ctl_nativa_fecha'):
            vc.selector_fecha_tarjeta('vt_ctlf','vt_ctl_fecha_flag',categoria=None,label='Elegir fechas')
        if cache is None or cache[0]!=clave:
            with st.spinner('Preparando pedidos y transacciones…'):
                p,t=vc._cargar(ini,fin,turno,canales)
                cache=(clave,datos.armar(p,t,(ini,fin),turno=turno,canales=canales,cortesias=cortesias))
                # Un fallo de fuente no queda pegado en la caché de sesión.
                if p is not None and t is not None:
                    ss['_vt_ctl_pieza_cache']=cache
        mensaje=dict(cache[1])
        mensaje['inicial']=dict(gran=ss.get('vt_ctl_gran','Día'),sub=ss.get('vt_ctl_sub','Anulaciones'))
        _PIEZA(key='vt_ctl_pieza',data=mensaje,width='stretch')
