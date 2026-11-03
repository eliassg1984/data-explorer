"""Detalle histórico (#809): pieza propia con la forma de Compras › Detalle docs.
Los meses son el panel nativo de Ajuste; todo lo demás vive en el navegador."""
from graficos.movil import css_movil, js_movil
from pathlib import Path
import hashlib
import pickle

import streamlit as st

from . import _historico_datos as datos
from ._comun import ctx_meses, mes_operativo_activo, rango_meses, recortar_meses, selector_meses

_DIR = Path(__file__).parent
# La hoja de Detalle docs. va primero: la misma forma, las mismas clases `dc-*`.
_CSS = ((_DIR.parent / 'compras' / 'documentos.css').read_text(encoding='utf-8')
        + (_DIR / 'historico.css').read_text(encoding='utf-8'))
_PIEZA = st.components.v2.component(
    'ajuste_historico_809', css=css_movil(_CSS),
    js=js_movil((_DIR.parent / '_xlsx.js').read_text(encoding='utf-8')
                + (_DIR / 'historico.js').read_text(encoding='utf-8')))


def renderizar(d, col_fecha):
    if d is None or d.empty or not col_fecha or col_fecha not in d.columns:
        st.info('No hay datos de ajuste.')
        return
    ss = st.session_state
    st.markdown('''<style>
    .st-key-ajh_nativa{position:relative;gap:0!important}
    .st-key-ajh_nativa_fecha{position:absolute;left:12px;top:52px;z-index:5;width:auto!important}
    .st-key-ajh_nativa>[data-testid="stElementContainer"]{margin:0!important}
    </style>''', unsafe_allow_html=True)
    # Abre en 3 meses: 12 son ~115 mil líneas (#797).
    ctx = ctx_meses('exp', d[col_fecha], defecto='mm3')
    rng = rango_meses(ctx)
    d_e = recortar_meses(d, col_fecha, rng)
    contexto = {'Meses': str(rng),
                'Fecha del mes': 'Mes operativo' if mes_operativo_activo() else 'Fecha de registro',
                'Fuente': 'Ajuste de inventario; cantidades y soles originales, sin redondear.'}
    firma = hashlib.sha256(pickle.dumps((d_e, contexto, mes_operativo_activo()), protocol=5)).hexdigest()
    cache = ss.get('_ajh_809_cache')
    if cache is None or cache[0] != firma:
        cache = (firma, datos.armar(d_e, contexto, mes_operativo_activo()))
        ss['_ajh_809_cache'] = cache
    with st.container(key='ajh_nativa'):
        with st.container(key='ajh_nativa_fecha'):
            selector_meses('ajf_exp', ctx)
        _PIEZA(key='ajuste_historico_pieza', data=cache[1], width='stretch')
