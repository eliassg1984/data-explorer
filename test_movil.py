"""La presentación móvil conserva eventos, estado y montaje de las piezas."""

import ast
from pathlib import Path
import unittest

from graficos.movil import css_movil, js_movil

ROOT = Path(__file__).parent


class ContratoMovil(unittest.TestCase):
    def test_las_piezas_comparten_la_presentacion(self):
        miradas = 0
        for path in [*ROOT.glob('graficos/**/*.py'), ROOT / 'formulario_receta.py']:
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.Call) and ast.unparse(node.func) == 'st.components.v2.component':
                    for kw in node.keywords:
                        if kw.arg in ('css', 'js'):
                            self.assertIsInstance(kw.value, ast.Call, str(path))
                            self.assertEqual(ast.unparse(kw.value.func), kw.arg + '_movil', str(path))
                    miradas += 1
        self.assertGreater(miradas, 40)

    def test_inline_sin_montaje_no_cambia(self):
        self.assertEqual(js_movil('console.log("listo")'), 'console.log("listo")')
        self.assertIn('@media (max-width: 900px)', css_movil('.re{}'))


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, 'sin Playwright')
class PresentacionEnNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.browser = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def test_panel_conserva_eventos_y_estado_y_se_restaura_en_escritorio(self):
        page = self.browser.new_page(viewport={'width': 390, 'height': 844})
        try:
            page.set_content('<div id="host"></div>')
            page.add_style_tag(content=css_movil('body{margin:12px}.vp{display:flex;flex-direction:column}.fils{display:flex}'))
            original = '''export default function(component) {
              const root=document.createElement('div');root.className='vp';component.parentElement.append(root);
              const pintar=()=>{root.innerHTML=`<h2>Venta por período</h2><div class="fils"><select><option>Todos</option><option selected>Salón</option></select><input value="Lomo"><button data-click>Aplicar</button></div><div class="tabla"><table><tr>${'<th>Columna</th>'.repeat(6)}</tr><tr>${'<td>123.456789</td>'.repeat(6)}</tr></table></div><output>${window.clics||0}</output>`};pintar();
              root.addEventListener('click',e=>{if(e.target.matches('[data-click]')){window.clics=(window.clics||0)+1;pintar();}});
              return ()=>{window.limpiado=true};
            }'''
            page.add_script_tag(content=js_movil(original).replace('export default function(component)', 'window.montar=function(component)'))
            page.evaluate('()=>{window.limpiar=montar({parentElement:document.querySelector("#host")})}')
            page.locator('.rpt-movil-panel').wait_for()
            self.assertFalse(page.locator('.fils').is_visible())
            self.assertIn('Salón', page.locator('summary').inner_text())
            page.locator('summary').click()
            page.locator('[data-click]').click()
            page.locator('.rpt-movil-panel').wait_for()
            self.assertEqual(page.locator('output').inner_text(), '1')
            self.assertTrue(page.locator('.fils').is_visible())
            self.assertEqual(page.locator('input').input_value(), 'Lomo')
            self.assertEqual(page.locator('td').first.inner_text(), '123.456789')
            self.assertGreater(page.locator('table').evaluate('e=>e.offsetWidth'), page.locator('.vp').evaluate('e=>e.clientWidth'))
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth-innerWidth'), 1)
            page.set_viewport_size({'width': 1366, 'height': 768})
            page.wait_for_timeout(150)
            self.assertEqual(page.locator('.rpt-movil-panel').count(), 0)
            self.assertEqual(page.locator('.rpt-tabla-scroll').count(), 0)
            self.assertEqual(page.locator('.fils > select').count(), 1)
            page.evaluate('limpiar()')
            self.assertTrue(page.evaluate('window.limpiado'))
            self.assertTrue(page.evaluate('!document.querySelector("#host").__movilAdaptacion'))
        finally:
            page.close()

    def test_piezas_reales_en_vertical_horizontal_y_escritorio(self):
        import test_ventas_periodo as ventas
        import test_stock_producto_pieza as stock
        import test_movimientos_periodo_pieza as movimientos
        import test_compras_documentos_pieza as documentos
        import test_ajuste_pivote_pieza as pivote

        casos = [
            ('Ventas', ventas._armar()[1], ['ventas_periodo.js'], ['ventas_periodo.css'], '.vp'),
            ('Stock', stock.armar()[0], ['inventario_base.js', 'inventario_productos.js'], ['inventario_productos.css'], '.isp'),
            ('Movimientos', movimientos.payload()[0], ['movimientos_periodo.js'], ['movimientos_periodo.css'], '.mv'),
            ('Documentos', documentos.payload(documentos.muestra()), ['compras/documentos.js'], ['compras/documentos.css'], '.dc'),
            ('Ajuste', pivote.payload(), ['ajuste/pivote.js'], ['ajuste/pivote.css'], '.apv'),
        ]
        for nombre, datos, scripts, estilos, raiz in casos:
            with self.subTest(reporte=nombre):
                page = self.browser.new_page(viewport={'width': 390, 'height': 844})
                errores = []
                page.on('pageerror', lambda e: errores.append(str(e)))
                try:
                    page.set_content('<div id="host"></div>')
                    page.add_style_tag(content='body{margin:12px}:root{--alto-util:575px;--alto-util-base:575px}')
                    page.add_style_tag(content=css_movil('\n'.join((ROOT/'graficos'/p).read_text(encoding='utf-8') for p in estilos)))
                    js = (ROOT/'graficos/_xlsx.js').read_text(encoding='utf-8') + '\n'.join((ROOT/'graficos'/p).read_text(encoding='utf-8') for p in scripts)
                    page.add_script_tag(content=js_movil(js).replace('export default function(component)', 'window.montar=function(component)'))
                    page.evaluate('P=>montar({data:P,parentElement:document.querySelector("#host"),setTriggerValue:()=>{}})', datos)
                    page.locator(raiz).wait_for()
                    for w, h in ((390, 844), (320, 700), (844, 390)):
                        page.set_viewport_size({'width': w, 'height': h})
                        page.wait_for_timeout(250)
                        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth-innerWidth'), 2, nombre + str(w))
                        self.assertEqual(errores, [])
                        self.assertEqual(page.locator('.rpt-movil').count(), 1, nombre)
                        if nombre == 'Ventas':
                            self.assertEqual(page.locator('.et[transform]').count(), 0)
                            self.assertGreaterEqual(page.locator('.kpi').first.bounding_box()['width'], 100)
                    page.set_viewport_size({'width': 1366, 'height': 768})
                    page.wait_for_timeout(250)
                    self.assertEqual(page.locator('.rpt-movil-panel').count(), 0)
                    self.assertEqual(page.locator('.rpt-movil-kpis').count(), 0)
                finally:
                    page.close()

    def test_cabeceras_nativas_no_solapan_titulo_y_fecha(self):
        import re
        from estilos import get_css
        from navegacion import _CSS_AJUSTE

        page = self.browser.new_page(viewport={'width': 390, 'height': 844})
        try:
            page.set_content('''<style>body{margin:0}.block-container{box-sizing:border-box}.st-key-rec_carta_cab{display:flex}.chart-card-hdr{margin:0}button{height:28px}</style>
              <div data-testid="stAppViewContainer"><div class="st-key-app_reporte_recetas"></div>
              <main data-testid="stMain"><div data-testid="stMainBlockContainer" class="block-container">
              <div class="st-key-compras_tabs_row"></div><div class="st-key-rec_carta_cab">
              <div data-testid="stElementContainer"><p class="chart-card-hdr">Costo de Carta</p></div>
              <div data-testid="stLayoutWrapper"><div class="st-key-rec_carta_cab_fecha"><button data-testid="stPopoverButton">Últimos 3 meses · 25 jul – 24 oct</button></div></div>
              </div></div></main></div>''')
            hoja = re.sub(r'@import[^;]+;', '', get_css())
            page.add_style_tag(content=re.sub(r'</?style>', '', hoja))
            page.add_style_tag(content=re.sub(r'</?style>', '', _CSS_AJUSTE))
            for w, h in ((390, 844), (320, 700), (844, 390)):
                page.set_viewport_size({'width': w, 'height': h})
                page.wait_for_timeout(100)
                titulo = page.locator('.chart-card-hdr').bounding_box()
                fecha = page.locator('.st-key-rec_carta_cab_fecha').bounding_box()
                self.assertGreaterEqual(fecha['y'], titulo['y'] + titulo['height'])
                self.assertEqual(page.locator('[data-testid=stMainBlockContainer]').evaluate('e=>getComputedStyle(e).paddingTop'), '12px')
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth-innerWidth'), 1)
        finally:
            page.close()


if __name__ == '__main__':
    unittest.main()
