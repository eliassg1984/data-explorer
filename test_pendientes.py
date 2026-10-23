"""Inicio › «Pendientes del período» (regla #711): de qué vista sale cada
señal, su color, y que lo que no se calculó diga «sin calcular» y no 0. Y lo
que recibe el navegador. Sin secrets ni red."""
import ast
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import consistencia_maestro as cm
import data
import pendientes as pd_

RAIZ = Path(__file__).parent


def casos(n, soles=10.0):
    return pd.DataFrame({c: ([soles] * n if c == "soles" else ["x"] * n)
                         for c in cm.CASOS})


def filas_de(armado):
    return {f["t"]: f for col in armado["columnas"] for a in col for f in a["filas"]}


class Pendientes(unittest.TestCase):
    def test_sin_fuentes_nada_es_cero(self):
        a = pd_.armar({}, 26)
        f = filas_de(a)
        self.assertEqual(len(f), 13)
        sin = [t for t, x in f.items() if x["estado"] == pd_.SIN]
        # Todo es «sin calcular» salvo nada: sin horas, los datos tampoco se saben.
        self.assertEqual(len(sin), 13)
        self.assertTrue(all(x["v"] in ("sin calcular", "sin dato") for x in f.values()))
        self.assertEqual(a["cuenta"][pd_.SIN], 13)

    def test_consistencia_toma_nombre_y_color_del_control(self):
        r = {"hoy": "x", "casos": {"s2": casos(3), "m4": casos(2), "r3": casos(0),
                                  "p4": RuntimeError("caído"), "m3": casos(1),
                                  "c4": casos(0), "m9": casos(0)}}
        f = {x["ir"]["abrir"]: x for x in pd_.de_consistencia(r)}
        self.assertEqual(f["s2"]["estado"], pd_.ROJO)      # grave
        self.assertEqual(f["m4"]["estado"], pd_.AMBAR)     # no grave
        self.assertEqual(f["r3"]["estado"], pd_.VERDE)     # sin casos
        self.assertEqual(f["p4"]["estado"], pd_.SIN)       # falló: no es un cero
        self.assertEqual(f["p4"]["v"], "no se pudo calcular")
        self.assertEqual(f["s2"]["v"], "3 · S/ 30")
        nombres = {c.id: c.nombre for c in cm.CONTROLES}
        self.assertEqual(f["s2"]["t"], nombres["s2"])
        self.assertEqual(f["s2"]["ir"]["r"], "Costos")
        self.assertEqual(f["s2"]["ir"]["v"], "Consistencia de datos")

    def test_cada_control_existe(self):
        ids = {c.id for c in cm.CONTROLES}
        self.assertTrue({cid for cid, _a, _p in pd_.DE_CONSISTENCIA} <= ids)

    def test_diferencias_por_la_cantidad_y_sin_pista(self):
        lin = pd.DataFrame({
            "q": [-1.0, -2.0, 3.0, -1.0], "v": [-10.0, -20.0, 30.0, -5.0],
            "n_pistas": [0, 1, 0, 0], "pend_v": [15.0, 10.0, 0.0, 0.0]})
        f1, f2 = pd_.de_diferencias({"lineas": lin}, "Cierre de setiembre")
        self.assertEqual(f1["estado"], pd_.ROJO)
        self.assertEqual(f1["v"], "S/ 15 · 2 líneas")      # el sobrante no cuenta
        self.assertIn("Cierre de setiembre", f1["por"])
        self.assertEqual(f2["estado"], pd_.AMBAR)          # 25 ≥ 20
        g1, g2 = pd_.de_diferencias(None, None)
        self.assertEqual((g1["estado"], g2["estado"]), (pd_.SIN, pd_.SIN))

    def test_costos_con_la_regla_del_aviso(self):
        normal = [("m1", 100, 10_000), ("m2", 120, 10_000), ("m3", 90, 10_000),
                  ("m4", 110, 10_000)]
        self.assertEqual(pd_.de_costos(normal)["estado"], pd_.VERDE)
        raro = normal + [("m5", 500, 10_000)]
        f = pd_.de_costos(raro)
        self.assertEqual(f["estado"], pd_.ROJO)
        self.assertIn("m5", f["por"])
        # Con menos de tres meses no hay con qué comparar: no se marca.
        self.assertEqual(pd_.de_costos(normal[:2])["estado"], pd_.VERDE)
        self.assertEqual(pd_.umbral_sin_explicar([0.01, 0.01, 0.01]), 0.03)

    def test_datos_viejos(self):
        f = pd_.de_datos({"a.parquet": 5, "b.parquet": 40, "c.parquet": 30}, 26)
        self.assertEqual((f["estado"], f["v"]), (pd_.AMBAR, "2 de 3"))
        self.assertTrue(f["ayuda"].startswith("b 40 h"))
        self.assertEqual(pd_.de_datos({"a.parquet": 1}, 26)["estado"], pd_.VERDE)

    def test_pesos_y_recetas(self):
        self.assertEqual(pd_.de_pesos({"n": 2, "docs": 1})["v"], "2 cortes · 1 porcionamiento")
        self.assertEqual(pd_.de_pesos({"n": 0, "docs": 0})["estado"], pd_.VERDE)
        r = pd_.de_revisar_recetas({"n": 3, "valor": 1234.0, "fin": "2026-10-22"})
        self.assertEqual((r["estado"], r["v"]), (pd_.AMBAR, "3 cortes · S/ 1,234"))
        self.assertEqual(pd_.de_revisar_recetas(None)["v"], "sin calcular")

    def test_resumen_de_recetas_vs_porcionado(self):
        from graficos import recetas_revisar as rr
        t = pd.DataFrame({"que": [rr.QUE_SIN, rr.QUE_FALTA, rr.QUE_SALIDA],
                          "valor": [10.0, 5.0, 100.0]})
        self.assertEqual(rr.resumen_pendiente(t, "2026-10-22"),
                         {"n": 2, "valor": 15.0, "fin": "2026-10-22"})

    def test_areas_y_orden(self):
        a = pd_.armar({"horas": {"a.parquet": 1}}, 26)
        areas = [x["n"] for col in a["columnas"] for x in col]
        self.assertEqual(sorted(areas), sorted(pd_.AREAS))
        for col in a["columnas"]:
            for x in col:
                orden = [pd_.ORDEN[f["estado"]] for f in x["filas"]]
                self.assertEqual(orden, sorted(orden))

    def test_recordar(self):
        data.recordar("_prueba", ("s1",), {"x": 1})
        self.assertEqual(data.recordado("_prueba", ("s1",)), {"x": 1})
        self.assertIsNone(data.recordado("_prueba", ("s2",)))   # otros datos
        data.recordar("_prueba", ("s3",), None)                  # no pisa con None
        self.assertEqual(data.recordado("_prueba", ("s1",)), {"x": 1})
        data._RECIENTES.pop("_prueba", None)

    def test_destinos_existen(self):
        from graficos import vistas_de
        for r, sk, vista, _rot in (pd_.DIFERENCIAS, pd_.CONSISTENCIA, pd_.REVISAR_MERMA,
                                   pd_.REVISAR_RECETAS, pd_.COSTO_VENTAS):
            par = vistas_de(r)
            self.assertIsNotNone(par, r)
            self.assertEqual(par[0], sk, r)
            self.assertIn(vista, [v[0] for v in par[1]], (r, vista))

    def test_el_js_lee_lo_que_python_manda(self):
        js = (RAIZ / "graficos" / "pendientes.js").read_text(encoding="utf-8")
        for campo in ("columnas", "cuenta", "cierre", "calculable", "filas", "estado", "ir_rot",
                      "ayuda", ".ir", "'ir'", "'calcular'"):
            self.assertIn(campo, js, campo)
        py = (RAIZ / "graficos" / "pendientes.py").read_text(encoding="utf-8")
        self.assertIn("on_ir_change", py)
        self.assertIn("on_calcular_change", py)

    def test_consistencia_abre_el_control_pedido(self):
        from graficos import pendientes as vista
        src = (RAIZ / "graficos" / "costos_consistencia.py").read_text(encoding="utf-8")
        self.assertIn(f'st.session_state.pop("{vista.K_ABRIR_CONSISTENCIA}"', src)
        js = (RAIZ / "graficos" / "costos_consistencia.js").read_text(encoding="utf-8")
        self.assertIn("data.abrir", js)

    def test_nada_pesado_sin_pedirlo(self):
        """Lo pesado sólo se pide con «Calcular ahora»: cada llamada a la
        consistencia o a las diferencias sin `solo_si_calculado=True` está
        dentro del `if calcular`."""
        arbol = ast.parse((RAIZ / "graficos" / "pendientes.py").read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(arbol)
                  if isinstance(n, ast.FunctionDef) and n.name == "renderizar")
        si = next(n for n in ast.walk(fn) if isinstance(n, ast.If)
                  and getattr(n.test, "id", "") == "calcular")
        dentro = {id(c) for c in ast.walk(ast.Module(body=si.body, type_ignores=[]))}
        for c in ast.walk(fn):
            if (isinstance(c, ast.Call) and getattr(c.func, "attr", "") in
                    ("consistencia_maestro", "diferencias_ajuste_sesion")):
                solo = any(k.arg == "solo_si_calculado" for k in c.keywords)
                self.assertTrue(solo or id(c) in dentro, ast.unparse(c))


if __name__ == "__main__":
    np.seterr(all="ignore")
    unittest.main(verbosity=1)
