"""
graficos.ventas_resumen — vista "Resumen ejecutivo" del dashboard de Ventas:
KPIs del rango + candlestick diario (apertura/cierre/máx/mín de las líneas
de venta de cada día) + volumen de Pax, ticket promedio diario y top platos.

Inspirado en un mockup tipo "panel bursátil" para restaurantes. La vela NO es
decorativa: apertura/cierre son la primera/última línea de venta REGISTRADA
ese día y máx/mín el ticket de línea más caro/barato — mismo criterio que
`graficos/compras/volatilidad.py::_vol_ohlc_semana` (candlestick semanal de
precio unitario), aplicado a día/línea de venta en vez de semana/precio. NO
es una comparación día-contra-día (para eso está "Venta por día", que
grafica el TOTAL); esta vela expone la DISPERSIÓN de montos por línea
dentro de cada jornada, algo que ningún otro gráfico de Ventas muestra hoy.

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

MIN_DIAS = 5     # con menos, un candlestick diario no dice nada
MAX_DIAS = 30    # tope de velas legibles. Mismo espíritu que MAX_SEMANAS de
                 # compras/volatilidad.py (arquitectura.md regla #74): el
                 # filtro de fecha de la franja es un TECHO, no la ventana en
                 # sí — con un rango de "todo el año" cargado, esta vista
                 # sigue mostrando solo los últimos 30 días CON datos. 30
                 # replica el alcance del mockup original (un mes calendario).


def _resumen_ohlc_dia(montos_ordenados):
    """OHLC de una lista de montos de línea de venta de UN día, YA ordenada
    por hora. None si está vacía. Mismo criterio que
    graficos/compras/volatilidad.py::_vol_ohlc_semana, a nivel línea de
    venta/día en vez de precio unitario/semana."""
    montos = [m for m in montos_ordenados if pd.notna(m) and m > 0]
    if not montos:
        return None
    return {"o": float(montos[0]), "c": float(montos[-1]),
            "h": float(max(montos)), "l": float(min(montos))}


@st.fragment
def _ventas_resumen(d, col_venta, col_fecha, col_pax, col_pedido, col_prod, col_cant):
    """"Resumen ejecutivo": KPIs + candlestick diario + volumen + ticket
    promedio + top platos, todas las piezas sobre la MISMA ventana de días
    (últimos `MAX_DIAS` con datos) para que cuenten la misma historia.
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

    # ── OHLC + total por día (líneas de venta ordenadas por hora) ────────
    filas = []
    for f, gd in tabla.groupby("dia"):
        ohlc = _resumen_ohlc_dia(gd["venta"].tolist())
        if ohlc:
            filas.append({"dia": f, **ohlc, "total": gd["venta"].sum()})
    if not filas:
        st.info("Sin datos en el rango cargado.")
        return
    g = pd.DataFrame(filas).sort_values("dia").reset_index(drop=True)

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

    st.caption(
        f"Resumen ejecutivo · {dias[0]:%d/%m/%Y} – {dias[-1]:%d/%m/%Y} "
        f"({len(dias)} días con ventas)"
        + ("" if len(dias_disponibles) <= MAX_DIAS else
           f" — recortado a los últimos {MAX_DIAS} días del rango cargado."))

    # Contenedores minimalistas: st.container(border=True) nativo, sin CSS
    # nuevo — a diferencia de los `_card()` (key "chartcard_*"), estos NO
    # matchean la regla de estilos/_80_cards.py que transparenta los cards
    # internos, así que conservan su borde propio dentro de la card grande.
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1.container(border=True):
        st.metric("💰 Ventas totales", f"S/ {total_venta:,.0f}")
    with k2.container(border=True):
        st.metric(f"👥 {vol_label}" if vol_label else "👥 Clientes",
                  f"{total_pax:,.0f}" if vol_label else "—")
    with k3.container(border=True):
        st.metric("🎟️ Ticket promedio",
                  f"S/ {ticket_prom:,.2f}" if ticket_prom else "—")
    with k4.container(border=True):
        st.metric("🏆 Mejor día", f"S/ {mejor_valor:,.0f}",
                  delta=f"{mejor_dia:%d/%m}", delta_color="off")
    with k5.container(border=True):
        st.metric("📈 Días en alza", f"{alzas}/{len(g) - 1}",
                  delta="vs. día anterior", delta_color="off")

    # ── Candlestick diario + volumen ─────────────────────────────────────
    with _card("ventas_resumen_candle", "Rango de venta por día (candlestick)",
               titulo_arriba=True):
        filas_sub = 2 if vol_label else 1
        alturas = [0.72, 0.28] if vol_label else [1.0]
        fig = make_subplots(rows=filas_sub, cols=1, shared_xaxes=True,
                            row_heights=alturas, vertical_spacing=0.06)
        fig.add_trace(go.Candlestick(
            x=g["dia"], open=g["o"], high=g["h"], low=g["l"], close=g["c"],
            increasing=dict(line=dict(color=EXITO), fillcolor=EXITO),
            decreasing=dict(line=dict(color=ERROR), fillcolor=ERROR),
            hovertext=[
                f"{f:%d/%m/%Y} · Total del día S/ {t:,.0f}<br>"
                f"Apertura S/ {o:,.2f} · Máx S/ {h:,.2f} · "
                f"Mín S/ {l:,.2f} · Cierre S/ {c:,.2f}"
                for f, t, o, h, l, c in
                zip(g["dia"], g["total"], g["o"], g["h"], g["l"], g["c"])
            ],
            hoverinfo="text", name="",
        ), row=1, col=1)
        if vol_label:
            fig.add_trace(go.Bar(
                x=g["dia"], y=g["pax"], name=vol_label,
                marker=dict(color=GRIS_BORDE),
                hovertemplate=("%{x|%d/%m/%Y}<br>" + vol_label
                               + ": %{y:,.0f}<extra></extra>"),
            ), row=2, col=1)

        _compras_layout(fig, alto=520 if vol_label else 400)
        fig.update_layout(
            showlegend=False,
            xaxis=dict(rangeslider=dict(visible=False)),
            yaxis=dict(tickprefix="S/ ", gridcolor=GRIS_BORDE),
        )
        fig.update_xaxes(
            type="date", tickmode="linear", tick0=g["dia"].min(),
            dtick=86400000.0, tickformat="%d/%m", tickangle=-45,
            tickfont=dict(size=10), row=filas_sub, col=1,
        )
        if vol_label:
            fig.update_yaxes(title=vol_label, tickformat=",.0f", row=2, col=1)
        st.plotly_chart(fig, use_container_width=True, key="ventas_g_resumen_candle")
        st.caption(
            "Apertura/cierre = primera/última línea de venta registrada ese "
            "día · máx/mín = ticket de línea más caro/barato del día. No es "
            "una comparación contra el día anterior — para eso está "
            "«Venta por día».")

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
                _compras_layout(fig_t, alto=260)
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
                _compras_layout(fig_p, alto=max(240, 40 * len(top) + 60))
                fig_p.update_layout(
                    showlegend=False, margin=dict(l=10, r=90, t=10, b=10),
                    xaxis=dict(tickprefix="S/ " if metrica == "Ingreso" else ""),
                )
                st.plotly_chart(fig_p, use_container_width=True,
                                key="ventas_g_resumen_top")
