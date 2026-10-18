"""Alza Insumo: varios precios y su efecto sobre un período de ventas.

La exposición incluye recetas base y cortes (reglas #647, #656). La fecha
usa el panel compartido, con rango propio; no se extrapolan 90 días a mes.
El precio absoluto se compara con el promedio vigente del almacén, en su
unidad kardex; si falta, se identifica el respaldo de última compra.
"""

from html import escape

import pandas as pd
import streamlit as st

import simulador_receta as sr
from data import cargar, sello_datos
from graficos import alturas
from graficos.base import rango_tarjeta, selector_fecha_tarjeta
from graficos.carta_costeada import (ARCHIVO as ARCHIVO_CARTA, GRUPO_VENTA_INTERNA,
                                     _estilo_pct, con_ventas, preparar,
                                     ctx_fecha as ctx_fecha_carta)
from graficos.recetas_comun import catalogo_insumos
from graficos.simulador_plato import _precios_compra

CATEGORIA_FECHA = "alza"
_K_INS = "rec_alza_insumos"


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
    return (f'<div class="rec-alza-kpi"><small>{escape(titulo)}</small>'
            f'<b>{escape(valor)}</b><span>{escape(pie)}</span></div>')


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


def _sincronizar_precio(cod, base, desde):
    """Ambas entradas representan el mismo cambio; callback antes del rerun."""
    kp, kv = f"rec_alza_pct_{cod}", f"rec_alza_valor_{cod}"
    if desde == "pct":
        st.session_state[kv] = base * (1 + st.session_state[kp] / 100)
    else:
        st.session_state[kp] = (st.session_state[kv] / base - 1) * 100


def _editar_precios(insumos, nombres, referencias):
    cambios = {}
    with st.expander("Precios del escenario", expanded=True):
        for cod in insumos:
            ref = referencias.get(cod)
            base, unidad, fuente = ref or (0.0, "", "sin precio de referencia")
            kp, kv = f"rec_alza_pct_{cod}", f"rec_alza_valor_{cod}"
            st.session_state.setdefault(kp, 10.0 if len(insumos) == 1 else 0.0)
            # Si se actualiza el dato, el valor sigue representando el mismo %.
            if st.session_state.get(f"rec_alza_base_{cod}") != base or kv not in st.session_state:
                st.session_state[kv] = base * (1 + st.session_state[kp] / 100)
                st.session_state[f"rec_alza_base_{cod}"] = base
            cols = st.columns([2.5, 1, 1.3], vertical_alignment="center")
            with cols[0]:
                st.markdown(f"**{escape(nombres.get(cod, cod))}**")
                st.caption(f"Base: S/ {base:,.4f} / {unidad} · {fuente}" if ref else fuente)
            with cols[1]:
                cambios[cod] = st.number_input(
                    "Cambio %", min_value=-100.0, step=1.0, format="%.2f",
                    key=kp, on_change=_sincronizar_precio if ref else None,
                    args=(cod, base, "pct") if ref else (),
                    help="Admite alzas y bajas; −100 % lleva el precio a cero.")
            with cols[2]:
                st.number_input(
                    f"Nuevo precio S/ / {unidad}" if ref else "Nuevo precio S/",
                    min_value=0.0, step=0.10, format="%.4f", key=kv,
                    disabled=not ref, on_change=_sincronizar_precio if ref else None,
                    args=(cod, base, "valor") if ref else ())
        st.caption("Edita el porcentaje o el nuevo precio por unidad; ambos se actualizan juntos. "
                   "El cambio se aplica proporcionalmente al costo actual de las recetas.")
    return cambios


def _soles(v, signo=False):
    prefijo = ("+" if v >= 0 else "−") if signo else ("−" if v < 0 else "")
    return f"{prefijo}S/ {abs(v):,.2f}"


def render_alza(ventas=None):
    """La vista. `ventas`: lo vendido por producto y día, o la función que
    lo carga (`data.venta_por_producto_dia`)."""
    with st.container(border=True, key="rec_card_alza"):
        cab = st.container(horizontal=True, gap="small",
                           vertical_alignment="center", key="rec_alza_cab")
        with cab:
            st.markdown('<p class="chart-card-hdr">¿Y si cambian los insumos?</p>',
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
        # Orden estable al cambiar de fecha: no mueve las opciones del selector.
        ranking, _ = con_ventas(carta, agg, 90)
        orden, _ = _ranking(expo, ranking)
        if not orden:
            st.info("Ningún plato activo con receta y costo.")
            return
        if _K_INS not in st.session_state:
            anterior = st.session_state.get("rec_alza_insumo")
            st.session_state[_K_INS] = [anterior if anterior in orden else orden[0]]
        st.session_state[_K_INS] = [c for c in st.session_state[_K_INS] if c in orden]
        insumos = st.multiselect(
            "Insumos a evaluar", orden, key=_K_INS,
            format_func=lambda c: nombres.get(c, c),
            placeholder="Elige uno o varios insumos")
        if not insumos:
            st.info("Elige uno o varios insumos para simular sus precios juntos.")
            return
        cambios = _editar_precios(insumos, nombres, _referencias(catalogo_insumos(), compras))
        t = sr.alzas(expo, carta, cambios)
        resumen = sr.resumen_alzas(carta, t)
        periodo = (f"{rango[0]:%d/%m/%Y} – {rango[1]:%d/%m/%Y}"
                   if rango is not None else "sin ventas disponibles")

        def cruza(u):
            if t.empty:
                return 0
            return int(((t["PctHoy"] <= u) & (t["PctNuevo"] > u)).sum())

        st.markdown(
            '<div class="rec-alza-kpis">'
            + _kpi("Platos afectados", f"{len(t)}",
                   f"{int((t['Vendidos'] > 0).sum())} con ventas en el período")
            + _kpi("Cambio de costo del período", _soles(resumen["delta"], signo=True),
                   periodo if rango is not None else "—")
            + _kpi("Cambio de margen del período", _soles(-resumen["delta"], signo=True),
                   "mismas ventas y precios de venta")
            + _kpi("Superan 30 % / 35 %", f"{cruza(30)} / {cruza(35)}",
                   "platos que cruzan cada umbral")
            + _kpi("Venta neta evaluada", _soles(resumen["neto"]),
                   "carta activa con costo y precio")
            + "</div>", unsafe_allow_html=True)

        st.dataframe(pd.DataFrame({
            "Concepto": ["Costo de recetas", "Margen sobre recetas"],
            "Actual": [resumen["costo"], resumen["margen"]],
            "Simulado": [resumen["costo_nuevo"], resumen["margen_nuevo"]],
            "Cambio": [resumen["delta"], -resumen["delta"]],
        }).style.format(_soles, subset=["Actual", "Simulado"])
          .format(lambda v: _soles(v, signo=True), subset=["Cambio"]),
          hide_index=True, width="stretch")
        st.caption(f"Período de ventas: {periodo}. Usa el calendario para elegir días, semanas o meses. "
                   "Costo = unidades vendidas × receta actual. Margen = venta neta real − costo de recetas; "
                   "no descuenta personal, alquiler ni otros gastos. Incluye la carta activa con costo y precio, "
                   "sin venta interna.")
        if rango is None:
            st.info("Sin ventas disponibles: se calcula el efecto por plato, pero el impacto del período es cero.")
        elif not carta["Vendidos"].any() and not carta["VendidoNeto"].any():
            st.info("No hay ventas de la carta evaluada en el período elegido; el impacto del período es cero.")

        if t.empty:
            st.info("Ningún plato de la carta lleva los insumos elegidos.")
            return
        v = pd.DataFrame({
            "Plato": t["Producto"], "Subgrupo": t["Subgrupo"],
            "Insumos por plato": t["Lleva"], "Del costo": t["Parte"],
            "Costo hoy": t["Costo"], "Costo nuevo": t["CostoNuevo"],
            "Δ por plato": t["DeltaUnitario"],
            "% costo hoy": t["PctHoy"], "% costo nuevo": t["PctNuevo"],
            "P. venta": t["Precio"], "Para mantener su %": t["PrecioMantener"],
            "Vendidos período": t["Vendidos"], "Δ costo período": t["DeltaPeriodo"],
            "Margen nuevo período": t["MargenNuevoPeriodo"],
        })
        sty = (v.style
               .format(lambda x: f"S/ {x:,.2f}",
                       subset=["Insumos por plato", "Costo hoy", "Costo nuevo", "P. venta",
                               "Para mantener su %", "Margen nuevo período"])
               .format(lambda x: f"{x:.0f} %", subset=["Del costo"])
               .format(lambda x: f"{x:.1f} %", subset=["% costo hoy", "% costo nuevo"])
               .format(lambda x: f"{x:,.2f}", subset=["Vendidos período"])
               .format(lambda x: _soles(x, signo=True),
                       subset=["Δ por plato", "Δ costo período"])
               .map(_estilo_pct, subset=["% costo hoy", "% costo nuevo"]))
        st.dataframe(
            sty, hide_index=True, width="stretch",
            height=alturas.por_filas(len(v), px_fila=35, extra=38, minimo=0,
                                     rol=alturas.CARTA_COSTEADA),
            column_config={
                "Plato": st.column_config.TextColumn(width=220, pinned=True),
                "Insumos por plato": st.column_config.Column(
                    help="Soles de los insumos elegidos por plato: lo que pesan adentro "
                         "de sus recetas base y de los cortes que salen de él"),
                "Del costo": st.column_config.Column(
                    help="Qué parte del costo del plato son los insumos elegidos"),
                "Para mantener su %": st.column_config.Column(
                    help="El precio de venta con que el plato queda en su % de "
                         "costo de hoy"),
                "Δ costo período": st.column_config.Column(
                    help="Suma de los cambios por plato × unidades vendidas en las fechas elegidas"),
            })
        pie = ("% de costo con la receta y el precio de hoy, sobre el neto. "
               "Ámbar sobre 30 %, rojo sobre 35 %.")
        if rango is not None:
            pie += f" Vendidos: del {rango[0]:%d/%m} al {rango[1]:%d/%m/%Y}."
        st.caption(pie)
