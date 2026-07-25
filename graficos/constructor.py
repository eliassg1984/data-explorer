"""
graficos.constructor — constructor de gráficos estilo Power BI (config por el usuario).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


from tema import ACENTO, ESCALA_CONTINUA
from graficos.base import PALETA_CALLAI, _compras_layout

def _constructor_grafico(d, key_prefix="compras"):
    """Panel donde el usuario arma su propio gráfico: elige tipo, dimensión,
    métrica, agregación, agrupación, top-N y orden. Hace su propia
    agregación (sum/mean/count/min/max) y construye la figura Plotly."""
    cols_num = d.select_dtypes("number").columns.tolist()
    cols_txt = d.select_dtypes(["object", "string"]).columns.tolist()
    cols_fecha = [c for c in d.columns
                  if pd.api.types.is_datetime64_any_dtype(d[c])]
    dims = cols_txt + cols_fecha
    if not dims or not cols_num:
        st.info("No hay columnas suficientes para construir gráficos.")
        return

    TIPOS = ["Barras", "Barras horizontales", "Barras apiladas", "Líneas",
             "Área", "Torta", "Dispersión", "Treemap", "Mapa de calor"]
    AGG = {"Suma": "sum", "Promedio": "mean", "Conteo": "count",
           "Mínimo": "min", "Máximo": "max"}

    st.caption("🔧 Arma tu propio gráfico: combina tipo, dimensión, métrica "
               "y agregación. Los filtros de la franja también aplican.")

    r1 = st.columns([1.2, 1.3, 1.3, 1])
    with r1[0]:
        tipo = st.selectbox("Tipo de gráfico", TIPOS, key=f"{key_prefix}_cb_tipo")
    es_scatter = (tipo == "Dispersión")
    with r1[1]:
        dim_opts = cols_num if es_scatter else dims
        dim = st.selectbox(
            "Eje X" if es_scatter else "Dimensión (eje X)", dim_opts,
            key=f"{key_prefix}_cb_dim",
            format_func=lambda c: (f"{c} (por mes)" if c in cols_fecha else c),
        )
    with r1[2]:
        if es_scatter:
            medida = st.selectbox("Eje Y (numérico)", cols_num,
                                  key=f"{key_prefix}_cb_medy")
            agg, agg_lbl, conteo = "sum", "", False
        else:
            medida = st.selectbox("Métrica (eje Y)",
                                  ["(conteo de filas)"] + cols_num,
                                  key=f"{key_prefix}_cb_med")
            conteo = (medida == "(conteo de filas)")
    with r1[3]:
        if es_scatter or conteo:
            st.selectbox("Agregación", ["—"], disabled=True,
                         key=f"{key_prefix}_cb_agg_off")
            agg, agg_lbl = "sum", "Conteo" if conteo else ""
        else:
            agg_lbl = st.selectbox("Agregación", list(AGG.keys()),
                                   key=f"{key_prefix}_cb_agg")
            agg = AGG[agg_lbl]

    r2 = st.columns([1.4, 1, 1, 1.4])
    with r2[0]:
        _2dim_obligatoria = (tipo == "Mapa de calor")
        _ops_color = [c for c in cols_txt if c != dim]
        _label = "2ª dimensión (obligatoria)" if _2dim_obligatoria else "Agrupar / color"
        color_sel = st.selectbox(
            _label, (["(ninguna)"] if not _2dim_obligatoria else []) + _ops_color,
            key=f"{key_prefix}_cb_color") if _ops_color or not _2dim_obligatoria else None
    with r2[1]:
        topn = st.selectbox("Top N", ["Todos", 5, 10, 15, 20, 30],
                            index=2, key=f"{key_prefix}_cb_top")
    with r2[2]:
        orden = st.selectbox("Orden", ["Por valor", "Alfabético"],
                             key=f"{key_prefix}_cb_orden")
    with r2[3]:
        titulo = st.text_input("Título (opcional)", key=f"{key_prefix}_cb_titulo")

    etiquetas = st.toggle("Etiquetas de datos", key=f"{key_prefix}_cb_etq")
    color = None if (not color_sel or color_sel == "(ninguna)") else color_sel

    # ── Dispersión: puntos crudos, sin agregación ───────────────────────
    if es_scatter:
        if dim == medida:
            st.info("Elige columnas distintas para el eje X y el eje Y.")
            return
        _cols = list(dict.fromkeys([dim, medida] + ([color] if color else [])))
        dd = d[_cols].copy()
        dd[dim] = pd.to_numeric(dd[dim], errors="coerce")
        dd[medida] = pd.to_numeric(dd[medida], errors="coerce")
        dd = dd.dropna(subset=[dim, medida])
        if len(dd) > 5000:
            dd = dd.sample(5000, random_state=0)
        if dd.empty:
            st.info("Sin datos numéricos para dispersar.")
            return
        fig = px.scatter(dd, x=dim, y=medida, color=color,
                         color_discrete_sequence=PALETA_CALLAI,
                         opacity=0.7)
        fig.update_traces(marker=dict(size=8))
        _compras_layout(fig, alto=520)
        fig.update_layout(title=titulo or f"{medida} vs {dim}")
        st.plotly_chart(fig, use_container_width=True,
                        key=f"{key_prefix}_cb_fig")
        return

    # ── Resto: agrega según dimensión + (opcional) color ────────────────
    dd = d.copy()
    x = dim
    if dim in cols_fecha:
        dd["_x"] = (pd.to_datetime(dd[dim], errors="coerce")
                    .dt.to_period("M").astype(str))
        x = "_x"
    grupos = [x] + ([color] if color else [])
    if conteo:
        g = dd.groupby(grupos, as_index=False).size()
        g = g.rename(columns={"size": "valor"})
    else:
        dd["_y"] = pd.to_numeric(dd[medida], errors="coerce")
        g = (dd.dropna(subset=["_y"]).groupby(grupos, as_index=False)["_y"]
             .agg(agg).rename(columns={"_y": "valor"}))
    if g.empty:
        st.info("Sin datos para esa combinación.")
        return

    # Top-N y orden sobre la dimensión X
    tot_x = g.groupby(x)["valor"].sum()
    if topn != "Todos":
        top_x = tot_x.sort_values(ascending=False).head(int(topn)).index
        g = g[g[x].isin(top_x)]
        tot_x = tot_x.loc[top_x]
    orden_x = (tot_x.sort_values(ascending=False).index.tolist()
               if orden == "Por valor"
               else sorted(g[x].astype(str).unique()))

    if not titulo:
        _m = "Conteo de filas" if conteo else f"{agg_lbl} de {medida}"
        titulo = f"{_m} por {dim}" + (f", {color}" if color else "")

    fig = None
    if tipo in ("Barras", "Barras horizontales", "Barras apiladas"):
        horizontal = (tipo == "Barras horizontales")
        fig = px.bar(
            g, x=("valor" if horizontal else x),
            y=(x if horizontal else "valor"),
            color=color, orientation=("h" if horizontal else "v"),
            barmode=("stack" if tipo == "Barras apiladas"
                     else ("group" if color else "relative")),
            color_discrete_sequence=(PALETA_CALLAI if color else [ACENTO]),
            category_orders={x: (orden_x[::-1] if horizontal else orden_x)},
        )
    elif tipo in ("Líneas", "Área"):
        fn = px.line if tipo == "Líneas" else px.area
        fig = fn(g, x=x, y="valor", color=color,
                 color_discrete_sequence=PALETA_CALLAI,
                 category_orders={x: orden_x},
                 markers=(tipo == "Líneas"))
        fig.update_xaxes(type="category")
    elif tipo == "Torta":
        gt = g.groupby(x, as_index=False)["valor"].sum()
        fig = go.Figure(go.Pie(labels=gt[x].astype(str), values=gt["valor"],
                               hole=0.4, marker=dict(colors=PALETA_CALLAI * 6)))
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(showlegend=False)
    elif tipo == "Treemap":
        path = [x] + ([color] if color else [])
        fig = px.treemap(g, path=path, values="valor",
                         color="valor", color_continuous_scale=ESCALA_CONTINUA)
    elif tipo == "Mapa de calor":
        if not color:
            st.info("El mapa de calor necesita una 2ª dimensión.")
            return
        piv = g.pivot_table(index=color, columns=x, values="valor",
                            aggfunc="sum", fill_value=0)
        fig = px.imshow(piv, aspect="auto", color_continuous_scale=ESCALA_CONTINUA,
                        labels=dict(color="Valor"))

    if fig is None:
        st.info("No se pudo construir el gráfico con esa combinación.")
        return

    _compras_layout(fig, alto=520)
    fig.update_layout(title=titulo)
    if tipo not in ("Torta", "Treemap", "Mapa de calor"):
        fig.update_layout(xaxis_title=None, yaxis_title=None)
    if etiquetas and tipo in ("Barras", "Barras horizontales",
                              "Barras apiladas", "Líneas", "Área"):
        _tt = "%{x:,.0f}" if tipo == "Barras horizontales" else "%{y:,.0f}"
        fig.update_traces(texttemplate=_tt, textposition="outside")
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_cb_fig")
