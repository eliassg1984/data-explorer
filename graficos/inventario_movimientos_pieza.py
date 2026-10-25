"""Movimientos de Stock: sólo el período consulta las fuentes (#738)."""
import datetime as dt
import hashlib
import json
import pickle
from pathlib import Path

import streamlit as st
import data
import kardex
import tema
from . import inventario_movimientos as im
from . import inventario_movimientos_datos as datos

_DIR=Path(__file__).parent
_CSS='.imv{'+''.join(f'--{k}:{v};' for k,v in dict(acento=tema.ACENTO,pos=tema.AJUSTE_POS,neg=tema.AJUSTE_NEG).items())+'}'+(_DIR/'inventario_movimientos.css').read_text(encoding='utf-8')
_PIEZA=st.components.v2.component('stock_movimientos_738',css=_CSS,
    js=(_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'inventario_movimientos.js').read_text(encoding='utf-8'))


def renderizar(d,*,col_cod_area,col_cod,col_area,col_prod,col_fam=None,col_punit=None):
    if not (col_cod_area and col_cod and col_area and col_prod):
        st.info('El parquet de stock no trae los códigos de área y de producto: sin ellos no hay cómo cruzarlo con el kardex.');return
    rango=data.rango_fechas(kardex.ARCHIVO,kardex.COL_FECHA)
    if not rango:
        st.info('Falta el kardex: la consulta «kardex» del Sheet todavía no llegó a la app.');return
    ss=st.session_state;desde_min,tope=max(rango[0],kardex.INICIO),rango[1]
    if im._K_RANGO not in ss:ss[im._K_RANGO]=im.periodo_por_defecto(desde_min,tope)
    ss[im._K_RANGO]=tuple(min(max(f,desde_min),tope) for f in tuple(ss[im._K_RANGO] or ())) or (desde_min,tope)
    st.markdown('<style>.st-key-ajuste_graf_card_izq_inv_movimientos{height:auto!important;max-height:none!important;overflow:visible!important}.st-key-stock_mov_nativa{gap:0!important}.st-key-stock_mov_fecha{height:36px;min-height:36px;margin:0!important}@media(max-width:750px){.st-key-stock_mov_fecha{height:auto!important}}</style>',unsafe_allow_html=True)
    with st.container(key='stock_mov_nativa'):
        with st.container(key='stock_mov_fecha'):
            ct,cf=st.columns([3,1.3],vertical_alignment='center')
            with ct:st.markdown(f'<div style="font-size:17px;font-weight:600;color:{tema.ACENTO_TEXTO}">Por qué cambió el stock</div>',unsafe_allow_html=True)
            with cf:sel=st.date_input('Período',key=im._K_RANGO,min_value=desde_min,max_value=tope,format='DD/MM/YYYY',label_visibility='collapsed')
        sel=tuple(sel) if isinstance(sel,(tuple,list)) else (sel,)
        if not sel:return
        desde,hasta=sel[0],sel[-1];mov=data.movimientos_kardex(desde,hasta)
        foto_ini=data.stock_al(kardex.momento(desde-dt.timedelta(days=1),23));foto_fin=data.stock_al(kardex.momento(hasta,23))
        if mov is None or foto_ini is None or foto_fin is None:
            st.info('No se pudo leer el kardex. Probá de nuevo en un momento.');return
        cols=dict(col_cod_area=col_cod_area,col_cod=col_cod,col_area=col_area,col_prod=col_prod,col_fam=col_fam,col_punit=col_punit)
        contexto={'Ámbito':'Productos activos y filtros generales recibidos de la página','Fotos':'Al cierre del día anterior y del último día del período, con la hora de kardex original'}
        firma=hashlib.sha256(pickle.dumps((d,mov,foto_ini,foto_fin,cols,desde,hasta,contexto),protocol=5)).hexdigest();cache=ss.get('_stock_mov_738_cache')
        if cache is None or cache[0]!=firma:
            cache=(firma,datos.armar(d,mov,foto_ini,foto_fin,**cols,desde=desde,hasta=hasta,contexto=contexto));ss['_stock_mov_738_cache']=cache
        P=dict(cache[1]);P['inicial']=dict(areas=ss.get(im._K_AREAS) or [],familias=ss.get(im._K_FAMILIAS) or [],q=ss.get(im._K_BUSCAR) or '',vista='area' if ss.get(im._K_VISTA)==im._VISTAS[1] else 'tipo')
        for key,valor in [(im._K_AREAS,P['inicial']['areas']),(im._K_FAMILIAS,P['inicial']['familias']),(im._K_BUSCAR,P['inicial']['q']),(im._K_VISTA,im._VISTAS[1] if P['inicial']['vista']=='area' else im._VISTAS[0])]:ss[key]=valor
        P['comun']=json.dumps(P['inicial'],ensure_ascii=False)
        _PIEZA(key='stock_movimientos_pieza',data=P,width='stretch')
