"""Rendimiento nativo, valorización y foco compartidos (#730)."""
import json
from pathlib import Path

import streamlit as st

from . import movimientos_merma as mm
from . import merma_rendimiento_datos as datos

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component('merma_rendimiento',
    css=(_DIR/'merma_rendimiento.css').read_text(encoding='utf-8'),
    js=(_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'merma_rendimiento.js').read_text(encoding='utf-8'))


def _producto():
    ss=st.session_state;v=(ss.get('merma_rendimiento_pieza') or {}).get('producto');cache=ss.get('_merma_rendimiento_cache')
    if not isinstance(v,dict) or not cache or v.get('sello')!=cache[1]['sello']:
        return
    cod=v.get('cod');unid=v.get('unid')
    if not isinstance(cod,str) or not isinstance(unid,str) or not any(r['cod']==cod and r['unid']==unid for r in cache[1]['productos']):
        return
    ss['_merma_rendimiento_unid']=unid
    if ss.get(mm._K_PROD)!=cod:
        ss[mm._K_PROD]=cod;mm._avisar_a(mm.SEC_PROV)


def renderizar(d_hist,cols,rango):
    ss=st.session_state;precios=mm.precios_hoy();compras=mm._compras()
    contexto={'Áreas de la página':ss.get('mov_graf_filtro_sub') or []}
    firma=(datos.huella(d_hist),tuple(cols.items()),datos.huella(precios),datos.huella(compras),str(rango),str(contexto))
    cache=ss.get('_merma_rendimiento_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(d_hist,cols,precios,compras,rango=rango,contexto=contexto));ss['_merma_rendimiento_cache']=cache
    P=dict(cache[1]);P['modo']='hoy' if mm.valorizacion()==mm.VALOR_HOY else 'dia'
    P['salto']=ss.get('_merma_rend_salto',0)
    P['comun']=json.dumps([ss.get(mm._K_PROD),ss.get(mm.K_CORTE),ss.get(mm.K_MODO),P['salto']],ensure_ascii=False)
    P['inicial']=dict(cod=ss.get(mm._K_PROD),unid=ss.get('_merma_rendimiento_unid'),corte=ss.get(mm.K_CORTE),
                      ventana=ss.get('mov_merma_rend_ventana','12 meses'),precio=ss.get(mm.K_MODO,mm.MODO_CORTE),
                      lista=ss.get(mm.K_LISTA,mm.LISTA_CORTES))
    st.markdown('''<style>.st-key-merma_rend_nativa{gap:0!important}
    .st-key-merma_rend_control{height:36px;min-height:36px;margin:0!important}
    .st-key-merma_rend_nativa>[data-testid="stElementContainer"]{margin:0!important}</style>''',unsafe_allow_html=True)
    with st.container(key='merma_rend_nativa'):
        with st.container(key='merma_rend_control',horizontal=True,vertical_alignment='center',gap='small'):
            st.markdown('<span style="font-size:11px">Valorizar</span>',unsafe_allow_html=True)
            mm.control_valorizacion('mov_merma_rend_ctl')
        _PIEZA(key='merma_rendimiento_pieza',data=P,width='stretch',on_producto_change=_producto)
