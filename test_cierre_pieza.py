"""Cierre nativo: mismas cuentas y comparación conservadora, sin red (#720)."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

from graficos.ajuste import _cierre_datos as datos
from graficos.ajuste import _cascada as anterior
from graficos.ajuste._pareto import _pareto_datos
from graficos.ajuste._productos import filas_productos

ROOT = Path(__file__).parent
JS = (ROOT / "graficos/ajuste/cierre.js").read_text(encoding="utf-8")
CSS = (ROOT / "graficos/ajuste/cierre.css").read_text(encoding="utf-8")


def inventario():
    filas = []
    def linea(f, cod, prod, area, val, dif=1, sis=10, fis=9, um="Kg", fam="ALIMENTOS"):
        filas.append({"FECHA": pd.Timestamp(f), "CODIGO PRODUCTO": cod,
                      "NOMBRE PRODUCTO": prod, "FAMILIA": fam, "SUBFAMILIA": "INSUMOS",
                      "AREA": area, "UNIDAD MEDIDA": um, "AJUSTE VALORIZADO": val,
                      "AJUSTE": dif, "STOCK AL CIERRE": sis, "STOCK DECLARADO": fis,
                      "VALORIZADO TOTAL": 123.456789})
    for j, f in enumerate(["2025-12-02", "2026-01-02", "2026-02-01", "2026-02-06", "2026-03-02", "2026-03-16"]):
        for i, nombre in enumerate(["Arroz", "Carne", "Vino", "Envase"]):
            for k, area in enumerate(["CENTRAL", "COCINA", "CAVA "]):
                val = (i+1)*(k+1)*1.23456789*(-1 if (i+k+j)%2 else 1)
                linea(f, f"00{i}", nombre, area, val, dif=val/3,
                      fam=["ALIMENTOS", "ALIMENTOS", "VINOS Y ESPUMANTES", "ENVASES Y EMBALAJES"][i])
        linea(f,"EX","Exacto","CENTRAL",0,dif=0,sis=12,fis=12)
        linea(f,"ZZ","Maestro sin stock","CENTRAL",0,dif=0,sis=0,fis=0)
    # Comparación: cierre enero (1 y 6 febrero) → cierre febrero (2 marzo).
    for cod, v0, v1 in [("RE",-5,-7),("NE",0,-8),("SO",-9,0),("CA",-2,3)]:
        linea("2026-02-01",cod,cod,"CENTRAL",v0,dif=v0)
        linea("2026-03-02",cod,cod,"CENTRAL",v1,dif=v1)
    linea("2026-02-01","AU","Ausente hoy","CENTRAL",-25)
    linea("2026-03-02","AN","Ausente antes","CENTRAL",-26)
    linea("2026-02-01","NC","No contado hoy","CENTRAL",-27)
    linea("2026-03-02","NC","No contado hoy","CENTRAL",0,0,0,0)
    linea("2026-02-01","NA","Incompleto","CENTRAL",-28)
    linea("2026-03-02","NA","Incompleto","CENTRAL",0,0,None,10)
    linea("2026-02-01","UM","Cambio unidad","CENTRAL",-29,um="Kg")
    linea("2026-03-02","UM","Cambio unidad","CENTRAL",0,0,um="Und")
    linea("2026-02-01","RN","Nombre viejo","CENTRAL",-30)
    linea("2026-03-02","RN","Nombre nuevo","CENTRAL",-31)
    linea("2026-02-01","ID1","Mismo nombre","CENTRAL",-32)
    linea("2026-03-02","ID2","Mismo nombre","CENTRAL",0,0)
    linea("2026-02-01","","Sin código","CENTRAL",-33)
    linea("2026-03-02","","Sin código","CENTRAL",-34)
    linea("2026-02-01","DO","Dos conteos","CENTRAL",-10)
    linea("2026-02-06","DO","Dos conteos","CENTRAL",10)
    linea("2026-03-02","DO","Dos conteos","CENTRAL",0,0)
    linea("2026-03-02","QT","Sólo cantidad","CENTRAL",0,.123456)
    linea("2026-02-01","QT","Sólo cantidad","CENTRAL",0,0)
    linea("2026-03-02","EPS","Milésimas","CENTRAL",.00000002,.00000002)
    linea("2026-03-16","RE","RE","CENTRAL",-12)
    return pd.DataFrame(filas)


class Contrato(unittest.TestCase):
    def test_montaje_streamlit_sin_callbacks_invalidos(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_string('''import pandas as pd
import streamlit as st
from graficos.ajuste import _cierre
# AppTest tiene otro registro de componentes que el import del test.
_cierre._PIEZA=st.components.v2.component("cierre_montaje_test",js="export default function() {}")
_cierre.vista_cierre(pd.DataFrame({"FECHA":[pd.Timestamp("2026-03-02")],
    "FAMILIA":["ALIMENTOS"], "AREA":["CENTRAL"],
    "NOMBRE PRODUCTO":["Arroz"], "AJUSTE VALORIZADO":[-2]}))
''').run(timeout=60)
        self.assertFalse(app.exception)

    def test_sesiones_ultimo_cierre_y_lineas_sin_agrupar(self):
        d=inventario();p=datos.armar(d)
        json.dumps(p,allow_nan=False)
        self.assertEqual(len(d),len(p['filas']))
        self.assertEqual(p['sesiones'][p['inicial']]['clave'],'cierre_2026-02')
        ses=next(s for s in p['sesiones'] if s['clave']=='cierre_2026-01')
        self.assertEqual(ses['juntas'],2);self.assertEqual(ses['n_dias'],2)
        self.assertEqual(p['dic']['area'],['CAVA','CENTRAL','COCINA'])
        self.assertIn('000',p['dic']['cod'])
        self.assertEqual(datos.armar(d)['sello'],p['sello'])
        d.loc[0,'AJUSTE VALORIZADO']+=.00000002
        self.assertNotEqual(datos.armar(d)['sello'],p['sello'])
        self.assertIn('const CJ={c:0,fam:1,area:2,prod:3,cod:4,sub:5,um:6,val:7,dif:8,sis:9,fis:10,stock:11,flags:12};',JS)
        self.assertNotIn('setTriggerValue',JS)
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_sin_fechas_sin_columnas_y_nan_no_inventan_cierres(self):
        d=inventario().iloc[:4].copy();d.loc[d.index[0],'FECHA']=pd.NaT
        p=datos.armar(d);self.assertEqual(p['sin_fecha'],1)
        d=d.drop(columns=['FECHA','STOCK AL CIERRE','STOCK DECLARADO','UNIDAD MEDIDA'])
        p=datos.armar(d);self.assertEqual(p['sesiones'][0]['tipo'],'sin_fecha')
        self.assertTrue(all(r[12]&1 for r in p['filas']))
        self.assertTrue(all(not r[12]&8 for r in p['filas']))
        json.dumps(datos.armar(d.iloc[:0]),allow_nan=False)

    def test_codigos_numericos_nullable_e_indices_repetidos(self):
        d=inventario().iloc[:3].copy()
        d['CODIGO PRODUCTO']=pd.Series([1,pd.NA,3],dtype='Int64')
        d.index=[0,0,0]
        p=datos.armar(d)
        self.assertEqual(p['dic']['cod'],['','1','3'])
        self.assertEqual(len(p['filas']),3)
        d['CODIGO PRODUCTO']=['nan','None','  ']
        self.assertEqual(datos.armar(d)['dic']['cod'],[''])


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=inventario();cls.P=datos.armar(cls.d)
        cls.pw=sync_playwright().start()
        try:cls.b=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.b.new_page(viewport={'width':1323,'height':619},accept_downloads=True)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--bg-card:white;--border:rgb(220,220,230);--success:green;--danger:crimson;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarCierre=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.b.close();cls.pw.stop()

    def mount(self,p=None):self.pg.evaluate('P=>{window.__ajCierre=undefined;__montarCierre({data:P,parentElement:document.querySelector("#montar")})}',p or self.P)

    def test_cuentas_originales_por_corte_familia_y_area(self):
        p=self.P
        for i,s in enumerate(p['sesiones']):
            ds=self.d[self.d.FECHA.dt.date.between(pd.Timestamp(s['ini']).date(),pd.Timestamp(s['fin']).date())]
            for fam in [None,'ALIMENTOS']:
                for area in [None,'CENTRAL']:
                    d=ds.copy()
                    if fam:d=d[d.FAMILIA==fam]
                    if area:d=d[d.AREA.str.strip()==area]
                    out=self.pg.evaluate('''([P,i,fam,area])=>{const F=__ajCierreDatos,B=F.leer(P),rs=B.cortes[i].filter(r=>(!fam||r.fam===fam)&&(!area||r.area===area));return {m:F.metricas(rs,P.hay),familias:F.resumen(rs,'fam',P.hay),espejos:F.espejos(rs),pareto:F.pareto(rs)}}''',[p,i,fam,area])
                    ref=anterior.metricas(d,'AJUSTE VALORIZADO','NOMBRE PRODUCTO','STOCK AL CIERRE','STOCK DECLARADO','VALORIZADO TOTAL')
                    for k,v in ref.items():
                        if v is None:self.assertIsNone(out['m'][k])
                        else:self.assertAlmostEqual(out['m'][k],v,places=7,msg=k)
                    refs=anterior.resumen_familias(d,'FAMILIA','AJUSTE VALORIZADO','NOMBRE PRODUCTO','STOCK AL CIERRE','STOCK DECLARADO','VALORIZADO TOTAL')
                    self.assertEqual({r['nombre'] for r in out['familias']},{r['familia'] for r in refs})
                    self.assertEqual(out['espejos']['n'],anterior.productos_espejo(d,'NOMBRE PRODUCTO','AREA','AJUSTE VALORIZADO')[0])
                    for lado in ['Faltantes','Sobrantes']:
                        js=self.pg.evaluate('([P,i,fam,area,lado])=>{const F=__ajCierreDatos;return F.pareto(F.leer(P).cortes[i].filter(r=>(!fam||r.fam===fam)&&(!area||r.area===area)),lado)}',[p,i,fam,area,lado])
                        nombres,vs,_,pct,acum=_pareto_datos(d,'AJUSTE VALORIZADO','NOMBRE PRODUCTO',1000,lado)
                        self.assertEqual([r['prod'] for r in js],nombres)
                        for a,b in zip(js,zip(vs,pct,acum)):
                            for k,v in zip(['valor','pct','acum'],b):self.assertAlmostEqual(a[k],v,places=7)

    def test_tabla_productos_original_y_matriz_ausencia_vs_cero(self):
        for juntas in [True,False]:
            for i,s in enumerate(self.P['sesiones']):
                d=self.d[self.d.FECHA.dt.date.between(pd.Timestamp(s['ini']).date(),pd.Timestamp(s['fin']).date())]
                ref=filas_productos(d,col_cod='CODIGO PRODUCTO',col_fam='FAMILIA',col_subfam='SUBFAMILIA',col_prod='NOMBRE PRODUCTO',col_um='UNIDAD MEDIDA',col_area='AREA',col_sis='STOCK AL CIERRE',col_dif='AJUSTE',col_fis='STOCK DECLARADO',col_val='AJUSTE VALORIZADO',juntas=juntas)
                out=self.pg.evaluate('([P,i,j])=>__ajCierreDatos.productos(__ajCierreDatos.leer(P).cortes[i],j)',[self.P,i,juntas])
                ref=ref[ref['__tipo']=='p']
                self.assertEqual([r['cod'] for r in out],ref['codigo'].tolist())
                for a,b in zip(out,ref.to_dict('records')):
                    for k,old in [('val','valor'),('sis','sistema'),('fis','conteo'),('dif','dif')]:self.assertAlmostEqual(a[k],b[old],places=8)
        i=self.P['inicial'];ds=self.d[self.d.FECHA==pd.Timestamp('2026-03-02')]
        for medida,col in [('val','AJUSTE VALORIZADO'),('stock','VALORIZADO TOTAL')]:
            m=self.pg.evaluate('([P,i,m])=>__ajCierreDatos.matriz(__ajCierreDatos.leer(P).cortes[i],m)',[self.P,i,medida])
            refs=ds.assign(AREA=ds.AREA.str.strip()).groupby(['FAMILIA','AREA'])[col].sum()
            for r in m['cells']:self.assertAlmostEqual(r['valor'],refs.loc[r['fam'],r['area']],places=7)
            self.assertEqual(len(m['cells']),len(refs))

    def test_listas_por_nombre_y_areas_del_pareto(self):
        i=self.P['inicial'];d=self.d[self.d.FECHA==pd.Timestamp('2026-03-02')]
        for juntas in [True,False]:
            keys=['NOMBRE PRODUCTO'] if juntas else ['NOMBRE PRODUCTO','AREA']
            ref=d.assign(AREA=d.AREA.str.strip()).groupby(keys)['AJUSTE VALORIZADO'].sum()
            out=self.pg.evaluate('([P,i,j])=>__ajCierreDatos.listas(__ajCierreDatos.leer(P).cortes[i],j)',[self.P,i,juntas])
            ref=ref[ref.abs()>1e-9]
            self.assertEqual(len(out),len(ref))
            for r in out:self.assertAlmostEqual(r['val'],ref.loc[r['prod'] if juntas else (r['prod'],r['area'])],places=8)
        out=self.pg.evaluate('([P,i])=>__ajCierreDatos.areasPareto(__ajCierreDatos.leer(P).cortes[i],"Arroz")',[self.P,i])
        self.assertEqual({r['area'] for r in out},{'CENTRAL','COCINA','CAVA'})
        self.assertAlmostEqual(sum(r['val'] for r in out),d[d['NOMBRE PRODUCTO']=='Arroz']['AJUSTE VALORIZADO'].sum(),places=8)

    def test_estados_recurrencias_duplicados_unidad_y_codigo(self):
        out=self.pg.evaluate('''P=>{const F=__ajCierreDatos,B=F.leer(P),i=P.inicial,j=P.sesiones.findIndex(s=>s.clave==='cierre_2026-01');return F.comparar(B.cortes[i],B.cortes[j],B.cortes.slice(0,i+1))}''',self.P)
        def item(cod):return next(r for r in out if r['cod']==cod)
        for cod,estado in [('RE','Recurrente'),('NE','Nueva'),('SO','Resuelta'),('CA','Recurrente'),('AU','Sin base'),('AN','Sin base'),('NC','Sin base'),('NA','Sin base'),('RN','Recurrente'),('ID1','Sin base'),('ID2','Sin base'),('QT','Nueva'),('DO','Resuelta')]:
            self.assertEqual(item(cod)['estado'],estado,cod)
        self.assertEqual(item('CA')['signo'],'Cambió de signo')
        self.assertIn('cantidad',item('QT')['motivo'])
        self.assertEqual(item('RN')['prod'],'Nombre nuevo')
        self.assertEqual([r['estado'] for r in out if r['cod']=='UM'],['Sin base','Sin base'])
        self.assertEqual(item('DO')['abs_anterior'],20);self.assertEqual(item('DO')['delta'],-20)
        self.assertEqual(item('RE')['con'],2);self.assertEqual(item('RE')['de'],2)
        self.assertEqual(item('')['estado'],'Recurrente')
        for r in out:
            if r['estado']=='Sin base':self.assertIsNone(r['delta'])

    def test_ui_filtros_independientes_celdas_comparacion_y_remontaje(self):
        self.mount();pg=self.pg;root=pg.locator('.ajc')
        root.locator('[data-act="familia"][data-v="ALIMENTOS"]').first.click()
        root.locator('[data-act="tab"][data-v="Comparar cierres"]').click()
        root.locator('[data-act="estado"][data-v="Resuelta"]').click()
        self.assertTrue(pg.evaluate('__ajCierre.comp.every(r=>r.estado==="Resuelta")'))
        root.locator('[data-act="elegido"]').first.click()
        self.assertEqual(root.locator('.ajc-history').count(),1)
        root.locator('[data-act="vista"][data-v="1"]').click()
        self.assertEqual(pg.evaluate('__ajCierre.st.vistas[1].tab'),'Por producto')
        root.locator('[data-act="celda"]').first.click()
        self.assertIsNotNone(pg.evaluate('__ajCierre.st.vistas[1].area'))
        root.locator('[data-act="vista"][data-v="0"]').click()
        self.assertEqual(pg.evaluate('__ajCierre.st.vistas[0].status'),'Resuelta')
        pg.evaluate('P=>__montarCierre({data:P,parentElement:document.querySelector("#montar")})',self.P)
        self.assertEqual(pg.evaluate('__ajCierre.st.vistas[0].status'),'Resuelta')
        root.locator('[data-act="tab"][data-v="Por producto"]').click()
        root.locator('[data-act="orden"][data-v="3"]').click()
        self.assertEqual(pg.evaluate('__ajCierre.st.vistas[0].orden["Por producto"].i'),3)
        root.locator('.ajc-search').fill('Aoz')
        root.locator('.ajc-search').evaluate('e=>e.setSelectionRange(1,1)')
        root.locator('.ajc-search').type('rr',delay=20)
        self.assertEqual(root.locator('.ajc-search').input_value(),'Arroz')
        self.assertIn('Arroz',root.locator('.ajc-detail').inner_text())
        self.assertNotIn('Carne',root.locator('.ajc-detail').inner_text())
        root.locator('.ajc-search').fill('')
        root.locator('[data-act="tab"][data-v="Pareto"]').click()
        root.locator('[data-act="parProd"]').first.click()
        self.assertEqual(root.locator('.ajc-pareto-areas').count(),1)
        self.assertIsNotNone(pg.evaluate('__ajCierre.exportarExtra'))
        self.assertEqual(pg.evaluate('Math.round(document.querySelector(".ajc-main").getBoundingClientRect().height)'),575)
        pg.set_viewport_size({'width':390,'height':844})
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619})

    def test_cambios_de_datos_vacio_y_cantidades_de_unidades_distintas(self):
        d=self.d.iloc[:2].copy();d['CODIGO PRODUCTO']='MIX';d['NOMBRE PRODUCTO']='Mixto'
        d['UNIDAD MEDIDA']=['Kg','Und'];d['AREA']=['A','B'];d['AJUSTE VALORIZADO']=[-2,3]
        p=datos.armar(d);self.mount(p)
        out=self.pg.evaluate('P=>__ajCierreDatos.productos(__ajCierreDatos.leer(P).rows,true)',p)
        self.assertEqual(out[0]['um'],'Varias unidades');self.assertIsNone(out[0]['dif'])
        self.assertEqual(len(out[0]['hijos']),2)
        d['CODIGO PRODUCTO']='';d['NOMBRE PRODUCTO']='';d['AREA']='A';d['UNIDAD MEDIDA']='Kg'
        d['FECHA']=pd.to_datetime(['2026-02-01','2026-03-01']);d['AJUSTE VALORIZADO']=[-10,0];d['AJUSTE']=[-1,0]
        sin_id=self.pg.evaluate('P=>{const F=__ajCierreDatos,B=F.leer(P);return F.comparar(B.cortes[1],B.cortes[0])}',datos.armar(d))
        self.assertEqual(sin_id[0]['estado'],'Sin base')
        self.mount(datos.armar(d.iloc[:0]));self.assertIn('Sin sesiones disponibles',self.pg.locator('.ajc').inner_text())

    def test_excel_contexto_filas_completas_y_seis_decimales(self):
        self.mount();pg=self.pg;root=pg.locator('.ajc')
        root.locator('[data-act="tab"][data-v="Comparar cierres"]').click()
        root.locator('[data-act="estado"][data-v="Sin base"]').click()
        with pg.expect_download() as dl:root.locator('[data-act="excel"][data-v="detalle"]').click()
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'cierre.xlsx';dl.value.save_as(str(f))
            with zipfile.ZipFile(f) as z:
                self.assertIn('Contexto',z.read('xl/workbook.xml').decode())
                for n in z.namelist():
                    if n.endswith('.xml'):ET.fromstring(z.read(n))
                self.assertIn('Sin base',z.read('xl/worksheets/sheet1.xml').decode())
                self.assertIn('cierre',z.read('xl/worksheets/sheet2.xml').decode().lower())
        # La biblioteca mantiene dos decimales por defecto y permite seis
        # numéricos para cantidades, sin convertirlos en texto.
        texto=pg.evaluate('hoja(["cantidad"],[[.123456]],6)')
        self.assertIn('<v>0.123456</v>',texto)
        self.assertIn('<v>0.12</v>',pg.evaluate('hoja(["cantidad"],[[.123456]])'))
        with zipfile.ZipFile(io.BytesIO(bytes(pg.evaluate('async()=>Array.from(new Uint8Array(await libro([{nombre:"Datos",cabeza:["cantidad"],filas:[[.123456]],decimales:6}]).arrayBuffer()))')))) as z:
            self.assertIn('<v>0.123456</v>',z.read('xl/worksheets/sheet1.xml').decode())


if __name__=='__main__':unittest.main(verbosity=2)
