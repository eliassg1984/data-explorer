"""
graficos.movimientos — dashboard ÚNICO de Movimientos (requerimientos,
salidas y porcionamientos).

Una sola página con las SIETE vistas de los tres parquets del flujo de
stock. Las de requerimientos y salidas vivían hasta el 2026-09-05 en dos
reportes que un chip Requerimiento/Salidas alternaba. A pedido, al ver que
la Evolución ya mostraba los dos lados juntos: «esto ya no debería estar, ya
que ahora muestra ambos».

    Requerimientos (requerimientos)    Por período · Por sub almacén (la
                                       cadena de tablas) · Tabla
    Salidas (salidas.parquet)          Por período · Detalle de salidas (los
                                       cinco cuadros) · Tabla
    Porcionamientos                    Porcionamientos (la merma por período)
      (porcionamientos.parquet)

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
(`_cargar_porcionamientos_del_rango`) y lo recorta el chip «Sub Almacén»,
no el de Familia: la consulta no trae la familia. Ver `arquitectura.md`
regla #510.

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
borraron: siguen ahí, completos y documentados, para que volver a colgarlos
de la pila sea una línea. Lo dice también la cabecera de aquel módulo.

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

import pandas as pd
import streamlit as st

from data import cargar as _cargar_reporte
from estilos import TAM_FUENTE
from tablas import renderizar_aggrid_desktop
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills, _render_rail,
    _resolver, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.movimientos_comun import _rango_vigente
# `_ANULADO` y `SALIDAS` son de la tarjeta «Salidas por período»: el
# «Detalle de salidas» suma lo mismo que ella, y dos copias de «qué es una
# salida anulada» —o de cómo se escribe «3 anuladas»— se separan al primer
# retoque.
from graficos.movimientos_periodo import (
    _ANULADO, SALIDAS, orden_areas, tarjeta_porcionamientos_periodo,
    tarjeta_requerimientos_periodo, tarjeta_salidas_periodo,
)
from graficos import drill_tablas

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
    ("Requerimientos", (("Requerimientos por período", "Por período · req.", ":material/calendar_view_week:"),
                        ("Por sub almacén",            "Sub almacén",        ":material/warehouse:"),
                        ("Tabla · requerim.",          "Tabla · req.",       ":material/table_rows:"))),
    # «Detalle de salidas» (2026-09-24, regla #511) ocupa el sitio de «Top
    # productos · salidas», que se retiró ese día. Nombre sin sufijo: no
    # tiene gemela del lado de requerimientos. El ícono es el de un tablero
    # partido en paneles, que es lo que dibuja —cinco cuadros, 3 + 2—.
    ("Salidas", (("Salidas por período", "Por período · sal.", ":material/calendar_view_week:"),
                 ("Detalle de salidas",  "Detalle de salidas", ":material/view_quilt:"),
                 ("Tabla · salidas",     "Tabla · sal.",       ":material/table_view:"))),
    # «Porcionamientos» (2026-09-24, regla #510): tercer grupo, al final, a
    # pedido. Una sola vista, con el nombre que se pidió; el ícono son las
    # tijeras del corte.
    ("Porcionamientos", (("Porcionamientos", "Porcionamientos", ":material/content_cut:"),)),
))

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA tupla
# (el porqué, en `graficos/compras/__init__.py::_PILA`).
#
# Cada lado con sus vistas y su Tabla al final del bloque, igual que
# `recetas.py`. Requerimientos va primero por lo mismo que era el `archivo`
# del reporte: es el lado grande (144.636 filas contra 17.355).
#
# La FECHA ya no la gobierna ninguna sección: el selector de tarjeta vivía en
# la Evolución, que se retiró el 2026-09-13. Manda la píldora de la franja,
# que este reporte sí dibuja (`app.py`: `_franja_dibuja_fecha = reporte !=
# "Compras"`), y las secciones de Salidas la leen con `_rango_vigente()`.
_PILA = pila_sin_tablas((
    ("mov_sec_periodo",     "Requerimientos por período"),
    ("mov_sec_cadena",      "Por sub almacén"),
    ("mov_sec_tabla_req",   "Tabla · requerim."),
    ("mov_sec_sal_periodo", "Salidas por período"),
    ("mov_sec_detalle_sal", "Detalle de salidas"),
    ("mov_sec_tabla_sal",   "Tabla · salidas"),
    ("mov_sec_porc",        "Porcionamientos"),
))


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


_COLS_AREA_SALIDAS = ["AREA", "Area", "SUB ALMACEN", "Sub Almacen"]
"""Cómo se llama el área en `salidas.parquet`. La trae desde el 2026-09-23
su consulta (`vArea.Descripcion` por `MSUBSALIDA.tCodigoArea`, regla #509)
con el nombre `AREA`; «Sub Almacen» es el del demo de `data.py`."""

_FILAS_DETALLE_SAL = ((1.2, 1, 1), (1.2, 2))
"""El reparto de los cinco cuadros de «Detalle de salidas»: tipo de baja,
área y familia arriba; subfamilia y producto abajo. El 1.2 de las dos filas
es el mismo corte —la primera columna termina en el mismo sitio arriba y
abajo, a 2,7px: Streamlit le suma a cada columna su parte del sobrante del
flex, y en la fila de tres la parte es menor (medido a 1366: 538 y 541)—, y
la fila de arriba es la de «Stock por área» (`drill_tablas.
COLUMNAS_NIVELES[3]`). Regla #511."""


def _cargar_salidas_del_rango(col_fam_sal, fam_sel, sub_sel=()):
    """`salidas.parquet` recortado al MISMO rango, familia y área que el
    resto.

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
        return None
    col_fecha = _resolver(df, ["Fecha registro", "FECHA REGISTRO"])
    if not col_fecha:
        return None
    d = df.copy()
    d["_fecha"] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=["_fecha"])
    rango = _rango_vigente()
    if rango:
        _ini, _fin = rango
        d = d[(d["_fecha"] >= _ini) & (d["_fecha"] < _fin)]
    if fam_sel and col_fam_sal and col_fam_sal in d.columns:
        d = d[d[col_fam_sal].astype(str).isin(fam_sel)]
    col_area = _resolver(d, _COLS_AREA_SALIDAS)
    if sub_sel and col_area:
        _elegidas = {str(s).strip() for s in sub_sel}
        d = d[d[col_area].fillna("").astype(str).str.strip().isin(_elegidas)]
    return d


_COLS_PORC = {
    "fecha": "FEC REGIST",
    "doc": "COD PORC",
    "area": "SUB ALMACEN",
    "tipo": "USUARIO REG",
    "prod": "PROD INICIAL",
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


def _cargar_porcionamientos_del_rango(sub_sel=()):
    """`porcionamientos.parquet` recortado al rango de la franja y al chip
    «Sub Almacén», o None si no está o no trae su fecha.

    El borde superior va como `< fin + 1 día` por lo mismo que salidas:
    `FEC REGIST` trae hora (regla #321). EL CHIP «FAMILIA» NO RECORTA ESTA
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
    rango = _rango_vigente()
    if rango:
        _ini, _fin = rango
        d = d[(d["_fecha"] >= _ini) & (d["_fecha"] < _fin)]
    col_area = _resolver(d, _COLS_PORC["area"])
    if sub_sel and col_area:
        _elegidas = {str(s).strip() for s in sub_sel}
        d = d[d[col_area].fillna("").astype(str).str.strip().isin(_elegidas)]
    return d


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_movimientos(df_f, nombre_reporte, df_full=None,
                                    tabla_cb=None):
    """Dashboard de Movimientos. `df_f` es requerimientos.parquet, ya
    filtrado por la fecha de la franja; salidas.parquet se carga acá adentro
    y se recorta al mismo rango.

    `tabla_cb`: callback que arma la Tabla de requerimientos (inyectado por
    app.py — la pivote). La de salidas va por `_tabla_salidas`, ver el
    docstring del módulo.
    """
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
        _, sub_sel = filtro_pills(df_f, col_sub,
                                  "mov_graf_filtro_sub", "Sub Almacén")
        _, fam_sel = filtro_pills(df_f, col_fam,
                                  "mov_graf_filtro_fam", "Familia")

    d = df_f
    if sub_sel and col_sub:
        d = d[d[col_sub].astype(str).isin(sub_sel)]
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    # Ve el lado de REQUERIMIENTOS, que es el `archivo` del reporte: la
    # herramienta de SQL corre sobre un df, y darle el otro parquet sin que
    # lo pida sería contradecir el esquema que ya conoce.
    publicar_contexto_ia("Movimientos", d,
                         {"Sub Almacén": sub_sel, "Familia": fam_sel})

    if d is None or d.empty:
        st.info("No hay datos para los filtros seleccionados.")
        return

    # MÉTRICA FIJA EN VALORIZADO, igual que tenían los dos reportes por
    # separado (Salidas lo fijó el 2026-08-07 a pedido). `col_cant` queda
    # como fallback silencioso por si algún día faltara la columna de valor,
    # pero no hay UI para elegir Cantidad — y no la puede haber barata: las
    # dos mitades cuentan unidades distintas y sumarlas no significa nada.
    col_metrica = col_val or col_cant

    # ── El otro parquet ───────────────────────────────────────────────────
    col_fam_sal = "NOMBRE FAMILIA"
    d_sal = _cargar_salidas_del_rango(col_fam_sal, fam_sel, sub_sel)

    def _col_sal(*nombres):
        return _resolver(d_sal, list(nombres)) if d_sal is not None else None

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
        drill_tablas.seccion_cadena(
            d, pref="mov", slug="subalm",
            niveles=((col_sub, "sub almacén"), (col_fam, "familia"),
                     (col_subfam, "subfamilia")),
            col_val=col_metrica, col_hoja=col_prod,
            col_ctx=col_sub, nombre_ctx="Sub almacén",
            col_cant=col_cant, col_punit=col_punit,
            titulo_ranking="Valorizado requerido por sub almacén")

    def _dib_periodo():
        # La tarjeta abre su propio contenedor (con la key de su familia de
        # tarjetas) y sus grillas: vive entera en su módulo, como las de
        # Compras. La fecha es la de la franja: ya viene recortada en `d`.
        tarjeta_requerimientos_periodo(
            d, orden=orden,
            cols=dict(fecha=col_fecha, doc=col_req, area=col_sub,
                      estado=col_estado, fam=col_fam, prod=col_prod,
                      cant=col_cant, punit=col_punit, val=col_val))

    def _dib_sal_periodo():
        # La MISMA tarjeta sobre salidas (2026-09-23, en lugar de la dona de
        # «Tipo de descargo»): el área que dio de baja parte la barra, y el
        # tipo de descargo queda como filtro y como columna del Detalle. Sin
        # precio unitario en el parquet: lo despeja la tarjeta.
        if d_sal is None:
            with st.container(border=True,
                              key="ajuste_graf_card_izq_mov_sal_vacia"):
                _sin_salidas()
            return
        tarjeta_salidas_periodo(
            d_sal, orden=orden,
            cols=dict(fecha=_col_sal("Fecha registro", "FECHA REGISTRO"),
                      doc=_col_sal("Cod Salida", "COD SALIDA"),
                      area=_col_sal(*_COLS_AREA_SALIDAS),
                      estado=_col_sal("Nombre Estado Salida",
                                      "NOMBRE ESTADO SALIDA"),
                      fam=_col_sal("Nombre Familia", "NOMBRE FAMILIA"),
                      prod=col_prod_sal,
                      cant=_col_sal("Cant Salida", "CANT SALIDA"),
                      val=col_val_sal, tipo=col_tipo))

    def _dib_tabla_req():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_tabla_req"):
            if tabla_cb is not None:
                tabla_cb(d)
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
        if d_sal is None:
            with st.container(border=True, key=vacia):
                _sin_salidas()
            return
        if not (col_val_sal and col_prod_sal):
            with st.container(border=True, key=vacia):
                st.info("No hay columnas suficientes para esta sección.")
            return
        validas, nota = salidas_que_suman(
            d_sal, col_estado=_col_sal("Nombre Estado Salida",
                                       "NOMBRE ESTADO SALIDA"),
            col_prod=col_prod_sal, col_doc=_col_sal("Cod Salida", "COD SALIDA"),
            col_val=col_val_sal)
        if validas.empty:
            with st.container(border=True, key=vacia):
                st.info("Sin salidas en el rango de fechas. Ampliá el rango "
                        "en la franja de arriba.")
            return
        drill_tablas.seccion_cuadros(
            validas, pref="mov", slug="detsal",
            niveles=((col_tipo, "tipo de baja"),
                     (_col_sal(*_COLS_AREA_SALIDAS), "área"),
                     (_col_sal("Nombre Familia", "NOMBRE FAMILIA"), "familia"),
                     (_col_sal("Nombre Subfamilia", "NOMBRE SUBFAMILIA"),
                      "subfamilia"),
                     (col_prod_sal, "producto")),
            filas=_FILAS_DETALLE_SAL, col_val=col_val_sal, nota=nota)

    def _dib_tabla_sal():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_tabla_sal"):
            if d_sal is None:
                _sin_salidas()
            elif d_sal.empty:
                st.info("Ningún registro coincide con los filtros seleccionados.")
            else:
                _tabla_salidas(d_sal)

    def _dib_porc():
        # El tercer parquet se carga ACÁ y no arriba con el de salidas: sólo
        # hace falta cuando esta sección sale del esqueleto (la última de la
        # pila). `data.cargar` lo cachea igual.
        d_porc = _cargar_porcionamientos_del_rango(sub_sel)
        if d_porc is None:
            with st.container(border=True,
                              key="ajuste_graf_card_izq_mov_porc_vacia"):
                st.info("No se pudo cargar porcionamientos.parquet: esta "
                        "sección queda vacía.")
            return
        tarjeta_porcionamientos_periodo(
            d_porc, orden=orden,
            cols={nombre: _resolver(d_porc, columna)
                  for nombre, columna in _COLS_PORC.items()})

    _DIBUJANTES = {
        "mov_sec_periodo":     _dib_periodo,
        "mov_sec_cadena":      _dib_cadena,
        "mov_sec_tabla_req":   _dib_tabla_req,
        "mov_sec_sal_periodo": _dib_sal_periodo,
        "mov_sec_detalle_sal": _dib_detalle_sal,
        "mov_sec_tabla_sal":   _dib_tabla_sal,
        "mov_sec_porc":        _dib_porc,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje.
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
