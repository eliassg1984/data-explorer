"""graficos.ajuste._diferencias - la vista «Análisis de diferencias» de Ajuste.

Por qué no cuadra cada línea de un conteo (regla #650). Nació de un boceto
aprobado con los datos reales del cierre de setiembre 2026
(https://claude.ai/artifact/3xBmJP5pVSQpMQ7Ds5gcWo), con dos piezas:

  · A — POSIBLE ORIGEN. La lista de faltantes o sobrantes, una fila por
    línea (producto × área), con su pista principal, y filtros por tipo de
    pista. Arriba, cuánto del faltante y del sobrante tiene una pista fuerte.
    Desde el 2026-10-20 (regla #680) es una pieza propia
    (`lista_diferencias.js`): cada pista es una ficha corta con su número y
    un clic abre lo que la origina; la ficha de B aparece sólo al elegir una
    fila, y los totales de arriba son una tira de un renglón.
  · B — LA FICHA de la línea elegida, al costado, en PESTAÑAS desde el
    2026-10-18 («se verá en laptop»): sus pistas explicadas; la cuenta entre
    los dos conteos con entró y salió POR MOTIVO, el stock en el sistema entre
    ellos y sus ajustes en los últimos cierres; de dónde viene y quién lo
    pide; cómo sale y dónde se usa.

Y desde el mismo día, «Áreas juntas»: una fila por PRODUCTO con las áreas
elegidas sumadas (`da.agrupar_por_producto`) —lo que falta en una y sobra en
otra se compensa—, con la cuenta área por área en la ficha y un botón a cada
línea. El área se elige como en las demás vistas (`filtro_area_en_titulo`).

La cuenta vive en `diferencias_ajuste.py` (puro, con prueba) y la carga en
`data.diferencias_ajuste_sesion`, en caché de disco por sesión. Acá sólo se
dibuja.

Como las demás vistas de Ajuste (regla #632), elige SU sesión con la píldora
‹ [sesión] › (`_comun.selector_sesion`) y su familia en un popover (las cinco
de entrada). La tarjeta NO lleva techo (`estilos/_80_cards.py`): lo que sobra
lo desliza la página, como en Compras › Producto (#382). Dentro, sólo se
desliza la lista.
"""

import html
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import diferencias_ajuste as da
from graficos import alturas
from graficos.base import _compras_layout, filtro_pills, poner_seleccion, sembrar_seleccion
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.ajuste._comun import (
    FAMILIAS_DE_ENTRADA, css_filtros_vista, filtro_area_en_titulo, selector_sesion,
    sesion_vigente, sesiones_de, stats_de_vista, texto_familias,
)
from tema import (
    ACENTO, ACENTO_TEXTO, AJUSTE_ALERTA_BORDE, AJUSTE_ALERTA_FONDO,
    AJUSTE_ALERTA_TEXTO, AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS,
    AJUSTE_POS_TEXTO, BLANCO, GRIS_BORDE, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE, LAVANDA_BORDE,
    LAVANDA_FONDO, LAVANDA_SELECCION, TEXTO_PRINCIPAL,
)

CARD = "ajuste_graf_card_izq_dif"
"""El prefijo `ajuste_graf_card_izq_` le da el marco de las demás tarjetas;
la key entera la saca del techo de una pantalla (`estilos/_80_cards.py`)."""

K_SES = "ajdif_sesion"
K_FAM = "ajdif_filtro_familia"
K_LADO = "ajdif_lado"
K_PISTA = "ajdif_pista"
K_BUSCAR = "ajdif_buscar"
K_AREA = "ajdif_filtro_area"
K_VER = "ajdif_ver"
_K_FOCO = "_ajdif_foco"

LADOS = ("fal", "sob")
VER = ("junto", "area")
"""Una fila por producto, con las áreas elegidas juntas
(`da.agrupar_por_producto`) -- con la que abre la vista, a pedido --, o una
por línea (producto × área)."""
TABS = ("Posible origen", "La cuenta", "De dónde viene", "Dónde se usa")
TABS_JUNTO = ("Posible origen", "Por área", "De dónde viene", "Dónde se usa")
FILTROS = ("todas", "fuerte", "sin") + da.TIPOS
_NOMBRE_FILTRO = {"todas": "Todas", "fuerte": "Con pista fuerte",
                  "sin": "Sin pista", **da.NOMBRE_TIPO}

_SIN_DATOS = ("No se pudo armar el análisis de esta sesión: hace falta el "
              "kardex y las recetas en R2, y que la sesión tenga diferencias.")

_CSS = f"""
<style>
.dif-sub {{ font-size: 12px; color: {GRIS_TEXTO}; margin: -2px 0 0 2px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
/* UNA TIRA (2026-10-20, regla #680, a pedido: «mucha letra»): nombre y
   cifra en el mismo renglón, separados por una raya; hasta ese día eran
   cinco tarjetas de dos renglones (~52px). El comentario, al pasar el
   cursor (`title`), como desde el 2026-10-18. */
.dif-kpis {{ display: flex; flex-wrap: wrap; border: 1px solid {GRIS_LINEA};
             border-radius: 9px; overflow: hidden; margin: 2px 0 2px; }}
.dif-kpi {{ flex: 1 1 auto; padding: 5px 12px; border-right: 1px solid {GRIS_LINEA};
            display: flex; align-items: baseline; gap: 8px; min-width: 0; cursor: help; }}
.dif-kpi:last-child {{ border-right: 0; }}
.dif-kpi .r {{ font-size: 10.5px; letter-spacing: .04em; text-transform: uppercase;
               color: {GRIS_TEXTO}; font-weight: 600; white-space: nowrap;
               overflow: hidden; text-overflow: ellipsis; }}
.dif-kpi .v {{ font-size: 14.5px; font-weight: 700; color: {TEXTO_PRINCIPAL};
               font-variant-numeric: tabular-nums; white-space: nowrap; }}
/* La letra de la app y no la de Streamlit: sin esto las cifras salían en
   Source Sans y los rótulos en DM Sans (medido, 2026-10-20). */
.dif-kpi, .dif-kpi * {{ font-family: "DM Sans", "Inter", -apple-system, BlinkMacSystemFont,
                        sans-serif !important; }}
.dif-neg {{ color: {AJUSTE_NEG_TEXTO} !important; }}
.dif-pos {{ color: {AJUSTE_POS_TEXTO} !important; }}
.dif-n {{ font-size: 15px; font-weight: 700; color: {ACENTO_TEXTO}; line-height: 1.25; }}
.dif-s {{ font-size: 11.5px; color: {GRIS_TEXTO}; }}
.dif-monto {{ font-size: 19px; font-weight: 700; font-variant-numeric: tabular-nums; }}
.dif-monto span {{ font-size: 12px; font-weight: 400; color: {GRIS_TEXTO}; margin-left: 6px; }}
.dif-h {{ font-size: 10.5px; letter-spacing: .05em; text-transform: uppercase;
          color: {GRIS_TEXTO}; font-weight: 600; margin: 4px 0 4px; }}
.dif-pista {{ border: 1px solid {GRIS_LINEA}; border-radius: 8px; padding: 7px 10px;
              font-size: 12.5px; color: {GRIS_TEXTO_MEDIO}; line-height: 1.45; }}
.dif-pista.f {{ border-color: {LAVANDA_BORDE}; background: {LAVANDA_SELECCION}; }}
.dif-pista.receta.f {{ border-color: {AJUSTE_ALERTA_BORDE}; background: {AJUSTE_ALERTA_FONDO}; }}
.dif-pista b {{ color: {TEXTO_PRINCIPAL}; font-size: 13px; }}
.dif-fz {{ font-size: 9.5px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase;
           border-radius: 4px; padding: 0 5px; margin-left: 6px; vertical-align: 1px; }}
.dif-fz.f {{ background: {ACENTO}; color: {BLANCO}; }}
.dif-fz.p {{ border: 1px solid {GRIS_TEXTO_SUAVE}; color: {GRIS_TEXTO}; }}
.dif-ecu {{ display: flex; flex-wrap: wrap; gap: 4px; align-items: center;
            font-variant-numeric: tabular-nums; font-size: 12px; }}
.dif-ecu .c {{ border: 1px solid {GRIS_LINEA}; border-radius: 7px; padding: 3px 7px; }}
.dif-ecu .c i {{ display: block; font-style: normal; font-size: 10px; color: {GRIS_TEXTO}; }}
.dif-ecu .c b {{ font-size: 13.5px; color: {TEXTO_PRINCIPAL}; }}
.dif-ecu .o {{ color: {GRIS_TEXTO}; font-weight: 600; }}
.dif-ecu .c.dn {{ border-color: {AJUSTE_NEG}; }} .dif-ecu .c.dn b {{ color: {AJUSTE_NEG_TEXTO}; }}
.dif-ecu .c.dp {{ border-color: {AJUSTE_POS}; }} .dif-ecu .c.dp b {{ color: {AJUSTE_POS_TEXTO}; }}
.dif-ok {{ font-size: 11.5px; color: {AJUSTE_POS_TEXTO}; margin-top: 4px; }}
.dif-nook {{ font-size: 11.5px; color: {AJUSTE_ALERTA_TEXTO}; margin-top: 4px; }}
.dif-dos {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
            gap: 14px; margin-top: 8px; }}
.dif-mot {{ display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 1px 8px;
            font-size: 12px; padding: 2px 0; border-bottom: 1px solid {GRIS_LINEA};
            color: {GRIS_TEXTO_MEDIO}; }}
.dif-mot .k {{ font-weight: 600; text-align: right; white-space: nowrap;
               font-variant-numeric: tabular-nums; }}
.dif-mot .m {{ color: {GRIS_TEXTO_SUAVE}; font-size: 11px; text-align: right; white-space: nowrap; }}
.dif-t {{ font-size: 12px; font-weight: 700; color: {TEXTO_PRINCIPAL}; margin-bottom: 2px; }}
.dif-nota {{ font-size: 11.5px; color: {GRIS_TEXTO}; }}
/* Lo vendido y sin descontar al contar (#650): una tarjeta más de la fila,
   en ámbar -- hasta el 2026-10-18 era un renglón propio, y ocupaba dos. */
.dif-kpi.al {{ background: {AJUSTE_ALERTA_FONDO}; }}
.dif-kpi.al .r {{ color: {AJUSTE_ALERTA_TEXTO}; }}
.dif-viene {{ font-size: 12.5px; color: {GRIS_TEXTO_MEDIO}; line-height: 1.5; }}
.dif-uso {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 1px 8px;
            padding: 4px 0; border-bottom: 1px solid {GRIS_LINEA}; font-size: 12.5px; }}
.dif-uso .n {{ font-weight: 600; color: {TEXTO_PRINCIPAL}; min-width: 0; }}
.dif-uso .d {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums;
               color: {GRIS_TEXTO_MEDIO}; }}
.dif-uso .x {{ grid-column: 1 / -1; color: {GRIS_TEXTO}; font-size: 11.5px;
               display: flex; flex-wrap: wrap; gap: 3px 6px; align-items: center; }}
.dif-et {{ border: 1px solid {GRIS_BORDE}; border-radius: 4px; padding: 0 5px;
           font-size: 10.5px; white-space: nowrap; }}
.dif-et.aqui {{ border-color: {LAVANDA_BORDE}; background: {LAVANDA_FONDO}; color: {ACENTO_TEXTO}; }}
.dif-et.al {{ border-color: {AJUSTE_ALERTA_BORDE}; background: {AJUSTE_ALERTA_FONDO};
              color: {AJUSTE_ALERTA_TEXTO}; }}
.dif-hist {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 4px;
             align-items: end; height: 74px; }}
.dif-hist div {{ display: grid; grid-template-rows: 1fr auto auto; height: 100%;
                 text-align: center; font-size: 10.5px; color: {GRIS_TEXTO}; }}
.dif-hist i {{ align-self: end; justify-self: center; width: 60%; max-width: 28px;
               border-radius: 3px; }}
.dif-hist .v {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
.dif-hist .ult {{ color: {TEXTO_PRINCIPAL}; font-weight: 700; }}
/* El botón «Ver la otra línea» debajo de su pista, sin el aire del gap. */
.st-key-ajdif_ficha [class*="st-key-ajdif_ir_"] {{ margin-top: -10px; }}
.st-key-ajdif_ficha [class*="st-key-ajdif_ir_"] button {{ min-height: 0; padding: 0 2px;
    font-size: 12px; color: {ACENTO_TEXTO}; }}
/* La ficha abre sólo con una línea elegida (#680): su ✕, arriba a la
   derecha, encima del nombre del producto. */
.st-key-ajdif_ficha {{ position: relative; }}
.st-key-ajdif_cerrar {{ position: absolute; top: -4px; right: 0; z-index: 2; width: auto !important; }}
.st-key-ajdif_cerrar button {{ min-height: 0; padding: 0 6px; font-size: 16px;
    color: {GRIS_TEXTO}; }}
.st-key-ajdif_ficha .dif-n {{ padding-right: 28px; }}
/* El último renglón de la tarjeta: Streamlit le pone −16px abajo a todo
   markdown, y como no sigue nada, la tarjeta se deslizaba por dentro. */
[class*="st-key-ajdif_pie"] [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
/* La cuenta de cada área de un producto con las áreas juntas. */
.dif-partes {{ font-size: 12px; font-variant-numeric: tabular-nums; margin: 2px 0 6px; }}
.dif-partes .h, .dif-partes .f {{ display: grid; gap: 2px 8px; align-items: baseline;
    grid-template-columns: minmax(0, 1.5fr) repeat(5, minmax(0, .8fr)) minmax(0, .9fr); }}
.dif-partes .h {{ color: {GRIS_TEXTO}; font-size: 10.5px; text-transform: uppercase;
    letter-spacing: .04em; border-bottom: 1px solid {GRIS_LINEA}; padding-bottom: 3px; }}
.dif-partes .f {{ padding: 4px 0; border-bottom: 1px solid {GRIS_LINEA}; }}
.dif-partes span {{ text-align: right; white-space: nowrap; }}
.dif-partes .h span:first-child {{ text-align: left; }}
.dif-partes .a {{ text-align: left; font-weight: 600; color: {TEXTO_PRINCIPAL};
    overflow: hidden; text-overflow: ellipsis; }}
.dif-partes .x {{ grid-column: 1 / -1; text-align: left; color: {GRIS_TEXTO}; font-size: 11px;
    white-space: normal; }}
.dif-partes .f.s {{ border-bottom: none; }}
.dif-partes .t {{ font-weight: 700; }}
</style>
"""


# ── números ─────────────────────────────────────────────────────────────

def _soles(v, signo=True):
    if v is None or not np.isfinite(v):
        return "—"
    s = f"S/ {abs(v):,.0f}"
    if round(v) < 0:
        return "−" + s
    return ("+" + s) if signo and round(v) > 0 else s


def _cant(v):
    if v is None or not np.isfinite(v):
        return "—"
    return da.es(v)


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _clave(fila):
    """La identidad de una línea entre corridas: el área y el producto (el
    `id` de la cuenta cambia con la sesión)."""
    return f"{int(fila['acod'])}|{fila['cod']}"


# ── la lista ────────────────────────────────────────────────────────────
#
# UNA PIEZA PROPIA desde el 2026-10-20 (regla #680), como los paneles de
# fecha y de sesión: `lista_diferencias.js` + `.css`, un `st.components.v2`
# sin iframe. Hasta ese día era un `st.dataframe` (regla #650), y una celda
# de `st.dataframe` no tiene nada que se pueda clickear: «Posible origen»
# eran títulos en fila, y para saber de dónde salía cada uno había que abrir
# la ficha. Ahora cada pista es una ficha corta con su número (`dato`, de
# `diferencias_ajuste`) y un clic abre lo que la origina. A Python le llega
# sólo el trigger «fila».
_AQUI = Path(__file__).parent
_LISTA = st.components.v2.component(
    "lista_diferencias_ajuste",
    css=(_AQUI / "lista_diferencias.css").read_text(encoding="utf-8"),
    js=(_AQUI / "lista_diferencias.js").read_text(encoding="utf-8"),
)
_K_LISTA = "ajdif_lista"


def filas_lista(f, fichas, junto):
    """Lo que recibe `lista_diferencias.js`, una entrada por fila de `f`, en
    su orden. Pura (la prueba `test_graficos.py`). `fichas` es, por id, la
    ficha de la línea —o la del producto, con las áreas juntas—, con sus
    pistas en orden: TODAS van a la fila, cada una con su título, si es
    fuerte, su número corto y su texto (el pop lo parte en pasos)."""
    tope = float(f["v"].abs().max()) if len(f) else 1.0
    out = []
    for x in f.to_dict("records"):
        pistas = [{"ti": p_["ti"], "f": bool(p_["f"]), "dato": p_.get("dato") or "",
                   "tx": p_.get("tx") or ""}
                  for p_ in (fichas.get(int(x["id"])) or {}).get("pistas") or []]
        fam = str(x.get("familia") or "").capitalize()
        sub = str(x.get("subfamilia") or "").capitalize()
        u = x.get("u") or "und"
        out.append({
            "k": _clave(x), "p": str(x["producto"]),
            "sub": " › ".join(t for t in (fam, sub) if t) + f" · en {u}",
            "a": str(x["areas"] if junto and x.get("areas") else x["area"]),
            "q": ("+" if x["q"] > 0 else "") + da.es(x["q"]) + " " + u,
            "v": _soles(float(x["v"])), "lado": "neg" if x["q"] < 0 else "pos",
            "peso": round(min(1.0, abs(float(x["v"])) / max(tope, 1e-9)), 3),
            "pistas": pistas,
        })
    return out


def _al_elegir_fila():
    """Callback de la lista: la fila elegida pasa a ser el foco y la ficha
    aparece. Corre ANTES del rerun de la vista."""
    a = (st.session_state.get(_K_LISTA) or {}).get("fila") or {}
    if a.get("k"):
        st.session_state[_K_FOCO] = a["k"]


def _cerrar_ficha():
    st.session_state[_K_FOCO] = None


# ── la ficha ────────────────────────────────────────────────────────────

def _ir(clave, lado, soltar_area=True):
    """Callback de «Ver …»: la otra línea, en su lista y sin filtros que la
    escondan. La ficha se abre en ella."""
    ss = st.session_state
    ss[_K_FOCO] = clave
    ss[K_LADO] = lado
    ss[K_PISTA] = "todas"
    ss[K_BUSCAR] = ""
    ss[K_VER] = "area"
    # La otra línea puede ser de un área que el filtro esconde.
    if soltar_area and ss.get(K_AREA):
        poner_seleccion(K_AREA, [])


def _cabecera_ficha(x):
    lado = "dif-neg" if x["q"] < 0 else "dif-pos"
    fam = str(x["familia"]).capitalize()
    sub = str(x["subfamilia"]).capitalize()
    return (f'<div class="dif-n">{_e(x["producto"])}</div>'
            f'<div class="dif-s">{_e(x["area"])} · {_e(fam)}{" › " + _e(sub) if sub else ""}'
            f' · en {_e(x["u"] or "und")} · S/ {x["precio"]:,.2f} por {_e(x["u"] or "und")}</div>'
            f'<div class="dif-monto {lado}">{_soles(x["v"])}'
            f'<span>{"faltante" if x["q"] < 0 else "sobrante"} · '
            f'{"+" if x["q"] > 0 else ""}{da.es(x["q"])} {_e(x["u"])}</span></div>')


def _pista_html(p):
    # Sin f-strings anidados con las mismas comillas: eso es Python 3.12+
    # (PEP 701), y Cloud puede correr uno anterior.
    mas = " (y %d más)" % p["m"] if p.get("m") else ""
    return (f'<div class="dif-pista {p["t"]} {"f" if p["f"] else ""}"><b>{_e(p["ti"])}</b>'
            f'<span class="dif-fz {"f" if p["f"] else "p"}">{"Fuerte" if p["f"] else "Posible"}</span>'
            f'<br>{_e(p["tx"])}{mas}</div>')


def _cuenta_html(x, fi):
    u = _e(x["u"] or "und")
    t0, t1 = da.fecha_corta(x["t0w"]), da.fecha_corta(x["t1"])
    dif = "dn" if x["q"] < 0 else "dp"
    # Sin conteo anterior en el área, la cuenta arranca con lo que decía el
    # kardex hace DIAS_ATRAS días (#651).
    primero = f"kardex {t0}" if x["sin_ant"] else f"contado {t0}"
    h = ('<div class="dif-ecu">'
         f'<span class="c"><i>{primero}</i><b>{_cant(x["c0w"])}</b></span><span class="o">+</span>'
         f'<span class="c"><i>entró</i><b>{_cant(x["ing"])}</b></span><span class="o">−</span>'
         f'<span class="c"><i>salió</i><b>{_cant(x["sal"])}</b></span><span class="o">=</span>'
         f'<span class="c"><i>sistema {t1}</i><b>{_cant(x["s"])}</b></span><span class="o">→</span>'
         f'<span class="c"><i>contado {t1}</i><b>{_cant(x["k"])}</b></span>'
         f'<span class="c {dif}"><i>diferencia</i><b>{"+" if x["q"] > 0 else ""}{_cant(x["q"])} {u}</b></span>'
         '</div>')
    if x["sin_ant"]:
        antes = (f' Antes, el {da.fecha_corta(x["t0"])} {x["t0"].year}.'
                 if pd.notna(x["t0"]) else "")
        h += (f'<div class="dif-nook">No se había contado en esta área en los últimos '
              f'{da.DIAS_ATRAS} días: la cuenta arranca con lo que decía el kardex.{antes}</div>')
    elif abs(x["gap"]) < 0.01:
        h += (f'<div class="dif-ok">Cuadra con el kardex. Conteo anterior: '
              f'{_e(x["ses0"] or t0)}.</div>')
    else:
        h += (f'<div class="dif-nook">El kardex no cierra por {_cant(x["gap"])} {u}: '
              'hubo movimientos en la misma hora del conteo.</div>')

    def lista(movs, cls):
        if not movs:
            return '<div class="dif-nota">Nada.</div>'
        return "".join(f'<div class="dif-mot"><span>{_e(m)}</span><span class="k {cls}">'
                       f'{_cant(q)} {u}</span><span class="m">{n} mov.</span></div>'
                       for m, q, n in movs)
    h += (f'<div class="dif-dos"><div><div class="dif-t">Entró por</div>{lista(fi["ent"], "dif-pos")}</div>'
          f'<div><div class="dif-t">Salió por</div>{lista(fi["sal"], "dif-neg")}</div></div>')
    return h


def _fig_camino(x, fi):
    """El stock del sistema entre los dos conteos, en escalera, con el cero
    marcado y lo contado al final."""
    cam = fi["camino"]
    fig = go.Figure()
    xs, ys = [c[0] for c in cam], [c[1] for c in cam]
    fig.add_scatter(x=xs, y=ys, mode="lines", line=dict(shape="hv", color=ACENTO, width=2),
                    hovertemplate="%{x|%d/%m %H:%M}: %{y:,.2f}<extra>sistema</extra>")
    color = AJUSTE_NEG if x["q"] < 0 else AJUSTE_POS
    fig.add_scatter(x=[xs[-1]], y=[x["k"]], mode="markers",
                    marker=dict(size=9, color=color),
                    hovertemplate="Contado: %{y:,.2f}<extra></extra>")
    _compras_layout(fig, alto=alturas.DIFERENCIAS_FIG)
    fig.update_layout(showlegend=False, margin=dict(l=4, r=4, t=6, b=4))
    fig.update_xaxes(fixedrange=True, tickformat="%d/%m", showgrid=False,
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    fig.update_yaxes(fixedrange=True, zeroline=True, zerolinecolor=GRIS_BORDE,
                     zerolinewidth=1.5, showticklabels=True,
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    return fig


def _viene_html(x, fi):
    u = x["u"] or "und"
    out = []
    rec = fi["rec"]
    if rec:
        qo, no = rec["ordenes"]
        out.append(f'Es una <b>receta base{" DD" if rec["dd"] else ""}</b>: {rec["prod"]} '
                   f'receta(s) la descargan como producto y {rec["ins"]} por insumo.')
        uo = rec["uo"]
        if uo is not None and pd.notna(uo):
            out.append(f'Última orden de producción: <b>{da.fecha_corta(uo)} {uo.year}</b>'
                       + (f' · entre los dos conteos, {_cant(qo)} {_e(u)} en {no} órdenes.'
                          if no else ' · ninguna entre los dos conteos.'))
        else:
            out.append('<b>Nunca tuvo una orden de producción.</b>')
        if rec["insumos"]:
            mas = rec["n_ins"] - len(rec["insumos"])
            out.append("Se hace con: " + _e(", ".join(rec["insumos"]))
                       + (f" y {mas} más." if mas > 0 else "."))
    v = fi["viene"]
    if v["porc"]:
        up = v["uporc"]
        out.append(f'Sale de porcionar <b>{_e(v["porc"])}</b>'
                   + (f'; el último, el {da.fecha_corta(up)}.' if up is not None and pd.notna(up) else "."))
    if not rec and not v["porc"]:
        out.append(f'Última compra: <b>{da.fecha_corta(v["compra"])}</b>.'
                   if v["compra"] is not None and pd.notna(v["compra"])
                   else f"Sin compras en los últimos {da.DIAS_ATRAS} días.")
    html = '<div class="dif-viene">' + "".join(f"<div>{t}</div>" for t in out) + "</div>"
    return html + _porc_raros_html(x, v.get("raros") or [])


def _porc_raros_html(x, raros):
    """Los porcionamientos raros de este corte entre los dos conteos (#650):
    menos (o más) unidades por lo porcionado que lo habitual, o un precio
    fuera de lo habitual. Van aquí y no como pista: cambian el COSTO del
    corte, no cuántos hay."""
    if not raros:
        return ""
    u = _e(x["u"] or "und")
    filas = []
    for r in raros:
        ui = _e(r["ui"] or "und")
        rend = (f'{da.es(r["rend"], 1)} {u} por {ui}, lo habitual {da.es(r["hab"], 1)}')
        txt = (f'<b>{da.fecha_corta(r["f"])} · N° {_e(r["porc"])}</b>: de '
               f'{da.es(r["qe"])} {ui} de {_e(r["ini_n"])} salieron {da.es(r["qr"])} {u} '
               + (f'(<b>{rend}</b>)' if r["raro_r"] else f'({rend})'))
        if r["pr"] is not None and r["hab_p"]:
            pr = f'S/ {r["pr"]:,.2f} la unidad (lo habitual, S/ {r["hab_p"]:,.2f})'
            txt += f'. Entró a <b>{pr}</b>' if r["raro_p"] else f'. Entró a {pr}'
        filas.append(f"<div>{txt}.</div>")
    return ('<div class="dif-h">Porcionamientos raros entre los dos conteos</div>'
            '<div class="dif-viene">' + "".join(filas) + "</div>"
            '<div class="dif-nota">Cambian el costo de este producto —y el de los platos que '
            'lo llevan—, no cuántos hay: si se cortaron más de los registrados, sobrarían.'
            '</div>')


def _perfil_html(x, fi):
    """Cómo sale el producto (#650): lo de los últimos meses, en el
    restaurante entero, por ventas, producción o notas y de qué tipo."""
    pf = fi.get("perfil")
    if not pf:
        return '<div class="dif-nota">No salió con ningún documento en ese tiempo.</div>'
    u = _e(x["u"] or "und")
    t = pf["total"]
    partes = [("ventas", pf["ventas"]), ("producción o porcionamiento", pf["prod"])]
    h = " · ".join(f"{n} {round(100 * v / t)} %" for n, v in partes if v > 1e-9)
    notas = " · ".join(f"{_e(k)} {round(100 * v / t)} %" for k, v in pf["notas"][:3])
    return ('<div class="dif-viene"><div>' + " · ".join(p for p in (h, notas) if p)
            + f'</div><div class="dif-nota">{_cant(t)} {u} en total</div></div>')


def _pide_html(x, fi):
    """Quién lo pide: los requerimientos del producto por área (#652). No
    mueven consumo, pero dicen qué área lo usa."""
    u = _e(x["u"] or "und")
    filas = []
    for a, q, n, ult, win in fi.get("pide") or []:
        en = f" · entre los dos conteos, {_cant(win)} {u}" if win > 1e-9 else ""
        filas.append(f'<div><b>{_e(str(a).title())}</b>: {_cant(q)} {u} en {n} '
                     f'requerimiento{"s" if n != 1 else ""}, el último el '
                     f'{da.fecha_corta(ult)}{en}</div>')
    for n, a, q, f in fi.get("pend") or []:
        filas.append(f'<div><span class="dif-et al">sin procesar</span> N° {_e(n)} de '
                     f'{_e(str(a).title())}: {_cant(q)} {u}, el {da.fecha_corta(f)}</div>')
    if not filas:
        return '<div class="dif-nota">Nadie lo pidió por requerimiento en los últimos 90 días.</div>'
    return '<div class="dif-viene">' + "".join(filas) + "</div>"


def _usos_html(x, fi):
    u = _e(x["u"] or "und")
    if not fi["usos"]:
        return '<div class="dif-nota">Ningún plato, receta base ni porcionamiento lo usa.</div>'
    h = []
    for o in fi["usos"]:
        via = o["via"]
        if via == "combo":
            nombre = "Combo " + _e(o["n"])
            como = ("fijo" if o["fijo"] else
                    "una de %d opciones del grupo «%s»" % (o["n_op"], _e(o["g"].lower())))
            cuanto = (f'{_e(o["plato"])} · {como}'
                      f' · {o["nv"]:,.0f} vendidos entre los dos conteos')
            et = ""
            if o["a"]:
                et += (f'<span class="dif-et {"aqui" if o["aqui"] else ""}">'
                       + ("desde esta área" if o["aqui"] else "desde " + _e(str(o["a"]).title()))
                       + "</span>")
            if not o["fijo"] and o.get("hasta"):
                et += f'<span class="dif-et">si todos lo eligieron, {_cant(o["hasta"])} {u}</span>'
        elif via == "porc":
            nombre = "Porcionamiento → " + _e(o["n"])
            cuanto = (f'{_cant(o["nv"])} {u} porcionados en {o["no"]}' if o.get("no")
                      else "ninguno entre los dos conteos")
            et = ""
        else:
            nombre = _e(o["n"])
            if via == "receta":
                cuanto = (f'{_cant(o["q"])} {u} por unidad · '
                          + (f'{_cant(o["nv"])} producidas en {o["no"]} órdenes' if o.get("no")
                             else "ninguna orden entre los dos conteos"))
                et = '<span class="dif-et">receta base · al producirla</span>'
            else:
                cuanto = f'{_cant(o["q"])} {u} por plato · {o["nv"]:,.0f} vendidos'
                et = ('<span class="dif-et">dentro de ' + _e(o["por"])
                      + ', que se descarga por insumo</span>') if via == "plato_ins" else ""
            if o["a"]:
                et += (f'<span class="dif-et {"aqui" if o["aqui"] else ""}">'
                       + ("desde esta área" if o["aqui"] else "desde " + _e(str(o["a"]).title()))
                       + "</span>")
            else:
                et += '<span class="dif-et">descargo directo</span>'
            if o["t"] == "INSUMO":
                et += '<span class="dif-et al">por insumo: descuenta sus insumos, no este producto</span>'
        if o.get("ed") is not None:
            et += f'<span class="dif-et al">receta editada {da.fecha_corta(o["ed"])}</span>'
        if o.get("cc"):
            et += (f'<span class="dif-et">costo por plato S/ {o["cc"][0]:,.2f} → '
                   f'S/ {o["cc"][1]:,.2f} · este producto aporta S/ {o["ap"]:,.2f}</span>')
        d = (f'≈ {_cant(o["d"])} {u}' if o["d"] else
             f'hasta {_cant(o["hasta"])} {u}' if o.get("hasta") else "—")
        h.append(f'<div class="dif-uso"><div class="n">{nombre}</div><div class="d">{d}</div>'
                 f'<div class="x">{cuanto} {et}</div></div>')
    mas = fi["usos_n"] - len(fi["usos"])
    return "".join(h) + (f'<div class="dif-nota">y {mas} usos más.</div>' if mas > 0 else "")


def _hist_html(fi):
    vals = [abs(h[2]) for h in fi["hist"] if h[2] is not None]
    tope = max(vals) if vals else 1.0
    out = []
    for j, (lab, _q, v) in enumerate(fi["hist"]):
        alto = 0 if v is None else max(2.0, 40.0 * abs(v) / max(tope, 1e-9))
        color = "transparent" if v is None else (AJUSTE_NEG if v < 0 else AJUSTE_POS)
        cls = "dif-neg" if v is not None and v < 0 else "dif-pos" if v else ""
        txt = "—" if v is None else ("0" if abs(v) < 0.5 else _soles(v))
        ult = " ult" if j == len(fi["hist"]) - 1 else ""
        out.append(f'<div><i style="height:{alto:.0f}px;background:{color}"></i>'
                   f'<span class="v {cls}">{txt}</span><span class="{ult}">{lab}</span></div>')
    return '<div class="dif-hist">' + "".join(out) + "</div>"


def _pistas(fi, por_clave, vacio):
    """Las pistas de la ficha, con «Ver …» debajo de las que nombran otra
    línea (sólo en la vista por área: `por_clave` vacío la apaga)."""
    if not fi["pistas"]:
        st.markdown(f'<div class="dif-nota">{vacio}</div>', unsafe_allow_html=True)
    for j, p in enumerate(fi["pistas"]):
        st.markdown(_pista_html(p), unsafe_allow_html=True)
        ref = por_clave.get(p.get("r"))
        if ref is not None:
            st.button(f'Ver {ref["producto"]} · {ref["area"]} →', key=f"ajdif_ir_{j}",
                      type="tertiary", on_click=_ir,
                      args=(_clave(ref), "fal" if ref["q"] < 0 else "sob"))


def _viene_y_usos(x, fi, tab_viene, tab_usos):
    """Las dos pestañas que no cambian entre una línea y un producto con las
    áreas juntas: de dónde viene (y quién lo pide) y dónde se usa (y cómo
    sale)."""
    with tab_viene, st.container(key="ajdif_pie_viene"):
        st.markdown(_viene_html(x, fi)
                    + '<div class="dif-h">Quién lo pide (requerimientos, 90 días)</div>'
                    + _pide_html(x, fi), unsafe_allow_html=True)
    with tab_usos, st.container(key="ajdif_pie_usos"):
        st.markdown(f'<div class="dif-h">Cómo sale ({da.DIAS_ATRAS} días antes del conteo)</div>'
                    + _perfil_html(x, fi)
                    + '<div class="dif-h">Dónde se usa</div>'
                    '<div class="dif-nota">Lo que lo descarga, con lo vendido o producido entre '
                    'los dos conteos. «≈» es recetas × vendido: una referencia, no el kardex. '
                    '«Receta editada» marca las que cambiaron desde el conteo anterior.</div>'
                    + _usos_html(x, fi), unsafe_allow_html=True)


def _ficha(x, fi, por_clave):
    """La ficha de una línea, en PESTAÑAS (pedido 2026-10-18: «se verá en
    laptop», y una debajo de otra desbordaba la pantalla). La pestaña
    elegida se queda al cambiar de línea: tiene key y los mismos nombres."""
    st.markdown(_cabecera_ficha(x), unsafe_allow_html=True)
    t_or, t_cu, t_vi, t_us = st.tabs(list(TABS), key="ajdif_tabs")
    with t_or, st.container(key="ajdif_pie_origen"):
        _pistas(fi, por_clave, "Ninguna pista: ni otra área, ni la producción, ni el conteo "
                "anterior la explican. Es de las que hay que mirar a mano.")
    with t_cu:
        st.markdown(_cuenta_html(x, fi), unsafe_allow_html=True)
        if len(fi["camino"]) >= 2:
            st.plotly_chart(_fig_camino(x, fi), width="stretch", key="ajdif_camino",
                            config={"displaylogo": False, "displayModeBar": False})
        with st.container(key="ajdif_pie_cuenta"):
            st.markdown('<div class="dif-h">Sus ajustes en los últimos cierres</div>'
                        + _hist_html(fi), unsafe_allow_html=True)
    _viene_y_usos(x, fi, t_vi, t_us)


def _cabecera_junto(x):
    lado = "dif-neg" if x["q"] < 0 else "dif-pos"
    fam = str(x["familia"]).capitalize()
    sub = str(x["subfamilia"]).capitalize()
    return (f'<div class="dif-n">{_e(x["producto"])}</div>'
            f'<div class="dif-s">{_e(x["areas"])} · {_e(fam)}{" › " + _e(sub) if sub else ""}'
            f' · en {_e(x["u"] or "und")}</div>'
            f'<div class="dif-monto {lado}">{_soles(x["v"])}'
            f'<span>{"faltante" if x["q"] < 0 else "sobrante"} con las áreas juntas · '
            f'{"+" if x["q"] > 0 else ""}{da.es(x["q"])} {_e(x["u"])}</span></div>')


def _partes_html(x, fg):
    """La cuenta de cada área del producto, una fila por área, y la suma."""
    u = _e(x["u"] or "und")
    cab = ("<span>Área</span><span>Antes</span><span>Entró</span><span>Salió</span>"
           "<span>Sistema</span><span>Contado</span><span>Dif.</span>")
    filas = []
    for r in fg["partes"]:
        cls = "dif-neg" if r["q"] < 0 else "dif-pos"
        filas.append(f'<span class="a">{_e(r["area"])}</span><span>{_cant(r["c0w"])}</span>'
                     f'<span>{_cant(r["ing"])}</span><span>{_cant(r["sal"])}</span>'
                     f'<span>{_cant(r["s"])}</span><span>{_cant(r["k"])}</span>'
                     f'<span class="{cls}">{"+" if r["q"] > 0 else ""}{_cant(r["q"])}</span>'
                     f'<span class="x">{_e(r["pista"] or "sin pista")}</span>')
    tot = ("dif-neg" if x["q"] < 0 else "dif-pos")
    pie = (f'<span class="a t">Juntas</span><span></span><span></span><span></span>'
           f'<span class="t">{_cant(x["s"])}</span><span class="t">{_cant(x["k"])}</span>'
           f'<span class="t {tot}">{"+" if x["q"] > 0 else ""}{_cant(x["q"])} {u}</span>')
    nota = ""
    if any(np.sign(r["q"]) != np.sign(x["q"]) for r in fg["partes"] if abs(r["q"]) > 1e-6):
        nota = ('<div class="dif-nota">Un área tiene faltante y otra sobrante: juntas, se '
                'compensan en parte (un traslado o un requerimiento sin registrar).</div>')
    return (f'<div class="dif-partes"><div class="h">{cab}</div>'
            + "".join(f'<div class="f">{f_}</div>' for f_ in filas)
            + f'<div class="f s">{pie}</div></div>' + nota)


def _ficha_junto(x, fg, fichas):
    """La ficha de un producto con las áreas JUNTAS (2026-10-18): sus pistas
    —las de las áreas del lado de la suma—, la cuenta área por área con un
    botón a cada línea, y de dónde viene y dónde se usa (los de su línea
    más grande)."""
    st.markdown(_cabecera_junto(x), unsafe_allow_html=True)
    t_or, t_ar, t_vi, t_us = st.tabs(list(TABS_JUNTO), key="ajdif_tabs_junto")
    with t_or, st.container(key="ajdif_pie_origen"):
        _pistas(fg, {}, "Ninguna pista en las áreas del lado de la suma: hay que mirarlo a "
                "mano, o área por área.")
    with t_ar:
        st.markdown(_partes_html(x, fg), unsafe_allow_html=True)
        with st.container(key="ajdif_pie_partes"):
            for j, r in enumerate(fg["partes"]):
                st.button(f'Ver la línea de {r["area"]} →', key=f"ajdif_ir_parte_{j}",
                          type="tertiary", on_click=_ir,
                          args=(_clave(r), "fal" if r["q"] < 0 else "sob", False))
    base = next(r for r in fg["partes"] if int(r["id"]) == fg["base"])
    _viene_y_usos(base, fichas[fg["base"]], t_vi, t_us)


# ── la vista ────────────────────────────────────────────────────────────

def _tarjeta(rotulo, valor, ayuda, cls="", cls_valor=""):
    """Una tarjeta de la fila de totales: el nombre y la cifra; el
    comentario, al pasar el cursor."""
    return (f'<div class="dif-kpi {cls}" title="{html.escape(ayuda, quote=True)}">'
            f'<span class="r">{_e(rotulo)}</span>'
            f'<span class="v {cls_valor}">{valor}</span></div>')


def _kpis(f, extra="", que="líneas"):
    fal, sob, pf, ps, sin = da.cobertura(f)
    nf, ns = int((f["q"] < 0).sum()), int((f["q"] > 0).sum())
    sin_f = int(((f["n_pistas"] == 0) & (f["q"] < 0)).sum())
    return ('<div class="dif-kpis">'
            + _tarjeta("Faltó", _soles(-fal), f"{nf:,} {que} con faltante.", cls_valor="dif-neg")
            + _tarjeta("Sobró", _soles(sob), f"{ns:,} {que} con sobrante.", cls_valor="dif-pos")
            + _tarjeta("Con pista fuerte", f"{round(pf * 100)} % · {round(ps * 100)} %",
                       "Cuánto del faltante y del sobrante, en soles, tiene una pista fuerte: "
                       "los números calzan o es un hecho del kardex.", cls="a")
            + _tarjeta("Sin ninguna pista", f"{sin:,} {que}",
                       f"{sin_f:,} faltantes y {sin - sin_f:,} sobrantes sin ninguna pista: hay "
                       "que mirarlas a mano.", cls="a")
            + extra + '</div>')


def _kpi_sin_descontar(lin, lote):
    """La tarjeta de lo vendido que el POS todavía no había descontado al
    contar (#650): figura como faltante sin ser pérdida. Dice cuánto era de
    días ANTERIORES al conteo —el ajuste se abre después de descargar hasta
    el día anterior: eso no debía estar—; el detalle entero, al pasar el
    cursor. Vacío si es poco."""
    if not lote or lote.get("ultimo") is None or "pend_v" not in lin.columns:
        return ""
    v = float(lin["pend_v"].sum())
    if v < 20:
        return ""
    n = int((lin["pend"] > 1e-9).sum())
    nunca = float(lin["pend_nunca_v"].sum()) if "pend_nunca_v" in lin.columns else 0.0
    ant = float(lin["pend_ant_v"].sum()) if "pend_ant_v" in lin.columns else 0.0
    dias = da.dias_txt(lote.get("dias_antes") or [])
    sig, desde = lote.get("siguiente"), lote.get("desde")
    exacto = bool(lote.get("exacto"))
    ayuda = (f"Al contar, el Descargo de Ventas no había bajado lo vendido desde el último, el "
             f"{da.cuando(lote['ultimo'], minutos=exacto)}: ≈ {_soles(v, signo=False)} a costo en "
             f"{n:,} líneas, que figuran como faltante sin ser pérdida.")
    if ant >= 1 and dias:
        ayuda += (f" {_soles(ant, signo=False)} son del {dias}: el ajuste se abre después de "
                  "descargar las ventas hasta el día anterior, y no se descargaron.")
    if sig is not None and desde is not None and nunca >= 1:
        ayuda += (f" El Descargo de Ventas siguiente, el {da.fecha_corta(sig)}, tomó lo vendido "
                  f"desde el {da.cuando(desde, minutos=exacto)}: {_soles(nunca, signo=False)} no "
                  "se descargarán nunca; el resto volverá como sobrante en el próximo conteo.")
    elif sig is not None:
        ayuda += (f" El Descargo de Ventas siguiente fue el {da.fecha_corta(sig)}: lo que tomó volverá "
                  "como sobrante en el próximo conteo.")
    ayuda += " Están en la pista «Sin descargar»."
    return _tarjeta("Sin descargar al contar", _soles(v, signo=False), ayuda, cls="al")


def vista_diferencias(df_full, col_fecha, col_familia, col_area, col_ajuste_val,
                      col_producto):
    """La vista «Análisis de diferencias» (regla #650)."""
    ss = st.session_state
    titulo = "Análisis de diferencias"
    sesiones = sesiones_de(df_full, col_fecha)
    opc_fam = (sorted(df_full[col_familia].dropna().astype(str).unique().tolist())
               if col_familia and col_familia in df_full.columns else [])
    sembrar_seleccion(pd.DataFrame({col_familia or "f": opc_fam}), col_familia or "f",
                      K_FAM, list(FAMILIAS_DE_ENTRADA))
    fam_sel = [f for f in (ss.get(K_FAM) or []) if f in opc_fam]
    with st.container(border=True, key=CARD):
        st.markdown(CSS_TITULOS_DRILL + _CSS + "<style>"
                    + css_filtros_vista("ajdif_ctrl_", "ajdif_nolist_") + "</style>",
                    unsafe_allow_html=True)
        # columnas-internas: título, la sesión, el área y la familia, en UN renglón.
        c_t, c_s, c_a, c_f = st.columns([2.2, 1.6, 0.95, 0.95], vertical_alignment="center")
        with c_s:
            if sesiones:
                selector_sesion(
                    "ajses_dif", K_SES, sesiones,
                    stats=stats_de_vista(df_full, sesiones, col_fecha, col_area,
                                         col_ajuste_val, col_producto, col_familia,
                                         fam_sel),
                    familias_txt=texto_familias(fam_sel),
                    pie=["Cada línea se compara con SU conteo anterior: el último de ese "
                         "producto en esa área, que puede ser un parcial.",
                         "Elegir acá cambia sólo esta vista."])
        with c_f.container(key="ajdif_ctrl_familia"):
            et = ("todas las familias" if not fam_sel
                  else f"{len(fam_sel)} familias" if len(fam_sel) > 1 else fam_sel[0].lower())
            with st.popover(f":material/category: {et}", use_container_width=True):
                filtro_pills(pd.DataFrame({"familia": opc_fam}), "familia", K_FAM, "Familia",
                             valores=opc_fam or None)
        s = sesion_vigente(K_SES, sesiones) if sesiones else None
        with c_t:
            st.markdown(
                f'<div class="inv-rank-tit" title="{titulo}">{titulo}</div>'
                f'<div class="dif-sub">{_e(s["nombre"] if s else "")}'
                f'{" · " + _e(s["etiqueta_anio"]) if s else ""} · por qué falta o sobra '
                'cada producto en cada área</div>', unsafe_allow_html=True)
        if s is None:
            st.info("Sin sesiones de inventario.")
            return
        with st.spinner("Cruzando el conteo con el kardex y las recetas…"):
            r = data.diferencias_ajuste_sesion(s["clave"])
        if r is None:
            st.info(_SIN_DATOS)
            return
        lin = r["lineas"]
        if fam_sel:
            lin = lin[lin["familia"].isin([f.upper() for f in fam_sel])]
        # El área se elige con las líneas de la sesión a la vista: las áreas
        # que tienen alguna diferencia.
        lin = filtro_area_en_titulo(c_a, lin, "area", "v", K_AREA, "ajdif_ctrl_area")

        # Por área (una fila por línea) o con las áreas JUNTAS (una por
        # producto: lo que falta en una y sobra en otra se compensa). Se lee
        # antes de dibujar el control: los totales de arriba dependen de él.
        if ss.get(K_VER) not in VER:
            ss[K_VER] = "junto"
        junto = ss[K_VER] == "junto"
        G = FG = None
        lista = lin
        if junto:
            G, FG = da.agrupar_por_producto(lin, r["fichas"])
            lista = G[~G["comp"]]
        st.markdown(_kpis(lista, _kpi_sin_descontar(lin, r["resumen"].get("lote")),
                          que="productos" if junto else "líneas"),
                    unsafe_allow_html=True)

        # El lado, la pista y el buscador. Lo elegido se corrige ANTES de
        # dibujar cada widget: una opción que deja de estar lo revienta.
        if ss.get(K_LADO) not in LADOS:
            ss[K_LADO] = LADOS[0]
        lado = ss[K_LADO]
        # El lado lo dice la CANTIDAD: una línea sin precio vale S/ 0 y sigue
        # siendo un faltante o un sobrante (#651).
        base = lista[lista["q"] < 0] if lado == "fal" else lista[lista["q"] > 0]
        q = (ss.get(K_BUSCAR) or "").strip().lower()
        if q:
            donde = base["areas"] if junto else base["area"]
            base = base[(base["producto"].str.lower() + " " + donde.str.lower())
                        .str.contains(q, regex=False)]
        tipos = base["tipos"].str.split(",")
        cuenta = {"todas": len(base), "fuerte": int(base["fuerte"].sum()),
                  "sin": int((base["n_pistas"] == 0).sum())}
        for t in da.TIPOS:
            cuenta[t] = int(tipos.map(lambda ts, t=t: t in ts).sum())
        opciones = [o for o in FILTROS if cuenta[o] or o == "todas"]
        if ss.get(K_PISTA) not in opciones:
            ss[K_PISTA] = "todas"
        # columnas-internas: el lado, juntas o por área, la pista y el
        # buscador, en UN renglón (las pistas fueron pastillas en dos
        # renglones hasta el 2026-10-18: «no deseo que me ocupen dos filas»).
        c_l, c_v, c_p, c_b = st.columns([1.55, 1.25, 1.45, 1.05], vertical_alignment="center")
        with c_l:
            n_fal, n_sob = int((lista["q"] < 0).sum()), int((lista["q"] > 0).sum())
            st.segmented_control(
                "Lado", LADOS, key=K_LADO, required=True, label_visibility="collapsed",
                format_func=lambda o: f"Faltantes · {n_fal}" if o == "fal" else f"Sobrantes · {n_sob}")
        with c_v:
            st.segmented_control(
                "Ver", VER, key=K_VER, required=True, label_visibility="collapsed",
                format_func=lambda o: "Por área" if o == "area" else "Áreas juntas",
                help="«Áreas juntas» suma cada producto en las áreas elegidas: lo que falta "
                     "en una y sobra en otra se compensa.")
        with c_p:
            st.selectbox("Posible origen", opciones, key=K_PISTA, label_visibility="collapsed",
                         format_func=lambda o: ("Todas las pistas" if o == "todas"
                                                else _NOMBRE_FILTRO[o]) + f" · {cuenta[o]}")
        with c_b:
            st.text_input("Buscar", key=K_BUSCAR, placeholder="Buscar producto o área",
                          label_visibility="collapsed")
        filtro = ss.get(K_PISTA) or "todas"
        f = base
        if filtro == "fuerte":
            f = f[f["fuerte"]]
        elif filtro == "sin":
            f = f[f["n_pistas"] == 0]
        elif filtro != "todas":
            f = f[tipos.loc[f.index].map(lambda ts: filtro in ts)]
        f = f.sort_values(["v", "q"], ascending=(lado == "fal"),
                          kind="stable").reset_index(drop=True)

        if f.empty:
            st.info("Ninguna línea con estos filtros.")
            return
        # LA FICHA APARECE SÓLO CON UNA LÍNEA ELEGIDA (2026-10-20, regla #680, a
        # pedido: «mucha letra»). Sin foco la lista usa todo el ancho; un clic
        # en una fila la abre al costado y ✕ la cierra. Un foco que dejó de
        # estar en la lista (otro filtro, otra sesión) no abre nada.
        claves = [_clave(x) for x in f.to_dict("records")]
        foco = ss.get(_K_FOCO)
        if foco not in claves:
            foco = None
        fichas_lista = FG if junto else r["fichas"]
        if foco is None:
            c_tab, c_fic = st.container(), None
        else:
            # columnas-internas: la lista y la ficha de la línea elegida.
            c_tab, c_fic = st.columns([1.45, 1], gap="medium")
        with c_tab:
            _LISTA(key=_K_LISTA, data={
                "filas": filas_lista(f, fichas_lista, junto), "sel": foco,
                # Tope de una laptop (`DIFERENCIAS_TABLA`): la ficha de al
                # lado va en pestañas y mide lo mismo.
                "alto": alturas.DIFERENCIAS_TABLA,
                "neg": AJUSTE_NEG_TEXTO, "pos": AJUSTE_POS_TEXTO,
                "vacio": "Ninguna línea con estos filtros."},
                on_fila_change=_al_elegir_fila, width="stretch")
            with st.container(key="ajdif_pie_lista"):
                if junto:
                    comp = G[G["comp"]]
                    extra = (f" · {len(comp):,} se compensan entre áreas y no aparecen"
                             if len(comp) else "")
                    st.caption(f"{len(f):,} producto{'s' if len(f) != 1 else ''} · "
                               f"{_soles(float(f['v'].sum()))}{extra} · clic en una fila para "
                               "ver su ficha; en una pista, para ver de dónde sale.")
                else:
                    st.caption(f"{len(f):,} línea{'s' if len(f) != 1 else ''} · "
                               f"{_soles(float(f['v'].sum()))} · ordenada por soles · clic en "
                               "una fila para ver su ficha; en una pista, para ver de dónde "
                               "sale.")
        if c_fic is None:
            return
        with c_fic, st.container(key="ajdif_ficha"):
            st.button("✕", key="ajdif_cerrar", help="Cerrar la ficha", type="tertiary",
                      on_click=_cerrar_ficha)
            x = f.iloc[claves.index(foco)]
            if junto:
                _ficha_junto(x, FG[int(x["id"])], r["fichas"])
            else:
                por_clave = {int(i): fila for i, fila in
                             zip(r["lineas"]["id"], r["lineas"].to_dict("records"))}
                _ficha(x, r["fichas"][int(x["id"])], por_clave)
