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
           "FECH MODIF", "USUARIO REG") + CAMPOS_PLATO + CAMPOS_LINEA

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
