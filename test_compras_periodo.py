"""Compras › «Compras por período» como pieza propia (regla #716).

Lo que recibe la pieza (`lineas_pieza`, `referencias`, `armar_pieza`) y que
el navegador haga las MISMAS cuentas que la vista de antes, que siguen en
`semanal.py` (las usan también las tarjetas «por período» de Movimientos):
`calcular` de `semanal.js` contra `_variaciones`, `_rotulo_periodo`,
`partes_por_columna`, `partes_por_precio` (con `_precio_habitual_de`),
`_familias_de`, `detalle_con_notas` y `_plan_etiquetas`, en Chromium, en
cada grano, con Documento y Montos y con los filtros. Sin Playwright (es de
requirements-dev.txt) esa parte se salta.

    python test_compras_periodo.py
"""

import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import definicion_compra
from graficos.compras import semanal as sm
from graficos.compras._comun import (CON_IGV, DOC_FACTURAS, DOC_TODOS,
                                     _periodo_serie, documento_legible,
                                     filtrar_documento)

_JS = (Path(sm.__file__).parent / "semanal.js").read_text(encoding="utf-8")
_COLS = ("PROD", "FECHA", "CANT", "PUNIT", "PROV", "DOC", "VALOR", "FAM", "SUB",
         "IGV", "TIPO", "MONEDA")
_RANGO = (pd.Timestamp("2026-08-20"), pd.Timestamp("2026-10-22"))


def _compras():
    """Compras de mentira: cuatro proveedores, seis productos en dos familias
    y tres subfamilias, facturas y guías (sin IGV), una en dólares, desde
    junio (el precio habitual mira 90 días atrás)."""
    rng = np.random.default_rng(11)
    prods = [("Lomo", "ALIMENTOS", "CARNES", 70.0), ("Pato", "ALIMENTOS", "CARNES", 50.0),
             ("Lechuga", "ALIMENTOS", "VERDURAS", 3.0), ("Tomate", "ALIMENTOS", "VERDURAS", 4.0),
             ("Malbec", "VINOS", "TINTOS", 60.0), ("Syrah", "VINOS", "TINTOS", 55.0)]
    provs = ["ALFA SAC", "BETA EIRL", "GAMA S.A.C.", "DELTA SAC"]
    filas, n = [], 0
    for f in pd.date_range("2026-06-01", "2026-10-22", freq="D"):
        for _ in range(int(rng.integers(0, 4))):
            n += 1
            prov = provs[int(rng.integers(0, 4))]
            tipo = "Guía de Remisión" if rng.random() < 0.15 else "FACTURA"
            for k in rng.choice(6, size=int(rng.integers(1, 4)), replace=False):
                nom, fam, sub, base = prods[k]
                c = float(rng.integers(1, 20))
                neto = round(c * base * (1 + 0.15 * rng.standard_normal()), 4) / 1.18 * 1.18
                igv = 0.0 if (sub == "VERDURAS" or tipo != "FACTURA") else round(neto * 0.18, 6)
                filas.append((nom, f, c, neto / c, prov, f"F0E00100000{n:04d}", neto, fam, sub, igv, tipo,
                              "02" if n == 7 else "01"))
    return pd.DataFrame(filas, columns=list(_COLS))


def _notas(d):
    """Dos notas de crédito sobre facturas del rango: una por un producto
    entero, otra por la mitad de una línea."""
    fac = d[(d["FECHA"] >= _RANGO[0]) & (d["TIPO"] == "FACTURA")]
    a, b = fac.iloc[3], fac.iloc[20]
    nc = pd.DataFrame([a, b]).reset_index(drop=True)
    nc.loc[1, ["CANT", "VALOR", "IGV"]] = nc.loc[1, ["CANT", "VALOR", "IGV"]] / 2
    nc[definicion_compra.COL_NOTA] = ["N0E001000000011", "N0E001000000012"]
    nc[definicion_compra.COL_FECHA_NC] = nc["FECHA"] + pd.Timedelta(days=3)
    return nc


def _armar():
    d_full = _compras()
    d = d_full[(d_full["FECHA"] >= _RANGO[0]) & (d_full["FECHA"] <= _RANGO[1])]
    nc_raw = _notas(d)
    b = sm.lineas_pieza(d, _COLS)
    hist = sm.lineas_pieza(d_full, _COLS)
    b["refT"], b["refS"] = sm.referencias(b, hist)
    nc = sm._lineas_nc(nc_raw, "FECHA", "PROD", "PROV", "DOC", "FAM", "SUB", "VALOR", "IGV", "TIPO",
                       DOC_TODOS, col_cant="CANT", col_punit="PUNIT", col_moneda="MONEDA")
    nc = nc.assign(fecha=pd.to_datetime(nc["fecha"]).dt.normalize(),
                   fecha_nc=pd.to_datetime(nc["fecha_nc"]).dt.normalize())
    flags = {k: True for k in ("hay_fam", "hay_sub", "hay_prov", "hay_cant", "hay_doc", "hay_tipo", "hay_igv")}
    return d, d_full, nc_raw, sm.armar_pieza(b, hist, nc, _RANGO, flags, sm.sello_pieza(b, nc, hist))


# ── La vista de antes, en pandas (el `dd` del drill) ───────────────────


def _dd_ref(d, d_full, gran, docu, con_igv, fam=(), prov=()):
    d = filtrar_documento(d, "TIPO", docu)
    d_full = filtrar_documento(d_full, "TIPO", docu)
    valor = d["VALOR"] + (d["IGV"] if con_igv else 0)
    dd = pd.DataFrame({"fecha": d["FECHA"], "prod": d["PROD"], "prov": d["PROV"], "docn": d["DOC"],
                       "cant": d["CANT"], "valor": valor, "neto": d["VALOR"], "igv": d["IGV"],
                       "fam": d["FAM"], "sub": d["SUB"], "tipo": np.where(d["TIPO"] == "FACTURA", "F", "G")})
    if fam:
        dd = dd[dd["fam"].isin(fam)]
    if prov:
        dd = dd[dd["prov"].isin(prov)]
    dd["compra"] = dd["fecha"].dt.strftime("%Y-%m-%d") + "·" + dd["prov"] + "·" + dd["docn"]
    dd["clave"] = dd["compra"] if gran == "Por documento" else _periodo_serie(dd["fecha"], gran)
    return dd, d, d_full


class LoQueRecibe(unittest.TestCase):
    def test_todas_las_lineas_con_su_habitual(self):
        d, _f, _n, P = _armar()
        self.assertEqual(len(P["lineas"]), len(d))
        self.assertEqual(len(P["notas"]), 2)
        con = sum(1 for x in P["lineas"] if x[12] is not None)
        self.assertGreater(con, len(d) * 0.8)
        self.assertEqual(P["nota_doc"], ["E001-11", "E001-12"])
        self.assertEqual(P["rango"], ["2026-08-20", "2026-10-22"])

    def test_el_js_lee_las_mismas_posiciones(self):
        self.assertIn("const RL = { dia: 0, prod: 1, prov: 2, doc: 3, fam: 4, sub: 5, cant: 6, neto: 7, igv: 8, tipo: 9, "
                      "usd: 10, punit: 11, refT: 12, refS: 13 };", _JS)
        self.assertIn("const RN = { nota: 12, diaNc: 13 };", _JS)
        self.assertIn("const TIPOS = ['F', 'G', 'O'];", _JS)
        self.assertEqual(sm._TIPOS, ("F", "G", "O"))
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
        cls.d, cls.d_full, cls.nc_raw, cls.P = _armar()
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

    def _calc(self, st):
        return self.pg.evaluate("""([P, st0]) => {
          const C = window.__cpPerCalc, F = C.leer(P);
          const st = { gran: 'Semana', fam: [], sub: [], prov: [], prod: [], docu: 'Todos', montos: 'Sin IGV', partir: 'Subfamilia',
            res: {}, modo: 'Resumen Total', foco: null, doc: null, provDet: null, ...st0 };
          const V = C.calcular(F, st);
          if (V.vacio) return { vacio: true };
          const fam = C.familiasDe(V.dd, 3);
          const det = new Map();
          V.ddDet.forEach((l) => det.set(l.compra, (det.get(l.compra) || 0) + l.v));
          return { claves: V.claves, tot: V.tot, ndocs: V.ndocs, nlin: V.nlin, vars: V.vars, lbls: V.lbls,
            partes: V.partes.map(([r, c, v]) => [r, v]), extra: V.extra,
            fam: { top: fam.top.map(([f, v]) => [F.fams[f], v]), resto: fam.resto },
            det: [...det.values()].sort((a, b) => a - b), ncTot: V.ncTot,
            provs: V.provOps, prods: V.prodOps };
        }""", [self.P, st])

    def test_barras_en_cada_grano(self):
        for gran in ("Día", "Semana", "Mes", "Año", "Por documento"):
            for docu in (DOC_TODOS, DOC_FACTURAS):
                for montos in ("Sin IGV", CON_IGV):
                    with self.subTest(gran=gran, docu=docu, montos=montos):
                        j = self._calc({"gran": gran, "docu": docu, "montos": montos, "partir": "Proveedor"})
                        dd, _d, _f = _dd_ref(self.d, self.d_full, gran, docu, montos == CON_IGV)
                        claves = sorted(dd["clave"].unique())
                        self.assertEqual(len(j["claves"]), len(claves))
                        if gran != "Por documento":
                            self.assertEqual(j["claves"], claves)
                        tot = dd.groupby("clave")["valor"].sum().reindex(claves).tolist()
                        for a, b in zip(j["tot"], tot):
                            self.assertAlmostEqual(a, b, places=4)
                        self.assertEqual(j["ndocs"], dd.groupby("clave")["compra"].nunique().reindex(claves).tolist())
                        self.assertEqual(j["nlin"], dd.groupby("clave").size().reindex(claves).tolist())
                        if gran in ("Día", "Semana", "Mes"):
                            rango = tuple(x.date() for x in _RANGO)
                            ref = sm._variaciones(claves, tot, gran, rango)
                            for a, b in zip(j["vars"], ref):
                                self.assertEqual(a[0], b[0])
                                if b[1] is not None:
                                    self.assertAlmostEqual(a[1], b[1], places=6)
                            if gran != "Día":
                                self.assertEqual(j["lbls"], [sm._rotulo_periodo(k, gran, rango)[0] for k in claves])

    def test_partir_por_subfamilia_y_proveedor(self):
        for partir, campo, resto in (("Subfamilia", "sub", "Otras"), ("Proveedor", "prov", "Otros")):
            with self.subTest(partir=partir):
                j = self._calc({"gran": "Semana", "partir": partir})
                dd, _d, _f = _dd_ref(self.d, self.d_full, "Semana", DOC_TODOS, False)
                claves = sorted(dd["clave"].unique())
                nombrar = sm._rotulo_subfamilia if campo == "sub" else sm._rotulo_proveedor
                ref = sm.partes_por_columna(dd, campo, claves, orden=[], resto=resto, nombrar=nombrar)
                self.assertEqual([r for r, _v in j["partes"]], [r for r, _c, _v in ref])
                for (_r, a), (_r2, _c, b) in zip(j["partes"], ref):
                    for x, y in zip(a, b):
                        self.assertAlmostEqual(x, y, places=4)

    def test_partir_por_precio(self):
        for docu in (DOC_TODOS, DOC_FACTURAS):
            with self.subTest(docu=docu):
                j = self._calc({"gran": "Semana", "partir": "Precio", "docu": docu})
                dd, d, d_full = _dd_ref(self.d, self.d_full, "Semana", docu, False)
                claves = sorted(dd["clave"].unique())
                dd["ref"] = sm._precio_habitual_de(dd, d, d_full, "PROD", "FECHA", "VALOR", "CANT")
                partes, _pila, extra = sm.partes_por_precio(dd, claves)
                self.assertEqual([r for r, _v in j["partes"]], [r for r, _c, _v in partes])
                for (_r, a), (_r2, _c, b) in zip(j["partes"], partes):
                    for x, y in zip(a, b):
                        self.assertAlmostEqual(x, y, places=3)
                # El texto del hover: el neto contra el habitual, en las mismas palabras.
                for k, c in enumerate(claves):
                    if "Neto:" in extra[c]:
                        self.assertIn("contra el precio habitual", j["extra"][k])

    def test_filtros_y_familias(self):
        j = self._calc({"gran": "Mes", "fam": ["ALIMENTOS"], "prov": ["ALFA SAC"]})
        dd, _d, _f = _dd_ref(self.d, self.d_full, "Mes", DOC_TODOS, False, fam=["ALIMENTOS"], prov=["ALFA SAC"])
        self.assertAlmostEqual(sum(j["tot"]), float(dd["valor"].sum()), places=4)
        j = self._calc({"gran": "Mes"})
        dd, _d, _f = _dd_ref(self.d, self.d_full, "Mes", DOC_TODOS, False)
        total, top, resto = sm._familias_de(dd, n=3)
        self.assertEqual([f for f, _v in j["fam"]["top"]], [f for f, _v, _p in top])
        self.assertEqual(j["fam"]["resto"][0], resto[0])
        # Proveedor y Producto se ofrecen por valor, y un «Top N» suma sus N.
        val = dd.groupby("prov")["valor"].sum().sort_values(ascending=False)
        self.assertEqual(j["provs"], val.index.tolist())
        self.assertEqual(j["prods"][0], "Top 5 por valor")
        top5 = self._calc({"gran": "Mes", "prod": ["Top 5 por valor"]})
        p5 = dd.groupby("prod")["valor"].sum().sort_values(ascending=False).index[:5]
        self.assertAlmostEqual(sum(top5["tot"]), float(dd[dd["prod"].isin(p5)]["valor"].sum()), places=4)

    def test_notas_de_credito_en_el_detalle(self):
        j = self._calc({"gran": "Semana"})
        dd, _d, _f = _dd_ref(self.d, self.d_full, "Semana", DOC_TODOS, False)
        ncd = sm._lineas_nc(self.nc_raw, "FECHA", "PROD", "PROV", "DOC", "FAM", "SUB", "VALOR", "IGV", "TIPO",
                            DOC_TODOS, col_cant="CANT", col_punit="PUNIT", col_moneda="MONEDA")
        ncd = ncd.assign(valor=ncd["neto"], clave=_periodo_serie(ncd["fecha"], "Semana"))
        dd = dd.assign(doc=documento_legible(dd["docn"]), lbl="", usd=False, punit=np.nan)
        self.assertAlmostEqual(j["ncTot"], float(ncd["valor"].sum()), places=4)
        det = sm.detalle_con_notas(dd, ncd).groupby("compra")["valor"].sum().sort_values().tolist()
        self.assertEqual(len(j["det"]), len(det))
        for a, b in zip(j["det"], det):
            self.assertAlmostEqual(a, b, places=4)

    def test_rotulos_y_etiquetas(self):
        rango = (pd.Timestamp("2026-08-01").date(), pd.Timestamp("2026-10-07").date())
        claves = sorted(_periodo_serie(pd.Series(pd.date_range("2026-07-27", "2026-10-11")), "Semana").unique())
        claves += ["2026-01", "2026-08", "2026-09", "2026-12"]
        for k in claves:
            gran = "Semana" if "-S" in k else "Mes"
            with self.subTest(k=k):
                js = self.pg.evaluate("([k, g, r]) => window.__cpPerCalc.rotuloPeriodo(k, g, r.map((s) => Date.UTC(...s.split('-').map((x, i) => i === 1 ? x - 1 : +x)) / 864e5))",
                                      [k, gran, [str(x) for x in rango]])
                self.assertEqual(js, list(sm._rotulo_periodo(k, gran, rango)))
        # `_plan_etiquetas` con el ancho y el alto que usaba Python.
        lineas = [["S/ 15.5k", "36 docs", "parcial"], ["S/ 24.1k", "34 docs"], ["S/ 38.1k", "54 docs", "+58%"]] * 3
        for n, alto in ((5, 300), (9, 300), (30, 240), (31, 160), (260, 300)):
            with self.subTest(n=n, alto=alto):
                ls = (lineas * 40)[:n]
                ref = sm._plan_etiquetas(n, ls, alto)
                js = self.pg.evaluate("([ls, px, area]) => window.__cpPerCalc.planEtiquetas(ls.map((l) => l.map((t) => [t, t])), px, area, 0.45)",
                                      [ls, sm._LIENZO_PX / n, sm._alto_area_trazo(alto)])
                self.assertEqual(js[0], ref[0])
                self.assertEqual(js[1], ref[1])
                self.assertAlmostEqual(js[2], ref[2], places=6)

    def test_movil_filtros_y_documentos_al_tocar(self):
        """El panel conserva la selección y el toque permite llegar al detalle."""
        pg = self.b.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
        try:
            pg.set_content('<style>body {margin:12px}</style><div id="pieza"></div>')
            pg.add_style_tag(content=(Path(sm.__file__).parent / "semanal.css").read_text(encoding="utf-8"))
            pg.add_script_tag(content=_JS.replace("export default function (component)", "window.__montar = function (component)"))
            pg.evaluate("P => window.__montar({data:P,parentElement:document.querySelector('#pieza')})", self.P)
            pg.locator('.cpp').wait_for()
            self.assertFalse(pg.locator('.fils').is_visible())
            pg.locator('[data-acc="panel-filtros"]').click()
            pg.locator('[data-acc="menu"][data-v="fam"]').click()
            pg.locator('.ms-o input').first.check()
            seleccion = pg.evaluate('window.__cpPer.st.fam.slice()')
            self.assertEqual(len(seleccion), 1)
            pg.locator('[data-acc="panel-filtros"]').click()
            self.assertFalse(pg.locator('.fils').is_visible())
            self.assertEqual(pg.evaluate('window.__cpPer.st.fam'), seleccion)
            self.assertIn('1 activo', pg.locator('.filtros-toggle').inner_text())
            pg.locator('.hit').first.click()
            self.assertTrue(pg.locator('.lectura').is_visible())
            self.assertIn('Total', pg.locator('.lectura').inner_text())
            pg.locator('[data-acc="ver-barra"]').click()
            self.assertEqual(pg.evaluate('window.__cpPer.st.modo'), 'Detalle')
            self.assertIsNotNone(pg.evaluate('window.__cpPer.st.foco'))
            pg.locator('[data-acc="restablecer"]').click()
            self.assertEqual(pg.evaluate('window.__cpPer.st.fam'), [])
            self.assertFalse(pg.locator('.lectura').count())
            self.assertLessEqual(pg.locator('.cpp').evaluate('e=>e.scrollWidth-e.clientWidth'), 1)
            for w, h in ((320, 700), (844, 390)):
                pg.set_viewport_size({"width": w, "height": h})
                pg.wait_for_timeout(250)
                self.assertFalse(pg.locator('.etq[transform]').count())
                self.assertLessEqual(pg.locator('.cpp').evaluate('e=>e.scrollWidth-e.clientWidth'), 1)
            pg.set_viewport_size({"width": 1366, "height": 768})
            pg.wait_for_timeout(250)
            self.assertFalse(pg.locator('.filtros-toggle').is_visible())
            self.assertTrue(pg.locator('.fils').is_visible())
        finally:
            pg.close()


if __name__ == "__main__":
    unittest.main()
