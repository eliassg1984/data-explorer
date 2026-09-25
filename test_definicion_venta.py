"""test_definicion_venta.py — la DEFINICIÓN DE VENTA (regla #524).

Dos cosas, las dos sin secrets, sin red y sin navegador:

1. Las CUENTAS de `definicion_venta.py` sobre un parquet de mentira que
   reproduce los casos reales: el canje de una boleta por factura (boleta,
   factura y nota de crédito del mismo pedido, en días distintos), una
   cuenta dividida, una devolución, una cortesía, un anulado y un documento
   pagado con dos formas de pago. Los montos son inventados — el repo es
   público —, pero cada caso es uno que ya apareció en `ventas.parquet`.

2. El CABLEADO, leído del código con `ast`: que nadie vuelva a definir la
   venta por su cuenta. Así nació la regla: el Resumen sacaba cortesías y
   anulados, las otras nueve vistas y el rail no, y nadie restaba las notas
   de crédito.

La cifra contra el POS de verdad no vive acá (necesita R2 y el SQL Server
del restaurante): la da `herramientas/cuadrar_ventas.py`.

Se ejecuta solo:  python test_definicion_venta.py
"""

import ast
import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import definicion_venta as dv

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


# ── El parquet de mentira ──────────────────────────────────────────────────
# Columnas con los nombres REALES de `ventas.parquet` (incluido el espacio
# de « TOTAL NC» y la errata de «DDCOUMENTO»). Una fila por ítem Y por
# forma de pago, como el de verdad.
D1, D3 = dt.date(2026, 9, 1), dt.date(2026, 9, 3)


def _fila(doc, tipo_cod, tipo, estado, fecha, ped, pax, item, prod, cant,
          carta, desc, pago="1", propina=0.0, nc=None, nc_fecha=None,
          total_doc=None, total_nc=None, monto_pago=None):
    venta = carta * cant - desc if item is not None else np.nan
    return {
        "LLAVE LOCAL DOCUMENTO": "L" + doc,
        "NUMERO DOCUMENTO": doc,
        "COD TIPO DOC": tipo_cod,
        "TIPO DOC": tipo,
        "ESTADO DOCUMENTO": estado,
        "FEC REG DOCUMENTO": pd.Timestamp(fecha),
        "LLAVE LOCAL PEDIDO": ped,
        "CODIGO PEDIDO DDOCUMENTO": ped,
        "CANT PAX": pax,
        "LLAVE LOCAL DOCUMENTO ITEM": (f"L{doc}{item}" if item is not None
                                       else None),
        "LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO": (f"L{doc}P{pago}"
                                                   if pago else None),
        "NOMB ITEM VENTA": prod,
        "CANTIDAD ITEM DDOCUMENTO": cant,
        "PRECIO OFICIAL ITEM DDOCUMENTO": carta,
        "PRECIO COSTO": carta * 0.3 if carta else np.nan,
        "DESCUENTO ITEM DDOCUMENTO": desc,
        "VENTA ITEM DDOCUMENTO": venta,
        "NETO TOTAL ITEM DDOCUMENTO": venta / 1.18 if item is not None else np.nan,
        "IGV ITEM DDOCUMENTO": venta - venta / 1.18 if item is not None else np.nan,
        "RECARGO ITEM DDCOUMENTO": 0.0,
        "TOTAL MDOCUMENTO": total_doc,
        "MONTO TIPO PAGO DOC": monto_pago,
        "MONTO PROPINA": propina,
        "FECHA REGISTRO PAGO DOC": pd.Timestamp(fecha) if pago else pd.NaT,
        "NOTA CREDITO": nc,
        "FECH REG NC": pd.Timestamp(nc_fecha) if nc_fecha else pd.NaT,
        " TOTAL NC": total_nc,
    }


def _parquet():
    f = []
    # B1: boleta del día 1, pedido P (4 pax), pagada con DOS formas → cada
    # ítem sale dos veces. El día 3 se anula con la nota C1 y se reemite
    # como factura F1: el canje.
    for pago, monto in (("1", 120.0), ("2", 80.0)):
        f.append(_fila("B1", "02", "Boleta Electronica", "PAGADO", D1, "P", 4,
                       "01", "Lomo", 1, 110.0, 10.0, pago, 20.0 if pago == "1"
                       else 0.0, nc="C1", nc_fecha=D3, total_doc=200.0,
                       total_nc=200.0, monto_pago=monto))
        f.append(_fila("B1", "02", "Boleta Electronica", "PAGADO", D1, "P", 4,
                       "02", "Agua", 2, 50.0, 0.0, pago, 20.0 if pago == "1"
                       else 0.0, nc="C1", nc_fecha=D3, total_doc=200.0,
                       total_nc=200.0, monto_pago=monto))
    f.append(_fila("F1", "01", "Factura Electronica", "PAGADO", D3, "P", 4,
                   "01", "Lomo", 1, 110.0, 10.0, total_doc=200.0))
    f.append(_fila("F1", "01", "Factura Electronica", "PAGADO", D3, "P", 4,
                   "02", "Agua", 2, 50.0, 0.0, total_doc=200.0))
    # C1: la nota, SIN ítems, con su total en negativo.
    f.append(_fila("C1", "04", "NC B Electronica", "PROCESADO", D3, None,
                   np.nan, None, None, np.nan, np.nan, np.nan, pago=None,
                   propina=np.nan, total_doc=-200.0))
    # Q: cuenta dividida en dos boletas del mismo pedido (2 pax cada una).
    f.append(_fila("B2", "02", "Boleta Electronica", "C.POR COBRAR", D3, "Q",
                   2, "01", "Pato", 1, 60.0, 0.0, total_doc=60.0))
    f.append(_fila("B3", "02", "Boleta Electronica", "PAGADO", D3, "Q", 2,
                   "01", "Pisco", 1, 20.0, 0.0, total_doc=20.0))
    # Una cortesía y un anulado: ninguno es venta.
    f.append(_fila("K1", "00", "CORTESIA", "PAGADO", D3, "R", 1, "01",
                   "Postre", 1, 60.0, 0.0, total_doc=60.0))
    f.append(_fila("A1", "02", "Boleta Electronica", "ANULADO", D3, "S", 2,
                   "01", "Lomo", 1, 90.0, 0.0, total_doc=90.0))
    return pd.DataFrame(f)


def _items(df):
    llave = df["LLAVE LOCAL DOCUMENTO ITEM"]
    return df[~(llave.duplicated() & llave.notna())]


def _venta_dia(df):
    it = dv.solo_venta(_items(df))
    return it.groupby(it["FEC REG DOCUMENTO"].dt.date)[
        "VENTA ITEM DDOCUMENTO"].sum()


crudo = _parquet()
prep = dv.preparar(crudo, D1, D3)

print("── clasificación ──")
_clase = (prep.drop_duplicates("NUMERO DOCUMENTO")
          .set_index("NUMERO DOCUMENTO")[dv.CLASE].to_dict())
igual(_clase.get("B1"), dv.VENTA, "boleta pagada = Venta")
igual(_clase.get("B2"), dv.VENTA, "por cobrar = Venta (el 03 del POS)")
igual(_clase.get("F1"), dv.VENTA, "factura = Venta")
igual(_clase.get("K1"), dv.CORTESIA, "tipo CORTESIA = Cortesía")
igual(_clase.get("A1"), dv.ANULADO, "estado ANULADO = Anulado")
igual(_clase.get("C1"), dv.NOTA_CREDITO, "la nota = Nota de crédito")
ok(len(crudo) == 11, "el df de entrada no se toca", f"{len(crudo)} filas")
ok(dv.CLASE not in crudo.columns, "ni se le agrega la columna")

print("\n── la nota de crédito: los ítems del anulado, en negativo ──")
nota = prep[prep[dv.CLASE] == dv.NOTA_CREDITO]
igual(len(nota), 2, "un renglón por ÍTEM del anulado (no por forma de pago)")
igual(set(nota["FEC REG DOCUMENTO"].dt.date), {D3}, "con la fecha de la nota")
igual(set(nota["NUMERO DOCUMENTO"]), {"C1"}, "con el número de la nota")
igual(set(nota["TIPO DOC"]), {"NC B Electronica"}, "y el tipo de la nota")
igual(float(nota["VENTA ITEM DDOCUMENTO"].sum()), -200.0, "venta en negativo")
igual(float(nota["CANTIDAD ITEM DDOCUMENTO"].sum()), -3.0,
      "cantidad en negativo (los platos también se devuelven)")
igual(float((nota["PRECIO OFICIAL ITEM DDOCUMENTO"]
             * nota["CANTIDAD ITEM DDOCUMENTO"]).sum()), -210.0,
      "la carta sale negativa sola: unitario × cantidad negativa")
igual(set(nota["CANT PAX"]), {-4.0}, "pax en negativo")
igual(float(nota[dv.COSTO].sum()), -63.0,
      "y el costo de la línea: −(33 × 1 + 15 × 2)")
b1 = _items(prep)[_items(prep)["NUMERO DOCUMENTO"] == "B1"]
igual(float(b1[dv.COSTO].sum()), 63.0,
      "el costo es de la LÍNEA: 33 × 1 + 15 × 2 (sumar el unitario daba 48)")
ok(nota["MONTO PROPINA"].isna().all(), "la nota no trae propina")
ok(nota["LLAVE LOCAL DOCUMENTO ITEM"].is_unique
   and not nota["LLAVE LOCAL DOCUMENTO ITEM"].isin(
       crudo["LLAVE LOCAL DOCUMENTO ITEM"]).any(),
   "llaves de ítem propias: `unico_por_item` no las confunde con el anulado")
ok(pd.api.types.is_datetime64_any_dtype(prep["FECHA REGISTRO PAGO DOC"]),
   "vaciar el pago no vuelve `object` una columna de fechas",
   str(prep["FECHA REGISTRO PAGO DOC"].dtype))
ok(not ((prep["NUMERO DOCUMENTO"] == "C1")
        & prep["LLAVE LOCAL DOCUMENTO ITEM"].isna()).any(),
   "la fila sin ítems de la nota ya no está")

print("\n── la venta ──")
vd = _venta_dia(prep)
igual(float(vd.get(D1, 0)), 200.0, "día 1: la boleta")
igual(float(vd.get(D3, 0)), 80.0,
      "día 3: factura 200 − nota 200 + la cuenta dividida 80")
igual(float(vd.sum()), 280.0, "el canje cuenta UNA venta, no dos")
igual(float(dv.solo_venta(_items(prep))["VENTA ITEM DDOCUMENTO"].sum()), 280.0,
      "sin cortesía (60) ni anulado (90)")

print("\n── clientes: la mesa que vino cuenta, la nota resta ──")
it = dv.solo_venta(_items(prep)).assign(
    dia=lambda x: x["FEC REG DOCUMENTO"].dt.date)
pax_dia = dv.pax_por(it, "LLAVE LOCAL PEDIDO", "CANT PAX",
                     doc="LLAVE LOCAL DOCUMENTO", por="dia")
igual(float(pax_dia.get(D1, 0)), 4.0, "día 1: la mesa del canje")
igual(float(pax_dia.get(D3, 0)), 2.0,
      "día 3: la cuenta dividida una vez (2), el canje cero")
igual(dv.pax_por(it, "LLAVE LOCAL PEDIDO", "CANT PAX",
                 doc="LLAVE LOCAL DOCUMENTO"), 6.0,
      "el rango entero: 4 + 2 — igual a la suma de los días")
igual(dv.pax_por(it[it["dia"] == D3], "LLAVE LOCAL PEDIDO", "CANT PAX"), 2.0,
      "sin la columna del comprobante, la regla vieja da bien el día")
dev = pd.DataFrame({"ped": ["X", "X"], "pax": [3.0, -3.0], "doc": ["B", "C"],
                    "dia": [D1, D3]})
igual(float(dv.pax_por(dev, "ped", "pax", doc="doc", por="dia").get(D3, 0)),
      -3.0, "devolución: el día de la nota resta la mesa")
igual(dv.pax_por(dev, "ped", "pax", doc="doc"), 0.0,
      "y en el rango entero la mesa no queda")

print("\n── comprobantes ──")
docs = dv.documentos_por(it, "LLAVE LOCAL DOCUMENTO", dv.CLASE, por="dia")
igual(float(docs.get(D1, 0)), 1.0, "día 1: la boleta")
igual(float(docs.get(D3, 0)), 2.0,
      "día 3: factura + dos boletas − la nota = 2")

print("\n── el cuadre ──")
pt = dv.puente(_items(prep))
igual(pt.get("documentos"), 480.0, "facturas y boletas: 200 + 200 + 60 + 20")
igual(pt.get("notas_credito"), -200.0, "notas de crédito")
igual(pt.get("venta"), 280.0, "venta = documentos − notas")
igual(pt.get("cortesias"), 60.0, "cortesías, aparte")
igual(pt.get("anulados"), 90.0, "anulados, aparte")
igual(pt.get("carta", 0) - pt.get("descuentos", 0), pt.get("documentos"),
      "carta − descuentos = facturas y boletas (se cumple línea por línea)")

print("\n── el rango: lo que no es del rango se va ──")
solo3 = dv.preparar(crudo, D3, D3)
ok((solo3["FEC REG DOCUMENTO"].dt.date == D3).all(),
   "sólo filas del día 3 (el anulado del día 1 vino para espejarse)")
igual(float(_venta_dia(solo3).sum()), 80.0,
      "el día 3 solo: la nota resta lo que la factura suma")
sin_orig = dv.preparar(crudo[crudo["NUMERO DOCUMENTO"] != "B1"], D3, D3)
nota_suelta = sin_orig[sin_orig[dv.CLASE] == dv.NOTA_CREDITO]
igual(len(nota_suelta), 1, "sin el anulado en el df, la nota queda sola")
igual(float(nota_suelta["VENTA ITEM DDOCUMENTO"].sum()), -200.0,
      "y resta al menos su monto")
igual(float(nota_suelta["CANT PAX"].sum()), 0.0, "sin clientes")

print("\n── una nota por menos que el total ──")
parcial = crudo.copy()
parcial.loc[parcial["NUMERO DOCUMENTO"] == "B1", " TOTAL NC"] = 100.0
np_ = dv.preparar(parcial, D1, D3)
np_ = np_[np_[dv.CLASE] == dv.NOTA_CREDITO]
igual(float(np_["VENTA ITEM DDOCUMENTO"].sum()), -100.0,
      "resta la proporción de la nota")
igual(float(np_["CANT PAX"].abs().sum()), 0.0,
      "y no toca los clientes: la mesa vino igual")

print("\n── los KPIs del rail, con la misma definición ──")
k = dv.resumir(prep, (("Venta", "VENTA ITEM DDOCUMENTO", "sum"),
                      ("Pax", "CANT PAX", "sum_dedup")),
               col_ped="LLAVE LOCAL PEDIDO",
               col_item="LLAVE LOCAL DOCUMENTO ITEM")
igual(k.get("Venta"), 280.0, "venta del rail = venta de las vistas")
igual(k.get("Pax"), 6.0, "clientes del rail = los de las vistas")

print("\n── sin las columnas de la nota (el demo): sólo clasifica ──")
demo = pd.DataFrame({"Fec Reg Documento": [pd.Timestamp(D1)] * 2,
                     "Venta Item Ddocumento": [10.0, 5.0],
                     "Tipo Doc": ["Boleta", "CORTESIA"]})
pd_ = dv.preparar(demo)
igual(list(pd_[dv.CLASE]), [dv.VENTA, dv.CORTESIA],
      "resuelve los nombres sin importar mayúsculas")
igual(len(pd_), 2, "no inventa filas")


# ── El cableado ──────────────────────────────────────────────────────────
print("\n── nadie define la venta por su cuenta ──")
VISTAS = sorted((RAIZ / "graficos").glob("ventas*.py"))
ok(len(VISTAS) >= 4, "el barrido ve las vistas de Ventas",
   ", ".join(p.name for p in VISTAS))
for p in VISTAS:
    src = p.read_text(encoding="utf-8")
    ok('"CORTESIA"' not in src and '"ANULADO"' not in src,
       f"{p.name}: no detecta cortesías ni anulados a mano",
       "eso lo dice `definicion_venta` (CLASE VENTA)")
    ok('["pax"].max()' not in src,
       f"{p.name}: no cuenta clientes con `max()` suelto",
       "la nota de crédito tiene que restar: `definicion_venta.pax_por`")

_fuente_v = (RAIZ / "graficos/ventas.py").read_text(encoding="utf-8")
_arbol_v = ast.parse(_fuente_v)
_fn = next(n for n in ast.walk(_arbol_v) if isinstance(n, ast.FunctionDef)
           and n.name == "renderizar_graficos_ventas")
_asig = {n.targets[0].id: ast.unparse(n.value) for n in ast.walk(_fn)
         if isinstance(n, ast.Assign) and len(n.targets) == 1
         and isinstance(n.targets[0], ast.Name)}
igual(_asig.get("d"), "dv.solo_venta(d_todo)",
      "ventas.py: `d` —lo que suman las vistas— es sólo venta")
igual(_asig.get("d_todo"), "unico_por_item(d_pagos)",
      "ventas.py: `d_todo` es un ítem una vez, con todas las clases")
_filtrar = next(n for n in ast.walk(_fn) if isinstance(n, ast.FunctionDef)
                and n.name == "_filtrar_items")
_ret = next(n for n in ast.walk(_filtrar) if isinstance(n, ast.Return))
ok(ast.unparse(_ret.value).startswith("dv.solo_venta("),
   "ventas.py: lo que Año Pasado y Mapa por hora cargan aparte pasa por la "
   "definición", ast.unparse(_ret.value))
_llamadas = [n for n in ast.walk(_fn) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name)
             and n.func.id == "_ventas_resumen"]
ok([ast.unparse(c.args[0]) for c in _llamadas] == ["d_todo"],
   "ventas.py: el Resumen recibe todas las clases (muestra cortesías, "
   "anulados y el cuadre)")
_col_costo = next((n for n in ast.walk(_fn) if isinstance(n, ast.Assign)
                   and getattr(n.targets[0], "id", None) == "col_costo"), None)
_txt_costo = ast.unparse(_col_costo.value) if _col_costo is not None else ""
ok(0 <= _txt_costo.find("'Costo Venta'") < _txt_costo.find("'Precio Costo'"),
   "ventas.py: el costo que suman las vistas es el de la línea "
   "(«Costo Venta» antes que el unitario)", _txt_costo)

print("\n── data.py aplica la definición al cargar ──")
_fuente_d = (RAIZ / "data.py").read_text(encoding="utf-8")
_arbol_d = ast.parse(_fuente_d)
_prep = next((n for n in ast.walk(_arbol_d) if isinstance(n, ast.Assign)
              and any(getattr(t, "id", None) == "_PREPARAR"
                      for t in n.targets)), None)
ok(_prep is not None
   and "'ventas.parquet': definicion_venta" in ast.unparse(_prep.value),
   "_PREPARAR manda ventas.parquet a definicion_venta")
for nombre in ("_cargar_rango_cacheable", "_resumen_kpis_cacheable"):
    llamadas = [n for n in ast.walk(_arbol_d) if isinstance(n, ast.Call)
                and getattr(n.func, "id", None) == nombre]
    ok(llamadas and all(any(kw.arg == "definicion"
                            and "_version_preparar" in ast.unparse(kw.value)
                            for kw in c.keywords) for c in llamadas),
       f"toda llamada a {nombre}() pasa la versión de la definición",
       "sin ella, un cambio de definición sigue sirviendo el df viejo de "
       "la caché de disco")

print("\n── el asistente sabe qué es venta ──")
from asistente_datos import nota_de_grano  # noqa: E402

_nota = nota_de_grano(prep)
ok(_nota is not None and dv.CLASE in _nota and dv.NOTA_CREDITO in _nota,
   "la nota de grano dice qué filas son venta")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (definición de venta)")
