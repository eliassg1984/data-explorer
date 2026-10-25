"""Destino del producto: cuenta de referencia, controles locales y mejoras (#737)."""
import unittest
import zipfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).parent
from test_sin_plato_cierre_pieza import muestra
from graficos import destino_datos as datos
from graficos import movimientos_destino as md
import sin_plato as sp
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None


def payload(n=0):
    per,f,t=muestra(n);f.loc[f.cod=='0000000',['ini_q','entro_q','plato_q','prep_q','baja_q','otras_q','aj_q','fin_q']]=[10,30,12,3,2,1,-2,20]
    f.loc[f.cod=='0000001',['baja_q','otras_q','sobr_q']]=[-2,3,2]
    P=datos.armar(per,f,t);P.update(inicial=dict(k=1,cod=None,grupo='alimentos',filtro=0,medida='v',q=''),comun='inicio',parte='producto');return P,f


class Contrato(unittest.TestCase):
    def test_firma_cache_y_nonce_de_salto(self):
        from graficos import destino_producto_pieza as pieza
        ss={md._K_FOCO:'0000001',md.K_CIERRE_2:'cierre_0',md._K_SALTO:3};fake=SimpleNamespace(session_state=ss,container=lambda **kw:nullcontext(),markdown=Mock())
        with patch.object(pieza,'st',fake),patch.object(md,'st',fake),patch.object(md,'_cargar',return_value=muestra()),patch.object(pieza,'_PIEZA') as comp,patch.object(datos,'armar',wraps=datos.armar) as build:
            md.tarjeta_por_producto();P=comp.call_args.kwargs['data'];self.assertEqual(P['inicial']['cod'],'0000001');self.assertEqual(P['inicial']['k'],0)
            md.tarjeta_por_producto();self.assertEqual(build.call_count,1);self.assertEqual(P['comun'],comp.call_args.kwargs['data']['comun'])
            ss[md._K_SALTO]+=1;md.tarjeta_por_producto();self.assertNotEqual(P['comun'],comp.call_args.kwargs['data']['comun']);self.assertEqual(build.call_count,1)
        import inspect
        self.assertEqual(len(inspect.signature(md.tarjeta_por_producto).parameters),1)

    def test_fuente_ausente_y_familias(self):
        from graficos import destino_producto_pieza as pieza
        with patch.object(md,'_cargar',return_value=None) as load,patch.object(md,'_vacia') as vacia:pieza.renderizar(('ALIMENTOS',));load.assert_called_once_with(('ALIMENTOS',));self.assertIn('dos cierres',vacia.call_args.args[2])

    def test_cache_reconoce_distribucion(self):
        from graficos import destino_producto_pieza as pieza
        per,f,t=muestra();fake=SimpleNamespace(session_state={},container=lambda **kw:nullcontext(),markdown=Mock())
        with patch.object(pieza,'st',fake),patch.object(md,'st',fake),patch.object(md,'_cargar',return_value=(per,f,t)),patch.object(pieza,'_PIEZA'),patch.object(datos,'armar',wraps=datos.armar) as build:
            pieza.renderizar();f.loc[0,'entro_q']+=1;f.loc[1,'entro_q']-=1;pieza.renderizar();self.assertEqual(build.call_count,2)


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start();cls.br=cls.pw.chromium.launch();cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000)
        cls.pg.route('https://producto.example.test/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://producto.example.test/')
        from graficos import destino_producto_pieza as pieza
        css=pieza._CSS
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}',css)
        base=(ROOT/'graficos/destino_base.js').read_text(encoding='utf-8')
        js=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+base+(ROOT/'graficos/destino_producto.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarProducto=function(component)')
        cls.pg.add_script_tag(content=js,type='module');cls.pg.wait_for_function('typeof montarProducto==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,ui])=>{sessionStorage.setItem("destino_producto_737",JSON.stringify(ui||{}));montarProducto({data:P,parentElement:mount,setTriggerValue:()=>{throw Error("Control local pide Python")}})}',[P or payload()[0],ui]);return self.pg.locator('.dst-producto')

    def test_tabla_filtros_contra_helpers(self):
        P,f=payload();self.mount(P)
        for k in range(2):
            fk=f[f.k==k];mov=fk.salio_v.abs()+fk.entro_v.abs()+fk.aj_v.abs()>.5
            for grupo,clase in [('alimentos',sp.ALIMENTOS),('operacion',sp.OPERACION)]:
                for filtro in range(4):
                    state=dict(k=k,grupo=grupo,filtro=filtro,q='');got=self.pg.evaluate('s=>__destinoProductoDatos.tabla(__destinoProducto.B,s).visibles',state);exp=fk[mov&(fk.clase==clase)]
                    if grupo=='alimentos':
                        if filtro==1:exp=exp[exp.baja_v>.5]
                        if filtro==2:exp=exp[sp.sin_salida_registrada(exp)]
                        if filtro==3:exp=exp[exp.aj_v>.5]
                    self.assertEqual(set(r['cod'] for r in got),set(exp.cod))

    def test_porcentaje_ponderado_y_no_media(self):
        P,f=payload();self.mount(P);got=self.pg.evaluate('()=>Object.fromEntries(__destinoProductoDatos.previos(__destinoProducto.B,1))');exp=sp.pct_previo(f,1)
        for cod,v in exp.items():self.assertAlmostEqual(got[cod],v)
        self.assertEqual(self.pg.evaluate('__destinoProductoDatos.previos(__destinoProducto.B,0).size'),0)

    def test_seis_cierres_ponderados_excluyen_actual_y_muy_antiguo(self):
        self.mount();rs=[dict(k=k,cod='0000001',sinplato_v=sn,salio_v=sa) for k,sn,sa in [(0,1000,1000),(1,9,10),(2,0,90),(6,1,10),(7,100,100)]]
        got=self.pg.evaluate('rs=>Object.fromEntries(__destinoProductoDatos.previos({L:rs},7))',rs);self.assertAlmostEqual(got['0000001'],sp.pct_previo(pd.DataFrame(rs),7)['0000001']);self.assertAlmostEqual(got['0000001'],10/110)

    def test_grafico_producto_contra_plotly_cada_grupo(self):
        P,f=payload();self.mount(P);per,_,_=muestra()
        for _,r in f[f.k==1].iterrows():
            got=self.pg.evaluate('r=>__destinoProductoDatos.historia(__destinoProducto.B,r,1)',r.to_dict());fig=md._fig_producto(r,f,per,1)
            for j,h in enumerate(got):
                for i,serie in enumerate(fig.data[:-1]):self.assertEqual(h['partes'][i]['v'],serie.y[j])
                self.assertEqual(h['entro'],fig.data[-1].y[j])

    def test_parejas_contra_helper_y_pista_no_conclusion(self):
        P,f=payload();f.loc[f.cod=='0000000',['producto','aj_v']]=['(P) Lomo trozos',-30];f.loc[f.cod=='0000001',['producto','aj_v']]=['Lomo medallon',40]
        per,_,_=muestra();P2=datos.armar(per,f,sp.totales(f,2))|{k:P[k] for k in ['inicial','comun','parte']};root=self.mount(P2)
        for k in range(2):
            for cod in ['0000000','0000001']:
                got=self.pg.evaluate('([k,cod])=>__destinoProductoDatos.parejas(__destinoProducto.B.porK.get(k),cod)',[k,cod]);self.assertEqual([r['cod'] for r in got],sp.parejas(f[f.k==k],cod).cod.tolist())
        self.assertIn('no una conclusión',root.locator('[data-k=ficha]').inner_text())

    def test_cuenta_fisica_sin_cambiar_unidades(self):
        self.mount();c=self.pg.evaluate('__destinoProductoDatos.cuenta(__destinoProducto.F)');self.assertTrue(c['cuadra']);self.assertEqual(c['calc'],20)

    def test_busqueda_teclado_y_grupo_locales(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('0000001');self.assertEqual(q.input_value(),'0000001');root.locator('tr[data-a=producto]').press('Enter');self.assertEqual(self.pg.evaluate('__destinoProducto.F.cod'),'0000001')
        q.fill('');root.locator('[data-a=grupo][data-v=operacion]').click();self.assertEqual(self.pg.evaluate('__destinoProducto.F.clase'),sp.OPERACION)

    def test_cierres_unidades_y_orden(self):
        root=self.mount();root.locator('[data-k=medida]').select_option('q');self.assertIn('Unidad',root.locator('[data-k=cab]').inner_text());root.locator('[data-a=orden][data-v=entro_q]').click();root.locator('[data-a=anterior]').click();self.assertEqual(self.pg.evaluate('__destinoProducto.s.k'),0);root.locator('svg [data-a=cierre][data-v="1"]').click();self.assertEqual(self.pg.evaluate('__destinoProducto.s.k'),1)

    def test_seleccion_no_redibuja_lista(self):
        root=self.mount();self.pg.evaluate('window.primeraFila=__destinoProducto.D.visibles[0].cod');first=root.locator('tr[data-a=producto]').first.element_handle();root.locator('tr[data-a=producto]').last.click();self.assertTrue(first.evaluate('e=>e.isConnected'))

    def test_listas_largas_foco_fuera_de_primera_tanda(self):
        P,_=payload(330);root=self.mount(P);self.assertEqual(root.locator('tr[data-a=producto]').count(),150);root.locator('[data-a=mas]').click();self.assertEqual(root.locator('tr[data-a=producto]').count(),300)
        P['inicial']['cod']='0000333';P['comun']='salto';root=self.mount(P);self.assertEqual(self.pg.evaluate('__destinoProducto.F.cod'),'0000333');self.assertEqual(root.locator('tr.on').count(),1)

    def test_eco_no_pisa_estado_y_salto_repetido_si(self):
        root=self.mount();root.locator('[data-a=anterior]').click();ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("destino_producto_737"))');self.mount(ui=ui);self.assertEqual(self.pg.evaluate('__destinoProducto.s.k'),0)
        P,_=payload();P['inicial']['cod']='0000001';P['comun']='salto2';self.mount(P,ui);self.assertEqual(self.pg.evaluate('__destinoProducto.F.cod'),'0000001');self.assertEqual(self.pg.evaluate('__destinoProducto.s.k'),1)

    def test_excel_fuente_completa_codigos_y_cantidades(self):
        root=self.mount();root.locator('[data-k=q]').fill('Producto 1')
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        with zipfile.ZipFile(dl.value.path()) as z:
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),6);self.assertIn('0000001',z.read('xl/worksheets/sheet1.xml').decode());self.assertIn('0000002',z.read('xl/worksheets/sheet3.xml').decode())

    def test_movil_y_eventos_duplicados(self):
        root=self.mount();self.mount();self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),390);root.locator('[data-a=anterior]').click();self.assertEqual(self.pg.evaluate('__destinoProducto.s.k'),0)


if __name__=='__main__':unittest.main(verbosity=2)
