"""Órdenes de producción nativas: mismas cuentas y pendientes separados (#727)."""
import datetime as dt
import json
import tempfile
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from graficos import movimientos_periodo as mp
from graficos import movimientos_periodo_datos as datos
import test_movimientos_periodo_pieza as comun

ROOT=Path(__file__).parent
COLS=dict(fecha='F',doc='D',area='A',estado='E',fam='FM',prod='P',cant='Q',val='V',tipo='T',unid='U')
RANGO=(pd.Timestamp('2025-01-01'),pd.Timestamp('2025-03-16'))


def muestra():
    filas=[
        ('OP-01','2025-01-02 09:00','Cocina','PROCESADO','Salsa',2.123456789,21.23456789,'KILOS','Ana'),
        ('OP-01','2025-01-02 09:00','Cocina','PROCESADO','Postre',3,30,'UNIDAD','Ana'),
        ('OP-02','2025-01-07 10:00','Pastelería','GENERADO','Pendiente',100,9999.123456789,'KILOS','María'),
        ('OP-03','2025-01-10 08:00','Cocina','ANULADO','Salsa',40,400,'KILOS','Ana'),
        ('OP-04','2025-02-01 08:00','Cocina','PROCESADO','',None,5000,'','Ana'),
        ('OP-05','2025-02-02 08:00','Pastelería','GENERADO','',None,300,'','María'),
        ('OP-06','2025-02-03 08:00','Barra','PROCESADO','Sin cantidad',0,4.123456789,'UNIDAD','Luis'),
        ('OP-07','2025-03-03 08:00','Cocina','PROCESADO','Ajuste',-1.123456789,-3.123456789,'KILOS','Ana'),
        ('OP-08','2025-03-12 08:00','Cocina','PROCESADO','Salsa',4,44.123456789,'KILOS','Ana'),
    ]
    d=pd.DataFrame(filas,columns=['D','F','A','E','P','Q','V','U','T']);d['F']=pd.to_datetime(d.F);d['FM']='Preparados'
    return d


def payload(d=None):
    return datos.armar(muestra() if d is None else d,mp.PRODUCCION,COLS,rango=RANGO,hoy=dt.date(2025,4,1))


class Contrato(unittest.TestCase):
    def test_estado_importes_y_sello(self):
        P=payload();json.dumps(P,allow_nan=False)
        self.assertTrue(P['produccion']);self.assertFalse(P['suma_sin_procesar']);self.assertEqual(P['rotulo_tipo'],'Usuario')
        self.assertEqual(len(P['filas']),len(muestra()));self.assertEqual(P['sello'],payload()['sello'])
        d=muestra();d.loc[0,'V']+=.000000001;self.assertNotEqual(P['sello'],payload(d)['sello'])

    def test_requerimientos_con_generados_conservan_su_regla(self):
        d=muestra();p=datos.armar(d,mp.REQUERIMIENTOS,COLS,rango=RANGO)
        self.assertTrue(p['suma_sin_procesar']);self.assertFalse(p['produccion'])
        self.assertGreater(float(mp._validas(mp.lineas_documentos(d,**COLS),mp.REQUERIMIENTOS).valor.sum()),float(mp._validas(mp.lineas_documentos(d,**COLS),mp.PRODUCCION).valor.sum()))


class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if comun.sync_playwright is None:raise unittest.SkipTest('sin Playwright')
        comun.Navegador.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):comun.Navegador.tearDownClass.__func__(cls)

    def calc(self,s=None,P=None):return self.pg.evaluate('([P,s])=>__movPeriodoDatos.calcular(P,__movPeriodoDatos.estado(s))',[P or payload(),s or {}])

    def mount(self,P=None):
        self.pg.evaluate('P=>{const old=window.__movPeriodo;old?.abort.abort();old?.ro?.disconnect();window.__movPeriodoEstados={};window.__requests=[];document.querySelector("#montar").replaceChildren();__montarMov({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__requests.push(v)})}',P or payload())
        return self.pg.locator('.mv')

    def test_cada_grano_y_filtros_contra_calculos_originales(self):
        b=mp.lineas_documentos(muestra(),**COLS)
        for gran in datos.GRANOS:
            for filtro in [{},{'area':['Cocina']},{'tipo':['Ana']},{'prod':['Salsa']},{'area':['Pastelería']}]:
                ref=b.copy()
                for k,v in filtro.items():ref=ref[ref[k].isin(v)]
                ref['clave']=mp._periodo_serie(ref.fecha,gran);r=mp.resumen_por_periodo(ref,mp.PRODUCCION)
                a=self.calc({'gran':gran,**filtro});self.assertAlmostEqual(a['total'],float(r.valor.sum()),places=7)
                self.assertEqual([s['clave'] for s in a['series']],list(r.index))
                for s,(_,rr) in zip(a['series'],r.iterrows()):
                    for key in ['valor','cant','docs','areas','lineas']:self.assertAlmostEqual(s[key],float(rr[key]),places=7)

    def test_pendientes_anuladas_vacias_no_entran_en_producido(self):
        a=self.calc();self.assertEqual(len(a['pendientes']),2);self.assertEqual(len(a['anuladas']),1);self.assertEqual(len(a['vacias']),1)
        self.assertEqual(a['nDocs'],4);self.assertEqual(a['noSuman'],4)
        docs={r['doc']:r for r in a['todosDocs']}
        for key in ['OP-02','OP-03','OP-04','OP-05']:self.assertFalse(docs[key]['suma'])
        self.assertEqual(docs['OP-02']['rotulo'],'Sin procesar');self.assertAlmostEqual(docs['OP-02']['registrado'],9999.123456789)
        self.assertAlmostEqual(sum(d['valor'] for d in a['pendientes']),10299.123456789)

    def test_montaje_refuerza_regla_con_mensaje_de_version_anterior(self):
        from graficos import movimientos_periodo_pieza as pieza
        antiguo=payload()
        for k in ['produccion','suma_sin_procesar','rotulo_tipo']:antiguo.pop(k)
        fake=SimpleNamespace(session_state={},markdown=Mock(),container=lambda **kw:nullcontext())
        with patch.object(pieza,'st',fake),patch.object(pieza.datos,'armar',return_value=antiguo),patch.object(pieza,'_PIEZA') as comp:
            pieza.renderizar(muestra(),mp.PRODUCCION,COLS,rango=RANGO)
        wire=comp.call_args.kwargs['data'];self.assertTrue(wire['produccion']);self.assertFalse(wire['suma_sin_procesar'])
        a=self.calc(P=wire);ref=mp._validas(mp.lineas_documentos(muestra(),**COLS),mp.PRODUCCION)
        self.assertAlmostEqual(a['total'],float(ref.valor.sum()),places=7)

    def test_area_solo_con_pendientes_sigue_accesible(self):
        a=self.calc();self.assertIn('Pastelería',a['ops']['area'])
        a=self.calc({'area':['Pastelería'],'modo':'Detalle','estadoDoc':'Sin procesar'})
        self.assertEqual(a['total'],0);self.assertEqual(a['series'],[]);self.assertEqual(len(a['docs']),2)
        self.mount(payload(muestra().query('E == "GENERADO"')));self.assertEqual(self.pg.evaluate('__movPeriodo.D.total'),0)

    def test_productos_unidades_y_valor_ponderado(self):
        a=self.calc();rs={r['prod']:r for r in a['productos']}
        self.assertNotIn('Pendiente',rs);self.assertEqual(rs['Salsa']['unid'],'KILOS')
        d=muestra().query('P == "Salsa" and E == "PROCESADO"')
        self.assertAlmostEqual(rs['Salsa']['medio'],float(d.V.sum()/d.Q.sum()),places=7)
        self.assertIsNone(rs['Sin cantidad']['medio']);self.assertEqual(rs['Ajuste']['cant'],-1.123456789)

    def test_kpi_abre_pendientes_y_filtros_no_cambian_total(self):
        root=self.mount();total=self.pg.evaluate('__movPeriodo.D.total')
        root.locator('[data-a=estadoDoc][data-v="Sin procesar"]').click()
        self.assertEqual(self.pg.evaluate('__movPeriodo.D.docs.map(r=>r.doc)'),['OP-02','OP-05'])
        self.assertEqual(root.locator('[data-select=estadoDoc]').input_value(),'Sin procesar')
        root.locator('[data-input=q]').fill('OP-05');self.assertEqual(self.pg.evaluate('__movPeriodo.D.docs.length'),1)
        self.assertEqual(self.pg.evaluate('__movPeriodo.D.total'),total);self.assertEqual(self.pg.evaluate('__requests.length'),0)
        self.assertIn('Usuario',root.inner_text())
        self.assertIn('Por usuario',root.inner_text())

    def test_seleccion_tramo_y_documento_completo(self):
        a=self.calc({'gran':'Mes','tramo':['2025-01','2025-01'],'modo':'Detalle','estadoDoc':'Sin procesar'})
        self.assertEqual([d['doc'] for d in a['docs']],['OP-02']);self.assertTrue(a['acotado'])
        a=self.calc({'area':['Cocina'],'prod':['Salsa'],'modo':'Detalle','doc':'OP-01','completo':True})
        self.assertEqual(len(a['lineas']),2)

    def test_excel_preciso_y_contexto_de_pendientes(self):
        root=self.mount();root.locator('[data-a=estadoDoc][data-v="Sin procesar"]').click()
        with self.pg.expect_download() as d:root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'prod.xlsx';d.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                text=' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for palabra in ['Contexto','Valor registrado','no producido','<v>9999.123457</v>']:self.assertIn(palabra,text)
                self.assertNotIn('<f>',text)

    def test_remontaje_y_movil(self):
        root=self.mount();root.locator('[data-a=estadoDoc][data-v=Anuladas]').click()
        self.pg.evaluate('()=>__montarMov({data:__movPeriodo.P,parentElement:document.querySelector("#montar")})')
        self.assertEqual(self.pg.evaluate('__movPeriodo.s.estadoDoc'),'Anuladas')
        self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),390)
        self.pg.set_viewport_size({'width':1323,'height':619})


if __name__=='__main__':unittest.main(verbosity=2)
