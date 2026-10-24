"""Diferencias del cierre: dos perspectivas locales con estado propio (#720)."""
from pathlib import Path
import hashlib

import pandas as pd
import streamlit as st

from ._cierre_datos import armar

_DIR = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "ajuste_cierre",
    css=(_DIR / "cierre.css").read_text(encoding="utf-8"),
    js=(_DIR.parent / "_xlsx.js").read_text(encoding="utf-8")
       + (_DIR / "cierre.js").read_text(encoding="utf-8"),
)


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
    _PIEZA(data=p, key="aj_cierre_pieza")
