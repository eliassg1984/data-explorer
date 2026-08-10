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

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import cargar as _cargar_reporte
from tema import (
    ACENTO, BLANCO, GRIS_BORDE, GRIS_TEXTO_SUAVE, LAVANDA_FONDO, PALETA_SERIES,
    SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _card, _layout, _render_rail, _resolver, renderizar_graficos_genericos,
)

# Familias de compras.parquet que SÍ son insumo/ingrediente — las únicas que
# tiene sentido cruzar contra receta. El resto (Costos Producción, Gastos
# Administrativos/Ventas, Envases y Embalajes) es gasto operativo real pero
# estructuralmente NUNCA va a matchear un COD INS de receta; incluirlas solo
# infla el nodo "Sin vincular" con ruido que no es un hueco de datos, es
# gasto que nunca fue insumo. Validado con datos reales 2026-08-09 — ver
# memoria de proyecto `esquema-real-compras-recetaventa` y arquitectura.md.
_FAMILIAS_INGREDIENTE_COMPRAS = frozenset({
    "ALIMENTOS", "VINOS Y ESPUMANTES", "BEBIDAS CON ALCOHOL", "BEBIDAS SIN ALCOHOL",
})

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py) — reemplaza el st.pills que vivia ANTES adentro del
# card. El selector "Medir por" (Costo/Cantidad) y el selectbox de Plato NO
# son parte del rail: son parametros de CADA grafico (Tabla no los usa).
_RECETAVENTA_RAIL_CATEGORIAS = (
    ("Vista", (("Sankey por plato",        "Sankey"),
               ("Composición del plato",   "Composición"),
               ("Ranking de platos",       "Ranking"),
               ("Ingredientes clave",      "Ingredientes"),
               ("Panorama de compras",     "Panorama"))),
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


# ─── 5. Panorama de compras (Producto comprado → Plato) ────────────────────
# Cruza compras.parquet (lo que se COMPRÓ a proveedores) con
# recetaventa.parquet (lo que la receta dice que se USA) — a diferencia de
# las 4 vistas de arriba, que solo miran recetaventa.parquet. Precedente de
# carga cruzada: graficos/ventas.py::_compra_por_dia ya llama
# data.cargar("compras.parquet") directamente desde el dashboard de Ventas.
#
# Detalles no obvios (ver memoria de proyecto
# `esquema-real-compras-recetaventa` para el detalle completo):
#   - El join es por CÓDIGO (compras.COD_PRODUCTO == recetaventa.COD INS),
#     nunca por nombre. LLAVE_PRODUCTO/ENLACE PARECEN la clave por el
#     nombre pero están casi vacías — no sirven.
#   - recetaventa.parquet mezcla platos activos y dados de baja (54,8% de
#     las filas son de platos INACTIV). Sin filtrar por
#     `ITEM VENTA ACTIVO`/`INS ACTIVO` el ranking de "top platos" sale mal
#     — se detectó a simple vista con el mockup (nombres de platos que ya
#     no están en carta) antes de construir esto.
#   - No hay click-drill sobre los nodos del Sankey: `go.Sankey` no es una
#     traza seleccionable (mismo caso que `go.Heatmap`, regla #11 de
#     arquitectura.md) y "Flujo" (Ajuste) ya tomó la misma decisión por la
#     misma razón. Selectbox en su lugar — mismo patrón que el selector de
#     Plato de este archivo.
def _cargar_flujo_compras_receta(df_rv, es_soles, top_n, fecha_ini, fecha_fin):
    """Arma nodos/links del panorama Producto→Plato. Devuelve un dict, o
    None si compras.parquet no está disponible, le faltan columnas, o no
    queda ninguna fila tras los filtros (mismo criterio defensivo que
    graficos/ventas.py::_compra_por_dia — nunca lanza, el caller decide
    qué mostrar)."""
    df_c = _cargar_reporte("compras.parquet")
    if df_c is None or df_c.empty:
        return None

    col_cod_prod = _resolver(df_c, ["COD_PRODUCTO", "Cod Producto", "Codigo Producto"])
    col_nombre_prod = _resolver(df_c, ["NOMBRE_PRODUCTO", "Nombre producto", "Nombre Producto"])
    col_familia_c = _resolver(df_c, ["FAMILIA", "Nombre Familia", "Familia"])
    col_valor_c = _resolver(df_c, ["VALOR_COMPRA", "Valor compra", "Importe Total"])
    col_cant_c = _resolver(df_c, ["CANTIDAD_COMPRA", "Cantidad compra", "Cantidad"])
    col_fecha_c = _resolver(df_c, ["FECHA_EMISION_DOC", "Fecha documento", "Fecha emision doc"])
    col_valor_medida = col_valor_c if es_soles else col_cant_c
    if not (col_cod_prod and col_nombre_prod and col_familia_c and col_valor_medida):
        return None

    col_cod_ins = _resolver(df_rv, ["COD INS", "Cod Ins"])
    col_cod_plato = _resolver(df_rv, ["COD PLATO", "Cod Plato"])
    col_plato = _resolver(df_rv, ["Nomb Plato", "Nombre Plato", "PLATO", "Plato"])
    col_total = _resolver(df_rv, ["Total", "TOTAL", "Importe", "Costo Total"])
    col_cant_rv = _resolver(df_rv, ["Cantidad", "CANTIDAD", "Cant"])
    col_valor_rv = col_total if es_soles else col_cant_rv
    col_activo_item = _resolver(df_rv, ["ITEM VENTA ACTIVO", "Item Venta Activo"])
    col_activo_ins = _resolver(df_rv, ["INS ACTIVO", "Ins Activo"])
    if not (col_cod_ins and col_cod_plato and col_plato and col_valor_rv):
        return None

    d = df_c.copy()
    d = d[d[col_familia_c].astype(str).str.upper().isin(_FAMILIAS_INGREDIENTE_COMPRAS)]
    if col_fecha_c:
        _f = pd.to_datetime(d[col_fecha_c], errors="coerce")
        d = d[_f.notna()]
        if fecha_ini is not None:
            d = d[_f.dt.normalize() >= pd.Timestamp(fecha_ini)]
        if fecha_fin is not None:
            d = d[_f.dt.normalize() <= pd.Timestamp(fecha_fin)]
    d = d.copy()
    d["_cod"] = d[col_cod_prod].astype(str).str.strip()
    d["_valor"] = pd.to_numeric(d[col_valor_medida], errors="coerce").fillna(0)
    if d.empty or d["_valor"].sum() <= 0:
        return None

    # Recetaventa: SOLO platos/insumos activos (ver docstring del módulo).
    rv = df_rv.copy()
    if col_activo_item:
        rv = rv[rv[col_activo_item].astype(str).str.upper().str.startswith("ACTIV")
                & ~rv[col_activo_item].astype(str).str.upper().str.startswith("INACTIV")]
    if col_activo_ins:
        rv = rv[rv[col_activo_ins].astype(str).str.upper().str.startswith("ACTIV")
                & ~rv[col_activo_ins].astype(str).str.upper().str.startswith("INACTIV")]
    rv["_cod_ins"] = rv[col_cod_ins].astype(str).str.strip()
    rv["_valor_rv"] = pd.to_numeric(rv[col_valor_rv], errors="coerce").fillna(0)
    rv_agg = rv.groupby(["_cod_ins", col_plato], as_index=False)["_valor_rv"].sum()
    rv_agg = rv_agg[rv_agg["_valor_rv"] > 0]
    if rv_agg.empty:
        return None
    rv_agg["_prop"] = rv_agg.groupby("_cod_ins")["_valor_rv"].transform(lambda s: s / s.sum())
    cod_ins_set = set(rv_agg["_cod_ins"])

    d["_match"] = d["_cod"].isin(cod_ins_set)
    prod_val = (d[d["_match"]]
                .groupby("_cod")
                .agg(nombre=(col_nombre_prod, "first"), valor=("_valor", "sum"))
                .reset_index())
    if prod_val.empty:
        return None

    links = []
    for _, fila in prod_val.iterrows():
        cod, nombre, valor = fila["_cod"], str(fila["nombre"]), fila["valor"]
        for _, p in rv_agg[rv_agg["_cod_ins"] == cod].iterrows():
            links.append({"producto": nombre, "plato": str(p[col_plato]),
                          "valor": float(valor * p["_prop"])})
    links_df = pd.DataFrame(links)

    top_prod = links_df.groupby("producto")["valor"].sum().sort_values(ascending=False)
    top_plato = links_df.groupby("plato")["valor"].sum().sort_values(ascending=False)
    prod_top = set(top_prod.head(top_n).index)
    plato_top = set(top_plato.head(top_n).index)
    links_df["producto_n"] = links_df["producto"].where(links_df["producto"].isin(prod_top), "Otros insumos")
    links_df["plato_n"] = links_df["plato"].where(links_df["plato"].isin(plato_top), "Otros platos")
    links_final = links_df.groupby(["producto_n", "plato_n"], as_index=False)["valor"].sum()
    links_final = links_final[links_final["valor"] > 0]

    sin_receta_detalle = (
        d.loc[~d["_match"]]
        .groupby(col_nombre_prod, as_index=False)["_valor"].sum()
        .rename(columns={col_nombre_prod: "Producto", "_valor": "Valor"})
        .sort_values("Valor", ascending=False)
    )

    return {
        "links": links_final,
        "recetaventa_activa": rv,
        "col_plato": col_plato,
        "col_valor_rv": "_valor_rv",
        "nombre_a_cod": dict(zip(prod_val["nombre"].astype(str), prod_val["_cod"])),
        "total_alcance": float(d["_valor"].sum()),
        "total_matched": float(prod_val["valor"].sum()),
        "sin_receta": float(d.loc[~d["_match"], "_valor"].sum()),
        "sin_receta_detalle": sin_receta_detalle,
    }


def _fig_panorama_sankey(links_df, es_soles):
    """go.Sankey Producto→Plato. Mismo lenguaje visual que `_sankey_plato`:
    PALETA_SERIES por producto (gris para el cajón 'Otros insumos'),
    listones al color del ORIGEN (los platos reciben de insumos de colores
    distintos a la vez — pintarlos de un solo color no significaría nada,
    por eso quedan en lavanda fija, igual que un nodo 'destino' neutro)."""
    prods = (links_df.groupby("producto_n")["valor"].sum()
             .sort_values(ascending=False).index.tolist())
    platos = (links_df.groupby("plato_n")["valor"].sum()
              .sort_values(ascending=False).index.tolist())
    idx = {n: i for i, n in enumerate(prods)}
    idx.update({n: i + len(prods) for i, n in enumerate(platos)})

    color_por_prod = {
        n: (GRIS_TEXTO_SUAVE if n == "Otros insumos" else PALETA_SERIES[i % len(PALETA_SERIES)])
        for i, n in enumerate(prods)
    }
    node_colors = [color_por_prod[n] for n in prods] + [LAVANDA_FONDO] * len(platos)
    link_colors = [_hex_a_rgba(color_por_prod[p], 0.38) for p in links_df["producto_n"]]
    pref, num = _fmt_valor(es_soles)

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=prods + platos, color=node_colors, pad=14, thickness=16,
            line=dict(color=BLANCO, width=0.5),
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=[idx[p] for p in links_df["producto_n"]],
            target=[idx[p] for p in links_df["plato_n"]],
            value=links_df["valor"].tolist(),
            color=link_colors,
            hovertemplate=(f"%{{source.label}} → %{{target.label}}<br>"
                           f"{pref}%{{value:{num}}}<extra></extra>"),
        ),
    ))
    alto = min(760, max(420, (len(prods) + len(platos)) * 15 + 150))
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
    )
    return fig


def _kpis_panorama(resultado, es_soles):
    """Fila de 3 st.metric (mismo patrón que Salidas). `delta_color='off'`
    a propósito en los 3: el % no es un indicador de bueno/malo (un string
    sin signo se pintaría verde por default), es solo proporción."""
    pref, _ = _fmt_valor(es_soles)
    total = resultado["total_alcance"]
    matched = resultado["total_matched"]
    sin = resultado["sin_receta"]
    pct_m = f"{matched / total * 100:.1f}%" if total else None
    pct_s = f"{sin / total * 100:.1f}%" if total else None
    c1, c2, c3 = st.columns(3)
    c1.metric("Compras en alcance", f"{pref}{total:,.0f}")
    c2.metric("Vinculado a receta activa", f"{pref}{matched:,.0f}", pct_m, delta_color="off")
    c3.metric("Sin vincular todavía", f"{pref}{sin:,.0f}", pct_s, delta_color="off")


def _drill_insumo(resultado, es_soles):
    """Selectbox de insumo → tabla de las recetas (platos activos) que lo
    usan. Reemplaza al click-en-nodo (ver nota del módulo: Sankey no es
    seleccionable)."""
    prods = sorted(n for n in resultado["links"]["producto_n"].unique() if n != "Otros insumos")
    if not prods:
        return
    sel = st.selectbox("Ver recetas de este insumo", prods, key="rv_pan_insumo_sel")
    cod = resultado["nombre_a_cod"].get(sel)
    if cod is None:
        return
    rv = resultado["recetaventa_activa"]
    col_plato = resultado["col_plato"]
    col_valor_rv = resultado["col_valor_rv"]
    sub = (rv[rv["_cod_ins"] == cod]
           .groupby(col_plato, as_index=False)[col_valor_rv].sum()
           .sort_values(col_valor_rv, ascending=False)
           .rename(columns={col_plato: "Plato", col_valor_rv: "Valor"}))
    pref, _ = _fmt_valor(es_soles)
    sub["Valor"] = sub["Valor"].map(lambda v: f"{pref}{v:,.2f}")
    st.caption(f"**{sel}** aparece en {len(sub)} platos activos")
    st.dataframe(sub, hide_index=True, use_container_width=True, height=220)


def _drill_plato_jump(resultado):
    """Selectbox de plato + botón que reusa la vista 'Sankey por plato' YA
    EXISTENTE: setea su session_state y hace rerun, en vez de duplicar esa
    lógica acá. Ver docstring del módulo (por qué no hay click directo)."""
    platos = sorted(n for n in resultado["links"]["plato_n"].unique() if n != "Otros platos")
    if not platos:
        return
    sel = st.selectbox("Ver el flujo completo de un plato", platos, key="rv_pan_plato_sel")
    if st.button("Abrir Sankey de este plato →", key="rv_pan_plato_ir", use_container_width=True):
        st.session_state["rv_plato_sel"] = sel
        st.session_state["rv_graf_tipo"] = "Sankey por plato"
        st.rerun()


def _panorama_compras(df_f, es_soles):
    """Punto de entrada de la vista 'Panorama de compras'."""
    c_topn, c_fecha = st.columns([1, 2])
    with c_topn:
        top_n = st.selectbox("Top N", [8, 10, 15, 20], index=1, key="rv_pan_topn")
    with c_fecha:
        rango = st.date_input(
            "Rango de compras (vacío = todo el histórico)", value=(),
            format="DD/MM/YYYY", key="rv_pan_rango",
        )
    fecha_ini = rango[0] if len(rango) >= 1 else None
    fecha_fin = rango[1] if len(rango) >= 2 else None

    resultado = _cargar_flujo_compras_receta(df_f, es_soles, top_n, fecha_ini, fecha_fin)
    if resultado is None:
        st.info(
            "No se pudo armar el panorama: falta compras.parquet, o no hay "
            "compras de Alimentos/Vinos/Bebidas con receta activa asociada "
            "en el rango elegido."
        )
        return

    _kpis_panorama(resultado, es_soles)

    fig = _fig_panorama_sankey(resultado["links"], es_soles)
    with _card("rv_panorama", "Productos comprados → platos que los usan"):
        st.plotly_chart(fig, use_container_width=True, key=f"rv_panorama_sankey_{top_n}")

    col_a, col_b = st.columns(2)
    with col_a:
        _drill_insumo(resultado, es_soles)
    with col_b:
        _drill_plato_jump(resultado)

    detalle = resultado["sin_receta_detalle"]
    with st.expander(f"📋 Sin vincular todavía — {len(detalle)} productos"):
        pref, _ = _fmt_valor(es_soles)
        tabla = detalle.head(50).copy()
        tabla["Valor"] = tabla["Valor"].map(lambda v: f"{pref}{v:,.2f}")
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

    # El selector de plato solo aparece para las vistas por plato — pero
    # `with c_plato:` se entra SIEMPRE (el if va adentro, no afuera). Si el
    # if envuelve el `with`, en los runs donde no aplica Streamlit nunca
    # "visita" esa posición del árbol y no la limpia: el selectbox de la
    # vista anterior queda pegado (visto en vivo 2026-08-09 cambiando de
    # Sankey a Ranking — el combo "Plato" seguía ahí, funcional pero
    # huérfano). Entrar siempre y decidir adentro fuerza a Streamlit a
    # registrar la posición vacía y limpiarla.
    plato = None
    with c_plato:
        if graf in ("Sankey por plato", "Composición del plato"):
            plato = st.selectbox("Plato", platos, index=idx_def, key="rv_plato_sel")

    with st.container(border=True, key="rv_graf_card"):
        # Mismo problema, mismo motivo: sub-container CON KEY QUE VARÍA POR
        # VISTA (no un key fijo) para que cambiar de rail fuerce un remount
        # limpio en vez de acumular widgets de la vista anterior debajo de
        # la nueva (le pasó a _panorama_compras: sus selectbox de drill
        # aparecían también en Ranking). Mismo espíritu que el contador de
        # remount de arquitectura.md regla #9, aplicado al nombre del graf
        # en vez de a un contador de aperturas.
        with st.container(key=f"rv_graf_body_{graf.lower().replace(' ', '_')}"):
            if graf == "Sankey por plato":
                _sankey_plato(df_f, col_plato, col_item, col_valor, plato, es_soles)
            elif graf == "Composición del plato":
                _composicion_plato(df_f, col_plato, col_item, col_valor, plato, es_soles)
            elif graf == "Ranking de platos":
                _ranking_platos(df_f, col_plato, col_valor, es_soles)
            elif graf == "Ingredientes clave":
                _ingredientes_clave(df_f, col_plato, col_item, col_valor, es_soles)
            elif graf == "Panorama de compras":
                _panorama_compras(df_f, es_soles)
