"""graficos.compras.producto - drill de Producto.

Ranking de TODOS los productos comprados (valor, cantidad, UM, precio real
de inicio/fin de periodo y su variación) con el mismo patrón de tabla-
ranking + clic-para-enfocar que graficos/compras/proveedor.py. El producto
en foco muestra su evolución (Precio / Cantidad / Valor, con granularidad
Semana / Mes / Año) fusionando el promedio del período con el precio real
de cada compra en un solo gráfico.

Reemplaza a los antiguos drills "Precio top 10", "Precio por compra" y
"Cantidad por producto" (graficos/compras/cantidad.py, eliminado 2026-08-17):
las tres separaban precio-promedio, precio-real y cantidad/valor de UN mismo
producto en tres pantallas distintas — acá conviven en una, con un selector
de texto plano en vez de tabs/pills con caja (a pedido, para no ocupar sitio).

Debajo, un segundo ranking agrupa las mismas compras por Familia; un clic
abre el mini ranking de productos de esa familia (reusa `_compras_mini_barras`).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, ERROR, EXITO, GRIS_TEXTO
from graficos.base import _compras_layout, _compras_truncar
from graficos.compras._comun import _compras_mini_barras
from graficos import alturas

_ALTO_FILA = 28
"""Filas "algo delgadas" a pedido (2026-08-24) para los dos rankings de este
drill — más finas que el default de `st.dataframe` (~35px, el mismo número
que usa el `rowHeight` de AgGrid en Proveedor/Inventario). Con `row_height=`
explícito, `_ALTO_FRAME` tiene que usar el mismo número: si no, el frame se
calcula para filas de 35px y filas reales de 28px dejan aire de sobra
abajo (o de más, si `_ALTO_FRAME` quedara más chico que 8 filas reales)."""

_ALTO_FRAME = alturas.por_filas(8, px_fila=_ALTO_FILA, extra=45, minimo=0)

# Eje X por granularidad: forzado a propósito. Con pocos puntos (rango de
# fecha corto, o un producto con 1-2 compras) Plotly no tiene de dónde sacar
# un paso de tick razonable y cae en sub-segundos ("23:59:59.9995 Jul 31,
# 2026") — visto en vivo con un solo bucket de Mes. `dtick` fija el paso al
# calendario real (mes/año) y `tickformat` la etiqueta, sin importar cuántos
# puntos haya.
_EJE_X_GRAN = {
    "Semana": dict(dtick=7 * 24 * 60 * 60 * 1000, tickformat="%d %b"),
    "Mes": dict(dtick="M1", tickformat="%b %Y"),
    "Año": dict(dtick="M12", tickformat="%Y"),
}


def _eje_x_kwargs(gran, agg):
    """`_EJE_X_GRAN[gran]`, con `tick0` anclado al primer bucket real de
    ESTE gráfico para "Semana". "M1"/"M12" (Mes/Año) se alinean solos al
    calendario sin importar `tick0`, pero un paso semanal en milisegundos
    no: sin un `tick0` que caiga sobre un bucket real, con pocos datos
    Plotly puede no dibujar NINGÚN tick semanal (rango angosto, ninguna
    posición de la grilla cae dentro) — visto en vivo con una sola semana
    de compras."""
    kw = dict(_EJE_X_GRAN[gran])
    if gran == "Semana" and not agg.empty:
        kw["tick0"] = agg.index.min()
    return kw


# Selector de texto plano (Semana/Mes/Año, Precio/Cantidad/Valor): mismo
# st.pills que el resto de la app (radiogroup accesible, estado en
# session_state), pero sin la cápsula — a pedido, para que no ocupe sitio
# dentro de la columna angosta del panel de detalle. El DOM de st.pills es
# fijo (ver estilos/__init__.py § Sobre st.pills): stButtonGroup > button
# [role="radio"], con `data-selected` SOLO en el activo.
_CSS_SELECTOR_TEXTO = f"""
<style>
.st-key-compras_prod_gran [data-testid="stButtonGroup"],
.st-key-compras_prod_modo [data-testid="stButtonGroup"] {{
    gap: 10px !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"],
.st-key-compras_prod_modo [data-testid="stButtonGroup"] button[role="radio"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1px 0 !important;
    min-height: 0 !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"][data-selected],
.st-key-compras_prod_modo [data-testid="stButtonGroup"] button[role="radio"][data-selected] {{
    color: {ACENTO} !important;
    font-weight: 600 !important;
}}
/* Título sobre cada tabla-ranking: mismo lenguaje visual que
   `.cp-rank-tit` de graficos/compras/_css_proveedor.py, pero declarado acá
   — ese CSS solo se inyecta cuando se renderiza el drill de Proveedor, así
   que reusar la clase sin redeclararla dejaría el título sin estilo en
   Producto. Nombre propio a propósito (evita cualquier acople). */
.cp-prod-rank-tit {{
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    padding-left: 2px;
    margin: 0 0 4px;
}}
</style>
"""


# ── Funciones puras ───────────────────────────────────────────────────────

def _prod_ranking(dd, col_prod, col_fecha, col_valor, col_cant, col_punit, col_um):
    """Un producto por fila: valor y cantidad totales del rango, UM (moda),
    y precio real de la primera y última compra del período (sin promediar
    — mismo criterio que "Por compra") con su % de variación. Ordenado por
    valor descendente."""
    filas = []
    for prod, g in dd.groupby(col_prod):
        valor = float(g[col_valor].sum())
        cantidad = float(g[col_cant].sum()) if col_cant else 0.0
        um = ""
        if col_um and col_um in g.columns:
            _u = g[col_um].dropna()
            if not _u.empty:
                um = str(_u.mode().iat[0])
        gp = g.dropna(subset=[col_punit])
        gp = gp[gp[col_punit] > 0].sort_values(col_fecha)
        if gp.empty:
            inicio = fin = var_pct = None
        else:
            inicio = float(gp[col_punit].iloc[0])
            fin = float(gp[col_punit].iloc[-1])
            var_pct = ((fin - inicio) / inicio * 100) if inicio else None
        filas.append({"producto": str(prod), "valor": valor, "cantidad": cantidad,
                      "um": um, "inicio": inicio, "fin": fin, "var_pct": var_pct})
    out = pd.DataFrame(filas).sort_values("valor", ascending=False).reset_index(drop=True)
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


def _prod_serie_periodo(g, col_fecha, col_punit, col_cant, col_valor, gran):
    """Serie por período (Semana/Mes/Año) de UN producto ya filtrado: precio
    promedio (relleno hacia adelante y hacia atrás en los huecos, para que
    la línea no corte), cantidad total y valor total. Indexada por la fecha
    de INICIO del período (eje real, no etiquetas de texto), así el
    promedio y las compras reales conviven en el mismo eje sin importar la
    granularidad elegida."""
    fe = pd.to_datetime(g[col_fecha], errors="coerce")
    if gran == "Semana":
        bucket = (fe - pd.to_timedelta(fe.dt.weekday, unit="D")).dt.normalize()
    elif gran == "Año":
        bucket = pd.to_datetime(fe.dt.year.astype("Int64").astype(str) + "-01-01",
                                errors="coerce")
    else:  # Mes
        bucket = fe.dt.to_period("M").dt.to_timestamp()
    base = pd.DataFrame({
        "bucket": bucket,
        "precio": pd.to_numeric(g[col_punit], errors="coerce"),
        "cantidad": (pd.to_numeric(g[col_cant], errors="coerce").fillna(0)
                     if col_cant else 0.0),
        "valor": pd.to_numeric(g[col_valor], errors="coerce").fillna(0),
    }).dropna(subset=["bucket"])
    if base.empty:
        return base.set_index("bucket")
    agg = base.groupby("bucket").agg(precio=("precio", "mean"),
                                     cantidad=("cantidad", "sum"),
                                     valor=("valor", "sum")).sort_index()
    agg["precio"] = agg["precio"].ffill().bfill()
    return agg


def _fam_normalizada(dd, col_fam):
    """Columna de familia como texto, con vacíos/NaN unificados en "Sin
    familia" — no se descartan, o el total de este ranking dejaría de
    cuadrar con el de productos."""
    return dd[col_fam].astype(str).replace({"": "Sin familia", "nan": "Sin familia"})


def _fam_ranking(dd, col_fam, col_prod, col_valor):
    """Una familia por fila: valor total y Nº de productos distintos."""
    g = dd.copy()
    g[col_fam] = _fam_normalizada(g, col_fam)
    out = g.groupby(col_fam).agg(valor=(col_valor, "sum"),
                                 productos=(col_prod, "nunique"))
    out = out.sort_values("valor", ascending=False).reset_index()
    out = out.rename(columns={col_fam: "familia"})
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


# ── Vista principal ──────────────────────────────────────────────────────

@st.fragment
def _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant, col_punit,
                            col_um, col_fecha, col_prov=None):
    """Ranking de productos → evolución del producto en foco (Precio /
    Cantidad / Valor). Debajo, ranking por Familia → mini ranking de sus
    productos."""
    if not (col_prod and col_valor and col_punit and col_fecha):
        st.info("Faltan columnas (Producto, Valor, Precio unitario o Fecha) "
                "para este gráfico.")
        return

    dd = d.copy()
    dd[col_fecha] = pd.to_datetime(dd[col_fecha], errors="coerce")
    dd[col_punit] = pd.to_numeric(dd[col_punit], errors="coerce")
    dd[col_valor] = pd.to_numeric(dd[col_valor], errors="coerce").fillna(0)
    dd = dd.dropna(subset=[col_fecha, col_prod])
    dd = dd[dd[col_prod].astype(str).str.strip() != ""]
    if dd.empty:
        st.info("Sin datos en el rango seleccionado.")
        return

    st.markdown(_CSS_SELECTOR_TEXTO, unsafe_allow_html=True)

    ranking = _prod_ranking(dd, col_prod, col_fecha, col_valor, col_cant,
                            col_punit, col_um)
    if ranking.empty:
        st.info("Sin productos con precio válido en el rango.")
        return

    # ── Card 1: ranking de productos + evolución del producto en foco ────
    with st.container(border=True, key="compras_prod_card_ranking"):
        prod_focus = st.session_state.get("compras_prod_focus")
        if prod_focus not in set(ranking["producto"]):
            prod_focus = None

        # Procesar clic ANTES de construir la tabla (mismo patrón que
        # Proveedor): así el rerun que cambia el foco sale correcto a la
        # primera, sin un segundo rerun para "alcanzarlo".
        _rank_tab_key = "compras_prod_rank_tab"
        _rows_sel = ((st.session_state.get(_rank_tab_key) or {})
                     .get("selection", {}).get("rows", []))
        if _rows_sel:
            _ri = _rows_sel[0]
            if 0 <= _ri < len(ranking):
                _clicked = ranking.iloc[_ri]["producto"]
                if st.session_state.get("compras_prod_last_click") != _clicked:
                    st.session_state["compras_prod_last_click"] = _clicked
                    prod_focus = None if _clicked == prod_focus else _clicked
                    st.session_state["compras_prod_focus"] = prod_focus
        elif st.session_state.get("compras_prod_last_click") is not None:
            # Sin el botón "✕ Quitar foco" (regla #133, mismo fix que ya
            # tiene Proveedor), destildar la fila enfocada es la ÚNICA
            # salida: reclickearla no dispara `on_select` (el valor del
            # widget no cambia), pero destildar sí — `rows: [i]` → `[]`.
            st.session_state["compras_prod_last_click"] = None
            prod_focus = None
            st.session_state["compras_prod_focus"] = None

        col_tabla, col_detalle = st.columns([1.6, 1], gap="small")
        with col_tabla:
            st.markdown('<div class="cp-prod-rank-tit">Ranking de productos</div>',
                       unsafe_allow_html=True)

            disp = ranking.rename(columns={
                "producto": "Producto", "valor": "Valor", "pct": "%",
                "cantidad": "Cant.", "um": "UM", "inicio": "Inicio",
                "fin": "Fin", "var_pct": "Var",
            })
            st.dataframe(
                disp[["Producto", "Valor", "%", "Cant.", "UM", "Inicio", "Fin", "Var"]],
                hide_index=True, width="stretch", height=_ALTO_FRAME,
                row_height=_ALTO_FILA,
                on_select="rerun", selection_mode="single-row", key=_rank_tab_key,
                column_config={
                    "Producto": st.column_config.TextColumn("Producto", width="medium"),
                    "Valor": st.column_config.ProgressColumn(
                        "Valor", format="S/ %.0f", min_value=0,
                        max_value=float(ranking["valor"].max())),
                    "%": st.column_config.NumberColumn("%", format="%.0f%%", width="small"),
                    "Cant.": st.column_config.NumberColumn("Cant.", format="%.0f", width="small"),
                    "UM": st.column_config.TextColumn("UM", width="small"),
                    "Inicio": st.column_config.NumberColumn("Inicio", format="S/ %.2f"),
                    "Fin": st.column_config.NumberColumn("Fin", format="S/ %.2f"),
                    "Var": st.column_config.NumberColumn("Var", format="%+.1f%%"),
                },
            )
            st.caption("UM = unidad de kardex · Inicio/Fin = primera y última "
                      "compra real del período · % es sobre el total del rango.")

        with col_detalle:
            prod_foco = prod_focus if prod_focus is not None else ranking.iloc[0]["producto"]
            g = dd[dd[col_prod].astype(str) == prod_foco]
            fila = ranking[ranking["producto"] == prod_foco].iloc[0]

            st.markdown(f'<div style="font-size:13.5px;font-weight:700;">'
                       f'{_compras_truncar(prod_foco, 40)}</div>',
                       unsafe_allow_html=True)

            with st.container(key="compras_prod_gran"):
                gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"], default="Mes",
                                key="compras_prod_gran_pills",
                                label_visibility="collapsed") or "Mes"
            with st.container(key="compras_prod_modo"):
                modo = st.pills("Ver", ["Precio", "Cantidad", "Valor"], default="Precio",
                                key="compras_prod_modo_pills",
                                label_visibility="collapsed") or "Precio"

            agg = _prod_serie_periodo(g, col_fecha, col_punit, col_cant, col_valor, gran)
            fig = go.Figure()
            gw = gran.lower()

            if modo == "Precio":
                if agg.empty or fila["inicio"] is None:
                    st.info("Sin compras con precio válido para este producto.")
                else:
                    fig.add_scatter(
                        x=agg.index, y=agg["precio"], mode="lines+markers",
                        name=f"Promedio {gw}", line=dict(color=ACENTO, width=2.4),
                        marker=dict(size=6),
                        hovertemplate="%{x|%d/%m/%Y}: S/ %{y:,.2f}<extra>Promedio</extra>",
                    )
                    _real = g.dropna(subset=[col_punit])
                    _real = _real[_real[col_punit] > 0].sort_values(col_fecha)
                    _cd = (_real[col_prov].astype(str).values
                           if col_prov and col_prov in _real.columns else None)
                    fig.add_scatter(
                        x=_real[col_fecha], y=_real[col_punit], mode="markers",
                        name="Compra real",
                        marker=dict(size=7, color="white",
                                   line=dict(color=ACENTO, width=1.5)),
                        customdata=_cd,
                        hovertemplate=(
                            "%{x|%d/%m/%Y}: S/ %{y:,.2f}"
                            + ("<br>%{customdata}" if _cd is not None else "")
                            + "<extra>Compra</extra>"),
                    )
                    var_pct = fila["var_pct"]
                    color_var = (ERROR if var_pct and var_pct > 0.05
                                else (EXITO if var_pct and var_pct < -0.05 else GRIS_TEXTO))
                    _um = f"/{fila['um']}" if fila["um"] else ""
                    st.markdown(
                        f'<div style="font-size:12px;color:{GRIS_TEXTO};margin:2px 0 6px;">'
                        f'actual <b>S/ {fila["fin"]:,.2f}{_um}</b> · '
                        f'<b style="color:{color_var};">'
                        f'{"+" if (var_pct or 0) >= 0 else "−"}{abs(var_pct or 0):.1f}%'
                        f'</b> en el período</div>', unsafe_allow_html=True)
                    _compras_layout(fig, alto=alturas.MINI)
                    fig.update_layout(legend=dict(orientation="h", y=-0.25, x=0,
                                                  font=dict(size=10)))
                    fig.update_xaxes(**_eje_x_kwargs(gran, agg))
                    st.plotly_chart(fig, use_container_width=True,
                                    key=f"compras_g_prod_precio_{gran}")
                    st.caption(f"Línea = promedio {gw} · puntos = precio real de cada compra.")
            else:
                col_serie = "cantidad" if modo == "Cantidad" else "valor"
                total = float(fila["cantidad"] if modo == "Cantidad" else fila["valor"])
                if agg.empty:
                    st.info("Sin compras para este producto en el rango.")
                else:
                    _pref = "" if modo == "Cantidad" else "S/ "
                    _tpl = "%{y:,.0f}" if modo == "Cantidad" else "S/ %{y:,.2f}"
                    fig.add_bar(x=agg.index, y=agg[col_serie], marker_color=ACENTO,
                               hovertemplate="%{x|%d/%m/%Y}<br>" + _tpl + "<extra></extra>")
                    _um = f" {fila['um']}" if (modo == "Cantidad" and fila["um"]) else ""
                    _prom = total / len(agg) if len(agg) else 0.0
                    st.markdown(
                        f'<div style="font-size:12px;color:{GRIS_TEXTO};margin:2px 0 6px;">'
                        f'total <b>{_pref}{total:,.0f}{_um}</b> · '
                        f'promedio <b>{_pref}{_prom:,.0f}{_um}/{gw}</b></div>',
                        unsafe_allow_html=True)
                    _compras_layout(fig, alto=alturas.MINI)
                    fig.update_layout(showlegend=False,
                                      yaxis=dict(tickprefix=_pref, tickformat=",.0f"))
                    fig.update_xaxes(**_eje_x_kwargs(gran, agg))
                    st.plotly_chart(fig, use_container_width=True,
                                    key=f"compras_g_prod_{modo}_{gran}")
                    _etq = "cantidad comprada" if modo == "Cantidad" else "valor comprado"
                    st.caption(f"Barras = {_etq} por {gw}.")

    # ── Card 2: ranking por familia + mini ranking de sus productos ──────
    if not col_fam or col_fam not in dd.columns:
        return

    with st.container(border=True, key="compras_prod_card_familia"):
        fam_ranking = _fam_ranking(dd, col_fam, col_prod, col_valor)
        fam_focus = st.session_state.get("compras_prod_fam_focus")
        if fam_focus not in set(fam_ranking["familia"]):
            fam_focus = None

        _fam_tab_key = "compras_prod_fam_rank_tab"
        _fam_rows_sel = ((st.session_state.get(_fam_tab_key) or {})
                         .get("selection", {}).get("rows", []))
        if _fam_rows_sel:
            _ri = _fam_rows_sel[0]
            if 0 <= _ri < len(fam_ranking):
                _clicked = fam_ranking.iloc[_ri]["familia"]
                if st.session_state.get("compras_prod_fam_last_click") != _clicked:
                    st.session_state["compras_prod_fam_last_click"] = _clicked
                    fam_focus = None if _clicked == fam_focus else _clicked
                    st.session_state["compras_prod_fam_focus"] = fam_focus
        elif st.session_state.get("compras_prod_fam_last_click") is not None:
            # Mismo fix que el ranking de arriba (regla #133): sin botón,
            # destildar la fila es la única forma de limpiar el foco.
            st.session_state["compras_prod_fam_last_click"] = None
            fam_focus = None
            st.session_state["compras_prod_fam_focus"] = None

        col_famtabla, col_famdet = st.columns([1.6, 1], gap="small")
        with col_famtabla:
            st.markdown('<div class="cp-prod-rank-tit">Compras por familia</div>',
                       unsafe_allow_html=True)

            disp_fam = fam_ranking.rename(columns={
                "familia": "Familia", "valor": "Valor", "pct": "%",
                "productos": "Productos",
            })
            st.dataframe(
                disp_fam[["Familia", "Valor", "%", "Productos"]],
                hide_index=True, width="stretch", height=_ALTO_FRAME,
                row_height=_ALTO_FILA,
                on_select="rerun", selection_mode="single-row", key=_fam_tab_key,
                column_config={
                    "Familia": st.column_config.TextColumn("Familia", width="medium"),
                    "Valor": st.column_config.ProgressColumn(
                        "Valor", format="S/ %.0f", min_value=0,
                        max_value=float(fam_ranking["valor"].max())),
                    "%": st.column_config.NumberColumn("%", format="%.0f%%", width="small"),
                    "Productos": st.column_config.NumberColumn(
                        "Productos", format="%.0f", width="small"),
                },
            )
            st.caption("% sobre el total comprado en el rango.")

        with col_famdet:
            fam_foco = fam_focus if fam_focus is not None else fam_ranking.iloc[0]["familia"]
            st.markdown(f'<div style="font-size:13.5px;font-weight:700;margin-bottom:8px;">'
                       f'{_compras_truncar(fam_foco, 40)}</div>', unsafe_allow_html=True)
            serie_fam = (dd[_fam_normalizada(dd, col_fam) == fam_foco]
                        .groupby(col_prod)[col_valor].sum().nlargest(10))
            _compras_mini_barras(serie_fam, f"prod_fam_{fam_foco}")
