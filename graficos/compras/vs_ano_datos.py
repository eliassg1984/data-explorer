"""Vs año pasado nativo: calendario y emparejamiento originales (#725)."""
import hashlib
import json

import pandas as pd

from graficos import periodo
from . import vs_ano_pasado as vp

TODAS='__todas__'


def huella(d,cols):
    if d is None:
        return None
    cs=list(dict.fromkeys(c for c in cols.values() if c and c in d))
    return hashlib.sha256(pd.util.hash_pandas_object(d[cs],index=True).values.tobytes()).hexdigest()


def armar(d,cols,d_full=None,contexto=None):
    fuente=d_full if d_full is not None else d
    fuente=fuente if fuente is not None else pd.DataFrame(columns=[c for c in cols.values() if c])
    prod,fe,val,cant=(cols[k] for k in ['prod','fecha','valor','cant'])
    fam,sub,um=(cols.get(k) for k in ['fam','sub','um'])
    nombres=sorted(fuente[prod].astype(str).unique()) if prod in fuente else []
    ids={p:i for i,p in enumerate(nombres)}
    familias=sorted(fuente[fam].dropna().astype(str).unique()) if fam and fam in fuente else []
    fuentes=[(TODAS,fuente)]+[(f,fuente[fuente[fam].astype(str)==f]) for f in familias]
    heredado=pd.to_datetime(d[fe],errors='coerce').dropna() if d is not None and fe in d else pd.Series(dtype='datetime64[ns]')
    hereda=[str(heredado.min().to_period('M')),str(heredado.max().to_period('M'))] if len(heredado) else None
    planes={}
    for nombre,src in fuentes:
        parcial=vp._mes_parcial(src[fe]) if fe in src else None
        g0=vp._mensual(src,prod,fe,val,cant)
        gh=g0 if parcial is None else vp._mensual(src,prod,fe,val,cant,recorte=(parcial[0]-12,parcial[1]))
        g=vp._con_ano_pasado(g0,gh)
        presentes={(str(r.prod),str(r.mes)) for r in g0.itertuples()}
        anteriores={(str(r.prod),str(r.mes+12)) for r in gh.itertuples()}
        filas=[[ids[str(r.prod)],str(r.mes),float(r.valor),float(r.cant),float(r.valor_aa),float(r.cant_aa),
                (str(r.prod),str(r.mes)) in presentes,(str(r.prod),str(r.mes)) in anteriores] for r in g.itertuples()]
        mapas={}
        for agrup,col in [('Producto',prod),('Familia',fam),('Subfamilia',sub)]:
            if col and col in src:
                mapa=src[[prod,col]].astype(str).drop_duplicates(prod).set_index(prod)[col] if col!=prod else None
                mapas[agrup]={str(ids[n]):n if mapa is None else str(mapa.get(n,n)) for n in src[prod].astype(str).unique()}
        unidades=vp._unidades_por(src,prod,um)
        ventanas={}
        meses=sorted(g.mes.unique()) if len(g) else []
        for op in periodo.OPCIONES:
            if op==periodo.HEREDA:
                ventanas[op]=[str(m) for m in meses if hereda and hereda[0]<=str(m)<=hereda[1]]
            elif meses:
                rng=periodo.ventana(op,meses[-1].to_timestamp(how='end'),meses[0].to_timestamp())
                ventanas[op]=[str(m) for m in meses if rng and rng[0].to_period('M')<=m<=rng[1].to_period('M')]
            else:
                ventanas[op]=[]
        planes[nombre]=dict(filas=filas,mapas=mapas,unidades={str(ids[p]):u for p,u in unidades.items() if p in ids},
                            ventanas=ventanas,parcial=[str(parcial[0]),parcial[1]] if parcial else None)
    meses=sorted({r[1] for p in planes.values() for r in p['filas']})
    payload=dict(productos=nombres,familias=familias,planes=planes,opciones=list(periodo.OPCIONES),
                 etiquetas={op:'Rango de la página' if op==periodo.HEREDA else periodo.etiqueta(op).capitalize() for op in periodo.OPCIONES},
                 meses={m:vp._etiqueta_mes(pd.Period(m,freq='M')) for m in meses},
                 meses_aa={m:vp._etiqueta_mes(pd.Period(m,freq='M')-12) for m in meses},
                 max_pasos=vp._TOPE_CASCADA,contexto=contexto or {},hereda=hereda)
    payload['sello']=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False,
                                           separators=(',',':')).encode()).hexdigest()
    return payload
