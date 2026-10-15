"""
graficos.simulador_plato — «Simular» un plato de Recetas › Costo Carta.

Lo abre el botón «Simular» de la ficha del plato (`carta_costeada.py::
_panel`), en una ventana modal (`st.dialog`, ancha): la receta como árbol,
con las recetas base abiertas y editables por dentro, el precio de cada línea
por la unidad en que se COMPRA (S/ por kg, no por gramo), la merma y el peso
por corte de los porcionados, los precios de hoy / de la última compra / del
promedio de 90 días, el precio de venta y «para quedar en X %».

REEMPLAZÓ al simulador de `recetaventa.py` (2026-09-17, una `st.data_editor`
de la primera línea de la receta), a pedido el 2026-10-15 sobre el boceto
https://claude.ai/artifact/JFkrxwH2wCipPTGQey1TJ5 («Simular, revisado»).
Aquél no abría las recetas base, editaba el precio de un gramo, no simulaba
el precio de venta ni la merma, y su columna «Costo» iba una corrida atrasada
—el editor de Streamlit no recalcula una columna bloqueada—.

ES UNA PIEZA PROPIA (`st.components.v2`, como `panel_fecha.py`): las cuentas
corren en el navegador mientras se escribe (`simulador_plato.js`), sin una
corrida de Python por tecla. A Python le llega sólo el trigger `guardar`, con
el borrador entero ({ruta: {cant, P, merma, peso}}, el modo de precios, el
precio de venta, el % objetivo y quién guarda), y Python vuelve a hacer la
cuenta con `simulador_receta.costo_arbol` —la gemela de la del JS— antes de
guardarla. Guardar es la PROPUESTA de Nuevo Costeo (`formulario_receta.
_guardar_propuesta`, un JSON en R2): la app no escribe en el POS.

Lo que lee de R2 va en caché por el SELLO de cada parquet (regla #367):
compras (los precios de compra), recetas base y porcionamientos.

Regla #656.
"""

from pathlib import Path

import streamlit as st

import simulador_receta as sr
from data import cargar, sello_datos
from graficos.recetas_comun import divisor_neto

_AQUI = Path(__file__).parent
_COMPONENTE = st.components.v2.component(
    "simulador_plato",
    css=(_AQUI / "simulador_plato.css").read_text(encoding="utf-8"),
    js=(_AQUI / "simulador_plato.js").read_text(encoding="utf-8"),
)

AYUDA = ("Probá cambios en la receta —cantidades, precios de compra, la merma "
         "de un corte, el precio de venta— y mirá cómo se mueven el costo y el "
         "%. Es un borrador: no toca el POS. Se puede guardar como propuesta "
         "de Nuevo Costeo.")

_K_AVISO = "rec_sim_aviso"
"""{cod del plato: texto} — lo que dijo el último «Guardar» de ese plato. Lo
escribe el callback y lo muestra el componente en la corrida siguiente."""

PCT_OBJETIVO = 30
"""El «para quedar en» con que abre: el corte ámbar del semáforo de la
carta (`carta_costeada._UMBRAL_COSTO_OK`)."""


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def _precios_compra(sello, version=sr.VERSION):
    return sr.precios_compra(cargar("compras.parquet"))


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def _bases(sello, version=sr.VERSION):
    return sr.lineas_de_bases(cargar("recetabase.parquet"))


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def _porcionamientos(sello, version=sr.VERSION):
    return sr.porcionamientos_vigentes(cargar("porcionamientos.parquet"))


def armar_arbol(df_rv, cod):
    """El árbol de la receta de `cod`, con lo de R2 en caché."""
    bases, info = _bases(sello_datos("recetabase.parquet"))
    porcs = _porcionamientos(sello_datos("porcionamientos.parquet"))
    compras = _precios_compra(sello_datos("compras.parquet"))
    return sr.arbol_plato(df_rv, cod, bases, info, porcs, compras)


def _usuario():
    """Quién está mirando, para sembrar «Tu nombre». Vacío si no se sabe."""
    try:
        return getattr(st.user, "email", None) or ""
    except Exception:
        return ""


def _lineas_propuesta(nodos, estado, modo):
    """Las líneas de PRIMER nivel del borrador, como las guarda Nuevo Costeo
    (cod, nombre, unidad, precio por unidad de receta, cantidad, tipo): su
    Σ cantidad × precio es el costo simulado. Lo que se cambió adentro de una
    receta base viaja aparte, en `simulacion.cambios`."""
    lineas = []
    for i, n in enumerate(nodos):
        ruta = str(i)
        cant = float((estado.get(ruta) or {}).get("cant", n["cant"]))
        c = sr.costo_nodo(n, ruta, 1.0, estado, modo)
        lineas.append({
            "cod": n["cod"], "nombre": n["ins"], "unidad": n["unid"],
            "precio": round(c / cant, 6) if cant else 0.0,
            "cantidad": round(cant, 6),
            "tipo": "receta base" if n.get("hijos") else "almacen",
        })
    return lineas


def _limpiar(estado):
    """El borrador tal como llega del navegador, con números de verdad."""
    out = {}
    for ruta, s in (estado or {}).items():
        if not isinstance(s, dict):
            continue
        limpio = {k: float(v) for k, v in s.items()
                  if k in ("cant", "P", "merma", "peso") and v is not None}
        if limpio:
            out[str(ruta)] = limpio
    return out


def simular_plato(cod, nombre, precio, df_rv):
    """El simulador del plato `cod`, adentro de la modal."""
    with st.spinner("Armando la receta con sus precios de compra…"):
        nodos = armar_arbol(df_rv, cod)
    k = f"rec_sim_{cod}"
    avisos = st.session_state.setdefault(_K_AVISO, {})

    def _al_guardar():
        valor = (st.session_state.get(k) or {}).get("guardar") or {}
        if str(valor.get("plato")) != str(cod):
            return
        estado = _limpiar(valor.get("estado"))
        modo = valor.get("modo") if valor.get("modo") in ("hoy", "ult", "p90") else "hoy"
        costo = sr.costo_arbol(nodos, estado, modo)
        extra = {
            "precio_venta": float(valor.get("precio") or 0),
            "simulacion": {
                "plato": cod, "nombre": nombre, "modo": modo,
                "pct_objetivo": float(valor.get("obj") or 0),
                "costo_hoy": round(sr.costo_arbol(nodos), 4),
                "costo": round(costo, 4), "cambios": estado,
                "version": sr.VERSION,
            },
        }
        # Import acá y no arriba: formulario_receta es pesado y sólo hace
        # falta al guardar.
        from formulario_receta import _guardar_propuesta
        ok = _guardar_propuesta("Simulación", f"{nombre} · simulación",
                                str(valor.get("por") or "").strip(),
                                _lineas_propuesta(nodos, estado, modo), extra)
        avisos[cod] = ("Guardada como propuesta: está en Nuevo Costeo › "
                       "Guardadas." if ok else
                       "No se pudo guardar la propuesta: probá de nuevo.")

    data = {
        "plato": {"cod": cod, "nombre": nombre, "precio": float(precio or 0)},
        "nodos": nodos,
        "divisor": divisor_neto(),
        "obj": PCT_OBJETIVO,
        "usuario": _usuario(),
        "aviso": avisos.get(cod, ""),
    }
    _COMPONENTE(key=k, data=data, on_guardar_change=_al_guardar,
                width="stretch")
