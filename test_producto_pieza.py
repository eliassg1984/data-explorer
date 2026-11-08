"""Compras › Producto como pieza propia (reglas #713 y #774).

Lo que recibe la pieza (`historial_pieza`, `armar_ranking`) y que el
navegador rehaga la curva con las MISMAS cuentas que Python: `serie` de
`producto.js` contra `_serie` de `producto.py`, en Chromium, en cada ventana
y cada grano. Desde la #774, también lo que se dejó de comprar, los indicadores y
«de dónde sale la diferencia» contra pandas, y la pantalla entera. Sin secrets ni
red; la parte de Chromium se salta si Playwright no está (es de
requirements-dev.txt).

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
_JS_LF = (_AQUI / "lista_ficha.js").read_text(encoding="utf-8")
_JS_TODO = (_AQUI.parent / "_xlsx.js").read_text(encoding="utf-8") + _JS_LF + _JS
_CSS = (_AQUI / "lista_ficha.css").read_text(encoding="utf-8") + (_AQUI / "producto.css").read_text(encoding="utf-8")

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

    def test_lo_que_se_dejo_de_comprar(self):
        r0, r1 = pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-30")
        prev = self.h[(self.h["fecha"] >= pd.Timestamp("2026-09-01")) & (self.h["fecha"] < r0)]
        rng = self.h[(self.h["fecha"] >= r0) & (self.h["fecha"] <= r1)]
        dj = P._dejados(rng, prev, self.h, r0, r1)
        # Nada se compró en octubre: todo lo de setiembre quedó afuera, del mayor al menor.
        self.assertEqual(set(dj.index), set(prev["prod"]))
        self.assertEqual(dj["prev"].tolist(), sorted(dj["prev"].tolist(), reverse=True))
        self.assertAlmostEqual(dj.loc["Lomo", "prev"], 745 + 237.75 + 800 + 380)
        # Compras en los 90 días antes: cuatro documentos y una línea sin número.
        self.assertEqual(dj.loc["Lomo", "n90"], 5)
        self.assertEqual(dj.loc["Lomo", "ult"], pd.Timestamp("2026-09-22"))
        # Un producto del rango no se cuenta como dejado.
        self.assertTrue(P._dejados(self.h, prev, self.h, r0, r1).empty)

    def test_viajan_en_el_ranking_sin_romper_el_json(self):
        r0, r1 = pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-30")
        rng = self.h[self.h["prod"] == "Bolsa"].assign(fecha=pd.Timestamp("2026-10-05"))
        prev = self.h[(self.h["fecha"] >= pd.Timestamp("2026-09-01")) & (self.h["fecha"] < r0)]
        res_p, res_f, res_s, pv = _ranking(pd.concat([self.h, rng]), r0, r1)
        dj = P._dejados(rng, prev, self.h, r0, r1)
        R = P.armar_ranking(res_p, res_f, res_s, self.F["nombres"], (r0, r1), r1, pv, 1, 0, self.sello, dejados=dj,
                            familias={"todas": [["ALIMENTOS", 5.0]], "elegidas": ["ALIMENTOS"]})
        json.dumps(R)
        self.assertEqual({self.F["nombres"][x[0]] for x in R["dejados"]}, set(dj.index))
        self.assertEqual(R["pagina"]["todas"], [["ALIMENTOS", "Alimentos", 5.0]])

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
            pg.add_script_tag(content=_JS_LF + js)
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


_ESTILOS = (":root{--alto-util:575px;--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);--text-muted:rgb(150,150,160);--accent:rgb(108,92,231);"
            "--accent-deep:rgb(73,56,184);--accent-tint:rgb(240,237,254);--accent-light:rgb(235,232,251);--bg-card:rgb(255,255,255);--bg-hover:rgb(247,246,251);"
            "--bg-primary:rgb(250,249,251);--rail-fondo:rgb(244,243,248);--border:rgb(230,230,235);--border-lavender:rgb(220,215,250);--line-soft:rgb(243,243,246);"
            "--danger-text:rgb(185,28,28);--success-text:rgb(15,118,110);--success-bg:rgb(225,245,240);--warning-text:rgb(180,72,15);--warning-bg:rgb(253,238,227);"
            "--warning:rgb(234,122,28);--shadow:none;--shadow-md:none}body{margin:0;font-family:sans-serif}")


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class LaPantalla(unittest.TestCase):
    """La pantalla de la regla #774: se monta como en la app, con sus dos montajes."""

    R0, R1 = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30")

    @classmethod
    def setUpClass(cls):
        hist = _hist()
        cls.sello = P.sello_historial(hist)
        cls.h, cls.F = P.historial_pieza(hist, cls.sello)
        res_p, res_f, res_s, prev = _ranking(cls.h, cls.R0, cls.R1)
        dias = (cls.R1 - cls.R0).days + 1
        rng = cls.h[(cls.h["fecha"] >= cls.R0) & (cls.h["fecha"] <= cls.R1)]
        p = cls.h[(cls.h["fecha"] >= cls.R0 - pd.Timedelta(days=dias)) & (cls.h["fecha"] < cls.R0)]
        cls.dj = P._dejados(rng, p, cls.h, cls.R0, cls.R1)
        cls.Rk = P.armar_ranking(res_p, res_f, res_s, cls.F["nombres"], (cls.R0, cls.R1), cls.h["fecha"].max(), prev, 3, 2, cls.sello,
                                 dejados=cls.dj, familias={"todas": [["A", 900.0], ["B", 300.0], ["SERV", 120.0]], "elegidas": ["A", "B"]})
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
          const G = window.__cpProd;
          Object.assign(G, { raiz: null, F: null, R: null, rankData: null, spark: null, pendFam: null });
          G.st = { kpi: 'todos', ver: 'todos', hasta: '1', ab: {}, q: '', sub: null, foco: null, amp: null, menu: null, tab: 'curva', gran: 'Mes', op: 'Todo', pw: '90', per: null, cprov: null, doc: null };
          window.__pedidos = [];
          document.querySelector('#montar').innerHTML = '';
          __montar({ data: F, parentElement: document.querySelector('#datos') });
          __montar({ data: JSON.parse(JSON.stringify(R)), parentElement: document.querySelector('#montar'), setTriggerValue: (...a) => window.__pedidos.push(a) });
        }""", [self.F, self.Rk])
        self.addCleanup(lambda: self.assertEqual(self.errores, []))

    def _texto(self, sel):
        return self.pg.locator(sel).first.inner_text()

    def test_las_cuentas_contra_pandas(self):
        j = self.pg.evaluate("""([F, R]) => {
          const C = window.__cpProdCalc, f = C.leerFicha(F), r = C.leerRank(R), V = C.vista(r, f, { kpi: 'todos', ver: 'todos', q: '' });
          return { n: V.base.length, vT: V.vT, prevT: V.prevT, n80: V.en80.size, nv: V.nv.length, rev: V.rev.length, dej: V.dej.map((p) => F.nombres[p.i]), seg: V.seg.length, dif: V.dif };
        }""", [self.F, self.Rk])
        h = self.h
        dias = (self.R1 - self.R0).days + 1
        rng = h[(h["fecha"] >= self.R0) & (h["fecha"] <= self.R1)]
        prev = h[(h["fecha"] >= self.R0 - pd.Timedelta(days=dias)) & (h["fecha"] < self.R0)]
        self.assertEqual(j["n"], rng["prod"].nunique())
        self.assertAlmostEqual(j["vT"], rng["valor"].sum(), places=2)
        self.assertAlmostEqual(j["prevT"], prev["valor"].sum(), places=2)
        v = rng.groupby("prod")["valor"].sum().sort_values(ascending=False)
        self.assertEqual(j["n80"], int((v.cumsum() / v.sum() < .8).sum() + 1))
        pr = prev.groupby("prod")["valor"].sum()
        self.assertEqual(j["nv"], int((~v.index.isin(pr.index)).sum()))
        self.assertEqual(j["rev"], rng.loc[rng["flag"] != "", "prod"].nunique())
        self.assertEqual(sorted(j["dej"]), sorted(set(pr.index) - set(v.index)))
        # Las cuatro partes suman el total.
        d = j["dif"]
        self.assertAlmostEqual(d["mas"] + d["men"] + d["nv"] + d["dej"], d["total"], places=2)
        self.assertAlmostEqual(d["total"], rng["valor"].sum() - prev["valor"].sum(), places=2)

    def test_abre_en_el_resumen(self):
        self.assertEqual(self.pg.locator(".lf-kpi").count(), 4)
        self.assertIn("En qué se va", self._texto(".lf-panel"))
        self.assertIn("Se dejaron de comprar", self._texto(".lf-dif"))
        self.assertIn("Fuera de esta cuenta", self._texto(".lf-fuera"))

    def test_no_pide_scroll_ni_se_sale(self):
        m = self.pg.evaluate("(()=>{const e=document.querySelector('.lf-main');return [e.scrollWidth-e.clientWidth, e.scrollHeight-e.clientHeight, document.documentElement.scrollWidth-innerWidth]})()")
        self.assertLessEqual(max(m), 1, m)

    def test_la_ficha_y_sus_pestanas(self):
        self.pg.locator("tbody tr[data-acc]", has_text="Lomo").click()
        self.assertEqual(self._texto(".lf-panel h3"), "Lomo")
        self.assertEqual(self.pg.locator(".lf-cf").count(), 0)
        self.assertEqual(self.pg.locator(".lf-frase").count(), 0)
        self.assertGreater(self.pg.locator(".lf-ba").count(), 0)
        self.pg.locator('.lf-panel [data-acc="tab"][data-v="resumen"]').click()
        self.assertEqual(self.pg.locator(".lf-cf").count(), 4)
        self.assertIn("revisar", self._texto(".lf-frase"))
        self.assertEqual(self.pg.locator(".lf-ba").count(), 0)
        self.assertEqual(self.pg.locator('.lf-panel [data-v="resumen"]').get_attribute("aria-pressed"), "true")
        self.pg.locator('.lf-panel [data-acc="tab"][data-v="curva"]').click()
        self.assertEqual(self.pg.locator(".lf-cf").count(), 0)
        self.assertEqual(self.pg.locator(".lf-frase").count(), 0)
        self.assertGreater(self.pg.locator(".lf-ba").count(), 0)
        self.assertGreater(self.pg.locator(".lf-pto.fl").count(), 0)
        hit = self.pg.locator(".lf-hit").last
        hit.hover()
        self.assertIn("Cantidad", self._texto(".lf-tip"))
        hit.click()
        self.assertEqual(self.pg.evaluate("__cpProd.st.tab"), "comp")
        self.pg.locator(".lf-fl .lf-quita", has_text="✕").first.click()
        self.pg.locator(".ft.cp .ft-l .ft-f[data-acc]").first.click()
        self.assertIn("Total del comprobante", self._texto(".lf-sub"))
        self.pg.locator(".lf-panel .lf-seg button", has_text="Proveedores").click()
        self.assertGreater(self.pg.locator(".ft.pv .ft-l .ft-f").count(), 0)
        self.pg.locator(".ft.pv .ft-l .ft-f").first.click()
        self.assertEqual(self.pg.evaluate("__cpProd.st.tab"), "comp")
        self.pg.locator(".lf-panel .lf-seg button", has_text="Períodos").click()
        self.assertGreater(self.pg.locator(".ft.pe .ft-l .ft-f").count(), 0)

    def test_resumen_conserva_la_pestana_y_el_alto_de_laptop(self):
        self.pg.locator('tbody tr[data-acc="fila"]').first.click()
        alto = self.pg.locator(".lf-main").bounding_box()["height"]
        self.pg.locator('.lf-panel [data-acc="tab"][data-v="resumen"]').click()
        self.pg.locator('tbody tr[data-acc="fila"]').nth(1).click()
        self.assertEqual(self.pg.evaluate("__cpProd.st.tab"), "resumen")
        self.assertEqual(self.pg.locator(".lf-cf").count(), 4)
        self.pg.evaluate("""(R) => __montar({ data: R,
          parentElement: document.querySelector('#montar'),
          setTriggerValue: (...a) => window.__pedidos.push(a) })""", self.Rk)
        self.assertEqual(self.pg.evaluate("__cpProd.st.tab"), "resumen")
        self.assertAlmostEqual(self.pg.locator(".lf-main").bounding_box()["height"], alto, delta=1)
        self.assertEqual(self.pg.locator(".lf-cf").count(), 4)
        self.assertEqual(self.pg.evaluate("__pedidos"), [])
        m = self.pg.evaluate("(()=>{const e=document.querySelector('.lf-main');return [e.scrollWidth-e.clientWidth, e.scrollHeight-e.clientHeight]})()")
        self.assertLessEqual(max(m), 1, m)

    def test_los_indicadores_y_lo_dejado_se_abre(self):
        self.pg.locator(".lf-kpi").nth(3).click()
        self.assertIn("Compras para revisar", self._texto(".lf-panel"))
        self.pg.locator(".lf-kpi").nth(3).click()
        if len(self.dj):
            self.pg.locator(".lf-kpi").nth(2).click()
            self.assertIn("Lo que se dejó de comprar", self._texto(".lf-panel"))
            self.pg.locator("tbody tr[data-acc]").first.click()
            self.pg.locator('.lf-panel [data-acc="tab"][data-v="resumen"]').click()
            self.assertIn("No se compró", self._texto(".lf-frase"))

    def test_por_familia_abre_y_cierra(self):
        self.pg.locator(".lf-tabs button", has_text="Por familia").click()
        self.assertEqual(self.pg.locator("tr.g0").count(), self.h[(self.h["fecha"] >= self.R0) & (self.h["fecha"] <= self.R1)]["fam"].nunique())
        self.pg.locator('select[data-sel="hasta"]').select_option("2")
        self.assertGreater(self.pg.locator('tbody tr[data-acc="fila"]').count(), 0)
        self.pg.locator('select[data-sel="hasta"]').select_option("0")
        self.assertEqual(self.pg.locator('tbody tr[data-acc="fila"]').count(), 0)
        self.pg.locator("tr.g0").first.click()
        self.assertGreater(self.pg.locator('tbody tr[data-acc="grupo"]').count(), self.pg.locator("tr.g0").count())

    def test_buscar_ampliar_familias_y_excel(self):
        b = self.pg.locator(".lf-busca")
        b.click()
        self.pg.keyboard.type("lomo", delay=20)
        self.assertEqual(self.pg.evaluate("document.querySelector('.lf-busca').value"), "lomo")
        self.assertEqual(self.pg.locator('tbody tr[data-acc="fila"]').count(), 1)
        b.fill("")
        # #789: «Detalle» suma columnas y el renglón de abajo de los indicadores;
        # ⤢ deja la lista sola debajo del nivel 2, y Esc vuelve.
        cols = self.pg.locator(".lf-t thead th").count()
        self.assertFalse(self.pg.locator(".lf-kpi .d").first.is_visible())
        self.pg.locator(".lf-switch").click()
        self.assertGreater(self.pg.locator(".lf-t thead th").count(), cols)
        self.assertTrue(self.pg.locator(".lf-kpi .d").first.is_visible())
        self.pg.locator(".lf-switch").click()
        self.assertEqual(self.pg.locator(".lf-t thead th").count(), cols)
        self.pg.locator(".lf-pie .lf-amp").click()
        self.assertEqual(self.pg.locator(".lf-panel").count(), 0)
        self.assertFalse(self.pg.locator(".lf-kpis").is_visible())
        self.pg.keyboard.press("Escape")
        self.assertEqual(self.pg.locator(".lf-panel").count(), 1)
        self.assertTrue(self.pg.locator(".lf-kpis").is_visible())
        self.pg.locator(".lf-link").click()
        self.assertIn("Vs. hab.", self.pg.locator(".lf-pop-como").inner_text())
        self.pg.keyboard.press("Escape")
        self.assertEqual(self.pg.locator(".lf-pop-como").count(), 0)
        self.pg.get_by_role("button", name="Sumarlas").click()
        self.assertEqual(self.pg.evaluate("__pedidos"), [["familias", ["A", "B", "SERV"]]])
        with self.pg.expect_download() as d:
            self.pg.locator('[data-acc="excel"]').click()
        self.assertIn("compras_productos", d.value.suggested_filename)

    def test_el_celular_no_se_desborda(self):
        self.pg.set_viewport_size({"width": 390, "height": 844})
        try:
            self.pg.locator("tbody tr[data-acc]").first.click()
            self.pg.locator('.lf-panel [data-acc="tab"][data-v="resumen"]').click()
            self.assertEqual(self.pg.locator(".lf-cf").count(), 4)
            self.assertLessEqual(self.pg.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 1)
        finally:
            self.pg.set_viewport_size({"width": 1323, "height": 619})


if __name__ == "__main__":
    unittest.main()
