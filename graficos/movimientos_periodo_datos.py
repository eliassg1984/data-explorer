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


def armar(d, lado, cols, *, hist=None, anios=0, rango=None, rot_fecha="",
          faltante=None, marcas=None, contexto=None, hoy=None):
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

    dias = pd.Series(sorted(base.fecha.dt.normalize().unique()), dtype="datetime64[ns]")
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
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
    payload["sello"] = hashlib.sha256(raw.encode()).hexdigest()
    return payload
