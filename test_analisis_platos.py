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


if __name__ == "__main__":
    unittest.main()
