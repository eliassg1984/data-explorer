"""Filas de Ajuste para la tabla propia: fechas y reglas del modelo canónico."""
import hashlib
import json
import math

import pandas as pd

from cortes import CORTE_MAX_SALTO_DIAS, MESES_ABR_ES
from graficos.base import _resolver
from ._comun import areas_con_ajuste, fechas_del_mes


def armar(d, cols, *, operativo=False, contexto=None):
    """Conserva valores binarios completos; no mezcla unidades ni cambia períodos."""
    fecha, fam, area, val, prod, cant = cols
    sub = _resolver(d, ['SUBFAMILIA', 'Subfamilia', 'Nombre Subfamilia'])
    cod = _resolver(d, ['CODIGO PRODUCTO', 'CODIGO', 'Código Producto'])
    unidad = _resolver(d, ['UNIDAD MEDIDA', 'UNIDAD', 'Unidad'])
    b = d.copy()
    b[fecha] = pd.to_datetime(b[fecha], errors='coerce')
    if area and area in b:
        b[area] = b[area].astype(str).str.strip()
    areas = areas_con_ajuste(b, area, val)
    meses = fechas_del_mes(b[fecha], operativo).dt.strftime('%Y-%m')
    rows = []
    def num(v):
        try:
            n = float(v)
            return n if math.isfinite(n) else None
        except (ValueError, TypeError):
            return None
    def txt(r, col):
        v = r.get(col) if col else None
        return '' if v is None or pd.isna(v) else str(v)
    for i, r in enumerate(b.to_dict('records')):
        if pd.isna(r[fecha]):
            continue
        rows.append(dict(id=i, d=r[fecha].date().isoformat(), m=meses.iloc[i],
            f=txt(r, fam), s=txt(r, sub), p=txt(r, prod), a=txt(r, area),
            c=txt(r, cod), u=txt(r, unidad), v=num(r.get(val)),
            q=num(r.get(cant)) if cant and cant in b else None,
            valida=bool(pd.notna(r.get(fam)) and pd.notna(r.get(prod))
                        and (not sub or pd.notna(r.get(sub))))))
    P = dict(version=740, filas=rows, areas=areas, sub=bool(sub),
        cantidad=bool(cant and cant in b), meses=list(MESES_ABR_ES),
        salto=CORTE_MAX_SALTO_DIAS, operativo=bool(operativo), contexto=contexto or {})
    P['sello'] = hashlib.sha256(json.dumps(P, ensure_ascii=False, allow_nan=False, sort_keys=True).encode()).hexdigest()
    return P
