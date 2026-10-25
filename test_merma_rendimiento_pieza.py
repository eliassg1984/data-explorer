"""Rendimiento nativo contra sus cuentas originales y con navegador (#730)."""
import copy
import inspect
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
from graficos import merma_rendimiento_datos as datos
from test_merma_proveedores_pieza import muestra as proveedor_muestra, RANGO
from test_porcionamientos_pieza import COLS, precios

ROOT=Path(__file__).parent


def muestra():
    d,c=proveedor_muestra();extra=[]
    for i,(q,m,qf,ps) in enumerate([(10,8,5,1),(10,0,5,0),(2,3,1,1),(10,None,5,None)]):
        r=d.iloc[0].copy();r['F']=r['_fecha']=pd.Timestamp('2026-06-12')+pd.Timedelta(days=i);r['D']='Observación '+str(i);r['Q']=q;r['M']=m;r['QF']=qf;r['PS']=ps;extra.append(r)
    d=pd.concat([d,pd.DataFrame(extra)],ignore_index=True)
    # Un corte repetido en la misma cabecera no repite su entrada en el factor K.
    r=d.iloc[0].copy();r['QF']=.123456789;r['PS']=.05;d=pd.concat([d,pd.DataFrame([r])],ignore_index=True)
    return d,c


def payload(d=None,ps='normal',modo='dia'):
    raw,c=muestra();P=datos.armar(raw if d is None else d,COLS,precios() if isinstance(ps,str) else ps,c,rango=RANGO)
    P['modo']=modo;return P


def base_original():
    raw,c=muestra();d=raw[(raw._fecha>=RANGO[1]-pd.Timedelta(days=mm.DIAS_NORMAL))&(raw._fecha<RANGO[1])]
    b,cs=mm.porcionamientos(d,COLS);return b,cs,c


class Contrato(unittest.TestCase):
    def test_doble_valorizacion_unidades_y_normal_sin_redondeo(self):
        P=payload();json.dumps(P,allow_nan=False);b,cs,_=base_original()
        self.assertEqual(len(P['filas']),len(b));self.assertEqual(len(P['cortes']),len(cs))
        self.assertEqual(len({r['doc'] for r in P['filas']}),len(b));self.assertEqual(len([p for p in P['productos'] if p['cod']=='0002']),2)
        a=next(r for r in P['filas'] if r['doc']=='Observación 2');self.assertEqual(a['cant'],2);self.assertEqual(a['merma'],3);self.assertEqual(a['pct'],1.5)
        self.assertEqual(P['sello'],payload()['sello']);q=payload(ps=precios()*2);self.assertNotEqual(P['sello'],q['sello']);self.assertEqual(P['sello_origen'],q['sello_origen'])
        for (cod,u),g in b.groupby(['cod','unid']):
            pid=next(i for i,p in enumerate(P['productos']) if p['cod']==cod and p['unid']==u);a=P['normales'][str(pid)];r=mm.normales(g).loc[cod]
            for k in ['n','q1','med','q3']:
                if pd.isna(r[k]):self.assertIsNone(a[k])
                else:self.assertAlmostEqual(a[k],r[k])

    def test_marcas_salen_de_la_cuenta_canonica(self):
        P=payload();b,cs,c=base_original();por_doc={r['doc']:r for r in P['filas']}
        for (_,u),g in b.groupby(['cod','unid']):
            xs=mm.marcar(mm.con_proveedor(mm.valorizar(g,mm.VALOR_DIA,precios()),c),mm.normales(g),cs)
            for r in xs.itertuples(index=False):self.assertEqual(por_doc[r.doc]['marcas'],[k for k in mm.MARCAS if bool(getattr(r,'m_'+k))])
        self.assertIn('alta',por_doc['Observación 0']['marcas']);self.assertIn('sinpeso',por_doc['Observación 1']['marcas'])

    def test_salto_repetido_a_corte_se_identifica_sin_cambiar_firma(self):
        ss={}
        with patch.object(mm,'st',SimpleNamespace(session_state=ss)):
            mm.ir_al_corte('0001','0');uno=ss['_merma_rend_salto'];mm.ir_al_corte('0001','0')
            self.assertEqual(ss['_merma_rend_salto'],uno+1);self.assertEqual(ss[mm.K_CORTE],'0')

    def test_firma_y_despacho_publicos(self):
        self.assertEqual(list(inspect.signature(mm.tarjeta_rendimiento).parameters),['d_hist','cols','rango'])
        with patch('graficos.merma_rendimiento_pieza.renderizar') as nueva:
            mm.tarjeta_rendimiento(pd.DataFrame(),COLS,RANGO);self.assertEqual(nueva.call_args.args[1],COLS)

    def test_foco_validado_y_cache_independiente_de_valorizacion(self):
        from graficos import merma_rendimiento_pieza as pieza
        raw,c=muestra();ss={mm.K_VALOR:mm.VALOR_HOY}
        fake=SimpleNamespace(session_state=ss,markdown=Mock(),container=lambda **kw:nullcontext())
        with patch.object(pieza,'st',fake),patch.object(mm,'st',fake),patch.object(mm,'precios_hoy',return_value=precios()),patch.object(mm,'_compras',return_value=c),patch.object(mm,'control_valorizacion'),patch.object(mm,'_avisar_a') as aviso,patch.object(pieza,'_PIEZA') as componente,patch.object(datos,'armar',wraps=datos.armar) as armar:
            pieza.renderizar(raw,COLS,RANGO);ss[mm.K_VALOR]=mm.VALOR_DIA;pieza.renderizar(raw,COLS,RANGO)
            self.assertEqual(armar.call_count,1);self.assertEqual(componente.call_args.kwargs['data']['modo'],'dia');P=ss['_merma_rendimiento_cache'][1]
            for v in [dict(sello='viejo',cod='0001',unid='KILOS'),dict(sello=P['sello'],cod='0001',unid='UNIDAD'),dict(sello=P['sello'],cod=['0001'],unid='KILOS')]:
                ss['merma_rendimiento_pieza']={'producto':v};pieza._producto();self.assertNotIn(mm._K_PROD,ss)
            ss['merma_rendimiento_pieza']={'producto':dict(sello=P['sello'],cod='0001',unid='KILOS')};pieza._producto();self.assertEqual(ss[mm._K_PROD],'0001');aviso.assert_called_once_with(mm.SEC_PROV)


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
        cls.pg.set_content('<div id="host"></div>');cls.pg.add_style_tag(content=':root{--alto-util:531px;--alto-util-base:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--accent:rgb(108,92,231);--accent-deep:rgb(80,65,180);--accent-tint:rgb(245,243,255);--bg-card:white;--border:rgb(220,220,230);--danger:crimson;}body{margin:0}')
        cls.pg.evaluate('css=>{const h=document.querySelector("#host");const sr=h.attachShadow({mode:"open"});const style=document.createElement("style");style.textContent=css;sr.append(style);window.__raiz=document.createElement("div");sr.append(__raiz);}',(ROOT/'graficos/merma_rendimiento.css').read_text(encoding='utf-8'))
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/merma_rendimiento.js').read_text(encoding='utf-8').replace('export default function(component)','window.__montarRend=function(component)'))

    @classmethod
    def tearDownClass(cls):cls.b.close();cls.pw.stop()

    def calc(self,P,s):return self.pg.evaluate('([P,s])=>{const {rows,xs,cs,docs,filasCorte,...D}=__mermaRendDatos.calcular(P,__mermaRendDatos.estado(s));return D;}',[P,s])

    def mount(self,P=None):
        self.pg.evaluate('P=>{window.__mermaRend?.abort.abort();window.__mermaRend?.ro.disconnect();window.__mermaRend=null;window.__requests=[];__montarRend({data:P,parentElement:__raiz,setTriggerValue:(...a)=>__requests.push(a)})}',P or payload())
        return self.pg.locator('.mre')

    def igual(self,a,b):
        if b is None or pd.isna(b):self.assertIsNone(a)
        else:self.assertAlmostEqual(a,b,places=7)

    def test_ventanas_bases_kpi_y_series_contra_originales(self):
        base,cs,c=base_original();P=payload()
        for ventana,meses in mm.VENTANAS.items():
            for modo in ['hoy','dia']:
                P['modo']=modo
                for (cod,u),g in base.groupby(['cod','unid']):
                    pid=next(i for i,p in enumerate(P['productos']) if p['cod']==cod and p['unid']==u)
                    xs=mm.valorizar(g[g.fecha>=RANGO[1]-pd.DateOffset(months=meses)],mm.VALOR_HOY if modo=='hoy' else mm.VALOR_DIA,precios())
                    D=self.calc(P,dict(ventana=ventana,prod=pid))
                    if xs.empty:self.assertFalse(any(r['id']==pid for r in D['productos']));continue
                    self.assertEqual(D['kpi']['n'],len(xs));self.igual(D['kpi']['pct'],xs.merma_cant.sum()/xs['cant'].sum());self.igual(D['kpi']['valor'],xs.valor.sum())
                    queda=(xs['cant']-xs.merma_cant).sum();self.igual(D['kpi']['util'],xs.costo_dia.sum()/queda if queda>0 else None)
                    ms=mm.por_mes(xs);self.assertEqual(len(D['mes']),len(ms))
                    for a,r in zip(D['mes'],ms.itertuples(index=False)):
                        self.assertEqual(a['mes'],r.mes.isoformat());self.igual(a['pct'],r.pct);self.igual(a['pkg'],r.pkg)
                    ch=mm.cambios(xs,RANGO[1]);actual=next((r for r in D['ch'] if r['prod']==pid),None)
                    if len(ch):
                        self.assertIsNotNone(actual)
                        for k in ['pct_ant','pct_rec','dpp','dprecio','impacto']:self.igual(actual[k],ch.loc[cod,k])
                    else:self.assertIsNone(actual)

    def test_cortes_factores_y_mensual_deduplican_cabecera(self):
        base,cs,_=base_original();P=payload()
        for ventana,meses in mm.VENTANAS.items():
            for (cod,u),g in base.groupby(['cod','unid']):
                pid=next(i for i,p in enumerate(P['productos']) if p['cod']==cod and p['unid']==u);xs=g[g.fecha>=RANGO[1]-pd.DateOffset(months=meses)]
                if xs.empty:continue
                D=self.calc(P,dict(ventana=ventana,prod=pid));pc=mm.precios_de_cortes(xs,cs,RANGO[1]);self.assertEqual(len(D['pc']),len(pc))
                for a,r in zip(D['pc'],pc.to_dict('records')):
                    self.assertEqual(a['clave'],r['clave']);self.igual(a['valor'],r['valor']);self.igual(a['var'],r['var'])
                    for lado in ['a','b']:
                        for k in ['n','P','K','m','g']:self.igual(a[lado][k],r[lado][k])
                    if r['desglose']:
                        for k in mm.FACTORES:self.igual(a['desglose'][k],r['desglose'][k])
                        self.igual(abs(r['desglose'][a['causa']]),max(abs(v) for v in r['desglose'].values()))
                        self.igual(sum(a['desglose'].values()),r['b']['P']-r['a']['P'])
                    else:self.assertIsNone(a['desglose'])
                    E=self.calc(P,dict(ventana=ventana,prod=pid,corte=a['key']));filas=cs[cs.doc.isin(xs.doc)&(mm.clave_corte(cs)==r['clave'])];med=D['med'];pm=mm.precio_corte_por_mes(xs,filas,med)
                    self.assertEqual(len(E['mesCorte']),len(pm))
                    for x,y in zip(E['mesCorte'],pm.to_dict('records')):
                        for k in ['precio','merma','normal']:self.igual(x[k],y[k])

    def test_lmdi_sin_base_y_con_precio_igual(self):
        a=dict(n=4,P=10.,K=4.,g=2.,m=.2);b={**a,'K':5.,'m':0.};expected=mm.desglose_precio(a,b)
        got=self.pg.evaluate('([a,b])=>__mermaRendDatos.desglose(a,b)',[a,b])
        for k in expected:self.igual(got[k],expected[k])
        self.igual(sum(got.values()),0)
        for k in ['P','K','g']:
            q={**a,k:0};self.assertIsNone(self.pg.evaluate('([a,b])=>__mermaRendDatos.desglose(a,b)',[q,b]))

    def test_corte_con_dos_unidades_no_se_mezcla(self):
        raw,_=muestra();d=raw[raw.C=='0001'].copy();a=d[d._fecha>=pd.Timestamp('2026-01-01')].iloc[[0]].assign(UF='UNIDAD',QF=1);b=a.assign(UF='CAJAS',QF=2);d=pd.concat([d,a,b],ignore_index=True);P=payload(d)
        pid=next(i for i,p in enumerate(P['productos']) if p['cod']=='0001');D=self.calc(P,dict(prod=pid,ventana='18 meses'))
        self.assertEqual({r['unid'] for r in D['pc'] if r['clave']=='0'},{'KILOS','UNIDAD','CAJAS'})

    def test_controles_locales_busqueda_en_shadow_y_ficha(self):
        root=self.mount();root.locator('[data-a=ventana][data-v="6 meses"]').click();root.locator('[data-a=precio][data-v="Costo del insumo"]').click();root.locator('[data-a=lista][data-v="Productos que cambiaron"]').click()
        q=root.locator('[data-k=q]');q.click();q.press_sequentially('Observación');self.assertEqual(q.input_value(),'Observación');self.assertEqual(self.pg.evaluate('__mermaRend.s.q'),'Observación')
        k=self.pg.evaluate('__mermaRend.D.kpi.n');self.assertGreater(k,self.pg.evaluate('__mermaRend.D.docs.length'));self.assertEqual(self.pg.evaluate('__requests'),[])
        row=root.locator('[data-tabla=docs] tbody tr').first;row.focus();row.press('Enter');dialog=root.get_by_role('dialog');self.assertTrue(dialog.is_visible());self.assertIn('Costo del día',root.inner_text())
        dialog.get_by_role('button',name='Cerrar ficha').press('Tab');self.assertEqual(self.pg.evaluate('__raiz.getRootNode().activeElement.getAttribute("aria-label")'),'Cerrar ficha')
        dialog.press('Escape');self.assertEqual(root.get_by_role('dialog').count(),0)

    def test_filtro_mensual_no_cambia_kpi_ni_mutila_cortes(self):
        root=self.mount();antes=self.pg.evaluate('__mermaRend.D.kpi');root.locator('.mre-grafica').first.locator('[data-a=mes]').last.dispatch_event('click')
        self.assertEqual(self.pg.evaluate('__mermaRend.D.kpi'),antes);self.assertEqual(len({r['fecha'][:7] for r in self.pg.evaluate('__mermaRend.D.docs')}),1)
        root.locator('[data-a=limpiarMes]').click();root.locator('[data-k=q]').fill('Corte 0');self.assertEqual(self.pg.evaluate('__mermaRend.D.kpi'),antes)

    def test_remontaje_conserva_estado_y_salto_externo_corte(self):
        P=payload();P['inicial']=dict(cod='0001',precio=mm.MODO_CORTE,corte='0');P['comun']='0001-0';root=self.mount(P)
        root.locator('[data-a=precio][data-v="Costo del insumo"]').click();root.locator('[data-a=ventana][data-v="6 meses"]').click();root.locator('[data-k=q]').fill('Corte')
        Q=copy.deepcopy(P);Q['modo']='hoy';self.pg.evaluate('P=>__montarRend({data:P,parentElement:__raiz,setTriggerValue:(...a)=>__requests.push(a)})',Q)
        self.assertEqual(self.pg.evaluate('__mermaRend.s.precio'),mm.MODO_INSUMO);self.assertEqual(self.pg.evaluate('__mermaRend.s.q'),'Corte');self.assertEqual(self.pg.evaluate('__mermaRend.s.ventana'),'6 meses')
        Q['inicial']['corte']='1';Q['comun']='0001-1';self.pg.evaluate('P=>__montarRend({data:P,parentElement:__raiz})',Q);self.assertEqual(self.pg.evaluate('__mermaRend.D.corte.clave'),'1')

    def test_producto_comun_envia_solo_codigo_unidad_y_sello(self):
        P=payload();root=self.mount(P);pid=next(i for i,p in enumerate(P['productos']) if p['cod']=='0002')
        root.locator('[data-k=prod]').select_option(str(pid));r=self.pg.evaluate('__requests');self.assertEqual(len(r),1);self.assertEqual(r[0][0],'producto');self.assertEqual(r[0][1],dict(sello=P['sello'],cod='0002',unid=P['productos'][pid]['unid']))

    def test_repetir_salto_y_merma_ausente_no_inventan_rendimiento(self):
        P=payload();P['inicial']=dict(cod='0001',corte='0',precio=mm.MODO_CORTE);P['comun']='salto1';P['salto']=1;root=self.mount(P)
        root.locator('[data-a=precio][data-v="Costo del insumo"]').click();P['salto']=2;P['comun']='salto2'
        self.pg.evaluate('P=>__montarRend({data:P,parentElement:__raiz})',P);self.assertEqual(self.pg.evaluate('__mermaRend.s.precio'),mm.MODO_CORTE)
        root.locator('[data-k=q]').fill('Observación 3');root.locator('[data-tabla=docs] tbody tr').first.click()
        self.assertIn('Falta merma',root.get_by_role('dialog').inner_text());self.assertIn('Merma sin dato',root.get_by_role('dialog').inner_text())

    def test_excel_numerico_completo_y_filtros_identificados(self):
        root=self.mount();root.locator('[data-k=q]').fill('no existe');hs=self.pg.evaluate('__mermaRendDatos.exportar(__mermaRend)');self.assertEqual(len(hs),8)
        self.assertEqual(len(next(h for h in hs if h['nombre']=='Historial visible')['filas']),0);self.assertGreater(len(next(h for h in hs if h['nombre']=='Historial completo')['filas']),0)
        with tempfile.TemporaryDirectory() as td:
            with self.pg.expect_download() as ev:root.locator('[data-a=excel]').click()
            p=Path(td)/'resultado.xlsx';ev.value.save_as(p)
            with zipfile.ZipFile(p) as z:
                text=''.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for w in ['10.123457','Factores del corte','LMDI','Historial completo','Unidad de origen']:self.assertIn(w,text)
                self.assertNotIn('<f>',text)

    def test_vacio_sin_precios_y_movil(self):
        raw,_=muestra();root=self.mount(payload(ps=None,modo='hoy'));self.assertIn('precio actual no disponible',root.inner_text());self.assertEqual(self.pg.evaluate('__mermaRend.D.modo'),'dia')
        root=self.mount(payload(raw.iloc[:0]));self.assertEqual(self.pg.evaluate('__mermaRend.D.kpi.n'),0)
        self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),390);self.pg.set_viewport_size({'width':1323,'height':619})

    def test_historia_larga_se_dibuja_por_tandas_y_exporta_toda(self):
        raw,_=muestra();base=raw.iloc[:2];d=pd.concat([base.assign(D='Largo '+str(i),F=pd.Timestamp('2026-06-10'),_fecha=pd.Timestamp('2026-06-10')) for i in range(230)],ignore_index=True)
        root=self.mount(payload(d));t=root.locator('[data-tabla=docs]');self.assertEqual(t.locator('tbody tr').count(),150);t.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}');self.assertEqual(t.locator('tbody tr').count(),230)
        hs=self.pg.evaluate('__mermaRendDatos.exportar(__mermaRend)');self.assertEqual(len(next(h for h in hs if h['nombre']=='Historial completo')['filas']),230)


if __name__=='__main__':unittest.main(verbosity=2)
