"""Compras › Producto como pieza propia (regla #713).

Lo que recibe la pieza (`historial_pieza`, `armar_ranking`) y que el
navegador rehaga la curva con las MISMAS cuentas que Python: `serie` de
`producto.js` contra `_serie` de `producto.py`, en Chromium, en cada ventana
y cada grano. Sin secrets ni red; la parte de Chromium se salta si Playwright
no está (es de requirements-dev.txt).

    python test_producto_pieza.py
"""

import json
import math
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from graficos.compras import producto as P

_AQUI = Path(P.__file__).parent
_JS = (_AQUI / "producto.js").read_text(encoding="utf-8")

# FAM, SUB, PROD, VAL, CANT, UM, FECHA, PROV, DOC — los casos de la regla
# #653 (la compra de lomo a S/ 15,85, el producto nuevo, el que vuelve, la
# subfamilia repetida entre familias) y una compra sin documento.
_FILAS = [
    ("A", "Carnes", "Lomo", 745.0, 10.0, "KILOS", "2026-01-15", "P1", "F00"),
    ("A", "Carnes", "Lomo", 745.0, 10.0, "KILOS", "2026-08-10", "P1", "F1"),
    ("A", "Carnes", "Lomo", 745.0, 10.0, "KILOS", "2026-09-04", "P1", "F2"),
    ("A", "Carnes", "Lomo", 237.75, 15.0, "KILOS", "2026-09-19", "P1", "F3"),
    ("A", "Carnes", "Lomo", 800.0, 10.0, "KILOS", "2026-09-22", "P2", "F4"),
    ("A", "Carnes", "Lomo", 380.0, 5.0, "KILOS", "2026-09-22", "P2", ""),
    ("A", "Carnes", "Asado", 200.0, 5.0, "KILOS", "2026-09-05", "P1", "F2"),
    ("A", "Varios", "Bolsa", 50.0, 100.0, "UND", "2026-09-06", "P3", "F5"),
    ("B", "Vinos", "Malbec", 300.0, 12.0, "UND", "2026-09-07", "P4", "F6"),
    ("B", "Vinos", "Malbec", 706.8, 4.5, "UND", "2026-09-29", "P4", "F9"),
    ("B", "Varios", "Tapa", 80.0, 40.0, "UND", "2026-09-08", "P3", "F7"),
    ("B", "Varios", "Corcho", 20.0, 200.0, "UND", "2026-03-01", "P3", "F0"),
    ("B", "Varios", "Corcho", 20.0, 200.0, "UND", "2026-09-09", "P3", "F8"),
]
_COLS = ("PROD", "FAM", "SUB", "VAL", "CANT", "UM", "FECHA", "PROV", "DOC")


def _hist():
    df = pd.DataFrame(_FILAS, columns=["FAM", "SUB", "PROD", "VAL", "CANT", "UM",
                                       "FECHA", "PROV", "DOC"])
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    return P._normalizar(df, *_COLS)


def _ranking(h, r0, r1):
    dias = (r1 - r0).days + 1
    rng = h[(h["fecha"] >= r0) & (h["fecha"] <= r1)]
    prev = h[(h["fecha"] >= r0 - pd.Timedelta(days=dias)) & (h["fecha"] < r0)]
    antes = h[h["fecha"] < r0]
    res_p = P._resumen(rng, ["prod"], prev, antes["prod"].unique())
    res_p["um"] = "kg"
    res_p["fam"] = rng.groupby("prod")["fam"].first().reindex(res_p.index)
    res_p["sub"] = rng.groupby("prod")["sub"].first().reindex(res_p.index)
    res_p["ultp"] = P._ultimo_precio(rng).reindex(res_p.index)
    res_p["cada"] = P._cada_cuanto(rng).reindex(res_p.index)
    res_f = P._resumen(rng, ["fam"], prev, antes["fam"].unique())
    res_s = P._resumen(rng, ["fam", "sub"], prev,
                       list(antes[["fam", "sub"]].drop_duplicates()
                            .itertuples(index=False, name=None)))
    return res_p, res_f, res_s, float(prev["valor"].sum())


class LoQueRecibe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hist = _hist()
        cls.sello = P.sello_historial(cls.hist)
        cls.h, cls.F = P.historial_pieza(cls.hist, cls.sello)
        cls.r0, cls.r1 = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30")
        res_p, res_f, res_s, prev = _ranking(cls.h, cls.r0, cls.r1)
        cls.R = P.armar_ranking(res_p, res_f, res_s, cls.F["nombres"], (cls.r0, cls.r1),
                                cls.h["fecha"].max(), prev, 3, 2, cls.sello)

    def test_cada_producto_lleva_su_historial_entero(self):
        nom = self.F["nombres"]
        self.assertEqual(nom, sorted(nom))
        lomo = self.F["lineas"][nom.index("Lomo")]
        self.assertEqual(len(lomo), 6)
        base = pd.Timestamp(self.F["base"])
        dias = [l[0] for l in lomo]
        self.assertEqual(dias, sorted(dias))
        self.assertEqual(base + pd.Timedelta(days=dias[0]), pd.Timestamp("2026-01-15"))

    def test_la_marca_y_el_habitual_van_en_la_linea(self):
        nom, docs = self.F["nombres"], self.F["docs"]
        lomo = self.F["lineas"][nom.index("Lomo")]
        marcada = [l for l in lomo if l[4] == 237.75][0]
        self.assertEqual(P._FLAGS[marcada[6]], "precio")
        self.assertAlmostEqual(marcada[5], 74.5)
        malbec = self.F["lineas"][nom.index("Malbec")]
        self.assertEqual(P._FLAGS[malbec[-1][6]], "um")
        sin_doc = [l for l in lomo if l[4] == 380.0][0]
        self.assertEqual(docs[sin_doc[2]], "")
        self.assertTrue(all(d for d in docs if d != ""))

    def test_la_misma_sello_en_las_dos_tarjetas(self):
        self.assertEqual(self.F["sello"], self.R["sello"])
        self.assertEqual((self.F["parte"], self.R["parte"]), ("ficha", "rank"))
        otro = self.hist.copy()
        otro.loc[0, "valor"] += 1
        self.assertNotEqual(P.sello_historial(otro), self.sello)
        self.assertEqual(P.sello_historial(self.hist.copy()), self.sello)

    def test_el_ranking_es_el_resumen_de_siempre(self):
        p = {self.F["nombres"][r[0]]: r for r in self.R["prods"]}
        lomo = p["Lomo"]
        self.assertAlmostEqual(lomo[4], 745 + 237.75 + 800 + 380)
        self.assertAlmostEqual(lomo[8], (745 + 800 + 380) / 25, places=4)
        self.assertEqual(p["Corcho"][7], "vuelve")
        self.assertEqual(p["Tapa"][7], "nuevo")
        self.assertEqual(self.R["rango"], ["2026-09-01", "2026-09-30"])
        self.assertEqual(self.R["dias"], 30)
        subs = {(r[0], r[1]): r for r in self.R["subs"]}
        self.assertEqual(subs[("A", "Varios")][2], 50.0)
        self.assertEqual(subs[("B", "Varios")][2], 100.0)
        json.dumps(self.R)
        json.dumps(self.F)

    def test_el_js_lee_las_mismas_posiciones(self):
        self.assertIn("const RP = { i: 0, fam: 1, sub: 2, um: 3, valor: 4, cant: 5, var: 6, est: 7, pp: 8, hab: 9, ppv: 10, nflag: 11,", _JS)
        self.assertIn("docs: 12, ult: 13, ultp: 14, cada: 15, prev: 16, vref: 17, refc: 18 };", _JS)
        self.assertIn("const RL = { dia: 0, prov: 1, doc: 2, cant: 3, valor: 4, ref: 5, flag: 6 };", _JS)
        self.assertIn("const FLAGS = ['', 'um', 'precio'];", _JS)
        self.assertEqual(P._FLAGS, ("", "um", "precio"))

    def test_el_js_hace_las_cuentas_de_python(self):
        # Sin las marcadas en el precio (`_precios`) y con el habitual pesado.
        self.assertIn("const precioDe = (a) => (a.pc > 0 ? a.pv / a.pc : null);", _JS)
        self.assertIn("const habDe = (a) => (a.cr > 0 ? a.rc / a.cr : null);", _JS)
        self.assertIn("const ok = !l.flag && l.cant > 0, okr = ok && finito(l.ref);", _JS)
        # La ventana de `periodo.ventana`: +1 día desde el último con datos.
        self.assertIn("let ini = restarMeses(ultimo, MESES_OP[op]) + 1;", _JS)
        # Nada de reclasificar: la marca llega hecha (`marcar_revisar`).
        self.assertNotIn("_VECES_REVISAR", _JS)
        self.assertIn("flag: FLAGS[l[RL.flag]] || ''", _JS)


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class LaCurvaEnElNavegador(unittest.TestCase):
    """`serie` del .js contra `_serie` de Python, período por período."""

    def test_misma_curva(self):
        hist = _hist()
        sello = P.sello_historial(hist)
        h, F = P.historial_pieza(hist, sello)
        rango = (pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30"))
        js = _JS.replace("export default function (component)", "function __montar(component)")
        casos = [(prod, gran, op, ultimo)
                 for prod in ("Lomo", "Malbec", "Corcho")
                 for gran in ("Semana", "Mes", "Año", "Documento")
                 for op in ("Rango", "3m", "12m", "Todo")
                 for ultimo in ("2026-09-29", "2026-09-30", "2026-12-31")]
        with _chromium()() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:  # Chromium no instalado
                self.skipTest(f"sin Chromium: {e}")
            pg = b.new_page()
            pg.set_content("<p>")
            pg.add_script_tag(content=js)
            out = pg.evaluate("""([F, casos, rango]) => {
              const f = leerFicha(F);
              return casos.map(([prod, gran, op, ultimo]) => {
                const S = serie(f.L[F.nombres.indexOf(prod)], gran, op, dn(ultimo), [dn(rango[0]), dn(rango[1])]);
                if (!S) return null;
                return { keys: S.keys, agg: S.agg.map((a) => [a.c, a.v, a.pc, a.pv, a.rc, a.cr, a.fl, a.docs]),
                         parc: !!S.parc, refq: S.refq, rot: S.parc ? [S.parc.rot, S.parc.rotRef] : null,
                         precio: S.agg.map(precioDe), hab: S.agg.map(habDe) };
              });
            }""", [F, casos, [f"{rango[0]:%Y-%m-%d}", f"{rango[1]:%Y-%m-%d}"]])
            b.close()
        for (prod, gran, op, ultimo), j in zip(casos, out):
            with self.subTest(prod=prod, gran=gran, op=op, ultimo=ultimo):
                S = P._serie(h[h["prod"] == prod].reset_index(drop=True), gran, op,
                             pd.Timestamp(ultimo), rango)
                if S is None:
                    self.assertIsNone(j)
                    continue
                self.assertIsNotNone(j)
                if gran != "Documento":
                    self.assertEqual(j["keys"], [str(k) for k in S["keys"]])
                self.assertEqual(len(j["keys"]), len(S["keys"]))
                py = S["agg"][["c", "v", "pc", "pv", "rc", "cr", "fl", "docs"]].to_numpy().tolist()
                np.testing.assert_allclose(np.array(j["agg"], dtype=float), np.array(py, dtype=float),
                                           rtol=1e-9, atol=1e-6)
                self.assertEqual(j["parc"], S["parc"] is not None)
                if S["parc"] is not None:
                    self.assertAlmostEqual(j["refq"], S["refq"])
                    self.assertEqual(j["rot"], [S["parc"]["rot"], S["parc"]["rot_ref"]])
                pr, hb = P._precios(S["agg"])
                for a, b_ in ((j["precio"], pr), (j["hab"], hb)):
                    for x, y in zip(a, b_.tolist()):
                        if y is None or (isinstance(y, float) and math.isnan(y)):
                            self.assertIsNone(x)
                        else:
                            self.assertAlmostEqual(x, y, places=6)


if __name__ == "__main__":
    unittest.main()
