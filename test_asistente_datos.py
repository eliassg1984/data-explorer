"""test_asistente_datos.py — pruebas de la capa de datos del asistente IA.

Corre SIN API key y SIN navegador: `asistente_datos.py` es Python puro sobre
un DataFrame, y esa testeabilidad es justo el motivo de haberlo separado de
`asistente.py` (que sí necesita Groq y Streamlit).

Se ejecuta solo:  python test_asistente_datos.py
"""

import sys

import pandas as pd

from asistente_datos import (
    MAX_FILAS_RESULTADO,
    _con_limite,
    _validar_sql,
    columnas_sin_comillas,
    ejecutar_sql,
    esquema_para_prompt,
    nota_de_grano,
    resumen_para_prompt,
)

# Igual que test_graficos.py: la consola de Windows (cp1252) no puede imprimir
# los ─/✅ de este script y revienta con UnicodeEncodeError en el PRIMER print,
# antes de correr una sola prueba — el gate de CLAUDE.md fallaba sin decir por
# qué. Forzar UTF-8 lo hace correr igual en Windows y en Linux.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_fallos = []


def ok(cond, nombre):
    print(f"{'OK  ' if cond else 'FALLA'}  {nombre}")
    if not cond:
        _fallos.append(nombre)


def df_prueba():
    """Imita la forma real de ajusteinventario.parquet: nombres con ESPACIOS."""
    return pd.DataFrame({
        "FECHA APERTURA INVENTARIO": pd.to_datetime(
            ["2026-08-01", "2026-08-01", "2026-08-02", "2026-08-02", "2026-08-03"]),
        "AREA": ["PRODUCCION", "GASTOS", "PRODUCCION", "BARRA", "PRODUCCION"],
        "FAMILIA": ["ALIMENTOS", "GASTOS", "ALIMENTOS", "BEBIDAS", "ALIMENTOS"],
        "PRODUCTO": ["Curasal", "Carbon", "Curasal", "Pisco", "Lomo"],
        "AJUSTE": [-10.0, -5.0, -3.0, 2.0, -1.0],
        "AJUSTE VALORIZADO": [-1000.0, -500.0, -300.0, 200.0, -100.0],
    })


# ── Validación de SQL ──────────────────────────────────────────────────────
print("\n── validación de SQL ──")
ok(_validar_sql("SELECT 1") is None, "acepta un SELECT")
ok(_validar_sql("  with x as (select 1) select * from x") is None,
   "acepta WITH ... SELECT")
ok(_validar_sql("") is not None, "rechaza consulta vacía")
ok(_validar_sql("DELETE FROM datos") is not None, "rechaza DELETE")
ok(_validar_sql("DROP TABLE datos") is not None, "rechaza DROP")
ok(_validar_sql("SELECT 1; DROP TABLE datos") is not None,
   "rechaza dos sentencias (';' intermedio)")
ok(_validar_sql("COPY datos TO 'x.csv'") is not None,
   "rechaza COPY (escribiría en disco)")
ok(_validar_sql("SELECT * FROM read_parquet('/etc/x')") is not None,
   "rechaza read_parquet (leería el disco del server)")
ok(_validar_sql("INSTALL httpfs") is not None, "rechaza INSTALL")
# La blocklist va por \b: no debe dispararse por substring en un nombre real.
ok(_validar_sql('SELECT "FECHA CREACION" FROM datos') is None,
   "NO rechaza por substring ('CREACION' contiene 'crea', no la palabra)")

print("\n── LIMIT automático ──")
ok(_con_limite("SELECT 1").endswith(f"LIMIT {MAX_FILAS_RESULTADO}"),
   "agrega LIMIT si falta")
ok(_con_limite("SELECT 1 LIMIT 5").endswith("LIMIT 5"),
   "respeta el LIMIT que ya trae")
ok(_con_limite("SELECT 1 limit 7 ").endswith("limit 7"),
   "respeta LIMIT en minúscula")

# ── Ejecución ──────────────────────────────────────────────────────────────
print("\n── ejecución sobre el df ──")
d = df_prueba()

r = ejecutar_sql(d, 'SELECT SUM("AJUSTE VALORIZADO") AS t FROM datos')
ok(r["ok"], "corre un SUM con columna entre comillas")
ok(abs(r["filas"][0]["t"] - (-1700.0)) < 1e-6, "el SUM da el total correcto")

r = ejecutar_sql(d, 'SELECT "PRODUCTO", SUM("AJUSTE VALORIZADO") AS m FROM datos '
                    'GROUP BY "PRODUCTO" ORDER BY m ASC')
ok(r["ok"] and r["filas"][0]["PRODUCTO"] == "Curasal",
   "GROUP BY agrega las 2 filas de Curasal y queda primero (-1300)")
ok(abs(r["filas"][0]["m"] - (-1300.0)) < 1e-6,
   "el agregado por producto suma bien (-1000 + -300)")

r = ejecutar_sql(d, "SELECT AREA FROM datos")
ok(r["ok"], "una columna SIN espacios no necesita comillas (AREA)")

# ── El fallo SILENCIOSO: columna con espacios sin comillas ─────────────────
# `SELECT AJUSTE VALORIZADO` NO da error en DuckDB: lo lee como
# `SELECT AJUSTE AS VALORIZADO` y devuelve unidades (-10) con el nombre de
# soles (-1000). Verificado en vivo. Por eso se rechaza ANTES de ejecutar.
print("\n── guarda de columnas con espacios ──")
ok(columnas_sin_comillas('SELECT AJUSTE VALORIZADO FROM datos',
                         d.columns) == ["AJUSTE VALORIZADO"],
   "detecta la columna con espacios sin comillas")
ok(columnas_sin_comillas('SELECT "AJUSTE VALORIZADO" FROM datos',
                         d.columns) == [],
   "no marca nada si está bien citada")
ok(columnas_sin_comillas("SELECT * FROM datos WHERE \"PRODUCTO\" = 'AJUSTE VALORIZADO'",
                         d.columns) == [],
   "no confunde un literal de texto con un identificador")
ok(columnas_sin_comillas("SELECT ajuste valorizado FROM datos",
                         d.columns) == ["AJUSTE VALORIZADO"],
   "detecta en minúscula (DuckDB no distingue caja en identificadores)")

r = ejecutar_sql(d, "SELECT AJUSTE VALORIZADO FROM datos")
ok(not r["ok"] and "comillas" in r["error"].lower(),
   "ejecutar_sql RECHAZA el alias silencioso en vez de devolver la columna mala")
ok("AJUSTE VALORIZADO" in (r.get("error") or ""),
   "el error le dice al modelo cuál columna citar para que reintente")

r = ejecutar_sql(d, "DELETE FROM datos")
ok(not r["ok"] and "rechazada" in r["error"].lower(),
   "el DELETE se rechaza ANTES de tocar DuckDB")

r = ejecutar_sql(d, "SELECT * FROM tabla_que_no_existe")
ok(not r["ok"] and "error" in r, "un error de DuckDB vuelve como dict, no lanza")

r = ejecutar_sql(pd.DataFrame(), "SELECT 1")
ok(not r["ok"], "df vacío se reporta como error legible")

r = ejecutar_sql(None, "SELECT 1")
ok(not r["ok"], "df None no revienta")

# Fechas: tienen que serializarse (el JSON de un Timestamp explota si no).
r = ejecutar_sql(d, 'SELECT "FECHA APERTURA INVENTARIO" AS f FROM datos LIMIT 1')
ok(r["ok"] and isinstance(r["filas"][0]["f"], str),
   "las fechas se serializan a texto ISO")

# Truncado
grande = pd.DataFrame({"n": range(500)})
r = ejecutar_sql(grande, "SELECT * FROM datos LIMIT 500")
ok(r["ok"] and r["filas_devueltas"] == MAX_FILAS_RESULTADO and r["truncado"],
   f"recorta a {MAX_FILAS_RESULTADO} filas y marca truncado=True")

# ── Esquema ────────────────────────────────────────────────────────────────
print("\n── esquema para el prompt ──")
esq = esquema_para_prompt(d)
ok('"AJUSTE VALORIZADO"' in esq, "las columnas van entre comillas dobles")
ok("DECIMAL" in esq and "FECHA" in esq and "TEXTO" in esq,
   "los tipos se traducen a etiquetas legibles")
ok("'PRODUCCION'" in esq and "'BARRA'" in esq,
   "lista los valores de las categóricas de baja cardinalidad")
ok("2026-08-01" in esq and "2026-08-03" in esq,
   "informa el rango de la columna de fecha")

muchos = pd.DataFrame({"COD": [f"P{i}" for i in range(200)]})
ok("valores distintos" in esquema_para_prompt(muchos),
   "con alta cardinalidad NO lista valores, solo el conteo")
ok("sin datos" in esquema_para_prompt(pd.DataFrame()),
   "df vacío no revienta el esquema")

# ── Resumen ────────────────────────────────────────────────────────────────
print("\n── resumen para el prompt ──")
res = resumen_para_prompt(d, "Ajuste de Inventario", {"Área": ["PRODUCCION"]})
ok("Ajuste de Inventario" in res, "nombra el reporte activo")
ok("FILTROS ACTIVOS" in res and "PRODUCCION" in res,
   "declara los filtros activos (si no, contesta totales que contradicen la pantalla)")
ok("5" in res, "informa el número de filas visibles")

res2 = resumen_para_prompt(d, "Ajuste de Inventario", {})
ok("ninguno" in res2, "sin filtros lo dice explícito")
res3 = resumen_para_prompt(d, "X", {"Área": []})
ok("ninguno" in res3, "un filtro con lista vacía NO cuenta como activo")
ok("no devuelve ninguna fila" in resumen_para_prompt(pd.DataFrame(), "X", {}),
   "df vacío se explica en el resumen")

# ── Grano de Ventas: una fila por ítem Y por forma de pago (regla #517) ───
# A pagado con dos formas: dos filas, cada una con la venta ENTERA del
# plato y la propina ENTERA de su pago. B, un solo pago. Un ítem sin pago.
dv = pd.DataFrame({
    "LLAVE LOCAL DOCUMENTO": ["D1", "D1", "D1", "D2"],
    "LLAVE LOCAL DOCUMENTO ITEM": ["A", "A", "B", "C"],
    "LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO": ["D1-1", "D1-2", "D1-1", None],
    "NOMBRE TIPO PAGO": ["CHEQUE", "TARJETA", "CHEQUE", None],
    "MONTO PROPINA": [5.0, 2.0, 5.0, 0.0],
    "TOTAL MDOCUMENTO": [130.0, 130.0, 130.0, 20.0],
    "VENTA ITEM DDOCUMENTO": [100.0, 100.0, 30.0, 20.0],
})
nota = nota_de_grano(dv)
ok(nota is not None and "LLAVE LOCAL DOCUMENTO ITEM" in nota
   and "LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO" in nota,
   "ventas: la nota de grano nombra las dos llaves")
ok(nota_de_grano(d) is None, "otro reporte: sin nota de grano")
dc = pd.DataFrame({
    "NUM_DOCUMENTO": ["F1", "F1", "F2"],
    "TOTAL NETO": [150.0, 150.0, 40.0],
    "VALOR_COMPRA": [100.0, 50.0, 40.0],
    "VALOR_NC": [0.0, 10.0, 0.0],
    "NOTA_CREDITO": ["", "N1", ""],
})
rc = resumen_para_prompt(dc, "Compras", {})
ok('Suma de "VALOR_COMPRA": S/ 190.00' in rc,
   "compras: el resumen suma VALOR_COMPRA, no la cabecera TOTAL NETO")
ok("NOTAS DE CRÉDITO" in (nota_de_grano(dc) or ""),
   "compras con notas restadas: la nota lo dice")
rv = resumen_para_prompt(dv, "Ventas", {})
ok("VENTA ITEM DDOCUMENTO" in rv and "150.00" in rv and "250.00" not in rv,
   "ventas: el resumen suma la VENTA un ítem una vez (150, no 250)")
ok("TOTAL MDOCUMENTO" not in rv.split("GRANO")[0],
   "ventas: el resumen no suma la cabecera repetida")
# El SQL que la nota le enseña al modelo tiene que correr y dar lo correcto.
r = ejecutar_sql(dv, 'SELECT SUM("VENTA ITEM DDOCUMENTO") AS v FROM (SELECT * '
                 'FROM datos QUALIFY "LLAVE LOCAL DOCUMENTO ITEM" IS NULL OR '
                 'ROW_NUMBER() OVER (PARTITION BY "LLAVE LOCAL DOCUMENTO ITEM")'
                 ' = 1)')
ok(r.get("ok") and r["filas"][0]["v"] == 150.0,
   "ventas: el QUALIFY de la nota pasa el validador y suma 150")
r = ejecutar_sql(dv, 'SELECT SUM(p) AS p FROM (SELECT ANY_VALUE("MONTO PROPINA")'
                 ' AS p FROM datos WHERE "LLAVE LOCAL DOCUMENTO CORRELATIVO '
                 'PAGO" IS NOT NULL GROUP BY "LLAVE LOCAL DOCUMENTO CORRELATIVO'
                 ' PAGO")')
ok(r.get("ok") and r["filas"][0]["p"] == 7.0,
   "ventas: la propina por pago suma 7 (por fila serían 12)")

# ── Tablas adicionales (regla #626) ────────────────────────────────────────
# Movimientos le da al modelo las SALIDAS además de `datos` (requerimientos).
from asistente_datos import esquema_extras, tablas_validas  # noqa: E402

sal = pd.DataFrame({"NOMBRE PRODUCTO": ["Arroz Blanco Granel", "Arroz Bomba"],
                    "TIPO DESCARGO": ["Comida Personal", "Bajas"],
                    "CANT SALIDA": [125.5, 1.0], "VALOR NETO": [580.0, 9.0]})
extras = {"salidas": {"df": sal, "nota": "las notas de salida"},
          "datos": {"df": sal}, "mal nombre": {"df": sal},
          "vacia": {"df": pd.DataFrame()}}
ok(list(tablas_validas(extras)) == ["salidas"],
   "extras: sólo nombres simples, no `datos` y con filas")
_e = esquema_extras(extras)
ok("Tabla `salidas` (2 filas) — las notas de salida" in _e
   and '"TIPO DESCARGO"' in _e, "extras: el prompt nombra la tabla y su esquema")
ok(esquema_extras({}) == "", "sin extras, el prompt no cambia")
r = ejecutar_sql(d, 'SELECT SUM("CANT SALIDA") AS kg FROM salidas WHERE '
                 '"TIPO DESCARGO" = \'Comida Personal\' AND '
                 '"NOMBRE PRODUCTO" ILIKE \'%arroz%\'', extras)
ok(r.get("ok") and r["filas"][0]["kg"] == 125.5,
   "extras: el SQL consulta `salidas` por su nombre")
r = ejecutar_sql(d, "SELECT CANT SALIDA FROM salidas", extras)
ok(not r.get("ok") and "CANT SALIDA" in r.get("error", ""),
   "extras: la guarda de comillas cubre las columnas de las extras")
r = ejecutar_sql(None, "SELECT COUNT(*) AS n FROM salidas", extras)
ok(r.get("ok") and r["filas"][0]["n"] == 2,
   "extras: sin `datos`, las extras se consultan igual")

# ── Requerimientos: lo que suma la página (regla #643) ─────────────────────
# El `datos` de Movimientos. Las vistas no suman los anulados ni las líneas
# sin producto (#641) y el modelo no lo sabía: S/ 238.884 contra 238.118 en
# los últimos 30 días. Los casos de `test_graficos.py::_pruebas_
# requerimientos_por_area`: R1 con dos líneas; R2 ANULADO con valor; R3 SIN
# ÍTEMS; R4 GENERADO con ítem (suma); R5 anulado, en minúscula y con un
# espacio, y sin ítems. Con PRECIO UNIT, que el resumen sumaba en vez del
# valorizado.
print("\n── requerimientos: qué suma ──")
from asistente_datos import filtro_requerimientos  # noqa: E402

dr = pd.DataFrame({
    "FECHA REGISTRO": pd.to_datetime(
        ["2026-09-12", "2026-09-12", "2026-09-13", "2026-09-14",
         "2026-09-15", "2026-09-16"]),
    "FECHA PROCESADO": pd.to_datetime(
        ["2026-09-12", "2026-09-12", None, "2026-09-14", None, None]),
    "COD REQUERIMIENTO": ["R1", "R1", "R2", "R3", "R4", "R5"],
    "NOMBRE ESTADO REQUERIMIENTO": ["PROCESADO", "PROCESADO", "ANULADO",
                                    "PROCESADO", "GENERADO", " anulado"],
    "SUB ALMACEN": ["COCINA", "COCINA", "PRODUCCION", "GASTOS", "BARRA",
                    "COCINA"],
    "NOMBRE PRODUCTO": ["A", "B", "C", None, "D", " "],
    "CANTIDAD": [1.0, 2.0, 3.0, None, 4.0, None],
    "PRECIO UNIT": [10.0, 10.0, 10.0, None, 10.0, None],
    "VALOR ITEM": [10.0, 20.0, 30.0, None, 40.0, None],
})
filtro = filtro_requerimientos(dr)
nr = nota_de_grano(dr) or ""
ok(filtro is not None and f"WHERE {filtro})" in nr,
   "requerimientos: la nota trae el filtro EXACTO que se prueba abajo")
ok('COUNT(DISTINCT "COD REQUERIMIENTO")' in nr and "COUNT(*)" in nr,
   "requerimientos: un requerimiento es un código, no una fila (#508)")
ok('"PRECIO UNIT" es por unidad: no lo sumes' in nr,
   "requerimientos: el precio unitario no se suma")
ok('"FECHA PROCESADO"' in nr and "NO está recortado" in nr,
   "requerimientos: nombra las dos fechas y que `datos` es el histórico")
r = ejecutar_sql(dr, 'SELECT SUM("VALOR ITEM") AS v, COUNT(DISTINCT '
                 f'"COD REQUERIMIENTO") AS n FROM (SELECT * FROM datos '
                 f'WHERE {filtro})')
ok(r.get("ok") and r["filas"][0] == {"v": 70.0, "n": 2},
   "requerimientos: el filtro de la nota pasa el validador y da 70 en 2 "
   "requerimientos (R1 y R4)")

# Contra las VISTAS: lo que el filtro deja tiene que ser lo que suma
# «Requerimientos por Área». Si `_que_suman` cambia de criterio —excluir
# también lo GENERADO, por ejemplo—, el asistente se queda atrás y esto
# falla.
from graficos.movimientos import requerimientos_que_suman  # noqa: E402

_val, _ = requerimientos_que_suman(
    dr, col_estado="NOMBRE ESTADO REQUERIMIENTO", col_prod="NOMBRE PRODUCTO",
    col_doc="COD REQUERIMIENTO", col_val="VALOR ITEM")
ok(r.get("ok") and r["filas"][0]["v"] == _val["VALOR ITEM"].sum()
   and r["filas"][0]["n"] == _val["COD REQUERIMIENTO"].nunique(),
   "requerimientos: la nota suma lo mismo que `requerimientos_que_suman`")

rr = resumen_para_prompt(dr, "Movimientos", {})
ok('Suma de "VALOR ITEM" sin anulados' in rr and "S/ 70.00" in rr,
   "requerimientos: el resumen suma como la página (70, no 100)")
ok("Requerimientos que suman: 2" in rr
   and "Anulados, aparte: 2 requerimientos por S/ 30.00" in rr,
   "requerimientos: el resumen cuenta códigos y nombra los anulados aparte")
ok('"PRECIO UNIT"' not in rr.split("REQUERIMIENTOS")[0],
   "requerimientos: el resumen no suma el precio unitario")

# El demo (`data._datos_demo`) escribe las columnas en otra caja y no trae
# el código: la nota usa los nombres REALES y el filtro sigue andando.
dd = pd.DataFrame({
    "Fecha Registro": pd.to_datetime(["2025-01-01", "2025-01-02",
                                      "2025-01-03"]),
    "Nombre Producto": ["Producto demo 001", "Producto demo 002", None],
    "Nombre Estado Requerimiento": ["Procesado", "Anulado", "Procesado"],
    "Valor Item": [5.0, 7.0, 0.0],
})
fd = filtro_requerimientos(dd) or ""
ok('"Nombre Estado Requerimiento"' in fd and '"Nombre Producto"' in fd,
   "requerimientos: el filtro usa la caja real de las columnas")
r = ejecutar_sql(dd, f'SELECT SUM("Valor Item") AS v FROM datos WHERE {fd}')
ok(r.get("ok") and r["filas"][0]["v"] == 5.0,
   "requerimientos: 'Anulado' en minúscula tampoco suma")
ok("COUNT(DISTINCT" not in (nota_de_grano(dd) or "-")
   and "Anulados, aparte: S/ 7.00" in resumen_para_prompt(dd, "X", {}),
   "requerimientos: sin código, la nota no habla de contar códigos")

ok(filtro_requerimientos(d) is None and filtro_requerimientos(dv) is None,
   "otros reportes: no se confunden con requerimientos")
_sin_estado = pd.DataFrame({"PRECIO UNIT": [10.0, 10.0],
                            "VALOR ITEM": [10.0, 20.0]})
ok('Suma de "VALOR ITEM": S/ 30.00' in resumen_para_prompt(_sin_estado,
                                                            "X", {}),
   "sin estado, el resumen igual elige VALOR ITEM antes que PRECIO UNIT")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (capa de datos del asistente)")
