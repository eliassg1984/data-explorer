"""test_sunat.py — pruebas de la capa de datos del SIRE Compras (sunat.py).

Corre SIN credenciales de SUNAT y SIN red: todo lo que se prueba acá son
funciones puras (validación de período, aplanado del JSON, la ficha) más el
modo demo y el render del PDF.

Lo que más vale tener cubierto es `_normalizar_registro`, porque falla EN
SILENCIO y con datos que parecen razonables:

  · **Los importes vienen ANIDADOS** en `montos` y el tipo de cambio en
    `tipoCambio`. Un `reg.get("mtoIgvIpmDG")` plano devuelve None, se
    convierte en 0.0 y el período entero sale con IGV cero — sin error.
  · **`total` no existe como campo** en la respuesta de SUNAT: se suma de
    sus componentes. Si mañana agregan un `mtoTotalCP`, ese gana, y hay
    prueba de las dos ramas.

Se ejecuta solo:  python test_sunat.py
"""

import sys

import pandas as pd

import sunat

# Igual que test_graficos.py / test_asistente_datos.py: la consola de Windows
# (cp1252) revienta con UnicodeEncodeError en el primer print con ─/✅.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_fallos = []


def ok(cond, nombre):
    print(f"{'OK  ' if cond else 'FALLA'}  {nombre}")
    if not cond:
        _fallos.append(nombre)


# Comprobante REAL de la respuesta de SUNAT (RUC 20605204300, período
# 202607), recortado a los campos que consume la app. Sirve de contrato: si
# SUNAT cambia la forma del JSON, esta prueba es la que avisa.
REG_REAL = {
    "codCar": "2060690231101E0010000001839",
    "codTipoCDP": "01",
    "desTipoCDP": "Factura",
    "numSerieCDP": "E001",
    "numCDP": "1839",
    "fecEmision": "2026-04-10",
    "fecVencPag": None,
    "numDocIdentidadProveedor": "20606902311",
    "nomRazonSocialProveedor": "GLAB GROUP E.I.R.L.",
    "codMoneda": "PEN",
    "desEstadoComprobante": "Activo",
    "perTributario": "202607",
    "indDetraccion": "D",
    "porTasaIGV": 0.18,
    "tipoCambio": {"mtoTipoCambio": 1},
    "montos": {
        "mtoBIGravadaDG": 1950.0, "mtoIgvIpmDG": 351.0,
        "mtoBIGravadaDGNG": 0.0, "mtoIgvIpmDGNG": 0.0,
        "mtoBIGravadaDNG": 0.0, "mtoIgvIpmDNG": 0.0,
    },
}


# ── Período tributario ─────────────────────────────────────────────────────
print("\n── período tributario ──")
ok(sunat.periodo_valido("202608"), "acepta yyyymm válido")
ok(not sunat.periodo_valido("2026-08"), "rechaza con guion")
ok(not sunat.periodo_valido("202613"), "rechaza mes 13")
ok(not sunat.periodo_valido("202600"), "rechaza mes 00")
ok(not sunat.periodo_valido("20268"), "rechaza longitud != 6")
ok(not sunat.periodo_valido(""), "rechaza vacío")
ok(not sunat.periodo_valido("199901"), "rechaza año anterior a 2000")

ok(sunat.periodo_desde_fecha(pd.Timestamp("2026-08-19")) == "202608",
   "período desde una fecha")
ok(sunat.periodo_desde_fecha(pd.Timestamp("2026-01-05")) == "202601",
   "período desde una fecha rellena el mes con cero")

# El rango de la franja es por FECHA y SUNAT razona por mes: un rango a
# caballo de tres meses son tres períodos, no dos.
ok(sunat.periodos_entre(pd.Timestamp("2026-01-15"),
                        pd.Timestamp("2026-03-03"))
   == ["202601", "202602", "202603"], "rango a caballo → 3 períodos")
ok(sunat.periodos_entre(pd.Timestamp("2026-08-01"),
                        pd.Timestamp("2026-08-31")) == ["202608"],
   "rango dentro de un mes → 1 período")
ok(sunat.periodos_entre(pd.Timestamp("2026-03-03"),
                        pd.Timestamp("2026-01-15"))
   == ["202601", "202602", "202603"], "rango invertido se ordena solo")
ok(sunat.periodos_entre(None, None) == [], "rango vacío → lista vacía")

# ── Tipos de comprobante ───────────────────────────────────────────────────
print("\n── tipos de comprobante ──")
ok(sunat.nombre_tipo_cdp("01") == "Factura", "01 es Factura")
ok(sunat.nombre_tipo_cdp("1") == "Factura", "sin cero a la izquierda también")
ok(sunat.nombre_tipo_cdp("07") == "Nota de crédito", "07 es Nota de crédito")
ok(sunat.nombre_tipo_cdp("30") == "Documentos emitidos por Adquiriente",
   "30 existe (aparece en datos reales de ABRASA)")
ok(sunat.nombre_tipo_cdp("99") == "99", "código desconocido se muestra crudo")

# ── Aplanado del JSON de SUNAT ─────────────────────────────────────────────
print("\n── _normalizar_registro (contrato con el JSON real) ──")
n = sunat._normalizar_registro(REG_REAL)
ok(n["documento"] == "E001-1839", "arma serie-número")
ok(n["ruc_proveedor"] == "20606902311", "RUC del PROVEEDOR, no el nuestro")
ok(n["proveedor"] == "GLAB GROUP E.I.R.L.", "razón social del proveedor")
ok(n["base_imponible"] == 1950.0, "base sale de montos.mtoBIGravadaDG (anidado)")
ok(n["igv"] == 351.0, "IGV sale de montos.mtoIgvIpmDG (anidado)")
ok(n["total"] == 2301.0, "total se SUMA de sus componentes (no viene dado)")
ok(n["tipo_nombre"] == "Factura", "usa desTipoCDP de SUNAT")
ok(n["tipo_cambio"] == 1.0, "tipo de cambio sale de tipoCambio (anidado)")
ok(n["estado"] == "Activo", "trae el estado del comprobante")
ok(n["periodo"] == "202607", "trae el período tributario")

# Si SUNAT algún día manda el total explícito, ese gana sobre la suma.
_con_total = {**REG_REAL, "montos": {**REG_REAL["montos"],
                                     "mtoTotalCP": 9999.0}}
ok(sunat._normalizar_registro(_con_total)["total"] == 9999.0,
   "si viene mtoTotalCP explícito, gana sobre la suma")

# Robustez: SUNAT manda null en varios campos según el tipo de comprobante.
_hueco = {"codTipoCDP": "07", "numSerieCDP": None, "numCDP": None,
          "montos": None, "tipoCambio": None}
_nh = sunat._normalizar_registro(_hueco)
ok(_nh["total"] == 0.0, "sin montos → 0.0, no revienta")
ok(_nh["tipo_nombre"] == "Nota de crédito",
   "sin desTipoCDP cae a la tabla local")
ok(_nh["tipo_cambio"] == 1.0, "sin tipoCambio cae a 1.0")

# ── registros_a_df ─────────────────────────────────────────────────────────
print("\n── registros_a_df ──")
df = sunat.registros_a_df([REG_REAL, _con_total])
ok(len(df) == 2, "convierte los dos registros")
ok(str(df["fecha_emision"].iloc[0].date()) == "2026-04-10",
   "parsea la fecha ISO que manda SUNAT")
ok(df["total"].sum() == 2301.0 + 9999.0, "suma los totales")
_vacio = sunat.registros_a_df([])
ok(_vacio.empty and "total" in _vacio.columns,
   "lista vacía → df vacío PERO con las columnas (la vista las lee)")

# ── Deduplicación (la paginación de SUNAT se solapa) ───────────────────────
print("\n── deduplicación por codCar (bug real de paginación de SUNAT) ──")
# Reproduce lo medido en vivo: pidiendo perPage=100 sobre 323 comprobantes,
# SUNAT devuelve 100 / 200 / 123 / 23 filas — el offset avanza pero el
# límite crece con la página, así que las páginas se SOLAPAN. Acumular a
# ciegas daba 446 filas y un total 38% inflado. Ver el bucle de
# `obtener_comprobantes`.
_univ = [{**REG_REAL, "codCar": f"CAR{i:04d}", "numCDP": str(i)}
         for i in range(323)]


def _pagina_simulada(page, per_page=100):
    """Lo que devuelve SUNAT: offset correcto, límite = page * per_page."""
    ini = (page - 1) * per_page
    return _univ[ini:ini + page * per_page]


ok(len(_pagina_simulada(1)) == 100, "simulador: page 1 → 100")
ok(len(_pagina_simulada(2)) == 200, "simulador: page 2 → 200 (solapada)")
ok(len(_pagina_simulada(3)) == 123, "simulador: page 3 → 123")
_crudo = sum((_pagina_simulada(p) for p in (1, 2, 3, 4)), [])
ok(len(_crudo) == 446, "acumular a ciegas da 446 (inflado)")
ok(len({r["codCar"] for r in _crudo}) == 323,
   "deduplicando por codCar quedan los 323 reales")
_df_dedup = sunat.registros_a_df(list({r["codCar"]: r for r in _crudo}.values()))
ok(len(_df_dedup) == 323, "registros_a_df sobre lo deduplicado da 323 filas")

# ── Modo demo ──────────────────────────────────────────────────────────────
print("\n── modo demo ──")
d1 = sunat._datos_demo("202608")
d2 = sunat._datos_demo("202608")
ok(d1["total"].sum() == d2["total"].sum(),
   "es determinista entre llamadas (crc32, no hash())")
ok(sunat._datos_demo("202607")["total"].sum() != d1["total"].sum(),
   "cambia con el período")
ok(len(d1) == 48, "genera las filas pedidas")
ok(set(d1["fecha_emision"].dt.month) == {8}, "las fechas caen dentro del mes")
ok((d1.loc[d1["tipo_cdp"] == "07", "total"] < 0).all(),
   "las notas de crédito restan")
ok(sunat._datos_demo("202602")["fecha_emision"].dt.day.max() <= 29,
   "respeta los días del mes (febrero)")
# El demo tiene que tener LA MISMA forma que el dato real, o la vista se
# rompe justo cuando se conectan las credenciales.
_faltan = set(sunat._COLUMNAS) - set(d1.columns)
ok(not _faltan, f"el demo trae todas las columnas canónicas (faltan: {_faltan})")

# ── Ficha PDF ──────────────────────────────────────────────────────────────
print("\n── ficha PDF ──")
pdf = sunat.ficha_pdf(d1.iloc[0])
ok(pdf[:4] == b"%PDF", "devuelve un PDF de verdad")
ok(len(pdf) > 1500, "el PDF tiene contenido, no es una página en blanco")
ok(sunat.ficha_pdf(n)[:4] == b"%PDF", "también con un registro real de SUNAT")
_hueca = {"documento": "F001-1", "tipo_nombre": "Factura", "total": None,
          "proveedor": None}
ok(sunat.ficha_pdf(_hueca)[:4] == b"%PDF", "un comprobante con huecos no revienta")

# La ficha en pantalla y el PDF salen de la MISMA fuente: si divergen, es
# porque alguien agregó un campo en un solo lado.
_secciones = sunat.campos_ficha(n)
ok([t for t, _ in _secciones] == ["Emisor", "Documento", "Importes"],
   "campos_ficha declara las 3 secciones esperadas")
ok(any(e == "Estado" for _, filas in _secciones for e, _ in filas),
   "la ficha muestra el estado del comprobante")

# ── Credenciales ───────────────────────────────────────────────────────────
print("\n── credenciales ──")
ok(len(sunat._SECRETS_SUNAT) == 5, "declara las 5 credenciales que pide SUNAT")
# El mensaje de error nunca debe arrastrar un secret: las credenciales van
# en el body del POST del token y `requests` las incluye en su repr.
ok("***" not in sunat._mensaje_error(ValueError("error comun")),
   "un error sin secrets se muestra tal cual")
ok(len(sunat._mensaje_error(ValueError("x" * 900))) <= 400,
   "recorta mensajes largos")

# ── Cierre ─────────────────────────────────────────────────────────────────
print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (capa de datos del SIRE Compras)")
