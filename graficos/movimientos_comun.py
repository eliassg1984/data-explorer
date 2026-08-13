"""
graficos.movimientos_comun — infraestructura COMPARTIDA entre Requerimientos
y Salidas.

Los dos parquets describen las DOS MITADES de un mismo flujo de stock:
Requerimiento es lo que Almacén Central le entrega a un área de producción
(Cocina, Barra, Pastelería...); Salidas es la baja que esa misma área
registra después (consumo, merma, evento — ver "Tipo Descargo"). Comparten
UN ítem de nav ("Movimientos", ver `grupo_nav` en
navegacion.py::inject_navegacion) con un chip Requerimiento/Salidas
(`_chip_movimientos`, mismo mecanismo que
`graficos/recetas_comun.py::_chip_fuente`: clic en el lado no activo NAVEGA,
no filtra).

A diferencia de Receta Base/Venta (0% overlap confirmado, por eso esas dos
NUNCA se cruzan — ver `recetas_comun.py`), acá SÍ hay overlap real de
producto: 726 de los 968 productos de Salidas (75%) también aparecen en
Requerimientos, confirmado con DuckDB directo contra R2 real 2026-08-13. Por
eso este módulo también trae `_comparativo_pedido_baja`, una vista que carga
AMBOS parquets y los cruza — precedente de carga cruzada entre dashboards:
`recetas_comun.py::_cargar_flujo_compras` ya carga compras.parquet desde
dentro de Receta Base/Venta.

Dos límites reales del DATO, no del código — no se resuelven con más
columnas, hay que diseñar la vista alrededor de ellos:
  - No hay llave documento-a-documento: `COD REQUERIMIENTO` y `COD SALIDA`
    numeran en secuencias independientes. El cruce es agregado por
    producto/familia/período ("¿cuánto entró vs cuánto se dio de baja en
    este mes?"), nunca "este Requerimiento se resolvió con esta Salida".
  - `salidas.parquet` NO trae el área/sub almacén que originó la baja (solo
    Requerimientos tiene esa columna) — el comparativo no puede desglosar
    por área, solo por producto/familia.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import cargar as _cargar_reporte
from tema import ACENTO, AJUSTE_NEG, AJUSTE_POS, GRIS_TEXTO_SUAVE
from graficos.base import _compras_layout, _compras_truncar, _resolver
from graficos.compras import _periodo_serie


# ─── Chip de fuente (mismo mecanismo que recetas_comun._chip_fuente) ───────
def _chip_movimientos(reporte_activo):
    """Segmented control Requerimiento/Salidas arriba del rail — separa los
    dos reportes dentro del mismo ítem de nav ("Movimientos"). Clic en el
    lado NO activo NAVEGA (session_state['_nav_reporte'] + rerun) en vez de
    filtrar, así reusa todo el pipeline de carga de app.py sin duplicar
    nada acá. La key incluye `reporte_activo` por la misma razón que en
    `_chip_fuente`: si el usuario entra por el RAIL (no por este chip) una
    key fija dejaría "pegado" el valor de la sesión anterior."""
    etiquetas = {"Requerimientos": "Requerimiento", "Salidas": "Salidas"}
    inverso = {v: k for k, v in etiquetas.items()}
    sel = st.segmented_control(
        "Fuente", list(etiquetas.values()),
        default=etiquetas.get(reporte_activo, "Requerimiento"),
        key=f"mov_fuente_chip_{reporte_activo}",
        label_visibility="collapsed",
    )
    destino = inverso.get(sel, reporte_activo)
    if destino != reporte_activo:
        st.session_state["_nav_reporte"] = destino
        st.rerun()


# ─── Comparativo Pedido vs Baja ─────────────────────────────────────────────
def _cargar_lado(archivo, *, col_fecha_cand, col_cod_cand, col_prod_cand,
                 col_fam_cand, col_valor_cand, col_cant_cand, col_estado_cand,
                 estados_excluir):
    """Carga y normaliza un lado (Requerimientos o Salidas) del comparativo:
    resuelve columnas, filtra estados anulados y devuelve un df con columnas
    de trabajo `_fecha/_cod/_prod/_fam/_valor/_cant`, o None si falta alguna
    columna imprescindible (fecha, código de producto, nombre, y al menos
    una métrica)."""
    df = _cargar_reporte(archivo)
    if df is None or df.empty:
        return None
    col_fecha = _resolver(df, col_fecha_cand)
    col_cod = _resolver(df, col_cod_cand)
    col_prod = _resolver(df, col_prod_cand)
    col_fam = _resolver(df, col_fam_cand)
    col_valor = _resolver(df, col_valor_cand)
    col_cant = _resolver(df, col_cant_cand)
    col_estado = _resolver(df, col_estado_cand)
    if not (col_fecha and col_cod and col_prod and (col_valor or col_cant)):
        return None

    d = df.copy()
    if col_estado and estados_excluir:
        excl = {e.upper() for e in estados_excluir}
        # .fillna ANTES de .astype(str): las columnas que trae DuckDB usan un
        # dtype "str" con NA propio (Arrow-backed) donde .astype(str) NO
        # convierte el nulo a texto — deja un float NaN suelto adentro de una
        # Series "de texto" (mismo tipo de trampa que ya documenta
        # `_activo()` en recetas_comun.py). Sin el fillna, un `sorted()` más
        # abajo sobre esos valores revienta comparando float con str.
        d = d[~d[col_estado].fillna("").astype(str).str.upper().isin(excl)]
    d["_fecha"] = pd.to_datetime(d[col_fecha], errors="coerce")
    d["_cod"] = d[col_cod].fillna("").astype(str).str.strip()
    d["_prod"] = d[col_prod].fillna("").astype(str)
    d["_fam"] = d[col_fam].fillna("Sin familia").astype(str) if col_fam else "Sin familia"
    d["_valor"] = pd.to_numeric(d[col_valor], errors="coerce").fillna(0) if col_valor else 0.0
    d["_cant"] = pd.to_numeric(d[col_cant], errors="coerce").fillna(0) if col_cant else 0.0
    return d.dropna(subset=["_fecha"])


def _comparativo_pedido_baja(*, key_prefix):
    """Vista compartida por Requerimientos y Salidas: cuánto se requirió
    (entrada al área) contra cuánto se dio de baja (salida de esa área)
    después, por producto/familia/período — ver límites del dato en el
    docstring del módulo.

    Trae SUS PROPIOS controles (fecha/familia/granularidad/métrica) en vez
    de heredar el rango o los chips del dashboard "anfitrión": los dos
    lados tienen que quedar filtrados exactamente igual para que el
    comparativo sea válido, y `df_f` del anfitrión solo trae SU parquet ya
    filtrado por SU fecha (mismo criterio que
    `recetas_comun._panorama_compras`, que también trae su propio
    `date_input` en vez de heredar el de la franja)."""
    req = _cargar_lado(
        "requerimientos.parquet",
        col_fecha_cand=["Fecha Registro", "FECHA REGISTRO"],
        col_cod_cand=["Codigo Producto", "CODIGO PRODUCTO"],
        col_prod_cand=["Nombre Producto", "NOMBRE PRODUCTO"],
        col_fam_cand=["Nombre Familia", "NOMBRE FAMILIA"],
        col_valor_cand=["Valor Item", "VALOR ITEM"],
        col_cant_cand=["Cantidad", "CANTIDAD"],
        col_estado_cand=["Nombre Estado Requerimiento", "NOMBRE ESTADO REQUERIMIENTO"],
        estados_excluir=("ANULADO",),
    )
    sal = _cargar_lado(
        "salidas.parquet",
        col_fecha_cand=["Fecha registro", "FECHA REGISTRO"],
        col_cod_cand=["Cod Producto", "COD PRODUCTO", "Codigo Producto"],
        col_prod_cand=["Nombre Producto", "NOMBRE PRODUCTO"],
        col_fam_cand=["Nombre Familia", "NOMBRE FAMILIA"],
        col_valor_cand=["Valor Neto", "VALOR NETO"],
        col_cant_cand=["Cant Salida", "CANT SALIDA"],
        col_estado_cand=["Nombre Estado Salida", "NOMBRE ESTADO SALIDA"],
        estados_excluir=("ANULADO",),
    )
    if req is None or sal is None:
        st.info(
            "No se pudo armar el comparativo: falta requerimientos.parquet "
            "o salidas.parquet, o no traen las columnas esperadas."
        )
        return

    c1, c2, c3 = st.columns([2, 2, 1.3])
    with c1:
        rango = st.date_input(
            "Rango (vacío = todo el histórico)", value=(),
            format="DD/MM/YYYY", key=f"{key_prefix}_rango",
        )
    fams = sorted(set(req["_fam"].unique()) | set(sal["_fam"].unique()))
    with c2:
        fam_sel = st.multiselect("Familia", fams, key=f"{key_prefix}_fam")
    with c3:
        metrica = st.radio("Medir por", ["Valor (S/)", "Cantidad"],
                           key=f"{key_prefix}_metrica")
    es_valor = (metrica == "Valor (S/)")
    campo = "_valor" if es_valor else "_cant"
    pref = "S/ " if es_valor else ""

    if len(rango) >= 1:
        req = req[req["_fecha"] >= pd.Timestamp(rango[0])]
        sal = sal[sal["_fecha"] >= pd.Timestamp(rango[0])]
    if len(rango) >= 2:
        req = req[req["_fecha"] <= pd.Timestamp(rango[1])]
        sal = sal[sal["_fecha"] <= pd.Timestamp(rango[1])]
    if fam_sel:
        req = req[req["_fam"].isin(fam_sel)]
        sal = sal[sal["_fam"].isin(fam_sel)]

    if req.empty and sal.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # ── KPIs ────────────────────────────────────────────────────────────
    total_req = float(req[campo].sum())
    total_sal = float(sal[campo].sum())
    pct = f"{total_sal / total_req * 100:.1f}%" if total_req else "—"
    k1, k2, k3 = st.columns(3)
    k1.metric("📥 Requerido", f"{pref}{total_req:,.0f}")
    k2.metric("📤 Dado de baja", f"{pref}{total_sal:,.0f}")
    k3.metric("Baja / Requerido", pct, delta_color="off")
    st.caption(
        "Agregado por producto/familia/período — no hay una llave que una "
        "un Requerimiento puntual con la Salida que lo originó."
    )

    # ── Evolución comparada ─────────────────────────────────────────────
    cg1, _sp = st.columns([1.4, 3.6])
    with cg1:
        gran = st.pills(
            "Agrupar por", ["Día", "Semana", "Mes", "Año"], default="Mes",
            key=f"{key_prefix}_gran", label_visibility="collapsed",
        ) or "Mes"

    g_req = (pd.DataFrame({"per": _periodo_serie(req["_fecha"], gran), "v": req[campo]})
             .groupby("per")["v"].sum())
    g_sal = (pd.DataFrame({"per": _periodo_serie(sal["_fecha"], gran), "v": sal[campo]})
             .groupby("per")["v"].sum())
    todos_per = sorted(set(g_req.index) | set(g_sal.index))
    g_req = g_req.reindex(todos_per, fill_value=0)
    g_sal = g_sal.reindex(todos_per, fill_value=0)

    with st.container(border=True, key="mov_cmp_card_evolucion"):
        fig = go.Figure([
            go.Bar(name="Requerido", x=todos_per, y=g_req.values, marker_color=ACENTO),
            go.Bar(name="Dado de baja", x=todos_per, y=g_sal.values,
                  marker_color=GRIS_TEXTO_SUAVE),
        ])
        _compras_layout(fig, alto=440)
        fig.update_layout(
            title=f"Requerido vs dado de baja ({gran.lower()})",
            barmode="group", xaxis_title=None, yaxis_title=None,
            legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=10)),
        )
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_evolucion")

    # ── Ranking por producto: mayor diferencia (requerido − baja) ───────
    g_req_p = req.groupby(["_cod", "_prod"])[campo].sum()
    g_sal_p = sal.groupby(["_cod", "_prod"])[campo].sum()
    idx = g_req_p.index.union(g_sal_p.index)
    tabla = pd.DataFrame({
        "requerido": g_req_p.reindex(idx, fill_value=0),
        "baja": g_sal_p.reindex(idx, fill_value=0),
    }).reset_index()
    tabla["dif"] = tabla["requerido"] - tabla["baja"]
    top = tabla.reindex(tabla["dif"].abs().sort_values(ascending=False).index).head(15)
    top = top.sort_values("dif")

    if not top.empty:
        colores = [AJUSTE_POS if v >= 0 else AJUSTE_NEG for v in top["dif"]]
        with st.container(border=True, key="mov_cmp_card_ranking"):
            fig2 = go.Figure(go.Bar(
                x=top["dif"], y=[_compras_truncar(p, 34) for p in top["_prod"]],
                orientation="h", marker_color=colores,
                text=[f"{pref}{v:,.0f}" for v in top["dif"]],
                textposition="outside", cliponaxis=False,
            ))
            _compras_layout(fig2, alto=min(560, max(320, len(top) * 30 + 120)))
            fig2.update_layout(
                title="Mayor diferencia entre lo requerido y lo dado de baja",
                xaxis_title=None, yaxis_title=None, showlegend=False,
            )
            fig2.update_xaxes(visible=False)
            st.plotly_chart(fig2, use_container_width=True, key=f"{key_prefix}_ranking")
            st.caption(
                "🟢 Se requirió más de lo que se dio de baja en el período. "
                "🔴 Se dio de baja más de lo requerido."
            )
