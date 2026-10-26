"""Montaje de Vs año pasado. Sus controles trabajan en el navegador (#725)."""
from graficos.movil import css_movil, js_movil
from pathlib import Path

import streamlit as st

from . import vs_ano_datos as datos
from . import vs_ano_pasado as vp

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component(
    'compras_ano',css=css_movil((_DIR/'vs_ano.css').read_text(encoding='utf-8')),
    js=js_movil((_DIR.parent/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'vs_ano.js').read_text(encoding='utf-8')))


def renderizar(d,cols,d_full=None):
    if not all(cols.get(k) for k in ['prod','fecha','valor','cant']):
        st.info('Faltan columnas (Producto, Fecha, Valor o Cantidad) para esta comparación.')
        return
    ss=st.session_state
    contexto={'Familias de la página':ss.get('compras_graf_filtro_fam') or [],
              'Subfamilias de la página':ss.get('compras_graf_filtro_sub') or []}
    firma=(datos.huella(d,cols),datos.huella(d_full,cols),tuple(cols.items()),str(contexto))
    cache=ss.get('_compras_ano_pieza_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(d,cols,d_full,contexto));ss['_compras_ano_pieza_cache']=cache
    P=dict(cache[1]);fam=ss.get('compras_vap_familia',vp._FAM_TODAS)
    P['inicial']=dict(ventana=ss.get('compras_vap_periodo','3m'),fam=datos.TODAS if fam==vp._FAM_TODAS else fam,
                       agrupar=ss.get('compras_vap_agrupar','Producto'),q=ss.get('compras_vap_q') or '',
                       modo=ss.get('compras_vap_modo_sel','Valor'),foco=ss.get('compras_vap_foco'),
                       auto=not ss.get(vp._K_FOCO_TOCADO,False),corte=ss.get(vp._K_CORTE,'Por qué'),
                       vista=ss.get(vp._K_VISTA,'Cascada'))
    _PIEZA(key='compras_ano_pieza',data=P,width='stretch')
