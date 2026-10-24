"""
graficos.ventas_resumen — Ventas › «Venta por Periodo» (id «Resumen
ejecutivo»): la venta por período partida por canal, sus indicadores, el
Resumen en nueve grupos de columnas y el Detalle de pedidos y platos.

DESDE EL 2026-10-23 ES UNA PIEZA PROPIA (regla #714): `ventas_periodo.js` +
`ventas_periodo.css`, sobre el boceto aprobado con sus cinco mejoras
(https://claude.ai/artifact/Pb748JiyYM8Wapb49KReMi). Hasta ese día cada clic
—el grano, un filtro, una barra, una subvista, una fila— era una corrida de
2,0 a 4,6 s (medido en la laptop con R2); ahora sólo la fecha vuelve a
Python. La historia de la vista de antes —Plotly, tres AgGrid, la pastilla
«Detalle» con interruptores— está en las reglas #515 a #525, #590 a #592 y
#667/#668: la pieza hace lo mismo, con las mismas cuentas.

LO QUE MANDA PYTHON (`armar_periodo`) y por qué en esa forma. Las cuentas
del gráfico, los indicadores, las nueve subvistas y las tablas de pedidos,
meseros, servicios y comprobantes salen de la venta sumada por COMPROBANTE
Y GRUPO (`unidades`): los filtros de Grupo, Servicio, Canal y Documento se
aplican ahí, y los clientes se cuentan por comprobante con la regla de
`definicion_venta.pax_por`. Sólo la tabla de PLATOS necesita las líneas, y
de ellas viajan las de todo el rango si cabe en `_DIAS_LINEAS` y, si no,
las de los últimos `_DIAS_RECIENTES`: doce meses de líneas son 6,5 MB; sumado
por comprobante, el mensaje entero es ~3,4 MB. Un período más viejo pide sus líneas con el
trigger `lineas` y las recibe en un segundo montaje chico
(`parte: "lineas"`), para que el mensaje grande no se vuelva a mandar.

Lo que sigue en este módulo además de eso son las cuentas puras que la pieza
rehace en el navegador —el IGV, lo vendido sin costo, las formas de pago,
las subvistas, los indicadores, los comprobantes, los grupos del Detalle—:
son la referencia contra la que `test_ventas_periodo.py` compara el `.js`.
Si se toca una, se toca la otra.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import cortes
import definicion_venta as dv
from tema import ERROR, EXITO, GRIS_TEXTO
from graficos.base import _resolver, preservar_widgets, selector_fecha_tarjeta
from graficos.compras._comun import _periodo_serie
from graficos import alturas
from graficos.recetas_comun import TASA_RECARGO
from utils import fmt_k

MAX_DIAS = 30    # tope de barras legibles en Día. Mismo espíritu que
                 # MAX_SEMANAS de compras/volatilidad.py (regla #74): con un
                 # rango de «todo el año» cargado, el grano Día muestra sólo
                 # los últimos 30 días CON datos. Lo usan también Mix y Control.

_KEYS_WIDGET_RESUMEN = ()
"""Los controles de la vista que la recarga de fecha (`st.rerun(scope=
"app")`) tendría que preservar (regla #373). Ninguno desde la pieza: lo que
se elige vive en el navegador (`window.__vtPeriodo`). La guarda de
`test_graficos.py` lee esta tupla con `ast.literal_eval`."""

_SUBVISTAS = ("Venta", "Clientes", "Canales", "Propinas", "Pagos",
              "Descuentos", "Cortesías", "Costo", "Cuadre")
"""Los grupos de columnas del Resumen (regla #519). Una subvista que el
parquet no permite (sin propina, un solo canal) no se ofrece de más."""

# «Ver por» del Detalle (regla #667): de qué es cada fila de la tabla de la
# izquierda. La de al lado son siempre los platos de la fila elegida.
_VER_PEDIDO, _VER_MESERO, _VER_SERVICIO, _VER_COMPROBANTE = (
    "Pedido", "Mesero", "Servicio", "Comprobante")
_VER_COLUMNA = {_VER_MESERO: "mesero", _VER_SERVICIO: "serv"}
"""La columna de `tabla` que agrupa cada «Ver por» de grupos. Pedido y
Comprobante no agrupan: una fila es un pedido o un documento."""


def _ver_disponibles(tabla):
    """Los «Ver por» que el parquet permite: sin la columna, no se ofrece."""
    hay = set(tabla.columns)
    return [_VER_PEDIDO] + [v for v, ok in (
        (_VER_MESERO, "mesero" in hay), (_VER_SERVICIO, "serv" in hay),
        (_VER_COMPROBANTE, bool({"ldoc", "doc"} & hay))) if ok]


# Abreviaturas en español para el eje/tabla — Plotly y pandas rotulan en
# inglés si no se les dice otra cosa (misma trampa que arquitectura.md #241).
_DIAS_ABR_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

_SIN_CANAL = "Sin canal"
_SIN_SERVICIO = "Sin servicio"
_SIN_MESERO = "Sin mesero"   # el de `ventas_meseros.SIN_MESERO`, que importa
                             # de acá: traerlo sería un import circular

_DIAS_LINEAS = 92
"""Con un rango de hasta tantos días viajan todas sus líneas."""

_DIAS_RECIENTES = 35
"""Con uno más largo, las de los últimos tantos días con ventas (el grano Día
muestra 30): para un período más viejo, la pieza pide las suyas."""

def _con_alpha(_hex, _a):
    """`#rrggbb` → `rgba(r,g,b,a)`. El foco se atenúa por COLOR y no con
    `marker.opacity` por punto: esa lista sobre barras crashea Plotly en el
    navegador. Copia de `compras/semanal.py::_con_alpha` (regla #476)."""
    _h = _hex.lstrip("#")
    _r, _g, _b = (int(_h[_i:_i + 2], 16) for _i in (0, 2, 4))
    return f"rgba({_r},{_g},{_b},{_a})"


def _fmt_dia(dt):
    """`Timestamp` → «Sáb 20/09», con el día de semana en español."""
    return f"{_DIAS_ABR_ES[dt.weekday()]} {dt.day:02d}/{dt.month:02d}"


def _canal_legible(s):
    """La columna de canal como texto, con los nulos nombrados. Pasa por
    `object` antes del `where` porque el parquet puede traerla como
    categórica, y a una categórica no se le escribe un valor que no tenía."""
    s = s.astype("object")
    return s.where(s.notna(), _SIN_CANAL).astype(str).str.strip()


def _texto_limpio(s):
    """Texto sin espacios de los bordes, con los nulos como «». Por `object`
    y con el `where` ANTES del `astype` (`ventas_meseros._texto`): una
    categórica no acepta un valor nuevo, y en la pandas 2.2 de Cloud un NaN
    pasa a «nan» con `astype(str)`."""
    s = s.astype("object")
    return s.where(s.notna(), "").astype(str).str.strip()


def _nombre_mesero(s):
    """El mesero en Title Case, como «Análisis de Meseros»; vacío, «»."""
    return _texto_limpio(s).str.title()


def _fmt_var_venta(pct):
    """`(texto, color)` de una variación: «+12%» verde, «−4.7%» rojo.

    El formato de `compras._comun._fmt_variacion` (un decimal debajo del
    10 %, el menos tipográfico, «0%» gris) con el color al revés: en
    VENTAS subir es la buena noticia; en Compras, gastar más es rojo."""
    dec = 1 if abs(pct) < 10 else 0
    if round(abs(pct), dec) == 0:
        return "0%", GRIS_TEXTO
    txt = f"{abs(pct):.{dec}f}%"
    return ("+" + txt, EXITO) if pct > 0 else ("−" + txt, ERROR)


def _renglones_barra(total, var):
    """Los renglones de la etiqueta de una barra, como `(plano, html)`: el
    total y la variación contra la barra anterior (`var` es la tupla de
    `_variaciones`). Misma forma que `semanal._renglones_etiqueta`: un
    período que el rango corta dice «parcial» en vez de un porcentaje."""
    if not total:
        return []
    _t = fmt_k(total)
    salida = [(_t, _t)]
    estado, pct, _ = var
    if estado == "ok":
        _v, _c = _fmt_var_venta(pct)
        salida.append((_v, f"<span style='color:{_c}'><b>{_v}</b></span>"))
    elif estado == "parcial":
        salida.append(("parcial", f"<span style='color:{GRIS_TEXTO}'>"
                                  "<i>parcial</i></span>"))
    return salida


def _hover_var_venta(var, nombre_ant):
    """El renglón del hover con la variación, o POR QUÉ no la hay. Empieza
    con `<br>`. Es `compras._comun._hover_variacion` con el color de Ventas
    y sin contar días (el «parcial» ya lo dice la etiqueta)."""
    estado, pct, _ = var
    if estado == "ok":
        _t, _c = _fmt_var_venta(pct)
        return (f"<br>vs {nombre_ant}: "
                f"<span style='color:{_c}'><b>{_t}</b></span>")
    if estado == "parcial":
        return "<br><i>Período incompleto en el rango: sin variación</i>"
    if estado == "ant_parcial":
        return (f"<br><i>Sin variación: la barra anterior ({nombre_ant}) "
                "está incompleta en el rango</i>")
    if estado == "sin_base":
        return f"<br><i>Sin variación: {nombre_ant} no vendió</i>"
    return "<br><i>Primera barra: sin anterior para comparar</i>"


def _nota_var_venta(var, nombre_ant):
    """Lo mismo que `_hover_var_venta`, en texto plano: el tooltip de la
    columna «Variación» de la tabla (AG Grid no entiende HTML)."""
    estado, pct, _ = var
    if estado == "ok":
        return f"vs {nombre_ant}: {_fmt_var_venta(pct)[0]}"
    if estado == "parcial":
        return "Período incompleto en el rango: sin variación"
    if estado == "ant_parcial":
        return (f"Sin variación: la barra anterior ({nombre_ant}) está "
                "incompleta en el rango")
    if estado == "sin_base":
        return f"Sin variación: {nombre_ant} no vendió"
    return "Primera barra: sin anterior para comparar"


# ── El IGV mueve el % de costo sin que cambie ningún costo (regla #590) ─────
# El % de costo es costo ÷ NETO, y el neto es el precio sin IGV ni recargo:
# con el mismo precio de carta, una tasa de IGV más baja deja más neto y un
# % más bajo. Medido en las ventas (IGV ÷ neto de cada línea): 18 % hasta el
# 9 de junio de 2025, 10 % desde el 10, y 10,5 % desde el 10 de febrero de
# 2026. El primero baja el % de costo un 6 % de sí mismo —~2 pp sobre un
# 35 %—; el segundo lo sube una décima. La tasa sale de las ventas y no se
# escribe acá: cambia por ley (regla #514). La comparten el Resumen y el Mix.
_UMBRAL_IGV = 0.01
"""Un cambio de la tasa de un punto o más se marca. El de 10 a 10,5 % no:
mueve el % de costo una décima, y una marca que no cambia nada es ruido."""


def cambios_de_igv(fecha, igv, neto):
    """Los días en que cambió la tasa de IGV de lo vendido, en un punto o
    más: `[(día, tasa de antes, tasa de después)]`, en orden.

    La tasa de un día es la de la MAYORÍA de sus líneas (la moda de IGV ÷
    neto) y no la de la suma: un día flojo con alguna línea exonerada no es
    un cambio de ley. Sólo cuentan las líneas con neto (las notas de crédito
    restan y no dicen la tasa). Pura."""
    t = pd.DataFrame({
        "dia": pd.to_datetime(pd.Series(fecha), errors="coerce").dt.normalize(),
        "igv": pd.to_numeric(pd.Series(igv), errors="coerce"),
        "neto": pd.to_numeric(pd.Series(neto), errors="coerce"),
    })
    t = t[t["dia"].notna() & t["igv"].notna() & (t["neto"] > 0.5)]
    if t.empty:
        return []
    t = t.assign(tasa=(t["igv"] / t["neto"]).round(3))
    moda = (t.groupby(["dia", "tasa"]).size().rename("n").reset_index()
            .sort_values(["dia", "n", "tasa"], ascending=[True, False, True])
            .drop_duplicates("dia").reset_index(drop=True))
    antes = moda["tasa"].shift()
    hubo = (moda["tasa"] - antes).abs() >= _UMBRAL_IGV
    return [(pd.Timestamp(d), float(a), float(b)) for d, a, b
            in zip(moda.loc[hubo, "dia"], antes[hubo], moda.loc[hubo, "tasa"])]


def _tasa(t):
    """0.18 → «18%», 0.105 → «10.5%»."""
    return f"{t * 100:g}%"


def marca_igv(antes, despues):
    """La marca corta de un período: «IGV 18→10%»."""
    return f"IGV {antes * 100:g}→{despues * 100:g}%"


def efecto_igv(antes, despues):
    """En qué proporción cambia el % de costo SÓLO por pasar de una tasa de
    IGV a otra, con el mismo precio y el mismo costo: −0,061 de 18 a 10 %. El
    recargo es el del restaurante (`recetas_comun.TASA_RECARGO`)."""
    return (1 + despues + TASA_RECARGO) / (1 + antes + TASA_RECARGO) - 1


def nota_igv(dia, antes, despues, pcosto=None):
    """La frase que explica la marca: qué día, de qué tasa a cuál y cuánto
    mueve eso el % de costo — en puntos si se sabe de qué % se parte. Pura."""
    rel = efecto_igv(antes, despues)
    txt = (f"El {pd.Timestamp(dia):%d/%m/%Y} el IGV pasó de {_tasa(antes)} a "
           f"{_tasa(despues)} del neto: con el mismo precio y el mismo costo, ")
    if pcosto:
        pp = rel * pcosto * 100
        txt += (f"un % de costo de {pcosto:.1%} pasa a {pcosto * (1 + rel):.1%} "
                f"({'+' if pp >= 0 else '−'}{abs(pp):.1f} pp)")
    else:
        txt += (f"el % de costo {'baja' if rel < 0 else 'sube'} un "
                f"{abs(rel):.1%} de sí mismo")
    return txt + " sin que cambie ningún costo."


# ── Lo que se vendió sin costo cargado (regla #590) ──────────────────────────
# La columna «Sin costo» del Resumen dice CUÁNTO desde el 2026-09-24; esto
# dice QUÉ: lo que hay que corregir en el POS. El costo con que se vende es
# una foto que el POS no corrige después (regla #557), así que lo vendido sin
# costo baja el % de costo de ese período para siempre.
def productos_sin_costo(tabla):
    """Lo vendido SIN costo cargado, de mayor a menor venta: `({clave:
    [(producto, venta)]}, [(producto, venta)])` — por período y en el rango.

    El mismo criterio que la columna «Sin costo» (`pc <= 0`, venta con
    impuestos); una nota de crédito resta de su producto y lo que queda en
    cero o menos no se nombra. Pura."""
    if not {"pc", "prod", "clave", "venta"} <= set(tabla.columns):
        return {}, []
    sc = tabla[tabla["pc"] <= 0]
    if sc.empty:
        return {}, []
    g = sc.groupby(["clave", "prod"], as_index=False)["venta"].sum()
    g = g[g["venta"] > 0].sort_values(["clave", "venta", "prod"],
                                      ascending=[True, False, True])
    por = {k: list(zip(grp["prod"], grp["venta"].astype(float)))
           for k, grp in g.groupby("clave", sort=False)}
    tot = sc.groupby("prod")["venta"].sum()
    tot = tot[tot > 0].sort_values(ascending=False)
    return por, list(zip(tot.index, tot.astype(float)))


def texto_sin_costo(lista, n=2):
    """«Agua Munay c/gas, Agua Munay s/gas y 6 más». Pura."""
    if not lista:
        return ""
    resto = len(lista) - n
    return (", ".join(p for p, _ in lista[:n])
            + (f" y {resto} más" if resto > 0 else ""))


def detalle_sin_costo(lista, n=8):
    """«Agua Munay c/gas S/ 412 · Agua Munay s/gas S/ 380 · y 6 más». Pura."""
    if not lista:
        return ""
    resto = len(lista) - n
    return (" · ".join(f"{p} S/ {v:,.0f}" for p, v in lista[:n])
            + (f" · y {resto} más" if resto > 0 else ""))


# ── Las formas de pago (regla #592) ──────────────────────────────────────────
_POR_COBRAR = "C.POR COBRAR"
"""El estado del comprobante que se cobra después: es venta y no tiene pago."""

_NOMBRE_FORMA = {"NOTA DE CREDITO": "Nota de crédito",
                 "AMERICAN EXPRESS": "Amex"}
"""Nombres del POS que se leen mal tal cual («Nota de Credito», sin tilde)
o que no entran en una cabecera de 112 px («American Express»)."""


def forma_de_pago(tipo, tarjeta=None, otro=None):
    """La forma de cada pago: «Tarjeta de Crédito» se abre en su MARCA
    (Visa, Amex…) y «Varios» en su detalle (vale, nota de crédito usada
    como pago). Un pago sin tipo es «Sin forma». Pura, sobre Series."""
    def _txt(s):
        if s is None:
            return pd.Series("", index=tipo.index)
        return s.astype(object).where(s.notna(), "").astype(str).str.strip()

    t, tj, ot = _txt(tipo), _txt(tarjeta), _txt(otro)
    tl = t.str.lower()
    out = t.where(~(tl.str.startswith("tarjeta") & (tj != "")), tj)
    out = out.where(~((tl == "varios") & (ot != "")), ot)
    out = out.map(lambda x: _NOMBRE_FORMA.get(x.upper(), x))
    return out.where(out != "", "Sin forma")


_OTRAS_FORMAS = "Otras"
_MAX_FORMAS = 6
"""Columnas de forma de pago en la tabla. Septiembre de 2026 tuvo nueve
(efectivo, cinco tarjetas, cheque, vale y nota de crédito) y no entraban en
los ~1.200 px de la tarjeta: las que pasan de cinco van juntas en «Otras»."""


def formas_de_pago(d_pagos, col_fecha, gran, claves_ok,
                   max_formas=_MAX_FORMAS):
    """Lo cobrado por período y forma de pago: un DataFrame indexado por la
    clave del período con una columna por forma, de la que más cobró a la
    que menos — o None si el parquet no trae los pagos. Con más de
    `max_formas`, las que siguen a las primeras `max_formas − 1` van
    sumadas en «Otras», y sus nombres en `.attrs["otras"]`.

    Un pago se cuenta una vez (el parquet repite cada pago en cada ítem,
    regla #517) y sólo si su comprobante es venta: ni anulados ni
    cortesías. El monto es el del pago en SOLES (la consulta del Sheet
    convierte los pagos en dólares desde el 2026-10-03)."""
    if d_pagos is None or d_pagos.empty:
        return None
    c_pago = _resolver(d_pagos, ["Llave Local Documento Correlativo Pago"])
    c_monto = _resolver(d_pagos, ["Monto Tipo Pago Doc"])
    c_tipo = _resolver(d_pagos, ["Nombre Tipo Pago"])
    if not (c_pago and c_monto and c_tipo and col_fecha in d_pagos.columns):
        return None
    p = d_pagos[d_pagos[c_pago].notna()]
    if dv.CLASE in p.columns:
        p = p[p[dv.CLASE] == dv.VENTA]
    p = p.drop_duplicates(c_pago)
    if p.empty:
        return None
    t = pd.DataFrame({
        "fecha": pd.to_datetime(p[col_fecha], errors="coerce"),
        "monto": pd.to_numeric(p[c_monto], errors="coerce").fillna(0.0),
        "forma": forma_de_pago(
            p[c_tipo],
            p[_resolver(p, ["Nombre Tarjeta Pago"])]
            if _resolver(p, ["Nombre Tarjeta Pago"]) else None,
            p[_resolver(p, ["Nombre Otro Tipo Pago Doc"])]
            if _resolver(p, ["Nombre Otro Tipo Pago Doc"]) else None),
    }).dropna(subset=["fecha"])
    t["clave"] = _periodo_serie(t["fecha"], gran)
    t = t[t["clave"].isin(claves_ok)]
    if t.empty:
        return None
    # Por NOMBRE de columna (regla #481), en el orden de lo cobrado.
    pv = t.pivot_table(index="clave", columns="forma", values="monto",
                       aggfunc="sum", fill_value=0.0)
    orden = list(pv.sum().sort_values(ascending=False).index)
    if len(orden) <= max_formas:
        return pv[orden]
    quedan, resto = orden[:max_formas - 1], orden[max_formas - 1:]
    out = pv[quedan].copy()
    out[_OTRAS_FORMAS] = pv[resto].sum(axis=1)
    out.attrs["otras"] = resto
    return out


def _subvistas(vol_label, canales, hay, formas=(), otras=()):
    """`{nombre: (columnas, ayuda)}` de las subvistas del Resumen (regla #519),
    sólo las que el parquet permite. Cada columna es `(campo, rótulo, tipo,
    ancho, tooltip)` — ver `tablas.ventas_resumen.renderizar_dias_venta`.
    `formas`: las formas de pago, de la que más cobró a la que menos, y
    `otras`, las que van juntas en «Otras» (#592).

    Nació a pedido («poder alternar subvistas o agrupar columnas, de manera
    que visualmente pueda comparar la fila de un período con las demás»): la
    franja desplegable mostraba todo de UN período, y lo que se pedía era
    mirar una sola cosa en TODOS."""
    S = 104   # «S/ 459,612» a 13px + padding + la flecha de ordenar
    # «116.6% +80.4 pp revisar»: con 150 la bandera salía cortada en «r.»
    # (medido en el 12/09). Es el peor caso de la columna.
    _ANCHO_PCOSTO = 176
    out = {}
    venta = [
        ("carta", "Carta", "soles0", S, "Venta a precio de CARTA: lo que se "
                                         "habría cobrado sin descuentos"),
        ("valor", "Venta", "celda", 118, "Venta documentada, con IGV y recargo. "
                                         "Sin cortesías ni anulados"),
        ("neto", "Neto", "soles0", S, "Venta sin IGV ni recargo: la base del "
                                      "% de costo"),
        ("costo", "Costo histórico", "soles0", 132, "Costo histórico de lo vendido, incluidos combos y propiedades"),
        ("pcosto", "% costo", "celda", _ANCHO_PCOSTO, "Costo ÷ Neto, y su cambio en pp "
                                            "contra la barra anterior"),
    ]
    _sin = ("sin la venta de los canales que no registran clientes "
            "(Rappi)" if "sin_cli" in hay else "")
    if vol_label:
        venta += [
            ("pax", "Pax" if vol_label == "Clientes" else vol_label, "entero",
             72, f"{vol_label} del período"),
            ("ticket", "Ticket", "celda", 132,
             f"Venta ÷ {vol_label.lower()}"
             + (f", {_sin}" if _sin else "") + ". Y su variación"),
        ]
        if "ticket_neto" in hay:
            venta.append(("ticket_neto", "Ticket neto", "celda", 132,
                          "Neto (sin IGV ni recargo) ÷ "
                          f"{vol_label.lower()}: el «Ticket Pro.» de la "
                          "Liquidación de Cajero del POS"))
    venta.append(("variacion", "Var. venta", "var", S,
                  "Variación de la venta contra la barra anterior"))
    out["Venta"] = (venta, "Precios, % de costo, clientes, ticket y variación.")
    if vol_label == "Clientes" and "ticket" in hay:
        # CLIENTES (regla #591, a pedido: «¿podemos indicar ticket sin niños
        # y con niños?»). Los adultos son «Clientes», como el POS; los
        # niños, si la consulta los trae, dan el ticket por persona.
        cols = [("valor", "Venta", "celda", 118, "Venta documentada: pagados y por cobrar, menos notas de crédito")]
        if "sin_cli" in hay:
            cols.append(("sin_cli", "Fuera del ticket", "celda", 128,
                         "Venta de los canales que no registran clientes "
                         "(Rappi): no entra en ningún ticket"))
        cols.append(("pax", "Adultos", "entero", 84,
                     "Clientes: los adultos, como cuenta el POS"))
        con_ninos = "ninos" in hay
        if con_ninos:
            cols += [("ninos", "Niños", "entero", 72, "Niños de las mesas"),
                     ("personas", "Personas", "entero", 92,
                      "Adultos + niños")]
        cols.append(("ticket", "Ticket", "celda", 132,
                     "Venta ÷ adultos, y su variación"))
        if con_ninos:
            cols.append(("ticket_p", "Ticket c/ niños", "celda", 140,
                         "Venta ÷ personas (adultos + niños)"))
        if "ticket_neto" in hay:
            cols.append(("ticket_neto", "Ticket neto", "celda", 132,
                         "Neto (sin IGV ni recargo) ÷ adultos: el «Ticket "
                         "Pro.» de la Liquidación de Cajero del POS"))
        if "ticket_neto_p" in hay:
            cols.append(("ticket_neto_p", "Neto c/ niños", "celda", 132,
                         "Neto ÷ personas (adultos + niños)"))
        out["Clientes"] = (cols, (
            "Ticket por adulto y con niños, con impuestos y neto."
            if con_ninos else
            "Ticket por adulto. Los niños no vienen todavía en la consulta "
            "de ventas."))
    if len(canales) > 1:
        cols = [("valor", "Venta", "celda", 118, "Venta documentada: pagados y por cobrar, menos notas de crédito")]
        for k, cn in enumerate(canales):
            cols += [(f"c{k}_v", cn, "celda", 128,
                      f"Venta de {cn} y su variación contra la barra anterior"),
                     (f"c{k}_p", f"% {cn}", "celda", 118,
                      f"Qué parte de la venta fue de {cn}, y su cambio en pp")]
        out["Canales"] = (cols, "Venta y peso de cada canal.")
    if "propina" in hay:
        cols = [("valor", "Venta", "celda", 118, "Venta documentada: pagados y por cobrar, menos notas de crédito"),
                ("propina", "Propina", "celda", 118,
                 "Propinas del período (una por pago) y su variación"),
                ("pprop", "% de la venta", "celda", 132,
                 "Propina ÷ venta, y su cambio en pp")]
        if "prop_cli" in hay:
            cols.append(("prop_cli", "Por cliente", "soles", 104,
                         "Propina ÷ clientes"))
        cols.append(("n_prop", "Pagos c/propina", "entero", 124,
                     "Pagos que dejaron propina"))
        if vol_label:
            cols.append(("pax", "Pax", "entero", 72, "Clientes del período"))
        out["Propinas"] = (cols, "Una propina por pago.")
    if formas:
        # PAGOS (regla #592): lo cobrado por forma, con la marca de cada
        # tarjeta. Forma por forma + lo por cobrar = los comprobantes del
        # período (venta + las notas de crédito, que se pagan con la nota).
        cols = [("valor", "Venta", "celda", 118, "Venta documentada: pagados y por cobrar, menos notas de crédito")]
        for k, fm in enumerate(formas):
            _con = (", ".join(otras) if fm == _OTRAS_FORMAS and otras
                    else fm)
            cols.append((f"f{k}_v", fm, "celda", 112,
                         f"Pagado con {_con} y su parte de los pagos de comprobantes "
                         "del período"))
        cols += [("cobrado", "Pagos registrados", "celda", 150,
                  "Pagos de los comprobantes seleccionados, agrupados por la fecha del comprobante"),
                 ("por_cobrar", "Por cobrar", "celda", 112,
                  "Importe de comprobantes en estado por cobrar, según la última actualización")]
        out["Pagos"] = (cols, "Pagos asociados a los comprobantes del período; "
                              "un pago una vez y por cobrar aparte.")
    if "pdesc" in hay:
        cols = [("carta", "Carta", "soles0", S, "Venta a precio de carta"),
                ("valor", "Venta", "celda", 118, "Venta documentada: pagados y por cobrar, menos notas de crédito"),
                ("desc", "Descuento", "celda", 118,
                 "Carta − Venta, y su variación"),
                ("pdesc", "% desc.", "celda", 132,
                 "Descuento ÷ carta, y su cambio en pp")]
        if "n_desc" in hay:
            cols += [("n_desc", "Comprob. c/desc.", "celda", 128,
                      "Comprobantes con algún descuento, de todos los del "
                      "período"),
                     ("ptrx", "% comprob.", "celda", 112,
                      "Qué parte de los comprobantes tuvo descuento")]
        out["Descuentos"] = (cols, "Carta − Venta, y en cuántos comprobantes.")
    if "pcort" in hay:
        cols = [("carta", "Carta vendida", "soles0", 112,
                 "Venta a precio de carta (sin cortesías)"),
                ("cort", "Cortesías", "celda", 118,
                 "Cortesías a precio carta, y su variación"),
                ("pcort", "% cortesía", "celda", 132,
                 "Cortesías ÷ carta vendida, y su cambio en pp"),
                ("n_cort", "Comprob.", "entero", 92,
                 "Comprobantes tipo CORTESIA"),
                ("costo_cort", "Costaron", "soles0", S,
                 "Costo de receta de las cortesías")]
        out["Cortesías"] = (cols, "A precio carta; no suman a la venta.")
    if "pcosto" in hay:
        cols = [("neto", "Neto", "soles0", S, "Venta sin IGV ni recargo"),
                ("costo_v", "Costo histórico", "celda", 142,
                 "Costo histórico de lo vendido, incluidos combos y propiedades, y su variación"),
                ("pcosto", "% costo", "celda", _ANCHO_PCOSTO,
                 "Costo ÷ Neto, y su cambio en pp. «revisar»: un plato con "
                 "costo mayor a su precio infla el período")]
        if "psin" in hay:
            cols += [("sin_costo", "Sin costo", "soles0", S,
                      "Venta de platos SIN costo cargado: baja el % de costo"),
                     ("psin", "% venta sin costo", "celda", 132,
                      "Qué parte de la venta no tiene costo cargado")]
        if "sin_que" in hay:
            # Regla #590: lo que hay que corregir en el POS. El costo con que
            # se vende es una foto, así que lo de ese período queda así.
            cols.append(("sin_que", "Qué se vendió sin costo", "texto", 220,
                         "Lo vendido sin costo cargado, de mayor a menor "
                         "venta: lo que hay que corregir en el POS. Con el "
                         "cursor, los montos"))
        cols.append(("revisar", "A revisar", "texto", 180,
                     "El plato con mayor exceso de costo sobre su precio, en "
                     "los períodos marcados «revisar»"))
        out["Costo"] = (cols, "Costo sobre neto; «sin costo» baja el %.")
    if "docs_v" in hay:
        # EL CUADRE (regla #524): de lo que registra el POS a la venta, y
        # lo que queda aparte. La fila Total es el cuadre de la vista.
        cols = [("docs_v", "Facturas y boletas", "celda", 150,
                 "Facturas y boletas pagadas o por cobrar: lo mismo que "
                 "registra el sistema de caja"),
                ("nc_v", "Notas de crédito", "celda", 140,
                 "Notas de crédito emitidas en el período. Restan de la "
                 "venta el día que se emiten, como en el Registro de Ventas"),
                ("valor", "= Venta", "celda", 118,
                 "Facturas y boletas − notas de crédito"),
                ("cort_c", "Cortesías", "celda", 132,
                 "Aparte: a precio carta. No son venta"),
                ("anul", "Anulados", "celda", 132,
                 "Aparte: comprobantes anulados. No son venta")]
        out["Cuadre"] = (cols, "Venta = facturas y boletas − notas de "
                               "crédito; cortesías y anulados, aparte.")
    return out

_ALTO_TABLA_VR = alturas.VENTAS_RESUMEN_TABLA
"""Las grillas de abajo muestran SIETE filas (2026-09-24, a pedido: «las
tablas de abajo que muestran 5 filas, ahora muestren 7»). Era `_ALTO_TABLA`,
el de Compras (191px, cinco filas); ver `alturas.VENTAS_RESUMEN_TABLA`."""

_COSTO_ALTO = 0.45
"""% de costo sobre el neto a partir del cual la celda va en ámbar."""

_COSTO_ROTO = 0.70
"""Y a partir del cual el período sale con «revisar»: por encima de eso no es
un día caro, es un costo mal cargado (medido: el 12/09 llegó al 117 % por
un menú con costo S/ 765,31 y precio S/ 175)."""


def _kpis_extra(g):
    """Las tarjetas de KPI que siguen a los canales: propinas, descuentos,
    cortesías y costo sobre neto. Sólo las que el parquet permite."""
    out = []
    tot = float(g["total"].sum())
    if "pax" in g.columns and float(g["pax"].sum()):
        # El ticket sin la venta de los canales que no registran clientes
        # (regla #591). La tarjeta no crece —la fila ya se corta a la
        # derecha—: el neto y los niños van en su tooltip.
        _x = float(g["pax"].sum())
        _vc = float(g["venta_cli"].sum()) if "venta_cli" in g.columns else tot
        _tip = [f"{_x:,.0f} clientes (adultos)"]
        _n = float(g["ninos"].sum()) if "ninos" in g.columns else 0.0
        if _n:
            _tip[0] += f" + {_n:,.0f} niños"
        _tip.append(f"ticket S/ {_vc / _x:,.2f}")
        if "neto_cli" in g.columns:
            _tip.append(f"ticket neto S/ {float(g['neto_cli'].sum()) / _x:,.2f}")
        if _n:
            _tip.append(f"con niños S/ {_vc / (_x + _n):,.2f}")
        if round(tot - _vc, 2):
            _tip.append(f"sin S/ {tot - _vc:,.2f} de los canales que no "
                        "registran clientes")
        out.append(("Clientes", f"{_x:,.0f}", f"ticket S/ {_vc / _x:,.2f}",
                    "", " · ".join(_tip)))
    if "propina" in g.columns and tot:
        _p = float(g["propina"].sum())
        out.append(("Propinas", fmt_k(_p), f"{_p / tot:.1%}", "",
                    f"Propinas: S/ {_p:,.2f} · {_p / tot:.1%} de la venta"))
    if "desc" in g.columns and "carta" in g.columns and float(g["carta"].sum()):
        _d, _c = float(g["desc"].sum()), float(g["carta"].sum())
        out.append(("Descuentos", fmt_k(_d), f"{_d / _c:.1%}", "",
                    f"Descuentos: S/ {_d:,.2f} · {_d / _c:.1%} de la carta"))
    if "cort_s" in g.columns:
        _k = float(g["cort_s"].sum())
        _n = int(g["n_cort"].sum()) if "n_cort" in g.columns else 0
        out.append(("Cortesías", fmt_k(_k), f"{_n:,} comp.", "",
                    f"Cortesías: S/ {_k:,.2f} a precio carta · {_n:,} "
                    "comprobantes. No suman a la venta"))
    if "nc_v" in g.columns and float(g["nc_v"].sum()):
        # Sólo cuando hay: casi nunca (22 en todo el histórico), y cuando
        # hay es lo primero que pregunta quien cuadra contra el POS.
        _nc = float(g["nc_v"].sum())
        _n = int(g["n_nc"].sum()) if "n_nc" in g.columns else 0
        out.append(("Notas de crédito", "−" + fmt_k(abs(_nc)),
                    f"{_n:,} nota" + ("" if _n == 1 else "s"), "",
                    f"Notas de crédito: S/ {_nc:,.2f}. Restan de la venta el "
                    "día que se emiten, como en el Registro de Ventas"))
    if "anul_s" in g.columns:
        _a = float(g["anul_s"].sum())
        _n = int(g["n_anul"].sum()) if "n_anul" in g.columns else 0
        out.append(("Anulados", fmt_k(_a), f"{_n:,} comp.", "",
                    f"Anulados: S/ {_a:,.2f} · {_n:,} comprobantes. No suman "
                    "a la venta"))
    if "pcosto" in g.columns and float(g["neto"].sum()):
        _pc = float(g["costo"].sum()) / float(g["neto"].sum())
        _rev = int((g["pcosto"] > _COSTO_ROTO).sum())
        out.append(("Costo / neto", f"{_pc:.1%}",
                    f"{_rev} a revisar" if _rev else "",
                    "vt-kpi-alerta" if (_rev or _pc > _COSTO_ALTO) else "",
                    f"Costo de receta ÷ venta neta: {_pc:.1%}"
                    + (f" · {_rev} períodos con un costo mayor al precio"
                       if _rev else "")))
    return out


def _etiqueta_comprobante(tdoc, clase, num):
    """«Boleta B00001000055996», «Nota de crédito …»: el tipo corto y el
    número. El POS escribe «Boleta Electronica», «NC F Electronica»; lo que
    no reconoce va tal cual."""
    t = tdoc.str.lower()
    corto = (tdoc.str.capitalize()
             .mask(t.str.contains("boleta"), "Boleta")
             .mask(t.str.contains("factura"), "Factura")
             .mask(t.str.startswith("nc") | (clase == dv.NOTA_CREDITO),
                   "Nota de crédito"))
    return (corto + " " + num).str.strip()


_RE_NUMERO_SUNAT = re.compile(r"([A-Z])(\d{5})(\d{9})")


def _numero_sunat(num, completo=False):
    """«B00001000056777» → «B001-56777», como lo imprime el comprobante
    (regla #668): la letra, la serie en tres dígitos y el correlativo.
    `completo` lo deja con sus ocho dígitos, «B001-00056777», que es como lo
    escribe SUNAT (lo confirma la respuesta que guarda el POS en
    `MDOCUMENTO.tRespFacturacion`: «F00001000009405» es la F001-00009405).
    Lo que no tiene esa forma —una cortesía, «000001000007948»— va tal
    cual."""
    t = "" if num is None or (isinstance(num, float) and pd.isna(num)) \
        else str(num).strip()
    m = _RE_NUMERO_SUNAT.fullmatch(t)
    if not m:
        return t
    corr = int(m[3])
    return f"{m[1]}{int(m[2]):03d}-" + (f"{corr:08d}" if completo
                                         else str(corr))


def _pedidos_con_horario(peds, k_fila, sel, txt_n):
    """La tabla «Ver por» Pedido con lo que pidió el usuario (regla #668):
    el número del pedido, su horario —de la apertura al último
    comprobante—, el tiempo que estuvo abierto, el tipo (el canal) y el
    documento. Devuelve `(tp, total)` para `renderizar_pedidos_venta`.

    Una nota de crédito no es una mesa: su «cierre» es el día de la nota, y
    su tiempo queda vacío. El total dice la MEDIANA del tiempo: un pedido
    que quedó abierto de un día al otro no mueve la típica. Y sólo de los
    pedidos CON CLIENTES —las mesas—: un Rappi se abre y se cobra en
    minutos, y con ellos el 14/10/2026 la mediana daba 1 h 49 con las
    mesas de la noche en 2-3 h."""
    idx = peds.index
    nc = (peds["clase"] == dv.NOTA_CREDITO) if "clase" in peds \
        else pd.Series(False, index=idx)
    minutos = (peds["cierre"] - peds["inicio"]).dt.total_seconds() / 60
    minutos = minutos.where(~nc & (minutos >= 0)).round(0)
    num = (peds["doc"].astype(str) if "doc" in peds
           else pd.Series("", index=idx))
    tipo = (_texto_limpio(peds["tdoc"]) if "tdoc" in peds
            else pd.Series("", index=idx))
    tp = pd.DataFrame({
        "pedido": peds["pcod"] if "pcod" in peds else peds[k_fila],
        "inicio": peds["inicio"].dt.strftime("%Y-%m-%d %H:%M"),
        "tiempo": minutos,
        "mesero": (peds["mesero"].replace("", "—") if "mesero" in peds
                   else "—"),
        "canal": peds["canal"] if "canal" in peds else "",
        "docn": num.map(_numero_sunat),
        "pax": (peds["pax"].fillna(0).astype(int) if "pax" in peds else 0),
        "valor": peds["valor"].astype(float).round(2),
        "hora": peds["cierre"].dt.strftime("%Y-%m-%d %H:%M"),
        "__doc": (tipo + " " + num.map(
            lambda x: _numero_sunat(x, completo=True))).str.strip(),
        "__ped": peds[k_fila],
        "__sel": peds[k_fila] == sel,
    })
    _mesas = (minutos[peds["pax"].fillna(0) > 0] if "pax" in peds
              else minutos)
    _med = _mesas.median()
    total = {
        "pedido": "Total", "mesero": txt_n,
        "tiempo": float(_med) if pd.notna(_med) else "",
        "pax": f"{int(tp['pax'].sum()):,}",
        "valor": f"S/ {float(peds['valor'].sum()):,.0f}",
    }
    return tp, total


def _grupos_detalle(amb, col, propinas, foco, vacio):
    """Una fila por valor de `col` (mesero, servicio) con sus pedidos,
    clientes, venta, peso, ticket y —por mesero— la propina (regla #667).

    Las cuentas son las del período (`_ventas_resumen`): los clientes con
    `definicion_venta.pax_por` (un canje de boleta por factura cuenta a la
    mesa una vez), el ticket con la venta de los canales que registran
    clientes, la propina una por pago. Sumadas, las filas dan el período."""
    amb = amb.assign(**{col: amb[col].replace("", vacio)})
    ven = amb[amb["clase"] == dv.VENTA] if "clase" in amb.columns else amb
    g = amb.groupby(col)["venta"].sum().rename("venta").to_frame()
    g["pedidos"] = ven.groupby(col)["ped"].nunique()
    if "pax" in amb.columns:
        # Un grupo sin pax (Rappi, «Sin mesero») no sale de `pax_por`: son
        # cero clientes, y su ticket queda «—».
        g["pax"] = dv.pax_por(amb, "ped", "pax",
                              doc="ldoc" if "ldoc" in amb.columns else None,
                              por=col).reindex(g.index).fillna(0.0)
        _base = amb[amb["cli"]] if "cli" in amb.columns else amb
        _vc = _base.groupby(col)["venta"].sum()
        g["ticket"] = _vc.reindex(g.index) / g["pax"].where(g["pax"] > 0)
    else:
        g["pax"] = np.nan
        g["ticket"] = np.nan
    if propinas is not None and col == "mesero":
        _p = propinas[propinas["clave"] == foco]
        g["propina"] = (_p.assign(mesero=_p["mesero"].replace("", vacio))
                        .groupby("mesero")["prop"].sum()
                        .reindex(g.index).fillna(0.0))
    g = g.fillna({"pedidos": 0}).reset_index().rename(columns={col: "nombre"})
    tot = float(g["venta"].sum())
    g["pct"] = g["venta"] / tot if tot else np.nan
    return g.sort_values(["venta", "nombre"], ascending=[False, True])


# ===========================================================================
# LO QUE RECIBE LA PIEZA (regla #714)
# ===========================================================================

_CLASES = (dv.VENTA, dv.NOTA_CREDITO, dv.CORTESIA, dv.ANULADO)
"""La clase de un comprobante como número para la pieza (su posición)."""

_TEXTOS = ("ldoc", "ped", "prod", "grupo", "canal", "serv", "mesero", "tdoc", "num", "pcod")
"""Las columnas de texto de `lineas_normalizadas`."""


def lineas_normalizadas(d, cols):
    """Las ventas con nombres FIJOS, una fila por ítem: lo que la pieza
    cuenta. `cols` son las columnas ya resueltas por `ventas.py`. Las
    opcionales que falten (el demo, un parquet viejo) quedan en cero o
    vacías. Pura."""
    idx = d.index

    def col(*nombres):
        return _resolver(d, list(nombres))

    def num(c):
        return (pd.to_numeric(d[c], errors="coerce").fillna(0.0) if c and c in d.columns
                else pd.Series(0.0, index=idx))

    def txt(c):
        return _texto_limpio(d[c]) if c and c in d.columns else pd.Series("", index=idx)

    fecha = pd.to_datetime(d[cols["fecha"]], errors="coerce")
    c_doc = col("Numero Documento", "Nro Documento")
    c_ldoc = col("Llave Local Documento")
    num_doc = txt(c_doc)
    ldoc = txt(c_ldoc) if c_ldoc else num_doc.where(num_doc != "", pd.Series(idx.astype(str), index=idx))
    ped = txt(cols.get("pedido"))
    c_clase = dv.columna(d, dv.CLASE)
    c_est = dv.columna(d, dv.ESTADO)
    c_em = dv.columna(d, dv.FECHA_EMISION)
    c_ini = col("Fecha Registro Pedido")
    c_ninos = dv.columna(d, dv.NINOS)
    serv = (_texto_limpio(d[cols["serv"]]).str.capitalize() if cols.get("serv") in d.columns
            else pd.Series("", index=idx))
    t = pd.DataFrame({
        "ldoc": ldoc, "ped": ped.where(ped != "", ldoc),
        "prod": txt(cols.get("prod")).where(lambda s: s != "", "—"),
        "grupo": txt(cols.get("fam")),
        "cant": num(cols.get("cant")) if cols.get("cant") else pd.Series(1.0, index=idx),
        "venta": num(cols["venta"]),
        "po": num(col("Precio Oficial Item Ddocumento")),
        "neto": num(col("Neto Total Item Ddocumento")),
        "desc": num(col("Descuento Item Ddocumento")),
        "pc": num(col("Precio Costo")),
        "igv": num(col("Igv Item Ddocumento")),
        "fecha": fecha,
        "emision": pd.to_datetime(d[c_em], errors="coerce") if c_em else fecha,
        "clase": (d[c_clase].astype(object) if c_clase else dv.VENTA),
        "porcobrar": (d[c_est].astype(str).str.strip().str.upper().eq(_POR_COBRAR) if c_est
                      else False),
        "canal": (_canal_legible(d[cols["canal"]]) if cols.get("canal") in d.columns
                  else pd.Series(_SIN_CANAL, index=idx)),
        "serv": serv.where(serv != "", _SIN_SERVICIO),
        "mesero": (_nombre_mesero(d[cols["mesero"]]) if cols.get("mesero") in d.columns
                   else pd.Series("", index=idx)),
        "tdoc": txt(col("Tipo Doc", "Tipo Documento", "Nomb Tipo Doc")),
        "num": num_doc,
        "pax": num(cols.get("pax")), "ninos": num(c_ninos),
        "pcod": txt(col("Codigo Pedido Ddocumento")),
        "inicio": pd.to_datetime(d[c_ini], errors="coerce") if c_ini else pd.NaT,
    })
    return t[t["fecha"].notna()].reset_index(drop=True)


def sello_periodo(t):
    """La identidad de lo que recibe la pieza: cambia con otro rango, otros
    chips de la franja u otro parquet."""
    if t.empty:
        return "0"
    h = pd.util.hash_pandas_object(t[["ldoc", "prod", "venta", "fecha"]], index=False)
    return f"{len(t)}-{int(h.sum()) & 0xFFFFFFFFFFFF:x}"


def _minutos(s, base):
    m = (pd.to_datetime(s, errors="coerce") - base).dt.total_seconds() // 60
    return [None if pd.isna(x) else int(x) for x in m]


def armar_periodo(t, sello, alto_fig, alto_fig_solo, alto_tabla):
    """Lo que recibe la pieza, de las ventas normalizadas
    (`lineas_normalizadas`). Pura: la lee el test.

    · `docs` — un comprobante por fila: [número, tipo, clase (índice de
      `_CLASES`), por cobrar, fecha del turno y de emisión (minutos desde
      `base`), pedido, canal, servicio, mesero, adultos, niños]. El pax de
      una nota de crédito viene en negativo (`definicion_venta.preparar`).
    · `unidades` — lo de cada comprobante por grupo de la carta: [doc,
      grupo, venta, venta a precio carta, neto, descuento, costo, venta sin
      costo cargado, líneas, alguna con descuento]. De acá salen todas las
      cuentas menos la tabla de platos.
    · `lineas` — [doc, plato, grupo, cantidad, venta], de los días desde
      `lineas_desde` (todo el rango si cabe en `_DIAS_LINEAS`).
    · `sinc` — lo vendido sin costo: [doc, plato, grupo, venta]; `culp` —
      lo vendido a un costo mayor que su precio: [doc, plato, grupo, costo
      unitario, precio carta, cantidad]; `igv` — los cambios de tasa
      (`cambios_de_igv`): [día, antes, después].
    · `pagos` — uno por pago: [doc, monto en soles, propina, forma]."""
    # Las columnas de texto como objetos de Python, UNA vez: con pandas 3
    # vienen respaldadas por Arrow y recorrerlas valor por valor convierte
    # cada uno (medido: 19 s para doce meses; así, menos de 1).
    t = t.astype({c: object for c in _TEXTOS})
    base = t["fecha"].min().normalize()
    dia = (t["fecha"].dt.normalize() - base).dt.days

    def dic(serie):
        vals = sorted(pd.unique(serie.to_numpy()))
        return vals, {v: i for i, v in enumerate(vals)}

    prods, ip = dic(t["prod"])
    grupos, ig = dic(t["grupo"])
    canales, ic = dic(t["canal"])
    servs, isv = dic(t["serv"])
    meseros, im = dic(t["mesero"])
    tdocs, it = dic(t["tdoc"])
    clase = t["clase"].map({c: i for i, c in enumerate(_CLASES)}).fillna(0).astype(int)
    docs = t.assign(_cl=clase).drop_duplicates("ldoc").reset_index(drop=True)
    idoc = {k: i for i, k in enumerate(docs["ldoc"])}
    peds, iped = dic(docs["ped"])
    pedidos = docs.drop_duplicates("ped").set_index("ped").reindex(peds)
    d_i = t["ldoc"].map(idoc)

    # Lo de cada comprobante por grupo.
    u = t.assign(_d=d_i, _g=t["grupo"].map(ig), carta=t["po"] * t["cant"],
                 costo=t["pc"] * t["cant"], sin=t["venta"].where(t["pc"] <= 0, 0.0),
                 tdesc=(t["desc"] != 0).astype(int))
    ug = (u.groupby(["_d", "_g"], as_index=False, sort=True)
          .agg(venta=("venta", "sum"), carta=("carta", "sum"), neto=("neto", "sum"),
               desc=("desc", "sum"), costo=("costo", "sum"), sin=("sin", "sum"),
               n=("venta", "size"), tdesc=("tdesc", "max")))
    # Con cuatro decimales: redondeadas a céntimos, 2.000 sumas parciales
    # corrían el total del mes en un par de soles.
    unidades = [[int(a), int(b), round(v, 4), round(c, 4), round(ne, 4), round(de, 4), round(co, 4),
                 round(si, 4), int(n), int(td)]
                for a, b, v, c, ne, de, co, si, n, td in zip(
                    ug["_d"], ug["_g"], ug["venta"], ug["carta"], ug["neto"], ug["desc"],
                    ug["costo"], ug["sin"], ug["n"], ug["tdesc"])]

    # Las líneas: todo el rango si es corto; si no, los últimos días.
    es_venta = t["clase"].isin(dv.CLASES_VENTA)
    dias_rango = int(dia.max()) + 1 if len(t) else 0
    desde = 0 if dias_rango <= _DIAS_LINEAS else max(0, int(dia[es_venta].max()) - _DIAS_RECIENTES + 1)
    ventana = t[(dia >= desde)]
    lineas = lineas_de(ventana, idoc, ip, ig)

    sc = t[es_venta & (t["pc"] <= 0)]
    cu = t[es_venta & (t["po"] > 0) & (t["pc"] > t["po"])]
    cambios = cambios_de_igv(t.loc[es_venta, "fecha"], t.loc[es_venta, "igv"],
                             t.loc[es_venta, "neto"])
    return {
        "parte": "periodo", "sello": sello, "base": f"{base:%Y-%m-%d}",
        "lineas_desde": int(desde), "max_dias": MAX_DIAS,
        "alto": {"fig": int(alto_fig), "fig_solo": int(alto_fig_solo), "tabla": int(alto_tabla)},
        "prods": prods, "grupos": grupos, "canales": canales, "servs": servs,
        "meseros": meseros, "tdocs": tdocs,
        "pedidos": [[p, a] for p, a in zip(pedidos["pcod"], _minutos(pedidos["inicio"], base))],
        "docs": [[n, it[td], int(cl), int(bool(pc)), f, e if e is not None else f, iped[pe],
                  ic[ca], isv[sv], im[me], float(px), float(ni)]
                 for n, td, cl, pc, f, e, pe, ca, sv, me, px, ni in zip(
                     docs["num"], docs["tdoc"], docs["_cl"], docs["porcobrar"],
                     _minutos(docs["fecha"], base), _minutos(docs["emision"], base),
                     docs["ped"], docs["canal"], docs["serv"], docs["mesero"],
                     docs["pax"], docs["ninos"])],
        "unidades": unidades, "lineas": lineas,
        "sinc": [[idoc[a], ip[b], ig[g], round(v, 2)]
                 for a, b, g, v in zip(sc["ldoc"], sc["prod"], sc["grupo"], sc["venta"])],
        "culp": [[idoc[a], ip[b], ig[g], round(p, 4), round(o, 2), round(q, 3)]
                 for a, b, g, p, o, q in zip(cu["ldoc"], cu["prod"], cu["grupo"], cu["pc"],
                                             cu["po"], cu["cant"])],
        "igv": [[int((pd.Timestamp(f) - base).days), round(a, 4), round(b, 4)]
                for f, a, b in cambios],
        "feriados": sorted(f"{x:%Y-%m-%d}" for a in range(base.year, int(t["fecha"].max().year) + 1)
                           for x in cortes.feriados_peru(a)),
    }


def lineas_de(t, idoc, ip, ig):
    """[doc, plato, grupo, cantidad, venta] de las líneas de `t`."""
    return [[idoc[a], ip[b], ig[g], round(q, 3), round(v, 2)]
            for a, b, g, q, v in zip(t["ldoc"].tolist(), t["prod"].tolist(), t["grupo"].tolist(),
                                     t["cant"].tolist(), t["venta"].tolist())]


def pagos_periodo(d_pagos, col_fecha, idoc):
    """[doc, monto en soles, propina, forma] de cada pago, una vez (regla
    #517: el parquet repite cada pago en cada ítem). Y las formas."""
    if d_pagos is None or d_pagos.empty:
        return [], []
    c = lambda *n: _resolver(d_pagos, list(n))  # noqa: E731
    c_pago, c_ldoc = c("Llave Local Documento Correlativo Pago"), c("Llave Local Documento")
    c_monto, c_tipo = c("Monto Tipo Pago Doc"), c("Nombre Tipo Pago")
    if not (c_pago and c_ldoc and c_tipo):
        return [], []
    p = d_pagos[d_pagos[c_pago].notna()].drop_duplicates(c_pago)
    forma = forma_de_pago(p[c_tipo], p[c("Nombre Tarjeta Pago")] if c("Nombre Tarjeta Pago") else None,
                          p[c("Nombre Otro Tipo Pago Doc")] if c("Nombre Otro Tipo Pago Doc") else None)
    formas = sorted(set(forma))
    ifo = {f: i for i, f in enumerate(formas)}
    c_prop = c("Monto Propina", "Propina")
    monto = pd.to_numeric(p[c_monto], errors="coerce").fillna(0.0) if c_monto else 0.0
    prop = (pd.to_numeric(p[c_prop], errors="coerce").fillna(0.0) if c_prop
            else pd.Series(0.0, index=p.index))
    out = [[idoc[str(ld)], round(float(m), 2), round(float(pr), 2), ifo[f]]
           for ld, m, pr, f in zip(_texto_limpio(p[c_ldoc]), monto, prop, forma)
           if str(ld) in idoc]
    return out, formas


# ── La pieza ──────────────────────────────────────────────────────────────
_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "ventas_periodo",
    css=(_AQUI / "ventas_periodo.css").read_text(encoding="utf-8"),
    # El Excel (`libro`, `bajar`, `archivo`) vive en `_xlsx.js`, compartido
    # con Costo de Carta, Consistencia y Producto: se antepone.
    js=(_AQUI / "_xlsx.js").read_text(encoding="utf-8")
    + (_AQUI / "ventas_periodo.js").read_text(encoding="utf-8"),
)
_K_PIEZA = "vt_periodo_pieza"
_K_LINEAS = "vt_periodo_lineas"
_K_CACHE = "_vt_periodo_cache"
"""(sello, ventas normalizadas, índices, lo que recibe la pieza, firma del `d`)
de la última corrida: armarlo para doce meses son ~2 s, y sólo cambia con el
rango, los chips de la franja o el parquet. La firma reconoce el MISMO `d`
cuando el fragment se vuelve a correr con sus argumentos (al pedir líneas)."""
_K_PEDIDO = "_vt_periodo_pedido"


def _al_pedir_lineas():
    """Un período sin sus líneas en la pieza las pide (`lineas`: {desde,
    hasta} en días desde `base`). Se guarda y la corrida del fragment las
    manda en el montaje chico."""
    v = (st.session_state.get(_K_PIEZA) or {}).get("lineas")
    if v:
        st.session_state[_K_PEDIDO] = v


@st.fragment
def _ventas_resumen(d, col_venta, col_fecha, col_pax, col_pedido, col_prod,
                    col_cant, col_fam=None, col_serv=None, col_canal=None,
                    col_mesero=None, d_pagos=None):
    """«Venta por Periodo»: la fecha (Python) y la pieza. Ver el docstring
    del módulo y `arquitectura.md` regla #714.

    La firma es la de antes: en Cloud un commit que le cambia la firma a algo
    ya importado deja el `app.py` nuevo hablando con el paquete viejo (regla
    #357)."""
    # La fecha escribe la clave canónica del rango, que es la que lee
    # `carga_por_rango` en `app.py`: el `d` de acá ya está materializado con
    # el rango VIEJO, así que hay que escalar a una corrida completa.
    if st.session_state.pop("vt_resumen_fecha_flag", False):
        preservar_widgets(_KEYS_WIDGET_RESUMEN)
        st.rerun(scope="app")
    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el resumen ejecutivo.")
        return
    with st.container(border=True, key="ajuste_graf_card_izq_ventas_resumen"):
        with st.container(key="vt_periodo_fecha"):
            selector_fecha_tarjeta("vt_resumen", "vt_resumen_fecha_flag", categoria=None)
        if d is None or d.empty:
            st.info("Sin ventas en el rango cargado.")
            return
        cols = {"venta": col_venta, "fecha": col_fecha, "pax": col_pax, "pedido": col_pedido,
                "prod": col_prod, "cant": col_cant, "fam": col_fam, "serv": col_serv,
                "canal": col_canal, "mesero": col_mesero}
        # El MISMO `d` de la corrida anterior (el fragment se vuelve a correr
        # con sus argumentos, p. ej. al pedir líneas): no se vuelve a
        # normalizar ni a sellar —con doce meses es ~1 s—.
        cache = st.session_state.get(_K_CACHE)
        firma_d = (id(d), d.shape, id(d_pagos))
        if cache is not None and cache[4] == firma_d:
            sello, t = cache[0], cache[1]
        else:
            t = lineas_normalizadas(d, cols)
            if t.empty:
                st.info("Sin ventas en el rango cargado.")
                return
            sello = sello_periodo(t)
        if cache is None or cache[0] != sello:
            from graficos.compras.semanal import _ALTO_FIG_SOLO
            datos = armar_periodo(t, sello, alturas.VENTAS_RESUMEN_FIG, _ALTO_FIG_SOLO,
                                  _ALTO_TABLA_VR)
            idoc = {k: i for i, k in enumerate(t.drop_duplicates("ldoc")["ldoc"])}
            datos["pagos"], datos["formas"] = pagos_periodo(d_pagos, col_fecha, idoc)
            cache = (sello, t, idoc, datos, firma_d)
            st.session_state[_K_CACHE] = cache
            st.session_state.pop(_K_PEDIDO, None)
        elif cache[4] != firma_d:
            cache = (*cache[:4], firma_d)
            st.session_state[_K_CACHE] = cache
        datos = dict(cache[3])
        # Lo que dice la línea de contexto: los filtros de la franja.
        ss = st.session_state
        datos["turno"] = dv.columna(d, dv.FECHA_EMISION) is not None
        datos["franja"] = [[r, list(ss.get(k) or [])] for r, k in (
            ("Grupos", "ventas_graf_filtro_fam"), ("Subgrupos", "ventas_graf_filtro_sub"),
            ("Canales", "ventas_graf_filtro_canal"), ("Servicios", "ventas_graf_filtro_serv"))]
        _PIEZA(key=_K_PIEZA, data=datos, on_lineas_change=_al_pedir_lineas, width="stretch")
        pedido = st.session_state.get(_K_PEDIDO)
        if pedido and pedido.get("sello") == sello:
            _s, t, idoc, datos0, _firma = cache
            base = pd.Timestamp(datos0["base"])
            dia = (t["fecha"].dt.normalize() - base).dt.days
            v = t[(dia >= int(pedido["desde"])) & (dia <= int(pedido["hasta"]))]
            ip = {p: i for i, p in enumerate(datos0["prods"])}
            ig = {g: i for i, g in enumerate(datos0["grupos"])}
            _PIEZA(key=_K_LINEAS, data={"parte": "lineas", "sello": sello,
                                        "desde": int(pedido["desde"]), "hasta": int(pedido["hasta"]),
                                        "lineas": lineas_de(v, idoc, ip, ig)}, width="stretch")
