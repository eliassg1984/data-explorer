"""
graficos.ventas_meseros — vista «Meseros» del dashboard de Ventas: las
PROPINAS por mesero, con lo que dan los reportes del POS y lo que no dan.

Nació el 2026-09-27 (regla #553), a pedido: «en primer fin obtener
información de propinas, que si bien el sistema nativo las muestra, es sólo
en un reporte plano». Reemplaza a «Propina real vs. esperada»: una regresión
que con el rango por defecto —un mes— no distinguía a nadie (la barra más
grande era la de un mesero con 4 pedidos en un día; pax, hora, fin de semana
y mesero explicaban el 2 % de la propina).

LOS REPORTES DEL POS QUE REPITE, con sus cuentas (leídas de INFOREST):

  · `spRep_AnaliticoMozo` — por mozo: pedidos, comensales, cantidad y venta
    de cada producto. Acá son Mesas, Personas, Productos y Venta.
  · `spRep_Propina` — cada pago con tarjeta (`tTipoPago` 02) que dejó
    propina, por fecha del PAGO. Acá es la Propina y la hoja «Pagos con
    propina» del Excel.

Cuadrado mesero por mesero del 1 al 26 sep 2026: mesas, personas y propinas
iguales. Una sola diferencia: el POS deja SIN mozo un pago cuyo comprobante
no tiene ninguna línea de DPEDIDO que apunte a él (B00001000055383, S/ 38,50);
el parquet lo liga al pedido y va a su mesero.

LAS CUENTAS, y por qué así:

  · MESAS = pedidos con venta, como el Analítico por mozo (con o sin
    personas). PERSONAS = adultos, como el resto de Ventas (decisión del
    2026-09-24, `definicion_venta.pax_por`).
  · DOS GRANOS DEL MISMO df (regla #517): la venta, un ítem una vez; la
    propina y la forma de pago, un PAGO una vez. Por eso la vista recibe las
    filas POR PAGO (`d_pagos`) y arma lo demás acá.
  · LA PROPINA SÓLO EXISTE CON TARJETA: el POS no tiene dónde anotarla en
    efectivo, cheque ni «varios» (0 en todo el histórico). Todas las
    tarjetas tienen `nFactorRetencion` 0: la propina es la bruta.
  · EL DÍA ES EL DEL COMPROBANTE, como el reporte de Propinas del POS. Una
    mesa abierta un día y cobrada al siguiente cae en el segundo: 32 de
    11.800 en un año (0,3 %).
  · POZO COMÚN (a pedido, «por cada mesero, pero también verlo como pozo
    común»): la propina de cada turno de cada día se reparte en partes
    iguales entre los meseros que atendieron al menos una mesa en ese turno.
    Es una regla supuesta, no la del restaurante: si se reparte de otra
    forma, cambia `pozo()`.
  · LA COMPARACIÓN es contra el mismo tramo del mes anterior (1–27 sep contra
    1–27 ago) y HASTA LA MISMA HORA: el parquet se extrae a la madrugada, y
    el último día trae sólo las cenas cobradas pasada la medianoche.
"""

import datetime as _dt
import io
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import definicion_venta as dv
import franja_fecha
from cortes import MESES_ABR_ES
from data import REPORTES, cargar_rango, sello_datos
from tema import (ACENTO, AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, GRIS_TEXTO,
                  LAVANDA_BORDE, TEXTO_PRINCIPAL)
from graficos import alturas
from graficos.base import (_compras_layout, _resolver, preservar_widgets,
                           selector_fecha_tarjeta, una_vez_por_corrida)
from graficos.ventas_platos import _clic, _fila, _key
from graficos.ventas_resumen import _con_alpha

SIN_MESERO = "Sin mesero"
SIN_TURNO = "Sin turno"
TURNOS = ("Todo el día", "Almuerzo", "Cena")
REPARTOS = ("Por mesero", "Pozo común")
TRAMOS = ("0 %", "hasta 5 %", "5 – 9 %", "10 %", "11 – 15 %", "más de 15 %")
_CORTES_TRAMO = (-0.01, 0.001, 5.0, 9.5, 10.5, 15.0, np.inf)
"""El 10 % es la propina más común (27 % de los pagos con tarjeta): su tramo
va de 9,5 a 10,5 para que no lo parta un redondeo."""

_TARJETA = "Tarjeta de Crédito"
_DIAS_ES = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
_BARRA_H = 14
"""Alto de la barra horizontal de `st.dataframe` cuando la grilla desliza de
costado (la planilla, con un día por columna)."""
_GRUPO_PLATOS = "Alimentos"
_N_PLATOS, _N_BEBIDAS = 8, 5
_MESES_EVOLUCION = 12

_KEYS_WIDGET_MES = ("vt_mes_turno", "vt_mes_reparto")
"""Los controles de la vista, para que la recarga de fecha
(`st.rerun(scope="app")`) no se los lleve (regla #373)."""

_COLS_RESUMEN = ["dias", "mesas", "personas", "venta", "items", "propina",
                 "tarjeta", "sin_propina", "solo_efectivo"]
_COLS_PEDIDOS = ["ped", "mesero", "dia", "cobro", "turno", "venta", "items",
                 "personas", "propina", "tarjeta", "solo_efectivo"]


# ===========================================================================
# LAS CUENTAS (puras: las prueba test_graficos.py)
# ===========================================================================

def columnas(df):
    """Los nombres reales de lo que usa la vista; None lo que falte."""
    def r(*nombres):
        return _resolver(df, list(nombres))
    return {
        "pedido": r("Llave Local Pedido", "Nro Pedido", "Numero Pedido"),
        "mesero": r("Nombre Mesero", "Nomb Mesero"),
        "fecha": r("Fec Reg Documento", "Fec_Reg_Documento"),
        "turno": r("Servicio", "Tipo Servicio", "Nomb Servicio"),
        "venta": r("Venta Item Ddocumento", "Venta_Item_Ddocumento"),
        "cant": r("Cantidad Item Ddocumento", "Cantidad"),
        "pax": r("Cant Pax", "Cantidad Pax"),
        "doc": r("Llave Local Documento"),
        "pago": r("Llave Local Documento Correlativo Pago"),
        "propina": r("Monto Propina", "Propina"),
        "tipo_pago": r("Nombre Tipo Pago"),
        "prod": r("Nomb Item Venta", "Nombre Producto"),
        "grupo": r("Grupo"),
        "numero": r("Numero Documento"),
        "fecha_pago": r("Fecha Registro Pago Doc"),
    }


def _texto(s, vacio):
    """Texto limpio en Title Case; lo vacío (o NaN) pasa a `vacio`. Con el
    `where` antes del `astype`: en pandas 3 un NaN sigue siendo NaN después
    de `astype(str)`, y en la 2.2 de Cloud pasa a «nan»."""
    t = s.where(s.notna(), "").astype(str).str.strip().str.title()
    return t.where(t != "", vacio)


def _num(df, col):
    if not col:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def preparar(d_pagos):
    """`(pedidos, items)` de un df de ventas con las filas POR PAGO.

    `pedidos` tiene una fila por pedido: mesero, día y hora del cobro, turno,
    venta, productos, personas, propina, si se pagó con tarjeta y si se pagó
    sólo en efectivo. `items` tiene una fila por ítem vendido (mesero, turno,
    día, producto, grupo, unidades, venta), para «Lo que vendió». Sin las
    columnas que hacen falta, `(None, None)`."""
    # Acá y no arriba: `graficos.ventas` importa este módulo.
    from graficos.ventas import unico_por_item

    if d_pagos is None or d_pagos.empty:
        return None, None
    c = columnas(d_pagos)
    if not (c["pedido"] and c["fecha"] and c["venta"]):
        return None, None
    # SÓLO LAS COLUMNAS QUE SE USAN, antes de filtrar filas: cada filtro
    # copia todas, y el parquet trae 61, casi todas texto. Con las 61, doce
    # meses tardaban 6 s en esta laptop y la mitad era copiar texto.
    usadas = list(dict.fromkeys(
        x for x in (*c.values(), dv.columna(d_pagos, dv.CLASE),
                    dv.columna(d_pagos, dv.LLAVE_ITEM)) if x))
    d_pagos = d_pagos[usadas]
    ven = dv.solo_venta(d_pagos)
    if ven is None or ven.empty:
        return None, None

    it = unico_por_item(ven)
    items = pd.DataFrame({
        "ped": it[c["pedido"]].astype(str),
        "mesero": (_texto(it[c["mesero"]], SIN_MESERO) if c["mesero"]
                   else pd.Series(SIN_MESERO, index=it.index)),
        "cobro": pd.to_datetime(it[c["fecha"]], errors="coerce"),
        "turno": (_texto(it[c["turno"]], SIN_TURNO) if c["turno"]
                  else pd.Series(SIN_TURNO, index=it.index)),
        "venta": _num(it, c["venta"]),
        "cant": _num(it, c["cant"]),
        # El producto va como lo escribe el POS: en Title Case «Agua Munay
        # s/gas» salía «Agua Munay S/Gas» y «Pan a la Brasa», «Pan A La Brasa».
        "prod": (it[c["prod"]].where(it[c["prod"]].notna(), "—").astype(str)
                 .str.strip() if c["prod"] else pd.Series("—", index=it.index)),
        "grupo": (it[c["grupo"]].where(it[c["grupo"]].notna(), "").astype(str)
                  if c["grupo"] else pd.Series("", index=it.index)),
    })
    items = items[items["cobro"].notna()]
    if items.empty:
        return None, None
    items = items.assign(dia=items["cobro"].dt.normalize())

    g = items.groupby("ped", sort=False)
    P = pd.DataFrame({
        "mesero": g["mesero"].first(),
        "dia": g["dia"].min(),
        "cobro": g["cobro"].max(),
        "turno": g["turno"].first(),
        "venta": g["venta"].sum(),
        "items": g["cant"].sum(),
    })

    # Personas: una vez por pedido, y la nota de crédito resta sin borrar a
    # la mesa que sí vino (`definicion_venta.pax_por`, la misma regla que la
    # ficha de la hora). El `por` es el pedido con otro nombre: `_p` no, que
    # es una columna interna de `pax_por`.
    P["personas"] = 0.0
    if c["pax"]:
        tp = pd.DataFrame({
            "ped": items["ped"], "_ped_por": items["ped"],
            "pax": pd.to_numeric(it.loc[items.index, c["pax"]], errors="coerce"),
        })
        if c["doc"]:
            tp["doc"] = it.loc[items.index, c["doc"]].astype(str)
        tp = tp.dropna(subset=["pax"])
        if not tp.empty:
            pax = dv.pax_por(tp, "ped", "pax",
                             doc="doc" if c["doc"] else None, por="_ped_por")
            P["personas"] = pax.reindex(P.index).fillna(0.0).astype(float)

    # La propina y la forma de pago son del PAGO: un pago una vez (#517).
    P["propina"] = 0.0
    P["tarjeta"] = False
    P["efectivo"] = False
    if c["pago"] and c["propina"]:
        pg = ven.dropna(subset=[c["pago"]]).drop_duplicates(c["pago"])
        if not pg.empty:
            tarj = (pg[c["tipo_pago"]].eq(_TARJETA) if c["tipo_pago"]
                    else pd.to_numeric(pg[c["propina"]], errors="coerce") > 0)
            pp = pd.DataFrame({
                "ped": pg[c["pedido"]].astype(str),
                "propina": _num(pg, c["propina"]),
                "tarjeta": tarj.astype(bool),
                "efectivo": (~tarj).astype(bool),
            })
            a = pp.groupby("ped").agg(propina=("propina", "sum"),
                                      tarjeta=("tarjeta", "any"),
                                      efectivo=("efectivo", "any"))
            # `fill_value` y no `fillna`: en pandas 2.2 (Cloud) rellenar un
            # objeto con False avisa que el downcast se va a retirar.
            P["propina"] = a["propina"].reindex(P.index, fill_value=0.0)
            P["tarjeta"] = a["tarjeta"].astype(bool).reindex(
                P.index, fill_value=False)
            P["efectivo"] = a["efectivo"].astype(bool).reindex(
                P.index, fill_value=False)
    P["solo_efectivo"] = P["efectivo"] & ~P["tarjeta"]
    P = P.rename_axis("ped").reset_index()
    return P[_COLS_PEDIDOS], items


def del_turno(P, turno):
    """`P` (o `items`) de un turno; «Todo el día» los deja todos."""
    if P is None or turno == TURNOS[0]:
        return P
    return P[P["turno"] == turno]


def resumen(P):
    """Por mesero: días, mesas, personas, venta, productos, propina, mesas
    pagadas con tarjeta, las que no dejaron propina y las pagadas sólo en
    efectivo. Mesas y días cuentan los pedidos con venta; la venta suma todo
    (también la nota de crédito que resta)."""
    if P is None or P.empty:
        return pd.DataFrame(columns=_COLS_RESUMEN, dtype=float)
    g = P.groupby("mesero")
    R = pd.DataFrame({
        "venta": g["venta"].sum(),
        "items": g["items"].sum(),
        "propina": g["propina"].sum(),
        "personas": g["personas"].sum(),
    })
    con = P[P["venta"] > 0]
    gc = con.groupby("mesero")
    R["dias"] = gc["dia"].nunique()
    R["mesas"] = gc.size()
    R["tarjeta"] = con[con["tarjeta"]].groupby("mesero").size()
    R["sin_propina"] = (con[con["tarjeta"] & (con["propina"] <= 0)]
                        .groupby("mesero").size())
    R["solo_efectivo"] = con[con["solo_efectivo"]].groupby("mesero").size()
    R = R.fillna(0)
    for k in ("dias", "mesas", "tarjeta", "sin_propina", "solo_efectivo"):
        R[k] = R[k].astype(int)
    return R[_COLS_RESUMEN]


def pozo(P):
    """Una fila por día, turno y mesero: la propina PROPIA y la PARTE que le
    toca si la del turno fuera un pozo común repartido en partes iguales
    entre los meseros que atendieron al menos una mesa en ese turno.

    «Sin mesero» (Rappi, para llevar) no entra: no deja propina. Un turno
    cuya propina no tiene con quién repartirse —ningún pedido con venta—
    deja a cada uno con la suya."""
    cols = ["dia", "turno", "mesero", "mesas", "propia", "pozo", "n", "parte"]
    if P is None or P.empty:
        return pd.DataFrame(columns=cols)
    M = P[P["mesero"] != SIN_MESERO]
    if M.empty:
        return pd.DataFrame(columns=cols)
    M = M.assign(con_venta=(M["venta"] > 0).astype(int))
    z = (M.groupby(["dia", "turno", "mesero"], as_index=False)
         .agg(mesas=("con_venta", "sum"), propia=("propina", "sum")))
    tot = (z.groupby(["dia", "turno"], as_index=False)
           .agg(pozo=("propia", "sum")))
    n = (z[z["mesas"] > 0].groupby(["dia", "turno"], as_index=False)
         .agg(n=("mesero", "nunique")))
    z = z.merge(tot, on=["dia", "turno"], how="left").merge(
        n, on=["dia", "turno"], how="left")
    z["n"] = z["n"].fillna(0).astype(int)
    reparte = z["n"] > 0
    z["parte"] = np.where(
        reparte,
        np.where(z["mesas"] > 0, z["pozo"] / z["n"].where(reparte, 1), 0.0),
        z["propia"])
    return z[cols]


def reparto(P):
    """Por mesero: la propina propia, la parte del pozo y la diferencia."""
    z = pozo(P)
    if z.empty:
        return pd.DataFrame(columns=["propia", "pozo", "diferencia"])
    r = z.groupby("mesero").agg(propia=("propia", "sum"),
                                pozo=("parte", "sum"))
    r["diferencia"] = r["pozo"] - r["propia"]
    return r


def planilla(P, modo=REPARTOS[0]):
    """`(soles, mesas)`: dos tablas mesero × día con las mismas filas y
    columnas. `soles` es la propina propia o, con «Pozo común», la parte
    del pozo de cada día (la suma de sus turnos)."""
    z = pozo(P)
    if z.empty:
        vacio = pd.DataFrame()
        return vacio, vacio
    col = "parte" if modo == REPARTOS[1] else "propia"
    soles = z.pivot_table(index="mesero", columns="dia", values=col,
                          aggfunc="sum", fill_value=0.0)
    mesas = z.pivot_table(index="mesero", columns="dia", values="mesas",
                          aggfunc="sum", fill_value=0)
    orden = soles.sum(axis=1).sort_values(ascending=False).index
    dias = sorted(soles.columns)
    return (soles.reindex(index=orden, columns=dias, fill_value=0.0),
            mesas.reindex(index=orden, columns=dias, fill_value=0))


def distribucion(P):
    """Mesas pagadas con tarjeta por tramo de % de propina, por mesero (una
    fila por mesero, una columna por tramo de `TRAMOS`)."""
    T = (P[P["tarjeta"] & (P["venta"] > 0) & (P["mesero"] != SIN_MESERO)]
         if P is not None and not P.empty else None)
    if T is None or T.empty:
        return pd.DataFrame(columns=list(TRAMOS), dtype=int)
    tramo = pd.cut(100 * T["propina"] / T["venta"], list(_CORTES_TRAMO),
                   labels=list(TRAMOS))
    tab = (T.assign(tramo=tramo)
           .groupby(["mesero", "tramo"], observed=False).size()
           .unstack(fill_value=0))
    return tab.reindex(columns=list(TRAMOS), fill_value=0).astype(int)


def mensual(P):
    """`(propina, venta)` por mes: propina en una tabla mes × mesero, venta
    en una serie por mes; los dos sin «Sin mesero»."""
    M = P[P["mesero"] != SIN_MESERO] if P is not None else None
    if M is None or M.empty:
        return pd.DataFrame(), pd.Series(dtype=float)
    M = M.assign(mes=M["dia"].dt.to_period("M").astype(str))
    prop = M.pivot_table(index="mes", columns="mesero", values="propina",
                         aggfunc="sum", fill_value=0.0).sort_index()
    venta = M.groupby("mes")["venta"].sum().reindex(prop.index)
    return prop, venta


def _es_bebida(grupo):
    g = grupo.str.lower()
    return g.str.contains("bebida") | g.str.contains("vino") | \
        g.str.contains("espumante")


def vendido(items, mesero):
    """`(platos, bebidas, grupos)` de un mesero: los platos (grupo
    «Alimentos») y las bebidas de más unidades, y las unidades por grupo."""
    x = items[items["mesero"] == mesero] if items is not None else None
    if x is None or x.empty:
        vacio = pd.DataFrame(columns=["prod", "u", "venta"])
        return vacio, vacio, pd.Series(dtype=float)

    def _top(s, n):
        if s.empty:
            return pd.DataFrame(columns=["prod", "u", "venta"])
        return (s.groupby("prod", as_index=False)
                .agg(u=("cant", "sum"), venta=("venta", "sum"))
                .sort_values(["u", "venta"], ascending=False, kind="stable")
                .head(n))
    grupos = (x.groupby("grupo")["cant"].sum().sort_values(ascending=False))
    grupos = grupos[grupos > 0]
    return (_top(x[x["grupo"] == _GRUPO_PLATOS], _N_PLATOS),
            _top(x[_es_bebida(x["grupo"])], _N_BEBIDAS), grupos)


def pagos_con_propina(d_pagos):
    """Cada pago con propina, como el reporte de Propinas del POS: fecha,
    comprobante, mesero, turno y propina. Sin anulados ni cortesías."""
    c = columnas(d_pagos) if d_pagos is not None else {}
    if d_pagos is None or d_pagos.empty or not (c["pago"] and c["propina"]):
        return pd.DataFrame(columns=["fecha", "comprobante", "mesero", "turno",
                                     "propina"])
    usadas = list(dict.fromkeys(
        x for x in (*c.values(), dv.columna(d_pagos, dv.CLASE)) if x))
    ven = dv.solo_venta(d_pagos[usadas])
    pg = ven.dropna(subset=[c["pago"]]).drop_duplicates(c["pago"])
    prop = _num(pg, c["propina"])
    pg, prop = pg[prop > 0], prop[prop > 0]
    col_f = c["fecha_pago"] or c["fecha"]
    out = pd.DataFrame({
        "fecha": pd.to_datetime(pg[col_f], errors="coerce"),
        "comprobante": (pg[c["numero"]].astype(str) if c["numero"]
                        else pg[c["pago"]].astype(str)),
        "mesero": (_texto(pg[c["mesero"]], SIN_MESERO) if c["mesero"]
                   else SIN_MESERO),
        "turno": (_texto(pg[c["turno"]], SIN_TURNO) if c["turno"]
                  else SIN_TURNO),
        "propina": prop,
    })
    return out.sort_values("fecha", kind="stable").reset_index(drop=True)


def periodo_anterior(ini, fin):
    """Con qué se compara `[ini, fin]`: los mismos días del mes anterior si
    el rango cabe en un mes (1–27 sep → 1–27 ago; un 31 cae en el último
    día del mes corto), y si no, el tramo de igual duración inmediatamente
    anterior."""
    if (ini.year, ini.month) == (fin.year, fin.month):
        ult = ini.replace(day=1) - _dt.timedelta(days=1)
        return (ult.replace(day=min(ini.day, ult.day)),
                ult.replace(day=min(fin.day, ult.day)))
    n = (fin - ini).days + 1
    return ini - _dt.timedelta(days=n), ini - _dt.timedelta(days=1)


def hora_de_corte(P, fin):
    """La hora del último cobro de `P` si cae en `fin`; si no, None.

    El parquet se extrae a la madrugada (o cuando alguien pide Refrescar):
    el último día trae sólo lo cobrado hasta esa hora —de madrugada, las
    cenas cobradas pasada la medianoche—, y contra un día ENTERO del mes
    anterior la comparación saldría baja sin que nada haya pasado."""
    if P is None or P.empty:
        return None
    ultimo = P["cobro"].max()
    if pd.isna(ultimo) or ultimo.normalize() != pd.Timestamp(fin):
        return None
    return ultimo - ultimo.normalize()


def hasta_la_misma_hora(P0, fin0, hora):
    """`P0` hasta la misma hora de su último día (`hora_de_corte`)."""
    if P0 is None or P0.empty or hora is None:
        return P0
    return P0[P0["cobro"] <= pd.Timestamp(fin0) + hora]


def excel(periodo, turno, modo, R, rep, soles, mesas, z, pagos):
    """El .xlsx para pagar las propinas: el Resumen de la tabla, la
    Planilla como está en pantalla, el detalle Por turno (propina propia y
    pozo de cada turno) y los Pagos con propina, como el reporte del POS."""
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    f_tit = wb.add_format({"bold": True, "font_size": 13})
    f_sub = wb.add_format({"italic": True})
    f_cab = wb.add_format({"bold": True, "bottom": 1, "text_wrap": True,
                           "valign": "bottom"})
    f_sol = wb.add_format({"num_format": "#,##0.00"})
    f_ent = wb.add_format({"num_format": "#,##0"})
    f_pct = wb.add_format({"num_format": "0.0%"})
    f_fec = wb.add_format({"num_format": "dd/mm/yyyy"})
    f_hor = wb.add_format({"num_format": "dd/mm/yyyy hh:mm"})
    f_tot = wb.add_format({"bold": True, "top": 1, "num_format": "#,##0.00"})
    f_tot_txt = wb.add_format({"bold": True, "top": 1})
    f_dia = wb.add_format({"bold": True, "bottom": 1, "num_format": "dd/mm"})
    titulo = f"Propinas por mesero · {periodo} · {turno}"

    def _cabecera(ws, fila, textos):
        for j, t in enumerate(textos):
            ws.write(fila, j, t, f_cab)

    # ── Resumen ──────────────────────────────────────────────────────────
    ws = wb.add_worksheet("Resumen")
    ws.write(0, 0, titulo, f_tit)
    ws.write(1, 0, "La propina sólo se registra en pagos con tarjeta. "
                   "Mesas = pedidos con venta; personas = adultos.", f_sub)
    _cabecera(ws, 3, ["Mesero", "Días", "Mesas", "Personas", "Venta",
                      "Productos", "Propina", "% de la venta", "Por mesa",
                      "Por persona", "Mesas con tarjeta", "Sin propina",
                      "Parte del pozo", "Diferencia con el pozo"])
    fila = 4
    for m, r in R.iterrows():
        ws.write(fila, 0, m)
        ws.write_number(fila, 1, int(r["dias"]), f_ent)
        ws.write_number(fila, 2, int(r["mesas"]), f_ent)
        ws.write_number(fila, 3, float(r["personas"]), f_ent)
        ws.write_number(fila, 4, float(r["venta"]), f_sol)
        ws.write_number(fila, 5, float(r["items"]), f_ent)
        ws.write_number(fila, 6, float(r["propina"]), f_sol)
        ws.write_number(fila, 7, r["propina"] / r["venta"] if r["venta"] > 0
                        else 0.0, f_pct)
        ws.write_number(fila, 8, r["propina"] / r["mesas"] if r["mesas"]
                        else 0.0, f_sol)
        ws.write_number(fila, 9, r["propina"] / r["personas"]
                        if r["personas"] > 0 else 0.0, f_sol)
        ws.write_number(fila, 10, int(r["tarjeta"]), f_ent)
        ws.write_number(fila, 11, int(r["sin_propina"]), f_ent)
        if m in rep.index:
            ws.write_number(fila, 12, float(rep.loc[m, "pozo"]), f_sol)
            ws.write_number(fila, 13, float(rep.loc[m, "diferencia"]), f_sol)
        fila += 1
    ws.write(fila, 0, "Total", f_tot_txt)
    for j in (4, 6):
        letra = "EG"[(j == 6)]
        ws.write_formula(fila, j, f"=SUM({letra}5:{letra}{fila})", f_tot)
    ws.set_column(0, 0, 20)
    ws.set_column(1, 13, 12)
    ws.freeze_panes(4, 1)

    # ── Planilla (como está en pantalla) ─────────────────────────────────
    ws = wb.add_worksheet("Planilla")
    ws.write(0, 0, f"{titulo} · {modo}", f_tit)
    ws.write(1, 0, ("Parte del pozo de cada día: la propina de cada turno "
                    "repartida en partes iguales entre los meseros que "
                    "atendieron mesas en ese turno.") if modo == REPARTOS[1]
             else "Propina de cada mesero por día (fecha del comprobante, "
                  "como el reporte de Propinas del POS).", f_sub)
    dias = list(soles.columns)
    ws.write(3, 0, "Mesero", f_cab)
    for j, d in enumerate(dias, start=1):
        ws.write_datetime(3, j, pd.Timestamp(d).to_pydatetime(), f_dia)
    ws.write(3, len(dias) + 1, "Total", f_cab)
    for i, m in enumerate(soles.index, start=4):
        ws.write(i, 0, m)
        for j, d in enumerate(dias, start=1):
            if mesas.loc[m, d] > 0 or soles.loc[m, d]:
                ws.write_number(i, j, float(soles.loc[m, d]), f_sol)
        ws.write_formula(i, len(dias) + 1,
                         f"=SUM({_col_xl(1)}{i + 1}:{_col_xl(len(dias))}{i + 1})",
                         f_tot, float(soles.loc[m].sum()))
    ult = 4 + len(soles.index)
    ws.write(ult, 0, "Total del día", f_tot_txt)
    for j in range(1, len(dias) + 2):
        ws.write_formula(ult, j, f"=SUM({_col_xl(j)}5:{_col_xl(j)}{ult})", f_tot)
    ws.set_column(0, 0, 20)
    ws.set_column(1, len(dias) + 1, 9)
    ws.freeze_panes(4, 1)

    # ── Por turno: la propina propia y el pozo de cada turno ─────────────
    ws = wb.add_worksheet("Por turno")
    ws.write(0, 0, f"Propina por día, turno y mesero · {periodo}", f_tit)
    _cabecera(ws, 2, ["Fecha", "Turno", "Mesero", "Mesas", "Propina propia",
                      "Pozo del turno", "Meseros en el turno",
                      "Parte del pozo"])
    for i, r in enumerate(z.sort_values(["dia", "turno", "mesero"])
                          .itertuples(index=False), start=3):
        ws.write_datetime(i, 0, pd.Timestamp(r.dia).to_pydatetime(), f_fec)
        ws.write(i, 1, r.turno)
        ws.write(i, 2, r.mesero)
        ws.write_number(i, 3, int(r.mesas), f_ent)
        ws.write_number(i, 4, float(r.propia), f_sol)
        ws.write_number(i, 5, float(r.pozo), f_sol)
        ws.write_number(i, 6, int(r.n), f_ent)
        ws.write_number(i, 7, float(r.parte), f_sol)
    ws.set_column(0, 0, 11)
    ws.set_column(1, 1, 10)
    ws.set_column(2, 2, 20)
    ws.set_column(3, 7, 13)
    ws.autofilter(2, 0, 2 + len(z), 7)
    ws.freeze_panes(3, 0)

    # ── Pagos con propina (el reporte de Propinas del POS) ───────────────
    ws = wb.add_worksheet("Pagos con propina")
    ws.write(0, 0, f"Pagos con propina · {periodo}", f_tit)
    _cabecera(ws, 2, ["Fecha y hora", "Comprobante", "Mesero", "Turno",
                      "Propina"])
    for i, r in enumerate(pagos.itertuples(index=False), start=3):
        if pd.notna(r.fecha):
            ws.write_datetime(i, 0, pd.Timestamp(r.fecha).to_pydatetime(),
                              f_hor)
        ws.write(i, 1, r.comprobante)
        ws.write(i, 2, r.mesero)
        ws.write(i, 3, r.turno)
        ws.write_number(i, 4, float(r.propina), f_sol)
    ws.set_column(0, 0, 17)
    ws.set_column(1, 1, 18)
    ws.set_column(2, 2, 20)
    ws.set_column(3, 4, 11)
    ws.autofilter(2, 0, 2 + len(pagos), 4)
    ws.freeze_panes(3, 0)

    wb.close()
    return buf.getvalue()


def _col_xl(j):
    """Índice de columna (0 = A) → letra de Excel."""
    s, j = "", j + 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


# ===========================================================================
# LOS DATOS DE OTROS TRAMOS (el mes anterior y los 12 meses)
# ===========================================================================

def _pedidos_tramo(ini, fin, filtrar_cb, firma):
    """Los pedidos de `[ini, fin]`, traídos de R2 y filtrados como la vista.

    Se guardan en la sesión por (versión del parquet, filtros, tramo): un
    clic en la tabla re-corre la vista, y rehacer doce meses de pedidos en
    cada clic costaba segundos. `cargar_rango` ya cachea el df; lo que se
    ahorra acá es `preparar`."""
    cfg = REPORTES.get("Ventas", {})
    archivo = cfg.get("archivo", "ventas.parquet")
    clave = (sello_datos(archivo), firma, ini, fin)
    memo = st.session_state.setdefault("_vt_mes_memo", {})
    if clave in memo:
        return memo[clave]
    df = cargar_rango(archivo, cfg.get("carga_por_rango", "FEC REG DOCUMENTO"),
                      ini, fin)
    if df is not None and not df.empty and filtrar_cb is not None:
        df = filtrar_cb(df)
    P, _ = preparar(df)
    if P is not None:
        # En modo demo el loader devuelve el df entero: se recorta acá.
        P = P[(P["dia"] >= pd.Timestamp(ini)) & (P["dia"] <= pd.Timestamp(fin))]
    if len(memo) >= 4:
        memo.clear()
    memo[clave] = P
    return P


# ===========================================================================
# LA VISTA
# ===========================================================================

def _leer_clic():
    """El clic en la tabla elige el mesero del detalle (regla #399: se lee
    ARRIBA, con un contador en la key)."""
    f = _clic("vt_mes_tabla", _fila)
    filas = st.session_state.get("_vt_mes_filas", [])
    if f is not None and 0 <= f < len(filas):
        st.session_state["vt_mes_foco"] = filas[f]


def _rango(P):
    """`(ini, fin)` del rango de la vista: el de la fecha de arriba, que es
    el que ya trae `d_pagos`; sin él, el de los datos."""
    ctx = franja_fecha.contexto()
    r = st.session_state.get(ctx["k_rango"]) if ctx else None
    if isinstance(r, (tuple, list)) and len(r) == 2 and all(r):
        return min(r), max(r)
    if P is not None and not P.empty:
        return P["dia"].min().date(), P["dia"].max().date()
    hoy = _dt.date.today()
    return hoy.replace(day=1), hoy


def _fmt_var(v, pp=False):
    """`(texto, color)` de una variación; sin base, «—»."""
    if v is None or not np.isfinite(v):
        return "—", GRIS_TEXTO
    if pp:
        txt = f"{'+' if v >= 0 else '−'}{abs(v):.1f} pp"
    else:
        txt = f"{'+' if v >= 0 else '−'}{abs(v):.0%}"
    return txt, (AJUSTE_POS_TEXTO if v > 0 else AJUSTE_NEG_TEXTO if v < 0
                 else GRIS_TEXTO)


def _totales(R):
    M = R.drop(index=SIN_MESERO, errors="ignore")
    return {k: float(M[k].sum()) for k in _COLS_RESUMEN if k != "dias"}


def _html_cab(t, t0, anterior):
    """Título + KPI en un renglón, con el dibujo del Resumen (`.vt-cab`)."""
    def _k(rot, val, sub="", color=None, clase="", tip=""):
        s = (f'<span class="vt-kpi-sub" style="color:{color}">{escape(sub)}'
             f'</span>' if sub else "")
        return (f'<div class="vt-kpi {clase}" title="{escape(tip or rot)}">'
                f'<span class="vt-kpi-rot">{escape(rot)}</span>'
                f'<span class="vt-kpi-val">{escape(val)}{s}</span></div>')

    def _var(a, b):
        return (a / b - 1) if b else None

    p, p0 = t["propina"], t0["propina"]
    pct = p / t["venta"] if t["venta"] > 0 else 0.0
    pct0 = p0 / t0["venta"] if t0["venta"] > 0 else None
    xm = p / t["mesas"] if t["mesas"] else 0.0
    xm0 = p0 / t0["mesas"] if t0["mesas"] else None
    xp = p / t["personas"] if t["personas"] > 0 else 0.0
    xp0 = p0 / t0["personas"] if t0["personas"] > 0 else None
    sp = t["sin_propina"] / t["tarjeta"] if t["tarjeta"] else 0.0
    sp0 = t0["sin_propina"] / t0["tarjeta"] if t0["tarjeta"] else None
    partes = [
        _k("Propinas", f"S/ {p:,.0f}", *_fmt_var(_var(p, p0)),
           clase="vt-kpi-total",
           tip=f"Propinas con tarjeta: S/ {p:,.2f}. {anterior}: S/ {p0:,.2f}"),
        _k("% de la venta", f"{pct:.1%}",
           *_fmt_var((pct - pct0) * 100 if pct0 is not None else None, pp=True),
           tip="Propina ÷ venta de las mesas con mesero"),
        _k("Por mesa", f"S/ {xm:,.2f}", *_fmt_var(_var(xm, xm0) if xm0 else None),
           tip=f"{t['mesas']:,.0f} mesas"),
        _k("Por persona", f"S/ {xp:,.2f}",
           *_fmt_var(_var(xp, xp0) if xp0 else None),
           tip=f"{t['personas']:,.0f} personas"),
    ]
    # «Sin propina» sube = malo: se invierte el color.
    _t, _c = _fmt_var((sp - sp0) * 100 if sp0 is not None else None, pp=True)
    if _c != GRIS_TEXTO:
        _c = AJUSTE_NEG_TEXTO if _c == AJUSTE_POS_TEXTO else AJUSTE_POS_TEXTO
    partes.append(_k("Con tarjeta sin propina", f"{sp:.0%}", _t, _c,
                     tip=f"{t['sin_propina']:,.0f} de {t['tarjeta']:,.0f} "
                         "mesas pagadas con tarjeta no dejaron propina"))
    partes.append(_k("Sólo efectivo", f"{t['solo_efectivo']:,.0f} mesas",
                     tip="Mesas pagadas sólo en efectivo: su propina, si la "
                         "hubo, no queda en el POS"))
    return ('<div class="vt-cab"><span class="vt-cab-tit">Propinas por '
            'mesero</span><div class="vt-kpis">' + "".join(partes)
            + "</div></div>")


# ANIDADO: la sección que lo llama (`seccion_perezosa`) es otro fragment,
# y CLAUDE.md pide la envoltura para que dos clics juntados en una corrida no
# lo corran dos veces (regla #456; el bug es de Streamlit < 1.62).
@una_vez_por_corrida
@st.fragment
def _ventas_meseros(d_pagos, filtrar_cb=None, firma=None):
    """«Meseros»: las propinas por mesero, su planilla por día y el detalle
    del mesero elegido. `d_pagos` son las filas POR PAGO con los chips de la
    franja; `filtrar_cb` es lo que se le aplica a lo que la vista trae aparte
    de R2 (el mes anterior, los 12 meses), y `firma` identifica esos filtros
    para guardar lo traído en la sesión."""
    ss = st.session_state
    # ── 0) La fecha cambió: recargar el parquet del rango nuevo ──────────
    # Igual que el Resumen y el Mix: el selector escribe la clave CANÓNICA
    # del rango (`categoria=None`), y el `d_pagos` que llegó es del viejo.
    if ss.pop("vt_mes_fecha_flag", False):
        preservar_widgets(_KEYS_WIDGET_MES)
        st.rerun(scope="app")
    _leer_clic()

    # Lo preparado del rango se guarda en la sesión: un clic en la tabla o
    # un cambio de turno re-corren la vista con el MISMO `d_pagos`.
    ini, fin = _rango(None)
    archivo = REPORTES.get("Ventas", {}).get("archivo", "ventas.parquet")
    clave = (sello_datos(archivo), firma, ini, fin,
             0 if d_pagos is None else len(d_pagos))
    memo = ss.setdefault("_vt_mes_actual", {})
    if clave not in memo:
        memo.clear()
        memo[clave] = preparar(d_pagos)
    P_todo, items_todo = memo[clave]
    ini, fin = _rango(P_todo)
    ini0, fin0 = periodo_anterior(ini, fin)
    periodo = franja_fecha.fmt_rango_es(ini, fin)
    anterior = franja_fecha.fmt_rango_es(ini0, fin0)

    with st.container(border=True, key="ajuste_graf_card_izq_ventas_meseros"):
        cab = st.container(key="vt_mes_cabfila")
        # columnas-internas: el turno, la comparación y la fecha
        c1, c2, c3 = st.columns([1.3, 2.4, 1.1], vertical_alignment="center")
        with c1:
            turno = st.segmented_control(
                "Turno", TURNOS, default=TURNOS[0], required=True,
                key="vt_mes_turno", label_visibility="collapsed") or TURNOS[0]
        with c3:
            # «vt_mesf» y no «vt_mes»: el selector arma SUS keys con ese
            # prefijo (`_escala`, `_fila`…), y no pueden chocar con las de la
            # vista (CLAUDE.md, regla #527).
            selector_fecha_tarjeta("vt_mesf", "vt_mes_fecha_flag",
                                   categoria=None)
        if P_todo is None or P_todo.empty:
            with cab:
                st.markdown('<div class="vt-cab"><span class="vt-cab-tit">'
                            'Propinas por mesero</span></div>',
                            unsafe_allow_html=True)
            st.info("No hay ventas con mesero en este rango (o al parquet le "
                    "faltan las columnas de pedido, fecha y venta).")
            return

        P = del_turno(P_todo, turno)
        items = del_turno(items_todo, turno)
        with st.spinner("Trayendo el mes anterior…"):
            P0 = _pedidos_tramo(ini0, fin0, filtrar_cb, firma)
        hora = hora_de_corte(P_todo, fin)
        P0 = hasta_la_misma_hora(del_turno(P0, turno), fin0, hora)
        R, R0 = resumen(P), resumen(P0)
        t, t0 = _totales(R), _totales(R0)
        with c2:
            # Se canta sólo si el corte muerde: un día cerrado a las 23:50
            # no cambia nada y el aviso sería ruido.
            _h = (f", hasta las {int(hora.total_seconds() // 3600):02d}:"
                  f"{int(hora.total_seconds() % 3600 // 60):02d} del último "
                  "día" if hora is not None and hora < pd.Timedelta(hours=20)
                  else "")
            st.caption(f"contra {anterior}{_h}")
        with cab:
            st.markdown(_html_cab(t, t0, anterior), unsafe_allow_html=True)

        M = R.drop(index=SIN_MESERO, errors="ignore")
        M = M[M["mesas"] > 0].sort_values("propina", ascending=False)
        if M.empty:
            st.info("En este turno no hay mesas atendidas por meseros.")
            return
        rep = reparto(P)
        _tabla(M, R0, t["propina"], rep, anterior)
        foco = ss.get("vt_mes_foco")
        if foco not in M.index:
            foco = M.index[0]
        st.caption(_nota_tabla(R, R0, M, anterior))

    _tarjeta_planilla(P, d_pagos, turno, periodo, R, rep)
    _tarjeta_foco(foco, P, items, M, t, turno, periodo, fin, filtrar_cb,
                  firma)


def _tabla(M, R0, total_prop, rep, anterior):
    """La tabla del reporte del POS, con la comparación y el pozo. Un clic
    elige el mesero del detalle."""
    ss = st.session_state
    mes_ant = anterior.split()[-2] if len(anterior.split()) > 2 else "antes"
    t = pd.DataFrame({"Mesero": list(M.index)})
    t["Días"] = M["dias"].to_numpy(dtype=float)
    t["Mesas"] = M["mesas"].to_numpy(dtype=float)
    t["Personas"] = M["personas"].to_numpy(dtype=float)
    t["Venta"] = M["venta"].to_numpy(dtype=float)
    t["Productos"] = M["items"].to_numpy(dtype=float)
    t["Propina"] = M["propina"].to_numpy(dtype=float)
    t["Parte"] = ((M["propina"] / total_prop).to_numpy(dtype=float)
                  if total_prop else np.zeros(len(M)))

    def _div(a, b):
        return (a / b.where(b > 0)).fillna(0.0).to_numpy(dtype=float)
    t["% de la venta"] = _div(M["propina"], M["venta"])
    t["Por mesa"] = _div(M["propina"], M["mesas"])
    t["Por persona"] = _div(M["propina"], M["personas"])
    # SIN VACÍOS (regla #529): un NaN se pinta «None». Sin mesas con
    # tarjeta va −1 («—»); un mesero sin propina el mes anterior va +∞
    # («nuevo»), como la variación de Análisis de platos.
    t["Sin propina"] = np.where(M["tarjeta"] > 0,
                                M["sin_propina"] / M["tarjeta"].where(
                                    M["tarjeta"] > 0, 1), -1.0)
    ant = R0["propina"] if not R0.empty else pd.Series(dtype=float)
    t[f"vs {mes_ant}"] = [
        (p / ant[m] - 1) if ant.get(m, 0) > 0 else np.inf
        for m, p in zip(M.index, M["propina"])]
    t["Pozo común"] = [float(rep.loc[m, "pozo"]) if m in rep.index else 0.0
                       for m in M.index]
    ss["_vt_mes_filas"] = list(M.index)
    col_var = f"vs {mes_ant}"

    def _color_var(v):
        if not np.isfinite(v):
            return f"color:{GRIS_TEXTO}"
        return f"color:{AJUSTE_POS_TEXTO if v >= 0 else AJUSTE_NEG_TEXTO}"

    sty = (t.style
           .format("{:,.0f}", subset=["Días", "Mesas", "Personas",
                                      "Productos"])
           .format("S/ {:,.0f}", subset=["Venta", "Propina", "Pozo común"])
           .format("{:.0%}", subset=["Parte"])
           .format("{:.1%}", subset=["% de la venta"])
           .format("S/ {:,.2f}", subset=["Por mesa", "Por persona"])
           .format(lambda v: "—" if v < 0 else f"{v:.0%}",
                   subset=["Sin propina"])
           .format(lambda v: "nuevo" if not np.isfinite(v)
                   else f"{'+' if v >= 0 else '−'}{abs(v):.0%}",
                   subset=[col_var])
           .map(_color_var, subset=[col_var]))
    cfg = {
        "Mesero": st.column_config.TextColumn(pinned=True, width=130),
        "Días": st.column_config.Column(width=48,
                                        help="Días con al menos una mesa"),
        "Mesas": st.column_config.Column(
            width=56, help="Pedidos con venta, como el Analítico por mozo "
                           "del POS"),
        "Personas": st.column_config.Column(width=68, help="Adultos"),
        "Productos": st.column_config.Column(
            width=74, help="Unidades vendidas, bebidas incluidas, como la "
                           "«Cantidad» del Analítico por mozo"),
        "Parte": st.column_config.Column(
            width=52, help="Parte de la propina del período"),
        "Sin propina": st.column_config.Column(
            width=80, help="Mesas pagadas con tarjeta que no dejaron "
                           "propina"),
        col_var: st.column_config.Column(
            width=70, help=f"Propina contra {anterior}"),
        "Pozo común": st.column_config.Column(
            width=90, help="Lo que le tocaría si la propina de cada turno "
                           "se repartiera en partes iguales entre los "
                           "meseros de ese turno"),
    }
    st.dataframe(sty, key=_key("vt_mes_tabla"), on_select="rerun",
                 selection_mode="single-row", hide_index=True, row_height=27,
                 height=alturas.por_filas(len(t) + 1, px_fila=27, extra=3,
                                          minimo=0, rol=alturas.VENTAS_PLATOS),
                 column_config=cfg)


def _nota_tabla(R, R0, M, anterior):
    notas = ["Clic en un mesero para ver su detalle abajo."]
    s = R.loc[SIN_MESERO] if SIN_MESERO in R.index else None
    if s is not None and s["mesas"] > 0:
        notas.append(f"Sin mesero (Rappi y para llevar): {int(s['mesas']):,} "
                     f"pedidos, S/ {s['venta']:,.0f}, sin propina.")
    if not R0.empty:
        idos = [m for m in R0.index if m != SIN_MESERO and m not in M.index
                and R0.loc[m, "propina"] > 0]
        if idos:
            partes = [f"{m} (S/ {R0.loc[m, 'propina']:,.0f})" for m in idos]
            lista = (", ".join(partes[:-1]) + " y " + partes[-1]
                     if len(partes) > 1 else partes[0])
            notas.append(f"En {anterior} también atendieron {lista}: en este "
                         "período no tienen mesas.")
    notas.append("La propina sólo se registra en pagos con tarjeta.")
    return " ".join(notas)


def _tarjeta_planilla(P, d_pagos, turno, periodo, R, rep):
    """La planilla mesero × día, propia o como pozo común, y el Excel."""
    with st.container(border=True,
                      key="ajuste_graf_card_izq_ventas_meseros_planilla"):
        # columnas-internas: el título, el reparto y la descarga
        c1, c2, c3 = st.columns([2.4, 1.3, 0.9], vertical_alignment="center")
        with c2:
            modo = st.segmented_control(
                "Reparto", REPARTOS, default=REPARTOS[0], required=True,
                key="vt_mes_reparto", label_visibility="collapsed",
                help="**Pozo común**: la propina de cada turno repartida en "
                     "partes iguales entre los meseros que atendieron mesas "
                     "en ese turno.") or REPARTOS[0]
        with c1:
            st.markdown(
                f'<div class="vt-mes-tit">Planilla de propinas · '
                f'{escape(turno.lower())} · {escape(modo.lower())}</div>',
                unsafe_allow_html=True)
        soles, mesas = planilla(P, modo)
        if soles.empty:
            st.info("Sin propinas de meseros en el rango.")
            return
        z = pozo(P)
        with c3:
            st.download_button(
                "Descargar Excel",
                data=excel(periodo, turno, modo, R, rep, soles,
                           mesas, z, del_turno(pagos_con_propina(d_pagos),
                                               turno)),
                file_name=f"propinas_{periodo.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument."
                     "spreadsheetml.sheet",
                key="vt_mes_excel", width="stretch")

        # «·» donde no atendió ese día: −1, que el Styler escribe así (un
        # NaN se pintaría «None», regla #529).
        dias = [pd.Timestamp(d) for d in soles.columns]
        # «lun 1» dentro de un mes; con más de uno se repetiría (dos «lun 1»
        # serían dos columnas con el mismo nombre), y va la fecha.
        etq = [f"{_DIAS_ES[d.dayofweek]} {d.day}" for d in dias]
        if len(set(etq)) < len(etq):
            etq = [f"{d.day}/{d.month:02d}" for d in dias]
        if len(set(etq)) < len(etq):
            etq = [f"{d:%d/%m/%y}" for d in dias]
        v = soles.where(mesas > 0, other=np.where(soles > 0, soles, -1.0))
        tabla = pd.DataFrame(v.to_numpy(dtype=float), columns=etq)
        tabla.insert(0, "Mesero", list(soles.index))
        tabla["Total"] = soles.sum(axis=1).to_numpy(dtype=float)
        if modo == REPARTOS[1]:
            propia = z.groupby("mesero")["propia"].sum()
            tabla["Diferencia"] = (tabla["Total"]
                                   - propia.reindex(soles.index).fillna(0.0)
                                   .to_numpy(dtype=float))
        tot = {"Mesero": "Total del día"}
        for e, d in zip(etq, soles.columns):
            tot[e] = float(soles[d].sum())
        tot["Total"] = float(soles.to_numpy().sum())
        if "Diferencia" in tabla:
            tot["Diferencia"] = 0.0
        tabla = pd.concat([tabla, pd.DataFrame([tot])], ignore_index=True)
        tope = float(soles.to_numpy().max()) or 1.0
        n = len(soles.index)

        def _calor(col):
            if col.name not in etq:
                return [""] * len(col)
            return [f"background-color:{_con_alpha(ACENTO, 0.06 + 0.42 * x / tope)}"
                    if (i < n and x > 0) else "" for i, x in enumerate(col)]

        sty = (tabla.style
               .format(lambda x: "·" if x < 0 else f"{x:,.0f}", subset=etq)
               .format("S/ {:,.0f}", subset=["Total"])
               .apply(_calor, axis=0))
        if "Diferencia" in tabla:
            sty = (sty.format(lambda x: f"{'+' if x >= 0 else '−'}"
                                        f"S/ {abs(x):,.0f}",
                              subset=["Diferencia"])
                   .map(lambda x: f"color:{AJUSTE_POS_TEXTO if x > 0.5 else AJUSTE_NEG_TEXTO if x < -0.5 else GRIS_TEXTO}",
                        subset=["Diferencia"]))
        cfg = {"Mesero": st.column_config.TextColumn(pinned=True, width=130),
               "Total": st.column_config.Column(width=78)}
        for e in etq:
            cfg[e] = st.column_config.Column(width=52)
        st.dataframe(sty, key="vt_mes_planilla", hide_index=True,
                     row_height=27, column_config=cfg,
                     # + la barra de deslizar de costado, que tapaba la
                     # fila «Total del día» (medido a 1366).
                     height=alturas.por_filas(len(tabla) + 1, px_fila=27,
                                              extra=3 + _BARRA_H, minimo=0,
                                              rol=alturas.VENTAS_PLATOS))
        st.caption(
            ("Pozo común: la propina de cada turno se reparte en partes "
             "iguales entre los meseros que atendieron al menos una mesa en "
             "ese turno; «Diferencia» es lo que gana o pierde cada uno contra "
             "su propina. Es una regla supuesta: si el restaurante reparte de "
             "otra forma, se cambia. ")
            if modo == REPARTOS[1] else
            ("El día es el del comprobante, como el reporte de Propinas del "
             "POS. «·»: no atendió mesas ese día. ")
            + "El Excel trae además el detalle por turno y cada pago con "
              "propina.")



def _tarjeta_foco(foco, P, items, M, t, turno, periodo, fin, filtrar_cb,
                  firma):
    """El detalle del mesero elegido: cómo dejan propina sus mesas, sus
    últimos 12 meses y lo que vendió."""
    r = M.loc[foco]
    with st.container(border=True,
                      key="ajuste_graf_card_izq_ventas_meseros_foco"):
        parte = r["propina"] / t["propina"] if t["propina"] else 0.0
        pct = r["propina"] / r["venta"] if r["venta"] > 0 else 0.0
        st.markdown(
            f'<div class="vt-mes-tit"><b>{escape(foco)}</b> · '
            f'{escape(periodo)}{" · " + escape(turno.lower()) if turno != TURNOS[0] else ""}'
            f'</div><div class="vt-mes-sub">{int(r["mesas"]):,} mesas en '
            f'{int(r["dias"])} {"día" if r["dias"] == 1 else "días"} y '
            f'{r["personas"]:,.0f} personas. Dejaron S/ {r["propina"]:,.0f} de '
            f'propina: el {parte:.0%} del total y el {pct:.1%} de su venta.'
            f'</div>', unsafe_allow_html=True)
        # columnas-internas: los dos gráficos y lo que vendió
        g1, g2, g3 = st.columns([1.05, 1.15, 1.0], gap="medium")
        with g1:
            st.markdown('<div class="vt-mes-h3">Cómo dejan propina sus mesas'
                        '</div>', unsafe_allow_html=True)
            _grafico_tramos(foco, distribucion(P))
        with g2:
            st.markdown('<div class="vt-mes-h3">Propina por mes · últimos '
                        '12 meses</div>', unsafe_allow_html=True)
            ini12 = (pd.Timestamp(fin).to_period("M")
                     - (_MESES_EVOLUCION - 1)).start_time.date()
            with st.spinner("Trayendo los 12 meses…"):
                P12 = _pedidos_tramo(ini12, fin, filtrar_cb, firma)
            _grafico_meses(foco, del_turno(P12, turno), fin)
        with g3:
            st.markdown('<div class="vt-mes-h3">Lo que vendió</div>',
                        unsafe_allow_html=True)
            _vendido(foco, items)


def _grafico_tramos(foco, D):
    """Barras del mesero y una marca con el equipo, por tramo de %."""
    if foco not in D.index or D.loc[foco].sum() == 0:
        st.caption("Sin mesas pagadas con tarjeta en el rango.")
        return
    n = D.loc[foco]
    eq = D.sum()
    sh = n / n.sum()
    she = eq / eq.sum() if eq.sum() else eq * 0.0
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=list(TRAMOS), x=sh.to_numpy() * 100, orientation="h", name=foco,
        marker=dict(color=ACENTO), width=0.5,
        text=[f"{v:.0%}" for v in sh], textposition="outside",
        cliponaxis=False,
        customdata=np.column_stack([n.to_numpy(), she.to_numpy() * 100]),
        hovertemplate=("%{y}: %{x:.1f}% de sus mesas con tarjeta "
                       "(%{customdata[0]:.0f})<br>Equipo: %{customdata[1]:.1f}%"
                       "<extra></extra>")))
    fig.add_trace(go.Scatter(
        y=list(TRAMOS), x=she.to_numpy() * 100, mode="markers", name="Equipo",
        marker=dict(symbol="line-ns", size=16,
                    line=dict(width=2.5, color=TEXTO_PRINCIPAL)),
        hovertemplate="Equipo: %{x:.1f}%<extra></extra>"))
    _compras_layout(fig, alto=alturas.VENTAS_MESEROS_FIG)
    tope = max(float(sh.max()), float(she.max())) * 100
    fig.update_layout(
        margin=dict(l=10, r=10, t=26, b=4), bargap=0.35,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    font=dict(size=11)),
        xaxis=dict(visible=False, range=[0, tope * 1.3], fixedrange=True),
        # Categorías SIEMPRE: «0 %» y «10 %» parecen números y Plotly los
        # ponía en un eje lineal, con dos barras en 0 y en 10 (#325).
        yaxis=dict(type="category", autorange="reversed",
                   showticklabels=True, showgrid=False, fixedrange=True,
                   tickfont=dict(size=11, color=GRIS_TEXTO)))
    st.plotly_chart(fig, key="vt_mes_tramos",
                    config={"displaylogo": False, "displayModeBar": False})
    st.caption(f"Sobre {int(n.sum()):,} mesas pagadas con tarjeta. La marca "
               "negra es el equipo.")


def _grafico_meses(foco, P12, fin):
    """Columnas: la propina del mesero abajo, la del resto encima."""
    prop, venta = mensual(P12)
    if prop.empty:
        st.caption("Sin datos de los meses anteriores.")
        return
    total = prop.sum(axis=1)
    fo = prop[foco] if foco in prop.columns else total * 0.0
    resto = total - fo
    etq = [f"{MESES_ABR_ES[int(m[5:7]) - 1]}"
           + ("*" if m == pd.Timestamp(fin).strftime("%Y-%m") else "")
           for m in prop.index]
    pct = [f"{(t / v):.1%}" if v else "—" for t, v in zip(total, venta)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=etq, y=fo.to_numpy(), name=foco, marker=dict(color=ACENTO),
        # Una lista de pares y no `np.column_stack`: con el % como texto,
        # numpy pasaría el total a texto y `:,.0f` no lo formatearía.
        customdata=[[float(a), b] for a, b in zip(total, pct)],
        hovertemplate=(f"{escape(foco)}: S/ %{{y:,.0f}}<br>Total del mes: "
                       "S/ %{customdata[0]:,.0f} · %{customdata[1]} de la "
                       "venta<extra></extra>")))
    fig.add_trace(go.Bar(
        x=etq, y=resto.to_numpy(), name="Resto del equipo",
        marker=dict(color=LAVANDA_BORDE),
        hovertemplate="Resto del equipo: S/ %{y:,.0f}<extra></extra>"))
    _compras_layout(fig, alto=alturas.VENTAS_MESEROS_FIG)
    fig.update_layout(
        barmode="stack", bargap=0.35, margin=dict(l=10, r=10, t=26, b=4),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                    font=dict(size=11)),
        # Categorías SIEMPRE: el eje de fecha rotula en inglés (#241) y un
        # rótulo que parece número cambia el tipo del eje (#448).
        xaxis=dict(type="category", fixedrange=True, tickfont=dict(size=10.5)),
        yaxis=dict(fixedrange=True, showticklabels=True, tickformat="~s",
                   tickfont=dict(size=10, color=GRIS_TEXTO)))
    st.plotly_chart(fig, key="vt_mes_meses",
                    config={"displaylogo": False, "displayModeBar": False})
    st.caption("El asterisco marca el mes en curso, que va hasta hoy.")


def _vendido(foco, items):
    """Las unidades por grupo y dos tablas: platos y bebidas."""
    platos, bebidas, grupos = vendido(items, foco)
    if grupos.empty:
        st.caption("Sin ventas en el rango.")
        return
    st.markdown(
        '<div class="vt-mes-chips">' + "".join(
            f'<span>{escape(g or "—")} · {u:,.0f} u</span>'
            for g, u in grupos.items()) + "</div>", unsafe_allow_html=True)
    for tabla, titulo, key in ((platos, "Platos", "vt_mes_platos"),
                               (bebidas, "Bebidas", "vt_mes_bebidas")):
        if tabla.empty:
            continue
        t = pd.DataFrame({titulo: tabla["prod"].to_numpy(),
                          "Unid.": tabla["u"].to_numpy(dtype=float),
                          "Venta": tabla["venta"].to_numpy(dtype=float)})
        st.dataframe(
            t.style.format("{:,.0f}", subset=["Unid."])
             .format("S/ {:,.0f}", subset=["Venta"]),
            key=key, hide_index=True, row_height=27,
            height=alturas.por_filas(len(t) + 1, px_fila=27, extra=3,
                                     minimo=0, rol=alturas.VENTAS_PLATOS),
            column_config={titulo: st.column_config.TextColumn(width=170),
                           "Unid.": st.column_config.Column(width=52),
                           "Venta": st.column_config.Column(width=76)})
