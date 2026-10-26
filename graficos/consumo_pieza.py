"""Consumo según recetas nativo; conserva el adaptador y sus seis decimales (#733)."""
from graficos.movil import css_movil, js_movil
import hashlib
import json
import pickle
from pathlib import Path

import streamlit as st

from . import movimientos_consumo as mc
from ._consumo_html import _TOKENS

_DIR = Path(__file__).parent
_CSS = '.consumo-pieza{' + ''.join(f'--{k}:{v};' for k, v in _TOKENS.items()) + '}'
_CSS += (_DIR / 'consumo.css').read_text(encoding='utf-8')
_JS = (_DIR / 'consumo.js').read_text(encoding='utf-8').replace(
    '/*__HTML__*/null', json.dumps((_DIR / 'consumo.html').read_text(encoding='utf-8'), ensure_ascii=False))
_PIEZA = st.components.v2.component('consumo_recetas_733', css=css_movil(_CSS),
    js=js_movil((_DIR / '_xlsx.js').read_text(encoding='utf-8') + _JS))


def renderizar(fam_sel=(), sub_sel=(), rango=None, fecha=None):
    ini, fin = mc.rango_de_la_vista(rango)
    with st.container(border=True, key=mc.CARD):
        titulo = ('<p class="chart-card-hdr">Consumo según recetas · consumo estimado de las ventas '
                  'en insumos de compra, bajando por recetas base y porcionamientos</p>')
        if fecha is not None:
            fecha(titulo)
        else:
            st.markdown(titulo, unsafe_allow_html=True)
        r = mc.data.consumo_recetas_rango(ini, fin)
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
        with st.container(key=mc.VISTA):
            _PIEZA(key='consumo_recetas_pieza', data=dict(datos=datos,
                contexto={'Familias de la página': list(fam_sel), 'Sub Almacén sin aplicar': list(sub_sel)}),
                width='stretch')
