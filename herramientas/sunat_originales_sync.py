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
    python herramientas/sunat_originales_sync.py --minutos 120        (la corrida nocturna)
    python herramientas/sunat_originales_sync.py --limite 3 --ver     (probar, viendo la ventana)
    python herramientas/sunat_originales_sync.py --desde 202608 --hasta 202608 --forzar

Sin `--desde`/`--hasta` toma TODO el universo, **más nuevo primero** — que
es lo que se quiere de noche: lo reciente es lo que la gente consulta, y
lo viejo se llena de a poco detrás. `--minutos` es el tope natural de una
corrida nocturna (acota el TIEMPO, no la cantidad, que es lo que importa
cuando cada documento tarda distinto).

Medido con datos reales (2026-08-20): de 16.577 comprobantes, 9.821 caen
dentro de la ventana de 24 meses. A 2 h por noche son ~41 noches para
cubrirlos todos; a 4 h, ~20 noches.

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

VERIFICADO EN VIVO (2026-08-20, contra el RUC real)
----------------------------------------------------
  · **Tres documentos seguidos en una sola sesión: 3/3**, con PDF y XML,
    cero errores. Costó tres arreglos, todos anotados en la regla #142:
    el login necesita visitar `sunat.gob.pe` ANTES y mandar `referer`;
    el panel "Resultado" tapaba el menú al pasar al 2º documento (reset
    con `goto`); y "Nueva Consulta" resolvía a un acceso de Favoritos
    OCULTO que SUNAT agrega tras el primer uso (`_click_texto_visible`).
  · Los archivos que quedan en R2: PDF válidos y XML PLANOS (no el ZIP
    que entrega SUNAT), con su detalle de líneas legible.
  · La selección: universo del parquet, ventana de 24 meses, orden
    más-nuevo-primero y descarte de lo ya subido.

RIESGO ACEPTADO A PROPÓSITO (igual que el endpoint no documentado de
`sunat.py`, ver regla #140, pero un escalón más arriba): esto navega el
portal SOL con técnicas anti-detección (esconder `navigator.webdriver`,
user-agent de navegador real) porque sin eso Chromium headless no pasa el
login. No es un contrato público de SUNAT — puede romperse con cualquier
cambio del portal.

Por eso, aunque esté pensado para correr de noche, conviene MIRAR EL LOG
cada tanto en vez de darlo por hecho: el día que SUNAT cambie un selector,
esto va a fallar en silencio salvo que alguien lea la salida. Y si empieza
a fallar todo junto, el diagnóstico es el mismo de siempre: `--ver` para
mirar la ventana, DevTools sobre el portal a mano, y comparar.
"""
from __future__ import annotations

import argparse
import io
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


def _click_texto_visible(pagina, texto: str, timeout_ms: int = 10000) -> None:
    """Click en la coincidencia VISIBLE de `texto` exacto — no en `.first`.

    SUNAT parece ir agregando accesos de "Favoritos"/recientes a medida
    que se usa un ítem del menú: después del primer uso, el mismo texto
    puede existir DOS veces en el DOM (el ítem real del menú + un acceso
    directo todavía escondido), y `.first` no garantiza cuál de los dos
    es — puede agarrar el escondido. Verificado en vivo (2026-08-20): con
    `.first` a secas, el 2º y 3er documento de una corrida fallaban acá
    con "Element is not visible", apuntando a un link
    `class="aUltimo aOpcionNavbar"` — justo la pinta de un acceso de
    Favoritos. Acá se revisan TODAS las coincidencias y se clickea la
    que esté realmente visible en ESE momento.
    """
    limite = time.time() + timeout_ms / 1000
    while time.time() < limite:
        for candidato in pagina.get_by_text(texto, exact=True).all():
            if candidato.is_visible():
                candidato.click(force=True)
                return
        time.sleep(0.3)
    raise Exception(f"'{texto}' no apareció visible en {timeout_ms}ms.")


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

    _click_texto_visible(pagina, "Comprobantes de pago")
    time.sleep(0.8)
    _click_texto_visible(pagina, "Comprobantes de Pago")
    time.sleep(0.8)
    _click_texto_visible(pagina, "Consulta de Comprobantes de Pago")
    time.sleep(0.8)
    _click_texto_visible(pagina, "Nueva Consulta de comprobantes de pago")


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


def _xml_del_zip(crudo: bytes) -> bytes:
    """El XML de la factura, sacado del ZIP que entrega SUNAT.

    El botón "Descargar XML" del portal NO baja un XML: baja un ZIP con
    DOS archivos — la factura (`<ruc>-01-<serie>-<numero>.xml`) y el CDR,
    la constancia de recepción, que va con prefijo `R-`. Acá se devuelve
    la factura.

    La primera versión guardaba el ZIP crudo bajo la clave `.xml`
    (verificado en vivo 2026-08-20 sobre el único documento sincronizado:
    empezaba con `PK`). Eso rompía dos cosas: el botón "XML" de
    la webapp entregaba un archivo `.xml` que ningún visor abre, y el
    detalle de líneas —que es la razón de guardar el XML— quedaba detrás
    de un unzip que nadie hacía.

    Si el contenido no fuera un ZIP (o no trajera XML adentro), se
    devuelve tal cual: mejor guardar algo que perder la descarga.
    """
    import zipfile

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
        # Distinguir "SUNAT no encontró nada" (normal, seguir con el
        # próximo documento) de "el servidor de SUNAT está caído en este
        # momento" (transitorio, NO es que falte este documento — visto
        # en vivo 2026-08-20: un modal "Error del Servidor" / "reintentar
        # en 5 minutos" se etiquetaba igual que un resultado vacío).
        if pagina.get_by_text("Error del Servidor", exact=False).is_visible():
            _log("    ⚠️ SUNAT devolvió \"Error del Servidor\" (transitorio, no es "
                "que falte el documento) — probá de nuevo en unos minutos")
            try:
                pagina.get_by_role("button", name="Aceptar").click(timeout=3000)
            except Exception:
                pass
        elif app_frame.get_by_text("No hay resultados", exact=False).is_visible():
            _log("    sin resultados (SUNAT no encontró el comprobante)")
        else:
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
        xml_bytes = _xml_del_zip(pathlib.Path(descarga.value.path()).read_bytes())

    return pdf_bytes, xml_bytes


# ===========================================================================
# R2
# ===========================================================================

def _claves_ya_en_r2(s3, bucket: str) -> set:
    """Todas las claves ya subidas bajo el prefijo de originales, en un set.

    UNA llamada por cada 1000 claves, en vez de dos `head_object` por
    documento. No es microoptimización: en el backfill de un par de años
    (~24.000 documentos = ~48.000 claves) la diferencia es entre ~50
    llamadas y ~48.000. Con head_object por documento, sólo el chequeo
    de "¿qué falta?" tardaba varios minutos por cada mes consultado
    (medido en vivo 2026-08-20, 1.034 documentos).
    """
    claves = set()
    token = None
    while True:
        kw = {"Bucket": bucket, "Prefix": f"{sunat.PREFIJO_ORIGINALES}/"}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        claves.update(o["Key"] for o in resp.get("Contents", []))
        if not resp.get("IsTruncated"):
            return claves
        token = resp.get("NextContinuationToken")


def _subir(s3, bucket: str, clave: str, contenido: bytes, content_type: str) -> None:
    s3.put_object(Bucket=bucket, Key=clave, Body=contenido, ContentType=content_type)


# ===========================================================================
# MAIN
# ===========================================================================

def _comprobantes(desde=None, hasta=None) -> pd.DataFrame:
    """El universo de comprobantes candidatos, MÁS NUEVOS PRIMERO.

    Sale del parquet que dejó `sunat_registro_sync.py` — que ya trae
    TODOS los períodos deduplicados (regla #143) — y sólo cae a la API si
    ese parquet todavía no existe. Es la diferencia entre arrancar en 1
    segundo o en ~4 minutos de llamadas a SUNAT antes de bajar el primer
    PDF.

    El orden importa y es una decisión, no un default: se baja de lo más
    nuevo hacia atrás porque es lo que la gente consulta. La contra está
    documentada en `_MESES_VENTANA`.
    """
    df = sunat._registro_de_parquet()
    if df is None:
        _log("(el parquet del registro no está en R2todavía; "
            "consultando la API — más lento)")
        periodos = [p for p in sunat.periodos_disponibles()
                    if (desde is None or p >= desde) and (hasta is None or p <= hasta)]
        if not periodos:
            return sunat.registros_a_df([])
        df = pd.concat([sunat.obtener_comprobantes(p) for p in periodos],
                       ignore_index=True)
        df = df.drop_duplicates(subset="car")
    elif desde or hasta:
        per = df["periodo_registro"] if "periodo_registro" in df else df["periodo"]
        if desde:
            df = df[per >= desde]
        if hasta:
            df = df[per <= hasta]

    if df.empty:
        return df
    return df.sort_values("fecha_emision", ascending=False).reset_index(drop=True)


# SUNAT no entrega el original de comprobantes muy antiguos: el README del
# proyecto de terceros del que salió este flujo avisa que pasados ~24 meses
# la consulta sólo muestra datos generales, sin botón de descarga. NO está
# verificado de primera mano acá — por eso es un flag y no una constante
# escondida. Sirve para que una corrida nocturna no gaste horas insistiendo
# con documentos que SUNAT nunca va a servir (cada intento fallido cuesta
# el timeout de 15 seg esperando la tabla de resultados).
_MESES_VENTANA = 24


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Baja PDF/XML originales de SUNAT (portal SOL) y los sube a R2.")
    ap.add_argument("--desde", help="Período yyyymm inicial (inclusive). "
                    "Sin --desde/--hasta toma todo, más nuevo primero.")
    ap.add_argument("--hasta", help="Período yyyymm final (inclusive)")
    ap.add_argument("--limite", type=int, default=None,
                    help="Máximo de documentos a bajar en esta corrida (para probar)")
    ap.add_argument("--minutos", type=int, default=None,
                    help="Corta la corrida pasados N minutos. Es el tope "
                        "natural de una corrida nocturna: acota el tiempo, "
                        "no la cantidad, que es lo que realmente importa "
                        "cuando cada documento tarda distinto.")
    ap.add_argument("--meses-atras", type=int, default=_MESES_VENTANA,
                    help=f"No intentar documentos con más de N meses "
                        f"(default {_MESES_VENTANA}: SUNAT deja de servir "
                        f"el original pasada esa ventana). 0 = sin límite.")
    ap.add_argument("--forzar", action="store_true",
                    help="Vuelve a bajar aunque ya exista en R2")
    ap.add_argument("--ver", action="store_true",
                    help="Abre el Chromium en una ventana visible en vez de "
                        "invisible (headless). Más lento, pero para la "
                        "primera corrida sirve para VER qué hace en vez de "
                        "leer un stack trace si algo falla.")
    args = ap.parse_args()

    for flag, val in (("--desde", args.desde), ("--hasta", args.hasta)):
        if val is not None and not sunat.periodo_valido(val):
            _log(f"❌ {flag} debe tener formato yyyymm (ej: 202608).")
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

    _log("Cargando el registro de comprobantes…")
    todos = _comprobantes(args.desde, args.hasta)
    _log(f"{len(todos)} comprobantes en el universo (más nuevos primero).")
    if todos.empty:
        return

    if args.meses_atras:
        corte = (pd.Timestamp.today().normalize()
                 - pd.DateOffset(months=args.meses_atras))
        antes = len(todos)
        todos = todos[todos["fecha_emision"] >= corte]
        if antes != len(todos):
            _log(f"{antes - len(todos)} documentos anteriores a "
                f"{corte:%Y-%m} se saltan: fuera de la ventana de "
                f"{args.meses_atras} meses en que SUNAT sirve el original "
                f"(--meses-atras 0 para intentarlos igual).")

    s3 = data.get_s3_cliente()
    bucket = st.secrets["R2_BUCKET"]

    _log("Listando lo que ya está en R2…")
    ya_en_r2 = _claves_ya_en_r2(s3, bucket)

    pendientes = []
    for _, doc in todos.iterrows():
        claves = set(sunat.claves_original(doc))
        if args.forzar or not claves <= ya_en_r2:
            pendientes.append(doc)

    # El total REAL pendiente se informa ANTES de recortar por --limite.
    # Antes se imprimía después, con el texto "el resto ya está en R2", y
    # mentía en el caso más importante: con --limite 3 sobre 1.034
    # documentos sin sincronizar decía "3 por sincronizar (el resto ya
    # está en R2)" — dando a entender que faltaban 3 cuando faltaban
    # 1.031. Un backfill se planifica con este número; si miente, se
    # planifica mal.
    total_pendiente = len(pendientes)
    ya = len(todos) - total_pendiente
    _log(f"{total_pendiente} sin sincronizar · {ya} ya en R2 "
        f"(de {len(todos)} del rango).")
    if args.limite is not None and args.limite < total_pendiente:
        pendientes = pendientes[:args.limite]
        _log(f"--limite {args.limite}: esta corrida intenta sólo "
            f"{len(pendientes)}, quedan {total_pendiente - len(pendientes)} "
            f"para después.")
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
            corte_t = (time.time() + args.minutos * 60) if args.minutos else None
            for i, doc in enumerate(pendientes, 1):
                # El corte se chequea ANTES de empezar el documento, no en
                # el medio: cortar a mitad de una descarga dejaría el PDF
                # subido sin su XML, y el chequeo de "ya está en R2" exige
                # los DOS para darlo por hecho — así que el documento se
                # reintentaría entero igual. Mejor no empezarlo.
                if corte_t and time.time() > corte_t:
                    _log(f"\n⏱ Corte por --minutos {args.minutos}: quedan "
                        f"{len(pendientes) - i + 1} para la próxima corrida.")
                    break
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
