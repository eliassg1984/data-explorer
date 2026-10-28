"""Balance de Stock local, con fuentes, filtros y contribuciones (#738), y
los dos relojes —de conteo a conteo y por calendario— desde la #747."""
import datetime as dt
import json
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import duckdb
import pandas as pd
import kardex
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
    fi=pd.DataFrame([['001','0000001',10,10],['002','0000001',-1,10],['001','0000002',0,0],['001','0000003',0,5],['003','0000004',8,3],['009','9999999',4,4]],columns=['area','cod','stock','precio']).astype({'stock':float,'precio':float});ff=fi.copy();ff.loc[0,['stock','precio']]=[13,12];ff.loc[1,'stock']=.5;ff.loc[2,'stock']=-2;ff.loc[3,'stock']=-3
    for j in range(n):
        c=f'{j+1000:07d}';d.loc[len(d)]=['001',c,'COCINA',f'Extra {j:04d}','Alimentos',1];add('001',c,'01',vi=2+j/1000);fi.loc[len(fi)]=['001',c,1,1];ff.loc[len(ff)]=['001',c,3,1]
    return d,pd.DataFrame(mov),fi,ff


PERIODO=dict(nombre='Setiembre 2026',en_curso=False,t0='2 set 10:00',t1='1 oct 18:00',desde='1 set',hasta='30 set',dias=30,excepciones=[['BARRA','hasta el 6 oct 12:00']],cierre='1 y 6 oct 2026',cierre_ant='2 set 2026')
CONTEOS=[dict(nombre='Cierre de agosto',etiqueta='2 set',tipo='cierre',dentro=True),dict(nombre='Cierre de setiembre',etiqueta='1 y 6 oct',tipo='cierre',dentro=False)]


def payload(n=0,**kw):
    return datos.armar(*muestra(n),**COLS,desde=DESDE,hasta=HASTA,**kw)|dict(inicial=dict(areas=[],familias=[],q=''),comun='inicio',comparar=False)


class Contrato(unittest.TestCase):
    def test_normalizacion_precision_codigo_y_sello(self):
        args=muestra();P=payload();json.dumps(P,allow_nan=False);idx=P['mov']['columnas'].index('val_in');self.assertEqual(P['mov']['filas'][0][idx],100.123456789);self.assertEqual(P['base']['filas'][0][1],'0000001')
        self.assertEqual(len(P['base']['filas']),len(args[0]));args[0].loc[0,'PU']=11;self.assertNotEqual(P['sello'],datos.armar(*args,**COLS,desde=DESDE,hasta=HASTA)['sello'])
        # Lo que no está en la base no viaja: ni el movimiento del 009 ni su foto,
        # ni las fotos en cero, que no suman nada.
        self.assertFalse(any('9999999' in f for f in P['mov']['filas']));self.assertFalse(any('9999999' in f for f in P['ini']['filas']))
        self.assertEqual(len(P['ini']['filas']),3);self.assertEqual(P['reloj'],'cal');self.assertIsNone(P['otro'])

    def test_foto_vacia_es_cero_conocido(self):
        d,m,fi,ff=muestra();P=datos.armar(d,m,pd.DataFrame(),ff,**COLS,desde=DESDE,hasta=HASTA);self.assertEqual(P['ini']['filas'],[]);self.assertEqual(P['ini']['columnas'],['area','cod','stock','precio'])

    def test_resumen_del_otro_reloj_suma_lo_mismo_que_la_cuenta(self):
        args=muestra();R=datos.resumen_por_area(*args,**COLS);M=im.armar_movimientos(*args,**COLS)
        df=pd.DataFrame(R['filas'],columns=R['columnas']);self.assertEqual(R['columnas'][:4],['area','familia','ini','fin'])
        self.assertAlmostEqual(df.ini.sum(),M.ini);self.assertAlmostEqual(df.fin.sum(),M.fin)
        for g,v in M.netos.items():self.assertAlmostEqual(df[g].sum(),v)
        por_area=df.groupby('area')[['ini','fin','compras','entre']].sum()
        for r in M.por_area.to_dict('records'):
            self.assertAlmostEqual(por_area.loc[r['area'],'fin'],r['fin']);self.assertAlmostEqual(por_area.loc[r['area'],'entre'],r['entre'])
        vacio=datos.resumen_por_area(args[0],args[1].iloc[0:0],pd.DataFrame(),pd.DataFrame(),**COLS);self.assertEqual(vacio['filas'],[])

    def test_consulta_por_ventana_de_cada_area(self):
        k=pd.DataFrame({'CODIGO AREA':['001','001','002','002','001'],'CODIGO PRODUCTO':['A','A','A','A','A'],'COD TIPO':['95','93','95','95','SI'],
            'TIPO MOVIMIENTO':['Venta','Ajuste','Venta','Venta','Saldo'],'CANT INGRESO':[0,0,0,0,9],'CANT SALIDA':[1,2,3,0,0],'VALOR INGRESO':[0,0,0,0,90],
            'VALOR SALIDA':[10,20,30,0,0],'MOVIMIENTOS':[1,1,1,1,1],'ANULACIONES':[0,0,0,0,0],
            'FECHA HORA':pd.to_datetime(['2026-09-02 09:00','2026-09-02 09:00','2026-09-03 12:00','2026-10-02 08:00','2026-09-05 10:00'])})
        con=duckdb.connect();con.register('kx',k)
        # 001 desde las 10 (su conteo fue a las 9) y 002 hasta el 6 oct (lo contaron otro día).
        v=[(1,'2026-09-02T10:00:00',dt.datetime(2026,10,1,18)),(2,dt.datetime(2026,9,2,10),'2026-10-06T12:00:00')]
        r=con.execute(kardex.sql_movimientos_tipo_ventanas('kx',v)).df()
        self.assertEqual(sorted(r.area),['002']);self.assertEqual(float(r.val_out.sum()),30.0);self.assertEqual(float(r.cant_sin_costo.sum()),0.0)
        self.assertEqual(list(r.columns),list(con.execute(kardex.sql_movimientos('kx',DESDE,HASTA)).df().columns))
        self.assertTrue(con.execute(kardex.sql_movimientos_tipo_ventanas('kx',[])).df().empty)

    def test_periodo_conteos_y_mes_entero(self):
        from graficos import inventario_movimientos_pieza as pieza
        t=pd.Timestamp;p=dict(nombre='Setiembre 2026',en_curso=False,t0=t('2026-09-02 10:00'),t1=t('2026-10-01 18:00'),dias=29.33,cierre='1 y 6 oct 2026',cierre_ant='2 set 2026',
            ventanas={1:(t('2026-09-02 11:00'),t('2026-10-01 18:00')),7:(t('2026-09-02 10:00'),t('2026-10-06 12:00')),9:(t('2026-09-02 10:00'),t('2026-10-01 18:00'))})
        js=pieza.periodo_js(p,{1:'COCINA',7:'VENTA INTERNA'})
        self.assertEqual(js['excepciones'],[['VENTA INTERNA','hasta el 6 oct 12:00']]);self.assertEqual(js['t0'],'2 set 10:00')
        ses=[dict(nombre='Cierre de agosto',etiqueta='2 set',tipo='cierre',mes=(2026,8),dias=(dt.date(2026,9,2),),ini=dt.date(2026,9,2)),
             dict(nombre='Parcial · 15-17 set',etiqueta='15-17 set',tipo='parcial',mes=(2026,9),dias=(dt.date(2026,9,15),),ini=dt.date(2026,9,15)),
             dict(nombre='Cierre de setiembre',etiqueta='1 y 6 oct',tipo='cierre',mes=(2026,9),dias=(dt.date(2026,10,1),dt.date(2026,10,6)),ini=dt.date(2026,10,1))]
        c=pieza.conteos_del_rango(ses,dt.date(2026,9,1),dt.date(2026,9,30))
        self.assertEqual([(x['nombre'],x['dentro']) for x in c],[('Cierre de agosto',True),('Parcial · 15-17 set',True),('Cierre de setiembre',False)])
        self.assertEqual(pieza.conteos_del_rango(ses,dt.date(2026,9,10),dt.date(2026,9,12)),[dict(nombre='Cierre de setiembre',etiqueta='1 y 6 oct',tipo='cierre',dentro=False)])
        self.assertEqual(pieza._mes_entero(dt.date(2026,9,1),dt.date(2026,9,30),dt.date(2026,10,26)),(2026,9))
        self.assertEqual(pieza._mes_entero(dt.date(2026,10,1),dt.date(2026,10,26),dt.date(2026,10,26)),(2026,10))
        self.assertIsNone(pieza._mes_entero(dt.date(2026,9,2),dt.date(2026,9,30),dt.date(2026,10,26)))
        ss={};per=[dict(clave='a',en_curso=False),dict(clave='b',en_curso=False),dict(clave='c',en_curso=True)]
        with patch.object(pieza,'st',SimpleNamespace(session_state=ss)):
            self.assertEqual(pieza.periodo_elegido(per)['clave'],'b');pieza._mover(['a','b','c'],1);self.assertEqual(ss[pieza.K_PERIODO],'c');pieza._mover(['a','b','c'],5);self.assertEqual(ss[pieza.K_PERIODO],'c')

    def _fake(self,ss):
        return SimpleNamespace(session_state=ss,info=Mock(),markdown=Mock(),container=lambda **kw:nullcontext(),button=Mock(),selectbox=Mock())

    def test_reloj_de_conteo_y_calendario_consultan_y_cachean(self):
        from graficos import inventario_movimientos_pieza as pieza
        d,m,fi,ff=muestra();t=pd.Timestamp
        per=[dict(k=0,clave='cierre_2026-09',mes=(2026,9),nombre='Setiembre 2026',corto='set 26',desde=dt.date(2026,9,2),hasta=dt.date(2026,10,1),
                  t0=t('2026-09-02 10:00'),t1=t('2026-10-01 18:00'),dias=29.3,ventanas={1:(t('2026-09-02 10:00'),t('2026-10-01 18:00'))},cierre='1 oct 2026',cierre_ant='2 set 2026',en_curso=False)]
        ss={};fake=self._fake(ss)
        comunes=dict(rango_fechas=Mock(return_value=(DESDE,dt.date(2026,10,26))),periodos_conteo=Mock(return_value=dict(periodos=per,sesiones=[])))
        fuentes=dict(movimientos_conteo=Mock(return_value=(m,fi,ff)),movimientos_kardex=Mock(return_value=m),stock_al=Mock(side_effect=lambda *_:fi))
        with patch.object(pieza,'st',fake),patch.multiple(pieza.data,**comunes,**fuentes),\
             patch.object(pieza,'eleccion_compartida',return_value=pieza.CONTEO),patch.object(pieza,'_PIEZA') as comp,patch.object(datos,'armar',wraps=datos.armar) as build:
            im.seccion_movimientos(d,**COLS);im.seccion_movimientos(d,**COLS)
            self.assertEqual(build.call_count,1);self.assertEqual(fuentes['movimientos_conteo'].call_args.args,(per[0],));fuentes['movimientos_kardex'].assert_not_called()
            P=comp.call_args.kwargs['data'];self.assertEqual(P['reloj'],'op');self.assertEqual(P['periodo']['cierre'],'1 oct 2026');self.assertIsNone(P['otro'])
            self.assertEqual([k for k in comp.call_args.kwargs if k.startswith('on_')],['on_comparar_change'])
            # «Traer» el otro reloj: el mismo mes por calendario, del 1 al 30.
            ss[pieza.K_PIEZA]={'comparar':P['sello']};comp.call_args.kwargs['on_comparar_change']();self.assertTrue(ss[pieza.K_COMPARAR])
            im.seccion_movimientos(d,**COLS);self.assertEqual(fuentes['movimientos_kardex'].call_args.args,(dt.date(2026,9,1),dt.date(2026,9,30)))
            P=comp.call_args.kwargs['data'];self.assertEqual(P['otro']['reloj'],'cal');self.assertTrue(P['comparar'])
        ss={};fake=self._fake(ss)
        fuentes=dict(movimientos_conteo=Mock(return_value=(m,fi,ff)),movimientos_kardex=Mock(return_value=m),stock_al=Mock(side_effect=[fi,ff]))
        with patch.object(pieza,'st',fake),patch.multiple(pieza.data,**comunes,**fuentes),\
             patch.object(pieza,'eleccion_compartida',return_value=pieza.CALENDARIO),patch.object(pieza,'selector_fecha_tarjeta') as fecha,patch.object(pieza,'rango_tarjeta',return_value=(DESDE,HASTA)),patch.object(pieza,'_PIEZA') as comp:
            im.seccion_movimientos(d,**COLS)
            self.assertEqual(fuentes['movimientos_kardex'].call_args.args,(DESDE,HASTA));fuentes['movimientos_conteo'].assert_not_called()
            self.assertEqual(fuentes['stock_al'].call_args_list[0].args,(kardex.momento(DESDE-dt.timedelta(days=1),23),));self.assertEqual(fuentes['stock_al'].call_args_list[1].args,(kardex.momento(HASTA,23),))
            self.assertEqual(fecha.call_args.kwargs['categoria'],pieza.CATEGORIA);P=comp.call_args.kwargs['data'];self.assertEqual(P['reloj'],'cal');self.assertTrue(P['comparable'] is False)
        import inspect
        self.assertEqual(len(inspect.signature(im.seccion_movimientos).parameters),7)

    def test_sin_periodos_de_conteo_queda_el_calendario(self):
        from graficos import inventario_movimientos_pieza as pieza
        d,m,fi,ff=muestra();ss={};fake=self._fake(ss)
        with patch.object(pieza,'st',fake),patch.multiple(pieza.data,rango_fechas=Mock(return_value=(DESDE,HASTA)),periodos_conteo=Mock(return_value=None),movimientos_kardex=Mock(return_value=m),stock_al=Mock(side_effect=[fi,ff])),\
             patch.object(pieza,'eleccion_compartida') as reloj,patch.object(pieza,'selector_fecha_tarjeta'),patch.object(pieza,'rango_tarjeta',return_value=(DESDE,HASTA)),patch.object(pieza,'_PIEZA') as comp:
            im.seccion_movimientos(d,**COLS);reloj.assert_not_called();self.assertEqual(comp.call_args.kwargs['data']['reloj'],'cal')

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
        cls.pg.add_script_tag(content=(ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8')+(ROOT/'graficos/inventario_movimientos.js').read_text(encoding='utf-8').replace('export default function (component)','window.montarStock=function(component)'),type='module');cls.pg.wait_for_function('typeof montarStock==="function"')

    @classmethod
    def tearDownClass(cls):cls.br.close();cls.pw.stop()

    def mount(self,P=None,ui=None,envios=False):
        self.pg.set_viewport_size({'width':1323,'height':619})
        self.pg.evaluate('([P,ui,envios])=>{sessionStorage.setItem("stock_mov_747",JSON.stringify(ui||{}));window.__envios=[];montarStock({data:P,parentElement:mount,setTriggerValue:envios?(k,v)=>__envios.push([k,v]):()=>{throw Error("Control local pide Python")}})}',[P or payload(),ui,envios]);return self.pg.locator('.imv')

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
        for k,v in [('ini',M.ini),('fin',M.fin),('neto',sum(M.netos.values())),('valorizacion',M.valorizacion),('ajustes',M.netos['ajustes'])]:self.assertAlmostEqual(sum(r[k] for r in rs),v)
        for r in rs:self.assertAlmostEqual(r['ini']+r['neto']+r['valorizacion'],r['fin']);self.assertAlmostEqual(r['mov']+r['ajustes'],r['neto'])

    def test_busqueda_checkbox_y_foco_son_locales(self):
        root=self.mount();q=root.locator('[data-k=q]');q.click();q.press_sequentially('cafe prueba');self.assertEqual(q.input_value(),'cafe prueba');self.assertEqual(len(self.pg.evaluate('__stockMov.M.base')),2);q.fill('')
        root.locator('[data-a=foco][data-v=COCINA]').click();self.assertEqual(self.pg.evaluate('__stockMov.s.foco'),'COCINA')
        M=im.armar_movimientos(*muestra(),**COLS,areas=['COCINA']);j=self.pg.evaluate('[__stockMov.M.ini,__stockMov.M.fin,__stockMov.M.netos.entre]');self.assertAlmostEqual(j[0],M.ini);self.assertAlmostEqual(j[1],M.fin);self.assertAlmostEqual(j[2],M.netos['entre'])
        self.assertIn('Cocina',root.locator('[data-k=g-tit]').inner_text());self.assertEqual(self.pg.evaluate('__stockMov.Mall.areas.length'),3)
        root.locator('[data-k=chip] [data-a=foco]').click();self.assertIsNone(self.pg.evaluate('__stockMov.s.foco'))
        f=root.locator('details[data-filter=areas]');f.locator('summary').click();f.locator('input').first.check();self.assertEqual(len(self.pg.evaluate('__stockMov.s.areas')),1);f.locator('input').first.press('Escape');self.assertFalse(f.evaluate('e=>e.open'))

    def test_drill_del_grafico_y_los_indicadores_no_cambian_balance(self):
        root=self.mount();before=self.pg.evaluate('[__stockMov.M.ini,__stockMov.M.fin,__stockMov.M.valorizacion]')
        root.locator('svg [data-a=paso][data-v=compras]').click();self.assertEqual(self.pg.evaluate('[__stockMov.s.grupo,__stockMov.s.tab]'),['compras','tipos']);self.assertEqual(self.pg.evaluate('[__stockMov.M.ini,__stockMov.M.fin,__stockMov.M.valorizacion]'),before)
        self.assertIn('Compras',root.locator('[data-k=tab]').inner_text())
        root.locator('svg [data-a=paso][data-v=valorizacion]').click();self.assertEqual(self.pg.evaluate('[__stockMov.s.tab,__stockMov.s.porden]'),['productos','valorizacion'])
        root.locator('.imv-kpi[data-v=ajustes]').click();self.assertEqual(self.pg.evaluate('__stockMov.s.porden'),'ajustes');self.assertEqual(root.locator('[data-k=porden]').input_value(),'ajustes')

    def test_producto_no_repinta_lista_y_tandas(self):
        root=self.mount(payload(330));self.assertEqual(root.locator('tr[data-a=producto]').count(),150);root.locator('[data-a=mas]').click();self.assertEqual(root.locator('tr[data-a=producto]').count(),300)
        first=root.locator('tr[data-a=producto]').first.element_handle();root.locator('tr[data-a=producto]').nth(4).click();self.assertTrue(first.evaluate('e=>e.isConnected'));self.assertIn('Al empezar',root.locator('[data-k=ficha]').inner_text())

    def test_eco_recuerda_filtros_y_pestana_aunque_cambie_fecha(self):
        root=self.mount();root.locator('[data-k=q]').fill('café');root.locator('[data-a=tab][data-v=tipos]').click();ui=self.pg.evaluate('JSON.parse(sessionStorage.getItem("stock_mov_747"))');P=payload();P['hasta']='2026-02-01'
        self.mount(P,ui);self.assertEqual(self.pg.evaluate('[__stockMov.s.q,__stockMov.s.tab]'),['café','tipos']);P['comun']='cambio externo';self.mount(P,ui);self.assertEqual(self.pg.evaluate('__stockMov.s.q'),'')

    def test_excel_completo_sin_filtros_locales_y_seis_decimales(self):
        root=self.mount();root.locator('[data-k=q]').fill('café')
        with self.pg.expect_download() as dl:root.locator('[data-a=excel]').click()
        with zipfile.ZipFile(dl.value.path()) as z:
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/')]),10);self.assertIn('0000002',z.read('xl/worksheets/sheet5.xml').decode());self.assertIn('<v>100.123457</v>',z.read('xl/worksheets/sheet6.xml').decode());self.assertNotIn('9999999',z.read('xl/worksheets/sheet6.xml').decode())
            todo=''.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'));self.assertIn('Fechas del calendario',todo)

    def test_ventana_de_conteo_y_aviso_del_calendario(self):
        root=self.mount(payload(reloj='op',periodo=PERIODO));t=root.locator('[data-k=ventana]').inner_text()
        self.assertIn('Del conteo del 2 set 2026 al del 1 y 6 oct 2026',t);self.assertIn('Abrió el conteo otro día: Barra, hasta el 6 oct 12:00',t);self.assertIn('del 1 set al 30 set · 30 días · el mes que se contó',t);self.assertTrue(root.locator('[data-k=aviso]').is_hidden())
        self.assertIn('lo contado',root.locator('.imv-kpi[data-v=ini]').inner_text())
        root=self.mount(payload(reloj='cal',conteos=CONTEOS));a=root.locator('[data-k=aviso]');self.assertTrue(a.is_visible())
        self.assertIn('Cierre de agosto',a.inner_text());self.assertIn('queda afuera',a.inner_text());self.assertIn('antes de contar',a.inner_text())

    def test_los_dos_relojes(self):
        args=muestra();otro=dict(reloj='cal',nombre='del 1 al 30 de setiembre',**datos.resumen_por_area(args[0],args[1].assign(val_out=args[1].val_out*2),*args[2:],**COLS))
        root=self.mount(payload(reloj='op',periodo=PERIODO,otro=otro));root.locator('[data-a=tab][data-v=relojes]').click()
        filas=root.locator('table.imv-relojes tbody tr');self.assertGreater(filas.count(),5)
        M=im.armar_movimientos(*args,**COLS);ventas=filas.filter(has_text='Ventas').inner_text().split('\t')
        self.assertEqual(ventas[2].strip(),f"−{abs(M.netos['ventas']):,.0f}");self.assertEqual(ventas[1].strip(),f"−{abs(2*M.netos['ventas']):,.0f}")
        j=self.pg.evaluate('__stockMovDatos.resumenOtro(__stockMov.P,["COCINA"],[])');Mc=im.armar_movimientos(args[0],args[1].assign(val_out=args[1].val_out*2),*args[2:],**COLS,areas=['COCINA'])
        self.assertAlmostEqual(j['ini'],Mc.ini);self.assertAlmostEqual(j['netos']['ventas'],Mc.netos['ventas']);self.assertAlmostEqual(j['valorizacion'],Mc.valorizacion)
        # Sin el otro reloj, un botón lo pide; y el calendario sin un mes entero no compara.
        root=self.mount(payload(reloj='op',periodo=PERIODO),envios=True);root.locator('[data-a=tab][data-v=relojes]').click();root.locator('[data-a=comparar]').click()
        self.assertEqual(self.pg.evaluate('__envios'),[['comparar',self.pg.evaluate('__stockMov.P.sello')]]);self.assertIn('Trayendo',root.locator('[data-k=tab]').inner_text())
        root=self.mount(payload(reloj='cal'));root.locator('[data-a=tab][data-v=relojes]').click();self.assertIn('mes entero',root.locator('[data-k=tab]').inner_text())

    def test_movil_popovers_y_eventos_no_duplicados(self):
        root=self.mount();self.mount();self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(root.evaluate('e=>e.getBoundingClientRect().right'),390)
        self.pg.wait_for_function('document.querySelector("#host").shadowRoot.querySelector(".imv-chart svg").viewBox.baseVal.width<=400')
        root.locator('details[data-filter=familias] summary').click();self.assertLessEqual(root.locator('details[data-filter=familias] .imv-pop').evaluate('e=>e.getBoundingClientRect().right'),390)
        root.locator('details[data-filter=familias] summary').click();root.locator('[data-a=tab][data-v=tipos]').click();self.pg.wait_for_function('__stockMov.s.tab==="tipos"');self.assertEqual(self.pg.evaluate('__stockMov.s.tab'),'tipos')


if __name__=='__main__':unittest.main(verbosity=2)
