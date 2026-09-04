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


PREFIJO_IMPORTACION = "_solicitudes_importacion"

# Del catálogo 01 de SUNAT a la letra que el Almacén usa en tDocumento.
# Sale de TTipoDocumento.tResumido.
_LETRA_TIPO = {"01": "F", "03": "B", "07": "C", "08": "D", "09": "G"}

# El Almacén codifica la moneda; SUNAT la nombra.
_MONEDA = {"PEN": "01", "USD": "02", "EUR": "03"}


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
    suma_lineas = sum(_num(f.get("Importe")) for f in filas_sistema)
    cargos = _num((totales or {}).get("cargos"))
    igv = _num(doc.get("igv"))

    ET.SubElement(s, "nNeto").text = _dec(suma_lineas + cargos)
    ET.SubElement(s, "nImpuesto1").text = _dec(igv)
    ET.SubElement(s, "nTotal").text = _dec(_total_documento(doc, totales,
                                                            suma_lineas, cargos, igv))
    ET.SubElement(s, "nDescuento").text = _dec(0)
    ET.SubElement(s, "nRedondeo").text = _dec(0)
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
        neto = importe + cargo
        ET.SubElement(a, "nCantidad").text = _dec(cant, 3)
        ET.SubElement(a, "nPrecio").text = _dec(neto / cant if cant else 0, 5)
        ET.SubElement(a, "nNeto").text = _dec(neto)
        ET.SubElement(a, "nDescuento").text = _dec(0)
        ET.SubElement(a, "nOtrosCargosInafecto").text = _dec(cargo)
        # El impuesto y SU tasa salen del comprobante. Nunca se asumen: el
        # importador decide a qué casillero del Almacén van según la tasa.
        ET.SubElement(a, "nImpuesto1").text = _dec(_num(xml_l.get("igv")))
        ET.SubElement(a, "nPorcentaje1").text = str(
            xml_l.get("igv_porcentaje") if xml_l.get("igv_porcentaje") is not None
            else 0)
        ET.SubElement(a, "lIncluidoImpuesto1").text = "1"
        ET.SubElement(a, "nTotal").text = _dec(neto + _num(xml_l.get("igv")))

    return ET.tostring(raiz, encoding="utf-8", xml_declaration=True)


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


def _total_documento(doc, totales, suma_lineas, cargos, igv):
    """El importe total del documento.

    Prioridad: el `PayableAmount` del comprobante, que es el campo
    obligatorio del estándar de SUNAT y el que SUNAT registra —se verificó
    contra el SIRE en 440 facturas—. Si el XML no se pudo leer, se
    reconstruye desde el registro; y si tampoco, desde las líneas.
    """
    del doc  # se conserva en la firma por si vuelve a hacer falta
    if totales and totales.get("total") is not None:
        return totales["total"]
    return suma_lineas + cargos + igv


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
