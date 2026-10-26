"""Destino del producto: cuenta de referencia, controles locales y mejoras (#737);
el flujo neteado, los dos relojes y el mapa por área (#743)."""
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


def areas_prueba():
    """El balance por área del cierre 1: el Almacén reparte, Producción
    porciona y devuelve, la Cocina vende; una bebida se compensa."""
    cols=list(sp._COLS_AREA)
    def v(**kw):return [float(kw.get(c,0)) for c in cols]
    k1={'areas':{'0':v(ini=10,fin=20,compra=1200,req_out=700,tr_in=300,aj_neg=15),
                 '1':v(ini=5,fin=40,req_in=500,venta=600,notas=75,aj_pos=10,aj_neg=25),
                 '6':v(fin=5,req_in=200,tr_out=300,prod_in=150,prod_out=150)},
        'flechas':[['99',0,1,500.0,10,3,[['Alimento de prueba',400.0],['Bebida sin bajas',100.0]]],
                   ['99',0,6,200.0,4,2,[['Alimento de prueba',200.0]]],['97',6,0,300.0,5,2,[['Alimento de prueba',300.0]]]],
        'detalle':{'1':{'95':[600.0,2,[['Alimento de prueba',580.0],['Bebida sin bajas',20.0]]],'falta':[25.0,1,[['Alimento de prueba',25.0]]],'sobra':[10.0,1,[['Bebida sin bajas',10.0]]]}},
        'compensa':{'total':10.0,'n':1,'tops':[['Bebida sin bajas',10.0,[[0,-10.0],[1,10.0]]]],'falta':40.0,'sobra':10.0}}
    k0={'areas':{},'flechas':[],'detalle':{},'compensa':{'total':0,'n':0,'tops':[],'falta':0,'sobra':0}}
    return {'areas':{sp.ALIMENTOS:[k0,k1],sp.OPERACION:[k0,k0]},'nombres_area':{'0':'Almacén Central','1':'Cocina','6':'Producción'}}


class Contrato(unittest.TestCase):
    def test_armar_lleva_reloj_borde_puente_y_areas(self):
        per,f,t=muestra();T=pd.Timestamp
        per=[dict(p,t0=T(str(p['desde']))+pd.Timedelta(hours=10),t1=T(str(p['hasta']))+pd.Timedelta(hours=18),dias=29.33,
                  ventanas={0:(T(str(p['desde'])),T(str(p['hasta']))+pd.Timedelta(hours=18)),20:(T(str(p['desde'])),T(str(p['hasta']))+pd.Timedelta(days=5))}) for p in per]
        extra={'reloj':'operativo','borde':pd.DataFrame({'k':[1],'fin':[30.0],'ini':[10.0],'nunca':[5.0]}),
               'puente':{'kardex':[{'k':0,'dias':34.0}],'operativo':[{'k':0,'dias':29.33}]},
               'areas':{sp.ALIMENTOS:[{'areas':{0:[1.0]},'flechas':[],'detalle':{0:{}},'compensa':{}}]},
               'nombres_area':{0:'ALMACEN CENTRAL',20:'VENTA INTERNA'},'per_operativo':per}
        P=datos.armar(per,f,t,{},extra)
        self.assertEqual(P['reloj'],'operativo');self.assertEqual(P['borde'],[[0.0,0.0,0.0],[30.0,10.0,5.0]])
        self.assertEqual(P['periodos'][0]['dias'],29.33);self.assertIn('de conteo a conteo de cada área (Venta Interna, hasta el',P['periodos'][0]['subtitulo'])
        self.assertEqual(P['periodos'][0]['cortes_op'][0][0],'Venta Interna');self.assertEqual(P['nombres_area'],{'0':'Almacén Central','20':'Venta Interna'})
        self.assertEqual(list(P['areas'][sp.ALIMENTOS][0]['areas']),['0']);self.assertEqual(P['puente']['operativo'][0]['dias'],29.33)
        import json;json.dumps(P,allow_nan=False)
        self.assertEqual(datos.armar(*muestra())['reloj'],'kardex')

    def test_reloj_se_valida_contra_el_sello(self):
        from graficos import destino_producto_pieza as pieza
        ss={'_destino_producto_cache':('f',{'sello':'abc'})};fake=SimpleNamespace(session_state=ss)
        with patch.object(pieza,'st',fake):
            for v in ({'reloj':'operativo','sello':'otro'},{'reloj':'semanal','sello':'abc'},'operativo'):
                ss[pieza._K_PIEZA]={'reloj':v};pieza._reloj();self.assertNotIn(md.K_RELOJ,ss)
            ss[pieza._K_PIEZA]={'reloj':{'reloj':'operativo','sello':'abc'}};pieza._reloj();self.assertEqual(ss[md.K_RELOJ],'operativo')

    def test_volver_al_otro_reloj_no_rearma(self):
        from graficos import destino_producto_pieza as pieza
        ss={};fake=SimpleNamespace(session_state=ss,container=lambda **kw:nullcontext(),markdown=Mock())
        with patch.object(pieza,'st',fake),patch.object(md,'st',fake),patch.object(md,'_cargar',return_value=muestra()),patch.object(pieza.data,'sin_plato_relojes',return_value=None),patch.object(pieza,'_PIEZA') as comp,patch.object(datos,'armar',wraps=datos.armar) as build:
            for reloj in ('kardex','operativo','kardex','operativo'):
                ss[md.K_RELOJ]=reloj;pieza.renderizar()
                self.assertEqual(comp.call_args.kwargs['data']['reloj'],reloj)
            self.assertEqual(build.call_count,2)

    def test_renderizar_carga_el_reloj_elegido(self):
        from graficos import destino_producto_pieza as pieza
        fake=SimpleNamespace(session_state={md.K_RELOJ:'operativo'},container=lambda **kw:nullcontext(),markdown=Mock())
        with patch.object(pieza,'st',fake),patch.object(md,'st',fake),patch.object(md,'_cargar',return_value=muestra()) as load,patch.object(pieza.data,'sin_plato_relojes',return_value=None),patch.object(pieza,'_PIEZA') as comp:
            pieza.renderizar(('Prueba',));load.assert_called_once_with(('Prueba',),'operativo')
            self.assertEqual(comp.call_args.kwargs['data']['reloj'],'operativo');self.assertIs(comp.call_args.kwargs['on_reloj_change'],pieza._reloj)
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
        with patch.object(md,'_cargar',return_value=None) as load,patch.object(md,'_vacia') as vacia:pieza.renderizar(('ALIMENTOS',));load.assert_called_once_with(('ALIMENTOS',),'kardex');self.assertIn('dos cierres',vacia.call_args.args[2])

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
        js=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+base+(ROOT/'graficos/destino_flujo.js').read_text(encoding='utf-8')+(ROOT/'graficos/destino_areas.js').read_text(encoding='utf-8')+(ROOT/'graficos/destino_producto.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarProducto=function(component)')
        cls.pg.add_script_tag(content=js,type='module');cls.pg.wait_for_function('typeof montarProducto==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,ui])=>{sessionStorage.setItem("destino_producto_737",JSON.stringify(ui||{}));window.triggers=[];montarProducto({data:P,parentElement:mount,setTriggerValue:(k,v)=>triggers.push([k,v])})}',[P or payload()[0],ui]);return self.pg.locator('.dst-producto')

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

    def test_franja_es_la_cuenta_neta_y_cuadra(self):
        P,_=payload_flujo();root=self.mount(P)
        n=self.pg.evaluate('__destinoProducto.flujo.ctx().n')
        for c,v in [('ini',150),('compra',1200),('plato',670),('sinplato',100),('fin',480),('prep',150),('val',-100),('borde',0)]:self.assertAlmostEqual(n[c],v,msg=c)
        nodos=self.pg.evaluate('__destinoFlujo.nodos(__destinoProducto.P,__destinoProducto.flujo.ctx().n,"alimentos","resumen")')
        ins=sum(x['v'] for x in nodos if x['lado']=='in');outs=sum(x['v'] for x in nodos if x['lado']=='out')
        self.assertAlmostEqual(ins,1350);self.assertAlmostEqual(outs,1350)
        self.assertEqual(next(x['lado'] for x in nodos if x['id']=='val'),'out')
        self.assertIn('S/ 1,350 que había o entró',root.locator('.dstf-resumen').inner_text())
        self.assertEqual(self.pg.evaluate('triggers'),[])

    def test_franja_filtra_la_tabla_y_se_quita(self):
        P,_=payload_flujo();root=self.mount(P)
        root.locator('.dstf-segs [data-f="sel:baja"]').click()
        self.assertEqual(root.locator('tr[data-a=producto]').count(),1);self.assertEqual(self.pg.evaluate('__destinoProducto.D.visibles[0].cod'),'0000000')
        self.assertIn('«Bajas»',root.locator('[data-k=elegido]').inner_text())
        self.assertAlmostEqual(self.pg.evaluate('__destinoProducto.flujo.ctx().n.compra'),1200)
        root.locator('[data-a=quitar_sel]').click();self.assertEqual(root.locator('tr[data-a=producto]').count(),2)
        root.locator('.dstf-ley [data-f="sel:fin"]').click();root.locator('.dstf-ley [data-f="sel:fin"]').click();self.assertEqual(self.pg.evaluate('__destinoProducto.s.flujo.sel'),'')

    def test_reloj_pide_python_con_su_sello_y_nada_mas(self):
        P,_=payload_flujo();root=self.mount(P)
        root.locator('[data-a=reloj][data-v=kardex]').click();self.assertEqual(self.pg.evaluate('triggers'),[])
        root.locator('[data-a=reloj][data-v=operativo]').click()
        self.assertEqual(self.pg.evaluate('triggers'),[['reloj',{'reloj':'operativo','sello':P['sello']}]])
        self.assertTrue(root.evaluate('e=>e.classList.contains("dst-cargando")'))
        P2=dict(P,reloj='operativo');ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("destino_producto_737"))')
        root=self.mount(P2,ui);self.assertFalse(root.evaluate('e=>e.classList.contains("dst-cargando")'))
        self.assertEqual(root.locator('[data-a=reloj].on').get_attribute('data-v'),'operativo')

    def test_operativo_pasa_el_borde_solo_con_el_grupo_entero(self):
        P,_=payload_flujo();P['reloj']='operativo';P['borde']=[[0,0,0],[30,10,5]];root=self.mount(P)
        n=self.pg.evaluate('__destinoProducto.flujo.ctx().n')
        self.assertAlmostEqual(n['plato'],690);self.assertAlmostEqual(n['falt'],5);self.assertAlmostEqual(n['val'],-100)
        root.locator('[data-k=q]').fill('Alimento')
        n=self.pg.evaluate('__destinoProducto.flujo.ctx().n');self.assertAlmostEqual(n['falt'],25);self.assertAlmostEqual(n['borde'],0)

    def test_del_bruto_al_neto_cierra(self):
        P,_=payload_flujo();root=self.mount(P)
        b=self.pg.evaluate('__destinoFlujo.bruto(__destinoProducto.flujo.ctx().rows)')
        self.assertAlmostEqual(b['entrada'],1400);self.assertAlmostEqual(b['ins']['prod94'],50);self.assertAlmostEqual(b['outs']['prep'],150)
        root.locator('[data-f=abrir]').click();root.locator('[data-f="que:calculo"]').click()
        texto=root.locator('.dstf-calc').inner_text()
        for t in ('1,400','−50','1,350','QUÉ FECHA USA CADA MOVIMIENTO'):self.assertIn(t,texto)
        self.assertEqual(self.pg.evaluate('triggers'),[])

    def test_simulacion_no_toca_los_datos(self):
        P,_=payload_flujo();root=self.mount(P);antes=self.pg.evaluate('JSON.stringify(__destinoProducto.B.L)')
        root.locator('[data-f=abrir]').click();root.locator('[data-f=simular]').click()
        self.assertEqual(self.pg.evaluate('__destinoProducto.s.flujo.sel'),'falt')
        panel=root.locator('.dstf-panel').inner_text();self.assertIn('¿Y si el faltante bajara?',panel);self.assertIn('S/ 5',panel)
        self.assertIn('ESCENARIO',root.locator('.dstf-lienzo').inner_text())
        root.locator('[data-f="sim:p10"]').click();self.assertIn('S/ 3',root.locator('.dstf-sim').inner_text())
        self.assertEqual(self.pg.evaluate('JSON.stringify(__destinoProducto.B.L)'),antes)
        self.assertAlmostEqual(self.pg.evaluate('__destinoProducto.flujo.ctx().n.falt'),25)

    def test_por_area_mapa_panel_capas_matriz_y_presentar(self):
        P,_=payload_flujo();P.update(areas_prueba());root=self.mount(P)
        root.locator('[data-f=abrir]').click();root.locator('[data-f="vista:area"]').click()
        self.assertEqual(root.locator('.dsta-caja').count(),4);self.assertEqual(root.locator('.dsta-hit').count(),4)
        flecha=root.locator('.dsta-hit[data-f="asel:f:99|0|1"]')
        self.assertIn('S/ 500 · 10 líneas en 3 documentos',flecha.get_attribute('data-tip'))
        flecha.evaluate('e=>{const r=e.getBoundingClientRect();e.dispatchEvent(new PointerEvent("pointermove",{bubbles:true,composed:true,clientX:r.x+2,clientY:r.y+2}))}')
        self.assertIn('Requerimientos · Almacén central → Cocina',root.locator('.dsta-tip').inner_text())
        flecha.press('Enter');panel=root.locator('.dstf-panel').inner_text()
        for t in ('S/ 500','10 líneas en 3 documentos','Alimento de prueba','80 %'):self.assertIn(t,panel)
        root.locator('[data-f="asel:c:1|95"]').click();panel=root.locator('.dstf-panel').inner_text();self.assertIn('VENDIÓ (95)',panel);self.assertIn('580',panel)
        root.locator('[data-f="asel:1"]').click();panel=root.locator('.dstf-panel').inner_text();self.assertIn('BALANCE DEL ÁREA · COCINA',panel);self.assertIn('Almacén central (99)',panel)
        root.locator('[data-f="capa:99"]').click();self.assertEqual(root.locator('.dsta-hit').count(),2)
        root.locator('[data-f="capa:99"]').click();self.assertEqual(root.locator('.dsta-hit').count(),4)
        root.locator('[data-f=comp]').click();self.assertIn('Almacén Central −10 / Cocina +10',root.locator('.dstf-panel').inner_text())
        root.locator('[data-f="forma:matriz"]').click();self.assertEqual(root.locator('.dsta-mfila').count(),5)
        root.locator('[data-f=pres]').click();self.assertIn('PASO 1 DE 6',root.locator('.dstf-panel').inner_text());self.assertEqual(root.locator('.dsta-caja').count(),4)
        for paso in range(2,7):root.locator('.dsta-sig').click();self.assertIn(f'PASO {paso} DE 6',root.locator('.dstf-panel').inner_text())
        titulos=self.pg.evaluate('(()=>{const c=__destinoProducto.flujo.ctx(),L=__destinoAreas.disposicion(c);return __destinoAreas.pasos(c,L,__destinoAreas.flechas(c,L)).map(p=>p.titulo)})()')
        self.assertIn('Producción porciona y devuelve',titulos)
        root.locator('.dsta-sig').click();self.assertFalse(self.pg.evaluate('__destinoProducto.s.flujo.presentar'))
        self.assertEqual(self.pg.evaluate('triggers'),[])

    def test_por_area_sin_datos_lo_dice(self):
        P,_=payload_flujo();root=self.mount(P);root.locator('[data-f=abrir]').click();root.locator('[data-f="vista:area"]').click()
        self.assertIn('no se pudo calcular',root.locator('.dst-flujo').inner_text())

    def test_excel_lleva_flujo_y_por_area(self):
        P,_=payload_flujo();P.update(areas_prueba());root=self.mount(P)
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        with zipfile.ZipFile(dl.value.path()) as z:
            libro=z.read('xl/workbook.xml').decode()
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),11)
            for nombre in ('Flujo','Por área','Traslados','Compensaciones'):self.assertIn(nombre,libro)
            self.assertIn('<v>1400</v>',z.read('xl/worksheets/sheet7.xml').decode())

    def test_flujo_responsivo_sin_rotulos_encimados_y_teclado(self):
        P,_=payload_flujo();root=self.mount(P);root.locator('[data-f=abrir]').click();root.locator('[data-f="modo:desglose"]').click()
        for width in (1323,1000,844,390):
            self.pg.set_viewport_size({'width':width,'height':900});self.pg.wait_for_timeout(120)
            self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),width)
            if width>900:
                overlaps=root.locator('.dstf-rot').evaluate_all("""es=>{const rs=es.map(e=>e.getBoundingClientRect());let n=0;for(let i=0;i<rs.length;i++)for(let j=i+1;j<rs.length;j++){const a=rs[i],b=rs[j];if(a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top)n++;}return n;}""")
                self.assertEqual(overlaps,0,f'rótulos a {width}px')
                self.assertFalse(root.locator('.dstf-lienzo').evaluate('e=>/NaN|undefined/.test(e.innerHTML)'))
            else:
                self.assertEqual(root.locator('.dstf-lienzo').count(),0);self.assertTrue(root.locator('.dstf-movil').is_visible())
        self.pg.set_viewport_size({'width':1323,'height':900});self.pg.wait_for_timeout(120)
        root.locator('.dstf-rot[data-f="sel:otras"]').press('Enter')
        self.assertEqual(self.pg.evaluate('__destinoProducto.s.flujo.sel'),'otras');self.assertIn('OTRAS NOTAS',root.locator('.dstf-panel').inner_text())
        root.locator('[data-f=cerrar]').click();self.assertEqual(root.locator('.dstf-franja').count(),1)

    def test_movil_lista_plegable(self):
        P,_=payload_flujo();root=self.mount(P);self.pg.set_viewport_size({'width':390,'height':844});self.pg.wait_for_timeout(120)
        root.locator('[data-f="acc:sinplato"]').click();texto=root.locator('.dstf-movil').inner_text()
        for t in ('Faltante','Otras notas','Bajas','Más pesan'):self.assertIn(t,texto)
        self.assertEqual(root.locator('[data-f="acc:sinplato"]').get_attribute('aria-expanded'),'true')

    def test_ficha_en_soles_cierra_con_quedo(self):
        P,_=payload_flujo();root=self.mount(P)
        lineas=self.pg.evaluate('__destinoProductoDatos.soles(__destinoProducto.F,true)')
        self.assertAlmostEqual(sum(v for _,v in lineas[:-1]),lineas[-1][1])
        self.assertIn('En soles, con fechas del kardex',root.locator('.dst-soles').inner_text())

if __name__=='__main__':unittest.main(verbosity=2)
