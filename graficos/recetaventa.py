"""
graficos.recetaventa — dashboard de gráficos de Receta Venta.

Cada fila de recetaventa.parquet es un ÍTEM de un plato:
    Nomb Plato · Item Rv · Cantidad · Total
    (plato)      (insumo)  (cant.)    (costo del insumo en el plato)

Este módulo es la capa FINA de Receta Venta: resuelve las columnas reales
del parquet y llama a 4 de los 5 gráficos compartidos de
`graficos.recetas_comun` (Sankey, Ranking, Ingredientes clave, Panorama de
compras) — cada uno vive ahí UNA sola vez, junto con la versión de
`recetabase.py` (el mismo tipo de dato: un BOM plato→insumos vs. receta
base→insumos). Desde 2026-08-13 Receta Base y Receta Venta comparten ítem
de nav ("Recetas") y un chip Base/Venta arriba del rail — ver
`_chip_fuente` en recetas_comun.py y `arquitectura.md` § Unificación
Recetas.

El quinto ("Composición") DEJÓ de ser compartido el 2026-08-24: acá es
`_tabla_composicion_venta`, una tabla propia (no una dona de un plato) con
columnas — Grupo/Subgrupo/P.VENTA SALON/CST SALON/%CST SALON — que no
existen en recetabase.parquet. Receta Base conserva la dona compartida
(`_composicion_contenedor`). El chip Base/Venta/Nueva no se muestra en
esta vista (no hay a qué "Base" equivalente navegar). Ver docstring de la
función.

Punto de entrada público: renderizar_graficos_recetaventa().
"""

import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, JsCode

from tema import ADVERTENCIA, ERROR, EXITO, TEXTO_PRINCIPAL
from graficos import alturas
from graficos.base import (
    _card, _render_rail, _resolver, renderizar_graficos_genericos,
    seccion_perezosa,
)
from graficos.recetas_comun import (
    _activo, _chip_fuente, _items_clave, _panorama_compras,
    _ranking_contenedores, _sankey_contenedor,
)

# Umbral de %Costo salón para el semáforo de la barra de progreso de
# Composición (más abajo): mismo criterio que ya usa formulario_receta.py
# para juzgar el % de costo de una receta nueva (🟢/🟠/🔴) — no vive en un
# módulo compartido porque son dos herramientas separadas (ésta lee
# recetaventa.parquet, aquélla arma una receta a mano) que coinciden en la
# misma referencia de negocio, no en código que debieran compartir.
_UMBRAL_COSTO_OK = 30
_UMBRAL_COSTO_WARN = 35

_RAIL_CATEGORIAS = (
    ("Vista", (("Sankey por plato",        "Sankey"),
               ("Composición del plato",   "Composición"),
               ("Ranking de platos",       "Ranking"),
               ("Ingredientes clave",      "Ingredientes"),
               ("Panorama de compras",     "Panorama"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — gemela de la de `graficos/recetabase.py` (los dos
# reportes comparten ítem de nav y casi todos los gráficos, ver
# recetas_comun.py). El porqué de que sección y vista vivan en la MISMA
# tupla está en `graficos/compras/__init__.py::_PILA`.
_PILA = (
    ("rv_sec_sankey",      "Sankey por plato"),
    ("rv_sec_composicion", "Composición del plato"),
    ("rv_sec_ranking",     "Ranking de platos"),
    ("rv_sec_ingredientes", "Ingredientes clave"),
    ("rv_sec_panorama",    "Panorama de compras"),
    ("rv_sec_tabla",       "Tabla"),
)


def _panorama_compras_venta(df_f, es_soles):
    _panorama_compras(
        df_f, es_soles, key_prefix="rv",
        col_cod_ins_cand=["COD INS", "Cod Ins"],
        col_contenedor_cand=["Nomb Plato", "Nombre Plato", "PLATO", "Plato"],
        col_valor_cand=["Total", "TOTAL", "Importe", "Costo Total"],
        col_cant_cand=["Cantidad", "CANTIDAD", "Cant"],
        col_activo_contenedor_cand=["ITEM VENTA ACTIVO", "Item Venta Activo"],
        col_activo_item_cand=["INS ACTIVO", "Ins Activo"],
        etiqueta_otros_contenedor="Otros platos",
        titulo_card="Productos comprados → platos que los usan",
        state_key_rail="rv_graf_tipo",
        nombre_vista_sankey="Sankey por plato",
        col_contenedor_out="Plato",
        etiqueta_contenedor_plural="platos activos",
        etiqueta_selectbox_jump="Ver el flujo completo de un plato",
        # Página APILADA: el Sankey ya está más arriba, así que "Abrir
        # Sankey →" scrollea en vez de cambiar de vista. Ver
        # `recetas_comun._drill_contenedor_jump`.
        clave_seccion_sankey="rv_sec_sankey",
    )


# ─── Composición: tabla de platos + drill a su receta ──────────────────────
# 2026-08-24, a pedido: reemplaza la dona de UN plato (`_composicion_
# contenedor`, compartida con Receta Base) por una tabla de TODOS los
# platos activos con Grupo/Subgrupo/Precio/Costo/%Costo de Salón — la dona
# "no mostraba mucho" (un plato a la vez, elegido a mano). NO vive en
# recetas_comun.py como los otros 4 gráficos compartidos: GRUPO, SUBGRUPO,
# P.VENTA SALON, CST SALON y %CST SALON no tienen equivalente en
# recetabase.parquet (25 columnas, esquema RB NOMBRE/INSUMO/CST SUBT INS —
# ver docstring de recetabase.py), así que Receta Base sigue con la dona.
#
# P.VENTA SALON / CST SALON / %CST SALON son atributos del PLATO, no del
# ítem-insumo: confirmado contra R2 real (2026-08-24, DuckDB directo sobre
# recetaventa.parquet) que los 850 platos del catálogo tienen un único
# valor de los tres por COD PLATO, repetido en cada fila-insumo — mismo
# patrón que VALOR_ANO_ANTERIOR en compras.parquet (CLAUDE.md § "Antes de
# sumar una columna comparable"). Por eso se toman con `.first()` por
# plato, nunca `.sum()`. También confirmado que CST SALON == suma de
# TOTAL de los ítems de ese plato — la receta de la derecha y el costo de
# la izquierda siempre cuadran, sin filtrar por INS ACTIVO (CST SALON
# tampoco filtra por eso).
#
# El insumo de la receta se lee de INS RV, no de ITEM RV: verificado que
# ITEM RV es el número de LÍNEA dentro de la receta (001, 002…), no una
# identidad de insumo — el mismo COD INS aparece como "001" en un plato y
# "019" en otro. INS RV es el texto descriptivo, estable 1:1 contra
# COD INS (0 variación en 1.058 códigos). Los otros 4 gráficos de este
# dashboard (Sankey/Ranking/Ingredientes clave, vía recetas_comun.py)
# todavía agrupan por ITEM RV — bug preexistente, fuera del alcance de
# este cambio, no tocado acá.
def _tabla_composicion_venta(df_f):
    """Vista 'Composición': ranking de platos activos (AgGrid, barra de
    %Costo salón coloreada por umbral) + la receta del plato en foco en
    una tabla al lado, actualizada al hacer clic en una fila."""
    col_cod_plato = _resolver(df_f, ["COD PLATO", "Cod Plato"])
    col_plato = _resolver(df_f, ["NOMB PLATO", "Nombre Plato", "PLATO", "Plato"])
    col_grupo = _resolver(df_f, ["GRUPO", "Grupo"])
    col_subgrupo = _resolver(df_f, ["SUBGRUPO", "Sub Grupo", "Subgrupo"])
    col_precio = _resolver(df_f, ["P.VENTA SALON", "P VENTA SALON",
                                  "Precio Venta Salon", "PVENTA SALON"])
    col_costo = _resolver(df_f, ["CST SALON", "CST SALÓN", "Costo Salon"])
    col_pct = _resolver(df_f, ["%CST SALON", "% CST SALON", "PCT CST SALON",
                               "Pct Cst Salon"])
    col_activo = _resolver(df_f, ["ITEM VENTA ACTIVO", "Item Venta Activo"])
    col_ins = _resolver(df_f, ["INS RV", "Ins Rv"])
    col_cant = _resolver(df_f, ["CANTIDAD", "Cantidad"])
    col_total = _resolver(df_f, ["TOTAL", "Total"])

    faltan = [n for n, c in (
        ("Plato", col_plato), ("Grupo", col_grupo), ("Subgrupo", col_subgrupo),
        ("Precio Venta Salón", col_precio), ("Costo Salón", col_costo),
        ("%Costo Salón", col_pct),
    ) if not c]
    if not col_cod_plato or faltan:
        st.info(
            "No se reconocieron todas las columnas de Composición "
            f"({', '.join(faltan) or 'Cod Plato'}). Esta vista necesita "
            "Cod Plato, Grupo, Subgrupo, P.Venta Salón, Cst Salón y "
            "%Cst Salón de recetaventa.parquet."
        )
        return

    d = df_f
    if col_activo:
        d = d[_activo(d[col_activo])]
    if d.empty:
        st.info("Sin platos activos para mostrar.")
        return

    g = d.groupby(col_cod_plato, as_index=False).agg(
        Grupo=(col_grupo, "first"),
        Subgrupo=(col_subgrupo, "first"),
        Plato=(col_plato, "first"),
        Precio=(col_precio, "first"),
        Costo=(col_costo, "first"),
        Pct=(col_pct, "first"),
    )
    g["Grupo"] = g["Grupo"].fillna("").astype(str)
    g["Subgrupo"] = g["Subgrupo"].fillna("").astype(str)
    g["Plato"] = g["Plato"].astype(str)
    g["Precio"] = pd.to_numeric(g["Precio"], errors="coerce").fillna(0.0)
    g["Costo"] = pd.to_numeric(g["Costo"], errors="coerce").fillna(0.0)
    g["Pct"] = pd.to_numeric(g["Pct"], errors="coerce").fillna(0.0) * 100
    g["_cod"] = g[col_cod_plato].astype(str)

    # P.VENTA SALON trae un cluster de precios centinela (1e-12…1.00,
    # verificado contra R2 real: 15 de 436 platos activos, TODOS con un
    # precio "redondo" que ningún plato real usa — cortesías, mermas,
    # ítems de exhibición) que no son precios de venta reales. Sin este
    # filtro %Costo se dispara a millones por ciento (S/0.58 de costo
    # sobre S/0.000000000001 de "precio") y esos platos degenerados
    # tapan el top entero del ranking — verificado en vivo, ver
    # arquitectura.md regla #205. El corte en 1 es el que mide el hueco
    # real: 0 platos activos caen entre 1 y 7 soles.
    _n_sin_precio = int((g["Precio"] <= 1).sum())
    g = g[g["Precio"] > 1]
    if g.empty:
        st.info("Ningún plato activo tiene un precio de Salón configurado.")
        return
    g = g.sort_values("Pct", ascending=False).reset_index(drop=True)

    # La barra es el FONDO de la celda (mismo `linear-gradient` que el
    # ranking de Proveedor/Producto de Compras — arquitectura.md regla
    # #136), coloreado por el semáforo 30/35% de arriba en vez de un
    # accent fijo: acá el color ES el dato (qué tan caro sale el plato),
    # no solo un ranking relativo.
    _js_barra_pct = JsCode(
        "function(p){"
        " var w = Math.max(0, Math.min(100, p.value||0));"
        f" var c = w <= {_UMBRAL_COSTO_OK} ? '{EXITO}'"
        f" : w <= {_UMBRAL_COSTO_WARN} ? '{ADVERTENCIA}' : '{ERROR}';"
        " return {'background': 'linear-gradient(90deg, ' + c + ' 0 ' + w"
        " + '%, transparent ' + w + '% 100%)',"
        " 'display':'flex','alignItems':'center','justifyContent':'flex-end',"
        f" 'color':'{TEXTO_PRINCIPAL}'"
        "};"
        "}")
    _js_soles = JsCode(
        "function(p){ return p.value==null ? '' : 'S/ ' + p.value.toFixed(2); }")
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' : p.value.toFixed(1) + '%'; }")
    # Clic en la fila = toggle (mismo patrón que Compras › Proveedor/
    # Producto): AG Grid no deselecciona solo al reclickear la fila ya
    # elegida, y `st.dataframe` no sirve para esto — su columna de
    # selección se dibuja en un canvas, sin nodo que ocultar por CSS.
    _js_toggle = JsCode(
        "function(e){ e.node.setSelected(!e.node.isSelected(), true); }")

    _ALTO_FILA = 28
    _ALTO_FRAME = alturas.por_filas(8, px_fila=_ALTO_FILA, extra=45, minimo=0)

    # [5, 2] y no [2, 1]: con 6 columnas fijas (nunca `flex`, ver más abajo)
    # la tabla necesita todo el ancho que se le pueda dar — medido en el
    # navegador a 1280px con [2, 1]: el iframe de AgGrid quedaba en 498px
    # contra 820px de columnas, y %Costo (la columna que importa) caía
    # fuera de vista sin scrollear. Con [5, 2] sube a ~537px.
    c_tabla, c_receta = st.columns([5, 2], gap="medium")
    with c_tabla:
        with _card("rv_comp_tabla",
                   "Platos activos · % de costo sobre venta en Salón"):
            # Ancho FIJO en las 6 columnas, ninguna con `flex`: probado en
            # graficos/compras/producto.py (arquitectura.md regla #192) que
            # `st_aggrid` le clava `width: 200` a toda columna sin `width`
            # propio, y como AG Grid prioriza el `width` explícito para el
            # tamaño inicial, un `flex` mezclado con eso nunca reparte nada.
            #
            # %Costo va justo después de Plato, NO al final (pedido "Grupo,
            # Subgrupo, Plato, Precio, Costo, %Costo"): medido en el
            # navegador a 1280px, ese orden dejaba %Costo —la columna con
            # la barra, la razón de ser de esta vista— 75px afuera del
            # viewport visible del iframe (610px de columnas contra 537px
            # de ancho real), oculta sin scrollear. Grupo+Subgrupo+Plato+
            # %Costo suman 430px: entran holgados. Precio/Costo (detalle
            # de apoyo) son los que quedan a un scroll de distancia.
            resp = AgGrid(
                g[["Grupo", "Subgrupo", "Plato", "Pct", "Precio", "Costo", "_cod"]],
                gridOptions={
                    "columnDefs": [
                        {"field": "Grupo", "width": 90, "tooltipField": "Grupo"},
                        {"field": "Subgrupo", "width": 100,
                         "tooltipField": "Subgrupo"},
                        {"field": "Plato", "width": 160, "tooltipField": "Plato"},
                        {"field": "Pct", "headerName": "% Costo",
                         "width": 80, "type": "numericColumn",
                         "cellStyle": _js_barra_pct,
                         "valueFormatter": _js_pct},
                        {"field": "Precio", "headerName": "P. Venta Salón",
                         "width": 90, "type": "numericColumn",
                         "valueFormatter": _js_soles},
                        {"field": "Costo", "headerName": "Costo Salón",
                         "width": 90, "type": "numericColumn",
                         "valueFormatter": _js_soles},
                        {"field": "_cod", "hide": True},
                    ],
                    "defaultColDef": {"sortable": True, "resizable": True},
                    "rowSelection": {"mode": "singleRow", "checkboxes": False,
                                     "enableClickSelection": False},
                    "onRowClicked": _js_toggle,
                    "rowHeight": _ALTO_FILA,
                    "headerHeight": 34,
                    "suppressCellFocus": True,
                    "suppressMovableColumns": True,
                },
                allow_unsafe_jscode=True,
                theme="streamlit",
                height=_ALTO_FRAME,
                update_on=["selectionChanged"],
                key="rv_comp_grid",
            )
            _pie = "Clic en una fila para ver su receta →"
            if _n_sin_precio:
                _pie += f" · {_n_sin_precio} sin precio de Salón configurado, no se muestran"
            st.caption(_pie)

    sel = getattr(resp, "selected_rows", None)
    if sel is not None and len(sel):
        fila_sel = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
        clicked = str(fila_sel["_cod"])
    else:
        clicked = None
    # Sin clic (o reclic que deselecciona, ver `_js_toggle`): cae al primer
    # plato de la tabla, que por el sort de arriba es el de %Costo más
    # alto — el panel de la derecha nunca arranca vacío.
    foco = clicked if clicked else str(g["_cod"].iloc[0])
    fila_foco = g[g["_cod"] == foco]
    nombre_foco = str(fila_foco["Plato"].iloc[0]) if len(fila_foco) else ""

    with c_receta:
        with _card("rv_comp_receta",
                   f"Receta · {nombre_foco}" if nombre_foco else "Receta"):
            if not (col_ins and col_total):
                st.info("No se reconoció la columna de insumo (INS RV) o "
                       "de costo (TOTAL) para mostrar la receta.")
            else:
                items = df_f[df_f[col_cod_plato].astype(str) == foco]
                r = pd.DataFrame({
                    "Insumo": items[col_ins].astype(str),
                    "Cantidad": (pd.to_numeric(items[col_cant], errors="coerce")
                                if col_cant else None),
                    "Costo": pd.to_numeric(items[col_total], errors="coerce").fillna(0.0),
                })
                r = r.sort_values("Costo", ascending=False).reset_index(drop=True)
                tot_r = r["Costo"].sum() or 1.0
                r["%"] = r["Costo"] / tot_r * 100
                st.dataframe(
                    r, hide_index=True, use_container_width=True,
                    height=alturas.MINI,
                    column_config={
                        "Cantidad": st.column_config.NumberColumn(format="%.3f"),
                        "Costo": st.column_config.NumberColumn(format="S/ %.2f"),
                        "%": st.column_config.ProgressColumn(
                            format="%.1f%%", min_value=0, max_value=100),
                    },
                )


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_recetaventa(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Receta Venta. df_full se ignora (catálogo sin fecha).

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py), llamado
    SIN args — igual que Ajuste: este dashboard no tiene chips propios de
    filtro (a diferencia de Ventas/Inventario), así que la Tabla usa los
    filtros genéricos que ya arma app.py."""
    col_plato = _resolver(df_f, ["Nomb Plato", "Nombre Plato", "PLATO", "Plato"])
    col_item = _resolver(df_f, ["Item Rv", "Item RV", "ITEM RV", "Item",
                                "Nombre Item", "Insumo", "Ingrediente",
                                "Nombre Producto"])
    col_total = _resolver(df_f, ["Total", "TOTAL", "Importe", "Costo Total",
                                 "Total Costo", "Valorizado"])
    col_cant = _resolver(df_f, ["Cantidad", "CANTIDAD", "Cant"])

    # Necesitamos plato + ítem + al menos una métrica numérica.
    if not col_plato or not col_item or not (col_total or col_cant):
        st.warning(
            "No se reconocieron las columnas de Receta Venta (se buscó "
            "«Nomb Plato», «Item Rv», «Total», «Cantidad»). "
            "Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # El rail ya no ELIGE: con `secciones` marca dónde estás y scrollea.
    _render_rail(_RAIL_CATEGORIAS, "rv_graf_tipo", btn_prefix="rv_rail_btn_",
                 secciones=_PILA)

    # El chip Base/Venta/Nueva se dibuja SIEMPRE. Hasta el apilado se
    # escondía en la vista "Composición del plato" (a pedido 2026-08-24:
    # esa vista es una tabla propia de Receta Venta y navegar a Base desde
    # ahí no lleva a nada equivalente). Con la pila el argumento se cae
    # solo: Composición ya no es LA pantalla, es una sección más de una
    # página que en conjunto ES Receta Venta, y el chip es un control de la
    # página entera.
    _chip_fuente("Receta Venta")

    # ── Controles COMPARTIDOS por toda la página ─────────────────────────
    # Van arriba de la pila: la métrica manda sobre cuatro secciones y el
    # selector de plato sobre el Sankey. Meterlos adentro de una sección
    # los escondería hasta que esa sección salga del esqueleto.
    metricas = []
    if col_total:
        metricas.append("Costo (S/)")
    if col_cant:
        metricas.append("Cantidad")

    c_met, c_plato = st.columns([1, 2])
    with c_met:
        metrica = st.radio("Medir por", metricas, horizontal=True,
                           key="rv_metrica")
    es_soles = (metrica == "Costo (S/)")
    col_valor = col_total if es_soles else col_cant

    # Default: el plato de mayor costo, para que la primera vista sea rica.
    platos = sorted(df_f[col_plato].dropna().astype(str).unique().tolist())
    totales = df_f.groupby(col_plato)[col_valor].sum()
    plato_rico = str(totales.idxmax()) if not totales.empty else (platos[0] if platos else "")
    idx_def = platos.index(plato_rico) if plato_rico in platos else 0

    # Ya no hace falta el `with c_plato:` incondicional con el `if` adentro
    # (estaba para que Streamlit "visitara" la posición en todos los runs y
    # no dejara el selectbox de la vista anterior pegado y huérfano, visto
    # en vivo 2026-08-09 al pasar de Sankey a Ranking). Con la pila el
    # Sankey está SIEMPRE en la página, así que el selector se dibuja
    # siempre y el problema desaparece solo — igual que en Receta Base.
    with c_plato:
        plato = st.selectbox("Plato", platos, index=idx_def, key="rv_plato_sel")

    # ── LA PILA, PEREZOSA ────────────────────────────────────────────────
    # Cada sección lleva su PROPIA key de tarjeta: las seis compartían
    # `rv_graf_card` porque nunca coexistían. Y desaparece el sub-container
    # `rv_graf_body_<vista>`, que existía para forzar un remount limpio al
    # cambiar de rail (si no, los selectbox de drill del Panorama aparecían
    # también en Ranking) — con una sección por vista, cada una tiene su
    # propio sitio en el árbol y no hay nada que limpiar.
    def _dib_sankey():
        with st.container(border=True, key="rv_card_sankey"):
            _sankey_contenedor(df_f, col_plato, col_item, col_valor, plato,
                               es_soles, card_key="rv_sankey")

    def _dib_composicion():
        with st.container(border=True, key="rv_card_composicion"):
            _tabla_composicion_venta(df_f)

    def _dib_ranking():
        with st.container(border=True, key="rv_card_ranking"):
            _ranking_contenedores(df_f, col_plato, col_valor, es_soles,
                                  key_topn="rv_ranking_topn",
                                  card_key="rv_ranking",
                                  titulo_card="Platos por costo total")

    def _dib_ingredientes():
        with st.container(border=True, key="rv_card_ingredientes"):
            _items_clave(df_f, col_plato, col_item, col_valor, es_soles,
                        card_key="rv_ingredientes",
                        titulo_card="Ingredientes de mayor costo total",
                        etiqueta_item="Ingrediente",
                        etiqueta_contenedor_plural="platos",
                        expander_titulo="📋 Tabla: ingredientes por costo y n.º de platos")

    def _dib_panorama():
        with st.container(border=True, key="rv_card_panorama"):
            _panorama_compras_venta(df_f, es_soles)

    def _dib_tabla():
        with st.container(border=True, key="rv_card_tabla"):
            if tabla_cb is not None:
                # Sin chips propios (como Ajuste): pasa su df tal cual.
                tabla_cb(df_f)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "rv_sec_sankey":       _dib_sankey,
        "rv_sec_composicion":  _dib_composicion,
        "rv_sec_ranking":      _dib_ranking,
        "rv_sec_ingredientes": _dib_ingredientes,
        "rv_sec_panorama":     _dib_panorama,
        "rv_sec_tabla":        _dib_tabla,
    }

    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
