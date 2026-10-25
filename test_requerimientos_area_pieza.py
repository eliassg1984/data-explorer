"""Requerimientos por Área: cuentas de referencia, rastro y mejoras locales (#734)."""
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

from graficos import movimientos_requerimientos as mr
from graficos import requerimientos_area_datos as datos

ROOT=Path(__file__).parent
VENT=mr.ventana_meses(pd.Timestamp('2026-07-01'))


def muestra():
    rows=[]
    def add(cod,area,fecha,q=10,val=20,doc=None,fam='ALIMENTOS',subfam='ABARROTES',**kw):
        rows.append(dict(cod=cod,prod='Producto '+cod,unid='KILOS' if cod!='0002' else 'UNIDAD',sub=area,fecha=pd.Timestamp(fecha),cant=q,valor=val,
            doc=doc or f'{cod}{len(rows):05d}',fam=fam,subfam=subfam,habitual=5.,veces=0.,exceso=0.,nuevo=False,repite_min=float('nan'),**kw))
    for i in range(155):add('0001','COCINA',pd.Timestamp('2025-07-01')+pd.Timedelta(days=i),q=10+i%3,val=20+i%3)
    for i in range(53):add('0002','BARRA',pd.Timestamp('2025-08-01')+pd.Timedelta(days=i),q=1,val=2,fam='BEBIDAS',subfam='SIN ALCOHOL')
    add('0001','COCINA','2026-06-10',q=30,val=90,doc='000000001');add('0001','COCINA','2026-06-10',q=2,val=6,doc='000000001')
    add('0002','COCINA','2026-06-10',q=3,val=9,doc='000000001',fam='BEBIDAS',subfam='SIN ALCOHOL')
    add('0001','BARRA','2026-06-11',q=5,val=10);add('0001','GASTOS','2026-06-12',q=4,val=8)
    add('0002','BARRA','2026-06-13',q=2,val=4,fam='BEBIDAS',subfam='SIN ALCOHOL');add('0003','GASTOS','2026-06-14',q=0,val=4)
    add('0004','COCINA','2026-06-15',q=-2,val=-4);add('0005','COCINA','2026-06-16',q=1,val=10)
    v=pd.DataFrame(rows);v.loc[v.doc=='000000001','veces']=3.;v.loc[v.doc=='000000001','exceso']=7.;v.loc[v.doc=='000000001','repite_min']=0
    v.loc[v.cod=='0005','nuevo']=True
    l=v[v.fecha>=pd.Timestamp('2026-06-01')].copy();v=v[v.cod!='0005'].copy()
    kx=pd.DataFrame([dict(cod=c,area=a,mes=m,ped=p,ven=ven,pro=pro,nts=nts,tra=tra,aj=aj) for c,a,m,p,ven,pro,nts,tra,aj in [
        ('0001','COCINA','2026-05',50,10,0,0,20,5),('0001','COCINA','2026-06',50,10,0,0,-18,-2),
        ('0002','COCINA','2026-06',10,-5,0,0,0,0),('0002','BARRA','2026-06',10,4,0,0,0,1),
        ('0001','GASTOS','2026-06',10,0,0,0,0,10),('0003','GASTOS','2026-06',10,0,0,0,0,10),
        ('0004','COCINA','2026-06',10,-5,0,0,0,0)]])
    return l,v,kx


def payload(kx='normal',n=0):
    l,v,k=muestra()
    if n:
        add=[]
        for i in range(n):
            r=l.iloc[0].to_dict();r.update(cod=f'{i+1000:07d}',prod=f'Producto extra {i:04d}',doc=f'{i+1000:08d}');add.append(r)
        l=pd.concat([l,pd.DataFrame(add)],ignore_index=True);v=pd.concat([v,pd.DataFrame(add)],ignore_index=True)
    return datos.armar(l,v,VENT,k if isinstance(kx,str) else kx,rango=(pd.Timestamp('2026-06-01'),pd.Timestamp('2026-07-01')),nota=('sin anulados','Los anulados no suman'))


class Contrato(unittest.TestCase):
    def test_normaliza_indices_marcas_y_unidad_del_maestro(self):
        d=pd.DataFrame(dict(F=['2026-06-01',None],D=['00001','00002'],A=[' COCINA ','BARRA'],C=['0001','0002'],P=[' A ','B'],Q=['1.234567891','2'],V=['2.123456789','3'],FAM=['ALIMENTOS',None]),index=[10,50])
        m=pd.DataFrame(dict(habitual=[3,4],veces=[2,0],exceso=[7,0],nuevo=[False,True],repite_min=[0,None]),index=d.index)
        cols=dict(fecha='F',doc='D',sub='A',cod='C',prod='P',cant='Q',valor='V',fam='FAM')
        out=datos.normalizar(d,cols,m,pd.Series({'0001':'LITROS'}));self.assertEqual(list(out.index),[10]);self.assertEqual(out.iloc[0].unid,'LITROS');self.assertEqual(out.iloc[0].repite_min,0);self.assertEqual(out.iloc[0]['cant'],1.234567891)

    def test_fuente_kardex_ausente_se_distingue_de_vacia(self):
        P=payload(kx=None);self.assertFalse(P['kardex_disponible']);Q=payload(kx=pd.DataFrame(columns=muestra()[2].columns));self.assertTrue(Q['kardex_disponible']);self.assertEqual(P['salida'],Q['salida'])
        json.dumps(P,allow_nan=False)

    def test_cache_incluye_distribucion_y_columnas_de_registro(self):
        from graficos import requerimientos_area_pieza as pieza
        l,v,k=muestra();raw=l.rename(columns={'fecha':'F','doc':'D','sub':'A','cod':'C','prod':'P','cant':'Q','valor':'V','fam':'FAM','subfam':'SF'})
        cols=dict(fecha='F',doc='D',sub='A',cod='C',prod='P',cant='Q',valor='V',fam='FAM',subfam='SF');cm=dict(fecha='REG',doc='D',sub='A',cod='C',cant='Q',valor='V')
        fake=SimpleNamespace(session_state={},container=lambda **kw:nullcontext(),markdown=Mock());fecha=Mock()
        with patch.object(pieza,'st',fake),patch.object(pieza,'_PIEZA') as comp,patch.object(mr,'pedido_y_salida',return_value=k),patch.object(mr,'marcas_de',return_value=None) as marcas,patch.object(datos,'armar',wraps=datos.armar) as build:
            pieza.renderizar(raw,raw,cols,cm,VENT,fecha=fecha);pieza.renderizar(raw,raw,cols,cm,VENT,fecha=fecha);self.assertEqual(build.call_count,1);self.assertEqual(marcas.call_args.kwargs['fecha'],'REG');self.assertEqual(fecha.call_count,2)
            raw['Q']=raw['Q'].astype(float);raw.loc[raw.index[0],'Q']+=.123;pieza.renderizar(raw,raw,cols,cm,VENT);self.assertEqual(build.call_count,2);self.assertTrue(comp.called)

    def test_ventana_calendario_termina_en_mes_del_fin_excluido(self):
        ini,fin,meses=mr.ventana_meses(pd.Timestamp('2026-06-15'));self.assertEqual(str(ini.date()),'2025-07-01');self.assertEqual(str(fin.date()),'2026-07-01');self.assertEqual(len(meses),12)


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
        from graficos import requerimientos_area_pieza as pieza
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000)
        cls.pg.route('https://req.example.test/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://req.example.test/')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}',pieza._CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/requerimientos_area.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarReq=function(component)'),type='module');cls.pg.wait_for_function('typeof montarReq==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,ui])=>{sessionStorage.setItem("mov_req_area_734",JSON.stringify(ui||{}));montarReq({data:P,parentElement:mount,setTriggerValue:()=>{throw Error("Control local pide Python")}})}',[P or payload(),ui]);return self.pg.locator('.rqa')

    def test_productos_contra_helper_en_todas_las_rutas(self):
        l,v,k=muestra()
        for source in [k,None]:
            P=payload(kx=source);self.mount(P);sal=mr.salida_por_area(source,VENT[2]) if source is not None else None
            for a,f,sf in itertools.product([None,*P['areas']],[None,*P['familias']],[None,*P['subfamilias']]):
                def cut(d):
                    for c,val in [('sub',a),('fam',f),('subfam',sf)]:
                        if val is not None:d=d[d[c]==val]
                    return d
                exp=mr.productos_requeridos(cut(l),cut(v),sal);state={key:names.index(val) if val is not None else None for key,names,val in [('area',P['areas'],a),('fam',P['familias'],f),('subfam',P['subfamilias'],sf)]}
                got=self.pg.evaluate('s=>__reqAreaDatos.calcular(__reqArea.B,s).tabla',state);rs={r['cod']:r for r in got};self.assertEqual(set(rs),set(exp.cod))
                for r in exp.to_dict('records'):
                    for key,val in r.items():
                        actual=rs[r['cod']][key]
                        if pd.isna(val):self.assertIsNone(actual)
                        elif isinstance(val,(float,int)) and not isinstance(val,bool):self.assertAlmostEqual(actual,val,places=7)
                        else:self.assertEqual(actual,val)

    def test_transferencia_positiva_por_mes_y_por_area_no_se_confunden(self):
        P=payload();self.mount(P,{'iniciado':True,'area':'COCINA'});p=self.pg.evaluate('__reqArea.D.tabla.find(r=>r.cod==="0001")');self.assertAlmostEqual(p['salio'],.22)
        self.pg.evaluate('__reqArea.s.cod="0001";__reqArea.render()');F=self.pg.evaluate('__reqArea.F');self.assertEqual(sum(r['sal'] for r in F['ms']),40);self.assertEqual(F['documentos'],156)

    def test_mediana_por_linea_dias_unicos_y_frecuencia(self):
        self.mount(ui={'iniciado':True,'area':'COCINA'});p=self.pg.evaluate('__reqArea.D.tabla.find(r=>r.cod==="0001")');l,v,_=muestra();vs=v[(v.cod=='0001')&(v['sub']=='COCINA')]
        self.assertEqual(p['tipico'],vs['cant'].median());self.assertEqual(p['dias'],vs.fecha.dt.normalize().nunique());self.assertEqual(p['grupo'],'Casi diario')

    def test_no_descarga_sin_cobertura_y_saldo_negativo(self):
        self.mount(ui={'iniciado':True,'area':None});rs={r['cod']:r for r in self.pg.evaluate('__reqArea.D.tabla')};self.assertTrue(rs['0003']['no_descarga']);self.assertIsNone(rs['0005']['salio']);self.assertIsNone(rs['0004']['salio']);p=self.pg.evaluate('()=>__reqAreaDatos.calcular(__reqArea.B,{area:__reqArea.P.areas.indexOf("COCINA")}).tabla.find(r=>r.cod==="0002")');self.assertAlmostEqual(p['salio'],-.5)

    def test_familia_y_subfamilia_se_reinician_al_cambiar_area(self):
        root=self.mount();root.locator('[data-rank=fam] tr[data-a=fam]').first.click();root.locator('[data-rank=subfam] tr[data-a=subfam]').first.click();root.locator('[data-rank=area] tr[data-a=area]').nth(1).click()
        self.assertIsNone(self.pg.evaluate('__reqArea.s.fam'));self.assertIsNone(self.pg.evaluate('__reqArea.s.subfam'))

    def test_escritura_en_shadow_root_y_estado(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('0001');self.assertEqual(q.input_value(),'0001');self.assertEqual(len(self.pg.evaluate('__reqArea.D.visibles')),1)
        self.pg.evaluate('()=>montarReq({data:__reqArea.P,parentElement:mount})');self.assertEqual(q.input_value(),'0001')

    def test_mes_y_semana_recortan_pedidos_sin_cambiar_producto(self):
        root=self.mount(ui={'iniciado':True,'area':'COCINA','cod':'0001'});cod=self.pg.evaluate('__reqArea.s.cod');root.locator('svg [data-a=mes]').last.click();self.assertEqual(len(self.pg.evaluate('__reqArea.F.ls')),157)
        self.assertTrue(all(r[7].startswith('2026-06') for r in self.pg.evaluate('__reqArea.exportar()[3].filas')));root.locator('[data-a=semana]').first.click();self.assertEqual(self.pg.evaluate('__reqArea.s.cod'),cod);self.assertIsNone(self.pg.evaluate('__reqArea.s.mes'))

    def test_documento_completo_incluye_otros_productos_fuera_del_filtro(self):
        root=self.mount(ui={'iniciado':True,'area':'COCINA','cod':'0001','q':'0001'});row=root.locator('[data-tabla=pedidos] tr').filter(has_text='000000001').first;row.click()
        self.assertEqual(root.locator('dialog [data-tabla=documento] tr').count(),3);self.assertIn('Producto 0002',root.locator('dialog').inner_text());root.locator('[data-a=cerrar]').click();self.assertFalse(root.locator('dialog').is_visible())

    def test_tablas_largas_no_pierden_filas_al_seleccionar(self):
        root=self.mount(payload(n=620));self.assertEqual(root.locator('[data-tabla=productos] tr').count(),150);root.locator('.rqa-mas:visible').first.click();antes=root.locator('[data-tabla=productos] tr').count();row=root.locator('[data-tabla=productos] tr').nth(180);cod=row.get_attribute('data-v');row.focus();row.press('Enter')
        self.assertEqual(root.locator('[data-tabla=productos] tr').count(),antes);self.assertEqual(self.pg.evaluate('__reqArea.P.productos['+cod+'][0]'),self.pg.evaluate('__reqArea.s.cod'));self.assertGreater(len(self.pg.evaluate('__reqArea.exportar()[0].filas')),600)

    def test_filtro_marcas_y_poco_respeta_clasificacion(self):
        root=self.mount(ui={'iniciado':True,'area':None});root.locator('[data-k=marca]').select_option('repite');self.assertTrue(all(r['repetidos'] for r in self.pg.evaluate('__reqArea.D.visibles')));root.locator('[data-k=marca]').select_option('');root.locator('[data-k=poco]').check();self.assertTrue(all(r['salio']<.5 and not r['no_descarga'] for r in self.pg.evaluate('__reqArea.D.visibles')))

    def test_sin_kardex_muestra_ausencia_y_excel_celdas_vacias(self):
        root=self.mount(payload(kx=None));self.assertIn('Kardex no disponible',root.inner_text());self.assertTrue(root.locator('[data-k=poco]').is_disabled());hs=self.pg.evaluate('__reqArea.exportar()');self.assertTrue(all(r[-1] is None for r in hs[2]['filas']))

    def test_orden_local_se_refleja_en_excel(self):
        root=self.mount();root.locator('[data-a=orden][data-v=prod]').click();rs=self.pg.evaluate('__reqArea.exportar()[0].filas');self.assertEqual([r[1] for r in rs],sorted(r[1] for r in rs))

    def test_excel_ocho_hojas_seis_decimales_y_codigos_texto(self):
        root=self.mount();hs=self.pg.evaluate('__reqArea.exportar()');self.assertEqual(len(hs),8);self.assertTrue(all(len(r)==len(h['cabeza']) for h in hs for r in h['filas']))
        with tempfile.TemporaryDirectory() as td:
            with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
            path=Path(td)/'r.xlsx';dl.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                from xml.etree import ElementTree as ET
                ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};count=0
                for name in z.namelist():
                    if not name.startswith('xl/worksheets/'):continue
                    tree=ET.fromstring(z.read(name));self.assertFalse(tree.findall('.//m:f',ns))
                    for node in tree.findall('.//m:v',ns):count+=1;self.assertLessEqual(len(node.text.partition('.')[2]),6)
                self.assertGreater(count,50);self.assertIn(b'0001',z.read('xl/worksheets/sheet1.xml'))

    def test_movil_scroll_y_modal(self):
        root=self.mount();self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),391)
        root.locator('[data-tabla=pedidos] tr[data-a]').first.click();self.assertLessEqual(root.locator('dialog').evaluate('e=>e.getBoundingClientRect().right'),391);self.pg.keyboard.press('Escape');self.assertFalse(root.locator('dialog').is_visible())


if __name__=='__main__':unittest.main()
