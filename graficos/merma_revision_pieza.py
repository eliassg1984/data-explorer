"""Para revisar nativo: fecha y valorización compartidas, casos locales (#732)."""
from pathlib import Path

import streamlit as st

from . import movimientos_merma as mm
from . import merma_revision_datos as datos

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component('merma_revision',
    css=(_DIR/'merma_revision.css').read_text(encoding='utf-8'),
    js=(_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'merma_revision.js').read_text(encoding='utf-8'))


def renderizar(d_rango,d_hist,cols,rango,fecha=None):
    ss=st.session_state;precios=mm.precios_hoy();compras=mm._compras()
    contexto={'Áreas de la página':ss.get('mov_graf_filtro_sub') or []}
    firma=(datos.huella(d_rango),datos.huella(d_hist),tuple(cols.items()),datos.huella(precios),datos.huella(compras),str(rango),str(contexto))
    cache=ss.get('_merma_revision_base_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(d_rango,d_hist,cols,precios,compras,rango=rango,contexto=contexto));ss['_merma_revision_base_cache']=cache
    P=cache[1]
    if P['carta']:
        recetas=mm._recetas_venta();f_carta=(P['sello'],datos.huella(recetas));carta=ss.get('_merma_revision_carta_cache')
        if carta is None or carta[0]!=f_carta:
            carta=(f_carta,datos.adjuntar_recetas(P,recetas));ss['_merma_revision_carta_cache']=carta
        P=carta[1]
    P=dict(P);P['modo']='hoy' if mm.valorizacion()==mm.VALOR_HOY else 'dia'
    marcas=ss.get('mov_merma_rev_marcas')
    P['inicial']=dict(marcas=[k for k in marcas if k in mm.MARCAS] if isinstance(marcas,list) else list(mm.MARCAS_DE_ENTRADA))
    P['solicitado']=ss.get(mm.K_FOCO_REV);P['salto']=ss.get('_merma_revision_salto',0)
    st.markdown('''<style>.st-key-merma_revision_nativa{gap:0!important}
    .st-key-merma_revision_controles{min-height:36px;margin:0!important}
    .st-key-merma_revision_fecha{margin-left:auto!important;width:auto!important}
    .st-key-merma_revision_nativa>[data-testid="stElementContainer"]{margin:0!important}</style>''',unsafe_allow_html=True)
    with st.container(key='merma_revision_nativa'):
        with st.container(key='merma_revision_controles',horizontal=True,vertical_alignment='center',gap='small'):
            st.markdown('<span style="font-size:11px">Valorizar</span>',unsafe_allow_html=True)
            mm.control_valorizacion('mov_merma_rev_ctl')
            if fecha:
                with st.container(key='merma_revision_fecha'):fecha()
        _PIEZA(key='merma_revision_pieza',data=P,width='stretch')
