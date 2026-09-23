"""
graficos.movimientos — dashboard ÚNICO de Movimientos (requerimientos + salidas).

Una sola página con las SEIS vistas de los dos parquets del flujo de stock,
que hasta el 2026-09-05 vivían repartidas en dos reportes que un chip
Requerimiento/Salidas alternaba. A pedido, al ver que la Evolución ya
mostraba los dos lados juntos: «esto ya no debería estar, ya que ahora
muestra ambos».

    Requerimientos (requerimientos)    Por sub almacén (la cadena de tablas)
                                       Top productos · Tabla
    Salidas (salidas.parquet)          Tipo de descargo · Top productos · Tabla

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
esta fusión es esa tarea.

DOS PARQUETS EN UNA PÁGINA. `app.py` carga UNO por reporte y lo pasa como
`df_f`; el segundo se carga acá con `data.cargar`, que es el patrón de
`recetas.py` y de `recetas_comun.py::_cargar_flujo_compras`. `df_f` es el de
REQUERIMIENTOS (el reporte «Movimientos» apunta a requerimientos.parquet):
es el lado grande —144.636 filas contra 17.355—, el que trae Sub Almacén, y
el dueño de la Tabla pivote.

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
NINGUNA descarta hoy los comprobantes ANULADOS. Las dos que sí lo hacían
eran las de «Ambos», que se retiraron el 2026-09-13; las seis que quedan
miran el mismo `d` post-chips, así que el valorizado que dicen es el mismo
en la cadena de tablas, en el Top de productos y en la Tabla pivote. Son
S/ 174.939 de S/ 8.481.700 (2,1%, medido contra R2 el 2026-09-13). No se
cambió acá porque es la conducta que estas seis ya tenían y mover números
que nadie pidió mover es otra decisión; queda anotado en la regla #322.

Punto de entrada público: renderizar_graficos_movimientos().
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import cargar as _cargar_reporte
from estilos import TAM_FUENTE
from tablas import renderizar_aggrid_desktop
from tema import ACENTO
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills,
    PALETA_CALLAI, _compras_layout, _compras_truncar, _render_rail,
    _resolver, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.movimientos_comun import _rango_vigente
from graficos import alturas, drill_tablas

# El rótulo del rail es CORTO a propósito: la franja de Vistas es horizontal
# y aplana las categorías a una sola fila (ver `base.py::_render_rail`), así
# que ocho ítems compiten por el ancho útil de una laptop (~1010px). El
# nombre largo vive en el id — que es lo que viaja en `?vista=` y lo que
# empareja con `_PILA`.
#
# El sufijo « · req.» / « · sal.» es el desambiguador: «Top productos» y
# «Tabla» existían en los dos lados y al juntarlas quedaban dos ítems con el
# mismo nombre.
#
# Las dos «Tabla» están OCULTAS desde el 2026-09-23, con las de los demás
# reportes: `rail_sin_tablas` acá y `pila_sin_tablas` en `_PILA`, de a par
# (regla #507).
_RAIL_CATEGORIAS = rail_sin_tablas((
    # «Por sub almacén» ocupa el sitio que tenían «Evolución», «Proporción
    # dada de baja» y el ranking «Sub Almacén», que se retiraron el
    # 2026-09-13. No hereda el nombre de aquel ranking —que era UN cuadro—
    # porque ahora son cuatro tablas encadenadas: el ítem del rail nombra la
    # cadena, no su primer eslabón.
    ("Requerimientos", (("Por sub almacén",           "Sub almacén",      ":material/warehouse:"),
                        ("Top productos · requerim.", "Top prod. · req.", ":material/format_list_numbered:"),
                        ("Tabla · requerim.",         "Tabla · req.",     ":material/table_rows:"))),
    ("Salidas", (("Tipo de descargo",       "Tipo descargo",    ":material/category:"),
                 ("Top productos · salidas", "Top prod. · sal.", ":material/leaderboard:"),
                 ("Tabla · salidas",         "Tabla · sal.",     ":material/table_view:"))),
))

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA tupla
# (el porqué, en `graficos/compras/__init__.py::_PILA`).
#
# Cada lado con sus vistas y su Tabla al final del bloque, igual que
# `recetas.py`. Requerimientos va primero por lo mismo que era el `archivo`
# del reporte: es el lado grande (144.636 filas contra 17.355) y el único que
# trae Sub Almacén.
#
# La FECHA ya no la gobierna ninguna sección: el selector de tarjeta vivía en
# la Evolución, que se retiró el 2026-09-13. Manda la píldora de la franja,
# que este reporte sí dibuja (`app.py`: `_franja_dibuja_fecha = reporte !=
# "Compras"`), y las secciones de Salidas la leen con `_rango_vigente()`.
_PILA = pila_sin_tablas((
    ("mov_sec_cadena",      "Por sub almacén"),
    ("mov_sec_top_req",     "Top productos · requerim."),
    ("mov_sec_tabla_req",   "Tabla · requerim."),
    ("mov_sec_tipo",        "Tipo de descargo"),
    ("mov_sec_top_sal",     "Top productos · salidas"),
    ("mov_sec_tabla_sal",   "Tabla · salidas"),
))


def _barras_ranking(serie, *, key, titulo, truncar=28):
    """Barras horizontales con el valor al lado — el ranking de siempre.

    Los cuatro rankings de esta página (Sub Almacén y los dos Top productos)
    eran el mismo bloque de 14 líneas copiado en `requerimientos.py` y
    `salidas.py`. Al juntarse en un módulo el copiado se ve, así que va una
    sola vez. Mide SIEMPRE en soles: las dos mitades reportan valorizado (ver
    el comentario de la métrica en el entry point).
    """
    if serie.empty:
        st.info("Sin datos.")
        return
    fig = go.Figure(go.Bar(
        x=serie.values,
        y=[_compras_truncar(i, truncar) for i in serie.index],
        orientation="h",
        marker=dict(color=ACENTO, opacity=0.85),
        text=[f"S/ {v:,.0f}" for v in serie.values],
        textposition="outside", cliponaxis=False,
    ))
    _compras_layout(fig, alto=alturas.PROTAGONISTA)
    fig.update_layout(title=titulo)
    # El eje X se oculta a propósito: el número ya está al lado de la barra.
    fig.update_xaxes(visible=False)
    st.plotly_chart(fig, use_container_width=True, key=key)


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


def _cargar_salidas_del_rango(col_fam_sal, fam_sel):
    """`salidas.parquet` recortado al MISMO rango y familia que el resto.

    Defensivo igual que `recetas.py` con recetabase: si el parquet no está o
    no trae su fecha, las tres secciones de Salidas avisan y el resto de la
    página sigue funcionando.

    El borde superior va como `< fin + 1 día` porque `FECHA REGISTRO` trae
    hora en las 17.101 filas — ver regla #321, que es donde se midió.
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

    if not col_val and not col_cant:
        st.warning("No se encontraron las columnas de cantidad/valor del "
                   "requerimiento. Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Sub Almacén / Familia como chips en la franja ─────────────
    # SUB ALMACÉN es de requerimientos y sólo de ahí: salidas.parquet no trae
    # el área que dio de baja. Las secciones de Salidas lo ignoran, y la
    # Evolución —que compara los dos lados— lo canta en su caption cuando
    # está puesto, porque filtrar un solo lado invalida una comparación.
    # FAMILIA sí existe en los dos, con las mismas seis familias.
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
    _met = pd.to_numeric(d[col_metrica], errors="coerce").fillna(0)

    # ── El otro parquet ───────────────────────────────────────────────────
    col_fam_sal = "NOMBRE FAMILIA"
    d_sal = _cargar_salidas_del_rango(col_fam_sal, fam_sel)
    col_tipo = _resolver(d_sal, ["Tipo Descargo", "TIPO DESCARGO"]) if d_sal is not None else None
    col_prod_sal = _resolver(d_sal, ["Nombre Producto", "NOMBRE PRODUCTO"]) if d_sal is not None else None
    col_val_sal = _resolver(d_sal, ["Valor Neto", "VALOR NETO"]) if d_sal is not None else None
    _met_sal = (pd.to_numeric(d_sal[col_val_sal], errors="coerce").fillna(0)
                if (d_sal is not None and col_val_sal) else None)

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

    def _dib_top_req():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_top_req"):
            if not col_prod:
                st.info("No hay columnas suficientes para este gráfico.")
                return
            _barras_ranking(
                _met.groupby(d[col_prod].astype(str)).sum().nlargest(10).sort_values(),
                key="mov_g_top_req", truncar=34,
                titulo="Top 10 productos por valorizado requerido")

    def _dib_tabla_req():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_tabla_req"):
            if tabla_cb is not None:
                tabla_cb(d)
            else:
                st.info("La tabla no está disponible en este contexto.")

    def _dib_tipo():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_tipo"):
            if d_sal is None:
                _sin_salidas()
                return
            if not col_tipo or _met_sal is None:
                st.info("No hay columnas suficientes para este gráfico.")
                return
            serie = (_met_sal.groupby(d_sal[col_tipo].astype(str)).sum()
                     .sort_values(ascending=False))
            if serie.empty:
                st.info("Sin datos.")
                return
            fig = go.Figure(go.Pie(
                labels=serie.index, values=serie.values, hole=0.45,
                marker=dict(colors=PALETA_CALLAI * 4),
                textinfo="label+percent",
                hovertemplate=("%{label}<br>S/ %{value:,.2f} "
                               "(%{percent})<extra></extra>"),
            ))
            _compras_layout(fig, alto=alturas.PROTAGONISTA)
            fig.update_layout(
                title="Participación del valorizado dado de baja por tipo de descargo",
                showlegend=False)
            st.plotly_chart(fig, use_container_width=True, key="mov_g_tipo")

    def _dib_top_sal():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_top_sal"):
            if d_sal is None:
                _sin_salidas()
                return
            if not col_prod_sal or _met_sal is None:
                st.info("No hay columnas suficientes para este gráfico.")
                return
            _barras_ranking(
                _met_sal.groupby(d_sal[col_prod_sal].astype(str)).sum()
                        .nlargest(10).sort_values(),
                key="mov_g_top_sal", truncar=34,
                titulo="Top 10 productos por valorizado dado de baja")

    def _dib_tabla_sal():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_tabla_sal"):
            if d_sal is None:
                _sin_salidas()
            elif d_sal.empty:
                st.info("Ningún registro coincide con los filtros seleccionados.")
            else:
                _tabla_salidas(d_sal)

    _DIBUJANTES = {
        "mov_sec_cadena":      _dib_cadena,
        "mov_sec_top_req":     _dib_top_req,
        "mov_sec_tabla_req":   _dib_tabla_req,
        "mov_sec_tipo":        _dib_tipo,
        "mov_sec_top_sal":     _dib_top_sal,
        "mov_sec_tabla_sal":   _dib_tabla_sal,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje.
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
