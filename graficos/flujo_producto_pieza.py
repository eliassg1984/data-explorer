"""Mapa de procesos para enseñar el recorrido de un producto."""
from pathlib import Path

import streamlit as st

import data
import tema
from flujo_producto import armar
from graficos.movil import css_movil, js_movil

_DIR = Path(__file__).parent
_CSS = '.flujo-producto{' + ''.join(f'--fp-{k}:{v};' for k, v in {
    'accent': tema.ACENTO, 'ink': tema.TEXTO_PRINCIPAL, 'bg': tema.BLANCO,
    'soft': tema.GRIS_FONDO, 'border': tema.GRIS_BORDE}.items()) + '}'
_CSS += (_DIR / 'flujo_producto.css').read_text(encoding='utf-8')
_PIEZA = st.components.v2.component('flujo_producto',
    css=css_movil(_CSS),
    js=js_movil((_DIR / 'flujo_producto.js').read_text(encoding='utf-8')))


def renderizar(rango, fecha=None):
    with st.container(border=True, key='flujo_producto_card'):
        titulo = '<p class="chart-card-hdr">Flujo del producto</p>'
        if fecha:
            fecha(titulo)
        else:
            st.markdown(titulo, unsafe_allow_html=True)
        archivos = ['inventariovalorizado.parquet', 'compras.parquet', 'porcionamientos.parquet',
                    'recetabase.parquet', 'recetaventa.parquet', 'ordenesproduccion.parquet']
        # cargar() conserva la caché y la definición canónica de compras netas.
        tablas = [data.cargar(a) for a in archivos]
        if tablas[2] is None and tablas[3] is None and tablas[4] is None:
            st.info('Faltan recetas y porcionamientos para reconstruir el flujo.')
            return
        firma = (tuple((data.sello_datos(a), None if t is None else len(t))
                       for a, t in zip(archivos, tablas)), tuple(map(str, rango)))
        cache = st.session_state.get('_flujo_producto_cache')
        if cache is None or cache[0] != firma:
            cache = (firma, armar(*tablas[:5], rango=rango, ordenes=tablas[5]))
            st.session_state['_flujo_producto_cache'] = cache
        grafo = dict(cache[1])
        grafo['exportCss'] = f':root{{--fp-border:{tema.GRIS_BORDE}}}'
        if not grafo['enlaces']:
            st.info('No se encontraron relaciones entre productos con estas fuentes y fechas.')
            return
        _PIEZA(key='flujo_producto_pieza', data=grafo, width='stretch')
