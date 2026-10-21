"""graficos.costos_consistencia — Costos › «Consistencia de datos».

VISTA NUEVA EL 2026-10-21, a pedido («quiero saber si mi sistema a nivel
data maestra es lógico»), sobre un boceto con los datos reales
(https://claude.ai/artifact/JDqYExY3U12yEfTrnewdhJ). Una lista de CONTROLES
—preguntas que el maestro del POS y del Almacén, y sus movimientos, deberían
poder contestar sin contradecirse— y, al costado, la ficha del elegido: por
qué importa, la regla, qué hacer y TODOS sus casos, con su CSV.

Nació el mismo día como «Consistencia del maestro» y dibujada con
`st.dataframe`; se renombró a pedido («no sólo ve el maestro») y pasó a una
PIEZA PROPIA (`st.components.v2`, como la tabla de Costo de ventas):
`costos_consistencia.js` y `.css`. La tabla nativa no podía tener la forma
del boceto aprobado —tarjetas de indicadores, pestañas con sus puntos,
grupos, chips y la ficha— y el usuario vio otra cosa de la que aprobó
(regla #689). Todo lo que se elige ahí lo resuelve el navegador: los casos
son pocos miles y viajan enteros.

La cuenta vive en `consistencia_maestro.py` (pura, con su test); la carga,
en `data.consistencia_maestro` (caché de disco con los sellos de catorce
parquets: la primera vez de cada versión tarda alrededor de un minuto).

Reglas #686, #689 y #690.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

import consistencia_maestro as cm
import data

_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "costos_consistencia",
    css=(_AQUI / "costos_consistencia.css").read_text(encoding="utf-8"),
    js=(_AQUI / "costos_consistencia.js").read_text(encoding="utf-8"),
)


def _num(v):
    """Un float para el JSON, o None (NaN no es JSON)."""
    return None if pd.isna(v) else float(v)


def _filas(casos):
    """Los casos de un control como filas [código, nombre, área, dato, soles,
    fecha, quién], de mayor a menor monto. Pura."""
    if casos.empty:
        return []
    orden = casos["soles"].abs().sort_values(ascending=False, na_position="last").index
    c = casos.loc[orden]
    fecha = pd.to_datetime(c["fecha"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")
    texto = lambda col: c[col].fillna("").astype(str).tolist()  # noqa: E731
    return [list(f) for f in zip(texto("codigo"), texto("nombre"), texto("area"),
                                 texto("dato"), [_num(v) for v in c["soles"]],
                                 fecha.tolist(), texto("quien"))]


def armar(resultado, hoy):
    """Lo que recibe la pieza: el corte, los grupos y, por control, sus
    textos (de `CONTROLES`), su estado y sus casos. Pura: la lee el test."""
    res = cm.resumen(resultado).set_index("id")
    controles = []
    for c in cm.CONTROLES:
        if c.id not in res.index:
            continue
        r, f = resultado[c.id], res.loc[c.id]
        ok = isinstance(r, pd.DataFrame)
        controles.append({
            "id": c.id, "dom": c.dominio, "estado": f["estado"], "nombre": c.nombre,
            "mide": c.mide, "porque": c.porque, "regla": c.regla, "accion": c.accion,
            "ya": c.ya_lo_ve, "cols": list(c.columnas), "n": int(f["casos"]),
            "soles": _num(f["soles"]), "concentra": f["concentra"] if ok else "",
            "error": "" if ok else str(r), "casos": _filas(r) if ok else [],
        })
    return {"hoy": f"{pd.Timestamp(hoy):%d/%m/%Y}", "dominios": [list(d) for d in cm.DOMINIOS],
            "controles": controles}


def renderizar():
    """La vista entera, en su tarjeta. La llama `graficos/costos.py` cuando
    el rail está en «Consistencia de datos»."""
    with st.container(border=True, key="ajuste_graf_card_izq_cmaestro"):
        with st.spinner("Revisando los datos… la primera vez del día tarda "
                        "alrededor de un minuto."):
            r = data.consistencia_maestro()
        if not r:
            st.warning("No se pudieron revisar los datos (¿R2 caído?). "
                       "Reintentá en unos segundos.")
            return
        _PIEZA(key="costos_consistencia", data=armar(r["casos"], r["hoy"]),
               width="stretch")
