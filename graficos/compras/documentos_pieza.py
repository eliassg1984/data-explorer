"""Detalle docs.: controles locales; fecha y aviso del ranking releen Python (#726)."""
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from graficos.base import rango_tarjeta
from ._comun import CATEGORIA_SEC, base_normalizada, selector_fecha_tarjeta
from . import documentos_datos as datos

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component('compras_documentos',
    css=(_DIR/'documentos.css').read_text(encoding='utf-8'),
    js=(_DIR.parent/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'documentos.js').read_text(encoding='utf-8'))


def renderizar(d,cols):
    ss=st.session_state
    if ss.pop('_cp_docs_atajo_pendiente',False):
        # Los controles propios viven en el navegador; no hay widgets que
        # preservar aquí ni se escriben los de la sección de Proveedores.
        st.rerun(scope='app')
    if not(cols[0] and cols[3]):
        st.info('Faltan columnas de Proveedor o Valor para mostrar los documentos.')
        return
    b=base_normalizada(d,*cols)
    universo=b.groupby('prov')['valor'].sum().sort_values(ascending=False,kind='stable').index.tolist()
    seleccion=datos.leer_seleccion(ss,'cp_prov',universo)
    top=[p for p in seleccion if p in set(b.prov)] or universo
    inicial=datos.leer_seleccion(ss,'cp_docs_prov',top)
    rango=rango_tarjeta(CATEGORIA_SEC['compras_sec_documentos'])
    if rango is None or any(f is None for f in rango):
        fechas=b.fecha.dropna();rango=(fechas.min(),fechas.max()) if len(fechas) else None
    contexto={'Familias de la página':ss.get('compras_graf_filtro_fam') or [],
              'Subfamilias de la página':ss.get('compras_graf_filtro_sub') or [],
              'Proveedores del ranking':top}
    firma=(hashlib.sha256(pd.util.hash_pandas_object(b,index=True).values.tobytes()).hexdigest(),
           tuple(top),str(contexto),str(rango),bool(cols[-1]),bool(cols[4]))
    cache=ss.get('_compras_documentos_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(b,top,col_docu=bool(cols[-1]),col_punit=bool(cols[4]),contexto=contexto,rango=rango))
        ss['_compras_documentos_cache']=cache
    P=dict(cache[1]);gran=ss.get('compras_prov_gran','Mes')
    P['inicial']=dict(gran=gran if gran in datos.GRANOS else 'Mes',
                       proveedores=None if set(inicial)==set(top) else inicial)
    st.markdown('''<style>
    .st-key-cp_docs_nativa{position:relative;gap:0!important}
    .st-key-cp_docs_nativa_fecha{position:absolute;right:18px;top:12px;z-index:5;width:auto!important}
    .st-key-cp_docs_nativa>[data-testid="stElementContainer"]{margin:0!important}
    </style>''',unsafe_allow_html=True)
    with st.container(key='cp_docs_nativa'):
        with st.container(key='cp_docs_nativa_fecha'):
            selector_fecha_tarjeta('cp_docs','_cp_docs_atajo_pendiente',
                                  categoria=CATEGORIA_SEC['compras_sec_documentos'])
        # El evento sólo solicita releer la selección canónica de Python.
        # No aplica filtros ni importes enviados desde el navegador.
        _PIEZA(key='compras_documentos_pieza',data=P,width='stretch',on_ranking_change=lambda:None)
