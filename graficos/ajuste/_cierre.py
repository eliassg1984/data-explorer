"""Diferencias del cierre: una pieza local con estado propio (#720, #748).
Lo único que vuelve a Python es «¿Por qué?»: el salto a la línea en
«Análisis de diferencias», la vista de abajo."""
from graficos.movil import css_movil, js_movil
from pathlib import Path
import hashlib

import pandas as pd
import streamlit as st

import navegacion
from graficos.base import poner_seleccion
from . import _diferencias as dif
from ._cierre_datos import armar

_DIR = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "ajuste_cierre",
    css=css_movil((_DIR / "cierre.css").read_text(encoding="utf-8")),
    js=js_movil((_DIR.parent / "_xlsx.js").read_text(encoding="utf-8")
       + (_DIR / "cierre.js").read_text(encoding="utf-8")),
)
K_PIEZA = "aj_cierre_pieza"
_K_IR = "_aj_cierre_ir"
VISTA_ANALISIS = "Diferencias"
"""El id de «Análisis de diferencias» en la pila de Ajuste (`_PILA`)."""


def al_porque(payload):
    """El clic en «¿Por qué? →» de un producto: deja «Análisis de
    diferencias» en ese cierre y en esa línea (área × producto), sin filtros
    que la escondan, y pide el salto a su sección. Corre antes de la corrida
    del fragment; la corrida completa la pide `vista_cierre` al final, cuando
    la pieza ya se registró (regla #373). Un pedido que no corresponde a una
    sesión ni a un área de los datos no hace nada."""
    ss = st.session_state
    v = (ss.get(K_PIEZA) or {}).get("porque")
    if not isinstance(v, dict):
        return
    ses = v.get("ses")
    sesiones = {s["clave"] for s in (payload or {}).get("sesiones", [])}
    acod = (payload or {}).get("acod", {}).get(str(v.get("area", "")))
    cod = str(v.get("cod") or "").strip().lstrip("0")
    if ses not in sesiones or acod is None or not cod:
        return
    ss[dif.K_SES] = ses
    dif._ir(f"{int(acod)}|{cod}", "sob" if v.get("lado") == "s" else "fal")
    # La familia del producto tiene que estar en el filtro de la vista de
    # abajo, que abre con las cinco de entrada.
    fam = str(v.get("fam") or "")
    actuales = list(ss.get(dif.K_FAM) or [])
    if fam and actuales and fam not in actuales:
        poner_seleccion(dif.K_FAM, actuales + [fam])
    ss[navegacion.CLAVE_SALTO_VISTA] = VISTA_ANALISIS
    ss[_K_IR] = True


def vista_cierre(df):
    # Cache de sesión: no normalizar todo el histórico por un rerun ajeno.
    huella = hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes()).hexdigest()
    firma = (huella, tuple(df.columns))
    cache = st.session_state.get("_aj_cierre_payload")
    if cache is None or cache[0] != firma:
        cache = (firma, armar(df))
        st.session_state["_aj_cierre_payload"] = cache
    p = dict(cache[1])
    p["perspectiva"] = st.session_state.get("_aj_persp_cierre", "Por familia")
    _PIEZA(data=p, key=K_PIEZA, on_porque_change=lambda: al_porque(cache[1]))
    if st.session_state.pop(_K_IR, False):
        # «Análisis de diferencias» es OTRO fragment: una corrida completa.
        st.rerun(scope="app")
