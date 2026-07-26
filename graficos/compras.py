"""
graficos.compras — dashboard de Compras: 4 drills (Proveedor, Familia, Cantidad Producto, Evolución Proveedores).
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


from tema import ACENTO, GRIS_BORDE, SERIE_PRINCIPAL, TEXTO_PRINCIPAL
from utils import _norm
from graficos.base import (
    PALETA_CALLAI, _card, _compras_layout, _compras_truncar, _resolver, _slug,
    renderizar_graficos_genericos,
)
from graficos.constructor import _constructor_grafico

def _first_point(evt):
    """Primer punto de una selección de st.plotly_chart(on_select=...).
    Devuelve el dict del punto o None (tolerante a formatos/errores)."""
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        pts = (sel or {}).get("points", [])
        return pts[0] if pts else None
    except Exception:
        return None


def _compras_mini_barras(serie, titulo, fmt="S/ {:,.0f}", alto=400):
    """Mini gráfico de barras horizontales top-N (mayor arriba)."""
    if serie is None or serie.empty:
        st.info("Sin datos para este top.")
        return
    d = serie.sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=d.values,
        y=[_compras_truncar(i) for i in d.index],
        orientation="h",
        marker=dict(color=ACENTO, opacity=0.85),
        text=[fmt.format(v) for v in d.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=alto,
        margin=dict(l=4, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True,
                    key=f"compras_mini_{_slug(titulo)}")


def _periodo_serie(fe, gran):
    """Serie de etiquetas de periodo (ordenables) según granularidad."""
    if gran == "Semana":
        iso = fe.dt.isocalendar()
        return (iso["year"].astype("Int64").astype(str) + "-S"
                + iso["week"].astype("Int64").astype(str).str.zfill(2))
    if gran == "Año":
        return fe.dt.year.astype("Int64").astype(str)
    return fe.dt.to_period("M").astype(str)  # Mes


@st.fragment
def _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                             col_punit, col_um, col_fecha, col_docu=None,
                             d_full=None):
    """Dashboard de Proveedor — barras verticales agrupadas por periodo.

    Gráfico principal: barras verticales por periodo (Semana/Mes/Año), un color
    por proveedor (top N). Clic en una barra → selecciona ese proveedor como
    foco y filtra los paneles A y B de abajo. Los nombres en el hover son
    completos; en las leyendas se truncan.

    Panel A: Top N productos comprados al proveedor en foco (valor + cantidad).
    Panel B: proveedores del producto seleccionado en Panel A.
    """
    if not (col_prov and col_valor):
        st.info("Faltan columnas (Proveedor, Valor) para este gráfico.")
        return

    # ── Controles ──────────────────────────────────────────────────────────
    # Calcular lista de proveedores ANTES de dibujar los controles
    _todos_provs_temp = (d.groupby(col_prov)[col_valor].sum()
                          .sort_values(ascending=False).index.tolist()
                          if col_prov and col_valor else [])
    # Agregar "Otros" al final si hay proveedores fuera del top
    _otros_mask_temp = ~d[col_prov].astype(str).isin(_todos_provs_temp[:20])
    if _otros_mask_temp.any():
        _todos_provs_temp = _todos_provs_temp + ["Otros"]
    _real_provs = [p for p in _todos_provs_temp if p != "Otros"]  # sin "Otros"
    _default_prov_sel = _real_provs[:5]
    # Inicializar el estado de cada proveedor (checkbox) la primera vez que
    # aparece. La clave usa el nombre (estable aunque cambie el orden/filtro).
    for _p in _todos_provs_temp:
        _k = "cp_prov_cb::" + str(_p)
        if _k not in st.session_state:
            st.session_state[_k] = (_p in _default_prov_sel)

    def _cp_set_topn(_n):
        """Marca solo los primeros _n proveedores (por valor). _n=0 → limpiar."""
        for _pp in _todos_provs_temp:
            st.session_state["cp_prov_cb::" + str(_pp)] = (_pp in _real_provs[:_n])

    # Granularidad y Top productos: se leen aquí (de session_state), pero sus
    # selectores se DIBUJAN flotando sobre sus gráficos respectivos (más abajo).
    gran = st.session_state.get("compras_prov_gran") or "Mes"
    topn = st.session_state.get("compras_prov_topn") or 10

    # Selección de proveedores: se LEE de session_state (cp_prov_cb::<nombre>).
    # El popover se DIBUJA flotando arriba-izquierda sobre el gráfico (más
    # abajo), por eso aquí solo se calcula la selección para armar el figure.
    prov_multisel = [p for p in _todos_provs_temp
                     if st.session_state.get("cp_prov_cb::" + str(p))] \
                    or _real_provs[:5]

    # ── Preparar base de datos ─────────────────────────────────────────────
    base = pd.DataFrame({
        "prov":  d[col_prov].astype(str).values,
        "prod":  (d[col_prod].astype(str).values if col_prod else "—"),
        "cant":  (pd.to_numeric(d[col_cant],  errors="coerce").fillna(0).values
                  if col_cant else 0.0),
        "valor": pd.to_numeric(d[col_valor], errors="coerce").fillna(0).values,
        "punit": (pd.to_numeric(d[col_punit], errors="coerce").values
                  if col_punit else np.nan),
        "um":    (d[col_um].astype(str).values if col_um else ""),
        "fecha": (pd.to_datetime(d[col_fecha], errors="coerce").values
                  if col_fecha else pd.NaT),
        "docu":  (d[col_docu].astype(str).values if col_docu else ""),
    })
    base = base[base["prov"].notna() & (base["prov"] != "nan")]
    if base.empty or base["valor"].sum() == 0:
        st.info("Sin datos en el rango seleccionado.")
        return

    # ── Calcular periodo ──────────────────────────────────────────────────
    fe_s = pd.to_datetime(base["fecha"], errors="coerce")
    if gran == "Semana":
        _wstart = (fe_s - pd.to_timedelta(fe_s.dt.weekday, unit="D")).dt.normalize()
        _wend = _wstart + pd.Timedelta(days=6)
        base["_per_sort"] = _wstart.dt.strftime("%Y-%m-%d")   # clave de orden
        _mes_es = {'Jan':'Ene','Apr':'Abr','Aug':'Ago','Dec':'Dic'}
        _per = _wstart.dt.strftime("%d%b") + "-" + _wend.dt.strftime("%d%b")
        for _en, _es in _mes_es.items():
            _per = _per.str.replace(_en, _es)
        base["per"] = _per
    elif gran == "Año":
        base["_per_sort"] = fe_s.dt.year.astype("Int64").astype(str)
        base["per"] = base["_per_sort"]
    else:  # Mes
        base["_per_sort"] = fe_s.dt.to_period("M").astype(str)
        base["per"] = base["_per_sort"]
    base = base[base["per"].notna() & (base["per"] != "<NA>")]

    # Top N proveedores por valor total (para la paleta y el filtro)
    _tot_all  = base["valor"].sum() or 1.0
    top_provs = [p for p in prov_multisel if p in set(base["prov"].unique())]
    if not top_provs:
        top_provs = (base.groupby("prov")["valor"].sum()
                         .nlargest(5).index.tolist())

    # Asignar color por proveedor (los que no están en top → "Otros" en gris)
    base["prov_label"] = base["prov"].where(base["prov"].isin(top_provs), "Otros")

    if "_per_sort" in base.columns:
        _per_order = (base[["_per_sort", "per"]].drop_duplicates()
                      .sort_values("_per_sort")["per"].tolist())
        periodos = list(dict.fromkeys(_per_order))   # deduplicado, orden cronológico
    else:
        periodos = sorted(base["per"].dropna().unique())

    # ── Estado de foco ────────────────────────────────────────────────────
    prov_focus = st.session_state.get("compras_prov_focus")
    prod_focus = st.session_state.get("compras_prov_prodfocus")
    if prov_focus not in set(base["prov"].unique()):
        prov_focus, prod_focus = None, None

    orden_provs = top_provs  # de mayor a menor valor total

    # ── Procesar clic ANTES de dibujar ────────────────────────────────────
    # Leemos la selección que Streamlit guardó en session_state[chart_key] en
    # la interacción previa. Así actualizamos el foco y construimos el figure
    # UNA sola vez con el foco correcto: sin doble rerun = sin parpadeo.
    # Clic en la MISMA barra enfocada → la desenfoca; clic en otra barra del
    # mismo proveedor → cambia el período sin perder el foco.
    _chart_key = f"compras_g_prov_main_{gran}"
    _mp = _first_point(st.session_state.get(_chart_key))
    if _mp is not None:
        _cn = _mp.get("curve_number")
        # Período (barra) clicado: x de la selección, con fallback al índice.
        _per_click = _mp.get("x")
        if _per_click is None:
            _pi = _mp.get("point_index", _mp.get("point_number"))
            if _pi is not None and 0 <= _pi < len(periodos):
                _per_click = periodos[_pi]
        if _cn is not None and 0 <= _cn < len(orden_provs):
            _clicked = orden_provs[_cn]
            # Dedup por (proveedor, período) para no reprocesar el mismo clic.
            _click_key = (_clicked, _per_click)
            if st.session_state.get("compras_prov_last_click") != _click_key:
                st.session_state["compras_prov_last_click"] = _click_key
                _misma_barra = (_clicked == prov_focus and _per_click ==
                                st.session_state.get("compras_prov_perfocus"))
                prov_focus = None if _misma_barra else _clicked
                prod_focus = None
                st.session_state["compras_prov_focus"]     = prov_focus
                st.session_state["compras_prov_prodfocus"] = None
                st.session_state["compras_prov_perfocus"]  = (
                    None if _misma_barra else _per_click)

    # ── Gráfico principal: barras verticales por periodo ──────────────────

    fig = go.Figure()
    for i, prov in enumerate(orden_provs):
        grp = (base[base["prov"] == prov]
               .groupby("per", as_index=False)["valor"].sum()
               .set_index("per")["valor"]
               .reindex(periodos, fill_value=0))
        _pct = base[base["prov"] == prov]["valor"].sum() / _tot_all * 100
        _color = PALETA_CALLAI[i % len(PALETA_CALLAI)]
        # Resaltar el proveedor en foco con opacidad plena; los demás, semitransparentes
        _opacity = 1.0 if (prov_focus is None or prov == prov_focus) else 0.30

        fig.add_bar(
            x=periodos,
            y=grp.values,
            name=_compras_truncar(prov, 22),
            marker=dict(color=_color, opacity=_opacity),
            customdata=[[prov, _pct]] * len(periodos),
            hovertemplate=(
                "<b>%{customdata[0]}</b>  %{x}<br>"
                "S/ %{y:,.0f} · %{customdata[1]:.1f}%"
                "<extra></extra>"
            ),
        )

    # "Otros" proveedores agrupados (gris) — solo si el usuario lo pidió
    _otros_mask = ~base["prov"].isin(top_provs)
    _hay_otros = _otros_mask.any()
    _otros_seleccionado = "Otros" in prov_multisel
    if _hay_otros and _otros_seleccionado:
        grp_otros = (base[_otros_mask]
                     .groupby("per", as_index=False)["valor"].sum()
                     .set_index("per")["valor"]
                     .reindex(periodos, fill_value=0))
        fig.add_bar(
            x=periodos,
            y=grp_otros.values,
            name="Otros",
            marker=dict(color=GRIS_BORDE, opacity=0.6),
            hovertemplate="Otros · %{x}<br>S/ %{y:,.0f}<extra></extra>",
        )

    _compras_layout(fig, alto=420)
    fig.update_layout(

        barmode="group",
        xaxis=dict(type="category", tickangle=0),
        yaxis=dict(tickprefix="S/ ", tickformat=",.0f"),
        # Leyenda VERTICAL flotando DENTRO del área (x<=1 → Plotly no reserva
        # margen → no encoge el gráfico). Fondo semitransparente para leerse
        # sobre las barras. Arranca en y=0.82 para no pisar el toggle superior.
        legend=dict(orientation="v", yanchor="top", y=0.82,
                    xanchor="right", x=0.99, font=dict(size=10),
                    bgcolor="rgba(255,255,255,0.78)",
                    bordercolor="rgba(0,0,0,0.12)", borderwidth=1),
        hovermode="closest",
    )
    # Range-slider si hay muchos periodos
    if len(periodos) > 12:
        fig.update_xaxes(
            rangeslider=dict(visible=True, thickness=0.07),
            range=[len(periodos) - 12.5, len(periodos) - 0.5],
        )

    # ── Selector de granularidad FLOTANTE sobre el gráfico ────────────────
    # El contenedor "compras_prov_card_chart" es posición relativa; dentro,
    # las pills se posicionan en absoluto arriba-derecha, superpuestas al gráfico.
    st.markdown("""
        <style>
        .st-key-compras_prov_card_chart { position: relative; }
        /* La leyenda se movió a la derecha (vertical); la banda superior solo
           tiene popover (izq) + toggle (der), alineados arriba. */
        .st-key-gran_float {
            position: absolute; top: 6px; right: 6px; z-index: 20;
            width: auto !important;
        }
        /* Popover de proveedores flotando arriba-IZQUIERDA (compacto) */
        .st-key-prov_pop_float {
            position: absolute; top: 6px; left: 6px; z-index: 21;
            width: auto !important;
        }
        .st-key-prov_pop_float [data-testid="stPopover"] button {
            min-width: 0 !important;
            padding: 4px 12px !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            border-radius: 999px !important;
        }
        .st-key-gran_float [data-testid="stElementToolbar"] { display: none; }
        /* Ocultar la barra de herramientas del propio gráfico (fullscreen) */
        .st-key-compras_prov_card_chart > div > [data-testid="stElementToolbar"] { display: none; }

        /* Top productos 5/10/20 — alojado en la cabecera del Panel A, a la
           derecha del título (Opción A: barra de cabecera con divisoria). */
        .st-key-chartcard_prov_prods { position: relative; }
        .st-key-topn_float {
            position: absolute; top: 10px; right: 16px; z-index: 20;
            width: auto !important;
        }
        /* Ámbito de período + Top N en una sola fila dentro de la cabecera
           (patrón del repo: fila sobre el stVerticalBlock del contenedor). */
        .st-key-topn_float [data-testid="stVerticalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 8px !important;
            align-items: center !important;
        }
        .st-key-topn_float [data-testid="stVerticalBlock"] > div {
            width: auto !important;
        }
        /* Reservar espacio a la derecha del título para que se trunque con
           "…" antes de llegar a los dos controles (ámbito + Top N). */
        .st-key-chartcard_prov_prods .chart-card-hdr { padding-right: 252px; }
        .st-key-topn_float [data-testid="stElementToolbar"] { display: none; }

        /* Ámbito de fecha (En rango / Todo) — en la cabecera del Panel B. */
        .st-key-chartcard_prov_prov_de_prod { position: relative; }
        .st-key-panelb_scope_float {
            position: absolute; top: 10px; right: 16px; z-index: 20;
            width: auto !important;
        }
        .st-key-chartcard_prov_prov_de_prod .chart-card-hdr { padding-right: 140px; }
        .st-key-panelb_scope_float [data-testid="stElementToolbar"] { display: none; }

        /* ── Cápsula segmentada: unir las pills en un solo control ── */
        .st-key-gran_float [data-testid="stButtonGroup"],
        .st-key-topn_float [data-testid="stButtonGroup"],
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] {
            gap: 0 !important;
            border: 1px solid rgba(49,51,63,0.2);
            border-radius: 999px;
            overflow: hidden;
            background: var(--background-color, #fff);
        }
        .st-key-gran_float [data-testid="stButtonGroup"] button,
        .st-key-topn_float [data-testid="stButtonGroup"] button,
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button {
            border: 0 !important;
            border-radius: 0 !important;
            margin: 0 !important;
        }
        .st-key-gran_float [data-testid="stButtonGroup"] button:not(:first-child),
        .st-key-topn_float [data-testid="stButtonGroup"] button:not(:first-child),
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button:not(:first-child) {
            border-left: 1px solid rgba(49,51,63,0.15) !important;
        }

        /* ── TARJETAS COLAPSABLES: animacion unfold (drill Proveedor) ── */
        @keyframes unfoldDown {
            0%   { transform: perspective(600px) scaleY(0) rotateX(-90deg);
                   opacity: 0; }
            65%  { transform: perspective(600px) scaleY(1.04) rotateX(3deg);
                   opacity: 1; }
            100% { transform: perspective(600px) scaleY(1) rotateX(0deg);
                   opacity: 1; }
        }
        /* La animacion se aplica DIRECTO a la tarjeta por su key estable.
           Streamlit reutiliza el nodo DOM mientras sigue abierta, asi que el
           unfold solo corre al montarse (oculta->visible), no en cada rerun.
           fill-mode backwards: arranca colapsada y al terminar no deja
           transform residual (evita texto borroso). NO usamos <script>
           porque st.markdown NO ejecuta JS. */
        .st-key-compras_prov_card_paneles,
        .st-key-compras_prov_card_docs {
            transform-origin: top center;
            animation: unfoldDown 0.38s cubic-bezier(0.4, 0, 0.2, 1) backwards;
        }
        /* Encabezado-toggle: el título ES el botón, con −/+ delante.
           Se ve como texto plano (sin fondo ni borde), no como botón. */
        .st-key-collapse_hdr_paneles button,
        .st-key-collapse_hdr_docs button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 4px 0 !important;
            min-height: 0 !important;
            width: auto !important;
            justify-content: flex-start !important;
            color: var(--text-secondary, #71717a) !important;
        }
        .st-key-collapse_hdr_paneles button p,
        .st-key-collapse_hdr_docs button p {
            font-size: 13px !important;
            font-weight: 600 !important;
            text-align: left !important;
            color: var(--text-secondary, #71717a) !important;
        }
        .st-key-collapse_hdr_paneles button:hover, .st-key-collapse_hdr_paneles button:hover p,
        .st-key-collapse_hdr_docs button:hover, .st-key-collapse_hdr_docs button:hover p,
        .st-key-collapse_hdr_paneles button:focus, .st-key-collapse_hdr_paneles button:focus p,
        .st-key-collapse_hdr_docs button:focus, .st-key-collapse_hdr_docs button:focus p {
            color: var(--accent, #6c5ce7) !important;
        }
        .st-key-collapse_hdr_paneles button:focus,
        .st-key-collapse_hdr_docs button:focus,
        .st-key-collapse_hdr_paneles button:active,
        .st-key-collapse_hdr_docs button:active {
            background: transparent !important;
            box-shadow: none !important;
            outline: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Key ESTABLE (solo depende de la granularidad): evita que Streamlit
    # remonte el componente Plotly en cada clic. El clic se procesa arriba,
    # antes de construir el figure (sin doble rerun = sin parpadeo).
    with st.container(border=True, key="compras_prov_card_chart"):
        # Popover de proveedores — flota arriba-izquierda (misma banda que la
        # leyenda y el toggle). Los checkboxes escriben cp_prov_cb::<nombre>;
        # la selección se leyó arriba para armar el figure (patrón 1 rerun).
        with st.container(key="prov_pop_float"):
            _sel_now = [p for p in _todos_provs_temp
                        if st.session_state.get("cp_prov_cb::" + str(p))]
            with st.popover(f"Proveedores ({len(_sel_now)})"):
                _bt = st.columns(4)
                _bt[0].button("Top 3", key="cp_topn3", use_container_width=True,
                              on_click=_cp_set_topn, args=(3,))
                _bt[1].button("Top 5", key="cp_topn5", use_container_width=True,
                              on_click=_cp_set_topn, args=(5,))
                _bt[2].button("Top 10", key="cp_topn10", use_container_width=True,
                              on_click=_cp_set_topn, args=(10,))
                _bt[3].button("Limpiar", key="cp_topnclr", use_container_width=True,
                              on_click=_cp_set_topn, args=(0,))
                _q = st.text_input("Buscar", key="cp_prov_q",
                                   placeholder="Buscar proveedor por nombre...",
                                   label_visibility="collapsed").strip().lower()
                _vistos = [p for p in _todos_provs_temp
                           if not _q or _q in str(p).lower()]
                if not _vistos:
                    st.caption("Sin coincidencias.")
                for _p in _vistos:
                    st.checkbox(_p, key="cp_prov_cb::" + str(_p))
        with st.container(key="gran_float"):
            st.pills("Periodo", ["Semana", "Mes", "Año"], default="Mes",
                     key="compras_prov_gran", label_visibility="collapsed")
        st.plotly_chart(
            fig,
            use_container_width=True,
            key=_chart_key,
            on_select="rerun",
            selection_mode="points",
            # edits.legendPosition: permite ARRASTRAR la leyenda con el cursor.
            # Ojo: la posición no persiste (al reejecutar vuelve a y=0.82).
            config={"displayModeBar": False, "edits": {"legendPosition": True}},
        )

    # ── Paneles A y B ─────────────────────────────────────────────────────
    def _um_de(grp):
        if not col_um:
            return ""
        m = grp["um"].mode()
        return (" " + m.iat[0]) if len(m) and m.iat[0] not in ("", "nan") else ""

    def _base_prov_de(_src):
        """Base mínima (prov/prod/punit/cant/um/fecha) para la tabla del
        Panel B, a partir de cualquier df origen (`d` filtrado por fecha o
        `d_full` con todo el histórico)."""
        _b = pd.DataFrame({
            "prov":  _src[col_prov].astype(str).values,
            "prod":  (_src[col_prod].astype(str).values if col_prod else "—"),
            "cant":  (pd.to_numeric(_src[col_cant], errors="coerce").fillna(0).values
                      if col_cant else 0.0),
            "punit": (pd.to_numeric(_src[col_punit], errors="coerce").values
                      if col_punit else np.nan),
            "um":    (_src[col_um].astype(str).values if col_um else ""),
            "fecha": (pd.to_datetime(_src[col_fecha], errors="coerce").values
                      if col_fecha else pd.NaT),
        })
        return _b[_b["prov"].notna() & (_b["prov"] != "nan")]

    if "cp_paneles_abierto" not in st.session_state:
        st.session_state["cp_paneles_abierto"] = True
    # El título ES el toggle: prefijo −/+ (signo menos U+2212 + NBSP para que no
    # se parsee como viñeta Markdown y para que + y − alineen igual).
    with st.container(key="collapse_hdr_paneles"):
        _pan_ab = st.session_state["cp_paneles_abierto"]
        if st.button(("−" if _pan_ab else "+")
                     + " Analisis de productos y proveedores",
                     key="cp_btn_paneles"):
            st.session_state["cp_paneles_abierto"] = not _pan_ab
            st.rerun()
    if st.session_state.get("cp_paneles_abierto", True):
        with st.container(border=True, key="compras_prov_card_paneles"):
            pa, pb = st.columns(2)

            # Panel A: Top N productos del proveedor en foco
            with pa:
                _ta = ("Selecciona un proveedor arriba para ver sus productos"
                       if prov_focus is None
                       else f"Productos · {_compras_truncar(prov_focus, 24)}")
                with _card("prov_prods", _ta, titulo_arriba=True):
                    # Controles de cabecera (encima de la divisoria, Opción 1):
                    # ámbito de período + Top N, en una fila. El ámbito arranca
                    # en "periodo" (el período de la barra que se clicó arriba).
                    _per_lbl = {"Semana": "Esta semana",
                                "Año": "Este año"}.get(gran, "Este mes")
                    with st.container(key="topn_float"):
                        _scope = st.pills(
                            "Ámbito de período", ["rango", "periodo"],
                            default="periodo",
                            format_func=lambda v: {"rango": "Todo el rango",
                                                   "periodo": _per_lbl}[v],
                            key="compras_prov_prod_scope",
                            label_visibility="collapsed",
                        ) or "periodo"
                        st.pills("Top productos", [5, 10, 20], default=10,
                                 key="compras_prov_topn", label_visibility="collapsed")
                    if prov_focus is None:
                        pass
                    else:
                        sub = base[base["prov"] == prov_focus]
                        _perf = st.session_state.get("compras_prov_perfocus")
                        if _scope == "periodo" and _perf is not None:
                            sub = sub[sub["per"] == _perf]
                            st.caption(f"📅 Solo {_perf} — período de la barra "
                                       "que clicaste arriba.")
                        agg = (sub.groupby("prod")
                                  .agg(valor=("valor", "sum"), cant=("cant", "sum"))
                                  .nlargest(topn, "valor")
                                  .sort_values("valor"))
                        if agg.empty:
                            st.info("Sin productos para este proveedor.")
                        else:
                            prod_cats = list(agg.index)
                            _um_map = {p: _um_de(sub[sub["prod"] == p]) for p in prod_cats}
                            _txt = [
                                f"S/ {v:,.0f}  ·  {c:,.0f}{_um_map[p]}"
                                for p, v, c in zip(prod_cats, agg["valor"], agg["cant"])
                            ]
                            _cc = [SERIE_PRINCIPAL if p == prod_focus else ACENTO
                                   for p in prod_cats]
                            figa = go.Figure(go.Bar(
                                x=agg["valor"].values,
                                y=[_compras_truncar(i, 24) for i in prod_cats],
                                orientation="h", marker_color=_cc,
                                text=_txt, textposition="outside", cliponaxis=False,
                                hovertemplate="%{y}<extra></extra>",
                            ))
                            _compras_layout(figa, alto=max(240, 34 * len(agg) + 80))
                            figa.update_xaxes(tickprefix="S/ ", tickformat=",.0f")
                            figa.update_layout(margin=dict(l=10, r=140, t=12, b=10))
                            _aevt = st.plotly_chart(
                                figa, use_container_width=True,
                                key=f"compras_g_prov_prods_{prov_focus}_{prod_focus}",
                                on_select="rerun", selection_mode="points",
                                config={"displayModeBar": False},
                            )
                            _ap = _first_point(_aevt)
                            if _ap is not None:
                                _j = _ap.get("point_number", _ap.get("point_index"))
                                if _j is not None and 0 <= _j < len(prod_cats):
                                    st.session_state["compras_prov_prodfocus"] = prod_cats[_j]
                                    st.rerun()


            # Panel B: proveedores del producto seleccionado
            with pb:
                _tb = ("Proveedores del producto" if prod_focus is None
                       else f"Proveedores de · {_compras_truncar(prod_focus, 26)}")
                with _card("prov_prov_de_prod", _tb, titulo_arriba=True):
                    # Toggle de ámbito de fecha, alojado en la cabecera (dcha.):
                    # "En rango" respeta el filtro superior; "Todo" recalcula con
                    # el histórico completo (d_full), ignorando el filtro de fecha.
                    with st.container(key="panelb_scope_float"):
                        _scope = st.pills(
                            "Ámbito de fecha", ["En rango", "Todo"],
                            default="En rango", key="compras_prov_prov_scope",
                            label_visibility="collapsed",
                        ) or "En rango"
                    if prod_focus is None:
                        pass
                    else:
                        _todo_hist = (_scope == "Todo" and d_full is not None)
                        _srcB = _base_prov_de(d_full) if _todo_hist else base
                        if _todo_hist:
                            st.caption("📅 Todo el histórico — ignora el filtro "
                                       "de fecha de arriba.")
                        sub2 = _srcB[_srcB["prod"] == prod_focus]
                        filas = []
                        for prov, grp in sub2.groupby("prov"):
                            g2 = grp
                            _uf = None
                            if col_fecha and grp["fecha"].notna().any():
                                g2 = grp.dropna(subset=["fecha"]).sort_values("fecha")
                                _uf = pd.to_datetime(g2["fecha"].iloc[-1])
                            ult = (g2["punit"].iloc[-1]
                                   if (col_punit and len(g2)
                                       and pd.notna(g2["punit"].iloc[-1])) else np.nan)
                            filas.append({
                                "Proveedor":     prov,
                                "Último precio": ult,
                                "Últ. compra":   (_uf.strftime("%d/%m/%Y")
                                                  if _uf is not None else "—"),
                                "Cant. acum.":   grp["cant"].sum(),
                                "Unid":          (_um_de(grp).strip() if col_um else ""),
                            })
                        tabla = pd.DataFrame(filas).sort_values("Cant. acum.", ascending=False)
                        _orden = ["Proveedor", "Último precio", "Últ. compra",
                                  "Cant. acum.", "Unid"]
                        if not col_um:
                            _orden.remove("Unid")
                            tabla = tabla.drop(columns=["Unid"])
                        if not col_fecha:
                            _orden.remove("Últ. compra")
                            tabla = tabla.drop(columns=["Últ. compra"])
                        tabla = tabla[_orden]
                        _min = (tabla["Último precio"].min()
                                if tabla["Último precio"].notna().any() else None)

                        def _hl(col):
                            if col.name != "Último precio" or _min is None:
                                return ["" for _ in col]
                            return ["color:#15803d;font-weight:600"
                                    if (pd.notna(v) and v == _min) else "" for v in col]

                        sty = (tabla.style
                               .format({"Último precio": "S/ {:,.2f}",
                                        "Cant. acum.": "{:,.0f}"},
                                       na_rep="—")
                               .apply(_hl, axis=0))
                        st.dataframe(sty, hide_index=True, use_container_width=True,
                                     height=min(430, 60 + 34 * len(tabla)))
                        st.caption("Último precio = precio unitario de la compra más "
                                   "reciente. Verde = menor precio.")

    # ── Tabla pivotable de documentos (debajo de los paneles A/B) ─────────
    # Cada fila es una línea de detalle (documento × producto). El usuario
    # puede arrastrar campos a Filas/Columnas/Valores (panel derecho) para
    # pivotar. Por defecto: filas = Proveedor→Fecha→Documento→Producto,
    # columnas = Período (Semana/Mes/Año), valor = suma. Gran total al pie.
    import json  # noqa: E402
    from st_aggrid import AgGrid, JsCode  # noqa: E402

    if "cp_docs_abierto" not in st.session_state:
        st.session_state["cp_docs_abierto"] = True
    # El titulo ES el toggle (mismo patron que Paneles): prefijo −/+ con NBSP
    # (evita que Markdown lo lea como vineta y alinea + con −).
    with st.container(key="collapse_hdr_docs"):
        _docs_ab = st.session_state["cp_docs_abierto"]
        if st.button(("−" if _docs_ab else "+")
                     + f" Detalle de documentos por proveedor · vista {gran}",
                     key="cp_btn_docs"):
            st.session_state["cp_docs_abierto"] = not _docs_ab
            st.rerun()
    _bd = base[base["prov"].isin(top_provs)].copy()
    if st.session_state.get("cp_docs_abierto", True) and not _bd.empty:
        _fe = pd.to_datetime(_bd["fecha"], errors="coerce")
        _pv_docs = pd.DataFrame({
            "Proveedor": _bd["prov"].astype(str).values,
            # Fecha en ISO para orden correcto; se muestra dd/mm/yyyy en el front
            "Fecha": _fe.dt.strftime("%Y-%m-%d").fillna("").values,
            "Documento": (_bd["docu"].astype(str).values
                          if col_docu else _bd.index.astype(str).values),
            "Producto": _bd["prod"].astype(str).values,
            "Periodo": _bd["per"].astype(str).values,
            "Valor": _bd["valor"].astype(float).values,
        })

        _pv_box = st.container(border=True, key="compras_prov_card_docs")
        _pv_box.caption("Arrastra campos a Filas / Columnas / Valores en el panel "
                        "derecho para pivotar. ▸ expande cada nivel.")

        _fmt_soles = JsCode(
            "function(p){ if(p.value==null) return ''; "
            "return 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
        _fmt_fecha = JsCode(
            "function(p){ if(!p.value) return ''; "
            "var s=String(p.value).split('-'); "
            "return s.length===3 ? s[2]+'/'+s[1]+'/'+s[0] : p.value; }")
        # Orden cronológico de las columnas de período en el pivote
        _pivot_cmp = JsCode(
            "function(a,b){ var o=" + json.dumps(periodos) + "; "
            "return o.indexOf(a)-o.indexOf(b); }")

        _col_defs_pv = [
            {"field": "Proveedor", "rowGroup": True, "rowGroupIndex": 0,
             "hide": True},
            {"field": "Fecha", "rowGroup": True, "rowGroupIndex": 1,
             "hide": True, "valueFormatter": _fmt_fecha},
            {"field": "Documento", "rowGroup": True, "rowGroupIndex": 2,
             "hide": True},
            {"field": "Producto", "rowGroup": True, "rowGroupIndex": 3,
             "hide": True},
            {"field": "Periodo", "headerName": "Período", "pivot": True,
             "hide": True, "pivotComparator": _pivot_cmp},
            {"field": "Valor", "type": "numericColumn", "aggFunc": "sum",
             "valueFormatter": _fmt_soles, "minWidth": 110},
        ]

        _grid_pv = {
            "columnDefs": _col_defs_pv,
            "defaultColDef": {
                "resizable": True, "sortable": True, "filter": True,
                "enableRowGroup": True, "enablePivot": True,
                "enableValue": True, "minWidth": 110,
            },
            "pivotMode": True,
            "groupDefaultExpanded": 0,
            "autoGroupColumnDef": {
                "headerName": "Proveedor / Fecha / Documento / Producto",
                "minWidth": 300, "pinned": "left",
                "cellRendererParams": {"suppressCount": True},
            },
            "grandTotalRow": "bottom",
            "getRowStyle": JsCode(
                "function(p){ if(p.node.footer && p.node.level===-1){ "
                "return {'fontWeight':'600','background':'#EEEDFE',"
                "'color':'#4938b8'}; } }"),
            "sideBar": {
                "toolPanels": [{
                    "id": "columns",
                    "labelDefault": "Columnas",
                    "labelKey": "columns",
                    "iconKey": "columns",
                    "toolPanel": "agColumnsToolPanel",
                }],
                "position": "right",
            },
            "rowHeight": 30,
            "headerHeight": 38,
        }
        with _pv_box:
            AgGrid(
                _pv_docs,
                gridOptions=_grid_pv,
                allow_unsafe_jscode=True,
                theme="streamlit",
                height=560,
                enable_enterprise_modules=True,
                fit_columns_on_grid_load=True,
                key=f"cp_prov_pivot_docs_{gran}",
            )

            st.download_button(
                "⬇ Descargar CSV",
                data=_pv_docs.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"compras_documentos_{gran.lower()}.csv",
                mime="text/csv",
                key="cp_prov_resumen_dl",
            )


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

    # ── Controles ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                        default="Mes", key="compras_fam_gran") or "Mes"
    with c2:
        vista = st.pills("Vista", ["Apilado", "Agrupado"],
                         default="Apilado", key="compras_fam_vista") or "Apilado"
    with c3:
        _meas = ["Valor S/"] + (["Cantidad"] if col_cant else [])
        meas = st.pills("Medir", _meas, default="Valor S/",
                        key="compras_fam_meas") or "Valor S/"
    with c4:
        topn = st.pills("Top", [5, 10, 20], default=10,
                        key="compras_fam_topn") or 10

    es_valor = (meas == "Valor S/")
    fe = pd.to_datetime(d[col_fecha], errors="coerce")

    valor_s = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    cant_s = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
              if col_cant else pd.Series(0.0, index=d.index))
    base = pd.DataFrame({
        "per": _periodo_serie(fe, gran).values,
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

    # ── Estado de drill (por clic en las barras) + navegación ───────────
    fams_all = sorted(base["fam"].dropna().unique().tolist())
    focus_fam = st.session_state.get("compras_fam_focus")
    focus_sub = st.session_state.get("compras_fam_subfocus")
    if focus_fam not in fams_all:
        focus_fam, focus_sub = None, None

    desglose = "Total familia"
    nav = st.columns([1.1, 1.5, 1.4, 3])
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
        # expandir a subfamilias en el gráfico del tiempo.
        if focus_fam is not None and col_subfam:
            desglose = st.pills("Desglose", ["Total familia", "Por subfamilia"],
                                default="Total familia", key="compras_fam_desglose",
                                label_visibility="collapsed") or "Total familia"
    with nav[3]:
        _ruta = ("Todas" + (f" › {focus_fam}" if focus_fam else "")
                 + (f" › {focus_sub}" if focus_sub else ""))
        st.caption(f"📂 {_ruta}  ·  clic en las barras para bajar de nivel")

    # ── Barras en el tiempo (serie = familia o subfamilia) ──────────────
    if focus_fam is None:
        tb, serie_col, titulo_ser = base, "fam", "familia"
    elif desglose == "Por subfamilia":
        tb, serie_col, titulo_ser = base[base["fam"] == focus_fam], "sub", "subfamilia"
    else:
        tb, serie_col, titulo_ser = base[base["fam"] == focus_fam], "fam", "familia"

    tot_ser = tb.groupby(serie_col)["m"].sum().sort_values(ascending=False)
    top_ser = tot_ser.head(6).index.tolist()
    tb = tb.copy()
    tb["serie"] = tb[serie_col].where(tb[serie_col].isin(top_ser), "Otros")
    g = tb.groupby(["per", "serie"], as_index=False)["m"].sum()
    periodos = sorted(g["per"].unique())
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
    _compras_layout(fig, alto=380)
    _mn = "Valor" if es_valor else "Cantidad"
    fig.update_layout(
        title=f"{_mn} de compra por {gran.lower()} y {titulo_ser}"
              + ("" if focus_fam is None else f" — {_compras_truncar(focus_fam, 32)}"),
        barmode="stack" if vista == "Apilado" else "group",
        yaxis=dict(tickprefix=_pref, tickformat=",.0f"),
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10)))
    fig.update_xaxes(type="category", tickangle=-45)
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
                _compras_layout(figc, alto=max(240, 32 * len(comp) + 80))
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
                _compras_layout(figt, alto=max(240, 32 * len(agg) + 80))
                figt.update_layout(xaxis=dict(tickprefix=_pref, tickformat=",.0f"),
                                   margin=dict(l=10, r=120, t=10, b=10))
                st.plotly_chart(figt, use_container_width=True, key="compras_g_fam_top")


@st.fragment
def _compras_cantidad_producto(d, col_prod, col_cant, col_valor, col_punit, col_fecha):
    """Cantidad/Valor de compra por producto, agrupable por Semana/Mes/Año.

    Controles: granularidad (Semana/Mes/Año), vista (Agrupado/Apilado),
    magnitud (Cantidad/Valor S/), y foco (Top 8 o un producto). Muestra 3
    KPIs del rango (valor total, precio promedio ponderado, cantidad total).
    Vive en su @st.fragment: cambiar un control solo redibuja esto.
    """
    if not (col_prod and col_fecha and (col_cant or col_valor)):
        st.info("Faltan columnas (Producto, Fecha y Cantidad o Valor) "
                "para este gráfico.")
        return

    # ── Controles ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([1.1, 1.1, 1.1, 2])
    with c1:
        gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                        default="Mes", key="compras_cant_gran") or "Mes"
    with c2:
        vista = st.pills("Vista", ["Agrupado", "Apilado"],
                         default="Agrupado", key="compras_cant_vista") or "Agrupado"
    with c3:
        _meas = []
        if col_cant:
            _meas.append("Cantidad")
        if col_valor:
            _meas.append("Valor S/")
        meas = st.pills("Medir", _meas, default=_meas[0],
                        key="compras_cant_meas") or _meas[0]
    with c4:
        prods = sorted(d[col_prod].dropna().astype(str).unique().tolist())
        foco = st.selectbox("Producto", ["Top 8 productos"] + prods,
                            key="compras_cant_prod")

    # ── Preparación de datos ────────────────────────────────────────────
    fe = pd.to_datetime(d[col_fecha], errors="coerce")
    val = (pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
           if col_valor else pd.Series(0.0, index=d.index))
    cant = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
            if col_cant else pd.Series(0.0, index=d.index))

    if gran == "Semana":
        iso = fe.dt.isocalendar()
        per = (iso["year"].astype("Int64").astype(str) + "-S"
               + iso["week"].astype("Int64").astype(str).str.zfill(2))
    elif gran == "Año":
        per = fe.dt.year.astype("Int64").astype(str)
    else:  # Mes
        per = fe.dt.to_period("M").astype(str)

    base = pd.DataFrame({
        "per": per.values, "prod": d[col_prod].astype(str).values,
        "cant": cant.values, "val": val.values,
    })
    base["m"] = base["cant"] if meas == "Cantidad" else base["val"]
    base = base[base["per"].notna() & (base["per"] != "<NA>")]
    if base.empty:
        st.info("Sin datos en el rango seleccionado.")
        return

    # ── Foco: Top 8 o un producto ───────────────────────────────────────
    if foco == "Top 8 productos":
        orden = base.groupby("prod")["m"].sum().nlargest(8).index.tolist()
        scope = base[base["prod"].isin(orden)]
        multi = True
    else:
        orden = [foco]
        scope = base[base["prod"] == foco]
        multi = False
    if scope.empty:
        st.info("Sin datos para el producto seleccionado.")
        return

    # ── KPIs del rango (sobre el foco mostrado) ─────────────────────────
    k_val = float(scope["val"].sum())
    k_cant = float(scope["cant"].sum())
    k_pp = (k_val / k_cant) if k_cant else 0.0
    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Valor total comprado", f"S/ {k_val:,.0f}")
    m2.metric("🏷️ Precio promedio", f"S/ {k_pp:,.2f}")
    m3.metric("📦 Cantidad total", f"{k_cant:,.0f}")

    # ── Barras por periodo ──────────────────────────────────────────────
    periodos = sorted(scope["per"].unique())
    es_valor = (meas == "Valor S/")
    _pref = "S/ " if es_valor else ""
    _tpl = "S/ %{y:,.0f}" if es_valor else "%{y:,.0f}"

    fig = go.Figure()
    if multi:
        for i, p in enumerate(orden):
            s = (scope[scope["prod"] == p].groupby("per")["m"].sum()
                 .reindex(periodos, fill_value=0))
            fig.add_bar(x=periodos, y=s.values,
                        name=_compras_truncar(p, 22),
                        marker_color=PALETA_CALLAI[i % len(PALETA_CALLAI)],
                        hovertemplate="%{fullData.name}<br>%{x}<br>"
                                      + _tpl + "<extra></extra>")
        fig.update_layout(barmode="stack" if vista == "Apilado" else "group")
    else:
        s = scope.groupby("per")["m"].sum().reindex(periodos, fill_value=0)
        fig.add_bar(x=periodos, y=s.values, name=foco, marker_color=ACENTO,
                    text=[f"{_pref}{v:,.0f}" for v in s.values],
                    textposition="outside", cliponaxis=False,
                    hovertemplate="%{x}<br>" + _tpl + "<extra></extra>")

    _compras_layout(fig, alto=440)
    fig.update_layout(
        title=f"{meas} de compra por {gran.lower()}"
              + ("" if multi else f" — {_compras_truncar(foco, 40)}"),
        yaxis=dict(tickprefix=_pref, tickformat=",.0f"),
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10)),
    )
    fig.update_xaxes(type="category", tickangle=-45)
    st.plotly_chart(fig, use_container_width=True, key="compras_g_cant_prod")


@st.fragment
def _compras_evolucion_proveedores(d, col_prov, col_prod, col_cant,
                                    col_valor, col_punit, col_fecha):
    """Dashboard rediseñado de evolución de compras por proveedor.

    Layout exacto del mockup:
      · Fila de controles: Agrupar por (Día/Semana/Mes/Año) + Métrica
        (dropdown) + Selector de proveedores con búsqueda (máx. 5).
      · Gráfico principal: barras agrupadas con range-slider inferior.
      · Panel de detalle del proveedor seleccionado (clic en leyenda o barra):
        - KPIs (Total Compras, % Participación, Órdenes, Productos, Última compra)
        - Mini sparkline de evolución
        - Tabla "Top productos comprados" con % participación (clic → drill)
      · Tabla "Otros proveedores que también vendieron X producto"
        con barras de progreso y % participación.
      · Consejo al pie.
    """
    if not (col_prov and col_valor and col_fecha):
        st.info("Faltan columnas (Proveedor, Valor, Fecha) para este gráfico.")
        return

    # ── Preparar datos base ───────────────────────────────────────────────
    _fe = pd.to_datetime(d[col_fecha], errors="coerce")
    _vv = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    _cn = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0) if col_cant
           else pd.Series(0.0, index=d.index))
    base = pd.DataFrame({
        "prov":  d[col_prov].astype(str).values,
        "prod":  (d[col_prod].astype(str).values if col_prod else "—"),
        "cant":  _cn.values,
        "valor": _vv.values,
        "punit": (pd.to_numeric(d[col_punit], errors="coerce").values
                  if col_punit else np.nan),
        "fecha": _fe.values,
    })
    base = base[base["prov"].notna() & (base["prov"] != "nan")]
    if base.empty or base["valor"].sum() == 0:
        st.info("Sin datos en el rango seleccionado.")
        return

    _tot_all = float(base["valor"].sum()) or 1.0
    _todos_provs = (base.groupby("prov")["valor"].sum()
                    .sort_values(ascending=False).index.tolist())

    # ── Fila 1: controles ─────────────────────────────────────────────────
    cc1, cc2, cc3 = st.columns([1.4, 1.4, 3.2])
    with cc1:
        gran = st.pills(
            "Agrupar por", ["Día", "Semana", "Mes", "Año"],
            default="Mes", key="evo_prov_gran",
            label_visibility="collapsed",
        ) or "Mes"
    with cc2:
        _meas_opts = ["Total Compras (S/)"] + (["Cantidad"] if col_cant else [])
        meas = st.selectbox(
            "Métrica", _meas_opts,
            key="evo_prov_meas", label_visibility="collapsed",
        )
    with cc3:
        # Multiselect con búsqueda, máx. 5 proveedores
        _prev_sel = st.session_state.get("evo_prov_sel") or []
        # Garantizar que los previamente seleccionados sigan en las opciones
        _valid_prev = [p for p in _prev_sel if p in _todos_provs]
        _default_provs = _valid_prev if _valid_prev else _todos_provs[:3]
        prov_sel = st.multiselect(
            "Seleccionar proveedores (máx. 5)",
            _todos_provs,
            default=_default_provs,
            max_selections=5,
            key="evo_prov_sel",
            label_visibility="collapsed",
            placeholder="Buscar proveedor...",
        ) or _todos_provs[:3]

    es_valor = (meas == "Total Compras (S/)")

    # ── Calcular periodos según granularidad ──────────────────────────────
    fe_s = pd.to_datetime(base["fecha"], errors="coerce")
    if gran == "Día":
        base["per"] = fe_s.dt.date.astype(str)
    elif gran == "Semana":
        _iso = fe_s.dt.isocalendar()
        base["per"] = (_iso["year"].astype("Int64").astype(str) + "-S"
                       + _iso["week"].astype("Int64").astype(str).str.zfill(2))
    elif gran == "Año":
        base["per"] = fe_s.dt.year.astype("Int64").astype(str)
    else:  # Mes
        base["per"] = fe_s.dt.to_period("M").astype(str)

    base["m"] = base["valor"] if es_valor else base["cant"]
    base_f = base[base["prov"].isin(prov_sel)].copy()
    base_f = base_f[base_f["per"].notna() & (base_f["per"] != "<NA>")]

    if base_f.empty:
        st.info("Sin datos para los proveedores seleccionados.")
        return

    periodos = sorted(base_f["per"].unique())

    # ── Gráfico principal: barras agrupadas + range-slider ─────────────────
    fig_main = go.Figure()
    for i, prov in enumerate(prov_sel):
        grp = base_f[base_f["prov"] == prov].groupby("per")["m"].sum().reindex(
            periodos, fill_value=0)
        fig_main.add_bar(
            x=periodos, y=grp.values,
            name=_compras_truncar(prov, 32),
            marker_color=PALETA_CALLAI[i % len(PALETA_CALLAI)],
            hovertemplate=(
                "<b>" + _compras_truncar(prov, 32) + "</b><br>"
                + "%{x}<br>"
                + ("S/ %{y:,.0f}" if es_valor else "%{y:,.0f}")
                + "<extra></extra>"
            ),
        )

    _pref_y = "S/ " if es_valor else ""
    _compras_layout(fig_main, alto=420)
    fig_main.update_layout(
        barmode="group",
        xaxis=dict(
            type="category",
            tickangle=-30,
            rangeslider=dict(
                visible=True,
                thickness=0.10,
                bgcolor="#f0edfe",
                bordercolor="#6c5ce7",
                borderwidth=1,
            ),
        ),
        yaxis=dict(tickprefix=_pref_y, tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    font=dict(size=11)),
        hovermode="x unified",
        margin=dict(l=10, r=10, t=10, b=70),
    )

    # Mostrar 12 periodos iniciales si hay más
    if len(periodos) > 12:
        fig_main.update_xaxes(
            range=[len(periodos) - 12.5, len(periodos) - 0.5]
        )

    st.plotly_chart(fig_main, use_container_width=True, key="evo_prov_main_chart")
    st.caption("Arrastra la barra inferior para desplazarte en el tiempo  ⓘ")

    # ── Estado de foco (proveedor + producto) ─────────────────────────────
    prov_focus = st.session_state.get("evo_prov_focus")
    prod_focus = st.session_state.get("evo_prov_prodfocus")

    # Si el proveedor en foco ya no está en la selección, resetear
    if prov_focus not in prov_sel:
        prov_focus = prov_sel[0] if prov_sel else None
        prod_focus = None
        st.session_state["evo_prov_focus"] = prov_focus
        st.session_state["evo_prov_prodfocus"] = None

    # Selector de proveedor activo (chips debajo del gráfico)
    if len(prov_sel) > 1:
        _sel_prov = st.pills(
            "Proveedor activo",
            prov_sel,
            format_func=lambda p: _compras_truncar(p, 28),
            default=prov_focus,
            key="evo_prov_chips",
            label_visibility="collapsed",
        )
        if _sel_prov and _sel_prov != prov_focus:
            st.session_state["evo_prov_focus"] = _sel_prov
            st.session_state["evo_prov_prodfocus"] = None
            st.rerun()
    else:
        prov_focus = prov_sel[0]
        st.session_state["evo_prov_focus"] = prov_focus

    prov_focus = st.session_state.get("evo_prov_focus") or (prov_sel[0] if prov_sel else None)
    if not prov_focus:
        return

    # ── Panel de detalle del proveedor ────────────────────────────────────
    st.divider()
    sub_prov = base[base["prov"] == prov_focus]

    # Calcular KPIs del proveedor
    _total_prov    = float(sub_prov["valor"].sum())
    _pct_part      = _total_prov / _tot_all * 100
    _num_ordenes   = int(sub_prov.shape[0]) if not col_cant else int(
        pd.to_numeric(sub_prov["cant"], errors="coerce").count())
    _num_productos = int(sub_prov["prod"].nunique()) if col_prod else 0
    _ultima_fecha  = "—"
    if col_fecha:
        _uf = pd.to_datetime(sub_prov["fecha"], errors="coerce").dropna()
        if not _uf.empty:
            _ultima_fecha = _uf.max().strftime("%d/%m/%Y")

    # Rango para el número top (1 = mayor proveedor)
    _rank = next((i + 1 for i, p in enumerate(_todos_provs) if p == prov_focus), None)
    _rank_badge = f"Top {_rank}" if _rank and _rank <= 10 else ""

    col_det_izq, col_det_der = st.columns([1.1, 1])

    with col_det_izq:
        # Cabecera del proveedor
        st.markdown(
            f"**Detalle del proveedor seleccionado**\n\n"
            f"### {prov_focus}"
            + (f" &nbsp; <span style='background:#6c5ce7;color:#fff;"
               f"border-radius:999px;padding:2px 10px;font-size:12px;"
               f"font-weight:600'>{_rank_badge}</span>" if _rank_badge else ""),
            unsafe_allow_html=True,
        )

        # KPIs en fila
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Compras", f"S/ {_total_prov:,.0f}")
        k2.metric("% Participación", f"{_pct_part:.1f}%")
        k3.metric("Órdenes de compra", f"{_num_ordenes:,}")
        k4.metric("Productos", f"{_num_productos:,}")
        k5.metric("Última compra", _ultima_fecha)

        # Mini sparkline de evolución del proveedor (área)
        if col_fecha:
            _sp = sub_prov.copy()
            _sp["mes"] = pd.to_datetime(
                _sp["fecha"], errors="coerce").dt.to_period("M").astype(str)
            _sp_g = (_sp[_sp["mes"].notna() & (_sp["mes"] != "<NA>")]
                     .groupby("mes", as_index=False)["valor"].sum()
                     .sort_values("mes"))
            if len(_sp_g) >= 2:
                st.markdown("**Evolución de compras del proveedor**")
                fig_sp = go.Figure(go.Scatter(
                    x=_sp_g["mes"], y=_sp_g["valor"],
                    mode="lines+markers",
                    line=dict(color=ACENTO, width=2),
                    marker=dict(size=5),
                    fill="tozeroy",
                    fillcolor="rgba(108,92,231,0.10)",
                    hovertemplate="%{x}: S/ %{y:,.0f}<extra></extra>",
                ))
                _compras_layout(fig_sp, alto=180)
                fig_sp.update_layout(
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(type="category", tickangle=-30,
                               tickfont=dict(size=10)),
                    yaxis=dict(tickprefix="S/ ", tickformat=",.0f",
                               tickfont=dict(size=10)),
                    showlegend=False,
                )
                st.plotly_chart(fig_sp, use_container_width=True,
                                key="evo_prov_sparkline")

    with col_det_der:
        # Tabla top productos del proveedor
        if col_prod:
            st.markdown("**Top productos comprados a este proveedor**")
            _top_prod = (sub_prov.groupby("prod", as_index=False)["valor"]
                         .sum()
                         .sort_values("valor", ascending=False)
                         .head(8))
            _tot_prov = float(_top_prod["valor"].sum()) or 1.0

            # Construir tabla estilizada con % participación
            filas_prod = []
            for rk, row in enumerate(_top_prod.itertuples(), 1):
                _p_pct = row.valor / _tot_prov * 100
                filas_prod.append({
                    "#": rk,
                    "Producto": _compras_truncar(row.prod, 30),
                    "Total Compras (S/)": f"S/ {row.valor:,.0f}",
                    "% Participación": f"{_p_pct:.1f}%",
                    "_prod_raw": row.prod,
                })

            # Mostrar como dataframe con click para drill
            df_prod_tbl = pd.DataFrame(filas_prod)[
                ["#", "Producto", "Total Compras (S/)", "% Participación"]
            ]
            st.dataframe(
                df_prod_tbl,
                hide_index=True,
                use_container_width=True,
                height=min(320, 60 + 35 * len(df_prod_tbl)),
            )

            # Selector de producto para drill-down
            _prods_lista = [r["_prod_raw"] for r in filas_prod]
            _lbl_drill = "Haz clic en un producto para ver a qué otros proveedores se les compró"
            _prod_drill = st.selectbox(
                _lbl_drill,
                ["(ninguno)"] + _prods_lista,
                format_func=lambda p: "— selecciona un producto —" if p == "(ninguno)"
                            else _compras_truncar(p, 40),
                key="evo_prov_proddrill",
                label_visibility="visible",
            )
            if _prod_drill and _prod_drill != "(ninguno)":
                st.session_state["evo_prov_prodfocus"] = _prod_drill
            prod_focus = st.session_state.get("evo_prov_prodfocus")

    # ── Tabla "Otros proveedores que también vendieron X" ─────────────────
    if prod_focus and prod_focus != "(ninguno)" and col_prod:
        st.divider()
        st.markdown(
            f"**Otros proveedores que también vendieron: "
            f"<span style='color:#6c5ce7'>{_compras_truncar(prod_focus, 50)}</span>**",
            unsafe_allow_html=True,
        )
        sub_prod = base[base["prod"] == prod_focus].copy()
        _otros = (sub_prod.groupby("prov", as_index=False)["valor"]
                  .sum()
                  .sort_values("valor", ascending=False))
        _tot_prod = float(_otros["valor"].sum()) or 1.0

        if _otros.empty:
            st.info("Sin datos de otros proveedores para ese producto.")
        else:
            # Barras de progreso inline + valores
            _filas_otros = []
            for row in _otros.itertuples():
                _pct = row.valor / _tot_prod * 100
                _filas_otros.append({
                    "Proveedor": _compras_truncar(row.prov, 36),
                    "Total Compras (S/)": f"S/ {row.valor:,.0f}",
                    "% Participación": f"{_pct:.1f}%",
                    "_valor": row.valor,
                    "_pct": _pct,
                })

            # Mostrar con barras de progreso usando plotly horizontal
            fig_otros = go.Figure()
            for i, row in enumerate(reversed(_filas_otros)):
                fig_otros.add_bar(
                    x=[row["_valor"]],
                    y=[_compras_truncar(row["Proveedor"], 36)],
                    orientation="h",
                    marker_color=(ACENTO if row["Proveedor"]
                                  == _compras_truncar(prov_focus, 36) else "#a0aec0"),
                    text=[f"S/ {row['_valor']:,.0f}   {row['_pct']:.1f}%"],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="%{y}: S/ %{x:,.0f}<extra></extra>",
                )
            _compras_layout(fig_otros, alto=max(180, 38 * len(_filas_otros) + 60))
            fig_otros.update_layout(
                showlegend=False,
                barmode="overlay",
                xaxis=dict(visible=False),
                margin=dict(l=10, r=130, t=10, b=10),
            )
            st.plotly_chart(fig_otros, use_container_width=True,
                            key="evo_prov_otros_chart")

    # ── Consejo al pie ────────────────────────────────────────────────────
    st.info(
        "💡 **Consejo:** Utiliza los filtros superiores para analizar "
        "por familia, subfamilia o rango de fechas.",
        icon=None,
    )


def renderizar_graficos_compras(df_f, nombre_reporte, df_full=None):
    """Dashboard dedicado de Compras: 5 gráficos con pestañas + 5 mini-tops."""
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
                    _lbl = f"Familia · {_n}" if _n else "Familia"
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
                    _lbl = f"Subfamilia · {_n}" if _n else "Subfamilia"
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
                "Precio vs año pasado", "Cantidad vs año pasado",
                "Cantidad por producto",
                "Semanal", "Vs año anterior", "Personalizado", "Tabla"]

    # Pestañas de tipo de gráfico (Familia, Proveedor, ...). G/T se dibuja
    # en la franja superior (app.py, col_titulo) igual que el resto de reportes.
    with st.container(key="compras_tabs_row"):
        with st.container(key="graf_tipo_chips"):
            graf = st.pills(
                "Gráfico", opciones, default=opciones[0],
                key="compras_graf_tipo", label_visibility="collapsed",
            ) or opciones[0]

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
                _compras_layout(fig, alto=560)
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
                _compras_layout(fig, alto=560)
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
                    _compras_layout(fig, alto=500)
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
                    _compras_layout(fig, alto=500)
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
                _compras_layout(fig, alto=540)
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
