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

from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import (ACENTO, BLANCO, GRIS_TEXTO, GRIS_TEXTO_SUAVE, LAVANDA_FOCO,
                  LAVANDA_FONDO)
from graficos import alturas
from graficos.base import _compras_layout, _compras_truncar
from graficos.ventas_mix import _estilo_costo

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

_KEYS_WIDGET_MENU = ("vt_ing_forma", "vt_ing_subs")
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


def _chips(r, antes, etq_ant):
    """Las marcas de un plato, en HTML: al límite, la clase que tendría
    contado por pedidos, y la que tenía en el período anterior."""
    h = ""
    if r.al_limite:
        h += ('<span class="ing-chip ing-limite" title="A menos de 5 % de un '
              'umbral: su clase puede cambiar con poco. Sólo se marca en los '
              'platos que venden al menos la mitad de lo que pide la '
              'popularidad.">al límite</span>')
    if r.clase_ped and r.clase_ped != r.clase:
        h += (f'<span class="ing-chip" title="Si cada pedido contara una vez">'
              f'con pedidos: {escape(_SING[r.clase_ped].lower())}</span>')
    a = antes.get(r.prod)
    if a and a != r.clase:
        h += (f'<span class="ing-chip ing-antes" title="Su clase en '
              f'{escape(etq_ant or "")}">antes: {escape(_SING[a].lower())}</span>')
    return h


def _html_cab(res):
    """Una cifra por clase, con el dibujo del Resumen (`.vt-cab`). Sin
    título: lo dice el interruptor de la vista, que va a su izquierda, y la
    categoría está en su desplegable (regla #569)."""
    partes = []
    for k in CLASES:
        c = res["clases"][k]
        parte = c["margen"] / res["margen"] if res["margen"] else 0.0
        partes.append(
            f'<div class="vt-kpi" title="{escape(_DETALLE[k])} '
            f'{escape(_ACCION[k])}."><span class="vt-kpi-rot">{_NOMBRE[k]}</span>'
            f'<span class="vt-kpi-val">{c["n"]}<span class="vt-kpi-sub">'
            f'{parte:.0%} del margen</span></span></div>')
    return ('<div class="vt-cab"><div class="vt-kpis">' + "".join(partes)
            + "</div></div>")


def _filas_html(del_k, antes, etq_ant, con_pedidos, tope=_FILAS_CUADRO):
    filas = []
    for r in del_k.head(tope).itertuples():
        ped = (f'<span class="ing-num ing-suave">{r.pedidos:,.0f} ped.</span>'
               if con_pedidos and pd.notna(r.pedidos) else "")
        filas.append(
            f'<li><span class="ing-nom">{escape(r.prod)}'
            f'{_chips(r, antes, etq_ant)}</span>'
            f'<span class="ing-num">{_soles(r.margen)}</span>'
            f'<span class="ing-num ing-suave">{r.u:,.0f} u</span>{ped}</li>')
    resto = len(del_k) - tope
    mas = (f'<p class="ing-mas">y {resto} más: en la Tabla.</p>'
           if resto > 0 else "")
    return "".join(filas), mas


def _cuadros(m, res, antes, etq_ant):
    """Las cuatro clases en cuatro cuadros, en el lugar que ocupan en la
    matriz: arriba lo que deja más, a la derecha lo que se pide más."""
    con_ped = res["pedidos"] is not None
    cuad = {}
    for k in CLASES:
        del_k = m[m["clase"] == k]
        c = res["clases"][k]
        parte = c["margen"] / res["margen"] if res["margen"] else 0.0
        filas, mas = _filas_html(del_k, antes, etq_ant, con_ped)
        cab_cols = ('<li class="ing-cols"><span></span><span>margen/plato</span>'
                    '<span>unid.</span>' + ("<span>pedidos</span>" if con_ped
                                            else "") + "</li>")
        cuerpo = (f'<ul class="ing-filas{" ing-con-ped" if con_ped else ""}">'
                  f'{cab_cols}{filas}</ul>{mas}' if len(del_k)
                  else '<p class="ing-vacio">Ninguno en este período.</p>')
        cuad[k] = (
            f'<div class="ing-cuadro ing-{k}"><div class="ing-tit"><b>'
            f'{_NOMBRE[k]}</b><span>{c["n"]} {"plato" if c["n"] == 1 else "platos"}'
            f' · {parte:.0%} del margen</span></div>'
            f'<p class="ing-acc">{_ACCION[k]} <span>· {_DETALLE[k]}</span></p>'
            f'{cuerpo}</div>')
    st.markdown(
        '<div class="ing-cuadros">'
        '<span class="ing-eje-y">deja más por plato →</span>'
        f'{cuad["rompecabezas"]}{cuad["estrella"]}{cuad["perro"]}{cuad["caballo"]}'
        '<span class="ing-eje-x">se pide más →</span></div>',
        unsafe_allow_html=True)


def _figura(m, res):
    """La matriz: cada plato en su lugar, con los umbrales y los cuadrantes.
    Un solo color: la clase la dice la posición, y los rótulos de las
    esquinas."""
    umbral, acm = res["umbral"], res["acm"]
    x_max = max(umbral * 1.6, float(m["mm"].max())) * 1.08
    y_max = max(acm * 1.5, float(m["margen"].max())) * 1.1
    fig = go.Figure()
    fig.add_shape(type="rect", x0=umbral, x1=x_max, y0=acm, y1=y_max,
                  fillcolor=LAVANDA_FONDO, line_width=0, layer="below")
    for forma in (dict(x0=umbral, x1=umbral, y0=0, y1=y_max),
                  dict(x0=0, x1=x_max, y0=acm, y1=acm)):
        fig.add_shape(type="line", line=dict(color=LAVANDA_FOCO, width=1.5),
                      layer="below", **forma)
    # Primero los que están al límite, después los que más margen dejan: si
    # no hay lugar para todos, se quedan sin nombre los que menos importan.
    prioridad = (list(m.loc[m["al_limite"], "prod"])
                 + list(m.loc[~m["al_limite"], "prod"]))
    pos = rotulos(m, x_max, y_max, alturas.VENTAS_MENU - 50, prioridad)
    for limite in (False, True):
        s = m[m["al_limite"] == limite]
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s["mm"], y=s["margen"], mode="markers+text",
            text=[_compras_truncar(p, 22) if p in pos else "" for p in s["prod"]],
            textposition=[pos.get(p, "middle right") for p in s["prod"]],
            textfont=dict(size=10.5, color=GRIS_TEXTO),
            marker=dict(size=10, symbol="circle-open" if limite else "circle",
                        color=ACENTO, line=dict(color=ACENTO if limite else BLANCO,
                                                width=2)),
            # Una lista y no un `np.stack`: con el nombre adentro, numpy
            # volvería texto a todos los números y el cursor no los formatea.
            customdata=[[r.prod, _SING[r.clase], r.u, r.mm,
                         0 if pd.isna(r.pedidos) else r.pedidos, r.precio,
                         r.costo_u, r.pct_costo, r.margen_tot]
                        for r in s.itertuples()],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>%{customdata[1]}"
                + (" · al límite" if limite else "")
                + "<br>Unidades: %{customdata[2]:,.0f} (%{customdata[3]:.1%})"
                "<br>Pedidos: %{customdata[4]:,.0f}"
                "<br>Precio neto: S/ %{customdata[5]:,.2f}"
                "<br>Costo: S/ %{customdata[6]:,.2f} (%{customdata[7]:.1%})"
                "<br>Margen por plato: S/ %{y:,.2f}"
                "<br>Margen total: S/ %{customdata[8]:,.0f}<extra></extra>"),
            showlegend=False))
    for txt, x, y, xa, ya, color in (
            ("ESTRELLAS", x_max, y_max, "right", "top", ACENTO),
            ("ROMPECABEZAS", 0, y_max, "left", "top", GRIS_TEXTO_SUAVE),
            ("CABALLOS DE BATALLA", x_max, 0, "right", "bottom", GRIS_TEXTO_SUAVE),
            ("PERROS", 0, 0, "left", "bottom", GRIS_TEXTO_SUAVE)):
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False, xanchor=xa,
                           yanchor=ya, font=dict(size=10.5, color=color))
    # Los valores de los dos umbrales no van adentro: con el umbral cerca del
    # borde (Cocteles, 2,3 %) chocaban con los rótulos de las esquinas. Los
    # dice la línea de arriba de la figura.
    _compras_layout(fig, alto=alturas.VENTAS_MENU)
    fig.update_layout(
        margin=dict(l=8, r=8, t=8, b=8), dragmode=False,
        xaxis=dict(range=[0, x_max], tickformat=".0%", fixedrange=True,
                   title=dict(text="Popularidad: % de las unidades",
                              font=dict(size=11, color=GRIS_TEXTO)),
                   tickfont=dict(size=10.5, color=GRIS_TEXTO)),
        yaxis=dict(range=[0, y_max], tickprefix="S/ ", fixedrange=True,
                   showticklabels=True,
                   title=dict(text="Margen por plato",
                              font=dict(size=11, color=GRIS_TEXTO)),
                   tickfont=dict(size=10.5, color=GRIS_TEXTO)))
    return fig


def _matriz(m, res, antes, etq_ant):
    # columnas-internas: la matriz y, al costado, la lista por clase
    c_graf, c_lista = st.columns([1.45, 1], gap="medium")
    with c_graf:
        st.plotly_chart(_figura(m, res), key="vt_ing_fig",
                        config={"displaylogo": False, "displayModeBar": False})
    with c_lista:
        bloques = []
        for k in CLASES:
            del_k = m[m["clase"] == k]
            filas, mas = _filas_html(del_k, antes, etq_ant, False,
                                     _FILAS_LISTA)
            bloques.append(
                f'<div class="ing-bloque"><div class="ing-tit"><b>{_NOMBRE[k]}'
                f'</b><span class="ing-acc">{_ACCION[k]}</span></div>'
                + (f'<ul class="ing-filas">{filas}</ul>{mas}' if len(del_k)
                   else '<p class="ing-vacio">Ninguno en este período.</p>')
                + "</div>")
        st.markdown('<div class="ing-lista">' + "".join(bloques) + "</div>",
                    unsafe_allow_html=True)


def _tabla(m, antes, etq_ant):
    """Cada número de cada plato. Sin vacíos: un NaN se pinta «None» (regla
    #529); sin pedidos va 0, que se escribe «—»."""
    notas = []
    for r in m.itertuples():
        n = []
        if r.al_limite:
            n.append("al límite")
        if r.clase_ped and r.clase_ped != r.clase:
            n.append(f"con pedidos: {_SING[r.clase_ped].lower()}")
        a = antes.get(r.prod)
        if a and a != r.clase:
            n.append(f"antes: {_SING[a].lower()}")
        notas.append(" · ".join(n))
    t = pd.DataFrame({
        "Plato": m["prod"].to_numpy(),
        "Clase": [_SING[k] for k in m["clase"]],
        "Nota": notas,
        "Unid.": m["u"].to_numpy(dtype=float),
        "% unid.": m["mm"].to_numpy(dtype=float),
        "Pedidos": m["pedidos"].fillna(0).to_numpy(dtype=float),
        "% pedidos": m["mm_ped"].fillna(0).to_numpy(dtype=float),
        "Precio neto": m["precio"].to_numpy(dtype=float),
        "Costo": m["costo_u"].to_numpy(dtype=float),
        "% costo": m["pct_costo"].to_numpy(dtype=float),
        "Margen/plato": m["margen"].to_numpy(dtype=float),
        "Margen total": m["margen_tot"].to_numpy(dtype=float),
    })

    def _pct(v):
        return f"{v:.1%}" if v else "—"
    sty = (t.style
           .format(lambda v: f"{v:,.0f}" if v else "—", subset=["Unid.", "Pedidos"])
           .format(_pct, subset=["% unid.", "% pedidos", "% costo"])
           .format(lambda v: _soles(v), subset=["Precio neto", "Costo",
                                              "Margen/plato"])
           .format(lambda v: _soles(v, 0), subset=["Margen total"])
           .map(_estilo_costo, subset=["% costo"]))
    st.dataframe(
        sty, key="vt_ing_tabla", hide_index=True, row_height=27,
        height=alturas.VENTAS_MENU,
        column_config={
            "Plato": st.column_config.TextColumn(pinned=True, width=190),
            "Nota": st.column_config.TextColumn(
                width=170,
                help="«Al límite»: a menos de 5 % de un umbral, sólo en los "
                     "platos que venden al menos la mitad de lo que pide la "
                     "popularidad. «Con pedidos»: la clase si cada pedido "
                     "contara una vez. «Antes»: su clase en "
                     f"{etq_ant or 'el período anterior'}."),
            "% unid.": st.column_config.Column(
                help="Su parte de las unidades de la categoría: la "
                     "popularidad del método"),
            "Pedidos": st.column_config.Column(
                help="En cuántos pedidos aparece: una mesa que pide tres "
                     "cuenta una vez"),
            "% costo": st.column_config.Column(
                help="Costo ÷ venta neta, con los colores del Resumen"),
            "Margen/plato": st.column_config.Column(
                help="Precio neto menos costo, por plato"),
        })


def control_forma():
    """«Cuadros | Matriz | Tabla». Se dibuja en la columna que le da la fila
    del Corte de Análisis de platos, antes de cargar los períodos: no los
    necesita."""
    return st.segmented_control(
        "Forma", FORMAS, default=_FORMA_DEFAULT, required=True,
        key="vt_ing_forma", label_visibility="collapsed", persist_state="page",
        help="Las tres muestran la misma clasificación.") or _FORMA_DEFAULT


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
    with cab:
        st.markdown(_html_cab(res), unsafe_allow_html=True)
    # Qué período se clasifica, dicho con las pastillas a la vista: es el
    # ÚLTIMO de los elegidos arriba, y el «antes: …» sale del penúltimo.
    # Sin el total de pedidos: sería la suma de los de cada plato, y un
    # pedido con dos fondos contaría dos veces. Los de cada plato sí van.
    st.caption(
        f"Se clasifica **{etq_ult}**, el último período elegido"
        + (f"; «antes» es {etq_ant}" if etq_ant else "") + ". "
        f"{dias} días con venta · {res['n']} platos, "
        f"{res['u']:,.0f} unidades, {_soles(res['margen'], 0)} de "
        f"margen. **Popular**: {res['umbral']:.1%} o más de las unidades "
        f"(70 % × 1/{res['n']}). **Deja mucho**: {_soles(res['acm'])} o "
        "más por plato (el promedio ponderado). **Al límite**: a menos de "
        "5 % de un corte, en los platos que venden "
        f"{res['piso_limite_u']:,} unidades o más.")
    if forma == "Matriz":
        _matriz(m, res, antes, etq_ant)
    elif forma == "Tabla":
        _tabla(m, antes, etq_ant)
    else:
        _cuadros(m, res, antes, etq_ant)
    pie = []
    if fuera:
        pie.append("**Fuera**: " + " · ".join(
            f"{f['plato']} ({f['motivo']}"
            + (f": {_soles(f['costo_u'])} de costo contra "
               f"{_soles(f['precio'])}" if f["motivo"].startswith("cuesta")
               else "") + ")" for f in fuera) + ".")
    pie.append("Método: Kasavana y Smith (1982), con las fórmulas de AHLEI. "
               "«Al límite» y «con pedidos» son agregados nuestros.")
    st.caption(" ".join(pie))
