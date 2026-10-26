"""
sin_plato — en qué se fue cada producto, de CIERRE A CIERRE de inventario.

Las dos vistas de Movimientos › Salidas que reemplazaron a «Destino de lo que
entra» (2026-10-12, regla #645), aprobadas sobre un boceto con los datos
reales (https://claude.ai/artifact/PGPfFuLb6MRGe42cscGtrQ):

  · «Sin plato, cierre por cierre» — lo que salió sin ir a un plato en el
    restaurante entero, mes a mes, y en qué productos se concentra.
  · «En qué se fue cada producto» — la misma cuenta, producto por producto.

POR QUÉ DE CIERRE A CIERRE. La vista vieja sumaba un rango cualquiera de
fechas, y el ajuste de inventario —el faltante— sólo existe el día en que se
cuenta: con «los últimos 30 días» podía caer un cierre, ninguno o dos. Un
período va del día siguiente al último conteo del cierre anterior al último
conteo de este (`cortes.sesiones_inventario`: cierre = lo contado del 1 al 7
del mes siguiente, regla #632). Setiembre 2026 va del 3 set al 6 oct.

LA CUENTA, por producto y período, en el restaurante entero (las áreas
sumadas; lo que va de un área a otra suma cero y no entra,
`kardex.TIPOS_ENTRE_AREAS`):

    había + entró − a un plato − en preparaciones − bajas − otras + ajuste
        = quedó                                    (cierra contra el kardex)

    entró            compras (tipos de SUNAT, < 90, netos de notas de
                     crédito) + lo que sale de una orden de producción (94),
                     un porcionamiento (96) o un empacado (90)
    a un plato       el descargo de ventas (95), partido en VENTA (con lo
                     servido dentro de combos), CORTESÍA y EVENTOS Y VENTA
                     INTERNA. Medido el 2026-10-11: el POS descuenta las
                     cortesías y no los anulados (el encurtido de vegetales,
                     6,6 en venta + 366,84 en cortesía = 373,44 en el kardex)
    en preparaciones lo que salió como insumo de 90, 94 o 96: no es pérdida,
                     el valor pasa al producto que sale de ahí
    bajas            las notas de salida de tipo «Bajas» (`salidas.parquet`),
                     por fecha de PROCESO, la del kardex (regla #614)
    otras            el resto de las notas (91, 92, 98): comida de personal,
                     uso del área, merma fija, control interno
    ajuste           los conteos del período (93). Negativo es FALTANTE.

    sin plato = bajas + otras + faltante
    % sin plato = sin plato ÷ todo lo que salió (cálculo propio, no un
                  indicador publicado)

CÓMO SE PARTE LO VENDIDO. El kardex no dice qué fue venta y qué cortesía: se
reparte con lo vendido en el POS por plato y día (`definicion_venta.
unidades_por_clase_dia`) × lo que cada plato descuenta: su receta de venta
(`recetaventa.parquet`) o, si el POS lo descuenta DIRECTO, una unidad del
producto enlazado (`cartacosteada.parquet`, `TIPO DESC` = DIRECTO: los cortes
de parrilla, los chorizos de Mayta, las aguas). Con las recetas solas
quedaba sin explicar el 37 % de lo vendido; con los directos, el 12 %.

UNA LÍNEA «POR INSUMO» NO DESCUENTA SU RECETA BASE (regla #648). Con el
check «descarga por insumo» del POS (`T DESCARG` = INSUMO) el kardex no
toca la receta base que nombra la línea sino SUS insumos, y cada línea de
`recetabase.parquet` vuelve a decir cómo se descarga la suya. Leída como
producto, la línea se llevaba lo vendido a un código que el kardex no movió
(setiembre 2026: de las 17 recetas base así nombradas en platos vendidos,
no movió 7, y las otras 10 las nombra como producto otro plato), el recorte
la dejaba en cero y sus insumos —la palta, el ají amarillo, el huevo—
quedaban sin explicar. Abriéndolas, lo que queda sin explicar baja al 10 %, y es lo
servido dentro de combos (CPEDIDO no llega a ningún parquet), que va en
«venta». Nunca se reparte más de lo que el kardex descontó.

INSUMOS DE OPERACIÓN: la familia «COSTOS PRODUCCION» (carbón, leña,
limpieza, descartables). Ninguna receta los descarga, así que su consumo
sólo aparece al contar: van aparte, para que no se lean como faltante de la
comida.

Puro pandas, sin streamlit. Lo vigila `test_graficos.py::_pruebas_sin_plato`.
"""

import datetime as dt

import numpy as np
import pandas as pd

import definicion_venta as dv
import kardex
from cortes import MESES_ABR_ES, MESES_LARGOS_ES

VERSION = 3
"""Va en la clave de la caché de disco (que no caduca): subirla cuando
cambie QUÉ se calcula. La 2: las líneas que se descargan por insumo bajan
por su receta base (regla #648). La 3 conserva el desglose por tipo del
Sankey; no cambia las columnas de la cuenta original."""

DESDE = (2025, 9)
"""El cierre desde el que se cuenta: el primer período es octubre 2025.
Antes los cierres no cuadran con el kardex, y el de setiembre 2025 trae la
limpieza de inventario de S/ 627 mil (regla #612)."""

CIERRES_ATRAS = 6
"""Contra cuántos cierres anteriores se compara el % sin plato. No contra el
año pasado: la limpieza de setiembre 2025 haría que cualquier mes pareciera
bueno."""

FAMILIA_OPERACION = "COSTOS PRODUCCION"
GRUPOS_APARTE = ("EVENTOS", "VENTA INTERNA")
"""Grupos de carta que gastan inventario y no son la venta del salón (los
mismos de `costo_ventas.GRUPOS_APARTE`)."""

TIPOS_PRODUCE = ("90", "94", "96")
TIPO_VENTAS = "95"
TIPO_AJUSTE = "93"
TIPOS_NOTAS = ("91", "92", "98")
TIPO_BAJAS = "BAJAS"

POR_INSUMO = "INSUMO"
"""El `T DESCARG` de una línea que el POS descarga por los insumos de su
receta base, y no por el producto (el otro valor es PRODUCTO)."""
RECETA_ACTIVA = "RB.ACTIV"
NIVELES_MAX = 12
"""Hasta cuántas recetas base anidadas se baja (`consumo_recetas` usa las
mismas): una receta que se nombra a sí misma no cuelga la cuenta."""

ALIMENTOS = "alimentos"
OPERACION = "operacion"

PARTES = ("ini", "entro", "compra", "venta", "combos", "cort", "evvi", "prep",
          "baja", "otras", "aj", "fin")
"""Lo que se mide de cada producto en cada período, en cantidad (`_q`, la
unidad del kardex) y en soles (`_v`). `compra` sólo en soles: es la parte de
`entro` que vino de afuera, la que suma el restaurante."""


def _norm(s):
    return str(s).strip().upper().replace("_", " ")


def _col(df, *nombres):
    """El nombre real de la primera columna de `nombres` que exista en `df`."""
    if df is None:
        return None
    mapa = {_norm(c): c for c in df.columns}
    for n in nombres:
        if _norm(n) in mapa:
            return mapa[_norm(n)]
    return None


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _cod(s):
    return s.fillna("").astype(str).str.strip()


# ═══════════════════════════════════════════════════════════════════════
# LOS PERÍODOS
# ═══════════════════════════════════════════════════════════════════════

def periodos(sesiones, desde=DESDE):
    """Los períodos de cierre a cierre, del más viejo al más nuevo: una lista
    de dicts con `k` (0..n-1), `clave` (la de la sesión que lo cierra),
    `mes`, `nombre` («Setiembre 2026»), `corto` («set 26»), `desde`/`hasta`
    (`date`, inclusive), `t0`/`t1` (Timestamps, `t1` exclusivo), `cierre` y
    `cierre_ant` (los días de los dos conteos) y `sesion` (la del cierre).

    `sesiones` es lo de `cortes.sesiones_inventario`; sólo cuentan los
    cierres de mes desde `desde`, que es el BORDE de entrada: con (2025, 9)
    el primer período es octubre."""
    cierres = [s for s in sesiones or []
               if s["tipo"] == "cierre" and tuple(s["mes"]) >= tuple(desde)]
    out = []
    for a, b in zip(cierres[:-1], cierres[1:]):
        y, m = b["mes"]
        t0 = pd.Timestamp(a["fin"]) + pd.Timedelta(days=1)
        t1 = pd.Timestamp(b["fin"]) + pd.Timedelta(days=1)
        out.append({
            "k": len(out), "clave": b["clave"], "mes": (y, m),
            "nombre": f"{MESES_LARGOS_ES[m - 1].capitalize()} {y}",
            "corto": f"{MESES_ABR_ES[m - 1]} {y % 100:02d}",
            "desde": t0.date(), "hasta": b["fin"], "t0": t0, "t1": t1,
            "cierre": b["etiqueta_anio"], "cierre_ant": a["etiqueta_anio"],
            "sesion": b,
        })
    return out


def momentos(per):
    """Los instantes de las fotos de stock: el final del día antes del
    primer período y el final del último día de cada uno (la hora 23, como
    `kardex.momento`). El stock con que ABRE el período k es el momento k;
    con el que CIERRA, el k+1."""
    if not per:
        return []
    ini = dt.datetime.combine(per[0]["desde"] - dt.timedelta(days=1), dt.time(23))
    return [ini] + [dt.datetime.combine(p["hasta"], dt.time(23)) for p in per]


def _periodo_de(fechas, per):
    """El `k` de cada fecha (NaN fuera de todos los períodos)."""
    if not per:
        return pd.Series(np.nan, index=fechas.index)
    bordes = [p["t0"] for p in per] + [per[-1]["t1"]]
    return pd.cut(pd.to_datetime(fechas, errors="coerce"), bins=bordes,
                  right=False, labels=False)


# ═══════════════════════════════════════════════════════════════════════
# LAS PIEZAS
# ═══════════════════════════════════════════════════════════════════════

def movimientos(kx):
    """De `kardex.sql_movimientos_cortes` (`k`, `cod`, `tipo`, `cant_in`,
    `cant_out`, `val_in`, `val_out`) a una fila por (`cod`, `k`) con lo que
    entró, se vendió, se usó en preparaciones, salió por notas y se ajustó,
    en cantidad y en soles. Pura."""
    detalle = ([f"{lado}_{tipo}_v" for tipo in TIPOS_PRODUCE
                for lado in ("ing", "prep")]
               + [f"nota_{tipo}_v" for tipo in TIPOS_NOTAS]
               + ["otros_ing_v", "otros_sal_v"])
    cols = ["cod", "k"] + [f"{p}_{s}" for p in ("entro", "prep", "vend",
                                                "aj", "notas")
                          for s in ("q", "v")] + ["compra_v"] + detalle
    if kx is None or kx.empty:
        return pd.DataFrame(columns=cols)
    t = kx.assign(cod=_cod(kx["cod"]), tipo=_cod(kx["tipo"]))
    tipo = t["tipo"]
    cin, cout = _num(t["cant_in"]), _num(t["cant_out"])
    vin, vout = _num(t["val_in"]), _num(t["val_out"])
    compra = tipo.str.isdigit() & (tipo < "90")
    produce = tipo.isin(TIPOS_PRODUCE)
    ventas, ajuste = tipo == TIPO_VENTAS, tipo == TIPO_AJUSTE
    notas = tipo.isin(TIPOS_NOTAS)
    b = pd.DataFrame({
        "cod": t["cod"], "k": t["k"].astype(int),
        "entro_q": np.where(compra, cin - cout, np.where(produce, cin, 0.0)),
        "entro_v": np.where(compra, vin - vout, np.where(produce, vin, 0.0)),
        "compra_v": np.where(compra, vin - vout, 0.0),
        "prep_q": np.where(produce, cout, 0.0),
        "prep_v": np.where(produce, vout, 0.0),
        "vend_q": np.where(ventas, cout - cin, 0.0),
        "vend_v": np.where(ventas, vout - vin, 0.0),
        "aj_q": np.where(ajuste, cin - cout, 0.0),
        "aj_v": np.where(ajuste, vin - vout, 0.0),
        "notas_q": np.where(notas, cout - cin, 0.0),
        "notas_v": np.where(notas, vout - vin, 0.0),
    })
    for codigo in TIPOS_PRODUCE:
        b[f"ing_{codigo}_v"] = np.where(tipo == codigo, vin, 0.0)
        b[f"prep_{codigo}_v"] = np.where(tipo == codigo, vout, 0.0)
    for codigo in TIPOS_NOTAS:
        b[f"nota_{codigo}_v"] = np.where(tipo == codigo, vout - vin, 0.0)
    # Los tipos desconocidos quedan explícitos; 97/99 son traslados internos
    # excluidos por la consulta del restaurante entero, no consumo adicional.
    otros = ~(compra | produce | ventas | ajuste | notas
              | tipo.isin((*kardex.TIPOS_ENTRE_AREAS, "SI")))
    b["otros_ing_v"] = np.where(otros, vin, 0.0)
    b["otros_sal_v"] = np.where(otros, vout, 0.0)
    return b.groupby(["cod", "k"], as_index=False)[cols[2:]].sum()[cols]


def bajas(salidas, per):
    """Las notas de tipo «Bajas» de `salidas.parquet` por (`cod`, `k`):
    `baja_q` y `baja_v` (su valor neto). Por fecha de PROCESO, la del kardex,
    sin las anuladas ni las líneas sin producto. Pura."""
    vacio = pd.DataFrame(columns=["cod", "k", "baja_q", "baja_v"])
    if salidas is None or salidas.empty or not per:
        return vacio
    c_f = _col(salidas, "FECHA PROCESADO", "Fecha procesado")
    c_est = _col(salidas, "NOMBRE ESTADO SALIDA", "Nombre Estado Salida")
    c_cod = _col(salidas, "COD PRODUCTO", "Cod Producto")
    c_tipo = _col(salidas, "TIPO DESCARGO", "Tipo Descargo")
    c_q = _col(salidas, "CANT SALIDA", "Cant Salida")
    c_v = _col(salidas, "VALOR NETO", "Valor Neto")
    if not all((c_f, c_cod, c_tipo, c_q, c_v)):
        return vacio
    est = (_cod(salidas[c_est]).str.upper() if c_est
           else pd.Series("", index=salidas.index))
    cod = _cod(salidas[c_cod])
    m = ((_cod(salidas[c_tipo]).str.upper() == TIPO_BAJAS)
         & (est != "ANULADO") & (cod != ""))
    b = pd.DataFrame({"cod": cod[m], "k": _periodo_de(salidas.loc[m, c_f], per),
                      "baja_q": _num(salidas.loc[m, c_q]),
                      "baja_v": _num(salidas.loc[m, c_v])}).dropna(subset=["k"])
    if b.empty:
        return vacio
    b["k"] = b["k"].astype(int)
    return b.groupby(["cod", "k"], as_index=False)[["baja_q", "baja_v"]].sum()


def stock_en_momentos(fotos, instantes):
    """El stock del restaurante entero de cada producto en cada instante:
    una fila por (`cod`, `i`) con `q` y `v`. `fotos` es lo de
    `kardex.sql_fotos`; la regla, la de `kardex.sql_stock_al` —por área y
    producto, el movimiento de MAYOR correlativo hasta ese instante— sobre
    una sola lectura, como `analisis_stock.valor_en_momentos`. Pura."""
    vacio = pd.DataFrame(columns=["cod", "i", "q", "v"])
    if fotos is None or fotos.empty or not instantes:
        return vacio
    st_ = _num(fotos["stock"])
    f = pd.DataFrame({
        "area": _cod(fotos["area"]), "cod": _cod(fotos["cod"]),
        "fecha": pd.to_datetime(fotos["fecha"], errors="coerce"),
        "correlativo": pd.to_numeric(fotos["correlativo"], errors="coerce"),
        "q": st_, "v": st_ * _num(fotos["precio"]),
    }).dropna(subset=["fecha"])
    # Estable: dos filas con el mismo correlativo quedan en el orden de la
    # fecha y manda la última (`keep="last"`).
    f = f.sort_values(["area", "cod", "correlativo", "fecha"], kind="stable")
    partes = []
    for i, m in enumerate(instantes):
        u = f[f["fecha"] <= pd.Timestamp(m)].drop_duplicates(["area", "cod"],
                                                              keep="last")
        g = u.groupby("cod", as_index=False)[["q", "v"]].sum()
        g["i"] = i
        partes.append(g)
    out = pd.concat(partes, ignore_index=True)
    return out[["cod", "i", "q", "v"]]


def lineas_receta_base(recetabase):
    """Lo que descuenta UNA unidad del kardex de cada receta base abierta
    por sus insumos: una fila por (`prod` la receta base, `ci` insumo, `t`)
    con `q` en la unidad del kardex del insumo (la línea habla en la de
    salida: se divide por su `FACTOR INS`; un lote es una unidad de entrada,
    como en `consumo_recetas`). `t` es el `T DESCARG` de la línea: si vuelve
    a ser POR_INSUMO, ese insumo se abre a su vez. Sólo la receta activa y
    las líneas que descargan. Pura."""
    vacio = pd.DataFrame(columns=["prod", "ci", "t", "q"])
    if recetabase is None or recetabase.empty:
        return vacio
    rb = recetabase
    c_p, c_i = _col(rb, "COD PROD RB"), _col(rb, "COD INS RB")
    c_c, c_f = _col(rb, "CANT"), _col(rb, "FACTOR INS")
    if not (c_p and c_i and c_c):
        return vacio
    c_a, c_d, c_t = _col(rb, "RB ACT"), _col(rb, "DESCARGA"), _col(rb, "T DESCARG")
    if c_a:
        rb = rb[_cod(rb[c_a]).str.upper() == RECETA_ACTIVA]
    if c_d:
        rb = rb[_cod(rb[c_d]).str.upper() == "DESC"]
    fac = (_num(rb[c_f]).replace(0, 1.0) if c_f
           else pd.Series(1.0, index=rb.index))
    e = pd.DataFrame({"prod": _cod(rb[c_p]), "ci": _cod(rb[c_i]),
                      "t": _cod(rb[c_t]).str.upper() if c_t else "",
                      "q": _num(rb[c_c]) / fac})
    e = e[(e["prod"] != "") & (e["ci"] != "")]
    return e.groupby(["prod", "ci", "t"], as_index=False)["q"].sum()


def _abrir_por_insumo(lineas, rb):
    """`lineas` (`cp`, `ci`, `q`, `t`) con cada una que se descarga
    POR_INSUMO cambiada por las de su receta base (`lineas_receta_base`),
    nivel por nivel, hasta que ninguna lo pida o hasta NIVELES_MAX. Una
    línea POR_INSUMO cuyo código no tiene receta activa, o que ya está en
    su propio camino (una receta que se nombra a sí misma), queda como
    producto. Pura."""
    if rb.empty:
        return lineas
    abribles = set(rb["prod"])
    m = lineas.assign(ruta="/" + lineas["ci"] + "/")
    hechas = []
    for _ in range(NIVELES_MAX):
        abrir = (m["t"] == POR_INSUMO) & m["ci"].isin(abribles)
        hechas.append(m[~abrir])
        if not abrir.any():
            m = m.iloc[0:0]
            break
        x = m[abrir].merge(rb.rename(columns={"prod": "ci", "ci": "hijo",
                                              "t": "t_hijo", "q": "coef"}),
                           on="ci")
        ruta = x["ruta"] + x["hijo"] + "/"
        vuelve = [f"/{h}/" in r for h, r in zip(x["hijo"], x["ruta"])]
        m = pd.DataFrame({"cp": x["cp"], "ci": x["hijo"],
                          "q": x["q"] * x["coef"],
                          "t": np.where(vuelve, "", x["t_hijo"]), "ruta": ruta})
    hechas.append(m)
    return pd.concat(hechas, ignore_index=True).drop(columns="ruta")


def mapa_descargo(recetaventa, carta=None, recetabase=None):
    """Qué descuenta del stock cada plato que se vende: una fila por
    (`cp` plato, `ci` producto) con `q`, la cantidad por plato en la unidad
    del KARDEX (la receta habla en la de salida: se divide por su `FACTOR`).

    Una línea con `T DESCARG` = INSUMO no descuenta el producto que nombra
    sino los insumos de su receta base (`recetabase`, la de
    `recetabase.parquet`), y así hacia abajo según el `T DESCARG` de cada
    línea de la receta base (regla #648). Sin `recetabase`, o sin la
    columna, toda línea descuenta su producto.

    Los platos sin receta que el POS descuenta DIRECTO —un plato, una unidad
    del producto enlazado— salen de `carta` (`cartacosteada.parquet`, `TIPO
    DESC` = DIRECTO). Pura."""
    partes = []
    con_receta = set()
    if recetaventa is not None and not recetaventa.empty:
        r = recetaventa
        c_d = _col(r, "DESCARG")
        if c_d:
            r = r[_cod(r[c_d]).str.upper() == "SI"]
        c_p, c_i = _col(r, "COD PLATO"), _col(r, "COD INS")
        c_c, c_f = _col(r, "CANTIDAD"), _col(r, "FACTOR")
        c_t = _col(r, "T DESCARG")
        if c_p and c_i and c_c:
            fac = (_num(r[c_f]).replace(0, 1.0) if c_f
                   else pd.Series(1.0, index=r.index))
            lineas = pd.DataFrame({"cp": _cod(r[c_p]), "ci": _cod(r[c_i]),
                                   "q": _num(r[c_c]) / fac,
                                   "t": _cod(r[c_t]).str.upper() if c_t else ""})
            con_receta = set(lineas["cp"])
            partes.append(_abrir_por_insumo(
                lineas, lineas_receta_base(recetabase))[["cp", "ci", "q"]])
    if carta is not None and not carta.empty:
        c_t, c_p = _col(carta, "TIPO DESC"), _col(carta, "COD PLATO")
        c_i = _col(carta, "COD ITEM O RECETA")
        if c_t and c_p and c_i:
            d = carta[_cod(carta[c_t]).str.upper() == "DIRECTO"]
            d = pd.DataFrame({"cp": _cod(d[c_p]), "ci": _cod(d[c_i]), "q": 1.0})
            partes.append(d[(d["ci"] != "") & ~d["cp"].isin(con_receta)])
    if not partes:
        return pd.DataFrame(columns=["cp", "ci", "q"])
    m = pd.concat(partes, ignore_index=True)
    m = m[(m["cp"] != "") & (m["ci"] != "")]
    return m.groupby(["cp", "ci"], as_index=False)["q"].sum()


def reparto_venta(vend, mapa, per):
    """Lo que el POS vendió, llevado a cada producto que descuenta: una fila
    por (`cod`, `k`) con `venta`, `cort` y `evvi` en la unidad del kardex.
    `vend` es lo de `definicion_venta.unidades_por_clase_dia`. Pura."""
    vacio = pd.DataFrame(columns=["cod", "k", "venta", "cort", "evvi"])
    if vend is None or vend.empty or mapa is None or mapa.empty or not per:
        return vacio
    grupo = _cod(vend["grupo"]).str.upper()
    cat = np.where(vend["clase"] == dv.CORTESIA, "cort",
                   np.where(grupo.isin(GRUPOS_APARTE), "evvi", "venta"))
    v = pd.DataFrame({"cp": _cod(vend["producto"]), "cat": cat,
                      "n": _num(vend["unidades"]),
                      "k": _periodo_de(vend["dia"], per)}).dropna(subset=["k"])
    x = v.merge(mapa, on="cp", how="inner")
    if x.empty:
        return vacio
    x["qq"] = x["n"] * x["q"]
    x["k"] = x["k"].astype(int)
    g = x.groupby(["ci", "k", "cat"], as_index=False)["qq"].sum()
    p = g.pivot_table(index=["ci", "k"], columns="cat", values="qq",
                      aggfunc="sum", fill_value=0.0).reset_index()
    for c in ("venta", "cort", "evvi"):
        if c not in p.columns:
            p[c] = 0.0
    p = p.rename(columns={"ci": "cod"})
    return p[["cod", "k", "venta", "cort", "evvi"]]


def _maestro(maestro):
    """Nombre, unidad del kardex y familia de cada producto, del inventario
    valorizado (una fila por área × producto: se queda una)."""
    vacio = pd.DataFrame(columns=["cod", "producto", "unidad", "familia"])
    if maestro is None or maestro.empty:
        return vacio
    c_c = _col(maestro, "CODIGO PRODUCTO", "Codigo Producto")
    if not c_c:
        return vacio
    c_n = _col(maestro, "NOMBRE PRODUCTO", "Nombre Producto")
    c_u = _col(maestro, "UNIDAD KARDEX", "Unidad Kardex")
    c_f = _col(maestro, "NOMBRE FAMILIA", "Nombre Familia")
    m = maestro.drop_duplicates(c_c)
    return pd.DataFrame({
        "cod": _cod(m[c_c]),
        "producto": _cod(m[c_n]) if c_n else _cod(m[c_c]),
        "unidad": _cod(m[c_u]) if c_u else "",
        "familia": _cod(m[c_f]) if c_f else "",
    })


# ═══════════════════════════════════════════════════════════════════════
# LA CUENTA
# ═══════════════════════════════════════════════════════════════════════

def calcular(per, kx, fotos, salidas, vend, recetaventa, carta, maestro,
             recetabase=None):
    """Todo lo que dibujan las dos vistas: `{"periodos", "filas",
    "totales"}`. `recetabase` abre las líneas que se descargan por insumo
    (`mapa_descargo`, regla #648).

    `filas`: una por (`cod`, `k`) con algún movimiento o stock, con
    `producto`, `unidad`, `familia`, `clase` (ALIMENTOS u OPERACION) y cada
    una de `PARTES` en `_q` y `_v` (salvo `compra`, sólo `_v`), más
    `falt`, `sobr`, `plato`, `sinplato` y `salio` en las dos medidas y
    `pct` (sin plato ÷ salió, en soles; NaN si no salió nada).

    `totales`: una por `k`, en soles, la cuenta del restaurante —ver
    `totales`—. Pura."""
    per = list(per or [])
    m = movimientos(kx)
    instantes = momentos(per)
    fot = stock_en_momentos(fotos, instantes)
    ini = fot.rename(columns={"i": "k", "q": "ini_q", "v": "ini_v"})
    fin = fot.assign(i=fot["i"] - 1).rename(
        columns={"i": "k", "q": "fin_q", "v": "fin_v"})
    fin = fin[fin["k"] >= 0]
    ini = ini[ini["k"] < len(per)]
    g = (m.merge(bajas(salidas, per), on=["cod", "k"], how="outer")
          .merge(ini, on=["cod", "k"], how="outer")
          .merge(fin, on=["cod", "k"], how="outer"))
    num = [c for c in g.columns if c not in ("cod", "k")]
    g[num] = g[num].fillna(0.0)
    g["k"] = g["k"].astype(int)

    # Lo vendido, repartido con el POS. Nunca más de lo que el kardex
    # descontó; lo que el POS no explica es lo servido dentro de combos.
    r = reparto_venta(vend, mapa_descargo(recetaventa, carta, recetabase), per)
    g = g.merge(r, on=["cod", "k"], how="left")
    for c in ("venta", "cort", "evvi"):
        g[c] = g[c].fillna(0.0)
    expl = g["venta"] + g["cort"] + g["evvi"]
    vend_q = g["vend_q"].clip(lower=0.0)
    esc = np.where(expl > vend_q, vend_q / expl.where(expl > 0, 1.0), 1.0)
    for c in ("cort", "evvi"):
        g[f"{c}_q"] = g[c] * esc
    g["combos_q"] = (vend_q - g["venta"] * esc - g["cort_q"] - g["evvi_q"]).clip(lower=0.0)
    # «venta» lleva lo vendido suelto Y lo de los combos: todo lo que el
    # kardex descontó por ventas, menos cortesías y eventos.
    g["venta_q"] = g["vend_q"] - g["cort_q"] - g["evvi_q"]
    pu = (g["vend_v"] / g["vend_q"].where(g["vend_q"].abs() > 1e-9)).fillna(0.0)
    for c in ("venta", "combos", "cort", "evvi"):
        g[f"{c}_v"] = g[f"{c}_q"] * pu
    g["venta_v"] = g["vend_v"] - g["cort_v"] - g["evvi_v"]

    # Las otras salidas: las notas del kardex sin las bajas. Una baja que el
    # kardex todavía no tiene (el parquet de salidas es más nuevo) no deja
    # «otras» negativas.
    for s in ("q", "v"):
        g[f"otras_{s}"] = (g[f"notas_{s}"] - g[f"baja_{s}"]).clip(lower=0.0)
        g[f"falt_{s}"] = (-g[f"aj_{s}"]).clip(lower=0.0)
        g[f"sobr_{s}"] = g[f"aj_{s}"].clip(lower=0.0)
        g[f"plato_{s}"] = g[f"venta_{s}"] + g[f"cort_{s}"] + g[f"evvi_{s}"]
        g[f"sinplato_{s}"] = g[f"baja_{s}"] + g[f"otras_{s}"] + g[f"falt_{s}"]
        g[f"salio_{s}"] = g[f"plato_{s}"] + g[f"prep_{s}"] + g[f"sinplato_{s}"]
    g["pct"] = (g["sinplato_v"] / g["salio_v"]).where(g["salio_v"] > 0.5)

    mae = _maestro(maestro)
    g = g.merge(mae, on="cod", how="left")
    g["producto"] = g["producto"].fillna(g["cod"])
    g["unidad"] = g["unidad"].fillna("")
    g["familia"] = g["familia"].fillna("")
    g["clase"] = np.where(g["familia"].str.upper() == FAMILIA_OPERACION,
                          OPERACION, ALIMENTOS)
    # Sin nada que contar: ni movimiento ni stock en ninguna punta.
    vivo = (g[["entro_v", "salio_v", "aj_v", "ini_v", "fin_v",
               "entro_q", "salio_q", "ini_q", "fin_q",
               "otros_ing_v", "otros_sal_v"]].abs() > 1e-9).any(axis=1)
    g = g[vivo].reset_index(drop=True)
    return {"periodos": per, "filas": g, "totales": totales(g, len(per))}


TOTALES = ("compras", "venta", "combos", "cort", "evvi", "baja", "otras",
           "falt", "sobr", "operacion", "ini", "fin", "valorizacion",
           "n_alimentos", "n_sinplato", "n_operacion")


def totales(filas, n_periodos):
    """La cuenta del restaurante por período, en soles:

        compras = a un plato (venta + cortesía + eventos) + bajas + otras
                  + faltante neto + insumos de operación + Δ stock
                  + valorización

    La valorización es lo que no explica ningún movimiento: el precio
    promedio que cambia mientras el producto está en stock (regla #602), y
    la diferencia de valor entre lo que entra y sale de una preparación.
    `falt`/`sobr` son de alimentos y bebidas; los insumos de operación van
    netos en `operacion`. Pura."""
    filas_out = []
    for k in range(n_periodos):
        h = filas[filas["k"] == k] if not filas.empty else filas
        a = h[h["clase"] == ALIMENTOS] if not h.empty else h
        o = h[h["clase"] == OPERACION] if not h.empty else h

        def s(df, c):
            return float(df[c].sum()) if not df.empty else 0.0
        t = {"k": k, "compras": s(h, "compra_v"), "venta": s(h, "venta_v"),
             "combos": s(h, "combos_v"), "cort": s(h, "cort_v"),
             "evvi": s(h, "evvi_v"), "baja": s(h, "baja_v"),
             "otras": s(h, "otras_v"), "falt": s(a, "falt_v"),
             "sobr": s(a, "sobr_v"), "operacion": -s(o, "aj_v"),
             "ini": s(h, "ini_v"), "fin": s(h, "fin_v"),
             "n_alimentos": int(((a["salio_v"].abs() + a["entro_v"].abs()) > 0.5).sum())
             if not a.empty else 0,
             "n_sinplato": int((a["sinplato_v"] > 0.5).sum()) if not a.empty else 0,
             "n_operacion": int((o["aj_v"] < -0.5).sum()) if not o.empty else 0}
        t["valorizacion"] = (t["compras"] - t["venta"] - t["cort"] - t["evvi"]
                             - t["baja"] - t["otras"] - (t["falt"] - t["sobr"])
                             - t["operacion"] - (t["fin"] - t["ini"]))
        filas_out.append(t)
    return pd.DataFrame(filas_out, columns=["k", *TOTALES])


# ═══════════════════════════════════════════════════════════════════════
# LO QUE LEEN LAS VISTAS
# ═══════════════════════════════════════════════════════════════════════

def pct_previo(filas, k, n=CIERRES_ATRAS):
    """El % sin plato de cada producto en los `n` cierres anteriores a `k`,
    sumados (sin plato ÷ salió, en soles): Series `cod` → fracción, sin los
    que no salieron nada. Pura."""
    h = filas[(filas["k"] < k) & (filas["k"] >= k - n)]
    if h.empty:
        return pd.Series(dtype=float)
    g = h.groupby("cod")[["sinplato_v", "salio_v"]].sum()
    return (g["sinplato_v"] / g["salio_v"]).where(g["salio_v"] > 0.5).dropna()


def sin_salida_registrada(filas):
    """Máscara: productos que en el período no tuvieron NINGUNA salida con
    documento —ni plato, ni preparación, ni nota— y sí faltante. Todo su uso
    aparece recién al contar. Pura."""
    reg = (filas["plato_q"].abs() + filas["prep_q"].abs()
           + filas["baja_q"].abs() + filas["otras_q"].abs())
    return (reg < 1e-9) & (filas["aj_q"] < -1e-9)


_SIN_PESO = {"del", "con", "para", "und", "por", "los", "las"}


def palabra_clave(nombre):
    """La primera palabra que dice QUÉ es un producto, sin el prefijo entre
    paréntesis ni conectores: «(P) Lomo trozos saltado 170gr» → «lomo»."""
    import re
    s = re.sub(r"\([^)]*\)", " ", str(nombre)).lower()
    for w in re.split(r"[^a-záéíóúñü]+", s):
        if len(w) > 2 and w not in _SIN_PESO:
            return w
    return ""


def parejas(filas_k, cod, n=2, minimo=20.0):
    """Los productos del mismo período, del mismo rubro por su
    `palabra_clave`, con el ajuste de signo CONTRARIO al de `cod`: un
    faltante en uno y un sobrante en otro suelen ser una receta o un conteo
    con el código del otro (el Lomo Saltado descarga medallón y la cocina
    porciona trozos: cierre de setiembre 2026, trozos −98 und, medallón
    +261,5). Una pista, no una conclusión. Pura."""
    f = filas_k[filas_k["cod"] == cod]
    if f.empty:
        return filas_k.iloc[0:0]
    aj = float(f["aj_v"].iloc[0])
    clave = palabra_clave(f["producto"].iloc[0])
    if not clave or abs(aj) < minimo:
        return filas_k.iloc[0:0]
    c = filas_k[(filas_k["cod"] != cod) & (filas_k["clase"] == ALIMENTOS)]
    # Primero el ajuste y la palabra suelta, vectorizados: la expresión
    # regular de `palabra_clave` sobre los 860 nombres de un cierre eran
    # 0,7 s por clic.
    c = c[(np.sign(c["aj_v"]) == -np.sign(aj)) & (c["aj_v"].abs() >= minimo)
          & c["producto"].str.lower().str.contains(clave, regex=False)]
    c = c[c["producto"].map(palabra_clave) == clave]
    return c.reindex(c["aj_v"].abs().sort_values(ascending=False).index).head(n)
