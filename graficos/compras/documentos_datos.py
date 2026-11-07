"""Líneas y calendario de Detalle docs.; misma normalización de Proveedor (#726, #773)."""
import hashlib
import json

import pandas as pd

from ._comun import agregar_periodo, base_normalizada, documento_legible
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


def con_detalle(fuente,cols,extra):
    """La base de `base_normalizada` con lo que dice cada línea y su documento: familia,
    IGV, tipo, hora de ingreso y nota de crédito, y el habitual y la marca de Compras ›
    Producto. `fuente` es el histórico entero, porque el habitual mira 90 días atrás.
    `base_normalizada` conserva la posición de cada fila en su índice. Pura."""
    from .producto import _con_referencia
    b=base_normalizada(fuente,*cols)
    def col(k):
        c=extra.get(k)
        return fuente[c].iloc[b.index] if c and c in fuente.columns else None
    for k,cast in (('fam',str),('tipo',str),('igv',float),('nc',float)):
        v=col(k)
        b[k]=('' if cast is str else 0.0) if v is None else (v.astype(str).str.strip().to_numpy() if cast is str else pd.to_numeric(v,errors='coerce').fillna(0).to_numpy())
    v=col('proc');b['proc']=pd.NaT if v is None else pd.to_datetime(v,errors='coerce').to_numpy()
    ok=b[b['fecha'].notna()&(b['prod'].astype(str).str.strip()!='')]
    h=_con_referencia(ok)
    b['ref']=float('nan');b['flag']=''
    b.loc[h.index,'ref']=h['ref'];b.loc[h.index,'flag']=h['flag']
    return b


def armar(base,top_provs,*,col_docu=True,col_punit=True,contexto=None,rango=None,pagina=None):
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
    con_mas='fam' in b.columns
    familias=sorted({str(f) for f in b['fam'].astype(str)}) if con_mas else []
    fa={f:i for i,f in enumerate(familias)}
    marca={'':0,'um':1,'precio':2}
    for pos,(r,leg) in enumerate(zip(b.itertuples(index=False),legibles)):
        fecha=_iso(r.fecha);raw=str(r.docu).strip() if col_docu else ''
        identificado=bool(raw and raw.lower() not in ('nan','none','nat','<na>'))
        llave=(r.prov,fecha,raw) if identificado else (r.prov,fecha,'~linea',pos)
        if llave not in di:
            di[llave]=len(docs)
            estable=hashlib.sha256(json.dumps(llave,ensure_ascii=False).encode()).hexdigest()[:24]
            d=[estable,pi[r.prov],fi[fecha],raw if identificado else '',str(leg) if identificado else 'Sin número',identificado]
            if con_mas:
                d+=[str(r.tipo),'' if pd.isna(r.proc) else pd.Timestamp(r.proc).strftime('%Y-%m-%d %H:%M')]
            docs.append(d)
        linea=[pi[r.prov],pr[str(r.prod)],fi[fecha],di[llave],float(r.cant),float(r.valor),
               _numero(r.punit) if col_punit else None,ui[str(r.um) if pd.notna(r.um) else '']]
        if con_mas:
            linea+=[float(r.igv),_numero(r.ref),marca.get(str(r.flag),0),fa[str(r.fam)],float(r.nc)]
        lineas.append(linea)
    P=dict(proveedores=[[p,nombre_propio(p)] for p in proveedores],productos=productos,unidades=unidades,
           fechas=fechas,documentos=docs,lineas=lineas,calendario=cal,granos=list(GRANOS),
           contexto=contexto or {},rango=[_iso(f) for f in rango] if rango else None)
    if con_mas:
        P['familias']=[nombre_propio(f) for f in familias]
    if pagina:
        P['pagina'] = dict(todas=[[f, nombre_propio(f), v] for f, v in pagina['todas']],
                           elegidas=list(pagina['elegidas']), en_panel=pagina.get('en_panel', False))
    P['sello']=hashlib.sha256(json.dumps(P,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return P
