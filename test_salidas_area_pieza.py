"""Salidas por Área: ventanas, notas, comparación y mejoras nativas (#735)."""
import itertools
import json
import tempfile
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from graficos import movimientos_bajas as mb
from graficos import salidas_area_datos as datos
from graficos.drill_tablas import claves, SIN_DATO

ROOT=Path(__file__).parent
VENT=mb.ventana(pd.Timestamp('2026-07-01'))
COLS=dict(fecha='F',doc='D',cod='C',prod='P',cant='Q',valor='V',unid='U',causa='CD',area='A',tipo='T',motivo='M')
NIVELES=dict(tipo='T',causa='CG',area='A',fam='FA',subfam='SF')


def muestra():
    rows=[]
    def add(cod,fecha,q=1,v=10,doc=None,tipo='Bajas',causa='Vencido',area='COCINA',familia='ALIMENTOS',detalle=None):
        rows.append(dict(F=pd.Timestamp(fecha),D=doc or f'{len(rows):09d}',C=cod,P='Producto '+cod,Q=q,V=v,U='KILOS' if cod!='0003' else 'UNIDAD',
            T=tipo,CG=causa,A=area,FA=familia,SF='Prueba',CD=detalle if detalle is not None else causa,M='Motivo de prueba'))
    for j in range(12):add('0001',VENT[0]+pd.Timedelta(days=j*7),v=1)
    add('0001','2026-06-01',v=90);add('0002','2026-06-02',q=20,v=30,doc='000000777');add('0002','2026-06-02',q=20,v=20,doc='000000777')
    add('0003','2026-06-02',v=10,doc='000000777',tipo='Comida Personal',causa='',detalle='',area='BARRA',familia='BEBIDAS')
    add('0002','2026-06-09',q=30,v=30,causa='Rotura');add('0002','2026-06-16',q=30,v=10,causa='Rotura')
    for j in range(3):add('0003',pd.Timestamp('2026-06-01')+pd.Timedelta(days=j*7),v=10,tipo='Comida Personal',causa='',detalle='',area='BARRA',familia='BEBIDAS')
    add('0004','2024-07-01',v=10);add('0005','2026-06-03',q=0,v=0);add('0006','2026-06-04',q=-2,v=-10,causa='A');add('0006','2026-06-05',q=-1,v=-10,causa='B')
    raw=pd.DataFrame(rows);vraw=raw[raw.F>=VENT[0]].copy();l=datos.normalizar(raw,COLS,NIVELES);v=datos.normalizar(vraw,COLS,NIVELES)
    ent=pd.DataFrame([dict(cod=c,fecha=pd.Timestamp(f),cant=q) for c,f,q in [('0001','2026-05-01',100),('0002','2026-06-01',40),('0003','2026-06-01',20),('0005','2026-06-01',0),('0006','2026-06-01',-3)]])
    ant=raw.copy();ant.F=ant.F-pd.DateOffset(years=1);ant.V=ant.V*2;A=datos.normalizar(ant,COLS,NIVELES)
    return raw,l,v,ent,A


def payload(entradas='normal',anterior='normal',n=0):
    raw,l,v,e,a=muestra()
    if n:
        extras=[]
        for j in range(n):
            r=l.iloc[0].to_dict();r.update(cod=f'{j+1000:07d}',prod=f'Producto extra {j:04d}',doc=f'{j+1000:09d}');extras.append(r)
        l=pd.concat([l,pd.DataFrame(extras)],ignore_index=True);v=pd.concat([v,pd.DataFrame(extras)],ignore_index=True)
    return datos.armar(l,v,e if isinstance(entradas,str) else entradas,VENT,anterior=a if isinstance(anterior,str) else anterior,
        rango=(pd.Timestamp('2024-06-01'),pd.Timestamp('2026-07-01')),rotulo_ant='2025',sin_comparar=['causa'])


class Contrato(unittest.TestCase):
    def test_rutas_usan_clave_canonica_y_causa_real_es_distinta(self):
        raw,*_=muestra();raw.loc[0,'A']=' COCINA ';raw.loc[1,'CG']=None;l=datos.normalizar(raw,COLS,NIVELES)
        self.assertEqual(l.loc[0,'ruta_area'],claves(raw,'A').iloc[0]);self.assertEqual(l.loc[1,'ruta_causa'],claves(raw,'CG').fillna(SIN_DATO).iloc[1])
        r=l[l.cod=='0003'].iloc[0];self.assertEqual(r.causa,'Comida Personal');self.assertNotEqual(r.ruta_causa,r.causa);json.dumps(datos.armar(l,l,None,VENT),allow_nan=False)

    def test_ventana_excluye_futuro_y_conserva_parcial_inicial(self):
        _,l,v,e,a=muestra();extra=v.iloc[[0]].copy();extra.fecha=VENT[1];future=pd.concat([v,extra]);E=pd.concat([e,e.iloc[[0]].assign(fecha=VENT[1],cant=999)])
        P=datos.armar(l,future,E,VENT);Q=datos.armar(l,v,e,VENT);self.assertEqual(P['sello'],Q['sello']);self.assertEqual((VENT[1]-VENT[0]).days,364)
        w=mb.ventana(pd.Timestamp('2026-06-15'));self.assertLess(w[0],pd.Period(mb.meses_de_ventana(w)[0],'M').start_time);json.dumps(P,allow_nan=False)

    def test_anterior_y_entradas_ausentes_no_son_fuente_vacia(self):
        P=payload(entradas=None,anterior=None);self.assertFalse(P['entradas_disponibles']);self.assertFalse(P['compara'])
        _,_,_,e,a=muestra();Q=payload(entradas=e.iloc[:0],anterior=a.iloc[:0]);self.assertTrue(Q['entradas_disponibles']);self.assertTrue(Q['compara'])

    def test_cache_reconoce_distribucion_y_fecha_nativa(self):
        from graficos import salidas_area_pieza as pieza
        raw,_,_,e,_=muestra();raw['Q']=raw['Q'].astype(float);fake=SimpleNamespace(session_state={},container=lambda **kw:nullcontext(),markdown=Mock());fecha=Mock()
        with patch.object(pieza,'st',fake),patch.object(pieza,'_PIEZA') as comp,patch.object(mb,'entradas',return_value=e),patch.object(datos,'armar',wraps=datos.armar) as build:
            pieza.renderizar(raw,raw,COLS,NIVELES,VENT,fecha=fecha);pieza.renderizar(raw,raw,COLS,NIVELES,VENT,fecha=fecha);self.assertEqual(build.call_count,1)
            raw.loc[0,'Q']+=.123;pieza.renderizar(raw,raw,COLS,NIVELES,VENT,fecha=fecha);self.assertEqual(build.call_count,2);self.assertEqual(fecha.call_count,3);self.assertTrue(comp.called)


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
        from graficos import salidas_area_pieza as pieza
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000)
        cls.pg.route('https://sal.example.test/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://sal.example.test/')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}',pieza._CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/salidas_area.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarSal=function(component)'),type='module');cls.pg.wait_for_function('typeof montarSal==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,ui])=>{sessionStorage.setItem("mov_sal_area_735",JSON.stringify(ui||{}));montarSal({data:P,parentElement:mount,setTriggerValue:()=>{throw Error("Control local pide Python")}})}',[P or payload(),ui]);return self.pg.locator('.saa')

    def test_productos_contra_helper_en_todas_las_rutas(self):
        _,l,v,e,_=muestra();P=payload();self.mount(P);keys=list(NIVELES);states=[dict(zip(keys,vals)) for vals in itertools.product(*[[None,*range(len(P['rutas'][k]))] for k in keys])]
        got=self.pg.evaluate('ss=>ss.map(s=>__salAreaDatos.calcular(__salArea.B,s).tabla)',states)
        for s,js in zip(states,got):
            def cut(d):
                for k in keys:
                    if s[k] is not None:d=d[d['ruta_'+k]==P['rutas'][k][s[k]]]
                return d
            exp=mb.productos_bajas(cut(l),cut(v),e,VENT);rs={r['cod']:r for r in js};self.assertEqual(set(rs),set(exp.cod))
            for r in exp.to_dict('records'):
                for k,value in r.items():
                    if pd.isna(value):self.assertIsNone(rs[r['cod']][k])
                    elif isinstance(value,(float,int)) and not isinstance(value,bool):self.assertAlmostEqual(rs[r['cod']][k],value,places=7)
                    else:self.assertEqual(rs[r['cod']][k],value)

    def test_cronico_manda_y_mayor_nota_suma_todas_las_lineas(self):
        self.mount();rs={r['cod']:r for r in self.pg.evaluate('__salArea.D.tabla')};self.assertEqual(rs['0001']['grupo'],'Crónico');self.assertGreater(rs['0001']['mayor_nota'],.5)
        self.assertEqual(rs['0002']['grupo'],'Puntual');self.assertAlmostEqual(rs['0002']['mayor_nota'],50/90);self.assertEqual(rs['0003']['grupo'],'Ocasional')

    def test_entradas_globales_no_cambian_con_el_area_y_tasa_no_se_clampa(self):
        root=self.mount();r=self.pg.evaluate('__salArea.D.tabla.find(r=>r.cod==="0002")');self.assertEqual(r['tasa'],250)
        i=self.pg.evaluate('__salArea.P.rutas.area.indexOf("COCINA")');root.locator(f'[data-a=ruta-area][data-v="{i}"]').click();r2=self.pg.evaluate('__salArea.D.tabla.find(r=>r.cod==="0002")');self.assertEqual(r2['entro'],r['entro']);self.assertEqual(r2['tasa'],r['tasa'])

    def test_cuadros_contra_agrupaciones_y_comparacion_anual(self):
        P=payload();self.mount(P);_,l,_,_,ant=muestra()
        for j,k in enumerate(NIVELES):
            got=self.pg.evaluate('j=>__salArea.D.ranks[j]',j);cur=l.groupby('ruta_'+k)['valor'].sum();cur=cur[cur.abs()>=.5];prev=ant.groupby('ruta_'+k)['valor'].sum()
            self.assertAlmostEqual(got['total'],cur.sum());self.assertAlmostEqual(got['antes'],prev.sum());self.assertEqual(got['compara'],k!='causa')
            for r in got['filas']:
                name=P['rutas'][k][r['i']];self.assertAlmostEqual(r['v'],cur[name]);self.assertAlmostEqual(r['antes'],prev.get(name,0))

    def test_aviso_no_pinta_de_verde_caidas_y_causa_no_compara(self):
        P=payload();P['aviso']=['Pocas salidas registradas','No confundir con menos merma'];root=self.mount(P);self.assertEqual(root.locator('.saa-baja').count(),0);self.assertNotIn('vs 2025',root.locator('[data-rank=causa]').inner_text())
        hs=self.pg.evaluate('__salArea.exportar()');causas=[r for r in hs[7]['filas'] if r[0]=='Causa'];self.assertTrue(all(r[4] is None and r[5] is None for r in causas))

    def test_cero_en_ficha_no_se_convierte_en_un_sol(self):
        root=self.mount(ui={'cod':'0005'});self.assertEqual(root.locator('[data-panel=ficha] .rqa-cifras b').first.inner_text(),'S/ 0')
        rs={r['cod']:r for r in self.pg.evaluate('__salArea.D.tabla')};self.assertIsNone(rs['0004']['cant_vent']);self.assertEqual(rs['0006']['cant_vent'],-3);self.assertIsNone(rs['0006']['tasa'])

    def test_busqueda_shadow_y_estado_conservan_entrada(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('0002');self.assertEqual(q.input_value(),'0002');self.assertEqual(len(self.pg.evaluate('__salArea.D.visibles')),1)
        self.pg.evaluate('()=>montarSal({data:__salArea.P,parentElement:mount})');self.assertEqual(q.input_value(),'0002')

    def test_mes_y_semana_acotan_notas_y_preservan_producto(self):
        root=self.mount(ui={'cod':'0002'});root.locator('svg [data-a=mes]').last.click();self.assertTrue(all(r[9].startswith('2026-06') for r in self.pg.evaluate('__salArea.exportar()[3].filas')))
        root.locator('[data-a=semana]').first.click();self.assertEqual(self.pg.evaluate('__salArea.s.cod'),'0002');self.assertIsNone(self.pg.evaluate('__salArea.s.mes'));root.locator('[data-a=todo]').click();self.assertIsNone(self.pg.evaluate('__salArea.s.semana'))

    def test_nota_completa_muestra_otros_productos(self):
        root=self.mount(ui={'cod':'0002','q':'0002'});root.locator('[data-tabla=notas] tr').filter(has_text='000000777').first.click();self.assertEqual(root.locator('dialog [data-tabla=documento] tr').count(),3);self.assertIn('Producto 0003',root.locator('dialog').inner_text());self.pg.keyboard.press('Escape');self.assertFalse(root.locator('dialog').is_visible())

    def test_tablas_largas_y_eleccion_por_teclado_conservan_tanda(self):
        root=self.mount(payload(n=620));self.assertEqual(root.locator('[data-tabla=productos] tr').count(),150);root.locator('.rqa-mas:visible').first.click();row=root.locator('[data-tabla=productos] tr').nth(180);i=row.get_attribute('data-v');row.focus();row.press('Enter');self.assertEqual(root.locator('[data-tabla=productos] tr').count(),300);self.assertEqual(self.pg.evaluate('__salArea.s.cod'),self.pg.evaluate('__salArea.P.productos['+i+'][0]'))
        self.assertGreater(len(self.pg.evaluate('__salArea.exportar()[0].filas')),600)

    def test_filtros_tasa_grupos_y_orden_son_locales(self):
        root=self.mount();root.locator('[data-k=tasa]').select_option('mayor');self.assertTrue(all(r['tasa']>100 for r in self.pg.evaluate('__salArea.D.visibles')));root.locator('[data-k=tasa]').select_option('');root.locator('[data-a=grupo][data-v=Crónico]').click();self.assertTrue(all(r['grupo']=='Crónico' for r in self.pg.evaluate('__salArea.D.visibles')))
        root.locator('[data-a=grupo][data-v=Crónico]').click();root.locator('[data-a=orden][data-v=prod]').click();rs=self.pg.evaluate('__salArea.exportar()[0].filas');self.assertEqual([r[1] for r in rs],sorted(r[1] for r in rs))

    def test_fuentes_ausentes_y_clasificacion_faltante_se_muestran(self):
        P=payload(entradas=None,anterior=None);P['disponibles']['causa']=False;root=self.mount(P);self.assertIn('No se recibió esta clasificación',root.inner_text());self.assertIn('Fuente de entradas no disponible',root.inner_text());hs=self.pg.evaluate('__salArea.exportar()');self.assertTrue(all(r[-2] is None and r[-1] is None for r in hs[2]['filas']));self.assertTrue(all(t=='—' for t in root.locator('.rqa-meses tbody tr td:last-child').all_text_contents()))

    def test_excel_completo_diez_hojas_numeros_seis_decimales(self):
        root=self.mount();hs=self.pg.evaluate('__salArea.exportar()');self.assertEqual(len(hs),10);self.assertTrue(all(len(r)==len(h['cabeza']) for h in hs for r in h['filas']));self.assertTrue(hs[8]['filas'])
        with tempfile.TemporaryDirectory() as td:
            with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
            path=Path(td)/'sal.xlsx';dl.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                from xml.etree import ElementTree as ET
                ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};count=0
                for name in z.namelist():
                    if not name.startswith('xl/worksheets/'):continue
                    t=ET.fromstring(z.read(name));self.assertFalse(t.findall('.//m:f',ns))
                    for v in t.findall('.//m:v',ns):count+=1;self.assertLessEqual(len(v.text.partition('.')[2]),6)
                self.assertGreater(count,50);self.assertIn(b'0002',z.read('xl/worksheets/sheet1.xml'))

    def test_cuadros_se_pliegan_y_recuerdan_sin_perder_recorte(self):
        root=self.mount(ui={'area':'COCINA'});self.assertIn('cocina',root.locator('[data-k=ruta-resumen]').inner_text().lower());antes=self.pg.evaluate('__salArea.D.tabla');root.locator('[data-a=cuadros]').click();self.assertFalse(root.locator('[data-k=cuadros]').is_visible())
        self.pg.evaluate('()=>montarSal({data:__salArea.P,parentElement:mount})');self.assertFalse(root.locator('[data-k=cuadros]').is_visible());self.assertEqual(self.pg.evaluate('__salArea.D.tabla'),antes)
        root.locator('[data-a=cuadros]').click();self.assertTrue(root.locator('[data-k=cuadros]').is_visible())

    def test_movil_conserva_tablas_y_modal_dentro_del_ancho(self):
        root=self.mount(ui={'cod':'0002'});self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),391);root.locator('[data-tabla=notas] tr[data-a]').first.click();self.assertLessEqual(root.locator('dialog').evaluate('e=>e.getBoundingClientRect().right'),391);self.pg.keyboard.press('Escape')


if __name__=='__main__':unittest.main()
