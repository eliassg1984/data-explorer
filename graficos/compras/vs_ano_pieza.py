"""Montaje de Vs año pasado. Sus controles trabajan en el navegador (#725, #749).

Vuelven a Python sólo dos cosas: la fecha, que es el panel de meses de las
demás tarjetas, y el pedido de la venta. La venta se pide DESPUÉS de dibujar
(trigger `venta`): sin caché son ~27 s de `ventas.parquet`, y la comparación
de compras no tiene por qué esperarlos.
"""
from graficos.movil import css_movil, js_movil
from pathlib import Path

import pandas as pd
import streamlit as st

import data
import franja_fecha
from estado_rango import atajos_meses
from graficos.base import rango_tarjeta
from ._comun import selector_fecha_tarjeta
from ._etiquetas_proveedor import nombre_propio
from . import vs_ano_datos as datos
from . import vs_ano_pasado as vp

_DIR = Path(__file__).parent
_PIEZA = st.components.v2.component(
    'compras_ano', css=css_movil((_DIR / 'vs_ano.css').read_text(encoding='utf-8')),
    js=js_movil((_DIR.parent / '_xlsx.js').read_text(encoding='utf-8') + (_DIR / 'vs_ano.js').read_text(encoding='utf-8')))

CATEGORIA = 'vs_ano'
"""El rango de esta tarjeta (`rango_cat_Compras_vs_ano`). No va en
`CATEGORIA_SEC`: el dispatcher sembraría la clave con los 12 meses del
reporte antes de que esta tarjeta pida los suyos (regla #376), y esta vista
no recibe su `d` recortado, empareja sobre el histórico entero."""
K_VENTA = '_compras_vap_venta_pedida'


def ctx_fecha(fechas):
    """El `ctx` del panel de MESES de la tarjeta: los topes de las compras y
    «Últimos 3 meses» de entrada (meses enteros: un mes empezado a la mitad
    se compararía con uno entero). Lo leen el botón y la ventana: con el
    mismo ctx nombran la misma clave."""
    base = franja_fecha.contexto()
    f = pd.to_datetime(fechas, errors='coerce').dropna() if fechas is not None else None
    if not base or f is None or f.empty:
        return None
    topes = (f.min().date().replace(day=1), f.max().date())
    r_def = next((r for c, _n, _g, r in atajos_meses(topes[1], topes) if c == 'mm3'), None)
    return {**base, 'fecha_min': topes[0], 'fecha_max': topes[1],
            'rango_default_cat': {CATEGORIA: r_def} if r_def else {},
            'atajos_fn': atajos_meses, 'solo_meses': True}


def _pedir_venta():
    st.session_state[K_VENTA] = True


def renderizar(d, cols, d_full=None):
    if not all(cols.get(k) for k in ['prod', 'fecha', 'valor', 'cant']):
        st.info('Faltan columnas (Producto, Fecha, Valor o Cantidad) para esta comparación.')
        return
    ss = st.session_state
    fuente = d_full if d_full is not None else d
    contexto = {'Familias de la página': [nombre_propio(x) for x in ss.get('compras_graf_filtro_fam') or []],
                'Subfamilias de la página': [nombre_propio(x) for x in ss.get('compras_graf_filtro_sub') or []]}
    firma = (datos.huella(fuente, cols), tuple(cols.items()), str(contexto))
    cache = ss.get('_compras_ano_pieza_cache')
    if cache is None or cache[0] != firma:
        cache = (firma, datos.armar(fuente, cols, contexto))
        ss['_compras_ano_pieza_cache'] = cache
    P = dict(cache[1])
    ctx = ctx_fecha(fuente[cols['fecha']] if fuente is not None and cols['fecha'] in fuente else None)
    P['rango'] = datos.meses_de_rango(rango_tarjeta(CATEGORIA, ctx) if ctx else None)
    if ss.get(K_VENTA):
        P['venta'] = datos.venta_por_mes(data.ventas_por_mes())
    else:
        P['venta'], P['venta_pendiente'] = None, True
    P['sello'] = datos.sellar(P)
    fam = ss.get('compras_vap_familia', vp._FAM_TODAS)
    P['inicial'] = dict(fam=datos.TODAS if fam == vp._FAM_TODAS else fam,
                        agrupar=ss.get('compras_vap_agrupar', 'Producto'), q=ss.get('compras_vap_q') or '',
                        modo=ss.get('compras_vap_modo_sel', 'Valor'), foco=ss.get('compras_vap_foco'),
                        corte=ss.get(vp._K_CORTE, 'Por qué'), vista=ss.get(vp._K_VISTA, 'Cascada'))
    with st.container(key='cp_vap_nativa'):
        if ctx:
            with st.container(key='cp_vap_nativa_fecha'):
                selector_fecha_tarjeta('cp_vap_f', None, categoria=CATEGORIA, ctx=ctx)
        _PIEZA(key='compras_ano_pieza', data=P, width='stretch', on_venta_change=_pedir_venta)
