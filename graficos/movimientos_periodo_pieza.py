"""Requerimientos, Salidas y Producción: sólo la fecha vuelve a Python (#722/#727)."""
from graficos.movil import css_movil, js_movil
import datetime as dt
import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st

from . import movimientos_periodo_datos as datos

_DIR = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "movimientos_periodo",
    # Los íconos de la app (descargar, ampliar; regla #821), desde la #845.
    css=css_movil((_DIR / "iconos.css").read_text(encoding="utf-8")
                  + (_DIR / "movimientos_periodo.css").read_text(encoding="utf-8")),
    js=js_movil((_DIR / "_xlsx.js").read_text(encoding="utf-8")
       + (_DIR / "iconos.js").read_text(encoding="utf-8")
       + (_DIR / "movimientos_periodo.js").read_text(encoding="utf-8")))

# ── Lo que Req. y salidas lee de Python (regla #845) ──────────────────────
K_CONTAR = "mov_contar"
"""«Contar por»: en qué mes cae cada documento. Se elige al costado del panel
de la fecha (`movimientos.AJUSTES_PIE`), como las fechas de las salidas
(#644); hasta la #845 era un control de la pieza."""
CONTAR = {"Cierre": "cie", "Registro": "reg", "Proceso": "pro"}
ROT_CONTAR = {"Cierre": "al cierre", "Registro": "por registro", "Proceso": "por proceso"}
K_CORTE_PERSP = "_mov_persp_corte"
"""La clave del segundo eje de la perspectiva (`movimientos.K_CORTE`): la
pestaña «Cadena por área» la escribe."""
K_ZONA = "_mov_zona_pedida"
"""`{"v": pestaña, "n": contador}`: la pestaña de la pieza que se pidió desde
«Cadena por área». La pieza la toma una vez por `n`."""


def contar_por():
    """El «Contar por» elegido (`"Cierre"` por defecto)."""
    v = st.session_state.get(K_CONTAR)
    return v if v in CONTAR else "Cierre"


def ir_a_cadena():
    """La pestaña «Cadena por área»: deja elegida la perspectiva «Análisis
    por área» del mismo lado. La corrida del fragment la dibuja."""
    st.session_state[K_CORTE_PERSP] = "Análisis por área"


def ir_a_zona(zona):
    """Una pestaña de la pieza, desde «Cadena por área»: vuelve a «Resumen»
    y le pide a la pieza que abra en `zona`."""
    ss = st.session_state
    ss[K_CORTE_PERSP] = "Resumen"
    ss[K_ZONA] = {"v": zona, "n": int((ss.get(K_ZONA) or {}).get("n", 0)) + 1}


def _huella(d):
    return (hashlib.sha256(pd.util.hash_pandas_object(d, index=True).values.tobytes()).hexdigest()
            if d is not None else None)


def referencias_por_mes():
    """`{"2026-09": {"plato", "compras"}}`: el costo de lo que salió a plato y
    lo comprado en cada mes físico, de `data.sin_plato_por_cierre`."""
    import data
    r = data.sin_plato_por_cierre()
    if not r:
        return {}
    out = {}
    for i, p in enumerate(r["periodos"]):
        t = r["totales"]
        y, m = p["mes"]
        out[f"{y}-{m:02d}"] = dict(
            plato=float(t["venta"][i] + t["cort"][i] + t["evvi"][i]),
            compras=float(t["compras"][i]))
    return out


def renderizar(d, lado, cols, *, hist=None, anios=0, rot_fecha="",
               rango=None, fecha=None, faltante=None, marcas=None):
    if not all(cols.get(c) for c in ("fecha", "val")):
        st.info("No hay columnas suficientes para este gráfico.")
        return
    ss = st.session_state
    # Las tres fechas viajan en `cols`: la firma de las tarjetas no cambia (#772).
    cols = dict(cols)
    relojes = cols.pop("relojes", None)
    # Lo que recortó la página (en Movimientos, nada desde la #846).
    _sub, _fam = ss.get("_mov_filtros_pagina") or ([], [])
    contexto = {"Áreas de la página": list(_sub), "Familias de la página": list(_fam)}
    firma = (727, _huella(d), tuple(d.columns), tuple(cols.items()), _huella(hist),
             _huella(marcas), anios, str(rango), rot_fecha, str(faltante),
             str(contexto), str(dt.date.today()))
    kc = f"_{lado.k}_pieza_cache"
    cache = ss.get(kc)
    if cache is None or cache[0] != firma:
        cache = (firma, datos.armar(d, lado, cols, hist=hist, anios=anios,
                 rango=rango, rot_fecha=rot_fecha, faltante=faltante,
                 marcas=marcas, contexto=contexto, relojes=relojes))
        ss[kc] = cache
    p = dict(cache[1])
    # También al reutilizar un mensaje de una versión anterior: la orden
    # generada no puede heredar la regla de Requerimientos (#575/#727).
    p.update(suma_sin_procesar=lado.suma_sin_procesar,
             produccion=not lado.suma_sin_procesar,rotulo_tipo=lado.rotulo_tipo)
    # #845: Req. y salidas va bajo las carpetas de su perspectiva: la cápsula sube
    # a la banda, la última pestaña lleva a la cadena por área y «Contar por»
    # viene del panel de la fecha. Producción usa la misma pieza sin carpetas.
    if relojes:
        p.update(banda=True, cadena=True, reloj=CONTAR[contar_por()],
                 zona=ss.get(K_ZONA))
    p["inicial"] = {"gran": ss.get(f"{lado.k}_gran", "Mes" if relojes else "Semana"),
                    "area": ss.get(f"{lado.k}_areas") or [],
                    "tipo": ss.get(f"{lado.k}_tipos") or [],
                    "fam": ss.get(f"{lado.k}_familias") or [],
                    "prod": ss.get(f"{lado.k}_productos") or [],
                    "partir": ss.get(f"{lado.k}_partir")}
    envoltura = f"{lado.k}_nativa"
    st.markdown(f"""<style>
    .st-key-{envoltura}{{position:relative;gap:0!important}}
    .st-key-{envoltura}_fecha{{position:absolute;right:18px;top:{-40 if relojes else 12}px;z-index:5;width:auto!important}}
    .st-key-{envoltura}>[data-testid="stElementContainer"]{{margin:0!important}}
    </style>""", unsafe_allow_html=True)
    with st.container(key=envoltura):
        if fecha:
            with st.container(key=f"{envoltura}_fecha"):
                fecha()
        k_refs = f"_{lado.k}_refs"
        _PIEZA(key=f"{lado.k}_pieza", data=p,
               on_refs_change=lambda: ss.__setitem__(k_refs, True),
               on_cadena_change=ir_a_cadena)
        # Lo vendido y lo comprado de cada mes salen de la cuenta de Sin plato,
        # que en frío tarda: la pieza dibuja primero y los pide (regla #772).
        if ss.get(k_refs) and relojes and relojes.get("pedir_refs"):
            _PIEZA(key=f"{lado.k}_pieza_refs", width="stretch",
                   data={"parte": "refs", "k": lado.k, "refs": referencias_por_mes()},
                   on_refs_change=lambda: None)
