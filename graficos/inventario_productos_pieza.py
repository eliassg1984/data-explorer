"""Stock por Producto como pieza propia (#721). Sólo una foto pide Python."""
import datetime as dt
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

import data
import kardex
from . import inventario_productos as ip
from . import inventario_productos_datos as datos

_DIR = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "stock_productos",
    css=(_DIR / "inventario_productos.css").read_text(encoding="utf-8"),
    js=(_DIR / "_xlsx.js").read_text(encoding="utf-8")
       + (_DIR / "inventario_base.js").read_text(encoding="utf-8")
       + (_DIR / "inventario_productos.js").read_text(encoding="utf-8"))
_K_PIEZA, _K_PEDIDO = "inv_stock_pieza", "_inv_stock_pedido"
_K_CACHE, _K_FOTOS = "_inv_stock_base", "_inv_stock_fotos"


def _pedir_foto():
    v = (st.session_state.get(_K_PIEZA) or {}).get("foto")
    if isinstance(v, dict):
        st.session_state[_K_PEDIDO] = dict(v)


def _huella(d):
    return hashlib.sha256(pd.util.hash_pandas_object(d, index=True).values.tobytes()).hexdigest()


def renderizar(d, cols):
    if not (cols.get("prod") and cols.get("val")):
        st.info("Faltan las columnas de producto o de valorizado para este listado.")
        return
    historia = data.historia_stock() if cols.get("cod_area") else None
    consumo = data.consumo_stock(historia[1][-1].date()) if historia is not None else None
    rango = data.rango_fechas(kardex.ARCHIVO, kardex.COL_FECHA) if cols.get("cod_area") and cols.get("cod") else None
    firma = (_huella(d), tuple(d.columns), tuple(cols.items()),
             _huella(historia[2]) if historia is not None else None,
             _huella(consumo) if consumo is not None else None,
             tuple(historia[0]) if historia is not None else (), tuple(rango or ()))
    cache = st.session_state.get(_K_CACHE)
    if cache is None or cache[0] != firma:
        cache = (firma, datos.armar(d, cols, historia, consumo, rango))
        st.session_state[_K_CACHE] = cache
        st.session_state[_K_FOTOS] = {}
    p = dict(cache[1]);ss = st.session_state
    p["semilla"] = ss.get("_inv_stock_salto", 0)
    p["inicial"] = {"areas": ss.get(ip._K_AREAS, p["areas_iniciales"]) or [],
                    "fams": ss.get(ip._K_FAMILIAS) or [], "subs": ss.get(ip._K_SUBFAMILIAS) or [],
                    "q": ss.get(ip._K_BUSCAR) or "", "sin": bool(ss.get(ip._K_SIN_STOCK)),
                    "salida": bool(ss.get(ip._K_SALIDA)), "chip": ss.get(ip._K_ESTADO, "todos")}
    _PIEZA(key=_K_PIEZA, data=p, on_foto_change=_pedir_foto)
    pedido = ss.get(_K_PEDIDO)
    if not pedido or pedido.get("sello") != p["sello"] or not rango:
        return
    try:
        fecha = dt.date.fromisoformat(str(pedido["fecha"]))
        hora = int(pedido["hora"])
    except (KeyError, ValueError, TypeError):
        return
    if not (rango[0] <= fecha <= rango[1] and 0 <= hora <= 23):
        return
    clave = (str(fecha), hora)
    fotos = ss.setdefault(_K_FOTOS, {})
    if clave not in fotos or pedido.get("reintentar"):
        ant = data.stock_al(kardex.momento(fecha, hora))
        hoy = data.stock_al(kardex.momento(rango[1], 23)) if ant is not None else None
        if len(fotos) >= 12:
            fotos.pop(next(iter(fotos)))
        fotos[clave] = datos.foto(d, cols, ant, hoy, fecha, hora, p["sello"])
        pedido["reintentar"] = False
    # Esta instancia sólo entrega la foto. Su wrapper no cobra alto ni gap.
    st.markdown('<style>.st-key-inv_stock_respuesta{display:none}</style>', unsafe_allow_html=True)
    with st.container(key="inv_stock_respuesta"):
        _PIEZA(key="inv_stock_foto", data=fotos[clave])
