"""Cuentas del resumen gerencial: venta preparada y costo de ventas mensual.

Las definiciones pertenecen a definicion_venta y costo_ventas. Este módulo
resume sus resultados; no usa stock de hoy ni mezcla un mes parcial con
el consumo de un mes completo.
"""

import calendar
import datetime as dt
import math
from urllib.parse import urlencode

import pandas as pd

import costo_ventas as cv
import definicion_venta as dv
import pendientes
from cortes import MESES_ABR_ES, MESES_LARGOS_ES

VERSION = 4
PEDIDO = "LLAVE LOCAL PEDIDO"
NOMBRE = "NOMB ITEM VENTA"


def rango_mes(mes, hasta=None):
    p = pd.Period(mes, freq="M")
    ini, fin = p.start_time.date(), p.end_time.date()
    return ini, min(fin, hasta) if hasta else fin


def rango_anterior(ini, fin):
    """Misma fecha del año pasado; febrero se recorta al último día real."""
    def anterior(d):
        return dt.date(d.year - 1, d.month,
                       min(d.day, calendar.monthrange(d.year - 1, d.month)[1]))
    return anterior(ini), anterior(fin)


def variacion(actual, anterior):
    if actual is None or anterior is None or anterior <= 0:
        return None
    return (actual - anterior) / anterior


def enlace_reporte(reporte, vista, ini=None, fin=None, mes=None):
    """URL relativa: conserva el host y el prefijo de despliegue de la app."""
    params = {"reporte": reporte, "vista": vista}
    if ini and fin:
        params.update(desde=ini.isoformat(), hasta=fin.isoformat())
    if mes:
        params.update(mes=str(mes), desde_resumen="1")
    return "?" + urlencode(params)


def rango_del_enlace(params):
    """Un rango ISO válido del enlace, o None. Nunca ejecuta texto de URL."""
    try:
        ini = dt.date.fromisoformat(params.get("desde", ""))
        fin = dt.date.fromisoformat(params.get("hasta", ""))
    except (TypeError, ValueError):
        return None
    return (ini, fin) if ini <= fin else None


def ventas_del_rango(df, ini, fin):
    """Venta neta y pedidos netos, sin duplicar ítems por forma de pago.

    Pedidos usa la misma conciliación por pedido/comprobante de pax_por:
    una cuenta dividida cuenta una vez, el canje no suma otro pedido y una
    devolución resta. La venta incluye todos los grupos del reporte Ventas.
    """
    if df is None:
        return None
    fecha, neto = dv.columna(df, dv.FECHA), dv.columna(df, dv.NETO_ITEM)
    if not (fecha and neto):
        if df.empty:
            return {"venta": 0.0, "pedidos": 0.0, "promedio": None,
                    "clientes": 0.0, "ticket": None, "descuentos": 0.0,
                    "pct_descuento": None, "dias": [], "sin_costo": 0.0,
                    "sin_costo_pct": None, "sin_costo_top": [], "sin_costo_n": 0}
        raise ValueError("Faltan la fecha o el neto de la venta")
    d = dv.solo_venta(df)
    f = pd.to_datetime(d[fecha], errors="coerce")
    d = d[(f >= pd.Timestamp(ini)) &
          (f < pd.Timestamp(fin) + pd.Timedelta(days=1))].copy()
    item = dv.columna(d, dv.LLAVE_ITEM)
    if item:
        llave = d[item]
        d = d[~(llave.duplicated() & llave.notna())].copy()
    valores = pd.to_numeric(d[neto], errors="coerce").fillna(0.0)
    venta = float(valores.sum())
    diario = pd.DataFrame({
        "dia": pd.to_datetime(d[fecha], errors="coerce").dt.normalize(),
        "neto": valores,
    }).groupby("dia")["neto"].sum()
    dias = [{"dia": x.date().isoformat(), "venta": float(v)}
            for x, v in diario.items()]
    ped, doc = dv.columna(d, PEDIDO), dv.columna(d, dv.LLAVE_DOC)
    clase = dv.columna(d, dv.CLASE)
    pedidos = None
    if ped and doc and clase:
        d["_pedido_signo"] = d[clase].map(
            lambda c: -1.0 if c == dv.NOTA_CREDITO else 1.0)
        pedidos = dv.pax_por(d, ped, "_pedido_signo", doc=doc)
    costo = dv.columna(d, dv.COSTO)
    sin_costo, sin_costo_top, sin_costo_n = None, [], 0
    if costo:
        cero = pd.to_numeric(d[costo], errors="coerce").fillna(0).eq(0)
        sin_costo = float(valores[cero].sum())
        nombre = dv.columna(d, NOMBRE)
        if nombre:
            # Los platos que la explican, como «Sin costo» de Ventas: una
            # nota resta de su plato y lo que queda en cero no se nombra.
            g = valores[cero].groupby(d.loc[cero, nombre].astype(str)).sum()
            g = g[g > 0.5].sort_values(ascending=False)
            sin_costo_n = int(len(g))
            sin_costo_top = [{"plato": k, "venta": float(v)}
                             for k, v in g.head(3).items()]
    clientes, ticket = None, None
    pax = dv.columna(d, dv.PAX)
    if ped and pax:
        clientes = dv.pax_por(d, ped, pax, doc=doc)
        # El ticket del POS: neto de los canales que registran clientes ÷
        # adultos (regla #591). Rappi vende sin pax y no entra.
        base = valores[dv.con_clientes(d, dv.columna(d, dv.CANAL), pax)]
        ticket = float(base.sum()) / clientes if clientes > 0 else None
    carta = descuentos = None
    c_carta, c_cant = dv.columna(d, dv.CARTA_UNIT), dv.columna(d, dv.CANTIDAD)
    c_desc = dv.columna(d, dv.DESCUENTO_ITEM)
    if c_desc:
        # De la línea y con impuestos, como «Descuentos» de Ventas › Resumen:
        # lo que se dejó de cobrar sobre el precio de carta.
        descuentos = float(pd.to_numeric(d[c_desc], errors="coerce").fillna(0).sum())
        if c_carta and c_cant:
            carta = float((pd.to_numeric(d[c_carta], errors="coerce").fillna(0)
                           * pd.to_numeric(d[c_cant], errors="coerce").fillna(0)).sum())
    return {"venta": venta, "pedidos": pedidos,
            "promedio": venta / pedidos if pedidos and pedidos > 0 else None,
            "clientes": clientes, "ticket": ticket,
            "descuentos": descuentos,
            "pct_descuento": descuentos / carta if descuentos is not None
            and carta and carta > 0 else None,
            "dias": dias, "sin_costo": sin_costo,
            "sin_costo_pct": sin_costo / venta if sin_costo and venta > 0 else None,
            "sin_costo_top": sin_costo_top, "sin_costo_n": sin_costo_n}


def costo_del_mes(datos, mes):
    """Mismos defaults que Costos: 4 familias, Eventos sí, Venta interna no.

    Las bajas siguen dentro del consumo carta. Cortesías y las demás
    salidas se restan; los descuentos son referencia comercial. No se utiliza
    la venta total de la portada como denominador: Costos tiene su propio
    ámbito de grupos y lo devuelve explícitamente como venta_base.
    """
    periodos = datos.get("periodos", []) if datos else []
    i = next((i for i, p in enumerate(periodos) if p["k"] == str(mes)), None)
    if i is None:
        return None
    filas = datos["filas"]

    def de(obj, cub):
        return float(obj.get(cub, [0.0] * len(periodos))[i])

    def extra(obj):
        return float(obj.get("Eventos", [0.0] * len(periodos))[i])

    familias = []
    for cub in cv.CUBETAS:
        venta = de(filas["venta"], cub)
        pos = de(filas["costo_pos"], cub)
        descuento = de(filas.get("descuentos", {}), cub)
        if cub == "Alimentos":
            venta += extra(datos.get("venta_extra", {}))
            pos += extra(datos.get("costo_extra", {}))
            descuento += extra(datos.get("descuento_extra", {}))
        operativo = (de(filas["inv_inicial"], cub) + de(filas["compras"], cub)
                     - de(filas["inv_final"], cub))
        bajas = de(datos.get("salidas", {}).get(cv.BAJAS, {}), cub)
        otros = sum(de(serie, cub) for tipo, serie in datos.get("salidas", {}).items()
                    if tipo != cv.BAJAS)
        nv = otros + de(filas["cortesias"], cub)
        carta = operativo - nv
        familias.append({"familia": cub, "venta_base": venta,
                         "operativo": operativo, "no_vendido": nv,
                         "carta": carta, "pos": pos, "bajas": bajas,
                         "descuentos": descuento, "diferencia": carta - pos,
                         "porcentaje": operativo / venta if venta > 0 else None})
    total = {k: sum(f[k] for f in familias) for k in (
        "venta_base", "operativo", "no_vendido", "carta", "pos", "bajas", "diferencia")}
    total["porcentaje"] = (total["operativo"] / total["venta_base"]
                           if total["venta_base"] > 0 else None)
    # El costo del Sistema sobre la MISMA venta: la distancia entre los dos
    # porcentajes es lo que la conciliación tiene que explicar.
    total["porcentaje_pos"] = (total["pos"] / total["venta_base"]
                               if total["venta_base"] > 0 else None)
    total["diferencia_pct"] = (total["diferencia"] / total["pos"]
                               if total["pos"] > 0 else None)
    total["faltante"] = total["diferencia"] - total["bajas"]
    total["porcentaje_faltante"] = (total["faltante"] / total["venta_base"]
                                    if total["venta_base"] > 0 else None)
    total["familias"] = familias
    total["cierre"] = periodos[i].get("sub", "")
    total["observaciones"] = datos.get("calidad", {}).get(str(mes), {})
    return total


# ── La portada de doce meses (regla #745) ───────────────────────────────
# La portada cuenta el mes CON su contexto: el presupuesto, los once meses
# de antes y lo que es habitual. Todo lo que sigue es puro: lo arma
# `graficos/resumen_ejecutivo.py` y lo lee `test_resumen_ejecutivo.py`.

CIFRAS = ("venta", "pedidos", "clientes", "ticket", "descuentos",
          "pct_descuento", "sin_costo", "sin_costo_pct")
"""Lo que se guarda de cada mes: las cifras de `ventas_del_rango`, sin la
lista de días ni los platos."""

MESES_HISTORIA = 12
VENTANA_HABITUAL = 6
"""Lo habitual de un indicador es la mediana de los seis meses anteriores:
la misma ventana con que Costos y Pendientes juzgan lo sin explicar."""

ROJO, AMBAR, VERDE = pendientes.ROJO, pendientes.AMBAR, pendientes.VERDE
_ORDEN = {ROJO: 0, AMBAR: 1, VERDE: 2}


def ventas_por_mes(df):
    """`{mes: cifras}` de cada mes del df PREPARADO, con `ventas_del_rango`
    —la misma cuenta que la portada—. Cada mes se filtra por máscara: un
    ítem, un comprobante y su nota caen enteros en su mes."""
    if df is None or df.empty:
        return {}
    fecha = dv.columna(df, dv.FECHA)
    if not fecha:
        return {}
    meses = pd.to_datetime(df[fecha], errors="coerce").dt.to_period("M")
    out = {}
    for p in sorted(meses.dropna().unique()):
        r = ventas_del_rango(df[meses == p], p.start_time.date(), p.end_time.date())
        out[str(p)] = {k: r.get(k) for k in CIFRAS}
    return out


def presupuesto_por_mes(tabla):
    """`{"2026-09": neta}` de la tabla de `presupuesto_ventas.leer()`, con
    todos los servicios. La venta de la portada es neta (sin IGV ni
    recargo), como la columna «neta» del presupuesto."""
    if tabla is None or len(tabla) == 0:
        return {}
    g = tabla.groupby(["anio", "mes"], as_index=False)["neta"].sum()
    return {f"{int(a):04d}-{int(m):02d}": float(v)
            for a, m, v in zip(g["anio"], g["mes"], g["neta"]) if v}


def presupuesto_dias(diario, ini, fin):
    """El presupuesto neto de cada día de `ini` a `fin` (todos los
    servicios), o None si ningún día tiene presupuesto cargado."""
    if diario is None or len(diario) == 0:
        return None
    dia = pd.to_datetime(diario["dia"]).dt.normalize()
    m = (dia >= pd.Timestamp(ini)) & (dia <= pd.Timestamp(fin))
    if not m.any():
        return None
    s = diario.loc[m, "neta"].groupby(dia[m]).sum()
    return [float(s.get(pd.Timestamp(ini) + pd.Timedelta(days=i), 0.0))
            for i in range((fin - ini).days + 1)]


def venta_diaria(grupos, ini, fin):
    """La venta de cada día de `ini` a `fin`, de `data.venta_por_grupo_dia`
    (la clase VENTA de todos los grupos, por día del turno). None si el
    parquet no cubre el primer día: un día antes del parquet no es un cero."""
    if grupos is None or len(grupos) == 0:
        return None
    dia = pd.to_datetime(grupos["dia"], errors="coerce").dt.normalize()
    if dia.min() > pd.Timestamp(ini):
        return None
    m = (grupos["clase"] == dv.VENTA) & (dia >= pd.Timestamp(ini)) & (dia <= pd.Timestamp(fin))
    s = pd.to_numeric(grupos.loc[m, "neto"], errors="coerce").fillna(0.0).groupby(dia[m]).sum()
    return [float(s.get(pd.Timestamp(ini) + pd.Timedelta(days=i), 0.0))
            for i in range((fin - ini).days + 1)]


def alinear_ano_pasado(ini, fin):
    """El tramo del año pasado que cae en los MISMOS días de la semana: 364
    días antes (regla #659). Lo usa el gráfico diario; los totales del mes
    se comparan contra la misma fecha del calendario (`rango_anterior`)."""
    d = dt.timedelta(days=364)
    return ini - d, fin - d


def _mes_menos(mes, n):
    return str(pd.Period(mes, freq="M") - n)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def mediana(valores):
    ok = sorted(v for v in valores if _num(v))
    if not ok:
        return None
    m = len(ok)
    return ok[m // 2] if m % 2 else (ok[m // 2 - 1] + ok[m // 2]) / 2


def historia(mes, ventas_mes, costos, ppto_mes, actual=None, anterior=None,
             ppto_tramo=None, parcial=False):
    """Los `MESES_HISTORIA` meses que terminan en `mes`, del más viejo al más
    nuevo: las cifras de venta, su año pasado (misma fecha del calendario),
    el presupuesto y el costo de cada uno. El mes elegido toma `actual` y
    `anterior` —el mismo tramo, si está en curso— y el presupuesto de esos
    días; los demás, el mes entero."""
    ventas_mes, ppto_mes = ventas_mes or {}, ppto_mes or {}
    out = []
    for n in range(MESES_HISTORIA - 1, -1, -1):
        k = _mes_menos(mes, n)
        es = n == 0
        v = actual if es and actual else ventas_mes.get(k)
        a = anterior if es and actual else ventas_mes.get(_mes_menos(k, 12))
        c = costo_del_mes(costos, k) if costos and not (es and parcial) else None
        if es and ppto_tramo:
            ppto = sum(ppto_tramo)
        else:
            ppto = None if es and parcial else ppto_mes.get(k)
        out.append({
            "k": k, "parcial": bool(es and parcial),
            **{x: (v or {}).get(x) for x in CIFRAS},
            "ap": ({x: a.get(x) for x in ("venta", "clientes", "ticket", "pct_descuento")}
                   if a else None),
            "ppto": ppto,
            "costo": ({"real": c["porcentaje"], "pos": c["porcentaje_pos"],
                       "faltante": c["faltante"], "faltante_pct": c["porcentaje_faltante"]}
                      if c else None),
        })
    return out


def habitual(hist, clave):
    """La mediana de `clave` en los `VENTANA_HABITUAL` meses anteriores al
    último de `hist`, o None con menos de tres."""
    previos = [h[clave] for h in hist[:-1][-VENTANA_HABITUAL:] if _num(h.get(clave))]
    return mediana(previos) if len(previos) >= 3 else None


def _nombre_mes(k, ref=None):
    """«febrero», o «diciembre 2025» si no es del año de `ref`."""
    p = pd.Period(k, freq="M")
    nombre = MESES_LARGOS_ES[p.month - 1]
    return nombre if ref and pd.Period(ref, freq="M").year == p.year else f"{nombre} {p.year}"


def _rot(k):
    p = pd.Period(k, freq="M")
    return f"{MESES_ABR_ES[p.month - 1]} {p.year}"


def _mil(v):
    return f"S/ {v / 1000:,.0f} mil" if abs(v) >= 10000 else f"S/ {v:,.0f}"


def _soles(v, dec=0):
    return f"{'−' if v < 0 else ''}S/ {abs(v):,.{dec}f}"


def _racha(valores, peor):
    """Cuántos de los `valores` ANTERIORES al último (del más nuevo hacia
    atrás, salteando los vacíos) son seguidos `peor(x)`, y la posición del
    primero que no lo es (None si todos lo son)."""
    k = 0
    for i in range(len(valores) - 2, -1, -1):
        x = valores[i]
        if not _num(x):
            continue
        if not peor(x):
            return k, i
        k += 1
    return k, None


def _contexto(hist, valores, actual, mes, mejor, peor):
    """«, la caída más chica desde febrero»: lo que dice la racha de `actual`
    contra los meses de antes. `mejor`/`peor` son los textos de cada lado."""
    k, i = _racha(valores, lambda x: x < actual)
    if k >= 2 and mejor:
        return (f", {mejor} desde {_nombre_mes(hist[i]['k'], mes)}" if i is not None
                else f", {mejor} de los últimos {k + 1} meses")
    k, i = _racha(valores, lambda x: x > actual)
    if k >= 2 and peor:
        return (f", {peor} desde {_nombre_mes(hist[i]['k'], mes)}" if i is not None
                else f", {peor} de los últimos {k + 1} meses")
    return ""


def titular(mes, hist, costo, previo, parcial, fin):
    """La frase que abre la portada, en tramos `[texto, clase]`: clase `b`
    (negrita), `bad` o `good`. Dice la venta, el presupuesto, el año pasado
    con su contexto y el costo. [] sin venta."""
    h = hist[-1]
    if not _num(h.get("venta")):
        return []
    nombre = MESES_LARGOS_ES[pd.Period(mes, freq="M").month - 1]
    out = ([[f"Al {fin.day} de {nombre} van ", ""], [_mil(h["venta"]), "b"]] if parcial
           else [[f"{nombre.capitalize()} cerró en ", ""], [_mil(h["venta"]), "b"]])
    ppto = h.get("ppto")
    if _num(ppto) and ppto > 0:
        c = h["venta"] / ppto
        out += [[": el ", ""], [f"{c:.0%} del presupuesto",
                                "good" if c >= 1 else "bad" if c < 0.95 else "b"]]
    v = variacion(h["venta"], (h.get("ap") or {}).get("venta"))
    if v is not None:
        out += [[" y " if len(out) > 2 else ": ", ""],
                [f"{abs(v):.1%} {'menos' if v < 0 else 'más'}", "bad" if v < 0 else "good"],
                [f" que {_nombre_mes(_mes_menos(mes, 12))}", ""]]
        vals = [None if x["parcial"] and x is not h else
                variacion(x.get("venta"), (x.get("ap") or {}).get("venta")) for x in hist]
        ctx = (_contexto(hist, vals, v, mes, "la caída más chica", "la caída más grande")
               if v < 0 else _contexto(hist, vals, v, mes, "el mejor crecimiento", None))
        if ctx:
            out.append([ctx, ""])
    out.append([". ", ""])
    if parcial or not costo or not _num(costo.get("porcentaje")):
        out.append(["El costo de ventas espera el cierre del mes." if parcial or not costo
                    else "", ""])
        return out
    real, antes = costo["porcentaje"], (previo or {}).get("porcentaje")
    if _num(antes) and abs(real - antes) >= 0.0005:
        out += [[f"El costo de ventas {'bajó' if real < antes else 'subió'} a ", ""],
                [f"{real:.1%}", "good" if real < antes else "bad"]]
    else:
        out += [["El costo de ventas quedó en ", ""], [f"{real:.1%}", "b"]]
    reales = [x["costo"]["real"] for x in hist
              if x.get("costo") and _num(x["costo"].get("real"))]
    if len(reales) >= 6:
        pos, n = sorted(reales).index(real) + 1, len(reales)
        if pos == 1:
            out.append([f", el más bajo de los últimos {n} meses", ""])
        elif pos <= 3:
            out.append([f", de los tres más bajos de los últimos {n} meses", ""])
        elif pos == n:
            out.append([f", el más alto de los últimos {n} meses", ""])
    out.append([".", ""])
    return out


def _item(nivel, titulo, chip, detalle=(), ir=None, serie=None, forma="pct"):
    """Una señal: `serie` son los doce meses de su cifra, `forma` cómo se
    escribe cada uno («pct», «soles» o «num»)."""
    return {"nivel": nivel, "t": titulo, "chip": chip, "det": list(detalle),
            "ir": ir, "serie": serie, "forma": forma}


def _serie(hist, valor):
    """`[[rótulo, valor], …]` de los doce meses, para el histograma de una
    señal (None donde no hay dato)."""
    out = []
    for h in hist:
        try:
            v = valor(h)
        except (TypeError, ZeroDivisionError):
            v = None
        out.append([_rot(h["k"]), v if _num(v) else None])
    return out


def _cumplimiento(x):
    return (x["venta"] / x["ppto"] if _num(x.get("venta")) and _num(x.get("ppto"))
            and x["ppto"] > 0 else None)


def para_revisar(mes, hist, actual, costo, previo, costos_meses, parcial):
    """Las señales del mes, por gravedad. Cada una con su título, su cifra,
    el detalle que aparece al tocarla, adónde lleva (`ir`, un destino de la
    portada) y sus doce meses. Una buena noticia sólo entra si responde a
    algo que se mira siempre: el presupuesto y lo sin explicar.

    `costos_meses` es `[(mes, sin explicar, venta base)]` de los meses
    cerrados hasta `mes`: lo sin explicar se juzga con la regla del ⚠ de
    Costo de ventas, la MISMA de Pendientes (`pendientes.umbral_sin_explicar`)."""
    h, a, out = hist[-1], actual or {}, []
    c = _cumplimiento(h)
    if c is not None:
        vals = [None if x["parcial"] and x is not h else _cumplimiento(x) for x in hist]
        k, i = _racha(vals, lambda x: x < c)
        det = []
        if k >= 2:
            det.append(f"Es el mejor cumplimiento desde {_nombre_mes(hist[i]['k'], mes)}."
                       if i is not None else
                       f"Es el mejor cumplimiento de los últimos {k + 1} meses.")
        det.append(("Presupuesto de estos días: " if parcial else "Presupuesto del mes: ")
                   + f"{_soles(h['ppto'])}; venta: {_soles(h['venta'])}.")
        serie = _serie(hist, _cumplimiento)
        if c >= 1:
            out.append(_item(VERDE, "Presupuesto cumplido", f"{c:.0%}", det,
                             "comparativo", serie))
        else:
            out.append(_item(ROJO if c < 0.9 else AMBAR,
                             "La venta va lejos del presupuesto" if parcial
                             else "La venta quedó lejos del presupuesto",
                             f"{c:.0%} · −{_soles(h['ppto'] - h['venta'])}", det,
                             "comparativo", serie))
    if _num(a.get("sin_costo_pct")) and a["sin_costo_pct"] >= 0.005:
        top = [x["plato"] for x in a.get("sin_costo_top") or []]
        resto = (a.get("sin_costo_n") or 0) - len(top)
        hab = habitual(hist, "sin_costo_pct")
        det = []
        if top:
            det.append(", ".join(top) + (f" y {resto} más." if resto > 0 else "."))
        det.append("Bajan el costo del Sistema"
                   + (f"; lo habitual es {hab:.1%} de la venta." if hab is not None else "."))
        out.append(_item(ROJO if hab is not None and a["sin_costo_pct"] >= max(2 * hab, 0.03)
                         else AMBAR, "Vendido sin costo en el POS",
                         f"{a['sin_costo_pct']:.1%} · {_soles(a['sin_costo'])}", det, "platos",
                         _serie(hist, lambda x: x.get("sin_costo_pct"))))
    hab_t = habitual(hist, "ticket")
    if _num(h.get("ticket")) and hab_t and h["ticket"] < 0.92 * hab_t:
        hab_c = habitual(hist, "clientes")
        det = [f"Lo habitual es {_soles(hab_t, 2)}: la mediana de los "
               f"{VENTANA_HABITUAL} meses anteriores."]
        if _num(h.get("clientes")) and hab_c:
            vc = h["clientes"] / hab_c - 1
            det.append(f"Los clientes van {abs(vc):.0%} {'sobre' if vc >= 0 else 'bajo'} "
                       "lo habitual." if abs(vc) >= 0.03 else "Los clientes, en lo habitual.")
        out.append(_item(AMBAR, f"El ticket está {1 - h['ticket'] / hab_t:.0%} bajo lo habitual",
                         _soles(h["ticket"], 2), det, "ventas",
                         _serie(hist, lambda x: x.get("ticket")), "soles"))
    hab_cl = habitual(hist, "clientes")
    if _num(h.get("clientes")) and hab_cl and not parcial and h["clientes"] < 0.85 * hab_cl:
        out.append(_item(AMBAR, f"{1 - h['clientes'] / hab_cl:.0%} menos clientes que lo habitual",
                         f"{h['clientes']:,.0f}",
                         [f"Lo habitual son {hab_cl:,.0f}: la mediana de los "
                          f"{VENTANA_HABITUAL} meses anteriores."], "ventas",
                         _serie(hist, lambda x: x.get("clientes")), "num"))
    hab_d = habitual(hist, "pct_descuento")
    d_ap = (h.get("ap") or {}).get("pct_descuento")
    if _num(h.get("pct_descuento")) and (
            (hab_d is not None and h["pct_descuento"] - hab_d >= 0.015)
            or (_num(d_ap) and h["pct_descuento"] - d_ap >= 0.01)):
        det = []
        if hab_d is not None:
            det.append(f"Lo habitual es {hab_d:.1%} de la carta.")
        if _num(d_ap):
            det.append(f"Hace un año, {d_ap:.1%}.")
        out.append(_item(AMBAR, f"Los descuentos suben a {h['pct_descuento']:.1%} de la carta",
                         _soles(h.get("descuentos") or 0), det, "ventas",
                         _serie(hist, lambda x: x.get("pct_descuento"))))
    if costo and not parcial:
        antes = (previo or {}).get("porcentaje")
        if _num(costo.get("porcentaje")) and _num(antes) and costo["porcentaje"] - antes >= 0.005:
            out.append(_item(ROJO, f"El costo real subió {(costo['porcentaje'] - antes) * 100:.1f} pp",
                             f"{costo['porcentaje']:.1%}",
                             [f"{_nombre_mes(_mes_menos(mes, 1)).capitalize()}: {antes:.1%}. "
                              "Comparación entre meses cerrados, con la misma venta de Costos."],
                             "costos", _serie(hist, lambda x: x["costo"]["real"])))
        tasas = [(f / v if v else None) for _m, f, v in (costos_meses or [])]
        tasas = tasas[-pendientes.VENTANA_COSTOS:]
        um = pendientes.umbral_sin_explicar(tasas)
        tasa = costo.get("porcentaje_faltante")
        raro = um is not None and _num(tasa) and tasa > um
        det = [f"Consumo carta {_soles(costo['carta'])} contra Sistema {_soles(costo['pos'])}, "
               f"menos bajas {_soles(costo['bajas'])}."]
        med = mediana(tasas[:-1])
        if um is not None and med is not None:
            det.append(("Más del doble" if raro else "Dentro") + " de lo habitual: la mediana "
                       f"de los meses anteriores es {med:.1%} de la venta.")
        out.append(_item(ROJO if raro else VERDE,
                         "Sin explicar, más del doble de lo habitual" if raro
                         else "Sin explicar, dentro de lo habitual",
                         f"{_soles(costo['faltante'])} · {tasa:.1%}" if _num(tasa)
                         else _soles(costo["faltante"]), det, "costos",
                         _serie(hist, lambda x: x["costo"]["faltante_pct"])))
        n = len((costo.get("observaciones") or {}).get("detalle") or [])
        if n:
            out.append(_item(AMBAR, "Líneas del cierre con observaciones", f"{n:,}",
                             ["Stock a precio cero, negativos o áreas que faltan en el cierre: "
                              "revisarlas antes de leer el costo real."], "costos"))
    out.sort(key=lambda x: _ORDEN[x["nivel"]])
    return out


def de_pendientes(armado):
    """Las filas de Pendientes (`pendientes.armar`) que la portada suma a su
    lista, con su destino, y cuántas están al día o sin calcular. Lo sin
    explicar queda afuera: la portada lo juzga para el mes elegido."""
    items, al_dia, sin = [], [], 0
    for col in (armado or {}).get("columnas", []):
        for area in col:
            for f in area["filas"]:
                if f["ir"] and f["ir"]["v"] == pendientes.COSTO_VENTAS[2]:
                    continue
                if f["estado"] == pendientes.SIN:
                    sin += 1
                elif f["estado"] == pendientes.VERDE:
                    al_dia.append(f["t"])
                else:
                    por = f["por"][:1].upper() + f["por"][1:] + "." if f["por"] else ""
                    items.append({"nivel": f["estado"], "t": f["t"], "chip": f["v"],
                                  "det": [x for x in (por, f.get("ayuda")) if x],
                                  "destino": f["ir"], "rot": f["ir_rot"], "serie": None})
    return items, al_dia, sin
