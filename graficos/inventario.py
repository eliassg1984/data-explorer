"""
graficos.inventario — dashboard de Inventario Valorizado (v3). Layout unificado
con chips en franja blanca + card con pills.

v3 (2026-08-10) reemplaza las 4 vistas de v2 (Área y familia / Torta / Top
valor / Top cantidad) por 3: **Por área**, **Por familia** (misma barra
horizontal ordenada para las dos, con un toggle Valor/Cantidad — la torta se
rompía apenas una familia concentraba >70% del total) y **Buscar producto**
(nueva: ficha de un producto puntual, o de un grupo — Subfamilia — completo,
con cantidad + valorizado + precio promedio + unidad de medida por área).
Se agrega un KPI "Valorizado total" — vive DENTRO de la card izquierda (no
en una franja aparte arriba: se probó así y quedaba la card muy abajo).
El panel lateral de la derecha (Mayor cantidad/Precio más alto)
se mantiene igual en Por área/Por familia, pero en Buscar producto pasa a
mostrar productos relacionados (misma subfamilia/familia) en vez de un top
genérico — repetir el mismo top ahí era redundante con lo que ya se ve a la
izquierda para el producto elegido.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


from tema import ACENTO, ACENTO_FUERTE, TEXTO_PRINCIPAL
from graficos.base import (
    _compras_layout, _compras_truncar, _render_rail,
    _resolver, _slug, publicar_contexto_ia, renderizar_graficos_genericos,
)

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py).
_INVENTARIO_RAIL_CATEGORIAS = (
    ("Vista", (("Por área",        "Por área"),
               ("Por familia",     "Por familia"),
               ("Buscar producto", "Buscar producto"))),
    ("Datos", (("Tabla", "Tabla"),)),
)


def _rango_con_holgura(*series, factor=0.28):
    """Rango de eje X con holgura para que el texto `outside` de la barra
    más larga no se corte contra el borde del gráfico — con `cliponaxis=
    False` Plotly no recorta en el eje, pero SÍ recorta contra el margen
    fijo de `_compras_layout` (r=10px) si la barra ya ocupa casi el 100%
    del ancho. Bug real: "Por área" con `GASTOS` en S/ 161,816 (barra al
    tope) mostraba la etiqueta cortada en "S/ 16…". `factor` más alto para
    etiquetas largas (p.ej. "S/ x · y unidad" en la ficha de un producto)."""
    valores = [v for s in series for v in s]
    if not valores:
        return None
    lo, hi = min(0, min(valores)), max(0, max(valores))
    pad = max(abs(hi), abs(lo), 1) * factor
    return [lo - pad, hi + pad]


def _grafico_ranking(d, col_grp, col_val, titulo, key, clic=False, state_key=None,
                     compacto=False):
    """Barra horizontal ordenada de mayor a menor — Por área/Por familia.
    Siempre valorizado (sin toggle Valor/Cantidad — se sacó a pedido: acá
    solo importa el valorizado). Cada barra lleva su % de participación
    sobre el total NETO (mismo total que el KPI "Valorizado total" de la
    card — no sobre la suma de absolutos, para que sumen 100% de verdad
    con lo que el usuario ya está viendo arriba).

    `clic=True` agrega click-drill (mismo patrón que compras/familia.py):
    clic en una barra la resalta y guarda la categoría en
    `st.session_state[state_key]` — clic de nuevo la quita. Devuelve la
    categoría en foco (o None) para que el caller filtre el panel derecho
    y muestre el detalle del siguiente nivel debajo.

    `compacto=True` fuerza el formato bajito (menos px/barra) — lo usa el
    caller para el detalle de `_grafico_detalle_foco`. Con foco activo,
    ESTE gráfico (el ranking de arriba) también se achica solo, sin que el
    caller tenga que pedirlo: no tiene sentido mantenerlo a tamaño completo
    cuando ya cumplió su función (elegir la categoría) y lo que importa
    ahora es el detalle de abajo."""
    met = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    serie = met.groupby(d[col_grp].astype(str)).sum().sort_values()
    if serie.empty:
        st.info("Sin datos.")
        return None
    total = float(serie.sum())
    _texto = [
        f"S/ {v:,.0f} · {(v / total * 100):.1f}%" if total else f"S/ {v:,.0f}"
        for v in serie.values
    ]
    foco = st.session_state.get(state_key) if clic else None
    if foco and foco not in serie.index:
        foco = None
        st.session_state[state_key] = None
    color = ([ACENTO_FUERTE if i == foco else ACENTO for i in serie.index]
              if clic else ACENTO)
    fig = go.Figure(go.Bar(
        x=serie.values,
        y=[_compras_truncar(i, 30) for i in serie.index],
        orientation="h",
        marker=dict(color=color, opacity=0.85),
        text=_texto,
        textposition="outside", cliponaxis=False,
    ))
    # Con foco activo el ranking se achica (menos px por barra, tope más
    # bajo) para dejarle sitio al detalle de abajo dentro de la misma
    # pantalla — sin esto, ranking completo + detalle sumaban más que el
    # viewport y el usuario tenía que hacer scroll para ver lo que acababa
    # de pedir con el clic.
    if clic and foco:
        alto = min(240, max(140, 20 * len(serie) + 40))  # ya cumplió su función, se achica al mínimo
    elif compacto:
        alto = min(420, max(200, 28 * len(serie) + 40))  # detalle: el que importa ahora, algo más de aire
    else:
        alto = min(900, max(360, 34 * len(serie) + 60))
    _compras_layout(fig, alto=alto)
    fig.update_layout(title=titulo)
    fig.update_xaxes(visible=False, range=_rango_con_holgura(serie.values, factor=0.5))
    fig.update_yaxes(showgrid=False)  # sin esto la cuadrícula de _compras_layout
    # cruza cada barra horizontal a la altura de su fila — tiene sentido en un
    # eje de VALORES, no acá donde el eje Y son nombres de categoría.
    if not clic:
        st.plotly_chart(fig, use_container_width=True, key=key)
        return None

    # La selección de on_select persiste entre reruns: con key estática,
    # cada rerun re-procesa el mismo clic → toggle infinito (parpadeo).
    # El foco (valor de ANTES de este clic) va en la key, así al cambiar
    # de foco el widget es uno nuevo y no arrastra la selección vieja.
    evt = st.plotly_chart(fig, use_container_width=True, key=f"{key}_{foco or 'none'}",
                          on_select="rerun", selection_mode="points")
    puntos = ((evt or {}).get("selection", {}) or {}).get("points", [])
    p = puntos[0] if puntos else None
    if p is not None:
        idx = p.get("point_index")
        if idx is None:
            idx = p.get("point_number")
        if idx is not None and 0 <= idx < len(serie):
            cat = str(serie.index[idx])
            st.session_state[state_key] = None if foco == cat else cat
            st.rerun()
    return st.session_state.get(state_key)


def _grafico_detalle_foco(d, graf, col_grp, foco, col_fam, col_subfam, col_val):
    """Debajo del ranking principal, cuando hay una barra en foco: siguiente
    nivel de desglose del grupo elegido (Área → Familia, Familia →
    Subfamilia) — la pregunta natural después de "cuánto vale GASTOS" es
    "de qué se compone". Sin clic propio (no hay drill anidado, dos niveles
    alcanza) — así no compite con el ranking de arriba por la selección."""
    dd = d[d[col_grp].astype(str) == foco]
    if graf == "Por área":
        col_next, nombre_next = col_fam, "familia"
    else:
        col_next, nombre_next = col_subfam, "subfamilia"
    if not col_next or dd.empty:
        st.caption(f"Sin desglose adicional para {foco}.")
        return
    _grafico_ranking(dd, col_next, col_val, f"{foco} — por {nombre_next}",
                     key=f"inv_g_detalle_{_slug(foco)}", compacto=True)


def _ficha_producto(d, prod_sel, col_prod, col_area, col_val, col_cant,
                     col_unidad):
    """Cantidad + valorizado + precio promedio por área para UN producto —
    siempre las tres cifras juntas, sin toggle (no hay "elegir métrica"
    cuando ya elegiste el producto)."""
    dd = d[d[col_prod].astype(str) == prod_sel]
    _v = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
    _c = pd.to_numeric(dd[col_cant], errors="coerce").fillna(0) if col_cant else None
    unidad = (str(dd[col_unidad].dropna().iloc[0])
              if col_unidad and dd[col_unidad].notna().any() else "u")

    total_val = float(_v.sum())
    total_cant = float(_c.sum()) if _c is not None else None
    precio_prom = (total_val / total_cant) if total_cant else None

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cantidad total",
              f"{total_cant:,.0f} {unidad}" if total_cant is not None else "—")
    k2.metric("Valorizado total", f"S/ {total_val:,.0f}")
    k3.metric("Precio promedio",
              f"S/ {precio_prom:,.2f}/{unidad}" if precio_prom else "—")
    k4.metric("Áreas", f"{dd[col_area].nunique():,}")

    g = (pd.DataFrame({"area": dd[col_area].astype(str), "val": _v,
                       "cant": _c if _c is not None else 0})
         .groupby("area", as_index=False).agg(val=("val", "sum"), cant=("cant", "sum")))
    # Áreas sin nada de este producto (val=0 y cant=0: "inactivas" para él)
    # no suman una barra — solo ruido, la mayoría de las áreas ni lo tienen.
    g = g[(g["val"] != 0) | (g["cant"] != 0)].sort_values("val")
    if g.empty:
        st.info("Sin stock ni valorizado activo para este producto en ninguna área.")
        return
    _texto = [f"S/ {v:,.0f}  ·  {c:,.0f} {unidad}" for v, c in zip(g["val"], g["cant"])]
    fig = go.Figure(go.Bar(
        x=g["val"], y=[_compras_truncar(a, 30) for a in g["area"]],
        orientation="h", marker=dict(color=ACENTO, opacity=0.85),
        text=_texto, textposition="outside", cliponaxis=False,
        customdata=g["cant"],
        hovertemplate=("%{y}<br>Valorizado: S/ %{x:,.2f}<br>Cantidad: "
                       "%{customdata:,.1f} " + unidad + "<extra></extra>"),
    ))
    _compras_layout(fig, alto=min(900, max(320, 40 * len(g) + 80)))
    fig.update_layout(title=f"{prod_sel} — cantidad y valorizado por área")
    fig.update_xaxes(visible=False, range=_rango_con_holgura(g["val"], factor=0.35))
    fig.update_yaxes(showgrid=False)  # eje Y = nombres de área, no valores
    st.plotly_chart(fig, use_container_width=True, key="inv_g_producto")


def _ficha_subfamilia(d, subfam_sel, col_subfam, col_prod, col_area,
                       col_val, col_cant, col_unidad):
    """Todos los productos de una subfamilia, valorizado desglosado por
    área (barra apilada Producto × Área) — la pregunta "necesito ver
    Carnes ahora" sin pasar por la Tabla."""
    dd = d[d[col_subfam].astype(str) == subfam_sel]
    _v = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
    _c = pd.to_numeric(dd[col_cant], errors="coerce").fillna(0) if col_cant else None

    unidades = (dd[col_unidad].dropna().astype(str).unique().tolist()
                if col_unidad else [])
    unidad_unica = unidades[0] if len(unidades) == 1 else None
    total_val = float(_v.sum())
    total_cant = float(_c.sum()) if (_c is not None and unidad_unica) else None
    n_prod = dd[col_prod].nunique() if col_prod else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cantidad total",
              f"{total_cant:,.0f} {unidad_unica}" if total_cant is not None
              else ("— (unidades mixtas)" if col_unidad else "—"))
    k2.metric("Valorizado total", f"S/ {total_val:,.0f}")
    k3.metric("Precio promedio",
              f"S/ {(total_val / total_cant):,.2f}/{unidad_unica}" if total_cant else "—")
    k4.metric("Productos", f"{n_prod:,}")

    if not col_prod or dd.empty:
        st.info("Sin datos para este grupo.")
        return
    g = (pd.DataFrame({"prod": dd[col_prod].astype(str), "area": dd[col_area].astype(str),
                       "val": _v, "cant": _c if _c is not None else 0})
         .groupby(["prod", "area"], as_index=False).agg(val=("val", "sum"), cant=("cant", "sum")))
    # Productos sin stock ni valorizado ("inactivos" para esta subfamilia)
    # no entran: son la mayoría en un catálogo real y ensucian el desglose
    # sin aportar nada — además, empatados en 0, arruinaban el orden por
    # valor (quedaban en el orden alfabético del groupby, no por importe).
    tot_prod = g.groupby("prod").agg(val=("val", "sum"), cant=("cant", "sum"))
    tot_prod = tot_prod[(tot_prod["val"] != 0) | (tot_prod["cant"] != 0)]
    if tot_prod.empty:
        st.info("Ningún producto de este grupo tiene stock o valorizado activo.")
        return
    # Mayor a menor LEYENDO DE ARRIBA HACIA ABAJO. A diferencia de un
    # go.Bar con y=lista literal (donde el primer elemento pinta ABAJO,
    # ver _grafico_ranking), category_orders de px.bar pone el primer
    # elemento ARRIBA — confirmado en vivo (medido por posición en
    # pantalla, no por lectura del código): con ascending=True el
    # producto más CHICO terminaba arriba y el más grande abajo, al
    # revés de lo pedido.
    orden = tot_prod["val"].sort_values(ascending=False).index.tolist()
    g = g[g["prod"].isin(orden)]
    fig = px.bar(g, x="val", y="prod", color="area", orientation="h",
                 category_orders={"prod": orden}, custom_data=["cant"])
    _compras_layout(fig, alto=min(900, max(360, 40 * len(orden) + 80)))
    fig.update_layout(
        title=f"{subfam_sel} — valorizado por producto, desglosado por área",
        barmode="stack", xaxis_title=None, yaxis_title=None,
        legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=10)),
    )
    fig.update_traces(
        hovertemplate=("%{fullData.name}<br>%{y}<br>Valorizado: S/ %{x:,.2f}"
                       "<br>Cantidad: %{customdata[0]:,.1f}<extra></extra>"))
    fig.update_yaxes(showgrid=False)  # eje Y = nombres de producto, no valores
    st.plotly_chart(fig, use_container_width=True, key="inv_g_subfamilia")


def _limpiar_subfam():
    st.session_state["inv_buscar_subfamilia"] = None


def _limpiar_producto():
    st.session_state["inv_buscar_producto"] = None


def _render_buscar_producto(d, col_prod, col_area, col_subfam, col_val,
                            col_cant, col_unidad):
    """Buscador de producto puntual O de un grupo (Subfamilia) completo —
    mutuamente excluyentes: elegir uno limpia el otro (callback, antes del
    rerun, mismo patrón que `_rail_set` en graficos/base.py)."""
    if not col_prod or not col_area:
        st.info("Faltan columnas de producto o área para este buscador.")
        return

    productos = sorted(d[col_prod].dropna().astype(str).unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Producto", productos, index=None,
                     placeholder="Buscar producto por nombre…",
                     key="inv_buscar_producto", on_change=_limpiar_subfam)
    if col_subfam:
        subfams = sorted(d[col_subfam].dropna().astype(str).unique().tolist())
        with c2:
            st.selectbox("Grupo (Subfamilia)", subfams, index=None,
                         placeholder="…o un grupo completo",
                         key="inv_buscar_subfamilia", on_change=_limpiar_producto)

    prod_sel = st.session_state.get("inv_buscar_producto")
    subfam_sel = st.session_state.get("inv_buscar_subfamilia") if col_subfam else None

    if not prod_sel and not subfam_sel:
        st.info("Buscá un producto o elegí un grupo para ver cuánto hay y en qué área.")
        return

    if prod_sel:
        _ficha_producto(d, prod_sel, col_prod, col_area, col_val, col_cant, col_unidad)
    else:
        _ficha_subfamilia(d, subfam_sel, col_subfam, col_prod, col_area,
                          col_val, col_cant, col_unidad)


def _panel_relacionados(d, col_prod, col_fam, col_subfam, col_val):
    """Panel lateral de Buscar producto: en vez de repetir el top-10
    genérico (redundante con la ficha que ya está a la izquierda), muestra
    otros productos de la misma subfamilia/familia que el seleccionado."""
    prod_sel = st.session_state.get("inv_buscar_producto")
    subfam_sel = st.session_state.get("inv_buscar_subfamilia") if col_subfam else None
    col_grp = col_subfam or col_fam
    etiqueta = "subfamilia" if col_subfam else "familia"

    if prod_sel and col_grp:
        fila = d[d[col_prod].astype(str) == prod_sel]
        grupo_val = (str(fila[col_grp].dropna().iloc[0])
                     if not fila.empty and fila[col_grp].notna().any() else None)
        if not grupo_val:
            st.caption("Sin más contexto disponible.")
            return
        st.markdown(f"**Otros productos de la misma {etiqueta}**")
        st.caption(grupo_val)
        dd = d[(d[col_grp].astype(str) == grupo_val) & (d[col_prod].astype(str) != prod_sel)]
        _v = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
        serie = _v.groupby(dd[col_prod].astype(str)).sum().nlargest(8).sort_values()
        if serie.empty:
            st.info("No hay más productos en este grupo.")
        else:
            fig = go.Figure(go.Bar(
                x=serie.values, y=[_compras_truncar(i, 24) for i in serie.index],
                orientation="h", marker=dict(color=ACENTO, opacity=0.85),
                text=[f"S/ {v:,.0f}" for v in serie.values],
                textposition="outside", cliponaxis=False,
            ))
            fig.update_layout(
                height=400, margin=dict(l=4, r=60, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
            )
            fig.update_xaxes(visible=False, range=_rango_con_holgura(serie.values))
            st.plotly_chart(fig, use_container_width=True, key="inv_relacionados")
    elif subfam_sel:
        st.caption("Todos los productos del grupo ya están a la izquierda, "
                   "con su desglose por área.")
    else:
        st.caption("Elegí un producto o un grupo para ver contexto relacionado acá.")


def renderizar_graficos_inventario(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Inventario Valorizado: KPIs + 3 vistas + panel lateral.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py). Se le
    pasa `d` — el df ya filtrado por los chips propios (Área/Familia) —
    igual que Ventas, para no tener un estado de filtros distinto entre
    Tabla y gráficos."""
    col_area   = _resolver(df_f, ["Nombre Area", "NOMBRE AREA", "Area"])
    col_fam    = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_subfam = _resolver(df_f, ["Nombre Subfamilia", "NOMBRE SUBFAMILIA", "Subfamilia"])
    col_prod   = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_cant   = _resolver(df_f, ["Stock al Dia", "Stock al dia", "STOCK AL DIA",
                                  "Cantidad", "Stock"])
    col_val    = _resolver(df_f, ["Valorizado total", "VALORIZADO TOTAL",
                                  "Valorizado"])
    col_punit  = _resolver(df_f, ["Precio Promedio", "PRECIO PROMEDIO", "Precio"])
    col_unidad = _resolver(df_f, ["Unidad Kardex", "UNIDAD KARDEX",
                                  "Unidad Medida", "Unidad"])

    if not col_val:
        st.warning("No se encontró la columna de valorizado. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Área / Familia como chips en la FRANJA blanca ────────────
    area_sel, fam_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if col_area:
                areas = sorted(df_f[col_area].dropna().astype(str).unique().tolist())
                if areas:
                    _n = len(st.session_state.get("inv_graf_filtro_area") or [])
                    _lbl = f":material/filter_alt: Área :violet-badge[{_n}]" if _n else ":material/filter_alt: Área"
                    with st.popover(_lbl, use_container_width=True):
                        area_sel = st.pills(
                            "Área", areas, selection_mode="multi",
                            key="inv_graf_filtro_area",
                            label_visibility="collapsed",
                        ) or []
        with c2:
            if col_fam:
                fams = sorted(df_f[col_fam].dropna().astype(str).unique().tolist())
                if fams:
                    _n = len(st.session_state.get("inv_graf_filtro_fam") or [])
                    _lbl = f":material/category: Familia :violet-badge[{_n}]" if _n else ":material/category: Familia"
                    with st.popover(_lbl, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia", fams, selection_mode="multi",
                            key="inv_graf_filtro_fam",
                            label_visibility="collapsed",
                        ) or []

    d = df_f
    if area_sel and col_area:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Inventario Valorizado", d,
                         {"Área": area_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _val  = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    _cant = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
             if col_cant else None)

    graf = _render_rail(_INVENTARIO_RAIL_CATEGORIAS, "inv_graf_tipo",
                        btn_prefix="inv_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            tabla_cb(d)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    col_izq, col_der = st.columns([1.7, 1])

    col_grp, foco = None, None
    with col_izq:
        with st.container(border=True, key="ajuste_graf_card_izq_inv"):
            st.metric("Valorizado total", f"S/ {_val.sum():,.0f}")

            if graf in ("Por área", "Por familia") and (col_area or col_fam):
                col_grp = col_area if graf == "Por área" else col_fam
                nombre_grp = "área" if graf == "Por área" else "familia"
                if not col_grp:
                    st.info(f"No se encontró la columna de {nombre_grp}.")
                else:
                    _state_key = f"inv_focus_{'area' if graf == 'Por área' else 'familia'}"
                    foco = _grafico_ranking(
                        d, col_grp, col_val, f"Valorizado por {nombre_grp}",
                        key=f"inv_g_{'area' if graf == 'Por área' else 'familia'}",
                        clic=True, state_key=_state_key,
                    )
                    if foco:
                        st.caption(f"📍 **{foco}** · panel derecho filtrado")
                        _grafico_detalle_foco(d, graf, col_grp, foco,
                                              col_fam, col_subfam, col_val)

            elif graf == "Buscar producto":
                _render_buscar_producto(d, col_prod, col_area, col_subfam,
                                        col_val, col_cant, col_unidad)

            else:
                st.info("No hay columnas suficientes para este gráfico.")

    with col_der:
        with st.container(border=True, key="ajuste_graf_card_der_inv"):
            if graf == "Buscar producto":
                _panel_relacionados(d, col_prod, col_fam, col_subfam, col_val)
            else:
                d_panel = d[d[col_grp].astype(str) == foco] if foco else d
                _cant_panel = _cant.loc[d_panel.index] if _cant is not None else None
                if foco:
                    st.caption(f"Top de **{foco}**.")
                tabs = st.tabs(["Mayor cantidad", "Precio más alto"])
                with tabs[0]:
                    if col_prod and _cant_panel is not None and col_area:
                        g = (pd.DataFrame({"prod": d_panel[col_prod].astype(str),
                                           "area": d_panel[col_area].astype(str),
                                           "cant": _cant_panel})
                             .groupby(["prod", "area"], as_index=False)["cant"].sum()
                             .nlargest(10, "cant").sort_values("cant"))
                        if g.empty:
                            st.info("Sin datos.")
                        else:
                            fig = go.Figure(go.Bar(
                                x=g["cant"],
                                y=[_compras_truncar(p_, 24) for p_ in g["prod"]],
                                orientation="h",
                                marker=dict(color=ACENTO, opacity=0.85),
                                text=[_compras_truncar(a_, 14) for a_ in g["area"]],
                                textposition="outside", cliponaxis=False,
                                customdata=g["area"],
                                hovertemplate=("%{y}<br>Área: %{customdata}"
                                               "<br>Cantidad: %{x:,.1f}<extra></extra>"),
                            ))
                            fig.update_layout(
                                height=400, margin=dict(l=4, r=60, t=10, b=10),
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(family="DM Sans, sans-serif",
                                          color=TEXTO_PRINCIPAL, size=11),
                            )
                            fig.update_xaxes(visible=False)
                            st.plotly_chart(fig, use_container_width=True,
                                            key="inv_mini_cant")
                    else:
                        st.info("Faltan columnas de cantidad o área.")
                with tabs[1]:
                    if col_prod and col_punit and col_area:
                        _pu = pd.to_numeric(d_panel[col_punit], errors="coerce")
                        g = (pd.DataFrame({"prod": d_panel[col_prod].astype(str),
                                           "area": d_panel[col_area].astype(str),
                                           "pu": _pu,
                                           "cant": (_cant_panel if _cant_panel is not None
                                                    else pd.Series(0, index=d_panel.index))})
                             .dropna(subset=["pu"])
                             .groupby(["prod", "area"], as_index=False)
                             .agg(pu=("pu", "mean"), cant=("cant", "sum"))
                             .nlargest(10, "pu").sort_values("pu"))
                        if g.empty:
                            st.info("Sin datos.")
                        else:
                            fig = go.Figure(go.Bar(
                                x=g["pu"],
                                y=[_compras_truncar(p_, 24) for p_ in g["prod"]],
                                orientation="h",
                                marker=dict(color=ACENTO, opacity=0.85),
                                text=[f"S/ {v:,.1f}" for v in g["pu"]],
                                textposition="outside", cliponaxis=False,
                                customdata=np.stack([g["area"], g["cant"]], axis=-1),
                                hovertemplate=("%{y}<br>Área: %{customdata[0]}"
                                               "<br>Precio: S/ %{x:,.2f}"
                                               "<br>Cantidad: %{customdata[1]:,.1f}"
                                               "<extra></extra>"),
                            ))
                            fig.update_layout(
                                height=400, margin=dict(l=4, r=60, t=10, b=10),
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(family="DM Sans, sans-serif",
                                          color=TEXTO_PRINCIPAL, size=11),
                            )
                            fig.update_xaxes(visible=False)
                            st.plotly_chart(fig, use_container_width=True,
                                            key="inv_mini_precio")
                    else:
                        st.info("Faltan columnas de precio o área.")
