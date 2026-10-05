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

LOS MOVIMIENTOS POR TIPO (regla #602) son las mismas filas sumadas en un
período: `sql_movimientos`, agrupadas por `GRUPOS`. Con la foto de antes y la
de después, explican el cambio del stock; lo que no explica ningún movimiento
es la VALORIZACIÓN (el precio promedio que cambia con stock negativo, o una
venta que sale sin costo).

EL AJUSTE SEGÚN EL KARDEX (regla #612) sale de OTRA consulta, la fila
`ajustekardex` del Sheet (`consulta_ajustes_sheet`): lo que el kardex registró
por cada cierre de inventario, para compararlo con lo que dice el cierre
(`sql_ajuste_con_kardex`).

Puro DuckDB, sin Streamlit, como `consumo_recetas.py`: `relacion` es lo que va
después del FROM (un `read_parquet(...)` de R2 o una tabla registrada en una
prueba). Lo lee `data.py`; lo vigila `test_graficos.py::_pruebas_kardex`.
Reglas #601, #602 y #612.
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


# ═══════════════════════════════════════════════════════════════════════
# MOVIMIENTOS POR TIPO (regla #602)
# ═══════════════════════════════════════════════════════════════════════

GRUPOS = (
    ("compras", "Compras"),
    ("ventas", "Ventas"),
    ("ajustes", "Ajustes de inventario"),
    ("salidas", "Notas de salida"),
    ("produccion", "Producción y porcionamiento"),
    ("entre", "Entre áreas"),
    ("otros", "Otros"),
)
"""Cómo se agrupan los tipos de documento del kardex, en el orden en que se
leen: lo que entra de afuera, lo que sale por la venta, lo que corrige el
conteo, lo que sale por otra vía, lo que se transforma adentro y lo que sólo
cambia de área. «Entre áreas» suma cero en el restaurante entero —lo que el
Almacén Central entrega lo recibe un área— y es lo que explica cada área."""

_GRUPO_DE_TIPO = {
    "95": "ventas",       # Descargo de Ventas
    "93": "ajustes",      # Ajuste Inventarios
    "98": "salidas",      # Nota de Salida
    "92": "salidas",      # Merma Fija
    "91": "salidas",      # Control Interno
    "90": "produccion",   # Empacado
    "94": "produccion",   # Orden de Producción
    "96": "produccion",   # Porcionamiento
    "97": "entre",        # Transferencia
    "99": "entre",        # Requerimiento
}

TIPO_VENTAS = "95"


def grupo_de(cod_tipo):
    """El grupo (`GRUPOS`) de un tipo de documento. Los de compra son los
    códigos de SUNAT, todos por debajo del 90 (01 Factura, 03 Boleta, 07
    Nota de Crédito, 46 Guía…); los internos del Almacén van del 90 al 99.
    Uno que no se conozca va a «Otros», que sólo se muestra si suma algo."""
    c = str(cod_tipo).strip()
    if c in _GRUPO_DE_TIPO:
        return _GRUPO_DE_TIPO[c]
    if c.isdigit() and int(c) < 90:
        return "compras"
    return "otros"


def sql_movimientos(relacion, desde, hasta):
    """Por área, producto y tipo de documento, lo que entró y salió entre
    `desde` (desde las 00:00) y `hasta` (hasta las 23:59), en cantidad y en
    soles, con cuántos movimientos y anulaciones fueron.

    Y lo que salió POR VENTAS SIN COSTO (`cant_sin_costo`,
    `movs_sin_costo`): las filas del descargo de ventas con cantidad y valor
    cero. El kardex saca cada venta al precio promedio de ese momento, y un
    producto que se vende antes de recibirlo —con el precio todavía en
    cero— sale gratis: medido en septiembre 2026, cuatro productos de Cocina
    por ≈ S/ 7.633 a su precio de hoy. La fila es una hora × tipo, así que
    una hora que mezcle ventas a cero y con precio cuenta como con precio:
    el error va del lado de no acusar."""
    d0 = dt.datetime.combine(desde, dt.time(0, 0))
    d1 = dt.datetime.combine(hasta, dt.time(0, 0)) + dt.timedelta(days=1)
    return f"""
        SELECT "CODIGO AREA" AS area, "CODIGO PRODUCTO" AS cod,
               "COD TIPO" AS tipo, any_value("TIPO MOVIMIENTO") AS nombre,
               sum("CANT INGRESO") AS cant_in, sum("CANT SALIDA") AS cant_out,
               sum("VALOR INGRESO") AS val_in, sum("VALOR SALIDA") AS val_out,
               sum("MOVIMIENTOS") AS movs, sum("ANULACIONES") AS anul,
               sum(CASE WHEN "COD TIPO" = '{TIPO_VENTAS}'
                         AND "CANT SALIDA" > 0 AND abs("VALOR SALIDA") < 1e-9
                        THEN "CANT SALIDA" ELSE 0 END) AS cant_sin_costo,
               sum(CASE WHEN "COD TIPO" = '{TIPO_VENTAS}'
                         AND "CANT SALIDA" > 0 AND abs("VALOR SALIDA") < 1e-9
                        THEN "MOVIMIENTOS" ELSE 0 END) AS movs_sin_costo
        FROM {relacion}
        WHERE "COD TIPO" <> 'SI'
          AND "{COL_FECHA}" >= TIMESTAMP '{d0:%Y-%m-%d %H:%M:%S}'
          AND "{COL_FECHA}" < TIMESTAMP '{d1:%Y-%m-%d %H:%M:%S}'
        GROUP BY 1, 2, 3
    """


# ═══════════════════════════════════════════════════════════════════════
# EL AJUSTE SEGÚN EL KARDEX (regla #612)
# ═══════════════════════════════════════════════════════════════════════
#
# El Almacén tiene DOS reportes de un mismo cierre de inventario, y hasta
# agosto de 2025 no dicen lo mismo:
#
#   «Cierre y Ajuste de Inventario»     `SpRepCierreInventario`, sobre
#   (y `ajusteinventario.parquet`)      `mCierreInventario`: stock al cierre
#                                       (`nStockActual`), lo contado
#                                       (`nTotal`), el ajuste (`nAjuste`) ×
#                                       el precio promedio.
#   «Movimientos por artículo ›         el kardex: `MKARDEX` (Almacén
#    Ajuste Inventarios»                Central) y `MSUBKARDEX` (las áreas),
#                                       tipo 93, con el código del cierre en
#                                       `tDocumento`.
#
# Medido el 2026-10-04 sobre los 903 cierres desde dic 2021: desde sep 2025
# coinciden todos al céntimo (la Cocina del 01/10/2025 difiere en S/ 12: el
# kardex movió un producto «4», un código que no existe). Antes, en
# 31.960 líneas el «stock al cierre» de `mCierreInventario` está escrito como
# LO CONTADO × 1,10 o × 0,90 (hasta el primer trimestre de 2024) y × 1,05 o
# × 0,95 (de ahí a agosto de 2025), o igual a lo contado: el ajuste del
# reporte sale de ±5-10 % o cero, y el del kardex es el de verdad. Lo contado
# es el mismo en los dos lados —el stock que deja el kardex después del
# ajuste es `nTotal` en el 99,8 % de esas líneas—: lo que no coincide es el
# stock de antes. El kardex suma S/ 1,4 millones más de faltante que el
# reporte entre dic 2021 y ago 2025 (S/ 264 mil en 2024, S/ 159 mil en 2025).

ARCHIVO_AJUSTES = "ajustekardex.parquet"
"""La fila `ajustekardex` del Sheet: una fila por cierre × producto."""

VERSION_AJUSTES = 1
"""Va en la clave de la caché del cruce: subirla cuando cambie QUÉ se cruza."""

COL_AJUSTE_KX = "AJUSTE KARDEX"
COL_VALOR_KX = "AJUSTE VALORIZADO KARDEX"
"""Las dos columnas que `sql_ajuste_con_kardex` agrega a cada línea del
cierre: la cantidad y los soles que movió el kardex por ella."""


def consulta_ajustes_sheet():
    """El SQL de la fila `ajustekardex` del Sheet, con los nombres completos
    que usa el usuario (sin apodos de tabla; la unión de los dos kardex es una
    subconsulta con nombre).

    Una fila por cierre × área × producto: lo que entró menos lo que salió por
    el ajuste (`AJUSTE KARDEX`), en soles con signo (`nValor` viene siempre
    positivo; el signo lo pone el lado), el stock que había antes del primer
    movimiento y cuántos fueron. El tipo 93 no tiene anulaciones (medido: cero
    en todo el histórico); si las tuviera, el reverso es del mismo tipo y la
    suma lo resta igual. Sin filtro de fecha: ~358 mil filas desde dic 2021,
    40 s en el servidor."""
    return """SELECT
    KARDEX_AJUSTES.tDocumento AS [CODIGO CIERRE],
    KARDEX_AJUSTES.tCodigoArea AS [CODIGO AREA],
    KARDEX_AJUSTES.tCodigoProducto AS [CODIGO PRODUCTO],
    MIN(KARDEX_AJUSTES.fRegistro) AS [FECHA KARDEX],
    SUM(KARDEX_AJUSTES.nIngreso - KARDEX_AJUSTES.nSalida) AS [AJUSTE KARDEX],
    SUM(CASE WHEN KARDEX_AJUSTES.nIngreso > 0 THEN KARDEX_AJUSTES.nValor
             WHEN KARDEX_AJUSTES.nSalida > 0 THEN -KARDEX_AJUSTES.nValor
             ELSE 0 END) AS [AJUSTE VALORIZADO KARDEX],
    SUM(CASE WHEN KARDEX_AJUSTES.nOrden = 1 THEN KARDEX_AJUSTES.nStockUltimo
             ELSE 0 END) AS [STOCK ANTES KARDEX],
    COUNT(*) AS [MOVIMIENTOS]
FROM (
    SELECT ALMACEN.DBO.MKARDEX.tDocumento, ALMACEN.DBO.MKARDEX.tCodigoArea,
           ALMACEN.DBO.MKARDEX.tCodigoProducto, ALMACEN.DBO.MKARDEX.fRegistro,
           ALMACEN.DBO.MKARDEX.nIngreso, ALMACEN.DBO.MKARDEX.nSalida,
           ALMACEN.DBO.MKARDEX.nValor, ALMACEN.DBO.MKARDEX.nStockUltimo,
           ROW_NUMBER() OVER (PARTITION BY ALMACEN.DBO.MKARDEX.tDocumento,
                                           ALMACEN.DBO.MKARDEX.tCodigoProducto
                              ORDER BY ALMACEN.DBO.MKARDEX.nCorrelativo) AS nOrden
    FROM ALMACEN.DBO.MKARDEX
    WHERE ALMACEN.DBO.MKARDEX.tTipoDocumento = '93'
    UNION ALL
    SELECT ALMACEN.DBO.MSUBKARDEX.tDocumento, ALMACEN.DBO.MSUBKARDEX.tCodigoArea,
           ALMACEN.DBO.MSUBKARDEX.tCodigoProducto, ALMACEN.DBO.MSUBKARDEX.fRegistro,
           ALMACEN.DBO.MSUBKARDEX.nIngreso, ALMACEN.DBO.MSUBKARDEX.nSalida,
           ALMACEN.DBO.MSUBKARDEX.nValor, ALMACEN.DBO.MSUBKARDEX.nStockUltimo,
           ROW_NUMBER() OVER (PARTITION BY ALMACEN.DBO.MSUBKARDEX.tDocumento,
                                           ALMACEN.DBO.MSUBKARDEX.tCodigoArea,
                                           ALMACEN.DBO.MSUBKARDEX.tCodigoProducto
                              ORDER BY ALMACEN.DBO.MSUBKARDEX.nCorrelativo) AS nOrden
    FROM ALMACEN.DBO.MSUBKARDEX
    WHERE ALMACEN.DBO.MSUBKARDEX.tTipoDocumento = '93'
) AS KARDEX_AJUSTES
GROUP BY KARDEX_AJUSTES.tDocumento, KARDEX_AJUSTES.tCodigoArea,
    KARDEX_AJUSTES.tCodigoProducto
ORDER BY KARDEX_AJUSTES.tDocumento, KARDEX_AJUSTES.tCodigoProducto"""


def sql_ajuste_con_kardex(rel_ajuste, rel_kardex):
    """`ajusteinventario.parquet` tal cual, en su orden, con dos columnas
    más: `COL_AJUSTE_KX` y `COL_VALOR_KX`, lo que el kardex movió por cada
    línea del cierre.

    El cruce es por el CÓDIGO DEL CIERRE (que ya dice el área) y los SIETE
    dígitos del producto: el parquet del ajuste lo trae con 10 («0000000033»)
    y el kardex con 7 («0000033»). No como número: el kardex tiene ocho
    movimientos con códigos que no existen («4», «50», «1.217»), y el «4»
    caía sobre el producto 0000004 de otro cierre.

    Un cierre que el kardex no tiene en absoluto queda en NULO —«sin dato»,
    no cero—: o es más nuevo que el parquet del kardex, o nunca pasó al
    kardex. Un producto que el kardex no movió en un cierre que sí tiene, en
    cero. Lo que el kardex movió y el cierre no lista no entra: medido, ocho
    líneas desde nov 2023 —casi todas esos códigos que no existen—, ninguna
    de más de S/ 195 (S/ 108 entre todas)."""
    return f"""
        WITH a AS (
            SELECT *, row_number() OVER () AS _fila_aj FROM {rel_ajuste}
        ), kx AS (
            SELECT trim("CODIGO CIERRE") AS cierre,
                   trim("CODIGO PRODUCTO") AS cod,
                   sum("{COL_AJUSTE_KX}") AS cant,
                   sum("{COL_VALOR_KX}") AS val
            FROM {rel_kardex}
            GROUP BY 1, 2
        ), cierres AS (
            SELECT DISTINCT cierre FROM kx
        )
        SELECT a.* EXCLUDE (_fila_aj),
               CASE WHEN c.cierre IS NULL THEN NULL
                    ELSE coalesce(kx.cant, 0) END AS "{COL_AJUSTE_KX}",
               CASE WHEN c.cierre IS NULL THEN NULL
                    ELSE coalesce(kx.val, 0) END AS "{COL_VALOR_KX}"
        FROM a
        LEFT JOIN cierres AS c ON c.cierre = trim(a."CODIGO CIERRE")
        LEFT JOIN kx ON kx.cierre = trim(a."CODIGO CIERRE")
                    AND kx.cod = right(trim(a."CODIGO PRODUCTO"), 7)
        ORDER BY a._fila_aj
    """
