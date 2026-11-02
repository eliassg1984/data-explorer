"""graficos.compras.proveedor - drill de Proveedor.

Desde el 2026-10-23 es una PIEZA PROPIA (regla #715) y desde la #774 una sola
pantalla: `proveedor.js` + `proveedor.css`, con `lista_ficha.js` y `.css`
antepuestos, como Producto:

    [ Proveedores · fecha y filtro (Python) · familias · buscar · Excel    ]
    [ Proveedores | Subieron el precio | Bajaron | Sólo se compran a uno   ]
    [ la lista, con su efecto del precio ][ resumen, o ficha del elegido:  ]
    [                                    ][ Curva | Productos | Documentos ]

Lo que hace la ficha es lo de la regla #646 (y sus anexos #663): la curva con
su ventana, su grano (con «Documento»), su medida y el período en curso rayado
contra los mismos días del anterior; «Total del rango» con los proveedores de
cada producto en 90 días y en todo el histórico; el Desglose de los últimos
seis puntos con su tendencia de trece; los documentos con los días desde la
compra anterior y lo que subió de precio, o agrupados por período. Sólo la
fecha, el filtro de proveedores y las familias vuelven a Python.

Lo que manda Python, partido en dos montajes para que la fecha no vuelva a
mandar el historial:

- `historial_pieza` (`parte: "ficha"`, sin nada que dibujar): cada línea de
  compra del historial de los filtros del reporte, por proveedor, con su
  precio habitual y su marca. Depende sólo del historial: con la misma
  `sello`, Streamlit no vuelve a mandar el mensaje.
- `armar_rank` (`parte: "rank"`, la pantalla): el rango, la selección del
  filtro de proveedores y las familias de la página. El ranking lo arma el
  navegador con las líneas del historial: `d` es `d_full` recortado al rango
  de la tarjeta (`_d_sec` del dispatcher), así que da lo mismo.

El FILTRO de proveedores sigue siendo de Python (`filtro_proveedores`, en la
fila del título): «Detalle de documentos por proveedor» lee su selección.
Ese detalle tiene su propio grano desde la regla #726. El montaje del
ranking le avisa si cambia la selección para que relea el filtro canónico,
incluso cuando la sección de documentos ya estaba dibujada.

UN SOLO PRECIO, el PONDERADO (valor ÷ cantidad), también en el «último
precio» del histórico de un producto, que antes salía de la columna de
precio unitario del parquet (regla #653).
"""

from graficos.movil import css_movil, js_movil
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from graficos.base import preservar_widgets, rango_tarjeta
from graficos.compras._comun import (
    CATEGORIA_SEC, base_normalizada, cambiar_familias, documento_legible,
    filtro_proveedores, selector_fecha_tarjeta, unidad_corta,
)
from graficos.compras._css_proveedor import CSS as CSS_PROVEEDOR
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras.producto import _FLAGS, marcar_revisar
from graficos.compras.semanal import precio_habitual


_KEYS_WIDGET = ("cp_prov_q", "cp_prov_cb::*")
"""Los controles de esta sección, para que la escalada no se los lleve.

La consume `preservar_widgets` en el `st.rerun(scope="app")` de más abajo:
ese rerun aborta la corrida antes de dibujarlos y Streamlit recolecta lo
que no se dibujó, así que sin esta tupla mover la fecha volvía a marcar a
TODOS los proveedores. Ver `graficos/base.py::preservar_widgets` y
`arquitectura.md` regla #373.

Son las del filtro de proveedores (`_comun.py`), que dibuja una checkbox
por razón social — de ahí el prefijo con `*`. Lo demás (grano, ventana,
medida, pestañas, el foco) vive en el navegador desde la regla #715."""


# ── Lo que recibe la pieza ─────────────────────────────────────────────


def _iso(v):
    return None if v is None or pd.isna(v) else f"{pd.Timestamp(v):%Y-%m-%d}"


def normalizar(d, cols):
    """`base_normalizada` con la fecha en DÍAS y sin las filas sin fecha:
    ninguna cae en un rango ni en una ventana."""
    b = base_normalizada(d, *cols)
    b = b.assign(fecha=pd.to_datetime(b["fecha"], errors="coerce").dt.normalize())
    return b[b["fecha"].notna()].reset_index(drop=True)


def sello_historial(hist):
    """La identidad del historial que recibe la pieza: cambia si cambia una
    línea (otro parquet, otros filtros de familia). Las dos tarjetas la
    llevan y el navegador sólo junta datos con la MISMA."""
    if hist.empty:
        return "0"
    _h = pd.util.hash_pandas_object(
        hist[["prov", "prod", "fecha", "valor", "cant", "docu"]], index=False)
    return f"{len(hist)}-{int(_h.sum()) & 0xFFFFFFFFFFFF:x}"


def historial_pieza(hist, sello):
    """Lo que recibe la tarjeta de la FICHA. Pura.

    Fila de una línea (en `lineas[i]`, las del proveedor `provs[i]`, de la
    más vieja a la más nueva): [día (desde `base`), producto (índice de
    `prods`), documento (índice de `docs`), cantidad, valor, precio
    habitual o None, unidad (índice de `ums`), marca (índice de `_FLAGS`)].

    El precio habitual es el de «Compras por período»
    (`semanal.precio_habitual`: la mediana del precio unitario de los 90
    días anteriores, de TODOS los proveedores, sin contar el mismo día).
    Mira sólo hacia atrás, así que sobre el historial entero da lo mismo
    que la cuenta de antes sobre el rango con sus 90 días (regla #646). La
    marca es la de Producto (`marcar_revisar`): esas líneas no entran en
    ningún precio, para que acá se lea lo mismo que en Precios (regla #774).

    `docs` va ORDENADA por el texto del parquet: el orden de los índices es
    el de los documentos, que es lo que desempata dos del mismo día."""
    h = hist.reset_index(drop=True)
    ref = precio_habitual(h["prod"], h["fecha"], h["valor"], h["cant"])
    flag = marcar_revisar(h["cant"], h["valor"], ref, h["um"])
    provs = sorted(h["prov"].unique())
    prods = sorted(h["prod"].unique())
    docs = sorted(h["docu"].astype(str).str.strip().unique())
    ums = sorted(h["um"].astype(str).str.strip().unique())
    base = h["fecha"].min() if len(h) else pd.Timestamp("2000-01-01")
    x = h.assign(
        _p=pd.Categorical(h["prov"], categories=provs).codes,
        _i=pd.Categorical(h["prod"], categories=prods).codes,
        _d=pd.Categorical(h["docu"].astype(str).str.strip(), categories=docs).codes,
        _u=pd.Categorical(h["um"].astype(str).str.strip(), categories=ums).codes,
        _r=np.round(ref.to_numpy(dtype=float), 4),
        _f=pd.Categorical(flag, categories=_FLAGS).codes,
    ).sort_values(["_p", "fecha", "_d"], kind="stable")
    filas = [[int(d), int(i), int(dc), c, v, (None if r != r else r), int(u), int(f)]
             for d, i, dc, c, v, r, u, f in zip(
                 (x["fecha"] - base).dt.days.tolist(), x["_i"].tolist(),
                 x["_d"].tolist(), np.round(x["cant"], 3).tolist(),
                 np.round(x["valor"], 2).tolist(), x["_r"].tolist(),
                 x["_u"].tolist(), x["_f"].tolist())]
    cortes = np.cumsum(np.bincount(x["_p"].to_numpy(), minlength=len(provs)))
    lineas = [filas[a:b] for a, b in zip(np.r_[0, cortes[:-1]], cortes)]
    _vacio = ("", "nan", "None")
    _con = [s for s in docs if s not in _vacio]
    _leg = dict(zip(_con, documento_legible(pd.Series(_con, dtype=object))
                    if _con else []))
    return {
        "parte": "ficha", "sello": sello, "base": _iso(base),
        "ultimo": _iso(h["fecha"].max()) if len(h) else _iso(base),
        "provs": provs, "noms": [nombre_propio(p) for p in provs],
        "prods": prods,
        "docs": [str(_leg.get(s, "")) for s in docs],
        "ums": ["" if u in _vacio else unidad_corta(u) for u in ums],
        "lineas": lineas,
    }


def armar_rank(rango, seleccion, sello, familias=None):
    """Lo que recibe el montaje de la pantalla. Pura.

    `seleccion` es la del filtro de proveedores (`filtro_proveedores`): los
    nombres marcados, con «Otros» si está marcado. El navegador aplica la
    regla de antes: si ninguno de los marcados compró en el rango, van
    todos; «Otros» junta a los que quedaron fuera. `familias` es lo de
    `_comun.familias_de_tarjeta`, para «Familias: 5 de 8» y «Fuera de esta
    cuenta»."""
    p = {
        "parte": "rank", "sello": sello,
        "rango": [_iso(rango[0]), _iso(rango[1])],
        "sel": [p for p in seleccion if p != "Otros"],
        "otros": "Otros" in seleccion,
    }
    if familias:
        p["pagina"] = {"todas": [[f, nombre_propio(f), v] for f, v in familias["todas"]],
                       "elegidas": list(familias["elegidas"])}
    return p


# ── La pieza propia (regla #715) ───────────────────────────────────────
_AQUI = Path(__file__).parent
# El montaje del ranking avisa a Detalle docs. si cambia el filtro nativo
# de proveedores; esa pieza pide actualizar sólo su propio fragment (#726).
_PIEZA = st.components.v2.component(
    "compras_proveedor",
    css=css_movil((_AQUI / "lista_ficha.css").read_text(encoding="utf-8")
                  + (_AQUI / "proveedor.css").read_text(encoding="utf-8")),
    # El Excel (`libro`, `bajar`, `archivo`) vive en `_xlsx.js`, compartido
    # con Producto, Costo de Carta y Consistencia: se antepone. `lista_ficha.js`
    # es lo que comparte con la pantalla de Producto.
    js=js_movil((_AQUI.parent / "_xlsx.js").read_text(encoding="utf-8")
    + (_AQUI / "lista_ficha.js").read_text(encoding="utf-8")
    + (_AQUI / "proveedor.js").read_text(encoding="utf-8")),
)

_CSS_BOTONES = """
    .st-key-cp_rank_escala.st-key-cp_rank_escala button,
    .st-key-cp_prov_pop_float.st-key-cp_prov_pop_float [data-testid="stPopover"] button {
        min-height: 30px !important; height: 30px !important; border: 0 !important; border-radius: 8px !important;
        background: var(--rail-fondo) !important; box-shadow: none !important; padding: 0 10px !important;
    }
    .st-key-cp_rank_escala.st-key-cp_rank_escala button:hover,
    .st-key-cp_prov_pop_float.st-key-cp_prov_pop_float [data-testid="stPopover"] button:hover { background: var(--bg-hover) !important; }
    .st-key-cp_rank_escala.st-key-cp_rank_escala button p,
    .st-key-cp_prov_pop_float.st-key-cp_prov_pop_float [data-testid="stPopover"] button p { font-size: 12.5px !important; color: var(--text-primary) !important; }
"""
"""Los dos botones de Python de la cabecera, con la forma de los de la pieza."""

_K_RANK = "cp_prov_pieza_rank"
_K_FICHA = "cp_prov_pieza_ficha"
_K_HIST = "_cp_prov_hist"
"""El mensaje de la ficha de la última corrida, con su `sello`: el precio
habitual sobre el historial entero son ~0,5 s, y sólo cambia con el parquet
o los filtros de familia, no con la fecha ni con el filtro de proveedores."""


def _historial(hist):
    sello = sello_historial(hist)
    _g = st.session_state.get(_K_HIST)
    if _g is None or _g[0] != sello:
        _g = (sello, historial_pieza(hist, sello))
        st.session_state[_K_HIST] = _g
    return _g


# ── El drill ───────────────────────────────────────────────────────────


@st.fragment
def _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                             col_punit, col_um, col_fecha, col_docu=None,
                             d_full=None, familias=None):
    """Dashboard de Proveedor: una pantalla, con la lista y la ficha del
    proveedor elegido. Ver el docstring del módulo y `arquitectura.md` reglas
    #646, #715 y #774.

    La firma es la de antes, con `col_punit` sin usar (el precio sale de
    valor ÷ cantidad): en Cloud un commit que le cambia la firma a algo ya
    importado deja el `app.py` nuevo hablando con el paquete viejo (regla
    #357)."""
    # La escalada del selector de fecha: el filtro que lee el rango vive en
    # app.py, FUERA de este fragment (regla #180), con `preservar_widgets`
    # porque el rerun aborta acá (#373).
    if st.session_state.pop("_cp_rank_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")
    if not (col_prov and col_valor):
        st.info("Faltan columnas (Proveedor, Valor) para este gráfico.")
        return
    cols = (col_prov, col_prod, col_cant, col_valor, col_punit, col_um,
            col_fecha, col_docu)
    b_rng = normalizar(d, cols)
    st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)
    if b_rng.empty or b_rng["valor"].sum() == 0:
        # SIN FILAS SE VACÍA EL CONTENIDO, NO LA VISTA (regla #354): la
        # tarjeta se dibuja con su selector de fecha, que es la salida.
        with st.container(border=True, key="compras_prov_card_vacio"):
            selector_fecha_tarjeta(
                "cp_rank", "_cp_rank_atajo_pendiente",
                titulo_html='<div class="cp-rank-tit">Ranking de '
                            'proveedores</div>',
                categoria=CATEGORIA_SEC["compras_sec_proveedor"])
            st.info("Sin compras en el rango seleccionado. Ampliá el rango "
                    "desde la fecha de la cabecera, o soltá el filtro de "
                    "Familia. «Vs año pasado» y «Volatilidad», más abajo, "
                    "tienen ventana propia y siguen mostrando datos.")
        return

    # El filtro de proveedores: todos los del rango, del que más se le
    # compró al que menos, y «Otros» si son más de 20 (regla de antes).
    _orden = (b_rng.groupby("prov")["valor"].sum()
              .sort_values(ascending=False, kind="stable").index.tolist())
    if len(_orden) > 20:
        _orden = _orden + ["Otros"]
    seleccion, _pop_proveedores = filtro_proveedores("cp_prov", _orden)

    hist = normalizar(d_full, cols) if d_full is not None else b_rng
    sello, payload_ficha = _historial(hist)
    _rango = rango_tarjeta(CATEGORIA_SEC["compras_sec_proveedor"])
    if _rango is None or any(x is None for x in _rango):
        _rango = (b_rng["fecha"].min(), b_rng["fecha"].max())
    rank = armar_rank((pd.Timestamp(_rango[0]).normalize(),
                       pd.Timestamp(_rango[1]).normalize()), seleccion, sello,
                      familias)

    # La fecha y el filtro son widgets de Python, parados en el hueco que la pieza
    # les deja en su cabecera (`lfPasarFecha`). El montaje del historial no dibuja.
    st.markdown("""<style>
    .st-key-cp_prov_nativa { position: relative; gap: 0 !important; }
    .st-key-cp_prov_nativa_fecha { position: absolute; left: 18px; top: 44px; z-index: 5; width: auto !important; }
    .st-key-cp_prov_nativa > [data-testid="stElementContainer"] { margin: 0 !important; }
    .st-key-cp_prov_nativa_fecha .st-key-cp_rank_fila { gap: 8px !important; align-items: center; flex-wrap: nowrap; }
    .st-key-cp_prov_pieza_ficha { position: absolute !important; width: 0 !important; height: 0 !important; overflow: hidden; }
    """ + _CSS_BOTONES + "</style>", unsafe_allow_html=True)
    with st.container(key="cp_prov_nativa"):
        with st.container(key="cp_prov_nativa_fecha"):
            selector_fecha_tarjeta(
                "cp_rank", "_cp_rank_atajo_pendiente",
                extra=_pop_proveedores,
                categoria=CATEGORIA_SEC["compras_sec_proveedor"])
        _PIEZA(key=_K_FICHA, data=payload_ficha, width="stretch")
        _PIEZA(key=_K_RANK, data=rank, width="stretch",
               on_familias_change=lambda: cambiar_familias(
                   _K_RANK, "_cp_rank_atajo_pendiente", familias))
