"""Contrato contable, selección local y exportación de Sin plato (#736)."""
import json
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
import sin_plato as sp
from graficos import destino_datos as datos
from graficos import movimientos_destino as md

ROOT=Path(__file__).parent
NUMEROS='entro_q entro_v prep_q prep_v vend_q vend_v aj_q aj_v notas_q notas_v compra_v baja_q baja_v ini_q ini_v fin_q fin_v venta cort evvi cort_q evvi_q combos_q venta_q venta_v combos_v cort_v evvi_v otras_q falt_q sobr_q plato_q sinplato_q salio_q otras_v falt_v sobr_v plato_v sinplato_v salio_v pct'.split()


def muestra(n=0):
    per=[]
    for k,(desde,hasta) in enumerate([('2026-01-04','2026-02-03'),('2026-02-04','2026-03-05')]):
        per.append(dict(k=k,clave=f'cierre_{k}',nombre=f'Cierre {k}',corto=f'c{k}',desde=pd.Timestamp(desde).date(),hasta=pd.Timestamp(hasta).date(),cierre='Conteo actual',cierre_ant='Conteo anterior'))
    rows=[]
    for k in range(2):
        for j in range(4+n):
            r=dict.fromkeys(NUMEROS,0.0);r.update(k=k,cod=f'{j:07d}',producto='Producto '+str(j),unidad='KILOS',familia='Prueba',clase=sp.ALIMENTOS)
            r.update(baja_v=1+k,otras_v=2,falt_v=3,sinplato_v=6+k,sobr_v=5,aj_v=-3,entro_v=20,compra_v=20,venta_v=10,venta=10,salio_v=16+k,pct=(6+k)/(16+k),ini_q=4,fin_q=5)
            if j==1:r.update(baja_v=2,otras_v=2,falt_v=2,sinplato_v=6)
            if j==2:r.update(clase=sp.OPERACION,aj_v=-30,otras_v=12)
            if j==3 and not k:continue
            rows.append(r)
    f=pd.DataFrame(rows);return per,f,sp.totales(f,len(per))


def payload(n=0):return datos.armar(*muestra(n),{'Familias':['Prueba']})|dict(parte='cierre',inicial=1)


class Contrato(unittest.TestCase):
    def test_transporte_numerico_sin_redondeo_y_codigos_texto(self):
        per,f,t=muestra();f.loc[0,'entro_q']=.123456789123;f.loc[1,'pct']=float('nan');P=datos.armar(per,f,t);json.dumps(P,allow_nan=False)
        self.assertEqual(P['filas'][0][P['columnas'].index('entro_q')+1],.123456789123);self.assertIsNone(P['filas'][1][P['columnas'].index('pct')+1]);self.assertEqual(P['productos'][0][0],'0000000')

    def test_metadatos_no_mezclan_unidades_ni_descripciones(self):
        per,f,t=muestra();f.loc[1,'cod']='0000000';f.loc[1,'unidad']='LITROS';P=datos.armar(per,f,t);self.assertNotEqual(P['filas'][0][0],P['filas'][1][0])

    def test_totales_html_y_dias_son_canonicos(self):
        per,f,t=muestra();P=datos.armar(per,f,t);self.assertEqual(P['periodos'][0]['dias'],31);self.assertEqual(P['periodos'][1]['dias'],30)
        tk=t.set_index('k');self.assertEqual(P['periodos'][1]['kpis'],md._kpis(tk.loc[1],tk.loc[0],per[0]));self.assertEqual(P['periodos'][1]['ecuacion'],md._ecuacion(tk.loc[1]))
        self.assertEqual(P['totales'][1]['otras'],t.set_index('k').loc[1,'otras'])

    def test_sello_reconoce_distribucion_y_contexto(self):
        per,f,t=muestra();P=datos.armar(per,f,t);g=f.copy();g.loc[0,'entro_q']+=1;g.loc[1,'entro_q']-=1
        self.assertNotEqual(P['sello'],datos.armar(per,g,t)['sello']);self.assertNotEqual(P['sello'],datos.armar(per,f,t,{'Familias':['Otra']})['sello'])

    def test_cache_y_firma_publica(self):
        from graficos import sin_plato_cierre_pieza as pieza
        fake=SimpleNamespace(session_state={},container=lambda **kw:nullcontext(),markdown=Mock(),rerun=Mock())
        with patch.object(pieza,'st',fake),patch.object(md,'st',fake),patch.object(md,'_cargar',return_value=muestra()),patch.object(pieza,'_PIEZA') as comp,patch.object(datos,'armar',wraps=datos.armar) as build:
            md.tarjeta_sin_plato();md.tarjeta_sin_plato();self.assertEqual(build.call_count,1);self.assertTrue(comp.called)
        import inspect
        self.assertEqual(len(inspect.signature(md.tarjeta_sin_plato).parameters),1)

    def test_salto_valida_fuente_y_conserva_contrato(self):
        from graficos import sin_plato_cierre_pieza as pieza
        import navegacion
        P=payload();ss={'_sin_plato_cierre_cache':('',P),'sin_plato_cierre_pieza':{'abrir':dict(sello=P['sello'],k=1,cod='0000000')}};fake=SimpleNamespace(session_state=ss)
        with patch.object(pieza,'st',fake),patch.object(md,'st',fake):
            pieza._abrir();self.assertEqual(ss[md.K_CIERRE_2],'cierre_1');self.assertEqual(ss[md._K_FOCO],'0000000');self.assertEqual(ss[navegacion.CLAVE_SALTO_VISTA],md.VISTA_PRODUCTO);self.assertNotIn('_sin_plato_cierre_salto',ss)
            for v in [dict(sello='viejo',k=1,cod='0000000'),dict(sello=P['sello'],k=True,cod='0000000'),dict(sello=P['sello'],k=1,cod='0000002'),dict(sello=P['sello'],k=-1,cod='0000000')]:
                ss['sin_plato_cierre_pieza']['abrir']=v;before=ss[md._K_SALTO];pieza._abrir();self.assertEqual(ss[md._K_SALTO],before)

    def test_sin_fuente_conserva_mensaje(self):
        from graficos import sin_plato_cierre_pieza as pieza
        with patch.object(md,'_cargar',return_value=None),patch.object(md,'_vacia') as vacia:pieza.renderizar();self.assertIn('dos cierres',vacia.call_args.args[2])


try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        try:cls.br=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        from graficos import sin_plato_cierre_pieza as pieza
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000)
        cls.pg.route('https://destino.example.test/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://destino.example.test/')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}',pieza._CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/destino.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarDestino=function(component)'),type='module');cls.pg.wait_for_function('typeof montarDestino==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,ui])=>{sessionStorage.setItem("sin_plato_cierre_736",JSON.stringify(ui||{}));window.triggers=[];montarDestino({data:P,parentElement:mount,setTriggerValue:(k,v)=>triggers.push([k,v])})}',[P or payload(),ui]);return self.pg.locator('.dst-cierre')

    def test_rank_contra_cuenta_sin_tope_40_y_empates(self):
        P=payload(170);root=self.mount(P);d=self.pg.evaluate('__sinPlatoCierre.D');self.assertEqual(len(d['todos']),173);self.assertEqual(root.locator('tbody[data-k=ranking] tr').count(),150)
        root.locator('[data-a=mas]').click();self.assertEqual(root.locator('tbody[data-k=ranking] tr').count(),173)
        for r in d['todos']:self.assertEqual(r['valor'],r['sinplato_v'])
        self.assertEqual(next(r for r in d['todos'] if r['cod']=='0000001')['dominante']['nombre'],'otras salidas')

    def test_delta_sin_referencia_y_cero_real(self):
        self.mount();rs={r['cod']:r for r in self.pg.evaluate('__sinPlatoCierre.D.todos')};self.assertIsNone(rs['0000003']['delta']);self.assertEqual(rs['0000000']['delta'],1)
        P=payload();vi=P['columnas'].index('sinplato_v')+1;ki=P['columnas'].index('k')+1
        for row in P['filas']:
            if row[ki]==0 and P['productos'][row[0]][0]=='0000000':row[vi]=0
        self.mount(P);r=self.pg.evaluate('__sinPlatoCierre.D.todos.find(r=>r.cod==="0000000")');self.assertEqual(r['antes'],0);self.assertEqual(r['delta'],7)

    def test_busqueda_shadowroot_filtros_orden_y_teclado(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('Producto 1');self.assertEqual(q.input_value(),'Producto 1');self.assertEqual(len(self.pg.evaluate('__sinPlatoCierre.D.visibles')),1)
        q.fill('0000003');root.locator('tr[data-a=abrir]').press('Enter');self.assertEqual(self.pg.evaluate('triggers[0][1].cod'),'0000003');self.assertEqual(self.pg.evaluate('triggers[0][1].k'),1)
        q.fill('');root.locator('[data-k=min]').select_option('100');self.assertEqual(len(self.pg.evaluate('__sinPlatoCierre.D.visibles')),0)

    def test_cierre_grafico_y_sobrantes_son_locales(self):
        root=self.mount();root.locator('[data-a=anterior]').click();self.assertEqual(self.pg.evaluate('__sinPlatoCierre.s.k'),0);root.locator('svg [data-a=cierre][data-v="1"]').click();self.assertEqual(self.pg.evaluate('__sinPlatoCierre.s.k'),1)
        root.locator('[data-k=modo]').select_option('sobr');self.assertTrue(all(r['valor']==5 for r in self.pg.evaluate('__sinPlatoCierre.D.todos')));self.assertEqual(self.pg.evaluate('triggers.length'),0)

    def test_comparacion_usa_totales_completos_y_dias_reales(self):
        self.mount();js=self.pg.evaluate('__destinoDatos.comparar(__sinPlatoCierre.B,1)');per,f,t=muestra();tk=t.set_index('k');self.assertEqual(js[0]['actual'],tk.loc[1,['baja','otras','falt']].sum());self.assertEqual(js[0]['por_dia'],js[0]['actual']/30)
        self.assertTrue(all(r['antes'] is None for r in self.pg.evaluate('__destinoDatos.comparar(__sinPlatoCierre.B,0)')))

    def test_grafico_contra_plotly_incluye_negativos(self):
        per,f,t=muestra();t.loc[0,'otras']=-50;P=datos.armar(per,f,t)|dict(inicial=1,parte='cierre');self.mount(P);js=self.pg.evaluate('__destinoDatos.grafico(__sinPlatoCierre.B,1)');fig,ks=md._fig_cierres(t,per,1)
        for i,k in enumerate(ks):
            for j,tr in enumerate(fig.data):self.assertEqual(js[i]['partes'][j]['v'],tr.y[i])
        rects=self.pg.locator('.dst-chart rect').evaluate_all('rs=>rs.map(r=>Number(r.getAttribute("height")))');self.assertTrue(all(v>=0 for v in rects))

    def test_estado_local_sobrevive_rerun_y_clave_desaparecida(self):
        root=self.mount();root.locator('[data-a=anterior]').click();ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("sin_plato_cierre_736"))');self.mount(ui=ui);self.assertEqual(self.pg.evaluate('__sinPlatoCierre.s.k'),0)
        ui['clave']='desaparecida';self.mount(ui=ui);self.assertEqual(self.pg.evaluate('__sinPlatoCierre.s.k'),1)

    def test_excel_numeros_seis_decimales_codigos_y_fuente_sin_filtro(self):
        root=self.mount();root.locator('[data-k=q]').fill('Producto 1')
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        with dl.value.path().open('rb') as source,zipfile.ZipFile(source) as z:
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),8)
            xml=z.read('xl/worksheets/sheet1.xml').decode();self.assertIn('0000001',xml);self.assertIn('<v>6</v>',xml)
            fuente=z.read('xl/worksheets/sheet3.xml').decode();self.assertIn('0000002',fuente);self.assertEqual(fuente.count('<row '),5)

    def test_movil_no_desborda_y_no_duplica_eventos(self):
        root=self.mount();self.mount();self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),390)
        root.locator('tr[data-a=abrir]').first.click();self.assertEqual(self.pg.evaluate('triggers.length'),1)


if __name__=='__main__':unittest.main(verbosity=2)
