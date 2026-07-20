"""
Dashboard de gráficos: KPIs, treemap, sunburst, scatter precio/stock,
rankings y distribución de precios.
"""

import datetime as _dt
import re
from contextlib import contextmanager

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
# HELPERS: CARDS PARA GRÁFICOS
#
# _card(key, titulo)  →  PATRÓN ACTUAL (buena práctica). Contenedor NATIVO
#   de Streamlit (st.container border=True): el gráfico queda DE VERDAD
#   dentro del card, sin divs abiertos ni position:absolute. El título se
#   pinta como pie lavanda al final, en flujo normal. Uso:
#       with _card("cascada", "Cascada por familia"):
#           st.plotly_chart(fig, use_container_width=True)
#
# _chart_card / _chart_card_close  →  LEGACY. Solo lo usa el dashboard de
#   Inventario Valorizado (sección NO TOCAR). No usar en código nuevo:
#   el div abierto por markdown no envuelve realmente a los elementos.
# ===========================================================================

def _slug(texto):
    """Convierte un texto a un identificador válido para keys/CSS."""
    return re.sub(r"\W+", "_", str(texto)).strip("_").lower()


@contextmanager
def _card(key, titulo: str = ""):
    """Card nativo para un gráfico. `key` debe ser único por rerun.
    Si hay `titulo`, se muestra como banda lavanda al pie del card
    (clase .chart-card-pie, estilizada en estilos.py)."""
    with st.container(border=True, key=f"chartcard_{_slug(key)}"):
        yield
        if titulo:
            st.markdown(
                f'<p class="chart-card-pie">{titulo}</p>',
                unsafe_allow_html=True,
            )


def _chart_card(titulo: str = ""):
    """LEGACY (solo Inventario Valorizado). Abre un div card por markdown.
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
    """LEGACY (solo Inventario Valorizado). Cierra el div de _chart_card()."""
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
    # Altura base compacta: permite ver el gráfico completo junto con sus
    # controles, incluso en laptops de pantalla baja.
    height=380,
    barcornerradius=6,          # ← NUEVO: esquinas redondeadas en TODAS las barras
    xaxis=dict(gridcolor=GRIS_BORDE),
    yaxis=dict(gridcolor=GRIS_BORDE, tickformat=",.0f"),
)


def _layout(**overrides):
    """_LAYOUT_BASE fusionado con `overrides`, aplicando a los ejes de
    TODOS los gráficos un estilo común:
      · sin valores en el eje Y (la cuadrícula interna SÍ se ve)
      · nombres del eje X horizontales (tickangle=0 + automargin)

    La cuadrícula conserva su color; solo se ocultan las ETIQUETAS del
    eje Y y se enderezan los nombres del eje X. Los overrides del gráfico
    se respetan y luego se les inyecta este estilo encima.

    Los gráficos cuyo eje Y lleva nombres (no valores numéricos) — p. ej.
    el mapa de calor, con familias en Y — pueden pasar showticklabels=True
    en su yaxis para conservar esas etiquetas."""
    base = dict(_LAYOUT_BASE)
    base.update(overrides)

    xaxis = dict(base.get("xaxis", {}))
    yaxis = dict(base.get("yaxis", {}))

    xaxis.update(tickangle=0, automargin=True,
                 showline=False, zeroline=False, mirror=False)
    yaxis.update(showline=False, zeroline=False, mirror=False)
    yaxis.setdefault("showticklabels", False)  # oculta valores del eje Y

    base["xaxis"] = xaxis
    base["yaxis"] = yaxis
    return base


def _wrap_cat(labels, width=14):
    """Parte etiquetas de categoría largas en varias líneas (con <br>) para
    que, mostradas en horizontal, no se enciman. `width` es el número
    aproximado de caracteres por línea. Se usa como `ticktext` del eje X,
    así que el hover (que lee el valor real) no se ve afectado."""
    out = []
    for lab in labels:
        s = str(lab)
        if len(s) <= width:
            out.append(s)
            continue
        lineas, actual = [], ""
        for palabra in s.split():
            if actual and len(actual) + 1 + len(palabra) > width:
                lineas.append(actual)
                actual = palabra
            else:
                actual = palabra if not actual else f"{actual} {palabra}"
        if actual:
            lineas.append(actual)
        out.append("<br>".join(lineas))
    return out


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
        with _card(f"explorador_{nombre_reporte}"):
            st.plotly_chart(fig, use_container_width=True)
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
        height=380,
    ))

    with _card("evolucion", "Evolución temporal"):
        st.plotly_chart(fig, use_container_width=True)

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
            with _card("evolucion_dual"):
                st.plotly_chart(fig2, use_container_width=True)


def _graf_comparativa_mensual(df, col_fecha, col_ajuste_val):
    """Comparativa mensual: barras de ajuste neto por mes.

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
        xaxis=dict(dtick="M1", tickformat="%b %Y", gridcolor=GRIS_BORDE),
        yaxis=dict(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE),
        showlegend=False, height=360,
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=GRIS_BORDE, line_width=1)

    with _card("comparativa", "Comparativa mensual"):
        evento = st.plotly_chart(
            fig,
            use_container_width=True,
            key="comparativa_mensual",
            on_select="rerun",
            selection_mode="points",
        )

    # ── Drill-down: clic en un mes → filas de ese mes ────────────────────
    sel = evento.get("selection", {}) if evento else {}
    puntos = sel.get("points", [])
    if puntos:
        mes_clic = pd.to_datetime(puntos[0].get("x"))
        detalle = d[d["_mes"] == mes_clic.replace(day=1)].drop(columns=["_mes"])
        if not detalle.empty:
            st.markdown(
                f"**Detalle de {mes_clic:%B %Y}** — {len(detalle)} filas · "
                f"ajuste neto S/ {detalle[col_ajuste_val].sum():,.2f}"
            )
            st.dataframe(detalle, use_container_width=True)


def _graf_waterfall_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto=None, col_valorizado=None,
                           col_cantidad=None):
    """Cascada (Waterfall) por familia/área — SOLO el gráfico.

    Los análisis complementarios (Faltantes, Sobrantes, Extremos, etc.) que
    antes vivían aquí como 8 tabs se movieron a `_panel_analisis_ajuste`,
    que renderiza el contenedor derecho de la vista Gráficos de Ajuste.

    `col_producto`, `col_valorizado` y `col_cantidad` se mantienen en la
    firma por compatibilidad (test_graficos.py y llamadas existentes las
    pasan); ya no se usan aquí.
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita columna de familia o área para el gráfico de cascada.")
        return

    agg = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
           .sum().sort_values(col_ajuste_val))
    total = float(agg[col_ajuste_val].sum())

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
            color=ACENTO_TEXTO_OSCURO if total >= 0 else "#ef4444",
        )),
        hovertemplate="%{x}<br><b>S/ %{y:,.2f}</b><extra></extra>",
    ))
    fig.update_layout(**_layout(
        title=f"Cascada de ajuste valorizado por {grp_col}",
        xaxis=dict(tickangle=-35, gridcolor=GRIS_BORDE),
        yaxis=dict(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE),
        showlegend=False, height=360,
    ))
    _xcats = agg[grp_col].tolist() + ["TOTAL"]
    fig.update_xaxes(tickmode="array", tickvals=_xcats,
                     ticktext=_wrap_cat(_xcats))
    with _card("cascada", "Cascada por familia"):
        st.plotly_chart(fig, use_container_width=True)


def _panel_analisis_ajuste(df, col_familia, col_area, col_ajuste_val,
                           col_producto, col_valorizado, col_cantidad,
                           ambito):
    """Panel derecho: UNA mini-tabla analítica a la vez, en pestañas.

    Vive dentro del contenedor blanco derecho de la vista Gráficos de
    Ajuste. Usa st.tabs (8 pestañas); si no caben en el ancho, Streamlit
    aplica scroll horizontal automáticamente. Para añadir un mini-gráfico
    nuevo: sumar el nombre a `tab_names` y su bloque `with tabs[i]:`.

    Las 8 vistas responden a preguntas distintas del mismo df activo:
      0. Faltantes por familia (top 5 negativos)
      1. Sobrantes por familia (top 5 positivos)
      2. Productos críticos (top 10 negativos, nivel producto)
      3. Ranking por área (+ % sobre |total|)
      4. Resumen de familia (N productos, ajuste, % s/ valorizado)
      5. Movimientos extremos (top+bottom en una tabla)
      6. Ranking por valorizado
      7. Ranking por cantidad (unidades)

    `ambito` se mantiene en la firma por si más adelante se usa para
    diferenciar contenido entre «Del periodo» e «Histórico»; hoy no lo
    necesita (las pestañas son las mismas para ambos).
    """
    grp_col = col_familia or col_area
    if not grp_col:
        st.info("Se necesita familia o área para el panel analítico.")
        return

    agg = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
           .sum().sort_values(col_ajuste_val))

    tab_names = [
        "Faltantes",
        "Sobrantes",
        "Críticos",
        "Por área",
        "Resumen",
        "Extremos",
        "Valorizado",
        "Cantidad",
    ]
    tabs = st.tabs(tab_names)

    def _fmt_soles(df_, col):
        df_ = df_.copy()
        df_[col] = df_[col].map(lambda v: f"S/ {v:,.2f}")
        return df_

    def _fmt_int(df_, col):
        df_ = df_.copy()
        df_[col] = df_[col].map(lambda v: f"{int(v):,}")
        return df_

    # 0 — Faltantes por familia
    with tabs[0]:
        st.caption("Top 5 faltantes")
        neg = agg.nsmallest(5, col_ajuste_val)[[grp_col, col_ajuste_val]]
        st.dataframe(_fmt_soles(neg, col_ajuste_val),
                     hide_index=True, use_container_width=True)

    # 1 — Sobrantes por familia
    with tabs[1]:
        st.caption("Top 5 sobrantes")
        pos = agg.nlargest(5, col_ajuste_val)[[grp_col, col_ajuste_val]]
        st.dataframe(_fmt_soles(pos, col_ajuste_val),
                     hide_index=True, use_container_width=True)

    # 2 — Productos críticos (top 10 negativos, nivel producto)
    with tabs[2]:
        if col_producto and col_producto in df.columns:
            st.caption("Top 10 productos más negativos")
            cols_p = [col_producto, col_ajuste_val]
            if grp_col in df.columns and grp_col not in cols_p:
                cols_p.insert(1, grp_col)
            prod_agg = (df.groupby(cols_p[:-1], as_index=False)[col_ajuste_val]
                          .sum()
                          .nsmallest(10, col_ajuste_val))
            st.dataframe(_fmt_soles(prod_agg, col_ajuste_val),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No hay columna de producto en el reporte.")

    # 3 — Ranking por área
    with tabs[3]:
        if col_area and col_area in df.columns:
            area_agg = (df.groupby(col_area, as_index=False)[col_ajuste_val]
                          .sum()
                          .sort_values(col_ajuste_val))
            _total_abs = abs(area_agg[col_ajuste_val]).sum() or 1
            area_agg["% |total|"] = (
                abs(area_agg[col_ajuste_val]) / _total_abs * 100
            ).round(1)
            area_agg["% |total|"] = area_agg["% |total|"].map(lambda v: f"{v:.1f}%")
            st.dataframe(_fmt_soles(area_agg, col_ajuste_val),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No hay columna de área en el reporte.")

    # 4 — Resumen familia (todas las familias, N productos + ajuste + %)
    with tabs[4]:
        if col_producto and col_producto in df.columns:
            resumen = (df.groupby(grp_col)
                         .agg(**{
                             "N° productos": (col_producto, "nunique"),
                             col_ajuste_val: (col_ajuste_val, "sum"),
                         })
                         .reset_index())
        else:
            resumen = (df.groupby(grp_col, as_index=False)[col_ajuste_val]
                         .sum())
        resumen = resumen.reindex(
            resumen[col_ajuste_val].abs().sort_values(ascending=False).index
        )
        if col_valorizado and col_valorizado in df.columns:
            val_por_fam = df.groupby(grp_col)[col_valorizado].sum()
            resumen["% s/ valorizado"] = resumen.apply(
                lambda r: (r[col_ajuste_val] / val_por_fam.get(r[grp_col], 1) * 100)
                          if val_por_fam.get(r[grp_col], 0) else 0,
                axis=1,
            ).round(2).map(lambda v: f"{v:+.2f}%")
        st.dataframe(_fmt_soles(resumen, col_ajuste_val),
                     hide_index=True, use_container_width=True)

    # 5 — Movimientos extremos (5 más rojos + 5 más verdes en una tabla)
    with tabs[5]:
        neg5 = agg.nsmallest(5, col_ajuste_val)
        pos5 = agg.nlargest(5, col_ajuste_val)[::-1]  # descendente
        sep = pd.DataFrame({grp_col: ["———"], col_ajuste_val: [0.0]})
        extremos = pd.concat([neg5, sep, pos5], ignore_index=True)
        extremos[col_ajuste_val] = extremos[col_ajuste_val].map(
            lambda v: "" if v == 0 else f"S/ {v:,.2f}"
        )
        st.dataframe(extremos[[grp_col, col_ajuste_val]],
                     hide_index=True, use_container_width=True)

    # 6 — Ranking por valorizado (familias ordenadas por valorizado total)
    with tabs[6]:
        if col_valorizado and col_valorizado in df.columns:
            val_agg = (df.groupby(grp_col, as_index=False)[col_valorizado]
                         .sum()
                         .sort_values(col_valorizado, ascending=False))
            st.dataframe(_fmt_soles(val_agg, col_valorizado),
                         hide_index=True, use_container_width=True)
        else:
            st.caption("No hay columna de valorizado en el reporte.")

    # 7 — Ranking por cantidad (ajuste en unidades, no en soles)
    with tabs[7]:
        if col_cantidad and col_cantidad in df.columns:
            cant_agg = (df.groupby(grp_col, as_index=False)[col_cantidad]
                          .sum()
                          .sort_values(col_cantidad))
            st.dataframe(_fmt_int(cant_agg, col_cantidad),
                         hide_index=True, use_container_width=True)
        else:
            st.caption(
                "No se encontró la columna de cantidad de ajuste "
                "(se buscó 'AJUSTE', 'CANTIDAD AJUSTE')."
            )


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
        yaxis=dict(autorange="reversed", gridcolor=GRIS_BORDE, showticklabels=True),
        # Evita que una lista larga de familias convierta el gráfico en una
        # sección más alta que la ventana.
        height=min(400, max(320, len(pivot.index) * 32 + 100)),
    ))
    _xcats = [str(c) for c in pivot.columns.tolist()]
    fig.update_xaxes(tickmode="array", tickvals=_xcats,
                     ticktext=_wrap_cat(_xcats))

    with _card("heatmap", "Mapa de calor"):
        st.plotly_chart(fig, use_container_width=True)

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
            _xcats = list(pd.unique(df[grp].astype(str)))
            fig.update_xaxes(tickmode="array", tickvals=_xcats,
                             ticktext=_wrap_cat(_xcats))
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
        with _card("dist_grupo", "Distribución por grupo"):
            st.plotly_chart(fig, use_container_width=True)

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
        with _card("dist_hist", "Histograma"):
            st.plotly_chart(fig2, use_container_width=True)

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
    Gráficos de Ajuste de Inventario — layout de dos contenedores.

    Estructura:
      · Filtros Área y Familia como st.multiselect (dropdowns colapsados),
        FUERA del contenedor grande. Cada uno con su propio label.
      · El segmented «Del periodo / Histórico» y su auto-detección por
        rango viven ahora en `app.py` (fila superior, junto al widget de
        fecha). Esta función solo LEE el ámbito desde:
            st.session_state["ajuste_graf_ambito"]
        Si por algún motivo no está seteado (p. ej. se llama fuera de la
        vista Ajuste), cae a «Del periodo».
      · Contenedor IZQUIERDO (grande): chips de tipo de gráfico arriba
        (Cascada / Mapa de calor / Distribución  ó  Evolución /
        Comparativa mensual) SIN iconos, y el gráfico elegido debajo.
      · Contenedor DERECHO: `_panel_analisis_ajuste` renderiza pestañas
        (st.tabs) con una mini-tabla a la vez.
      · «Del periodo»  → usa df_f (respeta el rango aplicado).
      · «Histórico»    → usa df_full acotado al AÑO ACTUAL.

    Nota: df_full es opcional; si no se pasa, se usa df_f también para
    Histórico (compatibilidad con llamadas antiguas).
    """
    col_fecha      = _resolver(df_f, ["FECHA APERTURA INVENTARIO", "FECHA", "MES"])
    col_familia    = _resolver(df_f, ["FAMILIA", "Nombre Familia", "NOMBRE FAMILIA"])
    col_area       = _resolver(df_f, ["AREA", "Nombre Area", "NOMBRE AREA"])
    col_ajuste_val = _resolver(df_f, ["AJUSTE VALORIZADO", "AJUSTEVALORIZADO"])
    col_valorizado = _resolver(df_f, ["VALORIZADO TOTAL", "VALORIZADO", "VALORIZADOTOTAL"])
    col_producto   = _resolver(df_f, ["NOMBRE PRODUCTO", "PRODUCTO", "DESCRIPCION"])
    col_cantidad   = _resolver(df_f, ["AJUSTE", "CANTIDAD AJUSTE", "CANTIDAD"])

    if not col_ajuste_val:
        st.warning(
            "No se encontró la columna de ajuste valorizado. "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Ámbito: se lee de session_state; app.py es la fuente de verdad ───
    # Todas las visualizaciones respetan el rango de fecha seleccionado.
    # Se eliminó el selector «Del periodo / Histórico».
    ambito = "actual"

    # ── FILTROS FUERA DEL CONTENEDOR: Área y Familia (popover desplegable) ─
    # Cada filtro es un botón compacto (chip) que al hacer clic abre un
    # popover con pills multi-selección adentro. Cuando está cerrado NO
    # ocupa espacio vertical. El label del botón muestra cuántos ítems
    # están seleccionados (o "Área" / "Familia" si no hay filtro activo).
    # DISEÑO UNIFICADO: los chips van en la FRANJA blanca superior
    # (mismo contenedor y CSS fijo que los chips de la vista Tabla,
    # que no se renderizan en Gráficos, así que no hay colisión).
    area_sel, fam_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        col_ff_area, col_ff_fam, _ = st.columns([1, 1, 4])
        with col_ff_area:
            if col_area and col_area in df_f.columns:
                areas = sorted(df_f[col_area].dropna()
                               .astype(str).unique().tolist())
                if areas:
                    _n_area = len(st.session_state.get("ajuste_graf_filtro_area") or [])
                    _lbl_area = f"Área · {_n_area}" if _n_area else "Área"
                    with st.popover(_lbl_area, use_container_width=True):
                        area_sel = st.pills(
                            "Área",
                            areas,
                            selection_mode="multi",
                            key="ajuste_graf_filtro_area",
                            label_visibility="collapsed",
                        ) or []
        with col_ff_fam:
            if col_familia and col_familia in df_f.columns:
                familias = sorted(df_f[col_familia].dropna()
                                  .astype(str).unique().tolist())
                if familias:
                    _n_fam = len(st.session_state.get("ajuste_graf_filtro_familia") or [])
                    _lbl_fam = f"Familia · {_n_fam}" if _n_fam else "Familia"
                    with st.popover(_lbl_fam, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia",
                            familias,
                            selection_mode="multi",
                            key="ajuste_graf_filtro_familia",
                            label_visibility="collapsed",
                        ) or []


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

    # ── Aplicar filtros externos de Área y Familia ───────────────────────
    if area_sel and col_area and col_area in d.columns:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_familia and col_familia in d.columns:
        d = d[d[col_familia].astype(str).isin(fam_sel)]

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # ── Opciones de gráfico según ámbito (SIN iconos, punto 3) ───────────
    opciones = [
        "Cascada", "Mapa de calor", "Distribución",
        "Evolución", "Comparativa mensual",
    ]

    # ── DOS CONTENEDORES BLANCOS lado a lado ─────────────────────────────
    # Las keys empiezan con "ajuste_graf_card_", así el selector
    # div[class*="st-key-ajuste_graf_card_"] de estilos.py las cubre.
    col_izq, col_der = st.columns([1.7, 1])

    with col_izq:
        _card_izq = st.container(
            border=True, key=f"ajuste_graf_card_izq_{_slug(ambito)}",
        )
        with _card_izq:
            # Chips de tipo de gráfico DENTRO del contenedor, arriba
            graf = st.pills(
                "Gráfico",
                opciones,
                default=opciones[0],
                key=f"ajuste_graf_tipo_{ambito}",
                label_visibility="collapsed",
            )
            if not graf:
                graf = opciones[0]

            # Render del gráfico elegido (solo uno por rerun)
            if graf == "Evolución":
                _graf_evolucion_ajuste(d, col_fecha, col_familia,
                                       col_ajuste_val, col_valorizado)
            elif graf == "Comparativa mensual":
                _graf_comparativa_mensual(d, col_fecha, col_ajuste_val)
            elif graf == "Cascada":
                _graf_waterfall_ajuste(d, col_familia, col_area, col_ajuste_val,
                                       col_producto=col_producto,
                                       col_valorizado=col_valorizado,
                                       col_cantidad=col_cantidad)
            elif graf == "Mapa de calor":
                _graf_heatmap_ajuste(d, col_familia, col_area, col_ajuste_val)
            elif graf == "Distribución":
                _graf_distribucion_ajuste(d, col_familia, col_area,
                                          col_ajuste_val, col_producto)

    with col_der:
        _card_der = st.container(
            border=True, key=f"ajuste_graf_card_der_{_slug(ambito)}",
        )
        with _card_der:
            _panel_analisis_ajuste(
                d, col_familia, col_area, col_ajuste_val,
                col_producto, col_valorizado, col_cantidad, ambito,
            )

def renderizar_graficos_reporte(df_f, reporte, cfg, df_full=None):
    """Punto de entrada de la vista Gráficos para reportes genéricos.

    df_full: opcional, DataFrame sin el filtro de fecha aplicado. Ajuste de
    Inventario lo usa para su pestaña Histórico (año actual completo).
    Reportes genéricos lo ignoran.
    """
    if reporte == "Ajuste de Inventario":
        renderizar_graficos_ajuste(df_f, reporte, df_full=df_full)
        return

    if reporte == "Compras":
        renderizar_graficos_compras(df_f, reporte, df_full=df_full)
        return

    if reporte == "Inventario Valorizado":
        renderizar_graficos_inventario(df_f, reporte, df_full=df_full)
        return

    if reporte == "Ventas":
        renderizar_graficos_ventas(df_f, reporte, df_full=df_full)
        return

    graficos_conf = cfg.get("graficos", [])

    if graficos_conf:
        omitidos = []
        for _i, conf in enumerate(graficos_conf):
            fig, err = crear_grafico(df_f, conf)
            if fig:
                with _card(f"conf_{reporte}_{_i}"):
                    st.plotly_chart(fig, use_container_width=True)
            else:
                omitidos.append(f"«{conf.get('titulo', conf.get('tipo'))}» ({err})")
        if omitidos:
            st.caption("⚠️ Gráficos omitidos: " + "; ".join(omitidos))

        with st.expander("🎛️ Explorador de gráficos"):
            renderizar_graficos_genericos(df_f, reporte)
    else:
        renderizar_graficos_genericos(df_f, reporte)


# ===========================================================================
# DASHBOARD DE GRÁFICOS — COMPRAS
# ===========================================================================
# Réplica del layout del dashboard de Ajuste: filtros como chips en la
# franja blanca, contenedor izquierdo con pills de tipo de gráfico y
# contenedor derecho con pestañas de mini-tops. Las keys de los cards
# reutilizan el prefijo "ajuste_graf_card_" para heredar el CSS existente.

def _compras_truncar(s, n=26):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _compras_layout(fig, alto=430):
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        colorway=PALETA_CALLAI,
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor=GRIS_BORDE, zeroline=False)
    return fig


def _compras_mini_barras(serie, titulo, fmt="S/ {:,.0f}", alto=400):
    """Mini gráfico de barras horizontales top-N (mayor arriba)."""
    if serie is None or serie.empty:
        st.info("Sin datos para este top.")
        return
    d = serie.sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=d.values,
        y=[_compras_truncar(i) for i in d.index],
        orientation="h",
        marker=dict(color=ACENTO, opacity=0.85),
        text=[fmt.format(v) for v in d.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=alto,
        margin=dict(l=4, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True,
                    key=f"compras_mini_{_slug(titulo)}")


def renderizar_graficos_compras(df_f, nombre_reporte, df_full=None):
    """Dashboard dedicado de Compras: 5 gráficos con pestañas + 5 mini-tops."""
    col_fam    = _resolver(df_f, ["Familia", "Nombre Familia"])
    col_subfam = _resolver(df_f, ["Subfamilia", "Nombre Subfamilia"])
    col_prov   = _resolver(df_f, ["Nombre_proveedor", "Nombre proveedor", "Proveedor"])
    col_prod   = _resolver(df_f, ["Nombre_producto", "Nombre producto", "Producto"])
    col_cant   = _resolver(df_f, ["Cantidad_compra", "Cantidad compra", "Cantidad"])
    col_valor  = _resolver(df_f, ["Valor_compra", "Valor compra", "Importe Total", "Valorizado"])
    col_val_aa = _resolver(df_f, ["Valor_ano_anterior", "Valor año anterior"])
    col_punit  = _resolver(df_f, ["Precio_unit", "Precio unit", "Precio Unitario"])
    col_punit_ant = _resolver(df_f, ["Ultimo_precio_unit", "Ultimo precio unit",
                                     "Ultimo_anterior", "Ultimo anterior"])
    col_fecha  = _resolver(df_f, ["Fecha_documento", "Fecha documento",
                                  "Fecha_registro", "Fecha registro", "FECHA"])
    if not col_fecha:
        for _c in df_f.columns:
            if pd.api.types.is_datetime64_any_dtype(df_f[_c]) or "fecha" in _norm(str(_c)):
                col_fecha = _c
                break

    if not col_valor:
        st.warning("No se encontró la columna de valor de compra. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Familia / Subfamilia como chips en la FRANJA blanca ──────
    fam_sel, sub_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if col_fam and col_fam in df_f.columns:
                fams = sorted(df_f[col_fam].dropna().astype(str).unique().tolist())
                if fams:
                    _n = len(st.session_state.get("compras_graf_filtro_fam") or [])
                    _lbl = f"Familia · {_n}" if _n else "Familia"
                    with st.popover(_lbl, use_container_width=True):
                        fam_sel = st.pills(
                            "Familia", fams, selection_mode="multi",
                            key="compras_graf_filtro_fam",
                            label_visibility="collapsed",
                        ) or []
        with c2:
            if col_subfam and col_subfam in df_f.columns:
                _d_sub = df_f
                if fam_sel and col_fam:
                    _d_sub = _d_sub[_d_sub[col_fam].astype(str).isin(fam_sel)]
                subs = sorted(_d_sub[col_subfam].dropna().astype(str).unique().tolist())
                if subs:
                    _n = len(st.session_state.get("compras_graf_filtro_sub") or [])
                    _lbl = f"Subfamilia · {_n}" if _n else "Subfamilia"
                    with st.popover(_lbl, use_container_width=True):
                        sub_sel = st.pills(
                            "Subfamilia", subs, selection_mode="multi",
                            key="compras_graf_filtro_sub",
                            label_visibility="collapsed",
                        ) or []

    d = df_f
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_subfam:
        d = d[d[col_subfam].astype(str).isin(sub_sel)]
    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    _mes = None
    if col_fecha and col_fecha in d.columns:
        _f = pd.to_datetime(d[col_fecha], errors="coerce")
        _mes = _f.dt.to_period("M").astype(str)

    opciones = ["Familia", "Proveedor", "Evolución proveedor",
                "Precio top 10", "Precio por compra",
                "Precio vs año pasado", "Cantidad vs año pasado",
                "Semanal", "Vs año anterior", "Personalizado"]

    graf = st.pills(
        "Gráfico", opciones, default=opciones[0],
        key="compras_graf_tipo", label_visibility="collapsed",
    ) or opciones[0]

    # Constructor: ancho completo, sin panel de mini-tops.
    if graf == "Personalizado":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _constructor_grafico(d, "compras")
        return

    col_izq, col_der = st.columns([1.7, 1])

    with col_izq:
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            if graf == "Familia" and col_fam:
                serie = _valor.groupby(d[col_fam].astype(str)).sum().sort_values(ascending=False)
                fig = go.Figure(go.Bar(
                    x=serie.index, y=serie.values,
                    marker=dict(color=PALETA_CALLAI * 4),
                    text=[f"S/ {v:,.0f}" for v in serie.values],
                    textposition="outside", cliponaxis=False,
                ))
                _compras_layout(fig)
                fig.update_layout(title="Valorizado de compra por familia")
                st.plotly_chart(fig, use_container_width=True, key="compras_g_fam")

            elif graf == "Proveedor" and col_prov:
                serie = (_valor.groupby(d[col_prov].astype(str)).sum()
                         .sort_values(ascending=False).head(15).sort_values())
                fig = go.Figure(go.Bar(
                    x=serie.values,
                    y=[_compras_truncar(i, 32) for i in serie.index],
                    orientation="h",
                    marker=dict(color=ACENTO, opacity=0.85),
                    text=[f"S/ {v:,.0f}" for v in serie.values],
                    textposition="outside", cliponaxis=False,
                ))
                _compras_layout(fig, alto=480)
                fig.update_layout(title="Top 15 proveedores por valorizado")
                fig.update_xaxes(visible=False)
                st.plotly_chart(fig, use_container_width=True, key="compras_g_prov")

            elif graf == "Evolución proveedor" and col_prov and _mes is not None:
                top = _valor.groupby(d[col_prov].astype(str)).sum().nlargest(8).index
                dd = pd.DataFrame({"mes": _mes, "prov": d[col_prov].astype(str),
                                   "valor": _valor})
                dd = dd[dd["prov"].isin(top)]
                piv = dd.groupby(["mes", "prov"])["valor"].sum().reset_index()
                fig = px.line(piv, x="mes", y="valor", color="prov", markers=True)
                fig.for_each_trace(lambda t: t.update(name=_compras_truncar(t.name, 22)))
                _compras_layout(fig, alto=540)
                fig.update_layout(
                    title="Evolución mensual de compra — top 8 proveedores",
                    xaxis_title=None, yaxis_title=None,
                    hovermode="x unified",
                    legend=dict(orientation="h", y=-0.22, x=0,
                                font=dict(size=10)),
                )
                fig.update_xaxes(type="category")
                st.plotly_chart(fig, use_container_width=True, key="compras_g_evo_prov")

            elif graf == "Precio top 10" and col_prod and col_punit and _mes is not None:
                top = _valor.groupby(d[col_prod].astype(str)).sum().nlargest(10).index
                _pu = pd.to_numeric(d[col_punit], errors="coerce")
                dd = pd.DataFrame({"mes": _mes, "prod": d[col_prod].astype(str),
                                   "precio": _pu})
                dd = dd[dd["prod"].isin(top)].dropna(subset=["precio"])
                piv = dd.groupby(["mes", "prod"])["precio"].mean().reset_index()
                fig = px.line(piv, x="mes", y="precio", color="prod", markers=True)
                fig.for_each_trace(lambda t: t.update(name=_compras_truncar(t.name, 22)))
                _compras_layout(fig, alto=560)
                fig.update_layout(
                    title="Precio unitario promedio — top 10 productos más comprados",
                    xaxis_title=None, yaxis_title=None,
                    hovermode="x unified",
                    legend=dict(orientation="h", y=-0.2, x=0,
                                font=dict(size=10)),
                )
                fig.update_xaxes(type="category")
                fig.update_traces(line=dict(width=2.2),
                                  marker=dict(size=6))
                st.plotly_chart(fig, use_container_width=True, key="compras_g_precio")

            elif graf == "Precio por compra" and col_prod and col_punit and col_fecha:
                # Precio REAL de cada compra en su fecha exacta (sin promediar):
                # un punto por ingreso; varios ingresos el mismo día = varios puntos.
                top = _valor.groupby(d[col_prod].astype(str)).sum().nlargest(10).index
                _pu = pd.to_numeric(d[col_punit], errors="coerce")
                _fe = pd.to_datetime(d[col_fecha], errors="coerce")
                dd = pd.DataFrame({"fecha": _fe, "prod": d[col_prod].astype(str),
                                   "precio": _pu})
                dd = dd[dd["prod"].isin(top)].dropna(subset=["fecha", "precio"])
                dd = dd.sort_values("fecha")
                fig = px.line(dd, x="fecha", y="precio", color="prod", markers=True)
                fig.for_each_trace(lambda t: t.update(name=_compras_truncar(t.name, 22)))
                _compras_layout(fig, alto=560)
                fig.update_layout(
                    title="Precio real por compra — top 10 productos más comprados",
                    xaxis_title=None, yaxis_title=None,
                    legend=dict(orientation="h", y=-0.2, x=0,
                                font=dict(size=10)),
                )
                fig.update_traces(
                    line=dict(width=1.6), marker=dict(size=7),
                    hovertemplate="%{fullData.name}<br>%{x|%d/%m/%Y}: S/ %{y:,.2f}<extra></extra>",
                )
                st.plotly_chart(fig, use_container_width=True, key="compras_g_precio_real")

            elif graf == "Precio vs año pasado" and col_prod and col_punit and col_fecha:
                # Un producto a la vez: precio real de cada compra (línea
                # sólida) vs el precio unitario del año pasado (punteada).
                _col_pu_aa = _resolver(d, ["Precio_unit_ano_anterior",
                                           "Precio unit ano anterior",
                                           "Precio_unit_ano_a nterior"])
                _tops = _valor.groupby(d[col_prod].astype(str)).sum().nlargest(30).index.tolist()
                _cp, _ = st.columns([1.4, 1.6])
                with _cp:
                    prod_sel = st.selectbox("Producto", _tops,
                                            key="compras_pvsaa_prod")
                dd = d[d[col_prod].astype(str) == prod_sel]
                _fe = pd.to_datetime(dd[col_fecha], errors="coerce")
                _pu = pd.to_numeric(dd[col_punit], errors="coerce")
                base = pd.DataFrame({"fecha": _fe, "pu": _pu})
                if _col_pu_aa:
                    base["pu_aa"] = pd.to_numeric(dd[_col_pu_aa], errors="coerce")
                base = base.dropna(subset=["fecha", "pu"]).sort_values("fecha")
                if base.empty:
                    st.info("Sin compras de ese producto en el rango.")
                else:
                    fig = go.Figure()
                    fig.add_scatter(
                        x=base["fecha"], y=base["pu"], mode="lines+markers",
                        name="Precio por compra",
                        line=dict(color=ACENTO, width=2.2),
                        marker=dict(size=7),
                        hovertemplate="%{x|%d/%m/%Y}: S/ %{y:,.2f}<extra>Compra</extra>",
                    )
                    _sub = ""
                    if _col_pu_aa and base.get("pu_aa") is not None and base["pu_aa"].notna().any():
                        fig.add_scatter(
                            x=base["fecha"], y=base["pu_aa"], mode="lines",
                            name="Precio año pasado",
                            line=dict(color="#9aa0a6", width=2, dash="dot"),
                            hovertemplate="%{x|%d/%m/%Y}: S/ %{y:,.2f}<extra>Año pasado</extra>",
                        )
                        _m_act = base["pu"].mean()
                        _m_aa = base["pu_aa"].mean()
                        if _m_aa and _m_aa > 0:
                            _var = (_m_act - _m_aa) / _m_aa * 100
                            _sub = f" · variación promedio {_var:+.1f}% vs año pasado"
                    else:
                        st.caption("Este producto no tiene precio del año pasado registrado.")
                    _compras_layout(fig, alto=500)
                    fig.update_layout(
                        title=_compras_truncar(prod_sel, 48) + _sub,
                        xaxis_title=None, yaxis_title=None,
                        legend=dict(orientation="h", y=-0.18, x=0),
                    )
                    st.plotly_chart(fig, use_container_width=True,
                                    key="compras_g_pvsaa")

            elif graf == "Cantidad vs año pasado" and col_fecha and col_cant:
                _col_cant_aa = _resolver(d, ["Cantidad_ano_anterior",
                                             "Cantidad ano anterior"])
                _tops = (["(Todos)"] +
                         _valor.groupby(d[col_prod].astype(str)).sum()
                         .nlargest(30).index.tolist()) if col_prod else ["(Todos)"]
                _cp, _ = st.columns([1.4, 1.6])
                with _cp:
                    prod_sel = st.selectbox("Producto", _tops,
                                            key="compras_cvsaa_prod")
                dd = d if prod_sel == "(Todos)" else d[
                    d[col_prod].astype(str) == prod_sel]
                _fe = pd.to_datetime(dd[col_fecha], errors="coerce")
                _mm = _fe.dt.to_period("M").astype(str)
                _cn = pd.to_numeric(dd[col_cant], errors="coerce").fillna(0)
                base = pd.DataFrame({"mes": _mm, "Este año": _cn})
                if _col_cant_aa:
                    base["Año pasado"] = pd.to_numeric(
                        dd[_col_cant_aa], errors="coerce").fillna(0)
                g = base.groupby("mes").sum().sort_index()
                if g.empty:
                    st.info("Sin datos en el rango.")
                else:
                    fig = go.Figure()
                    if "Año pasado" in g.columns:
                        fig.add_bar(x=g.index, y=g["Año pasado"],
                                    name="Año pasado",
                                    marker=dict(color=GRIS_BORDE))
                    fig.add_bar(x=g.index, y=g["Este año"], name="Este año",
                                marker=dict(color=ACENTO))
                    _compras_layout(fig, alto=500)
                    _tt = ("Cantidad comprada por mes: este año vs año pasado"
                           if prod_sel == "(Todos)" else
                           _compras_truncar(prod_sel, 40)
                           + " — cantidad mensual vs año pasado")
                    fig.update_layout(title=_tt, barmode="group",
                                      legend=dict(orientation="h", y=-0.18, x=0))
                    fig.update_xaxes(type="category")
                    fig.update_traces(
                        hovertemplate="%{fullData.name}<br>%{x}: %{y:,.1f}<extra></extra>")
                    st.plotly_chart(fig, use_container_width=True,
                                    key="compras_g_cvsaa")

            elif graf == "Semanal" and col_prod and col_fecha:
                # Compra por SEMANA: barras apiladas (valor) por producto
                # (top 8 + Otros); el hover muestra valor y cantidad.
                _dias_ini = {"Lunes": 0, "Sábado": 5, "Domingo": 6}
                _cd, _ = st.columns([1, 2.2])
                with _cd:
                    _dini = st.selectbox("La semana empieza:",
                                         list(_dias_ini.keys()),
                                         key="compras_sem_inicio")
                _off = _dias_ini[_dini]
                _fe = pd.to_datetime(d[col_fecha], errors="coerce")
                _sem_ini = (_fe - pd.to_timedelta(
                    (_fe.dt.weekday - _off) % 7, unit="D")).dt.date
                _cnt = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                        if col_cant else pd.Series(0, index=d.index))
                top = _valor.groupby(d[col_prod].astype(str)).sum().nlargest(8).index
                _pr = d[col_prod].astype(str).where(
                    d[col_prod].astype(str).isin(top), "Otros")
                dd = pd.DataFrame({"sem": _sem_ini, "prod": _pr,
                                   "valor": _valor, "cant": _cnt}).dropna(subset=["sem"])
                g = dd.groupby(["sem", "prod"], as_index=False)[["valor", "cant"]].sum()
                g = g.sort_values("sem")
                g["sem_lbl"] = pd.to_datetime(g["sem"]).dt.strftime("Sem %d/%m")
                fig = go.Figure()
                _prods = ([p_ for p_ in top if p_ in set(g["prod"])] +
                          (["Otros"] if (g["prod"] == "Otros").any() else []))
                for _i, _p in enumerate(_prods):
                    gg = g[g["prod"] == _p]
                    fig.add_bar(
                        x=gg["sem_lbl"], y=gg["valor"],
                        name=_compras_truncar(_p, 22),
                        marker=dict(color=(GRIS_BORDE if _p == "Otros"
                                    else PALETA_CALLAI[_i % len(PALETA_CALLAI)])),
                        customdata=gg["cant"],
                        hovertemplate=("%{fullData.name}<br>%{x}"
                                       "<br>Valor: S/ %{y:,.2f}"
                                       "<br>Cantidad: %{customdata:,.1f}"
                                       "<extra></extra>"),
                    )
                _compras_layout(fig, alto=540)
                fig.update_layout(
                    title="Compra por semana — valor por producto (top 8 + Otros)",
                    barmode="stack",
                    legend=dict(orientation="h", y=-0.22, x=0,
                                font=dict(size=10)),
                )
                fig.update_xaxes(type="category")
                st.plotly_chart(fig, use_container_width=True, key="compras_g_semanal")

            elif graf == "Vs año anterior" and col_fam and col_val_aa:
                _vaa = pd.to_numeric(d[col_val_aa], errors="coerce").fillna(0)
                g = pd.DataFrame({
                    "fam": d[col_fam].astype(str),
                    "Este año": _valor, "Año anterior": _vaa,
                }).groupby("fam").sum().sort_values("Este año", ascending=False)
                fig = go.Figure()
                fig.add_bar(x=g.index, y=g["Año anterior"], name="Año anterior",
                            marker=dict(color=GRIS_BORDE))
                fig.add_bar(x=g.index, y=g["Este año"], name="Este año",
                            marker=dict(color=ACENTO))
                _compras_layout(fig)
                fig.update_layout(title="Compra por familia: este año vs año anterior",
                                  barmode="group")
                st.plotly_chart(fig, use_container_width=True, key="compras_g_vsaa")

            else:
                st.info("No hay columnas suficientes para este gráfico.")

    with col_der:
        with st.container(border=True, key="ajuste_graf_card_der_compras"):
            tabs = st.tabs(["Prod. valor", "Proveedores", "Cantidad",
                            "Frecuencia", "Alzas precio"])
            with tabs[0]:
                if col_prod:
                    _compras_mini_barras(
                        _valor.groupby(d[col_prod].astype(str)).sum().nlargest(10),
                        "prod_valor")
            with tabs[1]:
                if col_prov:
                    _compras_mini_barras(
                        _valor.groupby(d[col_prov].astype(str)).sum().nlargest(10),
                        "prov_valor")
            with tabs[2]:
                if col_prod and col_cant:
                    _cnt = pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                    _compras_mini_barras(
                        _cnt.groupby(d[col_prod].astype(str)).sum().nlargest(10),
                        "prod_cant", fmt="{:,.0f}")
            with tabs[3]:
                if col_prod:
                    _compras_mini_barras(
                        d[col_prod].astype(str).value_counts().head(10),
                        "prod_freq", fmt="{:,.0f}")
            with tabs[4]:
                if col_prod and col_punit and col_punit_ant:
                    _pu  = pd.to_numeric(d[col_punit], errors="coerce")
                    _pa  = pd.to_numeric(d[col_punit_ant], errors="coerce")
                    base = pd.DataFrame({"prod": d[col_prod].astype(str),
                                         "pu": _pu, "pa": _pa}).dropna()
                    base = base[base["pa"] > 0]
                    if base.empty:
                        st.info("Sin datos de precio anterior.")
                    else:
                        g = base.groupby("prod")[["pu", "pa"]].mean()
                        alza = ((g["pu"] - g["pa"]) / g["pa"] * 100)
                        alza = alza[alza > 0].nlargest(10)
                        _compras_mini_barras(alza, "alzas", fmt="+{:,.1f}%")
                else:
                    st.info("Sin columnas de precio anterior.")


# ===========================================================================
# DASHBOARD DE GRÁFICOS — INVENTARIO VALORIZADO (v2, layout unificado)
# ===========================================================================
# Mismo esqueleto que el dashboard de Compras: chips de filtro en la franja
# blanca, card izquierdo con pills de tipo de gráfico y card derecho con
# pestañas de mini-tops. Reutiliza _compras_layout y _compras_mini_barras.
# (El dashboard legacy renderizar_graficos queda intacto; este lo reemplaza
# en la ruta de la vista Gráficos.)

def renderizar_graficos_inventario(df_f, nombre_reporte, df_full=None):
    """Dashboard de Inventario Valorizado: 4 gráficos + 2 mini-tops."""
    col_area  = _resolver(df_f, ["Nombre Area", "NOMBRE AREA", "Area"])
    col_fam   = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_prod  = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_cant  = _resolver(df_f, ["Stock al Dia", "Stock al dia", "STOCK AL DIA",
                                 "Cantidad", "Stock"])
    col_val   = _resolver(df_f, ["Valorizado total", "VALORIZADO TOTAL",
                                 "Valorizado"])
    col_punit = _resolver(df_f, ["Precio Promedio", "PRECIO PROMEDIO", "Precio"])

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
                    _lbl = f"Área · {_n}" if _n else "Área"
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
                    _lbl = f"Familia · {_n}" if _n else "Familia"
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
    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _val  = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    _cant = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
             if col_cant else None)

    opciones = ["Área y familia", "Torta familias",
                "Top por área (valor)", "Top por área (cantidad)"]

    col_izq, col_der = st.columns([1.7, 1])

    with col_izq:
        with st.container(border=True, key="ajuste_graf_card_izq_inv"):
            graf = st.pills(
                "Gráfico", opciones, default=opciones[0],
                key="inv_graf_tipo", label_visibility="collapsed",
            ) or opciones[0]

            if graf == "Área y familia" and col_area and col_fam:
                g = (pd.DataFrame({"area": d[col_area].astype(str),
                                   "fam": d[col_fam].astype(str),
                                   "val": _val})
                     .groupby(["area", "fam"], as_index=False)["val"].sum())
                orden = (g.groupby("area")["val"].sum()
                         .sort_values(ascending=False).index.tolist())
                fig = px.bar(g, x="area", y="val", color="fam",
                             category_orders={"area": orden})
                _compras_layout(fig, alto=520)
                fig.update_layout(
                    title="Valorizado por área, desglosado por familia",
                    barmode="stack", xaxis_title=None, yaxis_title=None,
                    legend=dict(orientation="h", y=-0.25, x=0,
                                font=dict(size=10)),
                )
                fig.update_traces(
                    hovertemplate="%{fullData.name}<br>%{x}: S/ %{y:,.2f}<extra></extra>")
                st.plotly_chart(fig, use_container_width=True, key="inv_g_areafam")

            elif graf == "Torta familias" and col_fam:
                serie = (_val.groupby(d[col_fam].astype(str)).sum()
                         .sort_values(ascending=False))
                fig = go.Figure(go.Pie(
                    labels=serie.index, values=serie.values, hole=0.45,
                    marker=dict(colors=PALETA_CALLAI * 4),
                    textinfo="label+percent",
                    hovertemplate="%{label}<br>S/ %{value:,.2f} (%{percent})<extra></extra>",
                ))
                _compras_layout(fig, alto=520)
                fig.update_layout(title="Participación del valorizado por familia",
                                  showlegend=False)
                st.plotly_chart(fig, use_container_width=True, key="inv_g_torta")

            elif graf in ("Top por área (valor)", "Top por área (cantidad)") and col_area and col_prod:
                es_valor = (graf == "Top por área (valor)")
                if not es_valor and _cant is None:
                    st.info("No se encontró la columna de cantidad.")
                else:
                    areas = sorted(d[col_area].dropna().astype(str).unique().tolist())
                    _ca, _ = st.columns([1, 2])
                    with _ca:
                        area_top = st.selectbox("Área", areas, key="inv_graf_area_top")
                    dd = d[d[col_area].astype(str) == area_top]
                    met = (pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
                           if es_valor
                           else pd.to_numeric(dd[col_cant], errors="coerce").fillna(0))
                    serie = (met.groupby(dd[col_prod].astype(str)).sum()
                             .nlargest(10).sort_values())
                    if serie.empty:
                        st.info("Sin datos en esa área.")
                    else:
                        _fmt = "S/ {:,.0f}" if es_valor else "{:,.1f}"
                        fig = go.Figure(go.Bar(
                            x=serie.values,
                            y=[_compras_truncar(i, 34) for i in serie.index],
                            orientation="h",
                            marker=dict(color=ACENTO, opacity=0.85),
                            text=[_fmt.format(v) for v in serie.values],
                            textposition="outside", cliponaxis=False,
                        ))
                        _compras_layout(fig, alto=480)
                        _t = "valorizado" if es_valor else "cantidad"
                        fig.update_layout(
                            title=f"Top 10 productos por {_t} — {area_top}")
                        fig.update_xaxes(visible=False)
                        st.plotly_chart(fig, use_container_width=True,
                                        key=f"inv_g_top_{_t}")
            else:
                st.info("No hay columnas suficientes para este gráfico.")

    with col_der:
        with st.container(border=True, key="ajuste_graf_card_der_inv"):
            tabs = st.tabs(["Mayor cantidad", "Precio más alto"])
            with tabs[0]:
                if col_prod and _cant is not None and col_area:
                    g = (pd.DataFrame({"prod": d[col_prod].astype(str),
                                       "area": d[col_area].astype(str),
                                       "cant": _cant})
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
                    _pu = pd.to_numeric(d[col_punit], errors="coerce")
                    g = (pd.DataFrame({"prod": d[col_prod].astype(str),
                                       "area": d[col_area].astype(str),
                                       "pu": _pu,
                                       "cant": (_cant if _cant is not None
                                                else pd.Series(0, index=d.index))})
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


# ===========================================================================
# CONSTRUCTOR DE GRÁFICOS (estilo Power BI, config por el usuario)
# ===========================================================================

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


# ===========================================================================
# DASHBOARD DE GRÁFICOS — VENTAS
# ===========================================================================

@st.fragment
def _ventas_grafico_dia(g, col_costo, col_pax):
    """Gráfico 'Venta bruta por día' aislado en su PROPIO @st.fragment.

    Al vivir en un fragment, togglear una métrica (pills) solo redibuja
    ESTE gráfico: no re-ejecuta los filtros de Grupo/Sub Grupo ni el resto
    de la vista de Ventas. `g` ya viene agregado por día (venta, costo,
    pax, ratio); Streamlit reutiliza el mismo `g` en los reruns del
    fragment, así que no se recalcula nada aguas arriba.
    """
    _opts = ["Venta"]
    if col_costo:
        _opts.append("Costo")
    if col_pax:
        _opts += ["Pax", "Pax/Venta"]
    _def = [m for m in ("Venta", "Costo") if m in _opts]
    sel = st.pills(
        "Métricas", _opts, selection_mode="multi", default=_def,
        key="ventas_dia_metricas", label_visibility="collapsed",
    ) or ["Venta"]

    _need_y2 = "Pax" in sel and "pax" in g.columns
    _need_y3 = "Pax/Venta" in sel and "ratio" in g.columns

    fig = go.Figure()
    if "Venta" in sel:
        fig.add_bar(
            x=g["dia"], y=g["venta"], name="Venta",
            marker=dict(color=ACENTO), yaxis="y",
            texttemplate="S/ %{y:,.0f}", textposition="outside",
            textfont=dict(size=13), cliponaxis=False,
            hovertemplate="%{x|%d/%m/%Y}<br>Venta: S/ %{y:,.2f}<extra></extra>")
    if "Costo" in sel and "costo" in g.columns:
        fig.add_bar(
            x=g["dia"], y=g["costo"], name="Costo",
            marker=dict(color=PALETA_CALLAI[1]), yaxis="y",
            texttemplate="S/ %{y:,.0f}", textposition="outside",
            textfont=dict(size=13), cliponaxis=False,
            hovertemplate="%{x|%d/%m/%Y}<br>Costo: S/ %{y:,.2f}<extra></extra>")
    if _need_y2:
        fig.add_trace(go.Scatter(
            x=g["dia"], y=g["pax"], name="Pax",
            mode="lines+markers+text",
            text=g["pax"], texttemplate="%{y:,.0f}",
            textposition="top center", textfont=dict(size=12),
            line=dict(color=PALETA_CALLAI[2], width=2.5), yaxis="y2",
            hovertemplate="%{x|%d/%m/%Y}<br>Pax: %{y:,.0f}<extra></extra>"))
    if _need_y3:
        fig.add_trace(go.Scatter(
            x=g["dia"], y=g["ratio"], name="Pax/Venta",
            mode="lines+markers",
            line=dict(color=PALETA_CALLAI[3], width=2, dash="dot"),
            yaxis="y3",
            hovertemplate="%{x|%d/%m/%Y}<br>Pax/Venta: %{y:.4f}<extra></extra>"))

    _compras_layout(fig, alto=500)
    _xright = 0.88 if _need_y3 else 1.0
    fig.update_layout(
        title="Venta bruta por día",
        barmode="group",
        xaxis=dict(
            domain=[0.0, _xright], type="date",
            tickmode="linear", tick0=g["dia"].min(), dtick=86400000.0,
            tickformat="%d/%m", tickangle=-45, tickfont=dict(size=10),
        ),
        yaxis=dict(tickprefix="S/ ", tickformat=",.0f"),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickformat=",.0f", title="Pax", visible=_need_y2),
        yaxis3=dict(overlaying="y", side="right", anchor="free",
                    position=1.0, showgrid=False, tickformat=".4f",
                    title="Pax/Venta", visible=_need_y3),
        margin=dict(l=10, r=(70 if _need_y3 else 10), t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True, key="ventas_g_dia")


_MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


@st.fragment
def _ventas_matriz_agrupada(d, col_venta, col_fam, col_sub, col_prod, col_fecha):
    """Matriz dinámica Nivel × Mes con comparación vs Año Pasado.

    Vive DENTRO de la vista Gráficos (una opción más del pills), NO toca la
    Tabla. Al estar en su propio @st.fragment, cambiar el chip de nivel solo
    redibuja esta matriz.

    - Chip "Nivel": Grupo / Sub Grupo / Producto → hasta qué nivel se agrega.
    - Columnas agrupadas por mes; dentro de cada mes: Vta AP (año pasado),
      Actual (año en curso), %Part y %vs AP.
    - "Actual" = año máximo presente en los datos cargados; "AP" = año-1.
      El vs AP solo tiene valor si el rango cargado incluye el año anterior.
    """
    _map = {}
    if col_fam:
        _map["Grupo"] = col_fam
    if col_sub:
        _map["Sub Grupo"] = col_sub
    if col_prod:
        _map["Producto"] = col_prod
    if not _map or not col_fecha:
        st.info("Faltan columnas (grupo/subgrupo/producto o fecha) para la matriz.")
        return

    _niveles = list(_map.keys())
    _def = "Sub Grupo" if "Sub Grupo" in _niveles else _niveles[0]
    nivel = st.pills("Nivel", _niveles, default=_def,
                     key="ventas_matriz_nivel",
                     label_visibility="collapsed") or _def
    nivel_col = _map[nivel]

    _fe = pd.to_datetime(d[col_fecha], errors="coerce")
    base = pd.DataFrame({
        "niv": d[nivel_col].astype(str).values,
        "anio": _fe.dt.year.values,
        "mes": _fe.dt.month.values,
        "venta": pd.to_numeric(d[col_venta], errors="coerce").fillna(0).values,
    }).dropna(subset=["anio", "mes"])
    if base.empty:
        st.info("Sin datos en el rango cargado.")
        return

    base["anio"] = base["anio"].astype(int)
    base["mes"] = base["mes"].astype(int)
    cur = int(base["anio"].max())
    prev = cur - 1
    hay_ap = (base["anio"] == prev).any()
    base = base[base["anio"].isin([cur, prev])]

    piv = base.pivot_table(index="niv", columns=["mes", "anio"],
                           values="venta", aggfunc="sum", fill_value=0.0)
    meses = sorted({m for (m, _a) in piv.columns})

    datos, act_cols, vs_cols = {}, [], []
    for m in meses:
        mn = _MESES_ES[m - 1]
        act = piv[(m, cur)] if (m, cur) in piv.columns else pd.Series(0.0, index=piv.index)
        ap = piv[(m, prev)] if (m, prev) in piv.columns else pd.Series(0.0, index=piv.index)
        tot = act.sum() or 1.0
        with np.errstate(divide="ignore", invalid="ignore"):
            vs = np.where(ap.values > 0, (act.values - ap.values) / ap.values * 100, np.nan)
        datos[(mn, "Vta AP")] = ap.values
        datos[(mn, "Actual")] = act.values
        datos[(mn, "%Part")] = act.values / tot * 100
        datos[(mn, "%vs AP")] = vs
        act_cols.append((mn, "Actual"))
        vs_cols.append((mn, "%vs AP"))

    tabla = pd.DataFrame(datos, index=piv.index)
    tabla.columns = pd.MultiIndex.from_tuples(tabla.columns)
    # Ordenar filas por venta actual total (desc)
    _tot_fila = sum(tabla[c] for c in act_cols)
    tabla = tabla.loc[_tot_fila.sort_values(ascending=False).index]
    tabla.index.name = nivel

    if nivel == "Producto" and len(tabla) > 30:
        tabla = tabla.head(30)
        st.caption("Mostrando top 30 productos por venta actual del periodo.")

    # ── Estilo: formato + heat (Actual) + color (%vs AP) ────────────────
    fmt = {}
    for (mn, met) in tabla.columns:
        if met in ("Vta AP", "Actual"):
            fmt[(mn, met)] = lambda x: f"S/ {x:,.0f}"
        elif met == "%Part":
            fmt[(mn, met)] = lambda x: f"{x:.0f}%"
        else:  # %vs AP
            fmt[(mn, met)] = lambda x: "—" if pd.isna(x) else f"{x:+.0f}%"

    def _color_vs(v):
        if pd.isna(v):
            return "color:#9aa0a6"
        if v > 0:
            return "color:#15803d"
        if v < 0:
            return "color:#dc2626"
        return ""

    sty = (tabla.style
           .format(fmt, na_rep="—")
           .background_gradient(cmap="Purples", subset=act_cols, axis=0)
           .map(_color_vs, subset=vs_cols))

    st.dataframe(sty, use_container_width=True, height=min(560, 80 + 34 * len(tabla)))

    st.caption(
        f"Actual = {cur} · Año pasado = {prev}. "
        + ("" if hay_ap else
           "⚠️ El rango cargado no incluye datos de "
           f"{prev}; amplía el rango de fecha para ver el «vs AP»."))


def renderizar_graficos_ventas(df_f, nombre_reporte, df_full=None):
    """Dashboard de Ventas: venta por día, familia/subfamilia por semana,
    e histórica de subfamilia. Columnas reales del parquet de ventas."""
    col_venta = _resolver(df_f, ["Venta Item Ddocumento", "Venta_Item_Ddocumento",
                                 "Neto Total Item Ddocumento", "Venta"])
    col_fam   = _resolver(df_f, ["Grupo"])
    col_sub   = _resolver(df_f, ["Sub Grupo", "Sub_Grupo", "Subgrupo"])
    col_fecha = _resolver(df_f, ["Fec Reg Documento", "Fec_Reg_Documento",
                                 "Fecha Registro", "FECHA"])
    col_costo  = _resolver(df_f, ["Precio Costo", "Costo Item Ddocumento", "Costo"])
    col_pax    = _resolver(df_f, ["Cant Pax", "Cantidad Pax", "Pax"])
    col_pedido = _resolver(df_f, ["Llave Local Pedido", "Llave_Local_Pedido",
                                  "Nro Pedido", "Numero Pedido"])
    col_prod   = _resolver(df_f, ["Nomb Item Venta", "Nombre Producto",
                                  "Producto", "Descripcion"])
    if not col_fecha:
        for _c in df_f.columns:
            if pd.api.types.is_datetime64_any_dtype(df_f[_c]):
                col_fecha = _c
                break

    if not col_venta:
        st.warning("No se encontró la columna de venta. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Grupo / Sub Grupo como chips en la franja ───────────────
    fam_sel, sub_sel = [], []
    with st.container(key="chips_ajuste_tabla"):
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if col_fam:
                fams = sorted(df_f[col_fam].dropna().astype(str).unique().tolist())
                if fams:
                    _n = len(st.session_state.get("ventas_graf_filtro_fam") or [])
                    _lbl = f"Grupo · {_n}" if _n else "Grupo"
                    with st.popover(_lbl, use_container_width=True):
                        fam_sel = st.pills(
                            "Grupo", fams, selection_mode="multi",
                            key="ventas_graf_filtro_fam",
                            label_visibility="collapsed") or []
        with c2:
            if col_sub:
                _dd = df_f
                if fam_sel and col_fam:
                    _dd = _dd[_dd[col_fam].astype(str).isin(fam_sel)]
                subs = sorted(_dd[col_sub].dropna().astype(str).unique().tolist())
                if subs:
                    _n = len(st.session_state.get("ventas_graf_filtro_sub") or [])
                    _lbl = f"Sub Grupo · {_n}" if _n else "Sub Grupo"
                    with st.popover(_lbl, use_container_width=True):
                        sub_sel = st.pills(
                            "Sub Grupo", subs, selection_mode="multi",
                            key="ventas_graf_filtro_sub",
                            label_visibility="collapsed") or []

    d = df_f
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_sub:
        d = d[d[col_sub].astype(str).isin(sub_sel)]
    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _venta = pd.to_numeric(d[col_venta], errors="coerce").fillna(0)

    opciones = ["Venta por día", "Familia/Subfamilia semanal",
                "Histórica subfamilia", "Matriz agrupada"]

    graf = st.pills("Gráfico", opciones, default=opciones[0],
                    key="ventas_graf_tipo",
                    label_visibility="collapsed") or opciones[0]

    with st.container(border=True, key="ajuste_graf_card_izq_ventas"):

        # ── 1) Venta bruta por día (Venta / Costo / Pax / Pax·Venta) ─────
        # Venta y Costo comparten el eje IZQUIERDO (soles). Pax va a un eje
        # derecho (conteo) y el ratio Pax/Venta a un tercer eje derecho
        # (escala minúscula), para que las 4 escalas no se pisen. El selector
        # de métricas (pills multi) permite prender/apagar cada serie.
        if graf == "Venta por día" and col_fecha:
            _fe = pd.to_datetime(d[col_fecha], errors="coerce").dt.normalize()

            # Venta y Costo: suma por línea (cada línea es un valor distinto).
            _base = pd.DataFrame({"dia": _fe, "venta": _venta})
            if col_costo:
                _base["costo"] = pd.to_numeric(d[col_costo], errors="coerce").fillna(0)
            _base = _base.dropna(subset=["dia"])
            _agg = {c: "sum" for c in _base.columns if c != "dia"}
            g = _base.groupby("dia", as_index=False).agg(_agg).sort_values("dia")

            # Pax: NO sumar todas las líneas (Cant Pax se repite por línea del
            # mismo pedido). Se toma 1 valor por pedido y luego se suma por día.
            if col_pax:
                _pdf = pd.DataFrame({
                    "dia": _fe,
                    "pax": pd.to_numeric(d[col_pax], errors="coerce").fillna(0),
                })
                if col_pedido:
                    _pdf["ped"] = d[col_pedido].astype(str)
                    _pdf = _pdf.dropna(subset=["dia"])
                    _pax_dia = (_pdf.groupby(["dia", "ped"], as_index=False)["pax"]
                                .max()
                                .groupby("dia", as_index=False)["pax"].sum())
                else:
                    _pdf = _pdf.dropna(subset=["dia"])
                    _pax_dia = _pdf.groupby("dia", as_index=False)["pax"].sum()
                g = g.merge(_pax_dia, on="dia", how="left")
                g["pax"] = g["pax"].fillna(0)
                g["ratio"] = g["pax"] / g["venta"].replace(0, np.nan)

            if g.empty:
                st.info("Sin fechas válidas en el rango.")
            else:
                _ventas_grafico_dia(g, col_costo, col_pax)

        # ── 2) Venta por familia/subfamilia por semana ──────────────────
        elif graf == "Familia/Subfamilia semanal" and col_fecha and col_fam:
            _dias_ini = {"Lunes": 0, "Sábado": 5, "Domingo": 6}
            cc = st.columns([1, 1, 2])
            with cc[0]:
                _dini = st.selectbox("La semana empieza:",
                                     list(_dias_ini.keys()),
                                     key="ventas_sem_ini")
            with cc[1]:
                _desg = st.selectbox("Desglosar por:",
                                     ["Familia", "Subfamilia"],
                                     key="ventas_sem_desg")
            col_seg = col_fam if _desg == "Familia" else (col_sub or col_fam)
            _off = _dias_ini[_dini]
            _fe = pd.to_datetime(d[col_fecha], errors="coerce")
            _sem = (_fe - pd.to_timedelta(
                (_fe.dt.weekday - _off) % 7, unit="D")).dt.date
            seg = d[col_seg].astype(str)
            top = _venta.groupby(seg).sum().nlargest(8).index
            seg2 = seg.where(seg.isin(top), "Otros")
            dd = (pd.DataFrame({"sem": _sem, "seg": seg2, "venta": _venta})
                  .dropna(subset=["sem"]))
            g = (dd.groupby(["sem", "seg"], as_index=False)["venta"].sum()
                 .sort_values("sem"))
            if g.empty:
                st.info("Sin datos en el rango.")
            else:
                g["lbl"] = pd.to_datetime(g["sem"]).dt.strftime("Sem %d/%m")
                fig = go.Figure()
                segs = ([s for s in top if s in set(g["seg"])] +
                        (["Otros"] if (g["seg"] == "Otros").any() else []))
                for i, sname in enumerate(segs):
                    gg = g[g["seg"] == sname]
                    fig.add_bar(
                        x=gg["lbl"], y=gg["venta"],
                        name=_compras_truncar(sname, 22),
                        marker=dict(color=(GRIS_BORDE if sname == "Otros"
                                    else PALETA_CALLAI[i % len(PALETA_CALLAI)])),
                        hovertemplate="%{fullData.name}<br>%{x}<br>S/ %{y:,.2f}<extra></extra>",
                    )
                _compras_layout(fig, alto=540)
                fig.update_layout(
                    title=f"Venta semanal por {_desg.lower()} (top 8 + Otros)",
                    barmode="stack",
                    legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10)))
                fig.update_xaxes(type="category")
                st.plotly_chart(fig, use_container_width=True, key="ventas_g_sem")

        # ── 3) Venta histórica de subfamilia ────────────────────────────
        elif graf == "Histórica subfamilia" and col_fecha and col_sub:
            _fams = ["(Todas)"] + (sorted(d[col_fam].dropna().astype(str)
                                          .unique().tolist()) if col_fam else [])
            cc = st.columns([1.4, 1.6])
            with cc[0]:
                fam_pick = st.selectbox("Familia", _fams, key="ventas_hist_fam")
            dd = (d if (fam_pick == "(Todas)" or not col_fam)
                  else d[d[col_fam].astype(str) == fam_pick])
            _fe = pd.to_datetime(dd[col_fecha], errors="coerce")
            _mes = _fe.dt.to_period("M").astype(str)
            _vv = pd.to_numeric(dd[col_venta], errors="coerce").fillna(0)
            seg = dd[col_sub].astype(str)
            top = _vv.groupby(seg).sum().nlargest(10).index
            g = pd.DataFrame({"mes": _mes, "sub": seg, "venta": _vv})
            g = (g[g["sub"].isin(top)]
                 .groupby(["mes", "sub"], as_index=False)["venta"].sum())
            if g.empty:
                st.info("Sin datos para esa familia.")
            else:
                fig = px.line(g, x="mes", y="venta", color="sub", markers=True,
                              color_discrete_sequence=PALETA_CALLAI)
                fig.for_each_trace(
                    lambda t: t.update(name=_compras_truncar(t.name, 22)))
                _compras_layout(fig, alto=520)
                fig.update_layout(
                    title="Venta histórica por subfamilia (top 10)",
                    xaxis_title=None, yaxis_title=None, hovermode="x unified",
                    legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=10)))
                fig.update_xaxes(type="category")
                st.plotly_chart(fig, use_container_width=True, key="ventas_g_hist")
                st.caption("Histórica sobre el rango de fechas cargado. Para ver "
                           "más meses, amplía el rango en el selector de fecha.")

        # ── 4) Matriz agrupada (Nivel × Mes, vs Año Pasado) ─────────────
        elif graf == "Matriz agrupada":
            _ventas_matriz_agrupada(d, col_venta, col_fam, col_sub,
                                    col_prod, col_fecha)
        else:
            st.info("No hay columnas suficientes para este gráfico.")
