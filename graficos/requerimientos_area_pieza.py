"""Requerimientos por Área nativo: jerarquía, productos y ficha locales (#734)."""
import hashlib
import pickle
from pathlib import Path

import streamlit as st
import tema

from . import movimientos_requerimientos as mr
from . import requerimientos_area_datos as datos

_DIR=Path(__file__).parent
_CSS='.rqa{'+''.join(f'--{k}:{v};' for k,v in {
    'accent':tema.ACENTO,'accent-tint':tema.LAVANDA_FONDO,'text-primary':tema.TEXTO_PRINCIPAL,
    'text-secondary':tema.GRIS_TEXTO,'border':tema.GRIS_BORDE,'bg-card':tema.BLANCO}.items())+'}'
_CSS+=(_DIR/'requerimientos_area.css').read_text(encoding='utf-8')
_PIEZA=st.components.v2.component('requerimientos_area_734',css=_CSS,
    js=(_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'requerimientos_area.js').read_text(encoding='utf-8'))


def renderizar(d,d_vent,cols,cols_marcas,vent,*,unidades=None,rango=None,fecha=None,nota=None,titulo='Requerido por sub almacén',contexto=None):
    kx=mr.pedido_y_salida();firma=hashlib.sha256(pickle.dumps((d,d_vent,cols,cols_marcas,vent,unidades,kx,rango,nota,contexto),protocol=5)).hexdigest()
    cache=st.session_state.get('_req_area_734_cache')
    if cache is None or cache[0]!=firma:
        def lineas(raw):return datos.normalizar(raw,cols,mr.marcas_de(raw,**cols_marcas),unidades)
        cache=(firma,datos.armar(lineas(d),lineas(d_vent),vent,kx,rango=rango,nota=nota,contexto=contexto))
        st.session_state['_req_area_734_cache']=cache
    st.markdown(mr.CSS_TITULOS_DRILL+'<style>.st-key-ajuste_graf_card_izq_mov_req_area{height:auto!important;max-height:none!important;overflow:visible!important}</style>',unsafe_allow_html=True)
    with st.container(border=True,key='ajuste_graf_card_izq_mov_req_area'):
        cab=f'<div class="inv-rank-tit">{titulo}</div>'
        if fecha is not None:fecha(cab)
        else:st.markdown(cab,unsafe_allow_html=True)
        _PIEZA(key='requerimientos_area_pieza',data=cache[1],width='stretch')
