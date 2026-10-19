"""Observaciones del reporte mensual de Costos, calculadas desde sus fuentes.

No corrige cantidades o precios, ni convierte importes documentales SUNAT en
consumo de inventario. Módulo puro; nunca contiene datos del negocio.
"""

import pandas as pd

import costo_ventas as cv
from cortes import fecha_operativa


def inventarios(ajuste, meses):
    """Calidad de AMBAS puntas y detalle de productos por mes y familia."""
    if ajuste is None or ajuste.empty or not len(meses):
        return {}
    col = lambda n: cv._col(ajuste, n)  # noqa: E731
    fecha = pd.to_datetime(ajuste[col("FECHA APERTURA INVENTARIO")], errors="coerce")
    b = ajuste.assign(_fecha=fecha, _mes=fecha_operativa(fecha).dt.to_period("M"),
                      _area=ajuste[col("CODIGO AREA")].astype(str).str.strip())
    b = b[b["_fecha"] == b.groupby(["_mes", "_area"])["_fecha"].transform("max")].copy()
    b["_familia"] = b[col("FAMILIA")].map(lambda v: cv.FAMILIAS.get(cv._norm(v)))
    b = b[b["_familia"].notna()]
    valor = col("VALORIZADO TOTAL")
    b["_valor"] = pd.to_numeric(b[valor], errors="coerce")
    cantidad, precio = col("STOCK DECLARADO"), col("PRECIO PROMEDIO")
    b["_cantidad"] = pd.to_numeric(b[cantidad], errors="coerce") if cantidad else float("nan")
    b["_precio"] = pd.to_numeric(b[precio], errors="coerce") if precio else float("nan")
    b["_sin_precio"] = (b["_cantidad"] > 0) & (b["_precio"].abs() < 1e-9)
    b["_negativo"] = (b["_valor"] < -0.005) | (b["_cantidad"] < -1e-9)
    b["_valor_nulo"] = (b["_valor"].isna()
                        | (b["_cantidad"].isna() if cantidad else False)
                        | (b["_precio"].isna() if precio else False))
    b["_duplicado"] = False
    codigo, cierre = col("CODIGO PRODUCTO"), col("CODIGO CIERRE")
    if codigo and cierre:
        b["_duplicado"] = b.duplicated([cierre, codigo], keep=False)
    resultado = {}
    for mes in meses:
        ii, fi = b[b["_mes"] == mes - 1], b[b["_mes"] == mes]
        ai, af = set(ii["_area"]), set(fi["_area"])
        con_valor_i = set(ii.groupby("_area")["_valor"].sum().loc[lambda x: x.abs() > .5].index)
        con_valor_f = set(fi.groupby("_area")["_valor"].sum().loc[lambda x: x.abs() > .5].index)
        registro = {"familias": {}, "areas_sin_cierre_final": sorted(con_valor_i - af),
                    "areas_sin_cierre_inicial": sorted(con_valor_f - ai),
                    "fechas_finales": sorted(fi["_fecha"].dt.strftime("%d/%m/%Y").unique().tolist()),
                    "detalle": [], "columnas_valorizacion": bool(cantidad and precio)}
        for fam in cv.CUBETAS:
            g = b[b["_mes"].isin([mes - 1, mes]) & (b["_familia"] == fam)]
            registro["familias"][fam] = {"sin_precio": int(g["_sin_precio"].sum()),
                "negativos": int(g["_negativo"].sum()), "valor_nulo": int(g["_valor_nulo"].sum()),
                "duplicados": int(g["_duplicado"].sum())}
        problemas = b[b["_mes"].isin([mes - 1, mes]) & (
            b["_sin_precio"] | b["_negativo"] | b["_valor_nulo"] | b["_duplicado"])]
        for _, r in problemas.iterrows():
            motivos = [nom for llave, nom in (("_sin_precio", "Stock con precio cero"),
                       ("_negativo", "Inventario negativo"), ("_valor_nulo", "Dato de valorización ausente"),
                       ("_duplicado", "Línea duplicada")) if r[llave]]
            def numero(llave):
                return round(float(r[llave]), 4) if pd.notna(r[llave]) else None
            registro["detalle"].append({"familia": r["_familia"],
                "punta": "Inicial" if r["_mes"] == mes - 1 else "Final",
                "fecha": r["_fecha"].strftime("%d/%m/%Y"),
                "area": str(r[col("AREA")]) if col("AREA") else r["_area"],
                "codigo": str(r[codigo]) if codigo else "",
                "producto": str(r[col("PRODUCTO")]) if col("PRODUCTO") else "",
                "cantidad": numero("_cantidad"), "precio": numero("_precio"),
                "valor": numero("_valor"), "observacion": ", ".join(motivos)})
        resultado[str(mes)] = registro
    return resultado


def ventas(por_grupo_dia, meses):
    """Advertencias por grupo; los conteos proceden de ítems deduplicados."""
    if por_grupo_dia is None or por_grupo_dia.empty:
        return {}
    b = por_grupo_dia.copy()
    b["mes"] = pd.to_datetime(b["dia"], errors="coerce").dt.to_period("M")
    resultado = {}
    for mes in meses:
        grupos = []
        for grupo, g in b[b["mes"] == mes].groupby("grupo", dropna=False):
            def suma(c):
                return float(pd.to_numeric(g[c], errors="coerce").sum()) if c in g else 0
            grupos.append({"grupo": str(grupo), "familia": cv.GRUPOS_VENTA.get(cv._norm(grupo)),
                "extra": cv.GRUPOS_APARTE.get(cv._norm(grupo)),
                "sin_costo": int(suma("lineas_sin_costo")), "venta_sin_costo": round(suma("venta_sin_costo"), 2),
                "neto": round(suma("neto"), 2), "costo": round(suma("costo"), 2)})
        resultado[str(mes)] = grupos
    return resultado


def cobertura_documental(cruce):
    """Denominador SUNAT antes de filtrar estados; notas separadas."""
    if cruce is None or cruce.empty:
        return {"disponible": False}
    sunat = cruce[cruce["estado"] != "Solo sistema"]
    if sunat.empty:
        return {"disponible": False}
    estados = sunat["estado"].value_counts()
    sin = sunat[sunat["estado"] == "Solo SUNAT"]
    total = len(sunat)
    coincide, diferente = int(estados.get("Coincide", 0)), int(estados.get("Diferencia", 0))
    montos = pd.to_numeric(sin["total_sunat"], errors="coerce").fillna(0)
    return {"disponible": True, "documentos": total, "coinciden": coincide,
            "con_diferencia": diferente, "ubicados": coincide + diferente,
            "sin_coincidencia": len(sin), "cobertura": (coincide + diferente) / total,
            "importe_positivo_sin_coincidencia": round(float(montos[montos >= 0].sum()), 2),
            "notas_sin_coincidencia": int((montos < 0).sum()),
            "importe_notas_sin_coincidencia": round(float(montos[montos < 0].abs().sum()), 2)}
