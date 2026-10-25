"""Detalle docs. nativo: paridad, pivote configurable y ficha completa (#726)."""
import inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from graficos.compras import documentos_datos as datos
from graficos.compras import _documentos_proveedor as anterior
from graficos.compras import _comun as comun
from graficos.compras._comun import base_normalizada, agregar_periodo

ROOT=Path(__file__).parent
JS=(ROOT/'graficos/compras/documentos.js').read_text(encoding='utf-8')
CSS=(ROOT/'graficos/compras/documentos.css').read_text(encoding='utf-8')
COLS=('PROV','PROD','Q','V','PU','U','F','DOC')


def muestra():
    filas=[
        ('PROV A','Arroz','2024-01-01','F001-0001',2,12.123456789,7,'KILOS'),
        ('PROV A','Aceite','2024-01-01','F001-0001',1,10,10,'LITROS'),
        ('PROV B','Arroz','2024-01-01','F001-0001',1,5,5,'KILOS'),
        ('PROV A','Arroz','2025-01-01','F001-0001',4,28,6,'KILOS'),
        ('PROV A','Arroz','2025-01-01','F001-0001',-1,-6,6,'KILOS'),
        ('PROV B','Azúcar','2025-01-07','B001-0002',0,8,None,'KILOS'),
        ('PROV B','Azúcar','2025-01-07','B001-0002',1,10,9,'UNIDAD'),
        ('PROV C','Sal',None,'F002-0003',1,3,3,'KILOS'),
        ('PROV C','Sin número','2025-01-10','',1,1.123456789,1,'UNIDAD'),
        ('PROV C','Sin unidad','2025-01-11',None,1,0,None,''),
    ]
    d=pd.DataFrame(filas,columns=['PROV','PROD','F','DOC','Q','V','PU','U'])
    return base_normalizada(d,*COLS)


def payload(b=None,top=None):
    b=muestra() if b is None else b
    return datos.armar(b,top if top is not None else ['PROV A','PROV B','PROV C'])


class Contrato(unittest.TestCase):
    def test_filtro_canonico_sin_escribir_widgets_de_otra_seccion(self):
        universo=['PROV A','PROV B','Otros'];clave='cp_prov'
        for estado in [{},{'cp_prov_cb::PROV A':False,'cp_prov_cb::PROV B':False},
                       {'cp_prov_cb::PROV A':False,'cp_prov_cb::PROV B':True},
                       {'cp_prov_cb::PROV A':False,'cp_prov_cb::PROV B':False,'cp_prov_cb::Otros':True}]:
            copia=dict(estado);got=datos.leer_seleccion(copia,clave,universo);self.assertEqual(copia,estado)
            with patch.object(comun,'st',SimpleNamespace(session_state=dict(estado))):
                esperado,_=comun.filtro_proveedores(clave,universo)
            self.assertEqual(got,esperado)

    def test_identidad_precision_y_firmas(self):
        b=muestra();P=payload(b);json.dumps(P,allow_nan=False)
        self.assertEqual(len(P['lineas']),len(b));self.assertEqual(P['sello'],payload(b)['sello'])
        self.assertEqual(len(inspect.signature(anterior.render_seccion).parameters),9)
        self.assertEqual(len(inspect.signature(anterior.tabla_documentos).parameters),6)
        self.assertEqual(len([d for d in P['documentos'] if d[3]=='F001-0001']),3)
        b.loc[0,'valor']+=.000000001;self.assertNotEqual(P['sello'],payload(b)['sello'])
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_ranking_acota_fuente_y_no_inventa_documentos(self):
        P=payload(top=['PROV B']);self.assertEqual([p[0] for p in P['proveedores']],['PROV B'])
        P=payload();self.assertEqual(len([d for d in P['documentos'] if not d[5]]),2)
        P=datos.armar(muestra(),['PROV A'],col_docu=False,col_punit=False)
        self.assertTrue(all(not d[5] for d in P['documentos']));self.assertTrue(all(l[6] is None for l in P['lineas']))

    def test_calendario_cronologico_multianual_y_sin_fecha(self):
        P=payload();fechas=P['fechas'];self.assertIn(None,fechas)
        for gran in datos.GRANOS:
            c=P['calendario'][gran];self.assertEqual(c['por_fecha'][fechas.index(None)],'~sinfecha')
            g=agregar_periodo(pd.DataFrame({'fecha':pd.to_datetime([f for f in fechas if f])}),gran)
            self.assertEqual(c['por_fecha'][:len(g)],g['_per_sort'].astype(str).tolist())
        for gran in ['Día','Semana']:
            c=P['calendario'][gran];self.assertNotEqual(c['por_fecha'][0],c['por_fecha'][1])
            self.assertTrue(any('2024' in t for t in c['rotulos'].values()))

    def test_cero_neto_vacio_y_documento_estable(self):
        b=muestra();b=b.iloc[:2].copy();b['valor']=[10,-10];P=payload(b)
        self.assertEqual(len(P['lineas']),2);self.assertEqual(sum(l[5] for l in P['lineas']),0)
        self.assertEqual(P['documentos'][0][0],payload(b.iloc[::-1])['documentos'][0][0])
        self.assertEqual(payload(b.iloc[:0])['lineas'],[])


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=muestra();cls.P=payload(cls.b);cls.pw=sync_playwright().start()
        try:cls.br=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(8000)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarDocs=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def calc(self,s=None,P=None):
        return self.pg.evaluate('([P,s])=>{const D=__docsDatos.calcular(P,__docsDatos.inicial(s));return {resumen:D.resumen,docs:D.docs,ficha:D.ficha}}',[P or self.P,s or {}])

    def mount(self,P=None):
        self.pg.evaluate('P=>{window.__comprasDocs?.abort.abort();window.__comprasDocs?.ro?.disconnect();window.__comprasDocs=undefined;window.__requests=[];document.querySelector("#montar").replaceChildren();__montarDocs({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__requests.push(v)})}',P or self.P)
        return self.pg.locator('.dc')

    def test_aviso_del_ranking_solo_con_misma_fuente_y_rango(self):
        self.pg.evaluate('window.__cpProv={rankData:{sello:"historia"}}')
        P=datos.armar(self.b,['PROV A','PROV B','PROV C'],contexto={'Proveedores del ranking':['PROV A','PROV B','PROV C']},rango=(pd.Timestamp('2024-01-01'),pd.Timestamp('2025-01-31')))
        self.mount(P)
        enviar='d=>window.dispatchEvent(new CustomEvent("compras-proveedores-cambio",{detail:d}))'
        for d in [dict(sello='otra',rango=P['rango'],sel=['PROV A']),dict(sello='historia',rango=['2020-01-01','2020-01-31'],sel=['PROV A']),dict(sello='historia',rango=P['rango'],sel=['PROV C','PROV B','PROV A'])]:self.pg.evaluate(enviar,d)
        self.assertEqual(self.pg.evaluate('__requests.length'),0)
        d=dict(sello='historia',rango=P['rango'],sel=['PROV A']);self.pg.evaluate(enviar,d);self.pg.evaluate(enviar,d)
        self.assertEqual(self.pg.evaluate('__requests.length'),1)
        self.assertEqual(self.pg.evaluate('__requests[0]'),['ranking',{'sello':P['sello']}])
        self.pg.evaluate('()=>__montarDocs({data:__comprasDocs.P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__requests.push(v)})')
        self.pg.evaluate(enviar,{**d,'sel':['PROV B']});self.assertEqual(self.pg.evaluate('__requests.length'),2)
        self.pg.evaluate('window.__cpProv=undefined')

    def test_resumen_filtros_y_busqueda_acentuada(self):
        for s,ref in [({},self.b),({'proveedores':['PROV B']},self.b[self.b.prov=='PROV B']),({'importe':'Negativos'},self.b[self.b.valor<0]),({'q':'azucar'},self.b[self.b['prod']=='Azúcar'])]:
            a=self.calc(s);self.assertAlmostEqual(a['resumen']['valor'],float(ref.valor.sum()),places=7)
            self.assertEqual(a['resumen']['lineas'],len(ref))
        self.assertEqual(self.calc()['resumen']['documentos'],5)
        self.assertEqual(self.calc()['resumen']['sinNumero'],2)

    def test_pivote_contra_pandas_cada_grano_y_ejes(self):
        for gran in datos.GRANOS:
            # Canonical calendario por fecha, sin unir días de años distintos.
            g=agregar_periodo(self.b.copy(),gran);mp=dict(zip(g.index,g['_per_sort'].astype(str)))
            for filas,cols in [(['Proveedor'],['Periodo']),(['Proveedor','Producto','Unidad'],['Periodo']),(['Fecha','Documento'],['Proveedor','Periodo']),([],[]),(['Producto'],[])]:
                s=dict(gran=gran,filas=filas,columnas=cols)
                got=self.pg.evaluate('''([P,s])=>{s=__docsDatos.inicial(s);const D=__docsDatos.calcular(P,s),out=[];
                  const cv=(v,f)=>f==='Proveedor'?P.proveedores[v][0]:f==='Producto'?P.productos[v]:f==='Unidad'?P.unidades[v]:f==='Documento'?P.documentos[v][0]:v;
                  function walk(n){if(!n.hijos.size){for(const [k,a] of n.celdas)out.push({r:n.camino.map((v,i)=>cv(v,s.filas[i])),c:JSON.parse(k).map((v,i)=>cv(v,s.columnas[i])),v:__docsDatos.valor(a,{campo:'Valor',aggr:'Suma'},P)});}else n.hijos.forEach(walk);}walk(D.piv.raiz);return out}''',[self.P,s])
                expected={}
                for i,r in self.b.iterrows():
                    date=datos._iso(r.fecha)
                    doc=next(d[0] for d in self.P['documentos'] if self.P['proveedores'][d[1]][0]==r.prov and self.P['fechas'][d[2]]==date and ((d[3]==str(r.docu).strip() and d[5]) or (not d[5] and r['prod'] in ['Sin número','Sin unidad'])))
                    dims={'Proveedor':r.prov,'Producto':r['prod'],'Unidad':r.um,'Fecha':date or '~sinfecha','Documento':doc,'Periodo':mp.get(i,'~sinfecha') if date else '~sinfecha'}
                    key=(tuple(dims[f] for f in filas),tuple(dims[f] for f in cols));expected[key]=expected.get(key,0)+r.valor
                self.assertEqual(len(got),len(expected))
                for a in got:self.assertAlmostEqual(a['v'],float(expected[(tuple(a['r']),tuple(a['c']))]),places=7)

    def test_cantidades_y_precios_solo_en_unidades_compatibles(self):
        vals=self.pg.evaluate('''P=>{const s=__docsDatos.inicial(),D=__docsDatos.calcular(P,s),all=D.piv.raiz.total;
          const rows=D.base.filter(l=>P.proveedores[l.prov][0]==='PROV A'&&P.productos[l.prod]==='Arroz');
          const a=__docsDatos.pivot(rows,P,s).raiz.total;
          return [__docsDatos.valor(all,{campo:'Cantidad',aggr:'Suma'},P),__docsDatos.valor(all,{campo:'Precio informado',aggr:'Media'},P),
            __docsDatos.valor(a,{campo:'Cantidad',aggr:'Suma'},P),__docsDatos.valor(a,{campo:'Precio informado',aggr:'Media'},P),__docsDatos.valor(a,{campo:'Precio medio',aggr:'Ponderado'},P)]}''',self.P)
        self.assertEqual(vals[:2],[None,None]);b=self.b[(self.b.prov=='PROV A')&(self.b['prod']=='Arroz')]
        self.assertAlmostEqual(vals[2],float(b['cant'].sum()));self.assertAlmostEqual(vals[3],float(b.punit.mean()));self.assertAlmostEqual(vals[4],float(b.valor.sum()/b['cant'].sum()))

    def test_ficha_completa_buscando_un_producto(self):
        a=self.calc({'q':'aceite'});self.assertEqual(a['resumen']['lineas'],1)
        doc=a['docs'][0];self.assertGreater(doc['completo'],doc['valor'])
        f=self.calc({'q':'aceite','doc':doc['key']})['ficha'];self.assertEqual(f['lineas'],2)
        self.assertAlmostEqual(f['valor'],doc['completo']);self.assertEqual(len(f['ls']),2)

    def test_configuracion_arrastre_orden_y_ficha_teclado(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=config]').click()
        root.locator('[data-campo=Producto]').drag_to(root.locator('.dc-eje[data-eje=columnas]'))
        self.assertIn('Producto',pg.evaluate('__comprasDocs.s.columnas'));self.assertNotIn('Producto',pg.evaluate('__comprasDocs.s.filas'))
        root.locator('[data-a=restaurar]').click();root.locator('[data-a=config]').click()
        root.locator('[data-a=modo][data-v=Documentos]').click();root.locator('[data-input=q]').fill('aceite')
        root.locator('tr[data-a=doc]').first.focus();pg.keyboard.press('Enter');self.assertEqual(pg.evaluate('__comprasDocs.D.ficha.lineas'),2)
        self.assertEqual(pg.evaluate('__requests.length'),0)

    def test_mover_al_final_y_proveedores_vacios(self):
        s=self.pg.evaluate('()=>{const s=__docsDatos.inicial();__docsDatos.mover(s,"Proveedor","filas");return s}')
        self.assertEqual(s['filas'][-1],'Proveedor')
        root=self.mount();root.locator('.dc-provs summary').click();root.locator('[data-a=provtop][data-v=Ninguno]').click()
        self.assertEqual(self.pg.evaluate('__comprasDocs.D.resumen.lineas'),0);self.assertTrue(root.locator('[data-a=excel]').is_disabled())
        root.locator('[data-a=provtop][data-v=Todos]').click();self.assertGreater(self.pg.evaluate('__comprasDocs.D.resumen.lineas'),0)

    def test_ejes_numericos_y_columnas_completas_en_excel(self):
        self.mount()
        r=self.pg.evaluate('''()=>{const G=__comprasDocs;Object.assign(G.s,{filas:['Cantidad'],columnas:['Valor'],nCols:1});
          __docsDatos.pintar(G);const H=__docsDatos.exportar(G).find(h=>h.nombre==='Tabla dinámica');return {n:G.D.piv.columnas.length,vis:G.tablas.pivot.cols.length,head:H.cabeza.length,total:G.D.piv.raiz.total.v}}''')
        self.assertEqual(r['vis'],1);self.assertGreater(r['n'],1);self.assertEqual(r['head'],r['n']+2)
        self.assertAlmostEqual(r['total'],float(self.b.valor.sum()),places=7)

    def test_remontaje_estado_y_documento_por_identidad_estable(self):
        root=self.mount();root.locator('[data-a=modo][data-v=Documentos]').click();root.locator('[data-input=q]').fill('aceite');root.locator('tr[data-a=doc]').first.click()
        key=self.pg.evaluate('__comprasDocs.s.doc');P=payload(self.b.iloc[::-1])
        self.pg.evaluate('P=>__montarDocs({data:P,parentElement:document.querySelector("#montar")})',P)
        self.assertEqual(self.pg.evaluate('__comprasDocs.s.doc'),key);self.assertEqual(root.locator('[data-input=q]').input_value(),'aceite')
        self.assertEqual(self.pg.evaluate('__comprasDocs.D.ficha.lineas'),2)
        P=payload(top=['PROV B']);self.pg.evaluate('P=>__montarDocs({data:P,parentElement:document.querySelector("#montar")})',P)
        self.assertIsNone(self.pg.evaluate('__comprasDocs.s.doc'))

    def test_excel_todas_las_columnas_ficha_y_seis_decimales(self):
        root=self.mount();root.locator('[data-a=modo][data-v=Documentos]').click();root.locator('[data-input=q]').fill('aceite');root.locator('tr[data-a=doc]').first.click()
        hojas=self.pg.evaluate('__docsDatos.exportar(__comprasDocs)');f=next(h for h in hojas if h['nombre']=='Ficha completa');self.assertEqual(len(f['filas']),2)
        with self.pg.expect_download() as d:root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'docs.xlsx';d.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                text=' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for word in ['Contexto','Tabla dinámica','Ficha completa','Rango compartido','<v>12.123457</v>']:self.assertIn(word,text)
                self.assertNotIn('<f>',text)

    def test_tandas_largas_exportacion_y_movil(self):
        b=pd.concat([self.b.iloc[:1].assign(prod=f'Producto {i:04d}',docu=f'F-{i:04d}') for i in range(540)],ignore_index=True)
        root=self.mount(payload(b));root.locator('[data-a=modo][data-v=Líneas]').click()
        t=root.locator('[data-tabla=lineas]');self.assertEqual(t.locator('tbody tr').count(),150)
        for _ in range(3):t.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}')
        self.assertGreater(t.locator('tbody tr').count(),150)
        h=self.pg.evaluate('__docsDatos.exportar(__comprasDocs)');self.assertEqual(len(next(x for x in h if x['nombre']=='Líneas filtradas')['filas']),540)
        self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),390)
        self.pg.set_viewport_size({'width':1323,'height':619});self.assertEqual(root.locator('.dc-main').evaluate('e=>Math.round(e.getBoundingClientRect().height)'),575)


if __name__=='__main__':unittest.main(verbosity=2)
