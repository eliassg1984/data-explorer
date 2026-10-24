"""
graficos.ventas_meseros — vista «Meseros» del dashboard de Ventas: las
PROPINAS por mesero, con lo que dan los reportes del POS y lo que no dan.
Desde la regla #719 la UI vive en `ventas_meseros.js` y `.css`: lista y
ficha en la primera tarjeta, planilla y mapa en la segunda. Sólo la fecha
pide una corrida; el Excel para pagar sigue saliendo de `excel`.

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
import streamlit as st

import definicion_venta as dv
import franja_fecha
from data import REPORTES, cargar_rango, sello_datos
from tema import AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, GRIS_TEXTO
from graficos.base import (_resolver, preservar_widgets,
                           selector_fecha_tarjeta, una_vez_por_corrida)

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

_KEYS_WIDGET_MES = ()
"""Sin widgets nativos de control: el estado vive en window.__vtMes (#719)."""

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


def excel(periodo, turno, modo, R, rep, soles, mesas, z, pagos, contexto=None):
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

    if contexto:
        ws = wb.add_worksheet("Contexto")
        _cabecera(ws, 0, ["Dato", "Valor"])
        for i, (k, v) in enumerate(contexto.items(), start=1):
            ws.write(i, 0, k)
            ws.write(i, 1, v)
        ws.set_column(0, 0, 23)
        ws.set_column(1, 1, 85)
        ws.freeze_panes(1, 0)
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
from pathlib import Path

_PIEZA = st.components.v2.component(
    "ventas_meseros",
    css=(Path(__file__).parent / "ventas_meseros.css").read_text(encoding="utf-8"),
    js=(Path(__file__).parent / "_xlsx.js").read_text(encoding="utf-8")
    + (Path(__file__).parent / "ventas_meseros.js").read_text(encoding="utf-8"),
)
_K_PIEZA_CACHE = "_vt_mes_pieza_cache"


@una_vez_por_corrida
@st.fragment
def _ventas_meseros(d_pagos, filtrar_cb=None, firma=None):
    """Firma de la vista conservada (#357). Sólo la fecha pide Python (#719)."""
    from graficos import ventas_meseros_datos as datos

    if st.session_state.pop("vt_mes_fecha_flag", False):
        preservar_widgets(_KEYS_WIDGET_MES)
        st.rerun(scope="app")
    with st.container(key="vt_mes_pieza_wrap"):
        with st.container(key="vt_mes_fecha"):
            selector_fecha_tarjeta("vt_mesf", "vt_mes_fecha_flag", categoria=None,
                                   label="Elegir fechas")
        ini, fin = _rango(None)
        archivo = REPORTES.get("Ventas", {}).get("archivo", "ventas.parquet")
        clave = (sello_datos(archivo), firma, ini, fin, id(d_pagos),
                 None if d_pagos is None else d_pagos.shape)
        cache = st.session_state.get(_K_PIEZA_CACHE)
        if cache is None or cache[0] != clave:
            with st.spinner("Preparando propinas, comparación y planillas…"):
                P, items = preparar(d_pagos)
                if P is None or P.empty:
                    st.info("Sin ventas en este rango o sin las columnas necesarias. Elegí otras fechas.")
                    return
                ini, fin = _rango(P)
                ini0, fin0 = periodo_anterior(ini, fin)
                P0 = _pedidos_tramo(ini0, fin0, filtrar_cb, firma)
                ini12 = (pd.Timestamp(fin).to_period("M") - 11).start_time.date()
                P12 = _pedidos_tramo(ini12, fin, filtrar_cb, firma)
                mensaje = datos.armar(d_pagos, P, items, P0, P12, (ini, fin), firma)
                st.session_state[_K_PIEZA_CACHE] = (clave, mensaje)
        else:
            mensaje = cache[1]
        _PIEZA(key="vt_mes_pieza", data=mensaje, width="stretch")
