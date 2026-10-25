"""
graficos.inventario — dashboard de Inventario Valorizado (v3). Layout unificado
con chips en franja blanca + card con pills.

v3 (2026-08-10) reemplaza las 4 vistas de v2 (Área y familia / Torta / Top
valor / Top cantidad) por 3: **Por área**, **Por familia** (mismo ranking
ordenado para las dos — desde 2026-08-23 una TABLA con barra de progreso en
la celda, como el Ranking de proveedores de Compras; la torta se rompía
apenas una familia concentraba >70% del total) y una tercera que fue
"Buscar producto" hasta el 2026-09-17: una ficha de UN producto o de UN
grupo, con una barra por producto. Hoy es **Productos**, el listado entero
como tabla con las áreas de cada producto desplegables en su fila y filtros
de familia, subfamilia y producto — vive en `inventario_productos.py`, ver
la regla #466.
El KPI "Valorizado total" vivía DENTRO de la card izquierda (no en una
franja aparte arriba: se probó así y quedaba la card muy abajo). Se retiró
de las cuatro secciones el 2026-09-13, a pedido: en las dos de ranking lo
dice la fila TOTAL de la tabla. Ver regla #404.

2026-09-13, a pedido: Por área y Por familia son TABLAS de punta a punta, y
las tres son clickeables en cadena. Ranking (izquierda) → desglose del nivel
siguiente (derecha, era un `go.Bar` sin clic) → productos (franja de abajo),
que ahora lista TODOS los del recorte en vez de un top-20: "ya que es una
tabla, el usuario puede hacer scroll". Ver `arquitectura.md` regla #403.

2026-10-11, a pedido (regla #638): el reporte queda en DOS vistas de stock.
«Stock por Familia» se fue —era Stock por Área empezando por la familia— y
su lugar lo ocupa la fila «Todas las áreas», la primera del ranking de
áreas. La tabla de productos de abajo (la de las casillas y «Selección %»)
también: la tabla de productos es una sola, la de Stock por Producto. Abajo
quedan «Qué más cambió» y «Dónde mirar», que llevan a esa vista con el
filtro puesto. La tabla de abajo sólo vuelve con «Inactivos y servicios»,
que no tiene otra vista donde verse (regla #598).
"""

import numpy as np
import pandas as pd
import streamlit as st


from tema import (
    ACENTO, ACENTO_TEXTO, ACENTO_TEXTO_OSCURO, AJUSTE_ALERTA_TEXTO, AJUSTE_NEG,
    AJUSTE_NEG_TEXTO, GRIS_BORDE, GRIS_TEXTO, GRIS_TEXTO_MEDIO, LAVANDA_BORDE,
    LAVANDA_CABECERA_GRUPO, LAVANDA_CHIP, LAVANDA_FILA, TEXTO_PRINCIPAL,
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
# La ÚNICA del repo, y se importa de acá y no de `graficos.base` a propósito
# (`test_graficos.py::_pruebas_una_sola_nombre_propio` monta guardia): hubo
# dos definiciones hasta el 2026-09-11 y diferían en 48 de 773 nombres — el
# mismo texto escrito distinto según qué módulo lo formateara. Regla #379.
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.base import (
    compartimento_filtros, contar_filtros, dibujar_perspectiva, filtro_pills,
    _render_rail, pila_sin_tablas, rail_sin_tablas, poner_seleccion,
    _resolver, _slug, publicar_contexto_ia, renderizar_graficos_genericos,
    scroll_a_seccion, seccion_perezosa,
)
from graficos import alturas
# La vista 1 (Stock por Producto): su sección, la mini-línea —la misma en
# las dos vistas— y las claves de sus filtros, que «Ver sus productos» y
# «Dónde mirar» escriben para llevar al usuario allá con el filtro puesto.
from graficos.inventario_productos import (
    _JS_MINI_LINEA, _K_A_FECHA, _K_AREAS, _K_BUSCAR, _K_ESTADO, _K_FAMILIAS,
    _K_SUBFAMILIAS, _js_fijo, armar_listado, seccion_productos,
)
import analisis_stock
import data
from graficos.inventario_movimientos import seccion_movimientos
from data import INVENTARIO_ACTIVO

# Lo que NO es stock (regla #598): el nombre con que se lo ve en «Stock por
# Área» —una fila debajo del TOTAL que se abre como un área más— y la columna
# con el motivo que le agrega `separar_activos`. No dice «excluidos» a
# secas: el nombre tiene que decir QUÉ es, y son eso, artículos inactivos
# (en el producto, en el área o el área entera) y servicios.
ETIQUETA_EXCLUIDOS = "Inactivos y servicios"
COL_MOTIVO = "MOTIVO"
_COL_GRUPO_EXCL = "__grupo_excluidos"


def separar_activos(d):
    """`(activos, excluidos)`: lo que es stock y lo que no, con la regla de
    `data.INVENTARIO_ACTIVO` (regla #598).

    `excluidos` lleva además `COL_MOTIVO`, la PRIMERA marca que falla en el
    orden de esa tupla (área inactiva antes que producto inactivo, etc.). Una
    marca cuya columna no está en `d` no filtra, y una celda vacía tampoco:
    sin dato no hay motivo para sacar la fila. Pura, sin Streamlit."""
    motivo = pd.Series("", index=d.index, dtype=object)
    for col, ok, por_que in INVENTARIO_ACTIVO:
        c = _resolver(d, [col])
        if not c:
            continue
        # `fillna` antes del `astype`: con pandas 3 un vacío sigue vacío
        # después de `astype(str)` y no llega a ser «None» (Cloud corre 2.2).
        s = d[c].fillna("").astype(str).str.strip().str.upper()
        falla = ~s.isin(("", "NAN", "NONE", "<NA>", "NULL")) & (s != ok)
        motivo = motivo.mask((motivo == "") & falla, por_que)
    fuera = motivo != ""
    return d[~fuera], d[fuera].assign(**{COL_MOTIVO: motivo[fuera]})

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

# «Inactivos y servicios» (regla #598): una fila más debajo del TOTAL del
# ranking, no un botón suelto — se lee como la tabla de arriba y se abre como
# un área. La key lleva el estado (`_on`/`_off`) porque el CSS no puede
# preguntarle a un botón si está «elegido».
CSS_EXCLUIDOS = f"""
<style>
div[class*="st-key-inv_excl_btn_"] {{ margin-top: -6px; }}
div[class*="st-key-inv_excl_btn_"] button {{
    width: 100%; justify-content: flex-start; min-height: 26px;
    padding: 2px 10px; border-radius: 0 0 6px 6px;
    background: {LAVANDA_FILA}; color: {ACENTO_TEXTO}; }}
div[class*="st-key-inv_excl_btn_"] button p {{ font-size: 12px; }}
div[class*="st-key-inv_excl_btn_"][class*="_on"] button {{
    background: {LAVANDA_CABECERA_GRUPO}; color: {ACENTO_TEXTO_OSCURO}; }}
div[class*="st-key-inv_excl_btn_"][class*="_on"] button p {{
    font-weight: 600; }}
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

# «Todas las áreas» (regla #638): la PRIMERA fila del ranking de áreas, que se
# elige como cualquier área y deja las otras dos tarjetas con el restaurante
# entero —lo que era Stock por Familia—. Su clave no es un nombre del ERP:
# `_filtrar_ruta` la salta, así que no recorta nada.
TODAS = "__todas__"
ROTULO_TODAS = "Todas las áreas"


def _filtrar_ruta(d, ruta):
    """`d` recortado por los tríos (columna, valor crudo, texto) de `ruta`.
    «Todas las áreas» y un eslabón sin elegir no recortan."""
    for _col_r, _val_r, _ in ruta:
        if _col_r and _val_r and _val_r != TODAS:
            d = d[d[_col_r].astype(str) == _val_r]
    return d

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
# pantalla—. El bug del eje corrido que ataja `COLUMNAS_DRILL` en Compras es
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

# Qué categorías se ESCRIBEN como nombre propio en vez de como las grita el
# ERP (2026-09-13, a pedido: "que las letras en el cuadro de familia y
# subfamilia sean nombre propio"). Son las frases largas —"BEBIDAS CON
# ALCOHOL", "GASTOS ADMINISTRATIVOS"— donde ocho filas de mayúsculas se leen
# como un bloque; el área queda gritada porque son nombres cortos de almacén
# ("GASTOS", "SALON", "CAVA") y ahí el grito no molesta.
#
# Se decide por el NOMBRE de la categoría y no por la posición del cuadro: en
# "Por área" la familia es el segundo cuadro y en "Por familia" es el primero,
# así que atarlo a "el cuadro 2" la dejaría gritada en una de las dos vistas.
_CATEGORIAS_NOMBRE_PROPIO = ("familia", "subfamilia")


def _texto_cat(nombre_cat, valor):
    """Cómo se ESCRIBE `valor` cuando es de la categoría `nombre_cat`.

    El valor crudo no se toca nunca: es la clave con la que se filtra el df
    (ver el docstring de `nombre_propio`, que explica la misma separación
    del lado de Compras). Esto es sólo para mostrar."""
    if not valor or nombre_cat not in _CATEGORIAS_NOMBRE_PROPIO:
        return valor
    return nombre_propio(valor)


# Cuántas filas RESERVA una tabla-ranking antes de scrollear por dentro. El
# 8 es el techo de Compras (`proveedor.py::_FILAS_RANK`) y viaja con el
# resto del look: dos tablas con el mismo tema y el mismo alto de fila pero
# distinta cantidad de filas a la vista no se leen como la misma tabla.
_FILAS_RANK = 8


# Rail vertical fijo al borde DERECHO (componente compartido _render_rail,
# ver graficos/base.py).
# El elemento 0 de cada tupla (`oid`) es la IDENTIDAD interna de la vista:
# el valor que se persiste en `inv_graf_tipo`, el slug de la key del botón,
# el `id_vista` con que la aparea `_PILA`, y el deep-link `?vista=`. El
# elemento 1 es lo único que ve el usuario. Por eso el rótulo se reescribió
# a "Stock por …" (a pedido, 2026-09-21) SIN tocar el `oid` — cambiarlo
# habría roto el apareo con `_PILA` y los enlaces guardados. La pestaña de
# la franja lleva otro, más corto (`navegacion.py::ROTULO_PESTANA`, regla
# #708), también colgado del `oid`.
#
# La «Tabla» está OCULTA desde el 2026-09-23, con las de los demás reportes:
# `rail_sin_tablas` acá y `pila_sin_tablas` en `_PILA`, de a par (#507).
_INVENTARIO_RAIL_CATEGORIAS = rail_sin_tablas((
    # «Stock por Familia» se fue el 2026-10-11 (regla #638): es la fila
    # «Todas las áreas» de esta vista. Un `?vista=por_familia` guardado cae
    # en la primera vista, como cualquier id que ya no existe.
    #
    # «Stock por Producto» y «Stock por Área y Familia» son UNA vista desde
    # el 2026-10-23 (regla #712): «Stock», con dos perspectivas
    # (`PERSPECTIVAS_STOCK`), que dibujan cada una la vista de siempre. Etapa
    # 5 de la navegación del boceto del rail compacto (#708). Un
    # `?vista=productos` o `?vista=por_area` guardado cae en «Stock».
    ("Vista", (("Stock",       "Stock", ":material/inventory_2:"),
               ("Movimientos", "Movimientos por Tipo",
                ":material/waterfall_chart:"))),
    ("Datos", (("Tabla", "Tabla", ":material/table_rows:"),)),
))

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué, largo, está en `graficos/compras/__init__.py::_PILA`).
# Las cuatro vistas de Inventario comparten el mismo rango de fecha, así
# que a diferencia de Ajuste acá va UNA sola pila con todo adentro.
#
# LAS PERSPECTIVAS DE «Stock» (regla #712): (perspectiva, sección, id de la
# vista que era, su rótulo). Las secciones siguen siendo las de siempre —su
# dibujante, su estado—; la de la pila es `inv_sec_persp_stock`, y el
# `_sec_persp_` le hace ceder a su tarjeta el alto de la franja.
K_PERSP_STOCK = "_inv_persp_stock"
PERSPECTIVAS_STOCK = (
    ("Por producto", "inv_sec_productos", "Productos", "Stock por Producto"),
    ("Por área y familia", "inv_sec_area", "Por área", "Stock por Área y Familia"),
)
EJES_STOCK = ((K_PERSP_STOCK, "Ver", tuple(p[0] for p in PERSPECTIVAS_STOCK)),)
_PILA = pila_sin_tablas((
    ("inv_sec_persp_stock", "Stock"),
    # Por qué cambió el stock entre dos fechas, del kardex (regla #602).
    ("inv_sec_movimientos", "Movimientos"),
    ("inv_sec_tabla",   "Tabla"),
))


def _tabla_ranking(d, col_grp, col_val, nombre_grp, key, *,
                   ancho_pct=80, flex_nombre=2, ancho_barra=0.62,
                   monto_corto=False, nombre_bonito=False, abre_en=(),
                   abrir_en_mayor=False, filas_vista=None, historia=None,
                   meses=None, fila_todas=False):
    """Ranking de Por area/Por familia como TABLA con barra de progreso.

    Es la tabla-ranking del repo, la misma que el Ranking de proveedores de
    Compras: `CSS_RANKING_GRID` sobre `theme="streamlit"` (franja en vez de
    caja, todo blanco, sin lineas verticales, cuerpo de 11.5px), filas de
    `ALTO_FILA_RANK`, ocho a la vista y el resto por scroll interno, y una
    fila TOTAL fija abajo.

    `historia` (regla #638): lo que valía cada fila de `d` después de cada
    cierre (un DataFrame con el índice de `d`); con ella cada categoría lleva
    su mini-línea de 12 meses —la de Stock por Producto, sin ficha—, y
    `meses` son sus rótulos. `fila_todas` pone arriba «Todas las áreas», que
    se elige como una fila más (devuelve `TODAS`) y reemplaza a la fila
    TOTAL: las dos dirían el mismo número. La barra NO es un `cellRenderer` (ni la clase
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

    # % sobre lo que tiene stock POSITIVO, y una fila negativa no lleva %
    # (2026-10-03, regla #598). Hasta ese día era sobre el total NETO, que
    # suma 100 con la fila TOTAL mientras no haya negativos; con CALIENTES
    # en −S/ 38.161 el neto bajaba a S/ 18.513 y el Almacén Central salía
    # con 166 %. Sin negativos da lo mismo que antes.
    total = float(serie.sum())
    _positivo = float(serie[serie > 0].sum())
    _hay_neg = bool((serie < 0).any())
    _mayor = float(np.abs(serie.values).max()) or 1.0
    col_nombre = nombre_grp.capitalize()
    _pcts = [(v / _positivo * 100) if (_positivo and v >= 0) else None
             for v in serie.values]
    _crudos = [str(i) for i in serie.index]
    tabla = pd.DataFrame({
        # Lo que se VE puede ir en capitalización de nombre propio; lo que
        # se COMPARA es `_crudo`, unas líneas más abajo. Misma separación que
        # el Ranking de proveedores con su `_prov_raw`: el texto formateado
        # ya no matchea contra el parquet, así que usarlo para filtrar
        # devolvería un df vacío sin decir por qué.
        col_nombre: ([nombre_propio(x) for x in _crudos] if nombre_bonito
                     else _crudos),
        "Valorizado": serie.values,
        "%": _pcts,
        "_crudo": _crudos,
        # Ocultas: el % de LLENADO de la barra (contra la mayor MAGNITUD,
        # que no es el mismo numero que la columna "%"), y el signo, que se
        # lee por color y no por direccion, igual que en los graficos de
        # este dashboard (regla #80). La columna visible mantiene el valor
        # con signo; sin `_neg`, un ajuste negativo pintaria una barra larga
        # indistinguible de una compra grande.
        "_barra": [abs(v) / _mayor * 100 for v in serie.values],
        "_neg": [bool(v < 0) for v in serie.values],
        "_todas": False,
    })
    _sp_total = ""
    if historia is not None:
        _h = historia.loc[d.index].groupby(d[col_grp].astype(str)).sum()

        def _txt(fila):
            return ",".join(str(int(round(float(x)))) for x in fila)
        tabla["__sp"] = [_txt(_h.loc[k]) if k in _h.index else ""
                         for k in _crudos]
        _sp_total = _txt(historia.loc[d.index].sum())
    if fila_todas:
        tabla = pd.concat([pd.DataFrame([{
            col_nombre: ROTULO_TODAS, "Valorizado": total,
            "%": 100.0 if (_positivo and not _hay_neg) else None,
            "_crudo": TODAS, "_barra": 0.0, "_neg": False, "_todas": True,
            **({"__sp": _sp_total} if historia is not None else {}),
        }]), tabla], ignore_index=True)
    # La fila TOTAL reemplaza al KPI "Valorizado total" que vivia arriba de
    # esta tabla (pedido del 2026-09-13: "quitar el KPI"). Mismo mecanismo
    # que el Ranking de proveedores: un dict calculado en PYTHON +
    # `pinnedBottomRowData`, no el `"grandTotalRow"` nativo, que en este
    # repo solo esta probado junto a `pivotMode=True` y esta tabla es plana.
    # Suma lo que la tabla MUESTRA, que aca es todo el recorte.
    # "TOTAL" no pasa por `nombre_propio` —quedaría "Total"— porque no es
    # un nombre del ERP sino el rótulo de la fila de cierre.
    # El 100 % sólo cuando el TOTAL es la suma de lo que tiene %: con
    # negativos el TOTAL es menor, y un «100 %» al lado mentiría.
    fila_total = {col_nombre: "TOTAL", "Valorizado": round(total, 2),
                  "%": 100.0 if (_positivo and not _hay_neg) else None}

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
        " if (p.node.rowPinned || (p.data && p.data._todas))"
        " return {'display':'flex',"
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
        "}; }"
        # «Todas las áreas»: con el peso del total, pero se elige.
        " if (p.data && p.data._todas) return {'fontWeight':'600',"
        f"'background':'{LAVANDA_FILA}','color':'{ACENTO_TEXTO_OSCURO}'"
        "}; }")
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
    # `filas_vista`: una menos en «Valorizado por área», que paga así el
    # alto de la fila «Inactivos y servicios» de debajo (regla #598).
    _filas = min(filas_vista or _FILAS_RANK, max(1, len(serie)))
    _alto = alturas.por_filas(_filas, px_fila=ALTO_FILA_RANK,
                              extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                              minimo=0)
    # El alto, ATADO desde el documento padre. Medido el 2026-09-13 en
    # «Valorizado por área»: atributo 255 (8 filas), `style height` INLINE
    # de 508, tarjeta de 554 contra los 308 de sus dos vecinas — el pedido
    # fue "veo que es más larga verticalmente".
    #
    # CORREGIDO el 2026-09-17: ese inline NO lo reportaba st_aggrid (así
    # decía este comentario). Lo escribía `inject_dynamic_grid_height` de la
    # tabla de detalle, que estiraba "el primer AgGrid de la página" —éste—
    # a `innerHeight - 260`. Ya busca su tabla por key (regla #455); lo de
    # abajo queda de red, y lo que dice de las dos capas sigue valiendo
    # para quien escriba un `style` inline sobre un componente.
    #
    # Son dos capas: `CSS_RANKING_GRID` le pone `height: 100%` +
    # `max-height: 100%` al `.ag-root-wrapper`, que es lo que mantiene la
    # GRILLA en su alto aunque el iframe crezca, y esta regla ata el IFRAME.
    # Sin guard de "una sola vez": un `st.markdown` de estilos con ese guard
    # desaparece en el rerun siguiente (regla #59). Los DOS nodos, no sólo
    # el iframe: el inline se escribía sobre el `stElementContainer` que lo
    # envuelve Y sobre el iframe. Atando sólo el de adentro, el de afuera se
    # quedaba con los 508 y la tarjeta seguía midiendo igual — medido, con
    # el iframe ya en 255 el contenedor seguía en 508.
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
                {"field": "Valorizado", "flex": 2, "type": "numericColumn",
                 "cellStyle": _js_barra, "valueFormatter": _js_soles},
                {"field": "%", "width": ancho_pct, "type": "numericColumn",
                 "valueFormatter": _js_pct},
            ] + ([{"field": "__sp", "headerName": "12 meses", "width": 72,
                   "minWidth": 72, "maxWidth": 72, "sortable": False,
                   "cellRenderer": _js_fijo(_JS_MINI_LINEA),
                   "cellRendererParams": {"sinFicha": True, "ancho": 62},
                   "headerTooltip": "Lo que valió después de cada cierre (el "
                                    "día 7 del mes siguiente) y hoy."}]
                 if historia is not None else []) + [
                {"field": "_barra", "hide": True},
                {"field": "_neg", "hide": True},
                {"field": "_todas", "hide": True},
                {"field": "_crudo", "hide": True},
            ],
            "context": {"meses": list(meses or [])},
            "rowSelection": {"mode": "singleRow", "checkboxes": False,
                             "enableClickSelection": False},
            "onRowClicked": _js_toggle,
            "rowHeight": ALTO_FILA_RANK,
            "headerHeight": ALTO_HEADER_RANK,
            "suppressCellFocus": True,
            "suppressMovableColumns": True,
            "pinnedBottomRowData": [] if fila_todas else [fila_total],
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
    # nombre viaja escrito a mano en `ABRE_EN_AREA` y el ERP los manda
    # gritados y con espacios de sobra.
    _norm = {str(i).strip().upper(): str(i) for i in serie.index}
    for _cand in abre_en:
        _hit = _norm.get(str(_cand).strip().upper())
        if _hit is not None:
            return _hit
    return str(serie.index[0])


def _tabla_detalle_foco(d, col_next, nombre_next, col_val, key, ruta=(),
                        formato=None, historia=None, meses=None):
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

    `ruta` es el recorte que ya está aplicado, en tríos (columna, valor
    crudo, texto): el valor FILTRA el df y el texto arma el título. Van los
    dos porque desde el 2026-09-13 no son lo mismo — familia y subfamilia se
    escriben en capitalización de nombre propio y esa forma ya no matchea
    contra el parquet. Se recibe hecha en vez de recalcularse acá porque el
    caller la va acumulando nivel a nivel — con dos eslabones ya no alcanza
    un `col_grp`/`foco` sueltos, y tres argumentos paralelos por nivel es lo
    que convierte una cadena en un `if` por profundidad.

    La `key` que le pasa el caller lleva el foco adentro a propósito: al
    cambiar de área, la grilla es OTRA y nace sin selección. Con AgGrid eso
    es correcto —la selección es estado que se relee en cada run, no el
    evento que se repite de `plotly_chart(on_select=...)` (regla #399)—, y es
    lo que evita que un sub-foco sobreviva al área que lo justificaba."""
    dd = _filtrar_ruta(d, ruta)
    # El titulo nombra sólo el ÚLTIMO eslabón, no la ruta entera: con tres
    # cuadros "ALMACEN CENTRAL › COSTOS PRODUCCION — por subfamilia" no entra
    # en 339px, y de qué área viene ya lo dice el cuadro de la izquierda. La
    # ruta completa va al `title=`, que es donde se la puede leer sin que
    # empuje el layout.
    _ruta_txt = " › ".join(str(t) for _, v, t in ruta if v)
    _de = next((str(t) for _, v, t in reversed(list(ruta)) if v), "")
    if not col_next or dd.empty:
        st.caption(f"Sin desglose adicional para {_de}." if _de
                   else "Sin desglose adicional.")
        return None
    st.markdown(
        f'<div class="inv-rank-tit" title="{_ruta_txt.replace(chr(34), "")}">'
        f'{_de} — por {nombre_next}</div>', unsafe_allow_html=True)
    return _tabla_ranking(
        dd, col_next, col_val, nombre_next, key,
        nombre_bonito=nombre_next in _CATEGORIAS_NOMBRE_PROPIO,
        historia=historia, meses=meses, filas_vista=_FILAS_RANK - 1,
        **(formato or _FORMATO_DETALLE[2]))


def _panel_top(d, ruta, col_prod, col_area, col_val, col_punit, _cant,
               col_unidad=None, col_motivo=None):
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

    `ruta` son los tríos (columna, valor crudo, texto) de la cadena de
    arriba —área, familia, subfamilia— hasta donde el usuario haya
    clickeado: el valor filtra, el texto se escribe. El % de
    participación se recalcula sobre ESE recorte, no sobre el área entera,
    porque el criterio de la tarjeta es "sumar 100% con lo que el usuario ya
    está viendo arriba".

    La columna "UM" (2026-09-13, a pedido) escribe la `Unidad Kardex` del
    producto con `unidad_corta` —el mismo mapa que rotula las cantidades de
    Compras, no una copia— y va pegada a "Cantidad", que es el número al que
    le da sentido: 34 de qué. El TOTAL la deja vacía: sumar kg con L no da
    una unidad.

    Desde el 2026-10-11 (regla #638) se dibuja SÓLO con «Inactivos y
    servicios», que no tiene otra vista donde verse: la tabla de productos
    del stock es la de Stock por Producto. Y sin las casillas ni «Selección
    %»: calculaba un % también en las filas no marcadas (108,2 %) y en el
    TOTAL (1.188,2 %), cada casilla iba al servidor y la suma de lo marcado
    no se veía en ningún lado.

    `col_motivo` (regla #598): con «Inactivos y servicios» abierto, la tabla
    lista lo que NO es stock y suma una columna «Por qué» — el motivo es de
    la fila (producto × área), así que va junto al área."""
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

    d_panel = _filtrar_ruta(d, ruta)
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
        "Por qué": (d_panel[col_motivo].astype(str).values if col_motivo
                    else ""),
    })
    # `first` para la UM y no una agregación: es un atributo del producto,
    # no una medida. Va dentro del `agg` y no como cuarta clave del groupby
    # a propósito — si un producto llegara con dos unidades distintas, una
    # clave más lo partiría en dos filas que suman mal; así se queda en una
    # y a lo sumo rotula con la primera.
    g = (base.groupby(["Producto", "Área"], as_index=False)
         .agg(Cantidad=("Cantidad", "sum"), Valorizado=("Valorizado", "sum"),
              UM=("UM", "first"), **{"Por qué": ("Por qué", "first")},
              **{"Precio unitario": ("Precio unitario", "mean")}))
    if g.empty:
        st.info("Sin datos.")
        return

    # Participación % contra el total del FOCO (no solo el top mostrado) —
    # mismo criterio que el % de las barras de _grafico_ranking: sobre el
    # total neto que el usuario ya ve arriba, no sobre una suma parcial.
    #
    # Sobre lo POSITIVO, como los rankings de arriba (regla #598): con
    # negativos en el recorte —«Inactivos y servicios», CALIENTES— el neto
    # dejaba a «Compras Mantenimiento Varios» en 103 %. Una fila negativa
    # no lleva participación.
    _total_foco = float(_val_panel[_val_panel > 0].sum())
    _hay_neg_panel = bool((_val_panel < 0).any())
    g["Participación %"] = ((g["Valorizado"] / _total_foco * 100)
                            .where(g["Valorizado"] >= 0)
                            if _total_foco else 0.0)
    g = g.sort_values("Valorizado", ascending=False)

    # El encabezado dice el recorte Y cuántas filas trae: sin el número, una
    # tabla que scrollea no deja ver si son 12 productos o 400.
    _ruta = " › ".join([str(t) for _, v, t in ruta if v])
    st.markdown(
        '<div class="inv-rank-tit">Productos'
        + (f" · {_ruta}" if _ruta else "")
        + f' <span class="inv-rank-tit-n">{len(g):,}</span></div>',
        unsafe_allow_html=True)

    # Fila TOTAL, igual que las otras dos tablas de la sección. "Precio
    # unitario" queda VACÍA a propósito: es un ratio y un ratio no se suma ni
    # se promedia sobre el agregado (la misma trampa que la regla #199).
    _fila_total = {
        "Producto": "TOTAL",
        "Área": "",
        "Por qué": "",
        "UM": "",
        # Sin Cantidad: sumar kilos con litros no da una unidad (regla #638;
        # hasta ese día decía 7.576).
        "Valorizado": round(float(g["Valorizado"].sum()), 2),
        "Participación %": (None if _hay_neg_panel else
                            round(float(g["Participación %"].sum()), 1)),
    }

    gb = GridOptionsBuilder.from_dataframe(
        g[["Producto", "Área", "Por qué", "Cantidad", "UM", "Precio unitario",
           "Valorizado", "Participación %"]])
    gb.configure_column("Por qué", minWidth=150, hide=not col_motivo)
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    # minWidths ajustados para que las 7 entren sin scroll horizontal en la
    # franja de abajo (~911-1117px medido en vivo): con los anchos "cómodos"
    # originales (170+110+100+120+120+140+140=900px de columnas centrales)
    # quedaban ~19px cortos contra el ancho disponible real y la última
    # columna quedaba virtualizada fuera de vista (ni scrolleable a simple
    # vista: parecía que no existía).
    gb.configure_column("Producto", pinned="left", minWidth=150)
    # El ÁREA se esconde cuando la cadena de arriba ya la fijó: con el foco
    # por defecto en ALMACEN CENTRAL, esa columna escribe la misma palabra
    # en las 3.865 filas y el dato ya está en el título de la tarjeta — el
    # caso exacto de la regla #239. Oculta y no borrada: sigue en el modelo
    # por si hace falta ordenar por ella, y son los 90px que necesitaba la
    # UM para entrar sin empujar la tabla a scroll horizontal.
    _area_fija = any(c == col_area and v for c, v, _t in ruta)
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

    # Misma barra-gradiente que tablas/desktop.py::_pct_bar_style; el "–"
    # con value null es el de una fila negativa, que no lleva participación.
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
    grid_options = gb.build()
    # Sin esto, la última columna quedaba virtualizada
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
    # La fila TOTAL con la paleta de cierre de las otras dos.
    grid_options["getRowStyle"] = JsCode(
        "function(p){ if(p.node.rowPinned){ return {"
        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
        f"'color':'{ACENTO_TEXTO_OSCURO}'"
        "}; } }")

    AgGrid(
        g, gridOptions=grid_options, theme="streamlit",
        # Seis filas reservadas y el resto por scroll interno, la misma
        # cuenta que `_tabla_ranking` (ver el comentario de `extra` allá).
        # Seis y no ocho desde la regla #638: con ocho, en «Inactivos y
        # servicios» la tabla salía por debajo de la pantalla del usuario.
        height=alturas.por_filas(min(_FILAS_RANK - 2, max(1, len(g))),
                                 px_fila=ALTO_FILA_RANK,
                                 extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                                 minimo=0),
        custom_css=CSS_RANKING_GRID,
        allow_unsafe_jscode=True,
        # Nada vuelve a Python: sin esto, el default de st_aggrid avisaba
        # al servidor cada orden y cada casilla (regla #638).
        update_on=[],
        # La key lleva el recorte entero: cambiar de recorte estrena grilla.
        key="inv_top_grid_" + (_slug("_".join(str(v) for _, v, _ in ruta if v))
                               or "global"),
    )


# ── Debajo de los rankings: qué más cambió y dónde mirar (regla #638) ─────
# Los rankings dicen cuánto hay y las mini-líneas si sube o baja; esto dice
# QUÉ productos explican el cambio y QUÉ conviene revisar, del recorte que
# esté elegido, y lleva a Stock por Producto con ese filtro puesto.
_K_IR = "inv_ir_productos"
_K_SALTAR = "inv_saltar_a_productos"
_MOVIDOS = 7

CSS_BANDA_AREA = f"""
<style>
.inv-mov-t {{ font-size: 12px; color: {GRIS_TEXTO}; margin-bottom: 2px; }}
.inv-mov-t b {{ color: {TEXTO_PRINCIPAL}; font-weight: 600; }}
.inv-mov {{ display: grid; grid-template-columns: minmax(0, 1fr) 40% 92px;
    align-items: center; gap: 10px; height: 21px; font-size: 12px; }}
.inv-mov .n {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    color: {ACENTO_TEXTO}; }}
.inv-mov .n small {{ color: {GRIS_TEXTO}; margin-left: 5px; }}
.inv-mov .pista {{ position: relative; height: 12px; }}
.inv-mov .pista::before {{ content: ""; position: absolute; left: 50%; top: -3px;
    bottom: -3px; border-left: 1px solid {GRIS_BORDE}; }}
.inv-mov .pista i {{ position: absolute; top: 1px; bottom: 1px; background: {ACENTO}; }}
.inv-mov .pista i.baja {{ background: {AJUSTE_NEG}; }}
.inv-mov .d {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }}
.inv-mov .d.baja {{ color: {AJUSTE_NEG_TEXTO}; }}
/* El `padding-bottom` paga el −16px del `st.markdown` (regla #162): sin él,
   este renglón quedaba fuera de la tarjeta cuando la columna de la izquierda
   es la más alta. */
.inv-mov-pie {{ font-size: 11.5px; color: {GRIS_TEXTO}; margin-top: 2px;
    padding-bottom: 14px; }}
.inv-tile .l {{ display: block; font-size: 11px; color: {GRIS_TEXTO}; }}
.inv-tile .v {{ display: block; font-size: 17px; font-weight: 600;
    font-variant-numeric: tabular-nums; color: {TEXTO_PRINCIPAL}; line-height: 1.25; }}
.inv-tile .v.neg {{ color: {AJUSTE_NEG_TEXTO}; }}
.inv-tile .v.alerta {{ color: {AJUSTE_ALERTA_TEXTO}; }}
.inv-tile .s {{ display: block; font-size: 11.5px; color: {GRIS_TEXTO_MEDIO}; }}
/* El de los días no lleva botón debajo: sin este aire, su último renglón
   pisaba el borde (el −16px del `st.markdown`, regla #162). */
.st-key-inv_donde_dias .inv-tile {{ padding-bottom: 8px; }}
.st-key-inv_donde_dias, .st-key-inv_donde_neg, .st-key-inv_donde_sin,
.st-key-inv_donde_alto {{ padding: 6px 10px !important; gap: 0 !important; }}
/* «Ver ↑» a la DERECHA de la última línea del recuadro, la del monto: un
   renglón propio hacía medir la sección 591px de los 575 de la pantalla. Esa
   línea sólo lleva montos cortos («S/ 2,851»), así que no se pisan. */
.st-key-inv_donde_btn_neg, .st-key-inv_donde_btn_sin,
.st-key-inv_donde_btn_alto {{ align-self: flex-end !important; width: auto !important;
    margin-top: -20px !important; }}
.st-key-inv_donde_btn_neg button, .st-key-inv_donde_btn_sin button,
.st-key-inv_donde_btn_alto button {{ min-height: 0 !important; padding: 0 2px !important;
    height: 18px; }}
.st-key-inv_donde_btn_neg button p, .st-key-inv_donde_btn_sin button p,
.st-key-inv_donde_btn_alto button p {{ font-size: 11.5px !important; }}
</style>
"""


def _ir_a_productos(areas, familias, subfamilias, chip):
    """Deja Stock por Producto con este recorte y este chip, sin buscador ni
    fecha, y pide el salto. Es un `on_click`: corre antes de la corrida del
    fragment, y al final de la sección `_K_IR` escala a una corrida completa
    —la vista 1 es OTRO fragment— cuando sus widgets ya se registraron
    (regla #373)."""
    poner_seleccion(_K_AREAS, areas)
    poner_seleccion(_K_FAMILIAS, familias)
    poner_seleccion(_K_SUBFAMILIAS, subfamilias)
    st.session_state[_K_ESTADO] = chip
    st.session_state[_K_BUSCAR] = ""
    st.session_state[_K_A_FECHA] = False
    st.session_state[_K_IR] = True
    st.session_state[_K_SALTAR] = True
    st.session_state["_inv_stock_salto"] = st.session_state.get("_inv_stock_salto", 0) + 1
    # Las dos son perspectivas de «Stock» desde la regla #712: el salto es
    # cambiar a la de productos (y llevar la página al tope de la vista).
    st.session_state[K_PERSP_STOCK] = PERSPECTIVAS_STOCK[0][0]


def _soles(v):
    return ("−" if v < 0 else "") + f"S/ {abs(v):,.0f}"


def _banda_area(d, ruta, historia, meses, consumo, cols, slug):
    """La tarjeta de abajo de Stock por Área y Familia: el recorte de `ruta`
    —área (o todas), familia, subfamilia—, lo que más cambió en él desde un
    cierre y los cuatro recuadros de «Dónde mirar»."""
    d_rec = _filtrar_ruta(d, ruta)
    sel = {c: str(v).strip() for c, v, _ in ruta if c and v and v != TODAS}
    areas = [sel[cols["area"]]] if cols["area"] in sel else []
    familias = [sel[cols["fam"]]] if cols["fam"] in sel else []
    subfamilias = [sel[cols["subfam"]]] if cols["subfam"] in sel else []
    nombre = " › ".join(str(t) for _, v, t in ruta if v)
    listado = armar_listado(
        d, col_cod=cols["cod"], col_prod=cols["prod"], col_fam=cols["fam"],
        col_subfam=cols["subfam"], col_area=cols["area"],
        col_unidad=cols["unidad"], col_punit=cols["punit"],
        col_cant=cols["cant"], col_val=cols["val"], areas=areas,
        familias=familias, subfamilias=subfamilias,
        col_cod_area=cols["cod_area"], consumo=consumo)
    p = listado.productos
    with st.container(border=True, key=f"ajuste_graf_card_abajo_inv_{slug}"):
        # columnas-internas: el nombre del recorte, desde qué cierre se
        # compara y el botón a Stock por Producto, en la cabecera.
        c_t, c_r, c_b = st.columns([3.2, 2.6, 1.6], vertical_alignment="center")
        with c_t:
            st.markdown(
                f'<div class="inv-rank-tit" style="margin:0">{nombre}'
                f'<span class="inv-rank-tit-n">{len(p):,} productos con stock'
                '</span></div>', unsafe_allow_html=True)
        _k_ref = f"inv_desde_{slug}"
        _ops = [len(meses) - 3, 0] if meses and len(meses) > 3 else [0]
        if st.session_state.get(_k_ref) not in _ops:
            st.session_state[_k_ref] = _ops[0]
        with c_r:
            ref = st.segmented_control(
                "Comparar con", _ops, key=_k_ref, label_visibility="collapsed",
                format_func=lambda i: (f"desde el cierre de {meses[i]}"
                                       if i == _ops[0]
                                       else f"desde el de {meses[i]}")
            ) if meses else None
        with c_b:
            st.button(f"Ver sus {len(p):,} productos ↑", key=f"inv_ir_{slug}",
                      type="primary", width="stretch", on_click=_ir_a_productos,
                      args=(areas, familias, subfamilias, "todos"))
        # columnas-internas: lo que más cambió y dónde mirar, lado a lado.
        c_m, c_d = st.columns([1.55, 1], gap="medium")
        with c_m:
            _lo_que_cambio(d_rec, historia, meses, ref if ref is not None else _ops[0],
                           cols)
        with c_d:
            _donde_mirar(p, areas, familias, subfamilias)


def _lo_que_cambio(d_rec, historia, meses, ref, cols):
    """Los productos del recorte que más subieron o bajaron desde el cierre
    `ref`, incluidos los que se vaciaron, y cuánto explican del total."""
    if historia is None or not meses or d_rec.empty:
        st.caption("Sin historia del kardex: falta la consulta «kardex».")
        return
    cod = d_rec[cols["cod"]].astype(str).str.strip()
    por_prod = historia.loc[d_rec.index].groupby(cod).sum()
    top, total, cambiaron = analisis_stock.lo_que_mas_cambio(por_prod, ref,
                                                             _MOVIDOS)
    nombres = d_rec[cols["prod"]].astype(str).groupby(cod).first()
    hoy_val = (pd.to_numeric(d_rec[cols["val"]], errors="coerce").fillna(0)
               .abs().groupby(cod).sum())
    filas = []
    mayor = float(top.abs().max()) if len(top) else 1.0
    for c, delta in top.items():
        baja = delta < 0
        ancho = abs(delta) / mayor * 50
        vacio = hoy_val.get(c, 0) < 0.5
        antes, ahora = float(por_prod.loc[c].iloc[ref]), float(por_prod.loc[c].iloc[-1])
        filas.append(
            f'<div class="inv-mov" title="{_soles(antes)} → {_soles(ahora)}">'
            f'<span class="n">{nombres.get(c, c)}'
            + ("<small>se vació</small>" if vacio else "") + "</span>"
            f'<span class="pista"><i class="{"baja" if baja else ""}" style="'
            f'{"right" if baja else "left"}:50%;width:{ancho:.1f}%"></i></span>'
            f'<span class="d{" baja" if baja else ""}">{"−" if baja else "+"}'
            f'{_soles(abs(delta))}</span></div>')
    explican = float(top.sum())
    resto = cambiaron - len(top)
    pie = (f"Estos {len(top)} explican {'−' if explican < 0 else '+'}"
           f"{_soles(abs(explican))}"
           + (f"; los otros {resto:,} que cambiaron, "
              f"{'−' if total - explican < 0 else '+'}{_soles(abs(total - explican))}."
              if resto > 0 else ".")) if len(top) else "Nada cambió en este recorte."
    st.markdown(
        f'<div class="inv-mov-t"><b>Qué más cambió</b> · '
        f'{"subió" if total >= 0 else "bajó"} {_soles(abs(total))} desde el '
        f'cierre de {meses[ref]}</div>' + "".join(filas)
        + f'<div class="inv-mov-pie">{pie}</div>', unsafe_allow_html=True)


def _donde_mirar(p, areas, familias, subfamilias):
    """Cuatro recuadros: los días de inventario del recorte y, para los
    negativos, lo que no se consumió y lo que sobra, cuántos son y cuánto
    valen, con un «Ver ↑» que lleva a Stock por Producto con ese chip."""
    st.markdown('<div class="inv-mov-t"><b>Dónde mirar</b></div>',
                unsafe_allow_html=True)
    e = p["estado"] if "estado" in p else pd.Series(dtype=object)
    dias = (analisis_stock.dias_del_conjunto(p["valorizado"], p["cantidad"],
                                             p["consumo"], p["precio"])
            if "consumo" in p else float("nan"))
    _v = analisis_stock.VENTANA_CONSUMO
    recuadros = [
        ("dias", "Días de inventario",
         "–" if dias != dias else ("más de 365" if dias > 365 else f"{dias:,.0f}"),
         f"al ritmo de consumo de {_v} días", ""),
    ]
    for k, rotulo, clase in (("neg", "Negativos", "neg"),
                             ("sin", f"Sin consumo {_v} días", "alerta"),
                             ("alto", f"Más de {analisis_stock.UMBRAL_DIAS} días",
                              "alerta")):
        m = e.eq(k)
        recuadros.append((k, rotulo, f"{int(m.sum()):,}",
                          _soles(float(p.loc[m, "valorizado"].sum())), clase))
    for fila in (recuadros[:2], recuadros[2:]):
        # columnas-internas: los recuadros de «Dónde mirar», de a dos.
        for col, (k, rotulo, valor, sub, clase) in zip(st.columns(2, gap="small"),
                                                       fila):
            with col, st.container(border=True, key=f"inv_donde_{k}"):
                st.markdown(
                    f'<div class="inv-tile"><span class="l">{rotulo}</span>'
                    f'<span class="v {clase}">{valor}</span>'
                    f'<span class="s">{sub}</span></div>',
                    unsafe_allow_html=True)
                if k != "dias":
                    st.button("Ver ↑", key=f"inv_donde_btn_{k}", type="tertiary",
                              disabled=valor == "0", on_click=_ir_a_productos,
                              args=(areas, familias, subfamilias, k))


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
    col_cod    = _resolver(df_f, ["Codigo Producto", "CODIGO PRODUCTO",
                                  "Cod Producto"])
    col_unidad = _resolver(df_f, ["Unidad Kardex", "UNIDAD KARDEX",
                                  "Unidad Medida", "Unidad"])
    # Con qué se parte la cantidad en la unidad de salida (regla #598).
    # UNIDAD SALIDA llegó con la consulta del Sheet del 2026-10-03; sin ella
    # el interruptor de Productos no se dibuja.
    col_factor = _resolver(df_f, ["FACTOR", "Factor"])
    col_usal   = _resolver(df_f, ["UNIDAD SALIDA", "Unidad Salida"])
    # El código del área es con lo que la tabla de Productos se cruza con el
    # kardex para ver el stock a una fecha (regla #601).
    col_cod_area = _resolver(df_f, ["CODIGO AREA", "Codigo Area"])

    if not col_val:
        st.warning("No se encontró la columna de valorizado. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # SÓLO LO ACTIVO es stock (regla #598): todo el reporte —los chips, las
    # cuatro secciones, la Tabla y el asistente— lee `df_f` ya sin lo
    # inactivo ni los servicios. Lo que queda fuera viaja aparte, para la
    # fila «Inactivos y servicios» de Por área. Va ANTES de los chips: un
    # área inactiva (CALIENTES) no se ofrece para filtrar.
    df_f, df_excl = separar_activos(df_f)

    # ── Filtros Área / Familia como chips en la FRANJA blanca ────────────
    area_sel, fam_sel = [], []
    with compartimento_filtros(contar_filtros("inv_graf_filtro_area",
                                              "inv_graf_filtro_fam")):
        _, area_sel = filtro_pills(df_f, col_area,
                                   "inv_graf_filtro_area", "Área")
        _, fam_sel = filtro_pills(df_f, col_fam,
                                  "inv_graf_filtro_fam", "Familia")

    d, d_excl = df_f, df_excl
    if area_sel and col_area:
        d = d[d[col_area].astype(str).isin(area_sel)]
        d_excl = d_excl[d_excl[col_area].astype(str).isin(area_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]
        d_excl = d_excl[d_excl[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Inventario Valorizado", d,
                         {"Área": area_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    _cant = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
             if col_cant else None)

    # «Ver sus productos» y «Dónde mirar» (regla #638) dejaron Stock por
    # Producto filtrado y pidieron esta corrida completa: ahora, el salto.
    if st.session_state.pop(_K_SALTAR, False):
        scroll_a_seccion("inv_sec_persp_stock")

    # La historia de cada fila de `d` después de cada cierre y el consumo del
    # restaurante (regla #638): las mini-líneas de los rankings y la tarjeta
    # de abajo. Sin kardex, los rankings van como antes.
    meses = hist_d = consumo = None
    _h = data.historia_stock() if (col_cod_area and col_cod) else None
    if _h is not None:
        meses, _momentos, _val = _h
        _claves = pd.MultiIndex.from_arrays([
            d[col_cod_area].astype(str).str.strip(),
            d[col_cod].astype(str).str.strip()])
        hist_d = pd.DataFrame(
            np.nan_to_num(_val.reindex(_claves).to_numpy(dtype=float)),
            index=d.index, columns=list(_val.columns))
        consumo = data.consumo_stock(_momentos[-1].date())

    # Sin guard de "inyectar una sola vez": un `st.markdown` de estilos con
    # ese guard DESAPARECE en el rerun siguiente (regla #59).
    st.markdown(CSS_TITULOS_INV + CSS_EXCLUIDOS + CSS_BANDA_AREA,
                unsafe_allow_html=True)

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
    def _seccion_grupo(slug, niveles, abre_en=(), excluidos=None):
        # (La historia, los meses y el consumo vienen de afuera: el fragment
        # se re-ejecuta con lo de la última corrida del dashboard.)
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
        franja ancha, que es donde entra.

        `excluidos` (regla #598, sólo Por área): lo que no es stock, con su
        `COL_MOTIVO`. Se ofrece como una fila más debajo del TOTAL del
        ranking —«Inactivos y servicios»— y elegirla hace con los otros tres
        cuadros lo mismo que un área: el segundo lo parte por motivo, el
        tercero por área y la tabla de abajo lista sus productos con el
        motivo al lado. Un clic en un área del ranking la suelta."""
        col_grp, nombre_grp = niveles[0]
        _k_excl = f"inv_excl_{slug}"
        _k_excl_foco = f"inv_excl_foco_{slug}"
        hay_excl = excluidos is not None and not excluidos.empty
        _bonito_grp = nombre_grp in _CATEGORIAS_NOMBRE_PROPIO
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
                    # Una fila menos que los desgloses de al lado: la
                    # paga «Inactivos y servicios», debajo (regla #145).
                    foco = _tabla_ranking(d, col_grp, col_val, nombre_grp,
                                          key=f"inv_rank_grid_{slug}",
                                          abre_en=abre_en,
                                          abrir_en_mayor=True,
                                          nombre_bonito=_bonito_grp,
                                          filas_vista=(_FILAS_RANK - 2
                                                       if hay_excl else
                                                       _FILAS_RANK - 1),
                                          historia=hist_d, meses=meses,
                                          fila_todas=True,
                                          **_FORMATO_RANKING[len(niveles)])
                    ruta.append((col_grp, foco,
                                 ROTULO_TODAS if foco == TODAS
                                 else _texto_cat(nombre_grp, foco)))
                    if hay_excl:
                        # Elegir un área del ranking suelta la fila de
                        # excluidos: el foco del ranking sólo cambia con un
                        # clic del usuario (la selección de AgGrid es estado
                        # que se relee, regla #399), así que comparar contra
                        # el de la corrida anterior es «hizo clic en un área».
                        if st.session_state.get(_k_excl_foco) != foco:
                            st.session_state[_k_excl] = False
                        st.session_state[_k_excl_foco] = foco
                        _on = bool(st.session_state.get(_k_excl))
                        _v = float(pd.to_numeric(excluidos[col_val],
                                                 errors="coerce").sum())
                        st.button(
                            f"{ETIQUETA_EXCLUIDOS} · "
                            f"{'−' if _v < 0 else ''}S/ {abs(_v):,.0f}"
                            f"{'  ✕' if _on else '  ›'}",
                            key=f"inv_excl_btn_{slug}_{'on' if _on else 'off'}",
                            type="tertiary", width="stretch",
                            help=("No suman al stock: artículos inactivos, "
                                  "servicios, artículos no habilitados en su "
                                  "área y áreas inactivas. Clic para verlos."),
                            on_click=lambda: st.session_state.update(
                                {_k_excl: not st.session_state.get(_k_excl)}))
        modo_excl = hay_excl and bool(st.session_state.get(_k_excl))
        d_drill, niveles_drill, col_motivo = d, niveles, None
        if modo_excl:
            # La ruta EMPIEZA en el grupo entero y no en un área: los dos
            # cuadros y la tabla de abajo lo leen como si fuera un foco más.
            # Sólo las filas con stock: de lo inactivo, lo que está en cero
            # no hay que corregirlo (medido el 2026-10-03: 201 filas con
            # stock de 7.955).
            _con = (pd.to_numeric(excluidos[col_cant], errors="coerce")
                    .fillna(0).ne(0) if col_cant
                    else pd.Series(True, index=excluidos.index))
            _con |= pd.to_numeric(excluidos[col_val], errors="coerce").fillna(0).ne(0)
            d_drill = (excluidos[_con]
                       .assign(**{_COL_GRUPO_EXCL: ETIQUETA_EXCLUIDOS}))
            niveles_drill = ((_COL_GRUPO_EXCL, ""), (COL_MOTIVO, "motivo"),
                             (col_area, "área"))
            ruta = [(_COL_GRUPO_EXCL, ETIQUETA_EXCLUIDOS, ETIQUETA_EXCLUIDOS)]
            col_motivo = COL_MOTIVO
        for _i, (_col_n, _nombre_n) in enumerate(niveles_drill[1:]):
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
                    if not [v for _, v, _t in ruta if v]:
                        st.caption("Elegí una fila del cuadro anterior.")
                        continue
                    # La key lleva la ruta adentro a propósito: al cambiar
                    # lo de arriba, la grilla es OTRA y nace sin selección
                    # (ver el docstring de `_tabla_detalle_foco`).
                    _k = _slug("_".join(str(v) for _, v, _t in ruta if v))
                    _sub = _tabla_detalle_foco(
                        d_drill, _col_n, _nombre_n, col_val,
                        key=f"inv_det_grid_{slug}_{_i}_{_k}", ruta=tuple(ruta),
                        formato=_FORMATO_DETALLE[len(niveles)],
                        historia=None if modo_excl else hist_d, meses=meses)
                    ruta.append((_col_n, _sub, _texto_cat(_nombre_n, _sub)))
        if modo_excl:
            # Lo que NO es stock no tiene otra vista donde verse: su lista
            # sigue acá, con el motivo (regla #598).
            with st.container(border=True,
                              key=f"ajuste_graf_card_abajo_inv_{slug}"):
                _panel_top(d_drill, tuple(ruta), col_prod, col_area, col_val,
                           col_punit,
                           (pd.to_numeric(d_drill[col_cant], errors="coerce")
                            .fillna(0) if col_cant else None),
                           col_unidad=col_unidad, col_motivo=col_motivo)
        else:
            _banda_area(d, tuple(ruta), hist_d, meses, consumo, dict(
                area=col_area, fam=col_fam, subfam=col_subfam, cod=col_cod,
                prod=col_prod, unidad=col_unidad, punit=col_punit,
                cant=col_cant, val=col_val, cod_area=col_cod_area), slug)
        # Un «Ver ↑» o «Ver sus productos» pidió ir a Stock por Producto: la
        # vista 1 es otro fragment, así que hace falta una corrida completa.
        # Al FINAL de la sección, con todos sus widgets ya registrados: un
        # `st.rerun` antes los habría dado por viejos (regla #373).
        if st.session_state.pop(_K_IR, False):
            st.rerun(scope="app")

    def _dib_area():
        from .inventario_areas_pieza import renderizar
        renderizar(d,d_excl,dict(area=col_area,fam=col_fam,subfam=col_subfam,
                   cod=col_cod,prod=col_prod,unidad=col_unidad,punit=col_punit,
                   cant=col_cant,val=col_val,cod_area=col_cod_area,
                   factor=col_factor,usal=col_usal,motivo=COL_MOTIVO),_h,consumo)

    def _dib_productos():
        # UNA tarjeta a lo ancho y no el par ficha + panel de apoyo de
        # "Buscar producto": son ocho columnas, y en dos tercios de pantalla
        # el nombre del producto no entraba. El panel de "productos
        # relacionados" no tiene reemplazo a propósito: con el listado
        # entero y el filtro de subfamilia, los relacionados son la tabla.
        seccion_productos(
            d, col_cod=col_cod, col_prod=col_prod, col_fam=col_fam,
            col_subfam=col_subfam, col_area=col_area,
            col_unidad=col_unidad, col_punit=col_punit,
            col_cant=col_cant, col_val=col_val,
            col_factor=col_factor, col_usal=col_usal,
            col_cod_area=col_cod_area)
        if st.session_state.pop(_K_IR,False):
            st.rerun(scope="app")

    def _dib_movimientos():
        with st.container(border=True,
                          key="ajuste_graf_card_izq_inv_movimientos"):
            seccion_movimientos(
                d, col_cod_area=col_cod_area, col_cod=col_cod,
                col_area=col_area, col_prod=col_prod, col_fam=col_fam,
                col_punit=col_punit)

    def _dib_tabla():
        with st.container(border=True, key="ajuste_graf_card_izq_inv_tabla"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    _DIBUJANTES = {
        "inv_sec_persp_stock": lambda: dibujar_perspectiva(
            "stock", EJES_STOCK, PERSPECTIVAS_STOCK, _DIBUJANTES),
        "inv_sec_area":    _dib_area,
        "inv_sec_productos": _dib_productos,
        "inv_sec_movimientos": _dib_movimientos,
        "inv_sec_tabla":   _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment: es el que observan el
    # scrollspy y la precarga (mismo bucle que Compras, Receta Base y Ajuste).
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
