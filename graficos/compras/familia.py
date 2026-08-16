"""graficos.compras.familia - drill de Familia.

Familia -> Subfamilia -> productos, con barras en el tiempo arriba y
paneles de composicion y top N abajo. El clic navega de nivel.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, GRIS_BORDE, SERIE_PRINCIPAL
from graficos.base import (
    PALETA_CALLAI, _card, _compras_layout, _compras_truncar,
    franja_linea_inferior, titulo_en_franja,
)
from graficos.compras._comun import (_first_point, _periodo_serie)
from graficos import alturas


@st.fragment
def _compras_familia_drill(d, col_fam, col_subfam, col_prod, col_valor,
                           col_cant, col_fecha):
    """Dashboard de Familia con drill-down (reemplaza la barra simple).

    - Granularidad Semana/Mes/Año, vista Apilado/Agrupado, medida Valor/Cantidad.
    - Drill: Familia (selectbox) → sus Subfamilias en el tiempo; Subfamilia
      (selectbox) refina el Top N de productos.
    - Paneles: composición (Familias o Subfamilias) + Top N productos.
    Series apiladas se limitan a Top 6 + «Otros» para no saturar.
    """
    if not (col_fam and col_fecha and col_valor):
        st.info("Faltan columnas (Familia, Fecha, Valor) para este gráfico.")
        return

    # ── Estado de drill (por clic en las barras) ─────────────────────────
    fams_all = sorted(d[col_fam].dropna().astype(str).unique().tolist())
    focus_fam = st.session_state.get("compras_fam_focus")
    focus_sub = st.session_state.get("compras_fam_subfocus")
    if focus_fam not in fams_all:
        focus_fam, focus_sub = None, None

    # Desglose: se lee de session_state ANTES de dibujar su pill (que vive
    # más abajo, en la fila de navegación) para poder resolver qué serie
    # corresponde — familia o subfamilia — y armar el selector de series
    # ya en la fila de controles de arriba, junto a la granularidad. Mismo
    # patrón "leer del estado, dibujar el widget después" que usa el rail
    # flotante del drill de Proveedor.
    _es_subfam = bool(
        focus_fam is not None and col_subfam
        and st.session_state.get("compras_fam_desglose", "Total familia")
        == "Por subfamilia")
    serie_col = "sub" if _es_subfam else "fam"
    titulo_ser = "subfamilia" if _es_subfam else "familia"

    _dsub = d if focus_fam is None else d[d[col_fam].astype(str) == focus_fam]
    _dsub = _dsub[pd.to_datetime(_dsub[col_fecha], errors="coerce").notna()]
    _col_serie_raw = col_subfam if _es_subfam else col_fam
    _valor_ser = pd.to_numeric(_dsub[col_valor], errors="coerce").fillna(0)
    tot_ser = (_valor_ser.groupby(_dsub[_col_serie_raw].astype(str)).sum()
               .sort_values(ascending=False))
    _ser_all = tot_ser.index.tolist()
    _top6_default = tot_ser.head(6).index.tolist()
    for _s in _ser_all:
        _k = f"compras_fam_ser_cb::{titulo_ser}::{_s}"
        if _k not in st.session_state:
            st.session_state[_k] = (_s in _top6_default)
    top_ser = [s for s in _ser_all
               if st.session_state.get(f"compras_fam_ser_cb::{titulo_ser}::{s}")] \
              or _top6_default

    # ── Título en la FRANJA superior (fuera de la tarjeta) → controles →
    # línea → gráfico ── Mismo patrón que Ventas › Comparativo
    # (arquitectura.md regla #120): el título vive en un contenedor propio,
    # `compras_fam_titulo_franja`, anclado por CSS a la franja superior; la
    # fecha y los chips Familia/Subfamilia se corren a la derecha para
    # hacerle sitio (estilos/_50_fecha.py, scope `:has()` sobre esta misma
    # key — solo en la dimensión Familia de Compras, no en el resto de
    # vistas del reporte).
    #
    # El título necesita `gran`, que se elige DENTRO de la fila de
    # controles (en c1, más abajo) — circularidad resuelta con la técnica de
    # la regla #108: cabecera PROVISIONAL con el `gran` de session_state
    # (acierta casi siempre) antes de dibujar los pills, y reescritura con
    # el valor real después de leerlos. Sin esto, la cabecera queda vacía
    # durante la carga y todo lo de abajo salta ~40px en cada clic.
    def _titulo_familia(_gran):
        return (f"Valor de compra por {_gran.lower()} y {titulo_ser}"
                + ("" if focus_fam is None
                   else f" — {_compras_truncar(focus_fam, 32)}"))

    _ph_hdr = st.container(key="compras_fam_titulo_franja").empty()
    titulo_en_franja(_ph_hdr, _titulo_familia(
        st.session_state.get("compras_fam_gran") or "Mes"))

    # Medida fija en Valor S/: se quitó el toggle Valor/Cantidad (la
    # cantidad sigue viva igual en los paneles, junto al valor). El
    # selector de series comparte fila con la granularidad — antes vivía
    # solo, en un botón grande una fila más abajo.
    #
    # `compras_fam_controles_row` es solo un ancla de CSS (sin border): el
    # título de arriba colapsa a 0px de alto (position:fixed) pero su
    # wrapper de Streamlit sigue contando para el gap:16px del flex que lo
    # contiene, así que esta fila aparecía 16px más abajo de lo que estaba
    # antes de que el título tuviera un hermano invisible. Se cancela con
    # margin-top:-16px en estilos/_80_cards.py — mismo hallazgo que en
    # Ventas › Comparativo (arquitectura.md regla #120, addendum).
    with st.container(key="compras_fam_controles_row"):
        c1, c2, c3, c4 = st.columns([1.3, 1.2, 0.9, 1.3])
        with c1:
            gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                            default="Mes", key="compras_fam_gran",
                            label_visibility="collapsed") or "Mes"
        with c2:
            vista = st.pills("Vista", ["Apilado", "Agrupado"],
                             default="Apilado", key="compras_fam_vista",
                             label_visibility="collapsed") or "Apilado"
        with c3:
            topn = st.pills("Top", [5, 10, 20], default=10,
                            key="compras_fam_topn",
                            label_visibility="collapsed") or 10
        with c4:
            # estilos/_30_filtros.py pone [data-testid="stPopover"] button
            # GRANDE sin scope (pensado para el popover de filtros de la
            # franja): acá se sobreescribe con más especificidad para que
            # este quede al tamaño de los pills vecinos, no del popover de
            # filtros.
            with st.container(key="compras_fam_ser_pop"):
                st.markdown(
                    """<style>
                    .st-key-compras_fam_ser_pop [data-testid="stPopover"] button {
                        min-width: 0 !important;
                        padding: 4px 12px !important;
                        font-size: 13px !important;
                        font-weight: 500 !important;
                        border-radius: 999px !important;
                    }
                    </style>""",
                    unsafe_allow_html=True,
                )
                with st.popover(f"{titulo_ser.capitalize()}s ({len(top_ser)})"):
                    st.caption(f"Elegí qué {titulo_ser}s mostrar en el gráfico.")
                    for _s in _ser_all:
                        st.checkbox(_compras_truncar(_s, 30),
                                   key=f"compras_fam_ser_cb::{titulo_ser}::{_s}")

    # Reescritura con el `gran` REAL, ya resuelto por el widget. Casi siempre
    # coincide con el provisional de arriba (mismo valor de session_state);
    # cuando difiere (primer render, o cambió el foco de familia), Streamlit
    # sólo toca el DOM si el texto cambió de verdad.
    titulo_en_franja(_ph_hdr, _titulo_familia(gran))
    franja_linea_inferior()

    es_valor = True
    fe = pd.to_datetime(d[col_fecha], errors="coerce")

    if gran == "Semana":
        # Rango real lunes-domingo de esa semana, no el número ISO
        # ("2026-S31" no se lee sin calendario a mano): "del 27 Jul - 02 Ago
        # 2026". per_sort ordena cronológicamente (fecha ISO del lunes);
        # per es la etiqueta que ve el usuario en el eje.
        _wstart = (fe - pd.to_timedelta(fe.dt.weekday, unit="D")).dt.normalize()
        _wend = _wstart + pd.Timedelta(days=6)
        per_sort = _wstart.dt.strftime("%Y-%m-%d")
        _mismo_anio = _wstart.dt.year == _wend.dt.year
        _ini = _wstart.dt.strftime("%d %b")
        _ini_con_anio = _wstart.dt.strftime("%d %b %Y")
        _fin = _wend.dt.strftime("%d %b %Y")
        per_disp = pd.Series(
            np.where(_mismo_anio, "del " + _ini + " - " + _fin,
                     "del " + _ini_con_anio + " - " + _fin),
            index=fe.index)
        for _en, _es in {"Jan": "Ene", "Apr": "Abr",
                         "Aug": "Ago", "Dec": "Dic"}.items():
            per_disp = per_disp.str.replace(_en, _es)
    else:
        per_disp = _periodo_serie(fe, gran)
        per_sort = per_disp

    valor_s = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    cant_s = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
              if col_cant else pd.Series(0.0, index=d.index))
    base = pd.DataFrame({
        "per": per_disp.values,
        "per_sort": per_sort.values,
        "fam": d[col_fam].astype(str).values,
        "sub": (d[col_subfam].astype(str).values if col_subfam else "—"),
        "prod": (d[col_prod].astype(str).values if col_prod else "—"),
        "valor": valor_s.values,
        "cant": cant_s.values,
    })
    base["m"] = base["valor"] if es_valor else base["cant"]
    base = base[base["per"].notna() & (base["per"] != "<NA>")]
    if base.empty or base["m"].sum() == 0:
        st.info("Sin datos en el rango seleccionado.")
        return

    def _fmt(v):
        return f"S/ {v:,.0f}" if es_valor else f"{v:,.0f}"

    # ── Navegación (breadcrumb + desglose) ────────────────────────────────
    nav = st.columns([1.1, 1.5, 1.4])
    with nav[0]:
        if st.button("↩ Todas", key="cf_bc_all", use_container_width=True,
                     disabled=(focus_fam is None)):
            st.session_state["compras_fam_focus"] = None
            st.session_state["compras_fam_subfocus"] = None
            st.rerun()
    with nav[1]:
        if focus_fam is not None and st.button(
                f"↩ {_compras_truncar(focus_fam, 18)}", key="cf_bc_fam",
                use_container_width=True, disabled=(focus_sub is None)):
            st.session_state["compras_fam_subfocus"] = None
            st.rerun()
    with nav[2]:
        # Al elegir una familia NO se desglosa solo: el usuario decide si
        # expandir a subfamilias en el gráfico del tiempo. El valor ya se
        # leyó de session_state arriba (para armar serie_col/titulo_ser
        # antes de esta fila); acá solo se dibuja el widget.
        if focus_fam is not None and col_subfam:
            st.pills("Desglose", ["Total familia", "Por subfamilia"],
                     default="Total familia", key="compras_fam_desglose",
                     label_visibility="collapsed")

    # ── Barras en el tiempo (serie = familia o subfamilia) ──────────────
    tb = (base if focus_fam is None else base[base["fam"] == focus_fam]).copy()
    tb["serie"] = tb[serie_col].where(tb[serie_col].isin(top_ser), "Otros")
    g = tb.groupby(["per", "serie"], as_index=False)["m"].sum()
    # Orden cronológico por per_sort, no alfabético sobre la etiqueta que ve
    # el usuario (necesario desde que "per" dejó de ser un string ordenable
    # como "2026-S31" para pasar a una fecha legible "04 Ago 2026").
    periodos = (tb[["per_sort", "per"]].drop_duplicates()
                .sort_values("per_sort")["per"].tolist())
    periodos = list(dict.fromkeys(periodos))
    orden = top_ser + (["Otros"] if (tb["serie"] == "Otros").any() else [])

    _pref = "S/ " if es_valor else ""
    _tpl = ("S/ %{y:,.0f}" if es_valor else "%{y:,.0f}")
    fig = go.Figure()
    for i, s in enumerate(orden):
        ss = (g[g["serie"] == s].set_index("per")["m"]
              .reindex(periodos, fill_value=0))
        color = (GRIS_BORDE if s == "Otros"
                 else PALETA_CALLAI[i % len(PALETA_CALLAI)])
        fig.add_bar(x=periodos, y=ss.values, name=_compras_truncar(s, 22),
                    marker_color=color,
                    hovertemplate="%{fullData.name}<br>%{x}<br>"
                                  + _tpl + "<extra></extra>")
    _compras_layout(fig, alto=alturas.APOYO)
    # Sin `title=`: el título de este gráfico ya lo dibuja la cabecera de la
    # franja, arriba (regla #103 — un título dentro de la figura choca con la
    # leyenda cuando la hay; acá no la hay, `showlegend=False`, pero el título
    # vive en la franja por CONSISTENCIA con el resto de los dashboards, no
    # porque este caso puntual chocara).
    fig.update_layout(
        barmode="stack" if vista == "Apilado" else "group",
        yaxis=dict(tickprefix=_pref, tickformat=",.0f"),
        showlegend=False)
    fig.update_xaxes(type="category", tickangle=0)
    # Muchos periodos → rangeslider para deslizar horizontal + ventana inicial
    # (últimos ~12). El usuario arrastra el slider para ver periodos anteriores.
    if len(periodos) > 12:
        fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.07),
                         range=[len(periodos) - 12.5, len(periodos) - 0.5])

    # Clic en el gráfico:
    #  · en "Todas": clic en una familia → baja a esa familia (drill).
    #  · dentro de una familia: clic en una columna → filtra los paneles a ese
    #    periodo. `key` incluye el foco para limpiar la selección al navegar.
    _rst = st.session_state.get("compras_fam_time_rst", 0)
    _tkey = f"compras_g_fam_time_{focus_fam}_{focus_sub}_{gran}_{_rst}"
    _evt = st.plotly_chart(fig, use_container_width=True, key=_tkey,
                           on_select="rerun", selection_mode="points")
    _p = _first_point(_evt)
    periodo_sel = None
    if _p is not None:
        if focus_fam is None:
            _cn = _p.get("curve_number")
            if _cn is not None and 0 <= _cn < len(orden) and orden[_cn] != "Otros":
                st.session_state["compras_fam_focus"] = orden[_cn]
                st.session_state["compras_fam_subfocus"] = None
                st.session_state["compras_fam_time_rst"] = 0
                st.rerun()
        else:
            periodo_sel = _p.get("x")

    if periodo_sel is not None:
        cinfo, cbtn = st.columns([4, 1])
        cinfo.caption(f"📍 Paneles abajo filtrados al bloque **{periodo_sel}**. "
                      "Clic en otra columna para cambiar.")
        if cbtn.button("Ver todo el rango", key="compras_fam_verrango",
                       use_container_width=True):
            st.session_state["compras_fam_time_rst"] = _rst + 1
            st.rerun()
        base_b = base[base["per"] == periodo_sel]
    else:
        base_b = base

    # ── Panel composición (clic en una barra → baja de nivel) ───────────
    pc, pt = st.columns(2)
    with pc:
        if focus_fam is None:
            comp = base_b.groupby("fam")["m"].sum().sort_values()
            ctitulo = "Valorizado por Familia" if es_valor else "Cantidad por Familia"
        else:
            comp = (base_b[base_b["fam"] == focus_fam]
                    .groupby("sub")["m"].sum().sort_values())
            ctitulo = f"Subfamilias de {_compras_truncar(focus_fam, 26)}"
        comp_cats = list(comp.index)
        with _card("fam_comp", ctitulo, titulo_arriba=True):
            if comp.empty:
                st.info("Sin datos.")
            else:
                _cc = [SERIE_PRINCIPAL if (focus_sub and c == focus_sub) else ACENTO
                       for c in comp_cats]
                figc = go.Figure(go.Bar(
                    x=comp.values, y=[_compras_truncar(i, 26) for i in comp_cats],
                    orientation="h", marker_color=_cc,
                    text=[_fmt(v) for v in comp.values],
                    textposition="outside", cliponaxis=False,
                    hovertemplate="%{y}<br>" + _tpl.replace("y", "x") + "<extra></extra>"))
                _compras_layout(figc, alto=alturas.por_filas(
                    len(comp), px_fila=32, minimo=240, extra=80))
                figc.update_layout(xaxis=dict(tickprefix=_pref, tickformat=",.0f"),
                                   margin=dict(l=10, r=70, t=10, b=10))
                _ckey = f"compras_g_fam_comp_{focus_fam}_{focus_sub}_{_rst}"
                _cevt = st.plotly_chart(figc, use_container_width=True, key=_ckey,
                                        on_select="rerun", selection_mode="points")
                _cp = _first_point(_cevt)
                if _cp is not None:
                    _idx = _cp.get("point_number")
                    if _idx is None:
                        _idx = _cp.get("point_index")
                    if _idx is not None and 0 <= _idx < len(comp_cats):
                        _cat = comp_cats[_idx]
                        if focus_fam is None:
                            st.session_state["compras_fam_focus"] = _cat
                            st.session_state["compras_fam_subfocus"] = None
                            st.rerun()
                        else:
                            st.session_state["compras_fam_subfocus"] = (
                                None if focus_sub == _cat else _cat)
                            st.rerun()
                st.caption("👆 Clic en una barra para "
                           + ("bajar a sus subfamilias."
                              if focus_fam is None else
                              "filtrar el Top de productos a esa subfamilia "
                              "(clic de nuevo para quitar)."))

    # ── Panel Top N productos (muestra Valor S/ + Cantidad) ─────────────
    with pt:
        scope = base_b
        if focus_fam is not None:
            scope = scope[scope["fam"] == focus_fam]
        if focus_sub is not None:
            scope = scope[scope["sub"] == focus_sub]
        _amb = (focus_sub or focus_fam or "todas las familias")
        with _card("fam_top", f"Top {topn} productos · {_compras_truncar(_amb, 24)}",
                   titulo_arriba=True):
            agg = scope.groupby("prod").agg(
                valor=("valor", "sum"), cant=("cant", "sum"), m=("m", "sum"))
            agg = agg.nlargest(topn, "m").sort_values("m")
            if agg.empty:
                st.info("Sin datos de productos.")
            else:
                _txt = [f"S/ {v:,.0f}" + (f"  ·  {c:,.0f} u" if col_cant else "")
                        for v, c in zip(agg["valor"], agg["cant"])]
                figt = go.Figure(go.Bar(
                    x=agg["m"].values, y=[_compras_truncar(i, 28) for i in agg.index],
                    orientation="h", marker_color=SERIE_PRINCIPAL,
                    text=_txt, textposition="outside", cliponaxis=False,
                    customdata=np.stack([agg["valor"].values, agg["cant"].values], axis=-1),
                    hovertemplate="%{y}<br>S/ %{customdata[0]:,.0f} · "
                                  "%{customdata[1]:,.0f} u<extra></extra>"))
                _compras_layout(figt, alto=alturas.por_filas(
                    len(agg), px_fila=32, minimo=240, extra=80))
                figt.update_layout(xaxis=dict(tickprefix=_pref, tickformat=",.0f"),
                                   margin=dict(l=10, r=120, t=10, b=10))
                st.plotly_chart(figt, use_container_width=True, key="compras_g_fam_top")
