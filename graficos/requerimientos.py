"""
graficos.requerimientos — dashboard de Requerimientos. Mismo layout que
graficos/salidas.py (chips en franja blanca + rail derecho): son las dos
mitades de un mismo flujo de stock — ver docstring de
graficos/movimientos_comun.py, que aporta el chip Requerimiento/Salidas y la
vista "Comparativo".

Columnas reales de requerimientos.parquet (confirmadas 2026-08-13, DuckDB
directo contra R2): Fecha Registro, Codigo Producto, Nombre Producto,
Sub Almacen (el área de producción que lo pide), Nombre Familia,
Nombre Subfamilia, Cantidad, Valor Item, Nombre Estado Requerimiento
(Procesado/Anulado/Generado).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills,
    PALETA_CALLAI, _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.compras import _periodo_serie
from graficos.movimientos_comun import _chip_movimientos, _comparativo_pedido_baja
from graficos import alturas

_REQ_RAIL_CATEGORIAS = (
    ("Vista", (("Evolución",         "Evolución"),
               ("Sub Almacén",       "Sub Almacén"),
               ("Estado",            "Estado"),
               ("Cruce",             "Subalm. × estado"),
               ("Top productos",     "Top productos"),
               ("Comparativo",       "Pedido vs Baja"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — gemela de la de `graficos/salidas.py` (los dos reportes
# comparten ítem de nav y la vista Comparativo, ver movimientos_comun.py).
# Las 7 vistas comparten el mismo rango, así que va UNA sola pila.
_PILA = (
    ("req_sec_evolucion",   "Evolución"),
    ("req_sec_subalmacen",  "Sub Almacén"),
    ("req_sec_estado",      "Estado"),
    ("req_sec_cruce",       "Cruce"),
    ("req_sec_top",         "Top productos"),
    ("req_sec_comparativo", "Comparativo"),
    ("req_sec_tabla",       "Tabla"),
)


def renderizar_graficos_requerimientos(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Requerimientos: KPIs + evolución temporal + composición
    por sub almacén (área que pide) y estado + comparativo contra Salidas.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py). Se le
    pasa `d` — el df ya filtrado por los chips propios (Sub Almacén/
    Familia) —, igual que Salidas, para que la Tabla no tenga un estado de
    filtros distinto al de los gráficos."""
    _chip_movimientos("Requerimientos")

    col_fecha = _resolver(df_f, ["Fecha Registro", "FECHA REGISTRO"])
    col_prod  = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_sub   = _resolver(df_f, ["Sub Almacen", "SUB ALMACEN", "Subalmacen", "Sub Almacén"])
    col_fam   = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_estado = _resolver(df_f, ["Nombre Estado Requerimiento", "NOMBRE ESTADO REQUERIMIENTO"])
    col_cant  = _resolver(df_f, ["Cantidad", "CANTIDAD"])
    col_val   = _resolver(df_f, ["Valor Item", "VALOR ITEM", "Valorizado"])

    if not col_val and not col_cant:
        st.warning("No se encontraron las columnas de cantidad/valor del requerimiento. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Sub Almacén / Familia como chips en la franja ─────────────
    sub_sel, fam_sel = [], []
    metrica = "Valorizado" if col_val else "Cantidad"
    with compartimento_filtros(contar_filtros("req_graf_filtro_sub",
                                              "req_graf_filtro_fam")):
        _, sub_sel = filtro_pills(df_f, col_sub,
                                  "req_graf_filtro_sub", "Sub Almacén")
        _, fam_sel = filtro_pills(df_f, col_fam,
                                  "req_graf_filtro_fam", "Familia")

    d = df_f
    if sub_sel and col_sub:
        d = d[d[col_sub].astype(str).isin(sub_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Requerimientos", d,
                         {"Sub Almacén": sub_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    es_valor = (metrica == "Valorizado")
    col_metrica = col_val if es_valor else col_cant
    _met = pd.to_numeric(d[col_metrica], errors="coerce").fillna(0)
    _fmt_pref = "S/ " if es_valor else ""
    _fmt_num = ",.2f" if es_valor else ",.0f"
    _hover_m = "%{fullData.name}<br>%{x}: " + _fmt_pref + "%{y:" + _fmt_num + "}<extra></extra>"

    # ── KPIs (calculados sobre `d`, ya filtrado por los chips) ────────────
    kpis = st.columns(3)
    kpis[0].metric("📄 Registros", f"{len(d):,}")
    if col_cant:
        kpis[1].metric("📦 Cantidad total",
                       f"{pd.to_numeric(d[col_cant], errors='coerce').fillna(0).sum():,.0f}")
    if col_val:
        kpis[2].metric("💰 Valorizado total",
                       f"S/ {pd.to_numeric(d[col_val], errors='coerce').fillna(0).sum():,.2f}")

    # El rail ya no ELIGE: con `secciones` marca dónde estás y scrollea.
    _render_rail(_REQ_RAIL_CATEGORIAS, "req_graf_tipo",
                 btn_prefix="req_rail_btn_", secciones=_PILA)

    # La cadena `if graf == ...` de abajo NO se toca: pasa de vivir dentro
    # de un `with st.container(...)` compartido por las cinco vistas de
    # gráfico a ser el cuerpo de esta función, que cada sección llama con SU
    # nombre de vista. Mismo movimiento que en `graficos/salidas.py`.
    def _cuerpo_grafico(graf):
        if graf == "Evolución" and col_fecha:
            _fe = pd.to_datetime(d[col_fecha], errors="coerce")
            cg1, _sp = st.columns([1.4, 3.6])
            with cg1:
                gran = st.pills(
                    "Agrupar por", ["Día", "Semana", "Mes", "Año"],
                    default="Mes", key="req_graf_gran",
                    label_visibility="collapsed",
                ) or "Mes"
            per = _periodo_serie(_fe, gran)
            if col_estado:
                g = (pd.DataFrame({"per": per, "estado": d[col_estado].astype(str), "m": _met})
                     .dropna(subset=["per"])
                     .groupby(["per", "estado"], as_index=False)["m"].sum())
                orden = sorted(g["per"].unique())
                fig = px.bar(g, x="per", y="m", color="estado",
                             category_orders={"per": orden})
                fig.update_layout(barmode="stack")
            else:
                g = (pd.DataFrame({"per": per, "m": _met})
                     .dropna(subset=["per"]).groupby("per", as_index=False)["m"].sum())
                fig = px.bar(g, x="per", y="m")
            _compras_layout(fig, alto=alturas.PROTAGONISTA)
            fig.update_layout(
                title=f"Evolución de {metrica.lower()} por estado ({gran.lower()})"
                      if col_estado else f"Evolución de {metrica.lower()} ({gran.lower()})",
                xaxis_title=None, yaxis_title=None,
                legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=10)),
            )
            fig.update_xaxes(type="category")
            fig.update_traces(hovertemplate=_hover_m)
            st.plotly_chart(fig, use_container_width=True, key="req_g_evolucion")

        elif graf == "Sub Almacén" and col_sub:
            serie = _met.groupby(d[col_sub].astype(str)).sum().sort_values(ascending=True)
            if serie.empty:
                st.info("Sin datos.")
            else:
                _fmt = "S/ {:,.0f}" if es_valor else "{:,.0f}"
                fig = go.Figure(go.Bar(
                    x=serie.values,
                    y=[_compras_truncar(i, 28) for i in serie.index],
                    orientation="h",
                    marker=dict(color=ACENTO, opacity=0.85),
                    text=[_fmt.format(v) for v in serie.values],
                    textposition="outside", cliponaxis=False,
                ))
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
                fig.update_layout(title=f"{metrica} por sub almacén")
                fig.update_xaxes(visible=False)
                st.plotly_chart(fig, use_container_width=True, key="req_g_subalmacen")

        elif graf == "Estado" and col_estado:
            serie = _met.groupby(d[col_estado].astype(str)).sum().sort_values(ascending=False)
            if serie.empty:
                st.info("Sin datos.")
            else:
                fig = go.Figure(go.Pie(
                    labels=serie.index, values=serie.values, hole=0.45,
                    marker=dict(colors=PALETA_CALLAI * 4),
                    textinfo="label+percent",
                    hovertemplate=("%{label}<br>" + _fmt_pref
                                   + "%{value:" + _fmt_num + "} (%{percent})<extra></extra>"),
                ))
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
                fig.update_layout(
                    title=f"Participación de {metrica.lower()} por estado",
                    showlegend=False)
                st.plotly_chart(fig, use_container_width=True, key="req_g_estado")

        elif graf == "Cruce" and col_sub and col_estado:
            g = (pd.DataFrame({"sub": d[col_sub].astype(str),
                               "estado": d[col_estado].astype(str), "m": _met})
                 .groupby(["sub", "estado"], as_index=False)["m"].sum())
            orden = (g.groupby("sub")["m"].sum()
                     .sort_values(ascending=False).index.tolist())
            fig = px.bar(g, x="sub", y="m", color="estado",
                         category_orders={"sub": orden})
            _compras_layout(fig, alto=alturas.PROTAGONISTA)
            fig.update_layout(
                title=f"{metrica} por sub almacén, desglosado por estado",
                barmode="stack", xaxis_title=None, yaxis_title=None,
                legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=10)),
            )
            fig.update_traces(hovertemplate=_hover_m)
            st.plotly_chart(fig, use_container_width=True, key="req_g_cruce")

        elif graf == "Top productos" and col_prod:
            serie = _met.groupby(d[col_prod].astype(str)).sum().nlargest(10).sort_values()
            if serie.empty:
                st.info("Sin datos.")
            else:
                _fmt = "S/ {:,.0f}" if es_valor else "{:,.0f}"
                fig = go.Figure(go.Bar(
                    x=serie.values,
                    y=[_compras_truncar(i, 34) for i in serie.index],
                    orientation="h",
                    marker=dict(color=ACENTO, opacity=0.85),
                    text=[_fmt.format(v) for v in serie.values],
                    textposition="outside", cliponaxis=False,
                ))
                _compras_layout(fig, alto=alturas.PROTAGONISTA)
                fig.update_layout(title=f"Top 10 productos por {metrica.lower()}")
                fig.update_xaxes(visible=False)
                st.plotly_chart(fig, use_container_width=True, key="req_g_top_productos")

        else:
            st.info("No hay columnas suficientes para este gráfico.")

    def _seccion(slug, nombre):
        """Envuelve una vista de gráfico en su propia tarjeta.

        Conserva el prefijo `ajuste_graf_card_` (de ahí cuelga el CSS de
        tarjeta) y suma el sufijo de la vista: antes las cinco compartían
        `ajuste_graf_card_izq_req`, lo que funcionaba sólo porque nunca
        coexistían."""
        def _f():
            with st.container(border=True,
                              key=f"ajuste_graf_card_izq_req_{slug}"):
                _cuerpo_grafico(nombre)
        return _f

    def _dib_comparativo():
        with st.container(border=True, key="ajuste_graf_card_izq_req_comparativo"):
            _comparativo_pedido_baja(key_prefix="req_cmp")

    def _dib_tabla():
        with st.container(border=True, key="ajuste_graf_card_izq_req_tabla"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "req_sec_evolucion":   _seccion("evolucion", "Evolución"),
        "req_sec_subalmacen":  _seccion("subalmacen", "Sub Almacén"),
        "req_sec_estado":      _seccion("estado", "Estado"),
        "req_sec_cruce":       _seccion("cruce", "Cruce"),
        "req_sec_top":         _seccion("top", "Top productos"),
        "req_sec_comparativo": _dib_comparativo,
        "req_sec_tabla":       _dib_tabla,
    }

    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
