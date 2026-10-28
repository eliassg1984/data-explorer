"""graficos.movimientos_destino — las dos vistas de Movimientos › Salidas que
dicen en qué se fue lo que entró, de CIERRE A CIERRE de inventario (regla
#645):

  · «Sin plato, cierre por cierre» (`tarjeta_sin_plato`): lo que salió sin ir
    a un plato en el restaurante entero —bajas, otras salidas y faltante—,
    los últimos cierres, y en qué productos se concentra.
  · «En qué se fue cada producto» (`tarjeta_por_producto`): la misma cuenta,
    producto por producto, con la ficha del elegido al costado.

Reemplazaron el 2026-10-12 a «Destino de lo que entra» (regla #614), que
listaba sólo los productos CON BAJA (57 de los 609 con entradas en 30 días)
sobre un rango cualquiera de fechas, y dejaba afuera lo que más pesa: en
setiembre 2026, S/ 1.071 de bajas contra S/ 50.730 de faltante. Las dos
nacieron de un boceto aprobado con los datos reales, partido en dos para
que cada una entre en una pantalla.

La cuenta vive en `sin_plato.py` (puro, con prueba) y la carga en
`data.sin_plato_por_cierre`. Acá sólo se dibuja. El chip «Familia» de la
franja recorta; el de «Sub Almacén» no: la cuenta es del restaurante entero
(lo que va de un área a otra suma cero).

CADA VISTA ELIGE SU CIERRE, como el resto de Movimientos (regla #617), con
la píldora ‹ [cierre] › de Ajuste (`ajuste._comun.selector_sesion`). Un clic
en un producto de «Dónde se concentra» abre la otra vista en ese cierre y
con ese producto (`navegacion.CLAVE_SALTO_VISTA`, el salto del panel del
rail).
"""

import hashlib
import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import sin_plato
from graficos import alturas
from graficos.ajuste._comun import selector_sesion
from graficos.base import _compras_layout
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.movimientos_periodo import unidad_corta
from tema import (
    ACENTO_TEXTO, AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO, AJUSTE_NEG_TEXTO,
    AJUSTE_POS_TEXTO, AJUSTE_SOB_FONDO, COLORES_DESTINO as C, GRIS_BORDE,
    GRIS_FONDO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_FONDO, TEXTO_PRINCIPAL,
)

VISTA_CIERRE = "Sin plato por cierre"
VISTA_PRODUCTO = "En qué se fue cada producto"
"""Los ids de las dos vistas en el rail y la pila (`graficos/movimientos.py`)."""

CARD_CIERRE = "ajuste_graf_card_izq_mov_sinplato"
CARD_PRODUCTO = "ajuste_graf_card_izq_mov_destino"
"""El prefijo `ajuste_graf_card_izq_` les da el marco de las demás tarjetas
de Movimientos (`estilos/_80_cards.py`)."""

K_CIERRE_1 = "mov_sp_cierre"
K_CIERRE_2 = "mov_pr_cierre"
_K_FOCO = "_mov_pr_foco"
_K_SALTO = "_mov_pr_salto"
_K_IR = "_mov_sp_ir"
_K_N_FIG = "_mov_sp_n_fig"
_K_N_TOP = "_mov_sp_n_top"
K_GRUPO = "mov_pr_grupo"
K_FILTRO = "mov_pr_filtro"
K_MEDIDA = "mov_pr_medida"
K_BUSCAR = "mov_pr_buscar"

GRUPOS = ("Alimentos y bebidas", "Insumos de operación")
FILTROS = ("Todos", "Con bajas", "Sin salida registrada", "Con sobrante")
MEDIDAS = ("S/", "Unidades")
CIERRES_GRAFICO = 12
"""Cuántos cierres dibujan los gráficos (los últimos)."""

# Las partes de lo que salió, en el orden en que se apilan, con su nombre.
PARTES_SALIO = (("venta", "Venta"), ("cort", "Cortesía"),
                ("evvi", "Eventos y VI"),
                ("prep", "En preparaciones"), ("baja", "Bajas"),
                ("otras", "Otras salidas"), ("falt", "Faltante"))
PARTES_SIN_PLATO = (("baja", "Bajas"), ("otras", "Otras salidas"),
                    ("falt", "Faltante"))

_CSS = f"""
<style>
.spd-sub {{ font-size: 12px; color: {GRIS_TEXTO}; margin: -2px 0 0 2px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.spd-kpis {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr));
             gap: 8px; }}
.spd-kpi {{ border: 1px solid {GRIS_LINEA}; border-radius: 10px;
            padding: 7px 10px; display: flex; flex-direction: column; gap: 3px;
            min-width: 0; }}
.spd-kpi .r {{ font-size: 10.5px; letter-spacing: .04em; text-transform: uppercase;
               color: {GRIS_TEXTO}; font-weight: 600; white-space: nowrap;
               overflow: hidden; text-overflow: ellipsis; }}
.spd-kpi .v {{ font-size: 19px; font-weight: 700; color: {TEXTO_PRINCIPAL};
               font-variant-numeric: tabular-nums; line-height: 1.2; }}
.spd-kpi .d {{ font-size: 11.5px; color: {GRIS_TEXTO}; line-height: 1.35;
               font-variant-numeric: tabular-nums; }}
.spd-kpi .d b {{ color: {GRIS_TEXTO_MEDIO}; font-weight: 600; }}
.spd-mini {{ display: flex; height: 5px; gap: 2px; border-radius: 3px;
             overflow: hidden; background: {GRIS_LINEA}; }}
.spd-mini span {{ display: block; height: 100%; }}
.spd-tit {{ font-size: 12.5px; font-weight: 600; color: {GRIS_TEXTO_MEDIO};
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.spd-tit span {{ font-weight: 400; color: {GRIS_TEXTO}; font-size: 12px;
                 margin-left: 8px; }}
.spd-ley {{ display: flex; flex-wrap: wrap; gap: 2px 12px; font-size: 11.5px;
            color: {GRIS_TEXTO}; }}
.spd-ley i {{ display: inline-block; width: 9px; height: 9px; border-radius: 2px;
              margin-right: 5px; vertical-align: -1px; }}
.spd-ecu {{ font-size: 11.5px; color: {GRIS_TEXTO}; background: {GRIS_FONDO};
            border-radius: 8px; padding: 6px 10px;
            font-variant-numeric: tabular-nums; }}
/* El ÚLTIMO renglón de cada tarjeta: Streamlit le pone −16px de margen abajo
   a todo markdown y a todo caption (lo compensa el `gap` del que sigue), y
   como no sigue nada, se metía debajo del borde y la tarjeta se deslizaba
   8px por dentro — en Windows, con su barra. */
.st-key-mov_sp_pie [data-testid="stMarkdownContainer"],
.st-key-mov_pr_pie [data-testid="stCaptionContainer"] {{
    margin-bottom: 0 !important; }}
.spd-ecu b {{ color: {GRIS_TEXTO_MEDIO}; font-weight: 600; }}
.spd-ecu .ok {{ color: {AJUSTE_POS_TEXTO}; font-weight: 600; }}
.spd-ficha-n {{ font-size: 14px; font-weight: 700; color: {ACENTO_TEXTO};
                line-height: 1.25; }}
.spd-ficha-s {{ font-size: 11.5px; color: {GRIS_TEXTO}; margin-bottom: 8px; }}
.spd-cien {{ display: flex; height: 14px; gap: 2px; border-radius: 3px;
             overflow: hidden; margin: 4px 0 6px; }}
.spd-cien span {{ display: block; height: 100%; min-width: 2px; }}
.spd-cley {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1px 14px;
             font-size: 11.5px; margin-bottom: 8px; }}
.spd-cley div {{ display: flex; justify-content: space-between; gap: 6px;
                 color: {GRIS_TEXTO_MEDIO}; white-space: nowrap; }}
.spd-cley div.cero {{ color: {GRIS_TEXTO_SUAVE}; }}
.spd-cley i {{ display: inline-block; width: 8px; height: 8px; border-radius: 2px;
               margin-right: 5px; }}
.spd-cuenta {{ font-size: 11.5px; background: {GRIS_FONDO}; border-radius: 8px;
               padding: 7px 10px; color: {GRIS_TEXTO_MEDIO}; line-height: 1.55;
               font-variant-numeric: tabular-nums; }}
.spd-cuenta b {{ color: {TEXTO_PRINCIPAL}; }}
.spd-cuenta .ok {{ color: {AJUSTE_POS_TEXTO}; font-weight: 600; }}
.spd-pista {{ font-size: 11.5px; color: {GRIS_TEXTO_MEDIO}; margin-top: 8px;
              border-left: 3px solid {GRIS_BORDE}; padding: 1px 0 1px 8px; }}
.spd-pista b {{ color: {ACENTO_TEXTO}; }}
.spd-tag {{ font-size: 10px; font-weight: 600; padding: 0 5px; border-radius: 4px;
            line-height: 15px; display: inline-block; margin-left: 6px; }}
.spd-tag.solo {{ background: {AJUSTE_ALERTA_FONDO}; color: {AJUSTE_ALERTA_TEXTO}; }}
.spd-tag.sob {{ background: {AJUSTE_SOB_FONDO}; color: {AJUSTE_POS_TEXTO}; }}
</style>
"""


# ── números ─────────────────────────────────────────────────────────────

def _soles(v, signo=False):
    if v is None or not np.isfinite(v):
        return "—"
    s = f"S/ {abs(v):,.0f}"
    if round(v) < 0:
        return "−" + s
    return ("+" + s) if signo and round(v) > 0 else s


def _cant(v):
    if v is None or not np.isfinite(v):
        return "—"
    s = f"{abs(v):,.1f}".rstrip("0").rstrip(".")
    return ("−" if v < -0.05 else "") + s


def _corto(v):
    a = abs(v)
    t = f"{a / 1000:,.1f}k" if a >= 1000 else f"{a:,.0f}"
    return ("−" if v < 0 else "") + t


# ── datos ───────────────────────────────────────────────────────────────

def _cargar(fam_sel, reloj="operativo"):
    """`(periodos, filas, totales)` de la cuenta de conteo a conteo
    (`sin_plato.RELOJES`, reglas #743 y #750), con el chip Familia aplicado (y los
    totales rehechos sobre lo filtrado), o None."""
    r = data.sin_plato_por_cierre(reloj)
    if not r or not r.get("periodos"):
        return None
    per, filas, tot = r["periodos"], r["filas"], r["totales"]
    if fam_sel:
        fams = {str(f).strip().upper() for f in fam_sel}
        filas = filas[filas["familia"].str.upper().isin(fams)]
        tot = sin_plato.totales(filas, len(per))
    return per, filas, tot


def _k_elegido(clave_estado, per):
    """El período elegido en `clave_estado` o, si no hay o ya no existe, el
    último cierre (y lo deja escrito, como `selector_sesion`)."""
    claves = [p["clave"] for p in per]
    c = st.session_state.get(clave_estado)
    if c not in claves:
        c = claves[-1]
        st.session_state[clave_estado] = c
    return claves.index(c)


_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set",
          "oct", "nov", "dic")


def _fecha(d):
    return f"{d.day} {_MESES[d.month - 1]}"


def _selector(prefijo, clave_estado, per, tot):
    """La píldora ‹ [cierre] › con su panel: cada cierre con lo que salió
    sin plato (en negativo, como un faltante) y sus fechas."""
    tot_k = tot.set_index("k")
    meta, stats = {}, {}
    for p in per:
        t = tot_k.loc[p["k"]]
        stats[p["clave"]] = (-(t["baja"] + t["otras"] + t["falt"]), 0, 0)
        meta[p["clave"]] = (f"del {_fecha(p['desde'])} al {_fecha(p['hasta'])} · "
                            f"{int(t['n_sinplato']):,} productos sin plato")
    selector_sesion(
        prefijo, clave_estado, [p["sesion"] for p in per], stats=stats,
        meta=meta,
        pie=["Lo que salió sin plato en alimentos y bebidas: bajas, otras "
             "salidas y faltante. Cada cierre va del día después del conteo "
             "anterior al último conteo de este.",
             "Elegir acá cambia sólo esta vista."])


def _subtitulo(p):
    return (f"Del {_fecha(p['desde'])} al {_fecha(p['hasta'])} "
            f"{p['hasta'].year}, de cierre a cierre ({p['cierre_ant']} → "
            f"{p['cierre']}) · el restaurante entero")


def _cabecera(titulo, p):
    st.markdown(f'<div class="inv-rank-tit" title="{html.escape(titulo)}">'
                f'{html.escape(titulo)}</div>'
                f'<div class="spd-sub">{html.escape(_subtitulo(p))}</div>',
                unsafe_allow_html=True)


def _vacia(card, titulo, texto):
    with st.container(border=True, key=card):
        st.markdown(CSS_TITULOS_DRILL, unsafe_allow_html=True)
        st.markdown(f'<div class="inv-rank-tit">{titulo}</div>',
                    unsafe_allow_html=True)
        st.info(texto)


_SIN_DATOS = ("No se pudo leer el kardex o todavía no hay dos cierres de "
              "inventario desde octubre de 2025: esta vista queda vacía.")


# ═══════════════════════════════════════════════════════════════════════
# VISTA 1 · SIN PLATO, CIERRE POR CIERRE
# ═══════════════════════════════════════════════════════════════════════

def _mini(partes):
    tot = sum(max(v, 0) for v, _ in partes)
    if tot <= 0:
        return '<div class="spd-mini"></div>'
    return ('<div class="spd-mini">' + "".join(
        f'<span style="flex:{v:.2f};background:{c}"></span>'
        for v, c in partes if v > 0) + "</div>")


def _kpis(t, ant, p_ant):
    plato = t["venta"] + t["cort"] + t["evvi"]
    sinp = t["baja"] + t["otras"] + t["falt"]
    salio = plato + sinp
    pct = f"{100 * sinp / salio:.0f} % de lo que salió" if salio > 0 else ""
    if ant is not None:
        sinp_a = ant["baja"] + ant["otras"] + ant["falt"]
        pct += (f" · <b>{_soles(sinp - sinp_a, signo=True)}</b> vs "
                f"{p_ant['corto']}")
    neto = t["falt"] - t["sobr"]
    tiles = [
        ("Sin plato", _soles(sinp),
         _mini([(t["baja"], C["baja"]), (t["otras"], C["otras"]),
                (t["falt"], C["falt"])]), pct),
        ("Bajas", _soles(t["baja"]), "", "notas de baja procesadas"),
        ("Otras salidas", _soles(t["otras"]), "",
         "personal, uso del área, merma fija"),
        ("Faltante del conteo", _soles(t["falt"]), "",
         f"sobrante <b>{_soles(t['sobr'])}</b> · neto <b>{_soles(-neto)}</b>"),
        ("A un plato", _soles(plato),
         _mini([(t["venta"], C["venta"]), (t["cort"], C["cort"]),
                (t["evvi"], C["evvi"])]),
         f"cortesía <b>{_soles(t['cort'])}</b> · eventos y VI "
         f"<b>{_soles(t['evvi'])}</b>"),
        ("Insumos de operación", _soles(t["operacion"]), "",
         "carbón, leña, limpieza: sólo al contar"),
    ]
    return ('<div class="spd-kpis">' + "".join(
        f'<div class="spd-kpi"><div class="r">{r}</div><div class="v">{v}</div>'
        f'{m}<div class="d">{d}</div></div>' for r, v, m, d in tiles) + "</div>")


def _ecuacion(t):
    plato = t["venta"] + t["cort"] + t["evvi"]
    neto = t["falt"] - t["sobr"]
    stock = t["fin"] - t["ini"]

    def mas(v):
        return ("+ " if v >= 0 else "− ") + _soles(abs(v))
    return (f'<div class="spd-ecu"><b>La cuenta cierra:</b> entró '
            f'{_soles(t["compras"])} = a un plato {_soles(plato)} + sin plato '
            f'{_soles(t["baja"] + t["otras"])} {mas(neto)} de faltante neto '
            f'{mas(t["operacion"])} de operación {mas(stock)} de stock '
            f'{mas(t["valorizacion"])} de valorización '
            f'<span class="ok">✓</span></div>')


def _ks_grafico(per, k):
    """Los cierres que dibuja un gráfico: los últimos `CIERRES_GRAFICO`, o
    los que terminan en `k` si el elegido es más viejo."""
    ks = list(range(max(0, len(per) - CIERRES_GRAFICO), len(per)))
    if k not in ks:
        ks = list(range(max(0, k - CIERRES_GRAFICO + 1), k + 1))
    return ks


def _fig_cierres(tot, per, k):
    """Las columnas de los últimos cierres: bajas, otras salidas y faltante
    apilados, el sobrante debajo del cero. El elegido, con fondo."""
    ks = _ks_grafico(per, k)
    t = tot.set_index("k").loc[ks]
    xs = [per[i]["corto"] for i in ks]
    fig = go.Figure()
    for c, nombre in PARTES_SIN_PLATO:
        fig.add_bar(x=xs, y=t[c], name=nombre, marker_color=C[c],
                    marker_line=dict(width=1, color="white"),
                    hovertemplate=f"{nombre}: S/ %{{y:,.0f}}<extra></extra>")
    fig.add_bar(x=xs, y=-t["sobr"], name="Sobrante", marker_color=C["sobr"],
                marker_line=dict(width=1, color="white"),
                customdata=t["sobr"],
                hovertemplate="Sobrante: S/ %{customdata:,.0f}<extra></extra>")
    _compras_layout(fig, alto=alturas.SIN_PLATO_FIG)
    sel = ks.index(k)
    arriba = float((t["baja"] + t["otras"] + t["falt"]).iloc[sel])
    fig.update_layout(
        barmode="relative", bargap=0.35, showlegend=False,
        hovermode="x unified", dragmode="pan",
        margin=dict(l=8, r=8, t=18, b=8),
        shapes=[dict(type="rect", xref="x", yref="paper", x0=sel - 0.5,
                     x1=sel + 0.5, y0=0, y1=1, fillcolor=LAVANDA_FONDO,
                     line_width=0, layer="below")],
        annotations=[dict(x=xs[sel], y=arriba, text=f"S/ {_corto(arriba)}",
                          showarrow=False, yshift=10,
                          font=dict(size=11, color=GRIS_TEXTO_MEDIO))])
    fig.update_xaxes(type="category", fixedrange=True)
    fig.update_yaxes(showticklabels=True, tickprefix="S/ ", tickformat="~s",
                     fixedrange=True, zeroline=True, zerolinecolor=GRIS_BORDE,
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    return fig, ks


def _puntos(ev):
    try:
        return (ev.get("selection") or {}).get("points") or []
    except AttributeError:
        return getattr(getattr(ev, "selection", None), "points", []) or []


def _filas_sel(ev):
    try:
        return (ev.get("selection") or {}).get("rows") or []
    except AttributeError:
        return getattr(getattr(ev, "selection", None), "rows", []) or []


def _clic_cierre(key, ks, per):
    """Callback del gráfico: el mes tocado pasa a ser el cierre de la vista
    y la key cambia, para que el próximo clic se lea (regla #399)."""
    pts = _puntos(st.session_state.get(key) or {})
    if pts:
        cortos = [per[j]["corto"] for j in ks]
        x = pts[0].get("x")
        i = cortos.index(x) if x in cortos else pts[0].get("point_index")
        if i is not None and 0 <= int(i) < len(ks):
            st.session_state[K_CIERRE_1] = per[ks[int(i)]]["clave"]
    st.session_state[_K_N_FIG] = st.session_state.get(_K_N_FIG, 0) + 1


def _ir_al_producto(key, codigos, clave_cierre):
    """Callback de «Dónde se concentra»: la otra vista, en este cierre y con
    este producto. El salto lo resuelve `_render_rail` en la corrida
    completa que pide `tarjeta_sin_plato` al terminar de dibujarse."""
    filas = _filas_sel(st.session_state.get(key) or {})
    st.session_state[_K_N_TOP] = st.session_state.get(_K_N_TOP, 0) + 1
    if not filas or not (0 <= filas[0] < len(codigos)):
        return
    import navegacion
    st.session_state[K_CIERRE_2] = clave_cierre
    st.session_state[_K_FOCO] = codigos[filas[0]]
    st.session_state[K_GRUPO] = GRUPOS[0]
    st.session_state[K_FILTRO] = FILTROS[0]
    st.session_state[K_BUSCAR] = ""
    st.session_state[_K_SALTO] = st.session_state.get(_K_SALTO, 0) + 1
    st.session_state[navegacion.CLAVE_SALTO_VISTA] = VISTA_PRODUCTO
    st.session_state[_K_IR] = True


def _dominante(r):
    """La parte de lo que salió sin plato que más pesa: «faltante 98 %»."""
    if r["sinplato_v"] <= 0:
        return ""
    v, n = max((r["falt_v"], "faltante"), (r["baja_v"], "bajas"),
               (r["otras_v"], "otras salidas"))
    return f"{n} {100 * v / r['sinplato_v']:.0f} %"


def tarjeta_sin_plato(fam_sel=()):
    """La vista nativa conserva la firma y el salto al producto (#736)."""
    from .sin_plato_cierre_pieza import renderizar
    return renderizar(fam_sel)


def _tarjeta_sin_plato_legacy(fam_sel=()):
    """La vista «Sin plato, cierre por cierre»."""
    titulo = "Sin plato, cierre por cierre"
    datos = _cargar(fam_sel)
    if datos is None:
        _vacia(CARD_CIERRE, titulo, _SIN_DATOS)
        return
    per, filas, tot = datos
    k = _k_elegido(K_CIERRE_1, per)
    p = per[k]
    tk = tot.set_index("k")
    with st.container(border=True, key=CARD_CIERRE):
        st.markdown(CSS_TITULOS_DRILL + _CSS, unsafe_allow_html=True)
        # columnas-internas: el título a la izquierda y la píldora del
        # cierre a la derecha, en el mismo renglón.
        c_t, c_s = st.columns([3, 1.3], vertical_alignment="center")
        with c_t:
            _cabecera(titulo, p)
        with c_s:
            _selector("ajses_movsp", K_CIERRE_1, per, tot)
        st.markdown(_kpis(tk.loc[k], tk.loc[k - 1] if k > 0 else None,
                          per[k - 1] if k > 0 else None),
                    unsafe_allow_html=True)
        # columnas-internas: el gráfico y la lista miden lo mismo; la lista
        # se lleva más de un tercio: con menos, su tercera columna no entraba
        # a 1323px.
        c_g, c_l = st.columns([1.3, 1], gap="medium")
        with c_g:
            st.markdown(
                '<div class="spd-tit">Lo que salió sin plato<span>S/ · '
                'alimentos y bebidas · clic en un mes para verlo</span></div>'
                '<div class="spd-ley">' + "".join(
                    f'<span><i style="background:{C[c]}"></i>{n}</span>'
                    for c, n in (*PARTES_SIN_PLATO, ("sobr", "Sobrante (abajo)")))
                + "</div>", unsafe_allow_html=True)
            fig, ks = _fig_cierres(tot, per, k)
            key_fig = f"mov_sp_fig_{st.session_state.get(_K_N_FIG, 0)}"
            st.plotly_chart(fig, width="stretch", key=key_fig,
                            on_select=lambda: _clic_cierre(key_fig, ks, per),
                            selection_mode="points",
                            config={"displaylogo": False,
                                    "displayModeBar": False})
        with c_l:
            st.markdown('<div class="spd-tit">Dónde se concentra<span>clic '
                        'para abrirlo en «En qué se fue cada producto»'
                        '</span></div>', unsafe_allow_html=True)
            a = filas[(filas["k"] == k) & (filas["clase"] == sin_plato.ALIMENTOS)
                      & (filas["sinplato_v"] > 0.5)]
            a = a.sort_values("sinplato_v", ascending=False).head(40)
            if a.empty:
                st.caption("Nada salió sin plato en este cierre.")
            else:
                lista = pd.DataFrame({
                    "Producto": a["producto"].tolist(),
                    "Sin plato": a["sinplato_v"].round(0).tolist(),
                    "Sobre todo": [_dominante(r) for _, r in a.iterrows()],
                })
                codigos = a["cod"].tolist()
                key_top = f"mov_sp_top_{st.session_state.get(_K_N_TOP, 0)}"
                st.dataframe(
                    lista, key=key_top, hide_index=True, row_height=27,
                    height=alturas.SIN_PLATO_FIG,
                    on_select=lambda: _ir_al_producto(key_top, codigos,
                                                      p["clave"]),
                    selection_mode="single-row",
                    column_config={
                        "Producto": st.column_config.TextColumn(width=200),
                        "Sin plato": st.column_config.ProgressColumn(
                            "Sin plato", format="S/ %d", min_value=0,
                            max_value=float(a["sinplato_v"].max()),
                            width=130),
                        "Sobre todo": st.column_config.TextColumn(
                            width=100,
                            help="Qué parte pesa más: faltante del conteo, "
                                 "bajas u otras salidas."),
                    })
        with st.container(key="mov_sp_pie"):
            st.markdown(_ecuacion(tk.loc[k]), unsafe_allow_html=True)
    # El salto a la otra vista, DESPUÉS de dibujar la tarjeta entera: así
    # ningún widget de acá queda sin registrar en la corrida que se corta
    # (regla #373).
    if st.session_state.pop(_K_IR, False):
        st.rerun(scope="app")


# ═══════════════════════════════════════════════════════════════════════
# VISTA 2 · EN QUÉ SE FUE CADA PRODUCTO
# ═══════════════════════════════════════════════════════════════════════

def _key_tabla(codigos):
    firma = hashlib.md5("|".join(codigos).encode("utf-8")).hexdigest()[:12]
    return f"mov_pr_tabla_{firma}_{st.session_state.get(_K_SALTO, 0)}"


def _foco_anterior():
    """El producto que la tabla tenía elegido en la corrida anterior. Se lee
    ANTES de dibujar (regla #556): la selección es de la KEY, no de las
    filas, y la key cambia con ellas."""
    ss = st.session_state
    key, codigos = ss.get("_mov_pr_key"), ss.get("_mov_pr_codigos") or []
    filas = _filas_sel(ss.get(key) or {}) if key else []
    if filas and 0 <= filas[0] < len(codigos):
        ss[_K_FOCO] = codigos[filas[0]]


def _tabla_alimentos(f, medida):
    s = "q" if medida == MEDIDAS[1] else "v"
    solo = sin_plato.sin_salida_registrada(f)
    nota = np.where(solo, " · sin salida registrada",
                    np.where(f["aj_v"] > 0.5, " · sobrante", ""))
    tabla = pd.DataFrame({"Producto": (f["producto"] + nota).tolist()})
    if s == "q":
        tabla["U."] = f["unidad"].map(unidad_corta).tolist()
    for col, rot in (("entro", "Entró"), ("plato", "A un plato"),
                     ("prep", "En prep."), ("baja", "Bajas"),
                     ("otras", "Otras"), ("aj", "Ajuste"),
                     ("sinplato", "Sin plato")):
        tabla[rot] = f[f"{col}_{s}"].tolist()
    tabla["% sin plato"] = (f["pct"] * 100).fillna(np.inf).tolist()
    tabla["vs 6 cierres"] = ((f["pct"] - f["pct_prev"]) * 100).fillna(np.inf).tolist()
    return tabla


def _tabla_operacion(f, medida):
    s = "q" if medida == MEDIDAS[1] else "v"
    tabla = pd.DataFrame({"Producto": f["producto"].tolist()})
    if s == "q":
        tabla["U."] = f["unidad"].map(unidad_corta).tolist()
    tabla["Había"] = f[f"ini_{s}"].tolist()
    tabla["Entró"] = f[f"entro_{s}"].tolist()
    tabla["Consumido al contar"] = f[f"falt_{s}"].tolist()
    tabla["Notas de salida"] = (f[f"baja_{s}"] + f[f"otras_{s}"]).tolist()
    tabla["Quedó"] = f[f"fin_{s}"].tolist()
    return tabla


def _estilo(tabla, pos, medida):
    """El formato y los colores de la tabla. Todo por COLUMNA entera
    (`set_properties`, `apply` con `np.where`): con un `apply` fila por fila
    para pintar la elegida, el estilo de 862 filas costaba 0,94 s por clic;
    así, 0,18 (medido el 2026-10-12)."""
    en_q = medida == MEDIDAS[1]
    tope = 0.05 if en_q else 0.5

    def num(v):
        if abs(v) < tope:
            return "—"
        return _cant(v) if en_q else f"{v:,.0f}".replace("-", "−")
    fmt = {c: num for c in tabla.columns
           if c not in ("Producto", "U.", "% sin plato", "vs 6 cierres",
                        "Ajuste")}
    if "Ajuste" in tabla.columns:
        fmt["Ajuste"] = (
            lambda v: "—" if abs(v) < tope else ("+" if v > 0 else "−") + num(abs(v)))
    if "% sin plato" in tabla.columns:
        fmt["% sin plato"] = lambda v: "—" if not np.isfinite(v) else f"{v:.0f} %"
        fmt["vs 6 cierres"] = (lambda v: "—" if not np.isfinite(v) else
                               f"{'+' if v > 0 else '−' if v < 0 else ''}"
                               f"{abs(v):.0f} pts")
    sty = tabla.style.format(fmt).set_properties(
        subset=pd.IndexSlice[[pos], :], **{"background-color": LAVANDA_FONDO})
    rojo, verde = f"color: {AJUSTE_NEG_TEXTO}", f"color: {AJUSTE_POS_TEXTO}"
    if "Ajuste" in tabla.columns:
        sty = sty.apply(lambda c: np.where(c < -tope, rojo,
                                           np.where(c > tope, verde, "")),
                        subset=["Ajuste"], axis=0)
    if "vs 6 cierres" in tabla.columns:
        sty = sty.apply(lambda c: np.where(~np.isfinite(c) | (c.abs() < 1), "",
                                           np.where(c > 0, rojo, verde)),
                        subset=["vs 6 cierres"], axis=0)
    fuertes = [c for c in ("Sin plato", "Consumido al contar")
               if c in tabla.columns]
    if fuertes:
        sty = sty.set_properties(subset=fuertes, **{"font-weight": "600"})
    return sty


_ANCHOS = {"Producto": 180, "U.": 40, "Entró": 62, "A un plato": 70,
           "En prep.": 60, "Bajas": 52, "Otras": 52, "Ajuste": 62,
           "Sin plato": 66, "% sin plato": 72, "vs 6 cierres": 78,
           "Había": 70, "Consumido al contar": 120, "Notas de salida": 100,
           "Quedó": 70}
"""El ancho de cada columna a 1323px: a lo que pide su número más largo,
para que entren las diez sin deslizar la tabla de costado. Con «Unidades»
aparece «U.», y lo paga el nombre del producto (que la ficha muestra
entero)."""

_AYUDA = {
    "Entró": "Compras netas de notas de crédito, más lo que salió de una "
             "orden de producción, un porcionamiento o un empacado.",
    "A un plato": "Lo que el POS descontó del stock por las ventas: venta "
                  "(con lo servido dentro de combos), cortesías, eventos y "
                  "venta interna. El reparto está en la ficha.",
    "En prep.": "Lo que salió como insumo de una orden de producción, un "
                "porcionamiento o un empacado. No es pérdida: pasa al "
                "producto que sale de ahí.",
    "Bajas": "Notas de salida del tipo «Bajas», por fecha de proceso.",
    "Otras": "El resto de las notas de salida: comida de personal, uso del "
             "área, merma fija, control interno.",
    "Ajuste": "Lo que corrigieron los conteos del cierre. Faltante (−): "
              "salió sin documento; puede ser pérdida, una preparación no "
              "registrada, una receta que descarga otro código o un error de "
              "conteo. Sobrante (+): había más de lo que el sistema decía.",
    "Sin plato": "Bajas + otras + faltante. La tabla abre ordenada por acá.",
    "% sin plato": "Sin plato ÷ todo lo que salió, en soles. Cálculo propio, "
                   "no un indicador publicado.",
    "vs 6 cierres": "El % sin plato de este cierre menos el de los seis "
                    "anteriores juntos. No contra el año pasado: el cierre de "
                    "setiembre 2025 trae la limpieza de inventario (regla "
                    "#612).",
    "Consumido al contar": "Ninguna receta descarga estos insumos: su uso "
                           "aparece recién en el conteo, como ajuste.",
}


def _ficha(fila, filas, filas_k, per, k):
    """El producto elegido: en qué se fue lo que salió, su cuenta, la pista
    del otro lado del conteo y el gráfico de sus cierres."""
    u = html.escape(unidad_corta(fila["unidad"]) or "und")
    p = per[k]
    h = (f'<div class="spd-ficha-n">{html.escape(str(fila["producto"]))}</div>'
         f'<div class="spd-ficha-s">{html.escape(str(fila["familia"]).lower())}'
         f' · en {u} · cierre de {p["nombre"].lower()}</div>')
    if fila["clase"] == sin_plato.ALIMENTOS:
        seg = [(c, n, max(float(fila[f"{c}_q"]), 0.0)) for c, n in PARTES_SALIO]
        tot = sum(v for *_, v in seg)
        if tot > 0:
            h += (f'<div class="spd-tit">De lo que salió<span>{_cant(tot)} {u}'
                  f' · {_soles(fila["salio_v"])}</span></div>'
                  '<div class="spd-cien">' + "".join(
                      f'<span title="{n}: {_cant(v)}" style="flex:{v:.3f};'
                      f'background:{C[c]}"></span>' for c, n, v in seg if v > 0)
                  + '</div><div class="spd-cley">' + "".join(
                      f'<div class="{"" if v > 0 else "cero"}"><span><i style="'
                      f'background:{C[c]}"></i>{n}</span><span>'
                      f'{f"{100 * v / tot:.0f} %" if v > 0 else "—"}</span></div>'
                      for c, n, v in seg) + "</div>")
        calc = (fila["ini_q"] + fila["entro_q"] - fila["plato_q"] - fila["prep_q"]
                - fila["baja_q"] - fila["otras_q"] + fila["aj_q"])
        partes = [f'Había <b>{_cant(fila["ini_q"])}</b> + entró '
                  f'<b>{_cant(fila["entro_q"])}</b> − a un plato '
                  f'<b>{_cant(fila["plato_q"])}</b>']
        for c, n in (("prep", "en prep."), ("baja", "bajas"), ("otras", "otras")):
            if fila[f"{c}_q"] > 0.05:
                partes.append(f'− {n} <b>{_cant(fila[f"{c}_q"])}</b>')
        if fila["aj_q"] < -0.05:
            partes.append(f'− faltante <b>{_cant(-fila["aj_q"])}</b>')
        elif fila["aj_q"] > 0.05:
            partes.append(f'+ sobrante <b>{_cant(fila["aj_q"])}</b>')
        partes.append(f'= quedan <b>{_cant(calc)}</b> {u}')
        ok = (' <span class="ok">✓ igual que el kardex</span>'
              if abs(calc - fila["fin_q"]) < 0.05
              else f' (el kardex dice {_cant(fila["fin_q"])})')
        extra = ""
        if fila["combos_q"] > 0.05:
            extra += (f'<br>De la venta, {_cant(fila["combos_q"])} {u} se '
                      'sirvieron dentro de combos.')
        if fila["ini_q"] < -0.05 or fila["fin_q"] < -0.05:
            extra += "<br>Stock negativo: se vendió antes de registrar el ingreso."
        h += f'<div class="spd-cuenta">{" ".join(partes)}{ok}{extra}</div>'
        par = sin_plato.parejas(filas_k, fila["cod"])
        if not par.empty:
            h += ('<div class="spd-pista" title="Un faltante en uno y un '
                  'sobrante en otro puede ser una receta o un conteo con el '
                  'código del otro: el Lomo Saltado descarga medallón y la '
                  'cocina porciona trozos. Es una pista, no una conclusión.">'
                  '<b>Del otro lado del conteo:</b> ' + " · ".join(
                      f'{html.escape(str(o["producto"]))} '
                      f'{"+" if o["aj_q"] > 0 else "−"}{_cant(abs(o["aj_q"]))} '
                      f'{html.escape(unidad_corta(o["unidad"]))}'
                      for _, o in par.iterrows()) + "</div>")
    else:
        h += (f'<div class="spd-cuenta">Había <b>{_cant(fila["ini_q"])}</b> + '
              f'entró <b>{_cant(fila["entro_q"])}</b> − notas '
              f'<b>{_cant(fila["baja_q"] + fila["otras_q"])}</b> − consumido al '
              f'contar <b>{_cant(fila["falt_q"])}</b> = quedan '
              f'<b>{_cant(fila["fin_q"])}</b> {u}<br>Ninguna receta lo '
              f'descarga: su uso aparece recién en el conteo '
              f'({_soles(fila["falt_v"])} en este cierre).</div>')
    st.markdown(h, unsafe_allow_html=True)
    st.plotly_chart(_fig_producto(fila, filas, per, k), width="stretch",
                    key=f"mov_pr_fig_{fila['cod']}",
                    config={"displaylogo": False, "displayModeBar": False})


def _fig_producto(fila, filas, per, k):
    """Los últimos cierres del producto, en su unidad: lo que salió apilado
    —abajo lo que fue a un plato o a una preparación, encima lo que no—, el
    sobrante debajo del cero y una raya con lo que entró."""
    ks = _ks_grafico(per, k)
    h = (filas[filas["cod"] == fila["cod"]].set_index("k")
         .reindex(ks))
    num = h.select_dtypes("number").columns
    h[num] = h[num].fillna(0.0)
    xs = [per[i]["corto"] for i in ks]
    alim = fila["clase"] == sin_plato.ALIMENTOS
    fig = go.Figure()
    capas = (PARTES_SALIO if alim
             else (("falt", "Consumido al contar"), ("otras", "Notas")))
    for c, n in capas:
        y = h[f"{c}_q"] if alim or c != "otras" else h["baja_q"] + h["otras_q"]
        fig.add_bar(x=xs, y=y.clip(lower=0), name=n, marker_color=C[c],
                    marker_line=dict(width=1, color="white"),
                    hovertemplate=f"{n}: %{{y:,.1f}}<extra></extra>")
    if alim:
        fig.add_bar(x=xs, y=-h["sobr_q"], name="Sobrante",
                    marker_color=C["sobr"], customdata=h["sobr_q"],
                    marker_line=dict(width=1, color="white"),
                    hovertemplate="Sobrante: %{customdata:,.1f}<extra></extra>")
    fig.add_scatter(x=xs, y=h["entro_q"], mode="markers", name="Entró",
                    # El trazo de un símbolo de línea es su `color`, no el
                    # de `line`: sin él salía con el primero de la paleta.
                    marker=dict(symbol="line-ew", size=18, color=TEXTO_PRINCIPAL,
                                line=dict(width=2, color=TEXTO_PRINCIPAL)),
                    hovertemplate="Entró: %{y:,.1f}<extra></extra>")
    _compras_layout(fig, alto=alturas.DESTINO_FIG)
    sel = ks.index(k)
    fig.update_layout(
        barmode="relative", bargap=0.4, showlegend=False, hovermode="x unified",
        margin=dict(l=4, r=4, t=8, b=4),
        shapes=[dict(type="rect", xref="x", yref="paper", x0=sel - 0.5,
                     x1=sel + 0.5, y0=0, y1=1, fillcolor=LAVANDA_FONDO,
                     line_width=0, layer="below")])
    fig.update_xaxes(type="category", fixedrange=True,
                     tickfont=dict(size=10, color=GRIS_TEXTO),
                     tickvals=xs, ticktext=[x[:3] for x in xs])
    fig.update_yaxes(fixedrange=True, zeroline=True, zerolinecolor=GRIS_BORDE)
    return fig


def tarjeta_por_producto(fam_sel=()):
    """Tabla, ficha y cierres locales, conservando la firma y el foco (#737)."""
    from .destino_producto_pieza import renderizar
    return renderizar(fam_sel)


def _tarjeta_por_producto_legacy(fam_sel=()):
    """La vista «En qué se fue cada producto»."""
    titulo = "En qué se fue cada producto"
    datos = _cargar(fam_sel)
    if datos is None:
        _vacia(CARD_PRODUCTO, titulo, _SIN_DATOS)
        return
    per, filas, tot = datos
    k = _k_elegido(K_CIERRE_2, per)
    p = per[k]
    _foco_anterior()
    ss = st.session_state
    with st.container(border=True, key=CARD_PRODUCTO):
        st.markdown(CSS_TITULOS_DRILL + _CSS, unsafe_allow_html=True)
        # columnas-internas: título, soles o unidades, y el cierre.
        c_t, c_m, c_s = st.columns([2.6, 0.9, 1.3], vertical_alignment="center")
        with c_t:
            _cabecera(titulo, p)
        with c_m:
            medida = st.segmented_control(
                "Ver en", MEDIDAS, default=MEDIDAS[0], key=K_MEDIDA,
                label_visibility="collapsed") or MEDIDAS[0]
        with c_s:
            _selector("ajses_movpr", K_CIERRE_2, per, tot)

        fk = filas[filas["k"] == k]
        fk = fk.assign(pct_prev=fk["cod"].map(sin_plato.pct_previo(filas, k)))
        mov = (fk["salio_v"].abs() + fk["entro_v"].abs() + fk["aj_v"].abs()) > 0.5
        alim = fk[mov & (fk["clase"] == sin_plato.ALIMENTOS)]
        oper = fk[mov & (fk["clase"] == sin_plato.OPERACION)]
        cuenta = {FILTROS[0]: len(alim),
                  FILTROS[1]: int((alim["baja_v"] > 0.5).sum()),
                  FILTROS[2]: int(sin_plato.sin_salida_registrada(alim).sum()),
                  FILTROS[3]: int((alim["aj_v"] > 0.5).sum())}
        # columnas-internas: qué productos, cuáles y el buscador, en UN
        # renglón (con 1.35 el primero partía sus dos botones en dos).
        c_g, c_f, c_b = st.columns([1.5, 2.75, 0.9], vertical_alignment="center")
        with c_g:
            grupo = st.segmented_control(
                "Qué productos", GRUPOS, default=GRUPOS[0], key=K_GRUPO,
                label_visibility="collapsed") or GRUPOS[0]
        with c_f:
            if grupo == GRUPOS[0]:
                filtro = st.segmented_control(
                    "Cuáles", FILTROS, default=FILTROS[0], key=K_FILTRO,
                    format_func=lambda x: f"{x} · {cuenta[x]:,}",
                    label_visibility="collapsed") or FILTROS[0]
            else:
                filtro = FILTROS[0]
                st.caption(f"{len(oper):,} insumos de operación movieron algo "
                           "en este cierre.")
        with c_b:
            buscar = st.text_input("Buscar", key=K_BUSCAR,
                                   placeholder="Buscar producto",
                                   label_visibility="collapsed")

        f = alim if grupo == GRUPOS[0] else oper
        if filtro == FILTROS[1]:
            f = f[f["baja_v"] > 0.5]
        elif filtro == FILTROS[2]:
            f = f[sin_plato.sin_salida_registrada(f)]
        elif filtro == FILTROS[3]:
            f = f[f["aj_v"] > 0.5]
        q = (buscar or "").strip().lower()
        if q:
            f = f[f["producto"].str.lower().str.contains(q, regex=False)
                  | f["cod"].str.contains(q, regex=False)]
        orden = "sinplato_v" if grupo == GRUPOS[0] else "falt_v"
        f = f.sort_values(orden, ascending=False).reset_index(drop=True)

        # columnas-internas: la tabla y la ficha del elegido, lado a lado
        # (debajo, la tarjeta pasaba de una pantalla). La tabla se lleva
        # dos tercios largos: sus diez columnas, en `_ANCHOS`.
        c_tab, c_fic = st.columns([2.25, 1], gap="medium")
        if f.empty:
            with c_tab:
                st.info("Ningún producto con estos filtros en el cierre de "
                        f"{p['nombre'].lower()}.")
            return
        codigos = f["cod"].tolist()
        foco = ss.get(_K_FOCO)
        pos = codigos.index(foco) if foco in codigos else 0
        ss[_K_FOCO] = codigos[pos]
        tabla = (_tabla_alimentos(f, medida) if grupo == GRUPOS[0]
                 else _tabla_operacion(f, medida))
        with c_tab:
            key = _key_tabla(codigos)
            ss["_mov_pr_key"], ss["_mov_pr_codigos"] = key, codigos
            st.dataframe(
                _estilo(tabla, pos, medida), key=key, on_select="rerun",
                selection_mode="single-row-required",
                selection_default={"selection": {"rows": [pos]}},
                hide_index=True, row_height=27,
                height=min(alturas.DESTINO_TABLA,
                           alturas.por_filas(len(tabla), px_fila=27, extra=38,
                                             minimo=0)),
                column_config={
                    c: st.column_config.Column(
                        width=(_ANCHOS.get(c) if not (c == "Producto" and "U." in tabla.columns)
                               else _ANCHOS[c] - _ANCHOS["U."]),
                        help=_AYUDA.get(c))
                    for c in tabla.columns})
            n_sp = int(tot.set_index("k").loc[k, "n_sinplato"])
            pie = st.container(key="mov_pr_pie")
            pie.caption(
                ("En S/" if medida == MEDIDAS[0] else "En la unidad de cada "
                 "producto") + f" · {len(f):,} productos · "
                + (f"{n_sp:,} salieron sin plato en este cierre"
                   if grupo == GRUPOS[0] else "consumo por conteo"))
        with c_fic:
            _ficha(f.iloc[pos], filas, fk, per, k)
