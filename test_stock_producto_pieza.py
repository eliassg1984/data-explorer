"""Stock por Producto nativo: mismas cuentas, fotos y mejoras locales (#721)."""
import datetime as dt
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd

import analisis_stock
from graficos import inventario_productos as ip
from graficos import inventario_productos_datos as datos
from graficos.inventario import separar_activos

ROOT=Path(__file__).parent
JS=(ROOT/'graficos/inventario_base.js').read_text(encoding='utf-8')+(ROOT/'graficos/inventario_productos.js').read_text(encoding='utf-8')
CSS=(ROOT/'graficos/inventario_productos.css').read_text(encoding='utf-8')
COLS=dict(cod='COD',prod='PROD',fam='FAM',subfam='SUB',area='AREA',unidad='UM',
          punit='PRECIO',cant='Q',val='V',factor='FACTOR',usal='USAL',cod_area='ACOD')
RANGO=(dt.date(2025,1,1),dt.date(2026,10,24))


def inventario():
    filas=[]
    def r(cod,prod,area,q,precio=10,fam='ALIMENTOS',sub='ABARROTES',um='KILOGRAMO',f=1000,us='GRAMO'):
        filas.append(dict(COD=cod,PROD=prod,FAM=fam,SUB=sub,AREA=area,UM=um,PRECIO=precio,
                          Q=q,V=q*precio,FACTOR=f,USAL=us,ACOD={'ALMACEN CENTRAL':'000','COCINA':'001','CAVA':'002'}[area],
                          **{'AREA ACTIVA':'ACTIVA','PRODUCTO ACTIVO':'ACTIVO','COMPARTIDO':'COMPARTIDO','TIPO PRODUCTO':'MERCADERIA'}))
    r('001','(P) Pollo Áñéjo','ALMACEN CENTRAL',20.123456,12.345678)
    r('001','(P) Pollo Áñéjo','COCINA',-2.123456,12.345678)
    r('001','(P) Pollo Áñéjo','CAVA',0,12.345678)
    r('002','Arroz','ALMACEN CENTRAL',5,8)
    r('003','Negativo','COCINA',-3,5)
    r('004','Nunca con stock','ALMACEN CENTRAL',0,5)
    r('005','Aceite','COCINA',1.813,7,um='LITRO',f=32,us='ONZAS')
    r('006','Valor grande','ALMACEN CENTRAL',100,20)
    r('007','Precio por área','ALMACEN CENTRAL',10,2)
    r('007','Precio por área','COCINA',5,4)
    r('008','Se terminó','COCINA',0,18)
    r('009','(P) Pollo Áñéjo','COCINA',1,13)
    r('010','Vino','CAVA',10,30,fam='VINOS',sub='TINTOS',um='UNIDAD',f=1,us='UNIDAD')
    r('011','Sin consumo positivo','COCINA',2,10)
    r('012','Con valor sin cantidad','COCINA',0,10)
    filas[-1]['V']=1.12345678
    return pd.DataFrame(filas)


def historia(d):
    idx=pd.MultiIndex.from_frame(d[['ACOD','COD']].drop_duplicates())
    valores=pd.DataFrame([[float((i+2)*(j+1)*13.123456) for j in range(4)] for i in range(len(idx))],index=idx,columns=[0,1,2,3])
    valores.index.names=['area','cod']
    return (['set 25','mar 26','set 26','hoy'],[dt.datetime(2025,10,7,23),dt.datetime(2026,4,7,23),dt.datetime(2026,10,7,23),dt.datetime(2026,10,24,3)],valores)


def armar(d=None,analisis=True):
    d=inventario() if d is None else d
    h=historia(d)
    consumo=pd.Series({'001':18.,'002':0.,'003':12.,'005':90.,'006':450.,'007':60.,'009':5.,'010':20.,'011':-3.})
    p=datos.armar(d,COLS,h if analisis else None,consumo if analisis else None,RANGO)
    p.update(semilla=0,inicial={})
    return p,d,h,consumo


def referencia(d,h,cons,st,analisis=True):
    l=ip.armar_listado(d,**{'col_'+k:v for k,v in COLS.items()},areas=st.get('areas',[]),
                       familias=st.get('fams',[]),subfamilias=st.get('subs',[]),texto=st.get('q',''),
                       incluir_sin_stock=st.get('sin',False),historia=h[2] if analisis else None,
                       consumo=cons if analisis else None)
    return l,ip.por_estado(l,st.get('chip','todos'))


class Contrato(unittest.TestCase):
    def test_grano_precision_activos_unidades_y_sello(self):
        p,d,h,cons=armar()
        self.assertEqual(len(p['filas']),len(d));json.dumps(p,allow_nan=False)
        self.assertEqual(p['dic']['cod'][p['filas'][0][0]],'001')
        self.assertEqual(p['filas'][0][11],d.iloc[0].V)
        self.assertEqual(p['filas'][0][12],h[2].iloc[0].tolist())
        self.assertEqual(datos.armar(d,COLS,h,cons,RANGO)['sello'],p['sello'])
        self.assertEqual(datos.armar(d,COLS,h,cons.iloc[::-1],RANGO)['sello'],p['sello'])
        d.loc[0,'Q']+=.00000001
        self.assertNotEqual(datos.armar(d,COLS,h,cons,RANGO)['sello'],p['sello'])
        raw=inventario();extra=raw.iloc[[0]].assign(COD='INACTIVO',**{'PRODUCTO ACTIVO':'INACTIVO'})
        activos,_=separar_activos(pd.concat([raw,extra],ignore_index=True))
        self.assertNotIn('INACTIVO',datos.armar(activos,COLS)['dic']['cod'])
        self.assertIn('const SP={cod:0,prod:1,fam:2,sub:3,area:4,um:5,usal:6,acod:7,factor:8,precio:9,q:10,v:11,h:12};',JS)
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_foto_usa_regla_original_y_error_no_es_cero(self):
        p,d,_,_=armar();ant=d[['ACOD','COD','Q','PRECIO']].rename(columns={'ACOD':'area','COD':'cod','Q':'stock','PRECIO':'precio'})
        hoy=ant.copy();hoy['stock']=hoy.stock+1;ant=ant.iloc[1:].copy();ant['stock']=ant.stock-2
        out=datos.foto(d,COLS,ant,hoy,RANGO[0],23,p['sello'])
        ref=ip.stock_a_la_fecha(d,ant,col_area='ACOD',col_cod='COD',col_cant='Q',col_val='V',col_punit='PRECIO',foto_hoy=hoy)
        self.assertTrue(out['ok']);self.assertTrue(out['comparar'])
        self.assertEqual(out['filas'],ref[['PRECIO','Q','V',ip.COL_CANT_HOY,ip.COL_VAL_HOY]].to_numpy().tolist())
        fail=datos.foto(d,COLS,None,None,RANGO[0],23,p['sello'])
        self.assertFalse(fail['ok']);self.assertNotIn('filas',fail)
        sin_hoy=datos.foto(d,COLS,ant,None,RANGO[0],23,p['sello'])
        self.assertTrue(sin_hoy['ok']);self.assertFalse(sin_hoy['comparar'])

    def test_columnas_opcionales_nullable_indices_y_sin_historia(self):
        d=inventario().iloc[:3].copy();d['COD']=pd.Series([1,pd.NA,3],dtype='Int64');d.index=[0,0,0]
        p=datos.armar(d,COLS)
        self.assertEqual(p['dic']['cod'],['','1','3']);self.assertFalse(p['analisis'])
        self.assertEqual(len(p['filas']),3)
        cols={k:v for k,v in COLS.items() if k not in ['factor','usal','cod_area','cod']}
        p=datos.armar(d,cols);self.assertFalse(p['hay_salida']);self.assertFalse(p['hay_fecha'])
        self.assertIn('(P) Pollo Áñéjo',p['dic']['cod'])

    def test_montaje_callback_y_salto_externo_con_apptest(self):
        from streamlit.testing.v1 import AppTest
        from graficos import inventario_productos_pieza as pieza
        old=pieza._PIEZA
        try:
            with patch.object(pieza.data,'historia_stock',return_value=None),patch.object(pieza.data,'rango_fechas',return_value=RANGO):
                app=AppTest.from_string('''import streamlit as st
from graficos import inventario_productos_pieza as pieza
from test_stock_producto_pieza import inventario,COLS
pieza._PIEZA=st.components.v2.component("stock_montaje_test",js="export default function() {}")
pieza.renderizar(inventario(),COLS)
''').run(timeout=60)
                self.assertFalse(app.exception)
        finally:pieza._PIEZA=old


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P,cls.d,cls.h,cls.cons=armar();cls.pw=sync_playwright().start()
        try:cls.b=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.b.new_page(viewport={'width':1323,'height':619},accept_downloads=True)
        cls.pg.set_content('<div id="montar"></div><div id="foto"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:531px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--success:green;--danger:crimson;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarStock=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.b.close();cls.pw.stop()

    def calc(self,st=None,p=None):
        return self.pg.evaluate('''([P,st])=>{const F=__stockDatos,B=F.leer(P),s={...__stockUI.inicial(P),...st};return F.filtrar(B,s)}''',[p or self.P,st or {}])

    def mount(self,p=None):self.pg.evaluate('P=>{window.__stockProd=undefined;window.__requests=[];__montarStock({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(k,v)=>__requests.push([k,v])})}',p or self.P)

    def test_listado_contra_python_en_filtros_y_estados(self):
        for areas in [[],['COCINA'],['ALMACEN CENTRAL','CAVA']]:
            for fams in [[],['ALIMENTOS']]:
                for sin in [False,True]:
                    for q in ['', 'pollo anejo','007']:
                        st={'areas':areas,'fams':fams,'subs':[],'sin':sin,'q':q,'chip':'todos'}
                        a=self.calc(st);ref,visible=referencia(self.d,self.h,self.cons,st)
                        self.assertEqual([r['cod'] for r in a['visibles']],visible.productos.index.tolist())
                        self.assertEqual(a['sin'],ref.sin_stock);self.assertEqual(a['counts']['A'],ip.cuentas_estado(ref.productos)['A'])
                        self.assertAlmostEqual(a['total'],visible.productos.valorizado.sum(),places=7)
                        for r in a['visibles']:
                            rr=ref.productos.loc[r['cod']]
                            for k,c in [('q','cantidad'),('v','valorizado'),('precio','precio'),('consumo','consumo')]:self.assertAlmostEqual(r[k],rr[c],places=7)
                            self.assertEqual(r['abc'],rr.abc);self.assertEqual(r['estado'],rr.estado)
                            if pd.isna(rr.dias):self.assertIsNone(r['dias'])
                            else:self.assertAlmostEqual(r['dias'],rr.dias,places=7)
                            ar=ref.areas[ref.areas.codigo==r['cod']]
                            self.assertEqual([z['area'] for z in r['areas']],ar.area.tolist())
                        for chip in ['A','neg','sin','alto']:
                            b=self.calc({**st,'chip':chip});vis=ip.por_estado(ref,chip)
                            self.assertEqual([r['cod'] for r in b['visibles']],vis.productos.index.tolist())

    def test_serie_sin_stock_busqueda_abc_y_dias_del_conjunto(self):
        st={'areas':[],'fams':[],'subs':[],'sin':False,'q':'','chip':'todos'}
        a=self.calc(st);ref,vis=referencia(self.d,self.h,self.cons,st)
        np.testing.assert_allclose(a['serie'],ref.serie,rtol=0,atol=1e-7)
        dias=analisis_stock.dias_del_conjunto(vis.productos.valorizado,vis.productos.cantidad,vis.productos.consumo,vis.productos.precio)
        self.assertAlmostEqual(a['dias'],dias,places=7)
        b=self.calc({**st,'q':'aceite'});rr=ref.productos.loc['005']
        self.assertEqual(b['visibles'][0]['abc'],rr.abc)
        np.testing.assert_allclose(b['serie'],ref.productos.loc['005',[f'__h{i}' for i in range(4)]].astype(float),rtol=0,atol=1e-7)
        c=self.calc({**st,'chip':'neg'});neg=ip.por_estado(ref,'neg')
        np.testing.assert_allclose(c['serie'],neg.productos[[f'__h{i}' for i in range(4)]].sum(),rtol=0,atol=1e-7)

    def test_metadatos_numericos_toman_primer_valor_no_nulo(self):
        d=self.d.iloc[:3].copy();d.loc[0,'PRECIO']=np.nan;d.loc[0,'FACTOR']=np.nan
        p,_,h,c=armar(d);out=self.calc({'areas':[]},p)['visibles'][0]
        ref,_=referencia(d,h,c,{'areas':[]})
        self.assertEqual(out['factor'],ref.productos.loc['001','factor'])
        self.assertEqual(out['precio'],ref.productos.loc['001','precio'])

    def test_formatos_salida_y_redondeo_como_python(self):
        for q in [.9999,-10.645,2.813,.0004,1.0625,2.675,0.1,16.0009999,-.5,0]:
            for f,ue,us in [(1000,'KILOGRAMO','GRAMO'),(32,'LITRO','ONZAS'),(1,'UNIDAD','UNIDAD')]:
                out=self.pg.evaluate('([q,f,ue,us])=>__stockDatos.cantidad(q,f,ue,us,true)',[q,f,ip.unidad_corta(ue),ip.unidad_corta(us)])
                self.assertEqual(out,ip.texto_unidad_salida(q,f,ue,us),(q,f))
            for dec in [0,1,2,3]:self.assertEqual(self.pg.evaluate('([x,d])=>__stockDatos.round(x,d)',[q,dec]),round(q,dec))

    def test_foto_historica_comparacion_y_fallo_sin_base(self):
        self.mount();pg=self.pg;root=pg.locator('.isp')
        root.locator('[data-toggle=af]').check()
        self.assertEqual(len(pg.evaluate('__requests')),1);self.assertTrue(pg.evaluate('__stockProd.D.pending'))
        req=pg.evaluate('__requests[0][1]');raw=self.d[['ACOD','COD','Q','PRECIO']].rename(columns={'ACOD':'area','COD':'cod','Q':'stock','PRECIO':'precio'})
        ant=raw.copy();ant['stock']=ant.stock+2;ant['precio']=ant.precio+1
        photo=datos.foto(self.d,COLS,ant,raw,req['fecha'],req['hora'],self.P['sello'])
        pg.evaluate('P=>__montarStock({data:P,parentElement:document.querySelector("#foto")})',photo)
        self.assertFalse(pg.evaluate('__stockProd.D.analisis'))
        root.locator('[data-toggle=comparar]').check();self.assertEqual(len(pg.evaluate('__requests')),1)
        refd=ip.stock_a_la_fecha(self.d,ant,col_area='ACOD',col_cod='COD',col_cant='Q',col_val='V',col_punit='PRECIO',foto_hoy=raw)
        st=pg.evaluate('__stockProd.st');ref=ip.armar_listado(refd,**{'col_'+k:v for k,v in COLS.items()},areas=st['areas'],col_cant_hoy=ip.COL_CANT_HOY,col_val_hoy=ip.COL_VAL_HOY)
        out=pg.evaluate('__stockProd.D.visibles')
        self.assertEqual([r['cod'] for r in out],ref.productos.index.tolist())
        for r in out:
            rr=ref.productos.loc[r['cod']]
            for k,c in [('q','cantidad'),('v','valorizado'),('qh','cant_hoy'),('vh','val_hoy'),('precio','precio')]:self.assertAlmostEqual(r[k],rr[c],places=7)
        fail=datos.foto(self.d,COLS,None,None,req['fecha'],req['hora'],self.P['sello'])
        pg.evaluate('P=>__montarStock({data:P,parentElement:document.querySelector("#foto")})',fail)
        self.assertIn('No se pudo consultar',root.inner_text());self.assertIsNone(pg.evaluate('__stockUI.exportar(__stockProd,"lista")'))
        root.locator('[data-toggle=af]').uncheck();self.assertGreater(pg.evaluate('__stockProd.D.visibles.length'),0)

    def test_areas_negativas_ficha_escenario_y_excel(self):
        self.mount();pg=self.pg;root=pg.locator('.isp')
        root.locator('[data-act=chip][data-v=areaNeg]').click()
        self.assertIn('001',pg.evaluate('__stockProd.D.visibles.map(r=>r.cod)'))
        r=next(r for r in pg.evaluate('__stockProd.D.visibles') if r['cod']=='001');self.assertGreater(r['q'],0)
        root.locator('[data-act=foco][data-v="001"]').click()
        root.locator('[data-act=tab][data-v=historia]').click()
        root.locator('[data-change=curvaArea]').select_option('COCINA')
        self.assertEqual(pg.evaluate('__stockProd.st.focoArea'),'COCINA')
        root.locator('[data-act=tab][data-v=escenario]').click()
        root.locator('[data-input=objetivo]').fill('30');root.locator('[data-input=objetivo]').press('Tab')
        self.assertEqual(pg.evaluate('__stockProd.st.objetivo'),30)
        e=pg.evaluate('__stockDatos.escenario(__stockProd.D.visibles.find(r=>r.cod==="001"),30)')
        self.assertAlmostEqual(e['equivalente'],6,places=8);self.assertAlmostEqual(e['diferencia'],12,places=8)
        with pg.expect_download() as dl:root.locator('[data-act=excel][data-v=ficha]').click()
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'stock.xlsx';dl.value.save_as(str(f))
            with zipfile.ZipFile(f) as z:
                wb=z.read('xl/workbook.xml').decode()
                for nombre in ['Productos','Áreas','Historia','Escenario','Contexto']:self.assertIn(nombre,wb)
                for nombre in z.namelist():
                    if nombre.endswith('.xml'):ET.fromstring(z.read(nombre))
                self.assertIn('<v>20.123456</v>',z.read('xl/worksheets/sheet2.xml').decode())
                self.assertIn('restaurante entero',z.read('xl/worksheets/sheet5.xml').decode().lower())

    def test_orden_busqueda_despliegue_remontaje_y_salto(self):
        self.mount();pg=self.pg;root=pg.locator('.isp')
        root.locator('[data-act=abrir][data-v="001"]').click();self.assertGreater(root.locator('.isp-child').count(),0)
        root.locator('[data-act=orden][data-v=v]').click();self.assertEqual(pg.evaluate('__stockProd.st.orden'),[{'k':'v','d':1}])
        root.locator('[data-act=orden][data-v=v]').click();root.locator('[data-act=orden][data-v=v]').click();self.assertEqual(pg.evaluate('__stockProd.st.orden'),[])
        root.locator('.isp-search').fill('Aoz');root.locator('.isp-search').evaluate('e=>e.setSelectionRange(1,1)');root.locator('.isp-search').type('rr',delay=20)
        self.assertEqual(root.locator('.isp-search').input_value(),'Arroz')
        self.assertEqual(pg.evaluate('__stockProd.D.visibles.map(r=>r.cod)'),['002'])
        pg.evaluate('P=>__montarStock({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(k,v)=>__requests.push([k,v])})',self.P)
        self.assertEqual(pg.evaluate('__stockProd.st.q'),'Arroz')
        p={**self.P,'semilla':1,'inicial':{'areas':['COCINA'],'fams':[],'subs':[],'q':'','chip':'neg'}}
        pg.evaluate('P=>__montarStock({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:()=>{}})',p)
        self.assertEqual(pg.evaluate('__stockProd.st.q'),'');self.assertEqual(pg.evaluate('__stockProd.D.visibles.map(r=>r.cod)'),['003','001'])

    def test_sin_consumo_historico_unidades_distintas_y_movil(self):
        p,d,_,_=armar(analisis=False);self.mount(p)
        self.assertFalse(self.pg.evaluate('__stockProd.D.analisis'))
        self.assertEqual(self.pg.locator('.isp-chips').count(),0)
        p['inicial']={'chip':'A'};self.mount(p)
        self.assertGreater(self.pg.evaluate('__stockProd.D.visibles.length'),0)
        d=d.iloc[:2].copy();d['UM']=['KILOGRAMO','UNIDAD'];p,_,_,_=armar(d);self.mount(p)
        r=self.pg.evaluate('__stockProd.D.visibles[0]');self.assertTrue(r['mixed']);self.assertIsNone(r['dias'])
        self.assertIsNone(self.pg.evaluate('__stockDatos.escenario(__stockProd.D.visibles[0],60)'))
        self.mount();pg=self.pg;pg.set_viewport_size({'width':390,'height':844})
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.locator('.isp-filter').nth(2).locator('summary').click()
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619});pg.keyboard.press('Escape')
        self.assertEqual(pg.evaluate('Math.round(document.querySelector(".isp-main").getBoundingClientRect().height)'),531)
        self.assertEqual(pg.evaluate('Math.round(document.querySelector(".isp-ficha").getBoundingClientRect().height)'),575)

    def test_respuesta_antigua_y_nuevo_sello_piden_su_propia_foto(self):
        self.mount();pg=self.pg;root=pg.locator('.isp');root.locator('[data-toggle=af]').check()
        d=self.d.copy();d.loc[0,'Q']+=1;p,_,_,_=armar(d)
        pg.evaluate('P=>__montarStock({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(k,v)=>__requests.push([k,v])})',p)
        self.assertEqual(pg.evaluate('__requests.length'),2)
        self.assertEqual(pg.evaluate('__requests[1][1].sello'),p['sello'])
        old=datos.foto(self.d,COLS,None,None,'2026-09-30',23,self.P['sello'])
        pg.evaluate('P=>__montarStock({data:P,parentElement:document.querySelector("#foto")})',old)
        self.assertTrue(pg.evaluate('__stockProd.D.pending'))


if __name__=='__main__':unittest.main(verbosity=2)
