"""Sin plato por cierre: navegación local y salto público conservado (#736)."""
from graficos.movil import css_movil, js_movil
import hashlib
import pickle
from pathlib import Path

import streamlit as st

from . import destino_datos as datos
from . import movimientos_destino as md

_DIR=Path(__file__).parent
_CSS=md._CSS.replace('<style>','').replace('</style>','')+(_DIR/'destino.css').read_text(encoding='utf-8')
_PIEZA=st.components.v2.component('sin_plato_cierre_736',css=css_movil(_CSS),
    js=js_movil((_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'destino_base.js').read_text(encoding='utf-8')+(_DIR/'destino.js').read_text(encoding='utf-8')))


def _abrir():
    ss=st.session_state;v=(ss.get('sin_plato_cierre_pieza') or {}).get('abrir');cache=ss.get('_sin_plato_cierre_cache')
    if not isinstance(v,dict) or not cache or v.get('sello')!=cache[1]['sello']:return
    P=cache[1];k=v.get('k');cod=v.get('cod')
    if type(k) is not int or not 0<=k<len(P['periodos']) or not isinstance(cod,str):return
    ki=P['columnas'].index('k')+1;vi=P['columnas'].index('sinplato_v')+1;si=P['columnas'].index('sobr_v')+1
    if not any(r[ki]==k and P['productos'][r[0]][0]==cod and P['productos'][r[0]][4]==P['alimentos']
               and ((r[vi] or 0)>.5 or (r[si] or 0)>.5) for r in P['filas']):return
    clave=P['periodos'][k]['clave'];ss[md.K_CIERRE_1]=clave
    key='_sin_plato_cierre_salto';ss[key]={'selection':{'rows':[0]}}
    try:md._ir_al_producto(key,[cod],clave)
    finally:ss.pop(key,None)


def renderizar(fam_sel=()):
    fuente=md._cargar(fam_sel)
    if fuente is None:
        md._vacia(md.CARD_CIERRE,'Sin plato, cierre por cierre',md._SIN_DATOS);return
    per,filas,tot=fuente;ss=st.session_state
    contexto={'Familias de la página':list(fam_sel),'Ámbito':'Restaurante entero; no aplica el filtro de subalmacén'}
    firma=hashlib.sha256(pickle.dumps((per,filas,tot,contexto),protocol=5)).hexdigest();cache=ss.get('_sin_plato_cierre_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(per,filas,tot,contexto));ss['_sin_plato_cierre_cache']=cache
    P=dict(cache[1]);P['inicial']=md._k_elegido(md.K_CIERRE_1,per);P['parte']='cierre'
    st.markdown('<style>.st-key-ajuste_graf_card_izq_mov_sinplato{height:auto!important;max-height:none!important;overflow:visible!important}</style>',unsafe_allow_html=True)
    with st.container(border=True,key=md.CARD_CIERRE):
        _PIEZA(key='sin_plato_cierre_pieza',data=P,width='stretch',on_abrir_change=_abrir)
    if ss.pop(md._K_IR,False):st.rerun(scope='app')
