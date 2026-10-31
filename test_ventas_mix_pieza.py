"""Ventas › «Mix de carta» como pieza propia (reglas #702 y #763).

Lo que vigila:

  · la nota de crédito de una venta sin costo no deja la base en negativo y
    neta su «sin costo»; una nota con su costo sí resta (`ventas_mix.base`);
  · en Chromium, con datos armados por `armar_mix`: los cuatro indicadores
    contra pandas y su variación contra el año pasado, que el año pasado se
    pida UNA vez y después de dibujar, «Medir» con los indicadores;
  · la tabla: niveles que abren y cierran, «% dentro» y «% del total» contra
    pandas, «Abrir hasta», que elegir un plato NO la achique y «Volver a…»;
  · que el Excel baje el árbol entero, y que las demás pestañas se dibujen.

Sin secrets ni red; la parte de Chromium se salta sin Playwright.

    python test_ventas_mix_pieza.py
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

import pandas as pd

_AQUI = Path(__file__).parent
sys.path.insert(0, str(_AQUI))

from graficos import ventas_alcance as va  # noqa: E402
from graficos import ventas_mix as vm  # noqa: E402

FILAS = [
    # fecha, grupo, subgrupo, producto, área, venta, cant, costo, neto, carta
    ("2026-08-04", "Alimentos", "Fondos", "Lomo", "Cocina", 100.0, 2, 30.0, 81.0, 81.0),
    ("2026-08-05", "Alimentos", "Fondos", "Lomo", "Cocina", 100.0, 2, 30.0, 81.0, 81.0),
    ("2026-08-05", "Alimentos", "Fondos", "Pulpo", "Cocina", 50.0, 1, 20.0, 40.5, 40.5),
    ("2026-08-11", "Alimentos", "Entradas", "Causa", "Frios", 40.0, 2, 10.0, 32.4, 32.4),
    ("2026-08-12", "Bebidas", "Vinos", "Malbec", "Bar", 60.0, 1, 24.0, 48.6, 48.6),
    ("2026-08-12", "Eventos", "Eventos", "Menu", "Cocina", 80.0, 1, 0.0, 64.8, 64.8),
]
ANTES = [
    ("2025-08-05", "Alimentos", "Fondos", "Lomo", "Cocina", 80.0, 2, 20.0, 64.8, 64.8),
    ("2025-08-13", "Bebidas", "Vinos", "Malbec", "Bar", 100.0, 2, 30.0, 81.0, 81.0),
]


def _df(filas):
    return pd.DataFrame({
        "FEC REG DOCUMENTO": pd.to_datetime([f[0] for f in filas]),
        "GRUPO": [f[1] for f in filas], "SUB GRUPO": [f[2] for f in filas],
        "PROD": [f[3] for f in filas], "AREA": [f[4] for f in filas],
        "VENTA": [f[5] for f in filas], "CANT": [f[6] for f in filas],
        "COSTO": [f[7] for f in filas], "NETO": [f[8] for f in filas],
        "CARTA": [f[9] for f in filas],
    })


COLS = {"fecha": "FEC REG DOCUMENTO", "grupo": "GRUPO", "sub": "SUB GRUPO", "prod": "PROD",
        "area": "AREA", "venta": "VENTA", "cant": "CANT", "costo": "COSTO", "neto": "NETO"}


def _armar():
    b, claves, nota = vm.periodos(vm.base(_df(FILAS), COLS), "Semana")
    rango = (dt.date(2026, 8, 3), dt.date(2026, 8, 16))
    b_ap, nombres = vm.ano_pasado(vm.base(_df(ANTES), COLS), claves, "Semana", rango)
    sin = vm.armar_mix(b, claves, "Semana", rango, nota=nota)
    con = vm.armar_mix(b, claves, "Semana", rango, b_ap, nombres, nota)
    return sin, con, b


class LaBase(unittest.TestCase):
    def test_nota_de_una_venta_sin_costo(self):
        d = _df([FILAS[0], FILAS[1]])
        d["COSTO"] = 0.0
        d["VENTA"] = [100.0, -100.0]
        d["NETO"] = [81.0, -81.0]
        b = vm.base(d, COLS)
        self.assertEqual(round(float(b["base_costo"].sum()), 6), 0.0)
        self.assertEqual(round(float(b["venta_sin_costo"].sum()), 6), 0.0)

    def test_nota_con_su_costo_si_resta(self):
        d = _df([FILAS[0], FILAS[1]])
        d["COSTO"] = [30.0, -30.0]
        d["VENTA"] = [100.0, -100.0]
        d["NETO"] = [81.0, -81.0]
        b = vm.base(d, COLS)
        self.assertEqual(round(float(b["base_costo"].iloc[1]), 6), -81.0)
        self.assertEqual(float(b["venta_sin_costo"].sum()), 0.0)

    def test_nota_de_lo_sin_descargo_sigue_en_la_base(self):
        d = _df([FILAS[0], FILAS[1]])
        d["COSTO"] = 0.0
        d["VENTA"] = [100.0, -100.0]
        d["NETO"] = [81.0, -81.0]
        d["COD ITEM VENTA DDOCUMENTO"] = "0000153"
        b = vm.base(d, COLS, sin_descargo=("0000153",))
        self.assertEqual(float(b["venta_sin_costo"].abs().sum()), 0.0)
        self.assertEqual(round(float(b["base_costo"].iloc[1]), 6), -81.0)


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class EnElNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._pw = _chromium()().start()
        try:
            cls.b = cls._pw.chromium.launch()
        except Exception as e:  # Chromium no instalado
            cls._pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {e}")
        cls.sin, cls.con, cls.base = _armar()

    @classmethod
    def tearDownClass(cls):
        cls.b.close()
        cls._pw.stop()

    def _pagina(self, ancho=1300, alto=760):
        carpeta = _AQUI / "graficos"
        js = (va.js() + (carpeta / "_xlsx.js").read_text(encoding="utf-8")
              + (carpeta / "ventas_mix.js").read_text(encoding="utf-8"))
        js = js.replace("export default function (component)", "window.__montar = function (component)")
        # El Excel no baja nada acá: se queda lo que iba a bajar.
        js = js.replace("function bajarExcel(raiz) {", "function bajarExcel(raiz) { window.__excel = true;")
        css = (carpeta / "ventas_mix.css").read_text(encoding="utf-8") + va.css()
        pg = self.b.new_page(viewport={"width": ancho, "height": alto})
        pg.set_content(f"<style>:root{{--alto-util:640px;--accent:#6c5ce7;--bg-card:#fff}}{css}</style><div id='r' style='margin-top:50px'></div>")
        pg.add_script_tag(content=js)
        errores = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.errores = errores
        return pg

    def _montar(self, pg, P):
        pg.evaluate("""(P) => {
          window.__enviados = [];
          window.__set = (k, v) => window.__enviados.push(k);
          const parent = document.getElementById('r');
          window.__montar({ data: P, parentElement: parent, setTriggerValue: window.__set });
        }""", P)

    @staticmethod
    def _t(pg, s):
        return [t.replace("\n", " ").strip() for t in pg.locator(s).all_inner_texts()]

    def test_abre_y_pide_el_ano_pasado_una_vez(self):
        pg = self._pagina()
        self._montar(pg, self.sin)
        self.assertEqual(pg.locator(".vm-kpi").count(), 4)
        self.assertIn("trayendo", self._t(pg, ".vm-kpi")[0])
        pg.wait_for_timeout(500)
        self.assertEqual(pg.evaluate("window.__enviados"), ["ap"])
        self._montar(pg, self.con)
        pg.wait_for_timeout(500)
        self.assertEqual(pg.evaluate("window.__enviados"), [], "con el año pasado ya no lo pide")
        self.assertEqual(pg.errores, [])
        pg.close()

    def test_indicadores_contra_pandas(self):
        b = self.base
        # La venta de Menu no tiene costo: fuera de la base y del % de costo.
        v, q, c, base = b["venta"].sum(), b["cant"].sum(), b["costo"].sum(), b["base_costo"].sum()
        pg = self._pagina()
        self._montar(pg, self.con)
        k = self._t(pg, ".vm-kpi")
        self.assertIn(f"S/ {v:.0f}", k[0])
        self.assertIn(f"{c / base * 100:.1f}%", k[1])
        self.assertIn(f"S/ {base - c:.0f}", k[2])
        self.assertIn(f"{q:.0f}", k[3])
        # Sólo las semanas con año pasado: 8 y 9 de 2025 contra sus espejos.
        self.assertIn("vs año pasado", k[0])
        self.assertIn("Sin costo cargado", self._t(pg, ".vm-ojo")[0])
        pg.close()

    def test_medir_y_los_indicadores_son_lo_mismo(self):
        pg = self._pagina()
        self._montar(pg, self.con)
        pg.locator("select[data-acc='medir']").select_option("und")
        self.assertIn("Unidades", self._t(pg, ".vm-kpi.on")[0])
        pg.locator("select[data-acc='medir']").select_option("soles")
        self.assertIn("Venta", self._t(pg, ".vm-kpi.on")[0])
        pg.locator(".vm-kpi").nth(1).click()
        self.assertEqual(pg.locator("select[data-acc='medir']").input_value(), "pct")
        pg.locator(".vm-kpi").nth(2).click()
        self.assertEqual(pg.locator("select[data-acc='medir']").input_value(), "soles")
        self.assertEqual(pg.errores, [])
        pg.close()

    def test_la_tabla_abre_cuadra_y_no_se_achica(self):
        b = self.base
        pg = self._pagina()
        self._montar(pg, self.con)
        pg.locator(".vm-pie .vm-seg button[data-id='Tabla']").click()
        filas = lambda: self._t(pg, ".vm-tabla tbody tr")  # noqa: E731
        self.assertEqual(len(filas()), 4, "Total y tres grupos")
        # Alimentos sobre el total, y Fondos dentro de Alimentos y sobre el total.
        total = b["venta"].sum()
        ali = b.loc[b["grupo"] == "Alimentos", "venta"].sum()
        fon = b.loc[b["sub"] == "Fondos", "venta"].sum()
        self.assertIn(f"{ali / total * 100:.1f}%", [x for x in filas() if "Alimentos" in x][0])
        pg.locator(".tn[data-n='0']", has_text="Alimentos").click()
        fila = [x for x in filas() if "Fondos" in x][0]
        self.assertIn(f"{fon / ali * 100:.1f}%", fila)
        self.assertIn(f"{fon / total * 100:.1f}%", fila)
        # Abrir hasta los productos.
        pg.locator(".vm-zcab .vm-seg button[data-id='2']").click()
        n = len(filas())
        self.assertEqual(n, 1 + 3 + 4 + 5, "Total, grupos, subgrupos y productos")
        # Elegir un plato no la achica y lo lleva a la ficha.
        pg.locator("tr.n2 .tn", has_text="Pulpo").click()
        self.assertEqual(len(filas()), n)
        self.assertIn("Pulpo", self._t(pg, ".vm-ficha")[0])
        self.assertIn("Pesa en Fondos", self._t(pg, ".vm-ficha")[0])
        self.assertIn("Pesa en el total", self._t(pg, ".vm-ficha")[0])
        self.assertEqual(pg.locator("tr.sel").count(), 1)
        # ▾ cierra un nivel, y «Abrir hasta» cierra todo.
        pg.locator("tr.n1 .tn", has_text="Fondos").click()
        self.assertLess(len(filas()), n)
        pg.locator(".vm-zcab .vm-seg button[data-id='0']").click()
        self.assertEqual(len(filas()), 4)
        self.assertEqual(pg.errores, [])
        pg.close()

    def test_volver_sale_de_donde_se_entro(self):
        pg = self._pagina()
        self._montar(pg, self.con)
        pg.locator(".vm-pie .vm-seg button[data-id='Tabla']").click()
        self.assertEqual(pg.locator(".vm-volver").count(), 0)
        pg.locator(".vm-bajar").first.click()
        pg.locator(".vm-bajar").first.click()
        self.assertIn("Volver a Alimentos", self._t(pg, ".vm-volver")[0])
        self.assertIn("Total · Fondos", self._t(pg, ".vm-tabla tbody tr")[0])
        pg.locator(".vm-volver").click()
        self.assertIn("Volver a", self._t(pg, ".vm-volver")[0])
        pg.locator(".vm-volver").click()
        self.assertEqual(pg.locator(".vm-volver").count(), 0)
        self.assertEqual(pg.errores, [])
        pg.close()

    def test_las_demas_pestanas_y_el_excel(self):
        pg = self._pagina()
        self._montar(pg, self.con)
        for z in ("Movio", "Mapa", "Mix", "Calculo", "Graf"):
            pg.locator(f".vm-pie .vm-seg button[data-id='{z}']").click()
            self.assertTrue(pg.locator(".vm-zona").inner_text().strip() or pg.locator(".vm-zona svg").count(), z)
        self.assertGreater(pg.locator(".g-col").count(), 0)
        self.assertGreater(pg.locator(".g-ap").count(), 0, "el año pasado, al lado de la barra")
        pg.locator(".vm-kpi").nth(1).click()
        self.assertGreater(pg.locator(".g-tot").count(), 0)
        pg.locator(".vm-excel").click()
        self.assertTrue(pg.evaluate("window.__excel"))
        self.assertEqual(pg.errores, [])
        pg.close()

    def test_celular_sin_desborde(self):
        pg = self._pagina(390, 844)
        self._montar(pg, self.con)
        self.assertEqual(pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), 0)
        pg.close()


if __name__ == "__main__":
    unittest.main()
