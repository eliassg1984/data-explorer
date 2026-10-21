"""test_consistencia_maestro.py — Costos › «Consistencia de datos» (reglas #686 y #689).

Sin secrets, sin red y sin navegador:

1. Cada CONTROL de `consistencia_maestro.py` sobre parquets de mentira con
   los nombres reales de las columnas, con el caso que tiene que marcar y el
   que se le parece y NO: el stock parado que sólo se contó (el conteo no es
   uso), el área donde el producto sí se mueve, el cambio de factor que la
   receta sí acompañó, el artículo NUEVO de la auditoría (ANTES vacío), el
   redondeo del precio de costo, Venta Interna al costo, los insumos de
   operación, el código de 10 dígitos del cierre, la factura de servicios y
   la anulada con una nota, el pedido que una corrida sí tomó. Montos y
   nombres inventados: el repo es público.

2. El RESUMEN: verde sin casos, rojo o ámbar según el control, y un control
   que revienta no tapa a los demás.

3. El CABLEADO, con `ast`: la vista está en el rail de Costos, dibuja lo que
   devuelve el módulo y la caché lleva su versión.

La cifra sobre R2 la da `herramientas/consistencia_maestro.py`.

Se ejecuta solo:  python test_consistencia_maestro.py
"""

import ast
import sys
from pathlib import Path

import pandas as pd

import consistencia_maestro as cm
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


HOY = pd.Timestamp("2026-10-20")


def d(dias, hora=12):
    """`dias` días antes de HOY, a la `hora`."""
    return HOY - pd.Timedelta(days=dias) + pd.Timedelta(hours=hora)


# ── el maestro de stock ───────────────────────────────────────────────────
# Códigos de 7 dígitos y áreas de 3, como el kardex.
def _inv(area, nom_area, cod, nombre, stock=0.0, precio=1.0, tipo="MERCADERIA",
         activo="ACTIVO", fam="ALIMENTOS", uk="KILOS", us="KILOS", factor=1.0,
         compartido="COMPARTIDO"):
    return {"CODIGO AREA": area, "NOMBRE AREA": nom_area, "PRODUCTO ACTIVO": activo,
            "COMPARTIDO": compartido, "AREA ACTIVA": "ACTIVA", "TIPO PRODUCTO": tipo,
            "NOMBRE FAMILIA": fam, "NOMBRE SUBFAMILIA": "", "CODIGO PRODUCTO": cod,
            "NOMBRE PRODUCTO": nombre, "UNIDAD KARDEX": uk, "UNIDAD SALIDA": us,
            "FACTOR": factor, "STOCK AL DIA": stock, "PRECIO PROMEDIO": precio,
            "VALORIZADO TOTAL": stock * precio}


INV = pd.DataFrame([
    _inv("001", "COCINA", "0000001", "Vino de guarda", stock=5, precio=20),
    _inv("001", "COCINA", "0000002", "Palta", stock=-3, precio=8, us="GRAMOS", factor=1000),
    _inv("017", "BAJAS DE ALMACEN", "0000002", "Palta", us="GRAMOS", factor=1000),
    _inv("001", "COCINA", "0000003", "Sal ahumada", stock=2, precio=0),
    _inv("001", "COCINA", "0000004", "Producto viejo"),
    _inv("011", "BARRA", "0000004", "Producto viejo"),
    _inv("009", "GASTOS", "0000005", "Mantenimiento varios", stock=10, precio=50,
         tipo="SERVICIO", fam="GASTOS"),
    _inv("001", "COCINA", "0000006", "Leña de olivo", us="GRAMOS", factor=1),
    _inv("001", "COCINA", "0000007", "Ají viejo", activo="NO ACTIVO"),
    _inv("001", "COCINA", "0000008", "Entraña porcionada", stock=0),
    _inv("001", "COCINA", "0000009", "Hueso de pollo"),
    _inv("001", "COCINA", "0000010", "Papel toalla", fam="COSTOS PRODUCCION"),
    _inv("001", "COCINA", "0000011", "Hielo en cubos", tipo="SERVICIO"),
    _inv("001", "COCINA", "0000012", "Azúcar Rubia"),
    _inv("001", "COCINA", "0000013", "AZUCAR  RUBIA."),
    _inv("001", "COCINA", "0000014", "Aceite", stock=1, precio=10),
])
INV["_activo"] = ((INV["PRODUCTO ACTIVO"] == "ACTIVO")
                  & (INV["TIPO PRODUCTO"] == "MERCADERIA"))


def _k(dias, area, cod, tipo, ing=0.0, sal=0.0, val=0.0):
    return {"FECHA HORA": d(dias), "CODIGO AREA": area, "CODIGO PRODUCTO": cod,
            "COD TIPO": tipo, "CANT INGRESO": ing, "CANT SALIDA": sal,
            "VALOR SALIDA": val}


KDX = pd.DataFrame([
    _k(200, "001", "0000001", "95", sal=1, val=20),   # vino: último uso hace 200 d
    _k(10, "001", "0000001", "93", ing=1),             # … y un conteo: no es uso
    _k(5, "001", "0000002", "99", ing=10),             # palta: entra en Cocina
    _k(3, "001", "0000002", "95", sal=13, val=104),
    _k(4, "001", "0000003", "95", sal=1),              # sal: se mueve
    _k(20, "002", "0000008", "95", sal=5, val=150),    # entraña: se descarga en 002…
    _k(100, "001", "0000008", "99", ing=5),            # … y entra sólo en 001
    _k(30, "001", "0000014", "99", ing=1),
    _k(70, "001", "0000003", "01", ing=1),             # sal: compra ANTES del conteo
])                                                     # anterior: no explica el sobrante

# ── recetas y carta ──────────────────────────────────────────────────────
def _rv(plato, nombre, cod_ins, ins, activo_ins="ACTIV", area="COCINA",
        modif=d(300), act="ACTIV"):
    return {"COD PLATO": plato, "NOMB PLATO": nombre, "ITEM VENTA ACTIVO": act,
            "RV ACTIV": "RV ACT", "COD INS": cod_ins, "INS RV": ins,
            "INS ACTIVO": activo_ins, "SUBALM INS": area, "FECH MODIF": modif,
            "USUARIO REG": "U"}


RV = pd.DataFrame([
    _rv("V1", "Ensalada", "0000002", "Palta"),
    _rv("V1", "Ensalada", "0000007", "Ají viejo", activo_ins="INACTIV"),
    _rv("V1", "Ensalada", "0000003", "Sal ahumada", area="BARRA"),
    _rv("V2", "Parrilla", "0000006", "Leña de olivo", modif=d(10)),
    _rv("V9", "Plato fuera de carta", "0000007", "Ají viejo", activo_ins="INACTIV",
        act="INACTIV"),
])


def _rb(cod, prod, nombre, act="RB.ACTIV", art="ART.ACT", ins="0000002",
        ins_act="INS.ACT"):
    return {"COD RB": cod, "COD PROD RB": prod, "RB NOMBRE": nombre, "RB ACT": act,
            "RB ART ACT": art, "RB AREA PROD": "COCINA", "COD INS RB": ins,
            "INSUMO": "x", "INS ACTIVO": ins_act, "FECH REG": d(400),
            "USUARIO REG": "U", "RB COSTO": 5.0}


RB = pd.DataFrame([
    _rb("RB1", "0000020", "Guacamole quieto"),
    _rb("RB2", "0000021", "Fondo de baja", art="ART.INAC"),
    _rb("RB3", "0000008", "Entraña limpia", ins="0000007", ins_act="INS.INAC"),
])


def _cc(cod, nombre, tipo="RECETA", costo=10.0, neto=50.0, ultima=d(2),
        grupo="Alimentos", act="ACTIV"):
    return {"COD PLATO": cod, "ITEM VENT": nombre, "ITEM VENT ACT": act,
            "TIPO DESC": tipo, "COSTO SALON": costo, "P.NET SALON": neto,
            "ULTIMA VENT": ultima, "GRUPO": grupo, "USUARIO REG": "U"}


CC = pd.DataFrame([
    _cc("V1", "Ensalada"),
    _cc("V3", "Bourbon sour", costo=40, neto=50),                 # 80 %
    _cc("V4", "Menú de evento", tipo="SIN ENLACE", costo=None),
    _cc("V5", "Shot que ya no sale", ultima=d(200)),
    _cc("V6", "Limoncello", costo=56, neto=50, grupo="Venta Interna"),
    _cc("V7", "Cortesía de carta", costo=1, neto=0.01),          # precio de S/ 0,01
    _cc("V8", "Propina", tipo="NO APLICA", ultima=None),
])


def _ven(cod, nombre, dia, cant=1.0, neto=50.0, costo=10.0, clase=dv.VENTA,
         combo=0, mesero="", precio=50.0):
    return {"COD ITEM VENTA DDOCUMENTO": cod, "NOMB ITEM VENTA": nombre,
            "FEC REG DOCUMENTO": d(dia), "CANTIDAD ITEM DDOCUMENTO": cant,
            "NETO TOTAL ITEM DDOCUMENTO": neto, "PRECIO COSTO": costo,
            "CLASE VENTA": clase, "ES COMBO": combo, "NOMBRE MESERO": mesero,
            "PRECIO VENTA ITEM DDOCUMENTO": precio}


_COMBO_CONOCIDO = sorted(dv.COMBOS)[0]
VEN = pd.DataFrame([
    _ven("V1", "Ensalada", 3, neto=900),
    _ven("V4", "Menú de evento", 5, cant=10, neto=2000, costo=0),
    _ven("9999999", "Combo nuevo", 6, combo=1),
    _ven(_COMBO_CONOCIDO, "Combo conocido", 6, combo=1),
    # Un mesero que da 50 de cortesía casi todos los días… y un día 600.
    *[_ven("V1", "Ensalada", 10 + i, clase=dv.CORTESIA, mesero="Mesero A", precio=50)
      for i in range(10)],
    _ven("V1", "Ensalada", 2, cant=12, clase=dv.CORTESIA, mesero="Mesero A", precio=50),
])

# ── auditoría del POS ─────────────────────────────────────────────────────
def _aud(corr, dias, cod, campo, antes, despues, ua="", ud=""):
    return {"CORRELATIVO": corr, "FECHA": d(dias), "USUARIO": "USR1",
            "PANTALLA": "ARTICULOS Y PRECIOS", "CODIGO": cod, "CAMPO": campo,
            "ANTES": antes, "DESPUES": despues, "UNIDAD ANTES": ua, "UNIDAD DESPUES": ud}


AUD = pd.DataFrame([
    # La palta: factor y unidad en el mismo guardado → UN caso; la receta de
    # V1 es de hace 300 días → no acompañó el cambio.
    _aud(10, 100, "0000002", "Factor", "1", "1000"),
    _aud(10, 100, "0000002", "Unidad de Salida", "001", "002", "KILOS", "GRAMOS"),
    # La leña: cambio hace 20 días, la receta de V2 se editó hace 10 → acompañó.
    _aud(11, 20, "0000006", "Factor", "1000", "1"),
    # Un artículo NUEVO (ANTES vacío): no es un cambio.
    _aud(12, 15, "0000003", "Factor", "", "1000"),
    # Un factor que no cambió (32 → 32.0).
    _aud(13, 15, "0000003", "Factor", "32", "32.0"),
    # Precios de costo: uno a ×3 (raro) y un redondeo.
    _aud(14, 50, "0000009", "Precio de Costo", "10", "30"),
    _aud(15, 40, "0000009", "Precio de Costo", "15.2379400260756", "15.238"),
])

# ── compras ───────────────────────────────────────────────────────────────
def _cmp(dias, cod, nombre, cant, valor, fam="ALIMENTOS", um="KILOS", prov="P1"):
    return {"FECHA_EMISION_DOC": d(dias).normalize(), "COD_PRODUCTO": cod,
            "NOMBRE_PRODUCTO": nombre, "CANTIDAD_COMPRA": cant, "VALOR_COMPRA": valor,
            "FAMILIA": fam, "UNIDAD_DE_INGRESO": um, "NOMBRE_PROVEEDOR": prov}


CMP = pd.DataFrame([
    _cmp(30, "0000009", "Hueso de pollo", 20, 80),             # nadie lo usa
    _cmp(30, "0000010", "Papel toalla", 10, 50, fam="COSTOS PRODUCCION"),
    _cmp(30, "0000011", "Hielo en cubos", 10, 60),             # servicio en ALIMENTOS
    # La palta a 10 el kilo, y un día a 40: precio raro.
    *[_cmp(60 + i, "0000002", "Palta", 10, 100) for i in range(5)],
    _cmp(10, "0000002", "Palta", 10, 400),
    _cmp(12, "0000001", "Vino de guarda", 4.5, 90, fam="VINOS", um="UND"),
])

# ── porcionamientos ───────────────────────────────────────────────────────
def _porc(cod_porc, dias, cant, merma):
    return {"COD PORC": cod_porc, "COD PROD INIC": "0000030", "PROD INICIAL": "Bife",
            "FEC REGIST": d(dias), "CANT A PORCIONAR": cant, "CANT MERMA": merma,
            "CANT RESULT": 1.0, "PREC PROM PROD FIN": 100.0, "SUB ALMACEN": "PRODUCCION",
            "USUARIO REG": "USR2"}


PORC = pd.DataFrame([
    *[_porc(f"P{i}", 100 + 10 * i, 10, 2 + (i % 3) * 0.1) for i in range(10)],  # ~20 %
    _porc("PNEG", 20, 10, -0.5),     # merma negativa: imposible
    _porc("PALTA", 25, 10, 6),       # 60 %: fuera de lo normal del producto
    _porc("PBIEN", 30, 10, 2.1),     # normal
])

# ── notas de salida ───────────────────────────────────────────────────────
def _sal(cod, registro, area="COCINA", valor=10.0, estado="PROCESADO"):
    return {"COD SALIDA": cod, "FECHA REGISTRO": registro, "FECHA PROCESADO": registro,
            "AREA": area, "VALOR NETO": valor, "MOTIVO": "Consumo directo",
            "NOMBRE ESTADO SALIDA": estado}


SAL = pd.DataFrame([
    *[_sal(f"N{i}", d(20) + pd.Timedelta(minutes=2 * i)) for i in range(16)],   # lote
    *[_sal(f"M{i}", d(20) + pd.Timedelta(hours=3, minutes=30 * i)) for i in range(16)],
    _sal("A1", d(20) + pd.Timedelta(minutes=1), estado="ANULADO"),
])

# ── pedidos y corridas del descargo de ventas ─────────────────────────────
def _ped(cod, apertura, monto=100.0, anulado=0.0, usuario=""):
    return {"CODIGO PEDIDO": cod, "FECHA APERTURA": apertura,
            "DIA CONTABLE": apertura.normalize(), "ESTADO PEDIDO": "FACTURADO",
            "PLATOS": 2.0, "MONTO PEDIDO": monto, "MONTO ANULADO": anulado,
            "USUARIO ANULACION": usuario}


PED = pd.DataFrame([
    _ped("A", d(40, 13)),                       # lo tomó la corrida 1
    _ped("B", d(31, 21)),                       # en el hueco entre corridas
    _ped("C", d(29, 13)),                       # lo tomó la corrida 2
    *[_ped(f"U{i}", d(10 + i), anulado=20, usuario="CAJ1") for i in range(10)],
    _ped("UX", d(3), anulado=500, usuario="CAJ1"),
])
DSC = pd.DataFrame([
    {"VENTAS DESDE": d(45, 0), "VENTAS HASTA": d(31, 8)},
    {"VENTAS DESDE": d(30, 0), "VENTAS HASTA": d(1, 8)},
])

# ── cierres de inventario: códigos de 10 dígitos ──────────────────────────
def _ajs(dias, cod, area, ajuste, stock, prod="Sal ahumada"):
    return {"FECHA APERTURA INVENTARIO": d(dias), "CODIGO PRODUCTO": "000" + cod,
            "CODIGO AREA": "0000000" + area, "AREA": "COCINA", "PRODUCTO": prod,
            "AJUSTE": ajuste, "STOCK AL CIERRE": stock, "UNIDAD MEDIDA": "KILOS",
            "AJUSTE VALORIZADO": ajuste * 3}


AJS = pd.DataFrame([
    _ajs(60, "0000003", "001", 0, 0),
    _ajs(10, "0000003", "001", 2, 0),           # sobró sin entrar
    _ajs(60, "0000014", "001", 0, 0, prod="Aceite"),
    _ajs(10, "0000014", "001", 1, 0, prod="Aceite"),   # entró hace 30 d: explicado
    _ajs(10, "0000002", "001", 1, -3, prod="Palta"),   # sistema negativo: otra cosa
])

# ── el cruce con SUNAT ────────────────────────────────────────────────────
SUNAT = pd.DataFrame([
    {"documento": "F001-1", "proveedor": "Carnes SAC", "estado": "Solo SUNAT",
     "fecha_emision": d(30), "total_sunat": 1000.0, "tipo": "Mercadería"},
    {"documento": "F001-2", "proveedor": "Alquileres SAC", "estado": "Solo SUNAT",
     "fecha_emision": d(30), "total_sunat": 9000.0, "tipo": "Servicios"},
    {"documento": "F001-3", "proveedor": "Verduras SAC", "estado": "Solo SUNAT",
     "fecha_emision": d(40), "total_sunat": 200.0, "tipo": "Mercadería"},
    {"documento": "F001-4", "proveedor": "Verduras SAC", "estado": "Solo SUNAT",
     "fecha_emision": d(38), "total_sunat": -200.0, "tipo": "Mercadería"},
    {"documento": "F001-5", "proveedor": "Carnes SAC", "estado": "Solo SUNAT",
     "fecha_emision": d(5), "total_sunat": 300.0, "tipo": "Mercadería"},
    {"documento": "F001-6", "proveedor": "Carnes SAC", "estado": "Coincide",
     "fecha_emision": d(30), "total_sunat": 300.0, "tipo": "Mercadería"},
])

T = {"inv": INV, "kdx": KDX, "rv": RV, "rb": RB, "cc": CC, "aud": AUD, "ven": VEN,
     "cmp": CMP, "porc": PORC, "sal": SAL, "ped": PED, "dsc": DSC, "ajs": AJS,
     "sunat": SUNAT}
RES = cm.calcular(dict(T), HOY)


def casos(cid):
    r = RES[cid]
    ok(isinstance(r, pd.DataFrame), f"{cid} · se calcula",
       f"{type(r).__name__}: {r}" if not isinstance(r, pd.DataFrame) else "")
    if not isinstance(r, pd.DataFrame):
        return pd.DataFrame(columns=list(cm.CASOS))
    ok(list(r.columns) == list(cm.CASOS), f"{cid} · devuelve las columnas de CASOS",
       f"columnas: {list(r.columns)}")
    return r


def codigos(cid):
    return set(casos(cid)["codigo"])


print("── stock ──")
ok(codigos("s1") == {"0000001"},
   "s1 · el vino con 200 días sin uso está parado aunque lo hayan contado hace 10")
ok(set(casos("s2")["codigo"]) == {"0000002"}, "s2 · la palta en negativo")
ok(codigos("s3") == {"0000003"}, "s3 · la sal con stock y precio cero")
ok("0000004" in codigos("s4") and "0000001" not in codigos("s4"),
   "s4 · el producto viejo sin vida; el vino con stock no")
ok(codigos("s5") == {"0000005"}, "s5 · el servicio con existencia")
ok(codigos("s6") == {"0000006"},
   "s6 · la leña KILOS → GRAMOS con factor 1; la palta con 1000 no")
s7 = casos("s7")
ok(list(zip(s7["codigo"], s7["area"])) == [("0000002", "BAJAS DE ALMACEN")],
   "s7 · la palta sobra en Bajas, no en Cocina donde se mueve",
   f"casos: {list(zip(s7['codigo'], s7['area']))}")

print("── recetas ──")
ok(codigos("r1") == {"0000020"},
   "r1 · el guacamole no se mueve; la entraña, que sí, no sale")
r2 = casos("r2")
ok(set(r2["dato"]) >= {"insumo inactivo", "no habilitado en Barra",
                       "insumo inactivo (receta base)"},
   "r2 · insumo inactivo, no habilitado en el área y la receta base",
   f"datos: {sorted(set(r2['dato']))}")
ok("V9" not in set(r2["codigo"]), "r2 · un plato inactivo no cuenta")
ok(r2.loc[r2["codigo"] == "V1", "soles"].iloc[0] == 900,
   "r2 · lo que está en juego es la venta del plato")
r3 = casos("r3")
ok(set(r3["codigo"]) == {"0000002"},
   "r3 · la palta (receta vieja) sí; la leña (receta editada después) no")
ok(r3["quien"].tolist() == ["USR1"], "r3 · dice quién cambió el factor")
ok(codigos("r4") == {"V3"},
   "r4 · el 80 % sí; Venta Interna al costo y el plato a S/ 0,01 no")
ok(codigos("r5") == {"0000021"}, "r5 · la receta base de un artículo de baja")

print("── carta y ventas ──")
ok(codigos("c1") == {"V5"}, "c1 · el shot que no se vende; «no aplica» no cuenta")
c2 = casos("c2")
ok(set(c2["codigo"]) == {"V4"} and c2["soles"].iloc[0] == 2000,
   "c2 · el menú sin enlace que se vendió, con su venta")
c3 = casos("c3")
ok(list(zip(c3["codigo"], c3["soles"])) == [("0000008", 150)],
   "c3 · la entraña se descarga en un área donde nunca entra; la palta no")
ok(set(casos("c4")["codigo"]) == {"9999999"},
   "c4 · el combo nuevo sí, el de la lista no")

print("── compras ──")
ok(codigos("p1") == {"0000009", "0000001"},
   "p1 · el hueso de pollo y el vino (comprado, y sin uso en 180 días); el papel "
   "toalla (operación) y la palta (se vende) no")
ok(codigos("p2") == {"0000011"}, "p2 · el hielo comprado como servicio")
p3 = casos("p3")
ok(len(p3) == 1 and p3["codigo"].iloc[0] == "0000012, 0000013",
   "p3 · «Azúcar Rubia» y «AZUCAR  RUBIA.» son el mismo producto")

print("── movimientos raros ──")
m1 = casos("m1")
ok(m1["codigo"].tolist().count("0000002") == 1,
   "m1 · factor y unidad del mismo guardado son UN caso")
ok("0000003" not in set(m1["codigo"]),
   "m1 · un artículo nuevo o un factor igual no es un cambio")
m2 = casos("m2")
ok(m2["dato"].tolist() == ["10.00 → 30.00"],
   "m2 · el precio a ×3 sí, el redondeo no", f"datos: {m2['dato'].tolist()}")
ok(codigos("m3") == {"PNEG", "PALTA"},
   "m3 · la merma negativa y la del 60 % sí; la normal no")
m4 = casos("m4")
ok(set(zip(m4["codigo"], m4["dato"])) == {("0000002", "×4.0"), ("0000001", "4.5 und")},
   "m4 · la palta a 4 veces y el vino con decimales en unidades",
   f"casos: {list(zip(m4['codigo'], m4['dato']))}")
ok(codigos("m5") == {"0000003"},
   "m5 · la sal sobró sin entrar; el aceite tuvo entrada y la palta estaba en negativo")
m6 = casos("m6")
ok(m6["codigo"].tolist() == ["F001-1"],
   "m6 · sólo la mercadería sin ingresar de hace más de 15 días; ni servicios, "
   "ni la anulada con nota", f"casos: {m6['codigo'].tolist()}")
m7 = casos("m7")
ok(len(m7) == 1 and m7["fecha"].iloc[0] == d(31, 0).normalize(),
   "m7 · el pedido del hueco entre corridas, en su día")
m8 = casos("m8")
ok(len(m8) == 1 and m8["dato"].iloc[0].startswith("16 en"),
   "m8 · las 16 notas seguidas son un lote; las de cada media hora no")
m9 = casos("m9")
ok(set(zip(m9["quien"], m9["nombre"].str.split(" · ").str[1]))
   == {("CAJ1", "anulado"), ("Mesero A", "cortesía")},
   "m9 · el día que el cajero anuló 25 veces lo suyo y el del mesero",
   f"casos: {list(zip(m9['quien'], m9['nombre']))}")

print("── resumen ──")
res = cm.resumen(RES)
est = dict(zip(res["id"], res["estado"]))
ok(len(res) == len(cm.CONTROLES), "resumen · una fila por control")
ok(est["s2"] == cm.ROJO and est["s1"] == cm.AMBAR,
   "resumen · rojo si el control es grave, ámbar si no")
_vacio = cm.calcular({**T, "aud": AUD.iloc[0:0]}, HOY, solo=("m2",))
ok(cm.estado(cm.POR_ID["m2"], _vacio["m2"]) == cm.VERDE, "resumen · verde sin casos")
_roto = cm.calcular({**T, "cc": CC.drop(columns="TIPO DESC")}, HOY, solo=("r4", "s1"))
ok(isinstance(_roto["r4"], Exception) and isinstance(_roto["s1"], pd.DataFrame),
   "resumen · un control que revienta no tapa a los demás")
ok(cm.resumen(_roto).set_index("id").loc["r4", "estado"] == cm.FALLO,
   "resumen · y sale como «no se pudo calcular»")
ok(dict(zip(res["id"], res["concentra"]))["s2"] == "COCINA 1",
   "resumen · dónde se concentran los casos")

print("── el registro ──")
ids = [c.id for c in cm.CONTROLES]
ok(len(ids) == len(set(ids)), "cada control tiene su id")
ok(all(c.dominio in dict(cm.DOMINIOS) for c in cm.CONTROLES),
   "cada control cae en un grupo de DOMINIOS")
ok(all(len(c.columnas) == 3 and c.mide and c.porque and c.regla and c.accion
       for c in cm.CONTROLES), "cada control tiene sus textos y sus tres rótulos")
ok(all(c.agrupar in (None, *cm.CASOS) for c in cm.CONTROLES),
   "«se concentra en» agrupa por una columna de CASOS")

print("── lo que recibe la pieza ──")
import json  # noqa: E402
from graficos.costos_consistencia import armar  # noqa: E402
_p = armar(RES, HOY)
ok(len(_p["controles"]) == len(cm.CONTROLES) and _p["hoy"] == "20/10/2026",
   "pieza · un control por CONTROLES y el corte escrito como fecha")
_ok_json = True
try:
    json.dumps(_p, allow_nan=False)
except ValueError:
    _ok_json = False
ok(_ok_json, "pieza · viaja como JSON: sin NaN (un NaN rompe el JSON del navegador)")
_s2 = next(x for x in _p["controles"] if x["id"] == "s2")
ok(_s2["estado"] == cm.ROJO and _s2["n"] == 1 and _s2["casos"][0][0] == "0000002",
   "pieza · el control lleva su estado y sus casos como filas")
_r2 = next(x for x in _p["controles"] if x["id"] == "r2")
_montos = [f[4] for f in _r2["casos"]]
ok(_montos[0] == 900 and all(m is None for m in _montos[1:] if m != 900),
   "pieza · los casos van de mayor a menor monto, los sin monto al final")
_roto_p = armar(_roto, HOY)
ok(next(x for x in _roto_p["controles"] if x["id"] == "r4")["error"] != "",
   "pieza · el control que reventó lleva su error, no casos")

print("── el cableado ──")
_costos = (RAIZ / "graficos" / "costos.py").read_text(encoding="utf-8")
ok("Consistencia de datos" in {n.value for n in ast.walk(ast.parse(_costos))
                                  if isinstance(n, ast.Constant)},
   "la vista está en el rail de Costos")
ok("costos_consistencia.renderizar()" in _costos, "y Costos la despacha")
_data = (RAIZ / "data.py").read_text(encoding="utf-8")
ok("cm.VERSION" in _data and "_consistencia_cacheable.clear()" in _data,
   "la caché lleva la versión de los controles y se vacía con un refresco")

print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for x in _fallos:
        print(f"   · {x}")
    sys.exit(1)
print("✅ Todo OK (consistencia del maestro)")
