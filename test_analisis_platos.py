"""Ventas › «Análisis de platos» como pieza propia (regla #699): lo que
recibe el navegador y que rehaga las cuentas de `ventas_platos.py` igual.
Sin secrets ni red."""
import unittest
from pathlib import Path

import pandas as pd

from graficos import ventas_platos as vp


def periodo(filas, dias):
    a = pd.DataFrame(filas, columns=["prod", "grupo", "sub", "venta", "cant", "costo", "neto"])
    return a.assign(pedidos=float("nan")), dias


class LoQueRecibeLaPieza(unittest.TestCase):
    def setUp(self):
        self.datos = {
            "ago": periodo([["Lomo", "Alimentos", "Fondos", 3100.0, 31.0, 900.0, 2500.0],
                            ["Pisco", "Bebidas", "Cocteles", 620.0, 31.0, 50.0, 500.0]], 31),
            "oct": periodo([["Lomo", "Alimentos", "Parrilla", 2100.0, 21.0, 600.0, 1700.0],
                            ["Ceviche", "Alimentos", "Entradas", 400.0, 8.0, 120.0, 320.0]], 21),
        }
        self.d = vp.armar_ranking(self.datos, ["ago", "oct"], {"ago": "Ago 26", "oct": "Oct 26"},
                                  foco="Lomo", codigos={"lomo": "0000959"})
        self.p = {x[0]: x for x in self.d["platos"]}

    def test_una_posicion_por_periodo(self):
        self.assertEqual(self.p["Lomo"][3:7], [[3100.0, 2100.0], [31.0, 21.0], [900.0, 600.0], [2500.0, 1700.0]])
        self.assertEqual(self.p["Pisco"][3], [620.0, 0.0])
        self.assertEqual(self.p["Ceviche"][3], [0.0, 400.0])

    def test_grupo_y_subgrupo_del_periodo_mas_nuevo(self):
        self.assertEqual(self.p["Lomo"][1:3], ["Alimentos", "Parrilla"])

    def test_codigo_para_saltar_a_costo_de_carta(self):
        self.assertEqual((self.p["Lomo"][7], self.p["Pisco"][7]), ("0000959", ""))

    def test_periodos_y_reglas(self):
        self.assertEqual(self.d["periodos"], [{"etq": "Ago 26", "dias": 31}, {"etq": "Oct 26", "dias": 21}])
        self.assertEqual(self.d["umbrales"], [45.0, 70.0])
        self.assertEqual((self.d["salto"], self.d["tope"], self.d["foco"]), (vp._SALTO, vp._TOPE_GRAFICO, "Lomo"))

    def test_el_js_hace_las_cuentas_de_python(self):
        js = Path(vp.__file__).with_suffix(".js").read_text(encoding="utf-8")
        # Puestos: los empatados se quedan con el puesto más alto.
        self.assertIn("x === v[i - 1][1] ? out.get(v[i - 1][0]) : i + 1", js)
        # Movimiento: verde o rojo desde `salto` puestos, como `movimiento`.
        self.assertIn("dd >= d.salto ? 'sube' : 'igual'", js)
        # Variación POR DÍA con venta, como `var_por_dia`.
        self.assertIn("const a = d0 ? v0 / d0 : 0, b = d1 ? v1 / d1 : 0;", js)
        self.assertIn("return a ? (b - a) / a : null;", js)
        # El % de costo es costo ÷ neto, sin número sin costo (`pct_costo`).
        self.assertIn("costo > 0 && neto > 0.5 ? costo / neto * 100 : null", js)
        self.assertEqual(vp.var_por_dia(3100.0, 31, 2100.0, 21), 0.0)


class IngenieriaDeMenu(unittest.TestCase):
    """La Ingeniería de menú en la pieza (regla #700): la cuenta sigue en
    `ventas_menu.clasificar` y la pieza recibe cada plato ya clasificado."""

    def test_lo_que_recibe(self):
        from graficos import ventas_menu as vm
        a = pd.DataFrame({
            "prod": ["Lomo", "Pato", "Sopa", "Agua"], "grupo": ["Alimentos"] * 4,
            "sub": ["Fondos"] * 4, "venta": [0.0] * 4, "cant": [100.0, 10.0, 80.0, 5.0],
            "costo": [2000.0, 100.0, 1500.0, 0.0], "neto": [6000.0, 900.0, 2000.0, 50.0],
            "pedidos": [90.0, 10.0, 70.0, 5.0]})
        m, fuera, res = vm.clasificar(a, [("Alimentos", "Fondos")])
        d = vm.armar_menu(m, fuera, res, {"Lomo": "caballo"}, "Oct 26", "Sep 26", 21)
        p = {x[0]: x for x in d["platos"]}
        self.assertEqual(set(p), set(m["prod"]))
        self.assertEqual(p["Lomo"][2], m.set_index("prod").loc["Lomo", "clase"])
        self.assertEqual(p["Lomo"][14], "caballo")
        self.assertEqual(d["fuera"], [["Agua", "sin costo cargado", 10.0, 0.0]])
        self.assertEqual(d["resumen"]["n"], res["n"])
        self.assertEqual(d["umbrales_costo"], [45.0, 70.0])
        self.assertEqual((d["etq"], d["etq_ant"], d["dias"]), ("Oct 26", "Sep 26", 21))

    def test_el_js_no_reclasifica(self):
        from graficos import ventas_menu as vm
        js = Path(vm.__file__).with_suffix(".js").read_text(encoding="utf-8")
        # La clase llega hecha: el .js no tiene el umbral del 70 % ni el promedio.
        self.assertNotIn("0.7", js)
        self.assertIn("p[F.clase] === k", js)


def _pieza_en_chromium(pw, nombre, data, alto=650):
    aqui = Path(vp.__file__).parent
    leer = lambda n: (aqui / n).read_text(encoding="utf-8")
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1240, "height": alto})
    pg.set_content(f"<style>:root{{--alto-util:{alto}px}}{leer('ventas_platos_cromo.css')}{leer(nombre + '.css')}</style><div id='r'></div>")
    js = (leer("ventas_platos_cromo.js") + leer(nombre + ".js")).replace(
        "export default function (component)", "window.__montar = function (component)")
    pg.add_script_tag(content=js)
    pg.evaluate("(d) => { window.__enviados = []; window.__montar({ data: d, parentElement: document.getElementById('r'), "
                "setTriggerValue: (k, v) => window.__enviados.push([k, v]) }); }", data)
    return b, pg


class UnaPantallaEnElNavegador(unittest.TestCase):
    """Una fila de controles y una zona por pestaña (regla #767), en Chromium:
    a 1240×650 la tabla muestra lo que antes pedía deslizar, la ficha entra
    entera y lo que carga datos vuelve a Python por `cromo`."""

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
            cls.pw = sync_playwright().start()
        except Exception:
            raise unittest.SkipTest("sin Playwright")

    @classmethod
    def tearDownClass(cls):
        cls.pw.stop()

    def _datos(self):
        filas = [[f"Plato {i:02d}", "Alimentos" if i % 2 else "Bebidas", f"Sub {i % 3}", 3000.0 - i * 90, 40.0 - i, 900.0, 2400.0 - i * 70]
                 for i in range(30)]
        datos = {"ago": periodo([f[:3] + [f[3] * 0.8] + f[4:] for f in filas], 31),
                 "sep": periodo(filas[::-1], 30), "oct": periodo(filas, 30)}
        d = vp.armar_ranking(datos, ["ago", "sep", "oct"], {"ago": "Ago 26", "sep": "Sep 26", "oct": "Oct 26"}, "Plato 00",
                             {"nombre": "Plato 00", "corte": "mes", "serie": [["Ago 26", 80.0, 1.0, True], ["Sep 26", 90.0, 1.0, True], ["Oct 26", 100.0, 1.0, True]]},
                             {"plato 00": "0000001"})
        d["cromo"] = {"vista": "Ranking", "cortes": list(vp.CORTES), "corte": "Mes",
                      "periodos": ["Jul 26", "Ago 26", "Sep 26", "Oct 26", "Nov 26"], "elegidos": ["Ago 26", "Sep 26", "Oct 26"], "max": vp.MAX_PERIODOS}
        return d

    def test_ranking(self):
        b, pg = _pieza_en_chromium(self.pw, "ventas_platos", self._datos())
        r = pg.evaluate("""async () => {
          const raiz = document.querySelector('.vp'), $ = (s) => raiz.querySelector(s), $$ = (s) => [...raiz.querySelectorAll(s)], out = {};
          const t = $('.vp-tabla').getBoundingClientRect();
          out.filas = $$('tr.vp-f').filter((f) => f.getBoundingClientRect().bottom <= t.bottom + 1).length;
          out.altoPieza = raiz.clientHeight; out.desborde = raiz.scrollHeight - raiz.clientHeight;
          out.ficha = [$('.vp-ficha').scrollHeight, $('.vp-ficha').clientHeight];
          out.botones = $$('.vp-fbot button').map((x) => x.textContent.trim());
          out.kpis = $$('.vp-kpi').length;
          out.comparar = $('[data-id="comparar"]').textContent.trim();
          // Puestos: la zona cambia sin una corrida.
          $('[data-acc="tab"][data-id="Puestos"]').click();
          out.puestos = !!$('.vp-z svg') && !$('.vp-tabla'); out.alEnviar0 = window.__enviados.length;
          $('[data-acc="tab"][data-id="Tabla"]').click();
          // «Dentro de» filtra sin una corrida.
          $('[data-id="ambito"]').click();
          $('[data-acc="ambito"][data-tipo="g"][data-id="Bebidas"]').click();
          out.dentro = $('[data-id="ambito"]').textContent.trim();
          $('[data-id="ambito"]').click(); $('[data-acc="ambito"][data-tipo=""]').click();
          // Los meses esperan: dos clics, un pedido, y el menú al cerrarse lo suelta.
          $('[data-id="comparar"]').click();
          $('[data-acc="mes"][data-id="Jul 26"]').click();
          $('[data-acc="mes"][data-id="Nov 26"]').click();
          out.antes = window.__enviados.length;
          $('[data-id="comparar"]').click();
          out.pedido = window.__enviados.at(-1);
          out.apagada = raiz.classList.contains('cargando');
          // Otro corte y la Ingeniería también vuelven a Python.
          $('[data-acc="corte"][data-id="Semana"]').click(); out.corte = window.__enviados.at(-1)[1].corte;
          $('[data-acc="tab"][data-id="Menu"]').click(); out.vista = window.__enviados.at(-1)[1].vista;
          // Elegir un plato pide su evolución.
          $$('tr.vp-f')[3].click(); out.foco = window.__enviados.at(-1);
          return out;
        }""")
        b.close()
        self.assertGreaterEqual(r["filas"], 10)
        self.assertLessEqual(r["desborde"], 0)
        self.assertLessEqual(r["ficha"][0], r["ficha"][1])
        self.assertEqual(r["botones"], ["☆ Elegir", "A qué hora →", "Su costo →"])
        self.assertEqual(r["kpis"], 4)
        self.assertIn("Ago · Sep · Oct 26", r["comparar"])
        self.assertTrue(r["puestos"])
        self.assertEqual(r["alEnviar0"], 0)
        self.assertIn("Bebidas", r["dentro"])
        self.assertEqual(r["antes"], 0)
        self.assertEqual(r["pedido"][0], "cromo")
        self.assertEqual(r["pedido"][1]["elegidos"], ["Ago 26", "Sep 26", "Oct 26", "Nov 26"])
        self.assertTrue(r["apagada"])
        self.assertEqual(r["corte"], "Semana")
        self.assertEqual(r["vista"], "Ingeniería de menú")
        self.assertEqual(r["foco"][0], "foco")

    def test_ingenieria_en_columnas(self):
        from graficos import ventas_menu as vm
        a = pd.DataFrame([{"prod": f"Plato {i:02d}", "grupo": "Alimentos", "sub": "Fondos", "venta": 100.0 + i, "cant": 200.0 - i * 9,
                           "costo": (200.0 - i * 9) * (10 + i), "neto": (200.0 - i * 9) * 60.0, "pedidos": 100.0} for i in range(20)])
        m, fuera, res = vm.clasificar(a, [("Alimentos", "Fondos")])
        d = vm.armar_menu(m, fuera, res, {}, "Oct 26", "Sep 26", 30)
        d["cromo"] = {"vista": "Menu", "cortes": list(vp.CORTES), "corte": "Mes", "periodos": ["Sep 26", "Oct 26"], "elegidos": ["Sep 26", "Oct 26"], "max": vp.MAX_PERIODOS}
        d["categorias"] = [{"r": "Fondos · Alimentos", "on": True}, {"r": "Entradas · Alimentos", "on": False}]
        b, pg = _pieza_en_chromium(self.pw, "ventas_menu", d)
        r = pg.evaluate("""() => {
          const raiz = document.querySelector('.ig'), $ = (s) => raiz.querySelector(s), $$ = (s) => [...raiz.querySelectorAll(s)], out = {};
          const kx = $$('.ig-kpi').map((k) => Math.round(k.getBoundingClientRect().left)), cx = $$('.ig-cuadro').map((k) => Math.round(k.getBoundingClientRect().left));
          out.alineados = kx.join() === cx.join();
          out.platos = $$('.ig-filas li:not(.ig-cols)').length;
          out.desborde = raiz.scrollHeight - raiz.clientHeight;
          $('[data-id="cat"]').click();
          out.cats = $$('[data-cat]').length;
          const nueva = $('[data-cat="Entradas · Alimentos"]'); nueva.click();
          $('[data-id="cat"]').click();
          out.subs = window.__enviados.at(-1);
          $('[data-acc="tab"][data-id="Puestos"]').click();
          out.vista = window.__enviados.at(-1)[1].vista;
          return out;
        }""")
        b.close()
        self.assertTrue(r["alineados"])
        self.assertEqual(r["platos"], 20)
        self.assertLessEqual(r["desborde"], 0)
        self.assertEqual(r["cats"], 2)
        self.assertEqual(r["subs"][1]["subs"], ["Fondos · Alimentos", "Entradas · Alimentos"])
        self.assertEqual(r["vista"], "Ranking")


if __name__ == "__main__":
    unittest.main()
