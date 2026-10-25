"""Porcionamientos nativos: cabecera única, costos identificados y cortes (#728)."""
import json
import tempfile
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from graficos import movimientos_periodo as mp
from graficos import porcionamientos_datos as datos
import test_movimientos_periodo_pieza as comun

ROOT=Path(__file__).parent
COLS=dict(fecha='F',doc='D',area='A',tipo='T',prod='P',cod='C',unid='U',cant='Q',merma='M',
          fin='PF',cod_fin='CF',cant_fin='QF',unid_fin='UF',pprom='PP',peso='PS')
RANGO=(pd.Timestamp('2025-01-01'),pd.Timestamp('2025-04-01'))


def muestra():
    filas=[]
    headers=[('P-01','2025-01-02 10:00','Origen A','0001','KILOS',10.123456789,2.123456789,'Ana'),
             ('P-02','2025-01-25 10:00','Origen A','0001','KILOS',20,1,'Ana'),
             ('P-03','2025-02-03 10:00','Porciones','0002','UNIDAD',12,.5,'Luis'),
             ('P-04','2025-02-04 10:00','Cantidad cero','0001','KILOS',0,1,'Luis'),
             ('P-05','2025-02-05 10:00','Sin cortes','0003','KILOS',2,.3,'Luis'),
             ('P-06','2025-03-02 10:00','Merma excesiva','0001','KILOS',2,3,'Ana'),
             ('P-07','2025-03-03 10:00','Sin datos','0002','UNIDAD',None,None,'Luis'),
             ('P-08','2025-03-04 10:00','','0001','KILOS',1,.1,'Ana'),
             ('P-09','2025-03-05 10:00','Merma negativa','0001','KILOS',2,-.1,'Ana')]
    for i,(doc,f,p,c,u,q,m,t) in enumerate(headers):
        cortes=[('Corte útil A',4.2,10,6),('Corte útil B',3.8,20,2)] if i==0 else [('Corte simple',1,5,1)]
        if doc=='P-05':cortes=[('',None,None,None)]
        for j,(fin,qf,pp,peso) in enumerate(cortes):filas.append(dict(F=pd.Timestamp(f),D=doc,A='Cocina' if t=='Ana' else 'Barra',T=t,P=p,C=c,U=u,Q=q,M=m,PF=fin,CF=f'F{j:04}',QF=qf,UF='UNIDAD' if j else u,PP=pp,PS=peso))
    return pd.DataFrame(filas)


def precios():return pd.Series({'0001':8.234567891,'0002':2.5})


def payload(modo='hoy',d=None,ps='normal'):
    return datos.armar(muestra() if d is None else d,COLS,precios=precios() if isinstance(ps,str) else ps,modo=modo,rango=RANGO)


class Contrato(unittest.TestCase):
    def test_cabecera_una_vez_costos_y_precision(self):
        d=muestra();base,cortes=mp.lineas_porcionamientos(d,**COLS);P=payload();json.dumps(P,allow_nan=False)
        self.assertEqual(len(P['filas']),len(base));self.assertEqual(len(P['cortes']),len(cortes))
        p=P['porciones']['P-01'];self.assertAlmostEqual(p['costoDia'],118);self.assertAlmostEqual(p['valorDia'],118*2.123456789/10.123456789)
        self.assertAlmostEqual(p['valorHoy'],2.123456789*precios()['0001']);self.assertEqual(p['cortes'],2)
        self.assertEqual(P['sello'],payload()['sello']);d.loc[0,'M']+=.000000001;self.assertNotEqual(P['sello'],payload(d=d)['sello'])
        self.assertFalse(P['familia']);self.assertTrue(P['merma'])

    def test_identidad_origen_estable_entre_valorizaciones(self):
        a,b=payload('hoy'),payload('dia');self.assertNotEqual(a['sello'],b['sello']);self.assertEqual(a['sello_origen'],b['sello_origen'])
        self.assertEqual(datos.valorar(a,'dia')['sello'],b['sello']);self.assertEqual(datos.valorar(b,'hoy')['sello'],a['sello'])
        self.assertEqual(a['cortes'],b['cortes'])
        d=muestra();d.loc[0,'Q']+=1;self.assertNotEqual(a['sello_origen'],payload(d=d)['sello_origen'])

    def test_sin_precio_fallback_y_sin_mezclar_bases_por_codigo(self):
        P=payload(ps=None);self.assertEqual(P['valoracion'],'dia');self.assertEqual(P['valoracion_solicitada'],'hoy')
        self.assertIsNone(P['porciones']['P-01']['valorHoy'])
        P=payload();r=P['porciones']['P-05'];self.assertFalse(r['precioDisponible']);self.assertEqual(r['valorHoy'],0)
        self.assertIn('Sin precio actual',r['flags']);self.assertIn('Sin cortes',r['flags'])

    def test_cantidades_invalidas_y_mermas_fuera_de_rango_no_se_corrigen(self):
        P=payload();p=P['porciones']
        self.assertIn('Cantidad sin base',p['P-04']['flags']);self.assertIsNone(p['P-04']['pctFisico'])
        self.assertGreater(p['P-04']['valorHoy'],0);self.assertEqual(p['P-04']['valorDia'],0)
        self.assertEqual(p['P-06']['pctFisico'],150);self.assertEqual(p['P-09']['pctFisico'],-5)
        self.assertIn('Merma sin dato',p['P-07']['flags']);self.assertIn('Sin producto de origen',p['P-08']['flags'])


class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if comun.sync_playwright is None:raise unittest.SkipTest('sin Playwright')
        comun.Navegador.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):comun.Navegador.tearDownClass.__func__(cls)

    def calc(self,s=None,P=None):return self.pg.evaluate('([P,s])=>__movPeriodoDatos.calcular(P,__movPeriodoDatos.estado(s))',[P or payload(),s or {}])

    def mount(self,P=None):
        self.pg.evaluate('P=>{const old=window.__movPeriodo;old?.abort.abort();old?.ro?.disconnect();window.__movPeriodoEstados={};window.__requests=[];document.querySelector("#montar").replaceChildren();__montarMov({data:P,parentElement:document.querySelector("#montar"),setTriggerValue:(...v)=>__requests.push(v)})}',P or payload())
        return self.pg.locator('.mv')

    def test_cada_grano_y_base_contra_funciones_originales(self):
        base,_=mp.lineas_porcionamientos(muestra(),**COLS)
        for modo in ['hoy','dia']:
            b=mp.a_precio_de_hoy(base,precios()) if modo=='hoy' else base
            for gran in comun.datos.GRANOS:
                for filtro in [{},{'area':['Cocina']},{'tipo':['Luis']},{'prod':['Origen A']}]:
                    ref=b.copy()
                    for k,v in filtro.items():ref=ref[ref[k].isin(v)]
                    ref['clave']=mp._periodo_serie(ref.fecha,gran);rs=mp.resumen_por_periodo(ref,mp.PORCIONAMIENTOS)
                    a=self.calc({'gran':gran,**filtro},payload(modo));self.assertAlmostEqual(a['total'],float(rs.valor.sum()),places=7)
                    self.assertAlmostEqual(a['costo'],float(rs.costo.sum()),places=7);self.assertEqual(a['nDocs'],len(ref))
                    self.assertEqual([s['clave'] for s in a['series']],list(rs.index))
                    for s,(_,r) in zip(a['series'],rs.iterrows()):
                        for k in ['valor','costo','cortes','docs','cant']:self.assertAlmostEqual(s[k],float(r[k]),places=7)

    def test_porcentaje_monetario_no_promedia_porcentajes_fisicos(self):
        P=payload();a=self.calc({'prod':['Origen A']},P);self.mount(P)
        self.pg.evaluate('()=>{const G=__movPeriodo;G.s.prod=["Origen A"];__movPeriodoDatos.dibujar(G)}')
        self.assertAlmostEqual(a['total']/a['costo'],sum(r['valorHoy'] for k,r in P['porciones'].items() if k in ['P-01','P-02'])/sum(r['costoHoy'] for k,r in P['porciones'].items() if k in ['P-01','P-02']))
        self.assertNotAlmostEqual(a['total']/a['costo'],sum(P['porciones'][k]['pctFisico']/100 for k in ['P-01','P-02'])/2)

    def test_cortes_y_busqueda_no_mutilan_la_cabecera(self):
        a=self.calc({'q':'util b','modo':'Detalle'});self.assertEqual([r['doc'] for r in a['docs']],['P-01']);self.assertEqual(len(a['lineas']),2)
        self.assertAlmostEqual(sum(r['valor'] for r in a['lineas']),118);self.assertEqual(a['lineas'][0]['unidOrigen'],'KILOS')
        self.assertAlmostEqual(a['porcion']['cant'],10.123456789)

    def test_observaciones_solo_filtran_lista_y_documentos_sin_nombre_cuentan(self):
        a=self.calc();self.assertEqual(a['nDocs'],9)
        for marca,doc in [('Sin cortes','P-05'),('Sin precio actual','P-05'),('Merma fuera de rango','P-06'),('Merma sin dato','P-07'),('Sin producto de origen','P-08')]:
            b=self.calc({'porcFlag':marca});self.assertIn(doc,[r['doc'] for r in b['docs']]);self.assertEqual(a['total'],b['total'])
        b=self.calc({'fam':['Familia ajena']});self.assertEqual(a['total'],b['total'])

    def test_kpi_ficha_y_cambio_de_valorizacion_conserva_seleccion(self):
        root=self.mount();root.locator('[data-a=modo][data-v=Detalle]').click();root.locator('[data-input=q]').fill('util b')
        root.locator('.mv-ficha-porc summary').click();self.assertIn('dos valorizaciones',root.inner_text())
        self.pg.evaluate('()=>{const G=__movPeriodo;G.s.foco=G.D.claves[0];G.s.doc="P-01";__movPeriodoDatos.dibujar(G)}')
        foco=self.pg.evaluate('__movPeriodo.s.foco')
        self.pg.evaluate('P=>__montarMov({data:P,parentElement:document.querySelector("#montar")})',payload('dia'))
        self.assertEqual(self.pg.evaluate('__movPeriodo.s.foco'),foco);self.assertEqual(self.pg.evaluate('__movPeriodo.s.doc'),'P-01')
        self.assertTrue(root.locator('.mv-ficha-porc').evaluate('e=>e.open'))
        self.assertEqual(self.pg.evaluate('__requests.length'),0)

    def test_selector_compartido_se_dibuja_y_no_cambia_base_elegida(self):
        from graficos import porcionamientos_pieza as pieza
        fake=SimpleNamespace(session_state={'mov_graf_filtro_fam':['No aplica']},markdown=Mock(),container=lambda **kw:nullcontext())
        control=Mock()
        with patch.object(pieza,'st',fake),patch.object(pieza.mm,'valorizacion',return_value=pieza.mm.VALOR_DIA),patch.object(pieza.mm,'precios_hoy',return_value=precios()),patch.object(pieza,'_PIEZA') as comp:
            pieza.renderizar(muestra(),COLS,control=control,rango=RANGO)
        control.assert_called_once();P=comp.call_args.kwargs['data'];self.assertEqual(P['valoracion'],'dia');self.assertNotIn('Familias de la página',P['contexto'])
        a=self.calc(P=P);ref,_=mp.lineas_porcionamientos(muestra(),**COLS);self.assertAlmostEqual(a['total'],float(ref.valor.sum()),places=7)

    def test_cambio_de_base_reutiliza_cabeceras_y_cortes_en_python(self):
        from graficos import porcionamientos_pieza as pieza
        fake=SimpleNamespace(session_state={},markdown=Mock(),container=lambda **kw:nullcontext())
        original=pieza.datos.armar
        with patch.object(pieza,'st',fake),patch.object(pieza.mm,'valorizacion') as modo,patch.object(pieza.mm,'precios_hoy',return_value=precios()),patch.object(pieza.datos,'armar',wraps=original) as construir,patch.object(pieza,'_PIEZA') as comp:
            modo.return_value=pieza.mm.VALOR_HOY;pieza.renderizar(muestra(),COLS,control=Mock(),rango=RANGO)
            modo.return_value=pieza.mm.VALOR_DIA;pieza.renderizar(muestra(),COLS,control=Mock(),rango=RANGO)
        self.assertEqual(construir.call_count,1);P=comp.call_args.kwargs['data'];self.assertEqual(P['valoracion'],'dia')
        self.assertAlmostEqual(self.calc(P=P)['total'],sum(p['valorDia'] for p in P['porciones'].values()),places=7)

    def test_excel_cabeceras_y_cortes_separados_con_contexto(self):
        root=self.mount();root.locator('[data-a=modo][data-v=Detalle]').click();root.locator('[data-input=q]').fill('util b')
        h=self.pg.evaluate('__movPeriodoDatos.exportar(__movPeriodo).hojas');cs=next(x for x in h if x['nombre']=='Cortes de documentos visibles');self.assertEqual(len(cs['filas']),2)
        dv=next(x for x in h if x['nombre']=='Dos valorizaciones');self.assertEqual(len(dv['filas']),1)
        with self.pg.expect_download() as down:root.locator('[data-a=excel]').click()
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'porc.xlsx';down.value.save_as(path)
            with zipfile.ZipFile(path) as z:
                text=' '.join(z.read(n).decode() for n in z.namelist() if n.endswith('.xml'))
                for palabra in ['Dos valorizaciones','Cortes del elegido','Valorización efectiva','Unidad de origen','<v>10.123457</v>']:self.assertIn(palabra,text)
                self.assertNotIn('<f>',text)

    def test_fuente_vacia_sin_precio_y_movil(self):
        self.mount(payload(ps=None));self.assertIn('precio actual no disponible',self.pg.locator('.mv').inner_text())
        self.mount(payload(d=muestra().iloc[:0]));self.assertEqual(self.pg.evaluate('__movPeriodo.D.nDocs'),0)
        self.pg.set_viewport_size({'width':390,'height':844});self.assertLessEqual(self.pg.evaluate('document.documentElement.scrollWidth'),390)
        self.pg.set_viewport_size({'width':1323,'height':619})

    def test_cortes_largos_se_dibujan_por_tandas_y_se_exportan_todos(self):
        b=muestra().iloc[[0]].copy();d=pd.concat([b.assign(PF=f'Corte {i:03d}',CF=f'C{i:03d}',QF=.04,PS=.04) for i in range(220)],ignore_index=True)
        root=self.mount(payload(d=d));root.locator('[data-a=modo][data-v=Detalle]').click()
        t=root.locator('[data-tabla=lineas]');self.assertEqual(t.locator('tbody tr').count(),150)
        t.evaluate('e=>{e.scrollTop=e.scrollHeight;e.dispatchEvent(new Event("scroll"))}')
        self.assertEqual(t.locator('tbody tr').count(),220)
        h=self.pg.evaluate('__movPeriodoDatos.exportar(__movPeriodo).hojas');self.assertEqual(len(next(x for x in h if x['nombre']=='Cortes del elegido')['filas']),220)
        self.assertEqual(self.pg.evaluate('__movPeriodo.D.nDocs'),1)


if __name__=='__main__':unittest.main(verbosity=2)
