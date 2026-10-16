"""graficos.compras.producto - drill de Producto.

Desde el 2026-10-13 (regla #653) tiene la forma de Proveedor (#646): UNA
fila de dos tarjetas, la lista a la izquierda y la ficha del producto
elegido a la derecha — elegida sobre una maqueta clicable con datos reales.

    [ Ranking de productos   ][ Ficha del producto elegido                ]
    [ fecha · buscador · Ver ][  nombre · ventana · grano                 ]
    [ familias, subfamilias  ][  cifras del rango                         ]
    [ (a toda la altura)     ][  curva: cantidad en barras, precio línea  ]
    [                        ][  Proveedores | Compras | Períodos         ]

Hasta ese día era [Evolución | Familia + Subfamilia + Ranking] (reglas
#381, #480, #581 a #583), con el orden al revés que Proveedor —la sección de
arriba— y cuatro AgGrid (1,28 MB y 1-2 s de navegador cada una, regla
#540). Lo que se conserva, con su sitio nuevo:

- Familia y Subfamilia → botones encima del ranking, y «Ver por: Producto |
  Subfamilia | Familia» cambia la lista a los totales de cada grupo, con su
  monto, %, Δ y «vs. hab.»; un clic baja a sus productos.
- El ranking → el mismo, con % sobre el ámbito, Δ contra el período
  anterior de igual largo («nuevo» / «vuelve») y «vs. hab.». Se van Inicio,
  Fin y Var (primera contra última compra): 91 de 313 productos del rango
  tenían una sola compra y la Var daba 0 sin importar nada, y la de cinco
  vinos era un error de carga.
- La Evolución → la CURVA de la ficha: ventana (abre en 3 meses, a pedido
  del 2026-09-12), grano Semana / Mes / Año / Documento, clic en una barra.
- «Resumen Total» → Períodos; «Resumen del Período» → Proveedores (con
  «La curva» o la barra elegida como ámbito); «Detalle» → Compras.

Dos reglas que la maqueta midió y la vista cumple en todos lados:

- UN SOLO PRECIO, el PONDERADO (soles ÷ cantidad; el costo promedio
  ponderado de la NIC 2, §25). La barra de antes promediaba las facturas
  sin pesar: lomo fino de setiembre decía S/ 67,17 arriba y S/ 70,80 en la
  tabla de abajo. Pasaba en 728 de 4.007 producto-mes.
- LAS COMPRAS MARCADAS «revisar» (`marcar_revisar`) no entran en ningún
  PRECIO; sí en la cantidad y el valor, que es lo que se registró. Sin eso
  el lomo fino mostraba un «ahorro» de S/ 861 que era, entero, una compra
  cargada a S/ 15,85 el kilo.
"""

import html
import unicodedata
import zlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from st_aggrid import AgGrid, JsCode

from cortes import MESES_ABR_ES
from tema import (ACENTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA, GRIS_BORDE,
                  GRIS_TEXTO, GRIS_TEXTO_MEDIO, LAVANDA_BORDE, LAVANDA_CHIP,
                  TEXTO_PRINCIPAL)
from inyecciones import inyectar_html
from graficos.base import (
    _compras_layout, _compras_truncar, paso_etiquetas,
    preservar_widgets, rango_tarjeta, scope_rerun,
)
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CATEGORIA_SEC, COLUMNAS_DRILL_FICHA,
    CROMO_GRID_RANK, GAP_DRILL, _clave_grilla, _first_point,
    documento_legible, inicio_de_periodo, moda_por_grupo,
    selector_fecha_tarjeta, tramo_parcial, unidad_corta,
)
from graficos.compras._css_proveedor import (
    CSS as CSS_PROVEEDOR, CSS_FICHA, CSS_RANKING_PROV, clonar_prefijo,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras.semanal import precio_habitual
from graficos import alturas, periodo


_KEYS_WIDGET = ("compras_prod_q", "cp_prod_ver", "cp_prod_fam",
                "cp_prod_sub", "compras_prod_periodo", "cp_prod_gran",
                "cp_prod_tab", "cp_prod_pw")
"""Los controles de esta sección, para que la escalada no se los lleve.

La consume `preservar_widgets` en los `st.rerun` de más abajo: el rerun
aborta la corrida antes de dibujarlos y Streamlit recolecta lo que no se
dibujó (regla #373). Todas como TEXTO: la guarda de `test_graficos.py` lee
esta tupla con `ast.literal_eval`."""

_KEYS_FICHA = ("compras_prod_periodo", "cp_prod_gran", "cp_prod_tab",
               "cp_prod_pw")
"""Los de la FICHA, que se dibujan después de la lista. El clic en una
familia o subfamilia de la lista pide un rerun DESPUÉS de dibujar los
controles de la lista y ANTES de los de la ficha: se preservan sólo éstos.
Reescribir uno ya dibujado en la corrida es un StreamlitAPIException
(«cannot be modified after the widget … is instantiated»)."""

_GRANOS = ("Semana", "Mes", "Año", "Documento")
_VER = {"prod": "Producto", "sub": "Subfamilia", "fam": "Familia"}
_TODAS = "__todas__"
_TABS = ("prov", "comp", "per")
_PW = ("rango", "90", "ven")

_VECES_REVISAR = 2.5
"""Una compra a `_VECES_REVISAR` veces su precio habitual, o a menos de su
inversa (0,4), se marca «revisar». Regla PROPIA, no un estándar: medida
sobre 12 meses de compras el 2026-10-13 — con 40 % de desvío marcaba el
11 % de las líneas (verduras y hierbas de un día a otro), con 2,5 veces 54
líneas de 11.374."""

_MINIMO_REVISAR = 50.0
"""Y sólo si la línea vale al menos esto (S/): una ramita de hierba a otro
precio no cambia nada que se mida."""

_UND_ENTERAS = frozenset({"UND", "UNID", "UNIDAD", "UNIDADES", "UN"})
"""Las unidades que se cuentan enteras. Una cantidad con decimales en una
de ellas es la otra marca: Grupo Idali cargó el 29/09/2026 seis botellas
como 4,5 (6 × 0,75 L) y la vista leía cinco vinos «+33 %»."""

_FILAS_LISTA = 8
"""Filas a la vista en las tablas de la ficha antes de scrollear: lo que
deja la curva hasta el alto del ranking de al lado."""

_ALTO_FILA = 24
_FILAS_RANK = 12
"""Filas a la vista del ranking: lo que entra en `--alto-util` (575 px en
la laptop de 1323×619) con la fila de familias en dos renglones. Con la
de subfamilias abierta, dos menos (mide 27 + 6 de aire)."""


# ── Formato ────────────────────────────────────────────────────────────


def _esc(t):
    return html.escape(str(t), quote=True)


def _var_pct(cur, prev):
    """Variación % de `cur` contra `prev`; `inf` sin contra qué."""
    if prev is None or pd.isna(prev) or float(prev) <= 0 or cur is None \
            or pd.isna(cur):
        return np.inf
    return (float(cur) - float(prev)) / float(prev) * 100


def _fmt_var(v):
    """«▲ 12.3%», «▼ 4.0%», «0.0%» o «—»."""
    if v is None or not np.isfinite(v):
        return "—"
    if abs(v) < 0.05:
        return "0.0%"
    return f"{'▲' if v > 0 else '▼'} {abs(v):.1f}%"


def _cls_var(v):
    """Rojo si subió, verde si bajó, sin color debajo del 0,5 %: el código
    de todo Compras."""
    if v is None or not np.isfinite(v) or abs(v) < 0.5:
        return "igual"
    return "sube" if v > 0 else "baja"


def _soles(v):
    if v is None or pd.isna(v):
        return "—"
    return f"{'−' if v < 0 else ''}S/ {abs(v):,.0f}"


def _precio(v):
    return "—" if v is None or pd.isna(v) else f"S/ {v:,.2f}"


def _cant(c, um=""):
    """«112 kg», «2.5 und», «0.75»: sin ceros de más."""
    if c is None or pd.isna(c):
        return "—"
    t = (f"{c:,.1f}".rstrip("0").rstrip(".") if abs(c) < 100
         else f"{c:,.0f}")
    return f"{t} {um}" if um else t


def _um_corta(um):
    s = str(um or "").strip()
    return "" if s.lower() in ("", "nan", "none") else unidad_corta(s)


def _fecha_corta(f):
    f = pd.Timestamp(f)
    return f"{f.day} {MESES_ABR_ES[f.month - 1]}"


def _sin_tildes(texto):
    """Minúsculas y sin tildes, para que «limon» encuentre «Limón»."""
    return (unicodedata.normalize("NFKD", str(texto))
            .encode("ascii", "ignore").decode().lower())


def _coincide(nombres, consulta):
    """Máscara del buscador (regla #581): cada PALABRA de la consulta tiene
    que aparecer en el nombre, en cualquier orden."""
    _pal = _sin_tildes(consulta).split()
    _nom = nombres.astype(str).map(_sin_tildes)
    _m = pd.Series(True, index=nombres.index)
    for _p in _pal:
        _m &= _nom.str.contains(_p, regex=False)
    return _m


def _sin_gritar(nombre):
    """«CARNES» → «Carnes»; lo que ya viene en nombre propio, tal cual.

    `nombre_propio` (reglas #347 y #379) sólo sobre el texto que llega TODO
    en mayúsculas: las 8 familias gritan, y de las 95 subfamilias sólo 34
    (medido el 2026-09-11). Pasado sobre las otras 61, «Serv. Analisis»
    vuelve «SERV. Analisis»."""
    s = str(nombre)
    return nombre_propio(s) if not any(c.islower() for c in s) else s


# ── Los datos ──────────────────────────────────────────────────────────


def _normalizar(d, col_prod, col_fam, col_subfam, col_valor, col_cant,
                col_um, col_fecha, col_prov, col_docu):
    """El df del drill con nombres FIJOS (prod, fam, sub, valor, cant, um,
    fecha, prov, docu). Las familias y subfamilias vacías se unifican en
    «Sin familia» / «Sin subfamilia» en vez de descartarse: si no, sus
    totales dejarían de cuadrar con el del ranking."""
    n = len(d)

    def _txt(col, vacio=""):
        if col and col in d.columns:
            s = d[col].astype(str).str.strip()
            return s.where(~s.isin(("", "nan", "None")), vacio).to_numpy()
        return np.full(n, vacio, dtype=object)

    def _num(col):
        if col and col in d.columns:
            return pd.to_numeric(d[col], errors="coerce").fillna(0).to_numpy(
                dtype=float)
        return np.zeros(n)

    b = pd.DataFrame({
        "prod": _txt(col_prod),
        "fam": _txt(col_fam, "Sin familia"),
        "sub": _txt(col_subfam, "Sin subfamilia"),
        "valor": _num(col_valor),
        "cant": _num(col_cant),
        "um": _txt(col_um),
        "fecha": (pd.to_datetime(d[col_fecha], errors="coerce").dt.normalize()
                  .to_numpy() if col_fecha else pd.NaT),
        "prov": _txt(col_prov),
        "docu": _txt(col_docu),
    })
    return b[b["fecha"].notna() & (b["prod"] != "")].reset_index(drop=True)


def marcar_revisar(cant, valor, ref, um):
    """La marca de cada línea: «precio», «um» o «» (regla #653). Pura.

    · «um»: una cantidad con decimales en una unidad que se cuenta entera
      (`_UND_ENTERAS`) — 33 líneas en 12 meses, casi todas vinos cargados
      en litros.
    · «precio»: el precio de la línea a `_VECES_REVISAR` veces su precio
      habitual o a menos de su inversa, en una línea de `_MINIMO_REVISAR`
      soles o más — un error de tipeo, de unidad o de producto.

    La regla es PROPIA, no un estándar (ver las constantes)."""
    c = pd.to_numeric(pd.Series(cant), errors="coerce").reset_index(drop=True)
    v = pd.to_numeric(pd.Series(valor), errors="coerce").reset_index(drop=True)
    r = pd.to_numeric(pd.Series(ref), errors="coerce").reset_index(drop=True)
    u = pd.Series(um).astype(str).str.strip().str.upper().reset_index(drop=True)
    pu = (v / c).where(c > 0)
    q = pu / r.where(r > 0)
    fracc = u.isin(_UND_ENTERAS) & (c > 0) & ((c - c.round()).abs() > 1e-9)
    caro = q.notna() & ((q >= _VECES_REVISAR) | (q <= 1 / _VECES_REVISAR)) \
        & (v >= _MINIMO_REVISAR)
    return np.where(fracc, "um", np.where(caro, "precio", ""))


def _con_referencia(b):
    """`b` con el precio habitual de cada línea (`ref`, el de «Compras por
    período»: la mediana de los 90 días anteriores) y su marca (`flag`)."""
    if b.empty:
        return b.assign(ref=pd.Series(dtype=float), flag="")
    ref = precio_habitual(b["prod"], b["fecha"], b["valor"], b["cant"])
    b = b.assign(ref=ref.to_numpy())
    b["flag"] = marcar_revisar(b["cant"], b["valor"], b["ref"], b["um"])
    return b


def _resumen(rng, keys, prev, antes):
    """Una fila por `keys` (producto, familia o familia + subfamilia) con lo
    que muestran la lista y la ficha. Todo de una vez, sin un bucle por
    grupo (regla #537); se agrupa por columnas y se nombra por nombre
    (regla #481).

    · valor, cant, ult, docs, n (productos), nflag (líneas marcadas).
    · var / est: contra `prev` (el período anterior de igual largo);
      «nuevo» si nunca se compró antes, «vuelve» si sí pero no en `prev`.
    · pp, hab, ppv: precio ponderado, % contra el habitual y su impacto en
      soles — los tres SIN las líneas marcadas."""
    g = rng.groupby(keys, sort=False)
    out = g.agg(valor=("valor", "sum"), cant=("cant", "sum"),
                ult=("fecha", "max"), n=("prod", "nunique"))
    ok = rng[(rng["flag"] == "") & (rng["cant"] > 0)]
    out = out.join(ok.groupby(keys).agg(v_ok=("valor", "sum"),
                                        c_ok=("cant", "sum")))
    okr = ok[ok["ref"].notna()].assign(rc=lambda t: t["ref"] * t["cant"])
    out = out.join(okr.groupby(keys).agg(vref=("valor", "sum"),
                                         refc=("rc", "sum")))
    out = out.join(prev.groupby(keys).agg(prev=("valor", "sum")))
    out = out.join(rng[rng["flag"] != ""].groupby(keys)
                   .agg(nflag=("valor", "size")))
    _d = rng[rng["docu"] != ""].drop_duplicates(list(keys) + ["docu", "prov"])
    out = out.join(_d.groupby(keys).agg(docs=("docu", "size")))
    out[["prev", "nflag", "docs"]] = out[["prev", "nflag", "docs"]].fillna(0)
    out["var"] = np.where(out["prev"] > 0,
                          (out["valor"] / out["prev"].where(out["prev"] > 0)
                           - 1) * 100, np.nan)
    _vistos = set(antes)
    _idx = [tuple(i) if isinstance(i, tuple) else i for i in out.index]
    out["est"] = ["" if p > 0 else ("vuelve" if i in _vistos else "nuevo")
                  for i, p in zip(_idx, out["prev"])]
    out["pp"] = np.where(out["c_ok"] > 0, out["v_ok"] / out["c_ok"].where(
        out["c_ok"] > 0), out["valor"] / out["cant"].where(out["cant"] > 0))
    out["hab"] = (out["vref"] / out["refc"].where(out["refc"] > 0) - 1) * 100
    out["ppv"] = out["vref"] - out["refc"]
    return out.sort_values(["valor"], ascending=False, kind="stable")


def _ambito(res_p, fam, sub):
    """Los productos de `res_p` (un `_resumen` por producto, con `fam` y
    `sub`) que caen en la familia y la subfamilia elegidas.

    Siempre por la familia PRIMERO: la clave es el PAR (familia,
    subfamilia). 9 de las 95 subfamilias del parquet se repiten entre
    familias (medido el 2026-09-09), y un recorte por la subfamilia sola
    mezclaría productos de dos familias sin dar error."""
    amb = res_p
    if fam is not None:
        amb = amb[amb["fam"] == fam]
        if sub is not None:
            amb = amb[amb["sub"] == sub]
    return amb


def _ultimo_precio(rng):
    """El precio de la ÚLTIMA compra de cada producto en el rango
    (ponderado si ese día hubo varias)."""
    u = rng[rng["cant"] > 0]
    if u.empty:
        return pd.Series(dtype=float)
    u = u[u["fecha"] == u.groupby("prod")["fecha"].transform("max")]
    a = u.groupby("prod").agg(v=("valor", "sum"), c=("cant", "sum"))
    return a["v"] / a["c"]


def _cada_cuanto(h90):
    """Cada cuántos días se compra cada producto: la mediana de los saltos
    entre días con compra, en los últimos 90."""
    x = (h90[["prod", "fecha"]].drop_duplicates()
         .sort_values(["prod", "fecha"], kind="stable"))
    if x.empty:
        return pd.Series(dtype=float)
    x["gap"] = x.groupby("prod")["fecha"].diff().dt.days
    return x.groupby("prod")["gap"].median()


# ── Los períodos de la curva ──────────────────────────────────────────


def _clave(fechas, gran):
    f = pd.to_datetime(fechas)
    if gran == "Mes":
        return f.dt.to_period("M").astype(str)
    if gran == "Semana":
        return (f - pd.to_timedelta(f.dt.weekday, unit="D")).dt.strftime(
            "%Y-%m-%d")
    return f.dt.year.astype(str)


def _secuencia(ini, fin, gran):
    """TODOS los períodos entre `ini` y `fin`, también los sin compras: el
    eje es el tiempo, y un mes vacío se ve como un hueco, no desaparece."""
    ini, fin = pd.Timestamp(ini), pd.Timestamp(fin)
    if gran == "Mes":
        return [str(p) for p in pd.period_range(ini, fin, freq="M")]
    if gran == "Semana":
        lun = ini - pd.Timedelta(days=ini.weekday())
        return [x.strftime("%Y-%m-%d")
                for x in pd.date_range(lun, fin, freq="7D")]
    return [str(y) for y in range(ini.year, fin.year + 1)]


def _etq(k, gran, largo=False):
    """El rótulo de un período a partir de su clave."""
    k = str(k)
    try:
        if gran == "Mes":
            f = pd.Timestamp(k + "-01")
            m = MESES_ABR_ES[f.month - 1]
            return f"{m} {f.year}" if largo else f"{m} {str(f.year)[2:]}"
        if gran == "Semana":
            f = pd.Timestamp(k)
            return (f"sem. del {_fecha_corta(f)}" if largo
                    else _fecha_corta(f))
        if gran == "Documento":
            fec, doc, prov = (k.split("|") + ["", "", ""])[:3]
            corto = _fecha_corta(fec)
            if not largo:
                return corto
            leg = documento_legible(pd.Series([doc])).iat[0] if doc \
                and not doc.startswith("#") else ""
            return " · ".join(x for x in (corto, nombre_propio(prov), leg) if x)
    except (ValueError, IndexError):
        pass
    return k


def _serie(h, gran, op, ultimo, rango):
    """La curva del producto: un dict con `keys` (en orden), `agg` (una fila
    por período: c, v, pc, pv, rc, cr, docs, fl), `lineas` (las del
    ámbito, con su clave `k`), `parc` (`tramo_parcial` o None) y `refq` (la
    cantidad de los mismos días del período anterior). `None` sin compras.

    La ventana arranca al INICIO de su período (`inicio_de_periodo`): «3
    meses» al 11 de octubre empezaba el 12 de julio y la primera barra era
    un mes de 20 días (regla #646)."""
    if h.empty:
        return None
    if op == periodo.HEREDA and rango is not None:
        ini, fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    else:
        v = periodo.ventana(op, ultimo, minimo=h["fecha"].min())
        if v is None:
            return None
        ini, fin = v
    if gran != "Documento":
        ini = inicio_de_periodo(ini, gran)
    w = h[(h["fecha"] >= ini) & (h["fecha"] <= fin)].copy()
    if w.empty:
        return None
    if gran == "Documento":
        _doc = w["docu"].where(w["docu"] != "", "#" + w.index.astype(str))
        w["k"] = (w["fecha"].dt.strftime("%Y-%m-%d") + "|" + _doc + "|"
                  + w["prov"])
        keys = sorted(w["k"].unique())
    else:
        w["k"] = _clave(w["fecha"], gran).to_numpy()
        keys = _secuencia(ini, fin, gran)
    ok = (w["flag"] == "") & (w["cant"] > 0)
    okr = ok & w["ref"].notna()
    w["pc"] = w["cant"].where(ok, 0.0)
    w["pv"] = w["valor"].where(ok, 0.0)
    w["rc"] = (w["ref"] * w["cant"]).where(okr, 0.0)
    w["cr"] = w["cant"].where(okr, 0.0)
    w["fl"] = (w["flag"] != "").astype(int)
    agg = (w.groupby("k").agg(c=("cant", "sum"), v=("valor", "sum"),
                              pc=("pc", "sum"), pv=("pv", "sum"),
                              rc=("rc", "sum"), cr=("cr", "sum"),
                              fl=("fl", "sum"), docs=("valor", "size"))
           .reindex(keys).fillna(0.0))
    parc = tramo_parcial(gran, ultimo) if gran != "Documento" else None
    if parc is not None and _clave(pd.Series([parc["ini"]]), gran).iat[0] \
            != keys[-1]:
        parc = None
    refq = None
    if parc is not None:
        _r = h[(h["fecha"] >= parc["ref_ini"]) & (h["fecha"] <= parc["ref_fin"])]
        refq = float(_r["cant"].sum())
    return {"keys": keys, "agg": agg, "lineas": w, "parc": parc,
            "refq": refq, "ini": ini, "fin": fin}


def _precios(agg):
    """El precio ponderado y el habitual de cada período, SIN las líneas
    marcadas (regla #653)."""
    p = agg["pv"] / agg["pc"].where(agg["pc"] > 0)
    hab = agg["rc"] / agg["cr"].where(agg["cr"] > 0)
    return p, hab


def _fig_producto(S, gran, um, sel):
    """La curva de la ficha: la CANTIDAD en barras (eje izquierdo) y el
    PRECIO ponderado en línea (eje derecho), con el habitual punteado.

    La barra del valor de antes mezclaba precio y cantidad: subía igual si
    se compraba más o si se pagaba más. Separadas, la pregunta «¿compré más
    o pagué más?» se contesta mirando.

    El período en curso va RAYADO, con una raya en la cantidad de los
    mismos días del anterior y el último tramo del precio punteado (regla
    #646). Un período con compras marcadas lleva un punto naranja: su
    precio es el de las otras; si no hay otras, el punto va en el precio
    marcado, recortado al borde del eje."""
    keys, agg = S["keys"], S["agg"]
    n = len(keys)
    cant = agg["c"].tolist()
    precio, hab = _precios(agg)
    pr = [None if pd.isna(x) else float(x) for x in precio]
    hb = [None if pd.isna(x) else float(x) for x in hab]
    parc = S["parc"] is not None
    fig = go.Figure()

    _col = [(ACENTO if k == sel else LAVANDA_CHIP) if sel else LAVANDA_BORDE
            for k in keys]
    _pat = ["/" if parc and i == n - 1 else "" for i in range(n)]
    _hover = []
    for i, k in enumerate(keys):
        a = agg.iloc[i]
        _l = [f"<b>{_esc(_etq(k, gran, largo=True))}"
              + (" (en curso)" if parc and i == n - 1 else "") + "</b>",
              _cant(a["c"], um) + (f" · {_precio(pr[i])} por {um or 'unidad'}"
                                    if pr[i] is not None else ""),
              f"{_soles(a['v'])} · {int(a['docs'])} "
              + ("compra" if int(a["docs"]) == 1 else "compras")]
        if a["fl"]:
            _l.append(f"{int(a['fl'])} para revisar, fuera del precio")
        _hover.append("<br>".join(_l))
    fig.add_bar(x=keys, y=cant, marker=dict(
        color=_col, line=dict(width=0),
        pattern=dict(shape=_pat, fgcolor=GRIS_BORDE, size=6, solidity=0.35)),
        customdata=_hover, hovertemplate="%{customdata}<extra></extra>",
        showlegend=False)
    if parc and S["refq"]:
        fig.add_scatter(
            x=[keys[-1]], y=[S["refq"]], mode="markers",
            marker=dict(symbol="line-ew-open", size=26, color=GRIS_TEXTO_MEDIO,
                        line=dict(color=GRIS_TEXTO_MEDIO, width=2)),
            hoverinfo="skip", showlegend=False)

    # El eje del precio: con un mínimo de alto (8 % del máximo), si no una
    # variación de 0,4 % se dibujaba como una montaña.
    _nums = [x for x in pr + hb if x is not None]
    if _nums:
        _lo, _hi = min(_nums), max(_nums)
        _pad = (_hi - _lo) * 0.18
        _min = _hi * 0.08 or 1.0
        if _hi - _lo + 2 * _pad < _min:
            _mid = (_hi + _lo) / 2
            y2 = [max(0.0, _mid - _min / 2), _mid + _min / 2]
        else:
            y2 = [max(0.0, _lo - _pad), _hi + _pad]
    else:
        y2 = [0.0, 1.0]
    _ult = n - 2 if parc else n - 1
    fig.add_scatter(x=keys, y=hb, mode="lines", yaxis="y2", connectgaps=True,
                    line=dict(color=GRIS_TEXTO, width=1.6, dash="dash"),
                    hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=keys[:_ult + 1], y=pr[:_ult + 1], mode="lines+markers",
                    yaxis="y2", connectgaps=True,
                    line=dict(color=ACENTO_TEXTO_OSCURO, width=2.4),
                    marker=dict(color=ACENTO_TEXTO_OSCURO, size=5),
                    hoverinfo="skip", showlegend=False)
    if parc and n > 1 and pr[-1] is not None:
        _k = next((i for i in range(n - 2, -1, -1) if pr[i] is not None), None)
        if _k is not None:
            fig.add_scatter(x=[keys[_k], keys[-1]], y=[pr[_k], pr[-1]],
                            mode="lines", yaxis="y2",
                            line=dict(color=ACENTO_TEXTO_OSCURO, width=2,
                                      dash="dot"),
                            hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=[keys[-1]], y=[pr[-1]], mode="markers", yaxis="y2",
                        marker=dict(symbol="circle-open", size=9,
                                    color=ACENTO_TEXTO_OSCURO,
                                    line=dict(color=ACENTO_TEXTO_OSCURO,
                                              width=2)),
                        hoverinfo="skip", showlegend=False)
    _fx, _fy = [], []
    for i, k in enumerate(keys):
        a = agg.iloc[i]
        if not a["fl"]:
            continue
        if pr[i] is not None:
            _fy.append(pr[i])
        elif a["c"] > 0:
            _fy.append(min(max(a["v"] / a["c"], y2[0]), y2[1]))
        else:
            continue
        _fx.append(k)
    if _fx:
        fig.add_scatter(x=_fx, y=_fy, mode="markers", yaxis="y2",
                        marker=dict(color=ADVERTENCIA, size=8,
                                    line=dict(color="white", width=1)),
                        hoverinfo="skip", showlegend=False)

    _etqs = [_etq(k, gran) for k in keys]
    _paso = paso_etiquetas(n, max((len(e) for e in _etqs), default=1),
                           ancho=560, px_fuente=11)
    _tv = [k for i, k in enumerate(keys) if (n - 1 - i) % _paso == 0]
    _ymax = max(cant + [S["refq"] or 0, 0]) * 1.18 or 1.0
    _compras_layout(fig, alto=alturas.CURVA_FICHA)
    fig.update_layout(
        margin=dict(l=40, r=52, t=6, b=22),
        xaxis=dict(type="category", tickangle=0, tickmode="array",
                   tickvals=_tv, ticktext=[_etq(k, gran) for k in _tv],
                   tickfont=dict(size=11), categoryorder="array",
                   categoryarray=list(keys), fixedrange=True),
        yaxis=dict(showticklabels=True, range=[0, _ymax], nticks=3,
                   tickformat="~s", ticksuffix=f" {um}" if um else "",
                   tickfont=dict(size=10, color=GRIS_TEXTO), fixedrange=True),
        yaxis2=dict(overlaying="y", side="right", range=y2, showgrid=False,
                    nticks=3, tickprefix="S/ ",
                    tickformat=",.0f" if y2[1] >= 100 else ",.1f",
                    tickfont=dict(size=10, color=ACENTO_TEXTO_OSCURO),
                    fixedrange=True, zeroline=False),
        showlegend=False, hovermode="closest", bargap=0.35,
    )
    return fig


# ── La ficha: cifras y tablas en HTML ─────────────────────────────────


def _html_kpis(fila, um, dias, ant_txt):
    """Las cinco cifras del RANGO del ranking."""
    if fila["est"]:
        _ayuda = ("Primera compra de este producto" if fila["est"] == "nuevo"
                  else "No se compró en el período anterior")
        _v = (f'<span class="cp-fi-chip {fila["est"]}" title="{_esc(_ayuda)}">'
              f'{fila["est"]}</span>')
    else:
        _v = f'<b class="{_cls_var(fila["var"])}">{_fmt_var(fila["var"])}</b>'
    # `<i>` y no `<span>`: `.cp-fi-kpis span` es el rótulo, en bloque.
    _warn = ('<i class="cpp-warn" title="Sin las compras marcadas para '
             'revisar">⚠</i>' if fila["nflag"] else "")
    _ppv = fila["ppv"]
    if _ppv is None or pd.isna(_ppv):
        _p = '<b class="igual">—</b>'
    elif abs(_ppv) < 1:
        _p = '<b class="igual">S/ 0</b>'
    else:
        _p = (f'<b class="{"sube" if _ppv > 0 else "baja"}">'
              f'{"+" if _ppv > 0 else "−"}S/ {abs(_ppv):,.0f}</b>'
              f'<small>{"de más" if _ppv > 0 else "de ahorro"}</small>')
    _ayuda_hab = ("El precio pagado en el rango contra el habitual de cada "
                  "compra: la mediana de los 90 días anteriores, la misma "
                  "de «Compras por período» y de Proveedor")
    _ayuda_ppv = ("(precio pagado − precio habitual) × cantidad, sobre las "
                  "compras del rango: la variación de precio de compra de "
                  "la contabilidad de costos estándar")
    return ('<div class="cp-fi-kpis">'
            f'<div><span>Compra en el rango</span><b>{_soles(fila["valor"])}</b>'
            f'<small>{_esc(_cant(fila["cant"], um))}</small></div>'
            f'<div title="{_esc(ant_txt)}"><span>vs. los {dias} días antes'
            f'</span>{_v}</div>'
            f'<div><span>Precio ponderado</span><b>{_precio(fila["pp"])}</b>'
            f'<small>/ {_esc(um or "unidad")}</small>{_warn}</div>'
            f'<div title="{_esc(_ayuda_hab)}"><span>vs. precio habitual</span>'
            f'<b class="{_cls_var(fila["hab"])}">{_fmt_var(fila["hab"])}</b></div>'
            f'<div title="{_esc(_ayuda_ppv)}"><span>Impacto del precio</span>'
            f'{_p}</div></div>')


def _fila_html(clase, celdas, acc=None, extra=""):
    _a = f' data-acc="{_esc(acc)}"' if acc else ""
    return (f'<div class="cpp-f {clase} {extra}"{_a}>' + "".join(celdas)
            + "</div>")


def _por_documento(L):
    """Las líneas de `L` juntadas por documento: un producto entra una vez
    por comprobante, pero un comprobante puede traerlo en dos líneas."""
    if L.empty:
        return L
    return (L.groupby(["fecha", "docu", "prov"], as_index=False, sort=False)
             .agg(cant=("cant", "sum"), valor=("valor", "sum"),
                  ref=("ref", "mean"), flag=("flag", "max")))


def _html_proveedores(L, um, alto):
    """Proveedores: el precio PONDERADO de cada uno en el mismo ámbito, el
    más barato marcado y cuánto más caro sale el resto. El precio va sin
    las compras marcadas; la cantidad y el valor, con ellas."""
    if L.empty:
        return ('<div class="cp-modo-nota">Sin compras en esos días.</div>',
                0)
    ok = (L["flag"] == "") & (L["cant"] > 0)
    t = L.assign(pc=L["cant"].where(ok, 0.0), pv=L["valor"].where(ok, 0.0),
                 fl=(L["flag"] != "").astype(int))
    g = (t.groupby("prov").agg(c=("cant", "sum"), v=("valor", "sum"),
                               pc=("pc", "sum"), pv=("pv", "sum"),
                               ult=("fecha", "max"), fl=("fl", "sum"))
          .sort_values("v", ascending=False, kind="stable"))
    g["p"] = np.where(g["pc"] > 0, g["pv"] / g["pc"].where(g["pc"] > 0),
                      g["v"] / g["c"].where(g["c"] > 0))
    _min = g["p"].min() if g["p"].notna().any() else None
    _tot = float(g["v"].sum()) or 1.0
    filas = []
    for prov, a in g.iterrows():
        _cheap = len(g) > 1 and _min is not None and a["p"] == _min
        if _cheap:
            _d = '<span class="cpp-chip barato">más barato</span>'
        elif len(g) > 1 and pd.notna(a["p"]) and _min:
            _dif = (a["p"] / _min - 1) * 100
            _d = (f'<span class="{"sube" if _dif > 10 else ""}">'
                  f'+{_dif:.1f}%</span>')
        else:
            _d = '<span class="igual">—</span>'
        _w = (' <span class="cpp-warn" title="Incluye una compra para '
              'revisar">⚠</span>' if a["fl"] else "")
        filas.append(_fila_html("cpp-pv", [
            f'<span class="nm" title="{_esc(nombre_propio(prov))}">'
            f'{_esc(nombre_propio(prov))}{_w}</span>',
            f'<span class="r">{_esc(_cant(a["c"], um))}</span>',
            f'<span class="r">{_precio(a["p"])}</span>',
            f'<span class="r">{_d}</span>',
            f'<span class="r">{_soles(a["v"])}</span>',
            f'<span class="r gr">{a["v"] / _tot * 100:.0f}%</span>',
            f'<span class="r gr">{_fecha_corta(a["ult"])}</span>'],
            acc=f"prov:{prov}"))
    _pc, _pv = float(g["pc"].sum()), float(g["pv"].sum())
    _p = _pv / _pc if _pc else (float(g["v"].sum()) / float(g["c"].sum())
                               if float(g["c"].sum()) else None)
    tot = _fila_html("cpp-pv tot", [
        f'<span class="nm">Total · {len(g)} '
        f'{"proveedor" if len(g) == 1 else "proveedores"}</span>',
        f'<span class="r">{_esc(_cant(float(g["c"].sum()), um))}</span>',
        f'<span class="r">{_precio(_p)}</span>', "<span></span>",
        f'<span class="r">{_soles(float(g["v"].sum()))}</span>',
        '<span class="r">100%</span>', "<span></span>"])
    cab = _fila_html("cpp-pv cpp-h", [
        "<span>Proveedor</span>", '<span class="r">Cant.</span>',
        '<span class="r">Precio</span>',
        '<span class="r" title="Cuánto más caro sale que el más barato, en '
        'los mismos días">vs. más barato</span>',
        '<span class="r">Valor</span>', '<span class="r">%</span>',
        '<span class="r">Última</span>'])
    return (f'<div class="cpp-t">{cab}<div class="cpp-l" style="max-height:'
            f'{alto}px">' + "".join(filas) + f"</div>{tot}</div>", len(g))


def _ayuda_marca(flag, cant, valor, ref, um):
    if flag == "um":
        _b = cant / 0.75
        _6 = (f" {round(_b)} botellas × 0,75 L = {_cant(cant)}: ¿se cargó en "
              "litros?") if abs(_b - round(_b)) < 0.01 else \
            " ¿Se cargó en otra unidad?"
        return (f"{_cant(cant, um)}: una unidad que se cuenta entera viene "
                f"con decimales.{_6}")
    if flag == "precio" and cant and ref:
        _pu = valor / cant
        return (f"Precio {_precio(_pu)} contra un habitual de {_precio(ref)} "
                f"({_pu / ref:.1f} veces): ¿error de tipeo, de unidad o de "
                "producto?")
    return ""


def _html_compras(L, um, alto):
    """Compras: una fila por documento, de la más nueva a la más vieja,
    con su precio contra el habitual y la marca «revisar»."""
    D = _por_documento(L)
    if D.empty:
        return ('<div class="cp-modo-nota">Sin compras en este ámbito.</div>',
                0)
    D = D.sort_values("fecha", ascending=False, kind="stable")
    filas = []
    for _, a in D.iterrows():
        _pu = a["valor"] / a["cant"] if a["cant"] else None
        _h = (_pu / a["ref"] - 1) * 100 if _pu and pd.notna(a["ref"]) \
            and a["ref"] > 0 else np.inf
        _m = ""
        if a["flag"]:
            _m = (f'<span class="cpp-chip revisar" title="'
                  f'{_esc(_ayuda_marca(a["flag"], a["cant"], a["valor"], a["ref"], um))}'
                  '">revisar</span>')
        _doc = (documento_legible(pd.Series([a["docu"]])).iat[0]
                if a["docu"] else "—")
        filas.append(_fila_html("cpp-cp", [
            f'<span>{_fecha_corta(a["fecha"])}</span>',
            f'<span class="nm">{_esc(nombre_propio(a["prov"]))}</span>',
            f'<span class="nm gr">{_esc(_doc)}</span>',
            f'<span class="r">{_esc(_cant(a["cant"]))}</span>',
            f'<span class="r">{_precio(_pu)}</span>',
            f'<span class="r {_cls_var(_h)}">{_fmt_var(_h)}</span>',
            f'<span class="r">{_soles(a["valor"])}</span>',
            f'<span class="r">{_m}</span>']))
    ok = (D["flag"] == "") & (D["cant"] > 0)
    _pc, _pv = float(D.loc[ok, "cant"].sum()), float(D.loc[ok, "valor"].sum())
    okr = ok & D["ref"].notna()
    _rc = float((D.loc[okr, "ref"] * D.loc[okr, "cant"]).sum())
    _cr = float(D.loc[okr, "cant"].sum())
    _ph = (_pv / _pc) / (_rc / _cr) * 100 - 100 if _pc and _rc and _cr \
        else np.inf
    _w = (' <span class="cpp-warn" title="Sin las compras marcadas para '
          'revisar">⚠</span>' if (D["flag"] != "").any() else "")
    tot = _fila_html("cpp-cp tot", [
        f'<span class="nm">Total · {len(D)}</span>', "<span></span>",
        "<span></span>",
        f'<span class="r">{_esc(_cant(float(D["cant"].sum()), um))}</span>',
        f'<span class="r">{_precio(_pv / _pc if _pc else None)}{_w}</span>',
        f'<span class="r {_cls_var(_ph)}">{_fmt_var(_ph)}</span>',
        f'<span class="r">{_soles(float(D["valor"].sum()))}</span>',
        "<span></span>"])
    cab = _fila_html("cpp-cp cpp-h", [
        "<span>Fecha</span>", "<span>Proveedor</span>",
        "<span>Documento</span>", '<span class="r">Cant.</span>',
        '<span class="r">Precio</span>',
        '<span class="r" title="El precio de esa compra contra el habitual '
        'de ese día">vs. hab.</span>',
        '<span class="r">Valor</span>', "<span></span>"])
    return (f'<div class="cpp-t">{cab}<div class="cpp-l" style="max-height:'
            f'{alto}px">' + "".join(filas) + f"</div>{tot}</div>", len(D))


def _html_periodos(S, gran, um, alto, sel):
    """Períodos: la curva escrita, una fila por barra en el orden del eje.
    Un clic en una fila abre sus compras."""
    keys, agg = S["keys"], S["agg"]
    precio, hab = _precios(agg)
    _tot = float(agg["v"].sum()) or 1.0
    filas, prev = [], None
    n = len(keys)
    for i, k in enumerate(keys):
        a = agg.iloc[i]
        p, h = precio.iat[i], hab.iat[i]
        _h = (p / h - 1) * 100 if pd.notna(p) and pd.notna(h) and h else np.inf
        _dp = _var_pct(p, prev) if pd.notna(p) else np.inf
        if pd.notna(p):
            prev = p
        _parc = S["parc"] is not None and i == n - 1
        _lab = _etq(k, gran, largo=True) + (
            f' (1–{S["parc"]["fin"].day})' if _parc and gran == "Mes" else
            (" (en curso)" if _parc else ""))
        _w = (' <span class="cpp-warn" title="Precio sin las compras '
              'marcadas para revisar">⚠</span>' if a["fl"] else "")
        filas.append(_fila_html("cpp-pe", [
            f'<span class="nm{" cpp-parc" if _parc else ""}">{_esc(_lab)}</span>',
            f'<span class="r">{_esc(_cant(a["c"], um)) if a["c"] else "—"}</span>',
            f'<span class="r">{_precio(p)}{_w}</span>',
            f'<span class="r {_cls_var(_h)}">{_fmt_var(_h)}</span>',
            f'<span class="r">{_soles(a["v"]) if a["v"] else "—"}</span>',
            f'<span class="r gr">{a["v"] / _tot * 100:.0f}%</span>'
            if a["v"] else '<span class="r gr">—</span>',
            f'<span class="r">{int(a["docs"]) or "—"}</span>',
            f'<span class="r {_cls_var(_dp)}">{_fmt_var(_dp)}</span>'],
            acc=f"per:{k}", extra="sel" if k == sel else ""))
    _pc, _pv = float(agg["pc"].sum()), float(agg["pv"].sum())
    _rc, _cr = float(agg["rc"].sum()), float(agg["cr"].sum())
    _ph = (_pv / _pc) / (_rc / _cr) * 100 - 100 if _pc and _rc and _cr \
        else np.inf
    tot = _fila_html("cpp-pe tot", [
        '<span class="nm">Total</span>',
        f'<span class="r">{_esc(_cant(float(agg["c"].sum()), um))}</span>',
        f'<span class="r">{_precio(_pv / _pc if _pc else None)}</span>',
        f'<span class="r {_cls_var(_ph)}">{_fmt_var(_ph)}</span>',
        f'<span class="r">{_soles(_tot)}</span>',
        '<span class="r">100%</span>',
        f'<span class="r">{int(agg["docs"].sum())}</span>', "<span></span>"])
    cab = _fila_html("cpp-pe cpp-h", [
        "<span>Período</span>", '<span class="r">Cant.</span>',
        '<span class="r">Precio</span>', '<span class="r">vs. hab.</span>',
        '<span class="r">Valor</span>',
        '<span class="r" title="% del valor de la curva">%</span>',
        '<span class="r">Docs</span>',
        '<span class="r" title="El precio contra el período anterior">'
        'Δ precio</span>'])
    return (f'<div class="cpp-t">{cab}<div class="cpp-l" style="max-height:'
            f'{alto}px">' + "".join(filas) + f"</div>{tot}</div>")


# ── El clic en una fila de la ficha (HTML, sin widget) ────────────────


_K_RELEVO = "cp_prod_relevo"
"""El `st.text_input` oculto por el que un clic en una fila de Proveedores
o de Períodos llega a Python (regla #217, como en Proveedor)."""

_SEP_RELEVO = "@@"


def _relevo():
    """`on_change` del relevo: «prov:<nombre>» acota Compras a ese
    proveedor, «per:<clave>» a ese período. Los dos llevan a Compras.
    Corre ANTES de dibujar nada, así que puede escribir la pestaña."""
    raw = (st.session_state.get(_K_RELEVO) or "").rsplit(_SEP_RELEVO, 1)[0]
    tipo, _, val = raw.partition(":")
    if not val:
        return
    if tipo == "prov":
        st.session_state["cp_prod_cprov"] = val
        if st.session_state.get("cp_prod_pw") != "ven":
            st.session_state["cp_prod_per"] = None
    elif tipo == "per":
        _act = st.session_state.get("cp_prod_per")
        st.session_state["cp_prod_per"] = None if _act == val else val
        st.session_state["cp_prod_cprov"] = None
    st.session_state["cp_prod_tab"] = "comp"


def _soltar():
    st.session_state["cp_prod_per"] = None
    st.session_state["cp_prod_cprov"] = None


_JS_CLIC = f"""<script>
(function () {{
  // Un clic en una fila con `data-acc` de la ficha escribe su acción en el
  // relevo y la confirma con un Enter de verdad (regla #217). Delegado en
  // el DOCUMENTO: la tabla se rehace en cada corrida.
  var w = window.parent, doc = w.document;
  if (w.__cppClic) doc.removeEventListener('click', w.__cppClic, true);
  w.__cppClic = function (ev) {{
    var t = ev.target && ev.target.closest && ev.target.closest('[data-acc]');
    if (!t || !t.closest('.st-key-compras_prod_card_ficha')) return;
    var relevo = doc.querySelector('.st-key-{_K_RELEVO} input');
    if (!relevo) return;
    var setter = w.Object.getOwnPropertyDescriptor(
      w.HTMLInputElement.prototype, 'value').set;
    relevo.focus({{preventScroll: true}});
    setter.call(relevo, t.getAttribute('data-acc') + '{_SEP_RELEVO}' + w.Date.now());
    relevo.dispatchEvent(new w.Event('input', {{bubbles: true}}));
    var o = {{key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
             bubbles: true, cancelable: true}};
    relevo.dispatchEvent(new w.KeyboardEvent('keydown', o));
    relevo.dispatchEvent(new w.KeyboardEvent('keyup', o));
  }};
  doc.addEventListener('click', w.__cppClic, true);
}})();
</script>"""


# ── CSS ────────────────────────────────────────────────────────────────
# La ficha es la de Proveedor: sus reglas se CLONAN con los prefijos de
# acá (`clonar_prefijo`, el mismo mecanismo que `cp_docs`), así un retoque
# allá llega solo. Lo propio —las tres tablas y la fila de familias— va
# abajo, escrito.
_CSS_PROPIO = """
        .st-key-compras_prod_card_ficha {
            container-type: inline-size; container-name: cpprods;
        }
        .st-key-cpp_ficha_cab .cp-fi-nom { line-height: 28px; }
        .cpp-sub {
            font-size: 11.5px; color: var(--text-secondary); line-height: 16px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            margin-top: -4px;
        }
        .cpp-warn { color: var(--warning-text); margin-left: 4px; font-size: 11px;
                    font-style: normal; }
        /* El desplegable de la ventana dice «Últimos 3 meses»: el ancho de
           Proveedor (56 px, para «12m») lo cortaba en «Últim…». */
        .st-key-cpp_evo_ctrl > .st-key-compras_prod_periodo { width: 128px !important; }
        .st-key-cpp_pw_fila {
            display: flex !important; flex-direction: row !important;
            align-items: center !important; gap: 8px !important;
            width: auto !important; flex-wrap: nowrap !important;
        }
        .st-key-cpp_pw_fila > * { width: auto !important; flex: 0 0 auto; margin: 0 !important; }
        .st-key-cpp_pw_fila .cp-modo-nota { margin: 0 !important; padding: 0 !important;
                                            line-height: 22px; height: 22px; }
        .st-key-cpp_pw_fila [data-testid="stMarkdownContainer"] { margin: 0 !important; }
        .st-key-cpp_pw_fila div[class*="st-key-cp_modo_"] {
            position: static !important; height: auto !important;
        }
        .cpp-ley { display: flex; gap: 12px; flex-wrap: wrap; align-items: center;
                   font-size: 11px; color: var(--text-secondary); min-height: 18px; }
        .cpp-ley span { display: inline-flex; align-items: center; gap: 5px; }
        .cpp-ley i { display: inline-block; flex: 0 0 auto; }
        .cpp-ley i.bar { width: 10px; height: 9px; border-radius: 2px;
                         background: var(--border-lavender); }
        .cpp-ley i.lin { width: 14px; height: 0; border-top: 2.5px solid var(--accent-deep); }
        .cpp-ley i.hab { width: 14px; height: 0; border-top: 2px dashed var(--text-secondary); }
        .cpp-ley i.raya { width: 14px; height: 2px; background: var(--text-secondary); }
        .cpp-ley i.mar { width: 8px; height: 8px; border-radius: 50%;
                         background: var(--warning); }
        .cpp-ley .var { font-weight: 600; color: var(--text-primary); }
        .cpp-t { font-size: 12px; line-height: 1.25; overflow-x: auto; }
        /* En una ventana angosta la tabla se desliza de costado en vez de
           aplastar la columna del nombre (a 860 px «Proveedor» salía letra
           por letra). En la laptop mide más que esto y no se nota. */
        .cpp-t > * { min-width: 600px; }
        .cpp-f > span { min-width: 0; overflow: hidden; text-overflow: ellipsis;
                        white-space: nowrap; }
        .cpp-f {
            display: grid; align-items: center; column-gap: 8px; padding: 0 8px;
            height: 24px; border-bottom: 1px solid var(--border);
            font-variant-numeric: tabular-nums; color: var(--text-primary);
        }
        .cpp-f.cpp-h { height: 22px; font-size: 11px; color: var(--text-secondary); }
        .cpp-f[data-acc] { cursor: pointer; }
        .cpp-f[data-acc]:hover { background: var(--bg-primary); }
        .cpp-f.sel { background: var(--accent-tint); }
        .cpp-f.tot { background: var(--bg-primary); font-weight: 700;
                     border-bottom: none; border-radius: 8px; }
        .cpp-l { overflow-y: auto; }
        .cpp-l::-webkit-scrollbar { width: 6px; }
        .cpp-l::-webkit-scrollbar-thumb { background: var(--scroll-thumb); border-radius: 3px; }
        .cpp-t .r { text-align: right; white-space: nowrap; }
        .cpp-t .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                     min-width: 0; }
        .cpp-t .gr { color: var(--text-secondary); }
        .cpp-t .sube { color: var(--danger-text); font-weight: 600; }
        .cpp-t .baja { color: var(--success-text); font-weight: 600; }
        .cpp-t .igual { color: var(--text-muted); }
        .cpp-t .cpp-parc { background: repeating-linear-gradient(45deg,
            var(--border) 0 2px, transparent 2px 6px); border-radius: 4px; }
        .cpp-pv { grid-template-columns: minmax(0, 1fr) 72px 72px 92px 80px 40px 52px; }
        .cpp-cp { grid-template-columns: 48px minmax(0, 1fr) 92px 60px 70px 62px 76px 56px; }
        .cpp-pe { grid-template-columns: minmax(0, 1fr) 80px 76px 62px 80px 40px 38px 66px; }
        .cpp-chip { display: inline-block; font-size: 10px; font-weight: 600;
                    border-radius: 999px; padding: 0 6px; line-height: 16px; }
        .cpp-chip.barato { color: var(--success-text); background: var(--success-bg); }
        .cpp-chip.revisar { color: var(--warning-text); background: var(--warning-bg); }
        .st-key-cp_prod_relevo {
            position: absolute !important;
            width: 1px !important; height: 1px !important;
            overflow: hidden !important; opacity: 0 !important;
            margin: 0 !important; padding: 0 !important;
        }
        .st-key-cpp_ficha_tabs .cp-modo-nota { font-size: 11px; color: var(--text-secondary); }
        .st-key-cp_prod_soltar button {
            min-height: 22px !important; height: 22px !important;
            padding: 0 8px !important; font-size: 11.5px !important;
            color: var(--accent-deep) !important;
        }
        /* La fila del buscador y «Ver por», y los botones de familia y
           subfamilia: chicos, para que las cinco familias entren en dos
           renglones y la lista no pierda filas. */
        .st-key-cp_prod_busca {
            display: flex !important; flex-direction: row !important;
            align-items: center !important; gap: 6px !important;
            flex-wrap: nowrap !important;
        }
        .st-key-cp_prod_busca > *:first-child { flex: 1 1 auto; min-width: 0; }
        .st-key-cp_prod_busca > * { width: auto !important; flex: 0 0 auto; }
        .st-key-cp_prod_busca [data-testid="stTextInputRootElement"] {
            height: 28px !important; min-height: 28px !important;
        }
        .st-key-cp_prod_busca input { font-size: 12px !important; padding: 0 10px !important; }
        .st-key-cp_prod_busca [data-testid="stButtonGroup"] button,
        .st-key-cp_prod_chips [data-testid="stButtonGroup"] button,
        .st-key-cp_prod_subchips [data-testid="stButtonGroup"] button,
        .st-key-cpp_fi_grano [data-testid="stButtonGroup"] button {
            min-height: 24px !important; height: 24px !important;
            padding: 0 8px !important; font-size: 11.5px !important;
        }
        /* El texto va en un `<p>` con su propio cuerpo (14 px): sin esto
           el botón se achica y la letra no, y las familias van en tres
           renglones. */
        .st-key-cp_prod_busca [data-testid="stButtonGroup"] button p,
        .st-key-cp_prod_chips [data-testid="stButtonGroup"] button p,
        .st-key-cp_prod_subchips [data-testid="stButtonGroup"] button p,
        .st-key-cpp_fi_grano [data-testid="stButtonGroup"] button p {
            font-size: 11.5px !important; line-height: 1 !important;
        }
        .st-key-cp_prod_chips [data-testid="stButtonGroup"] > div,
        .st-key-cp_prod_subchips [data-testid="stButtonGroup"] > div { gap: 4px !important; }
        .st-key-cp_prod_subchips [data-testid="stButtonGroup"] > div {
            flex-wrap: nowrap !important; overflow-x: auto; padding-bottom: 3px;
        }
        .st-key-cp_prod_subchips [data-testid="stButtonGroup"] button {
            flex: 0 0 auto !important; max-width: none !important;
        }
        .st-key-cp_prod_busca [data-testid="stElementToolbar"],
        .st-key-cp_prod_chips [data-testid="stElementToolbar"],
        .st-key-cp_prod_subchips [data-testid="stElementToolbar"] { display: none; }
        .st-key-compras_prod_card_ranking [data-testid="stVerticalBlock"] {
            gap: 6px !important;
        }
        .st-key-compras_prod_card_ranking .st-key-cp_prod_fila {
            flex-wrap: wrap !important; row-gap: 4px !important;
        }
"""

_CSS_PRODUCTO = (
    "<style>"
    + clonar_prefijo(CSS_FICHA, "compras_prov_card_ficha",
                     "compras_prod_card_ficha")
    + clonar_prefijo(CSS_FICHA, "cp_ficha_", "cpp_ficha_")
    + clonar_prefijo(CSS_FICHA, "cp_fi_grano", "cpp_fi_grano")
    + clonar_prefijo(CSS_PROVEEDOR, "cp_evo_ctrl", "cpp_evo_ctrl",
                     extra=(("cp_evo_periodo", "compras_prod_periodo"),))
    + _CSS_PROPIO + "</style>")
"""El CSS de la sección. Supone el de Proveedor (`CSS_PROVEEDOR`) en la
página —la fila de la fecha, las pestañas `cp_modo_*`—, que inyecta la
sección de arriba; con la lista vacía se inyecta acá también."""


# ── El ranking (AgGrid) ────────────────────────────────────────────────

_JS_BARRA = JsCode(
    "function(p){"
    " if (p.node.rowPinned) return {'display':'flex','alignItems':'center',"
    " 'justifyContent':'flex-end','fontWeight':'700'};"
    " var sel = p.node.isSelected() || (p.context &&"
    " p.data._raw === p.context.defecto && p.api.getSelectedNodes().length === 0);"
    " var w = Math.max(0, Math.min(100, p.data._barra||0)) * 0.62;"
    f" var c = sel ? '{ACENTO}' : '{LAVANDA_BORDE}';"
    " return {'background': 'linear-gradient(90deg, ' + c + ' 0 ' + w +"
    " '%, transparent ' + w + '% 100%)', 'display':'flex',"
    " 'alignItems':'center','justifyContent':'flex-end',"
    f" 'color':'{TEXTO_PRINCIPAL}'"
    "};}")
_JS_FILA_TOTAL = JsCode(
    "function(p){ if(p.node.rowPinned){ return {"
    f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
    f"'color':'{ACENTO_TEXTO_OSCURO}'"
    "}; } }")
_JS_SOLES = JsCode(
    "function(p){ return p.value==null ? '' :"
    " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
_JS_PCT = JsCode(
    "function(p){ if (p.value==null) return '';"
    " return (p.value >= 10 || p.value === 0 ? Math.round(p.value)"
    " : p.value.toFixed(1)) + '%'; }")
_JS_VAR = JsCode(
    "function(p){ if (p.data && p.data._estado) return p.data._estado;"
    " if (p.value==null) return '—'; var a = Math.abs(p.value);"
    " if (a < 0.05) return '0.0%';"
    " return (p.value > 0 ? '▲ ' : '▼ ') + (a >= 100 ? Math.round(a)"
    " : a.toFixed(1)) + '%'; }")
_JS_HAB = JsCode(
    "function(p){ if (p.value==null) return '—'; var a = Math.abs(p.value);"
    " if (a < 0.05) return '0.0%';"
    " return (p.value > 0 ? '▲ ' : '▼ ') + a.toFixed(1) + '%'; }")
_JS_ENTERO = JsCode(
    "function(p){ return p.value==null ? '' : Math.round(p.value); }")
_REGLAS_VAR = {
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
_REGLAS_HAB = {
    "cp-rk-sube": JsCode(
        "function(p){ return p.value != null && p.value >= 0.5; }"),
    "cp-rk-baja": JsCode(
        "function(p){ return p.value != null && p.value <= -0.5; }"),
}
_REGLAS_FILA = {
    "cp-rank-defecto": JsCode(
        "function(p){ return !!(p.data && p.context &&"
        " p.data._raw === p.context.defecto &&"
        " p.api.getSelectedNodes().length === 0); }"),
}
_JS_TOGGLE = JsCode(
    "function(e){ if (e.node.rowPinned) return;"
    " e.node.setSelected(!e.node.isSelected(), true);"
    " e.api.redrawRows(); }")


def _grilla(filas, total, nombre_col, con_n, defecto, alto, key):
    """El AgGrid del ranking: Producto (o Familia / Subfamilia) | Valor |
    % | Δ | vs. hab. Devuelve la clave `_raw` de la fila elegida o None."""
    cols = [
        {"field": "Nombre", "headerName": nombre_col, "flex": 2.4,
         "minWidth": 110, "tooltipField": "_ayuda_nom"},
        {"field": "Valor", "flex": 1.7, "minWidth": 84,
         "type": "numericColumn",
         "cellStyle": _JS_BARRA, "valueFormatter": _JS_SOLES},
        {"field": "%", "width": 50, "type": "numericColumn",
         "valueFormatter": _JS_PCT, "headerTooltip": filas.attrs.get(
             "ayuda_pct", "")},
    ]
    if con_n:
        cols.append({"field": "n", "headerName": "Prod.", "width": 50,
                     "type": "numericColumn", "valueFormatter": _JS_ENTERO,
                     "headerTooltip": "Productos distintos comprados"})
    cols += [
        {"field": "_var", "headerName": "Δ", "width": 70,
         "type": "numericColumn", "valueFormatter": _JS_VAR,
         "cellClassRules": _REGLAS_VAR, "tooltipField": "_ayuda",
         "headerTooltip": "El valor contra el período anterior de igual largo"},
        {"field": "_hab", "headerName": "vs. hab.", "width": 66,
         "type": "numericColumn", "valueFormatter": _JS_HAB,
         "cellClassRules": _REGLAS_HAB,
         "headerTooltip": "El precio pagado contra el habitual (la mediana de "
                          "los 90 días anteriores), sin las compras marcadas"},
        {"field": "_estado", "hide": True}, {"field": "_ayuda", "hide": True},
        {"field": "_ayuda_nom", "hide": True}, {"field": "_barra", "hide": True},
        {"field": "_raw", "hide": True},
    ]
    resp = AgGrid(
        filas,
        gridOptions={
            "columnDefs": cols,
            "context": {"defecto": defecto or ""},
            "rowClassRules": _REGLAS_FILA,
            "rowSelection": {"mode": "singleRow", "checkboxes": False,
                             "enableClickSelection": False},
            "onRowClicked": _JS_TOGGLE,
            "rowHeight": ALTO_FILA_RANK, "headerHeight": ALTO_HEADER_RANK,
            "suppressCellFocus": True, "suppressMovableColumns": True,
            "tooltipShowDelay": 300,
            "pinnedBottomRowData": [total],
            "getRowStyle": _JS_FILA_TOTAL,
        },
        allow_unsafe_jscode=True, theme="streamlit",
        custom_css=CSS_RANKING_PROV, height=alto,
        update_on=["selectionChanged"], key=key,
    )
    _sel = getattr(resp, "selected_rows", None)
    if _sel is not None and len(_sel):
        _f = _sel.iloc[0] if hasattr(_sel, "iloc") else _sel[0]
        return str(_f["_raw"])
    return None


def _filas_grilla(res, nombres, raws, base_pct, ayudas_nom):
    """El df de la grilla a partir de un `_resumen`."""
    _max = float(res["valor"].max()) if len(res) else 1.0
    df = pd.DataFrame({
        "Nombre": nombres,
        "Valor": res["valor"].astype(float).to_numpy(),
        "%": (res["valor"] / (base_pct or 1.0) * 100).round(1).to_numpy(),
        "n": res["n"].astype(int).to_numpy(),
        "_var": [None if pd.isna(v) else round(float(v), 2)
                 for v in res["var"]],
        "_hab": [None if pd.isna(v) else round(float(v), 2)
                 for v in res["hab"]],
        "_estado": res["est"].to_numpy(),
        "_ayuda": [("Primera compra en este rango" if e == "nuevo" else
                    ("No se compró en el período anterior" if e == "vuelve"
                     else "")) for e in res["est"]],
        "_ayuda_nom": ayudas_nom,
        "_barra": (res["valor"] / (_max or 1.0) * 100).to_numpy(),
        "_raw": raws,
    })
    return df


def _total_grilla(res, n, etiqueta, base_pct, prev_tot):
    _v = float(res["valor"].sum())
    _vr, _rc = float(res["vref"].sum()), float(res["refc"].sum())
    _var = _var_pct(_v, prev_tot) if prev_tot is not None else np.inf
    return {"Nombre": f"Total · {n}{etiqueta}", "Valor": round(_v, 2),
            "%": round(_v / (base_pct or 1.0) * 100, 1),
            "n": int(res["n"].sum()) if "n" in res else None,
            "_var": round(_var, 2) if np.isfinite(_var) else None,
            "_hab": round((_vr / _rc - 1) * 100, 2) if _rc else None}


# ── El drill ───────────────────────────────────────────────────────────


def _aplicar_pendiente():
    """El clic en una familia o subfamilia de la lista llega DESPUÉS de
    dibujar sus botones: deja el pedido acá y un rerun lo aplica antes de
    que vuelvan a dibujarse (un widget no se escribe una vez dibujado)."""
    p = st.session_state.pop("_cp_prod_ir", None)
    if not p:
        return
    st.session_state["cp_prod_ver"] = "prod"
    st.session_state["cp_prod_fam"] = p.get("fam") or _TODAS
    st.session_state["cp_prod_sub"] = p.get("sub") or _TODAS
    st.session_state["compras_prod_q"] = ""
    st.session_state["cp_prod_gclic"] = st.session_state.get("cp_prod_gclic", 0) + 1


def _al_cambiar_familia():
    st.session_state["cp_prod_sub"] = _TODAS


def _al_cambiar_ver():
    if st.session_state.get("cp_prod_ver") == "fam":
        st.session_state["cp_prod_fam"] = _TODAS
        st.session_state["cp_prod_sub"] = _TODAS
    elif st.session_state.get("cp_prod_ver") == "sub":
        st.session_state["cp_prod_sub"] = _TODAS


def _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant, col_punit,
                            col_um, col_fecha, col_prov=None, d_full=None,
                            col_subfam=None, col_docu=None):
    """Dashboard de Producto: el ranking y la ficha del producto elegido.
    Ver el docstring del módulo y `arquitectura.md` regla #653.

    La firma es la de antes, con `col_punit` sin usar (el precio sale de
    valor ÷ cantidad) y los opcionales al final: en Cloud un commit que le
    cambia el orden a algo ya importado deja el `app.py` nuevo hablando con
    el paquete viejo (regla #357)."""
    # La escalada del selector de fecha: el filtro que lee el rango vive en
    # app.py, FUERA de este fragment (regla #180), con `preservar_widgets`
    # porque el rerun aborta acá (#373).
    if st.session_state.pop("_cp_prod_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")
    if not (col_prod and col_valor and col_fecha):
        st.info("Faltan columnas (Producto, Valor o Fecha) para este gráfico.")
        return
    _aplicar_pendiente()
    cols = (col_prod, col_fam, col_subfam, col_valor, col_cant, col_um,
            col_fecha, col_prov, col_docu)
    b_rng = _normalizar(d, *cols)
    if b_rng.empty or b_rng["valor"].sum() == 0:
        # SIN FILAS SE VACÍA EL CONTENIDO, NO LA VISTA (regla #354): la
        # tarjeta se dibuja con su selector de fecha, que es la salida.
        st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)
        st.markdown(_CSS_PRODUCTO, unsafe_allow_html=True)
        with st.container(border=True, key="compras_prod_card_vacio"):
            selector_fecha_tarjeta(
                "cp_prod", "_cp_prod_atajo_pendiente",
                titulo_html='<div class="cp-prod-rank-tit">Ranking de '
                            'productos</div>',
                categoria=CATEGORIA_SEC["compras_sec_producto"])
            st.info("Sin compras en el rango seleccionado. Ampliá el rango "
                    "desde la fecha de la cabecera.")
        return
    hist = _normalizar(d_full, *cols) if d_full is not None else b_rng
    _rango = rango_tarjeta(CATEGORIA_SEC["compras_sec_producto"])
    if _rango is None or any(x is None for x in _rango):
        _rango = (b_rng["fecha"].min(), b_rng["fecha"].max())
    r0 = pd.Timestamp(_rango[0]).normalize()
    r1 = pd.Timestamp(_rango[1]).normalize()
    dias = (r1 - r0).days + 1
    ultimo = hist["fecha"].max()

    # El precio habitual y la marca de cada línea del rango: la mediana se
    # toma de los 90 días ANTERIORES a cada compra, así que entran al
    # cálculo los 90 días previos al rango (y después se descartan).
    _ant90 = hist[(hist["fecha"] >= r0 - pd.Timedelta(days=90))
                  & (hist["fecha"] < r0)]
    _x = _con_referencia(pd.concat([_ant90.assign(_en=False),
                                    b_rng.assign(_en=True)],
                                   ignore_index=True))
    rng = _x[_x["_en"]].drop(columns="_en").reset_index(drop=True)
    prev = hist[(hist["fecha"] >= r0 - pd.Timedelta(days=dias))
                & (hist["fecha"] < r0)]
    antes = hist[hist["fecha"] < r0]

    res_p = _resumen(rng, ["prod"], prev, antes["prod"].unique())
    res_p["um"] = (moda_por_grupo(rng[rng["um"] != ""][["prod", "um"]],
                                  "prod", "um").reindex(res_p.index)
                   .fillna("").map(_um_corta))
    res_p["fam"] = rng.groupby("prod")["fam"].first().reindex(res_p.index)
    res_p["sub"] = rng.groupby("prod")["sub"].first().reindex(res_p.index)
    res_p["ultp"] = _ultimo_precio(rng).reindex(res_p.index)
    res_p["cada"] = _cada_cuanto(
        hist[(hist["fecha"] > r1 - pd.Timedelta(days=90))
             & (hist["fecha"] <= r1)]).reindex(res_p.index)
    res_f = _resumen(rng, ["fam"], prev, antes["fam"].unique())
    res_s = _resumen(rng, ["fam", "sub"], prev,
                     list(antes[["fam", "sub"]].drop_duplicates()
                          .itertuples(index=False, name=None)))
    _tot = float(res_p["valor"].sum()) or 1.0
    _acum = res_p["valor"].cumsum() / _tot * 100
    _n80 = int((_acum < 80).sum() + 1)
    _nflag = int((res_p["nflag"] > 0).sum())

    # ── Los controles de la lista, validados ANTES de dibujarlos ──────────
    _fams = list(res_f.index)
    if st.session_state.get("cp_prod_ver") not in (None, *_VER):
        del st.session_state["cp_prod_ver"]
    if st.session_state.get("cp_prod_fam") not in (None, _TODAS, *_fams):
        st.session_state["cp_prod_fam"] = _TODAS
    ver = st.session_state.get("cp_prod_ver") or "prod"
    fam = st.session_state.get("cp_prod_fam") or _TODAS
    fam = None if fam == _TODAS else fam
    _subs = (list(res_s.loc[fam].index) if fam is not None
             and fam in res_s.index.get_level_values(0) else [])
    if st.session_state.get("cp_prod_sub") not in (None, _TODAS, *_subs):
        st.session_state["cp_prod_sub"] = _TODAS
    sub = st.session_state.get("cp_prod_sub") or _TODAS
    sub = None if (sub == _TODAS or ver != "prod" or fam is None) else sub
    q = str(st.session_state.get("compras_prod_q") or "").strip()

    # ── El ámbito y la lista ──────────────────────────────────────────────
    amb = _ambito(res_p, fam, sub)
    vis = amb[_coincide(pd.Series(amb.index, index=amb.index), q)] if q \
        else amb
    foco = st.session_state.get("compras_prod_focus")
    if foco not in set(vis.index):
        foco = None
    prod_sel = foco or (vis.index[0] if len(vis) else
                        (amb.index[0] if len(amb) else res_p.index[0]))

    st.markdown(_CSS_PRODUCTO, unsafe_allow_html=True)
    with st.container(key="compras_prod_marco"):
        _c_rank, _c_ficha = st.columns(COLUMNAS_DRILL_FICHA, gap=GAP_DRILL)

        # ═══ RANKING ════════════════════════════════════════════════════
        with _c_rank:
            with st.container(border=True, key="compras_prod_card_ranking"):
                selector_fecha_tarjeta(
                    "cp_prod", "_cp_prod_atajo_pendiente",
                    titulo_html='<div class="cp-prod-rank-tit">Ranking de '
                                'productos</div>',
                    categoria=CATEGORIA_SEC["compras_sec_producto"])
                with st.container(key="cp_prod_busca"):
                    st.text_input("Buscar", key="compras_prod_q",
                                  placeholder="Buscar…",
                                  label_visibility="collapsed")
                    st.segmented_control(
                        "Ver por", list(_VER), key="cp_prod_ver",
                        default=None if "cp_prod_ver" in st.session_state
                        else "prod", required=True,
                        format_func=_VER.get, on_change=_al_cambiar_ver,
                        label_visibility="collapsed")
                if ver != "fam":
                    with st.container(key="cp_prod_chips"):
                        st.pills(
                            "Familia", [_TODAS] + _fams, key="cp_prod_fam",
                            default=None if "cp_prod_fam" in st.session_state
                            else _TODAS, required=True,
                            format_func=lambda o: ("Todas" if o == _TODAS
                                                   else _sin_gritar(o)),
                            on_change=_al_cambiar_familia,
                            label_visibility="collapsed")
                if ver == "prod" and fam is not None and _subs:
                    with st.container(key="cp_prod_subchips"):
                        st.pills(
                            "Subfamilia", [_TODAS] + _subs, key="cp_prod_sub",
                            default=None if "cp_prod_sub" in st.session_state
                            else _TODAS, required=True,
                            format_func=lambda o: (
                                "Todas" if o == _TODAS else _sin_gritar(o)),
                            label_visibility="collapsed")

                _filas_rk = _FILAS_RANK - (2 if ver == "prod" and fam is not None
                                           and _subs else 0)
                _alto_rk = alturas.por_filas(
                    _filas_rk, px_fila=ALTO_FILA_RANK,
                    extra=CROMO_GRID_RANK + ALTO_FILA_RANK, minimo=0)
                _amb_v = float(amb["valor"].sum()) or 1.0
                if ver == "prod":
                    _prev_amb = prev
                    if fam is not None:
                        _prev_amb = _prev_amb[_prev_amb["fam"] == fam]
                    if sub is not None:
                        _prev_amb = _prev_amb[_prev_amb["sub"] == sub]
                    filas = _filas_grilla(
                        vis, [("⚠ " if n_ else "") + p for p, n_
                              in zip(vis.index, vis["nflag"])],
                        list(vis.index), _amb_v,
                        [p + (" · tiene una compra para revisar" if n_ else "")
                         for p, n_ in zip(vis.index, vis["nflag"])])
                    _ayuda_pct = (f"% sobre {_sin_gritar(sub or fam)}"
                                  if fam is not None else
                                  "% sobre el total comprado en el rango")
                    total = _total_grilla(
                        vis, len(vis), f" de {len(res_p)}" if len(vis) != len(res_p)
                        else "", _amb_v,
                        None if q else float(_prev_amb["valor"].sum()))
                    _k = ("compras_prod_rank_"
                          + _clave_grilla(fam or "", sub or "", _sin_tildes(q)))
                    nombre_col, defecto = "Producto", prod_sel
                else:
                    if ver == "fam":
                        rg = res_f
                        nombres = [_sin_gritar(f) for f in rg.index]
                        raws = list(rg.index)
                        ayudas = nombres
                        base_pct = _tot
                        _ayuda_pct = "% sobre el total comprado en el rango"
                        _cur = res_p.at[prod_sel, "fam"]
                    else:
                        rg = res_s if fam is None else res_s.loc[[fam]]
                        rg = rg.sort_values("valor", ascending=False,
                                            kind="stable")
                        nombres = [_sin_gritar(s) for _f, s in rg.index]
                        raws = [f"{_f}\x1f{s}" for _f, s in rg.index]
                        ayudas = [f"{_sin_gritar(s)} · {_sin_gritar(_f)}"
                                  for _f, s in rg.index]
                        base_pct = (_tot if fam is None
                                    else float(res_f.at[fam, "valor"]))
                        _ayuda_pct = (f"% sobre {_sin_gritar(fam)}" if fam
                                      else "% sobre el total comprado en el rango")
                        _cur = (f"{res_p.at[prod_sel, 'fam']}\x1f"
                                f"{res_p.at[prod_sel, 'sub']}")
                    if q:
                        _m = _coincide(pd.Series(nombres, index=rg.index), q)
                        rg = rg[_m.to_numpy()]
                        nombres = [x for x, m in zip(nombres, _m) if m]
                        raws = [x for x, m in zip(raws, _m) if m]
                        ayudas = [x for x, m in zip(ayudas, _m) if m]
                    filas = _filas_grilla(rg, nombres, raws, base_pct, ayudas)
                    _prev_g = float(rg["prev"].sum())
                    total = _total_grilla(rg, len(rg), "", base_pct,
                                          None if q else _prev_g)
                    _k = ("compras_prod_grupo_" + ver + "_"
                          + _clave_grilla(fam or "", _sin_tildes(q),
                                          st.session_state.get("cp_prod_gclic", 0)))
                    nombre_col = _VER[ver]
                    defecto = _cur
                filas.attrs["ayuda_pct"] = _ayuda_pct
                _clic = _grilla(filas, total, nombre_col, ver != "prod",
                                defecto, _alto_rk, _k)
                if ver == "prod":
                    st.markdown(
                        f'<div class="cp-rank-pie">{_n80} productos hacen el '
                        f'80 % de lo comprado · <span class="cpp-warn">⚠</span>'
                        f' {_nflag} con una compra para revisar</div>',
                        unsafe_allow_html=True)
                    if _clic != foco:
                        st.session_state["compras_prod_focus"] = _clic
                        st.session_state["cp_prod_per"] = None
                        st.session_state["cp_prod_cprov"] = None
                        prod_sel = _clic or prod_sel
                        if _clic is None:
                            prod_sel = (vis.index[0] if len(vis)
                                        else prod_sel)
                else:
                    st.markdown(
                        '<div class="cp-rank-pie">Clic en una '
                        f'{"familia" if ver == "fam" else "subfamilia"}: sus '
                        'productos · Δ contra el período anterior</div>',
                        unsafe_allow_html=True)
                    if _clic is not None:
                        _f, _, _s = _clic.partition("\x1f")
                        st.session_state["_cp_prod_ir"] = {
                            "fam": _f, "sub": _s or None}
                        preservar_widgets(_KEYS_FICHA)
                        st.rerun(scope=scope_rerun())

        # ═══ FICHA ══════════════════════════════════════════════════════
        with _c_ficha:
            with st.container(border=True, key="compras_prod_card_ficha"):
                _ficha(prod_sel, res_p.loc[prod_sel], hist, (r0, r1), ultimo,
                       dias)


def _ficha(prod, fila, hist, rango, ultimo, dias):
    """La ficha del producto: cabecera, cifras del rango, curva y las
    pestañas Proveedores | Compras | Períodos."""
    um = fila["um"] or ""
    h = _con_referencia(hist[hist["prod"] == prod].reset_index(drop=True))
    r0, r1 = rango

    # ── Cabecera: nombre, ventana y grano ────────────────────────────────
    if st.session_state.get("cp_prod_gran") not in (None, *_GRANOS):
        del st.session_state["cp_prod_gran"]
    gran = st.session_state.get("cp_prod_gran") or "Mes"
    with st.container(key="cpp_ficha_cab"):
        st.markdown(f'<div class="cp-fi-nom" title="{_esc(prod)}">'
                    f'{_esc(_compras_truncar(prod, 44))}</div>',
                    unsafe_allow_html=True)
        with st.container(key="cpp_evo_ctrl"):
            op = periodo.selector(
                "compras_prod_periodo", default="3m", widget="lista",
                format_func=lambda o: ("Rango de las tablas"
                                       if o == periodo.HEREDA else
                                       ("Todo el histórico" if o == "Todo"
                                        else f"Últimos {o[:-1]} meses")))
        with st.container(key="cpp_fi_grano"):
            st.segmented_control(
                "Grano", list(_GRANOS), key="cp_prod_gran",
                default=None if "cp_prod_gran" in st.session_state else "Mes",
                required=True,
                format_func=lambda g: "Doc." if g == "Documento" else g,
                label_visibility="collapsed")
    _sub = [_sin_gritar(fila["sub"]), _sin_gritar(fila["fam"])]
    if pd.notna(fila["ult"]):
        _u = f"última compra {_fecha_corta(fila['ult'])}"
        if pd.notna(fila["ultp"]):
            _u += f" a {_precio(fila['ultp'])} / {um or 'unidad'}"
        if pd.notna(fila["cada"]):
            _c = int(round(fila["cada"]))
            _u += f", cada {_c} {'día' if _c == 1 else 'días'}"
        _sub.append(_u)
    _n = int(fila["docs"])
    _sub.append(f"{_n} {'compra' if _n == 1 else 'compras'} en el rango")
    st.markdown(f'<div class="cpp-sub" title="{_esc(" · ".join(_sub))}">'
                f'{_esc(" · ".join(_sub))}</div>', unsafe_allow_html=True)

    # ── Las cifras del rango ─────────────────────────────────────────────
    _ant = (f"{(r0 - pd.Timedelta(days=dias)):%d/%m} – "
            f"{(r0 - pd.Timedelta(days=1)):%d/%m}")
    st.markdown(_html_kpis(fila, um, dias, _ant), unsafe_allow_html=True)

    # ── La curva ─────────────────────────────────────────────────────────
    S = _serie(h, gran, op, ultimo, rango)
    if S is None:
        st.info("Sin compras de este producto en «"
                + ("el rango" if op == periodo.HEREDA else
                   periodo.etiqueta(op) or "la ventana") + "».")
        return
    keys = S["keys"]
    per = st.session_state.get("cp_prod_per")
    if per not in keys:
        per = None
    st.session_state["cp_prod_per"] = per
    # EL CLIC EN UNA BARRA, ANTES DE DIBUJARLA (regla #399): la selección
    # persiste mientras la key no cambie, así que se lee la key dibujada la
    # vez pasada y el contador sube en esta misma corrida. Y va antes de
    # las pestañas porque puede cambiarlas: en Proveedores acota los
    # proveedores a esa barra; en las otras dos abre sus compras.
    _base = f"cp_prod_curva_{zlib.crc32(f'{prod}|{gran}|{op}'.encode()):08x}"
    _nclic = st.session_state.get("cp_prod_nclic", 0)
    _pt = _first_point(st.session_state.get(f"{_base}_{_nclic}"))
    if _pt is not None:
        _nclic += 1
        st.session_state["cp_prod_nclic"] = _nclic
        _kx = str(_pt.get("x")) if _pt.get("x") is not None else None
        if _kx in keys:
            per = None if per == _kx else _kx
            st.session_state["cp_prod_per"] = per
            st.session_state["cp_prod_cprov"] = None
            if st.session_state.get("cp_prod_tab", "prov") == "prov":
                st.session_state["cp_prod_pw"] = "ven"
            else:
                st.session_state["cp_prod_tab"] = "comp"
    st.plotly_chart(_fig_producto(S, gran, um, per), width="stretch",
                    on_select="rerun", selection_mode="points",
                    key=f"{_base}_{_nclic}",
                    config={"displayModeBar": False})

    # ── La leyenda ───────────────────────────────────────────────────────
    _ley = [f'<span><i class="bar"></i>{_esc(um or "unidades")} comprados</span>',
            '<span><i class="lin"></i>precio ponderado</span>',
            '<span><i class="hab"></i>precio habitual</span>']
    if S["agg"]["fl"].any():
        _ley.append('<span><i class="mar"></i>con compras para revisar</span>')
    _p = S["parc"]
    if _p is not None and (float(S["agg"]["c"].iat[-1]) or S["refq"]):
        _ult = float(S["agg"]["c"].iat[-1])
        _ley.append(f'<span>{_esc(_p["rot"])}: {_esc(_cant(_ult, um))} · '
                    f'<i class="raya"></i>{_esc(_p["rot_ref"])}: '
                    f'{_esc(_cant(S["refq"], um))} <b class="var">'
                    f'{_fmt_var(_var_pct(_ult, S["refq"]))}</b></span>')
    st.markdown('<div class="cpp-ley">' + "".join(_ley) + "</div>",
                unsafe_allow_html=True)

    # ── Los ámbitos de las pestañas ──────────────────────────────────────
    if st.session_state.get("cp_prod_tab") not in (None, *_TABS):
        del st.session_state["cp_prod_tab"]
    if st.session_state.get("cp_prod_pw") not in (None, *_PW):
        del st.session_state["cp_prod_pw"]
    tab = st.session_state.get("cp_prod_tab") or "prov"
    pw = st.session_state.get("cp_prod_pw") or "90"
    lin = S["lineas"]
    bsel = lin[lin["k"] == per] if per else None
    if pw == "ven":
        Lp = bsel if bsel is not None else lin
    else:
        _p0 = r0 if pw == "rango" else r1 - pd.Timedelta(days=89)
        Lp = h[(h["fecha"] >= _p0) & (h["fecha"] <= r1)]
    cprov = st.session_state.get("cp_prod_cprov")
    if cprov is not None and cprov not in set(h["prov"]):
        cprov = None
    if bsel is not None:
        Lc = bsel
    elif cprov is not None:
        Lc = Lp
    else:
        Lc = h[(h["fecha"] >= r0) & (h["fecha"] <= r1)]
    if cprov is not None:
        Lc = Lc[Lc["prov"] == cprov]
    _ven = (_etq(per, gran, largo=True) if per else "La curva")
    _alto = (_FILAS_LISTA - 1) * _ALTO_FILA
    _html_pv, _npv = _html_proveedores(Lp, um, _alto)
    _html_cp, _ncp = _html_compras(Lc, um, _alto)

    # ── Pestañas ─────────────────────────────────────────────────────────
    with st.container(key="cpp_ficha_tabs"):
        with st.container(key="cp_modo_ptab"):
            tab = st.pills(
                "Ver", list(_TABS), key="cp_prod_tab",
                default=None if "cp_prod_tab" in st.session_state else "prov",
                required=True,
                format_func=lambda o: {"prov": f"Proveedores · {_npv}",
                                       "comp": f"Compras · {_ncp}",
                                       "per": f"Períodos · {len(keys)}"}[o],
                label_visibility="collapsed") or "prov"
        if tab == "prov":
            with st.container(key="cpp_pw_fila"):
                st.markdown('<div class="cp-modo-nota">comparar en</div>',
                            unsafe_allow_html=True)
                with st.container(key="cp_modo_ppw"):
                    st.pills(
                        "Ámbito de los proveedores", list(_PW),
                        key="cp_prod_pw",
                        default=None if "cp_prod_pw" in st.session_state
                        else "90", required=True,
                        format_func=lambda o: {"rango": "El rango",
                                               "90": "90 días",
                                               "ven": _ven}[o],
                        label_visibility="collapsed")
        elif tab == "comp":
            if per or cprov is not None:
                _t = " · ".join(x for x in (
                    _etq(per, gran, largo=True) if per else "",
                    nombre_propio(cprov) if cprov is not None else "",
                    "" if per or cprov is None else
                    {"rango": "el rango", "90": "90 días",
                     "ven": "la curva"}[pw]) if x)
                st.button(f"{_compras_truncar(_t, 46)} ✕", key="cp_prod_soltar",
                          type="tertiary", on_click=_soltar)
            else:
                st.markdown('<div class="cp-modo-nota">del rango · clic en una '
                            'barra: ese período</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="cp-modo-nota">una fila por barra de la '
                        'curva · clic: sus compras</div>',
                        unsafe_allow_html=True)

    st.text_input("Acción", key=_K_RELEVO, label_visibility="collapsed",
                  on_change=_relevo)
    if tab == "prov":
        _html = _html_pv
    elif tab == "comp":
        _html = _html_cp
    else:
        _html = _html_periodos(S, gran, um, _alto, per)
    _k = zlib.crc32(_html.encode("utf-8"))
    with st.container(key=f"cpp_fi_tabla_{_k:08x}"):
        st.markdown(_html, unsafe_allow_html=True)
    inyectar_html(_JS_CLIC)
