"""
graficos.movimientos — dashboard ÚNICO de Movimientos (requerimientos + salidas).

Una sola página con las OCHO vistas que hasta el 2026-09-05 vivían repartidas
en dos reportes que un chip Requerimiento/Salidas alternaba. A pedido, al ver
que la Evolución ya mostraba los dos lados juntos: «esto ya no debería estar,
ya que ahora muestra ambos».

    Ambos                              Evolución · Proporción dada de baja
    Requerimientos (requerimientos)    Sub Almacén · Top productos · Tabla
    Salidas (salidas.parquet)          Tipo de descargo · Top productos · Tabla

POR QUÉ ERAN DOS Y AHORA SON UNA. La separación tenía sentido mientras cada
lado contestaba sólo por lo suyo. Dejó de tenerlo el 2026-09-05, cuando la
Evolución pasó a dibujar requerido y baja en la misma figura (regla #320): a
partir de ahí el chip pedía elegir un lado en una página cuyo primer gráfico
ya mostraba los dos. Es el mismo movimiento —y el mismo pedido, casi con las
mismas palabras— que fusionó Receta Base y Receta Venta el 2026-09-04; ver
`graficos/recetas.py` y la regla #303.

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
las dos vistas de «Ambos» descartan los comprobantes ANULADOS —lo hacen
desde que nacieron, y lo dicen en su caption— y las seis de un solo lado no.
Es la conducta que ya tenían por separado y no se cambió acá para no mover
números que nadie pidió mover; queda anotado como pendiente en la regla #322.

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
    _resolver, publicar_contexto_ia, renderizar_graficos_genericos,
    seccion_perezosa,
)
from graficos.movimientos_comun import (
    _evolucion_movimientos, _ranking_proporcion_baja, _rango_vigente,
)
from graficos import alturas

# El rótulo del rail es CORTO a propósito: la franja de Vistas es horizontal
# y aplana las categorías a una sola fila (ver `base.py::_render_rail`), así
# que ocho ítems compiten por el ancho útil de una laptop (~1010px). El
# nombre largo vive en el id — que es lo que viaja en `?vista=` y lo que
# empareja con `_PILA`.
#
# El sufijo « · req.» / « · sal.» es el desambiguador: «Top productos» y
# «Tabla» existían en los dos lados y al juntarlas quedaban dos ítems con el
# mismo nombre.
_RAIL_CATEGORIAS = (
    # La segunda se llamó «Pedido vs Baja» y después «Diferencias por
    # producto», las dos veces el mismo día (2026-09-05). El primer nombre
    # describía la vista cuando abría con una evolución requerido-vs-baja
    # —que es la sección de al lado, o sea el rail decía dos veces lo
    # mismo—; el segundo, cuando el ranking todavía iba por la RESTA. Hoy
    # va por el cociente y el nombre dice eso. Ver regla #323.
    ("Ambos", (("Evolución",                "Evolución"),
               ("Proporción dada de baja",  "Proporción"))),
    ("Requerimientos", (("Sub Almacén",               "Sub Almacén"),
                        ("Top productos · requerim.", "Top prod. · req."),
                        ("Tabla · requerim.",         "Tabla · req."))),
    ("Salidas", (("Tipo de descargo",       "Tipo descargo"),
                 ("Top productos · salidas", "Top prod. · sal."),
                 ("Tabla · salidas",         "Tabla · sal."))),
)

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA tupla
# (el porqué, en `graficos/compras/__init__.py::_PILA`).
#
# Las dos de «Ambos» van PRIMERO: son la razón de que esta página sea una
# sola, y la Evolución es además la que trae el selector de fecha que manda
# sobre todo lo demás. Después cada lado con sus vistas y su Tabla al final
# del bloque, igual que `recetas.py`.
_PILA = (
    ("mov_sec_evolucion",   "Evolución"),
    ("mov_sec_proporcion",  "Proporción dada de baja"),
    ("mov_sec_subalmacen",  "Sub Almacén"),
    ("mov_sec_top_req",     "Top productos · requerim."),
    ("mov_sec_tabla_req",   "Tabla · requerim."),
    ("mov_sec_tipo",        "Tipo de descargo"),
    ("mov_sec_top_sal",     "Top productos · salidas"),
    ("mov_sec_tabla_sal",   "Tabla · salidas"),
)


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
    col_cant = _resolver(df_f, ["Cantidad", "CANTIDAD"])
    col_val = _resolver(df_f, ["Valor Item", "VALOR ITEM", "Valorizado"])

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
    # abajo. El caption de la Evolución dice exactamente lo mismo ("En el
    # período: S/ X requerido · S/ Y dado de baja · baja/requerido Z%"),
    # pegado al gráfico que los explica, que es donde se leen bien.
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
    def _dib_evolucion():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_evolucion"):
            _evolucion_movimientos(fam_sel=fam_sel, sub_sel=sub_sel)

    def _dib_proporcion():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_proporcion"):
            # Hereda la familia como todo lo demás de la página: desde que
            # los dos parquets se cargan y recortan acá, un filtro propio
            # sólo agregaba una segunda fecha que contradecía a la de
            # arriba (regla #323).
            _ranking_proporcion_baja(key_prefix="mov_prop", fam_sel=fam_sel)

    def _dib_subalmacen():
        with st.container(border=True, key="ajuste_graf_card_izq_mov_subalmacen"):
            if not col_sub:
                st.info("No hay columnas suficientes para este gráfico.")
                return
            _barras_ranking(
                _met.groupby(d[col_sub].astype(str)).sum().sort_values(),
                key="mov_g_subalmacen",
                titulo="Valorizado requerido por sub almacén")

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
        "mov_sec_evolucion":   _dib_evolucion,
        "mov_sec_proporcion":  _dib_proporcion,
        "mov_sec_subalmacen":  _dib_subalmacen,
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
