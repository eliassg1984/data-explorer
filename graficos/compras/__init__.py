"""graficos.compras - dashboard de Compras (4 drills).

Este modulo era un unico compras.py de 2.835 lineas; desde el refactor de
2026-08-01 es un paquete con un drill por archivo, igual que graficos/ tiene
un dashboard por archivo.

    _comun.py       helpers compartidos (movil, seleccion, mini barras)
    proveedor.py    drill de Proveedor (el mas grande)
    familia.py      drill Familia -> Subfamilia -> productos
    cantidad.py     top de productos por cantidad
    evolucion.py    evolucion de proveedores en el tiempo

Punto de entrada publico: renderizar_graficos_compras (lo consume el 
dispatcher de graficos/__init__.py). Vive aca abajo junto a la config del
rail derecho, que es lo que decide que drill se muestra.

_first_point y _periodo_serie se re-exportan porque test_graficos.py los
importa desde graficos.compras.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, GRIS_BORDE
from utils import _norm
from graficos.base import (
    PALETA_CALLAI, _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos
)
from graficos.constructor import _constructor_grafico
from graficos.compras._comun import (  # noqa: F401  (re-export)
    _compras_mini_barras, _es_movil, _first_point, _periodo_serie,
)
from graficos.compras.proveedor import _compras_proveedor_drill
from graficos.compras.familia import _compras_familia_drill
from graficos.compras.cantidad import _compras_cantidad_producto
from graficos.compras.evolucion import _compras_evolucion_proveedores
from graficos.compras.volatilidad import _compras_volatilidad_drill
from graficos import alturas




# Rail derecho de Compras — cabecera "Compras / Gráficos" + secciones
# agrupadas por categoría (variante 2). El id interno (izquierda de cada tupla)
# es el string que consume el resto del dashboard; el label (derecha) es lo que
# se pinta en el botón del rail.
_COMPRAS_RAIL_CATEGORIAS = (
    ("Dimensión", (("Familia",              "Familia"),
                   ("Proveedor",            "Proveedor"),
                   ("Evolución proveedor",  "Evolución prov."))),
    ("Precios",   (("Precio top 10",        "Top 10"),
                   ("Precio por compra",    "Por compra"),
                   ("Precio vs año pasado", "Vs año pasado"),
                   ("Volatilidad",          "Volatilidad"))),
    ("Cantidad",  (("Cantidad vs año pasado", "Vs año pasado"),
                   ("Cantidad por producto",  "Por producto"))),
    ("Más",       (("Semanal",              "Semanal"),
                   ("Vs año anterior",      "Vs año ant."),
                   ("Personalizado",        "Personalizado"),
                   ("Tabla",                "Tabla"))),
)

def renderizar_graficos_compras(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard dedicado de Compras: 5 gráficos con pestañas + 5 mini-tops.

    `tabla_cb` se acepta por uniformidad de firma con el resto de
    dashboards (ver graficos/__init__.py) pero NO se usa: la vista Tabla
    de Compras es un item más de su propio rail y la arma este módulo,
    con los mismos chips Familia/Subfamilia que los gráficos."""
    col_fam    = _resolver(df_f, ["Familia", "Nombre Familia"])
    col_subfam = _resolver(df_f, ["Subfamilia", "Nombre Subfamilia"])
    col_prov   = _resolver(df_f, ["Nombre_proveedor", "Nombre proveedor", "Proveedor"])
    col_prod   = _resolver(df_f, ["Nombre_producto", "Nombre producto", "Producto"])
    col_um     = _resolver(df_f, ["Unidad de Ingreso", "Unidad_de_ingreso",
                                  "Unidad Ingreso", "Unidad Kardex", "Unidad_medida",
                                  "Unidad medida", "Unidad de medida", "Unidad_compra",
                                  "Unidad compra", "Unidad", "UM", "Und"])
    col_cant   = _resolver(df_f, ["Cantidad_compra", "Cantidad compra", "Cantidad"])
    col_valor  = _resolver(df_f, ["Valor_compra", "Valor compra", "Importe Total", "Valorizado"])
    col_val_aa = _resolver(df_f, ["Valor_ano_anterior", "Valor año anterior"])
    col_punit  = _resolver(df_f, ["Precio_unit", "Precio unit", "Precio Unitario"])
    col_punit_ant = _resolver(df_f, ["Ultimo_precio_unit", "Ultimo precio unit",
                                     "Ultimo_anterior", "Ultimo anterior"])
    col_fecha  = _resolver(df_f, ["Fecha_documento", "Fecha documento",
                                  "Fecha_registro", "Fecha registro", "FECHA"])
    col_docu   = _resolver(df_f, ["Num Documento", "Num_Documento",
                                  "Numero Documento", "Numero_documento",
                                  "Nro Documento", "Nro_Documento", "Num Doc",
                                  "N Documento", "Documento", "Comprobante"])
    # Solo la usa el drill Volatilidad (mezclar monedas en una misma serie de
    # precio sería incorrecto). Ninguna otra vista de Compras la resuelve, y
    # el demo local no la trae — por eso el drill la trata como opcional.
    col_moneda = _resolver(df_f, ["Tipo_moneda", "Tipo Moneda", "Moneda"])
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
                    _lbl = f"Familia :violet-badge[{_n}]" if _n else "Familia"
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
                    _lbl = f"Subfamilia :violet-badge[{_n}]" if _n else "Subfamilia"
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

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Compras", d,
                         {"Familia": fam_sel, "Subfamilia": sub_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # Data SIN filtro de fecha (para el toggle "Todo el histórico" del Panel B
    # del drill Proveedor). Se le aplican los mismos chips Familia/Subfamilia,
    # que no son de fecha. Si no llega df_full, cae a df_f (mismo comportamiento).
    d_full = df_full if df_full is not None else df_f
    if fam_sel and col_fam and col_fam in d_full.columns:
        d_full = d_full[d_full[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_subfam and col_subfam in d_full.columns:
        d_full = d_full[d_full[col_subfam].astype(str).isin(sub_sel)]

    _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    _mes = None
    if col_fecha and col_fecha in d.columns:
        _f = pd.to_datetime(d[col_fecha], errors="coerce")
        _mes = _f.dt.to_period("M").astype(str)

    opciones = ["Familia", "Proveedor", "Evolución proveedor",
                "Precio top 10", "Precio por compra",
                "Precio vs año pasado", "Volatilidad", "Cantidad vs año pasado",
                "Cantidad por producto",
                "Semanal", "Vs año anterior", "Personalizado", "Tabla"]

    # Rail vertical fijo al borde DERECHO (componente compartido _render_rail):
    # selector de tipo de gráfico agrupado por categoría. El activo se marca
    # con type="primary"; la selección se persiste en compras_graf_tipo.
    graf = _render_rail(_COMPRAS_RAIL_CATEGORIAS, "compras_graf_tipo")
    if graf not in opciones:
        graf = opciones[0]

    # Tabla: usa el mismo AgGrid de la vista Tabla, pero como una opción más
    # del selector. `d` ya viene filtrado por los chips Familia/Subfamilia.
    if graf == "Tabla":
        from tablas import renderizar_aggrid_compras as _render_tabla_compras
        from estilos import TAM_FUENTE
        _font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam", "Mediano"), 14)
        _render_tabla_compras(d, _font_px)
        return

    # Constructor: ancho completo, sin panel de mini-tops.
    if graf == "Personalizado":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _constructor_grafico(d, "compras")
        return

    # Cantidad por producto: ancho completo (KPIs + controles + barras).
    if graf == "Cantidad por producto":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _compras_cantidad_producto(d, col_prod, col_cant, col_valor,
                                       col_punit, col_fecha)
        return

    # Familia: ancho completo (dashboard con drill Familia→Subfamilia→productos).
    if graf == "Familia":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _compras_familia_drill(d, col_fam, col_subfam, col_prod,
                                   col_valor, col_cant, col_fecha)
        return

    # Proveedor: ancho completo (drill Proveedor→productos→proveedores del prod.).
    # Sin borde externo: cada uno de los 4 bloques internos (gráfico, panel A,
    # panel B, tabla AgGrid) lleva su propio borde para separación visual
    # limpia sin cajas anidadas.
    if graf == "Proveedor":
        with st.container(key="compras_prov_drill_wrap"):
            _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                                     col_punit, col_um, col_fecha, col_docu,
                                     d_full=d_full)
        return

    # Evolución proveedor: ancho completo (dashboard rediseñado con drill y detalle).
    if graf == "Evolución proveedor":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _compras_evolucion_proveedores(d, col_prov, col_prod, col_cant,
                                           col_valor, col_punit, col_fecha)
        return

    # Volatilidad: ranking de insumos por variación de precio semanal +
    # candlestick del insumo elegido + compras de la semana clickeada.
    if graf == "Volatilidad":
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                                       col_valor, col_cant, col_um, col_moneda)
        return

    col_izq, col_der = st.columns([1.7, 1])

    with col_izq:
        with st.container(border=True, key="ajuste_graf_card_izq_compras"):
            if graf == "Precio top 10" and col_prod and col_punit and _mes is not None:
                top = _valor.groupby(d[col_prod].astype(str)).sum().nlargest(10).index
                _pu = pd.to_numeric(d[col_punit], errors="coerce")
                dd = pd.DataFrame({"mes": _mes, "prod": d[col_prod].astype(str),
                                   "precio": _pu})
                dd = dd[dd["prod"].isin(top)].dropna(subset=["precio"])
                piv = dd.groupby(["mes", "prod"])["precio"].mean().reset_index()
                fig = px.line(piv, x="mes", y="precio", color="prod", markers=True)
                fig.for_each_trace(lambda t: t.update(name=_compras_truncar(t.name, 22)))
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
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
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
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
                    _compras_layout(fig, alto=alturas.PROTAGONISTA)
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
                    _compras_layout(fig, alto=alturas.PROTAGONISTA)
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
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
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
