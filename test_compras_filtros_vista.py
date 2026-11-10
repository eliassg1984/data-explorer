"""Las tarjetas de Compras conservan y aplican su propio recorte."""

from contextlib import ExitStack, nullcontext
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from graficos import compras
from graficos.compras import _filtros_vista as filtros


class FiltrosVistaCompras(unittest.TestCase):
    def test_casillas_del_panel_y_cascada_son_independientes(self):
        app = AppTest.from_string("""
from graficos.compras._filtros_vista import panel_filtros_vista, preparar_filtros_vista

opciones = ["ALIMENTOS", "BEBIDAS"]
mapa = {"ALIMENTOS": ["CARNES"], "BEBIDAS": ["AGUAS"]}
for vista, familia in [("volatilidad", "ALIMENTOS"), ("proveedor", "BEBIDAS")]:
    seccion = "compras_sec_" + vista
    preparar_filtros_vista(seccion, opciones, mapa, [familia])
    panel_filtros_vista(seccion, opciones, mapa)
""").run()
        self.assertFalse(app.exception)

        def casilla(clave, rotulo):
            return next(c for c in app.checkbox if c.key.startswith(f"{clave}__") and c.label == rotulo)

        familias = "cp_familias_volatilidad"
        subfamilias = "cp_subfamilias_volatilidad"
        casilla(subfamilias, "Carnes").check().run()
        self.assertEqual(app.session_state[subfamilias], ["CARNES"])
        casilla(familias, "Alimentos").uncheck().run()
        self.assertEqual(app.session_state[subfamilias], [])
        self.assertFalse(any(c.key.startswith(f"{subfamilias}__") for c in app.checkbox))

        casilla(familias, "Bebidas").check().run()
        self.assertFalse(casilla(subfamilias, "Aguas").value)
        app.button(key=f"{familias}_todas").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(casilla(familias, "Bebidas").value)
        self.assertTrue(casilla("cp_familias_proveedor", "Bebidas").value)

    def test_migra_el_filtro_previo_y_recorta_solo_la_subfamilia_propia(self):
        estado = {"compras_graf_filtro_fam": ["ALIMENTOS"], "compras_graf_filtro_sub": ["CARNES"]}
        opciones = ["ALIMENTOS", "BEBIDAS"]
        mapa = {"ALIMENTOS": ["CARNES"], "BEBIDAS": ["AGUAS"]}
        precios, proveedor = "compras_sec_volatilidad", "compras_sec_proveedor"
        with patch.object(filtros.st, "session_state", estado):
            for vista in (precios, proveedor):
                self.assertEqual(filtros.preparar_filtros_vista(vista, opciones, mapa, ()),
                                 (("ALIMENTOS",), ("CARNES",)))

            filtros.poner_seleccion("cp_familias_volatilidad", ["BEBIDAS"])
            self.assertEqual(filtros.preparar_filtros_vista(precios, opciones, mapa, ()),
                             (("BEBIDAS",), ()))
            self.assertEqual(filtros.filtros_vista(proveedor),
                             {"Familia": ["ALIMENTOS"], "Subfamilia": ["CARNES"]})
            self.assertEqual(estado["compras_graf_filtro_fam"], ["ALIMENTOS"])

    def test_dispatcher_envia_a_cada_tarjeta_su_rango_e_historico_filtrados(self):
        d = pd.DataFrame([
            ("ALIMENTOS", "CARNES", "Entraña", "A", 10.0),
            ("ALIMENTOS", "VERDURAS", "Cebolla", "B", 20.0),
            ("BEBIDAS", "AGUAS", "Agua", "C", 30.0),
        ], columns=["Familia", "Subfamilia", "Producto", "Proveedor", "Valor compra"])
        d["Fecha documento"] = pd.Timestamp("2026-10-09")
        estado = {}
        expectativas = {
            "_compras_semanal_drill": ("semanal", "ALIMENTOS", "VERDURAS", "Cebolla"),
            "_compras_proveedor_drill": ("proveedor", "BEBIDAS", "AGUAS", "Agua"),
            "_compras_producto_drill": ("producto", "ALIMENTOS", "CARNES", "Entraña"),
            "_compras_volatilidad_drill": ("volatilidad", "BEBIDAS", "AGUAS", "Agua"),
            "_compras_vs_ano_pasado_drill": ("vs_ano_pasado", "ALIMENTOS", "VERDURAS", "Cebolla"),
            "_docs_seccion": ("documentos", "ALIMENTOS", "CARNES", "Entraña"),
        }
        with ExitStack() as stack:
            stack.enter_context(patch.object(compras.st, "session_state", estado))
            stack.enter_context(patch.object(compras.st, "container", side_effect=lambda **_: nullcontext()))
            stack.enter_context(patch.object(compras, "recortar_por_tarjeta", side_effect=lambda df, *_: df))
            stack.enter_context(patch.object(compras, "_render_rail", return_value="Volatilidad"))
            stack.enter_context(patch.object(compras, "publicar_contexto_ia"))
            stack.enter_context(patch.object(compras.data, "notas_restadas_compras", return_value=d))
            stack.enter_context(patch.object(compras, "seccion_perezosa",
                                            side_effect=lambda _c, _v, dibujar, **_: dibujar()))
            panel = stack.enter_context(patch.object(compras, "panel_filtros_vista"))
            dibujos = {}
            for funcion, (slug, familia, subfamilia, _) in expectativas.items():
                filtros.poner_seleccion(f"cp_familias_{slug}", [familia])
                filtros.poner_seleccion(f"cp_subfamilias_{slug}", [subfamilia])
                dibujos[funcion] = stack.enter_context(patch.object(compras, funcion))

            compras.renderizar_graficos_compras(d, "Compras", df_full=d)

        # El popover ⚙ va en todas menos en las que dibujan su ficha (regla #843).
        self.assertEqual(panel.call_count, len(expectativas) - len(filtros.VISTAS_CON_FICHA))
        self.assertNotIn("compras_sec_semanal", [c.args[0] for c in panel.call_args_list])
        for funcion, (slug, familia, subfamilia, producto) in expectativas.items():
            with self.subTest(funcion=funcion):
                args, kwargs = dibujos[funcion].call_args
                self.assertEqual(args[0]["Producto"].tolist(), [producto])
                if "d_full" in kwargs:
                    self.assertEqual(kwargs["d_full"]["Producto"].tolist(), [producto])
                if kwargs.get("familias"):
                    self.assertTrue(kwargs["familias"]["en_panel"])
                    con_ficha = f"compras_sec_{slug}" in filtros.VISTAS_CON_FICHA
                    self.assertEqual(bool(kwargs["familias"].get("ficha")), con_ficha)
        ficha = dibujos["_compras_semanal_drill"].call_args.kwargs["familias"]
        self.assertEqual(ficha["seccion"], "compras_sec_semanal")
        self.assertEqual([f for f, _ in ficha["todas"]], ["ALIMENTOS", "BEBIDAS"])
        self.assertEqual((ficha["elegidas"], ficha["subs"]["elegidas"]), (["ALIMENTOS"], ["VERDURAS"]))
        self.assertEqual(ficha["subs"]["mapa"], {"ALIMENTOS": ["CARNES", "VERDURAS"], "BEBIDAS": ["AGUAS"]})
        notas = dibujos["_compras_semanal_drill"].call_args.kwargs["d_nc"]
        self.assertEqual(notas["Producto"].tolist(), ["Cebolla"])
        # Comparten calendario. Los filtros y los recortes son independientes.
        self.assertEqual(compras.CATEGORIA_SEC["compras_sec_documentos"],
                         compras.CATEGORIA_SEC["compras_sec_proveedor"])


class FichaDeFamilias(unittest.TestCase):
    """Regla #843: la pieza dibuja el filtro y Python lo valida y lo escribe."""

    OPCIONES = ["ALIMENTOS", "BEBIDAS", "LIMPIEZA", "VINOS"]
    MAPA = {"ALIMENTOS": ("CARNES", "VERDURAS"), "BEBIDAS": ("AGUAS",), "VINOS": ("TINTOS",)}

    def _ficha(self, seleccion=((), ())):
        return filtros.datos_ficha("compras_sec_semanal", self.OPCIONES, self.MAPA,
                                   [["VINOS", 50.0], ["ALIMENTOS ", 100.0]], seleccion,
                                   ("ALIMENTOS", "VINOS", "YA NO EXISTE"))

    def test_lo_que_recibe_la_pieza(self):
        ficha = self._ficha((("VINOS", "ALIMENTOS"), ("TINTOS",)))
        # Todas las de la página, por lo que suman; la que no compró, con cero.
        self.assertEqual(ficha["todas"], [["ALIMENTOS", 100.0], ["VINOS", 50.0], ["BEBIDAS", 0.0], ["LIMPIEZA", 0.0]])
        self.assertEqual(ficha["elegidas"], ["VINOS", "ALIMENTOS"])
        self.assertEqual(ficha["subs"]["elegidas"], ["TINTOS"])
        self.assertEqual(ficha["subs"]["mapa"]["LIMPIEZA"], [])
        self.assertEqual(ficha["entrada"], ["ALIMENTOS", "VINOS"])
        self.assertTrue(ficha["ficha"])

    def test_solo_escribe_lo_que_python_ofrecio(self):
        ficha, estado = self._ficha(), {}
        with patch.object(filtros.st, "session_state", estado):
            for malo in (None, ["ALIMENTOS"], {"fam": "ALIMENTOS", "sub": []}, {"fam": ["ALIMENTOS"]},
                         {"fam": ["OTRA"], "sub": []}, {"fam": [["ALIMENTOS"]], "sub": []},
                         {"fam": ["ALIMENTOS"], "sub": ["TINTOS"]}, {"fam": [], "sub": ["CARNES"]},
                         {"fam": ["ALIMENTOS"], "sub": [{"x": 1}]}):
                with self.subTest(malo=malo):
                    self.assertFalse(filtros.aplicar_ficha(ficha, malo))
            self.assertEqual(estado, {})

            self.assertTrue(filtros.aplicar_ficha(ficha, {"fam": ["VINOS", "ALIMENTOS", "VINOS"], "sub": ["TINTOS"]}))
            self.assertEqual((estado["cp_familias_semanal"], estado["cp_subfamilias_semanal"]),
                             (["ALIMENTOS", "VINOS"], ["TINTOS"]))
            version = estado["cp_familias_semanal__v"]
            # Lo mismo otra vez no cambia nada: no hay por qué pedir una corrida.
            self.assertFalse(filtros.aplicar_ficha(ficha, {"fam": ["ALIMENTOS", "VINOS"], "sub": ["TINTOS"]}))
            self.assertEqual(estado["cp_familias_semanal__v"], version)
            # Todas y sin subfamilias es «sin filtro»; todas con una subfamilia, no.
            self.assertTrue(filtros.aplicar_ficha(ficha, {"fam": list(self.OPCIONES), "sub": []}))
            self.assertEqual((estado["cp_familias_semanal"], estado["cp_subfamilias_semanal"]), ([], []))
            self.assertTrue(filtros.aplicar_ficha(ficha, {"fam": list(self.OPCIONES), "sub": ["AGUAS"]}))
            self.assertEqual(estado["cp_familias_semanal"], self.OPCIONES)
            # Lo que escribe sobrevive a la preparación de la corrida siguiente.
            self.assertEqual(filtros.preparar_filtros_vista("compras_sec_semanal", self.OPCIONES, self.MAPA, ()),
                             (tuple(self.OPCIONES), ("AGUAS",)))

    def test_la_pieza_pide_la_corrida_solo_si_cambio(self):
        from graficos.compras import _comun
        ficha = {**self._ficha((("ALIMENTOS",), ())), "en_panel": True}
        estado = {"cp_familias_semanal": ["ALIMENTOS"], "cp_subfamilias_semanal": [],
                  "pieza": {"familias": {"fam": ["ALIMENTOS"], "sub": []}}}
        with patch.object(filtros.st, "session_state", estado), patch.object(_comun.st, "session_state", estado):
            _comun.cambiar_familias("pieza", "pendiente", ficha)
            self.assertNotIn("pendiente", estado)
            estado["pieza"] = {"familias": {"fam": [], "sub": []}}
            _comun.cambiar_familias("pieza", "pendiente", ficha)
            self.assertTrue(estado["pendiente"])
            self.assertEqual(estado["cp_familias_semanal"], [])
            # El filtro de la PÁGINA no se toca: es de las vistas sin ficha.
            self.assertNotIn("compras_graf_filtro_fam", estado)
            # Sin ficha, `en_panel` sigue sin mandar.
            estado.pop("pendiente")
            estado["pieza"] = {"familias": ["ALIMENTOS"]}
            _comun.cambiar_familias("pieza", "pendiente", {"todas": [["ALIMENTOS", 1.0]], "elegidas": [], "en_panel": True})
            self.assertNotIn("pendiente", estado)

    def test_quitar_el_filtro_cuando_la_pieza_no_se_dibuja(self):
        estado = {"cp_familias_semanal": ["LIMPIEZA"], "cp_subfamilias_semanal": ["X"]}
        with patch.object(filtros.st, "session_state", estado):
            filtros.quitar_filtros_vista("compras_sec_semanal", "pendiente")
        self.assertEqual((estado["cp_familias_semanal"], estado["cp_subfamilias_semanal"]), ([], []))
        self.assertTrue(estado["pendiente"])


if __name__ == "__main__":
    unittest.main()
