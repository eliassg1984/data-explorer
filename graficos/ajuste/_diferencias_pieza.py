"""Análisis de diferencias: sesión nativa; filtros, lista y ficha locales (#739)."""
from graficos.movil import css_movil, js_movil
import hashlib
import json
import pickle
from pathlib import Path

import pandas as pd
import streamlit as st
import data
import tema
from . import _diferencias as dif
from . import _diferencias_datos as datos

_DIR=Path(__file__).parent
_CSS=dif._CSS.replace('<style>','').replace('</style>','')+(_DIR/'diferencias.css').read_text(encoding='utf-8')
_CSS+='.adf{'+''.join(f'--{k}:{v};' for k,v in dict(acento=tema.ACENTO,neg=tema.AJUSTE_NEG,pos=tema.AJUSTE_POS).items())+'}'
_PIEZA=st.components.v2.component('ajuste_diferencias_739',css=css_movil(_CSS),
    js=js_movil((_DIR.parent/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'diferencias.js').read_text(encoding='utf-8')))


def renderizar(df_full,col_fecha,col_familia,col_area,col_ajuste_val,col_producto):
    ss=st.session_state;sesiones=dif.sesiones_de(df_full,col_fecha)
    opciones=sorted(df_full[col_familia].dropna().astype(str).unique().tolist()) if col_familia and col_familia in df_full else []
    dif.sembrar_seleccion(pd.DataFrame({col_familia or 'f':opciones}),col_familia or 'f',dif.K_FAM,list(dif.FAMILIAS_DE_ENTRADA))
    familias=[f for f in (ss.get(dif.K_FAM) or []) if f in opciones]
    st.markdown(dif.CSS_TITULOS_DRILL+'<style>.st-key-ajdif_nativa{gap:0!important}.st-key-ajdif_sesion_nativa{height:36px;min-height:36px;margin:0!important}@media(max-width:750px){.st-key-ajdif_sesion_nativa{height:auto!important}}</style>',unsafe_allow_html=True)
    with st.container(border=True,key=dif.CARD),st.container(key='ajdif_nativa'):
        with st.container(key='ajdif_sesion_nativa'):
            ct,cs=st.columns([3,1.3],vertical_alignment='center')
            with ct:st.markdown('<div class="inv-rank-tit">Análisis de diferencias</div>',unsafe_allow_html=True)
            with cs:
                if sesiones:dif.selector_sesion('ajses_dif',dif.K_SES,sesiones,stats=dif.stats_de_vista(df_full,sesiones,col_fecha,col_area,col_ajuste_val,col_producto,col_familia,[]),familias_txt='todas las familias',pie=['Las cifras del selector corresponden a todas las familias.','Cada línea se compara con su conteo anterior en esa área, que puede ser un parcial.'])
        s=dif.sesion_vigente(dif.K_SES,sesiones) if sesiones else None
        if s is None:st.info('Sin sesiones de inventario.');return
        with st.spinner('Cruzando el conteo con el kardex y las recetas…'):r=data.diferencias_ajuste_sesion(s['clave'])
        if r is None:st.info(dif._SIN_DATOS);return
        contexto={'Sesión':s['clave'],'Nombre':s['nombre'],'Conteo':s.get('etiqueta_anio') or '',
            'Ámbito':'Cada línea conserva su conteo anterior y su ventana propios; el selector de sesión muestra todas las familias.'}
        firma=hashlib.sha256(pickle.dumps((r,contexto),protocol=5)).hexdigest();cache=ss.get('_ajdif_739_cache')
        if cache is None or cache[0]!=firma:
            cache=(firma,datos.armar(r,contexto));ss['_ajdif_739_cache']=cache
        P=dict(cache[1]);P['familias']=opciones;P['salto']=ss.get('_ajdif_salto',0)
        P['inicial']=dict(familias=familias,areas=ss.get(dif.K_AREA) or [],ver=ss.get(dif.K_VER) if ss.get(dif.K_VER) in dif.VER else 'junto',
            lado=ss.get(dif.K_LADO) if ss.get(dif.K_LADO) in dif.LADOS else 'fal',pista=ss.get(dif.K_PISTA) or 'todas',q=ss.get(dif.K_BUSCAR) or '',foco=ss.get(dif._K_FOCO))
        for key,v in [(dif.K_FAM,familias),(dif.K_AREA,P['inicial']['areas']),(dif.K_VER,P['inicial']['ver']),(dif.K_LADO,P['inicial']['lado']),(dif.K_PISTA,P['inicial']['pista']),(dif.K_BUSCAR,P['inicial']['q']),(dif._K_FOCO,P['inicial']['foco'])]:ss[key]=v
        P['comun']=json.dumps(P['inicial'],ensure_ascii=False)
        _PIEZA(key='ajuste_diferencias_pieza',data=P,width='stretch')
