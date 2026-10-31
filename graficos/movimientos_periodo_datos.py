"""Contrato de Requerimientos, Salidas y Órdenes de producción (#722/#727).

Se reutilizan la normalización y el calendario de la vista original. Los
importes viajan sin redondear; los documentos vacíos también viajan.
"""
import datetime as dt
import hashlib
import json
import math

import pandas as pd

import cortes
from . import movimientos_periodo as mp
from .compras._comun import _cobertura

GRANOS = ("Día", "Semana", "Mes", "Año")
TEXTOS = ("doc", "area", "tipo", "fam", "prod", "unid", "causa", "estado")
DIA_MS = 86400000


def _ms(t):
    return int(pd.Timestamp(t).value // 1000000)


def _numero(v):
    return float(v) if pd.notna(v) and math.isfinite(float(v)) else None


def fecha_al_cierre(f, periodos):
    """La fecha con que `f` (el proceso de cada línea) cuenta AL CIERRE (regla
    #772): lo procesado entre el día 1 y la apertura del conteo es del mes que
    cerró, y lo de antes del día 1 con la apertura ya hecha, del mes nuevo. Con
    la apertura de la mayoría de las áreas (`t1`, de
    `sin_plato.periodos_operativos`). Sólo mueve las de esos bordes. Pura."""
    out = pd.to_datetime(f, errors="coerce").copy()
    for p in periodos or ():
        c1, t1 = p.get("c1"), p.get("t1")
        if c1 is None or t1 is None or p.get("en_curso"):
            continue
        out[(out >= c1) & (out < t1)] = c1 - pd.Timedelta(minutes=1)
        out[(out >= t1) & (out < c1)] = c1
    return out


def armar(d, lado, cols, *, hist=None, anios=0, rango=None, rot_fecha="",
          faltante=None, marcas=None, contexto=None, hoy=None, relojes=None):
    """`relojes` (regla #772): `{"reg", "pro", "cie", "sub"}`, columnas de `d`
    con cada fecha de la línea y su subfamilia; más `"ap"` (`{mes: soles}` un
    año antes) y `"aperturas"`. Con ellas, «Contar por» cambia en el navegador."""
    base = mp.lineas_documentos(d, **cols)
    if marcas is not None:
        base = base.join(marcas[[c for c in mp.COLS_MARCA if c in marcas]])
    for c, defecto in (("habitual", float("nan")), ("veces", 0.), ("exceso", 0.),
                       ("nuevo", False), ("repite_min", float("nan"))):
        if c not in base:
            base[c] = defecto
    base["veces"] = base.veces.fillna(0.)
    base["exceso"] = base.exceso.fillna(0.)
    base["nuevo"] = base.nuevo.fillna(False).astype(bool)
    bh = mp.lineas_documentos(hist, **cols) if hist is not None else base.iloc[:0].copy()
    if not rango:
        inicio = base.fecha.min() if len(base) else pd.Timestamp(hoy or dt.date.today())
        fin = base.fecha.max().normalize() + pd.Timedelta(days=1) if len(base) else inicio + pd.Timedelta(days=1)
        rango = inicio.normalize(), fin
    ini, fin = map(pd.Timestamp, rango)
    rango_d = ini.date(), (fin - pd.Timedelta(days=1)).date()
    dic = {c: sorted(set(base[c]) | set(bh[c])) for c in TEXTOS}
    ids = {c: {v: i for i, v in enumerate(dic[c])} for c in TEXTOS}

    def filas(b, con_marcas=False):
        out = []
        for r in b.itertuples(index=False):
            f = _ms(r.fecha)
            fila = [f] + [ids[c][getattr(r, c)] for c in TEXTOS]
            fila += [_numero(r.cant), _numero(r.punit), _numero(r.valor) or 0.]
            if con_marcas:
                fila += [_numero(r.habitual), float(r.veces), float(r.exceso),
                         bool(r.nuevo), _numero(r.repite_min),
                         mp.texto_marca(r.veces, r.habitual, r.nuevo, r.repite_min,
                                        mp.unidad_corta(r.unid))]
            out.append(fila)
        return out

    fechas_reloj = {}
    subs = None
    if relojes:
        for c in ("reg", "pro", "cie"):
            if relojes.get(c) and relojes[c] in d.columns:
                fechas_reloj[c] = pd.to_datetime(d[relojes[c]], errors="coerce").reindex(base.index)
        if relojes.get("sub") and relojes["sub"] in d.columns:
            subs = d[relojes["sub"]].fillna("").astype(str).str.strip().reindex(base.index).fillna("")
    todas = pd.concat([base.fecha, *fechas_reloj.values()]) if fechas_reloj else base.fecha
    dias = pd.Series(sorted(todas.dropna().dt.normalize().unique()), dtype="datetime64[ns]")
    dias_h = pd.Series(sorted(bh.fecha.dt.normalize().unique()), dtype="datetime64[ns]")
    feriados = set()
    for y in set(dias.dt.year):
        feriados |= cortes.feriados_peru(y)
    planes = {}
    for gran in GRANOS:
        claves = mp._periodo_serie(dias, gran)
        mapa = {str(_ms(d) // DIA_MS): str(k) for d, k in zip(dias, claves)}
        metas = {}
        for k in sorted(set(claves)):
            a, b = mp._limites_periodo(k, gran)
            eje, largo = mp._rotulo_periodo(k, gran, rango_d)
            parcial = _cobertura(k, gran, rango_d)
            especial = ""
            if gran == "Día":
                dia = pd.Timestamp(k).date()
                eje = f"{cortes.DIAS_ABR_ES[dia.weekday()].capitalize()} {dia:%d/%m}"
                largo = f"{eje}/{dia.year}" + (" · feriado" if dia in feriados else "")
                especial = "feriado" if dia in feriados else "fin de semana" if dia.weekday() >= 5 else ""
            fila = f"{eje} {mp._anio_semana(k)}" if gran == "Semana" else largo
            metas[str(k)] = dict(eje=eje, largo=largo, fila=fila,
                                  parcial=parcial[0] < parcial[1], especial=especial,
                                  desde=str(a), hasta=str(b))
        comps = []
        for n in range(1, min(int(anios), 2) + 1):
            off = mp.desfase_comparacion(gran, n)
            desplazadas = mp._periodo_serie(dias_h + off, gran)
            comps.append(dict(n=n, rot=mp.rotulo_anio(ini, fin, off),
                              ini=_ms(ini - off), fin=_ms(fin - off),
                              mapa={str(_ms(d) // DIA_MS): str(k)
                                    for d, k in zip(dias_h, desplazadas)}))
        planes[gran] = dict(mapa=mapa, metas=metas, comps=comps)
    meses = sorted(set(mp._periodo_serie(dias, "Mes")))
    registro = dict(zip(meses, mp.registro_por_mes(bh, meses, faltante, lado)))
    poco = (mp.meses_poco_registro(bh, (ini, fin), hoy or dt.date.today(), lado)
            if hist is not None else [])
    payload = dict(k=lado.k, lado=lado.plur, titulo=lado.titulo, sing=lado.sing,
                   corto=lado.corto, fem=lado.fem, dic=dic, filas=filas(base, True),
                   hist=filas(bh), planes=planes, rango=[str(ini), str(fin)],
                   rot_fecha=rot_fecha, marcas=marcas is not None,
                   tipo=bool(cols.get("tipo") and lado.rotulo_tipo),
                   rotulo_tipo=lado.rotulo_tipo,
                   produccion=lado.k==mp.PRODUCCION.k,
                   suma_sin_procesar=lado.suma_sin_procesar,
                   causa=bool(cols.get("causa")), registro=registro,
                   poco=[dict(mes=str(p), docs=int(n), referencia=float(ref)) for p, n, ref in poco],
                   contexto=contexto or {})
    if fechas_reloj:
        dic_sub = sorted(set(subs)) if subs is not None else []
        id_sub = {v: i for i, v in enumerate(dic_sub)}
        for i, fila in enumerate(payload["filas"]):
            for c in ("reg", "pro", "cie"):
                v = fechas_reloj[c].iloc[i] if c in fechas_reloj else pd.NaT
                fila.append(None if pd.isna(v) else _ms(v))
            fila.append(id_sub[subs.iloc[i]] if subs is not None else None)
        payload["relojes"] = dict(
            disponibles=[c for c in ("cie", "reg", "pro") if c in fechas_reloj],
            ap={str(k): float(v) for k, v in (relojes.get("ap") or {}).items()},
            aperturas=[str(a) for a in relojes.get("aperturas") or ()],
            subs=dic_sub, pedir_refs=bool(relojes.get("pedir_refs")))
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
    payload["sello"] = hashlib.sha256(raw.encode()).hexdigest()
    return payload
