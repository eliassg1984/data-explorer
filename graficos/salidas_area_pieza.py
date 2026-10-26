"""Salidas por Área: cadena y notas locales, mismas cuentas de referencia (#735)."""
from graficos.movil import css_movil, js_movil
import hashlib
import pickle
from pathlib import Path

import streamlit as st
import tema

from . import movimientos_bajas as mb
from . import salidas_area_datos as datos
from .drill_tablas import CSS_TITULOS_DRILL

_DIR=Path(__file__).parent
_CSS='.rqa{'+''.join(f'--{k}:{v};' for k,v in {
    'accent':tema.ACENTO,'accent-tint':tema.LAVANDA_FONDO,'text-primary':tema.TEXTO_PRINCIPAL,
    'text-secondary':tema.GRIS_TEXTO,'border':tema.GRIS_BORDE,'bg-card':tema.BLANCO,
    'saa-alza':tema.ERROR,'saa-baja':tema.AJUSTE_POS_TEXTO}.items())+'}'
_CSS+=(_DIR/'requerimientos_area.css').read_text(encoding='utf-8')+(_DIR/'salidas_area.css').read_text(encoding='utf-8')
_PIEZA=st.components.v2.component('salidas_area_735',css=css_movil(_CSS),
    js=js_movil((_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'salidas_area.js').read_text(encoding='utf-8')))


def renderizar(d,d_vent,cols,niveles,vent,*,d_ant=None,rango=None,fecha=None,nota=None,titulo='Salidas por área',rotulo_ant='',sin_comparar=(),aviso=None,contexto=None):
    entradas=mb.entradas();firma=hashlib.sha256(pickle.dumps((d,d_vent,cols,niveles,vent,d_ant,rango,nota,rotulo_ant,sin_comparar,aviso,contexto,entradas),protocol=5)).hexdigest()
    cache=st.session_state.get('_sal_area_735_cache')
    if cache is None or cache[0]!=firma:
        def lineas(raw):return datos.normalizar(raw,cols,niveles)
        cache=(firma,datos.armar(lineas(d),lineas(d_vent),entradas,vent,anterior=lineas(d_ant) if d_ant is not None else None,
            rango=rango,nota=nota,rotulo_ant=rotulo_ant,sin_comparar=sin_comparar,aviso=aviso,
            disponibles={k:c is not None and c in d for k,c in niveles.items()},contexto=contexto))
        st.session_state['_sal_area_735_cache']=cache
    st.markdown(CSS_TITULOS_DRILL+'<style>.st-key-ajuste_graf_card_izq_mov_sal_area{height:auto!important;max-height:none!important;overflow:visible!important}</style>',unsafe_allow_html=True)
    with st.container(border=True,key='ajuste_graf_card_izq_mov_sal_area'):
        cab=f'<div class="inv-rank-tit">{titulo}</div>'
        if fecha is not None:fecha(cab)
        else:st.markdown(cab,unsafe_allow_html=True)
        _PIEZA(key='salidas_area_pieza',data=cache[1],width='stretch')
