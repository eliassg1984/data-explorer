"""graficos.ajuste._diferencias - la vista «Análisis de diferencias» de Ajuste.

Por qué no cuadra cada línea de un conteo (regla #650). Nació de un boceto
aprobado con los datos reales del cierre de setiembre 2026
(https://claude.ai/artifact/3xBmJP5pVSQpMQ7Ds5gcWo), con dos piezas:

  · A — POSIBLE ORIGEN. La lista de faltantes o sobrantes, una fila por
    línea (producto × área), con su pista principal, y filtros por tipo de
    pista. Arriba, cuánto del faltante y del sobrante tiene una pista fuerte.
  · B — LA FICHA de la línea elegida, al costado: sus pistas explicadas, la
    cuenta entre los dos conteos con entró y salió POR MOTIVO, el stock en el
    sistema entre ellos, de dónde viene, dónde se usa y sus ajustes en los
    últimos cierres.

La cuenta vive en `diferencias_ajuste.py` (puro, con prueba) y la carga en
`data.diferencias_ajuste_sesion`, en caché de disco por sesión. Acá sólo se
dibuja.

Como las demás vistas de Ajuste (regla #632), elige SU sesión con la píldora
‹ [sesión] › (`_comun.selector_sesion`) y su familia en un popover (las cinco
de entrada). La tarjeta NO lleva techo (`estilos/_80_cards.py`): la ficha es
más alta que una pantalla, y lo que sobra lo desliza la página, como en
Compras › Producto (#382). Dentro, sólo se desliza la lista.
"""

import hashlib
import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import diferencias_ajuste as da
from graficos import alturas
from graficos.base import _compras_layout, filtro_pills, sembrar_seleccion
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.ajuste._comun import (
    FAMILIAS_DE_ENTRADA, css_filtros_vista, selector_sesion, sesion_vigente,
    sesiones_de, stats_de_vista, texto_familias,
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
_K_FOCO = "_ajdif_foco"
_K_SALTO = "_ajdif_salto"
_K_TABLA = "_ajdif_key"
_K_FILAS = "_ajdif_filas"

LADOS = ("fal", "sob")
FILTROS = ("todas", "fuerte", "sin") + da.TIPOS
_NOMBRE_FILTRO = {"todas": "Todas", "fuerte": "Con pista fuerte",
                  "sin": "Sin pista", **da.NOMBRE_TIPO}
_ICONO = {"receta": ":material/error:", "prod": ":material/precision_manufacturing:",
          "area": ":material/swap_horiz:", "neg": ":material/remove:",
          "rev": ":material/undo:", "nada": ":material/block:",
          "combo": ":material/restaurant_menu:",
          "nadie": ":material/no_meals:", "rubro": ":material/compare_arrows:"}

_SIN_DATOS = ("No se pudo armar el análisis de esta sesión: hace falta el "
              "kardex y las recetas en R2, y que la sesión tenga diferencias.")

_CSS = f"""
<style>
.dif-sub {{ font-size: 12px; color: {GRIS_TEXTO}; margin: -2px 0 0 2px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.dif-kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr));
             gap: 8px; margin: 2px 0 2px; }}
.dif-kpi {{ border: 1px solid {GRIS_LINEA}; border-radius: 10px; padding: 6px 10px;
            display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
.dif-kpi.a {{ border-color: {LAVANDA_BORDE}; background: {LAVANDA_SELECCION}; }}
.dif-kpi .r {{ font-size: 10.5px; letter-spacing: .04em; text-transform: uppercase;
               color: {GRIS_TEXTO}; font-weight: 600; white-space: nowrap;
               overflow: hidden; text-overflow: ellipsis; }}
.dif-kpi .v {{ font-size: 18px; font-weight: 700; color: {TEXTO_PRINCIPAL};
               font-variant-numeric: tabular-nums; line-height: 1.2; }}
.dif-kpi .d {{ font-size: 11.5px; color: {GRIS_TEXTO}; }}
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
/* El último renglón de la tarjeta: Streamlit le pone −16px abajo a todo
   markdown, y como no sigue nada, la tarjeta se deslizaba por dentro. */
.st-key-ajdif_pie [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
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


# ── la tabla ────────────────────────────────────────────────────────────

def _filas_sel(ev):
    try:
        return (ev.get("selection") or {}).get("rows") or []
    except AttributeError:
        return getattr(getattr(ev, "selection", None), "rows", []) or []


def _foco_anterior():
    """La línea que la tabla tenía elegida en la corrida anterior. Se lee
    ANTES de dibujar (regla #556): la selección es de la KEY, no de las
    filas, y la key cambia con ellas."""
    ss = st.session_state
    key, claves = ss.get(_K_TABLA), ss.get(_K_FILAS) or []
    filas = _filas_sel(ss.get(key) or {}) if key else []
    if filas and 0 <= filas[0] < len(claves):
        ss[_K_FOCO] = claves[filas[0]]


def _key_tabla(claves):
    firma = hashlib.md5("|".join(claves).encode("utf-8")).hexdigest()[:12]
    return f"ajdif_tabla_{firma}_{st.session_state.get(_K_SALTO, 0)}"


def _tabla(f):
    return pd.DataFrame({
        "Producto": f["producto"].tolist(),
        "Área": f["area"].tolist(),
        "Dif.": f["q"].tolist(),
        "S/": f["v"].tolist(),
        "Posible origen": [(p + (f"  +{n - 1}" if n > 1 else "")) if p else "—"
                           for p, n in zip(f["pista"], f["n_pistas"])],
    })


def _estilo(tabla, f, pos):
    """Formato y colores por COLUMNA entera (regla #645: fila por fila
    costaba casi un segundo por clic)."""
    sty = tabla.style.format({"S/": lambda v: _soles(v)})
    # La unidad va DENTRO de «Dif.» (una columna menos) sin volverla texto:
    # un formato por unidad, y la columna se sigue ordenando por número.
    u = f["u"].replace("", "und").to_numpy()
    for un in sorted(set(u)):
        filas = np.flatnonzero(u == un).tolist()
        sty = sty.format(lambda v, un=un: ("+" if v > 0 else "") + da.es(v) + " " + un,
                         subset=pd.IndexSlice[filas, ["Dif."]])
    sty = sty.set_properties(subset=pd.IndexSlice[[pos], :],
                             **{"background-color": LAVANDA_FONDO})
    rojo, verde = f"color: {AJUSTE_NEG_TEXTO}", f"color: {AJUSTE_POS_TEXTO}"
    sty = sty.apply(lambda c: np.where(c < 0, rojo, verde), subset=["Dif.", "S/"], axis=0)
    fuerte = np.array(f["pista_f"].tolist(), dtype=bool)
    sty = sty.apply(lambda c: np.where(fuerte, f"color: {ACENTO_TEXTO}; font-weight: 600",
                                       f"color: {GRIS_TEXTO}"),
                    subset=["Posible origen"], axis=0)
    return sty.set_properties(subset=["Producto"], **{"font-weight": "600"})


_ANCHOS = {"Producto": 205, "Área": 84, "Dif.": 82, "S/": 70,
           "Posible origen": 205}
_AYUDA = {
    "Dif.": "Contado menos sistema, en la unidad del producto.",
    "S/": "La diferencia valorizada al precio promedio del cierre.",
    "Posible origen": "La pista principal de la línea; en morado si es fuerte "
                      "(los números calzan o es un hecho del kardex). «+2» "
                      "dice cuántas más hay en la ficha.",
}


# ── la ficha ────────────────────────────────────────────────────────────

def _ir(clave, lado):
    """Callback de «Ver …»: la otra línea, en su lista y sin filtros que la
    escondan. La key de la tabla cambia, así la selección nueva manda."""
    ss = st.session_state
    ss[_K_FOCO] = clave
    ss[K_LADO] = lado
    ss[K_PISTA] = "todas"
    ss[K_BUSCAR] = ""
    ss[_K_SALTO] = ss.get(_K_SALTO, 0) + 1
    # Sin esto, `_foco_anterior` leería en la próxima corrida la fila que
    # seguía elegida en la tabla vieja y devolvería el foco a ella.
    ss[_K_TABLA] = None


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
    return '<div class="dif-viene">' + "".join(f"<div>{t}</div>" for t in out) + "</div>"


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


def _ficha(x, fi, por_clave):
    st.markdown(_cabecera_ficha(x) + '<div class="dif-h">Posible origen</div>',
                unsafe_allow_html=True)
    if not fi["pistas"]:
        st.markdown('<div class="dif-nota">Ninguna pista: ni otra área, ni la producción, '
                    'ni el conteo anterior la explican. Es de las que hay que mirar a mano.</div>',
                    unsafe_allow_html=True)
    for j, p in enumerate(fi["pistas"]):
        st.markdown(_pista_html(p), unsafe_allow_html=True)
        ref = por_clave.get(p.get("r"))
        if ref is not None:
            st.button(f'Ver {ref["producto"]} · {ref["area"]} →', key=f"ajdif_ir_{j}",
                      type="tertiary", on_click=_ir,
                      args=(_clave(ref), "fal" if ref["q"] < 0 else "sob"))
    st.markdown('<div class="dif-h">La cuenta entre los dos conteos</div>'
                + _cuenta_html(x, fi), unsafe_allow_html=True)
    if len(fi["camino"]) >= 2:
        st.plotly_chart(_fig_camino(x, fi), width="stretch", key="ajdif_camino",
                        config={"displaylogo": False, "displayModeBar": False})
    st.markdown('<div class="dif-h">De dónde viene</div>' + _viene_html(x, fi)
                + '<div class="dif-h">Dónde se usa</div>'
                '<div class="dif-nota">Lo que lo descarga, con lo vendido o producido entre los '
                'dos conteos. «≈» es recetas × vendido: una referencia, no el kardex. «Receta '
                'editada» marca las que cambiaron desde el conteo anterior.</div>'
                + _usos_html(x, fi), unsafe_allow_html=True)
    with st.container(key="ajdif_pie"):
        st.markdown('<div class="dif-h">Sus ajustes en los últimos cierres</div>'
                    + _hist_html(fi), unsafe_allow_html=True)


# ── la vista ────────────────────────────────────────────────────────────

def _kpis(f):
    fal, sob, pf, ps, sin = da.cobertura(f)
    nf, ns = int((f["q"] < 0).sum()), int((f["q"] > 0).sum())
    sin_f = int(((f["n_pistas"] == 0) & (f["q"] < 0)).sum())
    return ('<div class="dif-kpis">'
            f'<div class="dif-kpi"><span class="r">Faltó</span><span class="v dif-neg">'
            f'{_soles(-fal)}</span><span class="d">{nf:,} líneas</span></div>'
            f'<div class="dif-kpi"><span class="r">Sobró</span><span class="v dif-pos">'
            f'{_soles(sob)}</span><span class="d">{ns:,} líneas</span></div>'
            f'<div class="dif-kpi a"><span class="r">Con pista fuerte</span><span class="v">'
            f'{round(pf * 100)} % · {round(ps * 100)} %</span><span class="d">del faltante y '
            'del sobrante, en soles</span></div>'
            f'<div class="dif-kpi a"><span class="r">Sin ninguna pista</span><span class="v">'
            f'{sin:,} líneas</span><span class="d">{sin_f:,} faltantes y {sin - sin_f:,} '
            'sobrantes: hay que mirarlas a mano</span></div></div>')


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
    _foco_anterior()
    with st.container(border=True, key=CARD):
        st.markdown(CSS_TITULOS_DRILL + _CSS + "<style>"
                    + css_filtros_vista("ajdif_ctrl_", "ajdif_nolist_") + "</style>",
                    unsafe_allow_html=True)
        # columnas-internas: título, la sesión y la familia, en UN renglón.
        c_t, c_s, c_f = st.columns([2.4, 1.7, 1.0], vertical_alignment="center")
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
        st.markdown(_kpis(lin), unsafe_allow_html=True)

        # El lado, la pista y el buscador. Lo elegido se corrige ANTES de
        # dibujar cada widget: una opción que deja de estar lo revienta.
        if ss.get(K_LADO) not in LADOS:
            ss[K_LADO] = LADOS[0]
        lado = ss[K_LADO]
        # El lado lo dice la CANTIDAD: una línea sin precio vale S/ 0 y sigue
        # siendo un faltante o un sobrante (#651).
        base = lin[lin["q"] < 0] if lado == "fal" else lin[lin["q"] > 0]
        q = (ss.get(K_BUSCAR) or "").strip().lower()
        if q:
            base = base[(base["producto"].str.lower() + " " + base["area"].str.lower())
                        .str.contains(q, regex=False)]
        tipos = base["tipos"].str.split(",")
        cuenta = {"todas": len(base), "fuerte": int(base["fuerte"].sum()),
                  "sin": int((base["n_pistas"] == 0).sum())}
        for t in da.TIPOS:
            cuenta[t] = int(tipos.map(lambda ts, t=t: t in ts).sum())
        opciones = [o for o in FILTROS if cuenta[o] or o == "todas"]
        if ss.get(K_PISTA) not in opciones:
            ss[K_PISTA] = "todas"
        # columnas-internas: el lado y el buscador; las pistas, en el renglón
        # de abajo a lo ancho (en un tercio de la fila se partían en tres).
        c_l, c_b = st.columns([3.0, 1.0], vertical_alignment="center")
        with c_l:
            n_fal, n_sob = int((lin["q"] < 0).sum()), int((lin["q"] > 0).sum())
            st.segmented_control(
                "Lado", LADOS, key=K_LADO, required=True, label_visibility="collapsed",
                format_func=lambda o: f"Faltantes · {n_fal}" if o == "fal" else f"Sobrantes · {n_sob}")
        with c_b:
            st.text_input("Buscar", key=K_BUSCAR, placeholder="Buscar producto o área",
                          label_visibility="collapsed")
        with st.container(key="ajdif_pistas"):
            st.pills("Posible origen", opciones, key=K_PISTA, label_visibility="collapsed",
                     format_func=lambda o: (f"{_ICONO[o]} " if o in _ICONO else "")
                     + f"{_NOMBRE_FILTRO[o]} · {cuenta[o]}")
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

        # columnas-internas: la lista y la ficha de la línea elegida.
        c_tab, c_fic = st.columns([1.5, 1], gap="medium")
        if f.empty:
            with c_tab:
                st.info("Ninguna línea con estos filtros.")
            return
        claves = [_clave(x) for x in f.to_dict("records")]
        foco = ss.get(_K_FOCO)
        if foco not in claves:
            fuerte = f.index[f["fuerte"]]
            foco = claves[int(fuerte[0]) if len(fuerte) else 0]
        pos = claves.index(foco)
        ss[_K_FOCO] = foco
        with c_tab:
            key = _key_tabla(claves)
            ss[_K_TABLA], ss[_K_FILAS] = key, claves
            tabla = _tabla(f)
            st.dataframe(
                _estilo(tabla, f, pos), key=key, on_select="rerun",
                selection_mode="single-row-required",
                selection_default={"selection": {"rows": [pos]}},
                hide_index=True, row_height=27,
                # El tope es el de la vista y no el de un PROTAGONISTA: la
                # lista acompaña a la ficha, que mide casi mil píxeles.
                height=alturas.por_filas(len(tabla), px_fila=27, extra=38, minimo=0,
                                         rol=alturas.DIFERENCIAS_TABLA),
                column_config={c: st.column_config.Column(width=_ANCHOS.get(c),
                                                          help=_AYUDA.get(c))
                               for c in tabla.columns})
            st.caption(f"{len(f):,} líneas · {_soles(float(f['v'].sum()))} · ordenada por "
                       "soles; el círculo de una fila abre su ficha al costado.")
        with c_fic, st.container(key="ajdif_ficha"):
            x = f.iloc[pos]
            por_clave = {int(i): fila for i, fila in
                         zip(r["lineas"]["id"], r["lineas"].to_dict("records"))}
            _ficha(x, r["fichas"][int(x["id"])], por_clave)
