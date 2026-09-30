"""
graficos.recetas_base_costo — Recetas y Costos › «Costo Recetas Base»
(2026-09-30, regla #576).

Reemplaza al «Ranking de recetas base», un gráfico de barras con el COSTO
POR LOTE de cada receta del catálogo: decía cuál cuesta más hacer una vez, y
nada de cuánto se usa ni de cómo se movió su costo. A pedido: «me da muy poca
información… una tabla que me muestre las recetas más usadas dentro de los
platos de venta, cruzadas con las veces que se registran en una orden de
producción, y un histórico de cómo evolucionó el costo por unidad según la
orden de producción», en el tamaño de una tarjeta, que puede alternar, y con
desplegables de una línea.

DOS tarjetas, una debajo de la otra:

    Costo recetas base    la tabla: una fila por receta base — cuántos
                          platos vendidos la llevaron, cuánto usaron (con lo
                          que va ADENTRO de otra receta base), cuántas
                          órdenes de producción la produjeron, cuánto,
                          producido ÷ usado, su último costo por unidad y la
                          línea de sus últimos 12 meses
    <la receta elegida>   lo de la fila elegida, en el mismo lugar según el
                          desplegable «Ver»:
                            Receta        sus ingredientes por una unidad de
                                          entrada; un clic en uno que es
                                          receta base abre la suya AL
                                          COSTADO, proporcionada, y así
                                          hacia adentro
                            Producciones  cada orden con su costo por unidad,
                                          el de cada mes, el de la receta HOY
                                          y sus órdenes

Hasta la segunda versión del mismo día era UNA tarjeta con «Ver: Uso y
producción / Evolución del costo». A pedido («no veo la tabla para ver el
detalle de la receta base… una tarjeta abajo de la tabla principal, que sea
clickeable para mostrar al lado derecho alguna receta anidada, y que se
alterne en su mismo lugar con el historial de producciones»), la evolución
bajó a la tarjeta de abajo como «Producciones».

DE DÓNDE SALE CADA COSA
  · Lo USADO: el primer nivel de las ventas (`paloteoinsumosnivel1.parquet`,
    el SP del POS con la fecha del pedido) — lo que la receta de venta de
    cada plato vendido nombra. Una receta base que va dentro de OTRA no sale
    ahí: se baja por las recetas base activas, un lote por unidad de entrada
    (la regla de `consumo_recetas.py`, regla #558). Medido el 2026-09-30:
    de 427 recetas activas, 257 salen directo en una venta y 95 SÓLO dentro
    de otra (un fondo, un aderezo). Sin bajar, esas 95 decían «sin uso».
  · Lo PRODUCIDO y su costo: `ordenesproduccion.parquet` (el reporte
    Producción del Almacén, regla #575), sólo las órdenes PROCESADAS — una
    generada no movió el kardex. `PRECIO UNIT` es el costo por unidad de
    ENTRADA (kilo, litro, unidad) que el Almacén calculó al procesarla, con
    los precios de ESE día: es la evolución que se pidió. La unidad de la
    orden y la de la receta coinciden en el 100 % (medido).
  · El costo de HOY: `RB COSTO` de recetabase.parquet, la receta con los
    precios de hoy. La mediana de último costo producido ÷ costo de hoy da
    1,00 (498 recetas).

PRODUCIDO ÷ USADO no tiene por qué dar 100 %: la cocina produce por tandas
y guarda stock, algo se pierde, y una receta que además se porciona («(P)»,
«(L)») sale también de porcionamientos, que no son órdenes. Medido en 12
meses: la milanesa de lomo 0,98, la empanada 1,02, el flat bread 1,03; la
papa crocante (P) 0,01.

COSTOS FUERA DE ESCALA. Hay órdenes con un costo por unidad absurdo —el
aderezo de cebolla a S/ 34.239 el kilo, un zumo a S/ 0,008—, casi siempre
una cantidad mal cargada. Una orden es atípica si se separa más de 10 veces
de la mediana de sus vecinas (las 9 órdenes alrededor, `ATIPICO_VECINAS`):
así un CAMBIO de régimen —el choclo blanqueado pasó de S/ 7 a S/ 33 el kilo
en setiembre de 2026— no es atípico después de unas pocas órdenes. Las
atípicas no entran en el promedio del mes ni en el último costo; el gráfico
las muestra aparte y el pie las cuenta.
"""

import hashlib
import math
from functools import partial
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import consumo_recetas
import data
from cortes import MESES_ABR_ES
from graficos import alturas
from graficos.base import _compras_layout
from tema import (ACENTO, ACENTO_TEXTO, ADVERTENCIA, ADVERTENCIA_TEXTO, AJUSTE_POS_TEXTO,
                  GRIS_TEXTO, LAVANDA_FONDO)
from utils import _norm

ARCHIVO_ORDENES = "ordenesproduccion.parquet"
ARCHIVO_N1 = consumo_recetas.ARCHIVOS["paloteo"]

TITULO = "Costo recetas base"
SUBTITULO = ("Lo que usan las ventas de cada receta base, lo que se produjo y "
             "su costo por unidad según las órdenes de producción")

VER_DETALLE = ("Receta", "Producciones")
"""El desplegable de la tarjeta de abajo: la receta elegida en la tabla —sus
ingredientes, con las recetas base de adentro al costado— o su historial de
producciones. Alternan en el mismo lugar."""

VENTANAS = {"Últimos 30 días": 30, "Últimos 90 días": 90,
            "Últimos 6 meses": 182, "Últimos 12 meses": 365}
"""La ventana de lo usado y lo producido. Termina en el último día con venta
del primer nivel (no hoy), como las de la Carta costeada y Revisar recetas.
El primer nivel trae 12 meses: no hay ventana más larga."""

ESTADO_PROCESADO = "PROCESADO"
"""Lo único que suma de una orden (regla #575): GENERADO no produjo nada."""

MESES_LINEA = 12
"""Los meses de la línea «Costo 12 m» de la tabla y de su variación."""

ATIPICO_FACTOR = 10.0
ATIPICO_VECINAS = 9
"""Una orden es atípica si su costo por unidad se separa más de
`ATIPICO_FACTOR` veces de la mediana de las `ATIPICO_VECINAS` órdenes de la
misma receta alrededor suyo (ver el docstring del módulo)."""

UNIDAD_CORTA = {"KILOS": "kg", "LITROS": "L", "UND": "und", "UNIDAD": "und",
                "PORCION": "porc"}

UNIDAD_RECETA = {"GRAMOS": "g", "MILILITROS": "ml", "KILOS": "kg", "LITROS": "L",
                 "UND": "und", "UNIDAD": "und", "ONZAS": "oz", "PORCION": "porc"}
"""La unidad en que la receta pide cada ingrediente (la de SALIDA), corta."""

COBERTURA_BAJA, COBERTURA_ALTA = 0.5, 1.5
"""Producido ÷ usado fuera de este tramo va en ámbar: se produjo mucho menos
de lo que usaron las ventas (o se hace de otra forma), o mucho más."""

VAR_MARCADA = 0.2
"""Desde cuánto se marca «Var. 12 m»: una suba en ámbar, una baja en verde."""

PRODUCCION = ("Todas las recetas", "Con órdenes", "Sin órdenes")
"""El desplegable que separa las recetas que alguna vez produjo una orden de
las que no (casi todas «(L)» y «(P)», que salen de un porcionamiento)."""

_K_VER_DETALLE = "rec_rb_det_ver"
_K_RUTA = "rec_rb_ruta"
"""Las recetas base abiertas al costado de la receta elegida:
`{"raiz", "ruta", "gen", "aviso"}` — `ruta` va de la de afuera a la de más
adentro."""
_K_VENTANA = "rec_rb_ventana"
_K_AREA = "rec_rb_area"
_K_PRODUCCION = "rec_rb_produccion"
_K_BUSCAR = "rec_rb_buscar"
_K_FOCO = "rec_rb_foco"
"""El código de la receta en foco: lo elige la fila de la tabla principal y
lo muestra la tarjeta de abajo."""

COLUMNAS_RB = ("COD PROD RB", "RB NOMBRE", "RB UNID", "RB COSTO", "RB ACT",
               "RB FACTOR", "COD INS RB", "CANT", "FACTOR INS")
COLUMNAS_OP = ("COD ORDEN PRODUCCION", "FECHA REGISTRO", "NOMBRE ESTADO", "AREA",
               "COD PRODUCTO", "NOMBRE PRODUCTO", "CANTIDAD", "UNIDAD", "PRECIO UNIT",
               "VALOR ITEM")
"""Lo que la vista lee de cada parquet. Sin alguna —el modo demo, un
parquet de antes de la regla #558— la tarjeta lo dice en vez de caerse."""

AREA_TODAS = "Todas"

_AREA_ESCRITA = {"PRODUCCION": "Producción", "PASTELERIA": "Pastelería", "FRIOS": "Fríos",
                 "CHARCUTERIA": "Charcutería"}


def area_escrita(a):
    """El área como se lee: «Cocina», «Producción» (el POS la guarda en
    mayúsculas y sin tildes)."""
    return "Todas las áreas" if a == AREA_TODAS else _AREA_ESCRITA.get(a, a.capitalize())


# ===========================================================================
# EL CÁLCULO (puro: DataFrames adentro, DataFrames afuera)
# ===========================================================================

def _txt(s):
    return s.astype("string").fillna("").str.strip()


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def cabeceras(df_rb):
    """Una fila por receta base (índice: su código de PRODUCTO, `COD PROD
    RB`): nombre, unidad de entrada, área, factor de entrada a salida, costo
    de hoy por unidad y si está activa."""
    d = df_rb.assign(_cod=_txt(df_rb["COD PROD RB"]))
    d = d[d["_cod"] != ""].drop_duplicates("_cod").set_index("_cod")
    return pd.DataFrame({
        "nombre": _txt(d["RB NOMBRE"]),
        "unid": _txt(d["RB UNID"]).str.upper(),
        "area": _txt(d["RB AREA PROD"]) if "RB AREA PROD" in d else "",
        "factor": _num(d["RB FACTOR"]) if "RB FACTOR" in d else np.nan,
        "costo_hoy": _num(d["RB COSTO"]).fillna(0.0),
        "activa": _txt(d["RB ACT"]) == consumo_recetas.RECETA_ACTIVA,
    }, index=d.index.rename("cod"))


def aristas(df_rb):
    """Las recetas base que van DENTRO de otra: `padre`, `hijo` y `coef`,
    cuánto del hijo (en SU unidad de entrada) lleva una unidad de entrada del
    padre. Sólo las recetas activas, como `consumo_recetas.calcular`."""
    cab = cabeceras(df_rb)
    d = df_rb[_txt(df_rb["RB ACT"]) == consumo_recetas.RECETA_ACTIVA]
    d = pd.DataFrame({"padre": _txt(d["COD PROD RB"]), "hijo": _txt(d["COD INS RB"]),
                      "cant": _num(d["CANT"]), "fac": _num(d["FACTOR INS"])})
    d = d[d["hijo"].isin(cab.index) & (d["padre"] != d["hijo"])]
    d = d.assign(coef=d["cant"] / d["fac"].where(d["fac"] > 0))
    return (d.dropna(subset=["coef"]).groupby(["padre", "hijo"], as_index=False)["coef"]
            .sum())


def uso(n1, df_rb, niveles=consumo_recetas.NIVELES_MAX):
    """Lo que usaron las ventas de cada receta base, directo en el plato y
    dentro de otras recetas base.

    `n1` es lo que devuelve `data.demanda_nivel1_rango` (cod, plato, consumo
    en unidad de SALIDA, vendido). Devuelve, por código de receta: `usado` (en
    su unidad de ENTRADA, sumando todos los caminos), `directo` (la parte que
    nombra la receta del plato), `platos` (cuántos platos distintos la
    llevaron) y `vendidos` (cuántas unidades de esos platos: un plato que la
    lleva por dos caminos cuenta una vez)."""
    cab = cabeceras(df_rb)
    vacio = pd.DataFrame(columns=["usado", "directo", "platos", "vendidos"],
                         index=pd.Index([], name="cod"), dtype=float)
    if n1 is None or n1.empty:
        return vacio
    d = pd.DataFrame({"cod": _txt(n1["cod"]), "plato": _txt(n1["plato"]),
                      "consumo": _num(n1["consumo"]).fillna(0.0),
                      "vendido": _num(n1["vendido"]).fillna(0.0)})
    d = d[d["cod"].isin(cab.index)]
    if d.empty:
        return vacio
    fac = d["cod"].map(cab["factor"])
    d = d.assign(q=d["consumo"] / fac.where(fac > 0))
    ar = aristas(df_rb)

    # LA CANTIDAD baja multiplicando: un kilo de salsa lleva 0,2 kg de fondo.
    directo = d.groupby("cod")["q"].sum(min_count=1)
    total = directo.fillna(0.0)
    frente = total[total > 0]
    for _ in range(niveles):
        j = ar.merge(frente.rename("d"), left_on="padre", right_index=True)
        if j.empty:
            break
        frente = (j["d"] * j["coef"]).groupby(j["hijo"]).sum()
        frente = frente[frente > 1e-12]
        total = total.add(frente, fill_value=0.0)

    # LOS PLATOS bajan sin multiplicar: un plato que lleva la salsa lleva
    # también su fondo. Un par (plato, receta) se cuenta una vez aunque
    # llegue por dos caminos — y así tampoco da vueltas en un círculo.
    todos = d.groupby(["plato", "cod"], as_index=False)["vendido"].sum()
    frente = todos
    for _ in range(niveles):
        j = frente.merge(ar[["padre", "hijo"]], left_on="cod", right_on="padre")
        if j.empty:
            break
        nuevos = (j.assign(cod=j["hijo"]).groupby(["plato", "cod"], as_index=False)
                  ["vendido"].max())
        nuevos = nuevos.merge(todos[["plato", "cod"]], how="left", indicator=True)
        nuevos = nuevos[nuevos["_merge"] == "left_only"].drop(columns="_merge")
        if nuevos.empty:
            break
        todos = pd.concat([todos, nuevos], ignore_index=True)
        frente = nuevos
    platos = todos.groupby("cod").agg(platos=("plato", "nunique"),
                                      vendidos=("vendido", "sum"))
    out = pd.DataFrame({"usado": total, "directo": directo}).join(platos, how="outer")
    out.index.name = "cod"
    return out.fillna({"usado": 0.0, "directo": 0.0, "platos": 0, "vendidos": 0.0})


def ordenes(df_op):
    """Las líneas de las órdenes PROCESADAS, con nombres propios, ordenadas
    por fecha, y la marca `atipico` (ver el docstring del módulo)."""
    d = df_op[_txt(df_op["NOMBRE ESTADO"]).str.upper() == ESTADO_PROCESADO]
    d = pd.DataFrame({
        "cod": _txt(d["COD PRODUCTO"]),
        "fecha": pd.to_datetime(d["FECHA REGISTRO"], errors="coerce"),
        "orden": _txt(d["COD ORDEN PRODUCCION"]),
        "nombre": _txt(d["NOMBRE PRODUCTO"]),
        "area": _txt(d["AREA"]),
        "cant": _num(d["CANTIDAD"]).fillna(0.0),
        "unid": _txt(d["UNIDAD"]).str.upper(),
        "punit": _num(d["PRECIO UNIT"]),
        "valor": _num(d["VALOR ITEM"]).fillna(0.0),
    })
    d = d.dropna(subset=["fecha"])
    d = d[d["cod"] != ""]
    # Orden ESTABLE: dos órdenes del mismo minuto quedan como vinieron.
    d = d.sort_values(["cod", "fecha", "orden"], kind="stable").reset_index(drop=True)
    # UN rolling agrupado sobre todas las filas, y no un `transform` con una
    # función por receta: son ~500 recetas y cada llamada paga lo fijo de
    # pandas (regla #537).
    vecinas = (d.groupby("cod", sort=False)["punit"]
               .rolling(ATIPICO_VECINAS, center=True, min_periods=1).median()
               .reset_index(level=0, drop=True).reindex(d.index))
    p = d["punit"]
    d["atipico"] = (p.isna() | (p <= 0)
                    | ((vecinas > 0) & ((p > vecinas * ATIPICO_FACTOR)
                                        | (p < vecinas / ATIPICO_FACTOR))))
    return d


def produccion(ords, ini, fin):
    """Por receta: cuántas órdenes la produjeron entre `ini` y `fin` (fechas,
    inclusive, sobre la fecha de REGISTRO, como el reporte del Almacén) y
    cuánto, en su unidad de entrada."""
    t = ords[(ords["fecha"] >= pd.Timestamp(ini))
             & (ords["fecha"] < pd.Timestamp(fin) + pd.Timedelta(days=1))]
    return t.groupby("cod").agg(ordenes=("orden", "nunique"), producido=("cant", "sum"))


def costo_por_mes(ords):
    """El costo por unidad de cada receta, mes a mes: lo que costó lo
    producido ese mes ÷ lo producido, sin las órdenes atípicas. Columnas
    cod, mes, costo, n (órdenes)."""
    t = ords[~ords["atipico"] & (ords["cant"] > 0)]
    t = t.assign(mes=t["fecha"].dt.to_period("M").dt.to_timestamp())
    g = t.groupby(["cod", "mes"], as_index=False).agg(
        valor=("valor", "sum"), cant=("cant", "sum"), n=("orden", "nunique"))
    return g.assign(costo=g["valor"] / g["cant"])[["cod", "mes", "costo", "n"]]


def ultimos_costos(ords, hasta):
    """Por receta, hasta `hasta` (inclusive): el costo por unidad de la última
    orden no atípica y su fecha, la línea de los últimos `MESES_LINEA` meses
    (una lista con los meses que tuvieron órdenes) y su variación, del primer
    mes de la línea al último."""
    fin = pd.Timestamp(hasta) + pd.Timedelta(days=1)
    t = ords[(ords["fecha"] < fin) & ~ords["atipico"]]
    ult = t.groupby("cod").last()[["punit", "fecha"]].rename(
        columns={"punit": "ultimo", "fecha": "f_ultimo"})
    desde = (pd.Timestamp(hasta).to_period("M") - (MESES_LINEA - 1)).to_timestamp()
    m = costo_por_mes(t)
    m = m[m["mes"] >= desde].sort_values(["cod", "mes"])
    linea = m.groupby("cod")["costo"].agg(list).rename("linea")
    extremos = m.groupby("cod")["costo"].agg(["first", "last", "size"])
    var = (extremos["last"] / extremos["first"] - 1).where(
        (extremos["size"] >= 2) & (extremos["first"] > 0)).rename("var")
    return ult.join(linea, how="outer").join(var, how="left")


def tabla(df_rb, n1, ords, ini, fin):
    """Lo que dibuja «Uso y producción»: una fila por receta base activa, y
    también por una inactiva que se usó o produjo en el período. Ordenada por
    lo vendido que la llevó y, a igual venta, por órdenes. `ords` es lo que
    devuelve `ordenes()`. Sin vacíos (un
    vacío se pinta «None» en `st.dataframe`, regla #529): lo que no hay va
    en 0 —o en infinito donde 0 sería un dato— y el formato lo escribe «—»."""
    cab = cabeceras(df_rb)
    u = uso(n1, df_rb)
    p = produccion(ords, ini, fin)
    c = ultimos_costos(ords, fin)
    t = cab.join(u, how="outer").join(p, how="outer").join(c, how="left")
    t.index.name = "cod"
    t["activa"] = t["activa"].fillna(False).astype(bool)
    for col in ("usado", "directo", "platos", "vendidos", "ordenes", "producido",
                "ultimo", "costo_hoy"):
        t[col] = t[col].fillna(0.0)
    t = t[t["activa"] | (t["usado"] > 0) | (t["ordenes"] > 0)]
    # Un código que produjo una orden y ya no está en las recetas: su nombre
    # y su unidad, de la orden.
    de_orden = ords.drop_duplicates("cod", keep="last").set_index("cod")
    sin_nombre = t["nombre"].isna() | (t["nombre"] == "")
    t.loc[sin_nombre, "nombre"] = de_orden["nombre"].reindex(t.index[sin_nombre])
    sin_unid = t["unid"].isna() | (t["unid"] == "")
    t.loc[sin_unid, "unid"] = de_orden["unid"].reindex(t.index[sin_unid])
    t["nombre"] = t["nombre"].fillna("").astype(str)
    t["area"] = t["area"].fillna("").astype(str)
    t["unid"] = t["unid"].fillna("").astype(str)
    # «Con órdenes»: alguna vez, hasta el fin del período, la produjo una
    # orden. Sin ninguna —casi todas las «(L)» y «(P)», que salen de un
    # porcionamiento—, producido ÷ usado no es un 0 %: no se hace así. Va en
    # infinito, que se escribe «—».
    hasta = pd.Timestamp(fin) + pd.Timedelta(days=1)
    t["con_ordenes"] = t.index.isin(set(ords.loc[ords["fecha"] < hasta, "cod"]))
    t["cobertura"] = np.where(t["con_ordenes"] & (t["usado"] > 0),
                              t["producido"] / t["usado"].where(t["usado"] > 0), np.inf)
    t["var"] = t["var"].fillna(np.inf)
    # Una línea de un solo mes se dibuja plana contra el piso de la celda y
    # parece un costo que no se movió: con menos de dos meses, sin línea.
    t["linea"] = [v if isinstance(v, list) and len(v) >= 2 else [] for v in t["linea"]]
    t = t.sort_values(["vendidos", "ordenes", "nombre"], ascending=[False, False, True],
                      kind="stable")
    return t.reset_index()


def filtrar(t, area=AREA_TODAS, buscar="", produccion=None):
    """Las filas del área elegida, con o sin órdenes de producción
    (`PRODUCCION`) y cuyo nombre contiene `buscar` (sin acentos, mayúsculas
    ni espacios)."""
    if area and area != AREA_TODAS:
        t = t[t["area"] == area]
    if produccion == PRODUCCION[1]:
        t = t[t["con_ordenes"]]
    elif produccion == PRODUCCION[2]:
        t = t[~t["con_ordenes"]]
    if buscar and buscar.strip():
        q = _norm(buscar)
        t = t[[q in _norm(n) for n in t["nombre"]]]
    return t


def codigos_base(df_rb):
    """Los códigos de producto que tienen receta base."""
    return frozenset(cabeceras(df_rb).index)


def ingredientes(df_rb, cod, escala=1.0, bases=frozenset()):
    """Los ingredientes de la receta base del producto `cod`, proporcionados a
    `escala` unidades de entrada de ella: Cod, Insumo, Cantidad y Unid (en la
    unidad de la receta: gramos, mililitros), Costo, %, Factor (a la unidad
    de entrada del ingrediente) y EsBase (si el ingrediente tiene a su vez
    receta base). Ordenados por costo."""
    cols = ["Cod", "Insumo", "Cantidad", "Unid", "Costo", "%", "Factor", "EsBase"]
    d = df_rb[_txt(df_rb["COD PROD RB"]) == str(cod).strip()]
    d = d[d["COD INS RB"].notna()]
    if d.empty:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame({
        "Cod": _txt(d["COD INS RB"]),
        "Insumo": _txt(d["INSUMO"]) if "INSUMO" in d else _txt(d["COD INS RB"]),
        "Cantidad": _num(d["CANT"]).fillna(0.0) * escala,
        "Unid": ([UNIDAD_RECETA.get(u, u.lower()) for u in _txt(d["UNID"]).str.upper()]
                 if "UNID" in d else ""),
        "Costo": (_num(d["CST SUBT INS"]).fillna(0.0) * escala if "CST SUBT INS" in d
                  else 0.0),
        "Factor": _num(d["FACTOR INS"]).fillna(0.0),
    })
    total = out["Costo"].sum() or 1.0
    out["%"] = out["Costo"] / total * 100
    out["EsBase"] = out["Cod"].isin(bases) & (out["Cod"] != str(cod).strip())
    return out.sort_values("Costo", ascending=False, kind="stable").reset_index(drop=True)[cols]


COLUMNAS = ("Receta base", "Unid.", "Platos", "Vendidos", "Usado", "Órdenes",
            "Producido", "Prod. ÷ uso", "Último costo", "Var. 12 m", "Costo 12 m")
"""Las columnas de la tabla, en orden; `columnas_tabla` las arma."""


def columnas_tabla(t):
    """El DataFrame que se muestra, con las columnas de `COLUMNAS`."""
    nombre = [n if a else f"{n} · inactiva" for n, a in zip(t["nombre"], t["activa"])]
    return pd.DataFrame({
        "Receta base": nombre,
        "Unid.": [UNIDAD_CORTA.get(u, u.lower()) for u in t["unid"]],
        "Platos": t["platos"].astype(int),
        "Vendidos": t["vendidos"],
        "Usado": t["usado"],
        "Órdenes": t["ordenes"].astype(int),
        "Producido": t["producido"],
        "Prod. ÷ uso": t["cobertura"],
        "Último costo": t["ultimo"],
        "Var. 12 m": t["var"],
        "Costo 12 m": t["linea"],
    })


# ─── Formatos ──────────────────────────────────────────────────────────────
def _cant(v):
    if not v or not math.isfinite(v):
        return "—"
    return f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.1f}" if abs(v) >= 10 else f"{v:,.2f}"


def _entero(v):
    return f"{v:,.0f}" if v else "—"


def _soles(v):
    if not v or not math.isfinite(v):
        return "—"
    return f"S/ {v:,.2f}" if v < 1000 else f"S/ {v:,.0f}"


def _pct(v):
    if not math.isfinite(v):
        return "—"
    return f"{v * 100:,.0f} %"


def _var(v):
    if not math.isfinite(v):
        return "—"
    return f"{'+' if v >= 0 else '−'}{abs(v) * 100:,.0f} %"


def _estilo_cobertura(v):
    if math.isfinite(v) and not (COBERTURA_BAJA <= v <= COBERTURA_ALTA):
        return f"color: {ADVERTENCIA_TEXTO}; font-weight: 600"
    return ""


def _estilo_var(v):
    """Una suba de `VAR_MARCADA` o más en ámbar, una baja igual en verde:
    como en Compras, subir es gastar más."""
    if math.isfinite(v) and v >= VAR_MARCADA:
        return f"color: {ADVERTENCIA_TEXTO}; font-weight: 600"
    if math.isfinite(v) and v <= -VAR_MARCADA:
        return f"color: {AJUSTE_POS_TEXTO}; font-weight: 600"
    return ""


def etiqueta_mes(ts):
    return f"{MESES_ABR_ES[ts.month - 1]} {ts.year % 100:02d}"


# ===========================================================================
# LA TARJETA
# ===========================================================================

def faltan(df, columnas):
    """Las `columnas` que `df` no trae."""
    return [c for c in columnas if c not in df.columns]


@st.cache_data(ttl=3600, max_entries=8, show_spinner=False)
def _calculo(sellos, ini, fin, _df_rb, _n1, _df_op):
    """`tabla` y `ordenes`, una vez por versión de los tres parquets y por
    ventana: cada clic en la tabla re-ejecuta la sección, y la cuenta son
    ~0,7 s en la laptop. La clave son los SELLOS de los parquets (`sellos`) y
    la ventana; los DataFrames van con `_` delante, fuera de la clave:
    hashearlos en cada clic costaría casi lo que ahorra la caché. En memoria,
    sin `persist="disk"` (regla #367)."""
    ords = ordenes(_df_op)
    return tabla(_df_rb, _n1, ords, ini, fin), ords


def _key(base, codigos):
    """La key de una tabla con la firma de su lista de filas: la selección de
    un `st.dataframe` es de la KEY y no de sus filas —con otro filtro, la
    fila elegida sería otra receta— (regla #556)."""
    firma = hashlib.md5("|".join(codigos).encode("utf-8")).hexdigest()[:12]
    return f"{base}_{firma}"


def _fila_elegida(evt):
    try:
        sel = evt.get("selection", {}) if isinstance(evt, dict) else getattr(evt, "selection", {})
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _leer_eleccion():
    """La receta que la tabla principal tenía elegida en la corrida anterior,
    al foco. Se lee ANTES de dibujar: la tabla nueva sale con ella marcada, y
    la tarjeta de abajo la muestra."""
    ss = st.session_state
    key = ss.get("_rec_rb_tabla_key")
    codigos = ss.get("_rec_rb_tabla_codigos") or []
    fila = _fila_elegida(ss.get(key)) if key else None
    if fila is not None and 0 <= fila < len(codigos):
        ss[_K_FOCO] = codigos[fila]


def _pintar_foco(pos):
    def _fila(r):
        return [f"background-color: {LAVANDA_FONDO}" if r.name == pos else ""] * len(r)
    return _fila


def _dib_tabla(t, ini, fin):
    ss = st.session_state
    codigos = list(t["cod"])
    foco = ss.get(_K_FOCO)
    pos = codigos.index(foco) if foco in codigos else 0
    ss[_K_FOCO] = codigos[pos]
    v = columnas_tabla(t)
    sty = (v.style
           .format(_cant, subset=["Vendidos", "Usado", "Producido"])
           .format(_entero, subset=["Platos", "Órdenes"])
           .format(_pct, subset=["Prod. ÷ uso"])
           .format(_soles, subset=["Último costo"])
           .format(_var, subset=["Var. 12 m"])
           .map(_estilo_cobertura, subset=["Prod. ÷ uso"])
           .map(_estilo_var, subset=["Var. 12 m"])
           .apply(_pintar_foco(pos), axis=1))
    periodo = f"del {ini:%d/%m} al {fin:%d/%m/%Y}"
    cfg = {
        "Receta base": st.column_config.TextColumn(pinned=True, width=250),
        "Unid.": st.column_config.TextColumn(
            width=44, help="La unidad de ENTRADA de la receta —la del kardex y la "
                           "de la orden de producción—: «Usado» y «Producido» van en ella"),
        "Platos": st.column_config.Column(
            width=56, help=f"Cuántos platos distintos vendidos {periodo} la llevaron, "
                           "directo o dentro de otra receta base"),
        "Vendidos": st.column_config.Column(
            width=74, help=f"Unidades vendidas {periodo} de esos platos"),
        "Usado": st.column_config.Column(
            width=74, help="Lo que usaron esas ventas según las recetas de HOY, "
                           "sumando lo que va dentro de otras recetas base"),
        "Órdenes": st.column_config.Column(
            width=64, help=f"Órdenes de producción PROCESADAS {periodo} que la "
                           "produjeron (las generadas no produjeron nada)"),
        "Producido": st.column_config.Column(width=78, help="Lo que produjeron esas órdenes"),
        "Prod. ÷ uso": st.column_config.Column(
            width=80, help="Producido ÷ usado. En ámbar, debajo de 50 % o arriba de "
                           "150 %: se produce poco para lo que se vende (o se hace de "
                           "otra forma, como un porcionamiento) o mucho más"),
        "Último costo": st.column_config.Column(
            width=86, help="Costo por unidad de la última orden de producción, con "
                           "los precios de ese día"),
        "Var. 12 m": st.column_config.Column(
            width=70, help="Cuánto cambió el costo por unidad del primer al último "
                           "mes con órdenes de los últimos 12. Una suba de 20 % o más, "
                           "en ámbar; una baja igual, en verde"),
        "Costo 12 m": st.column_config.LineChartColumn(
            width=110, help="El costo por unidad de cada mes con órdenes, últimos 12 "
                            "meses. «Producciones», en la tarjeta de abajo, lo abre entero"),
    }
    key = _key("rec_rb_tabla", codigos)
    ss["_rec_rb_tabla_key"] = key
    ss["_rec_rb_tabla_codigos"] = codigos
    st.dataframe(sty, key=key, on_select="rerun", selection_mode="single-row-required",
                 selection_default={"selection": {"rows": [pos]}},
                 hide_index=True, row_height=27, column_config=cfg,
                 height=alturas.por_filas(len(v), px_fila=27, extra=38, minimo=0,
                                          rol=alturas.RB_COSTO_TABLA))


def fig_evolucion(o, meses, costo_hoy, unid, alto=alturas.RB_COSTO_DETALLE):
    """El costo por unidad de UNA receta en el tiempo: un punto por orden,
    la línea del costo de cada mes y, punteado, el de la receta hoy. Las
    órdenes atípicas van como triángulos contra el borde de arriba (si se
    pasan) o en su valor (si quedan debajo), sin estirar la escala."""
    u = UNIDAD_CORTA.get(unid, unid.lower()) or "unidad"
    normales = o[~o["atipico"]]
    raras = o[o["atipico"]]
    tope_datos = [normales["punit"].max() if not normales.empty else 0.0,
                  meses["costo"].max() if not meses.empty else 0.0, costo_hoy or 0.0]
    tope = float(np.nanmax(tope_datos)) * 1.12 or 1.0

    def _hover(r):
        costo = (f"S/ {r['punit']:,.2f} por {u}" if math.isfinite(r["punit"])
                 else "sin costo")
        return (f"<b>{r['fecha']:%d/%m/%Y}</b> · orden {r['orden']}<br>"
                f"{_cant(r['cant'])} {u} · {costo}<br>{area_escrita(r['area'])}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=normales["fecha"], y=normales["punit"], mode="markers", name="Orden",
        marker=dict(size=6, color=ACENTO, opacity=0.35),
        text=[_hover(r) for _, r in normales.iterrows()],
        hovertemplate="%{text}<extra></extra>"))
    if not meses.empty:
        # El punto del mes, a mitad de mes: sobre el día 1 caería antes de
        # las órdenes de las que sale.
        fig.add_trace(go.Scatter(
            x=meses["mes"] + pd.Timedelta(days=14), y=meses["costo"], mode="lines+markers",
            name="Costo del mes", line=dict(color=ACENTO_TEXTO, width=2),
            marker=dict(size=5, color=ACENTO_TEXTO),
            text=[f"<b>{etiqueta_mes(m)}</b><br>S/ {c:,.2f} por {u}<br>"
                  f"{n} {'orden' if n == 1 else 'órdenes'}"
                  for m, c, n in zip(meses["mes"], meses["costo"], meses["n"])],
            hovertemplate="%{text}<extra></extra>"))
    if not raras.empty:
        arriba = raras["punit"].fillna(0) > tope
        fig.add_trace(go.Scatter(
            x=raras["fecha"], y=np.where(arriba, tope * 0.985, raras["punit"].fillna(0)),
            mode="markers", name="Fuera de escala",
            marker=dict(symbol=np.where(arriba, "triangle-up", "x-thin"), size=9,
                        color=ADVERTENCIA, line=dict(width=2, color=ADVERTENCIA)),
            text=[_hover(r) + "<br><i>fuera de escala: no entra en el costo del mes</i>"
                  for _, r in raras.iterrows()],
            hovertemplate="%{text}<extra></extra>"))
    if costo_hoy:
        fig.add_hline(y=float(costo_hoy), line=dict(color=GRIS_TEXTO, width=1, dash="dot"),
                      annotation_text=f"receta hoy S/ {costo_hoy:,.2f}",
                      annotation_position="top left",
                      annotation_font=dict(size=10, color=GRIS_TEXTO))
    _compras_layout(fig, alto=alto)
    # Meses en español (regla #241): los ticks los arma Python, uno cada
    # tantos meses para que no se pisen.
    ini = o["fecha"].min().to_period("M").to_timestamp()
    fin = o["fecha"].max().to_period("M").to_timestamp()
    todos = pd.date_range(ini, fin, freq="MS")
    paso = max(1, math.ceil(len(todos) / 8))
    ticks = list(todos[::paso])
    fig.update_layout(showlegend=False, margin=dict(l=6, r=10, t=18, b=6))
    fig.update_xaxes(type="date", tickvals=ticks, ticktext=[etiqueta_mes(t) for t in ticks],
                     tickfont=dict(size=10), fixedrange=True,
                     range=[ini - pd.Timedelta(days=12), fin + pd.Timedelta(days=45)])
    fig.update_yaxes(showticklabels=True, tickprefix="S/ ", range=[0, tope],
                     tickformat=",.2f" if tope < 20 else ",.0f",
                     tickfont=dict(size=10), automargin=True, fixedrange=True)
    return fig


# ─── La tarjeta de abajo: la receta elegida ────────────────────────────────
def resumen_producciones(fila, o):
    """(info, ayuda) de «Producciones»: la línea de números que va en la
    cabecera de la tarjeta y lo que explica el gráfico, que aparece al pasar
    el cursor por el nombre (a pedido: la tarjeta entera en una pantalla)."""
    u = UNIDAD_CORTA.get(fila["unid"], fila["unid"].lower()) or "unidad"
    partes = []
    if fila["ultimo"]:
        partes.append(f"Último S/ {fila['ultimo']:,.2f} por {u} ({fila['f_ultimo']:%d/%m/%y})")
    if fila["costo_hoy"]:
        partes.append(f"receta hoy S/ {fila['costo_hoy']:,.2f}")
    if math.isfinite(fila["var"]):
        partes.append(f"12 m {_var(fila['var'])}")
    if not o.empty:
        partes.append(f"{o['orden'].nunique():,} órdenes desde {o['fecha'].min():%m/%Y}")
    ayuda = ("Un punto por orden de producción procesada: el costo por unidad que calculó "
             "el Almacén al procesarla, con los precios de ese día. La línea es el costo de "
             "cada mes (lo que costó lo producido ÷ lo producido); la punteada, la receta "
             "con los precios de hoy.")
    n_raras = int(o["atipico"].sum()) if not o.empty else 0
    if n_raras:
        ayuda += (f" {n_raras} {'orden fuera' if n_raras == 1 else 'órdenes fuera'} de "
                  "escala (más de 10 veces sobre o bajo sus vecinas, casi siempre una "
                  "cantidad mal cargada): en ámbar, y no entran en el costo del mes.")
    return " · ".join(partes), ayuda


def _dib_producciones(fila, o):
    """El historial de producciones de la receta elegida: su costo por unidad
    orden a orden y mes a mes, y sus órdenes al costado."""
    cod = fila["cod"]
    if o.empty:
        st.info("Esta receta base nunca se produjo con una orden de producción: si se "
                "usa, sale de un porcionamiento o no se registra.")
        return
    u = UNIDAD_CORTA.get(fila["unid"], fila["unid"].lower()) or "unidad"
    meses = costo_por_mes(o)
    # columnas-internas: el gráfico y, al costado, sus órdenes; es la
    # tarjeta de la receta, no parte la página.
    c_fig, c_ord = st.columns([0.62, 0.38], gap="medium")
    with c_fig:
        st.plotly_chart(fig_evolucion(o, meses, fila["costo_hoy"], fila["unid"],
                                      alto=alturas.RB_COSTO_DETALLE),
                        use_container_width=True, key=f"rec_rb_evo_{cod}",
                        config={"displaylogo": False, "displayModeBar": False})
    with c_ord:
        v = o.sort_values("fecha", ascending=False, kind="stable")
        v = pd.DataFrame({"Fecha": v["fecha"].dt.strftime("%d/%m/%Y"),
                          "Área": [area_escrita(a) for a in v["area"]],
                          f"Cant. ({u})": v["cant"], f"S/ por {u}": v["punit"].fillna(0.0),
                          "Valor": v["valor"], "_rara": v["atipico"]})

        def _marca(r):
            return [f"color: {ADVERTENCIA_TEXTO}" if r["_rara"] else ""] * len(r)

        sty = (v.style.format(_cant, subset=[f"Cant. ({u})"])
               .format(_soles, subset=[f"S/ por {u}", "Valor"])
               .apply(_marca, axis=1))
        st.dataframe(sty, hide_index=True, row_height=27,
                     column_order=[c for c in v.columns if c != "_rara"],
                     column_config={"Fecha": st.column_config.TextColumn(width=78),
                                    "Área": st.column_config.TextColumn(width=86)},
                     height=alturas.por_filas(len(v), px_fila=27, extra=38, minimo=0,
                                              rol=alturas.RB_COSTO_DETALLE))


_CFG_INGREDIENTES = {
    "Insumo": st.column_config.TextColumn(
        width=230, help="▸ receta base: clic en la fila para ver la suya al costado"),
    "Cantidad": st.column_config.TextColumn(width=86),
    "Costo": st.column_config.NumberColumn(format="S/ %.2f", width=74),
    "%": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100,
                                         width=90),
}


def _filas_clic(r):
    """Lo que un clic en una fila de ingredientes necesita saber: si abre (es
    receta base) y a cuánto se proporciona su receta (su cantidad ÷ el factor
    a su unidad de entrada: 300 g ÷ 1.000 = 0,3 kg)."""
    return [{"cod": c, "nombre": n, "costo": float(co), "es_base": bool(b),
             "escala": float(q) / float(f) if f and f > 0 else float(q)}
            for c, n, q, f, co, b in zip(r["Cod"], r["Insumo"], r["Cantidad"], r["Factor"],
                                          r["Costo"], r["EsBase"])]


def _estado_ruta(raiz):
    """Las recetas base abiertas al costado, PARA ESTA receta elegida: si la
    de arriba cambió, se vacía."""
    ss = st.session_state
    e = ss.get(_K_RUTA) or {}
    if e.get("raiz") != raiz:
        e = {"raiz": raiz, "ruta": [], "gen": e.get("gen", 0)}
        ss[_K_RUTA] = e
    return e


def _al_elegir_ingrediente(key, raiz, filas):
    """Clic en la receta de la izquierda: abre al costado la receta base de esa
    fila, o avisa que es un insumo de compra."""
    fila = _fila_elegida(st.session_state.get(key))
    e = _estado_ruta(raiz)
    nuevo = {"raiz": raiz, "ruta": [], "gen": e.get("gen", 0)}
    if fila is not None and 0 <= fila < len(filas):
        if filas[fila]["es_base"]:
            nuevo["ruta"] = [filas[fila]]
        else:
            nuevo["aviso"] = filas[fila]["nombre"]
    st.session_state[_K_RUTA] = nuevo


def _al_elegir_anidada(key, raiz, ruta, filas):
    """Clic en la receta del costado: si esa fila también es receta base, se
    abre ella, un nivel más adentro."""
    fila = _fila_elegida(st.session_state.get(key))
    if fila is not None and 0 <= fila < len(filas) and filas[fila]["es_base"]:
        e = _estado_ruta(raiz)
        st.session_state[_K_RUTA] = {"raiz": raiz, "ruta": ruta + [filas[fila]],
                                     "gen": e.get("gen", 0)}


def _subir(raiz):
    e = _estado_ruta(raiz)
    st.session_state[_K_RUTA] = {"raiz": raiz, "ruta": list(e["ruta"])[:-1],
                                 "gen": e.get("gen", 0)}


def _cerrar(raiz):
    """«✕»: cierra lo de la derecha y estrena la tabla de la izquierda (una
    tabla sin el foco se come el primer clic sobre una fila ya marcada,
    regla #572)."""
    e = _estado_ruta(raiz)
    st.session_state[_K_RUTA] = {"raiz": raiz, "ruta": [], "gen": e.get("gen", 0) + 1}


def _tabla_ingredientes(r, key, on_select, rol=alturas.RB_COSTO_DETALLE):
    v = pd.DataFrame({
        "Insumo": np.where(r["EsBase"], "▸ " + r["Insumo"], r["Insumo"]),
        "Cantidad": [f"{_cant(q)} {u}".strip() for q, u in zip(r["Cantidad"], r["Unid"])],
        "Costo": r["Costo"],
        "%": r["%"],
    })
    st.dataframe(v, key=key, on_select=on_select, selection_mode="single-row",
                 hide_index=True, row_height=27, column_config=_CFG_INGREDIENTES,
                 height=alturas.por_filas(len(v), px_fila=27, extra=38, minimo=0, rol=rol))


def _dib_receta(fila, df_rb, bases):
    """La receta elegida, por UNA unidad de entrada (un kilo, un litro), a la
    izquierda; y al costado, la receta base de un ingrediente que se elija,
    proporcionada a lo que lleva esa unidad — y así hacia adentro."""
    raiz = fila["cod"]
    u = UNIDAD_CORTA.get(fila["unid"], fila["unid"].lower()) or "unidad"
    r = ingredientes(df_rb, raiz, 1.0, bases)
    e = _estado_ruta(raiz)
    # columnas-internas: la receta y, al costado, la receta base que se abra
    # de adentro de ella; es la tarjeta de la receta, no parte la página.
    c_izq, c_der = st.columns(2, gap="medium")
    with c_izq:
        if r.empty:
            st.info("Esta receta base no tiene ingredientes cargados.")
            return
        filas = _filas_clic(r)
        key = _key(f"rec_rb_ing_{raiz}_{e.get('gen', 0)}",
                   [f"{x['cod']}:{x['nombre']}" for x in filas])
        _tabla_ingredientes(r, key, partial(_al_elegir_ingrediente, key, raiz, filas))
    with c_der:
        e = _estado_ruta(raiz)
        if not e.get("ruta"):
            if e.get("aviso"):
                st.caption(f"«{e['aviso']}» es un insumo de compra: no tiene receta base.")
            elif r["EsBase"].any():
                n = int(r["EsBase"].sum())
                st.caption(f"Lleva {n} {'receta base' if n == 1 else 'recetas base'} "
                           "adentro (▸). Elegí una a la izquierda para ver la suya acá.")
            else:
                st.caption("No lleva otras recetas base: todo lo que usa se compra o "
                           "se porciona.")
            return
        ruta = e["ruta"]
        actual = ruta[-1]
        with st.container(horizontal=True, vertical_alignment="center",
                          key="rec_rb_anidada_hdr"):
            migas = " › ".join([fila["nombre"]] + [x["nombre"] for x in ruta])
            # El total va en el renglón del nombre y no en un pie: la
            # tarjeta entera tiene que entrar en una pantalla.
            st.markdown(f'<p class="rec-base-tit" title="{escape(migas)}">'
                        f'{escape(actual["nombre"])} <span class="rec-rb-anid-tot">· en 1 '
                        f'{u}: S/ {actual["costo"]:,.2f}</span></p>', unsafe_allow_html=True)
            if len(ruta) > 1:
                st.button("↑ Subir", key="rec_rb_anidada_subir", on_click=_subir,
                          args=(raiz,))
            st.button("✕", key="rec_rb_anidada_cerrar", on_click=_cerrar, args=(raiz,))
        rr = ingredientes(df_rb, actual["cod"], actual["escala"], bases)
        if rr.empty:
            st.info("La receta base no tiene ingredientes cargados.")
            return
        filas2 = _filas_clic(rr)
        key2 = _key(f"rec_rb_anid_{raiz}_" + "-".join(x["cod"] for x in ruta),
                    [f"{x['cod']}:{x['nombre']}" for x in filas2])
        # Una fila menos que la de la izquierda: el renglón del nombre ocupa
        # su lugar y las dos columnas terminan a la misma altura.
        _tabla_ingredientes(rr, key2, partial(_al_elegir_anidada, key2, raiz, ruta, filas2),
                            rol=alturas.RB_COSTO_DETALLE - 27)


def _tarjeta_receta(fila, df_rb, ords):
    """La tarjeta de abajo: la receta elegida en la tabla, con su receta o
    su historial de producciones —en el mismo lugar, que alterna el
    desplegable «Ver»—."""
    ss = st.session_state
    if ss.get(_K_VER_DETALLE) not in VER_DETALLE:
        ss[_K_VER_DETALLE] = VER_DETALLE[0]
    ver = ss[_K_VER_DETALLE]
    bases = codigos_base(df_rb)
    o = ords[ords["cod"] == fila["cod"]]
    if ver == VER_DETALLE[0]:
        info, ayuda = resumen_receta(fila, ingredientes(df_rb, fila["cod"], 1.0, bases))
    else:
        info, ayuda = resumen_producciones(fila, o)
    with st.container(border=True, key="rec_card_rb_detalle"):
        with st.container(horizontal=True, gap="small", vertical_alignment="center",
                          key="rec_rb_det_cab"):
            # Lo que decían los pies de la tarjeta aparece al pasar el cursor
            # por el nombre; los números, en su mismo renglón.
            st.markdown(f'<p class="chart-card-hdr rec-carta-tit rec-ayuda-larga '
                        f'rec-rb-det-tit" data-ayuda="{escape(ayuda)}">'
                        f'<span class="rec-rb-det-nom">{escape(fila["nombre"])}</span></p>',
                        unsafe_allow_html=True)
            st.markdown(f'<p class="rec-rb-det-info">{escape(info)}</p>',
                        unsafe_allow_html=True)
            with st.container(key="rec_rb_det_cab_ver", width="content"):
                st.selectbox("Ver", VER_DETALLE, key=_K_VER_DETALLE,
                             label_visibility="collapsed", width=140)
        if ver == VER_DETALLE[0]:
            _dib_receta(fila, df_rb, bases)
        else:
            _dib_producciones(fila, o)


def resumen_receta(fila, r):
    """(info, ayuda) de «Receta»: el costo por unidad y cuántas recetas base
    lleva adentro, para la cabecera; y cómo se lee, al pasar el cursor."""
    u = UNIDAD_CORTA.get(fila["unid"], fila["unid"].lower()) or "unidad"
    info = f"Por 1 {u}, precios de hoy: S/ {float(r['Costo'].sum()):,.2f}" if not r.empty else ""
    n = int(r["EsBase"].sum()) if not r.empty else 0
    if n:
        info += f" · {n} {'receta base' if n == 1 else 'recetas base'} adentro (▸)"
    ayuda = (f"Los ingredientes para 1 {u}, con los precios de hoy. Un ingrediente con ▸ "
             "es otra receta base: clic en su fila para ver la suya al costado, "
             f"proporcionada a lo que lleva 1 {u}; adentro se sigue bajando.")
    return info, ayuda


def render_costo_recetas_base(df_rb, df_op=None):
    """Las dos tarjetas: la tabla de las recetas base y, abajo, la receta
    elegida. `df_rb` es recetabase.parquet (o None); `df_op`,
    ordenesproduccion.parquet, o la FUNCIÓN que lo carga (así sólo se lee al
    llegar a la vista, regla #573), o None. Lo usado por las ventas lo pide
    acá (`data.demanda_nivel1_rango`)."""
    ss = st.session_state
    _leer_eleccion()
    with st.container(border=True, key="rec_card_costo_rb"):
        cab = st.container(horizontal=True, gap="small", vertical_alignment="center",
                           key="rec_rb_cab")
        with cab:
            # Un hueco para el título, que se llena al final: su ayuda —lo que
            # era el pie de la tabla— dice el período, que se sabe después.
            hueco_tit = st.empty()
            hueco_tit.markdown(f'<p class="chart-card-hdr">{TITULO}</p>',
                               unsafe_allow_html=True)
        if df_rb is None or df_rb.empty:
            st.info("No se pudieron cargar las recetas base (recetabase.parquet).")
            return
        if callable(df_op):
            if data.secrets_disponibles() and not data.sello_datos(ARCHIVO_ORDENES):
                df_op = None
            else:
                df_op = df_op()
        if df_op is None or df_op.empty:
            st.info("Todavía no hay órdenes de producción (ordenesproduccion.parquet): "
                    "falta la consulta «ordenesproduccion» en el Sheet, o que corra la "
                    "extracción.")
            return
        falta = faltan(df_rb, COLUMNAS_RB) + faltan(df_op, COLUMNAS_OP)
        if falta:
            st.info("A las recetas base o a las órdenes de producción les faltan "
                    f"columnas que esta vista lee: {', '.join(falta)}.")
            return
        cab_rb = cabeceras(df_rb)
        areas = [AREA_TODAS] + sorted(a for a in cab_rb["area"].unique() if a)

        # EL RENGLÓN DEL TÍTULO: los desplegables de la Carta costeada (regla
        # #574).
        with cab:
            with st.container(key="rec_rb_cab_ventana", width="content"):
                if ss.get(_K_VENTANA) not in VENTANAS:
                    ss[_K_VENTANA] = "Últimos 90 días"
                ventana = st.selectbox("Período", list(VENTANAS), key=_K_VENTANA,
                                       label_visibility="collapsed", width=146)
            with st.container(key="rec_rb_cab_area", width="content"):
                if ss.get(_K_AREA) not in areas:
                    ss[_K_AREA] = AREA_TODAS
                area = st.selectbox("Área", areas, key=_K_AREA, label_visibility="collapsed",
                                    width=132, format_func=area_escrita)
            with st.container(key="rec_rb_cab_produccion", width="content"):
                produccion = st.selectbox("Producción", PRODUCCION, key=_K_PRODUCCION,
                                          label_visibility="collapsed", width=150)
            with st.container(key="rec_rb_cab_buscar", width="content"):
                buscar = st.text_input("Buscar", key=_K_BUSCAR, placeholder="Buscar receta",
                                       label_visibility="collapsed", width=160)

        rango = data.rango_fechas(ARCHIVO_N1, "FECHA PEDIDO")
        if rango is None:
            st.info("No se pudo leer el primer nivel de las ventas "
                    f"({ARCHIVO_N1}): sin él no hay «usado».")
            return
        fin = pd.Timestamp(rango[1]).normalize()
        ini = fin - pd.Timedelta(days=VENTANAS[ventana] - 1)
        n1 = data.demanda_nivel1_rango(ini.date(), fin.date())
        if n1 is not None and "vendido" not in n1.columns:
            n1 = None
        sellos = tuple(data.sello_datos(a) for a in
                       ("recetabase.parquet", ARCHIVO_ORDENES, ARCHIVO_N1)) + (n1 is None,)
        t, ords = _calculo(sellos, ini, fin, df_rb, n1, df_op)
        t = filtrar(t, area, buscar, produccion)
        if t.empty:
            st.info("Ninguna receta base con este filtro.")
            return
        _dib_tabla(t, ini, fin)
        # Sin pie, a pedido: la tabla y la receta de abajo tienen que entrar
        # juntas en una pantalla. Lo que decía aparece al pasar el cursor por
        # el título. «¿Vendidos cuándo?» (regla #572): la ventana termina en
        # el último día con venta, no hoy.
        desde = (f"{ini:%d/%m}" if ini.year == fin.year else f"{ini:%d/%m/%Y}")
        ayuda = (f"Del {desde} al {fin:%d/%m/%Y}. {SUBTITULO}. Usado: lo que pidieron las "
                 "ventas según las recetas de hoy, también adentro de otras recetas base. "
                 "Producido: órdenes procesadas. «—» en Prod. ÷ uso: nunca la produjo una "
                 "orden (casi todas las «(L)» y «(P)» salen de un porcionamiento). Elegí "
                 "una fila: abajo, su receta y sus producciones.")
        if n1 is None:
            ayuda = ("No se pudo leer lo que pidieron las ventas: «Platos», «Vendidos» "
                     "y «Usado» salen vacíos. " + ayuda)
            st.caption("No se pudo leer lo que pidieron las ventas.")
        hueco_tit.markdown(f'<p class="chart-card-hdr rec-carta-tit rec-ayuda-larga" '
                           f'data-ayuda="{escape(ayuda)}">{TITULO}</p>',
                           unsafe_allow_html=True)
    fila = t.set_index("cod").loc[ss[_K_FOCO]].copy()
    fila["cod"] = ss[_K_FOCO]
    _tarjeta_receta(fila, df_rb, ords)
