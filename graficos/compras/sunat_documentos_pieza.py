"""Documentos SUNAT propios; fuentes y acciones siguen en Python (#741)."""
from graficos.movil import css_movil, js_movil
import hashlib
import pickle
from pathlib import Path

import streamlit as st
import tema
from graficos.base import una_vez_por_corrida
import tipo_compra
from . import documentos_sunat as ds
from . import _sunat_vistas as sv
from . import sunat_documentos_datos as datos

_DIR=Path(__file__).parent
_KEY='sunat_documentos_pieza'
_KEY_LINEAS=_KEY+'_lineas'
_K_LINEAS='_sunat_docs_lineas'
_K_LINEAS_VISTO='_sunat_docs_lineas_visto'
_K_ACCION='_sunat_docs_accion'


def validar_accion(a,P):
    """Sólo identificadores del censo actual; nunca confía en filas del navegador."""
    if not isinstance(a,dict) or a.get('sello')!=P['sello'] or a.get('que') not in ('ficha','ingreso','lote'):
        return None
    nonce=a.get('nonce')
    if not isinstance(nonce,str) or not nonce or len(nonce)>128:return None
    por_id={r['id']:r for r in P['filas']}
    if a['que']=='lote':
        ids=a.get('ids')
        if not isinstance(ids,list) or len(ids)>len(por_id) or any(not isinstance(i,str) or i not in por_id for i in ids):return None
        return dict(que='lote',ids=list(dict.fromkeys(ids)),nonce=nonce)
    r=por_id.get(a.get('id')) if isinstance(a.get('id'),str) else None
    if r is None or not r['_car'] or r[P['estado_col']]=='Solo sistema':return None
    if a['que']=='ingreso' and r['Ingresar']!='Ingresar':return None
    return dict(que=a['que'],id=r['id'],nonce=nonce)


def _refrescar():
    for fn in [ds.sunat._registro_de_parquet,ds.sunat.obtener_comprobantes,ds.sunat.obtener_comprobantes_rango,
               ds.sunat.periodos_con_estado,ds.sunat._existe_original,ds.sunat._bytes_original,ds.sunat.claves_xml_en_r2]:fn.clear()


def _doc(P,vis,identidad):
    r=next((r for r in P['filas'] if r['id']==identidad),None)
    if r is None or not r['_car'] or vis is None or vis.empty:return None
    return ds._fila_de(vis,{'_car':r['_car']})


def _pieza():
    css=(_DIR/'sunat_documentos.css').read_text(encoding='utf-8')
    css+='.sud{'+''.join(f'--sud-{k}:{v};' for k,v in dict(acento=tema.ACENTO,neg=tema.AJUSTE_NEG,pos=tema.AJUSTE_POS).items())+'}'
    return st.components.v2.component('sunat_documentos_741',css=css_movil(css),
        js=js_movil((_DIR.parent/'_xlsx.js').read_text(encoding='utf-8')+(_DIR/'sunat_documentos.js').read_text(encoding='utf-8')))


_PIEZA=_pieza()


def validar_lineas(a,P):
    """El id del pedido de líneas, si es de esta tabla."""
    if not isinstance(a,dict) or a.get('sello')!=P['sello'] or not isinstance(a.get('id'),str):return None
    return a['id'] if any(r['id']==a['id'] for r in P['filas']) else None


def _lineas(P,vis,d,identidad):
    r=next(r for r in P['filas'] if r['id']==identidad)
    if r['_car']:
        doc=ds._fila_de(vis,{'_car':r['_car']})
        doc=doc.to_dict() if hasattr(doc,'to_dict') else dict(doc or {})
    else:
        raw=r['raw'];doc=dict(documento=raw.get('documento'),ruc_proveedor=raw.get('ruc_sistema'),fecha_emision=raw.get('fecha_emision'))
    xml=None
    if r['_car'] and r['XML']:
        try:xml=ds.sunat._bytes_original(ds.sunat.claves_original(doc)[1])
        except Exception:xml=None
    return datos.lineas_documento(r,doc,d,xml)


def _montar_cuerpo(P,vis,d):
    """La pieza y su montaje chico, en un fragment: elegir una fila trae sus líneas
    sin rehacer la página. Una acción (la ficha, ingresar, el lote) sí pide una
    corrida completa, porque abre ventanas que viven fuera del fragment."""
    ss=st.session_state
    _PIEZA(key=_KEY,data=P,width='stretch',on_accion_change=lambda:None,on_lineas_change=lambda:None)
    a=validar_accion((ss.get(_KEY) or {}).get('accion'),P)
    if a and ss.get('_sunat_docs_atendida')!=(P['sello'],a['nonce']):
        # El trigger no sobrevive a la corrida que sigue: se deja anotado.
        ss[_K_ACCION]=a;st.rerun()
    pedido=(ss.get(_KEY) or {}).get('lineas')
    identidad=validar_lineas(pedido,P)
    if identidad and ss.get(_K_LINEAS_VISTO)!=pedido.get('t'):
        ss[_K_LINEAS_VISTO]=pedido.get('t')
        ss[_K_LINEAS]=dict(id=identidad,d=_lineas(P,vis,d,identidad))
    guardado=ss.get(_K_LINEAS)
    if guardado:_PIEZA(key=_KEY_LINEAS,data=dict(parte='lineas',id=guardado['id'],d=guardado['d']),width='stretch')


_montar=una_vez_por_corrida(st.fragment(_montar_cuerpo))


def renderizar(d,col_fecha):
    ss=st.session_state;ini,fin=ds._rango_vigente();doc=None
    st.markdown('<style>.st-key-sunat_cabecera_nativa{height:36px;min-height:36px;margin:0!important}@media(max-width:750px){.st-key-sunat_cabecera_nativa{height:auto!important}}</style>',unsafe_allow_html=True)
    with st.container(border=True,key='sunat_card_izq'):
        with st.container(key='sunat_cabecera_nativa'):
            cf,cm,cp,cr=st.columns([1.7,1.0,2.2,.4],vertical_alignment='center')
            with cf:ds.selector_fecha_tarjeta('sunat_f','sunat_fecha_flag')
            with cm:mes=st.selectbox('Mes en SUNAT',list(ds._MES_SUNAT),key='sunat_mes_sunat',label_visibility='collapsed',help='Estado del período tributario; se aplica antes de cruzar las fuentes.')
            with cp:slot=st.empty()
            with cr:
                if st.button('⟳',key='sunat_actualizar',help='Volver a consultar a SUNAT',use_container_width=True):_refrescar();st.rerun()
        if ini is None:st.info('Elegí una fecha en el calendario.');return None
        with st.spinner('Cargando el registro de compras de SUNAT…'):
            try:sire,origen=ds.sunat.comprobantes_rango(ini,fin)
            except Exception as e:st.error(f'No se pudo consultar a SUNAT: {e}');return None
        if sire is None or sire.empty:st.info('SUNAT no tiene comprobantes en el rango elegido.');return None
        situacion=ds._MES_SUNAT.get(mes);vis=sire if situacion is None else sire[sire.situacion==situacion]
        if vis.empty:st.info(f'No hay comprobantes de «{mes.lower()}» en el rango.');return None
        pq=ds._parquet_agrupado_por_documento(d,col_fecha,ini,fin,notas=ds.data.notas_credito_compras())
        tablas=ds._tablas_tipo((ds.data.sello_datos(ds.definicion_compra.ARCHIVO),ds.data.sello_datos('inventariovalorizado.parquet')),tipo_compra.VERSION,d)
        firma=hashlib.sha256(pickle.dumps((vis,pq,tablas,tipo_compra.VERSION),protocol=5)).hexdigest();cache=ss.get('_sunat_docs_cruce_741')
        if cache is None or cache[0]!=firma:
            cache=(firma,tipo_compra.clasificar(ds.cruzar_con_parquet(vis,pq),vis,tablas));ss['_sunat_docs_cruce_741']=cache
        cruce=cache[1];claves=ds._claves_proveedor_cruce(cruce);prov=ds._filtro_proveedor(slot,cruce,claves)
        if prov:
            cruce=cruce[claves==prov];vis=vis[ds._claves_proveedor_sire(vis)==prov]
        ds._publicar_conteos(cruce)
        llegada=ss.get(sv.K_LLEGADA)
        if llegada:
            ds._aviso_llegada(llegada);cruce=sv.aplicar_llegada(cruce,llegada)
            if 'car' in vis and 'car' in cruce:vis=vis[vis.car.astype(str).isin(set(cruce.car.astype(str)))]
        ds._aviso_origen(origen)
        xmls=ds.sunat.claves_xml_en_r2()|ss.get(ds._K_XML_LLEGADOS,frozenset())
        contexto={'Desde':str(ini),'Hasta':str(fin),'Mes en SUNAT':mes,'Proveedor':prov or 'Todos',
            'Ámbito':'Rango y proveedor compartidos; los filtros del componente recortan tabla y Excel.',
            'Moneda':'Las dos fuentes se comparan en soles. La moneda del papel se indica por separado.'}
        firma=hashlib.sha256(pickle.dumps((cruce,vis,xmls,contexto),protocol=5)).hexdigest();cache=ss.get('_sunat_docs_datos_741')
        if cache is None or cache[0]!=firma:
            cache=(firma,datos.armar(cruce,vis,xmls,contexto));ss['_sunat_docs_datos_741']=cache
        P=dict(cache[1]);P['inicial']=dict(estado=ss.get('sunat_estado__eco') or '')
        P['salto']=ss.get('_sunat_docs_salto',0);P['menos']=34 if llegada else 0
        a=ss.pop(_K_ACCION,None) or validar_accion((ss.get(_KEY) or {}).get('accion'),P)
        if a and ss.get('_sunat_docs_atendida')!=(P['sello'],a['nonce']):
            ss['_sunat_docs_atendida']=(P['sello'],a['nonce'])
            if a['que']=='lote':ss['_sunat_docs_lote']=(P['sello'],a['ids']);ss[ds._K_LOTE_ABIERTO]=True
            else:
                doc=_doc(P,vis,a['id'])
                if doc is not None:
                    ss['_sunat_docs_elegido']=(P['sello'],a['id'])
                    marca=max(float(ss.get(ds._K_FICHA_PEDIDO) or 0),float(ss.get(ds._K_INGRESO_PEDIDO) or 0))+1
                    if a['que']=='ficha':ds._atender_pedido_de_ficha({'_ver':marca},doc)
                    else:ds._atender_pedido_de_ingreso({'_ing':marca},doc)
        _montar(P,vis,d)
        elegido=ss.get('_sunat_docs_elegido')
        if elegido and elegido[0]==P['sello']:doc=_doc(P,vis,elegido[1])
        lote=ss.get('_sunat_docs_lote');ids=set(lote[1]) if lote and lote[0]==P['sello'] else set()
        indices=[i for i,r in enumerate(P['filas']) if r['id'] in ids];lcruce=cruce.iloc[indices]
        if ss.get(ds._K_LOTE_ABIERTO):
            st.caption(f'Lote preparado para {len(indices)} documentos elegidos al abrirlo. Para cambiar el recorte, cancela y vuelve a abrir el lote.')
        ds._avance_lote_xml(lcruce,vis)
    if ds._ficha_abierta(doc):ds._ficha_modal(doc)
    elif ds._ingreso_abierto(doc):
        fila=ds._fila_cruce_de(cruce,doc)
        if fila is not None and str(fila.get('estado') or '')=='Solo SUNAT':ds._ingresar_modal(doc,d)
    return doc
