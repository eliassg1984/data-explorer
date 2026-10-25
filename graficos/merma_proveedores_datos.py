"""Cabeceras y compras atribuidas para costo por unidad útil (#729)."""
import hashlib
import json
import math

import pandas as pd

from . import movimientos_merma as mm


def huella(d):
    return hashlib.sha256(pd.util.hash_pandas_object(d,index=True).values.tobytes()).hexdigest() if d is not None else None


def _n(v):
    return float(v) if pd.notna(v) and math.isfinite(float(v)) else None


def _fecha(v):
    return pd.Timestamp(v).isoformat() if pd.notna(v) else None


def armar(d_hist,cols,compras,*,rango=None,contexto=None):
    fin=mm.fin_de_ventana(d_hist,rango)
    ventanas={k:dict(ini=_fecha(fin-pd.DateOffset(months=n)),fin=_fecha(fin),
                    rotulo=mm._rotulo_ventana(fin-pd.DateOffset(months=n),fin))
              for k,n in mm.VENTANAS.items()} if pd.notna(fin) else {}
    d=d_hist[(d_hist['_fecha']>=fin-pd.DateOffset(months=18))&(d_hist['_fecha']<fin)] if pd.notna(fin) else d_hist.iloc[:0]
    base,_=mm.porcionamientos(d,cols)
    b=mm.con_proveedor(base,compras if len(base) else None)
    productos=[];grupos={}
    for r in b.itertuples(index=False):
        key=(str(r.cod),str(r.unid))
        if key not in grupos:
            grupos[key]=len(productos)
            productos.append(dict(cod=key[0],unid=key[1],nombre=str(r.prod)))
    provs=sorted(b['prov'].dropna().astype(str).unique().tolist())
    pi={v:i for i,v in enumerate(provs)};rastros={}
    for (_,prov),g in b[b['prov'].notna()].groupby(['cod','prov'],sort=False):
        for r in mm.rastro_proveedor(g,compras,prov).itertuples(index=False):
            rastros[str(r.doc)]=r
    filas=[]
    for r in b.itertuples(index=False):
        t=rastros.get(str(r.doc))
        filas.append(dict(doc=str(r.doc),fecha=_fecha(r.fecha),area=str(r.area),
            prod=grupos[(str(r.cod),str(r.unid))],prov=pi.get(str(r.prov)) if pd.notna(r.prov) else None,
            unico=bool(r.unico),cant=_n(r.cant),merma=_n(r.merma_cant),costo=_n(r.costo_dia),
            pct=_n(r.pct),dias=_n(r.dias),pcompra=_n(r.pcompra),
            compra=_fecha(t.compra) if t is not None else None,
            otro=str(t.otro) if t is not None and isinstance(t.otro,str) else None,
            f_otro=_fecha(t.f_otro) if t is not None else None,
            difiere=bool(t.difiere) if t is not None else False))
    P=dict(productos=productos,proveedores=provs,filas=filas,ventanas=ventanas,
           compras_disponibles=compras is not None,contexto=contexto or {},
           min_porc=mm.MIN_PORC_PROVEEDOR,dias_proveedor=mm.DIAS_PROVEEDOR,dias_unico=mm.DIAS_UNICO)
    P['sello']=hashlib.sha256(json.dumps(P,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return P
