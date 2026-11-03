"""Ajuste › Detalle histórico como pieza propia (#809): lo que Python manda y, en
Chromium, que los conteos, los indicadores y la tabla dinámica del navegador den lo
mismo que pandas, la ficha, «Detalle», «Ampliar» con Esc y el Excel."""
import json
import unittest
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from graficos.ajuste import _historico_datos as datos

ROOT = Path(__file__).parent


def muestra():
    rows = []

    def add(fecha, area, fam, sub, prod, cod, um, sis, fis, val, stock):
        rows.append({"FECHA APERTURA INVENTARIO": fecha, "AREA": area, "FAMILIA": fam,
                     "SUBFAMILIA": sub, "NOMBRE PRODUCTO": prod, "CODIGO PRODUCTO": cod,
                     "UNIDAD MEDIDA": um, "STOCK AL CIERRE": sis, "STOCK DECLARADO": fis,
                     "AJUSTE": None if sis is None else fis - sis, "AJUSTE VALORIZADO": val,
                     "VALORIZADO TOTAL": stock})
    add("2026-09-01 08:10", "COCINA", "ALIMENTOS", "CARNES", "Lomo", "0000000010", "KILOS", 10, 8, -100.0, 400.0)
    add("2026-09-01 08:20", "COCINA", "ALIMENTOS", "SECOS", "Arroz", "0000000011", "KILOS", 5, 6, 4.5, 27.0)
    add("2026-09-01 09:00", "BARRA", "BEBIDAS", "VINOS", "Malbec", "0000000012", "BOT", 12, 12, 0.0, 600.0)
    add("2026-09-15 10:00", "BARRA", "BEBIDAS", "VINOS", "Malbec", "0000000012", "BOT", 12, 10, -120.0, 500.0)
    add("2026-10-02 08:00", "COCINA", "ALIMENTOS", "CARNES", "Lomo", "0000000010", "KILOS", 9, 9.5, 25.0, 475.0)
    add("2026-10-02 08:30", "SALON", "COSTOS PRODUCCION", "MENAJE", "Cuchillos", None, "UND", 20, 18, -30.0, None)
    add(None, "COCINA", "ALIMENTOS", "SECOS", "Sin fecha", "0000000099", "KILOS", 1, 0, -3.0, 0.0)
    return pd.DataFrame(rows).assign(**{"FECHA APERTURA INVENTARIO": lambda d: pd.to_datetime(d["FECHA APERTURA INVENTARIO"])})


def pandas_lineas():
    d = muestra().dropna(subset=["FECHA APERTURA INVENTARIO"]).copy()
    d["dia"] = d["FECHA APERTURA INVENTARIO"].dt.strftime("%Y-%m-%d")
    return d


class Contrato(unittest.TestCase):
    def test_posiciones_meses_y_json(self):
        d = muestra()
        antes = d.copy(deep=True)
        P = datos.armar(d, {"Meses": "prueba"})
        pd.testing.assert_frame_equal(d, antes)
        json.dumps(P, allow_nan=False)
        self.assertEqual(len(P["filas"]), 6)  # la línea sin fecha no viaja
        self.assertEqual(P["campos"], list(datos.CAMPOS))
        f0 = P["filas"][0]
        self.assertEqual(P["dic"]["prod"][f0[4]], "Lomo")
        self.assertEqual(P["dic"]["cod"][f0[5]], "0000000010")
        self.assertEqual(f0[9:], [-2.0, -100.0, 400.0])
        # Lo del 1 al 7 es del mes anterior (#613); con registro, no.
        self.assertEqual(P["meses"], ["2026-08", "2026-09", "2026-09"])
        self.assertEqual(datos.armar(d, operativo=False)["meses"], ["2026-09", "2026-09", "2026-10"])
        self.assertTrue(P["sesiones"][0])
        self.assertIsNone(P["filas"][-1][11])  # sin valorizado: null, no cero

    def test_cache_y_selector_de_meses(self):
        from graficos.ajuste import _historico_pieza as pieza
        ss = {}
        fake = SimpleNamespace(session_state=ss, markdown=Mock(), info=Mock(),
                               container=lambda **kw: nullcontext())
        d = muestra()
        with patch.object(pieza, "st", fake), patch.object(pieza, "ctx_meses", return_value={}), \
                patch.object(pieza, "rango_meses", return_value=None), \
                patch.object(pieza, "recortar_meses", side_effect=lambda d, *a: d), \
                patch.object(pieza, "selector_meses") as cal, \
                patch.object(pieza, "mes_operativo_activo", return_value=True), \
                patch.object(datos, "armar", wraps=datos.armar) as build, \
                patch.object(pieza, "_PIEZA") as comp:
            pieza.renderizar(d, "FECHA APERTURA INVENTARIO")
            pieza.renderizar(d, "FECHA APERTURA INVENTARIO")
        self.assertEqual(build.call_count, 1)
        self.assertEqual(cal.call_args.args, ("ajf_exp", {}))
        self.assertFalse(any(k.startswith("on_") for k in comp.call_args.kwargs))

    def test_rail_y_pestana_dicen_detalle_historico(self):
        import navegacion
        from graficos import ajuste
        self.assertEqual(navegacion.ROTULO_PESTANA[("Ajuste de Inventario", "Explorar")], "Detalle histórico")
        vistas = [v for _, vs in ajuste._AJUSTE_RAIL_CATEGORIAS for v in vs]
        self.assertIn(("Explorar", "Detalle histórico", ":material/pivot_table_chart:"), vistas)


try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, "sin Playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.br = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))
        from graficos.ajuste import _historico_pieza as pieza
        cls.pg = cls.br.new_page(viewport={"width": 1323, "height": 619}, accept_downloads=True)
        cls.pg.set_default_timeout(5000)
        cls.pg.route("https://ajh.test.example/**", lambda r: r.fulfill(body='<div id="host"></div>', content_type="text/html"))
        cls.pg.goto("https://ajh.test.example/")
        cls.pg.evaluate('css=>{const sr=document.querySelector("#host").attachShadow({mode:"open"}),st=document.createElement("style");st.textContent=css;sr.append(st);window.mount=document.createElement("div");sr.append(mount)}', pieza._CSS)
        js = (ROOT / "graficos/_xlsx.js").read_text(encoding="utf-8") + (ROOT / "graficos/ajuste/historico.js").read_text(encoding="utf-8")
        cls.pg.add_script_tag(content=js.replace("export default function(component)", "window.montarAjh=function(component)"), type="module")
        cls.pg.wait_for_function('typeof montarAjh==="function"')

    @classmethod
    def tearDownClass(cls):
        cls.br.close()
        cls.pw.stop()

    def mount(self, P=None):
        self.pg.evaluate("P=>{if(window.__ajHist){__ajHist.abort.abort();window.__ajHist=null;}mount.innerHTML='';montarAjh({data:P,parentElement:mount})}", P or datos.armar(muestra()))
        return self.pg.locator(".ajh")

    def test_conteos_e_indicadores_contra_pandas(self):
        self.mount()
        d = pandas_lineas()
        g = d.groupby(["dia", "AREA"])["AJUSTE VALORIZADO"]
        ref = {(k[0], k[1]): (v.sum(), v[v < 0].sum(), v[v > 0].sum()) for k, v in g}
        js = self.pg.evaluate("__ajHist.D.conteos.map(c=>[c.fecha,c.areaN,c.neto,c.falta,c.sobra,c.lineas])")
        self.assertEqual(len(js), len(ref))
        for fecha, area, neto, falta, sobra, n in js:
            r = ref[(fecha, area)]
            self.assertAlmostEqual(neto, r[0])
            self.assertAlmostEqual(falta, r[1])
            self.assertAlmostEqual(sobra, r[2])
        k = self.pg.evaluate("Object.fromEntries(Object.entries(__ajHist.D.kpis).map(([k,v])=>[k,v.length]))")
        v = d["AJUSTE VALORIZADO"]
        self.assertEqual(k, {"todos": len(d), "falta": int((v < 0).sum()), "sobra": int((v > 0).sum()), "grande": int((v.abs() >= 100).sum())})
        self.mount().locator("[data-a=kpi][data-v=falta]").click()
        self.assertAlmostEqual(self.pg.evaluate("__ajHist.D.conteos.reduce((a,c)=>a+c.neto,0)"), v[v < 0].sum())

    def test_tabla_dinamica_por_familia_y_mes(self):
        root = self.mount()
        root.locator("[data-a=modo][data-v='Tabla dinámica']").click()
        P = datos.armar(muestra())
        d = pandas_lineas()
        d["mes"] = d["dia"].map(dict(zip([f for f in P["fechas"]], P["meses"])))
        ref = d.groupby(["FAMILIA", "mes"])["AJUSTE VALORIZADO"].sum()
        js = self.pg.evaluate("(()=>{const r=__ajHist.D.piv.raiz,P=__ajHist.P,o=[];for(const n of r.hijos.values())for(const [ck,a] of n.celdas)o.push([P.dic.fam[n.val],ck,a.val]);return o})()")
        self.assertEqual(len(js), len(ref))
        for fam, mes, val in js:
            self.assertAlmostEqual(val, ref[(fam, mes)])
        # Producto lleva su código delante.
        root.locator("[data-a=abrir]").first.click()
        self.assertRegex(root.locator(".dc-p tbody").inner_text(), r"00000000\d\d · ")

    def test_ficha_detalle_ampliar_y_esc(self):
        root = self.mount()
        root.locator("tr[data-a=conteo]").filter(has_text="COCINA").first.click()
        ficha = root.locator(".dc-panel")
        self.assertIn("COCINA", ficha.inner_text())
        self.assertIn("0000000010", ficha.inner_text())
        root.locator("[data-a=modo][data-v='Líneas']").click()
        root.locator("[data-a=det]").click()
        ancho = self.pg.evaluate("(()=>{const t=__ajHist.root.querySelector('[data-tabla=lineas] th:nth-child(3)');return t.getBoundingClientRect().width})()")
        self.assertGreater(ancho, 120)
        self.assertIn("Stock declarado", root.locator("[data-tabla=lineas] thead").inner_text())
        root.locator(".dc-izq [data-a=amp]").click()
        self.assertEqual(root.locator(".dc-panel").count(), 0)
        self.pg.keyboard.press("Escape")
        self.assertEqual(root.locator(".dc-panel").count(), 1)
        root.locator("[data-a=det]").click()

    def test_filtros_busqueda_y_excel(self):
        root = self.mount()
        root.locator("[data-a=menu][data-v=area]").click()
        root.locator("[data-a=ninguna][data-v=area]").click()
        self.assertEqual(self.pg.evaluate("__ajHist.D.rs.length"), 0)
        root.locator("[data-a=todas][data-v=area]").click()
        root.locator("[data-input=q]").fill("malbec")
        self.assertEqual(self.pg.evaluate("__ajHist.D.rs.length"), 2)
        with self.pg.expect_download() as dl:
            root.locator("[data-a=excel]").click()
        with zipfile.ZipFile(dl.value.path()) as z:
            nombres = " ".join(z.namelist())
            libro = z.read("xl/workbook.xml").decode("utf-8")
        self.assertIn("sheet", nombres)
        for h in ("Conteos", "Líneas", "Tabla dinámica", "Contexto"):
            self.assertIn(h, libro)
        root.locator("[data-input=q]").fill("")


if __name__ == "__main__":
    unittest.main()
