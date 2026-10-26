"""
graficos.ventas_menu — la «Ingeniería de menú», la segunda vista de Ventas ›
Análisis de platos: cada plato clasificado por lo que se pide y lo que deja.

Nació el 2026-09-26 de una maqueta aprobada (regla #550), como una segunda
tarjeta debajo del ranking. Desde el 2026-09-29 es una de las dos vistas de
UNA tarjeta (regla #569): el interruptor «Ranking | Ingeniería de menú» del
renglón del título elige cuál se dibuja, y ésta pone sus controles en la
fila del Corte, que comparte con el ranking. El método es el de
Kasavana y Smith (1982), *Menu Engineering: A Practical Guide to Menu
Analysis*, con las fórmulas y las acciones como las publica AHLEI:

  · POPULAR: su parte de las unidades de la categoría llega al 70 % de 1/N.
  · DEJA MUCHO: su margen por plato —precio NETO menos costo— llega al
    promedio de la categoría PONDERADO por lo vendido (margen total ÷
    unidades), no al promedio simple de los márgenes.
  · Estrella (las dos), caballo de batalla (sólo popular), rompecabezas
    (sólo deja mucho), perro (ninguna), cada una con su acción.

TRES DECISIONES DEL USUARIO, del mismo día:

  · LA CATEGORÍA LA ARMA QUIEN MIRA, juntando subgrupos: el método compara
    platos que compiten por la misma elección, y el sistema no los agrupa
    así — la Entraña, el plato que más vende en soles, está en «Carnes
    Americanas» (2 platos) y no en «Fondos».
  · «AL LÍMITE» (agregado nuestro, no del método): a menos de 5 % de un
    umbral, y desde el 2026-09-27 sólo en los platos que venden al menos la
    mitad de lo que pide la popularidad (`_PISO_LIMITE`). Lomo Saltado
    quedaba a S/ 0,05 de ser estrella.
  · SE MUESTRAN UNIDADES Y PEDIDOS: la clase sale de las unidades, como en
    el método; los pedidos (cada mesa o delivery una vez) van al lado, y si
    contados así el plato cambiaría de clase, lo dice.

Y tres formas de mostrar lo mismo, que se alternan: Cuadros (abre ahí),
Matriz y Tabla. Leen la MISMA clasificación: `clasificar` corre una vez.

QUÉ NO ENTRA, y se lista con su motivo: la cortesía cobrada a S/ 0 (no se
elige en la carta, regla #547), el plato sin costo cargado y el que cuesta
más de lo que se cobra (casi siempre una receta mal cargada).
"""

from graficos.movil import css_movil, js_movil
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from graficos.base import _compras_truncar
from graficos.ventas_resumen import _COSTO_ALTO, _COSTO_ROTO

FORMAS = ("Cuadros", "Matriz", "Tabla")
_FORMA_DEFAULT = "Cuadros"

_UMBRAL_POP = 0.70
"""La regla del 70 % de Kasavana y Smith: popular es quien vende al menos el
70 % de lo que le tocaría si todos los platos de la categoría vendieran igual."""

_LIMITE = 0.05
"""«Al límite»: a menos de 5 % de un umbral. Agregado nuestro, no del método."""

_PISO_LIMITE = 0.5
"""Y sólo en los platos que venden al menos la MITAD de lo que pide la
popularidad (2026-09-27, a pedido). Por debajo, que un plato sea perro o
rompecabezas se decide por céntimos, y su margen es el de un par de tickets:
en Cocteles —márgenes apretados, la mitad entre S/ 24,70 y S/ 30,04— la
marca salía en 9 de 31 tragos, seis vendidos de 1 a 7 veces. Con el piso
quedan 4, los que se venden y un sol cambia de cuadro (regla #550)."""

_PRECIO_MIN = 1.0
"""Un sol NETO por unidad. Menos que eso es una cortesía cobrada a S/ 0, que
deja un residuo de redondeo y no un precio (regla #547)."""

_FILAS_CUADRO = 7
"""Platos por cuadro en «Cuadros». Con más, la tarjeta pasa de una pantalla a
1366×768; los demás están en la Tabla, y el cuadro lo dice. Medido con
Fondos + carnes: 676px."""

_FILAS_LISTA = 5
"""Platos por clase en la lista al lado de la «Matriz»: la columna es más
angosta y larga que un cuadro, y con siete la tarjeta medía 748px."""

_ANCHO_TRAZO = 620
"""Ancho supuesto del área de trazo de la matriz, en px, para ubicar los
rótulos (`rotulos`): la columna del gráfico mide ~700 a 1366 menos el eje.
Plotly no esquiva rótulos solo; en una pantalla más ancha sobra lugar."""

CLASES = ("estrella", "caballo", "rompecabezas", "perro")
_NOMBRE = {"estrella": "Estrellas", "caballo": "Caballos de batalla",
           "rompecabezas": "Rompecabezas", "perro": "Perros"}
_SING = {"estrella": "Estrella", "caballo": "Caballo de batalla",
         "rompecabezas": "Rompecabezas", "perro": "Perro"}
_ACCION = {"estrella": "Mantener", "caballo": "Revisar precio o porción",
           "rompecabezas": "Reubicar o recomendar", "perro": "Sacar o rehacer"}
_DETALLE = {
    "estrella": "Se piden mucho y dejan mucho.",
    "caballo": "Se piden mucho pero dejan poco por plato.",
    "rompecabezas": "Dejan mucho pero se piden poco.",
    "perro": "Ni se piden ni dejan.",
}

_KEYS_WIDGET_MENU = ("vt_ing_subs",)
# «Cuadros | Matriz | Tabla» (`vt_ing_forma`) es de la pieza desde la regla #700.
"""Los controles de la vista. Van también en
`ventas_platos._KEYS_WIDGET_PL`: la vista se dibuja dentro de ese fragment,
y su salto a «Por hora» lo corta con un `st.rerun` (regla #373). Y los dos
llevan `persist_state="page"`: mientras se mira el ranking no se dibujan, y
sin eso volverían a su default (regla #569)."""


# ===========================================================================
# LA CUENTA
# ===========================================================================

def _clase(mm, margen, umbral, acm):
    """La clase de cada plato: popular si `mm` llega al umbral, deja mucho si
    su margen llega al promedio ponderado."""
    pop, deja = mm >= umbral, margen >= acm
    return np.select([pop & deja, pop, deja], ["estrella", "caballo",
                                               "rompecabezas"], "perro")


def clasificar(a, subs):
    """La Ingeniería de menú de un período: `(platos, fuera, resumen)`.

    `a` es el agregado por plato de `ventas_platos.agregar` (con `pedidos`
    si el parquet los trae) y `subs`, los `(grupo, sub)` que forman la
    categoría. `platos` tiene una fila por plato clasificado, ordenada por el
    margen total que deja; `fuera`, los que no se pueden clasificar con su
    motivo; `resumen`, los umbrales y lo que deja cada clase. Sin platos
    clasificables, `resumen` es None."""
    subs = {tuple(s) for s in subs or ()}
    if a is None or a.empty or not subs:
        return pd.DataFrame(), [], None
    m = a[[(g, s) in subs for g, s in zip(a["grupo"], a["sub"])]]
    if m.empty:
        return pd.DataFrame(), [], None
    if "pedidos" not in m.columns:
        m = m.assign(pedidos=np.nan)
    # Un plato que cambió de subgrupo a mitad del período viene en dos filas:
    # se suma por NOMBRE (el de `costo_por_plato`, regla #546).
    m = (m.groupby("prod", as_index=False)
         .agg(grupo=("grupo", "last"), sub=("sub", "last"), u=("cant", "sum"),
              neto=("neto", "sum"), costo=("costo", "sum"),
              pedidos=("pedidos", lambda s: s.sum(min_count=1))))
    m = m[m["u"] > 0].copy()
    m["precio"] = m["neto"] / m["u"]
    m["costo_u"] = m["costo"] / m["u"]
    motivo = np.select(
        [m["precio"] < _PRECIO_MIN, m["costo"] <= 0, m["costo_u"] > m["precio"]],
        ["cortesía a S/ 0", "sin costo cargado", "cuesta más de lo que se cobra"],
        "")
    fuera = [{"plato": r.prod, "u": float(r.u), "motivo": mo,
              "precio": float(r.precio), "costo_u": float(r.costo_u)}
             for r, mo in zip(m.itertuples(), motivo) if mo]
    m = m[motivo == ""].copy()
    if m.empty:
        return m, fuera, None

    n, u_tot = len(m), float(m["u"].sum())
    umbral = _UMBRAL_POP / n
    m["margen"] = m["precio"] - m["costo_u"]
    m["margen_tot"] = m["neto"] - m["costo"]
    acm = float(m["margen_tot"].sum()) / u_tot
    m["mm"] = m["u"] / u_tot
    m["clase"] = _clase(m["mm"], m["margen"], umbral, acm)
    ped_tot = m["pedidos"].sum(min_count=1)
    if pd.notna(ped_tot) and ped_tot > 0:
        m["mm_ped"] = m["pedidos"] / ped_tot
        m["clase_ped"] = _clase(m["mm_ped"], m["margen"], umbral, acm)
    else:
        m["mm_ped"], m["clase_ped"] = np.nan, None
    cerca = (((m["mm"] / umbral - 1).abs() < _LIMITE)
             | (((m["margen"] / acm - 1).abs() < _LIMITE) if acm > 0 else False))
    m["al_limite"] = cerca & (m["mm"] >= _PISO_LIMITE * umbral)
    m["pct_costo"] = m["costo"] / m["neto"]
    cm_tot = float(m["margen_tot"].sum())
    resumen = {
        "n": n, "umbral": umbral, "acm": acm, "u": u_tot, "margen": cm_tot,
        # Desde cuántas unidades un plato puede llevar la marca «al límite».
        "piso_limite_u": int(np.ceil(_PISO_LIMITE * umbral * u_tot - 1e-9)),
        "pedidos": float(ped_tot) if pd.notna(ped_tot) else None,
        "clases": {k: {"n": int((m["clase"] == k).sum()),
                       "margen": float(m.loc[m["clase"] == k, "margen_tot"].sum())}
                   for k in CLASES},
    }
    return (m.sort_values("margen_tot", ascending=False).reset_index(drop=True),
            fuera, resumen)


def _solapa(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and \
        a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def rotulos(m, x_max, y_max, alto_px, prioridad):
    """Dónde va el nombre de cada plato en la matriz: `{plato:
    textposition}` para los que entran sin pisar otro nombre, un punto ni el
    rótulo de una esquina, probando derecha, izquierda, arriba y abajo en el
    orden de `prioridad`. El que no entra queda en el cursor. Es la
    colocación de la maqueta: Plotly pone cada texto donde se le dice, y dos
    platos casi iguales —Lomo Saltado y Lomo a la Pimienta— se pisaban."""
    W, H = _ANCHO_TRAZO, alto_px
    pts = {p: (mm / x_max * W, (1 - mg / y_max) * H)
           for p, mm, mg in zip(m["prod"], m["mm"], m["margen"])}
    puntos = [(p, (x - 5, y - 5, 10, 10)) for p, (x, y) in pts.items()]
    puestas = [(0, 0, 110, 14), (W - 80, 0, 80, 14),        # las esquinas
               (0, H - 14, 60, 14), (W - 150, H - 14, 150, 14)]
    salida = {}
    for p in prioridad:
        x, y = pts[p]
        w, h = len(_compras_truncar(p, 22)) * 5.6 + 6, 13
        for pos, bx, by in (("middle right", x + 7, y - h / 2),
                            ("middle left", x - 7 - w, y - h / 2),
                            ("top center", x - w / 2, y - 8 - h),
                            ("bottom center", x - w / 2, y + 8)):
            caja = (bx, by, w, h)
            if bx < 0 or bx + w > W or by < 0 or by + h > H:
                continue
            if any(_solapa(caja, o) for o in puestas) or any(
                    _solapa(caja, c) for q, c in puntos if q != p):
                continue
            puestas.append(caja)
            salida[p] = pos
            break
    return salida


def subgrupos(a):
    """Los `(grupo, sub)` del período, del que más vende al que menos: las
    opciones para armar la categoría."""
    if a is None or a.empty:
        return []
    t = a.groupby(["grupo", "sub"], as_index=False)["neto"].sum()
    t = t[t["neto"] > 0].sort_values("neto", ascending=False)
    return list(zip(t["grupo"], t["sub"]))


# ===========================================================================
# LA TARJETA
# ===========================================================================

def _rotulo(gs):
    return f"{gs[1]} · {gs[0]}"


def _soles(v, dec=2):
    return f"S/ {v:,.{dec}f}"


# ===========================================================================
# LA PIEZA PROPIA (regla #700)
# ===========================================================================
# Desde el 2026-10-22 lo que se ve —las cifras por clase, los cuatro cuadros
# (abre ahí), la matriz y la tabla— es `ventas_menu.js` + `.css`
# (`st.components.v2`), sobre el boceto aprobado
# (https://claude.ai/artifact/Lzua6AASjVigJ8GJktVwM8). La CUENTA no se mudó:
# `clasificar` corre acá y la pieza recibe cada plato ya clasificado, así que
# el método vive en un solo lugar. «Cuadros | Matriz | Tabla» la elige el
# navegador sin una corrida; la categoría (qué subgrupos compiten) sigue en
# Python, porque cambia la clasificación.

_PIEZA = st.components.v2.component(
    "ventas_menu",
    css=css_movil((Path(__file__).parent / "ventas_menu.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent / "ventas_menu.js").read_text(encoding="utf-8")),
)


def _n(v, dec=4):
    return round(float(v), dec) if pd.notna(v) else None


def armar_menu(m, fuera, res, antes, etq_ult, etq_ant, dias):
    """Lo que recibe la pieza. Pura: la lee el test.

    Un plato: [nombre, subgrupo, clase, unidades, % de las unidades,
    pedidos, % de los pedidos, precio neto, costo por plato, % de costo,
    margen por plato, margen total, al límite, clase con pedidos, clase en
    el período anterior], en el orden de `clasificar` (lo que más deja
    primero)."""
    platos = [[str(r.prod), str(r.sub), r.clase, _n(r.u, 2), _n(r.mm), _n(r.pedidos, 0),
               _n(r.mm_ped), _n(r.precio, 2), _n(r.costo_u, 2), _n(r.pct_costo),
               _n(r.margen, 2), _n(r.margen_tot, 2), bool(r.al_limite),
               r.clase_ped or "", antes.get(r.prod, "")]
              for r in m.itertuples()]
    return {
        "platos": platos,
        "resumen": {"n": res["n"], "umbral": res["umbral"], "acm": res["acm"], "u": res["u"],
                    "margen": res["margen"], "piso": res["piso_limite_u"],
                    "pedidos": res["pedidos"],
                    "clases": {k: res["clases"][k] for k in CLASES}},
        "fuera": [[f["plato"], f["motivo"], round(f["precio"], 2), round(f["costo_u"], 2)]
                  for f in fuera],
        "etq": etq_ult, "etq_ant": etq_ant or "", "dias": int(dias),
        "nombres": dict(_NOMBRE), "singular": dict(_SING), "accion": dict(_ACCION),
        "detalle": dict(_DETALLE), "umbrales_costo": [_COSTO_ALTO * 100, _COSTO_ROTO * 100],
    }


def vista_ingenieria(a_ult, etq_ult, dias, a_ant, etq_ant, *, forma, cab,
                     c_cat):
    """La vista, dentro de la tarjeta de Análisis de platos (regla #569): la
    categoría la arma quien mira —su desplegable va en `c_cat`, la columna de
    la fila del Corte—, las cifras por clase van en `cab` —el renglón del
    título, a la derecha del interruptor de la vista— y la clasificación, en
    la forma elegida, en el contenedor desde el que se llama.

    `a_ult` es el agregado por plato del último período de la comparación y
    `a_ant`, el del anterior (para «antes: …»), los dos de
    `ventas_platos.agregar`."""
    ss = st.session_state
    ops = subgrupos(a_ult)
    if not ops:
        st.info("Sin platos con venta en el período para clasificar.")
        return
    rot = {_rotulo(gs): gs for gs in ops}
    # Lo elegido que ya no existe en este período se descarta: un valor fuera
    # de las opciones es un error. Sin nada, el subgrupo que más vende.
    _validas = [x for x in (ss.get("vt_ing_subs") or []) if x in rot]
    ss["vt_ing_subs"] = _validas or [_rotulo(ops[0])]
    with c_cat:
        elegidos = st.multiselect(
            "Categoría", list(rot), key="vt_ing_subs",
            label_visibility="collapsed", persist_state="page",
            placeholder="Subgrupos que compiten entre sí…",
            help="El método compara platos que compiten por la misma "
                 "elección: juntá los subgrupos que van juntos en la "
                 "carta, por ejemplo Fondos con las carnes.")
    subs = [rot[x] for x in elegidos]
    m, fuera, res = clasificar(a_ult, subs)
    if res is None:
        st.info("Elegí al menos un subgrupo con platos para clasificar.")
        return
    antes = {}
    if a_ant is not None:
        m_ant, _f, _r = clasificar(a_ant, subs)
        if not m_ant.empty:
            antes = dict(zip(m_ant["prod"], m_ant["clase"]))
    # Las cifras por clase, la explicación de los cortes, la forma elegida
    # y lo que quedó fuera los dibuja la pieza (regla #700).
    _PIEZA(key="vt_ing_pieza", data=armar_menu(m, fuera, res, antes, etq_ult, etq_ant, dias),
           width="stretch")
