"""Vs año pasado: cada producto-mes una vez; el navegador arma las parejas (#725, #749).

Hasta la regla #749 Python mandaba las parejas ya hechas (cada mes contra el
mismo mes de doce antes), una copia por familia y con el calendario de cada
familia. Desde ahí manda lo comprado de cada producto en cada mes, una sola
vez, y el navegador lo empareja contra el período que se elija en «Contra»:
el año pasado, hace dos años, el período anterior o el que empiece en otro
mes. La regla de las parejas es la de `vs_ano_pasado._con_ano_pasado`, con
doce meses cambiados por los que pida «Contra»: el mes parcial se compara
con los mismos días de su espejo, y no se muestran meses sin espejo.

El calendario es UNO para la página. Una familia que no compró en los
últimos días no tiene por qué recortar su espejo: no comprar es el dato, y
con un calendario por familia las fichas de las familias no sumaban el
total de arriba.
"""
import hashlib
import json

import pandas as pd

from cortes import MESES_ABR_ES
from ._etiquetas_proveedor import nombre_propio
from . import vs_ano_pasado as vp

TODAS = '__todas__'


def huella(d, cols):
    if d is None:
        return None
    cs = list(dict.fromkeys(c for c in cols.values() if c and c in d))
    return hashlib.sha256(pd.util.hash_pandas_object(d[cs], index=True).values.tobytes()).hexdigest()


def _filas(fuente, prod, fe, val, cant, ids, parcial):
    """`[p, mes, v, q]` por producto-mes con compras. Si el mes tiene compras
    después del día del mes parcial, `[p, mes, v, q, vd, qd]`: lo comprado
    hasta ese día, por si el mes es el espejo del parcial (`vd` None si hasta
    ese día no hubo ninguna compra)."""
    g0 = vp._mensual(fuente, prod, fe, val, cant)
    if g0.empty:
        return []
    otro = {}
    if parcial is not None:
        dia = parcial[1]
        fechas = pd.to_datetime(fuente[fe], errors='coerce')
        tarde = fuente[fechas.dt.day > dia]
        if len(tarde):
            con_tarde = vp._mensual(tarde, prod, fe, val, cant)
            hasta = vp._mensual(fuente[fechas.dt.day <= dia], prod, fe, val, cant)
            hasta = {(r.prod, r.mes): (float(r.valor), float(r.cant)) for r in hasta.itertuples()}
            otro = {(r.prod, r.mes): hasta.get((r.prod, r.mes), (None, None)) for r in con_tarde.itertuples()}
    filas = []
    for r in g0.sort_values(['mes', 'prod'], kind='stable').itertuples():
        fila = [ids[str(r.prod)], str(r.mes), float(r.valor), float(r.cant)]
        if (r.prod, r.mes) in otro:
            fila += list(otro[(r.prod, r.mes)])
        filas.append(fila)
    return filas


def armar(fuente, cols, contexto=None):
    """Lo que la pieza necesita, sin la fecha ni la venta (las pone el
    montaje): productos, familias, filas, mapas, unidades y calendario."""
    fuente = fuente if fuente is not None else pd.DataFrame(columns=[c for c in cols.values() if c])
    prod, fe, val, cant = (cols[k] for k in ['prod', 'fecha', 'valor', 'cant'])
    fam, sub, um = (cols.get(k) for k in ['fam', 'sub', 'um'])
    nombres = sorted(fuente[prod].astype(str).unique()) if prod in fuente else []
    ids = {p: i for i, p in enumerate(nombres)}
    fechas = pd.to_datetime(fuente[fe], errors='coerce').dropna() if fe in fuente else pd.Series(dtype='datetime64[ns]')
    parcial = vp._mes_parcial(fechas) if len(fechas) else None
    filas = _filas(fuente, prod, fe, val, cant, ids, parcial) if len(fechas) else []
    mapas = {}
    for agrup, col in [('Familia', fam), ('Subfamilia', sub)]:
        if col and col in fuente:
            mapa = fuente[[prod, col]].astype(str).drop_duplicates(prod).set_index(prod)[col]
            # Como nombre propio, igual que el resto de Compras: llegan gritados del ERP.
            mapas[agrup] = {str(ids[n]): nombre_propio(str(mapa.get(n, n))) for n in nombres}
    familias = sorted(set(mapas.get('Familia', {}).values()))
    unidades = vp._unidades_por(fuente, prod, um)
    payload = dict(
        productos=nombres, familias=familias, filas=filas, mapas=mapas,
        unidades={str(ids[p]): u for p, u in unidades.items() if p in ids},
        primero=str(fechas.min().to_period('M')) if len(fechas) else None,
        techo=str(fechas.max().to_period('M')) if len(fechas) else None,
        ultimo_dia=fechas.max().strftime('%Y-%m-%d') if len(fechas) else None,
        parcial=[str(parcial[0]), parcial[1]] if parcial else None,
        etq_meses=list(MESES_ABR_ES), max_pasos=vp._TOPE_CASCADA, contexto=contexto or {})
    return payload


def sellar(payload):
    """El sello de lo que se le manda a la pieza, sin lo que es sólo de
    entrada (`inicial`): con el mismo sello la pieza no se rehace."""
    datos = {k: v for k, v in payload.items() if k not in ('inicial', 'sello')}
    return hashlib.sha256(json.dumps(datos, sort_keys=True, ensure_ascii=False, allow_nan=False,
                                     separators=(',', ':')).encode()).hexdigest()


def meses_de_rango(rango):
    """`['2026-08', '2026-10']` del rango de fechas del panel, o None."""
    if not rango or len(rango) != 2 or not all(rango):
        return None
    a, b = (pd.Timestamp(x).to_period('M') for x in rango)
    return [str(min(a, b)), str(max(a, b))]


def venta_por_mes(cifras):
    """`{mes: venta neta}` de `data.ventas_por_mes`, o `{}` si no hay."""
    return {str(m): float(c['venta']) for m, c in (cifras or {}).items()
            if isinstance(c, dict) and c.get('venta') is not None}
