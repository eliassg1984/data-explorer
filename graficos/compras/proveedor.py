"""graficos.compras.proveedor - drill de Proveedor.

Barras verticales por periodo (una serie por proveedor). Clic en una barra
fija el foco y filtra los paneles A/B y la tabla de documentos de abajo.

Es el drill mas grande del dashboard. Incluye un bloque largo de CSS
inyectado con st.markdown para los controles flotantes sobre el grafico;
vive aca (y no en estilos/) porque esta scopeado a las keys de este drill.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, GRIS_BORDE, SERIE_PRINCIPAL
from graficos.base import PALETA_CALLAI, _card, _compras_layout, _compras_truncar
from graficos.compras._comun import _es_movil, _first_point
from graficos.compras._css_proveedor import CSS as CSS_PROVEEDOR
from graficos.compras._documentos_proveedor import tabla_documentos
from graficos.compras._etiquetas_proveedor import (
    abrev_nombre, etiqueta_serie, sufijo_granularidad,
)


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
    # Nombres sobre las barras: TRUE por defecto (filtro principal para el
    # usuario). El seed corre una vez por sesión — bumping el key del flag
    # resetea sesiones antiguas que hayan quedado con False.
    if not st.session_state.get("_cp_show_names_seed_v2"):
        st.session_state["cp_prov_show_names"] = True
        st.session_state["_cp_show_names_seed_v2"] = True

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
    if gran == "Día":
        base["_per_sort"] = fe_s.dt.strftime("%Y-%m-%d")
        base["per"] = fe_s.dt.strftime("%d %b")
        _mes_es = {'Jan':'Ene','Apr':'Abr','Aug':'Ago','Dec':'Dic'}
        for _en, _es in _mes_es.items():
            base["per"] = base["per"].str.replace(_en, _es)
    elif gran == "Semana":
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

    # ── Ventana de periodos (paginacion server-side) ──────────────────────
    # En vez de zoom client-side (rangeslider), la cantidad de agrupaciones
    # visibles se decide en Python y el desplazamiento vive en session_state.
    # Ventaja clave: clicar una barra dispara un rerun, pero la ventana NO se
    # pierde (el zoom del rangeslider si se perdia, porque era estado del
    # navegador y Streamlit remonta el componente en cada rerun).
    #
    # El tamano por defecto se adapta a la cantidad de series para que el
    # ancho de barra siga siendo legible: mas proveedores -> menos
    # agrupaciones a la vez. (~1200px de plot / 16px minimos por barra) /
    # n_series, acotado a 4..12. El usuario puede fijarlo a mano desde el
    # popover de navegacion (cp_prov_win_size; None = automatico).
    _otros_mask = ~base["prov"].isin(top_provs)
    _hay_otros = _otros_mask.any()
    _otros_seleccionado = "Otros" in prov_multisel
    _n_series = len(orden_provs) + (1 if (_hay_otros and _otros_seleccionado) else 0)
    _n_per = len(periodos)
    _ventana_auto = max(4, min(12, int(1200 / (16 * max(1, _n_series)))))
    _win_size_sel = st.session_state.get("cp_prov_win_size")   # None = auto
    _ventana = (_ventana_auto if _win_size_sel is None
                else min(int(_win_size_sel), _n_per))
    _ventana = max(1, min(_ventana, _n_per))
    _ini_max = max(0, _n_per - _ventana)
    # Al cambiar granularidad / rango / densidad, reanclar al tramo mas
    # reciente (lo habitual en series de tiempo: interesa lo ultimo).
    _win_sig = f"{gran}|{_n_per}|{_ventana}"
    if st.session_state.get("cp_prov_win_sig") != _win_sig:
        st.session_state["cp_prov_win_sig"] = _win_sig
        st.session_state["cp_prov_win_ini"] = _ini_max
    # Clamp de bounds justo antes de usarlo (el rango pudo cambiar de tamano).
    _win_ini = min(max(0, st.session_state.get("cp_prov_win_ini", _ini_max)),
                   _ini_max)
    st.session_state["cp_prov_win_ini"] = _win_ini
    _per_vis = periodos[_win_ini:_win_ini + _ventana]
    _sl = slice(_win_ini, _win_ini + _ventana)

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
            # El indice es relativo a las barras DIBUJADAS (ventana visible).
            _pi = _mp.get("point_index", _mp.get("point_number"))
            if _pi is not None and 0 <= _pi < len(_per_vis):
                _per_click = _per_vis[_pi]
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

    _gran_suffix = sufijo_granularidad(gran)

    # Ancho útil del plot según el dispositivo (User-Agent): móvil ~345px,
    # descontando el espacio entre barras queda ~245 útil; desktop ~700. De ahí
    # sale el ancho estimado por barra, que gobierna DOS decisiones que Plotly
    # dibuja en el servidor (y no puede adaptar al ancho real): cuánto abreviar
    # el nombre y cuándo compactar la etiqueta. Así móvil abrevia/compacta y
    # desktop conserva nombres y etiquetas completas.
    _plot_util_px = 245 if _es_movil() else 700
    _ancho_barra_lbl = _plot_util_px / max(1, len(_per_vis) * _n_series)

    # Etiqueta compacta (recorta docs + % del período, deja valor + variación)
    # en dos casos:
    #  · Hay un proveedor en foco → el chart baja a 180px y la etiqueta de 4
    #    líneas se come casi todo el aire de las barras.
    #  · Las barras son ANGOSTAS → una etiqueta de 4 líneas no cabe sobre una
    #    barra de ~50px y plotly la recorta, dejando solo el valor ("incompleta").
    #    Bajo ~78px de ancho estimado se activa el modo compacto. En desktop las
    #    barras son anchas, así que casi nunca se activa por ancho.
    # En ambos casos docs y % siguen en el hover, que ya los trae.
    _lab_compacta = (prov_focus is not None) or (_ancho_barra_lbl < 78)

    # Nota: la serie se calcula sobre TODOS los periodos y recien despues se
    # recorta a la ventana visible (_sl). Asi la variacion % de la primera
    # barra visible sigue comparando contra su periodo anterior real, aunque
    # ese periodo quede fuera de la ventana.
    #
    # Toggle "Nombres en barras": prepende el nombre abreviado del proveedor
    # a la etiqueta de cada barra. El ancho de barra estimado depende de la
    # ventana visible y de la cantidad de series → recalculado en cada render.
    _show_names = st.session_state.get("cp_prov_show_names", True)
    # Cuánto abreviar el nombre según el ancho estimado por barra (ya calculado
    # arriba con el ancho de plot según dispositivo). Móvil (~245 útil) abrevia
    # a la primera palabra cuando hay 3+ series; desktop (~700) conserva el
    # nombre largo salvo que las barras sean muy angostas. La leyenda y el hover
    # siempre traen el nombre completo.
    _ancho_barra_est_px = _ancho_barra_lbl
    _max_chars = max(0, int(_ancho_barra_est_px / 6.5))  # ~6.5px por char a 11px
    # Totales por período (sobre TODA la base filtrada, no solo los provs
    # seleccionados) para el % de participación en cada barra.
    _tot_por_periodo = (base.groupby("per")["valor"].sum()
                        .reindex(periodos, fill_value=0))
    # Cantidad de documentos unicos por (prov, per). Solo si la columna docu
    # existe y no esta vacia; si no, dejamos None y la etiqueta lo omite.
    if "docu" in base.columns and (base["docu"].astype(str) != "").any():
        _docs_por = (base.groupby(["prov", "per"])["docu"]
                     .nunique().rename("n_docs"))
    else:
        _docs_por = None
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

        # % que esta barra representa del total del período (0-100). Si el
        # total del periodo es 0, deja None (etiqueta_serie lo ignora).
        _pct_per = [(g / t * 100) if t > 0 else None
                    for g, t in zip(grp.values, _tot_por_periodo.values)]
        # Docs por bar (alineado con periodos): si el (prov, per) no aparece
        # en el groupby -> reindex con fill_value=0 -> etiqueta lo omite.
        if _docs_por is not None and prov in _docs_por.index.get_level_values(0):
            _docs_prov = (_docs_por.loc[prov]
                          .reindex(periodos, fill_value=0).astype(int))
            _docs_lst = list(_docs_prov.values)
        else:
            _docs_lst = None
        _tags = etiqueta_serie(list(grp.values), _gran_suffix,
                               compacta=_lab_compacta,
                               pct_periodo=_pct_per,
                               docs=_docs_lst)[_sl]
        if _show_names:
            _abbr = abrev_nombre(prov, _max_chars)
            if _abbr:
                _prefix = (f"<b><span style='color:{_color};font-size:10px'>"
                           f"{_abbr}</span></b><br>")
                _tags = [(_prefix + t) if t else "" for t in _tags]

        # customdata por barra: [prov, pct_total_prov, docs_barra, pct_periodo_barra]
        # para que el tooltip repita la misma info que el rótulo sobre la barra.
        _docs_lst_vis = list(_docs_lst)[_sl] if _docs_lst else [None] * len(_per_vis)
        _pct_per_vis = list(_pct_per)[_sl] if _pct_per else [None] * len(_per_vis)
        _cd = [
            [prov, _pct,
             int(_d) if _d and not pd.isna(_d) else 0,
             float(_p) if _p is not None and not pd.isna(_p) else 0.0]
            for _d, _p in zip(_docs_lst_vis, _pct_per_vis)
        ]
        fig.add_bar(
            x=_per_vis,
            y=grp.values[_sl],
            name=_compras_truncar(prov, 22),
            marker=dict(color=_color, opacity=_opacity),
            text=_tags,
            textposition="outside",
            textfont=dict(size=13),
            cliponaxis=False,
            customdata=_cd,
            hovertemplate=(
                "<b>%{customdata[0]}</b>  %{x}<br>"
                "S/ %{y:,.0f} · %{customdata[1]:.1f}%<br>"
                "%{customdata[2]} docs · %{customdata[3]:.0f}% "
                + _gran_suffix +
                "<extra></extra>"
            ),
        )

    # "Otros" proveedores agrupados (gris) — solo si el usuario lo pidió
    if _hay_otros and _otros_seleccionado:
        grp_otros = (base[_otros_mask]
                     .groupby("per", as_index=False)["valor"].sum()
                     .set_index("per")["valor"]
                     .reindex(periodos, fill_value=0))
        _tags_o = etiqueta_serie(list(grp_otros.values), _gran_suffix,
                                 compacta=_lab_compacta)[_sl]
        if _show_names and _max_chars >= 2:
            _prefix_o = ("<b><span style='color:#7a7a86;font-size:10px'>"
                         "Otros</span></b><br>")
            _tags_o = [(_prefix_o + t) if t else "" for t in _tags_o]
        fig.add_bar(
            x=_per_vis,
            y=grp_otros.values[_sl],
            name="Otros",
            marker=dict(color=GRIS_BORDE, opacity=0.6),
            text=_tags_o,
            textposition="outside",
            textfont=dict(size=13),
            cliponaxis=False,
            hovertemplate="Otros · %{x}<br>S/ %{y:,.0f}<extra></extra>",
        )

    # Alto del chart principal: se encoge cuando hay un proveedor en foco para
    # dar aire al detalle de abajo. El figure se dibuja YA al alto final; la
    # transicion la hace el wrapper (ver _anim_css mas abajo).
    #
    # El foco manda las dos cosas a la vez: abre el detalle A/B y encoge el
    # chart. Cerrar con la X limpia el foco -> el detalle se va y el chart
    # vuelve a 360 en el mismo rerun.
    #
    # 180 en foco: cabe porque la etiqueta se recorta a 2 lineas en ese estado
    # (ver _lab_compacta). Con las 4 lineas del estado normal no entraria.
    _alto_chart = 180 if prov_focus is not None else 360
    _compras_layout(fig, alto=_alto_chart)
    fig.update_layout(

        barmode="group",
        # Margen superior mínimo: el gráfico sube dentro de la tarjeta y elimina
        # la franja vacía sobre las barras (los flotantes Proveedores/Periodo se
        # superponen encima; van con fondo semitransparente y no molestan).
        margin=dict(l=10, r=10, t=6, b=36),
        xaxis=dict(type="category", tickangle=0),
        # Eje Y sin etiquetas de valor (S/ 4,000, S/ 3,500…): cada barra ya
        # lleva su monto encima, así que la escala numérica era redundante.
        # Se conserva la grilla como referencia visual de altura, pero sin
        # números. Ademas libera el margen izquierdo → las barras ganan ancho.
        yaxis=dict(showticklabels=False),
        # Leyenda VERTICAL flotando DENTRO del área (x<=1 → Plotly no reserva
        # margen → no encoge el gráfico). Fondo semitransparente para leerse
        # sobre las barras. Arranca en y=0.82 para no pisar el toggle superior.
        legend=dict(orientation="v", yanchor="top", y=0.82,
                    xanchor="right", x=0.99, font=dict(size=10),
                    bgcolor="rgba(255,255,255,0.78)",
                    bordercolor="rgba(0,0,0,0.12)", borderwidth=1),
        hovermode="closest",
        # uirevision estable: evita que Plotly reinicie estado de UI propio
        # (p. ej. leyenda arrastrada) en cada rerun por clic.
        uirevision=_chart_key,
    )

    # Sin rangeslider: la navegacion es server-side (ventana + flechas), asi
    # sobrevive al clic en una barra. Eso ademas libera el alto que ocupaba el
    # slider, que ahora queda para las barras.

    # ── Selector de granularidad FLOTANTE sobre el gráfico ────────────────
    # El contenedor "compras_prov_card_chart" es posición relativa; dentro,
    # las pills se posicionan en absoluto arriba-derecha, superpuestas al gráfico.
    st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)

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
            # Numero como badge: se inyecta via CSS var (::after lo pinta).
            # Sin cuenta → badge vacio. La CSS var vive scoped al contenedor.
            st.markdown(
                f"<style>.st-key-prov_pop_float "
                f"{{ --cp-prov-count: '{len(_sel_now)}'; }}</style>",
                unsafe_allow_html=True,
            )
            with st.popover("Proveedores", icon=":material/groups:"):
                _bt = st.columns(5)
                _bt[0].button("Top 3", key="cp_topn3", use_container_width=True,
                              on_click=_cp_set_topn, args=(3,))
                _bt[1].button("Top 5", key="cp_topn5", use_container_width=True,
                              on_click=_cp_set_topn, args=(5,))
                _bt[2].button("Top 10", key="cp_topn10", use_container_width=True,
                              on_click=_cp_set_topn, args=(10,))
                _bt[3].button("Todos", key="cp_topnall", use_container_width=True,
                              on_click=_cp_set_topn, args=(len(_real_provs),))
                _bt[4].button("Limpiar", key="cp_topnclr", use_container_width=True,
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
                st.divider()
                st.toggle("Nombres en barras", key="cp_prov_show_names",
                          help="Muestra el nombre del proveedor "
                          "sobre cada barra. Se abrevia segun el ancho "
                          "disponible.")
        with st.container(key="gran_float"):
            st.pills("Periodo", ["Día", "Semana", "Mes", "Año"], default="Mes",
                     key="compras_prov_gran", label_visibility="collapsed")
        # -- Transicion del alto del chart (360 <-> 220) ---------------------
        # Plotly reescribe el SVG con el alto nuevo de golpe: entre 360 y 220 no
        # hay estado intermedio que el navegador pueda interpolar, y `transition`
        # no sirve (el alto lo escribe plotly.js inline en px, y el wrapper esta
        # en height:auto, que no es animable). Lo que SI se anima es el hueco:
        # el figure se dibuja ya al alto final y el wrapper colapsa de un alto al
        # otro con @keyframes (declara ambos extremos, no necesita valor previo).
        # El ojo lee "el chart se encogio y el detalle subio".
        #
        # Dos condiciones para que funcione:
        #  1) nombre de animacion UNICO por transicion. El key de plotly es
        #     estable (ver arriba), asi que el nodo no se remonta; reaplicar el
        #     mismo animation-name a un nodo vivo no reinicia nada.
        #  2) emitir el CSS SOLO en el rerun donde el alto cambio. Si no, cada
        #     clic en un producto del Panel A repetiria el encogido.
        # Sin `forwards`: al terminar, el wrapper vuelve a su alto natural, que
        # ya es el final. overflow:hidden solo hace falta al CRECER (el chart
        # grande desbordaria); al encoger el wrapper solo sobra aire, y evitarlo
        # deja los tooltips de plotly sin recortar.
        # El st.markdown se emite SIEMPRE (con <style> vacio si no toca animar):
        # un elemento condicional cambiaria la cuenta de hijos del bloque y el
        # gap de 1rem haria saltar la tarjeta 16px al enfocar/desenfocar.
        _alto_prev = st.session_state.get("cp_chart_alto_prev", _alto_chart)
        _anim_css = ""
        if _alto_prev != _alto_chart:
            st.session_state["cp_chart_anim_n"] = (
                st.session_state.get("cp_chart_anim_n", 0) + 1)
            _an = st.session_state["cp_chart_anim_n"]
            _ovf = ("overflow:hidden;" if _alto_chart > _alto_prev else "")
            _anim_css = (
                f"@keyframes cpChartH{_an}{{"
                f"from{{height:{_alto_prev}px;}}to{{height:{_alto_chart}px;}}}}"
                f".st-key-cp_chart_wrap{{{_ovf}"
                f"animation:cpChartH{_an} .35s cubic-bezier(.2,.7,.2,1);}}")
        st.markdown(f"<style>{_anim_css}</style>", unsafe_allow_html=True)
        st.session_state["cp_chart_alto_prev"] = _alto_chart

        # Config del chart. En DESKTOP el modebar va oculto (vista BI limpia).
        # En MÓVIL se activa el modebar pero SOLO para conservar el botón de
        # pantalla completa (⛶) que Streamlit inyecta en él: se quitan todos los
        # botones estándar de Plotly (zoom/pan/lasso/descarga…) y queda el ⛶.
        # Tocándolo el gráfico llena la pantalla; girando el teléfono a
        # horizontal las etiquetas caben holgadas y el hover trae el detalle.
        # displaylogo off para no meter el logo de Plotly.
        _cfg_chart = {"edits": {"legendPosition": True}, "displaylogo": False}
        if _es_movil():
            _cfg_chart["displayModeBar"] = True
            _cfg_chart["modeBarButtonsToRemove"] = [
                "zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d",
                "zoomOut2d", "autoScale2d", "resetScale2d", "toImage",
            ]
        else:
            _cfg_chart["displayModeBar"] = False

        # Chart siempre responsive al contenedor (estándar BI). La densidad se
        # controla con la ventana de periodos (server-side) + flechas de
        # navegación — nunca scroll horizontal externo ni zoom client-side.
        with st.container(key="cp_chart_wrap"):
            st.plotly_chart(
                fig,
                use_container_width=True,
                key=_chart_key,
                on_select="rerun",
                selection_mode="points",
                # edits.legendPosition: permite ARRASTRAR la leyenda con el cursor.
                # Ojo: la posición no persiste (al reejecutar vuelve a y=0.82).
                config=_cfg_chart,
            )
        # Navegacion de la ventana de periodos. El indice y el tamano viven en
        # session_state, asi que clicar una barra NO los mueve. El popover
        # central muestra cuantas agrupaciones se ven y permite cambiarlo.
        def _win_mover(_delta):
            st.session_state["cp_prov_win_ini"] = min(
                max(0, _win_ini + _delta), _ini_max)

        def _win_size(_n):
            st.session_state["cp_prov_win_size"] = _n     # None = automatico

        with st.container(key="win_nav"):
            st.button("‹", key="cp_win_prev", disabled=_win_ini <= 0,
                      help="Periodos anteriores",
                      on_click=_win_mover, args=(-_ventana,))
            # Pills de tamano inline (sin popover). El pill activo se marca
            # via <style> inyectado con la key exacta (no se puede aplicar
            # la clase :active desde Python porque Streamlit re-renderiza).
            _sel_key = ("cp_win_auto" if _win_size_sel is None
                        else "cp_win_all" if _win_size_sel == _n_per
                        else f"cp_win_{int(_win_size_sel)}")
            st.markdown(
                f"<style>.st-key-{_sel_key} button{{"
                f"background:#6c5ce7 !important;color:#fff !important;"
                f"border-color:#6c5ce7 !important;"
                f"box-shadow:0 2px 5px rgba(76,60,180,0.28),"
                f"inset 0 1px 0 rgba(255,255,255,0.18) !important;}}</style>",
                unsafe_allow_html=True)
            st.button(f"Auto {_ventana_auto}", key="cp_win_auto",
                      on_click=_win_size, args=(None,))
            for _op in (1, 2, 3, 6, 12, 24):
                if _op < _n_per:
                    st.button(str(_op), key=f"cp_win_{_op}",
                              on_click=_win_size, args=(_op,))
            st.button(f"Todo {_n_per}", key="cp_win_all",
                      on_click=_win_size, args=(_n_per,))
            st.button("›", key="cp_win_next", disabled=_win_ini >= _ini_max,
                      help="Periodos siguientes",
                      on_click=_win_mover, args=(_ventana,))

    # ── Paneles A y B ─────────────────────────────────────────────────────
    def _um_de(grp):
        if not col_um:
            return ""
        m = grp["um"].mode()
        return (" " + m.iat[0]) if len(m) and m.iat[0] not in ("", "nan") else ""

    def _base_prov_de(_src):
        """Base mínima (prov/prod/valor/punit/cant/um/fecha) para el Panel B,
        a partir de cualquier df origen (`d` filtrado por fecha o `d_full` con
        todo el histórico). `valor` es necesario para el total de la tarjeta."""
        _b = pd.DataFrame({
            "prov":  _src[col_prov].astype(str).values,
            "prod":  (_src[col_prod].astype(str).values if col_prod else "—"),
            "cant":  (pd.to_numeric(_src[col_cant], errors="coerce").fillna(0).values
                      if col_cant else 0.0),
            "valor": pd.to_numeric(_src[col_valor], errors="coerce").fillna(0).values,
            "punit": (pd.to_numeric(_src[col_punit], errors="coerce").values
                      if col_punit else np.nan),
            "um":    (_src[col_um].astype(str).values if col_um else ""),
            "fecha": (pd.to_datetime(_src[col_fecha], errors="coerce").values
                      if col_fecha else pd.NaT),
        })
        return _b[_b["prov"].notna() & (_b["prov"] != "nan")]

    # -- Bloque 2: el detalle A/B lo manda el FOCO, no un pestillo. Clic en una
    #    barra lo abre; la X (gutter izquierdo) limpia el foco y lo cierra. La
    #    tarjeta vive en una funcion local para NO re-indentar su cuerpo; se
    #    llama abajo solo si hay proveedor en foco.
    def _paneles_card():
        with st.container(border=True, key="compras_prov_card_paneles"):
            pa, pb = st.columns(2)

            # Panel A: Top N productos del proveedor en foco
            with pa:
                _ta = ("Selecciona un proveedor arriba para ver sus productos"
                       if prov_focus is None
                       else f"Productos · {_compras_truncar(prov_focus, 24)}")
                with _card("prov_prods", _ta, titulo_arriba=True):
                    # Controles flotantes en la cabecera (Opción 1). Dos flotantes
                    # absolutos apilados a la derecha: un texto chico con la
                    # selección (período) clicada ARRIBA y, justo debajo, Ámbito +
                    # Top N en una fila. Flotantes → no empujan el gráfico. El
                    # ámbito arranca en "periodo" (el período de la barra clicada).
                    _perf = st.session_state.get("compras_prov_perfocus")
                    if _perf is not None:
                        st.markdown(
                            f'<style>.st-key-topn_pills {{ '
                            f'--periodo-selec: "{_perf}"; }}</style>',
                            unsafe_allow_html=True)
                    with st.container(key="topn_float"):
                        with st.container(key="topn_pills"):
                            _scope = st.pills(
                                "Ámbito de período", ["rango", "periodo"],
                                default="periodo",
                                format_func=lambda v: ("Rango"
                                                       if v == "rango" else "Selección"),
                                key="compras_prov_prod_scope",
                                label_visibility="collapsed",
                            ) or "periodo"
                            st.pills("Top productos", [5, 10, 20], default=10,
                                     key="compras_prov_topn",
                                     label_visibility="collapsed")
                    if prov_focus is None:
                        pass
                    else:
                        sub = base[base["prov"] == prov_focus]
                        if _scope == "periodo" and _perf is not None:
                            sub = sub[sub["per"] == _perf]
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
                            # 30px por fila -> 22px: menos aire vertical entre
                            # barras, sin tocar el grosor. La lista se compacta
                            # (con Top 20 el chart baja de ~640 a ~480px).
                            _compras_layout(figa, alto=max(180, 22 * len(agg) + 40))
                            # _compras_layout enciende la grilla del eje Y, que
                            # es lo correcto en barras VERTICALES (lineas de
                            # referencia detras de las barras). Aqui las barras
                            # son horizontales: el eje Y es el categorico, asi
                            # que esa grilla dibuja una raya por producto que
                            # cruza el rotulo. Se apaga.
                            figa.update_yaxes(showgrid=False)
                            # Eje X oculto: cada barra ya lleva su valor como
                            # texto (S/ ... · ... KG), asi que la escala de
                            # ticks (S/ 0, S/ 20,000...) era redundante y solo
                            # sumaba ruido al pie del panel.
                            figa.update_xaxes(visible=False)
                            # bargap = aire entre filas, como fraccion del alto
                            # de fila (22px). 0.35 -> barra de ~14px, mismo
                            # grosor que antes pero con menos aire arriba/abajo.
                            figa.update_layout(margin=dict(l=10, r=140, t=2, b=10),
                                               bargap=0.35)
                            _aevt = st.plotly_chart(
                                figa, use_container_width=True,
                                key=f"compras_g_prov_prods_{prov_focus}_{prod_focus}_{_pan_inst}",
                                on_select="rerun", selection_mode="points",
                                config={"displayModeBar": False},
                            )
                            _ap = _first_point(_aevt)
                            if _ap is not None:
                                _j = _ap.get("point_number", _ap.get("point_index"))
                                if _j is not None and 0 <= _j < len(prod_cats):
                                    st.session_state["compras_prov_prodfocus"] = prod_cats[_j]
                                    st.rerun(scope="fragment")


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
                        # Color por proveedor: los del top toman su color de la
                        # paleta (el mismo que en el chart principal); los que
                        # no estan en top -> gris. Asi el swatch de la tarjeta
                        # matchea con la barra de arriba.
                        _color_map = {p: PALETA_CALLAI[i % len(PALETA_CALLAI)]
                                      for i, p in enumerate(top_provs)}
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
                                "prov":  prov,
                                "color": _color_map.get(prov, GRIS_BORDE),
                                "total": float(grp["valor"].sum()),
                                "ult_p": ult,
                                "ult_f": (_uf.strftime("%d/%m/%Y")
                                          if _uf is not None else None),
                                "cant":  float(grp["cant"].sum()),
                                "um":    (_um_de(grp).strip() if col_um else ""),
                            })
                        # Orden por total desc — la tarjeta principal arriba,
                        # igual que el mockup (VIBEJ / LEON / LA CESTA...).
                        filas.sort(key=lambda r: r["total"], reverse=True)
                        _precios = [r["ult_p"] for r in filas
                                    if pd.notna(r["ult_p"])]
                        _min = min(_precios) if _precios else None

                        def _esc(s):
                            return (str(s).replace("&", "&amp;")
                                    .replace("<", "&lt;").replace(">", "&gt;"))

                        def _fmt_soles(v):
                            if v is None or pd.isna(v):
                                return "—"
                            if v >= 1000:
                                return f"S/ {v/1000:.1f}k"
                            return f"S/ {v:,.0f}"

                        _cards = []
                        for r in filas:
                            _es_min = (_min is not None and pd.notna(r["ult_p"])
                                       and r["ult_p"] == _min)
                            _pu_txt = ("—" if pd.isna(r["ult_p"])
                                       else f"S/ {r['ult_p']:,.2f}")
                            _pu_cls = " pu-min" if _es_min else ""
                            _cells = [
                                ("Últ.",  r["ult_f"] or "—"),
                                ("P.U.",  f'<span class="pu{_pu_cls}">{_pu_txt}</span>'),
                                ("Cant.", f"{r['cant']:,.0f}"),
                            ]
                            if col_um and r["um"]:
                                _cells.append(("UM", _esc(r["um"])))
                            _grid = "".join(
                                f'<div class="cell"><span class="lab">{lab}</span>'
                                f'<span class="val">{val}</span></div>'
                                for lab, val in _cells
                            )
                            _cards.append(
                                f'<div class="pb-card{"  is-min" if _es_min else ""}">'
                                f'<div class="line1">'
                                f'<span class="sw" style="background:{r["color"]}"></span>'
                                f'<span class="name" title="{_esc(r["prov"])}">'
                                f'{_esc(r["prov"])}</span>'
                                f'<span class="total">{_fmt_soles(r["total"])}</span>'
                                f'</div>'
                                f'<div class="grid">{_grid}</div>'
                                f'</div>'
                            )
                        st.markdown(
                            '<div class="pb-cards">' + "".join(_cards) + '</div>',
                            unsafe_allow_html=True,
                        )
                        if _min is not None:
                            st.caption("Último precio = precio unitario de la compra "
                                       "más reciente. Verde = menor precio.")

    # -- Visibilidad del detalle A/B = hay proveedor en foco. Sin pestillo y sin
    #    boton de cerrar: la barra lo abre y esa misma barra lo cierra (el
    #    toggle vive en el procesado de clic, arriba).
    _pan_ab = prov_focus is not None
    # Instance id: se incrementa cada vez que el bloque pasa de cerrado a
    # abierto. Se anade al key de los componentes hijos (plotly / aggrid /
    # dataframe) para forzar REMOUNT limpio al reabrir. Sin esto, Streamlit
    # reusa los nodos DOM y los componentes internos no se re-miden el
    # ancho del contenedor -> chart vacio, tabla con columnas colapsadas.
    if _pan_ab and not st.session_state.get("cp_paneles_prev_ab", False):
        st.session_state["cp_paneles_inst"] = (
            st.session_state.get("cp_paneles_inst", 0) + 1)
    st.session_state["cp_paneles_prev_ab"] = _pan_ab
    _pan_inst = st.session_state.get("cp_paneles_inst", 0)

    # (El CSS del pegado al chart vive en el <style> estatico de arriba.
    #  Inyectarlo aqui con un st.markdown propio metia un stElementContainer
    #  vacio justo entre las dos tarjetas: alto 0, pero el gap de 1rem del
    #  bloque vertical igual se aplicaba -> ~16px de aire.)
    with st.container(key="paneles_row"):
        if _pan_ab:
            _paneles_card()

    # ── Tabla pivotable de documentos (debajo de los paneles A/B) ─────────
    # Vive en su propio modulo desde 2026-08-08: es la pieza del drill con
    # menos acoplamiento hacia atras (solo estos 6 valores) y su estado de
    # abierto/cerrado no lo lee nadie mas. Ver _documentos_proveedor.py.
    tabla_documentos(base, top_provs, gran, periodos, col_docu, col_punit)
