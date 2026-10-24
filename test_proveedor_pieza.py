"""Compras › Proveedor como pieza propia (regla #715).

Lo que recibe la pieza (`normalizar`, `historial_pieza`, `armar_rank`) y que
el navegador haga las MISMAS cuentas que la vista de antes (regla #646),
escritas acá en pandas: el ranking contra el período anterior de igual largo
(«nuevo», «vuelve», «Otros», el 80 %), las cifras del proveedor (documentos,
el «vs. precio habitual»), la curva en cada grano y ventana con el período
en curso y los mismos días del anterior, el Desglose y la historia de los
documentos. Corre `calcular` de `proveedor.js` en Chromium; sin Playwright
(es de requirements-dev.txt) esa parte se salta.

    python test_proveedor_pieza.py
"""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from graficos import periodo
from graficos.compras import proveedor as pv
from graficos.compras._comun import (agregar_periodo, inicio_de_periodo,
                                     tramo_parcial)
from graficos.compras.semanal import precio_habitual

_JS = (Path(pv.__file__).parent / "proveedor.js").read_text(encoding="utf-8")
_COLS = ("PROV", "PROD", "CANT", "VALOR", None, "UM", "FECHA", "DOC")
_ULTIMO = pd.Timestamp("2026-10-22")          # jueves: mes y semana a medias
_RANGO = (pd.Timestamp("2026-09-23"), _ULTIMO)  # 30 días


def _compras():
    """Compras de mentira con cada caso: A compra todas las semanas dos
    productos; B compró hace meses y vuelve en el rango; C es nuevo; D compra
    el mismo producto que A más caro; E tiene una línea sin documento."""
    rng = np.random.default_rng(7)
    filas = []
    n = 0
    for f in pd.date_range("2025-01-06", _ULTIMO, freq="7D"):
        for prod, base, um in (("Lomo fino", 70.0, "KG"), ("Agua", 2.0, "UND")):
            n += 1
            c = float(rng.integers(5, 40))
            p = base * (1 + 0.05 * rng.standard_normal())
            filas.append(("ALFA SAC", prod, c, round(c * p, 2), um, f, f"F00{n:05d}"))
        if f.day % 3 == 0:
            n += 1
            filas.append(("DELTA SAC", "Lomo fino", 10.0, 780.0, "KG", f + pd.Timedelta(days=1), f"E00{n:05d}"))
    filas += [("BETA SAC", "Agua", 100.0, 190.0, "UND", pd.Timestamp("2026-03-02"), "B0001"),
              ("BETA SAC", "Agua", 120.0, 250.0, "UND", pd.Timestamp("2026-10-01"), "B0002"),
              ("GAMA SAC", "Pato", 8.0, 400.0, "KG", pd.Timestamp("2026-10-10"), "G0001"),
              ("GAMA SAC", "Lomo fino", 3.0, 240.0, "KG", pd.Timestamp("2026-10-10"), "G0001"),
              ("EPSILON SAC", "Agua", 10.0, 20.0, "UND", pd.Timestamp("2026-10-05"), "")]
    return pd.DataFrame(filas, columns=["PROV", "PROD", "CANT", "VALOR", "UM", "FECHA", "DOC"])


def _armar(seleccion=()):
    h = pv.normalizar(_compras(), _COLS)
    sello = pv.sello_historial(h)
    return h, pv.historial_pieza(h, sello), pv.armar_rank(_RANGO, list(seleccion), sello)


# ── Las cuentas de la vista de antes, en pandas ─────────────────────────


def _ranking_ref(h, seleccion=(), otros=False):
    r0, r1 = _RANGO
    dias = (r1 - r0).days + 1
    rng = h[(h["fecha"] >= r0) & (h["fecha"] <= r1)]
    val = rng.groupby("prov")["valor"].sum().sort_values(ascending=False, kind="stable")
    prev = h[(h["fecha"] >= r0 - pd.Timedelta(days=dias)) & (h["fecha"] < r0)].groupby("prov")["valor"].sum()
    ult = h[h["fecha"] < r0].groupby("prov")["fecha"].max()
    top = [p for p in val.index if p in seleccion] or list(val.index)
    filas = {}
    for p in top:
        pr = float(prev.get(p, 0.0))
        if pr > 0:
            filas[p] = (val[p], "", (val[p] - pr) / pr * 100)
        else:
            filas[p] = (val[p], "vuelve" if p in ult.index else "nuevo", None)
    fuera = [p for p in val.index if p not in top]
    vals = [val[p] for p in top] + ([float(val[fuera].sum())] if otros and fuera else [])
    acum = np.cumsum(sorted(vals, reverse=True)) / float(val.sum()) * 100
    return filas, int((acum < 80).sum() + 1), (float(val.sum()) if fuera and otros else float(val[top].sum()))


def _cifras_ref(h, prov):
    r0, r1 = _RANGO
    ref = precio_habitual(h["prod"], h["fecha"], h["valor"], h["cant"])
    m = (h["prov"] == prov) & (h["fecha"] >= r0) & (h["fecha"] <= r1)
    docs = h.loc[m & (h["docu"].str.strip() != ""), "docu"].nunique()
    ok = m & ref.notna() & (h["cant"] > 0) & (h["valor"] > 0)
    ppv = float((h["valor"] - ref * h["cant"])[ok].sum()) if ok.any() else None
    return float(h.loc[m, "valor"].sum()), int(docs), ppv


def _curva_ref(h, prov, prod, gran, op, medida):
    """La curva de `_ficha` de antes: la fuente, los períodos y el valor."""
    r0, r1 = _RANGO
    if op == periodo.HEREDA:
        src = h[(h["fecha"] >= r0) & (h["fecha"] <= r1)]
    else:
        v = periodo.ventana(op, h["fecha"].max(), minimo=h["fecha"].min())
        src = h[(h["fecha"] >= inicio_de_periodo(v[0], gran)) & (h["fecha"] <= v[1])]
    src = agregar_periodo(src.copy(), gran)
    src["k"] = src["_per_sort"]
    m_prov = src["prov"] == prov
    keys = sorted(src.loc[m_prov if gran == "Documento" else slice(None), "k"].unique())
    if op == periodo.HEREDA and gran != "Documento":
        keys = keys[-12:]
    mc = m_prov & (src["prod"] == prod) if prod else m_prov
    g = src[mc].groupby("k").agg(v=("valor", "sum"), c=("cant", "sum")).reindex(keys).fillna(0.0)
    med = medida if prod else "valor"
    ys = g["c"] if med == "cant" else (g["v"] / g["c"].where(g["c"] > 0) if med == "precio" else g["v"])
    # El último día CON DATOS (el ancla de `periodo.py`), no el fin del rango.
    ult = h["fecha"].max()
    parc = tramo_parcial(gran, ult)
    if parc is not None:
        k_ult = agregar_periodo(pd.DataFrame({"fecha": [ult], "docu": [""]}), gran)["_per_sort"].iat[0]
        if k_ult != keys[-1]:
            parc = None
    ref = None
    if parc is not None and med != "precio":
        hh = h[(h["prov"] == prov) & ((h["prod"] == prod) if prod else True)]
        r = hh[(hh["fecha"] >= parc["ref_ini"]) & (hh["fecha"] <= parc["ref_fin"])]
        ref = float(r["cant" if med == "cant" else "valor"].sum())
    return keys, [None if pd.isna(y) else float(y) for y in ys], parc is not None, ref


def _historia_ref(h, prov):
    """`_historia_docs` de antes: días desde el documento anterior y el
    producto que más subió contra su compra anterior al mismo proveedor."""
    hp = h[(h["prov"] == prov) & (h["docu"].str.strip() != "")]
    docs = hp.groupby("docu").agg(fecha=("fecha", "min")).sort_values("fecha", kind="stable")
    dias = pd.to_datetime(docs["fecha"]).diff().dt.days
    lin = (hp[hp["cant"] > 0].groupby(["docu", "prod"], as_index=False)
           .agg(v=("valor", "sum"), c=("cant", "sum"), f=("fecha", "min")))
    lin["pu"] = lin["v"] / lin["c"]
    lin = lin.sort_values(["prod", "f", "docu"], kind="stable")
    lin["dp"] = (lin["pu"] / lin.groupby("prod")["pu"].shift() - 1) * 100
    sube = lin[lin["dp"] > 0.5].sort_values("dp", ascending=False, kind="stable").drop_duplicates("docu")
    return dias.to_dict(), {r.docu: (r.prod, r.dp) for r in sube.itertuples()}


class LoQueRecibe(unittest.TestCase):
    def test_una_lista_por_proveedor_en_orden(self):
        h, F, R = _armar()
        self.assertEqual(F["provs"], sorted(h["prov"].unique()))
        self.assertEqual(sum(map(len, F["lineas"])), len(h))
        for ls in F["lineas"]:
            self.assertEqual([x[0] for x in ls], sorted(x[0] for x in ls))
        # La línea sin documento: documento vacío y sin rótulo.
        e = F["provs"].index("EPSILON SAC")
        self.assertEqual(F["docs"][F["lineas"][e][0][2]], "")
        self.assertEqual(R["rango"], ["2026-09-23", "2026-10-22"])

    def test_el_filtro_viaja_sin_otros(self):
        _h, _F, R = _armar(["ALFA SAC", "Otros"])
        self.assertEqual(R["sel"], ["ALFA SAC"])
        self.assertTrue(R["otros"])

    def test_el_js_lee_las_mismas_posiciones(self):
        self.assertIn("const RL = { dia: 0, prod: 1, doc: 2, cant: 3, valor: 4, ref: 5, um: 6 };", _JS)
        doc = " ".join(pv.historial_pieza.__doc__.split())
        self.assertIn("[día (desde `base`), producto (índice de `prods`), documento (índice de `docs`), cantidad, "
                      "valor, precio habitual o None, unidad (índice de `ums`)]", doc)
        self.assertNotRegex(_JS, r"#[0-9a-fA-F]{6}\b")


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class LasCuentasEnElNavegador(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.h, cls.F, cls.R = _armar()
        js = _JS.replace("export default function (component)", "window.__montar = function (component)")
        cls._pw = _chromium()().start()
        try:
            cls.b = cls._pw.chromium.launch()
        except Exception as e:  # Chromium no instalado
            cls._pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {e}")
        cls.pg = cls.b.new_page()
        cls.pg.set_content("<p>")
        cls.pg.add_script_tag(content=js)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls._pw.stop()

    def _calc(self, st, R=None):
        return self.pg.evaluate("""([F, R, st]) => {
          const C = window.__cpProvCalc, f = C.leerFicha(F), r = C.leerRank(R);
          const x = C.calcular(f, r, { winFirma: null, winIni: null, win: null, ...st });
          const rk = x.rk;
          const out = { filas: rk.filas.map((a) => [a.p < 0 ? 'Otros' : f.provs[a.p], a.valor, a.est, a.var]),
            n80: rk.n80, total: rk.total.valor, p: x.p == null ? null : f.provs[x.p] };
          if (x.ci) out.ci = [x.ci.compra, x.ci.docs, x.ci.ppv];
          if (x.C) out.C = { keys: x.C.keys, ys: x.C.ys, parc: !!x.C.parc, ref: x.C.ref };
          if (x.C) { const D = C.desglose(f, x.C, f.P[x.p], st.medida || 'valor');
            out.D = D.filas.map((a) => [f.prods[a.prod], a.m.slice(-D.vis.length)]); }
          if (x.p != null) { const hd = C.historiaDocs(f.P[x.p]);
            out.hd = { dias: [...hd.dias.entries()].map(([d, v]) => [F.docs[d], v]),
              top: [...hd.top.entries()].map(([d, a]) => [F.docs[d], f.prods[a.prod], a.dp]) }; }
          return out;
        }""", [self.F, R or self.R, st])

    def _foco(self, prov):
        return self.F["provs"].index(prov)

    def test_ranking(self):
        for sel, otros in (((), False), (("ALFA SAC", "GAMA SAC"), True), (("NADIE",), False)):
            with self.subTest(sel=sel, otros=otros):
                R = pv.armar_rank(_RANGO, list(sel) + (["Otros"] if otros else []), self.R["sello"])
                j = self._calc({"gran": "Mes", "op": "12m", "medida": "valor"}, R)
                ref, n80, tot = _ranking_ref(self.h, sel, otros)
                filas = {n: (v, e, x) for n, v, e, x in j["filas"] if n != "Otros"}
                self.assertEqual(set(filas), set(ref))
                for p, (v, e, x) in ref.items():
                    self.assertAlmostEqual(filas[p][0], v, places=6)
                    self.assertEqual(filas[p][1], e, p)
                    if x is None:
                        self.assertIsNone(filas[p][2])
                    else:
                        self.assertAlmostEqual(filas[p][2], x, places=6)
                self.assertEqual(j["n80"], n80)
                self.assertAlmostEqual(j["total"], tot, places=6)
                self.assertEqual("Otros" in [f[0] for f in j["filas"]], otros)
        self.assertEqual(dict((n, e) for n, _v, e, _x in self._calc({"gran": "Mes", "op": "12m", "medida": "valor"})["filas"])
                         ["BETA SAC"], "vuelve")

    def test_cifras_del_proveedor(self):
        for prov in ("ALFA SAC", "DELTA SAC", "GAMA SAC", "EPSILON SAC"):
            with self.subTest(prov=prov):
                j = self._calc({"gran": "Mes", "op": "12m", "medida": "valor", "foco": self._foco(prov)})
                self.assertEqual(j["p"], prov)
                compra, docs, ppv = _cifras_ref(self.h, prov)
                self.assertAlmostEqual(j["ci"][0], compra, places=6)
                self.assertEqual(j["ci"][1], docs)
                if ppv is None:
                    self.assertIsNone(j["ci"][2])
                else:
                    # El habitual viaja con 4 decimales: milésimas de sol.
                    self.assertAlmostEqual(j["ci"][2], ppv, delta=0.01)

    def test_la_curva(self):
        prods = self.F["prods"]
        casos = [(g, op, prod, med)
                 for g in ("Día", "Semana", "Mes", "Año", "Documento")
                 for op in (periodo.HEREDA, "3m", "12m", "Todo")
                 for prod, med in ((None, "valor"), ("Lomo fino", "cant"), ("Lomo fino", "precio"))]
        for g, op, prod, med in casos:
            with self.subTest(gran=g, op=op, prod=prod, medida=med):
                st = {"gran": g, "op": op, "medida": med, "foco": self._foco("ALFA SAC"),
                      "prod": prods.index(prod) if prod else None}
                j = self._calc(st)["C"]
                keys, ys, parc, ref = _curva_ref(self.h, "ALFA SAC", prod, g, op, med)
                self.assertEqual(len(j["keys"]), len(keys))
                if g != "Documento":
                    self.assertEqual(j["keys"], keys)
                for a, b in zip(j["ys"], ys):
                    if b is None:
                        self.assertIsNone(a)
                    else:
                        self.assertAlmostEqual(a, b, places=6)
                self.assertEqual(j["parc"], parc)
                if ref is None:
                    self.assertIsNone(j["ref"])
                else:
                    self.assertAlmostEqual(j["ref"], ref, places=6)

    def test_el_desglose(self):
        j = self._calc({"gran": "Mes", "op": "12m", "medida": "valor", "foco": self._foco("ALFA SAC")})
        keys, _ys, _p, _r = _curva_ref(self.h, "ALFA SAC", None, "Mes", "12m", "valor")
        src = agregar_periodo(self.h[self.h["prov"] == "ALFA SAC"].copy(), "Mes")
        piv = src.groupby(["prod", "_per_sort"])["valor"].sum().unstack().reindex(columns=keys[-6:]).fillna(0)
        orden = piv.sum(axis=1).sort_values(ascending=False, kind="stable").index.tolist()
        self.assertEqual([p for p, _m in j["D"]], orden)
        for p, m in j["D"]:
            for a, b in zip(m, piv.loc[p].tolist()):
                self.assertAlmostEqual(a, b, places=6)

    def test_la_historia_de_los_documentos(self):
        for prov in ("ALFA SAC", "DELTA SAC"):
            with self.subTest(prov=prov):
                j = self._calc({"gran": "Mes", "op": "12m", "medida": "valor", "foco": self._foco(prov)})["hd"]
                dias, sube = _historia_ref(self.h, prov)
                got = dict(j["dias"])
                self.assertEqual(set(got), set(dias))
                for d, v in dias.items():
                    self.assertEqual(got[d], None if pd.isna(v) else int(v), d)
                top = {d: (p, x) for d, p, x in j["top"]}
                self.assertEqual(set(top), set(sube))
                for d, (p, x) in sube.items():
                    self.assertEqual(top[d][0], p)
                    self.assertAlmostEqual(top[d][1], x, places=6)


if __name__ == "__main__":
    unittest.main()
