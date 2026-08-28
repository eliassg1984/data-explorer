"""
graficos.inventario — dashboard de Inventario Valorizado (v3). Layout unificado
con chips en franja blanca + card con pills.

v3 (2026-08-10) reemplaza las 4 vistas de v2 (Área y familia / Torta / Top
valor / Top cantidad) por 3: **Por área**, **Por familia** (mismo ranking
ordenado para las dos — desde 2026-08-23 una TABLA con barra de progreso en
la celda, como el Ranking de proveedores de Compras; la torta se rompía
apenas una familia concentraba >70% del total) y **Buscar producto**
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
import plotly.graph_objects as go
import streamlit as st


from tema import (
    ACENTO, AJUSTE_NEG, LAVANDA_BORDE, LAVANDA_CABECERA_GRUPO, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _compras_layout, _compras_truncar, _render_rail,
    _resolver, _slug, publicar_contexto_ia, renderizar_graficos_genericos, seccion_perezosa,
)
from graficos import alturas

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py).
_INVENTARIO_RAIL_CATEGORIAS = (
    ("Vista", (("Por área",        "Por área"),
               ("Por familia",     "Por familia"),
               ("Buscar producto", "Buscar producto"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué, largo, está en `graficos/compras/__init__.py::_PILA`).
# Las cuatro vistas de Inventario comparten el mismo rango de fecha, así
# que a diferencia de Ajuste acá va UNA sola pila con todo adentro.
_PILA = (
    ("inv_sec_area",    "Por área"),
    ("inv_sec_familia", "Por familia"),
    ("inv_sec_buscar",  "Buscar producto"),
    ("inv_sec_tabla",   "Tabla"),
)


def _rango_con_holgura(*series, factor=0.28):
    """Rango de eje X con holgura para que el texto `outside` de la barra
    más larga no se corte contra el borde del gráfico — con `cliponaxis=
    False` Plotly no recorta en el eje, pero SÍ recorta contra el margen
    fijo de `_compras_layout` (r=10px) si la barra ya ocupa casi el 100%
    del ancho. Bug real: "Por área" con `GASTOS` en S/ 161,816 (barra al
    tope) mostraba la etiqueta cortada en "S/ 16…". `factor` más alto para
    etiquetas largas (p.ej. "S/ x · y unidad" en la ficha de un producto).

    Holgura SOLO del lado que se usa: con todo >= 0 (regla #80 — barras
    convertidas a magnitud, negativo se lee por color no por dirección)
    `lo` da 0 y no hace falta reservarle aire — eso dejaba una franja en
    blanco entre las etiquetas del eje Y y el arranque de las barras."""
    valores = [v for s in series for v in s]
    if not valores:
        return None
    lo, hi = min(0, min(valores)), max(0, max(valores))
    pad = max(abs(hi), abs(lo), 1) * factor
    return [lo - pad if lo < 0 else 0, hi + pad]


def _tabla_ranking(d, col_grp, col_val, nombre_grp, key):
    """Ranking de Por área/Por familia como TABLA con barra de progreso.

    Reemplaza (2026-08-23, a pedido) la barra horizontal de Plotly que vivía
    en esta tarjeta. Es el mismo componente que el Ranking de proveedores de
    Compras (`compras/proveedor.py`): la barra NO es un `cellRenderer` (ni la
    clase `init()/getGui()` de la regla #25, ni los sparklines de AG Grid,
    que son Enterprise) sino el FONDO de la celda, un `linear-gradient`
    cortado en el % del valor. Los colores salen de `tema.py` y no de
    `var(--accent)` a propósito: el grid vive en un iframe propio y las
    variables CSS del documento padre no llegan.

    Clic en una fila = TOGGLE del foco; devuelve la categoría elegida (o
    None) para que el caller filtre el panel derecho y muestre el detalle
    del siguiente nivel. A diferencia de `plotly_chart(on_select=...)`,
    AgGrid devuelve la selección VIGENTE en cada run —es estado, no un
    evento que se repite—, así que acá no hacen falta ni la key dinámica por
    foco ni el `st.rerun()` que evitaban el toggle infinito del gráfico."""
    from st_aggrid import AgGrid, JsCode
    from tablas._css import _css_grid

    met = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    serie = met.groupby(d[col_grp].astype(str)).sum().sort_values(ascending=False)
    if serie.empty:
        st.info("Sin datos.")
        return None

    # % sobre el total NETO — el mismo que el KPI "Valorizado total" de
    # arriba, para que sumen 100% con lo que el usuario ya está viendo (no
    # sobre la suma de absolutos).
    total = float(serie.sum())
    _mayor = float(np.abs(serie.values).max()) or 1.0
    col_nombre = nombre_grp.capitalize()
    tabla = pd.DataFrame({
        col_nombre: serie.index.astype(str),
        "Valorizado": serie.values,
        "%": [(v / total * 100) if total else 0.0 for v in serie.values],
        # Ocultas: el % de LLENADO de la barra (contra la mayor MAGNITUD, que
        # no es el mismo número que la columna "%"), y el signo — que se lee
        # por color y no por dirección, igual que en los gráficos de este
        # dashboard (regla #80). La columna visible mantiene el valor con
        # signo; sin `_neg`, un ajuste negativo pintaría una barra larga
        # indistinguible de una compra grande.
        "_barra": [abs(v) / _mayor * 100 for v in serie.values],
        "_neg": [bool(v < 0) for v in serie.values],
    })

    # La barra llega al 62% de la celda y el texto va a la DERECHA: así
    # nunca se pisan (con la barra al 100% el monto caía sobre el morado,
    # texto oscuro sobre fondo oscuro). No falsea la lectura — todas se
    # escalan igual, las proporciones entre filas se mantienen. La pista va
    # transparente, no tintada: con fondo, la columna entera se lee como un
    # bloque lavanda que compite con las barras.
    # `justifyContent` es obligatorio: el `display:flex` de esta misma regla
    # anula el alineado a la derecha que trae `type: numericColumn`.
    _js_barra = JsCode(
        "function(p){"
        " var w = Math.max(0, Math.min(100, p.data._barra||0)) * 0.62;"
        f" var c = p.data._neg ? '{AJUSTE_NEG}' : '{ACENTO}';"
        " return {'background': 'linear-gradient(90deg, ' + c + ' 0 ' + w"
        " + '%, transparent ' + w + '% 100%)',"
        " 'display':'flex','alignItems':'center','justifyContent':'flex-end',"
        f" 'color':'{TEXTO_PRINCIPAL}'"
        "};"
        "}")
    _js_soles = JsCode(
        "function(p){ return p.value==null ? '' :"
        " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' : p.value.toFixed(1) + '%'; }")
    # AG Grid, por sí solo, NO deselecciona al reclickear la fila ya
    # seleccionada (pide Ctrl+clic, que nadie descubre). `setSelected(valor,
    # true)` limpia las demás → sigue siendo selección única.
    _js_toggle = JsCode(
        "function(e){ e.node.setSelected(!e.node.isSelected(), true); }")

    resp = AgGrid(
        tabla,
        gridOptions={
            "columnDefs": [
                {"field": col_nombre, "flex": 2, "tooltipField": col_nombre},
                {"field": "Valorizado", "flex": 2, "type": "numericColumn",
                 "cellStyle": _js_barra, "valueFormatter": _js_soles},
                {"field": "%", "width": 80, "type": "numericColumn",
                 "valueFormatter": _js_pct},
                {"field": "_barra", "hide": True},
                {"field": "_neg", "hide": True},
            ],
            "rowSelection": {"mode": "singleRow", "checkboxes": False,
                             "enableClickSelection": False},
            "onRowClicked": _js_toggle,
            "rowHeight": 35,
            "headerHeight": 38,
            "suppressCellFocus": True,
            "suppressMovableColumns": True,
        },
        allow_unsafe_jscode=True,
        theme="material",
        # `_css_grid` no estila la fila SELECCIONADA, y acá esa fila ES el
        # foco del drill: sin marcarla, el usuario no ve sobre qué categoría
        # está mirando el panel de la derecha. La tabla de Documentos SUNAT
        # copia esta receta desde el 2026-08-28 (hasta ese día el comentario
        # decía que ninguna otra tabla tenía selección de fila — la tenía,
        # sin marcar, y el rayado de filas disimulaba el problema).
        custom_css={**_css_grid(12),
                    ".ag-row-selected": {
                        "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
                        "font-weight": "600 !important",
                    }},
        height=alturas.por_filas(len(serie), px_fila=35, extra=45, minimo=0,
                                 rol=alturas.APOYO),
        update_on=["selectionChanged"],
        key=key,
    )
    sel = getattr(resp, "selected_rows", None)
    if sel is None or not len(sel):
        return None
    fila = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
    return str(fila[col_nombre])


def _grafico_detalle_foco(d, graf, col_grp, foco, col_fam, col_subfam, col_val):
    """Al lado del ranking, cuando hay una categoría en foco: siguiente nivel
    de desglose del grupo elegido (Área → Familia, Familia → Subfamilia) — la
    pregunta natural después de "cuánto vale GASTOS" es "de qué se compone".
    Sin clic propio (no hay drill anidado, dos niveles alcanza) — así no
    compite con el ranking por la selección.

    Barra horizontal y no tabla, a diferencia del ranking: acá no hay nada
    que elegir, y el gráfico se lee de un vistazo en una columna angosta."""
    dd = d[d[col_grp].astype(str) == foco]
    if graf == "Por área":
        col_next, nombre_next = col_fam, "familia"
    else:
        col_next, nombre_next = col_subfam, "subfamilia"
    if not col_next or dd.empty:
        st.caption(f"Sin desglose adicional para {foco}.")
        return

    met = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
    serie = met.groupby(dd[col_next].astype(str)).sum().sort_values()
    if serie.empty:
        st.info("Sin datos.")
        return
    total = float(serie.sum())
    _texto = [
        f"S/ {v:,.0f} · {(v / total * 100):.1f}%" if total else f"S/ {v:,.0f}"
        for v in serie.values
    ]
    # Un valor negativo (ajuste/devolución) dibujado hacia la izquierda
    # descentra el gráfico: el resto de las barras arranca en x=0 y esa queda
    # flotando sola contra el margen. Mismo lado que todas (largo = magnitud)
    # pero en un color de la familia AJUSTE_NEG — el mismo que usa el heatmap
    # de Ajuste para "negativo" — así el signo se lee por color, no por
    # dirección. El texto/hover siguen con el valor real con signo.
    fig = go.Figure(go.Bar(
        x=np.abs(serie.values),
        y=[_compras_truncar(i, 30) for i in serie.index],
        orientation="h",
        marker=dict(color=[AJUSTE_NEG if v < 0 else ACENTO for v in serie.values],
                    opacity=0.85),
        text=_texto,
        textposition="outside", cliponaxis=False,
        customdata=serie.values,
        hovertemplate="%{y}<br>S/ %{customdata:,.2f}<extra></extra>",
    ))
    _compras_layout(fig, alto=alturas.por_filas(
        len(serie), px_fila=22, minimo=190, extra=50, rol=alturas.MINI))
    fig.update_layout(title=f"{foco} — por {nombre_next}")
    # Esta figura vive en col_der, angosta (~1/2.7 del ancho de la card izq):
    # el factor de holgura que alcanza en una card ancha se queda corto y la
    # etiqueta de la barra más larga se corta contra el borde (mismo bug de la
    # regla #44, con otra causa — antes era la barra al 100%, acá la columna).
    fig.update_xaxes(visible=False,
                     range=_rango_con_holgura(np.abs(serie.values), factor=3.2))
    fig.update_yaxes(showgrid=False)  # sin esto la cuadrícula de _compras_layout
    # cruza cada barra horizontal a la altura de su fila — tiene sentido en un
    # eje de VALORES, no acá donde el eje Y son nombres de categoría.
    st.plotly_chart(fig, use_container_width=True,
                    key=f"inv_g_detalle_{_slug(foco)}")


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
    # Mismo criterio que _grafico_ranking: negativo va hacia la derecha
    # como el resto (largo = magnitud), diferenciado por color en vez de
    # descentrar el gráfico dibujando hacia la izquierda.
    color = [AJUSTE_NEG if v < 0 else ACENTO for v in g["val"]]
    fig = go.Figure(go.Bar(
        x=g["val"].abs(), y=[_compras_truncar(a, 30) for a in g["area"]],
        orientation="h", marker=dict(color=color, opacity=0.85),
        text=_texto, textposition="outside", cliponaxis=False,
        customdata=np.stack([g["val"], g["cant"]], axis=-1),
        hovertemplate=("%{y}<br>Valorizado: S/ %{customdata[0]:,.2f}<br>Cantidad: "
                       "%{customdata[1]:,.1f} " + unidad + "<extra></extra>"),
    ))
    _compras_layout(fig, alto=alturas.por_filas(
        len(g), px_fila=40, minimo=320, extra=80, enmarcada=True))
    fig.update_layout(title=f"{prod_sel} — cantidad y valorizado por área")
    fig.update_xaxes(visible=False, range=_rango_con_holgura(g["val"].abs(), factor=0.35))
    fig.update_yaxes(showgrid=False)  # eje Y = nombres de área, no valores
    st.plotly_chart(fig, use_container_width=True, key="inv_g_producto")


def _ficha_subfamilia(d, subfam_sel, col_subfam, col_prod, col_area,
                       col_val, col_cant, col_unidad):
    """Todos los productos de una subfamilia — un bar por producto (sumado
    entre áreas; ya no desglosado por área — el color lo necesita el signo,
    ver abajo). Cada barra muestra precio + unidad + % de participación.
    Solo 2 KPIs (Valorizado total, Productos): Cantidad total/Precio
    promedio se sacaron a pedido — mezclaban unidades entre productos
    (kg, und, Lt) y el número agregado no representaba nada accionable.

    Negativo va a la derecha, diferenciado por color — mismo criterio que
    `_grafico_ranking`/`_ficha_producto` (regla #80). Antes esta ficha era
    la única sin ese tratamiento porque el color codificaba ÁREA (barra
    apilada); al pasar a un bar por producto, el color queda libre para
    codificar signo como en el resto del dashboard."""
    dd = d[d[col_subfam].astype(str) == subfam_sel]
    _v = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
    _c = pd.to_numeric(dd[col_cant], errors="coerce").fillna(0) if col_cant else None

    total_val = float(_v.sum())
    n_prod = dd[col_prod].nunique() if col_prod else 0

    k1, k2 = st.columns(2)
    k1.metric("Valorizado total", f"S/ {total_val:,.0f}")
    k2.metric("Productos", f"{n_prod:,}")

    if not col_prod or dd.empty:
        st.info("Sin datos para este grupo.")
        return
    base = pd.DataFrame({
        "prod": dd[col_prod].astype(str),
        "val": _v,
        "cant": _c if _c is not None else 0,
        "unidad": dd[col_unidad].astype(str) if col_unidad else "",
    })
    g = base.groupby("prod").agg(
        val=("val", "sum"), cant=("cant", "sum"),
        unidad=("unidad", lambda s: next(iter(s.dropna()), "")),
    )
    # Productos sin stock ni valorizado ("inactivos" para esta subfamilia)
    # no entran — regla #78.
    g = g[(g["val"] != 0) | (g["cant"] != 0)]
    if g.empty:
        st.info("Ningún producto de este grupo tiene stock o valorizado activo.")
        return

    _precio = np.where(g["cant"] != 0, g["val"] / g["cant"], np.nan)
    _pct = (g["val"] / total_val * 100) if total_val else pd.Series(0.0, index=g.index)
    _texto = []
    for _precio_v, _pct_v, _unidad_v in zip(_precio, _pct, g["unidad"]):
        if pd.notna(_precio_v):
            _precio_txt = (f"S/ {_precio_v:,.2f}/{_unidad_v}" if _unidad_v
                           else f"S/ {_precio_v:,.2f}")
        else:
            _precio_txt = "—"
        _texto.append(f"{_precio_txt} · {_pct_v:.1f}%")
    g["_texto"] = _texto

    # Ascendente: en un go.Bar (a diferencia del px.bar que usaba esta
    # ficha antes) el primer elemento del array `y` pinta ABAJO — mayor a
    # menor leyendo de arriba hacia abajo pide el más grande AL FINAL de
    # la lista. Mismo criterio que _grafico_ranking/_ficha_producto.
    g = g.sort_values("val", ascending=True)
    color = [AJUSTE_NEG if v < 0 else ACENTO for v in g["val"]]

    fig = go.Figure(go.Bar(
        x=np.abs(g["val"]), y=[_compras_truncar(p, 30) for p in g.index],
        orientation="h", marker=dict(color=color, opacity=0.85),
        text=g["_texto"], textposition="outside", cliponaxis=False,
        customdata=g["val"],
        hovertemplate="%{y}<br>S/ %{customdata:,.2f}<extra></extra>",
    ))
    _compras_layout(fig, alto=alturas.por_filas(
        len(g), px_fila=34, minimo=360, extra=60, enmarcada=True))
    fig.update_layout(title=f"{subfam_sel} — valorizado por producto")
    fig.update_xaxes(visible=False, range=_rango_con_holgura(np.abs(g["val"]), factor=0.5))
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
                height=alturas.APOYO, margin=dict(l=4, r=60, t=10, b=10),
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


def _panel_top(d, foco, col_grp, col_prod, col_area, col_val, col_punit, _cant):
    """Top de productos de Por área/Por familia — tabla ordenable, no un
    gráfico. Reemplaza las 2 pestañas de mini-barras (Mayor cantidad/Precio
    más alto): con columnas ordenables por header, "top por cantidad" y
    "top por precio" son el mismo componente visto con otro orden — dos
    gráficos separados eran redundantes.

    Barra de "Participación %" + checkbox con "Selección %" recalculada en
    vivo (sin rerun de Streamlit): MISMO patrón ya usado en la Tabla
    principal de este reporte (`tablas/desktop.py`, sección "Inventario
    Valorizado: 2 columnas de % + checkbox de selección") — no un
    componente nuevo, la barra-gradiente vive en `cellStyle` de AgGrid, no
    en un Styler de pandas (ver `arquitectura.md` sobre por qué acá sí
    hace falta JsCode y en `compras/volatilidad.py` no)."""
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    from tablas._css import _css_grid

    d_panel = d[d[col_grp].astype(str) == foco] if foco else d
    if foco:
        st.caption(f"Top de **{foco}**.")
    if not (col_prod and col_area and _cant is not None and col_val):
        st.info("Faltan columnas para esta tabla.")
        return

    _cant_panel = _cant.loc[d_panel.index]
    _val_panel = pd.to_numeric(d_panel[col_val], errors="coerce").fillna(0)
    _pu_panel = (pd.to_numeric(d_panel[col_punit], errors="coerce")
                if col_punit else pd.Series(np.nan, index=d_panel.index))
    base = pd.DataFrame({
        "Producto": d_panel[col_prod].astype(str),
        "Área": d_panel[col_area].astype(str),
        "Cantidad": _cant_panel.values,
        "Precio unitario": _pu_panel.values,
        "Valorizado": _val_panel.values,
    })
    g = (base.groupby(["Producto", "Área"], as_index=False)
         .agg(Cantidad=("Cantidad", "sum"), Valorizado=("Valorizado", "sum"),
              **{"Precio unitario": ("Precio unitario", "mean")}))
    if g.empty:
        st.info("Sin datos.")
        return

    # Participación % contra el total del FOCO (no solo el top mostrado) —
    # mismo criterio que el % de las barras de _grafico_ranking: sobre el
    # total neto que el usuario ya ve arriba, no sobre una suma parcial.
    _total_foco = float(_val_panel.sum())
    g["Participación %"] = ((g["Valorizado"] / _total_foco * 100)
                            if _total_foco else 0.0)
    g["Selección %"] = g["Participación %"]  # semilla; el valueGetter de abajo la recalcula en vivo
    g = g.nlargest(20, "Valorizado")

    gb = GridOptionsBuilder.from_dataframe(
        g[["Producto", "Área", "Cantidad", "Precio unitario", "Valorizado",
           "Participación %", "Selección %"]])
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    # minWidths ajustados para que las 7 entren sin scroll horizontal en la
    # franja de abajo (~911-1117px medido en vivo): con los anchos "cómodos"
    # originales (170+110+100+120+120+140+140=900px de columnas centrales)
    # quedaban ~19px cortos contra el ancho disponible real — Selección %,
    # al ser la última, quedaba virtualizada fuera de vista (ni scrolleable
    # a simple vista: parecía que la columna no existía).
    gb.configure_column("Producto", pinned="left", minWidth=150)
    gb.configure_column("Área", minWidth=90)

    _num_fmt = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined || isNaN(params.value)) return '–';
            return Number(params.value).toLocaleString('es-PE', {maximumFractionDigits: 1});
        }
    """)
    _money_fmt = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined || isNaN(params.value)) return '–';
            return 'S/ ' + Number(params.value).toLocaleString('es-PE', {maximumFractionDigits: 0});
        }
    """)
    gb.configure_column("Cantidad", type=["numericColumn"], minWidth=90,
                        valueFormatter=_num_fmt)
    gb.configure_column("Precio unitario", type=["numericColumn"], minWidth=100,
                        valueFormatter=_money_fmt)
    gb.configure_column("Valorizado", type=["numericColumn"], minWidth=110,
                        valueFormatter=_money_fmt, sort="desc")

    # Misma barra-gradiente que tablas/desktop.py::_pct_bar_style — el "–"
    # con value null cubre "Selección %" mientras no haya nada marcado
    # (Participación % siempre tiene valor).
    _pct_bar_style = JsCode(f"""
        function(params) {{
            var base = {{ textAlign: 'right', fontWeight: '500', paddingRight: '12px' }};
            if (params.value === null || params.value === undefined) return base;
            var pct = Math.max(0, Math.min(100, Number(params.value)));
            return Object.assign({{}}, base, {{
                backgroundImage: 'linear-gradient(to right, {LAVANDA_BORDE} 0%, {LAVANDA_BORDE} ' + pct + '%, transparent ' + pct + '%, transparent 100%)',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '100% 80%',
                backgroundPosition: 'left center',
            }});
        }}
    """)
    _pct_fmt = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined) return '–';
            return Number(params.value).toLocaleString('es-PE',
                { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
        }
    """)
    gb.configure_column("Participación %", minWidth=115, type=["numericColumn"],
                        cellStyle=_pct_bar_style, valueFormatter=_pct_fmt)
    gb.configure_column(
        "Selección %", minWidth=115, type=["numericColumn"],
        cellStyle=_pct_bar_style, valueFormatter=_pct_fmt,
        # Recalcula en vivo contra la suma de getSelectedNodes() — sin
        # selección, null (el formatter de arriba pinta "–").
        valueGetter=JsCode("""
            function(params) {
                if (!params.data) return null;
                var val = Number(params.data["Valorizado"]);
                if (isNaN(val)) return null;
                var nodes = (params.api && params.api.getSelectedNodes)
                    ? params.api.getSelectedNodes() : [];
                if (!nodes || nodes.length === 0) return null;
                var suma = 0;
                nodes.forEach(function(n) {
                    if (n.data) {
                        var v = Number(n.data["Valorizado"]);
                        if (!isNaN(v)) suma += v;
                    }
                });
                if (suma <= 0) return null;
                return (val / suma) * 100;
            }
        """),
    )
    gb.configure_selection("multiple", use_checkbox=True, header_checkbox=True)
    grid_options = gb.build()
    # Sin esto, la última columna ("Selección %") quedaba virtualizada
    # fuera de rango y NUNCA renderizaba celda — bug real, verificado en
    # vivo: el header aparecía pero la fila tenía un hueco vacío del ancho
    # de una columna. La grilla es chica (7 columnas, ~20 filas), así que
    # desactivar la virtualización horizontal no cuesta nada de
    # performance. Causa raíz probable: AG Grid calcula el rango visible
    # ANTES de que el iframe de Streamlit se asiente en su ancho final.
    grid_options["suppressColumnVirtualisation"] = True
    # AG Grid no sabe que un valueGetter "cambió" (no depende de ningún
    # field propio) — sin este refreshCells forzado tras cada click de
    # checkbox, "Selección %" se queda pintada con el valor anterior.
    grid_options["onSelectionChanged"] = JsCode("""
        function(params) {
            try {
                params.api.refreshCells({ columns: ['Selección %'], force: true });
            } catch(e) {}
        }
    """)

    AgGrid(
        g, gridOptions=grid_options, height=alturas.APOYO, theme="material",
        custom_css=_css_grid(12),
        allow_unsafe_jscode=True, key=f"inv_top_grid_{foco or 'global'}",
    )


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

    # El rail ya no ELIGE: con `secciones` marca dónde estás y scrollea.
    _render_rail(_INVENTARIO_RAIL_CATEGORIAS, "inv_graf_tipo",
                 btn_prefix="inv_rail_btn_", secciones=_PILA)

    # Las tres vistas de gráfico compartían UN layout de dos columnas con
    # `if graf ==` salpicado adentro, y las mismas tres keys de tarjeta
    # (`ajuste_graf_card_{izq,der,abajo}_inv`) para todas. Apiladas, eso
    # serían varios widgets con la misma key — excepción de Streamlit. Cada
    # sección pasa a ser AUTÓNOMA: arma su propio par de columnas y lleva su
    # sufijo. Se conserva el prefijo `ajuste_graf_card_`, de donde cuelga el
    # CSS de tarjeta (`estilos/_80_cards.py`).
    def _seccion_grupo(slug, graf_nombre, col_grp, nombre_grp):
        """Una de las dos vistas de ranking (Por área / Por familia).

        Las dos son el MISMO layout sobre otra columna de agrupación, que es
        lo que antes resolvía el `col_area if graf == "Por área" else
        col_fam` de adentro del bloque compartido."""
        # columnas-internas: el ranking y su panel de apoyo, dentro de la
        # sección. No es una fila de drill de Compras: COLUMNAS_DRILL no
        # aplica. Proporción heredada tal cual del layout anterior.
        col_izq, col_der = st.columns([1.7, 1])
        foco = None
        with col_izq:
            with st.container(border=True,
                              key=f"ajuste_graf_card_izq_inv_{slug}"):
                st.metric("Valorizado total", f"S/ {_val.sum():,.0f}")
                if not col_grp:
                    st.info(f"No se encontró la columna de {nombre_grp}.")
                else:
                    st.markdown(f"**Valorizado por {nombre_grp}**")
                    foco = _tabla_ranking(d, col_grp, col_val, nombre_grp,
                                          key=f"inv_rank_grid_{slug}")
                    # El detalle NO se apila acá abajo: con foco activo se
                    # dibuja lateral, en col_der — el Top que vive ahí
                    # normalmente le cede el lugar y baja a su propia
                    # franja debajo de las dos columnas.
        with col_der:
            with st.container(border=True,
                              key=f"ajuste_graf_card_der_inv_{slug}"):
                if foco:
                    _grafico_detalle_foco(d, graf_nombre, col_grp, foco,
                                          col_fam, col_subfam, col_val)
                else:
                    _panel_top(d, None, col_grp, col_prod, col_area, col_val,
                              col_punit, _cant)
        if foco:
            with st.container(border=True,
                              key=f"ajuste_graf_card_abajo_inv_{slug}"):
                _panel_top(d, foco, col_grp, col_prod, col_area, col_val,
                          col_punit, _cant)

    def _dib_area():
        _seccion_grupo("area", "Por área", col_area, "área")

    def _dib_familia():
        _seccion_grupo("familia", "Por familia", col_fam, "familia")

    def _dib_buscar():
        # columnas-internas: mismo par que las de ranking, para que las
        # tres secciones partan la fila en el mismo sitio al bajar.
        col_izq, col_der = st.columns([1.7, 1])
        with col_izq:
            with st.container(border=True, key="ajuste_graf_card_izq_inv_buscar"):
                st.metric("Valorizado total", f"S/ {_val.sum():,.0f}")
                _render_buscar_producto(d, col_prod, col_area, col_subfam,
                                        col_val, col_cant, col_unidad)
        with col_der:
            with st.container(border=True, key="ajuste_graf_card_der_inv_buscar"):
                _panel_relacionados(d, col_prod, col_fam, col_subfam, col_val)

    def _dib_tabla():
        with st.container(border=True, key="ajuste_graf_card_izq_inv_tabla"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "inv_sec_area":    _dib_area,
        "inv_sec_familia": _dib_familia,
        "inv_sec_buscar":  _dib_buscar,
        "inv_sec_tabla":   _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga (mismo bucle que Compras, Receta Base y Ajuste).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
