"""
graficos.recetas_comun — infraestructura COMPARTIDA entre Receta Base y
Receta Venta.

Los dos parquets son la MISMA forma de dato — un BOM (lista de materiales):
cada fila es un ítem/insumo dentro de un contenedor (plato o receta base),
con una cantidad y un costo. Tres gráficos (Ranking, Ingredientes/Insumos
clave, Panorama de compras) son literalmente el mismo cálculo sobre
columnas distintas — este módulo tiene la ÚNICA copia de cada uno,
parametrizada por nombre de columna y por las etiquetas de cada dominio
("Plato" vs "Receta base"). `graficos/recetaventa.py` y
`graficos/recetabase.py` son capas finas: resuelven SUS columnas reales y
llaman a lo de acá con un `key_prefix`/keys propias (evita choques de
session_state — los dos dashboards conviven en la MISMA sesión de navegador
desde que comparten ítem de nav, ver `_chip_fuente`).

Dos gráficos QUEDARON en el camino, los dos por el mismo motivo — se
borran cuando pierden su ÚLTIMO llamador, no antes:

  · `_composicion_contenedor` (la dona de UN plato/receta) vivió acá hasta
    el 2026-08-28. Dejó de ser compartida el 2026-08-24, cuando Receta
    Venta reemplazó su "Composición" por una tabla propia
    (`recetaventa.py::_tabla_composicion_venta`) que necesita columnas
    —Grupo/Subgrupo/P.VENTA SALON/CST SALON/%CST SALON— sin equivalente en
    recetabase.parquet; y se borró al sacarle a Receta Base sus vistas de
    UNA receta elegida a mano, que la dejaron sin un solo llamador. Ver
    `arquitectura.md` #236.
  · `_sankey_contenedor` corrió la MISMA suerte el 2026-08-30: Receta
    Base ya no lo llamaba desde el #236, así que Receta Venta —que dio de
    baja esa vista a pedido ese mismo día— era su último llamador. Con
    él se fue `_drill_contenedor_jump` (el botón "Abrir Sankey →" del
    Panorama de compras), que sólo existía para saltar hasta ahí y quedó
    sin destino. Ver el docstring de `recetaventa.py`.

Confirmado que NO se cruzan entre sí (0% overlap `recetabase.COD RB` vs
`recetaventa.COD INS`, ver memoria de proyecto
`esquema-real-compras-recetaventa`): son dos catálogos de insumos
independientes que cuelgan de `compras.COD_PRODUCTO` cada uno por su lado.
Por eso nunca se ofrece un puente Base↔Venta — solo el mismo esqueleto
visual aplicado a cada uno.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import cargar as _cargar_reporte
from tema import (
    ACENTO, BLANCO, GRIS_BORDE, GRIS_TEXTO_SUAVE, LAVANDA_FONDO, PALETA_SERIES,
    SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
)
from graficos.base import _card, _layout, _resolver
from graficos import alturas

# Familias de compras.parquet que SÍ son insumo/ingrediente — las únicas que
# tiene sentido cruzar contra receta (compra de gasto operativo real como
# Envases/Gastos Administrativos nunca va a matchear un código de insumo).
# Compartida: aplica igual de compras → Receta Venta que de compras →
# Receta Base, ambas cruzan contra el mismo compras.parquet. Validado con
# datos reales 2026-08-09 — ver memoria de proyecto
# `esquema-real-compras-recetaventa` y arquitectura.md.
_FAMILIAS_INGREDIENTE_COMPRAS = frozenset({
    "ALIMENTOS", "VINOS Y ESPUMANTES", "BEBIDAS CON ALCOHOL", "BEBIDAS SIN ALCOHOL",
})


# ─── Helpers de formato ─────────────────────────────────────────────────────
def _hex_a_rgba(hex_color: str, alpha: float = 0.45) -> str:
    """'#6c5ce7' → 'rgba(108,92,231,0.45)'. Para links de Sankey semitransp."""
    h = str(hex_color).lstrip("#")
    if len(h) != 6:
        return f"rgba(108,92,231,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _fmt_valor(es_soles: bool):
    """(prefijo, formato) según la métrica activa sea costo (S/) o cantidad."""
    return ("S/ ", ",.2f") if es_soles else ("", ",.2f")


def _activo(serie):
    """True donde el flag de activo/inactivo de la fila indica ACTIVO.

    Los TRES flags de "activo" que usan estos dos parquets vienen en
    formatos DISTINTOS aunque compartan intención (confirmado contra R2
    real, 2026-08-13):
      · recetaventa.ITEM VENTA ACTIVO / INS ACTIVO → "ACTIV" / "INACTIV" / ""
      · recetabase.RB ACT                          → "RB.ACTIV" / "RB.INACT"
      · recetabase.INS ACTIVO (MISMO NOMBRE que en recetaventa, formato
        DISTINTO)                                  → "INS.ACT" / "INS.INAC"
    Un `.str.startswith("ACTIV")` (lo que usaba el código original de
    Receta Venta, antes de esta función) no sirve para los dos de Base:
    ninguno arranca con "ACTIV" por el prefijo ("RB."/"INS."). La señal que
    SÍ es estable en los tres formatos es la sub-cadena "INAC" (siempre
    presente en la forma inactiva, nunca en la activa) — más vacío/NaN, que
    se trata como "no confirmado activo" (mismo criterio que ya usaba
    Receta Venta para su ~0.5% de INS ACTIVO en blanco). Verificado que
    reproduce EXACTO el conteo de filas activas que ya tenía Receta Venta
    en producción (1200/2713 con ambos flags) antes de generalizar esto.

    `serie.isna()` (no un match de texto tipo "nan"/"none") para el vacío:
    según la fuente, un valor faltante llega como `None`, `NaN` o `pd.NA`,
    y `.astype(str)` los serializa DISTINTO ("None" vs "nan") — confiar en
    el texto se comió el caso `None` en la primera versión de esta función."""
    vacio = serie.isna() | (serie.astype(str).str.strip() == "")
    s = serie.astype(str).str.upper()
    return ~vacio & ~s.str.contains("INAC")


# ─── Chip de fuente (Opción A del rail unificado) ──────────────────────────
def _chip_fuente(reporte_activo):
    """Segmented control Base/Venta/Nueva arriba del rail — separa las tres
    entradas del mismo ítem de nav ("Recetas", ver
    navegacion.py::grupo_nav). Clic en el lado NO activo NAVEGA (mismo
    mecanismo que el rail de navegación: session_state['_nav_reporte'] +
    rerun) en vez de filtrar — así reusa TODO el pipeline de carga de
    app.py (cfg, archivo, fecha_ultima_actualizacion, refresco...) sin
    duplicar ni un `if` ahí. "Nueva Receta" es `tool: True` (no un parquet,
    ver formulario_receta.py) — igual navega por el mismo mecanismo, app.py
    la desvía antes de tocar el pipeline de carga.

    La key incluye `reporte_activo` a propósito: si el usuario entra por el
    RAIL de navegación (no por este chip) — p.ej. volviendo de otro reporte
    — una key fija dejaría "pegado" el valor de la sesión anterior. Mismo
    patrón que la key de `st.plotly_chart(on_select=...)` en
    graficos/ajuste (CLAUDE.md § trampas de Streamlit)."""
    etiquetas = {
        "Receta Base": "Receta base",
        "Receta Venta": "Receta venta",
        "Nueva Receta": "+ Nueva",
    }
    inverso = {v: k for k, v in etiquetas.items()}
    sel = st.segmented_control(
        "Fuente", list(etiquetas.values()),
        default=etiquetas.get(reporte_activo, "Receta base"),
        key=f"recetas_fuente_chip_{reporte_activo}",
        label_visibility="collapsed",
    )
    destino = inverso.get(sel, reporte_activo)
    if destino != reporte_activo:
        st.session_state["_nav_reporte"] = destino
        st.rerun()


# ─── 1. Ranking de contenedores por costo ───────────────────────────────────
def _ranking_contenedores(d, col_contenedor, col_valor, es_soles, *,
                          key_topn, card_key, titulo_card):
    """Barras horizontales: los contenedores que más cuestan (suma de sus
    ítems)."""
    g = (d.groupby(col_contenedor, as_index=False)[col_valor].sum()
           .sort_values(col_valor, ascending=False))
    if g.empty:
        st.info("Sin datos para el ranking.")
        return
    pref, num = _fmt_valor(es_soles)

    topn = st.selectbox("Mostrar", [10, 15, 20, 30, "Todos"], index=1,
                        key=key_topn)
    g_top = g if topn == "Todos" else g.head(int(topn))
    g_top = g_top.sort_values(col_valor)  # ascendente → mayor arriba en barh

    fig = go.Figure(go.Bar(
        x=g_top[col_valor], y=g_top[col_contenedor].astype(str),
        orientation="h", marker_color=SERIE_PRINCIPAL,
        text=[f"{pref}{v:,.0f}" for v in g_top[col_valor]],
        textposition="outside",
        hovertemplate=f"%{{y}}<br>{pref}%{{x:{num}}}<extra></extra>",
    ))
    fig.update_layout(**_layout(
        height=alturas.por_filas(len(g_top), px_fila=30,
                                 minimo=360, extra=120),
        xaxis=dict(tickprefix=pref, tickformat=",.0f", gridcolor=GRIS_BORDE),
        yaxis=dict(showticklabels=True, gridcolor=GRIS_BORDE),
        showlegend=False,
    ))
    with _card(card_key, titulo_card):
        st.plotly_chart(fig, use_container_width=True)


# ─── 2. Ítems clave (transversales) ─────────────────────────────────────────
def _items_clave(d, col_contenedor, col_item, col_valor, es_soles, *,
                 card_key, titulo_card, etiqueta_item, etiqueta_contenedor_plural,
                 expander_titulo):
    """Insumos/ítems que más pesan en el costo total y en cuántos
    contenedores distintos aparecen — dónde conviene negociar con
    proveedores o revisar la ficha técnica."""
    g = (d.groupby(col_item)
           .agg(_valor=(col_valor, "sum"),
                _n=(col_contenedor, "nunique"))
           .reset_index()
           .sort_values("_valor", ascending=False))
    if g.empty:
        st.info("Sin datos para mostrar.")
        return
    pref, num = _fmt_valor(es_soles)

    g_top = g.head(15).sort_values("_valor")
    fig = go.Figure(go.Bar(
        x=g_top["_valor"], y=g_top[col_item].astype(str),
        orientation="h", marker_color=ACENTO,
        customdata=g_top["_n"],
        text=[f"{pref}{v:,.0f}" for v in g_top["_valor"]],
        textposition="outside",
        hovertemplate=(f"%{{y}}<br>{pref}%{{x:{num}}}"
                       f"<br>en %{{customdata}} {etiqueta_contenedor_plural}<extra></extra>"),
    ))
    fig.update_layout(**_layout(
        height=alturas.por_filas(len(g_top), px_fila=30,
                                 minimo=360, extra=120),
        xaxis=dict(tickprefix=pref, tickformat=",.0f", gridcolor=GRIS_BORDE),
        yaxis=dict(showticklabels=True, gridcolor=GRIS_BORDE),
        showlegend=False,
    ))
    with _card(card_key, titulo_card):
        st.plotly_chart(fig, use_container_width=True)

    with st.expander(expander_titulo):
        tabla = g.head(40).rename(columns={
            col_item: etiqueta_item, "_valor": "Costo total",
            "_n": f"N.° {etiqueta_contenedor_plural}",
        })
        tabla["Costo total"] = tabla["Costo total"].map(lambda v: f"{pref}{v:,.2f}")
        st.dataframe(tabla, hide_index=True, use_container_width=True)


# ─── 3. Panorama de compras (Producto comprado → contenedor) ───────────────
# Cruza compras.parquet (lo que se COMPRÓ a proveedores) con el parquet de
# receta activo (lo que la receta dice que se USA). Precedente de carga
# cruzada: graficos/ventas.py::_compra_por_dia ya llama
# data.cargar("compras.parquet") directamente desde otro dashboard.
#
#   - El join es por CÓDIGO (compras.COD_PRODUCTO == COD INS / COD INS RB),
#     nunca por nombre. LLAVE_PRODUCTO/ENLACE/RB ART ENLAZADO/RB INS
#     ENLAZADO PARECEN la clave por el nombre pero están casi vacías.
#   - Ambos parquets mezclan ítems activos y dados de baja — filtrar con
#     `_activo()` ANTES de agrupar, o el ranking sale mal (ver su docstring
#     para los 3 formatos distintos de flag).
#   - Sin click-drill sobre los nodos del Sankey: `go.Sankey` no es una
#     traza seleccionable (mismo caso que `go.Heatmap`, arquitectura.md
#     regla #11/#44). Selectbox en su lugar.
def _cargar_flujo_compras(df_x, es_soles, top_n, fecha_ini, fecha_fin, *,
                          col_cod_ins_cand, col_contenedor_cand,
                          col_valor_cand, col_cant_cand,
                          col_activo_contenedor_cand, col_activo_item_cand,
                          etiqueta_otros_contenedor):
    """Arma nodos/links del panorama Producto→contenedor. Devuelve un dict,
    o None si compras.parquet no está disponible, faltan columnas, o no
    queda ninguna fila tras los filtros — nunca lanza, el caller decide qué
    mostrar (mismo criterio defensivo que graficos/ventas.py::_compra_por_dia)."""
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

    col_cod_ins = _resolver(df_x, col_cod_ins_cand)
    col_contenedor = _resolver(df_x, col_contenedor_cand)
    col_total = _resolver(df_x, col_valor_cand)
    col_cant_x = _resolver(df_x, col_cant_cand)
    col_valor_x = col_total if es_soles else col_cant_x
    col_activo_cont = _resolver(df_x, col_activo_contenedor_cand)
    col_activo_ins = _resolver(df_x, col_activo_item_cand)
    if not (col_cod_ins and col_contenedor and col_valor_x):
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

    # Solo ítems/contenedores ACTIVOS (ver docstring de _activo()).
    x = df_x.copy()
    if col_activo_cont:
        x = x[_activo(x[col_activo_cont])]
    if col_activo_ins:
        x = x[_activo(x[col_activo_ins])]
    x["_cod_ins"] = x[col_cod_ins].astype(str).str.strip()
    x["_valor_x"] = pd.to_numeric(x[col_valor_x], errors="coerce").fillna(0)
    x_agg = x.groupby(["_cod_ins", col_contenedor], as_index=False)["_valor_x"].sum()
    x_agg = x_agg[x_agg["_valor_x"] > 0]
    if x_agg.empty:
        return None
    x_agg["_prop"] = x_agg.groupby("_cod_ins")["_valor_x"].transform(lambda s: s / s.sum())
    cod_ins_set = set(x_agg["_cod_ins"])

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
        for _, p in x_agg[x_agg["_cod_ins"] == cod].iterrows():
            links.append({"producto": nombre, "contenedor": str(p[col_contenedor]),
                          "valor": float(valor * p["_prop"])})
    links_df = pd.DataFrame(links)

    top_prod = links_df.groupby("producto")["valor"].sum().sort_values(ascending=False)
    top_cont = links_df.groupby("contenedor")["valor"].sum().sort_values(ascending=False)
    prod_top = set(top_prod.head(top_n).index)
    cont_top = set(top_cont.head(top_n).index)
    links_df["producto_n"] = links_df["producto"].where(links_df["producto"].isin(prod_top), "Otros insumos")
    links_df["contenedor_n"] = links_df["contenedor"].where(
        links_df["contenedor"].isin(cont_top), etiqueta_otros_contenedor)
    links_final = links_df.groupby(["producto_n", "contenedor_n"], as_index=False)["valor"].sum()
    links_final = links_final[links_final["valor"] > 0]

    sin_receta_detalle = (
        d.loc[~d["_match"]]
        .groupby(col_nombre_prod, as_index=False)["_valor"].sum()
        .rename(columns={col_nombre_prod: "Producto", "_valor": "Valor"})
        .sort_values("Valor", ascending=False)
    )

    return {
        "links": links_final,
        "activa": x,
        "col_contenedor": col_contenedor,
        "col_valor_x": "_valor_x",
        "nombre_a_cod": dict(zip(prod_val["nombre"].astype(str), prod_val["_cod"])),
        "total_alcance": float(d["_valor"].sum()),
        "total_matched": float(prod_val["valor"].sum()),
        "sin_receta": float(d.loc[~d["_match"], "_valor"].sum()),
        "sin_receta_detalle": sin_receta_detalle,
        "etiqueta_otros_contenedor": etiqueta_otros_contenedor,
    }


def _fig_panorama_sankey(links_df, es_soles):
    """go.Sankey Producto→contenedor. PALETA_SERIES por producto (gris para
    el cajón 'Otros insumos'), listones al color del ORIGEN (los
    contenedores reciben de insumos de colores distintos a la vez — pintarlos
    de un solo color no significaría nada, por eso quedan en lavanda fija,
    igual que un nodo 'destino' neutro)."""
    prods = (links_df.groupby("producto_n")["valor"].sum()
             .sort_values(ascending=False).index.tolist())
    conts = (links_df.groupby("contenedor_n")["valor"].sum()
             .sort_values(ascending=False).index.tolist())
    idx = {n: i for i, n in enumerate(prods)}
    idx.update({n: i + len(prods) for i, n in enumerate(conts)})

    color_por_prod = {
        n: (GRIS_TEXTO_SUAVE if n == "Otros insumos" else PALETA_SERIES[i % len(PALETA_SERIES)])
        for i, n in enumerate(prods)
    }
    node_colors = [color_por_prod[n] for n in prods] + [LAVANDA_FONDO] * len(conts)
    link_colors = [_hex_a_rgba(color_por_prod[p], 0.38) for p in links_df["producto_n"]]
    pref, num = _fmt_valor(es_soles)

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=prods + conts, color=node_colors, pad=14, thickness=16,
            line=dict(color=BLANCO, width=0.5),
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=[idx[p] for p in links_df["producto_n"]],
            target=[idx[p] for p in links_df["contenedor_n"]],
            value=links_df["valor"].tolist(),
            color=link_colors,
            hovertemplate=(f"%{{source.label}} → %{{target.label}}<br>"
                           f"{pref}%{{value:{num}}}<extra></extra>"),
        ),
    ))
    alto = min(760, max(420, (len(prods) + len(conts)) * 15 + 150))
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
    )
    return fig


def _kpis_panorama(resultado, es_soles):
    """Fila de 3 st.metric (mismo patrón que Salidas). `delta_color='off'` a
    propósito en los 3: el % no es un indicador de bueno/malo, es proporción."""
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


def _drill_insumo(resultado, es_soles, *, key_select, col_contenedor_out, etiqueta_plural):
    """Selectbox de insumo → tabla de los contenedores (activos) que lo
    usan. Reemplaza al click-en-nodo (Sankey no es seleccionable)."""
    prods = sorted(n for n in resultado["links"]["producto_n"].unique() if n != "Otros insumos")
    if not prods:
        return
    sel = st.selectbox("Ver dónde se usa este insumo", prods, key=key_select)
    cod = resultado["nombre_a_cod"].get(sel)
    if cod is None:
        return
    act = resultado["activa"]
    col_contenedor = resultado["col_contenedor"]
    col_valor_x = resultado["col_valor_x"]
    sub = (act[act["_cod_ins"] == cod]
           .groupby(col_contenedor, as_index=False)[col_valor_x].sum()
           .sort_values(col_valor_x, ascending=False)
           .rename(columns={col_contenedor: col_contenedor_out, col_valor_x: "Valor"}))
    pref, _ = _fmt_valor(es_soles)
    sub["Valor"] = sub["Valor"].map(lambda v: f"{pref}{v:,.2f}")
    st.caption(f"**{sel}** aparece en {len(sub)} {etiqueta_plural}")
    st.dataframe(sub, hide_index=True, use_container_width=True,
                 height=alturas.MINI)


def _panorama_compras(df_f, es_soles, *, key_prefix,
                      col_cod_ins_cand, col_contenedor_cand,
                      col_valor_cand, col_cant_cand,
                      col_activo_contenedor_cand, col_activo_item_cand,
                      etiqueta_otros_contenedor, titulo_card,
                      col_contenedor_out, etiqueta_contenedor_plural):
    """Punto de entrada de la vista 'Panorama de compras', compartido por
    Receta Base y Receta Venta.

    Hasta el 2026-08-30 tomaba cuatro parámetros más (`state_key_rail`,
    `nombre_vista_sankey`, `etiqueta_selectbox_jump`, `clave_seccion_
    sankey`) para un segundo drill — "Abrir Sankey →" — que saltaba a la
    vista Sankey de UN contenedor. Se borraron junto con
    `_drill_contenedor_jump` cuando Receta Venta, su último llamador, dio
    de baja esa vista: ver el docstring del módulo."""
    c_topn, c_fecha = st.columns([1, 2])
    with c_topn:
        top_n = st.selectbox("Top N", [8, 10, 15, 20], index=1, key=f"{key_prefix}_pan_topn")
    with c_fecha:
        rango = st.date_input(
            "Rango de compras (vacío = todo el histórico)", value=(),
            format="DD/MM/YYYY", key=f"{key_prefix}_pan_rango",
        )
    fecha_ini = rango[0] if len(rango) >= 1 else None
    fecha_fin = rango[1] if len(rango) >= 2 else None

    resultado = _cargar_flujo_compras(
        df_f, es_soles, top_n, fecha_ini, fecha_fin,
        col_cod_ins_cand=col_cod_ins_cand,
        col_contenedor_cand=col_contenedor_cand,
        col_valor_cand=col_valor_cand,
        col_cant_cand=col_cant_cand,
        col_activo_contenedor_cand=col_activo_contenedor_cand,
        col_activo_item_cand=col_activo_item_cand,
        etiqueta_otros_contenedor=etiqueta_otros_contenedor,
    )
    if resultado is None:
        st.info(
            "No se pudo armar el panorama: falta compras.parquet, o no hay "
            "compras de Alimentos/Vinos/Bebidas con receta activa asociada "
            "en el rango elegido."
        )
        return

    _kpis_panorama(resultado, es_soles)

    fig = _fig_panorama_sankey(resultado["links"], es_soles)
    with _card(f"{key_prefix}_panorama", titulo_card):
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_panorama_sankey_{top_n}")

    # Un solo drill, a lo ancho. Hasta el 2026-08-30 había un segundo
    # ("Abrir Sankey →") que saltaba a la vista Sankey de un contenedor —
    # se borró con ella, ver el docstring de la función.
    _drill_insumo(resultado, es_soles, key_select=f"{key_prefix}_pan_insumo_sel",
                 col_contenedor_out=col_contenedor_out,
                 etiqueta_plural=etiqueta_contenedor_plural)

    detalle = resultado["sin_receta_detalle"]
    with st.expander(f"📋 Sin vincular todavía — {len(detalle)} productos"):
        pref, _ = _fmt_valor(es_soles)
        tabla = detalle.head(50).copy()
        tabla["Valor"] = tabla["Valor"].map(lambda v: f"{pref}{v:,.2f}")
        st.dataframe(tabla, hide_index=True, use_container_width=True)
