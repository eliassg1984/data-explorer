"""Barra y editor: apartar herramientas sin alterar la app ni perder el diseño."""
import ast
import json
import re
import unittest

from test_diseno_visual import HTML, ROOT, script_editor, sync_playwright


def script_herramienta(nombre):
    modulo = ast.parse((ROOT / 'inyecciones' / nombre).read_text(encoding='utf-8'))
    js = ast.literal_eval(next(n.value for n in modulo.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'JS' for t in n.targets)))
    js = re.sub(r'__[A-Z_]+__', '{}', js)
    return js.replace('<script>', '').replace('</script>', '')


@unittest.skipIf(sync_playwright is None, 'sin Playwright')
class HerramientasVisuales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)
        cls.inspector = script_herramienta('_inspector_js.py')
        cls.herramientas = script_herramienta('_herramientas_js.py')
        cls.editor = script_editor()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page(viewport={'width': 1366, 'height': 900})
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.route('http://editor.test/**', lambda r: r.fulfill(body=HTML, content_type='text/html'))
        self.page.goto('http://editor.test/?debug=1&diseno=1')
        self.page.evaluate('''() => {
            document.execCommand=()=>{window.textoCopiadoPrueba=document.activeElement.value||String(getSelection());return true;};
            Object.defineProperty(navigator,'clipboard',{value:{writeText:texto=>{window.textoCopiadoPrueba=texto;return Promise.resolve();}},configurable:true});
        }''')
        self.page.evaluate(self.inspector)
        self.page.evaluate(self.editor)
        self.page.evaluate(self.herramientas)

    def tearDown(self):
        try:
            self.assertEqual(self.errors, [])
        finally:
            self.page.close()

    def mover_barra(self, x, y):
        barra = self.page.locator('#herr-barra').bounding_box()
        agarre = self.page.get_by_role('button', name='Mover herramientas', exact=True).bounding_box()
        ax, ay = agarre['x'] + agarre['width']/2, agarre['y'] + agarre['height']/2
        self.page.mouse.move(ax, ay)
        self.page.mouse.down()
        self.page.mouse.move(ax + x - barra['x'], ay + y - barra['y'], steps=6)
        self.page.mouse.up()

    def pin(self, key, sub=None):
        self.page.evaluate('''d=>{
            __inspectorPinned=true; __inspectorUltimo={key:d.key};
            __disenoState.sub=d.sub?{key:d.key,clase:d.sub}:null;
            editorPrueba.sync();
        }''', {'key': key, 'sub': sub})

    def montar_cierre(self):
        from test_cierre_pieza import CSS, JS, datos, inventario

        self.page.add_script_tag(content=(ROOT / 'graficos/_xlsx.js').read_text(encoding='utf-8')
            + JS.replace('export default function(component)', 'window.montarCierrePrueba=function(component)'))
        self.page.locator('.st-key-piece').evaluate('''(e, [css, datos]) => {
            const r=e.attachShadow({mode:'open'}), estilo=document.createElement('style');
            e.style.setProperty('--accent-tint','rgb(235,230,255)');
            e.style.setProperty('--bg-card','rgb(255,255,255)');
            estilo.textContent=css; r.appendChild(estilo);
            const montaje=document.createElement('div'); r.appendChild(montaje);
            montarCierrePrueba({data:datos,parentElement:montaje,setTriggerValue:()=>{}});
        }''', [CSS, datos.armar(inventario())])
        self.page.get_by_role('button', name='Panel a la izquierda', exact=True).click()
        return self.page.locator('.st-key-piece select[data-change=corte]')

    def montar_zona_interna(self):
        self.page.locator('.st-key-piece').evaluate('''e=>{
            e.style.width='620px';
            e.attachShadow({mode:'open'}).innerHTML='<section class="dv-zona" style="padding:16px"><div class="dv-ancla" style="width:220px;height:32px">Ancla de la pieza</div></section>';
        }''')
        self.page.keyboard.press('Alt+t')
        self.page.locator('.dv-ancla').click(button='right')
        self.page.wait_for_function("__disenoState.sub?.clase==='dv-ancla'")

    def insertar_mock(self, tipo='Tarjeta', modo='flujo', posicion=None):
        boton = self.page.get_by_role('button', name='+ ' + tipo, exact=True, include_hidden=True)
        if not boton.is_visible():
            boton.locator('xpath=ancestor::details[1]/summary').click()
        if posicion:
            self.page.get_by_role('button', name=posicion, exact=True).click()
        if modo:
            self.page.get_by_label('Distribución al insertar', exact=True).select_option(modo)
        boton.click()
        key = self.page.evaluate('__disenoState.mocks.at(-1).key')
        return self.page.locator('.st-key-' + key)

    def insertar_tarjeta(self, modo='flujo', posicion=None):
        return self.insertar_mock('Tarjeta', modo, posicion)

    def seleccionar_insertado(self, nodo):
        key = nodo.evaluate('e=>e.classList[0].slice(7)')
        if not self.page.evaluate("k=>__inspectorPinned && __inspectorUltimo.key===k && !__disenoState.sub", key):
            nodo.click(button='right', position={'x': 30, 'y': 5})
        self.page.wait_for_function("k=>__inspectorPinned && document.getElementById('el-diseno-panel').dataset.builtForKey===k", arg=key)

    def clase_en_punto(self, punto):
        return self.page.evaluate('''p=>{
            let el=document.elementFromPoint(p.x,p.y);
            while(el && el.shadowRoot) {
                const siguiente=el.shadowRoot.elementFromPoint(p.x,p.y);
                if(!siguiente || siguiente===el) break;
                el=siguiente;
            }
            return el && el.getAttribute('class');
        }''', punto)

    def orden_insertados(self, punto):
        return self.page.evaluate('''p=>Array.from(new Set(document.elementsFromPoint(p.x,p.y)
            .map(e=>e.closest('[data-diseno-mock]')).filter(Boolean).map(e=>e.classList[0].slice(7))))''', punto)

    def test_crear_sin_seleccion_es_independiente_y_no_mueve_la_app(self):
        antes = self.page.locator('.stApp').bounding_box()
        scroll = self.page.evaluate('[scrollX,scrollY,document.documentElement.scrollWidth,document.documentElement.scrollHeight]')
        tarjeta = self.insertar_tarjeta(modo=None)
        self.assertTrue(self.page.evaluate('__disenoState.mocks[0].enLienzo'))
        self.assertEqual(self.page.get_by_label('Destino al insertar', exact=True).input_value(), 'lienzo')
        self.assertEqual(self.page.evaluate('__inspectorUltimo.key'), 'diseno_tarjeta_1')
        self.assertTrue(self.page.evaluate('__inspectorPinned'))
        self.assertEqual(self.page.evaluate('typeof textoCopiadoPrueba'), 'undefined')
        self.assertFalse(self.page.locator('#el-inspector-tip').is_visible())
        caja = tarjeta.bounding_box()
        self.assertGreaterEqual(caja['x'], 0)
        self.assertLessEqual(caja['x'] + caja['width'], 1136)
        self.assertGreaterEqual(caja['y'], 0)
        self.assertLessEqual(caja['y'] + caja['height'], 900)
        self.assertEqual(self.page.locator('.stApp').bounding_box(), antes)
        self.assertEqual(self.page.evaluate('[scrollX,scrollY,document.documentElement.scrollWidth,document.documentElement.scrollHeight]'), scroll)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(tarjeta.count(), 0)
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(tarjeta.count(), 1)
        self.assertEqual(tarjeta.bounding_box(), caja)
        self.page.locator('.st-key-a').evaluate('e=>e.remove()')
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(tarjeta.count(), 1)
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('directamente en el lienzo', entrega)
        self.assertNotIn('de __diseno_lienzo', entrega)

    def test_elegir_lienzo_con_algo_seleccionado_y_volver_a_insertar_dentro(self):
        self.montar_zona_interna()
        self.page.get_by_role('button', name='+ Insertar', exact=True).click()
        self.page.get_by_label('Destino al insertar', exact=True).select_option('lienzo')
        tarjeta = self.insertar_tarjeta(modo=None)
        otra = self.insertar_tarjeta(modo=None)
        self.assertTrue(self.page.evaluate('__disenoState.mocks.every(m=>m.enLienzo)'))
        self.assertEqual(otra.evaluate('e=>e.parentElement.id'), 'diseno-insertados-libres')
        self.pin('diseno_tarjeta_1')
        self.page.get_by_label('Destino al insertar', exact=True).select_option('seleccion')
        texto = self.insertar_mock('Texto', modo=None, posicion='Dentro')
        self.assertEqual(texto.evaluate('e=>e.parentElement.className'), tarjeta.get_attribute('class'))
        self.assertEqual(texto.get_attribute('data-diseno-distribucion'), 'flujo')
        self.assertFalse(self.page.evaluate('__disenoState.mocks.at(-1).enLienzo'))

    def test_tarjeta_independiente_se_conserva_en_perfiles_y_preview_movil(self):
        self.insertar_tarjeta(modo=None)
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.assertTrue(self.page.evaluate('__disenoState.mocks[0].enLienzo'))
        self.page.get_by_role('button', name='Vista previa', exact=True).click()
        marco = self.page.get_by_title('Vista previa del diseño').element_handle().content_frame()
        caja = marco.locator('.st-key-diseno_tarjeta_1').evaluate('e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})')
        self.assertGreaterEqual(caja['left'], 0)
        self.assertLessEqual(caja['right'], 390)
        self.assertEqual(marco.locator('script').count(), 0)

    def test_subir_y_bajar_una_capa_no_salta_las_otras_tarjetas(self):
        for _ in range(3):
            self.insertar_tarjeta(modo=None)
        self.page.evaluate('''()=>{
            const origen={...__disenoState.mocks[0].libre};
            __disenoState.mocks.forEach(m=>m.libre={...origen}); editorPrueba.sync();
        }''')
        caja = self.page.locator('.st-key-diseno_tarjeta_1').bounding_box()
        punto = {'x': caja['x'] + 40, 'y': caja['y'] + 35}
        self.assertEqual(self.orden_insertados(punto), ['diseno_tarjeta_3', 'diseno_tarjeta_2', 'diseno_tarjeta_1'])
        self.pin('diseno_tarjeta_1')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.orden_insertados(punto), ['diseno_tarjeta_3', 'diseno_tarjeta_1', 'diseno_tarjeta_2'])
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.orden_insertados(punto), ['diseno_tarjeta_1', 'diseno_tarjeta_3', 'diseno_tarjeta_2'])
        self.assertTrue(self.page.get_by_role('button', name='Subir una capa', exact=True).is_disabled())
        self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.assertEqual(self.orden_insertados(punto), ['diseno_tarjeta_3', 'diseno_tarjeta_1', 'diseno_tarjeta_2'])
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.orden_insertados(punto), ['diseno_tarjeta_1', 'diseno_tarjeta_3', 'diseno_tarjeta_2'])
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(self.orden_insertados(punto), ['diseno_tarjeta_3', 'diseno_tarjeta_1', 'diseno_tarjeta_2'])
        self.assertEqual(self.page.locator('.st-key-diseno_tarjeta_1').bounding_box(), caja)
        self.page.get_by_role('button', name='Traer al frente', exact=True).click()
        self.assertEqual(self.orden_insertados(punto)[0], 'diseno_tarjeta_1')
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        self.assertEqual(self.orden_insertados(punto)[-1], 'diseno_tarjeta_1')

    def test_pasos_de_capa_en_controles_reales_respetan_su_contenedor(self):
        self.montar_zona_interna()
        self.page.locator('.dv-zona').evaluate('''e=>{
            e.style.position='relative';
            for(const letra of ['a','b','c']) {
                const n=document.createElement('div'); n.className='dv-capa-'+letra;
                n.style.cssText='position:absolute;left:16px;top:16px;width:180px;height:40px;background:white';
                n.textContent=letra; e.appendChild(n);
            }
        }''')
        caja = self.page.locator('.dv-capa-a').bounding_box()
        punto = {'x': caja['x'] + 25, 'y': caja['y'] + 20}
        self.pin('piece', 'dv-capa-a')
        self.assertEqual(self.clase_en_punto(punto), 'dv-capa-c')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-capa-c')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-capa-a')
        self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-capa-c')
        self.assertEqual(self.page.locator('.dv-capa-a').bounding_box(), caja)
        self.assertEqual(self.page.locator('.st-key-piece').evaluate('e=>e.style.zIndex'), '')

    def test_ordenar_tarjetas_no_restaura_etiquetas_de_vecinos_no_seleccionados(self):
        self.page.locator('.st-key-boton p').evaluate('''e=>{
            const texto=document.createElement('div'); texto.dataset.testid='stMarkdownContainer';
            e.before(texto); texto.appendChild(e);
        }''')
        self.insertar_tarjeta(modo=None)
        self.insertar_tarjeta(modo=None)
        self.pin('diseno_tarjeta_1')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.page.locator('.st-key-boton p').evaluate('e=>e.textContent="Etiqueta actualizada por la app"')
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.page.locator('.st-key-boton p').inner_text(), 'Etiqueta actualizada por la app')

    def test_pasos_de_capa_dentro_de_tarjeta_no_cambian_su_capa_global(self):
        tarjeta = self.insertar_tarjeta(modo=None)
        self.page.get_by_label('Destino al insertar', exact=True).select_option('seleccion')
        for _ in range(3):
            self.insertar_mock('Texto', modo='libre', posicion='Dentro')
        self.page.evaluate('''()=>{
            const hijos=__disenoState.mocks.slice(1), origen={...hijos[0].libre};
            hijos.forEach(m=>m.libre={...origen}); editorPrueba.sync();
        }''')
        capa = tarjeta.evaluate('e=>getComputedStyle(e).zIndex')
        app = self.page.locator('.stApp').bounding_box()
        r = self.page.locator('.st-key-diseno_texto_2').bounding_box()
        punto = {'x':r['x']+30,'y':r['y']+8}
        self.pin('diseno_texto_2')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.orden_insertados(punto)[:3], ['diseno_texto_4','diseno_texto_2','diseno_texto_3'])
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).zIndex'), capa)
        self.assertEqual(self.page.locator('.stApp').bounding_box(), app)

    def test_exportar_pasos_de_capa_respeta_general_y_movil(self):
        for _ in range(3):
            self.insertar_tarjeta(modo=None)
        self.pin('diseno_tarjeta_1')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        general = self.page.evaluate('__disenoState.porKey.diseno_tarjeta_1.capa.nivel')
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        movil = self.page.evaluate('__disenoState.porKey.diseno_tarjeta_1.capa.nivel')
        self.assertNotEqual(general, movil)
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        for nombre, nivel in [('General', general), ('Móvil', movil)]:
            seccion = entrega.split('\n## ' + nombre + '\n', 1)[1].split('\n## ', 1)[0]
            bloque = re.search(r'\n### diseno_tarjeta_1\n(.*?)(?=\n### |\Z)', seccion, re.S).group(1)
            self.assertEqual([int(v) for v in re.findall(r'z-index:\s*(-?\d+)', bloque)], [nivel])

    def test_exportar_conserva_capas_de_insertados_de_otra_variante_no_visible(self):
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.insertar_tarjeta(modo=None)
        self.insertar_tarjeta(modo=None)
        self.pin('diseno_tarjeta_1')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        nivel = self.page.evaluate('__disenoState.porKey.diseno_tarjeta_1.capa.nivel')
        self.page.get_by_label('Diseñar para', exact=True).select_option('general')
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 0)
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        seccion = entrega.split('\n## Móvil\n', 1)[1]
        bloque = re.search(r'\n### diseno_tarjeta_1\n(.*?)(?=\n### |\Z)', seccion, re.S).group(1)
        capa = json.loads(re.search(r'Orden de capas propuesto: (.+)', bloque).group(1))
        self.assertEqual(capa['nivel'], nivel)
        self.assertIn('directamente en el lienzo', seccion)

    def test_capa_de_rama_sin_clase_de_autor_se_repone_y_conserva_original(self):
        self.page.locator('.fila').evaluate('''e=>{
            const padre=document.createElement('div'); padre.dataset.testid='stLayoutWrapper';
            e.before(padre); padre.appendChild(e);
        }''')
        html = self.page.locator('[data-testid=stLayoutWrapper]').evaluate('e=>e.outerHTML')
        tarjeta = self.insertar_tarjeta(modo=None)
        self.page.evaluate('''()=>{
            const r=document.querySelector('.st-key-a').getBoundingClientRect();
            const base=document.querySelector('main').getBoundingClientRect();
            __disenoState.mocks[0].libre={x:r.left-base.left,y:r.top-base.top}; editorPrueba.sync();
        }''')
        r = self.page.locator('.st-key-a').bounding_box()
        punto = {'x':r['x']+30,'y':r['y']+30}
        for _ in range(3):
            self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'st-key-a')
        self.page.locator('[data-testid=stLayoutWrapper]').evaluate('(e,s)=>e.outerHTML=s', html)
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(self.clase_en_punto(punto), 'st-key-a')
        self.assertEqual(tarjeta.count(), 1)
        self.page.get_by_role('button', name='Ver original', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-mock-titulo')
        self.assertTrue(self.page.get_by_role('button', name='Bajar una capa', exact=True).is_disabled())
        self.page.get_by_role('button', name='Ver con cambios', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'st-key-a')
        self.assertTrue(self.page.get_by_role('button', name='Subir una capa', exact=True).is_enabled())

    def test_pasos_de_capa_respetan_el_orden_visual_de_un_flex(self):
        self.page.locator('.fila').evaluate('''e=>{
            e.style.gap='0'; e.style.paddingLeft='180px';
            for(const [key, orden] of [['a',2],['b',0],['c',1]]) {
                const n=e.querySelector('.st-key-'+key);
                n.style.margin='0 0 0 -180px'; n.style.order=String(orden);
            }
        }''')
        cajas = [self.page.locator('.st-key-' + k).bounding_box() for k in ['a','b','c']]
        punto = {'x':cajas[0]['x']+40,'y':cajas[0]['y']+40}
        self.pin('b')
        self.assertEqual(self.clase_en_punto(punto), 'st-key-a')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'st-key-a')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'st-key-b')
        self.assertEqual([self.page.locator('.st-key-' + k).bounding_box() for k in ['a','b','c']], cajas)

    def test_pasos_y_extremos_siguen_funcionando_entre_tarjeta_y_control_real(self):
        self.montar_zona_interna()
        self.page.locator('.dv-zona').evaluate('''e=>{
            const n=document.createElement('button'); n.className='dv-control'; n.textContent='Control real';
            n.style.cssText='display:block;width:220px;height:32px;margin-top:8px'; e.appendChild(n);
        }''')
        self.page.get_by_role('button', name='+ Insertar', exact=True).click()
        self.page.get_by_label('Destino al insertar', exact=True).select_option('lienzo')
        self.insertar_tarjeta(modo=None)
        r = self.page.locator('.dv-control').bounding_box()
        self.page.evaluate('''r=>{
            const b=document.querySelector('main').getBoundingClientRect();
            __disenoState.mocks[0].libre={x:r.x-b.left,y:r.y-b.top}; editorPrueba.sync();
        }''', r)
        punto = {'x':r['x']+20,'y':r['y']+16}
        self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-mock-titulo')
        self.pin('piece', 'dv-control')
        self.page.get_by_role('button', name='Traer al frente', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-control')
        self.pin('diseno_tarjeta_1')
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-mock-titulo')
        self.pin('piece', 'dv-control')
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-mock-titulo')

    def test_un_paso_de_tarjeta_sobre_cierre_descubre_un_control_sin_saltar_el_reporte(self):
        self.montar_cierre()
        self.page.locator('.st-key-piece').evaluate("e=>e.style.isolation='isolate'")
        self.page.get_by_role('button', name='+ Insertar', exact=True).click()
        self.page.get_by_label('Destino al insertar', exact=True).select_option('lienzo')
        tarjeta = self.insertar_tarjeta(modo=None)
        self.page.locator('.ajc-acciones').evaluate('''e=>{
            const a=e.getBoundingClientRect(), base=document.querySelector('main').getBoundingClientRect();
            const m=__disenoState.mocks[0]; m.libre={x:a.left-base.left,y:a.top-base.top};
            const r=__disenoState.porKey[m.key]; r.cambios.width=a.width+'px'; r.cambios.height=a.height+'px';
            r.cambios.padding='0'; r.cambios.overflow='hidden'; editorPrueba.sync();
        }''')
        caja = tarjeta.bounding_box()
        originales = self.page.locator('.ajc-acciones > *').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().toJSON())')

        def cubiertos():
            return self.page.locator('.ajc-acciones').evaluate('''e=>Array.from(e.children)
                .filter(n=>!n.hasAttribute('data-diseno-capas')).map(n=>{
                    const r=n.getBoundingClientRect(), raiz=n.getRootNode();
                    const encima=raiz.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
                    return !!encima?.closest('[data-diseno-mock]');
                })''')

        self.assertEqual(cubiertos(), [True]*4)
        for paso in range(1, 5):
            self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
            self.assertEqual(cubiertos().count(False), paso)
            self.assertEqual(tarjeta.bounding_box(), caja)
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(cubiertos().count(False), 3)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(cubiertos().count(False), 4)
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(cubiertos().count(False), 3)
        self.assertEqual(self.page.locator('.ajc-acciones > :not([data-diseno-capas])').evaluate_all(
            'es=>es.map(e=>e.getBoundingClientRect().toJSON())'), originales)

    def montar_controles_superpuestos_por_tarjeta(self, contenido=False):
        self.page.locator('.st-key-piece').evaluate('''(e, contenido)=>{
            e.style.cssText='width:620px;height:150px;position:relative;isolation:isolate;'
                +(contenido?'contain:paint;transform:translate(20px,10px);':'');
            e.attachShadow({mode:'open'}).innerHTML='<section class="dv-fila" style="display:flex;gap:8px;padding:16px;background:#eee">'
                +['Uno','Dos','Tres'].map((s,i)=>'<button class="dv-b'+i+'" style="width:70px;height:32px">'+s+'</button>').join('')+'</section>';
        }''', contenido)
        tarjeta = self.insertar_tarjeta(modo=None)
        self.page.locator('.dv-b0').evaluate('''e=>{
            const a=e.getBoundingClientRect(), base=document.querySelector('main').getBoundingClientRect();
            const m=__disenoState.mocks[0]; m.libre={x:a.left-base.left,y:a.top-base.top};
            const r=__disenoState.porKey[m.key]; r.cambios.width='226px'; r.cambios.height='32px';
            r.cambios.padding='0'; r.cambios.overflow='hidden'; r.cambios['margin-left']='-15px';
            r.transformState.translateX=15; editorPrueba.sync();
        }''')
        return tarjeta

    def controles_descubiertos(self):
        return self.page.locator('.dv-fila').evaluate('''e=>Array.from(e.querySelectorAll('button')).filter(n=>{
            const r=n.getBoundingClientRect(), raiz=n.getRootNode();
            return !raiz.elementFromPoint(r.left+r.width/2,r.top+r.height/2)?.closest('[data-diseno-mock]');
        }).length''')

    def test_capas_locales_conservan_coordenadas_en_host_con_contain_y_transform(self):
        tarjeta = self.montar_controles_superpuestos_por_tarjeta(contenido=True)
        caja = tarjeta.bounding_box()
        originales = self.page.locator('.dv-fila button').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().toJSON())')
        self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.assertEqual(self.controles_descubiertos(), 1)
        self.assertEqual(tarjeta.bounding_box(), caja)
        self.page.get_by_role('button', name='Vista previa', exact=True).click()
        marco = self.page.get_by_title('Vista previa del diseño').element_handle().content_frame()
        self.assertEqual(marco.locator('.st-key-diseno_tarjeta_1').evaluate('e=>e.getBoundingClientRect().toJSON()'),
            tarjeta.evaluate('e=>e.getBoundingClientRect().toJSON()'))
        self.page.get_by_role('button', name='Cerrar vista previa', exact=True).click()
        self.assertEqual(self.page.locator('.dv-fila button').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().toJSON())'), originales)

    def test_capas_locales_se_reponen_con_la_pieza_y_conservan_original_y_entrega(self):
        tarjeta = self.montar_controles_superpuestos_por_tarjeta()
        html = self.page.locator('.st-key-piece').evaluate('e=>e.shadowRoot.innerHTML')
        caja = tarjeta.bounding_box()
        self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.page.evaluate('__inspectorTogglePin(true)')
        tarjeta.click(button='right', position={'x':30,'y':25})
        self.page.wait_for_function("__inspectorPinned && __inspectorUltimo.key==='diseno_tarjeta_1' && !__disenoState.sub")
        self.page.evaluate("__inspectorTipVisible(document.getElementById('el-inspector-tip'),false)")
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('Ámbito visual de capas:', entrega)
        self.assertIn('dv-fila', entrega)
        self.assertIn('Va en el .css de la PIEZA', entrega)
        self.page.locator('.st-key-piece').evaluate('(e,s)=>e.shadowRoot.innerHTML=s', html)
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(self.controles_descubiertos(), 1)
        self.assertEqual(tarjeta.count(), 1)
        self.assertEqual(tarjeta.bounding_box(), caja)
        self.page.get_by_role('button', name='Ver original', exact=True).click()
        self.assertEqual(self.controles_descubiertos(), 0)
        original = tarjeta.bounding_box()
        self.assertEqual((original['x'], original['y']), (caja['x'], caja['y']))
        self.page.get_by_role('button', name='Ver con cambios', exact=True).click()
        self.assertEqual(self.controles_descubiertos(), 1)
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.assertEqual(self.controles_descubiertos(), 1)
        self.page.get_by_role('button', name='Traer al frente', exact=True).click()
        self.assertEqual(self.controles_descubiertos(), 0)
        self.assertEqual(tarjeta.evaluate('e=>e.parentElement.id'), 'diseno-insertados-libres')
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertEqual(self.controles_descubiertos(), 2)

    def test_al_mover_tarjeta_a_otros_controles_el_paso_usa_el_nuevo_grupo(self):
        tarjeta = self.montar_controles_superpuestos_por_tarjeta()
        self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertTrue(self.page.get_by_role('button', name='Subir una capa', exact=True).is_disabled())
        self.page.locator('.dv-fila').evaluate('''e=>{
            const otra=e.cloneNode(true); otra.className='dv-otra-fila';
            otra.querySelectorAll('[data-diseno-capas]').forEach(n=>n.remove()); e.after(otra);
        }''')
        origen = tarjeta.bounding_box()
        destino = self.page.locator('.dv-otra-fila button').first.bounding_box()
        agarre = self.page.locator('#el-diseno-mover').bounding_box()
        x, y = agarre['x']+12, agarre['y']+12
        self.page.mouse.move(x,y)
        self.page.mouse.down()
        self.page.mouse.move(x,y+destino['y']-origen['y'],steps=5)
        self.page.mouse.up()
        caja = tarjeta.bounding_box()
        self.assertTrue(self.page.get_by_role('button', name='Subir una capa', exact=True).is_enabled())
        self.page.get_by_role('button', name='Subir una capa', exact=True).click()
        self.assertTrue(tarjeta.evaluate("e=>e.parentElement.parentElement.classList.contains('dv-otra-fila')"))
        self.assertEqual(tarjeta.bounding_box(), caja)
        self.assertEqual(self.page.locator('.dv-otra-fila').evaluate('''e=>Array.from(e.querySelectorAll('button')).filter(n=>{
            const r=n.getBoundingClientRect();return !n.getRootNode().elementFromPoint(r.left+r.width/2,r.top+r.height/2)?.closest('[data-diseno-mock]');
        }).length'''), 2)

    def test_exportar_capas_conserva_posicion_de_lienzo_libre_y_flujo_por_variante(self):
        self.insertar_tarjeta(modo=None)
        self.page.get_by_role('button', name='Bajar una capa', exact=True).click()
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.page.get_by_label('Distribución del insertado', exact=True).select_option('flujo')
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        for nombre, posicion in [('General','fixed'),('Móvil','relative')]:
            seccion = entrega.split('\n## ' + nombre + '\n', 1)[1].split('\n## ', 1)[0]
            bloque = re.search(r'\n### diseno_tarjeta_1\n(.*?)(?=\n### |\Z)', seccion, re.S).group(1)
            self.assertIn('position: ' + posicion, bloque)

    def test_tarjeta_libre_se_envia_detras_de_imagenes_formas_y_controles_reales(self):
        from io import BytesIO
        from PIL import Image

        self.montar_zona_interna()
        self.page.locator('main').evaluate("e=>e.style.background='#a0a0a0'")
        self.page.locator('.dv-zona').evaluate('''e=>{
            const fila=document.createElement('div');
            fila.style.cssText='display:flex;gap:8px;margin-top:8px';
            fila.innerHTML='<button class="dv-control" style="width:50px;height:32px">Real</button>'
                +'<img class="dv-imagen" width="50" height="32" alt="Imagen de prueba">'
                +'<div class="dv-forma" style="width:50px;height:32px;background:#d05040"></div>';
            fila.querySelector('img').src='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="50" height="32"><rect width="50" height="32" fill="#00aa44"/></svg>');
            e.appendChild(fila);
        }''')
        tarjeta = self.insertar_tarjeta(modo=None)
        self.seleccionar_insertado(tarjeta)
        caja = tarjeta.bounding_box()
        puntos = {c: {'x': caja['x'] + x, 'y': caja['y'] + 16}
            for c, x in [('dv-control', 25), ('dv-imagen', 83), ('dv-forma', 141)]}
        self.assertTrue(all(self.clase_en_punto(p) == 'dv-mock-titulo' for p in puntos.values()))
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        for clase, punto in puntos.items():
            self.assertEqual(self.clase_en_punto(punto), clase)
        self.assertEqual(tarjeta.bounding_box(), caja)
        # La parte sin vecinos sigue pintada sobre el fondo gris del lienzo.
        pixel = self.page.screenshot(clip={'x': caja['x'] + 220, 'y': caja['y'] + 24, 'width': 1, 'height': 1})
        self.assertEqual(Image.open(BytesIO(pixel)).getpixel((0, 0))[:3], (255, 255, 255))
        css = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('z-index: -', css)
        self.assertIn('isolation: isolate', css)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.clase_en_punto(puntos['dv-imagen']), 'dv-mock-titulo')
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(self.clase_en_punto(puntos['dv-imagen']), 'dv-imagen')
        self.page.get_by_role('button', name='Ver original', exact=True).click()
        self.assertEqual(self.clase_en_punto(puntos['dv-imagen']), 'dv-mock-titulo')
        self.assertEqual(tarjeta.bounding_box(), caja)
        self.page.get_by_role('button', name='Ver con cambios', exact=True).click()
        self.assertEqual(self.clase_en_punto(puntos['dv-imagen']), 'dv-imagen')
        tarjeta.evaluate('e=>e.remove()')
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(tarjeta.count(), 1)
        self.assertEqual(self.clase_en_punto(puntos['dv-imagen']), 'dv-imagen')
        bloque = self.page.evaluate('''()=>editorPrueba.construirBloqueCSS('diseno_tarjeta_1',
            document.querySelector('.st-key-diseno_tarjeta_1'),editorPrueba.registroPara('diseno_tarjeta_1'),'',null)''')
        self.assertIn('[data-testid="stMainBlockContainer"]', bloque)
        self.page.get_by_role('button', name='Ver original', exact=True).click()
        self.assertEqual(self.clase_en_punto(puntos['dv-imagen']), 'dv-mock-titulo')
        self.page.add_style_tag(content=bloque)
        self.assertEqual(self.clase_en_punto(puntos['dv-imagen']), 'dv-imagen')
        pixel = self.page.screenshot(clip={'x': caja['x'] + 220, 'y': caja['y'] + 24, 'width': 1, 'height': 1})
        self.assertEqual(Image.open(BytesIO(pixel)).getpixel((0, 0))[:3], (255, 255, 255))

    def test_tarjeta_libre_se_envia_detras_del_fechador_real_sin_mover_la_cabecera(self):
        corte = self.montar_cierre()
        self.page.keyboard.press('Alt+t')
        self.pin('piece', 'ajc-fnav')
        tarjeta = self.insertar_tarjeta(modo=None, posicion='Dentro')
        self.seleccionar_insertado(tarjeta)
        t, r = tarjeta.bounding_box(), corte.bounding_box()
        for etiqueta, valor in [('Desplazamiento X (px)', r['x'] - t['x']), ('Desplazamiento Y (px)', r['y'] - t['y'])]:
            campo = self.page.get_by_label(etiqueta, exact=True)
            campo.fill(str(round(valor))); campo.press('Tab')
        punto = {'x': r['x'] + 15, 'y': r['y'] + 16}
        geometria = [self.page.locator(s).bounding_box() for s in ['.ajc-fnav', '.ajc-cuerpo']]
        self.assertEqual(self.clase_en_punto(punto), 'dv-mock-titulo')
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        self.assertIn('ajc-selector-corte', self.clase_en_punto(punto))
        self.assertEqual([self.page.locator(s).bounding_box() for s in ['.ajc-fnav', '.ajc-cuerpo']], geometria)
        self.page.get_by_role('button', name='Traer al frente', exact=True).click()
        self.assertEqual(self.clase_en_punto(punto), 'dv-mock-titulo')

    def test_libre_por_defecto_no_empuja_la_cabecera_real_ni_crea_scroll(self):
        self.montar_cierre()
        cabecera = self.page.locator('.ajc-fnav')
        cuerpo = self.page.locator('.ajc-cuerpo')
        antes = [e.bounding_box() for e in [cabecera, cuerpo]]
        scroll = self.page.evaluate('[scrollX,scrollY,document.documentElement.scrollWidth,document.documentElement.scrollHeight]')
        self.pin('piece', 'ajc-fnav')
        tarjeta = self.insertar_tarjeta(modo=None, posicion='Dentro')
        self.assertEqual(tarjeta.get_attribute('data-diseno-distribucion'), 'libre')
        self.assertEqual([e.bounding_box() for e in [cabecera, cuerpo]], antes)
        self.assertEqual(self.page.evaluate('[scrollX,scrollY,document.documentElement.scrollWidth,document.documentElement.scrollHeight]'), scroll)
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).position'), 'fixed')
        self.assertEqual(tarjeta.evaluate('e=>e.parentElement.id'), 'diseno-insertados-libres')
        self.seleccionar_insertado(tarjeta)
        distribucion = self.page.get_by_label('Distribución del insertado', exact=True)
        self.assertLess(distribucion.bounding_box()['y'], self.page.viewport_size['height'])
        distribucion.select_option('flujo')
        self.assertGreater(cabecera.bounding_box()['height'], antes[0]['height'])
        self.assertGreater(cuerpo.bounding_box()['y'], antes[1]['y'])
        self.page.get_by_label('Distribución del insertado', exact=True).select_option('libre')
        self.assertEqual([e.bounding_box() for e in [cabecera, cuerpo]], antes)

    def test_dentro_de_tarjeta_libre_el_contenido_es_en_flujo_y_solo_crece_la_tarjeta(self):
        self.montar_zona_interna()
        tarjeta = self.insertar_tarjeta(modo=None)
        antes_app = self.page.locator('.stApp').bounding_box()
        alto = tarjeta.bounding_box()['height']
        self.seleccionar_insertado(tarjeta)
        texto = self.insertar_mock('Texto', modo=None, posicion='Dentro')
        self.assertEqual(texto.get_attribute('data-diseno-distribucion'), 'flujo')
        self.assertEqual(texto.evaluate('e=>e.parentElement.className'), 'st-key-diseno_tarjeta_1')
        self.assertGreater(tarjeta.bounding_box()['height'], alto)
        self.assertEqual(self.page.locator('.stApp').bounding_box(), antes_app)
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('Distribución: Libre', entrega)
        self.assertIn('Distribución: En flujo', entrega)
        self.assertIn('Anclaje relativo:', entrega)
        self.assertNotIn('diseno-insertados-libres', entrega)
        self.seleccionar_insertado(tarjeta)
        self.page.get_by_label('Distribución del insertado', exact=True).select_option('flujo')
        self.assertEqual(texto.evaluate('e=>e.parentElement.className'), 'st-key-diseno_tarjeta_1')
        self.page.get_by_label('Distribución del insertado', exact=True).select_option('libre')
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 2)
        self.assertEqual(texto.evaluate('e=>e.parentElement.className'), 'st-key-diseno_tarjeta_1')
        self.assertEqual(self.page.locator('.stApp').bounding_box(), antes_app)

    def test_libre_dentro_de_tarjeta_sigue_a_su_padre_y_sus_capas_no_mueven_la_tarjeta(self):
        self.montar_zona_interna()
        tarjeta = self.insertar_tarjeta(modo=None)
        self.seleccionar_insertado(tarjeta)
        texto = self.insertar_mock('Texto', modo='libre', posicion='Dentro')
        self.assertEqual(texto.evaluate('e=>e.parentElement.className'), 'st-key-diseno_tarjeta_1')
        self.assertEqual(texto.evaluate('e=>getComputedStyle(e).position'), 'absolute')
        posicion = texto.bounding_box()
        capa = tarjeta.evaluate('e=>getComputedStyle(e).zIndex')
        self.seleccionar_insertado(texto)
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).zIndex'), capa)
        self.seleccionar_insertado(tarjeta)
        campo = self.page.get_by_label('Desplazamiento X (px)', exact=True)
        campo.fill('40'); campo.press('Tab')
        self.assertAlmostEqual(texto.bounding_box()['x'], posicion['x'] + 40, delta=1)
        self.page.get_by_label('Distribución del insertado', exact=True).select_option('flujo')
        self.assertEqual(texto.evaluate('e=>getComputedStyle(e).position'), 'fixed')
        self.page.get_by_label('Distribución del insertado', exact=True).select_option('libre')
        self.assertEqual(texto.evaluate('e=>e.parentElement.className'), 'st-key-diseno_tarjeta_1')
        self.assertEqual(texto.evaluate('e=>getComputedStyle(e).position'), 'absolute')

    def test_convertir_distribucion_conserva_ajustes_e_historial(self):
        self.montar_zona_interna()
        alto_inicial = self.page.locator('.dv-zona').bounding_box()['height']
        tarjeta = self.insertar_tarjeta()
        self.seleccionar_insertado(tarjeta)
        for etiqueta, valor in [('Ancho (px)', '300'), ('Desplazamiento X (px)', '18')]:
            campo = self.page.get_by_label(etiqueta, exact=True)
            campo.fill(valor); campo.press('Tab')
        fila = self.page.get_by_text('Fondo', exact=True).locator('xpath=../../..')
        fila.locator('xpath=ancestor::details[1]/summary').click()
        fila.get_by_title('Acento', exact=True).click()
        posicion = tarjeta.bounding_box()
        self.page.get_by_label('Distribución del insertado', exact=True).select_option('libre')
        self.assertEqual(tarjeta.get_attribute('data-diseno-distribucion'), 'libre')
        self.assertEqual(tarjeta.bounding_box()['width'], 300)
        self.assertAlmostEqual(tarjeta.bounding_box()['x'], posicion['x'], delta=1)
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(108, 92, 231)')
        self.assertEqual(self.page.locator('.dv-zona').bounding_box()['height'], alto_inicial)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(tarjeta.get_attribute('data-diseno-distribucion'), 'flujo')
        self.assertEqual(tarjeta.bounding_box()['width'], 300)
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        self.assertEqual(tarjeta.get_attribute('data-diseno-distribucion'), 'libre')
        self.assertEqual(tarjeta.bounding_box()['width'], 300)
        self.page.get_by_role('button', name='Ver original', exact=True).click()
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(255, 255, 255)')
        self.page.get_by_role('button', name='Ver con cambios', exact=True).click()
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(108, 92, 231)')

    def test_libre_sigue_el_ancla_y_se_repone_sin_duplicados(self):
        self.montar_zona_interna()
        tarjeta = self.insertar_tarjeta(modo=None)
        antes = tarjeta.bounding_box()
        self.page.locator('.st-key-piece').evaluate('e=>e.style.marginTop="25px"')
        self.page.evaluate('editorPrueba.sync()')
        self.assertAlmostEqual(tarjeta.bounding_box()['y'], antes['y'] + 25, delta=1)
        self.page.locator('.dv-ancla').evaluate('e=>e.remove()')
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(tarjeta.count(), 0)
        self.page.locator('.dv-zona').evaluate('e=>e.innerHTML=\'<div class="dv-ancla" style="width:220px;height:32px">Ancla nueva</div>\'')
        self.page.evaluate('editorPrueba.sync()')
        self.assertEqual(tarjeta.count(), 1)
        self.assertEqual(self.page.evaluate('__disenoState.mocks.length'), 1)

    def test_capas_de_libres_no_cambian_distribucion_ni_tapan_todos_los_insertados(self):
        self.montar_zona_interna()
        primera = self.insertar_tarjeta(modo=None)
        segunda = self.insertar_tarjeta(modo=None)
        self.seleccionar_insertado(segunda)
        for etiqueta in ['Desplazamiento X (px)', 'Desplazamiento Y (px)']:
            campo = self.page.get_by_label(etiqueta, exact=True)
            campo.fill('-12'); campo.press('Tab')
        punto = primera.bounding_box()
        punto = {'x': punto['x']+40, 'y': punto['y']+35}
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        self.assertEqual(self.page.evaluate("p=>document.elementFromPoint(p.x,p.y).closest('[data-diseno-mock]').className", punto), 'st-key-diseno_tarjeta_1')
        self.page.get_by_role('button', name='Traer al frente', exact=True).click()
        self.assertEqual(self.page.evaluate("p=>document.elementFromPoint(p.x,p.y).closest('[data-diseno-mock]').className", punto), 'st-key-diseno_tarjeta_2')
        self.assertEqual(segunda.get_attribute('data-diseno-distribucion'), 'libre')

    def test_vista_previa_reubica_libres_en_movil_y_no_ejecuta_scripts(self):
        self.montar_zona_interna()
        self.insertar_tarjeta(modo=None)
        self.page.get_by_label('Diseñar para', exact=True).select_option('movil')
        self.page.get_by_role('button', name='Vista previa', exact=True).click()
        marco = self.page.get_by_title('Vista previa del diseño').element_handle().content_frame()
        tarjeta = marco.locator('.st-key-diseno_tarjeta_1')
        caja = tarjeta.bounding_box()
        self.assertEqual(marco.locator('script').count(), 0)
        self.assertEqual(marco.evaluate('innerWidth'), 390)
        self.assertGreaterEqual(tarjeta.evaluate('e=>e.getBoundingClientRect().left'), 0)
        self.assertLessEqual(tarjeta.evaluate('e=>e.getBoundingClientRect().right'), 390)
        self.assertGreater(caja['width'], 0)

    def test_control_real_puede_traerse_al_frente_de_una_tarjeta_libre(self):
        self.montar_zona_interna()
        self.page.locator('.dv-zona').evaluate('''e=>{
            const control=document.createElement('button'); control.className='dv-control';
            control.style.cssText='display:block;width:220px;height:32px;margin-top:8px';
            control.textContent='Control real'; e.appendChild(control);
        }''')
        tarjeta = self.insertar_tarjeta(modo=None)
        caja = tarjeta.bounding_box()
        punto = {'x': caja['x'] + 30, 'y': caja['y'] + 15}
        self.assertTrue(self.page.evaluate("p=>!!document.elementFromPoint(p.x,p.y).closest('[data-diseno-mock]')", punto))
        self.pin('piece', 'dv-control')
        self.page.get_by_role('button', name='Traer al frente', exact=True).click()
        self.assertTrue(self.page.evaluate("p=>!!document.elementFromPoint(p.x,p.y).closest('.st-key-piece')", punto))
        self.page.get_by_role('button', name='Enviar al fondo', exact=True).click()
        self.assertTrue(self.page.evaluate("p=>!!document.elementFromPoint(p.x,p.y).closest('[data-diseno-mock]')", punto))
        self.assertEqual(tarjeta.get_attribute('data-diseno-distribucion'), 'libre')

    def test_modelos_anteriores_sin_modo_siguen_en_flujo(self):
        self.montar_zona_interna()
        self.page.evaluate("()=>{__disenoState.mocks.push({key:'diseno_tarjeta_vieja',tipo:'tarjeta',anclaKey:'piece',anclaSub:'dv-ancla',posicion:'despues',texto:'Vieja'});editorPrueba.sync()}")
        vieja = self.page.locator('.st-key-diseno_tarjeta_vieja')
        self.assertEqual(vieja.get_attribute('data-diseno-distribucion'), 'flujo')
        self.assertTrue(vieja.evaluate('e=>e.getRootNode() instanceof ShadowRoot'))

    def test_quitar_tarjeta_con_contenido_no_deja_insertados_huerfanos_y_se_puede_deshacer(self):
        self.montar_zona_interna()
        tarjeta = self.insertar_tarjeta(modo=None)
        self.seleccionar_insertado(tarjeta)
        self.insertar_mock('Texto', modo=None, posicion='Dentro')
        self.seleccionar_insertado(tarjeta)
        quitar = self.page.get_by_role('button', name='Quitar este', exact=True, include_hidden=True)
        if not quitar.is_visible():
            quitar.locator('xpath=ancestor::details[1]/summary').click()
        quitar.click()
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 0)
        self.assertEqual(self.page.evaluate('__disenoState.mocks.length'), 0)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(self.page.locator('[data-diseno-mock]').count(), 2)
        self.assertEqual(self.page.locator('.st-key-diseno_texto_2').evaluate('e=>e.parentElement.className'), 'st-key-diseno_tarjeta_1')

    def test_dentro_se_deshabilita_en_un_selector_nativo(self):
        corte = self.montar_cierre()
        corte.click(button='right')
        self.page.wait_for_function("__disenoState.sub?.clase==='ajc-selector-corte'")
        boton = self.page.get_by_role('button', name='+ Tarjeta', exact=True, include_hidden=True)
        boton.locator('xpath=ancestor::details[1]/summary').click()
        self.assertTrue(self.page.get_by_role('button', name='Dentro', exact=True).is_disabled())
        opciones = corte.locator('option').count()
        tarjeta = self.insertar_tarjeta(modo=None)
        self.assertEqual(tarjeta.get_attribute('data-diseno-distribucion'), 'libre')
        self.assertEqual(corte.locator('option').count(), opciones)

    def test_tarjeta_insertada_en_pieza_se_selecciona_con_un_clic_derecho_y_se_edita(self):
        self.montar_zona_interna()
        tarjeta = self.insertar_tarjeta()
        tarjeta.click(button='right', position={'x': 5, 'y': 5})
        self.page.wait_for_function("__inspectorPinned && __inspectorUltimo.key==='diseno_tarjeta_1' && document.getElementById('el-diseno-panel').dataset.builtForKey==='diseno_tarjeta_1'", timeout=5000)
        self.assertEqual(self.page.evaluate('__inspectorUltimo.ctx.padre'), 'piece')
        self.assertEqual(self.page.evaluate('__inspectorUltimo.extras2.keysCad'), ['diseno_tarjeta_1', 'piece'])
        self.assertIn('Widget key: diseno_tarjeta_1', self.page.evaluate('textoCopiadoPrueba'))
        ancho_ancla = self.page.locator('.dv-ancla').bounding_box()['width']
        self.page.get_by_label('Ancho (px)', exact=True).fill('300')
        self.page.get_by_label('Ancho (px)', exact=True).press('Tab')
        self.assertEqual(tarjeta.bounding_box()['width'], 300)
        self.assertEqual(self.page.locator('.dv-ancla').bounding_box()['width'], ancho_ancla)
        fila = self.page.get_by_text('Fondo', exact=True).locator('xpath=../../..')
        fila.locator('xpath=ancestor::details[1]/summary').click()
        fila.get_by_title('Acento', exact=True).click()
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(108, 92, 231)')
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(255, 255, 255)')
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('Destino: CSS de la pieza', entrega)
        css = '\n'.join(re.findall(r'```css\n(.*?)\n```', entrega, re.S))
        tarjeta.evaluate('e=>e.style.removeProperty("background-color")')
        self.page.locator('.st-key-piece').evaluate('''(e,css)=>{
            const st=document.createElement('style'); st.textContent=css; e.shadowRoot.appendChild(st);
        }''', css)
        self.assertEqual(tarjeta.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(108, 92, 231)')

    def test_cambiar_de_tarjeta_a_su_titulo_y_al_ancla_y_soltar_el_mismo_nodo(self):
        self.montar_zona_interna()
        tarjeta = self.insertar_tarjeta()
        tarjeta.click(button='right', position={'x': 5, 'y': 5})
        self.page.wait_for_function("__inspectorPinned && __inspectorUltimo.key==='diseno_tarjeta_1'", timeout=5000)
        tarjeta.locator('.dv-mock-titulo').click(button='right')
        self.page.wait_for_function("__inspectorPinned && __inspectorUltimo.key==='diseno_tarjeta_1' && __disenoState.sub?.clase==='dv-mock-titulo'", timeout=5000)
        self.page.locator('.dv-ancla').click(button='right')
        self.page.wait_for_function("__inspectorPinned && __inspectorUltimo.key==='piece' && __disenoState.sub?.clase==='dv-ancla'", timeout=5000)
        self.page.locator('.dv-ancla').click(button='right')
        self.assertFalse(self.page.evaluate('__inspectorPinned'))

    def test_tarjetas_encadenadas_en_shadow_root_no_se_duplican_y_recuperan_seleccion(self):
        self.montar_zona_interna()
        primera = self.insertar_tarjeta()
        primera.click(button='right', position={'x': 5, 'y': 5})
        self.page.wait_for_function("__inspectorPinned && __inspectorUltimo.key==='diseno_tarjeta_1' && document.getElementById('el-diseno-panel').dataset.builtForKey==='diseno_tarjeta_1'", timeout=5000)
        segunda = self.insertar_tarjeta()
        self.page.evaluate('()=>{for(let i=0;i<4;i++)editorPrueba.sync()}')
        self.assertEqual(self.page.locator('[data-diseno-mock=tarjeta]').count(), 2)
        segunda.click(button='right', position={'x': 5, 'y': 5})
        self.page.wait_for_function("__inspectorPinned && __inspectorUltimo.key==='diseno_tarjeta_2' && document.getElementById('el-diseno-panel').dataset.builtForKey==='diseno_tarjeta_2'", timeout=5000)
        self.page.get_by_label('Ancho (px)', exact=True).fill('280')
        self.page.get_by_label('Ancho (px)', exact=True).press('Tab')
        self.assertEqual(segunda.bounding_box()['width'], 280)
        self.page.locator('.dv-zona').evaluate('e=>e.innerHTML=\'<div class="dv-ancla" style="width:220px;height:32px">Ancla redibujada</div>\'')
        self.page.wait_for_function("document.querySelector('.st-key-piece').shadowRoot.querySelectorAll('[data-diseno-mock=tarjeta]').length===2 && getComputedStyle(document.querySelector('.st-key-piece').shadowRoot.querySelector('.st-key-diseno_tarjeta_2')).width==='280px'")
        self.assertEqual(self.page.locator('.st-key-diseno_tarjeta_2').bounding_box()['width'], 280)
        self.assertEqual(self.page.evaluate('__inspectorUltimo.key'), 'diseno_tarjeta_2')
        self.assertEqual(self.page.locator('.st-key-diseno_tarjeta_2').evaluate('e=>e.previousElementSibling.className'), 'st-key-diseno_tarjeta_1')

    def test_titulo_de_tarjeta_exporta_css_limitado_a_esa_tarjeta(self):
        self.montar_zona_interna()
        primera = self.insertar_tarjeta()
        primera.click(button='right', position={'x': 5, 'y': 5})
        self.page.wait_for_function("document.getElementById('el-diseno-panel').dataset.builtForKey==='diseno_tarjeta_1'")
        segunda = self.insertar_tarjeta()
        titulo = self.page.locator('.st-key-diseno_tarjeta_1 .dv-mock-titulo')
        vecino = segunda.locator('.dv-mock-titulo')
        original_vecino = vecino.evaluate('e=>getComputedStyle(e).color')
        titulo.click(button='right')
        self.page.wait_for_function("__inspectorPinned && document.getElementById('el-diseno-panel').dataset.builtForKey==='diseno_tarjeta_1 .dv-mock-titulo'")
        fila = self.page.get_by_text('Texto', exact=True).locator('xpath=../../..')
        fila.locator('xpath=ancestor::details[1]/summary').click()
        fila.get_by_title('Acento', exact=True).click()
        self.assertEqual(titulo.evaluate('e=>getComputedStyle(e).color'), 'rgb(108, 92, 231)')
        self.assertEqual(vecino.evaluate('e=>getComputedStyle(e).color'), original_vecino)
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        css = '\n'.join(re.findall(r'```css\n(.*?)\n```', entrega, re.S))
        self.assertIn('.st-key-diseno_tarjeta_1 .dv-mock-titulo', css)
        titulo.evaluate('e=>e.style.removeProperty("color")')
        self.page.locator('.st-key-piece').evaluate('''(e,css)=>{
            const st=document.createElement('style'); st.textContent=css; e.shadowRoot.appendChild(st);
        }''', css)
        self.assertEqual(titulo.evaluate('e=>getComputedStyle(e).color'), 'rgb(108, 92, 231)')
        self.assertEqual(vecino.evaluate('e=>getComputedStyle(e).color'), original_vecino)

    def test_corte_real_se_selecciona_y_su_fondo_se_exporta_sin_pintar_la_caja(self):
        corte = self.montar_cierre()
        padre = self.page.locator('.ajc-ses')
        buscador = self.page.locator('.ajc-search')
        fondo = corte.evaluate('e=>getComputedStyle(e).backgroundColor')
        vecinos = [e.evaluate('n=>getComputedStyle(n).backgroundColor') for e in [padre, buscador]]
        corte.click(button='right')
        self.page.wait_for_function("__disenoState.sub?.clase==='ajc-selector-corte'")
        caja = corte.bounding_box()
        contorno = self.page.locator('#el-diseno-overlay').bounding_box()
        self.assertAlmostEqual(contorno['width'], caja['width'] + 8, delta=1)
        self.assertAlmostEqual(contorno['height'], caja['height'] + 8, delta=1)
        fila = self.page.get_by_text('Fondo', exact=True).locator('xpath=../../..')
        fila.locator('xpath=ancestor::details[1]/summary').click()
        fila.get_by_title('Acento', exact=True).click()
        self.assertEqual(corte.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(108, 92, 231)')
        self.assertEqual([e.evaluate('n=>getComputedStyle(n).backgroundColor') for e in [padre, buscador]], vecinos)
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        self.assertEqual(corte.evaluate('e=>getComputedStyle(e).backgroundColor'), fondo)
        self.page.get_by_role('button', name='Rehacer', exact=True).click()
        entrega = self.page.evaluate('editorPrueba.exportarEdicion()')
        self.assertIn('CSS de la pieza', entrega)
        css = '\n'.join(re.findall(r'```css\n(.*?)\n```', entrega, re.S))
        self.assertIn('.ajc-selector-corte', css)
        corte.evaluate('e=>e.style.cssText=""')
        self.page.locator('.st-key-piece').evaluate('''(e, css)=>{
            const estilo=document.createElement('style'); estilo.textContent=css;
            e.shadowRoot.appendChild(estilo);
        }''', css)
        self.assertEqual(corte.evaluate('e=>getComputedStyle(e).backgroundColor'), 'rgb(108, 92, 231)')
        self.assertEqual([e.evaluate('n=>getComputedStyle(n).backgroundColor') for e in [padre, buscador]], vecinos)

    def test_corte_real_conserva_pin_tras_redibujar_y_sigue_filtrando_al_salir_de_diseno(self):
        corte = self.montar_cierre()
        corte.click(button='right')
        self.page.wait_for_function("__disenoState.sub?.clase==='ajc-selector-corte'")
        fila = self.page.get_by_text('Fondo', exact=True).locator('xpath=../../..')
        fila.locator('xpath=ancestor::details[1]/summary').click()
        fila.get_by_title('Acento', exact=True).click()
        corte.evaluate('e=>{window.corteAnteriorPrueba=e; __ajCierreUI.pintar(__ajCierre)}')
        self.page.wait_for_function("!corteAnteriorPrueba.isConnected && getComputedStyle(__ajCierre.root.querySelector('select[data-change=corte]')).backgroundColor==='rgb(108, 92, 231)'")
        self.page.get_by_role('button', name=re.compile('Diseño$')).click()
        valor = corte.input_value()
        otro = next(v for v in corte.locator('option').evaluate_all('es=>es.map(e=>e.value)') if v != valor)
        corte.select_option(otro)
        self.assertEqual(self.page.evaluate('__ajCierre.st.c'), int(otro))
        self.assertEqual(corte.input_value(), otro)

    def test_barra_arrastrable_y_plegable_conserva_diseno_activo(self):
        antes = self.page.locator('#herr-barra').bounding_box()
        self.mover_barra(300, 200)
        despues = self.page.locator('#herr-barra').bounding_box()
        self.assertAlmostEqual(despues['x'], 300, delta=1)
        self.assertAlmostEqual(despues['y'], 200, delta=1)
        self.page.get_by_role('button', name='Plegar herramientas', exact=True).click()
        plegada = self.page.locator('#herr-barra').bounding_box()
        self.assertLess(plegada['width'], antes['width'])
        self.assertEqual(self.page.locator('#herr-barra').get_attribute('data-plegada'), '1')
        self.assertIn('diseno=1', self.page.url)
        self.assertTrue(self.page.locator('#el-diseno-panel').is_visible())
        self.page.get_by_role('button', name='Abrir herramientas', exact=True).click()
        self.assertEqual(self.page.locator('#herr-barra').get_attribute('data-plegada'), '0')
        self.assertTrue(self.page.get_by_role('button', name=re.compile('Diseño$')).is_visible())
        self.assertEqual(self.page.evaluate('document.body.style.userSelect'), '')

    def test_posicion_y_plegado_sobreviven_a_reinyectar_el_script(self):
        self.mover_barra(250, 250)
        self.page.get_by_role('button', name='Plegar herramientas', exact=True).click()
        self.page.evaluate(self.herramientas)
        barra = self.page.locator('#herr-barra')
        self.assertEqual(barra.count(), 1)
        self.assertEqual(barra.get_attribute('data-plegada'), '1')
        self.assertAlmostEqual(barra.bounding_box()['x'], 250, delta=1)
        self.assertAlmostEqual(barra.bounding_box()['y'], 250, delta=1)
        self.mover_barra(400, 300)
        self.assertAlmostEqual(barra.bounding_box()['x'], 400, delta=1)
        self.assertEqual(self.page.evaluate('localStorage.length+sessionStorage.length'), 0)

    def test_barra_queda_dentro_de_la_ventana_al_reducirla(self):
        self.mover_barra(500, 800)
        self.page.set_viewport_size({'width': 390, 'height': 600})
        self.page.wait_for_function('''() => {
            const r=document.getElementById('herr-barra').getBoundingClientRect();
            return r.right<=innerWidth && r.bottom<=innerHeight && r.left>=0 && r.top>=0;
        }''')
        r = self.page.locator('#herr-barra').bounding_box()
        self.assertLessEqual(r['x'] + r['width'], 390)
        self.assertLessEqual(r['y'] + r['height'], 600)
        self.page.get_by_role('button', name='Panel a la izquierda', exact=True).click()
        self.page.wait_for_function('''() => {
            const r=document.getElementById('herr-barra').getBoundingClientRect();
            return r.right<=innerWidth && r.bottom<=innerHeight && r.left>=230 && r.top>=0;
        }''')

    def test_ayuda_integrada_no_deja_otra_leyenda_flotante(self):
        self.assertFalse(self.page.locator('#el-inspector-badge').is_visible())
        self.page.get_by_role('button', name='Atajos de herramientas', exact=True).click()
        self.assertIn('Alt+D', self.page.locator('[data-herr-ayuda]').inner_text())
        self.assertIn('Alt+T', self.page.locator('[data-herr-ayuda]').inner_text())
        self.page.evaluate(self.inspector)
        self.assertFalse(self.page.locator('#el-inspector-badge').is_visible())
        self.page.keyboard.press('Alt+t')
        self.assertFalse(self.page.locator('#el-inspector-badge').is_visible())

    def test_bloqueo_se_avisa_dentro_de_la_barra_y_desaparece(self):
        self.page.evaluate('__inspectorAlternarSilenciado()')
        self.page.locator('.st-key-a').click()
        estado = self.page.locator('#herr-barra [role="status"]')
        estado.wait_for(state='visible')
        self.assertTrue(estado.is_visible())
        self.assertIn('navegación bloqueada', estado.inner_text())
        self.assertEqual(self.page.locator('#el-diseno-aviso-bloqueo').count(), 0)
        self.page.evaluate('__herramientasUI.avisoHasta=0')
        self.page.wait_for_function("getComputedStyle(document.querySelector('#herr-barra [role=status]')).display==='none'")

    def test_aviso_no_abre_la_barra_plegada(self):
        self.page.get_by_role('button', name='Plegar herramientas', exact=True).click()
        self.page.evaluate('__inspectorAlternarSilenciado()')
        self.page.locator('.st-key-a').click()
        self.page.wait_for_function("document.querySelector('#herr-barra [role=status]').textContent==='🔒'")
        self.assertEqual(self.page.locator('#herr-barra').get_attribute('data-plegada'), '1')
        self.assertEqual(self.page.locator('#el-diseno-aviso-bloqueo').count(), 0)

    def test_panel_cambia_de_lado_y_sus_manijas_son_accesibles(self):
        self.pin('box')
        self.page.get_by_role('button', name='Panel a la izquierda', exact=True).click()
        panel = self.page.locator('#el-diseno-panel').bounding_box()
        self.assertEqual(panel['x'], 0)
        for selector in ['#el-diseno-mover', '#el-diseno-rh-w', '#el-diseno-rh-e', '#el-diseno-rh-se']:
            r = self.page.locator(selector).bounding_box()
            self.assertGreaterEqual(r['x'], panel['width'])
            self.assertLessEqual(r['x'] + r['width'], 1366)
        self.page.get_by_role('button', name='Panel a la derecha', exact=True).click()
        panel = self.page.locator('#el-diseno-panel').bounding_box()
        self.assertEqual(panel['x'] + panel['width'], 1366)
        self.assertEqual(self.page.evaluate('__disenoRuntime.historial.atras.length'), 0)

    def test_reserva_de_espacio_seguida_por_lado_y_restablecida_al_salir(self):
        self.page.get_by_role('button', name='Panel a la izquierda', exact=True).click()
        self.page.evaluate('__disenoState.empujarLienzo=true; editorPrueba.sync()')
        self.assertEqual(self.page.locator('.stApp').evaluate('e=>getComputedStyle(e).marginLeft'), '230px')
        self.page.get_by_role('button', name='Panel a la derecha', exact=True).click()
        self.assertEqual(self.page.locator('.stApp').evaluate('e=>getComputedStyle(e).marginLeft'), '0px')
        self.page.get_by_role('button', name=re.compile('Diseño$')).click()
        self.page.wait_for_function("document.getElementById('el-diseno-reserva').textContent===''")
        self.assertFalse(self.page.locator('#el-diseno-panel').is_visible())

    def test_plegar_panel_conserva_lado_y_ediciones(self):
        self.pin('a')
        self.page.get_by_label('Ancho (px)', exact=True).fill('240')
        self.page.get_by_label('Ancho (px)', exact=True).press('Tab')
        self.page.get_by_role('button', name='Panel a la izquierda', exact=True).click()
        self.page.get_by_role('button', name='Plegar panel', exact=True).click()
        self.assertTrue(self.page.evaluate('__disenoState.panelColapsado'))
        self.page.keyboard.press('Alt+d')
        self.assertEqual(self.page.locator('#el-diseno-panel').bounding_box()['x'], 0)
        self.assertEqual(self.page.locator('.st-key-a').bounding_box()['width'], 240)

    def test_flechas_en_agarre_mueven_barra_y_no_el_elemento(self):
        self.pin('a')
        self.mover_barra(300, 200)
        agarre = self.page.get_by_role('button', name='Mover herramientas', exact=True)
        agarre.focus()
        agarre.press('ArrowRight')
        self.assertAlmostEqual(self.page.locator('#herr-barra').bounding_box()['x'], 310, delta=1)
        self.assertEqual(self.page.evaluate('__disenoState.porKey.a.transformState.translateX'), 0)

    def test_salir_y_volver_con_alt_i_conserva_la_barra(self):
        self.mover_barra(300, 200)
        self.page.keyboard.press('Alt+i')
        self.page.wait_for_function("!document.getElementById('herr-barra')")
        self.assertFalse(self.page.locator('#el-inspector-badge').is_visible())
        self.page.keyboard.press('Alt+i')
        self.page.wait_for_function("!!document.getElementById('herr-barra')")
        self.assertAlmostEqual(self.page.locator('#herr-barra').bounding_box()['x'], 300, delta=1)

    def test_arrastre_sigue_al_cruzar_un_iframe(self):
        self.page.evaluate('''() => {
            const f=document.createElement('iframe'); f.title='Tabla de ejemplo';
            f.style.cssText='position:fixed;left:200px;top:250px;width:600px;height:200px';
            f.srcdoc='<p>Contenido de la tabla</p>'; document.body.appendChild(f);
        }''')
        self.mover_barra(300, 300)
        r = self.page.locator('#herr-barra').bounding_box()
        self.assertAlmostEqual(r['x'], 300, delta=1)
        self.assertAlmostEqual(r['y'], 300, delta=1)
        self.assertEqual(self.page.evaluate('document.body.style.userSelect'), '')

    def test_barra_conserva_eventos_al_reemplazar_iframe_de_montaje(self):
        self.mover_barra(300, 200)
        for _ in range(2):
            self.page.locator('#montaje-herramientas').evaluate_all('es=>es.forEach(e=>e.remove())')
            frame = self.page.evaluate_handle('''() => {
                const f=document.createElement('iframe'); f.id='montaje-herramientas';
                f.style.display='none'; document.body.appendChild(f); return f;
            }''').as_element().content_frame()
            frame.evaluate(self.herramientas)
        self.mover_barra(400, 300)
        self.assertAlmostEqual(self.page.locator('#herr-barra').bounding_box()['x'], 400, delta=1)
        self.assertEqual(self.page.locator('#herr-barra').count(), 1)


if __name__ == '__main__':
    unittest.main()
