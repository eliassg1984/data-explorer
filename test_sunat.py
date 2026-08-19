"""test_sunat.py — pruebas de la capa de datos del SIRE Compras (sunat.py).

Corre SIN credenciales de SUNAT y SIN red: todo lo que se prueba acá son
funciones puras (validación de período, normalización de columnas, parseo
del archivo de la propuesta) más el modo demo y el render de la ficha PDF.

Las dos cosas que más vale la pena tener cubiertas, porque fallan EN
SILENCIO y con datos que parecen razonables:

  · **El formato numérico.** SUNAT devuelve importes con coma decimal
    (`1.234,56`). Un `pd.to_numeric` directo los convierte en NaN y el
    total del período sale 0,00 sin ningún error a la vista.
  · **El mapeo de columnas.** El layout del archivo lo fija una resolución
    que ha cambiado de encabezados entre versiones. Si un alias deja de
    pegar, la columna desaparece del DataFrame y la vista muestra un total
    incompleto — otra vez, sin excepción.

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
ok(sunat.nombre_tipo_cdp("99") == "99", "código desconocido se muestra crudo")

# ── Formato numérico ───────────────────────────────────────────────────────
print("\n── formato numérico ──")
euro = sunat._a_numero(pd.Series(["1.234,56", "980,00", "1.000.000,10"]))
ok(list(euro) == [1234.56, 980.00, 1000000.10], "coma decimal + punto de miles")
usa = sunat._a_numero(pd.Series(["1,234.56", "980.00", "1234.5"]))
ok(list(usa) == [1234.56, 980.00, 1234.5], "punto decimal + coma de miles")
ok(sunat._a_numero(pd.Series(["12345"]))[0] == 12345, "entero sin separadores")
ok(pd.isna(sunat._a_numero(pd.Series(["N/A"]))[0]), "texto no numérico → NaN")

# ── Mapeo de columnas ──────────────────────────────────────────────────────
print("\n── mapeo de columnas ──")
crudo = pd.DataFrame({
    "Periodo": ["202608"],
    "CAR SUNAT": ["20260000000000000000001"],
    # "Año emisión CDP" va ANTES a propósito: es la trampa que motivó el
    # orden de alias. Un alias suelto "emision" se llevaría esta columna y
    # fecha_emision terminaría siendo el año, en silencio.
    "Año emisión CDP": ["2026"],
    "Fecha de emisión": ["15/08/2026"],
    "Tipo CP/Doc.": ["01"],
    "Serie del CDP": ["F001"],
    "Nro CP o Doc. Nro Inicial (Rango)": ["00001234"],
    "Nro Doc Identidad": ["20100047218"],
    "Apellidos Nombres/ Razón Social": ["PROVEEDOR SAC"],
    "BI Gravado DG": ["1.000,00"],
    "IGV/IPM DG": ["180,00"],
    "Total CP": ["1.180,00"],
    "Columna que no nos interesa": ["x"],
})
norm = sunat.normalizar_columnas(crudo)
ok("ruc_proveedor" in norm.columns, "mapea 'Nro Doc Identidad' → ruc_proveedor")
ok("proveedor" in norm.columns, "mapea 'Apellidos Nombres/ Razón Social'")
ok("base_imponible" in norm.columns, "mapea 'BI Gravado DG'")
ok("igv" in norm.columns, "mapea 'IGV/IPM DG'")
ok("total" in norm.columns, "mapea 'Total CP'")
ok("Columna que no nos interesa" not in norm.columns,
   "descarta las columnas no reconocidas")
ok("fecha_emision" in norm.columns, "mapea 'Fecha de emisión' (con 'de' en medio)")
ok(norm["fecha_emision"].iloc[0] == "15/08/2026",
   "'Año emisión CDP' NO le roba la columna a fecha_emision")
ok(norm["ruc_proveedor"].iloc[0] == "20100047218",
   "'Nro Doc Identidad' NO se lo lleva 'periodo' ni otro alias previo")
ok(sunat.normalizar_columnas(None).empty, "None → df vacío con las columnas")
ok(sunat.normalizar_columnas(pd.DataFrame()).empty, "df vacío no revienta")

# ── Parseo del archivo de la propuesta ─────────────────────────────────────
print("\n── parseo de la propuesta ──")
csv = (
    "Periodo,Fecha de emisión,Tipo CP/Doc.,Serie del CDP,Nro CP o Doc.,"
    "Nro Doc Identidad,Apellidos Nombres/ Razón Social,BI Gravado DG,"
    "IGV/IPM DG,Total CP\n"
    "202608,15/08/2026,01,F001,00001234,20100047218,PROVEEDOR SAC,"
    "1000.00,180.00,1180.00\n"
    "202608,20/08/2026,07,F001,00000045,20100047218,PROVEEDOR SAC,"
    "-100.00,-18.00,-118.00\n"
)
df = sunat.parsear_propuesta(csv)
ok(len(df) == 2, "parsea las 2 filas del csv")
ok(df["total"].sum() == 1062.0, "suma los importes (la NC resta)")
ok(df["documento"].iloc[0] == "F001-00001234", "arma serie-número")
ok(df["tipo_nombre"].iloc[0] == "Factura", "resuelve el nombre del tipo")
ok(df["tipo_nombre"].iloc[1] == "Nota de crédito", "07 → Nota de crédito")
ok(str(df["fecha_emision"].iloc[0].date()) == "2026-08-15",
   "parsea la fecha como dd/mm/yyyy, no mm/dd")

# El txt (codTipoArchivo=0) viene separado por pipe: el delimitador se
# detecta, no se asume.
pipe = csv.replace(",", "|")
ok(len(sunat.parsear_propuesta(pipe)) == 2, "también parsea el txt con pipe")
ok(sunat.parsear_propuesta("").empty, "texto vacío → df vacío")
ok(sunat.parsear_propuesta("   ").empty, "texto en blanco → df vacío")

# ── ZIP que devuelve `archivoreporte` ──────────────────────────────────────
print("\n── descompresión del reporte ──")
import io
import zipfile

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("20100047218-CPF-202608-01.txt", "hola|mundo")
ok(sunat._extraer_texto_zip(buf.getvalue()) == "hola|mundo",
   "saca el txt de adentro del zip")
ok(sunat._extraer_texto_zip(b"no soy un zip") == "no soy un zip",
   "si no es zip, lo trata como texto plano (SUNAT lo hace con reportes chicos)")
ok(sunat._extraer_texto_zip(b"") == "", "contenido vacío → texto vacío")

# ── Modo demo ──────────────────────────────────────────────────────────────
print("\n── modo demo ──")
d1 = sunat._datos_demo("202608")
d2 = sunat._datos_demo("202608")
ok(d1["total"].sum() == d2["total"].sum(),
   "es determinista entre llamadas (crc32, no hash())")
ok(sunat._datos_demo("202607")["total"].sum() != d1["total"].sum(),
   "cambia con el período")
ok(not d1.empty and len(d1) == 48, "genera las filas pedidas")
ok(set(d1["fecha_emision"].dt.month) == {8}, "las fechas caen dentro del mes")
ok((d1.loc[d1["tipo_cdp"] == "07", "total"] < 0).all(),
   "las notas de crédito restan")
faltan = {"documento", "tipo_nombre", "ruc_proveedor", "proveedor", "total",
          "igv", "base_imponible", "car"} - set(d1.columns)
ok(not faltan, f"trae las columnas que la vista consume (faltan: {faltan})")
ok(sunat._datos_demo("202602")["fecha_emision"].dt.day.max() <= 29,
   "respeta los días del mes (febrero)")

# ── Ficha PDF ──────────────────────────────────────────────────────────────
print("\n── ficha PDF ──")
pdf = sunat.ficha_pdf(d1.iloc[0])
ok(pdf[:4] == b"%PDF", "devuelve un PDF de verdad")
ok(len(pdf) > 1500, "el PDF tiene contenido, no es una página en blanco")
# Una fila con huecos no debe reventar: SUNAT deja campos vacíos (moneda,
# fecha de vencimiento) según el tipo de comprobante.
hueca = {"documento": "F001-1", "tipo_cdp": "01", "total": None,
         "proveedor": None}
ok(sunat.ficha_pdf(hueca)[:4] == b"%PDF", "un comprobante con huecos no revienta")

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
