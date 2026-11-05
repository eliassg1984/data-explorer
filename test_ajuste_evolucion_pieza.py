"""Ajuste › Evolución con el grano «Cierre» (regla #827), sin red.

Lo que fue la pestaña «12 cierres» de «Diferencias del cierre» vive ahora
en Evolución: un período por SESIÓN de inventario (lo contado del 1 al 7
del mes siguiente, junto), los parciales a pedido, los insumos de operación
aparte y la calidad del conteo en la Tabla. Las cuentas se comparan con
pandas, y con las mismas filas que usa Diferencias: los dos lados tienen
que dar el mismo neto para el mismo cierre. En Chromium, la pieza entera
(`evolucion_ajuste.js` + `.css`)."""
import unittest
from pathlib import Path

from graficos.ajuste import _evolucion as ev
from test_cierre_pieza import inventario
import tema

ROOT = Path(__file__).parent
JS = (ROOT / "graficos/ajuste/evolucion_ajuste.js").read_text(encoding="utf-8")
CSS = (ROOT / "graficos/ajuste/evolucion_ajuste.css").read_text(encoding="utf-8")
OPER = "COSTOS PRODUCCION"
COLORES = {"pos": tema.AJUSTE_POS, "neg": tema.AJUSTE_NEG, "post": tema.AJUSTE_POS_TEXTO,
           "negt": tema.AJUSTE_NEG_TEXTO, "alerta": tema.AJUSTE_ALERTA_TEXTO,
           "ven": tema.AJUSTE_ORIGEN_VEN, "pro": tema.AJUSTE_ORIGEN_PRO,
           "reg": tema.AJUSTE_ORIGEN_REG, "gneg": tema.AJUSTE_ORIGEN_NEG,
           "op": tema.AJUSTE_OPERACION}


def datos(d, gran="Cierre"):
    """Lo que manda `vista_evolucion_ajuste`, con sus mismas funciones puras."""
    dp, orden = ev.periodos_ajuste(d, "FECHA", gran)
    m = ev.es_operacion(dp, "FAMILIA").to_numpy()
    aparte = bool(m.any() and (~m).any())
    main = dp[~m] if aparte else dp
    s = ev.serie_ajuste(main, orden, "AJUSTE VALORIZADO", "VALORIZADO TOTAL")
    sf = ev.serie_ajuste(dp, orden, "AJUSTE VALORIZADO", "VALORIZADO TOTAL", col_grupo="FAMILIA")
    p = ev.datos_pieza(
        s, sf, gran, negativo=ev.negativo_por_periodo(main, "AJUSTE VALORIZADO"),
        oper=ev.serie_ajuste(dp[m], orden, "AJUSTE VALORIZADO") if aparte else None,
        oper_id=OPER if aparte else None,
        calidad=ev.calidad_por_periodo(dp, "AJUSTE VALORIZADO", "AREA"))
    return {**p, "ayuda_kx": "", "alto": {"graf": 186, "abajo": 172}, "col": COLORES}


def con_operacion():
    d = inventario()
    d.loc[d["NOMBRE PRODUCTO"] == "Envase", "FAMILIA"] = OPER
    return d


class Cuentas(unittest.TestCase):
    def test_cada_cierre_da_lo_mismo_que_diferencias(self):
        d = con_operacion()
        p = datos(d)
        ses = {s["clave"]: s for s in ev.sesiones_inventario(d["FECHA"])}
        self.assertEqual([x["k"] for x in p["periodos"]], list(ses))
        for x in p["periodos"]:
            s = ses[x["k"]]
            dia = d[d["FECHA"].dt.date.isin(s["dias"])]
            op = dia["FAMILIA"] == OPER
            v = dia["AJUSTE VALORIZADO"]
            # Diferencias: «Neto» = alimentos y bebidas; «Operación, neto» aparte.
            self.assertAlmostEqual(x["n"], round(v[~op].sum(), 2), places=2)
            self.assertAlmostEqual(x["s"] + x["f"], x["n"], places=2)
            # Sobró y faltó van redondeados por separado: un céntimo de diferencia.
            self.assertAlmostEqual((x["os"] or 0) + (x["of"] or 0), v[op].sum(), delta=0.011)
            self.assertEqual(x["parcial"], s["tipo"] == "parcial")
            contada = (dia["STOCK AL CIERRE"].fillna(0).abs() > 1e-9) | (dia["STOCK DECLARADO"].fillna(0).abs() > 1e-9)
            n = int(contada.sum())
            self.assertEqual(x["q"][:2], [dia.loc[contada, "AREA"].str.strip().nunique(), n])
            self.assertAlmostEqual(x["q"][3], round(100 * (contada & (v.abs() <= 5)).sum() / n, 2))
            self.assertAlmostEqual(x["q"][2], round(100 * (contada & (v.abs() <= 1e-9)).sum() / n, 2))

    def test_el_cierre_de_dos_conteos_es_uno(self):
        p = datos(inventario())
        enero = next(x for x in p["periodos"] if x["k"] == "cierre_2026-01")
        # Contado el 1 y el 6 de febrero: una sola columna, rotulada con el mes que cierra.
        self.assertEqual(enero["eje"], "ene 26")
        self.assertEqual(sum(1 for x in p["periodos"] if x["eje"].startswith("ene")), 1)

    def test_sin_operacion_no_hay_tramo_aparte(self):
        p = datos(inventario())
        self.assertIsNone(p["oper"])
        self.assertTrue(all(x["os"] is None for x in p["periodos"]))


try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None


@unittest.skipIf(sync_playwright is None, "sin Playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.b = cls.pw.chromium.launch()
        except Exception as e:
            cls.pw.stop()
            raise unittest.SkipTest(str(e))
        cls.pg = cls.b.new_page(viewport={"width": 1323, "height": 619})
        cls.errores = []
        cls.pg.on("pageerror", lambda e: cls.errores.append(str(e)))
        cls.pg.set_content('<div id="montar" style="width:1000px"></div>')
        cls.pg.add_style_tag(content=":root{--text-primary:rgb(40,40,50);--text-secondary:rgb(100,100,110);"
                             "--text-muted:rgb(160,160,170);--accent:rgb(108,92,231);--bg-card:white;"
                             "--border:rgb(220,220,230);--line-soft:rgb(240,240,245)}body{margin:0}")
        cls.pg.add_style_tag(content=CSS)
        cls.pg.add_script_tag(content=JS.replace("export default function (component)",
                                                 "window.__montarEvo=function (component)"))

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls.pw.stop()

    def mount(self, p):
        self.pg.evaluate('P=>{const m=document.querySelector("#montar");m.innerHTML="";window.__pedidos=[];'
                         '__montarEvo({data:P,parentElement:m,setTriggerValue:(k,v)=>__pedidos.push([k,v])})}', p)
        self.assertEqual(self.errores, [])
        return self.pg.locator(".ev")

    def kpi(self, root, rotulo):
        """La cifra del indicador cuyo rótulo EMPIEZA con `rotulo` (el «neto»
        aparece también en la explicación de otros)."""
        return root.evaluate("(r,t)=>[...r.querySelectorAll('.ev-kpi')].find(k=>k.querySelector('.r').textContent.startsWith(t)).querySelector('.v').textContent", rotulo)

    def test_cierre_a_cierre_y_los_parciales_a_pedido(self):
        p = datos(con_operacion())
        root = self.mount(p)
        cierres = [x for x in p["periodos"] if not x["parcial"]]
        parciales = [x for x in p["periodos"] if x["parcial"]]
        self.assertTrue(parciales)
        # De entrada, sólo los cierres: una columna por cierre.
        self.assertEqual(root.locator(".serie .col").count(), len(cierres))
        self.assertEqual(root.locator(".col.parcial").count(), 0)
        boton = root.locator('[data-act="parciales"]')
        self.assertIn(f"Parciales · {len(parciales)}", boton.inner_text())
        self.assertEqual(boton.get_attribute("aria-pressed"), "false")
        self.assertIn(f"Neto · {len(cierres)} cierres", root.locator(".ev-kpis").inner_text())
        # Los totales son los de los cierres, sin la operación.
        neto = sum(x["n"] for x in cierres)
        self.assertIn(f"{abs(neto):.0f}", self.kpi(root, "Neto").replace("k", ""))
        # Con los parciales: aparecen marcados, y el período ya no se llama «cierre».
        boton.click()
        self.assertEqual(root.locator(".serie .col").count(), len(p["periodos"]))
        self.assertEqual(root.locator(".col.parcial").count(), len(parciales))
        self.assertIn("Parcial", root.locator(".leyenda").inner_text())
        self.assertIn(f"{len(p['periodos'])} conteos", root.locator(".ev-kpis").inner_text())
        self.assertIn("Parcial ·", root.locator(".col.parcial").first.get_attribute("title"))
        # Elegir una columna con los parciales a la vista elige ESA columna.
        i = next(j for j, x in enumerate(p["periodos"]) if x["parcial"])
        root.locator(".serie .col").nth(i).click()
        self.assertIn(f"Parcial · {p['periodos'][i]['eje']}", root.locator(".panel h3").inner_text())
        # Esconderlos suelta lo elegido si era un parcial.
        root.locator('[data-act="parciales"]').click()
        self.assertEqual(root.locator(".col.foco").count(), 0)

    def test_la_operacion_aparte_en_barras_indicador_panel_tabla_y_matriz(self):
        p = datos(con_operacion())
        root = self.mount(p)
        cierres = [x for x in p["periodos"] if not x["parcial"]]
        on = sum((x["os"] or 0) + (x["of"] or 0) for x in cierres)
        self.assertIn("Operación · aparte", root.locator(".ev-kpis").inner_text())
        self.assertIn(f"{abs(on):.0f}", self.kpi(root, "Operación"))
        # Los cinco indicadores van en UNA fila.
        tops = root.locator(".ev-kpi").evaluate_all("es=>es.map(e=>Math.round(e.getBoundingClientRect().top))")
        self.assertEqual(len(set(tops)), 1)
        self.assertGreater(root.locator(".sup i.op, .inf i.op").count(), 0)
        self.assertIn("Operación, aparte", root.locator(".leyenda").inner_text())
        root.locator(".serie .col").first.click()
        panel = root.locator(".panel").inner_text()
        self.assertIn("OPERACIÓN · APARTE", panel)
        self.assertIn("áreas ·", panel)
        self.assertIn("Cierre de", root.locator(".panel h3").inner_text())
        # La Tabla: la operación y la calidad del conteo, que traía «12 cierres».
        root.locator('[data-act="zona"][data-arg="tabla"]').click()
        cab = root.locator(".tabla thead").inner_text()
        for col in ("Operación", "Áreas", "Líneas", "Exactas", "±S/ 5"):
            self.assertIn(col, cab)
        self.assertEqual(root.locator(".tabla tbody tr").count(), len(cierres))
        root.locator('[data-act="parciales"]').click()
        self.assertEqual(root.locator(".tabla tbody tr.parcial").count(),
                         sum(1 for x in p["periodos"] if x["parcial"]))
        self.assertIn("Parcial ·", root.locator(".tabla tbody tr.parcial").first.inner_text())
        # La matriz: el total es el de la serie (sin operación) y la operación va debajo.
        root.locator('[data-act="zona"][data-arg="fam"]').click()
        self.assertIn("Familia × cierre", root.locator(".ev-tabs").inner_text())
        nombres = root.locator(".mz .fam .nm").all_inner_texts()
        self.assertIn("Total sin operación", nombres)
        self.assertEqual(nombres.index("Total sin operación"), len(nombres) - 2)
        op = root.locator(".mz .fam.op")
        self.assertEqual(op.count(), 1)
        self.assertEqual(nombres[-1], op.locator(".nm").inner_text())
        self.assertIn("Aparte", op.get_attribute("title"))
        # La nota del kardex cuenta lo que está a la vista (sin datos del kardex, nada).
        root.locator('[data-act="zona"][data-arg="tabla"]').click()
        self.assertNotIn("kardex", root.locator(".abajo .ayuda").inner_text())

    def test_la_nota_del_kardex_cuenta_lo_que_esta_a_la_vista(self):
        p = datos(con_operacion())
        p["kardex"] = True
        for x in p["periodos"]:
            x["kx"], x["dkx"] = x["n"], x["parcial"]  # difiere sólo el parcial
        root = self.mount(p)
        root.locator('[data-act="zona"][data-arg="tabla"]').click()
        self.assertIn("igual al kardex", root.locator(".abajo .ayuda").inner_text())
        root.locator('[data-act="parciales"]').click()
        n = len(p["periodos"])
        self.assertIn(f"el kardex difiere en 1 de {n} conteos", root.locator(".abajo .ayuda").inner_text())

    def test_por_mes_y_sin_operacion_no_cambia_nada(self):
        root = self.mount(datos(inventario(), "Mes"))
        self.assertEqual(root.locator('[data-act="parciales"]').count(), 0)
        self.assertEqual(root.locator(".sup i.op, .inf i.op").count(), 0)
        self.assertNotIn("Operación", root.locator(".ev-kpis").inner_text())
        self.assertIn("Familia × mes", root.locator(".ev-tabs").inner_text())

    def test_celular_sin_desborde(self):
        self.pg.set_viewport_size({"width": 390, "height": 844})
        try:
            self.pg.evaluate('document.querySelector("#montar").style.width="390px"')
            self.mount(datos(con_operacion()))
            self.assertLessEqual(self.pg.evaluate("document.documentElement.scrollWidth"), 390)
        finally:
            self.pg.evaluate('document.querySelector("#montar").style.width="1000px"')
            self.pg.set_viewport_size({"width": 1323, "height": 619})


if __name__ == "__main__":
    unittest.main(verbosity=2)
