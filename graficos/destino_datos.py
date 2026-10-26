"""Transporte fiel de la cuenta de sin_plato; no vuelve a calcularla (#736)."""
import hashlib
import json
import math

import pandas as pd
import sin_plato
from tema import (
    ACENTO, ACENTO_TEXTO, BLANCO, GRIS_BORDE, GRIS_FONDO, GRIS_LINEA,
    GRIS_TEXTO, LAVANDA_FONDO, TEXTO_PRINCIPAL,
)

IDENTIDAD=('cod','producto','unidad','familia','clase')


def armar(per,filas,tot,contexto=None):
    from . import movimientos_destino as md
    def numero(v):
        return float(v) if pd.notna(v) and math.isfinite(float(v)) else None
    columnas=[c for c in filas.columns if c not in IDENTIDAD]
    meta=[];indices={};rows=[]
    for r in filas.to_dict('records'):
        clave=tuple('' if pd.isna(r[c]) else str(r[c]) for c in IDENTIDAD)
        if clave not in indices:indices[clave]=len(meta);meta.append(clave)
        rows.append([indices[clave],*[numero(r[c]) for c in columnas]])
    tk=tot.set_index('k');periodos=[]
    for k,p in enumerate(per):
        periodo={c:str(p[c]) for c in ('clave','nombre','corto','desde','hasta','cierre','cierre_ant')}
        periodo.update(k=k,dias=(p['hasta']-p['desde']).days+1,subtitulo=md._subtitulo(p),
            kpis=md._kpis(tk.loc[k],tk.loc[k-1] if k else None,per[k-1] if k else None),ecuacion=md._ecuacion(tk.loc[k]))
        periodos.append(periodo)
    P=dict(version=736,identidad=list(IDENTIDAD),columnas=columnas,productos=meta,filas=rows,
        periodos=periodos,totales=[{c:numero(v) for c,v in r.items()} for r in tot.to_dict('records')],
        alimentos=sin_plato.ALIMENTOS,operacion=sin_plato.OPERACION,colores=md.C,
        contexto=contexto or {},cierres_grafico=md.CIERRES_GRAFICO,
        tema_flujo=dict(acento=ACENTO,activo=ACENTO_TEXTO,panel=BLANCO,
            fondo=GRIS_FONDO,borde=GRIS_BORDE,linea=GRIS_LINEA,
            suave=GRIS_TEXTO,seleccion=LAVANDA_FONDO,texto=TEXTO_PRINCIPAL))
    P['sello']=hashlib.sha256(json.dumps(P,ensure_ascii=False,allow_nan=False,sort_keys=True).encode()).hexdigest()
    return P
