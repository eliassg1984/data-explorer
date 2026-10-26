"""Regreso contextual: ida/vuelta, cadena, fechas, privacidad y navegador."""
import datetime as dt
from pathlib import Path
from unittest import TestCase, main, mock, skipIf

import navegacion_retorno as retorno

ROOT = Path(__file__).parent


class Estado(dict):
    def to_dict(self):
        return dict(self)

    def from_dict(self, v):
        self.clear()
        self.update(v)


class Viajes(TestCase):
    def setUp(self):
        self.ss = Estado(_retorno_actual="Ventas", vt_graf_tipo="Mix de carta",
                         filtro=["Salón"], rango=(dt.date(2026, 9, 1), dt.date(2026, 9, 30)))
        self.q = Estado(reporte="Ventas", vista="Mix de carta", debug="1")
        self.patches = [mock.patch.object(retorno.st, "session_state", self.ss),
                        mock.patch.object(retorno.st, "query_params", self.q),
                        mock.patch.object(retorno, "_efimeras", return_value={"boton", "pieza"}),
                        mock.patch("graficos.vistas_de", side_effect=lambda r: (
                            "vt_graf_tipo" if r == "Ventas" else "rec_graf_tipo", []))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        retorno._ENLACES.clear()

    def test_restaurar_fecha_filtros_y_borrar_semillas_del_destino(self):
        retorno.capturar_origen()
        self.ss.update(filtro=["Eventos"], semilla_destino="otro", rango=(dt.date(2026, 10, 1), dt.date(2026, 10, 5)))
        self.q.update(reporte="Recetas", concepto="c", desde_costos="1")
        retorno._volver()
        self.assertEqual(self.ss["filtro"], ["Salón"])
        self.assertEqual(self.ss["rango"], (dt.date(2026, 9, 1), dt.date(2026, 9, 30)))
        self.assertNotIn("semilla_destino", self.ss)
        self.assertEqual(self.ss["_nav_reporte"], "Ventas")
        self.assertEqual(self.q, {"reporte": "Ventas", "vista": "Mix de carta", "debug": "1"})
        self.assertEqual(self.ss["_retorno_comando"]["accion"], "restaurar")

    def test_varios_saltos_se_desandan_de_uno_en_uno(self):
        retorno.capturar_origen()
        self.ss.update(_retorno_actual="Recetas", rec_graf_tipo="Carta costeada")
        retorno.capturar_origen()
        self.ss["rec_graf_tipo"] = "Cambios en recetas base"
        retorno._volver()
        self.assertEqual(self.ss["_nav_reporte"], "Recetas")
        self.assertEqual(self.ss["rec_graf_tipo"], "Carta costeada")
        retorno._volver()
        self.assertEqual(self.ss["_nav_reporte"], "Ventas")
        self.assertEqual(self.ss["_retorno_pila"], [])

    def test_no_copia_datos_credenciales_ni_acciones(self):
        self.ss.update(api_key="privada", _ctx_ia={"filas": [1]}, boton=True,
                       pieza={"carta": {"cod": "01"}}, df=object(), enorme=list(range(900)))
        retorno.capturar_origen()
        estado = self.ss["_retorno_pila"][0]["estado"]
        for k in ("api_key", "_ctx_ia", "boton", "pieza", "df", "enorme"):
            self.assertNotIn(k, estado)
        self.ss["filtro"].append("otro")
        self.assertEqual(estado["filtro"], ["Salón"])

    def test_enlace_entre_pestanas_y_caducidad(self):
        token = retorno.enlace_desde_aqui()
        self.assertRegex(token, r"^[a-f0-9]{32}$")
        self.ss.clear()
        self.q.update(reporte="Compras", retorno=token)
        retorno.preparar("Compras")
        self.assertEqual(len(self.ss["_retorno_pila"]), 1)
        retorno.preparar("Compras")
        self.assertEqual(len(self.ss["_retorno_pila"]), 1)
        retorno._volver()
        self.assertEqual(self.ss["_nav_reporte"], "Ventas")
        self.assertEqual(self.ss["filtro"], ["Salón"])
        self.ss.clear()
        retorno._ENLACES[token]["creado"] -= retorno._TTL + 1
        retorno.preparar("Compras")
        self.assertNotIn("_retorno_pila", self.ss)

    def test_historial_acotado_y_token_invalido(self):
        for _ in range(18):
            retorno.capturar_origen()
        self.assertEqual(len(self.ss["_retorno_pila"]), 12)
        self.ss.clear()
        self.q["retorno"] = "<script>"
        retorno.preparar("Compras")
        self.assertNotIn("_retorno_pila", self.ss)
        retorno._volver()  # vacío no cambia ni la URL ni el reporte
        self.assertNotIn("_nav_reporte", self.ss)

    def test_contadores_de_llegada_no_retroceden(self):
        self.ss['_rec_cambios_n'] = 3
        retorno.capturar_origen()
        self.ss['_rec_cambios_n'] = 4
        retorno._volver()
        self.assertEqual(self.ss['_rec_cambios_n'], 4)

    def test_vuelta_no_repite_avisos_ni_pedidos(self):
        self.ss.update(_aviso_ingreso_enviado=False, sunat_lote_xml={'pedidos': []}, form_receta_guardada_sel=None)
        retorno.capturar_origen()
        self.ss.update(_aviso_ingreso_enviado=True, sunat_lote_xml={'pedidos': ['nuevo']}, form_receta_guardada_sel='guardada')
        retorno._volver()
        self.assertTrue(self.ss['_aviso_ingreso_enviado'])
        self.assertEqual(self.ss['sunat_lote_xml'], {'pedidos': ['nuevo']})
        self.assertEqual(self.ss['form_receta_guardada_sel'], 'guardada')


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@skipIf(sync_playwright is None, "sin Playwright")
class Navegador(TestCase):
    def setUp(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch()
        self.page = self.browser.new_page(viewport={"width": 1100, "height": 700})
        self.page.context.route("http://retorno.test/**", lambda route: route.fulfill(content_type="text/html", body="<main></main>"))
        self.page.goto("http://retorno.test/")
        self.page.add_script_tag(content=(ROOT / "navegacion_retorno.js").read_text(encoding="utf-8"))

    def tearDown(self):
        self.browser.close()
        self.pw.stop()

    def montar(self):
        self.page.evaluate("""() => {
          document.querySelector('main').innerHTML='<div class="st-key-fuente"><div id="host"></div></div>';
          const shadow=document.querySelector('#host').attachShadow({mode:'open'});
          window.render=c=>{
            let e=c.parentElement.querySelector('.pieza');
            if(!e){e=document.createElement('div');e.className='pieza';e.__d={st:{q:'elegido',sel:'003',grupos:new Set(['A'])}};c.parentElement.append(e)}
            e.innerHTML='<details><summary>Grupo</summary><p>Abierto</p></details><div class="tabla" style="overflow:auto;overscroll-behavior:contain;width:300px;height:180px"><table style="width:1000px">'+Array.from({length:90},(_,i)=>'<tr data-cod="'+i+'"><td style="height:30px">'+i+'</td><td><button data-acc="carta" data-id="'+i+'">Ver</button></td></tr>').join('')+'</table></div>';
          }; window.c={parentElement:shadow}; render(c);
        }""")

    def test_vuelta_con_estado_shadow_scroll_dos_ejes_foco_y_desplegable(self):
        self.montar()
        self.page.locator('details').evaluate("e=>e.open=true")
        self.page.locator('.tabla').evaluate("e=>{e.scrollTop=920;e.scrollLeft=240}")
        self.page.locator('tr[data-cod="31"] button').click()
        self.page.evaluate("window.__retorno.configurar({comando:{accion:'guardar',id:'paso'},activo:true})")
        self.page.evaluate("document.querySelector('main').replaceChildren()")
        self.page.evaluate("window.__retorno.restaurar('paso')")
        self.montar()
        self.page.evaluate("""() => {
          c.parentElement.querySelector('.pieza').__d.st.q='cambiado';
          window.__retorno.montar(c,render);
          window.__retorno.configurar({comando:{accion:'restaurar',id:'paso'},activo:false});
        }""")
        self.page.wait_for_function("document.querySelector('#host').shadowRoot.querySelector('.tabla').scrollLeft===240")
        self.page.wait_for_function("document.querySelector('#host').shadowRoot.querySelector('tr[data-cod=\"31\"] td:last-child').style.outline!==''")
        self.assertGreater(self.page.locator('.tabla').evaluate('e=>e.scrollTop'), 850)
        self.assertTrue(self.page.locator('details').evaluate('e=>e.open'))
        self.assertEqual(self.page.locator('.pieza').evaluate('e=>e.__d.st.q'), 'elegido')
        self.assertEqual(self.page.locator('.pieza').evaluate('e=>[...e.__d.st.grupos]'), ['A'])
        self.assertEqual(self.page.locator('tr[data-cod="31"] td').last.evaluate('e=>getComputedStyle(e).outlineColor'), 'rgb(144, 120, 186)')

    def test_enlace_nueva_pestana_y_datos_solo_ui(self):
        self.page.evaluate("""() => {
          document.querySelector('main').innerHTML='<a href="?reporte=Compras" target="_blank" rel="noopener noreferrer">Compras</a>';
          localStorage.setItem('api_key','secreto');localStorage.setItem('cc_est','{"canal":2}');
          window.__retorno.configurar({enlace:'123456789012345678901234567890ab',activo:false});
        }""")
        with self.page.expect_popup() as pop:
            self.page.locator('a').click()
        nueva = pop.value
        nueva.wait_for_load_state()
        self.assertIn('retorno=123456789012345678901234567890ab', nueva.url)
        nueva.add_script_tag(content=(ROOT / 'navegacion_retorno.js').read_text(encoding='utf-8'))
        snap = nueva.evaluate("window.__retorno.leer('123456789012345678901234567890ab')")
        self.assertEqual(snap['local'], {'cc_est': '{"canal":2}'})
        self.assertEqual(self.page.locator('a').get_attribute('target'), '_blank')
        self.assertEqual(self.page.locator('a').get_attribute('rel'), 'noopener noreferrer')

    def test_boton_conserva_estilos_del_montaje_y_no_duplica_eventos(self):
        self.page.set_viewport_size({'width':390,'height':844})
        self.page.evaluate("css=>document.querySelector('main').innerHTML='<style>'+css+'</style>'",retorno._CSS_BOTON)
        self.page.add_script_tag(content=retorno._JS_BOTON.replace('export default function', 'window.boton=function'))
        self.page.evaluate("""() => {
          window.n=0;window.comp={parentElement:document.querySelector('main'),data:{id:'x',nombre:'Origen'},setTriggerValue:()=>n++};
          boton(comp);boton(comp);
        }""")
        b=self.page.get_by_role('button',name='← Volver a Origen',exact=True)
        self.assertEqual(b.count(),1)
        self.assertEqual(b.evaluate('e=>getComputedStyle(e).color'),'rgb(89, 75, 134)')
        self.assertGreaterEqual(b.bounding_box()['height'],44)
        b.click()
        self.assertEqual(self.page.evaluate('n'),1)

    def test_reinyectar_tras_rerun_conserva_estado_y_reenlaza_clics(self):
        js=(ROOT/'navegacion_retorno.js').read_text(encoding='utf-8')
        # El mismo mecanismo que st.iframe: sus callbacks deben sobrevivir
        # a que Streamlit retire el iframe anterior y dibuje el siguiente.
        self.page.evaluate('window.__retorno.desenlazar();delete window.__retorno')
        self.page.evaluate("""js=>new Promise(resolve=>{const f=document.createElement('iframe');f.id='inyeccion';f.onload=resolve;f.srcdoc='<script>'+js+'</scr'+'ipt>';document.body.append(f)})""",js)
        self.page.evaluate("""()=>{document.querySelector('#inyeccion').remove();document.querySelector('main').innerHTML='<a href="?reporte=Compras" target="_blank">Ir</a>';window.__retorno.configurar({enlace:'123456789012345678901234567890ab'})}""")
        self.page.evaluate("""js=>new Promise(resolve=>{const f=document.createElement('iframe');f.id='inyeccion';f.onload=resolve;f.srcdoc='<script>'+js+'</scr'+'ipt>';document.body.append(f)})""",js)
        with self.page.expect_popup() as pop:
            self.page.locator('a').click()
        pop.value.wait_for_load_state()
        self.assertIsNotNone(self.page.evaluate("window.__retorno.leer('123456789012345678901234567890ab')"))

    def test_identifica_la_celda_por_codigo_al_cambiar_el_orden(self):
        self.montar()
        self.page.locator('tr[data-cod="31"] button').click()
        self.page.evaluate("window.__retorno.configurar({comando:{accion:'guardar',id:'orden'},activo:true})")
        self.page.evaluate("window.__retorno.restaurar('orden')")
        self.montar()
        self.page.evaluate("""() => {
          const tb=c.parentElement.querySelector('tbody');tb.append(...[...tb.children].reverse());
          window.__retorno.configurar({comando:{accion:'restaurar',id:'orden'},activo:false});
        }""")
        self.page.wait_for_function("document.querySelector('#host').shadowRoot.querySelector('tr[data-cod=\"31\"] td:last-child').style.outline!==''")
        self.assertFalse(self.page.locator('tr[data-cod="58"] td').last.evaluate('e=>!!e.style.outline'))

    def test_espera_tandas_antes_de_reponer_una_celda_lejana(self):
        self.montar()
        self.page.evaluate("""() => {
          window.lote=(n)=>{const tb=c.parentElement.querySelector('tbody');tb.innerHTML=Array.from({length:n},(_,i)=>'<tr data-cod="'+i+'"><td style="height:30px">'+i+'</td><td><button data-acc="carta">Ver</button></td></tr>').join('')};lote(600);
        }""")
        self.page.locator('tr[data-cod="400"] button').click()
        self.page.evaluate("window.__retorno.configurar({comando:{accion:'guardar',id:'tandas'},activo:true})")
        self.page.evaluate("window.__retorno.restaurar('tandas')")
        self.montar()
        self.page.evaluate("""() => {
          let limite=150;lote(limite);
          c.parentElement.querySelector('.tabla').addEventListener('scroll',()=>{if(limite<600){limite+=150;lote(limite)}});
          window.__retorno.configurar({comando:{accion:'restaurar',id:'tandas'},activo:false});
        }""")
        try:
            self.page.wait_for_function("document.querySelector('#host').shadowRoot.querySelector('tr[data-cod=\"400\"] td:last-child')?.style.outline",timeout=10000)
        except Exception as exc:
            info=self.page.evaluate("""() => {const r=document.querySelector('#host').shadowRoot;return {snap:__retorno.leer('tandas'),filas:r.querySelectorAll('tr').length,y:r.querySelector('.tabla').scrollTop}}""")
            raise AssertionError(info) from exc
        self.assertGreater(self.page.locator('.tabla').evaluate('e=>e.scrollTop'),10000)


if __name__ == '__main__':
    main(verbosity=2)
