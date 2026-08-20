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

import io

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
# antes y después de la primera corrida del sync. Ver regla #143.

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


def comprobantes_rango(fecha_ini, fecha_fin, _progreso=None):
    """Comprobantes emitidos en el rango. Prefiere el parquet; si no, la API.

    Es la puerta que usa la vista. Devuelve `(df, origen)` donde `origen`
    es "parquet" o "api", para que la pantalla pueda decir de dónde salió
    el número — misma exigencia que dejó la regla #141: una vista con
    datos externos tiene que mostrar su procedencia, no sólo el total.
    """
    df = _registro_de_parquet()
    if df is None:
        return obtener_comprobantes_rango(fecha_ini, fecha_fin, _progreso), "api"

    ini = pd.Timestamp(fecha_ini).normalize()
    fin = pd.Timestamp(fecha_fin).normalize() + pd.Timedelta(days=1)
    m = (df["fecha_emision"] >= ini) & (df["fecha_emision"] < fin)
    return (df[m].sort_values("fecha_emision").reset_index(drop=True),
            "parquet")


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


@st.cache_data(ttl=3600, show_spinner=False)
def _leer_original(clave):
    """Bytes de un objeto de R2, o None si no existe / no hay credenciales.

    Nunca lanza: un original todavía no sincronizado es un estado normal
    de este drill (el sync corre aparte y a demanda), no un error a
    mostrar en pantalla.
    """
    import data  # import local: sunat.py no necesita boto3 si nadie pide un original

    if not data.secrets_disponibles():
        return None
    try:
        s3 = data.get_s3_cliente()
        return s3.get_object(Bucket=st.secrets["R2_BUCKET"], Key=clave)["Body"].read()
    except Exception:
        return None


def originales(doc):
    """(bytes_pdf|None, bytes_xml|None) de un comprobante ya sincronizado.

    Ambos None si `sunat_originales_sync.py` todavía no pasó por este
    documento — la UI lo trata como "no disponible aún", no como error.
    """
    clave_pdf, clave_xml = claves_original(doc)
    return _leer_original(clave_pdf), _leer_original(clave_xml)


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
    try:
        data.get_s3_cliente().put_object(
            Bucket=st.secrets["R2_BUCKET"], Key=clave_solicitud(doc),
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json")
    except Exception:
        return False
    # Sin esto la UI seguiría mostrando el botón "pedir" durante los 15 seg
    # del TTL, invitando a un segundo clic sobre algo ya pedido.
    _hay_senal.clear()
    return True


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
    s = str(v).strip()
    return s if s else defecto


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
             _val(comprobante, "tipo_nombre")),
            ("Fecha de emisión", _val(comprobante, "fecha_emision")),
            ("Fecha de vencimiento", _val(comprobante, "fecha_vencimiento")),
            ("Período tributario", _val(comprobante, "periodo")),
            ("Moneda", _val(comprobante, "moneda")),
            ("Estado", _val(comprobante, "estado")),
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
        ax.text(0.90, y - 0.018, _soles(comprobante, "total"),
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
