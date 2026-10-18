"""Impacto conjunto, períodos inclusivos y edición sincronizada de precios."""
import datetime as dt
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

import simulador_receta as sr
from graficos import recetas_alza as vista
from graficos.carta_costeada import con_ventas, ctx_fecha as ctx_carta


def datos():
    carta = pd.DataFrame({
        "Cod": ["P1", "P2", "P3"], "Producto": ["Lomo", "Sopa", "Agua"],
        "Grupo": ["Alimentos"] * 3, "Subgrupo": ["Fondos"] * 3,
        "Precio": [100.0, 50.0, 10.0], "Neto": [80.0, 40.0, 8.0],
        "Costo": [20.0, 10.0, 2.0], "SinCosto": [False] * 3,
    })
    ventas = pd.DataFrame({
        "dia": ["2026-09-30", "2026-10-01", "2026-10-07 23:59:00",
                "2026-10-08", "2026-10-31", "2026-11-01"],
        "producto": ["P1", "P1", "P2", "P1", "P3", "P1"],
        "unidades": [100.0, 10.0, 4.0, 20.0, 2.0, 100.0],
        "neto": [8000.0, 700.0, 150.0, 1400.0, 16.0, 8000.0],
        "costo": [2000.0, 200.0, 40.0, 400.0, 4.0, 2000.0],
        "neto_sin_costo": [0.0] * 6,
    })
    ventas["dia"] = pd.to_datetime(ventas["dia"], format="mixed")
    expo = {"P1": {"A": 12.0, "B": 8.0}, "P2": {"B": 10.0}, "P3": {"C": 2.0}}
    catalogo = pd.DataFrame({
        "cod": ["A", "B"], "precio_kardex": [60.0, 20.0],
        "unidad_kardex": ["KILOS", "LITROS"], "precio": [0.06, 0.02],
    })
    return carta, ventas, expo, catalogo


class ImpactoAlza(unittest.TestCase):
    def setUp(self):
        self.carta, self.ventas, self.expo, self.catalogo = datos()

    def periodo(self, ini, fin):
        return con_ventas(self.carta, self.ventas, rango=(ini, fin))[0]

    def test_varios_insumos_suman_sin_duplicar_plato(self):
        carta = self.periodo("2026-10-01", "2026-10-07")
        t = sr.alzas(self.expo, carta, {"A": 25, "B": -10})
        self.assertEqual(set(t.Cod), {"P1", "P2"})
        self.assertTrue(t.Cod.is_unique)
        p1 = t.set_index("Cod").loc["P1"]
        self.assertAlmostEqual(p1.CostoNuevo, 22.2)
        self.assertAlmostEqual(p1.DeltaPeriodo, 22.0)
        self.assertAlmostEqual(p1.PrecioMantener, 111.0)
        self.assertAlmostEqual(t.DeltaPeriodo.sum(), 18.0)
        self.assertAlmostEqual(p1.MargenNuevoPeriodo, 478.0)

    def test_dia_semana_mes_con_sus_ventas_reales(self):
        for ini, fin, esperado in [
            ("2026-10-01", "2026-10-01", 12.0),
            ("2026-10-01", "2026-10-07", 12.0),
            ("2026-10-01", "2026-10-31", 36.0),
            ("2026-09-30", "2026-10-01", 132.0),
        ]:
            with self.subTest(ini=ini, fin=fin):
                t = sr.alzas(self.expo, self.periodo(ini, fin), {"A": 10})
                self.assertAlmostEqual(t.DeltaPeriodo.sum(), esperado)
        semana = self.periodo("2026-10-01", "2026-10-07")
        self.assertEqual(semana.set_index("Cod").loc["P2", "Vendidos"], 4)

    def test_resumen_incluye_no_afectados_y_descuentos_reales(self):
        carta = self.periodo("2026-10-01", "2026-10-31")
        t = sr.alzas(self.expo, carta, {"A": 10})
        r = sr.resumen_alzas(carta, t)
        self.assertEqual(r["neto"], 2266.0)
        self.assertEqual(r["costo"], 644.0)
        self.assertAlmostEqual(r["costo_nuevo"], 680.0)
        self.assertAlmostEqual(r["margen_nuevo"], 1586.0)
        self.assertAlmostEqual(r["margen_nuevo"] - r["margen"], -r["delta"])

    def test_sin_ventas_conserva_costo_unitario_y_periodo_cero(self):
        for ventas in (None, self.ventas.iloc[:0]):
            carta, _ = con_ventas(self.carta, ventas)
            t = sr.alzas(self.expo, carta, {"A": -100})
            self.assertEqual(t.CostoNuevo.iloc[0], 8.0)
            self.assertEqual(t.DeltaPeriodo.sum(), 0.0)
            self.assertEqual(sr.resumen_alzas(carta, t)["margen_nuevo"], 0.0)
        carta = self.periodo("2026-10-02", "2026-10-06")
        self.assertEqual(sr.alzas(self.expo, carta, {"A": 10}).DeltaPeriodo.sum(), 0)

    def test_cancelacion_baja_y_escenario_vacio(self):
        carta = self.periodo("2026-10-01", "2026-10-01")
        t = sr.alzas(self.expo, carta, {"A": 20, "B": -30})
        self.assertAlmostEqual(t.set_index("Cod").loc["P1", "DeltaUnitario"], 0)
        self.assertEqual(t.set_index("Cod").loc["P2", "DeltaUnitario"], -3)
        self.assertTrue(sr.alzas(self.expo, carta, {}).empty)
        self.assertTrue(sr.alzas(self.expo, carta.iloc[:0], {"A": 10}).empty)
        self.assertTrue(sr.alzas(self.expo, carta, {"DESCONOCIDO": 10}).empty)
        for pct in (-101, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                sr.alzas(self.expo, carta, {"A": pct})

    def test_referencias_en_unidad_de_compra_no_gramo(self):
        compras = {"A": {"ult": 65.0, "unid": "kg"}, "C": {"ult": 2.0, "unid": "und"}}
        refs = vista._referencias(self.catalogo, compras)
        self.assertEqual(refs["A"], (60.0, "KILOS", "promedio de almacén"))
        self.assertEqual(refs["C"], (2.0, "und", "última compra"))
        self.assertNotIn("D", refs)

    def test_fecha_independiente_de_costo_carta(self):
        hoy = dt.date(2026, 11, 1)
        a, c = vista.ctx_fecha(self.ventas, hoy), ctx_carta(self.ventas, hoy)
        self.assertNotEqual(a["k_rango"], c["k_rango"])
        self.assertEqual(a["fecha_min"], dt.date(2026, 9, 30))
        self.assertEqual(a["fecha_max"], dt.date(2026, 11, 1))
        self.assertIn("alza", a["rango_default_cat"])
        self.assertIsNone(vista.ctx_fecha(None, hoy))


SCRIPT_UI = '''
from unittest.mock import patch
from test_recetas_alza import datos
from graficos import recetas_alza as v
carta, ventas, expo, catalogo = datos()
with patch.object(v, "cargar", return_value=carta), \\
     patch.object(v, "preparar", return_value=(carta, 0)), \\
     patch.object(v, "sello_datos", return_value="test"), \\
     patch.object(v, "_exposicion", return_value=(expo, {"A": "Lomo", "B": "Aceite", "C": "Agua"})), \\
     patch.object(v, "_precios_compra", return_value={}), \\
     patch.object(v, "catalogo_insumos", return_value=catalogo), \\
     patch.object(v, "selector_fecha_tarjeta"):
    v.render_alza(ventas=ventas)
'''


class EdicionPrecios(unittest.TestCase):
    def test_porcentaje_valor_y_varios_insumos(self):
        at = AppTest.from_string(SCRIPT_UI, default_timeout=30).run()
        self.assertFalse(at.exception)
        at.multiselect(key="rec_alza_insumos").set_value(["A", "B"]).run()
        at.number_input(key="rec_alza_pct_A").set_value(25.0).run()
        self.assertFalse(at.exception)
        self.assertAlmostEqual(at.number_input(key="rec_alza_valor_A").value, 75.0)
        at.number_input(key="rec_alza_valor_B").set_value(18.0).run()
        self.assertFalse(at.exception)
        self.assertAlmostEqual(at.number_input(key="rec_alza_pct_B").value, -10.0)
        self.assertAlmostEqual(at.number_input(key="rec_alza_pct_A").value, 25.0)
        # Cambiar sólo la fecha conserva el escenario y recalcula ambas tablas.
        ctx = vista.ctx_fecha(datos()[1])
        at.session_state[ctx["k_rango"]] = (dt.date(2026, 10, 1), dt.date(2026, 10, 7))
        at.run()
        self.assertFalse(at.exception)
        self.assertAlmostEqual(at.dataframe[0].value.loc[0, "Cambio"], 18.0)
        self.assertAlmostEqual(at.dataframe[1].value["Δ costo período"].sum(), 18.0)
        self.assertEqual(at.number_input(key="rec_alza_pct_A").value, 25.0)
        at.number_input(key="rec_alza_valor_A").set_value(0.0).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.number_input(key="rec_alza_pct_A").value, -100.0)
        at.multiselect(key="rec_alza_insumos").set_value(["C"]).run()
        self.assertFalse(at.exception)
        self.assertTrue(at.number_input(key="rec_alza_valor_C").disabled)
        at.multiselect(key="rec_alza_insumos").set_value([]).run()
        self.assertFalse(at.exception)
        self.assertTrue(at.info)


if __name__ == "__main__":
    unittest.main()
