"""Vs año pasado como pieza propia: parejas contra cualquier «Contra», precio
repartido parejo, dejados y nuevos, venta y la pantalla: indicadores que suman la
diferencia, Gráfico | Productos, ficha, familias de la página (#725, #749, #771)."""
import datetime
import inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from graficos.compras import vs_ano_datos as datos
from graficos.compras import vs_ano_pasado as vp

ROOT = Path(__file__).parent
JS = (ROOT / 'graficos/compras/vs_ano.js').read_text(encoding='utf-8')
CSS = (ROOT / 'graficos/compras/vs_ano.css').read_text(encoding='utf-8')
COLS = dict(prod='P', fecha='F', valor='V', cant='Q', fam='FM', sub='SUB', um='UM')


def muestra():
    rows = []
    for year in [2023, 2024, 2025]:
        for month in range(1, 13 if year < 2025 else 4):
            for p, fam, sub, um in [('Harina', 'Alimentos', 'Secos', 'KILOS'), ('Bebida', 'Bebidas', 'Frías', 'UNIDAD')]:
                if p == 'Bebida' and year == 2025 and month == 3:
                    continue
                for day in [10, 20]:
                    rows.append(dict(P=p, F=pd.Timestamp(year, month, day), Q=2.123456789 * (1 + (year - 2023) * .1),
                                     V=(year - 2020 + month) * 3.123456789, FM=fam, SUB=sub, UM=um, VALOR_ANO_ANTERIOR=99999999))
    for p, year, q, v in [('Sólo anterior', 2024, 3, 33.123456789), ('Sólo actual', 2025, 1, 11.123456789), ('Sin cantidad', 2024, 1, 4), ('Sin cantidad', 2025, 0, 5)]:
        rows.append(dict(P=p, F=pd.Timestamp(year, 3, 20), Q=q, V=v, FM='Alimentos', SUB='Secos', UM='KILOS', VALOR_ANO_ANTERIOR=99999999))
    rows.append(dict(P='Harina', F=pd.Timestamp('2024-03-25'), Q=100, V=9999, FM='Alimentos', SUB='Secos', UM='KILOS', VALOR_ANO_ANTERIOR=99999999))
    rows.append(dict(P='Harina', F=pd.Timestamp('2025-02-15'), Q=-.123456789, V=-1.123456789, FM='Alimentos', SUB='Secos', UM='KILOS', VALOR_ANO_ANTERIOR=99999999))
    return pd.DataFrame(rows)


def payload(rango=None, venta=None, **extra):
    h = muestra()
    P = datos.armar(h, COLS)
    if rango:
        P['rango'] = rango
    if venta is not None:
        P['venta'] = venta
    P.update(extra)
    return P, h


def pares(h, k):
    """Las parejas como `vs_ano_pasado._con_ano_pasado`, con k meses en vez de 12."""
    parcial = vp._mes_parcial(h.F)
    g0 = vp._mensual(h, 'P', 'F', 'V', 'Q')
    gh = g0 if parcial is None else vp._mensual(h, 'P', 'F', 'V', 'Q', recorte=(parcial[0] - k, parcial[1]))
    if k == 12:
        return vp._con_ano_pasado(g0, gh)
    prev = gh[['prod', 'mes', 'valor', 'cant']].copy()
    prev['mes'] = prev['mes'] + k
    prev = prev.rename(columns={'valor': 'valor_aa', 'cant': 'cant_aa'})
    g = g0.merge(prev, on=['prod', 'mes'], how='outer')
    for c in ('valor', 'cant', 'valor_aa', 'cant_aa'):
        g[c] = pd.to_numeric(g[c], errors='coerce').fillna(0.0)
    return g[(g.mes >= gh.mes.min() + k) & (g.mes <= g0.mes.max())]


def referencia(h, k, meses, fam=None):
    g = pares(h, k)
    g = g[g.mes.astype(str).isin(meses)]
    if fam:
        mp = h.drop_duplicates('P').set_index('P').FM
        g = g[g['prod'].map(mp) == fam]
    p = g.groupby('prod', as_index=False)[['valor', 'cant', 'valor_aa', 'cant_aa']].sum()
    ambos = (p.cant > 0) & (p.cant_aa > 0)
    p['ep'] = 0.0
    p.loc[ambos, 'ep'] = .5 * (p.cant + p.cant_aa) * (p.valor / p.cant - p.valor_aa / p.cant_aa)
    return g, p.set_index('prod')


class Contrato(unittest.TestCase):
    def test_filas_calendario_y_sello(self):
        P, h = payload()
        json.dumps(P, allow_nan=False)
        self.assertEqual(P['parcial'], ['2025-03', 20])
        self.assertEqual((P['primero'], P['techo'], P['ultimo_dia']), ('2023-01', '2025-03', '2025-03-20'))
        ids = {n: i for i, n in enumerate(P['productos'])}
        filas = {(P['productos'][r[0]], r[1]): r for r in P['filas']}
        # Marzo 2024 tuvo una compra el 25: viaja también lo comprado hasta el 20, sin ella.
        r = filas[('Harina', '2024-03')]
        self.assertEqual(len(r), 6)
        self.assertGreater(r[2], 9999)
        self.assertLess(r[4], 1000)
        self.assertEqual(len(filas[('Harina', '2024-02')]), 4)
        self.assertEqual(datos.sellar(P), datos.sellar(dict(P, inicial={'fam': 'x'})))
        h.loc[0, 'V'] += .000000001
        self.assertNotEqual(datos.sellar(P), datos.sellar(datos.armar(h, COLS)))
        self.assertEqual(set(P['mapas']['Familia'].values()), {'Alimentos', 'Bebidas'})
        self.assertEqual(P['mapas']['Familia'][str(ids['Bebida'])], 'Bebidas')
        self.assertNotRegex(JS + CSS, r'#[0-9a-fA-F]{6}\b')
        self.assertNotIn(':has(', CSS)

    def test_un_calendario_y_sin_columnas_repetidas(self):
        P, h = payload()
        self.assertNotIn('planes', P)
        h = h.copy()
        h['VALOR_ANO_ANTERIOR'] = 0
        self.assertEqual(datos.sellar(P), datos.sellar(datos.armar(h, COLS)))
        self.assertEqual(len(inspect.signature(vp._compras_vs_ano_pasado_drill).parameters), 11)

    def test_sin_historia_y_columnas_opcionales(self):
        h = muestra()
        P = datos.armar(h.iloc[:0], COLS)
        self.assertEqual((P['filas'], P['primero'], P['parcial']), ([], None, None))
        P = datos.armar(h, {**COLS, 'fam': None, 'sub': None, 'um': None})
        self.assertEqual((P['familias'], P['mapas'], P['unidades']), ([], {}, {}))

    def test_rango_y_venta(self):
        self.assertEqual(datos.meses_de_rango((datetime.date(2026, 8, 1), datetime.date(2026, 10, 26))), ['2026-08', '2026-10'])
        self.assertIsNone(datos.meses_de_rango(None))
        self.assertEqual(datos.venta_por_mes({'2026-09': {'venta': 10.5}, '2026-10': {'venta': None}}), {'2026-09': 10.5})
        self.assertEqual(datos.venta_por_mes(None), {})


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, 'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P, cls.h = payload()
        cls.pw = sync_playwright().start()
        try:
            cls.br = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))
        cls.pg = cls.br.new_page(viewport={'width': 1323, 'height': 619}, accept_downloads=True)
        cls.pg.set_default_timeout(8000)
        cls.errores = []
        cls.pg.on('pageerror', lambda e: cls.errores.append(str(e)))
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--danger:crimson;--success:green;--danger-text:darkred;--success-text:darkgreen;--warning:orange;--warning-text:chocolate;--border-lavender:rgb(212,205,247);--bg-hover:rgb(247,246,251)}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT / 'graficos/_xlsx.js').read_text(encoding='utf-8') + JS.replace('export default function(component)', 'window.__montarVap=function(component)'))

    @classmethod
    def tearDownClass(cls):
        cls.br.close()
        cls.pw.stop()

    def tearDown(self):
        self.assertEqual(self.errores, [])

    def calc(self, s=None, P=None):
        return self.pg.evaluate('([P,s])=>{const D=__vapDatos.calcular(P,__vapDatos.inicial(s));delete D.plan;return D}', [P or self.P, s or {}])

    def mount(self, P=None):
        self.pg.evaluate('P=>{window.__comprasAno?.abort.abort();window.__comprasAno?.ro?.disconnect();window.__comprasAno=undefined;window.__requests=[];__montarVap({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__requests.push(v)})}', P or self.P)
        return self.pg.locator('.vap')

    def test_parejas_contra_python_en_cada_contra_familia_y_ventana(self):
        for rango in [['2025-01', '2025-03'], ['2024-04', '2025-03'], ['2023-01', '2025-03'], ['2024-06', '2024-09']]:
            P = dict(self.P, rango=rango)
            for contra in ['aa', 'aa2', 'ant', 'm:2023-05']:
                for fam in [datos.TODAS, 'Alimentos', 'Bebidas']:
                    a = self.calc(dict(contra=contra, fam=fam), P)
                    k = a['V']['k']
                    if contra == 'aa':
                        self.assertEqual(k, 12)
                    g, ref = referencia(self.h, k, a['V']['meses'], None if fam == datos.TODAS else fam)
                    self.assertEqual(len(a['g']), len(g), (rango, contra, fam))
                    got = {r['item']: r for r in self.pg.evaluate('([P,s])=>{const D=__vapDatos.calcular(P,__vapDatos.inicial(s));return __vapDatos.porProducto(D.g,P,D.plan)}', [P, dict(contra=contra, fam=fam)])}
                    self.assertEqual(set(got), set(ref.index))
                    for item, r in ref.iterrows():
                        rr = got[item]
                        for kk, col in [('v', 'valor'), ('va', 'valor_aa'), ('q', 'cant'), ('qa', 'cant_aa'), ('ep', 'ep')]:
                            self.assertAlmostEqual(rr[kk], float(r[col]), places=7, msg=(rango, contra, fam, item, kk))
                        self.assertAlmostEqual(rr['ep'] + rr['ev'] + rr['nue'] + rr['dej'] + rr['otr'], rr['delta'], places=7)
                    t = a['tot']
                    self.assertAlmostEqual(t['ep'] + t['ev'] + t['nue'] + t['dej'] + t['otr'], t['v'] - t['va'], places=6)

    def test_mes_parcial_dejados_nuevos_y_sin_cantidad(self):
        # Con toda la historia, «Sólo anterior» (marzo 2024) es actual y también la base de marzo 2025.
        a = self.calc({'agrupar': 'Producto'}, dict(self.P, rango=['2025-01', '2025-03']))
        items = {r['item']: r for r in a['det']}
        self.assertEqual(items['Sólo anterior']['clase'], 'dejado')
        self.assertEqual(items['Sólo actual']['clase'], 'nuevo')
        self.assertEqual(items['Sin cantidad']['clase'], 'otro')
        self.assertEqual(items['Harina']['clase'], 'ambos')
        # La compra grande del 25 de marzo anterior queda fuera del espejo al día 20.
        b = self.calc({'contra': 'aa'}, dict(self.P, rango=['2025-03', '2025-03']))
        self.assertLess({r['item']: r for r in b['det']}['Harina']['va'], 1000)
        self.assertIn('Sólo anterior', [r['item'] for r in a['dejados']])
        self.assertIn('Sólo actual', [r['item'] for r in a['nuevos']])
        self.assertEqual([r['nombre'] for r in a['partes']][:2], ['Precio', 'Se compró más' if a['totC']['ev'] >= 0 else 'Se compró menos'])

    def test_partes_cierran_y_cortes(self):
        for s in [{}, {'corte': 'Quién'}, {'corte': 'Cuándo'}, {'meses': ['2025-03']}, {'fam': 'Bebidas'}]:
            a = self.calc(s, dict(self.P, rango=['2024-04', '2025-03']))
            self.assertAlmostEqual(sum(r['valor'] for r in a['partes']), a['delta'], places=6, msg=s)
        a = self.calc({'meses': ['2025-03']}, dict(self.P, rango=['2024-04', '2025-03']))
        self.assertEqual(a['ops'], ['Por qué', 'Quién'])
        b = self.calc({'meses': ['2025-03'], 'detalleMeses': True}, dict(self.P, rango=['2024-04', '2025-03']))
        self.assertAlmostEqual(sum(r['v'] for r in b['tabla']), a['totC']['v'], places=7)

    def test_cantidad_y_precio_solo_con_foco(self):
        a = self.calc({'modo': 'Cantidad'})
        self.assertEqual((a['modo'], a['referencia']), ('Valor', None))
        a = self.calc({'modo': 'Precio', 'foco': 'Harina', 'focoPor': 'Producto'})
        self.assertEqual(a['modo'], 'Precio')
        for r in a['serie']:
            if r['q'] > 0:
                self.assertAlmostEqual(self.pg.evaluate('r=>__vapDatos.magnitud(r,"Precio")', r), r['v'] / r['q'], places=7)
        a = self.calc({'modo': 'Cantidad', 'foco': 'Alimentos', 'focoPor': 'Familia', 'agrupar': 'Producto'})
        self.assertEqual(len({r['p'] for r in a['gf']}), 1)
        self.assertTrue(a['referencia'])
        a = self.calc({'modo': 'Precio', 'foco': 'Sin cantidad', 'focoPor': 'Producto'}, dict(self.P, rango=['2025-01', '2025-03']))
        self.assertIsNone(a['a'])
        self.assertIsNone(a['delta'])

    def test_pestanas_busqueda_y_cobertura(self):
        P = dict(self.P, rango=['2024-04', '2025-03'])
        a = self.calc({}, P)
        self.assertTrue(all(r['clase'] == 'ambos' and r['ep'] > .5 for r in a['precio']))
        self.assertEqual([r['ep'] for r in a['precio']], sorted([r['ep'] for r in a['precio']], reverse=True))
        b = self.calc({'sentido': {'precio': 'baja', 'volumen': 'sube'}}, P)
        self.assertTrue(all(r['ep'] < -.5 for r in b['precio']))
        self.assertTrue(all(r['ev'] > .5 for r in b['volumen']))
        for filtro, esperado in [('Sólo actual', 'Sólo actual'), ('Sólo anterior', 'Sólo anterior'), ('Sin precio comparable', 'Sin cantidad')]:
            self.assertIn(esperado, [r['item'] for r in self.calc({'cobertura': filtro}, P)['tabla']])
        self.assertEqual([r['item'] for r in self.calc({'q': 'solo anterior'}, P)['tabla']], ['Sólo anterior'])
        g = self.calc({'agrupar': 'Familia'}, P)
        self.assertEqual({r['item'] for r in g['tabla']}, {'Alimentos', 'Bebidas'})
        self.assertAlmostEqual(sum(r['delta'] for r in g['tabla']), g['tot']['delta'], places=6)

    def test_venta_ratio_y_pedido_una_vez(self):
        meses = [f'{y}-{m:02d}' for y in (2023, 2024, 2025) for m in range(1, 13)]
        venta = {m: 1000.0 + i for i, m in enumerate(meses)}
        P = dict(self.P, rango=['2025-01', '2025-03'], venta=venta)
        a = self.calc({}, P)
        v = a['venta']
        self.assertEqual(v['meses'], ['2025-01', '2025-02'])  # marzo es parcial
        g = [r for r in a['g'] if r['mes'] in v['meses']]
        self.assertAlmostEqual(v['cn'], sum(r['v'] for r in g), places=7)
        self.assertAlmostEqual(v['vn'], venta['2025-01'] + venta['2025-02'])
        self.assertAlmostEqual(v['va'], venta['2024-01'] + venta['2024-02'])
        root = self.mount(P)
        self.assertIn('por cada S/ 100 vendidos', root.locator('.vap-frase').inner_text())
        self.assertEqual(self.pg.evaluate('__requests.length'), 0)
        P2 = dict(self.P, venta=None, venta_pendiente=True)
        self.mount(P2)
        self.pg.wait_for_timeout(300)
        self.assertEqual([r[0] for r in self.pg.evaluate('__requests')], ['venta'])
        self.assertIn('Cargando la venta', self.pg.locator('.vap-frase').inner_text())
        self.pg.evaluate('P=>__montarVap({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__requests.push(v)})', P2)
        self.pg.wait_for_timeout(300)
        self.assertEqual(len(self.pg.evaluate('__requests')), 1)

    def test_indicadores_suman_la_diferencia_y_familias_de_la_pagina(self):
        P = dict(self.P, rango=['2024-04', '2025-03'], pagina=dict(todas=[['ALIM', 'Alimentos'], ['BEB', 'Bebidas']], elegidas=['ALIM']))
        a = self.calc({}, P)
        self.assertTrue(all(P['mapas']['Familia'][str(r['p'])] == 'Alimentos' for r in a['g']))
        b = self.calc({'fam': 'Alimentos'}, self.P | {'rango': P['rango']})
        self.assertAlmostEqual(a['tot']['v'], b['tot']['v'], places=7)
        self.assertEqual([f['fam'] for f in a['familias']], ['Alimentos'])
        t = a['tot']
        self.assertAlmostEqual(t['ep'] + t['ev'] + t['dej'] + t['nue'] + t['otr'], t['v'] - t['va'], places=6)
        root = self.mount(P)
        vs = root.locator('.vap-kpi .v').all_inner_texts()
        num = lambda x: float(x.replace('−', '-').replace('+', '').replace('S/ ', '').replace(',', ''))
        self.assertLessEqual(abs(sum(num(v) for v in vs[1:]) - round(t['delta'])), 3)
        self.assertEqual(root.locator('.vap-kpi').count(), 4)
        fuera = root.locator('.vap-fuera').inner_text()
        self.assertIn('Bebidas', fuera)
        self.assertIn('año pasado', fuera)
        # El menú avisa al cerrarse, una vez; «Sumarlas», enseguida.
        root.locator('[data-a=menu]').click()
        root.locator('[data-a=pfam][value=BEB]').check()
        self.assertEqual(self.pg.evaluate('__requests.length'), 0)
        self.pg.keyboard.press('Escape')
        self.assertEqual(self.pg.evaluate('__requests'), [['familias', ['ALIM', 'BEB']]])
        P2 = dict(self.P, rango=P['rango'], pagina=dict(todas=[['ALIM', 'Alimentos'], ['BEB', 'Bebidas']], elegidas=['ALIM']))
        root = self.mount(P2)
        root.locator('[data-a=sumar]').click()
        self.assertEqual(self.pg.evaluate('__requests'), [['familias', ['ALIM', 'BEB']]])

    def test_trece_meses_contra_python(self):
        P = dict(self.P, rango=['2025-01', '2025-03'])
        T = self.pg.evaluate("""P=>{const c={},s=__vapDatos.inicial({}),D=__vapDatos.calcular(P,s,c),T=__vapDatos.trece(P,s,D,c);return {meses:T.meses,base:T.base,porMes:T.porMes}}""", P)
        self.assertEqual(T['meses'][-1], '2025-03')
        self.assertEqual(len(T['meses']), 13)
        g = pares(self.h, 12)
        for m in T['meses']:
            x = g[g.mes.astype(str) == m]
            self.assertAlmostEqual(T['porMes'][m]['v'], float(x.valor.sum()), places=6, msg=m)
            self.assertAlmostEqual(T['porMes'][m]['va'], float(x.valor_aa.sum()), places=6, msg=m)
            t = T['porMes'][m]
            self.assertAlmostEqual(t['ep'] + t['ev'] + t['dej'] + t['nue'] + t['otr'], t['delta'], places=6)

    def test_ui_zonas_lista_ficha_meses_y_remontaje(self):
        venta = {f'{y}-{m:02d}': 1000.0 + m for y in (2023, 2024, 2025) for m in range(1, 13)}
        root = self.mount(dict(self.P, rango=['2024-04', '2025-03'], venta=venta))
        pg = self.pg
        # Abre en el total: gráfico, cascada y familias.
        self.assertEqual(root.locator('.vap-col').count(), 12)
        self.assertEqual(root.locator('.vap-cp').count(), 5)
        self.assertIn('Qué explica la diferencia', root.locator('.vap-panel h3').inner_text())
        # Detalle al cursor y venta como medida.
        root.locator('.vap-col').nth(3).hover()
        self.assertTrue(root.locator('[data-plot=mes] .vap-tip').is_visible())
        self.assertIn('Dejados y nuevos', root.locator('[data-plot=mes] .vap-tip').inner_text())
        root.locator('[data-select=medir]').select_option('venta')
        self.assertIn('Compra por cada S/ 100', root.locator('.vap-sub').first.inner_text())
        root.locator('[data-select=medir]').select_option('soles')
        # Los meses: un clic, Mayús + clic, y el chip que los quita.
        root.locator('[data-a=mes][data-v="2025-01"]').click()
        root.locator('[data-a=mes][data-v="2025-03"]').click(modifiers=['Shift'])
        self.assertEqual(pg.evaluate('__comprasAno.s.meses'), ['2025-01', '2025-02', '2025-03'])
        self.assertEqual(root.locator('[data-a=quita-mes]').count(), 3)
        d = pg.evaluate('__comprasAno.D.totC.v')
        self.assertAlmostEqual(d, pg.evaluate('__comprasAno.D.tabla.reduce((s,r)=>s+r.v,0)'), places=6)
        pg.evaluate('__comprasAno.s.meses=[];__vapDatos.dibujar(__comprasAno)')
        # Un indicador deja sólo lo suyo; el orden y Ver por son de la lista.
        root.locator('.vap-kpi[data-v=precio]').click()
        self.assertEqual(pg.evaluate('__comprasAno.s.zona'), 'prod')
        filas = pg.evaluate('__comprasAno.D.precio.length')
        self.assertEqual(root.locator('tbody tr:not(.tot)').count(), filas)
        root.locator('[data-a=orden][data-v=item]').click()
        root.locator('[data-select=agrupar]').select_option('Familia')
        self.assertIn('grupo', root.locator('tr.tot').inner_text())
        root.locator('[data-select=agrupar]').select_option('Producto')
        # La ficha: cifras, 13 meses y Ampliar en los dos sentidos.
        root.locator('.vap-kpi[data-v=compra]').click()
        root.locator('[data-a=zona][data-v=prod]').click()
        root.locator('[data-input=q]').fill('Harina')
        self.assertEqual(root.locator('tbody .vap-tn').count(), 1)
        self.assertEqual(root.locator('[data-input=q]').evaluate('e=>e.getRootNode().activeElement===e'), True)
        root.locator('tbody .vap-tn').click()
        self.assertEqual(root.locator('.vap-panel h3').inner_text(), 'Harina')
        self.assertEqual(root.locator('.vap-cf').count(), 4)
        self.assertEqual(root.locator('.vap-plot.chica .vap-col').count(), 13)
        root.locator('.vap-plot.chica .vap-col').nth(5).hover()
        self.assertTrue(root.locator('[data-plot=ficha] .vap-tip').is_visible())
        root.locator('[data-a=magn][data-v=Precio]').click()
        root.locator('.vap-panel [data-a=amp]').click()
        self.assertEqual(root.locator('.vap-izq').count(), 0)
        root.locator('.vap-panel [data-a=amp]').click()
        # Remontar con los mismos datos no borra lo elegido.
        pg.evaluate('()=>__montarVap({data:__comprasAno.P,parentElement:document.querySelector("#montar")})')
        self.assertEqual(pg.evaluate('__comprasAno.s.sel'), 'Harina')
        root.locator('[data-a=soltar]').click()
        root.locator('[data-input=q]').fill('')
        # #793: ⤢ deja la lista sola; las columnas de más son de «Detalle».
        root.locator('.vap-izq [data-a=amp]').click()
        self.assertEqual(root.locator('.vap-panel').count(), 0)
        pg.keyboard.press('Escape')
        self.assertEqual(root.locator('.vap-panel').count(), 1)
        self.assertNotIn('Motivo', root.locator('thead').inner_text())
        root.locator('.vap-switch').click()
        self.assertIn('Motivo', root.locator('thead').inner_text())
        root.locator('.vap-switch').click()
        # Dejados y nuevos, con dónde se reemplazó; y la familia del panel filtra.
        root.locator('.vap-kpi[data-v=carta]').click()
        root.locator('[data-a=sent][data-v=nue]').click()
        self.assertIn('Sólo actual', root.locator('tbody').inner_text())
        root.locator('.vap-fi[data-a=fam][data-v=Bebidas]').click()
        self.assertEqual(pg.evaluate('__comprasAno.s.fam'), 'Bebidas')
        root.locator('[data-a=quita-fam]').click()
        root.locator('[data-select=contra]').select_option('aa2')
        self.assertEqual(pg.evaluate('__comprasAno.D.V.k'), 24)
        self.assertIn('hace dos años', root.locator('.vap-cab').get_attribute('title'))
        pg.evaluate('()=>__montarVap({data:__comprasAno.P,parentElement:document.querySelector("#montar")})')
        self.assertEqual(pg.evaluate('__comprasAno.s.contra'), 'aa2')
        self.assertEqual(pg.evaluate('__requests.length'), 0)

    def test_excel_numerico_y_contexto(self):
        root = self.mount()
        pg = self.pg
        with pg.expect_download() as down:
            root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ano.xlsx'
            down.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                text = ' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
        for word in ['Contexto', 'Serie mensual', 'Descomposición', 'Familias', 'Efecto precio', 'Efecto volumen', 'Meses de la base', 'cantidad promedio', 'Compra por S/ 100 vendidos']:
            self.assertIn(word, text)
        self.assertIn('<v>', text)
        self.assertNotIn('<f>', text)
        self.assertIn('<v>33.123457</v>', text)

    def test_remontaje_valida_familia_y_vacio(self):
        root = self.mount()
        root.locator('.vap-fi[data-a=fam][data-v=Bebidas]').click()
        self.pg.evaluate('''()=>{const P=structuredClone(__comprasAno.P);P.familias=P.familias.filter(f=>f!=='Bebidas');
          __montarVap({data:P,parentElement:document.querySelector('#montar')})}''')
        self.assertEqual(self.pg.evaluate('__comprasAno.s.fam'), datos.TODAS)
        self.assertTrue(self.pg.evaluate('__comprasAno.D.serie.length'))
        P = dict(self.P, rango=['2023-01', '2023-12'])
        root = self.mount(P)
        self.assertIn('No hay meses para comparar', root.inner_text())
        self.assertTrue(root.locator('[data-a=excel]').is_disabled())

    def test_una_pantalla_y_movil(self):
        root = self.mount(dict(self.P, rango=['2024-04', '2025-03']))
        pg = self.pg
        self.assertEqual(pg.locator('.vap').evaluate('e=>Math.round(e.getBoundingClientRect().height)'), 575)
        self.assertLessEqual(pg.locator('.vap').evaluate('e=>e.scrollHeight-e.clientHeight'), 1)
        for kpi in ('precio', 'cantidad', 'carta', 'compra'):
            root.locator(f'.vap-kpi[data-v={kpi}]').click()
            self.assertLessEqual(pg.locator('.vap').evaluate('e=>e.scrollHeight-e.clientHeight'), 1, kpi)
        pg.set_viewport_size({'width': 390, 'height': 844})
        try:
            self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'), 390)
            pg.locator('.vap-kpi[data-v=precio]').click()
            self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'), 390)
        finally:
            pg.set_viewport_size({'width': 1323, 'height': 619})


if __name__ == '__main__':
    unittest.main(verbosity=2)
