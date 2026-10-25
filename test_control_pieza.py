"""Control de pedidos nativo: reglas originales, investigación y exportación (#723)."""
import inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd

from graficos import ventas_control as vc
from graficos import ventas_control_datos as datos

ROOT=Path(__file__).parent
JS=(ROOT/'graficos/ventas_control.js').read_text(encoding='utf-8')
CSS=(ROOT/'graficos/ventas_control.css').read_text(encoding='utf-8')
RANGO=(pd.Timestamp('2025-09-01'),pd.Timestamp('2025-09-07'))


def muestra():
    rows=[]
    for i in range(34):
        ap=RANGO[0]+pd.Timedelta(days=i%7,hours=12+i%2*8,minutes=i%6)
        primer=ap+pd.Timedelta(minutes=i%8)
        if i==8:primer=ap+pd.Timedelta(minutes=800)
        ultimo=primer+pd.Timedelta(minutes=30+i)
        pre=ultimo+pd.Timedelta(minutes=10+i)
        comp=pre+pd.Timedelta(minutes=i%10)
        rows.append({'CODIGO PEDIDO':f'{i:04}','FECHA APERTURA':ap,'DIA CONTABLE':ap.normalize(),
                     'ESTADO PEDIDO':'ANULADO' if i in [2,5] else 'COBRADO','CANAL VENTA':'Salón' if i%2 else 'Terraza',
                     'MESA':'SIN MESA' if i==3 else str(100+i%4),'MESERO':['Ana','Bruno'][i%2],
                     'ADULTOS':[0,1,2,4,6,8][i%6],'NINOS':0,'PRIMER ITEM':primer,'ULTIMO ITEM':ultimo,
                     'PLATOS':i+1,'MONTO PEDIDO':(i+1)*17.123456789,'MONTO ANULADO':12.123456789 if i in [2,5] else 0,
                     'FECHA PRECUENTA':pre if i!=9 else pd.NaT,'PRECUENTAS':2 if i%7==0 else 1,
                     'ULTIMO COMPROBANTE':comp if i!=4 else pd.NaT,
                     'FECHA ANULACION':ap+pd.Timedelta(minutes=2) if i in [2,5] else pd.NaT,
                     'USUARIO ANULACION':'Cajero','MOTIVO ANULACION':'MESA VACIA' if i==2 else 'ERROR PRECIO' if i==5 else ''})
    # Foto que cruza medianoche y extremo final incluido.
    rows[0].update({'FECHA APERTURA':pd.Timestamp('2025-09-01 23:00'),'PRIMER ITEM':pd.Timestamp('2025-09-01 23:01'),
                    'ULTIMO ITEM':pd.Timestamp('2025-09-02 00:30'),'FECHA PRECUENTA':pd.Timestamp('2025-09-02 01:00'),
                    'ULTIMO COMPROBANTE':pd.Timestamp('2025-09-02 01:30')})
    raw=pd.DataFrame(rows)
    trs=[]
    for i in range(18):
        origin=rows[i];f=origin['FECHA APERTURA']+pd.Timedelta(minutes=1 if i%3==0 else 8)
        destino=rows[(i+1)%len(rows)]
        trs.append({'TIPO':vc.PLATO_ANULADO if i%2==0 else vc.TRANSFERENCIA,'CODIGO PEDIDO':origin['CODIGO PEDIDO'],
                    'PEDIDO DESTINO':destino['CODIGO PEDIDO'],'PRODUCTO':f'Plato {i%5}','CANTIDAD':1.123456789,
                    'VENTA':(i+1)*3.123456789,'FECHA ITEM':origin['FECHA APERTURA'],'FECHA TRANSACCION':f,
                    'DIA CONTABLE':origin['DIA CONTABLE'],'USUARIO TRANSACCION':['Caja','Servicio'][i%2],
                    'ENVIADO A COCINA':1 if i%4==0 else 0,'OBSERVACION':'Cambio <sin salsa>'})
    rawt=pd.DataFrame(trs)
    return raw,rawt,vc.pedidos(raw),vc.transacciones(rawt)


def payload():
    raw,rawt,p,t=muestra()
    return datos.armar(p,t,RANGO,cortesias={'0002','0006'}),p,t,raw,rawt


class Contrato(unittest.TestCase):
    def test_montaje_y_cache_de_fuentes_con_apptest(self):
        from streamlit.testing.v1 import AppTest
        from graficos import ventas_control_pieza as pieza
        import streamlit as st
        _,p,t,_,_=payload()
        def recibir(**kw):
            st.session_state['_mensaje_ctl']=kw['data']
        with patch.object(pieza,'_PIEZA',recibir),patch.object(vc,'_cargar',return_value=(p,t)) as cargar,\
             patch.object(vc,'_rango',return_value=RANGO),patch.object(pieza.data,'sello_datos',return_value='version'),\
             patch.object(pieza.data,'venta_por_turno',return_value=True),\
             patch.object(vc,'selector_fecha_tarjeta',lambda *a,**kw: st.button('Elegir fecha')):
            app=AppTest.from_string('from graficos.ventas_control_pieza import renderizar\nrenderizar(cortesias={"0002"})').run(timeout=30)
            self.assertFalse(app.exception);self.assertEqual(cargar.call_count,1)
            self.assertTrue(app.session_state['_mensaje_ctl']['fuentes']['pedidos'])
            app.run(timeout=30);self.assertFalse(app.exception);self.assertEqual(cargar.call_count,1)

    def test_precision_calendario_y_sello(self):
        P,p,t,_,_=payload();json.dumps(P,allow_nan=False)
        self.assertEqual(P['p'][0][P['cp'].index('monto')],float(p.iloc[0].monto))
        self.assertEqual(P['sello'],datos.armar(p,t,RANGO,cortesias={'0006','0002'})['sello'])
        self.assertEqual(P['p'][0][0],'0000')
        p.loc[0,'monto']+=.000000001
        self.assertNotEqual(P['sello'],datos.armar(p,t,RANGO,cortesias={'0006','0002'})['sello'])
        self.assertEqual(P['slots'][0],'12:00');self.assertEqual(P['slots'][-1],'01:30')
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_normalizacion_y_tramos_siguen_en_python(self):
        _,p,t,_,_=payload();pp,tt,b=datos.preparar(p,t,{'0002','0006'})
        ref=vc.tiempos(p)
        for c in ['espera','comida','sobremesa','cobro','total']:
            np.testing.assert_allclose(b[c],ref[c],equal_nan=True)
        self.assertEqual(set(b.ped),set(ref.ped));self.assertNotIn('0003',set(b.ped))
        self.assertEqual(b.loc[b.ped=='0008','inicio'].iloc[0],p.loc[p.ped=='0008','primer'].iloc[0])
        tr=tt[tt.tipo==vc.TRANSFERENCIA]
        self.assertEqual(tr.clase.tolist(),vc.tipo_transferencia(tr,p,{'0002','0006'}).tolist())
        self.assertEqual(len(pp),len(p))

    def test_dia_del_turno_y_fecha_real(self):
        _,_,_,raw,rawt=payload();raw=raw.iloc[:1].copy();raw['DIA CONTABLE']=pd.Timestamp('2025-08-31')
        rawt=rawt.iloc[:1].copy();rawt['DIA CONTABLE']=pd.Timestamp('2025-08-31')
        a=datos.armar(vc.pedidos(raw),vc.transacciones(rawt),RANGO)
        b=datos.armar(vc.pedidos(raw,False),vc.transacciones(rawt,False),RANGO,turno=False)
        self.assertNotEqual(a['p'][0][1],b['p'][0][1]);self.assertFalse(b['turno'])

    def test_fuentes_vacias_y_parciales_no_rompen(self):
        _,p,t,_,_=payload()
        for a,b in [(None,None),(p,None),(None,t)]:
            P=datos.armar(a,b,RANGO);json.dumps(P,allow_nan=False)
            self.assertEqual(P['fuentes']['pedidos'],a is not None)
            self.assertEqual(P['fuentes']['transacciones'],b is not None)
        self.assertEqual(list(inspect.signature(vc._ventas_control).parameters),['cortesias','canales'])

    def test_canal_no_atribuye_transacciones_sin_pedido(self):
        rawt=muestra()[1]
        with patch.object(vc,'cargar_rango',side_effect=[None,rawt]):
            p,t=vc._cargar(*RANGO,True,('Salón',))
            self.assertIsNone(p);self.assertIsNone(t)
        with patch.object(vc,'cargar_rango',side_effect=[None,rawt]):
            p,t=vc._cargar(*RANGO,True,())
            self.assertIsNone(p);self.assertEqual(len(t),len(rawt))


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P,cls.p,cls.t,_,_=payload();cls.pp,cls.tt,cls.b=datos.preparar(cls.p,cls.t,{'0002','0006'})
        cls.pw=sync_playwright().start()
        try:cls.browser=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.browser.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(8000)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--danger:crimson;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarControl=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.pw.stop()

    def calc(self,s=None,P=None):
        return self.pg.evaluate('([P,s])=>{const F=__controlDatos;return F.calcular(F.leer(P),F.inicial(s))}',[P or self.P,s or {}])

    def mount(self,P=None):
        self.pg.evaluate('P=>{window.__ventasControl=undefined;window.__pedidosPython=[];__montarControl({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__pedidosPython.push(v)})}',P or self.P)
        return self.pg.locator('.ctl')

    def test_todos_los_granos_y_filtros_contra_las_cuentas_anteriores(self):
        for gran in vc._GRANOS:
            for mesa,mesero in [('', ''),('100',''),('','Ana'),('NO EXISTE','')]:
                p=self.pp.copy();t=self.tt.copy();b=self.b.copy()
                if mesa:p=p[p.mesa==mesa]
                if mesero:p=p[p.mesero==mesero]
                if mesa or mesero:t=t[t.ped.isin(set(p.ped))]
                b=b[b.ped.isin(set(p.ped))]
                for x in (p,t,b):x['clave']=vc._periodo_serie(x.dia,gran)
                keys=sorted(set(p.clave)|set(t.clave));rot=vc._rotulos(keys,gran,(RANGO[0].date(),RANGO[1].date()))
                a=self.calc(dict(gran=gran,mesa=mesa,mesero=mesero))
                self.assertEqual([r['clave'] for r in a['series']],keys)
                refs=[vc._filas_anulaciones(p,t,keys,rot),vc._filas_transferencias(t,keys,rot),vc._filas_tiempos(b,keys,rot)]
                for rs in refs:
                    for got,ref in zip(a['series'],rs):
                        for k,v in ref.items():
                            if k.startswith('__') or k=='periodo':continue
                            if v is None:self.assertIsNone(got[k])
                            else:self.assertAlmostEqual(got[k],v,delta=.00006 if k=='pct' else .051 if k.startswith('t_') else .006)
                self.assertAlmostEqual(a['total']['s_tr'],float(t.loc[t.tipo==vc.TRANSFERENCIA,'venta'].sum()),places=7)
                self.assertAlmostEqual(a['total']['t_total'] or 0,float(b.total.median()) if len(b) else 0,places=7)

    def test_mesas_grupos_ocupacion_y_fotos_contra_python(self):
        a=self.calc({'sub':'Ocupación'});z=vc.ocupacion(self.b,pd.date_range(*RANGO))
        np.testing.assert_equal(a['z'],z)
        self.assertEqual(a['z'][0][-1],1)
        self.assertEqual(a['nmesas'],self.b.mesa.nunique())
        ref=vc.por_mesa(self.b);got=self.pg.evaluate('P=>__controlDatos.porMesa(__controlDatos.leer(P).b)',self.P)
        for r in got:
            rr=ref[ref.mesa==r['mesa']].iloc[0]
            for k in ['usos','personas','consumo','minutos','x_hora','mediana']:self.assertAlmostEqual(r[k],float(rr[k]),places=7)
        a=self.calc({'sub':'Ocupación','foto':{'dia':int(RANGO[0].value//86400000000000),'slot':27},'lista':'Pedidos'})
        self.assertEqual([r['ped'] for r in a['filas']],['0000'])

    def test_p90_nulos_y_medianas_sin_promediar_periodos(self):
        a=self.calc({'sub':'Tiempos','lista':'Pedidos','lentos':True})
        q=float(self.b.total.quantile(.9));self.assertAlmostEqual(a['total']['p90'],q,places=7)
        self.assertEqual({r['ped'] for r in a['filas']},set(self.b.loc[self.b.total>=q,'ped']))
        self.assertIsNone(self.pg.evaluate('__controlDatos.quantil([null,null])'))
        self.assertEqual(self.pg.evaluate('__controlDatos.quantil([1,null,5])'),3)
        # La sobremesa sin precuenta no se reemplaza por cero.
        row=next(r for r in self.P['b'] if r[0]=='0009')
        self.assertIsNone(row[self.P['cb'].index('sobremesa')])

    def test_transaccion_sin_pedido_conserva_su_periodo(self):
        p=self.p.iloc[:1].copy();t=self.t.iloc[:1].copy();t['dia']=pd.Timestamp('2025-09-07');t['ped']='FUERA'
        P=datos.armar(p,t,RANGO);a=self.calc(P=P)
        self.assertEqual(len(a['series']),2);self.assertEqual(sum(r['pl_anul'] for r in a['series']),1)
        a=self.calc({'mesa':'100'},P=P);self.assertEqual(a['total']['pl_anul'],0)

    def test_busqueda_periodo_y_ficha_sin_recargar(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=sub][data-v=Transferencias]').click()
        root.locator('[data-input=q]').fill('0001')
        self.assertTrue(pg.evaluate('__ventasControl.D.filas.every(r=>r.ped==="0001"||r.destino==="0001")'))
        root.locator('[data-input=q]').fill('')
        row=root.locator('[data-tabla=detalle] tbody tr').first;row.focus();pg.keyboard.press('Enter')
        expected=pg.evaluate('__ventasControl.D.elegido');self.assertIn(expected,root.locator('.ctl-ficha h3').inner_text())
        root.locator('[data-a=ped]').last.click();self.assertEqual(pg.evaluate('__pedidosPython.length'),0)
        root.locator('[data-tabla=periodos] tbody tr').first.click()
        self.assertIsNotNone(pg.evaluate('__ventasControl.s.foco'))
        self.assertNotIn('Transferencia elegida',root.locator('.ctl-ficha').inner_text())
        root.locator('[data-a=rango]').click();self.assertIsNone(pg.evaluate('__ventasControl.s.foco'))

    def test_foto_y_grupos_abren_los_pedidos_que_los_componen(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=sub][data-v=Ocupación]').click()
        root.locator('[data-a=foto][data-slot="27"]').first.click()
        self.assertEqual(pg.evaluate('__ventasControl.D.filas.map(r=>r.ped)'),['0000'])
        root.locator('[data-tabla=detalle] tbody tr').first.click()
        self.assertNotIn('Transferencia elegida',root.locator('.ctl-ficha').inner_text())
        root.locator('[data-a=sub][data-v=Tiempos]').click()
        root.locator('[data-tabla=detalle] tbody tr').first.click()
        grupo=pg.evaluate('__ventasControl.s.grupoLista')
        self.assertTrue(pg.evaluate('g=>__ventasControl.D.filas.every(r=>r.grupo===g)',grupo))
        self.assertGreater(pg.evaluate('__ventasControl.D.filas.length'),0)
        root.locator('[data-lentos]').check();self.assertTrue(pg.evaluate('__ventasControl.D.filas.every(r=>r.total>=__ventasControl.D.scope.p90)'))

    def test_cache_estado_y_datos_nuevos(self):
        root=self.mount();pg=self.pg
        pg.evaluate('window.__core=__ventasControl.cache.core')
        root.locator('[data-input=q]').fill('plato');self.assertTrue(pg.evaluate('__core===__ventasControl.cache.core'))
        pg.evaluate('()=>__montarControl({data:__ventasControl.P,parentElement:document.querySelector("#montar")})')
        self.assertEqual(root.locator('[data-input=q]').input_value(),'plato')
        root.locator('[data-select=mesa]').select_option('100')
        pg.evaluate('P=>{P.sello="nuevo";P.p=[];P.b=[];__montarControl({data:P,parentElement:document.querySelector("#montar")})}',self.P)
        self.assertEqual(pg.evaluate('__ventasControl.s.mesa'),'100');self.assertEqual(pg.evaluate('__ventasControl.D.total.pedidos'),0)

    def test_fuentes_parciales_y_pedido_fuera_del_rango(self):
        root=self.mount(datos.armar(None,self.t,RANGO));pg=self.pg
        self.assertIn('Sin registros',root.inner_text())
        root.locator('[data-a=sub][data-v=Ocupación]').click()
        self.assertEqual(root.locator('[data-a=foto]').count(),0)
        self.mount();pg.evaluate('()=>{__ventasControl.s.ped="NO CARGADO";__controlDatos.dibujar(__ventasControl)}')
        self.assertIn('no está entre los datos cargados',root.locator('.ctl-ficha').inner_text())

    def test_excel_numerico_y_contexto(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=sub][data-v=Tiempos]').click()
        with pg.expect_download() as down:root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'control.xlsx';down.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                sheets=[ET.fromstring(z.read(n)) for n in z.namelist() if n.startswith('xl/worksheets/')]
                self.assertTrue(any(t.findall('.//s:v',ns) for t in sheets))
                text=' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for word in ['Contexto','P90','Día del turno','Consumo','0000']:self.assertIn(word,text)
                self.assertFalse(any(t.findall('.//s:f',ns) for t in sheets))

    def test_alturas_movil_y_tablas_largas(self):
        P=json.loads(json.dumps(self.P));original=P['t'][0]
        for i in range(400):r=original.copy();r[3]=f'Extra {i}';P['t'].append(r)
        root=self.mount(P);pg=self.pg
        self.assertEqual(root.locator('[data-tabla=detalle] tbody tr').count(),150)
        sc=root.locator('[data-tabla=detalle]');sc.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}')
        self.assertGreater(root.locator('[data-tabla=detalle] tbody tr').count(),150)
        for selector in ['.ctl-main','.ctl-ficha']:
            self.assertEqual(pg.locator(selector).evaluate('e=>Math.round(e.getBoundingClientRect().height)'),575)
        pg.set_viewport_size({'width':390,'height':844})
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619})


if __name__=='__main__':unittest.main(verbosity=2)
