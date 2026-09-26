"""graficos.compras.producto - drill de Producto.

Ranking de TODOS los productos comprados (valor, cantidad, UM, precio real
de inicio/fin de periodo y su variación) con el mismo patrón de tabla-
ranking + clic-para-enfocar que graficos/compras/proveedor.py. El producto
en foco muestra su evolución: una barra por período (Semana / Mes / Año)
con el precio promedio y el valor comprado escritos encima. Esa tarjeta va
a la IZQUIERDA y tiene VENTANA PROPIA elegible (Rango/3m/12m/24m/Todo) que
abre en los últimos 3 meses (2026-09-12; antes abría en 12m). La fecha de
la sección vive en la fila del título de «Compras por familia» y manda
sobre las tablas. Filtro de proveedores no hay: se pidió fuera el mismo día
(regla #382).

DEBAJO DEL GRÁFICO, EN SU MISMA TARJETA, LA ZONA (2026-09-20, regla #480).
Alterna sola, sin control propio: sin foco es el RESUMEN —una fila por
barra, en el orden del eje— y un clic en una barra la pasa al DETALLE de
ese período, una fila por compra con su proveedor; tocar la misma barra
vuelve al resumen. Es el patrón de «Compra por período» (#476) y la misma
grilla. El alto de la figura sale de restarle la zona a la tarjeta, no de
un rol: ver `_CROMO_CARD_EVO`.

Reemplaza a los antiguos drills "Precio top 10", "Precio por compra" y
"Cantidad por producto" (graficos/compras/cantidad.py, eliminado 2026-08-17):
las tres separaban precio-promedio, precio-real y cantidad/valor de UN mismo
producto en tres pantallas distintas — acá conviven en una, con selectores
aplanados a texto en vez de tabs/pills con caja (a pedido, para no ocupar
sitio).

ENCIMA del ranking, en su misma tarjeta, el drill jerárquico: Familia |
Subfamilia (2026-09-09, a pedido). Un clic en una familia repuebla las
subfamilias y recorta el ranking a esa familia; un clic en una subfamilia
lo recorta a ella. Cada % es sobre su padre, no sobre el total.

Hasta el 2026-09-12 había un TERCER panel —los productos del grupo
elegido— y el ranking vivía en otra tarjeta, debajo, al lado de la
Evolución. Se pidió fuera el panel y que el ranking hiciera su papel: dos
tablas de productos una encima de la otra eran la misma pregunta con dos
respuestas. Con eso la fila queda [paneles + ranking] | Evolución, como el
drill de Proveedor. Ver regla #381.

Las tres tablas se ven como el Ranking de Proveedores: mismo
`CSS_RANKING_GRID` (franja en vez de caja, todo blanco, sin líneas
verticales, cuerpo 11.5 y el texto en violeta), mismas filas de 24px y la
misma capitalización de nombre propio (regla #380). Y sin captions debajo:
lo que decían vive en los `headerTooltip` de las columnas, que no gastan
alto.
"""

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from st_aggrid import AgGrid, JsCode

from cortes import MESES_ABR_ES
from tema import (
    ACENTO, ERROR, EXITO, GRIS_TEXTO, LAVANDA_FOCO, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _compras_layout, _compras_truncar, _slug, preservar_widgets,
    rango_tarjeta,
)
from graficos.ventas_comparativo import _fmt_soles_compacto
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CATEGORIA_SEC, COLUMNAS_DRILL_ESPEJO,
    CROMO_GRID_RANK, GAP_DRILL, moda_por_grupo, selector_fecha_tarjeta,
    # Las de la variación contra la barra anterior (#470): nacieron en
    # Semanal y viven en `_comun` desde que esta tarjeta pidió lo mismo.
    _UNIDAD_GRAN, _clave_grilla, _first_point, _fmt_variacion,
    _hover_variacion, _nota_variacion, _periodo_serie, _variaciones,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
# LA TABLA DE ABAJO ES LA MISMA QUE LA DE «Compra por período», y por eso su
# módulo dejó de llamarse `_semanal` el 2026-09-20: es la tabla de «el
# gráfico escrito» —una fila por barra, en el orden del eje— y la usan las
# dos vistas. `ALTO_FILA` viaja con ella porque el alto de la tarjeta se
# despeja contra el alto de SU fila, no contra un número copiado.
from tablas.compras_semanal import (
    ALTO_FILA, renderizar_compras_producto, renderizar_periodos,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos import alturas, periodo

_FILAS_PROD = 7
"""Filas que reserva el Ranking de productos. Un techo, no un alto: lo que
sobra scrollea adentro.

Desde el 2026-09-12 las dibuja a 24px (`ALTO_FILA_RANK`) y no a los 28 que
tenía: entró en la tarjeta de los paneles de Familia, que ya estaban a 24,
y dos altos de fila en la misma tarjeta se leían como dos tablas pegadas.

7, a pedido (2026-09-12, «quitemos dos filas al ranking de productos, para
que se reduzca la tarjeta»). Esa misma mañana había subido a 9 para
aprovechar el alto de una pantalla de 768; con la tarjeta ya sin techo
(regla #382) el alto que manda es el que el usuario quiere ver, no el que
cabe."""

_ALTO_FRAME = alturas.por_filas(
    _FILAS_PROD, px_fila=ALTO_FILA_RANK, extra=CROMO_GRID_RANK, minimo=0)

_FILAS_FAM = 6
"""Filas que RESERVAN los dos paneles de arriba (Familia | Subfamilia).

Los dos el mismo número a propósito: se leen como UNA grilla de dos
columnas, así que una altura por panel los dejaría terminando a dos
alturas distintas. Y es un techo, no un alto: lo que sobra scrollea
adentro.

6 desde el 2026-09-12, a pedido («una fila [menos] a la tabla de
subfamilias»). El pedido nombró sólo a Subfamilia, y bajan LAS DOS: van
lado a lado en la misma fila de columnas, que mide lo que la más alta, así
que achicar sólo la B no achicaba la tarjeta — dejaba la B terminando 24px
antes que la A. El panel A no pierde nada: las 8 familias del parquet son
5 con el filtro de entrada (medido sobre R2 el 2026-09-11) y las 5 entran
en 6 filas. El B scrollea, como ya lo hacía con 7: ALIMENTOS tiene 10
subfamilias. Venía de 8 (hasta el 2026-09-11) y de 7."""

_ALTO_FRAME_FAM = alturas.por_filas(
    _FILAS_FAM, px_fila=ALTO_FILA_RANK, extra=CROMO_GRID_RANK, minimo=0)
"""El `height=` de los dos AgGrid de Familia y Subfamilia."""

# La Evolución mide contra la tarjeta DE AL LADO, el mismo arreglo que
# `_ALTO_EVO` en proveedor.py: su alto no sale de los datos, así que si se
# pidiera por su cuenta la fila saldría en escalón y el piso `:has()` de
# estilos/_80_cards.py rellenaría la diferencia con blanco al pie.
#
# Las dos constantes son el CROMO de cada tarjeta —todo lo que mide y no
# son sus grids ni su figura—, MEDIDAS en el navegador el 2026-09-12
# (1280x650, con el layout final de ese día), no deducidas. Se miden las
# TARJETAS, no la suma de sus hijos: los hijos traen fracciones de px y
# la suma redondeada se pasaba por 2.
#   Ranking:   600 de tarjeta − 207 − 255 de grids = 138 (padding 32 +
#              fila de títulos con la fecha 30 + 8 del wrapper del grid de
#              paneles + título del ranking 14, por el `margin-bottom:
#              -16px` de `st.markdown` de la regla #162 + 8 del wrapper del
#              grid + tres gaps de 16)
#   Evolución: 528 de tarjeta − 384 de figura = 144 (padding 32 + nombre
#              del producto 6, por la misma #162 + ventana y granularidad
#              32 + las dos líneas de cifras 26 + tres gaps de 16)
# Con una sola línea de cifras (un producto que no fluctuó) la Evolución
# pide menos y el piso `:has()` rellena esos px al pie: es el caso raro.
_CROMO_CARD_RANK = 138

_FILAS_ZONA = 4
"""Cuántas filas de la zona de abajo se ven sin deslizar.

Es un TECHO, no un alto: lo que sobra scrollea DENTRO de la grilla, que es
el único sitio de esta vista donde se permite una barra (las tarjetas de
Producto no tienen techo desde la regla #382).

CUATRO Y NO MÁS porque cada fila se la saca a la figura: la tarjeta mide lo
que mide la del Ranking de al lado y ese total no cambia, así que la zona y
el gráfico se reparten el mismo presupuesto. Cuatro cubre el caso que se ve
de verdad —la ventana por defecto son 3 meses agrupados por Mes, o sea 3 ó
4 barras, y entran todas sin deslizar— y le deja 237px a la figura. Con
cinco la figura caía a 210 y con seis a 183.

La zona mide LO MISMO en sus dos estados, Resumen y Detalle: si midiera
distinto, tocar una barra cambiaría el alto de la tarjeta y la fila entera
bailaría con cada clic (es la #398, la misma razón por la que las dos
tablas de Semanal miden igual)."""

_ALTO_ZONA = alturas.por_filas(_FILAS_ZONA, px_fila=ALTO_FILA,
                               extra=CROMO_GRID_RANK, minimo=0)

# La tarjeta de la Evolución cambió de forma el 2026-09-20: la tabla «una
# fila por barra» dejó de vivir a lo ancho de la vista y bajó ADENTRO de
# esta tarjeta, a pedido. El cromo se recalcula, y son 157 + la zona,
# MEDIDO bloque por bloque en el navegador a 1366x768:
#
#   padding                                       32
#   fila 1 (nombre + ventana + granularidad)      22
#   las dos líneas de cifras                      26,4
#   rótulo de la zona                              5,2  (la #162 se come 16)
#   el wrapper de la grilla, por encima del iframe 7,6
#   CUATRO gaps de 16                             64
#                                                ────
#                                                157,2
#
# Los tres números que no se pueden deducir y hay que medir, porque la
# primera cuenta los erró y la tarjeta salió 13px más alta que su vecina:
# la fila de controles mide **22 y no 32** (los dos selectores van aplanados
# a texto, ver `_CSS_SELECTOR_TEXTO`), el bloque de la grilla suma **7,6
# propios** al alto del iframe, y los gaps son **cuatro y no tres** — la
# zona agregó uno.
_CROMO_CARD_EVO = 157 + _ALTO_ZONA

# El piso ya no es `alturas.MINI`: ver su docstring en `alturas.py`. Con los
# números de hoy la resta da 237 y el piso no ata — está para el día en que
# la tarjeta de al lado se achique.
_ALTO_EVO = max(alturas.FIG_CON_SU_TABLA,
                _ALTO_FRAME_FAM + _ALTO_FRAME + _CROMO_CARD_RANK
                - _CROMO_CARD_EVO)

_ETIQ_VENTANA_EVO = {
    periodo.HEREDA: "Rango de las tablas",
    "3m": "Últimos 3 meses",
    "12m": "Últimos 12 meses",
    "24m": "Últimos 24 meses",
    "Todo": "Todo el histórico",
}
"""Lo que muestra el desplegable de ventana del gráfico de Producto.

Sólo el TEXTO: el valor sigue siendo la cadena de `periodo.OPCIONES`, que
es contra lo que se compara (`== periodo.HEREDA`). «Rango de las tablas» y
no el «Rango» pelado de las otras tarjetas: acá el rango que hereda vive
en la tarjeta de AL LADO (el selector de «Compras por familia»), y
«Rango» a secas no dice cuál."""

_KEYS_WIDGET = ("compras_prod_gran_sel", "compras_prod_periodo")
"""Los controles de esta sección, para que la escalada no se los lleve.

La consume `preservar_widgets` en el `st.rerun(scope="app")` de más abajo:
ese rerun aborta la corrida antes de dibujarlos y Streamlit recolecta lo
que no se dibujó, así que sin esta tupla mover la fecha de la cabecera
devolvía la granularidad a «Mes» y la ventana a «Últimos 3 meses». Ver
`graficos/base.py::preservar_widgets` y `arquitectura.md` regla #373.
Hasta el 2026-09-12 había dos más, las del filtro de proveedores
(`cp_prod_prov_q`, `cp_prod_prov_cb::*`), que se fue ese día."""

# Eje X por granularidad: forzado a propósito. Con pocos puntos (rango de
# fecha corto, o un producto con 1-2 compras) Plotly no tiene de dónde sacar
# un paso de tick razonable y cae en sub-segundos ("23:59:59.9995 Jul 31,
# 2026") — visto en vivo con un solo bucket de Mes. `dtick` fija el paso al
# calendario real (mes/año) y `tickformat` la etiqueta, sin importar cuántos
# puntos haya.
_EJE_X_GRAN = {
    "Semana": dict(dtick=7 * 24 * 60 * 60 * 1000, tickformat="%d %b"),
    "Mes": dict(dtick="M1", tickformat="%b %Y"),
    "Año": dict(dtick="M12", tickformat="%Y"),
}


def _eje_x_kwargs(gran, agg):
    """Un tick por BARRA, rotulado en español.

    Hasta el 2026-09-20 esto era `_EJE_X_GRAN[gran]` —un `dtick` de
    calendario más un `tickformat`— y el eje decía «Aug 2026»: Plotly
    rotula en INGLÉS con su locale por defecto, que es la regla #241. Con
    `tickvals`/`ticktext` el rótulo lo escribe Python
    (`_rotulo_periodo`, sobre `cortes.MESES_ABR_ES`) y de paso se va la
    razón de ser del `dtick`: los ticks caen sobre los buckets REALES, así
    que ni hay que anclar un `tick0` semanal ni Plotly puede irse a
    sub-segundos ("23:59:59.9995 Jul 31, 2026") cuando hay un solo punto.

    `_EJE_X_GRAN` queda como respaldo del caso vacío, que no tiene buckets
    de los que sacar los ticks."""
    if agg.empty:
        return dict(_EJE_X_GRAN[gran])
    _vals = list(agg.index)
    return dict(tickmode="array", tickvals=_vals,
                ticktext=[_rotulo_periodo(_t, gran) for _t in _vals])


# LOS DOS CONTROLES DE LA CABECERA SON EL MISMO WIDGET desde el
# 2026-09-20: `st.selectbox` aplanado a texto con su chevron. La
# granularidad era un `st.pills` de tres cápsulas sin cápsula (Semana | Mes
# | Año, texto suelto); pasó a desplegable a pedido —«hagamos minimalista
# la granulación de semana mes año, en una línea desplegable y pongámosla
# en la misma fila del título»— y eso paga la fila entera: los tres
# rótulos en línea medían ~146px y el desplegable mide 74, que es lo que
# deja sitio para el nombre del producto al lado.
#
# Un selector cerrado dice UNA opción y las pills dicen las tres: se pierde
# saber qué más hay sin abrirlo. Es el precio del renglón que se ahorra, y
# el renglón se lo lleva la tabla de abajo.
_CSS_SELECTOR_TEXTO = f"""
<style>
/* Los dos selectores de la cabecera del gráfico («Últimos 3 meses ▾» y
   «Mes ▾»), APLANADOS A TEXTO: son texto suelto, no una caja contra unas
   palabras — al lado del nombre del producto una caja se leería como el
   dato principal. Misma receta que `cp_evo_ctrl` en _css_proveedor.py; se
   conserva el chevron, que es la única señal de que eso despliega. La
   ventana se fue y volvió el 2026-09-12: ver su comentario en
   `compras_prod_card_evo`. */
.st-key-compras_prod_ctrl [data-testid="stSelectbox"] div[role="group"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    min-height: 0 !important;
    height: 22px !important;
}}
.st-key-compras_prod_ctrl [data-testid="stSelectbox"] input {{
    padding: 0 !important;
    height: auto !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
    cursor: pointer !important;
}}
.st-key-compras_prod_ctrl [data-testid="stSelectbox"]:hover input {{
    color: {ACENTO} !important;
}}
.st-key-compras_prod_ctrl [data-testid="stSelectbox"] svg {{
    width: 13px !important;
    height: 13px !important;
    fill: {ACENTO} !important;
    color: {ACENTO} !important;
}}
.st-key-compras_prod_ctrl [data-testid="stSelectbox"]
    button[aria-haspopup] {{
    width: 16px !important;
    min-width: 0 !important;
    height: 22px !important;
    min-height: 0 !important;
    padding: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    flex: 0 0 auto !important;
}}
/* El nombre del producto en foco. Recorta con puntos suspensivos y el
   nombre entero va en el `title`: un corte fijo en N caracteres no sigue
   al ancho de la columna. */
.cp-prod-evo-tit {{
    font-size: 13.5px;
    font-weight: 700;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    /* Comparte renglón con los dos selectores desde el 2026-09-20, así que
       se alinea con ELLOS y no con el borde de arriba de su columna: los
       22px son el alto del selector aplanado de acá arriba. No se centra
       en la TARJETA (regla #449) porque no es un título centrado — es la
       primera cosa del renglón, y lo que sigue a su derecha son controles
       suyos. */
    line-height: 22px;
}}
/* EL RÓTULO DE LA ZONA DE ABAJO. Dice qué se está viendo —«Resumen» o el
   período en foco— y cómo volver. Va con el mismo peso que las cifras de
   arriba y no con el del título: es un pie, no una cabecera. */
.cp-prod-zona-rot {{
    font-size: 12px;
    color: {GRIS_TEXTO};
    margin: 0 0 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.cp-prod-zona-rot b {{ color: var(--text-primary); font-weight: 600; }}
/* Título sobre cada tabla-ranking: mismo lenguaje visual que
   `.cp-rank-tit` de graficos/compras/_css_proveedor.py, pero declarado acá
   — ese CSS solo se inyecta cuando se renderiza el drill de Proveedor, así
   que reusar la clase sin redeclararla dejaría el título sin estilo en
   Producto. Nombre propio a propósito (evita cualquier acople). */
.cp-prod-rank-tit {{
    /* 16px, en sync con `.cp-rank-tit` de _css_proveedor.py — el
       comentario de arriba explica por que son dos declaraciones. */
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    padding-left: 2px;
    margin: 0 0 4px;
}}
/* El ÁMBITO del Ranking de productos («· Vinos Tinto»): lo pone un clic en
   los paneles de Familia/Subfamilia de arriba. Más liviano que el título
   porque lo califica, no lo reemplaza. */
.cp-prod-rank-amb {{
    font-weight: 400;
    color: {GRIS_TEXTO};
}}
</style>
"""


# ── AgGrid: los dos rankings de este drill, sin checkbox ──────────────────
# 2026-08-24, a pedido ("como en Proveedor, sin el check de selección, y
# con filas delgadas"): mismo patrón que la regla #136/#192 de
# arquitectura.md — `st.dataframe` dibuja su columna de selección en un
# CANVAS (glide-data-grid), no hay nodo DOM por celda, así que no hay CSS
# que apunte "sólo esa columna". Cambiar a AgGrid es la única salida.
#
# Los dos rankings de este archivo (Producto y Familia) comparten el mismo
# toggle y los mismos formatters — se definen UNA vez a nivel de módulo
# (mismo criterio que `_EJE_X_GRAN`, arriba) en vez de recrear los `JsCode`
# en cada corrida del fragment.
_js_toggle_prod = JsCode(
    "function(e){ e.node.setSelected(!e.node.isSelected(), true); }")

# La barra es el FONDO de la celda (regla #136): un `linear-gradient`
# cortado en el % de LLENADO contra el MAYOR valor de la lista (`_barra`,
# columna oculta) — no contra el total, que es lo que ya muestra la
# columna "%".
_js_barra_prod = JsCode(
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

# Montos GRANDES (Valor): redondeado, CON separador de miles.
_js_soles0_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")

# Precios UNITARIOS (Inicio/Fin): 2 decimales, SIN separador de miles —
# mismo criterio que el `format="S/ %.2f"` que tenían como
# `column_config.NumberColumn`: un precio unitario no necesita agrupar.
_js_soles2_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " 'S/ ' + p.value.toFixed(2); }")

_js_pct_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " Math.round(p.value) + '%'; }")

# Var: con signo y 1 decimal (`%+.1f%%` en Python). `toFixed` ya antepone
# el signo "-" en un negativo; sólo hace falta el "+" del lado positivo.
_js_pct_signed_prod = JsCode(
    "function(p){ if(p.value==null) return '';"
    " return (p.value>=0?'+':'') + p.value.toFixed(1) + '%'; }")

# Conteos (Cant./Productos): redondeado, CON separador de miles — mismo
# criterio que "Valor", consistente con el resto de las tablas AgGrid de
# este drill (Proveedor).
_js_num0_prod = JsCode(
    "function(p){ return p.value==null ? '' :"
    " Math.round(p.value).toLocaleString('es-PE'); }")


# ── Funciones puras ───────────────────────────────────────────────────────

def _prod_ranking(dd, col_prod, col_fecha, col_valor, col_cant, col_punit, col_um):
    """Un producto por fila: valor y cantidad totales del rango, UM (moda),
    y precio real de la primera y última compra del período (sin promediar
    — mismo criterio que "Por compra") con su % de variación. Ordenado por
    valor descendente.

    TODO DE UNA VEZ, NO PRODUCTO POR PRODUCTO (2026-09-26, regla #537). Era
    un bucle que armaba un sub-DataFrame por producto —suma, moda, dropna,
    filtro y `sort_values` cada uno— y se llevaba el 90 % de la sección:
    2,3-2,5 s por llamada en la laptop con un mes de compras. Así, 30 ms, y
    el mismo resultado columna por columna, verificado sobre el parquet
    real (el histórico entero, cada año y cada trimestre).

    Dos cosas que el bucle hacía sin decirlo y que acá se escriben:
      · «la primera y la última compra»: por fecha y, entre compras del
        MISMO día, en el orden del parquet (orden estable);
      · MONTOS IGUALES AL CÉNTIMO van por nombre. En el bucle su orden
        dependía del último decimal de la suma (164,00000000000003 contra
        164,0): dos productos de S/ 164 podían salir en cualquier orden, y
        salían distinto según cómo se sumara.
    """
    g = dd.groupby(col_prod)                     # claves ordenadas, sin NaN
    valor = g[col_valor].sum().astype(float)
    prods = valor.index
    cantidad = (g[col_cant].sum().astype(float).reindex(prods)
                if col_cant else pd.Series(0.0, index=prods))
    if col_um and col_um in dd.columns:
        um = (moda_por_grupo(dd[[col_prod, col_um]].dropna(subset=[col_um]),
                             col_prod, col_um)
              .map(str).reindex(prods).fillna(""))
    else:
        um = pd.Series("", index=prods)
    # Precio de la primera y la última compra VÁLIDA del período.
    v = dd[[col_prod, col_fecha, col_punit]]
    v = v[v[col_prod].notna() & v[col_punit].notna()]
    v = v[v[col_punit] > 0].sort_values([col_prod, col_fecha], kind="stable")
    gv = v.groupby(col_prod, sort=False)[col_punit]
    inicio = gv.first().reindex(prods)
    fin = gv.last().reindex(prods)
    out = pd.DataFrame({
        "producto": [str(p) for p in prods],
        "valor": valor.to_numpy(),
        "cantidad": cantidad.to_numpy(dtype=float),
        "um": um.to_numpy(dtype=object),
        "inicio": inicio.to_numpy(dtype=float),
        "fin": fin.to_numpy(dtype=float),
        "var_pct": ((fin - inicio) / inicio * 100).to_numpy(dtype=float),
    })
    out["_orden"] = out["valor"].round(2)
    out = (out.sort_values(["_orden", "producto"], ascending=[False, True],
                           kind="stable")
              .drop(columns="_orden").reset_index(drop=True))
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


def _prod_serie_periodo(g, col_fecha, col_punit, col_cant, col_valor, gran,
                        col_docu=None, col_prov=None):
    """Serie por período (Semana/Mes/Año) de UN producto ya filtrado: precio
    promedio (relleno hacia adelante y hacia atrás en los huecos, para que
    la línea no corte), cantidad total, valor total, CUÁNTOS DOCUMENTOS lo
    respaldan y QUÉ PROVEEDORES lo atendieron. Indexada por la fecha
    de INICIO del período (eje real, no etiquetas de texto), así el
    promedio y las compras reales conviven en el mismo eje sin importar la
    granularidad elegida.

    `docs` y `provs` son del 2026-09-20, a pedido («que las barras tengan
    también el total de documentos, y ver los proveedores que atendieron
    esa barra»). Las dos son opcionales: sin `col_docu`/`col_prov` la
    columna sale vacía y la etiqueta la omite sola, que es lo que pasa con
    un parquet al que le falte la columna.

    UN DOCUMENTO ES (número, proveedor), NO EL NÚMERO SOLO. Medido sobre
    compras.parquet el 2026-09-20: 14.555 `NUM_DOCUMENTO` distintos contra
    17.988 pares (número, proveedor) — o sea que contar el número pelado se
    come el 19% de los comprobantes, porque dos proveedores numeran su
    "F001-123" cada uno por su cuenta. El TIPO no agrega nada (los mismos
    14.555 con o sin él), así que no se pide.

    `provs` es una lista de `(proveedor, valor)` ordenada de mayor a menor,
    no un número: el hover los NOMBRA. Caben porque son pocos — de los
    1.409 grupos producto-mes del último trimestre, 1.063 tienen UN solo
    proveedor y el máximo es 7."""
    fe = pd.to_datetime(g[col_fecha], errors="coerce")
    if gran == "Semana":
        bucket = (fe - pd.to_timedelta(fe.dt.weekday, unit="D")).dt.normalize()
    elif gran == "Año":
        bucket = pd.to_datetime(fe.dt.year.astype("Int64").astype(str) + "-01-01",
                                errors="coerce")
    else:  # Mes
        bucket = fe.dt.to_period("M").dt.to_timestamp()
    _hay_prov = bool(col_prov and col_prov in g.columns)
    _cols = {
        "bucket": bucket,
        "precio": pd.to_numeric(g[col_punit], errors="coerce"),
        "cantidad": (pd.to_numeric(g[col_cant], errors="coerce").fillna(0)
                     if col_cant else 0.0),
        "valor": pd.to_numeric(g[col_valor], errors="coerce").fillna(0),
    }
    if _hay_prov:
        _cols["prov"] = g[col_prov].astype(str).str.strip()
    if col_docu and col_docu in g.columns:
        _doc = g[col_docu].astype(str).str.strip()
        # La llave, no el número: ver el docstring.
        _cols["doc"] = (_doc + "|" + _cols["prov"]) if _hay_prov else _doc
    base = pd.DataFrame(_cols).dropna(subset=["bucket"])
    if base.empty:
        out = base.set_index("bucket")
        out["docs"] = pd.Series(dtype="float")
        out["provs"] = pd.Series(dtype="object")
        return out
    agg = base.groupby("bucket").agg(precio=("precio", "mean"),
                                     cantidad=("cantidad", "sum"),
                                     valor=("valor", "sum")).sort_index()
    agg["precio"] = agg["precio"].ffill().bfill()
    agg["docs"] = (base.groupby("bucket")["doc"].nunique()
                   if "doc" in base.columns else pd.NA)
    if _hay_prov:
        _pv = base.groupby(["bucket", "prov"], as_index=False)["valor"].sum()
        _pv = _pv.sort_values(["bucket", "valor"], ascending=[True, False])
        _pares = {_b: list(zip(_d["prov"].tolist(), _d["valor"].tolist()))
                  for _b, _d in _pv.groupby("bucket")}
    else:
        _pares = {}
    # `pd.Series(dict)` y no un `map`: con listas adentro, `Index.map`
    # intenta desempacarlas y devuelve un MultiIndex.
    agg["provs"] = pd.Series(_pares, dtype="object").reindex(agg.index)
    return agg


# ── LO QUE DICE CADA BARRA ────────────────────────────────────────────────
# 2026-09-20, a pedido: «que las barras tengan también el porcentaje de
# variación respecto a la barra anterior, así como el total de documentos, y
# poder ver en la etiqueta los proveedores que atendieron esa barra».
#
# Los tres datos NO van al mismo sitio, y el reparto es el que cabe:
#
#   · variación y documentos → ENCIMA de la barra. Son un número corto cada
#     uno y contestan de un vistazo («subí 10%, en 16 comprobantes»).
#   · proveedores → al HOVER. Son NOMBRES: el más largo del parquet mide 40
#     caracteres y la barra da 60px. Ahí también va el detalle fino (el
#     valor exacto, contra qué barra se comparó, y la variación del PRECIO,
#     que arriba no entra sin que la etiqueta deje de leerse).
#
# LA VARIACIÓN DE LA ETIQUETA ES LA DEL VALOR, o sea la de la ALTURA de la
# barra: es lo que "respecto a la barra anterior" significa mirando el
# gráfico. Sale de `_comun._variaciones`, la misma de Semanal, y con ella
# viene la regla #470: un período que la VENTANA corta dice «parcial» en vez
# de un porcentaje, y el de al lado calla. No es un detalle acá — la ventana
# de esta tarjeta es rodante («los últimos 3 meses» terminan el último día
# con datos), así que la primera y la última barra están cortadas SIEMPRE.
# Medido el 2026-09-20 con la ventana de 3 meses por Mes: «jul» decía +181%
# contra un «jun» que eran 11 días de mes.
#
# LA DEL PRECIO NO PASA POR AHÍ, y no es un olvido: el valor es una SUMA
# (medio mes suma la mitad) y el precio un PROMEDIO (medio mes promedia
# igual de bien). Por eso el precio conserva su variación en las barras
# cortadas, y por eso vive en el hover pegada a su propio número: dos
# porcentajes sueltos encima de una barra no dicen de qué son.
_UMBRAL_BARRAS_ROTADAS = 6
"""Desde cuántas barras la etiqueta se rota a un solo renglón.

MEDIDO (1366x768, 2026-09-20): el panel del gráfico da 429px de área útil y
el renglón más ancho de la etiqueta nueva («S/ 74.50 +182%») mide ~57px, así
que entran 7 — 429/7 = 61px por barra. Con 8 el hueco baja a 53 y las
etiquetas se pisan. Era 8 cuando la etiqueta medía 38px (dos renglones de
sólo cifras) y el panel 312: la cuenta es la misma, cambió el numerador.

Rotada, la etiqueta necesita ~13px de ancho, así que arriba de este umbral
entra siempre. Es la regla #91: Plotly NO oculta ni corta una etiqueta que
no entra, la ESCALA hasta que deja de leerse — y eso no se ve en el DOM.

La forma completa —probar tres disposiciones contra el slot y contra el alto
de la figura— es `semanal._plan_etiquetas`. Acá alcanza el umbral: estas
barras son siempre las de UN producto en una ventana de 3 a 24 meses (4 a 25
barras), no las 263 de «Por documento»."""


def _var_precio(precios):
    """% de variación del PRECIO de cada barra contra la anterior.

    Sin la guarda de «parcial» de `_comun._variaciones` a propósito: ver el
    comentario de arriba. El primero no tiene contra qué compararse y una
    base en cero o negativa tampoco (el % no significaría nada): los dos dan
    None, que el hover omite en vez de escribir un "+inf%"."""
    out = []
    previo = None
    for v in precios:
        if previo is not None and previo > 0 and not pd.isna(v):
            out.append((float(v) - previo) / previo * 100.0)
        else:
            out.append(None)
        previo = (float(v) if not pd.isna(v) else None)
    return out


def _fmt_docs(n, largo=False):
    """'16 docs' / '1 doc' (o 'documentos', en el hover). Vacío si el parquet
    no trae columna de documento: la etiqueta se arma igual sin ella."""
    if n is None or pd.isna(n) or int(n) <= 0:
        return ""
    n = int(n)
    if largo:
        return f"{n:,} documentos" if n != 1 else "1 documento"
    return f"{n:,} docs" if n != 1 else "1 doc"


def _etiquetas_barras(precios, valores, rotada=False):
    """El texto que Plotly dibuja SOBRE cada barra: precio y valor.

    Sin rotar son dos renglones; rotada es uno solo con los dos separados
    por «·», porque de costado los renglones se apilan a lo ANCHO y ahí el
    hueco por barra son 30px.

    DOS DATOS Y NO CUATRO desde el 2026-09-20. El 19 la etiqueta sumó la
    variación contra la barra anterior y cuántos documentos la forman
    (regla #479), y al día siguiente volvieron a salir: *«veo que cuando
    todas son barras altas la etiqueta de datos es bastante larga, hay
    alguna opción de [...] optativamente hacerlo visible con el paso del
    cursor»*. Esa es la solución que se aplicó, y ninguno de los dos datos
    se perdió: los dos están en el hover —que ya los decía— y además
    escritos en su propia columna en la tabla de abajo, que desde ese mismo
    día vive DENTRO de esta tarjeta y está siempre a la vista.

    MEDIDO en el navegador (1366x768, 14 barras semanales): la etiqueta
    girada baja de **144px a 70** sobre un área de trazo de 317, o sea de
    comerse el 45% del alto del gráfico a un 22%. Que es justo lo que hacía
    falta, porque en la misma vuelta la figura pasó de 384px a 237 para
    hacerle sitio a la tabla."""
    out = []
    for pr, val in zip(precios, valores):
        _pr = ("" if pr is None or pd.isna(pr) else f"S/ {pr:,.2f}")
        _val = _fmt_soles_compacto(val)
        sep = " · " if rotada else "<br>"
        out.append(sep.join(x for x in (_pr, _val) if x))
    return out


def _hover_barras(rotulos, precios, valores, docs, provs, variaciones=None,
                  claves=None, gran=None, rango=None, tope_provs=4):
    """Una cadena por barra para el `hovertemplate`: lo que no entra arriba.

    El valor va exacto, la variación dice contra QUÉ barra se comparó (o por
    qué no la hay, que es lo que salva a «parcial» de leerse como un dato
    faltante), el precio trae SU propia variación y abajo van los
    proveedores que atendieron el período con cuánto puso cada uno —
    ordenados de mayor a menor, cortados en `tope_provs` y con el resto
    contado.

    `provs` es la columna que arma `_prod_serie_periodo`: una lista de
    `(nombre, valor)` por barra, o NaN si el parquet no trae proveedor."""
    var_pre = _var_precio(list(precios))
    out = []
    for i, rot in enumerate(rotulos):
        lineas = [f"<b>{rot}</b>", f"valor S/ {valores[i]:,.2f}"]
        _v = variaciones[i] if variaciones else None
        if _v:
            _ant = (rotulos[_v[2]] if _v[2] is not None else "")
            # Llega con su propio `<br>` adelante, así que no va a `lineas`.
            lineas[-1] += _hover_variacion(
                _v, gran, (claves[i] if claves else None), _ant, rango)
        if not pd.isna(precios[i]):
            _p = ("" if var_pre[i] is None
                  else " {}".format(
                      "<span style='color:{1}'>{0}</span>".format(
                          *_fmt_variacion(var_pre[i]))))
            lineas.append(f"precio prom. S/ {precios[i]:,.2f}{_p}")
        _lista = provs[i] if provs is not None else None
        if _lista is None or not isinstance(_lista, (list, tuple)):
            _lista = []
        _cab = [x for x in (_fmt_docs(None if docs is None else docs[i],
                                      largo=True),
                            (f"{len(_lista):,} proveedores" if len(_lista) > 1
                             else ("1 proveedor" if _lista else "")))
                if x]
        if _cab:
            lineas.append(" · ".join(_cab))
        for _nom, _val in _lista[:tope_provs]:
            # 30 y no los 26 de siempre: MEDIDO, el hover con tres
            # proveedores mide 226px y el renglón más ancho es el del
            # nombre + su monto, así que hay sitio — con 26 se cortaba
            # «Compañia Food Retail S.A.C.», que entra entero.
            _nom = _compras_truncar(nombre_propio(_nom), 30)
            # El monto VA EXACTO y no compacto como en la barra: acá hay
            # sitio, y "S/ 4k" por S/ 4,354.51 en el sitio donde se va a
            # comparar un proveedor contra otro es esconder la diferencia.
            lineas.append(f"<span style='color:{GRIS_TEXTO}'>{_nom} · "
                          f"S/ {_val:,.0f}</span>")
        if len(_lista) > tope_provs:
            lineas.append(f"<span style='color:{GRIS_TEXTO}'>y "
                          f"{len(_lista) - tope_provs} más</span>")
        out.append("<br>".join(lineas))
    return out


def _tabla_periodos(rotulos, precios, valores, docs, variaciones,
                    claves, gran, rango):
    """Las filas del RESUMEN: una por BARRA, en el orden del eje.

    Es «el gráfico escrito», el mismo trato que la tabla Resumen de «Compra
    por período» —y la misma grilla, `tablas.compras_semanal.
    renderizar_periodos`, en su juego de anchos estrecho—: lo que la barra
    dice arriba, en columnas que se pueden ordenar y leer hacia abajo.

    Devuelve `(filas, total)`. En `total` los valores van ya FORMATEADOS
    como texto: es una fila fija (`pinnedBottomRowData`), no entra al modelo
    de filas y no se ordena.

    TRES COLUMNAS QUE NO ESTÁN, y ninguna por olvido:

      · «Proveedores». Estuvo un día. Se fue el 2026-09-20 a pedido
        —«quitemos la columna de proveedores»— y la vista no perdió el
        dato: tocando la barra, la zona pasa a Detalle y ahí hay una fila
        por comprobante CON su proveedor, que es donde el nombre se lee
        entero en vez de apretado contra otras cinco columnas.
      · «Líneas». Medido sobre compras.parquet el 2026-09-20: en los 1.295
        grupos producto-mes del último trimestre las líneas son EXACTAMENTE
        los documentos (diferencia máxima 0) — un producto entra una vez por
        comprobante. Una columna que repite a su vecina en el 100% de las
        filas es ruido (regla #239).
      · El precio en la fila TOTAL. Un promedio de promedios no mide nada, y
        el promedio ponderado de verdad (valorizado/cantidad) sería OTRA
        definición de «precio» en la misma columna. Va «—», que es lo que
        `_JS_SOLES` escribe con un None.
    """
    _tot = float(sum(valores))
    filas = {
        "periodo": list(rotulos),
        "precio": [(None if pd.isna(pr) else float(pr)) for pr in precios],
        "valor": [float(v) for v in valores],
        "parte": [(float(v) / _tot if _tot else 0.0) for v in valores],
    }
    if docs is not None:
        filas["docs"] = [(0 if d is None or pd.isna(d) else int(d))
                         for d in docs]
    filas["variacion"] = [(_v[1] if _v and _v[0] == "ok" else None)
                          for _v in variaciones]
    # «parcial» no es un dato faltante, es la respuesta: por eso viaja como
    # texto propio y con su motivo al lado, igual que en el hover.
    filas["__vtxt"] = [("parcial" if _v and _v[0] == "parcial" else "—")
                       for _v in variaciones]
    filas["__nota"] = [
        _nota_variacion(_v, gran, claves[_i],
                        (rotulos[_v[2]] if _v and _v[2] is not None else ""),
                        rango)
        for _i, _v in enumerate(variaciones)]
    filas["__sel"] = [False] * len(valores)

    # EL TOTAL SE ESCRIBE CORTO porque su celda mide 97px, no 180: «Total ·
    # 14 semanas» mide 108 y se cortaría con «…» justo en el número, que es
    # lo único suyo que hay que leer. La unidad la dice el eje del gráfico
    # de arriba, que es la misma.
    _n = len(valores)
    total = {
        "periodo": f"Total · {_n:,}",
        "precio": None,
        "valor": f"S/ {_tot:,.2f}",
        "parte": "100.0%",
        "variacion": None,
        "__vtxt": "",
        "__nota": "",
    }
    if "docs" in filas:
        total["docs"] = f"{sum(filas['docs']):,}"
    return pd.DataFrame(filas), total


def _periodo_del_clic(pt, claves, momentos):
    """Clave del período que corresponde al punto de un clic en una barra.

    A diferencia de su prima de Semanal (`_clave_del_clic`), acá el eje NO
    es lineal: `_eje_x_kwargs` dibuja las barras sobre los timestamps de los
    buckets, así que la `x` del evento vuelve como fecha y no como índice.
    Por eso se mira primero la POSICIÓN del punto, que Streamlit manda con
    el evento y no depende del tipo de eje, y la fecha queda de respaldo.

    Tolerante a propósito: un clic fuera de rango, un formato que cambie o
    una fecha que no case tienen que ser un no-op, no una excepción en medio
    del render — el usuario tocó un gráfico, no pidió un traceback."""
    for _k in ("point_index", "pointIndex", "point_number", "pointNumber"):
        _i = pt.get(_k)
        if isinstance(_i, (int, float)) and not isinstance(_i, bool):
            _i = int(_i)
            return claves[_i] if 0 <= _i < len(claves) else None
    try:
        _x = pd.Timestamp(pt.get("x"))
    except (TypeError, ValueError):
        return None
    for _i, _m in enumerate(momentos):
        if pd.Timestamp(_m) == _x:
            return claves[_i] if _i < len(claves) else None
    return None


def _compras_del_periodo(g, clave, gran, col_fecha, col_punit, col_cant,
                         col_valor, col_docu, col_prov):
    """Las filas del DETALLE: una por COMPRA del período que se tocó.

    Devuelve `(filas, total)` o `(None, None)` si el parquet no trae la
    columna de documento — sin ella no hay «una fila por comprobante» que
    armar, y la zona se queda en Resumen diciéndolo.

    UNA COMPRA ES (NÚMERO, PROVEEDOR) y no el número solo, la misma cuenta
    que `_prod_serie_periodo` (regla #479): dos proveedores numeran su
    «F001-123» cada uno por su cuenta, y medido sobre `compras.parquet` son
    14.555 números distintos contra 17.988 pares. Contar el número pelado se
    come el 19% de los comprobantes y devuelve un número creíble.

    El precio de la fila es el PONDERADO de esa compra (valor/cantidad) y no
    el promedio de sus líneas: si un comprobante trae el producto dos veces
    a precios distintos, el promedio simple diría un precio que nadie pagó.
    Por eso el total tampoco promedia precios — divide el valor entre la
    cantidad, que es la única definición que se sostiene al agregar."""
    if not col_docu or col_docu not in g.columns:
        return None, None
    _g = g[_periodo_serie(pd.Series(g[col_fecha]), gran) == clave].copy()
    if _g.empty:
        return None, None
    _g["__prov"] = (_g[col_prov].astype(str) if col_prov
                    and col_prov in _g.columns else "")
    _g["__cant"] = pd.to_numeric(_g[col_cant], errors="coerce").fillna(0.0)
    _g["__val"] = pd.to_numeric(_g[col_valor], errors="coerce").fillna(0.0)
    # SE AGRUPA POR DOS COLUMNAS DE VERDAD, y el renombre es POR NOMBRE.
    # La primera versión agrupaba por `[_g[col_docu].astype(str), "__prov"]`
    # —una Series suelta y un nombre— y después reescribía `_d.columns` con
    # una lista de cinco. Funcionaba en la máquina de desarrollo (pandas 3,
    # que deja la clave-Series como columna) y reventaba en Cloud con un
    # `ValueError: Length mismatch`, porque ahí corre la versión de
    # `requirements.txt` (pandas 2.2) y el frame sale con otra forma.
    # Renombrar por POSICIÓN es apostar a la forma; por nombre, no. Ver la
    # regla #481, que es sobre el desfase de versiones y no sobre esta
    # función.
    _g["__doc"] = _g[col_docu].astype(str)
    _d = (_g.groupby(["__doc", "__prov"], as_index=False)
            .agg(fecha=(col_fecha, "min"), cant=("__cant", "sum"),
                 valor=("__val", "sum"))
            .rename(columns={"__prov": "prov"}))
    _d["punit"] = [(_v / _c if _c else None)
                   for _v, _c in zip(_d["valor"], _d["cant"])]
    _d["prov"] = [nombre_propio(_n) if _n else "—" for _n in _d["prov"]]
    _d["fecha"] = pd.to_datetime(_d["fecha"]).dt.strftime("%Y-%m-%d")
    _d = _d.sort_values("valor", ascending=False).reset_index(drop=True)
    _d = _d[["fecha", "prov", "cant", "punit", "valor", "__doc"]]

    _cant, _val = float(_d["cant"].sum()), float(_d["valor"].sum())
    _n = len(_d)
    total = {
        "fecha": f"Total · {_n:,}",
        "prov": "",
        "cant": _cant,
        "punit": (f"S/ {_val / _cant:,.2f}" if _cant else None),
        "valor": f"S/ {_val:,.2f}",
        "__doc": "",
    }
    return _d, total


def _rotulo_periodo(ts, gran):
    """El período en español, para el hover y para el eje.

    Plotly rotula en INGLÉS con `tickformat` («Aug 2026»): usa su locale por
    defecto. La lista de meses en español es `cortes.MESES_ABR_ES`, una sola
    en todo el repo. Ver la regla #241."""
    ts = pd.Timestamp(ts)
    if gran == "Año":
        return str(ts.year)
    if gran == "Semana":
        return f"{ts.day:02d} {MESES_ABR_ES[ts.month - 1]}"
    return f"{MESES_ABR_ES[ts.month - 1]} {ts.year}"


def _sin_gritar(nombre):
    """"CARNES" -> "Carnes"; "Otros Servicios Prestados Por Terceros" ->
    tal cual.

    El `nombre_propio` de las reglas #347 y #379, pero SÓLO sobre el texto
    que llega TODO en mayúsculas. La guarda no es prudencia: es lo que midió el
    parquet el 2026-09-11, cuando estos tres paneles se pidieron
    "similares al de Ranking de Proveedores".

      · Las 8 FAMILIAS llegan gritadas, las 8.
      · De las 95 SUBFAMILIAS, sólo 34 gritan: las otras 61 ya vienen en
        capitalización de nombre propio desde el ERP ("Otros Servicios
        Prestados Por Terceros"). O sea que el panel B mezcla los dos
        estilos según qué familia esté enfocada, y una pasada ciega no
        arregla eso: lo empareja mal.

    Correrlo sobre las 61 que ya están bien NO es inocuo, y tampoco es
    teoría — se corrió: "Serv. Analisis Y Certificacion" vuelve como
    "SERV. Analisis y Certificacion", porque la regla de "token con punto
    = sigla" está escrita para `S.A.C.`, no para un `Serv.` abreviado. Con
    la guarda, cada texto se toca una vez o ninguna.

    Es la MISMA que usa el Ranking de Proveedores, que es lo que estos
    paneles están copiando. Hasta el 2026-09-11 había dos implementaciones
    conviviendo (`base.py` y ésta) y acá importaba cuál: en dos de las ocho
    familias dan distinto —"BEBIDAS CON ALCOHOL" sale "Bebidas con Alcohol"
    o "Bebidas Con Alcohol" según la versión, y "RB ALIMENTOS" conserva el
    "RB" o lo baja a "Rb"—. La regla #379 las unificó ese mismo día en esta,
    con las reglas de las dos, así que ya no hay elección que hacer.

    Los PRODUCTOS del ranking quedan fuera de esto a propósito: ya vienen
    en minúscula y con la medida pegada al nombre ("Bife Ancho Argentino x
    Kg"), donde capitalizar por palabra devolvería "X Kg".
    """
    s = str(nombre)
    return nombre_propio(s) if not any(c.islower() for c in s) else s


def _fam_normalizada(dd, col_fam):
    """Columna de familia como texto, con vacíos/NaN unificados en "Sin
    familia" — no se descartan, o el total de este ranking dejaría de
    cuadrar con el de productos."""
    return dd[col_fam].astype(str).replace({"": "Sin familia", "nan": "Sin familia"})


def _subfam_normalizada(dd, col_subfam):
    """Gemela de `_fam_normalizada` para Subfamilia, y por el mismo motivo:
    los vacíos se unifican en "Sin subfamilia" en vez de descartarse, o el
    total del panel B dejaría de cuadrar con la fila de su familia en el A.

    Medido sobre R2 el 2026-09-09: hoy no hace falta para nada —
    `compras.parquet` trae `SUBFAMILIA` en las 51.838 filas, 0 nulas y 0
    vacías, 95 valores distintos. Es una red por si el parquet cambia, no
    una rama que se recorra."""
    return dd[col_subfam].astype(str).replace({"": "Sin subfamilia",
                                               "nan": "Sin subfamilia"})


def _fam_ranking(dd, col_fam, col_valor):
    """Una familia por fila: valor total y % sobre el total comprado.

    Hasta el 2026-09-12 contaba además las subfamilias de cada una (la
    columna «Subfam.» del panel) y los productos distintos (la «Prod.» sin
    panel B). Se pidió fuera la primera y la segunda se fue con ella: un
    conteo calculado que ninguna tabla muestra es trabajo que nadie lee."""
    g = dd.copy()
    g[col_fam] = _fam_normalizada(g, col_fam)
    out = g.groupby(col_fam).agg(valor=(col_valor, "sum"))
    out = out.sort_values("valor", ascending=False).reset_index()
    out = out.rename(columns={col_fam: "familia"})
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


def _subfam_ranking(d_fam, col_subfam, col_prod, col_valor):
    """Una subfamilia por fila, DENTRO de una familia ya recortada: valor,
    Nº de productos y % SOBRE ESA FAMILIA — no sobre el total comprado.

    El % es sobre el padre a propósito: con % global, las cinco subfamilias
    de VINOS Y ESPUMANTES darían 4%, 0,5%, 0,2%… y la columna dejaría de
    servir para comparar las filas que se están viendo. Lo dice el
    `headerTooltip` de esa columna ("% sobre ALIMENTOS"), que es lo que
    evita que se lea como el % del panel A — hasta el 2026-09-11 lo decía
    un caption debajo de la tabla, que se pidió fuera.

    Recibe el df YA filtrado por familia y no `(df, familia)` a propósito:
    la clave real es el PAR (familia, subfamilia), no la subfamilia sola.
    Medido sobre R2 el 2026-09-09, 9 de las 95 subfamilias de
    `compras.parquet` aparecen en más de una familia, así que un
    `df[col_subfam] == x` suelto mezcla productos de dos familias sin dar
    error y sin que se note."""
    g = d_fam.copy()
    g[col_subfam] = _subfam_normalizada(g, col_subfam)
    out = g.groupby(col_subfam).agg(valor=(col_valor, "sum"),
                                    productos=(col_prod, "nunique"))
    out = out.sort_values("valor", ascending=False).reset_index()
    out = out.rename(columns={col_subfam: "subfamilia"})
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


def _ambito_ranking(dd, col_fam, col_subfam, familia, subfamilia):
    """El recorte de compras sobre el que se rankean los PRODUCTOS: todo,
    una familia, o una subfamilia DE una familia.

    Nace el 2026-09-12, cuando el tercer panel del drill (los productos del
    grupo elegido) se fue y su papel lo tomó el Ranking de productos: el
    clic en Familia o en Subfamilia ahora recorta esa tabla.

    Se filtra por familia PRIMERO, siempre, aunque la subfamilia sola
    parezca bastar: la clave es el PAR (familia, subfamilia). 9 de las 95
    subfamilias de `compras.parquet` aparecen en más de una familia (ver
    `_subfam_ranking`), así que un `df[col_subfam] == x` suelto rankearía
    productos de dos familias sin dar error."""
    if familia is None:
        return dd
    d = dd[_fam_normalizada(dd, col_fam) == familia]
    if subfamilia is not None and col_subfam and col_subfam in d.columns:
        d = d[_subfam_normalizada(d, col_subfam) == subfamilia]
    return d


# ── Vista principal ──────────────────────────────────────────────────────

@st.fragment
def _prod_stats(g, col_fecha, col_punit, col_cant, col_valor, col_um):
    """Las cifras del encabezado del panel de detalle, sobre EL MISMO df
    que dibujan los puntos.

    Nace el 2026-08-26 con la ventana propia de la tarjeta: antes salían de
    la fila del ranking, que se calcula sobre el rango de la franja. Con
    dos ventanas distintas eso sería un número describiendo un período y
    unos puntos dibujando otro.

    Devuelve también `minimo`/`maximo`, que el ranking no tiene: con
    `var` = primera contra última compra, un producto que arrancó y terminó
    en el mismo precio da 0.0% aunque en el medio haya oscilado 39% — el
    caso real que motivó el pedido. El rango min-max es lo que la persona
    está viendo en los puntos, así que se dice.
    """
    _r = g.dropna(subset=[col_punit])
    _r = _r[_r[col_punit] > 0].sort_values(col_fecha)
    if _r.empty:
        return None
    _p = _r[col_punit]
    _ini, _fin = float(_p.iloc[0]), float(_p.iloc[-1])
    return {
        "inicio": _ini, "fin": _fin,
        "var_pct": ((_fin - _ini) / _ini * 100.0) if _ini else None,
        "minimo": float(_p.min()), "maximo": float(_p.max()),
        "n": int(len(_r)),
        "um": (str(_r[col_um].iloc[-1]) if col_um and col_um in _r.columns
               else ""),
        "cantidad": (float(pd.to_numeric(g[col_cant], errors="coerce")
                           .fillna(0).sum()) if col_cant else 0.0),
        "valor": float(pd.to_numeric(g[col_valor], errors="coerce")
                       .fillna(0).sum()),
    }


def _paneles_familia(dd, col_fam, col_subfam, col_prod, col_valor,
                     fecha=None):
    """Los dos paneles de arriba de la tarjeta —Familia | Subfamilia— y el
    ÁMBITO que dejan elegido, como `(familia, subfamilia)` para
    `_ambito_ranking`.

    El ámbito NO es el foco de los paneles, y la diferencia importa: sin
    ningún clic el panel B igual muestra las subfamilias de la familia de
    arriba (para no abrir vacío), pero el ranking de abajo tiene que seguir
    siendo el de TODO lo comprado, que es lo que fue siempre. Por eso:

      · nada elegido     → (None, None): todo lo comprado
      · una familia      → (familia, None)
      · una subfamilia   → (la familia que muestra el panel B, subfamilia),
                           aunque esa familia no se haya clicado.

    Sin columna de Subfamilia en el parquet, el panel B no se dibuja y la
    mitad derecha de la fila queda vacía: es una red, no un caso real
    (`SUBFAMILIA` viene en las 51.838 filas, ver `_subfam_normalizada`).

    `fecha` es un callable `fecha(titulo_html)` que dibuja el selector de
    fecha de la sección con ese título a su izquierda. Va en la fila del
    título del panel A, «Compras por familia» (2026-09-12, a pedido, y
    repetido: «el selector de fecha debe estar al lado de la primera tabla
    de familia»). Una primera versión lo había puesto del lado del panel B
    —el borde derecho de la tarjeta, donde está en las otras cuatro que lo
    usan— y no era lo pedido: el selector se lee como parte de la tabla que
    tiene al lado. Es un callable y no un valor por la misma razón que el
    `extra=` de `selector_fecha_tarjeta`: en Streamlit el sitio se elige
    entrando."""
    hay_sub = bool(col_subfam and col_subfam in dd.columns)
    fam_ranking = _fam_ranking(dd, col_fam, col_valor)
    fam_focus = st.session_state.get("compras_prod_fam_focus")
    if fam_focus not in set(fam_ranking["familia"]):
        fam_focus = None

    # DOS filas de columnas y no una, desde el 2026-09-12: los títulos en
    # una y los grids en otra. Con el título de cada panel dentro de su
    # columna, el que comparte fila con la píldora de la fecha (hoy el del
    # A; ese día, el del B) medía distinto que el otro, texto suelto con el
    # margen negativo de la #162, y los grids arrancaban a 16px de
    # distancia (medido, 1280px).
    # En filas separadas Streamlit alinea las dos columnas solo. El título B
    # se escribe DESPUÉS del grid A (depende de su clic) en una columna
    # creada antes: en Streamlit el sitio lo decide el contenedor, no el
    # orden de escritura.
    # columnas-internas: títulos de los dos niveles del drill.
    tit_fam, tit_sub = st.columns(2, gap=GAP_DRILL,
                                  vertical_alignment="center")
    # columnas-internas: los dos niveles del drill, mitad y mitad, dentro
    # de la tarjeta del ranking. No es una fila de drill.
    col_famtabla, col_subtabla = st.columns(2, gap=GAP_DRILL)

    with tit_fam:
        # Título y fecha en UNA fila (`cp_prod_fila`, flex): el título cede
        # con puntos suspensivos y el trigger conserva su ancho.
        _tit_fam = '<div class="cp-prod-rank-tit">Compras por familia</div>'
        if fecha is not None:
            fecha(_tit_fam)
        else:
            st.markdown(_tit_fam, unsafe_allow_html=True)

    with col_famtabla:

        disp_fam = fam_ranking.rename(columns={
            "familia": "Familia", "valor": "Valor", "pct": "%",
        })
        _val_max_fam = (float(fam_ranking["valor"].max())
                       if len(fam_ranking) else 1.0)
        disp_fam["_barra"] = disp_fam["Valor"] / _val_max_fam * 100
        # El nombre CRUDO viaja en una columna oculta y es el que se
        # lee de vuelta: la columna visible pasa por `_sin_gritar` y
        # ya no matchea contra los datos. Mismo patrón —y mismo
        # motivo— que `_prov_raw` en el Ranking de Proveedores.
        disp_fam["_fam_raw"] = disp_fam["Familia"]
        disp_fam["Familia"] = disp_fam["Familia"].map(_sin_gritar)
        # Sin columna de conteo desde el 2026-09-12, a pedido: la
        # «Subfam.» (cuántas subfamilias abre el clic) se fue, y con ella
        # la «Prod.» que la reemplazaba sin panel B. El número de puertas
        # se ve igual —es el alto del panel de al lado— y lo que no se
        # ve, no se estaba leyendo.
        _resp_fam = AgGrid(
            disp_fam[["Familia", "Valor", "%", "_barra", "_fam_raw"]],
            gridOptions={
                # Sin `flex`: mismo motivo que el Ranking de productos
                # (`st_aggrid` le clava `width: 200` a toda columna sin
                # `width` propio, y ese `width` le gana al `flex`).
                #
                # Los anchos se eligieron con la regla #349 en la mano:
                # AG Grid reescala las columnas para llenar la grilla.
                # El reparto prioriza "Valor", porque un número
                # recortado por la izquierda es plausible y falso
                # ("S/ 1,452,437" → "452,437"), mientras que un nombre
                # recortado se ve recortado — y encima tiene tooltip.
                # Familia se queda con los 52px de la columna que se fue,
                # así el total declarado es el mismo que el del panel B
                # y los dos escalan igual.
                "columnDefs": [
                    {"field": "Familia", "width": 156,
                     "tooltipField": "Familia"},
                    {"field": "Valor", "width": 108, "minWidth": 100,
                     "type": "numericColumn",
                     "cellStyle": _js_barra_prod,
                     "valueFormatter": _js_soles0_prod},
                    # El `headerTooltip` es donde se fue a vivir el
                    # caption que había debajo de la tabla. Los tres
                    # paneles tenían el suyo y el 2026-09-11 se
                    # pidieron fuera ("eliminemos el texto que está
                    # abajo de ellos"); lo que decían no era adorno
                    # —de qué es % esta columna— así que en vez de
                    # borrarse se movió al rótulo, que no gasta alto.
                    {"field": "%", "width": 38, "minWidth": 44,
                     "type": "numericColumn",
                     "headerTooltip": "% sobre el total comprado "
                                      "en el rango",
                     "valueFormatter": _js_pct_prod},
                    {"field": "_barra", "hide": True},
                    {"field": "_fam_raw", "hide": True},
                ],
                "rowSelection": {"mode": "singleRow",
                                 "checkboxes": False,
                                 "enableClickSelection": False},
                "onRowClicked": _js_toggle_prod,
                # Que las columnas LLENEN el panel, que es la otra
                # mitad de parecerse al Ranking de Proveedores: sin
                # esto los 302px declarados no entraban en los 255 de
                # un panel a 1024px de ventana (con tres paneles, hasta
                # el 2026-09-12) y la tabla salía con scroll horizontal
                # y la última columna cortada.
                #
                # `fitGridWidth` y NO `colDef.flex`, y eso está
                # medido en la regla #350: los grids de esta tarjeta se
                # construyen dentro de una `seccion_perezosa`, o sea
                # FUERA de pantalla, y `flex` calculado sobre un
                # cuerpo de ancho 0 se queda clavado en los 200px
                # por defecto para siempre. `fitGridWidth` reintenta
                # (0 → 100 → 500ms). El `minWidth` de "Valor" sigue
                # mandando: un monto recortado por la izquierda es
                # plausible y falso (#349).
                "autoSizeStrategy": {"type": "fitGridWidth"},
                "rowHeight": ALTO_FILA_RANK,
                "headerHeight": ALTO_HEADER_RANK,
                "suppressCellFocus": True,
                "suppressMovableColumns": True,
            },
            allow_unsafe_jscode=True,
            theme="streamlit",
            # El look del Ranking de Proveedores, a pedido
            # (2026-09-11): franja en vez de caja, todo blanco, sin
            # líneas verticales, cuerpo 11.5 y el texto en violeta.
            # Es el MISMO dict, no una copia — un grid vive en un
            # iframe y el `<style>` del padre no lo alcanza, así que
            # `custom_css=` es la única vía (ver `_css_proveedor.py`).
            custom_css=CSS_RANKING_GRID,
            height=_ALTO_FRAME_FAM,
            update_on=["selectionChanged"],
            key="compras_prod_fam_rank_tab",
        )
        _sel_fam = getattr(_resp_fam, "selected_rows", None)
        if _sel_fam is not None and len(_sel_fam):
            _fila_fam = (_sel_fam.iloc[0] if hasattr(_sel_fam, "iloc")
                        else _sel_fam[0])
            _clicked_fam = str(_fila_fam["_fam_raw"])
        else:
            _clicked_fam = None
        if _clicked_fam != fam_focus:
            fam_focus = _clicked_fam
            st.session_state["compras_prod_fam_focus"] = fam_focus
            # Cambiar de familia INVALIDA la subfamilia: sin esto,
            # elegir CARNES y saltar a VINOS deja el ranking de
            # abajo mostrando carne. El guard de más abajo lo
            # ataja igual (la subfamilia vieja no está en el ranking
            # de la familia nueva), pero se limpia también acá para
            # que el estado y la key del grid del medio —que lleva
            # el slug de la familia— cuenten lo mismo en la MISMA
            # pasada, sin depender del orden de lectura.
            st.session_state.pop("compras_prod_subfam_focus", None)

    # El foco se resuelve DESPUÉS del panel A y antes del B: así el clic
    # de esta corrida ya manda, sin un rerun de por medio. Sin selección
    # el panel B muestra la familia de arriba, que es lo que evita que
    # abra vacío — pero eso es el FOCO, no el ámbito del ranking (ver el
    # docstring).
    fam_foco = (fam_focus if fam_focus is not None
                else fam_ranking.iloc[0]["familia"])
    d_fam = dd[_fam_normalizada(dd, col_fam) == fam_foco]

    sub_focus = None
    _tit_sub = (f'<div class="cp-prod-rank-tit">'
                f'{html.escape(_sin_gritar(fam_foco))}</div>')
    if hay_sub:
        with tit_sub:
            st.markdown(_tit_sub, unsafe_allow_html=True)
    if hay_sub:
        with col_subtabla:
            sub_ranking = _subfam_ranking(d_fam, col_subfam, col_prod,
                                          col_valor)
            sub_focus = st.session_state.get("compras_prod_subfam_focus")
            if sub_focus not in set(sub_ranking["subfamilia"]):
                sub_focus = None
            if sub_ranking.empty:
                st.info("Sin subfamilias para esta familia.")
            else:
                disp_sub = sub_ranking.rename(columns={
                    "subfamilia": "Subfamilia", "valor": "Valor",
                    "pct": "%", "productos": "Productos",
                })
                _val_max_sub = float(sub_ranking["valor"].max())
                disp_sub["_barra"] = disp_sub["Valor"] / _val_max_sub * 100
                # Cruda en una columna oculta: es la que se lee de
                # vuelta y la que recorta el ranking. Ver el panel A.
                disp_sub["_sub_raw"] = disp_sub["Subfamilia"]
                disp_sub["Subfamilia"] = disp_sub["Subfamilia"].map(
                    _sin_gritar)
                _resp_sub = AgGrid(
                    disp_sub[["Subfamilia", "Valor", "%", "Productos",
                             "_barra", "_sub_raw"]],
                    gridOptions={
                        # Mismo total declarado que el panel A (302px):
                        # lado a lado, los dos escalan igual y se leen
                        # como una grilla, no como dos tablas parecidas.
                        "columnDefs": [
                            {"field": "Subfamilia", "width": 104,
                             "tooltipField": "Subfamilia",
                             "headerTooltip": "Otro clic en la misma "
                                              "subfamilia la suelta"},
                            {"field": "Valor", "width": 108, "minWidth": 100,
                             "type": "numericColumn",
                             "cellStyle": _js_barra_prod,
                             "valueFormatter": _js_soles0_prod},
                            # Sobre la FAMILIA, no sobre el total:
                            # es la decisión de diseño del drill y lo
                            # decía el caption que se fue. Ver el
                            # docstring de `_subfam_ranking`.
                            # `minWidth` 44 (también en los otros dos
                            # grids): a 1280px, con la barra vertical de
                            # este panel, `fitGridWidth` la dejaba en 39px
                            # y «11%» salía «1…» — la regla #349.
                            {"field": "%", "width": 38, "minWidth": 44,
                             "type": "numericColumn",
                             "headerTooltip":
                                 f"% sobre {_sin_gritar(fam_foco)}",
                             "valueFormatter": _js_pct_prod},
                            {"field": "Productos", "headerName": "Prod.",
                             "width": 52, "type": "numericColumn",
                             "headerTooltip": "Productos distintos",
                             "valueFormatter": _js_num0_prod},
                            {"field": "_barra", "hide": True},
                            {"field": "_sub_raw", "hide": True},
                        ],
                        "rowSelection": {"mode": "singleRow",
                                         "checkboxes": False,
                                         "enableClickSelection": False},
                        "onRowClicked": _js_toggle_prod,
                        # Ver el panel A: `fitGridWidth`, no `flex`.
                        "autoSizeStrategy": {"type": "fitGridWidth"},
                        "rowHeight": ALTO_FILA_RANK,
                        "headerHeight": ALTO_HEADER_RANK,
                        "suppressCellFocus": True,
                        "suppressMovableColumns": True,
                    },
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    custom_css=CSS_RANKING_GRID,
                    height=_ALTO_FRAME_FAM,
                    update_on=["selectionChanged"],
                    # La key lleva el slug de la FAMILIA a propósito:
                    # al cambiar de familia el componente se remonta y
                    # nace sin selección, así que la fila marcada del
                    # panel viejo no puede sobrevivir a la de al lado.
                    key=f"compras_prod_subfam_tab_{_slug(fam_foco)}",
                )
                _sel_sub = getattr(_resp_sub, "selected_rows", None)
                if _sel_sub is not None and len(_sel_sub):
                    _fila_sub = (_sel_sub.iloc[0]
                                if hasattr(_sel_sub, "iloc")
                                else _sel_sub[0])
                    _clicked_sub = str(_fila_sub["_sub_raw"])
                else:
                    _clicked_sub = None
                if _clicked_sub != sub_focus:
                    sub_focus = _clicked_sub
                    st.session_state["compras_prod_subfam_focus"] = sub_focus

    if sub_focus:
        return fam_foco, sub_focus
    return fam_focus, None


def _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant, col_punit,
                            col_um, col_fecha, col_prov=None, d_full=None,
                            col_subfam=None, col_docu=None):
    """Una fila de dos tarjetas: a la izquierda Familia | Subfamilia y,
    debajo, el ranking de productos que esos dos recortan; a la derecha la
    evolución del producto en foco.

    `col_subfam` va al FINAL y con default: el resto de la firma es
    posicional en el llamador, y en Cloud un commit que le cambia el orden
    a algo ya importado deja el `app.py` nuevo hablando con el paquete
    viejo (regla #357). Con default, la firma vieja sigue siendo válida.

    `d_full` es el histórico sin la fecha de la sección: de ahí sale la
    ventana fija de 3 meses del gráfico, que no depende del rango elegido.

    `col_docu` va DESPUÉS de `col_subfam` y con default, por lo mismo que
    aquélla (regla #357): sólo la usa la etiqueta de las barras, y sin ella
    la etiqueta se arma igual, sin la línea de documentos."""
    if not (col_prod and col_valor and col_punit and col_fecha):
        st.info("Faltan columnas (Producto, Valor, Precio unitario o Fecha) "
                "para este gráfico.")
        return

    # La bandera del selector de fecha de la tarjeta: el filtro que lee el
    # rango vive en app.py, FUERA de este fragment, así que sin escalar a
    # `st.rerun(scope="app")` el estado cambiaría y la pantalla no. Se
    # consume al entrar, antes de dibujar nada. Mismo mecanismo que el
    # Ranking de Proveedores.
    # `preservar_widgets` porque el rerun aborta ACÁ, antes de que los
    # controles de la sección se registren, y Streamlit recolecta el estado
    # de todo widget de este fragment que no se dibujó (ver `_KEYS_WIDGET`).
    if st.session_state.pop("_cp_prod_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")

    dd = d.copy()
    dd[col_fecha] = pd.to_datetime(dd[col_fecha], errors="coerce")
    dd[col_punit] = pd.to_numeric(dd[col_punit], errors="coerce")
    dd[col_valor] = pd.to_numeric(dd[col_valor], errors="coerce").fillna(0)
    dd = dd.dropna(subset=[col_fecha, col_prod])
    dd = dd[dd[col_prod].astype(str).str.strip() != ""]
    if dd.empty:
        # Gemelo del cartel vacío del Ranking de Proveedores, y por el mismo
        # motivo: este `return` salía antes de la cabecera, que es donde
        # vive el ÚNICO control de rango de la sección desde que la franja
        # no dibuja calendario. La tarjeta se dibuja siempre; lo que se
        # decide adentro es el contenido (regla #115, y ver #354).
        #
        # DOS blobs de CSS, y los dos hacen falta acá arriba: la fila del
        # selector la estila `CSS_PROVEEDOR` (lo inyecta el drill de
        # Proveedor, la sección de ARRIBA, que con `d` vacío cae en su
        # propia rama vacía — y por eso ahí también se inyecta), y el
        # título `.cp-prod-rank-tit` vive en `_CSS_SELECTOR_TEXTO`, que
        # este módulo inyectaba DESPUÉS de esta guarda.
        st.markdown(_CSS_SELECTOR_TEXTO, unsafe_allow_html=True)
        with st.container(border=True, key="compras_prod_card_vacio"):
            selector_fecha_tarjeta(
                "cp_prod", "_cp_prod_atajo_pendiente",
                titulo_html='<div class="cp-prod-rank-tit">'
                            'Ranking de productos</div>',
                categoria=CATEGORIA_SEC["compras_sec_producto"])
            st.info("Sin compras en el rango seleccionado. Ampliá el rango "
                    "desde la fecha de la cabecera.")
        return

    st.markdown(_CSS_SELECTOR_TEXTO, unsafe_allow_html=True)

    # (Acá vivió el filtro de proveedores de esta sección —el mismo
    # `_comun.py::filtro_proveedores` del Ranking de Proveedores, clave
    # "cp_prod_prov"—, que recortaba `dd` a "los productos que le compro a
    # estos proveedores". Nació el 2026-09-02 y se fue el 2026-09-12, a
    # pedido: «eliminemos el filtro de proveedores, ya no lo necesitaremos
    # en este grupo de vista». `col_prov` sigue en la firma por la #357.
    # Su CSS NO se borró: las reglas `cp_prod_prov_*` de `_css_proveedor.py`
    # son el molde del que se clona el filtro de «Detalle de documentos»
    # (`cp_docs_prov_*`), que sigue vivo. Ver regla #382.)

    # ── UNA fila: Evolución | [Familia | Subfamilia + Ranking de productos] ─
    # 2026-09-12, a pedido. Hasta ese día eran DOS filas: arriba una tarjeta
    # de ancho completo con tres paneles en cascada (Familia › Subfamilia ›
    # Productos del grupo), y debajo el Ranking de productos al lado de la
    # Evolución. El pedido fue en cuatro partes: sacarle al panel de Familia
    # su columna «Subfam.», eliminar el tercer panel, que el clic en
    # Subfamilia recorte el RANKING en su lugar, y meter el ranking en la
    # tarjeta de Familia/Subfamilia — con lo que la Evolución sube a la
    # altura de los paneles.
    #
    # El tercer panel y el Ranking eran dos tablas de productos una encima
    # de la otra: la de arriba mostraba los del grupo elegido, la de abajo
    # los de todo el rango. Ahora hay una sola y el grupo la RECORTA — ver
    # `_paneles_familia` para qué ámbito deja cada combinación de clics.
    #
    # El contenedor de afuera es MARCO, no tarjeta: las dos tarjetas son las
    # columnas (el mismo movimiento que hizo el drill de Proveedor el
    # 2026-08-18). Su key NO empieza con `compras_prod_card_`, que es un
    # wildcard por familia en estilos/_80_cards.py: si lo llevara, se
    # pintaría de blanco con padding y sombra ENCIMA de las dos tarjetas.
    #
    # 2026-09-12, segunda vuelta del mismo día: el gráfico pasa a la
    # IZQUIERDA y las tablas a la derecha, a pedido — `COLUMNAS_DRILL_ESPEJO`
    # (ver `_comun.py` sobre por qué es la misma proporción al revés). Las
    # tablas se siguen escribiendo PRIMERO en el código: el gráfico necesita
    # el ranking y el foco que ellas resuelven, y en Streamlit la posición la
    # decide la columna, no el orden del `with`. En esa misma vuelta la
    # fecha pasó a la fila de títulos de las tablas, el gráfico a una
    # ventana fija de 3 meses, el filtro de proveedores se fue del segmento,
    # y las dos tarjetas dejaron de scrollear por dentro (ver
    # estilos/_80_cards.py y la regla #382).
    hay_fam = bool(col_fam and col_fam in dd.columns)
    # LA TABLA DE DETALLE SE ARMA ARRIBA Y SE DIBUJA ABAJO. Se arma donde
    # están los datos —dentro de la tarjeta del gráfico, que es quien sabe
    # qué barras hay— y se dibuja DESPUÉS de la fila, a lo ancho: sus siete
    # columnas piden 744px de anchos fijos y el panel del gráfico da 429.
    # Meterla adentro habría sido elegir entre cortar columnas o angostar
    # el gráfico que describe.
    _detalle = None
    with st.container(key="compras_prod_marco"):
        col_detalle, col_tabla = st.columns(COLUMNAS_DRILL_ESPEJO,
                                            gap=GAP_DRILL)
        with col_tabla:
            with st.container(border=True, key="compras_prod_card_ranking"):
                # El `if` y no un `return`: sin columna de Familia se va la
                # fila de paneles, no la sección entera.
                # El selector de fecha de la sección. `clave` propio
                # ("cp_prod") porque Compras se lee APILADA y la tarjeta de
                # Proveedores está en la página a la vez.
                def _fecha(titulo_html):
                    selector_fecha_tarjeta(
                        "cp_prod", "_cp_prod_atajo_pendiente",
                        titulo_html=titulo_html,
                        categoria=CATEGORIA_SEC["compras_sec_producto"])

                fam_amb = sub_amb = None
                if hay_fam:
                    fam_amb, sub_amb = _paneles_familia(dd, col_fam, col_subfam,
                                                        col_prod, col_valor,
                                                        fecha=_fecha)
                d_rank = _ambito_ranking(dd, col_fam, col_subfam, fam_amb,
                                         sub_amb)
                ranking = _prod_ranking(d_rank, col_prod, col_fecha, col_valor,
                                        col_cant, col_punit, col_um)
                prod_focus = st.session_state.get("compras_prod_focus")
                if prod_focus not in set(ranking["producto"]):
                    prod_focus = None

                # El ámbito se DICE en el título: el recorte lo decide un
                # clic en otro panel, y una tabla que cambia de contenido
                # sin decir por qué se lee como un bug.
                _amb = sub_amb or fam_amb
                _amb_txt = (html.escape(_compras_truncar(_sin_gritar(_amb), 30))
                            if _amb else "")
                _amb_html = (f'<span class="cp-prod-rank-amb"> · {_amb_txt}'
                             f'</span>' if _amb else "")
                # Título solo, sin controles: el filtro de proveedores y la
                # fecha compartían esta fila hasta el 2026-09-12. El filtro
                # se fue del segmento y la fecha a la fila de títulos de
                # arriba (ver `_paneles_familia`). Sólo sin
                # columna de Familia —sin fila de arriba— la fecha vuelve
                # acá: la sección no puede quedarse sin control de rango.
                _tit_rank = ('<div class="cp-prod-rank-tit">'
                             f'Ranking de productos{_amb_html}</div>')
                if hay_fam:
                    st.markdown(_tit_rank, unsafe_allow_html=True)
                else:
                    _fecha(_tit_rank)

                # SIN el punto en "Cant": AG Grid resuelve `field` con notación
                # de PATH ("a.b" -> row.a.b), así que un campo "Cant." se parte
                # en ["Cant", ""] y la celda sale vacía en silencio, sin ningún
                # error (arquitectura.md regla #192). El punto vuelve como
                # `headerName` en el columnDef, así que el rótulo no cambia.
                disp = ranking.rename(columns={
                    "producto": "Producto", "valor": "Valor", "pct": "%",
                    "cantidad": "Cant", "um": "UM", "inicio": "Inicio",
                    "fin": "Fin", "var_pct": "Var",
                })
                _val_max_prod = float(ranking["valor"].max()) if len(ranking) else 1.0
                disp["_barra"] = disp["Valor"] / _val_max_prod * 100
                _resp_prod = AgGrid(
                    disp[["Producto", "Valor", "%", "Cant", "UM", "Inicio",
                         "Fin", "Var", "_barra"]],
                    gridOptions={
                        # Ancho fijo en las OCHO columnas, ninguna con `flex`:
                        # `st_aggrid` le clava `width: 200` a cada columna sin
                        # `width` propio y ese `width` le gana al flex
                        # (verificado con `api.getColumnDefs()`).
                        #
                        # Lo que decía el caption de debajo de la tabla («UM =
                        # unidad de kardex · Inicio/Fin = primera y última
                        # compra real del período · % es sobre el total del
                        # rango») se mudó a los `headerTooltip`, igual que los
                        # de los paneles de arriba el 2026-09-11: en la misma
                        # tarjeta que ellos, el renglón de alto era el que
                        # no alcanzaba.
                        "columnDefs": [
                            {"field": "Producto", "width": 150,
                             "tooltipField": "Producto"},
                            {"field": "Valor", "width": 96, "minWidth": 90,
                             "type": "numericColumn",
                             "cellStyle": _js_barra_prod,
                             "valueFormatter": _js_soles0_prod},
                            {"field": "%", "width": 44, "minWidth": 44,
                             "type": "numericColumn",
                             "headerTooltip": (f"% sobre {_sin_gritar(_amb)}"
                                               if _amb else
                                               "% sobre el total comprado "
                                               "en el rango"),
                             "valueFormatter": _js_pct_prod},
                            {"field": "Cant", "headerName": "Cant.",
                             "width": 60, "type": "numericColumn",
                             "headerTooltip": "Cantidad en la UM del "
                                              "producto; no se suma "
                                              "entre productos",
                             "valueFormatter": _js_num0_prod},
                            {"field": "UM", "width": 52,
                             "headerTooltip": "Unidad de kardex"},
                            {"field": "Inicio", "width": 72, "minWidth": 64,
                             "type": "numericColumn",
                             "headerTooltip": "Precio de la PRIMERA compra "
                                              "real del período",
                             "valueFormatter": _js_soles2_prod},
                            {"field": "Fin", "width": 72, "minWidth": 64,
                             "type": "numericColumn",
                             "headerTooltip": "Precio de la ÚLTIMA compra "
                                              "real del período",
                             "valueFormatter": _js_soles2_prod},
                            # `minWidth` por la regla #349: «+176.9%» mide
                            # 51px y recortado por la izquierda se lee
                            # «76.9%», un número plausible y falso.
                            {"field": "Var", "width": 60, "minWidth": 56,
                             "type": "numericColumn",
                             "headerTooltip": "Variación de Fin contra "
                                              "Inicio",
                             "valueFormatter": _js_pct_signed_prod},
                            {"field": "_barra", "hide": True},
                        ],
                        "rowSelection": {"mode": "singleRow",
                                         "checkboxes": False,
                                         "enableClickSelection": False},
                        "onRowClicked": _js_toggle_prod,
                        # El look de los paneles de arriba —que es el del
                        # Ranking de Proveedores—, y no el suyo de antes: con
                        # las tres tablas en la misma tarjeta, dos idiomas de
                        # grilla se leían como dos tarjetas pegadas. Eso trae
                        # las filas de 24px, la cabecera de 32 y el
                        # `fitGridWidth` (ver el panel A de `_paneles_familia`
                        # sobre por qué no `flex`).
                        "autoSizeStrategy": {"type": "fitGridWidth"},
                        "rowHeight": ALTO_FILA_RANK,
                        "headerHeight": ALTO_HEADER_RANK,
                        "suppressCellFocus": True,
                        "suppressMovableColumns": True,
                    },
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    custom_css=CSS_RANKING_GRID,
                    height=_ALTO_FRAME,
                    update_on=["selectionChanged"],
                    # El ámbito en la key, como la tenía el panel que esto
                    # reemplaza: fuerza el remonte con los datos nuevos (con
                    # key estable y el `client_wins` de fábrica el navegador
                    # puede quedarse con la tabla anterior, regla #227). De
                    # paso el remonte nace sin fila elegida, así que al
                    # cambiar de grupo la Evolución pasa al primero del grupo
                    # nuevo en vez de quedarse en un producto de otro.
                    key=("compras_prod_rank_tab_"
                         f"{_slug(fam_amb or 'todo')}_{_slug(sub_amb or 'todo')}"),
                )
                # AgGrid devuelve la selección VIGENTE en cada corrida (no un
                # evento) — comparar contra `prod_focus` alcanza, sin dedup.
                # Selección vacía (reclic en la fila ya elegida, el toggle de
                # `_js_toggle_prod`) TAMBIÉN limpia el foco.
                _sel_prod = getattr(_resp_prod, "selected_rows", None)
                if _sel_prod is not None and len(_sel_prod):
                    _fila_sel = (_sel_prod.iloc[0] if hasattr(_sel_prod, "iloc")
                                else _sel_prod[0])
                    _clicked = str(_fila_sel["Producto"])
                else:
                    _clicked = None
                if _clicked != prod_focus:
                    prod_focus = _clicked
                    st.session_state["compras_prod_focus"] = prod_focus

        with col_detalle:
            with st.container(border=True, key="compras_prod_card_evo"):
                prod_foco = prod_focus if prod_focus is not None else ranking.iloc[0]["producto"]

                # ── CABECERA: el producto en foco ────────────────────────────
                # Sin controles de sección, y eso es lo que quedó de tres
                # vueltas del 2026-09-12: la fecha y el filtro de proveedores
                # llegaron a vivir acá; la fecha se pidió en la fila del
                # título de «Compras por familia» —que es sobre lo que manda;
                # este gráfico tiene su ventana fija— y el filtro se pidió
                # fuera del segmento.
                #
                # Recorte por CSS (ellipsis) y el nombre entero en el
                # `title`: el ancho de la tarjeta cambia con la ventana, y
                # un corte fijo en N caracteres o sobra o no alcanza.
                # ── CABECERA: el producto, su ventana y su granularidad ─
                # UN SOLO RENGLÓN desde el 2026-09-20, a pedido: «hagamos
                # minimalista la granulación de semana mes año, en una línea
                # desplegable y pongámosla en la misma fila del título». El
                # renglón que se ahorra es lo que paga la tabla de abajo —
                # ver el reparto en `_CROMO_CARD_EVO`.
                #
                # Sin controles de sección, y eso es lo que quedó de tres
                # vueltas del 2026-09-12: la fecha y el filtro de proveedores
                # llegaron a vivir acá; la fecha se pidió en la fila del
                # título de «Compras por familia» —que es sobre lo que manda—
                # y el filtro se pidió fuera del segmento.
                #
                # El nombre recorta por CSS (ellipsis) y va entero en el
                # `title`: el ancho de la tarjeta cambia con la ventana, y un
                # corte fijo en N caracteres o sobra o no alcanza.
                #
                # 2.6 / 1.75 / 1.0 son los 433px del panel repartidos según
                # lo que mide el peor caso de cada uno a 12.5px: «Últimos 24
                # meses» pide ~116 con su chevron y «Semana» ~61, así que al
                # nombre le quedan ~196 — unos 26 caracteres antes del «…».
                #
                # columnas-internas: el nombre del producto y sus dos
                # selectores, dentro de la tarjeta. No es una fila de drill.
                _nom = html.escape(str(prod_foco))
                # La key del contenedor es el ANCLA del CSS que aplana los
                # dos selectores a texto (`_CSS_SELECTOR_TEXTO`). Es una
                # regla por contenedor, así que captura a todo selectbox que
                # se meta acá dentro: si algún día entra un tercero que SÍ
                # tiene que verse como caja, acotarla a su key propia.
                with st.container(key="compras_prod_ctrl"):
                    # columnas-internas: el nombre del producto y sus dos
                    # selectores, dentro de la tarjeta. No es una fila de
                    # drill (el reparto y su medición, doce líneas arriba).
                    _c_tit, _c_win, _c_gran = st.columns(
                        [2.6, 1.75, 1.0], vertical_alignment="center")
                    with _c_tit:
                        st.markdown(
                            f'<div class="cp-prod-evo-tit" title="{_nom}">'
                            f'{_nom}</div>', unsafe_allow_html=True)
                    with _c_win:
                        # ── VENTANA PROPIA, ELEGIBLE, ABRIENDO EN 3 MESES ─
                        # Historia corta, porque cambió tres veces:
                        #   · 2026-08-26 → 2026-09-12: ventana propia
                        #     ELEGIBLE (`periodo.selector`), abría en 12m.
                        #     Nació porque el rango de la franja era de ~24
                        #     días y cualquier granularidad daba UN período.
                        #   · 2026-09-12: se quitó, para que la fecha del
                        #     segmento (entonces en esta tarjeta) mandara
                        #     también acá —si no, era la regla #330, un
                        #     control de fecha sentado sobre un gráfico que
                        #     lo ignora—, y el mismo día volvió como ventana
                        #     FIJA de 3 meses, sin selector, a pedido.
                        #   · 2026-09-12, más tarde, a pedido: «no permite
                        #     cambiar las opciones de "Últimos 3 meses",
                        #     recuerdo que se podía personalizar». Vuelve el
                        #     desplegable, abriendo en 3m. Lo que se quiso
                        #     fijar era el DEFAULT, no quitar la elección.
                        #
                        # La #330 ya no muerde: la fecha del segmento vive en
                        # la OTRA tarjeta, así que ésta tiene un solo control
                        # de fecha y es el suyo. Con «Rango» el gráfico sigue
                        # a esa fecha.
                        _op_prod = periodo.selector(
                            "compras_prod_periodo", default="3m",
                            widget="lista",
                            format_func=lambda o: _ETIQ_VENTANA_EVO.get(o, o))
                    with _c_gran:
                        gran = st.selectbox(
                            "Agrupar por", ("Semana", "Mes", "Año"), index=1,
                            key="compras_prod_gran_sel",
                            label_visibility="collapsed",
                            help="Cada barra es un período de este tamaño. "
                                 "La tabla de abajo lleva una fila por "
                                 "barra, en el mismo orden.")

                # El ancla es el último día CON DATOS del parquet, no `hoy`
                # (ver el docstring de `graficos/periodo.py`). La ventana se
                # recorta de `d_full`, el histórico sin la fecha de la
                # sección: con `dd` quedaría dentro del rango elegido.
                if _op_prod != periodo.HEREDA and d_full is not None:
                    _src_evo = periodo.recortar(d_full, col_fecha,
                                                _op_prod).copy()
                    _src_evo[col_fecha] = pd.to_datetime(_src_evo[col_fecha],
                                                         errors="coerce")
                    _src_evo[col_punit] = pd.to_numeric(_src_evo[col_punit],
                                                        errors="coerce")
                    _src_evo[col_valor] = pd.to_numeric(
                        _src_evo[col_valor], errors="coerce").fillna(0)
                    _src_evo = _src_evo.dropna(subset=[col_fecha, col_prod])
                else:
                    _src_evo = dd
                # EL RANGO QUE SE ESTÁ MIRANDO, como dos `date`. Lo necesita
                # la variación contra la barra anterior para saber qué
                # período quedó CORTADO (#470), y sale del mismo sitio que
                # recortó el df — si saliera de los datos, un mes con
                # compras sólo hasta el 12 se leería como mes entero.
                #
                # Las dos ramas son las dos fuentes de `_src_evo`: la
                # ventana propia de esta tarjeta, o el rango de la sección
                # (el selector de la tarjeta de al lado) cuando hereda.
                if _op_prod != periodo.HEREDA and d_full is not None:
                    _f_full = pd.to_datetime(d_full[col_fecha],
                                             errors="coerce")
                    _rng_evo = periodo.ventana(_op_prod, _f_full.max(),
                                               minimo=_f_full.min())
                else:
                    _rng_evo = rango_tarjeta(
                        CATEGORIA_SEC["compras_sec_producto"])
                _rng_evo = (tuple(pd.Timestamp(_x).date() for _x in _rng_evo)
                            if _rng_evo and all(_x is not None
                                                for _x in _rng_evo) else None)

                g = _src_evo[_src_evo[col_prod].astype(str) == prod_foco]
                # Las cifras del encabezado salen de `g`, o sea de la MISMA
                # ventana que las barras. Si salieran de `ranking` —que mira
                # el rango de la sección— serían un número describiendo un
                # período y unas barras dibujando otro.
                fila = _prod_stats(g, col_fecha, col_punit, col_cant, col_valor,
                                   col_um)
                agg = _prod_serie_periodo(g, col_fecha, col_punit, col_cant,
                                          col_valor, gran, col_docu=col_docu,
                                          col_prov=col_prov)

                if agg.empty or fila is None:
                    # Con la ventana propia es un caso NORMAL, no un borde:
                    # el Ranking mira el rango de la sección (12 meses de
                    # entrada) y un producto que se compró en enero no tiene
                    # nada en los últimos 3. El mensaje dice cuál ventana,
                    # o se lee como un producto sin datos.
                    _en = _ETIQ_VENTANA_EVO.get(_op_prod, _op_prod).lower()
                    st.info("Sin compras con precio válido de este producto "
                            f"en «{_en}».")
                else:
                    var_pct = fila["var_pct"]
                    color_var = (ERROR if var_pct and var_pct > 0.05
                                else (EXITO if var_pct and var_pct < -0.05 else GRIS_TEXTO))
                    _um = f"/{fila['um']}" if fila["um"] else ""
                    # Dos líneas, no una: la de una sola línea obligaba a leer
                    # "1ª → última" sin decir última QUÉ, y mezclaba
                    # precio+variación con el rango mín-máx en la misma
                    # respiración. 2026-09-03, a pedido.
                    _rango_txt = ""
                    if fila["maximo"] > fila["minimo"]:
                        _rango_txt = (
                            f'<div style="font-size:12px;color:{GRIS_TEXTO};'
                            f'margin:0 0 2px;">fluctuó entre '
                            f'<b>S/ {fila["minimo"]:,.2f}</b> y '
                            f'<b>S/ {fila["maximo"]:,.2f}</b></div>')
                    # DICE "última compra" Y NO "actual" desde el
                    # 2026-09-20. Se preguntó qué era («dice actual y un
                    # valor, ¿a qué se refiere, al precio actual?») y la
                    # pregunta estaba bien hecha: son DOS cosas distintas.
                    # Esta cifra es el precio unitario de la ÚLTIMA compra
                    # dentro de la ventana del gráfico — no un promedio, no
                    # el precio de hoy, y no lo que dicen las barras (que es
                    # el promedio del período). Con una compra suelta a otra
                    # unidad de medida las dos cifras se separan tanto que
                    # parecen de productos distintos: medido en vivo, «actual
                    # S/ 15.85» debajo de barras de S/ 74.50.
                    st.markdown(
                        f'<div style="font-size:12px;color:{GRIS_TEXTO};margin:0 0 2px;"'
                        f' title="Precio unitario de la última compra dentro de'
                        f' la ventana del gráfico. Las barras muestran el'
                        f' promedio de cada período.">'
                        f'última compra <b>S/ {fila["fin"]:,.2f}{_um}</b> · '
                        f'<b style="color:{color_var};">'
                        f'{"+" if (var_pct or 0) >= 0 else "−"}{abs(var_pct or 0):.1f}%'
                        f'</b> desde la 1ª del período</div>'
                        f'{_rango_txt}',
                        unsafe_allow_html=True)

                    _precio = agg["precio"].tolist()
                    _valor = agg["valor"].tolist()
                    _docs = (agg["docs"].tolist() if "docs" in agg.columns
                             else None)
                    _provs = (agg["provs"].tolist() if "provs" in agg.columns
                              else None)
                    # Las claves («2026-S38», «2026-09») son lo que sabe
                    # desarmar `_cobertura` para decidir si la VENTANA corta
                    # ese período. Las arma `_periodo_serie`, la misma que
                    # las escribe en Semanal: dos formatos distintos de la
                    # misma clave serían dos definiciones de "un mes".
                    _claves = list(_periodo_serie(pd.Series(agg.index), gran))
                    _vars = _variaciones(_claves, _valor, gran, _rng_evo)
                    _rotulos = [_rotulo_periodo(_t, gran) for _t in agg.index]

                    # ── EL CLIC EN UNA BARRA, ANTES DE DIBUJARLA ─────────
                    # Regla #399: la selección de `on_select` PERSISTE entre
                    # corridas mientras la key no cambie, así que se lee la
                    # key que se DIBUJÓ la vez pasada y el contador sube en
                    # esta misma corrida — con el foco en la key se perdía un
                    # clic de cada dos (medido en Semanal). Es la receta de
                    # Volatilidad (`compras_vol_nclic`).
                    #
                    # Y va acá arriba, no después de la figura, porque de qué
                    # barra está en foco dependen DOS cosas de esta misma
                    # corrida: el color de las barras y qué dibuja la zona de
                    # abajo.
                    _key_base = f"compras_g_prod_{gran}"
                    _nclic = st.session_state.get("compras_prod_nclic", 0)
                    _foco_antes = st.session_state.get("compras_prod_foco_per")
                    _pt = _first_point(
                        st.session_state.get(f"{_key_base}_{_nclic}"))
                    if _pt is not None:
                        # Todo evento leído se CONSUME, haya movido el foco o
                        # no: con la key igual, la corrida siguiente lo
                        # volvería a leer y el clic se repetiría solo.
                        _nclic += 1
                        st.session_state["compras_prod_nclic"] = _nclic
                        _clic = _periodo_del_clic(_pt, _claves, agg.index)
                        if _clic is not None:
                            # La MISMA barra apaga el foco: sin toggle no
                            # habría forma de volver al Resumen, porque esta
                            # zona no tiene control propio (el pestillo
                            # «Detalle» se quitó a pedido el 2026-09-20).
                            st.session_state["compras_prod_foco_per"] = (
                                None if _foco_antes == _clic else _clic)
                    _key_graf = f"{_key_base}_{_nclic}"
                    _foco_per = st.session_state.get("compras_prod_foco_per")
                    # Un foco que ya no existe (cambió la ventana, la
                    # granularidad o el producto) no es un error: es que el
                    # período se fue. La zona vuelve a Resumen sin avisar.
                    if _foco_per not in _claves:
                        _foco_per = None

                    # ── BARRAS, con las dos cifras SIEMPRE a la vista ────
                    # La barra ES el valor comprado del período y encima
                    # lleva, fijo, el precio promedio de ese período — que es
                    # la pregunta que traía a este panel ("¿a cuánto me
                    # salió, y cuánto compré?") respondida de una mirada.
                    #
                    # El valor va COMPACTO (`_fmt_soles_compacto`, nacido para
                    # este mismo problema en ventas_comparativo.py): "S/ 11k"
                    # entra en una barra angosta donde "S/ 11,268" se corta o
                    # se pisa con la vecina. El monto exacto sigue en el hover
                    # y, desde el 2026-09-20, en la tabla de abajo.
                    fig = go.Figure()
                    # LA ETIQUETA ROTA SI NO ENTRA, no se encoge: Plotly la
                    # ESCALA hasta que deja de leerse y sigue en el DOM (regla
                    # #91). El umbral y su medición, en
                    # `_UMBRAL_BARRAS_ROTADAS`.
                    _muchas = len(agg) > _UMBRAL_BARRAS_ROTADAS
                    _etiquetas = _etiquetas_barras(_precio, _valor,
                                                   rotada=_muchas)
                    _hover = _hover_barras(
                        _rotulos, _precio, _valor, _docs, _provs,
                        variaciones=_vars, claves=_claves, gran=gran,
                        rango=_rng_evo)
                    # LA BARRA EN FOCO SE QUEDA CON EL ACENTO y las demás se
                    # apagan: es lo que dice que la tabla de abajo habla de
                    # ÉSA y no de todas. Mismo gesto que los meses no
                    # elegidos de la cascada de «Vs año pasado».
                    _colores = (ACENTO if _foco_per is None else
                                [ACENTO if _k == _foco_per else LAVANDA_FOCO
                                 for _k in _claves])
                    fig.add_bar(
                        x=agg.index, y=_valor, marker_color=_colores,
                        text=_etiquetas, textposition="outside",
                        textangle=-90 if _muchas else 0,
                        textfont=dict(size=10, color=GRIS_TEXTO),
                        cliponaxis=False, constraintext="none",
                        # El hover se arma ENTERO en Python (nombres de
                        # proveedor, meses en español, los dos porcentajes):
                        # `%{x|...}` rotularía el mes en inglés, y un
                        # `customdata` por dato obligaría a repetir acá el
                        # formato que ya sabe `_hover_barras`.
                        customdata=[[h] for h in _hover],
                        hovertemplate="%{customdata[0]}<extra></extra>",
                    )
                    _compras_layout(fig, alto=_ALTO_EVO)
                    fig.update_layout(showlegend=False,
                                      yaxis=dict(showticklabels=False),
                                      bargap=0.35)
                    # Techo con aire para que la etiqueta quepa encima de
                    # la barra más alta: `textposition="outside"` no expande
                    # el rango solo, y sin esto la etiqueta del máximo se
                    # corta contra el borde.
                    #
                    # Rotada la etiqueta ocupa ALTO en vez de ancho, así que
                    # el techo tiene que dar más aire. Con las dos cifras
                    # MEDIDO: 70px de etiqueta girada, y 1.75 sobre un área
                    # de trazo de ~170 deja los ~73 que hacen falta.
                    if max(_valor) > 0:
                        fig.update_yaxes(
                            range=[0, max(_valor) * (1.75 if _muchas
                                                     else 1.28)])
                    fig.update_xaxes(**_eje_x_kwargs(gran, agg))
                    # `on_select="rerun"` es lo que hace clickeable la barra.
                    # El `key` lleva el contador de arriba, no el foco.
                    st.plotly_chart(fig, use_container_width=True,
                                    on_select="rerun", key=_key_graf)

                    # ── LA ZONA DE ABAJO: el gráfico escrito, o UNA barra ─
                    # 2026-09-20, a pedido: «la tabla debe estar debajo del
                    # gráfico y formar parte de la tarjeta del gráfico [...]
                    # y al hacer click en una columna debe mostrar la
                    # información de esa columna, algo similar a lo que ya
                    # tengo en la vista por período». Son los dos estados de
                    # la zona, y no hay control que los cambie: los cambia el
                    # clic en la barra, que es el gesto que ya significaba
                    # «mostrame ésta».
                    #
                    # Las dos tablas miden `_ALTO_ZONA`, lo mismo: si
                    # midieran distinto, tocar una barra cambiaría el alto de
                    # la tarjeta y la fila entera bailaría con cada clic
                    # (#398).
                    _det_filas, _det_total = (None, None)
                    if _foco_per is not None:
                        _det_filas, _det_total = _compras_del_periodo(
                            g, _foco_per, gran, col_fecha, col_punit,
                            col_cant, col_valor, col_docu, col_prov)
                    _i_foco = (_claves.index(_foco_per)
                               if _foco_per in _claves else None)

                    if _det_filas is not None:
                        _n_c = len(_det_filas)
                        _rot_z = (
                            f'<b>{html.escape(_rotulos[_i_foco])}</b> · '
                            f'{_n_c:,} '
                            f'{"compra" if _n_c == 1 else "compras"}'
                            ' · tocá la misma barra para volver al resumen')
                    else:
                        _uni = _UNIDAD_GRAN.get(gran, ("período", "períodos"))
                        _n_b = len(_claves)
                        _rot_z = (
                            f'<b>Resumen</b> · {_n_b:,} '
                            f'{_uni[0] if _n_b == 1 else _uni[1]}'
                            ' · tocá una barra para ver sus compras')
                    st.markdown(f'<div class="cp-prod-zona-rot">{_rot_z}</div>',
                                unsafe_allow_html=True)

                    # La key la ESTRENA todo lo que cambia las filas: el
                    # producto, la granularidad, la ventana, el rango y el
                    # foco. Con key estable la grilla se refresca y el
                    # navegador puede quedarse con los datos de antes (#227).
                    _k_z = _clave_grilla(prod_foco, gran, _op_prod, _rng_evo,
                                         _foco_per, len(_claves))
                    if _det_filas is not None:
                        renderizar_compras_producto(
                            _det_filas, altura=_ALTO_ZONA,
                            key=f"compras_prod_zona_det_{_k_z}",
                            total=_det_total)
                    else:
                        _filas_z, _tot_z = _tabla_periodos(
                            _rotulos, _precio, _valor, _docs, _vars,
                            _claves, gran, _rng_evo)
                        renderizar_periodos(
                            _filas_z, altura=_ALTO_ZONA,
                            key=f"compras_prod_zona_res_{_k_z}",
                            rotulo_periodo="Período", total=_tot_z,
                            estrecha=True)
