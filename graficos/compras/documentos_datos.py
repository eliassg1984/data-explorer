"""Líneas y calendario de Detalle docs.; misma normalización de Proveedor (#726)."""
import hashlib
import json

import pandas as pd

from ._comun import agregar_periodo, documento_legible
from ._etiquetas_proveedor import nombre_propio

GRANOS=('Día','Semana','Mes','Año')


def leer_seleccion(estado,clave,universo):
    """Mismo default/fallback del filtro canónico, sin crear sus widgets.

    El ranking dibuja los suyos; los de documentos viven en JavaScript.
    No se inicializan ni escriben claves que pertenecen a otra sección.
    """
    reales=[p for p in universo if p!='Otros']
    return [p for p in universo if estado.get(f'{clave}_cb::{p}',p in reales)] or reales


def _iso(f):
    return None if pd.isna(f) else pd.Timestamp(f).strftime('%Y-%m-%d')


def _numero(v):
    return None if pd.isna(v) else float(v)


def armar(base,top_provs,*,col_docu=True,col_punit=True,contexto=None,rango=None):
    b=base[base['prov'].isin(top_provs)].copy()
    b['fecha']=pd.to_datetime(b['fecha'],errors='coerce').dt.normalize()
    proveedores=list(dict.fromkeys(p for p in top_provs if p in set(b.prov)))
    productos=sorted(b['prod'].astype(str).unique())
    unidades=sorted(b['um'].fillna('').astype(str).unique())
    fechas=sorted(b['fecha'].dropna().map(_iso).unique())
    if b.fecha.isna().any():fechas.append(None)
    pi={v:i for i,v in enumerate(proveedores)};pr={v:i for i,v in enumerate(productos)}
    ui={v:i for i,v in enumerate(unidades)};fi={v:i for i,v in enumerate(fechas)}
    cal={};df=pd.DataFrame({'fecha':pd.to_datetime(fechas)})
    varios=len({f[:4] for f in fechas if f})>1
    for gran in GRANOS:
        g=agregar_periodo(df.copy(),gran);por_fecha=['~sinfecha']*len(fechas);rotulos={}
        for i,k,r in zip(g.index,g['_per_sort'],g['per']):
            if fechas[i] is None:continue
            k=str(k);por_fecha[i]=k
            rotulos[k]=str(r)+((' · '+k[:4]) if varios and gran in ('Día','Semana') else '')
        if None in fechas:rotulos['~sinfecha']='Sin fecha'
        cal[gran]=dict(por_fecha=por_fecha,rotulos=rotulos,orden=sorted(rotulos))
    docs=[];di={};lineas=[]
    legibles=documento_legible(b['docu'].astype(str)).tolist()
    for pos,(r,leg) in enumerate(zip(b.itertuples(index=False),legibles)):
        fecha=_iso(r.fecha);raw=str(r.docu).strip() if col_docu else ''
        identificado=bool(raw and raw.lower() not in ('nan','none','nat','<na>'))
        llave=(r.prov,fecha,raw) if identificado else (r.prov,fecha,'~linea',pos)
        if llave not in di:
            di[llave]=len(docs)
            estable=hashlib.sha256(json.dumps(llave,ensure_ascii=False).encode()).hexdigest()[:24]
            docs.append([estable,pi[r.prov],fi[fecha],raw if identificado else '',str(leg) if identificado else 'Sin número',identificado])
        lineas.append([pi[r.prov],pr[str(r.prod)],fi[fecha],di[llave],float(r.cant),float(r.valor),
                       _numero(r.punit) if col_punit else None,ui[str(r.um) if pd.notna(r.um) else '']])
    P=dict(proveedores=[[p,nombre_propio(p)] for p in proveedores],productos=productos,unidades=unidades,
           fechas=fechas,documentos=docs,lineas=lineas,calendario=cal,granos=list(GRANOS),
           contexto=contexto or {},rango=[_iso(f) for f in rango] if rango else None)
    P['sello']=hashlib.sha256(json.dumps(P,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return P
