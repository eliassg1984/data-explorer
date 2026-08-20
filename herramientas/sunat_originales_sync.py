"""
herramientas/sunat_originales_sync.py — baja el PDF/XML ORIGINAL (el que
emitió el proveedor) de los comprobantes de un rango de períodos, y los
sube a R2 para que la webapp los sirva.

POR QUÉ ES UN SCRIPT APARTE, NO PARTE DE LA WEBAPP
---------------------------------------------------
`sunat.py` trae el REGISTRO del comprobante por API (rápido, OAuth2, sin
navegador). El original NO tiene esa puerta: SUNAT sólo lo entrega por el
portal SOL (Consulta de Comprobantes de Pago), con los mismos clics que
haría una persona — hace falta un navegador de verdad (Playwright), y eso
no cabe en Streamlit Community Cloud ni tiene sentido correrlo por cada
visita a la webapp. Este script corre LOCAL, a mano, cuando querés
backfillear un rango; desde ahí la webapp sólo LEE lo que dejó en R2
(`sunat.originales()`, en `graficos/compras/documentos_sunat.py`).

Ver `arquitectura.md` regla #142.

USO
---
    python herramientas/sunat_originales_sync.py --desde 202607 --hasta 202608
    python herramientas/sunat_originales_sync.py --desde 202608 --hasta 202608 --limite 2 --ver   (probar primero, viendo la ventana)
    python herramientas/sunat_originales_sync.py --desde 202607 --hasta 202608 --forzar           (repetir aunque ya esté en R2)

Por default el navegador es INVISIBLE (headless): no abre ninguna ventana,
no se ve ningún cursor moviéndose — corre como proceso de fondo, igual que
cualquier otro script. Con `--ver` sí abre una ventana de Chrome de
verdad y se puede mirar. Conviene usarlo la primera vez: más fácil
describir "se quedó trabado en esta pantalla" que leer un stack trace.

REQUIERE
--------
    pip install -r requirements-dev.txt
    playwright install chromium

Y en `.streamlit/secrets.toml` (los mismos que ya usa la webapp): las 5
credenciales de SUNAT (SUNAT_RUC, SUNAT_USUARIO_SOL, SUNAT_CLAVE_SOL,
SUNAT_CLIENT_ID, SUNAT_CLIENT_SECRET) y las 4 de R2 (R2_ACCOUNT_ID,
R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET). `st.secrets` funciona igual
fuera de `streamlit run` — mismo truco que usa `herramientas/ver_figura.py`.

DE DÓNDE SALE ESTE CÓDIGO
--------------------------
Login, manejo de popups y llenado del formulario de consulta están
ADAPTADOS de un proyecto de escritorio de terceros (app-sire, Playwright +
Tkinter) que ya los tenía probados contra SUNAT en producción — no se
reinventó esa parte. Lo que SÍ cambia acá:

  · Una sola sesión/login para TODO el rango, no una por comprobante. El
    proyecto original abría navegador y se logueaba de nuevo por cada PDF;
    para un período con cientos de documentos eso es lento y son cientos
    de logins contra el mismo portal — una señal de bot mucho más fuerte
    que loguearse una vez y consultar varios documentos seguidos, que es
    además lo que haría una persona.
  · Sube a R2 en vez de guardar en disco: la webapp lee de ahí, no de esta
    máquina.
  · Salta lo que YA está en R2 (backfill incremental) salvo `--forzar`.

SIN VERIFICAR CONTRA SUNAT EN VIVO — LEER ANTES DE CORRER EN SERIO
--------------------------------------------------------------------
Todo lo de login/popups/primer formulario viene de código ya probado. Lo
que NO probó nadie todavía es volver a "Nueva Consulta" DESPUÉS de bajar
un documento, para el segundo en adelante dentro de la misma sesión — el
proyecto original nunca lo necesitó porque reabría el navegador para cada
uno. Es la parte más probable de necesitar un ajuste de selector. Por eso:
correlo primero con `--limite 2` contra un período que conozcas, mirá el
log, y recién después soltale un rango grande.

RIESGO ACEPTADO A PROPÓSITO (igual que el endpoint no documentado de
`sunat.py`, ver regla #140, pero un escalón más arriba): esto navega el
portal SOL con técnicas anti-detección (esconder `navigator.webdriver`,
user-agent de navegador real) porque sin eso Chromium headless no pasa el
login. No es un contrato público de SUNAT — puede romperse con cualquier
cambio del portal, y correrlo seguido sube el riesgo de que la cuenta
quede señalada. Por eso es manual y local, no un cron: corré esto cuando
lo necesites, no como un proceso de fondo.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

# Importar el proyecto desde la raíz aunque el script se invoque por ruta
# — mismo patrón que herramientas/ver_figura.py.
_RAIZ = pathlib.Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

if hasattr(sys.stdout, "reconfigure"):      # consola cp1252 de Windows
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd            # noqa: E402
import streamlit as st         # noqa: E402  — st.secrets vive sin server

import data                    # noqa: E402
import sunat                   # noqa: E402

PAUSA_ENTRE_DOCS_SEG = 1.5   # no golpear el portal sin respiro entre consultas


def _log(msg: str) -> None:
    print(msg, flush=True)


# ===========================================================================
# NAVEGACIÓN DEL PORTAL SOL
# adaptado de un proyecto de terceros (app-sire/services/sunat_pdf_downloader.py)
# ===========================================================================

def _iniciar_navegador(p, headless: bool = True):
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
"""Confirmada CORRECTA en vivo (2026-08-20): un usuario copió esta misma
URL, carácter por carácter, desde una sesión real recién logueada en su
navegador de todos los días — así que el `state` no es un nonce de una
sola vez, es un valor fijo que SUNAT arma siempre igual para este flujo.
La primera versión de este script sospechaba de la URL y la cambió por
una que resultó peor (regla #142 de arquitectura.md); esto la revierte."""


def _login(pagina, ruc, usuario, clave) -> None:
    """Login en SUNAT SOL.

    Visita primero el sitio público (como lo haría una persona) y RECIÉN
    desde ahí navega a la URL de login, con `referer` explícito — para
    que el pedido no llegue "de la nada", como sí pasa al saltar directo
    a una URL profunda sin haber estado antes en ningún lado del dominio.
    Sospecha en investigación (2026-08-20): con la URL confirmada CORRECTA
    (ver `URL_LOGIN_SOL`), lo que quedaba fallando en vivo apuntaba a
    detección de automatización, no a un dato mal armado.
    """
    _log("Accediendo al login de SUNAT…")
    pagina.goto("https://www.sunat.gob.pe/", wait_until="domcontentloaded")
    pagina.goto(URL_LOGIN_SOL, referer="https://www.sunat.gob.pe/")
    pagina.wait_for_selector("#txtRuc", timeout=30000)
    pagina.fill("#txtRuc", ruc)
    pagina.fill("#txtUsuario", usuario)
    pagina.fill("#txtContrasena", clave)
    pagina.click("#btnAceptar")


def _cerrar_popups(pagina) -> None:
    """Modales de campaña/publicidad que a veces aparecen tras el login.
    No siempre salen — por eso no hacer nada si no aparecen no es un error.
    """
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


URL_MENU_SOL = "https://e-menu.sunat.gob.pe/cl-ti-itmenu/MenuInternet.htm?pestana=*&agrupacion=*"
"""Confirmada en vivo (2026-08-20): a dónde aterriza un login exitoso."""


def _ir_a_consulta_comprobantes(pagina) -> None:
    """Camino Empresas → Comprobantes de Pago → Consulta → Nueva Consulta.

    Se llama UNA vez por documento. Arranca con un `goto` limpio al menú
    — no navega desde donde haya quedado la página — porque después de
    bajar un comprobante queda abierto un panel "Resultado" que tapa (o
    directamente saca del layout) el ítem "Empresas", y el click al
    segundo documento en adelante fallaba con "Element is not visible"
    (verificado en vivo 2026-08-20, primera corrida real: documento 1 de
    2 salió perfecto, el 2 rompió acá exactamente). Un reload cuesta un
    par de segundos pero deja SIEMPRE el mismo estado conocido, sin
    depender de qué panel dejó abierto el documento anterior.
    """
    pagina.goto(URL_MENU_SOL, wait_until="domcontentloaded")
    pagina.locator(".list-group-item").filter(has_text="Empresas").first.click(force=True)
    time.sleep(1.5)

    def paso(texto: str) -> None:
        item = pagina.get_by_text(texto, exact=True).first
        item.wait_for(state="visible", timeout=10000)
        item.click(force=True)
        time.sleep(0.8)

    paso("Comprobantes de pago")
    paso("Comprobantes de Pago")
    paso("Consulta de Comprobantes de Pago")
    link = pagina.get_by_text("Nueva Consulta de comprobantes de pago", exact=True).first
    link.wait_for(state="visible", timeout=10000)
    link.click(force=True)


def _tipo_label(tipo_cdp: str, serie: str) -> str:
    """Texto que hay que tipear en el combo "Tipo" del formulario del
    portal. `tipo_cdp` es el código de `sunat.py` (ya viene zfill(2))."""
    tipo = str(tipo_cdp).strip().zfill(2)
    s = str(serie).strip().upper()
    if tipo == "01":
        return "Factura"
    if tipo == "03":
        return "Boleta de venta"
    if tipo == "07":
        if s.startswith("B"):
            return "Boleta de Venta - Nota de Crédito"
        if s.startswith("T"):
            return "Ticket POS - Nota de Crédito"
        return "Factura - Nota de Crédito"
    if tipo == "08":
        if s.startswith("B"):
            return "Boleta de Venta - Nota de Débito"
        if s.startswith("T"):
            return "Ticket POS - Nota de Débito"
        return "Factura - Nota de Débito"
    return "Factura"


def _consultar_y_descargar(pagina, ruc_emisor: str, serie: str, numero: str,
                           tipo_cdp: str) -> tuple[bytes | None, bytes | None]:
    """Llena el formulario para UN comprobante y descarga PDF + XML.

    Devuelve (bytes_pdf, bytes_xml); cualquiera puede ser None si el
    portal no ofreció ese botón (pasa con comprobantes muy antiguos, ver
    el aviso de "24 meses" del README del proyecto original) o si la
    consulta no encontró resultados.
    """
    label = _tipo_label(tipo_cdp, serie)
    app_frame = pagina.frame_locator("#iframeApplication")

    pagina.wait_for_selector("ngx-spinner", state="hidden", timeout=15000)

    radio = app_frame.get_by_text("Recibido", exact=True)
    radio.wait_for(state="visible", timeout=15000)
    radio.click()
    time.sleep(1.5)

    app_frame.locator("#rucEmisor, [formcontrolname='rucEmisor']").first.fill(ruc_emisor)

    dropdown = app_frame.locator("p-dropdown[formcontrolname='tipoComprobanteI']")
    dropdown.wait_for(state="visible", timeout=10000)
    dropdown.click()
    buscador = app_frame.locator("input.p-dropdown-filter")
    buscador.wait_for(state="visible", timeout=5000)
    buscador.fill(label)
    time.sleep(1.2)
    # exact=True es crítico: sin eso "Factura" matchea también
    # "Factura - Nota de Crédito".
    app_frame.get_by_role("option", name=label, exact=True).click()

    app_frame.locator("input[formcontrolname='serieComprobante'], #serie").first.fill(str(serie))
    app_frame.locator("input[formcontrolname='numeroComprobante'], #numero").first.fill(str(numero))
    app_frame.get_by_role("button", name="Consultar").click()

    try:
        app_frame.get_by_text("Resultado", exact=True).wait_for(state="visible", timeout=15000)
    except Exception:
        _log("    sin resultados (¿fuera de la ventana de consulta de SUNAT?)")
        return None, None

    pdf_bytes = None
    xml_bytes = None

    btn_pdf = app_frame.locator("button[ngbtooltip='Descargar PDF']").first
    if btn_pdf.is_visible():
        with pagina.expect_download() as descarga:
            btn_pdf.click()
        pdf_bytes = pathlib.Path(descarga.value.path()).read_bytes()

    time.sleep(1)
    btn_xml = app_frame.locator("button[ngbtooltip='Descargar XML']").first
    if btn_xml.is_visible():
        with pagina.expect_download() as descarga:
            btn_xml.click()
        xml_bytes = pathlib.Path(descarga.value.path()).read_bytes()

    return pdf_bytes, xml_bytes


# ===========================================================================
# R2
# ===========================================================================

def _ya_en_r2(s3, bucket: str, clave: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=clave)
        return True
    except Exception:
        return False


def _subir(s3, bucket: str, clave: str, contenido: bytes, content_type: str) -> None:
    s3.put_object(Bucket=bucket, Key=clave, Body=contenido, ContentType=content_type)


# ===========================================================================
# MAIN
# ===========================================================================

def _comprobantes_del_rango(desde: str, hasta: str) -> pd.DataFrame:
    periodos = [p for p in sunat.periodos_disponibles() if desde <= p <= hasta]
    if not periodos:
        return sunat.registros_a_df([])
    partes = [sunat.obtener_comprobantes(p) for p in periodos]
    df = pd.concat(partes, ignore_index=True) if partes else sunat.registros_a_df([])
    return df.drop_duplicates(subset="car") if not df.empty else df


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Baja PDF/XML originales de SUNAT (portal SOL) y los sube a R2.")
    ap.add_argument("--desde", required=True, help="Período yyyymm inicial (inclusive)")
    ap.add_argument("--hasta", required=True, help="Período yyyymm final (inclusive)")
    ap.add_argument("--limite", type=int, default=None,
                    help="Máximo de documentos a bajar en esta corrida (para probar)")
    ap.add_argument("--forzar", action="store_true",
                    help="Vuelve a bajar aunque ya exista en R2")
    ap.add_argument("--ver", action="store_true",
                    help="Abre el Chromium en una ventana visible en vez de "
                        "invisible (headless). Más lento, pero para la "
                        "primera corrida sirve para VER qué hace en vez de "
                        "leer un stack trace si algo falla.")
    args = ap.parse_args()

    if not sunat.periodo_valido(args.desde) or not sunat.periodo_valido(args.hasta):
        _log("❌ --desde/--hasta deben tener formato yyyymm (ej: 202608).")
        sys.exit(1)
    if not sunat.secrets_disponibles():
        _log("❌ Faltan credenciales de SUNAT en .streamlit/secrets.toml "
            "(SUNAT_RUC, SUNAT_USUARIO_SOL, SUNAT_CLAVE_SOL, SUNAT_CLIENT_ID, "
            "SUNAT_CLIENT_SECRET).")
        sys.exit(1)
    if not data.secrets_disponibles():
        _log("❌ Faltan credenciales de R2 en .streamlit/secrets.toml "
            "(R2_ACCOUNT_ID, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET).")
        sys.exit(1)

    _log(f"Consultando el registro de SUNAT para {args.desde}–{args.hasta}…")
    todos = _comprobantes_del_rango(args.desde, args.hasta)
    _log(f"{len(todos)} comprobantes en el rango.")
    if todos.empty:
        return

    s3 = data.get_s3_cliente()
    bucket = st.secrets["R2_BUCKET"]

    _log(f"Chequeando contra R2 cuáles de esos {len(todos)} ya están sincronizados "
        f"(sin aviso de más: son ~{len(todos) * 2} consultas chicas, puede tardar)…")
    pendientes = []
    for i, (_, doc) in enumerate(todos.iterrows(), 1):
        clave_pdf, clave_xml = sunat.claves_original(doc)
        if args.forzar or not (_ya_en_r2(s3, bucket, clave_pdf)
                              and _ya_en_r2(s3, bucket, clave_xml)):
            pendientes.append(doc)
        if i % 100 == 0:
            _log(f"  …{i}/{len(todos)} revisados")
    if args.limite is not None:
        pendientes = pendientes[:args.limite]

    _log(f"{len(pendientes)} por sincronizar "
        f"(el resto ya está en R2 — usá --forzar para repetirlos).")
    if not pendientes:
        return

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador, _contexto, pagina = _iniciar_navegador(p, headless=not args.ver)
        try:
            _login(pagina, sunat._cred("SUNAT_RUC"), sunat._cred("SUNAT_USUARIO_SOL"),
                  sunat._cred("SUNAT_CLAVE_SOL"))
            _cerrar_popups(pagina)

            ok = fallidos = 0
            for i, doc in enumerate(pendientes, 1):
                etiqueta = f"{doc['serie']}-{doc['numero']} ({doc['proveedor']})"
                _log(f"[{i}/{len(pendientes)}] {etiqueta}…")
                try:
                    _ir_a_consulta_comprobantes(pagina)
                    pdf_bytes, xml_bytes = _consultar_y_descargar(
                        pagina, doc["ruc_proveedor"], doc["serie"], doc["numero"],
                        doc["tipo_cdp"])
                    clave_pdf, clave_xml = sunat.claves_original(doc)
                    if pdf_bytes:
                        _subir(s3, bucket, clave_pdf, pdf_bytes, "application/pdf")
                    if xml_bytes:
                        _subir(s3, bucket, clave_xml, xml_bytes, "application/xml")
                    if pdf_bytes or xml_bytes:
                        ok += 1
                        _log(f"    ✓ subido (PDF: {'sí' if pdf_bytes else 'no'}, "
                            f"XML: {'sí' if xml_bytes else 'no'})")
                    else:
                        fallidos += 1
                except Exception as e:
                    fallidos += 1
                    _log(f"    ⚠️ error: {e}")
                time.sleep(PAUSA_ENTRE_DOCS_SEG)

            _log(f"\nListo: {ok} sincronizados, {fallidos} sin datos/con error, "
                f"de {len(pendientes)} intentados.")
        finally:
            navegador.close()


if __name__ == "__main__":
    main()
