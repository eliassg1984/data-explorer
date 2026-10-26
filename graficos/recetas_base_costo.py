"""
graficos.recetas_base_costo — Recetas y Costos › «Costo Recetas Base»
(2026-09-30, regla #576).

Reemplaza al «Ranking de recetas base», un gráfico de barras con el COSTO
POR LOTE de cada receta del catálogo: decía cuál cuesta más hacer una vez, y
nada de cuánto se usa ni de cómo se movió su costo. A pedido: «una tabla que
me muestre las recetas más usadas dentro de los platos de venta, cruzadas
con las veces que se registran en una orden de producción, y un histórico de
cómo evolucionó el costo por unidad según la orden de producción».

DESDE EL 2026-10-22 ES UNA PIEZA PROPIA (regla #706): `recetas_base_costo.js`
+ `.css` (`st.components.v2`), sobre el boceto aprobado
(https://claude.ai/artifact/8Mgy71Rs9TC4TirzoE8pSo). Hasta ese día eran dos
tarjetas —la tabla de 11 columnas y, debajo, la receta elegida con «Ver:
Receta | Producciones»— hechas con `st.dataframe` y Plotly. Ahora es UNA
tarjeta: arriba el período, el área, «Con | Sin órdenes», el buscador y seis
indicadores que filtran; abajo la lista y, al costado, la ficha de la
elegida con un veredicto y cuatro pestañas —Receta (las recetas base de
adentro se abren en su lugar, y «abrir» lleva a la suya por 1 unidad, como
se pidió en la #576), Producciones (el costo orden a orden y mes a mes con
las ediciones de la receta ▼, 13 semanas de producido contra usado y las
órdenes), Dónde se usa y Cambios—. Python manda todo lo de las cuatro
ventanas de una vez: cambiar de período, filtrar o elegir no pide corrida.

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
    los precios de ESE día. La unidad de la orden y la de la receta
    coinciden en el 100 % (medido).
  · El costo de HOY: `RB COSTO` de recetabase.parquet, la receta con los
    precios de hoy.
  · CÓMO SE DESCARGA cada receta: cada línea de una receta de plato (y de
    una receta base activa) dice si descarga el producto o sus insumos
    (`T DESCARG`). Una receta «DD» se descarga por insumo y no lleva orden;
    una línea que la descarga COMO PRODUCTO pide un producto que nadie
    produce (regla #648). Medido el 2026-10-22: 24 recetas DD tienen líneas
    así —el Zumo de limón de cocina, 24 de sus 44—.
  · Las EDICIONES: el log del Almacén (`carta_costeada.ediciones_bases`,
    reglas #657 y #671).

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
las muestra aparte.
"""

from graficos.movil import css_movil, js_movil
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import consumo_recetas
import data
from simulador_receta import ARCHIVO_LOG, ARCHIVO_LOG_DET

ARCHIVO_ORDENES = "ordenesproduccion.parquet"
ARCHIVO_N1 = consumo_recetas.ARCHIVOS["paloteo"]

TITULO = "Costo recetas base"

VENTANAS = {"30": 30, "90": 90, "182": 182, "365": 365}
"""Las ventanas de lo usado y lo producido, en días. Terminan en el último
día con venta del primer nivel (no hoy), como las de la Carta costeada y
Revisar recetas. El primer nivel trae 12 meses: no hay ventana más larga.
La pieza abre en `VENTANA_INICIAL`."""
VENTANA_INICIAL = "90"

ESTADO_PROCESADO = "PROCESADO"
"""Lo único que suma de una orden (regla #575): GENERADO no produjo nada."""

MESES_LINEA = 12
"""Los meses de la línea «12 m» de la lista y de su variación."""

ATIPICO_FACTOR = 10.0
ATIPICO_VECINAS = 9
"""Una orden es atípica si su costo por unidad se separa más de
`ATIPICO_FACTOR` veces de la mediana de las `ATIPICO_VECINAS` órdenes de la
misma receta alrededor suyo (ver el docstring del módulo)."""

SEMANAS = 13
"""Las semanas de «producido contra usado» en Producciones."""

UNIDAD_CORTA = {"KILOS": "kg", "LITROS": "L", "UND": "und", "UNIDAD": "und",
                "PORCION": "porc"}

UNIDAD_RECETA = {"GRAMOS": "g", "MILILITROS": "ml", "KILOS": "kg", "LITROS": "L",
                 "UND": "und", "UNIDAD": "und", "ONZAS": "oz", "PORCION": "porc"}
"""La unidad en que la receta pide cada ingrediente (la de SALIDA), corta."""

UNIDAD_COMPRA = {("g", 1000.0): "kg", ("ml", 1000.0): "L", ("und", 1.0): "und",
                 ("kg", 1.0): "kg", ("L", 1.0): "L", ("porc", 1.0): "porc"}
"""(unidad de la receta, factor) → la unidad de COMPRA del insumo, la del
kardex: 2.165 líneas en gramos y 490 en mililitros con factor 1.000."""

COBERTURA_BAJA, COBERTURA_ALTA = 0.5, 1.5
"""Producido ÷ usado fuera de este tramo va en ámbar: se produjo mucho menos
de lo que usaron las ventas (o se hace de otra forma), o mucho más."""

VAR_MARCADA = 0.2
"""Desde cuánto se marca la variación de 12 meses: una suba en ámbar, una
baja en verde (como en Compras, subir es gastar más)."""

BRECHA_ORDEN = 0.25
DIAS_ORDEN_RECIENTE = 180
"""«Receta ≠ orden»: la receta con los precios de hoy y la última orden de
los últimos `DIAS_ORDEN_RECIENTE` días se separan más de `BRECHA_ORDEN` —una
cantidad mal cargada en la orden, o el factor de un insumo—."""

CAMPOS_TABLA = ("platos", "vendidos", "usado", "ordenes", "producido")
"""Lo que viaja de cada receta en cada ventana, en ESTE orden."""
CAMPOS_ORDEN = ("fecha", "orden", "area", "cant", "punit", "valor", "atipico")
"""Una orden de producción, en ESTE orden."""
CAMPOS_ING = ("cod", "insumo", "cant", "unid", "costo_unit", "unid_compra",
              "costo", "es_base", "factor")
"""Una línea de una receta (por 1 unidad de entrada), en ESTE orden."""
CAMPOS_DONDE = ("plato", "usado", "vendidos", "directo")
"""Un plato que lleva la receta, en ESTE orden."""

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

_PIEZA = st.components.v2.component(
    "recetas_base_costo",
    css=css_movil((Path(__file__).parent / "recetas_base_costo.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent / "recetas_base_costo.js").read_text(encoding="utf-8")),
)
_K_PIEZA = "rec_rb_pieza"
VERSION = 1
"""Va en la clave de lo armado: tocar qué viaja es subirla."""


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


def _a_entrada(n1, cab, extra=()):
    """El primer nivel con sólo las recetas base y lo pedido en su unidad de
    ENTRADA (`q`): el POS lo da en la de salida (gramos, mililitros)."""
    d = pd.DataFrame({"cod": _txt(n1["cod"]),
                      "consumo": _num(n1["consumo"]).fillna(0.0),
                      **{c: n1[c].values for c in extra}})
    d = d[d["cod"].isin(cab.index)]
    fac = d["cod"].map(cab["factor"])
    return d.assign(q=(d["consumo"] / fac.where(fac > 0)).fillna(0.0))


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


def donde(n1, df_rb, niveles=consumo_recetas.NIVELES_MAX):
    """«Dónde se usa»: cada plato vendido que lleva la receta, directo o
    DENTRO de otra receta base, con lo que usó de ella (en su unidad de
    entrada, por todos los caminos), lo vendido del plato y si la nombra
    directo. Columnas cod, plato, usado, vendidos, directo.

    Hasta el boceto sólo salían los platos que la nombran directo, y la
    Pasta de ajo —31 platos vendidos, todos adentro de otra receta— decía
    «ningún plato la lleva»."""
    cab = cabeceras(df_rb)
    cols = ["cod", "plato", "usado", "vendidos", "directo"]
    if n1 is None or n1.empty:
        return pd.DataFrame(columns=cols)
    d = _a_entrada(n1, cab, extra=("plato", "vendido"))
    d = d.assign(plato=_txt(d["plato"]), vendido=_num(d["vendido"]).fillna(0.0))
    base = d.groupby(["plato", "cod"], as_index=False).agg(q=("q", "sum"),
                                                           vendido=("vendido", "max"))
    base["directo"] = True
    ar = aristas(df_rb)
    partes, frente = [base], base
    for _ in range(niveles):
        j = frente.merge(ar, left_on="cod", right_on="padre")
        if j.empty:
            break
        nuevo = (j.assign(cod=j["hijo"], q=j["q"] * j["coef"])
                 .groupby(["plato", "cod"], as_index=False)
                 .agg(q=("q", "sum"), vendido=("vendido", "max")))
        nuevo = nuevo[nuevo["q"] > 1e-12].assign(directo=False)
        if nuevo.empty:
            break
        partes.append(nuevo)
        frente = nuevo
    t = (pd.concat(partes, ignore_index=True)
         .groupby(["cod", "plato"], as_index=False)
         .agg(usado=("q", "sum"), vendidos=("vendido", "max"), directo=("directo", "max")))
    return t.sort_values(["cod", "usado"], ascending=[True, False], kind="stable")[cols]


def uso_semanal(sem, df_rb, niveles=consumo_recetas.NIVELES_MAX):
    """Lo que usaron las ventas de cada receta base, SEMANA a semana, con lo
    de adentro de otras recetas base. `sem` es lo que devuelve
    `data.demanda_nivel1_semanas` (cod, semana —el lunes—, consumo en unidad
    de salida). Columnas cod, semana, usado (en unidad de entrada)."""
    cab = cabeceras(df_rb)
    cols = ["cod", "semana", "usado"]
    if sem is None or sem.empty:
        return pd.DataFrame(columns=cols)
    d = _a_entrada(sem, cab, extra=("semana",))
    d = d.assign(semana=pd.to_datetime(d["semana"]).dt.normalize())
    total = d.groupby(["cod", "semana"], as_index=False)["q"].sum()
    ar = aristas(df_rb)
    partes, frente = [total], total[total["q"] > 0]
    for _ in range(niveles):
        j = frente.merge(ar, left_on="cod", right_on="padre")
        if j.empty:
            break
        frente = (j.assign(cod=j["hijo"], q=j["q"] * j["coef"])
                  .groupby(["cod", "semana"], as_index=False)["q"].sum())
        frente = frente[frente["q"] > 1e-12]
        partes.append(frente)
    t = pd.concat(partes, ignore_index=True).groupby(["cod", "semana"], as_index=False)["q"].sum()
    return t.rename(columns={"q": "usado"})[cols]


def descarga(df_rv, df_rb):
    """Cómo descargan la receta las líneas que la nombran: por receta base,
    cuántas líneas la nombran (de recetas de plato y de recetas base
    activas) y cuántas la descargan POR INSUMO (`T DESCARG`). Columnas cod,
    lineas, por_insumo. Sin la columna, vacío."""
    cab = cabeceras(df_rb)
    partes = []
    if df_rv is not None and {"COD INS", "T DESCARG"} <= set(df_rv.columns):
        partes.append(pd.DataFrame({"cod": _txt(df_rv["COD INS"]),
                                    "t": _txt(df_rv["T DESCARG"]).str.upper()}))
    if "T DESCARG" in df_rb.columns:
        act = df_rb[_txt(df_rb["RB ACT"]) == consumo_recetas.RECETA_ACTIVA]
        partes.append(pd.DataFrame({"cod": _txt(act["COD INS RB"]),
                                    "t": _txt(act["T DESCARG"]).str.upper()}))
    if not partes:
        return pd.DataFrame(columns=["cod", "lineas", "por_insumo"])
    d = pd.concat(partes, ignore_index=True)
    d = d[d["cod"].isin(cab.index)]
    return (d.assign(ins=d["t"].eq("INSUMO"))
            .groupby("cod", as_index=False)
            .agg(lineas=("t", "size"), por_insumo=("ins", "sum")))


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
    """Una fila por receta base activa, y también por una inactiva que se usó
    o produjo en el período. Ordenada por lo vendido que la llevó y, a igual
    venta, por órdenes. `ords` es lo que devuelve `ordenes()`. Lo que no hay
    va en 0 —o en infinito donde 0 sería un dato (producido ÷ usado de una
    receta que nunca produjo una orden)—."""
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
    # porcionamiento—, producido ÷ usado no es un 0 %: no se hace así.
    hasta = pd.Timestamp(fin) + pd.Timedelta(days=1)
    t["con_ordenes"] = t.index.isin(set(ords.loc[ords["fecha"] < hasta, "cod"]))
    t["cobertura"] = np.where(t["con_ordenes"] & (t["usado"] > 0),
                              t["producido"] / t["usado"].where(t["usado"] > 0), np.inf)
    t["var"] = t["var"].fillna(np.inf)
    # Una línea de un solo mes se dibuja plana y parece un costo que no se
    # movió: con menos de dos meses, sin línea.
    t["linea"] = [v if isinstance(v, list) and len(v) >= 2 else [] for v in t["linea"]]
    t = t.sort_values(["vendidos", "ordenes", "nombre"], ascending=[False, False, True],
                      kind="stable")
    return t.reset_index()


def codigos_base(df_rb):
    """Los códigos de producto que tienen receta base."""
    return frozenset(cabeceras(df_rb).index)


def ingredientes(df_rb, cod, escala=1.0, bases=frozenset()):
    """Los ingredientes de la receta base del producto `cod`, proporcionados a
    `escala` unidades de entrada de ella: Cod, Insumo, Cantidad y Unid (en la
    unidad de la receta: gramos, mililitros), CostoUnit y UnidCompra (lo que
    cuesta una unidad de COMPRA del insumo —el kilo de arroz, S/ 3—, que no
    depende de la escala), Costo (lo que cuesta la cantidad de la receta:
    100 g de ese arroz, S/ 0,30), %, Factor (a la unidad de entrada del
    ingrediente) y EsBase (si el ingrediente tiene a su vez receta base).
    Ordenados por costo.

    `CST SUBT INS` es exactamente `CANT × CST UNIT INS` en todo el parquet
    (medido el 2026-09-30), y `CST UNIT INS` va por unidad de SALIDA (por
    gramo): por unidad de compra es × `FACTOR INS`. Con un factor que no es
    el de gramos o mililitros a kilo o litro, ni 1, no se sabe el nombre de
    la unidad de compra (las onzas de barra, factor 32 o 33): va por unidad
    de la receta."""
    cols = ["Cod", "Insumo", "Cantidad", "Unid", "CostoUnit", "UnidCompra", "Costo", "%",
            "Factor", "EsBase"]
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
    unit = (_num(d["CST UNIT INS"]).fillna(0.0) if "CST UNIT INS" in d
            else out["Costo"] / out["Cantidad"].where(out["Cantidad"] > 0)).fillna(0.0)
    compra = [UNIDAD_COMPRA.get((u, f)) for u, f in zip(out["Unid"], out["Factor"])]
    out["CostoUnit"] = [c * f if uc else c
                        for c, f, uc in zip(unit, out["Factor"], compra)]
    out["UnidCompra"] = [uc or u for uc, u in zip(compra, out["Unid"])]
    total = out["Costo"].sum() or 1.0
    out["%"] = out["Costo"] / total * 100
    out["EsBase"] = out["Cod"].isin(bases) & (out["Cod"] != str(cod).strip())
    return out.sort_values("Costo", ascending=False, kind="stable").reset_index(drop=True)[cols]


def semanas(fin):
    """Los lunes de las `SEMANAS` semanas que terminan en la de `fin`."""
    lunes = pd.Timestamp(fin).normalize() - pd.Timedelta(days=pd.Timestamp(fin).weekday())
    return [lunes - pd.Timedelta(weeks=i) for i in range(SEMANAS - 1, -1, -1)]


def faltan(df, columnas):
    """Las `columnas` que `df` no trae."""
    return [c for c in columnas if c not in df.columns]


# ===========================================================================
# LO QUE VIAJA A LA PIEZA
# ===========================================================================

def _r(v, d=4):
    """Un número para el JSON: None si no es finito."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, d) if np.isfinite(f) else None


def armar(df_rb, ords, n1s, fin, sem=None, df_rv=None, eds=None):
    """Lo que dibuja la pieza (ver el docstring del módulo). `n1s` es
    {ventana: primer nivel de esa ventana}; `ords`, lo que devuelve
    `ordenes()`; `sem`, el primer nivel por semana; `eds`, las ediciones del
    log (o None). Las listas viajan en el orden de `CAMPOS_*`: el `.js` las
    lee por posición."""
    fin = pd.Timestamp(fin).normalize()
    cab = cabeceras(df_rb)
    tablas, dondes, base = {}, {}, None
    for k, dias in VENTANAS.items():
        ini = fin - pd.Timedelta(days=dias - 1)
        n1 = n1s.get(k)
        t = tabla(df_rb, n1, ords, ini, fin)
        # Las filas salen de la ventana más larga: tiene a todas las de las
        # demás (una inactiva que se usó en el año); lo que no depende de la
        # ventana —el último costo, la línea, las órdenes— es el mismo.
        if k == "365":
            base = t
        tablas[k] = {c: [_r(r, 3) for r in fila]
                     for c, *fila in zip(t["cod"], *(t[x] for x in CAMPOS_TABLA))}
        dw = donde(n1, df_rb)
        dondes[k] = {c: [[p, _r(q, 3), _r(v, 0), bool(dr)] for p, q, v, dr in
                         zip(g["plato"], g["usado"], g["vendidos"], g["directo"])][:30]
                     for c, g in dw.groupby("cod", sort=False)}
    filas = [{
        "cod": r["cod"], "nombre": r["nombre"],
        "unid": UNIDAD_CORTA.get(r["unid"], r["unid"].lower()) or "und",
        "area": area_escrita(r["area"]) if r["area"] else "", "activa": bool(r["activa"]),
        "costo_hoy": _r(r["costo_hoy"], 2), "ultimo": _r(r["ultimo"], 2),
        "f_ultimo": r["f_ultimo"].strftime("%Y-%m-%d") if pd.notna(r.get("f_ultimo")) else None,
        "var": _r(r["var"], 4), "linea": [_r(x, 2) for x in r["linea"]],
        "con_ordenes": bool(r["con_ordenes"]),
    } for _, r in base.iterrows()]
    o = {c: [[f.strftime("%Y-%m-%d"), n, area_escrita(a) if a else "", _r(q, 3), _r(p, 3),
              _r(v, 2), int(bool(at))]
             for f, n, a, q, p, v, at in zip(g["fecha"], g["orden"], g["area"], g["cant"],
                                              g["punit"], g["valor"], g["atipico"])]
         for c, g in ords.groupby("cod", sort=False)}
    meses = {c: [[m.strftime("%Y-%m"), _r(x, 3), int(n)] for m, x, n in
                 zip(g["mes"], g["costo"], g["n"])]
             for c, g in costo_por_mes(ords).groupby("cod", sort=False)}
    bases = frozenset(cab.index)
    recetas = {}
    for cod in base["cod"]:
        r = ingredientes(df_rb, cod, 1.0, bases)
        if not r.empty:
            recetas[cod] = [[c, i, _r(q), u, _r(cu, 3), uc, _r(co), int(bool(b)), _r(f)]
                            for c, i, q, u, cu, uc, co, b, f in zip(
                                r["Cod"], r["Insumo"], r["Cantidad"], r["Unid"],
                                r["CostoUnit"], r["UnidCompra"], r["Costo"], r["EsBase"],
                                r["Factor"])]
    padres = {h: [[p, _r(c)] for p, c in zip(g["padre"], g["coef"])]
              for h, g in aristas(df_rb).groupby("hijo", sort=False)}
    lunes = semanas(fin)
    pos = {s: i for i, s in enumerate(lunes)}
    us, pr = {}, {}
    for c, s, q in uso_semanal(sem, df_rb).itertuples(index=False):
        if s in pos and q > 0:
            us.setdefault(c, [0] * SEMANAS)[pos[s]] = _r(q, 3)
    for i, s in enumerate(lunes):
        p = produccion(ords, s, min(s + pd.Timedelta(days=6), fin))
        for c, q in p["producido"].items():
            if q > 0:
                pr.setdefault(c, [0] * SEMANAS)[i] = _r(q, 3)
    desc = {c: [int(n), int(i)] for c, n, i in descarga(df_rv, df_rb).itertuples(index=False)}
    ediciones = {}
    for ed in eds or []:
        ediciones.setdefault(ed["cod_prod"], []).append([
            pd.Timestamp(ed["t"]).strftime("%Y-%m-%d %H:%M"), ed.get("usr") or "",
            _r(ed.get("delta"), 3),
            [[x[1], _r(x[2]), _r(x[3]), _r(x[4], 3)] for x in (ed.get("cambios") or [])][:12]])
    return {
        "v": VERSION, "fin": fin.strftime("%Y-%m-%d"), "ventana": VENTANA_INICIAL,
        "filas": filas, "tablas": tablas, "donde": dondes, "ordenes": o, "meses": meses,
        "recetas": recetas, "padres": padres,
        "semanas": {"lunes": [s.strftime("%Y-%m-%d") for s in lunes], "usado": us, "prod": pr},
        "descarga": desc, "ediciones": ediciones, "hay_log": eds is not None,
        "umbral": {"cob_baja": COBERTURA_BAJA, "cob_alta": COBERTURA_ALTA, "var": VAR_MARCADA,
                   "brecha": BRECHA_ORDEN, "dias_orden": DIAS_ORDEN_RECIENTE},
    }


@st.cache_data(ttl=3600, max_entries=4, show_spinner=False)
def _armado(sellos, fin, _df_rb, _df_op, _n1s, _sem, _df_rv, _eds):
    """`armar`, una vez por versión de los parquets y por día final: la
    cuenta son unos segundos (cuatro ventanas). La clave son los SELLOS
    (`sellos`) y `fin`; los DataFrames van con `_` delante, fuera de la
    clave: hashearlos en cada corrida costaría casi lo que ahorra la caché.
    En memoria, sin `persist="disk"` (regla #367)."""
    return armar(_df_rb, ordenes(_df_op), _n1s, fin, _sem, _df_rv, _eds)


# ===========================================================================
# LA TARJETA
# ===========================================================================

def _sin_datos(msg):
    st.markdown(f'<p class="chart-card-hdr">{TITULO}</p>', unsafe_allow_html=True)
    st.info(msg)


def render_costo_recetas_base(df_rb, df_op=None, df_rv=None):
    """La tarjeta. `df_rb` es recetabase.parquet (o None); `df_op`,
    ordenesproduccion.parquet, o la FUNCIÓN que lo carga (así sólo se lee al
    llegar a la vista, regla #573), o None; `df_rv`, recetaventa.parquet (el
    `df_f` del reporte), para saber cómo descarga cada línea. Lo usado por
    las ventas lo pide acá (`data.demanda_nivel1_rango`)."""
    with st.container(border=True, key="rec_card_costo_rb"):
        if df_rb is None or df_rb.empty:
            _sin_datos("No se pudieron cargar las recetas base (recetabase.parquet).")
            return
        if callable(df_op):
            if data.secrets_disponibles() and not data.sello_datos(ARCHIVO_ORDENES):
                df_op = None
            else:
                df_op = df_op()
        if df_op is None or df_op.empty:
            _sin_datos("Todavía no hay órdenes de producción (ordenesproduccion.parquet): "
                       "falta la consulta «ordenesproduccion» en el Sheet, o que corra la "
                       "extracción.")
            return
        falta = faltan(df_rb, COLUMNAS_RB) + faltan(df_op, COLUMNAS_OP)
        if falta:
            _sin_datos("A las recetas base o a las órdenes de producción les faltan "
                       f"columnas que esta vista lee: {', '.join(falta)}.")
            return
        rango = data.rango_fechas(ARCHIVO_N1, "FECHA PEDIDO")
        if rango is None:
            _sin_datos(f"No se pudo leer el primer nivel de las ventas ({ARCHIVO_N1}): "
                       "sin él no hay «usado».")
            return
        fin = pd.Timestamp(rango[1]).normalize()
        with st.spinner("Armando las recetas base…"):
            n1s = {}
            for k, dias in VENTANAS.items():
                n1 = data.demanda_nivel1_rango((fin - pd.Timedelta(days=dias - 1)).date(),
                                               fin.date())
                n1s[k] = n1 if n1 is not None and "vendido" in n1.columns else None
            sem = data.demanda_nivel1_semanas(semanas(fin)[0].date(), fin.date())
            try:
                from graficos.carta_costeada import ediciones_bases
                eds = ediciones_bases()
            except Exception:
                eds = None
            sellos = tuple(data.sello_datos(a) for a in (
                "recetabase.parquet", ARCHIVO_ORDENES, ARCHIVO_N1, "recetaventa.parquet",
                ARCHIVO_LOG, ARCHIVO_LOG_DET)) + (VERSION, eds is None,
                                                  tuple(k for k, v in n1s.items() if v is None))
            datos = _armado(sellos, fin, df_rb, df_op, n1s, sem, df_rv, eds)
        _PIEZA(key=_K_PIEZA, data=datos, width="stretch")
