"""Relaciones por código, fechas, activos y evidencia sin duplicar cabeceras."""
import unittest

import pandas as pd

from flujo_producto import armar


def fuentes():
    maestro = pd.DataFrame([
        ['I1', 'Lomo entero', 'KILOS'], ['C1', 'Lomo al trapo', 'UND'],
        ['B1', 'Salsa', 'KILOS'], ['I2', 'Lomo entero', 'KILOS']],
        columns=['CODIGO PRODUCTO', 'NOMBRE PRODUCTO', 'UNIDAD KARDEX'])
    compras = pd.DataFrame([['I1', '2026-10-01', 'F01', 'Proveedor']],
        columns=['COD_PRODUCTO', 'FECHA_EMISION_DOC', 'NUM_DOCUMENTO', 'PROVEEDOR'])
    porc = pd.DataFrame([
        ['P1', '2026-10-02', 'I1', 'C1', 10],
        ['P1', '2026-10-02', 'I1', 'C1', 10],
        ['P0', '2024-01-01', 'I2', 'C1', 5],
        ['P2', '2026-10-03', 'I1', 'I2', 0]],
        columns=['COD PORC', 'FEC REGIST', 'COD PROD INIC', 'COD PROD FINAL', 'CANT RESULT'])
    base = pd.DataFrame([
        ['B1', 'I1', 'RB.ACTIV', 'INS.ACT'], ['B1', 'I2', 'RB.INACT', 'INS.ACT']],
        columns=['COD PROD RB', 'COD INS RB', 'RB ACT', 'INS ACTIVO'])
    venta = pd.DataFrame([
        ['I1', 'Lomo al Trapo 1kg', 'C1', 'ACTIV', 'ACTIV'],
        ['V2', 'Plato inactivo', 'B1', 'INACTIV', 'ACTIV'],
        ['V3', 'Plato sin confirmar', 'B1', '', 'ACTIV']],
        columns=['COD PLATO', 'NOMB PLATO', 'COD INS', 'ITEM VENTA ACTIVO', 'INS ACTIVO'])
    return maestro, compras, porc, base, venta


class Flujo(unittest.TestCase):
    def test_cadena_real_por_codigo_y_no_por_nombre(self):
        d = armar(*fuentes(), rango=['2026-10-01', '2026-10-28'])
        edges = {(e['origen'], e['destino'], e['tipo']) for e in d['enlaces']}
        self.assertIn(('p:I1', 'p:C1', 'porcionamiento'), edges)
        self.assertIn(('p:C1', 'v:I1', 'receta de venta'), edges)
        self.assertNotIn('p:I2', {n['id'] for n in d['nodos']})
        # El plato y el insumo comparten código: siguen siendo nodos distintos.
        self.assertIn('v:I1', {n['id'] for n in d['nodos']})
        self.assertFalse(d['avisos'])

    def test_un_documento_repetido_y_compras_con_fecha_canonica(self):
        d = armar(*fuentes(), rango=['2026-10-01', '2026-10-28'])
        e = next(e for e in d['enlaces'] if e['tipo'] == 'porcionamiento')
        self.assertEqual(e['cantidad'], 1)
        self.assertEqual(e['registros'][0]['doc'], 'P1')
        n = next(n for n in d['nodos'] if n['id'] == 'p:I1')
        self.assertEqual(n['compras'], [('F01', '2026-10-01', 'Proveedor')])
        self.assertNotIn('v:V2', {n['id'] for n in d['nodos']})
        self.assertNotIn('v:V3', {n['id'] for n in d['nodos']})

    def test_recetas_son_actuales_y_no_desaparecen_sin_compras(self):
        d = armar(*fuentes(), rango=['2026-11-01', '2026-11-28'])
        self.assertTrue(any(e['tipo'] == 'receta de venta' for e in d['enlaces']))
        self.assertFalse(any(e['tipo'] == 'porcionamiento' for e in d['enlaces']))
        self.assertTrue(all(not n['compras'] for n in d['nodos']))

    def test_fuentes_ausentes_y_correcciones_no_causan_recursion(self):
        args = list(fuentes())
        args[2] = pd.concat([args[2], pd.DataFrame([['P3', '2026-10-03', 'C1', 'I1', 1]],
                                                 columns=args[2].columns)])
        d = armar(*args, rango=['2026-10-01', '2026-10-28'])
        self.assertTrue(any(e['origen'] == 'p:C1' and e['destino'] == 'p:I1' for e in d['enlaces']))
        vacio = armar(None, None, None, None, None, rango=['2026-10-01', '2026-10-28'])
        self.assertEqual(vacio['enlaces'], [])
        self.assertEqual(len(vacio['avisos']), 4)


if __name__ == '__main__':
    unittest.main()
