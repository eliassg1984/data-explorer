"""Movimientos por Tipo de Stock: el reloj y el período son nativos y
consultan las fuentes; lo demás es local (#738). Dos relojes desde la #747:
«De conteo a conteo» (el operativo de Destino, #743) para leer un mes y
«Fechas del calendario» para un rango libre."""
from graficos.movil import css_movil, js_movil
import datetime as dt
import hashlib
import pickle
from pathlib import Path

import streamlit as st
import data
import kardex
from cortes import MESES_LARGOS_ES
from estado_rango import atajos_tarjeta, clave_rango
from graficos.base import eleccion_compartida, rango_tarjeta, selector_fecha_tarjeta
from . import inventario_movimientos as im
from . import inventario_movimientos_datos as datos

_DIR=Path(__file__).parent
_CSS=(_DIR/'inventario_movimientos.css').read_text(encoding='utf-8')
_PIEZA=st.components.v2.component('stock_movimientos_738',css=css_movil(_CSS),
    js=js_movil((_DIR/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'inventario_movimientos.js').read_text(encoding='utf-8')))

CONTEO='De conteo a conteo'
CALENDARIO='Fechas del calendario'
RELOJES=(CONTEO,CALENDARIO)
K_RELOJ='inv_mov_reloj'
K_PERIODO='inv_mov_periodo'
K_COMPARAR='inv_mov_comparar'
K_PIEZA='stock_movimientos_pieza'
CATEGORIA='mov_tipo'
REPORTE='Inventario Valorizado'
_ABR=('ene','feb','mar','abr','may','jun','jul','ago','set','oct','nov','dic')


def ctx_calendario(desde_min,tope,hoy=None):
    """El `ctx` del panel de fecha del reloj del calendario: Stock no tiene
    fecha en la franja, así que se arma con los topes del kardex. Abre en el
    mes pasado entero, como abría el `date_input` de antes (#602)."""
    hoy=hoy or dt.date.today()
    defecto=next((r for c,_n,_g,r in atajos_tarjeta(min(tope,hoy),(desde_min,tope)) if c=='mes_ant'),
                 im.periodo_por_defecto(desde_min,tope))
    return {'k_rango':clave_rango(REPORTE,False,CATEGORIA),'fecha_min':desde_min,'fecha_max':tope,
            'reporte':REPORTE,'usa_carga_rango':False,'hoy':hoy,'rango_default':defecto,
            'rango_default_cat':{CATEGORIA:defecto}}


def periodo_elegido(periodos):
    """El período de conteo elegido o, si no hay o ya no existe, el último
    CERRADO (el en curso no tiene conteo al final), y lo deja escrito."""
    claves=[p['clave'] for p in periodos]
    c=st.session_state.get(K_PERIODO)
    if c not in claves:
        c=([p for p in periodos if not p['en_curso']] or periodos)[-1]['clave']
        st.session_state[K_PERIODO]=c
    return periodos[claves.index(c)]


def _mover(claves,paso):
    c=st.session_state.get(K_PERIODO)
    i=claves.index(c) if c in claves else len(claves)-1
    st.session_state[K_PERIODO]=claves[max(0,min(len(claves)-1,i+paso))]


def _selector_periodo(periodos,p):
    """‹ [mes] ›: el valor vive en `K_PERIODO` y la key del desplegable lleva
    el valor, para que las flechas lo estrenen con el mes nuevo."""
    claves=[x['clave'] for x in periodos];i=claves.index(p['clave'])
    nombres={x['clave']:x['nombre']+(' · en curso' if x['en_curso'] else '') for x in periodos}
    wkey=f"stock_mov_per_{p['clave']}"
    def _copiar():
        v=st.session_state.get(wkey)
        if v in claves:st.session_state[K_PERIODO]=v
    with st.container(key='stock_mov_cab_periodo',horizontal=True,gap='small',width='content',vertical_alignment='center'):
        st.button('‹',key='stock_mov_ant',disabled=i==0,on_click=_mover,args=(claves,-1),help='Mes anterior')
        st.selectbox('Mes',claves,index=i,format_func=nombres.get,key=wkey,on_change=_copiar,label_visibility='collapsed',width=200)
        st.button('›',key='stock_mov_sig',disabled=i==len(claves)-1,on_click=_mover,args=(claves,1),help='Mes siguiente')


def _hora(t):
    return f'{t.day} {_ABR[t.month-1]} {t.hour:02d}:00'


def _dia(d):
    return f'{d.day} {_ABR[d.month-1]}'


def periodo_js(p,nombres_area):
    """Lo que la pieza dice del período de conteo: el mes físico (regla
    #752: se cuenta el día 1 por la mañana), las aperturas de la mayoría en
    el sistema y las áreas que abrieron en OTRO día, con su nombre."""
    # Una hora de diferencia es lo normal (cada área cierra su conteo cuando
    # termina); se nombra el área que se contó OTRO día, como Venta Interna
    # el 6 de octubre de 2026 con las demás el 1.
    lejos=lambda x,y:abs(x-y)>dt.timedelta(hours=12)
    exc=[[nombres_area[a],' y '.join(([f'desde el {_hora(t0)}'] if lejos(t0,p['t0']) else [])
                                     +([f'hasta el {_hora(t1)}'] if lejos(t1,p['t1']) else []))]
         for a,(t0,t1) in sorted(p['ventanas'].items())
         if a in nombres_area and (lejos(t0,p['t0']) or lejos(t1,p['t1']))]
    return dict(nombre=p['nombre'],en_curso=bool(p['en_curso']),t0=_hora(p['t0']),t1=_hora(p['t1']),
                desde=_dia(p['desde']) if p.get('desde') is not None else '',
                hasta=_dia(p['hasta']) if p.get('hasta') is not None else '',
                dias=round(float(p['dias']),2),excepciones=exc,cierre=p.get('cierre'),cierre_ant=p.get('cierre_ant'))


def conteos_del_rango(sesiones,desde,hasta):
    """Las sesiones de conteo con algún día dentro del rango del calendario
    y los cierres de sus meses que caen DESPUÉS (del 1 al 7 del mes que
    sigue): el aviso de por qué los ajustes no son los del mes."""
    out=[]
    for s in sesiones or []:
        dias=[d for d in s['dias'] if desde<=d<=hasta]
        y,m=s['mes']
        if dias:
            out.append(dict(nombre=s['nombre'],etiqueta=s['etiqueta'],tipo=s['tipo'],dentro=True))
        elif s['tipo']=='cierre' and s['ini']>hasta and dt.date(y,m,1)<=hasta and _fin_de_mes(y,m)>=desde:
            out.append(dict(nombre=s['nombre'],etiqueta=s['etiqueta'],tipo=s['tipo'],dentro=False))
    return out


def _fin_de_mes(y,m):
    return (dt.date(y+(m==12),m%12+1,1)-dt.timedelta(days=1))


def _mes_entero(desde,hasta,tope):
    """`(y, m)` si el rango es un mes entero (o lo que va del mes en curso,
    hasta el último día del kardex); si no, None."""
    if desde.day!=1 or (desde.year,desde.month)!=(hasta.year,hasta.month):return None
    if hasta in (_fin_de_mes(desde.year,desde.month),tope):return (desde.year,desde.month)
    return None


def _otro_calendario(p,tope,d,cols):
    """El mismo mes de `p` por las fechas del calendario, resumido por área
    y familia, o None."""
    y,m=p['mes'];m0=dt.date(y,m,1);m1=min(_fin_de_mes(y,m),tope)
    mov=data.movimientos_kardex(m0,m1)
    fi=data.stock_al(kardex.momento(m0-dt.timedelta(days=1),23));ff=data.stock_al(kardex.momento(m1,23))
    if mov is None or fi is None or ff is None:return None
    nombre=f'del 1 al {m1.day} de {MESES_LARGOS_ES[m-1]}'
    return dict(reloj='cal',nombre=nombre,**datos.resumen_por_area(d,mov,fi,ff,**cols))


def _otro_conteo(p,d,cols):
    fuente=data.movimientos_conteo(p)
    if fuente is None:return None
    return dict(reloj='op',nombre=f"del conteo del {p['cierre_ant']} al del {p['cierre'] or 'último día'}",
                **datos.resumen_por_area(d,*fuente,**cols))


def renderizar(d,*,col_cod_area,col_cod,col_area,col_prod,col_fam=None,col_punit=None):
    if not (col_cod_area and col_cod and col_area and col_prod):
        st.info('El parquet de stock no trae los códigos de área y de producto: sin ellos no hay cómo cruzarlo con el kardex.');return
    rango=data.rango_fechas(kardex.ARCHIVO,kardex.COL_FECHA)
    if not rango:
        st.info('Falta el kardex: la consulta «kardex» del Sheet todavía no llegó a la app.');return
    ss=st.session_state;desde_min,tope=max(rango[0],kardex.INICIO),rango[1]
    cols=dict(col_cod_area=col_cod_area,col_cod=col_cod,col_area=col_area,col_prod=col_prod,col_fam=col_fam,col_punit=col_punit)
    pc=data.periodos_conteo() or {}
    periodos,sesiones=pc.get('periodos') or [],pc.get('sesiones') or []
    with st.container(key='stock_mov_cab',horizontal=True,gap='small',vertical_alignment='center'):
        st.markdown('<p class="chart-card-hdr">Por qué cambió el stock</p>',unsafe_allow_html=True)
        reloj=CALENDARIO
        if periodos:
            with st.container(key='stock_mov_cab_reloj',width='content'):
                reloj=eleccion_compartida(K_RELOJ,'Con qué fechas',RELOJES,CONTEO,'stock_mov_reloj')
        if reloj==CONTEO:
            p=periodo_elegido(periodos);_selector_periodo(periodos,p)
        else:
            ctx=ctx_calendario(desde_min,tope)
            with st.container(key='stock_mov_cab_fecha',width='content'):
                selector_fecha_tarjeta('stock_mov_f',None,categoria=CATEGORIA,ctx=ctx)
    nombres_area={int(c):n for c,n in zip(im._texto(d[col_cod_area]),im._texto(d[col_area])) if c.isdigit()}
    comparar=bool(ss.get(K_COMPARAR))
    if reloj==CONTEO:
        fuente=data.movimientos_conteo(p)
        if fuente is None:
            st.info('No se pudo leer el kardex. Probá de nuevo en un momento.');return
        mov,foto_ini,foto_fin=fuente;desde,hasta=p['desde'],p['hasta']
        extra=dict(reloj='op',periodo=periodo_js(p,nombres_area))
        otro=_otro_calendario(p,tope,d,cols) if comparar else None
        ventana=(f"Del conteo del {p['cierre_ant']} al del {p['cierre']}" if p['cierre']
                 else f"Desde el conteo del {p['cierre_ant']} hasta el último movimiento del kardex")
        contexto={'Reloj':CONTEO,'Período':p['nombre']+(' (en curso)' if p['en_curso'] else ''),'Ventana':ventana,
                  'Cortes':'Cada área desde la hora siguiente a su conteo hasta la de su conteo siguiente: las puntas son el stock contado.',
                  'Áreas contadas otro día':'; '.join(f'{a}: {t}' for a,t in extra['periodo']['excepciones']) or 'Ninguna'}
    else:
        r=rango_tarjeta(CATEGORIA,ctx) or im.periodo_por_defecto(desde_min,tope)
        desde,hasta=r[0],r[-1]
        mov=data.movimientos_kardex(desde,hasta)
        foto_ini=data.stock_al(kardex.momento(desde-dt.timedelta(days=1),23));foto_fin=data.stock_al(kardex.momento(hasta,23))
        if mov is None or foto_ini is None or foto_fin is None:
            st.info('No se pudo leer el kardex. Probá de nuevo en un momento.');return
        extra=dict(reloj='cal',conteos=conteos_del_rango(sesiones,desde,hasta))
        mes=_mes_entero(desde,hasta,tope)
        p_op=next((x for x in periodos if tuple(x['mes'])==mes),None) if mes else None
        otro=_otro_conteo(p_op,d,cols) if (comparar and p_op) else None
        if mes and p_op is None:mes=None
        extra['comparable']=bool(mes)
        contexto={'Reloj':CALENDARIO,'Fotos':'Al cierre del día anterior y del último día del período, con la hora de kardex original'}
    contexto['Ámbito']='Productos activos y filtros generales recibidos de la página'
    firma=hashlib.sha256(pickle.dumps((d,mov,foto_ini,foto_fin,cols,desde,hasta,contexto,extra,otro),protocol=5)).hexdigest()
    cache=ss.get('_stock_mov_747_cache')
    if cache is None or cache[0]!=firma:
        cache=(firma,datos.armar(d,mov,foto_ini,foto_fin,**cols,desde=desde,hasta=hasta,contexto=contexto,otro=otro,**extra))
        ss['_stock_mov_747_cache']=cache
    P=dict(cache[1]);P['inicial']=dict(areas=[],familias=[],q='');P['comun']='stock_mov_747'
    P['comparar']=comparar or otro is not None

    def _al_comparar():
        if isinstance((ss.get(K_PIEZA) or {}).get('comparar'),str):ss[K_COMPARAR]=True
    _PIEZA(key=K_PIEZA,data=P,on_comparar_change=_al_comparar,width='stretch')
