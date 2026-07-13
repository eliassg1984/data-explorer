"""
Dashboard de gráficos: KPIs, treemap, sunburst, scatter precio/stock,
rankings y distribución de precios.
"""

import datetime as _dt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from utils import buscar_columna, _norm
from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO,
    GRIS_FONDO, GRIS_BORDE, TEXTO_PRINCIPAL, BLANCO,
    SERIE_PRINCIPAL, PALETA_SERIES, ESCALA_CONTINUA, ESCALA_SEMAFORO,
)


# ===========================================================================
# TEMA CALLAI — paleta categórica para series múltiples
# ===========================================================================

PALETA_CALLAI = PALETA_SERIES  # alias retrocompatible; fuente en tema.py


# ===========================================================================
# HELPERS: CARD BLANCO PARA GRÁFICOS
# Uso:
#   _chart_card("Título opcional")
#   st.plotly_chart(fig, use_container_width=True)
#   _chart_card_close()
# ===========================================================================

def _chart_card(titulo: str = ""):
    """Abre un div card blanco con bordes redondeados.
    Llamar siempre seguido de _chart_card_close() después del gráfico."""
    if titulo:
        st.markdown(
            f'<div class="chart-card">'
            f'<p class="chart-card-title">{titulo}</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)


def _chart_card_close():
    """Cierra el div card abierto por _chart_card()."""
    st.markdown('</div>', unsafe_allow_html=True)


# ===========================================================================
# FUNCIÓN: DASHBOARD DE GRÁFICOS (Inventario Valorizado - NO TOCAR)
# ===========================================================================

def renderizar_graficos(df_f, es_movil=False):
    """Renderiza todos los gráficos del dashboard."""
    
    col_area = buscar_columna(df_f, "Nombre Area", "area")
    col_familia = buscar_columna(df_f, "Nombre Familia", "familia")
    col_producto = buscar_columna(df_f, "Nombre Producto", "producto")
    col_stock = buscar_columna(df_f, "Stock al dia", "stock")
    col_precio = buscar_columna(df_f, "Precio Promedio", "precio promedio")
    col_valorizado = buscar_columna(df_f, "Valorizado total", "valorizado")
    
    if not col_producto or not col_stock or not col_precio or not col_valorizado:
        st.warning("Faltan columnas esenciales (Producto, Stock, Precio, Valorizado). No se pueden generar gráficos.")
        return
    
    total_val = df_f[col_valorizado].sum()
    total_prod = len(df_f[col_producto].unique())
    stock_bajo = len(df_f[df_f[col_stock] < 10])
    stock_cero = len(df_f[df_f[col_stock] == 0])
    areas = len(df_f[col_area].unique()) if col_area else 0
    precio_prom = df_f[col_precio].mean()
    
    if es_movil:
        cols_kpi = st.columns(2)
        with cols_kpi[0]:
            st.metric("💰 Total Valorizado", f"S/ {total_val:,.0f}")
        with cols_kpi[1]:
            st.metric("📦 Productos", total_prod)
        
        cols_kpi2 = st.columns(2)
        with cols_kpi2[0]:
            st.metric("⚠️ Stock Bajo", stock_bajo, delta=f"{stock_cero} sin stock", delta_color="inverse")
        with cols_kpi2[1]:
            st.metric("💵 Precio Prom.", f"S/ {precio_prom:,.2f}")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("💰 Total Valorizado", f"S/ {total_val:,.0f}")
        with col2:
            st.metric("📦 Productos", total_prod, delta=f"{areas} áreas" if areas else None)
        with col3:
            st.metric("⚠️ Stock Bajo (<10)", stock_bajo, delta=f"{stock_cero} sin stock", delta_color="inverse")
        with col4:
            st.metric("💵 Precio Prom.", f"S/ {precio_prom:,.2f}")
        with col5:
            rotacion = total_val / total_prod if total_prod > 0 else 0
            st.metric("📊 Valor/Prod", f"S/ {rotacion:,.0f}")
    
    def crear_scatter(df, col_precio, col_stock, col_valorizado, col_producto, col_area=None, height=450):
        fig = go.Figure()
        
        valores = df[col_valorizado].fillna(0).values
        max_val = max(valores.max(), 1)
        
        if col_area:
            for area in df[col_area].unique():
                df_area = df[df[col_area] == area].copy()
                if df_area.empty:
                    continue
                
                sizes = df_area[col_valorizado].fillna(0).values
                sizes_norm = np.clip((sizes / max_val) * 35 + 5, 5, 40)
                
                fig.add_trace(go.Scatter(
                    x=df_area[col_precio],
                    y=df_area[col_stock],
                    mode='markers',
                    name=str(area),
                    marker=dict(
                        size=sizes_norm,
                        opacity=0.7,
                        sizemode='diameter'
                    ),
                    text=df_area[col_producto],
                    hovertemplate='<b>%{text}</b><br>Precio: S/ %{x:,.2f}<br>Stock: %{y:,.0f}<extra></extra>'
                ))
        else:
            sizes = df[col_valorizado].fillna(0).values
            sizes_norm = np.clip((sizes / max_val) * 35 + 5, 5, 40)
            
            fig.add_trace(go.Scatter(
                x=df[col_precio],
                y=df[col_stock],
                mode='markers',
                name='Productos',
                marker=dict(
                    size=sizes_norm,
                    opacity=0.7,
                    color=SERIE_PRINCIPAL,
                    sizemode='diameter'
                ),
                text=df[col_producto],
                hovertemplate='<b>%{text}</b><br>Precio: S/ %{x:,.2f}<br>Stock: %{y:,.0f}<extra></extra>'
            ))
        
        fig.add_hline(y=10, line_dash="dash", line_color="red", 
                     annotation_text="Stock mínimo")
        
        if not col_area and height >= 400:
            fig.add_vline(x=df[col_precio].mean(), line_dash="dash", 
                         line_color=SERIE_PRINCIPAL,
                         annotation_text=f"Precio prom. (S/ {df[col_precio].mean():.2f})")
        
        fig.update_layout(
            title='Relación Precio vs Stock (tamaño = valorizado)',
            xaxis_title='Precio Promedio (S/)',
            yaxis_title='Stock',
            height=height,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=BLANCO,
            showlegend=True if col_area else False
        )
        
        return fig
    
    if es_movil:
        tab1, tab2 = st.tabs(["🗺️ Mapa", "📊 Análisis"])
        
        with tab1:
            if col_area:
                try:
                    path = [col_area]
                    if col_familia:
                        path.append(col_familia)
                    
                    fig_tree = px.treemap(
                        df_f, path=path, values=col_valorizado,
                        color=col_valorizado, color_continuous_scale=ESCALA_CONTINUA,
                        title='Valorización por Área y Familia'
                    )
                    fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=350,
                                           paper_bgcolor="rgba(0,0,0,0)")
                    _chart_card()
                    st.plotly_chart(fig_tree, use_container_width=True)
                    _chart_card_close()
                except Exception as e:
                    st.warning(f"No se pudo generar el treemap: {str(e)}")
            else:
                st.info("Se necesita columna de Área para el treemap")
            
            with st.expander("🏆 Top 10 Productos"):
                try:
                    top_10 = df_f.nlargest(10, col_valorizado)
                    fig_top = px.bar(
                        top_10, x=col_valorizado, y=col_producto,
                        orientation='h',
                        title='Top 10 por Valorización',
                        text=col_valorizado,
                        color_discrete_sequence=[SERIE_PRINCIPAL]
                    )
                    fig_top.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                    fig_top.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)")
                    _chart_card()
                    st.plotly_chart(fig_top, use_container_width=True)
                    _chart_card_close()
                except Exception as e:
                    st.warning(f"No se pudo generar el top 10: {str(e)}")
        
        with tab2:
            try:
                fig_scatter = crear_scatter(
                    df_f, col_precio, col_stock, col_valorizado, 
                    col_producto, col_area, height=350
                )
                _chart_card()
                st.plotly_chart(fig_scatter, use_container_width=True)
                _chart_card_close()
            except Exception as e:
                st.warning(f"No se pudo generar el scatter plot: {str(e)}")
            
            if col_area:
                with st.expander("☀️ Distribución Jerárquica"):
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_sun = px.sunburst(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale=ESCALA_CONTINUA,
                            title='Distribución Jerárquica del Valor'
                        )
                        fig_sun.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)")
                        _chart_card()
                        st.plotly_chart(fig_sun, use_container_width=True)
                        _chart_card_close()
                    except Exception as e:
                        st.warning(f"No se pudo generar el sunburst: {str(e)}")
            
            with st.expander("📈 Distribución de Precios"):
                try:
                    fig_hist = px.histogram(
                        df_f, x=col_precio, nbins=20,
                        title='Distribución de Precios Promedio',
                        color_discrete_sequence=[SERIE_PRINCIPAL]
                    )
                    fig_hist.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)")
                    _chart_card()
                    st.plotly_chart(fig_hist, use_container_width=True)
                    _chart_card_close()
                except Exception as e:
                    st.warning(f"No se pudo generar el histograma: {str(e)}")
    
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗺️ Mapa de Valor", "📊 Análisis Precio/Stock",
            "🏆 Top Productos", "📈 Distribución"
        ])
        
        with tab1:
            col_a, col_b = st.columns(2)
            
            with col_a:
                if col_area:
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_tree = px.treemap(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale=ESCALA_CONTINUA,
                            title='Valorización por Área y Familia'
                        )
                        fig_tree.update_layout(margin=dict(l=10, r=10, t=30, b=10),
                                               paper_bgcolor="rgba(0,0,0,0)")
                        _chart_card()
                        st.plotly_chart(fig_tree, use_container_width=True)
                        _chart_card_close()
                    except Exception as e:
                        st.warning(f"Error en treemap: {str(e)}")
                else:
                    st.info("Se necesita columna de Área")
            
            with col_b:
                if col_area:
                    try:
                        path = [col_area]
                        if col_familia:
                            path.append(col_familia)
                        
                        fig_sun = px.sunburst(
                            df_f, path=path, values=col_valorizado,
                            color=col_valorizado, color_continuous_scale=ESCALA_CONTINUA,
                            title='Distribución Jerárquica'
                        )
                        fig_sun.update_layout(margin=dict(l=10, r=10, t=30, b=10),
                                              paper_bgcolor="rgba(0,0,0,0)")
                        _chart_card()
                        st.plotly_chart(fig_sun, use_container_width=True)
                        _chart_card_close()
                    except Exception as e:
                        st.warning(f"Error en sunburst: {str(e)}")
        
        with tab2:
            try:
                fig_scatter = crear_scatter(
                    df_f, col_precio, col_stock, col_valorizado, 
                    col_producto, col_area, height=450
                )
                _chart_card()
                st.plotly_chart(fig_scatter, use_container_width=True)
                _chart_card_close()
            except Exception as e:
                st.warning(f"Error en scatter: {str(e)}")
            
            with st.expander("🔍 Productos con stock bajo y alto valor"):
                try:
                    outliers = df_f[(df_f[col_stock] < 10) & 
                                   (df_f[col_valorizado] > df_f[col_valorizado].median())]
                    if not outliers.empty:
                        st.warning(f"⚠️ {len(outliers)} productos con stock bajo y alto valor")
                        cols_out = [col_producto, col_stock, col_valorizado]
                        if col_area:
                            cols_out.insert(1, col_area)
                        st.dataframe(
                            outliers[cols_out].sort_values(col_valorizado, ascending=False).head(10),
                            use_container_width=True
                        )
                    else:
                        st.success("✅ No hay productos críticos")
                except Exception as e:
                    st.warning(f"Error en outliers: {str(e)}")
        
        with tab3:
            col_a, col_b = st.columns(2)
            
            with col_a:
                try:
                    top_15 = df_f.nlargest(15, col_valorizado)
                    fig_top = px.bar(
                        top_15, x=col_valorizado, y=col_producto,
                        orientation='h', color=col_stock,
                        color_continuous_scale=ESCALA_SEMAFORO,
                        title='Top 15 Productos (color = stock)',
                        text=col_valorizado
                    )
                    fig_top.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                    fig_top.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)")
                    _chart_card()
                    st.plotly_chart(fig_top, use_container_width=True)
                    _chart_card_close()
                except Exception as e:
                    st.warning(f"Error en top 15: {str(e)}")
            
            with col_b:
                if col_area:
                    try:
                        area_val = df_f.groupby(col_area)[col_valorizado].sum().reset_index()
                        area_val = area_val.sort_values(col_valorizado, ascending=True)
                        
                        fig_area = px.bar(
                            area_val, x=col_valorizado, y=col_area,
                            orientation='h', color=col_valorizado,
                            color_continuous_scale=ESCALA_CONTINUA,
                            title='Ranking por Área',
                            text=col_valorizado
                        )
                        fig_area.update_traces(texttemplate='S/ %{text:,.0f}', textposition='outside')
                        fig_area.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)")
                        _chart_card()
                        st.plotly_chart(fig_area, use_container_width=True)
                        _chart_card_close()
                    except Exception as e:
                        st.warning(f"Error en ranking: {str(e)}")
        
        with tab4:
            col_a, col_b = st.columns(2)
            
            with col_a:
                try:
                    if col_area:
                        fig_box = px.box(
                            df_f, x=col_area, y=col_precio,
                            color=col_area,
                            title='Distribución de Precios por Área',
                            color_discrete_sequence=PALETA_CALLAI
                        )
                    else:
                        fig_box = px.box(
                            df_f, y=col_precio,
                            title='Distribución de Precios',
                            color_discrete_sequence=[SERIE_PRINCIPAL]
                        )
                    fig_box.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)")
                    _chart_card()
                    st.plotly_chart(fig_box, use_container_width=True)
                    _chart_card_close()
                except Exception as e:
                    st.warning(f"Error en box plot: {str(e)}")
            
            with col_b:
                try:
                    fig_hist = px.histogram(
                        df_f, x=col_precio, nbins=30,
                        title='Distribución de Precios',
                        color_discrete_sequence=[SERIE_PRINCIPAL]
                    )
                    fig_hist.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)")
                    _chart_card()
                    st.plotly_chart(fig_hist, use_container_width=True)
                    _chart_card_close()
                except Exception as e:
                    st.warning(f"Error en histograma: {str(e)}")
            
            with st.expander("📋 Resumen por Área"):
                if col_area:
                    try:
                        resumen = df_f.groupby(col_area).agg(
                            Productos=(col_producto, 'nunique'),
                            Stock_Promedio=(col_stock, 'mean'),
                            Precio_Promedio=(col_precio, 'mean'),
                            Valorizado_Total=(col_valorizado, 'sum')
                        ).reset_index()
                        resumen['% del Total'] = (resumen['Valorizado_Total'] / total_val * 100).round(1)
                        
                        st.dataframe(
                            resumen.style.format({
                                'Stock_Promedio': '{:,.0f}',
                                'Precio_Promedio': 'S/ {:.2f}',
                                'Valorizado_Total': 'S/ {:,.0f}',
                                '% del Total': '{:.1f}%'
                            }).background_gradient(subset=['Valorizado_Total'], cmap='Blues'),
                            use_container_width=True
                        )
                    except Exception as e:
                        st.warning(f"Error en resumen: {str(e)}")


# ===========================================================================
# MINI-FÁBRICA DE GRÁFICOS (config-driven)
# ===========================================================================

# paper_bgcolor = "rgba(0,0,0,0)" para que el fondo del card blanco sea el
# visible en lugar del gris de Plotly. plot_bgcolor sigue siendo BLANCO para
# la zona interior del gráfico.
_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=BLANCO,
    font_color=TEXTO_PRINCIPAL,
    font_family="DM Sans, Inter, -apple-system, sans-serif",
    margin=dict(l=20, r=20, t=50, b=20),
    height=420,
    xaxis=dict(gridcolor=GRIS_BORDE),
    yaxis=dict(gridcolor=GRIS_BORDE, tickformat=",.0f"),
)


def _layout(**overrides):
    """_LAYOUT_BASE fusionado con `overrides` (los overrides SIEMPRE ganan)."""
    base = dict(_LAYOUT_BASE)
    base.update(overrides)
    return base


def _resolver(df, candidatos):
    """Resuelve una lista de candidatos (o un string) a la columna real."""
    if candidatos is None:
        return None
    if isinstance(candidatos, str):
        candidatos = [candidatos]
    return buscar_columna(df, *candidatos)


def _preparar_datos(df, x, y, color, tipo):
    """Agrupa los datos según el tipo de gráfico. Si x es fecha, agrupa por mes."""
    if pd.api.types.is_datetime64_any_dtype(df[x]):
        df = df.copy()
        df["_mes"] = df[x].dt.to_period("M").astype(str)
        x = "_mes"

    if tipo in ("bar", "line", "area") and y:
        grupo = [x] + ([color] if color else [])
        df = df.groupby(grupo, as_index=False)[y].sum()

    return df, x


def _hover_fmt(col_y):
    """Devuelve (prefijo, formato_numero) para el valor Y del tooltip."""
    n = _norm(col_y) if col_y else ""
    if any(k in n for k in ("valorizado", "precio", "importe", "total",
                            "monto", "costo", "unitario")):
        return "S/ ", ",.2f"
    if any(k in n for k in ("stock", "cantidad", "qty", "unidades")):
        return "", ",.0f"
    return "", ",.2f"


def crear_grafico(df, conf):
    """Crea una figura Plotly desde una configuración.
    Retorna (fig, None) o (None, motivo) si falta alguna columna."""
    tipo = conf.get("tipo", "bar")

    x = _resolver(df, conf.get("x"))
    y = _resolver(df, conf.get("y"))
    color = _resolver(df, conf.get("color"))
    size = _resolver(df, conf.get("size"))

    if conf.get("x") and not x:
        return None, f"columna X no encontrada ({conf['x']})"
    if conf.get("y") and not y:
        return None, f"columna Y no encontrada ({conf['y']})"

    titulo = conf.get("titulo", f"{y} por {x}")

    try:
        if tipo == "treemap":
            path = [_resolver(df, c) for c in conf.get("path", [])]
            path = [p for p in path if p]
            if not path or not y:
                return None, "faltan columnas para el treemap"
            df_agg = df.groupby(path, as_index=False)[y].sum()
            fig = px.treemap(df_agg, path=path, values=y,
                             color=y, color_continuous_scale=ESCALA_CONTINUA, title=titulo)

        elif tipo == "scatter":
            fig = px.scatter(df, x=x, y=y, color=color, size=size, title=titulo)

        elif tipo == "histogram":
            fig = px.histogram(df, x=x, nbins=conf.get("nbins", 20), title=titulo,
                               color_discrete_sequence=[SERIE_PRINCIPAL])

        elif tipo == "box":
            fig = px.box(df, x=x, y=y, color=x if x else None, title=titulo)

        else:  # bar, line, area
            df_p, x_p = _preparar_datos(df, x, y, color, tipo)
            fn = {"bar": px.bar, "line": px.line, "area": px.area}[tipo]
            kwargs = dict(x=x_p, y=y, color=color, title=titulo)
            if tipo == "bar":
                kwargs["barmode"] = conf.get("barmode", "group" if color else "relative")
                kwargs["color_discrete_sequence"] = None if color else [SERIE_PRINCIPAL]
            if tipo == "line":
                kwargs["markers"] = True
            fig = fn(df_p, **kwargs)

        fig.update_layout(**_layout())
        if conf.get("tickangle"):
            fig.update_layout(xaxis_tickangle=conf["tickangle"])

        if tipo in ("bar", "line", "area") and y:
            _pref, _num = _hover_fmt(y)
            fig.update_traces(
                hovertemplate=f"<b>%{{x}}</b><br>{y}: {_pref}%{{y:{_num}}}<extra></extra>"
            )
            fig.update_layout(hovermode="x unified")

        if conf.get("x_categorico"):
            fig.update_xaxes(type="category")

        if conf.get("etiquetas"):
            if tipo == "bar":
                fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
            elif tipo in ("line", "area"):
                fig.update_traces(mode="lines+markers+text",
                                  texttemplate="%{y:,.0f}",
                                  textposition="top center")

        return fig, None

    except Exception as e:
        return None, str(e)


def renderizar_graficos_genericos(df_data, nombre_reporte):
    """Explorador dinámico estilo tabla dinámica."""
    cols_num = df_data.select_dtypes("number").columns.tolist()
    cols_txt = df_data.select_dtypes(["object", "string"]).columns.tolist()
    cols_fecha = [c for c in df_data.columns
                  if pd.api.types.is_datetime64_any_dtype(df_data[c])]

    opciones_x = cols_fecha + cols_txt
    if not cols_num or not opciones_x:
        st.info("No hay suficientes columnas para generar gráficos.")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        eje_x = st.selectbox(
            "📅 Eje X", opciones_x,
            format_func=lambda c: f"{c} (por mes)" if c in cols_fecha else c,
            key=f"ejex_{nombre_reporte}",
        )
    with c2:
        eje_y = st.selectbox("📊 Métrica (suma)", cols_num,
                             key=f"ejey_{nombre_reporte}")
    with c3:
        ops_color = ["(ninguna)"] + [c for c in cols_txt if c != eje_x]
        color_sel = st.selectbox("🎨 Serie (color)", ops_color,
                                 key=f"color_{nombre_reporte}")
    with c4:
        tipo_sel = st.selectbox(
            "📈 Tipo", ["Barras", "Barras apiladas", "Líneas", "Área"],
            key=f"tipo_{nombre_reporte}",
        )

    etiquetas = st.toggle("🏷️ Etiquetas de datos", key=f"etq_{nombre_reporte}")

    color = None if color_sel == "(ninguna)" else color_sel
    tipo_map = {"Barras": "bar", "Barras apiladas": "bar",
                "Líneas": "line", "Área": "area"}

    df_plot = df_data
    if eje_x in cols_txt:
        top_cats = (df_data.groupby(eje_x)[eje_y].sum()
                           .sort_values(ascending=False).head(20).index)
        df_plot = df_data[df_data[eje_x].isin(top_cats)]

    conf = {
        "tipo": tipo_map[tipo_sel], "x": eje_x, "y": eje_y, "color": color,
        "titulo": f"{eje_y} por {eje_x}" + (f" y {color}" if color else ""),
        "etiquetas": etiquetas,
    }
    if eje_x in cols_txt:
        conf["tickangle"] = -45
        conf["x_categorico"] = True

    if tipo_sel == "Barras apiladas":
        conf["barmode"] = "stack"

    fig, err = crear_grafico(df_plot, conf)
    if fig:
        fig.update_layout(height=450)
        _chart_card()
        st.plotly_chart(fig, use_container_width=True)
        _chart_card_close()
    else:
        st.warning(f"No se pudo generar el gráfico: {err}")


# =============================================================================
# HELPERS PRIVADOS — Ajuste de Inventario
# =============================================================================

def _graf_evolucion_ajuste(df, col_fecha, col_familia, col_ajuste_val, col_valorizado):
    """Serie temporal con range-selector + range-slider + eje dual opcional."""
    if not col_fecha:
        st.info("Sin columna de fecha — no se puede graficar la evolución.")
        return

    df = df.copy()
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
    df = df.dropna(subset=[col_fecha]).sort_values(col_fecha)
    if df.empty:
        st.info("Sin fechas válidas en el rango seleccionado.")
        return

    fig = go.Figure()

    if col_familia and col_familia in df.columns:
        for i, fam in enumerate(sorted(df[col_familia].dropna().unique())):
            df_fam = (df[df[col_familia] == fam]
                      .groupby(col_fecha, as_index=False)[col_ajuste_val].sum()
                      .sort_values(col_fecha))
            color = PALETA_SERIES[i % len(PALETA_SERIES)]
            fig.add_trace(go.Scatter(
                x=df_fam[col_fecha], y=df_fam[col_ajuste_val],
                name=str(fam), mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=6, symbol="circle"),
                hovertemplate=(
                    f"<b>{fam}</b><br>"
                    "Fecha: %{x|%d/%m/%Y}<br>"
                    "Ajuste: <b>S/ %{y:,.2f}</b><extra></extra>"
                ),
            ))
    else:
        agg = (df.groupby(col_fecha, as_index=False)[col_ajuste_val]
               .sum().sort_values(col_fecha))
        fig.add_trace(go.Scatter(
            x=agg[col_fecha], y=agg[col_ajuste_val],
            name="Ajuste valorizado", mode="lines+markers",
            line=dict(color=SERIE_PRINCIPAL, width=2.5),
            fill="tozeroy", fillcolor="rgba(108,92,231,0.10)",
            hovertemplate="Fecha: %{x|%d/%m/%Y}<br>Ajuste: <b>S/ %{y:,.2f}</b><extra></extra>",
        ))

    fig.add_hline(
        y=0, line_dash="dot", line_color="#ef4444", line_width=1.5,
        annotation_text="Equilibrio (0)",
        annotation_font_color="#ef4444",
        annotation_position="top right",
    )

    fig.update_layout(**_layout(
        title="Evolución del ajuste valorizado",
        xaxis=dict(
            gridcolor=GRIS_BORDE,
            rangeselector=dict(
                buttons=[
                    dict(count=1,  label="1M",  step="month", stepmode="backward"),
                    dict(count=3,  label="3M",  step="month", stepmode="backward"),
                    dict(count=6,  label="6M",  step="month", stepmode="backward"),
                    dict(step="all", label="Todo"),
                ],
                bgcolor=GRIS_FONDO, activecolor=ACENTO,
                font=dict(size=12),
            ),
            rangeslider=dict(visible=True, thickness=0.06, bgcolor=GRIS_FONDO),
            type="date",
        ),
        yaxis=dict(gridcolor=GRIS_BORDE, tickprefix="S/ ", tickformat=",.2f"),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
    ))

    _chart_card("Evolución temporal")
    st.plotly_chart(fig, use_container_width=True)
    _chart_card_close()

    if col_valorizado and col_valorizado in df.columns:
        with st.expander("📊 Comparativa: ajuste vs valorizado total (eje dual)"):
            agg2 = (df.groupby(col_fecha, as_index=False)
                    .agg(ajuste=(col_ajuste_val, "sum"), val=(col_valorizado, "sum"))
                    .sort_values(col_fecha))

            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            fig2.add_trace(go.Bar(
                x=agg2[col_fecha], y=agg2["ajuste"],
                name="Ajuste valorizado",
                marker_color=[SERIE_PRINCIPAL if v >= 0 else "#ef4444"
                              for v in agg2["ajuste"]],
                hovertemplate="Ajuste: S/ %{y:,.2f}<extra></extra>",
            ), secondary_y=False)
            fig2.add_trace(go.Scatter(
                x=agg2[col_fecha], y=agg2["val"],
                name="Valorizado total",
                mode="lines+markers",
                line=dict(color="#16a34a", width=2.5),
                hovertemplate="Valorizado: S/ %{y:,.2f}<extra></extra>",
            ), secondary_y=True)

            fig2.update_layout(**_layout(
                title="Ajuste vs Valorizado total",
                hovermode="x unified",
                legend=dict(orientation="h", y=1.05, x=0),
            ))
            fig2.update_yaxes(
                tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE,
                title_text="Ajuste valorizado", secondary_y=False,
            )
            fig2.update_yaxes(
                tickprefix="S/ ", tickformat=",.2f",
                title_text="Valorizado total", secondary_y=True,
            )
            _chart_card()
            st.plotly_chart(fig2, use_container_width=True)
            _chart_card_close()


def _graf_comparativa_mensual(df, col_fecha, col_ajuste_val):
    """Barras de ajuste total por mes (positivo lavanda, negativo rojo).
    Pensada para la pestaña Histórico: da una lectura rápida de qué meses
    tuvieron sobrante o faltante neto sin necesidad de leer la línea."""
    if not col_fecha:
        st.info("Sin columna de fecha para la comparativa mensual.")
        return

    d = df.copy()
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=[col_fecha])
    if d.empty:
        st.info("Sin fechas válidas para la comparativa mensual.")
        return

    d["_mes"] = d[col_fecha].dt.to_period("M").dt.to_timestamp()
    agg = d.groupby("_mes", as_index=False)[col_ajuste_val].sum().sort_values("_mes")

    fig = go.Figure(go.Bar(
        x=agg["_mes"], y=agg[col_ajuste_val],
        marker_color=[SERIE_PRINCIPAL if v >= 0 else "#ef4444"
                      for v in agg[col_ajuste_val]],
        text=[f"S/ {v:,.0f}" for v in agg[col_ajuste_val]],
        textposition="outside",
        hovertemplate="%{x|%b %Y}<br><b>S/ %{y:,.2f}</b><extra></extra>",
    ))
    fig.update_layout(**_layout(
        title="Ajuste valorizado total por mes",
        xaxis=dict(dtick="M1", tickformat="%b %Y", gridcolor=GRIS_BORDE),
        yaxis=dict(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE),
        showlegend=False, height=440,
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=GRIS_BORDE, line_width=1)

    _chart_card("Comparativa mensual")
    st.plotly_chart(fig, use_container_width=True)
    _chart_card_close()


def _graf_waterfall_ajuste(df, col_familia, col_area, col_ajuste_val):
    """Cascada (Waterfall) por familia + tabla top faltantes/sobrantes."""
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para el gráfico de cascada.")
        return

    agg = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
           .sum().sort_values(col_ajuste_val))
    total = float(agg[col_ajuste_val].sum())

    col_chart, col_tabla = st.columns([2, 1])

    with col_chart:
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative"] * len(agg) + ["total"],
            x=agg[grp_col].tolist() + ["TOTAL"],
            y=agg[col_ajuste_val].tolist() + [None],
            text=[f"S/ {v:,.0f}" for v in agg[col_ajuste_val]] + [f"S/ {total:,.0f}"],
            textposition="outside",
            connector=dict(line=dict(color=GRIS_BORDE, width=1, dash="dot")),
            increasing=dict(marker=dict(color="rgba(108,92,231,0.85)")),
            decreasing=dict(marker=dict(color="rgba(239,68,68,0.85)")),
            totals=dict(marker=dict(
                color=ACENTO_TEXTO_OSCURO if total >= 0 else "#ef4444"
            )),
            hovertemplate="%{x}<br><b>S/ %{y:,.2f}</b><extra></extra>",
        ))
        fig.update_layout(**_layout(
            title=f"Cascada de ajuste valorizado por {grp_col}",
            xaxis=dict(tickangle=-35, gridcolor=GRIS_BORDE),
            yaxis=dict(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE),
            showlegend=False, height=480,
        ))
        _chart_card("Cascada por familia")
        st.plotly_chart(fig, use_container_width=True)
        _chart_card_close()

    with col_tabla:
        st.markdown("**📉 Top 5 faltantes**")
        neg = agg.nsmallest(5, col_ajuste_val)[[grp_col, col_ajuste_val]].copy()
        neg[col_ajuste_val] = neg[col_ajuste_val].map(lambda v: f"S/ {v:,.2f}")
        st.dataframe(neg, hide_index=True, use_container_width=True)

        st.markdown("**📈 Top 5 sobrantes**")
        pos = agg.nlargest(5, col_ajuste_val)[[grp_col, col_ajuste_val]].copy()
        pos[col_ajuste_val] = pos[col_ajuste_val].map(lambda v: f"S/ {v:,.2f}")
        st.dataframe(pos, hide_index=True, use_container_width=True)


def _graf_heatmap_ajuste(df, col_familia, col_area, col_ajuste_val):
    """Mapa de calor familia × área con escala divergente centrada en cero."""
    if not col_familia or not col_area:
        st.info("Se necesitan columnas de familia y área para el mapa de calor.")
        return

    pivot = df.pivot_table(
        index=col_familia, columns=col_area,
        values=col_ajuste_val, aggfunc="sum", fill_value=0,
    )
    text_mat = [[f"S/ {v:,.0f}" for v in row] for row in pivot.values]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        text=text_mat,
        texttemplate="%{text}",
        textfont=dict(size=10, color=TEXTO_PRINCIPAL),
        colorscale=[
            [0.0,  "#ef4444"],
            [0.45, "#fff7ed"],
            [0.5,  GRIS_FONDO],
            [0.55, "#f0fdf4"],
            [1.0,  "#16a34a"],
        ],
        zmid=0,
        colorbar=dict(title="Ajuste S/", tickformat=",.0f"),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Área: <b>%{x}</b><br>"
            "Ajuste: <b>S/ %{z:,.2f}</b><extra></extra>"
        ),
    ))
    fig.update_layout(**_layout(
        title="Mapa de calor: ajuste valorizado por Familia × Área",
        xaxis=dict(tickangle=-30, side="bottom", gridcolor=GRIS_BORDE),
        yaxis=dict(autorange="reversed", gridcolor=GRIS_BORDE),
        height=max(380, len(pivot.index) * 42 + 120),
    ))

    _chart_card("Mapa de calor")
    st.plotly_chart(fig, use_container_width=True)
    _chart_card_close()

    with st.expander("📋 Tabla pivot Familia × Área"):
        st.dataframe(
            pivot.style
                 .format("S/ {:,.2f}")
                 .background_gradient(
                     cmap="RdYlGn", axis=None,
                     vmin=float(pivot.values.min()),
                     vmax=float(pivot.values.max()),
                 ),
            use_container_width=True,
        )


def _graf_distribucion_ajuste(df, col_familia, col_area, col_ajuste_val, col_producto):
    """Box plot con outliers visibles + histograma con líneas estadísticas."""
    col_izq, col_der = st.columns(2)
    grp = col_familia or col_area

    with col_izq:
        if grp and grp in df.columns:
            fig = px.box(
                df, x=grp, y=col_ajuste_val, color=grp,
                color_discrete_sequence=PALETA_SERIES,
                title=f"Distribución del ajuste por {grp}",
                points="outliers",
                labels={col_ajuste_val: "Ajuste S/", grp: ""},
            )
            fig.add_hline(y=0, line_dash="dash", line_color="#ef4444",
                          annotation_text="Cero", annotation_position="top right")
            fig.update_layout(**_layout(
                showlegend=False,
                xaxis=dict(tickangle=-30, gridcolor=GRIS_BORDE),
                yaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
            ))
            fig.update_traces(hovertemplate="%{x}<br>S/ %{y:,.2f}<extra></extra>")
        else:
            fig = px.histogram(
                df, x=col_ajuste_val, nbins=30,
                title="Distribución de ajustes valorizados",
                color_discrete_sequence=[SERIE_PRINCIPAL],
            )
            fig.add_vline(x=0, line_dash="dash", line_color="#ef4444",
                          annotation_text="Cero")
            fig.update_layout(**_layout(
                xaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE),
                yaxis=dict(gridcolor=GRIS_BORDE),
            ))
        _chart_card("Distribución por grupo")
        st.plotly_chart(fig, use_container_width=True)
        _chart_card_close()

    with col_der:
        media   = float(df[col_ajuste_val].mean())
        mediana = float(df[col_ajuste_val].median())

        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=df[col_ajuste_val], nbinsx=30,
            name="Frecuencia",
            marker_color=SERIE_PRINCIPAL, opacity=0.75,
            hovertemplate="Valor: S/ %{x:,.2f}<br>Frecuencia: %{y}<extra></extra>",
        ))
        fig2.add_vline(x=0, line_dash="solid", line_color="#ef4444", line_width=2,
                       annotation_text="Cero", annotation_font_color="#ef4444")
        fig2.add_vline(x=media, line_dash="dot", line_color="#f97316",
                       annotation_text=f"Media S/ {media:,.0f}",
                       annotation_font_color="#f97316",
                       annotation_position="top left")
        fig2.add_vline(x=mediana, line_dash="dash", line_color="#16a34a",
                       annotation_text=f"Mediana S/ {mediana:,.0f}",
                       annotation_font_color="#16a34a")
        fig2.update_layout(**_layout(
            title="Histograma de frecuencias",
            xaxis=dict(tickprefix="S/ ", tickformat=",.2f", gridcolor=GRIS_BORDE,
                       title="Ajuste Valorizado"),
            yaxis=dict(title="Frecuencia", gridcolor=GRIS_BORDE),
            hovermode="x",
        ))
        _chart_card("Histograma")
        st.plotly_chart(fig2, use_container_width=True)
        _chart_card_close()

    if col_producto and col_producto in df.columns:
        umbral = float(df[col_ajuste_val].quantile(0.05))
        outliers = df[df[col_ajuste_val] <= umbral].copy()
        if not outliers.empty:
            st.markdown(
                f"**⚠️ Productos en el 5% inferior del ajuste "
                f"(< S/ {umbral:,.2f})**"
            )
            cols_tabla = [col_producto, col_ajuste_val]
            for c in (grp,):
                if c and c in outliers.columns and c not in cols_tabla:
                    cols_tabla.append(c)
            out_df = (outliers[cols_tabla]
                      .sort_values(col_ajuste_val)
                      .head(10)
                      .copy())
            out_df[col_ajuste_val] = out_df[col_ajuste_val].map(
                lambda v: f"S/ {v:,.2f}"
            )
            st.dataframe(out_df, hide_index=True, use_container_width=True)


# =============================================================================
# FUNCIÓN PÚBLICA — Ajuste de Inventario
# =============================================================================

def renderizar_graficos_ajuste(df_f, nombre_reporte, df_full=None):
    """
    Gráficos de Ajuste de Inventario (rediseño sin KPIs).

    Estructura:
      · Selector de ámbito: «Del periodo» / «Histórico» (segmented control).
      · Chips (st.pills) para elegir el gráfico dentro del ámbito.
      · Chips de filtro rápido por Familia (aplican al ámbito activo).
      · «Del periodo»  → usa df_f (respeta el rango del popover):
            Cascada, Mapa de calor, Distribución.
      · «Histórico»    → usa df_full acotado al AÑO ACTUAL (ignora el rango
            del popover): Evolución temporal, Comparativa mensual.
      · Expander final: Explorador libre de gráficos.

    Nota: df_full es opcional; si no se pasa, se usa df_f también para
    Histórico (compatibilidad con llamadas antiguas).
    """
    col_fecha      = _resolver(df_f, ["FECHA APERTURA INVENTARIO", "FECHA", "MES"])
    col_familia    = _resolver(df_f, ["FAMILIA", "Nombre Familia", "NOMBRE FAMILIA"])
    col_area       = _resolver(df_f, ["AREA", "Nombre Area", "NOMBRE AREA"])
    col_ajuste_val = _resolver(df_f, ["AJUSTE VALORIZADO", "AJUSTEVALORIZADO"])
    col_valorizado = _resolver(df_f, ["VALORIZADO TOTAL", "VALORIZADO", "VALORIZADOTOTAL"])
    col_producto   = _resolver(df_f, ["NOMBRE PRODUCTO", "PRODUCTO", "DESCRIPCION"])

    if not col_ajuste_val:
        st.warning(
            "No se encontró la columna de ajuste valorizado. "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Selector de ámbito: Del periodo / Histórico ──────────────────────
    ambito = st.segmented_control(
        "Ámbito",
        ["Del periodo", "Histórico"],
        default="Del periodo",
        key="ajuste_graf_ambito",
        label_visibility="collapsed",
    )
    if not ambito:
        ambito = "Del periodo"

    # ── Datos según ámbito ───────────────────────────────────────────────
    if ambito == "Histórico":
        base = df_full if df_full is not None else df_f
        anio_actual = _dt.date.today().year
        if col_fecha and col_fecha in base.columns:
            _f = pd.to_datetime(base[col_fecha], errors="coerce")
            base = base[_f.dt.year == anio_actual]
        d = base
        st.caption(
            f"📆 Vista histórica del año {anio_actual}. "
            "El rango de fechas del popover no aplica aquí."
        )
    else:
        d = df_f

    # ── Chips de filtro rápido por Familia (opcional) ────────────────────
    if col_familia and col_familia in d.columns:
        familias = sorted(d[col_familia].dropna().astype(str).unique().tolist())
        if familias:
            fam_sel = st.pills(
                "Familia",
                familias,
                selection_mode="multi",
                key=f"ajuste_graf_fam_{ambito}",
                label_visibility="collapsed",
            )
            if fam_sel:
                d = d[d[col_familia].astype(str).isin(fam_sel)]

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # ── Chips selectores de gráfico ──────────────────────────────────────
    if ambito == "Histórico":
        opciones = ["📅 Evolución", "📊 Comparativa mensual"]
    else:
        opciones = ["🏗️ Cascada", "🔥 Mapa de calor", "📦 Distribución"]

    graf = st.pills(
        "Gráfico",
        opciones,
        default=opciones[0],
        key=f"ajuste_graf_tipo_{ambito}",
        label_visibility="collapsed",
    )
    if not graf:
        graf = opciones[0]

    # ── Render del gráfico elegido (solo uno por rerun) ──────────────────
    if graf == "📅 Evolución":
        _graf_evolucion_ajuste(d, col_fecha, col_familia,
                               col_ajuste_val, col_valorizado)
    elif graf == "📊 Comparativa mensual":
        _graf_comparativa_mensual(d, col_fecha, col_ajuste_val)
    elif graf == "🏗️ Cascada":
        _graf_waterfall_ajuste(d, col_familia, col_area, col_ajuste_val)
    elif graf == "🔥 Mapa de calor":
        _graf_heatmap_ajuste(d, col_familia, col_area, col_ajuste_val)
    elif graf == "📦 Distribución":
        _graf_distribucion_ajuste(d, col_familia, col_area,
                                  col_ajuste_val, col_producto)

    with st.expander("🎛️ Explorador libre de gráficos"):
        renderizar_graficos_genericos(d, nombre_reporte)


def renderizar_graficos_reporte(df_f, reporte, cfg, df_full=None):
    """Punto de entrada de la vista Gráficos para reportes genéricos.

    df_full: opcional, DataFrame sin el filtro de fecha aplicado. Ajuste de
    Inventario lo usa para su pestaña Histórico (año actual completo).
    Reportes genéricos lo ignoran.
    """
    if reporte == "Ajuste de Inventario":
        renderizar_graficos_ajuste(df_f, reporte, df_full=df_full)
        return

    graficos_conf = cfg.get("graficos", [])

    if graficos_conf:
        omitidos = []
        for conf in graficos_conf:
            fig, err = crear_grafico(df_f, conf)
            if fig:
                _chart_card()
                st.plotly_chart(fig, use_container_width=True)
                _chart_card_close()
            else:
                omitidos.append(f"«{conf.get('titulo', conf.get('tipo'))}» ({err})")
        if omitidos:
            st.caption("⚠️ Gráficos omitidos: " + "; ".join(omitidos))

        with st.expander("🎛️ Explorador de gráficos"):
            renderizar_graficos_genericos(df_f, reporte)
    else:
        renderizar_graficos_genericos(df_f, reporte)
