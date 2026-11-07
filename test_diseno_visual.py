"""Editor visual: preview, historial y entrega, en Chromium sin red."""
import ast
from pathlib import Path
import re
import unittest

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


ROOT = Path(__file__).parent
PALETA = '[{"nombre":"Acento","hex":"#6c5ce7"}, {"nombre":"Blanco","hex":"#ffffff"}, {"nombre":"Gris borde","hex":"#dddddd"}, {"nombre":"Texto principal","hex":"#222222"}]'


def script_editor():
    module = ast.parse((ROOT / 'inyecciones/_diseno_js.py').read_text(encoding='utf-8'))
    js = ast.literal_eval(next(n.value for n in module.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'JS' for t in n.targets)))
    js = js.replace('__PALETA__', PALETA).replace('<script>', '').replace('</script>', '')
    return js.rsplit('})();', 1)[0] + '''
    win.editorPrueba = { registroPara, establecerCambio, establecerCambioEstilo,
        aplicarEstado, sync, construirBloqueCSS, accionEdicion, deshacerEdicion,
        cambiarPerfil, exportarEdicion, agregarMock, ajustarGrupo, aplicarMedida,
        reaplicarEdicion, mostrarPreview, mostrarEntrega, instalarHistorial,
        tablaDe, aplicarEstiloTabla };
    })();'''


HTML = '''<!doctype html><html><head><style>
body {margin:0;font-family:Arial} main {padding:20px}
.fila {display:flex;gap:30px;align-items:flex-start}
.st-key-a,.st-key-b,.st-key-c {width:180px;height:120px;flex:none;border-radius:8px}
.st-key-a {background-color:rgb(255,0,0)!important}
.st-key-b {background-color:rgb(0,0,255);margin-top:30px}
.st-key-c {background-color:rgb(240,240,240);margin-top:60px}
.st-key-boton {width:180px;height:40px;margin-top:20px}
.st-key-boton button {width:180px;height:40px;background:rgb(255,0,0)}
.st-key-boton button p {font-size:13px!important;margin:0}
.st-key-box {width:500px;margin-top:15px}.st-key-box span {display:block}
@media(max-width:600px) {.fila {flex-direction:column}}
</style></head><body><div class="stApp"><main data-testid="stMainBlockContainer">
<div class="fila"><div class="st-key-a">A</div><div class="st-key-b">B</div><div class="st-key-c">C</div></div>
<div class="st-key-boton"><button><p>Ejemplo</p></button></div>
<div class="st-key-box"><span class="dv-item">Uno</span><span class="dv-item">Dos</span></div>
<div class="st-key-piece"></div></main></div></body></html>'''


@unittest.skipIf(sync_playwright is None, 'sin Playwright')
class EditorVisual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)
        cls.js = script_editor()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1366, 'height': 900})
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('http://editor.test/**', lambda route: route.fulfill(body=HTML, content_type='text/html'))
        self.page.goto('http://editor.test/?debug=1&diseno=1')
        self.page.evaluate(self.js)
        self.page.evaluate('clearInterval(window.__disenoPollInterval)')
        self.pin('a')

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [])
        finally:
            self.page.close()

    def pin(self, key, sub=None, idx=0):
        self.page.evaluate('''d => {
            window.__inspectorPinned = true;
            window.__inspectorUltimo = {key:d.key};
            window.__disenoState.sub = d.sub ? {key:d.key,clase:d.sub,idx:d.idx} : null;
            editorPrueba.sync();
        }''', {'key': key, 'sub': sub, 'idx': idx})

    def color(self, selector):
        return self.page.locator(selector).evaluate('e => getComputedStyle(e).backgroundColor')

    def editar(self, prop, value):
        self.page.evaluate('''d => editorPrueba.accionEdicion(() => {
            const r = window.__inspectorUltimo.key;
            editorPrueba.establecerCambioEstilo(document.querySelector('.st-key-'+r),
                editorPrueba.registroPara(r), d.prop, d.value);
        })''', {'prop': prop, 'value': value})

    def test_css_exportado_reproduce_la_prioridad_del_preview(self):
        self.editar('background-color', 'rgb(0,128,0)')
        self.assertEqual(self.color('.st-key-a'), 'rgb(0, 128, 0)')
        css = self.page.evaluate('''() => editorPrueba.construirBloqueCSS('a',
            document.querySelector('.st-key-a'),editorPrueba.registroPara('a'),'',null)''')
        self.page.locator('.st-key-a').evaluate('e => e.style.cssText=""')
        self.page.add_style_tag(content=css)
        self.assertEqual(self.color('.st-key-a'), 'rgb(0, 128, 0)')

    def test_original_incluye_boton_y_texto_internos(self):
        self.pin('boton')
        self.editar('background-color', 'rgb(0,128,0)')
        self.editar('font-size', '24px')
        self.assertEqual(self.color('.st-key-boton button'), 'rgb(0, 128, 0)')
        self.page.get_by_role('button', name='Ver original', exact=True).click()
        self.assertEqual(self.color('.st-key-boton button'), 'rgb(255, 0, 0)')
        self.assertEqual(self.page.locator('.st-key-boton p').evaluate('e=>getComputedStyle(e).fontSize'), '13px')
        self.page.get_by_role('button', name='Ver con cambios', exact=True).click()
        self.assertEqual(self.color('.st-key-boton button'), 'rgb(0, 128, 0)')

    def test_recreacion_de_elemento_sin_seleccion_conserva_cambios(self):
        self.editar('background-color', 'rgb(0,128,0)')
        self.pin('b')
        self.page.locator('.st-key-a').evaluate('e=>e.outerHTML=\'<div class="st-key-a">Nueva A</div>\'')
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(self.color('.st-key-a'), 'rgb(0, 128, 0)')

    def test_medidas_deshacer_rehacer_y_teclado(self):
        ancho = self.page.get_by_role('spinbutton', name='Ancho (px)', exact=True)
        ancho.fill('250')
        ancho.press('Tab')
        self.page.wait_for_timeout(30)
        self.assertEqual(self.page.locator('.st-key-a').evaluate('e=>e.getBoundingClientRect().width'), 250)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.page.locator('.st-key-a').evaluate('e=>e.getBoundingClientRect().width'), 180)
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(self.page.locator('.st-key-a').evaluate('e=>e.getBoundingClientRect().width'), 250)
        self.page.evaluate('document.activeElement.blur()')
        self.page.keyboard.press('ArrowRight')
        self.assertEqual(self.page.evaluate('__disenoState.porKey.a.transformState.translateX'), 1)
        self.page.keyboard.press('Control+z')
        self.assertEqual(self.page.evaluate('__disenoState.porKey.a.transformState.translateX'), 0)

    def test_distribucion_no_mueve_nodos_de_react(self):
        self.pin('box')
        original = self.page.locator('.st-key-box').inner_html()
        self.page.get_by_label('Distribución del contenedor', exact=True).select_option('grid')
        self.assertEqual(self.page.locator('.st-key-box').evaluate('e=>getComputedStyle(e).display'), 'grid')
        self.assertEqual(self.page.locator('.st-key-box').inner_html(), original)
        self.page.get_by_label('Columnas de la rejilla', exact=True).fill('3')
        self.page.get_by_label('Columnas de la rejilla', exact=True).press('Tab')
        self.assertIn('repeat(3', self.page.locator('.st-key-box').get_attribute('style'))

    def test_grupo_alinea_y_recupera_el_estado_anterior(self):
        self.pin('b')
        self.page.evaluate("__disenoState.grupo=['a','b']; editorPrueba.sync()")
        self.page.get_by_role('button', name='Arriba', exact=True).click()
        tops = self.page.locator('.st-key-a,.st-key-b').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().top)')
        self.assertEqual(tops[0], tops[1])
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        tops = self.page.locator('.st-key-a,.st-key-b').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().top)')
        self.assertNotEqual(tops[0], tops[1])

    def test_colores_se_aplican_al_grupo_en_una_sola_accion(self):
        self.pin('b')
        self.page.evaluate("__disenoState.grupo=['a','b']; editorPrueba.sync()")
        self.page.get_by_label('Fondo del grupo', exact=True).select_option('#6c5ce7')
        self.assertEqual(self.color('.st-key-a'), 'rgb(108, 92, 231)')
        self.assertEqual(self.color('.st-key-b'), 'rgb(108, 92, 231)')
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.color('.st-key-a'), 'rgb(255, 0, 0)')
        self.assertEqual(self.color('.st-key-b'), 'rgb(0, 0, 255)')

    def test_variantes_independientes_y_entrega_completa(self):
        self.editar('background-color', 'rgb(0,128,0)')
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.editar('background-color', 'rgb(0,0,255)')
        self.page.evaluate("editorPrueba.accionEdicion(()=>editorPrueba.agregarMock('indicador'))")
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('@media (max-width: 600px)', entrega)
        self.assertIn('rgb(0,128,0)', entrega)
        self.assertIn('rgb(0,0,255)', entrega)
        self.assertIn('Insertar indicador', entrega)
        self.assertIn('1,234', entrega)
        self.page.get_by_label('Diseñar para', exact=True).select_option('general')
        self.assertEqual(self.color('.st-key-a'), 'rgb(0, 128, 0)')
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 0)
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.assertEqual(self.color('.st-key-a'), 'rgb(0, 0, 255)')
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 1)

    def test_estilo_compartido_actualiza_todos_los_vinculados(self):
        self.editar('background-color', 'rgb(0,128,0)')
        self.page.get_by_text('Estilos compartidos', exact=True).click()
        self.page.get_by_label('Nombre del estilo compartido').fill('Tarjetas')
        self.page.get_by_role('button', name='Crear o actualizar estilo', exact=True).click()
        self.pin('b')
        self.page.get_by_label('Aplicar estilo', exact=True).select_option('Tarjetas')
        self.assertEqual(self.color('.st-key-b'), 'rgb(0, 128, 0)')
        self.pin('a')
        self.editar('background-color', 'rgb(255,255,0)')
        self.page.get_by_label('Nombre del estilo compartido').fill('Tarjetas')
        self.page.get_by_role('button', name='Crear o actualizar estilo', exact=True).click()
        self.assertEqual(self.color('.st-key-a'), 'rgb(255, 255, 0)')
        self.assertEqual(self.color('.st-key-b'), 'rgb(255, 255, 0)')

    def test_componentes_se_pueden_deshacer_y_rehacer(self):
        for tipo in ['boton', 'tarjeta', 'indicador', 'filtro']:
            self.page.evaluate('(t)=>editorPrueba.accionEdicion(()=>editorPrueba.agregarMock(t))', tipo)
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 4)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 3)
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 4)

    def test_subseleccion_repetida_y_shadow_root_se_exportan_sin_afectar_vecinos(self):
        self.page.locator('.st-key-piece').evaluate('e=>e.attachShadow({mode:"open"}).innerHTML=\'<div class="dv-tile">Uno</div><div class="dv-tile">Dos</div>\'')
        self.pin('piece', 'dv-tile', 1)
        self.page.get_by_label('Desplazamiento X (px)', exact=True).fill('10')
        self.page.get_by_label('Desplazamiento X (px)', exact=True).press('Tab')
        exportado = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('CSS de la pieza', exportado)
        self.assertIn('nth-child(2)', exportado)
        transforms = self.page.locator('.dv-tile').evaluate_all('es=>es.map(e=>getComputedStyle(e).transform)')
        self.assertEqual(transforms[0], 'none')
        self.assertNotEqual(transforms[1], 'none')

    def test_vista_previa_movil_es_aislada_y_sin_scripts(self):
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.page.get_by_role('button', name='Vista previa', exact=True).click()
        frame = self.page.get_by_title('Vista previa del diseño').element_handle().content_frame()
        self.assertEqual(frame.evaluate('innerWidth'), 390)
        self.assertEqual(frame.locator('script').count(), 0)
        self.assertEqual(frame.locator('.fila').evaluate('e=>getComputedStyle(e).flexDirection'), 'column')
        self.page.get_by_role('button', name='Cerrar vista previa', exact=True).click()
        self.assertEqual(self.page.locator('#el-diseno-preview').count(), 0)

    def test_reset_de_variante_sobrescribe_el_general_en_la_entrega(self):
        self.editar('background-color', 'rgb(0,128,0)')
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.page.evaluate('''() => editorPrueba.accionEdicion(() => {
            editorPrueba.establecerCambioEstilo(document.querySelector('.st-key-a'),
                editorPrueba.registroPara('a'),'background-color',null);
        })''')
        self.assertEqual(self.color('.st-key-a'), 'rgb(255, 0, 0)')
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        css = '\n'.join(re.findall(r'```css\n(.*?)\n```', entrega, re.S))
        self.page.locator('.st-key-a').evaluate('e=>e.style.cssText=""')
        self.page.add_style_tag(content=css)
        self.page.set_viewport_size({'width': 390, 'height': 900})
        self.assertEqual(self.color('.st-key-a'), 'rgb(255, 0, 0)')
        self.page.set_viewport_size({'width': 1366, 'height': 900})
        self.assertEqual(self.color('.st-key-a'), 'rgb(0, 128, 0)')

    def test_reset_de_movimiento_en_variante_se_exporta_sobre_la_caja(self):
        self.pin('boton')
        self.page.get_by_label('Desplazamiento X (px)', exact=True).fill('30')
        self.page.get_by_label('Desplazamiento X (px)', exact=True).press('Tab')
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.page.get_by_label('Desplazamiento X (px)', exact=True).fill('0')
        self.page.get_by_label('Desplazamiento X (px)', exact=True).press('Tab')
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        css = '\n'.join(re.findall(r'```css\n(.*?)\n```', entrega, re.S))
        self.page.locator('.st-key-boton').evaluate('e=>e.style.cssText=""')
        self.page.add_style_tag(content=css)
        self.page.set_viewport_size({'width':390,'height':900})
        self.assertEqual(self.page.locator('.st-key-boton').evaluate('e=>getComputedStyle(e).transform'), 'none')

    def test_entrega_incluye_texto_sin_css_y_se_puede_cerrar(self):
        self.page.evaluate('''() => editorPrueba.accionEdicion(() => {
            editorPrueba.registroPara('a').texto.actual='Nuevo titulo';
        })''')
        self.page.get_by_role('button', name='Todos los cambios', exact=True).click()
        self.assertIn('Nuevo titulo', self.page.get_by_label('Todos los cambios para implementar').input_value())
        self.page.get_by_role('button', name='Cerrar entrega', exact=True).click()
        self.assertEqual(self.page.locator('#el-diseno-entrega').count(), 0)

    def test_edicion_de_texto_se_deshace_y_rehace(self):
        self.page.get_by_label('Texto de vista previa', exact=True).fill('Texto nuevo')
        self.assertEqual(self.page.locator('.st-key-a').inner_text(), 'Texto nuevo')
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.page.locator('.st-key-a').inner_text(), 'A')
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(self.page.locator('.st-key-a').inner_text(), 'Texto nuevo')

    def test_se_puede_seguir_editando_un_texto_insertado_despues_de_exportar(self):
        self.page.evaluate("editorPrueba.accionEdicion(()=>editorPrueba.agregarMock('texto'))")
        self.page.evaluate('editorPrueba.exportarEdicion()')
        self.page.locator('[data-diseno-mock="texto"]').fill('Texto despues de exportar')
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('Texto despues de exportar', entrega)

    def test_inspector_real_selecciona_con_clic_derecho(self):
        module = ast.parse((ROOT / 'inyecciones/_inspector_js.py').read_text(encoding='utf-8'))
        js = max((n.value for n in ast.walk(module)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)), key=len)
        js = re.sub(r'__[A-Z_]+__', '{}', js).replace('<script>', '').replace('</script>', '')
        self.page.evaluate(js)
        self.page.evaluate('window.__inspectorPinned=false')
        self.page.locator('.st-key-b').click(button='right')
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(self.page.evaluate('__inspectorUltimo.key'), 'b')
        self.assertTrue(self.page.evaluate('__inspectorPinned'))
        self.assertEqual(self.page.locator('#el-diseno-panel [data-diseno-mejoras]').count(), 1)

    def test_script_sobrevive_al_reemplazo_del_iframe_que_lo_inyecta(self):
        self.editar('background-color', 'rgb(0,128,0)')
        frame = self.page.evaluate_handle('''() => {
            const f=document.createElement('iframe'); f.id='montaje-editor';
            document.body.appendChild(f); return f;
        }''').as_element().content_frame()
        frame.evaluate(self.js)
        self.page.locator('#montaje-editor').evaluate('e=>e.remove()')
        frame2 = self.page.evaluate_handle('''() => {
            const f=document.createElement('iframe'); f.id='montaje-editor';
            document.body.appendChild(f); return f;
        }''').as_element().content_frame()
        frame2.evaluate(self.js)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.color('.st-key-a'), 'rgb(255, 0, 0)')
        self.page.evaluate('clearInterval(window.__disenoPollInterval)')

    def test_remontaje_no_duplica_panel_ni_historial_y_no_hay_borradores(self):
        self.editar('background-color', 'rgb(0,128,0)')
        self.page.evaluate(self.js)
        self.page.evaluate('clearInterval(window.__disenoPollInterval)')
        self.assertEqual(self.page.locator('[data-diseno-mejoras]').count(), 1)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.color('.st-key-a'), 'rgb(255, 0, 0)')
        self.assertEqual(self.page.evaluate('localStorage.length+sessionStorage.length'), 0)

    def test_reactivar_editor_sin_pin_y_en_grupo_vuelve_a_mostrar_panel(self):
        for grupo in [[], ['a', 'b']]:
            self.page.evaluate('''g => {
                __inspectorPinned=false; __disenoState.grupo=g;
                history.replaceState({},'', '/?debug=1&diseno=1'); editorPrueba.sync();
                history.replaceState({},'', '/?debug=1'); editorPrueba.sync();
            }''', grupo)
            self.assertFalse(self.page.locator('#el-diseno-panel').is_visible())
            self.page.evaluate("history.replaceState({},'', '/?debug=1&diseno=1'); editorPrueba.sync()")
            self.assertTrue(self.page.locator('#el-diseno-panel').is_visible())

    def montar_tabla(self):
        self.page.evaluate('''() => {
            const f=document.createElement('iframe'); f.title='st_aggrid.AgGrid.agGrid';
            document.querySelector('.st-key-box').appendChild(f);
            const d=f.contentDocument;
            d.body.innerHTML='<div id="gridContainer"><div class="ag-root-wrapper"><div class="ag-header"><div class="ag-header-cell"><span class="ag-header-cell-text">Nombre</span></div></div><div class="ag-row"><div class="ag-cell">Uno</div></div></div></div>';
            let rowHeight=20;
            d.__disenoAgApi={getGridOption:()=>rowHeight,setGridOption:(k,v)=>{rowHeight=v},resetRowHeights:()=>{}};
        }''')
        self.pin('box')

    def test_original_de_tabla_incluye_estilo_y_altura_de_filas(self):
        self.montar_tabla()
        self.page.evaluate('''() => editorPrueba.accionEdicion(() => {
            const t=editorPrueba.tablaDe('box'); t.cabFondo='#6c5ce7'; t.filaAlto=34;
            editorPrueba.aplicarEstiloTabla('box');
        })''')
        alto = "document.querySelector('.st-key-box iframe').contentDocument.__disenoAgApi.getGridOption('rowHeight')"
        self.assertEqual(self.page.evaluate(alto), 34)
        self.page.get_by_role('button', name='Ver original', exact=True).click()
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(self.page.evaluate(alto), 20)
        self.assertEqual(self.page.frame_locator('.st-key-box iframe').locator('#diseno-tabla-css').count(), 0)
        self.page.get_by_role('button', name='Ver con cambios', exact=True).click()
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(self.page.evaluate(alto), 34)

    def test_historial_restaura_altura_de_tabla_y_tamano_de_plotly(self):
        self.montar_tabla()
        self.page.evaluate('''() => editorPrueba.accionEdicion(() => {
            editorPrueba.tablaDe('box').filaAlto=34; editorPrueba.aplicarEstiloTabla('box');
        })''')
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.page.evaluate("document.querySelector('.st-key-box iframe').contentDocument.__disenoAgApi.getGridOption('rowHeight')"), 20)
        self.page.evaluate('''() => {
            const gd=document.createElement('div'); gd.className='js-plotly-plot';
            gd.layout={width:300,height:160}; document.querySelector('.st-key-c').appendChild(gd);
            window.Plotly={relayout:(g,layout)=>{Object.assign(g.layout,layout); return Promise.resolve();}};
        }''')
        self.pin('c')
        self.page.get_by_label('Ancho (px)', exact=True).fill('450')
        self.page.get_by_label('Ancho (px)', exact=True).press('Tab')
        self.assertEqual(self.page.evaluate("document.querySelector('.js-plotly-plot').layout.width"), 450)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.page.evaluate("document.querySelector('.js-plotly-plot').layout.width"), 300)


if __name__ == '__main__':
    unittest.main()
