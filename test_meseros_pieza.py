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
                  'GRUPO':'Alimentos' if i==0 else 'Bebidas s/ Alcohol','SUB GRUPO':'Fondos' if i==0 else 'Aguas','CLASE VENTA':clase,
                  'DESCUENTO ITEM DDOCUMENTO':desc*(.7 if i==0 else .3),
                  'FECHA REGISTRO PAGO DOC':pd.Timestamp(f)+pd.Timedelta(minutes=1),
                  # #856: el código del pedido, el pago y el cliente del comprobante.
                  'CODIGO PEDIDO DDOCUMENTO':ped,'MONTO TIPO PAGO DOC':venta/pagos,
                  'NOMBRE TARJETA PAGO':'Visa' if tarj and k==0 else None,'USUARIO REG PAGO DOC':'CAJA1',
                  'TIPO DOC':'Factura' if mesero=='BETO' else 'Boleta',
                  'CLIENTE':'Empresa SAC' if mesero=='BETO' else 'CLIENTE -',
                  'DOC CLIENTE':'20000000002' if mesero=='BETO' else '11111111'})
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


# #855: la carta activa trae un plato sin venta, uno vendido (no se repite) y el
# grupo en otra caja de letras (se escribe como en la venta).
CARTA=pd.DataFrame({'prod':['Risotto','agua','Coco'],'grupo':['ALIMENTOS','Bebidas s/ Alcohol','Postres'],
                    'sub':['fondos','Aguas','Postres']})


def pedidos_y_horas(d):
    """#856: pedidos.parquet y las horas del paloteo, de mentira: la mesa se abre
    2 h antes del comprobante, los platos se marcan 115 min antes y el último 40."""
    t=d.drop_duplicates('LLAVE LOCAL PEDIDO')
    f=t['FEC REG DOCUMENTO']
    ped=pd.DataFrame({'CODIGO PEDIDO':t['LLAVE LOCAL PEDIDO'].values,'MESA':[str(100+i%9) for i in range(len(t))],'SALON':'SALON',
        'ADULTOS':t['CANT PAX'].values,'NINOS':0,'FECHA APERTURA':(f-pd.Timedelta(hours=2)).values,
        'PRIMER ITEM':(f-pd.Timedelta(minutes=115)).values,'ULTIMO ITEM':(f-pd.Timedelta(minutes=40)).values,
        'FECHA PRECUENTA':(f-pd.Timedelta(minutes=10)).values,'PRECUENTAS':1,'ULTIMO COMPROBANTE':f.values,'USUARIO PEDIDO':'MOZO1'})
    horas=pd.concat([pd.DataFrame({'cod':t['LLAVE LOCAL PEDIDO'].values,'prod':n,'hora':(f-pd.Timedelta(minutes=m)).values,'cant':c})
                     for n,m,c in [('Plato',115,1.0),('Agua',115,2.0)]],ignore_index=True)
    return ped,horas


def armar(d=None,rango=(INI,FIN),P0_missing=False,carta=CARTA,sin_extra=False):
    d=ventas() if d is None else d
    P,H=vm.preparar(d)
    actual=P[P.dia.dt.date.between(*rango)]
    items=H[H.dia.dt.date.between(*rango)]
    raw=d[d['FEC REG DOCUMENTO'].dt.date.between(*rango)]
    i0,f0=vm.periodo_anterior(*rango)
    prev=P[P.dia.dt.date.between(i0,f0)]
    ped,horas=(None,None) if sin_extra else pedidos_y_horas(raw)
    return datos.armar(raw,actual,items,None if P0_missing else prev,P,rango,(('Alimentos',),(),(),()),carta=carta,pedidos_pos=ped,horas=horas),actual,items,prev,P


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
        # #852: el subgrupo viaja en la posición 8 de cada ítem.
        self.assertIn('const MIT={ped:0,mesero:1,dia:2,turno:3,prod:4,grupo:5,cant:6,venta:7,sub:8};',JS)
        self.assertEqual({P['subs'][r[8]] for r in P['items']},{'Fondos','Aguas'})
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
class CartaSinVenta(unittest.TestCase):
    def test_platos_activos_sin_venta_en_el_contrato(self):
        P,*_=armar()
        filas=[(P['prods'][a],P['grupos'][b],P['subs'][c]) for a,b,c in P['carta']]
        # «agua» se vendió como «Agua»: no se repite; el grupo y el subgrupo, como en la venta.
        self.assertEqual(sorted(filas),[('Coco','Postres','Postres'),('Risotto','Alimentos','Fondos')])
        P2,*_=armar(carta=None)
        self.assertEqual(P2['carta'],[])


class FichaPedido(unittest.TestCase):
    def test_ficha_de_cada_pedido(self):
        # #856: cada pago y cada comprobante UNA vez, los tiempos en minutos desde la base.
        P,actual,*_=armar()
        F={P['pedidos'][int(k)]:dict(zip(datos.FICHA,v)) for k,v in P['fichas'].items()}
        self.assertEqual(set(F),set(P['pedidos']))
        for ped,f in F.items():
            with self.subTest(ped=ped):
                self.assertEqual(f['comprobante']-f['apertura'],120)
                self.assertEqual(f['ultimo']-f['primer'],75)
                self.assertEqual([x[0] for x in f['platos']],['Plato','Agua'])
                self.assertEqual(len(f['docs']),1)
        # Dos pagos (efectivo y tarjeta) en las filas de los dos ítems: dos pagos, no cuatro.
        dos=next(p for p in F if p.split('-')[1:2]==['0'])
        self.assertEqual(len(F[dos]['pagos']),2)
        self.assertEqual(F[dos]['pagos'][0][:2],['Tarjeta de Crédito','Visa'])
        beto=next(p for p in F if p.split('-')[1:2]==['1'])
        self.assertEqual(F[beto]['docs'][0][2:],['Empresa SAC','20000000002'])
        self.assertEqual(json.loads(json.dumps(P['fichas'],allow_nan=False)),P['fichas'])
        # Sin los dos parquets la ficha sigue, sin mesa ni platos.
        P2,*_=armar(sin_extra=True)
        f=dict(zip(datos.FICHA,next(iter(P2['fichas'].values()))))
        self.assertIsNone(f['apertura']);self.assertIsNone(f['platos']);self.assertFalse(P2['hay_platos'])

    def test_tildes_rotas_del_pago(self):
        self.assertEqual(datos._tildes('Tarjeta de Cr�dito'),'Tarjeta de Crédito')


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

    def test_venta_por_mesero_contra_pandas(self):
        # #852: cada celda, por nombre de columna, contra un groupby de pandas.
        col={'Grupo':'grupo','Subgrupo':'sub','Plato':'prod'}
        for turno in vm.TURNOS:
            it=vm.del_turno(self.items,turno)
            ref=it.groupby([c for c in ['grupo','sub','prod','mesero']],as_index=False).agg(u=('cant','sum'),v=('venta','sum'))
            por_ms=it.groupby('mesero')['venta'].sum()
            for dim,c in col.items():
                with self.subTest(turno=turno,dim=dim):
                    out=self.pg.evaluate("""([P,s])=>{const B=__mesCalc.leer(P),st={...__mesUI.inicial(),...s},C=__mesCalc.cruce(B,st);
                      return C.filas.flatMap(f=>[...f.cel].map(([ms,x])=>({fila:f.label,ms:P.meseros[ms],u:x.u,v:x.v,pct:__mesCalc.valor('% de su venta',x,C.col.get(ms))})))}""",[self.P,{'turno':turno,'vdim':dim}])
                    r2=ref.groupby([c,'mesero'],as_index=False).agg(u=('u','sum'),v=('v','sum'))
                    self.assertEqual(len(out),len(r2))
                    idx={(a,b):(u,v) for a,b,u,v in r2[[c,'mesero','u','v']].itertuples(index=False,name=None)}
                    for o in out:
                        u,v=idx[(o['fila'],o['ms'])]
                        self.assertAlmostEqual(o['u'],u,places=5);self.assertAlmostEqual(o['v'],v,places=5)
                        if por_ms[o['ms']]>0:self.assertAlmostEqual(o['pct'],v/por_ms[o['ms']],places=6)

    def test_venta_por_mesero_controles_filtros_y_excel(self):
        self.mount();pg=self.pg;card=pg.locator('.ms-vt')
        total=self.items['venta'].sum()
        foot=lambda:card.locator('tfoot td').last.inner_text()
        num=lambda:float(foot().replace(',',''))
        self.assertAlmostEqual(num(),total,delta=.51)
        card.locator('[data-acc="vdim"][data-v="Plato"]').click()
        self.assertEqual(card.locator('tbody tr:not(.ms-vt-secc)').count(),self.items['prod'].nunique())
        g=self.P['grupos'].index('Alimentos')
        card.locator('[data-acc="vgrupo"]').select_option(str(g))
        self.assertEqual(pg.evaluate('__vtMes.C.filas.map(f=>f.label)'),['Plato'])
        card.locator('[data-acc="vgrupo"]').select_option('-1')
        # Buscar escribiendo de a una letra: el foco no se pierde con el redibujo.
        card.locator('[data-acc="vbuscar"]').press_sequentially('agu')
        self.assertEqual(pg.evaluate('document.activeElement.dataset?.acc||document.activeElement.shadowRoot?.activeElement?.dataset.acc'),'vbuscar')
        self.assertEqual(card.locator('tbody tr:not(.ms-vt-secc)').count(),1)
        self.assertIn('Total de lo visible',card.locator('tfoot').inner_text())
        agua=self.items.loc[self.items['prod']=='Agua','venta'].sum()
        self.assertAlmostEqual(num(),agua,delta=.51)
        card.locator('[data-acc="vbuscar"]').fill('')
        card.locator('[data-acc="vmed"][data-v="% de su venta"]').click()
        self.assertEqual(foot(),'100.0%')
        # Ordenar por un mesero y al revés.
        ana=self.P['meseros'].index('Ana')
        card.locator(f'[data-acc="vorden"][data-v="{ana}"]').click()
        self.assertEqual(pg.evaluate('[__vtMes.st.vorden,__vtMes.st.vdir]'),[str(ana),-1])
        card.locator(f'[data-acc="vorden"][data-v="{ana}"]').click()
        self.assertEqual(pg.evaluate('__vtMes.st.vdir'),1)
        card.locator('[data-acc="vmed"][data-v="Venta"]').click()
        with pg.expect_download() as dl:card.locator('[data-acc="excelventa"]').click()
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'venta.xlsx';dl.value.save_as(str(p))
            with zipfile.ZipFile(p) as z:
                wb=z.read('xl/workbook.xml').decode()
                for h in ['Plato × mesero','Detalle','Contexto']:self.assertIn(h,wb)
                ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                det=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
                ventas=[float(c.find('s:v',ns).text) for c in det.iter('{%s}c'%ns['s']) if c.attrib['r'].startswith('F') and c.find('s:v',ns) is not None]
                self.assertAlmostEqual(sum(ventas),total,places=1)
        # El turno de arriba manda también acá.
        pg.locator('.ms-overview [data-acc="turno"][data-v="Cena"]').click()
        self.assertIn('Venta por mesero · Cena',card.inner_text())
        cena=vm.del_turno(self.items,'Cena')['venta'].sum()
        self.assertAlmostEqual(num(),cena,delta=.51)

    def test_venta_por_mesero_precio_subgrupo_y_elegidas(self):
        # #853: precio unitario contra pandas, filtro de subgrupo, columnas de
        # grupo y subgrupo, y «Solo elegidas» con su total y su Excel.
        it=self.items
        ref=it.groupby(['prod','mesero'],as_index=False).agg(u=('cant','sum'),v=('venta','sum'))
        out=self.pg.evaluate("""([P])=>{const B=__mesCalc.leer(P),st={...__mesUI.inicial(),vdim:'Plato'},C=__mesCalc.cruce(B,st);
          return C.filas.flatMap(f=>[...f.cel].map(([ms,x])=>({fila:f.label,ms:P.meseros[ms],pu:__mesCalc.valor('Precio unitario',x)})))}""",[self.P])
        idx={(a,b):(u,v) for a,b,u,v in ref[['prod','mesero','u','v']].itertuples(index=False,name=None)}
        for o in out:
            u,v=idx[(o['fila'],o['ms'])]
            if u>0:self.assertAlmostEqual(o['pu'],v/u,places=6)
            else:self.assertIsNone(o['pu'])
        self.mount();pg=self.pg;card=pg.locator('.ms-vt')
        card.locator('[data-acc="vdim"][data-v="Plato"]').click()
        card.locator('[data-acc="vsec"]').click()  # sin secciones, Grupo y Subgrupo son columnas
        cab=[t.strip(' ▲▼') for t in card.locator('thead th').all_inner_texts()]
        self.assertEqual(cab[:3],['Plato','Grupo','Subgrupo'])
        # Subgrupo: las opciones siguen al grupo, y filtra.
        s=self.P['subs'].index('Aguas')
        card.locator('[data-acc="vsub"]').select_option(str(s))
        esperados=sorted(it.loc[it['sub']=='Aguas','prod'].unique())
        self.assertEqual(sorted(pg.evaluate('__vtMes.C.filas.map(f=>f.label)')),esperados)
        card.locator('[data-acc="vsub"]').select_option('-1')
        # Elegir dos platos desde la búsqueda y ver sólo esos.
        elegidos=['Agua','Plato']
        for n in elegidos:
            card.locator('[data-acc="vbuscar"]').fill(n.lower())
            card.locator(f'[data-acc="vsel"][data-v="{n}"]').check()
        card.locator('[data-acc="vsolo"]').click()
        self.assertEqual(pg.evaluate('__vtMes.st.vq'),'')
        self.assertEqual(sorted(card.locator('.ms-vt-nom b').all_inner_texts()),elegidos)
        total=it.loc[it['prod'].isin(elegidos),'venta'].sum()
        self.assertAlmostEqual(float(card.locator('tfoot td').last.inner_text().replace(',','')),total,delta=.51)
        card.locator('[data-acc="vmed"][data-v="Precio unitario"]').click()
        u=it.loc[it['prod'].isin(elegidos),'cant'].sum()
        self.assertAlmostEqual(float(card.locator('tfoot td').last.inner_text().replace(',','')),total/u,delta=.006)
        with pg.expect_download() as dl:card.locator('[data-acc="excelventa"]').click()
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'venta.xlsx';dl.value.save_as(str(p))
            with zipfile.ZipFile(p) as z:
                ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                det=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
                ventas=[float(c.find('s:v',ns).text) for c in det.iter('{%s}c'%ns['s']) if c.attrib['r'].startswith('F') and c.find('s:v',ns) is not None]
                self.assertAlmostEqual(sum(ventas),total,places=1)
        # Las elegidas son por nombre: sobreviven a otra fecha (remontaje).
        pg.evaluate('P=>__montarMes({data:{...P,sello:"otro"},parentElement:document.querySelector("#montar")})',self.P)
        self.assertEqual(sorted(card.locator('.ms-vt-nom b').all_inner_texts()),elegidos)
        card.locator('[data-acc="vlimpiar"]').click()
        self.assertEqual(card.locator('tbody tr:not(.ms-vt-secc)').count(),it['prod'].nunique())

    def test_unidades_y_venta_secciones_sin_venta_y_pedidos(self):
        # #855: dos columnas por mesero, secciones con subtotal, platos sin venta
        # (carta activa y elegidos) y el panel con los pedidos de una celda.
        self.mount();pg=self.pg;card=pg.locator('.ms-vt');it=self.items
        self.assertEqual(pg.evaluate('__vtMes.st.vmed'),'Unidades y venta')
        ncols=pg.evaluate('__vtMes.C.cols.length')
        self.assertEqual(card.locator('.ms-vt-sub th').count(),2*ncols+2)
        num=lambda t:float(t.replace(',',''))
        self.assertAlmostEqual(num(card.locator('tfoot td').last.inner_text()),it['venta'].sum(),delta=.006)
        self.assertAlmostEqual(num(card.locator('tfoot td').nth(-2).inner_text()),it['cant'].sum(),delta=.006)
        card.locator('[data-acc="vdim"][data-v="Plato"]').click()
        bandas=card.locator('tr.ms-vt-secc')
        self.assertEqual(bandas.count(),2)
        for sub in ['Fondos','Aguas']:
            fila=bandas.filter(has_text=sub).locator('td')
            self.assertAlmostEqual(num(fila.last.inner_text()),it.loc[it['sub']==sub,'venta'].sum(),delta=.006)
        # Los de la carta sin venta, en cero y en su sección; el total no cambia.
        card.locator('[data-acc="vsin"]').click()
        noms=card.locator('.ms-vt-nom b').all_inner_texts()
        for n in ['Risotto','Coco']:self.assertIn(n,noms)
        self.assertEqual(card.locator('tr.ms-vt-secc').count(),3)
        self.assertIn('Risotto',card.locator('tr.ms-vt-secc',has_text='Fondos').locator('xpath=following-sibling::tr[1]').inner_text()+card.locator('tbody').inner_text())
        self.assertAlmostEqual(num(card.locator('tfoot td').last.inner_text()),it['venta'].sum(),delta=.006)
        # Un elegido sin venta se queda aunque se apague el interruptor.
        card.locator('[data-acc="vsel"][data-v="Risotto"]').check()
        card.locator('[data-acc="vsin"]').click()
        self.assertIn('Risotto',card.locator('.ms-vt-nom b').all_inner_texts())
        self.assertNotIn('Coco',card.locator('.ms-vt-nom b').all_inner_texts())
        card.locator('[data-acc="vlimpiar"]').click()
        # Los pedidos de Ana × Plato: los mismos que en pandas, y suman la celda.
        ana=self.P['meseros'].index('Ana');ip=self.P['prods'].index('Plato')
        card.locator(f'td[data-acc="vcel"][data-v="{ana}~k:{ip}"]').last.click()
        det=card.locator('.ms-vt-det');self.assertEqual(det.count(),1)
        D=pg.evaluate('(()=>{const D=__vtMes.D;return {peds:D.lista.map(p=>__vtMes.B.P.pedidos[p.ped]),u:D.u,v:D.v}})()')
        ref=it[(it['prod']=='Plato')&(it['mesero']=='Ana')]
        self.assertEqual(sorted(D['peds']),sorted(ref['ped'].astype(str).unique()))
        self.assertAlmostEqual(D['u'],ref['cant'].sum(),places=5);self.assertAlmostEqual(D['v'],ref['venta'].sum(),places=5)
        # Abrir un pedido muestra todas sus líneas, y la de la celda marcada.
        det.locator('tr[data-acc="vdetped"]').first.click()
        ped=pg.evaluate('__vtMes.B.P.pedidos[__vtMes.st.vdetPed]')
        self.assertEqual(det.locator('.ms-vt-det-lin tbody tr').count(),int((it['ped'].astype(str)==ped).sum()))
        self.assertEqual(det.locator('.ms-vt-det-lin tbody tr.on').count(),1)
        with pg.expect_download() as dl:det.locator('[data-acc="excelped"]').click()
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'pedidos.xlsx';dl.value.save_as(str(p))
            with zipfile.ZipFile(p) as z:
                wb=z.read('xl/workbook.xml').decode()
                for h in ['Pedidos','Lo cobrado','Cómo se pidió','Pagos','Contexto']:self.assertIn(h,wb)
        pg.keyboard.press('Escape');self.assertEqual(card.locator('.ms-vt-det').count(),0)
        # El total de abajo abre todo lo visible: la venta entera del rango.
        card.locator('tfoot td[data-acc="vcel"]').last.click()
        self.assertAlmostEqual(pg.evaluate('__vtMes.D.v'),it['venta'].sum(),places=4)
        self.assertEqual(pg.evaluate('__vtMes.D.lista.length'),it['ped'].nunique())

    def test_tabla_de_pedidos_y_ficha(self):
        # #856: «Tabla» con una fila por pedido y todas las columnas; la ficha del
        # pedido con su recorrido, el comprobante, el pago y cómo se fue pidiendo.
        self.mount();pg=self.pg;card=pg.locator('.ms-vt');it=self.items
        card.locator('[data-acc="vdim"][data-v="Plato"]').click()
        ana=self.P['meseros'].index('Ana');ip=self.P['prods'].index('Plato')
        card.locator(f'td[data-acc="vcel"][data-v="{ana}~k:{ip}"]').last.click()
        det=card.locator('.ms-vt-det')
        det.locator('[data-acc="vdetvista"][data-v="Tabla"]').click()
        self.assertIn('ancho',det.get_attribute('class'))
        cab=[t.strip(' ▲▼') for t in det.locator('thead th').all_inner_texts()]
        for c in ['Mesa','Apertura','Precuenta','Duración','Cliente','Pago','Propina','Total pedido']:self.assertIn(c,cab)
        ref=it[(it['prod']=='Plato')&(it['mesero']=='Ana')]
        self.assertEqual(det.locator('tbody tr[data-acc="vdetped"]').count(),ref['ped'].nunique())
        self.assertIn('2 h 00',det.locator('tbody tr[data-acc="vdetped"]').first.inner_text())
        # Ordenar por mesa y al revés.
        det.locator('[data-acc="vdetorden"][data-v="mesa"]').click()
        mesas=pg.evaluate('__vtMes.D.lista.map(p=>p.fi.mesa)')
        self.assertEqual(mesas,sorted(mesas,key=int))
        det.locator('[data-acc="vdetorden"][data-v="mesa"]').click()
        self.assertEqual(pg.evaluate('__vtMes.D.lista.map(p=>p.fi.mesa)'),sorted(mesas,key=int,reverse=True))
        # La ficha: seis pasos, Ana factura con boleta genérica, dos tandas en el mismo minuto.
        det.locator('tbody tr[data-acc="vdetped"]').first.click()
        ficha=det.locator('.ms-ped')
        self.assertEqual(ficha.locator('.ms-tl li').count(),6)
        self.assertIn('Consumidor final',ficha.inner_text())
        self.assertEqual(ficha.locator('.ms-tandas li').count(),1)
        self.assertIn('Agua ×2',ficha.locator('.ms-tandas').inner_text())
        self.assertIn('+1 h 15',ficha.locator('.ms-tl').inner_text())
        with pg.expect_download() as dl:det.locator('[data-acc="excelped"]').click()
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'pedidos.xlsx';dl.value.save_as(str(p))
            with zipfile.ZipFile(p) as z:
                wb=z.read('xl/workbook.xml').decode()
                for h in ['Pedidos','Lo cobrado','Pagos','Contexto']:self.assertIn(h,wb)
                ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                hoja=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
                self.assertEqual(len(hoja.findall('.//s:row',ns))-1,ref['ped'].nunique())
        # El cliente: una empresa sin nombre (la razón social está en tEmpresa) dice su RUC;
        # el genérico del POS es «Consumidor final»; el «-» de un apellido vacío se quita.
        casos=[[['F1','Factura','','20000000001']],[['B1','Boleta','CLIENTE','11111111']],
               [['B2','Boleta','PEREZ JUAN -','40000000']],[['B3','Boleta','EMPRESA FICTICIA S.A.','20000000001']]]
        self.assertEqual(pg.evaluate('cs=>cs.map(d=>__mesCalc.cliente({docs:d}))',casos),
                         ['RUC 20000000001','Consumidor final','PEREZ JUAN','EMPRESA FICTICIA S.A.'])
        # Un pedido de Beto lleva la factura con su cliente.
        pg.keyboard.press('Escape')  # el panel ancho tapa la tabla: se cierra para elegir otra celda
        beto=self.P['meseros'].index('Beto')
        card.locator(f'td[data-acc="vcel"][data-v="{beto}~k:{ip}"]').last.click()
        det.locator('tbody tr[data-acc="vdetped"]').first.click()
        self.assertIn('Empresa SAC',det.locator('.ms-ped').inner_text())

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
