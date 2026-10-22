"""«Nuevo Costeo» como pieza propia (regla #697): lo que recibe la pieza y
cómo vuelve lo que se edita en ella. Sin secrets ni red."""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

SCRIPT = '''
from unittest.mock import patch
import streamlit as st
import graficos  # noqa: F401  (formulario_receta se importa desde graficos.recetas)
import formulario_receta as fr

ss = st.session_state
fr._init_estado()
if "armado" not in ss:
    ss["armado"] = True
    ss[fr._key_lineas("modificar")] = [
        {"sid": "959:0", "cod": "0001078", "nombre": "(L) Aji Amarillo limpio",
         "unidad": "GRAMOS", "cantidad": 60.0, "precio": 0.01105, "tipo": "sistema", "activo": None},
        {"sid": "959:1", "cod": "0004160", "nombre": "(P) Lomo trozos 170gr", "unidad": "UND",
         "cantidad": 1.0, "precio": 22.16, "tipo": "sistema", "activo": None},
        {"cod": "0000297", "nombre": "Mantequilla Sin Sal", "unidad": "GRAMOS",
         "cantidad": 8.0, "precio": 0.0394, "tipo": "almacen", "activo": False},
    ]
    ss[fr._key("modificar", "origen")] = {
        "cod": "0000959", "nombre": "Lomo Saltado", "pv": 79.0, "costo": 22.823,
        "lineas": {"959:0": (60.0, 0.01105), "959:1": (1.0, 22.16), "959:2": (2.0, 0.0107)}}
    ss[fr._key("modificar", "pv")] = 79.0
with patch.object(fr, "_PIEZA") as pieza, \\
     patch.object(fr, "_usos", return_value=[]), patch.object(fr, "_otros", return_value=None), \\
     patch.object(fr, "_que_modificar", return_value="plato"):
    if ss.get("cambio"):
        ss[fr._key("modificar", "pieza")] = {"cambios": ss["cambio"]}
        fr._aplicar_cambios("modificar")
    origen = ss[fr._key("modificar", "origen")]
    fr._pieza("modificar", origen, None)
    ss["data"] = pieza.call_args.kwargs["data"]
'''


class LaPieza(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_string(SCRIPT, default_timeout=60).run()
        self.assertFalse(self.at.exception)

    def test_lo_que_recibe(self):
        d = self.at.session_state["data"]
        self.assertEqual([l["chip"] for l in d["lineas"]], ["L", "P", "insumo"])
        self.assertEqual(d["lineas"][0]["antes"], [60.0, 0.01105])
        self.assertIsNone(d["lineas"][2]["antes"])
        self.assertTrue(d["lineas"][2]["inactivo"])
        self.assertEqual(d["origen"]["quitadas"], 1)
        self.assertEqual(d["canales"], ["En el Local", "Delivery", "Para Llevar", "Rappi", "Pedidos Ya"])
        self.assertEqual((d["pv"], d["precios"], d["rev"]), (79.0, None, 0))
        self.assertEqual(len({l["uid"] for l in d["lineas"]}), 3)

    def test_lo_editado_vuelve(self):
        uids = [l["uid"] for l in self.at.session_state["data"]["lineas"]]
        self.at.session_state["cambio"] = {
            "rev": 3, "lineas": [[uids[0], 30.0, 0.012], [uids[1], 1.0, 22.16]],
            "quitar": [uids[2]], "pv": 85.0, "precios": [85, 85, 85, 89, 89]}
        self.at.run()
        self.assertFalse(self.at.exception)
        d = self.at.session_state["data"]
        self.assertEqual([l["uid"] for l in d["lineas"]], uids[:2])
        self.assertEqual((d["lineas"][0]["cantidad"], d["lineas"][0]["precio"]), (30.0, 0.012))
        self.assertEqual((d["pv"], d["precios"], d["rev"]), (85.0, [85, 85, 85, 89, 89], 3))

    def test_el_js_hace_la_cuenta_del_sistema(self):
        js = Path(__file__).with_name("graficos").joinpath("nuevo_costeo.js").read_text(encoding="utf-8")
        # Neto = precio ÷ divisor; recargo e IGV sobre el neto; % = costo ÷ neto.
        for f in ("const neto = pv > 0 ? pv / d.divisor : 0;", "recargo: neto * d.recargo, igv: neto * d.igv",
                  "pct: neto > 0 ? costo / neto * 100 : null", "l.cantidad * l.precio"):
            self.assertIn(f, js)


class Guardadas(unittest.TestCase):
    """«Guardadas» (regla #698): lo que recibe la lista y en qué modo se
    abre cada propuesta."""

    def setUp(self):
        import graficos  # noqa: F401  (formulario_receta se importa desde graficos.recetas)
        import formulario_receta as fr
        self.fr = fr

    def test_la_lista(self):
        props = [
            {"_clave": "a.json", "tipo": "Receta de Venta", "nombre": "lomo", "guardado_por": "jose",
             "guardado_en": "2026-08-13T15:00:41+00:00",
             "lineas": [{"cod": "1", "nombre": "Lomo", "unidad": "KILOS", "cantidad": 1, "precio": 100.74}]},
            {"_clave": "b.json", "tipo": "Modificación de receta", "nombre": "Lomo Saltado",
             "guardado_en": "2026-10-22T14:00:00+00:00", "precio_venta": 79.0,
             "plato_sistema": "0000959", "precio_venta_sistema": 79.0, "costo_sistema": 28.35,
             "precios_canal": {"En el Local": 79, "Rappi": 89},
             "lineas": [{"cod": "2", "nombre": "x", "unidad": "UND", "cantidad": 2, "precio": 14.0}]},
        ]
        d = self.fr.armar_guardadas(props, "b.json")
        a, b = d["propuestas"]
        self.assertEqual((a["cuando"], a["n"], a["costo"], a["pv"], a["pct"]), ("13 ago 26", 1, 100.74, 0.0, None))
        self.assertAlmostEqual(b["pct"], 28 / (79 / d["divisor"]) * 100)
        self.assertAlmostEqual(b["sistema"]["pct"], 28.35 / (79 / d["divisor"]) * 100)
        self.assertEqual(b["canales"], [["En el Local", 79.0], ["Rappi", 89.0]])
        self.assertEqual(d["sel"], "b.json")

    def test_en_que_modo_se_abre(self):
        m = self.fr._modo_de_propuesta
        self.assertEqual(m({"tipo": "Receta de Venta"}), ("venta", None))
        self.assertEqual(m({"tipo": "Combo"}), ("combo", None))
        self.assertEqual(m({"plato_sistema": "1"}), ("modificar", "plato"))
        self.assertEqual(m({"combo_sistema": "1"}), ("modificar", "combo"))
        self.assertEqual(m({"receta_base_sistema": "1"}), ("modificar", "base"))


if __name__ == "__main__":
    unittest.main()
