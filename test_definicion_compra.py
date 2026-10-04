"""test_definicion_compra.py — las NOTAS DE CRÉDITO de compras (regla #603).

Dos cosas, las dos sin secrets, sin red y sin navegador:

1. Las CUENTAS de `definicion_compra.py` sobre un parquet de mentira que
   reproduce los casos reales: la factura anulada entera y re-emitida, la
   devolución parcial de un producto, la nota por monto (sin líneas), la
   nota en dólares, la nota todavía generada, la que corrige una factura
   que el parquet no trae y la línea de nota cuyo producto no está en su
   factura. Montos inventados — el repo es público —, pero cada caso es
   uno que ya apareció en el Almacén.

2. El CABLEADO, leído del código con `ast`: que `data.cargar` reste las
   notas de compras para todos, que «Documentos SUNAT» pida el parquet sin
   restarlas (cruza documento contra documento) y que ninguna vista lea el
   parquet de notas por su cuenta.

La cifra contra el Almacén de verdad la da
`herramientas/cuadrar_compras.py` (necesita R2 y el SQL Server).

Se ejecuta solo:  python test_definicion_compra.py
"""

import ast
import sys
from pathlib import Path

import pandas as pd

import definicion_compra as dc

# La consola de Windows (cp1252) revienta con UnicodeEncodeError en el
# PRIMER print y el gate falla sin decir por qué — igual que los otros tests.
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
    if isinstance(exp, float) or isinstance(got, float):
        cond = got is not None and abs(float(got) - float(exp)) <= tol
    else:
        cond = got == exp
    ok(cond, nombre, f"got={got!r} exp={exp!r}")


# ── compras.parquet de mentira (nombres REALES de las columnas) ────────────
#   F-A  factura de pato, 40 kg a 90: anulada ENTERA por una nota P.
#   F-B  la re-emitida, igual: queda.
#   F-C  dos productos: devuelven 5 de 20 kg de lomo; el ajo queda.
#   F-D  dos líneas: una nota POR MONTO del 25 %.
#   F-E  en dólares (cambio 3,80): una nota en dólares por el total.
#   F-F  sin nota que valga: la suya está GENERADA (01).
#   F-G  una línea de nota pide un producto que la factura no tiene: se
#        reparte entre sus líneas como una nota por monto.
_FILAS = [
    # doc,  prov,   prod,   cant, valor,  moneda, cambio
    ("F-A", "00100", "PATO", 40.0, 3600.0, "01", 3.70),
    ("F-B", "00100", "PATO", 40.0, 3600.0, "01", 3.70),
    ("F-C", "00200", "LOMO", 20.0, 1500.0, "01", 3.70),
    ("F-C", "00200", "AJO", 10.0, 100.0, "01", 3.70),
    ("F-D", "00300", "PAPA", 100.0, 400.0, "01", 3.70),
    ("F-D", "00300", "CAMOTE", 50.0, 100.0, "01", 3.70),
    ("F-E", "00400", "SERV", 1.0, 760.0, "02", 3.80),
    ("F-F", "00500", "PAN", 10.0, 50.0, "01", 3.70),
    ("F-G", "00600", "LECHE", 10.0, 60.0, "01", 3.70),
    ("F-G", "00600", "QUESO", 2.0, 40.0, "01", 3.70),
]
compras = pd.DataFrame(_FILAS, columns=[dc.DOCUMENTO, dc.PROVEEDOR, dc.PRODUCTO,
                                        dc.CANTIDAD, dc.VALOR, "TIPO_MONEDA",
                                        dc.CAMBIO])
compras["VALOR_IGV_COMPRA_MN"] = compras[dc.VALOR] * 0.18
compras["VALOR_BRUTO_COMPRA_MN"] = compras[dc.VALOR] * 1.18
compras["PRECIO_UNIT"] = compras[dc.VALOR] / compras[dc.CANTIDAD]
compras["TOTAL NETO"] = compras.groupby(dc.DOCUMENTO)[dc.VALOR].transform("sum")
compras["FECHA_EMISION_DOC"] = pd.Timestamp("2026-09-10").date()

# La consulta del Sheet: una fila por línea DEVUELTA, con la cabecera de la
# nota repetida; la nota sin líneas, una fila con el producto vacío.
_NOTAS = [
    # nota, prov, tipo, estado, ref, moneda, neto_nota, prod, cant, neto_linea
    ("N-1", "00100", "P", "02", "F-A", "01", 3600.0, "PATO", 40.0, 3600.0),
    ("N-2", "00200", "P", "02", "F-C", "01", 375.0, "LOMO", 5.0, 375.0),
    ("N-3", "00300", "D", "02", "F-D", "01", 125.0, None, None, None),
    ("N-4", "00400", "D", "03", "F-E", "02", 200.0, None, None, None),
    ("N-5", "00500", "P", "01", "F-F", "01", 50.0, "PAN", 10.0, 50.0),
    ("N-6", "00999", "P", "02", "F-X", "01", 80.0, "OTRO", 1.0, 80.0),
    ("N-7", "00600", "P", "02", "F-G", "01", 30.0, "YOGUR", 3.0, 30.0),
    # Una nota P de DOS líneas: su cabecera (8 + 6) sale en las dos.
    ("N-8", "00200", "P", "02", "F-C", "01", 14.0, "AJO", 1.0, 10.0),
]
notas = pd.DataFrame(_NOTAS, columns=[dc.NC_NUMERO, dc.NC_PROVEEDOR, dc.NC_TIPO,
                                      dc.NC_ESTADO, dc.NC_REF, dc.NC_MONEDA,
                                      dc.NC_NETO, dc.NC_PRODUCTO, dc.NC_CANTIDAD,
                                      dc.NC_NETO_LINEA])
# N-8 tiene una segunda línea (el lomo de la misma factura, 0,5 kg).
notas = pd.concat([notas, pd.DataFrame([{
    dc.NC_NUMERO: "N-8", dc.NC_PROVEEDOR: "00200", dc.NC_TIPO: "P",
    dc.NC_ESTADO: "02", dc.NC_REF: "F-C", dc.NC_MONEDA: "01", dc.NC_NETO: 14.0,
    dc.NC_PRODUCTO: "LOMO", dc.NC_CANTIDAD: 0.5, dc.NC_NETO_LINEA: 4.0}])],
    ignore_index=True)

out = dc.aplicar_notas(compras, notas)


def fila(doc, prod):
    f = out[(out[dc.DOCUMENTO] == doc) & (out[dc.PRODUCTO] == prod)]
    return f.iloc[0] if len(f) == 1 else None


print("\n── la factura anulada entera y re-emitida ──")
ok(fila("F-A", "PATO") is None, "la factura anulada por la nota desaparece")
igual(float(fila("F-B", "PATO")[dc.VALOR]), 3600.0, "la re-emitida queda entera")
igual(float(out.loc[out[dc.PRODUCTO] == "PATO", dc.CANTIDAD].sum()), 40.0,
      "el pato comprado es 40 kg, no 80")

print("\n── la devolución parcial de un producto ──")
_lomo = fila("F-C", "LOMO")
igual(float(_lomo[dc.CANTIDAD]), 14.5, "lomo: 20 − 5 (N-2) − 0,5 (N-8) = 14,5 kg")
igual(float(_lomo[dc.VALOR]), 1121.0, "lomo: 1.500 − 375 − 4 = 1.121")
igual(float(_lomo[dc.VALOR]) / float(_lomo[dc.CANTIDAD]), 77.31,
      "el precio por kg casi no se mueve (la nota de 4 por 0,5 kg)", tol=0.01)
igual(float(_lomo["PRECIO_UNIT"]), 75.0, "PRECIO_UNIT es el de la factura")
igual(float(_lomo["VALOR_IGV_COMPRA_MN"]), 1121.0 * 0.18, "el IGV baja igual")
igual(float(_lomo[dc.COL_VALOR_NC]), 379.0, "VALOR_NC dice lo restado")
ok(_lomo[dc.COL_NOTA] == "N-2, N-8", "NOTA_CREDITO nombra las dos notas",
   repr(_lomo[dc.COL_NOTA]))
igual(float(fila("F-C", "AJO")[dc.VALOR]), 90.0,
      "ajo: la línea de 10 de N-8, aunque su cabecera (14) se repita")
igual(float(fila("F-C", "AJO")["TOTAL NETO"]), 1600.0,
      "la CABECERA no se toca: describe la factura emitida")

print("\n── la nota por monto, sin líneas ──")
_papa, _camote = fila("F-D", "PAPA"), fila("F-D", "CAMOTE")
igual(float(_papa[dc.VALOR]), 300.0, "papa: 400 × (1 − 125/500)")
igual(float(_papa[dc.CANTIDAD]), 75.0, "y su cantidad baja en la misma proporción")
igual(float(_camote[dc.VALOR]), 75.0, "camote: 100 × 0,75")
igual(float(_papa[dc.VALOR]) / float(_papa[dc.CANTIDAD]), 4.0,
      "el precio unitario no se mueve")

print("\n── la nota en dólares ──")
ok(fila("F-E", "SERV") is None,
   "200 dólares al cambio de SU factura (3,80) restan 760 de 760: la anula "
   "(y la nota es cancelada, 03, que también vale)")

print("\n── lo que no se aplica ──")
igual(float(fila("F-F", "PAN")[dc.VALOR]), 50.0, "una nota GENERADA (01) no resta")
ok(dc.COL_NOTA in out.columns and fila("F-F", "PAN")[dc.COL_NOTA] == "",
   "y la línea queda sin nota")
_ap = dc.aplicadas(compras, notas).set_index("nota")["estado"]
ok(_ap.get("N-6") == "sin factura en el parquet",
   "una nota de una factura que el parquet no trae no se aplica", repr(_ap.to_dict()))
ok("N-5" not in _ap.index, "la generada ni figura entre las procesadas")

print("\n── la línea de nota sin su producto en la factura ──")
igual(float(fila("F-G", "LECHE")[dc.VALOR]), 42.0,
      "se reparte como por monto: 60 × (1 − 30/100)")
igual(float(fila("F-G", "QUESO")[dc.VALOR]), 28.0, "queso: 40 × 0,7")

print("\n── totales ──")
igual(float(compras[dc.VALOR].sum() - out[dc.VALOR].sum()),
      3600.0 + 379.0 + 10.0 + 125.0 + 760.0 + 30.0,
      "lo restado es la suma de las notas procesadas con factura")
igual(float(out[dc.COL_VALOR_NC].sum()), 379.0 + 10.0 + 125.0 + 30.0,
      "VALOR_NC suma lo restado a las líneas que QUEDAN")

print("\n── sin notas no cambia nada ──")
ok(dc.aplicar_notas(compras, None) is compras, "sin parquet de notas: el mismo df")
ok(dc.aplicar_notas(compras, notas.iloc[0:0]) is compras, "con el parquet vacío: igual")
ok(dc.aplicar_notas(compras, notas.drop(columns=[dc.NC_NETO_LINEA])) is compras,
   "si a las notas les falta una columna: igual")
ok(dc.aplicar_notas(compras.drop(columns=[dc.CAMBIO]), notas) is not None,
   "si a compras le falta una columna, no revienta")
ok(dc.COL_NOTA not in compras.columns, "aplicar no toca el df de entrada")

print("\n── la consulta del Sheet ──")
_sql = dc.consulta_sheet()
for col in (dc.NC_NUMERO, dc.NC_PROVEEDOR, dc.NC_TIPO, dc.NC_ESTADO, dc.NC_REF,
            dc.NC_MONEDA, dc.NC_NETO, dc.NC_PRODUCTO, dc.NC_CANTIDAD,
            dc.NC_NETO_LINEA):
    ok(f"AS [{col}]" in _sql, f"la consulta trae [{col}]")
ok("nCantidad > 0" in _sql, "sólo las líneas DEVUELTAS (DNOTACREDITO trae todas)")
ok("LEFT JOIN ALMACEN.DBO.DNOTACREDITO" in _sql,
   "LEFT JOIN: la nota por monto, sin líneas, también sale")

# ── El cableado ──────────────────────────────────────────────────────────
print("\n── el cableado ──")
_data = (RAIZ / "data.py").read_text(encoding="utf-8")
_arbol = ast.parse(_data)
_cargar = next(n for n in ast.walk(_arbol)
               if isinstance(n, ast.FunctionDef) and n.name == "cargar")
ok("notas_credito" in [a.arg for a in _cargar.args.args],
   "data.cargar tiene el interruptor notas_credito")
ok("_compras_netas_cacheable" in ast.dump(_cargar),
   "data.cargar resta las notas de compras (para todos los consumidores)")
_kpis = next(n for n in ast.walk(_arbol)
             if isinstance(n, ast.FunctionDef) and n.name == "_resumen_kpis_cacheable")
ok("_compras_netas_cacheable" in ast.dump(_kpis),
   "los KPIs del rail suman las compras con las notas restadas")

_sunat = (RAIZ / "graficos" / "sunat_reporte.py").read_text(encoding="utf-8")
_pide_crudo = any(
    isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "cargar"
    and any(k.arg == "notas_credito" and getattr(k.value, "value", None) is False
            for k in n.keywords)
    for n in ast.walk(ast.parse(_sunat)))
ok(_pide_crudo, "«Documentos SUNAT» pide compras SIN restar las notas",
   "cruza documento contra documento: una factura anulada que desaparece "
   "saldría «Solo SUNAT» siendo falso (regla #301)")

_lectores = [p.relative_to(RAIZ).as_posix()
             for p in (RAIZ / "graficos").rglob("*.py")
             if "notascreditocompras" in p.read_text(encoding="utf-8")
             or "ARCHIVO_NOTAS" in p.read_text(encoding="utf-8")]
ok(not _lectores, "ninguna vista lee el parquet de notas por su cuenta",
   f"lo leen: {_lectores} — las notas se restan UNA vez, en data.cargar")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (notas de crédito de compras)")
