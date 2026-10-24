"""Contrato de Stock por Producto (#721), sin red ni widgets.

Conserva la línea producto × área y los valores originales. El navegador
aplica los filtros antes de sumar y calcula el ABC antes de la búsqueda.
"""
import hashlib
import json

import numpy as np
import pandas as pd

from graficos.compras._comun import unidad_corta
from graficos.compras._etiquetas_proveedor import nombre_propio
from . import inventario_productos as ip

TEXTO = ("cod", "prod", "fam", "subfam", "area", "unidad", "usal", "cod_area")
NUMERO = ("factor", "punit", "cant", "val")


def _texto(d, col):
    if not col:
        return pd.Series("", index=d.index, dtype=object)
    t = d[col].astype(object).where(d[col].notna(), "").map(str).str.strip()
    return t.mask(t.str.lower().isin(ip._VACIOS), "")


def _numero(d, col):
    return (pd.to_numeric(d[col], errors="coerce").astype(float).to_numpy()
            if col else np.full(len(d), np.nan))


def _n(v):
    return float(v) if pd.notna(v) and np.isfinite(v) else None


def armar(d, cols, historia=None, consumo=None, rango=None):
    """`historia=(meses, momentos, valores)` ya calculada por analisis_stock."""
    d = d.reset_index(drop=True)
    dic, ids, textos = {}, {}, {}
    for k in TEXTO:
        t = _texto(d, cols.get(k))
        if k == "cod" and not cols.get(k):
            t = _texto(d, cols.get("prod"))
        textos[k] = t
        dic[k] = sorted(set(t.to_numpy(dtype=object)))
        ids[k] = t.map({v: i for i, v in enumerate(dic[k])}).to_numpy()
    nums = {k: _numero(d, cols.get(k)) for k in NUMERO}
    meses, momentos, valores = historia if historia is not None else ([], [], None)
    h = None
    if valores is not None and cols.get("cod_area") and len(valores.columns):
        claves = pd.MultiIndex.from_arrays([textos["cod_area"], textos["cod"]])
        h = np.nan_to_num(valores.reindex(claves).to_numpy(dtype=float))
    filas = []
    for i in range(len(d)):
        filas.append([*(int(ids[k][i]) for k in TEXTO),
                      *(_n(nums[k][i]) for k in NUMERO),
                      [float(v) for v in h[i]] if h is not None else []])
    units = {u: unidad_corta(u) for u in set(dic["unidad"]) | set(dic["usal"])}
    cons = {str(k): _n(v) for k, v in consumo.items()} if consumo is not None else None
    p = {"parte": "base", "dic": dic, "filas": filas, "unidades": units,
         "rotulos": {k: {v: nombre_propio(v) for v in dic[k]} for k in ("fam", "subfam", "area")},
         "meses": list(meses), "momentos": [str(v) for v in momentos],
         "consumo": cons, "analisis": h is not None and consumo is not None,
         "hay_salida": bool(cols.get("factor") and cols.get("usal")),
         "hay_fecha": bool(cols.get("cod") and cols.get("cod_area") and cols.get("cant") and rango),
         "rango": [str(v) for v in rango] if rango else None,
         "areas_iniciales": [a for a in ip.AREAS_DE_ENTRADA if a in dic["area"]],
         "ventana": 90, "umbral": 60}
    p["sello"] = hashlib.sha256(json.dumps(p, ensure_ascii=False, allow_nan=False, sort_keys=True,
                            separators=(",", ":")).encode()).hexdigest()[:20]
    return p


def foto(d, cols, anterior, hoy, fecha, hora, sello):
    """Una respuesta chica, alineada con las líneas del mensaje base.

    Falta de filas EN una foto disponible conserva la regla del kardex
    (sin movimientos anteriores = cero). Una consulta fallida no es cero.
    """
    p = {"parte": "foto", "sello": sello, "fecha": str(fecha), "hora": int(hora),
         "ok": anterior is not None, "comparar": hoy is not None}
    if anterior is None:
        return {**p, "error": "No se pudo consultar el kardex para esa fecha. Reintente la consulta."}
    v = ip.stock_a_la_fecha(d, anterior, col_area=cols["cod_area"], col_cod=cols["cod"],
                           col_cant=cols["cant"], col_val=cols["val"],
                           col_punit=cols.get("punit"), foto_hoy=hoy)
    campos = [cols.get("punit"), cols["cant"], cols["val"], ip.COL_CANT_HOY, ip.COL_VAL_HOY]
    arrays = [_numero(v, c) for c in campos]
    p["filas"] = [[_n(v) for v in r] for r in zip(*arrays)]
    return p
