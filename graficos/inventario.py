"""
graficos.inventario — dashboard de Inventario Valorizado (v3). Layout unificado
con chips en franja blanca + card con pills.

v3 (2026-08-10) reemplaza las 4 vistas de v2 (Área y familia / Torta / Top
valor / Top cantidad) por 3: **Por área**, **Por familia** (mismo ranking
ordenado para las dos — desde 2026-08-23 una TABLA con barra de progreso en
la celda, como el Ranking de proveedores de Compras; la torta se rompía
apenas una familia concentraba >70% del total) y **Buscar producto**
(nueva: ficha de un producto puntual, o de un grupo — Subfamilia — completo,
con cantidad + valorizado + precio promedio + unidad de medida por área).
El KPI "Valorizado total" vivía DENTRO de la card izquierda (no en una
franja aparte arriba: se probó así y quedaba la card muy abajo). Se retiró
de las cuatro secciones el 2026-09-13, a pedido: en las dos de ranking lo
dice la fila TOTAL de la tabla, y en "Buscar producto" era el valorizado de
todo el inventario en una ficha de UN producto. Ver regla #404.
El panel lateral de la derecha (Mayor cantidad/Precio más alto)
se mantiene igual en Por área/Por familia, pero en Buscar producto pasa a
mostrar productos relacionados (misma subfamilia/familia) en vez de un top
genérico — repetir el mismo top ahí era redundante con lo que ya se ve a la
izquierda para el producto elegido.

2026-09-13, a pedido: Por área y Por familia son TABLAS de punta a punta, y
las tres son clickeables en cadena. Ranking (izquierda) → desglose del nivel
siguiente (derecha, era un `go.Bar` sin clic) → productos (franja de abajo),
que ahora lista TODOS los del recorte en vez de un top-20: "ya que es una
tabla, el usuario puede hacer scroll". Ver `arquitectura.md` regla #403.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, AJUSTE_NEG, LAVANDA_BORDE, LAVANDA_CHIP,
    TEXTO_PRINCIPAL,
)
# El LOOK de una tabla-ranking del repo. Nació en `proveedor.py`, se
# generalizó a los tres paneles del drill de Producto el 2026-09-11 ("que
# sean similares al de Ranking de Proveedores") y el 2026-09-13 cruza a
# Inventario con el mismo pedido. Se importa de Compras en vez de copiarse
# —o de mudarse a `tablas/_css.py` y `alturas.py`, que es donde terminará
# viviendo— porque el alto y el CSS son UNA sola decisión y hoy están
# juntos: partirlos en dos mudanzas es lo que deja una tabla a 24px de fila
# con el cuerpo de 12px de otro tema. Ver `arquitectura.md` regla #404.
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CROMO_GRID_RANK, unidad_corta,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills,
    _compras_layout, _compras_truncar, _render_rail,
    _resolver, _slug, publicar_contexto_ia, renderizar_graficos_genericos, seccion_perezosa,
)
from graficos import alturas

# Los títulos de las tarjetas de ranking, con los MISMOS cuatro valores que
# `.cp-rank-tit` de `graficos/compras/_css_proveedor.py`: las dos se mueven
# juntas. No se reusa aquella clase porque su regla vive dentro de un
# `<style>` de 2.400 líneas que estila el drill entero de Compras, y traerlo
# a Inventario para heredar cuatro propiedades sería peor que repetirlas.
# Va sin guard de "inyectar una sola vez" a propósito (regla #59).
CSS_TITULOS_INV = """
<style>
.inv-rank-tit { font-size: 16px; font-weight: 600; color: var(--text-primary);
                padding-left: 2px; margin: 0 0 4px;
                /* UNA linea, siempre. Con tres cuadros la ruta del titulo
                   crece ("ALMACEN CENTRAL > COSTOS PRODUCCION - por
                   subfamilia") y al pasar a dos renglones esa tarjeta media
                   334px contra los 308 de sus vecinas: dos tarjetas de la
                   misma fila tienen que medir lo mismo (regla #145). El
                   nombre completo queda en el `title=`. */
                white-space: nowrap; overflow: hidden;
                text-overflow: ellipsis; }
/* Cuantos productos hay: va en el titulo y no en un `st.caption` aparte
   (que sumaba un renglon a una tarjeta que se acaba de podar), pero con
   menos peso que el nombre. En una tabla que scrollea, sin el numero no se
   ve si son 12 productos o 400. */
.inv-rank-tit-n { font-size: 12px; font-weight: 500; opacity: .55;
                  margin-left: 6px; }
</style>
"""

# Con qué categoría ABRE "Por área" mientras nadie haya elegido otra
# (2026-09-13, a pedido: "abrir en almacen"). No es un filtro ni quita la
# elección — es dónde abre: un clic en cualquier otra fila la reemplaza, y
# soltarla vuelve acá. GASTOS es la mayor por valorizado (79%) pero no es
# inventario que se pueda contar en un estante, así que abrir ahí gastaba la
# primera pantalla en la categoría menos accionable. Ver regla #405.
#
# Es una tupla y no un string: si el nombre cambia en el ERP, el siguiente
# candidato sigue sirviendo sin tocar código. Si ninguno está en los datos,
# `_tabla_ranking` abre en la categoría mayor — nunca en vacío.
ABRE_EN_AREA = ("ALMACEN CENTRAL",)

# Reparto horizontal de la fila de arriba, por cantidad de cuadros.
#
# Con TRES el ranking cede: 1.2 y no 1.7. Medido en 1366x768, con (1.5, 1, 1)
# le quedaban 194px a la columna de nombres de área —que miden ~110— mientras
# los dos cuadros de la derecha cortaban "RB ALIMENTOS PRODUCCION" (185px de
# texto en 171 de celda). El ancho sobrante estaba del lado que no lo
# necesitaba.
#
# Las secciones de DOS cuadros se quedan en (1.7, 1), el reparto de siempre,
# y por lo tanto ya no parten la fila en el mismo sitio que la de tres. Es a
# propósito: alinear los cortes obligaría a darle 772px al único cuadro de
# desglose de "Por familia" —una tabla de tres columnas ocupando media
# pantalla— y a dejar la ficha de "Buscar producto" más angosta que su panel
# de apoyo. El bug del eje corrido que ataja `COLUMNAS_DRILL` en Compras es
# entre filas de UNA vista; acá son secciones distintas de la pila, cada una
# con su título y 16px de gap.
_COLUMNAS_NIVELES = {2: (1.7, 1), 3: (1.2, 1, 1)}

# Y el FORMATO de un cuadro de desglose depende de lo mismo, porque el ancho
# decide el formato (regla #349). Medido en 1366x768: con dos cuadros la
# grilla de la derecha mide 413px y con tres, 306 — y en 306 no entran a la
# vez un nombre largo, un monto exacto y la columna "%".
#
#   · `flex_nombre` 5 contra 2+2 del ranking: el nombre es lo único que no
#     se puede abreviar. "GASTOS ADMINISTRATIVOS" pide 174px de texto y
#     "RB ALIMENTOS PRODUCCION", 185.
#   · `monto_corto`: "S/ 39.2k" en vez de "S/ 39,210" libera ~15px. Los
#     montos exactos siguen en el ranking de la izquierda, que es ancho, y
#     en la tabla de productos de abajo.
#   · `ancho_barra` 0.30: la barra y el monto comparten celda (barra de
#     fondo, texto a la derecha), así que en una celda angosta la barra
#     tiene que ceder o el número termina escrito sobre el morado.
_FORMATO_DETALLE = {
    2: {"ancho_pct": 64, "flex_nombre": 3, "ancho_barra": 0.45},
    3: {"ancho_pct": 52, "flex_nombre": 5, "ancho_barra": 0.30,
        "monto_corto": True},
}

# Y el RANKING de la izquierda necesita lo suyo por el mismo motivo: al ceder
# ancho para que entraran tres cuadros, sus 416px de grilla dejaban la
# columna de nombres en 161 y empezó a cortar los que los desgloses habían
# dejado de cortar ("GASTOS ADMINISTRATIVOS", "LIMPIEZA Y MANTENIMIENTO").
# Los montos siguen EXACTOS acá —es el cuadro ancho, el que se lee como
# fuente del número— así que lo que cede es el ancho de la barra.
_FORMATO_RANKING = {
    2: {},  # los defaults de `_tabla_ranking`: 80 / flex 2 / barra 0.62
    3: {"ancho_pct": 64, "flex_nombre": 3, "ancho_barra": 0.45},
}

# Cuántas filas RESERVA una tabla-ranking antes de scrollear por dentro. El
# 8 es el techo de Compras (`proveedor.py::_FILAS_RANK`) y viaja con el
# resto del look: dos tablas con el mismo tema y el mismo alto de fila pero
# distinta cantidad de filas a la vista no se leen como la misma tabla.
_FILAS_RANK = 8


# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py).
_INVENTARIO_RAIL_CATEGORIAS = (
    ("Vista", (("Por área",        "Por área"),
               ("Por familia",     "Por familia"),
               ("Buscar producto", "Buscar producto"))),
    ("Datos", (("Tabla", "Tabla"),)),
)

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué, largo, está en `graficos/compras/__init__.py::_PILA`).
# Las cuatro vistas de Inventario comparten el mismo rango de fecha, así
# que a diferencia de Ajuste acá va UNA sola pila con todo adentro.
_PILA = (
    ("inv_sec_area",    "Por área"),
    ("inv_sec_familia", "Por familia"),
    ("inv_sec_buscar",  "Buscar producto"),
    ("inv_sec_tabla",   "Tabla"),
)


def _rango_con_holgura(*series, factor=0.28):
    """Rango de eje X con holgura para que el texto `outside` de la barra
    más larga no se corte contra el borde del gráfico — con `cliponaxis=
    False` Plotly no recorta en el eje, pero SÍ recorta contra el margen
    fijo de `_compras_layout` (r=10px) si la barra ya ocupa casi el 100%
    del ancho. Bug real: "Por área" con `GASTOS` en S/ 161,816 (barra al
    tope) mostraba la etiqueta cortada en "S/ 16…". `factor` más alto para
    etiquetas largas (p.ej. "S/ x · y unidad" en la ficha de un producto).

    Holgura SOLO del lado que se usa: con todo >= 0 (regla #80 — barras
    convertidas a magnitud, negativo se lee por color no por dirección)
    `lo` da 0 y no hace falta reservarle aire — eso dejaba una franja en
    blanco entre las etiquetas del eje Y y el arranque de las barras."""
    valores = [v for s in series for v in s]
    if not valores:
        return None
    lo, hi = min(0, min(valores)), max(0, max(valores))
    pad = max(abs(hi), abs(lo), 1) * factor
    return [lo - pad if lo < 0 else 0, hi + pad]


def _tabla_ranking(d, col_grp, col_val, nombre_grp, key, *,
                   ancho_pct=80, flex_nombre=2, ancho_barra=0.62,
                   monto_corto=False, abre_en=(), abrir_en_mayor=False):
    """Ranking de Por area/Por familia como TABLA con barra de progreso.

    Es la tabla-ranking del repo, la misma que el Ranking de proveedores de
    Compras: `CSS_RANKING_GRID` sobre `theme="streamlit"` (franja en vez de
    caja, todo blanco, sin lineas verticales, cuerpo de 11.5px), filas de
    `ALTO_FILA_RANK`, ocho a la vista y el resto por scroll interno, y una
    fila TOTAL fija abajo. La barra NO es un `cellRenderer` (ni la clase
    `init()/getGui()` de la regla #25, ni los sparklines de AG Grid, que son
    Enterprise) sino el FONDO de la celda, un `linear-gradient` cortado en
    el % del valor. Los colores salen de `tema.py` y no de `var(--accent)` a
    proposito: el grid vive en un iframe propio y las variables CSS del
    documento padre no llegan.

    Clic en una fila = TOGGLE del foco; devuelve la categoria elegida para
    que el caller filtre el panel derecho y muestre el detalle del siguiente
    nivel. Sin seleccion devuelve None, salvo que el caller pida un default
    con `abrir_en_mayor`: ahi devuelve el primer nombre de `abre_en` que
    exista en los datos y, si ninguno esta, la categoria mayor. Es el mismo
    criterio que el drill de Proveedor, donde la tarjeta de al lado nunca
    esta vacia; soltar la seleccion vuelve a ese default, no a "nada".

    El default es del PRIMER nivel y no del segundo, a proposito: si el
    desglose tambien se auto-enfocara, la franja de productos de abajo
    abriria recortada a una familia y no habria forma de ver el area
    entera. A diferencia de `plotly_chart(on_select=...)`,
    AgGrid devuelve la seleccion VIGENTE en cada run --es estado, no un
    evento que se repite--, asi que aca no hacen falta ni la key dinamica
    por foco ni el `st.rerun()` que evitaban el toggle infinito del grafico.

    La usan los DOS niveles de la seccion: el ranking de la tarjeta
    izquierda y el desglose de la derecha (`_tabla_detalle_foco`). Lo unico
    que cambia entre ellos es el reparto horizontal, porque la tarjeta
    derecha mide 449px contra 770 de la izquierda (medido en 1366x768, la
    pantalla objetivo) y ahi el ancho decide el formato (regla #349):

      - `flex_nombre` 3 en vez de 2: el nombre de la categoria es el dato
        que no se puede abreviar. Con 2, "GASTOS ADMINISTRATIVOS" (174px de
        texto) cae en una celda de 145 y se lee "GASTOS ADMINISTRATI...".
      - `ancho_barra` 0.45 en vez de 0.62: la barra y el monto comparten
        celda (barra de fondo, texto a la derecha), asi que cuanto mas
        angosta la celda, menos puede ocupar la barra sin meterse debajo
        del numero. "S/ 164,858" mide 68px: en los 141 de la celda angosta,
        con la barra al 62% le quedan 54 y el monto termina escrito sobre
        el morado.
      - `ancho_pct`, la columna de porcentaje.
    """
    from st_aggrid import AgGrid, JsCode

    met = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    serie = met.groupby(d[col_grp].astype(str)).sum().sort_values(ascending=False)
    if serie.empty:
        st.info("Sin datos.")
        return None

    # % sobre el total NETO, el mismo que la fila TOTAL de abajo, para que
    # sumen 100% con lo que el usuario ya esta viendo (no sobre la suma de
    # absolutos).
    total = float(serie.sum())
    _mayor = float(np.abs(serie.values).max()) or 1.0
    col_nombre = nombre_grp.capitalize()
    _pcts = [(v / total * 100) if total else 0.0 for v in serie.values]
    tabla = pd.DataFrame({
        col_nombre: serie.index.astype(str),
        "Valorizado": serie.values,
        "%": _pcts,
        # Ocultas: el % de LLENADO de la barra (contra la mayor MAGNITUD,
        # que no es el mismo numero que la columna "%"), y el signo, que se
        # lee por color y no por direccion, igual que en los graficos de
        # este dashboard (regla #80). La columna visible mantiene el valor
        # con signo; sin `_neg`, un ajuste negativo pintaria una barra larga
        # indistinguible de una compra grande.
        "_barra": [abs(v) / _mayor * 100 for v in serie.values],
        "_neg": [bool(v < 0) for v in serie.values],
    })
    # La fila TOTAL reemplaza al KPI "Valorizado total" que vivia arriba de
    # esta tabla (pedido del 2026-09-13: "quitar el KPI"). Mismo mecanismo
    # que el Ranking de proveedores: un dict calculado en PYTHON +
    # `pinnedBottomRowData`, no el `"grandTotalRow"` nativo, que en este
    # repo solo esta probado junto a `pivotMode=True` y esta tabla es plana.
    # Suma lo que la tabla MUESTRA, que aca es todo el recorte.
    fila_total = {col_nombre: "TOTAL", "Valorizado": round(total, 2),
                  "%": round(sum(_pcts), 2)}

    # La barra llega al 62% de la celda y el texto va a la DERECHA: asi
    # nunca se pisan (con la barra al 100% el monto caia sobre el morado,
    # texto oscuro sobre fondo oscuro). No falsea la lectura: todas se
    # escalan igual, las proporciones entre filas se mantienen. La pista va
    # transparente, no tintada: con fondo, la columna entera se lee como un
    # bloque lavanda que compite con las barras.
    # `justifyContent` es obligatorio: el `display:flex` de esta misma regla
    # anula el alineado a la derecha que trae `type: numericColumn`.
    # La fila TOTAL no dibuja barra: no hay `_barra` contra que escalarla
    # (seria 100% de si misma, una barra llena sin informacion) y el fondo
    # lo pone `getRowStyle` - un `background` aca se lo comeria, porque la
    # celda pinta ENCIMA de la fila.
    _js_barra = JsCode(
        "function(p){"
        " if (p.node.rowPinned) return {'display':'flex',"
        " 'alignItems':'center','justifyContent':'flex-end',"
        " 'fontWeight':'700'};"
        f" var w = Math.max(0, Math.min(100, p.data._barra||0)) * {ancho_barra};"
        f" var c = p.data._neg ? '{AJUSTE_NEG}' : '{ACENTO}';"
        " return {'background': 'linear-gradient(90deg, ' + c + ' 0 ' + w"
        " + '%, transparent ' + w + '% 100%)',"
        " 'display':'flex','alignItems':'center','justifyContent':'flex-end',"
        f" 'color':'{TEXTO_PRINCIPAL}'"
        "};"
        "}")
    # Misma paleta que la fila TOTAL del Ranking de proveedores: dos filas
    # de cierre del mismo idioma visual. SIN `borderTop`: la linea sobre los
    # totales la dibuja (o no) el tema en `.ag-floating-bottom`, y un inline
    # aca se apilaria con ella dando dos rayas pegadas de distinto color.
    _js_fila_total = JsCode(
        "function(p){ if(p.node.rowPinned){ return {"
        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
        f"'color':'{ACENTO_TEXTO_OSCURO}'"
        "}; } }")
    # El monto abreviado a miles es para las celdas angostas (ver
    # `_FORMATO_DETALLE`): abajo de 1.000 sigue exacto, porque ahi el
    # redondeo a "S/ 0.4k" perderia el dato en vez de acortarlo.
    _js_soles = JsCode(
        "function(p){ if (p.value==null) return '';"
        " var v = p.value;"
        + (" if (Math.abs(v) >= 1000) return 'S/ ' +"
           " (v/1000).toLocaleString('es-PE',{maximumFractionDigits:1})"
           " + 'k';" if monto_corto else "")
        + " return 'S/ ' + Math.round(v).toLocaleString('es-PE'); }")
    # Entero y no un decimal, igual que el Ranking de proveedores: "79%" y
    # no "79.0%". La columna es angosta y el decimal no cambia ninguna
    # decision: para el numero exacto esta el monto de al lado.
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' :"
        " Math.round(p.value) + '%'; }")
    # AG Grid, por si solo, NO deselecciona al reclickear la fila ya
    # seleccionada (pide Ctrl+clic, que nadie descubre). `setSelected(valor,
    # true)` limpia las demas -> sigue siendo seleccion unica. El guard de
    # `rowPinned` va afuera: sin el, clickear la fila TOTAL la "selecciona"
    # como si fuera una categoria real y el panel de al lado intentaria
    # enfocar un area llamada "TOTAL" que no existe en los datos.
    _js_toggle = JsCode(
        "function(e){ if (e.node.rowPinned) return;"
        " e.node.setSelected(!e.node.isSelected(), true); }")

    # Ocho filas de datos y el resto por scroll interno, como el Ranking de
    # proveedores. `extra` es todo lo que el grid mide y no son esas filas:
    # el cromo del grid (cabecera + borde + chrome del tema) mas la fila
    # TOTAL, que reserva su espacio DENTRO del `height=` - sin ese sumando
    # le comeria una fila a los datos. El `max(1, ...)` deja la cabecera y
    # el TOTAL con una fila de aire en el caso vacio, en vez de un grid de 0
    # filas que AG Grid dibuja recortando su propio overlay.
    _filas = min(_FILAS_RANK, max(1, len(serie)))

    resp = AgGrid(
        tabla,
        gridOptions={
            "columnDefs": [
                {"field": col_nombre, "flex": flex_nombre,
                 "tooltipField": col_nombre},
                {"field": "Valorizado", "flex": 2, "type": "numericColumn",
                 "cellStyle": _js_barra, "valueFormatter": _js_soles},
                {"field": "%", "width": ancho_pct, "type": "numericColumn",
                 "valueFormatter": _js_pct},
                {"field": "_barra", "hide": True},
                {"field": "_neg", "hide": True},
            ],
            "rowSelection": {"mode": "singleRow", "checkboxes": False,
                             "enableClickSelection": False},
            "onRowClicked": _js_toggle,
            "rowHeight": ALTO_FILA_RANK,
            "headerHeight": ALTO_HEADER_RANK,
            "suppressCellFocus": True,
            "suppressMovableColumns": True,
            "pinnedBottomRowData": [fila_total],
            "getRowStyle": _js_fila_total,
        },
        allow_unsafe_jscode=True,
        theme="streamlit",
        # El tema de fabrica no alcanza: filas blancas, cuerpo de 11.5px y
        # el marco de franja salen de `CSS_RANKING_GRID`, y el unico camino
        # es `custom_css=` porque el grid es un iframe y el `<style>` del
        # documento padre no entra. Ese dict ya estila la fila SELECCIONADA
        # (`.ag-row-selected::before`, el acento al 12%), que aca es el foco
        # del drill: sin marcarla, no se ve sobre que categoria esta
        # mirando el panel de la derecha.
        custom_css=CSS_RANKING_GRID,
        height=alturas.por_filas(_filas, px_fila=ALTO_FILA_RANK,
                                 extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                                 minimo=0),
        update_on=["selectionChanged"],
        key=key,
    )
    sel = getattr(resp, "selected_rows", None)
    if sel is not None and len(sel):
        fila = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
        return str(fila[col_nombre])
    if not abrir_en_mayor:
        return None
    # Sin seleccion: el default. La comparacion va normalizada porque el
    # nombre viaja escrito a mano en `ABRE_EN_AREA` y el ERP los manda
    # gritados y con espacios de sobra.
    _norm = {str(i).strip().upper(): str(i) for i in serie.index}
    for _cand in abre_en:
        _hit = _norm.get(str(_cand).strip().upper())
        if _hit is not None:
            return _hit
    return str(serie.index[0])


def _tabla_detalle_foco(d, col_next, nombre_next, col_val, key, ruta=(),
                        formato=None):
    """Al lado del ranking, un eslabón más de la cadena: el desglose del
    recorte que ya está en foco (Área → Familia → Subfamilia) — la pregunta
    natural después de "cuánto vale GASTOS" es "de qué se compone".

    Es la MISMA tabla que el ranking de la izquierda (`_tabla_ranking`), no
    una copia: sólo cambia el ancho de la columna "%". Era un `go.Bar`
    horizontal hasta el 2026-09-13, sin clic propio y con el argumento de que
    "acá no hay nada que elegir"; a pedido pasa a tabla y SÍ tiene clic:
    devuelve la categoría elegida (o None) para que el eslabón siguiente —y
    la tabla de productos de abajo— se recorten a ella. Ver `arquitectura.md`
    reglas #403 y #407.

    `ruta` es el recorte que ya está aplicado, en pares (columna, valor):
    filtra el df Y arma el título. Se recibe hecha en vez de recalcularse
    acá porque el caller la va acumulando nivel a nivel — con dos eslabones
    ya no alcanza un `col_grp`/`foco` sueltos, y tres argumentos paralelos
    por nivel es lo que convierte una cadena en un `if` por profundidad.

    La `key` que le pasa el caller lleva el foco adentro a propósito: al
    cambiar de área, la grilla es OTRA y nace sin selección. Con AgGrid eso
    es correcto —la selección es estado que se relee en cada run, no el
    evento que se repite de `plotly_chart(on_select=...)` (regla #399)—, y es
    lo que evita que un sub-foco sobreviva al área que lo justificaba."""
    dd = d
    for _col_r, _val_r in ruta:
        if _col_r and _val_r:
            dd = dd[dd[_col_r].astype(str) == _val_r]
    # El titulo nombra sólo el ÚLTIMO eslabón, no la ruta entera: con tres
    # cuadros "ALMACEN CENTRAL › COSTOS PRODUCCION — por subfamilia" no entra
    # en 339px, y de qué área viene ya lo dice el cuadro de la izquierda. La
    # ruta completa va al `title=`, que es donde se la puede leer sin que
    # empuje el layout.
    _ruta_txt = " › ".join(str(v) for _, v in ruta if v)
    _de = next((str(v) for _, v in reversed(list(ruta)) if v), "")
    if not col_next or dd.empty:
        st.caption(f"Sin desglose adicional para {_de}." if _de
                   else "Sin desglose adicional.")
        return None
    st.markdown(
        f'<div class="inv-rank-tit" title="{_ruta_txt.replace(chr(34), "")}">'
        f'{_de} — por {nombre_next}</div>', unsafe_allow_html=True)
    return _tabla_ranking(dd, col_next, col_val, nombre_next, key,
                          **(formato or _FORMATO_DETALLE[2]))


def _ficha_producto(d, prod_sel, col_prod, col_area, col_val, col_cant,
                     col_unidad):
    """Cantidad + valorizado + precio promedio por área para UN producto —
    siempre las tres cifras juntas, sin toggle (no hay "elegir métrica"
    cuando ya elegiste el producto)."""
    dd = d[d[col_prod].astype(str) == prod_sel]
    _v = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
    _c = pd.to_numeric(dd[col_cant], errors="coerce").fillna(0) if col_cant else None
    unidad = (str(dd[col_unidad].dropna().iloc[0])
              if col_unidad and dd[col_unidad].notna().any() else "u")

    total_val = float(_v.sum())
    total_cant = float(_c.sum()) if _c is not None else None
    precio_prom = (total_val / total_cant) if total_cant else None

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cantidad total",
              f"{total_cant:,.0f} {unidad}" if total_cant is not None else "—")
    k2.metric("Valorizado total", f"S/ {total_val:,.0f}")
    k3.metric("Precio promedio",
              f"S/ {precio_prom:,.2f}/{unidad}" if precio_prom else "—")
    k4.metric("Áreas", f"{dd[col_area].nunique():,}")

    g = (pd.DataFrame({"area": dd[col_area].astype(str), "val": _v,
                       "cant": _c if _c is not None else 0})
         .groupby("area", as_index=False).agg(val=("val", "sum"), cant=("cant", "sum")))
    # Áreas sin nada de este producto (val=0 y cant=0: "inactivas" para él)
    # no suman una barra — solo ruido, la mayoría de las áreas ni lo tienen.
    g = g[(g["val"] != 0) | (g["cant"] != 0)].sort_values("val")
    if g.empty:
        st.info("Sin stock ni valorizado activo para este producto en ninguna área.")
        return
    _texto = [f"S/ {v:,.0f}  ·  {c:,.0f} {unidad}" for v, c in zip(g["val"], g["cant"])]
    # Mismo criterio que _grafico_ranking: negativo va hacia la derecha
    # como el resto (largo = magnitud), diferenciado por color en vez de
    # descentrar el gráfico dibujando hacia la izquierda.
    color = [AJUSTE_NEG if v < 0 else ACENTO for v in g["val"]]
    fig = go.Figure(go.Bar(
        x=g["val"].abs(), y=[_compras_truncar(a, 30) for a in g["area"]],
        orientation="h", marker=dict(color=color, opacity=0.85),
        text=_texto, textposition="outside", cliponaxis=False,
        customdata=np.stack([g["val"], g["cant"]], axis=-1),
        hovertemplate=("%{y}<br>Valorizado: S/ %{customdata[0]:,.2f}<br>Cantidad: "
                       "%{customdata[1]:,.1f} " + unidad + "<extra></extra>"),
    ))
    _compras_layout(fig, alto=alturas.por_filas(
        len(g), px_fila=40, minimo=320, extra=80, enmarcada=True))
    fig.update_layout(title=f"{prod_sel} — cantidad y valorizado por área")
    fig.update_xaxes(visible=False, range=_rango_con_holgura(g["val"].abs(), factor=0.35))
    fig.update_yaxes(showgrid=False)  # eje Y = nombres de área, no valores
    st.plotly_chart(fig, use_container_width=True, key="inv_g_producto")


def _ficha_subfamilia(d, subfam_sel, col_subfam, col_prod, col_area,
                       col_val, col_cant, col_unidad):
    """Todos los productos de una subfamilia — un bar por producto (sumado
    entre áreas; ya no desglosado por área — el color lo necesita el signo,
    ver abajo). Cada barra muestra precio + unidad + % de participación.
    Solo 2 KPIs (Valorizado total, Productos): Cantidad total/Precio
    promedio se sacaron a pedido — mezclaban unidades entre productos
    (kg, und, Lt) y el número agregado no representaba nada accionable.

    Negativo va a la derecha, diferenciado por color — mismo criterio que
    `_grafico_ranking`/`_ficha_producto` (regla #80). Antes esta ficha era
    la única sin ese tratamiento porque el color codificaba ÁREA (barra
    apilada); al pasar a un bar por producto, el color queda libre para
    codificar signo como en el resto del dashboard."""
    dd = d[d[col_subfam].astype(str) == subfam_sel]
    _v = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
    _c = pd.to_numeric(dd[col_cant], errors="coerce").fillna(0) if col_cant else None

    total_val = float(_v.sum())
    n_prod = dd[col_prod].nunique() if col_prod else 0

    k1, k2 = st.columns(2)
    k1.metric("Valorizado total", f"S/ {total_val:,.0f}")
    k2.metric("Productos", f"{n_prod:,}")

    if not col_prod or dd.empty:
        st.info("Sin datos para este grupo.")
        return
    base = pd.DataFrame({
        "prod": dd[col_prod].astype(str),
        "val": _v,
        "cant": _c if _c is not None else 0,
        "unidad": dd[col_unidad].astype(str) if col_unidad else "",
    })
    g = base.groupby("prod").agg(
        val=("val", "sum"), cant=("cant", "sum"),
        unidad=("unidad", lambda s: next(iter(s.dropna()), "")),
    )
    # Productos sin stock ni valorizado ("inactivos" para esta subfamilia)
    # no entran — regla #78.
    g = g[(g["val"] != 0) | (g["cant"] != 0)]
    if g.empty:
        st.info("Ningún producto de este grupo tiene stock o valorizado activo.")
        return

    _precio = np.where(g["cant"] != 0, g["val"] / g["cant"], np.nan)
    _pct = (g["val"] / total_val * 100) if total_val else pd.Series(0.0, index=g.index)
    _texto = []
    for _precio_v, _pct_v, _unidad_v in zip(_precio, _pct, g["unidad"]):
        if pd.notna(_precio_v):
            _precio_txt = (f"S/ {_precio_v:,.2f}/{_unidad_v}" if _unidad_v
                           else f"S/ {_precio_v:,.2f}")
        else:
            _precio_txt = "—"
        _texto.append(f"{_precio_txt} · {_pct_v:.1f}%")
    g["_texto"] = _texto

    # Ascendente: en un go.Bar (a diferencia del px.bar que usaba esta
    # ficha antes) el primer elemento del array `y` pinta ABAJO — mayor a
    # menor leyendo de arriba hacia abajo pide el más grande AL FINAL de
    # la lista. Mismo criterio que _grafico_ranking/_ficha_producto.
    g = g.sort_values("val", ascending=True)
    color = [AJUSTE_NEG if v < 0 else ACENTO for v in g["val"]]

    fig = go.Figure(go.Bar(
        x=np.abs(g["val"]), y=[_compras_truncar(p, 30) for p in g.index],
        orientation="h", marker=dict(color=color, opacity=0.85),
        text=g["_texto"], textposition="outside", cliponaxis=False,
        customdata=g["val"],
        hovertemplate="%{y}<br>S/ %{customdata:,.2f}<extra></extra>",
    ))
    _compras_layout(fig, alto=alturas.por_filas(
        len(g), px_fila=34, minimo=360, extra=60, enmarcada=True))
    fig.update_layout(title=f"{subfam_sel} — valorizado por producto")
    fig.update_xaxes(visible=False, range=_rango_con_holgura(np.abs(g["val"]), factor=0.5))
    fig.update_yaxes(showgrid=False)  # eje Y = nombres de producto, no valores
    st.plotly_chart(fig, use_container_width=True, key="inv_g_subfamilia")


def _limpiar_subfam():
    st.session_state["inv_buscar_subfamilia"] = None


def _limpiar_producto():
    st.session_state["inv_buscar_producto"] = None


def _render_buscar_producto(d, col_prod, col_area, col_subfam, col_val,
                            col_cant, col_unidad):
    """Buscador de producto puntual O de un grupo (Subfamilia) completo —
    mutuamente excluyentes: elegir uno limpia el otro (callback, antes del
    rerun, mismo patrón que `_rail_set` en graficos/base.py)."""
    if not col_prod or not col_area:
        st.info("Faltan columnas de producto o área para este buscador.")
        return

    productos = sorted(d[col_prod].dropna().astype(str).unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Producto", productos, index=None,
                     placeholder="Buscar producto por nombre…",
                     key="inv_buscar_producto", on_change=_limpiar_subfam)
    if col_subfam:
        subfams = sorted(d[col_subfam].dropna().astype(str).unique().tolist())
        with c2:
            st.selectbox("Grupo (Subfamilia)", subfams, index=None,
                         placeholder="…o un grupo completo",
                         key="inv_buscar_subfamilia", on_change=_limpiar_producto)

    prod_sel = st.session_state.get("inv_buscar_producto")
    subfam_sel = st.session_state.get("inv_buscar_subfamilia") if col_subfam else None

    if not prod_sel and not subfam_sel:
        st.info("Buscá un producto o elegí un grupo para ver cuánto hay y en qué área.")
        return

    if prod_sel:
        _ficha_producto(d, prod_sel, col_prod, col_area, col_val, col_cant, col_unidad)
    else:
        _ficha_subfamilia(d, subfam_sel, col_subfam, col_prod, col_area,
                          col_val, col_cant, col_unidad)


def _panel_relacionados(d, col_prod, col_fam, col_subfam, col_val):
    """Panel lateral de Buscar producto: en vez de repetir el top-10
    genérico (redundante con la ficha que ya está a la izquierda), muestra
    otros productos de la misma subfamilia/familia que el seleccionado."""
    prod_sel = st.session_state.get("inv_buscar_producto")
    subfam_sel = st.session_state.get("inv_buscar_subfamilia") if col_subfam else None
    col_grp = col_subfam or col_fam
    etiqueta = "subfamilia" if col_subfam else "familia"

    if prod_sel and col_grp:
        fila = d[d[col_prod].astype(str) == prod_sel]
        grupo_val = (str(fila[col_grp].dropna().iloc[0])
                     if not fila.empty and fila[col_grp].notna().any() else None)
        if not grupo_val:
            st.caption("Sin más contexto disponible.")
            return
        st.markdown(f"**Otros productos de la misma {etiqueta}**")
        st.caption(grupo_val)
        dd = d[(d[col_grp].astype(str) == grupo_val) & (d[col_prod].astype(str) != prod_sel)]
        _v = pd.to_numeric(dd[col_val], errors="coerce").fillna(0)
        serie = _v.groupby(dd[col_prod].astype(str)).sum().nlargest(8).sort_values()
        if serie.empty:
            st.info("No hay más productos en este grupo.")
        else:
            fig = go.Figure(go.Bar(
                x=serie.values, y=[_compras_truncar(i, 24) for i in serie.index],
                orientation="h", marker=dict(color=ACENTO, opacity=0.85),
                text=[f"S/ {v:,.0f}" for v in serie.values],
                textposition="outside", cliponaxis=False,
            ))
            fig.update_layout(
                height=alturas.APOYO, margin=dict(l=4, r=60, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
            )
            fig.update_xaxes(visible=False, range=_rango_con_holgura(serie.values))
            st.plotly_chart(fig, use_container_width=True, key="inv_relacionados")
    elif subfam_sel:
        st.caption("Todos los productos del grupo ya están a la izquierda, "
                   "con su desglose por área.")
    else:
        st.caption("Elegí un producto o un grupo para ver contexto relacionado acá.")


def _panel_top(d, ruta, col_prod, col_area, col_val, col_punit, _cant,
               col_unidad=None):
    """Productos de Por área/Por familia — tabla ordenable, no un
    gráfico. Reemplaza las 2 pestañas de mini-barras (Mayor cantidad/Precio
    más alto): con columnas ordenables por header, "top por cantidad" y
    "top por precio" son el mismo componente visto con otro orden — dos
    gráficos separados eran redundantes.

    Lista TODOS los productos del recorte, no los 20 más grandes: "ya que es
    una tabla, el usuario puede hacer scroll" (2026-09-13). Un top-20 en una
    tabla ORDENABLE miente por partida doble — ordenar por "Precio unitario"
    reordena esos 20, no los productos caros, y el nº 21 por valorizado no
    existe para el usuario. El scroll lo hace la GRILLA, que reserva las
    mismas ocho filas que las otras dos tablas de la sección; la tarjeta no
    crece ni saca barra propia.

    `ruta` son los pares (columna, valor) de la cadena de arriba —área,
    familia, subfamilia— hasta donde el usuario haya clickeado. El % de
    participación se recalcula sobre ESE recorte, no sobre el área entera,
    porque el criterio de la tarjeta es "sumar 100% con lo que el usuario ya
    está viendo arriba".

    La columna "UM" (2026-09-13, a pedido) escribe la `Unidad Kardex` del
    producto con `unidad_corta` —el mismo mapa que rotula las cantidades de
    Compras, no una copia— y va pegada a "Cantidad", que es el número al que
    le da sentido: 34 de qué. El TOTAL la deja vacía: sumar kg con L no da
    una unidad.

    Barra de "Participación %" + checkbox con "Selección %" recalculada en
    vivo (sin rerun de Streamlit): MISMO patrón ya usado en la Tabla
    principal de este reporte (`tablas/desktop.py`, sección "Inventario
    Valorizado: 2 columnas de % + checkbox de selección") — no un
    componente nuevo, la barra-gradiente vive en `cellStyle` de AgGrid, no
    en un Styler de pandas (ver `arquitectura.md` sobre por qué acá sí
    hace falta JsCode y en `compras/volatilidad.py` no)."""
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

    d_panel = d
    for _col_r, _val_r in ruta:
        if _col_r and _val_r:
            d_panel = d_panel[d_panel[_col_r].astype(str) == _val_r]
    if not (col_prod and col_area and _cant is not None and col_val):
        st.info("Faltan columnas para esta tabla.")
        return

    _cant_panel = _cant.loc[d_panel.index]
    _val_panel = pd.to_numeric(d_panel[col_val], errors="coerce").fillna(0)
    _pu_panel = (pd.to_numeric(d_panel[col_punit], errors="coerce")
                if col_punit else pd.Series(np.nan, index=d_panel.index))
    base = pd.DataFrame({
        "Producto": d_panel[col_prod].astype(str),
        "Área": d_panel[col_area].astype(str),
        "Cantidad": _cant_panel.values,
        "UM": ([unidad_corta(u) for u in d_panel[col_unidad]]
               if col_unidad else ""),
        "Precio unitario": _pu_panel.values,
        "Valorizado": _val_panel.values,
    })
    # `first` para la UM y no una agregación: es un atributo del producto,
    # no una medida. Va dentro del `agg` y no como cuarta clave del groupby
    # a propósito — si un producto llegara con dos unidades distintas, una
    # clave más lo partiría en dos filas que suman mal; así se queda en una
    # y a lo sumo rotula con la primera.
    g = (base.groupby(["Producto", "Área"], as_index=False)
         .agg(Cantidad=("Cantidad", "sum"), Valorizado=("Valorizado", "sum"),
              UM=("UM", "first"),
              **{"Precio unitario": ("Precio unitario", "mean")}))
    if g.empty:
        st.info("Sin datos.")
        return

    # Participación % contra el total del FOCO (no solo el top mostrado) —
    # mismo criterio que el % de las barras de _grafico_ranking: sobre el
    # total neto que el usuario ya ve arriba, no sobre una suma parcial.
    _total_foco = float(_val_panel.sum())
    g["Participación %"] = ((g["Valorizado"] / _total_foco * 100)
                            if _total_foco else 0.0)
    g["Selección %"] = g["Participación %"]  # semilla; el valueGetter de abajo la recalcula en vivo
    g = g.sort_values("Valorizado", ascending=False)

    # El encabezado dice el recorte Y cuántas filas trae: sin el número, una
    # tabla que scrollea no deja ver si son 12 productos o 400.
    _ruta = " › ".join([str(v) for _, v in ruta if v])
    st.markdown(
        '<div class="inv-rank-tit">Productos'
        + (f" · {_ruta}" if _ruta else "")
        + f' <span class="inv-rank-tit-n">{len(g):,}</span></div>',
        unsafe_allow_html=True)

    # Fila TOTAL, igual que las otras dos tablas de la sección. "Precio
    # unitario" queda VACÍA a propósito: es un ratio y un ratio no se suma ni
    # se promedia sobre el agregado (la misma trampa que la regla #199). El
    # "Selección %" tampoco lleva total — su valor lo calcula en vivo el
    # valueGetter contra lo tildado, así que un número fijo ahí mentiría en
    # cuanto se marque la primera fila.
    _fila_total = {
        "Producto": "TOTAL",
        "Área": "",
        "UM": "",
        "Cantidad": round(float(g["Cantidad"].sum()), 1),
        "Valorizado": round(float(g["Valorizado"].sum()), 2),
        "Participación %": round(float(g["Participación %"].sum()), 1),
    }

    gb = GridOptionsBuilder.from_dataframe(
        g[["Producto", "Área", "Cantidad", "UM", "Precio unitario",
           "Valorizado", "Participación %", "Selección %"]])
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    # minWidths ajustados para que las 7 entren sin scroll horizontal en la
    # franja de abajo (~911-1117px medido en vivo): con los anchos "cómodos"
    # originales (170+110+100+120+120+140+140=900px de columnas centrales)
    # quedaban ~19px cortos contra el ancho disponible real — Selección %,
    # al ser la última, quedaba virtualizada fuera de vista (ni scrolleable
    # a simple vista: parecía que la columna no existía).
    gb.configure_column("Producto", pinned="left", minWidth=150)
    # El ÁREA se esconde cuando la cadena de arriba ya la fijó: con el foco
    # por defecto en ALMACEN CENTRAL, esa columna escribe la misma palabra
    # en las 3.865 filas y el dato ya está en el título de la tarjeta — el
    # caso exacto de la regla #239. Oculta y no borrada: sigue en el modelo
    # por si hace falta ordenar por ella, y son los 90px que necesitaba la
    # UM para entrar sin empujar la tabla a scroll horizontal.
    _area_fija = any(c == col_area and v for c, v in ruta)
    gb.configure_column("Área", minWidth=90, hide=_area_fija)
    # Angosta: son tres letras ("kg", "L", "und"). Sin `flex`, para que no
    # se coma el ancho que necesitan los nombres de producto.
    gb.configure_column("UM", minWidth=52, maxWidth=64)

    _num_fmt = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined || isNaN(params.value)) return '–';
            return Number(params.value).toLocaleString('es-PE', {maximumFractionDigits: 1});
        }
    """)
    _money_fmt = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined || isNaN(params.value)) return '–';
            return 'S/ ' + Number(params.value).toLocaleString('es-PE', {maximumFractionDigits: 0});
        }
    """)
    gb.configure_column("Cantidad", type=["numericColumn"], minWidth=90,
                        valueFormatter=_num_fmt)
    gb.configure_column("Precio unitario", type=["numericColumn"], minWidth=100,
                        valueFormatter=_money_fmt)
    gb.configure_column("Valorizado", type=["numericColumn"], minWidth=110,
                        valueFormatter=_money_fmt, sort="desc")

    # Misma barra-gradiente que tablas/desktop.py::_pct_bar_style — el "–"
    # con value null cubre "Selección %" mientras no haya nada marcado
    # (Participación % siempre tiene valor).
    _pct_bar_style = JsCode(f"""
        function(params) {{
            var base = {{ textAlign: 'right', fontWeight: '500', paddingRight: '12px' }};
            if (params.value === null || params.value === undefined) return base;
            var pct = Math.max(0, Math.min(100, Number(params.value)));
            return Object.assign({{}}, base, {{
                backgroundImage: 'linear-gradient(to right, {LAVANDA_BORDE} 0%, {LAVANDA_BORDE} ' + pct + '%, transparent ' + pct + '%, transparent 100%)',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '100% 80%',
                backgroundPosition: 'left center',
            }});
        }}
    """)
    _pct_fmt = JsCode("""
        function(params) {
            if (params.value === null || params.value === undefined) return '–';
            return Number(params.value).toLocaleString('es-PE',
                { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
        }
    """)
    gb.configure_column("Participación %", minWidth=115, type=["numericColumn"],
                        cellStyle=_pct_bar_style, valueFormatter=_pct_fmt)
    gb.configure_column(
        "Selección %", minWidth=115, type=["numericColumn"],
        cellStyle=_pct_bar_style, valueFormatter=_pct_fmt,
        # Recalcula en vivo contra la suma de getSelectedNodes() — sin
        # selección, null (el formatter de arriba pinta "–").
        valueGetter=JsCode("""
            function(params) {
                if (!params.data) return null;
                var val = Number(params.data["Valorizado"]);
                if (isNaN(val)) return null;
                var nodes = (params.api && params.api.getSelectedNodes)
                    ? params.api.getSelectedNodes() : [];
                if (!nodes || nodes.length === 0) return null;
                var suma = 0;
                nodes.forEach(function(n) {
                    if (n.data) {
                        var v = Number(n.data["Valorizado"]);
                        if (!isNaN(v)) suma += v;
                    }
                });
                if (suma <= 0) return null;
                return (val / suma) * 100;
            }
        """),
    )
    gb.configure_selection("multiple", use_checkbox=True, header_checkbox=True)
    grid_options = gb.build()
    # Sin esto, la última columna ("Selección %") quedaba virtualizada
    # fuera de rango y NUNCA renderizaba celda — bug real, verificado en
    # vivo: el header aparecía pero la fila tenía un hueco vacío del ancho
    # de una columna. La grilla es chica (7 columnas, ~20 filas), así que
    # desactivar la virtualización horizontal no cuesta nada de
    # performance. Causa raíz probable: AG Grid calcula el rango visible
    # ANTES de que el iframe de Streamlit se asiente en su ancho final.
    grid_options["suppressColumnVirtualisation"] = True
    # Las tres tablas de la sección miden lo mismo y se leen igual: mismo
    # alto de fila y de cabecera que el ranking, mismo tema, mismo CSS.
    grid_options["rowHeight"] = ALTO_FILA_RANK
    grid_options["headerHeight"] = ALTO_HEADER_RANK
    grid_options["pinnedBottomRowData"] = [_fila_total]
    # La fila TOTAL con la paleta de cierre de las otras dos. `rowPinned`
    # también apaga su checkbox: una fila que no es un producto no se puede
    # sumar a la selección (y "Selección %" la contaría dos veces).
    grid_options["getRowStyle"] = JsCode(
        "function(p){ if(p.node.rowPinned){ return {"
        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
        f"'color':'{ACENTO_TEXTO_OSCURO}'"
        "}; } }")
    # AG Grid no sabe que un valueGetter "cambió" (no depende de ningún
    # field propio) — sin este refreshCells forzado tras cada click de
    # checkbox, "Selección %" se queda pintada con el valor anterior.
    grid_options["onSelectionChanged"] = JsCode("""
        function(params) {
            try {
                params.api.refreshCells({ columns: ['Selección %'], force: true });
            } catch(e) {}
        }
    """)

    AgGrid(
        g, gridOptions=grid_options, theme="streamlit",
        # Ocho filas reservadas y el resto por scroll interno, la misma
        # cuenta que `_tabla_ranking` (ver el comentario de `extra` allá).
        height=alturas.por_filas(min(_FILAS_RANK, max(1, len(g))),
                                 px_fila=ALTO_FILA_RANK,
                                 extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                                 minimo=0),
        custom_css=CSS_RANKING_GRID,
        allow_unsafe_jscode=True,
        # La key lleva el recorte entero: cambiar de área o de familia
        # estrena grilla, así los checkboxes de "Selección %" no quedan
        # marcados sobre productos que ya no están en la tabla.
        key="inv_top_grid_" + (_slug("_".join(str(v) for _, v in ruta if v))
                               or "global"),
    )


def renderizar_graficos_inventario(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Inventario Valorizado: KPIs + 3 vistas + panel lateral.

    `tabla_cb`: callback que arma la Tabla (inyectado por app.py). Se le
    pasa `d` — el df ya filtrado por los chips propios (Área/Familia) —
    igual que Ventas, para no tener un estado de filtros distinto entre
    Tabla y gráficos."""
    col_area   = _resolver(df_f, ["Nombre Area", "NOMBRE AREA", "Area"])
    col_fam    = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_subfam = _resolver(df_f, ["Nombre Subfamilia", "NOMBRE SUBFAMILIA", "Subfamilia"])
    col_prod   = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_cant   = _resolver(df_f, ["Stock al Dia", "Stock al dia", "STOCK AL DIA",
                                  "Cantidad", "Stock"])
    col_val    = _resolver(df_f, ["Valorizado total", "VALORIZADO TOTAL",
                                  "Valorizado"])
    col_punit  = _resolver(df_f, ["Precio Promedio", "PRECIO PROMEDIO", "Precio"])
    col_unidad = _resolver(df_f, ["Unidad Kardex", "UNIDAD KARDEX",
                                  "Unidad Medida", "Unidad"])

    if not col_val:
        st.warning("No se encontró la columna de valorizado. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Área / Familia como chips en la FRANJA blanca ────────────
    area_sel, fam_sel = [], []
    with compartimento_filtros(contar_filtros("inv_graf_filtro_area",
                                              "inv_graf_filtro_fam")):
        _, area_sel = filtro_pills(df_f, col_area,
                                   "inv_graf_filtro_area", "Área")
        _, fam_sel = filtro_pills(df_f, col_fam,
                                  "inv_graf_filtro_fam", "Familia")

    d = df_f
    if area_sel and col_area:
        d = d[d[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Inventario Valorizado", d,
                         {"Área": area_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _cant = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
             if col_cant else None)

    # Sin guard de "inyectar una sola vez": un `st.markdown` de estilos con
    # ese guard DESAPARECE en el rerun siguiente (regla #59).
    st.markdown(CSS_TITULOS_INV, unsafe_allow_html=True)

    # El rail ya no ELIGE: con `secciones` marca dónde estás y scrollea.
    _render_rail(_INVENTARIO_RAIL_CATEGORIAS, "inv_graf_tipo",
                 btn_prefix="inv_rail_btn_", secciones=_PILA)

    # Las tres vistas de gráfico compartían UN layout de dos columnas con
    # `if graf ==` salpicado adentro, y las mismas tres keys de tarjeta
    # (`ajuste_graf_card_{izq,der,abajo}_inv`) para todas. Apiladas, eso
    # serían varios widgets con la misma key — excepción de Streamlit. Cada
    # sección pasa a ser AUTÓNOMA: arma su propio par de columnas y lleva su
    # sufijo. Se conserva el prefijo `ajuste_graf_card_`, de donde cuelga el
    # CSS de tarjeta (`estilos/_80_cards.py`).
    def _seccion_grupo(slug, niveles, abre_en=()):
        """Una de las dos vistas de ranking (Por área / Por familia).

        Las dos son el MISMO layout sobre otra cadena de agrupación, que es
        lo que antes resolvía el `col_area if graf == "Por área" else
        col_fam` de adentro del bloque compartido. `niveles` es esa cadena,
        en pares (columna, nombre): el primero es el ranking y los que
        siguen, un cuadro cada uno. Por área son tres —Área › Familia ›
        Subfamilia (2026-09-13, a pedido: "que hayan tres cuadros en el
        primer segmento")— y Por familia son dos, porque su tercer nivel
        sería el producto y ése ya es la tabla de abajo.

        Todos los cuadros se dibujan SIEMPRE: cada uno desglosa el recorte
        que viene de su izquierda, y la tabla de abajo muestra los productos
        del recorte MÁS PROFUNDO que esté activo. Hasta el 2026-09-13 el
        cuadro de la derecha mostraba, sin foco, la tabla de productos de
        TODO el inventario —15.360 filas en un tercio de pantalla, con
        scroll horizontal porque sus 7 columnas piden 620px y ahí hay 248—.
        Con un foco por defecto (`abre_en`) esa tabla vive siempre en la
        franja ancha, que es donde entra."""
        col_grp, nombre_grp = niveles[0]
        # columnas-internas: el ranking y sus desgloses, dentro de la
        # sección. No es una fila de drill de Compras: COLUMNAS_DRILL no
        # aplica; el reparto propio vive en `_COLUMNAS_NIVELES`.
        cols = st.columns(_COLUMNAS_NIVELES[len(niveles)])
        # La RUTA: los pares (columna, valor) elegidos hasta acá. Empieza
        # con el ranking y crece un eslabón por cuadro. Es lo que cada
        # cuadro recibe para recortarse y lo que la tabla de abajo recibe
        # entera — sin ella, cada nivel nuevo agregaba dos argumentos
        # paralelos (`col_sub`/`sub_foco`, `col_sub2`/`sub2_foco`…) y el
        # tercero ya no entraba sin un `if` por profundidad.
        ruta = []
        with cols[0]:
            with st.container(border=True,
                              key=f"ajuste_graf_card_izq_inv_{slug}"):
                # El KPI "Valorizado total" que abría esta tarjeta se retiró
                # el 2026-09-13, a pedido: ocupaba un cuarto de la tarjeta
                # para decir un número que la fila TOTAL de la tabla dice en
                # una línea, en la columna donde el usuario ya está leyendo
                # montos. El título pasa a ser el de la tarjeta, con el
                # mismo cuerpo que "Ranking de proveedores".
                if not col_grp:
                    st.info(f"No se encontró la columna de {nombre_grp}.")
                else:
                    st.markdown(
                        f'<div class="inv-rank-tit">Valorizado por '
                        f'{nombre_grp}</div>', unsafe_allow_html=True)
                    foco = _tabla_ranking(d, col_grp, col_val, nombre_grp,
                                          key=f"inv_rank_grid_{slug}",
                                          abre_en=abre_en,
                                          abrir_en_mayor=True,
                                          **_FORMATO_RANKING[len(niveles)])
                    ruta.append((col_grp, foco))
        for _i, (_col_n, _nombre_n) in enumerate(niveles[1:]):
            # La key de la tarjeta conserva el prefijo `ajuste_graf_card_der_`
            # aunque ahora sean dos: de ese prefijo cuelga el CSS por FAMILIA
            # de `estilos/_80_cards.py` y de `_20_compras_rail.py`, así que
            # un nombre nuevo la dejaría sin marco. El sufijo `_n<i>` va al
            # final por lo mismo — el selector es `[class*=...der_]`.
            _key_card = (f"ajuste_graf_card_der_inv_{slug}"
                         + ("" if _i == 0 else f"_n{_i + 1}"))
            with cols[_i + 1]:
                with st.container(border=True, key=_key_card):
                    # Sin recorte de arriba no hay nada que desglosar: el
                    # cuadro queda callado en vez de repetir el nivel
                    # anterior. Con el default de `abre_en`, al primero
                    # nunca le falta.
                    if not [v for _, v in ruta if v]:
                        st.caption("Elegí una fila del cuadro anterior.")
                        continue
                    # La key lleva la ruta adentro a propósito: al cambiar
                    # lo de arriba, la grilla es OTRA y nace sin selección
                    # (ver el docstring de `_tabla_detalle_foco`).
                    _k = _slug("_".join(str(v) for _, v in ruta if v))
                    _sub = _tabla_detalle_foco(
                        d, _col_n, _nombre_n, col_val,
                        key=f"inv_det_grid_{slug}_{_i}_{_k}", ruta=tuple(ruta),
                        formato=_FORMATO_DETALLE[len(niveles)])
                    ruta.append((_col_n, _sub))
        with st.container(border=True,
                          key=f"ajuste_graf_card_abajo_inv_{slug}"):
            _panel_top(d, tuple(ruta), col_prod, col_area, col_val,
                       col_punit, _cant, col_unidad=col_unidad)

    def _dib_area():
        _seccion_grupo("area",
                       ((col_area, "área"), (col_fam, "familia"),
                        (col_subfam, "subfamilia")),
                       abre_en=ABRE_EN_AREA)

    def _dib_familia():
        # Dos niveles y no tres: el tercero sería el producto, y ése ya es
        # la tabla de abajo.
        _seccion_grupo("familia",
                       ((col_fam, "familia"), (col_subfam, "subfamilia")))

    def _dib_buscar():
        # columnas-internas: el mismo reparto que una sección de ranking de
        # dos cuadros. Sale de `_COLUMNAS_NIVELES` y no de un literal para
        # que las dos se muevan juntas si ese reparto cambia.
        col_izq, col_der = st.columns(_COLUMNAS_NIVELES[2])
        with col_izq:
            with st.container(border=True, key="ajuste_graf_card_izq_inv_buscar"):
                # Sin KPI, como las otras tres secciones (2026-09-13). Acá
                # no hay fila TOTAL que lo herede: el número se fue, y es
                # lo pedido — en una ficha de UN producto, el valorizado de
                # todo el inventario no era el dato de la pantalla.
                _render_buscar_producto(d, col_prod, col_area, col_subfam,
                                        col_val, col_cant, col_unidad)
        with col_der:
            with st.container(border=True, key="ajuste_graf_card_der_inv_buscar"):
                _panel_relacionados(d, col_prod, col_fam, col_subfam, col_val)

    def _dib_tabla():
        with st.container(border=True, key="ajuste_graf_card_izq_inv_tabla"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "inv_sec_area":    _dib_area,
        "inv_sec_familia": _dib_familia,
        "inv_sec_buscar":  _dib_buscar,
        "inv_sec_tabla":   _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga (mismo bucle que Compras, Receta Base y Ajuste).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
