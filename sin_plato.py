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

VERSION = 7
"""Va en la clave de la caché de disco (que no caduca): subirla cuando
cambie QUÉ se calcula. La 2: las líneas que se descargan por insumo bajan
por su receta base (regla #648). La 3 conserva el desglose por tipo del
Sankey; no cambia las columnas de la cuenta original. La 4 agrega el reloj
operativo y el balance por área (regla #743); el reloj del kardex da lo
mismo que la 3. La 5: el corte lo ponen sólo las áreas que contaron
stock, y Destino queda sólo con el reloj operativo (regla #750) —el número
no se subió en ese commit—. La 6: el cierre físico, el mes calendario con
lo digitado hasta la apertura y las ventas del día 1 en su mes (regla
#752). La 7: las compras del mes nuevo procesadas antes de la apertura,
también en su mes (regla #753)."""

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
    `cierre_ant` (los días de los dos conteos), `sesion` (la del cierre) y
    `sesion_ant` (la del cierre anterior: de ahí arrancan las ventanas por
    área del reloj operativo, `periodos_operativos`).

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
            "sesion": b, "sesion_ant": a,
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


def _periodo_de(fechas, per, fisico=False):
    """El `k` de cada fecha (NaN fuera de todos los períodos). Con
    `fisico`, por el mes físico (`c0`/`c1`, regla #752): lo VENDIDO cae en
    el mes en que pasó; lo REGISTRADO (una nota, el proceso de una baja), en
    el cierre que lo abarca hasta la apertura."""
    if not per:
        return pd.Series(np.nan, index=fechas.index)
    a, z = ("c0", "c1") if fisico and "c0" in per[0] else ("t0", "t1")
    bordes = [p[a] for p in per] + [per[-1][z]]
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
                      "k": _periodo_de(vend["dia"], per, fisico=True)}).dropna(subset=["k"])
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
             recetabase=None, stock=None):
    """Todo lo que dibujan las dos vistas: `{"periodos", "filas",
    "totales"}`. `recetabase` abre las líneas que se descargan por insumo
    (`mapa_descargo`, regla #648). `stock` es lo de `stock_por_area` (el
    stock de cada área en SU corte, regla #743); sin él, las fotos se sacan
    al final del día de cada período (`momentos`), como siempre.

    `filas`: una por (`cod`, `k`) con algún movimiento o stock, con
    `producto`, `unidad`, `familia`, `clase` (ALIMENTOS u OPERACION) y cada
    una de `PARTES` en `_q` y `_v` (salvo `compra`, sólo `_v`), más
    `falt`, `sobr`, `plato`, `sinplato` y `salio` en las dos medidas y
    `pct` (sin plato ÷ salió, en soles; NaN si no salió nada).

    `totales`: una por `k`, en soles, la cuenta del restaurante —ver
    `totales`—. Pura."""
    per = list(per or [])
    m = movimientos(kx)
    if stock is not None:
        s = stock.groupby(["punta", "k", "cod"], as_index=False)[["q", "v"]].sum()
        ini = s[s["punta"] == "ini"].drop(columns="punta").rename(
            columns={"q": "ini_q", "v": "ini_v"})
        fin = s[s["punta"] == "fin"].drop(columns="punta").rename(
            columns={"q": "fin_q", "v": "fin_v"})
    else:
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


# ═══════════════════════════════════════════════════════════════════════
# EL RELOJ OPERATIVO Y EL BALANCE POR ÁREA (regla #743)
# ═══════════════════════════════════════════════════════════════════════
#
# Con el reloj del KARDEX el período va del día siguiente al último conteo
# del cierre anterior al último conteo de este, a las 23:59, para todo el
# restaurante. Si una sola área se cuenta días después que las demás (Venta
# Interna, el 6 oct 2026, cuando las otras doce se contaron el 1 oct a las
# 17:35), el período de todas arrastra esos días: setiembre 2026 traía
# S/ 20.156 de compras de octubre y un stock final con esas compras y sin
# sus ventas (el descargo no corre entre el conteo y el fin del cierre).
#
# Con el reloj OPERATIVO cada área se corta en la hora de SU conteo. El
# ajuste (93) entra al kardex en la misma hora en que se abre el conteo
# (medido en todos los cierres de jun–set 2026), así que esa hora, cerrada,
# es el corte. Lo vendido antes de un conteo y descontado después (o nunca:
# el último día del mes, regla #650) se pasa al período de la venta con el
# paloteo; su contrapartida está en el ajuste.
#
# Desde la regla #750 el corte lo ponen sólo las áreas que CONTARON STOCK
# en ese cierre (`areas_con_stock`). Venta Interna, Cocina Personal, Eventos
# o Bajas de Almacén registran su conteo —a veces días después: Venta
# Interna el 6 oct 2026— pero no guardan mercadería: su conteo no mide nada
# en el borde y sólo estiraba el mes. Toman el corte de la mayoría; su
# ajuste sigue siendo del cierre. La regla mira el VALOR contado, no el
# nombre: Limpieza contó S/ 5.500 en julio 2026 y S/ 0 en setiembre.
# Destino usa sólo este reloj: el del kardex (días enteros hasta el último
# conteo de la sesión) era un tercer «setiembre», del 3 set al 6 oct.

RELOJES = ("operativo",)
_HORA = pd.Timedelta(hours=1)


def cortes_de_conteo(sesion, ajustes):
    """`{área: corte}` de una sesión de conteo: la hora siguiente al último
    ajuste (93) de cada área en los días de la sesión. `ajustes` es un
    DataFrame (`area`, `f`) con las horas del kardex en que hubo un 93.
    Pura."""
    if ajustes is None or ajustes.empty or not sesion:
        return {}
    dias = {pd.Timestamp(d).date() for d in sesion.get("dias", ())}
    f = pd.to_datetime(ajustes["f"])
    a = ajustes.assign(f=f)[f.dt.date.isin(dias)]
    if a.empty:
        return {}
    return {int(area): pd.Timestamp(t) + _HORA
            for area, t in a.groupby("area")["f"].max().items()}


def _corte_principal(cortes, respaldo):
    """El corte de la mayoría de las áreas (el más temprano si empatan): el
    que marca el período para lo que no es de un área."""
    if not cortes:
        return pd.Timestamp(respaldo)
    cuenta = pd.Series(list(cortes.values())).value_counts()
    return min(cuenta[cuenta == cuenta.max()].index)


def areas_con_stock(contado, sesiones):
    """`{clave de sesión: {área}}`: las áreas que contaron stock en cada
    sesión. `contado` es un DataFrame (`area` entero, `dia`, `v`) con el
    valor contado por área y día (`VALORIZADO TOTAL` de
    `ajusteinventario.parquet`); cuenta el área cuyo valor en los días de
    la sesión pasa S/ 0,50, como el inventario de Costos. Regla #750. Pura."""
    if contado is None or contado.empty:
        return {}
    c = contado.assign(dia=pd.to_datetime(contado["dia"]).dt.date,
                       v=_num(contado["v"]))
    out = {}
    for s in sesiones or []:
        dias = {pd.Timestamp(d).date() for d in s.get("dias", ())}
        v = c[c["dia"].isin(dias)].groupby("area")["v"].sum()
        out[s["clave"]] = {int(a) for a, x in v.items() if abs(x) > 0.5}
    return out


def _con_stock(cortes, sesion, con_stock):
    """Los `cortes` de las áreas que contaron stock en `sesion`. Sin el
    dato de esa sesión, todos."""
    if con_stock is None or not sesion or sesion.get("clave") not in con_stock:
        return cortes
    validas = con_stock[sesion["clave"]]
    return {a: t for a, t in cortes.items() if a in validas}


def periodos_operativos(per, ajustes, areas, con_stock=None):
    """Los períodos de `periodos` con el reloj operativo: cada uno con
    `ventanas` (`{área: (t0, t1)}`, cada área de su APERTURA a la siguiente:
    lo que el kardex registró antes de abrir el conteo es del cierre) y
    `t0`/`t1` en la apertura de la mayoría. El área que no se contó en un
    cierre —o que contó sin stock, con `con_stock` de `areas_con_stock`,
    regla #750— toma la de la mayoría.

    Desde la regla #752 el período es el mes FÍSICO: el conteo se hace el
    día 1 por la mañana y es el stock al cierre del mes; la apertura llega
    después, cuando se terminó de digitar lo atrasado. `c0`/`c1` son el
    1 del mes y el 1 del siguiente; `desde`/`hasta` y `dias` (30 en
    setiembre 2026), los de ese mes. Pura."""
    out = []
    for p in per:
        ca = _con_stock(cortes_de_conteo(p.get("sesion_ant"), ajustes),
                        p.get("sesion_ant"), con_stock)
        cb = _con_stock(cortes_de_conteo(p.get("sesion"), ajustes),
                        p.get("sesion"), con_stock)
        t0 = _corte_principal(ca, p["t0"])
        t1 = _corte_principal(cb, p["t1"])
        vent = {int(a): (ca.get(int(a), t0), cb.get(int(a), t1)) for a in areas}
        # El cierre FÍSICO (regla #752): el mes calendario del cierre. Sin
        # `mes` (un período armado a mano), el de las aperturas.
        c0, c1 = t0, t1
        if p.get("mes"):
            y, m = p["mes"]
            c0 = pd.Timestamp(int(y), int(m), 1)
            c1 = c0 + pd.offsets.MonthBegin(1)
        fis = bool(p.get("mes"))
        out.append(dict(p, t0=t0, t1=t1, c0=c0, c1=c1, ventanas=vent, reloj="operativo",
                        desde=c0.date(),
                        hasta=((c1 - pd.Timedelta(days=1)) if fis else (t1 - _HORA)).date(),
                        dias=(c1 - c0) / pd.Timedelta(days=1)))
    return out


def ventanas(per, areas):
    """`(k, area, t0, t1)` de cada período y área, `t1` exclusivo: las del
    reloj operativo si el período las trae, si no la del período entero para
    todas (el reloj del kardex). Pura."""
    filas = []
    for p in per:
        v = p.get("ventanas") or {}
        for a in areas:
            t0, t1 = v.get(int(a), (p["t0"], p["t1"]))
            filas.append((int(p["k"]), int(a), pd.Timestamp(t0), pd.Timestamp(t1)))
    return pd.DataFrame(filas, columns=["k", "area", "t0", "t1"])


# ═══════════════════════════════════════════════════════════════════════
# EL CIERRE FÍSICO (regla #752)
# ═══════════════════════════════════════════════════════════════════════
#
# El conteo se hace el día 1 por la mañana, antes de que haya movimientos:
# es el stock al cierre del mes. La APERTURA del conteo en el sistema llega
# después (el día 1 por la tarde, el 2 o el 3), cuando se terminó de digitar
# lo atrasado —producción, porcionamientos, notas, requerimientos—, que es
# del mes que cerró. Y el POS calcula el ajuste contra el stock del sistema
# EN LA APERTURA (medido: 8 de 8 aperturas, todos los productos movidos).
#
# Lo único del mes NUEVO que puede registrarse antes de la apertura es el
# descargo de ventas: la corrida del 1 jul 2026 a las 23:15 descontó lo
# vendido el 1 de julio, y Cocina abrió el 2 a las 17:33. Esa venta queda en
# la ventana del cierre que se abrió y, como el ajuste se calculó después,
# reaparece como sobrante del cierre; en el mes siguiente vuelve como
# faltante. `cierre_fisico` la pasa a su mes y corrige los dos ajustes.
# Desde la regla #753 también las COMPRAS del mes nuevo procesadas antes de
# la apertura (`compras_del_mes_nuevo`, con la `FECHA_PROCESO_DOC` que el
# Sheet agregó a `compras.parquet`): el 1 oct 2026, S/ 1.022 en facturas de
# octubre procesadas antes de las 17:44.

CORTE_TURNO = pd.Timedelta(hours=6)
"""Lo vendido hasta las 6 de la mañana del día 1 es del turno del último
día del mes: se contó después."""


def bordes_fisicos(per):
    """`(k, area, c, t)`: de cada período, el tramo entre el fin del mes
    físico (`c1`) y la apertura de cada área (el fin de su ventana), donde
    el kardex puede traer descargos del mes nuevo. Pura."""
    out = []
    for p in per:
        if "c1" not in p:
            continue
        c = pd.Timestamp(p["c1"])
        for a, (_t0, t1) in sorted((p.get("ventanas") or {}).items()):
            if pd.Timestamp(t1) > c:
                out.append((int(p["k"]), int(a), c, pd.Timestamp(t1)))
    return out


def ventas_del_mes_nuevo(desc, corridas, pedidos):
    """La parte de cada descargo (95) registrado entre el fin de un mes y la
    apertura de su área que descontó ventas del mes NUEVO. `desc`: (`k`, el
    período que cierra ese conteo; `area`, `cod`, `h` la hora del kardex,
    `c` el 1 del mes nuevo; `cant_in`, `cant_out`, `val_in`, `val_out`).
    `corridas`: (`ini`, `desde`, `hasta`), el calendario del descargo;
    `pedidos`: (`t`, `costo`), lo vendido por hora de pedido. La parte es la
    del costo que la corrida cubrió vendido desde el día 1 a las 6; sin
    corrida en esa hora, nada (se queda en el cierre). Devuelve `desc` con
    los montos multiplicados por esa parte, sin las filas en cero. Pura."""
    cols = ["k", "area", "cod", "cant_in", "cant_out", "val_in", "val_out"]
    if desc is None or desc.empty or corridas is None or corridas.empty:
        return pd.DataFrame(columns=cols)
    p = pd.DataFrame({"t": pd.to_datetime(pedidos["t"]), "c": _num(pedidos["costo"])}) \
        if pedidos is not None and not pedidos.empty else pd.DataFrame(columns=["t", "c"])
    co = pd.DataFrame({"ini": pd.to_datetime(corridas["ini"]),
                       "desde": pd.to_datetime(corridas["desde"]),
                       "hasta": pd.to_datetime(corridas["hasta"])}).dropna()
    co["h"] = co["ini"].dt.floor("h")
    parte = {}
    for (h, c), _g in desc.groupby(["h", "c"]):
        rs = co[co["h"] == pd.Timestamp(h)]
        tot = nuevo = 0.0
        for r in rs.itertuples(index=False):
            en = p[(p["t"] >= r.desde) & (p["t"] <= r.hasta)]
            tot += float(en["c"].sum())
            nuevo += float(en.loc[en["t"] >= pd.Timestamp(c) + CORTE_TURNO, "c"].sum())
        parte[(pd.Timestamp(h), pd.Timestamp(c))] = nuevo / tot if tot > 0 else 0.0
    d = desc.copy()
    f = np.array([parte.get((pd.Timestamp(h), pd.Timestamp(c)), 0.0)
                  for h, c in zip(d["h"], d["c"])])
    for col in ("cant_in", "cant_out", "val_in", "val_out"):
        d[col] = _num(d[col]) * f
    d = d[f > 1e-9]
    if d.empty:
        return pd.DataFrame(columns=cols)
    d = d.assign(cod=_cod(d["cod"]), k=d["k"].astype(int), area=d["area"].astype(int))
    return d.groupby(["k", "area", "cod"], as_index=False)[cols[3:]].sum()[cols]


AREA_ALMACEN = 0
"""El Almacén Central: las compras entran al kardex por él."""


def compras_del_mes_nuevo(compras, bordes):
    """Las compras del mes NUEVO que el Almacén procesó antes de abrir el
    conteo: factura emitida desde el día 1 (la regla del Almacén es la fecha
    de emisión) y procesada entre el 1 y la apertura del Almacén Central
    (`FECHA_PROCESO_DOC`, la hora en que entró al kardex). `compras` son las
    líneas de `compras.parquet` SIN las notas de crédito (el kardex las
    registra aparte); `bordes`, lo de `bordes_fisicos`. Devuelve (`k`,
    `area`, `cod`, `tipo` «01», `cant_in`, `cant_out`, `val_in`, `val_out`)
    para `cierre_fisico`. Sin la columna de proceso, nada. Regla #753. Pura."""
    cols = ["k", "area", "cod", "tipo", "cant_in", "cant_out", "val_in", "val_out"]
    c_cod, c_em = _col(compras, "COD_PRODUCTO"), _col(compras, "FECHA_EMISION_DOC")
    c_pr, c_q = _col(compras, "FECHA_PROCESO_DOC"), _col(compras, "CANTIDAD_COMPRA")
    c_v = _col(compras, "VALOR_COMPRA")
    if compras is None or compras.empty or not all((c_cod, c_em, c_pr, c_q, c_v)):
        return pd.DataFrame(columns=cols)
    em = pd.to_datetime(compras[c_em], errors="coerce").dt.normalize()
    pr = pd.to_datetime(compras[c_pr], errors="coerce")
    partes = []
    for k, a, c, t in bordes or []:
        if int(a) != AREA_ALMACEN:
            continue
        c, t = pd.Timestamp(c), pd.Timestamp(t)
        m = (em >= c.normalize()) & (pr >= c) & (pr < t)
        if m.any():
            partes.append(pd.DataFrame({
                "k": int(k), "area": int(a), "cod": _cod(compras.loc[m, c_cod]), "tipo": "01",
                "cant_in": _num(compras.loc[m, c_q]), "cant_out": 0.0,
                "val_in": _num(compras.loc[m, c_v]), "val_out": 0.0}))
    if not partes:
        return pd.DataFrame(columns=cols)
    return (pd.concat(partes, ignore_index=True)
            .groupby(["k", "area", "cod", "tipo"], as_index=False)[cols[4:]].sum()[cols])


def cierre_fisico(kx, nuevas, n_periodos):
    """`kx` (lo de `kardex.sql_movimientos_ventanas`) con las ventas del mes
    nuevo (`ventas_del_mes_nuevo`) en su mes: el descargo sale del período
    `k` y entra al `k + 1`, y el ajuste (93) se corrige en los dos —en `k`
    vuelve el faltante que el POS borró al ajustar contra el sistema en la
    apertura; en `k + 1` se le quita el que le cargó—. La foto de cada punta
    (lo contado) no cambia, y cada período sigue cerrando contra el kardex.
    Lo que cae fuera de `0 … n_periodos − 1` se descarta: un `k` de −1 en
    `nuevas` es el borde de ANTES del primer período (sólo entra a él); lo
    que pasa al siguiente del último es del mes en curso. `kx` lleva `k`;
    el `area` de lo agregado es entera. Pura."""
    if nuevas is None or nuevas.empty or kx is None:
        return kx
    n = nuevas.assign(cod=_cod(nuevas["cod"]))
    # El tipo de lo que se mueve: el descargo de ventas (95) o, desde la
    # regla #753, la compra (lo de `compras_del_mes_nuevo`, «01»).
    tipo = n["tipo"] if "tipo" in n.columns else pd.Series(TIPO_VENTAS, index=n.index)
    m = ("cant_in", "cant_out", "val_in", "val_out")

    def filas(k, tipo, signo, cruzado):
        orden = ("cant_out", "cant_in", "val_out", "val_in") if cruzado else m
        x = pd.DataFrame({"k": k, "area": n["area"].astype(int), "cod": n["cod"], "tipo": tipo})
        for dest, src in zip(m, orden):
            x[dest] = signo * _num(n[src])
        return x
    extra = pd.concat([
        filas(n["k"], tipo, -1.0, False),             # el movimiento sale del cierre…
        filas(n["k"], TIPO_AJUSTE, 1.0, False),       # …y su ajuste vuelve al físico
        filas(n["k"] + 1, tipo, 1.0, False),          # entra al mes en que pasó…
        filas(n["k"] + 1, TIPO_AJUSTE, 1.0, True),    # …sin el ajuste que le cargó
    ], ignore_index=True)
    extra = extra[(extra["k"] >= 0) & (extra["k"] < n_periodos)]
    return pd.concat([kx, extra[[c for c in extra.columns if c in kx.columns]]],
                     ignore_index=True)


def stock_por_area(fotos, ven):
    """El stock de cada producto en cada área al empezar y al terminar cada
    período (`punta` «ini»/«fin», `k`, `area`, `cod`, `q`, `v`): la foto
    del kardex en la última hora ANTES del corte de esa área. La regla de
    la foto es la de `stock_en_momentos` (el movimiento de mayor
    correlativo); con las ventanas del reloj del kardex, sumada por
    producto, da lo mismo que ella. Pura."""
    vacio = pd.DataFrame(columns=["punta", "k", "area", "cod", "q", "v"])
    if fotos is None or fotos.empty or ven is None or ven.empty:
        return vacio
    st_ = _num(fotos["stock"])
    f = pd.DataFrame({
        "area": pd.to_numeric(fotos["area"], errors="coerce"),
        "cod": _cod(fotos["cod"]),
        "fecha": pd.to_datetime(fotos["fecha"], errors="coerce"),
        "correlativo": pd.to_numeric(fotos["correlativo"], errors="coerce"),
        "q": st_, "v": st_ * _num(fotos["precio"]),
    }).dropna(subset=["fecha", "area"])
    f["area"] = f["area"].astype(int)
    # En orden de fecha, cada fila apunta a la de MAYOR correlativo vista
    # hasta ella en su área y producto: la foto en un instante es la fila a
    # la que apunta la última anterior a él. Así un movimiento cargado con
    # fecha atrasada (correlativo mayor, fecha menor) manda, como en
    # `stock_en_momentos`, sin recorrer instante por instante.
    f = f.sort_values(["area", "cod", "fecha", "correlativo"], kind="stable").reset_index(drop=True)
    grupo = [f["area"], f["cod"]]
    tope = f["correlativo"].fillna(-np.inf).groupby(grupo).cummax()
    pos = pd.Series(np.where(f["correlativo"].fillna(-np.inf) >= tope, np.arange(len(f)), np.nan))
    f["pos"] = pos.groupby(grupo).ffill()
    usos = pd.concat([ven[["k", "area", "t0"]].rename(columns={"t0": "t"}).assign(punta="ini"),
                      ven[["k", "area", "t1"]].rename(columns={"t1": "t"}).assign(punta="fin")],
                     ignore_index=True)
    pares = f[["area", "cod"]].drop_duplicates()
    # merge_asof exige la misma resolución de fecha en los dos lados (DuckDB
    # entrega microsegundos y un Timestamp suelto, nanosegundos).
    izq = usos.merge(pares, on="area")
    izq["t"] = pd.to_datetime(izq["t"]).astype("datetime64[ns]")
    izq = izq.sort_values("t", kind="stable")
    der = f[["area", "cod", "fecha", "pos"]].assign(
        fecha=f["fecha"].astype("datetime64[ns]")).sort_values("fecha", kind="stable")
    m = pd.merge_asof(izq, der, left_on="t", right_on="fecha", by=["area", "cod"],
                      direction="backward", allow_exact_matches=False).dropna(subset=["pos"])
    if m.empty:
        return vacio
    filas = f.loc[m["pos"].astype(int).to_numpy(), ["q", "v"]].reset_index(drop=True)
    out = m[["punta", "k", "area", "cod"]].reset_index(drop=True).join(filas)
    out["k"] = out["k"].astype(int)
    return out[["punta", "k", "area", "cod", "q", "v"]]


def ventas_del_borde(pedidos, corridas, per):
    """Por período (`k`, `fin`, `ini`, `nunca`, en soles al costo del
    paloteo): `fin` es lo vendido dentro del período y descontado después
    de su corte o nunca —el descargo de ventas se corre a mano por la
    mañana y no corre entre el conteo y el fin del cierre—; `ini`, lo
    vendido antes de su comienzo y descontado dentro; `nunca`, la parte de
    `fin` que ninguna corrida tomó (el último día del mes, regla #650).

    `pedidos`: (`t`, `costo`), el costo de lo vendido por hora de pedido;
    `corridas`: (`ini`, `desde`, `hasta`), el calendario del descargo
    (`descargosventas.parquet`). Una venta la descuenta la primera corrida
    que la cubre y empieza después de ella. Pura."""
    cols = ["k", "fin", "ini", "nunca"]
    if pedidos is None or pedidos.empty or not per:
        return pd.DataFrame([(p["k"], 0.0, 0.0, 0.0) for p in per], columns=cols)
    p = pd.DataFrame({"t": pd.to_datetime(pedidos["t"]), "c": _num(pedidos["costo"])})
    p = p.dropna(subset=["t"]).sort_values("t", kind="stable").reset_index(drop=True)
    desc = pd.Series(pd.NaT, index=p.index, dtype="datetime64[ns]")
    if corridas is not None and not corridas.empty:
        c = pd.DataFrame({"ini": pd.to_datetime(corridas["ini"]),
                          "desde": pd.to_datetime(corridas["desde"]),
                          "hasta": pd.to_datetime(corridas["hasta"])}).dropna()
        for r in c.sort_values("ini", kind="stable").itertuples(index=False):
            m = desc.isna() & (p["t"] >= r.desde) & (p["t"] <= r.hasta) & (p["t"] <= r.ini)
            desc[m] = r.ini
    out = []
    for q in per:
        a, z = pd.Timestamp(q["t0"]), pd.Timestamp(q["t1"])
        # Desde la regla #752 lo VENDIDO se mira por el mes físico (hasta las
        # 6 del día 1) y lo DESCONTADO, por la apertura: lo vendido el día 1
        # antes de abrir el conteo ya no pasa al cierre anterior.
        va, vz = ((pd.Timestamp(q["c0"]) + CORTE_TURNO, pd.Timestamp(q["c1"]) + CORTE_TURNO)
                  if "c0" in q else (a, z))
        dentro = (p["t"] >= va) & (p["t"] < vz)
        tarde = desc.isna() | (desc >= z)
        out.append((q["k"], float(p.loc[dentro & tarde, "c"].sum()),
                    float(p.loc[(p["t"] < va) & (desc >= a) & (desc < z), "c"].sum()),
                    float(p.loc[dentro & desc.isna(), "c"].sum())))
    return pd.DataFrame(out, columns=cols)


def _tops(serie, nombres, n=4):
    """`[total, cuántos, [[nombre, valor], …]]` de una Series código → soles
    (sólo lo positivo), los `n` que más pesan."""
    s = serie[serie > 0.5].sort_values(ascending=False)
    return [round(float(s.sum()), 2), int(len(s)),
            [[str(nombres.get(c, c)), round(float(v), 2)] for c, v in s.head(n).items()]]


_COLS_AREA = ("ini", "fin", "fin_neg", "compra", "req_in", "req_out", "tr_in", "tr_out",
              "prod_in", "prod_out", "venta", "notas", "aj_pos", "aj_neg", "val")
"""El orden de los números de cada área en `por_area` (y en el `.js`)."""


def _traslados(trans, ven, clase):
    """Los requerimientos y transferencias con su período: la fila es del
    área que la registró —la que envía, salvo lo que sale del Almacén
    Central, que registra quien recibe— y cae en la ventana de esa área."""
    cols = ["k", "tipo", "o", "d", "cod", "v", "doc", "clase"]
    if trans is None or trans.empty or ven is None or ven.empty:
        return pd.DataFrame(columns=cols)
    t = pd.DataFrame({"tipo": _cod(trans["tipo"]), "t": pd.to_datetime(trans["t"], errors="coerce"),
                      "o": pd.to_numeric(trans["o"], errors="coerce"),
                      "d": pd.to_numeric(trans["d"], errors="coerce"),
                      "cod": _cod(trans["cod"]), "v": _num(trans["v"]),
                      "doc": _cod(trans["doc"])}).dropna(subset=["t", "o", "d"])
    t["o"], t["d"] = t["o"].astype(int), t["d"].astype(int)
    dueno = np.where(t["o"] == 0, t["d"], t["o"])
    t["k"] = -1
    for w in ven.itertuples(index=False):
        t.loc[(dueno == w.area) & (t["t"] >= w.t0) & (t["t"] < w.t1), "k"] = w.k
    t = t[t["k"] >= 0]
    t["clase"] = t["cod"].map(clase).fillna(ALIMENTOS)
    return t[cols]


def por_area(kx, stock, trans, ven, clase, nombres):
    """El balance de cada área, las flechas entre áreas y lo que se compensa
    entre ellas, por período: `{clase: [por cada k: {"areas", "flechas",
    "detalle", "compensa"}]}`, con `clase` ALIMENTOS u OPERACION.

    `kx`: lo del kardex por (`k`, `area`, `cod`, `tipo`) con los traslados
    (97/99) incluidos; `stock`: lo de `stock_por_area`; `trans`: cada
    requerimiento y transferencia de `transferencias.parquet` (`tipo`, `t`,
    `o`, `d`, `cod`, `v`, `doc`), que dice el ORIGEN y el DESTINO que el
    kardex por área pierde; `ven`: las ventanas de `ventanas`; `clase`:
    código → clase; `nombres`: código → nombre.

    `areas[área]` son los números de `_COLS_AREA`. El ajuste va por
    producto Y área: lo que falta en un área y sobra en otra no se netea, y
    esa diferencia con el restaurante entero es `compensa`. Pura."""
    nk = int(ven["k"].max()) + 1 if ven is not None and not ven.empty else 0
    out = {ALIMENTOS: [], OPERACION: []}
    if nk == 0:
        return out
    if kx is not None and not kx.empty:
        x = pd.DataFrame({"k": pd.to_numeric(kx["k"]).astype(int),
                          "area": pd.to_numeric(kx["area"]).astype(int),
                          "cod": _cod(kx["cod"]), "tipo": _cod(kx["tipo"]),
                          "vin": _num(kx["val_in"]), "vout": _num(kx["val_out"])})
    else:
        x = pd.DataFrame({"k": [], "area": [], "cod": [], "tipo": [], "vin": [], "vout": []})
    x["clase"] = x["cod"].map(clase).fillna(ALIMENTOS)
    num = pd.to_numeric(x["tipo"], errors="coerce")
    x["grupo"] = np.select(
        [num.notna() & (num < 90), x["tipo"] == "99", x["tipo"] == "97",
         x["tipo"].isin(TIPOS_PRODUCE), x["tipo"] == TIPO_VENTAS,
         x["tipo"].isin(TIPOS_NOTAS), x["tipo"] == TIPO_AJUSTE],
        ["compra", "req", "tr", "prod", "venta", "notas", "aj"], "otro")
    if stock is not None and not stock.empty:
        s = stock.assign(cod=_cod(stock["cod"]), area=pd.to_numeric(stock["area"]).astype(int))
    else:
        s = pd.DataFrame({"punta": [], "k": [], "area": [], "cod": [], "v": []})
    s["clase"] = s["cod"].map(clase).fillna(ALIMENTOS)
    t = _traslados(trans, ven, clase)

    # Todo con UN groupby por clase, período y área (regla #537): recorrer
    # áreas y períodos filtrando el kardex entero costaba 26 s.
    g = x.groupby(["clase", "k", "area", "grupo"])[["vin", "vout"]].sum()
    g = g.unstack("grupo").fillna(0.0) if not g.empty else g

    def col(lado, grupo):
        return g[(lado, grupo)] if not g.empty and (lado, grupo) in g.columns else pd.Series(0.0, index=g.index)
    base = pd.DataFrame(index=g.index)
    base["compra"] = col("vin", "compra") - col("vout", "compra")
    base["req_in"], base["req_out"] = col("vin", "req"), col("vout", "req")
    base["tr_in"], base["tr_out"] = col("vin", "tr"), col("vout", "tr")
    base["prod_in"], base["prod_out"] = col("vin", "prod"), col("vout", "prod")
    base["venta"] = col("vout", "venta") - col("vin", "venta")
    base["notas"] = col("vout", "notas") - col("vin", "notas")
    aj = (x[x["grupo"] == "aj"].assign(n=lambda d: d["vin"] - d["vout"])
          .groupby(["clase", "k", "area", "cod"])["n"].sum())
    ajp = aj.clip(lower=0).groupby(["clase", "k", "area"]).sum()
    ajn = (-aj).clip(lower=0).groupby(["clase", "k", "area"]).sum()
    ini = s[s["punta"] == "ini"].groupby(["clase", "k", "area"])["v"].sum()
    fin = s[s["punta"] == "fin"].groupby(["clase", "k", "area"])["v"].sum()
    neg = s[(s["punta"] == "fin") & (s["v"] < 0)].groupby(["clase", "k", "area"])["v"].sum()
    idx = base.index.union(ini.index).union(fin.index).union(ajp.index)
    b = base.reindex(idx).fillna(0.0)
    b["ini"], b["fin"], b["fin_neg"] = ini.reindex(idx).fillna(0.0), fin.reindex(idx).fillna(0.0), neg.reindex(idx).fillna(0.0)
    b["aj_pos"], b["aj_neg"] = ajp.reindex(idx).fillna(0.0), ajn.reindex(idx).fillna(0.0)
    b["val"] = b["fin"] - (b["ini"] + b["compra"] + b["req_in"] - b["req_out"] + b["tr_in"] - b["tr_out"]
                           + b["prod_in"] - b["prod_out"] - b["venta"] - b["notas"] + b["aj_pos"] - b["aj_neg"])
    b = b[list(_COLS_AREA)]
    b = b[b.abs().sum(axis=1) > 0.5]

    # Lo que forma cada chip: los productos que más pesan, por grupo
    serie = x.assign(n=np.where(x["grupo"] == "prod", x["vin"], x["vout"] - x["vin"]))
    serie = serie[serie["grupo"].isin(["venta", "notas", "prod"])].groupby(
        ["clase", "k", "area", "grupo", "cod"])["n"].sum()
    partes = [serie.rename("n").reset_index().replace({"grupo": {"venta": "95", "notas": "98"}}),
              (-aj).rename("n").reset_index().assign(grupo="falta"),
              aj.rename("n").reset_index().assign(grupo="sobra")]
    det = pd.concat([p_ for p_ in partes if not p_.empty], ignore_index=True) if any(not p_.empty for p_ in partes) else pd.DataFrame()
    detalle = {}
    if not det.empty:
        det = det[det["n"] > 0.5].sort_values("n", ascending=False, kind="stable")
        claves = ["clase", "k", "area", "grupo"]
        tot = det.groupby(claves)["n"].agg(["sum", "count"])
        tot = dict(zip(tot.index, zip(tot["sum"], tot["count"])))
        # Fila por fila y no grupo por grupo: son miles de grupos de cuatro.
        for r in det.groupby(claves, sort=False).head(4).itertuples(index=False):
            clv = (r.clase, r.k, r.area, r.grupo)
            e = detalle.setdefault(clv[:3], {})
            if clv[3] not in e:
                sm, cn = tot[clv]
                e[clv[3]] = [round(float(sm), 2), int(cn), []]
            e[clv[3]][2].append([str(nombres.get(r.cod, r.cod)), round(float(r.n), 2)])

    # Las flechas entre áreas, con lo que más pesó en cada una
    flechas = {}
    if not t.empty:
        claves = ["clase", "k", "tipo", "o", "d"]
        tt = t[t["o"] != t["d"]]
        agg = tt.groupby(claves).agg(v=("v", "sum"), n=("v", "size"), docs=("doc", "nunique"))
        pc = tt.groupby([*claves, "cod"])["v"].sum().rename("n").reset_index()
        pc = pc[pc["n"] > 0.5].sort_values("n", ascending=False, kind="stable").groupby(claves, sort=False).head(4)
        tops = {}
        for r in pc.itertuples(index=False):
            tops.setdefault((r.clase, r.k, r.tipo, r.o, r.d), []).append(
                [str(nombres.get(r.cod, r.cod)), round(float(r.n), 2)])
        for clv, r in agg.iterrows():
            flechas.setdefault(clv[:2], []).append(
                [str(clv[2]), int(clv[3]), int(clv[4]), round(float(r["v"]), 2), int(r["n"]),
                 int(r["docs"]), tops.get(clv, [])])

    # Lo que faltó en un área y sobró en otra, producto por producto
    comp = {}
    if not aj.empty:
        pc = aj.rename("n").reset_index()
        pos = pc[pc["n"] > 0].groupby(["clase", "k", "cod"])["n"].sum()
        ng = -pc[pc["n"] < 0].groupby(["clase", "k", "cod"])["n"].sum()
        c = pd.concat([pos.rename("pos"), ng.rename("neg")], axis=1).fillna(0.0)
        c["comp"] = c[["pos", "neg"]].min(axis=1)
        c = c[c["comp"] > 0.5].sort_values("comp", ascending=False, kind="stable")
        primeros = c.groupby(level=["clase", "k"], sort=False).head(5)
        lados = pc[(pc["n"].abs() > 0.5)
                   & pd.MultiIndex.from_frame(pc[["clase", "k", "cod"]]).isin(primeros.index)]
        lados_d = {}
        for r in lados.sort_values("n", kind="stable").itertuples(index=False):
            lados_d.setdefault((r.clase, r.k, r.cod), []).append([int(r.area), round(float(r.n), 2)])
        lados = lados_d
        for (cl, k), h in c.groupby(level=["clase", "k"], sort=False):
            comp[(cl, k)] = {"total": round(float(h["comp"].sum()), 2), "n": int(len(h)), "tops": [
                [str(nombres.get(cod, cod)), round(float(r["comp"]), 2), lados.get((cl, k, cod), [])]
                for (_, _, cod), r in h.head(5).iterrows()]}
    falta = (-aj).clip(lower=0).groupby(["clase", "k"]).sum() if not aj.empty else pd.Series(dtype=float)
    sobra = aj.clip(lower=0).groupby(["clase", "k"]).sum() if not aj.empty else pd.Series(dtype=float)

    for cl in (ALIMENTOS, OPERACION):
        for k in range(nk):
            areas = {}
            if not b.empty and (cl, k) in b.index.droplevel("area"):
                for a, fila in b.loc[(cl, k)].iterrows():
                    areas[int(a)] = [round(float(v), 2) for v in fila]
            cmp_ = dict(comp.get((cl, k), {"total": 0.0, "n": 0, "tops": []}))
            cmp_["falta"] = round(float(falta.get((cl, k), 0.0)), 2)
            cmp_["sobra"] = round(float(sobra.get((cl, k), 0.0)), 2)
            out[cl].append({
                "areas": areas,
                "flechas": sorted(flechas.get((cl, k), []), key=lambda f: -f[3]),
                "detalle": {int(a): detalle.get((cl, k, a), {}) for a in areas},
                "compensa": cmp_})
    return out


def resumen_reloj(filas, per, borde=None):
    """La cuenta del restaurante de cada período con lo que se ve al abrir
    la vista —alimentos y bebidas que se movieron—, para comparar los dos
    relojes: `[{k, dias, compra, plato, falt, sobr, notas, fin, ini, prep,
    sinplato}]`. Con `borde` (lo de `ventas_del_borde`), lo vendido de un
    lado del conteo y descontado del otro pasa de faltante a plato. Pura."""
    b = {} if borde is None or borde.empty else {int(r.k): r for r in borde.itertuples(index=False)}
    out = []
    for p in per:
        k = p["k"]
        h = filas[(filas["k"] == k) & (filas["clase"] == ALIMENTOS)] if not filas.empty else filas
        if not h.empty:
            mov = (h["salio_v"].abs() + h["entro_v"].abs() + h["aj_v"].abs()
                   + h.get("otros_ing_v", 0).abs() + h.get("otros_sal_v", 0).abs())
            h = h[mov > 0.5]

        def s(c):
            return float(h[c].sum()) if not h.empty else 0.0
        mover = (b[k].fin - b[k].ini) if k in b else 0.0
        dias = p.get("dias")
        if dias is None:
            dias = (pd.Timestamp(p["t1"]) - pd.Timestamp(p["t0"])) / pd.Timedelta(days=1)
        out.append({"k": k, "dias": round(float(dias), 2), "compra": s("compra_v"),
                    "plato": s("plato_v") + mover, "falt": s("falt_v") - mover,
                    "sobr": s("sobr_v"), "notas": s("baja_v") + s("otras_v"),
                    "fin": s("fin_v"), "ini": s("ini_v"), "prep": s("prep_v"),
                    "sinplato": s("sinplato_v") - mover})
    return out
