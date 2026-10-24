"""Contrato de Meseros (#719): pedidos, ítems y planillas canónicas.

La planilla para pagar se genera con el exportador existente de Python en
los seis modos posibles. La ficha y sus filtros son análisis local; no
vuelven a repartir el pozo sobre un subconjunto de mesas o de meseros.
"""
import base64
import hashlib
import json

import numpy as np
import pandas as pd

import definicion_venta as dv
from graficos import ventas_meseros as vm


def extras(d):
    """Documento y descuento por pedido, con un ítem una vez (#517)."""
    from graficos.ventas import unico_por_item

    c = vm.columnas(d)
    it = unico_por_item(dv.solo_venta(d))
    ped = it[c["pedido"]].astype(str).astype(object)
    dc = dv.columna(it, dv.DESCUENTO_ITEM)
    desc = pd.to_numeric(it[dc], errors="coerce").fillna(0) if dc else 0.0
    doc = it[c["numero"]].fillna("").astype(str) if c["numero"] else pd.Series("", index=it.index)
    t = pd.DataFrame({"ped": ped, "desc": desc, "doc": doc.astype(object)})
    return {p: {"desc": float(g["desc"].sum()),
                "doc": " · ".join(dict.fromkeys(str(x) for x in g["doc"] if x))}
            for p, g in t.groupby("ped", sort=False)}


def armar(d_pagos, P, items, P0, P12, rango, firma=None):
    """Importes a 6 decimales; la hora del último día se aplica en Python."""
    ini, fin = rango
    ini0, fin0 = vm.periodo_anterior(ini, fin)
    hora = vm.hora_de_corte(P, fin)
    anterior = vm.hasta_la_misma_hora(P0, fin0, hora)
    vacio = P.iloc[:0]
    P0 = anterior if anterior is not None else vacio
    H = P12 if P12 is not None else vacio
    e = extras(d_pagos)
    meseros = sorted({vm.SIN_MESERO} | set(P["mesero"]) | set(P0["mesero"]) | set(H["mesero"]))
    turnos = sorted(set(P["turno"]) | set(P0["turno"]) | set(H["turno"]))
    peds = sorted(set(P["ped"]) | set(items["ped"]))
    prods, grupos = sorted(set(items["prod"])), sorted(set(items["grupo"]))
    docs = sorted({v["doc"] for v in e.values()} | {""})
    im, it, ip, idc = ({v: i for i, v in enumerate(vs)} for vs in (meseros, turnos, peds, docs))
    ipr, ig = ({v: i for i, v in enumerate(vs)} for vs in (prods, grupos))
    base = min(P["dia"].min(), P0["dia"].min() if not P0.empty else P["dia"].min())

    def dia(v):
        return int((pd.Timestamp(v).normalize() - base).days)

    def n(v):
        return round(float(v), 6) if pd.notna(v) and np.isfinite(v) else 0.0

    def pedidos(t, actual):
        out = []
        for k, r in enumerate(t.itertuples(index=False)):
            ex = e.get(r.ped, {}) if actual else {}
            ms = int((pd.Timestamp(r.cobro) - pd.Timestamp(r.cobro).normalize()).total_seconds() * 1000)
            out.append([ip[r.ped] if actual else k, im[r.mesero], dia(r.dia), ms, it[r.turno],
                        n(r.venta), n(r.items), n(r.personas), n(r.propina), bool(r.tarjeta),
                        bool(r.solo_efectivo), n(ex.get("desc", 0)), idc[ex.get("doc", "")]])
        return out

    # Pivote por columnas nombradas: el contrato no depende de pandas 2/3.
    hi = H.assign(mes=H["dia"].dt.strftime("%Y-%m"))
    hi = hi.groupby(["mes", "mesero", "turno"], as_index=False, sort=True).agg(
        propina=("propina", "sum"), venta=("venta", "sum"))
    hist = [[m, im[me], it[tu], n(p), n(v)] for m, me, tu, p, v in hi.itertuples(index=False, name=None)]
    lineas = [[ip[r.ped], im[r.mesero], dia(r.dia), it[r.turno], ipr[r.prod], ig[r.grupo], n(r.cant), n(r.venta)]
              for r in items.itertuples(index=False)]
    filtros = {rot: [str(v) for v in vs] for rot, vs in zip(
        ("Grupo", "Subgrupo", "Canal", "Servicio"), firma or ((), (), (), ()))}
    libros = {}
    periodo = f"{ini:%d/%m/%Y}–{fin:%d/%m/%Y}"
    pagos = vm.pagos_con_propina(d_pagos)
    for turno in vm.TURNOS:
        pp = vm.del_turno(P, turno)
        R, rep, z = vm.resumen(pp), vm.reparto(pp), vm.pozo(pp)
        for modo in vm.REPARTOS:
            soles, mesas = vm.planilla(pp, modo)
            contexto = {"Desde": str(ini), "Hasta": str(fin), "Turno": turno, "Reparto": modo,
                        **{rot: " / ".join(vs) if vs else "Todos" for rot, vs in filtros.items()},
                        "Alcance": "Planilla completa del rango y turno. La búsqueda y la ficha son análisis.",
                        "Regla del pozo": "Partes iguales por día y turno entre meseros con mesas; regla supuesta de la vista."}
            # El exportador histórico requiere al menos una columna de día.
            if soles.empty:
                libros[f"{turno}|{modo}"] = None
                continue
            blob = vm.excel(periodo, turno, modo, R, rep, soles, mesas, z,
                            vm.del_turno(pagos, turno), contexto=contexto)
            libros[f"{turno}|{modo}"] = base64.b64encode(blob).decode("ascii")
    payload = {"base": str(base.date()), "rango": [str(ini), str(fin)],
               "anterior": [str(ini0), str(fin0)],
               "corte_ms": int(hora.total_seconds() * 1000) if hora is not None else None,
               "hay_anterior": anterior is not None, "hay_historia": P12 is not None,
               "meseros": meseros, "sin_mesero": im[vm.SIN_MESERO], "turnos": turnos,
               "pedidos": peds, "docs": docs, "prods": prods, "grupos": grupos,
               "actual": pedidos(P, True), "previo": pedidos(P0, False),
               "items": lineas, "historia": hist, "libros": libros, "filtros": filtros,
               "hay_descuento": bool(dv.columna(d_pagos, dv.DESCUENTO_ITEM)),
               "tramos": list(vm.TRAMOS)}
    # XLSXWriter añade la fecha de creación a los libros. El estado de la
    # ficha depende de datos y contexto, no de ese reloj de exportación.
    identidad = {k: v for k, v in payload.items() if k != "libros"}
    h = hashlib.sha256(json.dumps(identidad, ensure_ascii=False, allow_nan=False,
                                 separators=(",", ":")).encode()).hexdigest()
    payload["sello"] = h[:20]
    return payload
