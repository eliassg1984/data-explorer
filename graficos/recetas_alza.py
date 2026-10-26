"""Recetas › «Simular Alza de Insumos»: varios precios de compra y su efecto
en la carta y en un período de ventas.

La exposición incluye recetas base y cortes (reglas #647, #656). La fecha
usa el panel compartido, con rango propio; no se extrapolan 90 días a mes.
El precio absoluto se compara con el promedio vigente del almacén, en su
unidad kardex; si falta, se identifica el respaldo de última compra.

PIEZA PROPIA DESDE EL 2026-10-22 (regla #695), sobre un boceto aprobado
(https://claude.ai/artifact/9Cyr741W82XtckkUzZheCJ): hasta ese día era una
fila de `st.number_input` por insumo, siete `st.info` y dos `st.dataframe`,
y se veía «de fábrica» al lado de «Consistencia de datos». Ahora el
escenario, los indicadores, la lista de platos y la ficha del elegido son
`recetas_alza.js` + `.css` (`st.components.v2`, como Consistencia). Python
manda la exposición de TODOS los insumos y lo vendido del período; el
navegador hace la cuenta mientras se escribe, con las fórmulas de
`simulador_receta.alzas` (las vigila `test_recetas_alza.py`), y guarda el
escenario en su raíz y en `localStorage`: nada vuelve a Python, así que
cambiar un % no pide una corrida, y cambiar la fecha conserva el escenario.
"""

from graficos.movil import css_movil, js_movil
from pathlib import Path

import pandas as pd
import streamlit as st

import simulador_receta as sr
from data import cargar, sello_datos
from graficos.base import rango_tarjeta, selector_fecha_tarjeta
from graficos.carta_costeada import (ARCHIVO as ARCHIVO_CARTA, GRUPO_VENTA_INTERNA,
                                     con_ventas, preparar,
                                     ctx_fecha as ctx_fecha_carta)
from graficos.recetas_comun import catalogo_insumos
from graficos.simulador_plato import _precios_compra

CATEGORIA_FECHA = "alza"
TITULO = "Simular Alza de Insumos"

_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "recetas_alza",
    css=css_movil((_AQUI / "recetas_alza.css").read_text(encoding="utf-8")),
    js=js_movil((_AQUI / "recetas_alza.js").read_text(encoding="utf-8")),
)

AYUDA = ("Costo = unidades vendidas en las fechas elegidas × receta de hoy, "
         "abierta hasta el insumo de compra (recetas base y cortes "
         "porcionados). Margen = venta neta real − costo de recetas: no "
         "descuenta personal, alquiler ni otros gastos. Carta activa con costo "
         "y precio, sin venta interna. El cambio se aplica en proporción al "
         "costo actual de cada insumo en las recetas.")


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def _exposicion(sello_rv, sello_rb, sello_po, version=sr.VERSION):
    """{plato: {insumo de compra: soles}} y {insumo: nombre}."""
    df_rv = cargar("recetaventa.parquet")
    df_rb = cargar("recetabase.parquet")
    df_po = cargar("porcionamientos.parquet")
    expo = sr.exposicion_carta(df_rv, df_rb, df_po)
    nombres = {}
    for df, c_cod, c_nom in ((df_rb, "COD INS RB", "INSUMO"),
                             (df_rv, "COD INS", "INS RV"),
                             (df_po, "COD PROD INIC", "PROD INICIAL")):
        if df is not None and c_cod in df.columns and c_nom in df.columns:
            for cod, nom in zip(df[c_cod].astype(str).str.strip(),
                                df[c_nom].astype(str).str.strip()):
                nombres.setdefault(cod, nom)
    return expo, nombres


def _ranking(expo, carta):
    """Los insumos, de los que más costo cargan a los que menos: Σ lo que
    lleva cada plato × lo vendido en 90 días (o × 1 si no hay ventas)."""
    vend = dict(zip(carta["Cod"].astype(str), carta.get("Vendidos", pd.Series(dtype=float))))
    tot = {}
    for plato, e in expo.items():
        if plato not in vend:
            continue
        peso = max(float(vend.get(plato) or 0.0), 0.0) or 0.01
        for ins, soles in e.items():
            tot[ins] = tot.get(ins, 0.0) + soles * peso
    return sorted(tot, key=lambda c: -tot[c]), tot


def ctx_fecha(agg, hoy=None):
    """Mismos límites de ventas que Costo Carta, con su propio rango."""
    ctx = ctx_fecha_carta(agg, hoy=hoy)
    if ctx is not None:
        from estado_rango import clave_rango
        ctx["k_rango"] = clave_rango("Recetas", False, CATEGORIA_FECHA)
        ctx["rango_default_cat"] = {CATEGORIA_FECHA: ctx["rango_default"]}
    return ctx


def _referencias(catalogo, compras):
    """Precio por unidad de almacén; sin referencia sólo se edita el %."""
    refs = {}
    if catalogo is not None:
        for r in catalogo.itertuples(index=False):
            if pd.notna(r.precio_kardex) and r.precio_kardex > 0:
                refs[str(r.cod).strip()] = (float(r.precio_kardex),
                                          r.unidad_kardex, "promedio de almacén")
    for cod, c in compras.items():
        if pd.notna(c["ult"]) and c["ult"] > 0:
            refs.setdefault(cod, (c["ult"], c["unid"], "última compra"))
    return refs


_UNIDAD_CORTA = {"KILOS": "kg", "KILO": "kg", "KG": "kg", "LITROS": "l",
                 "LITRO": "l", "UND": "und", "UNIDAD": "und", "UNIDADES": "und"}


def _unidad(u):
    u = str(u or "").strip()
    return _UNIDAD_CORTA.get(u.upper(), u.lower())


def _f(v):
    """Un float para el JSON (NaN no es JSON)."""
    v = float(v) if pd.notna(v) else 0.0
    return round(v, 4)


def armar(expo, nombres, carta, orden, tot, refs, rango):
    """Lo que recibe la pieza. Pura: la lee el test.

    - `insumos`: [cod, nombre, precio base, unidad, fuente, peso 90 días,
      nº de platos], en el orden del ranking (el de «Agregar insumo»).
    - `platos`: [cod, plato, subgrupo, precio, neto, costo, vendidos,
      neto vendido, {índice de insumo: soles}] — los que llevan alguno de
      esos insumos, con las mismas exclusiones que `sr.alzas` (sin neto, sin
      exposición). El costo, como allá: el de la carta, o la suma de la
      exposición si no tiene.
    - `neto` y `costo`: los de TODA la carta evaluada en el período, como
      `sr.resumen_alzas` — incluye los platos que ningún insumo toca.
    """
    idx = {c: i for i, c in enumerate(orden)}
    usados = {}
    platos = []
    for r in carta.itertuples(index=False):
        e = expo.get(str(r.Cod).strip(), {})
        lleva = {idx[c]: round(float(s), 4) for c, s in e.items()
                 if c in idx and s and s > 0}
        if not lleva or not pd.notna(r.Neto) or r.Neto <= 0:
            continue
        costo = float(r.Costo) if pd.notna(r.Costo) and r.Costo > 0 else sum(e.values())
        for i in lleva:
            usados[i] = usados.get(i, 0) + 1
        platos.append([str(r.Cod), str(r.Producto), str(r.Subgrupo or ""),
                       _f(r.Precio), _f(r.Neto), _f(costo),
                       _f(getattr(r, "Vendidos", 0.0)), _f(getattr(r, "VendidoNeto", 0.0)),
                       {str(i): s for i, s in lleva.items()}])
    insumos = []
    for i, c in enumerate(orden):
        base, unidad, fuente = refs.get(c, (None, "", "sin precio de referencia"))
        insumos.append([c, nombres.get(c, c), _f(base) if base else None,
                        _unidad(unidad), fuente, round(tot.get(c, 0.0)), usados.get(i, 0)])
    hay = rango is not None
    return {
        "insumos": insumos, "platos": platos,
        "neto": _f(carta["VendidoNeto"].sum()) if hay and "VendidoNeto" in carta else 0.0,
        "costo": _f((carta["Costo"] * carta["Vendidos"]).sum()) if hay and "Vendidos" in carta else 0.0,
        "periodo": f"{rango[0]:%d/%m/%Y} – {rango[1]:%d/%m/%Y}" if hay else "",
        "ayuda": AYUDA,
    }


def render_alza(ventas=None):
    """La vista. `ventas`: lo vendido por producto y día, o la función que
    lo carga (`data.venta_por_producto_dia`)."""
    with st.container(border=True, key="rec_card_alza"):
        cab = st.container(horizontal=True, gap="small",
                           vertical_alignment="center", key="rec_alza_cab")
        with cab:
            st.markdown(f'<p class="chart-card-hdr">{TITULO}</p>',
                        unsafe_allow_html=True)
        df_carta = cargar(ARCHIVO_CARTA)
        if df_carta is None or df_carta.empty:
            st.info("Todavía no hay datos de la carta costeada "
                    f"({ARCHIVO_CARTA}).")
            return
        with st.spinner("Abriendo las recetas hasta el insumo de compra…"):
            expo, nombres = _exposicion(sello_datos("recetaventa.parquet"),
                                        sello_datos("recetabase.parquet"),
                                        sello_datos("porcionamientos.parquet"))
            compras = _precios_compra(sello_datos("compras.parquet"))
        if not expo:
            st.info("No se pudieron abrir las recetas (recetaventa.parquet).")
            return
        carta, _ = preparar(df_carta)
        carta = carta[(carta["Grupo"].str.casefold() != GRUPO_VENTA_INTERNA.casefold())
                      & ~carta["SinCosto"]]
        agg = None
        if ventas is not None:
            with st.spinner("Cargando lo vendido… la primera vez del día tarda"):
                agg = ventas() if callable(ventas) else ventas
        ctx = ctx_fecha(agg)
        if ctx is not None:
            with cab:
                with st.container(key="rec_alza_cab_fecha", width="content"):
                    selector_fecha_tarjeta("rec_alza_f", None,
                                           categoria=CATEGORIA_FECHA, ctx=ctx)
        rango = rango_tarjeta(CATEGORIA_FECHA, ctx) if ctx is not None else None
        carta, rango = con_ventas(carta, agg, rango=rango)
        # Orden estable al cambiar de fecha: no mueve la lista de «Agregar».
        ranking, _ = con_ventas(carta, agg, 90)
        orden, tot = _ranking(expo, ranking)
        if not orden:
            st.info("Ningún plato activo con receta y costo.")
            return
        data = armar(expo, nombres, carta, orden, tot,
                     _referencias(catalogo_insumos(), compras), rango)
        _PIEZA(key="rec_alza_pieza", data=data, width="stretch")
