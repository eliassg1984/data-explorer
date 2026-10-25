"""Para revisar: reglas, peso anterior, impacto superpuesto y ficha nativa (#732)."""
import copy
import inspect
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

from graficos import movimientos_merma as mm
from graficos import merma_revision_datos as datos
from test_porcionamientos_pieza import COLS

ROOT=Path(__file__).parent
RANGO=(pd.Timestamp('2026-06-01'),pd.Timestamp('2026-07-01'))
PESO='260600101'


def muestra():
    filas=[]
    def doc(cod,fecha,m=6,q=10,cs=None,prod='Crudo de prueba',codigo='0001',u='KILOS'):
        for cf,nombre,qf,peso,pp in cs or [('0000100','Corte A',4,2,8),('0000200','Corte B',4,2,8)]:
            filas.append(dict(F=pd.Timestamp(fecha),D=cod,A='Cocina',T='Ana',P=prod,C=codigo,U=u,Q=q,M=m,PF=nombre,CF=cf,QF=qf,UF='UNIDAD',PP=pp,PS=peso))
    for i in range(20):doc('260200'+str(i),pd.Timestamp('2026-02-01')+pd.Timedelta(days=i))
    for i in range(10):doc('260600'+str(i),pd.Timestamp('2026-06-01')+pd.Timedelta(days=i))
    doc(PESO,'2026-06-15',m=2,cs=[('0000100','Corte A',4,6,15),('0000200','Corte B',4,2,5),('0000300','Corte sin peso',2,0,0)])
    doc('260600102','2026-06-16',m=0);doc('260600103','2026-06-17',m=9.5)
    doc('259900201','2026-06-18');doc('260600104','2026-06-19',cs=[('0000100','Corte A',4,2,40),('0000200','Corte B',4,2,40)])
    doc('260600105','2026-06-20',m=None);doc('260600106','2026-06-21',q=0,m=1)
    doc('260600107','2026-06-22',m=11);doc('260600108','2026-06-23',m=1,codigo='0002',u='UNIDAD',prod='Porciones')
    doc('260600109','2026-06-24',m=-1);doc('260700999','2026-07-15',m=9,cs=[('0000100','Corte A',4,200,8)])
    hist=pd.DataFrame(filas);hist['_fecha']=hist.F
    d=hist[(hist._fecha>=RANGO[0])&(hist._fecha<RANGO[1])].copy()
    compras=mm.compras_para_proveedor(pd.DataFrame([dict(COD_PRODUCTO='0001',FECHA_EMISION_DOC=pd.Timestamp('2026-05-25'),NOMBRE_PROVEEDOR='Proveedor A',CANTIDAD_COMPRA=10,VALOR_COMPRA=80)]))
    ps=pd.Series({'0001':8.234567891,'0000100':15.,'0000200':5.})
    rv=pd.DataFrame([{'COD PLATO':p,'NOMB PLATO':n,'ITEM VENTA ACTIVO':'ACTIV' if a==1 else a,'COD INS':c,'TOTAL':v,'CST SALON':cost,'%CST SALON':pct} for p,n,a,c,v,cost,pct in [
        ('000001','Plato A',1,'0000100',30,50,.5),('000001','Plato A',1,'otro',20,50,.5),
        ('000002','Plato B',1,'0000100',5,25,.25),('000002','Plato B',1,'0000100',5,25,.25),('000003','Plato inactivo','INACTIVO','0000100',30,50,.5)]])
    return d,hist,compras,ps,rv


def payload(d=None,h=None,ps='normal',recetas='normal',modo='dia'):
    raw,hist,c,precios,rv=muestra();P=datos.armar(raw if d is None else d,hist if h is None else h,COLS,precios if isinstance(ps,str) else ps,c,rango=RANGO)
    if P['carta']:P=datos.adjuntar_recetas(P,rv if isinstance(recetas,str) else recetas)
    P['modo']=modo;return P


def original(modo='dia',d=None,h=None,ps='normal'):
    raw,hist,c,precios,_=muestra();raw=raw if d is None else d;hist=hist if h is None else h
    base,cs=mm.porcionamientos(raw,COLS);b,ch=mm.porcionamientos(hist[(hist._fecha<RANGO[1])&(hist._fecha>=RANGO[1]-pd.Timedelta(days=mm.DIAS_NORMAL))],COLS)
    pesos=mm.pesos_por_unidad(b,ch);val=mm.valorizar(mm.con_proveedor(base,c),mm.VALOR_HOY if modo=='hoy' else mm.VALOR_DIA,precios if isinstance(ps,str) else ps)
    return mm.marcar(val,mm.normales(b),cs,pesos),cs,pesos


class Contrato(unittest.TestCase):
    def test_cabeceras_marcas_y_pesos_contra_originales(self):
        P=payload();json.dumps(P,allow_nan=False);b,cs,pesos=original();wire={r['doc']:r for r in P['filas']}
        self.assertEqual(len(wire),len(b));self.assertNotIn('260600106',wire);self.assertTrue(all(c['doc'] in wire for c in P['cortes']))
        for r in b.itertuples(index=False):
            a=wire[r.doc];self.assertEqual(a['marcas'],[k for k in mm.MARCAS if bool(getattr(r,'m_'+k))]);self.assertAlmostEqual(a['dpeso'],r.dpeso)
            self.assertAlmostEqual(a['costoDia'],r.costo_dia)
        bad=wire[PESO];self.assertEqual(bad['dpeso'],4);self.assertIn('peso',bad['marcas']);self.assertIn('sinpeso',bad['marcas']);self.assertIn('baja',bad['marcas'])

    def test_peso_anterior_no_usa_el_futuro_y_separa_unidades(self):
        d,h,_,_,_=muestra();P=payload();q=h.copy();q.loc[q._fecha>=RANGO[1],'PS']=10000;Q=payload(h=q)
        self.assertEqual(P['sello'],Q['sello'])
        a=next(c for c in P['cortes'] if c['doc']==PESO and c['cod']=='0000100');self.assertEqual(a['hab'],.5);self.assertEqual(a['kgu'],1.5)
        extra=d[d.D==PESO].iloc[[0]].assign(U='UNIDAD',D='260600777');h2=pd.concat([h,extra],ignore_index=True);d2=pd.concat([d,extra],ignore_index=True);R=payload(d2,h2)
        p=next(r for r in R['filas'] if r['doc']=='260600777');self.assertNotIn('peso',p['marcas']);self.assertTrue(all(c['hab'] is None for c in R['cortes'] if c['doc']=='260600777'))

    def test_arrastre_y_carta_conservan_la_cuenta_canonica(self):
        P=payload();self.assertEqual(len(P['carta']),1);c=next(c for c in P['cortes'] if c.get('carta')==0)
        self.assertEqual(c['precioCorregido'],10);self.assertEqual(c['precioHoy'],15);self.assertAlmostEqual(P['carta'][0]['factor'],2/3)
        platos={r['nombre']:r for r in P['carta'][0]['platos']};self.assertEqual(set(platos),{'Plato A','Plato B'});self.assertEqual(platos['Plato A']['costoCorr'],40);self.assertAlmostEqual(platos['Plato B']['costoCorr'],25-10/3)
        Q=payload(recetas=None);self.assertFalse(Q['recetas_disponibles']);self.assertEqual(Q['carta'][0]['platos'],[]);self.assertEqual(P['sello_origen'],Q['sello_origen'])

    def test_sin_precio_no_mezcla_bases_y_conserva_valores_anomalos(self):
        P=payload(ps=None,modo='hoy');self.assertFalse(P['precios_disponibles']);self.assertTrue(all(r['precioHoy'] is None for r in P['filas']))
        Q=payload();a=next(r for r in Q['filas'] if Q['productos'][r['prod']]['cod']=='0002');self.assertEqual(a['precioHoy'],0);self.assertFalse(a['precioDisponible'])
        self.assertEqual(next(r for r in Q['filas'] if r['doc']=='260600107')['merma'],11);self.assertEqual(next(r for r in Q['filas'] if r['doc']=='260600109')['merma'],-1)

    def test_firma_y_salto_repetido(self):
        self.assertEqual(list(inspect.signature(mm.tarjeta_revisar).parameters),['d_rango','d_hist','cols','rango','fecha'])
        with patch('graficos.merma_revision_pieza.renderizar') as pieza:
            mm.tarjeta_revisar(pd.DataFrame(),pd.DataFrame(),COLS,RANGO,fecha=None);self.assertEqual(pieza.call_args.args[2],COLS)
        ss={}
        with patch.object(mm,'st',SimpleNamespace(session_state=ss)):
            mm.ir_a_revisar(PESO);uno=ss['_merma_revision_salto'];mm.ir_a_revisar(PESO);self.assertEqual(ss['_merma_revision_salto'],uno+1)

    def test_cache_de_ambas_bases_y_carga_condicional_de_recetas(self):
        from graficos import merma_revision_pieza as pieza
        d,h,c,p,rv=muestra();ss={mm.K_VALOR:mm.VALOR_DIA};fake=SimpleNamespace(session_state=ss,markdown=Mock(),container=lambda **kw:nullcontext());fecha=Mock()
        with patch.object(pieza,'st',fake),patch.object(mm,'st',fake),patch.object(mm,'precios_hoy',return_value=p),patch.object(mm,'_compras',return_value=c),patch.object(mm,'_recetas_venta',return_value=rv) as recetas,patch.object(mm,'control_valorizacion'),patch.object(pieza,'_PIEZA') as componente,patch.object(datos,'armar',wraps=datos.armar) as armar,patch.object(datos,'adjuntar_recetas',wraps=datos.adjuntar_recetas) as adjuntar:
            pieza.renderizar(d,h,COLS,RANGO,fecha);ss[mm.K_VALOR]=mm.VALOR_HOY;pieza.renderizar(d,h,COLS,RANGO,fecha)
            self.assertEqual(armar.call_count,1);self.assertEqual(adjuntar.call_count,1);self.assertEqual(componente.call_args.kwargs['data']['modo'],'hoy');self.assertEqual(fecha.call_count,2)
            self.assertGreaterEqual(recetas.call_count,1)
        d=d[d.D!=PESO];ss={};fake.session_state=ss
        with patch.object(pieza,'st',fake),patch.object(mm,'st',fake),patch.object(mm,'precios_hoy',return_value=p),patch.object(mm,'_compras',return_value=c),patch.object(mm,'_recetas_venta') as recetas,patch.object(mm,'control_valorizacion'),patch.object(pieza,'_PIEZA'):
            pieza.renderizar(d,h,COLS,RANGO);recetas.assert_not_called()


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
        cls.pg.set_content('<div id="host"></div>');cls.pg.add_style_tag(content=':root{--alto-util:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--danger:crimson;}body{margin:0}')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),style=document.createElement("style");style.textContent=css;sr.append(style);window.__revMount=document.createElement("div");sr.append(__revMount);}',(ROOT/'graficos/merma_revision.css').read_text(encoding='utf-8'))
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/merma_revision.js').read_text(encoding='utf-8').replace('export default function(component)','window.__montarRev=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.b.close();cls.pw.stop()

    def mount(self,P=None):
        self.pg.evaluate('P=>{window.__mermaRev?.abort.abort();window.__mermaRev=null;window.__requests=[];__montarRev({data:P,parentElement:__revMount,setTriggerValue:(...a)=>__requests.push(a)})}',P or payload())
        return self.pg.locator('.mrv')

    def test_todas_las_combinaciones_de_marcas_y_bases(self):
        P=payload();codigos=list(mm.MARCAS);estados=[list(itertools.compress(codigos,[(mask>>i)&1 for i in range(len(codigos))])) for mask in range(1<<len(codigos))]
        self.pg.evaluate('P=>window.__P=P',P)
        for modo in ['dia','hoy']:
            b,_,_=original(modo)
            got=self.pg.evaluate('([modo,es])=>{__P.modo=modo;return es.map(marcas=>__mermaRevDatos.calcular(__P,__mermaRevDatos.estado({marcas})).visibles.map(r=>({doc:r.doc,impacto:r.impacto})));}',[modo,estados])
            for marks,rs in zip(estados,got):
                x=b[b[[f'm_{k}' for k in marks]].any(axis=1)] if marks else b.iloc[:0];imp=mm.impacto(x,marks);expected=dict(zip(x.doc,imp))
                self.assertEqual(set(r['doc'] for r in rs),set(expected))
                for r in rs:self.assertAlmostEqual(r['impacto'],expected[r['doc']],places=8)

    def test_marcas_superpuestas_no_se_suman_ni_compensan(self):
        P=payload();a=self.pg.evaluate('P=>{const D=__mermaRevDatos.calcular(P,__mermaRevDatos.estado({marcas:["baja","sinpeso","peso"]}));return D.visibles.find(r=>r.doc==="'+PESO+'")}',P)
        self.assertEqual(a['impacto'],-32);self.assertNotEqual(a['impacto'],-48)
        P['modo']='hoy';a=self.pg.evaluate('P=>__mermaRevDatos.calcular(P,__mermaRevDatos.estado({marcas:["sinpeso"]})).visibles.find(r=>r.doc==="'+PESO+'")',P)
        self.assertAlmostEqual(a['impacto'],2*8.234567891)

    def test_busqueda_continua_conserva_ficha_cortes_y_resumen(self):
        root=self.mount();antes=self.pg.evaluate('[__mermaRev.D.positivos,__mermaRev.D.negativos]');q=root.locator('[data-k=q]');q.click();q.press_sequentially(PESO);self.assertEqual(q.input_value(),PESO)
        self.assertEqual(root.locator('[data-tabla=casos] tbody tr').count(),1);self.assertEqual(len(self.pg.evaluate('__mermaRev.D.cs')),3);self.assertEqual(self.pg.evaluate('[__mermaRev.D.positivos,__mermaRev.D.negativos]'),antes)
        self.assertIn('Rastro en el Almacén y la carta',root.inner_text());self.assertIn('Plato A',root.inner_text());self.assertEqual(self.pg.evaluate('__requests'),[])

    def test_fecha_con_numero_invalido_y_todos_sin_marcas(self):
        root=self.mount();root.locator('[data-a=marca][data-v=fecha]').click();root.locator('[data-k=q]').fill('259900201');self.assertIn('2599',root.locator('.mrv-ficha').inner_text())
        root.locator('[data-k=todos]').check();root.locator('[data-k=q]').fill('260600105');self.assertIn('Sin dato',root.locator('.mrv-ficha').inner_text())
        self.assertEqual(self.pg.evaluate('__mermaRev.D.elegido.merma'),None)

    def test_filtros_unidades_signo_y_teclado_no_piden_python(self):
        root=self.mount();root.locator('[data-k=sentido]').select_option('Negativo');self.assertTrue(all(r['impacto']<0 for r in self.pg.evaluate('__mermaRev.D.visibles')))
        row=root.locator('[data-tabla=casos] tbody tr').last;doc=row.get_attribute('data-v');row.focus();row.press('Enter');self.assertEqual(self.pg.evaluate('__mermaRev.D.elegido.doc'),doc)
        root.locator('[data-k=todos]').check();root.locator('[data-k=prod]').select_option('1');self.assertTrue(all(r['prod']==1 for r in self.pg.evaluate('__mermaRev.D.visibles')));self.assertEqual(self.pg.evaluate('__requests'),[])

    def test_estado_precio_y_salto_a_documento_fuera_de_filtros(self):
        P=payload();P['solicitado']='259900201';P['salto']=1;root=self.mount(P);self.assertIn('fuera de los filtros',root.inner_text());root.locator('[data-a=solicitud]').click();self.assertEqual(self.pg.evaluate('__mermaRev.D.elegido.doc'),'259900201')
        Q=copy.deepcopy(P);Q['modo']='hoy';self.pg.evaluate('P=>__montarRev({data:P,parentElement:__revMount})',Q);self.assertEqual(self.pg.evaluate('__mermaRev.D.elegido.doc'),'259900201')
        root.locator('[data-k=q]').fill('260600103');self.assertNotIn('solicitado queda fuera',root.inner_text())
        Q['salto']=2;self.pg.evaluate('P=>__montarRev({data:P,parentElement:__revMount})',Q);root.locator('[data-a=solicitud]').click();self.assertEqual(self.pg.evaluate('__mermaRev.s.doc'),'259900201')

    def test_motivos_cerrados_se_conservan_al_revalorizar(self):
        P=payload();root=self.mount(P);root.locator('[data-k=q]').fill(PESO);root.locator('details[data-detalle=peso] summary').click()
        self.assertFalse(root.locator('details[data-detalle=peso]').evaluate('e=>e.open'))
        P['modo']='hoy';self.pg.evaluate('P=>__montarRev({data:P,parentElement:__revMount})',P);self.assertFalse(root.locator('details[data-detalle=peso]').evaluate('e=>e.open'))

    def test_falta_recetas_no_se_presenta_como_ningun_plato(self):
        root=self.mount(payload(recetas=None));root.locator('[data-k=q]').fill(PESO);self.assertIn('No se pudo leer la receta',root.inner_text());self.assertNotIn('Ningún plato activo',root.inner_text())

    def test_excel_cabeceras_completas_y_numericidad(self):
        root=self.mount();root.locator('[data-k=q]').fill(PESO);hs=self.pg.evaluate('__mermaRevDatos.exportar(__mermaRev)');self.assertEqual(len(hs),8)
        self.assertEqual(len(next(h for h in hs if h['nombre']=='Casos visibles')['filas']),1);self.assertEqual(len(next(h for h in hs if h['nombre']=='Cabeceras del rango')['filas']),len(payload()['filas']))
        with tempfile.TemporaryDirectory() as td:
            with self.pg.expect_download() as ev:root.locator('[data-a=excel]').click()
            p=Path(td)/'resultado.xlsx';ev.value.save_as(p)
            with zipfile.ZipFile(p) as z:
                text=''.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for w in ['8.234568','Cabeceras del rango','Marcas por cabecera','Peso habitual','Plato A']:self.assertIn(w,text)
                self.assertNotIn('<f>',text)

    def test_vacio_sin_precio_y_movil(self):
        d,h,_,_,_=muestra();root=self.mount(payload(ps=None,modo='hoy'));self.assertEqual(self.pg.evaluate('__mermaRev.D.modo'),'dia');self.assertIn('precio actual no disponible',root.inner_text())
        root=self.mount(payload(d.iloc[:0],h));self.assertEqual(self.pg.evaluate('__mermaRev.D.visibles.length'),0)
        self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),390);self.pg.set_viewport_size({'width':1323,'height':619})

    def test_listas_y_cortes_largos_por_tandas_con_excel_completo(self):
        raw,h,_,_,_=muestra();base=raw[raw.D==PESO].iloc[[2]].copy();d=pd.concat([base.assign(D='2606Largo'+str(i)) for i in range(230)],ignore_index=True)
        root=self.mount(payload(d,pd.concat([h,d],ignore_index=True)));t=root.locator('[data-tabla=casos]');self.assertEqual(t.locator('tbody tr').count(),150);t.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}');self.assertEqual(t.locator('tbody tr').count(),230)
        ultimo=t.locator('tbody tr').last;doc=ultimo.get_attribute('data-v');ultimo.focus();ultimo.press('Enter');self.assertEqual(t.locator('tbody tr').count(),230);self.assertEqual(self.pg.evaluate('__mermaRev.D.elegido.doc'),doc)
        base=raw[raw.D==PESO].iloc[[2]];d=pd.concat([base.assign(CF='C'+str(i),PF='Corte '+str(i)) for i in range(220)],ignore_index=True)
        root=self.mount(payload(d,pd.concat([h,d],ignore_index=True)));t=root.locator('[data-detalle-tabla=cortes]');self.assertEqual(t.locator('tbody tr').count(),150);t.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}');self.assertEqual(t.locator('tbody tr').count(),220)
        hs=self.pg.evaluate('__mermaRevDatos.exportar(__mermaRev)');self.assertEqual(len(next(h for h in hs if h['nombre']=='Cortes del rango')['filas']),220)


if __name__=='__main__':unittest.main(verbosity=2)
