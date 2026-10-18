"""Filtros compartidos y regresiones al alternar los modos horarios."""
import unittest
from unittest.mock import patch

import pandas as pd

from graficos import ventas_franja as franja
from graficos.ventas_hora_controles import filtrar


class ContextoHorario(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "Canal Venta": ["En el Local", "Rappi", "En el Local", "Rappi"],
            "Grupo": ["Alimentos", "Alimentos", "Venta Interna", "Eventos"],
            "Sub Grupo": ["Fondos", "Pizzas", "Charcutería", "Eventos"],
            "Venta": [100, 80, 40, 200]})

    def test_interseccion_canal_ambito_y_exclusion(self):
        resultado = filtrar(self.df, canales=("Rappi",),
                            ambito="Grupo: Alimentos", incluir=False)
        self.assertEqual(resultado["Venta"].sum(), 80)
        self.assertEqual(list(self.df.index), [0, 1, 2, 3])

    def test_sin_venta_no_se_convierte_en_todos(self):
        self.assertTrue(filtrar(self.df, canales=("Canal sin ventas",)).empty)
        self.assertTrue(filtrar(self.df, ambito="Subgrupo: Inexistente").empty)

    def test_excluir_eventos_no_excluye_rappi(self):
        resultado = filtrar(self.df, incluir=False)
        self.assertEqual(resultado["Venta"].sum(), 180)
        self.assertIn("Rappi", resultado["Canal Venta"].values)

    def test_franja_vacia_no_recupera_ventas_de_otro_rango(self):
        from datetime import date
        with patch.object(franja, "cargar_rango", return_value=self.df.iloc[:0]):
            resultado = franja._cargar(date(2026, 10, 1), date(2026, 10, 2),
                                      False, lambda df:df, self.df)
        self.assertTrue(resultado.empty)

    def test_cargar_por_la_base_temporal_elegida(self):
        from datetime import date
        df = self.df.assign(**{"Fecha Registro Pedido": pd.Timestamp("2026-10-01"),
                               "Fec Reg Documento": pd.Timestamp("2026-10-02")})
        with patch.object(franja, "cargar_rango", return_value=df) as cargar:
            franja._cargar(date(2026, 10, 1), date(2026, 10, 2), False,
                           lambda x:x, df, base="Hora del cobro")
        self.assertEqual(cargar.call_args.args[1], "FEC REG DOCUMENTO")


if __name__ == "__main__":
    unittest.main()
