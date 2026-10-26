"""
graficos.ventas_platos — vista «Análisis de platos» del dashboard de Ventas:
el ranking de platos entre hasta cuatro períodos, con su movimiento de puesto.

Nació el 2026-09-25 (regla #529) como el reemplazo del «Top platos
vendidos» que se quitó del Resumen (#528): aquél eran ocho barras de UN
período; éste compara hasta cuatro —de un corte que abre en Mes y puede ser
Día, Semana o Año—, dentro de toda la carta, un grupo o un subgrupo, con el
top, todos los platos o los que el usuario elige a mano.

UNA TARJETA, DOS VISTAS (2026-09-29, regla #569): el interruptor del renglón
del título alterna este ranking y la Ingeniería de menú (popularidad ×
margen, `ventas_menu.py`, regla #550), que hasta ese día era una segunda
tarjeta debajo. Las dos comparten la fila del Corte y las pastillas de los
períodos —la Ingeniería clasifica el último elegido—, que no se mueven al
cambiar de vista; lo demás es de cada una y se dibuja sólo con la suya, con
`persist_state="page"` para que vuelva como quedó.

DE DÓNDE SALEN LOS DATOS: como en «Año Pasado», cada período se trae con
`data.cargar_rango` y pasa por `filtrar_cb` (el `_filtrar_items` de
`ventas.py`: los chips de la franja, un ítem una vez y sólo venta). El `d`
de la franja no alcanza: con el rango por defecto —un mes— pedir trece meses
mostraría uno. El calendario de los períodos es el de «Año Pasado»
(`ventas_comparativo`) con el Año, que allá no existe (`_claves_hacia_atras`,
`_rango_de_clave`, `_etiqueta_clave`, acá abajo): hasta el 2026-10-22 vivía
en `ventas_horario`, que lo usaba para los paneles del mapa viejo (#704).

TRES COSAS QUE NO SON OBVIAS:

  · EL PUESTO SE CALCULA DENTRO DEL ÁMBITO: «3º de Fondos», no «3º de la
    carta». Con empates, el puesto más alto para los dos (`method="min"`),
    como en cualquier tabla de posiciones.
  · LA VARIACIÓN ES POR DÍA: un mes en curso tiene menos días que uno
    entero, y en soles saldría rojo sin que nada haya pasado. Se divide por
    los días CON VENTA de cada período. Y el título dice lo mismo para el
    ámbito entero: con esa vara se mide cada plato.
  · LOS CLICS SE LEEN ARRIBA (regla #399), con contador en la key, como en
    «Mix de carta»: el gráfico de puestos y la tabla eligen el plato cuya
    evolución se muestra abajo.
"""

from graficos.movil import css_movil, js_movil
import datetime as _dt
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from data import REPORTES, cargar_rango, rango_fechas
from tema import (PALETA_SERIES)
from graficos.base import (_resolver,
                           preservar_widgets, scroll_a_seccion)
from graficos.ventas_comparativo import (
    _claves_hacia_atras as _claves_cmp, _etiqueta_clave as _etiqueta_cmp,
    _rango_de_clave as _rango_cmp)
from graficos import ventas_menu as _menu
from graficos.ventas_menu import _KEYS_WIDGET_MENU
# `_estilo_costo` ya no se usa acá (la tabla es de la pieza, regla #699), pero
# test_graficos.py::_pruebas_ventas_platos verifica que sea la del Mix.
from graficos.ventas_mix import _estilo_costo, base, columnas, pct_costo  # noqa: F401
from graficos.ventas_resumen import _COSTO_ALTO, _COSTO_ROTO

CORTES = ("Día", "Semana", "Mes", "Año")
_CORTE_DEFAULT = "Mes"
_N_PERIODOS = {"Día": 14, "Semana": 10, "Mes": 13}
"""Cuántos períodos ofrece cada corte hacia atrás. Trece meses y no doce: así
el mismo mes del año pasado está en la lista. Año ofrece todos los años con
dato."""

VISTAS = ("Ranking", "Ingeniería de menú")
_VISTA_DEFAULT = VISTAS[0]

MAX_PERIODOS = 4
_N_DEFECTO = 3
_MEDIDAS = ("Venta", "Unidades")
TODA_LA_CARTA = "Toda la carta"
_MOSTRAR = ("Top 10", "Top 15", "Top 20", "Todos", "Elegidos")
_MOSTRAR_DEFAULT = "Top 15"
_TOPE_GRAFICO = 20
"""Con «Todos» la tabla lista cada plato del ámbito; el gráfico de puestos se
queda con los 20 primeros: 300 líneas no se leen."""

FILA_RANKING = (2.0, 1.35, 3.15, 2.3)
FILA_MENU = (2.0, 1.9, 4.85, 0.05)
"""La fila de controles de cada vista: el Corte y, a su derecha, Medida ·
Mostrar · Ámbito en el ranking, Forma · Categoría en la Ingeniería. Suman lo
mismo y abren con el mismo número a propósito: el Corte, que es de las dos,
no cambia de ancho ni de lugar al cambiar de vista (lo que se toca no se
mueve, regla #465). Las proporciones son los anchos medidos a 1366 (199,
133, 313 y ~230 px), para que cada control entre en su columna.

Y las dos tienen CUATRO columnas, aunque la Ingeniería use tres: la cuarta
va con un `st.empty()`. Con tres, el desplegable del Ámbito quedaba en la
Ingeniería como un resto a lo ancho de la tarjeta (visto una vez de tres):
Streamlit borra lo que una corrida no volvió a dibujar SÓLO si la corrida
termina limpia (`clearStaleNodes`, con FINISHED_SUCCESSFULLY), y si otra
corrida la corta —la precarga de las secciones vecinas— el resto se queda
hasta el próximo clic en la tarjeta. Escribir la posición la reemplaza
siempre (regla #569)."""

_KEYS_WIDGET_PL = ("vt_pl_vista", "vt_pl_corte", "vt_pl_per_*") + _KEYS_WIDGET_MENU
"""Los controles de la tarjeta —también los de la Ingeniería de menú, que se
dibuja en este mismo fragment—, para que el salto a «Por hora»
(`st.rerun(scope="app")`) no se los lleve (regla #373)."""

_COLORES_ELEGIDOS = tuple(PALETA_SERIES)
MAX_ELEGIDOS = len(_COLORES_ELEGIDOS)
_SALTO = 3
"""Puestos que tiene que subir o bajar un plato para pintarse verde o rojo."""


# ===========================================================================
# LAS CUENTAS (puras: las prueba test_graficos.py)
# ===========================================================================

def _claves_hacia_atras(ancla, grano, n):
    """Las `n` claves de período que terminan en el período de `ancla`."""
    if grano == "Año":
        return list(range(ancla.year - n + 1, ancla.year + 1))
    return _claves_cmp(ancla, grano, n)


def _rango_de_clave(clave, grano):
    """(primer_día, último_día) del período."""
    if grano == "Año":
        return _dt.date(clave, 1, 1), _dt.date(clave, 12, 31)
    return _rango_cmp(clave, grano)


def _etiqueta_clave(clave, grano):
    """Etiqueta corta del período: «Ago 26», «2025»."""
    return str(clave) if grano == "Año" else _etiqueta_cmp(clave, grano)


def periodos(corte, ancla, primer_dia):
    """Las claves de período que ofrece `corte`, cronológicas, hasta la de
    `ancla` (el último día con dato)."""
    if corte == "Año":
        return list(range(primer_dia.year, ancla.year + 1))
    return _claves_hacia_atras(ancla, corte, _N_PERIODOS[corte])


def puestos(valores):
    """Puesto de cada plato (Series nombre → valor): 1 el que más, empates
    con el mismo puesto (el más alto de los dos). Sin venta, sin puesto."""
    v = valores[valores > 0]
    return v.rank(ascending=False, method="min").astype(int)


def movimiento(p0, p1):
    """`(texto, tipo)` del cambio de puesto entre el primer y el último
    período. `tipo` ∈ entra, sale, sube, baja, igual."""
    if not p0 and p1:
        return "entra", "entra"
    if p0 and not p1:
        return "sale", "sale"
    if not p0 and not p1:
        return "—", "igual"
    d = int(p0) - int(p1)
    if d > 0:
        return f"▲ {d}", "sube" if d >= _SALTO else "igual"
    if d < 0:
        return f"▼ {-d}", "baja" if -d >= _SALTO else "igual"
    return "=", "igual"


def var_por_dia(v0, d0, v1, d1):
    """Variación de la venta POR DÍA entre dos períodos, o None sin base."""
    a = v0 / d0 if d0 else 0.0
    b = v1 / d1 if d1 else 0.0
    return (b - a) / a if a else None


_SUMAS = ["venta", "cant", "costo", "neto"]


def agregar(b):
    """Por plato: grupo, subgrupo, venta, unidades, costo, neto y en cuántos
    pedidos aparece, de un período (`b` es la `base` de `ventas_mix`, con la
    columna `pedido` que le suma `_cargar_periodo`). Agrupa por columnas de
    verdad (regla #481). Sin la columna —el modo demo—, `pedidos` es NaN."""
    claves = ["prod", "grupo", "sub"]
    if b is None or b.empty:
        return pd.DataFrame(columns=claves + _SUMAS + ["pedidos"])
    a = b.groupby(claves, as_index=False)[_SUMAS].sum()
    if "pedido" in b.columns:
        ped = (b.groupby(claves, as_index=False)["pedido"].nunique()
               .rename(columns={"pedido": "pedidos"}))
        return a.merge(ped, on=claves, how="left")
    return a.assign(pedidos=np.nan)


def costo_por_plato(a):
    """El % de costo de cada plato (Series nombre → costo ÷ neto) en un
    agregado de `agregar` indexado por plato: la cuenta del Resumen y del Mix
    (`ventas_mix.pct_costo`, regla #546). Suma antes por nombre: un plato
    que cambió de subgrupo a mitad del período sale en dos filas."""
    if a is None or a.empty:
        return pd.Series(dtype=float)
    cn = a.groupby(level=0)[["costo", "neto"]].sum()
    return pct_costo(cn["costo"], cn["neto"])


def opciones_ambito(todos):
    """Las opciones del desplegable del ámbito, `{rótulo: (columna, valor)}`:
    toda la carta —`(None, None)`—, cada grupo y cada subgrupo, cada tanda de
    la que más vende a la que menos. Uno solo en vez de «Grupo | Subgrupo» y
    un segundo desplegable con cuál (2026-09-29, regla #569): el tipo va en
    el rótulo («Subgrupo: Fondos»), que además separa un grupo de un
    subgrupo que se llamen igual. `todos` trae `grupo`, `sub` y `venta`."""
    ops = {TODA_LA_CARTA: (None, None)}
    if todos is None or todos.empty:
        return ops
    for col, rot in (("grupo", "Grupo"), ("sub", "Subgrupo")):
        orden = todos.groupby(col)["venta"].sum().sort_values(ascending=False)
        ops.update({f"{rot}: {v}": (col, v) for v in orden.index})
    return ops


# ===========================================================================
# LOS DATOS
# ===========================================================================

def _cargar_periodo(clave, corte, ancla, filtrar_cb, d_demo):
    """`(agregado por plato, días con venta)` de un período."""
    ini, fin = _rango_de_clave(clave, corte)
    fin = min(fin, ancla)
    cfg = REPORTES.get("Ventas", {})
    df = cargar_rango(cfg.get("archivo", "ventas.parquet"),
                      cfg.get("carga_por_rango", "FEC REG DOCUMENTO"), ini, fin)
    if df is None or df.empty:
        df = d_demo
    elif filtrar_cb is not None:
        df = filtrar_cb(df)
    if df is None or df.empty:
        return agregar(None), 0
    b = base(df, columnas(df))
    # En cuántos pedidos aparece cada plato (la Ingeniería de menú muestra
    # los pedidos al lado de las unidades, #550). `base` conserva el índice
    # de `df`, así que la llave se alinea sola.
    col_ped = _resolver(df, ["Llave Local Pedido", "Nro Pedido",
                             "Numero Pedido"])
    if col_ped:
        b = b.assign(pedido=df[col_ped].reindex(b.index))
    # El recorte se re-aplica en pandas: en modo demo el loader devuelve el
    # df entero (mismo motivo que `ventas_comparativo._cargar_tramo`).
    b = b[(b["fecha"].dt.date >= ini) & (b["fecha"].dt.date <= fin)]
    return agregar(b), int(b["fecha"].dt.normalize().nunique())


def _etiqueta(clave, corte):
    return _etiqueta_clave(clave, corte)


# ===========================================================================
# LOS CLICS (regla #399): se leen arriba, con un contador en la key
# ===========================================================================

def _key(base_key):
    return f"{base_key}_{st.session_state.get('_' + base_key + '_n', 0)}"


def _clic(base_key, extraer):
    valor = extraer(st.session_state.get(_key(base_key)))
    if valor is not None:
        _n = "_" + base_key + "_n"
        st.session_state[_n] = st.session_state.get(_n, 0) + 1
    return valor


def _fila(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _ir_a_hora(nombre):
    """«Ver a qué hora se vende»: deja pedido el plato para «Análisis por
    hora», que lo abre en «Qué se vende a cada hora» (`ventas_horario._K_IR`,
    regla #704), y marca el salto. El salto necesita una corrida COMPLETA
    —es otra sección, con su propio fragment— y el scroll va en la corrida
    siguiente a ésa (ver `_ventas_platos`)."""
    ss = st.session_state
    ss["_vh_ir"] = nombre
    ss["_vt_pl_ir_hora"] = 1


# ===========================================================================
# LA VISTA
# ===========================================================================

@st.fragment
def _ventas_platos(d, filtrar_cb=None):
    """«Análisis de platos»: UNA tarjeta con dos vistas —el ranking de
    platos entre hasta 4 períodos y la Ingeniería de menú del último— que
    alterna el interruptor de su renglón del título (regla #569)."""
    ss = st.session_state
    # El salto a «Por hora», en dos pasos: una corrida completa para que esa
    # sección se redibuje con la ficha pedida, y en ESA corrida el scroll.
    if ss.get("_vt_pl_ir_hora") == 1:
        ss["_vt_pl_ir_hora"] = 2
        preservar_widgets(_KEYS_WIDGET_PL)
        st.rerun(scope="app")
    if ss.pop("_vt_pl_ir_hora", None) == 2:
        scroll_a_seccion("vt_sec_hora")
    # El salto a «Costo de Carta» (regla #699): otro reporte, una corrida
    # completa; el salto a su sección lo resuelve el rail de Recetas.
    if ss.pop("_vt_pl_ir_carta", None):
        preservar_widgets(_KEYS_WIDGET_PL)
        st.rerun(scope="app")
    cols_d = columnas(d)
    if not (cols_d["fecha"] and cols_d["prod"] and cols_d["venta"]):
        st.info("Faltan columnas (Fecha, Plato, Venta) para el ranking.")
        return

    cfg = REPORTES.get("Ventas", {})
    lim = rango_fechas(cfg.get("archivo", "ventas.parquet"),
                       cfg.get("carga_por_rango", "FEC REG DOCUMENTO"))
    _fd = pd.to_datetime(d[cols_d["fecha"]], errors="coerce").dropna()
    primer, ancla = lim if lim else (_fd.min().date(), _fd.max().date())

    with st.container(border=True, key="ajuste_graf_card_izq_ventas_platos"):
        _cuerpo(d, filtrar_cb, cols_d, primer, ancla)


def _cuerpo(d, filtrar_cb, cols_d, primer, ancla):
    """Lo de la tarjeta, en el orden en que se lee: el interruptor de la
    vista con sus KPI, la fila del Corte, los períodos y la vista elegida."""
    ss = st.session_state
    # ── El renglón del título: el interruptor y, a su derecha, los KPI de
    # la vista, que se escriben al final (hacen falta los períodos) ───────
    cab = st.container(horizontal=True, gap="medium",
                       vertical_alignment="center", key="vt_pl_cabfila")
    with cab:
        vista = st.segmented_control(
            "Vista", VISTAS, default=_VISTA_DEFAULT, required=True,
            key="vt_pl_vista", label_visibility="collapsed") or _VISTA_DEFAULT
    ranking = vista == VISTAS[0]

    # ── La fila de controles: el Corte, en el mismo lugar en las dos
    # vistas, y a su derecha los de la vista en pantalla. Los que dependen
    # de los datos —el Ámbito, la Categoría— se llenan después de cargar.
    # columnas-internas: la fila de controles de la tarjeta (FILA_RANKING)
    fila = st.columns(FILA_RANKING if ranking else FILA_MENU,
                      vertical_alignment="center")
    with fila[0]:
        corte = st.segmented_control(
            "Corte", CORTES, default=_CORTE_DEFAULT, required=True,
            key="vt_pl_corte", label_visibility="collapsed") or _CORTE_DEFAULT
    forma = None
    if ranking:
        # Medida, Mostrar y el Ámbito son de la pieza desde la regla #699:
        # las columnas se escriben vacías (ver FILA_MENU).
        for c in fila[1:]:
            with c:
                st.empty()
    else:
        # Por atributo y no importadas por nombre (regla #357, como el
        # `getattr` de `_render_rail`): si Cloud recarga este módulo con el
        # `ventas_menu` de antes de la #569 en memoria, la Ingeniería pide
        # reiniciar en vez de tumbar Ventas entero con un ImportError.
        if not hasattr(_menu, "vista_ingenieria"):
            st.info("La Ingeniería de menú se actualizó: hace falta "
                    "reiniciar la app («Manage app» → «Reboot app»).")
            return
        # «Cuadros | Matriz | Tabla» es de la pieza desde la regla #700.
        with fila[1]:
            st.empty()
        with fila[3]:
            st.empty()      # la columna del Ámbito, vacía: ver FILA_MENU

    # ── Los períodos del corte: una pastilla por período, hasta 4 ────────
    lista = periodos(corte, ancla, primer)
    etq = {k: _etiqueta(k, corte) for k in lista}
    k_per = f"vt_pl_per_{corte}"
    # Lo guardado que ya no está en la lista (el día avanzó y la ventana se
    # corrió) se descarta: un valor fuera de las opciones es un error.
    _validas = [x for x in (ss.get(k_per) or []) if x in etq.values()]
    ss[k_per] = _validas or [etq[k] for k in
                             lista[-min(_N_DEFECTO, len(lista)):]]
    elegidas = st.pills(
        "Comparar", [etq[k] for k in lista], selection_mode="multi",
        key=k_per, label_visibility="collapsed",
        help="Hasta 4, y no tienen que ser seguidos. Con más de 4 se usan "
             "los 4 más recientes. La Ingeniería de menú clasifica el "
             "último.") or []
    sel = [k for k in lista if etq[k] in elegidas][-MAX_PERIODOS:]
    if not sel:
        st.info("Elegí al menos un período para comparar.")
        return

    with st.spinner("Cargando los períodos…" if len(sel) > 1
                    else "Cargando el período…"):
        datos = {k: _cargar_periodo(k, corte, ancla, filtrar_cb, d)
                 for k in sel}
    ult = sel[-1]
    if not ranking:
        # La Ingeniería de menú del ÚLTIMO período, el mismo del puesto «#»
        # y del % de costo del ranking (regla #550).
        ant = sel[-2] if len(sel) > 1 else None
        _menu.vista_ingenieria(datos[ult][0], etq[ult], datos[ult][1],
                               datos[ant][0] if ant else None,
                               etq[ant] if ant else None,
                               forma=forma, cab=cab, c_cat=fila[2])
        return
    _pieza_ranking(datos, sel, etq, corte, lista, ancla, filtrar_cb, d)


# ===========================================================================
# LAS PIEZAS
# ===========================================================================


# ===========================================================================
# EL RANKING, PIEZA PROPIA (regla #699)
# ===========================================================================
# Desde el 2026-10-22 el ranking —los indicadores, «Dentro de», Venta |
# Unidades, el top, el gráfico de puestos, la tabla y la ficha del plato—
# es `ventas_platos.js` + `.css` (`st.components.v2`), sobre el boceto
# aprobado (https://claude.ai/artifact/Lzua6AASjVigJ8GJktVwM8). Python
# carga los períodos elegidos y los manda enteros: el ámbito, la medida, el
# top y los elegidos los resuelve el navegador sin una corrida. Vuelven a
# Python el plato en foco (`foco`: su evolución en TODO el corte se carga
# acá), «A qué hora se vende» (`hora`) y «Su costo en Costo de Carta»
# (`carta`). Las cuentas puras de arriba (`puestos`, `movimiento`,
# `var_por_dia`) siguen siendo la referencia: el `.js` las rehace igual, y
# el test busca las fórmulas escritas igual.

_PIEZA = st.components.v2.component(
    "ventas_platos",
    css=css_movil((Path(__file__).parent / "ventas_platos.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent / "ventas_platos.js").read_text(encoding="utf-8")),
)
_K_PIEZA = "vt_pl_pieza"


@st.cache_data(ttl=3600, show_spinner=False)
def _codigos_carta(sello):
    """{nombre del plato en minúsculas: código} de la carta costeada, para
    saltar de un plato a su ficha en Costo de Carta. `sello` es la clave."""
    try:
        from data import cargar
        df = cargar("cartacosteada.parquet")
    except Exception:
        return {}
    if df is None or df.empty or "ITEM VENT" not in df.columns:
        return {}
    return {str(n).strip().lower(): str(c).strip()
            for n, c in zip(df["ITEM VENT"], df["COD PLATO"])}


def armar_ranking(datos, sel, etq, foco=None, evolucion=None, codigos=None):
    """Lo que recibe la pieza. Pura: la lee el test.

    `datos` es {período: (agregado por plato, días con venta)} y `sel` los
    períodos elegidos, del más viejo al más nuevo. Un plato: [nombre, grupo,
    subgrupo, [venta], [unidades], [costo], [neto], código] con una posición
    por período elegido; el grupo y el subgrupo son los del período más
    nuevo en que vendió."""
    codigos = codigos or {}
    por = {}
    for j, k in enumerate(sel):
        a = datos[k][0]
        if a is None or a.empty:
            continue
        g = a.groupby("prod", as_index=False).agg(
            grupo=("grupo", "last"), sub=("sub", "last"), venta=("venta", "sum"),
            cant=("cant", "sum"), costo=("costo", "sum"), neto=("neto", "sum"))
        for r in g.itertuples(index=False):
            p = por.setdefault(r.prod, {"grupo": r.grupo, "sub": r.sub,
                                        "v": [0.0] * len(sel), "c": [0.0] * len(sel),
                                        "k": [0.0] * len(sel), "n": [0.0] * len(sel)})
            p["grupo"], p["sub"] = r.grupo, r.sub
            p["v"][j], p["c"][j] = round(float(r.venta), 2), round(float(r.cant), 2)
            p["k"][j], p["n"][j] = round(float(r.costo), 2), round(float(r.neto), 2)
    platos = [[n, str(p["grupo"] or ""), str(p["sub"] or ""), p["v"], p["c"], p["k"], p["n"],
               codigos.get(str(n).strip().lower(), "")] for n, p in por.items()]
    return {
        "periodos": [{"etq": etq[k], "dias": int(datos[k][1])} for k in sel],
        "platos": platos, "foco": foco, "evolucion": evolucion,
        "umbrales": [_COSTO_ALTO * 100, _COSTO_ROTO * 100], "salto": _SALTO,
        "tope": _TOPE_GRAFICO, "max_elegidos": MAX_ELEGIDOS,
    }


def _evolucion_de(nombre, corte, lista, etq, sel, ancla, filtrar_cb, d):
    """El plato en foco en TODO el corte: [etiqueta, venta por día, unidades
    por día, si está entre los elegidos] por período."""
    serie = []
    for k in lista:
        a, n_dias = _cargar_periodo(k, corte, ancla, filtrar_cb, d)
        f = a[a["prod"] == nombre]
        v, c = float(f["venta"].sum()), float(f["cant"].sum())
        serie.append([etq[k], v / n_dias if n_dias else 0.0, c / n_dias if n_dias else 0.0,
                      k in sel])
    return {"nombre": nombre, "corte": corte.lower(), "serie": serie}


def _ir_a_carta(cod):
    """«Su costo en Costo de Carta»: deja el plato elegido allá y pide el
    salto a Recetas, que necesita una corrida COMPLETA (ver `_ventas_platos`).
    Con un `graficos` viejo en Cloud (regla #357), no hace nada."""
    try:
        import navegacion
        from graficos.carta_costeada import _K_FOCO
        st.session_state[_K_FOCO] = cod
        navegacion._ir_a_vista("Recetas", "rec_graf_tipo", "Carta costeada")
        st.session_state["_vt_pl_ir_carta"] = 1
    except (ImportError, AttributeError):
        return


def _pieza_ranking(datos, sel, etq, corte, lista, ancla, filtrar_cb, d):
    """El ranking en la pieza, con la evolución del plato en foco."""
    ss = st.session_state
    nombres = set()
    for k in sel:
        a = datos[k][0]
        if a is not None and not a.empty:
            nombres.update(a["prod"])
    foco = ss.get("vt_pl_foco")
    if foco not in nombres:
        ult = datos[sel[-1]][0]
        foco = (str(ult.groupby("prod")["venta"].sum().idxmax())
                if ult is not None and not ult.empty else None)
    evo = None
    if foco:
        with st.spinner("Cargando la evolución…"):
            evo = _evolucion_de(foco, corte, lista, etq, sel, ancla, filtrar_cb, d)

    def _al_foco():
        v = (ss.get(_K_PIEZA) or {}).get("foco")
        if v:
            ss["vt_pl_foco"] = v

    def _a_la_hora():
        v = (ss.get(_K_PIEZA) or {}).get("hora")
        if v and v.get("plato"):
            _ir_a_hora(v["plato"])

    def _a_la_carta():
        v = (ss.get(_K_PIEZA) or {}).get("carta")
        if v and v.get("cod"):
            _ir_a_carta(v["cod"])

    try:
        from data import sello_datos
        codigos = _codigos_carta(sello_datos("cartacosteada.parquet"))
    except Exception:
        codigos = {}
    _PIEZA(key=_K_PIEZA, data=armar_ranking(datos, sel, etq, foco, evo, codigos),
           on_foco_change=_al_foco, on_hora_change=_a_la_hora,
           on_carta_change=_a_la_carta, width="stretch")
