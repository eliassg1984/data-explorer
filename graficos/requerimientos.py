"""
graficos.requerimientos — dashboard de Requerimientos. Mismo layout que
graficos/salidas.py (chips en franja blanca + rail derecho): son las dos
mitades de un mismo flujo de stock — ver docstring de
graficos/movimientos_comun.py, que aporta el chip Requerimiento/Salidas y la
vista "Comparativo".

El layout es el mismo, pero la LISTA DE VISTAS ya no: acá son 5 y en Salidas
7. Las dos que faltan salieron el 2026-09-05 (ver `_PILA` y arquitectura.md
regla #319) — no es un olvido de sincronización.

Columnas reales de requerimientos.parquet (confirmadas 2026-08-13, DuckDB
directo contra R2): Fecha Registro, Codigo Producto, Nombre Producto,
Sub Almacen (el área de producción que lo pide), Nombre Familia,
Nombre Subfamilia, Cantidad, Valor Item, Nombre Estado Requerimiento
(Procesado/Anulado/Generado).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills,
    _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.movimientos_comun import (
    _chip_movimientos, _comparativo_pedido_baja, _evolucion_movimientos,
)
from graficos import alturas

_REQ_RAIL_CATEGORIAS = (
    ("Vista", (("Evolución",         "Evolución"),
               ("Sub Almacén",       "Sub Almacén"),
               ("Top productos",     "Top productos"),
               ("Comparativo",       "Pedido vs Baja"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — los dos reportes de Movimientos comparten ítem de nav y
# la vista Comparativo (ver movimientos_comun.py), pero desde el 2026-09-05
# ya no son gemelos: acá se sacaron "Estado" y "Subalm. × estado" a pedido,
# y Salidas conserva sus dos equivalentes ("Tipo descargo" y "Subalm. ×
# tipo") porque el tipo de descargo no es un estado, es el motivo de la baja.
# El estado NO desaparece del reporte: sigue siendo el color de la Evolución.
# Las 5 vistas comparten el mismo rango, así que va UNA sola pila.
_PILA = (
    ("req_sec_evolucion",   "Evolución"),
    ("req_sec_subalmacen",  "Sub Almacén"),
    ("req_sec_top",         "Top productos"),
    ("req_sec_comparativo", "Comparativo"),
    ("req_sec_tabla",       "Tabla"),
)


def renderizar_graficos_requerimientos(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Requerimientos: KPIs + evolución temporal + composición
    por sub almacén (área que pide) + comparativo contra Salidas.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py). Se le
    pasa `d` — el df ya filtrado por los chips propios (Sub Almacén/
    Familia) —, igual que Salidas, para que la Tabla no tenga un estado de
    filtros distinto al de los gráficos."""
    _chip_movimientos("Requerimientos")

    col_prod  = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_sub   = _resolver(df_f, ["Sub Almacen", "SUB ALMACEN", "Subalmacen", "Sub Almacén"])
    col_fam   = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
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
        if graf == "Sub Almacén" and col_sub:
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

    def _dib_evolucion():
        # La Evolución ya no es de Requerimientos: es la de MOVIMIENTOS, con
        # los dos lados en barras agrupadas (2026-09-05, a pedido). Vive en
        # `movimientos_comun.py` y la dibuja igual Salidas — por eso recibe
        # los chips en vez de leerlos: la función no sabe de qué lado entró.
        with st.container(border=True, key="ajuste_graf_card_izq_req_evolucion"):
            _evolucion_movimientos(fam_sel=fam_sel, sub_sel=sub_sel)

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
        "req_sec_evolucion":   _dib_evolucion,
        "req_sec_subalmacen":  _seccion("subalmacen", "Sub Almacén"),
        "req_sec_top":         _seccion("top", "Top productos"),
        "req_sec_comparativo": _dib_comparativo,
        "req_sec_tabla":       _dib_tabla,
    }

    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
