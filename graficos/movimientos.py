"""
graficos.movimientos — dashboard ÚNICO de Movimientos (requerimientos,
salidas, porcionamientos y producción).

Una sola página con las NUEVE vistas del flujo de stock (la octava, desde
el 2026-09-28, «Consumo según recetas»: lo que usaron las VENTAS en
insumos de compra, en `graficos/movimientos_consumo.py`, regla #558; la
novena, desde el 2026-09-30, «Producción»). Las de requerimientos y salidas vivían hasta el 2026-09-05 en dos
reportes que un chip Requerimiento/Salidas alternaba. A pedido, al ver que
la Evolución ya mostraba los dos lados juntos: «esto ya no debería estar, ya
que ahora muestra ambos».

    Requerimientos (requerimientos)    Por período · Por sub almacén (la
                                       cadena de tablas) · Tabla
    Salidas (salidas.parquet)          Por período · Detalle de salidas (los
                                       cinco cuadros) · Tabla
    Porcionamientos                    Porcionamientos (la merma por período)
      (porcionamientos.parquet)
    Producción                         Producción (lo producido por período)
      (ordenesproduccion.parquet)

QUÉ PASÓ EL 2026-09-30. Entró «Producción», a pedido: el reporte
«Producción» del Almacén (`Sp_RepOrdenProduccion`) llevado a una consulta
del Sheet y a la MISMA tarjeta «por período», con un cuarto `Lado` —la
orden es el documento; lo que produjo, sus líneas— que no suma las órdenes
generadas: no produjeron nada (`graficos/movimientos_periodo.py::
tarjeta_produccion_periodo`). Va después de Porcionamientos, que es la otra
transformación que se registra en el Almacén. La recortan los DOS chips de
la franja: su área y su familia son las mismas de requerimientos. Ver
`arquitectura.md` regla #575.

QUÉ PASÓ EL 2026-09-24 (2). «Top productos · salidas» —un gráfico de barras
con los diez productos de mayor valorizado dado de baja— se retiró a pedido
y en su lugar entró «Detalle de salidas»: cinco cuadros clickeables en
cadena, tipo de baja › área › familia › subfamilia › producto, cada uno con
su valorizado y su %, con el look de los de «Stock por área» de Inventario
(`graficos/drill_tablas.py::seccion_cuadros`). El top de productos no se
perdió: es el quinto cuadro, ordenado por valorizado y sin corte en diez.
Suma lo MISMO que «Salidas por período» —sin las anuladas ni las líneas sin
producto (`salidas_que_suman`)—, así que las dos secciones de salidas dan
el mismo total para el mismo rango. Ver `arquitectura.md` regla #511.

QUÉ PASÓ EL 2026-09-24. Entró «Porcionamientos», a pedido y aprobada sobre
un mockup: la MISMA tarjeta de las dos «por período», con un tercer `Lado`
que en vez de un valorizado mide la MERMA EN SOLES de cada porcionamiento
(`graficos/movimientos_periodo.py::tarjeta_porcionamientos_periodo`). Va
como tercer grupo, al final. Su parquet lo carga la sección misma
(`_cargar_porcionamientos`) y lo recorta el chip «Sub Almacén», no el de
Familia: la consulta no trae la familia. Ver `arquitectura.md` regla #510.

QUÉ PASÓ EL 2026-10-08. Cada vista tiene su propio botón de fecha y su
propio rango (`CATEGORIA_VISTA`), y la franja de este reporte ya no dibuja
calendario: las secciones reciben los parquets ENTEROS y cada una recorta
el suyo. Ver `arquitectura.md` regla #617.

QUÉ PASÓ EL 2026-09-23. «Top productos · requerim.» se retiró a pedido y en
su lugar —y primera de la pila— entró «Requerimientos por período»
(`graficos/movimientos_periodo.py`): la gemela de «Compras por período»,
con las barras partidas por área, un Resumen de una fila por barra y el
Detalle de los requerimientos de la que se toque. El top de productos no se
perdió: es un recorte de esa tarjeta («Top 5/10/20 por valor» en su selector
de Producto) y sigue la tabla de productos al pie de «Por sub almacén».
Ver `arquitectura.md` regla #508.

El mismo día, y también a pedido, la dona de «Tipo de descargo» dejó su
lugar a «Salidas por período»: la MISMA tarjeta sobre salidas.parquet, con
las barras partidas por el área que dio de baja —que el parquet trae desde
ese día, `AREA`— y el tipo de descargo como filtro y como columna del
Detalle. Y el chip «Sub Almacén» de la franja pasó a recortar también las
salidas. Ver `arquitectura.md` regla #509.

QUÉ PASÓ EL 2026-09-13. La página abría con TRES gráficos —Evolución
(requerido vs dado de baja), Proporción dada de baja y el ranking de Sub
Almacén— y los tres se fueron a pedido: «eliminemos los 3 gráficos
iniciales». En su lugar entra UNA sección con la cadena de cuatro tablas
clickeables que Inventario estrenó ese mismo día: Sub Almacén › Familia ›
Subfamilia arriba y la tabla de Productos abajo. El componente es compartido
(`graficos/drill_tablas.py::seccion_cadena`), así que no hay una segunda
versión del mismo look acá adentro.

Los dos builders que quedaron sin caller —`_evolucion_movimientos` y
`_ranking_proporcion_baja`, en `graficos/movimientos_comun.py`— no se
borraron entonces, para que volver a colgarlos de la pila fuera una línea.
La Evolución se borró el 2026-10-08 con la escala de tiempo vieja (regla
#618); el ranking sigue ahí, completo y documentado. Lo dice también la
cabecera de aquel módulo.

POR QUÉ ERAN DOS REPORTES Y AHORA SON UNO. La separación tenía sentido
mientras cada lado contestaba sólo por lo suyo. Dejó de tenerlo el
2026-09-05, cuando la Evolución pasó a dibujar requerido y baja en la misma
figura (regla #320): a partir de ahí el chip pedía elegir un lado en una
página cuyo primer gráfico ya mostraba los dos. Es el mismo movimiento —y el
mismo pedido, casi con las mismas palabras— que fusionó Receta Base y Receta
Venta el 2026-09-04; ver `graficos/recetas.py` y la regla #303.

DOS VISTAS DE SALIDAS NO SOBREVIVIERON, y no por falta de lugar: estaban
MUERTAS. «Subalmacén» y «Subalm. × tipo» colgaban de una columna que
`salidas.parquet` no trae — sus columnas reales son LOCAL (constante
"SAPIENS") y TIPO DESCARGO, confirmado contra R2 el 2026-09-05. Las dos
dibujaban «No hay columnas suficientes para este gráfico» desde que nacieron.
La regla #98 ya había medido esto en 2026-08-13 («el chip/agrupar de Sub
Almacén en Salidas no hace nada, en silencio») y lo dejó como tarea aparte;
esta fusión es esa tarea. (El área que faltaba llegó el 2026-09-23: la
consulta de salidas trae desde entonces `AREA`, regla #509.)

DOS PARQUETS EN UNA PÁGINA. `app.py` carga UNO por reporte y lo pasa como
`df_f`; el segundo se carga acá con `data.cargar`, que es el patrón de
`recetas.py` y de `recetas_comun.py::_cargar_flujo_compras`. `df_f` es el de
REQUERIMIENTOS (el reporte «Movimientos» apunta a requerimientos.parquet):
es el lado grande —144.636 filas contra 17.355— y el dueño de la Tabla
pivote. (Hasta el 2026-09-23 era también el único que traía el área.)

Las dos Tablas NO se dibujan igual, y no es un descuido:
  · la de requerimientos va por `tabla_cb`, que app.py resuelve a
    `_cb_requerimientos_tabla` — la pivote de siempre, que deriva Mes/Año y
    usa `grandTotalRow`;
  · la de salidas llama a `renderizar_aggrid_desktop` directo, porque
    `tabla_cb` recorta con el `cols_mostrar` del reporte ACTIVO (ver
    `app.py::_render_tabla`) y pasarle el df de salidas reventaría con un
    KeyError. Las dos le pasan al grid el nombre LITERAL de su lado
    ("Requerimientos" / "Salidas") y no el del reporte activo: `tablas/
    desktop.py` decide por ese string el modo pivote y la paginación, así
    que los dos comportamientos se conservan tal cual estaban.

QUÉ EXCLUYE CADA SECCIÓN, que es donde la página puede contradecirse:
las dos tarjetas «por período» (2026-09-23, a pedido) descartan los
documentos ANULADOS y los SIN ÍTEMS —una línea sin producto ni valor— y los
nombran en su fila de KPI (reglas #508 y #509). «Detalle de salidas»
(2026-09-24) nació con el mismo criterio que su vecina de salidas y nombra
las anuladas junto al título de su primer cuadro (#511). Las demás miran sus
datos con anulados incluidos, así que el valorizado de requerimientos es el
mismo en la cadena de tablas y en la Tabla pivote. Las salidas anuladas de
los últimos doce meses son 52, por S/ 11.129 (el 5,7 % de lo que sí se dio
de baja, medido el 2026-09-24): lo que separa el total de la Tabla de
salidas del de sus dos vecinas. Los requerimientos anulados son S/ 174.939
de S/ 8.481.700 en el histórico (2,1%, medido contra R2 el 2026-09-13) y
S/ 15.868 en 2026 (0,9%): lo que puede separar el total de «Requerimientos
por período» del de «Por sub almacén». Las otras no se cambiaron porque
mover números que nadie pidió mover es otra decisión; queda anotado en la
regla #322.

Punto de entrada público: renderizar_graficos_movimientos().
"""

import re
import unicodedata

import pandas as pd
import streamlit as st

import franja_fecha
import kardex
from data import cargar as _cargar_reporte, secrets_disponibles, sello_datos
from estado_rango import atajos_tarjeta
from estilos import TAM_FUENTE
from tablas import renderizar_aggrid_desktop
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills, _render_rail,
    _resolver, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    rango_tarjeta, renderizar_graficos_genericos, seccion_perezosa,
    selector_fecha_tarjeta,
)
# `_ANULADO` y `SALIDAS` son de la tarjeta «Salidas por período»: el
# «Detalle de salidas» suma lo mismo que ella, y dos copias de «qué es una
# salida anulada» —o de cómo se escribe «3 anuladas»— se separan al primer
# retoque.
from graficos.movimientos_periodo import (
    _ANULADO, SALIDAS, aviso_poco_registro, aviso_rango_poco_registro,
    lineas_documentos, meses_poco_registro, orden_areas, rango_poco_registro,
    rotulo_anio,
    tarjeta_porcionamientos_periodo,
    tarjeta_produccion_periodo, tarjeta_requerimientos_periodo,
    tarjeta_salidas_periodo,
)
from graficos import drill_tablas
from graficos.movimientos_consumo import tarjeta_consumo
from graficos.movimientos_destino import tarjeta_destino
from graficos.movimientos_merma import (
    VALOR_HOY, precios_hoy, selector_valorizacion, tarjeta_proveedores,
    tarjeta_rendimiento, tarjeta_revisar, unidades_kardex, valorizacion,
)

# El rótulo del rail es CORTO a propósito: la franja de Vistas es horizontal
# y aplana las categorías a una sola fila (ver `base.py::_render_rail`), así
# que ocho ítems compiten por el ancho útil de una laptop (~1010px). El
# nombre largo vive en el id — que es lo que viaja en `?vista=` y lo que
# empareja con `_PILA`.
#
# El sufijo « · req.» / « · sal.» es el desambiguador: «Por período» y
# «Tabla» existen en los dos lados (y «Top productos» existió en los dos
# hasta el 2026-09-24) y al juntarlas quedaban dos ítems con el mismo nombre.
#
# Las dos «Tabla» están OCULTAS desde el 2026-09-23, con las de los demás
# reportes: `rail_sin_tablas` acá y `pila_sin_tablas` en `_PILA`, de a par
# (regla #507).
_RAIL_CATEGORIAS = rail_sin_tablas((
    # «Requerimientos por período» va PRIMERA desde el 2026-09-23, a pedido,
    # y ocupa el lugar de «Top productos · requerim.», que se retiró ese día;
    # «Salidas por período», su gemela, reemplazó a «Tipo de descargo» el
    # mismo día (ver `graficos/movimientos_periodo.py`). Rótulo e ícono son
    # los de «Compras por período», con el sufijo de su lado: dos «Por
    # período» sueltos serían dos ítems con el mismo nombre.
    #
    # «Por sub almacén» ocupa el sitio que tenían «Evolución», «Proporción
    # dada de baja» y el ranking «Sub Almacén», que se retiraron el
    # 2026-09-13. No hereda el nombre de aquel ranking —que era UN cuadro—
    # porque ahora son cuatro tablas encadenadas: el ítem del rail nombra la
    # cadena, no su primer eslabón.
    #
    # Los rótulos de las cuatro primeras se escriben enteros desde el
    # 2026-10-01, a pedido («Requerimientos por Período», «… por Área»,
    # «Salidas por …»): los ids de la izquierda NO cambian — los usan la
    # pila, las keys y los tests.
    ("Requerimientos", (("Requerimientos por período", "Requerimientos por Período", ":material/calendar_view_week:"),
                        ("Por sub almacén",            "Requerimientos por Área",    ":material/warehouse:"),
                        ("Tabla · requerim.",          "Tabla · req.",               ":material/table_rows:"))),
    # «Detalle de salidas» (2026-09-24, regla #511) ocupa el sitio de «Top
    # productos · salidas», que se retiró ese día. Nombre sin sufijo: no
    # tiene gemela del lado de requerimientos. El ícono es el de un tablero
    # partido en paneles, que es lo que dibuja —cinco cuadros, 3 + 2—.
    # «Destino de lo que entra» (2026-10-08, regla #614): las bajas
    # contra lo que se compró, produjo o porcionó, producto por producto.
    # Va con las salidas porque su pregunta es «cuánto de esto se tiró».
    ("Salidas", (("Salidas por período", "Salidas por Período", ":material/calendar_view_week:"),
                 ("Detalle de salidas",  "Salidas por Área",    ":material/view_quilt:"),
                 ("Destino de lo que entra", "Destino de lo que entra", ":material/alt_route:"),
                 ("Tabla · salidas",     "Tabla · sal.",        ":material/table_view:"))),
    # «Porcionamientos» (2026-09-24, regla #510): tercer grupo, al final, a
    # pedido. Una sola vista, con el nombre que se pidió; el ícono son las
    # tijeras del corte.
    # Las tres de MERMA (2026-10-08, regla #615): lo que el «Reporte de
    # Mermas» del Almacén no dice — qué porcionamiento revisar, cómo rinde
    # un producto en el tiempo y cuánto cuesta el kg útil según a quién se
    # le compró. Viven en `graficos/movimientos_merma.py`.
    ("Porcionamientos", (("Porcionamientos", "Porcionamientos", ":material/content_cut:"),
                         ("Merma para revisar", "Para revisar", ":material/flag:"),
                         ("Rendimiento por producto", "Rendimiento", ":material/monitoring:"),
                         ("Proveedor por kg útil", "Costo por kg útil", ":material/local_shipping:"))),
    # «Producción» (2026-09-30, regla #575): las órdenes de producción del
    # Almacén, lo que las áreas preparan con sus recetas base. Va junto a
    # Porcionamientos —las dos transformaciones que se registran en el
    # Almacén— y antes de Consumo, que es la cuenta TEÓRICA de las ventas.
    # El ícono es una licuadora: una preparación.
    ("Producción", (("Producción", "Producción", ":material/blender:"),)),
    # «Consumo según recetas» (2026-09-28, regla #558): cuarto grupo, al
    # final. Lo que las VENTAS usaron en insumos de compra, bajando por las
    # recetas base y los porcionamientos — el lado teórico de lo que las
    # tres de arriba miden del almacén. El ícono es una olla.
    ("Consumo", (("Consumo según recetas", "Consumo", ":material/soup_kitchen:"),)),
))

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA tupla
# (el porqué, en `graficos/compras/__init__.py::_PILA`).
#
# Cada lado con sus vistas y su Tabla al final del bloque, igual que
# `recetas.py`. Requerimientos va primero por lo mismo que era el `archivo`
# del reporte: es el lado grande (144.636 filas contra 17.355).
#
# LA FECHA LA GOBIERNA CADA SECCIÓN desde el 2026-10-08 (regla #617): cada
# vista tiene su botón de fecha y su rango (`CATEGORIA_VISTA`, más abajo), y
# la franja de este reporte ya no dibuja calendario (`app.py`,
# `_franja_dibuja_fecha`). Hasta ese día mandaba la píldora de la franja,
# sobre todas a la vez.
_PILA = pila_sin_tablas((
    ("mov_sec_periodo",     "Requerimientos por período"),
    ("mov_sec_cadena",      "Por sub almacén"),
    ("mov_sec_tabla_req",   "Tabla · requerim."),
    ("mov_sec_sal_periodo", "Salidas por período"),
    ("mov_sec_detalle_sal", "Detalle de salidas"),
    ("mov_sec_destino",     "Destino de lo que entra"),
    ("mov_sec_tabla_sal",   "Tabla · salidas"),
    ("mov_sec_porc",        "Porcionamientos"),
    ("mov_sec_merma_rev",   "Merma para revisar"),
    ("mov_sec_merma_rend",  "Rendimiento por producto"),
    ("mov_sec_merma_prov",  "Proveedor por kg útil"),
    ("mov_sec_prod",        "Producción"),
    ("mov_sec_consumo",     "Consumo según recetas"),
))


# ── LA FECHA DE CADA VISTA (2026-10-08, regla #617) ──────────────────────
# A pedido: «cada vista debe tener su propio selector de fecha». Una
# categoría de rango por sección (la clave `rango_cat_Movimientos_<cat>` de
# `estado_rango.clave_rango`), con el mismo botón y el mismo panel que las
# tarjetas de Compras (`selector_fecha_tarjeta`, regla #616). Fuera
# «Rendimiento por producto» y «Proveedor por kg útil»: ya tienen su propia
# ventana (6/12/18 meses), que ahora termina en el último día con datos.
#
# Cada vista recorta SUS datos adentro de su sección, que es un fragment: un
# cambio de fecha la recalcula a ella sola, sin escalar a la página (sin
# `bandera`). Por eso los parquets llegan enteros (con los chips) y el
# recorte es de cada dibujante.
CATEGORIA_VISTA = {
    "mov_sec_periodo":     "req_periodo",
    "mov_sec_cadena":      "req_area",
    "mov_sec_tabla_req":   "req_tabla",
    "mov_sec_sal_periodo": "sal_periodo",
    "mov_sec_detalle_sal": "sal_area",
    "mov_sec_destino":     "destino",
    "mov_sec_tabla_sal":   "sal_tabla",
    "mov_sec_porc":        "porc",
    "mov_sec_merma_rev":   "merma_rev",
    "mov_sec_prod":        "prod",
    "mov_sec_consumo":     "consumo",
}
VISTAS_EN_12_MESES = ("req_periodo", "sal_periodo", "porc", "prod")
"""Las cuatro «por período» abren en «Últimos 12 meses»: dibujan una serie,
y con un mes les queda una barra. Las demás, en «Últimos 30 días»."""


def ctx_de_vista(categoria, fechas=None):
    """El `ctx` de la franja para la vista `categoria`: los topes de SUS
    datos (`fechas` = primer y último día con datos de su parquet; sin
    ellos, los del reporte) y su rango de entrada como default. Lo leen el
    recorte (`rango_de_vista`) y el botón (`fecha_de_vista`): con el mismo
    ctx, los dos nombran la misma clave y siembran el mismo default."""
    ctx = franja_fecha.contexto()
    if not ctx:
        return None
    if fechas and all(fechas):
        fmin, fmax = fechas
    else:
        fmin, fmax = ctx["fecha_min"], ctx["fecha_max"]
    if not (fmin and fmax):
        return None
    hoy = ctx.get("hoy")
    ancla = min(fmax, hoy) if hoy else fmax
    pedido = "m12" if categoria in VISTAS_EN_12_MESES else "d30"
    defecto = next((r for c, _n, _g, r in atajos_tarjeta(ancla, (fmin, fmax))
                    if c == pedido), None)
    return {**ctx, "fecha_min": fmin, "fecha_max": fmax,
            "rango_default_cat": {categoria: defecto} if defecto else {}}


def rango_de_vista(categoria, ctx_v):
    """`(inicio, fin EXCLUSIVO)` de la vista, como Timestamps: la forma de
    `movimientos_comun._rango_vigente`, porque estas fechas traen hora y el
    borde de arriba va con `<` (regla #321). None sin contexto."""
    r = rango_tarjeta(categoria, ctx_v) if ctx_v else None
    if not r:
        return None
    return pd.Timestamp(r[0]), pd.Timestamp(r[1]) + pd.Timedelta(days=1)


def fecha_de_vista(categoria, ctx_v):
    """El que dibuja el botón de fecha de la vista: `dibujar(titulo_html)`.
    Con título, comparten renglón (la fila de `selector_fecha_tarjeta`).
    Las keys llevan el prefijo `mov_f_`, de donde cuelga su CSS
    (`estilos/_80_cards.py`)."""
    def dibujar(titulo_html=None):
        if ctx_v:
            selector_fecha_tarjeta(f"mov_f_{categoria}", None,
                                   titulo_html=titulo_html,
                                   categoria=categoria, ctx=ctx_v)
        elif titulo_html:
            st.markdown(titulo_html, unsafe_allow_html=True)
    return dibujar


def fechas_de(serie):
    """`(primer, último)` día con datos de una serie de fechas, o None."""
    if serie is None:
        return None
    f = pd.to_datetime(serie, errors="coerce").dropna()
    if f.empty:
        return None
    return f.min().date(), f.max().date()


def recortar_vista(d, rng, col="_fecha"):
    """`d` en el rango `rng` (fin exclusivo). Sin rango, entero."""
    if d is None or rng is None or col not in getattr(d, "columns", ()):
        return d
    f = pd.to_datetime(d[col], errors="coerce")
    return d[(f >= rng[0]) & (f < rng[1])]


# (Acá vivía `_barras_ranking`, las barras horizontales de los rankings de
# esta página. Se fue el 2026-09-24 con el último que la usaba, «Top
# productos · salidas»: el de Sub Almacén se había ido el 2026-09-13 y el
# Top de requerimientos el 2026-09-23. Regla #511.)


def salidas_que_suman(d, *, col_estado, col_prod, col_doc=None,
                      col_val=None):
    """`(validas, nota)`: las líneas de salidas que SUMAN y, si en el
    recorte hay salidas anuladas, lo que no se sumó, para decirlo.

    El criterio es el de «Salidas por período»
    (`movimientos_periodo._validas`): una línea suma si trae producto y su
    salida no está anulada. Las que no traen producto son las 91 salidas
    sin ítems del histórico —48 generadas que todavía no movieron el
    kardex, 42 anuladas y una procesada—, que valen cero; las anuladas en
    conjunto no: 52 en los últimos doce meses, por S/ 11.129 (medido el
    2026-09-24). Con el mismo criterio las dos secciones de
    salidas dan el mismo total para el mismo rango, que es lo que la guarda
    de `test_graficos.py::_pruebas_detalle_salidas` compara.

    `nota` es `(corto, largo)` —la forma de `nota_no_suman`— o None: sólo
    nombra las anuladas, porque las líneas sin producto no tienen nada que
    mostrar en ningún cuadro. Las cuenta por SALIDA (`col_doc`), no por
    línea, como la fila de KPI de su vecina; sin código, cada línea es una.
    Sin columna de estado todo suma, que es lo que hace `lineas_documentos`.
    """
    idx = d.index
    if col_estado and col_estado in d.columns:
        estado = d[col_estado].fillna("").astype(str).str.strip().str.upper()
    else:
        estado = pd.Series("", index=idx)
    prod = (d[col_prod].fillna("").astype(str).str.strip()
            if col_prod and col_prod in d.columns else pd.Series("", index=idx))
    anulada = estado == _ANULADO
    validas = d[~anulada & (prod != "")]
    if not anulada.any():
        return validas, None
    an = d[anulada]
    n = (int(an[col_doc].nunique()) if col_doc and col_doc in an.columns
         else len(an))
    valor = (float(pd.to_numeric(an[col_val], errors="coerce").fillna(0).sum())
             if col_val and col_val in an.columns else 0.0)
    corto = f"{SALIDAS.anulados(n)} no suman"
    largo = (f"No suman en ningún cuadro: {SALIDAS.anulados(n)}"
             + (f", por S/ {valor:,.0f}" if valor else "")
             + ". El mismo criterio que «Salidas por período».")
    return validas, (corto, largo)


def _tabla_salidas(df_sal):
    """La Tabla del parquet SECUNDARIO, sin pasar por `tabla_cb`.

    `app.py::_render_tabla` recorta con `_df[cols_mostrar]`, y `cols_mostrar`
    son las columnas del reporte ACTIVO (requerimientos). Pasarle el df de
    salidas por ahí lanzaría KeyError.

    El nombre que recibe el grid es "Salidas" y no el del reporte activo: de
    ese string cuelga `tablas/desktop.py::es_salidas`, que apaga la
    paginación. Sin él, la Tabla de salidas cambiaría de conducta sólo por
    haberse mudado de página.
    """
    cols = [c for c in df_sal.columns if not c.startswith("_")]
    font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam"), 14)
    renderizar_aggrid_desktop(df_sal[cols], cols, "Salidas", font_px,
                              cols_visibles=None)


# ── LA FECHA DE LAS SALIDAS Y LA COMPARACIÓN (2026-10-08, regla #614) ─────
# Una nota de salida tiene DOS fechas: cuándo se REGISTRÓ (la que escribe la
# «Relación de Notas de Salidas» del Almacén, `MSUBSALIDA.fRegistro`) y
# cuándo se PROCESÓ y movió el stock (la del kardex: la «Relación de
# Salidas», `SpLisRepSalida`, y Stock › Movimientos por Tipo). Casi siempre
# es el mismo día; cambia en las notas que cruzan de mes. Septiembre 2026:
# S/ 6.893 por registro y 7.703 por proceso, las dos cuadradas al céntimo.
# Abre en REGISTRO, a pedido: «es la fecha en que supuestamente ocurrió la
# baja en forma física».
FECHA_REGISTRO = "Registro"
FECHA_PROCESO = "Proceso"
K_FECHA_SAL = "mov_sal_fecha"
_COLS_FECHA_SAL = {
    FECHA_REGISTRO: ["Fecha registro", "FECHA REGISTRO"],
    FECHA_PROCESO: ["Fecha procesado", "FECHA PROCESADO"],
}
_ROT_FECHA_SAL = {FECHA_REGISTRO: "fecha de registro",
                  FECHA_PROCESO: "fecha de proceso"}

COMPARAR_SAL = ("Sin comparar", "Año pasado", "Dos años")
"""Cuántos años atrás comparan las secciones de salidas: el índice es el
número de años. Abre en «Año pasado», como el mockup aprobado."""
K_COMP_SAL = "mov_sal_comparar"


def _selectores_salidas():
    """La fecha y la comparación de las secciones de SALIDAS, en el panel
    «Filtros» de la franja (regla #614).

    En el panel y no en una tarjeta por dos razones: mandan sobre TRES
    secciones a la vez —por período, por área y el destino—, y un control
    adentro de una sección vive en su fragment, que no vuelve a cargar el
    parquet (lo carga `renderizar_graficos_movimientos`, afuera). Y en la
    franja no le cuestan alto a ninguna tarjeta. Es el lugar de los otros
    dos selectores de «qué fecha cuenta»: el día de la venta (#593) y el
    mes del cierre (#613)."""
    st.markdown('<div class="filtro-rotulo filtro-mov_sal_fecha">Fecha de '
                'las salidas</div>', unsafe_allow_html=True)
    st.segmented_control(
        "Fecha de las salidas", [FECHA_REGISTRO, FECHA_PROCESO],
        default=FECHA_REGISTRO, required=True, key=K_FECHA_SAL,
        label_visibility="collapsed",
        help=("**Registro**: el día en que se digitó la nota, como la "
              "«Relación de Notas de Salidas» del Almacén. **Proceso**: el "
              "día en que movió el stock, como el kardex, la «Relación de "
              "Salidas» y Stock › Movimientos por Tipo. Sólo cambian las "
              "notas que cruzan de mes."))
    st.markdown('<div class="filtro-rotulo filtro-mov_sal_comparar">Comparar '
                'salidas con</div>', unsafe_allow_html=True)
    st.segmented_control(
        "Comparar salidas con", list(COMPARAR_SAL), default=COMPARAR_SAL[1],
        required=True, key=K_COMP_SAL, label_visibility="collapsed",
        help=("El mismo rango de fechas uno o dos años atrás: un trazo gris "
              "sobre cada barra, una tarjeta con la variación y, en el "
              "Resumen y en los cuadros, una columna «vs <año>»."))


def fecha_salidas():
    """La fecha elegida para las salidas (`FECHA_REGISTRO` por defecto)."""
    f = st.session_state.get(K_FECHA_SAL)
    return f if f in _COLS_FECHA_SAL else FECHA_REGISTRO


def anios_comparar_salidas():
    """0, 1 o 2: cuántos años atrás comparan las secciones de salidas."""
    c = st.session_state.get(K_COMP_SAL, COMPARAR_SAL[1])
    return COMPARAR_SAL.index(c) if c in COMPARAR_SAL else 1


# ── LA CAUSA DE UNA BAJA (regla #614) ─────────────────────────────────────
# `MSUBSALIDA.tMotivo` es texto libre, pero desde octubre de 2025 se escribe
# casi siempre igual: «PRODUCTO DE BAJA / <causa>» (el 90 % de lo dado de
# baja en 2026), con erratas («PRODCUTO», «TEIMPIO»). Doce meses (oct 2025 –
# sep 2026), S/ 34.431 en bajas: tiempo de vida 51 %, cocción o término
# 10 %, equipo malogrado o frío 6 %. La columna llega al parquet con
# `ALMACEN.DBO.MSUBSALIDA.tMotivo AS 'MOTIVO'` en la consulta del Sheet.
_COLS_MOTIVO_SAL = ["MOTIVO", "Motivo"]
COL_CAUSA = "_causa"
SIN_CAUSA = "Sin causa escrita"
OTRA_CAUSA = "Otra causa"
_CAUSAS = (
    # (causa, palabras), en orden de precedencia: «PRODUCTO DE BAJA
    # (MANIPULACION DE COCINA / TIEMPO DE VIDA)» es tiempo de vida, y
    # «SE ROMPIO» no lo es.
    ("Equipo malogrado o frío", ("MALOGRAD", "REFRIGER", "FRIO", "MAQUIN",
                                 "MAQU ", "CONGELA")),
    ("Cocción o término", ("COCCION", "TERMINO", "QUEM")),
    ("Prueba o degustación", ("PRUEBA", "DEGUSTA")),
    ("Producción", ("PRODUCCION",)),
    ("Tiempo de vida", ("VIDA", "VENC", "TIEMP", "TEIMP")),
    ("Manipulación", ("MANIPULACION", "ROMPIO", "ROTO", "GUARDAR", "CAYO")),
    # Las dos de abajo (2026-10-10, regla #626): eran «Otra causa». «Uso en
    # el área» se escribe como «USO EN AREA», «USO DE AREA» o «USO SALON»;
    # «USO MENSUAL» sigue siendo otra cosa. La comida de personal se llama
    # «FAMILIA» en la cocina: «PRODUCTOS DE BAJA / FAMILIA» es comida de
    # personal registrada como baja (S/ 2.194 en doce meses).
    ("Uso en el área", ("USO EN", "USO DE", "USO SALON")),
    ("Comida de personal", ("FAMILIA", "PERSONAL")),
    ("Consumo directo", ("CONSUMO DIRECTO",)),
    ("No cumple el estándar", ("STANDAR", "ESTANDAR")),
)
TIPO_BAJAS = "BAJAS"
"""El `TIPO DESCARGO` de la merma de verdad. La causa sólo se lee ahí."""
NO_ES_BAJA = "No es baja"
"""La causa de una salida de otro tipo —comida de personal, despacho a
Mayta, uso en el área—: su motivo dice para qué salió, no por qué se
perdió (regla #626). Sin esto el cuadro «Causa» abría con «Consumo directo
55 %», que era la comida de personal."""
CAUSA_DESDE = pd.Timestamp("2025-10-01")
"""Desde cuándo el motivo se escribe con la forma «PRODUCTO DE BAJA /
<causa>». Antes casi todo dice «PRODUCTOS DE BAJA» y nada más, así que
comparar causas con un rango anterior marca «nuevo» lo que siempre pasó
(«Tiempo de vida: nuevo» en sep 2026 contra sep 2025). Regla #626."""
_PALABRAS_SIN_CAUSA = {"PRODUCTO", "PRODUCTOS", "PRODCUTO", "PRODCUTOS",
                       "PROUCTOS", "PRODUCCTOS", "BAJA", "BAJAS", "DE", "DEL",
                       "LA", "LAS", "EL", "LOS", "Y", "X", "POR"}


def causa_de_baja(motivo):
    """La causa de una salida a partir de su motivo escrito: una de
    `_CAUSAS`, `SIN_CAUSA` si el texto no dice más que «producto de baja»
    (o nada) y `OTRA_CAUSA` si dice algo que no está en la lista. Sin
    tildes ni mayúsculas que importen. Pura."""
    t = unicodedata.normalize("NFKD", str(motivo or "")).encode(
        "ascii", "ignore").decode().upper()
    t = " ".join(t.split())
    if t in ("", "NAN", "NONE", "NULL"):
        return SIN_CAUSA
    for causa, palabras in _CAUSAS:
        if any(p in t for p in palabras):
            return causa
    resto = {w for w in re.split(r"[^A-Z]+", t) if w} - _PALABRAS_SIN_CAUSA
    return OTRA_CAUSA if resto else SIN_CAUSA


def con_causa(d, col_motivo, col_tipo=None):
    """`d` con la columna `COL_CAUSA`, o `d` tal cual sin motivo. Cada texto
    distinto se clasifica una vez. Con `col_tipo`, las salidas que no son
    del tipo Bajas llevan `NO_ES_BAJA` (regla #626)."""
    if d is None or not col_motivo or col_motivo not in d.columns:
        return d
    m = d[col_motivo].fillna("").astype(str)
    mapa = {x: causa_de_baja(x) for x in m.unique()}
    causa = m.map(mapa)
    if col_tipo and col_tipo in d.columns:
        tipo = d[col_tipo].fillna("").astype(str).str.strip().str.upper()
        causa = causa.where(tipo == TIPO_BAJAS, NO_ES_BAJA)
    return d.assign(**{COL_CAUSA: causa})


_COLS_TIPO_SAL = ["TIPO DESCARGO", "Tipo Descargo"]
COL_UNIDAD_SAL = "UNIDAD"
"""La unidad del kardex de cada línea de salidas, que `_cargar_salidas` le
pega desde el maestro (`unidades_kardex`, regla #626)."""

_COLS_AREA_SALIDAS = ["AREA", "Area", "SUB ALMACEN", "Sub Almacen"]
"""Cómo se llama el área en `salidas.parquet`. La trae desde el 2026-09-23
su consulta (`vArea.Descripcion` por `MSUBSALIDA.tCodigoArea`, regla #509)
con el nombre `AREA`; «Sub Almacen» es el del demo de `data.py`."""

_FILAS_DETALLE_SAL = ((1.2, 1, 1), (1.2, 1, 1))
"""El reparto de los SEIS cuadros de «Detalle de salidas»: tipo de baja,
causa y área arriba; familia, subfamilia y producto abajo. El 1.2 de las
dos filas es el mismo corte —la primera columna termina en el mismo sitio
arriba y abajo—, y la fila de arriba es la de «Stock por área»
(`drill_tablas.COLUMNAS_NIVELES[3]`). Regla #511.

LA CAUSA VA SEGUNDA (2026-10-08, regla #614), y no al final: un clic en
«Tiempo de vida» recorta los cuadros que la SIGUEN, así que puesta ahí
contesta «qué se vence, y en qué área»; al final no recortaría nada. Las
dos filas con el mismo reparto: con la subfamilia en 0.8 su columna de
valorizado salía cortada («V…»), medido a 1323px."""


_COLS_SAL_SIN_IA = ("LLAVE SALIDAS", "LOCAL", "CODIGO ESTADO SALIDA")


def salidas_para_ia(hist):
    """Las salidas como las ve el asistente IA (regla #626): sin las
    columnas internas —la causa y la fecha que usa la página salen con
    nombre propio, `CAUSA` y `FECHA`— ni las que no dicen nada (el local es
    uno solo). Pura."""
    d = hist.drop(columns=[c for c in _COLS_SAL_SIN_IA if c in hist.columns])
    d = d.rename(columns={COL_CAUSA: "CAUSA", "_fecha": "FECHA"})
    return d[[c for c in d.columns if not str(c).startswith("_")]]


def nota_salidas_ia(fecha):
    """Qué es la tabla `salidas` y cómo se suma, para el system prompt."""
    return (
        "las notas de salida del Almacén, una fila por LÍNEA (producto) de "
        "cada nota (\"COD SALIDA\"). \"FECHA\" es la de "
        + _ROT_FECHA_SAL.get(fecha, "registro") + ", la que usa la página. "
        "Para sumar, excluye WHERE \"NOMBRE ESTADO SALIDA\" <> 'ANULADO' y "
        "las líneas sin producto. \"VALOR NETO\" es el valorizado en soles; "
        "\"CANT SALIDA\" está en \"UNIDAD\" (la del kardex: KILOS, UND, "
        "LITROS) — suma cantidades sólo de UN producto o de una misma "
        "unidad. \"TIPO DESCARGO\" dice QUÉ salida es: sólo 'Bajas' es merma; "
        "'Comida Personal' es la comida del personal, 'Despacho Mayta' una "
        "venta interna, 'Uso en el Area' un consumo. \"CAUSA\" sale del "
        "motivo escrito y sólo se lee en las Bajas (desde octubre de 2025). "
        "Un mes con muchas menos notas que los anteriores puede ser falta "
        "de registro y no menos merma: si lo ves, dilo.")


def _cargar_salidas(col_fam_sal, fam_sel, sub_sel=(), fecha=FECHA_REGISTRO):
    """`(hist, col_fecha)`: `salidas.parquet` ENTERO con la familia y el
    área de los chips —cada vista lo recorta a SU fecha, regla #617; el
    entero sirve además para comparar con años anteriores y medir cuánto
    se registra, regla #614— y la columna de fecha que se usó — la de
    `fecha`, registro o proceso; sin la de proceso (un parquet viejo, el
    demo), la de registro. `(None, None)` si no hay parquet.

    Por PROCESO, una salida generada y sin procesar no tiene fecha y no
    entra: todavía no movió el stock.

    Defensivo igual que `recetas.py` con recetabase: si el parquet no está o
    no trae su fecha, las secciones de Salidas avisan y el resto de la
    página sigue funcionando.

    El borde superior va como `< fin + 1 día` porque `FECHA REGISTRO` trae
    hora en las 17.101 filas — ver regla #321, que es donde se midió.

    EL CHIP «SUB ALMACÉN» TAMBIÉN RECORTA LAS SALIDAS desde que el parquet
    trae su área (2026-09-23, regla #509). Antes no podía —la columna no
    existía— y la página lo decía; ahora son el MISMO catálogo de áreas
    (las 16 de salidas están entre las de requerimientos, «CAVA » con su
    espacio incluido), así que la comparación va sin espacios de los dos
    lados. Sin la columna (un parquet viejo), el chip no recorta, como antes.
    """
    df = _cargar_reporte("salidas.parquet")
    if df is None or df.empty:
        return None, None
    col_fecha = (_resolver(df, _COLS_FECHA_SAL[fecha])
                 or _resolver(df, _COLS_FECHA_SAL[FECHA_REGISTRO]))
    if not col_fecha:
        return None, None
    d = con_causa(df, _resolver(df, _COLS_MOTIVO_SAL),
                  _resolver(df, _COLS_TIPO_SAL)).copy()
    # La UNIDAD de cada cantidad (regla #626): sin ella «cuánto arroz»
    # sólo se contestaba en soles.
    col_cod = _resolver(d, ["COD PRODUCTO", "Cod Producto"])
    if col_cod and COL_UNIDAD_SAL not in d.columns:
        unid = unidades_kardex()
        if unid is not None:
            d[COL_UNIDAD_SAL] = (d[col_cod].fillna("").astype(str).str.strip()
                                 .map(unid).fillna(""))
    d["_fecha"] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=["_fecha"])
    if fam_sel and col_fam_sal and col_fam_sal in d.columns:
        d = d[d[col_fam_sal].astype(str).isin(fam_sel)]
    col_area = _resolver(d, _COLS_AREA_SALIDAS)
    if sub_sel and col_area:
        _elegidas = {str(s).strip() for s in sub_sel}
        d = d[d[col_area].fillna("").astype(str).str.strip().isin(_elegidas)]
    return d, col_fecha


_COLS_PORC = {
    "fecha": "FEC REGIST",
    "doc": "COD PORC",
    "area": "SUB ALMACEN",
    "tipo": "USUARIO REG",
    "prod": "PROD INICIAL",
    "cod": "COD PROD INIC",
    "unid": "UNID PROD INIC",
    "cant": "CANT A PORCIONAR",
    "merma": "CANT MERMA",
    "fin": "PROD FINAL RESULT",
    "cant_fin": "CANT RESULT",
    "unid_fin": "UNID PROD FIN",
    "pprom": "PREC PROM PROD FIN",
    "peso": "PESO RESULT",
}
"""Las columnas de `porcionamientos.parquet` (la fila 9 del Sheet de
consultas, 2026-09-23) por el nombre que pide `lineas_porcionamientos`.
`_resolver` compara sin mayúsculas ni espacios, así que «Fec Regist» (el
demo de `data.py`) también las encuentra."""


def _cargar_porcionamientos(sub_sel=()):
    """`porcionamientos.parquet` ENTERO con el chip «Sub Almacén», o None si
    no está o no trae su fecha. Cada vista lo recorta a SU fecha (regla
    #617); entero, además, es de donde salen lo normal de un producto y la
    ventana de «Rendimiento», que miran para atrás (regla #615).

    El borde superior del recorte va como `< fin + 1 día` por lo mismo que
    salidas: `FEC REGIST` trae hora (regla #321). EL CHIP «FAMILIA» NO RECORTA ESTA
    SECCIÓN: la consulta no trae la familia del producto (se dejó para más
    adelante, regla #510), y filtrar por un dato que no está sería vaciarla
    en silencio. El de Sub Almacén sí: `SUB ALMACEN` es el mismo catálogo
    de áreas (`vArea`) que el de requerimientos."""
    df = _cargar_reporte("porcionamientos.parquet")
    if df is None or df.empty:
        return None
    col_fecha = _resolver(df, _COLS_PORC["fecha"])
    if not col_fecha:
        return None
    d = df.copy()
    d["_fecha"] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=["_fecha"])
    col_area = _resolver(d, _COLS_PORC["area"])
    if sub_sel and col_area:
        _elegidas = {str(s).strip() for s in sub_sel}
        d = d[d[col_area].fillna("").astype(str).str.strip().isin(_elegidas)]
    return d


ARCHIVO_PRODUCCION = "ordenesproduccion.parquet"
"""El reporte «Producción» del Almacén (`Sp_RepOrdenProduccion`), llevado
al Sheet de consultas el 2026-09-30 con el nombre `ordenesproduccion`.
Regla #575."""

_COLS_PROD = {
    "fecha": "FECHA REGISTRO",
    "doc": "COD ORDEN PRODUCCION",
    "area": "AREA",
    "estado": "NOMBRE ESTADO",
    "tipo": "USUARIO REGISTRO",
    "fam": "NOMBRE FAMILIA",
    "prod": "NOMBRE PRODUCTO",
    "cant": "CANTIDAD",
    "unid": "UNIDAD",
    "punit": "PRECIO UNIT",
    "val": "VALOR ITEM",
}
"""Las columnas de `ordenesproduccion.parquet` por el nombre que pide
`lineas_documentos`. La fecha es la de REGISTRO, como el reporte del
Almacén: su «Filtrado por Proceso» filtra también por el registro (el SP
usa `fRegistro` en las dos ramas). `CANTIDAD` va en la unidad de ENTRADA
del producto (`UNIDAD`), la del kardex."""


def _cargar_produccion(fam_sel=(), sub_sel=()):
    """`(df, falta)`: `ordenesproduccion.parquet` ENTERO con sus dos chips;
    la sección lo recorta a SU fecha (regla #617).

    `falta` es True si el parquet todavía no existe en R2 —la fila del Sheet
    no se agregó o la extracción no corrió—: la sección lo dice en vez del
    error rojo de `data.cargar`. Se sabe por el sello (el `LastModified`,
    cacheado un minuto), sin intentar la descarga. En modo demo no hay R2 y
    carga el demo.

    Los DOS chips recortan: el área es la de `vArea` y la familia la del
    maestro, los mismos catálogos que requerimientos (comparado contra los
    dos parquets el 2026-09-30). El borde superior va como `< fin + 1 día`
    porque `FECHA REGISTRO` trae hora (regla #321)."""
    if secrets_disponibles() and not sello_datos(ARCHIVO_PRODUCCION):
        return None, True
    df = _cargar_reporte(ARCHIVO_PRODUCCION)
    if df is None or df.empty:
        return None, False
    col_fecha = _resolver(df, _COLS_PROD["fecha"])
    if not col_fecha:
        return None, False
    d = df.copy()
    d["_fecha"] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=["_fecha"])
    col_area = _resolver(d, _COLS_PROD["area"])
    if sub_sel and col_area:
        _elegidas = {str(s).strip() for s in sub_sel}
        d = d[d[col_area].fillna("").astype(str).str.strip().isin(_elegidas)]
    col_fam = _resolver(d, _COLS_PROD["fam"])
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]
    return d, False


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_movimientos(df_f, nombre_reporte, df_full=None,
                                    tabla_cb=None):
    """Dashboard de Movimientos. `df_f` es requerimientos.parquet filtrado
    por la fecha de la franja y `df_full`, el mismo parquet entero: desde el
    2026-10-08 cada sección recorta el suyo a SU fecha (regla #617), así
    que se trabaja sobre `df_full`. salidas.parquet se carga acá adentro,
    también entero.

    `tabla_cb`: callback que arma la Tabla de requerimientos (inyectado por
    app.py — la pivote). La de salidas va por `_tabla_salidas`, ver el
    docstring del módulo.
    """
    # Cada sección recorta a su fecha: el parquet llega ENTERO. `df_f` (el
    # rango de la franja, que en este reporte ya no se ve) queda sólo de
    # respaldo para quien llame sin `df_full`.
    df_req = df_full if df_full is not None else df_f
    # ── Columnas de REQUERIMIENTOS (df_f) ─────────────────────────────────
    col_prod = _resolver(df_f, ["Nombre Producto", "NOMBRE PRODUCTO", "Producto"])
    col_sub = _resolver(df_f, ["Sub Almacen", "SUB ALMACEN", "Subalmacen", "Sub Almacén"])
    col_fam = _resolver(df_f, ["Nombre Familia", "NOMBRE FAMILIA", "Familia"])
    col_subfam = _resolver(df_f, ["Nombre Subfamilia", "NOMBRE SUBFAMILIA",
                                  "Subfamilia"])
    col_cant = _resolver(df_f, ["Cantidad", "CANTIDAD"])
    col_val = _resolver(df_f, ["Valor Item", "VALOR ITEM", "Valorizado"])
    col_punit = _resolver(df_f, ["Precio Unit", "PRECIO UNIT",
                                 "Precio Unitario"])
    # Las tres que usa sólo «Requerimientos por período»: la fecha que
    # agrupa las barras, el código que cuenta requerimientos (el demo no lo
    # trae: ahí cada fila cuenta como uno) y el estado.
    col_fecha = _resolver(df_f, ["Fecha Registro", "FECHA REGISTRO"])
    col_req = _resolver(df_f, ["Cod Requerimiento", "COD REQUERIMIENTO"])
    col_estado = _resolver(df_f, ["Nombre Estado Requerimiento",
                                  "NOMBRE ESTADO REQUERIMIENTO"])

    if not col_val and not col_cant:
        st.warning("No se encontraron las columnas de cantidad/valor del "
                   "requerimiento. Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Sub Almacén / Familia como chips en la franja ─────────────
    # SUB ALMACÉN recorta los DOS lados desde el 2026-09-23: hasta ese día
    # salidas.parquet no traía el área que dio de baja y sus secciones lo
    # ignoraban; ahora la trae (`AREA`, regla #509) y es el mismo catálogo.
    # Sus opciones siguen saliendo de requerimientos, que es el `archivo`
    # del reporte. FAMILIA existe en los dos, con las mismas seis familias.
    with compartimento_filtros(contar_filtros("mov_graf_filtro_sub",
                                              "mov_graf_filtro_fam")):
        # Primero, como el día de la venta en Ventas: el panel tiene techo
        # de 60vh y con las 13 áreas de Sub Almacén lo de abajo queda fuera
        # de la vista sin que nada avise que hay más.
        _selectores_salidas()
        selector_valorizacion()
        _, sub_sel = filtro_pills(df_req, col_sub,
                                  "mov_graf_filtro_sub", "Sub Almacén")
        _, fam_sel = filtro_pills(df_req, col_fam,
                                  "mov_graf_filtro_fam", "Familia")

    d = df_req
    if sub_sel and col_sub:
        d = d[d[col_sub].astype(str).isin(sub_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    # Ve el lado de REQUERIMIENTOS, que es el `archivo` del reporte: la
    # herramienta de SQL corre sobre un df, y darle el otro parquet sin que
    # lo pida sería contradecir el esquema que ya conoce. Entero: cada vista
    # tiene su fecha y no hay una de la página (regla #617).
    publicar_contexto_ia("Movimientos", d,
                         {"Sub Almacén": sub_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # La fecha de requerimientos, una vez: la recortan tres secciones.
    _f_req = (pd.to_datetime(d[col_fecha], errors="coerce")
              if col_fecha else None)
    fechas_req = fechas_de(_f_req)

    def _req_de(rng):
        """Las líneas de requerimientos en `rng` (fin exclusivo)."""
        if rng is None or _f_req is None:
            return d
        return d[(_f_req >= rng[0]) & (_f_req < rng[1])]

    # MÉTRICA FIJA EN VALORIZADO, igual que tenían los dos reportes por
    # separado (Salidas lo fijó el 2026-08-07 a pedido). `col_cant` queda
    # como fallback silencioso por si algún día faltara la columna de valor,
    # pero no hay UI para elegir Cantidad — y no la puede haber barata: las
    # dos mitades cuentan unidades distintas y sumarlas no significa nada.
    col_metrica = col_val or col_cant

    # ── El otro parquet ───────────────────────────────────────────────────
    col_fam_sal = "NOMBRE FAMILIA"
    fecha_sal = fecha_salidas()
    anios_comp = anios_comparar_salidas()
    hist_sal, col_fecha_sal = _cargar_salidas(
        col_fam_sal, fam_sel, sub_sel, fecha=fecha_sal)
    # Si se pidió proceso y el parquet no trae esa fecha, se usó la de
    # registro: el rótulo dice la que de verdad se usó.
    if col_fecha_sal and col_fecha_sal in _COLS_FECHA_SAL[FECHA_REGISTRO]:
        fecha_sal = FECHA_REGISTRO
    fechas_sal = fechas_de(hist_sal["_fecha"]) if hist_sal is not None else None
    # El asistente IA ve también las SALIDAS (regla #626), como una tabla
    # aparte: `datos` siguen siendo los requerimientos.
    if hist_sal is not None:
        publicar_contexto_ia(
            "Movimientos", d, {"Sub Almacén": sub_sel, "Familia": fam_sel},
            extras={"salidas": {"df": salidas_para_ia(hist_sal),
                                "nota": nota_salidas_ia(fecha_sal)}})

    def _col_sal(*nombres):
        return (_resolver(hist_sal, list(nombres))
                if hist_sal is not None else None)

    def _rango_y_boton(clave_sec, fechas):
        """`(rango, dibujante del botón)` de una sección (regla #617)."""
        cat = CATEGORIA_VISTA[clave_sec]
        ctx_v = ctx_de_vista(cat, fechas)
        return rango_de_vista(cat, ctx_v), fecha_de_vista(cat, ctx_v)

    col_tipo = _col_sal("Tipo Descargo", "TIPO DESCARGO")
    col_prod_sal = _col_sal("Nombre Producto", "NOMBRE PRODUCTO")
    col_val_sal = _col_sal("Valor Neto", "VALOR NETO")

    # El orden de las áreas que reparte los COLORES de las dos tarjetas «por
    # período»: el del histórico de requerimientos, para las dos. Así Cocina
    # es del mismo color en la que pide y en la que da de baja (regla #509).
    orden = orden_areas(df_full if df_full is not None else df_f,
                        col_sub, col_val)

    # ── SIN BANDA DE KPIs, a propósito (2026-09-05) ───────────────────────
    # Acá había tres `st.metric` (Requerido / Dado de baja / Baja÷Requerido)
    # y un caption. Se fueron a pedido —"eliminemos todo esto, está muy
    # feo"— y el pedido tiene razón de fondo: la banda ocupaba una pantalla
    # de alto para repetir números que la página ya da DOS renglones más
    # abajo. Lo decía el caption de la Evolución hasta el 2026-09-13; hoy lo
    # dice la fila TOTAL de la primera tabla, pegada a las filas que la
    # componen, que es donde ese número se lee bien.
    #
    # El KPI del reporte —el que se ve sin entrar— no se pierde: vive en el
    # rail de Reportes, y sale de `kpis` en REPORTES (data.py).
    #
    # Ojo si alguna vez vuelve una fila de KPIs EN FLUJO acá arriba: hay que
    # devolver la excepción del jalón en `estilos/_20_compras_rail.py`, o la
    # primera tarjeta se la come (regla #38, y la #322 para esta vuelta).

    # El rail ya no ELIGE: con `secciones` marca dónde estás y scrollea.
    _render_rail(_RAIL_CATEGORIAS, "mov_graf_tipo",
                 btn_prefix="mov_rail_btn_", secciones=_PILA)

    def _sin_salidas():
        st.info("No se pudo cargar salidas.parquet: esta sección queda vacía.")

    # ── LA PILA, PEREZOSA ─────────────────────────────────────────────────
    # Cada sección con su PROPIA key de tarjeta: apiladas, compartir key es
    # una excepción de Streamlit.
    def _dib_cadena():
        # Las CUATRO tablas encadenadas, el mismo componente que Inventario
        # Valorizado (2026-09-13, a pedido: "cuatro tablas similares a las
        # de inventario valorizado, y clickeables"). No hay `st.container`
        # acá: las tres tarjetas las abre `seccion_cadena`, que es la que
        # sabe cuántas son y con qué key va cada una.
        #
        # EL PRIMER NIVEL ES SUB ALMACÉN, que es el área que PIDE
        # (COCINA/BARRA/SALON/GASTOS…) — `requerimientos.parquet` no trae
        # una columna "área" aparte, y es la misma que filtran los chips de
        # la franja, así que la página no se contradice llamándola de dos
        # maneras. Los otros dos niveles son la jerarquía del producto.
        #
        # Sin `abre_en`: el foco por defecto es el sub almacén MAYOR. En
        # Inventario hubo que nombrarlo (GASTOS era el mayor pero no era
        # inventario contable, regla #405); acá el mayor es el que más pide,
        # que es exactamente la primera pantalla que se quiere ver.
        #
        # La fecha de la sección va en el renglón del título del primer
        # cuadro (regla #617), que por eso se acortó: «Valorizado requerido
        # por sub almacén» y el botón no entraban juntos en la tarjeta.
        rng, fecha = _rango_y_boton("mov_sec_cadena", fechas_req)
        drill_tablas.seccion_cadena(
            _req_de(rng), pref="mov", slug="subalm",
            niveles=((col_sub, "sub almacén"), (col_fam, "familia"),
                     (col_subfam, "subfamilia")),
            col_val=col_metrica, col_hoja=col_prod,
            col_ctx=col_sub, nombre_ctx="Sub almacén",
            col_cant=col_cant, col_punit=col_punit,
            titulo_ranking="Requerido por sub almacén", fecha=fecha)

    def _dib_periodo():
        # La tarjeta abre su propio contenedor (con la key de su familia de
        # tarjetas) y sus grillas: vive entera en su módulo, como las de
        # Compras. La fecha es la SUYA (regla #617): se recorta acá y el
        # botón lo dibuja la tarjeta.
        rng, fecha = _rango_y_boton("mov_sec_periodo", fechas_req)
        tarjeta_requerimientos_periodo(
            _req_de(rng), orden=orden, rango=rng, fecha=fecha,
            cols=dict(fecha=col_fecha, doc=col_req, area=col_sub,
                      estado=col_estado, fam=col_fam, prod=col_prod,
                      cant=col_cant, punit=col_punit, val=col_val))

    def _dib_sal_periodo():
        # La MISMA tarjeta sobre salidas (2026-09-23, en lugar de la dona de
        # «Tipo de descargo»): el área que dio de baja parte la barra, y el
        # tipo de descargo queda como filtro y como columna del Detalle. Sin
        # precio unitario en el parquet: lo despeja la tarjeta.
        if hist_sal is None:
            with st.container(border=True,
                              key="ajuste_graf_card_izq_mov_sal_vacia"):
                _sin_salidas()
            return
        rng, fecha = _rango_y_boton("mov_sec_sal_periodo", fechas_sal)
        tarjeta_salidas_periodo(
            recortar_vista(hist_sal, rng), orden=orden, hist=hist_sal,
            anios=anios_comp, rot_fecha=_ROT_FECHA_SAL[fecha_sal],
            rango=rng, fecha=fecha,
            cols=dict(fecha=col_fecha_sal,
                      doc=_col_sal("Cod Salida", "COD SALIDA"),
                      area=_col_sal(*_COLS_AREA_SALIDAS),
                      estado=_col_sal("Nombre Estado Salida",
                                      "NOMBRE ESTADO SALIDA"),
                      fam=_col_sal("Nombre Familia", "NOMBRE FAMILIA"),
                      prod=col_prod_sal,
                      cant=_col_sal("Cant Salida", "CANT SALIDA"),
                      val=col_val_sal, tipo=col_tipo,
                      unid=_col_sal(COL_UNIDAD_SAL)))

    def _dib_tabla_req():
        rng, fecha = _rango_y_boton("mov_sec_tabla_req", fechas_req)
        with st.container(border=True, key="ajuste_graf_card_izq_mov_tabla_req"):
            fecha()
            if tabla_cb is not None:
                tabla_cb(_req_de(rng))
            else:
                st.info("La tabla no está disponible en este contexto.")

    def _dib_detalle_sal():
        # Los CINCO cuadros en cadena (2026-09-24, a pedido, en lugar de «Top
        # productos · salidas»): tipo de baja › área › familia › subfamilia ›
        # producto, cada uno con su valorizado y su %, «similar estilo a los
        # cuadros de la vista de stock por área». Tres arriba y dos abajo:
        # cinco en una fila no entran en 1366px sin cortar los nombres, y el
        # producto —los nombres más largos del parquet— se queda con dos
        # tercios de la fila de abajo. El corte de la primera columna es el
        # mismo en las dos filas (1.2 de 3.2), así que se leen como una
        # grilla. Regla #511.
        #
        # «Tipo de baja» es el TIPO DESCARGO del ERP, con el nombre que se
        # pidió; «Área», la que dio de baja, como en «Salidas por período».
        vacia = "ajuste_graf_card_izq_mov_detsal_vacia"
        if hist_sal is None:
            with st.container(border=True, key=vacia):
                _sin_salidas()
            return
        if not (col_val_sal and col_prod_sal):
            with st.container(border=True, key=vacia):
                st.info("No hay columnas suficientes para esta sección.")
            return
        rng, fecha = _rango_y_boton("mov_sec_detalle_sal", fechas_sal)
        titulo = f"Por tipo de baja · {fecha_sal.lower()}"
        _kw_suman = dict(
            col_estado=_col_sal("Nombre Estado Salida",
                                "NOMBRE ESTADO SALIDA"),
            col_prod=col_prod_sal, col_doc=_col_sal("Cod Salida", "COD SALIDA"),
            col_val=col_val_sal)
        validas, nota = salidas_que_suman(recortar_vista(hist_sal, rng),
                                          **_kw_suman)
        if validas.empty:
            # El botón de fecha va igual: sin él, unas fechas sin salidas
            # dejaban la sección sin manera de cambiarlas.
            with st.container(border=True, key=vacia):
                st.markdown(drill_tablas.CSS_TITULOS_DRILL,
                            unsafe_allow_html=True)
                fecha(f'<div class="inv-rank-tit">{titulo}</div>')
                st.info("Sin salidas en estas fechas. Ampliá el rango con el "
                        "botón de fecha.")
            return
        # El MISMO rango un año atrás, con los mismos chips y la misma
        # fecha: la columna «vs <año>» de cada cuadro (regla #614). Con
        # «Dos años» los cuadros comparan contra el más cercano; los dos
        # años van en el gráfico de «Salidas por período».
        d_ant, rot_ant, sin_comparar = None, "", ()
        if anios_comp and rng and hist_sal is not None:
            off = pd.DateOffset(years=1)
            _h = hist_sal[(hist_sal["_fecha"] >= rng[0] - off)
                          & (hist_sal["_fecha"] < rng[1] - off)]
            d_ant, _ = salidas_que_suman(_h, **_kw_suman)
            rot_ant = rotulo_anio(rng[0], rng[1], off)
            # Antes de que el motivo tuviera forma, las causas no se
            # comparan: todo salía «nuevo» (regla #626).
            if rng[0] - off < CAUSA_DESDE:
                sin_comparar = ("causa",)
        # Los meses con pocas salidas registradas, como en «Salidas por
        # período» (regla #626): ahí una caída no es menos merma, y los
        # cuadros no la pintan de verde.
        aviso = None
        if rng:
            _bh = lineas_documentos(
                hist_sal, fecha="_fecha", doc=_kw_suman["col_doc"],
                area=None, estado=_kw_suman["col_estado"], fam=None,
                prod=col_prod_sal, cant=None, val=col_val_sal)
            # Primero los meses enteros; si el rango no tiene ninguno (los
            # últimos 30 días cruzan dos), el rango entero.
            aviso = (aviso_poco_registro(
                meses_poco_registro(_bh, rng, pd.Timestamp.today().normalize(),
                                    SALIDAS), SALIDAS)
                or aviso_rango_poco_registro(
                    rango_poco_registro(_bh, rng, SALIDAS), SALIDAS))
            if aviso:
                aviso = (f"⚠ Pocas salidas registradas en estas fechas "
                         f"({aviso[0]}): una caída puede ser que no se "
                         "registró, no menos merma.", aviso[1])
        hay_causa = COL_CAUSA in validas.columns
        drill_tablas.seccion_cuadros(
            validas, pref="mov", slug="detsal",
            niveles=((col_tipo, "tipo de baja"),
                     (COL_CAUSA if hay_causa else None, "causa"),
                     (_col_sal(*_COLS_AREA_SALIDAS), "área"),
                     (_col_sal("Nombre Familia", "NOMBRE FAMILIA"), "familia"),
                     (_col_sal("Nombre Subfamilia", "NOMBRE SUBFAMILIA"),
                      "subfamilia"),
                     (col_prod_sal, "producto")),
            filas=_FILAS_DETALLE_SAL, col_val=col_val_sal, nota=nota,
            titulo=titulo, fecha=fecha,
            d_ant=d_ant, rotulo_ant=rot_ant, sin_comparar=sin_comparar,
            aviso=aviso,
            cantidad=(_col_sal("Cant Salida", "CANT SALIDA"),
                      _col_sal(COL_UNIDAD_SAL)),
            aviso_falta={"causa": (
                "La causa sale del motivo escrito en cada nota («PRODUCTO "
                "DE BAJA / TIEMPO DE VIDA»), y la consulta de salidas "
                "todavía no lo trae. Se agrega en el Sheet con "
                "`ALMACEN.DBO.MSUBSALIDA.tMotivo AS 'MOTIVO'` y llega con "
                "«Refrescar».")})

    def _dib_destino():
        # Carga ACÁ, como Porcionamientos: el kardex por mes sólo hace falta
        # cuando la sección sale del esqueleto. La familia del chip recorta;
        # el sub almacén no (la cuenta es del restaurante entero, #614). Sus
        # topes arrancan donde arranca el kardex, no el parquet del reporte.
        rng, fecha = _rango_y_boton("mov_sec_destino",
                            (kardex.INICIO, fechas_req[1]) if fechas_req
                            else None)
        tarjeta_destino(fam_sel, anios_comp, rango=rng, fecha=fecha)

    def _dib_tabla_sal():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_tabla_sal"):
            if hist_sal is None:
                _sin_salidas()
                return
            rng, fecha = _rango_y_boton("mov_sec_tabla_sal", fechas_sal)
            fecha()
            d_sal = recortar_vista(hist_sal, rng)
            if d_sal.empty:
                st.info("Ningún registro coincide con los filtros seleccionados.")
            else:
                _tabla_salidas(d_sal)

    def _dib_porc():
        # El tercer parquet se carga ACÁ y no arriba con el de salidas: sólo
        # hace falta cuando esta sección sale del esqueleto (la última de la
        # pila). `data.cargar` lo cachea igual.
        d_todo_p = _cargar_porcionamientos(sub_sel)
        if d_todo_p is None:
            with st.container(border=True,
                              key="ajuste_graf_card_izq_mov_porc_vacia"):
                st.info("No se pudo cargar porcionamientos.parquet: esta "
                        "sección queda vacía.")
            return
        rng, fecha = _rango_y_boton("mov_sec_porc", fechas_de(d_todo_p["_fecha"]))
        d_porc = recortar_vista(d_todo_p, rng)
        # Con «Precio de hoy» (el default, regla #615) la merma vale lo
        # que el Reporte de Mermas del Almacén.
        tarjeta_porcionamientos_periodo(
            d_porc, orden=orden, rango=rng, fecha=fecha,
            precios=precios_hoy() if valorizacion() == VALOR_HOY else None,
            cols={nombre: _resolver(d_porc, columna)
                  for nombre, columna in _COLS_PORC.items()})

    def _dib_merma(tarjeta, con_rango):
        # Las tres de merma (regla #615) leen el parquet ENTERO con el chip
        # «Sub Almacén»: lo normal de un producto y sus ventanas miran para
        # atrás del rango. Se carga acá, como Porcionamientos. «Para
        # revisar» tiene su fecha (regla #617); «Rendimiento» y «Proveedor»
        # tienen su ventana de 6/12/18 meses, que termina en el último día
        # con datos.
        def dibujar():
            d_todo_p = _cargar_porcionamientos(sub_sel)
            if d_todo_p is None:
                with st.container(border=True,
                                  key=f"ajuste_graf_card_izq_mov_merma_vacia_{tarjeta.__name__}"):
                    st.info("No se pudo cargar porcionamientos.parquet: "
                            "esta sección queda vacía.")
                return
            cols = {nombre: _resolver(d_todo_p, columna)
                    for nombre, columna in _COLS_PORC.items()}
            if con_rango:
                rng, fecha = _rango_y_boton("mov_sec_merma_rev",
                                    fechas_de(d_todo_p["_fecha"]))
                tarjeta(recortar_vista(d_todo_p, rng), d_todo_p, cols, rng,
                        fecha=fecha)
            else:
                tarjeta(d_todo_p, cols, None)
        return dibujar

    def _dib_prod():
        # Se carga ACÁ, como Porcionamientos: sólo cuando la sección sale
        # del esqueleto. Los dos chips la recortan (regla #575).
        d_prod, falta = _cargar_produccion(fam_sel, sub_sel)
        if d_prod is None:
            with st.container(border=True,
                              key="ajuste_graf_card_izq_mov_prod_vacia"):
                if falta:
                    st.info("Todavía no hay datos de producción: falta la "
                            "consulta «ordenesproduccion» en el Sheet de "
                            "consultas, o que corra la extracción.")
                else:
                    st.info(f"No se pudo cargar {ARCHIVO_PRODUCCION}: esta "
                            "sección queda vacía.")
            return
        rng, fecha = _rango_y_boton("mov_sec_prod", fechas_de(d_prod["_fecha"]))
        tarjeta_produccion_periodo(
            recortar_vista(d_prod, rng), orden=orden, rango=rng, fecha=fecha,
            cols={nombre: _resolver(d_prod, columna)
                  for nombre, columna in _COLS_PROD.items()})

    def _dib_consumo():
        # Carga y calcula ACÁ, como Porcionamientos: sólo cuando la sección
        # sale del esqueleto (la última de la pila). La familia del chip
        # recorta los insumos de compra; el sub almacén no aplica (regla
        # #558, `graficos/movimientos_consumo.py`).
        rng, fecha = _rango_y_boton("mov_sec_consumo", fechas_req)
        tarjeta_consumo(fam_sel, sub_sel, rango=rng, fecha=fecha)

    _DIBUJANTES = {
        "mov_sec_periodo":     _dib_periodo,
        "mov_sec_cadena":      _dib_cadena,
        "mov_sec_tabla_req":   _dib_tabla_req,
        "mov_sec_sal_periodo": _dib_sal_periodo,
        "mov_sec_detalle_sal": _dib_detalle_sal,
        "mov_sec_destino":     _dib_destino,
        "mov_sec_tabla_sal":   _dib_tabla_sal,
        "mov_sec_porc":        _dib_porc,
        "mov_sec_merma_rev":   _dib_merma(tarjeta_revisar, True),
        "mov_sec_merma_rend":  _dib_merma(tarjeta_rendimiento, False),
        "mov_sec_merma_prov":  _dib_merma(tarjeta_proveedores, False),
        "mov_sec_prod":        _dib_prod,
        "mov_sec_consumo":     _dib_consumo,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje.
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
