"""Contrato de Control de pedidos como pieza propia (#723).

El POS se interpreta con las funciones originales; el navegador agrupa,
filtra y dibuja sin convertir importes ni duraciones a texto.
"""
import hashlib
import json
import math

import numpy as np
import pandas as pd

from . import ventas_control as vc

CP = ('ped','dia','apertura','estado','canal','mesa','mesero','adultos','ninos',
      'primer','ultimo','platos','monto','monto_anulado','precuenta','n_precuenta',
      'comp','f_anul','usu_anul','obs_anul','anulado','motivo')
CT = ('tipo','ped','destino','producto','cant','venta','f_item','f_trx','dia',
      'usuario','cocina','obs','min','clase')
CB = ('ped','dia','mesa','mesero','adultos','monto','n_precuenta','inicio','comp',
      'espera','comida','sobremesa','cobro','total','servicio','grupo','desde','hasta')
FECHAS = {'dia','apertura','primer','ultimo','precuenta','comp','f_anul','f_item','f_trx','inicio'}


def preparar(p, t, cortesias=frozenset()):
    p = p.copy() if p is not None else vc.pedidos(pd.DataFrame({'CODIGO PEDIDO':['']}))
    t = t.copy() if t is not None else vc.transacciones(pd.DataFrame({'TIPO':['']}))
    t['clase'] = ''
    an, tr = t.tipo.eq(vc.PLATO_ANULADO), t.tipo.eq(vc.TRANSFERENCIA)
    if an.any():
        t.loc[an,'clase'] = vc.clase_plato_anulado(t[an])
    if tr.any():
        t.loc[tr,'clase'] = vc.tipo_transferencia(t[tr],p,cortesias)
    b = vc.tiempos(p)
    if b is None:
        b = pd.DataFrame(columns=CB)
    else:
        b['grupo'] = vc.grupo_de(b.adultos)
        base = b.dia + pd.Timedelta(minutes=vc._PRIMER_SLOT_MIN)
        b['desde'] = np.ceil((b.inicio-base).dt.total_seconds()/1800).clip(lower=0).astype(int)
        b['hasta'] = np.floor((b.comp-base).dt.total_seconds()/1800).clip(upper=vc._N_SLOTS-1).astype(int)
    return p,t,b


def _valor(v, campo):
    if pd.isna(v):
        return None
    if campo in FECHAS:
        return int(pd.Timestamp(v).value//1000000)
    if isinstance(v,(bool,np.bool_)):
        return bool(v)
    if isinstance(v,(int,float,np.number)):
        return float(v) if math.isfinite(float(v)) else None
    return str(v)


def armar(p, t, rango, *, turno=True, canales=(), cortesias=frozenset()):
    fuentes = dict(pedidos=p is not None,transacciones=t is not None)
    p,t,b = preparar(p,t,cortesias)
    ini,fin = map(pd.Timestamp,rango)
    dias = pd.date_range(ini,fin,freq='D')
    fechas = pd.Series(sorted(set(dias) | set(p.dia) | set(t.dia)),dtype='datetime64[ns]')
    planes = {}
    for gran in vc._GRANOS:
        claves = vc._periodo_serie(fechas,gran)
        ks = sorted(set(claves))
        planes[gran] = dict(mapa={str(int(f.value//86400000000000)):str(k) for f,k in zip(fechas,claves)},
                            rotulos=dict(zip(ks,vc._rotulos(ks,gran,(ini.date(),fin.date())))))
    def filas(df, cols):
        return [[_valor(v,c) for c,v in zip(cols,f)] for f in df.reindex(columns=cols).itertuples(index=False,name=None)]
    payload=dict(cp=CP,ct=CT,cb=CB,p=filas(p,CP),t=filas(t,CT),b=filas(b,CB),
                 fuentes=fuentes,rango=[str(ini.date()),str(fin.date())],turno=bool(turno),
                 canales=sorted(canales),planes=planes,
                 dias=[int(d.value//86400000000000) for d in dias],slots=vc.etiquetas_slots(),
                 grupos=[n for _,_,n in vc._GRUPOS]+['Sin dato'])
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
    payload['sello']=hashlib.sha256(raw.encode()).hexdigest()
    return payload
