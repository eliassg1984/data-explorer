"""Movimientos por período: cifras originales e interacción nativa (#722)."""
import datetime as dt
import inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd

from graficos import movimientos_periodo as mp
from graficos import movimientos_periodo_datos as datos

ROOT = Path(__file__).parent
JS = (ROOT/'graficos/movimientos_periodo.js').read_text(encoding='utf-8')
CSS = (ROOT/'graficos/movimientos_periodo.css').read_text(encoding='utf-8')
COLS = dict(fecha='F',doc='D',area='A',estado='E',fam='FM',prod='P',cant='Q',val='V',tipo='T',unid='U',causa='C')
RANGO = (pd.Timestamp('2025-01-02'),pd.Timestamp('2025-04-16'))


def muestra():
    filas = []
    for y in [2023,2024,2025]:
        for i, f in enumerate(pd.date_range(f'{y}-01-01',f'{y}-04-17',freq='3D')):
            for j in range(2):
                filas.append(dict(F=f+pd.Timedelta(hours=9+j),D=f'{y}-{i:04}',A=['Cocina','Cava','Barra','Almacén','Personal'][i%5],
                                  E='ANULADO' if i%17==0 else 'GENERADO' if i%19==0 else 'PROCESADO',
                                  FM=['Comida','Bebida'][i%2],P=f'Producto {i%27:02}',Q=(i+1)*.123456789,
                                  V=(i+1)*(j+1)*1.23456789,T=['Bajas','Uso en el área','Comida personal'][i%3],
                                  U='KILOS' if j==0 else 'UNIDAD',C=['Vencimiento','Mala preparación','Rotura'][i%3]))
    filas += [dict(F=pd.Timestamp('2025-02-02'),D='VACIO',A='Cocina',E='PROCESADO',FM='',P='',Q=None,V=0,T='Bajas',U='',C=''),
              dict(F=pd.Timestamp('2025-02-02'),D='GENERADO',A='Cocina',E='GENERADO',FM='',P='',Q=None,V=0,T='Bajas',U='',C=''),
              dict(F=pd.Timestamp('2025-02-02'),D='ANULADO',A='Cocina',E='ANULADO',FM='',P='',Q=None,V=99,T='Bajas',U='',C=''),
              dict(F=pd.Timestamp('2025-03-10'),D='NEGATIVO',A='Cocina',E='PROCESADO',FM='Comida',P='Devolución',Q=-1,V=-4.12345678,T='Bajas',U='KILOS',C='Rotura')]
    h=pd.DataFrame(filas);d=h[(h.F>=RANGO[0])&(h.F<RANGO[1])].copy()
    m=pd.DataFrame({'habitual':10.,'veces':0.,'exceso':0.,'nuevo':False,'repite_min':float('nan')},index=d.index)
    m.loc[d.index[::3],'repite_min']=22.
    m.loc[d.index[::7],['veces','exceso']]=[4.7,1.123456789]
    m.loc[d.index[::11],'nuevo']=True
    return d,h,m


def payload(lado=mp.REQUERIMIENTOS, **kwargs):
    d,h,m=muestra()
    p=datos.armar(d,lado,COLS,hist=h,anios=2,rango=RANGO,marcas=m if lado==mp.REQUERIMIENTOS else None,
                  rot_fecha='fecha de registro',faltante={'2025-02':1000.123456},hoy=dt.date(2025,5,1),**kwargs)
    return p,d,h,m


class Contrato(unittest.TestCase):
    def test_identidad_precision_y_documentos_vacios(self):
        p,d,h,m=payload();json.dumps(p,allow_nan=False)
        self.assertEqual(p['filas'][0][11],float(d.iloc[0].V))
        self.assertEqual(len(p['filas']),len(d));self.assertIn('VACIO',p['dic']['doc'])
        self.assertEqual(p['sello'],payload()[0]['sello'])
        d.loc[d.index[0],'V']+=.000000001
        self.assertNotEqual(p['sello'],datos.armar(d,mp.REQUERIMIENTOS,COLS,hist=h,anios=2,rango=RANGO,marcas=m)['sello'])
        self.assertNotRegex(JS+CSS,r'#[0-9a-fA-F]{6}\b')

    def test_fecha_feriados_semana_iso_y_parciales(self):
        p,_,_,_=payload()
        semana=p['planes']['Semana']['metas']['2025-S01']
        self.assertTrue(semana['parcial']);self.assertIn('2',semana['eje'])
        d,_,_=muestra();d=d.iloc[:1].copy();d['F']=pd.Timestamp('2021-01-01')
        p=datos.armar(d,mp.REQUERIMIENTOS,COLS,rango=(pd.Timestamp('2020-12-28'),pd.Timestamp('2021-01-05')))
        self.assertIn('2020-S53',p['planes']['Semana']['metas'])
        self.assertEqual(p['planes']['Día']['metas']['2021-01-01']['especial'],'feriado')

    def test_faltantes_opcionales_y_fecha_invalida(self):
        d,_,_=muestra();d=d.iloc[:4].copy();d.loc[d.index[0],'F']=pd.NaT
        cols={**COLS,'doc':None,'area':None,'estado':None,'cant':None,'unid':None,'tipo':None,'causa':None}
        p=datos.armar(d,mp.SALIDAS,cols,rango=RANGO)
        self.assertEqual(len(p['filas']),3);self.assertFalse(p['tipo']);self.assertFalse(p['causa'])
        self.assertEqual(p['dic']['area'],['Sin área']);self.assertIsNone(p['filas'][0][9])
        json.dumps(p,allow_nan=False)

    def test_firma_publica_y_despacho_de_lados(self):
        self.assertEqual(list(inspect.signature(mp.tarjeta_requerimientos_periodo).parameters),['d','cols','orden','rango','fecha','rot_fecha','marcas'])
        with patch.object(mp,'_tarjeta_legacy') as vieja:
            mp.tarjeta_porcionamientos_periodo(pd.DataFrame(),cols={})
            self.assertEqual(vieja.call_args.args[1],mp.PORCIONAMIENTOS)
        with patch('graficos.movimientos_periodo_pieza.renderizar') as pieza:
            mp.tarjeta_salidas_periodo(pd.DataFrame(),cols={},anios=2,rango=RANGO)
            self.assertEqual(pieza.call_args.kwargs['anios'],2)
            mp.tarjeta_produccion_periodo(pd.DataFrame(),cols={},rango=RANGO)
            self.assertEqual(pieza.call_args.args[1],mp.PRODUCCION)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        try:cls.b=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.b.new_page(viewport={'width':1323,'height':619},accept_downloads=True)
        cls.pg.set_default_timeout(7000)
        cls.pg.set_content('<div id="montar"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:531px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--danger:crimson;}body{margin:0}')
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+JS.replace('export default function(component)','window.__montarMov=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.b.close();cls.pw.stop()

    def calc(self,p,s):
        return self.pg.evaluate('([p,s])=>__movPeriodoDatos.calcular(p,s)',[p,s])

    def mount(self,p=None):
        p=payload()[0] if p is None else p
        self.pg.evaluate('p=>{window.__movPeriodoEstados={};window.__requests=[];__montarMov({data:p,parentElement:document.querySelector("#montar"),setTriggerValue:(...args)=>__requests.push(args)})}',p)
        return self.pg.locator('.mv')

    def test_cuentas_originales_en_ambos_lados_y_todos_los_granos(self):
        for lado in [mp.REQUERIMIENTOS,mp.SALIDAS]:
            p,d,h,m=payload(lado);base=mp.lineas_documentos(d,**COLS);bh=mp.lineas_documentos(h,**COLS)
            if lado==mp.REQUERIMIENTOS:base=base.join(m)
            for gran in datos.GRANOS:
                for area,tipo,fam,prod in [([],[],[],[]),(['Cocina'],[],[],[]),([],['Bajas'],[],[]),
                                          ([],[],['Comida'],[]),([],[],[],['Producto 05']),(['NO EXISTE'],[],[],[])]:
                    s=dict(gran=gran,area=area,tipo=tipo,fam=fam,prod=prod)
                    mask=pd.Series(True,index=base.index);mh=pd.Series(True,index=bh.index)
                    for k,vs in [('area',area),('tipo',tipo),('fam',fam),('prod',prod)]:
                        if vs:mask&=base[k].isin(vs);mh&=bh[k].isin(vs)
                    bl=base[mask].copy();bl['clave']=mp._periodo_serie(bl.fecha,gran)
                    ref=mp.vista_periodos(bl,gran,(RANGO[0].date(),(RANGO[1]-pd.Timedelta(days=1)).date()),lado=lado)
                    a=self.calc(p,s);self.assertEqual(a['claves'],ref['claves'])
                    for i,r in enumerate(a['series']):
                        rr=ref['res'].iloc[i]
                        for k in ['valor','cant','docs','lineas','areas','anulados','sin_procesar']:self.assertAlmostEqual(r[k],float(rr[k]),places=7)
                        var=ref['variaciones'][i]
                        if var is not None:
                            self.assertEqual(r['varEstado'],var[0])
                            if var[1] is not None:self.assertAlmostEqual(r['variacion'],var[1],places=7)
                    comps=mp.comparacion_periodos(bh[mh],RANGO,gran,ref['claves'],2,lado)
                    for c,rr in zip(a['comps'],comps):
                        np.testing.assert_allclose(c['valores'],rr['tot'],rtol=0,atol=1e-7)
                        self.assertAlmostEqual(c['total'],rr['total'],places=7);self.assertEqual(c['docs'],rr['docs'])

    def test_marcas_partes_sin_sumar_solapamientos(self):
        p,d,_,m=payload();bl=mp.lineas_documentos(d,**COLS).join(m);bl['clave']=mp._periodo_serie(bl.fecha,'Mes')
        v=mp.vista_periodos(bl,'Mes',(RANGO[0].date(),(RANGO[1]-pd.Timedelta(days=1)).date()))
        a=self.calc(p,{'gran':'Mes'});marcas=mp.marcas_de_vista(mp._validas(bl),v['claves'])
        for nombre,vs in marcas['marcas'].items():
            np.testing.assert_allclose(next(t['valores'] for t in a['trazas'] if t['nombre']==nombre),vs,rtol=0,atol=1e-7)
        for k in ['rep_n','rep_v','fuera_n','fuera_v','nuevos_n','por_dia']:
            np.testing.assert_allclose([r[k] for r in a['series']],marcas['marcas_tab'][k],rtol=0,atol=1e-7)
        trazas=mp.trazas_por_area(mp._validas(bl),v['claves'],())
        for nombre,_,vs in trazas:np.testing.assert_allclose(next(t['valores'] for t in a['trazas'] if t['nombre']==nombre),vs,rtol=0,atol=1e-7)

    def test_documentos_estados_y_unidades(self):
        p,d,_,_=payload();a=self.calc(p,{})
        bl=mp.lineas_documentos(d,**COLS);ref,_=mp.tabla_documentos(bl,None)
        got={r['doc']:r for r in a['docs']}
        for r in ref.itertuples():
            self.assertEqual(got[r.codigo]['lineas'],r.lineas)
            self.assertAlmostEqual(round(got[r.codigo]['valor'],2),r.valor,places=2)
        self.assertFalse(got['VACIO']['suma']);self.assertFalse(got['ANULADO']['suma'])
        self.assertFalse(got['GENERADO']['suma'])
        self.assertEqual(set(a['unidades']),{'KILOS','UNIDAD'})
        self.assertEqual(len([r for r in a['productos'] if r['prod']=='Producto 05']),2)

    def test_bajas_causa_y_registro_solo_comparable(self):
        p,_,_,_=payload(mp.SALIDAS)
        a=self.calc(p,{'gran':'Mes','tipo':['Bajas']})
        self.assertEqual(a['partir'],'Por causa');self.assertIn('2025-02',a['registro']);self.assertNotIn('2025-01',a['registro'])
        self.assertFalse(self.calc(p,{'gran':'Mes','area':['Cocina']})['registro'])
        p['contexto']={'Áreas de la página':['Cocina']}
        self.assertFalse(self.calc(p,{'gran':'Mes','tipo':['Bajas']})['registro'])

    def test_historico_con_periodo_sin_barra_y_bisiesto(self):
        p,_,_,_=payload(mp.SALIDAS);a=self.calc(p,{'gran':'Día'})
        self.assertNotAlmostEqual(a['comps'][0]['total'],sum(a['comps'][0]['valores']))
        d,h,_=muestra();d=d.iloc[:1].copy();h=d.copy();d['F']=pd.Timestamp('2025-02-28 11:00');h['F']=pd.Timestamp('2024-02-29 11:00')
        p=datos.armar(d,mp.SALIDAS,COLS,hist=h,anios=1,rango=(pd.Timestamp('2025-02-01'),pd.Timestamp('2025-03-01')))
        a=self.calc(p,{'gran':'Mes'});self.assertAlmostEqual(a['comps'][0]['total'],float(h.iloc[0].V))

    def test_interaccion_busqueda_top_detalle_y_persistencia(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=menu][data-v=prod]').click();root.locator('[data-input=mq]').fill('Top 5')
        root.locator('[data-filtro=prod]').check();root.locator('[data-a=cerrar]').click()
        self.assertEqual(len(pg.evaluate('__movPeriodo.D.productos.map(r=>r.prod).filter((v,i,a)=>a.indexOf(v)===i)')),5)
        root.locator('[data-a=todos]').click();root.locator('[data-a=modo][data-v=Detalle]').click()
        root.locator('[data-input=q]').fill('VACIO');self.assertEqual(pg.evaluate('__movPeriodo.D.docs.length'),1)
        self.assertIn('Sin ítems',root.inner_text())
        root.locator('[data-input=q]').fill('Producto 05');self.assertTrue(pg.evaluate('__movPeriodo.D.docs.length>0'))
        pg.evaluate('()=>__montarMov({data:__movPeriodo.P,parentElement:document.querySelector("#montar")})')
        self.assertEqual(root.locator('[data-input=q]').input_value(),'Producto 05');self.assertEqual(pg.evaluate('__requests.length'),0)
        p=payload()[0];p['sello']='nuevo';p['dic']['prod']=['NO '+v for v in p['dic']['prod']]
        pg.evaluate('p=>{__movPeriodo.s.area=["NO EXISTE"];__montarMov({data:p,parentElement:document.querySelector("#montar")})}',p)
        self.assertEqual(pg.evaluate('__movPeriodo.s.area'),['NO EXISTE']);self.assertEqual(pg.evaluate('__movPeriodo.D.total'),0)

    def test_click_y_arrastre_del_tramo(self):
        root=self.mount();pg=self.pg
        root.locator('[data-a=gran][data-v=Mes]').click();root.locator('[data-bar="1"]').click()
        self.assertEqual(pg.evaluate('__movPeriodo.s.modo'),'Detalle');self.assertEqual(len(pg.evaluate('__movPeriodo.D.seleccion')),1)
        root.locator('[data-a=rango]').click()
        a=root.locator('[data-bar="0"]').bounding_box();b=root.locator('[data-bar="2"]').bounding_box()
        pg.mouse.move(a['x']+a['width']/2,a['y']+20);pg.mouse.down();pg.mouse.move(b['x']+b['width']/2,b['y']+20,steps=6);pg.mouse.up()
        self.assertEqual(len(pg.evaluate('__movPeriodo.D.seleccion')),3);self.assertIsNotNone(pg.evaluate('__movPeriodo.s.tramo'))
        self.assertAlmostEqual(pg.evaluate('__movPeriodo.D.total'),sum(r['valor'] for r in pg.evaluate('__movPeriodo.D.series')[:3]),places=7)

    def test_excel_numerico_contexto_y_navegacion_teclado(self):
        root=self.mount(payload(mp.SALIDAS)[0]);pg=self.pg
        root.locator('[data-a=modo][data-v=Comparación]').click()
        with pg.expect_download() as dow:root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'mov.xlsx';dow.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                sheets=[ET.fromstring(z.read(n)) for n in z.namelist() if n.startswith('xl/worksheets/')]
                ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                numeric=[c for t in sheets for c in t.findall('.//s:c',ns) if c.find('s:v',ns) is not None]
                self.assertTrue(numeric)
                text=' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                self.assertIn('Fecha usada',text);self.assertIn('2023',text);self.assertIn('Comparación',text)
                self.assertFalse(any(t.findall('.//s:f',ns) for t in sheets))
        root.locator('[data-bar="0"]').focus();pg.keyboard.press('Enter')
        self.assertEqual(pg.evaluate('__movPeriodo.s.modo'),'Detalle')

    def test_documento_completo_sin_perder_el_ambito(self):
        p,_,_,_=payload()
        # Dos productos del mismo documento: el filtro deja sólo uno.
        i=next(i for i,v in enumerate(p['dic']['prod']) if v=='Producto 05')
        filas=[r for r in p['filas'] if r[5]==i]
        otra=filas[0].copy();otra[5]=p['dic']['prod'].index('Producto 06');p['filas'].append(otra)
        root=self.mount(p);pg=self.pg
        pg.evaluate('doc=>{const G=__movPeriodo;G.s.modo="Detalle";G.s.prod=["Producto 05"];G.s.doc=doc;__movPeriodoDatos.dibujar(G)}',p['dic']['doc'][filas[0][1]])
        antes=pg.evaluate('__movPeriodo.D.total');n=pg.evaluate('__movPeriodo.D.lineas.length')
        root.locator('[data-completo]').check()
        self.assertGreater(pg.evaluate('__movPeriodo.D.lineas.length'),n)
        self.assertEqual(pg.evaluate('__movPeriodo.D.total'),antes)

    def test_cache_local_invalida_con_filtros_y_tramos(self):
        self.mount();pg=self.pg
        # La búsqueda y el modo reutilizan la serie; cambiar filtros la reemplaza.
        pg.evaluate('()=>{const G=__movPeriodo;window.__serie=G.cache.core;G.s.modo="Detalle";G.s.q="Producto 05";__movPeriodoDatos.dibujar(G)}')
        self.assertTrue(pg.evaluate('__serie===__movPeriodo.cache.core'))
        self.assertTrue(pg.evaluate('__movPeriodo.D.docs.length>0'))
        pg.evaluate('()=>{const G=__movPeriodo;G.s.area=["Cocina"];__movPeriodoDatos.dibujar(G)}')
        self.assertFalse(pg.evaluate('__serie===__movPeriodo.cache.core'))
        pg.evaluate('()=>{const G=__movPeriodo;G.s.foco=G.D.claves[0];__movPeriodoDatos.dibujar(G)}')
        a=pg.evaluate('()=>{const G=__movPeriodo,F=__movPeriodoDatos;const fresh=F.calcular(G.P,G.s);return [G.D.total,fresh.total,G.D.docs.map(r=>r.doc),fresh.docs.map(r=>r.doc)]}')
        self.assertEqual(a[0],a[1]);self.assertEqual(a[2],a[3])

    def test_tablas_largas_scroll_responsive_y_alturas(self):
        p,_,_,_=payload();n=len(p['filas']);original=p['filas'][0]
        for i in range(450):
            r=original.copy();p['dic']['doc'].append(f'EXTRA-{i}');r[1]=len(p['dic']['doc'])-1;r[8]=p['dic']['estado'].index('PROCESADO');p['filas'].append(r)
        root=self.mount(p);pg=self.pg
        root.locator('[data-a=modo][data-v=Detalle]').click()
        self.assertEqual(root.locator('[data-tabla=docs] tbody tr').count(),150)
        sc=root.locator('[data-tabla=docs]');sc.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}')
        self.assertGreater(root.locator('[data-tabla=docs] tbody tr').count(),150)
        self.assertEqual(pg.evaluate('Math.round(document.querySelector(".mv-main").getBoundingClientRect().height)'),531)
        self.assertEqual(pg.evaluate('Math.round(document.querySelector(".mv-detalle").getBoundingClientRect().height)'),575)
        pg.set_viewport_size({'width':390,'height':844})
        self.assertLessEqual(pg.evaluate('document.documentElement.scrollWidth'),390)
        pg.set_viewport_size({'width':1323,'height':619});self.assertEqual(len(p['filas']),n+450)


if __name__=='__main__':unittest.main(verbosity=2)
