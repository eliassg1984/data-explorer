"""graficos.movimientos_merma — las tres vistas de MERMA de Movimientos ›
Porcionamientos (2026-10-08, regla #615): «Para revisar», «Rendimiento por
producto» y «Proveedor por kg útil». Aprobadas sobre un mockup con los
datos reales, a partir del «Reporte de Mermas» del Almacén.

EL REPORTE DEL ALMACÉN es `SpReporteMerma`: la cabecera de cada
porcionamiento procesado (`MPORCIONAMIENTO`, estado 02) por su fecha de
registro, agrupada por área › familia › subfamilia › producto, con la merma
valorizada al PRECIO PROMEDIO DE HOY del producto (`vProducto.
nPrecioPromedio`) — no al que tenía el día que se porcionó. Septiembre
2026: 267 porcionamientos, 627,77 de merma, S/ 20.602,20, y la app da lo
mismo (`movimientos_periodo.a_precio_de_hoy`). Al costo del día —el de los
cortes, el mismo con que el kardex descargó el insumo— son S/ 20.413,15.
Las dos se eligen DENTRO de las tarjetas que valorizan —Porcionamientos,
Para revisar y Rendimiento— con `control_valorizacion`, un valor para las
tres (regla #644; hasta el 2026-10-11, en «Filtros»); abre como el Almacén,
a pedido.

LO QUE AGREGAN LAS TRES VISTAS, que el reporte no tiene:

    Para revisar      los porcionamientos del rango que se salen de lo
                      normal para su MISMO producto (la mitad central de
                      sus porcionamientos de los últimos 18 meses), o que
                      traen un error de registro: un corte sin peso (el
                      Almacén cuenta ese peso como merma y lo valora en 0),
                      merma cero en un producto que siempre pierde, un costo
                      lejos de lo pagado, una fecha anterior a su número.
    Rendimiento       un producto en el tiempo: el % de merma de cada
                      porcionamiento sobre su rango normal, y el costo por
                      unidad que entró contra el precio de hoy; al lado, los
                      productos cuya merma cambió en los últimos 90 días.
    Proveedor         el costo por kg ÚTIL —lo pagado ÷ lo que queda después
                      de la merma— de cada proveedor del mismo producto.

EL PROVEEDOR ES UNA ATRIBUCIÓN, no un dato: el Almacén no guarda de qué
lote salió lo porcionado. Es el de la última compra del producto hasta 45
días antes (`con_proveedor`, sobre `compras.parquet`), y el filtro «un solo
proveedor en los 21 días previos» deja los casos sin ambigüedad (el 62 %):
con él el orden de los proveedores no cambió en ninguno de los productos
medidos. Cruzar con el kardex del día no lo afina barato: las compras
entran al almacén central y llegan a Producción por requerimiento, así que
el lote saldría de un FIFO de dos niveles. En esta vista la merma va
SIEMPRE al costo del día: a precio de hoy todos los proveedores costarían
lo mismo.

EL PRECIO DE LOS CORTES Y SU PESO (2026-10-12, regla #647). El Almacén
reparte lo que costó lo que entró entre los cortes según el PESO que les
asigna: todos salen al mismo costo por kg asignado, y la merma no recibe
costo. Así, el precio de un corte = el costo por unidad que entró ÷ (1 −
merma) × el peso asignado a cada unidad del corte. Y la merma no se pesa:
es lo porcionado menos los pesos (en 7.767 de 7.770 porcionamientos). De
ahí salen dos piezas:

    Rendimiento       el precio de cada corte del producto en el tiempo, y
                      su cambio de los últimos 90 días repartido entre esas
                      tres cosas (`precios_de_cortes`, `desglose_precio`).
    Para revisar      la marca «Peso por unidad raro» (`pesos_por_unidad`):
                      un peso mal tipeado cambia la merma y el precio de
                      todos los cortes del porcionamiento, y el corte entra
                      al Almacén a ese precio — el 08/10/2026, 9,80 kg en
                      vez de 0,98 dejaron el «Pulpo cocido 70gr» en S/ 33,10
                      y la Fideua al 54 % de costo.

Las cuentas son puras y las vigila `test_graficos.py::_pruebas_merma`.
"""

import hashlib
import html
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
from cortes import MESES_ABR_ES
from tema import (
    ACENTO, AJUSTE_ALERTA_BORDE, AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO,
    AJUSTE_CRIT_BORDE, AJUSTE_CRIT_FONDO, AJUSTE_CRIT_TEXTO, AJUSTE_NEG,
    AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, GRIS_BORDE, GRIS_FONDO_CABECERA,
    GRIS_LINEA, GRIS_TEXTO, LAVANDA_FILA, LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import _compras_layout, _resolver, eleccion_compartida
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.movimientos_comun import K_RECARGA
from graficos.recetas_comun import ARCHIVO_RECETAVENTA, _activo
from graficos.movimientos_periodo import (
    a_precio_de_hoy, lineas_porcionamientos, unidad_corta,
)

# ── La valorización (`control_valorizacion`, en cada tarjeta) ──────────────
VALOR_HOY = "Precio de hoy"
VALOR_DIA = "Costo del día"
K_VALOR = "mov_porc_valor"

# ── Las tarjetas: el prefijo `ajuste_graf_card_izq_` les da el marco ───────
CARD_REV = "ajuste_graf_card_izq_mov_merma_rev"
CARD_REND = "ajuste_graf_card_izq_mov_merma_rend"
CARD_PROV = "ajuste_graf_card_izq_mov_merma_prov"

# ── Los criterios, medidos sobre los porcionamientos de abr 2025 – sep 2026
DIAS_NORMAL = 540
"""Lo NORMAL de un producto sale de sus porcionamientos de los últimos 18
meses, contados hacia atrás desde el fin del rango."""
N_MIN_NORMAL = 8
"""Con menos porcionamientos que esto, un producto no tiene «normal»."""
MARGEN_MIN = 0.10
"""Fuera de lo normal es más allá de dos veces el rango intercuartil por
encima o por debajo de él, y nunca menos de 10 puntos: con un rango
angosto (el lomo, 8 puntos) un 2 % de más no es una alarma."""
MERMA_TIPICA_MIN = 0.05
"""«Sin merma registrada» sólo se marca en un producto que suele perder al
menos esto: el asado de tira o la pierna se porcionan sin merma siempre."""
COSTO_FUERA = (0.6, 1.6)
"""El costo por unidad del día contra la última compra: fuera de esto, el
porcionamiento se valorizó con un precio que no es el que se pagó."""
DIAS_RECIENTES = 90
DIAS_PROVEEDOR = 45
DIAS_UNICO = 21
MIN_PORC_PROVEEDOR = 5
VENTANAS = {"6 meses": 6, "12 meses": 12, "18 meses": 18}

VENTANA_PESO = 10
"""Lo habitual del peso por unidad de un corte es la mediana de sus últimos
porcionamientos ANTERIORES, del mismo producto inicial, hasta estos..."""
MIN_PESO = 5
"""...y con menos de estos no hay habitual."""
PESO_LEJOS = 2.5
"""Fuera de lo habitual es más de 2,5 veces o menos de 1/2,5 (0,4). Medido
sobre los 12 meses a oct 2026: con la mediana de 18 meses y 2 veces, la
marca salía en 236 líneas, casi todas cambios de COSTUMBRE (un retazo que
se registra con el 30 % de su peso y un día con el 100 %), no errores."""
_GRAMOS = r"(\d{2,4})\s*gr\b"
"""Los gramos que dice el nombre de un corte («Pulpo cocido 70gr»)."""

MARCAS = {
    "alta": ("Merma muy alta", "crit"),
    "sinpeso": ("Corte sin peso", "crit"),
    "peso": ("Peso por unidad raro", "crit"),
    "cero": ("Sin merma registrada", "alerta"),
    "baja": ("Merma muy baja", "alerta"),
    "costo": ("Costo lejos de lo pagado", "info"),
    "fecha": ("Fecha anterior a su número", "info"),
}
"""Las marcas de «Para revisar», en el orden de su gravedad."""
MARCAS_DE_ENTRADA = ("alta", "sinpeso", "peso", "cero", "baja", "costo")
"""«Fecha anterior a su número» abre apagada: el cierre de mes se registra
así en tanda (15 en septiembre 2026) y taparía al resto. «Peso por unidad
raro» abre prendida, a pedido (regla #647)."""

_COLOR_MARCA = {
    "crit": (AJUSTE_CRIT_FONDO, AJUSTE_CRIT_BORDE, AJUSTE_CRIT_TEXTO),
    "alerta": (AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_BORDE, AJUSTE_ALERTA_TEXTO),
    "info": (GRIS_FONDO_CABECERA, GRIS_BORDE, GRIS_TEXTO),
}


# ═══════════════════════════════════════════════════════════════════════════
# LAS CUENTAS (puras)
# ═══════════════════════════════════════════════════════════════════════════
def porcionamientos(d, cols):
    """`(base, cortes)`: una fila por porcionamiento con cantidad (`cant`
    en la unidad del producto inicial), `merma_cant`, `pct` y `costo_dia`;
    y los cortes. El grano es el de `lineas_porcionamientos` (regla #510):
    la cabecera UNA vez. Los de cantidad cero quedan fuera: no tienen %."""
    base, cortes = lineas_porcionamientos(d, **cols)
    base = base[base["cant"] > 0].copy()
    base["pct"] = base["merma_cant"] / base["cant"]
    return base.reset_index(drop=True), cortes


def valorizar(base, modo, precios=None):
    """`base` con `costo` (lo porcionado), `valor` (la merma) y `precio`
    (por unidad que entró) según `modo`: `VALOR_HOY` como el Reporte de
    Mermas del Almacén, `VALOR_DIA` al costo de los cortes. Sin `precios`,
    al costo del día."""
    if modo == VALOR_HOY and precios is not None:
        b = a_precio_de_hoy(base, precios)
    else:
        b = base.copy()
        b["costo"] = b["costo_dia"]
        b["valor"] = b["costo_dia"] * b["pct"]
    b["precio"] = (b["costo"] / b["cant"]).where(b["cant"] > 0).fillna(0.0)
    # Las dos, para quien muestre la que no se eligió.
    b["valor_dia"] = b["costo_dia"] * b["pct"]
    b["valor_hoy"] = (b["merma_cant"] * pd.to_numeric(
        b["cod"].map(precios), errors="coerce").fillna(0.0)
        if precios is not None else np.nan)
    return b


def normales(hist):
    """Por código de producto, cuántos porcionamientos tiene `hist` y el
    rango de su % de merma: `n`, `q1`, `med`, `q3`."""
    g = hist.groupby("cod")["pct"]
    return pd.DataFrame({"n": g.size(), "q1": g.quantile(0.25),
                         "med": g.median(), "q3": g.quantile(0.75)})


def habitual_previo(valores, grupos):
    """Por fila, la mediana de hasta `VENTANA_PESO` valores ANTERIORES de su
    grupo, con `MIN_PESO` o más (NaN si no). `valores` llega ordenado por
    fecha dentro de cada grupo. Pura."""
    antes = valores.groupby(grupos, sort=False).shift()
    return (antes.groupby(grupos, sort=False)
            .rolling(VENTANA_PESO, min_periods=MIN_PESO).median()
            .reset_index(level=0, drop=True))


def gramos_del_nombre(nombres):
    """Los kilos que dice el nombre de un corte («Pulpo cocido 70gr» →
    0,07), o NaN. Pura."""
    return pd.to_numeric(nombres.astype(str).str.extract(
        _GRAMOS, flags=re.IGNORECASE, expand=False), errors="coerce") / 1000


def fuera_de_lo_habitual(kgu, hab, gramos):
    """Si el peso por unidad `kgu` está lejos de lo habitual `hab` y, donde
    el nombre los dice (`gramos`, NaN si no), también de esos gramos — el
    «Collar / Charela 125gr» se registra siempre al doble, y eso es
    costumbre. Pura."""
    def lejos(r):
        return (r > PESO_LEJOS) | (r < 1 / PESO_LEJOS)
    return lejos(kgu / hab) & (gramos.isna() | lejos(kgu / gramos))


def en_kilos(unidades):
    """Si cada unidad es de kilos. Pura."""
    return unidades.astype(str).str.strip().str.upper().isin(
        ("KILOS", "KILO", "KG"))


def pesos_por_unidad(base, cortes):
    """Cada línea de corte con su peso por unidad y lo habitual: `kgu` (el
    peso ÷ la cantidad: lo del producto INICIAL asignado a cada unidad del
    corte), `hab` (`habitual_previo` del mismo corte y el mismo producto
    inicial), `nombre` (los kilos que dice el nombre del corte, si el
    inicial va en kilos) y `raro` (`fuera_de_lo_habitual`). Las líneas sin
    cantidad o sin peso quedan fuera: ésas son «Corte sin peso». `base`
    tiene que traer los porcionamientos de ANTES del rango que se marca.
    Pura."""
    c = cortes.merge(base[["doc", "fecha", "cod", "unid"]]
                     .rename(columns={"unid": "unid_ini"}), on="doc",
                     how="inner")
    c = c[(c["cant"] > 0) & (c["peso"] > 0)].copy()
    c["kgu"] = c["peso"] / c["cant"]
    c["_par"] = c["cod"].astype(str) + "›" + clave_corte(c).astype(str)
    c = c.sort_values(["_par", "fecha", "doc"], kind="stable")
    c["hab"] = habitual_previo(c["kgu"], c["_par"])
    c["nombre"] = gramos_del_nombre(c["fin"]).where(en_kilos(c["unid_ini"]))
    c["raro"] = fuera_de_lo_habitual(c["kgu"], c["hab"], c["nombre"])
    return c.drop(columns="_par")


def marcar(base, norm, cortes, pesos=None):
    """`base` con lo normal de su producto y una columna booleana por marca
    (`m_alta`, `m_baja`, `m_cero`, `m_sinpeso`, `m_peso`, `m_costo`,
    `m_fecha`). La marca de costo necesita `pcompra` (de `con_proveedor`);
    sin ella no se marca. La de peso, `pesos` (de `pesos_por_unidad`), y
    deja `dpeso` —los kg de más (o de menos) que se llevaron los cortes
    raros contra su peso habitual— y `pct_corr`, la merma con el peso
    habitual: si sale imposible (menos de 0 o 100 % o más), lo habitual no
    le sirve a ese porcionamiento y no se marca."""
    b = base.join(norm, on="cod")
    n = b["n"].fillna(0)
    ok = n >= N_MIN_NORMAL
    margen = np.maximum(2 * (b["q3"] - b["q1"]), MARGEN_MIN)
    con_merma = b["merma_cant"] > 0
    b["m_alta"] = ok & con_merma & (b["pct"] > b["q3"] + margen)
    b["m_baja"] = ok & con_merma & (b["pct"] < b["q1"] - margen)
    crudo = ~b["prod"].astype(str).str.startswith("(")
    b["m_cero"] = (ok & (b["merma_cant"] == 0) & crudo
                   & (b["med"] >= MERMA_TIPICA_MIN))
    sin_peso = cortes.loc[(cortes["cant"] > 0)
                          & (cortes["peso"].fillna(0) == 0), "doc"]
    b["m_sinpeso"] = b["doc"].isin(set(sin_peso))
    if "pcompra" in b.columns:
        r = (b["costo_dia"] / b["cant"]) / b["pcompra"]
        b["m_costo"] = (b["pcompra"] > 0) & (b["costo_dia"] > 0) & (
            (r < COSTO_FUERA[0]) | (r > COSTO_FUERA[1]))
    else:
        b["m_costo"] = False
    num = b["doc"].astype(str).str[:4]
    b["m_fecha"] = num.str.isdigit() & (num != b["fecha"].dt.strftime("%y%m"))
    b["m_peso"], b["dpeso"], b["pct_corr"] = False, 0.0, b["pct"]
    if pesos is not None and len(pesos):
        r = pesos[pesos["raro"]]
        dp = (r["peso"] - r["cant"] * r["hab"]).groupby(r["doc"]).sum()
        dpeso = b["doc"].map(dp)
        corr = (b["merma_cant"] + dpeso) / b["cant"]
        b["m_peso"] = dpeso.notna() & (corr >= 0) & (corr < 1)
        b["dpeso"] = dpeso.where(b["m_peso"], 0.0)
        b["pct_corr"] = corr.where(b["m_peso"], b["pct"])
    return b


def impacto(b, marcas):
    """Lo que cuesta, en soles de la valorización de `b`, la marca más cara
    de cada porcionamiento entre las `marcas` pedidas: lo perdido de más (o
    de menos) contra lo normal, la merma que debió registrarse, o la merma
    entera si un corte sin peso la infló. Las de costo y fecha no tienen
    monto (0)."""
    vals = []
    if "alta" in marcas or "baja" in marcas:
        dif = (b["pct"] - b["med"]) * b["cant"] * b["precio"]
        if "alta" in marcas:
            vals.append(dif.where(b["m_alta"], 0.0))
        if "baja" in marcas:
            vals.append(dif.where(b["m_baja"], 0.0))
    if "cero" in marcas:
        vals.append((b["med"] * b["cant"] * b["precio"]).where(b["m_cero"], 0.0))
    if "sinpeso" in marcas:
        vals.append(b["valor"].where(b["m_sinpeso"], 0.0))
    if "peso" in marcas and "m_peso" in b.columns:
        # Como «Merma muy baja»: lo registrado menos lo que daría el peso
        # habitual — negativo si el peso de más escondió merma.
        vals.append((-b["dpeso"] * b["precio"]).where(b["m_peso"], 0.0))
    if not vals:
        return pd.Series(0.0, index=b.index)
    m = pd.concat(vals, axis=1).fillna(0.0)
    pos = m.abs().to_numpy().argmax(axis=1)
    return pd.Series(m.to_numpy()[np.arange(len(m)), pos], index=b.index)


def compras_para_proveedor(c):
    """Las compras como las pide `con_proveedor`: `cod`, `f` (el día),
    `prov`, `pu` (soles por unidad) y `f_otro`, el último día ANTERIOR en
    que se compró ese producto a OTRO proveedor. Sin las columnas, None.

    `f_otro` sale por TRAMOS: ordenadas las compras de un producto por
    fecha, cada racha del mismo proveedor es un tramo, y lo de otro
    proveedor anterior a una compra es el final del tramo de antes."""
    cc = {k: _resolver(c, v) for k, v in {
        "cod": ["COD_PRODUCTO", "Cod producto", "Codigo producto"],
        "f": ["FECHA_EMISION_DOC", "Fecha documento"],
        "prov": ["NOMBRE_PROVEEDOR", "Nombre proveedor"],
        "cant": ["CANTIDAD_COMPRA", "Cantidad compra"],
        "val": ["VALOR_COMPRA", "Valor compra"]}.items()}
    if c is None or not all(cc.values()):
        return None
    t = pd.DataFrame({
        "cod": c[cc["cod"]].fillna("").astype(str).str.strip(),
        "f": pd.to_datetime(c[cc["f"]], errors="coerce").dt.normalize(),
        "prov": c[cc["prov"]].fillna("").astype(str).str.strip(),
        "cant": pd.to_numeric(c[cc["cant"]], errors="coerce"),
        "val": pd.to_numeric(c[cc["val"]], errors="coerce"),
    })
    t = t[(t["cant"] > 0) & (t["cod"] != "") & (t["prov"] != "")
          & t["f"].notna()].copy()
    t["pu"] = t["val"] / t["cant"]
    t["f"] = t["f"].astype("datetime64[ns]")
    t = t.sort_values(["cod", "f", "prov"], kind="stable").reset_index(drop=True)
    nuevo = (t["cod"] != t["cod"].shift()) | (t["prov"] != t["prov"].shift())
    t["tramo"] = nuevo.cumsum()
    tr = t.groupby("tramo").agg(cod=("cod", "first"), fin=("f", "max"))
    tr["otro"] = tr["fin"].shift().where(tr["cod"].eq(tr["cod"].shift()))
    t["f_otro"] = t["tramo"].map(tr["otro"])
    return t[["cod", "f", "prov", "pu", "f_otro"]]


def con_proveedor(base, compras):
    """`base` con el proveedor de la última compra del producto hasta
    `DIAS_PROVEEDOR` días antes (`prov`, `pcompra`, `dias` desde la compra)
    y `unico`: nadie más le vendió ese producto en los `DIAS_UNICO` días
    previos. Conserva el orden de `base`."""
    b = base.copy()
    b["_i"] = np.arange(len(b))
    b["_dia"] = b["fecha"].dt.normalize().astype("datetime64[ns]")
    b["cod"] = b["cod"].astype(str)
    if compras is None or compras.empty:
        b["prov"], b["pcompra"], b["dias"], b["unico"] = None, np.nan, np.nan, False
        return b.drop(columns=["_i", "_dia"])
    c = compras.assign(cod=compras["cod"].astype(str)).sort_values("f")
    m = pd.merge_asof(b.sort_values("_dia"), c, left_on="_dia", right_on="f",
                      by="cod", direction="backward",
                      tolerance=pd.Timedelta(days=DIAS_PROVEEDOR))
    m["dias"] = (m["_dia"] - m["f"]).dt.days
    m["unico"] = m["prov"].notna() & (
        m["f_otro"].isna()
        | (m["f_otro"] <= m["_dia"] - pd.Timedelta(days=DIAS_UNICO)))
    m = m.rename(columns={"pu": "pcompra"}).sort_values("_i")
    return m.drop(columns=["_i", "_dia", "f", "f_otro"]).reset_index(drop=True)


def _agregado(g):
    """Las sumas de un grupo de porcionamientos, por nombre."""
    return g.agg(n=("doc", "size"), cant=("cant", "sum"),
                 merma=("merma_cant", "sum"), costo=("costo", "sum"),
                 costo_dia=("costo_dia", "sum"))


def cambios(b, fin):
    """Por producto, la merma de los últimos `DIAS_RECIENTES` días antes de
    `fin` contra la del resto de `b`, con al menos `MIN_PORC_PROVEEDOR`
    porcionamientos en cada lado: `pct_ant`, `pct_rec`, `dpp` (puntos),
    `dprecio` (variación del costo del día por unidad) e `impacto` —lo que
    cuestan esos puntos sobre lo porcionado hace poco, en la valorización
    de `b`—, ordenados por `impacto` en valor absoluto."""
    rec = b["fecha"] >= fin - pd.Timedelta(days=DIAS_RECIENTES)
    r = _agregado(b[rec].groupby("cod"))
    a = _agregado(b[~rec].groupby("cod"))
    t = r.join(a, lsuffix="_rec", rsuffix="_ant", how="inner")
    t = t[(t["n_rec"] >= MIN_PORC_PROVEEDOR) & (t["n_ant"] >= MIN_PORC_PROVEEDOR)
          & (t["cant_rec"] > 0) & (t["cant_ant"] > 0)].copy()
    t["pct_rec"] = t["merma_rec"] / t["cant_rec"]
    t["pct_ant"] = t["merma_ant"] / t["cant_ant"]
    t["dpp"] = t["pct_rec"] - t["pct_ant"]
    pr, pa = t["costo_dia_rec"] / t["cant_rec"], t["costo_dia_ant"] / t["cant_ant"]
    t["dprecio"] = (pr / pa - 1).where(pa > 0)
    t["impacto"] = t["dpp"] * t["costo_rec"]
    t = t.reindex(t["impacto"].abs().sort_values(ascending=False).index)
    return t[["pct_ant", "pct_rec", "dpp", "dprecio", "impacto"]]


def fin_de_ventana(d_hist, rango=None):
    """El borde de arriba (excluido) de las ventanas de 6/12/18 meses: el
    fin de `rango` o, sin él, las 00:00 del día siguiente al último
    porcionamiento. A las 00:00 y no a la hora del último (regla #655):
    con la hora, «6 meses» al 9/10 14:51 empezaba el 10/04 a las 14:51 y
    dejaba fuera un porcionamiento de esa mañana — y con él, a INVERMAR
    de «Mejor» proveedor de la charela. Pura."""
    if rango:
        return pd.Timestamp(rango[1])
    return (pd.Timestamp(d_hist["_fecha"].max()) + pd.Timedelta(days=1)).normalize()


DIFIERE_PAGADO = 0.05
"""El costo del día de un porcionamiento «difiere» de lo pagado en su compra
asignada si se aleja más que esto: el Almacén costea al promedio de lo que
tiene en stock, y con stock de otras compras no es el precio de ésa."""


def partes_pagado_de_mas(t):
    """De `por_proveedor` (de UN producto), las cuentas de «Pagado de más»,
    las mismas de `resumen_proveedores`: `mejor` y `peor` (entre los de
    `MIN_PORC_PROVEEDOR` porcionamientos o más), `minimo` (el útil del
    mejor), `queda` por proveedor y `de_mas`, lo pagado de más por cada
    uno: (su útil − el del mejor) × lo que quedó de lo suyo. None si no
    hay dos proveedores que comparar. Pura."""
    ok = t[(t["n"] >= MIN_PORC_PROVEEDOR) & (t["cant"] > t["merma"])]
    if len(ok) < 2:
        return None
    queda = ok["cant"] - ok["merma"]
    minimo = float(ok["util"].min())
    de_mas = (ok["util"] - minimo) * queda
    return {"mejor": ok["util"].idxmin(), "peor": ok["util"].idxmax(),
            "minimo": minimo, "queda": queda, "de_mas": de_mas,
            "extra": float(de_mas.sum())}


def rastro_proveedor(x, compras, prov):
    """Los porcionamientos de `x` (de UN producto, con `con_proveedor`) que
    se le asignan a `prov`, del más viejo al más nuevo, con lo que explica
    cada número: `compra` (el día de la compra asignada) y `pcompra` (lo
    que se pagó por unidad), `pkg` (el costo del día por unidad), `difiere`
    (si los dos se alejan más de `DIFIERE_PAGADO`) y, si no es «único»,
    `otro` y `f_otro`: el proveedor que le vendió el producto en los
    `DIAS_UNICO` días previos — la atribución no es segura. Un producto da
    unas decenas de porcionamientos: no hay grupos que recorrer. Pura."""
    r = x[x["prov"] == prov].copy()
    if r.empty:
        return r.assign(compra=pd.NaT, pkg=np.nan, difiere=False, otro=None,
                        f_otro=pd.NaT)
    r["compra"] = ((r["fecha"].dt.normalize()
                    - pd.to_timedelta(r["dias"], unit="D"))
                   .astype("datetime64[ns]"))
    r["pkg"] = (r["costo_dia"] / r["cant"]).where(r["cant"] > 0)
    r["difiere"] = (r["pcompra"] > 0) & (
        (r["pkg"] / r["pcompra"] - 1).abs() > DIFIERE_PAGADO)
    r = r.sort_values("compra", kind="stable")
    cod = str(r["cod"].iloc[0])
    otros = pd.DataFrame(columns=["f_otro", "otro"])
    if compras is not None and len(compras):
        c = compras[(compras["cod"].astype(str) == cod) & (compras["prov"] != prov)]
        otros = (c.sort_values("f")[["f", "prov"]]
                 .rename(columns={"f": "f_otro", "prov": "otro"}))
    otros["f_otro"] = pd.to_datetime(otros["f_otro"]).astype("datetime64[ns]")
    m = pd.merge_asof(r, otros, left_on="compra", right_on="f_otro",
                      direction="backward")
    m["otro"] = m["otro"].where(~m["unico"].astype(bool))
    m["f_otro"] = m["f_otro"].where(~m["unico"].astype(bool))
    return m.sort_values("fecha", kind="stable").reset_index(drop=True)


def por_proveedor(b, solo_unico=False):
    """Por proveedor (de `con_proveedor`), lo porcionado y su merma, al
    COSTO DEL DÍA: `n`, `cant`, `merma`, `costo`, `pct`, `pkg` (pagado por
    unidad), `util` (pagado por unidad que quedó) y `dias` (mediana de
    días entre la compra y el porcionamiento), del más barato por unidad
    útil al más caro."""
    x = b[b["prov"].notna()]
    if solo_unico:
        x = x[x["unico"]]
    x = x[x["costo_dia"] > 0]
    if x.empty:
        return pd.DataFrame(columns=["n", "cant", "merma", "costo", "pct",
                                     "pkg", "util", "dias"])
    g = x.groupby("prov")
    t = pd.DataFrame({"n": g.size(), "cant": g["cant"].sum(),
                      "merma": g["merma_cant"].sum(),
                      "costo": g["costo_dia"].sum(), "dias": g["dias"].median()})
    t["pct"] = t["merma"] / t["cant"]
    t["pkg"] = t["costo"] / t["cant"]
    t["util"] = (t["costo"] / (t["cant"] - t["merma"])).where(
        t["cant"] > t["merma"])
    # Los de pocos porcionamientos, al final: uno solo no dice nada.
    pocos = t["n"] < MIN_PORC_PROVEEDOR
    return t.assign(_p=pocos).sort_values(["_p", "util"]).drop(columns="_p")


def resumen_proveedores(b, solo_unico=False):
    """Por producto con al menos dos proveedores de `MIN_PORC_PROVEEDOR`
    porcionamientos o más: el mejor y el más caro por unidad útil y
    `extra`, lo pagado de más contra el mejor — Σ (útil del proveedor −
    útil del mejor) × lo que quedó de lo suyo. Del mayor al menor."""
    x = b[b["prov"].notna() & (b["costo_dia"] > 0)]
    if solo_unico:
        x = x[x["unico"]]
    if x.empty:
        return pd.DataFrame(columns=["mejor", "util_mejor", "peor",
                                     "util_peor", "extra", "provs"])
    g = x.groupby(["cod", "prov"])
    t = pd.DataFrame({"n": g.size(), "cant": g["cant"].sum(),
                      "merma": g["merma_cant"].sum(),
                      "costo": g["costo_dia"].sum()}).reset_index()
    t = t[(t["n"] >= MIN_PORC_PROVEEDOR) & (t["cant"] > t["merma"])].copy()
    t["queda"] = t["cant"] - t["merma"]
    t["util"] = t["costo"] / t["queda"]
    t["provs"] = t.groupby("cod")["prov"].transform("size")
    t = t[t["provs"] >= 2].copy()
    if t.empty:
        return pd.DataFrame(columns=["mejor", "util_mejor", "peor",
                                     "util_peor", "extra", "provs"])
    t["minimo"] = t.groupby("cod")["util"].transform("min")
    t["de_mas"] = (t["util"] - t["minimo"]) * t["queda"]
    mejor = t.loc[t.groupby("cod")["util"].idxmin()].set_index("cod")
    peor = t.loc[t.groupby("cod")["util"].idxmax()].set_index("cod")
    r = pd.DataFrame({
        "mejor": mejor["prov"], "util_mejor": mejor["util"],
        "peor": peor["prov"], "util_peor": peor["util"],
        "extra": t.groupby("cod")["de_mas"].sum(),
        "provs": t.groupby("cod")["prov"].size()})
    return r.sort_values("extra", ascending=False)


def por_mes(xs):
    """La merma y el costo del día de `xs`, mes a mes, ponderados por lo
    porcionado: `mes` (el día 15), `pct`, `pkg`."""
    if xs.empty:
        return pd.DataFrame(columns=["mes", "pct", "pkg"])
    g = xs.groupby(xs["fecha"].dt.to_period("M"))
    t = pd.DataFrame({"cant": g["cant"].sum(), "merma": g["merma_cant"].sum(),
                      "costo": g["costo_dia"].sum()})
    t["pct"] = t["merma"] / t["cant"]
    t["pkg"] = (t["costo"] / t["cant"]).where(t["costo"] > 0)
    t["mes"] = t.index.to_timestamp() + pd.Timedelta(days=14)
    return t.reset_index(drop=True)[["mes", "pct", "pkg"]]


# ── El precio de los cortes (regla #647) ──────────────────────────────────
FACTORES = ("insumo", "merma", "gramaje", "otros")
"""Lo que arma el precio de un corte, en el orden en que se explica."""


def nombre_corto(nombre):
    """«(P) Lomo trozos saltado 180gr x und (produccion)» → «Lomo trozos
    saltado 180gr»: el nombre de un corte para una celda. Pura."""
    t = re.sub(r"^\((P|Rs|L)\)\s*", "", str(nombre).strip())
    t = re.sub(r"\s*\((produccion|producción|calientes|pasteleria|"
               r"parrillas?|bar)\s*\)", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+x\s+(und|kg|porc)\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+DD\b", "", t)
    return re.sub(r"\s+", " ", t).strip() or str(nombre)


def clave_corte(c):
    """La identidad de un corte en las líneas `c`: su código y, si la
    consulta no lo trae, su nombre. Pura."""
    if "cod_fin" in c.columns:
        return c["cod_fin"].where(c["cod_fin"].astype(str) != "", c["fin"])
    return c["fin"]


def _lado_corte(filas, cab):
    """Un lado de la comparación del precio de un corte (`filas`: sus
    líneas; `cab`: los porcionamientos por `doc`): `n` porcionamientos,
    `P` (Σ valor ÷ Σ cantidad, el precio por unidad del corte) y los tres
    factores de los porcionamientos que lo dieron — `K` (costo del día por
    unidad que entró), `m` (la merma) y `g` (el peso asignado por unidad
    del corte)."""
    docs = pd.unique(filas["doc"])
    c = cab.loc[docs]
    cant, cn = float(filas["cant"].sum()), float(c["cant"].sum())
    return {"n": len(docs),
            "P": float(filas["valor"].sum()) / cant if cant > 0 else np.nan,
            "K": float(c["costo_dia"].sum()) / cn if cn > 0 else np.nan,
            "m": float(c["merma_cant"].sum()) / cn if cn > 0 else np.nan,
            "g": float(filas["peso"].fillna(0).sum()) / cant if cant > 0 else np.nan}


def desglose_precio(a, b):
    """El cambio del precio de un corte de un lado `a` a otro `b` (de
    `_lado_corte`), repartido entre lo que lo arma: `insumo` (K), `merma`
    (1 ÷ (1 − m)), `gramaje` (g) y `otros` — la mezcla de porcionamientos
    de distinto costo, que hace que el promedio no sea justo el producto de
    los promedios. Con el índice de Divisia de media logarítmica (LMDI-I;
    B. W. Ang, «The LMDI approach to decomposition analysis: a practical
    guide», Energy Policy 33, 2005): los cuatro suman EXACTO el cambio, sin
    resto. Dict factor → soles, o None si falta un lado o un factor. Pura."""
    if not (a["n"] and b["n"]):
        return None
    vals = (a["P"], a["K"], a["g"], b["P"], b["K"], b["g"],
            1 - a["m"], 1 - b["m"])
    if not all(np.isfinite(v) and v > 0 for v in vals):
        return None
    ra = a["P"] / (a["K"] / (1 - a["m"]) * a["g"])
    rb = b["P"] / (b["K"] / (1 - b["m"]) * b["g"])
    dl = np.log(b["P"] / a["P"])
    L = a["P"] if abs(dl) < 1e-12 else (b["P"] - a["P"]) / dl
    return {"insumo": L * np.log(b["K"] / a["K"]),
            "merma": L * np.log((1 - a["m"]) / (1 - b["m"])),
            "gramaje": L * np.log(b["g"] / a["g"]),
            "otros": L * np.log(rb / ra)}


def precios_de_cortes(xs, cortes, fin):
    """Los cortes de los porcionamientos `xs` (de UN producto), del de más
    valor al de menos: `clave`, `nombre`, `unid`, `valor`, el lado de antes
    y el de los últimos `DIAS_RECIENTES` días (`a`, `b`: de `_lado_corte`),
    `var` (cuánto cambió el precio), `desglose` (de `desglose_precio`) y
    `causa`, el factor que más pesó. Un producto da unos pocos cortes (13
    el lomo fino): no son los miles de grupos de la regla #537. Pura."""
    columnas = ["clave", "nombre", "unid", "valor", "a", "b", "var",
                "desglose", "causa"]
    cab = xs.set_index("doc")[["fecha", "cant", "merma_cant", "costo_dia"]]
    c = cortes[cortes["doc"].isin(cab.index) & (cortes["cant"] > 0)].copy()
    if c.empty:
        return pd.DataFrame(columns=columnas)
    c["clave"] = clave_corte(c)
    c["rec"] = (c["doc"].map(cab["fecha"])
                >= fin - pd.Timedelta(days=DIAS_RECIENTES))
    filas = []
    for clave, g in c.groupby("clave", sort=False):
        a, b = _lado_corte(g[~g["rec"]], cab), _lado_corte(g[g["rec"]], cab)
        des = desglose_precio(a, b)
        filas.append({
            "clave": clave, "nombre": g["fin"].iloc[-1],
            "unid": g["unid"].iloc[-1], "valor": float(g["valor"].sum()),
            "a": a, "b": b,
            "var": (b["P"] / a["P"] - 1) if a["n"] and b["n"] and a["P"] > 0
            else np.nan,
            "desglose": des,
            "causa": max(des, key=lambda k: abs(des[k])) if des else None})
    return (pd.DataFrame(filas, columns=columnas)
            .sort_values("valor", ascending=False, kind="stable")
            .reset_index(drop=True))


def precio_corte_por_mes(xs, filas, med=None):
    """El precio de un corte mes a mes (`filas`: sus líneas, de los
    porcionamientos `xs`): `mes` (el día 15), `precio` (Σ valor ÷ Σ
    cantidad), `merma` (la de los porcionamientos que lo dieron) y
    `normal`: el precio con la merma `med` —la mediana del producto—,
    precio × (1 − merma) ÷ (1 − med). Pura."""
    if filas.empty:
        return pd.DataFrame(columns=["mes", "precio", "merma", "normal"])
    cab = xs.set_index("doc")
    f = filas.assign(mes=filas["doc"].map(cab["fecha"]).dt.to_period("M"))
    g = f.groupby("mes")
    t = pd.DataFrame({"valor": g["valor"].sum(), "cant": g["cant"].sum()})
    d = f.drop_duplicates(["mes", "doc"])
    d = d.assign(ci=d["doc"].map(cab["cant"]), mi=d["doc"].map(cab["merma_cant"]))
    gd = d.groupby("mes")
    t["merma"] = gd["mi"].sum() / gd["ci"].sum()
    t["precio"] = (t["valor"] / t["cant"]).where(t["cant"] > 0)
    con_med = med is not None and np.isfinite(med) and med < 1
    t["normal"] = (t["precio"] * (1 - t["merma"]) / (1 - med)) if con_med else np.nan
    t["mes"] = t.index.to_timestamp() + pd.Timedelta(days=14)
    return t.reset_index(drop=True)[["mes", "precio", "merma", "normal"]]


# ── Lo que arrastra un corte con el peso fuera de lo habitual ─────────────
def precio_con_peso_habitual(f, linea):
    """El precio por unidad que habría tenido el corte `linea` del
    porcionamiento `f` (de `marcar`) con su peso habitual: lo que costó ÷
    lo que habría quedado (con la merma corregida) × el peso habitual. Pura."""
    queda = f["cant"] - f["merma_cant"] - f["dpeso"]
    hab = linea.get("hab", np.nan)
    if not (queda > 0 and np.isfinite(hab)):
        return np.nan
    return float(f["costo_dia"] / queda * hab)


def platos_con_insumo(rv, cod, factor):
    """Los platos ACTIVOS de `recetaventa` que llevan el insumo `cod`, del
    de más costo al de menos: `plato`, `costo` y `pct` (los del sistema:
    CST SALON y %CST SALON, que se calcula sobre el precio NETO), y
    `costo_corr` / `pct_corr` con ese insumo a `factor` veces su precio de
    hoy — sus líneas (TOTAL) son precio promedio × cantidad. Pura."""
    vacio = pd.DataFrame(columns=["plato", "costo", "pct", "costo_corr",
                                  "pct_corr"])
    if rv is None or rv.empty:
        return vacio
    c = {k: _resolver(rv, v) for k, v in {
        "plato": ["COD PLATO"], "nombre": ["NOMB PLATO"],
        "activo": ["ITEM VENTA ACTIVO"], "ins": ["COD INS"],
        "total": ["TOTAL"], "cst": ["CST SALON"],
        "pct": ["%CST SALON"]}.items()}
    if not all(c.values()):
        return vacio
    x = rv[(rv[c["ins"]].astype(str).str.strip() == str(cod).strip())
           & _activo(rv[c["activo"]])]
    if x.empty:
        return vacio
    x = x.assign(_p=x[c["plato"]].astype(str).str.strip(),
                 _t=pd.to_numeric(x[c["total"]], errors="coerce"),
                 _c=pd.to_numeric(x[c["cst"]], errors="coerce"),
                 _x=pd.to_numeric(x[c["pct"]], errors="coerce"))
    g = x.groupby("_p", sort=False)
    t = pd.DataFrame({"plato": g[c["nombre"]].first().astype(str).str.strip(),
                      "costo": g["_c"].first(), "pct": g["_x"].first(),
                      "linea": g["_t"].sum()})
    t["costo_corr"] = t["costo"] - t["linea"] * (1 - factor)
    t["pct_corr"] = (t["costo_corr"] * t["pct"] / t["costo"]).where(t["costo"] > 0)
    return (t.sort_values("costo", ascending=False, kind="stable")
            .reset_index(drop=True)[list(vacio.columns)])


# ═══════════════════════════════════════════════════════════════════════════
# LO QUE LEEN DE AFUERA
# ═══════════════════════════════════════════════════════════════════════════
def control_valorizacion(prefijo):
    """«Valorizar la merma» DENTRO de una tarjeta (regla #644): «Precio de
    hoy» —la merma × el precio promedio actual del producto, como el
    «Reporte de Mermas» del Almacén, que reimpreso otro día da otro monto— o
    «Costo del día» —lo que costaba el día que se porcionó, el precio con
    que el kardex lo descargó—. Un valor para las tres tarjetas que lo
    muestran (Porcionamientos, Para revisar y Rendimiento): elegido en una,
    sale elegido en las otras. `prefijo` es el de la key del widget, uno
    por tarjeta. Abre como el Almacén, a pedido. Devuelve el vigente."""
    return eleccion_compartida(K_VALOR, "Valorizar la merma",
                               (VALOR_HOY, VALOR_DIA), VALOR_HOY,
                               f"{prefijo}_valor", recarga=K_RECARGA)


def valorizacion():
    """La valorización elegida (`VALOR_HOY` por defecto)."""
    v = st.session_state.get(K_VALOR)
    return v if v in (VALOR_HOY, VALOR_DIA) else VALOR_HOY


def precios_hoy():
    """Código → precio promedio de hoy, del maestro que trae el inventario
    valorizado: es el `vProducto.nPrecioPromedio` del Almacén, uno por
    producto (comparado contra el SP en los 267 porcionamientos de sep
    2026: igual en todos). None si no se puede leer."""
    inv = data.cargar(data.REPORTES["Inventario Valorizado"]["archivo"])
    if inv is None or inv.empty:
        return None
    c_cod = _resolver(inv, ["CODIGO PRODUCTO", "Codigo Producto"])
    c_p = _resolver(inv, ["PRECIO PROMEDIO", "Precio Promedio"])
    if not (c_cod and c_p):
        return None
    t = pd.DataFrame({"cod": inv[c_cod].astype(str).str.strip(),
                      "p": pd.to_numeric(inv[c_p], errors="coerce")})
    return t.dropna().drop_duplicates("cod").set_index("cod")["p"]


def unidades_kardex():
    """Código → unidad del KARDEX («KILOS», «UND», «LITROS»), del mismo
    maestro que `precios_hoy`. None si no se puede leer.

    Es la unidad en que vienen las cantidades de `salidas.parquet`, que no
    la trae: medido el 2026-10-10 sobre los 342 productos con salidas desde
    junio, valor ÷ cantidad da el precio promedio del maestro (mediana
    1,00), y todos los códigos están en el maestro con UNA sola unidad
    (regla #626)."""
    inv = data.cargar(data.REPORTES["Inventario Valorizado"]["archivo"])
    if inv is None or inv.empty:
        return None
    c_cod = _resolver(inv, ["CODIGO PRODUCTO", "Codigo Producto"])
    c_u = _resolver(inv, ["UNIDAD KARDEX", "Unidad Kardex"])
    if not (c_cod and c_u):
        return None
    t = pd.DataFrame({"cod": inv[c_cod].astype(str).str.strip(),
                      "u": inv[c_u].fillna("").astype(str).str.strip()})
    t = t[t["u"] != ""]
    return t.drop_duplicates("cod").set_index("cod")["u"]


def _compras():
    try:
        return compras_para_proveedor(data.cargar("compras.parquet"))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# PIEZAS DE DIBUJO
# ═══════════════════════════════════════════════════════════════════════════
def _s(v, dec=0):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{'−' if v < 0 else ''}S/ {abs(v):,.{dec}f}"


def _p(v, dec=1):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v * 100:.{dec}f}%"


def _pp(v):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{'+' if v >= 0 else '−'}{abs(v) * 100:.1f} pp"


def _c(v):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v:,.3f}".rstrip("0").rstrip(".")


def _rot_valor(modo):
    return "a precio de hoy" if modo == VALOR_HOY else "al costo del día"


def _titulo(texto, sub="", fecha=None):
    """El título de una tarjeta. Con `fecha` (el que dibuja el botón de
    fecha de la sección, regla #617), comparten renglón."""
    st.markdown(CSS_TITULOS_DRILL, unsafe_allow_html=True)
    tit = (f'<div class="inv-rank-tit">{html.escape(texto)}'
           + (f'<span class="inv-rank-tit-n">{html.escape(sub)}</span>'
              if sub else "") + "</div>")
    if fecha is not None:
        fecha(tit)
    else:
        st.markdown(tit, unsafe_allow_html=True)


def _tiles(items):
    """Una fila de recuadros `(rótulo, valor, debajo)`; `debajo` puede
    traer HTML (ya escapado)."""
    celdas = "".join(
        f'<div style="flex:1 1 140px;min-width:0;background:{LAVANDA_FILA};'
        f'border:1px solid {GRIS_LINEA};border-radius:8px;padding:6px 10px">'
        f'<div style="font-size:11px;color:{GRIS_TEXTO}">{html.escape(r)}</div>'
        f'<div style="font-size:17px;font-weight:700;color:{TEXTO_PRINCIPAL}">'
        f'{html.escape(v)}</div>'
        f'<div style="font-size:11px;color:{GRIS_TEXTO}">{d}</div></div>'
        for r, v, d in items)
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:8px;'
                f'margin-bottom:4px">{celdas}</div>', unsafe_allow_html=True)


def _color_signo(v, subir_es_malo=True):
    if v is None or not np.isfinite(v) or abs(v) < 1e-9:
        return GRIS_TEXTO
    return AJUSTE_NEG_TEXTO if (v > 0) == subir_es_malo else AJUSTE_POS_TEXTO


def _aviso(clave, texto):
    fondo, borde, color = _COLOR_MARCA[MARCAS[clave][1]]
    st.markdown(
        f'<div style="background:{fondo};border:1px solid {borde};color:{color};'
        f'border-radius:8px;padding:6px 10px;font-size:13px;margin:2px 0">'
        f'<b>{html.escape(MARCAS[clave][0])}.</b> {html.escape(texto)}</div>',
        unsafe_allow_html=True)


def _key_tabla(base, codigos):
    firma = hashlib.md5("|".join(map(str, codigos)).encode("utf-8")).hexdigest()[:12]
    return f"{base}_{firma}"


def _fila_elegida(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _foco_anterior(base, k_foco):
    """Lo que la tabla `base` tenía elegido en la corrida anterior, a
    `k_foco`. Se lee ANTES de dibujar: la selección es de la KEY y la key
    cambia con las filas (el criterio de la Carta costeada, regla #556)."""
    ss = st.session_state
    key, codigos = ss.get(f"_{base}_key"), ss.get(f"_{base}_codigos") or []
    fila = _fila_elegida(ss.get(key)) if key else None
    if fila is not None and 0 <= fila < len(codigos):
        ss[k_foco] = codigos[fila]


def _tabla_elegible(base, sty, codigos, pos, alto, cfg, requerida=True):
    ss = st.session_state
    key = _key_tabla(base, codigos)
    ss[f"_{base}_key"], ss[f"_{base}_codigos"] = key, list(codigos)
    kw = dict(key=key, on_select="rerun", hide_index=True, row_height=27,
              height=alto, column_config=cfg)
    if requerida:
        kw.update(selection_mode="single-row-required",
                  selection_default={"selection": {"rows": [pos]}})
    else:
        kw.update(selection_mode="single-row")
    st.dataframe(sty, **kw)


def _resaltar(pos):
    return lambda r: ([f"background-color: {LAVANDA_FONDO}"] * len(r)
                      if r.name == pos else [""] * len(r))


def _alto_tabla(n, tope):
    return min(tope, alturas.por_filas(n, px_fila=27, extra=38, minimo=0))


def _ventana(key, fin):
    """El selector «6/12/18 meses» de una tarjeta y `(ini, fin)`: la
    ventana termina en `fin`. Es la fecha PROPIA de «Rendimiento» y de
    «Proveedor»: desde el 2026-10-08 (regla #617) `fin` es el último día con
    datos, porque la franja de Movimientos ya no tiene calendario."""
    v = st.segmented_control("Ventana", list(VENTANAS), default="12 meses",
                             required=True, key=key,
                             label_visibility="collapsed")
    meses = VENTANAS.get(v, 12)
    return fin - pd.DateOffset(months=meses), fin


def _ticks_meses(ini, fin):
    paso = 1 if (fin - ini).days <= 200 else 2
    vals, rots = [], []
    m = pd.Timestamp(ini.year, ini.month, 1)
    while m < fin:
        if m >= ini:
            vals.append(m)
            rots.append(f"{MESES_ABR_ES[m.month - 1]} {m.year % 100:02d}")
        m = m + pd.DateOffset(months=paso)
    return vals, rots


# ═══════════════════════════════════════════════════════════════════════════
# 1. PARA REVISAR
# ═══════════════════════════════════════════════════════════════════════════
def _motivo(f, clave, u, lineas=None):
    if clave in ("alta", "baja"):
        return (f"Perdió {_p(f['pct'])}; lo normal para este producto es "
                f"entre {_p(f['q1'])} y {_p(f['q3'])} (mediana {_p(f['med'])}).")
    if clave == "cero":
        return (f"No registró merma y este producto suele perder "
                f"{_p(f['med'])}: unos {_c(f['med'] * f['cant'])} {u} que no "
                "aparecen.")
    if clave == "sinpeso":
        return ("Un corte se registró con cantidad pero sin peso. El Almacén "
                "cuenta ese peso como merma y lo valora en S/ 0: la merma "
                "sale inflada y el corte entra sin costo.")
    if clave == "costo":
        return (f"Se valorizó a {_s(f['costo_dia'] / f['cant'], 2)} por {u} y "
                f"la última compra fue a {_s(f['pcompra'], 2)}.")
    if clave == "fecha":
        num = str(f["doc"])
        return (f"Su número es de {MESES_ABR_ES[int(num[2:4]) - 1]} "
                f"20{num[:2]} y se registró el {f['fecha']:%d/%m/%Y}: el "
                "reporte lo cuenta en el mes del registro y el kardex, por "
                "su fecha de proceso, puede llevarlo a otro.")
    if clave == "peso" and lineas is not None and len(lineas):
        partes = [
            f"«{nombre_corto(r['fin'])}»: {_c(r['cant'])} "
            f"{unidad_corta(r['unid'])} con {_c(r['peso'])} {u}, "
            f"{_c(r['kgu'])} {u} por {unidad_corta(r['unid'])}; lo habitual "
            f"es {_c(r['hab'])}" for _, r in lineas.iterrows()]
        normal = (f" (lo normal: {_p(f['q1'], 0)}–{_p(f['q3'], 0)})"
                  if np.isfinite(f.get("q1", np.nan)) else "")
        return (". ".join(partes) + ". La merma es lo porcionado menos los "
                f"pesos: con el peso habitual sería {_p(f['pct_corr'])}"
                f"{normal}, no {_p(f['pct'])}.")
    return ""


def _recetas_venta():
    try:
        return data.cargar(ARCHIVO_RECETAVENTA)
    except Exception:
        return None


def _arrastre(f, lineas, precios):
    """Lo que dejan en el Almacén y en la carta los cortes con el peso fuera
    de lo habitual: si el precio promedio de HOY de un corte es el de este
    porcionamiento (a 2 %) y con el peso habitual habría salido a otro
    precio (más de 10 % de diferencia), el corte quedó caro —o barato— en
    el Almacén, y con él los platos que lo llevan. Texto, o ""."""
    if precios is None or lineas is None or not len(lineas):
        return ""
    textos = []
    for _, r in lineas.iterrows():
        cod = str(r.get("cod_fin", "") or "")
        p_hoy = float(precios.get(cod, np.nan)) if cod else np.nan
        p_dia = float(r["pprom"]) if pd.notna(r["pprom"]) else np.nan
        p_corr = precio_con_peso_habitual(f, r)
        if not all(np.isfinite(v) and v > 0 for v in (p_hoy, p_dia, p_corr)):
            continue
        if abs(p_hoy - p_dia) > 0.02 * p_dia or abs(p_dia - p_corr) < 0.1 * p_corr:
            continue
        uc = unidad_corta(r["unid"])
        quien = ("Entró" if len(lineas) == 1
                 else f"«{nombre_corto(r['fin'])}» entró")
        t = (f"{quien} a {_s(p_dia, 2)} por {uc} —con el peso habitual, "
             f"{_s(p_corr, 2)}— y ése es hoy su precio en el Almacén.")
        platos = platos_con_insumo(_recetas_venta(), cod, p_corr / p_hoy)
        if len(platos):
            t += " En la carta: " + "; ".join(
                f"{r_['plato']}, {_s(r_['costo'], 2)} de costo "
                f"({_p(r_['pct'])}) en vez de {_s(r_['costo_corr'], 2)} "
                f"({_p(r_['pct_corr'])})"
                for _, r_ in platos.head(3).iterrows())
            t += (f" y {len(platos) - 3} plato{'s' if len(platos) > 4 else ''} "
                  "más." if len(platos) > 3 else ".")
        else:
            t += " Ningún plato de la carta lo lleva directo."
        textos.append(t)
    return " ".join(textos)


def tarjeta_revisar(d_rango, d_hist, cols, rango, fecha=None):
    """La sección «Para revisar». `d_rango` son las filas del parquet en el
    rango de la sección; `d_hist`, las de todo el parquet (con el chip
    «Sub Almacén» aplicado a las dos), de donde sale lo normal. `fecha`
    dibuja el botón de fecha de la sección junto al título (regla #617)."""
    with st.container(border=True, key=CARD_REV):
        modo = valorizacion()
        base, cortes = porcionamientos(d_rango, cols)
        if base.empty:
            _titulo("Porcionamientos para revisar", fecha=fecha)
            st.info("Sin porcionamientos en estas fechas.")
            return
        fin = rango[1] if rango else base["fecha"].max() + pd.Timedelta(days=1)
        hist, cortes_h = porcionamientos(
            d_hist[(d_hist["_fecha"] < fin)
                   & (d_hist["_fecha"] >= fin - pd.Timedelta(days=DIAS_NORMAL))],
            cols)
        # El peso habitual de cada corte sale de sus porcionamientos de
        # ANTES, que están en `hist` (regla #647).
        pesos = pesos_por_unidad(hist, cortes_h)
        precios = precios_hoy()
        b = con_proveedor(base, _compras())
        b = marcar(valorizar(b, modo, precios), normales(hist), cortes, pesos)
        cuenta = {k: int(b[f"m_{k}"].sum()) for k in MARCAS}
        _titulo("Porcionamientos para revisar",
                f"{len(b):,} en el rango · lo normal: sus últimos 18 meses",
                fecha=fecha)
        elegidas = st.pills(
            "Qué mostrar", list(MARCAS), selection_mode="multi",
            default=list(MARCAS_DE_ENTRADA), key="mov_merma_rev_marcas",
            format_func=lambda k: f"{MARCAS[k][0]} · {cuenta[k]}",
            label_visibility="collapsed") or []
        hay = np.zeros(len(b), dtype=bool)
        for k in elegidas:
            hay |= b[f"m_{k}"].to_numpy()
        x = b[hay].copy()
        if x.empty:
            st.info("Nada que revisar con estas marcas en el rango.")
            return
        x["impacto"] = impacto(x, elegidas)
        x = x.reindex(x["impacto"].abs().sort_values(ascending=False,
                                                     kind="stable").index)
        x = x.reset_index(drop=True)
        docs = x["doc"].astype(str).tolist()
        k_foco = K_FOCO_REV
        _foco_anterior("mov_merma_rev_tabla", k_foco)
        foco = st.session_state.get(k_foco)
        pos = docs.index(foco) if foco in docs else 0

        tabla = pd.DataFrame({
            "Porcionamiento": "PO-" + x["doc"].astype(str),
            "Fecha": x["fecha"].dt.strftime("%d/%m"),
            "Producto": x["prod"],
            "Merma": x["pct"],
            "Lo normal": [f"{_p(a, 0)}–{_p(c, 0)}" if np.isfinite(a) else "—"
                          for a, c in zip(x["q1"].fillna(np.nan),
                                          x["q3"].fillna(np.nan))],
            "Impacto": x["impacto"],
            "Motivo": [" · ".join(MARCAS[k][0] for k in MARCAS
                                  if k in elegidas and r[f"m_{k}"])
                       for _, r in x.iterrows()],
            "Usuario": x["tipo"],
        })
        sty = (tabla.style.format({"Merma": lambda v: _p(v),
                                   "Impacto": lambda v: _s(v) if v else "—"})
               .apply(_resaltar(pos), axis=1))
        # columnas-internas: la lista y la ficha del elegido, en la misma
        # tarjeta; la ficha necesita lugar para sus cortes.
        c_lista, c_ficha = st.columns([1.5, 1], gap="medium")
        with c_lista:
            _tabla_elegible(
                "mov_merma_rev_tabla", sty, docs, pos,
                _alto_tabla(len(tabla), alturas.MERMA_TABLA),
                {"Producto": st.column_config.TextColumn(width="medium"),
                 "Impacto": st.column_config.Column(
                     help=f"Lo que cuesta, {_rot_valor(modo)}: la merma de "
                          "más (o de menos) contra la mediana del producto, "
                          "la que debió registrarse, la que escondió (o "
                          "infló) un peso fuera de lo habitual, o la merma "
                          "entera si un corte sin peso la infló."),
                 "Lo normal": st.column_config.Column(
                     help="La mitad central de los porcionamientos del "
                          "producto en los últimos 18 meses.")})
            # La valorización, en el renglón que antes decía dónde
            # cambiarla —«(se cambia en «Filtros»)»—: la tarjeta no crece
            # (regla #644).
            with st.container(key="mov_merma_rev_pie", horizontal=True,
                              vertical_alignment="center", gap="small"):
                control_valorizacion("mov_merma_rev_ctl")
                st.caption("Clic en una fila para ver sus cortes.")
        with c_ficha:
            _ficha(x.iloc[pos], cortes, modo, pesos, precios)


def _ficha(f, cortes, modo, pesos=None, precios=None):
    u = unidad_corta(f["unid"])
    st.markdown(
        f'<div style="font-weight:700;font-size:14px">PO-{html.escape(str(f["doc"]))}'
        f' · {html.escape(str(f["prod"]))}</div>'
        f'<div style="font-size:12px;color:{GRIS_TEXTO}">'
        f'{f["fecha"]:%d/%m/%Y %H:%M} · {html.escape(str(f["area"]))} · '
        f'{html.escape(str(f["tipo"]))}'
        + (f' · última compra a {html.escape(str(f["prov"]))}, '
           f'{int(f["dias"])} día{"" if int(f["dias"]) == 1 else "s"} antes'
           if isinstance(f.get("prov"), str) and np.isfinite(f["dias"]) else "")
        + "</div>", unsafe_allow_html=True)
    otro = (f"al costo del día: {_s(f['valor_dia'], 2)}" if modo == VALOR_HOY
            else f"a precio de hoy: {_s(f['valor_hoy'], 2)}")
    _tiles([("Entró", f"{_c(f['cant'])} {u}", ""),
            ("Merma", f"{_c(f['merma_cant'])} {u}", _p(f["pct"])),
            ("Valor de la merma", _s(f["valor"], 2), otro)])
    cs = cortes[cortes["doc"].astype(str) == str(f["doc"])]
    if pesos is not None and len(cs):
        cs = cs.merge(pesos[["doc", "fin", "cant", "peso", "kgu", "hab",
                             "raro"]].drop_duplicates(
                                 ["doc", "fin", "cant", "peso"]),
                      on=["doc", "fin", "cant", "peso"], how="left")
        cs["raro"] = cs["raro"].fillna(False).astype(bool) & bool(f["m_peso"])
    else:
        cs = cs.assign(kgu=np.nan, hab=np.nan, raro=False)
    for k in MARCAS:
        if f[f"m_{k}"]:
            texto = _motivo(f, k, u, cs[cs["raro"]])
            if k == "peso":
                texto = (texto + " " + _arrastre(f, cs[cs["raro"]],
                                                 precios)).strip()
            _aviso(k, texto)
    if cs.empty:
        st.caption("Sin cortes registrados.")
        return
    inf = float("inf")
    kgu = (cs["peso"] / cs["cant"]).where(cs["cant"] > 0)
    t = pd.DataFrame({
        "Corte": [nombre_corto(n) for n in cs["fin"]],
        "Cantidad": [f"{_c(c)} {unidad_corta(un)}"
                     for c, un in zip(cs["cant"], cs["unid"])],
        f"Peso ({u})": cs["peso"].fillna(0).tolist(),
        "Por u.": kgu.fillna(inf).tolist(),
        "Habitual": cs["hab"].fillna(inf).tolist(),
        "S/ prom.": cs["pprom"].fillna(0).tolist(),
    })
    marcadas = (((cs["cant"] > 0) & (cs["peso"].fillna(0) == 0))
                | cs["raro"]).tolist()
    _f = (lambda v: _c(v) if np.isfinite(v) else "—")
    sty = (t.style.format({f"Peso ({u})": _c, "Por u.": _f, "Habitual": _f,
                           "S/ prom.": "{:,.2f}"})
           .apply(lambda r: ([f"color: {AJUSTE_NEG_TEXTO}; font-weight: 600"]
                             * len(r) if marcadas[r.name] else [""] * len(r)),
                  axis=1))
    st.dataframe(sty, hide_index=True, row_height=27,
                 height=_alto_tabla(len(t), alturas.MERMA_CORTES),
                 # Suman el ancho de la ficha a 1323px (~447): con «medium»
                 # en el corte, «Habitual» y «S/ prom.» quedaban afuera.
                 column_config={
                     "Corte": st.column_config.TextColumn(width=128),
                     "Cantidad": st.column_config.TextColumn(width=68),
                     f"Peso ({u})": st.column_config.Column(width=60),
                     "Por u.": st.column_config.Column(
                         width=54,
                         help=f"Los {u} del producto inicial asignados a cada "
                              "unidad del corte (su peso ÷ su cantidad)."),
                     "Habitual": st.column_config.Column(
                         width=62,
                         help="La mediana de sus últimos 10 porcionamientos "
                              "anteriores, del mismo producto inicial."),
                     "S/ prom.": st.column_config.Column(width=62)})


# ═══════════════════════════════════════════════════════════════════════════
# 2. RENDIMIENTO POR PRODUCTO
# ═══════════════════════════════════════════════════════════════════════════
_K_PROD = "_mov_merma_prod"
"""El producto en foco: UNO para «Rendimiento» y «Proveedor por kg útil»
(regla #647). Lo escriben sus desplegables y listas, y el salto desde
Recetas › Carta costeada (`ir_al_corte`)."""
_K_VER = "_mov_merma_prod_ver"
K_CORTE = "_mov_merma_corte"
"""El corte en foco de «Rendimiento» (su `clave_corte`)."""
K_MODO = "mov_merma_rend_modo"
MODO_CORTE, MODO_INSUMO = "Precio del corte", "Costo del insumo"
K_LISTA = "mov_merma_rend_lista"
LISTA_CORTES, LISTA_CAMBIOS = "Cortes de este producto", "Productos que cambiaron"
SEC_REND, SEC_PROV, SEC_REV = ("mov_sec_merma_rend", "mov_sec_merma_prov",
                               "mov_sec_merma_rev")
VISTA_REND, VISTA_REV = "Rendimiento por producto", "Merma para revisar"
"""Los ids de las dos vistas a las que se salta desde Recetas: los de
`graficos/movimientos.py::_PILA_PRODUCCION`."""
REPORTE_MERMA = "Producción"
RAIL_PRODUCCION = "prod_graf_tipo"
"""El reporte de estas secciones y el `state_key` de su rail
(`movimientos.py::_render_rail`): Producción desde la regla #709 — hasta
ese día eran el final de la pila de Movimientos, con `mov_graf_tipo`. Vive
acá y no allá porque `movimientos.py` importa este módulo: al revés sería
un import circular. Lo vigila `test_graficos.py::_pruebas_merma`."""
K_FOCO_REV = "_mov_merma_rev_foco"

# «Porcionamientos» y «Rendimiento por producto» son UNA vista desde el
# 2026-10-23 (regla #712): «Porcionamientos», con dos perspectivas, en la
# sección `SEC_PORC` de la pila de Producción. Viven acá por lo mismo que
# `RAIL_PRODUCCION`: los leen `produccion.py`, el salto de Costo de Carta
# y `_avisar_a`.
SEC_PORC = "mov_sec_persp_porc"
VISTA_PORC = "Porcionamientos"
K_PERSP_PORC = "_prod_persp_porc"
PERSPECTIVAS_PORC = (
    ("Por período", "mov_sec_porc", "Porcionamientos", "Porcionamientos"),
    ("Rendimiento", SEC_REND, VISTA_REND, "Rendimiento"),
)
EJES_PORC = ((K_PERSP_PORC, "Ver", tuple(p[0] for p in PERSPECTIVAS_PORC)),)


def _avisar_a(seccion):
    """El producto es UNO para dos secciones de la pila, y cada una es su
    propio fragment: si la otra ya se dibujó, una corrida completa para que
    se entere (`K_RECARGA`, el mismo camino que la valorización, regla
    #644). `_pila_visto_<clave>` lo pone `graficos/base.py::seccion_perezosa`
    después de dibujar una sección por primera vez. Rendimiento es una
    perspectiva de «Porcionamientos» (#712): avisa a esa sección, y sólo si
    la perspectiva a la vista es ella."""
    if seccion == SEC_REND:
        if st.session_state.get(K_PERSP_PORC) != PERSPECTIVAS_PORC[1][0]:
            return
        seccion = SEC_PORC
    if st.session_state.get(f"_pila_visto_{seccion}"):
        st.session_state[K_RECARGA] = True


def _al_elegir_producto(key):
    st.session_state[_K_PROD] = st.session_state.get(key)
    _avisar_a(SEC_PROV)


def ir_al_corte(cod_prod, clave):
    """Lo que deja escrito un salto a «Rendimiento» parado en el producto
    `cod_prod` y su corte `clave`, con el precio del corte a la vista. El
    llamador pide además la vista (`navegacion._ir_a_vista`)."""
    ss = st.session_state
    ss[_K_PROD], ss[K_CORTE] = str(cod_prod), str(clave)
    ss[K_MODO], ss[K_LISTA] = MODO_CORTE, LISTA_CORTES


def ir_a_revisar(doc):
    """Lo que deja escrito un salto a «Para revisar» parado en el
    porcionamiento `doc` (si está en su rango)."""
    st.session_state[K_FOCO_REV] = str(doc)


def _fig_merma(xs, norm, mes, ini, fin, u):
    fig = go.Figure()
    if norm is not None and np.isfinite(norm["q1"]):
        fig.add_scatter(x=[ini, fin], y=[norm["q3"]] * 2, mode="lines",
                        line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=[ini, fin], y=[norm["q1"]] * 2, mode="lines",
                        line=dict(width=0), fill="tonexty",
                        fillcolor=LAVANDA_FONDO, hoverinfo="skip",
                        showlegend=False)
    raros = xs["m_alta"] | xs["m_baja"] | xs["m_cero"] | xs["m_sinpeso"]
    for sub, color, simb, tam in ((xs[~raros], ACENTO, "circle", 7),
                                  (xs[raros], AJUSTE_NEG, "diamond", 9)):
        if sub.empty:
            continue
        txt = [f"PO-{d} · {f:%d/%m/%Y}<br>{_c(m)} de {_c(c)} {u} · <b>{_p(p)}</b>"
               f"<br>{html.escape(str(us))}"
               + (f" · {html.escape(pv)}" if isinstance(pv, str) else "")
               for d, f, m, c, p, us, pv in zip(
                   sub["doc"], sub["fecha"], sub["merma_cant"], sub["cant"],
                   sub["pct"], sub["tipo"], sub["prov"])]
        fig.add_scatter(x=sub["fecha"], y=sub["pct"], mode="markers",
                        marker=dict(size=tam, color=color, symbol=simb,
                                    opacity=0.6 if simb == "circle" else 1),
                        text=txt, hovertemplate="%{text}<extra></extra>",
                        showlegend=False)
    if not mes.empty:
        fig.add_scatter(
            x=mes["mes"], y=mes["pct"], mode="lines+markers",
            line=dict(color=TEXTO_PRINCIPAL, width=2),
            marker=dict(size=5, color=TEXTO_PRINCIPAL),
            text=[f"{MESES_ABR_ES[m.month - 1]} {m.year}" for m in mes["mes"]],
            hovertemplate="%{text}: %{y:.1%} en el mes<extra></extra>",
            showlegend=False)
    _compras_layout(fig, alto=alturas.MERMA_FIG)
    vals, rots = _ticks_meses(ini, fin)
    fig.update_layout(margin=dict(l=44, r=8, t=24, b=24),
                      title=dict(text="Merma por porcionamiento",
                                 font=dict(size=12, color=GRIS_TEXTO), x=0))
    fig.update_xaxes(type="date", range=[ini, fin], tickvals=vals,
                     ticktext=rots, fixedrange=True)
    fig.update_yaxes(tickformat=".0%", showticklabels=True, rangemode="tozero",
                     fixedrange=True)
    return fig


def _fig_tiempo(alto, ini, fin):
    """El marco de los dos gráficos de abajo de «Rendimiento»: sin título
    —lo lleva el renglón de arriba, con el selector— y con el eje de meses
    del de la merma."""
    fig = go.Figure()
    _compras_layout(fig, alto=alto)
    vals, rots = _ticks_meses(ini, fin)
    fig.update_layout(margin=dict(l=44, r=8, t=8, b=24))
    fig.update_xaxes(type="date", range=[ini, fin], tickvals=vals,
                     ticktext=rots, fixedrange=True)
    fig.update_yaxes(tickprefix="S/ ", showticklabels=True, fixedrange=True)
    return fig


def _fig_precio(xs, mes, p_hoy, ini, fin, u):
    fig = _fig_tiempo(alturas.MERMA_FIG_PRECIO, ini, fin)
    x = xs[xs["costo_dia"] > 0]
    if not x.empty:
        pk = x["costo_dia"] / x["cant"]
        fig.add_scatter(
            x=x["fecha"], y=pk, mode="markers",
            marker=dict(size=6, color=ACENTO, opacity=0.45),
            text=[f"PO-{d} · {f:%d/%m/%Y}<br>{_s(v, 2)} por {u}"
                  + (f"<br>{html.escape(pv)}" if isinstance(pv, str) else "")
                  for d, f, v, pv in zip(x["doc"], x["fecha"], pk, x["prov"])],
            hovertemplate="%{text}<extra></extra>", showlegend=False)
    m = mes.dropna(subset=["pkg"])
    if not m.empty:
        fig.add_scatter(
            x=m["mes"], y=m["pkg"], mode="lines+markers",
            line=dict(color=TEXTO_PRINCIPAL, width=2),
            marker=dict(size=5, color=TEXTO_PRINCIPAL),
            text=[f"{MESES_ABR_ES[t.month - 1]} {t.year}" for t in m["mes"]],
            hovertemplate="%{text}: S/ %{y:,.2f}<extra></extra>",
            showlegend=False)
    if p_hoy and np.isfinite(p_hoy):
        fig.add_scatter(x=[ini, fin], y=[p_hoy] * 2, mode="lines",
                        line=dict(color=AJUSTE_NEG, width=1.5, dash="dash"),
                        hovertemplate=f"Precio promedio de hoy: {_s(p_hoy, 2)}"
                                      "<extra></extra>", showlegend=False)
    return fig


def _fig_precio_corte(xs, filas, pm, ini, fin, uc):
    """El precio por unidad de UN corte: un punto por porcionamiento, la
    línea del mes y, cortada, el precio con la merma normal del producto."""
    fig = _fig_tiempo(alturas.MERMA_FIG_PRECIO, ini, fin)
    cab = xs.set_index("doc")
    f = filas[filas["cant"] > 0]
    if not f.empty:
        precio = f["valor"] / f["cant"]
        fechas = f["doc"].map(cab["fecha"])
        fig.add_scatter(
            x=fechas, y=precio, mode="markers",
            marker=dict(size=6, color=ACENTO, opacity=0.45),
            text=[f"PO-{d} · {t:%d/%m/%Y}<br>{_s(p, 2)} por {uc} · salieron "
                  f"{_c(q)} {uc}<br>merma del porcionamiento: "
                  f"{_p(cab.at[d, 'pct'])}"
                  for d, t, p, q in zip(f["doc"], fechas, precio, f["cant"])],
            hovertemplate="%{text}<extra></extra>", showlegend=False)
    m = pm.dropna(subset=["precio"])
    if not m.empty:
        fig.add_scatter(
            x=m["mes"], y=m["precio"], mode="lines+markers",
            line=dict(color=TEXTO_PRINCIPAL, width=2),
            marker=dict(size=5, color=TEXTO_PRINCIPAL),
            text=[f"{MESES_ABR_ES[t.month - 1]} {t.year}: {_s(p, 2)} por {uc}"
                  f" · merma {_p(r)}"
                  for t, p, r in zip(m["mes"], m["precio"], m["merma"])],
            hovertemplate="%{text}<extra></extra>", showlegend=False)
        n = m.dropna(subset=["normal"])
        if not n.empty:
            fig.add_scatter(
                x=n["mes"], y=n["normal"], mode="lines+markers",
                line=dict(color=AJUSTE_NEG, width=1.5, dash="dash"),
                marker=dict(size=4, color=AJUSTE_NEG),
                text=[f"{MESES_ABR_ES[t.month - 1]} {t.year}: {_s(p, 2)} con "
                      "la merma normal" for t, p in zip(n["mes"], n["normal"])],
                hovertemplate="%{text}<extra></extra>", showlegend=False)
    return fig


def _rotulo_corte(r):
    """La causa principal de un corte, para su celda."""
    if not r["a"]["n"]:
        return "sin cortes antes"
    if not r["b"]["n"]:
        return "no salió en 90 días"
    if not r["desglose"]:
        return "sin peso registrado"
    v = r["desglose"][r["causa"]]
    return f"{r['causa']} {'+' if v >= 0 else '−'}{abs(v):,.2f}"


def _signo_s(v):
    return f"{'+' if v >= 0 else '−'}S/ {abs(v):,.2f}"


def _factores_visibles(des):
    """Los factores del desglose de mayor a menor; «otros» sólo si pesa:
    más del 5 % de lo que se movió."""
    tot = sum(abs(v) for v in des.values()) or 1.0
    return sorted((k for k in FACTORES
                   if k != "otros" or abs(des[k]) > 0.05 * tot),
                  key=lambda k: -abs(des[k]))


def _nota_corte(r, u):
    """El renglón de debajo del gráfico del corte: su precio antes y en los
    últimos 90 días, y por qué cambió. HTML."""
    a, b, des = r["a"], r["b"], r["desglose"]
    if not des:
        return ("Con porcionamientos antes y en los últimos 90 días, acá se "
                "reparte el cambio de su precio entre el insumo, la merma y "
                "el gramaje.")
    var = b["P"] / a["P"] - 1
    partes = " · ".join(
        f'<span style="color:{_color_signo(des[k])};font-weight:600">{k} '
        f'{_signo_s(des[k])}</span>' for k in _factores_visibles(des))
    return (f"Antes <b>{_s(a['P'], 2)}</b> → 90 días <b>{_s(b['P'], 2)}</b> "
            f'<span style="color:{_color_signo(var)};font-weight:600">'
            f"({'+' if var >= 0 else '−'}{abs(var) * 100:.0f}%)</span>: "
            f"{partes}.")


def _ayuda_causa(u):
    return (f"Qué movió más el precio del corte: el **insumo** (lo que costó "
            f"cada {u} que entró), la **merma** (lo que no recibe costo: el "
            f"Almacén reparte lo pagado entre lo que queda), el **gramaje** "
            f"(los {u} del producto que el Almacén le asigna a cada unidad "
            "del corte) u **otros** (la mezcla de porcionamientos de distinto "
            "costo). En soles por unidad; los cuatro suman exacto el "
            "cambio (índice LMDI, Ang 2005). El reparto entero, debajo del "
            "gráfico.")


def _lista_cortes(pc, pos, nombres, u):
    """«Cortes de este producto»: el precio por unidad de cada corte antes
    y en los últimos 90 días, y qué lo movió. Las celdas sin dato llevan
    ∞ y el Styler las escribe «—»: un NaN se vería «None» (regla #529)."""
    st.markdown(f'<div style="font-size:12px;color:{GRIS_TEXTO}">Precio por '
                'unidad de cada corte: los últimos 90 días contra el resto de '
                'la ventana. Clic para ver su curva.</div>',
                unsafe_allow_html=True)
    inf = float("inf")
    tc = pd.DataFrame({
        "Corte": nombres,
        "Unid.": [unidad_corta(x) for x in pc["unid"]],
        "Antes": [r["P"] if r["n"] else inf for r in pc["a"]],
        "90 días": [r["P"] if r["n"] else inf for r in pc["b"]],
        "Δ": [v if np.isfinite(v) else inf for v in pc["var"]],
        "Por qué": [_rotulo_corte(r) for _, r in pc.iterrows()],
    })
    colores = [_color_signo(r["desglose"][r["causa"]]) if r["desglose"]
               else GRIS_TEXTO for _, r in pc.iterrows()]
    fmt = (lambda v: f"{v:,.2f}" if np.isfinite(v) else "—")
    sty = (tc.style.format({"Antes": fmt, "90 días": fmt,
                            "Δ": lambda v: (f"{'+' if v >= 0 else '−'}"
                                            f"{abs(v) * 100:.0f}%"
                                            if np.isfinite(v) else "—")})
           .map(lambda v: (f"color: {_color_signo(v)}; font-weight: 600"
                           if np.isfinite(v) else ""), subset=["Δ"])
           .apply(lambda c: [f"color: {k}" for k in colores],
                  subset=["Por qué"])
           .apply(_resaltar(pos), axis=1))
    _tabla_elegible(
        "mov_merma_cortes", sty, list(pc["clave"]), pos,
        _alto_tabla(len(tc), alturas.MERMA_CAMBIOS),
        # Suman lo que mide la columna a 1323px (~436 sin la de la marca):
        # con «medium» en el corte, «Por qué» quedaba afuera.
        {"Corte": st.column_config.TextColumn(width=126),
         "Unid.": st.column_config.TextColumn(width=40),
         "Antes": st.column_config.Column(
             width=50,
             help="Soles por unidad del corte en el resto de la ventana: lo "
                  "que valió lo que salió ÷ lo que salió."),
         "90 días": st.column_config.Column(
             width=54, help="Lo mismo, en los últimos 90 días."),
         "Δ": st.column_config.Column(width=44),
         "Por qué": st.column_config.Column(width=110,
                                            help=_ayuda_causa(u))})


def _nombres_de_cortes(pc):
    """El nombre corto de cada corte, salvo que dos queden iguales —aunque
    sea por una mayúscula: «(P) Pulpo Cocido 120gr…» y «(Rs) Pulpo cocido
    120gr…»—: ésos van enteros."""
    cortos = [nombre_corto(n) for n in pc["nombre"]]
    claves = [c.casefold() for c in cortos]
    return [str(n).strip() if claves.count(k) > 1 else c
            for c, k, n in zip(cortos, claves, pc["nombre"])]


def tarjeta_rendimiento(d_hist, cols, rango):
    """La sección «Rendimiento por producto». `d_hist` es el parquet entero
    con el chip «Sub Almacén»; la ventana la elige la tarjeta y termina
    donde termina `rango` o, sin él, en el último día con datos (regla
    #617: Movimientos lo llama sin rango).

    Desde el 2026-10-12 (regla #647) el segundo gráfico es, de entrada, el
    PRECIO DEL CORTE elegido en la lista de la derecha («Cortes de este
    producto»), con su cambio de los últimos 90 días repartido entre el
    insumo, la merma y el gramaje; el costo del insumo que entró —el
    gráfico de antes— sigue a un clic."""
    with st.container(border=True, key=CARD_REND):
        modo = valorizacion()
        precios = precios_hoy()
        fin_f = fin_de_ventana(d_hist, rango)
        # columnas-internas: el título a la izquierda, la ventana, la
        # valorización (regla #644) y el producto a la derecha, en el mismo
        # renglón. La del medio pide 492px —258 de la ventana y 226 de la
        # valorización—: con menos, las dos se apilaban y la cabecera pasaba
        # de 32 a 80px (medido a 1323px).
        c_tit, c_ven, c_prod = st.columns([0.8, 2.0, 1.4],
                                          vertical_alignment="center")
        with c_ven, st.container(key="mov_merma_rend_ctl", horizontal=True,
                                 vertical_alignment="center", gap="small"):
            ini, fin = _ventana("mov_merma_rend_ventana", fin_f)
            control_valorizacion("mov_merma_rend_ctl")
        todo, cortes = porcionamientos(
            d_hist[(d_hist["_fecha"] >= fin - pd.Timedelta(days=DIAS_NORMAL))
                   & (d_hist["_fecha"] < fin)], cols)
        if todo.empty:
            with c_tit:
                _titulo("Rendimiento por producto")
            st.info("Sin porcionamientos en la ventana.")
            return
        norm = normales(todo)
        b = valorizar(todo[todo["fecha"] >= ini], modo, precios)
        b = marcar(con_proveedor(b, _compras()), norm, cortes)
        ch = cambios(b, fin)

        # El clic en «Productos que cambiaron» manda sobre el desplegable.
        ss = st.session_state
        k_ult = "_mov_merma_cambio_ult"
        _foco_anterior("mov_merma_cambios", "_mov_merma_cambio_clic")
        clic = ss.pop("_mov_merma_cambio_clic", None)
        if clic is not None and clic != ss.get(k_ult):
            ss[_K_PROD] = clic
            _avisar_a(SEC_PROV)
        ss[k_ult] = clic if clic is not None else ss.get(k_ult)

        orden = (b.groupby("cod")["valor"].sum().sort_values(ascending=False))
        opciones = orden.index.tolist()
        nombres = b.drop_duplicates("cod").set_index("cod")["prod"]
        prod = ss.get(_K_PROD)
        if prod not in opciones:
            prod = ch.index[0] if len(ch) else opciones[0]
            ss[_K_PROD] = prod
        ver = ss.get(_K_VER, 0)
        wkey = f"mov_merma_rend_prod_{ver}"
        if wkey in ss and ss[wkey] != prod:
            ver += 1
            ss[_K_VER] = ver
            wkey = f"mov_merma_rend_prod_{ver}"
        with c_tit:
            _titulo("Rendimiento por producto")
        with c_prod:
            st.selectbox(
                "Producto", opciones, index=opciones.index(prod), key=wkey,
                format_func=lambda c: f"{nombres.get(c, c)} · {_s(orden.get(c, 0))}",
                on_change=_al_elegir_producto, args=(wkey,),
                label_visibility="collapsed")

        xs = b[b["cod"] == prod]
        u = unidad_corta(xs["unid"].iloc[0]) if len(xs) else ""
        rec = xs["fecha"] >= fin - pd.Timedelta(days=DIAS_RECIENTES)

        # ── Los cortes del producto: cuál está en foco ───────────────────
        # Se lee ANTES de dibujar nada: el clic en la lista de la derecha
        # pone a la vista el precio de ESE corte, y el selector del
        # gráfico se dibuja antes que la lista (regla #399).
        pc = precios_de_cortes(xs, cortes, fin)
        claves = pc["clave"].tolist()
        corte = ss.get(K_CORTE)
        if corte not in claves:
            corte = claves[0] if claves else None
        _foco_anterior("mov_merma_cortes", "_mov_merma_corte_clic")
        clic_c = ss.pop("_mov_merma_corte_clic", None)
        if clic_c is not None and clic_c in claves and clic_c != corte:
            corte = clic_c
            ss[K_MODO] = MODO_CORTE
        ss[K_CORTE] = corte
        ss.setdefault(K_MODO, MODO_CORTE)
        ss.setdefault(K_LISTA, LISTA_CORTES)
        sel = pc.iloc[claves.index(corte)] if corte is not None else None
        nombres_c = _nombres_de_cortes(pc)

        def _pct(z):
            return z["merma_cant"].sum() / z["cant"].sum() if z["cant"].sum() else np.nan

        def _pk(z):
            return z["costo_dia"].sum() / z["cant"].sum() if z["cant"].sum() else np.nan

        p_r, p_a = _pct(xs[rec]), _pct(xs[~rec])
        k_r, k_a = _pk(xs[rec]), _pk(xs[~rec])
        queda = (xs["cant"] - xs["merma_cant"]).sum()
        p_hoy = float(precios.get(prod, np.nan)) if precios is not None else np.nan
        _var = (lambda a, b_: "" if not (np.isfinite(a) and np.isfinite(b_))
                else (f'<span style="color:{_color_signo(a - b_)};font-weight:600">'))
        _tiles([
            ("Merma de la ventana", _p(_pct(xs)),
             f"{len(xs)} porcionamientos · {_c(xs['cant'].sum())} {u}"),
            ("Últimos 90 días", _p(p_r),
             (f'{_var(p_r, p_a)}{_pp(p_r - p_a)}</span> contra {_p(p_a)} antes'
              if np.isfinite(p_r) and np.isfinite(p_a) else "sin comparación")),
            (f"Costo del día por {u}, 90 días", _s(k_r, 2),
             (f'{_var(k_r, k_a)}{"+" if k_r >= k_a else "−"}'
              f'{abs(k_r / k_a - 1) * 100:.0f}%</span> contra {_s(k_a, 2)}'
              if np.isfinite(k_r) and np.isfinite(k_a) and k_a else "")
             + (f" · hoy {_s(p_hoy, 2)}" if np.isfinite(p_hoy) else "")),
            (f"Costo por {u} útil", _s(xs["costo_dia"].sum() / queda, 2)
             if queda > 0 else "—", "Lo pagado ÷ lo que quedó"),
            ("Merma en soles", _s(xs["valor"].sum()), _rot_valor(modo)),
        ])
        # columnas-internas: los dos gráficos del producto y, al lado, la
        # lista que elige el corte u otro producto.
        c_g, c_l = st.columns([1.45, 1], gap="medium")
        mes = por_mes(xs)
        n_row = norm.loc[prod] if prod in norm.index else None
        med = (float(n_row["med"]) if n_row is not None
               and n_row["n"] >= N_MIN_NORMAL else None)
        ver_corte = ss.get(K_MODO) == MODO_CORTE and sel is not None
        if ver_corte:
            uc = unidad_corta(sel["unid"])
            titulo = (f"«{nombres_c[claves.index(corte)]}», S/ por {uc}"
                      + (f" · cortada: con merma normal ({_p(med, 0)})"
                         if med is not None else ""))
        else:
            titulo = (f"Costo del día por {u} que entró · cortada: precio de "
                      "hoy")
        with c_g:
            st.plotly_chart(_fig_merma(xs, n_row, mes, ini, fin, u),
                            use_container_width=True,
                            key=f"mov_merma_fig_m_{prod}",
                            config={"displaylogo": False,
                                    "displayModeBar": False})
            with st.container(key="mov_merma_rend_g2_cab", horizontal=True,
                              vertical_alignment="center", gap="small"):
                st.markdown(f'<div class="mov-merma-g2-tit" '
                            f'title="{html.escape(titulo)}">'
                            f'{html.escape(titulo)}</div>',
                            unsafe_allow_html=True)
                st.segmented_control(
                    "Qué precio", (MODO_CORTE, MODO_INSUMO), key=K_MODO,
                    required=True, label_visibility="collapsed")
            if ver_corte:
                filas = cortes[cortes["doc"].isin(xs["doc"])
                               & (clave_corte(cortes) == corte)]
                st.plotly_chart(
                    _fig_precio_corte(xs, filas,
                                      precio_corte_por_mes(xs, filas, med),
                                      ini, fin, uc),
                    use_container_width=True,
                    key=f"mov_merma_fig_c_{prod}_{corte}",
                    config={"displaylogo": False, "displayModeBar": False})
                nota = _nota_corte(sel, u)
            else:
                st.plotly_chart(_fig_precio(xs, mes, p_hoy, ini, fin, u),
                                use_container_width=True,
                                key=f"mov_merma_fig_p_{prod}",
                                config={"displaylogo": False,
                                        "displayModeBar": False})
                nota = (f"Lo que costó cada {u} que entró (sus cortes ÷ "
                        "lo porcionado): el «insumo» del precio de los "
                        "cortes.")
            with st.container(key="mov_merma_rend_nota"):
                st.markdown(f'<div class="mov-merma-nota">{nota}</div>',
                            unsafe_allow_html=True)
        with c_l:
            lista = st.segmented_control(
                "Lista", (LISTA_CORTES, LISTA_CAMBIOS), key=K_LISTA,
                required=True, label_visibility="collapsed")
            if lista == LISTA_CORTES:
                if pc.empty:
                    st.caption("Este producto no tiene cortes en la ventana.")
                else:
                    _lista_cortes(pc, claves.index(corte), nombres_c, u)
                return
            st.markdown(f'<div style="font-size:12px;color:{GRIS_TEXTO}">'
                        'Últimos 90 días contra el resto de la ventana, con 5 '
                        'porcionamientos o más en cada lado. Clic para '
                        'verlo.</div>', unsafe_allow_html=True)
            if ch.empty:
                st.caption("Ningún producto con datos suficientes.")
                return
            tc = pd.DataFrame({
                "Producto": [nombres.get(c, c) for c in ch.index],
                "Antes": ch["pct_ant"].to_numpy(),
                "90 días": ch["pct_rec"].to_numpy(),
                "Δ merma": ch["dpp"].to_numpy(),
                "Δ costo": ch["dprecio"].fillna(0).to_numpy(),
                "Impacto": ch["impacto"].to_numpy(),
            })
            sty = (tc.style.format({"Antes": _p, "90 días": _p, "Δ merma": _pp,
                                    "Δ costo": lambda v: f"{v * 100:+.0f}%",
                                    "Impacto": _s})
                   .map(lambda v: f"color: {_color_signo(v)}; font-weight: 600",
                        subset=["Δ merma", "Δ costo"]))
            _tabla_elegible(
                "mov_merma_cambios", sty, list(ch.index), 0,
                _alto_tabla(len(tc), alturas.MERMA_CAMBIOS),
                {"Producto": st.column_config.TextColumn(width="medium"),
                 "Impacto": st.column_config.Column(
                     help=f"Los puntos de merma de más (o de menos) sobre lo "
                          f"porcionado en los 90 días, {_rot_valor(modo)}."),
                 "Δ costo": st.column_config.Column(
                     help="Cómo cambió el costo del día por unidad que "
                          "entró.")},
                requerida=False)


# ═══════════════════════════════════════════════════════════════════════════
# 3. PROVEEDOR POR KG ÚTIL
# ═══════════════════════════════════════════════════════════════════════════
def _rotulo_ventana(ini, fin):
    """«del 10 abr al 9 oct 2026»: los días que entran en la ventana."""
    ult = fin - pd.Timedelta(days=1)
    a = f"{ini.day} {MESES_ABR_ES[ini.month - 1]}" + (
        f" {ini.year}" if ini.year != ult.year else "")
    return f"del {a} al {ult.day} {MESES_ABR_ES[ult.month - 1]} {ult.year}"


def _corto_prov(nombre):
    """«INVERSIONES BARCO AZUL E.I.R.L.» → «BARCO AZUL»: para una celda."""
    t = re.sub(r"\b(S\.?A\.?C\.?|E\.?I\.?R\.?L\.?|S\.?A\.?|SOCIEDAD ANONIMA "
               r"CERRADA)(?=\s|$)\.?", "", str(nombre)).strip()
    t = re.sub(r"^(INVERSIONES|CORPORACION|COMPAÑIA|DISTRIBUIDORA)\s+", "", t,
               flags=re.IGNORECASE)
    return " ".join(t.split()[:2]) or str(nombre)


def _como_sale(s, nombre, u, pm, t, sin, minimo_porc):
    """El recuadro «Cómo sale» del proveedor elegido (regla #655): sus tres
    cuentas, lo pagado de más del producto con su cuenta, los proveedores
    que no compiten por tener pocos porcionamientos y los que quedaron sin
    proveedor. HTML."""
    def fila(rot, cuenta, res):
        return (f'<div style="display:grid;grid-template-columns:118px 1fr;'
                f'column-gap:8px;font-size:12.5px;line-height:17px">'
                f'<span style="color:{GRIS_TEXTO}">{rot}</span><span>{cuenta} = '
                f'<b>{res}</b></span></div>')
    queda = s["cant"] - s["merma"]
    filas = [
        fila("Merma", f"{_c(s['merma'])} de {_c(s['cant'])} {u}", _p(s["pct"])),
        fila(f"S/ por {u}", f"{_s(s['costo'], 2)} ÷ {_c(s['cant'])} {u}",
             _s(s["pkg"], 2)),
        fila(f"S/ por {u} útil",
             f"{_s(s['costo'], 2)} ÷ ({_c(s['cant'])} − {_c(s['merma'])}) {u}",
             _s(s["util"], 2) if queda > 0 else "—"),
    ]
    notas = []
    if pm is not None:
        partes = [(p, v) for p, v in pm["de_mas"].items() if v > 0]
        if len(partes) == 1:
            p, v = partes[0]
            detalle = (f"{html.escape(str(p))}, ({t.loc[p, 'util']:,.2f} − "
                       f"{pm['minimo']:,.2f}) × {_c(pm['queda'][p])} {u} útiles")
        else:
            detalle = (f"Σ (su útil − {pm['minimo']:,.2f}) × sus {u} útiles: "
                       + " · ".join(f"{html.escape(_corto_prov(p))} {_s(v)}"
                                    for p, v in sorted(partes, key=lambda z: -z[1])))
        if partes:
            notas.append((TEXTO_PRINCIPAL,
                          f"<b>Pagado de más {_s(pm['extra'])}</b> = {detalle}: lo "
                          f"que habría costado de menos comprarle todo eso a "
                          f"{html.escape(str(pm['mejor']))}."))
    for p, r in t[t["n"] < minimo_porc].iterrows():
        barato = pm is not None and r["util"] < pm["minimo"]
        notas.append((AJUSTE_ALERTA_TEXTO if barato else GRIS_TEXTO,
                      f"{html.escape(str(p))} ({int(r['n'])} porcionamiento"
                      f"{'' if r['n'] == 1 else 's'}) sale a {_s(r['util'], 2)} por "
                      f"{u} útil{', <b>más barato que el «Mejor»</b>,' if barato else ''}"
                      f" pero con menos de {minimo_porc} no entra en «Mejor» ni "
                      "en «Pagado de más»."))
    if sin:
        notas.append((GRIS_TEXTO,
                      f"{sin} porcionamiento{'s' if sin != 1 else ''} de este "
                      "producto sin proveedor asignable quedan fuera."))
    pie = "".join(f'<div style="font-size:12px;line-height:16px;color:{c}">{n}</div>'
                  for c, n in notas)
    return (f'<div style="border:1px solid {GRIS_BORDE};background:{LAVANDA_FILA};'
            f'border-radius:8px;padding:8px 12px;display:flex;flex-direction:column;'
            f'gap:4px"><div style="font-size:12.5px;font-weight:700;color:{ACENTO}">'
            f'Cómo sale · {html.escape(str(nombre))}</div>{"".join(filas)}'
            + (f'<div style="border-top:1px solid {GRIS_LINEA};margin-top:2px;'
               f'padding-top:4px;display:flex;flex-direction:column;gap:3px">'
               f'{pie}</div>' if notas else "") + "</div>")


def _ir(clave, valor):
    st.session_state[clave] = valor


def _tabla_rastro(rs, u, s):
    """Los porcionamientos de un proveedor con lo que explica cada número,
    y una fila Total que reproduce su línea (regla #655)."""
    inf = float("inf")
    tot = pd.DataFrame({
        "N° porc.": [f"Total · {len(rs)}"], "Fecha": [""],
        "Entró": [s["cant"]], "Merma": [s["merma"]], "%": [s["pct"]],
        "S/ día": [s["pkg"]], "Compra": [""], "Otro cerca": [""]})
    tr = pd.DataFrame({
        "N° porc.": rs["doc"].astype(str),
        "Fecha": rs["fecha"].dt.strftime("%d/%m"),
        "Entró": rs["cant"], "Merma": rs["merma_cant"], "%": rs["pct"],
        "S/ día": rs["pkg"].fillna(inf),
        "Compra": [f"{c:%d/%m} · {p:,.2f}" if pd.notna(c) else "—"
                            for c, p in zip(rs["compra"], rs["pcompra"])],
        "Otro cerca": [f"{f:%d/%m} · {_corto_prov(o)}" if isinstance(o, str) else "—"
                       for o, f in zip(rs["otro"], rs["f_otro"])],
    })
    # El Total ARRIBA: con muchas filas la tabla se desliza, y abajo no se veía.
    t = pd.concat([tot, tr], ignore_index=True)
    difiere = [False] + rs["difiere"].tolist()
    total = 0
    alerta = f"background-color: {AJUSTE_ALERTA_FONDO}; color: {AJUSTE_ALERTA_TEXTO}; font-weight: 600"

    def estilo(r):
        if r.name == total:
            return [f"background-color: {LAVANDA_FILA}; font-weight: 700"] * len(r)
        out = [""] * len(r)
        if difiere[r.name]:
            out[list(r.index).index("S/ día")] = alerta
        if r["Otro cerca"] != "—":
            out[list(r.index).index("Otro cerca")] = f"color: {AJUSTE_ALERTA_TEXTO}"
        return out

    _n = (lambda v: f"{v:,.2f}" if np.isfinite(v) else "—")
    sty = (t.style.format({"Entró": _n, "Merma": _n, "%": lambda v: _p(v, 0),
                           "S/ día": _n})
           .apply(estilo, axis=1))
    # Suman la columna a 1323px (~523): con anchos libres, «Otro cerca»
    # quedaba afuera.
    st.dataframe(
        sty, hide_index=True, row_height=27,
        height=_alto_tabla(len(t), alturas.MERMA_PROV),
        column_config={
            "N° porc.": st.column_config.TextColumn(width=80),
            "Fecha": st.column_config.TextColumn(width=44),
            "Entró": st.column_config.Column(width=48, help=f"Lo porcionado, en {u}."),
            "Merma": st.column_config.Column(width=48, help=f"La merma, en {u}."),
            "%": st.column_config.Column(width=38),
            "S/ día": st.column_config.Column(
                width=52,
                help=f"El costo del día por {u}: lo que valieron sus cortes ÷ lo "
                     "porcionado. En ámbar, si se aleja más de 5 % de lo pagado en "
                     "la compra asignada: el Almacén costea al promedio de lo que "
                     "tiene en stock."),
            "Compra": st.column_config.TextColumn(
                width=88,
                help=f"La compra asignada: la última de este producto hasta "
                     f"{DIAS_PROVEEDOR} días antes del porcionamiento: su día y "
                     f"lo que se le pagó por {u}."),
            "Otro cerca": st.column_config.TextColumn(
                help=f"Quién más le vendió este producto en los {DIAS_UNICO} "
                     "días previos: la atribución no es segura.")})


def tarjeta_proveedores(d_hist, cols, rango):
    """La sección «Proveedor por kg útil». Siempre al costo del día.

    Desde el 2026-10-13 (regla #655) cada número se puede rastrear: la
    ventana dice sus días y empieza a las 00:00, la tabla de proveedores
    marca al «mejor», al «más caro» y a los que tienen pocos porcionamientos
    para competir, un recuadro hace las cuentas del proveedor elegido y de
    «Pagado de más», y «Ver sus porcionamientos» los lista con la compra
    que se le asignó a cada uno."""
    with st.container(border=True, key=CARD_PROV):
        fin_f = fin_de_ventana(d_hist, rango)
        # columnas-internas: título, ventana y el filtro de proveedor único
        # en un renglón.
        c_tit, c_ven, c_uni = st.columns([1.3, 0.9, 1.3],
                                         vertical_alignment="center")
        with c_tit:
            _titulo("Costo por kg útil, por proveedor")
        with c_ven:
            ini, fin = _ventana("mov_merma_prov_ventana", fin_f)
        with c_uni:
            unico = st.toggle(
                "Sólo con un proveedor en los 21 días previos",
                key="mov_merma_prov_unico",
                help="El proveedor de un porcionamiento es el de la última "
                     "compra del producto hasta 45 días antes: el Almacén no "
                     "guarda de qué lote salió. Prendido, quedan sólo los "
                     "porcionamientos sin ambigüedad.")
        compras = _compras()
        base, _ = porcionamientos(
            d_hist[(d_hist["_fecha"] >= ini) & (d_hist["_fecha"] < fin)], cols)
        if compras is None:
            st.info("No se pudo leer compras.parquet: sin proveedores.")
            return
        if base.empty:
            st.info("Sin porcionamientos en la ventana.")
            return
        b = con_proveedor(base, compras)
        r = resumen_proveedores(b, unico)
        nombres = b.drop_duplicates("cod").set_index("cod")["prod"]
        st.markdown(f'<div style="font-size:13px;color:{GRIS_TEXTO}"><b style="'
                    f'color:{TEXTO_PRINCIPAL}">{_rotulo_ventana(ini, fin).capitalize()}.'
                    '</b> Lo que de verdad cuesta cada unidad aprovechable: lo '
                    'pagado ÷ lo que queda después de la merma. Siempre al costo '
                    'del día — a precio de hoy todos los proveedores costarían lo '
                    'mismo.</div>', unsafe_allow_html=True)
        if r.empty:
            st.info("Ningún producto con dos proveedores de 5 "
                    "porcionamientos o más en la ventana.")
            return
        codigos = r.index.tolist()
        # EL PRODUCTO ES UNO con «Rendimiento» (regla #647): un clic acá lo
        # lleva allá, y lo que se eligió allá se enfoca acá. La tabla se
        # estrena (otra key) cuando el cambio viene de afuera: su selección
        # es de la KEY (regla #556) y si no, seguiría marcada la de antes.
        ss = st.session_state
        k_foco, k_visto, k_ver = ("_mov_merma_prov_foco",
                                  "_mov_merma_prov_visto",
                                  "_mov_merma_prov_ver")
        base_t = f"mov_merma_prov_res_{ss.get(k_ver, 0)}"
        antes = ss.get(k_foco)
        _foco_anterior(base_t, k_foco)
        propio = ss.get(k_foco) if ss.get(k_foco) != antes else None
        comun = ss.get(_K_PROD)
        if propio is not None:
            ss[k_visto] = propio
            if propio != comun:
                ss[_K_PROD] = propio
                _avisar_a(SEC_REND)
        elif comun is not None and comun != ss.get(k_visto):
            ss[k_visto] = comun
            if comun in codigos and comun != ss.get(k_foco):
                ss[k_foco] = comun
                ss[k_ver] = ss.get(k_ver, 0) + 1
                base_t = f"mov_merma_prov_res_{ss[k_ver]}"
        foco = ss.get(k_foco)
        pos = codigos.index(foco) if foco in codigos else 0
        foco = codigos[pos]

        # El proveedor elegido del producto en foco: el clic en la tabla de
        # la derecha o, de entrada, el «Mejor». Se lee ANTES de dibujar.
        x = b[b["cod"] == foco]
        u = unidad_corta(x["unid"].iloc[0]) if len(x) else ""
        t = por_proveedor(x, unico)
        pm = partes_pagado_de_mas(t)
        provs = t.index.tolist()
        k_sel, k_vista, k_de = ("_mov_merma_prov_sel", "_mov_merma_prov_vista",
                                "_mov_merma_prov_de")
        if ss.get(k_de) != (foco, unico, ini):
            ss[k_de] = (foco, unico, ini)
            ss[k_vista], ss[k_sel] = "prov", None
        base_p = f"mov_merma_prov_det_{foco}"
        _foco_anterior(base_p, "_mov_merma_prov_sel_clic")
        clic = ss.pop("_mov_merma_prov_sel_clic", None)
        if clic in provs:
            ss[k_sel] = clic
        sel = ss.get(k_sel)
        if sel not in provs:
            sel = pm["mejor"] if pm else (provs[0] if provs else None)

        # columnas-internas: el resumen entre productos y el detalle del
        # elegido, en la misma tarjeta.
        c_res, c_det = st.columns([1.15, 1], gap="medium")
        with c_res:
            st.markdown('<div style="font-weight:600;font-size:13px">Dónde '
                        'pesa más el proveedor</div>', unsafe_allow_html=True)
            tr = pd.DataFrame({
                "Producto": [nombres.get(c, c) for c in codigos],
                "Pagado de más": r["extra"].tolist(),
                "Mejor": r["mejor"].tolist(),
                "S/ útil": r["util_mejor"].tolist(),
                "Más caro": r["peor"].tolist(),
                "S/ útil ": r["util_peor"].tolist(),
            })
            sty = (tr.style.format({"S/ útil": "{:,.2f}", "S/ útil ": "{:,.2f}",
                                    "Pagado de más": _s})
                   .apply(_resaltar(pos), axis=1))
            _tabla_elegible(
                base_t, sty, codigos, pos,
                _alto_tabla(len(tr), alturas.MERMA_PROV),
                {"Producto": st.column_config.TextColumn(width="medium"),
                 "Mejor": st.column_config.TextColumn(width="small"),
                 "Más caro": st.column_config.TextColumn(width="small"),
                 "Pagado de más": st.column_config.Column(
                     help="Lo pagado de más por lo que se aprovechó, contra "
                          "el mejor proveedor del mismo producto: Σ (costo "
                          "por unidad útil del proveedor − el del mejor) × "
                          "lo que quedó de lo suyo. La cuenta del producto "
                          "elegido, a la derecha.")})
        with c_det:
            sin = int((x["prov"].isna() | (unico & ~x["unico"])).sum())
            if ss.get(k_vista) == "porc" and sel is not None:
                with st.container(horizontal=True, vertical_alignment="center",
                                  gap="small", key="mov_merma_prov_det_cab"):
                    st.button("‹ Proveedores", key="mov_merma_prov_volver",
                              on_click=_ir, args=(k_vista, "prov"))
                    st.markdown(f'<div class="mov-merma-prov-tit">'
                                f'{html.escape(str(nombres.get(foco, foco)))} › '
                                f'{html.escape(str(sel))}</div>',
                                unsafe_allow_html=True)
                st.caption(f"Cada fila va a la última compra hasta "
                           f"{DIAS_PROVEEDOR} días antes: el Almacén no guarda "
                           "de qué compra salió.")
                # Las mismas filas que suma `por_proveedor`.
                xs = x[x["costo_dia"] > 0]
                if unico:
                    xs = xs[xs["unico"]]
                _tabla_rastro(rastro_proveedor(xs, compras, sel), u,
                              t.loc[sel])
                return
            st.markdown(f'<div style="font-weight:600;font-size:13px">'
                        f'{html.escape(str(nombres.get(foco, foco)))}</div>',
                        unsafe_allow_html=True)
            rol = {p: "" for p in provs}
            if pm:
                rol[pm["peor"]] = "más caro"
                rol[pm["mejor"]] = "mejor"
            for p in provs:
                if t.loc[p, "n"] < MIN_PORC_PROVEEDOR:
                    rol[p] = "pocos"
            td = pd.DataFrame({
                "Proveedor": provs,
                "": [rol[p] for p in provs],
                "Porc.": t["n"].astype(int).tolist(),
                "Merma": t["pct"].tolist(),
                f"S/ por {u}": t["pkg"].tolist(),
                f"S/ por {u} útil": t["util"].tolist(),
                "Días": t["dias"].tolist(),
            })
            _u = pd.to_numeric(td[f"S/ por {u} útil"], errors="coerce")
            tope = float(_u.max()) if _u.notna().any() else 1.0
            color_rol = {"mejor": AJUSTE_POS_TEXTO, "más caro": AJUSTE_NEG_TEXTO,
                         "pocos": GRIS_TEXTO, "": TEXTO_PRINCIPAL}
            p_sel = provs.index(sel) if sel in provs else 0
            sty = (td.style.format({"Merma": _p, f"S/ por {u}": "{:,.2f}",
                                    "Días": lambda v: "—" if not np.isfinite(v)
                                    else f"{v:.0f}"})
                   .apply(lambda r: [f"color: {GRIS_TEXTO}"] * len(r)
                          if r[""] == "pocos" else [""] * len(r), axis=1)
                   .map(lambda v: f"color: {color_rol.get(v, TEXTO_PRINCIPAL)}; "
                                  "font-weight: 600", subset=[""])
                   .apply(_resaltar(p_sel), axis=1))
            # Suman la columna a 1323px (~523, con la de la marca): con
            # «medium» en el proveedor, «Días» quedaba afuera.
            _tabla_elegible(
                base_p, sty, provs, p_sel,
                _alto_tabla(len(td), alturas.MERMA_PROV_DET),
                {"Proveedor": st.column_config.TextColumn(width=136),
                 "Porc.": st.column_config.Column(width=44),
                 "Merma": st.column_config.Column(width=50),
                 f"S/ por {u}": st.column_config.Column(width=58),
                 "": st.column_config.TextColumn(
                     width=62,
                     help=f"«Mejor» y «más caro», entre los proveedores con "
                          f"{MIN_PORC_PROVEEDOR} porcionamientos o más: con "
                          f"menos («pocos») no compiten."),
                 f"S/ por {u} útil": st.column_config.ProgressColumn(
                     format="%.2f", min_value=0.0, max_value=tope, width=96),
                 "Días": st.column_config.Column(
                     width=36,
                     help="Mediana de días entre la compra y el "
                          "porcionamiento.")})
            if sel is not None:
                st.markdown(_como_sale(t.loc[sel], sel, u, pm, t, sin,
                                       MIN_PORC_PROVEEDOR),
                            unsafe_allow_html=True)
                n_sel = int(t.loc[sel, "n"])
                st.button(f"Ver sus {n_sel} porcionamiento{'s' if n_sel != 1 else ''} →",
                          key="mov_merma_prov_ver_porc", on_click=_ir,
                          args=(k_vista, "porc"))
