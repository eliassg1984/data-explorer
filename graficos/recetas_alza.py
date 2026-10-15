"""
graficos.recetas_alza — Recetas y Costos › «¿Y si sube un insumo?».

Se elige un insumo de COMPRA y cuánto sube (o baja) su precio, y la vista
dice qué platos lo llevan, cuánto pasa a ser su % de costo, a qué precio
habría que venderlos para mantener el % de hoy y cuánto costo de más es al
mes con lo vendido. Pedida el 2026-10-15 sobre el boceto
https://claude.ai/artifact/JFkrxwH2wCipPTGQey1TJ5 («Simular, revisado»,
prototipo 2): el simulador de un plato responde de a un plato, y la pregunta
de todos los días —«el lomo subió 10 %»— toca a varios a la vez.

CUÁNTO LLEVA CADA PLATO DE CADA INSUMO sale de
`simulador_receta.exposicion_carta`: la receta abierta hasta el insumo de
compra, recetas base incluidas, y los cortes porcionados contados para el
insumo del que salen (si el lomo fino sube 10 %, el corte sube 10 %: su
precio es proporcional, regla #647). La suma de cada plato es su costo de
receta (medido el 2026-10-15: 835 platos, mediana 1,000).

El % de costo es el de la Carta costeada —receta y precio de hoy, sobre el
neto (`recetas_comun.divisor_neto`)— y lo vendido es el de sus 90 días
(`carta_costeada.con_ventas`). La exposición va en caché por los sellos de
los tres parquets que la arman (regla #367).

Regla #656.
"""

import pandas as pd
import streamlit as st

import simulador_receta as sr
from data import cargar, sello_datos
from graficos import alturas
from graficos.carta_costeada import (ARCHIVO as ARCHIVO_CARTA, GRUPO_VENTA_INTERNA,
                                     _estilo_pct, con_ventas, preparar)
from graficos.simulador_plato import _precios_compra

PASOS = list(range(-30, 55, 5))
"""Los cambios de precio que se ofrecen, en %."""

_K_INS = "rec_alza_insumo"
_K_PCT = "rec_alza_pct"


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


def _kpi(titulo, valor, pie=""):
    return (f'<div class="rec-alza-kpi"><small>{titulo}</small>'
            f'<b>{valor}</b><span>{pie}</span></div>')


def render_alza(ventas=None):
    """La vista. `ventas`: lo vendido por producto y día, o la función que
    lo carga (`data.venta_por_producto_dia`)."""
    with st.container(border=True, key="rec_card_alza"):
        cab = st.container(horizontal=True, gap="small",
                           vertical_alignment="center", key="rec_alza_cab")
        with cab:
            st.markdown('<p class="chart-card-hdr">¿Y si sube un insumo?</p>',
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
        carta, rango = con_ventas(carta, agg, 90)
        orden, tot = _ranking(expo, carta)
        if not orden:
            st.info("Ningún plato activo con receta y costo.")
            return
        if st.session_state.get(_K_INS) not in orden:
            st.session_state[_K_INS] = orden[0]

        with cab:
            with st.container(key="rec_alza_cab_ins", width="content"):
                insumo = st.selectbox(
                    "Insumo", orden, key=_K_INS, label_visibility="collapsed",
                    width=320, format_func=lambda c: nombres.get(c, c))
            with st.container(key="rec_alza_cab_pct", width="content"):
                pct = st.select_slider(
                    "Cambio de precio", PASOS, value=10, key=_K_PCT,
                    label_visibility="collapsed",
                    format_func=lambda v: f"{v:+d} %")

        t = sr.alza(expo, carta, insumo, pct)
        mes = float(t["DeltaMes"].sum()) if not t.empty else 0.0

        def cruza(u):
            if t.empty:
                return 0
            return int(((t["PctHoy"] <= u) & (t["PctNuevo"] > u)).sum())

        c = compras.get(insumo)
        if c:
            unid = {"kilos": "kg", "litros": "l"}.get(c["unid"], c["unid"])
            precio_txt = f"S/ {c['ult']:,.2f}"
            precio_pie = (f"última compra, {pd.Timestamp(c['fult']):%d/%m/%y}"
                          f" · 90 días S/ {c['p90']:,.2f} por {unid}")
        else:
            precio_txt, precio_pie = "—", "sin compras registradas"
        signo = "+" if mes >= 0 else "−"
        st.markdown(
            '<div class="rec-alza-kpis">'
            + _kpi("Platos que lo llevan", f"{len(t)}",
                   f"{int((t['Vendidos'] > 0).sum()) if not t.empty else 0} vendidos en 90 días")
            + _kpi("Costo de más al mes", f"{signo}S/ {abs(mes):,.0f}",
                   "lo vendido en 90 días ÷ 3")
            + _kpi("Pasan de 30 %", f"{cruza(30)}", "platos")
            + _kpi("Pasan de 35 %", f"{cruza(35)}", "platos")
            + _kpi("Precio de compra", precio_txt, precio_pie)
            + "</div>", unsafe_allow_html=True)

        if t.empty:
            st.info("Ningún plato de la carta lleva este insumo.")
            return
        v = pd.DataFrame({
            "Plato": t["Producto"], "Subgrupo": t["Subgrupo"],
            "Lleva": t["Lleva"], "Del costo": t["Parte"],
            "% costo hoy": t["PctHoy"], "% costo nuevo": t["PctNuevo"],
            "P. venta": t["Precio"], "Para mantener su %": t["PrecioMantener"],
            "Vendidos 90 d": t["Vendidos"], "Δ costo al mes": t["DeltaMes"],
        })
        sty = (v.style
               .format(lambda x: f"S/ {x:,.2f}",
                       subset=["Lleva", "P. venta", "Para mantener su %"])
               .format(lambda x: f"{x:.0f} %", subset=["Del costo"])
               .format(lambda x: f"{x:.1f} %", subset=["% costo hoy", "% costo nuevo"])
               .format(lambda x: f"{x:,.0f}", subset=["Vendidos 90 d"])
               .format(lambda x: f"{'+' if x >= 0 else '−'}S/ {abs(x):,.0f}",
                       subset=["Δ costo al mes"])
               .map(_estilo_pct, subset=["% costo hoy", "% costo nuevo"]))
        st.dataframe(
            sty, hide_index=True, use_container_width=True,
            height=alturas.por_filas(len(v), px_fila=35, extra=38, minimo=0,
                                     rol=alturas.CARTA_COSTEADA),
            column_config={
                "Plato": st.column_config.TextColumn(width=220, pinned=True),
                "Lleva": st.column_config.Column(
                    help="Soles de este insumo por plato: lo que pesa adentro "
                         "de sus recetas base y de los cortes que salen de él"),
                "Del costo": st.column_config.Column(
                    help="Qué parte del costo del plato es este insumo"),
                "Para mantener su %": st.column_config.Column(
                    help="El precio de venta con que el plato queda en su % de "
                         "costo de hoy"),
                "Δ costo al mes": st.column_config.Column(
                    help="Costo de más por mes: lo que sube por plato × lo "
                         "vendido en 90 días ÷ 3"),
            })
        pie = ("% de costo con la receta y el precio de hoy, sobre el neto. "
               "Ámbar sobre 30 %, rojo sobre 35 %.")
        if rango is not None:
            pie += f" Vendidos: del {rango[0]:%d/%m} al {rango[1]:%d/%m/%Y}."
        else:
            pie += " Sin ventas: no hay costo de más al mes."
        st.caption(pie)
