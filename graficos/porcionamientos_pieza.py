"""Porcionamientos nativo; fecha y valorización compartida siguen en Python (#728)."""
from graficos.movil import css_movil, js_movil
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from . import movimientos_merma as mm
from . import porcionamientos_datos as datos

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component('porcionamientos_periodo',
    css=css_movil((_DIR/'movimientos_periodo.css').read_text(encoding='utf-8')),
    js=js_movil((_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'movimientos_periodo.js').read_text(encoding='utf-8')))


def _huella(d):
    return hashlib.sha256(pd.util.hash_pandas_object(d,index=True).values.tobytes()).hexdigest() if d is not None else None


def renderizar(d,cols,*,precios=None,control=None,rango=None,fecha=None):
    if not all(cols.get(k) for k in ['fecha','cant','merma']):
        st.info('Faltan columnas de Fecha, Cantidad o Merma para los porcionamientos.')
        return
    ss=st.session_state
    modo=('hoy' if mm.valorizacion()==mm.VALOR_HOY else 'dia') if control else ('hoy' if precios is not None else 'dia')
    actual=precios if precios is not None else mm.precios_hoy()
    contexto={'Áreas de la página':ss.get('mov_graf_filtro_sub') or []}
    firma=(_huella(d),tuple(cols.items()),_huella(actual),str(rango),str(contexto))
    cache=ss.get('_porcionamientos_pieza_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(d,cols,precios=actual,modo=modo,rango=rango,contexto=contexto));ss['_porcionamientos_pieza_cache']=cache
    P=datos.valorar(cache[1],modo);P['inicial']=dict(gran=ss.get('mov_pporc_gran','Semana'),area=ss.get('mov_pporc_areas') or [],
                                       tipo=ss.get('mov_pporc_tipos') or [],prod=ss.get('mov_pporc_productos') or [])
    extra=36 if control else 0
    st.markdown(f'''<style>
    .st-key-mov_pporc_nativa{{position:relative;gap:0!important;--mv-control-alto:{extra}px}}
    .st-key-mov_pporc_nativa_fecha{{position:absolute;right:18px;top:{extra+12}px;z-index:5;width:auto!important}}
    .st-key-mov_pporc_nativa_valor{{height:36px;min-height:36px;margin:0!important}}
    .st-key-mov_pporc_nativa>[data-testid="stElementContainer"]{{margin:0!important}}
    </style>''',unsafe_allow_html=True)
    with st.container(key='mov_pporc_nativa'):
        if control:
            with st.container(key='mov_pporc_nativa_valor',horizontal=True,vertical_alignment='center',gap='small'):
                st.markdown('<span style="font-size:11px" title="Compartida con Rendimiento y Para revisar">Valorizar</span>',unsafe_allow_html=True)
                control()
        if fecha:
            with st.container(key='mov_pporc_nativa_fecha'):fecha()
        _PIEZA(key='porcionamientos_periodo_pieza',data=P,width='stretch')
