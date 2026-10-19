"""Contexto del clic y cuentas compartidas entre mapa y detalle horario."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from graficos import ventas_hora_detalle as detalle
from graficos import ventas_horario as horario


class DetalleHorario(unittest.TestCase):
    def setUp(self):
        self.tramo = pd.DataFrame({
            "dia": pd.to_datetime(["2026-10-01", "2026-10-01", "2026-10-02",
                                    "2026-10-02", "2026-10-03"]),
            "hora": [19, 20, 19, 0, 19], "dow": [3, 3, 4, 4, 5],
            "prod": ["Lomo", "Lomo", "Lomo", "Pisco", "Pisco"],
            "grupo": ["Alimentos", "Alimentos", "Alimentos", "Bebidas", "Bebidas"],
            "canal": ["Local", "Local", "Rappi", "Local", "Local"],
            "ped": ["1", "2", "3", "4", "5"],
            "venta": [100., 90., 50., 30., 120.],
            "cant": [1., 1., 2., 4., 6.], "desc": [10., 0., 5., 0., 10.]})

    def evento(self, periodo, columna):
        return {"selection": {"points": [{"customdata":
                ["Lomo", "Período", "Hora", "Venta", "", periodo, columna]}]}}

    def test_clic_conserva_periodo_y_hora_incluida_medianoche(self):
        horas = [19, 20, 0]
        seleccion = horario._seleccion_fila(self.evento(1, 2), horas, "prod")
        self.assertEqual(seleccion, {"que": "prod", "nombre": "Lomo",
                                    "sel": 1, "c": 2, "hora": 0})
        self.assertIsNone(horario._seleccion_fila(self.evento(1, 8), horas, "prod"))

    def test_otra_hora_actualiza_y_no_cierra(self):
        state = {"clic_0": self.evento(0, 0)}
        with patch.object(horario, "st", SimpleNamespace(session_state=state)):
            horario._clic_filas("clic", [19, 20], "prod")
            state["clic_1"] = self.evento(1, 1)
            horario._clic_filas("clic", [19, 20], "prod")
        self.assertEqual(state[horario._K_FICHA], "Lomo")
        self.assertEqual(state[horario._K_CELDA_FILA]["hora"], 20)
        self.assertEqual(state[horario._K_CELDA_FILA]["sel"], 1)

    def test_valor_de_celda_y_divisor_del_mapa(self):
        d = detalle.preparar(self.tramo, "prod", "Lomo", 19, "venta", True)
        matriz = horario._matriz_filas(self.tramo, "prod", ["Lomo"], True,
                                       "venta", [19, 20, 0], True)
        self.assertEqual(d["valores"]["venta"], matriz[0, 0])
        self.assertEqual(d["dias"], 3)  # incluye el día en que sólo vendió Pisco
        self.assertEqual(d["diario"].tolist(), [100., 50., 0.])
        self.assertEqual(d["participacion"], 150 / 270 * 100)

    def test_perfil_amplia_horas_sin_ampliar_el_periodo(self):
        celda = detalle.preparar(self.tramo, "prod", "Lomo", 19)
        perfil = detalle.preparar(self.tramo, "prod", "Lomo")
        self.assertEqual(celda["totales"]["venta"], 150)
        self.assertEqual(perfil["totales"]["venta"], 240)
        otro_periodo = self.tramo.assign(venta=lambda d:d.venta * 10)
        self.assertEqual(detalle.preparar(otro_periodo, "prod", "Lomo", 19)
                         ["totales"]["venta"], 1500)

    def test_grupo_y_pedidos_suman_solo_los_items_de_esa_hora(self):
        d = detalle.preparar(self.tramo, "grupo", "Alimentos", 19)
        self.assertEqual(d["platos"]["Nombre"].tolist(), ["Lomo"])
        self.assertEqual(d["pedidos"]["Venta"].sum(), 150)
        self.assertEqual(set(d["pedidos"]["Hora"]), {19})
        self.assertEqual(d["canales"]["Valor"].sum(), 150)

    def test_orden_y_puesto_siguen_la_medida(self):
        datos = detalle.preparar(self.tramo, "prod", "Lomo", None, "cant")
        self.assertEqual(datos["puesto"], 2)
        self.assertEqual(horario._items_filas([self.tramo], "prod", "cant"),
                         ["Pisco", "Lomo"])

    def test_abrir_plato_de_grupo_conserva_hora_periodo_y_perfil(self):
        celda = {"que": "grupo", "nombre": "Alimentos", "sel": 1,
                 "c": 2, "hora": 0}
        state = {horario._K_CELDA_FILA: celda, horario._K_PERFIL_FILA: True}
        with patch.object(horario, "st", SimpleNamespace(session_state=state)):
            horario._ver_producto_fila("Lomo")
        self.assertEqual(state[horario._K_CELDA_FILA],
                         dict(celda, que="prod", nombre="Lomo"))
        self.assertTrue(state[horario._K_PERFIL_FILA])
        self.assertEqual(state["vh_op_filas"], state["vh_filas_aplicada"])
        self.assertEqual(state[horario._K_FICHA], "Lomo")

    def test_vacio_no_recupera_datos_de_otro_contexto(self):
        d = detalle.preparar(self.tramo.iloc[:0], "grupo", "Alimentos", 19)
        self.assertEqual(d["totales"]["venta"], 0)
        self.assertTrue(d["pedidos"].empty)
        self.assertIsNone(d["participacion"])
        with self.assertRaises(ValueError):
            detalle.preparar(self.tramo, "prod", "Lomo", 19, "pax")


if __name__ == "__main__":
    unittest.main()
