"""
Importar al Almacén desde el conversor
======================================
Toma lo que ya resolvió la pantalla «Conversor SUNAT-Sistema» —qué
producto es cada línea del comprobante, en qué cantidad— y deja en R2 la
señal para que el servicio del servidor grabe el documento en el Almacén.

La webapp NO escribe en SQL Server, ni podría: corre en Streamlit Cloud y
el Almacén vive detrás de la VPN, en el restaurante. Lo que hace es
dejar un archivo en una carpeta de R2; del otro lado, `atender_solicitudes.py`
lo levanta cada 5 segundos y lo graba con los mismos procedimientos
almacenados que usa el formulario. Es el mismo mecanismo que ya se usa
para refrescar un reporte y para pedirle a SUNAT el original de un
comprobante — no es uno nuevo.

QUÉ VIAJA Y QUÉ NO
------------------
Viaja la IDENTIDAD de cada línea (producto y cantidad) y los VALORIZADOS
del comprobante. No viaja nada que el servidor pueda resolver mejor:

  · el código de proveedor      → lo busca por RUC
  · el correlativo del documento → lo calcula al grabar
  · el código de unidad          → lo manda el producto, no el XML
  · a qué casillero de impuesto  → lo decide la tasa

Eso no es delegar por comodidad: cada uno de esos datos vive en la base
del Almacén, y replicarlos acá sería mantener dos copias que se
desincronizan.

LOS VALORIZADOS SON INTOCABLES
------------------------------
Neto, impuesto y total salen del comprobante y del registro del SIRE, y
no se recalculan. Lo único que la homologación cambia es en qué unidad y
cantidad entra cada ítem — el IMPORTE de la línea es el invariante.

Se midió por qué importa: sobre 5.734 facturas cargadas a mano, el IGV
del Almacén difiere del que SUNAT tiene declarado en más de un sol en el
3,2%. El caso típico es deducir la base asumiendo 18% en una factura de
restaurante que va al 10,5%.
"""

import datetime as dt
import json
import xml.etree.ElementTree as ET

import streamlit as st

import sunat


PREFIJO_IMPORTACION = "_solicitudes_importacion"

# Del catálogo 01 de SUNAT a la letra que el Almacén usa en tDocumento.
# Sale de TTipoDocumento.tResumido.
_LETRA_TIPO = {"01": "F", "03": "B", "07": "C", "08": "D", "09": "G"}

# El Almacén codifica la moneda; SUNAT la nombra.
_MONEDA = {"PEN": "01", "USD": "02", "EUR": "03"}


# EL ISC VA ADENTRO DEL NETO, NO EN UN CASILLERO APARTE
# ---------------------------------------------------------------------------
# El Almacén tiene un marco genérico de "leyes aplicables" (Parámetros
# Generales → Leyes Aplicables) con tres grupos de tres ranuras. El tercer
# grupo se llama, literalmente, **«Impuestos incluidos en el Valor Neto»**, y
# su primera ranura está declarada como `tLeyAD1 = 'Isc'`.
#
# "Incluido en el valor neto" no es una etiqueta: es la aritmética que el
# Almacén ejecuta. Verificado leyendo sus propios objetos (2026-09-05):
#
#   · `spSaveLeyADDetails` guarda `DDOCUMENTO.nPorcentajeLeyAD = tasa/100`
#     — o sea una TASA, no un monto. El monto no tiene columna.
#   · la vista del Registro de Compras `vRegComprasTD` lo DESAGREGA:
#         ISC    = sum( nNeto / (1 + nPorcentajeLeyAD) * nPorcentajeLeyAD )
#         Afecta = (nTotal - ISC) - (nImpuesto1 + nImpuesto2 + nImpuesto3)
#     Esa división sólo tiene sentido si `nNeto` YA trae el ISC adentro.
#   · `usp_Almacen_CalculaPrecioPromedio` hace lo mismo con el precio
#     (`nPrecio / (1 + nPorcentajeLeyAD)`): el costo promedio sale SIN ISC.
#
# Contra la F003-4717 de BODEGA SAN NICOLAS (RUC 20511908401) cierra al céntimo:
# líneas 499.66, ISC 33.73, IGV 96.01, `PayableAmount` 629.40.
#
#     nNeto        = 499.66 + 33.73 = 533.39
#     tasa         = 33.73 / 499.66 = 0.0675063…
#     lo que recupera la vista: 533.39/(1+tasa)*tasa = 33.73  ✔
#     y la ecuación que valida el importador:
#     nNeto + nImpuesto1 + nRedondeo = 533.39 + 96.01 + 0 = 629.40  ✔
#
# Y EL CONTROL QUE VALE LA PENA MIRAR: ese 533.39 es, al céntimo, la
# `base_imponible` que el registro del SIRE declara para el documento. No
# es casualidad — la base gravada del registro ES la base del IGV, y el
# ISC forma parte de ella. Sumar el ISC a las líneas no es un ajuste para
# que cierre: es reconstruir el número que SUNAT ya tenía anotado. El
# `nNeto` que sale de acá se puede contrastar contra el registro.
#
# Sin esto la cabecera salía con `nNeto = 499.66` y el importador rechazaba
# —con razón: el XML no cerraba—. Ver `arquitectura.md` regla #314.
#
# LA TASA VIAJA PERO HOY NO SE ESCRIBE, Y ES A PROPÓSITO (decidido con el
# usuario, 2026-09-05). `DDOCUMENTO.nPorcentajeLeyAD` se deja en 0. Lo que
# cambia si se escribiera, medido sobre la F003-4717:
#
#                                  con la tasa    en 0 (lo que se hace)
#     Registro de Compras · base       499.66        533.39
#     Registro de Compras · ISC         33.73          0.00
#     Costo promedio (24 u)           20.8192       22.2246
#
# Las dos columnas de la derecha ganan por un motivo cada una:
#
#   · 533.39 es EXACTAMENTE la base gravada que SUNAT declara en el SIRE
#     (96.01 / 533.39 = 18,0 %). Con la tasa puesta, el Registro de
#     Compras del Almacén deja de coincidir con lo declarado.
#   · 22.2246 es lo que se pagó por unidad. El ISC no se recupera, así
#     que es costo; sacarlo del precio lo subvalúa un 6,3 % y ensucia el
#     control de fluctuación contra los documentos digitados a mano.
#
# Se manda igual en el XML para que la decisión se pueda dar vuelta
# tocando sólo el importador, sin volver acá.
#
# Y SI ALGÚN DÍA SE ESCRIBE: `spSaveLeyADDetails` PISA `nPorcentajeLeyAD`
# con la tasa del maestro de artículos (`TPRODUCTO.nPorcentajeLeyAD`), que
# para estos productos está vacía. Habría que escribir la de la línea
# directo y NO llamar a ese SP.
# ---------------------------------------------------------------------------


def tributos_en_el_neto(linea_xml):
    """Los tributos de una línea que viajan DENTRO de `nNeto`, en la moneda
    del comprobante.

    Son todos los que no son IGV: el ISC (código 2000 del catálogo 05) y el
    resto, que en la práctica es el ICBPER de la bolsa plástica (7152).
    `sunat._impuestos_linea` ya los separa por código.

    **El ICBPER entra por la MISMA ranura.** Es discutible por nombre —el
    Registro de Compras del Almacén lo va a rotular "ISC"— y es correcto por
    aritmética: es un tributo no recuperable, incluido en el precio, que
    forma parte del costo igual que el ISC. La alternativa era dejarlo
    afuera, y eso no es "más prolijo": es un documento que el importador
    rechaza y que alguien termina digitando a mano, que es de donde venimos.
    La ranura es UNA —sólo las tres `*1` tienen columna donde guardarse— así
    que no hay una segunda opción que probar.
    """
    if not linea_xml:
        return 0.0
    return _num(linea_xml.get("isc")) + _num(linea_xml.get("otros_tributos"))


def porcentaje_ley_ad(neto, incluido):
    """La tasa (en PORCENTAJE) que el Almacén necesitaría para volver a
    sacar `incluido` de adentro de `neto`.

    **Viaja en el XML pero hoy el importador no la escribe** — ver el
    bloque de arriba: dejar `DDOCUMENTO.nPorcentajeLeyAD` en 0 hace que la
    base del Registro de Compras coincida con la del SIRE y que el costo
    promedio incluya el ISC, que es lo que se pagó. Se manda para que esa
    decisión se pueda dar vuelta sin volver a tocar la webapp.

    Se despeja de la fórmula de la vista del Registro de Compras, que es
    quien la leería:

        neto / (1 + t) * t = incluido   →   t = incluido / (neto - incluido)

    Se deriva así —y no como `incluido / base_del_XML`— porque lo que tiene
    que salir exacto es el MONTO: la tasa es sólo el vehículo.

    **Y NUNCA se copia el `Percent` del UBL.** El ISC específico no es un
    porcentaje: es soles POR LITRO, y así viaja. Medido sobre los XML de
    los cuatro proveedores de bebidas que lo emiten, ese campo trae
    valores como `1.29987`, `1.81780` y `100.00` en facturas de pisco y
    vino. Copiarlo daría una ranura con un número que no significa nada
    en la fórmula que la lee.

    El Almacén guarda `nPorcentajeLeyAD = t`, o sea esto dividido por 100
    (es lo que hace `spSaveLeyADDetails`); acá va en porcentaje para que
    todos los `nPorcentaje*` de este XML se lean en la misma unidad.
    """
    base = _num(neto) - _num(incluido)
    if not incluido or base <= 0:
        return 0.0
    return round(_num(incluido) / base * 100, 6)


def _num(v, defecto=0.0):
    try:
        if v is None:
            return defecto
        return float(v)
    except (TypeError, ValueError):
        return defecto


def nombre_documento(doc):
    """El `tDocumento` del Almacén: letra + serie a 5 + número a 9.

    "FA28-2312488" con tipo 01 -> "F" + "0FA28" + "002312488"
    """
    tipo = str(doc.get("tipo_cdp") or "01").strip()
    serie = str(doc.get("serie") or "").strip().upper()
    numero = str(doc.get("numero") or "").strip()
    return f"{_LETRA_TIPO.get(tipo, 'F')}{serie:0>5}{numero:0>9}"


def clave_importacion(doc):
    """Key en R2 de la señal para importar este comprobante.

    Determinista, y con el RUC adelante porque serie-número NO es único
    entre proveedores: dos emisores distintos pueden tener su "E001-1".
    Así, además, dos clics sobre el mismo documento pisan la misma señal
    en vez de encolar dos importaciones.
    """
    ruc = str(doc.get("ruc_proveedor") or "").strip()
    return f"{PREFIJO_IMPORTACION}/{ruc}_{str(doc.get('documento') or '').strip()}.xml"


def clave_recibo(doc):
    """Key del recibo que deja el servidor: mismo nombre, otra extensión.
    Misma convención que el `.fallo.json` de `sunat_originales.py`."""
    return clave_importacion(doc)[:-4] + ".recibo.json"


# ---------------------------------------------------------------------------
# ARMADO DEL XML DE INTERCAMBIO
# ---------------------------------------------------------------------------

def construir_xml(doc, lineas_xml, filas_sistema, totales=None, glosa=None):
    """El XML de intercambio → bytes.

    doc            fila del registro del SIRE (lo que SUNAT tiene declarado)
    lineas_xml     el detalle del comprobante (`sunat.lineas_xml`)
    filas_sistema  lo que resolvió la pantalla: `_cod_sis`, `Cant.`, `Importe`
    totales        `sunat.totales_xml` del comprobante, si se pudo leer —
                   aporta los CARGOS GLOBALES, que el SIRE no trae
    glosa          texto libre para la cabecera

    Las líneas van UNA POR UNA como vienen del comprobante: consolidar las
    que repiten producto lo hace el importador, que es quien conoce la
    regla del Almacén (un producto, una línea).

    El ISC / ICBPER de cada línea se suma a su `nNeto` y viaja con su tasa
    al lado — ver el bloque «EL ISC VA ADENTRO DEL NETO». Dos elementos
    nuevos, y sólo uno es una columna: `nPorcentajeLeyAD` va derecho a
    `DDOCUMENTO.nPorcentajeLeyAD` (dividido por 100, como hace
    `spSaveLeyADDetails`), y `nLeyAD1` es el MONTO de esa ranura, que en el
    Almacén no tiene dónde guardarse y viaja para poder verificar la
    cabecera sin recorrer las líneas.
    """
    raiz = ET.Element("DocumentoCompra", {"version": "1.0"})

    origen = ET.SubElement(raiz, "Origen")
    ET.SubElement(origen, "SerieNumero").text = str(doc.get("documento") or "")
    ET.SubElement(origen, "FormatoOrigen").text = "UBL 2.1"
    ET.SubElement(origen, "GeneradoPor").text = "webapp/conversor"
    ET.SubElement(origen, "GeneradoEn").text = dt.datetime.now().isoformat(
        timespec="seconds")

    cab = ET.SubElement(raiz, "Cabecera")
    s = ET.SubElement(cab, "Sunat")
    ET.SubElement(s, "tDocumento").text = nombre_documento(doc)
    ET.SubElement(s, "tTipoDocumento").text = str(doc.get("tipo_cdp") or "01")
    ET.SubElement(s, "fEmision").text = _fecha_iso(doc.get("fecha_emision"))
    ET.SubElement(s, "RucProveedor").text = str(doc.get("ruc_proveedor") or "")
    ET.SubElement(s, "RazonSocialProveedor").text = str(doc.get("proveedor") or "")
    ET.SubElement(s, "tMoneda").text = _MONEDA.get(
        str(doc.get("moneda") or "PEN").upper(), "01")

    # -- los valorizados -------------------------------------------------
    # El neto se SUMA de las líneas homologadas, no se copia del registro:
    # el importe de cada línea es el invariante de la homologación, así que
    # por construcción tienen que dar lo mismo. Si no dieran, es que una
    # línea perdió su importe, y eso el importador lo va a rechazar — que
    # es exactamente lo que queremos que pase.
    # OJO CON LA MONEDA: las líneas vienen del XML, en la moneda del
    # comprobante, y el IGV viene del registro del SIRE, que está SIEMPRE
    # en soles (ver `sunat.en_moneda_del_papel`). En un documento en
    # dólares, sumarlos daba una cabecera con dólares y soles adentro —
    # medido en la F163-2309 de MAPFRE: 3.155,00 de líneas + 1.932,00 de
    # IGV = 5.087,00, que no es plata de ninguna moneda. El Almacén guarda
    # en la moneda del documento con su `nCambio` al lado, así que la
    # cabecera entera va en la moneda del papel. Regla #313.
    suma_lineas = sum(_num(f.get("Importe")) for f in filas_sistema)
    cargos = _num((totales or {}).get("cargos"))
    igv = _num(doc.get("igv"))
    _igv_papel = sunat.en_moneda_del_papel(doc, igv)
    if _igv_papel is not None:
        igv = _igv_papel
    # El ISC / ICBPER de las líneas va DENTRO del neto, que es donde el
    # Almacén lo espera (ver el bloque «EL ISC VA ADENTRO DEL NETO»). Sin
    # este término la cabecera no cierra en los comprobantes que lo llevan
    # y el importador los rechaza. Sale de las LÍNEAS y no puede salir de
    # otro lado: el registro del SIRE no lo desglosa —lo tiene sumado
    # dentro de `base_imponible`— y el Almacén lo necesita repartido,
    # porque la columna que lo guarda es de la línea.
    incluidos = [_tributos_de(lineas_xml, f, n)
                 for n, f in enumerate(filas_sistema)]
    incluido_total = round(sum(incluidos), 2)
    neto = suma_lineas + cargos + incluido_total
    total = _total_documento(doc, totales, neto, igv)

    ET.SubElement(s, "nNeto").text = _dec(neto)
    ET.SubElement(s, "nImpuesto1").text = _dec(igv)
    ET.SubElement(s, "nTotal").text = _dec(total)
    ET.SubElement(s, "nDescuento").text = _dec(0)
    ET.SubElement(s, "nRedondeo").text = _dec(redondeo_derivado(neto, igv, total))
    # Informativo: MDOCUMENTO no tiene columna para el ISC —el Registro de
    # Compras lo deriva de las líneas—, pero mandarlo deja la cabecera
    # verificable sin abrirla línea por línea.
    ET.SubElement(s, "nLeyAD1").text = _dec(incluido_total)
    ET.SubElement(s, "nPercepcion").text = _dec(0)
    ET.SubElement(s, "lDetraccion").text = (
        "1" if str(doc.get("detraccion") or "").strip() else "0")

    r = ET.SubElement(cab, "Resolver")
    # La fecha de INGRESO define el período contable y el correlativo, y es
    # el día que se carga — no la de emisión, que puede ser de otro mes.
    ET.SubElement(r, "fIngreso").text = dt.date.today().isoformat()
    ET.SubElement(r, "tTipoIngreso").text = "M"
    ET.SubElement(r, "tCodigoArea").text = "000"
    ET.SubElement(r, "tCodigoOperacion").text = "001"
    ET.SubElement(r, "tGlosa").text = (
        glosa or f"XML SUNAT {doc.get('documento') or ''}")[:150]
    if doc.get("tipo_cambio"):
        ET.SubElement(r, "nCambio").text = str(doc.get("tipo_cambio"))

    c = ET.SubElement(cab, "Constantes")
    ET.SubElement(c, "tEstadoDocumento").text = "01"   # GENERADO: no mueve stock
    ET.SubElement(c, "tSede").text = "000"

    # -- las líneas ------------------------------------------------------
    reparto = _repartir_cargo(cargos, [_num(f.get("Importe")) for f in filas_sistema])

    nodo_lineas = ET.SubElement(raiz, "Lineas")
    for n, fila in enumerate(filas_sistema):
        i = int(fila.get("_idx", n))
        xml_l = lineas_xml[i] if 0 <= i < len(lineas_xml) else {}
        ln = ET.SubElement(nodo_lineas, "Linea", {"nItem": str(n + 1)})
        a = ET.SubElement(ln, "Almacen")
        ET.SubElement(a, "tCodigoProducto").text = str(fila.get("_cod_sis") or "")
        ET.SubElement(a, "Nombre").text = str(fila.get("Ítem (sistema)") or "")
        # La unidad va sólo como referencia: el importador usa la del
        # producto, que es la de kardex y la única válida.
        ET.SubElement(a, "tUnidadEntrada").text = ""
        cant = _num(fila.get("Cant."))
        importe = _num(fila.get("Importe"))
        cargo = reparto[n]
        incluido = incluidos[n]
        # `nNeto` de la línea CON el ISC adentro, y su tasa al lado: es la
        # única forma que el Almacén tiene de volver a separarlos, porque
        # `DDOCUMENTO` guarda la tasa y no el monto.
        neto = importe + cargo + incluido
        ET.SubElement(a, "nCantidad").text = _dec(cant, 3)
        ET.SubElement(a, "nPrecio").text = _dec(neto / cant if cant else 0, 5)
        ET.SubElement(a, "nNeto").text = _dec(neto)
        ET.SubElement(a, "nDescuento").text = _dec(0)
        # OJO: `nOtrosCargosInafecto` RECORTA la base del impuesto, no suma
        # encima. Con el ISC adentro, la base sigue saliendo bien:
        # nNeto - nOtrosCargosInafecto = importe + ISC, que es exactamente
        # sobre lo que SUNAT calculó el IGV.
        ET.SubElement(a, "nOtrosCargosInafecto").text = _dec(cargo)
        ET.SubElement(a, "nLeyAD1").text = _dec(incluido)
        ET.SubElement(a, "nPorcentajeLeyAD").text = str(
            porcentaje_ley_ad(neto, incluido))
        # El impuesto y SU tasa salen del comprobante. Nunca se asumen: el
        # importador decide a qué casillero del Almacén van según la tasa.
        ET.SubElement(a, "nImpuesto1").text = _dec(_num(xml_l.get("igv")))
        ET.SubElement(a, "nPorcentaje1").text = str(
            xml_l.get("igv_porcentaje") if xml_l.get("igv_porcentaje") is not None
            else 0)
        ET.SubElement(a, "lIncluidoImpuesto1").text = "1"
        ET.SubElement(a, "nTotal").text = _dec(neto + _num(xml_l.get("igv")))

    return ET.tostring(raiz, encoding="utf-8", xml_declaration=True)


def _tributos_de(lineas_xml, fila, n):
    """El ISC / ICBPER de la línea del XML que le toca a esta fila.

    Comparte el `_idx` con el bucle que arma las líneas —una fila del
    conversor es una línea del comprobante— y tolera que no haya línea
    detrás, igual que `nImpuesto1`."""
    i = int(fila.get("_idx", n))
    xml_l = lineas_xml[i] if 0 <= i < len(lineas_xml) else {}
    return round(tributos_en_el_neto(xml_l), 2)


def _repartir_cargo(cargo, importes):
    """Reparte un cargo global entre las líneas, en proporción al importe.

    El recargo al consumo es un porcentaje del consumo, así que repartirlo
    proporcionalmente es lo que refleja la realidad — y deja cada línea con
    su base de impuesto correcta:

        base del impuesto = nNeto - nOtrosCargosInafecto = el importe original

    La ALTERNATIVA sería cargárselo entero a una línea, que es lo que hacen
    a mano y por eso cada quien elige otra. El sobrante del redondeo va a la
    última línea, para que la suma cierre al céntimo.
    """
    n = len(importes)
    if not cargo or n == 0:
        return [0.0] * n
    total = sum(importes)
    if not total:
        return [round(cargo / n, 2)] * n
    partes = [round(cargo * (imp / total), 2) for imp in importes]
    partes[-1] = round(partes[-1] + (cargo - sum(partes)), 2)
    return partes


# Un redondeo es de CÉNTIMOS. El caso peruano es el múltiplo de 0.10 —las
# monedas de 1 y 5 céntimos no circulan— y el retail lo aplica TRUNCANDO a
# favor del cliente, no al más cercano: 40.99 se cobra 40.90, o sea nueve
# céntimos, no cinco. Ése es el techo.
#
# Por encima de 0.09 el descuadre ya no es redondeo: es una línea que
# perdió su importe o un IGV que no corresponde, y eso hay que mirarlo, no
# ajustarlo.
REDONDEO_MAXIMO = 0.09


def redondeo_derivado(neto, igv, total):
    """El `nRedondeo` de la cabecera: lo que le falta a `neto + igv` para
    llegar al total del comprobante.

    SE DERIVA, NO SE LEE. El `cbc:PayableRoundingAmount` del UBL viene en
    POSITIVO aunque reste: la factura F402-358580 de WONG (CENCOSUD)
    declara 0.09 y su aritmética es 34.73 + 6.26 = 40.99 contra un
    `PayableAmount` de **40.90**. Creerle al signo dejaría el documento
    18 céntimos arriba. La ecuación que valida el Almacén —y que muestra
    la franja de totales de su formulario— es

        neto + impuesto + redondeo = total

    y tiene una sola incógnita, así que el redondeo se despeja.

    Sin esto el importador rechazaba el documento («El total no cuadra:
    neto + impuesto + redondeo = 40.99 pero el comprobante dice 40.90»),
    que es el rechazo correcto ante un XML incoherente — sólo que el XML
    lo armaba esta función mandando `nRedondeo` en cero.

    Un descuadre MAYOR a `REDONDEO_MAXIMO` no se absorbe: se deja el
    redondeo en cero a propósito, para que el importador rechace el
    documento. La red de seguridad de "si una línea perdió su importe,
    que no entre" vive justamente en esa validación, y taparla con un
    ajuste de cabecera la anularía.
    """
    d = round(_num(total) - (_num(neto) + _num(igv)), 2)
    if d == 0 or abs(d) > REDONDEO_MAXIMO + 1e-9:
        # `d == 0` cubre el `-0.0` que sale de restar floats que ya
        # cuadran: `_dec` lo escribiría "-0.00", que es un número raro de
        # ver en un XML que va a una base de datos.
        return 0.0
    return d


def _total_documento(doc, totales, neto, igv):
    """El importe total del documento.

    Prioridad: el `PayableAmount` del comprobante, que es el campo
    obligatorio del estándar de SUNAT y el que SUNAT registra —se verificó
    contra el SIRE en 440 facturas—. Si el XML no se pudo leer, se
    reconstruye desde el neto ya armado.

    Recibe el `neto` entero —líneas + cargos + ISC— y no sus partes: la
    reconstrucción tiene que usar el MISMO número que va a la cabecera, o
    el redondeo derivado sale distinto de cero por el término que se
    olvidó. Es lo que pasaba con el ISC antes de la regla #314.
    """
    del doc  # se conserva en la firma por si vuelve a hacer falta
    if totales and totales.get("total") is not None:
        return totales["total"]
    return neto + igv


def _dec(v, n=2):
    return f"{_num(v):.{n}f}"


def _fecha_iso(v):
    if v is None:
        return dt.date.today().isoformat()
    try:
        return v.date().isoformat()
    except AttributeError:
        pass
    try:
        return dt.datetime.fromisoformat(str(v)[:19]).date().isoformat()
    except ValueError:
        return str(v)[:10]


# ---------------------------------------------------------------------------
# LA SEÑAL EN R2 Y SU ESTADO
# ---------------------------------------------------------------------------

@st.cache_data(ttl=10, show_spinner=False)
def _hay_senal(clave):
    """True si la señal sigue en R2 (nadie la atendió todavía).

    TTL corto: el servicio revisa cada 5 seg, así que esto cambia de estado
    mientras el usuario mira la pantalla."""
    import data

    if not data.secrets_disponibles():
        return False
    try:
        data.get_s3_cliente().head_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave)
        return True
    except Exception:
        return False


@st.cache_data(ttl=10, show_spinner=False)
def _leer_recibo(clave):
    import data

    if not data.secrets_disponibles():
        return None
    try:
        crudo = data.get_s3_cliente().get_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave)["Body"].read()
        return json.loads(crudo)
    except Exception:
        return None


def importacion_pendiente(doc):
    """True si ya se pidió importar este documento y no lo atendieron."""
    return _hay_senal(clave_importacion(doc))


def recibo_importacion(doc):
    """El resultado de la última importación, o None.

    `{ok: True, correlativo: "202608-0292", ...}` si entró, o
    `{ok: False, error: "..."}` si el importador la rechazó — que es lo
    que pasa cuando el comprobante no cuadra contra su propia aritmética.
    """
    return _leer_recibo(clave_recibo(doc))


def solicitar_importacion(doc, lineas_xml, filas_sistema, totales=None):
    """Deja la señal en R2. Devuelve (ok, mensaje)."""
    import data

    if not data.secrets_disponibles():
        return False, "No hay credenciales de R2 configuradas."

    faltan = [f for f in filas_sistema if not str(f.get("_cod_sis") or "").strip()]
    if faltan:
        return False, (
            f"{len(faltan)} línea(s) sin producto asignado. Hay que "
            "completarlas antes de importar.")

    try:
        xml = construir_xml(doc, lineas_xml, filas_sistema, totales)
    except Exception as e:
        return False, f"No pude armar el XML: {e}"

    s3 = data.get_s3_cliente()
    bucket = st.secrets["R2_BUCKET"]
    try:
        s3.put_object(Bucket=bucket, Key=clave_importacion(doc), Body=xml,
                      ContentType="application/xml")
    except Exception as e:
        return False, f"No pude dejar la solicitud en R2: {e}"

    # El recibo anterior se borra: este pedido es un reintento, y dejarlo
    # haría que la pantalla siguiera mostrando el resultado viejo mientras
    # el nuevo está en curso.
    try:
        s3.delete_object(Bucket=bucket, Key=clave_recibo(doc))
    except Exception:
        pass
    _hay_senal.clear()
    _leer_recibo.clear()
    return True, "Solicitud enviada."
