"""
sunat.py — capa de datos del SIRE Compras (RCE) de SUNAT.

Hermano de `data.py`: mismo papel (traer datos de una fuente remota y
devolver un DataFrame) pero contra la API de SUNAT en vez de R2. La UI que
lo consume vive en `graficos/compras/sunat.py`.

QUÉ TRAE Y QUÉ NO
-----------------
El SIRE RCE devuelve el REGISTRO de los comprobantes que los proveedores
emitieron hacia nuestro RUC: quién emitió, qué serie/número, cuándo, base
imponible, IGV, total. Es la "propuesta" que SUNAT arma sola y que el
contribuyente acepta cada período.

NO devuelve el PDF ni el XML original del proveedor. Eso es otro servicio
(la descarga masiva de CPE, del lado de `cpe.sunat.gob.pe`), con otras
credenciales y otro flujo. Costó media hora de investigación descubrirlo,
así que queda escrito acá: si alguien pide "el PDF que mandó el proveedor",
no está en esta API.

Lo que SÍ se puede hacer con lo que hay —y es lo que hace `ficha_pdf()`—
es RENDERIZAR el comprobante a partir de los datos del registro. Sale un
PDF de verdad, legible e imprimible, con todo lo que SUNAT tiene anotado
del documento. No es el original escaneado; es la ficha oficial del dato.

EL FLUJO ES ASÍNCRONO (y no es un capricho del cliente)
-------------------------------------------------------
SUNAT no devuelve los comprobantes en la respuesta. El camino es:

    1. exportacioncomprobantepropuesta  → devuelve un numTicket
    2. consultaestadotickets            → se consulta hasta que termina
    3. archivoreporte                   → baja un ZIP con el txt/csv

`obtener_comprobantes()` encapsula los tres pasos. Por eso tarda unos
segundos la primera vez y por eso está cacheado: no es una consulta, es un
trabajo que SUNAT encola.

ENDPOINTS: DE DÓNDE SALEN
-------------------------
Transcritos del «Manual de servicios Web Api - SIRE_Compras v22» publicado
en cpe.sunat.gob.pe (secciones 5.1, 5.31, 5.32, 5.33 y 5.34). No son
inventados ni copiados de un blog. Existe una v27 más nueva: si algo
responde 404, ese es el primer sitio donde mirar.

MODO DEMO
---------
Igual que `data.py`: sin credenciales, datos sintéticos deterministas. No
es decoración — permite abrir la vista, revisar el layout y correr los
tests sin tocar SUNAT ni tener un RUC a mano.
"""

import io
import zipfile

import numpy as np
import pandas as pd
import streamlit as st

from utils import _norm

# ===========================================================================
# ENDPOINTS  (Manual Web Api SIRE_Compras v22)
# ===========================================================================

URL_TOKEN = ("https://api-seguridad.sunat.gob.pe/v1/clientessol/"
             "{client_id}/oauth2/token/")
"""§5.1 Servicio Api Seguridad. OAuth2 `password` grant."""

_BASE_SIRE = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros"

URL_EXPORTAR_PROPUESTA = (
    _BASE_SIRE + "/rce/propuesta/web/propuesta/{periodo}"
    "/exportacioncomprobantepropuesta")
"""§5.34 descargar propuesta. Devuelve `numTicket`, no los datos."""

URL_ESTADO_TICKET = (
    _BASE_SIRE + "/rvierce/gestionprocesosmasivos/web/masivo"
    "/consultaestadotickets")
"""§5.31 consultar estado ticket."""

URL_DESCARGAR_ARCHIVO = (
    _BASE_SIRE + "/rvierce/gestionprocesosmasivos/web/masivo/archivoreporte")
"""§5.32 descargar archivo (ZIP particionado)."""

URL_PERIODOS = _BASE_SIRE + "/rvierce/padron/web/omisos/{cod_libro}/periodos"
"""§5.33 consultar año y mes del RCE."""

COD_LIBRO_RCE = "080000"
"""Código de libro del Registro de Compras Electrónico (§5.33)."""

COD_ORIGEN_API = "2"
"""`codOrigenEnvio`: 2 = Servicio API (§5.34, obligatorio)."""

SCOPE = "https://api-sire.sunat.gob.pe"

# Timeouts generosos: SUNAT es lenta y un timeout corto se lee como caída.
_TIMEOUT = 60
_TIMEOUT_TOKEN = 30

# Polling del ticket. SUNAT encola el trabajo; 40 intentos x 3s = 2 min de
# techo, que en la práctica alcanza salvo períodos muy grandes.
_POLL_INTENTOS = 40
_POLL_ESPERA = 3

# Estados de `codEstadoProceso` (§5.31). SUNAT documenta los códigos en el
# Anexo I; los que importan acá son terminados-con-éxito vs terminados-con-
# error. Se comparan como string porque la API los devuelve así.
_TICKET_OK = {"06", "6"}
_TICKET_ERROR = {"07", "7", "08", "8", "09", "9"}


# ===========================================================================
# CREDENCIALES
# ===========================================================================
# Van en .streamlit/secrets.toml (local) y en los secrets de Streamlit Cloud.
# NUNCA en el repo: este módulo solo las lee, jamás las escribe ni las
# imprime — ni siquiera en un mensaje de error (ver `_mensaje_error`).

_SECRETS_SUNAT = ("SUNAT_RUC", "SUNAT_USUARIO_SOL", "SUNAT_CLAVE_SOL",
                  "SUNAT_CLIENT_ID", "SUNAT_CLIENT_SECRET")


def secrets_disponibles():
    """True si están las 5 credenciales de SUNAT. Nunca lanza excepción.

    Gemela de `data.py::secrets_disponibles`, y con el mismo propósito: que
    la app abra en modo demo en vez de reventar cuando falta configuración.
    """
    try:
        return all(k in st.secrets for k in _SECRETS_SUNAT)
    except Exception:
        return False


def _cred(clave):
    return str(st.secrets[clave]).strip()


# ===========================================================================
# FUNCIONES PURAS  (testeadas en test_sunat.py, sin red ni Streamlit)
# ===========================================================================

def periodo_valido(periodo):
    """True si `periodo` cumple el formato `yyyymm` que exige SUNAT.

    Es la validación que la API devuelve como error 1006. Vale hacerla acá
    porque un período mal armado gasta un round-trip y un token para nada.
    """
    p = str(periodo).strip()
    if len(p) != 6 or not p.isdigit():
        return False
    return 1 <= int(p[4:]) <= 12 and int(p[:4]) >= 2000


def periodo_desde_fecha(fecha):
    """`yyyymm` de un date/datetime/Timestamp."""
    return f"{fecha.year:04d}{fecha.month:02d}"


def periodos_entre(inicio, fin):
    """Lista de períodos `yyyymm` que cubren el rango [inicio, fin].

    El eje temporal de la app es un RANGO DE FECHAS (ver `estado_rango.py`),
    pero SUNAT razona por período tributario mensual. Esta función es el
    puente: un rango del 15/01 al 03/03 son tres períodos, no dos fechas.
    """
    if inicio is None or fin is None:
        return []
    if fin < inicio:
        inicio, fin = fin, inicio
    meses = pd.period_range(pd.Timestamp(inicio).to_period("M"),
                            pd.Timestamp(fin).to_period("M"), freq="M")
    return [f"{m.year:04d}{m.month:02d}" for m in meses]


# Tipos de comprobante — tabla 10 del anexo de la RS 112-2021/SUNAT. Solo
# los que aparecen en un registro de COMPRAS con volumen; el resto cae al
# `.get(cod, cod)` y se muestra con su código, que es mejor que "Otro".
TIPOS_CDP = {
    "01": "Factura",
    "03": "Boleta de venta",
    "07": "Nota de crédito",
    "08": "Nota de débito",
    "14": "Recibo de servicios",
    "12": "Ticket de máquina registradora",
    "02": "Recibo por honorarios",
    "50": "Declaración Única de Aduanas",
    "52": "Despacho simplificado",
    "91": "Comprobante de no domiciliado",
}


def nombre_tipo_cdp(cod):
    """Nombre legible de un código de tipo de comprobante."""
    return TIPOS_CDP.get(str(cod).strip().zfill(2), str(cod).strip())


# Mapa de columnas: nombre normalizado que manda SUNAT → nombre canónico
# que usa la app. Se matchea por `_norm` (sin acentos, espacios ni guiones)
# y por SUBCADENA, a propósito: el layout del archivo lo fija una resolución
# (RS 112-2021, anexo 8) que ha cambiado de nombres entre versiones, y un
# match exacto se rompe con que le agreguen un paréntesis a un encabezado.
#
# DENTRO de cada tupla los alias van del MÁS específico al más genérico, y
# se prueban en ese orden (ver `normalizar_columnas`). Importa: el archivo
# real trae tanto "Fecha de emisión" como "Año emisión CDP", y un alias
# suelto `"emision"` primero se llevaría la que apareciera antes en el
# archivo — o sea, el año en vez de la fecha, en silencio.
#
# Ojo con el "de" intercalado: `_norm("Fecha de emisión")` da
# `fechadeemision`, que NO contiene `fechaemision`. Por eso ambas variantes
# están listadas. Lo cazó test_sunat.py.
_ALIAS_COLUMNAS = (
    ("periodo",            ("periodo",)),
    ("car",                ("carsunat", "codcar", "numcar")),
    ("fecha_emision",      ("fechadeemision", "fechaemision", "fecemision")),
    ("fecha_vencimiento",  ("fechadevcto", "fechavcto", "fechavencimiento",
                            "fecvcto")),
    ("tipo_cdp",           ("tipocpdoc", "codtipocdp", "tipocp",
                            "tipodedocumento", "tipodocumento")),
    ("serie",              ("seriedelcdp", "numseriecdp", "serie")),
    ("numero",             ("nrocpodoc", "numcdp", "numerocp", "nrocp")),
    ("ruc_proveedor",      ("nrodocidentidad", "numdocidentidad",
                            "rucproveedor", "nrodedocidentidad")),
    ("proveedor",          ("apellidosnombres", "razonsocial",
                            "nombreproveedor")),
    ("base_imponible",     ("bigravado", "baseimponible", "mtobigravado")),
    ("igv",                ("igvipm", "mtoigv", "igv")),
    ("no_gravado",         ("mtoinafecto", "inafecto", "exonerado")),
    ("total",              ("totalcp", "mtototalcp", "importetotal", "total")),
    ("moneda",             ("codmoneda", "tipomoneda", "moneda")),
    ("tipo_cambio",        ("tipodecambio", "tipocambio")),
)


def normalizar_columnas(df):
    """Renombra las columnas de SUNAT a los nombres canónicos de la app.

    Devuelve una copia con SOLO las columnas reconocidas, en orden canónico.
    Las que no se reconocen se descartan: son ~40 y la vista usa 13.

    Por qué no un `df.rename(dict)` y listo: el archivo de la propuesta no
    trae siempre los mismos encabezados (ver comentario de
    `_ALIAS_COLUMNAS`), así que el match es por subcadena normalizada.

    El recorrido es alias-por-alias y no columna-por-columna: así el alias
    más específico se lleva su columna antes de que uno genérico pueda
    robársela. Cada columna se consume una sola vez (`usadas`).
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[c for c, _ in _ALIAS_COLUMNAS])

    normalizadas = {c: _norm(c) for c in df.columns}
    salida = {}
    usadas = set()
    for canonico, alias in _ALIAS_COLUMNAS:
        elegida = None
        for a in alias:
            for col, norm in normalizadas.items():
                if col not in usadas and a in norm:
                    elegida = col
                    break
            if elegida:
                break
        if elegida:
            salida[canonico] = df[elegida]
            usadas.add(elegida)
    return pd.DataFrame(salida)


def _a_numero(serie):
    """Serie numérica tolerante al formato de SUNAT (coma decimal, miles)."""
    if serie is None:
        return None
    s = serie.astype(str).str.strip()
    # "1.234,56" (europeo) vs "1234.56". Se detecta por la ÚLTIMA coma:
    # si viene después del último punto, la coma es el separador decimal.
    europeo = s.str.rfind(",") > s.str.rfind(".")
    s = s.where(~europeo, s.str.replace(".", "", regex=False)
                           .str.replace(",", ".", regex=False))
    s = s.where(europeo, s.str.replace(",", "", regex=False))
    return pd.to_numeric(s, errors="coerce")


def parsear_propuesta(texto):
    """DataFrame canónico a partir del contenido del archivo de la propuesta.

    Acepta el csv (`codTipoArchivo=1`) y el txt separado por `|`
    (`codTipoArchivo=0`), porque el delimitador se detecta de la primera
    línea en vez de asumirse.
    """
    if not texto or not texto.strip():
        return normalizar_columnas(None)

    primera = texto.splitlines()[0]
    sep = max("|,;\t", key=primera.count)
    try:
        crudo = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str,
                            engine="python", on_bad_lines="skip")
    except Exception:
        return normalizar_columnas(None)

    df = normalizar_columnas(crudo)
    if df.empty:
        return df

    for col in ("base_imponible", "igv", "no_gravado", "total", "tipo_cambio"):
        if col in df.columns:
            df[col] = _a_numero(df[col])
    for col in ("fecha_emision", "fecha_vencimiento"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    if "tipo_cdp" in df.columns:
        df["tipo_cdp"] = df["tipo_cdp"].astype(str).str.strip().str.zfill(2)
        df["tipo_nombre"] = df["tipo_cdp"].map(nombre_tipo_cdp)
    if {"serie", "numero"} <= set(df.columns):
        df["documento"] = (df["serie"].astype(str).str.strip() + "-"
                           + df["numero"].astype(str).str.strip())
    return df


def _extraer_texto_zip(contenido):
    """Texto del primer archivo de datos dentro del ZIP que manda SUNAT.

    `archivoreporte` devuelve un ZIP (a veces particionado). Si lo que llega
    no es un ZIP, se asume que ya es el texto plano — SUNAT lo devuelve así
    cuando el reporte es chico, y tratarlo como error sería un falso
    negativo.
    """
    if not contenido:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            nombres = [n for n in z.namelist()
                       if n.lower().endswith((".txt", ".csv"))] or z.namelist()
            if not nombres:
                return ""
            with z.open(nombres[0]) as f:
                return f.read().decode("latin-1", errors="replace")
    except zipfile.BadZipFile:
        return contenido.decode("latin-1", errors="replace")


# ===========================================================================
# CLIENTE HTTP
# ===========================================================================

def _mensaje_error(exc):
    """Texto de error seguro de mostrar en pantalla.

    Las credenciales viajan en el body del POST del token; un `repr` de la
    excepción de `requests` puede arrastrar la request entera. Se recorta a
    la clase y el texto, y se tapa cualquier eco de un secret.
    """
    txt = f"{type(exc).__name__}: {exc}"
    try:
        for clave in _SECRETS_SUNAT:
            valor = st.secrets.get(clave)
            if valor and str(valor) in txt:
                txt = txt.replace(str(valor), "***")
    except Exception:
        pass
    return txt[:400]


@st.cache_data(ttl=3000, show_spinner=False)
def obtener_token():
    """Token OAuth2 de SUNAT (§5.1). Cacheado 50 min — dura 60.

    El TTL va por debajo de la vida del token a propósito: con 60 min
    exactos, la última consulta de la ventana sale con un token vencido y
    el error que devuelve SUNAT (401 sin cuerpo) no se parece en nada a
    "el token expiró".
    """
    import requests

    resp = requests.post(
        URL_TOKEN.format(client_id=_cred("SUNAT_CLIENT_ID")),
        data={
            "grant_type": "password",
            "scope": SCOPE,
            "client_id": _cred("SUNAT_CLIENT_ID"),
            "client_secret": _cred("SUNAT_CLIENT_SECRET"),
            # §5.1: `username` es RUC y usuario SOL CONCATENADOS, sin
            # separador. Con un espacio en el medio SUNAT responde 401.
            "username": _cred("SUNAT_RUC") + _cred("SUNAT_USUARIO_SOL"),
            "password": _cred("SUNAT_CLAVE_SOL"),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=_TIMEOUT_TOKEN,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("SUNAT no devolvió access_token.")
    return token


def _get(url, token, params=None, binario=False):
    import requests

    resp = requests.get(
        url, params=params, timeout=_TIMEOUT,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/json"},
    )
    resp.raise_for_status()
    return resp.content if binario else resp.json()


def _esperar_ticket(token, num_ticket, periodo, progreso=None):
    """Consulta el ticket hasta que SUNAT termina de generar el archivo.

    Devuelve `(nom_archivo, cod_tipo_archivo)` o lanza. `progreso` es un
    callable opcional que recibe el intento — lo usa la UI para mover una
    barra sin que este módulo sepa nada de Streamlit.
    """
    import time

    for intento in range(_POLL_INTENTOS):
        if progreso:
            progreso(intento / _POLL_INTENTOS)
        datos = _get(URL_ESTADO_TICKET, token, params={
            "perIni": periodo, "perFin": periodo,
            "page": 1, "perPage": 20, "numTicket": num_ticket,
        })
        for reg in (datos.get("registros") or []):
            if str(reg.get("numTicket")) != str(num_ticket):
                continue
            estado = str(reg.get("codEstadoProceso", "")).strip()
            archivo = reg.get("archivoReporte") or []
            if isinstance(archivo, dict):
                archivo = [archivo]
            if estado in _TICKET_OK and archivo:
                a = archivo[0]
                return a.get("nomArchivoReporte"), a.get("codTipoArchivoReporte")
            if estado in _TICKET_ERROR:
                raise RuntimeError(
                    "SUNAT terminó el proceso con error: "
                    f"{reg.get('desEstadoProceso') or estado}")
        time.sleep(_POLL_ESPERA)
    raise TimeoutError(
        f"SUNAT no terminó de generar el archivo del ticket {num_ticket} "
        f"en {_POLL_INTENTOS * _POLL_ESPERA}s.")


# ===========================================================================
# MODO DEMO
# ===========================================================================

_PROVEEDORES_DEMO = [
    ("20100047218", "DISTRIBUIDORA ALIMENTARIA DEL SUR S.A.C."),
    ("20512345678", "COMERCIAL LOS ANDES E.I.R.L."),
    ("20603344551", "FRIGORIFICO PACIFICO S.A."),
    ("20477889900", "INSUMOS Y ABARROTES DEL NORTE S.R.L."),
    ("20556677889", "LACTEOS SIERRA VERDE S.A.C."),
    ("10456789012", "QUISPE MAMANI ROSA ELENA"),
    ("20334455667", "PESQUERA COSTA AZUL S.A.C."),
    ("20221133445", "SERVICIOS LOGISTICOS RAPIDOS S.A."),
]


def _datos_demo(periodo, filas=48):
    """Propuesta sintética determinista para un período.

    La semilla sale del período (crc32, no `hash()`: el hash de str va
    salteado por proceso y el demo cambiaría en cada reinicio — la misma
    trampa que documenta `data.py::_datos_demo`).
    """
    import zlib

    rng = np.random.default_rng(zlib.crc32(str(periodo).encode()))
    anio, mes = int(str(periodo)[:4]), int(str(periodo)[4:])
    dias_mes = pd.Period(f"{anio}-{mes:02d}").days_in_month

    idx = rng.integers(0, len(_PROVEEDORES_DEMO), filas)
    rucs = [_PROVEEDORES_DEMO[i][0] for i in idx]
    nombres = [_PROVEEDORES_DEMO[i][1] for i in idx]
    tipos = rng.choice(["01", "01", "01", "03", "07", "14"], filas)
    dias = rng.integers(1, dias_mes + 1, filas)
    base = np.round(rng.gamma(2.2, 900, filas) + 60, 2)
    # Las notas de crédito restan: sin esto el total del demo no cuadra con
    # cómo se lee un registro de compras real.
    base = np.where(tipos == "07", -base, base)
    igv = np.round(base * 0.18, 2)

    df = pd.DataFrame({
        "periodo": str(periodo),
        "car": [f"{anio}{i:023d}" for i in range(filas)],
        "fecha_emision": pd.to_datetime(
            [f"{anio}-{mes:02d}-{d:02d}" for d in dias]),
        "tipo_cdp": tipos,
        "serie": [("F001" if t in ("01", "07") else "B001") for t in tipos],
        "numero": [f"{n:08d}" for n in rng.integers(1, 99999, filas)],
        "ruc_proveedor": rucs,
        "proveedor": nombres,
        "base_imponible": base,
        "igv": igv,
        "no_gravado": 0.0,
        "total": np.round(base + igv, 2),
        "moneda": "PEN",
        "tipo_cambio": 1.0,
    })
    df["fecha_vencimiento"] = df["fecha_emision"] + pd.Timedelta(days=30)
    df["tipo_nombre"] = df["tipo_cdp"].map(nombre_tipo_cdp)
    df["documento"] = df["serie"] + "-" + df["numero"]
    return df.sort_values("fecha_emision").reset_index(drop=True)


# ===========================================================================
# API PÚBLICA
# ===========================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_comprobantes(periodo, _progreso=None):
    """Comprobantes que los proveedores emitieron hacia nuestro RUC.

    Orquesta los tres pasos del flujo asíncrono (exportar → ticket →
    descargar) y devuelve el DataFrame canónico ya parseado.

    Cacheado 1h porque cada llamada le encola un trabajo a SUNAT: sin caché,
    cada rerun de Streamlit —y hay uno por clic— dispararía uno nuevo. El
    botón "Actualizar" de la UI limpia la caché a mano cuando el usuario
    quiere el dato fresco de verdad.

    `_progreso` va con guion bajo para que Streamlit NO lo hashee (es un
    callable, y hashearlo invalidaría la caché en cada rerun).
    """
    if not periodo_valido(periodo):
        raise ValueError(f"Período '{periodo}' no cumple el formato yyyymm.")

    if not secrets_disponibles():
        return _datos_demo(periodo)

    token = obtener_token()
    ticket = _get(URL_EXPORTAR_PROPUESTA.format(periodo=periodo), token,
                  params={"codTipoArchivo": 1, "codOrigenEnvio": COD_ORIGEN_API})
    num_ticket = ticket.get("numTicket")
    if not num_ticket:
        raise RuntimeError("SUNAT no devolvió numTicket al pedir la propuesta.")

    nombre, cod_tipo = _esperar_ticket(token, num_ticket, periodo, _progreso)
    contenido = _get(URL_DESCARGAR_ARCHIVO, token, binario=True, params={
        "nomArchivoReporte": nombre,
        # §5.32: si el ticket devolvió null hay que reenviar null, no "".
        "codTipoArchivoReporte": cod_tipo if cod_tipo is not None else "null",
    })
    return parsear_propuesta(_extraer_texto_zip(contenido))


@st.cache_data(ttl=3600, show_spinner=False)
def periodos_disponibles():
    """Períodos `yyyymm` habilitados para el contribuyente (§5.33).

    En modo demo: los 12 meses hasta hoy, para que el selector tenga algo
    que ofrecer sin inventar años que no existen.
    """
    if not secrets_disponibles():
        hoy = pd.Timestamp.today()
        return [periodo_desde_fecha(hoy - pd.DateOffset(months=i))
                for i in range(12)]

    datos = _get(URL_PERIODOS.format(cod_libro=COD_LIBRO_RCE), obtener_token())
    registros = datos if isinstance(datos, list) else datos.get("registros", [])
    periodos = [str(p.get("perTributario"))
                for reg in registros
                for p in (reg.get("lisPeriodos") or [])
                if p.get("perTributario")]
    return sorted(set(periodos), reverse=True)


# ===========================================================================
# LA FICHA DEL COMPROBANTE
# ===========================================================================
# Dos representaciones del MISMO comprobante:
#   · `campos_ficha()` — qué se muestra y en qué orden. Fuente única.
#   · `ficha_pdf()`    — el archivo que el usuario se lleva.
# La versión en pantalla (HTML) vive en graficos/compras/documentos_sunat.py
# y también consume `campos_ficha()`.
#
# Están separadas porque el PDF NO se puede mostrar embebido: Chrome no
# renderiza un `data:application/pdf` dentro de un iframe con `sandbox`, y
# Streamlit monta todos sus iframes así (verificado en el navegador el
# 2026-08-19: el frame carga con el alto correcto y `contentDocument` en
# null). De ahí que la pantalla sea HTML y la descarga un PDF de verdad.

def _val(comprobante, clave, defecto="—"):
    """Valor de un campo, formateado para mostrar. `—` si falta."""
    v = comprobante.get(clave)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return defecto
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    return str(v)


def _soles(comprobante, clave):
    v = comprobante.get(clave)
    try:
        return f"S/ {float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def campos_ficha(comprobante):
    """Secciones de la ficha: `((titulo, ((etiqueta, valor), …)), …)`.

    Fuente ÚNICA de qué se muestra y en qué orden, para que la ficha en
    pantalla y el PDF descargado no puedan divergir. Agregar un campo es
    tocar solo esta función.
    """
    return (
        ("Emisor", (
            ("RUC", _val(comprobante, "ruc_proveedor")),
            ("Razón social", _val(comprobante, "proveedor")[:52]),
        )),
        ("Documento", (
            ("Serie - Número", _val(comprobante, "documento")),
            ("Tipo de comprobante",
             nombre_tipo_cdp(comprobante.get("tipo_cdp", ""))),
            ("Fecha de emisión", _val(comprobante, "fecha_emision")),
            ("Fecha de vencimiento", _val(comprobante, "fecha_vencimiento")),
            ("Período tributario", _val(comprobante, "periodo")),
            ("Moneda", _val(comprobante, "moneda")),
        )),
        ("Importes", (
            ("Base imponible", _soles(comprobante, "base_imponible")),
            ("IGV / IPM", _soles(comprobante, "igv")),
            ("No gravado", _soles(comprobante, "no_gravado")),
        )),
    )


PIE_FICHA = ("Ficha generada desde el Registro de Compras Electrónico (SIRE) "
             "de SUNAT. No sustituye al comprobante electrónico emitido por "
             "el proveedor.")


# Por qué matplotlib y no reportlab/weasyprint: matplotlib YA es una
# dependencia del proyecto (requirements.txt) y su backend PDF es vectorial,
# así que la ficha sale como texto seleccionable y no como imagen. Sumar una
# librería de PDF para dibujar 20 líneas de texto no se justificaba.

def ficha_pdf(comprobante):
    """PDF de una página con los datos que SUNAT tiene del comprobante.

    `comprobante` es un dict/Series con las columnas canónicas. Devuelve
    bytes listos para `st.download_button`.

    NO es el PDF que emitió el proveedor (ver el docstring del módulo): es
    la ficha del registro, construida con lo que devuelve el SIRE. El pie
    lo dice explícitamente para que nadie la confunda con el original.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    def val(clave, defecto="—"):
        return _val(comprobante, clave, defecto)

    def soles(clave):
        return _soles(comprobante, clave)

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))   # A4 vertical, en pulgadas
        fig.patch.set_facecolor("white")
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        morado = "#6c5ce7"
        gris = "#71717a"
        tinta = "#18181d"

        ax.add_patch(plt.Rectangle((0, 0.93), 1, 0.07, color=morado))
        ax.text(0.07, 0.955, nombre_tipo_cdp(comprobante.get("tipo_cdp", "")).upper(),
                color="white", fontsize=17, weight="bold", va="center")
        ax.text(0.93, 0.955, val("documento"), color="white", fontsize=15,
                weight="bold", va="center", ha="right")

        y = 0.87

        def bloque(titulo, filas):
            nonlocal y
            ax.text(0.07, y, titulo.upper(), color=morado, fontsize=9,
                    weight="bold")
            ax.plot([0.07, 0.93], [y - 0.012, y - 0.012], color="#e6e6eb", lw=1)
            y -= 0.038
            for etiqueta, valor in filas:
                ax.text(0.07, y, etiqueta, color=gris, fontsize=9.5)
                # weight="normal" y no "medium": DejaVu Sans (la que trae
                # matplotlib) no tiene medium, y cada texto emitía un
                # `findfont: Failed to find font weight medium` al log.
                ax.text(0.93, y, valor, color=tinta, fontsize=10.5,
                        ha="right", weight="normal")
                y -= 0.030
            y -= 0.022

        for titulo, filas in campos_ficha(comprobante):
            bloque(titulo, filas)

        ax.add_patch(plt.Rectangle((0.07, y - 0.045), 0.86, 0.055,
                                   color="#f0edfe"))
        ax.text(0.10, y - 0.018, "TOTAL", color="#4938b8", fontsize=12,
                weight="bold", va="center")
        ax.text(0.90, y - 0.018, soles("total"), color="#4938b8", fontsize=15,
                weight="bold", va="center", ha="right")

        ax.text(0.07, 0.055, f"CAR SUNAT: {val('car')}", color=gris, fontsize=7.5)
        ax.plot([0.07, 0.93], [0.042, 0.042], color="#e6e6eb", lw=1)
        ax.text(0.07, 0.024, PIE_FICHA, color=gris, fontsize=7.5, va="top",
                wrap=True)

        pdf.savefig(fig)
        plt.close(fig)

    return buf.getvalue()
