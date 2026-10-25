"""Fuentes del cambio de stock, con normalización y alcance originales (#738)."""
import hashlib
import json
import math

import pandas as pd
import kardex
from . import inventario_movimientos as im


def armar(d,mov,foto_ini,foto_fin,*,col_cod_area,col_cod,col_area,col_prod,col_fam=None,col_punit=None,desde,hasta,contexto=None):
    base=pd.DataFrame(dict(area_cod=im._texto(d[col_cod_area]),cod=im._texto(d[col_cod]),
        area=im._texto(d[col_area]),producto=im._texto(d[col_prod]),familia=im._texto(d[col_fam]) if col_fam else '',
        precio_hoy=pd.to_numeric(d[col_punit],errors='coerce') if col_punit else float('nan')))
    mc=['val_in','val_out','movs','anul','cant_sin_costo','movs_sin_costo']
    m=pd.DataFrame({**{k:im._texto(mov[v]) for k,v in dict(area_cod='area',cod='cod',tipo='tipo',nombre='nombre').items()},
                    **{c:pd.to_numeric(mov[c],errors='coerce').fillna(0) for c in mc}})
    m['grupo']=m.tipo.map(kardex.grupo_de)
    def foto(f):
        if f.empty:return pd.DataFrame(columns=["area","cod","stock","precio"])
        return pd.DataFrame({**{k:im._texto(f[k]) for k in ['area','cod']},
            **{k:pd.to_numeric(f[k],errors='coerce').fillna(0) for k in ['stock','precio']}})
    def serial(df):
        def valor(v):
            if pd.isna(v):return None
            if isinstance(v,str):return v
            return float(v) if math.isfinite(float(v)) else None
        return dict(columnas=list(df.columns),filas=[[valor(v) for v in r] for r in df.itertuples(index=False,name=None)])
    P=dict(version=738,base=serial(base),mov=serial(m),ini=serial(foto(foto_ini)),fin=serial(foto(foto_fin)),
        grupos=[list(g) for g in kardex.GRUPOS],grupos_area=[list(g) for g in im._COLS_AREA],desde=str(desde),hasta=str(hasta),
        areas=sorted(set(base.area)-{''}),familias=sorted(set(base.familia)-{''}),contexto=contexto or {})
    P['rotulos']={s:im.nombre_propio(s) for s in set(P['areas']+P['familias'])}
    P['sello']=hashlib.sha256(json.dumps(P,ensure_ascii=False,allow_nan=False,sort_keys=True).encode()).hexdigest()
    return P
