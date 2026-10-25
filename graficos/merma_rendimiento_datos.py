"""Historia de Rendimiento: cabeceras únicas, cortes y referencias (#730)."""
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


def armar(d_hist,cols,precios=None,compras=None,*,rango=None,contexto=None):
    fin=mm.fin_de_ventana(d_hist,rango)
    ventanas={k:dict(ini=_f(fin-pd.DateOffset(months=n)),fin=_f(fin),
                    rotulo=mm._rotulo_ventana(fin-pd.DateOffset(months=n),fin))
              for k,n in mm.VENTANAS.items()} if pd.notna(fin) else {}
    d=d_hist[(d_hist['_fecha']>=fin-pd.Timedelta(days=mm.DIAS_NORMAL))&(d_hist['_fecha']<fin)] if pd.notna(fin) else d_hist.iloc[:0]
    base,cortes=mm.porcionamientos(d,cols)
    b=mm.con_proveedor(mm.valorizar(base,mm.VALOR_DIA,precios),compras if len(base) else None)
    productos=[];ids={}
    for r in b.itertuples(index=False):
        key=(str(r.cod),str(r.unid))
        if key not in ids:
            ids[key]=len(productos);precio=_n(precios.get(key[0],float('nan'))) if precios is not None else None
            productos.append(dict(cod=key[0],unid=key[1],nombre=str(r.prod),precio=precio))
    # El código temporal sólo separa unidades para las referencias del producto.
    # La valorización y la atribución ya usaron su código original.
    b=b.assign(cod=[str(ids[(str(r.cod),str(r.unid))]) for r in b.itertuples(index=False)])
    norm=mm.normales(b);b=mm.marcar(b,norm,cortes)
    normas={k:{c:_n(r[c]) for c in ['n','q1','med','q3']} for k,r in norm.iterrows()}
    filas=[]
    for r in b.itertuples(index=False):
        filas.append(dict(doc=str(r.doc),fecha=_f(r.fecha),prod=int(r.cod),area=str(r.area),usuario=str(r.tipo),
            cant=_n(r.cant),merma=_n(r.merma_cant),pct=_n(r.pct),costo=_n(r.costo_dia),
            valorDia=_n(r.valor_dia),valorHoy=_n(r.valor_hoy),proveedor=str(r.prov) if isinstance(r.prov,str) else None,
            pcompra=_n(r.pcompra),marcas=[k for k in mm.MARCAS if bool(getattr(r,'m_'+k))]))
    claves=mm.clave_corte(cortes);cs=[]
    for (_,r),clave in zip(cortes.iterrows(),claves):
        cs.append(dict(doc=str(r['doc']),clave=str(clave),key=json.dumps([str(clave),str(r['unid'])],ensure_ascii=False,separators=(',',':')),
                       nombre=str(r['fin']),nombreCorto=mm.nombre_corto(r['fin']),cod=str(r['cod_fin']),unid=str(r['unid']),
                       cant=_n(r['cant']),peso=_n(r['peso']),valor=_n(r['valor']),pprom=_n(r['pprom'])))
    P=dict(productos=productos,filas=filas,cortes=cs,normales=normas,ventanas=ventanas,
           reciente=_f(fin-pd.Timedelta(days=mm.DIAS_RECIENTES)),historia_desde=_f(fin-pd.Timedelta(days=mm.DIAS_NORMAL)),
           precios_disponibles=precios is not None,marcas={k:v[0] for k,v in mm.MARCAS.items()},
           min_normal=mm.N_MIN_NORMAL,min_cambios=mm.MIN_PORC_PROVEEDOR,contexto=contexto or {})
    P['sello_origen']=hashlib.sha256(json.dumps([huella(d_hist),huella(compras),cols,str(rango),contexto],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    P['sello']=hashlib.sha256(json.dumps(P,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return P
