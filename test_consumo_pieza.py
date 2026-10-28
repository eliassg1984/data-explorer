"""Consumo según ventas nativo: cuenta histórica, límites de tablas, estado y
Excel (#733); la cuenta de cada porcionamiento, «Rendimiento» y la merma
esperada (#751)."""
import inspect
import json
import re
import tempfile
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from graficos import movimientos_consumo as mc
from graficos._consumo_html import _HTML

ROOT=Path(__file__).parent


def muestra(n=3):
    D=dict(periodo=dict(desde='2026-06-29',hasta='2026-07-05',grano='dia',
        finas=['2026-06-29','2026-06-30','2026-07-01','2026-07-02','2026-07-03','2026-07-04','2026-07-05'],
        meses=['2026-06-01','2026-07-01'],n_dia=[1]*7,n_dias=7),
        horas=[12,18],caminos=['receta base','porcionamiento','directo en el plato'],
        platos=[['Plato salón',False,10,'2026-07-10'],['Venta interna',True,20,None]],
        preps={'00100':['Preparación de prueba','porcionado','UNIDAD']},
        insumos={},filas=[],horas_ins={},mapa_ins={},rend={},revisar=[],porcionado={},porcs={},compras={},comprados={},
        compras_familias=['ALIMENTOS'],venta_interna=dict(pedidos=1,platos=1,nombres=['Venta interna'],produccion=[]),
        resumen=dict(costo=100,costo_nivel1=90,niveles=3,sin_maestro=0,sin_factor=0,costo_sin_convertir=0,hora_de_mesa=False))
    for i in range(n):
        c=f'{i+1:07d}';D['insumos'][c]=[f'Insumo {i:04d}','KILOS' if i%2==0 else 'UNIDAD',2.123456,'ALIMENTOS','Cocina',1,'UNIDAD']
        for pid,q in [(0,i+1.123456),(1,.25)]:
            v=[q,0,0,0,0,0,0];D['filas'].append([c,'00100',pid,'00100',pid,2,[[0,q]],[[0,q]],v,[q,0]])
        D['horas_ins'][c]=[[i+1.123456,0],[0,.25]];D['mapa_ins'][c]=[[[0,0,i+1.123456]],[[0,1,.25]]]
        D['compras'][c]=[i+2.5,10.123456,2]
    D['porcs']['0000001']={'00100':[2,3,'2026-06-01','2026-06-02',False,[['0000123','2026-06-02',10,8,4],['0000122','2026-06-01',10,8,4]]]}
    D['compras']['0099999']=[2.5,8.5,1];D['comprados']['0099999']=['Sólo comprado','LITROS','ALIMENTOS','Cocina']
    return D


def muestra_cuenta():
    """El insumo de mayor costo ('0000003') llega en julio por el corte
    porcionado '00100', con su cuenta y los porcionamientos de la ventana."""
    D=muestra()
    for f in D['filas']:
        if f[0]=='0000003':f[7]=[[1,f[7][0][1]]]
    D['rend_mes']={'0000003':{'00100':{'2026-07-01':[0.25,10.0,40.0,30.0,8.0,3,'2026-04-15','2026-07-01','ventana','90']}}}
    D['porcs_corte']={'00100':[['P3','2026-07-01','0000003',6.0,4.0,12.0,3.2],['P2','2026-06-10','0000003',8.0,6.0,18.0,4.8],
                               ['P1','2026-05-01','0000999',5.0,5.0,10.0,4.5]]}
    D['nombres']={'0000999':'Otro insumo'}
    return D


class Contrato(unittest.TestCase):
    def test_firma_publica_y_delegacion(self):
        self.assertEqual(list(inspect.signature(mc.tarjeta_consumo).parameters),['fam_sel','sub_sel','rango','fecha'])
        with patch('graficos.consumo_pieza.renderizar') as fn:
            mc.tarjeta_consumo(['ALIMENTOS'],['Cocina'],('inicio','fin'),None)
            self.assertEqual(fn.call_args.args,(['ALIMENTOS'],['Cocina'],('inicio','fin'),None))

    def test_fin_exclusivo_se_convierte_en_ultimo_dia_incluido(self):
        self.assertEqual(mc.rango_de_la_vista((pd.Timestamp('2026-06-01'),pd.Timestamp('2026-07-01'))),
            (pd.Timestamp('2026-06-01').date(),pd.Timestamp('2026-06-30').date()))

    def test_cache_reconoce_distribucion_y_conserva_adapter(self):
        from graficos import consumo_pieza as pieza
        r={'filas':pd.DataFrame({'q':[1.,2.]}),'horas':pd.DataFrame({'q':[3.]})};comp=pd.DataFrame({'cant':[1.]});D=muestra()
        fake=SimpleNamespace(session_state={},container=lambda **kw:nullcontext(),markdown=Mock(),caption=Mock(),info=Mock())
        with patch.object(pieza,'st',fake),patch.object(pieza,'_PIEZA') as component,patch.object(mc.data,'consumo_recetas_rango',return_value=r) as calc,patch.object(mc.data,'cargar',return_value=None),patch.object(mc,'compras_del_rango',return_value=comp),patch.object(mc,'recetas_editadas',return_value={}),patch.object(mc,'datos_de_la_vista',return_value=D) as adapter,patch.object(pieza.mermas_esperadas,'leer',return_value={'0000001':12.5}):
            rango=(pd.Timestamp('2026-06-01'),pd.Timestamp('2026-07-01'));fecha=Mock()
            pieza.renderizar([],['Cocina'],rango,fecha);pieza.renderizar([],[],rango,fecha)
            self.assertEqual(adapter.call_count,1);self.assertIs(component.call_args.kwargs['data']['datos'],D)
            r['filas']['q']=[2.,1.];pieza.renderizar([],[],rango,fecha);self.assertEqual(adapter.call_count,2)
            self.assertEqual(fecha.call_count,3);fake.caption.assert_called_once()
            # Regla #751: el rendimiento de la sesión va al cálculo y a la pieza, con las mermas.
            self.assertEqual(calc.call_args.kwargs['rendimiento'],'90')
            fake.session_state[pieza.K_REND]='mes';pieza.renderizar([],[],rango,fecha)
            self.assertEqual(calc.call_args.kwargs['rendimiento'],'mes')
            data=component.call_args.kwargs['data'];self.assertEqual((data['rendimiento'],data['mermas']),('mes',{'0000001':12.5}))
            fake.session_state[pieza.K_REND]='otro';pieza.renderizar([],[],rango,fecha)
            self.assertEqual(calc.call_args.kwargs['rendimiento'],'90')

    def test_rendimiento_y_merma_se_validan_en_python(self):
        from graficos import consumo_pieza as pieza
        import mermas_esperadas as me
        ss={};fake=SimpleNamespace(session_state=ss)
        with patch.object(pieza,'st',fake):
            for v,esperado in [('mes','mes'),('otro','mes'),('90','90'),(None,'90')]:
                ss[pieza.K_PIEZA]={'rendimiento':v};pieza._al_rendimiento();self.assertEqual(ss.get(pieza.K_REND),esperado)
            with patch.object(me,'poner',return_value=True) as poner:
                for v in [{'cod':'0000009','pct':10},{'cod':'0000001','pct':95},{'cod':'0000001','pct':'x'},'mal']:
                    ss[pieza.K_PIEZA]={'merma':v};pieza._al_merma({'0000001':[]})
                poner.assert_not_called()
                ss[pieza.K_PIEZA]={'merma':{'cod':'0000001','pct':12.5}};pieza._al_merma({'0000001':[]})
                ss[pieza.K_PIEZA]={'merma':{'cod':'0000001','pct':None}};pieza._al_merma({'0000001':[]})
                self.assertEqual([c.args for c in poner.call_args_list],[('0000001',12.5),('0000001',None)])
            with patch.object(me,'poner',return_value=False):
                ss[pieza.K_PIEZA]={'merma':{'cod':'0000001','pct':5}};pieza._al_merma({'0000001':[]})
                self.assertTrue(ss.get('_consumo_merma_error'))

    def test_mermas_esperadas_normaliza(self):
        import mermas_esperadas as me
        self.assertEqual(me.normalizar({' 001 ':'12.345','002':95,'003':-1,'004':'x','':5}),{'001':12.35})
        self.assertEqual(me.con({'001':5},'002',7),{'001':5.0,'002':7.0})
        self.assertEqual(me.con({'001':5},'001',None),{})
        self.assertIsNone(me.con({},'001',90));self.assertIsNone(me.con({},'',5))

    def test_datos_ausentes_no_inventan_ceros(self):
        from graficos import consumo_pieza as pieza
        fake=SimpleNamespace(session_state={},container=lambda **kw:nullcontext(),markdown=Mock(),info=Mock())
        with patch.object(pieza,'st',fake),patch.object(pieza,'_PIEZA') as component,patch.object(mc.data,'consumo_recetas_rango',return_value=None):
            pieza.renderizar(rango=(pd.Timestamp('2026-06-01'),pd.Timestamp('2026-07-01')));component.assert_not_called();fake.info.assert_called_once()


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        try:cls.br=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        from graficos import consumo_pieza as pieza
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000)
        cls.pg.route('https://consumo.example.test/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://consumo.example.test/');cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),s=document.createElement("style");s.textContent=css;sr.append(s);window.mount=document.createElement("div");sr.append(mount)}',pieza._CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+pieza._JS.replace('export default function(component)','window.montar=function(component)'),type='module');cls.pg.wait_for_function('typeof window.montar==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,D=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619})
        self.pg.evaluate('([D,ui])=>{sessionStorage.setItem("consumo_recetas_ui",JSON.stringify(ui||{}));montar({parentElement:mount,data:{datos:D},setTriggerValue:()=>{throw Error("No debe pedir Python")}})}',[D or muestra(),ui])
        return self.pg.locator('.consumo-pieza')

    def test_vectores_calendario_y_compra_contra_javascript_anterior(self):
        D=muestra();self.mount(D);ref=self.br.new_page();ref.set_content(re.search(r'<body>(.*?)<script>',_HTML,re.S).group(1))
        js=re.search(r'<script>(.*?)</script>',_HTML,re.S).group(1).replace('/*__DATOS__*/null',json.dumps(D))
        start=js.index('// ── el alto:');end=js.index('// ── las cubetas',start);js=js[:start]+js[end:]
        js+='\nwindow.__reference={UI,arbolDe,cubetas,filasCompras,horasDe,mapaDe,diasDe,semanasDe};'
        ref.add_script_tag(content=js)
        code='''([vi,cols])=>{const o=window.__reference||__consumoNative;o.UI.vi=vi;o.UI.tdCols=cols;const ar=o.arbolDe(vi);return ar.lista.map(a=>({cod:a.cod,q:a.tot,c:a.costo,cs:o.cubetas(a),dias:o.diasDe(a),horas:o.horasDe(a),mapa:o.mapaDe(a),sem:o.semanasDe(a)}))}'''
        for vi in [True,False]:
            for cols in ['total','semana','dia','mes','dsem','turno']:
                self.assertEqual(self.pg.evaluate(code,[vi,cols]),ref.evaluate(code,[vi,cols]))
        ref.close()

    def test_virtualiza_todas_las_tablas_y_exporta_mas_de_500(self):
        root=self.mount(muestra(620));self.assertEqual(root.locator('#td-filas tr').count(),150)
        for tab,tbody,expected in [('resumen','filas',620),('compras','cc-filas',621)]:
            root.locator(f'#vistas [data-v={tab}]').click();self.assertEqual(root.locator(f'#{tbody} tr').count(),150)
            for _ in range(5):
                boton=root.locator(f'#{tbody}').locator('xpath=ancestor::div[contains(@class,"tabla-wrap")]').locator('xpath=following-sibling::button').first
                if boton.is_visible():boton.click()
            self.assertEqual(root.locator(f'#{tbody} tr').count(),expected)
        hs=self.pg.evaluate('__consumoNative.exportar()');self.assertEqual(len(hs[1]['filas']),620);self.assertEqual(len(hs[2]['filas']),621)

    def test_busqueda_en_shadow_root_y_estado_al_remontar(self):
        root=self.mount();q=root.locator('#td-buscar');q.click();q.press_sequentially('Insumo 0001');self.assertEqual(q.input_value(),'Insumo 0001')
        root.locator('#td-plegar').click();self.assertEqual(self.pg.evaluate('__consumoNative.tdAbiertos.size'),0)
        self.pg.evaluate('()=>montar({parentElement:mount,data:{datos:__consumoNative.datos}})')
        self.assertEqual(q.input_value(),'insumo 0001');self.assertEqual(self.pg.evaluate('__consumoNative.tdAbiertos.size'),0)

    def test_seleccion_no_redibuja_tabla_ni_pierde_scroll(self):
        root=self.mount(muestra(230),{'vista':'resumen'});root.locator('.ccn-mas').filter(visible=True).first.click()
        root.locator('#filas').evaluate('e=>e.parentElement.parentElement.scrollTop=300')
        count=root.locator('#filas tr').count();row=root.locator('#filas tr').nth(20);cod=row.get_attribute('data-cod');row.focus();row.press('Enter')
        self.assertEqual(self.pg.evaluate('__consumoNative.UI.sel'),cod);self.assertEqual(root.locator('#filas tr').count(),count)

    def test_ficha_fuera_del_filtro_es_explicita_y_exporta_codigo(self):
        root=self.mount(ui={'vista':'resumen'});cod=self.pg.evaluate('__consumoNative.UI.sel');root.locator('#buscar').fill('no coincide')
        self.assertIn('queda fuera del filtro',root.locator('#ccn-seleccion').inner_text());hs=self.pg.evaluate('__consumoNative.exportar()');self.assertFalse(hs[1]['filas']);self.assertEqual(hs[3]['filas'][0][0],cod)

    def test_sin_venta_interna_compra_se_conserva(self):
        root=self.mount(ui={'vista':'compras'});antes=self.pg.evaluate('__consumoNative.filasCompras()');root.locator('#vi-lbl').click();despues=self.pg.evaluate('__consumoNative.filasCompras()')
        self.assertEqual([r['comp'] for r in antes],[r['comp'] for r in despues]);self.assertAlmostEqual(sum(r['usado'] for r in antes)-sum(r['usado'] for r in despues),.75)
        hs=self.pg.evaluate('__consumoNative.exportar()');self.assertTrue(all(r[4]=='Plato salón' for r in hs[4]['filas']))

    def test_cantidades_en_su_unidad_y_total_solo_monetario(self):
        root=self.mount();self.assertFalse(root.locator('#td-filas .lvt').count());root.locator('#td-val [data-x=soles]').click();self.assertEqual(root.locator('#td-filas .lvt').count(),1)
        hs=self.pg.evaluate('__consumoNative.exportar()');self.assertEqual({r[3] for r in hs[0]['filas']},{'KILOS','UNIDAD'});self.assertEqual({r[7] for r in hs[0]['filas']},{'S/'})

    def test_exporta_hijos_plegados_y_respeta_filtros_por_pestana(self):
        root=self.mount();root.locator('#td-plegar').click();root.locator('#td-buscar').fill('Insumo 0001');hs=self.pg.evaluate('__consumoNative.exportar()')
        self.assertEqual({r[1] for r in hs[0]['filas']},{'0000002'});self.assertEqual(len(hs[0]['filas']),4);self.assertEqual(len(hs[1]['filas']),3)

    def test_porcionamientos_no_confunde_conteos_y_fechas(self):
        self.mount();hs=self.pg.evaluate('__consumoNative.exportar()');h=hs[5];self.assertEqual(h['filas'][0][5:11],[2,3,'2026-06-01','2026-06-02','No','0000123'])
        self.assertTrue(all(len(r)==len(h['cabeza']) for r in h['filas']))

    def test_excel_completo_numeros_seis_decimales_codigos_texto(self):
        root=self.mount();hs=self.pg.evaluate('__consumoNative.exportar()');self.assertEqual(len(hs),9)
        self.assertTrue(all(len(r)==len(h['cabeza']) for h in hs for r in h['filas']))
        with tempfile.TemporaryDirectory() as td:
            with self.pg.expect_download() as dl:root.locator('#ccn-excel').click()
            path=Path(td)/'libro.xlsx';dl.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                from xml.etree import ElementTree as ET
                ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};numeric=0
                for name in z.namelist():
                    if not name.startswith('xl/worksheets/'):continue
                    tree=ET.fromstring(z.read(name));self.assertFalse(tree.findall('.//m:f',ns))
                    for v in tree.findall('.//m:v',ns):
                        numeric+=1;self.assertLessEqual(len(v.text.partition('.')[2]),6)
                self.assertGreater(numeric,40);self.assertIn(b'0000001',z.read('xl/worksheets/sheet1.xml'))

    def test_moviles_no_desbordan_pagina(self):
        root=self.mount();self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),391)
        for tab in ['resumen','compras','tabla']:
            root.locator(f'#vistas [data-v={tab}]').click();self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),391)

    def test_estado_corrupto_se_normaliza(self):
        root=self.mount(ui={'vista':'otro','modo':'otro','tdCols':'otro','tdVal':'otro','abiertos':'mal','tdTxt':3})
        self.assertEqual(self.pg.evaluate('__consumoNative.UI.vista'),'tabla');self.assertTrue(root.locator('#td-filas tr').count())

    def test_familias_inexistentes_se_limpian_aun_con_pestana_oculta(self):
        self.mount(ui={'vista':'compras','tdFam':'Ya no existe','famSel':'Ya no existe'})
        hs=self.pg.evaluate('__consumoNative.exportar()');self.assertEqual(len(hs[1]['filas']),3);self.assertGreater(len(hs[0]['filas']),3)

    def test_expandir_por_teclado_despues_de_primera_tanda_conserva_foco(self):
        root=self.mount(muestra(230));root.locator('.ccn-mas:visible').first.click()
        tr=root.locator('#td-filas tr[data-k]').nth(180);key=tr.get_attribute('data-k');tr.focus();tr.press('Enter')
        self.assertEqual(root.locator(f'tr[data-k="{key}"]').get_attribute('aria-expanded'),'true')
        self.assertEqual(root.evaluate('e=>e.getRootNode().activeElement?.getAttribute("data-k")'),key)

    # ── regla #751 ──
    def mount2(self,D,extra=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619})
        self.pg.evaluate('([D,extra,ui])=>{sessionStorage.setItem("consumo_recetas_ui",JSON.stringify(ui||{}));window.__req=[];montar({parentElement:mount,data:{datos:D,...extra},setTriggerValue:(...v)=>__req.push(v)})}',[D,extra or {},ui])
        return self.pg.locator('.consumo-pieza')

    def test_cuenta_del_corte_y_de_donde_sale(self):
        root=self.mount2(muestra_cuenta(),{'rendimiento':'90','mermas':{'0000003':10}})
        cu=self.pg.evaluate('()=>{const n=__consumoNative,a=n.A().ins.get("0000003");return n.cuentaCorte("0000003",a.preps.get("00100"))}')
        q=3.123456+.25;self.assertAlmostEqual(cu['kg'],q,places=6);self.assertAlmostEqual(cu['und'],q/.25,places=6);self.assertEqual(len(cu['lista']),3)
        t=root.locator('.porcs.cuenta').inner_text()
        for s in ['jul 2026: 13.5 und × 0.25 = 3.37 kg','De dónde sale 0.25 kg por und','10.0 ÷ 40.0 = 0.25','Los 2 que salieron de Insumo 0002 le pusieron',
                  'El otro salió de Otro insumo','El último de Insumo 0002, del 1 jul (N° P3)','Merma real 20.0 %','Con 10 %']:
            self.assertIn(s,t)
        mm=self.pg.evaluate('()=>{const n=__consumoNative,a=n.A().ins.get("0000003");return n.mermaDe([n.cuentaCorte("0000003",a.preps.get("00100"))])}')
        self.assertAlmostEqual(mm['real'],.2,places=9);self.assertAlmostEqual(mm['std'],q*.8/.9,places=9);self.assertAlmostEqual(mm['dif'],q-q*.8/.9,places=9)

    def test_ver_porcionamientos_con_sus_kilos(self):
        root=self.mount2(muestra_cuenta());self.assertFalse(root.locator('.porcs-t').count())
        root.locator('[data-porcs]').click();filas=root.locator('.porcs-t tbody tr')
        self.assertEqual(filas.count(),4);self.assertIn('Otro insumo',filas.nth(2).inner_text())
        self.assertIn('10.0',filas.nth(3).inner_text());self.assertIn('0.25',filas.nth(3).inner_text())
        self.assertEqual(self.pg.evaluate('__req'),[])

    def test_rendimiento_y_merma_piden_a_python(self):
        root=self.mount2(muestra_cuenta(),{'rendimiento':'90'})
        self.assertEqual(root.locator('#rend-seg [aria-pressed=true]').inner_text(),'90 días')
        root.locator('#rend-seg [data-r="90"]').click();self.assertEqual(self.pg.evaluate('__req'),[])
        root.locator('#rend-seg [data-r=mes]').click();root.locator('#rend-seg [data-r=mes]').click(force=True)
        self.assertEqual(self.pg.evaluate('__req'),[['rendimiento','mes']])
        for valor,esperado in [('12','{"cod":"0000003","pct":12}'),('','{"cod":"0000003","pct":null}'),('95',None)]:
            self.mount2(muestra_cuenta(),{'rendimiento':'mes'});i=root.locator('input[data-merma]').first
            i.fill(valor);i.dispatch_event('change')
            req=self.pg.evaluate('__req.map(r=>r[0]+":"+JSON.stringify(r[1]))')
            self.assertEqual(req,[] if esperado is None else ['merma:'+esperado])
        self.assertEqual(root.locator('#rend-seg [aria-pressed=true]').inner_text(),'Último mes')

    def test_metodo_corto_compra_arriba_y_nombres(self):
        root=self.mount2(muestra_cuenta())
        self.assertEqual(root.locator('#metodo-flujo .paso').count(),5)
        palabras=len(root.locator('#metodo').evaluate('e=>e.textContent').split());self.assertLess(palabras,300)
        self.assertIn('masa',root.locator('#vi-lbl').get_attribute('title'))
        self.assertEqual(root.locator('#vistas button').all_inner_texts()[:2],['Insumo › plato','Por insumo'])
        self.assertIn('Consumo teórico',root.locator('#ccn-seleccion').inner_text())
        comp=self.pg.evaluate('__consumoNative.filasCompras().filter(r=>r.comp>0).reduce((a,r)=>a+r.sComp,0)')
        self.assertEqual(root.locator('#k-comp').inner_text(),'S/ '+f'{comp:,.0f}')
        self.assertIn('ninguna venta',root.locator('#k-comp-sub').inner_text())
        self.assertFalse(root.locator('.barra').count());self.assertEqual(root.locator('.barra-llega').count(),2)

    def test_ficha_con_la_cuenta_y_excel_de_rendimientos(self):
        root=self.mount2(muestra_cuenta(),{'mermas':{'0000003':10}},{'vista':'resumen','sel':'0000003'})
        t=root.locator('#detalle').inner_text()
        for s in ['13.5 und × 0.25 kg = 3.37 kg','0.25 = 10.0 kg ÷ 40.0 und','Últimos 90 días','Merma real 20.0 %']:self.assertIn(s,t)
        hs=self.pg.evaluate('__consumoNative.exportar()');h=hs[6]
        self.assertEqual(h['nombre'],'Rendimientos');self.assertEqual(len(h['filas']),1);fila=dict(zip(h['cabeza'],h['filas'][0]))
        self.assertAlmostEqual(fila['Merma real'],.2,places=9);self.assertEqual(fila['Merma esperada %'],10)
        self.assertIn('90 días',dict(hs[-1]['filas'])['Rendimiento'])


if __name__=='__main__':unittest.main()
