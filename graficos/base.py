"""
graficos.base — infraestructura compartida por todos los dashboards de gráficos.

Helpers reutilizables (cards nativos, motor genérico config-driven, resolución
de columnas, formato de ejes/hover). NO contiene ningún dashboard concreto:
cada dashboard (ajuste.py, compras.py, ...) importa lo que necesita de aquí.
"""

import re
import unicodedata
from contextlib import contextmanager

import pandas as pd
import plotly.express as px
import streamlit as st

import pestillos
from utils import buscar_columna, _norm
from tema import (
    BLANCO, ESCALA_CONTINUA, GRIS_BORDE, SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
    PALETA_SERIES,
)
from graficos import alturas


def _slug(texto):
    """Convierte un texto a un identificador válido para keys/CSS."""
    return re.sub(r"\W+", "_", str(texto)).strip("_").lower()


def _slug_url(texto):
    """Como `_slug` pero SIN acentos — es lo que viaja en `?vista=`, para que
    la URL se pueda tipear a mano ("comparativo_vs_ano_pasado" y no
    "comparativo_vs_año_pasado", que en la barra sale percent-encodeado).

    NO se toca `_slug`: ese alimenta las keys de los widgets y por lo tanto
    los selectores de `estilos/` — cambiarlo movería CSS de sitio.
    Para LEER el parámetro no se usa esto sino `_norm`, que además ignora
    separadores: así entra igual "Año Pasado" que "ano-pasado"."""
    ascii_ = (unicodedata.normalize("NFKD", str(texto))
              .encode("ascii", "ignore").decode())
    return re.sub(r"\W+", "_", ascii_).strip("_").lower()


def _es_movil():
    """True si el request viene de un teléfono/tablet, leyendo el User-Agent
    del header (server-side, sin JS ni rerun). Se usa para decisiones que
    Plotly dibuja en el servidor y no puede adaptar al ancho real de pantalla
    (p. ej. cuánto abreviar los nombres sobre las barras, o si un heatmap
    ancho se renderiza a su tamaño completo y se scrollea en vez de achicarse
    hasta ser ilegible). Ante la duda (sin header o UA raro) asume desktop,
    que es el caso con más espacio. Cacheado por sesión.

    Vivía en graficos/compras/_comun.py (nació ahí para las etiquetas de
    barra de Proveedor) — se movió acá el 2026-08-07 al necesitarlo también
    graficos/ajuste.py para el mapa de calor: es infraestructura compartida,
    no algo propio de Compras. compras/_comun.py reexporta este mismo símbolo
    para no romper sus imports existentes."""
    _c = st.session_state.get("_es_movil_cache")
    if _c is not None:
        return _c
    try:
        ua = (st.context.headers.get("User-Agent", "") or "").lower()
    except Exception:
        ua = ""
    _m = any(k in ua for k in ("mobile", "android", "iphone", "ipad", "ipod"))
    st.session_state["_es_movil_cache"] = _m
    return _m


def _rail_set(state_key, opcion_id):
    """Callback de los botones del rail: fija la selección ANTES del rerun."""
    st.session_state[state_key] = opcion_id


def publicar_contexto_ia(reporte, df, filtros=None):
    """Publica el df EFECTIVO (con los chips ya aplicados) para el asistente IA.

    POR QUÉ existe: `app.py` llama a `inject_asistente(df_contexto=df_f)`, y
    `df_f` está filtrado por FECHA pero NO por los chips Área/Familia/etc —
    esos se aplican sobre una copia local dentro de cada dashboard (ver
    `graficos/ajuste/__init__.py`, misma trampa que la regla #58 con
    `df_full`). Resultado: el usuario filtraba a un área, preguntaba "¿cuál
    es el total?" y el asistente respondía el total SIN filtrar,
    contradiciendo lo que había en pantalla.

    Cada dashboard llama a esto justo DESPUÉS de aplicar sus chips. Funciona
    por el orden de `app.py`: `_render_contenido()` corre antes de
    `inject_asistente()`, así que lo publicado acá ya está disponible.

    Se guarda el nombre del reporte junto al df A PROPÓSITO: si el usuario
    cambia de reporte y el dashboard nuevo no publica (porque no tiene
    chips), el asistente detecta que el contexto es de OTRO reporte y cae al
    `df_f` que le pasa app.py, en vez de responder con datos del reporte
    anterior. Sin ese chequeo, un contexto viejo sobrevive en session_state
    y miente en silencio.

    `filtros` es un dict {etiqueta: valor(es)} solo para CONTARLE al modelo
    qué está filtrado; el filtrado real ya viene hecho en `df`.
    """
    st.session_state["_ia_contexto"] = {
        "reporte": reporte,
        "df": df,
        "filtros": {k: v for k, v in (filtros or {}).items() if v},
    }


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
    # ── Deep-link: el item del rail viaja en ?vista= ─────────────────────
    # Sin esto, la URL sólo decía el reporte y llegar a una pantalla
    # concreta eran 3-5 clics encadenados, cada uno con su rerun. Además
    # no se podía compartir "mirá ESTA pantalla": había que describirla.
    # Va acá, en el rail COMPARTIDO, así vale para los 6 dashboards de una.
    _por_norm = {_norm(o): o for o in _todos}
    sel = st.session_state.get(state_key)
    if sel not in _todos:
        # Todavía no hay selección válida: primera carga, o venimos de otro
        # reporte cuyo rail tenía otros ids. Ahí manda la URL, si trae uno
        # que exista en ESTE rail; si no, el primer item de siempre.
        # El match va por `_norm` (ignora acentos Y separadores), así entra
        # igual "comparativo_vs_ano_pasado" que "Comparativo vs Año Pasado".
        sel = _por_norm.get(_norm(st.query_params.get("vista", ""))) or _todos[0]
        st.session_state[state_key] = sel
    # Marcador del pestillo (ver pestillos.py). Solo existe si ESTE reporte
    # dibuja el rail: los que no lo usan tampoco reservan ancho para él.
    pestillos.marcar(pestillos.DER)
    with st.container(key="compras_tabs_row"):
        # FUERA de graf_tipo_chips a propósito: ese contenedor estila a
        # TODOS sus botones como ítems de la lista de vistas (regla #6 —
        # acotar al widget, no al contenedor). El pestillo no es una vista.
        pestillos.pestillo(pestillos.DER, "rail_pestillo")
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
    _final = st.session_state.get(state_key, _todos[0])
    # Espejo hacia la URL. Escribir query_params NO dispara rerun, pero se
    # compara antes igual: reescribir en cada rerun es ruido inútil.
    if st.query_params.get("vista") != _slug_url(_final):
        st.query_params["vista"] = _slug_url(_final)
    return _final


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


def publicar_var_px(nombre, px):
    """Publica un número de píxeles calculado en Python como VARIABLE CSS,
    para que las restas y las derivaciones las haga el navegador.

    Nació para los altos (ver `alturas.py` § LA RESTA NO SE HACE ACÁ) y hoy
    lo usan también los anchos de los rails plegables:
    el alto de una figura sólo lo puede decidir Python —Plotly ignora su
    contenedor—, pero el alto DISPONIBLE sólo lo conoce el navegador
    (`100dvh`). Cuando Python hace las dos cosas, resta contra una pantalla
    supuesta (`alturas.VIEWPORT_OBJETIVO`) y el resultado es correcto en un
    solo monitor. Publicando el número, el CSS puede escribir la resta
    verdadera:

        publicar_var_px("vh-alto-arriba", 351)
        /* en estilos/: */
        max-height: calc(var(--alto-util) - var(--vh-alto-arriba));

    SIN guard de "inyectar una sola vez": un `st.markdown` de estilos
    desaparece en el rerun siguiente (arquitectura.md regla #59), así que
    esto tiene que correr en cada render — que además es lo correcto, porque
    el número cambia con los datos.
    """
    st.markdown(
        f"<style>:root{{--{nombre}: {int(px)}px;}}</style>",
        unsafe_allow_html=True,
    )


def franja_cabecera(ph, titulo, color_texto=None):
    """Cabecera de una FRANJA DE CONTROLES: título + línea SUPERIOR que la
    cierra por arriba. Patrón `título → línea → tabs → línea → contenido`
    (arquitectura.md reglas #104/#107), nacido en Ventas › Por día y Año
    Pasado — este helper es la 3ª implementación, para no dejar una tercera
    copia con valores a mano que drifteen entre sí (las dos primeras YA
    tienen -15px/-18px/14px vs -6px/-18px/12px en el `<hr>` de abajo:
    exactamente el drift que este helper existe para frenar).

    `ph` es el `st.empty()` (o el propio `st`/contenedor) donde se pinta —
    normalmente un placeholder para poder escribir el título DESPUÉS de leer
    los controles que van debajo de él (ver `franja_linea_inferior` y el
    patrón de `session_state` en ventas_comparativo.py, regla #108: si el
    título depende de un widget que vive dentro de la misma franja, pintarlo
    dos veces —provisional con `session_state`, final con el valor real— es
    lo que evita el "salto" de layout en cada clic)."""
    color = color_texto or TEXTO_PRINCIPAL
    ph.markdown(
        '<div style="margin:-6px -18px 0;padding:0 18px 9px;'
        'width:calc(100% + 36px);font-size:16px;font-weight:600;'
        f'line-height:1.3;color:{color};'
        f'border-bottom:2px solid {GRIS_BORDE};">{titulo}</div>',
        unsafe_allow_html=True)


def titulo_en_franja(ph, titulo):
    """Pinta `titulo` en un placeholder que vive FUERA de la tarjeta y se
    ancla a la franja superior por CSS (position:fixed, con key propia por
    vista — ver estilos/_50_fecha.py, sección por dashboard). El `title=`
    del span es el tooltip para cuando el ellipsis del CSS lo trunca.

    Nace en Ventas › Comparativo (arquitectura.md regla #120) y se reusa en
    Compras › Familia para que una 3ra copia a mano no vuelva a driftear —
    mismo motivo por el que existe `franja_cabecera` más arriba."""
    ph.markdown(f'<span title="{titulo}">{titulo}</span>',
                unsafe_allow_html=True)


def franja_linea_inferior():
    """Línea INFERIOR que cierra una franja de controles por abajo, tocando
    el borde REAL de la tarjeta. Los -18px + `width:calc(100% + 36px)`
    compensan el padding horizontal de la tarjeta (16px 18px,
    `estilos/_80_cards.py`); sin eso la línea queda corta por los dos
    lados. Hermana de `franja_cabecera` — ver su docstring."""
    st.markdown(
        f'<hr style="border:none;border-top:2px solid {GRIS_BORDE};'
        'margin:-6px -18px 12px;width:calc(100% + 36px);">',
        unsafe_allow_html=True)


_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor=BLANCO,
    font_color=TEXTO_PRINCIPAL,
    font_family="DM Sans, Inter, -apple-system, sans-serif",
    margin=dict(l=20, r=20, t=50, b=20),
    # El alto NO se escribe suelto: sale de graficos/alturas.py, que es su
    # único dueño (ver su docstring: en este stack Plotly sólo obedece a
    # fig.layout.height, así que el número tiene que salir de Python).
    # APOYO vale 380, exactamente lo que este default decía antes.
    height=alturas.APOYO,
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
        fig.update_layout(height=alturas.PROTAGONISTA)
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


def _compras_layout(fig, alto=alturas.PROTAGONISTA):
    """Layout común de los dashboards. `alto` espera un ROL de
    graficos/alturas.py (PROTAGONISTA / APOYO / MINI) o el resultado de
    `alturas.por_filas(...)` — no un literal: ver la regla «nunca un alto
    suelto» en el docstring de ese módulo.

    El nombre `_compras_*` es histórico (nació en Compras); hoy lo usan
    también ventas, inventario, salidas, requerimientos y constructor.

    Con `alto=alturas.ELASTICO` la figura sale SIN `height`: el alto lo pone
    el CSS del contenedor y Plotly lo lee al montar. Requiere que el llamador
    pase `height="stretch"` a `st.plotly_chart` y que el CSS le dé alto a la
    cadena de contenedores — ver arquitectura.md regla #106."""
    if alto is alturas.ELASTICO:
        # height=None a propósito: mientras `fig.layout.height` esté puesto,
        # gana siempre y el contenedor no pinta nada (regla #102).
        alto = None
        fig.update_layout(autosize=True)
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
