"""Comparativo como pieza propia: las cuentas JS contra el Python anterior.

Sin secrets ni red. Chromium contrasta cada ventana, el neto, los filtros,
el canje, la cuenta dividida, Rappi, la jerarquía que cambió, 2027 (53
semanas ISO en 2026) y el 29 de febrero. También recorre las cinco mejoras
y abre el Excel para verificar sus hojas y el contexto exportado.
"""
import datetime as dt
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from graficos import ventas_comparativo as vc
from graficos import ventas_comparativo_datos as datos

_AQUI = Path(__file__).parent
_JS = (_AQUI / "graficos/ventas_comparativo.js").read_text(encoding="utf-8")
_CSS = (_AQUI / "graficos/ventas_comparativo.css").read_text(encoding="utf-8")
_COLS = {"fecha": "fecha", "venta": "venta", "neto": "neto", "pax": "pax", "pedido": "pedido",
         "prod": "prod", "cant": "cant", "fam": "fam", "sub": "sub"}
_ANCLA = dt.date(2026, 10, 23)


def _ventas():
    rows = []

    def fila(f, doc, ped, prod, v, q, pax, grupo="Fondos", canal="Local", sub="Carta"):
        rows.append((f, doc, ped, prod, v, v / 1.18, q, pax, grupo, sub, canal))

    for f in pd.date_range("2025-01-01", "2026-10-23", freq="7D"):
        for j in range(20):
            prod = f"Plato {j:02d}"
            grupo = "Eventos" if j == 18 else "Venta Interna" if j == 19 else "Bebidas" if j % 3 == 0 else "Fondos"
            if j == 1 and f.year == 2025:
                grupo = "Antiguo"
            v = (j + 1) * (10.12719 if f.year == 2025 else 12.341978)
            fila(f, f"D{f:%Y%m%d}-{j}", f"P{f:%Y%m%d}-{j // 2}", prod, v, j + 1,
                 0 if j == 17 else 4, grupo, "Rappi" if j == 17 else "Local")
    # Canje completo: boleta + factura − nota = una venta y una mesa.
    fila("2026-10-20", "B1", "canje", "Canje", 118, 1, 2)
    fila("2026-10-21", "F1", "canje", "Canje", 118, 1, 2)
    fila("2026-10-21", "N1", "canje", "Canje", -118, -1, -2)
    # Cuenta dividida, además de dos grupos en el mismo comprobante.
    fila("2026-10-22", "B2", "dividida", "Lomo", 70, 1, 4)
    fila("2026-10-22", "B2", "dividida", "Pan", 5, 1, 4)
    fila("2026-10-22", "B2", "dividida", "Agua", 10, 2, 4, "Bebidas")
    fila("2026-10-23", "B3", "dividida", "Pato", 60, 1, 4)
    fila("2026-10-23", "N2", "devolucion", "Retirado", -30, -1, -1)
    # Producto desaparecido, y fechas donde fallaba la semana ISO.
    fila("2025-10-21", "OLD", "old", "Retirado", 200, 2, 3)
    for f in ["2026-05-10", "2027-05-09", "2027-02-28", "2027-03-01", "2028-02-28", "2028-02-29", "2028-03-01"]:
        fila(f, "D" + f, "P" + f, "Calendario", 101.123456, 3, 2)
    d = pd.DataFrame(rows, columns=["fecha", "LLAVE LOCAL DOCUMENTO", "pedido", "prod", "venta", "neto",
                                    "cant", "pax", "fam", "sub", "CANAL VENTA"])
    d["fecha"] = pd.to_datetime(d["fecha"])
    return d


def _armar(ancla=_ANCLA, inicio=dt.date(2025, 1, 1), d=None, cols=None):
    d = _ventas() if d is None else d
    diario = pd.DataFrame({"dia": pd.date_range("2025-01-01", "2028-03-01"), "servicio": "CENA",
                           "bruta": 5000.123456, "neta": 4000.123456})
    return datos.armar(d, cols or _COLS, ancla, inicio, "test", diario=diario, ppto_aplica=True)


def _ref_series(d, plan, lado, neto=False, excluir=False):
    if excluir:
        d = d[~d["fam"].isin(vc.GRUPOS_RAROS)]
    rangos = [(i, dt.date.fromisoformat(a), dt.date.fromisoformat(b))
              for i, (a, b) in enumerate(plan[lado])]

    def cargar(_a, _c, ini, fin, _cb):
        return d[d["fecha"].dt.date.between(ini, fin)]

    with patch.object(vc, "_cargar_tramo", side_effect=cargar):
        return vc._series_por_rangos("x", "fecha", "fecha", "neto" if neto else "venta", "pax", "pedido",
                                    rangos, None, en_total=plan["ok"], col_neto=None if neto else "neto", col_grupo="fam")


class Contrato(unittest.TestCase):
    def test_importes_y_posiciones(self):
        d = _ventas()
        P = _armar(d=d)
        json.dumps(P, allow_nan=False)
        self.assertAlmostEqual(sum(r[5] for r in P["docs"]), d["venta"].sum(), places=4)
        self.assertAlmostEqual(sum(r[6] for r in P["productos"]), d["neto"].sum(), places=4)
        self.assertLess(len(P["docs"]), len(d))
        self.assertIn('const CD = { dia: 0, ped: 1, doc: 2, canal: 3, grupo: 4, venta: 5, neto: 6, pos: 7, neg: 8 };', _JS)
        self.assertIn('const CP = { dia: 0, prod: 1, grupo: 2, sub: 3, canal: 4, venta: 5, neto: 6, cant: 7, n: 8 };', _JS)
        self.assertNotIn('setTriggerValue', _JS)
        self.assertNotRegex(_JS + _CSS, r"#[0-9a-fA-F]{6}\b")

    def test_el_sello_cambia_con_datos_y_contexto(self):
        d = _ventas()
        a = _armar(d=d)
        d.loc[0, "venta"] += .01
        self.assertNotEqual(a["sello"], _armar(d=d)["sello"])
        self.assertNotEqual(a["sello"], _armar(inicio=dt.date(2025, 2, 1))["sello"])

    def test_las_ventanas_no_pierden_el_ano_a_la_fecha(self):
        ini, fin = datos.limites(dt.date(2027, 12, 30))
        self.assertLessEqual(ini, dt.date(2026, 1, 1))
        self.assertEqual(fin, dt.date(2027, 12, 30))
        P = _armar(dt.date(2028, 2, 29))
        plan = P["planes"]["Día|7|calendario"]
        self.assertEqual(plan["ap"][-2:], [["2027-02-28", "2027-02-28"]] * 2)


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        return None


@unittest.skipIf(_chromium() is None, "sin Playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = _ventas()
        cls.P = _armar(d=cls.d)
        cls.pw = _chromium()().start()
        try:
            cls.b = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))
        cls.pg = cls.b.new_page(viewport={"width": 1323, "height": 619}, accept_downloads=True)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--border-lavender:rgb(190,180,235);--success:green;--danger:crimson;--warning:orange;--warning-text:brown;--serie-2:teal;--serie-5:orange;}body{margin:0}')
        cls.pg.add_style_tag(content=_CSS)
        xlsx = (_AQUI / "graficos/_xlsx.js").read_text(encoding="utf-8")
        cls.pg.add_script_tag(content=xlsx + _JS.replace('export default function(component)', 'window.__montarComparativo = function(component)'))

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.pw.stop()

    def calc(self, state=None, P=None):
        return self.pg.evaluate('''([P,s])=>{const B=__vcCalc.leer(P),st={...__vcUI.inicial(),...s};const V=__vcCalc.calcular(B,st);
          return {a:V.a,p:V.p,ta:V.ta,tp:V.tp,puente:V.puente,cal:V.cal,ppto:V.ppto,acum:V.acum,
            detalle:V.detalle,ra:V.ra,rp:V.rp};}''', [P or self.P, state or {}])

    def test_cada_grano_ventana_neto_y_exclusion(self):
        for clave, plan in self.P["planes"].items():
            gran, n, modo = clave.split('|')
            for neto in (False, True):
                for excluir in (False, True):
                    with self.subTest(clave=clave, neto=neto, excluir=excluir):
                        out = self.calc({"gran": gran, "ventana": int(n), "modo": modo, "neto": neto, "excluir": excluir})
                        refs = []
                        for lado, k in (("actual", "a"), ("ap", "p")):
                            v, pax, cli, total = _ref_series(self.d, plan, lado, neto, excluir)
                            refs.append(total)
                            for i, row in enumerate(out[k]):
                                self.assertAlmostEqual(row['venta'], v[i], places=4)
                                self.assertAlmostEqual(row['pax'], pax[i], places=6)
                                self.assertAlmostEqual(row['cli'], cli[i], places=4)
                            for col in ('venta', 'pax', 'cli', 'raro'):
                                self.assertAlmostEqual(out['t'+k][col], total[col], places=4)
                        pq = vc._por_que(*refs)
                        if pq:
                            for k, v in pq.items():
                                self.assertAlmostEqual(out['puente'][k], v, places=4)
                            self.assertAlmostEqual(sum(out['puente'][k] for k in ('clientes','ticket','sin_clientes')), out['puente']['d'], places=4)
                        for i, (ra, rp) in enumerate(zip(plan['actual'], plan['ap'])):
                            if plan['ok'][i]:
                                ref = vc._efecto_calendario(tuple(map(dt.date.fromisoformat,ra)),tuple(map(dt.date.fromisoformat,rp)),refs[1]['dias'])
                                if ref is not None:
                                    self.assertAlmostEqual(out['cal'][i], ref, places=4)
                        if excluir:
                            self.assertTrue(all(x is None for x in out['ppto']))

    def test_bisiesto_union_y_semanas_2027(self):
        for ancla, gran, n, modo in [(dt.date(2028,2,29),'Día',7,'calendario'), (dt.date(2027,5,9),'Semana',4,'semana')]:
            P = _armar(ancla)
            plan = P['planes'][f'{gran}|{n}|{modo}']
            out = self.calc({'gran':gran,'ventana':n,'modo':modo}, P)
            ref = _ref_series(self.d, plan, 'ap')[-1]
            self.assertAlmostEqual(out['tp']['venta'], ref['venta'], places=4)
            self.assertEqual(out['tp']['pax'], ref['pax'])

    def test_tramo_y_todos_los_productos_con_su_grupo_actual(self):
        st = {'gran':'Mes','ventana':12,'sel':[8,11]}
        out = self.calc(st)
        plan = self.P['planes']['Mes|12|semana']
        ra = plan['actual'][8:12]
        rp = plan['ap'][8:12]
        def carga(_a,_c,i,f,_cb):
            return self.d[self.d['fecha'].dt.date.between(i,f)]
        with patch.object(vc, '_cargar_tramo', side_effect=carga):
            ref, _ = vc._ranking_platos('x','fecha','fecha','venta','prod','cant',
                                        tuple(map(dt.date.fromisoformat,[ra[0][0],ra[-1][1]])),
                                        tuple(map(dt.date.fromisoformat,[rp[0][0],rp[-1][1]])),None,top=10000,col_fam='fam',col_sub='sub')
        js = {r['prod']:r for r in out['detalle']['rows']}
        self.assertEqual(set(js),set(ref['prod']))
        for r in ref.to_dict('records'):
            self.assertEqual(js[r['prod']]['fam'],r['fam'])
            for k in ('venta','venta_ap','d','cant','cant_ap','ef_cant','ef_precio'):
                self.assertAlmostEqual(js[r['prod']][k],r[k],places=4)
        grp = self.P['grupos'].index('Fondos')
        filtrado = self.calc({**st,'grupo':grp})['detalle']['rows']
        self.assertTrue(all(r['fam']=='Fondos' for r in filtrado))
        # El plato que cambió de grupo conserva la venta de su grupo viejo en AP.
        self.assertGreater(next(r for r in filtrado if r['prod']=='Plato 01')['venta_ap'],0)

    def test_historico_ausente_no_es_cero_y_sin_clientes(self):
        P = _armar(dt.date(2025,2,10))
        out = self.calc(P=P)
        self.assertEqual(out['ta']['venta'],0)
        self.assertEqual(out['tp']['venta'],0)
        self.pg.evaluate('''P=>{window.__vtComparativo=undefined;document.querySelector('#montar').innerHTML='';__montarComparativo({data:P,parentElement:document.querySelector('#montar')})}''',P)
        self.pg.locator('.vcc [data-bar]').last.click()
        self.assertIn('no se considera una venta de cero',self.pg.locator('.vcc').inner_text())
        cols={**_COLS,'pax':None,'pedido':None}
        P = _armar(cols=cols)
        out = self.calc(P=P)
        self.assertIsNone(out['ta']['pax'])
        self.assertIsNone(out['puente'])

    def test_ui_cinco_mejoras_y_excel(self):
        pg = self.pg
        pg.evaluate('''P=>{window.__vtComparativo=undefined;document.querySelector('#montar').innerHTML='';__montarComparativo({data:P,parentElement:document.querySelector('#montar')});}''',self.P)
        root = pg.locator('.vcc')
        root.locator('[data-acc="gran"][data-v="Mes"]').click()
        root.locator('[data-acc="ventana"][data-v="12"]').click()
        hits = root.locator('[data-bar]')
        a,b = hits.nth(8).bounding_box(),hits.nth(11).bounding_box()
        pg.mouse.move(a['x']+a['width']/2,a['y']+a['height']/2)
        pg.mouse.down()
        pg.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2,steps=10)
        pg.mouse.up()
        self.assertEqual(pg.evaluate('__vtComparativo.st.sel'),[8,11])
        self.assertEqual(root.locator('.vcc-bridge-plot svg').count(),1)
        self.assertGreater(root.locator('.vcc-detail [data-acc="grupo"]').count(),0)
        root.locator('.vcc-detail .vcc-break [data-acc="grupo"]').first.click()
        self.assertIsNotNone(pg.evaluate('__vtComparativo.st.grupo'))
        root.locator('.vcc-search [data-acc="grupo"]').click()
        root.locator('[data-acc="buscar"]').fill('Plato 01')
        self.assertEqual(pg.evaluate('__vtComparativo.rows.map(r=>r.prod)'),['Plato 01'])
        self.assertIn('1 producto · búsqueda aplicada',root.locator('.vcc-table-foot').inner_text())
        root.locator('[data-acc="excluir"]').check()
        self.assertTrue(pg.evaluate('__vtComparativo.st.excluir'))
        self.assertEqual(pg.evaluate('__vtComparativo.V.ta.raro'),0)
        with pg.expect_download() as dl:
            root.locator('.vcc-detail [data-acc="excel"]').click()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'comparativo.xlsx'
            dl.value.save_as(str(path))
            with zipfile.ZipFile(path) as z:
                self.assertIn('Productos',z.read('xl/workbook.xml').decode())
                self.assertIn('Plato 01',z.read('xl/worksheets/sheet2.xml').decode())
                self.assertIn('Excluir Eventos',z.read('xl/worksheets/sheet3.xml').decode())
        # Remontar la misma pieza conserva lo elegido; otro sello limpia el tramo.
        pg.evaluate('''P=>{document.querySelector('#montar').innerHTML='';__montarComparativo({data:P,parentElement:document.querySelector('#montar')});}''',self.P)
        self.assertEqual(pg.evaluate('__vtComparativo.st.sel'),[8,11])
        pg.evaluate('''P=>__montarComparativo({data:{...P,sello:'otra'},parentElement:document.querySelector('#montar')})''',self.P)
        self.assertIsNone(pg.evaluate('__vtComparativo.st.sel'))


if __name__ == '__main__':
    unittest.main()
