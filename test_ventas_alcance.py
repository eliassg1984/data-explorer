"""Ventas › el filtro «Venta» de cada tarjeta (regla #755).

Grupo y Sub Grupo dejaron el «Filtros» de la franja: cada tarjeta trae el
suyo (`graficos/ventas_alcance.py` + `.js`) y lo que se elige en una no toca
a las otras. Vigila:

  · los tres bloques (Carta, Eventos, Otros) y los cuatro atajos, con
    «como en Costos» = los grupos que suma ese reporte;
  · con qué abre cada tarjeta (Venta por Periodo: toda; Mix: Carta +
    Eventos) y que las dos piezas antepongan el módulo;
  · que la franja ya no filtre por grupo y que el enlace desde Costos
    escriba el filtro de la tarjeta a la que llega (antes escribía una
    clave que nadie leía);
  · en Chromium, la cuenta del módulo (marcar y desmarcar grupos,
    subgrupos y bloques, los atajos, otro rango) y «Venta por Periodo»
    montada de verdad: llega desde Costos filtrada, lo dice, y la ✕ vuelve
    a toda la venta.

Sin secrets ni red; la parte de Chromium se salta sin Playwright.

    python test_ventas_alcance.py
"""

import json
import unittest
from pathlib import Path

from graficos import ventas_alcance as va

_AQUI = Path(__file__).parent
_JS = (_AQUI / "graficos" / "ventas_alcance.js").read_text(encoding="utf-8")
_GRUPOS = ["Alimentos", "Bebidas c/ Alcohol", "Bebidas s/ Alcohol", "Bebidas Calientes",
           "Vinos y Espumantes", "Eventos", "Venta Interna", "Otros", "No Show", "Promociones"]


class LosBloques(unittest.TestCase):
    def test_cada_grupo_en_su_bloque(self):
        self.assertEqual(va.bloque("Eventos"), va.EVENTOS)
        for g in ("Venta Interna", "VENTA_INTERNA", "Otros", "No Show"):
            self.assertEqual(va.bloque(g), va.OTROS, g)
        # Un grupo que el POS estrene cae en la carta, que es lo probable.
        for g in ("Alimentos", "Vinos y Espumantes", "Promociones"):
            self.assertEqual(va.bloque(g), va.CARTA, g)

    def test_los_atajos(self):
        A = va.datos(_GRUPOS)
        self.assertEqual([b for b, _ in A["bloques"]], [va.CARTA, va.EVENTOS, va.OTROS])
        at = {n: (None if lista is None else sorted(x[0] for x in lista)) for n, lista in A["atajos"]}
        self.assertIsNone(at[va.TODA])
        carta = sorted(["Alimentos", "Bebidas c/ Alcohol", "Bebidas s/ Alcohol", "Bebidas Calientes",
                        "Vinos y Espumantes", "Promociones"])
        self.assertEqual(at[va.SOLO_CARTA], carta)
        self.assertEqual(at[va.CARTA_EVENTOS], sorted(carta + ["Eventos"]))
        # Como en Costos: sus cinco grupos de carta, Eventos y Venta interna;
        # ni Otros, ni No Show, ni un grupo que Costos no conoce.
        self.assertEqual(at[va.COMO_COSTOS], sorted(["Alimentos", "Bebidas c/ Alcohol", "Bebidas s/ Alcohol",
                                                     "Bebidas Calientes", "Vinos y Espumantes", "Eventos",
                                                     "Venta Interna"]))

    def test_abre_y_subgrupos(self):
        A = va.datos(["Alimentos", "Eventos", None, " "], subs={"Alimentos": ["Postres", "Fondos", None]},
                     abre=va.CARTA_EVENTOS)
        self.assertEqual(A["abre"], va.CARTA_EVENTOS)
        self.assertEqual(A["subs"], {"Alimentos": ["Fondos", "Postres"]})
        self.assertEqual(va.datos(["Alimentos"], abre="otro")["abre"], va.TODA)


class CadaTarjetaLoSuyo(unittest.TestCase):
    def test_el_mix_abre_en_carta_y_eventos_con_sus_subgrupos(self):
        from graficos import ventas_mix
        A = ventas_mix.alcance_mix([["Alimentos", "Postres", "Flan", "Cocina"],
                                    ["Alimentos", "Fondos", "Lomo", "Cocina"],
                                    ["Otros", "Descorche", "Descorche", "Bar"]])
        self.assertEqual(A["abre"], va.CARTA_EVENTOS)
        self.assertEqual(A["subs"]["Alimentos"], ["Fondos", "Postres"])

    def test_las_piezas_anteponen_el_modulo(self):
        for f in ("ventas_resumen.py", "ventas_mix.py"):
            src = (_AQUI / "graficos" / f).read_text(encoding="utf-8")
            self.assertIn("ventas_alcance.js()", src, f)
            self.assertIn("ventas_alcance.css()", src, f)
        src = (_AQUI / "graficos" / "ventas_resumen.py").read_text(encoding="utf-8")
        self.assertIn('ventas_alcance.datos(datos["grupos"], abre=ventas_alcance.TODA)', src)

    def test_la_franja_ya_no_filtra_por_grupo(self):
        src = (_AQUI / "graficos" / "ventas.py").read_text(encoding="utf-8")
        self.assertNotIn('"ventas_graf_filtro_fam", "Grupo"', src)
        self.assertNotIn('"ventas_graf_filtro_sub", "Sub Grupo"', src)

    def test_el_enlace_de_costos_escribe_el_filtro_de_la_tarjeta(self):
        from graficos import ventas_resumen
        src = (_AQUI / "costos_enlaces.py").read_text(encoding="utf-8")
        self.assertIn(f'st.session_state["{ventas_resumen.K_ALCANCE}"]', src)
        self.assertNotIn('st.session_state["vt_resumen_grupo"]', src)

    def test_ningun_color_suelto(self):
        css = (_AQUI / "graficos" / "ventas_alcance.css").read_text(encoding="utf-8")
        # Seis dígitos, como las otras piezas: «#755» es una regla.
        self.assertNotRegex(css + _JS, r"#[0-9a-fA-F]{6}\b")


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class EnElNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = _chromium()().start()
        try:
            cls.b = cls._pw.chromium.launch()
        except Exception as e:  # Chromium no instalado
            cls._pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {e}")

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls._pw.stop()

    def test_la_cuenta_del_modulo(self):
        A = va.datos(_GRUPOS, subs={"Alimentos": ["Entradas", "Fondos", "Postres"]}, abre=va.CARTA_EVENTOS)
        A2 = va.datos(_GRUPOS + ["Ceviches"], subs={"Alimentos": ["Entradas", "Fondos", "Postres"]},
                      abre=va.CARTA_EVENTOS)
        pg = self.b.new_page()
        pg.set_content("<p>")
        pg.add_script_tag(content=_JS)
        r = pg.evaluate("""([A, A2]) => {
          const VA = window.VentasAlcance, ui = VA.nuevaUi();
          const el = (o) => ({ dataset: o });
          const out = {};
          let s = VA.inicio(A);
          out.inicio = VA.etiqueta(A, s);
          out.pasaEvento = VA.pasa(s, 'Eventos'); out.pasaOtros = VA.pasa(s, 'Otros');
          out.postres = VA.pasa(s, 'Alimentos', 'Postres');
          // Sólo los postres: se desmarca la carta y se marca un subgrupo.
          s = VA.accion(A, s, ui, el({ va: 'bloque', b: 'Carta' }));
          s = VA.accion(A, s, ui, el({ va: 'grupo', g: 'Eventos' }));
          s = VA.accion(A, s, ui, el({ va: 'sub', g: 'Alimentos', s: 'Postres' }));
          out.soloPostres = VA.etiqueta(A, s);
          out.fondos = VA.pasa(s, 'Alimentos', 'Fondos');
          out.postres2 = VA.pasa(s, 'Alimentos', 'Postres');
          // Marcar los tres subgrupos es el grupo entero.
          s = VA.accion(A, s, ui, el({ va: 'sub', g: 'Alimentos', s: 'Fondos' }));
          s = VA.accion(A, s, ui, el({ va: 'sub', g: 'Alimentos', s: 'Entradas' }));
          out.alimentos = VA.etiqueta(A, s);
          // Todo marcado es toda la venta; la ✕ vuelve a como abre.
          s = VA.accion(A, s, ui, el({ va: 'atajo', n: 'Toda la venta' }));
          out.toda = s === null;
          out.listaToda = VA.listaGrupos(A, s);
          s = VA.accion(A, s, ui, el({ va: 'inicio' }));
          out.vuelve = VA.etiqueta(A, s);
          // Nada marcado no es «todo».
          let n = VA.accion(A, null, ui, el({ va: 'atajo', n: 'Sólo carta' }));
          n = VA.accion(A, n, ui, el({ va: 'bloque', b: 'Carta' }));
          out.nada = VA.etiqueta(A, n);
          out.listaNada = VA.listaGrupos(A, n);
          // Otro rango con un grupo nuevo de la carta: el atajo lo suma; una
          // elección a mano no.
          out.reubicado = VA.pasa(VA.reubicar(A, A2, VA.inicio(A)), 'Ceviches');
          out.aMano = VA.pasa(VA.reubicar(A, A2, { Alimentos: true }), 'Ceviches');
          // El botón dice lo elegido y abre el panel con los bloques.
          ui.abierto = true;
          const h = VA.html(A, VA.inicio(A), ui);
          out.boton = h.includes('Venta: Carta + Eventos') && h.includes('Carta + Eventos · al abrir') && h.includes('Sólo cambia esta tarjeta');
          out.sinX = !VA.html(A, VA.inicio(A), VA.nuevaUi()).includes('data-va="inicio"');
          return out;
        }""", [A, A2])
        pg.close()
        self.assertEqual(r["inicio"], va.CARTA_EVENTOS)
        self.assertTrue(r["pasaEvento"])
        self.assertFalse(r["pasaOtros"])
        self.assertTrue(r["postres"])
        self.assertEqual(r["soloPostres"], "Alimentos › Postres")
        self.assertFalse(r["fondos"])
        self.assertTrue(r["postres2"])
        self.assertEqual(r["alimentos"], "Alimentos")
        self.assertTrue(r["toda"])
        self.assertEqual(r["listaToda"], [])
        self.assertEqual(r["vuelve"], va.CARTA_EVENTOS)
        self.assertEqual(r["nada"], "nada")
        self.assertEqual(r["listaNada"], ["\u0000ninguno"])
        self.assertTrue(r["reubicado"])
        self.assertFalse(r["aMano"])
        self.assertTrue(r["boton"])
        self.assertTrue(r["sinX"])

    def test_venta_por_periodo_llega_desde_costos_y_vuelve(self):
        import test_ventas_periodo as tvp
        from graficos import ventas_resumen as vr
        _t, P = tvp._armar()
        P["alcance"] = va.datos(P["grupos"] + ["Eventos"], abre=va.TODA)
        P["alcance_pedido"] = {"lista": [["Bebidas"]], "sub": "Costo", "n": "costos-1"}
        js = (va.js() + (_AQUI / "graficos" / "_xlsx.js").read_text(encoding="utf-8")
              + (Path(vr.__file__).parent / "ventas_periodo.js").read_text(encoding="utf-8"))
        js = js.replace("export default function (component)", "window.__montar = function (component)")
        css = (_AQUI / "graficos" / "ventas_periodo.css").read_text(encoding="utf-8") + va.css()
        pg = self.b.new_page(viewport={"width": 1300, "height": 900})
        pg.set_content(f"<style>{css}</style><div id='r'></div>")
        pg.add_script_tag(content=js)
        r = pg.evaluate("""(P) => {
          const parent = document.getElementById('r');
          window.__montar({ data: P, parentElement: parent, setTriggerValue: () => {} });
          const raiz = parent.querySelector('.vp'), G = raiz.__vp, out = {};
          out.grupo = G.st.fil.grupo.slice(); out.sub = G.st.sub;
          out.chip = raiz.querySelector('.caja').textContent;
          out.boton = raiz.querySelector('.va-b').textContent;
          // La corrida siguiente trae el mismo pedido: no lo vuelve a aplicar.
          raiz.querySelector('[data-va="inicio"]').click();
          window.__montar({ data: Object.assign({}, P, { sello: P.sello }), parentElement: parent, setTriggerValue: () => {} });
          out.grupo2 = G.st.fil.grupo.slice();
          out.chip2 = raiz.querySelector('.caja').textContent;
          // Abrir el panel y elegir un atajo.
          raiz.querySelector('[data-va="toggle"]').click();
          out.panel = !!raiz.querySelector('.va-p');
          raiz.querySelector('[data-va="atajo"][data-n="Sólo carta"]').click();
          out.grupo3 = G.st.fil.grupo.slice().sort();
          // Un clic afuera cierra el panel.
          raiz.querySelector('.cab').click();
          out.cerrado = !raiz.querySelector('.va-p');
          return out;
        }""", P)
        pg.close()
        self.assertEqual(r["grupo"], ["Bebidas"])
        self.assertEqual(r["sub"], "Costo")
        self.assertIn("no es el total", r["chip"])
        self.assertIn("Venta: Bebidas", r["boton"])
        self.assertEqual(r["grupo2"], [])
        self.assertIn("Toda la venta", r["chip2"])
        self.assertTrue(r["panel"])
        self.assertEqual(r["grupo3"], sorted(g for g in P["grupos"] if g and va.bloque(g) == va.CARTA))
        self.assertTrue(r["cerrado"])
        json.dumps(r)


if __name__ == "__main__":
    unittest.main()
