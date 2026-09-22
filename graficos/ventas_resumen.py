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

2026-09-22 — TRES AGREGADOS a pedido (mirando la vista publicada):
  1. Un SELECTOR DE FECHA propio, el mismo trigger-con-rango-escrito de
     Compras (`base.selector_fecha_tarjeta`). No es un filtro paralelo: con
     `categoria=None` escribe la MISMA clave canónica que la píldora de la
     franja, o sea que mover la fecha acá RECARGA el parquet del rango
     nuevo desde R2 (Ventas usa `carga_por_rango`, ver `app.py`). Es la
     segunda puerta al mismo dato — cómoda porque cae en la vista y no
     arriba de todo. De ahí el `st.rerun(scope="app")` del arranque: sin la
     corrida completa el `d` que recibe esta función seguiría siendo el del
     rango viejo.
  2. Dos filtros LOCALES de la vista, Grupo y Servicio, que recortan el `d`
     de esta tarjeta (los de la franja siguen existiendo y se COMPONEN con
     estos — el usuario pidió tenerlos a mano en la vista).
  3. Las barras de "Tendencia diaria" son CLICKEABLES, con un toggle
     Resumen/Detalle debajo — el mismo par que la vista «Compras por
     período» (arquitectura.md regla #476): «Resumen» es el gráfico escrito
     como tabla (una fila por día + total), «Detalle» es el desglose del
     día que se toca (sus platos). El clic sigue el patrón de foco-en-la-key
     de `ventas_comparativo.py` (regla #399): la selección de
     `st.plotly_chart(on_select=...)` persiste entre reruns, así que la key
     lleva el foco y cada clic procesado dispara un rerun de fragment.

El detalle profundo por producto (FoodCost, sparklines, %Var vs Año Pasado)
sigue viviendo en "Ranking & FoodCost" — este panel es la foto rápida de un
vistazo, no su reemplazo.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import (ACENTO, ADVERTENCIA, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO,
                  TEXTO_PRINCIPAL)
from graficos.base import (
    _card, _compras_layout, _compras_truncar, preservar_widgets,
    scope_rerun, selector_fecha_tarjeta,
)
from graficos.compras._comun import _first_point
from graficos import alturas

MIN_DIAS = 5     # con menos, la tendencia día-a-día no dice nada
MAX_DIAS = 30    # tope de barras legibles. Mismo espíritu que MAX_SEMANAS de
                 # compras/volatilidad.py (arquitectura.md regla #74): el
                 # filtro de fecha de la franja es un TECHO, no la ventana en
                 # sí — con un rango de "todo el año" cargado, esta vista
                 # sigue mostrando solo los últimos 30 días CON datos.

# Los controles propios de la vista, para que la recarga de fecha
# (`st.rerun(scope="app")`) no se los lleve. Es el mismo mecanismo que
# `_KEYS_WIDGET` de `compras/semanal.py` (arquitectura.md regla #373): ese
# rerun aborta la corrida antes de que estos widgets se registren, y
# Streamlit recolecta el estado de todo widget del fragment que no se
# dibujó. `preservar_widgets` los re-escribe sobre sí mismos antes de
# escalar.
_KEYS_WIDGET_RESUMEN = ("vt_resumen_grupo", "vt_resumen_serv",
                        "vt_resumen_modo", "ventas_resumen_top_metrica")

_MODO_DETALLE = "Detalle"
_MODO_RESUMEN = "Resumen"
_MODO_OPCIONES = (_MODO_RESUMEN, _MODO_DETALLE)
_MODO_DEFAULT = _MODO_RESUMEN   # "Resumen" no necesita un día en foco: la
                                # tabla del día completo se ve al abrir, y el
                                # clic queda para pasar a "Detalle".

_AYUDA_MODO = (
    "Qué se ve debajo del gráfico. **Resumen**: una fila por día —con su "
    "venta, sus clientes, su ticket y la variación contra el día anterior— "
    "más el total. **Detalle**: los platos del día que toques en el gráfico."
)

# Abreviaturas en español para el eje/tabla — Plotly y pandas rotulan en
# inglés si no se les dice otra cosa (misma trampa que arquitectura.md #241).
_DIAS_ABR_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Opacidad de las barras SIN foco cuando hay un día clickeado. Misma que
# `compras/semanal.py::_ATENUADO` y por el mismo motivo (regla #476).
_ATENUADO = 0.2


def _con_alpha(_hex, _a):
    """`#rrggbb` → `rgba(r,g,b,a)`. El foco se atenúa por COLOR y no con
    `marker.opacity` por punto: esa lista sobre barras crashea Plotly en el
    navegador. Copia de `compras/semanal.py::_con_alpha` (regla #476)."""
    _h = _hex.lstrip("#")
    _r, _g, _b = (int(_h[_i:_i + 2], 16) for _i in (0, 2, 4))
    return f"rgba({_r},{_g},{_b},{_a})"


def _fmt_dia(dt):
    """`Timestamp` → «Sáb 20/09», con el día de semana en español."""
    return f"{_DIAS_ABR_ES[dt.weekday()]} {dt.day:02d}/{dt.month:02d}"


@st.fragment
def _ventas_resumen(d, col_venta, col_fecha, col_pax, col_pedido, col_prod,
                    col_cant, col_fam=None, col_serv=None):
    """"Resumen ejecutivo": selector de fecha + filtros de Grupo/Servicio +
    KPIs + venta diaria clickeable + ticket promedio + top platos, todas las
    piezas sobre la MISMA ventana de días (últimos `MAX_DIAS` con datos)
    para que cuenten la misma historia.
    """
    # ── 0) La fecha cambió: recargar el parquet del rango nuevo ───────────
    # El selector escribe la clave canónica del rango (`categoria=None`), que
    # es la que lee `carga_por_rango` en `app.py`. Como el `d` de esta
    # función ya está materializado con el rango VIEJO, hay que escalar a una
    # corrida completa para que se vuelva a bajar. Va PRIMERO —antes de
    # dibujar nada— porque el rerun aborta lo que venga después, y
    # `preservar_widgets` salva los controles de la vista de la recolección.
    if st.session_state.pop("vt_resumen_fecha_flag", False):
        preservar_widgets(_KEYS_WIDGET_RESUMEN)
        st.rerun(scope="app")

    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el resumen ejecutivo.")
        return

    # ── 1) Fila de controles: Grupo · Servicio · … · fecha ────────────────
    # Grupo y Servicio son filtros LOCALES de esta vista (se componen con los
    # de la franja). La fecha es el trigger de Compras: apretarlo abre atajos
    # + escala de tiempo, y al aplicar uno recarga (ver el bloque 0).
    _ctrl = st.columns([1.6, 1.6, 3, 2.4], vertical_alignment="center")
    grupo_sel, serv_sel = [], []
    with _ctrl[0]:
        if col_fam and col_fam in d.columns:
            _grupos = sorted(d[col_fam].dropna().astype(str).unique().tolist())
            grupo_sel = st.multiselect(
                "Grupo", _grupos, key="vt_resumen_grupo",
                placeholder="Grupo: todos", label_visibility="collapsed")
    with _ctrl[1]:
        if col_serv and col_serv in d.columns:
            _servs = sorted(d[col_serv].dropna().astype(str).unique().tolist())
            serv_sel = st.multiselect(
                "Servicio", _servs, key="vt_resumen_serv",
                placeholder="Servicio: todos", label_visibility="collapsed")
    with _ctrl[3]:
        selector_fecha_tarjeta("vt_resumen", "vt_resumen_fecha_flag",
                               categoria=None)

    if grupo_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(grupo_sel)]
    if serv_sel and col_serv:
        d = d[d[col_serv].astype(str).isin(serv_sel)]
    if d is None or d.empty:
        st.info("No hay datos para los filtros de Grupo/Servicio elegidos.")
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

    # Los KPIs de arriba (Ventas/Clientes/Ticket/Mejor/Días en alza) se
    # quitaron a pedido el 2026-09-22: el gráfico sube y es el protagonista,
    # y esos mismos números viven en la tabla «Resumen» (una fila por día +
    # total) que va debajo. El ticket, que era un KPI y una tarjeta aparte,
    # ahora es una línea sobre el propio gráfico.
    _nota_recorte = ("" if len(dias_disponibles) <= MAX_DIAS else
                     f" Recortado a los últimos {MAX_DIAS} días con ventas "
                     "del rango cargado.")

    # ── Venta total por día (barras clickeables) + volumen + ticket ───────
    # Coloreadas por tendencia día-a-día (mismo criterio que el KPI "Días en
    # alza": total de hoy vs. total de ayer) — no por apertura/cierre de
    # transacciones sueltas (eso era el candlestick que reemplaza esta
    # vista, ver arquitectura.md regla #85). El primer día no tiene día
    # anterior con el que compararse: color neutro (ACENTO), ni sube ni baja.
    g["pct_vs_ayer"] = g["total"].pct_change() * 100
    _colores_base = [ACENTO if pd.isna(p) else (EXITO if p >= 0 else ERROR)
                     for p in g["pct_vs_ayer"]]
    hover_dia = [
        f"{f:%d/%m/%Y} · S/ {t:,.0f}<br>"
        + ("Primer día del rango" if pd.isna(p) else f"{p:+.1f}% vs. día anterior")
        for f, t, p in zip(g["dia"], g["total"], g["pct_vs_ayer"])
    ]

    # El día en foco (índice en `g`), leído ANTES de dibujar: la selección de
    # `on_select` persiste entre reruns, así que va en la key del gráfico y se
    # valida contra el largo actual (un rango nuevo puede tener menos días).
    foco = st.session_state.get("vt_resumen_foco")
    if foco is not None and not (0 <= foco < len(g)):
        foco = None
        st.session_state["vt_resumen_foco"] = None

    # AL HACER CLIC, ESA BARRA SE ILUMINA Y EL RESTO SE ATENÚA — el mismo
    # gesto que «Compras por período» (arquitectura.md regla #476): el foco
    # se marca por COLOR (las sin foco van a `_ATENUADO` de alfa) y no con
    # `marker.opacity` por punto, que sobre barras crashea Plotly. Sin foco,
    # todas a tono pleno.
    if foco is not None:
        colores = [c if i == foco else _con_alpha(c, _ATENUADO)
                   for i, c in enumerate(_colores_base)]
    else:
        colores = _colores_base

    with _card("ventas_resumen_dia", "Tendencia diaria de venta",
               titulo_arriba=True):
        # UNA sola figura (no make_subplots): la selección por clic de
        # `st.plotly_chart(on_select=...)` NO llega a las trazas de un
        # subplot —medido el 2026-09-22, `evt.selection.points` volvía
        # SIEMPRE vacío al clickear una barra de un `make_subplots`, y con
        # eso el drill no abría nunca—. Todas las vistas clickeables del
        # repo son figuras únicas (semanal, comparativo, volatilidad); acá
        # el volumen baja de subplot propio a una línea punteada sobre un
        # eje Y secundario, que es como `ventas.py::_ventas_grafico_dia`
        # dibuja Pax. Ver arquitectura.md regla #488.
        _hay_ticket = vol_label and "ticket" in g.columns
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=g["dia"], y=g["total"], name="Venta", yaxis="y",
            marker=dict(color=colores),
            hovertext=hover_dia, hoverinfo="text",
        ))
        if vol_label:
            fig.add_trace(go.Scatter(
                x=g["dia"], y=g["pax"], name=vol_label, mode="lines",
                line=dict(color=GRIS_TEXTO, width=1.5, dash="dot"),
                yaxis="y2",
                hovertemplate=("%{x|%d/%m/%Y}<br>" + vol_label
                               + ": %{y:,.0f}<extra></extra>"),
            ))
        # Ticket promedio como línea + puntos sobre un TERCER eje (soles,
        # pero otra escala que la venta: ~S/ 180 contra ~S/ 25.000). Va en su
        # propio eje a la derecha —igual que `ventas.py::_ventas_grafico_dia`
        # con Pax/Venta— para que las escalas no se aplasten. Antes era una
        # tarjeta aparte; se subió acá a pedido el 2026-09-22.
        if _hay_ticket:
            fig.add_trace(go.Scatter(
                x=g["dia"], y=g["ticket"], name="Ticket", mode="lines+markers",
                line=dict(color=ADVERTENCIA, width=2), marker=dict(size=5),
                yaxis="y3",
                hovertemplate=("%{x|%d/%m/%Y}<br>Ticket: S/ %{y:,.2f}"
                               "<extra></extra>"),
            ))

        # División sutil entre semanas (un lunes = arranca semana nueva):
        # línea punteada gris clara, yref="paper" para que cruce la figura
        # de arriba abajo. Se salta el lunes que coincide con el primer día
        # mostrado (una línea pegada al borde izquierdo no divide nada).
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

        # El gráfico es el protagonista de la vista (sin KPIs arriba): alto
        # PROTAGONISTA. `_xright` recorta el dominio del eje X para hacerle
        # lugar al tercer eje (el del ticket) a la derecha, como
        # `_ventas_grafico_dia`.
        _xright = 0.88 if _hay_ticket else 1.0
        _compras_layout(fig, alto=alturas.PROTAGONISTA)
        fig.update_layout(
            showlegend=bool(vol_label),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            margin=dict(l=10, r=(70 if _hay_ticket else 50 if vol_label else 10),
                        t=30, b=10),
            yaxis=dict(tickprefix="S/ ", gridcolor=GRIS_BORDE),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        title=vol_label or "", tickformat=",.0f",
                        visible=bool(vol_label)),
            yaxis3=dict(overlaying="y", side="right", anchor="free",
                        position=1.0, showgrid=False, tickprefix="S/ ",
                        tickformat=",.0f", title="Ticket",
                        visible=bool(_hay_ticket)),
        )
        fig.update_xaxes(
            domain=[0.0, _xright],
            type="date", tickmode="linear", tick0=g["dia"].min(),
            dtick=86400000.0, tickformat="%d/%m", tickangle=-45,
            tickfont=dict(size=10),
        )
        # MODO CLIC, no "select": al poner `on_select`, Streamlit deja el
        # dragmode en "select" (caja), y con eso un clic SUELTO no selecciona
        # nada (arquitectura.md regla #388). En "pan" Streamlit pone
        # clickmode="event+select" y el clic vuelve a abrir el detalle; los
        # ejes fijos dejan quieto el arrastre. Medido el 2026-09-22: sin esto
        # `evt.selection.points` volvía siempre vacío al clickear una barra.
        fig.update_layout(dragmode="pan")
        fig.update_xaxes(fixedrange=True)
        fig.update_yaxes(fixedrange=True)
        # on_select="rerun" + key con el foco: sin rotar la key el mismo clic
        # se re-procesa en cada rerun y el foco parpadea (regla #399).
        evt = st.plotly_chart(
            fig, use_container_width=True,
            key=f"ventas_g_resumen_dia_{foco if foco is not None else 'none'}",
            on_select="rerun", selection_mode="points",
            config={"displaylogo": False, "displayModeBar": False})
        st.caption(
            "Verde = vendió más que el día anterior · rojo = vendió menos "
            "(el primer día del rango no tiene con qué compararse). "
            "Clic en una barra para ver el detalle del día."
            + _nota_recorte)

        # Procesar el clic DESPUÉS de dibujar: se enfoca el día (o se suelta
        # si ya estaba enfocado) y se rerunea con la key nueva. La guarda
        # contra `vt_resumen_click` evita re-disparar el mismo clic.
        _mp = _first_point(evt)
        if _mp is not None:
            _pi = _mp.get("point_index", _mp.get("point_number"))
            if _pi is not None and st.session_state.get("vt_resumen_click") != _pi:
                st.session_state["vt_resumen_click"] = _pi
                st.session_state["vt_resumen_foco"] = (
                    None if foco == _pi else int(_pi))
                st.rerun(scope=scope_rerun())

    # ── Zona de abajo: Resumen (tabla por día) / Detalle (platos del día) ──
    _modo = st.segmented_control(
        "Vista de la tabla", _MODO_OPCIONES, default=_MODO_DEFAULT,
        key="vt_resumen_modo", label_visibility="collapsed",
        help=_AYUDA_MODO) or _MODO_DEFAULT

    if _modo == _MODO_RESUMEN:
        _tabla_resumen(g, vol_label)
    else:
        _tabla_detalle(tabla, g, foco, col_prod, col_cant)

    # (La tarjeta «Ticket promedio diario» que vivía acá se quitó el
    # 2026-09-22: el ticket es ahora la línea naranja del gráfico de arriba.)

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


def _fmt_pct(v):
    return "—" if pd.isna(v) else f"{v:+.0f}%"


def _tabla_resumen(g, vol_label):
    """El gráfico escrito como tabla: una fila por día (en el orden del eje)
    con venta, volumen, ticket y la variación contra el día anterior, más
    una fila TOTAL al pie. No depende del foco: se ve siempre.

    Las celdas se pre-formatean a STRING (no se deja el formateo al Styler):
    `st.dataframe` muestra «None» para un NaN de una columna numérica
    ignorando el `format` del Styler —el primer día no tiene variación—, y
    con la columna ya en texto eso se vuelve «—» de verdad. El color de la
    variación se decide por el signo del texto, que es lo único que queda."""
    filas = []
    for _, r in g.iterrows():
        fila = {"Día": _fmt_dia(r["dia"]),
                "Venta": f"S/ {r['total']:,.0f}",
                "Δ vs día ant.": _fmt_pct(r.get("pct_vs_ayer", np.nan))}
        if vol_label:
            fila[vol_label] = f"{r['pax']:,.0f}"
            _t = r.get("ticket", np.nan)
            fila["Ticket"] = "—" if pd.isna(_t) else f"S/ {_t:,.2f}"
        filas.append(fila)

    _tp = g["pax"].sum() if vol_label else 0
    total = {"Día": "Total", "Venta": f"S/ {g['total'].sum():,.0f}",
             "Δ vs día ant.": ""}
    if vol_label:
        total[vol_label] = f"{_tp:,.0f}"
        total["Ticket"] = (f"S/ {g['total'].sum() / _tp:,.2f}"
                           if _tp else "—")
    filas.append(total)
    tv = pd.DataFrame(filas)

    # Orden de columnas: Día · Venta · [Clientes · Ticket] · Δ
    orden = ["Día", "Venta"] + (
        [vol_label, "Ticket"] if vol_label else []) + ["Δ vs día ant."]
    tv = tv[orden]

    def _sty_fila(row):
        # La última fila (Total) en negrita; el resto normal.
        return ["font-weight:600" if row["Día"] == "Total" else ""
                for _ in row]

    def _color_delta(s):
        # El color sale del signo del texto ya formateado.
        if s.startswith("+"):
            return f"color:{EXITO}"
        if s.startswith("-"):
            return f"color:{ERROR}"
        return f"color:{GRIS_TEXTO}"

    sty = (tv.style
           .apply(_sty_fila, axis=1)
           .map(_color_delta, subset=["Δ vs día ant."]))
    st.dataframe(sty, use_container_width=True, hide_index=True,
                 height=alturas.por_filas(len(tv), px_fila=34,
                                          extra=48, minimo=0))


def _tabla_detalle(tabla, g, foco, col_prod, col_cant):
    """Los platos del día en foco: Producto · Cantidad · Ingreso · % del día,
    de mayor a menor ingreso. Sin foco (nadie tocó una barra todavía), lo
    dice en vez de mostrar una tabla vacía."""
    if foco is None:
        st.info("Tocá una barra del gráfico para ver el detalle de ese día.")
        return
    if not col_prod or "prod" not in tabla.columns:
        st.info("Este parquet no trae la columna de producto: no hay detalle "
                "por plato.")
        return

    dia_foco = g["dia"].iloc[foco]
    dd = tabla[tabla["dia"] == dia_foco]
    if dd.empty:
        st.info("Sin líneas de venta para ese día.")
        return

    agg = {"Ingreso": ("venta", "sum")}
    if "cant" in dd.columns:
        agg["Cantidad"] = ("cant", "sum")
    det = dd.groupby("prod").agg(**agg).reset_index()
    det = det.rename(columns={"prod": "Producto"})
    _tot = det["Ingreso"].sum()
    det["% del día"] = (det["Ingreso"] / _tot * 100) if _tot else 0.0
    det = det.sort_values("Ingreso", ascending=False).reset_index(drop=True)

    orden = ["Producto"] + (["Cantidad"] if "Cantidad" in det.columns
                            else []) + ["Ingreso", "% del día"]
    det = det[orden]

    st.markdown(
        f'<div style="font-size:14px;font-weight:600;color:{TEXTO_PRINCIPAL};'
        f'margin:2px 0 6px;">Detalle de {_fmt_dia(dia_foco)} · '
        f'{dia_foco.year} <span style="color:{GRIS_TEXTO};font-weight:400;">'
        f'({len(det):,} platos · S/ {_tot:,.0f})</span></div>',
        unsafe_allow_html=True)

    fmt = {"Ingreso": "S/ {:,.0f}", "% del día": "{:.1f}%"}
    if "Cantidad" in det.columns:
        fmt["Cantidad"] = "{:,.0f}"
    sty = det.style.format(fmt).bar(
        subset=["Ingreso"], color=f"{ACENTO}33", align="left")
    st.dataframe(sty, use_container_width=True, hide_index=True,
                 height=alturas.por_filas(min(len(det), 15), px_fila=34,
                                          extra=48, minimo=0))
