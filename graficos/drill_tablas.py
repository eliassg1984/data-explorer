"""
graficos.drill_tablas — la CADENA de tablas clickeables: ranking › desgloses ›
hojas.

Hasta tres cuadros en la fila de arriba —un nivel de agrupación cada uno, y
el de la izquierda manda sobre el de su derecha— y una tabla ancha abajo con
las HOJAS del recorte más profundo que esté activo. Es el layout que estrenó
Inventario Valorizado el 2026-09-13 ("que hayan tres cuadros en el primer
segmento", "que sean similares al de Ranking de Proveedores") y que
Movimientos pidió igual ese mismo día para requerimientos: Sub Almacén ›
Familia › Subfamilia › Producto.

QUÉ ES CADA PIEZA
  · `tabla_ranking` — la tabla-ranking del repo: AgGrid con la barra de
    progreso pintada como FONDO de la celda, fila TOTAL fija abajo y
    clic-toggle que devuelve la categoría elegida.
  · `tabla_detalle` — la MISMA tabla, recortada a la ruta que viene de la
    izquierda y con su título encima.
  · `tabla_hojas`   — la tabla ancha de abajo: todas las hojas del recorte
    (no un top-N, ver regla #403), ordenable, con % de participación y un
    % de selección que se recalcula en vivo contra lo tildado.
  · `seccion_cadena` — las cuatro juntas: arma las columnas, acumula la
    ruta y dibuja. Una sección de la pila en una sola llamada.

EL LOOK NO SE INVENTA ACÁ: sale de Compras (`ALTO_FILA_RANK`,
`CROMO_GRID_RANK`, `CSS_RANKING_GRID`), que es donde nació con el Ranking de
proveedores. El alto de fila y el CSS son UNA sola decisión y viajan juntos
—separarlos es lo que deja una tabla con filas de 24px y el cuerpo de otro
tema—, ver regla #404.

DOS COPIAS, POR AHORA — y es deuda, no diseño. `graficos/inventario.py`
tiene esta misma cadena escrita adentro (`_tabla_ranking`,
`_tabla_detalle_foco`, `_panel_top`, `_seccion_grupo`): este módulo salió de
ahí, copiando y generalizando lo que estaba atado a sus columnas. Mientras
las dos existan, un cambio de look va en las DOS — que es exactamente el
escenario que midió la regla #379 (dos definiciones de `nombre_propio` que
diferían en 48 de 773 nombres: el mismo texto escrito distinto según qué
módulo lo formateara). Migrar Inventario a este módulo es el paso pendiente
y es mecánico: sus cuatro funciones pasan a ser una llamada a
`seccion_cadena` por sección. Ver regla #411.
"""

import numpy as np
import pandas as pd
import streamlit as st

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, AJUSTE_NEG, LAVANDA_BORDE, LAVANDA_CHIP,
    TEXTO_PRINCIPAL,
)
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CROMO_GRID_RANK, unidad_corta,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
# La ÚNICA del repo (`test_graficos.py::_pruebas_una_sola_nombre_propio`
# monta guardia): hubo dos definiciones hasta el 2026-09-11 y diferían en 48
# de 773 nombres. Ver regla #379.
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.base import _slug
from graficos import alturas

# Los títulos de las tarjetas, con los MISMOS cuatro valores que
# `.cp-rank-tit` de `graficos/compras/_css_proveedor.py`: las dos se mueven
# juntas. El prefijo `inv-` es HISTORIA —la clase nació en Inventario, que
# hoy inyecta su propia copia idéntica— y se conserva por lo mismo que este
# módulo importa `CSS_RANKING_GRID` de un archivo que se llama "proveedor":
# renombrar una clase compartida es churn que no arregla nada.
# Va sin guard de "inyectar una sola vez" a propósito (regla #59).
CSS_TITULOS_DRILL = """
<style>
.inv-rank-tit { font-size: 16px; font-weight: 600; color: var(--text-primary);
                padding-left: 2px; margin: 0 0 4px;
                /* UNA linea, siempre. Con tres cuadros la ruta del titulo
                   crece y al pasar a dos renglones esa tarjeta mide 334px
                   contra los 308 de sus vecinas: dos tarjetas de la misma
                   fila tienen que medir lo mismo (regla #145). El nombre
                   completo queda en el `title=`. */
                white-space: nowrap; overflow: hidden;
                text-overflow: ellipsis; }
/* Cuantas hojas hay: va en el titulo y no en un `st.caption` aparte (que
   sumaria un renglon), pero con menos peso que el nombre. En una tabla que
   scrollea, sin el numero no se ve si son 12 productos o 400. */
.inv-rank-tit-n { font-size: 12px; font-weight: 500; opacity: .55;
                  margin-left: 6px; }
</style>
"""

# Cuántas filas RESERVA cada tabla antes de scrollear por dentro. El 8 es el
# techo de Compras (`proveedor.py::_FILAS_RANK`) y viaja con el resto del
# look: dos tablas con el mismo tema y el mismo alto de fila pero distinta
# cantidad de filas a la vista no se leen como la misma tabla.
FILAS_RANK = 8

# Reparto horizontal de la fila de arriba, por cantidad de cuadros. Con TRES
# el ranking cede (1.2 y no 1.7): medido en 1366x768, con (1.5, 1, 1) le
# quedaban 194px a la columna de nombres —que miden ~110— mientras los dos
# cuadros de la derecha cortaban "RB ALIMENTOS PRODUCCION" (185px de texto
# en 171 de celda). El ancho sobrante estaba del lado que no lo necesitaba.
COLUMNAS_NIVELES = {1: (1,), 2: (1.7, 1), 3: (1.2, 1, 1)}

# Y el FORMATO de un cuadro de desglose depende de lo mismo, porque el ancho
# decide el formato (regla #349). Medido en 1366x768: con dos cuadros la
# grilla de la derecha mide 413px y con tres, 306 — y en 306 no entran a la
# vez un nombre largo, un monto exacto y la columna "%".
#
#   · `flex_nombre` 5 contra 2 del ranking: el nombre es lo único que no se
#     puede abreviar.
#   · `monto_corto`: "S/ 39.2k" en vez de "S/ 39,210" libera ~15px. Los
#     montos exactos siguen en el ranking de la izquierda, que es ancho.
#   · `ancho_barra` 0.30: la barra y el monto comparten celda (barra de
#     fondo, texto a la derecha), así que en una celda angosta la barra
#     tiene que ceder o el número termina escrito sobre el morado.
FORMATO_DETALLE = {
    2: {"ancho_pct": 64, "flex_nombre": 3, "ancho_barra": 0.45},
    3: {"ancho_pct": 52, "flex_nombre": 5, "ancho_barra": 0.30,
        "monto_corto": True},
}

# Y el RANKING de la izquierda necesita lo suyo por el mismo motivo: al ceder
# ancho para que entraran tres cuadros, sus 416px de grilla dejaban la
# columna de nombres en 161 y empezaba a cortar los que los desgloses habían
# dejado de cortar. Los montos siguen EXACTOS acá —es el cuadro ancho, el
# que se lee como fuente del número— así que lo que cede es el ancho de la
# barra.
FORMATO_RANKING = {
    1: {},
    2: {},  # los defaults de `tabla_ranking`: 80 / flex 2 / barra 0.62
    3: {"ancho_pct": 64, "flex_nombre": 3, "ancho_barra": 0.45},
}

# Qué categorías se ESCRIBEN como nombre propio en vez de como las grita el
# ERP (pedido del 2026-09-13: "que las letras en el cuadro de familia y
# subfamilia sean nombre propio"). Son las frases largas —"BEBIDAS CON
# ALCOHOL", "PESCADOS Y MARISCOS"— donde ocho filas de mayúsculas se leen
# como un bloque; área y sub almacén quedan gritados porque son nombres
# cortos ("COCINA", "BARRA", "CAVA") y ahí el grito no molesta.
#
# Se decide por el NOMBRE del nivel y no por su posición: la familia es el
# segundo cuadro en una vista y el primero en otra, así que atarlo a "el
# cuadro 2" la dejaría gritada en una de las dos.
CATEGORIAS_NOMBRE_PROPIO = ("familia", "subfamilia")

# Cómo se llama la fila cuya categoría viene vacía. `requerimientos.parquet`
# trae 2.944 filas sin subfamilia (2% del total, medido contra R2 el
# 2026-09-13): sin esto el cuadro de Subfamilia abre con una fila "nan" —
# que además es CLICKEABLE y recorta la tabla de abajo a un nombre que no
# existe. La misma normalización que arma esta clave es la que filtra
# (`recorte`), así que lo que se ve y lo que se compara no se pueden
# separar. De paso une los espacios de sobra con los que el ERP manda
# algunas categorías ("CAVA ", "GASTOS OPERATIVOS ").
SIN_DATO = "(sin dato)"

_VACIOS = ("", "nan", "none", "nat", "<na>", "null")


def claves(d, col):
    """La columna `col` normalizada a CLAVE de agrupación.

    Una sola función para las dos cosas que tienen que coincidir o la cadena
    miente: con qué texto se AGRUPA (y por lo tanto qué dice la fila) y con
    qué se FILTRA cuando el usuario la clickea."""
    s = d[col].astype(str).str.strip()
    return s.mask(s.str.lower().isin(_VACIOS), SIN_DATO)


def texto_cat(nombre_cat, valor):
    """Cómo se ESCRIBE `valor` cuando es de la categoría `nombre_cat`.

    El valor crudo no se toca nunca: es la clave con la que se filtra el df
    (ver el docstring de `nombre_propio`, que explica la misma separación del
    lado de Compras). Esto es sólo para mostrar."""
    if (not valor or valor == SIN_DATO
            or nombre_cat not in CATEGORIAS_NOMBRE_PROPIO):
        return valor
    return nombre_propio(valor)


def recorte(d, ruta):
    """`d` filtrado por la ruta elegida hasta acá — tríos (columna, clave,
    texto). La clave se compara contra `claves()` y no contra la columna
    cruda: es lo que hace que la fila "(sin dato)" y las categorías con
    espacios de sobra recorten lo que dicen recortar."""
    for _col, _val, _ in ruta:
        if _col and _val:
            d = d[claves(d, _col) == _val]
    return d


def tabla_ranking(d, col_grp, col_val, nombre_grp, key, *,
                  ancho_pct=80, flex_nombre=2, ancho_barra=0.62,
                  monto_corto=False, nombre_bonito=False, abre_en=(),
                  abrir_en_mayor=False, etiqueta_valor="Valorizado"):
    """El ranking de un nivel, como TABLA con barra de progreso.

    Es la tabla-ranking del repo, la misma que el Ranking de proveedores de
    Compras: `CSS_RANKING_GRID` sobre `theme="streamlit"` (franja en vez de
    caja, todo blanco, sin lineas verticales, cuerpo de 11.5px), filas de
    `ALTO_FILA_RANK`, ocho a la vista y el resto por scroll interno, y una
    fila TOTAL fija abajo. La barra NO es un `cellRenderer` (ni la clase
    `init()/getGui()` de la regla #25, ni los sparklines de AG Grid, que son
    Enterprise) sino el FONDO de la celda, un `linear-gradient` cortado en el
    % del valor. Los colores salen de `tema.py` y no de `var(--accent)` a
    proposito: el grid vive en un iframe propio y las variables CSS del
    documento padre no llegan.

    Clic en una fila = TOGGLE del foco; devuelve la categoria elegida para
    que el eslabon siguiente se recorte a ella. Sin seleccion devuelve None,
    salvo que el caller pida un default con `abrir_en_mayor`: ahi devuelve el
    primer nombre de `abre_en` que exista en los datos y, si ninguno esta, la
    categoria mayor. Asi la tarjeta de al lado nunca esta vacia; soltar la
    seleccion vuelve a ese default, no a "nada".

    El default es del PRIMER nivel y no de los siguientes, a proposito: si un
    desglose tambien se auto-enfocara, la tabla de hojas de abajo abriria
    recortada y no habria forma de ver el nivel entero. A diferencia de
    `plotly_chart(on_select=...)`, AgGrid devuelve la seleccion VIGENTE en
    cada run —es estado, no un evento que se repite—, asi que aca no hacen
    falta ni la key dinamica por foco ni el `st.rerun()` que evitan el toggle
    infinito del grafico (regla #399).

    Lo unico que cambia entre el ranking y un desglose es el reparto
    horizontal, porque una tarjeta de desglose mide 306-449px contra los 770
    del ranking y ahi el ancho decide el formato (regla #349) — ver
    `FORMATO_RANKING` y `FORMATO_DETALLE`.
    """
    from st_aggrid import AgGrid, JsCode

    met = pd.to_numeric(d[col_val], errors="coerce").fillna(0)
    serie = met.groupby(claves(d, col_grp)).sum().sort_values(ascending=False)
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
    _crudos = [str(i) for i in serie.index]
    tabla = pd.DataFrame({
        # Lo que se VE puede ir en capitalización de nombre propio; lo que se
        # COMPARA es `_crudo`, unas líneas más abajo. Misma separación que el
        # Ranking de proveedores con su `_prov_raw`: el texto formateado ya
        # no matchea contra el parquet, así que usarlo para filtrar
        # devolvería un df vacío sin decir por qué.
        col_nombre: ([texto_cat(nombre_grp, x) for x in _crudos]
                     if nombre_bonito else _crudos),
        etiqueta_valor: serie.values,
        "%": _pcts,
        "_crudo": _crudos,
        # Ocultas: el % de LLENADO de la barra (contra la mayor MAGNITUD, que
        # no es el mismo numero que la columna "%"), y el signo, que se lee
        # por color y no por direccion (regla #80). La columna visible
        # mantiene el valor con signo; sin `_neg`, un valor negativo pintaria
        # una barra larga indistinguible de uno grande.
        "_barra": [abs(v) / _mayor * 100 for v in serie.values],
        "_neg": [bool(v < 0) for v in serie.values],
    })
    # La fila TOTAL reemplaza al KPI que vivia arriba de esta tabla (pedido
    # del 2026-09-13: "quitar el KPI"). Mismo mecanismo que el Ranking de
    # proveedores: un dict calculado en PYTHON + `pinnedBottomRowData`, no el
    # `"grandTotalRow"` nativo, que en este repo solo esta probado junto a
    # `pivotMode=True` y esta tabla es plana. Suma lo que la tabla MUESTRA.
    # "TOTAL" no pasa por `nombre_propio` —quedaría "Total"— porque no es un
    # nombre del ERP sino el rótulo de la fila de cierre.
    fila_total = {col_nombre: "TOTAL", etiqueta_valor: round(total, 2),
                  "%": round(sum(_pcts), 2)}

    # La barra llega al 62% de la celda y el texto va a la DERECHA: asi nunca
    # se pisan (con la barra al 100% el monto caia sobre el morado, texto
    # oscuro sobre fondo oscuro). No falsea la lectura: todas se escalan
    # igual, las proporciones entre filas se mantienen. La pista va
    # transparente, no tintada: con fondo, la columna entera se lee como un
    # bloque lavanda que compite con las barras.
    # `justifyContent` es obligatorio: el `display:flex` de esta misma regla
    # anula el alineado a la derecha que trae `type: numericColumn`.
    # La fila TOTAL no dibuja barra: no hay `_barra` contra que escalarla
    # (seria 100% de si misma, una barra llena sin informacion) y el fondo lo
    # pone `getRowStyle` — un `background` aca se lo comeria, porque la celda
    # pinta ENCIMA de la fila.
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
    # Misma paleta que la fila TOTAL del Ranking de proveedores: dos filas de
    # cierre del mismo idioma visual. SIN `borderTop`: la linea sobre los
    # totales la dibuja (o no) el tema en `.ag-floating-bottom`, y un inline
    # aca se apilaria con ella dando dos rayas pegadas de distinto color.
    _js_fila_total = JsCode(
        "function(p){ if(p.node.rowPinned){ return {"
        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
        f"'color':'{ACENTO_TEXTO_OSCURO}'"
        "}; } }")
    # El monto abreviado a miles es para las celdas angostas (ver
    # `FORMATO_DETALLE`): abajo de 1.000 sigue exacto, porque ahi el redondeo
    # a "S/ 0.4k" perderia el dato en vez de acortarlo.
    _js_soles = JsCode(
        "function(p){ if (p.value==null) return '';"
        " var v = p.value;"
        + (" if (Math.abs(v) >= 1000) return 'S/ ' +"
           " (v/1000).toLocaleString('es-PE',{maximumFractionDigits:1})"
           " + 'k';" if monto_corto else "")
        + " return 'S/ ' + Math.round(v).toLocaleString('es-PE'); }")
    # Entero y no un decimal, igual que el Ranking de proveedores: "79%" y no
    # "79.0%". La columna es angosta y el decimal no cambia ninguna decision:
    # para el numero exacto esta el monto de al lado.
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' :"
        " Math.round(p.value) + '%'; }")
    # AG Grid, por si solo, NO deselecciona al reclickear la fila ya
    # seleccionada (pide Ctrl+clic, que nadie descubre). `setSelected(valor,
    # true)` limpia las demas -> sigue siendo seleccion unica. El guard de
    # `rowPinned` va afuera: sin el, clickear la fila TOTAL la "selecciona"
    # como si fuera una categoria real y el cuadro de al lado intentaria
    # enfocar algo llamado "TOTAL" que no existe en los datos.
    _js_toggle = JsCode(
        "function(e){ if (e.node.rowPinned) return;"
        " e.node.setSelected(!e.node.isSelected(), true); }")

    # Ocho filas de datos y el resto por scroll interno, como el Ranking de
    # proveedores. `extra` es todo lo que el grid mide y no son esas filas:
    # el cromo (cabecera + borde + chrome del tema) mas la fila TOTAL, que
    # reserva su espacio DENTRO del `height=` — sin ese sumando le comeria
    # una fila a los datos. El `max(1, ...)` deja la cabecera y el TOTAL con
    # una fila de aire en el caso vacio, en vez de un grid de 0 filas que AG
    # Grid dibuja recortando su propio overlay.
    #
    # EL ALTO SALE DE LOS DATOS y no se fuerza parejo en toda la fila, aunque
    # eso deje las tres tarjetas de la cadena con alturas distintas (308, 140
    # y 212px con el sub almacén PRODUCCION: 8 categorías, 1 familia y 4
    # subfamilias). Se probó lo otro el 2026-09-13 —reservar `FILAS_RANK` en
    # los tres cuadros— y sale peor: el iframe del ranking se reporta al
    # DOBLE y la tarjeta queda con 250px de blanco debajo de una tabla que
    # adentro mide bien.
    _filas = min(FILAS_RANK, max(1, len(serie)))
    _alto = alturas.por_filas(_filas, px_fila=ALTO_FILA_RANK,
                              extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                              minimo=0)
    # El alto, ATADO desde el documento padre. El `height=` de abajo ya se lo
    # dice al componente, y no alcanza: st_aggrid mide su contenido y le
    # reporta a Streamlit un `setFrameHeight`, que termina como `style
    # height` INLINE sobre el iframe y le gana a su propio atributo `height`.
    # Medido el 2026-09-13 en las dos vistas que usan esta tabla: atributo
    # 255 (8 filas) e inline 508, con la tarjeta en 554 contra los 308 de sus
    # vecinas de fila. En Movimientos aparecía recién DESPUÉS del primer
    # clic, que es lo que lo hacía parecer un problema de datos: los cuadros
    # de desglose llevan la ruta en la key, así que cada rerun estrena
    # componente y nace midiendo bien; el ranking conserva la suya —tiene
    # que conservarla, ahí vive la fila marcada— y se queda con el número
    # que reportó.
    #
    # Se arregla en DOS sitios porque son dos capas distintas y las dos
    # fallan solas: `CSS_RANKING_GRID` le pone `height: 100%` al
    # `.ag-root-wrapper` (que sin eso computa `auto` y se desborda de su
    # contenedor), y esta regla ata el IFRAME, porque el componente ya
    # reportó su número antes de que ese CSS llegara y Streamlit no lo vuelve
    # a preguntar. Los DOS nodos y no sólo el iframe: Streamlit escribe el
    # alto reportado sobre el `stElementContainer` que lo envuelve Y sobre el
    # iframe, así que atando sólo el de adentro la tarjeta no se mueve. Sin
    # guard de "una sola vez" (regla #59). Ver regla #410 — la midió
    # Inventario el mismo día, sobre esta misma tabla.
    st.markdown(
        f"<style>div.st-key-{key}, div.st-key-{key} iframe "
        f"{{ height: {_alto}px !important; }}</style>",
        unsafe_allow_html=True)

    resp = AgGrid(
        tabla,
        gridOptions={
            "columnDefs": [
                {"field": col_nombre, "flex": flex_nombre,
                 "tooltipField": col_nombre},
                {"field": etiqueta_valor, "flex": 2, "type": "numericColumn",
                 "cellStyle": _js_barra, "valueFormatter": _js_soles},
                {"field": "%", "width": ancho_pct, "type": "numericColumn",
                 "valueFormatter": _js_pct},
                {"field": "_barra", "hide": True},
                {"field": "_neg", "hide": True},
                {"field": "_crudo", "hide": True},
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
        # El tema de fabrica no alcanza: filas blancas, cuerpo de 11.5px y el
        # marco de franja salen de `CSS_RANKING_GRID`, y el unico camino es
        # `custom_css=` porque el grid es un iframe y el `<style>` del
        # documento padre no entra. Ese dict ya estila la fila SELECCIONADA
        # (`.ag-row-selected::before`, el acento al 12%), que aca es el foco
        # de la cadena: sin marcarla, no se ve sobre que categoria esta
        # mirando el cuadro de la derecha.
        custom_css=CSS_RANKING_GRID,
        height=_alto,
        update_on=["selectionChanged"],
        key=key,
    )
    sel = getattr(resp, "selected_rows", None)
    if sel is not None and len(sel):
        fila = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
        # `_crudo` y no la columna visible: con `nombre_bonito` aquélla pasó
        # por `nombre_propio` y ya no es la clave de los datos.
        return str(fila["_crudo"])
    if not abrir_en_mayor:
        return None
    # Sin seleccion: el default. La comparacion va normalizada porque el
    # nombre viaja escrito a mano en el llamador y el ERP los manda gritados
    # y con espacios de sobra.
    _norm = {str(i).strip().upper(): str(i) for i in serie.index}
    for _cand in abre_en:
        _hit = _norm.get(str(_cand).strip().upper())
        if _hit is not None:
            return _hit
    return str(serie.index[0])


def tabla_detalle(d, col_next, nombre_next, col_val, key, ruta=(),
                  formato=None, etiqueta_valor="Valorizado"):
    """Un eslabón más de la cadena: el desglose del recorte que ya está en
    foco — la pregunta natural después de "cuánto pidió COCINA" es "de qué se
    compone".

    Es la MISMA tabla que el ranking de la izquierda (`tabla_ranking`), no
    una copia: sólo cambia el reparto de anchos. Y tiene clic propio:
    devuelve la categoría elegida (o None) para que el eslabón siguiente —y
    la tabla de hojas de abajo— se recorten a ella.

    `ruta` es el recorte que ya está aplicado, en tríos (columna, clave,
    texto): la clave FILTRA el df y el texto arma el título. Van los dos
    porque no son lo mismo — familia y subfamilia se escriben en
    capitalización de nombre propio y esa forma ya no matchea contra el
    parquet. Se recibe hecha en vez de recalcularse acá porque el caller la
    va acumulando nivel a nivel: con dos eslabones ya no alcanza un
    `col_grp`/`foco` sueltos, y tres argumentos paralelos por nivel es lo que
    convierte una cadena en un `if` por profundidad (regla #407).

    La `key` que le pasa el caller lleva el foco adentro a propósito: al
    cambiar lo de arriba, la grilla es OTRA y nace sin selección — que es lo
    que evita que un sub-foco sobreviva al recorte que lo justificaba."""
    dd = recorte(d, ruta)
    # El titulo nombra sólo el ÚLTIMO eslabón, no la ruta entera: con tres
    # cuadros "COCINA › ALIMENTOS — por subfamilia" no entra en 339px, y de
    # dónde viene ya lo dice el cuadro de la izquierda. La ruta completa va
    # al `title=`, que es donde se la puede leer sin que empuje el layout.
    _ruta_txt = " › ".join(str(t) for _, v, t in ruta if v)
    _de = next((str(t) for _, v, t in reversed(list(ruta)) if v), "")
    if not col_next or dd.empty:
        st.caption(f"Sin desglose adicional para {_de}." if _de
                   else "Sin desglose adicional.")
        return None
    st.markdown(
        f'<div class="inv-rank-tit" title="{_ruta_txt.replace(chr(34), "")}">'
        f'{_de} — por {nombre_next}</div>', unsafe_allow_html=True)
    return tabla_ranking(
        dd, col_next, col_val, nombre_next, key,
        nombre_bonito=nombre_next in CATEGORIAS_NOMBRE_PROPIO,
        etiqueta_valor=etiqueta_valor,
        **(formato or FORMATO_DETALLE[2]))


def tabla_hojas(d, ruta, *, col_hoja, col_val, key, nombre_hoja="Producto",
                titulo="Productos", col_ctx=None, nombre_ctx="Área",
                col_cant=None, col_punit=None, col_unidad=None,
                etiqueta_valor="Valorizado"):
    """La franja de abajo: las HOJAS del recorte, como tabla ordenable.

    Lista TODAS las del recorte, no las 20 más grandes: "ya que es una tabla,
    el usuario puede hacer scroll" (2026-09-13). Un top-N en una tabla
    ORDENABLE miente por partida doble — ordenar por "Precio unitario"
    reordena esos 20, no los productos caros, y el nº 21 por valorizado no
    existe para el usuario (regla #403). El scroll lo hace la GRILLA, que
    reserva las mismas ocho filas que los cuadros de arriba; la tarjeta no
    crece ni saca barra propia.

    `ruta` son los tríos (columna, clave, texto) de la cadena de arriba hasta
    donde el usuario haya clickeado: la clave filtra, el texto se escribe. El
    % de participación se recalcula sobre ESE recorte, no sobre el total del
    reporte, porque el criterio de la tarjeta es "sumar 100% con lo que el
    usuario ya está viendo arriba".

    Las columnas OPCIONALES se dibujan sólo si el parquet las trae: `UM` sale
    de `unidad_corta` —el mismo mapa que rotula las cantidades de Compras— y
    va pegada a "Cantidad", que es el número al que le da sentido (34 de
    qué); `requerimientos.parquet` no tiene unidad, así que ahí la columna no
    existe en vez de existir vacía. El TOTAL deja la UM en blanco: sumar kg
    con Lt no da una unidad.

    Barra de "Participación %" + checkbox con "Selección %" recalculada en
    vivo (sin rerun de Streamlit): MISMO patrón que la Tabla principal de
    Inventario (`tablas/desktop.py`) — la barra-gradiente vive en `cellStyle`
    de AgGrid, no en un Styler de pandas."""
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

    d_panel = recorte(d, ruta)
    if not (col_hoja and col_val):
        st.info("Faltan columnas para esta tabla.")
        return

    _val_panel = pd.to_numeric(d_panel[col_val], errors="coerce").fillna(0)
    cols_txt = {nombre_hoja: claves(d_panel, col_hoja)}
    if col_ctx:
        cols_txt[nombre_ctx] = claves(d_panel, col_ctx)
    base = pd.DataFrame(cols_txt)
    base[etiqueta_valor] = _val_panel.values
    if col_cant:
        base["Cantidad"] = pd.to_numeric(d_panel[col_cant],
                                         errors="coerce").fillna(0).values
    if col_unidad:
        base["UM"] = [unidad_corta(u) for u in d_panel[col_unidad]]
    if col_punit:
        base["Precio unitario"] = pd.to_numeric(d_panel[col_punit],
                                                errors="coerce").values

    # `first` para la UM y no una agregación: es un atributo del producto, no
    # una medida. Va dentro del `agg` y no como clave más del groupby a
    # propósito — si un producto llegara con dos unidades distintas, una
    # clave más lo partiría en dos filas que suman mal; así se queda en una y
    # a lo sumo rotula con la primera.
    _claves_grp = [nombre_hoja] + ([nombre_ctx] if col_ctx else [])
    _agg = {etiqueta_valor: (etiqueta_valor, "sum")}
    if col_cant:
        _agg["Cantidad"] = ("Cantidad", "sum")
    if col_unidad:
        _agg["UM"] = ("UM", "first")
    if col_punit:
        _agg["Precio unitario"] = ("Precio unitario", "mean")
    g = base.groupby(_claves_grp, as_index=False).agg(**_agg)
    if g.empty:
        st.info("Sin datos.")
        return

    # Participación % contra el total del FOCO (no sólo el top mostrado) —
    # sobre el total neto que el usuario ya ve arriba, no sobre una suma
    # parcial.
    _total_foco = float(_val_panel.sum())
    g["Participación %"] = ((g[etiqueta_valor] / _total_foco * 100)
                            if _total_foco else 0.0)
    # Semilla; el valueGetter de abajo la recalcula en vivo.
    g["Selección %"] = g["Participación %"]
    g = g.sort_values(etiqueta_valor, ascending=False)

    # El encabezado dice el recorte Y cuántas filas trae: sin el número, una
    # tabla que scrollea no deja ver si son 12 productos o 400.
    _ruta = " › ".join([str(t) for _, v, t in ruta if v])
    st.markdown(
        f'<div class="inv-rank-tit">{titulo}'
        + (f" · {_ruta}" if _ruta else "")
        + f' <span class="inv-rank-tit-n">{len(g):,}</span></div>',
        unsafe_allow_html=True)

    # Fila TOTAL, igual que los cuadros de arriba. "Precio unitario" queda
    # VACÍA a propósito: es un ratio y un ratio no se suma ni se promedia
    # sobre el agregado (la misma trampa que la regla #199). "Selección %"
    # tampoco lleva total — su valor lo calcula en vivo el valueGetter contra
    # lo tildado, así que un número fijo ahí mentiría en cuanto se marque la
    # primera fila.
    _fila_total = {nombre_hoja: "TOTAL", nombre_ctx: "", "UM": "",
                   etiqueta_valor: round(float(g[etiqueta_valor].sum()), 2),
                   "Participación %": round(
                       float(g["Participación %"].sum()), 1)}
    if col_cant:
        _fila_total["Cantidad"] = round(float(g["Cantidad"].sum()), 1)

    _orden = ([nombre_hoja] + ([nombre_ctx] if col_ctx else [])
              + (["Cantidad"] if col_cant else [])
              + (["UM"] if col_unidad else [])
              + (["Precio unitario"] if col_punit else [])
              + [etiqueta_valor, "Participación %", "Selección %"])
    gb = GridOptionsBuilder.from_dataframe(g[_orden])
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    # minWidths ajustados para que las columnas entren sin scroll horizontal
    # en la franja de abajo (~911-1117px medido en vivo): con los anchos
    # "cómodos" originales quedaban ~19px cortos contra el ancho disponible
    # real — la última columna, al serlo, quedaba virtualizada fuera de vista
    # (ni scrolleable a simple vista: parecía que no existía).
    gb.configure_column(nombre_hoja, pinned="left", minWidth=150)
    if col_ctx:
        # La columna de CONTEXTO se esconde cuando la cadena de arriba ya la
        # fijó: con el foco puesto escribe la misma palabra en todas las
        # filas y el dato ya está en el título de la tarjeta — el caso exacto
        # de la regla #239. Oculta y no borrada: sigue en el modelo por si
        # hace falta ordenar por ella, y son los 90px que necesita la UM para
        # entrar sin empujar la tabla a scroll horizontal.
        _ctx_fijo = any(c == col_ctx and v for c, v, _t in ruta)
        gb.configure_column(nombre_ctx, minWidth=90, hide=_ctx_fijo)
    if col_unidad:
        # Angosta: son tres letras ("kg", "Lt", "und"). Sin `flex`, para que
        # no se coma el ancho que necesitan los nombres de producto.
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
    if col_cant:
        gb.configure_column("Cantidad", type=["numericColumn"], minWidth=90,
                            valueFormatter=_num_fmt)
    if col_punit:
        gb.configure_column("Precio unitario", type=["numericColumn"],
                            minWidth=100, valueFormatter=_money_fmt)
    gb.configure_column(etiqueta_valor, type=["numericColumn"], minWidth=110,
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
    gb.configure_column("Participación %", minWidth=115,
                        type=["numericColumn"], cellStyle=_pct_bar_style,
                        valueFormatter=_pct_fmt)
    gb.configure_column(
        "Selección %", minWidth=115, type=["numericColumn"],
        cellStyle=_pct_bar_style, valueFormatter=_pct_fmt,
        # Recalcula en vivo contra la suma de getSelectedNodes() — sin
        # selección, null (el formatter de arriba pinta "–"). El nombre de la
        # columna de valor entra por `.replace` y no por f-string: el cuerpo
        # de la función lleva llaves de JS, y un f-string las tomaría suyas.
        valueGetter=JsCode("""
            function(params) {
                if (!params.data) return null;
                var val = Number(params.data[COLVAL]);
                if (isNaN(val)) return null;
                var nodes = (params.api && params.api.getSelectedNodes)
                    ? params.api.getSelectedNodes() : [];
                if (!nodes || nodes.length === 0) return null;
                var suma = 0;
                nodes.forEach(function(n) {
                    if (n.data) {
                        var v = Number(n.data[COLVAL]);
                        if (!isNaN(v)) suma += v;
                    }
                });
                if (suma <= 0) return null;
                return (val / suma) * 100;
            }
        """.replace("COLVAL", repr(etiqueta_valor))),
    )
    gb.configure_selection("multiple", use_checkbox=True, header_checkbox=True)
    grid_options = gb.build()
    # Sin esto, la última columna ("Selección %") quedaba virtualizada fuera
    # de rango y NUNCA renderizaba celda — bug real, verificado en vivo: el
    # header aparecía pero la fila tenía un hueco vacío del ancho de una
    # columna. La grilla es chica, así que desactivar la virtualización
    # horizontal no cuesta nada de performance. Causa raíz probable: AG Grid
    # calcula el rango visible ANTES de que el iframe de Streamlit se asiente
    # en su ancho final.
    grid_options["suppressColumnVirtualisation"] = True
    # Las tablas de la sección miden lo mismo y se leen igual: mismo alto de
    # fila y de cabecera que el ranking, mismo tema, mismo CSS.
    grid_options["rowHeight"] = ALTO_FILA_RANK
    grid_options["headerHeight"] = ALTO_HEADER_RANK
    grid_options["pinnedBottomRowData"] = [_fila_total]
    # La fila TOTAL con la paleta de cierre de los cuadros de arriba.
    # `rowPinned` también apaga su checkbox: una fila que no es un producto
    # no se puede sumar a la selección (y "Selección %" la contaría dos
    # veces).
    grid_options["getRowStyle"] = JsCode(
        "function(p){ if(p.node.rowPinned){ return {"
        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
        f"'color':'{ACENTO_TEXTO_OSCURO}'"
        "}; } }")
    # AG Grid no sabe que un valueGetter "cambió" (no depende de ningún field
    # propio) — sin este refreshCells forzado tras cada click de checkbox,
    # "Selección %" se queda pintada con el valor anterior.
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
        # cuenta que `tabla_ranking` (ver el comentario de `extra` allá).
        height=alturas.por_filas(min(FILAS_RANK, max(1, len(g))),
                                 px_fila=ALTO_FILA_RANK,
                                 extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                                 minimo=0),
        custom_css=CSS_RANKING_GRID,
        allow_unsafe_jscode=True,
        # La key lleva el recorte entero: cambiar de foco estrena grilla, así
        # los checkboxes de "Selección %" no quedan marcados sobre productos
        # que ya no están en la tabla.
        key=key + "_" + (_slug("_".join(str(v) for _, v, _ in ruta if v))
                         or "global"),
    )


def seccion_cadena(d, *, pref, slug, niveles, col_val, col_hoja,
                   nombre_hoja="Producto", titulo_hojas="Productos",
                   col_ctx=None, nombre_ctx="Área", col_cant=None,
                   col_punit=None, col_unidad=None, abre_en=(),
                   etiqueta_valor="Valorizado", titulo_ranking=None):
    """La sección entera: el ranking, sus desgloses y la tabla de hojas.

    `niveles` es la cadena de agrupación en pares (columna, nombre): el
    primero es el ranking de la izquierda y los que siguen, un cuadro cada
    uno (hasta tres en total — más no entran en 1366px sin que el nombre de
    la categoría deje de leerse).

    Todos los cuadros se dibujan SIEMPRE: cada uno desglosa el recorte que
    viene de su izquierda, y la tabla de abajo muestra las hojas del recorte
    MÁS PROFUNDO que esté activo. El primer nivel abre con un foco por
    defecto (`abre_en`, o la categoría mayor) para que la tabla de abajo viva
    siempre en la franja ancha, que es donde entra: sin foco mostraba el
    universo entero con scroll horizontal (regla #405).

    `pref` es el prefijo de las keys, uno por dashboard ("inv", "mov"). Las
    tarjetas conservan el prefijo `ajuste_graf_card_`, de donde cuelga el CSS
    de tarjeta (`estilos/_80_cards.py` y `_20_compras_rail.py`): un nombre
    nuevo las dejaría sin marco."""
    # Sin guard de "inyectar una sola vez": un `st.markdown` de estilos con
    # ese guard DESAPARECE en el rerun siguiente (regla #59).
    st.markdown(CSS_TITULOS_DRILL, unsafe_allow_html=True)

    col_grp, nombre_grp = niveles[0]
    # columnas-internas: el ranking y sus desgloses, dentro de la sección. No
    # es una fila de drill de Compras: COLUMNAS_DRILL no aplica; el reparto
    # propio vive en `COLUMNAS_NIVELES`.
    cols = st.columns(COLUMNAS_NIVELES[len(niveles)])
    # La RUTA: los tríos (columna, clave, texto) elegidos hasta acá. Empieza
    # con el ranking y crece un eslabón por cuadro. Es lo que cada cuadro
    # recibe para recortarse y lo que la tabla de abajo recibe entera — sin
    # ella, cada nivel nuevo agregaba dos argumentos paralelos
    # (`col_sub`/`sub_foco`, `col_sub2`/`sub2_foco`…) y el tercero ya no
    # entraba sin un `if` por profundidad (regla #407).
    ruta = []
    with cols[0]:
        with st.container(border=True,
                          key=f"ajuste_graf_card_izq_{pref}_{slug}"):
            if not col_grp:
                st.info(f"No se encontró la columna de {nombre_grp}.")
            else:
                st.markdown(
                    '<div class="inv-rank-tit">'
                    + (titulo_ranking or f"{etiqueta_valor} por {nombre_grp}")
                    + "</div>", unsafe_allow_html=True)
                foco = tabla_ranking(
                    d, col_grp, col_val, nombre_grp,
                    key=f"{pref}_rank_grid_{slug}",
                    abre_en=abre_en, abrir_en_mayor=True,
                    nombre_bonito=nombre_grp in CATEGORIAS_NOMBRE_PROPIO,
                    etiqueta_valor=etiqueta_valor,
                    **FORMATO_RANKING[len(niveles)])
                ruta.append((col_grp, foco, texto_cat(nombre_grp, foco)))
    for _i, (_col_n, _nombre_n) in enumerate(niveles[1:]):
        # La key de la tarjeta conserva el prefijo `ajuste_graf_card_der_`
        # aunque sean dos: de ese prefijo cuelga el CSS por FAMILIA de
        # `estilos/_80_cards.py`. El sufijo `_n<i>` va al final por lo mismo
        # — el selector es `[class*=...der_]`.
        _key_card = (f"ajuste_graf_card_der_{pref}_{slug}"
                     + ("" if _i == 0 else f"_n{_i + 1}"))
        with cols[_i + 1]:
            with st.container(border=True, key=_key_card):
                # Sin recorte de arriba no hay nada que desglosar: el cuadro
                # queda callado en vez de repetir el nivel anterior. Con el
                # default de `abre_en`, al primero nunca le falta.
                if not [v for _, v, _t in ruta if v]:
                    st.caption("Elegí una fila del cuadro anterior.")
                    continue
                # La key lleva la ruta adentro a propósito: al cambiar lo de
                # arriba, la grilla es OTRA y nace sin selección.
                _k = _slug("_".join(str(v) for _, v, _t in ruta if v))
                _sub = tabla_detalle(
                    d, _col_n, _nombre_n, col_val,
                    key=f"{pref}_det_grid_{slug}_{_i}_{_k}", ruta=tuple(ruta),
                    formato=FORMATO_DETALLE[len(niveles)],
                    etiqueta_valor=etiqueta_valor)
                ruta.append((_col_n, _sub, texto_cat(_nombre_n, _sub)))
    with st.container(border=True,
                      key=f"ajuste_graf_card_abajo_{pref}_{slug}"):
        tabla_hojas(d, tuple(ruta), col_hoja=col_hoja, col_val=col_val,
                    key=f"{pref}_hojas_grid_{slug}", nombre_hoja=nombre_hoja,
                    titulo=titulo_hojas, col_ctx=col_ctx,
                    nombre_ctx=nombre_ctx, col_cant=col_cant,
                    col_punit=col_punit, col_unidad=col_unidad,
                    etiqueta_valor=etiqueta_valor)
