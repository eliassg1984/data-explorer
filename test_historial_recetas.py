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

3. «CAMBIOS EN RECETAS» (regla #707): los precios de la auditoría
   juntados, la fecha de una edición de plato, el armado de la lista para
   la pieza (con y sin los precios de la auditoría) y que el `.js` lea lo
   que Python manda.

4. El CABLEADO: que `app.py` saque la foto y que «Ver cambios» de Costo de
   Carta llegue a Python.

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
            "P.UNIT COSTO": 0.1, "UNID COSTO": "GRAMOS",
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


# ── Las ediciones de cada receta de plato («Cambios en recetas», #707) ─────

eds = {e["rv"]: e for e in hr.ediciones_plato(_antes, _despues)}
igual(sorted(eds), ["R1", "R2", "R3", "R4"],
      "una edición por receta que cambió (R5 sigue igual: el plato que se "
      "fue a R4 no es un cambio de R5)")
igual((eds["R4"]["nueva"], eds["R3"]["quitada"], eds["R1"]["nueva"], eds["R1"]["quitada"]),
      (True, True, False, False), "nueva y quitada")
igual(sorted((x[0], x[2], x[3]) for x in eds["R1"]["lineas"]),
      [("I1", 100.0, 120.0), ("I2", 20.0, None), ("I6", None, 7.0)],
      "las líneas de R1: la cantidad, la quitada y la agregada (la renumerada no)")
igual((round(eds["R1"]["antes"], 6), round(eds["R1"]["despues"], 6),
       round(eds["R1"]["delta"], 6)), (12.5, 13.2, 0.7),
      "el costo de antes y de después, con los precios de hoy")
igual((eds["R1"]["usr"], eds["R3"]["usr"], eds["R1"]["platos"], eds["R2"]["platos"]),
      ("DOS", "UNO", ["P1"], ["P2", "P3"]),
      "quién guardó (el de la foto vieja si se quitó) y qué platos la llevan")
igual([(x[0], x[2], x[3]) for x in eds["R2"]["lineas"]], [("I4", 2.0, 3.0)],
      "el segundo I4 se compara con el segundo, aunque la receta la lleven dos platos")
_caro = _despues.copy()
_caro["P.UNIT COSTO"] = 0.5
igual(sorted(e["rv"] for e in hr.ediciones_plato(_antes[_antes["COD RV"] == "R5"],
                                                 _caro[_caro["COD RV"] == "R5"])), [],
      "una suba de precio sola no es una edición de la receta")
igual(hr.precios_de_fotos(_antes, _despues),
      {"P1": [("En el Local", 30.0, 32.0), ("Delivery", 30.0, 32.0),
              ("Para Llevar", 30.0, 32.0), ("Pedidos Ya", 30.0, 32.0)]},
      "los precios que cambiaron, por plato y canal (el plato nuevo no cuenta)")


# ── «Cambios en recetas» (graficos/recetas_cambios.py, regla #707) ────────
import logging  # noqa: E402
logging.getLogger("streamlit").setLevel(logging.ERROR)
import datetime as _dt  # noqa: E402
import graficos.recetas_cambios as rc  # noqa: E402

_t0 = pd.Timestamp("2026-10-12 13:08")
_aud = pd.DataFrame([
    # Dos guardados del mismo plato a 20 minutos: UN cambio, del primer
    # «antes» al último «después».
    {"t": _t0, "usr": "ANA", "pantalla": "PRODUCTOS", "cod": "P1", "guardado": "1",
     "campos": {"Precio Venta Canal 1": ("19", "21"), "Precio Venta Canal 3": ("19", "20")}},
    {"t": _t0 + pd.Timedelta(minutes=20), "usr": "ANA", "pantalla": "PRODUCTOS", "cod": "P1",
     "guardado": "2", "campos": {"Precio Venta Canal 1": ("21", "22")}},
    # El mismo plato tres horas después: otro cambio.
    {"t": _t0 + pd.Timedelta(hours=3), "usr": "LUIS", "pantalla": "PRODUCTOS", "cod": "P1",
     "guardado": "3", "campos": {"Precio Venta Canal 1": ("22", "21")}},
    # Un artículo del Almacén y el descargo de un plato: no son precios de venta.
    {"t": _t0, "usr": "ANA", "pantalla": "ARTICULOS Y PRECIOS", "cod": "A1", "guardado": "4",
     "campos": {"Factor": ("1000", "1")}},
    {"t": _t0, "usr": "ANA", "pantalla": "PRODUCTOS", "cod": "P2", "guardado": "5",
     "campos": {"Tipo Descargo": ("receta", "directo")}},
    # Ida y vuelta en el mismo rato: no cambió.
    {"t": _t0, "usr": "ANA", "pantalla": "PRODUCTOS", "cod": "P3", "guardado": "6",
     "campos": {"Precio Venta Canal 2": ("10", "12")}},
    {"t": _t0 + pd.Timedelta(minutes=5), "usr": "ANA", "pantalla": "PRODUCTOS", "cod": "P3",
     "guardado": "7", "campos": {"Precio Venta Canal 2": ("12", "10")}},
])
_pr = rc.precios_auditoria(_aud)
igual([(p["cod"], p["usr"], p["canales"]) for p in _pr],
      [("P1", "ANA", [("En el Local", 19.0, 22.0), ("Para Llevar", 19.0, 20.0)]),
       ("P1", "LUIS", [("En el Local", 22.0, 21.0)])],
      "precios · juntados a menos de 2 h, por canal; sin los que no son precios ni los de ida y vuelta")
igual(rc.precios_auditoria(None), [], "precios · sin auditoría, ninguno")
_crudo = pd.DataFrame({"FECHA": [_t0, _t0], "PANTALLA": ["PRODUCTOS"] * 2, "CODIGO": ["P9", "P8"],
                       "CAMPO": ["Precio Venta Canal 1"] * 2, "ANTES": ["", "46"],
                       "DESPUES": ["30", "46.0"], "CORRELATIVO": ["1", "2"], "USUARIO": ["A", "A"]})
igual(len(sr_cambios := __import__("simulador_receta").cambios_auditoria(_crudo)), 0,
      "precios · un producto que nace con su precio y «46» → «46.0» no son cambios")

_ta, _td = pd.Timestamp("2026-10-21 03:00"), pd.Timestamp("2026-10-22 03:00")
igual(rc.fecha_plato({"fmodif": pd.Timestamp("2026-10-21 19:56")}, _ta, _td),
      (pd.Timestamp("2026-10-21 19:56"), False), "plato · la hora del guardado, si cae entre las fotos")
igual(rc.fecha_plato({"fmodif": pd.Timestamp("2026-01-08 14:46")}, _ta, _td), (_td, True),
      "plato · un guardado viejo (otra edición en el medio) va con la hora de la foto, aproximada")
igual(rc.fecha_plato({"fmodif": None}, _ta, _td), (_td, True), "plato · sin fecha, la de la foto")

_carta = {"P1": ("Plato uno", "Alimentos › Fondos", [[3.0, 30.0, 24.3]] * 5),
          "P9": ("Propina", "Otros", [[None, 489.0, None]] * 5)}
_par = {"ediciones": hr.ediciones_plato(_antes, _despues), "precios": hr.precios_de_fotos(_antes, _despues)}
_items = rc.armar(_dt.date(2026, 10, 1), _dt.date(2026, 10, 31), [], _pr, [(_ta, _td, _par)],
                  _carta, _despues, None, {})
igual(sorted({x["tipo"] for x in _items}), ["plato", "precio"], "armar · recetas de plato y precios")
igual(sum(x["tipo"] == "precio" for x in _items), 2,
      "armar · con la auditoría, los precios de las fotos no se suman (serían los mismos dos veces)")
_sin = rc.armar(_dt.date(2026, 10, 1), _dt.date(2026, 10, 31), [], None, [(_ta, _td, _par)],
                _carta, _despues, None, {})
igual([(x["cods"], x["usr"]) for x in _sin if x["tipo"] == "precio"], [(["P1"], "")],
      "armar · sin la auditoría, los precios salen de las fotos, sin usuario")
igual([x["t"] for x in _items], sorted((x["t"] for x in _items), reverse=True),
      "armar · del más nuevo al más viejo")
igual(len(rc.armar(_dt.date(2026, 11, 1), _dt.date(2026, 11, 30), [], _pr, [(_ta, _td, _par)],
                   _carta, _despues, None, {})), 0, "armar · fuera del rango, nada")
_p9 = rc._item_precio("P9", _t0, "A", [("En el Local", 400.0, 489.0)], _carta)
ok(_p9["sinCosto"] and not rc._item_precio("P1", _t0, "A", [("En el Local", 30.0, 32.0)], _carta)["sinCosto"],
   "armar · Propina, sin costo en la carta, va marcada (la pieza la esconde)")

_js = (RAIZ / "graficos" / "recetas_cambios.js").read_text(encoding="utf-8")
_claves = set().union(*(x.keys() for x in _items + [_p9]))
_faltan = sorted(c for c in _claves if c not in ("id",) and f".{c}" not in _js)
igual(_faltan, [], "el .js lee todo lo que Python manda en cada cambio")
ok(all(f"data.{c}" in _js or f"d.{c}" in _js for c in ("items", "platos", "foco", "fotos",
                                                         "preciosDeFotos", "grande", "divisor")),
   "el .js lee lo que Python manda en `data`")


# ── 3. El cableado ─────────────────────────────────────────────────────────

_app = (RAIZ / "app.py").read_text(encoding="utf-8")
ok("historial_recetas.revisar_en_segundo_plano(" in _app,
   "app.py saca la foto",
   "sin la llamada, nadie fotografía el parquet y el historial no crece")
_carta_js = (RAIZ / "graficos" / "carta_costeada.js").read_text(encoding="utf-8")
_carta_py = (RAIZ / "graficos" / "carta_costeada.py").read_text(encoding="utf-8")
ok("enviar('cambios'" in _carta_js and "on_cambios_change=" in _carta_py
   and 'ss.pop("_rec_cambios_ir"' in _carta_py,
   "«Ver cambios» de Costo de Carta llega a Python y pide la corrida completa del salto")


print()
if _fallos:
    print(f"❌ {len(_fallos)} fallo(s):")
    for f in _fallos:
        print(f"   · {f}")
    sys.exit(1)
print("✅ Todo OK (historial de recetas)")
