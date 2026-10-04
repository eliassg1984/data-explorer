"""kardex — el stock A UNA FECHA y los movimientos POR TIPO, del kardex del Almacén.

Las dos preguntas (2026-10-03, a pedido) salen de la misma tabla:
`kardex.parquet`, la consulta «kardex» del Sheet sobre MKARDEX (Almacén
Central) y MSUBKARDEX (las áreas), desde el 2025-01-01.

EL GRANO: hora × área × producto × tipo de movimiento. Cada fila trae lo que
entró y salió en esa hora por ese tipo (cantidad y soles, `nValor`: las
compras a su costo, lo interno al precio promedio), cuántos movimientos fueron
y una FOTO: el stock y el precio promedio que dejó su último movimiento
(`STOCK DESPUES`, `PRECIO PROMEDIO DESPUES`, con su `ULTIMO CORRELATIVO`). Las
fotos NO se suman: son el stock en un instante. Medido: 1,48 millones de
movimientos en 559 mil filas (por día habrían sido 490 mil: la hora cuesta
12 % y deja elegirla).

EL STOCK A UNA FECHA es la regla del «Inventario Histórico Valorizado» del POS
(`spRepInventarioH`, modo 'R'): por área y producto, el último movimiento —el
de mayor correlativo— registrado hasta ese momento; su stock y su precio.
Cuadrado contra el PDF del Almacén Central al 30/09/2026 23:59:59: los 3.879
artículos con el mismo stock y el mismo precio, S/ 35.818,44 contra 35.818,45.
Y la foto más nueva da el stock de hoy en las 15.472 combinaciones de área y
producto (salvo cuatro filas de TSUBSTOCK con un código que no existe). Lo que
no se movió desde el 2025 sale de la fila «Saldo al 31/12/2024» que la
consulta agrega por área y producto.

LAS ANULACIONES son filas de reverso (estado 02) del MISMO tipo que el
documento que anulan: el ingreso de un requerimiento se anula con una salida.
La consulta las resta del lado del original —una salida anulada baja la
salida, no sube el ingreso—, así que un requerimiento anulado no infla nada.

Puro DuckDB, sin Streamlit, como `consumo_recetas.py`: `relacion` es lo que va
después del FROM (un `read_parquet(...)` de R2 o una tabla registrada en una
prueba). Lo lee `data.py`; lo vigila `test_graficos.py::_pruebas_kardex`.
Regla #601.
"""

import datetime as dt

VERSION = 1
"""Va en la clave de la caché de disco (que no caduca): subirla cuando cambie
QUÉ se calcula."""

ARCHIVO = "kardex.parquet"

INICIO = dt.date(2025, 1, 1)
"""Desde cuándo trae movimientos la consulta. Antes, sólo la foto del saldo."""

COL_FECHA = "FECHA HORA"


def momento(fecha, hora=23):
    """El momento «al» que se pide el stock: la HORA ENTERA `hora` del día
    `fecha`, o sea hasta las hora:59:59. El kardex va agrupado por hora, así
    que el corte cae al final de una."""
    return dt.datetime.combine(fecha, dt.time(int(hora), 0))


def sql_stock_al(relacion, cuando):
    """Por área y producto, el stock y el precio promedio que dejó el último
    movimiento hasta `cuando` (inclusive su hora): `area`, `cod`, `stock`,
    `precio`, `correlativo`. Sólo los que tienen kardex; el resto, en cero.

    El precio es el del ÁREA (cada subkardex lleva el suyo) y va a tres
    decimales, como lo escribe el POS antes de multiplicar
    (`CAST(nPrecioPromedio AS numeric(18,3))`): sin el redondeo el total
    del Almacén Central se corre unos céntimos."""
    tope = cuando.strftime("%Y-%m-%d %H:00:00")
    return f"""
        SELECT "CODIGO AREA" AS area, "CODIGO PRODUCTO" AS cod,
               "STOCK DESPUES" AS stock,
               round("PRECIO PROMEDIO DESPUES", 3) AS precio,
               "ULTIMO CORRELATIVO" AS correlativo
        FROM {relacion}
        WHERE "{COL_FECHA}" <= TIMESTAMP '{tope}'
        QUALIFY row_number() OVER (
            PARTITION BY "CODIGO AREA", "CODIGO PRODUCTO"
            ORDER BY "ULTIMO CORRELATIVO" DESC, "{COL_FECHA}" DESC) = 1
    """


def sql_ultimo_movimiento(relacion):
    """El último momento con movimientos (sin la fila del saldo inicial): el
    tope del selector de fecha."""
    return f"""SELECT max("{COL_FECHA}") FROM {relacion} WHERE "COD TIPO" <> 'SI'"""
