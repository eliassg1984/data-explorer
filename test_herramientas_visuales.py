"""Barra y editor: apartar herramientas sin alterar la app ni perder el diseño."""
import ast
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

    def pin(self, key):
        self.page.evaluate('''k=>{
            __inspectorPinned=true; __inspectorUltimo={key:k}; __disenoState.sub=null;
            editorPrueba.sync();
        }''', key)

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

    def insertar_tarjeta(self):
        boton = self.page.get_by_role('button', name='+ Tarjeta', exact=True, include_hidden=True)
        if not boton.is_visible():
            boton.locator('xpath=ancestor::details[1]/summary').click()
        boton.click()
        return self.page.locator('[data-diseno-mock=tarjeta]').last

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
