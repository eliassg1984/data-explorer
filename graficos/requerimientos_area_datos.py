"""Fuentes de Requerimientos por Área, sin cambiar las reglas de pedido (#734)."""
import hashlib
import json
import math

import pandas as pd

from graficos import movimientos_requerimientos as mr


def numero(v):
    if v is None or pd.isna(v):
        return None
    n=float(v)
    return n if math.isfinite(n) else None


def normalizar(d,cols,marcas=None,unidades=None):
    l=mr.lineas_req(d,**{k:cols.get(k) for k in ('fecha','doc','sub','cod','prod','cant','valor')})
    if unidades is not None:l['unid']=l['cod'].map(unidades).fillna('')
    for k in ('fam','subfam'):
        c=cols.get(k);l[k]=d[c].fillna('').astype(str).str.strip() if c and c in d else ''
    for k,valor in [('habitual',float('nan')),('veces',0.),('exceso',0.),('nuevo',False),('repite_min',float('nan'))]:
        l[k]=marcas[k].reindex(d.index) if marcas is not None and k in marcas else valor
    return l.dropna(subset=['fecha'])


def armar(lin,lin_vent,vent,kx=None,*,rango=None,nota=None,contexto=None):
    l=lin.copy();v=lin_vent.copy();todos=pd.concat([l,v],ignore_index=True)
    productos=[];codigos={};areas=[];familias=[];subfamilias=[];docs=[]
    mapas={id(xs):{} for xs in (areas,familias,subfamilias,docs)}
    def indice(xs,x):
        m=mapas[id(xs)]
        if x not in m:m[x]=len(xs);xs.append(x)
        return m[x]
    for c,p,u in todos[['cod','prod','unid']].itertuples(index=False,name=None):
        if c not in codigos:codigos[c]=len(productos);productos.append([c,p,u])
    def filas(d):
        out=[]
        for r in d.itertuples(index=False):
            out.append([codigos[r.cod],indice(areas,r.sub),indice(familias,r.fam),indice(subfamilias,r.subfam),
                indice(docs,r.doc),pd.Timestamp(r.fecha).isoformat(),numero(r.cant),numero(r.valor),
                numero(r.habitual),numero(r.veces),numero(r.exceso),bool(r.nuevo) if pd.notna(r.nuevo) else False,numero(r.repite_min)])
        return out
    rango_filas=filas(l);ventana_filas=filas(v)
    meses=vent[2];k= kx[kx['mes'].isin(meses)&kx['cod'].isin(codigos)] if kx is not None else None
    fuentes=[];salida=[]
    if k is not None and not k.empty:
        # El ratio y el criterio de área que descarga son los del helper único.
        sal=mr.salida_por_area(kx,meses)
        for r in sal[sal['cod'].isin(codigos)].itertuples(index=False):
            salida.append([codigos[r.cod],indice(areas,r.area),numero(r.cubre),bool(r.descarga)])
        for r in k.itertuples(index=False):
            fuentes.append([codigos[r.cod],indice(areas,r.area),meses.index(r.mes),*[numero(getattr(r,c)) for c in ('ped','ven','pro','nts','tra','aj')]])
    P=dict(productos=productos,areas=areas,familias=familias,subfamilias=subfamilias,docs=docs,
        rango=rango_filas,ventana=ventana_filas,kardex=fuentes,salida=salida,kardex_disponible=kx is not None,
        meses=meses,desde=str(pd.Timestamp(vent[0]).date()),hasta=str(pd.Timestamp(vent[1]).date()),
        rango_desde=str(pd.Timestamp(rango[0]).date()) if rango else '',
        rango_hasta=str(pd.Timestamp(rango[1]).date()) if rango else '',
        nota=list(nota or []),contexto=contexto or {})
    P['sello']=hashlib.sha256(json.dumps(P,ensure_ascii=False,allow_nan=False,sort_keys=True).encode()).hexdigest()
    return P
