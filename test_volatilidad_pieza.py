"""Volatilidad como pieza propia (#718): cuentas originales y recorrido UI.

Sin red ni credenciales. Cierres, puntaje, dispersión y sobrecosto contra
Python, ventanas y fechas con hora, compras duplicadas en un día, moneda,
unidades, base ausente y el puente exacto precio/cantidad. Chromium prueba
arrastre, búsqueda, proveedores, exportación y remontaje de la pieza.
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from graficos.compras import volatilidad as vol
from graficos.compras import volatilidad_datos as datos

ROOT = Path(__file__).parent
JS = (ROOT / 'graficos/compras/volatilidad.js').read_text(encoding='utf-8')
CSS = (ROOT / 'graficos/compras/volatilidad.css').read_text(encoding='utf-8')
COLS = {k: k for k in ('fecha', 'prod', 'prov', 'precio', 'cant', 'valor', 'um', 'doc', 'moneda')}


def compras():
    rows = []
    for i, f in enumerate(pd.date_range('2025-09-01', '2026-10-19', freq='7D')):
        for j in range(7):
            p = (j + 2) * (1 + (i % 5) * .07)
            for k in range(2):
                q = 15 + j + i % 3
                precio = p * (1 + k * .03)
                rows.append((f + pd.Timedelta(hours=10+k), f'Insumo {j}', f'PROVEEDOR {k}', precio,
                             q, precio*q+.000001, 'KG', f'F0001-{i}-{j}-{k}', '01'))
        if i % 11 == 0:
            rows.append((f, 'Esporádico', 'PROVEEDOR 0', 1, 1, 1, 'KG', f'E-{i}', '1'))
    # Tres compras a distinta hora y precio el mismo día, con orden estable.
    rows.extend([
        (pd.Timestamp('2026-10-19 16:00'), 'Insumo 0', 'PROVEEDOR 1', 12.345678, 2.123456, 26.234567, 'KG', 'A', '1'),
        (pd.Timestamp('2026-10-19 16:00'), 'Insumo 0', 'PROVEEDOR 0', 8.987654, 3.123456, 28.123456, 'KG', 'B', '01'),
        (pd.Timestamp('2026-10-19 20:00'), 'Insumo 0', 'PROVEEDOR 0', 99999, 5, 499995, 'KG', 'USD', '02'),
    ])
    return pd.DataFrame(rows, columns=['fecha', 'prod', 'prov', 'precio', 'cant', 'valor', 'um', 'doc', 'moneda'])


def armar(d=None, rango=None):
    d = compras() if d is None else d
    rango = rango or (pd.Timestamp('2026-08-01'), pd.Timestamp('2026-10-19'))
    return datos.armar(d, d, COLS, rango)


def ref(d, rango):
    dd = datos.normalizar(d, COLS)
    dd = dd[dd['fecha'].dt.normalize().between(*map(pd.Timestamp, rango))].copy()
    dd['_semana'] = (dd['fecha'] - pd.to_timedelta(dd['fecha'].dt.weekday, unit='D')).dt.normalize()
    sems = vol._vol_semanas_ventana(dd['fecha'], maximo=None)
    if not sems:
        return dd, [], {}, {}, {}
    rec = dd[dd['_semana'].isin(sems[-5:])]
    cand = vol._vol_candidatos(rec, 'prod', 'precio', 'fecha', 'valor', sems[-5:])
    cs = vol._vol_cierres_semanales(dd, dd['prod'].unique(), 'prod', 'precio', 'fecha', sems)
    disp = {p: vol._vol_dispersion(g['precio'].tolist()) for p, g in rec.groupby('prod')}
    return dd, sems, cand, cs, disp


class Contrato(unittest.TestCase):
    def test_lineas_precision_moneda_sello_y_fecha_con_hora(self):
        d = compras()
        P = armar(d)
        json.dumps(P, allow_nan=False)
        self.assertEqual(len(P['lineas']), len(d)-1)
        self.assertNotIn('USD', P['docs'])
        self.assertAlmostEqual(sum(r[8] for r in P['lineas']), d[d.moneda!='02']['valor'].sum(), places=4)
        self.assertEqual(len({r[1] for r in P['lineas']}), 4)
        self.assertIn('const VL = { dia:0, hora:1, prod:2, prov:3, doc:4, um:5, precio:6, cant:7, valor:8 };', JS)
        self.assertNotIn('setTriggerValue', JS)
        self.assertNotRegex(JS + CSS, r'#[0-9a-fA-F]{6}\b')
        d.loc[0, 'precio'] += .01
        self.assertNotEqual(P['sello'], armar(d)['sello'])
        self.assertNotEqual(P['sello'], armar(rango=(pd.Timestamp('2026-09-01'), pd.Timestamp('2026-10-19')))['sello'])

    def test_puente_de_referencia_cierra_y_no_inventa_base(self):
        a = [{'precio':12, 'cant':30}, {'precio':10, 'cant':0}, {'precio':None, 'cant':5}]
        p = [{'precio':10, 'cant':20}]
        v = datos.cambio_gasto(a,p)
        self.assertEqual((v['precio'],v['cantidad'],v['delta']),(60,100,160))
        self.assertIsNone(datos.cambio_gasto(a,[])['precio'])


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, 'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        try:
            cls.browser=cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))
        cls.pg=cls.browser.new_page(viewport={'width':1323,'height':619},accept_downloads=True)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--border-lavender:rgb(190,180,235);--success:green;--danger:crimson;--serie-0:teal;--serie-1:orange;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarVol=function(component)'))
        cls.d=compras()
        cls.P=armar(cls.d)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def calc(self, s=None, P=None):
        return self.pg.evaluate('''([P,s])=>{const B=__cvCalc.leer(P),st={...__cvUI.inicial(),...s},R=__cvCalc.ranking(B,st);
          if(st.prod==null)st.prod=R.visibles[0]?.id;return {R,D:R.sems.length>=4?__cvCalc.detalle(B,R,st):null}}''',[P or self.P,s or {}])

    def mount(self, P=None):
        self.pg.evaluate('''P=>{window.__cpVol=undefined;document.querySelector('#montar').innerHTML='';__montarVol({data:P,parentElement:document.querySelector('#montar')})}''',P or self.P)

    def test_todas_las_ventanas_contra_cuentas_originales(self):
        for op,rango in self.P['planes'].items():
            with self.subTest(op=op):
                dd,sems,cand,cs,disp=ref(self.d,rango)
                R=self.calc({'op':op})['R']
                self.assertEqual(len(R['sems']),len(sems))
                self.assertEqual({self.P['prods'][r['id']] for r in R['rank'] if r['candidato']},set(cand))
                for r in R['rank']:
                    nom=r['nombre']
                    for a,b in zip(r['cierres'],cs[nom]):
                        if b is None:
                            self.assertIsNone(a)
                        else:
                            self.assertAlmostEqual(a,b,places=6)
                    self.assertAlmostEqual(r['volatilidad'],vol._vol_score(cs[nom][-5:]),places=1)
                    if disp[nom] is not None:
                        self.assertAlmostEqual(r['dispersion'],disp[nom],places=6)
                D=self.calc({'op':op})['D']
                rs=[{'precio':r['p'],'cant':r['q']} for r in D['scope']]
                sob=vol._vol_sobrecosto(rs)
                self.assertAlmostEqual(D['sobre']['sobre'],sob[0],places=5)
                self.assertAlmostEqual(D['sobre']['gasto'],sob[1],places=5)

    def test_ohlc_y_cierre_previo_sin_perder_compras_del_mismo_dia(self):
        out=self.calc({'prod':self.P['prods'].index('Insumo 0')})
        D=out['D']
        self.assertEqual(D['rows'][-1]['p'],8.987654)
        self.assertEqual(len([r for r in D['rows'] if r['f']==D['rows'][-1]['f']]),4)
        dd=datos.normalizar(self.d,COLS)
        dd['_semana']=(dd.fecha-pd.to_timedelta(dd.fecha.dt.weekday,unit='D')).dt.normalize()
        dd=dd[dd.fecha.dt.normalize().between(*map(pd.Timestamp,self.P['planes']['12m']))]
        sems=[pd.Timestamp('1970-01-01')+pd.Timedelta(days=s) for s in out['R']['sems']]
        semanas=vol._vol_detalle_producto(dd,'Insumo 0','prod','precio','fecha','prov','cant',sems,col_docu='doc')
        for a,b in zip(D['weeks'],semanas):
            for k in ('o','c','h','l'):
                self.assertAlmostEqual(a[k],b[k],places=6)

    def test_unidades_cantidades_invalidas_y_puente(self):
        d=compras()
        extras=pd.DataFrame([
            [pd.Timestamp('2026-10-19'),'Insumo 0','PROVEEDOR 0',999,5,4995,'UND','U','01'],
            [pd.Timestamp('2026-10-19'),'Insumo 0','PROVEEDOR 0',None,5,30,'KG','X','01'],
            [pd.Timestamp('2026-10-19'),'Insumo 0','PROVEEDOR 0',10,-3,-30,'KG','N','01'],
        ],columns=d.columns)
        P=armar(pd.concat([d,extras],ignore_index=True))
        state={'prod':P['prods'].index('Insumo 0'),'modo':'Tramo'}
        D=self.calc(state,P)['D']
        self.assertGreater(D['total']['omitidas'],0)
        self.assertTrue(all(r['u']==P['ums'].index('KG') for r in D['scope']))
        a=[{'precio':r['p'],'cant':r['q']} for r in D['scope']]
        previo=[r for r in D['hist'] if D['ip']<=r['f']<=D['fp']]
        p=[{'precio':r['p'],'cant':r['q']} for r in previo]
        esperado=datos.cambio_gasto(a,p)
        for k in ('precio','cantidad','delta'):
            self.assertAlmostEqual(D['puente'][k],esperado[k],places=6)
        self.assertAlmostEqual(D['puente']['precio']+D['puente']['cantidad'],D['puente']['delta'],places=6)
        U=self.calc({**state,'u':P['ums'].index('UND')},P)['D']
        self.assertEqual(U['total']['precio'],999)
        self.assertIsNone(U['puente']['precio'])

    def test_busqueda_fuera_del_ranking_y_base_incompleta(self):
        out=self.calc({'q':'esporádico'})
        self.assertEqual([r['nombre'] for r in out['R']['visibles']],['Esporádico'])
        self.assertFalse(out['R']['visibles'][0]['candidato'])
        d=self.d[self.d.fecha>='2026-09-21']
        P=armar(d)
        D=self.calc(P=P)['D']
        self.assertFalse(D['puente']['completo'])
        self.assertIsNone(D['puente']['precio'])

    def test_columnas_opcionales_ausentes_y_rango_corto(self):
        cols={**COLS,'cant':None,'um':None,'prov':None,'doc':None}
        P=datos.armar(self.d,self.d,cols)
        self.assertFalse(P['hay_cant'])
        D=self.calc(P=P)['D']
        self.assertIsNone(D['total']['precio'])
        self.assertIsNone(D['puente']['precio'])
        self.assertEqual(D['total']['cant'],0)
        corto=self.d[self.d.fecha>='2026-10-12']
        P=armar(corto)
        self.mount(P)
        self.assertIn('al menos cuatro semanas',self.pg.locator('.cvol').inner_text())
        self.assertEqual(self.pg.locator('.cv-lower').count(),0)

    def test_ui_arrastre_proveedores_impacto_excel_y_remontaje(self):
        self.mount()
        pg=self.pg;root=pg.locator('.cvol')
        root.locator('.cv-detail').scroll_into_view_if_needed()
        hs=root.locator('[data-hit]');a,b=hs.first.bounding_box(),hs.last.bounding_box()
        pg.mouse.move(a['x']+a['width']/2,a['y']+a['height']/2);pg.mouse.down()
        pg.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2,steps=8);pg.mouse.up()
        self.assertIsNotNone(pg.evaluate('__cpVol.st.sel'))
        self.assertEqual(pg.evaluate('__cpVol.st.modo'),'Tramo')
        root.locator('[data-acc="tab"][data-v="Proveedores"]').click()
        root.locator('tr[data-acc="prov"]').first.click()
        self.assertIsNotNone(pg.evaluate('__cpVol.st.prov'))
        root.locator('[data-acc="tab"][data-v="Cambio del gasto"]').click()
        self.assertEqual(root.locator('.cv-bridge-plot svg').count(),1)
        root.locator('[data-acc="orden"]').select_option('impacto')
        self.assertTrue(pg.evaluate('__cpVol.st.verImpacto'))
        with pg.expect_download() as dl:
            root.locator('.cv-analysis [data-acc="excel"]').click()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'volatilidad.xlsx';dl.value.save_as(str(path))
            with zipfile.ZipFile(path) as z:
                self.assertIn('Cambio gasto',z.read('xl/workbook.xml').decode())
                ctx=z.read('xl/worksheets/sheet3.xml').decode()
                self.assertIn('Tramo anterior',ctx)
                self.assertIn('Proveedor',ctx)
        sel=pg.evaluate('__cpVol.st.sel')
        pg.evaluate('P=>__montarVol({data:P,parentElement:document.querySelector("#montar")})',self.P)
        self.assertEqual(pg.evaluate('__cpVol.st.sel'),sel)
        root.locator('[data-acc="q"]').fill('Esporádico')
        self.assertEqual(root.locator('.cv-ranking-scroll tbody tr').count(),1)
        self.assertIn('Fuera del ranking',root.inner_text())
        pg.set_viewport_size({'width':390,'height':844})
        pg.wait_for_function('document.documentElement.scrollWidth<=390')
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619})
        pg.evaluate('P=>__montarVol({data:{...P,sello:"nuevo",planes:{...P.planes,Rango:["2026-09-01","2026-10-19"]}},parentElement:document.querySelector("#montar")})',self.P)
        self.assertEqual(pg.evaluate('__cpVol.st.op'),'Rango')
        self.assertIsNone(pg.evaluate('__cpVol.st.sel'))

    def test_otro_filtro_conserva_el_nombre_del_insumo_no_su_posicion(self):
        self.mount()
        self.pg.locator('.cvol tr[data-acc="prod"]').filter(has_text='Insumo 4').click()
        filtrado=self.d[self.d['prod'].isin(['Insumo 2','Insumo 4','Insumo 5'])]
        P=armar(filtrado)
        self.pg.evaluate('P=>__montarVol({data:P,parentElement:document.querySelector("#montar")})',P)
        self.assertEqual(self.pg.evaluate('__cpVol.B.P.prods[__cpVol.st.prod]'),'Insumo 4')


if __name__=='__main__':
    unittest.main()
