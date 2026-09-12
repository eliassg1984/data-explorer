"""graficos.compras.producto - drill de Producto.

Ranking de TODOS los productos comprados (valor, cantidad, UM, precio real
de inicio/fin de periodo y su variación) con el mismo patrón de tabla-
ranking + clic-para-enfocar que graficos/compras/proveedor.py. El producto
en foco muestra su evolución (Precio / Cantidad / Valor, con granularidad
Semana / Mes / Año) fusionando el promedio del período con el precio real
de cada compra en un solo gráfico. Esa tarjeta va a la IZQUIERDA y tiene
VENTANA PROPIA elegible (Rango/3m/12m/24m/Todo) que abre en los últimos 3
meses (2026-09-12; antes abría en 12m). La fecha de la sección vive en la
fila del título de «Compras por familia» y manda sobre las tablas. Filtro
de proveedores no hay: se pidió fuera el mismo día (regla #382).

Reemplaza a los antiguos drills "Precio top 10", "Precio por compra" y
"Cantidad por producto" (graficos/compras/cantidad.py, eliminado 2026-08-17):
las tres separaban precio-promedio, precio-real y cantidad/valor de UN mismo
producto en tres pantallas distintas — acá conviven en una, con un selector
de texto plano en vez de tabs/pills con caja (a pedido, para no ocupar sitio).

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

from tema import ACENTO, ERROR, EXITO, GRIS_TEXTO, TEXTO_PRINCIPAL
from graficos.base import (
    _compras_layout, _compras_truncar, _slug, preservar_widgets,
)
from graficos.ventas_comparativo import _fmt_soles_compacto
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CATEGORIA_SEC, COLUMNAS_DRILL_ESPEJO,
    CROMO_GRID_RANK, GAP_DRILL, selector_fecha_tarjeta,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
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
#   Evolución: 582 de tarjeta − 438 de figura = 144 (padding 32 + nombre
#              del producto 6, por la misma #162 + ventana y granularidad
#              32 + las dos líneas de cifras 26 + tres gaps de 16)
# Con una sola línea de cifras (un producto que no fluctuó) la Evolución
# pide menos y el piso `:has()` rellena esos px al pie: es el caso raro.
_CROMO_CARD_RANK = 138
_CROMO_CARD_EVO = 144
_ALTO_EVO = max(alturas.MINI,
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

_KEYS_WIDGET = ("compras_prod_gran_pills", "compras_prod_periodo")
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
    """`_EJE_X_GRAN[gran]`, con `tick0` anclado al primer bucket real de
    ESTE gráfico para "Semana". "M1"/"M12" (Mes/Año) se alinean solos al
    calendario sin importar `tick0`, pero un paso semanal en milisegundos
    no: sin un `tick0` que caiga sobre un bucket real, con pocos datos
    Plotly puede no dibujar NINGÚN tick semanal (rango angosto, ninguna
    posición de la grilla cae dentro) — visto en vivo con una sola semana
    de compras."""
    kw = dict(_EJE_X_GRAN[gran])
    if gran == "Semana" and not agg.empty:
        kw["tick0"] = agg.index.min()
    return kw


# Selector de texto plano (Semana/Mes/Año, Precio/Cantidad/Valor): mismo
# st.pills que el resto de la app (radiogroup accesible, estado en
# session_state), pero sin la cápsula — a pedido, para que no ocupe sitio
# dentro de la columna angosta del panel de detalle. El DOM de st.pills es
# fijo (ver estilos/__init__.py § Sobre st.pills): stButtonGroup > button
# [role="radio"], con `data-selected` SOLO en el activo.
_CSS_SELECTOR_TEXTO = f"""
<style>
.st-key-compras_prod_gran [data-testid="stButtonGroup"] {{
    gap: 10px !important;
    justify-content: flex-end !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1px 0 !important;
    min-height: 0 !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
}}
.st-key-compras_prod_gran [data-testid="stButtonGroup"] button[role="radio"][data-selected] {{
    color: {ACENTO} !important;
    font-weight: 600 !important;
}}
/* El selector de ventana del gráfico («Últimos 3 meses ▾»), APLANADO A
   TEXTO para que haga juego con la granularidad de al lado: los dos son
   texto suelto, no una caja contra unas palabras. Misma receta que
   `cp_evo_ctrl` en _css_proveedor.py — se conserva el chevron, que es la
   única señal de que eso despliega. Se fue y volvió el 2026-09-12: ver el
   comentario de la ventana en `compras_prod_card_evo`. */
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"] div[role="group"] {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    min-height: 0 !important;
    height: 22px !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"] input {{
    padding: 0 !important;
    height: auto !important;
    font-size: 12.5px !important;
    font-weight: 400 !important;
    color: {GRIS_TEXTO} !important;
    cursor: pointer !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"]:hover input {{
    color: {ACENTO} !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"] svg {{
    width: 13px !important;
    height: 13px !important;
    fill: {ACENTO} !important;
    color: {ACENTO} !important;
}}
.st-key-compras_prod_periodo_wrap [data-testid="stSelectbox"]
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
}}
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
    valor descendente."""
    filas = []
    for prod, g in dd.groupby(col_prod):
        valor = float(g[col_valor].sum())
        cantidad = float(g[col_cant].sum()) if col_cant else 0.0
        um = ""
        if col_um and col_um in g.columns:
            _u = g[col_um].dropna()
            if not _u.empty:
                um = str(_u.mode().iat[0])
        gp = g.dropna(subset=[col_punit])
        gp = gp[gp[col_punit] > 0].sort_values(col_fecha)
        if gp.empty:
            inicio = fin = var_pct = None
        else:
            inicio = float(gp[col_punit].iloc[0])
            fin = float(gp[col_punit].iloc[-1])
            var_pct = ((fin - inicio) / inicio * 100) if inicio else None
        filas.append({"producto": str(prod), "valor": valor, "cantidad": cantidad,
                      "um": um, "inicio": inicio, "fin": fin, "var_pct": var_pct})
    out = pd.DataFrame(filas).sort_values("valor", ascending=False).reset_index(drop=True)
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


def _prod_serie_periodo(g, col_fecha, col_punit, col_cant, col_valor, gran):
    """Serie por período (Semana/Mes/Año) de UN producto ya filtrado: precio
    promedio (relleno hacia adelante y hacia atrás en los huecos, para que
    la línea no corte), cantidad total y valor total. Indexada por la fecha
    de INICIO del período (eje real, no etiquetas de texto), así el
    promedio y las compras reales conviven en el mismo eje sin importar la
    granularidad elegida."""
    fe = pd.to_datetime(g[col_fecha], errors="coerce")
    if gran == "Semana":
        bucket = (fe - pd.to_timedelta(fe.dt.weekday, unit="D")).dt.normalize()
    elif gran == "Año":
        bucket = pd.to_datetime(fe.dt.year.astype("Int64").astype(str) + "-01-01",
                                errors="coerce")
    else:  # Mes
        bucket = fe.dt.to_period("M").dt.to_timestamp()
    base = pd.DataFrame({
        "bucket": bucket,
        "precio": pd.to_numeric(g[col_punit], errors="coerce"),
        "cantidad": (pd.to_numeric(g[col_cant], errors="coerce").fillna(0)
                     if col_cant else 0.0),
        "valor": pd.to_numeric(g[col_valor], errors="coerce").fillna(0),
    }).dropna(subset=["bucket"])
    if base.empty:
        return base.set_index("bucket")
    agg = base.groupby("bucket").agg(precio=("precio", "mean"),
                                     cantidad=("cantidad", "sum"),
                                     valor=("valor", "sum")).sort_index()
    agg["precio"] = agg["precio"].ffill().bfill()
    return agg


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
                            col_subfam=None):
    """Una fila de dos tarjetas: a la izquierda Familia | Subfamilia y,
    debajo, el ranking de productos que esos dos recortan; a la derecha la
    evolución del producto en foco.

    `col_subfam` va al FINAL y con default: el resto de la firma es
    posicional en el llamador, y en Cloud un commit que le cambia el orden
    a algo ya importado deja el `app.py` nuevo hablando con el paquete
    viejo (regla #357). Con default, la firma vieja sigue siendo válida.

    `d_full` es el histórico sin la fecha de la sección: de ahí sale la
    ventana fija de 3 meses del gráfico, que no depende del rango elegido."""
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
                _nom = html.escape(str(prod_foco))
                st.markdown(
                    f'<div class="cp-prod-evo-tit" title="{_nom}">'
                    f'{_nom}</div>', unsafe_allow_html=True)

                # ── VENTANA PROPIA, ELEGIBLE, ABRIENDO EN 3 MESES ────────────
                # Historia corta, porque cambió tres veces:
                #   · 2026-08-26 → 2026-09-12: ventana propia ELEGIBLE
                #     (`periodo.selector`: Rango/3m/12m/24m/Todo, abría en
                #     12m). Nació porque el rango de la franja era de ~24
                #     días y cualquier granularidad daba UN solo período.
                #   · 2026-09-12: se quitó, para que la fecha del segmento
                #     (entonces en esta tarjeta) mandara también acá —si no,
                #     era la regla #330, un control de fecha sentado sobre
                #     un gráfico que lo ignora—, y el mismo día volvió como
                #     ventana FIJA de 3 meses, sin selector, a pedido.
                #   · 2026-09-12, más tarde, a pedido: «no permite cambiar
                #     las opciones de "Últimos 3 meses", recuerdo que se
                #     podía personalizar». Vuelve el desplegable, abriendo
                #     en 3m. Lo que se quiso fijar era el DEFAULT, no quitar
                #     la elección.
                #
                # La #330 ya no muerde: la fecha del segmento vive en la
                # OTRA tarjeta, así que ésta tiene un solo control de fecha
                # y es el suyo. Con «Rango» el gráfico sigue a esa fecha.
                # Las etiquetas dicen el período entero («Últimos 3 meses»,
                # no «3m»): con el selector de las tablas a la vista, que
                # cada tarjeta diga qué mira con todas las letras.
                #
                # El ancla es el último día CON DATOS del parquet, no `hoy`
                # (ver el docstring de `graficos/periodo.py`). La ventana se
                # recorta de `d_full`, el histórico sin la fecha de la
                # sección: con `dd` quedaría dentro del rango elegido.
                # columnas-internas: ventana y granularidad, dentro de la
                # tarjeta. No es una fila de drill.
                _c_win, _c_gran = st.columns([1.1, 1],
                                             vertical_alignment="center")
                with _c_win:
                    with st.container(key="compras_prod_periodo_wrap"):
                        _op_prod = periodo.selector(
                            "compras_prod_periodo", default="3m",
                            widget="lista",
                            format_func=lambda o: _ETIQ_VENTANA_EVO.get(o, o))
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
                with _c_gran:
                    with st.container(key="compras_prod_gran"):
                        gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                                        default="Mes",
                                        key="compras_prod_gran_pills",
                                        label_visibility="collapsed") or "Mes"

                g = _src_evo[_src_evo[col_prod].astype(str) == prod_foco]
                # Las cifras del encabezado salen de `g`, o sea de la MISMA
                # ventana que las barras. Si salieran de `ranking` —que mira
                # el rango de la sección— serían un número describiendo un
                # período y unas barras dibujando otro.
                fila = _prod_stats(g, col_fecha, col_punit, col_cant, col_valor,
                                   col_um)
                agg = _prod_serie_periodo(g, col_fecha, col_punit, col_cant,
                                          col_valor, gran)

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
                    st.markdown(
                        f'<div style="font-size:12px;color:{GRIS_TEXTO};margin:0 0 2px;">'
                        f'actual <b>S/ {fila["fin"]:,.2f}{_um}</b> · '
                        f'<b style="color:{color_var};">'
                        f'{"+" if (var_pct or 0) >= 0 else "−"}{abs(var_pct or 0):.1f}%'
                        f'</b> 1ª → última compra</div>'
                        f'{_rango_txt}',
                        unsafe_allow_html=True)

                    # ── BARRAS, con las dos cifras SIEMPRE a la vista ────────
                    # Antes había que elegir una de tres (Precio/Cantidad/
                    # Valor) con un selector, y las otras dos no existían. Ahora
                    # la barra ES el valor comprado del período y encima lleva,
                    # fijo, el precio promedio de ese período — que es la
                    # pregunta que traía a este panel ("¿a cuánto me salió, y
                    # cuánto compré?") respondida de una sola mirada.
                    #
                    # El valor va COMPACTO (`_fmt_soles_compacto`, nacido para
                    # este mismo problema en ventas_comparativo.py): "S/ 11k"
                    # entra en una barra angosta donde "S/ 11,268" se corta o
                    # se pisa con la vecina. El monto exacto sigue en el hover.
                    fig = go.Figure()
                    _precio = agg["precio"].tolist()
                    _valor = agg["valor"].tolist()
                    # LA ETIQUETA ROTA SI NO ENTRA, no se encoge. MEDIDO en
                    # vivo: el panel da 312px de ancho y la etiqueta de dos
                    # renglones ocupa 34-36px, así que entran hasta ~8 barras.
                    # Con 13 (la ventana de 12 meses por Mes) Plotly no la
                    # oculta ni la corta: la ESCALA hasta 13px de ancho por 8
                    # de alto — sigue en el DOM y ya no se lee. Es la trampa de
                    # la regla #91, y la razón de que este umbral esté acá y no
                    # a ojo.
                    #
                    # Rotada, la etiqueta necesita ~10px de ancho en vez de 36,
                    # así que entra siempre. Se paga leyéndola de costado, que
                    # es mejor que no leerla: el pedido fue "etiqueta SIEMPRE
                    # visible".
                    _muchas = len(agg) > 8
                    if _muchas:
                        _etiquetas = [f"S/ {pr:,.2f} · {_fmt_soles_compacto(v)}"
                                      for pr, v in zip(_precio, _valor)]
                    else:
                        _etiquetas = [f"S/ {pr:,.2f}<br>{_fmt_soles_compacto(v)}"
                                      for pr, v in zip(_precio, _valor)]
                    fig.add_bar(
                        x=agg.index, y=_valor, marker_color=ACENTO,
                        text=_etiquetas, textposition="outside",
                        textangle=-90 if _muchas else 0,
                        textfont=dict(size=10, color=GRIS_TEXTO),
                        cliponaxis=False, constraintext="none",
                        customdata=_precio,
                        hovertemplate=("%{x|%d/%m/%Y}<br>valor S/ %{y:,.2f}"
                                       "<br>precio prom. S/ %{customdata:,.2f}"
                                       "<extra></extra>"),
                    )
                    _compras_layout(fig, alto=_ALTO_EVO)
                    fig.update_layout(showlegend=False,
                                      yaxis=dict(showticklabels=False),
                                      bargap=0.35)
                    # Techo con aire para que la etiqueta de DOS renglones
                    # quepa encima de la barra más alta: `textposition=
                    # "outside"` no expande el rango solo, y sin esto la
                    # etiqueta del máximo se corta contra el borde.
                    # Rotada, la etiqueta ocupa ALTO en vez de ancho, así que
                    # el techo tiene que dar más aire.
                    if max(_valor) > 0:
                        fig.update_yaxes(
                            range=[0, max(_valor) * (1.75 if _muchas else 1.28)])
                    fig.update_xaxes(**_eje_x_kwargs(gran, agg))
                    st.plotly_chart(fig, use_container_width=True,
                                    key=f"compras_g_prod_{gran}")

