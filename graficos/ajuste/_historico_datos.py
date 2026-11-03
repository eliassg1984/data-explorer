"""Detalle histórico de Ajuste (#809): las líneas de los meses elegidos, como
«Detalle docs.» de Compras. Pura: sin UI ni acceso a datos.

Un CONTEO es una fecha × área (lo que se registró ese día en esa área); una
LÍNEA, un producto de ese conteo. No se suma nada antes de mandar: la pieza
cuenta, agrupa y pivotea en el navegador.
"""
import hashlib
import json

import numpy as np
import pandas as pd

from cortes import fecha_operativa, sesiones_inventario
from ._cierre_datos import columnas

# Posiciones de cada línea (el .js las lee en el mismo orden).
CAMPOS = ("fecha", "fam", "sub", "area", "prod", "cod", "um",
          "sis", "fis", "dif", "val", "stock")


def armar(df, contexto=None, operativo=True):
    df = df.reset_index(drop=True)
    c = columnas(df)
    fecha = (pd.to_datetime(df[c["fecha"]], errors="coerce") if c["fecha"]
             else pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]"))
    d = df.loc[fecha.notna()]
    f = fecha.loc[d.index].dt.normalize()
    # Por posición, no con un dict: en pandas 2.2 (Cloud) `unique()` da Timestamps y
    # `to_numpy()` datetime64, que no se encuentran como claves (KeyError, #811).
    codigos, unicas = pd.factorize(f, sort=True)
    fechas = [pd.Timestamp(x) for x in unicas]
    # La sesión de cada fecha («Cierre de octubre», «Parcial · 15-17 set»).
    ses = {}
    for s in sesiones_inventario(f):
        for dia in s["dias"]:
            ses[pd.Timestamp(dia)] = s["nombre"]
    dic, ids = {}, {}
    for k in ("fam", "sub", "area", "prod", "cod", "um"):
        t = (d[c[k]].astype(object).where(d[c[k]].notna(), "").map(str).str.strip()
             if c[k] else pd.Series("", index=d.index))
        t = t.mask(t.str.lower().isin(("nan", "none", "<na>")), "")
        valores = sorted(set(t.to_numpy(dtype=object)))
        dic[k] = valores
        ids[k] = t.map({v: i for i, v in enumerate(valores)}).to_numpy()
    nums = {}
    for k in ("sis", "fis", "dif", "val", "stock"):
        s = (pd.to_numeric(d[c[k]], errors="coerce").astype(float)
             if c[k] else pd.Series(np.nan, index=d.index))
        nums[k] = s.to_numpy()
    def num(v):
        return float(v) if np.isfinite(v) else None
    filas = [[int(a), *(int(x) for x in ids_), *(num(x) for x in ns)]
             for a, ids_, ns in zip(codigos,
                                    zip(*(ids[k] for k in ("fam", "sub", "area", "prod", "cod", "um"))),
                                    zip(*(nums[k] for k in ("sis", "fis", "dif", "val", "stock"))))]
    p = {"dic": dic,
         "fechas": [pd.Timestamp(x).strftime("%Y-%m-%d") for x in fechas],
         "sesiones": [ses.get(pd.Timestamp(x), "") for x in fechas],
         # El mes de cada fecha con la regla de Ajuste: el cierre registrado del 1 al
         # 7 es del mes anterior (#613), salvo que «Mes del cierre» diga registro.
         "meses": [(fecha_operativa(pd.Series([x])).iloc[0] if operativo else pd.Timestamp(x)).strftime("%Y-%m")
                   for x in fechas],
         "filas": filas, "campos": list(CAMPOS),
         "hay": {k: bool(c[k]) for k in ("sub", "cod", "um", "sis", "fis", "stock")},
         "contexto": contexto or {}}
    p["sello"] = hashlib.sha256(json.dumps(p, ensure_ascii=False, allow_nan=False,
                                           separators=(",", ":")).encode()).hexdigest()[:20]
    return p
