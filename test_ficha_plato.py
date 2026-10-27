"""La ficha del plato de «Costo de Carta» (reglas #744 y #746): la receta
aplanada, lo habitual de un corte, «Qué mueve el costo de hoy», lo que
recibe el navegador y, en Chromium, la pieza ÚNICA (lista + ficha con
Resumen | Receta | Evolución | Canales): las mismas cuentas, lo que se pagó
sobre el 30 %, la espera de la receta de otro plato y que siembre el
simulador con el precio que lo deja en lo habitual. Sin secrets ni red."""
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import simulador_receta as sr
from graficos import carta_costeada as cc

_AQUI = Path(cc.__file__).parent
_JS = (_AQUI / "ficha_plato.js").read_text(encoding="utf-8")
_CSS = (_AQUI / "ficha_plato.css").read_text(encoding="utf-8")
_JS_LISTA = (_AQUI / "carta_costeada.js").read_text(encoding="utf-8")
_CSS_LISTA = (_AQUI / "carta_costeada.css").read_text(encoding="utf-8")
_XLSX = (_AQUI / "_xlsx.js").read_text(encoding="utf-8")


def nodos():
    """Un plato con un corte porcionado (1 und, S/ 22) y una receta base de
    dos insumos (S/ 4 en el plato)."""
    corte = {"cod": "C1", "ins": "(P) Lomo trozos 170gr x und (produccion)", "cant": 1.0, "unid": "und",
             "factor": 1.0, "costo": 22.0,
             "porc": {"po": "P8", "fecha": "2026-10-21", "origen": "(P) Lomo cabeza x Kg", "cod_origen": "C0",
                      "merma": 35.0, "peso": 0.17, "unid_origen": "kg", "precio_corte": 22.0}}
    base = {"cod": "B1", "ins": "(Rs) Salsa de lomo x kg (Calientes)", "cant": 80.0, "unid": "g", "factor": 1000.0,
            "costo": 4.0, "base": {"nombre": "Salsa", "unid": "kg", "fecha": "2026-02-02"},
            "hijos": [{"cod": "I1", "ins": "Ostion", "cant": 50.0, "unid": "g", "factor": 1000.0, "costo": 3.0},
                      {"cod": "I2", "ins": "Sillao", "cant": 5.0, "unid": "ml", "factor": 1000.0, "costo": 1.0}]}
    return [corte, base]


def porcionamientos():
    """El último (21/10) desde Lomo cabeza a S/ 22; antes, tres desde Lomo
    fino: dos dentro de los 30 días (10 und a 15 y 30 und a 17) y uno de
    hace dos meses a 12, que no cuenta."""
    filas = [("P8", "2026-10-21", "Lomo cabeza", "C0", 4.3, 1.5, 13, 22.0),
             ("P7", "2026-10-15", "Lomo fino", "F0", 9.0, 2.0, 10, 15.0),
             ("P6", "2026-10-01", "Lomo fino", "F0", 30.0, 6.0, 30, 17.0),
             ("P5", "2026-08-10", "Lomo fino", "F0", 9.0, 2.0, 10, 12.0),
             ("P4", "2026-10-02", "Lomo fino", "F0", 5.0, 1.0, 40, 3.0)]
    df = pd.DataFrame(filas, columns=["COD PORC", "FEC REGIST", "PROD INICIAL", "COD PROD INIC",
                                      "CANT A PORCIONAR", "CANT MERMA", "CANT RESULT", "PREC PROM PROD FIN"])
    df["COD PROD FINAL"] = ["C1", "C1", "C1", "C1", "C0"]
    df["UNID PROD INIC"] = "KG"
    df["UNID PROD FIN"] = "UND"
    return df


def plato(**kw):
    f = {"Cod": "0001", "Producto": "Lomo Saltado", "Grupo": "Alimentos", "Subgrupo": "Fondos", "Tipo": "Receta",
         "Precio": 79.0, "Neto": 64.0, "Costo": 26.0, "SinCosto": False, "Vendidos": 10.0, "VendidoNeto": 560.0,
         "CostoVendido": 240.0, "SinCostoNeto": 0.0, "Actualizado": pd.Timestamp("2026-10-07"), "Descarga": ""}
    f.update(kw)
    return pd.Series(f)


def vendido():
    return pd.DataFrame({
        "producto": ["0001"] * 3, "dia": pd.to_datetime(["2026-09-03", "2026-10-02", "2026-10-20"]),
        "unidades": [10.0, 6.0, 4.0], "neto": [600.0, 330.0, 230.0], "costo": [200.0, 144.0, 96.0],
        "unidades_costeadas": [10.0, 6.0, 4.0], "neto_sin_costo": [0.0, 0.0, 0.0]})


class LaFichaEnPython(unittest.TestCase):
    def setUp(self):
        p = patch.object(cc, "divisor_neto", return_value=1.235)
        p.start()
        self.addCleanup(p.stop)

    def test_receta_aplanada(self):
        f = cc.filas_receta(nodos())
        self.assertEqual([r[0] for r in f], [0, 1, 2, 3])
        self.assertEqual([r[1] for r in f], [-1, -1, 1, 1])
        self.assertEqual([r[2] for r in f], [0, 0, 1, 1])
        self.assertEqual([r[4] for r in f], ["P", "Rs", "", ""])
        self.assertEqual([r[11] for r in f], ["0", "1", "1.0", "1.1"])
        self.assertEqual(f[0][3], "Lomo trozos 170gr x und (produccion)")
        self.assertEqual((f[1][8], f[1][10]), (2, "2026-02-02"))

    def test_habitual_pondera_y_mira_30_dias(self):
        po = cc.porcionamientos_de(porcionamientos(), "C1", n=60)
        h = cc.habitual_corte(po)
        self.assertEqual(h["n"], 2)
        self.assertAlmostEqual(h["costo"], (10 * 15 + 30 * 17) / 40)
        self.assertIsNone(cc.habitual_corte(po.head(1)))

    def test_cortes_y_que_mueve(self):
        df = porcionamientos()
        cortes = cc.cortes_del_plato(nodos(), df)
        self.assertEqual(list(cortes), ["C1"])
        c = cortes["C1"]
        self.assertEqual(c["filas"][0][:2], ["2026-10-21", "Lomo cabeza"])
        self.assertTrue(c["de_porc"], "Lomo cabeza (C0) también sale de un porcionamiento")
        hab = (10 * 15 + 30 * 17) / 40
        self.assertAlmostEqual(c["P_hab"], hab * (1 - .35) / .17, places=5)
        # El precio de origen sembrado deja el corte en lo habitual: la MISMA
        # cuenta que el simulador.
        self.assertAlmostEqual(sr.costo_nodo(nodos()[0], "0", 1.0, {"0": {"P": c["P_hab"]}}), hab, places=4)
        q = cc.que_mueve(cc.filas_receta(nodos()), cortes, 26.0, 64.0)
        self.assertEqual((q["cod"], q["ruta"], q["n"]), ("C1", "0", 2))
        self.assertAlmostEqual(q["plato"], 26.0 - 22.0 + hab)
        self.assertAlmostEqual(q["pct_hab"], (26.0 - 22.0 + hab) / 64.0 * 100)
        # Sin desvío de lo habitual, nada que decir.
        quieto = {"C1": dict(c, hab={"costo": 21.5, "n": 2, "salio": 40})}
        self.assertIsNone(cc.que_mueve(cc.filas_receta(nodos()), quieto, 26.0, 64.0))
        # Si la receta no tiene el precio del último, tampoco.
        otro = [dict(nodos()[0], costo=18.0), nodos()[1]]
        self.assertIsNone(cc.que_mueve(cc.filas_receta(otro), cortes, 22.0, 64.0))

    def test_lo_que_recibe_el_navegador(self):
        marcas = [{"t": pd.Timestamp("2026-10-07"), "base": "Salsa", "usr": "MQ", "esp": -0.79,
                   "txt": "Ostion: 50 → 40", "n": 2}]
        picos = [{"ini": pd.Timestamp("2026-09-03"), "fin": pd.Timestamp("2026-09-03"), "unid": 10.0,
                  "normal": 20.0, "pico": 30.0, "exceso": 100.0, "causa": "Posible causa: x."}]
        d = cc.armar_ficha(plato(), nodos(), vendido(), (pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-25")),
                           marcas, picos, [], cc.cortes_del_plato(nodos(), porcionamientos()), ["algo"])
        self.assertEqual(d["meses"], [["2026-09", 10.0, 20.0, 600.0, d["meses"][0][4], 0.0],
                                      ["2026-10", 10.0, 24.0, 560.0, d["meses"][1][4], 0.0]])
        self.assertEqual(d["rango"], ["2026-10-01", "2026-10-25"])
        self.assertEqual(d["marcas"][0]["t"], "2026-10-07")
        self.assertIn("MQ · Salsa: Ostion: 50 → 40 (y 1 cambio más) → −S/ 0.79 por plato", d["marcas"][0]["x"])
        self.assertTrue(d["picos"][0]["x"].startswith("Pico el 03/09/26: S/ 30.00 por plato"))
        self.assertEqual((d["plato"]["receta"], d["divisor"], d["faltan"]), ("2026-10-07", 1.235, ["algo"]))
        self.assertIsNotNone(d["q"])

    def test_sin_receta(self):
        d = cc.armar_ficha(plato(Tipo="Directo", Descarga="Agua"), [], None, None)
        self.assertEqual((d["filas"], d["meses"], d["cortes"], d["q"], d["rango"]), ([], [], {}, None, None))


class ElCodigo(unittest.TestCase):
    def test_sin_colores_sueltos_ni_has(self):
        for css in (_CSS, _CSS_LISTA):
            sin_comentarios = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
            self.assertNotRegex(sin_comentarios, r"#[0-9a-fA-F]{3,6}\b")
            self.assertNotIn(":has(", css)
        self.assertNotRegex(_JS + _JS_LISTA, r"#[0-9a-fA-F]{6}\b")

    def test_triggers_que_lee_python(self):
        """Desde la regla #746 la ficha va en la MISMA pieza que la lista:
        todos los pedidos salen de ella y los lee `render_carta_costeada`."""
        src = Path(cc.__file__).read_text(encoding="utf-8")
        for t in ("elegir", "simular", "cambios", "nuevo_costeo", "produccion"):
            self.assertIn(f"'{t}'", _JS + _JS_LISTA)
            self.assertIn(f"on_{t}_change", src)
        # Ya no hay una segunda pieza: la ficha es un módulo de la lista.
        self.assertNotIn("export default", _JS)
        self.assertEqual(src.count("st.components.v2.component("), 1)
        ficha = src[src.index("def _datos_ficha("):src.index("# ─── La pieza propia")]
        self.assertNotRegex(ficha, r"st\.(plotly_chart|dataframe|segmented_control|selectbox)")
        # La pieza lleva los tres archivos, en este orden, y las dos hojas.
        pieza = src[src.index("_PIEZA = st.components.v2.component("):]
        self.assertLess(pieza.index('"_xlsx.js"'), pieza.index('"ficha_plato.js"'))
        self.assertLess(pieza.index('"ficha_plato.js"'), pieza.index('"carta_costeada.js"'))
        self.assertIn('"ficha_plato.css"', pieza[:pieza.index("js=")])


def _chromium():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


def _pieza():
    """La pieza de la lista con la ficha del Lomo adentro, como la arma
    `render_carta_costeada`: la carta de test_costo_carta y el plato de acá."""
    import test_costo_carta as tcc
    with patch.object(cc, "divisor_neto", return_value=1.235):
        t, n = cc.preparar(tcc.carta(), incluir_inactivos=True)
        rango = (pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-31"))
        t, _ = cc.con_ventas(t, tcc.vendido(), rango=(rango[0].date(), rango[1].date()))
        datos = cc.armar_pieza(t, rango, cc.ventas_por_canal(tcc.otros_canales(), rango), "0000001", n)
        datos["ficha"] = cc.armar_ficha(plato(Cod="0000001", Producto="Lomo"), nodos(),
                                        vendido().assign(producto="0000001"), rango,
                                        cortes=cc.cortes_del_plato(nodos(), porcionamientos()))
    return datos


_RECORRIDO = """([d, css]) => {
  const sr = document.getElementById('h').attachShadow({ mode: 'open' });
  const s = document.createElement('style'); s.textContent = css; sr.appendChild(s);
  const c = document.createElement('div'); sr.appendChild(c);
  window.__t = [];
  window.__montar({ data: d, parentElement: c, setTriggerValue: (k, v) => window.__t.push([k, v]) });
  const $ = (q) => sr.querySelector(q), $$ = (q) => [...sr.querySelectorAll(q)];
  const F = window.FichaPlato, cf = F.cifras(d.ficha);
  const kpis = $$('.cc-kpi').map((k) => k.querySelector('.cc-kpi-rot').textContent);
  const ex = $('.cc-kpi[data-id=ex] .cc-kpi-val').textContent;
  const filtros = $$('.cc-filtros select').map((x) => x.dataset.acc);
  const tabs = $$('[data-acc=ftab]').map((x) => x.textContent);
  const resumen = $('.cc-fpanel').textContent;
  $('[data-acc=simular-hab]').click();
  $('.cc-ftit [data-acc=simular]').click();
  $('[data-acc=fmenu]').click();
  $('.cc-menu [data-acc=nuevo]').click();
  $('[data-acc=fmenu]').click();
  $('.cc-menu [data-acc=cambios]').click();
  $('[data-acc=ftab][data-id=receta]').click();
  const formas = $$('[data-acc=rec]').map((x) => x.textContent);
  $('[data-acc=linea][data-id="1"]').click();
  const filasAbiertas = $$('.fp-lineas .fp-fila').length;
  $('[data-acc=rec][data-id=rep]').click();
  const reparto = !!$('.fp-nodo');
  $('[data-acc=rec][data-id=porc]').click();
  const rend = $('[data-acc=rend]');
  if (rend) rend.click();
  $('[data-acc=ftab][data-id=evo]').click();
  const evo = !!$('.fp-graf svg');
  $('[data-acc=ftab][data-id=canales]').click();
  const canales = $$('.cc-canal-t tbody tr').length;
  // Otro producto: la ficha cambia ya y espera la receta.
  $('tr.cc-f[data-cod="0000002"]').click();
  $('[data-acc=ftab][data-id=receta]').click();
  const espera = !!$('.cc-cargando');
  const titulo = $('.cc-ftit h3').textContent;
  // Las columnas que se suman.
  $('[data-acc=cols]').click();
  $('[data-acc=col][data-id=margen]').click();
  const conMargen = $$('.cc-tabla th').map((x) => x.textContent.trim()).includes('Margen');
  return { cf, kpis, ex, filtros, tabs, resumen, formas, filasAbiertas, reparto, evo, canales, espera, titulo,
           conMargen, rep: F.reparto(d.ficha.filas), t: window.__t,
           cortos: ['Lomo trozos 170gr x und (produccion)', 'Salsa de lomo x kg (Calientes)', 'Pasta x gratinar'].map(F.corto) };
}"""


@unittest.skipIf(_chromium() is None, "sin Playwright (requirements-dev.txt)")
class EnElNavegador(unittest.TestCase):
    def test_una_pieza_mismas_cuentas_y_triggers(self):
        d = _pieza()
        js = (_XLSX + _JS + _JS_LISTA).replace("export default function (component)",
                                               "window.__montar = function (component)")
        with _chromium()() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:  # Chromium no instalado
                self.skipTest(f"sin Chromium: {e}")
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))
            pg.set_content("<div id=h style='--alto-util:800px'></div>")
            pg.add_script_tag(content=js)
            out = pg.evaluate(_RECORRIDO, [d, _CSS_LISTA + _CSS])
            b.close()
        self.assertEqual(errores, [])
        cf = out["cf"]
        self.assertAlmostEqual(cf["pctHoy"], 26 / 64 * 100)
        self.assertAlmostEqual(cf["margen"], 38.0)
        self.assertAlmostEqual(cf["pctV"], 240 / 560 * 100)
        self.assertAlmostEqual(cf["mm"]["var"], (24 / 20 - 1) * 100)
        for o, u in zip(cf["objetivos"], (30, 35)):
            self.assertAlmostEqual(o["precio"], sr.precio_sugerido(26.0, u, 1.235))
            self.assertAlmostEqual(o["costo"], 64 * u / 100)
        self.assertEqual(out["kpis"], ["% costo · ponderado por lo vendido", "Sobre el 30 %, en soles",
                                       "Sobre 35 %", "Datos para revisar"])
        # El Lomo en «En el Local»: 13 vendidos (15 − 2 de Rappi) y S/ 815.90
        # cobrados → 28.35 × 13 − 30 % de 815.90 = S/ 123.78.
        self.assertEqual(out["ex"], "S/ 124")
        self.assertEqual(out["filtros"], ["canal", "grupo", "tipo", "oferta", "ver", "incluir"])
        self.assertEqual(out["tabs"], ["Resumen", "Receta", "Evolución", "Canales"])
        for texto in ("Qué mueve el costo de hoy", "Costo y utilidad", "Para quedar en 30 %",
                      "Al vender, mes a mes", "set → oct (+20.0 %)"):
            self.assertIn(texto, out["resumen"])
        self.assertEqual(out["formas"], ["Lista", "Reparto del precio", "Porcionados"])
        self.assertEqual(out["filasAbiertas"], 4)
        self.assertTrue(out["reparto"] and out["evo"])
        self.assertEqual(out["canales"], 5)
        self.assertTrue(out["espera"])
        self.assertEqual(out["titulo"], "Agua")
        self.assertTrue(out["conMargen"])
        self.assertEqual([r["v"] for r in out["rep"]], [22.0, 4.0])
        self.assertEqual(out["cortos"], ["Lomo trozos 170gr", "Salsa de lomo", "Pasta x gratinar"])
        t = out["t"]
        self.assertEqual([k for k, _ in t], ["simular", "simular", "nuevo_costeo", "cambios", "produccion", "elegir"])
        self.assertEqual(t[0][1]["estado"], {"0": {"P": d["ficha"]["q"]["P"]}})
        self.assertEqual([x[1]["cod"] for x in t[:4]], ["0000001"] * 4)
        self.assertIsNone(t[1][1]["estado"])
        self.assertEqual((t[4][1]["destino"], t[4][1]["cod"]), ("rend", "C1"))
        self.assertTrue(re.fullmatch(r"\d+", str(t[4][1]["n"])))
        self.assertEqual(t[5][1], "0000002")


if __name__ == "__main__":
    unittest.main()
