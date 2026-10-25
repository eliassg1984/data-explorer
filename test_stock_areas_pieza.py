"""Área/Familia nativo: cuentas, matriz, comparación y salto a Productos (#724)."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import analisis_stock
from graficos import inventario_areas_datos as datos
from graficos import inventario_productos as ip
from test_stock_producto_pieza import COLS, armar as muestra

ROOT=Path(__file__).parent
JS=(ROOT/'graficos/inventario_base.js').read_text(encoding='utf-8')+(ROOT/'graficos/inventario_areas.js').read_text(encoding='utf-8')
CSS=(ROOT/'graficos/inventario_areas.css').read_text(encoding='utf-8')


def payload(analisis=True):
    _,d,h,c=muestra()
    ex=d.iloc[:3].copy();ex['MOTIVO']=['Inactivo','Servicio','Área no habilitada'];ex.iloc[2,ex.columns.get_loc('Q')]=0;ex.iloc[2,ex.columns.get_loc('V')]=0
    cols={**COLS,'motivo':'MOTIVO'}
    p=datos.armar(d,ex,cols,h if analisis else None,c if analisis else None)
    return p,d,h,c,ex


class Contrato(unittest.TestCase):
    def test_precision_grano_excluidos_y_sello(self):
        p,d,h,c,ex=payload();json.dumps(p,allow_nan=False)
        self.assertEqual(len(p['filas']),len(d));self.assertEqual(len(p['excluidos']['filas']),len(ex))
        self.assertEqual(p['filas'][0][11],float(d.iloc[0].V))
        self.assertEqual(p['sello'],payload()[0]['sello'])
        d.loc[0,'V']+=.000000001
        self.assertNotEqual(p['sello'],datos.armar(d,ex,{**COLS,'motivo':'MOTIVO'},h,c)['sello'])
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_callback_valida_sello_seleccion_y_chip(self):
        from graficos import inventario_areas_pieza as pieza
        p,_,_,_,_=payload()
        pedido=dict(sello=p['sello'],areas=['COCINA'],fams=[],subs=[],chip='neg')
        ss={'_inv_areas_cache':('firma',p),'inv_areas_pieza':{'ir':pedido}}
        with patch.object(pieza.st,'session_state',ss),patch.object(pieza.inv,'_ir_a_productos') as ir:
            pieza._ir();ir.assert_called_once_with(['COCINA'],[],[],'neg')
            for cambio in [{'sello':'viejo'},{'areas':['NO EXISTE']},{'chip':'inventado'},{'areas':'COCINA'}]:
                ir.reset_mock();ss['inv_areas_pieza']['ir']={**pedido,**cambio};pieza._ir();ir.assert_not_called()


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P,cls.d,cls.h,cls.c,cls.ex=payload();cls.pw=sync_playwright().start()
        try:cls.br=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(8000)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:531px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--success:green;--danger:crimson;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarAreas=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def calc(self,s=None,P=None):
        return self.pg.evaluate('([P,s])=>{const B=sleer(P),F=__areasDatos;return F.calcular(B,{...F.inicial(P,B),...s},P.excluidos?sleer(P.excluidos):null)}',[P or self.P,s or {}])

    def mount(self,P=None):
        self.pg.evaluate('P=>{window.__inventarioAreas=undefined;window.__pedidos=[];__montarAreas({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__pedidos.push(v)})}',P or self.P)
        return self.pg.locator('.iar')

    def test_rankings_pct_y_recortes_contra_pandas(self):
        for area in ['__todas__','ALMACEN CENTRAL','COCINA']:
            for fam in [None,'ALIMENTOS']:
                s={'area':area,'fam':fam};a=self.calc(s)
                for k,col,df in [('areas','AREA',self.d),('familias','FAM',self.d if area=='__todas__' else self.d[self.d.AREA==area])]:
                    ref=df.groupby(col).V.sum().sort_values(ascending=False);pos=ref[ref>0].sum()
                    self.assertEqual({r['nombre'] for r in a[k]},set(ref.index))
                    for r in a[k]:
                        self.assertAlmostEqual(r['v'],float(ref[r['nombre']]),places=7)
                        if r['v']<0:self.assertIsNone(r['pct'])
                        else:self.assertAlmostEqual(r['pct'],r['v']/pos*100,places=7)
                l=ip.armar_listado(self.d,**{'col_'+k:v for k,v in COLS.items()},areas=[] if area=='__todas__' else [area],familias=[] if fam is None else [fam],consumo=self.c)
                self.assertAlmostEqual(a['total'],l.productos.valorizado.sum(),places=7)
                self.assertEqual(a['stock'],len(l.productos))
                for estado in ['neg','sin','alto']:self.assertEqual(a['estados'][estado],int(l.productos.estado.eq(estado).sum()))

    def test_historia_cambios_y_dias_contra_funciones_originales(self):
        for area in ['__todas__','COCINA']:
            for ref in range(len(self.h[0])):
                a=self.calc({'area':area,'ref':ref})
                d=self.d if area=='__todas__' else self.d[self.d.AREA==area]
                hist=self.h[2].reindex(pd.MultiIndex.from_frame(d[['ACOD','COD']])).fillna(0)
                por=hist.groupby(d.COD.to_numpy()).sum();top,total,n=analisis_stock.lo_que_mas_cambio(por,ref,7)
                self.assertEqual([r['cod'] for r in a['cambios']['top']],top.index.tolist())
                self.assertAlmostEqual(a['cambios']['total'],total,places=7);self.assertEqual(a['cambios']['n'],n)
                np.testing.assert_allclose(a['h'],hist.sum().tolist(),rtol=0,atol=1e-7)
                l=ip.armar_listado(self.d,**{'col_'+k:v for k,v in COLS.items()},areas=[] if area=='__todas__' else [area],consumo=self.c)
                dias=analisis_stock.dias_del_conjunto(l.productos.valorizado,l.productos.cantidad,l.productos.consumo,l.productos.precio)
                self.assertAlmostEqual(a['dias'],dias,places=7)

    def test_matriz_negativos_no_se_esconden_en_el_neto(self):
        a=self.calc({'modo':'Matriz'});M=a['matriz'];fila=next(r for r in M['filas'] if r['nombre']=='ALIMENTOS')
        for i,area in enumerate(M['areas']):
            d=self.d[(self.d.FAM=='ALIMENTOS')&(self.d.AREA==area)]
            self.assertAlmostEqual(fila['cells'][i]['v'],d.V.sum(),places=7)
            self.assertEqual(fila['cells'][i]['neg'],d.loc[d.Q<0,'COD'].nunique())
        self.assertGreater(fila['cells'][M['areas'].index('COCINA')]['neg'],0)

    def test_comparacion_por_codigo_unidad_y_diferencias(self):
        for vista in ['Familias','Productos']:
            a=self.calc({'modo':'Comparar','a':'ALMACEN CENTRAL','b':'COCINA','comparar':vista})
            for r in a['comparacion']:
                d=self.d[self.d.COD.eq(r['cod'])&self.d.UM.eq(r['um'])] if vista=='Productos' else self.d[self.d.FAM.eq(r['fam'])]
                av=d.loc[d.AREA=='ALMACEN CENTRAL','V'].sum();bv=d.loc[d.AREA=='COCINA','V'].sum()
                self.assertAlmostEqual(r['a'],av,places=7);self.assertAlmostEqual(r['b'],bv,places=7);self.assertAlmostEqual(r['delta'],bv-av,places=7)
                if vista=='Productos':self.assertAlmostEqual(r['qa'],d.loc[d.AREA=='ALMACEN CENTRAL','Q'].sum(),places=7)
            if vista=='Productos':self.assertNotIn('004',[r['cod'] for r in a['comparacion']])

    def test_navegacion_matriz_comparacion_y_salto(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=modo][data-v=Matriz]').click()
        cell=root.locator('[data-a=celda][data-area=COCINA][data-fam=ALIMENTOS]');cell.click()
        self.assertEqual(pg.evaluate('__inventarioAreas.s.area'),'COCINA');self.assertEqual(pg.evaluate('__inventarioAreas.s.fam'),'ALIMENTOS')
        root.locator('[data-a=ir][data-v=neg]').click()
        pedido=pg.evaluate('__pedidos[0]');self.assertEqual(pedido[1]['areas'],['COCINA']);self.assertEqual(pedido[1]['fams'],['ALIMENTOS'])
        root.locator('[data-a=modo][data-v=Comparar]').click();root.locator('[data-select=a]').select_option('ALMACEN CENTRAL');root.locator('[data-select=b]').select_option('COCINA')
        root.locator('[data-a=comparar][data-v=Productos]').click();self.assertTrue(pg.evaluate('__inventarioAreas.D.comparacion.length>0'))

    def test_excluidos_separados_busqueda_y_fuentes_incompletas(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=modo][data-v=Excluidos]').click()
        a=pg.evaluate('__inventarioAreas.D');self.assertEqual(len(a['excluidos']),2)
        root.locator('[data-select=motivo]').select_option('Servicio');self.assertEqual(pg.evaluate('__inventarioAreas.D.exfilas.length'),1)
        self.assertEqual(root.locator('[data-a=ir]').count(),0)
        root=self.mount(payload(False)[0]);self.assertIn('Sin historia',root.inner_text());self.assertIn('Sin datos',root.inner_text())
        self.assertTrue(root.locator('[data-a=ir][data-v=neg]').is_disabled())

    def test_excel_numerico_contexto_y_ambito(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=modo][data-v=Comparar]').click()
        with pg.expect_download() as down:root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'stock.xlsx';down.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                text=' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for word in ['Comparación','Contexto','Restaurante entero','Productos del recorte']:self.assertIn(word,text)
                self.assertIn('<v>',text);self.assertNotIn('<f>',text)

    def test_estado_teclado_y_movil(self):
        root=self.mount();pg=self.pg
        row=root.locator('[data-a=area][data-v=COCINA]');row.focus();pg.keyboard.press('Enter')
        self.assertEqual(pg.evaluate('__inventarioAreas.s.area'),'COCINA')
        pg.evaluate('()=>__montarAreas({data:__inventarioAreas.P,parentElement:document.querySelector("#montar"),setTriggerValue:()=>{}})')
        self.assertEqual(pg.evaluate('__inventarioAreas.s.area'),'COCINA')
        for selector,h in [('.iar-main',531),('.iar-analisis',575)]:self.assertEqual(root.locator(selector).evaluate('e=>Math.round(e.getBoundingClientRect().height)'),h)
        pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619})

    def test_buscar_reutiliza_calculos_y_la_referencia_sigue_su_mes(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=modo][data-v=Comparar]').click()
        pg.evaluate('window.__calculado=__inventarioAreas.cache.datos')
        root.locator('[data-input=q]').fill('pollo')
        self.assertTrue(pg.evaluate('__calculado===__inventarioAreas.cache.datos'))
        root.locator('[data-select=ref]').select_option('1')
        P=json.loads(json.dumps(self.P));P['sello']='nueva';P['meses']=P['meses'][1:];P['momentos']=P['momentos'][1:]
        for r in P['filas']:r[12]=r[12][1:]
        pg.evaluate('P=>__montarAreas({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:()=>{}})',P)
        self.assertEqual(pg.evaluate('__inventarioAreas.s.ref'),0)

    def test_un_codigo_con_unidades_distintas_no_suma_sus_cantidades(self):
        P=json.loads(json.dumps(self.P));d=self.d
        cod=P['dic']['cod'].index('001');um=P['dic']['unidad'].index('UNIDAD')
        r=next(r.copy() for r in P['filas'] if r[0]==cod);r[5]=um;P['filas'].append(r)
        a=self.calc({'modo':'Comparar','a':'ALMACEN CENTRAL','b':'COCINA','comparar':'Productos'},P)
        self.assertEqual(len([r for r in a['comparacion'] if r['cod']=='001']),2)
        self.assertEqual(set(r['um'] for r in a['comparacion'] if r['cod']=='001'),{'KILOGRAMO','UNIDAD'})
        self.assertGreater(len(d),0)


if __name__=='__main__':unittest.main(verbosity=2)
