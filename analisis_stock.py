"""
analisis_stock — lo que Stock e Inventario mide además del stock de hoy
(2026-10-11, regla #637): cuánto valía cada área y producto después de cada
cierre, cuánto consume el restaurante, la clase ABC, los días de inventario y
el estado que dicen qué mirar.

Puro: sin Streamlit. Lo lee `graficos/inventario_productos.py` (Stock por
Producto) y `graficos/inventario.py` (Stock por Área y Familia); la carga
cacheada vive en `data.py` (`historia_stock`, `consumo_stock`).

DE DÓNDE SALE CADA COSA
  · La historia es la foto del kardex (`kardex.sql_fotos`) con la regla del
    Inventario Histórico Valorizado del POS: por área y producto, el
    movimiento de mayor correlativo hasta ese momento, su stock por su precio
    (regla #601). Un punto por cierre de mes, tomado el día
    `cortes.DIA_CIERRE_OPERATIVO` a las 23:59 del mes siguiente —después del
    conteo, que se registra del 1 al 7 (regla #613)—, más el último momento
    del kardex («hoy»). A fin de mes el stock todavía no está contado y Cocina
    y Barra salen con negativos de miles.
  · El consumo es el del RESTAURANTE ENTERO (`TIPOS_CONSUMO`). Las
    transferencias y requerimientos entre áreas no cuentan: lo que el Almacén
    entrega lo recibe un área, y sumarlo con lo que esa área vende lo contaría
    dos veces. Los ajustes de inventario tampoco: corrigen el conteo, no son
    consumo.
"""

import datetime as dt

import numpy as np
import pandas as pd

from cortes import DIA_CIERRE_OPERATIVO, MESES_ABR_ES

VENTANA_CONSUMO = 90
"""Días hacia atrás desde el último movimiento con que se mide el consumo.
Elección propia, no de un estándar."""

UMBRAL_DIAS = 60
"""Desde cuántos días de inventario un producto «sobra» (`estado` = "alto").
Elección propia."""

CIERRES = 13
"""Cuántos cierres lleva la historia: 13 son 12 meses de punta a punta (el
cierre de setiembre del año pasado y el de este), más «hoy»."""

TIPOS_CONSUMO = ("95", "96", "94", "90", "98", "92", "91")
"""Los tipos del kardex que son CONSUMO: descargo de ventas (95),
porcionamiento (96), orden de producción (94), empacado (90), nota de salida
(98), merma fija (92) y control interno (91). Fuera quedan las compras (los
códigos de SUNAT, menores de 90, incluidas las notas de crédito, que
devuelven al proveedor), el ajuste de inventario (93) y lo que va de un área
a otra (97 transferencia, 99 requerimiento). Ver `kardex._GRUPO_DE_TIPO`."""


def momentos_de_cierre(tope, n=CIERRES, dia=DIA_CIERRE_OPERATIVO):
    """`[(rótulo, datetime)]`: los `n` últimos cierres de mes cuyo conteo ya
    pasó al `tope` (un `datetime`: el último momento del kardex), del más
    viejo al más nuevo, y al final («hoy», `tope`).

    El cierre del mes M se toma el día `dia` del mes siguiente a las 23:00
    (la hora entera, como `kardex.momento`: hasta las 23:59). Con el kardex al
    9 de octubre, el último es setiembre (7 oct); con el kardex al 5, todavía
    no: es agosto. El rótulo es el mes que cierra, «set 26»."""
    cierres = []
    anio, mes = tope.year, tope.month
    while len(cierres) < n:
        # El cierre del mes ANTERIOR a (anio, mes) se toma en (anio, mes).
        momento = dt.datetime(anio, mes, dia, 23, 0)
        pa, pm = (anio, mes - 1) if mes > 1 else (anio - 1, 12)
        if momento <= tope:
            cierres.append((f"{MESES_ABR_ES[pm - 1]} {str(pa)[2:]}", momento))
        anio, mes = pa, pm
    return list(reversed(cierres)) + [("hoy", tope)]


def valor_en_momentos(fotos, momentos):
    """El valor del stock de cada área y producto en cada momento: DataFrame
    indexado por (`area`, `cod`) con una columna por momento (0..n-1), en el
    orden de `momentos` (`datetime`).

    `fotos` es lo que devuelve `kardex.sql_fotos`: `area`, `cod`, `fecha`,
    `correlativo`, `stock`, `precio`. La regla es la de `kardex.sql_stock_al`
    —el movimiento de MAYOR CORRELATIVO con fecha hasta el momento, no el de
    hora más tardía— aplicada a todos los momentos sobre una sola lectura,
    como `costo_ventas.inventario_en_momentos`. Un área y producto sin
    movimiento hasta un momento vale 0 en él."""
    if fotos is None or fotos.empty or not momentos:
        return pd.DataFrame(columns=list(range(len(momentos or []))),
                            index=pd.MultiIndex.from_arrays([[], []],
                                                            names=["area", "cod"]))
    f = pd.DataFrame({
        "area": fotos["area"].astype(str).str.strip(),
        "cod": fotos["cod"].astype(str).str.strip(),
        "fecha": pd.to_datetime(fotos["fecha"], errors="coerce"),
        "correlativo": pd.to_numeric(fotos["correlativo"], errors="coerce"),
        "v": (pd.to_numeric(fotos["stock"], errors="coerce").fillna(0)
              * pd.to_numeric(fotos["precio"], errors="coerce").fillna(0)),
    }).dropna(subset=["fecha"])
    # Estable: dos filas con el mismo correlativo quedan en el orden de la
    # fecha, y la última de las dos es la que manda (`keep="last"`).
    f = f.sort_values(["area", "cod", "correlativo", "fecha"], kind="stable")
    columnas = []
    for m in momentos:
        ultimo = f[f["fecha"] <= pd.Timestamp(m)].drop_duplicates(
            ["area", "cod"], keep="last")
        columnas.append(ultimo.set_index(["area", "cod"])["v"])
    # Las columnas se nombran con `keys`, no renombrando por posición
    # (regla #481): pandas 3 acá y 2.2 en Cloud.
    out = pd.concat(columnas, axis=1, keys=list(range(len(momentos)))).fillna(0.0)
    out.index.names = ["area", "cod"]
    return out


def consumo_por_producto(movs):
    """Cuánto consumió el restaurante entero de cada producto (Series `cod`
    → cantidad, en la unidad del kardex), de los movimientos por área,
    producto y tipo de `kardex.sql_movimientos`: la cantidad que SALIÓ por
    los `TIPOS_CONSUMO`, sumada entre áreas."""
    if movs is None or movs.empty:
        return pd.Series(dtype=float)
    t = movs["tipo"].astype(str).str.strip()
    m = movs[t.isin(TIPOS_CONSUMO)]
    return (pd.to_numeric(m["cant_out"], errors="coerce").fillna(0)
            .groupby(m["cod"].astype(str).str.strip()).sum())


def clase_abc(valores, cortes=(0.80, 0.95)):
    """La clase ABC de cada valor (Series del mismo índice): de mayor a
    menor, A hasta que lo acumulado ANTES de él llega al 80 %, B hasta el
    95 %, C el resto. Un valor que no es positivo no tiene clase (None): un
    negativo no es «parte del valor». Análisis ABC (H. F. Dickie, General
    Electric, 1951); los cortes 80/95 son práctica difundida, no del
    estándar."""
    v = pd.to_numeric(pd.Series(valores), errors="coerce")
    # Una lista de None y no `pd.Series(None, dtype=object)`, que en pandas 3
    # nace con NaN: un «sin clase» tiene que ser None en las dos versiones.
    out = pd.Series([None] * len(v), index=v.index, dtype=object)
    pos = v[v > 0].sort_values(ascending=False, kind="stable")
    total = float(pos.sum())
    if not total:
        return out
    antes = (pos.cumsum() - pos) / total
    out.loc[pos.index] = np.where(antes < cortes[0], "A",
                                  np.where(antes < cortes[1], "B", "C"))
    return out


def dias_de_inventario(cantidad, consumo, ventana=VENTANA_CONSUMO):
    """Para cuántos días alcanza `cantidad` al ritmo de `consumo` en
    `ventana` días: stock ÷ consumo diario promedio («inventory days of
    supply», métrica del modelo SCOR, ASCM). NaN si no hay stock positivo o
    no hubo consumo: «para siempre» no es un número. Vectorizada."""
    q = pd.to_numeric(pd.Series(cantidad), errors="coerce")
    c = pd.to_numeric(pd.Series(consumo, index=q.index), errors="coerce")
    ok = (q > 0) & (c > 0)
    return (q / (c / ventana)).where(ok)


def estado(cantidad, consumo, dias, umbral=UMBRAL_DIAS):
    """Qué mirar de cada producto, en este orden: "neg" (stock bajo cero),
    "sin" (con stock y sin consumo en la ventana), "alto" (alcanza para más
    de `umbral` días) o "" (nada). Vectorizada."""
    q = pd.to_numeric(pd.Series(cantidad), errors="coerce").fillna(0)
    c = pd.to_numeric(pd.Series(consumo, index=q.index), errors="coerce").fillna(0)
    d = pd.to_numeric(pd.Series(dias, index=q.index), errors="coerce")
    out = pd.Series("", index=q.index, dtype=object)
    out = out.mask(d > umbral, "alto")
    out = out.mask((q > 0) & (c <= 0), "sin")
    return out.mask(q < 0, "neg")


def dias_del_conjunto(valorizado, cantidad, consumo, precio,
                      ventana=VENTANA_CONSUMO):
    """Los días de inventario de VARIOS productos juntos: lo que vale el stock
    positivo ÷ lo que se consume por día, en soles (consumo × precio). Sumar
    los días de cada producto no tiene sentido; esto es la misma cuenta sobre
    el conjunto. NaN si no hubo consumo."""
    v = pd.to_numeric(pd.Series(valorizado), errors="coerce").fillna(0)
    q = pd.to_numeric(pd.Series(cantidad, index=v.index), errors="coerce").fillna(0)
    c = pd.to_numeric(pd.Series(consumo, index=v.index), errors="coerce").fillna(0)
    p = pd.to_numeric(pd.Series(precio, index=v.index), errors="coerce").fillna(0)
    con = q > 0
    diario = float((c[con] * p[con]).sum()) / ventana
    return float(v[con].clip(lower=0).sum()) / diario if diario > 0 else float("nan")
