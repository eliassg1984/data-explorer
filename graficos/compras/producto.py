"""graficos.compras.producto - drill de Producto.

Ranking de TODOS los productos comprados (valor, cantidad, UM, precio real
de inicio/fin de periodo y su variación) con el mismo patrón de tabla-
ranking + clic-para-enfocar que graficos/compras/proveedor.py. El producto
en foco muestra su evolución (Precio / Cantidad / Valor, con granularidad
Semana / Mes / Año) fusionando el promedio del período con el precio real
de cada compra en un solo gráfico. Esa tarjeta tiene VENTANA PROPIA
(`periodo.selector`, default 12m) desde el 2026-08-26: heredando el rango
de la franja —~24 días— cualquier granularidad daba UN solo período y la
"línea" de promedio era un punto suelto.

Reemplaza a los antiguos drills "Precio top 10", "Precio por compra" y
"Cantidad por producto" (graficos/compras/cantidad.py, eliminado 2026-08-17):
las tres separaban precio-promedio, precio-real y cantidad/valor de UN mismo
producto en tres pantallas distintas — acá conviven en una, con un selector
de texto plano en vez de tabs/pills con caja (a pedido, para no ocupar sitio).

ARRIBA de todo eso, la tarjeta del drill jerárquico: tres tablas AgGrid en
cascada — Familia › Subfamilia › Producto (2026-09-09, a pedido). Un clic
en una familia repuebla las subfamilias; un clic en una subfamilia, los
productos; y soltar la subfamilia devuelve el tercer panel a la familia
entera, que es lo que hacía la versión de DOS paneles que esto reemplaza.
Cada % es sobre su padre, no sobre el total. Las tres son tablas con el
mismo patrón barra-en-celda (2026-08-26 — antes el panel de la derecha era
un `_compras_mini_barras` de Plotly), a pedido para que la fila se lea como
una sola grilla y no como tabla+gráfico.

Desde el 2026-09-11 esas tres se ven como el Ranking de Proveedores, a
pedido: mismo `CSS_RANKING_GRID` (franja en vez de caja, todo blanco, sin
líneas verticales, cuerpo 11.5 y el texto en violeta), mismas filas de
24px y la misma capitalización de nombre propio. Y sin los tres captions
que llevaban debajo: lo que decían se mudó a los `headerTooltip` de las
columnas, que no gastan alto. Ver regla #378.
"""

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
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CATEGORIA_SEC, COLUMNAS_DRILL,
    CROMO_GRID_RANK, GAP_DRILL, filtro_proveedores, selector_fecha_tarjeta,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos import alturas, periodo

_ALTO_FILA = 28
"""Filas "algo delgadas" a pedido (2026-08-24) para el ranking de PRODUCTOS
de este drill — el mismo número que usa el `rowHeight` de AgGrid en
Inventario (antes era el `row_height=` de `st.dataframe`; con el pase a
AgGrid del mismo día, la constante es `rowHeight` en `gridOptions`).

Hasta el 2026-09-11 era "el de los DOS rankings de este drill". Ese día el
de Familia se fue a los 24px del Ranking de Proveedores (`ALTO_FILA_RANK`
en `_comun.py`, a pedido) y acá se queda el de Productos, que comparte fila
con la figura de Evolución: la tarjeta de al lado no encoge —su alto sale
de `alturas`— así que adelgazar esta tabla no baja la fila, sólo le deja un
hueco blanco abajo (la regla de "dos tarjetas de la misma fila miden lo
mismo", `estilos/_80_cards.py`). Si algún día la Evolución se dimensiona
contra la tabla, este 28 puede irse detrás del otro.

Con un alto de fila explícito, `_ALTO_FRAME` tiene que usar el mismo número:
si no, el frame se calcula para un alto y las filas reales dibujan otro,
dejando aire de sobra abajo (o de más, si `_ALTO_FRAME` quedara más chico
que 8 filas reales)."""

_ALTO_FRAME = alturas.por_filas(8, px_fila=_ALTO_FILA, extra=45, minimo=0)

_FILAS_FAM = 7
"""Filas que RESERVAN los tres paneles del drill de Familia.

Son los tres el mismo número a propósito: los paneles se leen como UNA
grilla de tres columnas (ver la tarjeta, más abajo), así que una altura por
panel los dejaría terminando a tres alturas distintas. Y es un techo, no un
alto: lo que sobra scrollea adentro.

7 y no 8 desde el 2026-09-11, a pedido ("reduzcamos verticalmente las
tarjetas"), junto con el pase a filas de 24px y con la salida de los tres
captions de abajo. Medido en el navegador: la tarjeta pasó de 421px a 276.
Lo que cabe con 7 filas, medido sobre R2 el mismo día: las 8 familias del
parquet (5 con el filtro de entrada) entran casi enteras en el panel A, y
los otros dos scrollean igual con 7 que con 8 — ALIMENTOS tiene 10
subfamilias y 442 productos."""

_ALTO_FRAME_FAM = alturas.por_filas(
    _FILAS_FAM, px_fila=ALTO_FILA_RANK, extra=CROMO_GRID_RANK, minimo=0)
"""El `height=` de los tres AgGrid del drill de Familia.

`extra=CROMO_GRID_RANK` y no el 45 de `_ALTO_FRAME`: estos tres grids se
dibujan con la cabecera de 32px del Ranking de Proveedores, y el cromo hay
que contarlo con el número que de verdad se dibuja (ver `_comun.py`)."""

_KEYS_WIDGET = ("compras_prod_gran_pills", "compras_prod_periodo",
                "cp_prod_prov_q", "cp_prod_prov_cb::*")
"""Los controles de esta sección, para que la escalada no se los lleve.

La consume `preservar_widgets` en el `st.rerun(scope="app")` de más abajo:
ese rerun aborta la corrida antes de dibujarlos y Streamlit recolecta lo
que no se dibujó, así que sin esta tupla mover la fecha de la cabecera
devolvía la granularidad a «Mes», la ventana a «12m» y marcaba de nuevo a
TODOS los proveedores. Ver `graficos/base.py::preservar_widgets` y
`arquitectura.md` regla #373. Las dos últimas son del filtro de proveedores
(`_comun.py`), que abre una checkbox por razón social."""

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
/* El selector de ventana (3m/12m/…), APLANADO A TEXTO para que haga
   juego con la granularidad de al lado: los dos son texto suelto, no
   una caja contra unas palabras. Misma receta que `cp_evo_ctrl` en
   _css_proveedor.py — se conserva el chevron, que es la única señal de
   que eso despliega. */
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

    Los PRODUCTOS del panel C quedan fuera de esto a propósito: ya vienen
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


def _fam_ranking(dd, col_fam, col_prod, col_valor, col_subfam=None):
    """Una familia por fila: valor total, Nº de productos distintos y —si el
    parquet trae Subfamilia— cuántas subfamilias hay detrás.

    `subfamilias` es la que se MUESTRA desde el 2026-09-09, y `productos`
    quedó calculada pero fuera de la tabla: con tres paneles no entran las
    dos (ver el comentario de anchos en la tarjeta), y la que dice algo en
    el panel A es cuántas puertas abre el clic. El conteo de productos baja
    al panel de Subfamilia, donde es más chico y más útil."""
    g = dd.copy()
    g[col_fam] = _fam_normalizada(g, col_fam)
    agg = {"valor": (col_valor, "sum"), "productos": (col_prod, "nunique")}
    if col_subfam and col_subfam in g.columns:
        # Normalizada, no cruda: si no, una subfamilia vacía no contaría acá
        # y sí sería una fila del panel B ("Sin subfamilia").
        g[col_subfam] = _subfam_normalizada(g, col_subfam)
        agg["subfamilias"] = (col_subfam, "nunique")
    out = g.groupby(col_fam).agg(**agg)
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


def _grupo_productos(g, col_prod, col_valor, col_cant, col_um):
    """Un producto por fila del grupo que se le pase (una familia entera o
    una de sus subfamilias): valor, % sobre ESE grupo, cantidad y UM.

    La CANTIDAD se suma por PRODUCTO y nunca por el grupo, y no es un
    detalle de implementación. Medido sobre R2 el 2026-09-09: los 1.592
    productos de `compras.parquet` tienen UNA sola unidad cada uno (cero
    con más de una), así que la cantidad de una fila es exacta y se puede
    mostrar — pero dentro de una misma subfamilia se mezclan (ABARROTES
    compra en LITROS, KILOS y UND el mismo mes). De ahí las dos decisiones
    que van pegadas a esta función: la UM viaja al lado del número, y la
    columna NO lleva fila de totales, porque sumar 213 kilos con 441
    unidades da un número inventado. Misma familia de trampa que el grano
    de las columnas `*_ANO_ANTERIOR` (reglas #198 a #200): el gráfico sale
    lindo igual, sólo miente."""
    agg = {"valor": (col_valor, "sum")}
    if col_cant and col_cant in g.columns:
        agg["cantidad"] = (col_cant, "sum")
    out = g.groupby(col_prod).agg(**agg)
    if "cantidad" not in out.columns:
        out["cantidad"] = 0.0
    if col_um and col_um in g.columns:
        # Moda y no `first`: mismo criterio que `_prod_ranking`, para que la
        # UM de un producto no dependa de qué compra quedó primera.
        out["um"] = g.groupby(col_prod)[col_um].agg(
            lambda s: str(s.dropna().mode().iat[0]) if not s.dropna().empty
            else "")
    else:
        out["um"] = ""
    out = out.sort_values("valor", ascending=False).reset_index()
    out = out.rename(columns={col_prod: "producto"})
    out["producto"] = out["producto"].astype(str)
    tot = out["valor"].sum() or 1.0
    out["pct"] = out["valor"] / tot * 100
    return out


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


def _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant, col_punit,
                            col_um, col_fecha, col_prov=None, d_full=None,
                            col_subfam=None):
    """Arriba, el drill Familia › Subfamilia › Producto. Debajo, el ranking
    de productos → evolución del producto en foco (Precio / Cantidad /
    Valor).

    `col_subfam` va al FINAL y con default: el resto de la firma es
    posicional en el llamador, y en Cloud un commit que le cambia el orden
    a algo ya importado deja el `app.py` nuevo hablando con el paquete
    viejo (regla #357). Con default, la firma vieja sigue siendo válida."""
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

    # ── Filtro de proveedores ────────────────────────────────────────────
    # 2026-09-02, a pedido ("añadamos el de proveedor"). El MISMO componente
    # que el Ranking de Proveedores, no una copia: vive en
    # `_comun.py::filtro_proveedores` desde este mismo pedido — ver el
    # comentario de allá sobre por qué devuelve la selección y el dibujo por
    # separado.
    #
    # Lo que filtra acá NO es lo mismo que allá, y conviene tenerlo claro:
    # en Proveedor la selección elige QUÉ FILAS del ranking se ven; acá
    # recorta el universo de compras sobre el que se rankean los PRODUCTOS
    # ("los productos que le compro a estos proveedores"). Por eso se aplica
    # sobre `dd`, antes de `_prod_ranking`, y no sobre el resultado.
    #
    # `clave` propio ("cp_prod_prov") porque Compras se lee APILADA: los dos
    # popovers están en la página a la vez y sus widgets no pueden compartir
    # key. El CSS de cada prefijo se lista explícito en `_css_proveedor.py`.
    _provs_prod = []
    if col_prov and col_prov in dd.columns:
        _provs_prod = (dd.groupby(col_prov)[col_valor].sum()
                         .sort_values(ascending=False).index.tolist())
    _pop_prov_prod = None
    if _provs_prod:
        _sel_prov_prod, _pop_prov_prod = filtro_proveedores(
            "cp_prod_prov", _provs_prod)
        # `set` porque la lista puede tener ~cientos y esto corre por fila.
        dd = dd[dd[col_prov].astype(str).isin({str(x) for x in _sel_prov_prod})]
        if dd.empty:
            st.info("Ningún proveedor seleccionado tiene compras en el rango.")
            return

    ranking = _prod_ranking(dd, col_prod, col_fecha, col_valor, col_cant,
                            col_punit, col_um)
    if ranking.empty:
        st.info("Sin productos con precio válido en el rango.")
        return

    # ── Card 1: el drill Familia › Subfamilia › Producto ────────────────
    # 2026-09-09, a pedido ("uno de familia, otro de subfamilia y otro de
    # producto… al hacer clic en una familia, muestre en el otro cuadro las
    # subfamilias"). Antes eran DOS paneles —familia → top 10 de SUS
    # productos— y el del medio no existía.
    #
    # Por qué el del medio importa, medido sobre R2 antes de escribir una
    # línea: ALIMENTOS es el 87% del gasto y era un callejón sin salida.
    # Abierto en 12 meses da CARNES 677k, ABARROTES 215k, VERDURAS 157k,
    # PESCADOS 146k, LÁCTEOS 137k, AVES 106k, FRUTAS 55k — o sea que el
    # "top 10 de ALIMENTOS" era en la práctica el top 10 de CARNES, y las
    # otras seis subfamilias no llegaban nunca a la pantalla.
    #
    # El panel del medio es OPCIONAL (`hay_sub`): si el parquet no trae
    # columna de Subfamilia, la tarjeta vuelve sola a los dos paneles de
    # antes, con la misma proporción de siempre.
    #
    # El `if not col_fam: return` que tenía se vuelve un `if` normal, y no
    # es cosmético: arriba del ranking, un `return` acá se llevaría puesto
    # el resto de la sección cada vez que el parquet no traiga columna de
    # Familia — o sea, apagaría la vista entera por una tarjeta.
    if col_fam and col_fam in dd.columns:
        hay_sub = bool(col_subfam and col_subfam in dd.columns)
        with st.container(border=True, key="compras_prod_card_familia"):
            fam_ranking = _fam_ranking(dd, col_fam, col_prod, col_valor,
                                       col_subfam if hay_sub else None)
            fam_focus = st.session_state.get("compras_prod_fam_focus")
            if fam_focus not in set(fam_ranking["familia"]):
                fam_focus = None

            if hay_sub:
                # 1.35 al último y no tres iguales: es el que carga el nombre
                # largo (media 17,5 caracteres, máximo 64) MÁS dos columnas
                # extra (Cant./UM); los otros dos llevan nombres de ≤22 y ≤38.
                # columnas-internas: los tres niveles del drill.
                col_famtabla, col_subtabla, col_famdet = st.columns(
                    [1, 1, 1.35], gap=GAP_DRILL)
            else:
                # columnas-internas: sin Subfamilia la tarjeta vuelve a los dos
                # paneles de antes, con la proporción que ya tenía.
                col_famtabla, col_famdet = st.columns([1.3, 1], gap=GAP_DRILL)
                col_subtabla = None

            with col_famtabla:
                st.markdown('<div class="cp-prod-rank-tit">Compras por familia</div>',
                           unsafe_allow_html=True)

                disp_fam = fam_ranking.rename(columns={
                    "familia": "Familia", "valor": "Valor", "pct": "%",
                    "productos": "Productos", "subfamilias": "Subfam",
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
                # Con el panel del medio, el conteo que se muestra es el de
                # SUBFAMILIAS (cuántas puertas abre el clic); sin él, el de
                # productos, que es lo que había.
                _col_cuenta = "Subfam" if hay_sub else "Productos"
                _resp_fam = AgGrid(
                    disp_fam[["Familia", "Valor", "%", _col_cuenta, "_barra",
                             "_fam_raw"]],
                    gridOptions={
                        # Sin `flex`: mismo motivo que el ranking de arriba
                        # (`st_aggrid` le clava `width: 200` a toda columna sin
                        # `width` propio, y ese `width` le gana al `flex`).
                        #
                        # Los anchos de los TRES paneles se eligieron con la
                        # regla #349 en la mano: AG Grid reescala las columnas
                        # para llenar la grilla, así que un panel de ~264px
                        # (tres paneles en una laptop de 1010) las achica ~13%.
                        # El reparto prioriza "Valor", porque un número
                        # recortado por la izquierda es plausible y falso
                        # ("S/ 1,452,437" → "452,437"), mientras que un nombre
                        # recortado se ve recortado — y encima tiene tooltip.
                        "columnDefs": [
                            {"field": "Familia", "width": 104,
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
                            {"field": "%", "width": 38,
                             "type": "numericColumn",
                             "headerTooltip": "% sobre el total comprado "
                                              "en el rango",
                             "valueFormatter": _js_pct_prod},
                            {"field": _col_cuenta,
                             "headerName": "Subfam." if hay_sub else "Prod.",
                             "width": 52, "type": "numericColumn",
                             "headerTooltip": ("Subfamilias que abre el clic"
                                               if hay_sub else
                                               "Productos distintos"),
                             "valueFormatter": _js_num0_prod},
                            {"field": "_barra", "hide": True},
                            {"field": "_fam_raw", "hide": True},
                        ],
                        "rowSelection": {"mode": "singleRow",
                                         "checkboxes": False,
                                         "enableClickSelection": False},
                        "onRowClicked": _js_toggle_prod,
                        # Que las columnas LLENEN el panel, que es la otra
                        # mitad de parecerse al Ranking de Proveedores: sin
                        # esto los 302px declarados no entran en los 255 de
                        # un panel a 1024px de ventana y la tabla sale con
                        # scroll horizontal y la última columna cortada
                        # (medido; se ve en la captura del pedido).
                        #
                        # `fitGridWidth` y NO `colDef.flex`, y eso está
                        # medido en la regla #350: estos tres grids se
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
                    # elegir CARNES y saltar a VINOS deja el panel de la
                    # derecha mostrando carne. El guard de más abajo lo
                    # ataja igual (la subfamilia vieja no está en el ranking
                    # de la familia nueva), pero se limpia también acá para
                    # que el estado y la key del grid del medio —que lleva
                    # el slug de la familia— cuenten lo mismo en la MISMA
                    # pasada, sin depender del orden de lectura.
                    st.session_state.pop("compras_prod_subfam_focus", None)

            # El foco se resuelve DESPUÉS del panel A y antes de los otros
            # dos: así el clic de esta corrida ya manda, sin un rerun de por
            # medio. Sin selección se enfoca la familia de arriba, que es lo
            # que evita que la tarjeta abra vacía.
            fam_foco = (fam_focus if fam_focus is not None
                        else fam_ranking.iloc[0]["familia"])
            d_fam = dd[_fam_normalizada(dd, col_fam) == fam_foco]

            sub_focus = None
            if hay_sub:
                with col_subtabla:
                    st.markdown(
                        f'<div class="cp-prod-rank-tit">'
                        f'{_compras_truncar(_sin_gritar(fam_foco), 34)}</div>',
                        unsafe_allow_html=True)
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
                        # vuelta y la que filtra el panel C. Ver el panel A.
                        disp_sub["_sub_raw"] = disp_sub["Subfamilia"]
                        disp_sub["Subfamilia"] = disp_sub["Subfamilia"].map(
                            _sin_gritar)
                        _resp_sub = AgGrid(
                            disp_sub[["Subfamilia", "Valor", "%", "Productos",
                                     "_barra", "_sub_raw"]],
                            gridOptions={
                                # Mismos anchos que el panel A: los tres se
                                # leen como una sola grilla, no como tres
                                # tablas que se parecen.
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
                                    {"field": "%", "width": 38,
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

            with col_famdet:
                # Sin subfamilia elegida el panel muestra la familia ENTERA,
                # que es exactamente lo que hacía la tarjeta de dos paneles.
                # O sea: el drill agrega un nivel sin sacar ninguna lectura.
                # `ambito` (el nombre del grupo que se está viendo) vivía
                # acá y se fue con el caption que lo nombraba: el título del
                # panel ya dice lo mismo, dos renglones más abajo.
                if sub_focus:
                    g_det = d_fam[_subfam_normalizada(d_fam, col_subfam) == sub_focus]
                    titulo_det = _compras_truncar(_sin_gritar(sub_focus), 40)
                else:
                    g_det = d_fam
                    # "· todas" y no el nombre pelado: sin subfamilia elegida
                    # este panel y el del medio se titulaban IGUAL, dos veces
                    # el nombre de la familia, uno al lado del otro.
                    _fam_tit = _sin_gritar(fam_foco)
                    titulo_det = (f"{_compras_truncar(_fam_tit, 30)} · todas"
                                  if hay_sub else _compras_truncar(_fam_tit, 40))
                st.markdown(
                    f'<div class="cp-prod-rank-tit">{titulo_det}</div>',
                    unsafe_allow_html=True)
                prod_grupo = _grupo_productos(g_det, col_prod, col_valor,
                                              col_cant, col_um)
                if prod_grupo.empty:
                    st.info("Sin productos para esta selección.")
                else:
                    disp_prodfam = prod_grupo.rename(columns={
                        "producto": "Producto", "valor": "Valor", "pct": "%",
                        "cantidad": "Cant", "um": "UM",
                    })
                    _val_max_prodfam = float(prod_grupo["valor"].max())
                    disp_prodfam["_barra"] = disp_prodfam["Valor"] / _val_max_prodfam * 100
                    AgGrid(
                        disp_prodfam[["Producto", "Valor", "%", "Cant", "UM",
                                     "_barra"]],
                        gridOptions={
                            # SIN el punto en "Cant": AG Grid resuelve `field`
                            # con notación de PATH, así que un campo "Cant."
                            # se parte en ["Cant", ""] y la celda sale vacía en
                            # silencio (regla #192). El punto vuelve como
                            # `headerName`, igual que en el ranking de arriba.
                            "columnDefs": [
                                {"field": "Producto", "width": 150,
                                 "tooltipField": "Producto"},
                                {"field": "Valor", "width": 108, "minWidth": 100,
                                 "type": "numericColumn",
                                 "cellStyle": _js_barra_prod,
                                 "valueFormatter": _js_soles0_prod},
                                {"field": "%", "width": 38,
                                 "type": "numericColumn",
                                 "headerTooltip": "% sobre el total de la "
                                                  "selección de la izquierda",
                                 "valueFormatter": _js_pct_prod},
                                # Lo que decía el caption y no se puede
                                # perder: la cantidad va con su unidad y NO
                                # se suma entre productos (ver el docstring
                                # de `_grupo_productos`).
                                {"field": "Cant", "headerName": "Cant.",
                                 "width": 58, "type": "numericColumn",
                                 "headerTooltip": "Cantidad en la UM del "
                                                  "producto; no se suma "
                                                  "entre productos",
                                 "valueFormatter": _js_num0_prod},
                                {"field": "UM", "width": 46,
                                 "headerTooltip": "Unidad de kardex"},
                                {"field": "_barra", "hide": True},
                            ],
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
                        # Fam Y subfamilia en la key: es lo que fuerza el
                        # remonte con los datos nuevos. Con una key estable y
                        # el `client_wins` que trae st_aggrid de fábrica, el
                        # navegador puede quedarse con la tabla anterior
                        # (regla #227).
                        key=("compras_prod_fam_det_tab_"
                             f"{_slug(fam_foco)}_{_slug(sub_focus or 'todo')}"),
                    )
                # La lista NO se corta en 10: el punto de bajar tres niveles
                # es llegar al ítem. Medido sobre R2, una subfamilia tiene
                # mediana 2 productos en un mes y máximo 180 en 12 meses, así
                # que lo que sobra scrollea dentro del frame de `_FILAS_FAM`.
                #
                # Acá vivía el caption que contaba los productos del ámbito y
                # repetía las dos advertencias de arriba. Se fue el
                # 2026-09-11 con los otros dos ("eliminemos el texto que está
                # abajo de ellos"); lo que decía no se perdió: el % y la
                # unidad los explica el `headerTooltip` de su columna, y el
                # conteo ya lo trae el panel de la izquierda, que muestra
                # cuántos productos tiene cada subfamilia.

    # ── Card 2: ranking de productos + evolución del producto en foco ──
    # 2026-09-02, a pedido ("al gráfico que está al costado de ranking de
    # producto, colocarlo en su propia tarjeta"). Este contenedor DEJA de
    # ser una tarjeta y queda como MARCO, exactamente el mismo movimiento
    # que hizo el drill de Proveedor el 2026-08-18: antes era el bloque
    # blanco que envolvía tabla + gráfico, ahora cada columna tiene el suyo
    # y el gris de la app los separa.
    #
    # El cambio de NOMBRE no es cosmético: la key vieja empezaba con
    # `compras_prod_card_`, que es un wildcard por FAMILIA en
    # estilos/_80_cards.py. Mientras la llevara seguiría pintándose de
    # blanco con padding y sombra ENCIMA de las dos tarjetas nuevas — un
    # bloque blanco dentro de otro. Sacarlo de la familia es lo que lo
    # vuelve invisible, sin pelearle a la regla con overrides.
    with st.container(key="compras_prod_marco"):
        prod_focus = st.session_state.get("compras_prod_focus")
        if prod_focus not in set(ranking["producto"]):
            prod_focus = None

        col_tabla, col_detalle = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)
        with col_tabla:
            with st.container(border=True, key="compras_prod_card_ranking"):
                # 2026-08-26, a pedido ("el mismo selector de fecha que la
                # tabla de proveedores"): el MISMO componente, no una copia —
                # vive en `_comun.py::selector_fecha_tarjeta`. Escribe la misma
                # clave canónica del rango, así que mover la fecha acá mueve
                # también el Ranking de Proveedores: son dos puertas al mismo
                # dato, que es justo lo correcto (las dos tablas rankean sobre
                # el mismo período).
                #
                # El `clave` distinto ("cp_prod") no es cosmético: desde que
                # Compras se lee APILADA, las dos tarjetas están en la página a
                # la vez, así que sus widgets no pueden compartir key.
                # 2026-09-02, a pedido ("alineemos el toggle de fecha...
                # para que quede alineado con el título, así como está en
                # Ranking de Proveedores"). El título entra por `titulo_html`
                # y comparte el flex row con los controles, en vez de gastar
                # un renglón propio de ancho completo con el control flotando
                # `position: absolute` sobre su esquina. Es el mismo cambio
                # que se le hizo a la tarjeta de Proveedores el 2026-09-01;
                # el CSS de esta fila pasó a compartir el bloque de aquélla
                # en `_css_proveedor.py`.
                selector_fecha_tarjeta(
                    "cp_prod", "_cp_prod_atajo_pendiente",
                    titulo_html='<div class="cp-prod-rank-tit">'
                                'Ranking de productos</div>',
                    extra=_pop_prov_prod,
                    categoria=CATEGORIA_SEC["compras_sec_producto"])

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
                        # Ocho columnas visibles, y NINGUNA lleva `flex`: se
                        # probó (Producto/Valor con flex:2/1.3 + minWidth) y
                        # `st_aggrid` le clava `width: 200` a cada columna que
                        # no trae un `width` propio — verificado con
                        # `api.getColumnDefs()`, que devolvía flex Y width:200
                        # JUNTOS en el mismo colDef resuelto. AG Grid prioriza
                        # el `width` explícito para el tamaño inicial, así que
                        # el flex nunca llegaba a repartir nada: a 1280px
                        # Producto+Valor se comían 400px fijos y "Var" quedaba
                        # fuera del viewport, con una scrollbar de 1px. Ancho
                        # fijo en las OCHO columnas —mismo criterio que ya
                        # usaban las seis angostas— saca el problema de raíz.
                        "columnDefs": [
                            {"field": "Producto", "width": 150,
                             "tooltipField": "Producto"},
                            {"field": "Valor", "width": 96,
                             "type": "numericColumn",
                             "cellStyle": _js_barra_prod,
                             "valueFormatter": _js_soles0_prod},
                            {"field": "%", "width": 52,
                             "type": "numericColumn",
                             "valueFormatter": _js_pct_prod},
                            {"field": "Cant", "headerName": "Cant.",
                             "width": 60, "type": "numericColumn",
                             "valueFormatter": _js_num0_prod},
                            {"field": "UM", "width": 56},
                            {"field": "Inicio", "width": 72,
                             "type": "numericColumn",
                             "valueFormatter": _js_soles2_prod},
                            {"field": "Fin", "width": 72,
                             "type": "numericColumn",
                             "valueFormatter": _js_soles2_prod},
                            {"field": "Var", "width": 60,
                             "type": "numericColumn",
                             "valueFormatter": _js_pct_signed_prod},
                            {"field": "_barra", "hide": True},
                        ],
                        "rowSelection": {"mode": "singleRow",
                                         "checkboxes": False,
                                         "enableClickSelection": False},
                        "onRowClicked": _js_toggle_prod,
                        "rowHeight": _ALTO_FILA,
                        "headerHeight": 38,
                        "suppressCellFocus": True,
                        "suppressMovableColumns": True,
                    },
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    height=_ALTO_FRAME,
                    update_on=["selectionChanged"],
                    key="compras_prod_rank_tab",
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
                st.caption("UM = unidad de kardex · Inicio/Fin = primera y última "
                          "compra real del período · % es sobre el total del rango.")

        with col_detalle:
            with st.container(border=True, key="compras_prod_card_evo"):
                prod_foco = prod_focus if prod_focus is not None else ranking.iloc[0]["producto"]

                st.markdown(f'<div style="font-size:13.5px;font-weight:700;">'
                           f'{_compras_truncar(prod_foco, 40)}</div>',
                           unsafe_allow_html=True)

                # ── VENTANA PROPIA DE ESTA TARJETA ───────────────────────────
                # 2026-08-26, a pedido ("creo que no es entendible para el
                # usuario"), y es la CAUSA de que no lo fuera: el eje salía del
                # rango de la franja —~24 días por defecto— así que pedirle
                # "agrupá por Mes" o "por Año" a 24 días sólo podía dar UN
                # grupo. Medido: con el default, la traza "Promedio mes" tenía
                # 1 punto y el eje un solo tick ("Aug 2026"); en Año, 1 punto
                # anclado al 1-ene mientras las compras eran de agosto, y las
                # 11 compras reales apiladas en 18px de los ~300 del gráfico.
                #
                # Con ventana propia (mismo `periodo.selector` que Evolución en
                # proveedor.py y que Volatilidad) "Mes" da 12 puntos y la línea
                # existe de verdad. El caso de UN período sigue siendo posible
                # (elegir "Año" sobre 12 meses) y se dibuja distinto, más
                # abajo — no se esconde la opción: que una granularidad
                # aparezca y desaparezca según el rango confunde más que
                # dibujar bien el caso degenerado.
                # ── UNA SOLA FILA DE CONTROLES: ventana + granularidad ──────
                # 2026-08-26, a pedido. Antes eran TRES renglones apilados —
                # ventana, granularidad y modo (Precio/Cantidad/Valor)— y el
                # gráfico arrancaba recién debajo. El modo se va del todo (las
                # tres métricas pasan a verse SIEMPRE, como etiqueta de cada
                # barra) y los dos que quedan comparten renglón, alineados.
                # Son ~40px que gana el gráfico.
                # columnas-internas: ventana y granularidad, dentro de la
                # tarjeta. No es una fila de drill: COLUMNAS_DRILL no aplica.
                _c_win, _c_gran = st.columns([1, 1.35],
                                             vertical_alignment="center")
                with _c_win:
                    with st.container(key="compras_prod_periodo_wrap"):
                        _op_prod = periodo.selector("compras_prod_periodo",
                                                    widget="lista")
                with _c_gran:
                    with st.container(key="compras_prod_gran"):
                        gran = st.pills("Agrupar por", ["Semana", "Mes", "Año"],
                                        default="Mes",
                                        key="compras_prod_gran_pills",
                                        label_visibility="collapsed") or "Mes"

                _src_evo = dd
                if _op_prod != periodo.HEREDA and d_full is not None:
                    _rec = periodo.recortar(d_full, col_fecha, _op_prod)
                    _rec = _rec.copy()
                    _rec[col_fecha] = pd.to_datetime(_rec[col_fecha], errors="coerce")
                    _rec[col_punit] = pd.to_numeric(_rec[col_punit], errors="coerce")
                    _rec[col_valor] = pd.to_numeric(_rec[col_valor], errors="coerce").fillna(0)
                    _src_evo = _rec.dropna(subset=[col_fecha, col_prod])

                g = _src_evo[_src_evo[col_prod].astype(str) == prod_foco]
                # Las cifras del encabezado salen de `g`, o sea de la MISMA
                # ventana que las barras. Antes salían de `ranking`, que se
                # calcula sobre el rango de la franja: con dos ventanas
                # distintas sería un número describiendo un período y unas
                # barras dibujando otro.
                fila = _prod_stats(g, col_fecha, col_punit, col_cant, col_valor,
                                   col_um)
                agg = _prod_serie_periodo(g, col_fecha, col_punit, col_cant,
                                          col_valor, gran)

                if agg.empty or fila is None:
                    st.info("Sin compras con precio válido para este producto.")
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
                    _compras_layout(fig, alto=alturas.MINI_PROD_EVO)
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

