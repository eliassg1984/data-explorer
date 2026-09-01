"""
graficos.salidas — dashboard de Salidas. Layout unificado con chips en franja
blanca + rail derecho (mismo patrón que graficos/inventario.py). Comparte
ítem de nav con Requerimientos ("Movimientos") — ver docstring de
graficos/movimientos_comun.py, que aporta el chip Requerimiento/Salidas y la
vista "Comparativo".

Columnas reales de salidas.parquet (confirmadas 2026-08-04, ver data.py):
    Nombre Producto, Fecha registro, Cant Salida, Valor Neto, Tipo Descargo,
    Sub Almacen, Nombre Familia.
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

# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py). "Cruce" (Subalmacén × Tipo descargo) responde a la
# pregunta que la tabla sola no contesta bien: qué tipos de descargo
# predominan en cada subalmacén.
_SALIDAS_RAIL_CATEGORIAS = (
    ("Vista", (("Evolución",         "Evolución"),
               ("Subalmacén",        "Subalmacén"),
               ("Tipo descargo",     "Tipo descargo"),
               ("Cruce",             "Subalm. × tipo"),
               ("Top productos",     "Top productos"),
               ("Comparativo",       "Pedido vs Baja"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué está en `graficos/compras/__init__.py::_PILA`). Las 7
# vistas comparten el mismo rango de fecha, así que va UNA sola pila.
_PILA = (
    ("sal_sec_evolucion",  "Evolución"),
    ("sal_sec_subalmacen", "Subalmacén"),
    ("sal_sec_tipo",       "Tipo descargo"),
    ("sal_sec_cruce",      "Cruce"),
    ("sal_sec_top",        "Top productos"),
    ("sal_sec_comparativo", "Comparativo"),
    ("sal_sec_tabla",      "Tabla"),
)


def renderizar_graficos_salidas(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Salidas: KPIs + evolución temporal (con granularidad
    Día/Semana/Mes/Año) + composición por subalmacén y tipo de descargo.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py). Se le
    pasa `d` — el df ya filtrado por los chips propios (Sub Almacén/
    Familia) y por la métrica elegida — igual que Ventas/Inventario, para
    no tener un estado de filtros distinto entre Tabla y gráficos."""
    _chip_movimientos("Salidas")

    col_fecha = _resolver(df_f, ["Fecha registro", "Fecha_registro", "FECHA REGISTRO"])
    col_prod  = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_sub   = _resolver(df_f, ["Sub Almacen", "SUB ALMACEN", "Subalmacen", "Sub Almacén"])
    col_fam   = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_tipo  = _resolver(df_f, ["Tipo Descargo", "TIPO DESCARGO", "Tipo de Descargo"])
    col_cant  = _resolver(df_f, ["Cant Salida", "CANT SALIDA", "Cantidad Salida"])
    col_val   = _resolver(df_f, ["Valor Neto", "VALOR NETO", "Valorizado"])

    if not col_val and not col_cant:
        st.warning("No se encontraron las columnas de cantidad/valor de salida. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Sub Almacén / Familia como chips en la franja ─────────────
    # Métrica fija en "Valorizado" (2026-08-07): el toggle Valorizado/
    # Cantidad se sacó de la franja a pedido — Salidas siempre reporta en
    # soles. `col_cant` queda como fallback silencioso solo si algún día
    # faltara la columna de valor (mismo criterio que el resto del archivo:
    # no romper si el parquet cambia), pero no hay UI para elegir Cantidad.
    sub_sel, fam_sel = [], []
    metrica = "Valorizado" if col_val else "Cantidad"
    with compartimento_filtros(contar_filtros("sal_graf_filtro_sub",
                                              "sal_graf_filtro_fam")):
        _, sub_sel = filtro_pills(df_f, col_sub,
                                  "sal_graf_filtro_sub", "Sub Almacén")
        _, fam_sel = filtro_pills(df_f, col_fam,
                                  "sal_graf_filtro_fam", "Familia")

    d = df_f
    if sub_sel and col_sub:
        d = d[d[col_sub].astype(str).isin(sub_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Salidas", d,
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
    _render_rail(_SALIDAS_RAIL_CATEGORIAS, "sal_graf_tipo",
                 btn_prefix="sal_rail_btn_", secciones=_PILA)

    # La cadena `if graf == ...` de abajo NO se toca: pasa de vivir dentro de
    # un `with st.container(...)` compartido por las cinco vistas de gráfico
    # a ser el cuerpo de esta función, que cada sección llama con SU nombre
    # de vista. Los cuerpos quedan idénticos —misma indentación, mismas
    # keys de figura— y lo único que cambia es quién los envuelve.
    def _cuerpo_grafico(graf):
        if graf == "Evolución" and col_fecha:
            _fe = pd.to_datetime(d[col_fecha], errors="coerce")
            cg1, _sp = st.columns([1.4, 3.6])
            with cg1:
                gran = st.pills(
                    "Agrupar por", ["Día", "Semana", "Mes", "Año"],
                    default="Mes", key="sal_graf_gran",
                    label_visibility="collapsed",
                ) or "Mes"
            per = _periodo_serie(_fe, gran)
            if col_tipo:
                g = (pd.DataFrame({"per": per, "tipo": d[col_tipo].astype(str), "m": _met})
                     .dropna(subset=["per"])
                     .groupby(["per", "tipo"], as_index=False)["m"].sum())
                orden = sorted(g["per"].unique())
                fig = px.bar(g, x="per", y="m", color="tipo",
                             category_orders={"per": orden})
                fig.update_layout(barmode="stack")
            else:
                g = (pd.DataFrame({"per": per, "m": _met})
                     .dropna(subset=["per"]).groupby("per", as_index=False)["m"].sum())
                fig = px.bar(g, x="per", y="m")
            _compras_layout(fig, alto=alturas.PROTAGONISTA)
            fig.update_layout(
                title=f"Evolución de {metrica.lower()} por tipo de descargo ({gran.lower()})"
                      if col_tipo else f"Evolución de {metrica.lower()} ({gran.lower()})",
                xaxis_title=None, yaxis_title=None,
                legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=10)),
            )
            fig.update_xaxes(type="category")
            fig.update_traces(hovertemplate=_hover_m)
            st.plotly_chart(fig, use_container_width=True, key="sal_g_evolucion")

        elif graf == "Subalmacén" and col_sub:
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
                fig.update_layout(title=f"{metrica} por subalmacén")
                fig.update_xaxes(visible=False)
                st.plotly_chart(fig, use_container_width=True, key="sal_g_subalmacen")

        elif graf == "Tipo descargo" and col_tipo:
            serie = _met.groupby(d[col_tipo].astype(str)).sum().sort_values(ascending=False)
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
                    title=f"Participación de {metrica.lower()} por tipo de descargo",
                    showlegend=False)
                st.plotly_chart(fig, use_container_width=True, key="sal_g_tipo")

        elif graf == "Cruce" and col_sub and col_tipo:
            g = (pd.DataFrame({"sub": d[col_sub].astype(str),
                               "tipo": d[col_tipo].astype(str), "m": _met})
                 .groupby(["sub", "tipo"], as_index=False)["m"].sum())
            orden = (g.groupby("sub")["m"].sum()
                     .sort_values(ascending=False).index.tolist())
            fig = px.bar(g, x="sub", y="m", color="tipo",
                         category_orders={"sub": orden})
            _compras_layout(fig, alto=alturas.PROTAGONISTA)
            fig.update_layout(
                title=f"{metrica} por subalmacén, desglosado por tipo de descargo",
                barmode="stack", xaxis_title=None, yaxis_title=None,
                legend=dict(orientation="h", y=-0.25, x=0, font=dict(size=10)),
            )
            fig.update_traces(hovertemplate=_hover_m)
            st.plotly_chart(fig, use_container_width=True, key="sal_g_cruce")

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
                st.plotly_chart(fig, use_container_width=True, key="sal_g_top_productos")

        else:
            st.info("No hay columnas suficientes para este gráfico.")

    def _seccion(slug, nombre):
        """Envuelve una vista de gráfico en su propia tarjeta.

        La key conserva el prefijo `ajuste_graf_card_` (de ahí cuelga el CSS
        de tarjeta, `estilos/_80_cards.py`) y suma el sufijo de la vista:
        antes las cinco compartían `ajuste_graf_card_izq_sal`, lo que
        funcionaba porque nunca coexistían. Apiladas serían cinco widgets
        con la misma key, que en Streamlit es una excepción."""
        def _f():
            with st.container(border=True,
                              key=f"ajuste_graf_card_izq_sal_{slug}"):
                _cuerpo_grafico(nombre)
        return _f

    def _dib_comparativo():
        with st.container(border=True, key="ajuste_graf_card_izq_sal_comparativo"):
            _comparativo_pedido_baja(key_prefix="sal_cmp")

    def _dib_tabla():
        with st.container(border=True, key="ajuste_graf_card_izq_sal_tabla"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "sal_sec_evolucion":   _seccion("evolucion", "Evolución"),
        "sal_sec_subalmacen":  _seccion("subalmacen", "Subalmacén"),
        "sal_sec_tipo":        _seccion("tipo", "Tipo descargo"),
        "sal_sec_cruce":       _seccion("cruce", "Cruce"),
        "sal_sec_top":         _seccion("top", "Top productos"),
        "sal_sec_comparativo": _dib_comparativo,
        "sal_sec_tabla":       _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga (mismo bucle que Compras, Receta Base, Ajuste
    # e Inventario).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
