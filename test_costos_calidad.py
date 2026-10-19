"""Cobertura, alertas y denominadores del reporte Costos; datos sintéticos."""
import unittest
from urllib.parse import parse_qs

import pandas as pd

import costo_ventas as cv
import costos_calidad as calidad
import costos_enlaces
import definicion_venta as dv


class CalidadCostos(unittest.TestCase):
    def cierres(self):
        return pd.DataFrame([
            {"FECHA APERTURA INVENTARIO": fecha, "CODIGO AREA": area, "AREA": area,
             "FAMILIA": "ALIMENTOS", "VALORIZADO TOTAL": valor,
             "STOCK DECLARADO": cantidad, "PRECIO PROMEDIO": precio,
             "CODIGO PRODUCTO": producto, "PRODUCTO": producto, "CODIGO CIERRE": cierre}
            for fecha, area, valor, cantidad, precio, producto, cierre in [
                ("2024-01-02", "A", 100, 10, 10, "Uno", "C1"),
                ("2024-01-02", "A", 0, 2, 0, "Dos", "C1"),
                ("2024-02-01", "A", -10, -1, 10, "Uno", "C2"),
                ("2024-02-01", "Z", 0, 0, 0, "Tres", "C3"),
                ("2024-03-01", "A", 80, 8, 10, "Uno", "C4"),
            ]])

    def test_alerta_de_ambas_puntas_y_area_cero_no_faltante(self):
        r = calidad.inventarios(self.cierres(), [pd.Period("2024-01"), pd.Period("2024-02")])
        enero, febrero = r["2024-01"], r["2024-02"]
        self.assertEqual(enero["familias"]["Alimentos"]["sin_precio"], 1)
        self.assertEqual(enero["familias"]["Alimentos"]["negativos"], 1)
        self.assertEqual(febrero["familias"]["Alimentos"]["negativos"], 1)
        self.assertEqual(febrero["areas_sin_cierre_final"], [])
        self.assertEqual(febrero["detalle"][0]["punta"], "Inicial")
        self.assertEqual(enero["familias"]["Vinos"]["sin_precio"], 0)

    def test_mes_2024_no_depende_del_ajuste_y_no_inventa_ventas(self):
        cierres = self.cierres().assign(**{"AJUSTE VALORIZADO": 999999})
        pgd = pd.DataFrame({"dia": pd.to_datetime(["2024-01-10"]),
                            "grupo": ["Alimentos"], "clase": [dv.VENTA],
                            "neto": [200], "costo": [70]})
        d = cv.armar(cierres, None, None, pgd)
        self.assertEqual([p["k"] for p in d["periodos"]], ["2024-01"])
        self.assertEqual(d["filas"]["inv_inicial"]["Alimentos"], [100])
        self.assertEqual(d["filas"]["inv_final"]["Alimentos"], [-10])
        self.assertEqual(cv.armar(cierres, None, None, pgd.iloc[:0])["periodos"], [])
        self.assertEqual(cv.DESDE, pd.Period("2025-10"))

    def test_parcial_no_es_inventario_final(self):
        cierres = self.cierres()
        cierres.loc[cierres["FECHA APERTURA INVENTARIO"] == "2024-03-01", "FECHA APERTURA INVENTARIO"] = "2024-02-16"
        pgd = pd.DataFrame({"dia": pd.to_datetime(["2024-02-20"]), "grupo": ["Alimentos"],
                            "clase": [dv.VENTA], "neto": [10], "costo": [3]})
        self.assertEqual(cv.armar(cierres, None, None, pgd)["periodos"], [])

    def test_cobertura_documental_no_filtra_pendientes_ni_suma_solo_sistema(self):
        d = pd.DataFrame({"estado": ["Coincide", "Diferencia", "Solo SUNAT", "Solo SUNAT", "Solo sistema"],
                          "total_sunat": [100, 200, 80, -10, None]})
        r = calidad.cobertura_documental(d)
        self.assertEqual(r["documentos"], 4)
        self.assertEqual(r["ubicados"], 2)
        self.assertEqual(r["cobertura"], .5)
        self.assertEqual(r["sin_coincidencia"], 2)
        self.assertEqual(r["importe_positivo_sin_coincidencia"], 80)
        self.assertEqual(r["importe_notas_sin_coincidencia"], 10)
        self.assertFalse(calidad.cobertura_documental(d.iloc[:0])["disponible"])

    def test_calidad_venta_se_cuenta_antes_de_agrupar_sin_duplicar_pagos(self):
        d = pd.DataFrame({dv.FECHA: pd.to_datetime(["2024-01-10"] * 4), dv.GRUPO: ["Alimentos"] * 4,
                          dv.CLASE: [dv.VENTA, dv.VENTA, dv.VENTA, dv.CORTESIA],
                          dv.LLAVE_ITEM: ["I1", "I1", "I2", "I3"],
                          dv.NETO_ITEM: [20, 20, 30, 0], dv.COSTO: [None, None, 10, 0],
                          dv.CANTIDAD: [1, 1, 1, 1]})
        agrupado = dv.por_grupo_dia(d)
        self.assertEqual(agrupado["lineas_sin_costo"].sum(), 1)
        self.assertEqual(agrupado["venta_sin_costo"].sum(), 20)
        self.assertEqual(calidad.ventas(agrupado, [pd.Period("2024-01")])["2024-01"][0]["sin_costo"], 1)

    def test_enlace_documental_conserva_mes_y_valida_destino(self):
        enlace = costos_enlaces.enlaces({"mes": {"periodos": [{"k": "2024-02"}], "salidas": {}}})["mes"]["2024-02"]["documental"]
        params = {k: v[0] for k, v in parse_qs(enlace["url"][1:]).items()}
        ini, fin = costos_enlaces._contexto(params, "Documentos SUNAT")
        self.assertEqual(str(ini), "2024-02-01")
        self.assertEqual(str(fin), "2024-02-29")
        self.assertIsNone(costos_enlaces._contexto(params, "Ventas"))


if __name__ == "__main__":
    unittest.main()
