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

        self.assertEqual(panel.call_count, len(expectativas))
        for funcion, (_, _, _, producto) in expectativas.items():
            with self.subTest(funcion=funcion):
                args, kwargs = dibujos[funcion].call_args
                self.assertEqual(args[0]["Producto"].tolist(), [producto])
                if "d_full" in kwargs:
                    self.assertEqual(kwargs["d_full"]["Producto"].tolist(), [producto])
                if kwargs.get("familias"):
                    self.assertTrue(kwargs["familias"]["en_panel"])
        notas = dibujos["_compras_semanal_drill"].call_args.kwargs["d_nc"]
        self.assertEqual(notas["Producto"].tolist(), ["Cebolla"])
        # Comparten calendario. Los filtros y los recortes son independientes.
        self.assertEqual(compras.CATEGORIA_SEC["compras_sec_documentos"],
                         compras.CATEGORIA_SEC["compras_sec_proveedor"])


if __name__ == "__main__":
    unittest.main()
