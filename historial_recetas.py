"""
historial_recetas — una FOTO de las recetas de venta por cada versión del
parquet, para saber qué cambió y cuándo (regla #705).

POR QUÉ EXISTE
--------------
El POS no guarda el pasado de una receta de PLATO. El de una receta BASE sí
(`ALMACEN.DBO.MRECETABASE_LOG`, el estado de antes de cada guardado) y el
de un precio de venta también (`INFSEGURIDAD.DBO.MMOVIMIENTO`, pantalla
«PRODUCTOS», «Precio Venta Canal 1..5», desde 2021). Pero
`MRECETAVENTA`/`DRECETAVENTA` sólo tienen el estado de hoy, con la fecha y
el usuario del ÚLTIMO guardado: sin triggers, sin CDC, y ningún
procedimiento escribe un log (revisado el 2026-10-22). Y el extractor
REESCRIBE `recetaventa.parquet` cada madrugada: la versión de ayer se pierde
— R2 no versiona.

LA FOTO
-------
`recetaventa.parquet` ya trae lo que hace falta comparar: la receta línea
por línea (insumo, cantidad por canal, cómo se descarga), los cinco
precios de venta del plato y `FECH MODIF`/`USUARIO REG` de la receta. La
foto es una COPIA de ese archivo dentro de R2 (`copy_object`: no se baja
nada), en `_historial/recetaventa/<LastModified UTC>.parquet`. Una por
versión del parquet: la de las 03:00 y la de cada refresco a pedido.

`CopySourceIfMatch` con el ETag leído asegura que la foto es la versión que
dice su nombre aunque el extractor reescriba el archivo en ese instante
(medido en R2: con otro ETag responde PreconditionFailed). Y antes de
copiar se pregunta si la foto ya existe — R2 no respeta `IfNoneMatch` en
una copia (medido) —, así que dos procesos que la saquen a la vez copian
lo mismo dos veces, nada peor.

QUIÉN LA SACA
-------------
La app, al arrancar una corrida (`revisar_en_segundo_plano`, desde
`app.py`), cada `CADA_SEGUNDOS` por proceso y en un hilo aparte: dos
`head_object` y, si hay versión nueva, una copia. Sin nada que mantener en
el servidor del restaurante. El hueco: un día en que nadie abre la app, el
parquet de ese día se pisa sin foto. El cambio no se pierde —sale en la foto
siguiente, y `FECH MODIF` dice cuándo se guardó la receta—; lo que se
pierde es un estado intermedio, si alguien editó dos días seguidos.
`herramientas/foto_recetas.py` hace lo mismo desde una consola y es lo que
se programaría en una máquina si ese hueco llegara a importar.

LA COMPARACIÓN
--------------
`cambios(antes, despues)` es pandas puro: una fila por cosa que cambió, al
nivel de la RECETA (nueva, quitada; un insumo agregado o quitado; una
cantidad, cómo se descarga) y del PLATO (nuevo, quitado, su receta, su
nombre, activo, sus precios). Una receta la comparten varios platos (57),
así que sus líneas se cuentan una vez por `COD RV`. Lo vigila
`test_historial_recetas.py`.
"""
from __future__ import annotations

import io
import sys
import threading
import time

import pandas as pd

VERSION = 1
"""La versión de `ediciones_plato` y `precios_de_fotos`: «Cambios en
recetas» guarda en disco lo que cambió entre cada par de fotos, sin
caducar. Tocar la cuenta es subirla."""

ARCHIVOS = ("recetaventa.parquet",)
"""Los parquets que se fotografían. Sumar otro es sumarlo acá."""

PREFIJO = "_historial/"
CADA_SEGUNDOS = 1800
"""Cada cuánto, como mucho, un proceso de la app vuelve a preguntar."""

FORMATO_FECHA = "%Y%m%dT%H%M%SZ"

CAMPOS_PLATO = ("NOMB PLATO", "ITEM VENTA ACTIVO", "COD RV",
                "P.VENTA SALON", "P.VENTA DELIV", "P.VENTA LLEVAR",
                "P.VENTA RAPPI", "P.VENTA 5")
CANT_CANALES = ("CANT LOCAL", "CANT DELIV", "CANT LLEVAR", "CANT RAPPI",
                "CANT 5")
CAMPOS_LINEA = ("CANTIDAD",) + CANT_CANALES + ("DESCARG", "T DESCARG",
                                                "SUBALM INS")

_USADAS = ("COD PLATO", "NOMB PLATO", "COD RV", "NOMB RV", "COD INS", "INS RV",
           "FECH MODIF", "USUARIO REG", "P.UNIT COSTO", "UNID COSTO") + CAMPOS_PLATO + CAMPOS_LINEA

COLUMNAS_CAMBIOS = ("NIVEL", "QUE", "COD PLATO", "NOMB PLATO", "COD RV",
                    "NOMB RV", "COD INS", "INS RV", "CAMPO", "ANTES",
                    "DESPUES", "FECH MODIF", "USUARIO REG")


# ── Las fotos en R2 ──────────────────────────────────────────────────────

def clave_foto(archivo, ultima_modificacion):
    """Dónde va la foto de la versión de `archivo` modificada en ese
    instante: `_historial/recetaventa/20261022T080009Z.parquet`."""
    t = pd.Timestamp(ultima_modificacion)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    base = archivo[:-len(".parquet")] if archivo.endswith(".parquet") else archivo
    return f"{PREFIJO}{base}/{t.strftime(FORMATO_FECHA)}.parquet"


def fecha_de_clave(clave):
    """El instante de la versión fotografiada (UTC), leído del nombre."""
    nombre = clave.rsplit("/", 1)[-1].removesuffix(".parquet")
    return pd.Timestamp(pd.to_datetime(nombre, format=FORMATO_FECHA, utc=True))


def _no_existe(error):
    codigo = str(getattr(error, "response", {}).get("Error", {}).get("Code", ""))
    return codigo in ("404", "NoSuchKey", "NotFound")


def guardar_foto(s3, bucket, archivo):
    """Copia la versión vigente de `archivo` a su foto. Devuelve la clave
    de la foto si la sacó, o None si ya existía."""
    fuente = s3.head_object(Bucket=bucket, Key=archivo)
    clave = clave_foto(archivo, fuente["LastModified"])
    try:
        s3.head_object(Bucket=bucket, Key=clave)
        return None
    except Exception as e:
        if not _no_existe(e):
            raise
    s3.copy_object(Bucket=bucket, Key=clave,
                   CopySource={"Bucket": bucket, "Key": archivo},
                   CopySourceIfMatch=fuente["ETag"])
    return clave


def asegurar_fotos(s3, bucket, archivos=ARCHIVOS):
    """La foto de la versión vigente de cada archivo. Un archivo que falla
    no impide los demás. Devuelve las claves nuevas."""
    nuevas = []
    for archivo in archivos:
        try:
            clave = guardar_foto(s3, bucket, archivo)
        except Exception as e:
            print(f"historial_recetas: sin foto de {archivo}: {e}",
                  file=sys.stderr)
            continue
        if clave:
            nuevas.append(clave)
    return nuevas


_REVISION = {"ultima": None}
_CANDADO = threading.Lock()


def revisar_en_segundo_plano(s3, bucket, ahora=None):
    """Lanza `asegurar_fotos` en un hilo si este proceso no lo hizo en los
    últimos `CADA_SEGUNDOS`. No bloquea la corrida ni lanza nunca. Devuelve
    True si lanzó el hilo."""
    ahora = time.monotonic() if ahora is None else ahora
    with _CANDADO:
        ultima = _REVISION["ultima"]
        if ultima is not None and ahora - ultima < CADA_SEGUNDOS:
            return False
        _REVISION["ultima"] = ahora
    threading.Thread(target=asegurar_fotos, args=(s3, bucket),
                     name="historial_recetas", daemon=True).start()
    return True


def fotos(s3, bucket, archivo=ARCHIVOS[0]):
    """Las fotos de `archivo`, de la más vieja a la más nueva:
    [(instante UTC, clave)]."""
    prefijo = clave_foto(archivo, pd.Timestamp(0, tz="UTC")).rsplit("/", 1)[0] + "/"
    claves, token = [], None
    while True:
        pedido = {"Bucket": bucket, "Prefix": prefijo}
        if token:
            pedido["ContinuationToken"] = token
        resp = s3.list_objects_v2(**pedido)
        claves += [o["Key"] for o in resp.get("Contents", [])
                   if o["Key"].endswith(".parquet")]
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return sorted((fecha_de_clave(c), c) for c in claves)


def leer_foto(s3, bucket, clave):
    cuerpo = s3.get_object(Bucket=bucket, Key=clave)["Body"].read()
    return pd.read_parquet(io.BytesIO(cuerpo))


# ── La comparación (pura) ────────────────────────────────────────────────

def _igual(a, b):
    a_vacio = a is None or (not isinstance(a, str) and pd.isna(a))
    b_vacio = b is None or (not isinstance(b, str) and pd.isna(b))
    if a_vacio or b_vacio:
        return a_vacio and b_vacio
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(a), abs(b))
    return str(a).strip() == str(b).strip()


def _valor(fila, campo):
    v = fila.get(campo)
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    return v


def _lineas(df):
    """Una fila por línea de receta (no por plato), con su identidad:
    receta + insumo + cuántas veces apareció antes ese insumo en la receta
    (hay recetas con el mismo insumo dos veces). `ITEM RV` no sirve de
    identidad: se renumera al quitar una línea."""
    lin = (df.drop_duplicates(["COD RV", "ITEM RV"])
             .sort_values(["COD RV", "ITEM RV"], kind="stable").copy())
    lin["_VEZ"] = lin.groupby(["COD RV", "COD INS"]).cumcount()
    return _por(lin, ["COD RV", "COD INS", "_VEZ"])


def _por(df, claves):
    """{clave: fila como dict}. Con dicts y no con `.loc` fila por fila:
    sobre la foto de verdad (2.618 filas), 1,3 s contra 8. Y sólo con las
    columnas que se miran: con las 53 del parquet, `to_dict` se llevaba 2,5."""
    usadas = set(_USADAS) | set(claves)
    filas = df[[c for c in df.columns if c in usadas]].to_dict("records")
    if len(claves) == 1:
        return {f[claves[0]]: f for f in filas}
    return {tuple(f[c] for c in claves): f for f in filas}


def _fila(nivel, que, ref, campo=None, antes=None, despues=None, receta=None):
    receta = ref if receta is None else receta
    return {
        "NIVEL": nivel, "QUE": que,
        "COD PLATO": _valor(ref, "COD PLATO") if nivel == "Plato" else None,
        "NOMB PLATO": _valor(ref, "NOMB PLATO") if nivel == "Plato" else None,
        "COD RV": _valor(ref, "COD RV"), "NOMB RV": _valor(ref, "NOMB RV"),
        "COD INS": _valor(ref, "COD INS") if nivel == "Línea" else None,
        "INS RV": _valor(ref, "INS RV") if nivel == "Línea" else None,
        "CAMPO": campo, "ANTES": antes, "DESPUES": despues,
        "FECH MODIF": _valor(receta, "FECH MODIF") if nivel != "Plato" else None,
        "USUARIO REG": _valor(receta, "USUARIO REG") if nivel != "Plato" else None,
    }


def cambios(antes, despues):
    """Lo que cambió entre dos fotos de `recetaventa.parquet`: un DataFrame
    con `COLUMNAS_CAMBIOS`, una fila por cambio.

    NIVEL «Receta»: receta nueva / quitada. «Línea»: insumo agregado /
    quitado, o un campo de `CAMPOS_LINEA` que cambió (si las cantidades de
    los canales se movieron igual que `CANTIDAD`, sale sólo `CANTIDAD`: en
    el 99,96 % de las líneas son iguales). «Plato»: plato nuevo / quitado, o
    un campo de `CAMPOS_PLATO` (su receta, su nombre, activo, los precios).
    `FECH MODIF`/`USUARIO REG` son los de la receta en la foto nueva (en la
    vieja, si se quitó): el último guardado, no necesariamente ESE cambio."""
    filas = []

    rec_a = _por(antes.drop_duplicates("COD RV"), ["COD RV"])
    rec_d = _por(despues.drop_duplicates("COD RV"), ["COD RV"])
    for cod in sorted(set(rec_d) - set(rec_a)):
        filas.append(_fila("Receta", "Receta nueva", rec_d[cod]))
    for cod in sorted(set(rec_a) - set(rec_d)):
        filas.append(_fila("Receta", "Receta quitada", rec_a[cod]))

    comunes = set(rec_a) & set(rec_d)
    lin_a = _lineas(antes[antes["COD RV"].isin(comunes)])
    lin_d = _lineas(despues[despues["COD RV"].isin(comunes)])
    for clave in sorted(set(lin_d) - set(lin_a)):
        f = lin_d[clave]
        filas.append(_fila("Línea", "Insumo agregado", f, "CANTIDAD", None,
                           _valor(f, "CANTIDAD"), rec_d[clave[0]]))
    for clave in sorted(set(lin_a) - set(lin_d)):
        f = lin_a[clave]
        filas.append(_fila("Línea", "Insumo quitado", f, "CANTIDAD",
                           _valor(f, "CANTIDAD"), None, rec_d[clave[0]]))
    for clave in sorted(set(lin_a) & set(lin_d)):
        fa, fd = lin_a[clave], lin_d[clave]
        movidos = {c: (_valor(fa, c), _valor(fd, c)) for c in CAMPOS_LINEA
                   if c in fa and c in fd
                   and not _igual(_valor(fa, c), _valor(fd, c))}
        if "CANTIDAD" in movidos:
            ref = movidos["CANTIDAD"]
            for c in CANT_CANALES:
                if c in movidos and all(_igual(x, y) for x, y in zip(movidos[c], ref)):
                    del movidos[c]
        for campo, (va, vd) in movidos.items():
            filas.append(_fila("Línea", "Cambio en la línea", fd, campo, va,
                               vd, rec_d[clave[0]]))

    pla_a = _por(antes.drop_duplicates("COD PLATO"), ["COD PLATO"])
    pla_d = _por(despues.drop_duplicates("COD PLATO"), ["COD PLATO"])
    for cod in sorted(set(pla_d) - set(pla_a)):
        filas.append(_fila("Plato", "Plato nuevo", pla_d[cod]))
    for cod in sorted(set(pla_a) - set(pla_d)):
        filas.append(_fila("Plato", "Plato quitado", pla_a[cod]))
    for cod in sorted(set(pla_a) & set(pla_d)):
        fa, fd = pla_a[cod], pla_d[cod]
        for campo in CAMPOS_PLATO:
            if campo in fa and campo in fd:
                va, vd = _valor(fa, campo), _valor(fd, campo)
                if not _igual(va, vd):
                    filas.append(_fila("Plato", "Cambio en el plato", fd,
                                       campo, va, vd))

    return pd.DataFrame(filas, columns=list(COLUMNAS_CAMBIOS))


# ── Las ediciones de una receta de plato (para «Cambios en recetas») ──────

CANALES_PRECIO = (("P.VENTA SALON", "En el Local"), ("P.VENTA DELIV", "Delivery"),
                  ("P.VENTA LLEVAR", "Para Llevar"), ("P.VENTA RAPPI", "Rappi"),
                  ("P.VENTA 5", "Pedidos Ya"))
"""Las columnas de precio de la foto, con el nombre de su canal en el POS."""


def _num(v):
    v = _valor({"v": v}, "v")
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _tabla_lineas(df):
    """Las líneas de receta de una foto, una vez por receta (no por plato),
    con la misma identidad que `_lineas` y los números ya numéricos."""
    lin = (df.drop_duplicates(["COD RV", "ITEM RV"])
             .sort_values(["COD RV", "ITEM RV"], kind="stable"))
    lin = lin[[c for c in ("COD RV", "COD INS", "INS RV", "CANTIDAD", "P.UNIT COSTO",
                           "UNID COSTO") if c in lin.columns]].copy()
    for c in ("INS RV", "UNID COSTO"):
        if c not in lin.columns:
            lin[c] = None
    lin["_VEZ"] = lin.groupby(["COD RV", "COD INS"]).cumcount()
    for c in ("CANTIDAD", "P.UNIT COSTO"):
        lin[c] = pd.to_numeric(lin[c], errors="coerce").fillna(0.0) if c in lin.columns else 0.0
    return lin


def ediciones_plato(antes, despues):
    """Lo que cambió en cada RECETA DE PLATO entre dos fotos, una edición
    por receta (`COD RV`): una lista de dicts rv, nombre, fmodif, usr,
    nueva, quitada, lineas [(cod, insumo, antes, después, unidad, soles)]
    (de la que más mueve el costo a la que menos), antes, despues, delta y
    platos (los códigos que la llevan en la foto nueva; en la vieja, si se
    quitó).

    El costo va con los precios de la foto NUEVA, los dos lados (el insumo
    que se quitó, con el suyo de la vieja): así una suba de precios entre
    las dos fotos no se lee como un cambio de receta — lo mismo que hace
    `simulador_receta.ediciones_base` con las recetas base, del otro lado
    porque acá el precio de antes no se guarda. `fmodif`/`usr` son los del
    último guardado de la receta (los de la vieja si se quitó). Con cruces
    de tablas y no línea por línea: sobre las fotos de verdad, 0,1 s por
    par contra 0,7."""
    la, ld = _tabla_lineas(antes), _tabla_lineas(despues)
    m = la.merge(ld, on=["COD RV", "COD INS", "_VEZ"], how="outer",
                 suffixes=("_a", "_d"), indicator=True)
    qa = m["CANTIDAD_a"].where(m["_merge"] != "right_only")
    qd = m["CANTIDAD_d"].where(m["_merge"] != "left_only")
    igual = (m["_merge"] == "both") & ((qa - qd).abs()
                                       <= 1e-9 * qa.abs().clip(lower=1.0))
    m = m.assign(_qa=qa, _qd=qd)[~igual]
    if m.empty:
        return []
    precio = m["P.UNIT COSTO_d"].where(m["_merge"] != "left_only", m["P.UNIT COSTO_a"])
    m = m.assign(_soles=(m["_qd"].fillna(0.0) - m["_qa"].fillna(0.0)) * precio.fillna(0.0),
                 _ins=m["INS RV_d"].where(m["_merge"] != "left_only", m["INS RV_a"]),
                 _uni=m["UNID COSTO_d"].where(m["_merge"] != "left_only", m["UNID COSTO_a"]))
    rvs = set(m["COD RV"])

    # El costo de cada receta tocada: el de después, con sus precios; el de
    # antes, con el precio de HOY del mismo insumo si sigue en la receta.
    hoy = ld[ld["COD RV"].isin(rvs)]
    c_d = (hoy["CANTIDAD"] * hoy["P.UNIT COSTO"]).groupby(hoy["COD RV"]).sum()
    p_hoy = hoy.drop_duplicates(["COD RV", "COD INS"]).set_index(["COD RV", "COD INS"])["P.UNIT COSTO"]
    viejo = la[la["COD RV"].isin(rvs)]
    p_v = pd.Series(list(zip(viejo["COD RV"], viejo["COD INS"]))).map(p_hoy).to_numpy()
    p_v = pd.Series(p_v, index=viejo.index).fillna(viejo["P.UNIT COSTO"])
    c_a = (viejo["CANTIDAD"] * p_v).groupby(viejo["COD RV"]).sum()

    rec_a = _por(antes[antes["COD RV"].isin(rvs)].drop_duplicates("COD RV"), ["COD RV"])
    rec_d = _por(despues[despues["COD RV"].isin(rvs)].drop_duplicates("COD RV"), ["COD RV"])
    pla_a = antes[antes["COD RV"].isin(rvs)].groupby("COD RV")["COD PLATO"].unique()
    pla_d = despues[despues["COD RV"].isin(rvs)].groupby("COD RV")["COD PLATO"].unique()

    out = []
    for rv, g in m.groupby("COD RV", sort=True):
        quitada = rv not in rec_d
        ref = rec_a[rv] if quitada else rec_d[rv]
        g = g.reindex(g["_soles"].abs().sort_values(ascending=False, kind="stable").index)
        lineas = [(cod, _valor({"v": ins}, "v"), _num(a), _num(d), _valor({"v": u}, "v"), float(sl))
                  for cod, ins, a, d, u, sl in zip(g["COD INS"], g["_ins"], g["_qa"], g["_qd"],
                                                   g["_uni"], g["_soles"])]
        antes_c = float(c_a.get(rv, 0.0))
        despues_c = 0.0 if quitada else float(c_d.get(rv, 0.0))
        platos = (pla_a if quitada else pla_d).get(rv, [])
        out.append({
            "rv": rv, "nombre": _valor(ref, "NOMB RV"),
            "fmodif": _valor(ref, "FECH MODIF"), "usr": _valor(ref, "USUARIO REG"),
            "nueva": rv not in rec_a, "quitada": quitada, "lineas": lineas,
            "antes": antes_c, "despues": despues_c, "delta": despues_c - antes_c,
            "platos": sorted(str(x) for x in platos),
        })
    return out


def precios_de_fotos(antes, despues):
    """Los precios de venta que cambiaron entre dos fotos, uno por plato:
    {cod: [(canal, antes, después)]}. Es el respaldo de «Cambios en
    recetas» mientras la auditoría del POS no traiga los precios (la fila
    `auditoriacostos` del Sheet sin los campos «Precio Venta Canal»): sin
    hora ni usuario. Un plato nuevo no cuenta: su precio no cambió, nació."""
    pla_a = _por(antes.drop_duplicates("COD PLATO"), ["COD PLATO"])
    pla_d = _por(despues.drop_duplicates("COD PLATO"), ["COD PLATO"])
    out = {}
    for cod in set(pla_a) & set(pla_d):
        cs = [(canal, _num(pla_a[cod].get(c)), _num(pla_d[cod].get(c)))
              for c, canal in CANALES_PRECIO]
        cs = [x for x in cs if not _igual(x[1], x[2])]
        if cs:
            out[str(cod)] = cs
    return out
