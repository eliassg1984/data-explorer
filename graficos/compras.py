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
    if gran == "Día":
        return fe.dt.strftime("%Y-%m-%d")
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

    def _etiqueta_serie(vals, pct_periodo=None, docs=None):
        """Texto por barra: total SIEMPRE encima + variación vs el período
        ANTERIOR del mismo proveedor (▲ verde sube / ▼ rojo baja) + cantidad
        de documentos + % de participación en el período. La 1ª barra no
        tiene anterior → solo total + docs + %. Barras en 0 → sin etiqueta.

        pct_periodo: lista del mismo largo que vals con el % que la barra
            representa del total del segmento (0-100). Si None, se omite.
        docs: lista del mismo largo que vals con la cantidad de documentos
            (facturas / comprobantes únicos) que respaldan cada barra. Si
            None, se omite.
        """
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
    _ancho_barra_est_px = 1200 / max(1, len(_per_vis) * _n_series)
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

    # Fase 1 del rediseño del drill: cuando hay un proveedor en foco el
    # gráfico principal se encoge para dar aire al detalle de abajo — sigue
    # visible como contexto/mini-comparativa pero no domina la vista.
    _alto_chart = 220 if prov_focus is not None else 360
    _compras_layout(fig, alto=_alto_chart)
    fig.update_layout(

        barmode="group",
        # Margen superior mínimo: el gráfico sube dentro de la tarjeta y elimina
        # la franja vacía sobre las barras (los flotantes Proveedores/Periodo se
        # superponen encima; van con fondo semitransparente y no molestan).
        margin=dict(l=10, r=10, t=6, b=36),
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
        /* Ocultar la barra de herramientas del propio gráfico (fullscreen) */
        .st-key-compras_prov_card_chart > div > [data-testid="stElementToolbar"] { display: none; }

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
        /* ── Fase 2: tarjetas ricas del Panel B (proveedores del producto). ── */
        .st-key-chartcard_prov_prov_de_prod .sbc-wrap {
            display: flex; flex-direction: column; gap: 6px;
            padding: 4px 0 6px;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc {
            background: #ffffff;
            border: 0.5px solid var(--border, #e6e6ea);
            border-radius: 6px;
            padding: 8px 10px;
            transition: border-color .12s;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc:hover {
            border-color: var(--border-strong, #c8c8d0);
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-line1 {
            display: flex; align-items: center; gap: 6px;
            margin-bottom: 4px;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-sw {
            width: 8px; height: 8px; border-radius: 2px;
            flex-shrink: 0; display: inline-block;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-name {
            flex: 1;
            color: var(--text-primary, #18181d);
            font-size: 11.5px; font-weight: 500;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
            min-width: 0;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-total {
            color: #534AB7;
            font-size: 11px; font-weight: 500;
            font-variant-numeric: tabular-nums;
            flex-shrink: 0;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-line2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
            gap: 3px 8px;
            font-size: 10px;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-cell {
            display: flex; flex-direction: column;
            min-width: 0;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-lab {
            color: var(--text-muted, #a2a2ad);
            text-transform: uppercase; letter-spacing: 0.03em;
            font-size: 8.5px; line-height: 1;
            margin-bottom: 1px;
        }
        .st-key-chartcard_prov_prov_de_prod .sbc-val {
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
            color: var(--text-primary, #18181d);
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }

        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button:not(:first-child) {
            border-left: 1px solid rgba(49,51,63,0.15) !important;
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
        /* Bloque paneles: se despliega hacia la DERECHA (sale del pestillo). */
        @keyframes unfoldRight {
            0%   { opacity: 0; transform: translateX(-14px); }
            100% { opacity: 1; transform: translateX(0); }
        }
        .st-key-compras_prov_card_paneles {
            animation: unfoldRight 0.32s cubic-bezier(0.4, 0, 0.2, 1) backwards;
        }
        /* ── PESTILLO como PILL (icono + titulo en una misma capsula) ──
           El boton ES el titulo: clic en cualquier parte del pill abre/cierra.
           Se usa en "Analisis de productos y proveedores" (paneles A/B) y
           "Detalle de documentos por proveedor". El icono (carrete SVG) va
           como background-image en ::before, dentro del pill, a la izquierda
           del texto del label. Cuando el bloque esta abierto el icono gira
           180deg (rotacion inyectada desde Python con <style>). */
        .st-key-paneles_row,
        .st-key-docs_row {
            margin: 8px 0 6px;
        }
        .st-key-latch_paneles,
        .st-key-latch_docs {
            width: auto !important;
            margin: 0 0 8px 0 !important;
            display: inline-block;
        }
        .st-key-latch_paneles button,
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
        .st-key-latch_paneles button:hover,
        .st-key-latch_docs button:hover {
            background: #e5e0fc !important;
            border-color: #b9adf1 !important;
        }
        .st-key-latch_paneles button:focus,
        .st-key-latch_paneles button:active,
        .st-key-latch_docs button:focus,
        .st-key-latch_docs button:active {
            outline: none !important; box-shadow: none !important;
        }
        /* Label del boton (el <p> que Streamlit inserta): tipografia del titulo. */
        .st-key-latch_paneles button p,
        .st-key-latch_docs button p {
            display: inline !important;
            font-size: 13px !important; font-weight: 500 !important;
            line-height: 1 !important;
            color: #4d3fb3 !important;
            margin: 0 !important; padding: 0 !important;
        }
        .st-key-latch_paneles button::before,
        .st-key-latch_docs button::before {
            content: ""; display: inline-block;
            width: 16px; height: 16px; flex-shrink: 0;
            background: center / contain no-repeat
                url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 22 22' fill='none'><circle cx='11' cy='11' r='3' fill='%236c5ce7'/><ellipse cx='11' cy='4' rx='5' ry='2.5' fill='%236c5ce7' opacity='.85'/><ellipse cx='11' cy='18' rx='5' ry='2.5' fill='%236c5ce7' opacity='.85'/><rect x='8' y='4' width='6' height='14' fill='%236c5ce7' opacity='.45' rx='1'/><line x1='11' y1='4' x2='11' y2='18' stroke='%23ffffff' stroke-width='1' opacity='.4'/><line x1='11' y1='4' x2='6.5' y2='3' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='4' x2='15.5' y2='3' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='18' x2='6.5' y2='19' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='18' x2='15.5' y2='19' stroke='%23ffffff' stroke-width='.8' opacity='.5'/></svg>");
            transition: transform .55s cubic-bezier(.4, 0, .2, 1);
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
        # Chart siempre responsive al contenedor (estándar BI). La densidad se
        # controla con la ventana de periodos (server-side) + flechas de
        # navegación — nunca scroll horizontal externo ni zoom client-side.
        st.plotly_chart(
            fig,
            use_container_width=True,
            key=_chart_key,
            on_select="rerun",
            selection_mode="points",
            # edits.legendPosition: permite ARRASTRAR la leyenda con el cursor.
            # Ojo: la posición no persiste (al reejecutar vuelve a y=0.82).
            config={"displayModeBar": False,
                    "edits": {"legendPosition": True}},
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

    # -- Bloque 2: pestillo lateral (ancla). El titulo queda SIEMPRE visible;
    #    la tarjeta A/B se despliega a la derecha del pestillo. La tarjeta vive
    #    en una funcion local para NO re-indentar su cuerpo; se llama dentro de
    #    la columna body (abajo) solo si el pestillo esta abierto.
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
                            _compras_layout(figa, alto=max(200, 30 * len(agg) + 40))
                            figa.update_xaxes(tickprefix="S/ ", tickformat=",.0f")
                            figa.update_layout(margin=dict(l=10, r=140, t=2, b=10),
                                               bargap=0.18)
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
                        # Mapa prov→color heredado del ranking del top chart (así
                        # el swatch de cada card matchea la barra de arriba).
                        _cmap = {p: PALETA_CALLAI[i % len(PALETA_CALLAI)]
                                 for i, p in enumerate(orden_provs)}
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
                            _cant = float(grp["cant"].sum())
                            _tot = float((grp["punit"] * grp["cant"]).sum()
                                         if col_punit else 0.0)
                            filas.append({
                                "prov":     prov,
                                "precio":   ult,
                                "fecha":    (_uf.strftime("%d/%m/%Y")
                                             if _uf is not None else "—"),
                                "cant":     _cant,
                                "um":       (_um_de(grp).strip() if col_um else ""),
                                "total":    _tot,
                                "color":    _cmap.get(prov, "#888887"),
                            })
                        # Orden por cantidad acumulada (comportamiento previo).
                        filas.sort(key=lambda r: r["cant"], reverse=True)
                        # Menor precio → resalte verde (comportamiento previo).
                        _precios = [r["precio"] for r in filas
                                    if pd.notna(r["precio"])]
                        _min = min(_precios) if _precios else None

                        def _fmt_soles(v):
                            return (f"S/ {v:,.2f}" if pd.notna(v) else "—")

                        def _fmt_int(v):
                            return f"{v:,.0f}" if v else "0"

                        _rows_html = []
                        for r in filas:
                            _es_min = (_min is not None and pd.notna(r["precio"])
                                       and r["precio"] == _min)
                            _precio_html = _fmt_soles(r["precio"])
                            if _es_min:
                                _precio_html = (f"<span style='color:#0F6E56;"
                                                f"font-weight:600'>"
                                                f"{_precio_html}</span>")
                            _cells = []
                            if col_fecha:
                                _cells.append(
                                    "<div class='sbc-cell'>"
                                    "<div class='sbc-lab'>Últ. compra</div>"
                                    f"<div class='sbc-val'>{r['fecha']}</div>"
                                    "</div>")
                            _cells.append(
                                "<div class='sbc-cell'>"
                                "<div class='sbc-lab'>Últ. precio</div>"
                                f"<div class='sbc-val'>{_precio_html}</div>"
                                "</div>")
                            _cells.append(
                                "<div class='sbc-cell'>"
                                "<div class='sbc-lab'>Cant. acum.</div>"
                                f"<div class='sbc-val'>{_fmt_int(r['cant'])}</div>"
                                "</div>")
                            if col_um:
                                _cells.append(
                                    "<div class='sbc-cell'>"
                                    "<div class='sbc-lab'>UM</div>"
                                    f"<div class='sbc-val'>{r['um'] or '—'}</div>"
                                    "</div>")
                            _rows_html.append(
                                "<div class='sbc'>"
                                "  <div class='sbc-line1'>"
                                f"    <span class='sbc-sw' style='background:{r['color']}'></span>"
                                f"    <span class='sbc-name' title=\"{r['prov']}\">{r['prov']}</span>"
                                f"    <span class='sbc-total'>{_fmt_soles(r['total'])}</span>"
                                "  </div>"
                                f"  <div class='sbc-line2'>{''.join(_cells)}</div>"
                                "</div>"
                            )
                        st.markdown(
                            "<div class='sbc-wrap'>"
                            + "".join(_rows_html) +
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        st.caption("Último precio = precio unitario de la compra "
                                   "más reciente. Verde = menor precio.")

    # -- Pestillo (carrete) + titulo en linea. El SVG del carrete lo pinta el
    #    CSS sobre ::before del boton; aqui solo fijamos la rotacion del estado
    #    (abierto = 180). scope="fragment" evita recargar toda la app.
    _pan_ab = st.session_state.get("cp_paneles_abierto", True)
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
    _rot = "180deg" if _pan_ab else "0deg"
    # Cuando el bloque esta ABIERTO, el pill se colapsa a solo el icono
    # en el gutter izquierdo (position:absolute) y la tarjeta ocupa el
    # ancho completo a su derecha. Cuando esta CERRADO, el pill queda
    # inline con el texto del titulo visible.
    _collapse_css = ("""
        .st-key-paneles_row { position: relative !important; }
        .st-key-paneles_row .st-key-latch_paneles {
            position: absolute !important;
            left: -50px !important;
            top: 18px !important;
            margin: 0 !important; z-index: 5;
        }
        .st-key-paneles_row .st-key-latch_paneles button {
            padding: 8px !important; border-radius: 8px !important;
        }
        .st-key-paneles_row .st-key-latch_paneles button p {
            display: none !important;
        }
        .st-key-paneles_row .st-key-latch_paneles button::before {
            width: 24px !important; height: 24px !important;
        }
    """ if _pan_ab else "")
    st.markdown(
        f"<style>.st-key-latch_paneles button::before"
        f"{{transform:rotate({_rot});}}{_collapse_css}</style>",
        unsafe_allow_html=True,
    )
    with st.container(key="paneles_row"):
        with st.container(key="latch_paneles"):
            if st.button("Analisis de productos y proveedores",
                         key="cp_btn_paneles",
                         help="Abrir / cerrar el analisis de productos y "
                              "proveedores"):
                st.session_state["cp_paneles_abierto"] = not _pan_ab
                st.rerun(scope="fragment")
        if _pan_ab:
            _paneles_card()

    # ── Tabla pivotable de documentos (debajo de los paneles A/B) ─────────
    # Cada fila es una línea de detalle (documento × producto). El usuario
    # puede arrastrar campos a Filas/Columnas/Valores (panel derecho) para
    # pivotar. Por defecto: filas = Proveedor→Fecha→Documento→Producto,
    # columnas = Período (Semana/Mes/Año), valor = suma. Gran total al pie.
    import json  # noqa: E402
    from st_aggrid import AgGrid, JsCode  # noqa: E402

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
                # autoHeight: el grid ocupa exactamente el alto que necesita.
                # Se achica cuando hay pocas filas y crece al expandir sin
                # scroll interno ni white space. Requiere desactivar la
                # virtualizacion (ok con hasta ~200 filas totales, es el
                # rango de este pivote).
                "domLayout": "autoHeight",
            }
            # Con domLayout=autoHeight el grid maneja su propio alto; igual
            # pasamos un height al wrapper (st_aggrid lo requiere) — se usa
            # como TOPE del iframe para el caso teorico de expandir muchisimas
            # filas. 900 = ~28 filas expandidas visibles sin scroll extra.
            with _pv_box:
                AgGrid(
                    _pv_docs,
                    gridOptions=_grid_pv,
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    height=900,
                    enable_enterprise_modules=True,
                    fit_columns_on_grid_load=True,
                    key=f"cp_prov_pivot_docs_{gran}_{_docs_inst}",
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
                   ("Precio vs año pasado", "Vs año pasado"))),
    ("Cantidad",  (("Cantidad vs año pasado", "Vs año pasado"),
                   ("Cantidad por producto",  "Por producto"))),
    ("Más",       (("Semanal",              "Semanal"),
                   ("Vs año anterior",      "Vs año ant."),
                   ("Personalizado",        "Personalizado"),
                   ("Tabla",                "Tabla"))),
)

_COMPRAS_RAIL_SVG_CART = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
    '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>'
    '<path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 '
    '2-1.61L23 6H6"/></svg>'
)


def _compras_set_graf(opcion_id):
    """Callback de los botones del rail: setea la selección ANTES del rerun."""
    st.session_state["compras_graf_tipo"] = opcion_id


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

    # Rail vertical fijo pegado al borde DERECHO (estilos.py): cabecera
    # "Compras / Gráficos" + secciones agrupadas por categoría con dot delante
    # de cada ítem. El activo lo marca `type="primary"` (accent-light + barra
    # izquierda). La selección se persiste en compras_graf_tipo vía on_click,
    # que corre antes del rerun.
    sel_actual = st.session_state.get("compras_graf_tipo", opciones[0])
    if sel_actual not in opciones:
        sel_actual = opciones[0]
        st.session_state["compras_graf_tipo"] = sel_actual
    with st.container(key="compras_tabs_row"):
        # Cabecera del rail (icono + "Compras / Gráficos") eliminada: el rail
        # arranca directo con la primera categoria para ganar aire vertical.
        with st.container(key="graf_tipo_chips"):
            for i, (cat_nombre, items) in enumerate(_COMPRAS_RAIL_CATEGORIAS):
                st.markdown(
                    f'<div class="rail-cat-badge">{cat_nombre}</div>',
                    unsafe_allow_html=True,
                )
                for opcion_id, opcion_label in items:
                    slug = _slug(opcion_id)
                    st.button(
                        opcion_label,
                        key=f"graf_btn_{slug}",
                        type=("primary" if opcion_id == sel_actual
                              else "secondary"),
                        use_container_width=True,
                        on_click=_compras_set_graf, args=(opcion_id,),
                    )
                if i < len(_COMPRAS_RAIL_CATEGORIAS) - 1:
                    st.markdown('<div class="rail-sep"></div>',
                                unsafe_allow_html=True)
    graf = st.session_state.get("compras_graf_tipo", opciones[0])
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
