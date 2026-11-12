"""Ruta integrada: destinos reales, grupos, memoria y teclado, sin red."""
import html
import re
import unittest

import data
import estilos
import navegacion as nav
from streamlit.testing.v1 import AppTest


APP = '''
from unittest.mock import patch
import streamlit as st
import data
import estilos
import navegacion as nav
st.set_page_config(layout="wide")
estilos.inject_css()
if st.session_state.get("_nav_reporte"):
    st.session_state["qa_reporte"] = st.session_state.pop("_nav_reporte")
reporte = st.session_state.get("qa_reporte", "Inventario Valorizado")
with patch.object(nav, "_formatear_kpis", return_value=None), \\
     patch.object(nav, "_kpis_franja", return_value=None), \\
     patch.object(nav, "boton_refresco"):
    nav.inject_navegacion(data.REPORTES, reporte)
'''

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


class Rotulos(unittest.TestCase):
    def test_un_reporte_no_dibuja_un_selector_de_grupo_vacio(self):
        markup = nav._html_barra_contexto("Ventas", "payments", ("", "Mix"),
                                         menu_compacto=True)
        self.assertNotIn('data-franja-abrir="secciones"', markup)
        self.assertIn('data-franja-abrir="vistas"', markup)

    def test_compras_usa_el_nombre_como_selector_sin_repetirlo(self):
        markup = nav._html_barra_contexto("Compras", "shopping_cart",
                                         ("Compras", "Período"), menu_compacto=True)
        self.assertEqual(re.sub("<[^>]+>", " ", markup).count("Compras"), 1)
        self.assertIn('data-franja-abrir="secciones"', markup)
        self.assertIn('data-franja-abrir="vistas"', markup)


class Renderizados(unittest.TestCase):
    def test_reportes_reales_y_callbacks_nativos(self):
        app = AppTest.from_string(APP, default_timeout=30)
        for reporte in data.REPORTES:
            par = nav._vistas_de(reporte)
            if not par:
                continue
            with self.subTest(reporte=reporte):
                app.session_state["qa_reporte"] = reporte
                app.run()
                self.assertEqual(list(app.exception), [])
                key, vistas = par
                destino = vistas[-1][0]
                app.button(key=nav.claves_vista(reporte, destino)[0]).click().run()
                self.assertEqual(list(app.exception), [])
                self.assertEqual(app.session_state[key], destino)
                self.assertEqual(app.session_state["qa_reporte"], reporte)


@unittest.skipIf(sync_playwright is None, "sin Playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()
        cls.page = cls.browser.new_page(viewport={"width": 1100, "height": 720})
        cls.page.set_default_timeout(10000)
        cls.page.route("**/*", lambda route: route.abort())
        cls.errors = []
        cls.page.on("pageerror", lambda e: cls.errors.append(str(e)))

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def montar(self, reporte):
        """DOM de los botones de Streamlit, con los IDs y menús de producción."""
        self.page.goto("about:blank")
        info = data.REPORTES[reporte]
        area = info.get("area")
        miembros = nav._areas_de(data.REPORTES).get(area, [reporte])
        miembros = [m for m in miembros if nav._vistas_de(m)]
        nombre = area or info.get("label_largo") or reporte
        vistas = nav._vistas_de(reporte)[1]

        def rotulo(m):
            cfg = data.REPORTES[m]
            return cfg.get("label_rail") or cfg.get("label_corto") or m

        grupo = rotulo(reporte) if len(miembros) > 1 else ""
        actual = nav.ROTULO_PESTANA.get((reporte, vistas[0][0]), vistas[0][1])
        cabecera = nav._html_barra_contexto(nombre, info.get("icono"),
                                          (grupo, actual), menu_compacto=True)
        menus = []
        if len(miembros) > 1:
            opciones = "".join(
                f'<button class="franja-seccion" data-grupo="{html.escape(rotulo(m))}">'
                f'{html.escape(rotulo(m))}</button>' for m in miembros)
            menus.append('<div class="st-key-nav_franja_secciones">'
                         '<div data-testid="stMarkdown"><div style="display:flex">'
                         '<div data-testid="stMarkdownContainer">'
                         f'<div class="franja-secciones">{opciones}</div>'
                         '</div></div></div></div>')
        for i, m in enumerate(miembros):
            vs = nav._vistas_de(m)[1]
            ruta = rotulo(m) if len(miembros) > 1 else ""
            activo = " franja-activo" if m == reporte else ""
            menus.append(f'<div class="st-key-nav_franja_g{i}">'
                         f'<span class="franja-miembro{activo}" data-ruta="{html.escape(ruta)}" '
                         f'data-reporte="{html.escape(m)}" '
                         f'data-franja-destino="{nav.claves_vista(m, vs[0][0])[0]}"></span>')
            for oid, label, *_ in vs:
                key = nav.claves_vista(m, oid)[0]
                label = nav.ROTULO_PESTANA.get((m, oid), label)
                selected = ' class="vista-en-pantalla"' if m == reporte and oid == vs[0][0] else ""
                menus.append(f'<div class="st-key-{key}"><div data-testid="stButton">'
                             f'<button{selected} data-vista="{html.escape(oid)}" '
                             f'data-reporte="{html.escape(m)}"><p>{html.escape(label)}</p>'
                             '</button></div></div>')
            menus.append('</div>')
        css = re.sub(r"</?style[^>]*>", "", estilos.get_css())
        self.page.set_content(
            f'<style>{css}</style><style>'
            '.st-key-nav_franja_rep{position:relative!important;left:0!important;'
            'top:0!important;width:100%!important;height:48px!important;'
            'display:flex!important;align-items:center!important;overflow:visible!important}'
            '.fuera{margin-top:400px;min-height:40px}'
            '</style><div class="st-key-nav_franja_rep">' + cabecera
            + '<div class="st-key-nav_franja_idx">' + "".join(menus)
            + '</div></div><div class="fuera">Contenido del reporte</div>',
            wait_until="domcontentloaded")
        script = re.search(r"<script>([\s\S]*)</script>", nav._script_capas()).group(1)
        self.page.add_script_tag(content=script)
        self.page.evaluate("""() => {
          window.elegidas = [];
          document.addEventListener('click', e => {
            const b = e.target.closest('button[data-vista]');
            if (b) window.elegidas.push([b.dataset.reporte, b.dataset.vista]);
          });
        }""")
        return vistas

    def test_todos_los_reportes_muestran_sus_vistas(self):
        """#851: las vistas del reporte en pantalla están a la vista en la barra, sin
        abrir nada; la elegida en pastilla índigo. El menú de vistas ya no se ve."""
        for reporte in data.REPORTES:
            if not nav._vistas_de(reporte):
                continue
            with self.subTest(reporte=reporte):
                vistas = self.montar(reporte)
                self.assertFalse(self.page.locator('[data-franja-abrir="vistas"]').is_visible())
                visibles = self.page.locator('.st-key-nav_franja_idx button[data-vista]:visible')
                self.assertEqual(visibles.all_text_contents(), [
                    nav.ROTULO_PESTANA.get((reporte, v[0]), v[1]) for v in vistas])
                cajas = [b.bounding_box() for b in visibles.all()]
                for r in cajas:
                    self.assertGreaterEqual(r['x'], 0)
                    self.assertLessEqual(r['x'] + r['width'], 1100)
                # En una fila.
                self.assertLessEqual(max(r['y'] for r in cajas) - min(r['y'] for r in cajas), 1)
                elegida = self.page.locator('.st-key-nav_franja_idx button.vista-en-pantalla')
                self.assertEqual(elegida.evaluate("e=>getComputedStyle(e).backgroundColor"), "rgb(73, 56, 184)")
        self.assertEqual(self.errors, [])

    def test_grupo_recupera_la_vista_navegada_sin_rerun(self):
        self.montar("Inventario Valorizado")
        key = nav.claves_vista("Ajuste de Inventario", "Evolución del ajuste")[0]
        self.page.evaluate("k=>window.__franjaUltimas={'Ajuste de Inventario':k}", key)
        self.page.locator('[data-franja-abrir="secciones"]').click()
        # El panel lleva su relleno (#851): la opción ocupa el ancho de su lista.
        ancho = self.page.locator('.franja-secciones').bounding_box()['width']
        opcion = self.page.locator('.franja-seccion[data-grupo="Ajuste"]')
        self.assertAlmostEqual(opcion.bounding_box()['width'], ancho, delta=1)
        opcion.click()
        self.assertEqual(self.page.evaluate("window.elegidas"),
                         [["Ajuste de Inventario", "Evolución del ajuste"]])
        self.assertIsNone(self.page.locator('html').get_attribute('data-franja-menu'))

    def test_teclado_escape_clic_fuera(self):
        """#851: las vistas se recorren con las flechas a los costados; el menú de
        reportes abre con flecha abajo y se cierra con Escape o con un clic afuera."""
        self.montar("Ventas")
        vs = nav._vistas_de("Ventas")[1]
        activa = "document.activeElement.dataset.vista"
        self.page.locator('.st-key-nav_franja_idx button[data-vista]').first.focus()
        self.page.keyboard.press("ArrowRight")
        self.assertEqual(self.page.evaluate(activa), vs[1][0])
        self.page.keyboard.press("ArrowLeft")
        self.assertEqual(self.page.evaluate(activa), vs[0][0])
        self.assertIsNone(self.page.locator('html').get_attribute('data-franja-menu'))
        self.montar("Inventario Valorizado")
        trigger = self.page.locator('[data-franja-abrir="secciones"]')
        trigger.focus()
        self.page.keyboard.press("ArrowDown")
        self.assertEqual(self.page.locator('html').get_attribute('data-franja-menu'), "ruta-secciones")
        self.assertTrue(self.page.evaluate("document.activeElement.classList.contains('franja-seccion')"))
        # Abrir el menú no mueve las vistas (#465).
        self.assertTrue(self.page.locator('.st-key-nav_franja_idx button[data-vista]').first.is_visible())
        self.page.keyboard.press("Escape")
        self.assertEqual(trigger.get_attribute("aria-expanded"), "false")
        self.assertTrue(trigger.evaluate("e=>document.activeElement===e"))
        trigger.click()
        self.page.locator('.fuera').click()
        self.assertIsNone(self.page.locator('html').get_attribute('data-franja-menu'))
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
