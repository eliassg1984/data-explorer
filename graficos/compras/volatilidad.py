"""graficos.compras.volatilidad - drill de Volatilidad de insumos.

Ranking de insumos por volatilidad de precio de compra semana a semana,
con drill a un candlestick (una vela = una semana: apertura/máximo/
mínimo/cierre de PRECIO_UNIT) y de ahí a las compras puntuales que
formaron la semana clickeada.

Semáforo de precio: como el dato es un COSTO (no una ganancia), "sube" es
malo (rojo, ERROR) y "baja" es bueno (verde, EXITO) — al revés de la
convención bursátil, a propósito.

`go.Candlestick` no tiene precedente de selección por clic en este
proyecto (a diferencia de go.Bar, que Proveedor ya usa con éxito). Se
asume NO seleccionable de forma confiable, igual que go.Heatmap (regla
#11) y go.Histogram (regla #44): se agrega una traza go.Scatter invisible
(un punto por semana) para capturar el clic, y se ignoran los eventos que
lleguen del candlestick mismo.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import ACENTO, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO, LAVANDA_FONDO
from graficos.base import _card, _compras_layout, _compras_truncar, _slug
from graficos.compras._comun import _first_point
from graficos import alturas

MIN_SEMANAS = 4          # con menos, un candlestick no dice nada
MAX_SEMANAS = 8          # tope de velas visibles — más se vuelve ilegible y
                          # además diluye la volatilidad real entre huecos
MIN_GASTO = 400.0        # S/ gastados en la ventana; filtra ruido de insumos
MIN_COBERTURA = 0.75     # % de semanas con al menos una compra


# ── Funciones puras (testeadas en test_graficos.py) ─────────────────────────

def _vol_semanas_ventana(fechas, minimo=MIN_SEMANAS, maximo=MAX_SEMANAS):
    """Lunes de cada semana con al menos una fecha en `fechas`, ordenados,
    recortado a las `maximo` MÁS RECIENTES. El rango de fecha lo elige el
    usuario en la franja (puede ser "Todo", años) pero el candlestick solo
    tiene sentido sobre una ventana corta y reciente — más semanas no es
    "más historia útil", es un gráfico ilegible y una volatilidad que
    mezcla huecos de años con movimiento real (ver arquitectura.md).
    None si hay menos de `minimo` semanas distintas en total."""
    fechas = fechas.dropna()
    if fechas.empty:
        return None
    inicios = (fechas - pd.to_timedelta(fechas.dt.weekday, unit="D")).dt.normalize()
    semanas = sorted(pd.to_datetime(inicios.unique()))
    if len(semanas) < minimo:
        return None
    return semanas[-maximo:]


def _vol_ohlc_semana(precios_ordenados):
    """OHLC de una lista/Serie de precios YA ordenada por fecha ascendente.
    None si está vacía."""
    precios = [p for p in precios_ordenados if pd.notna(p) and p > 0]
    if not precios:
        return None
    return {"o": float(precios[0]), "c": float(precios[-1]),
            "h": float(max(precios)), "l": float(min(precios))}


def _vol_score(cierres):
    """Suma de variaciones % absolutas semana a semana. Ignora huecos (None)
    al principio de la serie (sin cierre previo del que partir)."""
    cierres = list(cierres)
    while cierres and cierres[0] is None:
        cierres = cierres[1:]
    total = 0.0
    for i in range(1, len(cierres)):
        prev, cur = cierres[i - 1], cierres[i]
        if prev and cur is not None:
            total += abs((cur - prev) / prev * 100)
    return round(total, 1)


def _vol_candidatos(d, col_prod, col_punit, col_fecha, col_valor, semanas,
                    min_gasto=MIN_GASTO, min_cobertura=MIN_COBERTURA):
    """Cierres semanales (con relleno hacia adelante en huecos) por producto,
    solo para los que superan gasto y cobertura mínimos. Devuelve
    {producto: {"cierres": [...], "volatilidad": float}}, ordenable después
    por volatilidad."""
    out = {}
    for prod, g in d.groupby(col_prod):
        gasto = g[col_valor].sum()
        semanas_con_compra = g["_semana"].nunique()
        if gasto < min_gasto or semanas_con_compra < min_cobertura * len(semanas):
            continue
        cierres, prev = [], None
        for sem in semanas:
            sub = g[g["_semana"] == sem].sort_values(col_fecha)
            ohlc = _vol_ohlc_semana(sub[col_punit].tolist())
            c = ohlc["c"] if ohlc else prev
            cierres.append(c)
            if c is not None:
                prev = c
        out[prod] = {"cierres": cierres, "volatilidad": _vol_score(cierres)}
    return out


def _vol_detalle_producto(d, prod, col_prod, col_punit, col_fecha, col_prov,
                          col_cant, semanas):
    """OHLC + filas de compra (fecha, proveedor, cantidad, precio) por
    semana, para UN producto ya elegido."""
    g = d[d[col_prod] == prod]
    weeks = []
    prev_close = None
    for sem in semanas:
        sub = g[g["_semana"] == sem].sort_values(col_fecha)
        ohlc = _vol_ohlc_semana(sub[col_punit].tolist())
        rows = []
        for _, r in sub.iterrows():
            precio = r[col_punit]
            if pd.isna(precio) or precio <= 0:
                continue
            rows.append({
                "fecha": r[col_fecha],
                "prov": str(r[col_prov]) if col_prov else "—",
                "cant": r[col_cant] if col_cant else None,
                "precio": float(precio),
            })
        if ohlc is None:
            c = prev_close if prev_close is not None else 0.0
            ohlc = {"o": c, "h": c, "l": c, "c": c}
        weeks.append({**ohlc, "semana": sem, "rows": rows})
        prev_close = ohlc["c"]
    return weeks


# ── CSS de las celdas (semáforo) ─────────────────────────────────────────────

def _sty_delta(v):
    if pd.isna(v):
        return "color:#c9c9d1"
    if abs(v) < 1:
        return f"color:{GRIS_TEXTO}"
    color, fondo = (ERROR, "#fee2e2") if v > 0 else (EXITO, "#f0fdf4")
    return f"background-color:{fondo}; color:{color}; font-weight:600; border-radius:6px;"


def _fmt_delta(v):
    if pd.isna(v):
        return "—"
    return f"{'+' if v >= 0 else '−'}{abs(v):.1f}%"


def _sty_vol_bar(serie):
    """Barra de volatilidad falseada con un gradiente CSS: el color del
    acento hasta `pct`%, lavanda claro después — mismo truco que el mockup,
    sin necesitar un componente AgGrid aparte."""
    maximo = serie.max() or 1
    out = []
    for v in serie:
        pct = 0 if pd.isna(v) else round(v / maximo * 100)
        out.append(
            f"background:linear-gradient(90deg, {ACENTO} {pct}%, "
            f"{LAVANDA_FONDO} {pct}%); font-weight:600;"
        )
    return out


# ── Vista principal ──────────────────────────────────────────────────────────

@st.fragment
def _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                               col_valor, col_cant, col_um, col_moneda=None):
    """Ranking de insumos por volatilidad de precio → candlestick semanal
    del insumo elegido → compras de la semana clickeada.

    `col_moneda` es opcional (no resuelto en `__init__.py` hasta que este
    drill lo necesitó): si no llega o no está en `d`, no se filtra por
    moneda — mezclar monedas en una misma serie sería incorrecto, pero es
    preferible a que el drill no abra por falta de la columna (el demo
    local, por ejemplo, no la trae)."""
    if not (col_prod and col_punit and col_fecha and col_valor):
        st.info("Faltan columnas (Producto, Precio unitario, Fecha o Valor) "
                "para calcular volatilidad.")
        return

    dd = d.copy()
    if col_moneda and col_moneda in dd.columns:
        dd = dd[dd[col_moneda].astype(str).str.strip().isin(["01", "1"])]
    dd[col_fecha] = pd.to_datetime(dd[col_fecha], errors="coerce")
    dd[col_punit] = pd.to_numeric(dd[col_punit], errors="coerce")
    dd[col_valor] = pd.to_numeric(dd[col_valor], errors="coerce").fillna(0)
    dd = dd.dropna(subset=[col_fecha, col_prod])
    dd = dd[dd[col_prod].astype(str).str.strip() != ""]

    semanas = _vol_semanas_ventana(dd[col_fecha])
    if not semanas:
        st.info("Necesitás al menos 4 semanas de compras en el rango "
                "seleccionado para armar un candlestick.")
        return
    dd["_semana"] = (dd[col_fecha] - pd.to_timedelta(
        dd[col_fecha].dt.weekday, unit="D")).dt.normalize()
    dd = dd[dd["_semana"].isin(semanas)]

    candidatos = _vol_candidatos(dd, col_prod, col_punit, col_fecha, col_valor, semanas)
    if not candidatos:
        st.info("Ningún insumo tiene compras regulares (≥75% de las semanas) "
                "y gasto relevante (≥ S/ 400) en este rango.")
        return

    ranking = sorted(candidatos.items(), key=lambda kv: -kv[1]["volatilidad"])

    # ── Tabla ranking (semáforo, solo lectura) ───────────────────────────
    with _card("compras_vol_ranking", "Insumos ordenados por volatilidad", titulo_arriba=True):
        n_sem = len(semanas)
        cols_sem = [f"S{i + 2}" for i in range(n_sem - 1)]
        filas = []
        for prod, info in ranking:
            cierres = info["cierres"]
            deltas = [None if (cierres[i] is None or cierres[i - 1] is None or not cierres[i - 1])
                     else (cierres[i] - cierres[i - 1]) / cierres[i - 1] * 100
                     for i in range(1, len(cierres))]
            filas.append([_compras_truncar(str(prod), 34), *deltas, info["volatilidad"]])
        tv = pd.DataFrame(filas, columns=["Insumo", *cols_sem, "Volatilidad"])

        sty = tv.style.format({c: _fmt_delta for c in cols_sem} | {"Volatilidad": "{:.1f}"})
        for c in cols_sem:
            sty = sty.map(_sty_delta, subset=[c])
        sty = sty.apply(_sty_vol_bar, subset=["Volatilidad"])
        st.dataframe(sty, use_container_width=True, hide_index=True,
                     height=alturas.por_filas(len(tv), px_fila=34,
                                              extra=60, minimo=0))
        st.caption(f"Familia Alimentos · {n_sem} semanas · insumos con ≥ S/ 400 "
                   "de gasto y compras en al menos 75% de las semanas del rango.")

    # ── Selector de insumo (mismo orden que el ranking) ──────────────────
    nombres = [str(p) for p, _ in ranking]
    labels = [f"{i + 1}. {_compras_truncar(str(p), 40)} — {info['volatilidad']:.1f} pts"
             for i, (p, info) in enumerate(ranking)]
    idx_sel = st.selectbox("Ver candlestick de:", range(len(nombres)),
                           format_func=lambda i: labels[i], key="compras_vol_prod_idx")
    prod_sel = nombres[idx_sel]

    if st.session_state.get("compras_vol_prod_prev") != prod_sel:
        st.session_state["compras_vol_prod_prev"] = prod_sel
        st.session_state["compras_vol_semfocus"] = None
        st.session_state["compras_vol_last_click"] = None

    unidad_raw = str(dd.loc[dd[col_prod] == prod_sel, col_um].mode().iat[0]) \
        if col_um and col_um in dd.columns and not dd.loc[dd[col_prod] == prod_sel, col_um].empty \
        else "kg"
    unidad = {"KILOS": "kg", "KG": "kg", "LITROS": "L", "LT": "L", "UND": "und"}.get(
        unidad_raw.upper(), unidad_raw.lower())

    weeks = _vol_detalle_producto(dd, prod_sel, col_prod, col_punit, col_fecha,
                                  col_prov, col_cant, semanas)

    # ── Card de detalle: stats + candlestick + compras de la semana ──────
    with _card("compras_vol_detalle", titulo_arriba=False):
        cierres = [w["c"] for w in weeks]
        precio_actual = cierres[-1]
        cambio_total = ((cierres[-1] - cierres[0]) / cierres[0] * 100) if cierres[0] else 0.0
        vol_total = candidatos[prod_sel]["volatilidad"]
        color_cambio = ERROR if cambio_total > 0.05 else (EXITO if cambio_total < -0.05 else GRIS_TEXTO)
        st.markdown(
            f'<div style="display:flex; justify-content:space-between; align-items:baseline; '
            f'flex-wrap:wrap; gap:16px; margin-bottom:.75rem;">'
            f'<span style="font-size:1.1rem; font-weight:700;">{_compras_truncar(str(prod_sel), 48)}</span>'
            f'<div style="display:flex; gap:24px;">'
            f'<div style="text-align:right;"><span style="display:block; font-size:.68rem; '
            f'font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:{GRIS_TEXTO};">'
            f'Precio actual</span><span style="font-size:1.15rem; font-weight:700;">'
            f'S/ {precio_actual:,.2f} /{unidad}</span></div>'
            f'<div style="text-align:right;"><span style="display:block; font-size:.68rem; '
            f'font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:{GRIS_TEXTO};">'
            f'Cambio total</span><span style="font-size:1.15rem; font-weight:700; color:{color_cambio};">'
            f'{"+" if cambio_total >= 0 else "−"}{abs(cambio_total):.1f}%</span></div>'
            f'<div style="text-align:right;"><span style="display:block; font-size:.68rem; '
            f'font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:{GRIS_TEXTO};">'
            f'Volatilidad</span><span style="font-size:1.15rem; font-weight:700;">'
            f'{vol_total:.1f} pts</span></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=semanas, open=[w["o"] for w in weeks], high=[w["h"] for w in weeks],
            low=[w["l"] for w in weeks], close=[w["c"] for w in weeks],
            increasing=dict(line=dict(color=ERROR), fillcolor=ERROR),
            decreasing=dict(line=dict(color=EXITO), fillcolor=EXITO),
            hovertext=[f"Semana del {s:%d/%m} · abre S/ {w['o']:.2f} · máx S/ {w['h']:.2f} "
                      f"· mín S/ {w['l']:.2f} · cierra S/ {w['c']:.2f}"
                      for s, w in zip(semanas, weeks)],
            hoverinfo="text",
            name="",
        ))
        # Overlay invisible para capturar el clic (go.Candlestick sin
        # precedente de selección confiable en este proyecto — ver rules #11/#44).
        fig.add_trace(go.Scatter(
            x=semanas, y=[(w["h"] + w["l"]) / 2 for w in weeks],
            mode="markers", marker=dict(size=38, opacity=0),
            hoverinfo="skip", showlegend=False,
        ))
        _compras_layout(fig, alto=alturas.APOYO)
        fig.update_layout(
            xaxis=dict(gridcolor=GRIS_BORDE, showgrid=False, rangeslider=dict(visible=False)),
            yaxis=dict(gridcolor=GRIS_BORDE, tickprefix="S/ "),
            showlegend=False,
        )

        _chart_key = f"compras_g_vol_candle_{_slug(str(prod_sel))}"
        _cfg = {"displaylogo": False, "displayModeBar": False}
        evt = st.plotly_chart(fig, use_container_width=True, key=_chart_key,
                              on_select="rerun", selection_mode="points", config=_cfg)

        # Procesar clic (dedup, patrón de proveedor.py): solo se atiende un
        # punto que venga de la traza 1 (el overlay), no de la 0 (las velas).
        _mp = _first_point(evt)
        if _mp is not None and _mp.get("curve_number") == 1:
            _pi = _mp.get("point_index", _mp.get("point_number"))
            if _pi is not None and st.session_state.get("compras_vol_last_click") != _pi:
                st.session_state["compras_vol_last_click"] = _pi
                _misma = st.session_state.get("compras_vol_semfocus") == _pi
                st.session_state["compras_vol_semfocus"] = None if _misma else _pi

        sem_focus = st.session_state.get("compras_vol_semfocus")
        if sem_focus is None or not (0 <= sem_focus < len(weeks)):
            # sin clic: la semana con el mayor movimiento propio (abre→cierra)
            sem_focus = max(range(len(weeks)), key=lambda i: abs(weeks[i]["c"] - weeks[i]["o"]))

        w = weeks[sem_focus]
        ini = semanas[sem_focus]
        fin = ini + pd.Timedelta(days=6)
        delta_txt = ""
        if sem_focus > 0 and weeks[sem_focus - 1]["c"]:
            var = (w["c"] - weeks[sem_focus - 1]["c"]) / weeks[sem_focus - 1]["c"] * 100
            color = ERROR if var > 0 else (EXITO if var < 0 else GRIS_TEXTO)
            delta_txt = (f' <span style="color:{color}; font-weight:700;">'
                        f'{"+" if var >= 0 else "−"}{abs(var):.1f}% vs semana anterior</span>')
        st.markdown(
            f'<div style="margin-top:.5rem; padding-top:.75rem; border-top:1px solid {GRIS_BORDE};">'
            f'<span style="font-weight:600;">Semana del {ini:%d/%m} al {fin:%d/%m}</span>{delta_txt}'
            f'</div>', unsafe_allow_html=True,
        )

        if not w["rows"]:
            st.caption("Sin compras registradas esta semana — precio repetido del último cierre.")
        else:
            tp = pd.DataFrame(w["rows"])
            maxp, minp = tp["precio"].max(), tp["precio"].min()

            def _sty_precio(v):
                if maxp == minp:
                    return ""
                if v == maxp:
                    return f"color:{ERROR}; font-weight:700;"
                if v == minp:
                    return f"color:{EXITO}; font-weight:700;"
                return ""

            tp = tp.rename(columns={"fecha": "Fecha", "prov": "Proveedor",
                                    "cant": "Cantidad", "precio": f"Precio/{unidad}"})
            fmts = {"Fecha": lambda v: f"{v:%d/%m/%Y}",
                   "Cantidad": lambda v: "—" if pd.isna(v) else f"{v:,.2f} {unidad}",
                   f"Precio/{unidad}": lambda v: f"S/ {v:,.2f}"}
            sty_p = (tp.style.format(fmts)
                     .map(_sty_precio, subset=[f"Precio/{unidad}"])
                     .hide(axis="index"))
            st.dataframe(sty_p, use_container_width=True, hide_index=True,
                        height=alturas.por_filas(len(tp), px_fila=34, extra=60,
                                                 minimo=0, rol=alturas.MINI))
        st.caption("Tocá una vela para ver las compras de esa semana.")
