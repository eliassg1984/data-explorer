"""test_tipo_compra.py — QUÉ SE COMPRÓ en cada comprobante (regla #640).

Tres cosas, sin secrets, sin red y sin navegador:

1. Las REGLAS sueltas: del Almacén al tipo (`tipo_de_linea`, con las
   mayúsculas y los acentos como vienen) y la razón social de una entidad
   financiera (`es_entidad_financiera`), con los falsos parecidos.

2. La CASCADA sobre un Almacén y un SIRE de mentira, pasando por el cruce
   de verdad de «Documentos SUNAT» (`_parquet_agrupado_por_documento` +
   `cruzar_con_parquet`): así se prueba también que las claves con que
   `tipo_compra` busca un documento son las que el cruce devuelve. Cada
   proveedor es un caso real: el banco que factura sin IGV, la
   inmobiliaria exonerada, el supermercado al 92 %, la ferretería que
   vende de todo, la nota de crédito exonerada, el RUC con un espacio al
   final en el Almacén. Montos inventados — el repo es público.

3. El CABLEADO, leído del código con `ast`: que la vista clasifique el
   cruce y que la tabla muestre la columna con su motivo.

La cifra sobre los datos de verdad (cuántos documentos quedan con tipo y
cuánto aciertan) está en `arquitectura.md` regla #640.

Se ejecuta solo:  python test_tipo_compra.py
"""

import ast
import logging
import sys
from pathlib import Path

import pandas as pd

# La consola de Windows (cp1252) revienta con UnicodeEncodeError en el
# PRIMER print y el gate falla sin decir por qué — igual que los otros tests.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
logging.getLogger("streamlit").setLevel(logging.ERROR)

import tipo_compra as tc  # noqa: E402
from graficos.compras import documentos_sunat as ds  # noqa: E402

RAIZ = Path(__file__).resolve().parent
_fallos = []


def ok(cond, nombre, detalle=""):
    print(f"{'OK  ' if cond else 'FALLA'}  {nombre}")
    if not cond:
        _fallos.append(f"{nombre}{(' — ' + detalle) if detalle else ''}")
        if detalle:
            print(f"         {detalle}")


def igual(got, exp, nombre):
    ok(got == exp, nombre, f"got={got!r} exp={exp!r}")


# ── 1. Las reglas sueltas ──────────────────────────────────────────────────
print("\n── del Almacén al tipo ──")
for fam, sub, exp in (
    ("ALIMENTOS", "CARNES", tc.ALIMENTOS),
    ("VINOS Y ESPUMANTES", "VINO TINTO", tc.ALIMENTOS),
    ("ENVASES Y EMBALAJES", "ENVASE EMB. SERVICIO", tc.OTROS_BIENES),
    ("COSTOS PRODUCCION", "Compra De Leña Y Carbón", tc.OTROS_BIENES),
    ("COSTOS PRODUCCION", "MENAJE COCINA", tc.OTROS_BIENES),   # las dos grafías
    ("COSTOS PRODUCCION", "Menaje Cocina", tc.OTROS_BIENES),
    ("GASTOS VENTAS", "Utiles De Oficina", tc.OTROS_BIENES),
    ("COSTOS PRODUCCION", "Alquiler Local", tc.SERVICIOS),
    ("COSTOS PRODUCCION", "Agua", tc.SERVICIOS),              # Servicio De Agua
    ("GASTOS ADMINISTRATIVOS", "Asesoria Contable", tc.SERVICIOS),
    ("GASTOS ADMINISTRATIVOS", "Consumo Para El Personal", tc.ALIMENTOS),
    ("ACTIVOS FIJOS", "Hornos", None),     # familia sin regla: NO es servicio
    (None, None, None),
):
    igual(tc.tipo_de_linea(fam, sub), exp, f"{fam} › {sub} → {exp}")

print("\n── razón social de una entidad financiera ──")
for nombre in ("BANCO DE CREDITO DEL PERU", "Diners Club Perú S.A.",
               "PACÍFICO COMPAÑÍA DE SEGUROS Y REASEGUROS",
               "PRODUCTOS Y MERCADOS AGRICOLAS DE HUARAL CAJA RURAL DE AHORRO "
               "Y CREDITO - CAJA RURAL PRYMERA", "Financiera QAPAQ",
               "COOPERATIVA DE AHORRO Y CREDITO ABACO",
               "COMPAÑIA PERUANA DE MEDIOS DE PAGO S.A.C"):
    ok(tc.es_entidad_financiera(nombre), f"financiera: {nombre[:40]}")
for nombre in ("COMPAÑIA FOOD RETAIL S.A.C.", "A & A ABACO S.A.C.",
               "CAJAMARCA FOODS S.A.C.", "SEGURIDAD Y VIGILANCIA SAC",
               "BANCOS DE MADERA EIRL", "INMOBILIARIA LAS PIEDRAS S.A.C.", ""):
    ok(not tc.es_entidad_financiera(nombre), f"NO financiera: {nombre!r}")


# ── 2. La cascada, por el cruce de verdad ──────────────────────────────────
# compras.parquet de mentira: (NUM_DOCUMENTO, RUC, proveedor, familia,
# subfamilia, valor). NUM_DOCUMENTO como lo guarda el Almacén:
# "F0" + serie + número a 9 dígitos.
_ALM = [
    ("F0F001000000001", "20000000001", "CARNES DEL SUR SAC", "ALIMENTOS", "CARNES", 1000.0),
    ("F0F001000000002", "20000000001", "CARNES DEL SUR SAC", "ALIMENTOS", "CARNES", 800.0),
    # el RUC con un espacio al final, como ~24 % de las filas reales
    ("F0E001000000003", "20000000002 ", "INMOBILIARIA X SAC", "COSTOS PRODUCCION", "Alquiler Local", 5000.0),
    ("F0B001000000001", "20000000003", "SUPERMERCADO SAC", "ALIMENTOS", "ABARROTES", 920.0),
    ("F0B001000000001", "20000000003", "SUPERMERCADO SAC", "COSTOS PRODUCCION", "Suministros De Limpieza", 80.0),
    ("F0F002000000001", "20000000004", "FERRETERIA Y BODEGA SAC", "ALIMENTOS", "ABARROTES", 850.0),
    ("F0F002000000001", "20000000004", "FERRETERIA Y BODEGA SAC", "COSTOS PRODUCCION", "Suministros Y Repuestos Varios", 150.0),
    # sólo en el Almacén: «Solo sistema»
    ("F0F003000000009", "20000000008", "ENVASES PERU SAC", "ENVASES Y EMBALAJES", "ENVASE EMB. PRODUCCION", 300.0),
    # familia sin regla: el documento no da tipo y el proveedor tampoco
    ("F0F004000000001", "20000000009", "HORNOS SAC", "ACTIVOS FIJOS", "Hornos", 9000.0),
]
d = pd.DataFrame(_ALM, columns=["NUM_DOCUMENTO", "INDICADOR TRIBUTARIO",
                                "NOMBRE_PROVEEDOR", "FAMILIA", "SUBFAMILIA",
                                "VALOR_COMPRA"])
d["TOTAL NETO"] = d.groupby("NUM_DOCUMENTO")["VALOR_COMPRA"].transform("sum")
d["TOTAL IGV"] = d["TOTAL NETO"] * 0.18
d["TOTAL DOCUMENTO"] = d["TOTAL NETO"] * 1.18
d["VALOR_BRUTO_COMPRA_MN"] = d["VALOR_COMPRA"] * 1.18
d["TIPO_MONEDA"], d["TIPO_CAMBIO"] = "01", 3.7
d["FECHA_EMISION_DOC"] = pd.Timestamp("2026-09-10")

# El SIRE: (car, documento, RUC, proveedor, tipo_cdp, base gravada, no gravado)
_SIRE = [
    ("c1", "F001-1", "20000000001", "CARNES DEL SUR SAC", "01", 1000.0, 0.0),
    ("c2", "F001-3", "20000000001", "CARNES DEL SUR SAC", "01", 600.0, 0.0),
    ("c3", "E001-7", "20000000002", "INMOBILIARIA X SAC", "01", 0.0, 5000.0),
    ("c4", "B001-1", "20000000003", "SUPERMERCADO SAC", "01", 1000.0, 0.0),
    ("c5", "B001-2", "20000000003", "SUPERMERCADO SAC", "01", 400.0, 0.0),
    ("c6", "F002-5", "20000000004", "FERRETERIA Y BODEGA SAC", "01", 300.0, 0.0),
    ("c7", "F002-6", "20000000004", "FERRETERIA Y BODEGA SAC", "01", 0.0, 120.0),
    ("c8", "F100-9", "20100047218", "BANCO DE CREDITO DEL PERU", "01", 0.0, 35.0),
    ("c9", "A001-4", "20000000005", "PROCESADORA XYZ SAC", "30", 50.0, 0.0),
    ("c10", "F005-1", "20000000006", "NUEVO PROVEEDOR SAC", "01", 700.0, 0.0),
    ("c11", "F006-1", "20000000007", "VERDURAS DON PEPE", "01", 0.0, 260.0),
    ("c12", "FC01-2", "20000000007", "VERDURAS DON PEPE", "07", 0.0, -40.0),
    ("c13", "F004-1", "20000000009", "HORNOS SAC", "01", 9000.0, 0.0),
]
sire = pd.DataFrame(_SIRE, columns=["car", "documento", "ruc_proveedor",
                                    "proveedor", "tipo_cdp", "base_imponible",
                                    "no_gravado"])
sire["igv"] = sire["base_imponible"] * 0.18
sire["total"] = sire["base_imponible"] + sire["igv"] + sire["no_gravado"]
sire["tipo_nombre"] = sire["tipo_cdp"].map(
    {"01": "Factura", "07": "Nota de Crédito",
     "30": "Documentos emitidos por Adquiriente"})
sire["fecha_emision"] = pd.Timestamp("2026-09-10")
sire["situacion"] = "Registrado"

ini, fin = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30")
cruce = ds.cruzar_con_parquet(
    sire, ds._parquet_agrupado_por_documento(d, "FECHA_EMISION_DOC", ini, fin))
out = tc.clasificar(cruce, sire, tc.tablas_almacen(d))

print("\n── el cruce de mentira es el que se quiso armar ──")
est = dict(zip(out["car"], out["estado"]))
for car in ("c1", "c4", "c13"):
    ok(est.get(car) in ("Coincide", "Diferencia"), f"{car} está en los dos lados",
       f"estado={est.get(car)!r}")
ok(est.get("c3") == "Solo SUNAT", "la inmobiliaria exonerada no está cargada")
ok(((out["estado"] == "Solo sistema")
    & (out["documento_sistema"] == "F0F003000000009")).any(),
   "el documento de envases está sólo en el Almacén")

print("\n── la cascada ──")
_t = {c: (t, p) for c, t, p in zip(out["car"], out["tipo"], out["tipo_por"])}


def caso(car, tipo, frase, nombre):
    t, por = _t.get(car, (None, ""))
    ok(t == tipo and frase in por, nombre,
       f"tipo={t!r} por={por!r} — se esperaba {tipo!r} con «{frase}»")


caso("c1", tc.ALIMENTOS, "Cargado en el Almacén como CARNES.",
     "documento cargado: su familia, sin porcentaje si es puro")
caso("c2", tc.ALIMENTOS, "100 % Alimentos, sobre todo CARNES",
     "sin cargar: lo que se le compra al proveedor")
caso("c3", tc.SERVICIOS, "Alquiler Local",
     "el proveedor le GANA a la exoneración (inmobiliaria sin IGV), "
     "y con el RUC del Almacén con un espacio al final")
caso("c4", tc.ALIMENTOS, "el 92 % del documento es Alimentos",
     "documento mixto: dice qué parte es del tipo")
caso("c5", tc.ALIMENTOS, "92 % Alimentos",
     "supermercado al 92 %: pasa el umbral de 90 % y lo dice")
caso("c6", "", "no tiene un tipo claro",
     "proveedor al 85 % y factura con IGV: sin tipo")
caso("c7", tc.ALIMENTOS, "Toda la factura va sin IGV",
     "proveedor al 85 % y factura exonerada: la exoneración decide")
caso("c8", tc.FINANCIERO, "razón social",
     "el banco factura sin IGV y NO es comida")
caso("c9", tc.FINANCIERO, "Documentos emitidos por Adquiriente",
     "el tipo de comprobante 30 es financiero, aunque el nombre no lo diga")
caso("c10", "", "no tiene un tipo claro", "proveedor nuevo con IGV: sin tipo")
caso("c11", tc.ALIMENTOS, "Toda la factura va sin IGV",
     "proveedor nuevo exonerado: Alimentos")
caso("c12", tc.ALIMENTOS, "Toda la factura va sin IGV",
     "una NOTA exonerada (montos negativos) también")
caso("c13", "", "no tiene un tipo claro",
     "familia sin regla: ni el documento ni el proveedor dicen «Servicios»")
_ss = out[(out["estado"] == "Solo sistema")
          & (out["documento_sistema"] == "F0F003000000009")]
ok(len(_ss) == 1 and _ss["tipo"].iloc[0] == tc.OTROS_BIENES
   and "ENVASE EMB. PRODUCCION" in _ss["tipo_por"].iloc[0],
   "«Solo sistema»: el tipo de su documento en el Almacén",
   f"{_ss[['tipo', 'tipo_por']].to_dict('records')}")
ok(set(out["tipo"]) <= set(tc.TIPOS) | {""}, "sólo salen los cuatro tipos o vacío")
ok(len(out) == len(cruce) and list(out.columns[:len(cruce.columns)])
   == list(cruce.columns), "clasificar sólo AGREGA dos columnas al cruce")

print("\n── sin datos ──")
ok(tc.clasificar(cruce.iloc[0:0], sire, tc.tablas_almacen(d)).empty,
   "un cruce vacío sale vacío")
_vacias = tc.tablas_almacen(pd.DataFrame({"FAMILIA": ["ALIMENTOS"]}))
ok(_vacias == {"proveedores": {}, "documentos": {}},
   "un Almacén sin las columnas (modo demo) no revienta: tablas vacías")
_sin_alm = tc.clasificar(cruce, sire, _vacias)
ok(dict(zip(_sin_alm["car"], _sin_alm["tipo"])).get("c3") == tc.ALIMENTOS,
   "sin Almacén queda lo que dice SUNAT: la inmobiliaria exonerada sale "
   "Alimentos (por eso el proveedor va antes)")


# ── 3. El cableado ─────────────────────────────────────────────────────────
print("\n── el cableado en «Documentos SUNAT» ──")
_src = (RAIZ / "graficos" / "compras" / "documentos_sunat.py").read_text(
    encoding="utf-8")
_arbol = ast.parse(_src)
_funcs = {n.name: n for n in ast.walk(_arbol) if isinstance(n, ast.FunctionDef)}


def _llama(func, attr):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == attr and ast.unparse(n.func.value) == "tipo_compra"
               for n in ast.walk(_funcs.get(func, ast.Module(body=[]))))


ok(_llama("renderizar_documentos_sunat", "clasificar"),
   "la vista clasifica el cruce (tipo_compra.clasificar)")
ok(_llama("_tablas_tipo", "tablas_almacen")
   and "tipo_compra.VERSION" in ast.unparse(_funcs["renderizar_documentos_sunat"]),
   "la tabla del Almacén se cachea con la versión de las reglas",
   "sin VERSION en la clave, cambiar una regla sirve la tabla vieja una hora")
_tabla = ast.unparse(_funcs.get("_tabla_documentos", ast.Module(body=[])))
ok("'Tipo'" in _tabla and "tooltipField='_tipo_por'" in _tabla,
   "la tabla muestra «Tipo» con su motivo de tooltip")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (tipo de compra)")
