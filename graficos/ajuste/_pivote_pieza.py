"""Tabla dinámica propia; calendario nativo, exploración local (#740)."""
from pathlib import Path
import hashlib
import pickle
import streamlit as st
import tema
from . import _pivote_datos as datos
from ._comun import ctx_meses, mes_operativo_activo, rango_meses, recortar_meses, selector_meses

_DIR=Path(__file__).parent
_CSS=(_DIR/'pivote.css').read_text(encoding='utf-8')
_CSS+='.apv{'+''.join(f'--apv-{k}:{v};' for k,v in dict(acento=tema.ACENTO,neg=tema.AJUSTE_NEG,pos=tema.AJUSTE_POS).items())+'}'
_PIEZA=st.components.v2.component('ajuste_pivote_740',css=_CSS,
    js=(_DIR.parent/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'pivote.js').read_text(encoding='utf-8'))


def renderizar(d,col_fecha,col_familia,col_area,col_ajuste_val,col_producto,col_cantidad):
    if not col_fecha or col_fecha not in d:
        st.info('Sin columna de fecha: no se puede armar el detalle.')
        return
    ss=st.session_state
    st.markdown('<style>.st-key-ajdet_fecha_nativa{height:36px;min-height:36px;margin:0!important}@media(max-width:750px){.st-key-ajdet_fecha_nativa{height:auto!important}}</style>',unsafe_allow_html=True)
    with st.container(border=True,key='ajuste_graf_card_izq_detalle'):
        with st.container(key='ajdet_fecha_nativa'):
            ct,cf=st.columns([3,1.45],vertical_alignment='center')
            with ct:st.markdown('<div style="font-size:14px;font-weight:600">Detalle por producto</div>',unsafe_allow_html=True)
            ctx=ctx_meses('det',d[col_fecha])
            with cf:selector_meses('ajf_det',ctx)
        d=recortar_meses(d,col_fecha,rango_meses(ctx))
        operativo=mes_operativo_activo()
        cols=(col_fecha,col_familia,col_area,col_ajuste_val,col_producto,col_cantidad)
        if not(col_familia and col_producto and col_ajuste_val):
            st.info('Se necesita familia, producto y ajuste valorizado para la tabla dinámica.')
            return
        # La fecha y las familias ya recortan la página; el resto vive en JS.
        contexto={
            'Rango':str(rango_meses(ctx)),
            'Fecha del mes':'Mes operativo' if operativo else 'Fecha de registro',
            'Familias de la página':', '.join(ss.get('ajuste_graf_filtro_familia') or []) or 'Todas',
            'Fuente':'Ajuste de inventario; cantidades y soles originales, sin redondear.'}
        firma=hashlib.sha256(pickle.dumps((d,cols,operativo,contexto),protocol=5)).hexdigest()
        cache=ss.get('_ajdet_740_cache')
        if cache is None or cache[0]!=firma:
            cache=(firma,datos.armar(d,cols,operativo=operativo,contexto=contexto))
            ss['_ajdet_740_cache']=cache
        P=dict(cache[1])
        P['inicial']=dict(gran=ss.get('ajuste_det_gran') if ss.get('ajuste_det_gran') in ('Mes','Corte') else 'Mes',areas=ss.get('ajuste_det_filtro_area') or [])
        ss['ajuste_det_gran']=P['inicial']['gran'];ss['ajuste_det_filtro_area']=P['inicial']['areas']
        _PIEZA(key='ajuste_pivote_pieza',data=P,width='stretch')
