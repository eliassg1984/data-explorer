"""«Costo de Carta» como pieza propia (regla #696): los cinco canales del
POS, lo vendido por canal y lo que recibe el navegador. Sin secrets ni red."""
import datetime as dt
import unittest
from pathlib import Path

import pandas as pd

from graficos import carta_costeada as cc


def carta():
    """Tres productos con los nombres de columna de cartacosteada.parquet:
    el Lomo con otro precio en Rappi, el Agua sin costo y un inactivo."""
    return pd.DataFrame({
        "GRUPO": ["Alimentos", "Bebidas", "Alimentos"],
        "SUBGRUPO": ["Fondos", "Aguas", "Fondos"],
        "COD PLATO": ["0000001", "0000002", "0000003"],
        "ITEM VENT": ["Lomo", "Agua", "Viejo"],
        "ITEM VENT ACT": ["ACTIV", "ACTIV", "INACT"],
        "P.VENTA SALON": [79.0, 11.0, 50.0], "P.VENTA DELIVERY": [79.0, 11.0, 50.0],
        "P.VENTA LLEVAR": [1.0, 11.0, 50.0], "P.VENTA RAPPI": [89.0, 9.0, 50.0],
        "P.VENTA 5": [0.0, 9.0, 50.0],
        "COSTO SALON": [28.35, None, 10.0], "COSTO DELIVERY": [28.35, None, 10.0],
        "COSTO LLEVAR": [28.35, None, 10.0], "COSTO RAPPI": [28.35, None, 10.0],
        "COSTO 5": [28.35, None, 10.0],
        "TIPO DESC": ["RECETA", "NO APLICA", "RECETA"],
        "NOMB DESC": ["Lomo", "Agua", "Viejo"], "TIPO COMBO": [None] * 3,
        "Tipo de Oferta": ["Carta impresa", "Carta no impresa", None],
    })


def vendido():
    return pd.DataFrame({
        "producto": ["0000001", "0000001", "0000002"],
        "dia": pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-02"]),
        "unidades": [10.0, 5.0, 20.0], "neto": [640.0, 320.0, 178.0],
        "costo": [283.5, 141.75, 0.0], "unidades_costeadas": [10.0, 5.0, 0.0],
        "neto_sin_costo": [0.0, 0.0, 178.0],
    })


def otros_canales():
    return pd.DataFrame({
        "producto": ["0000001", "0000001", "0000002"],
        "dia": pd.to_datetime(["2026-10-02", "2026-11-05", "2026-10-02"]),
        "canal": ["Rappi", "Rappi", "Pedidos Ya"],
        "unidades": [2.0, 9.0, 4.0], "neto": [144.1, 600.0, 29.0], "costo": [56.7, 255.0, 0.0],
    })


class CanalesDeLaCarta(unittest.TestCase):
    def setUp(self):
        self.t, _ = cc.preparar(carta(), incluir_inactivos=True)
        self.t = self.t.set_index("Cod")

    def test_cinco_precios_y_cinco_costos(self):
        lomo = self.t.loc["0000001"]
        self.assertEqual([lomo[f"Precio{i}"] for i in range(5)], [79.0, 79.0, 0.0, 89.0, 0.0])
        self.assertEqual(lomo["Costo3"], 28.35)
        self.assertEqual(self.t.loc["0000002", "Costo0"], 0.0)

    def test_activo_viaja_y_no_filtra_con_inactivos(self):
        self.assertEqual(self.t["Activo"].to_dict(),
                         {"0000001": True, "0000002": True, "0000003": False})
        solo, _ = cc.preparar(carta())
        self.assertEqual(list(solo["Cod"]), ["0000001", "0000002"])

    def test_los_canales_son_los_del_pos_en_su_orden(self):
        self.assertEqual([n for n, _ in cc.CANALES],
                         ["En el Local", "Delivery", "Para Llevar", "Rappi", "Pedidos Ya"])


class LoQueRecibeLaPieza(unittest.TestCase):
    def setUp(self):
        t, n = cc.preparar(carta(), incluir_inactivos=True)
        self.rango = (dt.date(2026, 10, 1), dt.date(2026, 10, 31))
        self.t, _ = cc.con_ventas(t, vendido(), rango=self.rango)
        self.pc = cc.ventas_por_canal(otros_canales(), self.rango)
        self.d = cc.armar_pieza(self.t, self.rango, self.pc, "0000001", n)
        self.filas = {f[0]: f for f in self.d["filas"]}

    def test_ventas_por_canal_del_rango(self):
        # La venta de Rappi de noviembre queda fuera del rango.
        self.assertEqual(self.pc, {"0000001": {"3": [2.0, 144.1, 56.7]},
                                   "0000002": {"4": [4.0, 29.0, 0.0]}})
        self.assertEqual(cc.ventas_por_canal(None, self.rango), {})
        self.assertEqual(cc.ventas_por_canal(otros_canales(), None), {})

    def test_la_fila_del_lomo(self):
        f = self.filas["0000001"]
        self.assertEqual(f[1:7], ["Alimentos", "Fondos", "Lomo", "Receta", 1, 1])
        self.assertEqual(f[10], [79.0, 79.0, 0.0, 89.0, 0.0])
        self.assertEqual(f[12:16], [15.0, 960.0, 425.25, 0.0])
        self.assertEqual(f[17], {"3": [2.0, 144.1, 56.7]})
        self.assertIsNone(f[16])

    def test_lo_vendido_por_canal_suma_el_total(self):
        # «En el Local» = el total menos los otros: 15 + 20 − 2 − 4.
        canales = dict(self.d["canales"])
        self.assertEqual(canales["En el Local"], 29)
        self.assertEqual((canales["Rappi"], canales["Pedidos Ya"], canales["Delivery"]), (2, 4, 0))

    def test_el_resto_del_contrato(self):
        self.assertEqual(self.d["sel"], "0000001")
        self.assertEqual(self.d["umbrales"], [30, 35])
        self.assertAlmostEqual(self.d["divisor"], 1.235)
        self.assertTrue(self.d["rango"].startswith("01/10/2026"))
        self.assertEqual(self.filas["0000003"][5], 0)

    def test_el_js_lee_las_mismas_posiciones(self):
        js = Path(cc.__file__).with_name("carta_costeada.js").read_text(encoding="utf-8")
        self.assertIn("const F = { cod: 0, grupo: 1, sub: 2, prod: 3, tipo: 4, activo: 5, oferta: 6, "
                      "desc: 7, receta: 8, ultima: 9,", js)
        self.assertIn("precios: 10, costos: 11, vend: 12, vneto: 13, vcosto: 14, sinc: 15, "
                      "combo: 16, otros: 17 };", js)
        # Lo del canal principal sale restando los otros, y el neto con el divisor.
        self.assertIn("u -= ou; neto -= on; costo -= oc;", js)
        self.assertIn("precio / d.divisor", js)


if __name__ == "__main__":
    unittest.main()
