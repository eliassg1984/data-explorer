"""
graficos.recetaventa — dashboard de gráficos de Receta Venta.

Cada fila de recetaventa.parquet es un ÍTEM de un plato:
    Nomb Plato · Item Rv · Cantidad · Total
    (plato)      (insumo)  (cant.)    (costo del insumo en el plato)

Este módulo es la capa FINA de Receta Venta: resuelve las columnas reales
del parquet y llama a los gráficos compartidos de `graficos.recetas_comun`
(Ingredientes clave, Panorama de compras) — cada uno vive ahí UNA sola vez,
junto con la versión de `recetabase.py` (el mismo tipo de dato: un BOM
plato→insumos vs. receta base→insumos). Desde 2026-08-13 Receta Base y
Receta Venta comparten ítem de nav ("Recetas") y un chip Base/Venta arriba
del rail — ver `_chip_fuente` en recetas_comun.py y `arquitectura.md` §
Unificación Recetas.

"Composición" DEJÓ de ser compartida el 2026-08-24: acá es
`_tabla_composicion_venta`, una tabla propia (no una dona de un plato) con
columnas — Grupo/Subgrupo/P.VENTA SALON/CST SALON/%CST SALON — que no
existen en recetabase.parquet. El chip Base/Venta/Nueva no se muestra en
esta vista (no hay a qué "Base" equivalente navegar). Ver docstring de la
función.

Y desde el 2026-08-28, Composición pasó a ser SOLO de Receta Venta:
Receta Base se quedó con Ranking (hoy Costeo, ver más abajo), Insumos
clave, Panorama y Tabla (regla #236).

Y desde el 2026-08-30, "Ranking de platos" se renombra a "Costeo Receta
Venta" y deja el gráfico de barras horizontal por una tabla AgGrid propia
(`_tabla_costeo_venta`, más abajo) — a pedido: "en lugar de un gráfico,
una tabla tipo ranking, ordenada por costo, algo así como el que tengo
para compras". Mismo lenguaje visual que el Ranking de Proveedores de
Compras (barra como fondo de celda vía `linear-gradient`, fila TOTAL
fijada abajo) y misma agregación que el gráfico que reemplaza (suma de
costo/cantidad por plato, sin filtrar por activo). Sigue sin ser un quinto
compartido en `recetas_comun.py`: sólo Receta Venta pidió el cambio, así
que Receta Base se queda con el gráfico (`_ranking_contenedores`), que
conserva el nombre "Ranking".

Y el mismo 2026-08-30, más tarde, el Sankey se da de baja de Receta Venta
a pedido — con él se van el selector "Plato" (existía sólo para
alimentarlo, nada más lo usaba) y el drill "Abrir Sankey →" del Panorama
de compras (era sólo un atajo hacia esta vista). `_sankey_contenedor` se
BORRA de `recetas_comun.py`: Receta Base ya no lo llamaba desde el #236,
así que este dashboard era su último llamador — mismo criterio que se
aplicó con `_composicion_contenedor` esa vez (ver el docstring de
recetas_comun.py). El Panorama de compras conserva su PROPIO Sankey
(Producto→Plato, `_fig_panorama_sankey`): es un gráfico distinto, con otro
propósito, no tocado por este cambio.

Punto de entrada público: renderizar_graficos_recetaventa().
"""

import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, JsCode

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA, ERROR, EXITO, LAVANDA_CHIP,
    TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import (
    _card, _render_rail, _resolver, renderizar_graficos_genericos,
    seccion_perezosa,
)
from graficos.recetas_comun import (
    _activo, _chip_fuente, _items_clave, _panorama_compras,
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
    ("Vista", (("Composición del plato",   "Composición"),
               ("Costeo Receta Venta",     "Costeo Receta Venta"),
               ("Ingredientes clave",      "Ingredientes"),
               ("Panorama de compras",     "Panorama"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — gemela de la de `graficos/recetabase.py` (los dos
# reportes comparten ítem de nav y casi todos los gráficos, ver
# recetas_comun.py). El porqué de que sección y vista vivan en la MISMA
# tupla está en `graficos/compras/__init__.py::_PILA`.
_PILA = (
    ("rv_sec_composicion", "Composición del plato"),
    ("rv_sec_costeo",      "Costeo Receta Venta"),
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
        col_contenedor_out="Plato",
        etiqueta_contenedor_plural="platos activos",
        # Sin `nombre_vista_sankey`/`clave_seccion_sankey`: este dashboard ya
        # no tiene Sankey (dado de baja el 2026-08-30), así que
        # `_panorama_compras` deja el drill de insumo a lo ancho — mismo
        # criterio que `_panorama_compras_base`.
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
# COD INS (0 variación en 1.058 códigos). "Ingredientes clave" (vía
# recetas_comun.py) todavía agrupa por ITEM RV — bug preexistente, fuera
# del alcance de este cambio, no tocado acá. "Costeo Receta Venta" (antes
# "Ranking") ya usa INS RV y no ITEM RV desde que se armó como tabla — ver
# `_tabla_costeo_venta`, más abajo.
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


# ─── Costeo Receta Venta: ranking de platos por costo, en tabla ────────────
# Reemplaza el gráfico de barras horizontales que tenía esta vista hasta el
# 2026-08-30 (a pedido: "en lugar de un gráfico, una tabla tipo ranking,
# ordenada por costo, algo así como el que tengo para compras" — ver
# graficos/compras/proveedor.py, Ranking de Proveedores, mismo lenguaje
# visual: barra como FONDO de celda vía `linear-gradient`, fila TOTAL
# fijada abajo). Misma agregación que el gráfico que reemplazaba — suma de
# `col_valor` por plato, SIN filtrar por activo (ese filtro tampoco lo
# tenía `_ranking_contenedores`) — así que los números no cambian, sólo
# cómo se dibujan.
#
# NO vive en recetas_comun.py como los otros 3 gráficos compartidos
# (Sankey/Ingredientes clave/Panorama): sólo Receta Venta pidió el cambio,
# y Receta Base se queda con el gráfico de barras compartido
# (`_ranking_contenedores`) — mismo criterio que `_tabla_composicion_venta`,
# arriba.
#
# Ancho de columnas: FIJO en las cuatro, ninguna con `flex` — arquitectura.md
# regla #193 (`st_aggrid` inyecta `width: 200` a toda columna sin uno
# propio, y ese ancho explícito le gana al `flex` en el render inicial; el
# Ranking de Proveedores "funciona" con flex sólo porque nunca cruzó el
# umbral de columnas — la regla #193 lo llama "el bug dormido").
def _tabla_costeo_venta(df_f, col_plato, col_valor, es_soles):
    """Vista 'Costeo Receta Venta': ranking de platos por costo (o
    cantidad) total, en una tabla AgGrid — mismo lenguaje visual que el
    Ranking de Proveedores de Compras."""
    # INS RV, no ITEM RV, para el conteo de insumos: ITEM RV es el número
    # de LÍNEA dentro de la receta, no una identidad de insumo — ver
    # arquitectura.md regla #205 (punto 2). Columna opcional: si no está
    # (p.ej. un export viejo), la tabla se queda sin "Ítems" en vez de
    # romperse, mismo criterio defensivo que el resto del dashboard.
    col_ins = _resolver(df_f, ["INS RV", "Ins Rv"])

    agg = {"Plato": (col_plato, "first"), "Valor": (col_valor, "sum")}
    if col_ins:
        agg["Items"] = (col_ins, "nunique")
    g = df_f.groupby(col_plato, as_index=False).agg(**agg)
    g["Plato"] = g["Plato"].astype(str)
    g = g.sort_values("Valor", ascending=False).reset_index(drop=True)
    if g.empty:
        st.info("Sin datos para el ranking.")
        return

    total_valor = float(g["Valor"].sum()) or 1.0
    g["Pct"] = g["Valor"] / total_valor * 100
    g_max = float(g["Valor"].max()) or 1.0
    g["_barra"] = g["Valor"] / g_max * 100

    etiqueta_valor = "Costo (S/)" if es_soles else "Cantidad"

    # La barra es el FONDO de la celda (mismo `linear-gradient` que el
    # Ranking de Proveedores/Productos de Compras, arquitectura.md regla
    # #136), escalada contra el MAYOR valor visible y topada al 62% del
    # ancho para que el texto —alineado a la derecha— nunca caiga encima.
    _js_barra = JsCode(
        "function(p){"
        " if (p.node.rowPinned) return {'display':'flex','alignItems':'center',"
        " 'justifyContent':'flex-end','fontWeight':'700'};"
        " var w = Math.max(0, Math.min(100, p.data._barra||0)) * 0.62;"
        " return {'background': 'linear-gradient(90deg,"
        f" {ACENTO} 0 ' + w + '%, transparent ' + w + '% 100%)',"
        " 'display':'flex','alignItems':'center','justifyContent':'flex-end',"
        f" 'color':'{TEXTO_PRINCIPAL}'"
        "};"
        "}")
    # Números redondos (sin decimales): mismo formato que ya mostraban las
    # barras del gráfico que esto reemplaza (`text=f"{pref}{v:,.0f}"`).
    if es_soles:
        _js_valor_fmt = JsCode(
            "function(p){ return p.value==null ? '' :"
            " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
    else:
        _js_valor_fmt = JsCode(
            "function(p){ return p.value==null ? '' :"
            " Math.round(p.value).toLocaleString('es-PE'); }")
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' : Math.round(p.value) + '%'; }")
    # Misma paleta que la fila TOTAL del Ranking de Proveedores.
    _js_fila_total = JsCode(
        "function(p){ if(p.node.rowPinned){ return {"
        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
        f"'color':'{ACENTO_TEXTO_OSCURO}',"
        f"'borderTop':'2px solid {ACENTO}'"
        "}; } }")

    # Sin filtro de platos en esta vista (a diferencia del Ranking de
    # Proveedores, que sí puede excluir algunos): la tabla siempre muestra
    # TODOS, así que el TOTAL es exacto (100.0%) y no la suma de redondeos
    # por fila.
    _fila_total = {"Plato": "TOTAL", "Valor": round(total_valor, 2), "Pct": 100.0}
    if col_ins:
        _fila_total["Items"] = int(g["Items"].sum())

    _ALTO_FILA = 28
    # 10 filas visibles + la fila TOTAL fijada + cabecera(34) + chrome del
    # tema (~8px). El resto de los platos scrollea DENTRO del grid — a
    # diferencia del gráfico que esto reemplaza, ya no hace falta un
    # selector "Mostrar N": acá el scroll hace ese trabajo (mismo criterio
    # que el Ranking de Proveedores de Compras).
    _ALTO_FRAME = alturas.por_filas(
        10, px_fila=_ALTO_FILA, extra=34 + 8 + _ALTO_FILA, minimo=0)

    columnas = [
        {"field": "Plato", "width": 420, "tooltipField": "Plato"},
        {"field": "Valor", "headerName": etiqueta_valor, "width": 160,
         "type": "numericColumn", "sort": "desc",
         "cellStyle": _js_barra, "valueFormatter": _js_valor_fmt},
    ]
    campos = ["Plato", "Valor"]
    if col_ins:
        columnas.append({"field": "Items", "headerName": "Ítems", "width": 90,
                         "type": "numericColumn"})
        campos.append("Items")
    columnas.append({"field": "Pct", "headerName": "%", "width": 80,
                     "type": "numericColumn", "valueFormatter": _js_pct})
    campos.append("Pct")
    columnas.append({"field": "_barra", "hide": True})
    campos.append("_barra")

    with _card("rv_costeo",
               f"Platos por {'costo' if es_soles else 'cantidad'} total"):
        AgGrid(
            g[campos],
            gridOptions={
                "columnDefs": columnas,
                "defaultColDef": {"sortable": True, "resizable": True},
                "suppressCellFocus": True,
                "suppressMovableColumns": True,
                "rowHeight": _ALTO_FILA,
                "headerHeight": 34,
                "pinnedBottomRowData": [_fila_total],
                "getRowStyle": _js_fila_total,
            },
            allow_unsafe_jscode=True,
            theme="streamlit",
            height=_ALTO_FRAME,
            key="rv_costeo_grid",
        )
        st.caption(f"{len(g)} platos · ordenado por {etiqueta_valor.lower()}")


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
    # Va arriba de la pila: la métrica manda sobre las demás secciones.
    # Meterlo adentro de una sección lo escondería hasta que esa sección
    # salga del esqueleto. El selector "Plato" que vivía acá al lado se fue
    # con el Sankey (2026-08-30): era su único lector.
    metricas = []
    if col_total:
        metricas.append("Costo (S/)")
    if col_cant:
        metricas.append("Cantidad")

    metrica = st.radio("Medir por", metricas, horizontal=True,
                       key="rv_metrica")
    es_soles = (metrica == "Costo (S/)")
    col_valor = col_total if es_soles else col_cant

    # ── LA PILA, PEREZOSA ────────────────────────────────────────────────
    # Cada sección lleva su PROPIA key de tarjeta: las seis compartían
    # `rv_graf_card` porque nunca coexistían. Y desaparece el sub-container
    # `rv_graf_body_<vista>`, que existía para forzar un remount limpio al
    # cambiar de rail (si no, los selectbox de drill del Panorama aparecían
    # también en Ranking) — con una sección por vista, cada una tiene su
    # propio sitio en el árbol y no hay nada que limpiar.
    def _dib_composicion():
        with st.container(border=True, key="rv_card_composicion"):
            _tabla_composicion_venta(df_f)

    def _dib_costeo():
        with st.container(border=True, key="rv_card_costeo"):
            _tabla_costeo_venta(df_f, col_plato, col_valor, es_soles)

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
        "rv_sec_composicion":  _dib_composicion,
        "rv_sec_costeo":       _dib_costeo,
        "rv_sec_ingredientes": _dib_ingredientes,
        "rv_sec_panorama":     _dib_panorama,
        "rv_sec_tabla":        _dib_tabla,
    }

    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
