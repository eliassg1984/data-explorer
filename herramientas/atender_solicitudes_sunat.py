"""
herramientas/atender_solicitudes_sunat.py — atiende los pedidos de
originales que deja la webapp, bajando ese comprobante puntual de SUNAT.

EL PROBLEMA QUE RESUELVE
-------------------------
`sunat_originales_sync.py` baja de lo más nuevo hacia atrás y tarda
semanas en cubrir la ventana entera (~9.800 documentos a ~30 seg cada
uno). Mientras tanto, un comprobante viejo simplemente no está. Esperar
semanas a que le llegue el turno no sirve cuando alguien lo necesita HOY.

Acá está el atajo: la webapp deja una señal JSON en `_solicitudes_sunat/`
de R2 (`sunat.solicitar_original`), este script la levanta, baja ESE
documento y borra la señal. El usuario espera menos de un minuto en vez
de semanas.

Es el MISMO patrón que ya usa el proyecto para refrescar parquets
(`data.py::solicitar_refresco` + `atender_solicitudes.py`), aplicado a
otra cosa. La webapp nunca abre un navegador ni habla con el portal SOL:
sólo pide. Ver `arquitectura.md` regla #144.

USO
---
    python herramientas/atender_solicitudes_sunat.py              (una pasada)
    python herramientas/atender_solicitudes_sunat.py --vigilar    (bucle)
    python herramientas/atender_solicitudes_sunat.py --vigilar --cada 10

Una pasada sin pedidos sale en ~1 segundo y NO abre el navegador — es
barato programarlo cada minuto en el Task Scheduler. Con `--vigilar`
queda dando vueltas, como el poller de solicitudes que ya corre en la
CPU local.

CUANDO HAY VARIOS PEDIDOS, UN SOLO LOGIN
-----------------------------------------
Abrir Chromium y loguearse cuesta ~15 seg, bastante más que consultar un
comprobante. Por eso, si hay 3 pedidos esperando, se abre el navegador
UNA vez y se atienden los 3 en la misma sesión — no uno por pedido.

REQUIERE lo mismo que `sunat_originales_sync.py` (Playwright + Chromium +
las credenciales de SUNAT y R2 en `.streamlit/secrets.toml`).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
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

import streamlit as st         # noqa: E402  — st.secrets vive sin server

import data                    # noqa: E402
import sunat                   # noqa: E402


def _cargar_sync():
    """El módulo del sync nocturno, cargado por ruta.

    Se reusa TODA su lógica de navegación del portal (login, menú,
    formulario, descarga, extracción del XML del ZIP) en vez de
    duplicarla: es la parte frágil y cara de mantener, y tener dos copias
    garantiza que un arreglo se aplique a una sola. El nombre del archivo
    tiene guiones bajos pero vive en `herramientas/`, que no es un
    paquete — de ahí el import por ruta.
    """
    ruta = pathlib.Path(__file__).parent / "sunat_originales_sync.py"
    spec = importlib.util.spec_from_file_location("_sunat_sync", ruta)
    modulo = importlib.util.module_from_spec(spec)
    argv = sys.argv
    sys.argv = [str(ruta)]        # su argparse no debe ver NUESTROS flags
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.argv = argv
    return modulo


def _log(msg):
    print(f"{time.strftime('%H:%M:%S')}  {msg}", flush=True)


def _pedidos(s3, bucket):
    """Las señales pendientes en R2 → [(clave, payload)]."""
    try:
        resp = s3.list_objects_v2(
            Bucket=bucket, Prefix=f"{sunat.PREFIJO_SOLICITUDES}/")
    except Exception as e:
        _log(f"No se pudo listar los pedidos: {e}")
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
            # Una señal ilegible no puede trabar la cola: se borra. Si el
            # usuario todavía lo necesita, vuelve a pedirlo con un clic.
            _log(f"Señal corrupta, se descarta ({clave}): {e}")
            try:
                s3.delete_object(Bucket=bucket, Key=clave)
            except Exception:
                pass
    return salida


def _atender(sync, pagina, s3, bucket, clave_senal, pedido):
    """Baja un comprobante pedido y sube lo que consiga. True si subió algo."""
    doc = {
        "ruc_proveedor": pedido.get("ruc_proveedor", ""),
        "serie": pedido.get("serie", ""),
        "numero": pedido.get("numero", ""),
    }
    clave_pdf, clave_xml = sunat.claves_original(doc)

    sync._ir_a_consulta_comprobantes(pagina)
    pdf_bytes, xml_bytes = sync._consultar_y_descargar(
        pagina, doc["ruc_proveedor"], doc["serie"], doc["numero"],
        pedido.get("tipo_cdp", "01"))

    if pdf_bytes:
        sync._subir(s3, bucket, clave_pdf, pdf_bytes, "application/pdf")
    if xml_bytes:
        sync._subir(s3, bucket, clave_xml, xml_bytes, "application/xml")

    # La señal se borra SIEMPRE, haya salido bien o no. Si no, un
    # comprobante que SUNAT no puede servir (fuera de la ventana de 24
    # meses, o dado de baja) dejaría a la webapp mostrando "⏳ pedido"
    # para siempre y a este script reintentándolo en cada pasada. Que el
    # usuario vea de nuevo el botón y decida es mejor que un bucle mudo.
    s3.delete_object(Bucket=bucket, Key=clave_senal)
    return bool(pdf_bytes or xml_bytes)


def _pasada(sync, s3, bucket, headless=True):
    """Atiende todo lo pendiente. Devuelve cuántos pedidos procesó."""
    pedidos = _pedidos(s3, bucket)
    if not pedidos:
        return 0

    _log(f"{len(pedidos)} pedido(s) esperando.")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador, _ctx, pagina = sync._iniciar_navegador(p, headless=headless)
        try:
            sync._login(pagina, sunat._cred("SUNAT_RUC"),
                        sunat._cred("SUNAT_USUARIO_SOL"),
                        sunat._cred("SUNAT_CLAVE_SOL"))
            sync._cerrar_popups(pagina)

            for clave_senal, pedido in pedidos:
                etiqueta = pedido.get("documento") or clave_senal
                _log(f"  {etiqueta}…")
                try:
                    if _atender(sync, pagina, s3, bucket, clave_senal, pedido):
                        _log("    subido")
                    else:
                        _log("    SUNAT no devolvió el archivo")
                except Exception as e:
                    _log(f"    error: {str(e)[:160]}")
                    # Igual que arriba: se borra la señal para no dejar a la
                    # webapp esperando por algo que va a fallar de nuevo.
                    try:
                        s3.delete_object(Bucket=bucket, Key=clave_senal)
                    except Exception:
                        pass
                time.sleep(sync.PAUSA_ENTRE_DOCS_SEG)
        finally:
            navegador.close()
    return len(pedidos)


def main():
    ap = argparse.ArgumentParser(
        description="Atiende pedidos de originales que deja la webapp en R2.")
    ap.add_argument("--vigilar", action="store_true",
                    help="Queda en bucle en vez de hacer una sola pasada")
    ap.add_argument("--cada", type=int, default=15,
                    help="Con --vigilar: segundos entre pasadas (default 15)")
    ap.add_argument("--ver", action="store_true",
                    help="Navegador visible en vez de headless")
    args = ap.parse_args()

    if not sunat.secrets_disponibles():
        _log("Faltan credenciales de SUNAT en .streamlit/secrets.toml.")
        sys.exit(1)
    if not data.secrets_disponibles():
        _log("Faltan credenciales de R2 en .streamlit/secrets.toml.")
        sys.exit(1)

    sync = _cargar_sync()
    s3 = data.get_s3_cliente()
    bucket = st.secrets["R2_BUCKET"]

    if not args.vigilar:
        n = _pasada(sync, s3, bucket, headless=not args.ver)
        if n == 0:
            _log("Sin pedidos.")
        return

    _log(f"Vigilando {sunat.PREFIJO_SOLICITUDES}/ cada {args.cada} seg. "
         f"Ctrl+C para salir.")
    while True:
        try:
            _pasada(sync, s3, bucket, headless=not args.ver)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            # Un fallo de una pasada (R2 caído, SUNAT caído) no puede matar
            # el vigilante: se reporta y se reintenta en la próxima vuelta.
            _log(f"Pasada fallida: {str(e)[:160]}")
        time.sleep(args.cada)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _log("Cortado.")
