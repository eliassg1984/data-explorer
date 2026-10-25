"""Stock por área y familia: mismo grano y análisis de Productos (#724)."""
import hashlib
import json

import pandas as pd

from . import inventario_productos_datos as productos


def armar(d, excluidos, cols, historia=None, consumo=None, contexto=None):
    p=productos.armar(d,cols,historia,consumo)
    ex=productos.armar(excluidos,cols) if excluidos is not None else None
    if ex is not None:
        col=cols.get('motivo')
        ex['motivos']=(excluidos[col].fillna('').astype(str).tolist()
                       if col and col in excluidos else ['Sin motivo']*len(excluidos))
    p['excluidos']=ex
    p['contexto']=contexto or {}
    p['default_area']='ALMACEN CENTRAL' if 'ALMACEN CENTRAL' in p['dic']['area'] else None
    p['hay_cantidad']=bool(cols.get('cant'))
    p['ref_default']=max(0,len(p['meses'])-3)
    p['sello']=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False,allow_nan=False,
                                     separators=(',',':')).encode()).hexdigest()
    return p


def huella(d):
    return (hashlib.sha256(pd.util.hash_pandas_object(d,index=True).values.tobytes()).hexdigest()
            if d is not None else None)
