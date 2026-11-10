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
from unittest.mock import patch

import numpy as np
import pandas as pd

import definicion_compra
from graficos.compras import _filtros_vista as fv
from graficos.compras import semanal as sm
from graficos.compras.producto import marcar_revisar
from graficos.compras._comun import (CON_IGV, DOC_FACTURAS, DOC_TODOS,
                                     _periodo_serie, documento_legible,
                                     filtrar_documento)

_AQUI = Path(sm.__file__).parent
# Como la monta `semanal.py`: los íconos de la app y la ficha de familias
# (reglas #821 y #843) van antepuestos.
_JS = ((_AQUI.parent / "iconos.js").read_text(encoding="utf-8")
       + (_AQUI / "ficha_familias.js").read_text(encoding="utf-8")
       + (_AQUI / "semanal.js").read_text(encoding="utf-8"))
_CSS = ((_AQUI.parent / "iconos.css").read_text(encoding="utf-8")
        + (_AQUI / "ficha_familias.css").read_text(encoding="utf-8")
        + (_AQUI / "semanal.css").read_text(encoding="utf-8"))
_COLS =("PROD", "FECHA", "CANT", "PUNIT", "PROV", "DOC", "VALOR", "FAM", "SUB",
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


def _armar_una_pantalla(familias=None):
    """Como `_compras_semanal_drill`: con los doce meses, lo de contra y la marca;
    y una compra a diez veces su precio, para «Para revisar»."""
    d_full = _compras()
    raro = d_full[(d_full["PROD"] == "Lomo") & (d_full["FECHA"] >= "2026-10-01") & (d_full["VALOR"] > 50)].index[0]
    d_full.loc[raro, "VALOR"] *= 10
    d = d_full[(d_full["FECHA"] >= _RANGO[0]) & (d_full["FECHA"] <= _RANGO[1])]
    hist = sm.con_marca(sm.lineas_pieza(d_full, _COLS))
    b = sm.lineas_pieza(d, _COLS)
    b["refT"], b["refS"] = sm.referencias(b, hist)
    b["flag"] = marcar_revisar(b["cant"], b["neto"], b["refT"], b["um"])
    nc = sm._lineas_nc(d.iloc[0:0], "FECHA", "PROD", "PROV", "DOC", "FAM", "SUB", "VALOR", "IGV", "TIPO",
                       DOC_TODOS, col_cant="CANT", col_punit="PUNIT", col_moneda="MONEDA")
    flags = {k: True for k in ("hay_fam", "hay_sub", "hay_prov", "hay_cant", "hay_doc", "hay_tipo", "hay_igv")}
    return hist, sm.armar_pieza(b, hist, nc, _RANGO, flags, "sello", contra=sm.lineas_contra(hist, _RANGO),
                                meses=sm.resumen_meses(hist, _RANGO[1]), familias=familias)


def _ficha(familias=(), subfamilias=()):
    """Lo que `_familias_de` le manda a la pieza cuando ella dibuja el filtro
    (regla #843): cuatro familias de la página —una sin compras en el rango—,
    sus subfamilias y las dos con que abre la vista."""
    P = fv.datos_ficha(
        "compras_sec_semanal", ["ALIMENTOS", "GASTOS", "LIMPIEZA", "VINOS"],
        {"ALIMENTOS": ("CARNES", "VERDURAS"), "VINOS": ("TINTOS",)},
        [["ALIMENTOS", 100.0], ["VINOS", 50.0], ["GASTOS", 9.0]],
        (familias, subfamilias), ("ALIMENTOS", "VINOS", "YA NO EXISTE"))
    return {**P, "en_panel": True}


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
                      "usd: 10, punit: 11, refT: 12, refS: 13, fl: 14 };", _JS)
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

    def test_efecto_del_precio_y_revisar_contra_python(self):
        # Lo mismo que Compras › Producto: lo pagado menos el habitual, sin las
        # líneas marcadas; y las marcadas, por producto y por valor (regla #770).
        h, P = _armar_una_pantalla()
        t = h[h["fecha"].between(*_RANGO)]
        ok = t[(t["flag"] == "") & (t["cant"] > 0) & t["ref"].notna()]
        por = (ok["neto"] - ok["ref"] * ok["cant"]).groupby(ok["prod"]).sum()
        V = self._calc_de(P, {})
        self.assertAlmostEqual(V["e"]["up"], por[por >= 1].sum(), places=0)
        self.assertAlmostEqual(V["e"]["dn"], por[por <= -1].sum(), places=0)
        self.assertEqual(V["e"]["nUp"], int((por >= 1).sum()))
        self.assertEqual(V["e"]["nDn"], int((por <= -1).sum()))
        rev = t[t["flag"] != ""]
        self.assertGreater(len(rev), 0)
        self.assertEqual(V["revLin"], len(rev))
        self.assertEqual(V["revProd"], rev["prod"].nunique())
        self.assertAlmostEqual(V["revVal"], rev["neto"].sum(), places=0)

    def test_doce_meses_y_contra(self):
        h, P = _armar_una_pantalla()
        m = P["meses"]
        self.assertEqual(len(m), 13)
        self.assertEqual(m[-1][0], "2026-10")
        octubre = h[h["fecha"].dt.to_period("M") == pd.Period("2026-10")]
        self.assertAlmostEqual(m[-1][1], octubre["neto"].sum(), places=1)
        # El mes sin compras también cuenta: la curva no salta meses.
        self.assertEqual(m[0][1], 0.0)
        # Contra el año pasado no hay base; contra el período anterior, sí.
        self.assertIsNone(self._calc_de(P, {"contra": "ano"})["contraTot"])
        V = self._calc_de(P, {"contra": "ant"})
        n = (_RANGO[1] - _RANGO[0]).days + 1
        ant = h[h["fecha"].between(_RANGO[0] - pd.Timedelta(days=n), _RANGO[0] - pd.Timedelta(days=1))]
        self.assertAlmostEqual(V["contraTot"], ant["neto"].sum(), places=0)
        self.assertGreater(len([x for x in V["ghost"] if x is not None]), 0)

    def _calc_de(self, P, st0):
        return self.pg.evaluate("""([P, st0]) => { const C = window.__cpPerCalc, F = C.leer(P);
          const V = C.calcular(F, { gran: 'Semana', fam: [], sub: [], prov: [], prod: [], docu: 'Todos', montos: 'Sin IGV', partir: 'Familia',
            res: {}, modo: 'Resumen Total', foco: null, doc: null, provDet: null, contra: 'ano', ...st0 });
          return { e: { up: V.efecto.up, dn: V.efecto.dn, nUp: V.efecto.nUp, nDn: V.efecto.nDn }, revProd: V.revProd, revLin: V.revLin, revVal: V.revVal,
            contraTot: V.contraTot, ghost: V.ghost }; }""", [P, st0])

    def test_una_pantalla_tablas_y_familias_de_la_pagina(self):
        fam = {"todas": [["ALIMENTOS", 100.0], ["VINOS", 50.0], ["GASTOS", 9.0]], "elegidas": ["ALIMENTOS", "VINOS"]}
        _h, P = _armar_una_pantalla(fam)
        pg = self.b.new_page(viewport={"width": 1323, "height": 680})
        try:
            pg.set_content('<style>:root{--alto-util:612px}body{margin:0 16px}</style><div id="pieza"></div>')
            pg.add_style_tag(content=_CSS)
            pg.add_script_tag(content=_JS.replace("export default function (component)", "window.__montar = function (component)"))
            pg.evaluate("""P => { window.__avisos = []; window.__montar({data: P, parentElement: document.querySelector('#pieza'), setTriggerValue: (k, v) => window.__avisos.push([k, v])}); }""", P)
            # #842: los indicadores abren plegados en el renglón de las pestañas.
            pg.wait_for_selector(".kcap")
            self.assertEqual(pg.locator(".kpi").count(), 0)
            self.assertIn("Compra", pg.locator(".kcap").inner_text())
            alto_n2 = pg.evaluate("document.querySelector('.n2').getBoundingClientRect().height")
            y_graf = pg.evaluate("document.querySelector('.graf').getBoundingClientRect().top")
            pg.locator(".kcap").click()
            self.assertEqual(pg.locator(".kpi").count(), 4)
            # Abierta no tapa las pestañas ni corre nada.
            self.assertGreaterEqual(pg.evaluate("document.querySelector('.ktira').getBoundingClientRect().left"),
                                    pg.evaluate("document.querySelector('.tabs').getBoundingClientRect().right"))
            self.assertEqual(pg.evaluate("document.querySelector('.n2').getBoundingClientRect().height"), alto_n2)
            self.assertEqual(pg.evaluate("document.querySelector('.graf').getBoundingClientRect().top"), y_graf)
            self.assertIn("Fuera de esta cuenta", pg.locator(".fuera").inner_text())
            for m in ("docs", "precio", "revisar", "valor"):
                pg.locator(f'.kpi[data-v="{m}"]').click()
                self.assertEqual(pg.locator(f'.kpi[data-v="{m}"].on').count(), 1)
                self.assertGreater(pg.locator(".graf svg").count(), 0)
            # Plegada con Esc, dice el elegido; con otro, el suyo.
            pg.locator('.kpi[data-v="docs"]').click()
            pg.keyboard.press("Escape")
            self.assertEqual(pg.locator(".kpi").count(), 0)
            self.assertIn("Documentos", pg.locator(".kcap").inner_text())
            pg.locator(".kcap").click()
            pg.locator('.kpi[data-v="valor"]').click()
            pg.locator(".kcerrar").click()
            self.assertIn("Compra", pg.locator(".kcap").inner_text())
            # Una pantalla: la pieza no pide scroll.
            self.assertLessEqual(pg.evaluate("document.querySelector('.cpp').getBoundingClientRect().bottom"), 680)
            # Con una tabla ancha: se desliza en su zona y no se mete en el panel.
            for z in ("tabla", "docs"):
                pg.locator(f'.tabs [data-v="{z}"]').click()
                panel = pg.locator(".panel").bounding_box()
                self.assertLessEqual(pg.evaluate("document.querySelector('.zona').getBoundingClientRect().right"), panel["x"])
                self.assertEqual(pg.evaluate("getComputedStyle(document.querySelector('.zona')).overflowX"), "auto")
                self.assertGreaterEqual(pg.evaluate("document.querySelector('.tb').offsetWidth"),
                                        pg.evaluate("parseInt(document.querySelector('.tb').style.minWidth)"))
            pg.locator('.tabs [data-v="graf"]').click()
            # Sumar lo de afuera escribe el filtro de la página, y eso pide una corrida.
            pg.locator('[data-acc="pagina-todas"]').click()
            self.assertEqual(pg.evaluate("window.__avisos"), [["familias", ["ALIMENTOS", "VINOS", "GASTOS"]]])
        finally:
            pg.close()

    def _montar(self, pg, P, sello=None):
        """Monta la pieza (o le manda datos nuevos, como una corrida de Python)."""
        if not pg.locator("#pieza").count():
            pg.set_content('<style>:root{--alto-util:612px;--border:silver;--bg-card:white;--accent:slateblue}body{margin:0 16px}</style><div id="pieza"></div>')
            pg.add_style_tag(content=_CSS)
            pg.add_script_tag(content=_JS.replace("export default function (component)", "window.__montar = function (component)"))
            pg.evaluate("window.__avisos = []")
        pg.evaluate("""P => window.__montar({data: P, parentElement: document.querySelector('#pieza'),
                         setTriggerValue: (k, v) => window.__avisos.push([k, v])})""", {**P, "sello": sello or P["sello"]})
        pg.wait_for_selector(".cab")
        # El `ResizeObserver` de la pieza redibuja a los 120 ms de montarla: medir
        # antes es medir un nodo que está por irse.
        pg.wait_for_timeout(250)

    def test_ficha_de_familias(self):
        """#843: el filtro de familias de la vista es una ficha al lado de «Más
        filtros»; se edita en su panel, se aplica al cerrarlo y la ✕ lo quita."""
        ultimo = "window.__avisos[window.__avisos.length - 1]"
        _h, P = _armar_una_pantalla(_ficha(("ALIMENTOS", "VINOS")))
        pg = self.b.new_page(viewport={"width": 1323, "height": 680})
        try:
            self._montar(pg, P)
            # Ni el menú de la página ni el de la pieza: la ficha, pegada a «Más filtros».
            self.assertEqual(pg.locator('[data-acc="menu"][data-v="pag"], [data-acc="menu"][data-v="fam"]').count(), 0)
            self.assertEqual(pg.locator(".ff-b").inner_text(), "2 de 4 familias")
            mas, chip, fx = (pg.locator(s).bounding_box() for s in (".ms-b", ".ff-chip", ".ff-x"))
            self.assertAlmostEqual(chip["x"] - (mas["x"] + mas["width"]), 4, delta=1)
            self.assertAlmostEqual(chip["y"] + chip["height"] / 2, mas["y"] + mas["height"] / 2, delta=1.5)
            # La ✕ es un botón aparte, hermano del que abre el panel, de 24 × 24.
            self.assertEqual(pg.locator(".ff-x").evaluate("e => e.tagName + ' en ' + e.parentElement.tagName"), "BUTTON en SPAN")
            self.assertGreaterEqual(fx["width"], 24)
            self.assertGreaterEqual(fx["height"], 24)
            # El indicador dice sobre qué familias mide.
            pg.locator(".kcap").click()
            self.assertEqual(pg.locator(".kpi .r").first.inner_text(), "Compra · 2 de 4 familias")
            pg.locator(".kcerrar").click()
            # El panel de la ficha: todas las familias de la página con lo que suman
            # —también la que no compró— y el campo de Subfamilia, plegado.
            pg.locator(".ff-b").click()
            self.assertEqual(pg.locator(".ff-l .ff-fams label").all_inner_texts(),
                             ["Alimentos\nS/ 100", "Vinos\nS/ 50", "Gastos\nS/ 9", "Limpieza\nS/ 0"])
            self.assertEqual(pg.locator(".ff-fams input:checked").count(), 2)
            self.assertEqual(pg.locator(".ff-l .ff-campo").inner_text().strip(), "Todas las subfamilias\n▾")
            self.assertEqual(pg.locator(".ff-subs").count(), 0)
            self.assertIn("Sólo esta vista", pg.locator(".ff-pie").inner_text())
            # Ya son las de siempre: sólo queda ofrecer todas.
            self.assertEqual(pg.locator(".ff-pie .ff-at").all_inner_texts(), ["Todas las familias"])
            panel = pg.locator(".ff-l").bounding_box()
            self.assertEqual(panel["width"], 300)
            self.assertLessEqual(panel["y"] + panel["height"], 680)
            # A 619 px de alto la hoja recorta 16 px debajo de la pieza: ni este panel
            # ni el de «Más filtros», con un campo abierto, pasan de ahí.
            pg.evaluate("document.documentElement.style.setProperty('--alto-util', '527px')")
            fondo = pg.evaluate("document.querySelector('.cpp').getBoundingClientRect().bottom") + 16
            pg.locator('.ff-l [data-acc="campo"]').click()
            pie = pg.locator(".ff-pie").bounding_box()
            self.assertLessEqual(pie["y"] + pie["height"], fondo)
            # El campo que se abre al pie queda a la vista, por encima del pie fijo.
            subs = pg.locator(".ff-subs").bounding_box()
            self.assertLessEqual(subs["y"] + subs["height"], pie["y"] + 1)
            pg.locator(".ms-b").click()
            pg.locator('.ms-l .ff-campo[data-v="prod"]').click()
            mas_l = pg.locator(".ms-l").bounding_box()
            self.assertLessEqual(mas_l["y"] + mas_l["height"], fondo)
            pg.evaluate("document.documentElement.style.setProperty('--alto-util', '612px')")
            pg.locator(".ff-b").click()
            # Marcar no manda nada: se aplica al cerrar.
            pg.locator('.ff-fams input[data-v="VINOS"]').click()
            self.assertEqual(pg.locator(".ff-pie .ff-ap").count(), 1)
            self.assertIn("Se aplica al cerrar", pg.locator(".ff-pie").inner_text())
            self.assertEqual(pg.evaluate("window.__avisos"), [])
            # La última familia no se desmarca.
            pg.locator('.ff-fams input[data-v="ALIMENTOS"]').click()
            self.assertTrue(pg.locator('.ff-fams input[data-v="ALIMENTOS"]').is_checked())
            # Las subfamilias son las de las familias marcadas, y el teclado no pierde su casilla.
            pg.locator('.ff-l [data-acc="campo"]').click()
            self.assertEqual(pg.locator(".ff-subs label").all_inner_texts(), ["Carnes", "Verduras"])
            pg.locator('.ff-subs input[data-v="CARNES"]').focus()
            pg.keyboard.press("Space")
            self.assertTrue(pg.locator('.ff-subs input[data-v="CARNES"]').is_checked())
            self.assertEqual(pg.evaluate("document.activeElement.dataset.v"), "CARNES")
            self.assertEqual(pg.locator(".ff-l .ff-campo").inner_text().strip(), "Carnes\n▾")
            pg.keyboard.press("Escape")
            pedido = {"fam": ["ALIMENTOS"], "sub": ["CARNES"]}
            self.assertEqual(pg.evaluate("window.__avisos"), [["familias", pedido]])
            # Mientras Python no contesta, la ficha dice lo pedido, apagada y sin botones.
            self.assertEqual(pg.locator(".ff-chip.espera").count(), 1)
            self.assertIn("Familia: Alimentos · Subfamilia: Carnes", pg.locator(".ff-chip").inner_text())
            self.assertEqual(pg.locator(".ff button").count(), 0)
            # Python lo acepta tal cual llega, y lo escribe en las claves de la vista.
            estado = {}
            with patch.object(fv.st, "session_state", estado):
                self.assertTrue(fv.aplicar_ficha(P["familias"], pedido))
                self.assertFalse(fv.aplicar_ficha(P["familias"], pedido))
            self.assertEqual((estado["cp_familias_semanal"], estado["cp_subfamilias_semanal"]), (["ALIMENTOS"], ["CARNES"]))
            # Llega la corrida con lo pedido: la ficha deja de esperar.
            _h, P2 = _armar_una_pantalla(_ficha(("ALIMENTOS",), ("CARNES",)))
            self._montar(pg, P2, "s2")
            self.assertEqual(pg.locator(".ff-chip.espera").count(), 0)
            self.assertEqual(pg.locator(".ff-b").inner_text(), "Familia: Alimentos · Subfamilia: Carnes")
            # «Aplicar» cierra y manda; lo que no cambia, no viaja.
            pg.locator(".ff-b").click()
            pg.locator('.ff-l [data-acc="campo"]').click()
            pg.locator('[data-acc="ffam-sublimpiar"]').click()
            pg.locator(".ff-pie .ff-ap").click()
            self.assertEqual(pg.evaluate(ultimo), ["familias", {"fam": ["ALIMENTOS"], "sub": []}])
            self._montar(pg, _armar_una_pantalla(_ficha(("ALIMENTOS",)))[1], "s3")
            pg.locator(".ff-b").click()
            pg.locator(".tabs [data-v='tabla']").click()
            self.assertEqual(pg.locator(".ff-l").count(), 0)
            self.assertEqual(pg.evaluate("window.__avisos.length"), 2)
            # «Las de siempre» y «Sumarlas» se piden en el acto; la ✕ también, con el teclado.
            pg.locator(".tabs [data-v='graf']").click()
            pg.locator(".ff-b").click()
            pg.locator('[data-acc="ffam-entrada"]').click()
            self.assertEqual(pg.evaluate(ultimo), ["familias", {"fam": ["ALIMENTOS", "VINOS"], "sub": []}])
            self._montar(pg, P, "s4")
            self.assertIn("Fuera de esta cuenta: S/ 9 de Gastos", pg.locator(".fuera").inner_text())
            pg.locator('.fuera [data-acc="ffam-todas"]').click()
            self.assertEqual(pg.evaluate(ultimo), ["familias", {"fam": [], "sub": []}])
            self._montar(pg, P, "s5")
            pg.locator(".ff-x").focus()
            pg.keyboard.press("Enter")
            self.assertEqual(pg.evaluate("window.__avisos.length"), 5)
            self.assertEqual(pg.evaluate(ultimo), ["familias", {"fam": [], "sub": []}])
            self.assertIn("Quitando el filtro", pg.locator(".ff-chip").inner_text())
            # Sin filtro no hay ficha: Familia y Subfamilia son campos de «Más filtros».
            self._montar(pg, _armar_una_pantalla(_ficha())[1], "s6")
            self.assertEqual(pg.locator(".ff-chip").count(), 0)
            self.assertEqual(pg.locator(".fuera").count(), 0)
            pg.locator(".ms-b").click()
            self.assertEqual(pg.locator(".ms-l .ff-campo").first.inner_text().strip(), "Todas las familias\n▾")
            pg.locator('.ms-l .ff-campo[data-v="ffam"]').click()
            self.assertEqual(pg.locator(".ms-l .ff-fams input:checked").count(), 4)
            self.assertEqual(pg.locator(".ms-l .ff-at").all_inner_texts(), ["Las de siempre"])
            # Con todas las familias, una subfamilia viaja con las cuatro escritas.
            pg.locator('.ms-l .ff-campo[data-v="ffsub"]').click()
            pg.locator('.ff-subs input[data-v="TINTOS"]').click()
            self.assertIn("se aplican al cerrar", pg.locator(".ms-l .ff-pie").inner_text())
            pg.keyboard.press("Escape")
            self.assertEqual(pg.evaluate(ultimo), ["familias", {"fam": ["ALIMENTOS", "VINOS", "GASTOS", "LIMPIEZA"], "sub": ["TINTOS"]}])
            with patch.object(fv.st, "session_state", estado):
                self.assertTrue(fv.aplicar_ficha(P["familias"], pg.evaluate(ultimo)[1]))
            self.assertEqual(estado["cp_subfamilias_semanal"], ["TINTOS"])
        finally:
            pg.close()

    def test_cabecera_como_el_boceto(self):
        """#844: el nivel 3 con las medidas del boceto: tres grupos, «Nombre: valor ▾»
        sin caja, las acciones como íconos y «Más filtros» con sus campos plegados."""
        _h, P = _armar_una_pantalla(_ficha(("ALIMENTOS", "VINOS")))
        pg = self.b.new_page(viewport={"width": 1323, "height": 680})
        caja = lambda s: pg.locator(s).first.bounding_box()  # noqa: E731
        try:
            self._montar(pg, P)
            # «Más filtros» arranca donde las pestañas, y los grupos se separan por cercanía.
            tabs, mas, chip, men = caja(".tabs"), caja(".ms-b"), caja(".ff-chip"), caja(".men")
            self.assertAlmostEqual(mas["x"], tabs["x"], delta=1)
            self.assertEqual((mas["height"], chip["height"], men["height"]), (32, 28, 32))
            self.assertAlmostEqual(chip["x"] - (mas["x"] + mas["width"]), 4, delta=1)
            self.assertAlmostEqual(men["x"] - (chip["x"] + chip["width"]), 24, delta=1)
            # Los menús de la vista: rótulo gris, valor y ▾, sin relleno; el select va encima.
            menus = "xs => xs.map((e) => [...e.children].filter((c) => c.tagName !== 'SELECT').map((c) => c.textContent).join(' '))"
            self.assertEqual(pg.locator(".men").evaluate_all(menus),
                             ["Agrupar: Semana ▾", "Partir por: Familia ▾", "Contra: año pasado ▾"])
            self.assertEqual(pg.locator(".men").first.evaluate("e => getComputedStyle(e).backgroundColor"), "rgba(0, 0, 0, 0)")
            self.assertEqual(pg.locator(".men select").first.evaluate("e => getComputedStyle(e).opacity"), "0")
            pg.locator('select[data-sel="gran"]').select_option("Mes")
            pg.locator('select[data-sel="contra"]').select_option("no")
            self.assertEqual(pg.locator(".men").evaluate_all(menus)[::2],
                             ["Agrupar: Mes ▾", "Contra: sin comparar ▾"])
            self.assertEqual(pg.evaluate("[window.__cpPer.st.gran, window.__cpPer.st.contra]"), ["Mes", "no"])
            # Las acciones, al final y detrás de una raya: un enlace y dos íconos con nombre.
            acc = pg.locator(".acc")
            self.assertEqual(acc.evaluate("e => getComputedStyle(e).borderLeftWidth"), "1px")
            self.assertEqual(acc.locator("> *").evaluate_all("xs => xs.map((e) => e.getAttribute('aria-label') || e.innerText.trim())"),
                             ["Cómo se calcula", "Descargar Excel", "Ampliar el gráfico"])
            for s in ('.acc [data-acc="excel"]', ".acc .amp-b", ".pn-cab .amp-b"):
                b = caja(s)
                self.assertEqual((b["width"], b["height"]), (32, 32), s)
                self.assertEqual(pg.locator(s).first.get_attribute("data-tip"), pg.locator(s).first.get_attribute("aria-label"))
                self.assertEqual(pg.locator(s).first.locator("svg.ico").count(), 1)
            der = caja(".acc")["x"] + caja(".acc")["width"]
            self.assertAlmostEqual(der, caja(".cab")["x"] + caja(".cab")["width"], delta=1)
            # Ampliar esconde el nivel 3; el camino de vuelta queda en el renglón del gráfico.
            pg.locator(".acc .amp-b").click()
            self.assertFalse(pg.locator(".cab").is_visible())
            self.assertEqual(pg.locator(".tit .amp-b").get_attribute("aria-label"), "Volver (Esc)")
            pg.keyboard.press("Escape")
            self.assertTrue(pg.locator(".cab").is_visible())
            self.assertEqual(pg.locator(".tit .amp-b").count(), 0)
            # «Más filtros»: cuatro campos plegados que dicen lo elegido, Documento y Montos.
            pg.locator(".ms-b").click()
            panel = caja(".ms-l")
            self.assertEqual(panel["width"], 300)
            self.assertAlmostEqual(panel["y"] - (mas["y"] + mas["height"]), 4, delta=1)
            self.assertEqual(pg.locator(".ms-l h4").all_inner_texts(), ["Familia", "Subfamilia", "Proveedor", "Producto", "Documento", "Montos"])
            self.assertEqual([t.replace("\n", " ").strip() for t in pg.locator(".ms-l .ff-campo").all_inner_texts()],
                             ["2 de 4 familias ▾", "Todas las subfamilias ▾", "Todos los proveedores ▾", "Todos los productos ▾"])
            self.assertEqual(pg.locator(".ms-l .ff-campo").evaluate_all("xs => xs.map((e) => e.getBoundingClientRect().height)"), [32] * 4)
            self.assertEqual(pg.locator(".ms-l input").count(), 0)
            self.assertEqual(pg.locator(".ms-l .mas").count(), 0)
            self.assertEqual(pg.locator(".ms-l .ops .on").all_inner_texts(), ["Todos", "Sin IGV"])
            self.assertLess(panel["height"], 420)
            # Un campo se abre ahí mismo, de a uno; elegir cambia lo que dice, y el botón avisa.
            pg.locator('.ms-l .ff-campo[data-v="prov"]').click()
            self.assertEqual(pg.locator(".ms-l .ms-q").count(), 1)
            pg.locator(".ms-l .ms-o input").first.check()
            self.assertEqual(pg.locator('.ms-l .ff-campo[data-v="prov"]').get_attribute("aria-expanded"), "true")
            self.assertNotIn("Todos los proveedores", pg.locator('.ms-l .ff-campo[data-v="prov"]').inner_text())
            self.assertIn("Más filtros · 1", pg.locator(".ms-b").inner_text())
            pg.locator('.ms-l .ff-campo[data-v="prod"]').click()
            self.assertEqual(pg.locator(".ms-l .ms-q").get_attribute("data-k"), "prod")
            pg.locator('.ms-l .ops [data-v="Facturas"]').click()
            self.assertEqual(pg.locator(".ms-l .ops .on").all_inner_texts(), ["Facturas", "Sin IGV"])
            self.assertIn("Más filtros · 2", pg.locator(".ms-b").inner_text())
            # Familia, desde «Más filtros»: la misma lista, y se aplica al cerrar.
            pg.locator('.ms-l .ff-campo[data-v="ffam"]').click()
            pg.locator('.ms-l .ff-fams input[data-v="GASTOS"]').click()
            self.assertEqual(pg.locator('.ms-l .ff-campo[data-v="ffam"]').inner_text().replace("\n", " ").strip(), "3 de 4 familias ▾")
            self.assertEqual(pg.locator(".ff-b").inner_text(), "2 de 4 familias")
            self.assertEqual(pg.evaluate("window.__avisos"), [])
            pg.keyboard.press("Escape")
            self.assertEqual(pg.evaluate("window.__avisos"), [["familias", {"fam": ["ALIMENTOS", "VINOS", "GASTOS"], "sub": []}]])
            # Cerrado el menú, el próximo abre con todo plegado.
            pg.locator(".ms-b").click()
            self.assertEqual(pg.locator(".ms-l .ff-cl").count(), 0)
            # Una pantalla: nada de esto la hace pedir scroll.
            pg.keyboard.press("Escape")
            self.assertLessEqual(pg.evaluate("document.querySelector('.cpp').getBoundingClientRect().bottom"), 680)
        finally:
            pg.close()

    def test_ficha_de_familias_en_el_celular(self):
        """#843: en el celular la ficha va con las demás fichas, y todo mide 44 px."""
        _h, P = _armar_una_pantalla(_ficha(("ALIMENTOS", "VINOS")))
        pg = self.b.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
        try:
            self._montar(pg, P)
            self.assertIn("1 activo", pg.locator(".filtros-toggle").inner_text())
            self.assertEqual(pg.locator('.filtro-estado [data-acc="ffam-quitar"]').inner_text(), "2 de 4 familias ×")
            self.assertFalse(pg.locator(".ff-chip").is_visible())
            pg.locator('[data-acc="panel-filtros"]').click()
            for s in (".ff-b", ".ff-x"):
                self.assertGreaterEqual(pg.locator(s).bounding_box()["height"], 44)
            self.assertGreaterEqual(pg.locator(".ff-x").bounding_box()["width"], 44)
            pg.locator(".ff-b").click()
            self.assertEqual(pg.locator(".ff-l").evaluate("e => getComputedStyle(e).position"), "static")
            self.assertGreaterEqual(pg.locator(".ff-fams label").first.bounding_box()["height"], 44)
            self.assertLessEqual(pg.locator(".cpp").evaluate("e => e.scrollWidth - e.clientWidth"), 1)
            # Cerrar los filtros aplica lo marcado.
            pg.locator('.ff-fams input[data-v="GASTOS"]').click()
            pg.locator('[data-acc="panel-filtros"]').click()
            self.assertEqual(pg.evaluate("window.__avisos"), [["familias", {"fam": ["ALIMENTOS", "VINOS", "GASTOS"], "sub": []}]])
        finally:
            pg.close()

    def test_movil_filtros_y_documentos_al_tocar(self):
        """El panel conserva la selección y el toque permite llegar al detalle."""
        pg = self.b.new_page(viewport={"width": 390, "height": 844}, has_touch=True)
        try:
            pg.set_content('<style>body {margin:12px}</style><div id="pieza"></div>')
            pg.add_style_tag(content=_CSS)
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
