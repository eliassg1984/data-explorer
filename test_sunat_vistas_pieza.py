"""Documentos SUNAT › «Cruce con SUNAT» y «Proveedores y fechas» (regla #760).

Lista a la izquierda y ficha del elegido al costado: lo que recibe la pieza del
cruce de verdad (`_sunat_vistas.datos_cruce`) y, en Chromium, que se pueda elegir,
filtrar y saltar a la tabla o a un mes sin volver a Python.
"""
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from graficos.compras import _sunat_vistas as sv

ROOT = Path(__file__).parent


def cruce(desde="2026-08-10", k=1.0):
    def r(doc, ruc, nom, tipo, est, su, si, dia=0):
        return dict(documento=doc, car=doc, proveedor=nom, proveedor_sistema=nom, ruc_proveedor=ruc, ruc_sistema=ruc, tipo=tipo, estado=est,
                    total_sunat=None if est == "Solo sistema" else su * k, total_sistema=None if est == "Solo SUNAT" else si * k,
                    fecha_emision=pd.Timestamp(desde) + pd.Timedelta(days=dia), base_sunat=None, base_sistema=None, igv_sunat=None, igv_sistema=None)
    return pd.DataFrame([
        r("F1-1", "111", "Carnes", "Mercadería", "Coincide", 800, 800),
        r("F1-2", "111", "Carnes", "Mercadería", "Solo SUNAT", 100, None),
        r("F2-1", "222", "Licores", "Mercadería", "Diferencia", 100, 90, 25),
        r("N2-1", "222", "Licores", "Mercadería", "Solo SUNAT", -50, None, 25),
        r("S1-1", "333", "Luz", "Servicios", "Solo SUNAT", 500, None),
        r("Z1-1", "444", "Sin SUNAT", "Mercadería", "Solo sistema", None, 70),
    ])


def datos_cruce():
    return sv.datos_cruce(cruce(), [("2024-25", "r1", cruce("2025-08-10", .5), None), ("2023-24", "r2", None, "sin datos")], "ago – set 2026", {"doc": 2, "soles": 150.0, "dias": 7}, "2025-26")


def datos_prov():
    return sv.datos_proveedores(cruce(), {"111": [10.0] * 12}, "2026-09-30")


class Datos(unittest.TestCase):
    def test_mes_a_mes_por_tipo_suma_el_total(self):
        d = datos_cruce()
        self.assertEqual([m["k"] for m in d["mes"]["__total"]], ["2026-08", "2026-09"])
        self.assertEqual(sum(m["f"]["doc"]["sunat"] for m in d["mes"]["Mercadería"]), 4)
        self.assertEqual(sum(m["f"]["doc"]["sunat"] for t in ("Mercadería", "Servicios") for m in d["mes"][t]),
                         sum(m["f"]["doc"]["sunat"] for m in d["mes"]["__total"]))

    def test_ir_al_mes_lleva_a_proveedores(self):
        ss = {"sunat_pieza_cruce": {"ir": {"destino": "prov", "mes": "2026-09", "t": 5}}}
        with patch.object(sv.st, "session_state", ss):
            sv._al_ir()
        self.assertEqual(ss[sv.K_VISTA], sv.VISTA_PROV)
        self.assertEqual(ss[sv.K_PROV_INICIAL], {"agr": "mes", "k": "2026-09", "t": 5})
        self.assertNotIn(sv.K_LLEGADA, ss)

    def test_ir_a_la_tabla_sigue_igual(self):
        ss = {"sunat_pieza_cruce": {"ir": {"desde": "Cruce con SUNAT", "tipo": "Mercadería", "estados": ["Diferencia"], "t": 6}}}
        from graficos.compras import documentos_sunat as ds
        with patch.object(sv.st, "session_state", ss), patch.object(ds, "poner_proveedor"), patch.object(ds, "poner_estado"):
            sv._al_ir()
        self.assertEqual(ss[sv.K_VISTA], sv.VISTA_DOCS)
        self.assertEqual(ss[sv.K_LLEGADA]["tipo"], "Mercadería")


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, "sin Playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.br = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))
        cls.pg = cls.br.new_page(viewport={"width": 1323, "height": 696})
        cls.pg.set_default_timeout(5000)
        cls.pg.route("https://svx.test.example/**", lambda r: r.fulfill(body='<div id="host"></div>', content_type="text/html"))
        cls.pg.goto("https://svx.test.example/")
        css = (ROOT / "graficos/compras/sunat_vistas.css").read_text(encoding="utf-8")
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"});window.mount=document.createElement("div");'
                        'const st=document.createElement("style");st.textContent=css;sr.append(st,window.mount);}', css)
        js = (ROOT / "graficos/compras/sunat_vistas.js").read_text(encoding="utf-8")
        cls.pg.add_script_tag(content=re.sub(r"export\s+default\s+function\s*\(component\)", "window.pieza=function(component)", js))

    @classmethod
    def tearDownClass(cls):
        cls.br.close()
        cls.pw.stop()

    def mount(self, P):
        P = __import__("json").loads(__import__("json").dumps(P, default=str))
        self.pg.evaluate('P=>{window.trig=[];window.mount.innerHTML="";window.pieza({data:P,parentElement:window.mount,setTriggerValue:(k,v)=>window.trig.push(v)})}', P)

    def txt(self, sel):
        return self.pg.evaluate('s=>{const e=window.mount.querySelector(s);return e?e.innerText.replace(/\\n/g," | "):null}', sel)

    def clic(self, sel):
        self.pg.evaluate('s=>window.mount.querySelector(s).click()', sel)

    def trig(self):
        return self.pg.evaluate("window.trig")

    def test_cruce_abre_en_mercaderia_con_su_ficha(self):
        self.mount(datos_cruce())
        self.assertIn("Mercadería", self.txt(".fila.on"))
        self.assertIn("Fidelidad · Mercadería", self.txt(".kpi"))
        self.assertIn("Quién le baja", self.txt(".panel"))
        self.assertIn("Licores", self.txt(".panel"))

    def test_elegir_fila_y_el_total(self):
        self.mount(datos_cruce())
        self.clic('[data-sel-fila="__total"]')
        self.assertIn("Fidelidad · Total del período", self.txt(".kpi"))
        self.clic('[data-sel-fila="Servicios"]')
        self.assertIn("Luz", self.txt(".panel"))

    def test_indicador_filtra_la_ficha_y_el_salto(self):
        self.mount(datos_cruce())
        self.clic('.kpi[data-kpi="diferencia"]')
        self.assertTrue(self.pg.evaluate('()=>window.mount.querySelector(".kpi[data-kpi=diferencia]").classList.contains("on")'))
        self.assertIn("Licores", self.txt(".panel"))
        self.assertNotIn("Carnes", self.txt(".panel"))
        self.clic(".panel .ir")
        t = self.trig()[-1]
        self.assertEqual((t["tipo"], t["estados"], t["desde"]), ("Mercadería", ["Diferencia"], "Cruce con SUNAT"))

    def test_ver_un_proveedor_de_la_ficha(self):
        self.mount(datos_cruce())
        self.clic("button.pp")
        t = self.trig()[-1]
        self.assertEqual(t["tipo"], "Mercadería")
        self.assertTrue(t["prov"])

    def test_ano_por_ano_y_contra(self):
        self.mount(datos_cruce())
        self.clic('button[data-seg="Ficha"][data-v="anios"]')
        self.assertIn("2024-25", self.txt(".panel"))
        self.assertIn("vs 2024-25", self.txt(".kpi"))
        self.clic('button[data-seg="Filas"][data-v="anio"]')
        self.assertIn("2025-26", self.txt(".lista"))
        self.assertIn("Los tipos de 2025-26", self.txt(".panel"))

    def test_tipo_por_ano_sigue_y_a_todo_el_ancho(self):
        self.mount(datos_cruce())
        self.clic('button[data-seg="Filas"][data-v="tipoxanio"]')
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".tarjeta").length'), 3)
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".panel").length'), 0)

    def test_medida_notas_y_mes(self):
        self.mount(datos_cruce())
        antes = self.txt(".fila.on")
        self.clic('button[data-seg="Medir en"][data-v="doc"]')
        self.assertNotEqual(antes, self.txt(".fila.on"))
        self.clic('button[data-seg="Medir en"][data-v="soles"]')
        self.pg.evaluate('()=>{const s=window.mount.querySelector("select[data-sel=nc]");s.value="aparte";s.dispatchEvent(new Event("change",{bubbles:true}))}')
        self.assertIn("quedan aparte", self.txt(".nota"))
        self.clic('.mesc[data-mes="2026-09"]')
        t = self.trig()[-1]
        self.assertEqual((t["destino"], t["mes"]), ("prov", "2026-09"))

    def test_proveedores_lista_y_ficha(self):
        self.mount(datos_prov())
        self.assertEqual(self.pg.evaluate('()=>window.mount.querySelectorAll(".fila").length'), 4)
        self.assertIn("En SUNAT", self.txt(".panel"))
        self.clic('.fila[data-psel="111"]') if self.pg.evaluate('()=>!!window.mount.querySelector(".fila[data-psel=\\"111\\"]")') else self.pg.evaluate('()=>[...window.mount.querySelectorAll(".fila")].find(b=>b.innerText.includes("Carnes")).click()')
        self.assertIn("Carnes", self.txt(".panel h3"))
        self.assertIn("últimos 12 meses", self.txt(".panel"))
        self.clic(".panel .ir")
        self.assertTrue(self.trig()[-1]["prov"])

    def test_proveedores_buscar_sin_perder_el_foco(self):
        self.mount(datos_prov())
        self.pg.evaluate('()=>window.mount.querySelector(".buscar").focus()')
        self.pg.keyboard.type("luz", delay=20)
        estado = self.pg.evaluate('()=>[window.mount.getRootNode().activeElement.className,window.mount.querySelectorAll(".fila").length]')
        self.assertEqual(estado, ["buscar", 1])

    def test_proveedores_mes_y_llegada_desde_el_cruce(self):
        self.mount(datos_prov() | dict(inicial=dict(agr="mes", k="2026-08", t=9)))
        self.assertIn("Mes", self.txt(".seg .on"))
        self.assertIn("Ago 2026", self.txt(".fila.on"))
        self.clic(".panel .ir")
        t = self.trig()[-1]
        self.assertEqual((t["fini"], t["ffin"]), ("2026-08-10", "2026-08-10"))

    def test_no_desborda_y_cabe_en_celular(self):
        self.mount(datos_cruce())
        self.assertEqual(self.pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        self.pg.set_viewport_size({"width": 390, "height": 844})
        try:
            self.mount(datos_cruce())
            self.assertEqual(self.pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
            self.assertGreater(self.pg.evaluate('()=>window.mount.querySelector(".panel").getBoundingClientRect().width'), 300)
        finally:
            self.pg.set_viewport_size({"width": 1323, "height": 696})


if __name__ == "__main__":
    unittest.main()
