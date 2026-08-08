"""
graficos.recetaventa — dashboard de gráficos de Receta Venta.

Cada fila de recetaventa.parquet es un ÍTEM de un plato:
    Nomb Plato · Item Rv · Cantidad · Total
    (plato)      (insumo)  (cant.)    (costo del insumo en el plato)

De ahí salen cuatro lecturas, elegibles con chips (una a la vez, igual que
el dashboard de Ajuste):

  1. Sankey por plato   → flujo Plato → Ítems, ancho = costo (o cantidad).
                          Responde "¿en qué se va el costo de ESTE plato?".
  2. Composición        → dona de participación de cada ítem en el plato.
  3. Ranking de platos  → qué platos cuestan más (barras).
  4. Ingredientes clave → insumos transversales: cuánto suman y en cuántos
                          platos aparecen (dónde negociar con proveedores).

Punto de entrada público: renderizar_graficos_recetaventa(). La
infraestructura (cards, layout, resolución de columnas, explorador
genérico) viene de graficos.base.
"""

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from tema import (
    ACENTO, BLANCO, GRIS_BORDE, PALETA_SERIES, SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _card, _layout, _render_rail, _resolver, _wrap_cat,
    renderizar_graficos_genericos,
)

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py) — reemplaza el st.pills que vivia ANTES adentro del
# card. El selector "Medir por" (Costo/Cantidad) y el selectbox de Plato NO
# son parte del rail: son parametros de CADA grafico (Tabla no los usa).
_RECETAVENTA_RAIL_CATEGORIAS = (
    ("Vista", (("Sankey por plato",        "Sankey"),
               ("Composición del plato",   "Composición"),
               ("Ranking de platos",       "Ranking"),
               ("Ingredientes clave",      "Ingredientes"))),
    ("Datos", (("Tabla", "Tabla"),)),
)


# ─── Helpers ────────────────────────────────────────────────────────────────
def _hex_a_rgba(hex_color: str, alpha: float = 0.45) -> str:
    """'#6c5ce7' → 'rgba(108,92,231,0.45)'. Para links del Sankey semitransp."""
    h = str(hex_color).lstrip("#")
    if len(h) != 6:
        return f"rgba(108,92,231,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _fmt_valor(es_soles: bool):
    """(prefijo, formato) según la métrica activa sea costo (S/) o cantidad."""
    return ("S/ ", ",.2f") if es_soles else ("", ",.2f")


# ─── 1. Sankey por plato ────────────────────────────────────────────────────
def _sankey_plato(d, col_plato, col_item, col_valor, plato, es_soles):
    """Diagrama Sankey de UN plato: nodo plato → un nodo por ítem, con el
    ancho del flujo proporcional al costo (o cantidad) del ítem."""
    sub = d[d[col_plato].astype(str) == str(plato)]
    g = (sub.groupby(col_item, as_index=False)[col_valor].sum())
    g = g[g[col_valor] > 0].sort_values(col_valor, ascending=False)
    if g.empty:
        st.info("Este plato no tiene ítems con valor positivo para graficar.")
        return

    items = g[col_item].astype(str).tolist()
    valores = [float(v) for v in g[col_valor].tolist()]
    total = sum(valores) or 1.0
    pref, num = _fmt_valor(es_soles)

    # Nodo 0 = plato; nodos 1..n = ítems. Links plato → cada ítem.
    labels = [str(plato)] + items
    node_colors = [ACENTO] + [PALETA_SERIES[i % len(PALETA_SERIES)]
                              for i in range(len(items))]
    link_colors = [_hex_a_rgba(PALETA_SERIES[i % len(PALETA_SERIES)], 0.45)
                   for i in range(len(items))]
    pct = [v / total * 100 for v in valores]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=labels, color=node_colors, pad=16, thickness=18,
            line=dict(color=BLANCO, width=0.5),
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=[0] * len(items),
            target=list(range(1, len(items) + 1)),
            value=valores, color=link_colors, customdata=pct,
            hovertemplate=(
                "%{target.label}<br>"
                f"{pref}%{{value:{num}}}"
                "<br>%{customdata:.1f}% del plato<extra></extra>"
            ),
        ),
    ))
    alto = min(720, max(360, len(items) * 24 + 150))
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
    )

    st.caption(
        f"**{plato}** · {len(items)} ítems · costo total {pref}{total:,.2f}"
    )
    with _card("rv_sankey", "Flujo de costo del plato"):
        st.plotly_chart(fig, use_container_width=True)


# ─── 2. Composición del plato (dona) ────────────────────────────────────────
def _composicion_plato(d, col_plato, col_item, col_valor, plato, es_soles):
    """Dona: participación de cada ítem en el total del plato seleccionado."""
    sub = d[d[col_plato].astype(str) == str(plato)]
    g = (sub.groupby(col_item, as_index=False)[col_valor].sum())
    g = g[g[col_valor] > 0].sort_values(col_valor, ascending=False)
    if g.empty:
        st.info("Este plato no tiene ítems con valor positivo para graficar.")
        return
    pref, num = _fmt_valor(es_soles)

    # Agrupa la cola larga en "Otros" para que la dona sea legible.
    TOP = 10
    if len(g) > TOP:
        cabeza = g.head(TOP)
        otros = g[col_valor].iloc[TOP:].sum()
        etiquetas = cabeza[col_item].astype(str).tolist() + ["Otros"]
        valores = cabeza[col_valor].tolist() + [otros]
    else:
        etiquetas = g[col_item].astype(str).tolist()
        valores = g[col_valor].tolist()

    fig = go.Figure(go.Pie(
        labels=etiquetas, values=valores, hole=0.55,
        marker=dict(colors=PALETA_SERIES * 4,
                    line=dict(color=BLANCO, width=1)),
        textinfo="label+percent", textposition="inside",
        insidetextorientation="radial",
        hovertemplate=f"%{{label}}<br>{pref}%{{value:{num}}}"
                      "<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        height=420, showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
    )
    with _card("rv_dona", "Composición del costo"):
        st.plotly_chart(fig, use_container_width=True)


# ─── 3. Ranking de platos por costo ─────────────────────────────────────────
def _ranking_platos(d, col_plato, col_valor, es_soles):
    """Barras horizontales: los platos que más cuestan (suma de sus ítems)."""
    g = (d.groupby(col_plato, as_index=False)[col_valor].sum()
           .sort_values(col_valor, ascending=False))
    if g.empty:
        st.info("Sin datos para el ranking.")
        return
    pref, num = _fmt_valor(es_soles)

    topn = st.selectbox("Mostrar", [10, 15, 20, 30, "Todos"], index=1,
                        key="rv_ranking_topn")
    g_top = g if topn == "Todos" else g.head(int(topn))
    g_top = g_top.sort_values(col_valor)  # ascendente → mayor arriba en barh

    fig = go.Figure(go.Bar(
        x=g_top[col_valor], y=g_top[col_plato].astype(str),
        orientation="h", marker_color=SERIE_PRINCIPAL,
        text=[f"{pref}{v:,.0f}" for v in g_top[col_valor]],
        textposition="outside",
        hovertemplate=f"%{{y}}<br>{pref}%{{x:{num}}}<extra></extra>",
    ))
    fig.update_layout(**_layout(
        height=min(640, max(360, len(g_top) * 30 + 120)),
        xaxis=dict(tickprefix=pref, tickformat=",.0f", gridcolor=GRIS_BORDE),
        yaxis=dict(showticklabels=True, gridcolor=GRIS_BORDE),
        showlegend=False,
    ))
    with _card("rv_ranking", "Platos por costo total"):
        st.plotly_chart(fig, use_container_width=True)


# ─── 4. Ingredientes clave (transversales) ──────────────────────────────────
def _ingredientes_clave(d, col_plato, col_item, col_valor, es_soles):
    """Insumos que más pesan en el costo total del recetario y en cuántos
    platos distintos aparecen — dónde conviene negociar con proveedores."""
    g = (d.groupby(col_item)
           .agg(_valor=(col_valor, "sum"),
                _platos=(col_plato, "nunique"))
           .reset_index()
           .sort_values("_valor", ascending=False))
    if g.empty:
        st.info("Sin datos de ingredientes.")
        return
    pref, num = _fmt_valor(es_soles)

    g_top = g.head(15).sort_values("_valor")
    fig = go.Figure(go.Bar(
        x=g_top["_valor"], y=g_top[col_item].astype(str),
        orientation="h", marker_color=ACENTO,
        customdata=g_top["_platos"],
        text=[f"{pref}{v:,.0f}" for v in g_top["_valor"]],
        textposition="outside",
        hovertemplate=(f"%{{y}}<br>{pref}%{{x:{num}}}"
                       "<br>en %{customdata} platos<extra></extra>"),
    ))
    fig.update_layout(**_layout(
        height=min(640, max(360, len(g_top) * 30 + 120)),
        xaxis=dict(tickprefix=pref, tickformat=",.0f", gridcolor=GRIS_BORDE),
        yaxis=dict(showticklabels=True, gridcolor=GRIS_BORDE),
        showlegend=False,
    ))
    with _card("rv_ingredientes", "Ingredientes de mayor costo total"):
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Tabla: ingredientes por costo y n.º de platos"):
        tabla = g.head(40).rename(columns={
            col_item: "Ingrediente", "_valor": "Costo total", "_platos": "N° platos",
        })
        tabla["Costo total"] = tabla["Costo total"].map(lambda v: f"{pref}{v:,.2f}")
        st.dataframe(tabla, hide_index=True, use_container_width=True)


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_recetaventa(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Receta Venta. df_full se ignora (catálogo sin fecha).

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py), llamado
    SIN args — igual que Ajuste: este dashboard no tiene chips propios de
    filtro (a diferencia de Ventas/Inventario), así que la Tabla usa los
    filtros genéricos que ya arma app.py."""
    col_plato = _resolver(df_f, ["Nomb Plato", "Nombre Plato", "PLATO", "Plato"])
    col_item = _resolver(df_f, ["Item Rv", "Item RV", "ITEM RV", "Item",
                                "Nombre Item", "Insumo", "Ingrediente",
                                "Nombre Producto"])
    col_total = _resolver(df_f, ["Total", "TOTAL", "Importe", "Costo Total",
                                 "Total Costo", "Valorizado"])
    col_cant = _resolver(df_f, ["Cantidad", "CANTIDAD", "Cant"])

    # Necesitamos plato + ítem + al menos una métrica numérica.
    if not col_plato or not col_item or not (col_total or col_cant):
        st.warning(
            "No se reconocieron las columnas de Receta Venta (se buscó "
            "«Nomb Plato», «Item Rv», «Total», «Cantidad»). "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    graf = _render_rail(_RECETAVENTA_RAIL_CATEGORIAS, "rv_graf_tipo",
                        btn_prefix="rv_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            # Sin chips propios (como Ajuste): pasa su df tal cual.
            tabla_cb(df_f)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    # ── Métrica del ancho/valor: Total (costo) o Cantidad ────────────────
    metricas = []
    if col_total:
        metricas.append("Costo (S/)")
    if col_cant:
        metricas.append("Cantidad")

    c_met, c_plato = st.columns([1, 2])
    with c_met:
        metrica = st.radio("Medir por", metricas, horizontal=True,
                           key="rv_metrica")
    es_soles = (metrica == "Costo (S/)")
    col_valor = col_total if es_soles else col_cant

    # ── Selector de plato (compartido por Sankey y Composición) ──────────
    # Default: el plato de mayor costo, para que la primera vista sea rica.
    platos = sorted(df_f[col_plato].dropna().astype(str).unique().tolist())
    totales = df_f.groupby(col_plato)[col_valor].sum()
    plato_rico = str(totales.idxmax()) if not totales.empty else (platos[0] if platos else "")
    idx_def = platos.index(plato_rico) if plato_rico in platos else 0

    with st.container(border=True, key="rv_graf_card"):
        # El selector de plato solo aparece para las vistas por plato.
        plato = None
        if graf in ("Sankey por plato", "Composición del plato"):
            with c_plato:
                plato = st.selectbox("Plato", platos, index=idx_def,
                                     key="rv_plato_sel")

        if graf == "Sankey por plato":
            _sankey_plato(df_f, col_plato, col_item, col_valor, plato, es_soles)
        elif graf == "Composición del plato":
            _composicion_plato(df_f, col_plato, col_item, col_valor, plato, es_soles)
        elif graf == "Ranking de platos":
            _ranking_platos(df_f, col_plato, col_valor, es_soles)
        elif graf == "Ingredientes clave":
            _ingredientes_clave(df_f, col_plato, col_item, col_valor, es_soles)
