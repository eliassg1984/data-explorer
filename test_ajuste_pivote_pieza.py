"""Períodos, árbol, unidades y exploración local de la tabla de Ajuste (#740)."""
import json
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from graficos.ajuste import _pivote as pv
from graficos.ajuste import _pivote_datos as datos
from graficos.ajuste._evolucion import periodos_ajuste

ROOT=Path(__file__).parent
COLS=('FECHA','FAMILIA','AREA','AV','PRODUCTO','AJ')


def muestra(n=0):
    rows=[]
    def add(fecha,fam,sub,prod,cod,u,q,v,area='COCINA'):
        rows.append(dict(FECHA=fecha,FAMILIA=fam,SUBFAMILIA=sub,PRODUCTO=prod,
            **{'CODIGO PRODUCTO':cod,'UNIDAD MEDIDA':u},AJ=q,AV=v,AREA=area))
    add('2025-12-02','Alimentos','Secos','Arroz','000001','KG',-2,-20)
    add('2025-12-05','Alimentos','Secos','Arroz','000001','KG',1,10,'BARRA ')
    add('2026-01-02','Alimentos','Secos','Arroz','000001','KG',3,30)
    add('2026-03-03','Alimentos','Secos','Arroz','000001','KG',0,0)
    add('2026-03-12','Alimentos','Huevos','Huevos','000002','UND',-6,-12)
    add('2025-12-30','Bebidas','Bebidas','Botella','000003','BOT',2,15,'BARRA')
    add('2026-03-19','Bebidas','Bebidas','Botella','000003','CAJA',-1,-20,'BARRA')
    add('2026-03-20',None,'Sin familia','Fuera','000004','KG',8,91)
    add('2026-03-24','Alimentos',None,'Sin subfamilia','000005','KG',1,4)
    add('2026-03-27','Alimentos','Secos',None,'000006','KG',1,5)
    add(None,'Alimentos','Secos','Sin fecha','000007','KG',2,4)
    for i in range(n):add('2026-03-03','Alimentos','Largos',f'Producto {i:04}','00'+str(10000+i),'KG',-.000001*(i+1),-.00001*(i+1))
    return pd.DataFrame(rows).assign(FECHA=lambda d:pd.to_datetime(d.FECHA))


def payload(n=0,operativo=False):
    return datos.armar(muestra(n),COLS,operativo=operativo,contexto={'Rango':'prueba'})|dict(inicial={'gran':'Mes','areas':[]})


class Contrato(unittest.TestCase):
    def test_firma_y_referencia_se_conservan(self):
        import inspect
        self.assertEqual(len(inspect.signature(pv.vista_detalle_ajuste).parameters),7)
        self.assertTrue(callable(pv._vista_detalle_ajuste_legacy))
        self.assertTrue(callable(pv._armar_tabla_pivote_ajuste))

    def test_fuente_no_muta_ni_redondea_y_codigos_son_texto(self):
        d=muestra(1);d.loc[0,'AV']=.123456789123;d.loc[1,'AV']=float('nan');antes=d.copy(deep=True)
        P=datos.armar(d,COLS);pd.testing.assert_frame_equal(d,antes)
        self.assertEqual(P['filas'][0]['v'],.123456789123);self.assertEqual(P['filas'][0]['c'],'000001')
        self.assertIsNone(P['filas'][1]['v']);self.assertEqual(len(P['filas']),11)
        self.assertEqual(P['areas'],['BARRA','COCINA']);json.dumps(P,allow_nan=False)

    def test_fechas_operativas_y_filas_sin_clasificar(self):
        P=payload(operativo=True);self.assertEqual(P['filas'][0]['m'],'2025-11')
        self.assertEqual(P['filas'][0]['d'],'2025-12-02')
        self.assertEqual(sum(not r['valida'] for r in P['filas']),3)
        self.assertEqual(P['salto'],4)

    def test_calendario_cache_y_mismo_ambito(self):
        from graficos.ajuste import _pivote_pieza as pieza
        ss={};fake=SimpleNamespace(session_state=ss,markdown=Mock(),info=Mock(),container=lambda **kw:nullcontext(),columns=lambda *a,**kw:(nullcontext(),nullcontext()))
        d=muestra()
        with patch.object(pieza,'st',fake),patch.object(pieza,'ctx_meses',return_value={}),patch.object(pieza,'rango_meses',return_value=('2025-11-01','2026-03-31')),patch.object(pieza,'recortar_meses',side_effect=lambda d,*a:d),patch.object(pieza,'selector_meses') as calendar,patch.object(pieza,'mes_operativo_activo',return_value=True),patch.object(datos,'armar',wraps=datos.armar) as build,patch.object(pieza,'_PIEZA') as comp:
            pieza.renderizar(d,*COLS);pieza.renderizar(d,*COLS)
            self.assertEqual(build.call_count,1);self.assertEqual(calendar.call_args.args,('ajf_det',{}))
            self.assertFalse(any(k.startswith('on_') for k in comp.call_args.kwargs))


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
        from graficos.ajuste import _pivote_pieza as pieza
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(5000)
        cls.pg.route('https://piv.test.example/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://piv.test.example/')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}',pieza._CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/ajuste/pivote.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarPiv=function(component)'),type='module');cls.pg.wait_for_function('typeof montarPiv==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,s=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,s])=>{sessionStorage.setItem("ajuste_pivote_740",JSON.stringify(s||{}));montarPiv({data:P,parentElement:mount,setTriggerValue:()=>{throw Error("Control local pide Python")}})}',[P or payload(),s])
        return self.pg.locator('.apv')

    def test_cada_periodo_y_producto_contra_la_cuenta_canonica(self):
        for op in [False,True]:
            P=payload(operativo=op);self.mount(P)
            states=[dict(gran=g,areas=a) for g in ['Mes','Corte'] for a in [[],['COCINA'],['BARRA'],['COCINA','BARRA']]]
            out=self.pg.evaluate('ss=>ss.map(s=>{const b=__ajustePivoteDatos.agrupar(__ajustePivote.P,s);return{periodos:b.orden,hojas:b.hojas.map(h=>({ruta:h.ruta,v:h.v,q:h.q,total:h.total}))}})',states)
            for s,j in zip(states,out):
                d=muestra().assign(AREA=lambda d:d.AREA.str.strip())
                if s['areas']:d=d[d.AREA.isin(s['areas'])]
                dp,o=periodos_ajuste(d,'FECHA',s['gran'],operativo=op)
                w,ps=pv._armar_tabla_pivote_ajuste(dp.dropna(subset=['FAMILIA','SUBFAMILIA','PRODUCTO']),o,'FAMILIA','SUBFAMILIA','PRODUCTO','AJ','AV')
                self.assertEqual(j['periodos'],[dict(k=p['clave'],etq=p['label'],anio=p['anio']) for p in ps])
                ref={tuple(r[c] for c in ['FAMILIA','SUBFAMILIA','PRODUCTO']):r for r in w.to_dict('records')}
                self.assertEqual(set(tuple(h['ruta']) for h in j['hojas']),set(ref))
                for h in j['hojas']:
                    r=ref[tuple(h['ruta'])];self.assertAlmostEqual(h['total'],r['tot_ajv'])
                    for i,p in enumerate(ps):self.assertAlmostEqual(h['v'][i],r[p['field_ajv']]);self.assertAlmostEqual(h['q'][i],r[p['field_aj']])

    def test_cero_y_sin_conteo_son_distintos(self):
        root=self.mount();root.locator('[data-a=nivel][data-v="2"]').click()
        arroz=root.locator('tbody tr').filter(has_text='Arroz');self.assertIn('S/ 0',arroz.inner_text());self.assertIn('—',arroz.inner_text())
        self.assertEqual(self.pg.evaluate('__ajustePivote.B.orden.length'),4)

    def test_unidades_distintas_no_se_suman_en_pantalla_ni_comparacion(self):
        root=self.mount();self.assertIn('varias unidades',root.locator('tfoot').inner_text())
        h=self.pg.evaluate('(()=>{const h=__ajustePivote.D.hojas.find(h=>h.nombre==="Botella");return __ajustePivoteDatos.comparar(h,__ajustePivote.B.orden,"2025-12","2026-03")})()')
        self.assertIsNone(h['cantidad']);self.assertEqual(h['delta'],-35)

    def test_sin_columna_cantidad_no_se_inventa_un_cero(self):
        P=datos.armar(muestra().drop(columns='AJ'),(*COLS[:-1],None))
        root=self.mount(P);self.assertEqual(self.pg.evaluate('__ajustePivote.s.modo'),'soles')
        self.assertTrue(root.locator('[data-k=modo]').is_disabled())
        self.assertEqual(root.locator('td>small').count(),0)
        self.assertTrue(self.pg.evaluate('__ajustePivote.D.hojas.every(h=>__ajustePivoteDatos.comparar(h,__ajustePivote.B.orden,"2025-12","2026-03")?.cantidad==null)'))

    def test_filtros_busqueda_y_detalle_sin_recrear_tabla(self):
        root=self.mount();root.locator('[data-k=q]').fill('000001');self.pg.wait_for_function('__ajustePivote.D.hojas.length===1')
        root.locator('[data-a=nivel][data-v="2"]').click();row=root.locator('[data-k=tabla] tbody tr').filter(has_text='Arroz');row.evaluate('e=>e.__marca=1');row.locator('[data-a=ficha]').click()
        self.assertEqual(row.evaluate('e=>e.__marca'),1);self.assertIn('000001',root.locator('[data-k=ficha]').inner_text());self.assertTrue(root.locator('svg').is_visible())
        root.locator('[data-a=cerrar]').click();self.assertEqual(root.locator('[data-k=ficha]').inner_text(),'')

    def test_area_grano_y_estado_tras_rerun(self):
        root=self.mount();root.locator('[data-a=gran][data-v=Corte]').click();root.locator('.apv-areas summary').click();root.locator('input[value=COCINA]').check();self.assertEqual(self.pg.evaluate('__ajustePivote.s.areas'),['COCINA'])
        self.pg.evaluate('montarPiv({data:__ajustePivote.P,parentElement:mount})');self.assertEqual(self.pg.evaluate('__ajustePivote.s.gran'),'Corte');self.assertEqual(self.pg.evaluate('__ajustePivote.s.areas'),['COCINA'])
        self.pg.evaluate('montarPiv({data:{...__ajustePivote.P,inicial:{gran:"Mes",areas:["BARRA"]}},parentElement:mount})');self.assertEqual(self.pg.evaluate('__ajustePivote.s.areas'),['BARRA'])

    def test_montaje_conserva_el_estilo_que_inserta_streamlit(self):
        self.pg.evaluate('()=>{const st=document.createElement("style");st.dataset.runtime="si";st.textContent=".apv{--prueba-runtime:ok}";mount.append(st)}')
        self.mount();self.assertEqual(self.pg.evaluate('mount.querySelectorAll("style[data-runtime]").length'),1)
        self.assertEqual(self.pg.locator('.apv').evaluate('e=>getComputedStyle(e).getPropertyValue("--prueba-runtime").trim()'),'ok')
        self.pg.evaluate('mount.querySelector("style[data-runtime]").remove()')

    def test_tandas_y_excel_con_fuentes_y_seis_decimales(self):
        root=self.mount(payload(340));root.locator('[data-a=nivel][data-v="2"]').click();self.assertEqual(root.locator('tbody tr').count(),150)
        self.pg.set_viewport_size({'width':390,'height':844})
        root.locator('.apv-scroll').evaluate('e=>{e.scrollTop=200;e.scrollLeft=100}')
        root.locator('[data-a=mas]').click();self.assertEqual(root.locator('tbody tr').count(),300)
        self.assertEqual(root.locator('.apv-scroll').evaluate('e=>[e.scrollTop,e.scrollLeft]'),[200,100])
        root.locator('[data-k=q]').fill('Producto 0000');self.pg.wait_for_function('__ajustePivote.D.hojas.length===1')
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'piv.xlsx';dl.value.save_as(p)
            with zipfile.ZipFile(p) as z:
                self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),7)
                self.assertIn('000001',z.read('xl/worksheets/sheet3.xml').decode());self.assertIn('-0.000001',z.read('xl/worksheets/sheet2.xml').decode())

    def test_movil_sin_desborde_y_detalle_legible(self):
        root=self.mount();self.pg.set_viewport_size({'width':390,'height':844});root.locator('[data-a=ficha]').first.click();self.assertTrue(root.locator('svg').is_visible())
        self.assertTrue(self.pg.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
        self.assertLessEqual(root.locator('[data-k=ficha]').bounding_box()['width'],390)
        self.assertTrue(root.locator('.apv-scroll').evaluate('e=>e.scrollWidth>e.clientWidth'))

    def test_registros_de_ficha_en_tandas_sin_limite_oculto(self):
        d=pd.concat([muestra().iloc[[0]]]*340,ignore_index=True)
        root=self.mount(datos.armar(d,COLS)|dict(inicial={'gran':'Mes','areas':[]}))
        root.locator('[data-a=ficha]').first.click();root.locator('.apv-ficha summary').click()
        self.assertEqual(root.locator('.apv-fuente-scroll tbody tr').count(),150)
        root.locator('[data-a=mas-ficha]').click();self.assertEqual(root.locator('.apv-fuente-scroll tbody tr').count(),300)
        root.locator('[data-a=mas-ficha]').click();self.assertEqual(root.locator('.apv-fuente-scroll tbody tr').count(),340)
        self.assertTrue(root.locator('.apv-ficha details').evaluate('e=>e.open'))


if __name__=='__main__':unittest.main(verbosity=2)
