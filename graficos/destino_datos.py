"""Transporte fiel de la cuenta de sin_plato; no vuelve a calcularla (#736).

Desde la regla #743 lleva además el reloj con que se fechó la cuenta, las
ventas que cruzan cada conteo, el puente entre los dos relojes y el balance
por área: lo que dibuja el flujo de «En qué se fue cada producto»."""
import hashlib
import json
import math

import pandas as pd
import sin_plato
from tema import (
    ACENTO, ACENTO_TEXTO, BLANCO, COLORES_FLUJO_DESTINO, GRIS_BORDE, GRIS_FONDO,
    GRIS_LINEA, GRIS_TEXTO, LAVANDA_FONDO, TEXTO_PRINCIPAL,
)

IDENTIDAD=('cod','producto','unidad','familia','clase')
_MESES=('ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic')
_TILDES={'ALMACEN':'Almacén','PRODUCCION':'Producción','SALON':'Salón','PASTELERIA':'Pastelería',
    'CHARCUTERIA':'Charcutería','FRIOS':'Fríos','LIMPIEZA':'Limpieza'}


def nombre_area(n):
    """«VENTA INTERNA» → «Venta Interna», con las tildes que el POS no pone."""
    return ' '.join(_TILDES.get(w,w.capitalize() if len(w)>1 else w.lower()) for w in str(n).split())


def _hora(t):
    t=pd.Timestamp(t)
    return f"{t.day} {_MESES[t.month-1]} {t:%H:%M}"


def subtitulo_operativo(p,nombres):
    """El período del reloj operativo: del corte de la mayoría al de la
    mayoría, y las áreas que se contaron en otro momento."""
    t0,t1=pd.Timestamp(p['t0']),pd.Timestamp(p['t1'])
    aparte=sorted(((w[1],a) for a,w in (p.get('ventanas') or {}).items() if pd.Timestamp(w[1])!=t1),reverse=True)
    extra=''.join(f" ({'; '.join(nombre_area(nombres.get(a,a))+', hasta el '+_hora(t) for t,a in aparte[:2])})") if aparte else ''
    return (f"Del {_hora(t0)} al {_hora(t1)}, de conteo a conteo de cada área"
            f"{extra} · el restaurante entero")


def _cortes(p,nombres):
    """Dónde terminó cada área: `[[nombre, fin ISO], …]`, del más tardío."""
    v=p.get('ventanas') or {}
    return [[nombre_area(nombres.get(a,a)),pd.Timestamp(w[1]).isoformat()]
            for a,w in sorted(v.items(),key=lambda x:pd.Timestamp(x[1][1]),reverse=True)]


def _areas_json(areas):
    """`sin_plato.por_area` con las claves de área como texto, que es como
    las lee el navegador."""
    return {cl:[dict(x,areas={str(a):v for a,v in x['areas'].items()},
                     detalle={str(a):v for a,v in x['detalle'].items()}) for x in xs]
            for cl,xs in (areas or {}).items()}


def armar(per,filas,tot,contexto=None,extra=None):
    from . import movimientos_destino as md
    extra=extra or {}
    reloj=extra.get('reloj','kardex');nombres=extra.get('nombres_area') or {}
    def numero(v):
        return float(v) if pd.notna(v) and math.isfinite(float(v)) else None
    columnas=[c for c in filas.columns if c not in IDENTIDAD]
    meta=[];indices={};rows=[]
    for r in filas.to_dict('records'):
        clave=tuple('' if pd.isna(r[c]) else str(r[c]) for c in IDENTIDAD)
        if clave not in indices:indices[clave]=len(meta);meta.append(clave)
        rows.append([indices[clave],*[numero(r[c]) for c in columnas]])
    tk=tot.set_index('k');periodos=[];per_op=extra.get('per_operativo') or []
    for k,p in enumerate(per):
        po=per_op[k] if k<len(per_op) else None
        periodo={c:str(p[c]) for c in ('clave','nombre','corto','desde','hasta','cierre','cierre_ant')}
        dias=p.get('dias')
        periodo.update(k=k,dias=round(float(dias),2) if dias is not None else (p['hasta']-p['desde']).days+1,
            t0=pd.Timestamp(p.get('t0',p['desde'])).isoformat(),
            t1=pd.Timestamp(p.get('t1',pd.Timestamp(p['hasta'])+pd.Timedelta(days=1))).isoformat(),
            subtitulo=subtitulo_operativo(p,nombres) if reloj=='operativo' and p.get('ventanas') else md._subtitulo(p),
            cortes_op=_cortes(po,nombres) if po else [],t1_op=pd.Timestamp(po['t1']).isoformat() if po else '',
            kpis=md._kpis(tk.loc[k],tk.loc[k-1] if k else None,per[k-1] if k else None),ecuacion=md._ecuacion(tk.loc[k]))
        periodos.append(periodo)
    borde=extra.get('borde')
    bk={} if borde is None or borde.empty else {int(r.k):[round(float(r.fin),2),round(float(r.ini),2),round(float(r.nunca),2)] for r in borde.itertuples(index=False)}
    puente={r:[{c:(round(float(v),2) if isinstance(v,float) else v) for c,v in x.items()} for x in xs]
            for r,xs in (extra.get('puente') or {}).items()}
    P=dict(version=743,identidad=list(IDENTIDAD),columnas=columnas,productos=meta,filas=rows,
        periodos=periodos,totales=[{c:numero(v) for c,v in r.items()} for r in tot.to_dict('records')],
        alimentos=sin_plato.ALIMENTOS,operacion=sin_plato.OPERACION,colores=md.C,
        colores_flujo=COLORES_FLUJO_DESTINO,
        contexto=contexto or {},cierres_grafico=md.CIERRES_GRAFICO,
        reloj=reloj,borde=[bk.get(k,[0.0,0.0,0.0]) for k in range(len(per))],puente=puente,
        areas=_areas_json(extra.get('areas')),cols_area=list(sin_plato._COLS_AREA),
        nombres_area={str(a):nombre_area(n) for a,n in nombres.items()},
        areas_familias=bool((contexto or {}).get('Familias de la página')),
        tema_flujo=dict(acento=ACENTO,activo=ACENTO_TEXTO,panel=BLANCO,
            fondo=GRIS_FONDO,borde=GRIS_BORDE,linea=GRIS_LINEA,
            suave=GRIS_TEXTO,seleccion=LAVANDA_FONDO,texto=TEXTO_PRINCIPAL))
    P['sello']=hashlib.sha256(json.dumps(P,ensure_ascii=False,allow_nan=False,sort_keys=True,default=str).encode()).hexdigest()
    return P
