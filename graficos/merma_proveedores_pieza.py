"""Montaje del costo por unidad útil y foco compartido con Rendimiento (#729)."""
from graficos.movil import css_movil, js_movil
from pathlib import Path

import streamlit as st

from . import movimientos_merma as mm
from . import merma_proveedores_datos as datos

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component('merma_proveedores_731',
    css=css_movil((_DIR/'merma_proveedores.css').read_text(encoding='utf-8')),
    js=js_movil((_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'merma_proveedores.js').read_text(encoding='utf-8')))


def _producto():
    ss=st.session_state;v=(ss.get('merma_proveedores_pieza') or {}).get('producto')
    cache=ss.get('_merma_proveedores_cache')
    if not isinstance(v,dict) or not cache or v.get('sello')!=cache[1]['sello']:
        return
    cod=v.get('cod')
    if not isinstance(cod,str) or not any(r['cod']==cod for r in cache[1]['productos']):
        return
    if ss.get(mm._K_PROD)!=cod:
        ss[mm._K_PROD]=cod
        mm._avisar_a(mm.SEC_REND)


def renderizar(d_hist,cols,rango):
    ss=st.session_state;compras=mm._compras()
    contexto={'Áreas de la página':ss.get('mov_graf_filtro_sub') or []}
    firma=(datos.huella(d_hist),tuple(cols.items()),datos.huella(compras),str(rango),str(contexto))
    cache=ss.get('_merma_proveedores_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(d_hist,cols,compras,rango=rango,contexto=contexto))
        ss['_merma_proveedores_cache']=cache
    P=dict(cache[1]);P['comun']=ss.get(mm._K_PROD)
    P['inicial']=dict(ventana=ss.get('mov_merma_prov_ventana','12 meses'),
                      unico=bool(ss.get('mov_merma_prov_unico',False)))
    _PIEZA(key='merma_proveedores_pieza',data=P,width='stretch',on_producto_change=_producto)
