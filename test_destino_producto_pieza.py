"""Destino del producto: cuenta de referencia, controles locales y mejoras (#737)."""
import unittest
import zipfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).parent
from test_sin_plato_cierre_pieza import muestra, NUMEROS
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


def payload_flujo():
    """Movimientos que cuadran con dos unidades, producción y operación."""
    per,_,_=muestra()
    rs=[]
    for k in range(2):
        a=dict(cod='0000000',producto='Alimento de prueba',unidad='KILOS',familia='ALIMENTOS',clase=sp.ALIMENTOS,k=k,
            ini_v=100,compra_v=1000,entro_v=1050,venta_v=600,cort_v=20,evvi_v=30,combos_v=100,
            prep_94_v=100,prep_96_v=30,prep_90_v=20,ing_94_v=50,ing_96_v=0,ing_90_v=0,
            prep_v=150,baja_v=40,nota_91_v=10,nota_92_v=5,nota_98_v=60,otras_v=35,aj_v=-25,fin_v=250,
            plato_v=650,salio_v=900,sinplato_v=100,pct=100/900,falt_v=25,sobr_v=0)
        b=dict(a,cod='0000001',producto='Bebida sin bajas',unidad='LITROS',compra_v=200,entro_v=200,ini_v=50,fin_v=230,
            venta_v=20,cort_v=0,evvi_v=0,combos_v=0,prep_v=0,prep_94_v=0,prep_96_v=0,prep_90_v=0,
            ing_94_v=0,baja_v=0,nota_91_v=0,nota_92_v=0,nota_98_v=0,otras_v=0,aj_v=0,plato_v=20,salio_v=20,sinplato_v=0,pct=0,falt_v=0)
        c=dict(b,cod='0000002',producto='Carbón',unidad='KILOS',familia=sp.FAMILIA_OPERACION,clase=sp.OPERACION,
            venta_v=0,plato_v=0,aj_v=-100,falt_v=100,fin_v=150,salio_v=100,sinplato_v=100,pct=1)
        for r in (a,b,c):
            # Los campos de cantidad son independientes: el Sankey no suma
            # kilos con litros ni usa cantidades para repartir soles.
            base=dict.fromkeys(sp.movimientos(None).columns,0.0)
            base.update({c:0.0 for c in NUMEROS})
            base.update(r);rs.append(base)
    f=pd.DataFrame(rs);P=datos.armar(per,f,sp.totales(f,2))
    P.update(inicial=dict(k=1,cod=None,grupo='alimentos',filtro=0,medida='v',q=''),comun='flujo',parte='producto')
    return P,f


class Contrato(unittest.TestCase):
    def test_desglose_del_kardex_conserva_la_cuenta_y_tipos_desconocidos(self):
        rows=[('01',100,0),('07',0,10),('94',50,20),('96',30,15),('90',5,2),('95',0,40),('91',0,3),('92',0,4),('98',2,10),('93',0,6),('97',0,800),('99',900,0),('X',11,7)]
        kx=pd.DataFrame([dict(k=0,cod='0001',tipo=t,cant_in=a,cant_out=b,val_in=a*2,val_out=b*2) for t,a,b in rows])
        r=sp.movimientos(kx).iloc[0]
        self.assertEqual(r['entro_v'],350);self.assertEqual(r['compra_v'],180)
        self.assertEqual(r['prep_v'],74);self.assertEqual(r['notas_v'],30)
        self.assertEqual([r[f'prep_{t}_v'] for t in ('94','96','90')],[40,30,4])
        self.assertEqual([r[f'nota_{t}_v'] for t in ('91','92','98')],[6,8,16])
        self.assertEqual((r['otros_ing_v'],r['otros_sal_v']),(22,14))
        self.assertEqual(set(sp.movimientos(None).columns),set(sp.movimientos(kx).columns))

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
        js=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+base+(ROOT/'graficos/destino_flujo.js').read_text(encoding='utf-8')+(ROOT/'graficos/destino_producto.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarProducto=function(component)')
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
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),7);self.assertIn('0000001',z.read('xl/worksheets/sheet1.xml').decode());self.assertIn('0000002',z.read('xl/worksheets/sheet3.xml').decode())

    def test_movil_y_eventos_duplicados(self):
        root=self.mount();self.mount();self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),390);root.locator('[data-a=anterior]').click();self.assertEqual(self.pg.evaluate('__destinoProducto.s.k'),0)

    def test_flujo_cuadra_sin_duplicar_combos_y_con_todos_los_tipos(self):
        P,f=payload_flujo();self.mount(P)
        got=self.pg.evaluate('__destinoProducto.flujo.real')
        self.assertAlmostEqual(got['entradas'],1400);self.assertAlmostEqual(got['salidas'],1400)
        self.assertAlmostEqual(got['stock'],480);self.assertAlmostEqual(got['compras'],1200)
        hojas={n['id']:n['value'] for n in got['hojas']}
        self.assertEqual(hojas['out:venta'],620)
        self.assertNotIn('out:combos',hojas)
        for key,v in [('prep94',100),('prep96',30),('prep90',20),('nota91',10),('nota92',5),('nota98',20),('baja',40),('falt',25)]:self.assertEqual(hojas['out:'+key],v)
        self.assertFalse(any(n['parte']=='valorizacion' for n in got['hojas']))
        rs=f[f.k==1].to_dict('records')
        combined=self.pg.evaluate('rs=>__destinoFlujoDatos.modelo(rs)',rs)
        self.assertEqual(next(n['value'] for n in combined['hojas'] if n['parte']=='operacion'),100)
        self.assertEqual(combined['entradas'],combined['salidas'])

    def test_flujo_reversos_valorizacion_stock_negativo_y_otro_tipo(self):
        self.mount()
        rows=[dict(ini_v=100,compra_v=-25,entro_v=-25,fin_v=75),
              dict(ini_v=100,venta_v=-10,fin_v=110),
              dict(ini_v=100,fin_v=120),
              dict(venta_v=20,fin_v=-20),
              dict(otros_ing_v=60,otros_sal_v=10,fin_v=50)]
        for row in rows:
            got=self.pg.evaluate('r=>__destinoFlujoDatos.modelo([r],"detalle")',row)
            self.assertAlmostEqual(got['entradas'],got['salidas'])
            self.assertEqual(got['stock'],row['fin_v'])
            self.assertTrue(all(n['value']>0 for n in got['nodos']))
        reval=self.pg.evaluate('r=>__destinoFlujoDatos.modelo([r])',rows[2])
        self.assertEqual(next(n['value'] for n in reval['hojas'] if n['parte']=='valorizacion'),20)
        cancel=self.pg.evaluate('()=>__destinoFlujoDatos.modelo([{compra_v:50,entro_v:50,fin_v:50},{compra_v:-50,entro_v:-50,fin_v:-50}])')
        self.assertEqual(cancel['compras'],0)
        self.assertTrue({'in:compra','out:compra'}.issubset({n['id'] for n in cancel['hojas']}))
        reversal=self.pg.evaluate('()=>__destinoFlujoDatos.modelo([{nota_91_v:-5,nota_92_v:0,nota_98_v:0,otras_v:0,fin_v:5}],"detalle")')
        self.assertEqual({n['id'] for n in reversal['hojas']},{'in:nota91','out:fin'})
        mismatch=self.pg.evaluate('()=>__destinoFlujoDatos.modelo([{nota_91_v:0,nota_92_v:0,nota_98_v:0,baja_v:20,fin_v:0}],"detalle")')
        self.assertEqual({n['id'] for n in mismatch['hojas']},{'in:conciliacion_notas','out:baja'})

    def test_flujo_destino_filtra_detalle_y_producto_mantiene_soles(self):
        P,_=payload_flujo();root=self.mount(P)
        root.locator('[data-flujo-nodo="out:grupo:notas"]').click()
        self.assertEqual(root.locator('tr[data-a=producto]').count(),1)
        self.assertEqual(self.pg.evaluate('__destinoProducto.D.visibles[0].cod'),'0000000')
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.real.compras'),1200)
        root.locator('[data-flujo=limpiar]').click();self.assertEqual(root.locator('tr[data-a=producto]').count(),2)
        root.locator('[data-flujo=ambito]').select_option('producto')
        root.locator('tr[data-a=producto]').last.click()
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.real.compras'),200)
        root.locator('[data-k=medida]').select_option('q')
        self.assertIn('S/',root.locator('.dstf-metrics').inner_text())
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.real.stock'),230)

    def test_simulacion_recalcula_sin_mutar_datos_y_acepta_cero(self):
        P,_=payload_flujo();root=self.mount(P)
        before=self.pg.evaluate('JSON.stringify(__destinoProducto.B.L)')
        root.locator('[data-flujo=simular]').check()
        root.locator('[data-flujo-nodo="in:compra"]').click()
        amount=root.locator('[data-flujo-importe="in:compra"]');amount.fill('1300')
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.mostrado.stock'),580)
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.real.stock'),480)
        amount.fill('0');self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.mostrado.stock'),-720)
        self.assertIn('Stock negativo',root.locator('.dstf-validacion').inner_text())
        self.pg.evaluate('__destinoProducto.render()')
        self.assertEqual(root.locator('[data-flujo-importe="in:compra"]').input_value(),'0')
        self.assertEqual(self.pg.evaluate('JSON.stringify(__destinoProducto.B.L)'),before)
        root.locator('[data-flujo=simular]').uncheck()
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.mostrado.stock'),480)

    def test_simulacion_invalida_no_introduce_nan_y_contexto_reinicia_importes(self):
        P,_=payload_flujo();root=self.mount(P)
        root.locator('[data-flujo=simular]').check();root.locator('[data-flujo-nodo="in:compra"]').click()
        inp=root.locator('[data-flujo-importe="in:compra"]');inp.fill('-10')
        self.assertEqual(inp.get_attribute('aria-invalid'),'true')
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.mostrado.stock'),480)
        inp.fill('1300');ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("destino_producto_737"))')
        self.mount(P,ui);self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.mostrado.stock'),580)
        root.locator('[data-a=anterior]').click()
        self.assertEqual(self.pg.evaluate('__destinoProducto.s.flujo.cambios'),{})
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.mostrado.stock'),480)
        root.locator('[data-k=q]').fill('sin coincidencias')
        self.assertEqual(self.pg.evaluate('__destinoProducto.flujo.mostrado.entradas'),0)
        self.assertFalse(root.locator('.dstf-svg').evaluate('e=>/NaN|undefined/.test(e.innerHTML)'))

    def test_flujo_excel_distingue_fuente_de_escenario(self):
        P,_=payload_flujo();root=self.mount(P);root.locator('[data-flujo=simular]').check()
        root.locator('[data-flujo-nodo="in:compra"]').click();root.locator('[data-flujo-importe="in:compra"]').fill('1300')
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        with zipfile.ZipFile(dl.value.path()) as z:
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),8)
            self.assertIn('Flujo real',z.read('xl/workbook.xml').decode())
            self.assertIn('Escenario simulado',z.read('xl/workbook.xml').decode())
            self.assertIn('<v>1200</v>',z.read('xl/worksheets/sheet7.xml').decode())
            self.assertIn('<v>1300</v>',z.read('xl/worksheets/sheet8.xml').decode())

    def test_flujo_responsivo_todos_los_desgloses_y_teclado(self):
        P,_=payload_flujo();root=self.mount(P);root.locator('[data-flujo=detalle]').click()
        for width in (1323,844,390,320):
            self.pg.set_viewport_size({'width':width,'height':900});self.pg.wait_for_timeout(80)
            self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),width)
            overlaps=root.locator('.dstf-nodo').evaluate_all('''es=>{
                const rs=es.map(e=>e.getBoundingClientRect());let n=0;
                for(let i=0;i<rs.length;i++)for(let j=i+1;j<rs.length;j++){const a=rs[i],b=rs[j];if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)n++;}
                return n;
            }''')
            self.assertEqual(overlaps,0, f'etiquetas a {width}px')
        root.locator('[data-flujo-nodo="out:nota92"]').press('Enter')
        self.assertEqual(self.pg.evaluate('__destinoProducto.s.flujo.destino'),'out:nota92')
        self.assertIn('Merma fija',root.locator('.dstf-editor').inner_text())


if __name__=='__main__':unittest.main(verbosity=2)
