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

    def _fmt_k(v):
        """Monto compacto para etiquetas angostas: S/ 4.0k, S/ 1.2M."""
        if v >= 1_000_000:
            return f"S/ {v / 1_000_000:.1f}M"
        if v >= 1_000:
            return f"S/ {v / 1_000:.1f}k"
        return f"S/ {v:.0f}"

    # Sufijo para la línea '% del ...' según la granularidad activa. El
    # usuario ve el nombre del segmento directamente, sin genérico 'período'.
    _gran_suffix = {"Día": "del Día", "Semana": "de la Semana",
                    "Mes": "del Mes", "Año": "del Año"}.get(gran, "del período")

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

    def _etiqueta_serie(vals, pct_periodo=None, docs=None):
        """Texto por barra: total SIEMPRE encima + variación vs el período
        ANTERIOR del mismo proveedor (▲ verde sube / ▼ rojo baja) + cantidad
        de documentos + % de participación en el período. La 1ª barra no
        tiene anterior → solo total + docs + %. Barras en 0 → sin etiqueta.

        Con `_lab_compacta` (hay proveedor en foco) se omiten las dos líneas
        grises del pie: el chart está a 180px y no hay alto para ellas.

        pct_periodo: lista del mismo largo que vals con el % que la barra
            representa del total del segmento (0-100). Si None, se omite.
        docs: lista del mismo largo que vals con la cantidad de documentos
            (facturas / comprobantes únicos) que respaldan cada barra. Si
            None, se omite.
        """
        if _lab_compacta:
            docs, pct_periodo = None, None
        _txt = []
        for j, v in enumerate(vals):
            if v <= 0:
                _txt.append("")
                continue
            linea = _fmt_k(v)
            if j > 0 and vals[j - 1] > 0:
                chg = (v - vals[j - 1]) / vals[j - 1] * 100
                flecha = "▲" if chg >= 0 else "▼"
                col = "#0F6E56" if chg >= 0 else "#A32D2D"
                linea += (f"<br><span style='color:{col}'>"
                          f"{flecha}{abs(chg):.0f}%</span>")
            # Tercera linea (gris chico): docs + % del segmento.
            _foot = []
            if docs is not None:
                _n = docs[j]
                if _n is not None and not pd.isna(_n) and _n > 0:
                    _n = int(_n)
                    _foot.append(f"{_n} doc" if _n == 1 else f"{_n} docs")
            if pct_periodo is not None:
                _pp = pct_periodo[j]
                if _pp is not None and not pd.isna(_pp):
                    _foot.append(f"{_pp:.0f}% {_gran_suffix}")
            if _foot:
                linea += "".join(
                    f"<br><span style='color:#6b6b78;font-size:11.5px'>{_p}</span>"
                    for _p in _foot
                )
            _txt.append(linea)
        return _txt

    def _abrev_nombre(nombre, max_chars):
        """Abrevia el nombre del proveedor segun ancho disponible.
        - max<2: vacio (bar muy chica)
        - 2:      2 primeras iniciales de palabras
        - 3-5:    iniciales de todas las palabras significativas
        - 6-14:   primera palabra
        - >=15:   nombre completo (truncado con … si excede)
        """
        s = str(nombre).strip()
        if max_chars < 2 or not s:
            return ""
        if len(s) <= max_chars:
            return s
        words = [w for w in s.split() if w and w.lower() not in
                 ("de", "del", "la", "el", "los", "las", "y", "e", "s.a.c.",
                  "sac", "s.a.", "sa", "e.i.r.l.", "eirl")]
        if max_chars <= 5:
            ini = "".join(w[0].upper() for w in words[:max_chars])
            return ini[:max_chars] if len(ini) >= 2 else s[:max_chars]
        if max_chars <= 14 and words:
            first = words[0]
            return first if len(first) <= max_chars else first[:max_chars - 1] + "…"
        return s[:max_chars - 1] + "…"

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
        _tags = _etiqueta_serie(list(grp.values),
                                pct_periodo=_pct_per,
                                docs=_docs_lst)[_sl]
        if _show_names:
            _abbr = _abrev_nombre(prov, _max_chars)
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
        _tags_o = _etiqueta_serie(list(grp_otros.values))[_sl]
        if _show_names and _max_chars >= 2:
            _prefix_o = (f"<b><span style='color:#7a7a86;font-size:10px'>"
                         f"Otros</span></b><br>")
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
    st.markdown("""
        <style>
        .st-key-compras_prov_card_chart { position: relative; }
        /* La leyenda se movió a la derecha (vertical); la banda superior solo
           tiene popover (izq) + toggle (der), alineados arriba. */
        .st-key-gran_float {
            position: absolute; top: 14px; right: 16px; z-index: 5;
            width: auto !important;
            /* Aplanar todo lo que Streamlit mete arriba del ButtonGroup
               (label oculto, padding del stElementContainer). Sin esto el
               grupo de pills queda ~14px más abajo que la fila de proveedores. */
            padding: 0 !important; margin: 0 !important;
            line-height: 0 !important;
        }
        .st-key-gran_float [data-testid="stElementContainer"],
        .st-key-gran_float [data-testid="stElementContainer"] > div,
        .st-key-gran_float [data-testid="stVerticalBlock"] {
            padding: 0 !important; margin: 0 !important; gap: 0 !important;
        }
        /* Contenedor de las pills Día/Semana/Mes/Año: solo más delgado,
           sin tocar la fuente ni la ubicación originales. */
        .st-key-gran_float [data-testid="stButtonGroup"] {
            margin: 0 !important; padding: 0 !important;
        }
        .st-key-gran_float [data-testid="stButtonGroup"] button {
            min-height: 0 !important;
            height: auto !important;
            padding-top: 1px !important;
            padding-bottom: 1px !important;
            line-height: 1.3 !important;
        }
        /* Popover de proveedores flotando arriba-IZQUIERDA (compacto) */
        .st-key-prov_pop_float {
            position: absolute; top: 14px; left: 16px; z-index: 5;
            width: auto !important;
        }
        /* Variante "outline en tinte" (violeta claro con borde y texto oscuros).
           Contraste bajo: fondo casi blanco con leve tinte, borde tenue. */
        .st-key-prov_pop_float [data-testid="stPopover"] button {
            min-width: 0 !important;
            min-height: 0 !important;
            padding: 2px 10px !important;    /* contenedor un poco más delgado */
            font-size: 11px !important;      /* fuente igual que antes */
            font-weight: 500 !important;
            line-height: 1.35 !important;
            border-radius: 4px !important;   /* cuadrado, no cápsula */
            background: #F7F6FE !important;
            color: #534AB7 !important;
            border: 1px solid #E4E1F5 !important;
            box-shadow: none !important;
            transition: background .12s, border-color .12s !important;
        }
        .st-key-prov_pop_float [data-testid="stPopover"] button:hover {
            background: #DED9FA !important;
            border-color: #7F77DD !important;
        }
        .st-key-prov_pop_float [data-testid="stPopover"] button[aria-expanded="true"] {
            background: #DED9FA !important;
            border-color: #534AB7 !important;
        }
        /* Icono material (grupos) del popover: color acento */
        .st-key-prov_pop_float [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
            color: #7F77DD !important;
            font-size: 14px !important;
            margin-right: 4px !important;
        }
        /* Badge con el numero de proveedores: se inyecta el valor via
           ::after con content dinamico desde Python (ver _cp_badge_count) */
        .st-key-prov_pop_float [data-testid="stPopover"] button
            [data-testid="stMarkdownContainer"] p::after {
            content: var(--cp-prov-count, "");
            background: #534AB7;
            color: #EEEDFE;
            border-radius: 3px;
            padding: 1px 8px;
            font-size: 11px;
            font-weight: 500;
            margin-left: 8px;
            line-height: 1.4;
        }
        .st-key-gran_float [data-testid="stElementToolbar"] { display: none; }
        /* Ocultar la barra de herramientas del propio gráfico (fullscreen).
           Sin `> div >`: el chart vive dentro de cp_chart_wrap (un nivel más
           abajo) y el selector directo dejaba de matchear. */
        .st-key-compras_prov_card_chart [data-testid="stElementToolbar"] { display: none; }
        /* Wrapper del chart: solo existe para animar el alto (ver más abajo).
           Aplanado para no meter aire extra dentro de la tarjeta. */
        .st-key-cp_chart_wrap {
            padding: 0 !important; margin: 0 !important; gap: 0 !important;
        }

        /* Leyenda del gráfico Plotly: totalmente transparente en reposo. Solo
           se hace opaca cuando el cursor pasa DIRECTO sobre la leyenda (no
           al hover de toda la tarjeta). Sigue interactuable porque opacity:0
           conserva pointer-events. */
        .st-key-compras_prov_card_chart .js-plotly-plot .legend {
            opacity: 0.1 !important;
            transition: opacity .22s ease-in-out !important;
        }
        .st-key-compras_prov_card_chart .js-plotly-plot .legend:hover {
            opacity: 1 !important;
        }

        /* Navegacion de ventana: flechas ‹ › + pills de tamano en la misma
           fila, abajo-derecha, flotando (no suman alto a la tarjeta). El
           key de un container SIN borde ES el stVerticalBlock, por eso la
           direccion FILA se fija aqui directo. Los controles tienen sombra
           leve para leerse como "chips apoyados" sobre el grafico, no como
           pills sueltos. */
        .st-key-win_nav {
            position: absolute; bottom: 4px; right: 10px; z-index: 20;
            width: auto !important;
            display: flex !important; flex-direction: row !important;
            align-items: center !important;
            gap: 2px !important;
            padding: 1px 2px !important;
            background: rgba(255,255,255,0.55) !important;
            backdrop-filter: blur(4px);
            border-radius: 6px !important;
        }
        .st-key-win_nav [data-testid="stElementToolbar"] { display: none; }
        .st-key-win_nav [data-testid="stElementContainer"] { width: auto !important; }
        /* Estilo base compartido: rectangulo con esquinas suaves + sombra
           leve. Mismo alto para flechas y pills → se leen como una sola
           barra homogenea. Compacto verticalmente (18px) para no invadir
           la fila de las etiquetas del eje X. */
        .st-key-win_nav button {
            min-width: 20px !important; width: auto !important;
            height: 17.5px !important;
            min-height: 17.5px !important;
            padding: 0 6px !important;
            border-radius: 4px !important;
            border: 0.5px solid rgba(0,0,0,0.06) !important;
            background: #ffffff !important;
            color: #5a5a6a !important;
            font-size: 10.5px !important; font-weight: 400 !important;
            line-height: 1 !important;
            box-shadow: 0 1px 2px rgba(15,15,30,0.06),
                        0 1px 1px rgba(15,15,30,0.04) !important;
            transition: background .12s, color .12s, box-shadow .12s !important;
        }
        .st-key-win_nav button:hover:not(:disabled) {
            background: #f0edfe !important;
            color: #4d3fb3 !important;
            box-shadow: 0 2px 4px rgba(76,60,180,0.14) !important;
        }
        .st-key-win_nav button:disabled {
            opacity: .35 !important;
            box-shadow: none !important;
        }
        /* Flechas: mas chicas en X, glifo mas grande. */
        .st-key-cp_win_prev button,
        .st-key-cp_win_next button {
            width: 20px !important;
            padding: 0 !important;
            color: #6c5ce7 !important;
            font-size: 12px !important;
        }

        /* Panel A — controles flotantes en la cabecera (Opción 1): DOS flotantes
           absolutos apilados a la derecha — un texto chico con la selección
           (período) ARRIBA y, justo debajo, Ámbito + Top N en una FILA. Al ser
           absolutos no empujan el gráfico. El key de un st.container SIN borde ES
           el stVerticalBlock, por eso la dirección FILA se fija sobre .st-key-...
           directamente (no sobre un bloque anidado). Valores verificados. */
        .st-key-chartcard_prov_prods { position: relative; }
        /* MATAR TODO espacio vertical entre header y gráfico: Streamlit
           inyecta gap en stVerticalBlock + margins en cada stElementContainer
           (uno para el markdown del título, otro para el plotly). */
        .st-key-chartcard_prov_prods,
        .st-key-chartcard_prov_prods [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            row-gap: 0 !important;
        }
        .st-key-chartcard_prov_prods [data-testid="stElementContainer"],
        .st-key-chartcard_prov_prods [data-testid="stMarkdownContainer"],
        .st-key-chartcard_prov_prods [data-testid="stPlotlyChart"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Reducir el padding interior de la card (era 15px por defecto).
           Padding-top mínimo para que el título quede alineado con los
           botones absolutos de la derecha (que están anclados al top). */
        .st-key-chartcard_prov_prods {
            padding: 2px 12px 8px 12px !important;
        }
        /* Tooltip del período: aparece al posar el cursor sobre el botón
           "Selección" (2º botón del primer button group). El valor viene de
           la CSS variable --periodo-selec inyectada desde Python. */
        .st-key-topn_pills > div:first-child [data-testid="stButtonGroup"]
        button:nth-child(2) { position: relative; }
        .st-key-topn_pills > div:first-child [data-testid="stButtonGroup"]
        button:nth-child(2):hover::after {
            content: var(--periodo-selec, "");
            position: absolute; top: calc(100% + 4px); right: 0;
            background: var(--text-primary, #262730);
            color: var(--surface-2, #fff);
            padding: 4px 8px; border-radius: 4px;
            font-size: 11px; line-height: 1.2; white-space: nowrap;
            z-index: 100; pointer-events: none;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        }
        /* Toggles en la MISMA fila del título, centrados vertical. */
        .st-key-topn_float {
            position: absolute; top: 0; right: 12px; z-index: 20;
            height: 24px; display: flex; align-items: center;
            width: auto !important;
        }
        .st-key-topn_float > div { width: auto !important; }
        .st-key-topn_pills {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            gap: 6px !important;
            width: auto !important;
        }
        .st-key-topn_pills > div { width: auto !important; }
        /* Cabecera compacta: título y controles en una sola línea. Se reduce
           min-height y padding vertical para acercar el gráfico al título. */
        .st-key-chartcard_prov_prods .chart-card-hdr {
            padding: 0 200px 0 4px;
            min-height: 22px;
            margin: 0 !important;
            font-size: 13px;
            line-height: 1.25;
            display: flex;
            align-items: center;
            border-bottom: none;
        }
        .st-key-topn_float [data-testid="stElementToolbar"] { display: none; }
        /* Encoger los botones de los pills (Rango/Selección y 5/10/20). */
        .st-key-topn_float [data-testid="stButtonGroup"] button {
            min-height: 22px !important;
            height: 22px !important;
            padding: 0 8px !important;
            font-size: 11px !important;
            line-height: 1 !important;
        }

        /* Ámbito de fecha (En rango / Todo) — en la cabecera del Panel B.
           Se replican las mismas reglas de compactación del Panel A para
           que titulo, toggles y contenido queden a la misma altura. */
        .st-key-chartcard_prov_prov_de_prod { position: relative; }
        .st-key-chartcard_prov_prov_de_prod,
        .st-key-chartcard_prov_prov_de_prod [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            row-gap: 0 !important;
        }
        .st-key-chartcard_prov_prov_de_prod [data-testid="stElementContainer"],
        .st-key-chartcard_prov_prov_de_prod [data-testid="stMarkdownContainer"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        .st-key-chartcard_prov_prov_de_prod {
            padding: 2px 12px 8px 12px !important;
        }
        .st-key-chartcard_prov_prov_de_prod .chart-card-hdr {
            padding: 0 140px 0 4px;
            min-height: 22px;
            margin: 0 !important;
            font-size: 13px;
            line-height: 1.25;
            display: flex;
            align-items: center;
            border-bottom: none;
        }
        .st-key-panelb_scope_float {
            position: absolute; top: 0; right: 12px; z-index: 5;
            height: 24px; display: flex; align-items: center;
            width: auto !important;
        }
        .st-key-panelb_scope_float > div { width: auto !important; }
        .st-key-panelb_scope_float [data-testid="stElementToolbar"] { display: none; }
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button {
            min-height: 22px !important;
            height: 22px !important;
            padding: 0 8px !important;
            font-size: 11px !important;
            line-height: 1 !important;
        }

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

        /* ── Panel B: tarjetas por proveedor (reemplaza el st.dataframe) ──
           Reemplaza la tabla de 5 columnas por un stack de tarjetas: swatch
           del color del proveedor (matchea con la barra del chart principal)
           + nombre + total S/, y debajo un grid con las 4 metricas
           (Últ. compra, Precio unit., Cantidad, UM). En mobile el grid pasa a
           2 columnas; en desktop cabe en fila. La tarjeta con el menor precio
           lleva un borde izquierdo verde y el precio en verde. */
        .pb-cards {
            display: flex; flex-direction: column; gap: 6px;
            margin: 4px 0 8px;
        }
        .pb-card {
            background: #fff; border: 0.5px solid #e6e6ea;
            border-left: 3px solid transparent;
            border-radius: 6px; padding: 7px 10px;
        }
        .pb-card.is-min { border-left-color: #15803d; }
        .pb-card .line1 {
            display: flex; align-items: center; gap: 6px; margin-bottom: 4px;
        }
        .pb-card .sw {
            width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0;
        }
        .pb-card .name {
            flex: 1; min-width: 0;
            color: #18181d; font-size: 12px; font-weight: 500;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .pb-card .total {
            color: #534AB7; font-size: 11.5px; font-weight: 500;
            font-variant-numeric: tabular-nums; flex-shrink: 0;
        }
        .pb-card .grid {
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 4px 10px; font-size: 11px;
        }
        .pb-card .cell {
            display: flex; align-items: baseline; gap: 5px; min-width: 0;
        }
        .pb-card .cell .lab {
            color: #a2a2ad; text-transform: uppercase;
            letter-spacing: 0.03em; font-size: 9.5px; flex-shrink: 0;
        }
        .pb-card .cell .val {
            color: #18181d; font-variant-numeric: tabular-nums;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .pb-card .pu { font-weight: 500; }
        .pb-card .pu.pu-min { color: #15803d; font-weight: 600; }
        /* Grid a 2 columnas en anchos chicos: cuando la card mide <= 380px
           (mockup mobile). Container query, con fallback por ancho de
           viewport para navegadores sin soporte. */
        @container (max-width: 380px) {
            .pb-card .grid { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 900px) {
            .pb-card .grid { grid-template-columns: 1fr 1fr; }
        }

        /* ── TARJETAS COLAPSABLES: animacion unfold (drill Proveedor) ──
           IMPORTANTE: NO usar scaleX/scaleY/rotate en el contenedor. Al
           remontar plotly/aggrid/dataframe con key nueva, esos componentes
           miden el ancho durante la animacion; si el transform reduce el
           tamano visual, el getBoundingClientRect devuelve ~0 y el
           componente renderiza con columnas/chart colapsados. Usamos solo
           opacity + translate para que el ancho real del contenedor
           permanezca intacto durante toda la animacion. */
        @keyframes unfoldDown {
            0%   { opacity: 0; transform: translateY(-8px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        /* La animacion se aplica DIRECTO a la tarjeta por su key estable.
           Streamlit reutiliza el nodo DOM mientras sigue abierta, asi que el
           unfold solo corre al montarse (oculta->visible), no en cada rerun.
           fill-mode backwards: arranca invisible y al terminar no deja
           transform residual. NO usamos <script> porque st.markdown NO
           ejecuta JS. */
        /* Bloque docs: se despliega hacia ABAJO. */
        .st-key-compras_prov_card_docs {
            animation: unfoldDown 0.32s cubic-bezier(0.4, 0, 0.2, 1) backwards;
        }
        /* Bloque paneles: entra deslizando desde la izquierda al enfocar. */
        @keyframes unfoldRight {
            0%   { opacity: 0; transform: translateX(-14px); }
            100% { opacity: 1; transform: translateX(0); }
        }
        .st-key-compras_prov_card_paneles {
            animation: unfoldRight 0.32s cubic-bezier(0.4, 0, 0.2, 1) backwards;
        }
        /* ── PESTILLO como PILL: solo queda el de "Detalle de documentos por
           proveedor" (latch_docs). El boton ES el titulo: clic en cualquier
           parte del pill abre/cierra. El icono (carrete SVG) va como
           background-image en ::before, a la izquierda del label, y gira
           180deg cuando el bloque esta abierto (rotacion inyectada desde
           Python con <style>). El detalle A/B ya no tiene pestillo ni boton
           de cerrar: lo abre y lo cierra el clic en la barra. */
        .st-key-docs_row {
            margin: 8px 0 6px;
        }
        /* El detalle A/B va PEGADO al chart (es su continuacion, no un bloque
           aparte). El margen negativo se come parte del gap de 1rem que el
           bloque vertical de Streamlit mete entre hermanos. */
        .st-key-paneles_row {
            margin: -10px 0 6px !important;
        }
        .st-key-latch_docs {
            width: auto !important;
            margin: 0 0 8px 0 !important;
            display: inline-block;
        }
        .st-key-latch_docs button {
            display: inline-flex !important;
            align-items: center; justify-content: flex-start;
            gap: 8px !important;
            width: auto !important; min-width: 0 !important;
            height: auto !important; min-height: 0 !important;
            padding: 6px 16px 6px 10px !important;
            margin: 0 !important;
            border: 0.5px solid #d4cdf7 !important;
            border-radius: 999px !important;
            background: #f0edfe !important; box-shadow: none !important;
            cursor: pointer !important;
            transition: background .15s, border-color .15s !important;
        }
        .st-key-latch_docs button:hover {
            background: #e5e0fc !important;
            border-color: #b9adf1 !important;
        }
        .st-key-latch_docs button:focus,
        .st-key-latch_docs button:active {
            outline: none !important; box-shadow: none !important;
        }
        /* Label del boton (el <p> que Streamlit inserta): tipografia del titulo. */
        .st-key-latch_docs button p {
            display: inline !important;
            font-size: 13px !important; font-weight: 500 !important;
            line-height: 1 !important;
            color: #4d3fb3 !important;
            margin: 0 !important; padding: 0 !important;
        }
        /* Icono de carrete: solo el pestillo de documentos (la X del detalle
           A/B no lo lleva). */
        .st-key-latch_docs button::before {
            content: ""; display: inline-block;
            width: 16px; height: 16px; flex-shrink: 0;
            background: center / contain no-repeat
                url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 22 22' fill='none'><circle cx='11' cy='11' r='3' fill='%236c5ce7'/><ellipse cx='11' cy='4' rx='5' ry='2.5' fill='%236c5ce7' opacity='.85'/><ellipse cx='11' cy='18' rx='5' ry='2.5' fill='%236c5ce7' opacity='.85'/><rect x='8' y='4' width='6' height='14' fill='%236c5ce7' opacity='.45' rx='1'/><line x1='11' y1='4' x2='11' y2='18' stroke='%23ffffff' stroke-width='1' opacity='.4'/><line x1='11' y1='4' x2='6.5' y2='3' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='4' x2='15.5' y2='3' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='18' x2='6.5' y2='19' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='18' x2='15.5' y2='19' stroke='%23ffffff' stroke-width='.8' opacity='.5'/></svg>");
            transition: transform .55s cubic-bezier(.4, 0, .2, 1);
        }

        /* ══════════════════════════════════════════════════════════════
           MÓVIL: los controles flotantes de este drill son position:absolute
           sobre las tarjetas — pensados para desktop. En viewport angosto se
           enciman con el título de su tarjeta o desbordan el ancho. Se sacan
           del posicionamiento absoluto y fluyen como una fila propia bajo el
           título/gráfico. Nada se encima; a cambio la tarjeta crece un poco
           en alto, barato en móvil.
           ── Dos breakpoints, por qué distintos:
           · Paneles A/B viven en st.columns(2), que colapsa a 1 columna recién
             por debajo de ~640px. ENTRE 640 y 900px cada panel es media
             pantalla y su título + los 5 pills ya no caben en la cabecera →
             el fix de topn_float/panelb_scope_float aplica desde 900px.
           · El gráfico principal (y su win_nav / floats de tope) es de ancho
             completo: solo se aprieta de verdad por debajo de ~640px.
           ══════════════════════════════════════════════════════════════ */
        @media (max-width: 900px) {
            /* Panel A: Rango/Selección + 5/10/20 — bajo el título.
               Panel B: En rango/Todo — bajo el título. */
            .st-key-topn_float,
            .st-key-panelb_scope_float {
                position: static !important;
                height: auto !important;
                width: 100% !important;
                margin: 2px 0 6px !important;
                justify-content: flex-start !important;
            }
        }
        @media (max-width: 640px) {
            /* Navegación de periodos: fluye bajo el gráfico y puede envolver
               en dos filas en vez de cortarse. */
            .st-key-win_nav {
                position: static !important;
                width: 100% !important;
                margin: 4px 0 0 0 !important;
                flex-wrap: wrap !important;
                justify-content: flex-start !important;
            }
            /* Controles del tope del gráfico. En desktop flotan absolutos
               sobre la esquina del plot (Proveedores a la izq., pills de
               periodo a la der.); en 375px sus anchos se cruzan y se solapan.
               En móvil dejan de flotar y fluyen como fila de controles ARRIBA
               del gráfico, apilados: Proveedores en su línea, y la
               granularidad como segmentado a ancho completo (4 segmentos
               iguales = tap targets grandes). Nada se encima; el plot baja un
               poco, que en móvil es barato. */
            .st-key-prov_pop_float,
            .st-key-gran_float {
                position: static !important;
                top: auto !important; left: auto !important; right: auto !important;
                width: 100% !important;
                margin: 0 0 6px 0 !important;
            }
            /* Granularidad Día/Semana/Mes/Año a ancho completo, segmentos que
               se reparten el ancho por igual. */
            .st-key-gran_float [data-testid="stButtonGroup"] {
                width: 100% !important;
                display: flex !important;
            }
            .st-key-gran_float [data-testid="stButtonGroup"] button {
                flex: 1 1 0 !important;
                min-width: 0 !important;
            }
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
    # Cada fila es una línea de detalle (documento × producto). El usuario
    # puede arrastrar campos a Filas/Columnas/Valores (panel derecho) para
    # pivotar. Por defecto: filas = Proveedor→Fecha→Documento→Producto,
    # columnas = Período (Semana/Mes/Año), valor = suma. Gran total al pie.
    import json  # noqa: E402
    from st_aggrid import AgGrid, JsCode  # noqa: E402
    from inyecciones import inject_maximize_aggrid  # noqa: E402

    if "cp_docs_abierto" not in st.session_state:
        st.session_state["cp_docs_abierto"] = True
    # -- Pestillo (carrete) + titulo en linea. Mismo patron que paneles A/B:
    #    SVG del carrete pintado por CSS sobre ::before del boton; rotacion
    #    de estado (abierto = 180) fijada por <style> inyectado.
    _docs_ab = st.session_state["cp_docs_abierto"]
    # Instance id (mismo patron que paneles A/B): fuerza remount del AgGrid
    # cada vez que el bloque se reabre, para que fit_columns_on_grid_load
    # vuelva a medir el ancho del contenedor.
    if _docs_ab and not st.session_state.get("cp_docs_prev_ab", False):
        st.session_state["cp_docs_inst"] = (
            st.session_state.get("cp_docs_inst", 0) + 1)
    st.session_state["cp_docs_prev_ab"] = _docs_ab
    _docs_inst = st.session_state.get("cp_docs_inst", 0)
    _rot_d = "180deg" if _docs_ab else "0deg"
    # Mismo patron que paneles A/B: abierto -> icono chico en gutter;
    # cerrado -> pill inline con titulo visible.
    _collapse_docs_css = ("""
        .st-key-docs_row { position: relative !important; }
        .st-key-docs_row .st-key-latch_docs {
            position: absolute !important;
            left: -50px !important;
            top: 18px !important;
            margin: 0 !important; z-index: 5;
        }
        .st-key-docs_row .st-key-latch_docs button {
            padding: 8px !important; border-radius: 8px !important;
        }
        .st-key-docs_row .st-key-latch_docs button p {
            display: none !important;
        }
        .st-key-docs_row .st-key-latch_docs button::before {
            width: 24px !important; height: 24px !important;
        }
    """ if _docs_ab else "")
    st.markdown(
        f"<style>.st-key-latch_docs button::before"
        f"{{transform:rotate({_rot_d});}}{_collapse_docs_css}</style>",
        unsafe_allow_html=True,
    )
    with st.container(key="docs_row"):
        with st.container(key="latch_docs"):
            if st.button(f"Detalle de documentos por proveedor · vista {gran}",
                         key="cp_btn_docs",
                         help="Abrir / cerrar el detalle de documentos"):
                st.session_state["cp_docs_abierto"] = not _docs_ab
                st.rerun()
        _bd = base[base["prov"].isin(top_provs)].copy()
        if _docs_ab and not _bd.empty:
            _fe = pd.to_datetime(_bd["fecha"], errors="coerce")
            _pv_docs = pd.DataFrame({
                "Proveedor": _bd["prov"].astype(str).values,
                # Fecha en ISO para orden correcto; se muestra dd/mm/yyyy en el front
                "Fecha": _fe.dt.strftime("%Y-%m-%d").fillna("").values,
                "Documento": (_bd["docu"].astype(str).values
                              if col_docu else _bd.index.astype(str).values),
                "Producto": _bd["prod"].astype(str).values,
                "Periodo": _bd["per"].astype(str).values,
                "Cantidad": _bd["cant"].astype(float).values,
                "Precio Unitario": (_bd["punit"].astype(float).values
                                    if col_punit else np.nan),
                "Valor": _bd["valor"].astype(float).values,
            })

            _pv_box = st.container(border=True, key="compras_prov_card_docs")

            _fmt_soles = JsCode(
                "function(p){ if(p.value==null) return ''; "
                "return 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
            _fmt_pu = JsCode(
                "function(p){ if(p.value==null || isNaN(p.value)) return ''; "
                "return 'S/ ' + Number(p.value).toLocaleString('es-PE',"
                "{minimumFractionDigits:2, maximumFractionDigits:2}); }")
            _fmt_qty = JsCode(
                "function(p){ if(p.value==null || isNaN(p.value)) return ''; "
                "return Number(p.value).toLocaleString('es-PE',"
                "{maximumFractionDigits:2}); }")
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
                # Orden de columnas de valor: Cantidad -> Precio Unitario -> Valor.
                # AgGrid respeta el orden de declaracion en pivot mode.
                {"field": "Cantidad", "type": "numericColumn", "aggFunc": "sum",
                 "valueFormatter": _fmt_qty, "minWidth": 100},
                {"field": "Precio Unitario", "type": "numericColumn",
                 "aggFunc": "avg", "valueFormatter": _fmt_pu, "minWidth": 110},
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
                # Quita el envoltorio 'sum(...)' / 'avg(...)' de los headers de
                # las columnas pivote: se muestra solo el nombre del campo
                # (Cantidad, Precio Unitario, Valor). Mismo criterio que la
                # tabla de Ajuste de Inventario.
                "suppressAggFuncInHeader": True,
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
                # domLayout NORMAL (no autoHeight): el grid tiene un viewport de
                # alto fijo con scroll interno. Es lo que permite hacer scroll en
                # PANTALLA COMPLETA — el _FS_CSS_IFRAME fuerza el grid a 100vh y
                # confía en el ag-body-viewport para desplazarse. Con autoHeight
                # el grid crecía al contenido y en fullscreen quedaba clippeado
                # sin scroll (mismo criterio que las tablas de Ajuste, que usan
                # normal + paginación y sí scrollean maximizadas).
            }
            # Alto del iframe inline (no fullscreen). En fullscreen lo sobrescribe
            # _FS_CSS_IFRAME a 100vh. 460 ≈ 14 filas visibles con scroll interno.
            with _pv_box:
                AgGrid(
                    _pv_docs,
                    gridOptions=_grid_pv,
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    height=460,
                    enable_enterprise_modules=True,
                    fit_columns_on_grid_load=True,
                    key=f"cp_prov_pivot_docs_{gran}_{_docs_inst}",
                )
                # Botón ⛶ de pantalla completa nativa (mismo patrón que las
                # tablas de tablas/): ancla el ⛶ en el riel de la tabla y usa
                # la Fullscreen API sobre el iframe. En móvil se toca y se gira
                # el teléfono a horizontal para ver todas las columnas; Esc / ✕
                # restauran. Como el drill de Proveedor tiene UN solo AgGrid,
                # buscarIframe() da con este.
                inject_maximize_aggrid()

                st.download_button(
                    "⬇ Descargar CSV",
                    data=_pv_docs.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"compras_documentos_{gran.lower()}.csv",
                    mime="text/csv",
                    key="cp_prov_resumen_dl",
                )
