"""
graficos.base — infraestructura compartida por todos los dashboards de gráficos.

Helpers reutilizables (cards nativos, motor genérico config-driven, resolución
de columnas, formato de ejes/hover). NO contiene ningún dashboard concreto:
cada dashboard (ajuste.py, compras.py, ...) importa lo que necesita de aquí.
"""

import re
from contextlib import contextmanager

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import buscar_columna, _norm
from tema import (
    BLANCO, ESCALA_CONTINUA, GRIS_BORDE, SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
    PALETA_SERIES,
)


def _slug(texto):
    """Convierte un texto a un identificador válido para keys/CSS."""
    return re.sub(r"\W+", "_", str(texto)).strip("_").lower()


def _rail_set(state_key, opcion_id):
    """Callback de los botones del rail: fija la selección ANTES del rerun."""
    st.session_state[state_key] = opcion_id


def _render_rail(categorias, state_key, btn_prefix="graf_btn_"):
    """Rail vertical fijo al borde DERECHO — selector de tipo de gráfico.

    Componente COMPARTIDO: es el layout estándar de los dashboards (Compras,
    Ajuste, …). El rail, la franja superior, la posición de la fecha y el
    padding del contenido los activa el CSS de estilos.py scopeado a
    `:has(.st-key-compras_tabs_row)`. Esa key es HISTÓRICA (nació en Compras)
    pero hoy es LA KEY DEL RAIL COMPARTIDO — no renombrar sin actualizar sus
    ~40 referencias en estilos.py/navegacion.py.

    Parámetros
      · categorias: `((nombre_categoria, ((id, label), …)), …)`. `nombre` puede
        ser "" para omitir el badge de categoría (rail plano de una sección).
      · state_key: clave de session_state donde se persiste la selección.
      · btn_prefix: prefijo de las keys de los botones (único por reporte si dos
        rails pudieran coexistir; hoy solo hay un reporte activo por vez).

    Devuelve el id de la opción seleccionada (persistida en session_state, así
    sobrevive al rerun del clic sin doble render).
    """
    _todos = [oid for _, items in categorias for oid, _ in items]
    if not _todos:
        return None
    sel = st.session_state.get(state_key)
    if sel not in _todos:
        sel = _todos[0]
        st.session_state[state_key] = sel
    with st.container(key="compras_tabs_row"):
        with st.container(key="graf_tipo_chips"):
            for i, (cat_nombre, items) in enumerate(categorias):
                if cat_nombre:
                    st.markdown(
                        f'<div class="rail-cat-badge">{cat_nombre}</div>',
                        unsafe_allow_html=True,
                    )
                for oid, label in items:
                    st.button(
                        label,
                        key=f"{btn_prefix}{_slug(oid)}",
                        type=("primary" if oid == sel else "secondary"),
                        use_container_width=True,
                        on_click=_rail_set, args=(state_key, oid),
                    )
                if i < len(categorias) - 1:
                    st.markdown('<div class="rail-sep"></div>',
                                unsafe_allow_html=True)
    return st.session_state.get(state_key, _todos[0])


@contextmanager
def _card(key, titulo: str = "", titulo_arriba: bool = False):
    """Card nativo para un gráfico. `key` debe ser único por rerun.
    Con `titulo`:
      - por defecto se muestra al pie (clase .chart-card-pie);
      - si `titulo_arriba=True`, se muestra como cabecera arriba del card,
        con divisoria (clase .chart-card-hdr, estilizada en estilos.py)."""
    with st.container(border=True, key=f"chartcard_{_slug(key)}"):
        if titulo and titulo_arriba:
            st.markdown(
                f'<p class="chart-card-hdr">{titulo}</p>',
                unsafe_allow_html=True,
            )
        yield
        if titulo and not titulo_arriba:
            st.markdown(
                f'<p class="chart-card-pie">{titulo}</p>',
                unsafe_allow_html=True,
            )


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

# ===========================================================================
# ALIAS RETROCOMPATIBLES
# ===========================================================================

PALETA_CALLAI = PALETA_SERIES  # alias retrocompatible; fuente en tema.py


# ===========================================================================
# HELPERS DE LAYOUT COMPARTIDOS (nombre '_compras_*' es histórico; los usan
# también ventas, inventario y constructor. Se mantienen los nombres para
# no romper contratos existentes.)
# ===========================================================================

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
