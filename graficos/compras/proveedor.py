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

from tema import ACENTO, GRIS_BORDE
from graficos.base import (
    PALETA_CALLAI, _card, _compras_layout, _compras_truncar, titulo_en_franja,
)
from graficos.compras._comun import _es_movil, _first_point
from graficos.compras._css_proveedor import CSS as CSS_PROVEEDOR
from graficos.compras._documentos_proveedor import tabla_documentos
from graficos.compras._etiquetas_proveedor import sufijo_granularidad
from graficos import alturas


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
    # 2026-08-16, a pedido: por defecto se muestran TODOS los proveedores del
    # rango de fechas, no los 5 mas grandes. `_todos_provs_temp` sale de `d`,
    # que ya viene filtrado por fecha, asi que "todos" significa "todos los
    # que compraron en el periodo elegido" y cambia solo con la fecha.
    # El usuario sigue pudiendo recortar con Top 3/5/10 en el popover.
    _default_prov_sel = _real_provs
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
    # El `or` cubre el caso "el usuario destildo todo": cae al default, que
    # desde 2026-08-16 son TODOS (ver `_default_prov_sel` arriba) — los dos
    # tienen que decir lo mismo o el reset del popover cambiaria el default.
    prov_multisel = [p for p in _todos_provs_temp
                     if st.session_state.get("cp_prov_cb::" + str(p))] \
                    or _real_provs

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

    # Proveedores a dibujar (gobiernan la paleta, el filtro y el cuadro de
    # control de la izquierda).
    _tot_all  = base["valor"].sum() or 1.0
    top_provs = [p for p in prov_multisel if p in set(base["prov"].unique())]
    if not top_provs:
        # 2026-08-16: sin seleccion propia se muestran TODOS los del rango de
        # fechas (a pedido), no los 5 mas grandes. Ordenados por valor para
        # que la paleta siga asignando los colores mas fuertes a los que mas
        # pesan, igual que antes. Con "todos" ya no hay resto: la serie gris
        # "Otros" desaparece sola, porque _otros_mask queda vacia.
        top_provs = (base.groupby("prov")["valor"].sum()
                         .sort_values(ascending=False).index.tolist())

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

    # Total por proveedor sobre TODO el rango (el ranking no mira períodos).
    _tot_por_prov = (base[base["prov"].isin(orden_provs)]
                     .groupby("prov")["valor"].sum()
                     .reindex(orden_provs, fill_value=0))
    _rk_nombres = list(_tot_por_prov.index)
    _rk_valores = [float(v) for v in _tot_por_prov.values]
    _rk_colores = [PALETA_CALLAI[i % len(PALETA_CALLAI)]
                   for i in range(len(_rk_nombres))]
    if _hay_otros and _otros_seleccionado:
        _rk_nombres.append("Otros")
        _rk_valores.append(float(base[_otros_mask]["valor"].sum()))
        _rk_colores.append(GRIS_BORDE)

    # Plotly dibuja las barras horizontales de ABAJO hacia arriba, así que
    # para que el mayor quede ARRIBA hay que pasarle la lista al revés.
    # (Es la misma trampa que ya documenta el drill de Familia.)
    _ord = sorted(range(len(_rk_valores)), key=lambda i: _rk_valores[i])
    _rk_nombres = [_rk_nombres[i] for i in _ord]
    _rk_valores = [_rk_valores[i] for i in _ord]
    _rk_colores = [_rk_colores[i] for i in _ord]

    # ── Procesar clic ANTES de dibujar ────────────────────────────────────
    # Leemos la selección que Streamlit guardó en session_state[chart_key] en
    # la interacción previa. Así actualizamos el foco y construimos el figure
    # UNA sola vez con el foco correcto: sin doble rerun = sin parpadeo.
    # Clic en la MISMA barra → la desenfoca; en otra → cambia el foco. El
    # foco es lo que ABRE el drill inferior (paneles A/B), así que esto es lo
    # que mantiene viva esa navegación.
    #
    # 2026-08-16: el mapeo pasó de `curve_number` a `point_index`. Con las
    # barras verticales había UNA SERIE POR PROVEEDOR y el número de serie
    # identificaba al proveedor; el ranking horizontal es una sola serie con
    # un punto por proveedor, así que ahora identifica el ÍNDICE del punto.
    # Por eso los datos del ranking se calculan ARRIBA de este bloque: el
    # clic necesita el mismo orden con el que se dibujó.
    _chart_key = f"compras_g_prov_main_{gran}"
    _mp = _first_point(st.session_state.get(_chart_key))
    if _mp is not None:
        _pi = _mp.get("point_index", _mp.get("point_number"))
        if _pi is not None and 0 <= _pi < len(_rk_nombres):
            _clicked = _rk_nombres[_pi]
            # "Otros" no es un proveedor real: agrupa a los que quedaron
            # fuera, así que no hay drill que abrir.
            if _clicked != "Otros":
                # Dedup para no reprocesar el mismo clic en cada rerun (la
                # selección de plotly PERSISTE — CLAUDE.md).
                if st.session_state.get("compras_prov_last_click") != _clicked:
                    st.session_state["compras_prov_last_click"] = _clicked
                    _misma_barra = (_clicked == prov_focus)
                    prov_focus = None if _misma_barra else _clicked
                    prod_focus = None
                    st.session_state["compras_prov_focus"]     = prov_focus
                    st.session_state["compras_prov_prodfocus"] = None
                    # El período ya no sale de este gráfico (el ranking no
                    # tiene eje de tiempo): lo fija el de evolución.
                    st.session_state["compras_prov_perfocus"]  = None

    # ── Gráfico principal: RANKING horizontal de proveedores ─────────────
    # 2026-08-16, a pedido y con mockup aprobado (nivel 2 de densidad): deja
    # de ser barras verticales por período y pasa a un ranking horizontal —
    # un proveedor por FILA, ordenado por valor. El eje de tiempo no se
    # pierde: se muda al gráfico de evolución de al lado, que muestra el
    # proveedor elegido.
    #
    # Resuelve de raíz lo que se venía parchando: con 20+ proveedores en
    # vertical las barras se apretaban hasta ser ilegibles, y hubo que
    # meterles ancho mínimo y scroll horizontal. En horizontal cada
    # proveedor es una fila de alto fijo: la lista crece hacia abajo y no
    # hay nada que comprimir. Por eso también se fue el cuadro de control
    # de la izquierda: los nombres AHORA SON el eje, y tenerlos también en
    # una columna aparte era mostrarlos dos veces.
    _gran_suffix = sufijo_granularidad(gran)


    # Nivel 2 del mockup: monto y % del total del rango, nada más. El resto
    # (documentos) va al hover — en una barra lo que se compara es el LARGO,
    # y cada cifra extra al final se lo come.
    # OJO con el %: acá es sobre el total del RANGO, no del período. Con el
    # eje de tiempo, "12%" podía leerse como "12% de ese mes"; en un ranking
    # es "12% de todo lo comprado en el rango".
    _rk_pct = [v / _tot_all * 100 for v in _rk_valores]
    _rk_txt = [f"S/ {v:,.0f}  ·  {p:.0f}%"
               for v, p in zip(_rk_valores, _rk_pct)]
    if "docu" in base.columns and (base["docu"].astype(str) != "").any():
        _docs_prov = base.groupby("prov")["docu"].nunique()
    else:
        _docs_prov = None
    _rk_docs = [int(_docs_prov.get(p, 0)) if _docs_prov is not None else 0
                for p in _rk_nombres]
    # El foco se resalta apagando a los demás, igual que en el chart viejo.
    _rk_op = [1.0 if (prov_focus is None or p == prov_focus) else 0.30
              for p in _rk_nombres]

    fig = go.Figure(go.Bar(
        x=_rk_valores,
        y=[_compras_truncar(p, 24) for p in _rk_nombres],
        orientation="h",
        marker=dict(color=_rk_colores, opacity=_rk_op),
        text=_rk_txt,
        textposition="outside",
        textfont=dict(size=12),
        cliponaxis=False,
        customdata=[[p, d] for p, d in zip(_rk_nombres, _rk_docs)],
        hovertemplate=("<b>%{customdata[0]}</b><br>"
                       "S/ %{x:,.0f}<br>"
                       "%{customdata[1]} docs<extra></extra>"),
    ))

    # Alto POR FILA, no fijo: es lo que hace que 5 proveedores y 25 se lean
    # igual (CLAUDE.md § alturas). Ya no se encoge con el foco: en vertical
    # bajar a 180px daba aire al detalle de abajo, pero en un ranking eso
    # recortaría proveedores de la lista.
    _alto_chart = alturas.por_filas(len(_rk_nombres), px_fila=26,
                                    minimo=180, extra=40)
    _compras_layout(fig, alto=_alto_chart)
    fig.update_layout(
        # r=110 le reserva sitio al rótulo "S/ 4,6k · 19%" que va FUERA de
        # la barra; sin eso `cliponaxis=False` lo dibuja pero se sale de la
        # tarjeta.
        margin=dict(l=10, r=110, t=6, b=10),
        # En barras HORIZONTALES el eje Y son los NOMBRES, no valores:
        # `_compras_layout` oculta los ticks del eje Y por convención del
        # proyecto, así que acá hay que volver a encenderlos — con
        # `automargin` o los nombres largos se recortan (CLAUDE.md § Plotly).
        yaxis=dict(showticklabels=True, automargin=True,
                   tickfont=dict(size=11)),
        # El eje X sobra: cada barra lleva su monto y su % al final.
        xaxis=dict(visible=False),
        bargap=0.28,
        showlegend=False,
        hovermode="closest",
        uirevision=_chart_key,
    )

    # Sin rangeslider: la navegacion es server-side (ventana + flechas), asi
    # sobrevive al clic en una barra. Eso ademas libera el alto que ocupaba el
    # slider, que ahora queda para las barras.

    # ── Selector de granularidad FLOTANTE sobre el gráfico ────────────────
    # El contenedor "compras_prov_card_chart" es posición relativa; dentro,
    # las pills se posicionan en absoluto arriba-derecha, superpuestas al gráfico.
    st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)

    # Nombre de la vista PRIMERO en la FRANJA superior, pegado a la
    # izquierda y antes del pill de fecha — igual que Compras > Familia.
    # Mismo mecanismo que los otros titulos fantasma (arquitectura.md regla
    # #120): vive fuera de la tarjeta y lo ancla el CSS con position:fixed,
    # que es lo que corre al pill y a los chips (ver _css_proveedor.py).
    titulo_en_franja(
        st.container(key="compras_prov_titulo_franja").empty(), "Proveedor")

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

        # El scroll horizontal y el ancho mínimo por barra que vivían acá se
        # fueron con las barras verticales: existían porque muchas series en
        # pocos períodos se apretaban a lo ancho. El ranking horizontal no
        # tiene ese problema — cada proveedor es una fila de alto fijo y lo
        # que crece es el ALTO, que ya resuelve `alturas.por_filas`.

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
        # El chart es responsive al contenedor (estándar BI) MIENTRAS entre.
        # La densidad se controla con la ventana de periodos (server-side) +
        # flechas; cuando ni con eso alcanza —muchas series en pocos
        # periodos— toma su ancho mínimo y el contenedor scrollea.
        with st.container(key="cp_chart_wrap"):
            # ── Ranking (izq.) + evolución del elegido (der.) ──────────────
            # 2026-08-16: el cuadro de control de proveedores DESAPARECE.
            # Listaba color + nombre + monto + %, y con el ranking horizontal
            # los nombres pasaron a ser el eje: tenerlos también en una
            # columna aparte era mostrar lo mismo dos veces, a media pantalla
            # de distancia. Su información no se pierde — el monto y el % van
            # ahora al final de cada barra.
            # En su lugar, a la derecha, la EVOLUCIÓN del proveedor elegido:
            # es donde se mudó el eje de tiempo que el ranking dejó de tener.
            _c_rank, _c_evo = st.columns([1.5, 1], gap="small")
            with _c_rank:
                with st.container(key="cp_chart_scroll"):
                    st.plotly_chart(
                        fig,
                        width="stretch",
                        key=_chart_key,
                        on_select="rerun",
                        selection_mode="points",
                        config=_cfg_chart,
                    )
            with _c_evo:
                # Sin elección del usuario cae al primero del ranking (el de
                # mayor valor) — mismo criterio que el Panel B de abajo. Como
                # `_rk_nombres` viene ordenado ASCENDENTE (plotly dibuja de
                # abajo hacia arriba), el mayor es el ÚLTIMO.
                _prov_evo = prov_focus
                if _prov_evo is None:
                    _reales = [p for p in _rk_nombres if p != "Otros"]
                    _prov_evo = _reales[-1] if _reales else None
                if _prov_evo is None:
                    st.caption("Sin proveedores en el rango.")
                else:
                    _serie_evo = (base[base["prov"] == _prov_evo]
                                  .groupby("per")["valor"].sum()
                                  .reindex(periodos, fill_value=0))
                    # Se dibuja la ventana visible, la misma que gobiernan las
                    # flechas de arriba: son los períodos que el usuario eligió
                    # mirar, y el ranking ya no las usa.
                    _evo_x = list(_serie_evo.index)[_sl]
                    _evo_y = [float(v) for v in _serie_evo.values[_sl]]
                    _color_evo = dict(zip(_rk_nombres, _rk_colores)).get(
                        _prov_evo, ACENTO)
                    fig_evo = go.Figure(go.Scatter(
                        x=_evo_x, y=_evo_y,
                        mode="lines+markers",
                        line=dict(color=_color_evo, width=2.5),
                        marker=dict(color=_color_evo, size=7),
                        fill="tozeroy",
                        fillcolor=_color_evo.replace(")", ", 0.10)").replace(
                            "rgb(", "rgba(") if _color_evo.startswith("rgb")
                            else None,
                        hovertemplate="%{x}<br>S/ %{y:,.0f}<extra></extra>",
                    ))
                    _compras_layout(fig_evo, alto=_alto_chart)
                    fig_evo.update_layout(
                        margin=dict(l=10, r=10, t=6, b=10),
                        xaxis=dict(type="category", tickangle=0,
                                   tickfont=dict(size=10)),
                        # Acá el eje Y SÍ son valores, así que se respeta la
                        # convención del proyecto y va sin etiquetas: cada
                        # punto trae su monto en el hover.
                        yaxis=dict(showticklabels=False),
                        showlegend=False,
                        hovermode="x unified",
                    )
                    st.markdown(
                        f'<div class="cp-evo-tit">Evolución · '
                        f'{_compras_truncar(_prov_evo, 22)}</div>',
                        unsafe_allow_html=True)
                    st.plotly_chart(
                        fig_evo, width="stretch",
                        key=f"cp_evo_{gran}_{_prov_evo}",
                        config={"displayModeBar": False},
                    )
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
        # Producto por DEFECTO del Panel B: el primero de la tabla del Panel
        # A (el de mayor valor). Lo llena el Panel A mas abajo y lo lee el
        # Panel B, que se dibuja despues en el mismo `st.columns`. Existe
        # como variable local y NO se escribe en session_state a proposito:
        # es un DEFAULT de presentacion, no una seleccion del usuario. Si se
        # guardara como foco real, "no hay nada elegido" y "elegi justo el
        # primero" pasarian a ser el mismo estado, y ya no se podria volver
        # al vacio ni distinguir un clic deliberado.
        _prod_top = None
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
                        # `nlargest` ya devuelve de mayor a menor, que es el
                        # orden natural de una TABLA. El `.sort_values()`
                        # ascendente que habia aca era para el grafico de
                        # barras horizontales, que dibuja de abajo hacia
                        # arriba: sin el, el mas grande quedaba ultimo.
                        agg = (sub.groupby("prod")
                                  .agg(valor=("valor", "sum"), cant=("cant", "sum"))
                                  .nlargest(topn, "valor"))
                        if agg.empty:
                            st.info("Sin productos para este proveedor.")
                        else:
                            # 2026-08-16: era un grafico de barras horizontales
                            # con el clic capturado por `on_select` de Plotly.
                            # Pasa a TABLA (a pedido) conservando las dos cosas
                            # que aportaba: el clic que enfoca un producto — y
                            # que el Panel B de al lado sigue leyendo de
                            # `compras_prov_prodfocus`, sin enterarse del
                            # cambio — y la lectura de ranking, que ahora la da
                            # la barra DENTRO de la celda (ProgressColumn) en
                            # vez de una barra suelta. De yapa, ordenar por
                            # cualquier columna, que el grafico no permitia.
                            prod_cats = list(agg.index)
                            # `nlargest` ya ordeno de mayor a menor, asi que
                            # el primero es el producto de mas valor: ese es
                            # el que el Panel B muestra si no hay ninguno
                            # elegido a mano.
                            _prod_top = prod_cats[0]
                            # El % se calcula sobre el total del proveedor en el
                            # ambito vigente (`sub`), NO sobre la suma del Top N:
                            # asi "12%" sigue significando lo mismo tanto en Top
                            # 5 como en Top 20, y los porcentajes no suman 100
                            # cuando el Top deja productos afuera, que es la
                            # lectura honesta.
                            _tot_sub = float(sub["valor"].sum()) or 1.0
                            _val = agg["valor"].to_numpy(dtype=float)
                            tv = pd.DataFrame({
                                "Producto": prod_cats,
                                "Valor": _val,
                                "%": _val / _tot_sub * 100,
                                "Cant.": agg["cant"].to_numpy(dtype=float),
                                # _um_de devuelve la unidad con un espacio
                                # delante (viene de concatenarse a una etiqueta).
                                "UM": [_um_de(sub[sub["prod"] == p]).strip()
                                       for p in prod_cats],
                            })
                            # La key lleva `prod_focus` a proposito: la seleccion
                            # de un st.dataframe PERSISTE entre reruns igual que
                            # la de un plotly_chart (CLAUDE.md), asi que con key
                            # estable el mismo clic se re-procesaria en cada
                            # rerun. Al variar la key el widget remonta sin
                            # seleccion. El `!=` de mas abajo es el segundo
                            # cinturon, para el caso de reclic en la MISMA fila
                            # (ahi la key no cambia).
                            _aevt = st.dataframe(
                                tv,
                                hide_index=True,
                                use_container_width=True,
                                height=alturas.por_filas(len(tv), px_fila=35,
                                                         extra=45, minimo=0),
                                on_select="rerun",
                                selection_mode="single-row",
                                key=f"cp_prov_prods_tab_{prov_focus}_{prod_focus}_{_pan_inst}",
                                column_config={
                                    "Producto": st.column_config.TextColumn(
                                        "Producto", width="medium"),
                                    "Valor": st.column_config.ProgressColumn(
                                        "Valor", format="S/ %.0f",
                                        min_value=0,
                                        max_value=float(_val.max())),
                                    "%": st.column_config.NumberColumn(
                                        "%", format="%.0f%%", width="small"),
                                    "Cant.": st.column_config.NumberColumn(
                                        "Cant.", format="%.0f", width="small"),
                                    "UM": st.column_config.TextColumn(
                                        "UM", width="small"),
                                },
                            )
                            _rows = (_aevt or {}).get("selection", {}).get("rows", [])
                            if _rows and 0 <= _rows[0] < len(prod_cats):
                                _psel = prod_cats[_rows[0]]
                                if _psel != prod_focus:
                                    st.session_state["compras_prov_prodfocus"] = _psel
                                    st.rerun(scope="fragment")


            # Panel B: proveedores del producto seleccionado
            with pb:
                # Sin eleccion del usuario, cae al primero de la tabla de al
                # lado (a pedido: antes el panel arrancaba vacio, con solo el
                # titulo "Proveedores del producto" y nada debajo, y no habia
                # forma de saber que ese hueco se llenaba clickeando).
                # `_prod_top` es None si no hay proveedor en foco o su tabla
                # salio vacia: ahi el panel sigue mostrando el estado vacio.
                _prod_ver = prod_focus if prod_focus is not None else _prod_top
                _tb = ("Proveedores del producto" if _prod_ver is None
                       else f"Proveedores de · {_compras_truncar(_prod_ver, 26)}")
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
                    if _prod_ver is None:
                        pass
                    else:
                        # `_todo_hist` solo elige la FUENTE. El caption que lo
                        # anunciaba ("📅 Todo el histórico — ignora el filtro
                        # de fecha de arriba") se quitó a pedido: el pill
                        # "Todo" ya está marcado ahí mismo, en la cabecera del
                        # panel, así que la leyenda repetía lo que el propio
                        # control mostraba — y encima aparecía y desaparecía,
                        # moviendo las tarjetas de abajo en cada cambio.
                        _todo_hist = (_scope == "Todo" and d_full is not None)
                        _srcB = _base_prov_de(d_full) if _todo_hist else base
                        sub2 = _srcB[_srcB["prod"] == _prod_ver]
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
