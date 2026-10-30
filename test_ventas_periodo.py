"""Ventas › «Venta por Periodo» como pieza propia (regla #714).

Lo que recibe la pieza (`lineas_normalizadas`, `armar_periodo`,
`pagos_periodo`) y que el navegador haga las MISMAS cuentas que Python:
`calcular` de `ventas_periodo.js` contra `definicion_venta` (clientes,
comprobantes, ticket) y contra los ayudantes puros de `ventas_resumen.py`
(formas de pago, IGV, lo vendido sin costo), en Chromium, día por día y
semana por semana. Desde la regla #758, la comparación («Contra»), «Qué movió»,
el cierre y la tarjeta entera. Sin secrets ni red; la parte de Chromium se
salta si Playwright no está (es de requirements-dev.txt).

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

    def test_lo_sin_descargo_suma_en_la_venta_y_no_se_observa(self):
        # Regla #761: el agua está «Sin descargo» en el POS (costo cero de verdad).
        d = _ventas()
        d[dv.PRODUCTO] = d["NOMB ITEM VENTA"].map({"Agua": "0000153"}).fillna("0000001")
        t = vr.lineas_normalizadas(d, {**_CLAVES, "sin_descargo": ("0000153",)})
        P = vr.armar_periodo(t, vr.sello_periodo(t), 196, 380, 250)
        self.assertEqual(P["sinc"], [])
        self.assertEqual(sum(u[7] for u in P["unidades"]), 0)
        self.assertEqual(vr.productos_sin_costo(t.assign(clave="x")), ({}, []))
        # La venta y el neto no cambian: sólo deja de observarse.
        self.assertAlmostEqual(sum(u[2] for u in P["unidades"]), self.t["venta"].sum())
        self.assertAlmostEqual(sum(u[4] for u in P["unidades"]), self.t["neto"].sum())
        # Otra marca es otra pieza: no se reusa la de antes.
        self.assertNotEqual(vr.sello_periodo(t), vr.sello_periodo(vr.lineas_normalizadas(d, _CLAVES)))
        # Sin los códigos, el agua se sigue observando.
        P0 = vr.armar_periodo(vr.lineas_normalizadas(d, _CLAVES), "x", 196, 380, 250)
        self.assertEqual({P0["prods"][x[1]] for x in P0["sinc"]}, {"Agua"})

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


# ── La comparación y el cierre (regla #758) ───────────────────────────────
def _corridas(dias, sufijo=""):
    """Las mismas ventas, `dias` después, con otros comprobantes y pedidos."""
    d = _ventas()
    d["FEC REG DOCUMENTO"] = d["FEC REG DOCUMENTO"] + pd.Timedelta(days=dias)
    for c in ("LLAVE LOCAL DOCUMENTO", "LLAVE LOCAL PEDIDO"):
        d[c] = d[c] + sufijo
    return d


def _pieza(dias=0, ultimo=None):
    t = vr.lineas_normalizadas(_corridas(dias), _CLAVES)
    P = vr.armar_periodo(t, vr.sello_periodo(t), 236, 380, 250)
    idoc = {k: i for i, k in enumerate(t.drop_duplicates("ldoc")["ldoc"])}
    P["pagos"], P["formas"] = vr.pagos_periodo(_pagos(), "FEC REG DOCUMENTO", idoc)
    P.update(turno=True, franja=[], hist_ctx="c", datos_desde="2025-01-01",
             ultimo_dato=ultimo or str(t["fecha"].max().date()),
             ppto={"2026-10": {"ALMUERZO": 1000.0, "CENA": 3000.0}})
    return t, P


def _historia(dias, ventanas, sufijo="h"):
    t = vr.lineas_normalizadas(_corridas(dias, sufijo), _CLAVES)
    return vr.armar_historia(t, "c", ventanas)


class LaHistoria(unittest.TestCase):
    def test_lleva_lo_que_es_venta_por_comprobante_y_grupo(self):
        H = _historia(-364, [["2025-10-06", "2025-10-14"]])
        self.assertEqual(H["parte"], "historia")
        self.assertEqual(H["base"], "2025-10-06")
        # Fuera la cortesía y el anulado; adentro la nota, con su pax negativo.
        self.assertEqual(len(H["docs"]), 9)
        self.assertEqual(sorted(d[6] for d in H["docs"] if d[1] == vr._CLASES.index(NC)), [-2.0])
        self.assertAlmostEqual(sum(u[2] for u in H["unidades"]), 59 + 10 + 160 + 59 + 80 + 59 + 59 - 59 + 59 + 118)
        json.dumps(H)

    def test_sin_datos_o_con_error_igual_cubre_lo_pedido(self):
        H = vr.armar_historia(None, "c", [["2025-01-01", "2025-01-02"]], error=True)
        self.assertEqual((H["ventanas"], H["error"], H["docs"]), ([["2025-01-01", "2025-01-02"]], True, []))

    def test_el_js_lee_las_mismas_posiciones(self):
        self.assertIn("dia: base + d[0], clase: d[1], ped: off + d[2], canal: D.canales[d[3]], serv: D.servs[d[4]], tdoc: D.tdocs[d[5]], pax: d[6], ninos: d[7]", _JS)
        self.assertIn("grupo: D.grupos[u[1]], venta: u[2], carta: u[3], neto: u[4], desc: u[5], costo: u[6]", _JS)

    def test_el_presupuesto_es_la_columna_bruta_por_servicio(self):
        t = pd.DataFrame({"anio": [2026, 2026], "mes": [10, 10], "servicio": ["ALMUERZO", "CENA"],
                          "bruta": [100.0, 200.0], "neta": [80.0, 160.0]})
        self.assertEqual(vr.presupuesto_meses(t), {"2026-10": {"ALMUERZO": 100.0, "CENA": 200.0}})
        self.assertEqual(vr.presupuesto_meses(t.iloc[0:0]), {})

    def test_el_puente_es_la_cuenta_de_comparativo(self):
        comp = (Path(vr.__file__).parent / "ventas_comparativo.js").read_text(encoding="utf-8")
        self.assertIn("clientes:(a.pax - p.pax) * tp", comp)
        self.assertIn("clientes: (a.pax - p.pax) * tp, ticket: (ta - tp) * a.pax", _JS)


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class LaComparacionEnElNavegador(unittest.TestCase):
    def _pagina(self, p, ancho=1300, alto=800):
        try:
            b = p.chromium.launch()
        except Exception as e:  # Chromium no instalado
            self.skipTest(f"sin Chromium: {e}")
        xlsx = (Path(vr.__file__).parent / "_xlsx.js").read_text(encoding="utf-8")
        js = xlsx + _JS.replace("export default function (component)", "window.__montar = function (component)")
        css = (Path(vr.__file__).parent / "ventas_periodo.css").read_text(encoding="utf-8")
        pg = b.new_page(viewport={"width": ancho, "height": alto})
        pg.set_content(f"<style>:root{{--alto-util:620px}}{css}</style><div id='r'></div>")
        pg.add_script_tag(content=js)
        return b, pg

    def test_cada_base_contra_pandas(self):
        t, P = _pieza()
        # Hace un año, con Lomo Saltado de menos: el puente tiene que sumar.
        H = _historia(-364, [["2025-10-06", "2025-10-14"]])
        with _chromium()() as p:
            b, pg = self._pagina(p)
            out = pg.evaluate("""([P, H]) => {
              const V = window.VentasPeriodo, B = V.preparar(P), fil = { grupo: [], serv: [], canal: [], tdoc: [] };
              const st = { gran: 'Día', fil, contra: 'anio' }, R = V.calcular(B, st), out = {};
              B.hist = V.historiaNueva('c');
              out.falta0 = V.faltantes(B, V.ventanasDe(B, R, st)).length;
              V.agregarHistoria(B.hist, H);
              out.falta1 = V.faltantes(B, V.ventanasDe(B, R, st)).length;
              const Bs = V.calcularBase(B, R, st);
              out.venta = Bs.barras.map((x) => x && x.venta); out.total = Bs.total;
              out.actual = R.g.total;
              out.puenteIgual = V.puente(V.totalPeriodos(R, R.claves.map((_, i) => i)), Bs.total);
              const stF = { gran: 'Día', fil: Object.assign({}, fil, { grupo: ['Bebidas'] }), contra: 'anio' }, RF = V.calcular(B, stF);
              const F = V.calcularBase(B, RF, stF);
              out.filtrado = { venta: F.total.venta, pax: F.total.pax };
              out.opc = V.opcionesBase(R).map((x) => x[0]);
              out.opcMes = V.opcionesBase(V.calcular(B, { gran: 'Mes', fil })).map((x) => x[0]);
              const stA = { gran: 'Día', fil, contra: 'anio' }, RA = V.calcular(B, stA);
              const B0 = V.preparar(Object.assign({}, P, { datos_desde: '2026-01-01' }));
              B0.hist = V.historiaNueva('c');
              out.sinDatos = V.calcularBase(B0, RA, stA).total;
              return out;
            }""", [P, H])
            b.close()
        self.assertEqual(out["falta0"], 1)
        self.assertEqual(out["falta1"], 0)
        # Las mismas ventas 364 días antes: cada barra contra sí misma.
        self.assertEqual([x for x in out["venta"] if x is not None], out["actual"])
        tabla = t[t["clase"].isin(dv.CLASES_VENTA)]
        self.assertAlmostEqual(out["total"]["venta"], tabla["venta"].sum())
        self.assertEqual(out["total"]["pax"], dv.pax_por(tabla.assign(k=1), "ped", "pax", doc="ldoc", por="k").iloc[0])
        self.assertAlmostEqual(out["puenteIgual"]["d"], 0)
        # Con un filtro, la base sale filtrada: el agua de L1 y su mesa.
        self.assertAlmostEqual(out["filtrado"]["venta"], 10.0)
        self.assertEqual(out["filtrado"]["pax"], 2)
        self.assertEqual(out["opc"], ["anio", "ant", "normal"])
        self.assertEqual(out["opcMes"], ["anio"])
        # Antes de que empiecen los datos no hay base: no es «cero ventas» (#660).
        self.assertIsNone(out["sinDatos"])

    def test_el_puente_suma_la_diferencia(self):
        _t, P = _pieza()
        d = _corridas(-364, "h")
        d = d[d["LLAVE LOCAL DOCUMENTO"] != "L3h"]
        H = vr.armar_historia(vr.lineas_normalizadas(d, _CLAVES), "c", [["2025-10-06", "2025-10-14"]])
        with _chromium()() as p:
            b, pg = self._pagina(p)
            u = pg.evaluate("""([P, H]) => {
              const V = window.VentasPeriodo, B = V.preparar(P), st = { gran: 'Semana', fil: { grupo: [], serv: [], canal: [], tdoc: [] }, contra: 'anio' };
              const R = V.calcular(B, st); B.hist = V.historiaNueva('c'); V.agregarHistoria(B.hist, H);
              const Bs = V.calcularBase(B, R, st);
              return V.puente(V.totalPeriodos(R, R.claves.map((_, i) => i)), Bs.total);
            }""", [P, H])
            b.close()
        self.assertAlmostEqual(u["clientes"] + u["ticket"] + u["sin_clientes"], u["d"])
        self.assertAlmostEqual(u["d"], 59.0)

    def test_lo_normal_y_el_cierre_contra_pandas(self):
        import statistics
        t, P = _pieza(-4)
        semanas = list(range(1, 9))
        ventanas, hists = [], []
        for k in semanas:
            ini = pd.Timestamp("2026-10-01") - pd.Timedelta(days=7 * k)
            ventanas.append([str(ini.date()), str((ini + pd.Timedelta(days=8)).date())])
            hists.append(_corridas(-4 - 7 * k, f"h{k}"))
        todo = pd.concat(hists + [_corridas(-4)], ignore_index=True)
        n = vr.lineas_normalizadas(todo, _CLAVES)
        n = n[n["clase"].isin(dv.CLASES_VENTA)]
        por_dia = n.groupby(n["fecha"].dt.normalize())["venta"].sum()
        ultimo = t[t["clase"].isin(dv.CLASES_VENTA)]["fecha"].max().normalize()
        fut = pd.date_range(ultimo + pd.Timedelta(days=1), "2026-10-31")

        def normal(f):
            v = [por_dia.get(f - pd.Timedelta(days=7 * k), 0) for k in semanas]
            v = [x for x in v if x > 0]
            return statistics.median(v) if v else 0.0

        hist = [vr.armar_historia(vr.lineas_normalizadas(h, _CLAVES), "c", [w]) for h, w in zip(hists, ventanas)]
        P["ultimo_dato"] = str(ultimo.date())
        with _chromium()() as p:
            b, pg = self._pagina(p)
            out = pg.evaluate("""([P, Hs]) => {
              const V = window.VentasPeriodo, B = V.preparar(P), st = { gran: 'Día', fil: { grupo: [], serv: [], canal: [], tdoc: [] }, contra: 'normal' };
              const R = V.calcular(B, st); B.hist = V.historiaNueva('c'); Hs.forEach((H) => V.agregarHistoria(B.hist, H));
              const c = V.calcularCierre(B, R, st), Bs = V.calcularBase(B, R, st);
              const stS = { gran: 'Día', fil: { grupo: [], serv: ['Cena'], canal: [], tdoc: [] } };
              const stC = { gran: 'Día', fil: { grupo: [], serv: [], canal: ['Rappi'], tdoc: [] } };
              const conServ = V.calcularCierre(B, V.calcular(B, st), Object.assign({}, st, { fil: stS.fil }));
              const conCanal = V.calcularCierre(B, V.calcular(B, stC), stC);
              const P2 = Object.assign({}, P, { ultimo_dato: '2026-10-20' });
              const B2 = V.preparar(P2); B2.hist = B.hist;
              return { cierre: c.cierre, falta: c.falta, tot: c.tot, dias: c.dias.map((e) => e.t.venta), n: c.dias.length, ppto: c.ppto, pct: c.pct, porDia: c.porDia,
                base: Bs.barras.map((x) => x && x.venta), conServ: conServ.ppto, conCanal: conCanal.ppto, viejo: V.calcularCierre(B2, V.calcular(B2, st), st),
                semana: V.calcularCierre(B, V.calcular(B, { gran: 'Semana', fil: st.fil }), st) };
            }""", [P, hist])
            b.close()
        self.assertEqual(out["n"], len(fut))
        esperado = [normal(f) for f in fut]
        for a, e in zip(out["dias"], esperado):
            self.assertAlmostEqual(a, e, places=3)
        tot = t[t["clase"].isin(dv.CLASES_VENTA)]["venta"].sum()
        self.assertAlmostEqual(out["tot"], tot)
        self.assertAlmostEqual(out["cierre"], tot + sum(esperado), places=3)
        self.assertEqual(out["ppto"], 4000.0)
        self.assertAlmostEqual(out["pct"], (tot + sum(esperado)) / 4000)
        self.assertAlmostEqual(out["porDia"], (4000 - tot) / len(fut))
        # Lo normal de cada barra: el mismo día de la semana, ocho semanas atrás.
        dias = sorted(t[t["clase"].isin(dv.CLASES_VENTA)]["fecha"].dt.normalize().unique())
        for a, f in zip(out["base"], dias):
            self.assertAlmostEqual(a, normal(pd.Timestamp(f)), places=3)
        # El presupuesto no separa un canal; y sí un servicio.
        self.assertIsNone(out["conCanal"])
        self.assertEqual(out["conServ"], 3000.0)
        # Con datos más nuevos en el parquet, o por semana, no hay cierre.
        self.assertIsNone(out["viejo"])
        self.assertIsNone(out["semana"])

    def test_la_tarjeta(self):
        _t, P = _pieza(-4)
        hists = [_historia(-364 - 4, [["2025-10-01", "2025-10-31"]])]
        ventanas8 = [["2026-08-14", "2026-09-30"]]
        hists.append(_historia(-4 - 21, ventanas8, "s"))
        with _chromium()() as p:
            b, pg = self._pagina(p)
            r = pg.evaluate("""([P, Hs]) => {
              const parent = document.getElementById('r'), pedidos = [], out = {};
              const montar = (data) => window.__montar({ data, parentElement: parent, setTriggerValue: (k, v) => pedidos.push([k, v]) });
              montar(P);
              const raiz = parent.querySelector('.vp'), $ = (s) => raiz.querySelector(s), $$ = (s) => [...raiz.querySelectorAll(s)];
              const dd = () => document.body.scrollWidth - document.documentElement.clientWidth;
              out.trayendo = $('.kpi .kn').textContent; out.pedidos = pedidos.length; out.pedido = pedidos[0];
              // Pedir dos veces lo mismo no vuelve a mandar nada.
              $('[data-acc="med"][data-v="clientes"]').click();
              $('[data-acc="med"][data-v="venta"]').click();
              out.pedidos2 = pedidos.length;
              Hs.forEach((H) => { H.ctx = 'c'; montar(H); });
              out.tiles = $$('.kpi').map((k) => k.textContent);
              out.cierreTile = $('.kpi .kc') && $('.kpi .kc').textContent;
              out.futuros = $$('.gr .fut').length; out.zonasFuturas = $$('[data-acc="fut"]').length;
              out.base = $$('.gr .pt-b').length;
              out.etiquetasClave = $$('.gr .et').length;
              out.alto = raiz.clientHeight; out.altoTabla = $('.zr').clientHeight;
              out.desborde = dd();
              $('[data-acc="cifras"][data-v="Todas"]').click(); out.etiquetasTodas = $$('.gr .et').length;
              $('[data-acc="cifras"][data-v="Clave"]').click();
              // Un indicador elige qué mide el gráfico.
              $('[data-acc="med"][data-v="ticket"]').click();
              out.tit = $('.tit').textContent; out.ticketOn = $('.kpi.on .kr').textContent; out.capas = !!$('.ley');
              $('[data-acc="med"][data-v="venta"]').click();
              // Elegir un día no salta a los pedidos: lo cuenta el panel y marca su fila.
              $$('[data-acc="barra"]')[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
              out.modo = raiz.__vp.st.modo; out.foco = $('.pn-f b').textContent; out.filaSel = $$('tbody tr.sel').length;
              $('[data-acc="pan"][data-v="Qué movió"]').click(); out.movio = $('.pn').textContent;
              $('[data-acc="quitar"]').click(); out.sinFoco = !$('.pn-f');
              $('[data-acc="pan"][data-v="Qué movió"]').click(); out.movioTodo = $('.pn').textContent;
              $('[data-acc="pan"][data-v="Cierre"]').click(); out.cierre = $('.pn').textContent;
              $('[data-acc="pan"][data-v="Desglose"]').click(); out.desglose = $('.pn').textContent;
              // Un clic en la barra proyectada abre el Cierre.
              $$('[data-acc="fut"]')[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
              out.panFut = raiz.__vp.st.pan; $('[data-acc="pan"][data-v="Desglose"]').click();
              // Comparar con.
              const sel = $('.cn select'); out.opciones = [...sel.options].map((o) => o.textContent);
              sel.value = 'normal'; sel.dispatchEvent(new Event('change', { bubbles: true }));
              out.contra = raiz.__vp.st.contra; out.tileNormal = $('.kpi .kn').textContent;
              const s2 = $('.cn select'); s2.value = 'anio'; s2.dispatchEvent(new Event('change', { bubbles: true }));
              // Ampliar: una cosa o la otra, y se vuelve con todo igual.
              $$('.amp')[0].click(); out.amplGraf = { tabla: !!$('.zr'), pie: !!$('.pie'), panel: !!$('.pn'), alto: $('.gr svg').getAttribute('height'), volver: $$('.amp')[0].textContent };
              $$('.amp')[0].click();
              $('.pie .amp').click(); out.amplTabla = { graf: !!$('.gr'), tabla: $('.zr').clientHeight, volver: $('.pie .amp').textContent };
              $('.pie .amp').click(); out.vuelve = !!$('.gr') && !!$('.zr');
              // «Ver sus pedidos» y Capas siguen.
              $$('[data-acc="barra"]')[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
              $('[data-acc="verped"]').click(); out.detalle = raiz.__vp.st.modo;
              $('[data-acc="ley"]').click(); out.capasP = $('.ley-p').textContent;
              return out;
            }""", [P, hists])
            b.close()
        self.assertIn("Trayendo", r["trayendo"])
        self.assertEqual(r["pedidos"], 1)
        self.assertEqual(r["pedido"][0], "historia")
        self.assertEqual(r["pedido"][1]["ctx"], "c")
        self.assertEqual(r["pedidos2"], 1)
        self.assertIn("vs año pasado", r["tiles"][0])
        self.assertIn("Cierre ≈", r["cierreTile"])
        self.assertIn("del presupuesto", r["cierreTile"])
        self.assertEqual(r["zonasFuturas"], 22)
        self.assertGreater(r["futuros"], 0)
        self.assertGreater(r["base"], 0)
        self.assertLess(r["etiquetasClave"], r["etiquetasTodas"])
        self.assertEqual(r["alto"], 589)
        self.assertGreater(r["altoTabla"], 60)
        self.assertLessEqual(r["desborde"], 0)
        self.assertEqual(r["tit"], "Ticket por día")
        self.assertEqual(r["ticketOn"], "Ticket")
        self.assertFalse(r["capas"])
        self.assertEqual(r["modo"], "Resumen")
        self.assertTrue(r["foco"])
        self.assertEqual(r["filaSel"], 1)
        self.assertIn("Clientes", r["movio"])
        self.assertTrue(r["sinFoco"])
        self.assertIn("Esta vista", r["movioTodo"])
        self.assertIn("Canales sin clientes", r["movioTodo"])
        self.assertIn("Cierre proyectado", r["cierre"])
        self.assertIn("Presupuesto", r["cierre"])
        self.assertIn("Para llegar", r["cierre"])
        for rotulo_ in ("Precio de carta", "Rappi", "Notas de crédito", "Neto sin IGV", "Costo histórico", "Propinas", "Cortesías", "Anulados"):
            self.assertIn(rotulo_, r["desglose"])
        self.assertEqual(r["panFut"], "Cierre")
        self.assertEqual(r["opciones"][0], "Año pasado")
        self.assertEqual(r["opciones"][2], "Lo normal")
        self.assertEqual(r["contra"], "normal")
        self.assertFalse(r["amplGraf"]["tabla"])
        self.assertTrue(r["amplGraf"]["panel"])
        self.assertGreater(int(r["amplGraf"]["alto"]), 236)
        self.assertIn("Volver", r["amplGraf"]["volver"])
        self.assertFalse(r["amplTabla"]["graf"])
        self.assertGreater(r["amplTabla"]["tabla"], 300)
        self.assertTrue(r["vuelve"])
        self.assertEqual(r["detalle"], "Detalle")
        for capa in ("Clientes", "Ticket", "Descuento"):
            self.assertIn(capa, r["capasP"])

    def test_sin_historia_la_tarjeta_sigue_sin_comparar(self):
        _t, P = _armar()
        with _chromium()() as p:
            b, pg = self._pagina(p)
            r = pg.evaluate("""(P) => {
              const parent = document.getElementById('r'), pedidos = [];
              window.__montar({ data: P, parentElement: parent, setTriggerValue: (k) => pedidos.push(k) });
              const raiz = parent.querySelector('.vp');
              return { pedidos: pedidos.length, cn: !!raiz.querySelector('.cn'), tabs: [...raiz.querySelectorAll('.pn-t button')].map((x) => x.textContent), kpis: raiz.querySelectorAll('.kpi').length };
            }""", P)
            b.close()
        self.assertEqual(r, {"pedidos": 0, "cn": False, "tabs": ["Desglose"], "kpis": 4})

    def test_en_el_celular_no_se_desborda(self):
        _t, P = _pieza(-4)
        hists = [_historia(-368, [["2025-10-01", "2025-10-31"]]), _historia(-25, [["2026-08-14", "2026-09-30"]], "s")]
        with _chromium()() as p:
            b, pg = self._pagina(p, 390, 844)
            r = pg.evaluate("""([P, Hs]) => {
              const parent = document.getElementById('r');
              const montar = (data) => window.__montar({ data, parentElement: parent, setTriggerValue: () => {} });
              montar(P); Hs.forEach((H) => { H.ctx = 'c'; montar(H); });
              const raiz = parent.querySelector('.vp');
              return { ancho: raiz.scrollWidth - raiz.clientWidth, tabla: raiz.querySelector('.zr').clientHeight, kpi: raiz.querySelector('.kpi').getBoundingClientRect().width };
            }""", [P, hists])
            b.close()
        self.assertLessEqual(r["ancho"], 1)
        self.assertGreater(r["tabla"], 100)
        self.assertGreater(r["kpi"], 100)


if __name__ == "__main__":
    unittest.main()
