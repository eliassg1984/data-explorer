"""Meseros como pieza propia (#719): cuentas originales, pozo y exportación.

Sin red ni datos reales. Contrasta los tres turnos, los dos repartos y
las bajadas a mesas, conservando siempre el equipo completo de la planilla.
"""
import base64
import datetime as dt
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

from graficos import ventas_meseros as vm
from graficos import ventas_meseros_datos as datos

ROOT=Path(__file__).parent
JS=(ROOT/'graficos/ventas_meseros.js').read_text(encoding='utf-8')
CSS=(ROOT/'graficos/ventas_meseros.css').read_text(encoding='utf-8')
INI,FIN=dt.date(2026,10,1),dt.date(2026,10,23)


def ventas():
    filas=[]
    def pedido(ped,mesero,turno,f,venta,pax=2,tip=10,tarj=True,desc=0,pagos=1,clase='Venta'):
        for i,prod in enumerate(['Plato','Agua']):
            for k in range(pagos):
                filas.append({'LLAVE LOCAL PEDIDO':ped,'NOMBRE MESERO':mesero,'SERVICIO':turno,
                  'FEC REG DOCUMENTO':pd.Timestamp(f),'VENTA ITEM DDOCUMENTO':venta*(.7 if i==0 else .3),
                  'CANTIDAD ITEM DDOCUMENTO':1 if i==0 else 2,'CANT PAX':pax,
                  'LLAVE LOCAL DOCUMENTO':'D'+ped,'NUMERO DOCUMENTO':'B001-'+ped,
                  'LLAVE LOCAL DOCUMENTO ITEM':ped+'I'+str(i),
                  'LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO':ped+'P'+str(k),
                  'NOMBRE TIPO PAGO':'Tarjeta de Crédito' if tarj and k==0 else 'Efectivo',
                  'MONTO PROPINA':tip if k==0 else 0,'NOMB ITEM VENTA':prod,
                  'GRUPO':'Alimentos' if i==0 else 'Bebidas s/ Alcohol','CLASE VENTA':clase,
                  'DESCUENTO ITEM DDOCUMENTO':desc*(.7 if i==0 else .3),
                  'FECHA REGISTRO PAGO DOC':pd.Timestamp(f)+pd.Timedelta(minutes=1)})
    for k,f in enumerate(pd.date_range('2025-11-01','2026-10-23',freq='7D')):
        for j,nom in enumerate(['ANA','BETO','CARLA']):
            for turno,hora in [('ALMUERZO',13),('CENA',22)]:
                tip=[0,5,9.5,10.5,15,20][(k+j)%6]
                pedido(f'{k}-{j}-{turno}',nom,turno,f+pd.Timedelta(hours=hora),100+j*25,
                       tip=tip,desc=50 if (k+j)%3==0 else 0,pagos=2 if j==0 else 1)
    pedido('medianoche','CARLA','CENA','2026-10-23 00:04',75,tip=7.5)
    pedido('efectivo','ANA','ALMUERZO','2026-10-20 14:00',70,tip=0,tarj=False)
    pedido('sinmesero',None,'CENA','2026-10-20 21:00',90,tip=0,pax=0)
    pedido('cortesia','ANA','CENA','2026-10-20 21:00',80,tip=8,clase='Cortesía')
    pedido('devolucion','ANA','CENA','2026-10-21 21:00',-40,pax=-1,tip=-2)
    # Un pozo con tercio de céntimo: conserva la división antes de mostrar.
    for j,nom in enumerate(['ANA','BETO','CARLA']):
        pedido('tercio'+str(j),nom,'CENA','2026-10-19 21:00',10,tip=.01 if j==0 else 0)
    return pd.DataFrame(filas)


def armar(d=None,rango=(INI,FIN),P0_missing=False):
    d=ventas() if d is None else d
    P,H=vm.preparar(d)
    actual=P[P.dia.dt.date.between(*rango)]
    items=H[H.dia.dt.date.between(*rango)]
    raw=d[d['FEC REG DOCUMENTO'].dt.date.between(*rango)]
    i0,f0=vm.periodo_anterior(*rango)
    prev=P[P.dia.dt.date.between(i0,f0)]
    return datos.armar(raw,actual,items,None if P0_missing else prev,P,rango,(('Alimentos',),(),(),())),actual,items,prev,P


class Contrato(unittest.TestCase):
    def test_dos_granos_documentos_descuento_y_corte(self):
        P,actual,items,_,_=armar()
        json.dumps(P,allow_nan=False)
        self.assertEqual(len(P['actual']),len(actual))
        self.assertEqual(len(P['items']),len(items))
        self.assertEqual(P['corte_ms'],4*60000)
        self.assertAlmostEqual(sum(r[8] for r in P['actual']),actual.propina.sum(),places=5)
        a=next(r for r in P['actual'] if P['pedidos'][r[0]]=='efectivo')
        self.assertTrue(a[10]);self.assertFalse(a[9])
        self.assertNotIn('cortesia',P['pedidos'])
        self.assertTrue(P['hay_descuento'])
        self.assertIn('const MP={ped:0,mesero:1,dia:2,hora:3,turno:4,venta:5,items:6,pax:7,propina:8,tarjeta:9,efectivo:10,desc:11,doc:12};',JS)
        self.assertNotIn('setTriggerValue',JS)
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_seis_excels_canonicos_con_decimales_y_contexto(self):
        P,actual,_,_,_=armar()
        for turno in vm.TURNOS:
            for modo in vm.REPARTOS:
                with self.subTest(turno=turno,modo=modo):
                    blob=base64.b64decode(P['libros'][f'{turno}|{modo}'])
                    with zipfile.ZipFile(io.BytesIO(blob)) as z:
                        libro=z.read('xl/workbook.xml').decode()
                        self.assertTrue(all(s in libro for s in ['Resumen','Planilla','Por turno','Pagos con propina','Contexto']))
                        # Se conserva el formato monetario y las fórmulas del exportador original.
                        self.assertIn('#,##0.00',z.read('xl/styles.xml').decode())
                        self.assertIn('<f>SUM(',z.read('xl/worksheets/sheet2.xml').decode())
                        if modo==vm.REPARTOS[1] and turno!='Almuerzo':
                            self.assertIn('0.00333333',z.read('xl/worksheets/sheet3.xml').decode())
        self.assertAlmostEqual(vm.pozo(actual)['parte'].sum(),vm.pozo(actual)['propia'].sum(),places=8)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P,cls.actual,cls.items,cls.prev,cls.hist=armar()
        cls.pw=sync_playwright().start()
        try:cls.b=cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.b.new_page(viewport={'width':1323,'height':619},accept_downloads=True)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--border-lavender:rgb(190,180,235);--success:green;--danger:crimson;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarMes=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.b.close();cls.pw.stop()

    def calc(self,s=None,P=None):
        return self.pg.evaluate('''([P,s])=>{const B=__mesCalc.leer(P),st={...__mesUI.inicial(),...s},T=__mesCalc.equipo(B,st.turno);if(st.ms==null)st.ms=T.rank[0]?.id;
          return {R:T.R,R0:T.R0,z:T.z,plan:__mesCalc.planilla(T.z,st.modo),D:T.distribucion,S:__mesCalc.scope(B,T,st),meses:__mesCalc.historia(B,st),t:T.t}}''',[P or self.P,s or {}])

    def mount(self,P=None):self.pg.evaluate('''P=>{window.__vtMes=undefined;document.querySelector('#montar').innerHTML='';__montarMes({data:P,parentElement:document.querySelector('#montar')})}''',P or self.P)

    def test_resumen_pozo_planilla_tres_turnos_dos_repartos(self):
        for turno in vm.TURNOS:
            pa=vm.del_turno(self.actual,turno)
            prev=vm.hasta_la_misma_hora(vm.del_turno(self.prev,turno),vm.periodo_anterior(INI,FIN)[1],vm.hora_de_corte(self.actual,FIN))
            for modo in vm.REPARTOS:
                with self.subTest(turno=turno,modo=modo):
                    out=self.calc({'turno':turno,'modo':modo})
                    for key,df in [('R',pa),('R0',prev)]:
                        ref=vm.resumen(df)
                        for r in out[key]:
                            for c in vm._COLS_RESUMEN:self.assertAlmostEqual(r[c],ref.loc[self.P['meseros'][r['id']],c],places=5)
                    z=vm.pozo(pa)
                    self.assertEqual(len(z),len(out['z']))
                    refs={(str(r.dia.date()),r.turno,r.mesero):r for r in z.itertuples(index=False)}
                    for r in out['z']:
                        dia=(pd.Timestamp('1970-01-01')+pd.Timedelta(days=r['dia'])).date()
                        ref=refs[(str(dia),self.P['turnos'][r['turno']],self.P['meseros'][r['mesero']])]
                        for k in ['mesas','propia','pozo','n','parte']:self.assertAlmostEqual(r[k],getattr(ref,k),places=5)
                    soles,mesas=vm.planilla(pa,modo)
                    for r in out['plan']['filas']:
                        for i,dia in enumerate(out['plan']['dias']):
                            d=pd.Timestamp('1970-01-01')+pd.Timedelta(days=dia);nom=self.P['meseros'][r['id']]
                            self.assertAlmostEqual(r['valores'][i],soles.loc[nom,d],places=5)
                            self.assertEqual(r['mesas'][i],mesas.loc[nom,d])
                    self.assertAlmostEqual(out['plan']['total'],soles.to_numpy().sum(),places=5)

    def test_distribucion_y_lo_vendido_y_meses(self):
        for turno in vm.TURNOS:
            pa=vm.del_turno(self.actual,turno);dist=vm.distribucion(pa)
            for ms,nom in enumerate(self.P['meseros']):
                out=self.calc({'turno':turno,'ms':ms})
                for r in out['D']:
                    self.assertEqual(r['tramos'],dist.loc[self.P['meseros'][r['id']]].tolist())
                pl,be,_=vm.vendido(vm.del_turno(self.items,turno),nom)
                for k,ref in [('platos',pl),('bebidas',be)]:
                    self.assertEqual([self.P['prods'][r['id']] for r in out['S']['vendido'][k]],ref['prod'].tolist())
                    for a,b in zip(out['S']['vendido'][k],ref.to_dict('records')):
                        for c in ['u','venta']:self.assertAlmostEqual(a[c],b[c],places=5)
                prop,venta=vm.mensual(vm.del_turno(self.hist,turno))
                for r in out['meses']:
                    self.assertAlmostEqual(r['equipo'],prop.loc[r['mes']].sum(),places=5)
                    self.assertAlmostEqual(r['propina'],prop.loc[r['mes'],nom] if nom in prop else 0,places=5)

    def test_filtros_ficha_y_busqueda_no_reparten_pozo_sobre_subconjunto(self):
        self.mount();pg=self.pg;root=pg.locator('.msp')
        total=pg.evaluate('__vtMes.plan.total')
        root.locator('[data-acc="sinpropina"]').click()
        self.assertTrue(pg.evaluate('__vtMes.S.rows.every(r=>r.tarjeta&&r.propina<=0&&r.venta>0)'))
        self.assertEqual(pg.evaluate('__vtMes.plan.total'),total)
        root.locator('[data-acc="buscar"]').fill('Ana')
        self.assertEqual(root.locator('.ms-rank-scroll tbody tr').count(),1)
        self.assertEqual(pg.evaluate('__vtMes.plan.total'),total)
        root.locator('[data-acc="modo"][data-v="Pozo común"]').click()
        self.assertAlmostEqual(pg.evaluate('__vtMes.plan.total'),total,places=6)

    def test_celda_mapa_pedido_y_excel(self):
        self.mount();pg=self.pg;root=pg.locator('.msp')
        cell=root.locator('[data-acc="celda"]').filter(has_text='10.00').first
        if not cell.count():cell=root.locator('[data-acc="celda"]').first
        cell.click();self.assertIsNotNone(pg.evaluate('__vtMes.st.celda'))
        self.assertTrue(pg.evaluate('__vtMes.S.rows.every(r=>r.f===__vtMes.st.celda.f)'))
        rows=root.locator('tr[data-acc="pedido"]')
        if rows.count():
            rows.first.click();self.assertIsNotNone(pg.evaluate('__vtMes.st.pedido'))
            self.assertIn('Pedido',root.locator('.ms-ficha').inner_text())
            root.locator('[data-acc="volver"]').click()
        root.locator('[data-acc="weekday"]').first.click()
        self.assertIsNotNone(pg.evaluate('__vtMes.st.weekday'))
        self.assertTrue(pg.evaluate('__vtMes.S.rows.every(r=>(new Date(r.f*864e5).getUTCDay()+6)%7===__vtMes.st.weekday)'))
        for acc,nombre,hoja in [('excelplan','planilla','Planilla'),('excelmesas','mesas','Mesas')]:
            with pg.expect_download() as dl:root.locator(f'[data-acc="{acc}"]').click()
            with tempfile.TemporaryDirectory() as temp:
                p=Path(temp)/(nombre+'.xlsx');dl.value.save_as(str(p))
                with zipfile.ZipFile(p) as z:
                    self.assertIn(hoja,z.read('xl/workbook.xml').decode())
                    for f in z.namelist():
                        if f.endswith('.xml'):ET.fromstring(z.read(f))

    def test_remontaje_fecha_movil_y_historico_ausente(self):
        self.mount();pg=self.pg;root=pg.locator('.msp')
        root.locator('[data-acc="turno"][data-v="Cena"]').click()
        root.locator('[data-acc="tab"][data-v="12 meses"]').click()
        self.assertEqual(root.locator('.ms-meses svg').count(),1)
        pg.evaluate('P=>__montarMes({data:P,parentElement:document.querySelector("#montar")})',self.P)
        self.assertEqual(pg.evaluate('__vtMes.st.turno'),'Cena')
        pg.set_viewport_size({'width':390,'height':844});pg.wait_for_function('document.documentElement.scrollWidth<=390')
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619})
        P,*_=armar(P0_missing=True)
        self.mount(P)
        self.assertIn('sin datos anteriores disponibles',root.inner_text())

    def test_excel_de_ajuste_deja_sin_base_el_porcentaje(self):
        self.mount();pg=self.pg;root=pg.locator('.msp')
        root.locator('tr[data-acc="mesero"]').filter(has_text='Ana').click()
        root.locator('[data-acc="tab"][data-v="Mesas"]').click()
        with pg.expect_download() as dl:root.locator('[data-acc="excelmesas"]').click()
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'ajustes.xlsx';dl.value.save_as(str(p))
            with zipfile.ZipFile(p) as z:
                tree=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            row=next(r for r in tree.findall('.//s:row',ns)
                     if any(t.text=='devolucion' for t in r.findall('.//s:t',ns)))
            self.assertFalse(any(c.attrib['r'].startswith('I') for c in row))


if __name__=='__main__':unittest.main()
