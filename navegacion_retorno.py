"""Regreso contextual: sólo estado de interfaz, en memoria y con caducidad.

No modifica datos ni las firmas del navegador existente. Los llamadores
capturan ANTES de preparar los filtros del destino (arquitectura.md #742).
"""

from collections import OrderedDict
from copy import deepcopy
import datetime as dt
import json
from pathlib import Path
import re
import secrets
from threading import RLock
import time

import streamlit as st
from inyecciones._iframe import inyectar_html

_DIR = Path(__file__).parent
_JS = (_DIR / "navegacion_retorno.js").read_text(encoding="utf-8")
_PILA = "_retorno_pila"
_COMANDO = "_retorno_comando"
_ACTUAL = "_retorno_actual"
_TTL = 2 * 3600
_MAX = 128
_ENLACES = OrderedDict()
_LOCK = RLock()
_RESERVADAS = re.compile(
    r"(^_retorno|^_nav|^_ctx|^_refresco|^_vigilar|^_perf|^_asistente|^_aviso|"
    r"^form_receta|^nc_|^sunat_(ingreso|ficha_pedido|espera|xml_llegados|lote)|"
    r"token|secret|password|credential|api_key|^FormSubmitter:|"
    r"_ir_carta$|_nonce$|_n$|_docs_salto$|^_rail_saltar|^_pila_seccion_destino)"
)


def _valor_ui(v, nivel=0):
    if nivel > 8:
        return False
    if v is None or type(v) in (str, bool, int, float, dt.date, dt.datetime):
        return not isinstance(v, str) or len(v) < 16000
    if type(v) in (list, tuple, set):
        return len(v) <= 500 and all(_valor_ui(x, nivel + 1) for x in v)
    if type(v) is dict:
        return len(v) <= 100 and all(isinstance(k, (str, int)) and _valor_ui(x, nivel + 1)
                                    for k, x in v.items())
    return False


def _efimeras():
    """Botones y salidas de componentes no se reinyectan como selecciones."""
    try:
        from streamlit.runtime.state import get_session_state
        ss = get_session_state()._state
        meta = ss._new_widget_state.widget_metadata
        return {k for k in st.session_state
                if (m := meta.get(ss._key_id_mapper.get_id_from_key(k, None)))
                and m.value_type in {"trigger_value", "string_trigger_value",
                                     "chat_input_value", "json_value"}}
    except (AttributeError, ImportError, KeyError):
        return set()


def _estado():
    omitir = _efimeras()
    return {k: deepcopy(v) for k, v in st.session_state.items()
            if k not in omitir and not _RESERVADAS.search(k) and _valor_ui(v)}


def _origen():
    reporte = st.session_state.get(_ACTUAL) or st.query_params.get("reporte")
    if not reporte:
        return None
    from graficos import vistas_de
    par = vistas_de(reporte)
    vista = st.session_state.get(par[0]) if par else None
    params = st.query_params.to_dict()
    for k in ("retorno", "refresh"):
        params.pop(k, None)
    params["reporte"] = reporte
    if vista:
        params["vista"] = vista
    return dict(id=secrets.token_hex(16), reporte=reporte, vista=vista,
                nombre=vista or reporte, params=params, estado=_estado(),
                creado=time.time())


def capturar_origen():
    """Empila un salto contextual; nunca se llama desde el menú general."""
    origen = _origen()
    if origen:
        st.session_state[_PILA] = [*st.session_state.get(_PILA, []), origen][-12:]
        st.session_state[_COMANDO] = {"accion": "guardar", "id": origen["id"]}


def enlace_desde_aqui():
    """Token opaco para un enlace en otra pestaña; no lleva datos en la URL."""
    origen = _origen()
    if not origen:
        return ""
    with _LOCK:
        ahora = time.time()
        for k in list(_ENLACES):
            if ahora - _ENLACES[k]["creado"] > _TTL:
                del _ENLACES[k]
        _ENLACES[origen["id"]] = dict(origen, pila=deepcopy(st.session_state.get(_PILA, [])))
        while len(_ENLACES) > _MAX:
            _ENLACES.popitem(last=False)
    return origen["id"]


def preparar(reporte):
    """Antes de dibujar widgets, recibe un enlace contextual de otra pestaña."""
    token = st.query_params.get("retorno", "")
    if token and token != st.session_state.get("_retorno_recibido"):
        st.session_state["_retorno_recibido"] = token
        with _LOCK:
            origen = deepcopy(_ENLACES.get(token)) if re.fullmatch(r"[a-f0-9]{32}", token) else None
        if origen and time.time() - origen["creado"] <= _TTL:
            pila = origen.pop("pila", [])
            st.session_state[_PILA] = [*pila, origen][-12:]
    st.session_state[_ACTUAL] = reporte


def _volver():
    pila = list(st.session_state.get(_PILA, []))
    if not pila:
        return
    origen = pila.pop()
    # El callback corre antes de crear los widgets del nuevo reporte.
    # Borra también los filtros que sembró el destino y antes no existían.
    for k in _estado():
        if k not in origen["estado"]:
            st.session_state.pop(k, None)
    for k, v in origen["estado"].items():
        st.session_state[k] = deepcopy(v)
    st.session_state[_PILA] = pila
    st.session_state["_nav_reporte"] = origen["reporte"]
    if origen.get("vista"):
        st.session_state["_rail_saltar_a"] = origen["vista"]
    st.query_params.from_dict(origen["params"])
    st.session_state[_COMANDO] = {"accion": "restaurar", "id": origen["id"]}


_JS_BOTON = """export default function(c){const p=c.parentElement;
  let b=p.querySelector('button');if(!b){b=document.createElement('button');
    b.type='button';p.append(b)}
  b.disabled=false;b.textContent='← Volver a '+c.data.nombre;b.title=b.textContent;
  b.onclick=()=>{window.__retorno?.restaurar(c.data.id);
    b.disabled=true;c.setTriggerValue('volver',c.data.id)};}"""

_CSS_BOTON = """:host{display:block}button{font:inherit;font-size:14px;line-height:20px;
  box-sizing:border-box;color:#594b86;background:#f7f5fc;
  border:1px solid #ded7ef;border-radius:7px;padding:6px 12px;cursor:pointer;
  max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  button:hover{background:#eee8f8}button:focus-visible{outline:2px solid #7661ae;
  outline-offset:2px}@media(max-width:900px){button{min-height:44px;width:100%;text-align:left}}"""

_BOTON = st.components.v2.component(
    "retorno_contextual",
    css=_CSS_BOTON,
    js=_JS_BOTON,
)


def dibujar():
    pila = st.session_state.get(_PILA, [])
    comando = st.session_state.pop(_COMANDO, None)
    datos = json.dumps(dict(comando=comando, activo=bool(pila), enlace=enlace_desde_aqui()), ensure_ascii=True)
    inyectar_html("<script>" + _JS + "\nwindow.parent.__retorno.configurar(" + datos + ");</script>")
    if not pila:
        return
    st.markdown((_DIR / "navegacion_retorno.css").read_text(encoding="utf-8"), unsafe_allow_html=True)
    origen = pila[-1]
    _BOTON(key="retorno_contextual", data={"id": origen["id"], "nombre": origen["nombre"]},
           on_volver_change=_volver, width="stretch")


def actualizar_enlaces():
    """La primera carga ya tiene creados sus controles y fechas canónicas."""
    token = json.dumps(enlace_desde_aqui())
    inyectar_html("<script>window.parent.__retorno?.configurar({enlace:" + token + "});</script>")
