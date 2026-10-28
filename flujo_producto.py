"""Relaciones documentadas entre productos para capacitación, sin repartir consumos.

Las compras y los porcionamientos pertenecen al rango elegido; las recetas
son la composición activa de hoy. Una arista no atribuye lotes ni facturas.
"""
import re
import unicodedata
from functools import lru_cache

import pandas as pd


@lru_cache(maxsize=512)
def _norm(v):
    return re.sub(r"[^A-Z0-9]", "", unicodedata.normalize("NFKD", str(v)).encode(
        "ascii", "ignore").decode().upper())


def _registros(df, campos, rango=None, fechas=()):
    if df is None:
        return []
    wanted = {_norm(k) for k in campos}
    cols = {}
    for col in df.columns:
        key = _norm(col)
        if key in wanted and key not in cols.values():
            cols[col] = key
    d = df[list(cols)].rename(columns=cols)
    if rango:
        f = pd.Series(pd.NaT, index=d.index, dtype='datetime64[ns]')
        for key in fechas:
            if _norm(key) in d:
                f = f.fillna(pd.to_datetime(d[_norm(key)], errors='coerce'))
        mascara = f.dt.normalize().between(pd.Timestamp(rango[0]), pd.Timestamp(rango[1]))
        d = d.loc[mascara].copy()
        d['_fecha'] = f.loc[mascara].dt.strftime('%Y-%m-%d')
    # El maestro repite cada producto por área. Aquí sólo interesa la
    # relación documentada, no sumar líneas ni cantidades.
    return d.drop_duplicates().to_dict('records')


def _txt(v):
    return "" if v is None or pd.isna(v) else str(v).strip()


def _get(r, *keys):
    return next((_txt(r[_norm(k)]) for k in keys if _norm(k) in r), "")


def _activa(r, *keys):
    return all(_get(r, k) and "INAC" not in _get(r, k).upper()
               for k in keys if _norm(k) in r)


def _fecha(r, *keys):
    if '_fecha' in r:
        return r['_fecha']
    value = next((r[_norm(k)] for k in keys if _norm(k) in r and _txt(r[_norm(k)])), None)
    if hasattr(value, 'date') and not pd.isna(value):
        return value.date().isoformat()
    f = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(f) else f.date().isoformat()


def armar(maestro, compras, porcionamientos, base, venta, *, rango, ordenes=None):
    """Grafo por códigos, con evidencia resumida y sin inferir por nombres."""
    nodos, relaciones, avisos = {}, {}, []
    ini, fin = [pd.Timestamp(f).date().isoformat() for f in rango]

    def nodo(cod, nombre="", unidad="", plato=False):
        if not cod:
            return ""
        ident = ("v:" if plato else "p:") + cod
        n = nodos.setdefault(ident, dict(id=ident, cod=cod, nombre=nombre or cod,
                                        unidad=unidad, tipo="plato" if plato else "producto",
                                        compras=[], ordenes=[]))
        if nombre and n["nombre"] == cod:
            n["nombre"] = nombre
        if unidad and not n["unidad"]:
            n["unidad"] = unidad
        return ident

    def enlace(a, b, tipo, documento="", fecha="", area=""):
        if not a or not b or a == b:
            return
        k = (a, b, tipo)
        e = relaciones.setdefault(k, dict(origen=a, destino=b, tipo=tipo, registros={}))
        # La misma cabecera puede repetirse por corte: contar documentos únicos.
        e["registros"][(documento, fecha, area)] = dict(doc=documento, fecha=fecha, area=area)

    for r in _registros(maestro, ['CODIGO PRODUCTO', 'NOMBRE PRODUCTO', 'UNIDAD KARDEX']):
        nodo(_get(r, "CODIGO PRODUCTO"), _get(r, "NOMBRE PRODUCTO"), _get(r, "UNIDAD KARDEX"))

    for fuente, df, requeridas in (
        ("compras", compras, ["COD_PRODUCTO"]),
        ("porcionamientos", porcionamientos, ["COD PROD INIC", "COD PROD FINAL"]),
        ("recetas base", base, ["COD PROD RB", "COD INS RB"]),
        ("recetas de venta", venta, ["COD PLATO", "COD INS"]),
    ):
        cols = {_norm(c) for c in df.columns} if df is not None else set()
        if not all(_norm(c) in cols for c in requeridas):
            avisos.append(f"Sin información utilizable de {fuente}.")

    fechas_compra = ['FECHA_EMISION_DOC', 'FECHA', 'FECHA DOCUMENTO', 'FECHA DOC', 'FECHA REGISTRO']
    for r in _registros(compras, fechas_compra + ['COD_PRODUCTO', 'CODIGO PRODUCTO', 'PRODUCTO',
            'NOMBRE PRODUCTO', 'NUM_DOCUMENTO', 'DOCUMENTO', 'NRO DOCUMENTO', 'COD COMPRA',
            'PROVEEDOR', 'NOMBRE PROVEEDOR', 'NOMBRE ESTADO', 'ESTADO'], (ini, fin), fechas_compra):
        if "ANUL" in _get(r, "NOMBRE ESTADO", "ESTADO").upper():
            continue
        f = _fecha(r, "FECHA_EMISION_DOC", "FECHA", "FECHA DOCUMENTO", "FECHA DOC", "FECHA REGISTRO")
        if not f or not ini <= f <= fin:
            continue
        ident = nodo(_get(r, "COD_PRODUCTO", "CODIGO PRODUCTO"), _get(r, "PRODUCTO", "NOMBRE PRODUCTO"))
        if ident:
            nodos[ident]["compras"].append(dict(fecha=f,
                doc=_get(r, "NUM_DOCUMENTO", "DOCUMENTO", "NRO DOCUMENTO", "COD COMPRA"),
                proveedor=_get(r, "PROVEEDOR", "NOMBRE PROVEEDOR")))

    for r in _registros(porcionamientos, ['FEC REGIST', 'CANT RESULT', 'COD PROD INIC',
            'PROD INICIAL', 'UNID PROD INIC', 'COD PROD FINAL', 'PROD FINAL RESULT',
            'UNID PROD FIN', 'COD PORC', 'SUB ALMACEN'], (ini, fin), ['FEC REGIST']):
        f = _fecha(r, "FEC REGIST")
        if not f or not ini <= f <= fin:
            continue
        # Un corte sin cantidad positiva no prueba una transformación.
        try:
            if float(_get(r, "CANT RESULT") or 0) <= 0:
                continue
        except ValueError:
            continue
        a = nodo(_get(r, "COD PROD INIC"), _get(r, "PROD INICIAL"), _get(r, "UNID PROD INIC"))
        b = nodo(_get(r, "COD PROD FINAL"), _get(r, "PROD FINAL RESULT"), _get(r, "UNID PROD FIN"))
        enlace(a, b, "porcionamiento", _get(r, "COD PORC"), f, _get(r, "SUB ALMACEN"))

    for r in _registros(base, ['RB ACT', 'RB ART ACT', 'INS ACTIVO', 'COD INS RB',
            'INSUMO', 'UNID', 'COD PROD RB', 'RB NOMBRE', 'RB UNID']):
        if not _activa(r, "RB ACT", "RB ART ACT", "INS ACTIVO"):
            continue
        a = nodo(_get(r, "COD INS RB"), _get(r, "INSUMO"), _get(r, "UNID"))
        b = nodo(_get(r, "COD PROD RB"), _get(r, "RB NOMBRE"), _get(r, "RB UNID"))
        if b:
            nodos[b]["tipo"] = "preparacion"
        enlace(a, b, "receta base")

    for r in _registros(venta, ['ITEM VENTA ACTIVO', 'RV ACTIV', 'INS ACTIVO', 'COD INS',
            'INS RV', 'COD PLATO', 'NOMB PLATO']):
        if not _activa(r, "ITEM VENTA ACTIVO", "RV ACTIV", "INS ACTIVO"):
            continue
        a = nodo(_get(r, "COD INS"), _get(r, "INS RV"))
        b = nodo(_get(r, "COD PLATO"), _get(r, "NOMB PLATO"), plato=True)
        enlace(a, b, "receta de venta")

    for r in _registros(ordenes, ['NOMBRE ESTADO', 'FECHA PROCESO', 'FECHA REGISTRO',
            'COD PRODUCTO', 'NOMBRE PRODUCTO', 'COD ORDEN PRODUCCION'], (ini, fin),
            ['FECHA PROCESO', 'FECHA REGISTRO']):
        if _get(r, "NOMBRE ESTADO").upper() != "PROCESADO":
            continue
        f = _fecha(r, "FECHA PROCESO", "FECHA REGISTRO")
        if not f or not ini <= f <= fin:
            continue
        ident = nodo(_get(r, "COD PRODUCTO"), _get(r, "NOMBRE PRODUCTO"))
        if ident:
            nodos[ident]["ordenes"].append(dict(doc=_get(r, "COD ORDEN PRODUCCION"), fecha=f))

    usados = {x for e in relaciones.values() for x in (e["origen"], e["destino"])}
    salida = []
    for e in relaciones.values():
        registros = sorted(e.pop("registros").values(), key=lambda x: (x["fecha"], x["doc"]), reverse=True)
        salida.append(dict(e, cantidad=len(registros), registros=registros[:20]))
    for n in nodos.values():
        n["compras"] = sorted({(x["doc"], x["fecha"], x["proveedor"]) for x in n["compras"]},
                               key=lambda x: x[1], reverse=True)[:20]
        n["ordenes"] = [dict(doc=doc, fecha=fecha) for doc, fecha in
                        sorted({(x['doc'], x['fecha']) for x in n['ordenes']},
                               key=lambda x: x[1], reverse=True)[:20]]
    return dict(nodos=[n for k, n in nodos.items() if k in usados], enlaces=salida,
                rango=[ini, fin], avisos=avisos)
