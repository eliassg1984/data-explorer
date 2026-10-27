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
        self.assertEqual(r["no_vendido"], 150)
        self.assertEqual(r["carta"], 550)
        self.assertEqual(r["pos"], 510)
        self.assertEqual(r["diferencia"], 40)
        self.assertEqual(r["faltante"], 10)
        self.assertAlmostEqual(r["porcentaje"], 700 / 1200)
        self.assertIsNone(r["familias"][-1]["porcentaje"])
        self.assertIsNone(re.costo_del_mes(datos, "2026-08"))

    def test_clientes_ticket_descuentos_y_platos_sin_costo(self):
        cols = [dv.FECHA, re.PEDIDO, dv.LLAVE_DOC, dv.LLAVE_ITEM, dv.CLASE,
                dv.NETO_ITEM, dv.PAX, dv.CANAL, dv.CARTA_UNIT, dv.CANTIDAD,
                dv.DESCUENTO_ITEM, dv.COSTO, re.NOMBRE]
        filas = [
            # Mesa de 4 con dos formas de pago: los adultos, una vez.
            ("2026-09-01", "P1", "B1", "I1", dv.VENTA, 300, 4, "Salon", 100, 4, 54, 90, "Lomo"),
            ("2026-09-01", "P1", "B1", "I1", dv.VENTA, 300, 4, "Salon", 100, 4, 54, 90, "Lomo"),
            # Cuenta dividida: el mismo pedido, otro comprobante.
            ("2026-09-01", "P1", "B2", "I2", dv.VENTA, 100, 4, "Salon", 118, 1, 0, 0, "Agua"),
            # Rappi vende sin pax: suma a la venta, no al ticket.
            ("2026-09-02", "P2", "B3", "I3", dv.VENTA, 200, 0, "Rappi", 236, 1, 0, 0, "Pisco"),
            # Devolución parcial del agua: resta de su plato.
            ("2026-09-03", "P1", "N1", "I4", dv.NOTA_CREDITO, -40, -4, "Salon", 118, -1, 0, 0, "Agua"),
        ]
        d = pd.DataFrame(filas, columns=cols)
        r = re.ventas_del_rango(d, *re.rango_mes("2026-09"))
        self.assertEqual(r["venta"], 560)
        self.assertEqual(r["clientes"], 4)
        self.assertAlmostEqual(r["ticket"], 360 / 4)
        self.assertEqual(r["descuentos"], 54)
        self.assertAlmostEqual(r["pct_descuento"], 54 / (400 + 118 + 236 - 118))
        self.assertEqual(r["sin_costo"], 260)
        self.assertEqual([x["plato"] for x in r["sin_costo_top"]], ["Pisco", "Agua"])
        self.assertEqual(r["sin_costo_n"], 2)

    def test_costo_del_sistema_sobre_la_misma_venta(self):
        def serie(v):
            return {c: [v if c == "Alimentos" else 0] for c in cv.CUBETAS}
        datos = {"periodos": [{"k": "2026-09"}],
                 "filas": {k: serie(v) for k, v in {
                     "inv_inicial": 500, "compras": 400, "inv_final": 500,
                     "venta": 1000, "costo_pos": 300, "cortesias": 0}.items()}}
        r = re.costo_del_mes(datos, "2026-09")
        self.assertAlmostEqual(r["porcentaje"], 0.4)
        self.assertAlmostEqual(r["porcentaje_pos"], 0.3)
        self.assertAlmostEqual(r["porcentaje_faltante"], 0.1)

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


def _mes(k, venta, ppto=None, ap=None, parcial=False, costo=None, **otros):
    """Un mes de `historia`, para armar casos a mano."""
    h = {"k": k, "parcial": parcial, "venta": venta, "ppto": ppto, "costo": costo,
         "ap": {"venta": ap} if ap is not None else None}
    for c in re.CIFRAS:
        h.setdefault(c, otros.get(c))
    h["venta"] = venta
    return h


class PortadaDoceMesesTest(unittest.TestCase):
    """La portada de la regla #745: doce meses, presupuesto, frase y lista."""

    def test_meses_con_la_misma_cuenta_que_el_rango(self):
        filas = [("2026-08-31", "P1", "B1", "I1", dv.VENTA, 100),
                 ("2026-09-01", "P2", "B2", "I2", dv.VENTA, 50),
                 ("2026-09-01", "P2", "B2", "I2", dv.VENTA, 50),   # dos pagos
                 ("2026-09-15", "P3", "N1", "I3", dv.NOTA_CREDITO, -20)]
        d = pd.DataFrame(filas, columns=[dv.FECHA, re.PEDIDO, dv.LLAVE_DOC,
                                        dv.LLAVE_ITEM, dv.CLASE, dv.NETO_ITEM])
        m = re.ventas_por_mes(d)
        self.assertEqual(sorted(m), ["2026-08", "2026-09"])
        self.assertEqual(m["2026-09"]["venta"],
                         re.ventas_del_rango(d, *re.rango_mes("2026-09"))["venta"])
        self.assertEqual(m["2026-09"]["venta"], 30)
        self.assertEqual(set(m["2026-08"]), set(re.CIFRAS))
        self.assertEqual(re.ventas_por_mes(None), {})

    def test_presupuesto_por_mes_y_por_dia(self):
        tabla = pd.DataFrame({"anio": [2026, 2026, 2026], "mes": [9, 9, 10],
                              "servicio": ["ALMUERZO", "CENA", "CENA"],
                              "bruta": [130, 260, 1], "neta": [100, 200, 0]})
        self.assertEqual(re.presupuesto_por_mes(tabla), {"2026-09": 300.0})
        diario = pd.DataFrame({"dia": pd.to_datetime(["2026-09-01", "2026-09-01", "2026-09-03"]),
                               "servicio": ["ALMUERZO", "CENA", "CENA"], "neta": [10.0, 20.0, 5.0]})
        self.assertEqual(re.presupuesto_dias(diario, dt.date(2026, 9, 1), dt.date(2026, 9, 3)),
                         [30.0, 0.0, 5.0])
        self.assertIsNone(re.presupuesto_dias(diario, dt.date(2026, 10, 1), dt.date(2026, 10, 2)))
        self.assertEqual(re.presupuesto_por_mes(None), {})

    def test_ano_pasado_diario_cae_en_el_mismo_dia_de_la_semana(self):
        ini, fin = re.rango_mes("2026-09")
        a, b = re.alinear_ano_pasado(ini, fin)
        self.assertEqual((a, b), (dt.date(2025, 9, 2), dt.date(2025, 10, 1)))
        self.assertEqual(a.weekday(), ini.weekday())
        grupos = pd.DataFrame({"dia": pd.to_datetime(["2025-09-02", "2025-09-02", "2025-09-03"]),
                               "clase": [dv.VENTA, dv.CORTESIA, dv.VENTA], "neto": [10.0, 99.0, 5.0]})
        self.assertEqual(re.venta_diaria(grupos, dt.date(2025, 9, 2), dt.date(2025, 9, 4)),
                         [10.0, 5.0, 0.0])
        # Un día antes del parquet no es un cero.
        self.assertIsNone(re.venta_diaria(grupos, dt.date(2025, 9, 1), dt.date(2025, 9, 3)))

    def test_historia_toma_el_tramo_del_mes_en_curso(self):
        ventas = {"2026-09": {"venta": 300}, "2025-09": {"venta": 250}, "2025-10": {"venta": 200}}
        h = re.historia("2026-10", ventas, None, {"2026-09": 400, "2026-10": 900},
                        actual={"venta": 120}, anterior={"venta": 100},
                        ppto_tramo=[50.0, 50.0], parcial=True)
        self.assertEqual(len(h), re.MESES_HISTORIA)
        self.assertEqual([x["k"] for x in h][-2:], ["2026-09", "2026-10"])
        self.assertEqual((h[-1]["venta"], h[-1]["ap"]["venta"], h[-1]["ppto"]), (120, 100, 100.0))
        self.assertTrue(h[-1]["parcial"])
        self.assertEqual((h[-2]["venta"], h[-2]["ap"]["venta"], h[-2]["ppto"]), (300, 250, 400))
        # Sin presupuesto de esos días, un mes en curso no se compara con el mes entero.
        h = re.historia("2026-10", ventas, None, {"2026-10": 900}, actual={"venta": 120},
                        parcial=True)
        self.assertIsNone(h[-1]["ppto"])

    def test_habitual_es_la_mediana_de_seis_meses_anteriores(self):
        h = [_mes(f"2026-{i:02d}", 1, ticket=t) for i, t in enumerate(
            [999, 100, 110, 120, 130, 140, 150, 60], start=1)]
        self.assertEqual(re.habitual(h, "ticket"), 125)
        self.assertIsNone(re.habitual(h[-3:], "ticket"))

    def test_titular_dice_presupuesto_ano_pasado_y_racha(self):
        meses = ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07",
                 "2026-08", "2026-09"]
        ventas, ap = [96, 88, 72, 83, 74, 56, 68, 89], [100] * 8
        h = [_mes(k, v, ap=a) for k, v, a in zip(meses, ventas, ap)]
        h[-1]["ppto"] = 125.0
        costo = {"porcentaje": 0.40}
        t = "".join(x for x, _c in re.titular("2026-09", h, costo, {"porcentaje": 0.42},
                                               False, dt.date(2026, 9, 30)))
        self.assertIn("Setiembre cerró en S/ 89", t)
        self.assertIn("71% del presupuesto", t)
        self.assertIn("11.0% menos que setiembre 2025", t)
        self.assertIn("la caída más chica desde febrero", t)
        self.assertIn("bajó a 40.0%", t)
        clases = dict((x, c) for x, c in re.titular("2026-09", h, costo, None, False,
                                                     dt.date(2026, 9, 30)))
        self.assertEqual(clases["71% del presupuesto"], "bad")
        # En curso: el costo espera el cierre.
        h[-1]["parcial"] = True
        t = "".join(x for x, _c in re.titular("2026-09", h, None, None, True, dt.date(2026, 9, 16)))
        self.assertTrue(t.startswith("Al 16 de setiembre van"))
        self.assertIn("espera el cierre", t)
        self.assertEqual(re.titular("2026-09", [_mes("2026-09", None)], None, None, False,
                                    dt.date(2026, 9, 30)), [])

    def test_sin_explicar_con_la_regla_de_pendientes(self):
        """La portada y Pendientes juzgan lo sin explicar igual: no puede
        salir ámbar arriba y verde abajo."""
        import pendientes
        meses = [("2026-04", 4513, 282000), ("2026-05", 9764, 321000),
                 ("2026-06", 2533, 291000), ("2026-07", 39757, 213000),
                 ("2026-08", 10682, 283000), ("2026-09", 10202, 325180)]
        costo = {"porcentaje": 0.40, "porcentaje_faltante": 10202 / 325180, "faltante": 10202,
                 "carta": 120697, "pos": 109423, "bajas": 1071, "observaciones": {}}
        h = [_mes("2026-09", 1)]
        items = re.para_revisar("2026-09", h, {}, costo, None, meses, False)
        portada = next(x for x in items if x["t"].startswith("Sin explicar"))
        fila = pendientes.de_costos([(k, f, v) for k, f, v in meses])
        self.assertEqual(portada["nivel"] == re.VERDE, fila["estado"] == pendientes.VERDE)
        self.assertEqual(portada["nivel"], re.VERDE)
        raro = re.para_revisar("2026-07", h, {}, dict(costo, porcentaje_faltante=0.187,
                                                      faltante=39757), None, meses[:4], False)
        self.assertEqual(next(x for x in raro if x["t"].startswith("Sin explicar"))["nivel"],
                         re.ROJO)

    def test_senales_de_presupuesto_ticket_y_orden(self):
        h = [_mes(f"2026-{i:02d}", 100, ppto=100, ticket=130) for i in range(3, 9)]
        h.append(_mes("2026-09", 71, ppto=100, ticket=110))
        items = re.para_revisar("2026-09", h, {"sin_costo_pct": 0.065, "sin_costo": 21636,
                                               "sin_costo_top": [{"plato": "Agua"}],
                                               "sin_costo_n": 3}, None, None, [], False)
        titulos = [x["t"] for x in items]
        self.assertEqual(items[0]["nivel"], re.ROJO)
        self.assertEqual(titulos[0], "La venta quedó lejos del presupuesto")
        self.assertIn("71% · −S/ 29", items[0]["chip"])
        self.assertIn("El ticket está 15% bajo lo habitual", titulos)
        sc = next(x for x in items if x["t"] == "Vendido sin costo en el POS")
        self.assertIn("Agua y 2 más.", sc["det"][0])
        self.assertTrue(all(x["ir"] in ("comparativo", "ventas", "platos", "costos") for x in items))
        self.assertEqual([x["nivel"] for x in items],
                         sorted((x["nivel"] for x in items), key=re._ORDEN.get))
        cumplido = re.para_revisar("2026-09", [_mes("2026-09", 120, ppto=100)], {}, None,
                                   None, [], False)
        self.assertEqual((cumplido[0]["t"], cumplido[0]["nivel"]), ("Presupuesto cumplido", re.VERDE))

    def test_de_pendientes_deja_afuera_lo_sin_explicar(self):
        import pendientes
        armado = pendientes.armar({"pesos": {"n": 3, "docs": 2},
                                   "costos": [("ago", 100.0, 1000.0)] * 4,
                                   "horas": {"ventas.parquet": 1.0}}, 26)
        items, al_dia, sin = re.de_pendientes(armado)
        self.assertEqual([x["t"] for x in items], ["Peso por unidad raro"])
        self.assertEqual(items[0]["destino"]["v"], pendientes.REVISAR_MERMA[2])
        self.assertIn("Parquets sin refrescar", al_dia)
        self.assertNotIn("Sin explicar del último mes", al_dia)
        self.assertEqual(sin, 10)

    def test_la_vista_salta_con_volver_y_destinos_validados(self):
        """Los enlaces entran en la misma pestaña: el callback captura el
        origen ANTES de saltar y sólo acepta destinos que armó Python; el
        .js lee las claves que Python manda."""
        import ast
        from pathlib import Path
        raiz = Path(__file__).parent
        src = (raiz / "graficos" / "resumen_ejecutivo.py").read_text(encoding="utf-8")
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == "_al_ir")
        cuerpo = ast.unparse(fn)
        self.assertLess(cuerpo.index("capturar_origen()"), cuerpo.index("_ir_a_vista("))
        self.assertIn("_K_DESTINOS", cuerpo)
        self.assertIn("aplicar_atajo(", cuerpo)
        self.assertIn("K_MES_DESDE_RESUMEN", cuerpo)
        js = (raiz / "graficos" / "resumen_ejecutivo.js").read_text(encoding="utf-8")
        for clave in ("d.titular", "d.hist", "d.diario", "d.items", "d.al_dia", "d.sin_calcular",
                      "d.calculable", "d.destinos", "d.habitual", "d.costo_ap"):
            self.assertIn(clave, js)
        for trigger in ("'ir'", "'mes'", "'calcular'"):
            self.assertIn(f"setTriggerValue({trigger}", js)
        self.assertNotIn('target="_blank"', js)
        from graficos import costos
        self.assertTrue(costos.K_MES_DESDE_RESUMEN)


if __name__ == "__main__":
    unittest.main()
