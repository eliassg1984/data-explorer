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

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (capa de datos del asistente)")
