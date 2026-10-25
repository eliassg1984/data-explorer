"""Diferencias: cálculo de referencia, ficha local y compensación entre áreas (#739)."""
import json
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch

import pandas as pd
import diferencias_ajuste as da
from graficos.ajuste import _diferencias as dif
from graficos.ajuste import _diferencias_datos as datos

ROOT=Path(__file__).parent
T0=pd.Timestamp('2026-01-01');T1=pd.Timestamp('2026-02-02')


def muestra(n=0):
    rows=[];fs={}
    def add(cod,area,q,precio=10,pistas=None,fam='ALIMENTOS'):
        i=len(rows);ps=pistas or [];ps=sorted(ps,key=lambda p:(-p['f'],da.TIPOS.index(p['t'])));p0=ps[0] if ps else {}
        x=dict(id=i,cod=cod,acod=1 if area=='COCINA' else 2,producto='Producto '+cod,area=area,familia=fam,subfamilia='Prueba',u='KG',s=20.,k=20.+q,q=q,v=q*precio,precio=precio,t0=T0,t1=T1,c0=10.,ing=15.,sal=5.,gap=0.,sin_ant=False,t0w=T0,c0w=10.,pista=p0.get('ti',''),pista_t=p0.get('t',''),pista_f=bool(p0.get('f')),n_pistas=len(ps),fuerte=any(p['f'] for p in ps),tipos=','.join(sorted({p['t'] for p in ps})),ses0='Conteo anterior',pend=0.,pend_v=0.,pend_nunca_v=0.,pend_ant_v=0.)
        rows.append(x);fs[i]=dict(ent=[('Compra',15,1)],sal=[('Ventas',5,1)],camino=[(T0,10),(T1,20)],hist=[('dic25',None,None),('ene26',q,q*precio)],usos=[dict(via='plato',n='Plato de prueba',q=1,nv=5,a='COCINA',aqui=area=='COCINA',t='PRODUCTO',d=5,ed=None)],usos_n=1,rec=None,viene=dict(porc='',uporc=None,compra=T0,raros=[]),pide=[],pend=[],perfil=dict(total=5,ventas=5,prod=0,notas=[]),pistas=ps)
    pista=lambda t,ti,f=True,r=None:dict(t=t,ti=ti,tx='Primero se registra el movimiento. Después se compara con el conteo.',f=f,dato='2 KG',r=r)
    add('0000001','COCINA',-2,pistas=[pista('area','Otra área',r=1)]);add('0000001','BARRA',2,pistas=[pista('area','Otra área',r=0)])
    add('0000002','COCINA',-3,pistas=[pista('area','Otra área',r=3)]);add('0000002','BARRA',1,pistas=[pista('area','Otra área',r=2)])
    add('0000003','COCINA',-10,pistas=[pista('prod','Producción')],fam='BEBIDAS');add('0000003','BARRA',-.9,pistas=[pista('uso','Uso posible',False)],fam='BEBIDAS')
    add('0000004','COCINA',-10,precio=0,pistas=[pista('uso','Sin precio',False)]);add('0000004','BARRA',3,precio=0)
    add('0000005','COCINA',-.0024,precio=0)
    for j in range(n):add(f'{1000+j:07d}','COCINA',-1-j/1000)
    return dict(lineas=pd.DataFrame(rows),fichas=fs,resumen=dict(hist=['dic25','ene26'],lote=None))


def payload(n=0):return datos.armar(muestra(n),{'Sesión':'cierre_prueba','Nombre':'Sesión de prueba'})|dict(familias=['ALIMENTOS','BEBIDAS'],inicial=dict(familias=[],areas=[],ver='junto',lado='fal',pista='todas',q='',foco=None))


class Contrato(unittest.TestCase):
    def test_firma_y_callback_repetido(self):
        import inspect
        self.assertEqual(len(inspect.signature(dif.vista_diferencias).parameters),6);self.assertTrue(callable(dif._vista_diferencias_legacy));ss={}
        with patch.object(dif,'st',SimpleNamespace(session_state=ss)):
            dif._ir('1|0000002','fal');dif._ir('1|0000002','fal');self.assertEqual(ss['_ajdif_salto'],2);self.assertEqual(ss[dif.K_VER],'area');self.assertEqual(ss[dif.K_BUSCAR],'')

    def test_textos_y_curvas_vienen_de_los_helpers(self):
        r=muestra();P=payload();x=r['lineas'].iloc[0];fi=r['fichas'][0];self.assertEqual(P['fichas']['0']['html']['cabecera'],dif._cabecera_ficha(x));self.assertEqual(P['fichas']['0']['html']['cuenta'],dif._cuenta_html(x,fi));self.assertEqual(P['fichas']['0']['camino'][0],[T0.isoformat(),10]);json.dumps(P,allow_nan=False)

    def test_no_muta_fuente_y_nulos_son_json_validos(self):
        r=muestra();r['lineas']['opcional']=float('nan');before=r['lineas'].copy(deep=True);P=datos.armar(r);pd.testing.assert_frame_equal(before,r['lineas']);self.assertIsNone(P['lineas'][0]['opcional']);self.assertNotIn('html',r['fichas'][0]);json.dumps(P,allow_nan=False)

    def test_cache_y_una_sesion_sin_consultas_nuevas_en_la_pieza(self):
        from graficos.ajuste import _diferencias_pieza as pieza
        ses=dict(clave='prueba',nombre='Enero',etiqueta_anio='2026');ss={dif.K_FAM:['ALIMENTOS']};fake=SimpleNamespace(session_state=ss,markdown=Mock(),info=Mock(),container=lambda **kw:nullcontext(),columns=lambda *a,**kw:(nullcontext(),nullcontext()),spinner=lambda *a,**kw:nullcontext())
        master=pd.DataFrame(dict(fecha=[T1],familia=['ALIMENTOS']))
        with patch.object(pieza,'st',fake),patch.object(dif,'sesiones_de',return_value=[ses]),patch.object(dif,'sembrar_seleccion'),patch.object(dif,'sesion_vigente',return_value=ses),patch.object(dif,'selector_sesion'),patch.object(dif,'stats_de_vista',return_value={}),patch.object(pieza.data,'diferencias_ajuste_sesion',return_value=muestra()) as fuente,patch.object(pieza,'_PIEZA') as comp,patch.object(datos,'armar',wraps=datos.armar) as build:
            pieza.renderizar(master,'fecha','familia','area','valor','producto');pieza.renderizar(master,'fecha','familia','area','valor','producto');self.assertEqual(build.call_count,1);self.assertEqual(fuente.call_args.args,('prueba',));self.assertFalse(any(k.startswith('on_') for k in comp.call_args.kwargs));self.assertEqual(comp.call_args.kwargs['data']['inicial']['familias'],['ALIMENTOS'])


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
        from graficos.ajuste import _diferencias_pieza as pieza
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000);cls.pg.route('https://dif.test.example/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://dif.test.example/')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}',pieza._CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/ajuste/diferencias.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarDif=function(component)'),type='module');cls.pg.wait_for_function('typeof montarDif==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,ui])=>{sessionStorage.setItem("ajuste_dif_739",JSON.stringify(ui||{}));montarDif({data:P,parentElement:mount,setTriggerValue:()=>{throw Error("Control local pide Python")}})}',[P or payload(),ui]);return self.pg.locator('.adf')

    def test_grupos_y_pistas_contra_referencia(self):
        self.mount();r=muestra();states=[dict(familias=f,areas=a,lado='fal',ver='junto',pista='todas',q='') for f in [[],['ALIMENTOS'],['BEBIDAS']] for a in [[],['COCINA'],['BARRA'],['COCINA','BARRA']]]
        js=self.pg.evaluate('ss=>ss.map(s=>{const d=__ajusteDifDatos.calcular(__ajusteDif.B,s);return{G:d.G,FG:[...d.FG],c:d.cobertura}})',states)
        for s,j in zip(states,js):
            lin=r['lineas'];lin=lin[lin.familia.isin(s['familias'])] if s['familias'] else lin;areas=[a for a in s['areas'] if a in set(lin.area)];lin=lin[lin.area.isin(areas)] if areas else lin;G,FG=da.agrupar_por_producto(lin,r['fichas']);self.assertEqual(j['G'],datos.valor(G));jsfg=dict(j['FG'])
            for gid,fg in FG.items():self.assertEqual(jsfg[gid]['pistas'],datos.valor(fg['pistas']));self.assertEqual(jsfg[gid]['base'],fg['base']);self.assertEqual([x['id'] for x in jsfg[gid]['partes']],[x['id'] for x in fg['partes']])
            for k,v in zip(['fal','sob','pf','ps','sin'],da.cobertura(G[~G.comp] if not G.empty else G)):self.assertAlmostEqual(j['c'][k],v)

    def test_diez_por_ciento_y_otra_area_compensada(self):
        self.mount();G=self.pg.evaluate('__ajusteDif.D.G');g=next(r for r in G if r['cod']=='0000003');self.assertEqual(g['n_pistas'],1);self.assertEqual(g['pista'],'Producción');g=next(r for r in G if r['cod']=='0000002');self.assertEqual(g['n_pistas'],0)
        comp=next(r for r in G if r['cod']=='0000001');self.assertTrue(comp['comp']);self.assertFalse(any(r['cod']=='0000001' for r in self.pg.evaluate('__ajusteDif.D.visibles')))

    def test_sin_precio_se_clasifica_por_cantidad(self):
        root=self.mount();rs=self.pg.evaluate('__ajusteDif.D.visibles');self.assertTrue(any(r['cod']=='0000004' and r['q']<0 and r['v']==0 for r in rs));self.assertIn('0.0024',root.locator('[data-k=lista]').inner_text())

    def test_formato_exacto_de_python_ties_y_cantidades_pequenas(self):
        self.mount();vals=[0.,-.0,.5,-.5,1.5,2.5,1000.5,0.015,-0.015,.0024,-.0024,.00000024,2.675,-2.675,12345.555555,1e-30]
        js=self.pg.evaluate('vs=>vs.map(v=>[__ajusteDifFormato.numero(v),__ajusteDifFormato.soles(v)])',vals)
        for v,(numero,soles) in zip(vals,js):self.assertEqual(numero,da.es(v));self.assertEqual(soles,dif._soles(v))

    def test_lista_ficha_y_pestanas_sin_python(self):
        root=self.mount();self.assertFalse(root.locator('[data-k=ficha]').is_visible());row=root.locator('tr[data-a=fila]').first;first=row.element_handle();row.click();self.assertTrue(root.locator('[data-k=ficha]').is_visible());self.assertTrue(first.evaluate('e=>e.isConnected'));root.locator('[data-a=tab][data-v="2"]').click();self.assertIn('quién lo pide',root.locator('[data-k=cuerpo]').inner_text().lower());root.locator('[data-a=tab][data-v="2"]').press('ArrowRight');self.assertIn('dónde se usa',root.locator('[data-k=cuerpo]').inner_text().lower());root.get_by_role('button',name='Cerrar la ficha',exact=True).click();self.assertFalse(root.locator('[data-k=ficha]').is_visible())

    def test_por_area_curva_y_retornar_al_producto(self):
        root=self.mount();root.locator('tr[data-a=fila][data-v="-1|0000002"]').click();root.locator('[data-a=tab][data-v="1"]').click();root.locator('[data-a=linea-parte]').first.click();self.assertEqual(self.pg.evaluate('__ajusteDif.s.ver'),'area');self.assertTrue(root.locator('[data-a=volver]').is_visible());ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("ajuste_dif_739"))');root=self.mount(ui=ui);self.assertTrue(root.locator('[data-a=volver]').is_visible());root.locator('[data-a=tab][data-v="1"]').click();self.assertEqual(root.locator('[data-k=camino] svg path').count(),1);root.locator('[data-a=volver]').click();self.assertEqual(self.pg.evaluate('__ajusteDif.s.ver'),'junto');self.assertEqual(self.pg.evaluate('__ajusteDif.F.cod'),'0000002')

    def test_compensados_abren_sus_areas_sin_cambiar_totales(self):
        root=self.mount();before=self.pg.evaluate('__ajusteDif.D.cobertura');root.locator('[data-k=comp]>summary').click();root.locator('tr[data-a=comp]').first.click();self.assertTrue(self.pg.evaluate('__ajusteDif.F.comp'));self.assertIn('compensan por completo',root.locator('[data-k=cuerpo]').inner_text());self.assertEqual(self.pg.evaluate('__ajusteDif.D.cobertura'),before)

    def test_busqueda_checkbox_y_pistas(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('0000002');self.assertEqual(q.input_value(),'0000002');self.assertEqual(len(self.pg.evaluate('__ajusteDif.D.visibles')),1);q.fill('[');self.assertEqual(len(self.pg.evaluate('__ajusteDif.D.visibles')),0);q.fill('');f=root.locator('details[data-filter=familias]');f.locator('summary').click();f.locator('input').first.check();f.locator('input').first.press('Escape');self.assertEqual(self.pg.evaluate('__ajusteDif.s.familias'),['ALIMENTOS']);root.locator('[data-k=pista]').select_option('sin');self.assertTrue(all(r['n_pistas']==0 for r in self.pg.evaluate('__ajusteDif.D.visibles')))

    def test_pop_pista_recuerda_un_rerun_y_escapa(self):
        root=self.mount();root.locator('[data-a=pista]').first.click();self.assertTrue(root.locator('dialog').is_visible());ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("ajuste_dif_739"))');root=self.mount(ui=ui);self.assertTrue(root.locator('dialog').is_visible());self.pg.keyboard.press('Escape');self.assertFalse(root.locator('dialog').is_visible());self.pg.wait_for_function('__ajusteDif.s.pop===null')

    def test_estado_local_conservado_y_foco_externo(self):
        root=self.mount();root.locator('[data-k=q]').fill('0000002');ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("ajuste_dif_739"))');self.mount(ui=ui);self.assertEqual(self.pg.evaluate('__ajusteDif.s.q'),'0000002');P=payload();P['inicial'].update(q='',ver='area',foco='1|0000003');self.mount(P,ui);self.assertEqual(self.pg.evaluate('__ajusteDif.F.cod'),'0000003')

    def test_el_mismo_salto_vuelve_a_abrir_una_ficha_cerrada(self):
        P=payload();P['inicial'].update(ver='area',foco='1|0000002');P['salto']=1;root=self.mount(P);self.assertEqual(self.pg.evaluate('__ajusteDif.F.cod'),'0000002');root.get_by_role('button',name='Cerrar la ficha',exact=True).click();ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("ajuste_dif_739"))');P['salto']=2;self.mount(P,ui);self.assertEqual(self.pg.evaluate('__ajusteDif.F.cod'),'0000002')

    def test_listas_largas_y_cambio_de_linea_no_repinta(self):
        root=self.mount(payload(330));self.assertEqual(root.locator('tr[data-a=fila]').count(),150);root.locator('[data-a=mas]').click();self.assertEqual(root.locator('tr[data-a=fila]').count(),300);first=root.locator('tr[data-a=fila]').first.element_handle();root.locator('tr[data-a=fila]').nth(5).click();self.assertTrue(first.evaluate('e=>e.isConnected'))

    def test_excel_completo_y_fuentes_sin_filtro(self):
        root=self.mount();root.locator('[data-k=q]').fill('0000002');root.locator('tr[data-a=fila]').first.click()
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        with zipfile.ZipFile(dl.value.path()) as z:
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),10);self.assertIn('0000004',z.read('xl/worksheets/sheet3.xml').decode());self.assertIn('KG',z.read('xl/worksheets/sheet7.xml').decode())

    def test_movil_modal_y_curva_sin_desborde(self):
        root=self.mount();root.locator('[data-a=ver][data-v=area]').click();root.locator('tr[data-a=fila]').first.click();root.locator('[data-a=tab][data-v="1"]').click();self.pg.set_viewport_size({'width':390,'height':844});self.pg.wait_for_function('document.querySelector("#host").shadowRoot.querySelector("[data-k=camino] svg").viewBox.baseVal.width<=400');self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),390);cajas=root.locator('.dif-dos>div').evaluate_all('es=>es.map(e=>({top:e.getBoundingClientRect().top,bottom:e.getBoundingClientRect().bottom}))');self.assertGreaterEqual(cajas[1]['top'],cajas[0]['bottom']-1);root.locator('[data-a=pista]').first.click();self.assertLessEqual(root.locator('dialog').evaluate('e=>e.getBoundingClientRect().right'),390);self.pg.keyboard.press('Escape')


if __name__=='__main__':unittest.main(verbosity=2)
