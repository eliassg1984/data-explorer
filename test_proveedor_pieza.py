"""Compras › Proveedor como pieza propia (reglas #715 y #774).

Lo que recibe la pieza (`normalizar`, `historial_pieza`, `armar_rank`) y que
el navegador haga las MISMAS cuentas que la vista de antes (regla #646),
escritas acá en pandas: el ranking contra el período anterior de igual largo
(«nuevo», «vuelve», «Otros», el 80 %), las cifras del proveedor (documentos,
el «vs. precio habitual»), la curva en cada grano y ventana con el período
en curso y los mismos días del anterior, el Desglose y la historia de los
documentos. Corre `calcular` de `proveedor.js` en Chromium; sin Playwright
(es de requirements-dev.txt) esa parte se salta. Desde la #774, también los
indicadores contra pandas (el efecto del precio sin las compras marcadas, lo que
sólo se compra a uno, a quiénes ya no se les compró) y la pantalla entera.

    python test_proveedor_pieza.py
"""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from graficos import periodo
from graficos.compras import proveedor as pv
from graficos.compras.producto import marcar_revisar
from graficos.compras._comun import (agregar_periodo, inicio_de_periodo,
                                     tramo_parcial)
from graficos.compras.semanal import precio_habitual

_AQUI = Path(pv.__file__).parent
_JS = (_AQUI / "proveedor.js").read_text(encoding="utf-8")
_JS_TODO = (_AQUI.parent / "_xlsx.js").read_text(encoding="utf-8") + (_AQUI / "lista_ficha.js").read_text(encoding="utf-8") + _JS
_CSS = (_AQUI / "lista_ficha.css").read_text(encoding="utf-8") + (_AQUI / "proveedor.css").read_text(encoding="utf-8")
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
              ("EPSILON SAC", "Agua", 10.0, 20.0, "UND", pd.Timestamp("2026-10-05"), ""),
              # Una compra a 40 veces su habitual: entra en la cantidad, no en el precio.
              ("ALFA SAC", "Agua", 10.0, 800.0, "UND", pd.Timestamp("2026-10-12"), "F0099"),
              # Le compró el período anterior y en este no.
              ("ZETA SAC", "Agua", 10.0, 500.0, "UND", pd.Timestamp("2026-09-01"), "Z0001")]
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
    flag = marcar_revisar(h["cant"], h["valor"], ref, h["um"])
    ok = m & ref.notna() & (h["cant"] > 0) & (h["valor"] > 0) & (flag == "")
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
        self.assertIn("const RL = { dia: 0, prod: 1, doc: 2, cant: 3, valor: 4, ref: 5, um: 6, flag: 7 };", _JS)
        doc = " ".join(pv.historial_pieza.__doc__.split())
        self.assertIn("[día (desde `base`), producto (índice de `prods`), documento (índice de `docs`), cantidad, "
                      "valor, precio habitual o None, unidad (índice de `ums`), marca (índice de `_FLAGS`)]", doc)
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
        cls.pg.add_script_tag(content=(_AQUI / "lista_ficha.js").read_text(encoding="utf-8") + js)

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

    def test_los_indicadores_contra_pandas(self):
        j = self.pg.evaluate("""([F, R]) => {
          const C = window.__cpProvCalc, f = C.leerFicha(F), r = C.leerRank(R), P = C.panorama(f, r), rk = C.ranking(f, r);
          return { det: [...P.det].map(([p, a]) => [f.provs[p], a.ppv, a.docs.size, a.prods.size, a.nfl, [...a.solos].map((x) => f.prods[x]).sort(), a.vSolo]),
            ya: rk.yaNo.map((x) => [f.provs[x.p], x.prev]), totalVar: rk.total.var };
        }""", [self.F, self.R])
        h = self.h
        r0, r1 = _RANGO
        ref = precio_habitual(h["prod"], h["fecha"], h["valor"], h["cant"])
        flag = marcar_revisar(h["cant"], h["valor"], ref, h["um"])
        rng = h[(h["fecha"] >= r0) & (h["fecha"] <= r1)]
        w90 = h[(h["fecha"] > r1 - pd.Timedelta(days=90)) & (h["fecha"] <= r1)]
        uno = w90.groupby("prod")["prov"].nunique()
        solos = set(uno[uno == 1].index)
        for prov, ppv, docs, prods, nfl, sol, vsol in j["det"]:
            with self.subTest(prov=prov):
                x = rng[rng["prov"] == prov]
                ok = ref.loc[x.index].notna() & (x["cant"] > 0) & (x["valor"] > 0) & (flag[x.index] == "")
                self.assertAlmostEqual(ppv, float((x["valor"] - ref.loc[x.index] * x["cant"])[ok].sum()), delta=0.02)
                self.assertEqual(docs, x.loc[x["docu"].str.strip() != "", "docu"].nunique())
                self.assertEqual(prods, x["prod"].nunique())
                self.assertEqual(nfl, int((flag[x.index] != "").sum()))
                self.assertEqual(sol, sorted(set(x["prod"]) & solos))
                self.assertAlmostEqual(vsol, float(x.loc[x["prod"].isin(solos), "valor"].sum()), places=4)
        self.assertEqual([a for a, _b in j["ya"]], ["ZETA SAC"])
        # El total contra el período anterior es el de Producto: cuenta a todos.
        dias = (r1 - r0).days + 1
        prev = h[(h["fecha"] >= r0 - pd.Timedelta(days=dias)) & (h["fecha"] < r0)]["valor"].sum()
        self.assertAlmostEqual(j["totalVar"], (rng["valor"].sum() - prev) / prev * 100, places=6)

    def test_la_compra_marcada_no_mueve_el_precio(self):
        j = self._calc({"gran": "Mes", "op": "12m", "medida": "valor", "foco": self._foco("ALFA SAC")})
        h = self.h[self.h["docu"] != "F0099"]
        ref = precio_habitual(self.h["prod"], self.h["fecha"], self.h["valor"], self.h["cant"]).loc[h.index]
        r0, r1 = _RANGO
        m = (h["prov"] == "ALFA SAC") & (h["fecha"] >= r0) & (h["fecha"] <= r1) & ref.notna()
        flag = marcar_revisar(self.h["cant"], self.h["valor"], precio_habitual(self.h["prod"], self.h["fecha"], self.h["valor"], self.h["cant"]), self.h["um"])
        m = m & (flag[h.index] == "")
        self.assertAlmostEqual(j["ci"][2], float((h["valor"] - ref * h["cant"])[m].sum()), delta=0.02)

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


_ESTILOS = (":root{--alto-util:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--text-muted:rgb(150,150,160);--accent:rgb(108,92,231);"
            "--accent-deep:rgb(73,56,184);--accent-tint:rgb(240,237,254);--accent-light:rgb(235,232,251);--bg-card:rgb(255,255,255);--bg-hover:rgb(247,246,251);"
            "--bg-primary:rgb(250,249,251);--rail-fondo:rgb(244,243,248);--border:rgb(230,230,235);--border-lavender:rgb(220,215,250);--line-soft:rgb(243,243,246);"
            "--danger-text:rgb(185,28,28);--success-text:rgb(15,118,110);--success-bg:rgb(225,245,240);--warning-text:rgb(180,72,15);--warning-bg:rgb(253,238,227);"
            "--warning:rgb(234,122,28);--shadow:none;--shadow-md:none}body{margin:0;font-family:sans-serif}")


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class LaPantalla(unittest.TestCase):
    """La pantalla de la regla #774: se monta como en la app, con sus dos montajes."""

    @classmethod
    def setUpClass(cls):
        cls.h, cls.F, _R = _armar()
        familias = {"todas": [["ALIMENTOS", 900.0], ["SERVICIOS", 120.0]], "elegidas": ["ALIMENTOS"]}
        cls.R = pv.armar_rank(_RANGO, [], cls.F["sello"], familias)
        cls._pw = _chromium()().start()
        try:
            cls.b = cls._pw.chromium.launch()
        except Exception as e:
            cls._pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {e}")
        cls.pg = cls.b.new_page(viewport={"width": 1323, "height": 619})
        cls.errores = []
        cls.pg.on("pageerror", lambda e: cls.errores.append(str(e)))
        cls.pg.set_content('<div id="datos"></div><div id="montar"></div>')
        cls.pg.add_style_tag(content=_ESTILOS)
        cls.pg.add_style_tag(content=_CSS)
        cls.pg.add_script_tag(content=_JS_TODO.replace("export default function (component)", "window.__montar = function (component)"))

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls._pw.stop()

    def setUp(self):
        self.pg.evaluate("""([F, R]) => {
          const G = window.__cpProv;
          Object.assign(G, { raiz: null, F: null, R: null, rankData: null, pan: null, pendFam: null });
          G.st = { gran: 'Mes', op: '12m', medida: 'valor', tab: 'curva', pmodo: 'tot', dmodo: 'doc', kpi: 'todos', ver: 'todos', q: '', foco: null, per: null, amp: null, menu: null, abiertos: new Set() };
          window.__pedidos = [];
          document.querySelector('#montar').innerHTML = '';
          __montar({ data: F, parentElement: document.querySelector('#datos') });
          __montar({ data: JSON.parse(JSON.stringify(R)), parentElement: document.querySelector('#montar'), setTriggerValue: (...a) => window.__pedidos.push(a) });
        }""", [self.F, self.R])
        self.addCleanup(lambda: self.assertEqual(self.errores, []))

    def _texto(self, sel):
        return self.pg.locator(sel).first.inner_text()

    def test_abre_en_el_resumen_con_cuatro_indicadores(self):
        self.assertEqual(self.pg.locator(".lf-kpi").count(), 4)
        self.assertIn("A quién le compras", self._texto(".lf-panel"))
        self.assertIn("ya no se les compró", self._texto(".lf-frase"))
        self.assertEqual(self.pg.locator(".lf-izq .lf-seg button").count(), 4)
        self.assertIn("Fuera de esta cuenta", self._texto(".lf-fuera"))

    def test_no_pide_scroll_ni_se_sale(self):
        m = self.pg.evaluate("(()=>{const e=document.querySelector('.lf-main');return [e.scrollWidth-e.clientWidth, e.scrollHeight-e.clientHeight, document.documentElement.scrollWidth-innerWidth]})()")
        self.assertLessEqual(max(m), 1, m)

    def test_elegir_abre_la_ficha_y_soltar_vuelve(self):
        self.pg.locator("tbody tr[data-acc]").first.click()
        self.assertEqual(self.pg.locator(".lf-cf").count(), 4)
        self.assertEqual(self._texto(".lf-panel h3"), self.pg.evaluate("__cpProv.F.noms[__cpProv.st.foco]"))
        self.pg.get_by_role("button", name="Soltar").click()
        self.assertIn("A quién le compras", self._texto(".lf-panel"))

    def test_las_pestanas_y_el_clic_en_la_curva(self):
        self.pg.locator("tbody tr[data-acc]").first.click()
        self.assertGreater(self.pg.locator(".lf-ba").count(), 0)
        self.pg.locator(".lf-panel .lf-seg button", has_text="Productos").click()
        self.assertGreater(self.pg.locator(".ft.pl .ft-l .ft-f").count(), 0)
        self.pg.locator(".ft.pl .ft-l .ft-f").first.click()
        self.assertIn("Lo", self.pg.locator(".lf-panel .lf-quita").first.inner_text() + "Lo")
        self.assertGreater(self.pg.locator(".pl-provs .p90").count(), 0)
        self.pg.locator('.lf-panel select[data-sel="pmodo"]').select_option("per")
        self.assertGreater(self.pg.locator(".ft.pm .ft-l .ft-f").count(), 0)
        self.pg.locator(".lf-panel .lf-seg button", has_text="Curva").click()
        # Con un producto en foco se puede medir cantidad y precio; el precio va en línea.
        self.pg.locator('.lf-panel select[data-sel="medida"]').select_option("precio")
        self.assertEqual(self.pg.locator(".lf-ba").count(), 0)
        self.assertGreater(self.pg.locator(".lf-pto").count(), 0)
        self.pg.locator('.lf-panel select[data-sel="medida"]').select_option("valor")
        hit = self.pg.locator(".lf-hit").last
        hit.hover()
        self.assertFalse(self.pg.locator(".lf-tip").is_hidden())
        self.assertIn("clic: sus documentos", self._texto(".lf-tip"))
        hit.click()
        self.assertEqual(self.pg.evaluate("__cpProv.st.tab"), "doc")
        self.assertGreater(self.pg.locator(".ft.dd .ft-l .ft-f").count(), 0)

    def test_los_indicadores_filtran_y_el_seg_tambien(self):
        self.pg.locator(".lf-kpi").nth(3).click()
        self.assertIn("De quién dependes", self._texto(".lf-panel"))
        self.pg.locator(".lf-kpi").nth(3).click()
        self.pg.locator(".lf-izq .lf-seg button", has_text="Ya no").click()
        self.assertIn("Zeta", self._texto("tbody tr[data-acc]"))
        self.pg.locator("tbody tr[data-acc]").first.click()
        self.assertIn("No se le compró", self._texto(".lf-frase"))

    def test_ampliar_y_buscar_sin_perder_el_cursor(self):
        self.pg.locator(".lf-izq .lf-pil", has_text="Ampliar").click()
        self.assertEqual(self.pg.locator(".lf-panel").count(), 0)
        self.assertGreater(self.pg.locator("thead th").count(), 7)
        self.pg.locator(".lf-izq .lf-pil", has_text="Ver la ficha").click()
        b = self.pg.locator(".lf-busca")
        b.click()
        self.pg.keyboard.type("alfa", delay=20)
        self.assertEqual(self.pg.evaluate("document.querySelector('.lf-busca').value"), "alfa")
        self.assertEqual(self.pg.locator("tbody tr[data-acc]").count(), 1)

    def test_las_familias_las_pide_a_python_y_el_excel_baja(self):
        self.pg.get_by_role("button", name="Sumarlas").click()
        self.assertEqual(self.pg.evaluate("__pedidos"), [["familias", ["ALIMENTOS", "SERVICIOS"]]])
        with self.pg.expect_download() as d:
            self.pg.locator('[data-acc="excel"]').click()
        self.assertIn("compras_proveedores", d.value.suggested_filename)

    def test_avisa_a_detalle_docs_si_cambia_el_filtro(self):
        self.pg.evaluate("""(R) => { window.__aviso = null; window.addEventListener('compras-proveedores-cambio', (e) => { window.__aviso = e.detail; });
          __montar({ data: { ...R, sel: ['ALFA SAC'] }, parentElement: document.querySelector('#montar') }); }""", self.R)
        self.assertEqual(self.pg.evaluate("__aviso.sel"), ["ALFA SAC"])

    def test_el_celular_no_se_desborda(self):
        self.pg.set_viewport_size({"width": 390, "height": 844})
        try:
            self.pg.locator("tbody tr[data-acc]").first.click()
            self.assertLessEqual(self.pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 1)
            self.assertEqual(self.pg.evaluate("getComputedStyle(document.querySelector('.lf-kpis')).gridTemplateColumns.split(' ').length"), 2)
        finally:
            self.pg.set_viewport_size({"width": 1323, "height": 619})


if __name__ == "__main__":
    unittest.main()
