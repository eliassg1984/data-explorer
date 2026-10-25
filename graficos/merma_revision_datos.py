"""Casos de porcionamientos: reglas originales, ambas bases y rastro (#732)."""
import hashlib
import json
import math

import pandas as pd

from . import movimientos_merma as mm


def huella(d):
    return hashlib.sha256(pd.util.hash_pandas_object(d,index=True).values.tobytes()).hexdigest() if d is not None else None


def _n(v):
    return float(v) if pd.notna(v) and math.isfinite(float(v)) else None


def _f(v):
    return pd.Timestamp(v).isoformat() if pd.notna(v) else None


def _clave(r):
    return tuple(None if pd.isna(r[k]) else r[k] for k in ['doc','fin','cod_fin','unid','cant','peso'])


def armar(d_rango,d_hist,cols,precios=None,compras=None,*,rango=None,contexto=None):
    base,cortes=mm.porcionamientos(d_rango,cols)
    fin=pd.Timestamp(rango[1]) if rango else base['fecha'].max()+pd.Timedelta(days=1)
    historico=d_hist[(d_hist['_fecha']<fin)&(d_hist['_fecha']>=fin-pd.Timedelta(days=mm.DIAS_NORMAL))] if pd.notna(fin) else d_hist.iloc[:0]
    hist,cs_hist=mm.porcionamientos(historico,cols)
    grupos={};productos=[]
    for df in [base,hist]:
        for r in df.itertuples(index=False):
            key=(str(r.cod),str(r.unid))
            if key not in grupos:
                grupos[key]=str(len(productos));productos.append(dict(cod=key[0],unid=key[1],nombre=str(r.prod)))
    h=hist.assign(cod=[grupos[(str(r.cod),str(r.unid))] for r in hist.itertuples(index=False)])
    norm=mm.normales(h)
    pesos_partes=[]
    for (_,u),g in hist.groupby(['cod','unid'],sort=False):
        sc=cs_hist[cs_hist.doc.isin(g.doc)]
        for _,cs in sc.groupby('unid',sort=False):
            pesos_partes.append(mm.pesos_por_unidad(g,cs))
    pesos=pd.concat(pesos_partes,ignore_index=True) if pesos_partes else None
    b=mm.valorizar(mm.con_proveedor(base,compras if len(base) else None),mm.VALOR_DIA,precios)
    codigos={str(r.doc):str(r.cod) for r in b.itertuples(index=False)}
    b=b.assign(cod=[grupos[(str(r.cod),str(r.unid))] for r in b.itertuples(index=False)])
    b=mm.marcar(b,norm,cortes,pesos)
    peso_por_linea={_clave(r):r for _,r in pesos.iterrows()} if pesos is not None else {}
    filas=[];por_doc={};cs=[];carta=[]
    for r in b.itertuples(index=False):
        precio=_n(precios.get(codigos[str(r.doc)],float('nan'))) if precios is not None else None
        p=dict(doc=str(r.doc),fecha=_f(r.fecha),prod=int(r.cod),area=str(r.area),usuario=str(r.tipo),cant=_n(r.cant),merma=_n(r.merma_cant),pct=_n(r.pct),
               costoDia=_n(r.costo_dia),valorDia=_n(r.valor_dia),valorHoy=_n(r.valor_hoy),precioDia=_n(r.costo_dia/r.cant),precioHoy=precio if precio is not None else 0.0 if precios is not None else None,precioDisponible=precio is not None,
               proveedor=str(r.prov) if isinstance(r.prov,str) else None,pcompra=_n(r.pcompra),dias=_n(r.dias),
               normal={k:_n(getattr(r,k)) for k in ['n','q1','med','q3']},dpeso=_n(r.dpeso),pctCorr=_n(r.pct_corr),
               marcas=[k for k in mm.MARCAS if bool(getattr(r,'m_'+k))])
        filas.append(p);por_doc[str(r.doc)]=(r,p)
    for _,r in cortes.iterrows():
        t=peso_por_linea.get(_clave(r));header=por_doc.get(str(r['doc']))
        if header is None:continue
        raro=bool(t['raro']) and 'peso' in header[1]['marcas'] if t is not None and header else False
        c=dict(doc=str(r['doc']),nombre=str(r['fin']),corto=mm.nombre_corto(r['fin']),cod=str(r['cod_fin']),unid=str(r['unid']),
               cant=_n(r['cant']),peso=_n(r['peso']),valor=_n(r['valor']),pprom=_n(r['pprom']),
               kgu=_n(r['peso']/r['cant']) if r['cant']>0 else None,hab=_n(t['hab']) if t is not None else None,raro=raro)
        if raro and header:
            f=pd.Series(header[0]._asdict());linea=pd.Series({**r.to_dict(),'hab':t['hab']});p_corr=_n(mm.precio_con_peso_habitual(f,linea));p_hoy=_n(precios.get(c['cod'],float('nan'))) if precios is not None else None
            c['precioCorregido']=p_corr;c['precioHoy']=p_hoy
            if p_hoy is not None and c['pprom'] is not None and p_corr is not None and min(p_hoy,c['pprom'],p_corr)>0 and abs(p_hoy-c['pprom'])<=.02*c['pprom'] and abs(c['pprom']-p_corr)>=.1*p_corr:
                c['carta']=len(carta);carta.append(dict(cod=c['cod'],factor=p_corr/p_hoy,platos=[]))
        cs.append(c)
    P=dict(filas=filas,cortes=cs,productos=productos,marcas={k:dict(nombre=v[0],nivel=v[1]) for k,v in mm.MARCAS.items()},
           inicial_marcas=list(mm.MARCAS_DE_ENTRADA),precios_disponibles=precios is not None,compras_disponibles=compras is not None,
           recetas_disponibles=None,carta=carta,rango=[_f(rango[0]),_f(rango[1])] if rango else None,normal_desde=_f(fin-pd.Timedelta(days=mm.DIAS_NORMAL)),contexto=contexto or {})
    P['sello_origen']=hashlib.sha256(json.dumps([huella(d_rango),huella(historico),huella(compras[compras['f']<fin] if compras is not None and pd.notna(fin) else compras),cols,str(rango),contexto],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return sellar(P)


def sellar(P):
    Q=dict(P);Q.pop('sello',None);Q['sello']=hashlib.sha256(json.dumps(Q,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest();return Q


def adjuntar_recetas(P,rv):
    Q=dict(P);Q['recetas_disponibles']=rv is not None;Q['carta']=[]
    for c in P['carta']:
        filas=mm.platos_con_insumo(rv,c['cod'],c['factor'])
        Q['carta'].append({**c,'platos':[dict(nombre=str(r.plato),costo=_n(r.costo),pct=_n(r.pct),costoCorr=_n(r.costo_corr),pctCorr=_n(r.pct_corr)) for r in filas.itertuples(index=False)]})
    return sellar(Q)
