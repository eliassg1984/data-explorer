"""graficos.movimientos_destino — «A dónde fue lo que entró», la sección de
Movimientos que cruza las BAJAS con lo que se compró, produjo o porcionó
(2026-10-08, regla #614).

Pedido: «cruzar con compra o con producidos de orden de producción», con
una «gráfica de evolución por producto», y aprobado sobre un mockup con los
datos reales. La pregunta es la de cualquier producto que se tira: de lo
que ENTRÓ, cuánto se vendió, cuánto se usó en otras preparaciones y cuánto
se dio de baja. Medido de ene a sep 2026: de 729 tartas de queso producidas
se vendieron 549 y se dieron de baja 152 (21 %); del calamar limpio
porcionado, el 22 %.

DE DÓNDE SALE CADA COLUMNA, por producto y en el restaurante entero (las
áreas sumadas; lo que va de un área a otra suma cero y no entra,
`kardex.TIPOS_ENTRE_AREAS`):

    Entró              compras (los tipos de SUNAT, < 90, netos de notas de
                       crédito) + lo que produjo una orden (94), un
                       porcionamiento (96) o un empacado (90)
    Vendido            el descargo de ventas (95): lo que las recetas dicen
                       que salió
    En preparaciones   lo que salió como INSUMO de una orden, un
                       porcionamiento o un empacado
    Baja               las notas de salida del tipo «Bajas» (`salidas.parquet`)
    Otras salidas      el resto de las notas (comida de personal, uso en el
                       área, pruebas…) y la merma fija y el control interno
    Ajuste             el ajuste de los cierres de inventario (93), con signo:
                       negativo es faltante
    Δ stock            entró − vendido − preparaciones − notas + ajuste: lo
                       que cambió el stock (negativo: se usó stock de antes)

LA FECHA ES LA DEL KARDEX —la de proceso—, también para las bajas: si las
bajas fueran por registro, las columnas no cerrarían entre sí (regla #614,
y la diferencia entre las dos fechas). El chip «Sub Almacén» no recorta:
la cuenta es del restaurante entero. El de Familia, sí.

`% baja` = baja ÷ entró: un cálculo propio, no un estándar publicado.

`armar_destino` es pura y la vigila `test_graficos.py::_pruebas_destino`.
"""

import hashlib
import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
import kardex
from cortes import MESES_ABR_ES
from tema import (
    AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, GRIS_BORDE, GRIS_TEXTO,
    GRIS_TEXTO_SUAVE, LAVANDA_BORDE, LAVANDA_FONDO, PALETA_SERIES,
)
from graficos import alturas
from graficos.base import _compras_layout
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.movimientos_comun import _rango_vigente
from graficos.movimientos_periodo import unidad_corta

CARD = "ajuste_graf_card_izq_mov_destino"
"""La key de la tarjeta: el prefijo `ajuste_graf_card_izq_` le da el marco
de las demás tarjetas de Movimientos (`estilos/_80_cards.py`)."""

_K_FOCO = "_mov_destino_foco"

TIPOS_PRODUCE = ("90", "94", "96")
"""Empacado, orden de producción y porcionamiento: lo que ENTRA es el
producto que sale de ellos, y lo que SALE, el insumo que usaron."""
TIPO_VENTAS = "95"
TIPO_AJUSTE = "93"
TIPOS_NOTAS = ("91", "92", "98")
"""Control interno, merma fija y nota de salida: lo que sale del stock sin
venderse ni transformarse."""

TIPO_BAJA = "Bajas"
"""El tipo de descargo que cuenta como baja (`TIPO DESCARGO` de
`salidas.parquet`)."""

COLS = ("entro", "vendido", "prep", "baja", "baja_val", "otras", "ajuste",
        "quedo", "pct_baja")


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def armar_destino(kx, bajas, por=("cod",)):
    """Por producto (o por producto y mes, con `por=("cod", "mes")`), a
    dónde fue lo que entró. Pura.

    `kx` es lo de `kardex.sql_movimientos_mes` (`mes`, `cod`, `tipo`,
    `cant_in`, `cant_out`); `bajas`, las líneas de baja con `cod`, `mes`,
    `cant` y `valor`. Devuelve una fila por grupo con `COLS`: las
    cantidades en la unidad del kardex, `baja_val` en soles y `pct_baja`
    —baja ÷ entró— vacío donde no entró nada."""
    por = list(por)
    t = kx.copy()
    tipo = t["tipo"].astype(str).str.strip()
    cin, cout = _num(t["cant_in"]), _num(t["cant_out"])
    compra = tipo.str.isdigit() & (tipo < "90")
    produce = tipo.isin(TIPOS_PRODUCE)
    t["entro"] = np.where(compra, cin - cout, np.where(produce, cin, 0.0))
    t["prep"] = np.where(produce, cout, 0.0)
    t["vendido"] = np.where(tipo == TIPO_VENTAS, cout - cin, 0.0)
    t["ajuste"] = np.where(tipo == TIPO_AJUSTE, cin - cout, 0.0)
    t["notas"] = np.where(tipo.isin(TIPOS_NOTAS), cout - cin, 0.0)
    t["cod"] = t["cod"].astype(str).str.strip()
    g = t.groupby(por, as_index=False)[
        ["entro", "prep", "vendido", "ajuste", "notas"]].sum()
    b = bajas.assign(cod=bajas["cod"].astype(str).str.strip())
    b = (b.groupby(por, as_index=False)
          .agg(baja=("cant", "sum"), baja_val=("valor", "sum")))
    r = g.merge(b, on=por, how="outer")
    for c in ("entro", "prep", "vendido", "ajuste", "notas", "baja",
              "baja_val"):
        r[c] = r[c].fillna(0.0)
    # Las notas del kardex incluyen las bajas: el resto son las otras. Una
    # baja que el kardex todavía no tiene (el parquet de salidas es más
    # nuevo) no deja «otras» negativas.
    r["otras"] = (r["notas"] - r["baja"]).clip(lower=0.0)
    r["quedo"] = (r["entro"] - r["vendido"] - r["prep"] - r["notas"]
                  + r["ajuste"])
    r["pct_baja"] = (r["baja"] / r["entro"]).where(r["entro"] > 0) * 100.0
    return r[por + list(COLS)]


def bajas_de(salidas, ini, fin, *, col_fecha="FECHA PROCESADO"):
    """Las líneas de BAJA de `salidas.parquet` entre `ini` y `fin`
    (Timestamps, `fin` exclusivo), por la fecha de PROCESO —la del kardex—,
    sin las anuladas ni las líneas sin producto: `cod`, `mes`, `cant`,
    `valor`. Pura."""
    s = salidas
    f = pd.to_datetime(s[col_fecha], errors="coerce")
    estado = s["NOMBRE ESTADO SALIDA"].fillna("").astype(str).str.upper()
    cod = s["COD PRODUCTO"].fillna("").astype(str).str.strip()
    tipo = s["TIPO DESCARGO"].fillna("").astype(str).str.strip()
    m = ((f >= ini) & (f < fin) & (estado != "ANULADO") & (cod != "")
         & (tipo == TIPO_BAJA))
    return pd.DataFrame({
        "cod": cod[m], "mes": f[m].dt.to_period("M").dt.to_timestamp(),
        "cant": _num(s.loc[m, "CANT SALIDA"]),
        "valor": _num(s.loc[m, "VALOR NETO"]),
    })


def _maestro():
    """Nombre, unidad y familia de cada producto, del maestro que trae el
    inventario valorizado (una fila por área × producto: se queda una)."""
    inv = data.cargar(data.REPORTES["Inventario Valorizado"]["archivo"])
    if inv is None or inv.empty or "CODIGO PRODUCTO" not in inv.columns:
        return None
    m = inv.drop_duplicates("CODIGO PRODUCTO")
    return pd.DataFrame({
        "cod": m["CODIGO PRODUCTO"].astype(str).str.strip(),
        "producto": m["NOMBRE PRODUCTO"].astype(str).str.strip(),
        "unidad": m["UNIDAD KARDEX"].map(unidad_corta),
        "familia": m["NOMBRE FAMILIA"].astype(str).str.strip(),
    })


def _rango_kardex(rng, off=None):
    """`(desde, hasta)` como `date` del rango (corrido `off` atrás), o None
    si cae entero antes de que empiece el kardex (`kardex.INICIO`)."""
    ini, fin = rng
    if off is not None:
        ini, fin = ini - off, fin - off
    hasta = (fin - pd.Timedelta(days=1)).date()
    desde = max(ini.date(), kardex.INICIO)
    if hasta < desde:
        return None
    return desde, hasta


def _fmt(v, dec=1):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v:,.{dec}f}"


def _fmt_pts(v):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{'+' if v > 0 else '−' if v < 0 else ''}{abs(v):.1f}"


def _color_pts(v):
    if v is None or not np.isfinite(v) or abs(v) < 0.05:
        return f"color: {GRIS_TEXTO_SUAVE}"
    return (f"color: {AJUSTE_NEG_TEXTO}; font-weight: 600" if v > 0
            else f"color: {AJUSTE_POS_TEXTO}; font-weight: 600")


def _key_tabla(codigos):
    firma = hashlib.md5("|".join(codigos).encode("utf-8")).hexdigest()[:12]
    return f"mov_destino_tabla_{firma}"


def _foco_de_la_corrida_anterior():
    """El producto que la tabla tenía elegido en la corrida anterior. Se lee
    ANTES de dibujar (el criterio de la Carta costeada, regla #556): la
    selección es de la KEY, no de las filas, y la key cambia con ellas."""
    ss = st.session_state
    key, codigos = ss.get("_mov_destino_key"), ss.get("_mov_destino_codigos")
    evt = ss.get(key) if key else None
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
    except Exception:
        filas = []
    if filas and codigos and 0 <= filas[0] < len(codigos):
        ss[_K_FOCO] = codigos[filas[0]]


def _figura_mes(mes):
    """Lo que entró, se vendió y se dio de baja del producto, mes a mes."""
    fig = go.Figure()
    xs = [f"{MESES_ABR_ES[m.month - 1]} {m.year % 100:02d}" for m in mes["mes"]]
    for col, rot, color in (("entro", "Entró", LAVANDA_BORDE),
                            ("vendido", "Vendido", PALETA_SERIES[1]),
                            ("baja", "Baja", PALETA_SERIES[0])):
        fig.add_bar(x=xs, y=mes[col], name=rot, marker_color=color,
                    hovertemplate=f"%{{x}} · {rot}: %{{y:,.1f}}<extra></extra>")
    _compras_layout(fig, alto=alturas.DESTINO_FIG)
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05,
                      showlegend=True,
                      legend=dict(orientation="h", y=1.18, x=0,
                                  font=dict(size=11)),
                      margin=dict(t=28, b=24, l=8, r=8))
    fig.update_xaxes(type="category")
    return fig


def _fila_pct(mes, mes_ant, rot_ant):
    """El % de baja de cada mes, y el del mismo mes un año antes, como una
    tabla chica debajo del gráfico (dos números por mes no entran como
    etiqueta de barra)."""
    celdas = "".join(
        f'<td style="text-align:center;padding:2px 4px;border:none;color:{GRIS_TEXTO}">'
        f'{MESES_ABR_ES[m.month - 1]}</td>' for m in mes["mes"])
    fila = "".join(
        f'<td style="text-align:center;padding:2px 4px;border:none;font-weight:600">'
        f'{_fmt(p, 0)}{"" if not np.isfinite(p) else " %"}</td>'
        for p in mes["pct_baja"].fillna(np.nan))
    filas = (f'<tr><td style="padding:2px 6px 2px 0;border:none;color:{GRIS_TEXTO}">'
             f'</td>{celdas}</tr>'
             f'<tr><td style="padding:2px 6px 2px 0;border:none;font-weight:600">% baja'
             f'</td>{fila}</tr>')
    if mes_ant is not None:
        ant = "".join(
            f'<td style="text-align:center;padding:2px 4px;border:none;'
            f'color:{GRIS_TEXTO_SUAVE}">{_fmt(p, 0)}'
            f'{"" if not np.isfinite(p) else " %"}</td>'
            for p in mes_ant)
        filas += (f'<tr><td style="padding:2px 6px 2px 0;border:none;'
                  f'color:{GRIS_TEXTO_SUAVE}">{html.escape(rot_ant)}</td>'
                  f'{ant}</tr>')
    return (f'<table style="width:100%;border-collapse:collapse;font-size:12px;'
            f'border-top:1px solid {GRIS_BORDE}">{filas}</table>')


def tarjeta_destino(fam_sel=(), anios=1):
    """La sección entera. `fam_sel` es el chip Familia de la franja;
    `anios`, si se compara con el año pasado (lo elige el panel «Filtros»
    para todas las secciones de salidas: acá, uno o dos es lo mismo)."""
    with st.container(border=True, key=CARD):
        st.markdown(CSS_TITULOS_DRILL, unsafe_allow_html=True)
        st.markdown('<div class="inv-rank-tit">A dónde fue lo que entró</div>',
                    unsafe_allow_html=True)
        rng = _rango_vigente()
        rk = _rango_kardex(rng) if rng else None
        if rk is None:
            st.info("El kardex empieza en enero de 2025: elegí un rango "
                    "desde ahí en la franja de arriba.")
            return
        desde, hasta = rk
        kx = data.movimientos_kardex_mes(desde, hasta)
        salidas = data.cargar("salidas.parquet")
        maestro = _maestro()
        if kx is None or salidas is None or salidas.empty or maestro is None:
            st.info("No se pudo leer el kardex, las salidas o el maestro de "
                    "productos: esta sección queda vacía.")
            return
        ini_k, fin_k = pd.Timestamp(desde), pd.Timestamp(hasta) + pd.Timedelta(days=1)
        t = armar_destino(kx, bajas_de(salidas, ini_k, fin_k))
        t = t.merge(maestro, on="cod", how="left")
        if fam_sel:
            t = t[t["familia"].isin([str(f).strip() for f in fam_sel])]
        t = (t[t["baja"] > 0].sort_values("baja_val", ascending=False)
             .reset_index(drop=True))

        # El mismo rango un año atrás, si el kardex lo tiene.
        rot_ant, t_ant = "", None
        if anios:
            off = pd.DateOffset(years=1)
            rk_a = _rango_kardex((ini_k, fin_k), off)
            if rk_a is not None and pd.Timestamp(rk_a[0]) <= ini_k - off:
                kx_a = data.movimientos_kardex_mes(rk_a[0], rk_a[1])
                if kx_a is not None:
                    t_ant = armar_destino(
                        kx_a, bajas_de(salidas, ini_k - off, fin_k - off))
                    rot_ant = str((fin_k - pd.Timedelta(days=1) - off).year)
        st.caption(
            f"{len(t):,} productos con bajas del "
            f"{desde:%d/%m/%Y} al {hasta:%d/%m/%Y} · fecha del kardex (de "
            "proceso) · el restaurante entero: el chip «Sub Almacén» no "
            "recorta. Elegí uno para ver su evolución."
            + ("" if t_ant is not None or not anios else
               " Sin comparación: el kardex empieza en enero de 2025."))
        if t.empty:
            st.info("Sin bajas en el rango.")
            return

        tabla = pd.DataFrame({
            "Producto": t["producto"].fillna(t["cod"]),
            "U.": t["unidad"].fillna(""),
            "Entró": t["entro"], "Vendido": t["vendido"],
            "En preparaciones": t["prep"], "Baja": t["baja"],
            "S/ baja": t["baja_val"], "Otras salidas": t["otras"],
            "Ajuste": t["ajuste"], "Δ stock": t["quedo"],
            "% baja": t["pct_baja"].fillna(np.inf),
        })
        if t_ant is not None:
            pa = t["cod"].map(t_ant.set_index("cod")["pct_baja"])
            tabla[f"% baja {rot_ant}"] = pa.fillna(np.inf)
            tabla["Δ pts"] = (t["pct_baja"] - pa).fillna(np.inf)

        codigos = t["cod"].tolist()
        _foco_de_la_corrida_anterior()
        foco = st.session_state.get(_K_FOCO)
        pos = codigos.index(foco) if foco in codigos else 0
        foco = codigos[pos]

        fmt_cols = {c: (lambda v: _fmt(v, 1)) for c in (
            "Entró", "Vendido", "En preparaciones", "Baja", "Otras salidas",
            "Ajuste", "Δ stock")}
        fmt_cols["S/ baja"] = lambda v: _fmt(v, 0)
        for c in tabla.columns:
            if c.startswith("% baja"):
                fmt_cols[c] = lambda v: "—" if not np.isfinite(v) else f"{v:.1f} %"
        if "Δ pts" in tabla.columns:
            fmt_cols["Δ pts"] = _fmt_pts
        sty = (tabla.style.format(fmt_cols)
               .apply(lambda r: [f"background-color: {LAVANDA_FONDO}"
                                 if r.name == pos else ""] * len(r), axis=1))
        if "Δ pts" in tabla.columns:
            sty = sty.map(_color_pts, subset=["Δ pts"])
        key = _key_tabla(codigos)
        st.session_state["_mov_destino_key"] = key
        st.session_state["_mov_destino_codigos"] = codigos
        st.dataframe(
            sty, key=key, on_select="rerun",
            selection_mode="single-row-required",
            selection_default={"selection": {"rows": [pos]}},
            hide_index=True, row_height=27,
            height=min(alturas.DESTINO_TABLA,
                       alturas.por_filas(len(tabla), px_fila=27, extra=38,
                                         minimo=0)),
            column_config={
                "Producto": st.column_config.TextColumn(width="medium"),
                "Δ stock": st.column_config.Column(
                    help="Entró − vendido − en preparaciones − notas de "
                         "salida + ajuste: cuánto cambió el stock. Negativo, "
                         "se usó stock de antes del rango."),
                "Ajuste": st.column_config.Column(
                    help="El ajuste de los cierres de inventario. Negativo "
                         "es faltante: salió sin que nadie lo registrara."),
                "En preparaciones": st.column_config.Column(
                    "En prep.", help="Lo que salió como insumo de una orden "
                    "de producción, un porcionamiento o un empacado."),
            })

        # ── El elegido, mes a mes ─────────────────────────────────────────
        f = t.iloc[pos]
        mes = armar_destino(
            kx[kx["cod"].astype(str).str.strip() == foco],
            bajas_de(salidas, ini_k, fin_k).loc[lambda b: b["cod"] == foco],
            por=("cod", "mes")).sort_values("mes")
        mes["mes"] = pd.to_datetime(mes["mes"])
        mes_ant = None
        if t_ant is not None:
            off = pd.DateOffset(years=1)
            kx_a = data.movimientos_kardex_mes(*_rango_kardex(
                (ini_k, fin_k), off))
            if kx_a is not None:
                ma = armar_destino(
                    kx_a[kx_a["cod"].astype(str).str.strip() == foco],
                    bajas_de(salidas, ini_k - off, fin_k - off)
                    .loc[lambda b: b["cod"] == foco], por=("cod", "mes"))
                ma["mes"] = pd.to_datetime(ma["mes"]) + off
                por_mes = ma.set_index("mes")["pct_baja"]
                mes_ant = [float(por_mes.get(m, np.nan)) for m in mes["mes"]]
        u = f["unidad"] if isinstance(f["unidad"], str) else ""
        _pct = f["pct_baja"]
        st.markdown(
            f'<div class="inv-rank-tit" style="margin-top:4px">'
            f'{html.escape(str(f["producto"]))} <span class="inv-rank-tit-n">'
            f'entraron {_fmt(f["entro"])} {u} · se vendieron '
            f'{_fmt(f["vendido"])} · {_fmt(f["baja"])} de baja '
            f'(S/ {_fmt(f["baja_val"], 0)}'
            + (f", {_pct:.1f} % de lo que entró" if np.isfinite(_pct) else "")
            + ")</span></div>", unsafe_allow_html=True)
        st.plotly_chart(_figura_mes(mes), use_container_width=True,
                        key=f"mov_destino_fig_{foco}",
                        config={"displaylogo": False,
                                "displayModeBar": False})
        st.markdown(_fila_pct(mes, mes_ant, rot_ant), unsafe_allow_html=True)
