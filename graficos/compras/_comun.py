"""graficos.compras._comun - helpers compartidos por los drills de Compras.

Cosas chicas que usan dos o mas drills: deteccion de movil, lectura de
la seleccion de un plotly_chart, mini barras horizontales y etiquetas de
periodo segun granularidad.

Y la GRILLA (`COLUMNAS_DRILL` / `GAP_DRILL`): la proporcion con la que parte
en dos una fila de un drill. Vive aca y no en cada modulo porque el eje
vertical tiene que caer en el mismo sitio en TODAS las filas de una vista.
"""

import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, TEXTO_PRINCIPAL
from graficos.base import _compras_truncar, _slug
# REEXPORT, no import muerto: `_es_movil` vivía definida acá y se movió a
# graficos/base.py (2026-08-07, ver su docstring) porque graficos/ajuste.py
# la necesitó también. Este import la reexpone bajo el mismo nombre, así que
# proveedor.py y compras/__init__.py siguen haciendo
# `from graficos.compras._comun import _es_movil` sin enterarse. Este módulo
# NO la usa, de ahí el noqa: sin él, `ruff --fix` la borraría y rompería a
# sus dos consumidores.
from graficos.base import _es_movil  # noqa: F401
from graficos import alturas


# ===========================================================================
# LA GRILLA: UNA SOLA PROPORCIÓN POR VISTA
# ===========================================================================
# Hermana de `tema.py` (dueño del color) y `alturas.py` (dueño del alto): el
# EJE VERTICAL de una vista tampoco puede escribirse a mano en cada fila.
#
# POR QUÉ EXISTE (2026-08-21). El drill de Proveedor tenía dos filas de dos
# columnas y cada una partía en un sitio distinto: la de arriba con
# `st.columns([1.6, 1])` (61.5%) y la de abajo con `st.columns(2)` (50%). Con
# ~1750px de ancho útil eso son ~200px de salto — el canal gris que baja entre
# las columnas se cortaba a media página y la vista dejaba de leerse como una
# grilla. No lo cazaba nada: los dos números son correctos por separado.
#
# La regla: la proporción que parte una FILA de un drill sale de acá. Las
# subdivisiones DENTRO de una tarjeta (el chart y su pila de KPIs, una
# botonera) son otra cosa y siguen siendo literales — se marcan con un
# comentario `# columnas-internas: <por qué>` y `test_graficos.py` las
# distingue por esa marca.
COLUMNAS_DRILL = [1.6, 1]
"""Proporción izq./der. de una fila de dos columnas en un drill de Compras.

1.6/1 y no 1/1: la columna izquierda lleva siempre la tabla con nombres
largos (proveedores, productos) y la derecha un panel de apoyo. La grilla de
4 métricas del Panel B ya colapsa sola a 2x2 en anchos chicos
(`@container pbcard (max-width: 460px)` en `_css_proveedor.py`), así que
angostarla es seguro.

Ojo con lo que ese 1 significa en píxeles: medido con datos reales, el Panel
B mide 289px en una pantalla de 1280 y 535px en una de 1920. Cualquier cosa
que reaccione al ancho de ESE panel se consulta por `@container`, no por
`@media` — el viewport no distingue esos dos casos. Ver regla #317."""

COLUMNAS_COTEJO = [1, 1]
"""Proporción de una fila que COMPARA dos fuentes, no que parte una tabla
de su panel de apoyo.

`COLUMNAS_DRILL` es 1.6/1 porque su izquierda lleva siempre una tabla con
nombres largos y su derecha un panel que la acompaña — hay una jerarquía.
En una comparación no la hay: los dos lados son pares y cualquier
asimetría se lee como que uno importa más. Se estrenó el 2026-08-28 en
«Documentos SUNAT», cuando la ficha del comprobante pasó de ser una
tarjeta con cuatro columnas (campo | SUNAT | sistema | Δ) a DOS tarjetas
hermanas, a pedido.

Existe como constante y no como `st.columns(2)` suelto por lo mismo que
`COLUMNAS_DRILL`: el conversor de ese mismo drill parte sus dos mitades
por la mitad, y si una fila comparara 1.6/1 y la otra 1/1, el eje
vertical de la página se correría a media pantalla — que es exactamente
el bug que hizo nacer la regla #145."""

GAP_DRILL = "small"
"""Gap entre las columnas de un drill. Va con `COLUMNAS_DRILL`: si las dos
filas parten en el mismo sitio pero con gaps distintos, el canal gris cambia
de ancho a media página y el salto se ve igual."""

PARR = "\n\n"
"""Salto de párrafo para el markdown de un popover de ayuda.

Vivía en `vs_ano_pasado.py` hasta el 2026-09-07, cuando «Volatilidad»
estrenó el suyo (el mismo popover de sólo ícono). Dos cadenas iguales
escritas en dos módulos no driftean solas, pero el CRITERIO sí: si
mañana el popover pasa a separar con `---`, cambia en un sitio."""


def _first_point(evt):
    """Primer punto de una selección de st.plotly_chart(on_select=...).
    Devuelve el dict del punto o None (tolerante a formatos/errores)."""
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        pts = (sel or {}).get("points", [])
        return pts[0] if pts else None
    except Exception:
        return None


def _compras_mini_barras(serie, titulo, fmt="S/ {:,.0f}", alto=alturas.APOYO):
    """Mini gráfico de barras horizontales top-N (mayor arriba)."""
    if serie is None or serie.empty:
        st.info("Sin datos para este top.")
        return
    d = serie.sort_values(ascending=True)
    fig = go.Figure(go.Bar(
        x=d.values,
        y=[_compras_truncar(i) for i in d.index],
        orientation="h",
        marker=dict(color=ACENTO, opacity=0.85),
        text=[fmt.format(v) for v in d.values],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=alto,
        margin=dict(l=4, r=40, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True,
                    key=f"compras_mini_{_slug(titulo)}")


def _periodo_serie(fe, gran):
    """Serie de etiquetas de periodo (ordenables) según granularidad."""
    if gran == "Día":
        return fe.dt.strftime("%Y-%m-%d")
    if gran == "Semana":
        iso = fe.dt.isocalendar()
        return (iso["year"].astype("Int64").astype(str) + "-S"
                + iso["week"].astype("Int64").astype(str).str.zfill(2))
    if gran == "Año":
        return fe.dt.year.astype("Int64").astype(str)
    return fe.dt.to_period("M").astype(str)  # Mes


# ===========================================================================
# EL SELECTOR DE FECHA DE UNA TARJETA — vive en graficos/base.py
# ===========================================================================
# Nació dentro del Ranking de Proveedores (2026-08-23 → 08-26, cuatro vueltas
# de pedido), se mudó ACÁ el 2026-08-26 cuando lo pidió el Ranking de
# Productos, y SUBIÓ a `graficos/base.py` el 2026-09-05, cuando lo pidió la
# Evolución de Movimientos ("un selector de fecha, igual que el ranking de
# proveedores"). Tercera vez que un tercero lo pide: el criterio no cambió,
# cambió el alcance — ya no es un helper de Compras, es del proyecto, y vive
# al lado de `selector_escala`, que es la pieza que abre adentro.
#
# REEXPORT, no import muerto: `proveedor.py`, `producto.py` y `semanal.py`
# siguen haciendo `from graficos.compras._comun import selector_fecha_tarjeta`
# sin enterarse de la mudanza. Mismo patrón —y mismo `noqa`— que `_es_movil`
# acá arriba: sin él, `ruff --fix` lo borra y rompe a sus tres importadores.
from graficos.base import selector_fecha_tarjeta  # noqa: F401


def filtro_proveedores(clave, provs_ordenados, pie=None):
    """Filtro de proveedores para una tarjeta de Compras.

    Devuelve `(seleccion, dibujar)`:

    · `seleccion` es la lista de proveedores marcados (o TODOS los reales si
      el usuario destildó hasta el último — el default y el fallback tienen
      que decir lo mismo, o "limpiar" cambiaría el default).
    · `dibujar` es un CALLABLE para el hook `extra=` de
      `selector_fecha_tarjeta`, que lo mete en la fila del título.

    Los dos por separado a propósito: la selección se LEE temprano, para
    armar la figura y el ranking, y el popover se DIBUJA tarde, dentro de la
    tarjeta. Es el patrón de UN rerun que ya usaba cuando flotaba, y no
    cambia por mudarse de sitio.

    Nació el 2026-09-02 extrayendo el popover que vivía inline en
    `proveedor.py`, al pedirse el mismo control para el Ranking de Productos
    ("añadamos el de proveedor"). Copiarlo hubiera sido duplicar ~100 líneas
    y, peor, dos sitios donde arreglar el próximo detalle — el mismo
    argumento que ya había traído acá a `selector_fecha_tarjeta`.

    `clave` es el prefijo de TODAS las keys, así que las dos vistas
    coexisten en la página apilada sin chocar. El CSS de cada prefijo se
    lista EXPLÍCITO en `_css_proveedor.py`: nada de wildcards por familia
    (ver el aviso de CLAUDE.md).

    `pie` es un callable opcional que se dibuja al final del panel; hoy lo
    usa Proveedor para su toggle "Nombres en barras", que es de esa vista y
    no del filtro.
    """
    reales = [p for p in provs_ordenados if p != "Otros"]
    # Por defecto se muestran TODOS los del rango, no los N más grandes: la
    # lista sale de un `d` ya filtrado por fecha, así que "todos" significa
    # "todos los que compraron en el período" y cambia sólo con la fecha.
    # "Otros" arranca DESTILDADO: no es un proveedor, agrupa a los que
    # quedaron fuera del top, y encenderlo por defecto metería una fila
    # que no se puede enfocar.
    for _p in provs_ordenados:
        _k = f"{clave}_cb::{_p}"
        if _k not in st.session_state:
            st.session_state[_k] = (_p in reales)

    def _set_topn(_n):
        """Marca sólo los primeros _n proveedores (por valor). _n=0 → limpiar."""
        for _pp in provs_ordenados:
            st.session_state[f"{clave}_cb::{_pp}"] = (_pp in reales[:_n])

    seleccion = [p for p in provs_ordenados
                 if st.session_state.get(f"{clave}_cb::{p}")] or reales

    def dibujar():
        with st.container(key=f"{clave}_pop_float"):
            _sel_now = [p for p in provs_ordenados
                        if st.session_state.get(f"{clave}_cb::{p}")]
            # El número va como badge por CSS var (un `::after` lo pinta).
            # Sin cuenta → badge vacío. La var vive scopeada al contenedor.
            st.markdown(
                f"<style>.st-key-{clave}_pop_float "
                f"{{ --cp-prov-count: '{len(_sel_now)}'; }}</style>",
                unsafe_allow_html=True,
            )
            with st.popover("Proveedores", icon=":material/groups:"):
                # Panel COMPACTO. El detalle de por qué cada pieza es como
                # es —los 175px de aire que se midieron antes de tocarlo, el
                # `st.columns(5)` que imponía 382px de ancho, el
                # `st.divider()` de 49— está en arquitectura.md regla #272.
                # columnas-internas: botonera del popover, no el eje de la vista.
                with st.container(horizontal=True, gap="small",
                                  key=f"{clave}_atajos"):
                    st.button("Top 3", key=f"{clave}_topn3", type="tertiary",
                              on_click=_set_topn, args=(3,))
                    st.button("5", key=f"{clave}_topn5", type="tertiary",
                              on_click=_set_topn, args=(5,))
                    st.button("10", key=f"{clave}_topn10", type="tertiary",
                              on_click=_set_topn, args=(10,))
                    st.button("Todos", key=f"{clave}_topnall", type="tertiary",
                              on_click=_set_topn, args=(len(reales),))
                    st.button("Ninguno", key=f"{clave}_topnclr", type="tertiary",
                              on_click=_set_topn, args=(0,))
                _q = st.text_input("Buscar", key=f"{clave}_q",
                                   placeholder="Buscar proveedor...",
                                   label_visibility="collapsed").strip().lower()
                _vistos = [p for p in provs_ordenados
                           if not _q or _q in str(p).lower()]
                if not _vistos:
                    st.caption("Sin coincidencias.")
                # La lista scrollea DENTRO en vez de estirar el panel, y su
                # alto es dinámico: `st.container(height=N)` reserva N aunque
                # haya dos filas. NO son N filas iguales — los proveedores
                # son razones sociales completas y ENVUELVEN. Medido clonando
                # filas reales en los 200px de texto útil del panel: 1 línea =
                # 24px, 2 = 30, 3 = 45 (~15 por línea + 9 de caja). 190 es el
                # techo: por encima el panel vuelve a comerse media pantalla.
                _CHARS_LINEA = 30      # a 12px en 200px de ancho útil, medido
                _alto_lista = min(190, sum(
                    (-(-len(str(_p)) // _CHARS_LINEA) or 1) * 15 + 13
                    for _p in _vistos) or 28)
                with st.container(height=_alto_lista, border=False,  # alto-fijo-justificado: líneas x px de la lista, no una resta contra la pantalla
                                  key=f"{clave}_lista"):
                    for _p in _vistos:
                        # `width="stretch"`: el default de `st.checkbox` es
                        # `content`, o sea la fila —y con ella el área
                        # clicable— medía lo que el nombre. En una lista, la
                        # fila entera tiene que ser el blanco.
                        st.checkbox(_p, key=f"{clave}_cb::{_p}",
                                    width="stretch")
                if pie is not None:
                    pie()

    return seleccion, dibujar
