"""Ventas › «Venta por Periodo» como pieza propia (regla #714).

Lo que recibe la pieza (`lineas_normalizadas`, `armar_periodo`,
`pagos_periodo`) y que el navegador haga las MISMAS cuentas que Python:
`calcular` de `ventas_periodo.js` contra `definicion_venta` (clientes,
comprobantes, ticket) y contra los ayudantes puros de `ventas_resumen.py`
(formas de pago, IGV, lo vendido sin costo), en Chromium, día por día y
semana por semana. Sin secrets ni red; la parte de Chromium se salta si
Playwright no está (es de requirements-dev.txt).

    python test_ventas_periodo.py
"""

import json
import unittest
from pathlib import Path

import pandas as pd

import definicion_venta as dv
from graficos import ventas_resumen as vr

_JS = (Path(vr.__file__).parent / "ventas_periodo.js").read_text(encoding="utf-8")
V, NC, CO, AN = dv.VENTA, dv.NOTA_CREDITO, dv.CORTESIA, dv.ANULADO

# Una línea por ítem, con los nombres del parquet. Los casos: el canje de
# boleta por factura (B1, F1 y la nota N1 del mismo pedido), una cuenta
# dividida en dos boletas (B3, B4), Rappi sin clientes, una cortesía, un
# anulado, un descuento, un plato sin costo y otro con costo mayor a su
# precio, un comprobante con dos grupos, y dos semanas.
_FILAS = [
    # ldoc, num, tipo, clase, fecha (turno), ped, pax, niños, grupo, plato, cant, venta, precio, neto, desc, costo u., igv, canal, serv, mesero
    ("L1", "B00001000000001", "Boleta Electronica", V, "2026-10-05 13:10", "P1", 2, 1, "Fondos", "Lomo", 1, 59.0, 59.0, 47.8, 0.0, 20.0, 5.0, "En el Local", "ALMUERZO", "ANA RUIZ"),
    ("L1", "B00001000000001", "Boleta Electronica", V, "2026-10-05 13:10", "P1", 2, 1, "Bebidas", "Agua", 2, 10.0, 6.0, 8.1, 2.0, 0.0, 0.85, "En el Local", "ALMUERZO", "ANA RUIZ"),
    ("L2", "F00001000000002", "Factura Electronica", V, "2026-10-06 20:00", "P2", 4, 0, "Fondos", "Pato", 2, 160.0, 80.0, 129.6, 0.0, 90.0, 13.0, "En el Local", "CENA", "BETO SOL"),
    ("L3", "B00001000000003", "Boleta Electronica", V, "2026-10-06 21:00", "P3", 3, 0, "Fondos", "Lomo", 1, 59.0, 59.0, 47.8, 0.0, 20.0, 5.0, "En el Local", "CENA", "ANA RUIZ"),
    ("L4", "B00001000000004", "Boleta Electronica", V, "2026-10-06 21:05", "P3", 3, 0, "Fondos", "Pato", 1, 80.0, 80.0, 64.8, 0.0, 90.0, 6.5, "En el Local", "CENA", "ANA RUIZ"),
    ("L5", "B00001000000005", "Boleta Electronica", V, "2026-10-07 13:00", "P4", 2, 0, "Fondos", "Lomo", 1, 59.0, 59.0, 47.8, 0.0, 20.0, 5.0, "En el Local", "ALMUERZO", "BETO SOL"),
    ("L6", "F00001000000006", "Factura Electronica", V, "2026-10-08 13:00", "P4", 2, 0, "Fondos", "Lomo", 1, 59.0, 59.0, 47.8, 0.0, 20.0, 5.0, "En el Local", "ALMUERZO", "BETO SOL"),
    ("L7", "NC0001000000007", "NC B Electronica", NC, "2026-10-08 13:01", "P4", -2, 0, "Fondos", "Lomo", -1, -59.0, 59.0, -47.8, 0.0, 20.0, -5.0, "En el Local", "ALMUERZO", "BETO SOL"),
    ("L8", "B00001000000008", "Boleta Electronica", V, "2026-10-08 19:00", "P5", 0, 0, "Fondos", "Lomo", 1, 59.0, 59.0, 47.8, 0.0, 20.0, 5.0, "Rappi", "DELIVERY", ""),
    ("L9", "000001000000009", "Cortesia", CO, "2026-10-09 20:00", "P6", 2, 0, "Postres", "Flan", 1, 0.0, 25.0, 0.0, 0.0, 6.0, 0.0, "En el Local", "CENA", "ANA RUIZ"),
    ("L10", "B00001000000010", "Boleta Electronica", AN, "2026-10-09 21:00", "P7", 2, 0, "Fondos", "Pato", 1, 80.0, 80.0, 64.8, 0.0, 90.0, 6.5, "En el Local", "CENA", "ANA RUIZ"),
    ("L11", "B00001000000011", "Boleta Electronica", V, "2026-10-13 13:00", "P8", 5, 0, "Fondos", "Lomo", 2, 118.0, 59.0, 95.6, 0.0, 20.0, 10.0, "En el Local", "ALMUERZO", "ANA RUIZ"),
]
_COLS = ["LLAVE LOCAL DOCUMENTO", "NUMERO DOCUMENTO", "TIPO DOC", dv.CLASE, "FEC REG DOCUMENTO", "LLAVE LOCAL PEDIDO",
         "CANT PAX", dv.NINOS, "GRUPO", "NOMB ITEM VENTA", "CANTIDAD ITEM DDOCUMENTO", "VENTA ITEM DDOCUMENTO",
         "PRECIO OFICIAL ITEM DDOCUMENTO", "NETO TOTAL ITEM DDOCUMENTO", "DESCUENTO ITEM DDOCUMENTO", "PRECIO COSTO",
         "IGV ITEM DDOCUMENTO", "CANAL VENTA", "SERVICIO", "NOMBRE MESERO"]
_CLAVES = {"venta": "VENTA ITEM DDOCUMENTO", "fecha": "FEC REG DOCUMENTO", "pax": "CANT PAX", "pedido": "LLAVE LOCAL PEDIDO",
           "prod": "NOMB ITEM VENTA", "cant": "CANTIDAD ITEM DDOCUMENTO", "fam": "GRUPO", "serv": "SERVICIO",
           "canal": "CANAL VENTA", "mesero": "NOMBRE MESERO"}


def _ventas():
    d = pd.DataFrame(_FILAS, columns=_COLS)
    d["FEC REG DOCUMENTO"] = pd.to_datetime(d["FEC REG DOCUMENTO"])
    return d


def _pagos():
    # Un pago por fila; la propina va en el pago. L1 se pagó en dos formas.
    return pd.DataFrame({
        "LLAVE LOCAL DOCUMENTO": ["L1", "L1", "L2", "L3", "L4", "L5", "L6", "L8", "L10", "L11"],
        "LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO": ["L1-1", "L1-2", "L2-1", "L3-1", "L4-1", "L5-1", "L6-1", "L8-1", "L10-1", "L11-1"],
        "MONTO TIPO PAGO DOC": [40.0, 29.0, 160.0, 59.0, 80.0, 59.0, 59.0, 59.0, 80.0, 118.0],
        "MONTO PROPINA": [5.0, 0.0, 16.0, 0.0, 6.0, 0.0, 0.0, 0.0, 9.0, 12.0],
        "NOMBRE TIPO PAGO": ["Efectivo", "Tarjeta de Crédito", "Tarjeta de Crédito", "Efectivo", "Efectivo", "Efectivo",
                             "Efectivo", "Varios", "Efectivo", "Tarjeta de Crédito"],
        "NOMBRE TARJETA PAGO": ["", "VISA", "AMERICAN EXPRESS", "", "", "", "", "", "", "VISA"],
        "NOMBRE OTRO TIPO PAGO DOC": ["", "", "", "", "", "", "", "RAPPI", "", ""],
        "FEC REG DOCUMENTO": pd.to_datetime(["2026-10-05"] * 2 + ["2026-10-06"] * 3 + ["2026-10-07", "2026-10-08", "2026-10-08", "2026-10-09", "2026-10-13"]),
        dv.CLASE: [V, V, V, V, V, V, V, V, AN, V],
    })


def _armar():
    t = vr.lineas_normalizadas(_ventas(), _CLAVES)
    P = vr.armar_periodo(t, vr.sello_periodo(t), 196, 380, 250)
    idoc = {k: i for i, k in enumerate(t.drop_duplicates("ldoc")["ldoc"])}
    P["pagos"], P["formas"] = vr.pagos_periodo(_pagos(), "FEC REG DOCUMENTO", idoc)
    P["turno"], P["franja"] = True, []
    return t, P


class LoQueRecibe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t, cls.P = _armar()

    def test_un_comprobante_por_fila_con_su_clase_y_su_pax(self):
        P = self.P
        self.assertEqual(len(P["docs"]), 11)
        nc = [d for d in P["docs"] if d[2] == vr._CLASES.index(NC)]
        self.assertEqual(len(nc), 1)
        self.assertEqual(nc[0][10], -2.0)
        self.assertEqual(P["tdocs"][nc[0][1]], "NC B Electronica")

    def test_las_unidades_suman_lo_mismo_que_las_lineas(self):
        P, t = self.P, self.t
        self.assertAlmostEqual(sum(u[2] for u in P["unidades"]), t["venta"].sum())
        self.assertAlmostEqual(sum(u[3] for u in P["unidades"]), (t["po"] * t["cant"]).sum())
        self.assertAlmostEqual(sum(u[6] for u in P["unidades"]), (t["pc"] * t["cant"]).sum())
        # L1 tiene dos grupos: dos unidades; el agua lleva el descuento.
        l1 = [u for u in P["unidades"] if P["docs"][u[0]][0] == "B00001000000001"]
        self.assertEqual(sorted(P["grupos"][u[1]] for u in l1), ["Bebidas", "Fondos"])
        self.assertEqual([u[9] for u in l1 if P["grupos"][u[1]] == "Bebidas"], [1])
        # Lo vendido sin costo (el agua) y lo vendido por encima de su precio (el pato).
        self.assertEqual({P["prods"][x[1]] for x in P["sinc"]}, {"Agua"})
        self.assertEqual({P["prods"][x[1]] for x in P["culp"]}, {"Pato"})

    def test_un_rango_corto_lleva_todas_sus_lineas(self):
        self.assertEqual(self.P["lineas_desde"], 0)
        self.assertEqual(len(self.P["lineas"]), len(self.t))

    def test_un_rango_largo_lleva_las_de_los_ultimos_dias(self):
        d = _ventas()
        viejo = d.iloc[[0]].copy()
        viejo["FEC REG DOCUMENTO"] = pd.Timestamp("2026-01-05 13:00")
        viejo["LLAVE LOCAL DOCUMENTO"] = "L0"
        t = vr.lineas_normalizadas(pd.concat([viejo, d], ignore_index=True), _CLAVES)
        P = vr.armar_periodo(t, "x", 196, 380, 250)
        self.assertGreater(P["lineas_desde"], 0)
        self.assertNotIn("L0", {P["docs"][x[0]][0] for x in P["lineas"]})
        self.assertEqual(len(P["unidades"]), len(_armar()[1]["unidades"]) + 1)

    def test_los_pagos_una_vez_con_su_forma(self):
        P = self.P
        self.assertEqual(len(P["pagos"]), 10)
        formas = {P["formas"][p[3]] for p in P["pagos"]}
        self.assertTrue({"Efectivo", "VISA", "Amex", "RAPPI"} <= formas, formas)
        json.dumps(P)

    def test_el_js_lee_las_mismas_posiciones(self):
        self.assertIn("i, num: d[0], tdoc: D.tdocs[d[1]], clase: d[2], porCobrar: d[3], fecha: d[4], emision: d[5],", _JS)
        self.assertIn("ped: d[6], canal: D.canales[d[7]], serv: D.servs[d[8]], mesero: D.meseros[d[9]], pax: d[10], ninos: d[11],", _JS)
        self.assertIn("doc: docs[u[0]], grupo: D.grupos[u[1]], venta: u[2], carta: u[3], neto: u[4],", _JS)
        self.assertIn("desc: u[5], costo: u[6], sinCosto: u[7], n: u[8], tdesc: u[9]", _JS)
        self.assertIn("const linea = (l) => ({ doc: docs[l[0]], prod: D.prods[l[1]], grupo: D.grupos[l[2]], cant: l[3], venta: l[4] });", _JS)
        self.assertIn("const VENTA = 0, NC = 1, CORTESIA = 2, ANULADO = 3;", _JS)
        self.assertEqual(vr._CLASES, (V, NC, CO, AN))

    def test_el_js_cuenta_como_definicion_venta(self):
        # Clientes: un valor por pedido, y la nota RESTA (pax_por).
        self.assertIn("const dif = e.pos.size - e.neg.size, v = dif > 0 ? e.mp : dif < 0 ? e.mn : 0;", _JS)
        # Ticket: sólo los canales que registran clientes (con_clientes).
        self.assertIn("const canCli = new Set(tabla.filter((u) => u.doc.pax > 0).map((u) => u.doc.canal));", _JS)
        # Ningún color suelto: las variables de estilos/_00_base.py.
        self.assertNotRegex(_JS, r"#[0-9a-fA-F]{6}\b")


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class LasCuentasEnElNavegador(unittest.TestCase):
    """`calcular` del .js contra Python, período por período."""

    def test_mismas_cuentas(self):
        t, P = _armar()
        js = _JS.replace("export default function (component)", "function __montar(component)")
        with _chromium()() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:  # Chromium no instalado
                self.skipTest(f"sin Chromium: {e}")
            pg = b.new_page()
            pg.set_content("<p>")
            pg.add_script_tag(content=js)
            out = pg.evaluate("""(P) => {
              const V = window.VentasPeriodo, B = V.preparar(P), out = {};
              for (const gran of ['Día', 'Semana']) {
                const R = V.calcular(B, { gran, fil: { grupo: [], serv: [], canal: [], tdoc: [] } });
                out[gran] = { claves: R.claves, g: R.g, formas: R.porForma, sin: [...R.sinCostoProds.entries()],
                              culp: [...R.culpables.entries()].map(([k, c]) => [k, c.prod]) };
              }
              const F = V.calcular(B, { gran: 'Día', fil: { grupo: ['Bebidas'], serv: [], canal: [], tdoc: [] } });
              out.filtro = { claves: F.claves, total: F.g.total, pax: F.g.pax };
              return out;
            }""", P)
            b.close()
        tabla = t[t["clase"].isin(dv.CLASES_VENTA)].copy()
        for gran in ("Día", "Semana"):
            with self.subTest(gran=gran):
                k = vr._periodo_serie(tabla["fecha"], gran)
                tabla["k"] = k.to_numpy()
                j = out[gran]
                claves = sorted(tabla["k"].unique())
                self.assertEqual(j["claves"], claves)
                g = j["g"]
                tot = tabla.groupby("k")["venta"].sum().reindex(claves).tolist()
                for a, b_ in zip(g["total"], tot):
                    self.assertAlmostEqual(a, b_)
                pax = dv.pax_por(tabla, "ped", "pax", doc="ldoc", por="k").reindex(claves).fillna(0).tolist()
                self.assertEqual(g["pax"], pax)
                docs = dv.documentos_por(tabla, "ldoc", "clase", por="k").reindex(claves).fillna(0).tolist()
                self.assertEqual(g["n_docs"], docs)
                cli = dv.con_clientes(tabla, "canal", "pax")
                vc = tabla[cli].groupby("k")["venta"].sum().reindex(claves).fillna(0)
                for a, v_, px in zip(g["ticket"], vc, pax):
                    if px:
                        self.assertAlmostEqual(a, v_ / px)
                    else:
                        self.assertIsNone(a)
                # Las formas de pago: las de `formas_de_pago`, con la marca de cada tarjeta.
                fp = vr.formas_de_pago(_pagos(), "FEC REG DOCUMENTO", gran, set(claves))
                self.assertEqual(sorted(f for f, _ in j["formas"]), sorted(fp.columns))
                for f, serie in j["formas"]:
                    for a, b_ in zip(serie, fp[f].reindex(claves).fillna(0)):
                        self.assertAlmostEqual(a, b_)
                # Lo vendido sin costo y el plato que dispara el costo.
                por, _r = vr.productos_sin_costo(tabla.assign(clave=tabla["k"]))
                self.assertEqual({k: [p for p, _ in v] for k, v in j["sin"]}, {k: [p for p, _ in v] for k, v in por.items()})
                self.assertTrue(all(c == "Pato" for _k, c in j["culp"]))
        # Con Grupo = Bebidas: sólo el agua de L1, y los clientes de su mesa.
        self.assertEqual(out["filtro"]["claves"], ["2026-10-05"])
        self.assertAlmostEqual(out["filtro"]["total"][0], 10.0)
        self.assertEqual(out["filtro"]["pax"], [2])


if __name__ == "__main__":
    unittest.main()
