"""Costo útil nativo: atribución, ponderación, comparación y trazabilidad (#729)."""
import inspect
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from graficos import movimientos_merma as mm
from graficos import merma_proveedores_datos as datos
from test_porcionamientos_pieza import COLS

ROOT=Path(__file__).parent
RANGO=(pd.Timestamp('2025-01-01'),pd.Timestamp('2026-07-01'))


def muestra():
    filas=[];compras=[]
    def porc(doc,f,cod,unid,q,m,p):
        for corte in range(2):filas.append(dict(F=f,D=doc,A='Cocina',T='Ana',P='Producto '+cod,C=cod,U=unid,Q=q,M=m,PF='Corte '+str(corte),CF=str(corte),QF=q/2,UF=unid,PP=p,PS=q/2))
    for cod,unidades in [('0001',['KILOS']),('0002',['UNIDAD','CAJAS'])]:
        for i,f in enumerate(pd.date_range('2025-01-01','2026-06-01',freq='MS')):
            prov='Proveedor A' if i%2 else 'Proveedor B';p=10.123456789 if i%2 else 9.234567891
            compras.append(dict(COD_PRODUCTO=cod,FECHA_EMISION_DOC=f,NOMBRE_PROVEEDOR=prov,CANTIDAD_COMPRA=10,VALOR_COMPRA=p*10))
            if i%3==0:
                compras.append(dict(COD_PRODUCTO=cod,FECHA_EMISION_DOC=f-pd.Timedelta(days=3),NOMBRE_PROVEEDOR='Otro reciente',CANTIDAD_COMPRA=1,VALOR_COMPRA=p))
            for u in unidades:
                for j in range(8):
                    q=10.123456789+j/10;porc(f'{cod}-{u}-{i}-{j}',f+pd.Timedelta(days=j+1,hours=10),cod,u,q,q*(.2 if i%2 else .1),p)
        porc(cod+'-poco',pd.Timestamp('2026-06-28'),cod,unidades[0],10,1,2)
        compras.append(dict(COD_PRODUCTO=cod,FECHA_EMISION_DOC=pd.Timestamp('2026-06-27'),NOMBRE_PROVEEDOR='Barato con un registro',CANTIDAD_COMPRA=10,VALOR_COMPRA=20))
    porc('Sin proveedor',pd.Timestamp('2026-06-28'),'0003','KILOS',10,1,5)
    porc('Sin costo',pd.Timestamp('2026-06-20'),'0001','KILOS',10,1,0)
    porc('Sin cantidad',pd.Timestamp('2026-06-20'),'0001','KILOS',0,1,2)
    for day in [15,16]:porc('Límite '+str(day),pd.Timestamp(f'2026-02-{day}'),'0004','KILOS',10,1,2)
    compras.append(dict(COD_PRODUCTO='0004',FECHA_EMISION_DOC=pd.Timestamp('2026-01-01'),NOMBRE_PROVEEDOR='Límite',CANTIDAD_COMPRA=10,VALOR_COMPRA=20))
    d=pd.DataFrame(filas);d['_fecha']=d.F
    return d,mm.compras_para_proveedor(pd.DataFrame(compras))


def payload(d=None,c='normal'):
    raw,compras=muestra()
    return datos.armar(raw if d is None else d,COLS,compras if isinstance(c,str) else c,rango=RANGO)


class Contrato(unittest.TestCase):
    def test_cabecera_unica_limites_y_unidades(self):
        d,c=muestra();P=payload();json.dumps(P,allow_nan=False)
        b,_=mm.porcionamientos(d,COLS)
        self.assertEqual(len(P['filas']),len(b));self.assertEqual(len({r['doc'] for r in P['filas']}),len(b))
        self.assertEqual({p['unid'] for p in P['productos'] if p['cod']=='0002'},{'CAJAS','UNIDAD'})
        a={r['doc']:r for r in P['filas']};self.assertIsNotNone(a['Límite 15']['prov']);self.assertIsNone(a['Límite 16']['prov'])
        self.assertEqual(P['ventanas']['6 meses']['ini'],'2026-01-01T00:00:00');self.assertEqual(P['ventanas']['6 meses']['fin'],'2026-07-01T00:00:00')
        self.assertEqual(P['sello'],payload()['sello']);d.loc[0,'PP']+=.00000001;self.assertNotEqual(P['sello'],payload(d=d)['sello'])

    def test_rastro_conserva_compra_ambigua_y_precio_del_dia(self):
        d,c=muestra();base,_=mm.porcionamientos(d,COLS);b=mm.con_proveedor(base,c);P=payload();rs={r['doc']:r for r in P['filas']}
        for (_,prov),g in b[b.prov.notna()].groupby(['cod','prov']):
            for r in mm.rastro_proveedor(g,c,prov).itertuples(index=False):
                a=rs[r.doc];self.assertEqual(a['compra'],r.compra.isoformat());self.assertEqual(a['unico'],r.unico);self.assertEqual(a['difiere'],r.difiere)
                self.assertAlmostEqual(a['pcompra'],r.pcompra)
                self.assertEqual(a['otro'],r.otro if isinstance(r.otro,str) else None)

    def test_firma_publica_y_despacho(self):
        self.assertEqual(list(inspect.signature(mm.tarjeta_proveedores).parameters),['d_hist','cols','rango'])
        with patch('graficos.merma_proveedores_pieza.renderizar') as nueva:
            mm.tarjeta_proveedores(pd.DataFrame(),COLS,RANGO);self.assertEqual(nueva.call_args.args[1],COLS)

    def test_foco_compartido_valida_sello_y_codigo_y_cache(self):
        from graficos import merma_proveedores_pieza as pieza
        d,c=muestra();ss={};fake=Mock(session_state=ss)
        with patch.object(pieza,'st',fake),patch.object(pieza.mm,'st',fake),patch.object(pieza.mm,'_compras',return_value=c),patch.object(pieza,'_PIEZA') as componente,patch.object(pieza.datos,'armar',wraps=datos.armar) as armar,patch.object(pieza.mm,'_avisar_a') as avisar:
            pieza.renderizar(d,COLS,RANGO);ss[mm._K_PROD]='0002';pieza.renderizar(d,COLS,RANGO)
            self.assertEqual(armar.call_count,1);self.assertEqual(componente.call_args.kwargs['data']['comun'],'0002')
            P=ss['_merma_proveedores_cache'][1]
            for v in [{'sello':'viejo','cod':'0001'},{'sello':P['sello'],'cod':'desconocido'},{'sello':P['sello'],'cod':['0001']}]:
                ss['merma_proveedores_pieza']={'producto':v};pieza._producto();self.assertEqual(ss[mm._K_PROD],'0002')
            ss['merma_proveedores_pieza']={'producto':{'sello':P['sello'],'cod':'0001'}};pieza._producto();self.assertEqual(ss[mm._K_PROD],'0001');avisar.assert_called_once_with(mm.SEC_REND)


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
        cls.pg=cls.b.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000)
        cls.pg.set_content('<div id="host"></div>')
        cls.pg.add_style_tag(content=':root{--alto-util:531px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--danger:crimson;}body{margin:0}')
        cls.pg.evaluate('css=>{const h=document.querySelector("#host"),sr=h.attachShadow({mode:"open"}),style=document.createElement("style");style.textContent=css;sr.append(style);window.__pvMount=document.createElement("div");sr.append(__pvMount);}',(ROOT/'graficos/merma_proveedores.css').read_text(encoding='utf-8'))
        js=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/merma_proveedores.js').read_text(encoding='utf-8').replace('export default function(component)','window.__montarPVU=function(component)')
        cls.pg.add_script_tag(content=js)

    @classmethod
    def tearDownClass(cls):cls.b.close();cls.pw.stop()

    def calc(self,P,s):return self.pg.evaluate('([P,s])=>__provUtilDatos.calcular(P,__provUtilDatos.estado(s))',[P,s])

    def mount(self,P=None):
        self.pg.evaluate('P=>{window.__provUtil?.abort.abort();window.__provUtil=null;window.__requests=[];__montarPVU({data:P,parentElement:__pvMount,setTriggerValue:(...a)=>__requests.push(a)})}',P or payload())
        return self.pg.locator('.pvu')

    def test_seis_ventanas_y_atribuciones_contra_pandas(self):
        d,c=muestra();P=payload()
        for ventana,n in mm.VENTANAS.items():
            base,_=mm.porcionamientos(d[(d._fecha>=RANGO[1]-pd.DateOffset(months=n))&(d._fecha<RANGO[1])],COLS);b=mm.con_proveedor(base,c)
            for unico in [False,True]:
                D=self.calc(P,dict(ventana=ventana,unico=unico));esperados={}
                for (cod,u),g in b.groupby(['cod','unid']):
                    r=mm.resumen_proveedores(g,unico)
                    if len(r):esperados[(cod,u)]=r.loc[cod]
                    pid=next(i for i,p in enumerate(P['productos']) if p['cod']==cod and p['unid']==u)
                    a=self.calc(P,dict(ventana=ventana,unico=unico,prod=pid));t=mm.por_proveedor(g,unico)
                    if a['foco'] is None or a['foco']['id']!=pid:
                        self.assertEqual(len(t),0)
                        self.assertFalse(any(r['id']==pid for r in a['productos']))
                        continue
                    self.assertEqual(len(a['t']),len(t))
                    for row in a['t']:
                        r=t.loc[row['nombre']]
                        for k in ['n','cant','merma','costo','pct','pkg','util','dias']:
                            if pd.isna(r[k]):self.assertIsNone(row[k])
                            else:self.assertAlmostEqual(row[k],r[k],places=7,msg=f'{ventana} {unico} {cod} {u} {k}')
                self.assertEqual(len(D['ranking']),len(esperados));self.assertAlmostEqual(D['extra'],sum(r.extra for r in esperados.values()),places=7)
                for r in D['ranking']:self.assertAlmostEqual(r['extra'],esperados[(r['cod'],r['unid'])].extra,places=7)

    def test_factores_cierran_y_no_compiten_los_pocos(self):
        P=payload();D=self.calc(P,{});a=D['sel'];b=D['contra']
        c=D['comparacion'];self.assertAlmostEqual(c['precio']+c['rendimiento'],b['util']-a['util'],places=10)
        self.assertTrue(all(next(t for t in r['t'] if t['id']==m['id'])['n']>=P['min_porc'] for r in D['ranking'] for m in r['pm']['montos']))
        self.assertTrue(any(t['n']==1 for t in D['t']));self.assertAlmostEqual(a['util'],a['costo']/(a['cant']-a['merma']),places=10)
        inv=self.pg.evaluate('([a,b])=>__provUtilDatos.comparar(b,a)',[a,b]);self.assertAlmostEqual(inv['precio'],-c['precio']);self.assertAlmostEqual(inv['rendimiento'],-c['rendimiento'])

    def test_controles_locales_y_foco_compartido_por_teclado(self):
        root=self.mount();root.locator('[data-a=ventana][data-v="6 meses"]').click();root.locator('[data-k=unico]').check();root.locator('[data-a=modo][data-v=Comparar]').click()
        self.assertEqual(self.pg.evaluate('__requests'),[])
        row=root.locator('[data-tabla=rank] tbody tr').last;row.focus();row.press('Enter')
        req=self.pg.evaluate('__requests');self.assertEqual(len(req),1);self.assertEqual(req[0][0],'producto');self.assertEqual(req[0][1]['sello'],payload()['sello'])

    def test_busqueda_no_cambia_benchmark_y_rastro_conserva_total(self):
        root=self.mount();antes=self.pg.evaluate('__provUtil.D.extra');root.locator('[data-k=q]').fill('0001')
        self.assertEqual(self.pg.evaluate('__provUtil.D.extra'),antes);self.assertEqual(root.locator('[data-tabla=rank] tbody tr').count(),1)
        root.locator('[data-a=modo][data-v=Porcionamientos]').click();n=self.pg.evaluate('__provUtil.D.trace.length');root.locator('[data-k=dq]').fill('no existe')
        self.assertEqual(self.pg.evaluate('__provUtil.D.trace.length'),n);self.assertEqual(root.locator('[data-tabla=rastro] tbody tr').count(),0)
        self.assertIn(f'0 visibles de {n}',root.inner_text())

    def test_excel_numerico_completo_y_contexto(self):
        root=self.mount();root.locator('[data-a=modo][data-v=Comparar]').click();hs=self.pg.evaluate('__provUtilDatos.exportar(__provUtil)')
        self.assertEqual(len(hs),7);rows=next(h for h in hs if h['nombre']=='Porcionamientos ventana')['filas'];self.assertEqual(len(rows),self.pg.evaluate('__provUtil.D.rows.length'))
        with tempfile.TemporaryDirectory() as td:
            with self.pg.expect_download() as ev:root.locator('[data-a=excel]').click()
            p=Path(td)/'prueba.xlsx';ev.value.save_as(p)
            with zipfile.ZipFile(p) as z:
                text=''.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for w in ['Costo del día','Cantidad útil','Última compra','10.123457']:self.assertIn(w,text)
                self.assertNotIn('<f>',text)

    def test_escritura_continua_en_shadow_conserva_cursor_y_foco(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('0001');self.assertEqual(q.input_value(),'0001')
        self.assertEqual(self.pg.evaluate('__pvMount.getRootNode().activeElement.dataset.k'),'q')
        root.locator('[data-a=modo][data-v=Porcionamientos]').click();q=root.locator('[data-k=dq]');q.click();q.press_sequentially('sin coincidencia');self.assertEqual(q.input_value(),'sin coincidencia')
        self.assertEqual(self.pg.evaluate('__pvMount.getRootNode().activeElement.dataset.k'),'dq');self.assertEqual(self.pg.evaluate('__requests'),[])

    def test_vacio_sin_compras_y_movil(self):
        raw,_=muestra();self.mount(payload(raw.iloc[:0]));self.assertEqual(self.pg.evaluate('__provUtil.D.rows.length'),0)
        self.mount(payload(c=None));self.assertIn('No se pudo leer Compras',self.pg.locator('.pvu').inner_text())
        self.pg.locator('[data-k=todos]').check();self.assertGreater(self.pg.evaluate('__provUtil.D.visibles.length'),0)
        self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),390)
        self.pg.set_viewport_size({'width':1323,'height':619})

    def test_estado_y_cambio_externo_de_producto(self):
        P=payload();root=self.mount(P);root.locator('[data-a=ventana][data-v="6 meses"]').click();root.locator('[data-a=modo][data-v=Comparar]').click()
        P['comun']='0002';self.pg.evaluate('P=>__montarPVU({data:P,parentElement:__pvMount,setTriggerValue:(...a)=>__requests.push(a)})',P)
        self.assertEqual(self.pg.evaluate('__provUtil.P.productos[__provUtil.s.prod].cod'),'0002');self.assertEqual(self.pg.evaluate('__provUtil.s.ventana'),'6 meses');self.assertEqual(self.pg.evaluate('__provUtil.s.modo'),'Comparar');self.assertEqual(self.pg.evaluate('__requests'),[])

    def test_listas_largas_por_tandas_y_excel_completo(self):
        raw,c=muestra();base=raw.iloc[:2];d=pd.concat([base.assign(D='Largo '+str(i),F=pd.Timestamp('2026-06-10'),_fecha=pd.Timestamp('2026-06-10')) for i in range(230)],ignore_index=True)
        root=self.mount(payload(d));root.locator('[data-k=todos]').check();root.locator('[data-a=modo][data-v=Porcionamientos]').click();t=root.locator('[data-tabla=rastro]')
        self.assertEqual(t.locator('tbody tr').count(),150);t.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}')
        self.assertEqual(t.locator('tbody tr').count(),230);hs=self.pg.evaluate('__provUtilDatos.exportar(__provUtil)');self.assertEqual(len(next(h for h in hs if h['nombre']=='Rastro visible')['filas']),230)


if __name__=='__main__':unittest.main(verbosity=2)
