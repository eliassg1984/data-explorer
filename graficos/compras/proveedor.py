"""graficos.compras.proveedor - drill de Proveedor.

Ranking de proveedores como tabla (nombre + barra de valor + documentos +
%). Clic en una fila fija el foco y filtra los paneles A/B y la tabla de
documentos de abajo.

Es el drill mas grande del dashboard. Incluye un bloque largo de CSS
inyectado con st.markdown para los controles flotantes sobre el grafico;
vive aca (y no en estilos/) porque esta scopeado a las keys de este drill.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from st_aggrid import AgGrid, JsCode

from tema import ACENTO, GRIS_BORDE, TEXTO_PRINCIPAL
from graficos.base import (
    PALETA_CALLAI, _card, _compras_layout, _compras_truncar, paso_etiquetas,
    titulo_en_franja,
)
from graficos.compras._comun import COLUMNAS_DRILL, GAP_DRILL
from graficos.compras._css_proveedor import CSS as CSS_PROVEEDOR
from graficos.compras._documentos_proveedor import tabla_documentos
from graficos import alturas, periodo


@st.fragment
def _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                             col_punit, col_um, col_fecha, col_docu=None,
                             d_full=None):
    """Dashboard de Proveedor.

    Tabla-ranking (izq.): un proveedor por fila, ordenados por valor, con
    la barra de "Valor" pintada como FONDO de la celda (un `linear-gradient`
    cortado en el % del valor — ver el bloque del AgGrid). Clic en una fila
    la enfoca y filtra los paneles A y B de abajo; clic en la MISMA fila
    quita el foco. Sin checkbox: el gesto es la fila entera. Al lado, la
    evolución del proveedor elegido.

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
    # Extraído a función (2026-08-16) para poder aplicárselo TAMBIÉN al
    # histórico completo, que es lo que alimenta el gráfico de evolución:
    # con el rango de la franja puede haber un solo período y una línea de
    # un punto no dibuja ninguna evolución (reportado con captura: en
    # granularidad Año se veía un punto suelto en medio de la nada).
    def _agregar_periodo(_df):
        _fe = pd.to_datetime(_df["fecha"], errors="coerce")
        _mes_es = {'Jan': 'Ene', 'Apr': 'Abr', 'Aug': 'Ago', 'Dec': 'Dic'}
        if gran == "Día":
            _df["_per_sort"] = _fe.dt.strftime("%Y-%m-%d")
            _p = _fe.dt.strftime("%d %b")
            for _en, _es in _mes_es.items():
                _p = _p.str.replace(_en, _es)
            _df["per"] = _p
        elif gran == "Semana":
            _ws = (_fe - pd.to_timedelta(_fe.dt.weekday, unit="D")).dt.normalize()
            _we = _ws + pd.Timedelta(days=6)
            _df["_per_sort"] = _ws.dt.strftime("%Y-%m-%d")   # clave de orden
            _p = _ws.dt.strftime("%d%b") + "-" + _we.dt.strftime("%d%b")
            for _en, _es in _mes_es.items():
                _p = _p.str.replace(_en, _es)
            _df["per"] = _p
        elif gran == "Año":
            _df["_per_sort"] = _fe.dt.year.astype("Int64").astype(str)
            _df["per"] = _df["_per_sort"]
        else:  # Mes
            _df["_per_sort"] = _fe.dt.to_period("M").astype(str)
            _df["per"] = _df["_per_sort"]
        return _df[_df["per"].notna() & (_df["per"] != "<NA>")]

    base = _agregar_periodo(base)

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
    # Orden: DESCENDENTE (mayor primero) — `orden_provs` ya viene así, y es
    # el orden natural de una TABLA (a diferencia del ranking en Plotly que
    # había antes, que necesitaba la lista al revés por cómo dibuja barras
    # horizontales de abajo hacia arriba; con la tabla eso ya no aplica).

    # ── El foco del ranking ───────────────────────────────────────────────
    # 2026-08-19: el ranking pasó de `st.dataframe` a AgGrid, y con eso
    # cambió DE DÓNDE sale el clic. Antes había que leer
    # `session_state[key]` ANTES de dibujar la tabla (la selección de un
    # st.dataframe queda ahí de la interacción previa) y llevar un dedup con
    # `compras_prov_last_click` para no reprocesar el mismo clic en cada
    # rerun. AgGrid DEVUELVE su selección en la llamada, así que el foco se
    # resuelve justo después de dibujar el grid, más abajo — y el dedup
    # desaparece: la selección ES el estado, no un evento que se repite.
    # Key NUEVA al cambiar de widget: la vieja ("compras_prov_rank_tab")
    # quedó en session_state con la forma del `st.dataframe` (un dict con
    # {"selection": {"rows": [...]}}), y una sesión abierta que la reusara le
    # pasaría ese valor al componente nuevo, que espera otra cosa.
    _rank_tab_key = "compras_prov_rank_grid"

    # ── Tabla-ranking: datos que consume ────────────────────────────────
    # 2026-08-17, a pedido: el ranking se UNE con la tabla resumen — eran
    # dos vistas de los mismos números (barra horizontal vs. fila de tabla)
    # una al lado de la otra. Pasa a ser una sola tabla (`st.dataframe`,
    # más abajo) con una `ProgressColumn` haciendo de barra — conserva la
    # lectura de ranking sin duplicar la información. El eje de tiempo no
    # se pierde: vive en el gráfico de evolución de al lado, que muestra el
    # proveedor elegido.
    #
    # Nivel 2 del mockup (heredado de la versión en barras): monto y % del
    # total del rango. OJO con el %: es sobre el total del RANGO, no del
    # período — con eje de tiempo "12%" podía leerse como "12% de ese mes";
    # acá es "12% de todo lo comprado en el rango".
    _rk_pct = [v / _tot_all * 100 for v in _rk_valores]
    if "docu" in base.columns and (base["docu"].astype(str) != "").any():
        _docs_prov = base.groupby("prov")["docu"].nunique()
    else:
        _docs_prov = None
    _rk_docs = [int(_docs_prov.get(p, 0)) if _docs_prov is not None else 0
                for p in _rk_nombres]

    # Frame visible de la tabla Y de evolución: 8 filas fijas, para que el
    # bloque de 2 columnas no baile con la cantidad de proveedores — lo que
    # no entra scrollea DENTRO (`st.dataframe` ya trae su propio scroll
    # interno con `height=`, a diferencia del `st.plotly_chart` de antes,
    # que necesitó el rodeo de la regla #125 de arquitectura.md).
    # px_fila=35/extra=45 son los mismos que ya usa la tabla de Panel A
    # (más abajo) para su `st.dataframe` — el alto de una FILA de tabla, no
    # el de una barra de gráfico (26px, lo que usaba el ranking viejo).
    _ALTO_FRAME = alturas.por_filas(8, px_fila=35, extra=45, minimo=0)
    # La evolución comparte su columna con el selector de período Y con el
    # cromo de su propia tarjeta (2026-08-18: son dos bloques, no uno), así
    # que su figura mide eso menos que la tabla de al lado. La tabla no paga
    # el cromo: su columna tenía 119px de aire medidos, la evolución es la que
    # manda el alto de la fila.
    # 2026-08-23: se le suman dos filas más (FRANJA_GRAN, FRANJA_WIN_NAV) —
    # `gran_float`/`win_nav` se mudaron DENTRO de esta tarjeta (antes
    # flotaban afuera, sin costarle alto a nadie). Sin restarlas, la tarjeta
    # de Evolución crecía 66px y la de Ranking se estiraba igual para
    # empatarla (regla de _80_cards.py "dos tarjetas de la misma fila miden
    # lo mismo") — verificado en vivo: las dos daban 473px de alto en vez
    # de la fila "natural" de Ranking, dejando aire de más al fondo.
    _ALTO_EVO = max(alturas.MINI,
                    _ALTO_FRAME - alturas.FRANJA_PILLS - alturas.FRANJA_GRAN
                    - alturas.FRANJA_WIN_NAV - alturas.CROMO_TARJETA)
    # Ancho de la figura de evolución, MEDIDO en el navegador (viewport 1912,
    # rails desplegados). No sale de una cuenta porque su columna cuelga de
    # dos repartos anidados —COLUMNAS_DRILL y el [2.6, 1] de acá abajo— sobre
    # un ancho que Python no conoce. Lo consume `paso_etiquetas` para decidir
    # cuántas etiquetas entran en el eje X; es el número que quedó obsoleto
    # (era ~380 cuando la figura ocupaba la columna entera) y nadie revisó al
    # partirla. Si se cambia el reparto de columnas, volver a medir: con
    # ?debug=1 → Rayos X, o auditarGraficos() desde la misma barra.
    _ANCHO_EVO = 206

    # ── Selector de granularidad FLOTANTE sobre el gráfico ────────────────
    # El contenedor "compras_prov_marco" es posición relativa; dentro, las
    # pills se posicionan en absoluto arriba-derecha, superpuestas al gráfico.
    st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)

    # Nombre de la vista PRIMERO en la FRANJA superior, pegado a la
    # izquierda y antes del pill de fecha — igual que Compras > Familia.
    # Mismo mecanismo que los otros titulos fantasma (arquitectura.md regla
    # #120): vive fuera de la tarjeta y lo ancla el CSS con position:fixed,
    # que es lo que corre al pill y a los chips (ver _css_proveedor.py).
    titulo_en_franja(
        st.container(key="compras_prov_titulo_franja").empty(), "Proveedor")

    # `_rank_tab_key` es ESTABLE (no depende del foco): el clic se procesa
    # arriba, antes de construir la tabla, así el rerun que abre el drill ya
    # sale con el foco correcto (sin doble rerun = sin parpadeo).
    # 2026-08-18: este contenedor DEJÓ de ser una tarjeta. Antes era el
    # bloque blanco que envolvía tabla + gráfico; ahora cada columna tiene el
    # suyo y éste queda solo como MARCO: el `position: relative` contra el que
    # flotan los tres controles (popover de proveedores, granularidad, flechas
    # de ventana), que siguen sirviendo a las dos columnas.
    #
    # Por eso también cambió de nombre. La key vieja empezaba con
    # `compras_prov_card_`, que es un wildcard por familia en
    # estilos/_80_cards.py: mientras la llevara, seguía pintándose de blanco
    # con padding y sombra ENCIMA de las dos tarjetas nuevas (bloque blanco
    # dentro de bloque blanco). Sacarlo de la familia es lo que lo vuelve
    # invisible, sin pelearle a la regla con overrides.
    with st.container(key="compras_prov_marco"):
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
                # columnas-internas: botonera del popover, no el eje de la vista.
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
        # 2026-08-23: la pill Día/Semana/Mes/Año (key `gran_float`) se movió
        # DENTRO de la tarjeta de Evolución, a pedido — ver ese bloque más
        # abajo (justo debajo de `cp_evo_periodo`). Se queda el nombre de
        # la key aunque ya no flote (mismo criterio que `--rail-der-*`
        # después de que el rail cambió de lado: renombrar 15 sitios en 4
        # ficheros por una etiqueta no paga el riesgo).

        # El scroll horizontal y el ancho mínimo por barra que vivían acá se
        # fueron con las barras verticales: existían porque muchas series en
        # pocos períodos se apretaban a lo ancho. El ranking horizontal no
        # tiene ese problema.
        # (Acá vivió una animación de @keyframes para el alto del chart al
        # cambiar el filtro de proveedores — se sacó 2026-08-17: con el
        # frame fijo de 8 filas de arriba, el bloque ya no cambia de alto
        # entre reruns, así que no queda nada que animar.)

        with st.container(key="cp_chart_wrap"):
            # ── Ranking (izq., tabla) + evolución (der.) ────────────────
            # 2026-08-16: el cuadro de control de proveedores DESAPARECE.
            # Listaba color + nombre + monto + %, y con el ranking horizontal
            # los nombres pasaron a ser el eje: tenerlos también en una
            # columna aparte era mostrar lo mismo dos veces, a media pantalla
            # de distancia.
            # A su lado, la EVOLUCIÓN del proveedor elegido: es donde vive
            # el eje de tiempo que el ranking no tiene.
            # 2026-08-17, a pedido: el ranking (barras) y la tabla resumen
            # —antes dos columnas separadas mostrando los mismos números—
            # se UNEN acá en una sola tabla con `ProgressColumn` haciendo de
            # barra. Muestra 8 filas fijas (`_ALTO_FRAME`) y scrollea el
            # resto por dentro (scroll nativo de `st.dataframe`).
            _c_tabla, _c_evo = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)
            with _c_tabla:
                # ── BLOQUE 1: el ranking ─────────────────────────
                # 2026-08-18, a pedido: lo que era UNA tarjeta con la
                # tabla y el gráfico adentro pasa a ser DOS bloques
                # separados por el gris del app. El prefijo de la key
                # (`compras_prov_card_`) no es decorativo: es lo que les
                # da el fondo blanco, el radio y el clamp a una pantalla
                # con scroll interno (estilos/_80_cards.py, regla por
                # FAMILIA de key). Renombrarlas fuera de ese prefijo las
                # deja sin marco.
                with st.container(border=True,
                                  key="compras_prov_card_ranking"):
                    # 2026-08-23, segunda vuelta: el `help=` de st.markdown
                    # (primer intento) es hover-only — el usuario esperaba
                    # que abriera con CLIC, como un popover. `st.popover`
                    # con el label como shortcode de ícono (sin texto) es
                    # el mismo patrón que ya usa `pestillos.py::pestillo`
                    # para un botón de solo-ícono; acá va en su propia
                    # columna angosta para quedar pegado al título.
                    # columnas-internas: título + ícono de ayuda dentro de
                    # ESTA tarjeta, no el eje de la página (ese lo marca
                    # COLUMNAS_DRILL más abajo).
                    _c_rank_tit, _c_rank_ayuda = st.columns([16, 1], gap="small")
                    with _c_rank_tit:
                        st.markdown('<div class="cp-rank-tit">Ranking de '
                                    'proveedores</div>', unsafe_allow_html=True)
                    with _c_rank_ayuda:
                        with st.popover(":material/info:",
                                        key="compras_prov_rank_ayuda",
                                        use_container_width=False):
                            st.caption("Se agrupa por Día, Semana, Mes o "
                                       "Año (arriba). El rango de fechas "
                                       "se ajusta desde otra pestaña de "
                                       "Compras.")
                    # ── El ranking es un AgGrid, no un `st.dataframe` ──────
                    # 2026-08-19, a pedido: los checkbox de selección se van y
                    # el gesto pasa a ser "clic en la fila". No era posible con
                    # `st.dataframe`: su columna de selección no se puede
                    # ocultar (no hay parámetro en 1.59) ni esconder por CSS,
                    # porque la grilla se dibuja en un CANVAS y no hay nodo que
                    # tocar. Cambiar de widget era la única salida.
                    #
                    # La barra de "Valor" NO necesitó un `cellRenderer` (ni la
                    # clase `init()/getGui()` de la regla #25, ni los
                    # sparklines de AG Grid, que son Enterprise): es el FONDO
                    # de la celda, un `linear-gradient` cortado en el % del
                    # valor. Los colores salen de `tema.py` y no de
                    # `var(--accent)` a propósito — el grid vive en un iframe
                    # propio y las variables CSS del documento padre no llegan.
                    _rk_max = float(max(_rk_valores)) if _rk_valores else 1.0
                    _rk_df = pd.DataFrame({
                        "Proveedor": _rk_nombres,
                        "Valor": _rk_valores,
                        "Docs": _rk_docs,
                        "%": _rk_pct,
                        # Columna oculta: el % de LLENADO de la barra (contra
                        # el mayor), que no es el mismo número que la columna
                        # "%" (esa es sobre el total del rango).
                        "_barra": [v / _rk_max * 100 for v in _rk_valores],
                    })
                    # Dos decisiones de legibilidad, las dos aprendidas
                    # mirando la primera versión (2026-08-19):
                    #
                    # 1. La pista va TRANSPARENTE, no tintada. Con un color de
                    #    fondo la columna entera se leía como un bloque
                    #    lavanda —"una sombra"— compitiendo con las barras y
                    #    tapando las bandas de fila del resto de la tabla.
                    #    Sin pista, lo único que se ve es el dato.
                    # 2. La barra llega hasta el 62% de la celda, no al 100%,
                    #    y el texto va alineado a la DERECHA: así nunca se
                    #    pisan. Antes el monto caía encima del morado y quedaba
                    #    texto oscuro sobre fondo oscuro. El 62% no falsea la
                    #    lectura: todas las barras se escalan igual, así que
                    #    las proporciones entre filas se mantienen.
                    #    (`justifyContent` es obligatorio: el `display:flex`
                    #    de esta misma regla anula el alineado a la derecha
                    #    que trae `type: numericColumn`.)
                    _js_barra = JsCode(
                        "function(p){"
                        " var w = Math.max(0, Math.min(100, p.data._barra||0))"
                        " * 0.62;"
                        " return {'background': 'linear-gradient(90deg,"
                        f" {ACENTO} 0 ' + w + '%, transparent ' + w"
                        " + '% 100%)',"
                        " 'display':'flex','alignItems':'center',"
                        " 'justifyContent':'flex-end',"
                        f" 'color':'{TEXTO_PRINCIPAL}'"
                        "};"
                        "}")
                    _js_soles = JsCode(
                        "function(p){ return p.value==null ? '' :"
                        " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
                    _js_pct = JsCode(
                        "function(p){ return p.value==null ? '' :"
                        " Math.round(p.value) + '%'; }")
                    # Clic en la fila = TOGGLE. `enableClickSelection` va en
                    # False y la selección la maneja este handler: AG Grid, por
                    # sí solo, NO deselecciona al reclickear la fila ya
                    # seleccionada (pide Ctrl+clic, que nadie descubre).
                    # `setSelected(valor, true)` limpia las demás → sigue
                    # siendo selección única.
                    _js_toggle = JsCode(
                        "function(e){ e.node.setSelected(!e.node.isSelected(),"
                        " true); }")
                    _resp_rank = AgGrid(
                        _rk_df,
                        gridOptions={
                            "columnDefs": [
                                {"field": "Proveedor", "flex": 2,
                                 "tooltipField": "Proveedor"},
                                {"field": "Valor", "flex": 2,
                                 "type": "numericColumn",
                                 "cellStyle": _js_barra,
                                 "valueFormatter": _js_soles},
                                {"field": "Docs", "width": 80,
                                 "type": "numericColumn"},
                                {"field": "%", "width": 80,
                                 "type": "numericColumn",
                                 "valueFormatter": _js_pct},
                                {"field": "_barra", "hide": True},
                            ],
                            "rowSelection": {"mode": "singleRow",
                                             "checkboxes": False,
                                             "enableClickSelection": False},
                            "onRowClicked": _js_toggle,
                            "rowHeight": 35,
                            "headerHeight": 38,
                            "suppressCellFocus": True,
                            "suppressMovableColumns": True,
                        },
                        allow_unsafe_jscode=True,
                        theme="streamlit",
                        height=_ALTO_FRAME,
                        update_on=["selectionChanged"],
                        key=_rank_tab_key,
                    )
                    # ── El foco sale de la selección del grid ──────────────
                    # AgGrid devuelve la selección VIGENTE en cada run (no un
                    # evento), así que no hace falta dedup: alcanza con
                    # comparar contra el foco guardado. Selección vacía = el
                    # usuario reclickeó la fila (el toggle de arriba) y se
                    # quita el foco. "Otros" no es un proveedor real —agrupa a
                    # los que quedaron fuera— así que no abre drill.
                    _sel_rank = getattr(_resp_rank, "selected_rows", None)
                    if _sel_rank is not None and len(_sel_rank):
                        _fila = (_sel_rank.iloc[0] if hasattr(_sel_rank, "iloc")
                                 else _sel_rank[0])
                        _clicked = str(_fila["Proveedor"])
                    else:
                        _clicked = None
                    if _clicked == "Otros":
                        _clicked = prov_focus          # ignorar: no cambia nada
                    if _clicked != prov_focus:
                        prov_focus = _clicked
                        prod_focus = None
                        st.session_state["compras_prov_focus"]     = prov_focus
                        st.session_state["compras_prov_prodfocus"] = None
                        # El período ya no sale de esta tabla (el ranking no
                        # tiene eje de tiempo): lo fija el de evolución.
                        st.session_state["compras_prov_perfocus"]  = None
            with _c_evo:
                # ── BLOQUE 2: la evolución, con su propio período ──
                with st.container(border=True,
                                  key="compras_prov_card_evo"):
                    # Sin elección del usuario cae al primero del ranking (el de
                    # mayor valor) — mismo criterio que el Panel B de abajo.
                    # `_rk_nombres` viene ordenado DESCENDENTE (mayor primero,
                    # el orden natural de la tabla-ranking de al lado), así que
                    # el mayor es directamente el primero.
                    _prov_evo = prov_focus
                    if _prov_evo is None:
                        _reales = [p for p in _rk_nombres if p != "Otros"]
                        _prov_evo = _reales[0] if _reales else None
                    if _prov_evo is None:
                        st.caption("Sin proveedores en el rango.")
                    else:
                        # ── El período de ESTA tarjeta, elegido por el usuario ──
                        # Antes acá había una heurística muda: si el rango de la
                        # franja daba menos de 2 períodos (un mes, o un año en
                        # granularidad Año), la evolución se pasaba sola al
                        # histórico completo — una línea de un punto no dibuja
                        # ninguna evolución (reportado con captura). Acertaba,
                        # pero el usuario se enteraba DESPUÉS, por el caption.
                        #
                        # Desde 2026-08-18 la ventana es un control suyo
                        # (`graficos/periodo.py`): el ranking de al lado sigue
                        # mirando el rango de la franja y la evolución mira lo
                        # que le pidan. Son dos preguntas distintas —"quién pesa
                        # más ACÁ" y "cómo viene este proveedor"— y ahora cada
                        # una tiene su eje de tiempo, en vez de compartir uno y
                        # corregirlo a escondidas.
                        # El título se reserva ANTES del selector y se
                        # rellena al final: nombra la ventana, así que no puede
                        # escribirse hasta saber cuál eligió el usuario, pero
                        # tiene que DIBUJARSE arriba de él (si no, la columna de
                        # la evolución arranca con unas pills sueltas y su título
                        # deja de alinear con el del ranking de al lado).
                        _ph_tit_evo = st.empty()
                        # 2026-08-23, a pedido ("quita el texto que dice
                        # Rango, todo minimalista"): la pill de heredar el
                        # rango de la franja pasa a un ícono — el valor
                        # sigue siendo la cadena "Rango" (periodo.HEREDA),
                        # solo cambia lo que se VE.
                        _op_evo = periodo.selector(
                            "cp_evo_periodo",
                            format_func=lambda o: (
                                "📅" if o == periodo.HEREDA else o))
                        _evo_hist = _op_evo != periodo.HEREDA
                        # 2026-08-23 (2), a pedido ("que no estén arriba de
                        # Evolución sino que estén dentro... eliges si van
                        # sobre el gráfico interno o debajo, pero dentro de
                        # la tarjeta"): `gran_float` (Día/Semana/Mes/Año) y
                        # `win_nav` (‹ Auto/N/Todo ›) se mudan ACÁ, arriba
                        # del `st.plotly_chart` — mismo lugar que
                        # `cp_evo_periodo`, para que las tres filas de
                        # controles de tiempo de esta tarjeta queden
                        # juntas. La vuelta anterior (el caption "Agrupado
                        # por X") ya no hace falta: el control real está
                        # ahora al lado, no hace falta resumirlo en texto.
                        #
                        # Los dos siguen siendo, de verdad, compartidos con
                        # el Ranking (`gran` entra en `_agregar_periodo()`
                        # para las dos columnas; `win_nav` solo afecta a
                        # Evolución hoy — ver arquitectura.md regla #176,
                        # segunda mitad). Vivir DENTRO de la tarjeta de
                        # Evolución es una eleccion de UBICACION visual, no
                        # cambia a qué datos afectan.
                        with st.container(key="gran_float"):
                            st.pills("Periodo",
                                     ["Día", "Semana", "Mes", "Año"],
                                     default="Mes", key="compras_prov_gran",
                                     label_visibility="collapsed")

                        def _win_mover(_delta):
                            st.session_state["cp_prov_win_ini"] = min(
                                max(0, _win_ini + _delta), _ini_max)

                        def _win_size(_n):
                            st.session_state["cp_prov_win_size"] = _n

                        with st.container(key="win_nav"):
                            st.button("‹", key="cp_win_prev",
                                      disabled=_win_ini <= 0,
                                      help="Periodos anteriores",
                                      on_click=_win_mover, args=(-_ventana,))
                            # Pill activo marcado via <style> con la key
                            # exacta (no se puede aplicar :active desde
                            # Python porque Streamlit re-renderiza).
                            _sel_key = (
                                "cp_win_auto" if _win_size_sel is None
                                else "cp_win_all" if _win_size_sel == _n_per
                                else f"cp_win_{int(_win_size_sel)}")
                            st.markdown(
                                f"<style>.st-key-{_sel_key} button{{"
                                f"background:#6c5ce7 !important;"
                                f"color:#fff !important;"
                                f"border-color:#6c5ce7 !important;"
                                f"box-shadow:0 2px 5px rgba(76,60,180,0.28),"
                                f"inset 0 1px 0 rgba(255,255,255,0.18) "
                                f"!important;}}</style>",
                                unsafe_allow_html=True)
                            st.button(f"Auto {_ventana_auto}",
                                      key="cp_win_auto",
                                      on_click=_win_size, args=(None,))
                            for _op in (1, 2, 3, 6, 12, 24):
                                if _op < _n_per:
                                    st.button(str(_op), key=f"cp_win_{_op}",
                                              on_click=_win_size, args=(_op,))
                            st.button(f"Todo {_n_per}", key="cp_win_all",
                                      on_click=_win_size, args=(_n_per,))
                            st.button("›", key="cp_win_next",
                                      disabled=_win_ini >= _ini_max,
                                      help="Periodos siguientes",
                                      on_click=_win_mover, args=(_ventana,))
                        _src_evo = base
                        if _evo_hist and d_full is not None and col_fecha:
                            # La ventana se recorta sobre `d_full` (sin el filtro
                            # de fecha de la franja) ANTES de agrupar por período:
                            # recortar después dejaría los períodos del borde
                            # partidos a la mitad.
                            _d_evo = periodo.recortar(d_full, col_fecha, _op_evo)
                            # `cant` y `docu` no los usa la línea, pero sí el
                            # resumen de abajo: tiene que poder sumar sobre la
                            # MISMA fuente que el gráfico que resume.
                            _bf = pd.DataFrame({
                                "prov":  _d_evo[col_prov].astype(str).values,
                                "valor": pd.to_numeric(_d_evo[col_valor],
                                                       errors="coerce").fillna(0).values,
                                "cant":  (pd.to_numeric(_d_evo[col_cant],
                                                        errors="coerce").fillna(0).values
                                          if col_cant else 0.0),
                                "docu":  (_d_evo[col_docu].astype(str).values
                                          if col_docu else ""),
                                "fecha": pd.to_datetime(_d_evo[col_fecha],
                                                        errors="coerce").values,
                            })
                            _bf = _agregar_periodo(
                                _bf[_bf["prov"].notna() & (_bf["prov"] != "nan")])
                            if not _bf.empty:
                                _src_evo = _bf
                            else:
                                _evo_hist = False
                        _per_evo = (_src_evo[["_per_sort", "per"]].drop_duplicates()
                                    .sort_values("_per_sort")["per"].tolist())
                        _per_evo = list(dict.fromkeys(_per_evo))
                        _serie_evo = (_src_evo[_src_evo["prov"] == _prov_evo]
                                      .groupby("per")["valor"].sum()
                                      .reindex(_per_evo, fill_value=0))
                        # Con ventana propia se dibuja lo que el usuario pidió,
                        # entero: acá vivía un `tail(12)` fijo que tenía sentido
                        # cuando la fuente era "todo el histórico" y nadie la
                        # había elegido, pero ahora contradiría al selector (pedir
                        # 24m y ver 12 puntos). Las flechas de ventana (`_sl`) son
                        # del RANGO, así que solo se aplican cuando la tarjeta
                        # hereda el rango.
                        if _evo_hist:
                            _evo_x = list(_serie_evo.index)
                            _evo_y = [float(v) for v in _serie_evo.values]
                        else:
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
                        # Etiquetas del eje X: las "2026-08" se pisan entre sí
                        # y quedan ilegibles (reportado con captura). Dos cosas
                        # juntas: se acortan a "ago 26" y se muestra UNA CADA N.
                        # El punto sin etiqueta sigue estando en el hover, que
                        # trae el período completo.
                        _MES_AB = ("ene", "feb", "mar", "abr", "may", "jun",
                                   "jul", "ago", "sep", "oct", "nov", "dic")

                        def _etq_evo(_p):
                            _t = str(_p)
                            if gran == "Mes" and len(_t) == 7 and _t[4] == "-":
                                try:
                                    return f"{_MES_AB[int(_t[5:]) - 1]} {_t[2:4]}"
                                except (ValueError, IndexError):
                                    return _t
                            return _t

                        # El paso sale del ANCHO real, no de un divisor fijo.
                        # Acá había un `// 6` calibrado contra los ~380px que
                        # medía esta figura antes de que el 2026-08-19 su
                        # columna se partiera en [2.6, 1] para poner los KPIs
                        # al costado. Nadie revisó el número: quedó pidiendo 5
                        # etiquetas en 206px, y las CUATRO parejas se pisaban
                        # (-1 a -5px, medido en el navegador). Con el ancho de
                        # verdad da 4 y el peor hueco pasa a +11px.
                        _tickf_evo = 13
                        _etqs_evo = [_etq_evo(x) for x in _evo_x]
                        _paso_evo = paso_etiquetas(
                            len(_evo_x),
                            max((len(e) for e in _etqs_evo), default=1),
                            ancho=_ANCHO_EVO, px_fuente=_tickf_evo)
                        _tickv = [x for i, x in enumerate(_evo_x)
                                  if i % _paso_evo == 0]
                        # La fila de pills sale del MISMO presupuesto que la
                        # figura (alturas.py § LO QUE LA FIGURA NO ES): sin la
                        # resta, la columna de la evolución crece 42px contra la
                        # del ranking y la tarjeta empuja su propio borde.
                        _compras_layout(fig_evo, alto=_ALTO_EVO)
                        fig_evo.update_layout(
                            margin=dict(l=10, r=10, t=6, b=10),
                            # size=10 (reportado "casi no se ven"): es el mismo
                            # oscuro que el resto de la app (rgb(49,51,63), sin
                            # problema de contraste — medido), pero en una caja
                            # de 32x13px era chico de mas. 13, no 10, para que
                            # sean el UNICO texto legible de este grafico sin
                            # pasar el mouse (el eje Y va sin numeros a
                            # proposito, el valor de cada punto vive en el
                            # hover).
                            xaxis=dict(type="category", tickangle=0,
                                       tickmode="array", tickvals=_tickv,
                                       ticktext=[_etq_evo(x) for x in _tickv],
                                       tickfont=dict(size=13)),
                            # Acá el eje Y SÍ son valores, así que se respeta la
                            # convención del proyecto y va sin etiquetas: cada
                            # punto trae su monto en el hover.
                            yaxis=dict(showticklabels=False),
                            showlegend=False,
                            hovermode="x unified",
                        )
                        # El sufijo lo pone el propio módulo del período: es
                        # la misma opción escrita en prosa ("últimos 12 meses"),
                        # no un texto paralelo que un día quede desfasado del
                        # control que tiene tres píxeles más arriba.
                        _et_evo = periodo.etiqueta(_op_evo)
                        # Un punto suelto no dibuja ninguna evolución. Antes eso
                        # se corregía solo (se saltaba al histórico sin avisar);
                        # ahora la ventana la eligió el usuario, así que la salida
                        # correcta es DECIRLO y dejarle los controles que lo
                        # arreglan, no pasar por encima de lo que pidió. Va en el
                        # sufijo del título y no en un `st.caption` porque el
                        # caption medía 41px (dos líneas en una columna de 399) y
                        # empujaba la tarjeta a scroll interno: el aviso de que
                        # algo no se ve terminaba tapando lo que sí se veía.
                        # Acá cuesta cero alto y queda pegado a las pills que lo
                        # resuelven, que están tres píxeles más abajo.
                        _suf_evo = " · ".join(
                            x for x in (_et_evo,
                                        "1 solo período" if len(_evo_x) < 2 else "")
                            if x)
                        _ph_tit_evo.markdown(
                            f'<div class="cp-evo-tit">Evolución · '
                            f'{_compras_truncar(_prov_evo, 22)}'
                            + (f'<span> · {_suf_evo}</span>' if _suf_evo else '')
                            + '</div>',
                            unsafe_allow_html=True)
                        # 2026-08-19, a pedido: el resumen deja de ir DEBAJO
                        # del gráfico y pasa a su COSTADO, en columna. Gana el
                        # gráfico (recupera los ~97px de alto que le comía el
                        # bloque) y gana el resumen (4 cifras en vertical se
                        # leen de un barrido, no en un 2x2 que obliga a saltar
                        # en zigzag). Es un nivel de anidado de columnas —
                        # Streamlit permite exactamente uno, así que acá se
                        # agota: si algún día hay que subdividir otra vez,
                        # tiene que ser con contenedores, no con más columnas.
                        # 2.6/1 y no 2/1: medido, con 2/1 el gráfico quedaba
                        # en 243px para 13 puntos y la columna de cifras
                        # sobraba (la más ancha, "S/ 20,711", pide ~86 y
                        # tenía 117). El gráfico es el protagonista.
                        # columnas-internas: el chart y su pila de KPIs parten
                        # DENTRO de una tarjeta. No es el eje de la página,
                        # que lo manda COLUMNAS_DRILL.
                        _c_graf, _c_kpi = st.columns([2.6, 1], gap="small")
                        with _c_graf:
                            st.plotly_chart(
                                fig_evo, width="stretch",
                                key=f"cp_evo_{gran}_{_prov_evo}",
                                config={"displayModeBar": False},
                            )
                        # ── Resumen del proveedor ───────────────────────────
                        # Resume el ÚLTIMO período de la granularidad vigente (a
                        # pedido), no todo el tramo dibujado: es el último punto
                        # de la línea de arriba, o sea "cómo le fue el último
                        # mes / semana / año". El período se imprime en el
                        # encabezado — sin eso, "S/ 2,104" no dice contra qué.
                        #
                        # Sale de `_src_evo`, la MISMA fuente que la línea (rango
                        # o histórico según el caso). Un resumen pegado a un
                        # gráfico tiene que sumar lo que ese gráfico muestra, o
                        # los números contradicen a la curva que tienen encima.
                        if _evo_x:
                            with _c_kpi:
                                _per_ult = _evo_x[-1]
                                _ult = _src_evo[_src_evo["per"] == _per_ult]
                                _f_evo = _ult[_ult["prov"] == _prov_evo]
                                _r_val = float(_f_evo["valor"].sum())
                                _r_cant = (float(_f_evo["cant"].sum())
                                           if "cant" in _f_evo.columns else 0.0)
                                _r_docs = (int(_f_evo["docu"].replace("", pd.NA)
                                               .dropna().nunique())
                                           if "docu" in _f_evo.columns else 0)
                                # El % se mide contra lo comprado a TODOS los
                                # proveedores en ese mismo período: "de lo que gasté
                                # este mes, tanto fue con este proveedor".
                                _tot_ult = float(_ult["valor"].sum()) or 1.0
                                _r_pct = _r_val / _tot_ult * 100
                                _celdas = [("Total compra", f"S/ {_r_val:,.0f}"),
                                           ("% del total", f"{_r_pct:.1f}%"),
                                           ("Cantidad", f"{_r_cant:,.0f}"),
                                           ("Documentos", f"{_r_docs:,.0f}")]
                                st.markdown(
                                    f'<div class="cp-evo-kpis-tit">'
                                    # "Semana" es femenino y las otras tres no: sin
                                    # esto salia "Último semana".
                                    f'{"Última" if gran == "Semana" else "Último"} '
                                    f'{gran.lower()} · {_etq_evo(_per_ult)}</div>'
                                    '<div class="cp-evo-kpis">'
                                    + "".join(f'<div><span>{_k}</span><b>{_v}</b></div>'
                                              for _k, _v in _celdas)
                                    + '</div>', unsafe_allow_html=True)
        # 2026-08-23: `win_nav` (‹ Auto/N/Todo ›, navegación de la ventana de
        # períodos) se movió DENTRO de la tarjeta de Evolución, junto con
        # `gran_float` — ver ese bloque, debajo de `cp_evo_periodo`. Sigue
        # siendo lectura/escritura de `_win_ini`/`_ventana`/etc., calculados
        # arriba: mover DÓNDE se dibuja el control no cambia CUÁNDO corren
        # sus callbacks (Streamlit los corre antes del script, no en el
        # orden de render) ni qué valores ve — Python normal, un solo scope.

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
    #    fila del ranking lo abre; destildar el checkbox de esa fila lo
    #    cierra. La tarjeta vive en una funcion local
    #    para NO re-indentar su cuerpo; se llama abajo solo si hay proveedor
    #    en foco.
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
        # 2026-08-21: los paneles A/B eran UNA tarjeta ancha
        # (`compras_prov_card_paneles`) partida al 50% con dos `_card`
        # transparentes adentro, mientras la fila de arriba son DOS tarjetas
        # partidas al 61.5%. El ojo veía dos cajas arriba y una abajo, con el
        # canal gris cortado a media página y el eje corrido ~150px en un
        # viewport de 1536 (~200 en uno de 1920, crece con el ancho). Ahora son
        # cuatro bloques `compras_prov_card_*` sobre la MISMA grilla, así que
        # la vista se lee como un 2x2. Ver `_comun.COLUMNAS_DRILL`.
        pa, pb = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)

        # Panel A: Top N productos del proveedor en foco
        with pa:
            with st.container(border=True, key="compras_prov_card_prods"):
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
                                # Mismo frame de 8 filas que el ranking de
                                # arriba (`_ALTO_FRAME`), y por el mismo
                                # motivo: con `por_filas(len(tv), ...)` el
                                # alto salía de los datos — 80px con 1
                                # producto, 430 con 12 — y la tarjeta cambiaba
                                # de tamaño en cada clic del ranking. Lo que
                                # no entra scrollea DENTRO.
                                height=_ALTO_FRAME,
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
            with st.container(border=True, key="compras_prov_card_provde"):
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

    # -- Visibilidad del detalle A/B = hay proveedor en foco. Sin pestillo: lo
    #    abre un clic en la fila del ranking, lo cierra el botón "✕ Quitar
    #    foco" (junto al título de la tabla-ranking, más arriba).
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
