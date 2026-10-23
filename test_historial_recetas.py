"""test_historial_recetas.py — la FOTO diaria de las recetas de venta
(`historial_recetas.py`, regla #705).

Tres cosas, sin secrets, sin red y sin navegador:

1. Las FOTOS contra un R2 de mentira: el nombre sale del LastModified en
   UTC, la copia pide el ETag que se leyó, la segunda vez no copia, un
   error que no es «no existe» no se toma por «no existe», un archivo que
   falla no impide los demás, el listado pagina, y el hilo de la app sale
   como mucho una vez cada `CADA_SEGUNDOS`.

2. La COMPARACIÓN sobre dos fotos de mentira con cada caso: receta nueva y
   quitada, insumo agregado y quitado (con la renumeración de `ITEM RV`
   que deja al quitar una línea), el mismo insumo dos veces en una receta,
   la cantidad que se mueve en todos los canales (sale UNA fila) o sólo en
   delivery, cómo se descarga, una receta compartida por dos platos
   (cuenta una vez), el precio, el plato que pasa a otra receta, plato
   nuevo y quitado. Códigos y nombres inventados — el repo es público.

3. El CABLEADO: que `app.py` saque la foto.

Se ejecuta solo:  python test_historial_recetas.py
"""

import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import historial_recetas as hr  # noqa: E402

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


# ── 1. Las fotos ───────────────────────────────────────────────────────────

class ErrorR2(Exception):
    def __init__(self, codigo):
        super().__init__(codigo)
        self.response = {"Error": {"Code": codigo}}


class R2DeMentira:
    def __init__(self, objetos, error_head=None):
        self.objetos = dict(objetos)   # clave -> (LastModified, ETag)
        self.copias = []
        self.error_head = error_head

    def head_object(self, Bucket, Key):
        if self.error_head and Key.startswith(hr.PREFIJO):
            raise ErrorR2(self.error_head)
        if Key not in self.objetos:
            raise ErrorR2("404")
        fecha, etag = self.objetos[Key]
        return {"LastModified": fecha, "ETag": etag}

    def copy_object(self, Bucket, Key, CopySource, CopySourceIfMatch):
        self.copias.append((Key, CopySource["Key"], CopySourceIfMatch))
        self.objetos[Key] = self.objetos[CopySource["Key"]]

    def list_objects_v2(self, Bucket, Prefix, ContinuationToken=None):
        claves = sorted(k for k in self.objetos if k.startswith(Prefix))
        ini = int(ContinuationToken or 0)
        pagina = claves[ini:ini + 2]
        resp = {"Contents": [{"Key": k} for k in pagina],
                "IsTruncated": ini + 2 < len(claves)}
        if resp["IsTruncated"]:
            resp["NextContinuationToken"] = str(ini + 2)
        return resp


_ts = pd.Timestamp("2026-10-22 08:00:09", tz="UTC")
igual(hr.clave_foto("recetaventa.parquet", _ts),
      "_historial/recetaventa/20261022T080009Z.parquet",
      "la foto se nombra con el LastModified en UTC")
igual(hr.clave_foto("recetaventa.parquet",
                    pd.Timestamp("2026-10-22 03:00:09", tz="America/Lima")),
      "_historial/recetaventa/20261022T080009Z.parquet",
      "una hora de Lima se pasa a UTC antes de nombrar")
igual(hr.fecha_de_clave("_historial/recetaventa/20261022T080009Z.parquet"), _ts,
      "el instante se lee de vuelta del nombre")

r2 = R2DeMentira({"recetaventa.parquet": (_ts, '"abc"')})
_clave = hr.guardar_foto(r2, "b", "recetaventa.parquet")
igual(_clave, "_historial/recetaventa/20261022T080009Z.parquet",
      "la primera vez saca la foto")
igual(r2.copias, [(_clave, "recetaventa.parquet", '"abc"')],
      "copia DENTRO de R2 pidiendo el ETag que leyó")
igual(hr.guardar_foto(r2, "b", "recetaventa.parquet"), None,
      "la misma versión no se copia dos veces")
igual(len(r2.copias), 1, "… y no hubo segunda copia")

r2.objetos["recetaventa.parquet"] = (_ts + pd.Timedelta(days=1), '"def"')
hr.guardar_foto(r2, "b", "recetaventa.parquet")
igual(len(r2.copias), 2, "una versión nueva sí saca otra foto")

_negado = R2DeMentira({"recetaventa.parquet": (_ts, '"abc"')}, error_head="403")
try:
    hr.guardar_foto(_negado, "b", "recetaventa.parquet")
    ok(False, "un 403 no se toma por «la foto no existe»", "copió igual")
except ErrorR2:
    ok(not _negado.copias, "un 403 no se toma por «la foto no existe»")
igual(hr.asegurar_fotos(_negado, "b"), [],
      "asegurar_fotos no lanza: el error se informa y se sigue")
igual(hr.asegurar_fotos(R2DeMentira({}), "b"), [],
      "sin el parquet en R2 tampoco lanza")

_muchas = R2DeMentira({hr.clave_foto("recetaventa.parquet",
                                     _ts + pd.Timedelta(days=d)): (_ts, "")
                       for d in (3, 0, 4, 1, 2)})
igual([c for _, c in hr.fotos(_muchas, "b")],
      [hr.clave_foto("recetaventa.parquet", _ts + pd.Timedelta(days=d))
       for d in range(5)],
      "el listado junta todas las páginas, de la más vieja a la más nueva")

hr._REVISION["ultima"] = None
_vacio = R2DeMentira({})
ok(hr.revisar_en_segundo_plano(_vacio, "b", ahora=1000.0),
   "la primera corrida del proceso lanza el hilo")
ok(not hr.revisar_en_segundo_plano(_vacio, "b", ahora=1000.0 + hr.CADA_SEGUNDOS - 1),
   "antes de CADA_SEGUNDOS no vuelve a preguntar")
ok(hr.revisar_en_segundo_plano(_vacio, "b", ahora=1000.0 + hr.CADA_SEGUNDOS),
   "pasado CADA_SEGUNDOS, sí")
hr._REVISION["ultima"] = None


# ── 2. La comparación ──────────────────────────────────────────────────────

def _linea(plato, nombre, rv, item, ins, cant, precio=30.0, **extra):
    fila = {"COD PLATO": plato, "NOMB PLATO": nombre, "ITEM VENTA ACTIVO": "ACTIV",
            "COD RV": rv, "NOMB RV": f"Receta {rv}", "ITEM RV": item,
            "COD INS": ins, "INS RV": f"Insumo {ins}", "CANTIDAD": cant,
            "DESCARG": "SI", "T DESCARG": "PRODUCTO", "SUBALM INS": "COCINA",
            "FECH MODIF": pd.Timestamp("2026-01-01"), "USUARIO REG": "UNO",
            "P.VENTA SALON": precio, "P.VENTA DELIV": precio,
            "P.VENTA LLEVAR": precio, "P.VENTA RAPPI": 0.0, "P.VENTA 5": precio}
    for c in hr.CANT_CANALES:
        fila[c] = cant
    fila.update(extra)
    return fila


_antes = pd.DataFrame([
    # R1: tres líneas; se quita la del medio (la siguiente se renumera)
    _linea("P1", "Plato uno", "R1", "001", "I1", 100.0),
    _linea("P1", "Plato uno", "R1", "002", "I2", 20.0),
    _linea("P1", "Plato uno", "R1", "003", "I3", 5.0),
    # R2: compartida por dos platos; el mismo insumo dos veces
    _linea("P2", "Plato dos", "R2", "001", "I4", 1.0),
    _linea("P2", "Plato dos", "R2", "002", "I4", 2.0),
    _linea("P3", "Plato tres", "R2", "001", "I4", 1.0),
    _linea("P3", "Plato tres", "R2", "002", "I4", 2.0),
    # R3: se va entera, y su plato también
    _linea("P4", "Plato cuatro", "R3", "001", "I5", 1.0),
    # R5: el plato P6 pasa de R5 a R4 (R5 sigue para P7)
    _linea("P6", "Plato seis", "R5", "001", "I8", 1.0),
    _linea("P7", "Plato siete", "R5", "001", "I8", 1.0),
])
_despues = pd.DataFrame([
    _linea("P1", "Plato uno", "R1", "001", "I1", 120.0, precio=32.0,
           **{"FECH MODIF": pd.Timestamp("2026-10-21 12:00"), "USUARIO REG": "DOS"}),
    _linea("P1", "Plato uno", "R1", "002", "I3", 5.0, precio=32.0,
           **{"FECH MODIF": pd.Timestamp("2026-10-21 12:00"), "USUARIO REG": "DOS"}),
    _linea("P1", "Plato uno", "R1", "003", "I6", 7.0, precio=32.0,
           **{"FECH MODIF": pd.Timestamp("2026-10-21 12:00"), "USUARIO REG": "DOS"}),
    _linea("P2", "Plato dos", "R2", "001", "I4", 1.0),
    _linea("P2", "Plato dos", "R2", "002", "I4", 3.0,
           **{"CANT DELIV": 2.0, "T DESCARG": "INSUMO"}),
    _linea("P3", "Plato tres", "R2", "001", "I4", 1.0),
    _linea("P3", "Plato tres", "R2", "002", "I4", 3.0,
           **{"CANT DELIV": 2.0, "T DESCARG": "INSUMO"}),
    _linea("P5", "Plato cinco", "R4", "001", "I7", 2.0),
    _linea("P6", "Plato seis", "R4", "001", "I7", 2.0),
    _linea("P7", "Plato siete", "R5", "001", "I8", 1.0),
])

cb = hr.cambios(_antes, _despues)
igual(tuple(cb.columns), hr.COLUMNAS_CAMBIOS, "las columnas, por nombre")


def _que(que, col):
    return list(cb.loc[cb["QUE"] == que, col])


igual(_que("Receta nueva", "COD RV"), ["R4"], "receta nueva")
igual(_que("Receta quitada", "COD RV"), ["R3"], "receta quitada")
igual(_que("Insumo quitado", "COD INS"), ["I2"],
      "quitar la línea del medio es UN insumo quitado, no tres cambios")
igual(_que("Insumo agregado", "COD INS"), ["I6"], "insumo agregado")
_r1 = cb[(cb["COD RV"] == "R1") & (cb["NIVEL"] == "Línea")]
igual(sorted(zip(_r1["QUE"], _r1["COD INS"], _r1["CAMPO"])),
      [("Cambio en la línea", "I1", "CANTIDAD"),
       ("Insumo agregado", "I6", "CANTIDAD"),
       ("Insumo quitado", "I2", "CANTIDAD")],
      "la cantidad que cambió en todos los canales sale UNA vez, como CANTIDAD")
_i1 = cb[cb["COD INS"] == "I1"].iloc[0]
igual((_i1["ANTES"], _i1["DESPUES"], _i1["USUARIO REG"]), (100.0, 120.0, "DOS"),
      "antes, después y quién guardó la receta")

# El segundo I4 pasa de 2 a 3 en todos los canales menos delivery, que
# queda en 2: delivery NO se movió igual que CANTIDAD, pero tampoco se
# movió — no sale. Sí sale cómo se descarga.
_r2 = cb[cb["COD RV"] == "R2"]
igual(sorted(zip(_r2["CAMPO"], _r2["ANTES"], _r2["DESPUES"])),
      [("CANTIDAD", 2.0, 3.0), ("T DESCARG", "PRODUCTO", "INSUMO")],
      "la receta compartida por dos platos cuenta una vez y el segundo I4 se "
      "compara con el segundo")
ok(not ((cb["COD RV"] == "R2") & (cb["COD INS"] == "I4") & (cb["ANTES"] == 1.0)).any(),
   "el primer I4, igual, no sale")

_pl = cb[cb["NIVEL"] == "Plato"]
igual(sorted(_pl.loc[_pl["QUE"] == "Plato nuevo", "COD PLATO"]), ["P5"], "plato nuevo")
igual(sorted(_pl.loc[_pl["QUE"] == "Plato quitado", "COD PLATO"]), ["P4"], "plato quitado")
igual(sorted(_pl.loc[(_pl["COD PLATO"] == "P1"), "CAMPO"]),
      sorted(["P.VENTA SALON", "P.VENTA DELIV", "P.VENTA LLEVAR", "P.VENTA 5"]),
      "los precios del plato que cambiaron (Rappi, en 0 los dos, no)")
_p6 = _pl[_pl["COD PLATO"] == "P6"]
igual(list(zip(_p6["CAMPO"], _p6["ANTES"], _p6["DESPUES"])), [("COD RV", "R5", "R4")],
      "el plato que pasa a otra receta")
ok(_pl["FECH MODIF"].isna().all(),
   "un cambio de plato no lleva la fecha de la receta (no es de ella)")

igual(len(hr.cambios(_antes, _antes.copy())), 0, "sin cambios, cero filas")
_con_nan = _antes.copy()
_con_nan["SUBALM INS"] = None
igual(len(hr.cambios(_con_nan, _con_nan.copy())), 0, "un vacío igual a otro vacío no es cambio")


# ── 3. El cableado ─────────────────────────────────────────────────────────

_app = (RAIZ / "app.py").read_text(encoding="utf-8")
ok("historial_recetas.revisar_en_segundo_plano(" in _app,
   "app.py saca la foto",
   "sin la llamada, nadie fotografía el parquet y el historial no crece")


print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (historial de recetas)")
