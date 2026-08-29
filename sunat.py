"""
sunat.py — capa de datos del SIRE Compras (RCE) de SUNAT.

Hermano de `data.py`: mismo papel (traer datos de una fuente remota y
devolver un DataFrame) pero contra la API de SUNAT en vez de R2. La UI que
lo consume vive en `graficos/compras/documentos_sunat.py`.

QUÉ TRAE Y QUÉ NO
-----------------
Devuelve el REGISTRO de los comprobantes que los proveedores emitieron
hacia nuestro RUC: quién emitió, serie/número, fechas, base imponible,
IGV, moneda, estado, detracción. Es la "propuesta" que SUNAT arma sola a
partir de los comprobantes electrónicos.

NO devuelve el PDF ni el XML original del proveedor. Eso es otro servicio
(descarga masiva de CPE, del lado de `cpe.sunat.gob.pe`), con otras
credenciales y otro flujo. Queda escrito acá porque cuesta descubrirlo: si
alguien pide "el PDF que mandó el proveedor", no está en esta API.

Lo que SÍ se hace con lo que hay —y es lo que hace `ficha_pdf()`— es
RENDERIZAR el comprobante a partir de los datos del registro. Sale un PDF
de verdad, con todo lo que SUNAT tiene anotado. No es el original del
proveedor; es la ficha del dato.

EL ENDPOINT QUE SE USA, Y EL QUE NO (2026-08-19)
------------------------------------------------
Se consume `…/rce/propuesta/web/propuesta/{periodo}/busqueda`, que devuelve
los comprobantes en JSON paginado, de forma SÍNCRONA. **No está en el
manual oficial de SUNAT**: se descubrió mirando las llamadas XHR que hace
el propio portal del SIRE.

El manual, en cambio, documenta un flujo ASÍNCRONO de tres pasos
(`exportacioncomprobantepropuesta` → `consultaestadotickets` →
`archivoreporte`) para bajar el mismo dato como ZIP. Ese flujo se
implementó primero y **está roto del lado de SUNAT**: el ticket se crea, se
procesa, termina con estado 06 (OK) y entrega un nombre de archivo… que
después no existe. Verificado contra el RUC 20605204300, en dos períodos,
con los dos endpoints de descarga que documenta el manual, con
`codOrigenEnvio` 1 y 2, y con todos los valores de `codTipoArchivoReporte`
(00/0/1/2/null/vacío). Siempre la misma respuesta:

    422 · cod 2244 "El archivo solicitado no existe."
    500 · com.mongodb.MongoGridFSException: No file found with the
          filename: <RUC>-<fecha>-propuesta.zip and revision: -1

O sea: SUNAT nunca escribe el archivo que su propio ticket anuncia. No es
un parámetro mal puesto de nuestro lado. Si algún día lo arreglan, el
flujo por tickets NO haría falta igual — `busqueda` es más rápido (sin
encolar nada), trae más campos y no obliga a parsear un CSV.

Dato de paso, por si vuelve a aparecer: la respuesta de
`consultaestadotickets` trae el campo mal escrito, como
`codTipoAchivoReporte` (sin la primera "r" de "Archivo"). El manual repite
el typo. Leer el nombre correcto devuelve None en silencio.

MODO DEMO
---------
Igual que `data.py`: sin credenciales, datos sintéticos deterministas.
Permite abrir la vista, revisar el layout y correr los tests sin tocar
SUNAT ni tener un RUC a mano.
"""

import datetime
import io
import re

import numpy as np
import pandas as pd
import streamlit as st

# ===========================================================================
# ENDPOINTS
# ===========================================================================

URL_TOKEN = ("https://api-seguridad.sunat.gob.pe/v1/clientessol/"
             "{client_id}/oauth2/token/")
"""§5.1 del manual — Api Seguridad. OAuth2 `password` grant."""

_BASE_SIRE = "https://api-sire.sunat.gob.pe/v1/contribuyente/migeigv/libros"

URL_BUSQUEDA = (_BASE_SIRE
                + "/rce/propuesta/web/propuesta/{periodo}/busqueda")
"""Comprobantes de la propuesta, JSON paginado y SÍNCRONO.

NO documentado en el manual: sale de las llamadas XHR del portal del SIRE
(ver el docstring del módulo). Es el que usa `obtener_comprobantes`."""

URL_PERIODOS = _BASE_SIRE + "/rvierce/padron/web/omisos/{cod_libro}/periodos"
"""§5.33 — períodos habilitados para el contribuyente."""

URL_RESUMEN = (_BASE_SIRE + "/rvierce/resumen/web/resumencomprobantes"
               "/{periodo}/{tipo}/0/exporta")
"""§5.35 — totales por tipo de comprobante (txt con `|`). Se usa como
verificación cruzada barata de que el detalle cuadra: es otra vía de SUNAT
al mismo período. `tipo`: 1 propuesta, 2 preliminar, 4 registro."""

COD_LIBRO_RCE = "080000"
"""Código de libro del Registro de Compras Electrónico (§5.33)."""

SCOPE = "https://api-sire.sunat.gob.pe"

# `codTipoOpe=1` es lo que manda el portal para listar la propuesta. Los
# otros valores no están documentados y no se exploraron.
COD_TIPO_OPE_PROPUESTA = 1

# SUNAT corta la conexión si se la golpea seguido (verificado: varios
# ConnectionReset al encadenar pruebas), así que conviene hacer pocas
# llamadas. PERO 100 es el TOPE REAL del servidor, no una elección de
# performance: perPage=150 y 200 devuelven 422 (JerseyViolationException)
# — probado en vivo antes de subirlo "para optimizar". Sin ese chequeo,
# subir este número rompe la paginación entera en silencio.
FILAS_POR_PAGINA = 100
MAX_PAGINAS = 40          # techo de seguridad, ver el bucle de paginación

_TIMEOUT = 60
_TIMEOUT_TOKEN = 30


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

    Gemela de `data.py::secrets_disponibles`, con el mismo propósito: que
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


# Tipos de comprobante — tabla 10 del anexo de la RS 112-2021/SUNAT. Es un
# FALLBACK: la API ya manda `desTipoCDP` con el nombre resuelto, y ese gana
# (ver `_normalizar_registro`). Esta tabla cubre el modo demo y cualquier
# respuesta donde el campo venga vacío.
TIPOS_CDP = {
    "01": "Factura",
    "03": "Boleta de venta",
    "07": "Nota de crédito",
    "08": "Nota de débito",
    "14": "Recibo de servicios",
    "12": "Ticket de máquina registradora",
    "02": "Recibo por honorarios",
    "30": "Documentos emitidos por Adquiriente",
    "50": "Declaración Única de Aduanas",
    "52": "Despacho simplificado",
    "91": "Comprobante de no domiciliado",
}


def nombre_tipo_cdp(cod):
    """Nombre legible de un código de tipo de comprobante."""
    return TIPOS_CDP.get(str(cod).strip().zfill(2), str(cod).strip())


def _num(valor):
    """Float tolerante: None/""/no-numérico → 0.0."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if pd.isna(v) else v


def _normalizar_registro(reg):
    """Un comprobante del JSON de SUNAT → dict con las columnas canónicas.

    Los importes vienen anidados en `montos` y el tipo de cambio en
    `tipoCambio`; acá se aplanan. `total` NO viene como campo propio: se
    suma de sus componentes (gravado + IGV + no gravado + otros), que es
    como lo arma el propio portal.

    Función pura, para poder testear el aplanado sin red.
    """
    m = reg.get("montos") or {}
    tc = reg.get("tipoCambio") or {}

    base = (_num(m.get("mtoBIGravadaDG")) + _num(m.get("mtoBIGravadaDGNG"))
            + _num(m.get("mtoBIGravadaDNG")))
    igv = (_num(m.get("mtoIgvIpmDG")) + _num(m.get("mtoIgvIpmDGNG"))
           + _num(m.get("mtoIgvIpmDNG")))
    no_gravado = (_num(m.get("mtoValorAdqNG")) + _num(m.get("mtoInafecto"))
                  + _num(m.get("mtoExonerado")))
    otros = (_num(m.get("mtoISC")) + _num(m.get("mtoIcbper"))
             + _num(m.get("mtoOtrosTributos")))

    # Si SUNAT manda el total explícito, gana sobre la suma: evita que un
    # campo de montos que no estemos contemplando descuadre la fila.
    total_api = m.get("mtoTotalCP", m.get("mtoTotal"))
    total = _num(total_api) if total_api is not None else (
        base + igv + no_gravado + otros)

    serie = str(reg.get("numSerieCDP") or "").strip()
    numero = str(reg.get("numCDP") or "").strip()
    cod_tipo = str(reg.get("codTipoCDP") or "").strip().zfill(2)

    return {
        "periodo": str(reg.get("perTributario") or ""),
        "car": str(reg.get("codCar") or ""),
        "fecha_emision": reg.get("fecEmision"),
        "fecha_vencimiento": reg.get("fecVencPag"),
        "tipo_cdp": cod_tipo,
        # `desTipoCDP` viene resuelto por SUNAT: es preferible a nuestra
        # tabla, que puede quedar vieja si agregan un tipo.
        "tipo_nombre": (reg.get("desTipoCDP") or "").strip()
                       or nombre_tipo_cdp(cod_tipo),
        "serie": serie,
        "numero": numero,
        "documento": f"{serie}-{numero}" if serie or numero else "",
        "ruc_proveedor": str(reg.get("numDocIdentidadProveedor") or ""),
        "proveedor": str(reg.get("nomRazonSocialProveedor") or ""),
        "base_imponible": base,
        "igv": igv,
        "no_gravado": no_gravado,
        "total": total,
        "moneda": str(reg.get("codMoneda") or ""),
        "tipo_cambio": _num(tc.get("mtoTipoCambio")) or 1.0,
        "estado": str(reg.get("desEstadoComprobante") or ""),
        "detraccion": str(reg.get("indDetraccion") or ""),
    }


_COLUMNAS = ("periodo", "car", "fecha_emision", "fecha_vencimiento",
             "tipo_cdp", "tipo_nombre", "serie", "numero", "documento",
             "ruc_proveedor", "proveedor", "base_imponible", "igv",
             "no_gravado", "total", "moneda", "tipo_cambio", "estado",
             "detraccion")


def registros_a_df(registros):
    """Lista de comprobantes crudos de la API → DataFrame canónico."""
    if not registros:
        return pd.DataFrame(columns=list(_COLUMNAS))
    df = pd.DataFrame([_normalizar_registro(r) for r in registros])
    for col in ("fecha_emision", "fecha_vencimiento"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df.sort_values("fecha_emision").reset_index(drop=True)


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


def _get(url, token, params=None):
    import requests

    resp = requests.get(
        url, params=params, timeout=_TIMEOUT,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/json"},
    )
    resp.raise_for_status()
    return resp


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
    tipos = rng.choice(["01", "01", "01", "03", "07", "14"], filas)
    dias = rng.integers(1, dias_mes + 1, filas)
    base = np.round(rng.gamma(2.2, 900, filas) + 60, 2)
    # Las notas de crédito restan: sin esto el total del demo no cuadra con
    # cómo se lee un registro de compras real.
    base = np.where(tipos == "07", -base, base)
    igv = np.round(base * 0.18, 2)
    series = ["E001" if t in ("01", "07") else "B001" for t in tipos]
    numeros = [f"{n:08d}" for n in rng.integers(1, 99999, filas)]

    df = pd.DataFrame({
        "periodo": str(periodo),
        "car": [f"{anio}{i:023d}" for i in range(filas)],
        "fecha_emision": pd.to_datetime(
            [f"{anio}-{mes:02d}-{d:02d}" for d in dias]),
        "tipo_cdp": tipos,
        "tipo_nombre": [nombre_tipo_cdp(t) for t in tipos],
        "serie": series,
        "numero": numeros,
        "documento": [f"{s}-{n}" for s, n in zip(series, numeros)],
        "ruc_proveedor": [_PROVEEDORES_DEMO[i][0] for i in idx],
        "proveedor": [_PROVEEDORES_DEMO[i][1] for i in idx],
        "base_imponible": base,
        "igv": igv,
        "no_gravado": 0.0,
        "total": np.round(base + igv, 2),
        "moneda": "PEN",
        "tipo_cambio": 1.0,
        "estado": "Activo",
        "detraccion": "",
    })
    df["fecha_vencimiento"] = df["fecha_emision"] + pd.Timedelta(days=30)
    return df.sort_values("fecha_emision").reset_index(drop=True)


# ===========================================================================
# API PÚBLICA
# ===========================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_comprobantes(periodo, _progreso=None):
    """Comprobantes que los proveedores emitieron hacia nuestro RUC.

    Pagina sobre `URL_BUSQUEDA` hasta traer el período completo y devuelve
    el DataFrame canónico. Es síncrono: no encola nada en SUNAT, así que
    responde en segundos.

    Cacheado 1h para no repetir la paginación en cada rerun de Streamlit
    (hay uno por clic). El botón "Actualizar" de la UI limpia la caché a
    mano cuando se quiere el dato fresco.

    `_progreso` va con guion bajo para que Streamlit NO lo hashee (es un
    callable, y hashearlo invalidaría la caché en cada rerun). Recibe la
    fracción completada, 0..1.
    """
    if not periodo_valido(periodo):
        raise ValueError(f"Período '{periodo}' no cumple el formato yyyymm.")

    if not secrets_disponibles():
        return _datos_demo(periodo)

    token = obtener_token()

    # ── LA PAGINACIÓN DE SUNAT SE SOLAPA, HAY QUE DEDUPLICAR ────────────
    # Medido contra el RUC 20605204300, período 202607 (323 comprobantes),
    # pidiendo perPage=100:
    #     page=1 → 100 registros      page=3 → 123 (!)
    #     page=2 → 200 registros (!)  page=4 →  23
    # El OFFSET avanza bien, pero el LÍMITE crece con el número de página
    # (devuelve `page * perPage` filas desde el offset), así que cada página
    # se solapa con la anterior. Acumulando a ciegas salían 446 filas y un
    # total de S/ 257.541 contra los 323 reales — un 38% inflado, sin error
    # ni aviso. El modo de fallo más caro posible en un tablero de compras:
    # el número se ve plausible y está mal.
    #
    # Se deduplica por `codCar` (Código de Anotación de Registro), que es el
    # identificador único de la anotación en SUNAT. El bucle corta cuando
    # junta el total declarado o cuando una página deja de aportar únicos.
    vistos = {}
    total_esperado = None

    for pagina in range(1, MAX_PAGINAS + 1):
        datos = _get(URL_BUSQUEDA.format(periodo=periodo), token, params={
            "codTipoOpe": COD_TIPO_OPE_PROPUESTA,
            "page": pagina,
            "perPage": FILAS_POR_PAGINA,
        }).json()

        if total_esperado is None:
            total_esperado = int(
                (datos.get("paginacion") or {}).get("totalRegistros") or 0)

        antes = len(vistos)
        for reg in (datos.get("registros") or []):
            # `codCar` como clave; si faltara, la tupla serie+número+fecha
            # identifica igual al comprobante dentro de un período.
            clave = reg.get("codCar") or (
                reg.get("numSerieCDP"), reg.get("numCDP"), reg.get("fecEmision"))
            vistos[clave] = reg

        if _progreso and total_esperado:
            _progreso(min(1.0, len(vistos) / total_esperado))

        # Corta por ÚNICOS, no por filas recibidas (que vienen infladas), y
        # también si la página no aportó nada nuevo — así no se queda
        # pidiendo de más contra una API que corta la conexión.
        if len(vistos) >= (total_esperado or 0) or len(vistos) == antes:
            break

    return registros_a_df(list(vistos.values()))


@st.cache_data(ttl=3600, show_spinner=False)
@st.cache_data(ttl=3600, show_spinner=False)
def periodos_con_estado():
    """`[(periodo, cod_estado, descripcion)]`, del más reciente al más viejo.

    `cod_estado` "01" = Presentado (el registro del mes ya se generó);
    "03" = No Presentado (el período sigue abierto). La diferencia NO es
    cosmética — cambia qué devuelve la propuesta, ver
    `obtener_comprobantes_rango`.
    """
    if not secrets_disponibles():
        hoy = pd.Timestamp.today()
        # El mes en curso abierto y los 11 anteriores cerrados: la misma
        # forma que tienen los datos reales, para que la vista se comporte
        # igual en demo.
        return [(periodo_desde_fecha(hoy - pd.DateOffset(months=i)),
                 "03" if i == 0 else "01",
                 "No Presentado" if i == 0 else "Presentado")
                for i in range(12)]

    datos = _get(URL_PERIODOS.format(cod_libro=COD_LIBRO_RCE),
                 obtener_token()).json()
    registros = datos if isinstance(datos, list) else datos.get("registros", [])
    filas = [(str(p.get("perTributario")),
              str(p.get("codEstado") or ""),
              str(p.get("desEstado") or ""))
             for reg in registros
             for p in (reg.get("lisPeriodos") or [])
             if p.get("perTributario")]
    # Un período podría venir repetido entre ejercicios: gana el primero.
    vistos, salida = set(), []
    for per, cod, des in sorted(filas, reverse=True):
        if per not in vistos:
            vistos.add(per)
            salida.append((per, cod, des))
    return salida


def periodos_disponibles():
    """Períodos `yyyymm` habilitados, del más reciente al más viejo."""
    return [p for p, _, _ in periodos_con_estado()]


def periodos_a_consultar(fecha_ini, fecha_fin, disponibles):
    """Períodos que hay que pedir para cubrir el rango POR FECHA DE EMISIÓN.

    No alcanza con el período del mes: un comprobante emitido en junio
    puede estar anotado en junio, o seguir pendiente y aparecer recién en
    la propuesta del mes abierto. Medido contra datos reales (RUC
    20605204300): de los comprobantes emitidos en julio 2026, 323 estaban
    en el período 202607 (Presentado) y otros 88 —DISTINTOS, cero
    solapamiento por `codCar`— sólo aparecían en la propuesta de 202608.
    Consultar un solo período deja agujeros en cualquiera de los dos
    sentidos.

    Por eso se piden todos los períodos desde el del `fecha_ini` hasta el
    más reciente disponible: es la ventana donde puede estar anotado algo
    emitido dentro del rango.
    """
    if not disponibles or fecha_ini is None or fecha_fin is None:
        return []
    desde = periodo_desde_fecha(min(pd.Timestamp(fecha_ini),
                                    pd.Timestamp(fecha_fin)))
    return sorted([p for p in disponibles if p >= desde], reverse=True)


@st.cache_data(ttl=3600, show_spinner=False)
def obtener_comprobantes_rango(fecha_ini, fecha_fin, _progreso=None):
    """Comprobantes EMITIDOS dentro del rango, uniendo los períodos que hagan
    falta y marcando la situación de cada uno.

    Devuelve el DataFrame canónico más dos columnas:
      · `periodo_registro` — en qué período tributario lo tiene SUNAT.
      · `situacion` — "Registrado" si ese período ya está Presentado,
        "Pendiente" si sigue abierto. Un "Pendiente" es una compra que
        SUNAT ve y todavía no está anotada: crédito fiscal sin tomar.

    El filtro final es por `fecha_emision`, que es la fecha que le importa
    al negocio — y la que ordena el resto de los reportes de la app.
    """
    estados = {p: cod for p, cod, _ in periodos_con_estado()}
    periodos = periodos_a_consultar(fecha_ini, fecha_fin, list(estados))
    if not periodos:
        return registros_a_df([])

    partes = []
    for i, per in enumerate(periodos):
        if _progreso:
            _progreso(i / len(periodos))
        try:
            d = obtener_comprobantes(per)
        except Exception:
            # Un período que falla no puede tumbar la vista entera: se
            # sigue con los demás y el usuario ve lo que sí se pudo traer.
            continue
        if d.empty:
            continue
        d = d.copy()
        d["periodo_registro"] = per
        d["situacion"] = ("Registrado" if estados.get(per) == "01"
                          else "Pendiente")
        partes.append(d)

    if not partes:
        return registros_a_df([])

    df = pd.concat(partes, ignore_index=True)
    # Mismo criterio de deduplicación que dentro de un período (`codCar` es
    # único por anotación). Entre períodos no debería haber repetidos —se
    # verificó: cero solapamiento— pero si SUNAT llegara a devolver uno en
    # dos sitios, gana el "Registrado": es el estado más definitivo.
    df = (df.sort_values("situacion")            # "Pendiente" < "Registrado"
            .drop_duplicates(subset="car", keep="last"))

    ini = pd.Timestamp(fecha_ini).normalize()
    fin = pd.Timestamp(fecha_fin).normalize() + pd.Timedelta(days=1)
    df = df[(df["fecha_emision"] >= ini) & (df["fecha_emision"] < fin)]
    return df.sort_values("fecha_emision").reset_index(drop=True)


# ===========================================================================
# EL REGISTRO CACHEADO EN UN PARQUET DE R2
# ===========================================================================
# `obtener_comprobantes_rango` (arriba) pregunta a SUNAT EN VIVO. Funciona,
# pero paga dos costos en cada visita: es lento —la API sólo habla por mes,
# así que un rango ancho son N llamadas encadenadas de ~9 seg— y hereda la
# disponibilidad de SUNAT, que no es buena (verificado 2026-08-20: "Error
# del Servidor, reintentar en 5 minutos").
#
# `herramientas/sunat_registro_sync.py` corre de madrugada en la CPU local,
# trae TODOS los períodos y deja el resultado acá, en un parquet. Esta capa
# lo lee. Es el mismo trato que tiene el resto de la app con sus datos.
#
# `comprobantes_rango` es la puerta que usa la vista: prefiere el parquet y
# cae a la API en vivo si todavía no existe. Así la vista funciona igual
# antes y después de la primera corrida del sync. Ver regla #160.

ARCHIVO_REGISTRO = "sunat_compras.parquet"


@st.cache_data(ttl=3600, show_spinner=False)
def _registro_de_parquet():
    """El registro completo desde el parquet de R2, o None si no está.

    Devuelve None —en vez de lanzar— cuando el parquet todavía no existe:
    es el estado normal antes de la primera corrida del sync, y quien
    llama decide caer a la API en vivo.
    """
    import data

    if not data.secrets_disponibles():
        return None
    try:
        con = data.get_conn()
        url = f"s3://{st.secrets['R2_BUCKET']}/{ARCHIVO_REGISTRO}"
        df = con.execute(f"SELECT * FROM read_parquet('{url}')").df()
    except Exception:
        return None
    if df is None or df.empty:
        return None
    for col in ("fecha_emision", "fecha_vencimiento"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def fecha_registro():
    """Cuándo se subió el parquet del registro (UTC), o None.

    La vista lo muestra para que un sync que dejó de correr se vea en
    pantalla en vez de pasar por dato fresco — el agujero que tiene
    cualquier proceso de madrugada sin alertas.
    """
    import data

    return data.fecha_ultima_actualizacion(ARCHIVO_REGISTRO)


def limites_registro():
    """`(primera, ultima)` fecha de emisión que YA cubre el parquet, o None.

    Es un dato, no una política: dice hasta dónde llegó la última corrida
    del sync, nada más. El PISO del calendario de la vista sale de acá
    (antes de la primera factura no hay nada que pedir); el TECHO no —
    ése es HOY, porque los días que el parquet todavía no trajo se piden
    en vivo (ver `comprobantes_rango` y `tramo_pendiente`). Ver
    `arquitectura.md` regla #197.

    Barato: es un min/max sobre el df que `_registro_de_parquet` ya tiene
    cacheado en memoria, no una lectura nueva.
    """
    df = _registro_de_parquet()
    if df is None or df.empty or "fecha_emision" not in df.columns:
        return None
    fechas = pd.to_datetime(df["fecha_emision"], errors="coerce").dropna()
    if fechas.empty:
        return None
    return fechas.min().date(), fechas.max().date()


def tramo_pendiente(tope_parquet, fecha_ini, fecha_fin):
    """El pedazo de `[fecha_ini, fecha_fin]` que el parquet NO cubre, o None.

    Función PURA (sin red ni Streamlit, testeada en `test_sunat.py`): es la
    decisión de "¿hace falta molestar a la API?", separada de la lectura
    para poder probarla sin credenciales.

    El corte es **estrictamente después** del tope: si el rango termina en
    un día que el parquet ya tiene, no se consulta nada y la vista sigue
    siendo instantánea — que es el caso normal, porque casi todo lo que se
    mira es pasado. Sólo la cola verdaderamente nueva sale por la API.

    El precio de ese corte, escrito para que no sorprenda: un comprobante
    con fecha de emisión VIEJA que SUNAT recién anota hoy no aparece hasta
    la próxima corrida del sync. Es el agujero que tiene cualquier proceso
    de madrugada y ya estaba antes; lo que este tramo arregla es el otro,
    el que sí se veía en pantalla — los días recientes que no existían en
    el parquet y que el calendario, encima, no dejaba ni elegir.
    """
    if fecha_ini is None or fecha_fin is None:
        return None
    ini = pd.Timestamp(fecha_ini).normalize().date()
    fin = pd.Timestamp(fecha_fin).normalize().date()
    if fin < ini:
        ini, fin = fin, ini
    if tope_parquet is None:            # parquet vacío: todo es cola
        return ini, fin
    tope = pd.Timestamp(tope_parquet).normalize().date()
    if fin <= tope:
        return None
    return max(ini, tope + datetime.timedelta(days=1)), fin


def comprobantes_rango(fecha_ini, fecha_fin, _progreso=None):
    """Comprobantes emitidos en el rango: el parquet, más la cola en vivo.

    Es la puerta que usa la vista. Devuelve `(df, origen)` para que la
    pantalla pueda decir de dónde salió el número — misma exigencia que
    dejó la regla #141: una vista con datos externos tiene que mostrar su
    procedencia, no sólo el total. Los cuatro orígenes posibles:

      · `"api"` — el parquet todavía no existe en R2 y todo salió en vivo.
      · `"parquet"` — el rango entero ya estaba sincronizado.
      · `"parquet+vivo"` — el rango pasa del tope del parquet y la cola se
        pidió a SUNAT en el momento.
      · `"parquet-sin-cola"` — hacía falta esa cola y SUNAT no contestó. Lo
        que se devuelve está INCOMPLETO y la vista tiene que decirlo: un
        total creíble al que le faltan los últimos días es exactamente el
        modo de fallo de la regla #141.

    Preguntar por la cola no es un lujo: el sync corre de madrugada, así
    que entre esa corrida y ahora hay hasta un día entero de comprobantes
    que existen en SUNAT y no en R2. Ver `arquitectura.md` regla #197.
    """
    df = _registro_de_parquet()
    if df is None:
        return obtener_comprobantes_rango(fecha_ini, fecha_fin, _progreso), "api"

    ini = pd.Timestamp(fecha_ini).normalize()
    fin = pd.Timestamp(fecha_fin).normalize() + pd.Timedelta(days=1)
    m = (df["fecha_emision"] >= ini) & (df["fecha_emision"] < fin)
    del_parquet = df[m]

    def _solo_parquet(origen):
        return (del_parquet.sort_values("fecha_emision").reset_index(drop=True),
                origen)

    tope = df["fecha_emision"].max()
    cola = tramo_pendiente(None if pd.isna(tope) else tope, fecha_ini, fecha_fin)
    if cola is None:
        return _solo_parquet("parquet")

    try:
        vivo = obtener_comprobantes_rango(cola[0], cola[1], _progreso)
    except Exception:
        # SUNAT caído no puede tumbar la vista entera: lo que el parquet SÍ
        # tiene se muestra igual, con el sello que avisa que falta la cola.
        return _solo_parquet("parquet-sin-cola")

    if vivo is None or vivo.empty:
        # Sin filas no hay forma de distinguir "esos días no tienen nada"
        # de "no se pudo": `obtener_comprobantes_rango` se traga los
        # períodos que fallan con un `continue`. Se informa como consulta
        # hecha, que es lo que pasó.
        return _solo_parquet("parquet+vivo")

    # El `del_parquet.empty` no es paranoia: es EL caso del bug —
    # elegir un solo día que el parquet todavía no trajo. Y un
    # `concat` con un df vacío está deprecado en pandas 2.
    unido = (vivo.copy() if del_parquet.empty
             else pd.concat([del_parquet, vivo], ignore_index=True))
    # `car` es el identificador de la anotación en SUNAT y es la ÚNICA
    # clave sin colisiones: medido sobre los 16.583 comprobantes reales,
    # serie-número deja 1.422 duplicados de proveedores distintos y
    # RUC+documento deja 3 (ver `documentos_sunat._fila_de`). Gana la fila
    # en vivo (`keep="last"`), que es la más fresca: la situación de un
    # comprobante cambia de Pendiente a Registrado cuando cierra el período.
    if "car" in unido.columns:
        unido = unido.drop_duplicates(subset="car", keep="last")
    return (unido.sort_values("fecha_emision").reset_index(drop=True),
            "parquet+vivo")


# ===========================================================================
# ORIGINALES (PDF/XML tal como los emitió el proveedor) EN R2
# ===========================================================================
# Todo lo de arriba es el REGISTRO que arma SUNAT (ver el docstring del
# módulo) — nunca el archivo que mandó el proveedor. Ese original no tiene
# API pública: sólo se puede pedir haciendo los mismos clics que una
# persona en el portal SOL (Consulta de Comprobantes de Pago). Por eso NO
# se trae acá — se trae con `herramientas/sunat_originales_sync.py`, un
# script aparte que corrés a mano en tu máquina (usa un navegador de
# verdad vía Playwright, que no cabe en Streamlit Cloud) y que sube lo que
# descarga a R2 con las claves que arma `_clave_original`.
#
# Esta sección sólo LEE lo que ese script ya dejó — mismo trato que tiene
# el resto de la app con los parquets: la webapp nunca escribe datos, sólo
# los pide o los lee. Ver `arquitectura.md` regla #142.

PREFIJO_ORIGINALES = "sunat_originales"


def _clave_original(ruc_proveedor, serie, numero, extension):
    """Key en R2 de un original de un comprobante.

    Función pura, sin red: la comparte el script que SUBE (sync) y esta
    capa que LEE, para que nunca puedan divergir en el nombre.
    """
    ruc = str(ruc_proveedor or "").strip()
    doc = f"{str(serie or '').strip()}-{str(numero or '').strip()}"
    return f"{PREFIJO_ORIGINALES}/{ruc}/{doc}.{extension}"


def claves_original(doc):
    """(clave_pdf, clave_xml) en R2 para una fila del df canónico."""
    ruc = doc.get("ruc_proveedor", "")
    serie = doc.get("serie", "")
    numero = doc.get("numero", "")
    return (_clave_original(ruc, serie, numero, "pdf"),
            _clave_original(ruc, serie, numero, "xml"))


# EXISTENCIA y CONTENIDO se cachean por SEPARADO, y con TTL muy distintos.
# No es microoptimización: con una sola función cacheada 1 h, el flujo de
# "pedir un original" quedaba roto. El usuario abre el documento (se cachea
# "no está" por una hora), lo pide, llega en 30 segundos… y la pantalla
# sigue diciendo que no está hasta una hora después. El botón ⟳ lo
# arreglaba, pero nadie iba a adivinarlo.
#
# La existencia se pregunta seguido y es barata (un head_object). El
# contenido es caro pero INMUTABLE —un PDF ya subido no cambia nunca— así
# que una vez leído se puede cachear largo sin riesgo.

@st.cache_data(ttl=20, show_spinner=False)
def _existe_original(clave):
    """True si el objeto ya está en R2. TTL corto: esto cambia mientras el
    usuario mira la pantalla, esperando su pedido."""
    import data

    if not data.secrets_disponibles():
        return False
    try:
        data.get_s3_cliente().head_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave)
        return True
    except Exception:
        return False


@st.cache_data(ttl=3600, show_spinner=False)
def _bytes_original(clave):
    """Bytes de un objeto de R2, o None. TTL largo: el archivo no cambia."""
    import data  # import local: sunat.py no necesita boto3 si nadie pide un original

    if not data.secrets_disponibles():
        return None
    try:
        s3 = data.get_s3_cliente()
        return s3.get_object(Bucket=st.secrets["R2_BUCKET"], Key=clave)["Body"].read()
    except Exception:
        return None


def _leer_original(clave):
    """Bytes del original, o None si todavía no está en R2.

    Nunca lanza: un original todavía no sincronizado es un estado normal
    de este drill (el sync corre aparte y a demanda), no un error a
    mostrar en pantalla.
    """
    return _bytes_original(clave) if _existe_original(clave) else None


def originales(doc):
    """(bytes_pdf|None, bytes_xml|None) de un comprobante ya sincronizado.

    Ambos None si `sunat_originales_sync.py` todavía no pasó por este
    documento — la UI lo trata como "no disponible aún", no como error.
    """
    clave_pdf, clave_xml = claves_original(doc)
    return _leer_original(clave_pdf), _leer_original(clave_xml)


# ===========================================================================
# VER EL ORIGINAL EN PANTALLA
# ===========================================================================
# El PDF NO se puede embeber: Chrome no renderiza un `data:application/pdf`
# dentro de un iframe con `sandbox`, y Streamlit monta todos sus iframes
# así (probado y descartado el 2026-08-19, ver el docstring de
# `_ficha_html` en la vista). La salida es renderizarlo a imagen del lado
# del servidor y mostrar ESO, que además funciona igual en el teléfono.

# Unidades de medida del catálogo 03 de SUNAT. Solo las que aparecen de
# verdad en comprobantes de compras; el resto se muestra con su código,
# que es preferible a inventar una traducción.
_UNIDADES = {
    "NIU": "unidad", "ZZ": "servicio", "KGM": "kg", "GRM": "g",
    "LTR": "litro", "MLT": "ml", "MTR": "m", "CMT": "cm",
    "BX": "caja", "PK": "paquete", "BG": "bolsa", "CA": "lata",
    "BO": "botella", "TU": "tubo", "SET": "juego", "DZN": "docena",
    "GLL": "galón", "MTQ": "m³", "MTK": "m²", "HUR": "hora",
    "DAY": "día", "MON": "mes",
}

_NS_UBL = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


# ---------------------------------------------------------------------------
# DESCRIPCIONES EMPAQUETADAS
# ---------------------------------------------------------------------------
# Algunos emisores no usan `cbc:Description` como descripción: meten ahí el
# renglón ENTERO del ticket, con los campos pegados con `@@` de separador.
#
#     2028@@CHIRCUMEXXKG@@ 1.330 X     11.49@@15.28@@
#     └cód┘ └──nombre───┘ └cant┘ └precio┘ └total┘
#
# El resultado en pantalla es una columna "Descripción" ilegible que además
# repite —peor, con OTROS números: los del ticket llevan IGV y los del XML
# no— lo que las columnas de al lado ya muestran bien.
#
# Medido sobre R2 el 2026-08-24 antes de escribir esto, para no adivinar la
# forma: 3 de 123 proveedores con original sincronizado emiten así, y sus
# 503 líneas siguen todas el mismo patrón, en dos variantes — con total
# final (`cód@@nombre@@ cant X precio@@total@@`) y sin él. El nombre es
# SIEMPRE el segundo trozo, en 503 de 503.
#
# Aun así la elección no es "el trozo [1]" sino "el primer trozo que parece
# un nombre": el día que aparezca un cuarto emisor con los campos en otro
# orden, el peor caso es mostrar el texto crudo (lo de hoy), no una
# cantidad donde va el producto.
#
# Lo que NO se hace acá: inventarle espacios al nombre. `CHIRCUMEXXKG` sale
# así del sistema del proveedor, que abrevia a lo que le entra en el campo
# (`QUES.BRI.FLO`, `SALCHICHA DE HU`). Separarlo a ojo sería adivinar.
#
# Y lo que se DESCARTA a sabiendas: el primer trozo es un código de barras
# de verdad (429 de esas 503 líneas pasan el dígito de control), pero NO
# aporta una columna, y eso también está medido, no supuesto:
#
#   - 221 son EAN internacionales GS1 (prefijos 775 Perú, 800 Italia, 779
#     Argentina, 841 España…) y las 221 coinciden con el
#     `SellersItemIdentification` que ya se muestra en "Código".
#   - 147 difieren del código, y las 147 son de circulación RESTRINGIDA
#     (prefijo 2x, o PLU corto de balanza tipo `4002`): peso embebido,
#     distinto en cada línea del mismo producto — `0211033002309` y
#     `0211033002408` son los dos QUES.BRI.FLO del código `110334`.
#
# O sea: cuando el EAN sirve, ya está en pantalla; cuando difiere, difiere
# justamente porque NO identifica al producto sino a ESA pesada. Se tira;
# el identificador estable es el del emisor.

# " 1.330 X     11.49" — dígitos, separadores y una X en el medio.
_TROZO_CANT_X_PRECIO = re.compile(r"^[\d.,\s]+[Xx][\d.,\s]+$")


def _descripcion_limpia(texto):
    """El nombre del producto, sin el resto del renglón empaquetado.

    Función pura. Sin `@@` devuelve el texto tal cual: la enorme mayoría de
    los emisores manda una descripción normal y no hay que tocarla.
    """
    if "@@" not in (texto or ""):
        return texto
    for trozo in texto.split("@@"):
        trozo = trozo.strip()
        if (trozo and re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", trozo)
                and not _TROZO_CANT_X_PRECIO.match(trozo)):
            return trozo
    return texto


def _num_xml(txt):
    try:
        return float(txt)
    except (TypeError, ValueError):
        return None


def lineas_xml(xml_bytes):
    """Las líneas de detalle de un XML de comprobante → lista de dicts.

    Esto es lo que el parquet del registro NO tiene: qué se compró,
    cuánto y a qué precio. El registro es por DOCUMENTO; el detalle vive
    únicamente acá adentro.

    Función pura y tolerante: un XML raro devuelve lista vacía en vez de
    reventar la pantalla. Las notas de crédito usan `CreditNoteLine` y
    `CreditedQuantity` en vez de `InvoiceLine`/`InvoicedQuantity`.
    """
    import xml.etree.ElementTree as ET

    if not xml_bytes:
        return []
    try:
        raiz = ET.fromstring(xml_bytes)
    except Exception:
        return []

    filas = raiz.findall(".//cac:InvoiceLine", _NS_UBL)
    if not filas:
        filas = raiz.findall(".//cac:CreditNoteLine", _NS_UBL)
    if not filas:
        filas = raiz.findall(".//cac:DebitNoteLine", _NS_UBL)

    salida = []
    for linea in filas:
        cant = linea.find("cbc:InvoicedQuantity", _NS_UBL)
        if cant is None:
            cant = linea.find("cbc:CreditedQuantity", _NS_UBL)
        if cant is None:
            cant = linea.find("cbc:DebitedQuantity", _NS_UBL)

        desc = linea.find("cac:Item/cbc:Description", _NS_UBL)
        precio = linea.find("cac:Price/cbc:PriceAmount", _NS_UBL)
        importe = linea.find("cbc:LineExtensionAmount", _NS_UBL)
        codigo = linea.find("cac:Item/cac:SellersItemIdentification/cbc:ID",
                            _NS_UBL)

        unidad = (cant.get("unitCode") or "") if cant is not None else ""
        salida.append({
            "codigo": (codigo.text or "").strip() if codigo is not None else "",
            "descripcion": _descripcion_limpia(
                (desc.text or "").strip()) if desc is not None else "",
            "cantidad": _num_xml(cant.text) if cant is not None else None,
            "unidad": _UNIDADES.get(unidad.upper(), unidad),
            "precio_unitario": _num_xml(precio.text) if precio is not None else None,
            "importe": _num_xml(importe.text) if importe is not None else None,
        })
    return salida


@st.cache_data(ttl=1800, show_spinner=False, max_entries=20)
def paginas_pdf(pdf_bytes, escala=2):
    """El PDF → lista de PNG (bytes), una por página.

    Cacheado y con `max_entries` acotado a propósito: cada página son
    ~350 KB de PNG, así que sin tope la caché de un usuario que hojea
    muchos comprobantes crecería sin control.
    """
    if not pdf_bytes:
        return []
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return []
    try:
        doc = pdfium.PdfDocument(io.BytesIO(pdf_bytes))
        salida = []
        for pagina in doc:
            buf = io.BytesIO()
            pagina.render(scale=escala).to_pil().save(buf, format="PNG")
            salida.append(buf.getvalue())
        return salida
    except Exception:
        return []


# ===========================================================================
# PEDIR UN ORIGINAL A DEMANDA
# ===========================================================================
# La corrida nocturna baja de lo más nuevo hacia atrás y tarda semanas en
# cubrir la ventana entera (~9.800 documentos a ~30 seg cada uno). Mientras
# tanto, un documento viejo simplemente no está — y esperar semanas a que
# le llegue el turno no sirve cuando alguien lo necesita HOY.
#
# Para eso está esto: la webapp deja una SEÑAL en R2 y la CPU local, que ya
# vigila señales para los parquets (`data.py::solicitar_refresco` +
# `atender_solicitudes.py`), la levanta y baja ese documento puntual. Es el
# mismo mecanismo que ya existe en el proyecto, aplicado a otra cosa — no
# uno nuevo. Del otro lado lo atiende
# `herramientas/atender_solicitudes_sunat.py`.
#
# La webapp NUNCA abre un navegador ni habla con el portal SOL: sólo pide.
# Ver regla #144.

PREFIJO_SOLICITUDES = "_solicitudes_sunat"


def clave_solicitud(doc):
    """Key en R2 de la señal para pedir el original de un comprobante.

    Determinista a propósito: dos clics sobre el mismo documento pisan la
    misma señal en vez de encolar dos pedidos idénticos.
    """
    ruc = str(doc.get("ruc_proveedor") or "").strip()
    serie = str(doc.get("serie") or "").strip()
    numero = str(doc.get("numero") or "").strip()
    return f"{PREFIJO_SOLICITUDES}/{ruc}_{serie}-{numero}.json"


@st.cache_data(ttl=15, show_spinner=False)
def _hay_senal(clave):
    """True si la señal sigue en R2 (o sea, nadie la atendió todavía).

    TTL corto (15 seg) y no una hora: esto cambia de estado mientras el
    usuario mira la pantalla, y un cache largo lo dejaría viendo
    "pendiente" mucho después de que el archivo ya llegó.
    """
    import data

    if not data.secrets_disponibles():
        return False
    try:
        data.get_s3_cliente().head_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave)
        return True
    except Exception:
        return False


def solicitud_pendiente(doc):
    """True si ya se pidió este original y todavía no lo atendieron."""
    return _hay_senal(clave_solicitud(doc))


def clave_fallo(doc):
    """Key de la marca que deja el servidor cuando un pedido no se pudo servir."""
    return clave_solicitud(doc).replace(".json", ".fallo.json")


@st.cache_data(ttl=15, show_spinner=False)
def _leer_fallo(clave):
    import json

    import data

    if not data.secrets_disponibles():
        return None
    try:
        crudo = data.get_s3_cliente().get_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave)["Body"].read()
        return json.loads(crudo)
    except Exception:
        return None


def fallo_solicitud(doc):
    """`{motivo, cuando}` si el último pedido de este original falló, o None.

    Existe porque un pedido fallido, sin esto, es indistinguible de uno
    que nunca se hizo: la señal se borra, no aparece ningún archivo, y el
    usuario vuelve a ver el mismo botón. Apretarlo de nuevo da
    exactamente el mismo silencio.
    """
    return _leer_fallo(clave_fallo(doc))


def solicitar_original(doc):
    """Deja en R2 la señal para que la CPU local baje este original.

    Devuelve True si la señal quedó escrita. El payload lleva todo lo que
    el script del otro lado necesita para hacer la consulta en el portal
    (RUC del emisor, tipo, serie, número) — así no tiene que volver a
    buscar el comprobante en ningún lado.
    """
    import json
    from datetime import datetime, timezone

    import data

    if not data.secrets_disponibles():
        return False
    payload = {
        "ruc_proveedor": str(doc.get("ruc_proveedor") or "").strip(),
        "serie": str(doc.get("serie") or "").strip(),
        "numero": str(doc.get("numero") or "").strip(),
        "tipo_cdp": str(doc.get("tipo_cdp") or "01").strip(),
        "documento": str(doc.get("documento") or "").strip(),
        "solicitado_en": datetime.now(timezone.utc).isoformat(),
    }
    s3 = data.get_s3_cliente()
    try:
        s3.put_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave_solicitud(doc),
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json")
    except Exception:
        return False
    # Si había una marca de fallo anterior, se limpia: este pedido es un
    # reintento, y dejarla haría que la pantalla siguiera mostrando el
    # error viejo mientras el nuevo intento está en curso.
    try:
        s3.delete_object(Bucket=st.secrets["R2_BUCKET"], Key=clave_fallo(doc))
    except Exception:
        pass
    # Sin esto la UI seguiría mostrando el botón "pedir" durante los 15 seg
    # del TTL, invitando a un segundo clic sobre algo ya pedido.
    _hay_senal.clear()
    _leer_fallo.clear()
    return True


# ===========================================================================
# CORRECCIONES MANUALES DE LÍNEA («Detalle sistema», 2026-08-27)
# ===========================================================================
# El detalle del XML (`lineas_xml`) trae el código de línea que usa el
# PROVEEDOR; `compras.parquet` trae `COD_PRODUCTO`, el código INTERNO. No
# hay ninguna columna que una uno con otro — el emparejamiento que arma
# `graficos/compras/documentos_sunat.py::_parear_lineas_sistema` es una
# SUGERENCIA por texto/cantidad/precio, no una certeza, y a veces se
# equivoca o no encuentra nada. Esto guarda la corrección manual.
#
# Mismo patrón que la sección de arriba (señal en R2, `put_object` +
# `get_object`, cache corto para que el guardado se vea al toque): una
# corrección es una anotación de LA WEBAPP sobre un documento puntual,
# nunca un cambio a `compras.parquet` — ese parquet lo arma un ETL aparte
# y acá es de solo lectura.

PREFIJO_CORRECCIONES = "_correcciones_sunat"


def clave_correcciones(doc):
    """Key en R2 de las correcciones de línea de un comprobante.

    Determinista, igual que `clave_solicitud`: dos correcciones sobre el
    mismo comprobante pisan el mismo archivo en vez de acumular uno por
    intento."""
    ruc = str(doc.get("ruc_proveedor") or "").strip()
    serie = str(doc.get("serie") or "").strip()
    numero = str(doc.get("numero") or "").strip()
    return f"{PREFIJO_CORRECCIONES}/{ruc}_{serie}-{numero}.json"


@st.cache_data(ttl=15, show_spinner=False)
def correcciones_lineas(doc):
    """`{índice_línea_xml: registro}` de las correcciones guardadas para
    este comprobante, o `{}` si no hay ninguna (estado normal: la mayoría
    de los documentos no tiene correcciones).

    El registro trae SÓLO lo que se corrigió — las claves son opcionales y
    ausente significa "usar lo automático":

      · `cod_producto` + `nombre_producto` — el producto del sistema
        elegido a mano (`guardar_correccion_linea`). Ausentes: vale el
        emparejamiento automático contra `compras.parquet`/el maestro.
      · `cantidad` — la cantidad con la que se va a cargar la línea
        (`guardar_cantidad_linea`, 2026-08-27). Ausente: vale la del XML.
      · `corregido_en` — cuándo se tocó por última vez.

    Un registro sin ninguna de las dos correcciones no existe: el que
    quita la última borra el registro (y el archivo, si era el último).

    TTL corto (15 seg), igual que `_hay_senal`: esto puede cambiar
    mientras el usuario mira la pantalla, justo después de guardar una
    corrección."""
    import json

    import data

    if not data.secrets_disponibles():
        return {}
    try:
        crudo = data.get_s3_cliente().get_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave_correcciones(doc))["Body"].read()
        bruto = json.loads(crudo)
        return {int(k): v for k, v in bruto.items()}
    except Exception:
        return {}


def _escribir_correcciones(doc, actuales):
    """Persiste el dict ENTERO de correcciones de este comprobante en R2
    (o borra el archivo si no quedó ninguna). Devuelve True si quedó
    guardado. No lanza: un R2 caído durante el guardado es un estado a
    mostrar en pantalla, no un traceback.

    Es la única escritura de la familia: los cuatro `guardar_*`/`quitar_*`
    de abajo leen, mutan y llaman acá. Antes cada uno tenía su propio
    `put_object` + `clear`, y con la cantidad editable (2026-08-27) eso
    eran cuatro copias del mismo bloque.
    """
    import json

    import data

    if not data.secrets_disponibles():
        return False
    try:
        s3 = data.get_s3_cliente()
        if actuales:
            s3.put_object(
                Bucket=st.secrets["R2_BUCKET"], Key=clave_correcciones(doc),
                Body=json.dumps(actuales, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json")
        else:
            # No queda ninguna corrección: borrar el archivo entero es lo
            # mismo que "nunca hubo nada", y no deja un {} suelto en R2.
            s3.delete_object(Bucket=st.secrets["R2_BUCKET"],
                             Key=clave_correcciones(doc))
    except Exception:
        return False
    # Sin esto la UI seguiría mostrando el emparejamiento viejo durante los
    # 15 seg del TTL, como si la corrección no se hubiera guardado.
    correcciones_lineas.clear(doc)
    return True


def _sellar(registro):
    """Le pone la hora al registro de una línea y lo devuelve."""
    from datetime import datetime, timezone

    registro["corregido_en"] = datetime.now(timezone.utc).isoformat()
    return registro


def guardar_correccion_linea(doc, indice_linea, cod_producto, nombre_producto):
    """Guarda en R2 el PRODUCTO que corresponde a UNA línea del XML de este
    comprobante (pisa el producto corregido previo de esa línea, si había).

    MERGE, no reemplazo: si esa línea ya tenía una `cantidad` corregida
    (`guardar_cantidad_linea`), se conserva. Son dos correcciones
    independientes sobre la misma línea — cambiar el producto no tiene por
    qué borrar la cantidad que alguien ya ajustó a mano.
    """
    actuales = dict(correcciones_lineas(doc))
    registro = dict(actuales.get(int(indice_linea)) or {})
    registro["cod_producto"] = str(cod_producto)
    registro["nombre_producto"] = str(nombre_producto)
    actuales[int(indice_linea)] = _sellar(registro)
    return _escribir_correcciones(doc, actuales)


def quitar_correccion_linea(doc, indice_linea):
    """Saca el PRODUCTO corregido de UNA línea (esa línea vuelve a mostrar
    el emparejamiento automático). No es un error si esa línea no tenía
    corrección guardada — simplemente no cambia nada.

    Saca sólo las claves del producto: si quedaba una `cantidad`
    corregida, sobrevive (ver `guardar_correccion_linea`). El registro
    entero se borra recién cuando no queda ninguna de las dos.
    """
    actuales = dict(correcciones_lineas(doc))
    registro = dict(actuales.get(int(indice_linea)) or {})
    if not registro.get("cod_producto"):
        return True
    registro.pop("cod_producto", None)
    registro.pop("nombre_producto", None)
    if registro.get("cantidad") is None:
        actuales.pop(int(indice_linea), None)
    else:
        actuales[int(indice_linea)] = _sellar(registro)
    return _escribir_correcciones(doc, actuales)


def guardar_cantidad_linea(doc, indice_linea, cantidad):
    """Guarda la CANTIDAD con la que se va a cargar UNA línea al sistema.

    Agregado 2026-08-27 a pedido: la cantidad del conversor arranca igual
    a la del comprobante SUNAT, pero se puede editar — el caso real es un
    proveedor que factura 4 líneas del mismo producto (4 piezas pesadas
    una por una) y el sistema carga una sola con el total. Guardarla acá
    NO toca el XML ni `compras.parquet`: es una anotación de la webapp
    sobre ESE documento, igual que el producto corregido.

    Sólo se llama cuando la cantidad DIFIERE de la del XML; volver al
    valor del comprobante es `quitar_cantidad_linea`, no guardar el mismo
    número otra vez.
    """
    actuales = dict(correcciones_lineas(doc))
    registro = dict(actuales.get(int(indice_linea)) or {})
    registro["cantidad"] = float(cantidad)
    actuales[int(indice_linea)] = _sellar(registro)
    return _escribir_correcciones(doc, actuales)


def quitar_cantidad_linea(doc, indice_linea):
    """Saca la cantidad corregida de UNA línea (vuelve a la del XML).
    Gemela de `quitar_correccion_linea`: si quedaba un producto corregido,
    sobrevive."""
    actuales = dict(correcciones_lineas(doc))
    registro = dict(actuales.get(int(indice_linea)) or {})
    if registro.get("cantidad") is None:
        return True
    registro.pop("cantidad", None)
    if not registro.get("cod_producto"):
        actuales.pop(int(indice_linea), None)
    else:
        actuales[int(indice_linea)] = _sellar(registro)
    return _escribir_correcciones(doc, actuales)


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
    """Valor de un campo, formateado para mostrar. `—` si falta.

    El chequeo de "falta" usa `pd.isna` y NO `isinstance(v, float)`, que es
    lo que había y tumbaba la pantalla: una fecha ausente llega como
    `pd.NaT`, que **no es un float** —así que pasaba el filtro— y **sí
    tiene `.strftime`**, que lanza ValueError al llamarlo. El panel entero
    reventaba con un traceback.

    No era un caso raro: 9.524 de 16.583 comprobantes reales (57%) no
    traen fecha de vencimiento, porque las facturas al contado no la
    tienen. Más de la mitad del reporte era imposible de abrir.
    """
    v = comprobante.get(clave)
    if v is None:
        return defecto
    try:
        if pd.isna(v):
            return defecto
    except (TypeError, ValueError):
        pass          # listas/arrays: `pd.isna` devuelve otro array, no aplica
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    s = str(v).strip()
    return s if s else defecto


SIMBOLO_MONEDA = {"PEN": "S/", "USD": "$", "EUR": "\u20ac"}
"""Símbolo con el que se escribe un importe según su `codMoneda`. Fuera de
la tabla, cualquier código desconocido se escribe tal cual (`"CAD 12.00"`),
que es feo pero no MIENTE — que es lo que hacía la versión anterior."""


def simbolo_moneda(codigo):
    """`"PEN"` → `"S/"`. Un código que no esté en la tabla vuelve tal cual."""
    cod = str(codigo or "PEN").strip().upper()
    return SIMBOLO_MONEDA.get(cod, cod)


def _importe(comprobante, clave):
    """El importe de `clave` con el símbolo de SU moneda.

    Hasta el 2026-08-28 esto se llamaba `_soles` y escribía `"S/ "` fijo,
    mirara lo que mirara. Con 641 comprobantes en dólares en el registro
    (de 16.678) eso no era un detalle: la ficha de la factura F163-2309 de
    MAPFRE decía `Moneda: USD` y tres renglones más abajo
    `Base imponible: S/ 10,733.31` — se contradecía sola, y el PDF
    descargable salía igual porque usa esta misma función a través de
    `campos_ficha`. Los 10.733,31 son DÓLARES; a un TC de 3,402 son
    S/ 36.514,72, o sea que el número que se leía estaba errado por 26 mil
    soles.
    """
    v = comprobante.get(clave)
    try:
        return f"{simbolo_moneda(comprobante.get('moneda'))} {float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _convertido_a_soles(comprobante, clave):
    """El mismo importe convertido a soles con el tipo de cambio del propio
    comprobante, o `None` si ya está en soles (y entonces no hay nada que
    convertir ni que mostrar)."""
    if str(comprobante.get("moneda") or "PEN").strip().upper() == "PEN":
        return None
    try:
        tc = float(comprobante.get("tipo_cambio") or 1.0)
        return f"S/ {float(comprobante.get(clave)) * tc:,.2f}"
    except (TypeError, ValueError):
        return None


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
             _val(comprobante, "tipo_nombre")),
            ("Fecha de emisión", _val(comprobante, "fecha_emision")),
            ("Fecha de vencimiento", _val(comprobante, "fecha_vencimiento")),
            ("Período tributario", _val(comprobante, "periodo")),
            ("Moneda", _moneda_con_tc(comprobante)),
            ("Estado", _val(comprobante, "estado")),
            ("Detracción", "Sí" if str(
                comprobante.get("detraccion") or "").strip().upper() == "D"
                else "No"),
        )),
        ("Importes", _importes_ficha(comprobante)),
    )


def _moneda_con_tc(comprobante):
    """`"PEN"`, o `"USD · TC 3.402"` cuando no es la moneda local: el tipo
    de cambio sólo dice algo cuando hay algo que convertir."""
    cod = str(comprobante.get("moneda") or "").strip().upper()
    if not cod:
        return "—"
    if cod == "PEN":
        return cod
    try:
        return f"{cod} · TC {float(comprobante.get('tipo_cambio') or 1.0):.3f}"
    except (TypeError, ValueError):
        return cod


def _importes_ficha(comprobante):
    """Los importes de la ficha, cada uno con el símbolo de su moneda — y,
    sólo si el comprobante NO está en soles, el total convertido. Ver
    `_importe`, que es donde estaba el error que esto arregla."""
    filas = [
        ("Base imponible", _importe(comprobante, "base_imponible")),
        ("IGV / IPM", _importe(comprobante, "igv")),
        ("No gravado", _importe(comprobante, "no_gravado")),
        ("Total", _importe(comprobante, "total")),
    ]
    convertido = _convertido_a_soles(comprobante, "total")
    if convertido:
        filas.append(("Total en soles", convertido))
    return tuple(filas)


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
        ax.text(0.07, 0.955, val("tipo_nombre", "COMPROBANTE").upper(),
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
        ax.text(0.90, y - 0.018, _importe(comprobante, "total"),
                color="#4938b8", fontsize=15, weight="bold", va="center",
                ha="right")

        ax.text(0.07, 0.055, f"CAR SUNAT: {val('car')}", color=gris,
                fontsize=7.5)
        ax.plot([0.07, 0.93], [0.042, 0.042], color="#e6e6eb", lw=1)
        ax.text(0.07, 0.024, PIE_FICHA, color=gris, fontsize=7.5, va="top",
                wrap=True)

        pdf.savefig(fig)
        plt.close(fig)

    return buf.getvalue()
