"""Fuentes del cambio de stock, con normalización y alcance originales (#738).
Desde la #747, con los dos relojes: el período, los conteos que caen adentro
y el balance del OTRO reloj por área y familia («Los dos relojes»)."""
import hashlib
import json
import math

import pandas as pd
import kardex
from . import inventario_movimientos as im


def _base(d,col_cod_area,col_cod,col_area,col_prod,col_fam=None,col_punit=None):
    return pd.DataFrame(dict(area_cod=im._texto(d[col_cod_area]),cod=im._texto(d[col_cod]),
        area=im._texto(d[col_area]),producto=im._texto(d[col_prod]),familia=im._texto(d[col_fam]) if col_fam else '',
        precio_hoy=pd.to_numeric(d[col_punit],errors='coerce') if col_punit else float('nan')))


def _foto(f,claves=None):
    """La foto con sus columnas de siempre; con `claves`, sólo las de la base
    y sin las filas en cero, que no suman nada (la foto trae TODO el kardex)."""
    if f is None or f.empty:return pd.DataFrame(columns=["area","cod","stock","precio"])
    out=pd.DataFrame({**{k:im._texto(f[k]) for k in ['area','cod']},
        **{k:pd.to_numeric(f[k],errors='coerce').fillna(0) for k in ['stock','precio']}})
    if claves is not None:
        out=out[pd.MultiIndex.from_frame(out[['area','cod']]).isin(claves)&(out.stock.abs()>1e-12)]
    return out.reset_index(drop=True)


def _movs(mov,claves=None):
    mc=['val_in','val_out','movs','anul','cant_sin_costo','movs_sin_costo']
    m=pd.DataFrame({**{k:im._texto(mov[v]) for k,v in dict(area_cod='area',cod='cod',tipo='tipo',nombre='nombre').items()},
                    **{c:pd.to_numeric(mov[c],errors='coerce').fillna(0) for c in mc}})
    if claves is not None:
        m=m[pd.MultiIndex.from_frame(m[['area_cod','cod']]).isin(claves)]
    m['grupo']=m.tipo.map(kardex.grupo_de)
    return m.reset_index(drop=True)


def armar(d,mov,foto_ini,foto_fin,*,col_cod_area,col_cod,col_area,col_prod,col_fam=None,col_punit=None,desde,hasta,contexto=None,
          reloj='cal',periodo=None,conteos=None,otro=None,comparable=False):
    """Lo que viaja a la pieza. Los movimientos y las fotos llegan ya acotados
    a las áreas y productos de la base (la pieza no usa los demás, y las fotos
    traen el kardex entero: medido, 2,3 MB contra 1 MB). `reloj` es «op»
    (de conteo a conteo) o «cal» (fechas del calendario); `periodo`, la
    ventana del reloj de conteo; `conteos`, las sesiones que caen en el
    rango del calendario; `otro`, lo de `resumen_por_area` del otro reloj
    para el mismo mes (o None); `comparable`, si el rango del calendario es un
    mes entero con su período de conteo."""
    base=_base(d,col_cod_area,col_cod,col_area,col_prod,col_fam,col_punit)
    claves=pd.MultiIndex.from_frame(base[['area_cod','cod']]).unique()
    m=_movs(mov,claves)
    def serial(df):
        def valor(v):
            if pd.isna(v):return None
            if isinstance(v,str):return v
            return float(v) if math.isfinite(float(v)) else None
        return dict(columnas=list(df.columns),filas=[[valor(v) for v in r] for r in df.itertuples(index=False,name=None)])
    P=dict(version=747,base=serial(base),mov=serial(m),ini=serial(_foto(foto_ini,claves)),fin=serial(_foto(foto_fin,claves)),
        grupos=[list(g) for g in kardex.GRUPOS],grupos_area=[list(g) for g in im._COLS_AREA],desde=str(desde),hasta=str(hasta),
        areas=sorted(set(base.area)-{''}),familias=sorted(set(base.familia)-{''}),contexto=contexto or {},
        reloj='op' if reloj=='op' else 'cal',periodo=periodo,conteos=conteos or [],otro=otro,comparable=bool(comparable))
    P['rotulos']={s:im.nombre_propio(s) for s in set(P['areas']+P['familias'])}
    P['sello']=hashlib.sha256(json.dumps(P,ensure_ascii=False,allow_nan=False,sort_keys=True).encode()).hexdigest()
    return P


def resumen_por_area(d,mov,foto_ini,foto_fin,*,col_cod_area,col_cod,col_area,col_prod,col_fam=None,col_punit=None,**_):
    """El balance de un reloj por área y familia: `{columnas, filas}` con
    `area`, `familia`, `ini`, `fin` y el neto de cada grupo de
    `kardex.GRUPOS`. Es el OTRO reloj de «Los dos relojes» (regla #747): no
    viaja por producto —sería otra vez la pieza entera—, así que se puede
    filtrar por área y familia pero no por la búsqueda. Cada área y producto
    toma la PRIMERA fila de la base, como la pieza sin filtros."""
    base=_base(d,col_cod_area,col_cod,col_area,col_prod,col_fam,col_punit).drop_duplicates(['area_cod','cod'])
    claves=pd.MultiIndex.from_frame(base[['area_cod','cod']]).unique()
    llave=base[['area_cod','cod','area','familia']]
    m=_movs(mov,claves).merge(llave,on=['area_cod','cod'])
    m['neto']=m.val_in-m.val_out
    grupos=[g for g,_ in kardex.GRUPOS]
    columnas=['area','familia','ini','fin',*grupos]
    netos=(m.groupby(['area','familia','grupo'])['neto'].sum().unstack('grupo')
           if not m.empty else pd.DataFrame(columns=grupos))
    def puntas(f,nombre):
        x=_foto(f,claves).rename(columns={'area':'area_cod'}).merge(llave,on=['area_cod','cod'])
        return (x.stock*x.precio).groupby([x.area,x.familia]).sum().rename(nombre)
    partes=[p for p in (puntas(foto_ini,'ini'),puntas(foto_fin,'fin'),netos.reindex(columns=grupos)) if len(p)]
    if not partes:return dict(columnas=columnas,filas=[])
    tabla=pd.concat(partes,axis=1).reindex(columns=columnas[2:]).fillna(0.0)
    # Por NOMBRE: la forma de un concat de índices dobles no es la misma en
    # pandas 2 y 3 (regla #481).
    tabla.index=tabla.index.set_names(['area','familia'])
    tabla=tabla.reset_index()
    filas=[[r['area'],r['familia'],*[float(r[c]) for c in columnas[2:]]] for r in tabla.to_dict('records')]
    return dict(columnas=columnas,filas=filas)
