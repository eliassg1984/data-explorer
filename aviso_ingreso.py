"""aviso_ingreso.py - avisa por Telegram cuando alguien entra a la app, con
la ubicación GPS del dispositivo si el navegador la concede.

Se dispara UNA vez por sesión de Streamlit (guardia en `session_state`): un
F5 abre una sesión nueva, así que SÍ vuelve a avisar — es la definición de
"entrar" que usamos acá, distinta de la del login, que persiste por cookie
del lado de Streamlit Cloud y no pasa por este módulo.

Manda DOS mensajes en vez de uno para no perder el aviso si el usuario
rechaza el permiso de ubicación: el primero (quién entró, sin ubicación)
sale apenas arranca la sesión; el segundo llega cuando el navegador
responde al pedido de geolocalización — con las coordenadas o con el
motivo por el que no las dio.

Requiere en los secrets (Streamlit Cloud → Settings → Secrets), planos
como el resto de `data.py`:
    TELEGRAM_BOT_TOKEN = "123456:ABC..."
    TELEGRAM_CHAT_ID   = "123456789"
Si faltan, no hace nada — mismo criterio que `secrets_disponibles` en
`data.py`: un secret ausente no puede romper la app.

Quién es "alguien": `st.user.email`. Streamlit Community Cloud lo llena
solo en apps privadas SIN un `[auth]` propio en secrets (nuestro caso: la
restricción de acceso es la de "Only specific people can view this app"
de la consola, no un proveedor OIDC configurado a mano). Hay un bug
conocido de Streamlit (issue #11373 del repo streamlit/streamlit) donde a
veces vuelve vacío igual — si pasa, el aviso sale con "desconocido" en vez
de fallar.
"""

import datetime
import logging
from zoneinfo import ZoneInfo

import requests
import streamlit as st

from inyecciones import inyectar_html

_SECRETS_TG = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
_K_RELEVO = "aviso_ingreso_geo"
_ZONA_PERU = ZoneInfo("America/Lima")


def _telegram_disponible():
    try:
        return all(k in st.secrets for k in _SECRETS_TG)
    except Exception:
        return False


def _enviar_telegram(texto):
    if not _telegram_disponible():
        return
    token = st.secrets["TELEGRAM_BOT_TOKEN"]
    chat_id = st.secrets["TELEGRAM_CHAT_ID"]
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": texto},
            timeout=5,
        )
    except Exception:
        logging.getLogger("app").warning("aviso_ingreso: fallo al avisar por Telegram", exc_info=True)


def _viewer_email():
    try:
        email = getattr(st.user, "email", None)
    except Exception:
        email = None
    return email or "desconocido"


def _ahora_lima():
    return datetime.datetime.now(_ZONA_PERU).strftime("%d/%m/%Y %H:%M")


def _on_geo():
    valor = st.session_state.get(_K_RELEVO, "")
    st.session_state["_aviso_ingreso_geo_listo"] = True
    email = st.session_state.get("_aviso_ingreso_email", "desconocido")
    if valor.startswith("no_disponible"):
        motivo = valor.split(":", 1)[1] if ":" in valor else "desconocido"
        _enviar_telegram(f"📍 Sin ubicación para {email}\nMotivo: {motivo}")
        return
    try:
        lat_txt, lon_txt = valor.split(",")
        float(lat_txt)
        float(lon_txt)
    except ValueError:
        return
    _enviar_telegram(f"📍 Ubicación de {email}\nhttps://maps.google.com/?q={lat_txt},{lon_txt}")


def _capturar_ubicacion():
    if st.session_state.get("_aviso_ingreso_geo_listo"):
        return
    st.text_input("geo", key=_K_RELEVO, label_visibility="collapsed", on_change=_on_geo)
    inyectar_html(f"""<script>
    (function () {{
      var w = window.parent, doc = w.document;
      var intentos = 0;
      function intentar() {{
        intentos++;
        var relevo = doc.querySelector('[class*="st-key-{_K_RELEVO}"] input');
        if (!relevo) {{
          if (intentos < 20) w.setTimeout(intentar, 100);
          return;
        }}
        if (relevo.__geoDisparado) return;
        relevo.__geoDisparado = true;
        var setterInput = w.Object.getOwnPropertyDescriptor(
          w.HTMLInputElement.prototype, 'value').set;
        function mandar(valorTxt) {{
          relevo.focus();
          setterInput.call(relevo, valorTxt);
          relevo.dispatchEvent(new Event('input', {{bubbles: true}}));
          var opts = {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                      bubbles: true, cancelable: true}};
          relevo.dispatchEvent(new KeyboardEvent('keydown', opts));
          relevo.dispatchEvent(new KeyboardEvent('keyup', opts));
        }}
        if (!w.navigator.geolocation) {{
          mandar('no_disponible:sin_api_de_geolocalizacion');
          return;
        }}
        w.navigator.geolocation.getCurrentPosition(
          function (pos) {{
            mandar(pos.coords.latitude + ',' + pos.coords.longitude);
          }},
          function (err) {{
            mandar('no_disponible:' + ((err && err.message) || 'error'));
          }},
          {{timeout: 8000, maximumAge: 60000}}
        );
      }}
      intentar();
    }})();
    </script>""")


def procesar_aviso_ingreso():
    """Llamar UNA vez, cerca del arranque de `app.py`."""
    if not _telegram_disponible():
        return
    if not st.session_state.get("_aviso_ingreso_enviado"):
        st.session_state["_aviso_ingreso_enviado"] = True
        email = _viewer_email()
        st.session_state["_aviso_ingreso_email"] = email
        _enviar_telegram(
            f"🔓 Ingreso a la webapp\nUsuario: {email}\nHora: {_ahora_lima()} (Lima)\nUbicación: pidiendo permiso al navegador…"
        )
    _capturar_ubicacion()
