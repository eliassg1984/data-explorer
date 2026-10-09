"""test_costo_ventas.py — el COSTO DE VENTAS del reporte «Costos» (regla #622).

Sin secrets, sin red y sin navegador:

1. Las CUENTAS de `costo_ventas.py` sobre parquets de mentira con los nombres
   reales de las columnas y cada caso que ya apareció: el cierre de setiembre
   registrado el 1 de octubre, el área que cuenta a mitad de mes y otra vez
   al cierre, Costos de producción (que no entra), la salida anulada, el tipo
   de descargo «---», la cortesía, Eventos y Venta interna (que van aparte),
   Bebidas Calientes (que es Bebidas) y el mes sin cierre anterior. Montos
   inventados: el repo es público.

2. `definicion_venta.por_grupo_dia`, que separa venta y cortesía, cuenta un
   ítem una vez y deja fuera lo anulado.

3. El CABLEADO, con `ast`: que el reporte esté registrado en el dispatcher
   y en `data.REPORTES`, y que la vista no defina la venta por su cuenta.

La cifra sobre R2 se comparó contra el boceto aprobado el 2026-10-09: igual
mes por mes y familia por familia.

Se ejecuta solo:  python test_costo_ventas.py
"""

import ast
import sys
from pathlib import Path

import pandas as pd

import costo_ventas as cv
import definicion_venta as dv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent
_fallos = []


def ok(cond, nombre, detalle=""):
    print(f"{'OK  ' if cond else 'FALLA'}  {nombre}")
    if not cond:
        _fallos.append(f"{nombre}{(' — ' + detalle) if detalle else ''}")
        if detalle:
            print(f"         {detalle}")


def igual(got, exp, nombre, tol=0.005):
    if isinstance(exp, (int, float)) and not isinstance(exp, bool):
        cond = got is not None and abs(float(got) - float(exp)) <= tol
    else:
        cond = got == exp
    ok(cond, nombre, f"got={got!r} exp={exp!r}")


# ── ajusteinventario.parquet de mentira ──────────────────────────────────
# Tres cierres de fin de mes: agosto (registrado el 2 set), setiembre (1 oct)
# y octubre (3 nov). COCINA cuenta además a mitad de setiembre (16 set): el
# que manda es el del 1 oct. Una línea de COSTOS PRODUCCION no entra.
def _aj(fecha, cod, area, fam, valor):
    return {"FECHA APERTURA INVENTARIO": pd.Timestamp(fecha), "CODIGO AREA": cod,
            "AREA": area, "FAMILIA": fam, "VALORIZADO TOTAL": valor}


ajuste = pd.DataFrame([
    _aj("2026-09-02 10:00", "000", "ALMACEN CENTRAL", "ALIMENTOS", 1000.0),
    _aj("2026-09-02 10:00", "000", "ALMACEN CENTRAL", "VINOS Y ESPUMANTES", 300.0),
    _aj("2026-09-02 11:00", "001", "COCINA", "ALIMENTOS", 200.0),
    _aj("2026-09-16 15:00", "001", "COCINA", "ALIMENTOS", 999.0),
    _aj("2026-10-01 17:00", "000", "ALMACEN CENTRAL", "ALIMENTOS", 800.0),
    _aj("2026-10-01 17:00", "000", "ALMACEN CENTRAL", "VINOS Y ESPUMANTES", 250.0),
    _aj("2026-10-01 17:00", "000", "ALMACEN CENTRAL", "COSTOS PRODUCCION", 5000.0),
    _aj("2026-10-01 18:00", "001", "COCINA", "ALIMENTOS", 150.0),
    _aj("2026-10-01 18:00", "001", "COCINA", "ENVASES Y EMBALAJES", 40.0),
    _aj("2026-11-03 09:00", "000", "ALMACEN CENTRAL", "ALIMENTOS", 700.0),
    _aj("2026-11-03 09:00", "001", "COCINA", "ALIMENTOS", 100.0),
])

inv, areas = cv.inventario_por_mes(ajuste)
P = lambda s: pd.Period(s, freq="M")  # noqa: E731
igual(float(inv.loc[P("2026-08"), "Alimentos"]), 1200.0,
      "el cierre registrado el 2 de setiembre es el de AGOSTO (mes operativo)")
igual(float(inv.loc[P("2026-09"), "Alimentos"]), 950.0,
      "setiembre: manda el último cierre de cada área (COCINA 150, no 999)")
igual(float(inv.loc[P("2026-09"), "Envases"]), 40.0, "Envases entra al inventario")
igual(float(inv.loc[P("2026-09"), "Vinos"]), 250.0, "Vinos entra al inventario")
ok(5000.0 not in inv.to_numpy(), "Costos de producción no entra")
igual(areas[P("2026-09")]["COCINA"][1], 190.0,
      "las áreas del cierre llevan lo que entró de cada una")
igual(cv.meses_del_reporte(inv), [P("2026-09"), P("2026-10")],
      "sólo los meses con cierre propio Y del anterior")

# ── compras.parquet de mentira ───────────────────────────────────────────
compras = pd.DataFrame({
    "FECHA_EMISION_DOC": pd.to_datetime(["2026-09-05", "2026-09-20", "2026-09-21",
                                         "2026-10-02", "2026-10-03"]),
    "FAMILIA": ["ALIMENTOS", "BEBIDAS SIN ALCOHOL", "COSTOS PRODUCCION",
                "ALIMENTOS", "ENVASES Y EMBALAJES"],
    "VALOR_COMPRA": [500.0, 80.0, 999.0, 400.0, 30.0],
})
cm = cv.compras_por_mes(compras)
igual(float(cm.loc[P("2026-09"), "Alimentos"]), 500.0, "compras de alimentos de setiembre")
igual(float(cm.loc[P("2026-09"), "Bebidas"]), 80.0, "bebidas sin alcohol es Bebidas")
igual(float(cm.loc[P("2026-09")].sum()), 580.0, "compras de Costos de producción no entran")

# ── salidas.parquet de mentira ───────────────────────────────────────────
salidas = pd.DataFrame({
    "FECHA REGISTRO": pd.to_datetime(["2026-09-10", "2026-09-11", "2026-09-12",
                                      "2026-09-13", "2026-10-04", "2026-09-14"]),
    "NOMBRE ESTADO SALIDA": ["PROCESADO", "PROCESADO", "ANULADO", "PROCESADO",
                             "PROCESADO", "PROCESADO"],
    "TIPO DESCARGO": ["Comida Personal", "Bajas", "Bajas", "---", "Bajas", "Comida Personal"],
    "NOMBRE FAMILIA": ["ALIMENTOS", "ALIMENTOS", "ALIMENTOS", "ALIMENTOS",
                       "VINOS Y ESPUMANTES", "ALIMENTOS"],
    "VALOR NETO": [60.0, 20.0, 999.0, 7.0, 15.0, 40.0],
})
sal = cv.salidas_por_mes(salidas)
igual(list(sal), ["Bajas", "Comida Personal"],
      "«Bajas» primero; el tipo «---» no es una salida")
igual(float(sal["Bajas"].loc[P("2026-09"), "Alimentos"]), 20.0,
      "la baja anulada no cuenta")
igual(float(sal["Comida Personal"].loc[P("2026-09"), "Alimentos"]), 100.0,
      "las salidas se suman por mes de registro")
igual(float(sal["Bajas"].loc[P("2026-10"), "Vinos"]), 15.0, "las bajas de vinos")

# ── ventas: definicion_venta.por_grupo_dia ───────────────────────────────
ventas = pd.DataFrame({
    dv.FECHA: pd.to_datetime(["2026-09-03", "2026-09-03", "2026-09-04", "2026-09-05",
                              "2026-09-06", "2026-09-07", "2026-09-08", "2026-10-02"]),
    dv.GRUPO: ["Alimentos", "Alimentos", "Bebidas Calientes", "Alimentos",
               "Eventos", "Alimentos", "Vinos y Espumantes", "Alimentos"],
    dv.CLASE: [dv.VENTA, dv.VENTA, dv.VENTA, dv.CORTESIA, dv.VENTA, dv.ANULADO,
               dv.NOTA_CREDITO, dv.VENTA],
    dv.LLAVE_ITEM: ["A1", "A1", "B1", "C1", "E1", "X1", "N1", "D1"],
    dv.NETO_ITEM: [100.0, 100.0, 10.0, 0.0, 500.0, 70.0, -50.0, 300.0],
    dv.COSTO: [30.0, 30.0, 3.0, 12.0, 90.0, 20.0, -15.0, 95.0],
})
pgd = dv.por_grupo_dia(ventas)
igual(list(pgd.columns), list(dv.POR_GRUPO_DIA), "por_grupo_dia: columnas por nombre")
ok(set(pgd["clase"]) == {dv.VENTA, dv.CORTESIA},
   "la nota de crédito es venta (resta); lo anulado no está")
igual(float(pgd.loc[(pgd["grupo"] == "Alimentos") & (pgd["clase"] == dv.VENTA)
                    & (pgd["dia"] == pd.Timestamp("2026-09-03")), "neto"].sum()),
      100.0, "un ítem pagado en dos formas cuenta una vez (regla #517)")

venta, pos, cort, v_ap, c_ap = cv.ventas_por_mes(pgd)
igual(float(venta.loc[P("2026-09"), "Alimentos"]), 100.0, "venta neta de alimentos")
igual(float(venta.loc[P("2026-09"), "Bebidas"]), 10.0, "Bebidas Calientes es Bebidas")
igual(float(venta.loc[P("2026-09"), "Vinos"]), -50.0, "la nota de crédito resta")
igual(float(pos.loc[P("2026-09"), "Alimentos"]), 30.0, "el costo según el POS")
igual(float(cort.loc[P("2026-09"), "Alimentos"]), 12.0, "la cortesía, a su costo")
igual(float(v_ap.loc[P("2026-09"), "Eventos"]), 500.0, "Eventos va aparte")
ok(float(venta.loc[P("2026-09")].sum()) == 60.0, "Eventos no suma a la venta")

# ── armar: la tabla entera ───────────────────────────────────────────────
D = cv.armar(ajuste, compras, salidas, pgd)
igual(D["meses"], ["2026-09", "2026-10"], "armar: meses")
f = D["filas"]
igual(f["inv_inicial"]["Alimentos"][0], 1200.0, "el inicial de setiembre es el final de agosto")
igual(f["inv_final"]["Alimentos"][0], 950.0, "el final de setiembre")
consumo = (f["inv_inicial"]["Alimentos"][0] + f["compras"]["Alimentos"][0]
           - f["inv_final"]["Alimentos"][0])
igual(consumo, 750.0, "consumo operativo = inicial + compras − final")
carta = consumo - D["salidas"]["Bajas"]["Alimentos"][0] - f["cortesias"]["Alimentos"][0]
igual(carta, 718.0, "consumo carta = operativo − bajas − cortesías")
igual(D["venta_extra"]["Eventos"][0], 500.0, "armar: Eventos aparte")
ok(set(cv.tabla_larga(D).columns) == {"MES", "FAMILIA", "CONCEPTO", "SOLES"},
   "la tabla para el asistente, con columnas por nombre")
igual(cv.armar(ajuste.iloc[:0], compras, salidas, pgd)["meses"], [],
      "sin cierres no hay meses (y no revienta)")

# ── Cableado ─────────────────────────────────────────────────────────────
import graficos  # noqa: E402
import data      # noqa: E402

ok("Costos" in graficos._DASHBOARDS and "Costos" in graficos._RAILS,
   "el reporte Costos está en el dispatcher y en _RAILS")
ok(data.REPORTES.get("Costos", {}).get("fecha", "x") is None,
   "Costos no lleva fecha en la franja (los meses son su eje)")
_vista = (RAIZ / "graficos" / "costos.py").read_text(encoding="utf-8")
ok(not any(isinstance(n, ast.Constant) and n.value in ("CORTESIA", "ANULADO")
           for n in ast.walk(ast.parse(_vista))),
   "la vista no define la venta por su cuenta (regla #524)")

print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for x in _fallos:
        print(f"   · {x}")
    sys.exit(1)
print("✅ Todo OK (costo de ventas)")
