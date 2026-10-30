"""Celdas canónicas, recorte y acciones acotadas de SUNAT › Documentos (#741)."""
import json
import unittest
import zipfile
from contextlib import ExitStack, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from graficos.compras import documentos_sunat as ds
from graficos.compras import sunat_documentos_datos as datos
from graficos.compras import sunat_documentos_pieza as pieza

ROOT=Path(__file__).parent


def muestra(n=0):
    rows=[];sire=[]
    def add(car,doc,estado,total,sis,ruc,mon='PEN',tc=1,tipo='Mercadería',nombre=None):
        base=None if total is None else total/1.18;bs=None if sis is None else sis/1.18
        r=dict(car=car,documento=doc,fecha_emision=pd.Timestamp('2026-01-02'),proveedor=nombre or ('Proveedor '+ruc if car else ''),ruc_proveedor=ruc if car else '',proveedor_sistema=('Proveedor '+ruc if sis is not None else ''),ruc_sistema=ruc if sis is not None else '',documento_sistema=doc if sis is not None else '',base_sunat=base,igv_sunat=None if base is None else total-base,total_sunat=total,base_sistema=bs,igv_sistema=None if bs is None else sis-bs,total_sistema=sis,estado=estado,tipo=tipo,tipo_por='Clasificación de prueba')
        rows.append(r)
        if car:sire.append(dict(car=car,documento=doc,fecha_emision=pd.Timestamp('2026-01-02'),proveedor=r['proveedor'],ruc_proveedor=ruc,serie=doc.split('-')[0],numero=doc.split('-')[1],moneda=mon,tipo_cambio=tc,tipo_nombre='Factura',tipo_cdp='01',detraccion='D' if tc!=1 else '',estado='Activo',situacion='0',total=total))
    add('car-a','F001-1','Coincide',118,118,'00000000001')
    add('car-b','F001-1','Diferencia',200,220,'00000000002')
    add('car-c','F002-3','Solo SUNAT',-118,None,'00000000003',tipo='Servicios')
    add('','F003-4','Solo sistema',None,59,'00000000004',tipo='Otros bienes')
    add('car-e','F004-5','Diferencia',390,400,'00000000005','USD',3.9)
    for i in range(n):add('car-'+str(i+100),'F005-'+str(i+100),'Solo SUNAT',.123456*(i+1),None,'00000000100')
    return pd.DataFrame(rows),pd.DataFrame(sire)


def payload(n=0):
    c,s=muestra(n);xmls={ds.sunat.claves_original(s.iloc[0].to_dict())[1]}
    return datos.armar(c,s,xmls,{'Desde':'2026-01-01','Hasta':'2026-01-31'})|dict(inicial={'estado':''},salto=0)


class Contrato(unittest.TestCase):
    def test_todas_las_celdas_contra_la_tabla_original(self):
        c,s=muestra();xmls={ds.sunat.claves_original(s.iloc[0].to_dict())[1]}
        with patch.object(ds,'st',SimpleNamespace(session_state={},info=Mock())),patch.object(ds.sunat,'claves_xml_en_r2',return_value=xmls),patch.object(ds,'AgGrid',return_value=SimpleNamespace(selected_rows=None)) as grid:
            self.assertIsNone(ds._tabla_documentos(c,s))
            pd.testing.assert_frame_equal(datos.filas_tabla(c,s,xmls),grid.call_args.args[0])

    def test_origen_no_muta_y_moneda_ya_convertida_no_se_reconvierte(self):
        c,s=muestra();antes=c.copy(deep=True);P=payload();pd.testing.assert_frame_equal(c,antes)
        r=next(r for r in P['filas'] if r['_car']=='car-e');self.assertEqual(r['Total'],390);self.assertEqual(r['_conv'],ds.sunat.simbolo_moneda('USD')+' 100.00');self.assertEqual(r['brecha'],10)
        self.assertEqual(P['filas'][0]['ruc'],'00000000001');json.dumps(P,allow_nan=False)

    def test_car_identifica_sin_colisiones_y_id_persiste_al_reordenar(self):
        c,s=muestra();P=datos.armar(c,s);Q=datos.armar(c.iloc[::-1],s)
        self.assertEqual({r['_car']:r['id'] for r in P['filas']},{r['_car']:r['id'] for r in Q['filas']})
        self.assertNotEqual(P['filas'][0]['id'],P['filas'][1]['id'])
        self.assertEqual(pieza._doc(P,s,P['filas'][1]['id'])['ruc_proveedor'],'00000000002')

    def test_acciones_solo_del_censo_actual_y_solo_sunat_para_ingresar(self):
        P=payload();a=dict(sello=P['sello'],nonce='1',que='ficha',id=P['filas'][0]['id'])
        self.assertEqual(pieza.validar_accion(a,P)['id'],P['filas'][0]['id'])
        for b in [a|{'sello':'viejo'},a|{'id':'inexistente'},a|{'id':[1]},a|{'nonce':None},a|{'que':'ingreso'},a|{'id':P['filas'][3]['id']}]:self.assertIsNone(pieza.validar_accion(b,P))
        self.assertEqual(pieza.validar_accion(a|{'que':'ingreso','id':P['filas'][2]['id']},P)['que'],'ingreso')
        lote=dict(sello=P['sello'],nonce='2',que='lote',ids=[P['filas'][0]['id']]*2)
        self.assertEqual(pieza.validar_accion(lote,P)['ids'],[P['filas'][0]['id']]);self.assertIsNone(pieza.validar_accion(lote|{'ids':['ajeno']},P))

    def test_pares_por_importe_y_validar_lineas(self):
        lx=[dict(importe=100,igv=18),dict(importe=136.27,igv=24.53),dict(importe=5,igv=0)];la=[['A',1,'U',100,100],['B',1,'U',160.8,160.8]]
        self.assertEqual(datos.completar_pares(lx,la,[0,None,None]),[0,1,None])
        P=payload();i=P['filas'][0]['id']
        self.assertEqual(pieza.validar_lineas(dict(id=i,sello=P['sello']),P),i)
        for b in [dict(id=i,sello='viejo'),dict(id='otro',sello=P['sello']),dict(id=[i],sello=P['sello']),None]:self.assertIsNone(pieza.validar_lineas(b,P))

    def test_lineas_de_un_documento_con_su_causa(self):
        P=payload();r=next(x for x in P['filas'] if x['_car']=='car-b')
        L=pd.DataFrame([dict(NOMBRE_PRODUCTO='Prod',CANTIDAD_COMPRA=1,UNIDAD_DE_INGRESO='UND',PRECIO_UNIT=10,VALOR_COMPRA=10,FECHA_PROCESO_DOC=pd.Timestamp('2026-01-03'))])
        with patch.object(ds,'_lineas_parquet_del_documento',return_value=L),patch.object(ds,'_parear_lineas_sistema',return_value=[0]),patch.object(ds.sunat,'lineas_xml',return_value=[dict(descripcion='PROD',cantidad=1,unidad='u',precio_unitario=10,importe=10,igv=1.8,isc=0,igv_porcentaje=18)]):
            d=datos.lineas_documento(r,dict(moneda='PEN'),None,b'x')
        self.assertEqual((d['fp'],d['pa'],d['la'][0][0],d['lx'][0][0]),('03/01/2026',[0],'Prod','PROD'));self.assertTrue(d['ca']);json.dumps(d,allow_nan=False)

    def test_salto_externo_repetido_y_firma_publica(self):
        import inspect
        self.assertEqual(len(inspect.signature(ds.renderizar_documentos_sunat).parameters),3)
        with patch.object(ds,'st',SimpleNamespace(session_state={})):
            ds.poner_estado('Solo SUNAT');ds.poner_estado('Solo SUNAT');self.assertEqual(ds.st.session_state['_sunat_docs_salto'],2)

    def test_nulos_no_finitos_y_vacio_son_json_validos(self):
        c,s=muestra();c.loc[0,'opcional']=float('inf');P=datos.armar(c,s);self.assertIsNone(P['filas'][0]['raw']['opcional']);json.dumps(P,allow_nan=False)
        Q=datos.armar(c.iloc[:0],s.iloc[:0]);self.assertEqual(Q['filas'],[]);json.dumps(Q,allow_nan=False)

    def test_render_cache_y_lote_solo_con_las_filas_validadas(self):
        c,s=muestra();ss={};mes=next(k for k,v in ds._MES_SUNAT.items() if v is None)
        fake=SimpleNamespace(session_state=ss,markdown=Mock(),caption=Mock(),info=Mock(),error=Mock(),container=lambda **kw:nullcontext(),columns=lambda *a,**kw:[nullcontext() for _ in range(4)],empty=lambda:nullcontext(),button=lambda *a,**kw:False,selectbox=lambda *a,**kw:mes,spinner=lambda *a,**kw:nullcontext())
        with ExitStack() as stack:
            for contexto in [
                patch.object(pieza,'st',fake),patch.object(ds,'st',fake),
                patch.object(ds,'_rango_vigente',return_value=('2026-01-01','2026-01-31')),
                patch.object(ds.sunat,'comprobantes_rango',return_value=(s,'parquet')),
                patch.object(ds,'_parquet_agrupado_por_documento',return_value=c),
                patch.object(ds,'cruzar_con_parquet',return_value=c),
                patch.object(ds.data,'notas_credito_compras',return_value=None),
                patch.object(ds.data,'sello_datos',return_value='sello'),
                patch.object(ds,'_tablas_tipo',return_value={}),
                patch.object(pieza.tipo_compra,'clasificar',return_value=c),
                patch.object(ds,'_filtro_proveedor',return_value=None),
                patch.object(ds,'_publicar_conteos'),patch.object(ds,'_aviso_origen'),
                patch.object(ds.sunat,'claves_xml_en_r2',return_value=frozenset()),
                patch.object(ds,'_ficha_abierta',return_value=False),
                patch.object(ds,'_ingreso_abierto',return_value=False),
            ]:
                stack.enter_context(contexto)
            calendario=stack.enter_context(patch.object(ds,'selector_fecha_tarjeta'))
            avance=stack.enter_context(patch.object(ds,'_avance_lote_xml'))
            build=stack.enter_context(patch.object(datos,'armar',wraps=datos.armar))
            comp=stack.enter_context(patch.object(pieza,'_PIEZA'))
            stack.enter_context(patch.object(pieza,'_montar',pieza._montar_cuerpo))
            enviar=stack.enter_context(patch.object(ds,'_pedir_lote'))
            abrir=stack.enter_context(patch.object(ds,'_atender_pedido_de_ficha'))
            pieza.renderizar(c,'FECHA');P=comp.call_args.kwargs['data'];ss[pieza._KEY]={'accion':dict(que='lote',sello=P['sello'],nonce='n1',ids=[P['filas'][2]['id']])}
            pieza.renderizar(c,'FECHA');self.assertEqual(build.call_count,1);self.assertTrue(ss[ds._K_LOTE_ABIERTO]);enviar.assert_not_called()
            self.assertEqual(avance.call_args.args[0]['car'].tolist(),['car-c'])
            self.assertIn('on_accion_change',comp.call_args.kwargs)
            self.assertEqual(calendario.call_args.args,('sunat_f','sunat_fecha_flag'))
            self.assertNotIn('categoria',calendario.call_args.kwargs)
            ss[pieza._KEY]={'accion':dict(que='ficha',sello=P['sello'],nonce='n2',id=P['filas'][1]['id'])}
            pieza.renderizar(c,'FECHA');self.assertEqual(abrir.call_args.args[1]['ruc_proveedor'],'00000000002')
            ss[pieza._KEY]={'accion':dict(que='ficha',sello='anterior',nonce='n3',id=P['filas'][0]['id'])}
            pieza.renderizar(c,'FECHA');self.assertEqual(abrir.call_count,1);enviar.assert_not_called()


try:
    from playwright.sync_api import sync_playwright
except ImportError:sync_playwright=None


@unittest.skipIf(sync_playwright is None,'sin Playwright')
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw=sync_playwright().start()
        try:cls.br=cls.pw.chromium.launch()
        except Exception as e:cls.pw.stop();raise unittest.SkipTest(str(e))
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(5000)
        cls.pg.route('https://sud.test.example/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://sud.test.example/')
        css=(ROOT/'graficos/compras/sunat_documentos.css').read_text(encoding='utf-8')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"});window.mount=document.createElement("div");const st=document.createElement("style");st.textContent=css;mount.append(st);sr.append(mount)}',css)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/compras/sunat_documentos.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarSUD=function(component)'),type='module');cls.pg.wait_for_function('typeof montarSUD==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,s=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,s])=>{sessionStorage.setItem("sunat_docs_741",JSON.stringify(s||{}));window.pedidos=[];window.__sudLineas={};mount.__sudClave=null;montarSUD({data:P,parentElement:mount,setTriggerValue:(k,v)=>pedidos.push({k,v})})}',[P or payload(),s]);return self.pg.locator('.sud')

    def test_filtros_y_totales_separados_por_fuente(self):
        self.mount();states=[dict(estado=e,q=q,tipo=t,xml=x,brecha=b,orden='fecha',dir='desc') for e in ['',*payload()['estados']] for q in ['','00000000002'] for t in ['','Servicios'] for x in ['','si','no'] for b in [False,True]]
        out=self.pg.evaluate('ss=>ss.map(s=>{const d=__sunatDocumentosDatos.calcular(__sunatDocumentos.B,s);return{ids:d.visibles.map(r=>r.id),n:d.censo.length,conteos:d.conteos,totales:d.totales}})',states)
        P=payload()
        for s,j in zip(states,out):
            base=[r for r in P['filas'] if (not s['q'] or s['q'] in ' '.join(str(r.get(k) or '') for k in ['Documento','Proveedor','ruc'])) and (not s['tipo'] or r['Tipo']==s['tipo']) and (not s['xml'] or bool(r['XML'])==(s['xml']=='si')) and (not s['brecha'] or r['brecha'] is not None and abs(r['brecha'])>P['tolerancia'])]
            rows=[r for r in base if not s['estado'] or r[P['estado_col']]==s['estado']]
            self.assertEqual(set(j['ids']),{r['id'] for r in rows});self.assertEqual(j['n'],len(base))
            self.assertEqual(j['conteos'],{e:sum(r[P['estado_col']]==e for r in base) for e in P['estados']})
            for k,field in [('sunat','total_sunat'),('sistema','total_sistema')]:
                vals=[r['raw'][field] for r in rows if r['raw'][field] is not None]
                self.assertEqual(j['totales'][k],sum(vals) if vals else None)

    def test_elegir_ordenar_y_buscar_no_piden_acciones(self):
        root=self.mount();root.locator('tbody tr[data-id]').first.click();self.assertIn('Almacén',root.locator('.sud-panel').inner_text())
        root.locator('[data-a=orden][data-v=Total]').click();root.locator('[data-k=q]').fill('00000000002');self.pg.wait_for_function('__sunatDocumentos.D.visibles.length===1')
        self.assertEqual(self.pg.evaluate('pedidos.filter(p=>p.k==="accion").length'),0);self.assertEqual(self.pg.evaluate('getComputedStyle(mount.querySelector(".sud")).fontSize'),'13px')

    def test_elegir_pide_las_lineas_una_vez_y_las_muestra(self):
        root=self.mount();fila=root.locator('tbody tr[data-id]',has_text='F001-1').first;fila.click();self.pg.wait_for_function('pedidos.some(p=>p.k==="lineas")')
        a=self.pg.evaluate('pedidos.find(p=>p.k==="lineas").v');self.assertIn(a['id'],[r['id'] for r in payload()['filas']])
        self.assertIn('Trayendo las líneas',root.locator('.sud-panel').inner_text())
        d=dict(la=[['Producto A',2,'KILOS',59,118]],lx=[['PRODUCTO A',2,'kg',50,100,18,0]],pa=[0],mon='PEN',tc=1,fp='02/01/2026',ck='igv_adentro',ca='Parece cargado con el IGV adentro.')
        self.pg.evaluate('([id,d])=>montarSUD({data:{parte:"lineas",id,d},parentElement:mount,setTriggerValue:()=>{}})',[a['id'],d])
        t=root.locator('.sud-panel').inner_text();self.assertIn('Parece cargado con el IGV adentro.',t);self.assertIn('Producto A',t);self.assertIn('Es el neto',t.replace('El neto del Almacén es','Es el neto'))
        root.locator('[data-a=dtab][data-v=fa]').click();self.assertIn('PRODUCTO A',root.locator('.sud-panel').inner_text())
        root.locator('[data-a=lado]').click();self.assertIn('con IGV',root.locator('.sud-lado').inner_text())
        root.locator('[data-a=nolado]').click();self.assertEqual(root.locator('.sud-lado').count(),0)
        root.locator('tbody tr[data-id]',has_text='F004-5').click();fila.click();self.pg.wait_for_timeout(250)
        self.assertEqual(self.pg.evaluate(f'pedidos.filter(p=>p.k==="lineas"&&p.v.id==="{a["id"]}").length'),1)

    def test_mayor_diferencia_y_causa_con_el_total_igual(self):
        c,s=muestra();c.loc[0,'base_sistema']+=7;c.loc[0,'igv_sistema']-=7;c.loc[0,'estado']='Diferencia';P=datos.armar(c,s)|dict(inicial={'estado':''},salto=0)
        root=self.mount(P);root.locator('[data-a=estado][data-v=Diferencia]').click()
        self.assertEqual(self.pg.evaluate('__sunatDocumentos.D.visibles.find(r=>r._car==="car-a")._mayor'),7)
        self.assertEqual(self.pg.evaluate('__sunatDocumentos.s.elegido'),self.pg.evaluate('__sunatDocumentos.D.visibles[0].id'))
        self.assertGreater(root.locator('[data-k=causa] option').count(),1)
        k=root.locator('[data-k=causa] option').nth(1).get_attribute('value');root.locator('[data-k=causa]').select_option(k)
        self.assertTrue(self.pg.evaluate('__sunatDocumentos.D.visibles.every(r=>r._ck===__sunatDocumentos.s.causa)'))

    def test_ampliar_trae_todas_las_columnas(self):
        root=self.mount();self.assertEqual(root.locator('thead th').count(),6);self.assertEqual(root.locator('.sud-panel').count(),1)
        root.locator('[data-a=amp]').click();self.assertEqual(root.locator('thead th').count(),11);self.assertEqual(root.locator('.sud-panel').count(),0)
        root.locator('[data-a=amp]').click();self.assertEqual(root.locator('thead th').count(),6)

    def test_acciones_envian_id_y_recorte_sin_fabricar_filas(self):
        root=self.mount();root.locator('tbody tr[data-id]',has_text='F001-1').first.click();root.locator('[data-a=ficha]').first.click();a=self.pg.evaluate('pedidos.filter(p=>p.k==="accion")[0].v');self.assertEqual(a['que'],'ficha');self.assertIn(a['id'],[r['id'] for r in payload()['filas']])
        root.locator('[data-a=estado][data-v="Solo SUNAT"]').click();root.locator('[data-a=lote]').click();a=self.pg.evaluate('pedidos.filter(p=>p.k==="accion").at(-1).v');self.assertEqual(a['que'],'lote');self.assertEqual(len(a['ids']),1);self.assertNotIn('raw',a)
        root.locator('tbody tr[data-id]').first.click();root.locator('[data-a=ingreso]').click();self.assertEqual(self.pg.evaluate('pedidos.filter(p=>p.k==="accion").at(-1).v.que'),'ingreso')

    def test_repetir_salto_externo_y_conservar_filtros_al_rerun(self):
        root=self.mount();root.locator('[data-a=estado][data-v=Diferencia]').click();self.pg.evaluate('montarSUD({data:__sunatDocumentos.P,parentElement:mount,setTriggerValue:()=>{}})');self.assertEqual(self.pg.evaluate('__sunatDocumentos.s.estado'),'Diferencia')
        self.pg.evaluate('montarSUD({data:{...__sunatDocumentos.P,salto:1},parentElement:mount,setTriggerValue:()=>{}})');self.assertEqual(self.pg.evaluate('__sunatDocumentos.s.estado'),'')

    def test_tandas_excel_completo_y_codigos_como_texto(self):
        root=self.mount(payload(340));self.assertEqual(root.locator('tbody tr[data-id]').count(),150);root.locator('[data-a=mas]').click();self.assertEqual(root.locator('tbody tr[data-id]').count(),300)
        root.locator('[data-k=q]').fill('00000000002');self.pg.wait_for_function('__sunatDocumentos.D.visibles.length===1')
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'sud.xlsx';dl.value.save_as(p)
            with zipfile.ZipFile(p) as z:
                self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),6)
                self.assertIn('00000000002',z.read('xl/worksheets/sheet1.xml').decode());self.assertEqual(z.read('xl/worksheets/sheet3.xml').decode().count('<row r='),346)

    def test_movil_ficha_y_sin_contraparte_no_inventa_diferencia(self):
        root=self.mount();self.pg.set_viewport_size({'width':390,'height':844});root.locator('[data-a=estado][data-v="Solo sistema"]').click();root.locator('tbody tr[data-id]').click()
        panel=root.locator('.sud-panel');self.assertIn('—',panel.inner_text());self.assertTrue(self.pg.evaluate('document.documentElement.scrollWidth<=innerWidth+2'))
        box=panel.bounding_box();self.assertGreaterEqual(box['x'],0);self.assertLessEqual(box['x']+box['width'],390)

    def test_brecha_en_base_con_total_igual_tambien_se_puede_revisar(self):
        c,s=muestra();c.loc[0,'base_sistema']+=1;P=datos.armar(c,s)|dict(inicial={'estado':''},salto=0)
        root=self.mount(P);root.locator('[data-k=brecha]').check()
        self.assertIn(P['filas'][0]['id'],self.pg.evaluate('__sunatDocumentos.D.visibles.map(r=>r.id)'))
        self.assertEqual(self.pg.evaluate('__sunatDocumentos.D.visibles.find(r=>r._car==="car-a").brecha'),0)

    def test_cargar_mas_y_elegir_conservan_el_scroll(self):
        root=self.mount(payload(340));self.pg.set_viewport_size({'width':390,'height':844})
        wrap=root.locator('.sud-wrap');wrap.evaluate('e=>{e.scrollTop=300;e.scrollLeft=100}')
        root.locator('[data-a=mas]').click();self.assertEqual(wrap.evaluate('e=>[e.scrollTop,e.scrollLeft]'),[300,100])
        # Un clic de selección no reconstruye la página ni manda acción.
        self.pg.evaluate('()=>{const r=mount.querySelector(".sud tbody tr[data-id]");r.dispatchEvent(new MouseEvent("click",{bubbles:true}))}')
        self.assertEqual(wrap.evaluate('e=>[e.scrollTop,e.scrollLeft]'),[300,100]);self.assertEqual(self.pg.evaluate('pedidos.filter(p=>p.k==="accion").length'),0)


if __name__=='__main__':unittest.main(verbosity=2)
