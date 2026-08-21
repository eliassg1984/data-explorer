"""
sunat_originales.py — UN SOLO ARCHIVO, para dejar en C:\\proyecto\\ del
servidor. Baja de SUNAT el PDF/XML original de los comprobantes y los sube
a R2, para que la webapp los sirva.

POR QUÉ ES UN ARCHIVO SUELTO Y NO EL REPO
------------------------------------------
La webapp vive en un repo (`data-explorer`), pero el servidor es una
máquina compartida y de uso administrativo: no corresponde dejar ahí el
código entero, ni mantener un `git pull`. La convención que ya usa ese
servidor es archivos `.py` sueltos en `C:\\proyecto\\` (junto a
`Extraer a parquet.py` y `atender_solicitudes.py`), así que esto se
adapta a ESA convención en vez de imponer otra.

Consecuencia deliberada: este archivo DUPLICA un puñado de funciones que
también viven en `sunat.py` del repo — las que arman las claves de R2. Es
la parte peligrosa de la copia, y por eso `test_sunat.py` del repo tiene
una prueba que compara ambas y falla si divergen. Sin esa prueba, el día
que alguien cambie el nombre de una clave, este script subiría archivos
que la webapp nunca encontraría, **sin ningún error**.

QUÉ HACE
--------
Dos trabajos, en el mismo archivo:

  1. **Pedidos** — atiende las solicitudes que deja la webapp en
     `_solicitudes_sunat/` de R2 cuando alguien aprieta "Traer el original
     de SUNAT". Es lo urgente: hay una persona esperando.
  2. **Backfill nocturno** — baja lo que falta, de lo más nuevo hacia
     atrás, hasta que se acabe el tiempo asignado.

Por defecto hace los dos, en ese orden: primero lo que alguien pidió,
después lo que sobra de tiempo se usa para el backfill.

USO
---
    python sunat_originales.py --minutos 120     corrida nocturna
    python sunat_originales.py --pedidos         sólo pedidos (cada minuto)
    python sunat_originales.py --limite 3 --ver  probar, viendo la ventana

INSTALACIÓN EN EL SERVIDOR
---------------------------
    pip install pandas pyarrow boto3 playwright
    playwright install chromium

Credenciales:
  · **R2** — se leen de `Extraer a parquet.py` (mismo mecanismo que usa
    `atender_solicitudes.py`). No hay que configurarlas de nuevo.
  · **SUNAT** — en `credenciales/sunat.json`, junto al script:

        {
          "SUNAT_RUC": "20...",
          "SUNAT_USUARIO_SOL": "...",
          "SUNAT_CLAVE_SOL": "..."
        }

    Ese archivo tiene la Clave SOL en texto plano y da acceso completo a
    la cuenta tributaria. Si al servidor entran varias personas, conviene
    restringir la carpeta por permisos de Windows.

DEPENDE DE QUE EL PARQUET DEL REGISTRO EXISTA
----------------------------------------------
Saca la lista de comprobantes de `sunat_compras.parquet` en R2, que
genera el otro proceso (`sunat_registro_sync.py`, o su equivalente
programado). Si ese parquet no está, este script no tiene de dónde sacar
qué bajar y lo dice claro en vez de fallar raro.

RIESGO ACEPTADO: esto navega el portal SOL como lo haría una persona.
No es un contrato público de SUNAT — el día que cambien un selector, va a
fallar, y va a fallar EN SILENCIO salvo que alguien lea el log. Ver
`arquitectura.md` reglas #142 y #144 en el repo.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import pathlib
import sys
import time
import zipfile

AQUI = pathlib.Path(__file__).resolve().parent

# Nombre EXACTO del script de extracción diaria, de donde salen las
# credenciales de R2. Misma convención (y mismo comentario) que
# `atender_solicitudes.py`: debe estar en la misma carpeta que este archivo.
NOMBRE_ARCHIVO_EXTRACTOR = "Extraer a parquet.py"

ARCHIVO_CREDENCIALES_SUNAT = AQUI / "credenciales" / "sunat.json"

# ── Claves en R2 ───────────────────────────────────────────────────────────
# DUPLICADO A PROPÓSITO de `sunat.py` del repo (ver el docstring). Si esto
# cambia, hay que cambiarlo en los dos lados — `test_sunat.py` lo verifica.
PREFIJO_ORIGINALES = "sunat_originales"
PREFIJO_SOLICITUDES = "_solicitudes_sunat"
ARCHIVO_REGISTRO = "sunat_compras.parquet"

PAUSA_ENTRE_DOCS_SEG = 1.5
MESES_VENTANA = 24        # SUNAT deja de servir el original pasada esta ventana

# Cada cuánto revisa R2 el modo --vigilar. NO son los 5 seg que usa
# `atender_solicitudes.py`, y la diferencia es de presupuesto, no de gusto:
# cada revisión es un list_objects_v2, o sea una operación Class A de R2, y
# el tier gratuito da 1.000.000 al mes. A 5 seg son ~518.000 — que es
# justo lo que ya consume `atender_solicitudes.py`. Los dos juntos a 5 seg
# darían ~1.036.000 y se pasarían del límite. A 15 seg esto usa ~173.000 y
# el total queda en ~700.000, con aire.
#
# No se pierde casi nada: la descarga de un comprobante tarda ~23 seg, así
# que sumar hasta 15 de espera no cambia la experiencia de quien apretó el
# botón.
INTERVALO_VIGILAR_SEG = 15


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}", flush=True)


# ===========================================================================
# CLAVES DE R2  (duplicado de sunat.py — ver el docstring del módulo)
# ===========================================================================

def clave_original(ruc_proveedor, serie, numero, extension):
    ruc = str(ruc_proveedor or "").strip()
    doc = f"{str(serie or '').strip()}-{str(numero or '').strip()}"
    return f"{PREFIJO_ORIGINALES}/{ruc}/{doc}.{extension}"


def claves_original(doc):
    return (clave_original(doc.get("ruc_proveedor"), doc.get("serie"),
                           doc.get("numero"), "pdf"),
            clave_original(doc.get("ruc_proveedor"), doc.get("serie"),
                           doc.get("numero"), "xml"))


def clave_solicitud(doc):
    ruc = str(doc.get("ruc_proveedor") or "").strip()
    serie = str(doc.get("serie") or "").strip()
    numero = str(doc.get("numero") or "").strip()
    return f"{PREFIJO_SOLICITUDES}/{ruc}_{serie}-{numero}.json"


# ===========================================================================
# CREDENCIALES
# ===========================================================================

def _credenciales_r2():
    """Las 4 de R2. Primero de `Extraer a parquet.py`; si no, del JSON.

    En el SERVIDOR salen de `Extraer a parquet.py` — mismo mecanismo que
    `atender_solicitudes.py`: se carga ese script como módulo (su nombre
    tiene espacios, así que no sirve un `import` normal) y se leen sus
    variables. Así no hay que configurar R2 dos veces ni quedan dos copias
    de la misma credencial dando vueltas.

    FUERA del servidor ese archivo no existe, y sin fallback este script
    sería imposible de probar en otro lado: habría que subirlo a ciegas y
    descubrir los errores en producción. Por eso también se aceptan las 4
    claves en `credenciales/sunat.json`, junto a las de SUNAT.
    """
    ruta = AQUI / NOMBRE_ARCHIVO_EXTRACTOR
    if ruta.exists():
        spec = importlib.util.spec_from_file_location("_extractor", ruta)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return {
            "account_id": modulo.R2_ACCOUNT_ID,
            "access_key": modulo.R2_ACCESS_KEY,
            "secret_key": modulo.R2_SECRET_KEY,
            "bucket": modulo.R2_BUCKET,
        }

    datos = _leer_json_credenciales()
    faltan = [k for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY", "R2_SECRET_KEY",
                          "R2_BUCKET") if not datos.get(k)]
    if faltan:
        raise FileNotFoundError(
            f"No se encontró '{NOMBRE_ARCHIVO_EXTRACTOR}' en {AQUI} (de ahí "
            f"salen las credenciales de R2 en el servidor), y a "
            f"{ARCHIVO_CREDENCIALES_SUNAT} le faltan: {', '.join(faltan)}. "
            f"Poner una de las dos cosas.")
    return {
        "account_id": datos["R2_ACCOUNT_ID"],
        "access_key": datos["R2_ACCESS_KEY"],
        "secret_key": datos["R2_SECRET_KEY"],
        "bucket": datos["R2_BUCKET"],
    }


def _leer_json_credenciales():
    if not ARCHIVO_CREDENCIALES_SUNAT.exists():
        raise FileNotFoundError(
            f"Falta {ARCHIVO_CREDENCIALES_SUNAT}. Debe tener "
            f"SUNAT_RUC, SUNAT_USUARIO_SOL y SUNAT_CLAVE_SOL.")
    return json.loads(ARCHIVO_CREDENCIALES_SUNAT.read_text(encoding="utf-8"))


def _credenciales_sunat():
    datos = _leer_json_credenciales()
    faltan = [k for k in ("SUNAT_RUC", "SUNAT_USUARIO_SOL", "SUNAT_CLAVE_SOL")
              if not datos.get(k)]
    if faltan:
        raise ValueError(f"A {ARCHIVO_CREDENCIALES_SUNAT} le faltan: "
                         f"{', '.join(faltan)}")
    return datos


def _cliente_r2(cred):
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{cred['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=cred["access_key"],
        aws_secret_access_key=cred["secret_key"],
        region_name="auto",
    )


# ===========================================================================
# R2
# ===========================================================================

def leer_registro(s3, bucket):
    """El parquet del registro → DataFrame, más nuevos primero.

    Se baja entero con boto3 y se lee con pandas — nada de DuckDB. Son
    ~700 KB: no vale sumar una dependencia para filtrar eso.
    """
    import pandas as pd
    try:
        crudo = s3.get_object(Bucket=bucket, Key=ARCHIVO_REGISTRO)["Body"].read()
    except Exception as e:
        raise RuntimeError(
            f"No se pudo leer {ARCHIVO_REGISTRO} de R2 ({e}). Este script saca "
            f"de ahí la lista de comprobantes: primero tiene que correr el "
            f"proceso que genera ese parquet.")
    df = pd.read_parquet(io.BytesIO(crudo))
    df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")
    return df.sort_values("fecha_emision", ascending=False).reset_index(drop=True)


def claves_ya_en_r2(s3, bucket):
    """Todo lo ya subido bajo el prefijo de originales, en un set.

    Una llamada por cada 1000 claves, en vez de dos `head_object` por
    documento: con ~10.000 documentos la diferencia es entre ~20 llamadas
    y ~20.000.
    """
    claves, token = set(), None
    while True:
        kw = {"Bucket": bucket, "Prefix": f"{PREFIJO_ORIGINALES}/"}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        claves.update(o["Key"] for o in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            return claves
        token = resp.get("NextContinuationToken")


def subir(s3, bucket, clave, contenido, tipo):
    s3.put_object(Bucket=bucket, Key=clave, Body=contenido, ContentType=tipo)


# ===========================================================================
# NAVEGACIÓN DEL PORTAL SOL
# ===========================================================================

URL_LOGIN_SOL = (
    "https://api-seguridad.sunat.gob.pe/v1/clientessol/"
    "4f3b88b3-d9d6-402a-b85d-6a0bc857746a/oauth2/loginMenuSol"
    "?lang=es-PE&showDni=true&showLanguages=false"
    "&originalUrl=https://e-menu.sunat.gob.pe/cl-ti-itmenu/"
    "AutenticaMenuInternet.htm"
    "&state=rO0ABXNyABFqYXZhLnV0aWwuSGFzaE1hcAUH2sHDFmDRAwACRgAKbG9hZEZhY3RvckkACXRo"
    "cmVzaG9sZHhwP0AAAAAAAAx3CAAAABAAAAADdAADZXhlcHQABnBhcmFtc3QASyomKiYvY2wtdGktaXRt"
    "ZW51L01lbnVJbnRlcm5ldC5odG0mYjY0ZDI2YThiNWFmMDkxOTIzYjIzYjY0MDdhMWMxZGI0MWU3MzNh"
    "NnQABGV4ZWNweA=="
)

URL_MENU_SOL = ("https://e-menu.sunat.gob.pe/cl-ti-itmenu/"
                "MenuInternet.htm?pestana=*&agrupacion=*")


def iniciar_navegador(p, headless=True):
    navegador = p.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    contexto = navegador.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"),
    )
    pagina = contexto.new_page()
    pagina.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
    return navegador, contexto, pagina


def login(pagina, cred):
    """Visita el sitio público ANTES y manda `referer` al saltar al login.

    Sin eso SUNAT contesta "Error en la invocación" y nunca muestra el
    formulario — verificado en vivo 2026-08-20. Saltar directo a la URL
    profunda no alcanza.
    """
    log("Entrando a SUNAT SOL…")
    pagina.goto("https://www.sunat.gob.pe/", wait_until="domcontentloaded")
    pagina.goto(URL_LOGIN_SOL, referer="https://www.sunat.gob.pe/")
    pagina.wait_for_selector("#txtRuc", timeout=30000)
    pagina.fill("#txtRuc", cred["SUNAT_RUC"])
    pagina.fill("#txtUsuario", cred["SUNAT_USUARIO_SOL"])
    pagina.fill("#txtContrasena", cred["SUNAT_CLAVE_SOL"])
    pagina.click("#btnAceptar")


def cerrar_popups(pagina):
    """Modales de campaña que a veces aparecen tras el login. Puede que no
    salgan: que no aparezcan no es un error."""
    try:
        iframe = pagina.frame_locator("#ifrVCE")
        btn = iframe.get_by_role("button", name="Finalizar")
        btn.wait_for(state="visible", timeout=10000)
        btn.click()
        cont = iframe.get_by_text("Continuar sin confirmar")
        cont.wait_for(state="visible", timeout=5000)
        cont.click()
        time.sleep(2)
    except Exception:
        pass


def click_texto_visible(pagina, texto, timeout_ms=10000):
    """Click en la coincidencia VISIBLE del texto — no en la primera.

    SUNAT agrega accesos de "Favoritos" a medida que se usa un ítem del
    menú: después del primer uso el mismo texto existe DOS veces en el DOM
    (el ítem real + un acceso todavía oculto), y `.first` puede agarrar el
    escondido. Verificado en vivo: con `.first`, el 2º documento en
    adelante fallaba con "Element is not visible".
    """
    limite = time.time() + timeout_ms / 1000
    while time.time() < limite:
        for candidato in pagina.get_by_text(texto, exact=True).all():
            if candidato.is_visible():
                candidato.click(force=True)
                return
        time.sleep(0.3)
    raise Exception(f"'{texto}' no apareció visible en {timeout_ms}ms.")


def ir_a_consulta(pagina):
    """Menú → Consulta de Comprobantes, arrancando de una página limpia.

    El `goto` al menú antes de cada documento no es adorno: después de
    bajar uno queda abierto un panel "Resultado" que tapa el ítem
    "Empresas", y el click del siguiente fallaba con "Element is not
    visible". Un reload cuesta un par de segundos y deja siempre el mismo
    estado conocido.
    """
    pagina.goto(URL_MENU_SOL, wait_until="domcontentloaded")
    pagina.locator(".list-group-item").filter(has_text="Empresas").first.click(force=True)
    time.sleep(1.5)
    for texto in ("Comprobantes de pago", "Comprobantes de Pago",
                  "Consulta de Comprobantes de Pago",
                  "Nueva Consulta de comprobantes de pago"):
        click_texto_visible(pagina, texto)
        time.sleep(0.8)


def etiqueta_tipo(tipo_cdp, serie):
    """Texto a tipear en el combo "Tipo" del formulario del portal."""
    tipo = str(tipo_cdp).strip().replace(".0", "").zfill(2)
    s = str(serie).strip().upper()
    if tipo == "01":
        return "Factura"
    if tipo == "03":
        return "Boleta de venta"
    if tipo in ("07", "08"):
        clase = "Nota de Crédito" if tipo == "07" else "Nota de Débito"
        if s.startswith("B"):
            return f"Boleta de Venta - {clase}"
        if s.startswith("T"):
            return f"Ticket POS - {clase}"
        return f"Factura - {clase}"
    return "Factura"


def xml_del_zip(crudo):
    """El XML de la factura, sacado del ZIP que entrega SUNAT.

    El botón "Descargar XML" NO baja un XML: baja un ZIP con la factura y
    el CDR (constancia de recepción, prefijo `R-`). Guardar el ZIP crudo
    bajo la clave `.xml` rompe dos cosas: el visor de la webapp no lo abre,
    y el detalle de líneas —la razón de guardar el XML— queda detrás de un
    unzip que nadie hace.
    """
    if crudo[:2] != b"PK":
        return crudo
    try:
        with zipfile.ZipFile(io.BytesIO(crudo)) as z:
            nombres = [n for n in z.namelist()
                       if n.lower().endswith(".xml")
                       and not pathlib.PurePath(n).name.upper().startswith("R-")]
            if nombres:
                return z.read(nombres[0])
    except Exception:
        pass
    return crudo


def consultar_y_descargar(pagina, ruc_emisor, serie, numero, tipo_cdp):
    """Llena el formulario para UN comprobante. Devuelve (pdf, xml), None
    cualquiera que SUNAT no ofrezca."""
    label = etiqueta_tipo(tipo_cdp, serie)
    app = pagina.frame_locator("#iframeApplication")

    pagina.wait_for_selector("ngx-spinner", state="hidden", timeout=15000)
    radio = app.get_by_text("Recibido", exact=True)
    radio.wait_for(state="visible", timeout=15000)
    radio.click()
    time.sleep(1.5)

    app.locator("#rucEmisor, [formcontrolname='rucEmisor']").first.fill(str(ruc_emisor))

    dropdown = app.locator("p-dropdown[formcontrolname='tipoComprobanteI']")
    dropdown.wait_for(state="visible", timeout=10000)
    dropdown.click()
    buscador = app.locator("input.p-dropdown-filter")
    buscador.wait_for(state="visible", timeout=5000)
    buscador.fill(label)
    time.sleep(1.2)
    # exact=True es crítico: sin eso "Factura" matchea también
    # "Factura - Nota de Crédito".
    app.get_by_role("option", name=label, exact=True).click()

    app.locator("input[formcontrolname='serieComprobante'], #serie").first.fill(str(serie))
    app.locator("input[formcontrolname='numeroComprobante'], #numero").first.fill(str(numero))
    app.get_by_role("button", name="Consultar").click()

    try:
        app.get_by_text("Resultado", exact=True).wait_for(state="visible", timeout=15000)
    except Exception:
        # Distinguir "SUNAT no encontró nada" de "SUNAT está caído": lo
        # segundo es transitorio y no significa que falte el documento.
        if pagina.get_by_text("Error del Servidor", exact=False).is_visible():
            log("    SUNAT devolvió 'Error del Servidor' (transitorio)")
            try:
                pagina.get_by_role("button", name="Aceptar").click(timeout=3000)
            except Exception:
                pass
        else:
            log("    sin resultados")
        return None, None

    pdf_bytes = xml_bytes = None
    btn_pdf = app.locator("button[ngbtooltip='Descargar PDF']").first
    if btn_pdf.is_visible():
        with pagina.expect_download() as d:
            btn_pdf.click()
        pdf_bytes = pathlib.Path(d.value.path()).read_bytes()

    time.sleep(1)
    btn_xml = app.locator("button[ngbtooltip='Descargar XML']").first
    if btn_xml.is_visible():
        with pagina.expect_download() as d:
            btn_xml.click()
        xml_bytes = xml_del_zip(pathlib.Path(d.value.path()).read_bytes())

    return pdf_bytes, xml_bytes


def bajar_uno(pagina, s3, bucket, doc):
    """Un comprobante: consulta, descarga y sube. True si subió algo."""
    ir_a_consulta(pagina)
    pdf_bytes, xml_bytes = consultar_y_descargar(
        pagina, doc.get("ruc_proveedor"), doc.get("serie"),
        doc.get("numero"), doc.get("tipo_cdp", "01"))
    clave_pdf, clave_xml = claves_original(doc)
    if pdf_bytes:
        subir(s3, bucket, clave_pdf, pdf_bytes, "application/pdf")
    if xml_bytes:
        subir(s3, bucket, clave_xml, xml_bytes, "application/xml")
    return bool(pdf_bytes or xml_bytes)


# ===========================================================================
# LOS DOS TRABAJOS
# ===========================================================================

def pedidos_pendientes(s3, bucket):
    """Las señales que dejó la webapp → [(clave, payload)]."""
    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{PREFIJO_SOLICITUDES}/")
    except Exception as e:
        log(f"No se pudo listar los pedidos: {e}")
        return []
    salida = []
    for obj in resp.get("Contents", []):
        clave = obj["Key"]
        if not clave.endswith(".json"):
            continue
        try:
            crudo = s3.get_object(Bucket=bucket, Key=clave)["Body"].read()
            salida.append((clave, json.loads(crudo)))
        except Exception as e:
            # Una señal ilegible no puede trabar la cola.
            log(f"Señal corrupta, se descarta ({clave}): {e}")
            try:
                s3.delete_object(Bucket=bucket, Key=clave)
            except Exception:
                pass
    return salida


def atender_pedidos(pagina, s3, bucket):
    """Baja lo que la webapp pidió. Devuelve cuántos pedidos procesó."""
    pedidos = pedidos_pendientes(s3, bucket)
    if not pedidos:
        return 0
    log(f"{len(pedidos)} pedido(s) de la webapp.")
    for clave_senal, pedido in pedidos:
        log(f"  {pedido.get('documento') or clave_senal}…")
        try:
            if bajar_uno(pagina, s3, bucket, pedido):
                log("    subido")
            else:
                log("    SUNAT no devolvió el archivo")
        except Exception as e:
            log(f"    error: {str(e)[:160]}")
        # La señal se borra SIEMPRE, salga bien o mal. Si no, un
        # comprobante que SUNAT no puede servir dejaría a la webapp
        # mostrando "pedido" para siempre y a este script reintentándolo
        # en cada pasada.
        try:
            s3.delete_object(Bucket=bucket, Key=clave_senal)
        except Exception:
            pass
        time.sleep(PAUSA_ENTRE_DOCS_SEG)
    return len(pedidos)


def seleccionar_backfill(s3, bucket, meses_atras, limite):
    """Qué falta bajar, más nuevos primero."""
    import pandas as pd

    df = leer_registro(s3, bucket)
    log(f"{len(df)} comprobantes en el registro.")

    if meses_atras:
        corte = pd.Timestamp.today().normalize() - pd.DateOffset(months=meses_atras)
        antes = len(df)
        df = df[df["fecha_emision"] >= corte]
        if antes != len(df):
            log(f"{antes - len(df)} anteriores a {corte:%Y-%m} se saltan "
                f"(fuera de la ventana de {meses_atras} meses de SUNAT).")

    ya = claves_ya_en_r2(s3, bucket)
    pendientes = [d for _, d in df.iterrows()
                  if not set(claves_original(d)) <= ya]
    log(f"{len(pendientes)} sin sincronizar · {len(df) - len(pendientes)} ya en R2.")
    # `is not None` y no `if limite`: con `--limite 0` (que es lo natural
    # para "mirá qué falta pero no bajes nada"), un chequeo por verdadero
    # lo trata como "sin límite" y arranca la corrida COMPLETA. Pasó de
    # verdad al probar este archivo.
    if limite is not None:
        pendientes = pendientes[:limite]
        log(f"--limite {limite}: esta corrida intenta sólo {len(pendientes)}.")
    return pendientes


def correr_backfill(pagina, s3, bucket, pendientes, corte_t):
    ok = fallidos = 0
    for i, doc in enumerate(pendientes, 1):
        # El corte se chequea ANTES de empezar el documento: cortar a
        # mitad dejaría el PDF sin su XML, y el chequeo de "ya está en R2"
        # exige los dos, así que se reintentaría entero igual.
        if corte_t and time.time() > corte_t:
            log(f"Corte por tiempo: quedan {len(pendientes) - i + 1} "
                f"para la próxima corrida.")
            break
        log(f"[{i}/{len(pendientes)}] {doc.get('serie')}-{doc.get('numero')} "
            f"({str(doc.get('proveedor'))[:38]})…")
        try:
            if bajar_uno(pagina, s3, bucket, doc):
                ok += 1
                log("    subido")
            else:
                fallidos += 1
        except Exception as e:
            fallidos += 1
            log(f"    error: {str(e)[:160]}")
        time.sleep(PAUSA_ENTRE_DOCS_SEG)
    return ok, fallidos


# ===========================================================================
# CANDADO — una sola sesión de SUNAT a la vez
# ===========================================================================
# Las dos tareas programadas se pisan: el backfill corre 2 horas y la de
# pedidos salta cada minuto, así que durante esas 2 horas habría DOS
# navegadores logueados a la vez en la misma cuenta SOL. SUNAT puede
# invalidar una sesión, o tomarlo como comportamiento anómalo de la cuenta.
#
# El candado es un archivo con la hora de arranque. Se toma antes de abrir
# el navegador y se suelta al terminar.

ARCHIVO_CANDADO = AQUI / "logs" / "sunat.lock"

# Un candado más viejo que esto se considera basura de una corrida que murió
# sin limpiar (corte de luz, kill, excepción no atrapada). Va holgado sobre
# las 2 h del backfill: mejor esperar de más que quedar bloqueado para
# siempre por un archivo huérfano.
CANDADO_VENCE_HORAS = 4


def tomar_candado():
    """True si se pudo tomar. False si ya hay otra corrida en curso."""
    ARCHIVO_CANDADO.parent.mkdir(parents=True, exist_ok=True)
    if ARCHIVO_CANDADO.exists():
        edad_h = (time.time() - ARCHIVO_CANDADO.stat().st_mtime) / 3600
        if edad_h < CANDADO_VENCE_HORAS:
            log(f"Ya hay otra corrida en curso (candado de hace "
                f"{edad_h * 60:.0f} min). Se sale sin hacer nada.")
            return False
        log(f"Candado vencido ({edad_h:.1f} h): se ignora y se sigue.")
    # El contenido es informativo (para saber quién dejó el candado si hay
    # que borrarlo a mano); lo que importa es que el archivo exista.
    ARCHIVO_CANDADO.write_text(
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} pid={os.getpid()}",
        encoding="utf-8")
    return True


def soltar_candado():
    try:
        ARCHIVO_CANDADO.unlink(missing_ok=True)
    except Exception:
        pass


# ===========================================================================
# MAIN
# ===========================================================================

def una_sesion(cred_sunat, s3, bucket, headless, pedidos_hay, pendientes,
               corte_t):
    """Abre el navegador UNA vez, atiende pedidos y backfill, y lo cierra.

    El navegador se abre por tanda, no por documento ni para siempre: abrir
    Chromium y loguearse cuesta ~15 seg, pero dejarlo vivo indefinidamente
    en modo servicio sería peor —400 MB tomados todo el día y una sesión de
    SUNAT abierta durante días, que además vence sola.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador, _ctx, pagina = iniciar_navegador(p, headless=headless)
        try:
            login(pagina, cred_sunat)
            cerrar_popups(pagina)

            # Los pedidos van PRIMERO: hay una persona esperando del otro
            # lado. El backfill se come lo que sobre del tiempo asignado.
            n_ped = atender_pedidos(pagina, s3, bucket) if pedidos_hay else 0

            ok = fallidos = 0
            if pendientes:
                ok, fallidos = correr_backfill(pagina, s3, bucket,
                                               pendientes, corte_t)
            log(f"Listo: {n_ped} pedido(s) · backfill {ok} subidos, "
                f"{fallidos} sin datos/con error.")
        finally:
            navegador.close()


def bucle_pedidos(cred_sunat, s3, bucket, headless, intervalo):
    """Modo servicio: vigila los pedidos para siempre.

    Mismo patrón que `atender_solicitudes.py` del servidor, y por las
    mismas razones: el arranque pesado (importar pandas, cargar el
    extractor, crear el cliente de R2) ocurre UNA vez en vez de en cada
    revisión, y un error puntual se anota sin matar el servicio.

    El candado se toma POR TANDA, no al arrancar: si se tomara una vez y
    se sostuviera, el backfill nocturno no podría correr nunca.
    """
    log(f"Modo servicio: vigilando pedidos cada {intervalo}s. Ctrl+C para salir.")
    ultimo_latido = time.time()
    LATIDO_SEG = 300      # una línea cada 5 min para saber que sigue vivo

    while True:
        try:
            pedidos = pedidos_pendientes(s3, bucket)
            if pedidos:
                if tomar_candado():
                    try:
                        una_sesion(cred_sunat, s3, bucket, headless,
                                   True, [], None)
                    finally:
                        soltar_candado()
                    ultimo_latido = time.time()
                else:
                    log("Hay pedidos pero el backfill está corriendo; "
                        "se atienden apenas termine.")
            elif time.time() - ultimo_latido >= LATIDO_SEG:
                log("Servicio activo (sin pedidos recientes).")
                ultimo_latido = time.time()
        except Exception as e:
            # Un tropiezo puntual (R2 caído, SUNAT caído, sesión rechazada)
            # no puede matar el servicio: se anota y se sigue.
            log(f"ERROR en el ciclo: {str(e)[:200]}")
        time.sleep(intervalo)


def main():
    ap = argparse.ArgumentParser(
        description="Baja PDF/XML originales de SUNAT y los sube a R2.")
    ap.add_argument("--pedidos", action="store_true",
                    help="Sólo atender pedidos de la webapp, sin backfill. "
                         "Una pasada: si no hay nada sale en ~1 seg sin "
                         "abrir el navegador.")
    ap.add_argument("--vigilar", action="store_true",
                    help="Modo SERVICIO: queda vigilando pedidos para "
                         "siempre (implica --pedidos). Pensado para NSSM, "
                         "al lado de atender_solicitudes.py.")
    ap.add_argument("--cada", type=int, default=INTERVALO_VIGILAR_SEG,
                    help=f"Con --vigilar: segundos entre revisiones "
                         f"(default {INTERVALO_VIGILAR_SEG}).")
    ap.add_argument("--minutos", type=int, default=None,
                    help="Tope de tiempo del backfill. Acota el TIEMPO y no "
                         "la cantidad, que es lo que importa cuando cada "
                         "documento tarda distinto.")
    ap.add_argument("--limite", type=int, default=None,
                    help="Máximo de documentos del backfill (para probar)")
    ap.add_argument("--meses-atras", type=int, default=MESES_VENTANA,
                    help=f"No intentar documentos de más de N meses "
                         f"(default {MESES_VENTANA}). 0 = sin límite.")
    ap.add_argument("--ver", action="store_true",
                    help="Navegador visible en vez de invisible")
    args = ap.parse_args()

    try:
        cred_r2 = _credenciales_r2()
        cred_sunat = _credenciales_sunat()
    except Exception as e:
        log(f"ERROR de configuración: {e}")
        sys.exit(1)

    s3 = _cliente_r2(cred_r2)
    bucket = cred_r2["bucket"]
    headless = not args.ver

    if args.vigilar:
        bucle_pedidos(cred_sunat, s3, bucket, headless, args.cada)
        return

    # Se mira si hay trabajo ANTES de abrir el navegador: arrancar Chromium
    # y loguearse cuesta ~15 seg, y en el modo --pedidos la enorme mayoría
    # de las pasadas no tienen nada que hacer.
    pedidos = pedidos_pendientes(s3, bucket)
    pendientes = []
    if not args.pedidos:
        try:
            pendientes = seleccionar_backfill(s3, bucket, args.meses_atras,
                                              args.limite)
        except Exception as e:
            log(f"ERROR: {e}")
            sys.exit(1)

    if not pedidos and not pendientes:
        log("Nada que hacer.")
        return

    if not tomar_candado():
        return

    corte_t = (time.time() + args.minutos * 60) if args.minutos else None
    try:
        una_sesion(cred_sunat, s3, bucket, headless, bool(pedidos),
                   pendientes, corte_t)
    finally:
        soltar_candado()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Cortado.")
