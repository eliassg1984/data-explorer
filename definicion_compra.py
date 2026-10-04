"""
definicion_compra — las NOTAS DE CRÉDITO de los proveedores, restadas de la
compra que corrigen (regla #603).

Hasta el 2026-10-04 `compras.parquet` era todo lo procesado en el Almacén
—facturas, guías sin canjear, planillas de movilidad— y nada más: las notas
de crédito viven en otra tabla (`MNOTACREDITO` + `DNOTACREDITO`), y la app
no las veía. Cuadrado contra los reportes del Almacén (septiembre 2026):
«Ingreso de Artículos por Proveedor», «Proveedores vs Artículo» y «Resumen
de Ingresos» dan lo mismo que la app al céntimo (S/ 156.656,98), porque
tampoco las restan; los dos Rankings y el Registro de Compras sí. La de ese
mes es de un proveedor de carnes: anuló una factura de Magret de pato por
«error de tipeo» y la volvió a emitir, y la app contaba las dos — 109,66 kg
donde se compraron 69,68.

LA REGLA:

- **Qué notas**: las PROCESADAS (estado 02, y el 03, cancelada), como los
  Rankings del POS. Una generada (01) todavía no es nada; una anulada (04),
  tampoco.
- **Una nota por PRODUCTO (tipo P)** trae sus líneas: cuánto se devolvió de
  cada artículo (`CANTIDAD NC`) y por cuánto (`NETO LINEA NC`). Se le resta
  a la línea de ESE producto en la factura que corrige (`DOCUMENTO REF`): la
  cantidad tal cual, y los montos en la proporción del neto devuelto. El
  precio unitario no se toca — se devolvió a lo que se pagó.
- **Una nota por MONTO (tipo D)** no dice qué se devolvió. Se reparte entre
  todas las líneas de su factura en proporción a su valor, y la cantidad
  baja en la misma proporción: así tampoco mueve el precio unitario. Leerla
  como un descuento (sólo el monto) inventaba precios: una nota del 96 % de
  la factura dejaba el kilo al 4 % de lo pagado. Hoy son raras (la última,
  enero 2025); entre 2022 y 2024 fueron 29.
- **Se resta EN LA FECHA DE LA FACTURA**, no en la de la nota. Es al revés
  que en ventas (`definicion_venta.py`), a propósito: las vistas de Compras
  miden PRECIOS y CANTIDADES por compra (Volatilidad, Producto, Vs año
  pasado), y una nota como fila negativa en su propia fecha sería una
  «compra» de cantidad negativa a un precio — un punto más en la vela de la
  semana, un precio final que no se pagó. Restada de su factura, la compra
  queda como fue. El costo: en los meses en que nota y factura caen en meses
  distintos, el mes no cuadra con el Ranking del POS ni con el Registro de
  Compras, que la restan en su fecha. Medido: 1 de 9 notas en 2026 (Quality
  Beef, factura de diciembre 2025 y nota de enero), 2 de 9 en 2025.
- **Una línea devuelta ENTERA desaparece** (la factura anulada del
  Magret, por ejemplo): no hubo compra. Las que quedan llevan el número de
  la nota en `NOTA_CREDITO` y lo restado, en soles, en `VALOR_NC`.
- **Las columnas de CABECERA no se tocan** (`TOTAL NETO`, `TOTAL IGV`,
  `TOTAL DOCUMENTO`): describen la factura tal como se emitió. Por eso
  «Documentos SUNAT», que cruza documento contra documento, lee el parquet
  SIN las notas (`data.cargar(..., notas_credito=False)`): una factura
  anulada que desaparece saldría «Sólo en SUNAT» siendo falso — la misma
  trampa que la regla #301 con los chips de Familia.

Una nota cuya factura no está en el parquet (que arranca en 2023) no se
aplica: lo que corregía tampoco está. Desde 2023 es una sola, de 2023 sobre
una factura de 2022. Una línea P cuyo producto no está en su factura (no
pasó nunca) se reparte como una nota por monto.

CÓMO SE APLICA. `data.cargar("compras.parquet")` baja también
`notascreditocompras.parquet` (la fila `notascreditocompras` del Sheet) y
llama a `aplicar_notas`, así que TODO consumidor de compras recibe el df
neto: las vistas de Compras, los KPIs del rail, el asistente IA, «Consumo
según recetas» (contra compras) y «Revisar recetas». Sin ese parquet (antes
de que exista la fila del Sheet) devuelve compras tal cual.

LA CONSULTA DEL SHEET: una fila por línea DEVUELTA (`nCantidad > 0`), y una
sola fila con el producto vacío para la nota sin líneas. Las columnas de la
nota (`NETO NC`, `TOTAL NC`…) se REPITEN en cada línea: sumarlas por fila
cuenta la nota tantas veces como líneas tenga — misma trampa de grano que
`porcionamientos.parquet` (regla #510). Ver `consulta_sheet()`.

Módulo puro: pandas y nada más, como `definicion_venta.py`. Lo verifica
`test_definicion_compra.py` con un parquet de mentira; la cifra contra el
Almacén, `python herramientas/cuadrar_compras.py`.
"""

import numpy as np
import pandas as pd

VERSION = 1
"""Entra en la clave de la caché de `data.py`. Subirla al cambiar la regla:
sin esto la caché seguiría sirviendo el df con la regla anterior hasta que
cambie alguno de los dos parquets."""

ARCHIVO = "compras.parquet"
ARCHIVO_NOTAS = "notascreditocompras.parquet"
"""La fila `notascreditocompras` del Sheet de consultas (así, junta): el
extractor nombra el parquet con el nombre de la fila."""

# ── compras.parquet (en MAYÚSCULAS, como vienen de R2) ─────────────────────
DOCUMENTO = "NUM_DOCUMENTO"
PROVEEDOR = "COD_PROVEEDOR"
PRODUCTO = "COD_PRODUCTO"
CANTIDAD = "CANTIDAD_COMPRA"
CAMBIO = "TIPO_CAMBIO"
VALOR = "VALOR_COMPRA"
MONTOS = (VALOR, "VALOR_IGV_COMPRA_MN", "VALOR_BRUTO_COMPRA_MN")
"""Los montos de LÍNEA, en soles, que la nota achica. Los de cabecera (en la
moneda del documento) quedan como se emitió la factura."""
COL_NOTA = "NOTA_CREDITO"
"""Columna NUEVA: la(s) nota(s) que tocaron la línea, separadas por coma."""
COL_VALOR_NC = "VALOR_NC"
"""Columna NUEVA: lo que la nota le restó a `VALOR_COMPRA`, en soles y en
positivo. Sumada a `VALOR_COMPRA` da la línea tal como se facturó."""

# ── notascreditocompras.parquet (la consulta del Sheet) ────────────────────
NC_NUMERO = "NOTA CREDITO"
NC_PROVEEDOR = "COD PROVEEDOR"
NC_TIPO = "TIPO NC"
NC_ESTADO = "ESTADO NC"
NC_FECHA = "FECHA NC"
NC_REF = "DOCUMENTO REF"
NC_MONEDA = "MONEDA NC"
NC_NETO = "NETO NC"
NC_PRODUCTO = "COD PRODUCTO"
NC_CANTIDAD = "CANTIDAD NC"
NC_NETO_LINEA = "NETO LINEA NC"

ESTADOS = ("02", "03")
"""Procesada y cancelada: los que suman en los Rankings del POS
(`RP_RANKING_COMPRAS_PROVEEDOR`, `spRep_RankingComprasA`)."""
DOLARES = "02"
"""`tMoneda` del Almacén. Una nota en dólares se pasa a soles con el tipo de
cambio de SU FACTURA, que es con el que `compras.parquet` convirtió la
línea: así la proporción restada es exacta."""

_COLUMNAS_COMPRAS = (DOCUMENTO, PROVEEDOR, PRODUCTO, CANTIDAD, CAMBIO, VALOR)
_COLUMNAS_NOTAS = (NC_NUMERO, NC_PROVEEDOR, NC_ESTADO, NC_REF, NC_MONEDA,
                   NC_NETO, NC_PRODUCTO, NC_CANTIDAD, NC_NETO_LINEA)

_ENTERA = 1 - 1e-4
"""Desde qué fracción restada una línea se da por devuelta entera."""


def consulta_sheet():
    """El SQL de la fila `notascreditocompras` del Sheet, con los nombres
    completos que usa el usuario en sus consultas (sin apodos de tabla).

    `LEFT JOIN` a las líneas con `nCantidad > 0`: el Almacén guarda en
    `DNOTACREDITO` TODAS las líneas de la factura —una nota de 8 unidades de
    2025 trae 73—, y sólo las que tienen cantidad son lo
    devuelto. La nota por monto no tiene ninguna: sale una fila con el
    producto vacío. Sin filtro de fecha: son ~200 filas en total."""
    return """SELECT
    ALMACEN.DBO.MNOTACREDITO.tNotaCredito AS [NOTA CREDITO],
    ALMACEN.DBO.MNOTACREDITO.tCodigoProveedor AS [COD PROVEEDOR],
    ALMACEN.DBO.TPROVEEDOR.tRazonSocial AS [PROVEEDOR],
    ALMACEN.DBO.MNOTACREDITO.tTipoNotaCredito AS [TIPO NC],
    ALMACEN.DBO.MNOTACREDITO.tEstadoDocumento AS [ESTADO NC],
    ALMACEN.DBO.MNOTACREDITO.fFecha AS [FECHA NC],
    ALMACEN.DBO.MNOTACREDITO.fFechaIngreso AS [FECHA INGRESO NC],
    ALMACEN.DBO.MNOTACREDITO.tDocumento AS [DOCUMENTO REF],
    ALMACEN.DBO.MNOTACREDITO.tMoneda AS [MONEDA NC],
    ALMACEN.DBO.MNOTACREDITO.nTipoCambio AS [TIPO CAMBIO NC],
    ALMACEN.DBO.MNOTACREDITO.nNeto AS [NETO NC],
    ALMACEN.DBO.MNOTACREDITO.nTotal AS [TOTAL NC],
    ALMACEN.DBO.MNOTACREDITO.tObservacion AS [MOTIVO NC],
    ALMACEN.DBO.DNOTACREDITO.tCodigoProducto AS [COD PRODUCTO],
    ALMACEN.DBO.DNOTACREDITO.nItem AS [ITEM],
    ALMACEN.DBO.DNOTACREDITO.nCantidadDocumento AS [CANTIDAD DOCUMENTO],
    ALMACEN.DBO.DNOTACREDITO.nCantidad AS [CANTIDAD NC],
    ALMACEN.DBO.DNOTACREDITO.nSubTotalNeto AS [NETO LINEA NC],
    ALMACEN.DBO.DNOTACREDITO.nSubTotal AS [TOTAL LINEA NC]
FROM ALMACEN.DBO.MNOTACREDITO
LEFT JOIN ALMACEN.DBO.DNOTACREDITO
    ON ALMACEN.DBO.DNOTACREDITO.tNotaCredito = ALMACEN.DBO.MNOTACREDITO.tNotaCredito
    AND ALMACEN.DBO.DNOTACREDITO.tCodigoProveedor = ALMACEN.DBO.MNOTACREDITO.tCodigoProveedor
    AND ALMACEN.DBO.DNOTACREDITO.nCantidad > 0
LEFT JOIN ALMACEN.DBO.TPROVEEDOR
    ON ALMACEN.DBO.TPROVEEDOR.tCodigoProveedor = ALMACEN.DBO.MNOTACREDITO.tCodigoProveedor
ORDER BY ALMACEN.DBO.MNOTACREDITO.fFecha, ALMACEN.DBO.MNOTACREDITO.tNotaCredito,
    ALMACEN.DBO.DNOTACREDITO.nItem"""


def _texto(s):
    """Códigos como texto limpio: el Sheet y el parquet los traen como
    `nvarchar` con ceros a la izquierda, pero un nulo es `None` y no `""`."""
    return s.astype("string").str.strip().fillna("")


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def notas_validas(notas):
    """Las filas de `notas` que se aplican (procesadas), con los códigos como
    texto y los montos como número. Vacío si falta alguna columna."""
    if notas is None or notas.empty or any(c not in notas.columns
                                           for c in _COLUMNAS_NOTAS):
        return pd.DataFrame(columns=list(_COLUMNAS_NOTAS))
    n = pd.DataFrame({
        "nota": _texto(notas[NC_NUMERO]),
        "prov": _texto(notas[NC_PROVEEDOR]),
        "estado": _texto(notas[NC_ESTADO]),
        "doc": _texto(notas[NC_REF]),
        "moneda": _texto(notas[NC_MONEDA]),
        "neto": _num(notas[NC_NETO]),
        "prod": _texto(notas[NC_PRODUCTO]),
        "cant": _num(notas[NC_CANTIDAD]),
        "neto_linea": _num(notas[NC_NETO_LINEA]),
    })
    return n[n["estado"].isin(ESTADOS) & n["nota"].ne("")].reset_index(drop=True)


def _creditos(base, n):
    """Lo que cada nota le resta a cada línea de compra, como dos fracciones
    por fila de `base`: `f_valor` (de los montos) y `f_cant` (de la
    cantidad), más el texto de las notas que la tocaron.

    `base` tiene una fila por fila de compras (mismo índice) con `doc`,
    `prov`, `prod`, `valor`, `cant` y `cambio`. Todo con merges y groupbys
    sobre las ~200 filas de notas: nada de recorrer facturas una por una
    (regla #537)."""
    claves_doc = ["doc", "prov"]
    claves_lin = ["doc", "prov", "prod"]

    # Totales de la compra por línea (doc, prov, prod) y por factura.
    por_lin = base.groupby(claves_lin, sort=False).agg(
        valor_lin=("valor", "sum"), cant_lin=("cant", "sum")).reset_index()
    por_doc = base.groupby(claves_doc, sort=False).agg(
        valor_doc=("valor", "sum"), cambio=("cambio", "first")).reset_index()

    # Una nota en dólares se lleva a soles con el cambio de su factura.
    n = n.merge(por_doc, on=claves_doc, how="inner")
    tc = np.where(n["moneda"].eq(DOLARES), n["cambio"].fillna(1.0), 1.0)
    n = n.assign(neto_mn=n["neto"] * tc, neto_linea_mn=n["neto_linea"] * tc)

    # ── Por producto: la línea de la nota contra la MISMA línea de su
    # factura. Las que no la encuentran pasan a repartirse como por monto.
    con_prod = n[n["prod"].ne("") & (n["cant"] > 0)]
    lin = con_prod.merge(por_lin, on=claves_lin, how="left", indicator=True)
    hallada = lin["_merge"].eq("both")
    p = (lin[hallada].groupby(claves_lin, sort=False)
         .agg(cred_val=("neto_linea_mn", "sum"), cred_cant=("cant", "sum"),
              notas_p=("nota", lambda s: ", ".join(sorted(set(s)))))
         .reset_index())
    sueltas = (lin[~hallada].groupby(claves_doc + ["nota"], sort=False)
               ["neto_linea_mn"].sum().rename("monto").reset_index())

    # ── Por monto: la nota sin líneas (una fila por nota; su cabecera no se
    # repite) más las líneas P sueltas, contra la factura entera.
    sin_prod = (n[n["prod"].eq("")].drop_duplicates(["nota", "prov"])
                .rename(columns={"neto_mn": "monto"})[claves_doc + ["nota", "monto"]])
    d = (pd.concat([sin_prod, sueltas], ignore_index=True)
         .groupby(claves_doc, sort=False)
         .agg(cred_doc=("monto", "sum"),
              notas_d=("nota", lambda s: ", ".join(sorted(set(s)))))
         .reset_index())

    # ── A cada fila de compra, sus dos créditos como fracción. Un merge
    # `left` con la derecha sin claves repetidas conserva el orden y el
    # número de filas de la izquierda: la fila N sigue siendo la N.
    filas = (base[claves_lin].reset_index(drop=True)
             .merge(por_lin, on=claves_lin, how="left")
             .merge(por_doc[claves_doc + ["valor_doc"]], on=claves_doc, how="left")
             .merge(p, on=claves_lin, how="left")
             .merge(d, on=claves_doc, how="left"))
    with np.errstate(divide="ignore", invalid="ignore"):
        f_p_val = np.where(filas["valor_lin"] > 0,
                           filas["cred_val"] / filas["valor_lin"], 0.0)
        f_p_cant = np.where(filas["cant_lin"] > 0,
                            filas["cred_cant"] / filas["cant_lin"], 0.0)
        f_d = np.where(filas["valor_doc"] > 0,
                       filas["cred_doc"] / filas["valor_doc"], 0.0)
    f_p_val, f_p_cant, f_d = (np.nan_to_num(x) for x in (f_p_val, f_p_cant, f_d))
    notas_txt = (filas["notas_p"].fillna("") + ", " + filas["notas_d"].fillna("")
                 ).str.strip(", ")
    return pd.DataFrame({
        "f_valor": np.clip(f_p_val + f_d, 0.0, 1.0),
        "f_cant": np.clip(f_p_cant + f_d, 0.0, 1.0),
        "notas": notas_txt.to_numpy(),
    }, index=base.index)


def aplicar_notas(compras, notas):
    """`compras` con las notas de crédito procesadas restadas de las líneas
    que corrigen, en la fecha de su factura. Ver el docstring del módulo.

    Devuelve `compras` tal cual (el mismo objeto) si no hay notas que
    aplicar o si a alguno de los dos le faltan columnas — el demo, o un
    parquet de notas todavía sin la fila del Sheet. Si aplica, devuelve una
    copia con dos columnas nuevas (`NOTA_CREDITO`, `VALOR_NC`) y sin las
    líneas devueltas enteras."""
    if compras is None or compras.empty or any(c not in compras.columns
                                               for c in _COLUMNAS_COMPRAS):
        return compras
    n = notas_validas(notas)
    if n.empty:
        return compras
    base = pd.DataFrame({
        "doc": _texto(compras[DOCUMENTO]),
        "prov": _texto(compras[PROVEEDOR]),
        "prod": _texto(compras[PRODUCTO]),
        "valor": _num(compras[VALOR]),
        "cant": _num(compras[CANTIDAD]),
        "cambio": pd.to_numeric(compras[CAMBIO], errors="coerce"),
    }, index=compras.index)
    cr = _creditos(base, n)
    tocadas = cr["f_valor"].gt(0) | cr["f_cant"].gt(0)
    if not tocadas.any():
        return compras

    out = compras.copy()
    out[COL_NOTA] = cr["notas"].where(tocadas, "").astype(object)
    out[COL_VALOR_NC] = base["valor"] * cr["f_valor"]
    for col in MONTOS:
        if col in out.columns:
            out[col] = _num(out[col]) * (1.0 - cr["f_valor"])
    out[CANTIDAD] = base["cant"] * (1.0 - cr["f_cant"])
    # Basta con UNA de las dos: el neto de la línea de la nota y el de la
    # factura difieren en céntimos (Backus, 2023: 225,48 contra 225,43), así
    # que «devolví las 30 unidades» dejaba una línea de 0 unidades y 5
    # céntimos — un precio unitario infinito para Volatilidad y Producto.
    devuelta = cr["f_valor"].ge(_ENTERA) | cr["f_cant"].ge(_ENTERA)
    return out[~devuelta]


def aplicadas(compras, notas):
    """Una fila por nota procesada, con si se pudo aplicar o no y por qué
    —«sin factura en el parquet», «aplicada»— y su monto en la moneda de la
    nota. Para `herramientas/cuadrar_compras.py` y el test: la app no la
    necesita."""
    n = notas_validas(notas)
    if n.empty:
        return pd.DataFrame(columns=["nota", "prov", "doc", "neto", "estado"])
    cab = n.drop_duplicates(["nota", "prov"])[["nota", "prov", "doc", "neto"]]
    docs = pd.DataFrame({"doc": _texto(compras[DOCUMENTO]),
                         "prov": _texto(compras[PROVEEDOR])}).drop_duplicates()
    cab = cab.merge(docs.assign(hay=True), on=["doc", "prov"], how="left")
    cab["estado"] = np.where(cab["hay"].fillna(False).astype(bool),
                             "aplicada", "sin factura en el parquet")
    return cab.drop(columns="hay").reset_index(drop=True)
