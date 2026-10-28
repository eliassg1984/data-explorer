"""Consumo según ventas nativo; conserva el adaptador y sus seis decimales (#733).

Vuelven a Python dos cosas (regla #751): «Rendimiento» —el de los 90 días o el
del último mes, que rehace el cálculo— y la merma esperada de un insumo, que
se guarda en R2 (`mermas_esperadas.py`)."""
from graficos.movil import css_movil, js_movil
import hashlib
import json
import pickle
from pathlib import Path

import streamlit as st

import consumo_recetas
import mermas_esperadas
from . import movimientos_consumo as mc
from ._consumo_html import _TOKENS

_DIR = Path(__file__).parent
_CSS = '.consumo-pieza{' + ''.join(f'--{k}:{v};' for k, v in _TOKENS.items()) + '}'
_CSS += (_DIR / 'consumo.css').read_text(encoding='utf-8')
_JS = (_DIR / 'consumo.js').read_text(encoding='utf-8').replace(
    '/*__HTML__*/null', json.dumps((_DIR / 'consumo.html').read_text(encoding='utf-8'), ensure_ascii=False))
_PIEZA = st.components.v2.component('consumo_recetas_733', css=css_movil(_CSS),
    js=js_movil((_DIR / '_xlsx.js').read_text(encoding='utf-8') + _JS))


K_PIEZA = 'consumo_recetas_pieza'
K_REND = 'consumo_rendimiento'
"""El rendimiento elegido («90» o «mes»), uno para la sesión."""


def _al_rendimiento():
    v = (st.session_state.get(K_PIEZA) or {}).get('rendimiento')
    if v in consumo_recetas.RENDIMIENTOS:
        st.session_state[K_REND] = v


def _al_merma(insumos):
    """Guarda la merma esperada de un insumo de la vista. Un código que no
    está en la vista o un porcentaje fuera de rango no hacen nada."""
    v = (st.session_state.get(K_PIEZA) or {}).get('merma')
    if not isinstance(v, dict) or str(v.get('cod')) not in insumos:
        return
    pct = v.get('pct')
    if pct is not None and mermas_esperadas.con({}, v['cod'], pct) is None:
        return
    if not mermas_esperadas.poner(v['cod'], pct):
        st.session_state['_consumo_merma_error'] = True


def renderizar(fam_sel=(), sub_sel=(), rango=None, fecha=None):
    ini, fin = mc.rango_de_la_vista(rango)
    with st.container(border=True, key=mc.CARD):
        titulo = '<p class="chart-card-hdr">Consumo según ventas</p>'
        if fecha is not None:
            fecha(titulo)
        else:
            st.markdown(titulo, unsafe_allow_html=True)
        modo = st.session_state.get(K_REND, '90')
        if modo not in consumo_recetas.RENDIMIENTOS:
            modo = '90'
        r = mc.data.consumo_recetas_rango(ini, fin, rendimiento=modo)
        if r is None:
            st.info('No se pudo calcular el consumo. Hacen falta el primer nivel de las recetas '
                    'de venta, las recetas base, los porcionamientos y el inventario valorizado.')
            return
        if r['filas'].empty:
            st.info('Sin ventas con receta en estas fechas. Ampliá el rango con el botón de fecha.')
            return
        compras = mc.compras_del_rango(mc.data.cargar(mc.ARCHIVO_COMPRAS), ini, fin, fam_sel)
        editadas = mc.recetas_editadas(mc.data.cargar(mc.ARCHIVO_RECETAS), ini)
        # Objetos internos ya cargados: pickle sólo se escribe para obtener su huella.
        firma = hashlib.sha256(pickle.dumps((r, compras, editadas, tuple(fam_sel)), protocol=5)).hexdigest()
        cache = st.session_state.get('_consumo_733_cache')
        if cache is None or cache[0] != firma:
            cache = (firma, mc.datos_de_la_vista(r, fam_sel, compras=compras, editadas=editadas))
            st.session_state['_consumo_733_cache'] = cache
        datos = cache[1]
        if not datos['filas']:
            st.info('Ningún insumo de compra de la familia elegida en el rango.')
            return
        if sub_sel:
            st.caption('El chip «Sub Almacén» no recorta esta sección: la receta dice qué '
                       'insumo se usa, no de qué almacén sale.')
        if st.session_state.pop('_consumo_merma_error', False):
            st.warning('No se pudo guardar la merma esperada en R2. Probá de nuevo en un momento.')
        with st.container(key=mc.VISTA):
            _PIEZA(key=K_PIEZA, data=dict(datos=datos, rendimiento=modo, mermas=mermas_esperadas.leer(),
                contexto={'Familias de la página': list(fam_sel), 'Sub Almacén sin aplicar': list(sub_sel)}),
                width='stretch', on_rendimiento_change=_al_rendimiento,
                on_merma_change=lambda: _al_merma(datos['insumos']))
