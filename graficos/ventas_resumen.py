"""
graficos.ventas_resumen — vista "Resumen ejecutivo" del dashboard de Ventas:
KPIs del rango + venta total por día (barras coloreadas por tendencia
día-a-día) + volumen de Pax, ticket promedio diario y top platos.

Nació como un candlestick (mockup tipo "panel bursátil" para restaurantes)
con apertura/cierre = primera/última línea de venta del día — se reemplazó
por barras el 2026-08-11 porque esa apertura/cierre comparaba dos ventas
básicamente al azar (sin relación real entre sí, a diferencia de un precio
de acción) y el color resultante no tenía señal. Ver arquitectura.md
regla #85 para el detalle de por qué se dio de baja.

El detalle profundo por producto (FoodCost, sparklines, %Var vs Año Pasado)
sigue viviendo en "Ranking & FoodCost" — este panel es la foto rápida de un
vistazo, no su reemplazo.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from tema import ACENTO, ERROR, EXITO, GRIS_BORDE
from graficos.base import _card, _compras_layout, _compras_truncar
from graficos import alturas

MIN_DIAS = 5     # con menos, la tendencia día-a-día no dice nada
MAX_DIAS = 30    # tope de barras legibles. Mismo espíritu que MAX_SEMANAS de
                 # compras/volatilidad.py (arquitectura.md regla #74): el
                 # filtro de fecha de la franja es un TECHO, no la ventana en
                 # sí — con un rango de "todo el año" cargado, esta vista
                 # sigue mostrando solo los últimos 30 días CON datos.


@st.fragment
def _ventas_resumen(d, col_venta, col_fecha, col_pax, col_pedido, col_prod, col_cant):
    """"Resumen ejecutivo": KPIs + venta diaria + volumen + ticket promedio +
    top platos, todas las piezas sobre la MISMA ventana de días (últimos
    `MAX_DIAS` con datos) para que cuenten la misma historia.
    """
    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el resumen ejecutivo.")
        return

    fecha = pd.to_datetime(d[col_fecha], errors="coerce")
    venta = pd.to_numeric(d[col_venta], errors="coerce")
    dia = fecha.dt.normalize()

    cols = {"dia": dia, "fecha": fecha, "venta": venta}
    if col_prod:
        cols["prod"] = d[col_prod].astype(str)
    if col_cant:
        cols["cant"] = pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
    if col_pax:
        cols["pax"] = pd.to_numeric(d[col_pax], errors="coerce")
    if col_pedido:
        cols["ped"] = d[col_pedido].astype(str)
    tabla_full = pd.DataFrame(cols).dropna(subset=["dia", "venta"])
    if tabla_full.empty:
        st.info("Sin datos en el rango cargado.")
        return

    dias_disponibles = sorted(tabla_full["dia"].unique())
    if len(dias_disponibles) < MIN_DIAS:
        st.info(f"Necesitás al menos {MIN_DIAS} días con ventas en el rango "
                "cargado para el resumen ejecutivo.")
        return
    dias = dias_disponibles[-MAX_DIAS:]
    tabla = tabla_full[tabla_full["dia"].isin(dias)].sort_values("fecha")

    # ── Total de venta por día ────────────────────────────────────────────
    g = (tabla.groupby("dia", as_index=False)["venta"].sum()
         .rename(columns={"venta": "total"})
         .sort_values("dia").reset_index(drop=True))
    if g.empty:
        st.info("Sin datos en el rango cargado.")
        return

    # ── Volumen: Pax/día (dedup por pedido, mismo criterio que
    # ventas.py::_ventas_grafico_dia) o, sin Pax, pedidos distintos/día ────
    vol_label = None
    if col_pax:
        if col_pedido:
            vol = (tabla.groupby(["dia", "ped"], as_index=False)["pax"].max()
                   .groupby("dia", as_index=False)["pax"].sum())
        else:
            vol = tabla.groupby("dia", as_index=False)["pax"].sum()
        g = g.merge(vol, on="dia", how="left")
        g["pax"] = g["pax"].fillna(0)
        vol_label = "Clientes"
    elif col_pedido:
        vol = (tabla.groupby("dia", as_index=False)["ped"].nunique()
               .rename(columns={"ped": "pax"}))
        g = g.merge(vol, on="dia", how="left")
        g["pax"] = g["pax"].fillna(0)
        vol_label = "Pedidos"

    if vol_label:
        g["ticket"] = g["total"] / g["pax"].replace(0, np.nan)

    # ── KPIs ──────────────────────────────────────────────────────────────
    total_venta = float(tabla["venta"].sum())
    total_pax = float(g["pax"].sum()) if vol_label else None
    ticket_prom = (total_venta / total_pax) if total_pax else None
    idx_mejor = g["total"].idxmax()
    mejor_dia, mejor_valor = g.loc[idx_mejor, "dia"], g.loc[idx_mejor, "total"]
    alzas = int((g["total"].diff() >= 0).sum())  # NaN del primer día no cuenta

    _nota_recorte = ("" if len(dias_disponibles) <= MAX_DIAS else
                     f" Recortado a los últimos {MAX_DIAS} días con ventas "
                     "del rango cargado.")

    # Contenedores minimalistas: st.container(border=True) nativo, sin CSS
    # nuevo para el borde en sí — a diferencia de los `_card()` (key
    # "chartcard_*"), estos NO matchean la regla de estilos/_80_cards.py que
    # transparenta los cards internos, así que conservan su borde propio
    # dentro de la card grande. Tamaño/radius sí llevan CSS propio, acotado
    # al prefijo de key "ventas_resumen_kpi_" (estilos/_80_cards.py).
    # Labels cortos y sin delta: en una columna angosta, un label largo
    # ("Ventas totales") + un valor de varios dígitos no entra en una sola
    # línea aunque el CSS ponga stMetric en flex-row. El contexto extra
    # (fecha del mejor día, qué significa "en alza") pasa a `help=` — un
    # tooltip no consume ancho de línea.
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1.container(border=True, key="ventas_resumen_kpi_venta"):
        st.metric("Ventas", f"S/ {total_venta:,.0f}")
    with k2.container(border=True, key="ventas_resumen_kpi_vol"):
        st.metric(vol_label or "Clientes",
                  f"{total_pax:,.0f}" if vol_label else "—")
    with k3.container(border=True, key="ventas_resumen_kpi_ticket"):
        st.metric("Ticket", f"S/ {ticket_prom:,.2f}" if ticket_prom else "—")
    with k4.container(border=True, key="ventas_resumen_kpi_mejor"):
        st.metric("Mejor", f"S/ {mejor_valor:,.0f}",
                  help=f"{mejor_dia:%d/%m/%Y}")
    with k5.container(border=True, key="ventas_resumen_kpi_alza"):
        st.metric("Días en alza", f"{alzas}/{len(g) - 1}",
                  help="Días con más venta que el día anterior")

    # ── Venta total por día (barras) + volumen ───────────────────────────
    # Coloreadas por tendencia día-a-día (mismo criterio que el KPI "Días en
    # alza": total de hoy vs. total de ayer) — no por apertura/cierre de
    # transacciones sueltas (eso era el candlestick que reemplaza esta
    # vista, ver arquitectura.md regla #85). El primer día no tiene día
    # anterior con el que compararse: color neutro (ACENTO), ni sube ni baja.
    g["pct_vs_ayer"] = g["total"].pct_change() * 100
    colores = [ACENTO if pd.isna(p) else (EXITO if p >= 0 else ERROR)
               for p in g["pct_vs_ayer"]]
    hover_dia = [
        f"{f:%d/%m/%Y} · S/ {t:,.0f}<br>"
        + ("Primer día del rango" if pd.isna(p) else f"{p:+.1f}% vs. día anterior")
        for f, t, p in zip(g["dia"], g["total"], g["pct_vs_ayer"])
    ]

    with _card("ventas_resumen_dia", "Tendencia diaria de venta",
               titulo_arriba=True):
        filas_sub = 2 if vol_label else 1
        # `row_h` y no `alturas`: este nombre tapaba al módulo
        # graficos.alturas dentro de la función y `alturas.MINI` reventaba
        # con AttributeError sobre una lista (lo cazó ruff en la migración
        # del 2026-08-13). Son proporciones de fila, no píxeles.
        row_h = [0.72, 0.28] if vol_label else [1.0]
        fig = make_subplots(rows=filas_sub, cols=1, shared_xaxes=True,
                            row_heights=row_h, vertical_spacing=0.06)
        fig.add_trace(go.Bar(
            x=g["dia"], y=g["total"], marker=dict(color=colores),
            hovertext=hover_dia, hoverinfo="text", name="",
        ), row=1, col=1)
        if vol_label:
            fig.add_trace(go.Bar(
                x=g["dia"], y=g["pax"], name=vol_label,
                marker=dict(color=GRIS_BORDE),
                hovertemplate=("%{x|%d/%m/%Y}<br>" + vol_label
                               + ": %{y:,.0f}<extra></extra>"),
            ), row=2, col=1)

        # División sutil entre semanas (un lunes = arranca semana nueva):
        # línea punteada gris clara, yref="paper" para que cruce las DOS
        # filas del subplot (barra + volumen) aunque solo haya una xaxis
        # con nombre propio ("x", fila 1) — paper va de 0 a 1 en TODA la
        # figura, no por fila. Se salta el lunes que coincide con el primer
        # día mostrado (una línea pegada al borde izquierdo no divide nada).
        _lunes = pd.date_range(g["dia"].min(), g["dia"].max(), freq="W-MON")
        for _l in _lunes:
            if _l <= g["dia"].min():
                continue
            fig.add_shape(
                type="line", xref="x", yref="paper",
                x0=_l - pd.Timedelta(hours=12), x1=_l - pd.Timedelta(hours=12),
                y0=0, y1=1,
                line=dict(color=GRIS_BORDE, width=1, dash="dot"),
                opacity=0.8, layer="below",
            )

        _compras_layout(fig, alto=alturas.apilado(alturas.MINI, filas_sub))
        fig.update_layout(
            showlegend=False,
            yaxis=dict(tickprefix="S/ ", gridcolor=GRIS_BORDE),
        )
        fig.update_xaxes(
            type="date", tickmode="linear", tick0=g["dia"].min(),
            dtick=86400000.0, tickformat="%d/%m", tickangle=-45,
            tickfont=dict(size=10), row=filas_sub, col=1,
        )
        if vol_label:
            fig.update_yaxes(title=vol_label, tickformat=",.0f", row=2, col=1)
        st.plotly_chart(fig, use_container_width=True, key="ventas_g_resumen_dia")
        st.caption(
            "Verde = vendió más que el día anterior · rojo = vendió menos "
            "(el primer día del rango no tiene con qué compararse)."
            + _nota_recorte)

    # ── Ticket promedio diario ───────────────────────────────────────────
    if vol_label:
        with _card("ventas_resumen_ticket", "Ticket promedio diario",
                   titulo_arriba=True):
            gt = g.dropna(subset=["ticket"])
            if gt.empty:
                st.info("Sin datos de ticket promedio en el rango.")
            else:
                fig_t = go.Figure(go.Scatter(
                    x=gt["dia"], y=gt["ticket"], mode="lines+markers",
                    line=dict(color=ACENTO, width=2.2),
                    hovertemplate="%{x|%d/%m/%Y}<br>Ticket: S/ %{y:.2f}<extra></extra>",
                ))
                _compras_layout(fig_t, alto=alturas.MINI)
                fig_t.update_layout(showlegend=False,
                                    yaxis=dict(tickprefix="S/ ", gridcolor=GRIS_BORDE))
                fig_t.update_xaxes(type="date", tickformat="%d/%m", tickangle=-45,
                                   tickfont=dict(size=10))
                st.plotly_chart(fig_t, use_container_width=True,
                                key="ventas_g_resumen_ticket")

    # ── Top platos (Ingreso / Cantidad) ──────────────────────────────────
    if col_prod:
        with _card("ventas_resumen_top", "Top platos vendidos", titulo_arriba=True):
            agg = {"ingreso": ("venta", "sum")}
            agg["cantidad"] = ("cant", "sum") if col_cant else ("venta", "count")
            top = tabla.groupby("prod").agg(**agg).reset_index()

            metrica = st.pills(
                "Métrica", ["Ingreso", "Cantidad"], default="Ingreso",
                key="ventas_resumen_top_metrica", label_visibility="collapsed",
            ) or "Ingreso"
            campo = "ingreso" if metrica == "Ingreso" else "cantidad"
            top = top.sort_values(campo, ascending=False).head(8).sort_values(campo)

            if top.empty:
                st.info("Sin datos de productos en el rango.")
            else:
                _txt = ([f"S/ {v:,.0f}" for v in top[campo]] if metrica == "Ingreso"
                        else [f"{v:,.0f} uds" for v in top[campo]])
                fig_p = go.Figure(go.Bar(
                    x=top[campo], y=[_compras_truncar(p, 26) for p in top["prod"]],
                    orientation="h", marker=dict(color=ACENTO),
                    text=_txt, textposition="outside", cliponaxis=False,
                    hovertemplate=("%{y}<br>" + ("S/ %{x:,.0f}" if metrica == "Ingreso"
                                                 else "%{x:,.0f} unidades")
                                  + "<extra></extra>"),
                ))
                _compras_layout(fig_p, alto=alturas.por_filas(
                    len(top), px_fila=40, minimo=240, extra=60,
                    rol=alturas.APOYO))
                fig_p.update_layout(
                    showlegend=False, margin=dict(l=10, r=90, t=10, b=10),
                    xaxis=dict(tickprefix="S/ " if metrica == "Ingreso" else ""),
                )
                st.plotly_chart(fig_p, use_container_width=True,
                                key="ventas_g_resumen_top")
