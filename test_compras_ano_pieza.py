"""Vs año pasado nativo: meses espejo, efectos por producto y mejoras (#725)."""
import inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from graficos import periodo
from graficos.compras import vs_ano_datos as datos
from graficos.compras import vs_ano_pasado as vp

ROOT=Path(__file__).parent
JS=(ROOT/'graficos/compras/vs_ano.js').read_text(encoding='utf-8')
CSS=(ROOT/'graficos/compras/vs_ano.css').read_text(encoding='utf-8')
COLS=dict(prod='P',fecha='F',valor='V',cant='Q',fam='FM',sub='SUB',um='UM')


def muestra():
    rows=[]
    for year in [2023,2024,2025]:
        for month in range(1,13 if year<2025 else 4):
            for p,fam,sub,um in [('Harina','Alimentos','Secos','KILOS'),('Bebida','Bebidas','Frías','UNIDAD')]:
                if p=='Bebida' and year==2025 and month==3:continue
                for day in [10,20]:
                    rows.append(dict(P=p,F=pd.Timestamp(year,month,day),Q=2.123456789,V=(year-2020+month)*3.123456789,FM=fam,SUB=sub,UM=um,VALOR_ANO_ANTERIOR=99999999))
    for p,year,q,v in [('Sólo anterior',2024,3,33.123456789),('Sólo actual',2025,1,11.123456789),('Sin cantidad',2024,1,4),('Sin cantidad',2025,0,5)]:
        rows.append(dict(P=p,F=pd.Timestamp(year,3,20),Q=q,V=v,FM='Alimentos',SUB='Secos',UM='KILOS',VALOR_ANO_ANTERIOR=99999999))
    rows.append(dict(P='Harina',F=pd.Timestamp('2024-03-25'),Q=100,V=9999,FM='Alimentos',SUB='Secos',UM='KILOS',VALOR_ANO_ANTERIOR=99999999))
    rows.append(dict(P='Harina',F=pd.Timestamp('2025-02-15'),Q=-.123456789,V=-1.123456789,FM='Alimentos',SUB='Secos',UM='KILOS',VALOR_ANO_ANTERIOR=99999999))
    h=pd.DataFrame(rows);d=h[h.F>=pd.Timestamp('2025-03-01')].copy()
    return d,h


def payload():
    d,h=muestra();return datos.armar(d,COLS,h),d,h


def referencia(d,h,fam,ventana,agrupar):
    src=h if fam==datos.TODAS else h[h.FM==fam]
    parcial=vp._mes_parcial(src.F)
    g0=vp._mensual(src,'P','F','V','Q')
    gh=g0 if parcial is None else vp._mensual(src,'P','F','V','Q',recorte=(parcial[0]-12,parcial[1]))
    g=vp._con_ano_pasado(g0,gh)
    if ventana==periodo.HEREDA:
        fe=pd.to_datetime(d.F).dropna();g=g[(g.mes>=fe.min().to_period('M'))&(g.mes<=fe.max().to_period('M'))]
    elif len(g):
        ini,fin=periodo.ventana(ventana,g.mes.max().to_timestamp(how='end'),g.mes.min().to_timestamp())
        g=g[(g.mes>=ini.to_period('M'))&(g.mes<=fin.to_period('M'))]
    if agrupar!='Producto':
        col='FM' if agrupar=='Familia' else 'SUB';mp=src[['P',col]].drop_duplicates('P').set_index('P')[col];g=g.copy();g['grupo']=g['prod'].map(mp).fillna(g['prod'])
    return g,vp._por_item(g,'prod' if agrupar=='Producto' else 'grupo')


class Contrato(unittest.TestCase):
    def test_calendario_precision_y_sello(self):
        P,d,h=payload();json.dumps(P,allow_nan=False)
        self.assertEqual(P['sello'],datos.armar(d,COLS,h)['sello'])
        self.assertEqual(P['planes'][datos.TODAS]['parcial'],['2025-03',20])
        self.assertEqual(P['planes'][datos.TODAS]['ventanas']['3m'],['2025-01','2025-02','2025-03'])
        self.assertEqual(P['planes'][datos.TODAS]['ventanas']['Rango'],['2025-03'])
        h.loc[0,'V']+=.000000001
        self.assertNotEqual(P['sello'],datos.armar(d,COLS,h)['sello'])
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_familia_cambia_su_mes_parcial_y_no_usa_columnas_repetidas(self):
        P,d,h=payload()
        self.assertEqual(P['planes']['Bebidas']['parcial'],['2025-02',20])
        h=h.copy();h['VALOR_ANO_ANTERIOR']=0
        self.assertEqual(P['sello'],datos.armar(d,COLS,h)['sello'])
        self.assertEqual(len(inspect.signature(vp._compras_vs_ano_pasado_drill).parameters),9)

    def test_sin_historia_rango_vacio_y_columnas_opcionales(self):
        d,h=muestra();P=datos.armar(d.iloc[:0],COLS,h)
        self.assertEqual(P['planes'][datos.TODAS]['ventanas']['Rango'],[])
        P=datos.armar(d,COLS,d);self.assertEqual(P['planes'][datos.TODAS]['filas'],[])
        cols={**COLS,'fam':None,'sub':None,'um':None};P=datos.armar(d,cols,h)
        self.assertEqual(P['familias'],[]);self.assertEqual(list(P['planes'][datos.TODAS]['mapas']),['Producto'])


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P,cls.d,cls.h=payload();cls.pw=sync_playwright().start()
        try:cls.br=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(8000)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:575px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--danger:crimson;--success:green;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarVap=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def calc(self,s=None,P=None):
        return self.pg.evaluate('([P,s])=>__vapDatos.calcular(P,__vapDatos.inicial(s))',[P or self.P,s or {}])

    def mount(self,P=None):
        self.pg.evaluate('P=>{window.__comprasAno?.abort.abort();window.__comprasAno?.ro?.disconnect();window.__comprasAno=undefined;window.__requests=[];__montarVap({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__requests.push(v)})}',P or self.P)
        return self.pg.locator('.vap')

    def test_cada_familia_ventana_y_agrupacion_contra_python(self):
        for fam in [datos.TODAS,*self.P['familias']]:
            for ventana in self.P['opciones']:
                for agrup in ['Producto','Familia','Subfamilia']:
                    g,ref=referencia(self.d,self.h,fam,ventana,agrup)
                    a=self.calc(dict(fam=fam,ventana=ventana,agrupar=agrup,auto=False))
                    self.assertEqual(len(a['g']),len(g));got={r['item']:r for r in a['items']}
                    self.assertEqual(set(got),set(ref.item))
                    for r in ref.itertuples():
                        rr=got[r.item]
                        for k,col in [('v','valor'),('va','valor_aa'),('ep','ef_precio'),('ec','ef_cant')]:self.assertAlmostEqual(rr[k],float(getattr(r,col)),places=7)
                        if agrup=='Producto':
                            self.assertAlmostEqual(rr['q'],float(r.cant),places=7);self.assertAlmostEqual(rr['qa'],float(r.cant_aa),places=7)

    def test_parcial_mes_espejo_y_aa_sin_compra_actual(self):
        a=self.calc({'auto':False});items={r['item']:r for r in a['items']}
        self.assertTrue(items['Sólo anterior']['hb']);self.assertFalse(items['Sólo anterior']['ha']);self.assertEqual(items['Sólo anterior']['v'],0)
        self.assertTrue(items['Sólo actual']['ha']);self.assertFalse(items['Sólo actual']['hb'])
        # La compra grande del 25 de marzo anterior queda fuera del espejo al día 20.
        self.assertLess(items['Harina']['va'],1000)
        no=items['Sin cantidad'];self.assertEqual(no['ep'],0);self.assertAlmostEqual(no['ec'],no['delta']);self.assertEqual(no['sinBase'],1)

    def test_efectos_cierran_y_seleccion_de_mes_no_corta_tabla_por_defecto(self):
        a=self.calc({'auto':False,'meses':['2025-03']})
        self.assertAlmostEqual(a['tot']['ep']+a['tot']['ec'],a['tot']['v']-a['tot']['va'],places=7)
        self.assertEqual(len(a['tabla']),len(a['items']))
        b=self.calc({'auto':False,'meses':['2025-03'],'detalleMeses':True})
        self.assertAlmostEqual(sum(r['v'] for r in b['tabla']),a['tot']['v'],places=7)
        for corte in ['Quién','Cuándo']:
            a=self.calc({'auto':False,'corte':corte})
            self.assertAlmostEqual(sum(r['valor'] for r in a['partes']),a['delta'],places=7)

    def test_precio_y_cantidad_son_de_un_producto_y_ponderados(self):
        for modo in ['Precio','Cantidad']:
            a=self.calc({'auto':False,'agrupar':'Familia','foco':'Alimentos','modo':modo})
            self.assertEqual(len({r['p'] for r in a['gf']}),1)
            self.assertTrue(a['referencia'])
            for r in a['serie']:
                if modo=='Precio' and r['q']>0:self.assertAlmostEqual(self.pg.evaluate('r=>__vapDatos.magnitud(r,"Precio")',r),r['v']/r['q'],places=7)

    def test_cobertura_busqueda_y_fuente_no_disponible(self):
        for filtro,expected in [('Sólo actual','Sólo actual'),('Sólo anterior','Sólo anterior'),('Sin precio comparable','Sin cantidad')]:
            a=self.calc({'auto':False,'cobertura':filtro});self.assertIn(expected,[r['item'] for r in a['tabla']])
        P=datos.armar(self.d,COLS,self.d);root=self.mount(P)
        self.assertIn('No hay meses con historia comparable',root.inner_text());self.assertTrue(root.locator('[data-a=excel]').is_disabled())
        root=self.mount();pg=self.pg
        root.locator('[data-input=q]').fill('solo anterior');self.assertEqual(pg.evaluate('__comprasAno.D.tabla.map(r=>r.item)'),['Sólo anterior'])

    def test_ui_meses_multiples_foco_y_remontaje(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=todo]').click();root.locator('[data-a=mes][data-v="2025-01"]').click()
        root.locator('[data-a=mes][data-v="2025-03"]').click(modifiers=['Shift'])
        self.assertEqual(pg.evaluate('__comprasAno.s.meses'),['2025-01','2025-02','2025-03'])
        root.locator('[data-detallemeses]').check()
        root.locator('[data-input=q]').fill('Harina');root.locator('[data-a=foco]').first.focus();pg.keyboard.press('Enter')
        self.assertEqual(pg.evaluate('__comprasAno.D.foco'),'Harina')
        pg.evaluate('()=>__montarVap({data:__comprasAno.P,parentElement:document.querySelector("#montar")})')
        self.assertEqual(root.locator('[data-input=q]').input_value(),'Harina');self.assertEqual(pg.evaluate('__requests.length'),0)

    def test_excel_numerico_y_contexto(self):
        root=self.mount();pg=self.pg
        with pg.expect_download() as down:root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'ano.xlsx';down.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                text=' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for word in ['Contexto','Serie mensual','Descomposición','Efecto precio','doce meses','Meses anteriores de la serie']:self.assertIn(word,text)
                self.assertIn('<v>',text);self.assertNotIn('<f>',text)
                self.assertIn('<v>33.123457</v>',text)

    def test_remontaje_valida_familia_ante_filtro_global(self):
        root=self.mount();root.locator('[data-select=fam]').select_option('Bebidas')
        self.pg.evaluate('''()=>{const G=__comprasAno,P=structuredClone(G.P);delete P.planes.Bebidas;
          P.familias=P.familias.filter(f=>f!=='Bebidas');__montarVap({data:P,parentElement:document.querySelector('#montar')})}''')
        self.assertEqual(self.pg.evaluate('__comprasAno.s.fam'),datos.TODAS)
        self.assertTrue(self.pg.evaluate('__comprasAno.D.serie.length'))

    def test_excel_no_mezcla_cantidades_al_elegir_un_mes(self):
        self.mount()
        hojas=self.pg.evaluate('''()=>{const G=__comprasAno,P=structuredClone(G.P),p=P.planes.__todas__;
          p.filas=p.filas.filter(r=>r[1]!=='2025-03'||P.productos[r[0]]==='Harina');
          G.P=P;G.cache={};Object.assign(G.s,{auto:false,foco:null,meses:['2025-03']});
          __vapDatos.dibujar(G);return __vapDatos.exportar(G)}''')
        serie=next(h for h in hojas if h['nombre']=='Serie mensual')
        self.assertTrue(serie['filas']);self.assertTrue(all(r[3]=='' and r[4]=='' for r in serie['filas']))

    def test_negativos_cantidad_cero_y_movil(self):
        a=self.calc({'modo':'Precio','auto':False,'foco':'Sin cantidad'})
        self.assertIsNone(a['a']);self.assertIsNone(a['delta']);self.assertIsNone(a['pct'])
        self.mount();pg=self.pg
        pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619})
        self.assertEqual(pg.locator('.vap-detalle').evaluate('e=>Math.round(e.getBoundingClientRect().height)'),575)


if __name__=='__main__':unittest.main(verbosity=2)
