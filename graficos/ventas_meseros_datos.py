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


FICHA = ("cod", "mesa", "salon", "adultos", "ninos", "apertura", "primer", "ultimo",
         "precuenta", "n_precuenta", "comprobante", "usuario", "canal", "descuento",
         "docs", "pagos", "platos")
"""Contrato de la ficha de un pedido (#856), por posición: los tiempos van en
minutos desde las 00:00 de `base`; `docs` = [número, tipo, cliente, doc. cliente];
`pagos` = [forma, tarjeta u otro, monto, propina, cajero, minuto]; `platos` =
[plato, minuto, cantidad] o None si el rango no los trae."""


def _txt(v):
    return "" if v is None or (isinstance(v, float) and not np.isfinite(v)) or pd.isna(v) else str(v).strip()


_TILDES = {"Cr�dito": "Crédito", "D�bito": "Débito", "Cr�d": "Créd"}
"""El parquet de ventas trae las tildes rotas (U+FFFD, del extractor): la ficha
repara las palabras de los pagos que muestra."""


def _tildes(s):
    for k, v in _TILDES.items():
        s = s.replace(k, v)
    return s


def fichas(d_pagos, peds, base, pedidos=None, horas=None):
    """La ficha de cada pedido del rango (#856), {índice de `peds`: lista FICHA}.

    Sale de tres lados, cada uno con su grano: el pago, el comprobante y el
    cliente, de las filas por ítem y pago de la venta (cada pago y cada
    comprobante UNA vez, #517); la mesa y los tiempos, de `pedidos.parquet`
    (una fila por pedido, por su CÓDIGO); la hora de cada plato, de `horas`
    (pedido, plato, hora, cantidad). Lo que no llega queda vacío. Pura."""
    from graficos.base import _resolver
    if d_pagos is None or d_pagos.empty or not peds:
        return {}
    r = lambda *n: _resolver(d_pagos, list(n))  # noqa: E731
    c = {"ped": r("Llave Local Pedido"), "cod": r("Codigo Pedido Ddocumento"),
         "pago": r("Llave Local Documento Correlativo Pago"), "forma": r("Nombre Tipo Pago"),
         "tarjeta": r("Nombre Tarjeta Pago"), "otro": r("Nombre Otro Tipo Pago Doc"),
         "monto": r("Monto Tipo Pago Doc"), "propina": r("Monto Propina"),
         "cajero": r("Usuario Reg Pago Doc"), "hpago": r("Fecha Registro Pago Doc"),
         "cliente": r("Cliente"), "doccli": r("Doc Cliente"), "tipo": r("Tipo Doc"),
         "numero": r("Numero Documento"), "desc": r("Nombre Descuento"), "canal": r("Canal Venta")}
    if not c["ped"]:
        return {}
    ip = {str(p): i for i, p in enumerate(peds)}
    d = d_pagos[d_pagos[c["ped"]].astype(str).isin(set(ip))]
    base = pd.Timestamp(base).normalize()

    def col(k):
        return d[c[k]] if c[k] else pd.Series(None, index=d.index, dtype=object)

    def minuto(v):
        t = pd.to_datetime(v, errors="coerce")
        return None if pd.isna(t) else int((t - base).total_seconds() // 60)

    def num(v):
        v = pd.to_numeric(v, errors="coerce")
        return round(float(v), 6) if pd.notna(v) else None

    out = {}
    t = pd.DataFrame({"ped": d[c["ped"]].astype(str), "cod": col("cod"), "pago": col("pago"),
                      "forma": col("forma"), "tarjeta": col("tarjeta"), "otro": col("otro"),
                      "monto": col("monto"), "propina": col("propina"), "cajero": col("cajero"),
                      "hpago": col("hpago"), "cliente": col("cliente"), "doccli": col("doccli"),
                      "tipo": col("tipo"), "numero": col("numero"), "desc": col("desc"), "canal": col("canal")})
    for r_ in t.drop_duplicates("ped").itertuples(index=False):
        out[r_.ped] = [_txt(r_.cod), "", "", None, None, None, None, None, None, None, None, "",
                       _txt(r_.canal), _txt(r_.desc), [], [], None]
    # Un comprobante y un pago, una vez cada uno: las filas son por ítem × pago.
    for r_ in t.drop_duplicates(["ped", "numero"]).itertuples(index=False):
        if _txt(r_.numero):
            out[r_.ped][14].append([_txt(r_.numero), _txt(r_.tipo), _txt(r_.cliente), _txt(r_.doccli)])
    pagos = t[t["pago"].notna()].drop_duplicates(["ped", "pago"])
    for r_ in pagos.itertuples(index=False):
        out[r_.ped][15].append([_tildes(_txt(r_.forma)), _tildes(_txt(r_.tarjeta) or _txt(r_.otro)), num(r_.monto),
                                num(r_.propina), _txt(r_.cajero), minuto(r_.hpago)])
    por_cod = {}
    for ped, f in out.items():
        if f[0]:
            por_cod.setdefault(f[0], []).append(ped)
    if pedidos is not None and not pedidos.empty and "CODIGO PEDIDO" in pedidos.columns:
        pc = lambda n: pedidos[n] if n in pedidos.columns else pd.Series(None, index=pedidos.index)  # noqa: E731
        p = pd.DataFrame({"cod": pedidos["CODIGO PEDIDO"].map(_txt), "mesa": pc("MESA"), "salon": pc("SALON"),
                          "adultos": pc("ADULTOS"), "ninos": pc("NINOS"), "apertura": pc("FECHA APERTURA"),
                          "primer": pc("PRIMER ITEM"), "ultimo": pc("ULTIMO ITEM"),
                          "precuenta": pc("FECHA PRECUENTA"), "n_prec": pc("PRECUENTAS"),
                          "comp": pc("ULTIMO COMPROBANTE"), "usuario": pc("USUARIO PEDIDO")})
        for r_ in p[p["cod"].isin(set(por_cod))].drop_duplicates("cod").itertuples(index=False):
            for ped in por_cod[r_.cod]:
                f = out[ped]
                f[1:12] = [_txt(r_.mesa), _txt(r_.salon), num(r_.adultos), num(r_.ninos),
                           minuto(r_.apertura), minuto(r_.primer), minuto(r_.ultimo),
                           minuto(r_.precuenta), num(r_.n_prec), minuto(r_.comp), _txt(r_.usuario)]
    if horas is not None:
        for f in out.values():
            f[16] = []
        h = horas[horas["cod"].map(_txt).isin(set(por_cod))].sort_values(["cod", "hora"], kind="stable")
        for cod, prod, hora, cant in h[["cod", "prod", "hora", "cant"]].itertuples(index=False, name=None):
            for ped in por_cod[_txt(cod)]:
                out[ped][16].append([_txt(prod), minuto(hora), num(cant)])
    return {str(ip[p]): f for p, f in out.items()}


def _carta_sin_venta(items, carta):
    """Los platos activos de la carta que no están en `items`, con el grupo y el
    subgrupo escritos como en la venta cuando coinciden sin mayúsculas (#855)."""
    if carta is None or len(carta) == 0:
        return []
    vendidos = {str(p).strip().lower() for p in items["prod"]}
    gs = {str(g).strip().lower(): g for g in items["grupo"]}
    ss = {str(s).strip().lower(): s for s in items["sub"]} if "sub" in items else {}
    out, vistos = [], set()
    for p, g, s in carta[["prod", "grupo", "sub"]].itertuples(index=False, name=None):
        k = str(p).strip().lower()
        if not k or k in vendidos or k in vistos:
            continue
        vistos.add(k)
        out.append((str(p).strip(), gs.get(str(g).strip().lower(), str(g).strip()),
                    ss.get(str(s).strip().lower(), str(s).strip())))
    return out


def armar(d_pagos, P, items, P0, P12, rango, firma=None, carta=None, pedidos_pos=None, horas=None):
    """Importes a 6 decimales; la hora del último día se aplica en Python.
    `carta`: los platos activos (prod, grupo, sub) para mostrarlos en cero.
    `pedidos_pos` (pedidos.parquet) y `horas`: la mesa y los tiempos, y la hora de cada plato (#856)."""
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
    sin_venta = _carta_sin_venta(items, carta)
    prods = sorted(set(items["prod"]) | {p for p, _, _ in sin_venta})
    grupos = sorted(set(items["grupo"]) | {g for _, g, _ in sin_venta})
    subs = sorted((set(items["sub"]) if "sub" in items else {""}) | {s for _, _, s in sin_venta})
    docs = sorted({v["doc"] for v in e.values()} | {""})
    im, it, ip, idc = ({v: i for i, v in enumerate(vs)} for vs in (meseros, turnos, peds, docs))
    ipr, ig, isb = ({v: i for i, v in enumerate(vs)} for vs in (prods, grupos, subs))
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
    lineas = [[ip[r.ped], im[r.mesero], dia(r.dia), it[r.turno], ipr[r.prod], ig[r.grupo], n(r.cant), n(r.venta),
               isb[getattr(r, "sub", "")]]
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
               "pedidos": peds, "docs": docs, "prods": prods, "grupos": grupos, "subs": subs,
               "carta": [[ipr[p], ig[g], isb[s]] for p, g, s in sin_venta],
               "fichas": fichas(d_pagos, peds, base, pedidos_pos, horas),
               "hay_platos": horas is not None, "hay_mesa": pedidos_pos is not None,
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
