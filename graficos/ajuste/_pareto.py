"""graficos.ajuste._pareto - el Pareto de la diferencia, en el DETALLE.

Hasta el 2026-10-19 era uno de los tres modos de la vista «Distribución de
diferencias» (los otros dos, el strip por familia y el histograma). Se
reportó que de los tres sólo el Pareto se podía analizar: el histograma de
una sesión es una barra gigante en el cero y colas que no se ven, y los
casos extremos que mostraba el strip ya los listan «Por producto» y
«Análisis de diferencias». La vista se quitó y el Pareto pasó a ser una
opción del detalle de las dos vistas de arriba —«Detalle por: Pareto» en
Por familia y «Lista · Tabla · Pareto» en Familia × Área—, así que sigue a
lo que esté elegido en ellas: la familia en foco, o la celda. Regla #677.

Dos cosas cambiaron al mudarse:

  · FALTANTES O SOBRANTES. El de Distribución ordenaba sólo faltantes
    («dónde se pierde plata», a pedido, 2026-09-22). Ahora un selector
    elige el lado: muchos sobrantes son la otra mitad de un faltante —el
    producto vendido con el código de otro—, y sin ellos esa mitad no se ve.
  · LAS BARRAS DEL 80 % VAN EN COLOR FUERTE y el resto en claro: así la
    figura contesta de un vistazo cuántos productos explican el 80 % del
    lado (análisis ABC, H. F. Dickie, General Electric, 1951).

El grano de entrada es la LÍNEA (producto × área); el Pareto suma las
líneas de cada producto, o sea que un producto que faltó en un área y sobró
en otra entra por su NETO. Para verlo partido está la Tabla con «Áreas:
Separadas».
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import (
    ACENTO, AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS, AJUSTE_POS_TEXTO,
    GRIS_BORDE, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
)
from graficos import alturas
from graficos.base import _es_movil
from graficos.ajuste._comun import _layout_aj
from tablas.ajuste_familias import renderizar_desglose_ajuste

FALTANTES = "Faltantes"
SOBRANTES = "Sobrantes"
LADOS = (FALTANTES, SOBRANTES)

# Cuántos productos llevan barra. Diez, y no quince (2026-10-20, a pedido):
# con quince la tarjeta de Familia × Área se cortaba contra el borde de la
# pantalla de la laptop (619px), y la opción elegida fue que la tarjeta
# QUEPA, no que deslice por dentro (las tarjetas no llevan barra propia,
# CLAUDE.md). La cola no se dibuja (ver `_fig_pareto_ajuste`).
TOP_N = 10
# El corte del ABC: el mismo de la columna «Productos 80 %» de Por familia
# (`_cascada._PARETO`).
UMBRAL = 0.80


def _alfa(color, alfa):
    """`#rrggbb` -> `rgba(...)`: las barras fuera del 80 % son el MISMO
    color, apagado — no otro tono que se lea como otra categoría."""
    _h = color.lstrip("#")
    _r, _g, _b = (int(_h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({_r},{_g},{_b},{alfa})"


def _pareto_datos(df, col_ajuste_val, col_producto, top_n=TOP_N,
                  lado=FALTANTES):
    """Agrega el ajuste NETO por producto, se queda con UN lado (faltantes:
    neto < 0; sobrantes: neto > 0), ordena por magnitud y agrupa la cola en
    «Otros (N)».

    El grano del df es la LÍNEA (producto × área); sumar sus líneas por
    producto es legítimo porque `AJUSTE VALORIZADO` es un valor por línea
    (a diferencia de las columnas *_ANO_ANTERIOR, que vienen repetidas por
    grupo — CLAUDE.md). Los valores salen como MAGNITUD positiva, en soles,
    para que la barra y el acumulado crezcan hacia arriba. Devuelve
    `(etiquetas, valores, acumulado, pct, pct_acum)`, todo en el mismo orden;
    listas vacías si el lado no tiene ningún producto."""
    if not col_producto or col_producto not in df.columns:
        return [], [], [], [], []
    g = pd.to_numeric(df[col_ajuste_val], errors="coerce").fillna(0.0) \
        .groupby(df[col_producto].astype(str)).sum()
    sel = g[g < 0] if lado == FALTANTES else g[g > 0]
    if sel.empty:
        return [], [], [], [], []
    mags = sel.abs().sort_values(ascending=False, kind="stable")
    top = mags.iloc[:top_n]
    resto = mags.iloc[top_n:]
    etiquetas = [str(p) for p in top.index]
    valores = [float(v) for v in top.values]
    if len(resto) > 0:
        etiquetas.append(f"Otros ({len(resto)})")
        valores.append(float(resto.sum()))
    total = sum(valores) or 1.0
    acum, run = [], 0.0
    for v in valores:
        run += v
        acum.append(run)
    pct = [v / total * 100 for v in valores]
    pct_acum = [a / total * 100 for a in acum]
    return etiquetas, valores, acum, pct, pct_acum


def productos_80(df, col_ajuste_val, col_producto, lado=FALTANTES,
                 umbral=UMBRAL):
    """`(n, de, suma, total)`: cuántos productos del lado explican `umbral`
    de su total, de cuántos, cuánto suman ésos y el total del lado (soles,
    en magnitud). Sobre TODOS los productos, no sólo los del top: el 80 %
    puede caer adentro de «Otros»."""
    if not col_producto or col_producto not in df.columns:
        return 0, 0, 0.0, 0.0
    g = pd.to_numeric(df[col_ajuste_val], errors="coerce").fillna(0.0) \
        .groupby(df[col_producto].astype(str)).sum()
    sel = (g[g < 0] if lado == FALTANTES else g[g > 0]).abs() \
        .sort_values(ascending=False, kind="stable")
    if sel.empty:
        return 0, 0, 0.0, 0.0
    total = float(sel.sum())
    acum = sel.cumsum()
    n = int((acum < umbral * total - 1e-9).sum()) + 1
    n = min(n, len(sel))
    return n, len(sel), float(acum.iloc[n - 1]), total


def _fig_pareto_ajuste(df, col_ajuste_val, col_producto, top_n=TOP_N,
                       height=None, lado=FALTANTES):
    """Pareto de un lado, en HORIZONTAL: una barra por producto (soles), de
    mayor a menor hacia abajo, y la línea del acumulado en su propio eje,
    arriba, de 0 a 100 %.

    HORIZONTAL Y SIN «OTROS», medido con el cierre de setiembre 2026 en
    Alimentos: 73 de 273 productos explican el 80 % del faltante, así que en
    vertical la barra «Otros (263)» medía diez veces la más alta y aplastaba
    al resto, y los nombres del ERP —«(P) Bife Ancho Argentino Ojo 300gr x
    und (produccion)»— se pisaban debajo de barras de 57px. Acostados se
    leen enteros (`automargin` lo agrega `_layout`, regla #325). La cola no
    se dibuja: el acumulado termina donde llegan los `top_n`, y la línea
    punteada del 80 % muestra cuánto falta — el texto de arriba dice
    cuántos productos hacen falta.

    El acumulado va en `xaxis2` (arriba, en %), creado DESPUÉS del layout:
    un eje extra que existe antes de `update_xaxes` hereda lo ajeno (regla
    #610). Las barras que explican el 80 % van en el color del lado y el
    resto apagadas. Devuelve None si el lado no tiene productos."""
    etiquetas, valores, acum, pct, pct_acum = _pareto_datos(
        df, col_ajuste_val, col_producto, top_n, lado)
    if etiquetas and etiquetas[-1].startswith("Otros ("):
        etiquetas, valores = etiquetas[:-1], valores[:-1]
        pct, pct_acum = pct[:-1], pct_acum[:-1]
    if not etiquetas:
        return None
    color = AJUSTE_NEG if lado == FALTANTES else AJUSTE_POS
    n80, _de, _s, _t = productos_80(df, col_ajuste_val, col_producto, lado)
    colores = [color if i < n80 else _alfa(color, 0.35)
               for i in range(len(etiquetas))]
    nombre = "Faltante" if lado == FALTANTES else "Sobrante"
    if height is None:
        # 16px por barra: el renglón de 10.5px del nombre y su aire. Con diez
        # barras la figura mide 206 y la tarjeta entera entra debajo de la
        # tabla de Familia × Área en 1323×619 (medido: con 17px se pasaba 9).
        height = alturas.por_filas(len(etiquetas), px_fila=16, extra=46,
                                   rol=alturas.MINI)
    fig = go.Figure()
    fig.add_bar(
        y=etiquetas, x=valores, orientation="h", marker_color=colores,
        name=nombre, customdata=[[p, pa] for p, pa in zip(pct, pct_acum)],
        hovertemplate=f"<b>%{{y}}</b><br>{nombre}: S/ %{{x:,.2f}}"
                      f"<br>%{{customdata[0]:.1f}}% del {nombre.lower()}"
                      f" · acumulado %{{customdata[1]:.1f}}%<extra></extra>")
    fig.update_layout(**_layout_aj(
        height=height,
        showlegend=False,
        margin=dict(l=10, r=16, t=26, b=6),
        bargap=0.22,
        xaxis=dict(showticklabels=True, tickprefix="S/ ", tickformat=",.0f",
                   showgrid=True, gridcolor=GRIS_BORDE, fixedrange=True),
        # `type="category"`: un nombre que sea sólo un número convertiría el
        # eje en lineal (reglas #325 y #448). De arriba hacia abajo, en el
        # orden de la lista (`categoryorder="array"`, regla #610).
        yaxis=dict(showticklabels=True, type="category",
                   categoryorder="array", categoryarray=etiquetas,
                   autorange="reversed", fixedrange=True,
                   tickfont=dict(size=10.5)),
    ))
    fig.update_layout(xaxis2=dict(
        # De 20 en 20 con los valores escritos: con el `tickmode` automático
        # la 1.64 de Cloud rotulaba 21.1 %, 42.1 %, 63.2 %… (captura del
        # 2026-10-20).
        # Con `tickvals` el `ticksuffix` no se aplica: el texto va escrito.
        overlaying="x", side="top", range=[0, 102],
        tickmode="array", tickvals=[0, 20, 40, 60, 80, 100],
        ticktext=["0 %", "20 %", "40 %", "60 %", "80 %", "100 %"],
        showgrid=False, fixedrange=True, tickfont=dict(size=10,
                                                       color=GRIS_TEXTO)))
    fig.add_scatter(
        y=etiquetas, x=pct_acum, xaxis="x2", name="Acumulado",
        mode="lines+markers", line=dict(color=ACENTO, width=2),
        marker=dict(size=5),
        # `hoverinfo` NO es "skip": apagaría también el clic (regla #388).
        hovertemplate=f"<b>%{{y}}</b><br>Acumulado: %{{x:.1f}}% del "
                      f"{nombre.lower()}<extra></extra>")
    fig.add_shape(type="line", xref="x2", yref="paper", x0=UMBRAL * 100,
                  x1=UMBRAL * 100, y0=0, y1=1,
                  line=dict(color=GRIS_TEXTO_SUAVE, dash="dash", width=1))
    fig.add_annotation(xref="x2", yref="paper", x=UMBRAL * 100, y=0,
                       text="80 %", showarrow=False, xanchor="left",
                       yanchor="bottom", font=dict(size=10, color=GRIS_TEXTO))
    return fig


def render_pareto(det, col_val, col_prod, col_area, col_cantidad, col_unidad,
                  prefijo, ident):
    """El Pareto del detalle, adentro de la tarjeta que abre el llamador.

    `det` son las LÍNEAS de lo elegido (la familia en foco, o la celda de
    Familia × Área). `prefijo` separa las keys de cada vista (`ajcas`, `hm`)
    e `ident` es la firma de lo elegido: la key del gráfico cambia con ella,
    así un clic de otra familia no queda marcado en ésta.

    El lado es UN valor por vista (`<prefijo>_par_lado`), que sobrevive a
    cambiar de familia. Un clic en una barra lista a la derecha las ÁREAS de
    ese producto: es lo que el neto del Pareto no muestra. La key del gráfico
    es estática por lado e `ident` a propósito: la selección sólo pinta esa
    tabla, no realimenta la figura (no aplica la trampa de la #399), y abre
    en modo CLIC (`dragmode="pan"` + ejes fijos): en «select» Streamlit
    apaga el clic suelto (regla #388)."""
    from graficos.ajuste._cascada import _alto_grilla, _atar_alto, _clave

    _k_lado = f"{prefijo}_par_lado"
    # columnas-internas: el lado y el renglón que lo explica
    _cl, _ct = st.columns([1, 3], vertical_alignment="center")
    with _cl:
        lado = st.segmented_control(
            "Lado del Pareto", LADOS, default=FALTANTES, key=_k_lado,
            label_visibility="collapsed") or FALTANTES
    n, de, suma, total = productos_80(det, col_val, col_prod, lado)
    nombre = "faltante" if lado == FALTANTES else "sobrante"
    with _ct:
        if n:
            st.markdown(
                f"<div style='font-size:12px;color:{GRIS_TEXTO}'>"
                f"<b style='color:{AJUSTE_NEG_TEXTO if lado == FALTANTES else AJUSTE_POS_TEXTO}'>"
                f"{n} de {de} producto{'s' if de != 1 else ''}</b> explican el "
                f"{suma / total * 100:.0f} % del {nombre} "
                f"(S/ {suma:,.0f} de S/ {total:,.0f}) · clic en una barra "
                f"para ver sus áreas</div>", unsafe_allow_html=True)
    if not n:
        st.caption(f"Ningún producto quedó con {nombre} neto.")
        return

    # La figura NO depende de la selección (sin `marcado`): si el clic la
    # cambiara, Streamlit podría tomarla por otro elemento y soltar la
    # selección. La barra elegida la marca Plotly solo, apagando las demás.
    _key_graf = f"{prefijo}_par_graf_{_clave(ident, lado)}"
    # columnas-internas: el gráfico y las áreas del producto elegido
    _cg, _cd = st.columns([1.75, 1], gap="small")
    with _cg:
        fig = _fig_pareto_ajuste(det, col_val, col_prod, lado=lado)
        fig.update_layout(dragmode="pan")
        _ev = st.plotly_chart(
            fig, width="stretch", key=_key_graf, on_select="rerun",
            selection_mode="points",
            config={"displaylogo": False, "displayModeBar": False})
    # En horizontal el producto viaja en `y` (en la barra y en el acumulado).
    _pts = ((_ev or {}).get("selection") or {}).get("points") or []
    _marc = next((p.get("y") for p in _pts if p.get("y")), None)
    with _cd:
        if not _marc:
            st.markdown(
                f"<div style='font-size:12px;color:{GRIS_TEXTO_MEDIO};"
                f"padding:8px 2px'>Clic en una barra para ver en qué áreas "
                f"faltó o sobró ese producto.</div>", unsafe_allow_html=True)
            return
        _sel = det[det[col_prod].astype(str) == str(_marc)]
        _has_area = bool(col_area and col_area in _sel.columns)
        _has_cant = bool(col_cantidad and col_cantidad in _sel.columns)
        _has_um = bool(col_unidad and col_unidad in _sel.columns)
        tp = pd.DataFrame({
            "area": (_sel[col_area].astype(str).str.strip() if _has_area
                     else pd.Series("—", index=_sel.index)),
            "valor": pd.to_numeric(_sel[col_val], errors="coerce").fillna(0.0),
        })
        _cols = [("area", "Área", "nombre")]
        if _has_cant:
            tp["cantidad"] = pd.to_numeric(_sel[col_cantidad],
                                           errors="coerce").fillna(0.0)
            _cols.append(("cantidad", "Cantidad", "cantidad"))
        tp = tp.groupby("area", as_index=False).sum(numeric_only=True)
        if _has_cant and _has_um:
            _u = _sel[col_unidad].astype(str).str.strip()
            tp["__um"] = _u.iloc[0] if len(_u) else ""
        tp = tp.reindex(tp["valor"].abs().sort_values(
            ascending=False, kind="stable").index)
        tp["__sel"] = False
        _cols.append(("valor", "Valor", "saldo"))
        st.markdown(
            f"<div style='font-size:11.5px;font-weight:700;letter-spacing:.04em;"
            f"text-transform:uppercase;margin:2px 0 4px 2px'>{_marc}</div>",
            unsafe_allow_html=True)
        _kg = f"{prefijo}_par_areas_{_clave(ident, lado, _marc)}"
        _alto = _alto_grilla(min(6, max(1, len(tp))) + 1)
        _atar_alto(_kg, _alto)
        renderizar_desglose_ajuste(
            tp, _cols, _alto, _kg, movil=_es_movil(),
            total={"area": "TOTAL", "valor": float(tp["valor"].sum())})
