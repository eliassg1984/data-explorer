"""graficos.compras.producto - drill de Producto.

Desde el 2026-10-23 es una PIEZA PROPIA (regla #713): `producto.js` +
`producto.css`, montada dos veces —una en cada tarjeta— con el mismo cerebro
en el navegador, como «Análisis por hora» (#704). Es la forma del boceto
aprobado con sus cinco mejoras
(https://claude.ai/artifact/1fymSPwVmqUtpQLnjzRB9m, página «Compras ›
Producto: pieza propia»):

    [ Ranking de productos   ][ Ficha del producto elegido                ]
    [ fecha (Python)         ][  nombre · ventana · grano                 ]
    [ buscar · Ver por       ][  cifras del rango                         ]
    [ ⚠ para revisar · Excel ][  curva: cantidad en barras, precio línea  ]
    [ familias, subfamilias  ][  Proveedores | Compras | Períodos         ]
    [ lista con su curva 12m ][  (clic en una compra: el comprobante)     ]

Hasta ese día cada clic era una corrida de 2,5 a 4,4 s (medido en la laptop
con R2); ahora sólo la fecha del ranking vuelve a Python. Las cuentas son
las de la regla #653, que siguen escritas ACÁ (`_resumen`, `_serie`,
`_precios`) y el navegador las rehace con las mismas fórmulas: si se toca
una, se toca la otra (lo vigila `test_producto_pieza.py`).

Lo que manda Python, partido en dos para que cambiar la fecha no vuelva a
mandar el historial:

- la tarjeta de la FICHA (`historial_pieza`): cada línea de compra del
  historial, de TODOS los productos de los filtros, con su precio habitual
  y su marca. Depende sólo del historial: con la misma `sello`, Streamlit
  no vuelve a mandar el mensaje (el navegador lo tiene guardado).
- la del RANKING (`armar_ranking`): el resumen del rango por producto,
  familia y subfamilia, que depende de la fecha.

Dos reglas que la maqueta de la #653 midió y la vista cumple en todos lados:

- UN SOLO PRECIO, el PONDERADO (soles ÷ cantidad; el costo promedio
  ponderado de la NIC 2, §25). La barra de antes promediaba las facturas
  sin pesar: lomo fino de setiembre decía S/ 67,17 arriba y S/ 70,80 en la
  tabla de abajo. Pasaba en 728 de 4.007 producto-mes.
- LAS COMPRAS MARCADAS «revisar» (`marcar_revisar`) no entran en ningún
  PRECIO; sí en la cantidad y el valor, que es lo que se registró. Sin eso
  el lomo fino mostraba un «ahorro» de S/ 861 que era, entero, una compra
  cargada a S/ 15,85 el kilo.
"""

from graficos.movil import css_movil, js_movil
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from cortes import MESES_ABR_ES
from graficos.base import preservar_widgets, rango_tarjeta
from graficos.compras._comun import (
    CATEGORIA_SEC, COLUMNAS_DRILL_FICHA, GAP_DRILL, documento_legible,
    inicio_de_periodo, moda_por_grupo, selector_fecha_tarjeta, tramo_parcial,
    unidad_corta,
)
from graficos.compras._css_proveedor import CSS as CSS_PROVEEDOR
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras.semanal import precio_habitual
from graficos import alturas, periodo


_KEYS_WIDGET = ()
"""Los controles de esta sección que la escalada de la fecha tendría que
preservar (regla #373). Ninguno desde la pieza propia: lo que se elige en
la lista y en la ficha vive en el navegador (`window.__cpProd`), no en
widgets. La guarda de `test_graficos.py` lee esta tupla con
`ast.literal_eval`."""

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

_FLAGS = ("", "um", "precio")
"""La marca de una línea como número para la pieza (posición en esta
tupla): «» sin marca, «um» unidad entera con decimales, «precio»."""


# ── Formato ────────────────────────────────────────────────────────────


def _um_corta(um):
    s = str(um or "").strip()
    return "" if s.lower() in ("", "nan", "none") else unidad_corta(s)


def _fecha_corta(f):
    f = pd.Timestamp(f)
    return f"{f.day} {MESES_ABR_ES[f.month - 1]}"


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


# ── Lo que recibe la pieza ─────────────────────────────────────────────


def _num(v, dec):
    """Un número para el JSON: redondeado, o None si no hay."""
    if v is None or pd.isna(v) or not np.isfinite(float(v)):
        return None
    return round(float(v), dec)


def _iso(v):
    return None if v is None or pd.isna(v) else f"{pd.Timestamp(v):%Y-%m-%d}"


def sello_historial(hist):
    """La identidad del historial que recibe la pieza: cambia si cambia una
    línea (otro parquet, otros filtros de familia). Las dos tarjetas la
    llevan y el navegador sólo junta datos con la MISMA."""
    if hist.empty:
        return "0"
    _h = pd.util.hash_pandas_object(
        hist[["prod", "fecha", "valor", "cant", "prov", "docu"]], index=False)
    return f"{len(hist)}-{int(_h.sum()) & 0xFFFFFFFFFFFF:x}"


def historial_pieza(hist, sello):
    """El historial con su precio habitual y su marca (`h_ref`, para el
    resumen del rango) y lo que recibe la tarjeta de la FICHA. Pura.

    Fila de una línea (en `lineas[i]`, las del producto `nombres[i]`, de
    la más vieja a la más nueva): [día (desde `base`), proveedor (índice de
    `provs`), documento (índice de `docs`), cantidad, valor, precio
    habitual o None, marca (índice de `_FLAGS`)].

    Van TODOS los productos de los filtros y no sólo los del rango: la
    curva llega hasta «Todo el histórico» y el comprobante de una compra
    lleva sus otras líneas."""
    h = _con_referencia(hist.reset_index(drop=True))
    nombres = sorted(h["prod"].unique())
    provs = sorted(h["prov"].unique())
    docs = sorted(h["docu"].unique())
    base = h["fecha"].min() if len(h) else pd.Timestamp("2000-01-01")
    um = (moda_por_grupo(h[h["um"] != ""][["prod", "um"]], "prod", "um")
          .reindex(nombres).fillna("").map(_um_corta))
    x = h.assign(
        _i=pd.Categorical(h["prod"], categories=nombres).codes,
        _p=pd.Categorical(h["prov"], categories=provs).codes,
        _d=pd.Categorical(h["docu"], categories=docs).codes,
        _f=pd.Categorical(h["flag"], categories=_FLAGS).codes,
    ).sort_values(["_i", "fecha"], kind="stable")
    filas = [[int(d), int(p), int(dc), c, v, (None if r != r else r), int(f)]
             for d, p, dc, c, v, r, f in zip(
                 (x["fecha"] - base).dt.days.tolist(), x["_p"].tolist(),
                 x["_d"].tolist(), np.round(x["cant"], 3).tolist(),
                 np.round(x["valor"], 2).tolist(), np.round(x["ref"], 4).tolist(),
                 x["_f"].tolist())]
    cortes = np.cumsum(np.bincount(x["_i"].to_numpy(), minlength=len(nombres)))
    lineas = [filas[a:b] for a, b in zip(np.r_[0, cortes[:-1]], cortes)]
    _con = [x for x in docs if x]
    _leg = dict(zip(_con, documento_legible(pd.Series(_con, dtype=object))
                    if _con else []))
    payload = {
        "parte": "ficha", "sello": sello, "base": _iso(base),
        "nombres": nombres, "um": um.tolist(),
        "provs": [nombre_propio(p) for p in provs],
        "docs": [str(_leg.get(x, "")) for x in docs],
        "lineas": lineas, "alto_curva": alturas.CURVA_FICHA,
    }
    return h, payload


def armar_ranking(res_p, res_f, res_s, nombres, rango, ultimo, prev_total,
                  n80, nflag, sello):
    """Lo que recibe la tarjeta del RANKING: el resumen del rango. Pura.

    Producto (`prods`): [índice en `nombres` de la ficha, familia,
    subfamilia, unidad, valor, cantidad, Δ %, «nuevo»/«vuelve»/«», precio
    ponderado, vs. habitual %, impacto del precio, líneas marcadas,
    compras, última compra, su precio, cada cuántos días, valor del período
    anterior, valor y cantidad × habitual de las líneas con habitual].
    Familia (`fams`) y subfamilia (`subs`, con la familia adelante): valor,
    anterior, Δ %, estado, vs. habitual %, productos, marcadas y los dos
    del habitual."""
    pos = {p: i for i, p in enumerate(nombres)}
    r0, r1 = rango

    def _grupo(r):
        return [_num(r["valor"], 2), _num(r["prev"], 2), _num(r["var"], 3),
                r["est"], _num(r["hab"], 3), int(r["n"]), int(r["nflag"]),
                _num(r["vref"], 2) or 0, _num(r["refc"], 2) or 0]

    return {
        "parte": "rank", "sello": sello,
        "rango": [_iso(r0), _iso(r1)], "dias": int((r1 - r0).days + 1),
        "ultimo": _iso(ultimo), "n80": int(n80), "nflag": int(nflag),
        "prev_total": _num(prev_total, 2) or 0,
        "prods": [[pos[p], r["fam"], r["sub"], r["um"] or "",
                   _num(r["valor"], 2), _num(r["cant"], 3), _num(r["var"], 3),
                   r["est"], _num(r["pp"], 4), _num(r["hab"], 3),
                   _num(r["ppv"], 2), int(r["nflag"]), int(r["docs"]),
                   _iso(r["ult"]), _num(r["ultp"], 4), _num(r["cada"], 1),
                   _num(r["prev"], 2), _num(r["vref"], 2) or 0,
                   _num(r["refc"], 2) or 0]
                  for p, r in res_p.iterrows()],
        "fams": [[f, *_grupo(r)] for f, r in res_f.iterrows()],
        "subs": [[f, s, *_grupo(r)] for (f, s), r in res_s.iterrows()],
        "nomf": {f: _sin_gritar(f) for f in set(res_p["fam"]) | set(res_f.index)},
        "noms": {s: _sin_gritar(s) for s in set(res_p["sub"])
                 | {s2 for _f, s2 in res_s.index}},
    }


# ── La pieza propia (regla #713) ───────────────────────────────────────
_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "compras_producto",
    css=css_movil((_AQUI / "producto.css").read_text(encoding="utf-8")),
    # El Excel (`libro`, `bajar`, `archivo`) vive en `_xlsx.js`, compartido
    # con Costo de Carta y Consistencia: se antepone.
    js=js_movil((_AQUI.parent / "_xlsx.js").read_text(encoding="utf-8")
    + (_AQUI / "producto.js").read_text(encoding="utf-8")),
)

_K_RANK = "cp_prod_pieza_rank"
_K_FICHA = "cp_prod_pieza_ficha"
_K_HIST = "_cp_prod_hist"
"""El historial ya referenciado de la última corrida, con su `sello`:
`_con_referencia` sobre 45 mil líneas son 0,5 s, y sólo cambia con el
parquet o los filtros de familia, no con la fecha."""


def _historial(hist):
    sello = sello_historial(hist)
    _g = st.session_state.get(_K_HIST)
    if _g is None or _g[0] != sello:
        h, payload = historial_pieza(hist, sello)
        _g = (sello, h, payload)
        st.session_state[_K_HIST] = _g
    return _g


# ── El drill ───────────────────────────────────────────────────────────


def _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant, col_punit,
                            col_um, col_fecha, col_prov=None, d_full=None,
                            col_subfam=None, col_docu=None):
    """Dashboard de Producto: el ranking y la ficha del producto elegido,
    una pieza propia en cada tarjeta. Ver el docstring del módulo y
    `arquitectura.md` reglas #653 y #713.

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
    cols = (col_prod, col_fam, col_subfam, col_valor, col_cant, col_um,
            col_fecha, col_prov, col_docu)
    b_rng = _normalizar(d, *cols)
    if b_rng.empty or b_rng["valor"].sum() == 0:
        # SIN FILAS SE VACÍA EL CONTENIDO, NO LA VISTA (regla #354): la
        # tarjeta se dibuja con su selector de fecha, que es la salida.
        st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)
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
    sello, h_ref, payload_ficha = _historial(hist)
    _rango = rango_tarjeta(CATEGORIA_SEC["compras_sec_producto"])
    if _rango is None or any(x is None for x in _rango):
        _rango = (b_rng["fecha"].min(), b_rng["fecha"].max())
    r0 = pd.Timestamp(_rango[0]).normalize()
    r1 = pd.Timestamp(_rango[1]).normalize()
    dias = (r1 - r0).days + 1
    ultimo = h_ref["fecha"].max()

    # El precio habitual y la marca de cada línea salen del historial
    # entero: la mediana se toma de los 90 días ANTERIORES a cada compra,
    # así que da lo mismo que pedirla sobre el rango con sus 90 días.
    rng = h_ref[(h_ref["fecha"] >= r0) & (h_ref["fecha"] <= r1)]
    prev = h_ref[(h_ref["fecha"] >= r0 - pd.Timedelta(days=dias))
                 & (h_ref["fecha"] < r0)]
    antes = h_ref[h_ref["fecha"] < r0]

    res_p = _resumen(rng, ["prod"], prev, antes["prod"].unique())
    res_p["um"] = (moda_por_grupo(rng[rng["um"] != ""][["prod", "um"]],
                                  "prod", "um").reindex(res_p.index)
                   .fillna("").map(_um_corta))
    res_p["fam"] = rng.groupby("prod")["fam"].first().reindex(res_p.index)
    res_p["sub"] = rng.groupby("prod")["sub"].first().reindex(res_p.index)
    res_p["ultp"] = _ultimo_precio(rng).reindex(res_p.index)
    res_p["cada"] = _cada_cuanto(
        h_ref[(h_ref["fecha"] > r1 - pd.Timedelta(days=90))
              & (h_ref["fecha"] <= r1)]).reindex(res_p.index)
    res_f = _resumen(rng, ["fam"], prev, antes["fam"].unique())
    res_s = _resumen(rng, ["fam", "sub"], prev,
                     list(antes[["fam", "sub"]].drop_duplicates()
                          .itertuples(index=False, name=None)))
    _tot = float(res_p["valor"].sum()) or 1.0
    _n80 = int((res_p["valor"].cumsum() / _tot * 100 < 80).sum() + 1)
    _nflag = int((res_p["nflag"] > 0).sum())
    ranking = armar_ranking(res_p, res_f, res_s, payload_ficha["nombres"],
                            (r0, r1), ultimo, float(prev["valor"].sum()),
                            _n80, _nflag, sello)

    with st.container(key="compras_prod_marco"):
        _c_rank, _c_ficha = st.columns(COLUMNAS_DRILL_FICHA, gap=GAP_DRILL)
        with _c_rank:
            with st.container(border=True, key="compras_prod_card_ranking"):
                selector_fecha_tarjeta(
                    "cp_prod", "_cp_prod_atajo_pendiente",
                    titulo_html='<div class="cp-prod-rank-tit">Ranking de '
                                'productos</div>',
                    categoria=CATEGORIA_SEC["compras_sec_producto"])
                _PIEZA(key=_K_RANK, data=ranking, width="stretch")
        with _c_ficha:
            with st.container(border=True, key="compras_prod_card_ficha"):
                _PIEZA(key=_K_FICHA, data=payload_ficha, width="stretch")
