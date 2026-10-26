"""Destino de cada producto: tabla, ficha y cierres nativos (#737)."""
from graficos.movil import css_movil, js_movil
import hashlib
import json
import pickle
from pathlib import Path

import streamlit as st

from . import destino_datos as datos
from . import movimientos_destino as md

_DIR=Path(__file__).parent
_CSS=md._CSS.replace('<style>','').replace('</style>','')+(_DIR/'destino.css').read_text(encoding='utf-8')+(_DIR/'destino_flujo.css').read_text(encoding='utf-8')
_PIEZA=st.components.v2.component('destino_producto_737',css=css_movil(_CSS),
    js=js_movil((_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'destino_base.js').read_text(encoding='utf-8')+(_DIR/'destino_flujo.js').read_text(encoding='utf-8')+(_DIR/'destino_producto.js').read_text(encoding='utf-8')))


def renderizar(fam_sel=()):
    fuente=md._cargar(fam_sel)
    if fuente is None:
        md._vacia(md.CARD_PRODUCTO,'En qué se fue cada producto',md._SIN_DATOS);return
    per,filas,tot=fuente;ss=st.session_state
    contexto={'Familias de la página':list(fam_sel),'Ámbito':'Restaurante entero; no aplica el filtro de subalmacén'}
    firma=hashlib.sha256(pickle.dumps((per,filas,tot,contexto),protocol=5)).hexdigest();cache=ss.get('_destino_producto_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(per,filas,tot,contexto));ss['_destino_producto_cache']=cache
    P=dict(cache[1]);P['parte']='producto'
    P['inicial']=dict(k=md._k_elegido(md.K_CIERRE_2,per),cod=ss.get(md._K_FOCO),
        grupo='operacion' if ss.get(md.K_GRUPO)==md.GRUPOS[1] else 'alimentos',
        filtro=md.FILTROS.index(ss.get(md.K_FILTRO)) if ss.get(md.K_FILTRO) in md.FILTROS else 0,
        medida='q' if ss.get(md.K_MEDIDA)==md.MEDIDAS[1] else 'v',q=ss.get(md.K_BUSCAR) or '')
    P['comun']=json.dumps([P['inicial'],ss.get(md._K_SALTO,0)],ensure_ascii=False)
    st.markdown('<style>.st-key-ajuste_graf_card_izq_mov_destino{height:auto!important;max-height:none!important;overflow:visible!important}</style>',unsafe_allow_html=True)
    with st.container(border=True,key=md.CARD_PRODUCTO):
        _PIEZA(key='destino_producto_pieza',data=P,width='stretch')
