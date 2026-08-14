"""
graficos.ventas — dashboard de Ventas: gráfico por día, matriz agrupada Grupo/SubGrupo/Producto × período, ranking FoodCost.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from data import cargar as _cargar_reporte
from tema import ACENTO, ERROR, EXITO, GRIS_BORDE, TEXTO_PRINCIPAL
from graficos.base import (
    PALETA_CALLAI, _card, _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos,
)
from graficos.ventas_resumen import _ventas_resumen
from graficos.ventas_comparativo import _ventas_comparativo
from graficos.ventas_horario import _ventas_horario
from graficos import alturas

_MESES_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py) — reemplaza el st.pills que vivia ANTES en medio
# del dashboard. Mismo patron que Compras/Ajuste.
_VENTAS_RAIL_CATEGORIAS = (
    ("Resumen",  (("Resumen ejecutivo", "Resumen"),)),
    ("Tiempo",   (("Venta por día",              "Por día"),
                  ("Mapa por hora",               "Por hora"),
                  ("Comparativo vs Año Pasado",   "Año Pasado"),
                  ("Venta vs Compra",            "Vs Compra"),
                  ("Familia/Subfamilia semanal",  "Semanal"),
                  ("Histórica subfamilia",        "Histórica"))),
    ("Análisis", (("Matriz agrupada",     "Matriz"),
                  ("Ranking & FoodCost",  "Ranking"),
                  ("Meseros",             "Meseros"))),
    ("Datos",    (("Tabla",  "Tabla"),)),
)


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
    # ── Cabecera de la franja: título + línea SUPERIOR ────────────────────
    # Junto con el <hr> de más abajo ENCIERRAN los toggles en una banda
    # propia, en vez de dejarlos flotando sobre una sola línea. Es el
    # patrón de la franja de controles de un gráfico bursátil: header,
    # línea, tabs, línea, gráfico.
    #
    # El título vivía DENTRO de la figura (`title=` en update_layout) y
    # CHOCABA con la leyenda: `_compras_layout` deja 30px de margen
    # superior (t=30) y pone la leyenda horizontal en y=1.02 / x=0, o sea
    # exactamente donde Plotly dibuja el título. Se leían encimados. Al
    # sacar el título acá, la leyenda se queda sola con esa banda.
    #
    # Los `-18px` + `width:calc(100% + 36px)` son los MISMOS de la línea de
    # abajo y por la misma razón: compensan el padding horizontal de la
    # tarjeta (16px 18px, estilos/_80_cards.py::ajuste_graf_card_*) para
    # que la línea toque el borde REAL. Si cambia ese padding, cambian los
    # tres números (acá, en el <hr> y en el margen del toggle).
    st.markdown(
        '<div style="margin:-6px -18px 0;padding:0 18px 9px;'
        'width:calc(100% + 36px);font-size:16px;font-weight:600;'
        f'line-height:1.3;color:{TEXTO_PRINCIPAL};'
        f'border-bottom:2px solid {GRIS_BORDE};">Venta bruta por día</div>',
        unsafe_allow_html=True)
    # NO envolver esto en un st.container(key=...) para poder estilarlo:
    # `st.pills(key=...)` YA emite `st-key-ventas_dia_metricas` en su propio
    # element container, que es el ancla de estilo local. Un container extra
    # además reintroduce el bug de la regla #70 (un contenedor con key tiene
    # identidad estable y RETIENE hijos huérfanos de la vista anterior —
    # acá se quedaba con las columnas de KPI del Resumen ejecutivo).
    sel = st.pills(
        "Métricas", _opts, selection_mode="multi", default=_def,
        key="ventas_dia_metricas", label_visibility="collapsed",
    ) or ["Venta"]
    # Separador de base bajo los toggles: los distingue del gráfico como un
    # bloque de controles propio, en vez de flotar sueltos arriba del chart.
    # Sangra hasta el borde REAL de la tarjeta (no solo el ancho del
    # contenido): la tarjeta pinta 18px de padding horizontal
    # (estilos/_80_cards.py, ajuste_graf_card_*), así que hay que compensar
    # ese padding con margen negativo + ensanchar el width lo mismo, si no
    # la línea queda corta por los dos lados en vez de tocar el borde.
    # El margen SUPERIOR compensa la subida del toggle (-8px en
    # estilos/_80_cards.py sobre `st-key-ventas_dia_metricas`): el <hr> va
    # en flujo justo detrás de las pills, así que sin esto subiría con
    # ellas. Van acoplados — si cambia uno, recalcular el otro.
    # Color: el MISMO gris de la cuadrícula del gráfico (GRIS_BORDE, el
    # `gridcolor` de graficos/base.py), no uno propio — así el separador
    # se lee como una línea más del gráfico y no como un elemento ajeno.
    # Como ese gris es más claro que el del texto suave, va a 2px para no
    # desaparecer: el grosor compensa el contraste que pierde el color.
    st.markdown(
        f'<hr style="border:none;border-top:2px solid {GRIS_BORDE};'
        'margin:-15px -18px 14px;width:calc(100% + 36px);">',
        unsafe_allow_html=True)

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

    # ELASTICO: el alto lo pone el CSS de la tarjeta, no Python. Esta figura
    # comparte tarjeta con la franja de controles y se come lo que sobra, sea
    # cual sea la pantalla. Con un alto fijo (con_franja() = 373) quedaba bien
    # en el laptop objetivo y desperdiciaba 343px en un monitor de 1920x1080:
    # el MARCO es CSS y se adapta, el alto de la figura era una constante
    # calibrada para una sola pantalla. Ver arquitectura.md reglas #105 y #106.
    _compras_layout(fig, alto=alturas.ELASTICO)
    _xright = 0.88 if _need_y3 else 1.0
    fig.update_layout(
        # Sin `title=`: el título de este gráfico lo dibuja la cabecera de la
        # franja (ver arriba). Dentro de la figura chocaba con la leyenda.
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
    # height="stretch" acompaña a alturas.ELASTICO: estira el wrapper de
    # Streamlit para que la cadena de contenedores tenga alto, que es de
    # donde Plotly lee el suyo al montar. Solo no alcanza (regla #102): hace
    # falta además el CSS de estilos/_80_cards.py que le da alto a la tarjeta
    # y `flex: 1 1 auto` a este elemento.
    st.plotly_chart(fig, use_container_width=True, height="stretch",
                    key="ventas_g_dia")


def _ventas_cargar_compra_diaria(dia_min, dia_max):
    """Compra por día, acotada a [dia_min, dia_max] (el rango de días que
    ya tiene la vista de Ventas). Carga compras.parquet APARTE — Ventas y
    Compras son reportes independientes, sin llave compartida más que la
    fecha, así que esto es el gasto TOTAL en compras ese día, no el costo
    de lo que se vendió ese día (una compra de insumos no se vende
    necesariamente el mismo día). Sirve para comparar flujo de compra vs
    venta, no como margen exacto por transacción. Los chips de Ventas
    (Grupo/Sub Grupo/Canal/Servicio) no aplican acá: son categorías de
    venta, sin equivalente en compras.parquet.
    Retorna None si compras.parquet no está disponible o le faltan las
    columnas de fecha/valor (mismo criterio de resolución que
    graficos/compras/__init__.py)."""
    df_c = _cargar_reporte("compras.parquet")
    if df_c is None or df_c.empty:
        return None
    col_fecha_c = _resolver(df_c, ["Fecha_documento", "Fecha documento",
                                   "Fecha_registro", "Fecha registro", "FECHA"])
    col_valor_c = _resolver(df_c, ["Valor_compra", "Valor compra",
                                   "Importe Total", "Valorizado"])
    if not col_fecha_c or not col_valor_c:
        return None
    _fe = pd.to_datetime(df_c[col_fecha_c], errors="coerce").dt.normalize()
    _val = pd.to_numeric(df_c[col_valor_c], errors="coerce").fillna(0)
    g_c = pd.DataFrame({"dia": _fe, "compra": _val}).dropna(subset=["dia"])
    g_c = g_c[(g_c["dia"] >= dia_min) & (g_c["dia"] <= dia_max)]
    if g_c.empty:
        return None
    return g_c.groupby("dia", as_index=False)["compra"].sum()


@st.fragment
def _ventas_venta_compra_dia(g, hay_costo, hay_compra, hay_pax):
    """'Venta vs Compra' — línea de Venta/Costo/Compra arriba (normalizadas
    a % de variación desde el primer día del rango, con badge de color al
    final de cada línea) + barras de Pax abajo en un subplot separado.
    Mismo espíritu que un gráfico bursátil: % arriba con crosshair, volumen
    abajo. A diferencia de "Venta por día" (barras, valores en S/, Pax en
    eje secundario), esta vista normaliza a % — Venta/Costo/Compra tienen
    escalas muy distintas en soles, así que compararlas en % desde el
    mismo punto de partida es lo que las hace legibles juntas."""
    _opts = ["Venta"]
    if hay_costo:
        _opts.append("Costo")
    if hay_compra:
        _opts.append("Compra")
    sel = st.pills(
        "Métricas", _opts, selection_mode="multi", default=list(_opts),
        key="ventas_vc_metricas", label_visibility="collapsed",
    ) or ["Venta"]

    rows = 2 if hay_pax else 1
    row_heights = [0.72, 0.28] if hay_pax else [1.0]
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True,
                        row_heights=row_heights, vertical_spacing=0.06)

    _colores = {"Venta": ACENTO, "Costo": PALETA_CALLAI[1], "Compra": PALETA_CALLAI[2]}
    for _serie, _col in (("Venta", "venta"), ("Costo", "costo"), ("Compra", "compra")):
        if _serie in sel and _col in g.columns:
            serie = g[_col]
            # % de variación desde el primer valor != 0 del rango (si todo
            # el rango es cero, no hay base válida: se muestra plano en 0%
            # en vez de dividir por cero).
            _base = next((v for v in serie if v), None)
            pct = (serie / _base - 1) * 100 if _base else serie * 0
            fig.add_trace(go.Scatter(
                x=g["dia"], y=pct, name=_serie, mode="lines",
                line=dict(color=_colores[_serie], width=2.2),
                hovertemplate=("%{x|%d/%m/%Y}<br>" + _serie
                               + ": %{y:+.2f}%<extra></extra>"),
            ), row=1, col=1)
            # Badge de color al final de la línea con el % acumulado del
            # rango — como el "+110,71%" de la referencia. Sin bordes
            # redondeados (Plotly no los soporta en anotaciones), pero
            # mismo color de fondo que la línea + texto blanco.
            fig.add_annotation(
                x=g["dia"].iloc[-1], y=pct.iloc[-1], row=1, col=1,
                text=f"{pct.iloc[-1]:+.2f}%", showarrow=False,
                xanchor="left", xshift=8, align="left",
                bgcolor=_colores[_serie], borderpad=4,
                font=dict(color="white", size=11, family="DM Sans, sans-serif"),
            )

    if hay_pax:
        fig.add_trace(go.Bar(
            x=g["dia"], y=g["pax"], name="Pax",
            marker=dict(color=GRIS_BORDE),
            hovertemplate="%{x|%d/%m/%Y}<br>Pax: %{y:,.0f}<extra></extra>",
        ), row=2, col=1)

    _compras_layout(fig, alto=alturas.PROTAGONISTA if hay_pax else 460)
    fig.update_layout(
        title="Venta vs Compra por día (% de variación desde el inicio del rango)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=64, t=30, b=10),
        # Crosshair al pasar el mouse: línea vertical punteada que cruza
        # ambos paneles (spikemode="across") + fecha en el eje X + un
        # tooltip único con el valor de cada serie en esa fecha
        # (hovermode="x unified"). Es la aproximación nativa de Plotly al
        # crosshair-con-badges-en-el-borde de la referencia: los badges de
        # la imagen SIGUEN al cursor en tiempo real, algo que Plotly no
        # ofrece sin JS custom (ver arquitectura.md — CLAUDE.md prohíbe JS
        # inyectado por markdown; haría falta un componente aparte). Este
        # tooltip unificado da la misma información (fecha + % de cada
        # serie), agrupada en un solo cuadro junto al cursor en vez de
        # flotando en el borde derecho.
        hovermode="x unified",
    )
    fig.update_xaxes(
        type="date", tickmode="linear", tick0=g["dia"].min(),
        dtick=86400000.0, tickformat="%d/%m", tickangle=-45,
        tickfont=dict(size=10), row=rows, col=1,
    )
    # Spikes en TODAS las filas (no solo la de abajo): con shared_xaxes las
    # X están "matched", pero cada eje decide por su cuenta si dibuja su
    # propia línea de crosshair — si solo se lo pedís al de abajo, pasar el
    # mouse por el panel de arriba (Venta/Costo/Compra) no muestra la cruz.
    fig.update_xaxes(
        showspikes=True, spikemode="across", spikesnap="cursor",
        spikedash="dot", spikethickness=1, spikecolor=GRIS_BORDE,
    )
    fig.update_yaxes(ticksuffix="%", tickformat=",.2f", zeroline=True,
                     zerolinecolor=GRIS_BORDE, row=1, col=1)
    if hay_pax:
        fig.update_yaxes(tickformat=",.0f", title="Pax", row=2, col=1)
    if not hay_compra:
        st.caption("Sin datos de Compra para este rango de fechas (o a "
                   "compras.parquet le faltan las columnas de fecha/valor) "
                   "— se omite esa serie.")
    st.plotly_chart(fig, use_container_width=True, key="ventas_g_vc_dia")


@st.fragment
def _ventas_matriz_agrupada(d, col_venta, col_costo, col_fam, col_sub,
                            col_prod, col_fecha):
    """Matriz dinámica Grupo → Sub Grupo → Producto × Mes/Semana con
    comparación vs Año Pasado, en un ÁRBOL AgGrid expandible.

    Vive DENTRO de la vista Gráficos (opción del pills "Matriz agrupada"), no
    toca la Tabla. Al estar en su propio @st.fragment, cambiar sub-pestaña o
    expandir/colapsar solo redibuja esta matriz.

    Sub-pestañas: Venta mes / Venta semana / FoodCost mes / FoodCost semana.
    """
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode  # noqa: E402

    if not col_fam or not col_sub or not col_prod or not col_fecha or not col_venta:
        st.info("Faltan columnas (Grupo, Sub Grupo, Producto, Fecha, Venta) "
                "para la matriz agrupada.")
        return

    # ── Sub-pestañas: modo (Venta / FoodCost) × granularidad (mes / semana) ─
    modos = ["Venta mes", "Venta semana"]
    if col_costo:
        modos += ["FoodCost mes", "FoodCost semana"]
    modo = st.pills("Modo", modos, default="Venta mes",
                    key="ventas_matriz_modo",
                    label_visibility="collapsed") or "Venta mes"
    es_fc = modo.startswith("FoodCost")
    es_sem = modo.endswith("semana")

    # ── Preparar df base: producto/anio/periodo con venta y costo ───────
    _fe = pd.to_datetime(d[col_fecha], errors="coerce")
    if es_sem:
        iso = _fe.dt.isocalendar()
        anio_serie = iso["year"].astype("Int64")
        periodo_serie = iso["week"].astype("Int64")

        def et_periodo(w):
            return f"S{int(w):02d}"
    else:
        anio_serie = _fe.dt.year.astype("Int64")
        periodo_serie = _fe.dt.month.astype("Int64")

        def et_periodo(m):
            return _MESES_ES[int(m) - 1]

    base = pd.DataFrame({
        "grupo": d[col_fam].astype(str).values,
        "sub":   d[col_sub].astype(str).values,
        "prod":  d[col_prod].astype(str).values,
        "anio":  anio_serie.values,
        "per":   periodo_serie.values,
        "venta": pd.to_numeric(d[col_venta], errors="coerce").fillna(0).values,
    })
    if col_costo:
        base["costo"] = pd.to_numeric(d[col_costo], errors="coerce").fillna(0).values
    base = base.dropna(subset=["anio", "per"])
    if base.empty:
        st.info("Sin datos en el rango cargado.")
        return
    base["anio"] = base["anio"].astype(int)
    base["per"] = base["per"].astype(int)

    cur = int(base["anio"].max())
    prev = cur - 1
    hay_ap = (base["anio"] == prev).any()
    base = base[base["anio"].isin([cur, prev])]

    valores = ["venta"] + (["costo"] if "costo" in base.columns else [])
    piv = base.pivot_table(
        index=["grupo", "sub", "prod"], columns=["per", "anio"],
        values=valores, aggfunc="sum", fill_value=0.0,
    )

    periodos = sorted({p for (_v, p, _a) in piv.columns})

    # ── Armar df wide a nivel producto (una fila por Grupo/Sub/Prod) ────
    df_wide = piv.reset_index()
    df_wide.columns = ["grupo", "sub", "prod"] + [
        f"{v}_{a}_{p}" for (v, p, a) in piv.columns
    ]

    # Columnas numéricas del grid (sumables): Vta Act, Vta AP, y para FC
    # también Costo Act / Costo AP. %Part y %vs AP se calculan en JS.
    per_labels = {p: et_periodo(p) for p in periodos}
    fld_va, fld_ap = {}, {}          # per → nombre de columna Actual/AP (venta)
    fld_ca, fld_cp = {}, {}          # per → costo Actual/AP
    for p in periodos:
        fld_va[p] = f"venta_{cur}_{p}"
        fld_ap[p] = f"venta_{prev}_{p}"
        if col_costo:
            fld_ca[p] = f"costo_{cur}_{p}"
            fld_cp[p] = f"costo_{prev}_{p}"
        for f in (fld_va[p], fld_ap[p], fld_ca.get(p), fld_cp.get(p)):
            if f and f not in df_wide.columns:
                df_wide[f] = 0.0

    # Total del periodo actual (para %Part). Se pasa a JS por gridOptions.context.
    totales = {int(p): float(df_wide[fld_va[p]].sum()) for p in periodos}

    # ── AgGrid: rowGroup en grupo y sub, tree con expand/collapse ───────
    gb = GridOptionsBuilder.from_dataframe(df_wide)
    gb.configure_default_column(
        resizable=True, sortable=False, filter=False, suppressMenu=True,
    )
    gb.configure_column("grupo", header_name="Grupo", rowGroup=True, hide=True)
    gb.configure_column("sub", header_name="Sub Grupo", rowGroup=True, hide=True)
    # El producto se muestra en la MISMA columna del árbol (autoGroupColumnDef
    # con field="prod"): las hojas muestran el nombre del producto y las filas
    # de grupo su clave + conteo. Por eso la columna suelta va oculta.
    gb.configure_column("prod", header_name="Producto", hide=True)

    # Formatters JS reutilizables
    fmt_soles = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '';
          return 'S/ '+Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:0});}
    """)
    fmt_pct0 = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '—';
          return Number(p.value).toFixed(0)+'%';}
    """)
    fmt_pct_signed = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '—';
          var v=Number(p.value); return (v>=0?'+':'')+v.toFixed(0)+'%';}
    """)
    style_vs = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return {color:'#9aa0a6'};
          var v=Number(p.value);
          if(v>0)return {color:'#15803d',fontWeight:500};
          if(v<0)return {color:'#dc2626',fontWeight:500};
          return {};}
    """)
    # Sombreado según magnitud de "Actual". Máx por columna via gridOptions.context.
    # Filas de grupo (subtotales): sin heat — el máximo es de hojas y todos los
    # subtotales saldrían con el tono más oscuro; solo se marcan en negrita.
    style_heat = JsCode("""
        function(p){
          if(p.node&&p.node.group)return {fontWeight:600};
          if(p.value==null||isNaN(p.value)||!p.colDef||!p.colDef.field)return {};
          var mx=(p.context&&p.context.maxAct)?(p.context.maxAct[p.colDef.field]||0):0;
          if(mx<=0)return {};
          var t=Math.min(1,Math.max(0,Number(p.value)/mx));
          var a=(0.06+0.5*t).toFixed(3);
          return {background:'rgba(108,92,231,'+a+')', borderRadius:'4px'};}
    """)
    style_heat_fc = JsCode("""
        function(p){
          if(p.value==null||isNaN(p.value))return {color:'#9aa0a6'};
          var v=Number(p.value);
          var t=Math.min(1,Math.max(0,v/60));
          var a=(0.06+0.55*t).toFixed(3);
          return {background:'rgba(220,38,38,'+a+')', borderRadius:'4px', fontWeight:500};}
    """)

    # Getter %Part = Actual / total_periodo * 100
    def _mk_part(fld_act, per_i):
        return JsCode(f"""
            function(p){{ var d=p.data||(p.node&&p.node.aggData); if(!d)return null;
              var act=Number(d['{fld_act}']||0);
              var tot=(p.context&&p.context.totales)?(p.context.totales[{per_i}]||0):0;
              if(!tot)return null; return act/tot*100;}}
        """)

    # Getter %vs AP = (Actual - AP) / AP * 100
    def _mk_vs(fld_act, fld_ap):
        return JsCode(f"""
            function(p){{ var d=p.data||(p.node&&p.node.aggData); if(!d)return null;
              var a=Number(d['{fld_act}']||0), b=Number(d['{fld_ap}']||0);
              if(!(b>0))return null; return (a-b)/b*100;}}
        """)

    # Getter FoodCost % = Costo / Venta * 100
    def _mk_fc(fld_costo, fld_venta):
        return JsCode(f"""
            function(p){{ var d=p.data||(p.node&&p.node.aggData); if(!d)return null;
              var c=Number(d['{fld_costo}']||0), v=Number(d['{fld_venta}']||0);
              if(!(v>0))return null; return c/v*100;}}
        """)

    # Getter vs FoodCost AP (diferencia en puntos porcentuales)
    def _mk_fc_vs(f_c_a, f_v_a, f_c_p, f_v_p):
        return JsCode(f"""
            function(p){{ var d=p.data||(p.node&&p.node.aggData); if(!d)return null;
              var ca=Number(d['{f_c_a}']||0), va=Number(d['{f_v_a}']||0);
              var cp=Number(d['{f_c_p}']||0), vp=Number(d['{f_v_p}']||0);
              if(!(va>0)||!(vp>0))return null;
              return (ca/va - cp/vp)*100;}}
        """)

    # ── Construir columnas por periodo (con column groups) ──────────────
    columnDefs_period = []
    for p in periodos:
        header = per_labels[p]
        children = []
        if es_fc:
            # FoodCost: Vta · Costo · FC% · vs FC AP (puntos)
            children.append({
                "field": fld_va[p], "headerName": "Vta",
                "type": "numericColumn", "width": 100,
                "aggFunc": "sum", "valueFormatter": fmt_soles,
            })
            children.append({
                "field": fld_ca[p], "headerName": "Costo",
                "type": "numericColumn", "width": 100,
                "aggFunc": "sum", "valueFormatter": fmt_soles,
            })
            children.append({
                "headerName": "FC%", "type": "numericColumn", "width": 80,
                "valueGetter": _mk_fc(fld_ca[p], fld_va[p]),
                "valueFormatter": fmt_pct0,
                "cellStyle": style_heat_fc,
            })
            children.append({
                "headerName": "vs AP", "type": "numericColumn", "width": 90,
                "valueGetter": _mk_fc_vs(fld_ca[p], fld_va[p],
                                          fld_cp[p], fld_ap[p]),
                "valueFormatter": fmt_pct_signed,
                "cellStyle": style_vs,
            })
        else:
            # Venta: Vta AP · Actual · %Part · %vs AP
            children.append({
                "field": fld_ap[p], "headerName": "Vta AP",
                "type": "numericColumn", "width": 100,
                "aggFunc": "sum", "valueFormatter": fmt_soles,
                "cellStyle": {"color": "#9aa0a6"},
            })
            children.append({
                "field": fld_va[p], "headerName": "Actual",
                "type": "numericColumn", "width": 110,
                "aggFunc": "sum", "valueFormatter": fmt_soles,
                "cellStyle": style_heat,
            })
            children.append({
                "headerName": "%Part", "type": "numericColumn", "width": 80,
                "valueGetter": _mk_part(fld_va[p], int(p)),
                "valueFormatter": fmt_pct0,
                "cellStyle": {"color": "#5a5a5a"},
            })
            children.append({
                "headerName": "%vs AP", "type": "numericColumn", "width": 90,
                "valueGetter": _mk_vs(fld_va[p], fld_ap[p]),
                "valueFormatter": fmt_pct_signed,
                "cellStyle": style_vs,
            })
        columnDefs_period.append({"headerName": header, "children": children})

    opciones_grid = gb.build()
    # columnDefs SOLO con la jerarquía + los grupos por periodo. Sin este
    # filtro, from_dataframe() añade también las columnas crudas del df wide
    # (venta_2026_7, costo_2025_7, ...) sin formato y duplicadas.
    _base_defs = [c for c in opciones_grid.get("columnDefs", [])
                  if c.get("field") in ("grupo", "sub", "prod")]
    opciones_grid["columnDefs"] = _base_defs + columnDefs_period

    # Contexto (para JS): totales por periodo y máximo por campo Actual (heat)
    max_act = {fld_va[p]: float(df_wide[fld_va[p]].max() or 0) for p in periodos}
    opciones_grid["context"] = {"totales": totales, "maxAct": max_act}

    # Modo árbol "singleColumn": la PRIMERA columna contiene la jerarquía
    # (chevrons + indentación) y — a diferencia de "groupRows" — las filas de
    # grupo SÍ muestran los subtotales agregados en las columnas de valores.
    # field="prod": en las hojas esa misma columna muestra el producto.
    opciones_grid["groupDisplayType"] = "singleColumn"
    opciones_grid["groupDefaultExpanded"] = 1  # muestra Grupo abierto (Sub cerrado)
    opciones_grid["animateRows"] = True
    opciones_grid["suppressAggFuncInHeader"] = True
    opciones_grid["autoGroupColumnDef"] = {
        "headerName": "Grupo / Sub Grupo / Producto",
        "field": "prod",
        "pinned": "left",
        "minWidth": 280,
        "cellRendererParams": {"suppressCount": False},
    }

    st.caption(
        f"Actual = {cur} · Año pasado = {prev}. "
        + ("Modo: " + modo + ".")
        + ("" if hay_ap else
           f" ⚠️ El rango cargado no incluye datos de {prev}; "
           "amplía el rango de fecha para ver el «vs AP»."))

    # Botones de expandir/colapsar todo (sin rerun de la app)
    _b1, _b2, _b3 = st.columns([1, 1, 6])
    with _b1:
        _btn_exp = st.button("⤢ Expandir todo", key="ventas_matriz_exp",
                             use_container_width=True)
    with _b2:
        _btn_col = st.button("⤡ Colapsar todo", key="ventas_matriz_col",
                             use_container_width=True)
    if _btn_exp:
        opciones_grid["groupDefaultExpanded"] = -1
    elif _btn_col:
        opciones_grid["groupDefaultExpanded"] = 0

    AgGrid(
        df_wide,
        gridOptions=opciones_grid,
        allow_unsafe_jscode=True,
        theme="streamlit",
        height=alturas.PROTAGONISTA,
        # rowGroup (árbol Grupo→Sub Grupo→Producto) es función Enterprise:
        # sin esto AgGrid ignora la agrupación y muestra filas planas.
        enable_enterprise_modules=True,
        key=f"ventas_matriz_grid_{modo}",
        reload_data=False,
    )


def _fc_heat_css(v, lo=12.0, hi=42.0):
    """Color de fondo amarillo→rojo para %FoodCost (v en %). Más FC = más rojo
    = peor margen. Devuelve un rgba() para usar como background en Styler."""
    if pd.isna(v):
        return ""
    t = min(1.0, max(0.0, (float(v) - lo) / (hi - lo)))
    r = round(254 + (220 - 254) * t)
    g = round(240 + (38 - 240) * t)
    b = round(138 + (38 - 138) * t)
    return f"background-color: rgba({r},{g},{b},0.6); color:#3a2a10"


@st.fragment
def _ventas_ranking_foodcost(d, col_venta, col_costo, col_cant,
                             col_fam, col_sub, col_prod, col_fecha):
    """Dashboard "Ranking & FoodCost" (opción de Gráficos de Ventas).

    Tres piezas: barras de venta + %FC por Grupo (Plotly), tabla por SubGrupo
    con %VAR vs Año Pasado y semáforo de FoodCost (Styler), y un ranking por
    Producto con sparklines de tendencia mensual (AgGrid + cellRenderer SVG).

    v1: FoodCost = Precio Costo / Venta (el "FC Receta" teórico queda para
    después). Cantidad y Costo son opcionales; si faltan, se omiten.
    """
    from st_aggrid import AgGrid, JsCode  # noqa: E402

    if not (col_venta and col_fecha and col_fam and col_sub and col_prod):
        st.info("Faltan columnas para el ranking "
                "(Grupo, Sub Grupo, Producto, Venta, Fecha).")
        return

    _fe = pd.to_datetime(d[col_fecha], errors="coerce")
    base = pd.DataFrame({
        "grupo": d[col_fam].astype(str).values,
        "sub":   d[col_sub].astype(str).values,
        "prod":  d[col_prod].astype(str).values,
        "anio":  _fe.dt.year.values,
        "mes":   _fe.dt.month.values,
        "venta": pd.to_numeric(d[col_venta], errors="coerce").fillna(0).values,
    })
    base["costo"] = (pd.to_numeric(d[col_costo], errors="coerce").fillna(0).values
                     if col_costo else 0.0)
    base["cant"] = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0).values
                    if col_cant else 0.0)
    base = base.dropna(subset=["anio", "mes"])
    if base.empty:
        st.info("Sin datos en el rango cargado.")
        return
    base["anio"] = base["anio"].astype(int)
    cur = int(base["anio"].max())
    prev = cur - 1
    hay_ap = (base["anio"] == prev).any()
    cur_df = base[base["anio"] == cur]
    ap_df = base[base["anio"] == prev]

    def _fc(costo, venta):
        return (costo / venta * 100) if venta else np.nan

    st.caption(
        f"Actual = {cur} · Año pasado = {prev}. FoodCost = Costo/Venta. "
        + ("" if hay_ap else
           f"⚠️ El rango no incluye {prev}; «vs AP» sale como —."))

    # ══ 1) Barras: Venta + %FC por Grupo ══════════════════════════════
    col_izq, col_der = st.columns([1, 1.25])
    with col_izq:
        with _card("rank_grupo", "Venta + %FoodCost por Grupo"):
            gv = cur_df.groupby("grupo", as_index=False).agg(
                venta=("venta", "sum"), costo=("costo", "sum"))
            gv["fc"] = gv.apply(lambda r: _fc(r["costo"], r["venta"]), axis=1)
            gv = gv.sort_values("venta", ascending=True)
            if gv.empty:
                st.info("Sin datos.")
            else:
                _txt = [f"S/ {v/1000:,.0f}k · FC {f:.0f}%" if pd.notna(f)
                        else f"S/ {v/1000:,.0f}k"
                        for v, f in zip(gv["venta"], gv["fc"])]
                fig = go.Figure(go.Bar(
                    x=gv["venta"], y=gv["grupo"], orientation="h",
                    marker=dict(color=ACENTO), text=_txt,
                    textposition="outside",
                    hovertemplate="%{y}<br>S/ %{x:,.0f}<extra></extra>"))
                _compras_layout(fig, alto=alturas.por_filas(
                    len(gv), px_fila=46, minimo=280, extra=60))
                fig.update_layout(
                    xaxis=dict(tickprefix="S/ ", tickformat=",.0f"),
                    margin=dict(l=10, r=90, t=10, b=10), showlegend=False)
                st.plotly_chart(fig, use_container_width=True,
                                key="ventas_rank_grupo")

    # ══ 2) Tabla por SubGrupo (Styler: heat FC + color %VAR) ══════════
    with col_der:
        with _card("rank_sub", "Venta y FoodCost por SubGrupo"):
            a = cur_df.groupby("sub", as_index=False).agg(
                ac=("venta", "sum"), costo=("costo", "sum"))
            b = ap_df.groupby("sub", as_index=False).agg(ap=("venta", "sum"))
            t = a.merge(b, on="sub", how="left")
            t["ap"] = t["ap"].fillna(0.0)
            t["fc"] = t.apply(lambda r: _fc(r["costo"], r["ac"]), axis=1)
            with np.errstate(divide="ignore", invalid="ignore"):
                t["var"] = np.where(t["ap"] > 0,
                                    (t["ac"] - t["ap"]) / t["ap"] * 100, np.nan)
            t = t.sort_values("ac", ascending=False)
            # Fila Total
            _sap, _sac = t["ap"].sum(), t["ac"].sum()
            tot = pd.DataFrame([{
                "sub": "Total", "ap": _sap, "ac": _sac,
                "costo": t["costo"].sum(),
                "fc": _fc(t["costo"].sum(), _sac),
                "var": ((_sac - _sap) / _sap * 100) if _sap else np.nan,
            }])
            tv = pd.concat([t, tot], ignore_index=True)[
                ["sub", "ap", "ac", "var", "fc"]]
            tv.columns = ["SubGrupo", "Año Pasado", "Actual", "%VAR vs AP", "%FC Venta"]

            def _sty_var(v):
                if pd.isna(v):
                    return "color:#9aa0a6"
                return "color:#15803d" if v >= 0 else "color:#dc2626"

            sty = (tv.style
                   .format({"Año Pasado": "S/ {:,.0f}", "Actual": "S/ {:,.0f}",
                            "%VAR vs AP": lambda v: "—" if pd.isna(v) else f"{v:+.0f}%",
                            "%FC Venta": lambda v: "—" if pd.isna(v) else f"{v:.1f}%"})
                   .map(_sty_var, subset=["%VAR vs AP"])
                   .map(_fc_heat_css, subset=["%FC Venta"])
                   .set_properties(subset=["Año Pasado"], color="#9aa0a6"))
            st.dataframe(sty, use_container_width=True, hide_index=True,
                         height=alturas.por_filas(len(tv), px_fila=34,
                                                  extra=60, minimo=0))

    # ══ 3) Ranking por Producto con sparklines (AgGrid) ═══════════════
    ac_prod = cur_df.groupby("prod", as_index=False).agg(
        ac=("venta", "sum"), costo=("costo", "sum"), cant=("cant", "sum"))
    ap_prod = ap_df.groupby("prod", as_index=False).agg(ap=("venta", "sum"))
    rk = ac_prod.merge(ap_prod, on="prod", how="left")
    rk["ap"] = rk["ap"].fillna(0.0)
    rk["fc"] = rk.apply(lambda r: _fc(r["costo"], r["ac"]), axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        rk["var"] = np.where(rk["ap"] > 0, (rk["ac"] - rk["ap"]) / rk["ap"] * 100, np.nan)
    rk = rk.sort_values("ac", ascending=False).head(30).reset_index(drop=True)

    # Tendencia mensual (año actual) por producto → lista para el sparkline
    meses_cur = sorted(cur_df["mes"].dropna().astype(int).unique())
    pm = (cur_df.groupby(["prod", "mes"], as_index=False)["venta"].sum())
    trend_map = {}
    for prod, grp in pm.groupby("prod"):
        m2v = dict(zip(grp["mes"].astype(int), grp["venta"]))
        trend_map[prod] = [float(m2v.get(m, 0.0)) for m in meses_cur]
    # La tendencia se pasa como texto "v1,v2,v3" (no lista): streamlit-aggrid
    # no serializa listas de forma fiable a arrays JS y el cellRenderer fallaba
    # con "a.map is not a function". El renderer la separa por comas.
    rk["trend"] = rk["prod"].map(
        lambda p: ",".join(f"{v:.0f}" for v in trend_map.get(p, [])))

    df_rank = rk[["prod", "ap", "ac", "trend", "var", "cant", "fc"]].copy()

    fmt_soles = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '';
          return 'S/ '+Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:0});}
    """)
    fmt_int = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '';
          return Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:0});}
    """)
    fmt_var = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '—';
          var v=Number(p.value); return (v>=0?'+':'')+v.toFixed(0)+'% '+(v>=0?'▲':'▼');}
    """)
    fmt_fc = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '—';
          return Number(p.value).toFixed(1)+'%';}
    """)
    style_var = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return {color:'#9aa0a6'};
          var v=Number(p.value);
          return v>=0?{color:'#15803d',fontWeight:500}:{color:'#dc2626',fontWeight:500};}
    """)
    style_fc = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return {};
          var t=Math.min(1,Math.max(0,(Number(p.value)-12)/30));
          var r=Math.round(254+(220-254)*t),g=Math.round(240+(38-240)*t),b=Math.round(138+(38-138)*t);
          return {backgroundColor:'rgba('+r+','+g+','+b+',0.6)',color:'#3a2a10',fontWeight:500};}
    """)
    spark = JsCode("""
        function(p){
          var s=p.value; if(s==null)return '';
          var a=String(s).split(',').map(Number).filter(function(x){return !isNaN(x);});
          if(a.length<2)return '';
          var w=88,h=22,mn=Math.min.apply(null,a),mx=Math.max.apply(null,a),rng=(mx-mn)||1;
          var pts=a.map(function(v,i){return (i/(a.length-1)*(w-4)+2).toFixed(1)+','+(h-2-(v-mn)/rng*(h-4)).toFixed(1);}).join(' ');
          var col=a[a.length-1]>=a[0]?'#15803d':'#dc2626';
          return '<svg width="'+w+'" height="'+h+'"><polyline points="'+pts+'" fill="none" stroke="'+col+'" stroke-width="1.5"></polyline></svg>';}
    """)

    coldefs = [
        {"headerName": "#", "valueGetter": "node.rowIndex + 1",
         "width": 46, "pinned": "left", "cellStyle": {"color": "#9aa0a6"}},
        {"field": "prod", "headerName": "Producto", "pinned": "left",
         "minWidth": 210},
        {"field": "ap", "headerName": "Año Pasado", "type": "numericColumn",
         "width": 120, "valueFormatter": fmt_soles, "cellStyle": {"color": "#9aa0a6"}},
        {"field": "ac", "headerName": "Actual", "type": "numericColumn",
         "width": 120, "valueFormatter": fmt_soles},
        {"field": "trend", "headerName": "Tendencia", "width": 110,
         "sortable": False, "cellRenderer": spark},
        {"field": "var", "headerName": "%Var vs AP", "type": "numericColumn",
         "width": 110, "valueFormatter": fmt_var, "cellStyle": style_var},
    ]
    if col_cant:
        coldefs.append({"field": "cant", "headerName": "Cant. Act.",
                        "type": "numericColumn", "width": 100,
                        "valueFormatter": fmt_int})
    if col_costo:
        coldefs.append({"field": "fc", "headerName": "%FC Venta",
                        "type": "numericColumn", "width": 110,
                        "valueFormatter": fmt_fc, "cellStyle": style_fc})

    grid_options = {
        "columnDefs": coldefs,
        "defaultColDef": {"resizable": True, "sortable": True,
                          "suppressMenu": True},
        "rowHeight": 30,
        "headerHeight": 34,
    }

    with _card("rank_prod", "Ranking de Venta Bruta y FoodCost por Producto"):
        AgGrid(
            df_rank,
            gridOptions=grid_options,
            allow_unsafe_jscode=True,
            theme="streamlit",
            height=alturas.por_filas(len(df_rank), px_fila=30,
                                     extra=90, minimo=0),
            enable_enterprise_modules=False,
            key="ventas_ranking_grid",
            reload_data=False,
        )
    if len(rk) >= 30:
        st.caption("Mostrando top 30 productos por venta actual.")


@st.fragment
def _ventas_ranking_meseros(d, col_mesero, col_propina, col_pedido,
                            col_corr, col_pax, col_fecha, col_venta):
    """Ranking de meseros por propina real vs. esperada (puntos porcentuales),
    controlando por Pax/Hora/Fin de semana con una regresión simple ajustada
    EN VIVO sobre el rango cargado — no un ranking crudo, que confundiría
    "buen mesero" con "le tocaron las mesas que de por sí dejan más propina"
    (grupos grandes, cena, findes).

    Bar chart horizontal 2D a propósito, sin 3D: para comparar N categorías
    con precisión, un bar chart gana — ver arquitectura.md.
    """
    if not (col_mesero and col_propina and col_pedido and col_pax
            and col_fecha and col_venta):
        st.info("Faltan columnas (Mesero, Propina, Pedido, Pax, Fecha, "
                "Venta) para el ranking de meseros.")
        return

    # ── Agregar a nivel de PEDIDO: Pax/Hora/Mesero son del pedido, no de
    # la línea — mismo criterio que Pax en "Venta por día" más arriba
    # (Cant Pax se repite por línea, se toma 1 valor por pedido).
    ped = d[col_pedido].astype(str)
    fecha = pd.to_datetime(d[col_fecha], errors="coerce")
    base = pd.DataFrame({
        "ped":    ped,
        "mesero": d[col_mesero].astype(str).str.strip().str.title(),
        "pax":    pd.to_numeric(d[col_pax], errors="coerce"),
        "hora":   fecha.dt.hour + fecha.dt.minute / 60.0,
        "finde":  fecha.dt.day_name().isin(["Friday", "Saturday", "Sunday"]),
        "venta":  pd.to_numeric(d[col_venta], errors="coerce").fillna(0),
    }).dropna(subset=["pax", "hora"])
    base = base[(base["mesero"] != "") & (base["mesero"].str.lower() != "nan")
               & (base["pax"] > 0) & (base["pax"] <= 20)]
    if base.empty:
        st.info("Sin datos de mesero en el rango cargado.")
        return

    # ── Propina por pedido: MONTO PROPINA se repite por LÍNEA DE PAGO, no
    # por pedido completo — una mesa con pago dividido (2+ métodos) tiene
    # más de un monto distinto. Sumar por (pedido, Correlativo Pago) único
    # antes de sumar por pedido evita contar la misma propina una vez por
    # cada línea de producto de ese pago.
    if col_corr and col_corr in d.columns:
        pagos = (pd.DataFrame({
            "ped": ped, "corr": d[col_corr].astype(str),
            "propina": pd.to_numeric(d[col_propina], errors="coerce").fillna(0),
        }).drop_duplicates(subset=["ped", "corr"]))
    else:
        pagos = pd.DataFrame({
            "ped": ped,
            "propina": pd.to_numeric(d[col_propina], errors="coerce").fillna(0),
        }).drop_duplicates()
    propina_ped = pagos.groupby("ped", as_index=False)["propina"].sum()

    pedidos = (base.groupby("ped", as_index=False)
               .agg(mesero=("mesero", "first"), pax=("pax", "max"),
                    hora=("hora", "first"), finde=("finde", "first"),
                    venta=("venta", "sum")))
    pedidos = pedidos.merge(propina_ped, on="ped", how="left")
    pedidos["propina"] = pedidos["propina"].fillna(0)
    pedidos = pedidos[pedidos["venta"] > 0]
    if len(pedidos) < 30:
        st.info("Muy pocos pedidos con mesero/propina en este rango para "
                "un ranking confiable — ampliá el rango de fechas.")
        return
    pedidos["propina_pct"] = (pedidos["propina"] / pedidos["venta"] * 100).clip(0, 30)
    pedidos["finde"] = pedidos["finde"].astype(float)

    # ── Regresión simple (propina% ~ pax, hora, hora², pax·hora, finde)
    # ajustada EN VIVO sobre el rango cargado: si cambia el rango de la
    # franja, cambia la línea de base contra la que se compara cada mesero.
    X = np.column_stack([
        np.ones(len(pedidos)), pedidos["pax"], pedidos["hora"],
        pedidos["hora"] ** 2, pedidos["pax"] * pedidos["hora"], pedidos["finde"],
    ])
    coef, *_ = np.linalg.lstsq(X, pedidos["propina_pct"].values, rcond=None)
    pedidos["residual"] = pedidos["propina_pct"].values - X @ coef

    resumen = (pedidos.groupby("mesero", as_index=False)
               .agg(n=("ped", "count"),
                    pct_real=("propina_pct", "mean"),
                    residual=("residual", "mean"))
               .sort_values("residual"))  # ascendente: el mejor queda ARRIBA en el bar horizontal

    colores = [EXITO if r >= 0 else ERROR for r in resumen["residual"]]
    _txt = [f"{r:+.2f}pp · n={n}" for r, n in zip(resumen["residual"], resumen["n"])]
    fig = go.Figure(go.Bar(
        x=resumen["residual"], y=resumen["mesero"], orientation="h",
        marker=dict(color=colores), text=_txt, textposition="outside",
        cliponaxis=False,
        customdata=np.column_stack([resumen["pct_real"], resumen["n"]]),
        hovertemplate="%{y}<br>Propina real: %{customdata[0]:.2f}%<br>"
                      "vs. esperada: %{x:+.2f}pp<br>n=%{customdata[1]:.0f}"
                      "<extra></extra>",
    ))
    _compras_layout(fig, alto=alturas.por_filas(
        len(resumen), px_fila=46, minimo=280, extra=60))
    # Rango del eje con relleno extra (no solo min/max de los datos): el
    # texto "outside" de la barra MÁS ancha (más lejos del cero) necesita
    # aire antes de chocar contra la columna de nombres -- sin este padding
    # se pisaban (ver captura real: "Junior Mendoza" perdía el "-0.79pp").
    _lo, _hi = float(resumen["residual"].min()), float(resumen["residual"].max())
    _pad = max(_hi - _lo, 0.2) * 0.35
    fig.update_layout(
        xaxis=dict(zeroline=True, zerolinecolor=GRIS_BORDE, ticksuffix="pp",
                   range=[_lo - _pad, _hi + _pad]),
        margin=dict(l=10, r=90, t=10, b=10), showlegend=False)
    with _card("meseros", "Propina real vs. esperada por mesero"):
        st.plotly_chart(fig, use_container_width=True, key="ventas_g_meseros")
        st.caption(
            "Esperada = un modelo simple ajustado en vivo sobre pax, hora y "
            "fin de semana del rango cargado — compara desempeño "
            "controlando el tipo de mesas que atendió cada mesero, no un "
            "promedio crudo. Meseros con pocos pedidos (n bajo) pesan menos.")


def renderizar_graficos_ventas(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Ventas: venta por día, familia/subfamilia por semana,
    e histórica de subfamilia. Columnas reales del parquet de ventas.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py — igual que
    Ajuste). Se le pasa `d`, el df YA filtrado por los chips propios de
    Ventas (Grupo/Sub Grupo/Canal/Servicio) — reusarlo evita que la Tabla
    tenga un estado de filtros distinto al de los gráficos."""
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
    col_cant   = _resolver(df_f, ["Cantidad Item Ddocumento", "Cantidad",
                                  "Cant Item", "Unidades"])
    col_canal  = _resolver(df_f, ["Canal Venta", "Canal_Venta",
                                  "Nomb Canal Venta", "Canal"])
    col_serv   = _resolver(df_f, ["Servicio", "Tipo Servicio",
                                  "Nomb Servicio", "Nombre Servicio"])
    col_mesero  = _resolver(df_f, ["Nombre Mesero", "Nomb Mesero"])
    col_propina = _resolver(df_f, ["Monto Propina", "Propina"])
    col_corr    = _resolver(df_f, ["Correlativo Pago"])
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

    # ── Filtros como chips popover en la franja ─────────────────────────
    # Aplican a TODOS los gráficos de Ventas (venta por día, semanal, matriz).
    # Canal Venta y Servicio solo aparecen si su columna existe en el parquet
    # (Servicio no siempre está — se salta silenciosamente).
    def _filtro_popover(col_col, key, label):
        if not col_col or col_col not in df_f.columns:
            return []
        opts = sorted(df_f[col_col].dropna().astype(str).unique().tolist())
        if not opts:
            return []
        _n = len(st.session_state.get(key) or [])
        _lbl = f":material/filter_alt: {label} :violet-badge[{_n}]" if _n else f":material/filter_alt: {label}"
        # El wrapper `chipwrap_<key>_on|off` es lo que el CSS necesita para
        # marcar un filtro ACTIVO (estilos/_50_fecha.py). Ventas dibuja sus
        # chips acá y no por `app.py::_chip_categorico`, así que sin esta
        # línea sus cuatro filtros se veían iguales estuvieran filtrando o no
        # — el único indicio era el badge con el número.
        with st.container(key=f"chipwrap_{key}_{'on' if _n else 'off'}"):
            with st.popover(_lbl, use_container_width=True):
                return st.pills(label, opts, selection_mode="multi",
                                key=key, label_visibility="collapsed") or []

    fam_sel, sub_sel, canal_sel, serv_sel = [], [], [], []
    with st.container(key="chips_ajuste_tabla"):
        _cols = st.columns([1, 1, 1, 1, 2])
        with _cols[0]:
            fam_sel = _filtro_popover(col_fam, "ventas_graf_filtro_fam", "Grupo")
        with _cols[1]:
            # Sub Grupo depende del filtro de Grupo (cascada)
            if col_sub and col_sub in df_f.columns:
                _dd = df_f
                if fam_sel and col_fam:
                    _dd = _dd[_dd[col_fam].astype(str).isin(fam_sel)]
                subs = sorted(_dd[col_sub].dropna().astype(str).unique().tolist())
                if subs:
                    _n = len(st.session_state.get("ventas_graf_filtro_sub") or [])
                    _lbl = f":material/account_tree: Sub Grupo :violet-badge[{_n}]" if _n else ":material/account_tree: Sub Grupo"
                    with st.popover(_lbl, use_container_width=True):
                        sub_sel = st.pills(
                            "Sub Grupo", subs, selection_mode="multi",
                            key="ventas_graf_filtro_sub",
                            label_visibility="collapsed") or []
        with _cols[2]:
            canal_sel = _filtro_popover(col_canal, "ventas_graf_filtro_canal", "Canal Venta")
        with _cols[3]:
            serv_sel = _filtro_popover(col_serv, "ventas_graf_filtro_serv", "Servicio")

    def _aplicar_chips(df):
        """Aplica los chips de la franja a CUALQUIER df de ventas, no solo al
        del rango cargado. Existe como función (y no inline) porque el
        comparativo "Año Pasado" trae su propio df desde R2 y tiene que
        quedar filtrado IGUAL que la vista actual — si no, se comparan
        barras filtradas contra barras sin filtrar. Defensiva con las
        columnas: el df del año pasado sale del mismo parquet, pero si
        alguna faltara, ese filtro se saltea en vez de reventar."""
        for _col, _sel in ((col_fam, fam_sel), (col_sub, sub_sel),
                           (col_canal, canal_sel), (col_serv, serv_sel)):
            if _sel and _col and _col in df.columns:
                df = df[df[_col].astype(str).isin(_sel)]
        return df

    d = _aplicar_chips(df_f)

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Ventas", d, {
        "Grupo": fam_sel, "Sub Grupo": sub_sel,
        "Canal": canal_sel, "Servicio": serv_sel,
    })

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _venta = pd.to_numeric(d[col_venta], errors="coerce").fillna(0)

    graf = _render_rail(_VENTAS_RAIL_CATEGORIAS, "ventas_graf_tipo",
                        btn_prefix="ventas_rail_btn_")

    if graf == "Tabla":
        if tabla_cb is not None:
            tabla_cb(d)
        else:
            st.info("La tabla no está disponible en este contexto.")
        return

    with st.container(border=True, key="ajuste_graf_card_izq_ventas"):

        # ── 0) Resumen ejecutivo: KPIs + candlestick diario + ticket + top
        # platos (graficos/ventas_resumen.py). Vive DENTRO de esta misma
        # card compartida (no arriba, entre chips y card) a propósito: así
        # no hace falta repetir la excepción de margin-top de la regla #38
        # de arquitectura.md — esa regla solo aplica a contenido en flujo
        # POR FUERA de `ajuste_graf_card_izq_ventas`.
        if graf == "Resumen ejecutivo":
            _ventas_resumen(d, col_venta, col_fecha, col_pax, col_pedido,
                            col_prod, col_cant)

        # ── 1) Venta bruta por día (Venta / Costo / Pax / Pax·Venta) ─────
        # Venta y Costo comparten el eje IZQUIERDO (soles). Pax va a un eje
        # derecho (conteo) y el ratio Pax/Venta a un tercer eje derecho
        # (escala minúscula), para que las 4 escalas no se pisen. El selector
        # de métricas (pills multi) permite prender/apagar cada serie.
        elif graf == "Venta por día" and col_fecha:
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

        # ── 1a-bis) Mapa de calor día × hora, hasta 4 períodos ───────────
        # Trae sus propios tramos (uno por período comparado) con
        # data.cargar_rango y les aplica _aplicar_chips, igual que el
        # comparativo: el `d` de acá está acotado al rango de la franja y los
        # períodos que se comparan pueden caer fuera de él.
        elif graf == "Mapa por hora":
            _ventas_horario(d, col_venta, col_fecha, col_pax=col_pax,
                            col_pedido=col_pedido, col_prod=col_prod,
                            col_cant=col_cant, col_fam=col_fam,
                            col_sub=col_sub, filtrar_cb=_aplicar_chips)

        # ── 1a) Comparativo día a día vs Año Pasado ──────────────────────
        # Trae su propio df del año pasado (data.cargar_rango) y le pasa
        # _aplicar_chips para que quede filtrado igual que `d`.
        elif graf == "Comparativo vs Año Pasado":
            _ventas_comparativo(d, col_venta, col_fecha, col_pax=col_pax,
                                col_pedido=col_pedido, col_prod=col_prod,
                                col_cant=col_cant, col_fam=col_fam,
                                col_sub=col_sub, filtrar_cb=_aplicar_chips)

        # ── 1b) Venta vs Compra por día (líneas arriba, Pax en barras abajo) ─
        # Vista aparte de "Venta por día": mismo espíritu que un gráfico
        # bursátil (precio arriba, volumen abajo). Compra viene de
        # compras.parquet, un reporte independiente — ver el docstring de
        # _ventas_cargar_compra_diaria sobre qué significa (y qué NO significa)
        # cruzarlo por fecha con Venta.
        elif graf == "Venta vs Compra" and col_fecha:
            _fe = pd.to_datetime(d[col_fecha], errors="coerce").dt.normalize()

            _base = pd.DataFrame({"dia": _fe, "venta": _venta})
            if col_costo:
                _base["costo"] = pd.to_numeric(d[col_costo], errors="coerce").fillna(0)
            _base = _base.dropna(subset=["dia"])
            _agg = {c: "sum" for c in _base.columns if c != "dia"}
            g = _base.groupby("dia", as_index=False).agg(_agg).sort_values("dia")

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

            if g.empty:
                st.info("Sin fechas válidas en el rango.")
            else:
                g_compra = _ventas_cargar_compra_diaria(g["dia"].min(), g["dia"].max())
                hay_compra = g_compra is not None
                if hay_compra:
                    g = g.merge(g_compra, on="dia", how="left")
                    g["compra"] = g["compra"].fillna(0)
                _ventas_venta_compra_dia(
                    g, hay_costo=bool(col_costo), hay_compra=hay_compra,
                    hay_pax=bool(col_pax))

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
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
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
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
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
            _ventas_matriz_agrupada(d, col_venta, col_costo, col_fam,
                                    col_sub, col_prod, col_fecha)

        # ── 5) Ranking & FoodCost (dashboard) ───────────────────────────
        elif graf == "Ranking & FoodCost":
            _ventas_ranking_foodcost(d, col_venta, col_costo, col_cant,
                                     col_fam, col_sub, col_prod, col_fecha)

        # ── 6) Meseros: propina real vs. esperada (regresión en vivo) ───
        elif graf == "Meseros":
            _ventas_ranking_meseros(d, col_mesero, col_propina, col_pedido,
                                    col_corr, col_pax, col_fecha, col_venta)
        else:
            st.info("No hay columnas suficientes para este gráfico.")
