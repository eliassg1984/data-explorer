"""Cuentas del resumen gerencial: venta preparada y costo de ventas mensual.

Las definiciones pertenecen a definicion_venta y costo_ventas. Este módulo
resume sus resultados; no usa stock de hoy ni mezcla un mes parcial con
el consumo de un mes completo.
"""

import calendar
import datetime as dt
from urllib.parse import urlencode

import pandas as pd

import costo_ventas as cv
import definicion_venta as dv

VERSION = 1
PEDIDO = "LLAVE LOCAL PEDIDO"


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
                    "dias": [], "sin_costo": 0.0}
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
    sin_costo = (float(valores[pd.to_numeric(d[costo], errors="coerce")
                               .fillna(0).eq(0)].sum()) if costo else None)
    return {"venta": venta, "pedidos": pedidos,
            "promedio": venta / pedidos if pedidos and pedidos > 0 else None,
            "dias": dias, "sin_costo": sin_costo}


def costo_del_mes(datos, mes):
    """Mismos defaults que Costos: 4 familias, Eventos sí, Venta interna no.

    Las bajas siguen dentro del consumo carta. Cortesías, descuentos netos
    de devoluciones del banco y las demás salidas se restan. No se utiliza
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
        nv = otros + de(filas["cortesias"], cub) + descuento
        carta, ajustado = operativo - nv, pos - descuento
        familias.append({"familia": cub, "venta_base": venta,
                         "operativo": operativo, "no_vendido": nv,
                         "carta": carta, "pos": ajustado, "bajas": bajas,
                         "diferencia": carta - ajustado,
                         "porcentaje": operativo / venta if venta > 0 else None})
    total = {k: sum(f[k] for f in familias) for k in (
        "venta_base", "operativo", "no_vendido", "carta", "pos", "bajas", "diferencia")}
    total["porcentaje"] = (total["operativo"] / total["venta_base"]
                           if total["venta_base"] > 0 else None)
    total["diferencia_pct"] = (total["diferencia"] / total["pos"]
                               if total["pos"] > 0 else None)
    total["faltante"] = total["diferencia"] - total["bajas"]
    total["familias"] = familias
    total["cierre"] = periodos[i].get("sub", "")
    return total
