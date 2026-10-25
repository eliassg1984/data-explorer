"""Transporta el análisis canónico y sus textos; no recalcula sus pistas (#739)."""
import datetime as dt
import hashlib
import json
import math
from numbers import Integral, Real

import pandas as pd
import diferencias_ajuste as da
from . import _diferencias as dif


def valor(v):
    if v is None:return None
    if isinstance(v,dict):return {str(k):valor(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [valor(x) for x in v]
    if isinstance(v,pd.DataFrame):return valor(v.to_dict('records'))
    if isinstance(v,(str,bool)):return v
    if pd.isna(v):return None
    if isinstance(v,(dt.datetime,dt.date,pd.Timestamp)):return v.isoformat()
    if isinstance(v,Integral):return int(v)
    if isinstance(v,Real):return float(v) if math.isfinite(float(v)) else None
    if hasattr(v,'item'):return valor(v.item())
    return str(v)


def armar(r,contexto=None):
    lin=r['lineas'].assign(area=r['lineas']['area'].astype(str).str.strip());fs=r['fichas'];fichas={}
    for x in lin.to_dict('records'):
        fi=fs[int(x['id'])];f=valor(fi)
        f['html']=dict(cabecera=dif._cabecera_ficha(x),cuenta=dif._cuenta_html(x,fi),
            viene=dif._viene_html(x,fi)+'<div class="dif-h">Quién lo pide (requerimientos, 90 días)</div>'+dif._pide_html(x,fi),
            usos=f'<div class="dif-h">Cómo sale ({da.DIAS_ATRAS} días antes del conteo)</div>'+dif._perfil_html(x,fi)
                 +'<div class="dif-h">Dónde se usa</div><div class="dif-nota">«≈» es recetas × vendido: una referencia, no el kardex. «Receta editada» marca cambios desde el conteo anterior.</div>'+dif._usos_html(x,fi),
            hist=dif._hist_html(fi))
        fichas[str(int(x['id']))]=f
    lote=r.get('resumen',{}).get('lote');meta=None
    if lote and lote.get('ultimo') is not None and pd.notna(lote.get('ultimo')):
        exacto=bool(lote.get('exacto'));meta=dict(ultimo=da.cuando(lote['ultimo'],minutos=exacto),
            siguiente=da.fecha_corta(lote['siguiente']) if lote.get('siguiente') is not None else None,
            desde=da.cuando(lote['desde'],minutos=exacto) if lote.get('desde') is not None else None,
            dias=da.dias_txt(lote.get('dias_antes') or []),exacto=exacto)
    P=dict(version=739,lineas=valor(lin),fichas=fichas,lote=meta,resumen=valor(r.get('resumen') or {}),
           tipos=list(da.TIPOS),nombres=da.NOMBRE_TIPO,eps=da.EPS,contexto=contexto or {})
    P['sello']=hashlib.sha256(json.dumps(P,ensure_ascii=False,allow_nan=False,sort_keys=True).encode()).hexdigest()
    return P
