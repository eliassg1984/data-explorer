"""Balance de Stock local, con fuentes, filtros y contribuciones (#738)."""
import datetime as dt
import json
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from graficos import inventario_movimientos as im
from graficos import inventario_movimientos_datos as datos

ROOT=Path(__file__).parent
COLS=dict(col_cod_area='AC',col_cod='C',col_area='A',col_prod='P',col_fam='F',col_punit='PU')
DESDE=dt.date(2026,1,1);HASTA=dt.date(2026,1,31)


def muestra(n=0):
    d=pd.DataFrame([['001','0000001','COCINA','Café de prueba','Alimentos',10],['002','0000001','BARRA','Café de prueba','Alimentos',10],['001','0000002','COCINA','Mismo nombre','Bebidas',None],['001','0000003','COCINA','Mismo nombre','Bebidas',5],['001','0000001','COCINA','Otro registro','Otra',99],['003','0000004','SIN MOVIMIENTO','Stock sin movimiento','Alimentos',3]],columns=['AC','C','A','P','F','PU'])
    mov=[]
    def add(a,c,t,vi=0,vo=0,sc=0,an=0):mov.append(dict(area=a,cod=c,tipo=t,nombre='Tipo '+t,val_in=vi,val_out=vo,movs=1,anul=an,cant_sin_costo=sc,movs_sin_costo=1 if sc else 0))
    add('001','0000001','01',vi=100.123456789);add('001','0000001','95',vo=40);add('001','0000001','97',vo=15);add('002','0000001','97',vi=15);add('001','0000001','93',vo=4);add('001','0000001','91',vo=3,an=1);add('001','0000001','999',vi=.2)
    add('001','0000002','95',sc=2);add('001','0000003','95',sc=3);add('009','9999999','01',vi=9999)
    fi=pd.DataFrame([['001','0000001',10,10],['002','0000001',-1,10],['001','0000002',0,0],['001','0000003',0,5],['003','0000004',8,3]],columns=['area','cod','stock','precio']).astype({'stock':float,'precio':float});ff=fi.copy();ff.loc[0,['stock','precio']]=[13,12];ff.loc[1,'stock']=.5;ff.loc[2,'stock']=-2;ff.loc[3,'stock']=-3
    for j in range(n):
        c=f'{j+1000:07d}';d.loc[len(d)]=['001',c,'COCINA',f'Extra {j:04d}','Alimentos',1];add('001',c,'01',vi=2+j/1000);fi.loc[len(fi)]=['001',c,1,1];ff.loc[len(ff)]=['001',c,3,1]
    return d,pd.DataFrame(mov),fi,ff


def payload(n=0):return datos.armar(*muestra(n),**COLS,desde=DESDE,hasta=HASTA)|dict(inicial=dict(areas=[],familias=[],q='',vista='tipo'),comun='inicio')


class Contrato(unittest.TestCase):
    def test_normalizacion_precision_codigo_y_sello(self):
        args=muestra();P=payload();json.dumps(P,allow_nan=False);idx=P['mov']['columnas'].index('val_in');self.assertEqual(P['mov']['filas'][0][idx],100.123456789);self.assertEqual(P['base']['filas'][0][1],'0000001')
        self.assertEqual(len(P['base']['filas']),len(args[0]));args[0].loc[0,'PU']=11;self.assertNotEqual(P['sello'],datos.armar(*args,**COLS,desde=DESDE,hasta=HASTA)['sello'])

    def test_foto_vacia_es_cero_conocido(self):
        d,m,fi,ff=muestra();P=datos.armar(d,m,pd.DataFrame(),ff,**COLS,desde=DESDE,hasta=HASTA);self.assertEqual(P['ini']['filas'],[]);self.assertEqual(P['ini']['columnas'],['area','cod','stock','precio'])

    def test_firma_cache_y_horas_del_kardex(self):
        from graficos import inventario_movimientos_pieza as pieza
        d,m,fi,ff=muestra();fake=SimpleNamespace(session_state={},info=Mock(),markdown=Mock(),container=lambda **kw:nullcontext(),columns=lambda *a,**kw:(nullcontext(),nullcontext()),date_input=Mock(return_value=(DESDE,HASTA)))
        with patch.object(pieza,'st',fake),patch.object(pieza.data,'rango_fechas',return_value=(DESDE,HASTA)),patch.object(pieza.data,'movimientos_kardex',return_value=m) as fuente,patch.object(pieza.data,'stock_al',side_effect=[fi,ff,fi,ff]) as foto,patch.object(pieza,'_PIEZA') as comp,patch.object(datos,'armar',wraps=datos.armar) as build:
            im.seccion_movimientos(d,**COLS);im.seccion_movimientos(d,**COLS);self.assertEqual(build.call_count,1);self.assertEqual(fuente.call_args.args,(DESDE,HASTA));self.assertEqual(foto.call_args_list[0].args,(im.kardex.momento(DESDE-dt.timedelta(days=1),23),));self.assertEqual(foto.call_args_list[1].args,(im.kardex.momento(HASTA,23),));self.assertFalse(any(k.startswith('on_') for k in comp.call_args.kwargs))
        import inspect
        self.assertEqual(len(inspect.signature(im.seccion_movimientos).parameters),7)

    def test_sin_codigos_y_sin_fuente_no_inventa_saldos(self):
        from graficos import inventario_movimientos_pieza as pieza
        fake=SimpleNamespace(info=Mock())
        with patch.object(pieza,'st',fake):pieza.renderizar(pd.DataFrame(),**(COLS|dict(col_cod=None)));self.assertIn('códigos',fake.info.call_args.args[0])
        with patch.object(pieza,'st',fake),patch.object(pieza.data,'rango_fechas',return_value=None):pieza.renderizar(muestra()[0],**COLS);self.assertIn('Falta el kardex',fake.info.call_args.args[0])


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
        from graficos import inventario_movimientos_pieza as pieza
        cls.pg=cls.br.new_page(viewport={'width':1323,'height':619},accept_downloads=True);cls.pg.set_default_timeout(7000);cls.pg.route('https://stockmov.example.test/**',lambda r:r.fulfill(body='<div id="host"></div>',content_type='text/html'));cls.pg.goto('https://stockmov.example.test/')
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}',pieza._CSS)
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/inventario_movimientos.js').read_text(encoding='utf-8').replace('export default function(component)','window.montarStock=function(component)'),type='module');cls.pg.wait_for_function('typeof montarStock==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None):
        self.pg.set_viewport_size({'width':1323,'height':619});self.pg.evaluate('([P,ui])=>{sessionStorage.setItem("stock_mov_738",JSON.stringify(ui||{}));montarStock({data:P,parentElement:mount,setTriggerValue:()=>{throw Error("Control local pide Python")}})}',[P or payload(),ui]);return self.pg.locator('.imv')

    def test_m_contra_helper_filtros_y_palabras(self):
        self.mount();args=muestra();states=[dict(areas=a,familias=f,q=q) for a in [[],['COCINA'],['BARRA'],['COCINA','BARRA']] for f in [[],['Alimentos'],['Bebidas'],['Otra']] for q in ['', 'cafe prueba','0000001','[']]
        got=self.pg.evaluate('ss=>ss.map(s=>__stockMovDatos.calcular(__stockMov.B,s))',states)
        for s,j in zip(states,got):
            M=im.armar_movimientos(*args,**COLS,areas=s['areas'],familias=s['familias'],texto=s['q'])
            for k in ['ini','fin','valorizacion','movs']:self.assertAlmostEqual(j[k],getattr(M,k),places=7)
            for k,v in M.netos.items():self.assertAlmostEqual(j['netos'][k],v,places=7)
            for campo,df,keys in [('tipos',M.por_tipo,['grupo','tipo']),('areas',M.por_area,['area']),('sin_costo',M.sin_costo,['producto','area'])]:
                js={tuple(r[k] for k in keys):r for r in j[campo]};self.assertEqual(set(js),{tuple(r[k] for k in keys) for r in df.to_dict('records')})
                for r in df.to_dict('records'):
                    row=js[tuple(r[k] for k in keys)]
                    for k,v in r.items():
                        if pd.isna(v):self.assertIsNone(row[k])
                        elif isinstance(v,(float,int)):self.assertAlmostEqual(row[k],v,places=7)
                        else:self.assertEqual(row[k],v)

    def test_dedupe_despues_del_filtro_y_primer_precio_no_nulo(self):
        self.mount();j=self.pg.evaluate('__stockMovDatos.calcular(__stockMov.B,{areas:[],familias:["Otra"],q:""})');self.assertEqual(j['base'][0]['precio_hoy'],99)
        j=self.pg.evaluate('__stockMov.M.sin_costo[0]');self.assertEqual(j['precio_hoy'],5);self.assertEqual(j['cant'],5);self.assertEqual(j['valor_hoy'],25)

    def test_cascada_contra_plotly_y_entre_areas_cero(self):
        self.mount();M=im.armar_movimientos(*muestra(),**COLS);fig=im.fig_cascada(M,'ini','fin');rs=self.pg.evaluate('__stockMovDatos.cascada(__stockMov.B,__stockMov.M)');self.assertEqual([r['v'] for r in rs[:-1]],list(fig.data[0].y)[:-1]);self.assertEqual(rs[-1]['v'],M.fin);self.assertTrue(any(r['g']=='entre' and r['v']==0 for r in rs));self.assertFalse(any(r['g']=='otros' for r in rs));self.assertAlmostEqual(rs[-2]['b'],M.fin-M.netos['otros'])

    def test_productos_suman_puntas_movimientos_y_residual(self):
        self.mount();rs=self.pg.evaluate('__stockMovDatos.productos(__stockMov.B,__stockMov.M)');M=im.armar_movimientos(*muestra(),**COLS)
        for k,v in [('ini',M.ini),('fin',M.fin),('neto',sum(M.netos.values())),('valorizacion',M.valorizacion)]:self.assertAlmostEqual(sum(r[k] for r in rs),v)
        for r in rs:self.assertAlmostEqual(r['ini']+r['neto']+r['valorizacion'],r['fin'])

    def test_busqueda_checkbox_y_vista_son_locales(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('cafe prueba');self.assertEqual(q.input_value(),'cafe prueba');self.assertEqual(len(self.pg.evaluate('__stockMov.M.base')),2);q.fill('');root.locator('[data-a=vista][data-v=area]').click();self.assertTrue(root.locator('[data-k=area]').is_visible());f=root.locator('details[data-filter=areas]');f.locator('summary').click();f.locator('input').first.check();self.assertEqual(len(self.pg.evaluate('__stockMov.s.areas')),1);f.locator('input').first.press('Escape');self.assertFalse(f.evaluate('e=>e.open'))

    def test_drill_del_grafico_no_cambia_balance(self):
        root=self.mount();before=self.pg.evaluate('[__stockMov.M.ini,__stockMov.M.fin,__stockMov.M.valorizacion]');root.locator('svg [data-a=paso][data-v=compras]').click();self.assertEqual(self.pg.evaluate('__stockMov.s.grupo'),'compras');self.assertEqual(self.pg.evaluate('[__stockMov.M.ini,__stockMov.M.fin,__stockMov.M.valorizacion]'),before)
        root.locator('svg [data-a=paso][data-v=valorizacion]').click();self.assertTrue(root.locator('[data-k=productos]').evaluate('e=>e.open'));self.assertEqual(self.pg.evaluate('__stockMov.s.porden'),'valorizacion')

    def test_producto_no_repinta_lista_y_tandas(self):
        root=self.mount(payload(330));root.locator('[data-k=productos]>summary').click();self.assertEqual(root.locator('tr[data-a=producto]').count(),150);root.locator('[data-a=mas]').click();self.assertEqual(root.locator('tr[data-a=producto]').count(),300);first=root.locator('tr[data-a=producto]').first.element_handle();root.locator('tr[data-a=producto]').nth(4).click();self.assertTrue(first.evaluate('e=>e.isConnected'));self.assertIn('Inicial',root.locator('[data-k=ficha]').inner_text())

    def test_eco_recuerda_filtros_aunque_cambie_fecha(self):
        root=self.mount();root.locator('[data-k=q]').fill('café');ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("stock_mov_738"))');P=payload();P['hasta']='2026-02-01';self.mount(P,ui);self.assertEqual(self.pg.evaluate('__stockMov.s.q'),'café');P['comun']='cambio externo';self.mount(P,ui);self.assertEqual(self.pg.evaluate('__stockMov.s.q'),'')

    def test_excel_completo_sin_filtros_locales_y_seis_decimales(self):
        root=self.mount();root.locator('[data-k=q]').fill('café')
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        with zipfile.ZipFile(dl.value.path()) as z:
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),10);self.assertIn('0000002',z.read('xl/worksheets/sheet5.xml').decode());self.assertIn('<v>100.123457</v>',z.read('xl/worksheets/sheet6.xml').decode());self.assertNotIn('9999999',z.read('xl/worksheets/sheet6.xml').decode())

    def test_movil_popovers_y_eventos_no_duplicados(self):
        root=self.mount();self.mount();self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),390);self.pg.wait_for_function('document.querySelector("#host").shadowRoot.querySelector(".imv-chart svg").viewBox.baseVal.width<=400');root.locator('details[data-filter=familias] summary').click();self.assertLessEqual(root.locator('details[data-filter=familias] .imv-pop').evaluate('e=>e.getBoundingClientRect().right'),390);root.locator('[data-k=productos]>summary').click();self.assertTrue(self.pg.evaluate('__stockMov.s.productos'))


if __name__=='__main__':unittest.main(verbosity=2)
