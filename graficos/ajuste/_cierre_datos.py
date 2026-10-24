"""Contrato de Diferencias del cierre (#720). Sin UI ni acceso a datos.

Una fila sigue siendo una línea del inventario: sumar por producto antes
de enviarla borraría faltantes, sobrantes y el denominador de exactitud.
Los índices sólo comprimen texto; no son identificadores de productos.
"""
import hashlib
import json

import numpy as np
import pandas as pd

from cortes import sesiones_inventario, ultimo_cierre
from graficos.base import _resolver
from ._comun import FAMILIAS_DE_ENTRADA
from ._productos import COL_CODIGO, COL_SUBFAMILIA, COL_UNIDAD
from ._cascada import _COL_SISTEMA, _COL_FISICO


def columnas(df):
    candidatos = {
        "fecha": ["FECHA APERTURA INVENTARIO", "FECHA", "MES"],
        "fam": ["FAMILIA", "Nombre Familia", "NOMBRE FAMILIA"],
        "area": ["AREA", "Nombre Area", "NOMBRE AREA"],
        "prod": ["NOMBRE PRODUCTO", "PRODUCTO", "DESCRIPCION"],
        "cod": COL_CODIGO, "sub": COL_SUBFAMILIA,
        "um": ["Unidad de Ingreso", "Unidad_de_ingreso", "Unidad Ingreso",
               "Unidad Kardex", *COL_UNIDAD, "Unidad_medida", "Unidad medida",
               "Unidad de medida", "Unidad_compra", "Unidad compra", "Unidad", "UM", "Und"],
        "sis": _COL_SISTEMA, "fis": _COL_FISICO,
        "dif": ["AJUSTE", "CANTIDAD AJUSTE", "CANTIDAD"],
        "val": ["AJUSTE VALORIZADO", "AJUSTEVALORIZADO"],
        "stock": ["VALORIZADO TOTAL", "VALORIZADO", "VALORIZADOTOTAL"],
    }
    return {k: _resolver(df, v) for k, v in candidatos.items()}


def armar(df):
    df = df.reset_index(drop=True)
    c = columnas(df)
    fecha = (pd.to_datetime(df[c["fecha"]], errors="coerce") if c["fecha"]
             else pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]"))
    sesiones = sesiones_inventario(fecha)
    if not sesiones and not df.empty:
        sesiones = [{"clave": "sin_fecha", "tipo": "sin_fecha", "mes": (0, 0),
                     "nombre": "Sin fecha de corte", "corto": "Sin fecha de corte",
                     "etiqueta_anio": "Sin fecha", "dias": (), "ini": None,
                     "fin": None, "n_dias": 0, "juntas": 0}]
    dias = {d: i for i, s in enumerate(sesiones) for d in s["dias"]}
    corte = fecha.dt.date.astype(object).map(dias)
    if sesiones and sesiones[0]["tipo"] == "sin_fecha":
        corte = pd.Series(0, index=df.index)
    d = df.loc[corte.notna()]
    dic, ids = {}, {}
    for k in ("fam", "area", "prod", "cod", "sub", "um"):
        # pandas 3 conserva Arrow al hacer astype(str). Iterar esas seis
        # columnas para sus diccionarios penaliza el histórico completo.
        # Object ANTES de llenar vacíos: un código numérico nullable no
        # permite insertar "" mientras siga siendo Int64/Arrow.
        t = (d[c[k]].astype(object).where(d[c[k]].notna(), "").map(str)
             if c[k] else pd.Series("", index=d.index))
        # Familia/nombre del Pareto conservan su agrupación histórica.
        if k not in ("fam", "prod"):
            t = t.str.strip()
        if k in ("cod", "sub", "um"):
            t = t.mask(t.str.lower().isin(("nan", "none")), "")
        valores = sorted(set(t.to_numpy(dtype=object)))
        dic[k] = valores
        ids[k] = t.map({v: i for i, v in enumerate(valores)}).to_numpy()
    nums, validos = {}, {}
    for k in ("val", "dif", "sis", "fis", "stock"):
        s = (pd.to_numeric(d[c[k]], errors="coerce").astype(float)
             if c[k] else pd.Series(np.nan, index=d.index))
        validos[k] = np.isfinite(s.to_numpy())
        nums[k] = np.where(validos[k], s.to_numpy(), 0.0)
    hay_stock = bool(c["sis"] and c["fis"])
    contada = ((np.abs(nums["sis"]) > 1e-9) | (np.abs(nums["fis"]) > 1e-9)
               if hay_stock else np.ones(len(d), dtype=bool))
    diferente = np.abs(nums["val"]) > 1e-9
    hay_dif = diferente | (np.abs(nums["dif"]) > 1e-9)
    completa = (validos["sis"] & validos["fis"] & validos["val"]
                & (validos["dif"] if c["dif"] else True))
    # Bits: línea con stock; diferencia valorizada; diferencia de cualquier
    # clase; datos numéricos completos. Cero/cero NO prueba un recuento.
    flags = (contada.astype(int) + 2*diferente + 4*hay_dif + 8*completa)
    campos = [corte.loc[d.index].astype(int).to_numpy(),
              *(ids[k] for k in ("fam", "area", "prod", "cod", "sub", "um")),
              *(nums[k] for k in ("val", "dif", "sis", "fis", "stock")), flags]
    # No redondear por línea: también se conservan diferencias menores a
    # seis decimales y los importes suman como en pandas.
    filas = [[int(v) if j < 7 or j == 12 else float(v) for j, v in enumerate(r)]
             for r in zip(*campos)]
    ss = [{k: (str(v) if k in ("ini", "fin") and v else v)
           for k, v in s.items() if k != "dias"} for s in sesiones]
    ultimo = ultimo_cierre(sesiones)
    p = {"dic": dic, "sesiones": ss, "filas": filas,
         "inicial": sesiones.index(ultimo) if ultimo else 0,
         "familias_iniciales": [v for v in FAMILIAS_DE_ENTRADA if v in dic["fam"]],
         "hay": {k: bool(v) for k, v in c.items()},
         "sin_fecha": int(corte.isna().sum())}
    p["sello"] = hashlib.sha256(json.dumps(p, ensure_ascii=False, allow_nan=False,
                            separators=(",", ":")).encode()).hexdigest()[:20]
    return p
