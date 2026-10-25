"""Requerimientos, Salidas y Producción: sólo la fecha vuelve a Python (#722/#727)."""
import datetime as dt
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from . import movimientos_periodo_datos as datos

_DIR = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "movimientos_periodo",
    css=(_DIR / "movimientos_periodo.css").read_text(encoding="utf-8"),
    js=(_DIR / "_xlsx.js").read_text(encoding="utf-8")
       + (_DIR / "movimientos_periodo.js").read_text(encoding="utf-8"))


def _huella(d):
    return (hashlib.sha256(pd.util.hash_pandas_object(d, index=True).values.tobytes()).hexdigest()
            if d is not None else None)


def renderizar(d, lado, cols, *, hist=None, anios=0, rot_fecha="",
               rango=None, fecha=None, faltante=None, marcas=None):
    if not all(cols.get(c) for c in ("fecha", "val")):
        st.info("No hay columnas suficientes para este gráfico.")
        return
    ss = st.session_state
    contexto = {"Áreas de la página": ss.get("mov_graf_filtro_sub") or [],
                "Familias de la página": ss.get("mov_graf_filtro_fam") or []}
    firma = (727, _huella(d), tuple(d.columns), tuple(cols.items()), _huella(hist),
             _huella(marcas), anios, str(rango), rot_fecha, str(faltante),
             str(contexto), str(dt.date.today()))
    kc = f"_{lado.k}_pieza_cache"
    cache = ss.get(kc)
    if cache is None or cache[0] != firma:
        cache = (firma, datos.armar(d, lado, cols, hist=hist, anios=anios,
                 rango=rango, rot_fecha=rot_fecha, faltante=faltante,
                 marcas=marcas, contexto=contexto))
        ss[kc] = cache
    p = dict(cache[1])
    # También al reutilizar un mensaje de una versión anterior: la orden
    # generada no puede heredar la regla de Requerimientos (#575/#727).
    p.update(suma_sin_procesar=lado.suma_sin_procesar,
             produccion=not lado.suma_sin_procesar,rotulo_tipo=lado.rotulo_tipo)
    p["inicial"] = {"gran": ss.get(f"{lado.k}_gran", "Semana"),
                    "area": ss.get(f"{lado.k}_areas") or [],
                    "tipo": ss.get(f"{lado.k}_tipos") or [],
                    "fam": ss.get(f"{lado.k}_familias") or [],
                    "prod": ss.get(f"{lado.k}_productos") or [],
                    "partir": ss.get(f"{lado.k}_partir")}
    envoltura = f"{lado.k}_nativa"
    st.markdown(f"""<style>
    .st-key-{envoltura}{{position:relative;gap:0!important}}
    .st-key-{envoltura}_fecha{{position:absolute;right:18px;top:12px;z-index:5;width:auto!important}}
    .st-key-{envoltura}>[data-testid="stElementContainer"]{{margin:0!important}}
    </style>""", unsafe_allow_html=True)
    with st.container(key=envoltura):
        if fecha:
            with st.container(key=f"{envoltura}_fecha"):
                fecha()
        _PIEZA(key=f"{lado.k}_pieza", data=p)
