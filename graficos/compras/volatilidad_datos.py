"""Contrato de Volatilidad: líneas en soles, sin mezclar unidades (#718).

El navegador recibe también el histórico previo al rango: el primer cierre
y la comparación de igual duración necesitan esa base. No se redondea a
céntimos por línea, ni se funden compras del mismo día.
"""
import hashlib
import json

import numpy as np
import pandas as pd

from graficos import periodo
from graficos.compras._comun import documento_legible, unidad_corta
from graficos.compras._etiquetas_proveedor import nombre_propio


def normalizar(d, cols):
    def texto(k):
        c = cols.get(k)
        if not c or c not in d.columns:
            return pd.Series("", index=d.index, dtype=object)
        s = d[c].astype(object)
        return s.where(s.notna(), "").astype(str).astype(object)

    def numero(k):
        c = cols.get(k)
        if not c or c not in d.columns:
            return pd.Series(np.nan, index=d.index, dtype=float)
        v = pd.to_numeric(d[c], errors="coerce").to_numpy(dtype=float, na_value=np.nan, copy=True)
        v[~np.isfinite(v)] = np.nan
        return pd.Series(v, index=d.index)

    t = pd.DataFrame({"fecha": pd.to_datetime(d[cols["fecha"]], errors="coerce"),
                      **{k: texto(k) for k in ("prod", "prov", "doc", "um")},
                      **{k: numero(k) for k in ("precio", "cant", "valor")}})
    # El filtro es el de la vista anterior: no convertir dólares a soles.
    moneda = cols.get("moneda")
    if moneda and moneda in d.columns:
        t = t[texto("moneda").str.strip().isin(("01", "1"))]
    t = t[t["fecha"].notna() & t["prod"].str.strip().ne("")].copy()
    t["valor"] = t["valor"].fillna(0)
    t["um"] = t["um"].str.strip().str.upper()
    return t


def armar(d, hist, cols, rango=None, inicial="12m", filtros=None):
    """Todas las ventanas son planes del mismo histórico y sello de contenido."""
    fuente = hist if hist is not None else d
    t = normalizar(fuente, cols)
    fechas = pd.to_datetime(fuente[cols["fecha"]], errors="coerce").dt.normalize().dropna()
    fd = pd.to_datetime(d[cols["fecha"]], errors="coerce").dt.normalize().dropna()
    if rango is None or any(x is None for x in rango):
        rango = (fd.min(), fd.max()) if not fd.empty else (fechas.min(), fechas.max())
    if fechas.empty:
        return None
    planes = {periodo.HEREDA: [str(pd.Timestamp(x).date()) for x in rango]}
    for op in periodo.OPCIONES[1:]:
        planes[op] = [str(x.date()) for x in periodo.ventana(op, fechas.max(), fechas.min())]
    nombres = {k: sorted(set(t[k])) for k in ("prod", "prov", "doc", "um")}
    ids = {k: {v: i for i, v in enumerate(vs)} for k, vs in nombres.items()}
    base = t["fecha"].min().normalize() if not t.empty else fechas.min()
    dias = (t["fecha"].dt.normalize() - base).dt.days.to_numpy()
    horas = ((t["fecha"] - t["fecha"].dt.normalize()).dt.total_seconds() * 1000).to_numpy()

    def n(v):
        return round(float(v), 6) if pd.notna(v) else None

    rows = [[int(dias[i]), int(horas[i]), ids["prod"][p], ids["prov"][v],
             ids["doc"][dc], ids["um"][u], n(pr), n(q), n(val)]
            for i, (_, p, v, dc, u, pr, q, val) in enumerate(t.itertuples(index=False, name=None))]
    payload = {"base": str(base.date()), "planes": planes, "inicial": inicial,
               "prods": nombres["prod"], "provs": [nombre_propio(v) if v else "Sin proveedor" for v in nombres["prov"]],
               "docs": documento_legible(pd.Series(nombres["doc"], dtype=object)).replace("", "—").tolist(),
               "ums": nombres["um"], "um_c": [unidad_corta(u) if u else "sin unidad" for u in nombres["um"]],
               "lineas": rows, "historia": [str(fechas.min().date()), str(fechas.max().date())],
               "filtros": filtros or {},
               "hay_cant": bool(cols.get("cant")) and cols["cant"] in fuente.columns,
               "hay_doc": bool(cols.get("doc")) and cols["doc"] in fuente.columns,
               "hay_prov": bool(cols.get("prov")) and cols["prov"] in fuente.columns}
    h = hashlib.sha256(json.dumps(payload, ensure_ascii=False, allow_nan=False,
                                 separators=(",", ":")).encode()).hexdigest()
    payload["sello"] = h[:20]
    return payload


def cambio_gasto(actual, previo):
    """Referencia pura del puente: (Δq × p0) + (Δp × q1) = Δ(p × q).

    Cada lado lleva precio/cant. Sólo cantidades positivas y precios válidos;
    el gasto registrado se informa aparte, porque puede no ser precio × qty.
    Sin compras comparables no se inventa un precio previo de cero.
    """
    def total(rows):
        validos = [r for r in rows if r.get("precio") and r["precio"] > 0
                   and r.get("cant") and r["cant"] > 0]
        q = sum(r["cant"] for r in validos)
        v = sum(r["precio"] * r["cant"] for r in validos)
        return {"cant": q, "valor": v, "precio": v / q if q else None}
    a, p = total(actual), total(previo)
    if not a["cant"] or not p["cant"]:
        return {"actual": a, "previo": p, "precio": None, "cantidad": None, "delta": None}
    return {"actual": a, "previo": p,
            "precio": (a["precio"] - p["precio"]) * a["cant"],
            "cantidad": (a["cant"] - p["cant"]) * p["precio"],
            "delta": a["valor"] - p["valor"]}
