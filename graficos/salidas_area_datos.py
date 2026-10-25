"""Fuentes de Salidas por Área: ventana y entradas canónicas (#735)."""
import hashlib
import json
import math

import pandas as pd

from graficos import movimientos_bajas as mb
from graficos.drill_tablas import claves, SIN_DATO, texto_cat


def num(v):
    if v is None or pd.isna(v):return None
    x=float(v)
    return x if math.isfinite(x) else None


def normalizar(raw,cols,niveles):
    l=mb.lineas_salidas(raw,**{k:cols.get(k) for k in ('fecha','doc','cod','prod','cant','valor','unid','causa','area','tipo','motivo')})
    for k,c in niveles.items():l['ruta_'+k]=claves(raw,c).fillna(SIN_DATO).reindex(l.index) if c and c in raw else SIN_DATO
    return l


def armar(lin,lin_vent,entradas,vent,*,anterior=None,rango=None,nota=None,rotulo_ant='',sin_comparar=(),aviso=None,disponibles=None,contexto=None):
    L=lin.copy();V=lin_vent[(lin_vent.fecha>=vent[0])&(lin_vent.fecha<vent[1])].copy();A=anterior if anterior is not None else L.iloc[:0]
    rutas={k:[] for k in ('tipo','causa','area','fam','subfam')};productos=[];codigos={};docs=[];causas=[];motivos=[]
    mapas={id(xs):{} for xs in [*rutas.values(),docs,causas,motivos]}
    def idx(xs,v):
        m=mapas[id(xs)]
        if v not in m:m[v]=len(xs);xs.append(v)
        return m[v]
    todos=pd.concat([L,V,A],ignore_index=True)
    for c,p,u in todos[['cod','prod','unid']].itertuples(index=False,name=None):
        if c not in codigos:codigos[c]=len(productos);productos.append([c,p,u])
    def filas(d):
        return [[codigos[r.cod],*[idx(xs,getattr(r,'ruta_'+k)) for k,xs in rutas.items()],
            idx(docs,r.doc),pd.Timestamp(r.fecha).isoformat(),num(r.cant),num(r.valor),idx(causas,r.causa),idx(motivos,r.motivo)] for r in d.itertuples(index=False)]
    rango_f=filas(L);ventana_f=filas(V);ant_f=filas(A);e=[]
    if entradas is not None and len(entradas):
        ent=entradas[(entradas.fecha>=vent[0])&(entradas.fecha<vent[1])&entradas.cod.isin(codigos)]
        e=[[codigos[r.cod],pd.Timestamp(r.fecha).isoformat(),num(r.cant)] for r in ent.itertuples(index=False)]
    P=dict(productos=productos,rutas=rutas,docs=docs,causas=causas,motivos=motivos,rango=rango_f,ventana=ventana_f,anterior=ant_f,entradas=e,
        entradas_disponibles=entradas is not None,compara=anterior is not None,rotulo_ant=rotulo_ant,sin_comparar=list(sin_comparar),aviso=list(aviso or []),
        disponibles=disponibles or {k:True for k in rutas},nota=list(nota or []),contexto=contexto or {},
        desde=str(pd.Timestamp(vent[0]).date()),hasta=str(pd.Timestamp(vent[1]).date()),meses=mb.meses_de_ventana(vent),
        rango_desde=str(pd.Timestamp(rango[0]).date()) if rango else '',rango_hasta=str(pd.Timestamp(rango[1]).date()) if rango else '')
    nombres=dict(tipo='tipo de baja',causa='causa',area='área',fam='familia',subfam='subfamilia')
    P['rotulos']={k:[texto_cat(nombres[k],x) for x in xs] for k,xs in rutas.items()}
    P['sello']=hashlib.sha256(json.dumps(P,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest();return P
