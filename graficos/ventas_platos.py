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

DE DÓNDE SALEN LOS DATOS: como en «Año Pasado» y «Por hora», cada período se
trae con `data.cargar_rango` y pasa por `filtrar_cb` (el `_filtrar_items` de
`ventas.py`: los chips de la franja, un ítem una vez y sólo venta). El `d`
de la franja no alcanza: con el rango por defecto —un mes— pedir trece meses
mostraría uno. El calendario de los períodos es el de «Por hora»
(`ventas_horario._claves_hacia_atras`, `_rango_de_clave`,
`_etiqueta_clave`), para que las dos vistas nombren igual el mismo mes.

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

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from html import escape

from data import REPORTES, cargar_rango, rango_fechas
from tema import (ACENTO, AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, GRIS_TEXTO,
                  GRIS_TEXTO_SUAVE, LAVANDA_BORDE, PALETA_SERIES,
                  TEXTO_PRINCIPAL)
from graficos import alturas
from graficos.base import (_compras_layout, _compras_truncar, _resolver,
                           preservar_widgets, scroll_a_seccion)
from graficos.compras._comun import _first_point
from graficos.ventas_horario import (_COLOR_MARCA, _claves_hacia_atras,
                                     _etiqueta_clave, _rango_de_clave)
from graficos import ventas_menu as _menu
from graficos.ventas_menu import _KEYS_WIDGET_MENU
from graficos.ventas_mix import _estilo_costo, base, columnas, pct_costo
from utils import fmt_k

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

_KEYS_WIDGET_PL = ("vt_pl_vista", "vt_pl_corte", "vt_pl_medida",
                   "vt_pl_mostrar", "vt_pl_per_*", "vt_pl_amb",
                   "vt_pl_elegidos") + _KEYS_WIDGET_MENU
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


def _curva(evt):
    p = _first_point(evt)
    if p is None:
        return None
    c = p.get("curve_number")
    return c if isinstance(c, int) else None


def _fila(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _leer_clics():
    ss = st.session_state
    c = _clic("vt_pl_g", _curva)
    trazas = ss.get("_vt_pl_trazas", [])
    if c is not None and 0 <= c < len(trazas):
        ss["vt_pl_foco"] = None if ss.get("vt_pl_foco") == trazas[c] else trazas[c]
    f = _clic("vt_pl_tabla", _fila)
    filas = ss.get("_vt_pl_filas", [])
    if f is not None and 0 <= f < len(filas):
        ss["vt_pl_foco"] = None if ss.get("vt_pl_foco") == filas[f] else filas[f]


def _alternar_elegido(nombre):
    el = list(st.session_state.get("vt_pl_elegidos") or [])
    if nombre in el:
        el.remove(nombre)
    elif len(el) < MAX_ELEGIDOS:
        el.append(nombre)
    st.session_state["vt_pl_elegidos"] = el


def _soltar_foco():
    st.session_state["vt_pl_foco"] = None


def _ir_a_hora(nombre):
    """«Ver a qué hora se vende»: deja pedida la ficha del plato en «Por
    hora» (filas «Platos») y marca el salto. El salto necesita una corrida
    COMPLETA —«Por hora» es otra sección, con su propio fragment— y el
    scroll va en la corrida siguiente a ésa (ver `_ventas_platos`)."""
    ss = st.session_state
    ss["vh_op_filas"] = "Platos"
    # «Por hora» guarda la columna elegida en su sombra y reescribe
    # el widget desde ahí (`ventas_horario._pastillas`, regla #555).
    ss["_vh_op_cols_valor"] = "Hora"
    ss["_vh_ficha_pedida"] = nombre
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
    cols_d = columnas(d)
    if not (cols_d["fecha"] and cols_d["prod"] and cols_d["venta"]):
        st.info("Faltan columnas (Fecha, Plato, Venta) para el ranking.")
        return
    _leer_clics()

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
    medida = mostrar = forma = None
    if ranking:
        with fila[1]:
            medida = st.segmented_control(
                "Medida", _MEDIDAS, default=_MEDIDAS[0], required=True,
                key="vt_pl_medida", label_visibility="collapsed",
                persist_state="page") or _MEDIDAS[0]
        with fila[2]:
            mostrar = st.segmented_control(
                "Mostrar", _MOSTRAR, default=_MOSTRAR_DEFAULT, required=True,
                key="vt_pl_mostrar", label_visibility="collapsed",
                persist_state="page",
                help="**Todos**: la tabla lista cada plato del ámbito; el "
                     "gráfico sigue con los 20 primeros. **Elegidos**: sólo "
                     "los platos que buscaste arriba de la tabla."
            ) or _MOSTRAR_DEFAULT
    else:
        # Por atributo y no importadas por nombre (regla #357, como el
        # `getattr` de `_render_rail`): si Cloud recarga este módulo con el
        # `ventas_menu` de antes de la #569 en memoria, la Ingeniería pide
        # reiniciar en vez de tumbar Ventas entero con un ImportError.
        if not hasattr(_menu, "vista_ingenieria"):
            st.info("La Ingeniería de menú se actualizó: hace falta "
                    "reiniciar la app («Manage app» → «Reboot app»).")
            return
        with fila[1]:
            forma = _menu.control_forma()
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
    en_foco = _ranking(cab, fila[3], datos, sel, etq, medida, mostrar)
    if en_foco:
        foco, info, elegidos = en_foco
        _evolucion(foco, corte, lista, etq, sel, ancla, filtrar_cb, d,
                   "cant" if medida == "Unidades" else "venta", info,
                   elegidos)
    else:
        # Sin evolución, el lugar donde la Ingeniería pone su pie: se
        # escribe vacío para no depender de la limpieza (ver FILA_MENU).
        st.empty()


def _ranking(cab, c_amb, datos, sel, etq, medida, mostrar):
    """La vista del ranking, con los períodos ya cargados: el Ámbito (en
    `c_amb`, la última columna de la fila del Corte), los KPI (en `cab`), el
    gráfico de puestos, el buscador y la tabla. Con un plato en foco
    devuelve `(plato, info, elegidos)` para su evolución; si no, None."""
    ss = st.session_state
    m = "cant" if medida == "Unidades" else "venta"
    agg = {k: datos[k][0].set_index("prod") for k in sel}
    dias = {k: datos[k][1] for k in sel}
    todos = pd.concat([agg[k][["grupo", "sub", "venta"]] for k in sel])
    if todos.empty:
        st.info("Sin ventas en los períodos elegidos.")
        return None
    # Grupo y subgrupo de cada plato: los del período más nuevo en que vendió.
    info = todos[~todos.index.duplicated(keep="last")][["grupo", "sub"]]
    peso = todos.groupby(level=0)["venta"].sum().sort_values(ascending=False)

    # ── El ámbito: un desplegable en la fila del Corte (regla #569) ──────
    amb_ops = opciones_ambito(todos)
    # Un grupo que no vendió en los períodos de ahora ya no es opción: un
    # valor fuera de las opciones es un error.
    if ss.get("vt_pl_amb") not in amb_ops:
        ss["vt_pl_amb"] = TODA_LA_CARTA
    with c_amb:
        amb = st.selectbox(
            "Ámbito", list(amb_ops), key="vt_pl_amb",
            label_visibility="collapsed", persist_state="page",
            help="Toda la carta, un grupo o un subgrupo: el puesto se "
                 "calcula DENTRO de lo elegido («3º de Fondos»)."
        ) or TODA_LA_CARTA
    col_amb, cual = amb_ops[amb]
    en_amb = (info.index if col_amb is None
              else info.index[info[col_amb] == cual])

    # ── El gráfico de puestos a la izquierda; a la derecha el buscador de
    # platos y, debajo, la tabla. Las columnas se crean ANTES de contar:
    # con «Elegidos», lo buscado decide las filas ─────────────────────────
    # columnas-internas: el gráfico de puestos y su tabla
    g1, g2 = st.columns([0.9, 1.2], gap="medium")
    with g2:
        _opciones = list(dict.fromkeys(
            list(peso.index) + list(ss.get("vt_pl_elegidos") or [])))
        elegidos = st.multiselect(
            "Platos a comparar", _opciones, key="vt_pl_elegidos",
            max_selections=MAX_ELEGIDOS, placeholder="Buscar platos para "
            "comparar…", label_visibility="collapsed", persist_state="page",
            help="Hasta 8. Con «Elegidos» se comparan sólo ésos, cada uno "
                 "con su color, estén en el puesto que estén.")

    # ── Puestos, dentro del ámbito ───────────────────────────────────────
    val = {k: agg[k][m].reindex(en_amb).fillna(0.0) for k in sel}
    pue = {k: puestos(val[k]) for k in sel}
    pri, ult = sel[0], sel[-1]
    universo = sorted(
        set().union(*[set(pue[k].index) for k in sel]),
        key=lambda n: (pue[ult].get(n, 10 ** 6), -val[pri].get(n, 0.0)))
    if mostrar == "Elegidos":
        filas = [n for n in universo if n in elegidos] + [
            n for n in elegidos if n not in universo and n in en_amb]
    elif mostrar == "Todos":
        filas = universo
    else:
        tope = int(mostrar.split()[1])
        filas = [n for n in universo if pue[ult].get(n, 10 ** 6) <= tope]
    en_graf = (filas if mostrar == "Elegidos"
               else [n for n in filas if pue[ult].get(n, 10 ** 6) <= _TOPE_GRAFICO])

    # ── Los KPI del renglón del título ───────────────────────────────────
    tot = {k: float(val[k].sum()) for k in sel}
    g_amb = var_por_dia(tot[pri], dias[pri], tot[ult], dias[ult])
    movs = {n: movimiento(pue[pri].get(n), pue[ult].get(n)) for n in universo}
    # «Sube más» entre los que HOY están en el top 20 y «Baja más» entre los
    # que ESTABAN: sin ese corte los ganaban platos marginales que pasaban
    # del puesto 150 al 84, que no le dicen nada a nadie.
    _dif = {n: (pue[pri].get(n, 0) - pue[ult].get(n, 0)) for n in universo
            if pue[pri].get(n) and pue[ult].get(n)}
    _s = {n: v for n, v in _dif.items() if pue[ult][n] <= _TOPE_GRAFICO}
    _b = {n: v for n, v in _dif.items() if pue[pri][n] <= _TOPE_GRAFICO}
    sube = max(_s, key=_s.get) if _s and max(_s.values()) > 0 else None
    baja = min(_b, key=_b.get) if _b and min(_b.values()) < 0 else None
    n_entran = sum(1 for n in universo if movs[n][1] == "entra"
                   and pue[ult].get(n, 10 ** 6) <= _TOPE_GRAFICO)
    ambito = cual or "toda la carta"
    with cab:
        st.markdown(_html_cab(
            ambito, len(pue[ult]), etq[ult], g_amb, etq[pri],
            sube, _dif.get(sube), baja, _dif.get(baja), n_entran,
            len(sel) > 1), unsafe_allow_html=True)

    # ── El gráfico de puestos y la tabla ─────────────────────────────────
    foco = ss.get("vt_pl_foco")
    with g1:
        if en_graf:
            _grafico(en_graf, sel, etq, pue, mostrar, elegidos, foco)
        else:
            st.caption("Sin platos que mostrar: en «Elegidos», buscalos "
                       "arriba de la tabla.")
    with g2:
        # El % de costo es el del ÚLTIMO período, el mismo del puesto «#»:
        # la pregunta es cuánto cuesta hoy lo que hoy se vende (regla #546).
        _tabla(filas, sel, etq, val, pue, dias, m, movs,
               costo_por_plato(agg[ult]))
    notas = []
    if mostrar == "Todos" and len(filas) > _TOPE_GRAFICO:
        notas.append(f"La tabla lista los {len(filas)} platos de {ambito}; "
                     "el gráfico, los 20 primeros.")
    if mostrar == "Elegidos" and any(n not in en_amb for n in elegidos):
        notas.append(f"Hay elegidos fuera de {ambito}: no se muestran.")
    if len(sel) == 1:
        notas.append("Con un solo período no hay movimiento: elegí otro "
                      "para comparar.")
    notas.append("El % compara la venta POR DÍA con venta: un período en "
                 "curso tiene menos días.")
    st.caption(" ".join(notas))
    return (foco, info, elegidos) if foco else None


# ===========================================================================
# LAS PIEZAS
# ===========================================================================

def _html_cab(ambito, n_platos, ult, g_amb, pri, sube, d_sube, baja,
              d_baja, n_entran, compara):
    """Los KPI en un renglón, con el dibujo del Resumen (`.vt-cab`). Sin
    título desde que la tarjeta tiene dos vistas (regla #569): el nombre lo
    dice el interruptor, a su izquierda, y el «Top 15» que decía el título
    está marcado en «Mostrar»."""
    def _k(rot, val, clase="", tip=""):
        return (f'<div class="vt-kpi {clase}" title="{escape(tip or rot)}">'
                f'<span class="vt-kpi-rot">{escape(rot)}</span>'
                f'<span class="vt-kpi-val">{escape(val)}</span></div>')
    partes = [_k(f"Platos con venta · {ult}", f"{n_platos:,}", "vt-kpi-total")]
    if compara:
        if g_amb is not None:
            partes.append(_k(f"{ambito.capitalize()} por día",
                             f"{'+' if g_amb >= 0 else '−'}{abs(g_amb):.0%}",
                             tip=f"Venta por día de {ambito}, de {pri} a "
                                 f"{ult}: la vara con que se mide cada plato"))
        if sube:
            partes.append(_k("Sube más", f"{_compras_truncar(sube, 24)} ▲{d_sube}"))
        if baja:
            partes.append(_k("Baja más", f"{_compras_truncar(baja, 24)} ▼{-d_baja}"))
        partes.append(_k("Entran al top 20", f"{n_entran}",
                         tip=f"Platos del top 20 de {ult} que no vendieron "
                             f"en {pri}"))
    return ('<div class="vt-cab"><div class="vt-kpis">' + "".join(partes)
            + "</div></div>")


def _grafico(nombres, sel, etq, pue, mostrar, elegidos, foco):
    """Los puestos de cada plato a lo largo de los períodos (bump chart)."""
    ss = st.session_state
    xs = [etq[k] for k in sel]
    maxp = max([pue[k].get(n, 0) for k in sel for n in nombres] + [1])
    n_eje = maxp if mostrar == "Elegidos" else min(maxp, _TOPE_GRAFICO)
    techo = n_eje + 2
    fig = go.Figure()
    for n in nombres:
        ys = [pue[k].get(n) for k in sel]
        if mostrar == "Elegidos" and n in elegidos:
            color = _COLORES_ELEGIDOS[elegidos.index(n) % MAX_ELEGIDOS]
        else:
            tipo = movimiento(ys[0], ys[-1])[1]
            color = {"entra": ACENTO, "sube": AJUSTE_POS_TEXTO,
                     "baja": AJUSTE_NEG_TEXTO}.get(tipo, GRIS_TEXTO_SUAVE)
        resaltado = n == foco or (mostrar != "Elegidos" and n in elegidos)
        fig.add_trace(go.Scatter(
            x=xs, y=[y if y and y <= n_eje else techo for y in ys],
            mode="lines+markers",
            line=dict(color=color, width=4 if resaltado else 2.2),
            marker=dict(size=9 if resaltado else 7,
                        color=[color if y else "#ffffff" for y in ys],
                        line=dict(color=color, width=1.5)),
            opacity=0.35 if foco and n != foco else 1.0,
            customdata=[f"#{y}" if y else "sin venta" for y in ys],
            hovertemplate=(f"<b>{escape(n)}</b><br>%{{x}}: %{{customdata}}"
                           "<extra></extra>")))
        if ys[-1] and ys[-1] <= n_eje:
            fig.add_annotation(
                x=xs[-1], y=ys[-1], xanchor="left", xshift=8, showarrow=False,
                text=escape(_compras_truncar(n, 24)),
                font=dict(size=10.5, color=TEXTO_PRINCIPAL if n != foco
                          else ACENTO))
    ss["_vt_pl_trazas"] = list(nombres)
    alto = alturas.VENTAS_PLATOS
    _compras_layout(fig, alto=alto)
    tv = (list(range(1, n_eje + 1)) if n_eje <= 22 else sorted(
        {v for v in (1, 5, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300)
         if v < n_eje * 0.93} | {n_eje}))
    ejey = dict(fixedrange=True, gridcolor=LAVANDA_BORDE, zeroline=False,
                tickvals=tv + [techo],
                ticktext=[f"#{v}" for v in tv] + ["fuera"],
                tickfont=dict(size=10, color=GRIS_TEXTO))
    # Con puestos lejanos (un elegido en el 160) el eje es logarítmico: del
    # 1 al 10 conservan su lugar y del 100 para abajo se aprietan, que es
    # como se lee una tabla de posiciones.
    if n_eje > 22:
        ejey.update(type="log", range=[np.log10(techo * 1.08), np.log10(0.8)])
    else:
        ejey.update(range=[techo + 0.6, 0.4])
    fig.update_layout(
        showlegend=False, margin=dict(l=10, r=170, t=10, b=4),
        dragmode="pan", yaxis=ejey,
        # Categorías SIEMPRE: «2025» en un eje sin tipo es un número (#448).
        xaxis=dict(type="category", fixedrange=True, showgrid=False,
                   tickfont=dict(size=10.5)))
    st.plotly_chart(fig, key=_key("vt_pl_g"), on_select="rerun",
                    selection_mode="points",
                    config={"displaylogo": False, "displayModeBar": False})


def _tabla(filas, sel, etq, val, pue, dias, m, movs, pc):
    """La tabla: el puesto de hoy, lo vendido en cada período, el
    movimiento de puesto, la variación por día y el % de costo del último
    período (`pc`, de `costo_por_plato`). Un clic elige el plato."""
    ss = st.session_state
    pri, ult = sel[0], sel[-1]
    t = pd.DataFrame({"Plato": filas})
    # SIN VACÍOS: un NaN viaja a la grilla como nulo y Streamlit lo pinta
    # «None» sin mirar el formato del Styler (medido). Sin venta va 0 —y se
    # escribe «—»—, y la variación de un plato que no vendía en el primer
    # período va +∞ —y se escribe «nuevo»—: así la columna sigue siendo
    # numérica y se puede ordenar.
    t["#"] = np.array([pue[ult].get(n, 0) for n in filas], dtype=float)
    for k in sel:
        t[etq[k]] = np.array([val[k].get(n, 0.0) for n in filas], dtype=float)
    t["Puestos"] = [movs.get(n, ("—", "igual"))[0] for n in filas]

    def _dv(n):
        x = var_por_dia(val[pri].get(n, 0.0), dias[pri],
                        val[ult].get(n, 0.0), dias[ult])
        if x is not None:
            return x
        return np.inf if val[ult].get(n, 0.0) > 0 else -np.inf
    t["Δ por día"] = np.array([_dv(n) for n in filas], dtype=float)
    # Sin costo cargado —o sin venta en el último período— va 0, que se
    # escribe «—»: un % de costo de verdad nunca es 0 (`pct_costo`).
    t["% costo"] = np.nan_to_num(
        np.array([pc.get(n, np.nan) for n in filas], dtype=float), nan=0.0)
    ss["_vt_pl_filas"] = list(filas)
    per = [etq[k] for k in sel]
    # «—» donde no hubo venta, y los montos compactos: la tabla va al lado
    # del gráfico y tiene que entrar sin deslizar de costado.
    sty = (t.style
           .format(lambda v: f"#{int(v)}" if v else "—", subset=["#"])
           .format(lambda v: "—" if not v else (
               fmt_k(v).replace("S/ ", "") if m == "venta" else f"{v:,.0f}"),
               subset=per)
           .format(lambda v: ("nuevo" if v > 0 else "—") if np.isinf(v)
                   else f"{'+' if v >= 0 else '−'}{abs(v):.0%}",
                   subset=["Δ por día"])
           .format(lambda v: f"{v:.1%}" if v else "—", subset=["% costo"])
           # Los umbrales y los colores del Resumen, como en el Mix: el mismo
           # número se pinta igual en las tres vistas.
           .map(_estilo_costo, subset=["% costo"]))
    # Anchos en píxeles y no «small»/«medium»: con cuatro períodos, los de
    # nombre dejaban la última columna fuera de la tarjeta (medido a 1366).
    # Y desde que lleva el % de costo, con cuatro se angostan el nombre y
    # los montos para sumar lo mismo que con tres (medido: si no, «% costo»
    # quedaba afuera; cederle ancho al gráfico le giraba las fechas, #546).
    w_plato, w_per = (150, 58) if len(sel) >= MAX_PERIODOS else (180, 62)
    cfg = {"Plato": st.column_config.TextColumn(pinned=True, width=w_plato),
           "#": st.column_config.Column(
               width=44, help=f"Puesto en {per[-1]}, dentro del ámbito"),
           "Puestos": st.column_config.Column(
               width=62, help=f"Cambio de puesto de {per[0]} a {per[-1]}"),
           "Δ por día": st.column_config.Column(
               width=72, help="Variación de la venta POR DÍA del primer al "
                              "último período"),
           "% costo": st.column_config.Column(
               width=62, help=f"Costo ÷ venta neta de {per[-1]}, como el "
                              "Resumen. «—»: sin costo cargado o sin venta "
                              "en ese período.")}
    for x in per:
        cfg[x] = st.column_config.Column(
            width=w_per, help=("Venta" if m == "venta" else "Unidades")
            + f" de {x}" + (" (S/)" if m == "venta" else ""))
    st.dataframe(sty, key=_key("vt_pl_tabla"), on_select="rerun",
                 selection_mode="single-row", hide_index=True, row_height=27,
                 height=alturas.VENTAS_PLATOS_TABLA, column_config=cfg)


def _evolucion(nombre, corte, lista, etq, sel, ancla, filtrar_cb, d, m, info,
               elegidos):
    """El plato en foco en TODO el corte, por día. Va DENTRO de la tarjeta,
    debajo de la tabla y separado por una línea: hasta el 2026-09-29 era una
    segunda tarjeta (regla #569). La key no lleva el prefijo de tarjeta
    (`ajuste_graf_card_`) a propósito: con él heredaría fondo, borde y techo
    de una tarjeta metida en otra."""
    with st.container(key="vt_pl_evo_caja"):
        # columnas-internas: el título de la evolución y sus tres botones
        c1, c2, c4, c3 = st.columns([2.6, 1.1, 1.3, 0.7],
                                    vertical_alignment="center")
        sub = (f"{info.loc[nombre, 'grupo']} › {info.loc[nombre, 'sub']}"
               if nombre in info.index else "")
        with c1:
            st.markdown(
                f'<div class="vt-pl-evo-tit"><b>{escape(nombre)}</b> · '
                f'{escape(sub)} · {"venta" if m == "venta" else "unidades"} '
                f'por día, en cada {corte.lower()} del corte</div>',
                unsafe_allow_html=True)
        with c2:
            st.button("Quitar de elegidos" if nombre in elegidos
                      else "Agregar a elegidos", key="vt_pl_btn_elegir",
                      on_click=_alternar_elegido, args=(nombre,),
                      use_container_width=True)
        with c4:
            st.button("Ver a qué hora se vende →", key="vt_pl_btn_hora",
                      on_click=_ir_a_hora, args=(nombre,),
                      use_container_width=True,
                      help="Lleva a «Por hora» con este plato abierto en su "
                           "ficha.")
        with c3:
            st.button("Cerrar", key="vt_pl_btn_soltar", on_click=_soltar_foco,
                      use_container_width=True)
        ys = []
        with st.spinner("Cargando la evolución…"):
            for k in lista:
                a, n_dias = _cargar_periodo(k, corte, ancla, filtrar_cb, d)
                v = a.loc[a["prod"] == nombre, m].sum()
                ys.append(float(v) / n_dias if n_dias else 0.0)
        colores = [_COLOR_MARCA[sel.index(k) % len(_COLOR_MARCA)] if k in sel
                   else LAVANDA_BORDE for k in lista]
        fig = go.Figure(go.Bar(
            x=[etq[k] for k in lista], y=ys, marker=dict(color=colores),
            text=[fmt_k(y) if m == "venta" else f"{y:,.1f}" for y in ys],
            textposition="outside", cliponaxis=False,
            hovertemplate=("%{x}<br>" + ("S/ %{y:,.0f}" if m == "venta"
                                         else "%{y:,.1f} u")
                           + " por día<extra></extra>")))
        _compras_layout(fig, alto=alturas.COMPACTO)
        fig.update_layout(
            showlegend=False, bargap=0.3, margin=dict(l=10, r=10, t=18, b=4),
            xaxis=dict(type="category", fixedrange=True,
                       tickfont=dict(size=10)),
            yaxis=dict(fixedrange=True, showticklabels=False,
                       gridcolor=LAVANDA_BORDE))
        st.plotly_chart(fig, key="vt_pl_evo",
                        config={"displaylogo": False, "displayModeBar": False})
