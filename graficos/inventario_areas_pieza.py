"""Montaje y salto de Stock por Área y Familia a Productos (#724)."""
from pathlib import Path

import streamlit as st

from . import inventario as inv
from . import inventario_areas_datos as datos

_DIR=Path(__file__).parent
_PIEZA=st.components.v2.component(
    'inventario_areas',css=(_DIR/'inventario_areas.css').read_text(encoding='utf-8'),
    js=(_DIR/'_xlsx.js').read_text(encoding='utf-8')
       +(_DIR/'inventario_base.js').read_text(encoding='utf-8')
       +(_DIR/'inventario_areas.js').read_text(encoding='utf-8'))


def _ir():
    ss=st.session_state;v=(ss.get('inv_areas_pieza') or {}).get('ir')
    cache=ss.get('_inv_areas_cache')
    if not isinstance(v,dict) or not cache or v.get('sello')!=cache[1]['sello']:
        return
    p=cache[1]
    if any(not isinstance(v.get(k),list) or any(x not in p['dic'][dic] for x in v[k])
           for k,dic in [('areas','area'),('fams','fam'),('subs','subfam')]):
        return
    chip=v.get('chip','todos')
    if chip not in ('todos','neg','sin','alto'):
        return
    inv._ir_a_productos(v['areas'],v['fams'],v['subs'],chip)


def renderizar(d,excluidos,cols,historia=None,consumo=None):
    ss=st.session_state
    contexto={'Áreas de la página':ss.get('inv_graf_filtro_area') or [],
              'Familias de la página':ss.get('inv_graf_filtro_fam') or []}
    firma=(datos.huella(d),datos.huella(excluidos),tuple(cols.items()),str(contexto),
           datos.huella(historia[2]) if historia else None,
           tuple(historia[0]) if historia else (),tuple(map(str,historia[1])) if historia else (),datos.huella(consumo))
    cache=ss.get('_inv_areas_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(d,excluidos,cols,historia,consumo,contexto))
        ss['_inv_areas_cache']=cache
    _PIEZA(key='inv_areas_pieza',data=cache[1],on_ir_change=_ir,width='stretch')
    if ss.pop(inv._K_IR,False):
        st.rerun(scope='app')
