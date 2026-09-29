"""test_consumo_recetas.py — el CONSUMO SEGÚN RECETAS (regla #558).

Dos cosas, las dos sin secrets, sin red y sin navegador:

1. Las CUENTAS de `consumo_recetas.py` sobre cuatro parquets de mentira con
   los nombres de columna REALES del Sheet, pasados por las mismas `sql_*`
   que usa la app. Cada caso es uno que ya apareció en los datos de verdad
   (los montos son inventados: el repo es público):
     · un insumo directo en la receta del plato, en mililitros → litros;
     · una salsa (receta base) con otra receta base adentro: la crema a un
       nivel y el hueso a dos, con «en la receta: …» sólo donde hace falta;
     · el pulpo: un corte que sale de un porcionamiento, con su rendimiento
       repartido POR PESO entre los cortes y la merma adentro — y el mismo
       corte con una receta, que NO se usa (el rendimiento real manda);
     · un corte sin porcionamientos en los 90 días: los 10 más cercanos;
     · el chorizo de Venta Interna; los turnos (el postre de la 1 de la
       mañana es de la cena); el día de la semana; un ciclo entre recetas;
       un código sin factor y uno que no está en el maestro.
   Y la conservación: por las recetas base, con precios coherentes, el
   costo de las hojas es el del primer nivel.

2. El CABLEADO, con `ast`: que la lista de grupos que no son servicio sea la
   misma que la de Ventas › Por hora.

3. LA VISTA (regla #560), sobre el mismo resultado: lo comprado del rango
   que viaja con la página (sólo alimentos y bebidas sin chip; con chip,
   el chip), lo comprado que ninguna venta usó con su nombre, y la fecha de
   los platos cuya receta se editó dentro del rango.

La cifra contra los parquets de verdad no vive acá (necesita R2): la da
`herramientas/verificar_consumo.py`.

Se ejecuta solo:  python test_consumo_recetas.py
"""

import ast
import datetime as dt
import sys
from pathlib import Path

import duckdb
import pandas as pd

import consumo_recetas as cr

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


def igual(got, exp, nombre, tol=1e-6):
    cond = got is not None and abs(float(got) - float(exp)) <= tol
    ok(cond, nombre, f"got={got!r} exp={exp!r}")


T = pd.Timestamp

# ── Los parquets de mentira, con las columnas del Sheet ───────────────────
MAESTRO = pd.DataFrame([
    # cod, nombre, unidad kardex, factor, precio, familia, subfamilia
    ("LEC", "Lechuga", "KILOS", 1000.0, 10.0, "ALIMENTOS", "VERDURAS"),
    ("SAL", "(Rs) Salsa pimienta", "KILOS", 1000.0, 10.0, "ALIMENTOS", "RB"),  # = 0,3 × 20 + 0,5 × 8
    ("FON", "(Rs) Fondo oscuro", "LITROS", 1000.0, 8.0, "ALIMENTOS", "RB"),
    ("CRE", "Crema de leche", "LITROS", 1000.0, 20.0, "ALIMENTOS", "LACTEOS"),
    ("HUE", "Hueso de res", "KILOS", 1000.0, 4.0, "ALIMENTOS", "CARNES"),
    ("PC", "(P) Pulpo cocido 120gr", "UND", 1.0, 30.0, "ALIMENTOS", "PORC"),
    ("RET", "(P) Retazos de pulpo", "KILOS", 1000.0, 50.0, "ALIMENTOS", "PORC"),
    ("PE", "Pulpo entero", "KILOS", 1000.0, 60.0, "ALIMENTOS", "MARISCOS"),
    ("PQ", "(P) Pulpo 70gr", "UND", 1.0, 20.0, "ALIMENTOS", "PORC"),
    ("XX", "Insumo de la receta vieja del corte", "KILOS", 1000.0, 1.0, "ALIMENTOS", "X"),
    ("CHO", "(Rs) Chorizo de pato", "UND", 1.0, 5.0, "ALIMENTOS", "RB"),
    ("MAG", "Magret de pato", "KILOS", 1000.0, 40.0, "ALIMENTOS", "AVES"),
    ("CA", "(Rs) Ciclo A", "KILOS", 1000.0, 1.0, "ALIMENTOS", "RB"),
    ("CB", "(Rs) Ciclo B", "KILOS", 1000.0, 1.0, "ALIMENTOS", "RB"),
    ("SLT", "Sal", "KILOS", 1000.0, 2.0, "ALIMENTOS", "ABARROTES"),
    ("SF", "Sin factor", "KILOS", None, 3.0, "ALIMENTOS", "X"),
    ("PR", "(Rs) Pulpo cocido 120gr (código viejo)", "UND", 1.0, 31.0, "ALIMENTOS", "RB"),
    ("CX", "(P) Asado de tira 400gr", "UND", 1.0, 16.0, "ALIMENTOS", "PORC"),
    ("EX", "Asado de tira x Kg", "KILOS", 1000.0, 32.0, "ALIMENTOS", "CARNES"),
], columns=["CODIGO PRODUCTO", "NOMBRE PRODUCTO", "UNIDAD KARDEX", "FACTOR",
            "PRECIO PROMEDIO", "NOMBRE FAMILIA", "NOMBRE SUBFAMILIA"])
# El inventario trae una fila por área y producto: el maestro las junta.
MAESTRO = pd.concat([MAESTRO, MAESTRO.iloc[[0]]], ignore_index=True)

RECETAS = pd.DataFrame([
    # prod, ins, cant (unidad de salida del insumo), factor del insumo, unidad, activa
    ("SAL", "CRE", 300.0, 1000.0, "MILILITROS", "RB.ACTIV"),   # 0,3 L de crema por kg de salsa
    ("SAL", "FON", 500.0, 1000.0, "MILILITROS", "RB.ACTIV"),   # 0,5 L de fondo por kg
    ("FON", "HUE", 2000.0, 1000.0, "GRAMOS", "RB.ACTIV"),      # 2 kg de hueso por litro
    ("PC", "XX", 999.0, 1000.0, "GRAMOS", "RB.ACTIV"),         # el corte tiene receta: NO se usa
    ("CHO", "MAG", 80.0, 1000.0, "GRAMOS", "RB.ACTIV"),        # 80 g de magret por chorizo
    ("CA", "CB", 500.0, 1000.0, "GRAMOS", "RB.ACTIV"),         # A lleva B…
    ("CB", "CA", 500.0, 1000.0, "GRAMOS", "RB.ACTIV"),         # …y B lleva A: un ciclo
    ("CB", "SLT", 100.0, 1000.0, "GRAMOS", "RB.ACTIV"),
    ("PR", "PC", 1.0, 1.0, "UND", "RB.ACTIV"),                 # el código viejo del pulpo: hoy, receta sobre el corte nuevo
    ("PR", "SLT", 5.0, 1000.0, "GRAMOS", "RB.ACTIV"),          # …más 5 g de sal
    ("SAL", "HUE", 1000.0, 1000.0, "GRAMOS", "RB.INACT"),      # línea de una receta INACTIVA
], columns=["COD PROD RB", "COD INS RB", "CANT", "FACTOR INS", "UNID", "RB ACT"])

PORC = pd.DataFrame([
    # porc, fecha, origen, corte, cant a porcionar, total resultado (= Σ pesos), cant corte, peso corte
    # P1: 3 kg de pulpo entero → 8 cortes de 120 g (2,4 kg) y retazos (0,6 kg); merma 0 para leer fácil
    ("P1", T("2026-09-10 10:00"), "PE", "PC", 3.0, 3.0, 8.0, 2.4),
    ("P1", T("2026-09-10 10:00"), "PE", "RET", 3.0, 3.0, 0.6, 0.6),
    # P2: 4 kg → 10 cortes (2,0 kg) con 2 kg de merma: el corte carga su parte de la merma
    ("P2", T("2026-09-20 10:00"), "PE", "PC", 4.0, 2.0, 10.0, 2.0),
    # PQ: el único porcionamiento es de hace 200 días → respaldo (los 10 más cercanos)
    ("P3", T("2026-03-01 10:00"), "PE", "PQ", 1.0, 1.0, 5.0, 1.0),
    # uno sin peso: no se puede repartir y queda fuera
    ("P4", T("2026-09-11 10:00"), "PE", "PC", 9.0, 0.0, 50.0, 0.0),
    # PR se porcionó hace un año (desde el pulpo entero) pero HOY tiene receta: manda la receta
    ("P5", T("2025-09-01 10:00"), "PE", "PR", 2.0, 2.0, 4.0, 2.0),
    # CX sale de EX en la ventana… y hace un año alguien porcionó CX de vuelta a EX: un círculo
    ("P6", T("2026-09-05 10:00"), "EX", "CX", 5.0, 5.0, 10.0, 5.0),
    ("P7", T("2025-09-01 10:00"), "CX", "EX", 1.0, 1.0, 2.0, 1.0),
], columns=["COD PORC", "FEC REGIST", "COD PROD INIC", "COD PROD FINAL",
            "CANT A PORCIONAR", "CANT TOT RESUL", "CANT RESULT", "PESO RESULT"])

PALOTEO = pd.DataFrame([
    # pedido (mesa), plato (item), plato, grupo, insumo, consumo total (salida), costo total, vendido, unidad
    (T("2026-09-12 12:40"), T("2026-09-12 13:05"), "Ensalada", "Alimentos", "LEC", 250.0, 2.5, 1.0, "GRAMOS"),
    (T("2026-09-12 20:10"), T("2026-09-12 20:30"), "Lomo a la pimienta", "Alimentos", "SAL", 100.0, 1.0, 1.0, "GRAMOS"),
    (T("2026-09-14 20:00"), T("2026-09-14 20:20"), "Pulpo a la leña", "Alimentos", "PC", 2.0, 60.0, 2.0, "UND"),
    (T("2026-09-14 20:00"), T("2026-09-14 20:20"), "Fideua", "Alimentos", "PQ", 1.0, 20.0, 1.0, "UND"),
    (T("2026-09-15 23:30"), T("2026-09-16 01:10"), "Postre tarde", "Alimentos", "LEC", 1000.0, 10.0, 1.0, "GRAMOS"),
    (T("2026-09-16 09:00"), T("2026-09-16 09:00"), "Chorizo Mayta", "Venta Interna", "CHO", 10.0, 50.0, 10.0, "UND"),
    (T("2026-09-16 13:00"), T("2026-09-16 13:00"), "Plato del ciclo", "Alimentos", "CA", 1000.0, 1.0, 1.0, "GRAMOS"),
    (T("2026-09-16 13:00"), T("2026-09-16 13:00"), "Plato sin factor", "Alimentos", "SF", 500.0, 1.5, 1.0, "GRAMOS"),
    (T("2026-09-16 13:00"), T("2026-09-16 13:00"), "Plato sin maestro", "Alimentos", "NOEXISTE", 5.0, 7.0, 1.0, "UND"),
    (T("2026-07-01 13:00"), T("2026-07-01 13:00"), "Fuera del rango", "Alimentos", "LEC", 9999.0, 99.0, 1.0, "GRAMOS"),
    (T("2026-09-17 20:00"), T("2026-09-17 20:10"), "Pulpo a la leña (receta vieja)", "Alimentos", "PR", 1.0, 31.0, 1.0, "UND"),
    (T("2026-09-17 20:00"), T("2026-09-17 20:10"), "Asado de tira", "Alimentos", "CX", 3.0, 48.0, 3.0, "UND"),
], columns=["FECHA PEDIDO", "FECHA ITEM", "PRODUCTO", "GRUPO", "COD INSUMO",
            "CONSUMO TOTAL", "COSTO TOTAL", "CANT VENDIDA", "UNIDAD"])

INI, FIN = dt.date(2026, 9, 1), dt.date(2026, 9, 30)

con = duckdb.connect()
for nombre, df in (("pal", PALOTEO), ("rb", RECETAS), ("po", PORC), ("ma", MAESTRO)):
    con.register(nombre, df)
n1 = con.execute(cr.sql_nivel1("pal", INI, FIN)).df()
r = cr.calcular(n1, con.execute(cr.sql_recetas("rb")).df(),
                con.execute(cr.sql_porcionamientos("po")).df(),
                con.execute(cr.sql_maestro("ma")).df(), INI, FIN)
F = r["filas"]
RES = r["resumen"]


def total(cod, **filtro):
    x = F[F["cod"] == cod]
    for k, v in filtro.items():
        x = x[x[k] == v]
    return float(x["q"].sum())


print("\n── lo directo, en la unidad del kardex ──")
igual(total("LEC"), 0.25 + 1.0, "la lechuga: 250 g + 1000 g = 1,25 kg (sin lo de julio)")
ok(set(F.loc[F["cod"] == "LEC", "camino"]) == {cr.DIRECTO}, "su camino es «directo en el plato»")
ok(set(F.loc[F["cod"] == "LEC", "padre"]) == {""}, "y no tiene preparación")

print("\n── las recetas base, a uno y dos niveles ──")
igual(total("CRE"), 0.1 * 0.3, "la crema: 0,1 kg de salsa × 0,3 L = 0,03 L")
igual(total("HUE"), 0.1 * 0.5 * 2.0, "el hueso: 0,1 kg × 0,5 L de fondo × 2 kg = 0,1 kg")
hue = F[F["cod"] == "HUE"].iloc[0]
ok(hue["padre"] == "FON" and hue["n1"] == "SAL",
   "el hueso cuelga del fondo, y la receta del plato nombra la salsa",
   f"padre={hue['padre']!r} n1={hue['n1']!r}")
cre = F[F["cod"] == "CRE"].iloc[0]
ok(cre["padre"] == "SAL" and cre["n1"] == "", "la crema cuelga de la salsa, sin «en la receta»")
ok(cre["camino"] == "receta base" and cre["ultima"] == "receta base", "su camino es la receta base")
ok(total("HUE") > 0 and abs(total("HUE") - 0.1) < 1e-9,
   "la línea de una receta INACTIVA no suma")

print("\n── el porcionamiento: rendimiento real, por peso, con la merma ──")
# PC en septiembre: P1 aporta 2,4 kg por 8 cortes; P2, 4 kg por 10 (con su merma).
# P4 no pesa y queda fuera. rend = (2,4 + 4) / (8 + 10) kg por corte.
rend_pc = (2.4 + 4.0) / 18.0
igual(total("PE", padre="PC", plato="Pulpo a la leña"), 2 * rend_pc,
      "el pulpo del Pulpo a la leña: 2 cortes × rendimiento de la ventana")
ok(total("XX") == 0.0, "la receta del corte NO se usa: el rendimiento real manda")
ok(set(F.loc[(F["cod"] == "PE") & (F["padre"] == "PC"), "ultima"]) == {"porcionamiento"},
   "la última arista es el porcionamiento")
rp = r["rend"]
f_pc = rp[(rp["cod_x"] == "PC") & (rp["cod_e"] == "PE")].iloc[0]
ok(f_pc["fuente"] == "ventana" and int(f_pc["n_porc"]) == 2,
   "el rendimiento del corte es de la ventana, con 2 porcionamientos", f"{dict(f_pc)}")

print("\n── sin porcionamientos en 90 días: los más cercanos ──")
igual(total("PE", padre="PQ"), 1 * (1.0 / 5.0), "Fideua: 1 corte × 1 kg / 5 cortes")
f_pq = rp[(rp["cod_x"] == "PQ")].iloc[0]
ok(f_pq["fuente"] == "respaldo", "el rendimiento viene del respaldo", f"{dict(f_pq)}")

print("\n── un porcionamiento VIEJO no le gana a la receta de hoy ──")
pr = F[F["plato"] == "Pulpo a la leña (receta vieja)"]
igual(float(pr.loc[pr["cod"] == "PE", "q"].sum()), 1 * rend_pc,
      "el código viejo baja por su receta al corte NUEVO, con el rendimiento de la ventana")
igual(float(pr.loc[pr["cod"] == "SLT", "q"].sum()), 0.005, "y suma la sal de su receta")
ok(set(pr.loc[pr["cod"] == "PE", "camino"]) == {"receta base + porcionamiento"},
   "su camino es receta base y después porcionamiento",
   f"{set(pr['camino'])}")

print("\n── un porcionamiento al revés no se come el consumo ──")
igual(total("EX"), 3 * 5.0 / 10.0, "3 cortes de asado × 0,5 kg: el círculo CX→EX→CX se corta en EX")

print("\n── lo porcionado de verdad, por insumo de origen ──")
po = dict(zip(r["porcionado"]["cod"], r["porcionado"]["cant"]))
igual(po.get("PE", 0.0), 3.0 + 4.0 + 9.0, "pulpo entero porcionado en septiembre: cada porcionamiento una vez")

print("\n── venta interna, turnos y días ──")
cho = F[F["cod"] == "MAG"]
ok(bool(cho["interna"].all()) and len(cho) == 1, "el magret del chorizo es venta interna")
igual(total("MAG"), 10 * 0.08, "10 chorizos × 80 g = 0,8 kg de magret")
igual(RES["costo_nivel1_interna"], 50.0, "el costo de primer nivel de la venta interna")
lec = F[F["cod"] == "LEC"]
igual(float(lec["t0"].sum()), 0.25, "la ensalada de las 13:05 es del almuerzo")
igual(float(lec["t1"].sum()), 1.0, "el postre de la 1:10 es de la cena de la noche anterior")
igual(float(lec["d5"].sum()), 0.25, "el 12 de septiembre de 2026 es sábado")
igual(float(lec["d1"].sum()), 1.0, "el postre va al día de la MESA (martes 15), no al de la hora del plato")

print("\n── ciclos, factores y el maestro ──")
igual(total("SLT", plato="Plato del ciclo"), 1.0 * 0.5 * 0.1,
      "el ciclo A→B→A se corta y la sal de B sí se cuenta")
ok(RES["sin_factor"] == 1 and RES["sin_maestro"] == 1,
   "un código sin factor y uno fuera del maestro quedan contados aparte",
   f"sin_factor={RES['sin_factor']} sin_maestro={RES['sin_maestro']}")
igual(RES["costo_sin_convertir"], 1.5 + 7.0, "y su costo se informa, no se pierde en silencio")

print("\n── la conservación por las recetas base ──")
# El Almacén recuesta cada receta base con sus insumos: la salsa vale S/ 10 el kg = 0,3 L de crema
# (S/ 6) + 0,5 L de fondo (S/ 4: 2 kg de hueso a S/ 4 por litro de fondo). Con esos precios las hojas
# del lomo cuestan EXACTO lo del primer nivel (100 g de salsa = S/ 1): unidades y coeficientes bien.
precio = dict(zip(r["maestro"]["cod"], r["maestro"]["precio"]))
hojas_lomo = sum(float(x.q) * precio[x.cod] for x in F[F["plato"] == "Lomo a la pimienta"].itertuples())
n1_lomo = float(n1.loc[n1["plato"] == "Lomo a la pimienta", "costo"].sum())
igual(n1_lomo, 1.0, "el primer nivel del lomo: 100 g de salsa a S/ 10 el kg")
igual(hojas_lomo, n1_lomo, "y sus hojas —crema y hueso a precio de hoy— cuestan lo mismo")
cu = r["cuadre"].set_index("cod")
ok(abs(cu.loc["SAL", "costo_hojas"] - cu.loc["SAL", "costo_n1"]) < 1e-9
   and not bool(cu.loc["SAL", "con_porcionamiento"]),
   "el cuadre de la salsa cierra y dice que no pasó por un porcionamiento")
ok(bool(cu.loc["PC", "con_porcionamiento"]), "el del corte de pulpo dice que sí")

print("\n── las cubetas ──")
ok(RES["grano"] == "dia" and len(RES["finas"]) == 30, "un mes va día por día")
fino_lec = sorted(i for x in F.loc[F["cod"] == "LEC", "fino"] for i, _ in x)
ok(fino_lec == [11.0, 14.0], "cada venta en el índice de su día (12 → 11, 15 → 14)", f"{fino_lec}")
ok(cr.grano(dt.date(2026, 1, 1), dt.date(2026, 12, 31)) == "semana", "un año va por semana")
fin_sem, mes_sem = cr.cubetas(dt.date(2026, 8, 28), dt.date(2026, 9, 27), "semana")
ok(fin_sem[0] == dt.date(2026, 8, 24) and len(mes_sem) == 2, "las semanas arrancan en lunes; dos meses")
ok(cr.dias_por_dia_semana(dt.date(2026, 8, 28), dt.date(2026, 9, 27)) == [4, 4, 4, 4, 5, 5, 5],
   "del 28 de agosto al 27 de septiembre: cinco viernes, sábados y domingos")
ok(RES["niveles"] == 2, "el árbol más hondo del caso tiene dos niveles", f"{RES['niveles']}")
ok(set(rp.loc[rp["cod_x"] == "PR", "fuente"]) == {"respaldo"},
   "el porcionamiento viejo del código viejo sigue en la tabla de rendimientos (para mostrarlo)")

print("\n── la vista: contra lo que se compró y la receta editada (regla #560) ──")
# El modelo de la página (`graficos/movimientos_consumo.py`) sobre el mismo
# resultado: lo comprado del rango viaja con la página, y un plato cuya
# receta se editó dentro del rango lleva su fecha.
from graficos import movimientos_consumo as mc  # noqa: E402  (después del cálculo, a propósito)

COMPRAS = pd.DataFrame([
    # cod, nombre, unidad, familia, subfamilia, cantidad, valor, documento, fecha
    ("CRE", "Crema de leche", "LITROS", "ALIMENTOS", "LACTEOS", 2.0, 40.0, "F1", T("2026-09-03")),
    ("CRE", "Crema de leche", "LITROS", "ALIMENTOS", "LACTEOS", 1.0, 21.0, "F2", T("2026-09-18")),
    ("OLE", "Aceite de freír", "LITROS", "ALIMENTOS", "ABARROTES", 20.0, 150.0, "F2", T("2026-09-18")),
    ("CAR", "Carbón vegetal", "KILOS", "COSTOS PRODUCCION", "COMBUSTIBLE", 50.0, 90.0, "F3", T("2026-09-05")),
    ("LEC", "Lechuga", "KILOS", "ALIMENTOS", "VERDURAS", 5.0, 50.0, "F4", T("2026-08-20")),  # fuera
], columns=["COD_PRODUCTO", "NOMBRE_PRODUCTO", "UNIDAD_DE_INGRESO", "FAMILIA", "SUBFAMILIA",
            "CANTIDAD_COMPRA", "VALOR_COMPRA", "NUM_DOCUMENTO", "FECHA_EMISION_DOC"])
cp = mc.compras_del_rango(COMPRAS, INI, FIN)
cpi = cp.set_index("cod")
ok(set(cp["cod"]) == {"CRE", "OLE"},
   "las compras del rango, sólo alimentos y bebidas: el carbón y lo de agosto quedan fuera",
   f"{sorted(cp['cod'])}")
igual(cpi.loc["CRE", "cant"], 3.0, "la crema: dos facturas suman 3 litros")
igual(cpi.loc["CRE", "valor"], 61.0, "y S/ 61")
ok(int(cpi.loc["CRE", "docs"]) == 2, "en 2 documentos")
cp_car = mc.compras_del_rango(COMPRAS, INI, FIN, ("COSTOS PRODUCCION",))
ok(list(cp_car["cod"]) == ["CAR"], "con el chip de familia puesto, manda el chip")
ok(mc.compras_del_rango(None, INI, FIN) is None, "sin compras, None: la página lo dice")

RV = pd.DataFrame({
    "NOMB PLATO": ["Lomo a la pimienta", "Lomo a la pimienta", "Ensalada", "Fideua"],
    "FECH MODIF": [T("2026-09-02 14:26"), T("2026-09-02 14:26"), T("2026-03-10"), None],
})
ed = mc.recetas_editadas(RV, INI)
ok(ed == {"Lomo a la pimienta": "2026-09-02"},
   "las recetas editadas desde el primer día del rango, por nombre", f"{ed!r}")

d = mc.datos_de_la_vista(r, (), compras=cp, editadas=ed)
ok(d["compras"].get("CRE") == [3.0, 61.0, 2], "la crema comprada viaja con la página",
   f"{d['compras'].get('CRE')!r}")
ok("OLE" in d["comprados"] and "CRE" not in d["comprados"],
   "lo comprado que ninguna venta usó viaja con su nombre; lo usado, no (ya está en insumos)")
ok(d["comprados"].get("OLE", [None])[0] == "Aceite de freír", "con su nombre")
ok(d["compras_familias"] == sorted(mc.FAMILIAS_INSUMO),
   "sin chip, las familias de alimentos y bebidas", f"{d['compras_familias']!r}")
plato = {p[0]: p for p in d["platos"]}
ok(plato["Lomo a la pimienta"][3] == "2026-09-02" and plato["Ensalada"][3] == "",
   "el plato con la receta editada lleva su fecha; los demás, vacío")
sin = mc.datos_de_la_vista(r, ())
ok(sin["compras"] == {} and sin["compras_familias"] == [],
   "sin compras leídas, la página no promete la pestaña", f"{sin['compras_familias']!r}")

print("\n── el cableado ──")
arbol = ast.parse((RAIZ / "graficos" / "ventas_ficha_hora.py").read_text(encoding="utf-8"))
raros = next((ast.literal_eval(n.value) for n in ast.walk(arbol)
              if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "GRUPOS_RAROS" for t in n.targets)),
             None)
ok(raros is not None and tuple(raros) == tuple(cr.GRUPOS_NO_SERVICIO),
   "la venta interna es la misma de Ventas › Por hora (GRUPOS_RAROS)", f"{raros!r}")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (consumo según recetas)")
