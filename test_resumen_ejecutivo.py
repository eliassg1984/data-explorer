"""Casos financieros del Resumen: duplicados, canjes, cierres y enlaces."""

import datetime as dt
import unittest
from urllib.parse import parse_qs

import pandas as pd

import costo_ventas as cv
import definicion_venta as dv
import resumen_ejecutivo as re


class ResumenTest(unittest.TestCase):
    def test_pedidos_y_venta_no_duplican_pago_dividido_ni_canje(self):
        filas = [
            # Dos formas de pago del mismo ítem.
            ("2026-09-01", "P1", "B1", "I1", dv.VENTA, 100),
            ("2026-09-01", "P1", "B1", "I1", dv.VENTA, 100),
            # Factura que canjea la boleta: la nota compensa, no otra mesa.
            ("2026-09-02", "P1", "F1", "I2", dv.VENTA, 100),
            ("2026-09-02", "P1", "N1", "I3", dv.NOTA_CREDITO, -100),
            # Cuenta dividida en dos comprobantes: un pedido.
            ("2026-09-03", "P2", "B2", "I4", dv.VENTA, 40),
            ("2026-09-03", "P2", "B3", "I5", dv.VENTA, 60),
            # Cortesías y anulaciones no son venta.
            ("2026-09-04", "P3", "C1", "I6", dv.CORTESIA, 300),
            ("2026-09-04", "P4", "A1", "I7", dv.ANULADO, 400),
        ]
        d = pd.DataFrame(filas, columns=[dv.FECHA, re.PEDIDO, dv.LLAVE_DOC,
                                        dv.LLAVE_ITEM, dv.CLASE, dv.NETO_ITEM])
        d[dv.COSTO] = 10.0
        r = re.ventas_del_rango(d, dt.date(2026, 9, 1), dt.date(2026, 9, 30))
        self.assertEqual(r["venta"], 200)
        self.assertEqual(r["pedidos"], 2)
        self.assertEqual(r["promedio"], 100)
        self.assertEqual(sum(x["venta"] for x in r["dias"]), 200)
        self.assertEqual(re.ventas_del_rango(d, dt.date(2026, 9, 2),
                                           dt.date(2026, 9, 2))["pedidos"], 0)

    def test_devolucion_resta_y_no_inventa_promedio(self):
        d = pd.DataFrame({dv.FECHA: ["2026-09-02"], re.PEDIDO: ["P1"],
                          dv.LLAVE_DOC: ["NC"], dv.LLAVE_ITEM: ["I1"],
                          dv.CLASE: [dv.NOTA_CREDITO], dv.NETO_ITEM: [-100]})
        r = re.ventas_del_rango(d, dt.date(2026, 9, 1), dt.date(2026, 9, 30))
        self.assertEqual(r["pedidos"], -1)
        self.assertIsNone(r["promedio"])
        self.assertIsNone(r["sin_costo"])
        self.assertIsNone(re.ventas_del_rango(None, *re.rango_mes("2026-09")))
        d = d.drop(columns=re.PEDIDO)
        self.assertIsNone(re.ventas_del_rango(d, *re.rango_mes("2026-09"))["pedidos"])

    def test_mismo_tramo_y_febrero_bisiesto(self):
        ini, fin = re.rango_mes("2026-10", dt.date(2026, 10, 16))
        self.assertEqual((ini, fin), (dt.date(2026, 10, 1), dt.date(2026, 10, 16)))
        self.assertEqual(re.rango_anterior(ini, fin),
                         (dt.date(2025, 10, 1), dt.date(2025, 10, 16)))
        self.assertEqual(re.rango_anterior(*re.rango_mes("2024-02"))[1],
                         dt.date(2023, 2, 28))
        self.assertIsNone(re.variacion(100, 0))
        self.assertIsNone(re.variacion(100, None))

    def test_costo_coincide_con_defaults_y_bajas_no_se_deducen(self):
        def serie(v):
            return {c: [v if c == "Alimentos" else 0] for c in cv.CUBETAS}
        datos = {"periodos": [{"k": "2026-09", "sub": "1 oct"}],
                 "filas": {k: serie(v) for k, v in {
                     "inv_inicial": 1000, "compras": 500, "inv_final": 800,
                     "venta": 1000, "costo_pos": 450, "cortesias": 50,
                     "descuentos": 20}.items()},
                 "salidas": {"Bajas": serie(30), "Comida Personal": serie(100)},
                 "venta_extra": {"Eventos": [200], "Venta interna": [999]},
                 "costo_extra": {"Eventos": [60], "Venta interna": [900]},
                 "descuento_extra": {"Eventos": [10], "Venta interna": [100]}}
        r = re.costo_del_mes(datos, "2026-09")
        self.assertEqual(r["venta_base"], 1200)
        self.assertEqual(r["operativo"], 700)
        self.assertEqual(r["no_vendido"], 180)
        self.assertEqual(r["carta"], 520)
        self.assertEqual(r["pos"], 480)
        self.assertEqual(r["diferencia"], 40)
        self.assertEqual(r["faltante"], 10)
        self.assertAlmostEqual(r["porcentaje"], 700 / 1200)
        self.assertIsNone(r["familias"][-1]["porcentaje"])
        self.assertIsNone(re.costo_del_mes(datos, "2026-08"))

    def test_enlaces_llevan_periodo_y_validan_fecha(self):
        ini, fin = re.rango_mes("2026-09")
        url = re.enlace_reporte("Ventas", "resumen_ejecutivo", ini, fin)
        params = {k: v[0] for k, v in parse_qs(url[1:]).items()}
        self.assertEqual(params["reporte"], "Ventas")
        self.assertEqual(re.rango_del_enlace(params), (ini, fin))
        self.assertIsNone(re.rango_del_enlace({"desde": "invalido", "hasta": "2026-09-30"}))
        self.assertIsNone(re.rango_del_enlace({"desde": "2026-10-01", "hasta": "2026-09-30"}))
        url = re.enlace_reporte("Costos", "costo_de_ventas", mes="2026-09")
        self.assertEqual(parse_qs(url[1:])["mes"], ["2026-09"])


if __name__ == "__main__":
    unittest.main()
