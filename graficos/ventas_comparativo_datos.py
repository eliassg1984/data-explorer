"""Datos de Comparativo como pieza propia (regla #717).

Las fechas las planean los ayudantes originales de ventas_comparativo.
Los comprobantes conservan pedido, documento y los dos signos del pax:
sumar clientes por día rompería un canje o una cuenta dividida. El detalle
viaja por producto/día/grupo/canal, con la frecuencia que decide su moda.
"""
import hashlib
import json

import numpy as np
import pandas as pd

import cortes
import definicion_venta as dv
from graficos import ventas_comparativo as vc


def planes(ancla, inicio=None):
    """Todas las ventanas ofrecidas; los rangos son inclusivos, en ISO."""
    out = {}
    for gran in vc.GRANOS:
        for n in vc.VENTANAS[gran]:
            for modo in (("semana", "calendario") if gran == "Día" else ("semana",)):
                claves = vc._claves_hacia_atras(ancla, gran, n)
                prev = [vc._clave_ap(k, gran, modo) for k in claves]
                a, p, parciales = vc._rangos_comparables(claves, prev, gran, ancla)
                out[f"{gran}|{n}|{modo}"] = {
                    "actual": [[str(i), str(f)] for _, i, f in a],
                    "ap": [[str(i), str(f)] for _, i, f in p],
                    "etiquetas": [vc._etiqueta_clave(k, gran) for k in claves],
                    "ok": vc._comparables(p, inicio),
                    "parciales": sorted(parciales),
                    "sin_dato": vc._texto_sin_dato(prev, vc._comparables(p, inicio), gran),
                }
    return out


def limites(ancla):
    ps = planes(ancla)
    bordes = [r[0] for p in ps.values() for lado in ("actual", "ap") for r in p[lado]]
    bordes += [str(vc._a_la_fecha(ancla, "año")[2])]
    return pd.Timestamp(min(bordes)).date(), ancla


def normalizar(d, cols):
    """Texto object una vez (pandas 2/3), importes sin redondear por ítem."""
    def texto(c):
        if not c or c not in d.columns:
            return pd.Series("", index=d.index, dtype=object)
        s = d[c].astype(object)
        # En pandas 3 astype(str) vuelve a Arrow: terminar en object evita
        # pagar el acceso escalar Arrow por cada celda al serializar.
        return s.where(s.notna(), "").astype(str).astype(object)

    def numero(c):
        if not c or c not in d.columns:
            return pd.Series(0.0, index=d.index)
        values = pd.to_numeric(d[c], errors="coerce").to_numpy(dtype=float, na_value=0.0)
        return pd.Series(np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0), index=d.index)

    return pd.DataFrame({
        "dia": pd.to_datetime(d[cols["fecha"]], errors="coerce").dt.normalize(),
        "ped": texto(cols.get("pedido")), "doc": texto(dv.columna(d, dv.LLAVE_DOC)),
        "pax": numero(cols.get("pax")), "canal": texto(dv.columna(d, dv.CANAL)),
        "prod": texto(cols.get("prod")), "fam": texto(cols.get("fam")),
        "sub": texto(cols.get("sub")), "cant": numero(cols.get("cant")),
        "venta": numero(cols["venta"]),
        "neto": numero(cols.get("neto") or cols["venta"]),
    }).dropna(subset=["dia"])


def armar(d, cols, ancla, inicio=None, sello="", diario=None, ppto_aplica=False,
          servicios=None, filtros=None):
    """Contrato compacto; los importes, cantidades y pax llevan 6 decimales."""
    t = normalizar(d, cols)
    nombres = {k: sorted(set(t[k])) for k in ("ped", "doc", "canal", "prod", "fam", "sub")}
    indices = {k: {v: i for i, v in enumerate(vs)} for k, vs in nombres.items()}
    t = t.assign(pos=t["pax"].clip(lower=0), neg=t["pax"].clip(upper=0))
    docs = t.groupby(["dia", "ped", "doc", "canal", "fam"], as_index=False, sort=False).agg(
        venta=("venta", "sum"), neto=("neto", "sum"), pos=("pos", "max"), neg=("neg", "min"))
    productos = t.groupby(["dia", "prod", "fam", "sub", "canal"], as_index=False, sort=False).agg(
        venta=("venta", "sum"), neto=("neto", "sum"), cant=("cant", "sum"), n=("venta", "size"))
    base = t["dia"].min() if not t.empty else pd.Timestamp(ancla)
    dias = {v: int((v - base).days) for v in t["dia"].unique()}
    doc_rows = [[dias[f], indices["ped"][p], indices["doc"][dc], indices["canal"][c],
                 indices["fam"][g], round(v, 6), round(n, 6), round(a, 6), round(b, 6)]
                for f, p, dc, c, g, v, n, a, b in docs.itertuples(index=False, name=None)]
    prod_rows = [[dias[f], indices["prod"][p], indices["fam"][g], indices["sub"][s],
                  indices["canal"][c], round(v, 6), round(n, 6), round(q, 6), int(nn)]
                 for f, p, g, s, c, v, n, q, nn in productos.itertuples(index=False, name=None)]
    ps = planes(ancla, inicio)
    acumulados = {}
    for nombre, tipo in (("Mes a la fecha", "mes"), ("Año a la fecha", "año")):
        i, f, ip, fp = vc._a_la_fecha(ancla, tipo)
        if inicio is None or ip >= inicio:
            acumulados[nombre] = [[str(i), str(f)], [str(ip), str(fp)]]
    ppto = []
    if ppto_aplica and diario is not None and not diario.empty:
        p = diario
        if servicios:
            p = p[p["servicio"].isin({str(s).strip().upper() for s in servicios})]
        p = p.groupby("dia", as_index=False).agg(bruta=("bruta", "sum"), neta=("neta", "sum"))
        ppto = [[str(pd.Timestamp(f).date()), round(v, 6), round(n, 6)]
                for f, v, n in p.itertuples(index=False, name=None)]
    payload = {
        "parte": "comparativo", "base": str(base.date()), "ancla": str(ancla), "inicio": str(inicio) if inicio else None,
        "planes": ps, "acumulados": acumulados, "docs": doc_rows, "productos": prod_rows,
        "canales": nombres["canal"],
        "platos": nombres["prod"], "grupos": nombres["fam"], "subgrupos": nombres["sub"],
        "hay_pax": all(bool(cols.get(k)) and cols[k] in d.columns for k in ("pax", "pedido")),
        "hay_doc": bool(dv.columna(d, dv.LLAVE_DOC)),
        "hay_cant": bool(cols.get("cant")) and cols["cant"] in d.columns,
        "hay_canal": bool(dv.columna(d, dv.CANAL)),
        "hay_neto": bool(cols.get("neto")) and cols["neto"] in d.columns, "presupuesto": ppto,
        "filtros": filtros or {},
        "feriados": sorted(str(f) for y in range(ancla.year - 2, ancla.year + 1)
                           for f in cortes.feriados_peru(y)),
    }
    # La identidad incluye el contenido y el contexto, no sólo el nombre del parquet.
    h = hashlib.sha256(json.dumps([sello, payload], ensure_ascii=False,
                                 separators=(",", ":"), allow_nan=False).encode())
    payload["sello"] = h.hexdigest()[:20]
    return payload
