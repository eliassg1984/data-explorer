"""Porcionamientos: cabecera única, cortes y dos bases de valorización (#728)."""
import hashlib
import json
import math

import pandas as pd

from . import movimientos_periodo as mp
from . import movimientos_periodo_datos as comun

_COLS=dict(fecha='fecha',doc='doc',area='area',estado='estado',fam='fam',prod='prod',
           cant='cant',val='valor',punit='punit',tipo='tipo',unid='unid')


def _n(v):
    return float(v) if pd.notna(v) and math.isfinite(float(v)) else None


def armar(d,cols,*,precios=None,modo=None,rango=None,contexto=None):
    base,cortes=mp.lineas_porcionamientos(d,**cols)
    hoy=mp.a_precio_de_hoy(base,precios) if precios is not None else None
    solicitado=modo if modo in ('hoy','dia') else 'hoy' if precios is not None else 'dia'
    efectivo='hoy' if solicitado=='hoy' and hoy is not None else 'dia'
    elegida=hoy if efectivo=='hoy' else base
    P=comun.armar(elegida,mp.PORCIONAMIENTOS,_COLS,rango=rango,contexto=contexto)
    P.update(merma=True,produccion=False,suma_sin_procesar=True,familia=False,rotulo_tipo='Usuario',
             valoracion=efectivo,valoracion_solicitada=solicitado,precios_disponibles=precios is not None)
    P['rot_fecha']='fecha de registro'
    P['porciones']={}
    for i,r in base.iterrows():
        actual=hoy.loc[i] if hoy is not None else None
        precio=_n(precios.get(r.cod,float('nan'))) if precios is not None else None
        q,m=_n(r['cant']),_n(r.merma_cant);flags=[]
        if q is None or q<=0:flags.append('Cantidad sin base')
        if m is None:flags.append('Merma sin dato')
        elif m<0 or (q is not None and q>0 and m>q):flags.append('Merma fuera de rango')
        if not r.cortes:flags.append('Sin cortes')
        if precio is None:flags.append('Sin precio actual')
        if not r['prod']:flags.append('Sin producto de origen')
        costo=float(elegida.loc[i,'costo']);v=float(elegida.loc[i,'valor'])
        P['porciones'][str(r.doc)]=dict(costo=costo,mermaCant=m,cortes=int(r.cortes),cod=str(r.cod),
            costoDia=_n(r.costo_dia),valorDia=_n(r.valor),costoHoy=_n(actual.costo) if actual is not None else None,
            valorHoy=_n(actual.valor) if actual is not None else None,precioDisponible=precio is not None,
            precioActual=precio if precio is not None else 0.0 if precios is not None else None,
            pctFisico=m/q*100 if q is not None and q>0 and m is not None else None,
            pctMonetario=v/costo*100 if costo else None,flags=flags)
    cd={c:sorted(cortes[c].astype(str).unique()) for c in ['fin','unid','cod_fin']}
    ids={c:{v:i for i,v in enumerate(vs)} for c,vs in cd.items()};docs={v:i for i,v in enumerate(P['dic']['doc'])}
    P['cortes_dic']=cd
    unidad_origen=base.set_index('doc')['unid'].to_dict();ui={v:i for i,v in enumerate(P['dic']['unid'])}
    P['cortes']=[[docs[str(r.doc)],ids['fin'][str(r.fin)],ids['unid'][str(r.unid)],
                  _n(r.cant),_n(r.pprom),_n(r.peso),_n(r.valor),ids['cod_fin'][str(r.cod_fin)],
                  ui[unidad_origen[r.doc]]] for r in cortes.itertuples(index=False)]
    cs=list(dict.fromkeys(c for c in cols.values() if c and c in d))
    origen=pd.util.hash_pandas_object(d[cs],index=True).values.tobytes()+json.dumps([rango and list(map(str,rango)),contexto],sort_keys=True,ensure_ascii=False).encode()
    P['sello_origen']=hashlib.sha256(origen).hexdigest()
    P.pop('sello',None)
    P['sello']=hashlib.sha256(json.dumps(P,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return P


def valorar(P,modo):
    """Cambia de base usando los dos costos ya calculados, sin reagrupar cortes."""
    efectivo='hoy' if modo=='hoy' and P['precios_disponibles'] else 'dia'
    Q=dict(P);Q['valoracion_solicitada']=modo;Q['valoracion']=efectivo
    Q['porciones']={}
    for doc,p in P['porciones'].items():
        costo=p['costoHoy'] if efectivo=='hoy' else p['costoDia']
        valor=p['valorHoy'] if efectivo=='hoy' else p['valorDia']
        Q['porciones'][doc]={**p,'costo':costo,'pctMonetario':valor/costo*100 if costo else None}
    Q['filas']=[]
    for r in P['filas']:
        fila=list(r);p=Q['porciones'][P['dic']['doc'][r[1]]];cant=r[9]
        fila[10]=(p['precioActual'] if efectivo=='hoy' else p['costoDia']/cant) if cant is not None and cant>0 else None
        fila[11]=(p['valorHoy'] if efectivo=='hoy' else p['valorDia']) or 0.0
        Q['filas'].append(fila)
    Q.pop('sello',None)
    Q['sello']=hashlib.sha256(json.dumps(Q,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return Q
