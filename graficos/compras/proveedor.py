"""graficos.compras.proveedor - drill de Proveedor.

Desde el 2026-10-12 (regla #646) es UNA fila de dos tarjetas, la «opción
A» elegida sobre tres maquetas clicables:

    [ Ranking de proveedores ][ Ficha del proveedor elegido                ]
    [   (a toda la altura)   ][  nombre · cifras del rango                 ]
    [                        ][  curva (proveedor, o el producto en foco)  ]
    [                        ][  Productos | Documentos, con sus vistas    ]

Hasta ese día eran cuatro tarjetas en dos filas (reglas #578 y #579), y
tres de ellas podían hablar de proveedores distintos: sin clic, Productos y
Documentos mostraban el primero del ranking y la Evolución el mayor de SU
ventana. Ahora la fila marcada del ranking manda sobre toda la ficha.

Las columnas se crean ARRIBA, antes de llenar ninguna: el Ranking fija el
foco que lee la ficha, así que se dibuja primero.

Lo que se conserva de las cuatro tarjetas, con su sitio nuevo:

- Ranking: fecha, filtro de proveedores, clic para elegir y fila TOTAL. Gana
  la variación contra el período anterior de igual largo («nuevo» / «vuelve»
  cuando no hay contra qué) y pierde la columna Docs, que pasa a la ficha.
- Evolución → la CURVA de la ficha: ventana, grano (con «Documento»), medida
  y el producto en foco. El período en curso va rayado y se compara con los
  mismos días del anterior (`_comun.tramo_parcial`).
- Productos → pestaña Productos: «Total del rango» (con precio promedio y
  «vs. habitual») y «Desglose» (antes «Por mes»: los últimos seis puntos de
  la curva, con la tendencia de trece).
- Documentos → pestaña Documentos: «Por documento» (con días desde la
  compra anterior y el producto que subió de precio, en lugar de la
  variación contra la factura anterior) y «Por <grano>».
"""

import html
import zlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from st_aggrid import AgGrid, JsCode

from cortes import MESES_ABR_ES
from tema import (ACENTO, ACENTO_TEXTO_OSCURO, GRIS_BORDE, GRIS_TEXTO,
                  GRIS_TEXTO_MEDIO, LAVANDA_BORDE, LAVANDA_CHIP,
                  TEXTO_PRINCIPAL)
from inyecciones import inyectar_html
from graficos.base import (
    PALETA_CALLAI, _compras_layout, _compras_truncar, paso_etiquetas,
    preservar_widgets, rango_tarjeta,
)
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CATEGORIA_SEC, COLUMNAS_DRILL_FICHA,
    CROMO_GRID_RANK, GAP_DRILL, agregar_periodo, base_normalizada,
    documento_legible, filtro_proveedores, inicio_de_periodo,
    moda_por_grupo, periodos_ordenados, selector_fecha_tarjeta,
    tramo_parcial, unidad_corta,
)
from graficos.compras._css_proveedor import (
    CSS as CSS_PROVEEDOR, CSS_RANKING_PROV,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras.semanal import precio_habitual
from graficos import alturas, periodo


_KEYS_WIDGET = (
    "compras_prov_gran", "cp_prov_win_size", "cp_evo_periodo",
    "cp_prov_tab", "cp_prov_docs_modo", "cp_prov_prods_modo",
    "cp_evo_medida", "cp_prov_q", "cp_prov_cb::*",
)
"""Los controles de esta sección, para que la escalada no se los lleve.

La consume `preservar_widgets` en el `st.rerun(scope="app")` de más abajo:
ese rerun aborta la corrida antes de dibujarlos y Streamlit recolecta lo
que no se dibujó, así que sin esta tupla mover la fecha de la cabecera
devolvía el grano a «Mes» y volvía a marcar a TODOS los proveedores. Ver
`graficos/base.py::preservar_widgets` y `arquitectura.md` regla #373.

Las dos últimas son del filtro de proveedores (`_comun.py`), que dibuja una
checkbox por razón social — de ahí el prefijo con `*`. Los botones de atajo
(`cp_prov_topn3`…), las flechas de la ventana y «volver» NO van: un
`st.button` no guarda nada.

(«Nombres en barras», `cp_prov_show_names`, se fue el 2026-10-12: desde que
el ranking es una tabla nadie leía su valor. Y la medida propia del
Desglose, `cp_prov_prods_medida`, con él: la medida es UNA, la de la
ficha. Regla #646.)"""


_GRANOS = ("Día", "Semana", "Mes", "Año", "Documento")
"""Los granos de la curva, que también parten el Desglose y los Documentos
agrupados. «Documento» entró el 2026-10-12 (regla #646): con «Precio» es
revisar el precio de cada producto factura por factura."""

_GRAN_POR = {"Día": "Por día", "Semana": "Por semana", "Mes": "Por mes",
             "Año": "Por año", "Documento": "Por documento"}

_MEDIDAS = {"valor": "Soles", "cant": "Cantidad", "precio": "Precio"}
"""Lo que puede medir la curva y el Desglose (regla #579). Cantidad y
Precio sólo tienen sentido sobre UN producto en la curva: sumar kilos de
mantequilla con litros de aceite no da nada que se pueda leer. En el
Desglose sí, porque cada fila es un producto."""

_UMBRAL_PRECIO = 2.0
"""% de suba o baja del precio de un período contra el anterior a partir
del cual la celda del Desglose se pinta (rojo / verde). Umbral PROPIO, no
un estándar: es el que se probó en la maqueta (regla #646)."""

_FILAS_LISTA = 6
"""Filas a la vista de la tabla de la ficha antes de scrollear. Con
`alturas.CURVA_FICHA` es lo que entra en el `--alto-util` de la laptop."""

_ALTO_FILA = 24


# ── Formato ────────────────────────────────────────────────────────────


def _esc(t):
    return html.escape(str(t), quote=True)


def _var_pct(cur, prev):
    """Variación % de `cur` contra `prev`; `inf` si no hay contra qué (no
    hay anterior, o es cero). Desde cero no hay porcentaje."""
    if prev is None or pd.isna(prev) or float(prev) <= 0 or cur is None \
            or pd.isna(cur):
        return np.inf
    return (float(cur) - float(prev)) / float(prev) * 100


def _fmt_var(v):
    """«▲ 12.3%», «▼ 4.0%», «0.0%» o «—»."""
    if not np.isfinite(v):
        return "—"
    if abs(v) < 0.05:
        return "0.0%"
    return f"{'▲' if v > 0 else '▼'} {abs(v):.1f}%"


def _cls_var(v):
    """Rojo si subió el gasto, verde si bajó; sin color por debajo del
    0,5 % — el código de todo Compras."""
    if not np.isfinite(v) or abs(v) < 0.5:
        return ""
    return "sube" if v > 0 else "baja"


def _fila_var(v):
    return f'<span class="var {_cls_var(v)}">{_fmt_var(v)}</span>'


def _cant_txt(c):
    """Una cantidad sin ceros de más: «112», «2.5», «0.75»."""
    return f"{c:,.2f}".rstrip("0").rstrip(".")


def _um_corta(um):
    s = str(um or "").strip()
    return "" if s.lower() in ("", "nan", "none") else unidad_corta(s)


def _soles(v):
    return f"S/ {v:,.0f}"


def _fmt_medida(v, medida, um=""):
    """Un valor de la medida, como se lee: «S/ 4,421», «112 kg»,
    «S/ 39.41» (el precio con céntimos) o «—»."""
    if v is None or pd.isna(v):
        return "—"
    if medida == "cant":
        return _cant_txt(v) + (f" {um}" if um else "")
    if medida == "precio":
        return f"S/ {v:,.2f}"
    return _soles(v)


def _mes_anio(f):
    f = pd.Timestamp(f)
    return f"{MESES_ABR_ES[f.month - 1]} {f.year}"


def _etq(clave, gran, corta=False):
    """El rótulo de un período a partir de su CLAVE (`_per_sort`).

    La clave y no el rótulo de `agregar_periodo`: en grano Día el rótulo
    «11 Oct» se repite en una ventana de 12 meses alineada (el 11 de
    octubre de los dos años) y un eje de categorías juntaba los dos días en
    uno. La clave es única y ordena (regla #646)."""
    k = str(clave)
    try:
        if gran == "Mes":
            f = pd.Timestamp(k + "-01")
            return f"{MESES_ABR_ES[f.month - 1]} {str(f.year)[2:]}"
        if gran in ("Semana", "Día"):
            f = pd.Timestamp(k)
            return f"{f.day} {MESES_ABR_ES[f.month - 1]}"
        if gran == "Documento":
            leg = documento_legible(pd.Series([k.split("|", 1)[-1]])).iat[0]
            return str(leg).split("-")[-1] if corta else str(leg)
    except (ValueError, IndexError):
        pass
    return k


def _con_clave(df):
    """`per` pasa a ser la CLAVE del período (ver `_etq`)."""
    if "_per_sort" in df.columns:
        df["per"] = df["_per_sort"]
    return df


# ── Contra el período anterior (Ranking y cifras de la ficha) ─────────


def _contra_anterior(d_full, col_prov, col_valor, col_fecha, rango):
    """Lo comprado a cada proveedor en el período ANTERIOR de igual largo
    al rango del Ranking, y la última compra antes del rango.

    Con eso el Ranking dice qué cambió: Doble G −63 %, The Spirit +84 %, y
    Vittory Meats «vuelve» tras cuatro meses — nada de eso se veía con el
    monto solo (regla #646). Cuenta descriptiva, no un indicador estándar.
    `None` sin histórico o sin rango."""
    if d_full is None or rango is None or not col_fecha \
            or col_fecha not in d_full.columns:
        return None
    ini = pd.Timestamp(rango[0]).normalize()
    fin = pd.Timestamp(rango[1]).normalize()
    dias = (fin - ini).days + 1
    p_ini = ini - pd.Timedelta(days=dias)
    p_fin = ini - pd.Timedelta(days=1)
    f = pd.to_datetime(d_full[col_fecha], errors="coerce").dt.normalize()
    prov = d_full[col_prov].astype(str)
    v = pd.to_numeric(d_full[col_valor], errors="coerce").fillna(0)
    m_prev = (f >= p_ini) & (f <= p_fin)
    m_antes = f < ini
    return {
        "prev": v[m_prev].groupby(prov[m_prev]).sum(),
        "ult": f[m_antes].groupby(prov[m_antes]).max(),
        "ini": ini, "fin": fin, "dias": dias,
    }


def _estado(nombre, actual, ant):
    """`(variación, estado, ayuda)` de un proveedor contra el período
    anterior. Estado: «» (hay variación), «nuevo» (nunca antes) o «vuelve»
    (compró antes, pero no en el período anterior)."""
    if ant is None:
        return np.inf, "", ""
    prev = float(ant["prev"].get(nombre, 0.0))
    if prev > 0:
        return _var_pct(actual, prev), "", ""
    ult = ant["ult"].get(nombre)
    if ult is None or pd.isna(ult):
        return np.inf, "nuevo", "Primera compra en este rango"
    return (np.inf, "vuelve",
            f"Sin compras desde el {ult.day} {MESES_ABR_ES[ult.month - 1]} "
            f"{ult.year}")


def _ppv(d_full, base, cols, prov, rango):
    """«vs. precio habitual»: cuánto se pagó de más (+) o de menos (−) en
    soles contra el precio habitual de cada línea, y el % por producto.

    El precio habitual es el de «Compras por período»
    (`semanal.precio_habitual`: la mediana del precio unitario de los 90
    días anteriores, sin contar el mismo día) — la MISMA cuenta en las dos
    vistas. La forma es la de la variación de precio de compra (PPV) de la
    contabilidad de costos: (precio pagado − precio de referencia) ×
    cantidad; usar el habitual como referencia es adaptación propia.

    Ojo al leerlo: si un proveedor es casi el único que vende un producto,
    el habitual sale de SUS precios, y la columna dice «no subió», no «es
    barato»."""
    (col_prov, col_prod, col_cant, col_valor, _cp, _cu, col_fecha,
     _cd) = cols
    if d_full is None or not (col_prod and col_cant and col_fecha) \
            or rango is None:
        return None, {}
    prods = base.loc[base["prov"] == prov, "prod"].unique()
    if not len(prods):
        return None, {}
    ini = pd.Timestamp(rango[0]).normalize()
    fin = pd.Timestamp(rango[1]).normalize()
    h = d_full[d_full[col_prod].astype(str).isin(prods)]
    f = pd.to_datetime(h[col_fecha], errors="coerce").dt.normalize()
    h = h[(f >= ini - pd.Timedelta(days=90)) & (f <= fin)]
    f = f.loc[h.index]
    if h.empty:
        return None, {}
    v = pd.to_numeric(h[col_valor], errors="coerce")
    c = pd.to_numeric(h[col_cant], errors="coerce")
    ref = precio_habitual(h[col_prod].astype(str), f, v, c)
    m = ((h[col_prov].astype(str) == prov) & (f >= ini) & (ref.notna())
         & (c > 0) & (v > 0))
    if not m.any():
        return None, {}
    ppv = ((v / c - ref) * c)[m]
    vref = (ref * c)[m]
    prod = h.loc[m, col_prod].astype(str)
    g = pd.DataFrame({"ppv": ppv, "vref": vref, "prod": prod}).groupby(
        "prod")[["ppv", "vref"]].sum()
    pct = (g["ppv"] / g["vref"].where(g["vref"] > 0) * 100).to_dict()
    return float(ppv.sum()), pct


# ── Ficha: cabecera y cifras ───────────────────────────────────────────


def _html_kpis(compra, var, estado, ayuda, pct, docs, ppv, ant):
    """La franja de cifras de la ficha: todas del RANGO del Ranking."""
    if ant is not None:
        _dias = ant["dias"]
        _tit_var = f"vs. los {_dias} días antes"
        _det = (f'{ant["ini"] - pd.Timedelta(days=_dias):%d/%m} – '
                f'{ant["ini"] - pd.Timedelta(days=1):%d/%m}')
    else:
        _tit_var, _det = "vs. período anterior", ""
    if estado:
        _v = f'<span class="cp-fi-chip {estado}" title="{_esc(ayuda)}">{estado}</span>'
    else:
        _v = f'<b class="{_cls_var(var)}">{_fmt_var(var)}</b>'
    _tk = (_soles(compra / docs) if docs else "—")
    if ppv is None:
        _p = '<b class="igual">—</b>'
    elif abs(ppv) < 1:
        _p = '<b class="igual">S/ 0</b>'
    else:
        _p = (f'<b class="{"sube" if ppv > 0 else "baja"}">'
              f'{"+" if ppv > 0 else "−"}{_soles(abs(ppv))}</b>')
    _ayuda_ppv = ("Lo pagado de más (+) o de menos (−) contra el precio "
                  "habitual de cada compra: la mediana de los 90 días "
                  "anteriores, la misma de «Compras por período»")
    return ('<div class="cp-fi-kpis">'
            f'<div><span>Compra en el rango</span><b>{_soles(compra)}</b></div>'
            f'<div title="{_esc(_det)}"><span>{_tit_var}</span>{_v}</div>'
            f'<div><span>% del total</span><b>{pct:.1f}%</b></div>'
            f'<div><span>Documentos · ticket</span><b>{docs:,}</b>'
            f'<small>{_tk}</small></div>'
            f'<div title="{_esc(_ayuda_ppv)}"><span>vs. precio habitual</span>{_p}</div>'
            '</div>')


# ── La curva ───────────────────────────────────────────────────────────


def _fig_curva(xs, ys, gran, medida, um, parcial, ref, custom, color):
    """La curva de la ficha. El último período, si está a medias, va
    RAYADO, con el tramo final punteado y el punto hueco, y una raya en el
    valor de los mismos días del período anterior (`ref`): así no se lee
    como una caída (regla #646)."""
    n = len(xs)
    vals = [None if (v is None or pd.isna(v)) else float(v) for v in ys]
    nums = [v for v in vals if v is not None]
    if ref is not None and not pd.isna(ref):
        nums.append(float(ref))
    if not nums:
        nums = [0.0]
    if medida == "precio":
        lo, hi = min(nums), max(nums)
        pad = (hi - lo) * 0.2 or hi * 0.05 or 1.0
        y0, y1 = max(0.0, lo - pad), hi + pad
    else:
        y0, y1 = 0.0, max(nums) * 1.15 or 1.0
    fig = go.Figure()
    ult = n - 2 if parcial and n > 1 else n - 1
    if parcial and n:
        fig.add_bar(
            x=[xs[-1]], y=[y1 - y0], base=[y0], width=0.9,
            marker=dict(color="rgba(0,0,0,0)", line=dict(width=0),
                        pattern=dict(shape="/", fgcolor=GRIS_BORDE, size=7,
                                     solidity=0.25)),
            hoverinfo="skip", showlegend=False)
    _fill = "none" if medida == "precio" else "tozeroy"
    _rgba = color.replace(")", ", 0.10)").replace("rgb(", "rgba(") \
        if color.startswith("rgb") else "rgba(108,92,231,0.10)"
    if medida == "valor":
        _ht = "%{customdata[0]}<br><b>S/ %{y:,.0f}</b>%{customdata[1]}<extra></extra>"
    elif medida == "precio":
        _ht = "%{customdata[0]}<br><b>S/ %{y:,.2f}</b>%{customdata[1]}<extra></extra>"
    else:
        _ht = ("%{customdata[0]}<br><b>%{y:,.1f} " + str(um)
               + "</b>%{customdata[1]}<extra></extra>")
    fig.add_scatter(
        x=xs[:ult + 1], y=vals[:ult + 1], mode="lines+markers",
        line=dict(color=color, width=2.5), marker=dict(color=color, size=6),
        fill=_fill, fillcolor=_rgba, connectgaps=True,
        customdata=custom[:ult + 1], hovertemplate=_ht, showlegend=False)
    if parcial and n > 1:
        fig.add_scatter(
            x=xs[-2:], y=vals[-2:], mode="lines",
            line=dict(color=color, width=2, dash="dot"),
            hoverinfo="skip", showlegend=False)
        if ref is not None and not pd.isna(ref) and medida != "precio":
            fig.add_scatter(
                x=[xs[-1]], y=[float(ref)], mode="markers",
                marker=dict(symbol="line-ew-open", size=22,
                            color=GRIS_TEXTO_MEDIO,
                            line=dict(color=GRIS_TEXTO_MEDIO, width=2)),
                hoverinfo="skip", showlegend=False)
        fig.add_scatter(
            x=[xs[-1]], y=[vals[-1]], mode="markers",
            marker=dict(symbol="circle-open", size=9, color=color,
                        line=dict(color=color, width=2)),
            customdata=custom[-1:], hovertemplate=_ht, showlegend=False)
    _etqs = [_etq(x, gran, corta=True) for x in xs]
    # 560 y no los ~690 que mide en la laptop: el ancho real no lo conoce
    # Python, y con menos se pisaban los rótulos en una ventana angosta.
    _paso = paso_etiquetas(n, max((len(e) for e in _etqs), default=1),
                           ancho=560, px_fuente=11)
    _tv = [x for i, x in enumerate(xs) if (n - 1 - i) % _paso == 0]
    _compras_layout(fig, alto=alturas.CURVA_FICHA)
    if medida == "precio":
        _yfmt = dict(tickprefix="S/ ", tickformat=",.1f")
    else:
        _yfmt = dict(tickformat="~s")
    fig.update_layout(
        margin=dict(l=44, r=10, t=6, b=22),
        xaxis=dict(type="category", tickangle=0, tickmode="array",
                   tickvals=_tv, ticktext=[_etq(x, gran, corta=True) for x in _tv],
                   tickfont=dict(size=11), categoryorder="array",
                   categoryarray=list(xs)),
        yaxis=dict(showticklabels=True, range=[y0, y1], nticks=4,
                   tickfont=dict(size=10, color=GRIS_TEXTO), **_yfmt),
        showlegend=False, hovermode="closest", bargap=0.1,
    )
    return fig


# ── Productos: «Total del rango» ──────────────────────────────────────


def _filas_proveedores(src, prods, color_map):
    """`{producto: (n, html)}` con los proveedores de cada producto de
    `prods` en `src` (el df NORMALIZADO): el ÚLTIMO precio unitario y su
    fecha, y en el desplegable de cada uno la cantidad y el total. Es la
    lista «Todo el histórico» del despliegue (regla #377). TODO de una vez,
    sin un bucle por grupo (regla #537)."""
    s = src[src["prod"].isin(prods)]
    if s.empty:
        return {}
    g = (s.groupby(["prod", "prov"], as_index=False)
          .agg(total=("valor", "sum"), cant=("cant", "sum")))
    ult = (s.dropna(subset=["fecha"]).sort_values("fecha", kind="stable")
            .groupby(["prod", "prov"], as_index=False)
            .agg(ult_p=("punit", "last"), ult_f=("fecha", "last")))
    g = g.merge(ult, on=["prod", "prov"], how="left")
    _um = s[~s["um"].astype(str).isin(("", "nan", "None"))]
    if len(_um):
        _llave = _um["prod"] + "\x1f" + _um["prov"]
        um = moda_por_grupo(_um.assign(_k=_llave), "_k", "um")
        g["um"] = (g["prod"] + "\x1f" + g["prov"]).map(um).fillna("")
    else:
        g["um"] = ""
    g = g.sort_values(["prod", "total"], ascending=[True, False],
                      kind="stable")
    g["pmin"] = g.groupby("prod")["ult_p"].transform("min")
    g["tope"] = g.groupby("prod")["total"].transform("max")
    out = {}
    for prod, filas in g.groupby("prod", sort=False):
        # Sólo arma TEXTO: los cálculos ya se hicieron arriba (regla #537).
        html_filas = []
        for r in filas.itertuples(index=False):
            es_min = pd.notna(r.ult_p) and r.ult_p == r.pmin
            pu = "—" if pd.isna(r.ult_p) else f"S/ {r.ult_p:,.2f}"
            fec = "—" if pd.isna(r.ult_f) else pd.Timestamp(r.ult_f).strftime("%d/%m/%y")
            peso = (r.total / r.tope * 100) if r.tope else 0.0
            cant = f"{r.cant:,.0f}" + (f" {_esc(_um_corta(r.um))}" if _um_corta(r.um) else "")
            tot = (f"S/ {r.total/1000:.1f}k" if r.total >= 1000
                   else f"S/ {r.total:,.0f}")
            nom = _esc(nombre_propio(r.prov))
            html_filas.append(
                f'<details class="pb-row{" is-min" if es_min else ""}"><summary>'
                f'<span class="peso" style="width:{peso:.1f}%"></span>'
                f'<span class="sw" style="background:{color_map.get(r.prov, GRIS_BORDE)}"></span>'
                f'<span class="name" title="{nom}">{nom}</span>'
                f'<span class="pu{" pu-min" if es_min else ""}">{pu}</span>'
                f'<span class="fec">{fec}</span></summary>'
                f'<div class="mas"><span class="cell"><span class="lab">Cant.</span>'
                f'<span class="val">{cant}</span></span><span class="cell">'
                f'<span class="lab">Total</span><span class="val tot">{tot}</span>'
                f'</span></div></details>')
        out[prod] = (len(html_filas), "".join(html_filas))
    return out


def _filas_90(src, prods, fin):
    """`{producto: (n, html)}`: los proveedores de cada producto en los 90
    días que terminan en `fin`, con el PRECIO PROMEDIO del período (lo
    pagado ÷ lo comprado), del más barato al más caro.

    Reemplaza a «Año actual · último precio» (regla #646): el último precio
    de cada proveedor podía ser de junio para uno y de octubre para otro, y
    el «más barato» salía de comparar fechas distintas — en Mantequilla Sin
    Sal la app marcaba a un proveedor por un precio de junio, cuando en los
    mismos 90 días el más barato era el de la fila."""
    if fin is None or src is None or src.empty:
        return {}
    fin = pd.Timestamp(fin).normalize()
    s = src[src["prod"].isin(prods)]
    f = pd.to_datetime(s["fecha"], errors="coerce")
    s = s[(f > fin - pd.Timedelta(days=90)) & (f <= fin) & (s["cant"] > 0)]
    if s.empty:
        return {}
    g = (s.groupby(["prod", "prov"], as_index=False)
          .agg(v=("valor", "sum"), c=("cant", "sum"), ult=("fecha", "max")))
    g = g[g["c"] > 0]
    g["p"] = g["v"] / g["c"]
    _um = s[~s["um"].astype(str).isin(("", "nan", "None"))]
    um = (moda_por_grupo(_um, "prod", "um") if len(_um)
          else pd.Series(dtype=object))
    g = g.sort_values(["prod", "p"], kind="stable")
    g["pmin"] = g.groupby("prod")["p"].transform("min")
    out = {}
    for prod, filas in g.groupby("prod", sort=False):
        u = _um_corta(um.get(prod, ""))
        h = []
        for r in filas.itertuples(index=False):
            dif = (r.p / r.pmin - 1) * 100 if r.pmin else 0.0
            marca = ('<span class="cp-p90-min">más barato</span>'
                     if abs(dif) < 0.05 else
                     f'<span class="var sube">+{dif:.1f}%</span>')
            h.append(
                f'<div class="cp-p90"><span class="nm" title="{_esc(nombre_propio(r.prov))}">'
                f'{_esc(nombre_propio(r.prov))}</span>'
                f'<span class="r">S/ {r.p:,.2f} {marca}</span>'
                f'<span class="r">{_cant_txt(r.c)}{" " + _esc(u) if u else ""}</span>'
                f'<span class="r f">{pd.Timestamp(r.ult):%d/%m/%y}</span></div>')
        out[prod] = (len(h), "".join(h))
    return out


def _html_productos_total(base, prov, todo, color_map, alto_lista,
                          prod_foco, ppv_prod, fin):
    """La tabla «Total del rango»: los productos comprados a `prov` en el
    rango del Ranking, con su barra de valor, %, cantidad con su unidad,
    precio promedio y «vs. habitual». Clic en un producto despliega sus
    proveedores —los de los últimos 90 días con el precio promedio, y en un
    segundo desplegable los de todo el histórico— y lo pone en la curva."""
    sub = base[base["prov"] == prov]
    agg = (sub.groupby("prod", as_index=False)
              .agg(valor=("valor", "sum"), cant=("cant", "sum"))
              .sort_values("valor", ascending=False, kind="stable"))
    if agg.empty:
        return '<div class="cp-modo-nota">Sin productos para este proveedor.</div>'
    _um_ok = sub[~sub["um"].astype(str).isin(("", "nan", "None"))]
    um = (moda_por_grupo(_um_ok, "prod", "um") if len(_um_ok)
          else pd.Series(dtype=object))
    prods = agg["prod"].tolist()
    p90 = _filas_90(todo, prods, fin)
    p_todo = _filas_proveedores(todo, prods, color_map)
    tot = float(sub["valor"].sum()) or 1.0
    vmax = float(agg["valor"].max()) or 1.0
    filas = []
    for r in agg.itertuples(index=False):
        nom = _esc(r.prod)
        u = _um_corta(um.get(r.prod, ""))
        n9, h9 = p90.get(r.prod, (0, ""))
        nt, ht = p_todo.get(r.prod, (0, ""))
        cuerpo = (f'<div class="cp-pl-sub">Últimos 90 días · {n9} '
                  f'{"proveedor" if n9 == 1 else "proveedores"} · precio promedio del período</div>'
                  + (h9 if n9 else '<div class="cp-pl-vacio">Sin compras en los últimos 90 días.</div>')
                  + f'<details class="cp-pl-todo"><summary>Todo el histórico · '
                  f'{nt} {"proveedor" if nt == 1 else "proveedores"} · último precio</summary>'
                  f'<div class="pb-cards">{ht}</div></details>')
        pp = f"S/ {r.valor / r.cant:,.2f}" if r.cant else "—"
        hab = ppv_prod.get(r.prod)
        if hab is None or pd.isna(hab):
            _hab = '<span class="var">—</span>'
        elif abs(hab) < 0.5:
            _hab = '<span class="var igual" title="Igual al precio habitual (±0,5 %)">=</span>'
        else:
            _hab = f'<span class="var {"sube" if hab > 0 else "baja"}">{_fmt_var(hab)}</span>'
        _foco = r.prod == prod_foco
        filas.append(
            f'<details class="cp-pl-row{" foco" if _foco else ""}"'
            f'{" open" if _foco else ""}><summary data-prod="{nom}">'
            f'<span class="nm" title="{nom}">{nom}</span>'
            f'<span class="vb"><span class="bar" style="width:{r.valor / vmax * 62:.1f}%"></span>'
            f'<span class="v">S/ {r.valor:,.0f}</span></span>'
            f'<span class="n">{r.valor / tot * 100:.0f}%</span>'
            f'<span class="n">{_cant_txt(r.cant)}{" " + _esc(u) if u else ""}</span>'
            f'<span class="n">{pp}</span>{_hab}</summary>'
            f'<div class="cp-pl-provs">{cuerpo}</div></details>')
    return ('<div class="cp-modo-nota">El rango del Ranking · clic en un '
            'producto: sus proveedores y su curva</div>'
            '<div class="cp-pl"><div class="cp-pl-head"><span>Producto</span>'
            '<span class="r">Valor</span><span class="r">%</span>'
            '<span class="r">Cant.</span><span class="r">P. prom.</span>'
            '<span class="r" title="Contra la mediana del precio de los 90 días '
            'anteriores a cada compra">vs. habitual</span><span></span></div>'
            f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
            + "".join(filas) + '</div></div>')


# ── Productos: «Desglose» ──────────────────────────────────────────────


def _spark(vals, medida, parcial, n_band):
    """La TENDENCIA de una fila del Desglose: los últimos (hasta) trece
    puntos de la curva, con una franja sobre los `n_band` que muestran las
    columnas. SVG escalado sin proporción (`preserveAspectRatio=none`) con
    trazo que no se deforma (`vector-effect`).

    Hasta el 2026-10-12 eran cuatro barritas con los MISMOS cuatro números
    de las columnas de al lado; ahora dice cómo venía el producto antes de
    lo que muestra la tabla (regla #646)."""
    n = len(vals)
    nums = [v for v in vals if v is not None and not pd.isna(v)]
    if n < 2 or not nums:
        return '<span class="sp"></span>'
    lo, hi = 0.0, max(nums) or 1.0
    if medida == "precio":
        mn = min(nums)
        pad = (hi - mn) * 0.15 or hi * 0.05 or 1.0
        lo, hi = max(0.0, mn - pad), hi + pad

    def X(i):
        return 2 + i * 96 / (n - 1)

    def Y(v):
        return 28 - (v - lo) / ((hi - lo) or 1.0) * 25

    ult = n - 2 if parcial else n - 1
    d, pen = [], False
    for i in range(ult + 1):
        v = vals[i]
        if v is None or pd.isna(v):
            pen = False
            continue
        d.append(f"{'L' if pen else 'M'}{X(i):.1f},{Y(v):.1f}")
        pen = True
    dash = ""
    if parcial and vals[-1] is not None and vals[-2] is not None \
            and not pd.isna(vals[-1]) and not pd.isna(vals[-2]):
        dash = (f'<path class="d" d="M{X(n - 2):.1f},{Y(vals[-2]):.1f} '
                f'L{X(n - 1):.1f},{Y(vals[-1]):.1f}"/>')
    bx = max(0.0, X(max(0, n - n_band)) - 3)
    return ('<span class="sp"><svg viewBox="0 0 100 30" '
            'preserveAspectRatio="none" aria-hidden="true">'
            f'<rect x="{bx:.1f}" y="0" width="100" height="30"/>'
            f'<path class="l" d="{" ".join(d)}"/>{dash}</svg></span>')


def _html_desglose(sp_prov, hist_prov, evo_x, gran, medida, parc, alto_lista,
                   prod_foco):
    """El DESGLOSE de la curva por producto: una fila por producto, una
    columna por cada uno de los últimos seis puntos de la curva, en la
    medida de la ficha. La fila Total es la curva (en soles).

    Era «Por mes» (regla #579): cuatro períodos, barritas que repetían los
    números y el mes en curso comparado contra el mes entero — ▼75 % en
    verde en casi todas las filas (regla #646). Ahora:

    · OBEDECE al grano de la curva (día, semana, mes, año o documento).
    · El período en curso va rayado y se compara con los mismos días del
      anterior (soles y cantidad) o con el anterior entero (precio: un
      promedio sí se compara con un mes a medias).
    · Entre un día o un documento y otro sólo se compara el precio: una
      factura contra otra, en soles, es ruido.
    · En Precio, la celda se pinta si subió o bajó más de `_UMBRAL_PRECIO`
      contra la columna anterior."""
    if sp_prov is None or not evo_x or "prod" not in sp_prov.columns:
        return ('<div class="cp-modo-nota">La curva no tiene períodos '
                'que desglosar.</div>')
    n_tend = min(13, len(evo_x))
    tend = list(evo_x)[-n_tend:]
    vis = tend[-6:]
    sp = sp_prov[sp_prov["per"].isin(tend)]
    _v = (sp.groupby(["prod", "per"])["valor"].sum().unstack("per")
            .reindex(columns=tend).fillna(0.0))
    _c = (sp.groupby(["prod", "per"])["cant"].sum().unstack("per")
            .reindex(index=_v.index, columns=tend).fillna(0.0))
    _v = _v[_v[vis].sum(axis=1) > 0]
    if _v.empty:
        return ('<div class="cp-modo-nota">Sin compras a este proveedor en '
                'los últimos períodos de la curva.</div>')
    _c = _c.loc[_v.index]
    if medida == "cant":
        m = _c
    elif medida == "precio":
        m = _v / _c.where(_c > 0)
    else:
        m = _v
    m = m.loc[_v[vis].sum(axis=1).sort_values(ascending=False,
                                              kind="stable").index]
    um = pd.Series(dtype=object)
    if medida != "valor" and "um" in sp.columns:
        _u = sp[~sp["um"].astype(str).isin(("", "nan", "None"))]
        if len(_u):
            um = moda_por_grupo(_u, "prod", "um")
    # Los mismos días del período anterior, por producto (sólo a medias).
    ref_v = ref_c = pd.Series(dtype=float)
    if parc is not None and hist_prov is not None and not hist_prov.empty:
        _f = pd.to_datetime(hist_prov["fecha"], errors="coerce")
        _r = hist_prov[(_f >= parc["ref_ini"]) & (_f <= parc["ref_fin"])]
        ref_v = _r.groupby("prod")["valor"].sum()
        ref_c = _r.groupby("prod")["cant"].sum()
    if parc is not None:
        modo = "prev" if medida == "precio" else "ref"
    elif gran in ("Día", "Documento") and medida != "precio":
        modo = "nada"
    else:
        modo = "prev"
    _dec = 2 if medida == "precio" else (1 if medida == "cant" else 0)

    def _celda_txt(v):
        if v is None or pd.isna(v) or v == 0:
            return "—"
        return f"{v:,.{_dec}f}"

    def _delta(serie, prod=None, total=False):
        ult = serie[-1]
        if modo == "nada":
            return '<span class="var">—</span>'
        if modo == "ref":
            if total:
                rv = float(ref_v.sum()) if medida == "valor" else None
            else:
                rv = (ref_v if medida == "valor" else ref_c).get(prod)
            return _fila_var(_var_pct(ult, rv))
        return _fila_var(_var_pct(ult, serie[-2] if len(serie) > 1 else None))

    filas = []
    for prod, fila in m.iterrows():
        serie_t = [None if pd.isna(fila[p]) else float(fila[p]) for p in tend]
        serie = serie_t[-len(vis):]
        llenos = [v or 0 for v in (serie[:-1] if parc else serie)]
        tope = max(llenos + [0]) or 1.0
        celdas = []
        for k, v in enumerate(serie):
            es_parc = parc is not None and k == len(serie) - 1
            estilo = ""
            if not es_parc:
                if medida == "precio":
                    prev = serie_t[len(serie_t) - len(serie) + k - 1] \
                        if len(serie_t) - len(serie) + k - 1 >= 0 else None
                    ch = _var_pct(v, prev)
                    if np.isfinite(ch) and ch > _UMBRAL_PRECIO:
                        estilo = ' sube'
                    elif np.isfinite(ch) and ch < -_UMBRAL_PRECIO:
                        estilo = ' baja'
                elif v:
                    estilo = f'" style="--t:{v / tope * 30:.0f}%'
            celdas.append(
                f'<span class="c{" parc" if es_parc else ""}'
                f'{" z" if not v else ""}{estilo}">{_celda_txt(v)}</span>')
        nom = _esc(prod)
        _u = _esc(_um_corta(um.get(prod, ""))) if medida != "valor" else ""
        filas.append(
            f'<div class="cp-pm-fila{" foco" if prod == prod_foco else ""}"'
            f' data-prod="{nom}">'
            f'<span class="nm" title="{nom}">{nom}'
            f'{f"<small>{_u}</small>" if _u else ""}</span>'
            + _spark(serie_t, medida, parc is not None, len(vis))
            + "".join(celdas) + _delta(serie, prod) + '</div>')
    total = ""
    if medida == "valor":
        tv = (sp.groupby("per")["valor"].sum().reindex(vis).fillna(0.0)
              .tolist())
        total = ('<div class="cp-pm-fila tot"><span class="nm" title="Todos '
                 'sus productos: los mismos números que la curva">Total</span>'
                 '<span class="sp"></span>'
                 + "".join(f'<span class="c{" parc" if parc is not None and k == len(tv) - 1 else ""}">'
                           f'{_celda_txt(v)}</span>' for k, v in enumerate(tv))
                 + _delta(tv, total=True) + '</div>')
    if parc is not None:
        head_ult = parc["rot"]
    else:
        head_ult = _etq(vis[-1], gran)
    head = "".join(f'<span class="r">{_esc(_etq(p, gran))}</span>'
                   for p in vis[:-1]) + f'<span class="r">{_esc(head_ult)}</span>'
    if modo == "ref":
        tit_d = "vs. " + parc["rot_ref"].split(" de la ")[0] \
            if gran == "Semana" else "vs. " + parc["rot_ref"]
    elif modo == "prev":
        tit_d = "vs. anterior"
    else:
        tit_d = "vs. anterior"
    _que = {"valor": "Soles", "cant": "Cantidad", "precio": "Precios"}[medida]
    _gr = {"Día": "día", "Semana": "semana", "Mes": "mes", "Año": "año",
           "Documento": "documento"}[gran]
    nota = f'<b>{_que} por {_gr}</b> · los últimos {len(vis)} puntos de la curva'
    if parc is not None:
        nota += (f' · {_esc(parc["rot"])} se compara con el período anterior entero'
                 if medida == "precio" else
                 f' · {_esc(parc["rot"])} se compara con {_esc(parc["rot_ref"])}')
    if medida == "precio":
        nota += (f' · rojo: subió más de {_UMBRAL_PRECIO:.0f} % contra el '
                 'anterior; verde: bajó')
    if modo == "nada":
        nota += f' · entre un {_gr} y otro sólo se compara el precio'
    nota += ' · clic en una fila: su curva'
    return (f'<div class="cp-modo-nota">{nota}</div>'
            f'<div class="cp-pm" style="--n:{len(vis)}"><div class="cp-pm-head">'
            '<span>Producto</span><span class="sp" title="Los últimos puntos '
            'de la curva; la franja, las columnas de la tabla">Tendencia</span>'
            f'{head}<span class="r">{_esc(tit_d)}</span></div>'
            f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
            + "".join(filas) + '</div>' + total + '</div>')


# ── Documentos ─────────────────────────────────────────────────────────


def _historia_docs(hist_prov):
    """Por documento del proveedor (todo su histórico): los días desde la
    compra anterior y el producto que más subió de precio contra su compra
    anterior al MISMO proveedor.

    Reemplaza a la «Var. %» contra el documento anterior (regla #646): dos
    facturas de pedidos distintos no se comparan en soles — el rojo y el
    verde de esa columna eran ruido con cara de señal."""
    if hist_prov is None or hist_prov.empty:
        return pd.DataFrame(columns=["dias", "sube", "sube_prod", "n_sube"])
    h = hist_prov[hist_prov["docu"].astype(str).str.strip() != ""]
    if h.empty:
        return pd.DataFrame(columns=["dias", "sube", "sube_prod", "n_sube"])
    docs = (h.groupby("docu").agg(fecha=("fecha", "min"))
              .sort_values("fecha", kind="stable"))
    docs["dias"] = pd.to_datetime(docs["fecha"]).diff().dt.days
    lin = (h[h["cant"] > 0].groupby(["docu", "prod"], as_index=False)
             .agg(v=("valor", "sum"), c=("cant", "sum"), f=("fecha", "min")))
    lin = lin[lin["c"] > 0]
    lin["pu"] = lin["v"] / lin["c"]
    lin = lin.sort_values(["prod", "f", "docu"], kind="stable")
    lin["pu_ant"] = lin.groupby("prod")["pu"].shift()
    lin["dpct"] = (lin["pu"] / lin["pu_ant"] - 1) * 100
    sube = lin[lin["dpct"] > 0.5].sort_values("dpct", ascending=False,
                                             kind="stable")
    top = sube.drop_duplicates("docu").set_index("docu")
    docs["sube"] = top["dpct"]
    docs["sube_prod"] = top["prod"]
    docs["n_sube"] = sube.groupby("docu").size()
    return docs


def _html_docs_por_documento(sub, hdocs, alto_lista):
    """«Por documento»: una fila por comprobante del rango del Ranking, que
    se DESPLIEGA en sus productos con cantidad, precio unitario y valor.
    Devuelve `(html, n_documentos, total)`."""
    docs = (sub.groupby("docu", as_index=False)
               .agg(fecha=("fecha", "min"), valor=("valor", "sum"),
                    prods=("prod", "nunique"))
               .sort_values(["fecha", "docu"], ascending=False, kind="stable")
               .reset_index(drop=True))
    docs["leg"] = documento_legible(docs["docu"]).to_numpy()
    lin = (sub.groupby(["docu", "prod"], as_index=False)
              .agg(cant=("cant", "sum"), valor=("valor", "sum"),
                   um=("um", "first"))
              .sort_values(["docu", "valor"], ascending=[True, False],
                           kind="stable"))
    cuerpos = {}
    for docu, ls in lin.groupby("docu", sort=False):
        # Sólo arma TEXTO: lo calculado ya está arriba (regla #537).
        filas = []
        for r in ls.itertuples(index=False):
            um = _esc(_um_corta(r.um))
            pu = (f"S/ {r.valor / r.cant:,.2f}" if r.cant else "—")
            filas.append(
                f'<div class="cp-dl-lin"><span class="nm" title="{_esc(r.prod)}">'
                f'{_esc(r.prod)}</span><span class="r">{_cant_txt(r.cant)}'
                f'{" " + um if um else ""}</span>'
                f'<span class="r">{pu}</span>'
                f'<span class="r">S/ {r.valor:,.0f}</span></div>')
        cuerpos[docu] = "".join(filas)
    filas = []
    for r in docs.itertuples(index=False):
        fec = "—" if pd.isna(r.fecha) else pd.Timestamp(r.fecha).strftime("%d/%m/%y")
        dias = hdocs["dias"].get(r.docu) if len(hdocs) else None
        dias = "—" if dias is None or pd.isna(dias) else f"{int(dias)}"
        s = hdocs["sube"].get(r.docu) if len(hdocs) else None
        if s is None or pd.isna(s):
            subio = '<span class="var">—</span>'
        else:
            _n = hdocs["n_sube"].get(r.docu, 1)
            _mas = f' <small>y {int(_n) - 1} más</small>' if _n and _n > 1 else ""
            _p = _esc(hdocs["sube_prod"].get(r.docu, ""))
            subio = (f'<span class="nm" title="{_p}"><span class="var sube">▲ {s:.1f}%</span> '
                     f'{_p}{_mas}</span>')
        filas.append(
            f'<details class="cp-dl-row"><summary>'
            f'<span>{fec}</span><span class="nm">{_esc(r.leg)}</span>'
            f'<span class="r">{int(r.prods)}</span>'
            f'<span class="r">S/ {r.valor:,.0f}</span>'
            f'<span class="r">{dias}</span>{subio}</summary>'
            f'<div class="cp-dl-det"><div class="cp-dl-lin cab"><span>Producto</span>'
            f'<span class="r">Cant.</span><span class="r">P. unit.</span>'
            f'<span class="r">Valor</span></div>{cuerpos.get(r.docu, "")}</div>'
            f'</details>')
    html_ = ('<div class="cp-modo-nota">El rango del Ranking · Días: desde la '
             'compra anterior · Subió de precio: contra la compra anterior '
             'del mismo producto a este proveedor</div>'
             '<div class="cp-dl cp-dl-doc"><div class="cp-dl-head">'
             '<span>Fecha</span><span>Documento</span>'
             '<span class="r" title="Productos distintos en el documento">Prods</span>'
             '<span class="r">Valor</span><span class="r">Días</span>'
             '<span>Subió de precio</span><span></span></div>'
             f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
             + "".join(filas) + '</div></div>')
    return html_, len(docs), float(docs["valor"].sum())


def _html_docs_por_periodo(sp, per_orden, gran, alto_lista, parc, ref_val):
    """«Por <grano>»: una fila por período de la curva, que se DESPLIEGA en
    sus documentos. El período en curso se compara con los mismos días del
    anterior (`ref_val`). Devuelve `(html, n_documentos, total)`."""
    _sp = sp[sp["docu"].astype(str).str.strip() != ""]
    g = (sp.groupby("per")["valor"].sum().reindex(per_orden).fillna(0.0))
    n_docs = _sp.groupby("per")["docu"].nunique().reindex(per_orden).fillna(0)
    docs = (_sp.groupby(["per", "docu"], as_index=False)
               .agg(fecha=("fecha", "min"), valor=("valor", "sum"),
                    filas=("valor", "size"))
               .sort_values(["per", "fecha", "docu"],
                            ascending=[True, False, False], kind="stable"))
    docs["leg"] = documento_legible(docs["docu"]).to_numpy()
    cuerpos = {}
    for per, ds in docs.groupby("per", sort=False):
        cuerpos[per] = "".join(
            f'<div class="cp-dl-lin per"><span>'
            f'{"—" if pd.isna(r.fecha) else pd.Timestamp(r.fecha).strftime("%d/%m/%y")}'
            f'</span><span class="nm">{_esc(r.leg)}</span>'
            f'<span class="r">{int(r.filas)}</span>'
            f'<span class="r">S/ {r.valor:,.0f}</span></div>'
            for r in ds.itertuples(index=False))
    vals = g.to_numpy(dtype=float)
    filas = []
    cab = ('<div class="cp-dl-lin per cab"><span>Fecha</span>'
           '<span>Documento</span><span class="r">Filas</span>'
           '<span class="r">Total</span></div>')
    for i in range(len(per_orden) - 1, -1, -1):
        p = per_orden[i]
        es_parc = parc is not None and i == len(per_orden) - 1
        var = (_var_pct(vals[i], ref_val) if es_parc
               else _var_pct(vals[i], vals[i - 1] if i else None))
        rot = parc["rot"] if es_parc else _etq(p, gran)
        cuerpo = cuerpos.get(p)
        filas.append(
            f'<details class="cp-dl-row"><summary>'
            f'<span class="nm{" parc" if es_parc else ""}"><b>{_esc(rot)}</b></span>'
            f'<span class="r">{int(n_docs.iloc[i])}</span>'
            f'<span class="r">S/ {vals[i]:,.0f}</span>{_fila_var(var)}</summary>'
            f'<div class="cp-dl-det">'
            + (cab + cuerpo if cuerpo
               else '<div class="cp-pl-vacio">Sin documentos en el período.</div>')
            + '</div></details>')
    nota = "Los períodos de la curva · Var. %: contra el período anterior"
    if parc is not None:
        nota += f' · {_esc(parc["rot"])} contra {_esc(parc["rot_ref"])}'
    html_ = (f'<div class="cp-modo-nota">{nota}</div>'
             '<div class="cp-dl cp-dl-per"><div class="cp-dl-head">'
             '<span>Período</span><span class="r">Docs</span>'
             '<span class="r">Valor</span><span class="r">Var. %</span>'
             '<span></span></div>'
             f'<div class="cp-pl-lista" style="max-height:{alto_lista}px">'
             + "".join(filas) + '</div></div>')
    return html_, int(n_docs.sum()), float(vals.sum())


# ── El clic en un producto (HTML, sin widget) ──────────────────────────


_K_RELEVO_PROD = "cp_prov_prod_relevo"
"""El `st.text_input` oculto por el que un clic en un producto (HTML, sin
widget propio) llega a Python. Ver `_relevo_producto`."""

_SEP_RELEVO = "@@"
"""Separa el producto de un sello de tiempo en el valor del relevo: sin él,
clickear dos veces el MISMO producto escribiría el mismo texto y el
`on_change` no correría la segunda vez."""


def _relevo_producto():
    """`on_change` del relevo: el producto clickeado pasa a ser el foco de
    la curva, y clickear el que ya estaba en foco lo suelta."""
    raw = st.session_state.get(_K_RELEVO_PROD) or ""
    prod = raw.rsplit(_SEP_RELEVO, 1)[0]
    if not prod:
        return
    actual = st.session_state.get("compras_prov_prodfocus")
    st.session_state["compras_prov_prodfocus"] = (None if prod == actual
                                                  else prod)


def _soltar_producto():
    st.session_state["compras_prov_prodfocus"] = None


_JS_CLIC_PRODUCTO = f"""<script>
(function () {{
  // Un clic en una fila de producto (de «Total del rango» o del
  // «Desglose») escribe su nombre en el relevo y lo confirma con un Enter
  // de verdad (regla #217). Escucha en el DOCUMENTO, delegado: la tabla se
  // rehace en cada corrida y un listener por fila se perdería.
  var w = window.parent, doc = w.document;
  if (w.__cpProdClic) doc.removeEventListener('click', w.__cpProdClic, true);
  w.__cpProdClic = function (ev) {{
    var t = ev.target && ev.target.closest && ev.target.closest('[data-prod]');
    if (!t || !t.closest('.st-key-compras_prov_card_ficha')) return;
    var relevo = doc.querySelector('.st-key-{_K_RELEVO_PROD} input');
    if (!relevo) return;
    var setter = w.Object.getOwnPropertyDescriptor(
      w.HTMLInputElement.prototype, 'value').set;
    relevo.focus({{preventScroll: true}});
    setter.call(relevo, t.getAttribute('data-prod') + '{_SEP_RELEVO}' + w.Date.now());
    relevo.dispatchEvent(new w.Event('input', {{bubbles: true}}));
    var o = {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
             bubbles: true, cancelable: true}};
    relevo.dispatchEvent(new w.KeyboardEvent('keydown', o));
    relevo.dispatchEvent(new w.KeyboardEvent('keyup', o));
  }};
  doc.addEventListener('click', w.__cpProdClic, true);
}})();
</script>"""


# ── El drill ───────────────────────────────────────────────────────────


def _recortar_alineado(df, col_fecha, opcion, gran):
    """`periodo.recortar`, pero con el inicio llevado al PRIMER día de su
    período: «12 meses» al 11 de octubre arrancaba el 12 de octubre del año
    anterior, y el primer punto de la curva era un mes de 20 días (regla
    #646)."""
    if df is None or df.empty or not col_fecha or opcion == periodo.HEREDA:
        return df
    f = pd.to_datetime(df[col_fecha], errors="coerce").dt.normalize()
    v = periodo.ventana(opcion, f.max(), minimo=f.min())
    if v is None:
        return df
    ini = inicio_de_periodo(v[0], gran)
    return df[(f >= ini) & (f <= v[1])]


@st.fragment
def _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                             col_punit, col_um, col_fecha, col_docu=None,
                             d_full=None):
    """Dashboard de Proveedor: el Ranking y la ficha del proveedor elegido.
    Ver el docstring del módulo y `arquitectura.md` regla #646."""
    # ── Escalada a rerun COMPLETO tras un atajo de fecha ───────────────────
    # El filtro que consume el rango de la cabecera vive FUERA de este
    # fragment: sin escalar, el estado cambia y la pantalla no. Va ANTES de
    # dibujar nada (arquitectura.md #180), y con `preservar_widgets` porque
    # el rerun aborta acá (#373).
    if st.session_state.pop("_cp_rank_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")
    if not (col_prov and col_valor):
        st.info("Faltan columnas (Proveedor, Valor) para este gráfico.")
        return

    _todos_provs_temp = (d.groupby(col_prov)[col_valor].sum()
                          .sort_values(ascending=False).index.tolist())
    _otros_mask_temp = ~d[col_prov].astype(str).isin(_todos_provs_temp[:20])
    if _otros_mask_temp.any():
        _todos_provs_temp = _todos_provs_temp + ["Otros"]
    prov_multisel, _pop_proveedores = filtro_proveedores(
        "cp_prov", _todos_provs_temp)

    gran = st.session_state.get("compras_prov_gran") or "Mes"
    if gran not in _GRANOS:
        gran = "Mes"
    medida = st.session_state.get("cp_evo_medida") or "valor"
    if medida not in _MEDIDAS:
        medida = "valor"
    cols = (col_prov, col_prod, col_cant, col_valor, col_punit, col_um,
            col_fecha, col_docu)

    base = base_normalizada(d, *cols[:7], col_docu)
    if base.empty or base["valor"].sum() == 0:
        # SIN FILAS SE VACÍA EL CONTENIDO, NO LA VISTA (regla #354): la
        # tarjeta se dibuja con su selector de fecha, que es la salida.
        st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)
        with st.container(border=True, key="compras_prov_card_vacio"):
            selector_fecha_tarjeta(
                "cp_rank", "_cp_rank_atajo_pendiente",
                titulo_html='<div class="cp-rank-tit">Ranking de '
                            'proveedores</div>',
                categoria=CATEGORIA_SEC["compras_sec_proveedor"])
            st.info("Sin compras en el rango seleccionado. Ampliá el rango "
                    "desde la fecha de la cabecera, o soltá el filtro de "
                    "Familia. «Vs año pasado» y «Volatilidad», más abajo, "
                    "tienen ventana propia y siguen mostrando datos.")
        return

    base = _con_clave(agregar_periodo(base, gran))
    top_provs = [p for p in prov_multisel if p in set(base["prov"].unique())]
    if not top_provs:
        top_provs = (base.groupby("prov")["valor"].sum()
                         .sort_values(ascending=False).index.tolist())
    periodos = periodos_ordenados(base)

    prov_focus = st.session_state.get("compras_prov_focus")
    if prov_focus not in set(base["prov"].unique()):
        prov_focus = None

    # ── Ventana de períodos (sólo con la ventana «Rango») ─────────────────
    _otros_mask = ~base["prov"].isin(top_provs)
    _hay_otros = _otros_mask.any()
    _otros_sel = "Otros" in prov_multisel
    _n_per = max(1, len(periodos))
    _ventana_auto = max(4, min(12, int(1200 / (16 * 2))))
    _ops_win = ([None] + [o for o in (1, 2, 3, 6, 12, 24) if o < _n_per]
                + [_n_per])
    if st.session_state.get("cp_prov_win_size") not in _ops_win:
        st.session_state["cp_prov_win_size"] = None
    _win_size_sel = st.session_state.get("cp_prov_win_size")
    _ventana = (_ventana_auto if _win_size_sel is None
                else min(int(_win_size_sel), _n_per))
    _ventana = max(1, min(_ventana, _n_per))
    _ini_max = max(0, _n_per - _ventana)
    _win_sig = f"{gran}|{_n_per}|{_ventana}"
    if st.session_state.get("cp_prov_win_sig") != _win_sig:
        st.session_state["cp_prov_win_sig"] = _win_sig
        st.session_state["cp_prov_win_ini"] = _ini_max
    _win_ini = min(max(0, st.session_state.get("cp_prov_win_ini", _ini_max)),
                   _ini_max)
    st.session_state["cp_prov_win_ini"] = _win_ini
    _sl = slice(_win_ini, _win_ini + _ventana)

    # ── Datos del Ranking ─────────────────────────────────────────────────
    _tot_all = float(base["valor"].sum()) or 1.0
    _tot_por_prov = (base[base["prov"].isin(top_provs)]
                     .groupby("prov")["valor"].sum()
                     .reindex(top_provs, fill_value=0))
    _rk_nombres = list(_tot_por_prov.index)
    _rk_valores = [float(v) for v in _tot_por_prov.values]
    _rk_colores = [PALETA_CALLAI[i % len(PALETA_CALLAI)]
                   for i in range(len(_rk_nombres))]
    if _hay_otros and _otros_sel:
        _rk_nombres.append("Otros")
        _rk_valores.append(float(base[_otros_mask]["valor"].sum()))
        _rk_colores.append(GRIS_BORDE)
    _rk_pct = [v / _tot_all * 100 for v in _rk_valores]
    _rango = rango_tarjeta(CATEGORIA_SEC["compras_sec_proveedor"])
    if _rango is None and base["fecha"].notna().any():
        _rango = (base["fecha"].min(), base["fecha"].max())
    _ant = _contra_anterior(d_full, col_prov, col_valor, col_fecha, _rango)
    _rk_est = [(_estado(n, v, _ant) if n != "Otros" else (np.inf, "", ""))
               for n, v in zip(_rk_nombres, _rk_valores)]
    _acum = np.cumsum(sorted(_rk_valores, reverse=True)) / _tot_all * 100
    _n80 = int((_acum < 80).sum() + 1) if len(_acum) else 0

    # El SUJETO de la ficha: el foco, o sin foco la primera fila del
    # Ranking (el de mayor valor). Lo lee TODA la ficha — antes la
    # Evolución elegía el suyo y podía hablar de otro proveedor.
    _defecto = (base.groupby("prov")["valor"].sum().idxmax()
                if not base.empty else None)

    st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)

    with st.container(key="compras_prov_marco"):
        _c_rank, _c_ficha = st.columns(COLUMNAS_DRILL_FICHA, gap=GAP_DRILL)

        # ═══ RANKING ════════════════════════════════════════════════════
        with _c_rank:
            with st.container(border=True, key="compras_prov_card_ranking"):
                selector_fecha_tarjeta(
                    "cp_rank", "_cp_rank_atajo_pendiente",
                    titulo_html='<div class="cp-rank-tit">Ranking de '
                                'proveedores</div>',
                    extra=_pop_proveedores,
                    categoria=CATEGORIA_SEC["compras_sec_proveedor"])
                _rk_max = float(max(_rk_valores)) if _rk_valores else 1.0
                _rk_df = pd.DataFrame({
                    # Lo que se VE es el nombre en capitalización de nombre
                    # propio (`nombre_propio`); la clave es `_prov_raw`.
                    "Proveedor": [nombre_propio(n) for n in _rk_nombres],
                    "Valor": _rk_valores,
                    "_var": [None if not np.isfinite(e[0]) else round(e[0], 2)
                             for e in _rk_est],
                    "%": _rk_pct,
                    "_estado": [e[1] for e in _rk_est],
                    "_ayuda": [e[2] for e in _rk_est],
                    "_barra": [v / _rk_max * 100 for v in _rk_valores],
                    "_prov_raw": _rk_nombres,
                })
                _prev_tot = (float(_ant["prev"].reindex(
                    [n for n in _rk_nombres if n != "Otros"]).fillna(0).sum())
                    if _ant is not None else 0.0)
                _var_tot = _var_pct(sum(_rk_valores), _prev_tot)
                _rk_fila_total = {
                    "Proveedor": f"TOTAL · {len(_rk_nombres)}",
                    "Valor": round(sum(_rk_valores), 2),
                    "_var": (round(_var_tot, 2) if np.isfinite(_var_tot)
                             else None),
                    "%": round(sum(_rk_pct), 2),
                }
                # La barra es el FONDO de la celda (un `linear-gradient`
                # cortado en el % del valor, hasta el 62 %): lavanda, y en
                # ACENTO la del proveedor de la ficha — el mismo morado de
                # su curva. Los datos van por `context` (regla #226).
                _js_barra = JsCode(
                    "function(p){"
                    " if (p.node.rowPinned) return {'display':'flex',"
                    " 'alignItems':'center','justifyContent':'flex-end',"
                    " 'fontWeight':'700'};"
                    " var sel = p.node.isSelected() || (p.context &&"
                    " p.data._prov_raw === p.context.defecto &&"
                    " p.api.getSelectedNodes().length === 0);"
                    " var w = Math.max(0, Math.min(100, p.data._barra||0)) * 0.62;"
                    f" var c = sel ? '{ACENTO}' : '{LAVANDA_BORDE}';"
                    " return {'background': 'linear-gradient(90deg, ' + c +"
                    " ' 0 ' + w + '%, transparent ' + w + '% 100%)',"
                    " 'display':'flex','alignItems':'center',"
                    " 'justifyContent':'flex-end',"
                    f" 'color':'{TEXTO_PRINCIPAL}'"
                    "};}")
                _js_fila_total = JsCode(
                    "function(p){ if(p.node.rowPinned){ return {"
                    f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
                    f"'color':'{ACENTO_TEXTO_OSCURO}'"
                    "}; } }")
                _js_soles = JsCode(
                    "function(p){ return p.value==null ? '' :"
                    " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
                _js_pct = JsCode(
                    "function(p){ return p.value==null ? '' :"
                    " Math.round(p.value) + '%'; }")
                _js_var = JsCode(
                    "function(p){ if (p.data && p.data._estado) return p.data._estado;"
                    " if (p.value==null) return '—'; var a = Math.abs(p.value);"
                    " if (a < 0.05) return '0.0%';"
                    " return (p.value > 0 ? '▲ ' : '▼ ') + a.toFixed(1) + '%'; }")
                _reglas_var = {
                    "cp-rk-sube": JsCode(
                        "function(p){ return !!(p.data && !p.data._estado &&"
                        " p.value != null && p.value >= 0.5); }"),
                    "cp-rk-baja": JsCode(
                        "function(p){ return !!(p.data && !p.data._estado &&"
                        " p.value != null && p.value <= -0.5); }"),
                    "cp-rk-nuevo": JsCode(
                        "function(p){ return !!(p.data && p.data._estado === 'nuevo'); }"),
                    "cp-rk-vuelve": JsCode(
                        "function(p){ return !!(p.data && p.data._estado === 'vuelve'); }"),
                }
                # Fila de la ficha sin clic: la primera, marcada como si
                # estuviera elegida. `rowClassRules` y no `getRowClass`: la
                # segunda agrega clases y no las quita (regla #441).
                _reglas_fila = {
                    "cp-rank-defecto": JsCode(
                        "function(p){ return !!(p.data && p.context &&"
                        " p.data._prov_raw === p.context.defecto &&"
                        " p.api.getSelectedNodes().length === 0); }"),
                }
                # Clic en la fila = TOGGLE, y después `redrawRows` para que
                # la barra y la marca de la fila por defecto se recalculen.
                _js_toggle = JsCode(
                    "function(e){ if (e.node.rowPinned) return;"
                    " e.node.setSelected(!e.node.isSelected(), true);"
                    " e.api.redrawRows(); }")
                _filas_rank = min(16, max(1, len(_rk_nombres)))
                _alto_rank = alturas.por_filas(
                    _filas_rank, px_fila=ALTO_FILA_RANK,
                    extra=CROMO_GRID_RANK + ALTO_FILA_RANK, minimo=0)
                _resp_rank = AgGrid(
                    _rk_df,
                    gridOptions={
                        "columnDefs": [
                            {"field": "Proveedor", "flex": 2.3,
                             "tooltipField": "Proveedor"},
                            {"field": "Valor", "flex": 2,
                             "type": "numericColumn",
                             "cellStyle": _js_barra,
                             "valueFormatter": _js_soles},
                            {"field": "_var", "headerName": "Δ", "width": 76,
                             "type": "numericColumn",
                             "valueFormatter": _js_var,
                             "cellClassRules": _reglas_var,
                             "tooltipField": "_ayuda",
                             "headerTooltip": "Contra el período anterior "
                                              "de igual largo"},
                            {"field": "%", "width": 54,
                             "type": "numericColumn",
                             "valueFormatter": _js_pct},
                            {"field": "_estado", "hide": True},
                            {"field": "_ayuda", "hide": True},
                            {"field": "_barra", "hide": True},
                            {"field": "_prov_raw", "hide": True},
                        ],
                        "context": {"defecto": _defecto or ""},
                        "rowClassRules": _reglas_fila,
                        "rowSelection": {"mode": "singleRow",
                                         "checkboxes": False,
                                         "enableClickSelection": False},
                        "onRowClicked": _js_toggle,
                        "rowHeight": ALTO_FILA_RANK,
                        "headerHeight": ALTO_HEADER_RANK,
                        "suppressCellFocus": True,
                        "suppressMovableColumns": True,
                        "tooltipShowDelay": 300,
                        "pinnedBottomRowData": [_rk_fila_total],
                        "getRowStyle": _js_fila_total,
                    },
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    custom_css=CSS_RANKING_PROV,
                    height=_alto_rank,
                    update_on=["selectionChanged"],
                    key="compras_prov_rank_grid",
                )
                st.markdown(
                    f'<div class="cp-rank-pie">{_n80} '
                    f'{"proveedor hace" if _n80 == 1 else "proveedores hacen"} '
                    'el 80 % de lo comprado · Δ: contra el período anterior '
                    'de igual largo</div>', unsafe_allow_html=True)
                # El foco sale de la selección VIGENTE del grid. «Otros» no
                # es un proveedor: no abre ficha.
                _sel_rank = getattr(_resp_rank, "selected_rows", None)
                if _sel_rank is not None and len(_sel_rank):
                    _fila = (_sel_rank.iloc[0] if hasattr(_sel_rank, "iloc")
                             else _sel_rank[0])
                    _clicked = str(_fila["_prov_raw"])
                else:
                    _clicked = None
                if _clicked == "Otros":
                    _clicked = prov_focus
                if _clicked != prov_focus:
                    prov_focus = _clicked
                    st.session_state["compras_prov_focus"] = prov_focus
                    st.session_state["compras_prov_prodfocus"] = None

        _prov = prov_focus or _defecto
        _prod = st.session_state.get("compras_prov_prodfocus")
        if _prod is not None and (
                _prov is None
                or _prod not in set(base.loc[base["prov"] == _prov, "prod"])):
            _prod = None

        # ═══ FICHA ══════════════════════════════════════════════════════
        with _c_ficha:
            with st.container(border=True, key="compras_prov_card_ficha"):
                _ficha(base, d_full, cols, _prov, _prod, gran, medida,
                       _rango, _ant, _tot_all, periodos, _sl, _ventana_auto,
                       _ops_win, _n_per, _win_ini, _ini_max, _ventana,
                       {p: PALETA_CALLAI[i % len(PALETA_CALLAI)]
                        for i, p in enumerate(top_provs)})


def _ficha(base, d_full, cols, prov, prod_foco, gran, medida, rango, ant,
           tot_all, periodos, sl, ventana_auto, ops_win, n_per, win_ini,
           ini_max, ventana, color_map):
    """La ficha del proveedor `prov`: cabecera, cifras del rango, curva y
    las pestañas Productos y Documentos. Ver el docstring del módulo."""
    (col_prov, col_prod, col_cant, col_valor, col_punit, col_um, col_fecha,
     col_docu) = cols
    if prov is None:
        st.caption("Sin proveedores en el rango.")
        return
    sub = base[base["prov"] == prov]
    # El histórico entero del proveedor, normalizado: «desde», los días
    # entre documentos, lo que subió de precio y los mismos días del
    # período anterior.
    if d_full is not None:
        hist = base_normalizada(d_full[d_full[col_prov].astype(str) == prov],
                                *cols)
    else:
        hist = base[base["prov"] == prov]
    _desde = (hist["fecha"].min() if hist["fecha"].notna().any() else None)
    _ultimo = None
    if d_full is not None and col_fecha:
        _ultimo = pd.to_datetime(d_full[col_fecha], errors="coerce").max()
    if _ultimo is None or pd.isna(_ultimo):
        _ultimo = base["fecha"].max()

    # ── Cabecera: nombre, «desde» y la ventana de la curva ────────────────
    _op_evo = st.session_state.get("cp_evo_periodo", "12m")
    with st.container(key="cp_ficha_cab"):
        st.markdown(
            f'<div class="cp-fi-nom" title="{_esc(nombre_propio(prov))}">'
            f'{_esc(_compras_truncar(nombre_propio(prov), 34))}'
            + (f'<span>desde {_mes_anio(_desde)}</span>' if _desde is not None
               else "") + '</div>', unsafe_allow_html=True)
        with st.container(key="cp_evo_ctrl"):
            _op_evo = periodo.selector("cp_evo_periodo", widget="lista")
            # El tamaño de la ventana y las flechas sólo hacen algo con la
            # ventana «Rango»: con las otras se esconden (antes quedaban
            # apagadas, a la vista, sin decir por qué).
            if _op_evo == periodo.HEREDA and gran != "Documento":
                def _fmt_win(_o):
                    if _o is None:
                        return f"Auto {ventana_auto}"
                    if _o == n_per:
                        return f"Todo {n_per}" if n_per < 100 else "Todo"
                    return str(_o)

                def _win_mover(_delta):
                    st.session_state["cp_prov_win_ini"] = min(
                        max(0, win_ini + _delta), ini_max)

                with st.container(key="win_size"):
                    st.selectbox("Períodos visibles", ops_win, index=0,
                                 key="cp_prov_win_size", format_func=_fmt_win,
                                 label_visibility="collapsed")
                with st.container(key="win_nav"):
                    st.button("‹", key="cp_win_prev", disabled=win_ini <= 0,
                              help="Períodos anteriores", on_click=_win_mover,
                              args=(-ventana,))
                    st.button("›", key="cp_win_next",
                              disabled=win_ini >= ini_max,
                              help="Períodos siguientes", on_click=_win_mover,
                              args=(ventana,))
    _evo_hist = _op_evo != periodo.HEREDA

    # ── Las cifras del rango del Ranking ─────────────────────────────────
    _compra = float(sub["valor"].sum())
    _var, _est, _ayuda = _estado(prov, _compra, ant)
    _docs = int(sub.loc[sub["docu"].astype(str).str.strip() != "",
                        "docu"].nunique())
    _ppv_tot, _ppv_prod = _ppv(d_full, base, cols, prov, rango)
    st.markdown(_html_kpis(_compra, _var, _est, _ayuda,
                           _compra / tot_all * 100, _docs, _ppv_tot, ant),
                unsafe_allow_html=True)

    # ── La fuente de la curva ────────────────────────────────────────────
    src = base
    if _evo_hist and d_full is not None and col_fecha:
        _d_evo = _recortar_alineado(d_full, col_fecha, _op_evo, gran)
        _bf = base_normalizada(_d_evo, *cols)
        if not _bf.empty:
            src = _con_clave(agregar_periodo(_bf, gran))
        else:
            _evo_hist = False
    m_prov = src["prov"] == prov
    m_curva = m_prov & (src["prod"] == prod_foco) if prod_foco else m_prov
    if gran == "Documento":
        _per = periodos_ordenados(src[m_prov])
    else:
        _per = periodos_ordenados(src)
    if not _evo_hist and gran != "Documento":
        _per = list(_per)[sl] if len(periodos) == len(_per) else _per
    evo_x = list(_per)
    _med_curva = medida if prod_foco else "valor"
    _g = (src[m_curva].groupby("per").agg(valor=("valor", "sum"),
                                          cant=("cant", "sum"))
          .reindex(evo_x).fillna(0.0))
    if _med_curva == "cant":
        _ys = _g["cant"]
    elif _med_curva == "precio":
        _ys = _g["valor"] / _g["cant"].where(_g["cant"] > 0)
    else:
        _ys = _g["valor"]
    _um = ""
    if prod_foco:
        _u = src.loc[m_curva, "um"].astype(str)
        _u = _u[~_u.isin(("", "nan", "None"))]
        _um = _um_corta(_u.mode().iat[0]) if len(_u) else ""

    # ¿El último punto está a medias? Sólo si es el período del último día
    # con datos (con «Rango» puede no serlo).
    parc = tramo_parcial(gran, _ultimo)
    if parc is not None and evo_x:
        _k_ult = _con_clave(agregar_periodo(
            pd.DataFrame({"fecha": [_ultimo], "docu": [""]}), gran))
        if _k_ult.empty or _k_ult["per"].iat[0] != evo_x[-1]:
            parc = None
    _ref = None
    _hm = hist["prod"] == prod_foco if prod_foco else pd.Series(True, index=hist.index)
    if parc is not None:
        _hf = pd.to_datetime(hist["fecha"], errors="coerce")
        _r = hist[_hm & (_hf >= parc["ref_ini"]) & (_hf <= parc["ref_fin"])]
        if _med_curva == "cant":
            _ref = float(_r["cant"].sum())
        elif _med_curva == "precio":
            _ref = None
        else:
            _ref = float(_r["valor"].sum())

    # El hover: el período, y el % del total, la variación y los documentos.
    _tot_per = src.groupby("per")["valor"].sum().reindex(evo_x).fillna(0.0)
    _doc_per = (src[m_curva & (src["docu"].astype(str).str.strip() != "")]
                .groupby("per")["docu"].nunique().reindex(evo_x).fillna(0))
    _vals = _ys.tolist()
    custom = []
    for i, k in enumerate(evo_x):
        _rot = (parc["rot"] if parc is not None and i == len(evo_x) - 1
                else _etq(k, gran))
        _cmp = (_var_pct(_vals[i], _ref) if parc is not None
                and i == len(evo_x) - 1 and _med_curva != "precio"
                else _var_pct(_vals[i], _vals[i - 1] if i else None))
        _extra = f"<br>vs. anterior: {_fmt_var(_cmp)}"
        if _med_curva == "valor" and gran != "Documento":
            _pct = _g["valor"].iat[i] / (_tot_per.iat[i] or 1) * 100
            _extra += f"<br>{_pct:.1f}% del total"
        _extra += f"<br>{int(_doc_per.iat[i])} documentos"
        custom.append([_esc(_rot), _extra])

    # ── Controles de la curva: medida y grano ────────────────────────────
    with st.container(key="cp_ficha_ctrl"):
        _sujeto = (f'<b>{_esc(_compras_truncar(str(prod_foco), 30))}</b>'
                   f' · {_esc(_compras_truncar(nombre_propio(prov), 22))}'
                   if prod_foco else
                   f'<b>{_esc(_compras_truncar(nombre_propio(prov), 30))}</b>'
                   ' · todo lo comprado')
        st.markdown(f'<div class="cp-fi-curva">Curva de {_sujeto}</div>',
                    unsafe_allow_html=True)
        with st.container(key="cp_fi_medida"):
            st.segmented_control(
                "Medida", list(_MEDIDAS), key="cp_evo_medida",
                default=None if "cp_evo_medida" in st.session_state else "valor",
                format_func=_MEDIDAS.get, label_visibility="collapsed")
        with st.container(key="cp_fi_grano"):
            st.segmented_control(
                "Grano", list(_GRANOS), key="compras_prov_gran",
                default=None if "compras_prov_gran" in st.session_state else "Mes",
                format_func=lambda g: "Doc." if g == "Documento" else g,
                label_visibility="collapsed")

    if evo_x:
        fig = _fig_curva(evo_x, _vals, gran, _med_curva, _um,
                         parc is not None, _ref, custom, ACENTO)
        st.plotly_chart(fig, width="stretch",
                        key=f"cp_evo_{gran}_{zlib.crc32(f'{prov}|{prod_foco}'.encode()):08x}",
                        config={"displayModeBar": False})
    else:
        st.caption("Sin compras de este proveedor en la ventana.")

    # La leyenda de la curva, y «volver» con un producto en foco.
    with st.container(key="cp_ficha_ley"):
        _ley = []
        if parc is not None and _vals:
            _ley.append(f'<span><i class="hueco"></i>{_esc(parc["rot"])} en curso: '
                        f'{_esc(_fmt_medida(_vals[-1], _med_curva, _um))}</span>')
            if _med_curva == "precio":
                _ley.append(f'<span>contra el período anterior entero: '
                            f'{_fila_var(_var_pct(_vals[-1], _vals[-2] if len(_vals) > 1 else None))}</span>')
            else:
                _ley.append(f'<span><i class="raya"></i>{_esc(parc["rot_ref"])}: '
                            f'{_esc(_fmt_medida(_ref, _med_curva, _um))} '
                            f'{_fila_var(_var_pct(_vals[-1], _ref))}</span>')
        if medida != "valor" and not prod_foco:
            _ley.append('<span>en soles: la cantidad y el precio van por '
                        'producto (clic en uno)</span>')
        if _evo_hist:
            _ley.append(f'<span>{_esc(periodo.etiqueta(_op_evo))}</span>')
        st.markdown('<div class="cp-fi-ley">' + "".join(_ley) + '</div>',
                    unsafe_allow_html=True)
        if prod_foco:
            st.button("✕ volver a todo el proveedor", key="cp_prov_volver",
                      type="tertiary", on_click=_soltar_producto)

    # ── Pestañas ─────────────────────────────────────────────────────────
    _n_prod = int(sub["prod"].nunique())
    for _k, _ops in (("cp_prov_tab", ("prod", "doc")),
                     ("cp_prov_prods_modo", ("tot", "per")),
                     ("cp_prov_docs_modo", ("doc", "per"))):
        if st.session_state.get(_k) not in (None,) + _ops:
            del st.session_state[_k]
    with st.container(key="cp_ficha_tabs"):
        with st.container(key="cp_modo_tab"):
            _tab = st.pills(
                "Ver", ["prod", "doc"], default="prod", key="cp_prov_tab",
                format_func=lambda o: (f"Productos · {_n_prod}" if o == "prod"
                                       else f"Documentos · {_docs}"),
                label_visibility="collapsed") or "prod"
        if _tab == "prod":
            with st.container(key="cp_modo_prods"):
                _modo = st.pills(
                    "Vista de productos", ["tot", "per"], default="tot",
                    key="cp_prov_prods_modo",
                    format_func=lambda o: "Total del rango" if o == "tot" else "Desglose",
                    label_visibility="collapsed") or "tot"
        else:
            if gran == "Documento":
                _modo = "doc"
            else:
                with st.container(key="cp_modo_docs"):
                    _modo = st.pills(
                        "Agrupar documentos", ["doc", "per"], default="doc",
                        key="cp_prov_docs_modo",
                        format_func=lambda o: ("Por documento" if o == "doc"
                                               else _GRAN_POR.get(gran, "Por período")),
                        label_visibility="collapsed") or "doc"

    # «Total del rango» lleva sólo su cabecera; el Desglose y los
    # Documentos, además, la fila de total: una fila menos a la vista.
    _alto_lista = (_FILAS_LISTA - (0 if _tab == "prod" and _modo == "tot" else 1)
                   ) * _ALTO_FILA
    st.text_input("Producto en foco", key=_K_RELEVO_PROD,
                  label_visibility="collapsed", on_change=_relevo_producto)
    if _tab == "prod" and _modo == "per":
        _html = _html_desglose(src[m_prov], hist, evo_x, gran, medida, parc,
                               _alto_lista, prod_foco)
    elif _tab == "prod":
        _todo = hist
        if d_full is not None and col_prod:
            _prods = sub["prod"].unique()
            _todo = base_normalizada(
                d_full[d_full[col_prod].astype(str).isin(_prods)], *cols)
        _fin = rango[1] if rango is not None else base["fecha"].max()
        _html = _html_productos_total(base, prov, _todo, color_map,
                                      _alto_lista, prod_foco, _ppv_prod, _fin)
    elif _modo == "per":
        _ref_docs = None
        if parc is not None:
            _hf = pd.to_datetime(hist["fecha"], errors="coerce")
            _ref_docs = float(hist.loc[(_hf >= parc["ref_ini"])
                                       & (_hf <= parc["ref_fin"]), "valor"].sum())
        _html, _nd, _td = _html_docs_por_periodo(
            src[m_prov], evo_x, gran, _alto_lista, parc, _ref_docs)
        _html += (f'<div class="cp-docs-total"><span>Total · {_nd:,} '
                  f'{"documento" if _nd == 1 else "documentos"}</span>'
                  f'<span>S/ {_td:,.0f}</span></div>')
    else:
        _sub_d = sub[sub["docu"].astype(str).str.strip() != ""]
        if _sub_d.empty:
            _html = ('<div class="cp-modo-nota">Sin números de documento para '
                     'este proveedor en el rango.</div>')
        else:
            _html, _nd, _td = _html_docs_por_documento(
                _sub_d, _historia_docs(hist), _alto_lista)
            _html += (f'<div class="cp-docs-total"><span>Total · {_nd:,} '
                      f'{"documento" if _nd == 1 else "documentos"} · ticket '
                      f'{_soles(_td / _nd) if _nd else "—"}</span>'
                      f'<span>S/ {_td:,.0f}</span></div>')
    # REMONTAJE POR CONTENIDO (regla #377): un `<details>` guarda
    # abierto/cerrado en el DOM y ese nodo sobrevive al rerun.
    _k = zlib.crc32(_html.encode("utf-8"))
    with st.container(key=f"cp_fi_tabla_{_k:08x}"):
        st.markdown(_html, unsafe_allow_html=True)
    inyectar_html(_JS_CLIC_PRODUCTO)
