"""
diferencias_ajuste — por qué no cuadra cada línea de un conteo de inventario.

La cuenta de Ajuste › «Análisis de diferencias» (regla #650), aprobada sobre
un boceto con los datos reales del cierre de setiembre 2026
(https://claude.ai/artifact/3xBmJP5pVSQpMQ7Ds5gcWo). Para cada línea con
diferencia de una sesión de inventario —un producto en un área— arma dos
cosas:

  · LAS PISTAS (opción A del boceto): de dónde puede venir el faltante o el
    sobrante, cada una «fuerte» (los números calzan o es un hecho del kardex)
    o «posible» (hay relación; hay que mirarla).
  · LA FICHA (opción B): la cuenta entre los dos conteos —contado antes +
    entró − salió = sistema, contra lo contado ahora—, entró y salió POR
    MOTIVO, de dónde viene, en qué platos y recetas está, y sus ajustes en los
    últimos cierres.

EL CONTEO ANTERIOR DE UNA LÍNEA NO ES EL CIERRE ANTERIOR. Es el último conteo
de ese producto en esa área: en el cierre de setiembre 2026, 920 de 988
líneas venían del parcial del 15–17 set, no del cierre de agosto. Con esa
fecha, «contado antes + kardex = sistema» cierra en el 97,7 % de las líneas.
La ventana va por HORA: del movimiento siguiente al conteo anterior hasta la
hora del conteo, sin los ajustes (tipo 93).

LAS RECETAS, línea por línea (regla #648): `T DESCARG` dice si la línea se
descuenta «como producto» o «por insumo» (el check «descarga por insumo» del
POS). Una receta base que va por insumo no lleva orden de producción: al
vender, el POS descuenta SUS insumos. La que va como producto sólo sale con
una orden de producción, y por eso «se vendió sin orden» es una pista. El
área de descargo de un plato es `SUBALM INS` (medido: el 100 % de los
descargos caen ahí), no `AREA PROD`.

LAS PISTAS, en el orden en que se muestran (fuertes primero):

  receta   la línea ES una receta base que los platos descargan como
           producto y no tuvo órdenes en seis meses; o una DD que algún plato
           descarga como producto
  desc     las ventas lo descontaron desde ESTA área más de lo que las recetas
           de hoy descargan desde aquí, y un plato que lo lleva se editó
           desde el conteo anterior y hoy lo descarga desde OTRA: la receta
           apuntaba a un área que no recibe el producto (#654)
  prod     falta un insumo y sobra lo que se hace con él (o al revés), por
           receta base o porcionamiento
  combo    va en un combo que se vendió y esos días no lo descontó (#651):
           fijo, falta en lo que descarga el combo; a elegir, la opción no se
           marcó en el pedido
  sunat    un SOBRANTE que nombra una factura que SUNAT registra y el Almacén
           no (`Solo SUNAT` en «Documentos SUNAT»): la mercadería llegó y la
           factura no se ingresó (#652). Por la descripción del XML, con los
           números del nombre y sin quedarse en palabras genéricas
  req      un requerimiento SIN PROCESAR del producto, de antes del conteo:
           si se entregó, el Almacén ya no lo tiene y el sistema sí (#652)
  area     el mismo producto, al revés, en otra área (traslado sin registrar)
  neg      el sistema terminó en negativo: el sobrante corrige un descargo
           que se hizo sin ingreso, no es mercadería que apareció
  rev      revierte el conteo anterior de la misma línea
  nada     no salió nada del área con un documento; y POR QUÉ, siguiendo cada
           receta que debía descontarlo (`por_que_nada`)
  nadie    ningún plato, receta base ni porcionamiento lo usa
  rubro    mismo rubro (`sin_plato.palabra_clave`), al revés, con cantidades
           que calzan. Fuerte si lo que falta no tuvo salidas y lo que sobra se
           vendió sin haber entrado: se vendió uno con el código del otro (la
           Sauvignon Blanc y la Chardonnay de Cinco Sentidos, setiembre 2026)

Recetas × lo vendido NO cuadra con el descargo del kardex (31 % de las líneas
dentro de ±10 %: canales, recetas editadas en el mes, fecha de turno). En la
ficha va como referencia («≈»), sin compararlo con el kardex.

Puro pandas, sin streamlit. Lo vigila
`test_graficos.py::_pruebas_diferencias_ajuste`; lo carga
`data.diferencias_ajuste_sesion`.
"""

from collections import defaultdict
from types import SimpleNamespace

import numpy as np
import pandas as pd

from sin_plato import palabra_clave

VERSION = 4
"""Va en la clave de la caché de disco (que no caduca): subirla cuando
cambie QUÉ se calcula."""

EPS = 0.005
"""Soles: una línea con menos de esto no tiene diferencia."""

DIAS_ATRAS = 180
"""Hasta cuántos días antes de la sesión se lee el kardex. Una línea cuyo
conteo anterior es más viejo no arma la cuenta (lo dice la ficha)."""

DIAS_TARDE = 10
"""Una orden o un porcionamiento registrado hasta estos días DESPUÉS del
conteo es un registro tardío posible."""

USOS_FICHA = 10
"""Cuántos usos (platos, recetas, porcionamientos) lleva la ficha."""

FAMILIA_OPERACION = "COSTOS PRODUCCION"

TIPOS = ("receta", "desc", "prod", "combo", "sunat", "req", "area", "rubro", "neg", "rev",
         "nada", "nadie")
"""Los tipos de pista, en el orden en que se muestran a igual fuerza. «rubro»
va antes que «neg» y «nada» desde la #651: cuando es fuerte («vendido con el
código del otro») explica por qué hay un negativo o por qué no salió nada."""

NOMBRE_TIPO = {"receta": "Receta", "desc": "Área de descargo", "prod": "Producción",
               "combo": "Combo",
               "sunat": "Factura sin ingresar", "req": "Sin procesar",
               "area": "Otra área",
               "neg": "Sistema negativo", "rev": "Revierte",
               "nada": "Nada lo descargó", "nadie": "Ninguna receta",
               "rubro": "Mismo rubro"}

NOMBRE_MOV = {"01": "Factura", "03": "Boleta", "07": "Nota de crédito",
              "46": "Guía de remisión", "57": "Doc. no domiciliado",
              "58": "Planilla de movilidad", "90": "Empacado",
              "91": "Control interno", "92": "Merma fija",
              "94": "Orden de producción", "95": "Descargo de ventas",
              "96": "Porcionamiento", "97": "Transferencia",
              "98": "Nota de salida", "99": "Requerimiento"}

_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set",
          "oct", "nov", "dic")
_UNIDADES = {"KILOS": "kg", "LITROS": "L", "UND": "und", "UNIDAD": "und",
             "GRAMOS": "g", "MILILITROS": "ml", "ROLLO": "rollo",
             "BOTELLA": "bot", "PAQUETE": "paq", "CAJA": "caja",
             "GALON": "gal", "PORCION": "porc", "BOLSA": "bolsa"}


# ═══════════════════════════════════════════════════════════════════════
# FORMATO Y LIMPIEZA
# ═══════════════════════════════════════════════════════════════════════

def _cod(s):
    """El código sin ceros a la izquierda: el ajuste los trae de 10 dígitos
    y el kardex, las recetas y las ventas, de 7."""
    return s.fillna("").astype(str).str.strip().str.lstrip("0")


def _up(s):
    return s.fillna("").astype(str).str.strip().str.upper()


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _fecha(s):
    return pd.to_datetime(s, errors="coerce")


def fecha_corta(t):
    """«16 set». Vacío sin fecha."""
    if t is None or pd.isna(t):
        return ""
    t = pd.Timestamp(t)
    return f"{t.day} {_MESES[t.month - 1]}"


def es(x, dec=2):
    """Un número como lo escribe el resto de Ajuste (`toLocaleString('es-PE')`
    en sus tablas): 1,135.8, sin ceros de más y con el menos tipográfico."""
    t = f"{abs(float(x)):,.{dec}f}"
    if dec and "." in t:
        t = t.rstrip("0").rstrip(".")
    return ("−" if float(x) < 0 and t != "0" else "") + t


def unidad(u):
    """KILOS → kg, UND → und."""
    u = str(u or "").strip().upper()
    return _UNIDADES.get(u, u.lower())


def _q(q, u):
    """+39 und / −13,36 kg."""
    return f"{'+' if q > 0 else '−'}{es(abs(q))} {u}"


def _titulo(s):
    return str(s or "").strip().title()


_VACIAS = frozenset(
    "con sin para del los las und unid unidad unidades kg kgs kilo kilos grs gramos ml lts "
    "litro litros por caja cajas bolsa paquete pqt botella bot frasco sac eirl produccion "
    "calientes frios pasteleria parrilla parrillas cocina arroces bar limpio limpia".split())
_GENERICAS = frozenset(
    "vino vinos tinto blanco rosado salsa chocolate pisco cerveza aceite queso harina azucar "
    "agua leche crema pasta papa pan sal jugo fruta carne pollo pescado whisky vodka ron gin "
    "licor huevo huevos verde rojo roja amarillo negro negra fresco fresca organico extra "
    "entero entera premium".split())


def palabras(texto):
    """`(palabras, números)` de un nombre de producto o de una línea de XML,
    para emparejarlos (#652): sin tildes, sin lo que va entre paréntesis
    («(Rs)», «(produccion)»), sin palabras vacías, y los números de dos
    cifras o más aparte (750 ml, 60 % cacao, Pisco 1615)."""
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"\([^)]*\)", " ", t)
    pal = frozenset(w for w in re.findall(r"[a-z]+", t) if len(w) >= 3 and w not in _VACIAS)
    nums = frozenset(n for n in re.findall(r"\d+", t) if len(n) >= 2)
    return pal, nums


def _misma(a, b):
    """La misma palabra, o plural y singular («terroir», «terroirs»): un prefijo
    de cinco letras solo emparejaba «membrillo» con «membresía»."""
    if a == b:
        return True
    corta, larga = sorted((a, b), key=len)
    return len(corta) >= 5 and larga.startswith(corta) and len(larga) - len(corta) <= 3


def parecido(producto, linea):
    """Qué tanto nombra una línea de XML a un producto: la parte de las
    palabras del producto que aparecen en la línea, o None si no alcanza.
    No alcanza si los NÚMEROS no coinciden (un chocolate al 60 % no es uno al
    45 %), si coinciden menos de tres cuartos de las palabras («ají amarillo
    en polvo» no es «ají amarillo»), o si todas las que coinciden son
    genéricas («vino tinto de cocina» no es «Caelum vino tinto Malbec»). Un
    producto de UNA palabra tiene que ser lo único que nombra la línea:
    «Beterraga» no es «brote de beterraga»."""
    pw, pn = producto
    dw, dn = linea
    if not pw:
        return None
    if pn and dn and not (pn & dn):
        return None
    hay = [w for w in pw if any(_misma(w, t) for t in dw)]
    if len(pw) == 1:
        p = next(iter(pw))
        if not hay or len(p) < 6 or not all(w in _GENERICAS or _misma(w, p) for w in dw):
            return None
        return 1.0
    if len(hay) < 2 or len(hay) / len(pw) < 0.75 or all(w in _GENERICAS for w in hay):
        return None
    return len(hay) / len(pw)


_UNIDAD_XML = {"unidad": "und", "botella": "und", "kg": "kg", "litro": "L", "g": "g",
               "ml": "ml", "docena": "doc", "lata": "und"}


# ═══════════════════════════════════════════════════════════════════════
# LAS LÍNEAS DE UNA SESIÓN Y SU CONTEO ANTERIOR
# ═══════════════════════════════════════════════════════════════════════

def ajuste_normalizado(ajuste):
    """El parquet de ajuste con nombres cortos: `t` (el conteo), `acod`,
    `area` (mayúsculas), `cod`, `producto`, `familia`, `subfamilia`, `u`,
    `s` (sistema), `k` (contado), `q`, `v`, `precio`."""
    a = ajuste
    out = pd.DataFrame({
        "t": _fecha(a["FECHA APERTURA INVENTARIO"]),
        "acod": pd.to_numeric(a["CODIGO AREA"], errors="coerce").fillna(-1).astype(int),
        "area": _up(a["AREA"]),
        "cod": _cod(a["CODIGO PRODUCTO"]),
        "producto": a["PRODUCTO"].fillna("").astype(str).str.strip(),
        "familia": _up(a["FAMILIA"]),
        "subfamilia": _up(a["SUBFAMILIA"]) if "SUBFAMILIA" in a.columns else "",
        # Por valor DISTINTO: sobre las 248.000 filas eran 1,3 s.
        "u": (a["UNIDAD MEDIDA"].map({x: unidad(x) for x in a["UNIDAD MEDIDA"].unique()})
              if "UNIDAD MEDIDA" in a.columns else ""),
        "s": _num(a["STOCK AL CIERRE"]),
        "k": _num(a["STOCK DECLARADO"]),
        "q": _num(a["AJUSTE"]),
        "v": _num(a["AJUSTE VALORIZADO"]),
        "precio": _num(a["PRECIO PROMEDIO"]),
    })
    return out[out["t"].notna()]


def lineas_de_sesion(a, sesion):
    """Las líneas con diferencia de la sesión (`a` normalizado), una por
    producto y área, con su conteo anterior (`t0`, `c0`, `q0`). Si una línea
    se contó dos veces en la sesión, suma el ajuste y toma el sistema del
    primer conteo y lo contado del último."""
    dias = pd.to_datetime(list(sesion["dias"]))
    en = a[a["t"].dt.normalize().isin(dias)].sort_values("t", kind="stable")
    if en.empty:
        return en.assign(id=pd.Series(dtype=int))
    L = en.groupby(["acod", "cod"], as_index=False, sort=False).agg(
        t1=("t", "max"), area=("area", "first"), producto=("producto", "first"),
        familia=("familia", "first"), subfamilia=("subfamilia", "first"),
        u=("u", "first"), s=("s", "first"), k=("k", "last"), q=("q", "sum"),
        v=("v", "sum"), precio=("precio", "last"))
    # Con cantidad aunque valgan S/ 0: un producto que nunca se compró no
    # tiene precio, y su sobrante es la otra mitad de un faltante (#651).
    # Faltante o sobrante lo dice la CANTIDAD; el monto, cuánto pesa.
    L = L[(L["v"].abs() > EPS) | (L["q"].abs() > 1e-6)].reset_index(drop=True)
    ini = pd.Timestamp(min(sesion["dias"]))
    ant = (a[a["t"] < ini].sort_values("t", kind="stable")
           .drop_duplicates(["acod", "cod"], keep="last")
           [["acod", "cod", "t", "k", "q"]]
           .rename(columns={"t": "t0", "k": "c0", "q": "q0"}))
    L = L.merge(ant, on=["acod", "cod"], how="left")
    L["id"] = np.arange(len(L), dtype=int)
    return L


# ═══════════════════════════════════════════════════════════════════════
# EL KARDEX DE CADA LÍNEA ENTRE SUS DOS CONTEOS
# ═══════════════════════════════════════════════════════════════════════

def kardex_normalizado(kardex):
    """`hora`, `acod`, `cod`, `t` (tipo), `ent`, `sal`, `movs`, `stock`, sin
    la fila del saldo inicial."""
    k = kardex
    out = pd.DataFrame({
        "hora": _fecha(k["FECHA HORA"]),
        "acod": pd.to_numeric(k["CODIGO AREA"], errors="coerce").fillna(-1).astype(int),
        "cod": _cod(k["CODIGO PRODUCTO"]),
        "t": k["COD TIPO"].fillna("").astype(str).str.strip(),
        "ent": _num(k["CANT INGRESO"]),
        "sal": _num(k["CANT SALIDA"]),
        "movs": _num(k["MOVIMIENTOS"]).astype(int),
        "stock": _num(k["STOCK DESPUES"]),
    })
    return out[(out["t"] != "SI") & out["hora"].notna()]


def _es_compra(t):
    return t.str.isdigit() & (pd.to_numeric(t, errors="coerce") < 90)


def ventana(K, L):
    """Las filas del kardex de cada línea entre sus dos conteos (sin ajustes):
    después de la hora del conteo anterior (`t0w`) y hasta la hora de este.
    Una línea que nunca se contó en su área arranca en `desde`, lo más viejo
    que se lee del kardex (#651)."""
    base = L[["id", "acod", "cod", "t0w", "t1"]]
    W = K[K["t"] != "93"].merge(base, on=["acod", "cod"])
    W = W[(W["hora"] > W["t0w"].dt.floor("h")) & (W["hora"] <= W["t1"].dt.floor("h"))]
    return W.reset_index(drop=True)


def motivos(W, K, L, salidas, area_de):
    """Entró y salió POR MOTIVO, por línea: `{id: {"ent": [[motivo, q, n]],
    "sal": [...]}}`. Un requerimiento o una transferencia dice el área del
    otro lado (la que hizo el movimiento contrario del mismo producto en la
    misma hora); una nota de salida se parte por su tipo de descargo
    (Bajas, Comida Personal…) con `salidas.parquet`, por fecha de proceso,
    sin pasar de lo que dice el kardex."""
    lados = []
    for lado, col in (("ent", "ent"), ("sal", "sal")):
        x = W[W[col] > 1e-12][["id", "hora", "acod", "cod", "t", "movs"]].copy()
        x["lado"] = lado
        x["qty"] = W.loc[x.index, col]
        lados.append(x)
    M = pd.concat(lados, ignore_index=True)
    M = M[~((M["t"] == "98") & (M["lado"] == "sal"))]
    nom = M["t"].map(NOMBRE_MOV)
    nom = nom.where(nom.notna(), np.where(_es_compra(M["t"]), "Compra",
                                          "Tipo " + M["t"]))
    M["mot"] = nom
    M.loc[(M["t"] == "94") & (M["lado"] == "sal"), "mot"] = "Orden de producción · como insumo"
    M.loc[(M["t"] == "96") & (M["lado"] == "ent"), "mot"] = "Porcionamiento · corte que salió"
    M.loc[(M["t"] == "96") & (M["lado"] == "sal"), "mot"] = "Porcionamiento · se porcionó"

    # El área del otro lado de un requerimiento o una transferencia.
    entre = M[M["t"].isin(["97", "99"])].reset_index()
    if len(entre):
        X = K[K["t"].isin(["97", "99"])][["hora", "cod", "t", "acod", "ent", "sal"]]
        J = entre[["index", "hora", "cod", "t", "acod", "lado"]].merge(
            X.rename(columns={"acod": "acod2", "ent": "ent2", "sal": "sal2"}),
            on=["hora", "cod", "t"])
        J = J[J["acod2"] != J["acod"]]
        J["q2"] = np.where(J["lado"] == "ent", J["sal2"], J["ent2"])
        J = (J[J["q2"] > 0].sort_values("q2", kind="stable")
             .drop_duplicates("index", keep="last"))
        otra = J.set_index("index")["acod2"].map(area_de).dropna()
        if len(otra):
            de_a = np.where(M.loc[otra.index, "lado"] == "ent", " de ", " a ")
            M.loc[otra.index, "mot"] = M.loc[otra.index, "mot"] + de_a + otra.map(_titulo)

    G = (M.groupby(["id", "lado", "mot"], as_index=False)
         .agg(q=("qty", "sum"), n=("movs", "sum")))

    # Las notas de salida, por su tipo de descargo.
    k98 = (W[W["t"] == "98"].groupby("id", as_index=False)
           .agg(q98=("sal", "sum"), n98=("movs", "sum")))
    k98 = k98[k98["q98"] > 1e-9]
    notas = []
    if len(k98) and salidas is not None and len(salidas):
        S = salidas.merge(L[["id", "area", "cod", "t0w", "t1"]], on=["area", "cod"])
        S = S[S["id"].isin(k98["id"]) & (S["f"] > S["t0w"].dt.floor("D"))
              & (S["f"] <= S["t1"])]
        T = (S.groupby(["id", "tipo"], as_index=False)
             .agg(q=("q", "sum"), n=("q", "size"))
             .sort_values(["id", "q"], ascending=[True, False], kind="stable"))
        T = T.merge(k98[["id", "q98"]], on="id")
        antes = T.groupby("id")["q"].cumsum() - T["q"]
        T["q"] = np.minimum(T["q"], (T["q98"] - antes).clip(lower=0.0))
        T = T[T["q"] > 1e-9]
        notas.append(T.assign(lado="sal", mot="Nota de salida · " + T["tipo"])
                     [["id", "lado", "mot", "q", "n"]])
        asignado = T.groupby("id")["q"].sum()
    else:
        asignado = pd.Series(dtype=float)
    resto = k98.assign(q=k98["q98"] - k98["id"].map(asignado).fillna(0.0))
    resto = resto[resto["q"] > 0.005]
    notas.append(resto.assign(lado="sal", mot="Nota de salida")
                 .rename(columns={"n98": "n"})[["id", "lado", "mot", "q", "n"]])
    G = pd.concat([G, *notas], ignore_index=True).sort_values(
        ["id", "lado", "q"], ascending=[True, True, False], kind="stable")
    out = defaultdict(lambda: {"ent": [], "sal": []})
    for r in G.itertuples(index=False):
        out[int(r.id)][r.lado].append([r.mot, float(r.q), int(r.n)])
    return out


def caminos_del_stock(W, L):
    """El stock del sistema entre los dos conteos, por línea: el contado
    anterior, el último valor de cada día con movimientos y el sistema al
    conteo. `{id: [(Timestamp, stock), ...]}`."""
    out = {}
    if len(W):
        P = (W.sort_values("hora", kind="stable")
             .assign(dia=W["hora"].dt.floor("D"))
             .groupby(["id", "dia"], as_index=False)
             .agg(hora=("hora", "last"), stock=("stock", "last")))
        for r in P.itertuples(index=False):
            out.setdefault(int(r.id), []).append((r.hora, float(r.stock)))
    caminos = {}
    for r in L.itertuples(index=False):
        caminos[int(r.id)] = ([(r.t0w, float(r.c0w))] + out.get(int(r.id), [])
                              + [(r.t1, float(r.s))])
    return caminos


# ═══════════════════════════════════════════════════════════════════════
# LAS RECETAS
# ═══════════════════════════════════════════════════════════════════════

def recetas(recetaventa, recetabase, carta):
    """`(RVD, RB)`: quién descuenta cada producto.

    RVD: las líneas de los platos ACTIVOS que se descargan (`cp`, `plato`,
    `ci` el insumo, `q` en la unidad del kardex, `area` de descargo, `t`
    PRODUCTO o INSUMO, `fm` la última edición), más los platos que el POS
    descuenta DIRECTO (`cartacosteada.parquet`), sin área. RB: las líneas de
    las recetas base activas (`prod`, `rbn`, `ci`, `ins`, `q`, `area`, `t`,
    `fr`)."""
    rv = recetaventa
    rv = rv[(_up(rv["ITEM VENTA ACTIVO"]) == "ACTIV") & (_up(rv["RV ACTIV"]) == "RV ACT")
            & (_up(rv["DESCARG"]) == "SI")]
    RV = pd.DataFrame({
        "cp": _cod(rv["COD PLATO"]),
        "plato": rv["NOMB PLATO"].fillna("").astype(str).str.strip(),
        "ci": _cod(rv["COD INS"]),
        "q": _num(rv["CANTIDAD"]) / _num(rv["FACTOR"]).replace(0, 1.0),
        "area": _up(rv["SUBALM INS"]), "t": _up(rv["T DESCARG"]),
        "fm": _fecha(rv["FECH MODIF"]) if "FECH MODIF" in rv.columns else pd.NaT})
    partes = [RV]
    if carta is not None and len(carta):
        c = carta[_up(carta["TIPO DESC"]).str.contains("DIRECT")]
        D = pd.DataFrame({"cp": _cod(c["COD PLATO"]),
                          "plato": c["ITEM VENT"].fillna("").astype(str).str.strip(),
                          "ci": _cod(c["COD ITEM O RECETA"]), "q": 1.0, "area": "",
                          "t": "PRODUCTO", "fm": pd.NaT})
        partes.append(D[~D["cp"].isin(set(RV["cp"])) & (D["ci"] != "")])
    RVD = pd.concat(partes, ignore_index=True)
    rb = recetabase[_up(recetabase["RB ACT"]) == "RB.ACTIV"]
    RB = pd.DataFrame({
        "prod": _cod(rb["COD PROD RB"]),
        "rbn": rb["RB NOMBRE"].fillna("").astype(str).str.strip(),
        "ci": _cod(rb["COD INS RB"]),
        "ins": rb["INSUMO"].fillna("").astype(str).str.strip(),
        "q": _num(rb["CANT"]) / _num(rb["FACTOR INS"]).replace(0, 1.0),
        "area": _up(rb["AREA DESC RB"]), "t": _up(rb["T DESCARG"]),
        "fr": _fecha(rb["FECH REG"]) if "FECH REG" in rb.columns else pd.NaT})
    return RVD, RB[RB["ci"] != ""]


def es_dd(nombre):
    """Una receta base pensada para descargarse por insumo lleva «DD» en el
    nombre (palabra suelta)."""
    import re
    return bool(re.search(r"\bDD\b", str(nombre), re.I))


# ═══════════════════════════════════════════════════════════════════════
# LA CUENTA
# ═══════════════════════════════════════════════════════════════════════

def calcular(ajuste, sesion, sesiones, kardex, recetaventa, recetabase,
             carta, porcionamientos, ordenes, salidas, venta_dia, combos=None,
             requerimientos=None, sunat=None):
    """Todo lo que dibuja la vista para UNA sesión: `{"lineas", "fichas",
    "resumen"}`, o None sin líneas.

    `lineas`: un DataFrame, una fila por línea con diferencia (`id`, `cod`,
    `producto`, `area`, `familia`, `subfamilia`, `u`, `s`, `k`, `q`, `v`,
    `precio`, `pista`/`pista_t`/`pista_f` la principal, `n_pistas`, `fuerte`
    y `tipos`, los tipos separados por coma). `fichas`: `{id: dict}` con las
    pistas y todo lo de la ficha. `combos` es `combosdetalle.parquet` (la
    ficha de cada combo: sus opciones, no lo que se eligió); sin él, no hay
    pista de combo. `requerimientos` es `requerimientos.parquet` (quién pide
    cada producto) y `sunat`, las líneas del XML de los comprobantes que
    SUNAT registra y el Almacén no (`data.sunat_sin_ingresar`); sin ellos, no
    hay esas pistas. Pura."""
    A = ajuste_normalizado(ajuste)
    L = lineas_de_sesion(A, sesion)
    if L.empty:
        return None
    ini = pd.Timestamp(min(sesion["dias"]))
    desde = ini - pd.Timedelta(days=DIAS_ATRAS)
    area_de = A.drop_duplicates("acod").set_index("acod")["area"].to_dict()
    # Una línea que nunca se contó en su área (o hace más de DIAS_ATRAS días)
    # arranca en `desde`, con el stock que tenía el kardex: la Chardonnay que
    # se vendió sin entrar no tenía conteo anterior en Cava (#651).
    L["sin_ant"] = L["t0"].isna() | (L["t0"] < desde)
    L["t0w"] = L["t0"].where(~L["sin_ant"], desde)
    L["t0x"] = L["t0w"]

    # ── El kardex ─────────────────────────────────────────────────────
    K = kardex_normalizado(kardex)
    W = ventana(K, L)
    tot = W.groupby("id").agg(ing=("ent", "sum"), sal=("sal", "sum"))
    L["ing"] = L["id"].map(tot["ing"]).fillna(0.0)
    L["sal"] = L["id"].map(tot["sal"]).fillna(0.0)
    # Sin conteo anterior, lo que había es la foto del kardex ANTES de su
    # primer movimiento de la ventana; sin movimientos, lo que dice hoy.
    prim = W.sort_values("hora", kind="stable").drop_duplicates("id")
    abre = (prim["stock"] - prim["ent"] + prim["sal"]).set_axis(prim["id"].to_numpy())
    L["c0w"] = np.where(L["sin_ant"], L["id"].map(abre).fillna(L["s"]), L["c0"])
    L["gap"] = L["c0w"] + L["ing"] - L["sal"] - L["s"]
    S = None
    if salidas is not None and len(salidas):
        sa = salidas[_up(salidas["NOMBRE ESTADO SALIDA"]) == "PROCESADO"]
        S = pd.DataFrame({"area": _up(sa["AREA"]), "cod": _cod(sa["COD PRODUCTO"]),
                          "f": _fecha(sa["FECHA PROCESADO"]), "q": _num(sa["CANT SALIDA"]),
                          "tipo": sa["TIPO DESCARGO"].fillna("").astype(str).str.strip()})
    MOT = motivos(W, K, L, S, area_de)
    CAM = caminos_del_stock(W, L)
    K95 = K[(K["t"] == "95") & (K["sal"] > 0)]
    k95_de = {c: (g["hora"].to_numpy(), g["sal"].to_numpy())
              for c, g in K95.groupby("cod")}
    # Las compras de cada producto, para «última compra»: la última HASTA el
    # conteo, no la que llegó después (una sesión de dos días lee el kardex
    # hasta el último).
    comp_de = {c: np.sort(g["hora"].to_numpy())
               for c, g in K[_es_compra(K["t"]) & (K["ent"] > 0)].groupby("cod")}

    def ultima_compra(c, t1):
        h = comp_de.get(c)
        if h is None:
            return None
        h = h[h <= np.datetime64(t1)]
        return pd.Timestamp(h[-1]) if len(h) else None

    # ── Recetas, órdenes, porcionamientos, ventas ─────────────────────
    RVD, RB = recetas(recetaventa, recetabase, carta)
    como_prod, por_ins = defaultdict(set), defaultdict(set)
    for ci, t, donde in zip(np.concatenate([RVD["ci"], RB["ci"]]),
                            np.concatenate([RVD["t"], RB["t"]]),
                            np.concatenate([RVD["plato"], RB["rbn"]])):
        if t == "PRODUCTO":
            como_prod[ci].add(donde)
        elif t == "INSUMO":
            por_ins[ci].add(donde)
    como_prod = {c: sorted(v) for c, v in como_prod.items()}
    por_ins = {c: sorted(v) for c, v in por_ins.items()}
    con_stock = set(como_prod)
    rb_nombre = RB.drop_duplicates("prod").set_index("prod")["rbn"].to_dict()

    # Los combos: qué platos lleva cada uno, fijos o a elegir por grupo. El
    # grupo se compara en mayúsculas (en el POS «D» y «d» son el mismo).
    combos_de = defaultdict(list)
    if combos is not None and len(combos):
        cb = combos
        if "COMBO ACTIVO" in cb.columns:
            cb = cb[_num(cb["COMBO ACTIVO"]) == 1]
        cb = pd.DataFrame({"cc": _cod(cb["COD COMBO"]),
                           "combo": cb["COMBO"].fillna("").astype(str).str.strip(),
                           "g": _up(cb["GRUPO"]), "cp": _cod(cb["COD PRODUCTO"]),
                           "fijo": _num(cb["FIJO"]) == 1,
                           "cant": _num(cb["CANTIDAD"]).replace(0, 1.0)})
        cb["n_op"] = cb.groupby(["cc", "g"])["cp"].transform("nunique")
        for r in cb.itertuples(index=False):
            combos_de[r.cp].append((r.cc, r.combo, r.g, bool(r.fijo), float(r.cant),
                                    int(r.n_op)))
    cods_combo = {t_[0] for v_ in combos_de.values() for t_ in v_}

    # Los requerimientos de cada producto: quién lo pide y lo pendiente
    # (#652). Arreglos por código: se miran línea por línea.
    rq_de = {}
    if requerimientos is not None and len(requerimientos):
        rq = requerimientos
        RQ = pd.DataFrame({"cod": _cod(rq["CODIGO PRODUCTO"]), "area": _up(rq["SUB ALMACEN"]),
                           "f": _fecha(rq["FECHA REGISTRO"]),
                           "num": rq["COD REQUERIMIENTO"].fillna("").astype(str).str.strip(),
                           "estado": _up(rq["NOMBRE ESTADO REQUERIMIENTO"]),
                           "q": _num(rq["CANTIDAD"])})
        RQ = RQ[RQ["f"].notna() & (RQ["q"] > 0)]
        rq_de = {c: (g["f"].to_numpy(), g["area"].to_numpy(), g["q"].to_numpy(),
                     g["num"].to_numpy(), g["estado"].to_numpy())
                 for c, g in RQ.groupby("cod")}

    # Las líneas de las facturas que SUNAT tiene y el Almacén no (#652).
    SU = None
    if sunat is not None and len(sunat):
        SU = pd.DataFrame({"doc": sunat["doc"].astype(str), "prov": sunat["prov"].astype(str),
                           "fecha": _fecha(sunat["fecha"]),
                           "desc": sunat["descripcion"].fillna("").astype(str),
                           "q": _num(sunat["cantidad"]),
                           "u": sunat["unidad"].fillna("").astype(str).str.lower()})
        SU = SU[SU["fecha"].notna()].reset_index(drop=True)
        SU["pal"] = SU["desc"].map(palabras)
        su_f, su_pal = SU["fecha"].to_numpy(), SU["pal"].tolist()
        su_filas = SU.drop(columns="pal").to_dict("records")
    _su_idx = {}

    op = ordenes[_up(ordenes["NOMBRE ESTADO"]) == "PROCESADO"]
    OP = pd.DataFrame({"cod": _cod(op["COD PRODUCTO"]), "f": _fecha(op["FECHA PROCESO"]),
                       "q": _num(op["CANTIDAD"])})
    OP = OP[OP["f"].notna()]
    ult_orden = OP.groupby("cod")["f"].max()
    op_de = {c: (g["f"].to_numpy(), g["q"].to_numpy()) for c, g in OP.groupby("cod")}
    po = porcionamientos
    PO = pd.DataFrame({"ini": _cod(po["COD PROD INIC"]), "fin": _cod(po["COD PROD FINAL"]),
                       "fin_n": po["PROD FINAL RESULT"].fillna("").astype(str).str.strip(),
                       "ini_n": po["PROD INICIAL"].fillna("").astype(str).str.strip(),
                       "porc": po["COD PORC"].astype(str), "f": _fecha(po["FEC REGIST"]),
                       "qe": _num(po["CANT A PORCIONAR"])})
    PO = PO[PO["f"].notna()]
    ult_porc_fin = PO.groupby("fin")["f"].max()
    ult_porc_ini = PO.groupby("ini")["f"].max()
    porc_origen = (PO.groupby(["fin", "ini_n"]).size().reset_index(name="n")
                   .sort_values("n", kind="stable").drop_duplicates("fin", keep="last")
                   .set_index("fin")["ini_n"])
    VD = venta_dia.assign(cp=_cod(venta_dia["producto"]), dia=_fecha(venta_dia["dia"]))
    VD["cu"] = _num(VD["costo"]) / _num(VD["unidades_costeadas"]).where(
        _num(VD["unidades_costeadas"]) > 0)
    cu_de = {c: (g["dia"].to_numpy(), g["cu"].to_numpy())
             for c, g in VD[VD["cu"].notna()].sort_values("dia", kind="stable").groupby("cp")}
    _cc = {}

    # Ventanas distintas (pocas): ventas por plato, órdenes y porcionamientos.
    vent = L[["t0x", "t1"]].drop_duplicates().reset_index(drop=True)
    vent["w"] = np.arange(len(vent))
    L = L.merge(vent, on=["t0x", "t1"], how="left")
    vend, ords, porcs, vdias = {}, {}, {}, {}
    for r in vent.itertuples(index=False):
        x = VD[(VD["dia"] > r.t0x.normalize()) & (VD["dia"] <= r.t1.normalize())]
        vend[r.w] = x.groupby("cp")["unidades"].sum().to_dict()
        # Los días en que se vendió cada combo, para mirar el kardex esos días.
        vdias[r.w] = defaultdict(set)
        xc = x[x["cp"].isin(cods_combo) & (x["unidades"] > 0)]
        for cp_, d_ in zip(xc["cp"], xc["dia"]):
            vdias[r.w][cp_].add(d_)
        o = OP[(OP["f"] > r.t0x) & (OP["f"] <= r.t1)]
        ords[r.w] = o.groupby("cod")["q"].agg(["sum", "size"]).to_dict("index")
        p = PO[(PO["f"] > r.t0x) & (PO["f"] <= r.t1)]
        porcs[r.w] = p.groupby(["ini", "fin"]).agg(
            q=("qe", "sum"), n=("porc", "nunique")).to_dict("index")

    def costo_alrededor(cp, dia):
        """El costo por plato (la foto del POS en cada venta): mediana de los
        30 días antes de `dia` y de los 30 después. None con menos de tres
        días de venta a un lado."""
        g = cu_de.get(cp)
        if g is None or dia is None or pd.isna(dia):
            return None
        dia = pd.Timestamp(dia).normalize()
        if (cp, dia) not in _cc:
            d_, c_ = g
            d0 = np.datetime64(dia)
            a = c_[(d_ < d0) & (d_ >= np.datetime64(dia - pd.Timedelta(days=30)))]
            b = c_[(d_ > d0) & (d_ <= np.datetime64(dia + pd.Timedelta(days=30)))]
            _cc[(cp, dia)] = (None if len(a) < 3 or len(b) < 3
                              else [float(np.median(a)), float(np.median(b))])
        return _cc[(cp, dia)]

    # Los usos de cada producto: platos, recetas base (al producirlas o al
    # abrirse por insumo en un plato) y porcionamientos.
    rv_por_ci = defaultdict(list)
    for r in RVD.itertuples(index=False):
        rv_por_ci[r.ci].append(r)
    rb_por_ci = defaultdict(list)
    for r in RB.itertuples(index=False):
        rb_por_ci[r.ci].append(r)
    rb_por_prod = defaultdict(list)
    for r in RB.itertuples(index=False):
        rb_por_prod[r.prod].append(r)
    po_por_ini = defaultdict(list)
    for r in PO.drop_duplicates(["ini", "fin"]).itertuples(index=False):
        po_por_ini[r.ini].append((r.fin, r.fin_n))

    def usos_de(lin):
        c, w, area, t0x = lin["cod"], lin["w"], lin["area"], lin["t0x"]
        precio = float(lin["precio"])
        out = []
        for x in rv_por_ci.get(c, ()):
            nv = float(vend[w].get(x.cp, 0.0))
            ed = x.fm if pd.notna(x.fm) and x.fm >= t0x else None
            out.append({"via": "plato", "n": x.plato, "cp": x.cp, "q": float(x.q),
                        "a": x.area,
                        "t": x.t, "nv": nv, "d": nv * x.q if x.t == "PRODUCTO" else 0.0,
                        "ed": ed, "cc": costo_alrededor(x.cp, ed) if ed is not None else None,
                        "ap": float(x.q) * precio})
        for x in rb_por_ci.get(c, ()):
            o = ords[w].get(x.prod, {"sum": 0.0, "size": 0})
            ed = x.fr if pd.notna(x.fr) and x.fr >= t0x else None
            out.append({"via": "receta", "n": x.rbn, "q": float(x.q), "a": x.area,
                        "t": x.t, "nv": float(o["sum"]), "no": int(o["size"]),
                        "d": float(o["sum"]) * x.q if x.t == "PRODUCTO" else 0.0,
                        "ed": ed})
            for y in rv_por_ci.get(x.prod, ()):
                if y.t != "INSUMO":
                    continue
                nv = float(vend[w].get(y.cp, 0.0))
                ed = y.fm if pd.notna(y.fm) and y.fm >= t0x else None
                qq = float(x.q * y.q)
                out.append({"via": "plato_ins", "n": y.plato, "cp": y.cp, "por": x.rbn,
                            "q": qq,
                            "a": x.area, "t": x.t, "nv": nv,
                            "d": nv * qq if x.t == "PRODUCTO" else 0.0, "ed": ed,
                            "cc": costo_alrededor(y.cp, ed) if ed is not None else None,
                            "ap": qq * precio})
        # Los combos que llevan uno de esos platos: fijo, el combo lo
        # descuenta siempre; a elegir, sólo si se marcó esa opción.
        for u_ in [u for u in out if u["via"] in ("plato", "plato_ins")]:
            for cc_, nom, g, fijo, cant, n_op in combos_de.get(u_["cp"], ()):
                nv = float(vend[w].get(cc_, 0.0))
                qq = u_["q"] * cant
                prod_ = u_["t"] == "PRODUCTO"
                out.append({"via": "combo", "n": nom, "cc_": cc_, "plato": u_["n"],
                            "g": g, "fijo": fijo, "n_op": n_op, "q": qq, "a": u_["a"],
                            "t": u_["t"], "nv": nv,
                            "d": nv * qq if (fijo and prod_) else 0.0,
                            "hasta": nv * qq if prod_ else 0.0, "ed": None})
        for fin, fin_n in po_por_ini.get(c, ()):
            p = porcs[w].get((c, fin), {"q": 0.0, "n": 0})
            out.append({"via": "porc", "n": fin_n, "a": "", "t": "PRODUCTO",
                        "nv": float(p["q"]), "no": int(p["n"]), "d": float(p["q"]),
                        "ed": None})
        for u in out:
            u["aqui"] = (u["a"] == area) if u["a"] else None
        out.sort(key=lambda u: (-(u["d"] or 0.0), -(u["nv"] or 0.0), u["n"]))
        return out

    # Historia: el ajuste de la línea en los últimos seis cierres.
    cierres = [s for s in sesiones if s["tipo"] == "cierre"
               and min(s["dias"]) <= max(sesion["dias"])][-6:]
    hist = {}
    for i, s in enumerate(cierres):
        x = (A[A["t"].dt.normalize().isin(pd.to_datetime(list(s["dias"])))]
             .groupby(["acod", "cod"], as_index=False)[["q", "v"]].sum())
        hist.update({(ac, c, i): (float(q), float(v))
                     for ac, c, q, v in zip(x["acod"], x["cod"], x["q"], x["v"])})
    hist_lab = [_MESES[s["mes"][1] - 1] for s in cierres]

    # ── Las fichas ───────────────────────────────────────────────────
    def quien_pide(x):
        """`(pide, pendientes)`: los requerimientos PROCESADOS del producto en
        los 90 días antes del conteo, por área que lo pidió (`[área, cantidad,
        requerimientos, último, cantidad entre los dos conteos]`), y los SIN
        PROCESAR registrados en los 30 días antes del conteo."""
        h = rq_de.get(x["cod"])
        if h is None:
            return [], []
        f_, a_, q_, n_, e_ = h
        t1 = np.datetime64(x["t1"])
        m = ((e_ == "PROCESADO") & (f_ > np.datetime64(x["t1"] - pd.Timedelta(days=90)))
             & (f_ <= t1))
        por = {}
        for a, q, f, n, win in zip(a_[m], q_[m], f_[m], n_[m], f_[m] > np.datetime64(x["t0w"])):
            e = por.setdefault(a, [0.0, set(), f, 0.0])
            e[0] += float(q)
            e[1].add(n)
            e[2] = max(e[2], f)
            e[3] += float(q) if win else 0.0
        pide = sorted(([a, v[0], len(v[1]), pd.Timestamp(v[2]), v[3]] for a, v in por.items()),
                      key=lambda r_: -r_[1])
        mp = ((e_ == "GENERADO") & (f_ <= t1)
              & (f_ > np.datetime64(x["t1"] - pd.Timedelta(days=30))))
        pend = [[n, a, float(q), pd.Timestamp(f)]
                for a, q, f, n in zip(a_[mp], q_[mp], f_[mp], n_[mp])]
        return pide, pend

    lin = L.to_dict("records")
    fichas, usos_todos = {}, {}
    for x in lin:
        i, c = int(x["id"]), x["cod"]
        usos = usos_todos[i] = usos_de(x)
        rec = None
        if c in rb_nombre:
            ins = sorted(rb_por_prod.get(c, ()), key=lambda r: -r.q)
            o = ords[x["w"]].get(c, {"sum": 0.0, "size": 0})
            rec = {"dd": es_dd(rb_nombre[c]), "prod": len(como_prod.get(c, [])),
                   "ins": len(por_ins.get(c, [])), "prod_l": como_prod.get(c, [])[:6],
                   "ins_l": por_ins.get(c, [])[:6],
                   "uo": ult_orden.get(c), "ordenes": (float(o["sum"]), int(o["size"])),
                   "insumos": [r.ins for r in ins[:6]], "n_ins": len(ins)}
        fichas[i] = {
            "ent": MOT[i]["ent"] if i in MOT else [],
            "sal": MOT[i]["sal"] if i in MOT else [],
            "camino": CAM.get(i, []),
            "hist": [(lab,) + hist.get((x["acod"], c, j), (None, None))
                     for j, lab in enumerate(hist_lab)],
            "usos": usos[:USOS_FICHA], "usos_n": len(usos), "rec": rec,
            "viene": {"compra": ultima_compra(c, x["t1"]), "porc": porc_origen.get(c),
                      "uporc": ult_porc_fin.get(c)},
        }
        fichas[i]["pide"], fichas[i]["pend"] = quien_pide(x)

    # ── Las pistas ───────────────────────────────────────────────────
    E = pd.concat([
        RB[(RB["t"] == "PRODUCTO") & RB["prod"].isin(con_stock)][["ci", "prod"]]
        .rename(columns={"ci": "a", "prod": "b"}).assign(via="receta"),
        PO[["ini", "fin"]].rename(columns={"ini": "a", "fin": "b"}).assign(via="porc"),
    ]).drop_duplicates(["a", "b"])
    E = E[E["a"] != E["b"]]
    deriv, insum = defaultdict(list), defaultdict(list)
    for r in E.itertuples(index=False):
        deriv[r.a].append((r.b, r.via))
        insum[r.b].append((r.a, r.via))
    usados = set(RVD["ci"]) | set(RB["ci"]) | set(PO["ini"])
    por_cod = defaultdict(list)
    for x in lin:
        por_cod[x["cod"]].append(x)
    for x in lin:
        x["pk"] = palabra_clave(x["producto"])
    por_pk = defaultdict(list)
    for x in lin:
        if x["pk"]:
            por_pk[x["pk"]].append(x)

    def k95_en(cod, t0, t1):
        h = k95_de.get(cod)
        if h is None:
            return 0.0
        m = (h[0] > np.datetime64(t0)) & (h[0] <= np.datetime64(t1))
        return float(h[1][m].sum())

    def ordenes_en(cod, t0, t1):
        h = op_de.get(cod)
        if h is None:
            return 0
        return int(((h[0] > np.datetime64(t0)) & (h[0] <= np.datetime64(t1))).sum())

    def orden_tarde(cod, t1):
        h = op_de.get(cod)
        if h is None:
            return None
        f = h[0][(h[0] > np.datetime64(t1))
                 & (h[0] <= np.datetime64(t1 + pd.Timedelta(days=DIAS_TARDE)))]
        return pd.Timestamp(f.min()) if len(f) else None

    def area_de_descargo(x, usos, salio, sin_ing):
        """La pista del área de descargo (#654): lo que las ventas descontaron
        desde esta área en el período pasa de largo lo que las recetas de HOY
        descargan desde aquí, y un plato que lo lleva se editó desde el
        conteo anterior y hoy lo descarga desde OTRA área. El Pollito bb
        confitado, setiembre 2026: Cocina Personal descontó 54 —los 54
        Pollito Bebe Tostado vendidos— y el 7 oct esa receta pasó a Cocina.
        Un plato que el POS descuenta DIRECTO no dice su área: cuenta como de
        aquí, para no acusar lo que no se sabe."""
        kx = sum(m[1] for m in salio if m[0] == "Descargo de ventas")
        if kx <= 0:
            return None
        platos = [u_ for u_ in usos
                  if u_["via"] in ("plato", "plato_ins") and u_["t"] == "PRODUCTO"]
        aqui = sum(u_["d"] for u_ in platos if u_["aqui"] or not u_["a"])
        editados = [u_ for u_ in platos if u_.get("ed") is not None and u_["aqui"] is False]
        if not editados or kx <= 1.2 * aqui + 0.5:
            return None
        un = x["u"] or "und"
        e = max(editados, key=lambda u_: u_["nv"])
        de_aqui = [u_["n"] for u_ in platos if u_["aqui"] and u_["d"] > 0]
        tx = (f"Las ventas lo descontaron de {_titulo(x['area'])}: {es(kx)} {un} entre los dos "
              f"conteos, y con las recetas de hoy desde aquí saldrían {es(aqui)}"
              + (f" ({', '.join(de_aqui[:2])})" if de_aqui else "") + ". "
              f"{e['n']} se editó el {fecha_corta(e['ed'])} y hoy lo descarga desde "
              f"{_titulo(e['a'])}: antes lo descargaba desde aquí.")
        if sin_ing:
            tx += (f" Esta área no recibió el producto (ni compra, ni requerimiento, ni "
                   f"producción): por eso el sistema quedó en {es(x['s'])}.")
        return {"t": "desc", "f": 1, "ti": "Se descontó desde otra área", "tx": tx}

    def combo_sin_descontar(x, usos, salio):
        """La pista de combo: un combo que lleva un plato de este producto, que
        se vendió entre los dos conteos y que no lo descontó.

        POR TOTALES Y NO POR DÍA: el POS descuenta las ventas en LOTES, a la
        mañana siguiente y a veces juntando varios días (Reto Malbec, set
        2026: 1,6 el 21 a las 9, 4,8 el 23 a las 10, 3,4 el 28 a las 9). Lo
        que se mira es si lo que el kardex descontó por ventas en el período
        es lo de los platos SUELTOS: si es eso, el combo no puso nada."""
        kx = sum(m[1] for m in salio if m[0] == "Descargo de ventas")
        sueltos = sum(u_["d"] for u_ in usos
                      if u_["via"] in ("plato", "plato_ins") and u_["t"] == "PRODUCTO"
                      and u_["aqui"] is not False)
        if abs(kx - sueltos) > max(0.05, 0.03 * max(kx, sueltos)):
            return None
        cands = []
        for u_ in usos:
            if (u_["via"] != "combo" or u_["t"] != "PRODUCTO" or u_["nv"] <= 0
                    or u_["aqui"] is False):
                continue
            dias = sorted(vdias[x["w"]].get(u_["cc_"], ()))
            cands.append((u_["hasta"], u_, dias))
        if not cands:
            return None
        hasta, u_, dias = max(cands, key=lambda t_: t_[0])
        un = x["u"] or "und"
        falta = abs(x["q"])
        ratio = hasta / max(falta, 1e-9)
        fechas = (", ".join(fecha_corta(d) for d in dias[:3])
                  + (" y otros días" if len(dias) > 3 else ""))
        if kx > 1e-9:
            cuenta = (f"Lo que el kardex descontó por ventas ({es(kx)} {un}) es lo de los platos "
                      "sueltos: el combo no descontó nada de este producto. ")
        else:
            cuenta = "El kardex no descontó nada por ventas. "
        if u_["fijo"]:
            tx = (f"Va fijo en el combo {u_['n']} ({u_['plato']}), que se vendió "
                  f"{es(u_['nv'], 0)} veces ({fechas}). {cuenta}Serían {es(hasta)} {un} de los "
                  f"{es(falta)} que faltan: falta en lo que descarga el combo.")
            fu = 0.5 <= ratio <= 1.5
        else:
            tx = (f"{u_['plato']} es una de las {u_['n_op']} opciones del grupo "
                  f"«{u_['g'].lower()}» del combo {u_['n']}, que se vendió {es(u_['nv'], 0)} "
                  f"veces ({fechas}). {cuenta}Si se sirvió y la opción no se marcó en el "
                  f"pedido, serían hasta {es(hasta)} {un} de los {es(falta)} que faltan.")
            fu = False
        return {"t": "combo", "f": int(fu), "ti": "Combo que no lo descontó", "tx": tx}

    def factura_sin_ingresar(x):
        """La pista de SUNAT: una línea de una factura que SUNAT registra y el
        Almacén no, emitida entre los dos conteos (o hasta tres días antes),
        que nombra este producto. Fuerte si además la cantidad calza, en la
        misma unidad."""
        if SU is None:
            return None
        k_ = (x["t0w"], x["t1"])
        if k_ not in _su_idx:
            _su_idx[k_] = np.flatnonzero(
                (su_f > np.datetime64(x["t0w"] - pd.Timedelta(days=3)))
                & (su_f <= np.datetime64(x["t1"])))
        pp = palabras(x["producto"])
        mejor = None
        for j in _su_idx[k_]:
            sc = parecido(pp, su_pal[j])
            if sc is None:
                continue
            r = su_filas[j]
            calza = (_UNIDAD_XML.get(r["u"]) == (x["u"] or "und")
                     and 0.5 <= r["q"] / max(abs(x["q"]), 1e-9) <= 2.0)
            clave = (calza, sc, -abs(r["q"] - abs(x["q"])))
            if mejor is None or clave > mejor[0]:
                mejor = (clave, j)
        if mejor is None:
            return None
        (calza, _sc, _), j = mejor
        r = SimpleNamespace(**su_filas[j])
        n_doc = int((SU["doc"] == r.doc).sum())
        return {"t": "sunat", "f": int(calza), "ti": "Factura sin ingresar",
                "tx": f"La factura {r.doc} de {r.prov} ({fecha_corta(r.fecha)}) trae «{r.desc}» × "
                      f"{es(r.q)} {r.u} y no está ingresada en el Almacén: figura en SUNAT y no en el "
                      f"sistema{f' (con otras {n_doc - 1} líneas)' if n_doc > 1 else ''}. Si la "
                      "mercadería llegó, este sobrante es esa compra sin registrar."}

    def sin_procesar(x, pend):
        """La pista de un requerimiento SIN PROCESAR de antes del conteo: si
        se entregó, el que lo dio ya no lo tiene (faltante) y el que lo
        recibió sí (sobrante), y el sistema todavía dice lo contrario."""
        if not pend:
            return None
        q = float(x["q"])
        n, a, qq, f = max(pend, key=lambda p_: p_[2])
        if q > 0 and a == x["area"]:
            tx = (f"El requerimiento N° {n} de esta área ({es(qq)} {x['u'] or 'und'}, "
                  f"{fecha_corta(f)}) sigue sin procesar: si se entregó, aquí está lo que el "
                  "sistema todavía no ingresó.")
        elif q < 0 and a != x["area"]:
            tx = (f"El requerimiento N° {n} de {_titulo(a)} ({es(qq)} {x['u'] or 'und'}, "
                  f"{fecha_corta(f)}) sigue sin procesar: si se entregó, esta área ya no lo "
                  "tiene y el sistema todavía sí.")
        else:
            return None
        return {"t": "req", "f": int(0.6 <= qq / max(abs(q), 1e-9) <= 1.6),
                "ti": "Requerimiento sin procesar", "tx": tx}

    def lo_pide(x, pide):
        """Quién lo pide, en una frase, para las pistas de lo que nada
        descargó: si se gasta, es en el área que lo pide (#652)."""
        if not pide:
            return ""
        u = x["u"] or "und"
        a, q, n, ult, _ = pide[0]
        if a == x["area"]:
            frase = (f" {_titulo(a)} lo pidió por requerimiento: {es(q)} {u} en {n} "
                     f"requerimiento{'s' if n != 1 else ''} en 90 días (el último, "
                     f"{fecha_corta(ult)}). Es el área que lo usa, y nada registra en qué.")
        else:
            otros = ", ".join(f"{_titulo(r_[0])} {es(r_[1])} {u}" for r_ in pide[:3])
            frase = (f" Lo piden por requerimiento: {otros} en 90 días (el último, "
                     f"{fecha_corta(max(r_[3] for r_ in pide))}). Si se gasta, es ahí.")
        return frase

    def por_que_nada(x):
        """Por qué no salió: sigue cada camino por el que el POS lo
        descontaría y dice cuál falló. None si lo único que hay son platos que
        se vendieron DENTRO de un combo: eso lo dice la pista del combo."""
        c, area, t0, t1, w = x["cod"], x["area"], x["t0x"], x["t1"], x["w"]
        aqui = _titulo(x["area"])
        sin_orden, quieta, otra, quietos, vendidos, en_combo = [], [], [], [], [], []
        for r in rb_por_ci.get(c, ()):
            if r.t != "PRODUCTO" or r.prod not in con_stock:
                continue      # va por insumo: no lleva orden
            if ordenes_en(r.prod, t0, t1) == 0:
                kx = k95_en(r.prod, t0, t1)
                (sin_orden if kx > 0 else quieta).append((r, kx))
            elif r.area and r.area != area:
                otra.append((r.rbn, r.area))
        caminos = [(y.cp, y.plato, y.area, y.q, None, y.fm)
                   for y in rv_por_ci.get(c, ()) if y.t == "PRODUCTO"]
        for r in rb_por_ci.get(c, ()):
            if r.t != "PRODUCTO":
                continue
            caminos += [(y.cp, y.plato, r.area, r.q * y.q, r.rbn, y.fm)
                        for y in rv_por_ci.get(r.prod, ()) if y.t == "INSUMO"]
        for cp, plato, ar, qq, por, fm in caminos:
            nv = float(vend[w].get(cp, 0.0))
            if nv <= 0 and (not ar or ar == area) and any(
                    vend[w].get(t_[0], 0.0) > 0 for t_ in combos_de.get(cp, ())):
                en_combo.append(plato)
            elif nv <= 0:
                quietos.append(plato)
            elif ar and ar != area:
                otra.append((plato, ar))
            else:
                vendidos.append((nv, cp, plato, qq, por, fm))
        if sin_orden:
            r, kx = max(sin_orden, key=lambda t_: t_[1])
            tarde = orden_tarde(r.prod, t1)
            u_r = unidad(next((y["u"] for y in por_cod.get(r.prod, ())), "")) or "und"
            mas = len({t_[0].rbn for t_ in sin_orden}) - 1
            tx = (f"Va en {r.rbn}, que se vendió ({es(kx)} {u_r}) sin ninguna orden de "
                  f"producción entre los dos conteos{f' (y {mas} receta(s) base más igual)' if mas else ''}. "
                  "Sin la orden, este producto nunca se descontó: falta registrarla, o esa "
                  "receta base debería descargarse por insumo en sus platos.")
            if tarde is not None:
                tx += (f" Hubo una orden el {fecha_corta(tarde)}, después del conteo: si se "
                       "produjo antes de contar, se registró tarde.")
            return {"t": "nada", "f": 1, "tx": tx,
                    "ti": "Su orden se registró tarde" if tarde is not None
                    else "Su receta base no se produjo"}
        if vendidos:
            nv, cp, plato, qq, por, fm = max(vendidos, key=lambda t_: t_[0])
            tx = (f"{plato}{f' (dentro de {por}, por insumo)' if por else ''} se vendió "
                  f"{es(nv, 0)} veces desde esta área y aun así no lo descontó: la receta "
                  "de hoy no es la que había entre los dos conteos.")
            fu = 0
            if pd.notna(fm) and fm >= t0:
                tx += f" Se editó el {fecha_corta(fm)}{' (después del conteo)' if fm > t1 else ''}."
                cc = costo_alrededor(cp, fm)
                ap = qq * float(x["precio"])
                if cc:
                    calza = ap > 0.05 and abs((cc[1] - cc[0]) - ap) <= 0.35 * ap
                    tx += (f" El costo del plato pasó de S/ {es(cc[0])} a S/ {es(cc[1])} "
                           f"alrededor de esa fecha, y este producto aporta S/ {es(ap)} por "
                           "plato" + (": calza con que se sumó ese día." if calza
                                      else ": no calza solo con él."))
                    fu = int(calza)
                else:
                    tx += " Todavía no hay ventas suficientes después de la edición para ver el costo."
            else:
                tx += (" No se editó desde el conteo anterior: revisar si cambió el check "
                       "«descarga por insumo» o el área de descargo.")
            return {"t": "nada", "f": fu, "ti": "Se vendió y no se descontó", "tx": tx}
        if otra:
            areas = sorted({_titulo(a_) for _, a_ in otra})
            return {"t": "nada", "f": 1, "ti": "Se descarga desde otra área",
                    "tx": f"{otra[0][0]} lo descarga desde {', '.join(areas[:2])}, no desde "
                          f"{aqui}. Lo que falta aquí puede haberse usado allá sin traslado, "
                          "o la receta apunta al área equivocada."}
        if en_combo and not quietos:
            return None
        if quietos:
            nom = sorted(set(quietos))
            # Los combos que llevan esos platos, que tampoco se vendieron: el
            # plato no se vendió NI suelto NI dentro de un combo.
            cbs = sorted({t_[1] for cp, plato, *_ in caminos if plato in nom
                          for t_ in combos_de.get(cp, ())})
            ni = (f", ni sueltos ni en {'el combo' if len(cbs) == 1 else 'los combos'} que "
                  f"los lleva{'n' if len(cbs) > 1 else ''} ({', '.join(cbs[:2])})" if cbs else "")
            return {"t": "nada", "f": 1, "ti": "Sus platos no se vendieron",
                    "tx": f"Sólo lo descargan {', '.join(nom[:3])}{' y otros' if len(nom) > 3 else ''}, "
                          f"y no se vendieron entre los dos conteos{ni}. Si se gastó, fue en "
                          "platos cuya receta no lo lleva: ahí falta en una receta."}
        if quieta:
            return {"t": "nada", "f": 1, "ti": "Su receta base no se movió",
                    "tx": f"Va en {quieta[0][0].rbn}, que no se vendió ni se produjo entre los "
                          "dos conteos. Si se gastó, fue en algo cuya receta no lo lleva."}
        if c in ult_porc_ini.index:
            up = ult_porc_ini[c]
            if up > t1:
                return {"t": "nada", "f": 1, "ti": "Porcionamiento registrado tarde",
                        "tx": f"Sale al porcionarse, y el porcionamiento se registró el "
                              f"{fecha_corta(up)}, después del conteo del {fecha_corta(t1)}. Si "
                              "se porcionó antes de contar, se registró tarde: el próximo conteo "
                              "lo devolverá como sobrante."}
            return {"t": "nada", "f": 1, "ti": "No se porcionó",
                    "tx": f"Sale al porcionarse y no hubo porcionamientos entre los dos "
                          f"conteos (el último, {fecha_corta(up)}). Si se porcionó, falta registrarlo."}
        return {"t": "nada", "f": 1, "ti": "Nada lo descargó aquí",
                "tx": "Las recetas activas que lo nombran no lo descuentan como producto (lo "
                      "abren por insumo o no tienen platos activos): su uso real no pasa por "
                      "ninguna receta."}

    hace6 = ini - pd.Timedelta(days=DIAS_ATRAS)
    for x in lin:
        i, c, v, u = int(x["id"]), x["cod"], float(x["v"]), x["u"] or "und"
        q, sg = float(x["q"]), np.sign(x["q"])
        f = fichas[i]
        t0s = fecha_corta(x["t0"]) if pd.notna(x["t0"]) else "—"
        desde_ = (f"en los últimos {DIAS_ATRAS} días (no se había contado en esta área)"
                  if x["sin_ant"] else f"desde el conteo del {t0s}")
        sin_ing = x["ing"] <= 1e-9
        P = []
        # receta — la línea ES una receta base
        rec = f["rec"]
        if rec:
            vendida = any(m[0] == "Descargo de ventas" for m in f["sal"]) or any(
                u_["via"] == "plato" and u_["t"] == "PRODUCTO" and u_["nv"] > 0
                for u_ in f["usos"])
            uo, up = rec["uo"], ult_porc_fin.get(c)
            sin_orden = ((uo is None or pd.isna(uo) or uo < hace6)
                         and (up is None or pd.isna(up) or up < hace6))
            if rec["prod"] and sin_orden and vendida and not rec["dd"]:
                P.append({"t": "receta", "f": 1, "ti": "Receta base sin órdenes",
                          "tx": f"Los platos la descargan como producto "
                                f"({', '.join(rec['prod_l'][:3])}) y no tiene órdenes de "
                                "producción en los últimos seis meses. ¿Le falta el check "
                                "«descarga por insumo» en esos platos, o la cocina no "
                                "registra la orden?"})
            if rec["dd"] and rec["prod"]:
                P.append({"t": "receta", "f": 0, "ti": "DD descargada como producto",
                          "tx": f"Es DD, pero {rec['prod']} receta(s) la descargan como producto "
                                f"({', '.join(rec['prod_l'][:3])}). Si debía ir por insumo, "
                                "ahí falta el check."})
        # desc — se descontó desde un área a la que ya no apunta su receta
        if q > 0 and x["s"] < 0:
            pd_ = area_de_descargo(x, usos_todos[i], f["sal"], sin_ing)
            if pd_ is not None:
                P.append(pd_)
        # prod — falta el insumo y sobra lo que se hace con él (o al revés)
        if q < 0:
            cand = []
            for b, via in deriv.get(c, ()):
                sb = [y for y in por_cod.get(b, ()) if y["v"] > 0]
                if sum(y["v"] for y in sb) > 20:
                    top = max(sb, key=lambda y: y["v"])
                    fu = any(y["s"] < 0 and y["ing"] <= 1e-9 and y["sal"] > 0 for y in sb)
                    cand.append((fu, sum(y["v"] for y in sb), top, via))
            if cand:
                cand.sort(key=lambda t_: (not t_[0], -t_[1]))
                fu, _, top, via = cand[0]
                que = "orden de producción" if via == "receta" else "porcionamiento"
                como = "se hace con este producto" if via == "receta" else "sale de porcionar este producto"
                P.append({"t": "prod", "f": int(fu), "ti": "Sobra lo que se hace con él",
                          "tx": f"Sobra {top['producto']} ({_q(top['q'], top['u'] or 'und')} en "
                                f"{_titulo(top['area'])}), que {como}. "
                                + (f"Ese producto se descargó sin que entrara nada: falta registrar "
                                   f"la {que}." if fu else f"Puede ser una {que} sin registrar."),
                          "r": int(top["id"]), "m": len(cand) - 1})
        if q > 0 and c in insum:
            fal = []
            for a_, via in insum[c]:
                ya = [y for y in por_cod.get(a_, ()) if y["v"] < 0]
                if sum(y["v"] for y in ya) < -20:
                    fal.append((sum(y["v"] for y in ya), via, ya))
            if fal:
                fal.sort(key=lambda t_: t_[0])
                fu = x["s"] < 0 and sin_ing and x["sal"] > 0
                via = fal[0][1]
                que = "orden de producción" if via == "receta" else "porcionamiento"
                nom = "; ".join(
                    f"{min(ya, key=lambda y: y['v'])['producto']} "
                    f"({_q(sum(y['q'] for y in ya), ya[0]['u'] or 'und')})" for _, _, ya in fal[:3])
                P.append({"t": "prod", "f": int(fu),
                          "ti": "Faltan sus insumos" if via == "receta" else "Falta de donde sale",
                          "tx": f"Faltan productos con los que se hace: {nom}. "
                                + (f"No entró nada desde el conteo anterior: falta registrar la {que}."
                                   if fu else f"Puede ser una {que} sin registrar."),
                          "r": int(min(fal[0][2], key=lambda y: y["v"])["id"]), "m": len(fal) - 1})
        # area — el mismo producto, al revés, en otra área
        otras = [y for y in por_cod[c] if y["id"] != i and np.sign(y["q"]) == -sg]
        if otras:
            o = max(otras, key=lambda y: (abs(y["v"]), abs(y["q"])))
            ratio = abs(x["q"]) / max(abs(o["q"]), 1e-9)
            fu = 0.6 <= ratio <= 1.6
            extra = f" (el sistema tenía {es(o['s'])})" if o["s"] < 0 else ""
            P.append({"t": "area", "f": int(fu),
                      "ti": f"{'Sobró' if o['q'] > 0 else 'Faltó'} en {_titulo(o['area'])}",
                      "tx": f"En {_titulo(o['area'])} {'sobró' if o['q'] > 0 else 'faltó'} "
                            f"{es(abs(o['q']))} {u}{extra}. "
                            + ("Las cantidades calzan: parece un traslado o requerimiento sin "
                               "registrar." if fu else "Puede ser un traslado o requerimiento "
                               "sin registrar, por una parte."),
                      "r": int(o["id"])})
        # neg — el sistema terminó en negativo
        if q > 0 and x["s"] < 0:
            salio = sorted(f["sal"], key=lambda m: -m[1])[:2]
            por = " y ".join(f"{es(m[1])} {u} por {m[0][0].lower() + m[0][1:]}"
                             for m in salio) or "algo"
            if sin_ing:
                tx = (f"El sistema terminó en {es(x['s'])} {u}: {desde_} "
                      f"salieron {por} y no entró nada. El sobrante corrige ese negativo: no "
                      "es mercadería que apareció.")
            else:
                tx = (f"El sistema terminó en {es(x['s'])} {u}: entraron {es(x['ing'])} y "
                      f"salieron {es(x['sal'])}. El sobrante corrige ese negativo: algo entró "
                      "sin registrarse.")
            P.append({"t": "neg", "f": 1, "ti": "Sistema en negativo", "tx": tx})
        # rev — revierte el conteo anterior
        q0 = x["q0"]
        if pd.notna(q0) and abs(q0) > 1e-9 and np.sign(q0) == -np.sign(x["q"]):
            ratio = abs(x["q"]) / abs(q0)
            if 0.6 <= ratio <= 1.6:
                P.append({"t": "rev", "f": int(0.8 <= ratio <= 1.25),
                          "ti": "Revierte el conteo anterior",
                          "tx": f"En el conteo del {t0s} {'sobró' if q0 > 0 else 'faltó'} "
                                f"{es(abs(q0))} {u}; ahora {'sobra' if x['q'] > 0 else 'falta'} "
                                f"{es(abs(x['q']))} {u}. Puede ser un error de conteo o un "
                                "documento registrado tarde."})
        # sunat — una factura que SUNAT tiene y el Almacén no
        if q > 0:
            ps = factura_sin_ingresar(x)
            if ps is not None:
                P.append(ps)
        # req — un requerimiento sin procesar
        pr = sin_procesar(x, f["pend"])
        if pr is not None:
            P.append(pr)
        # combo — va en un combo que se vendió y no lo descontó
        pc = combo_sin_descontar(x, usos_todos[i], f["sal"]) if q < 0 else None
        # nada / nadie
        if q < 0:
            if c not in usados:
                P.append({"t": "nadie", "f": 1, "ti": "Ninguna receta lo usa",
                          "tx": "Ningún plato, receta base ni porcionamiento lo usa: su consumo "
                                "sólo aparece al contar. Si se usa en cocina, falta en una "
                                "receta; si es merma o uso del área, va en una nota de salida."
                                + lo_pide(x, f["pide"])})
            elif x["sal"] <= 1e-9:
                p_ = por_que_nada(x)
                antes_ = (desde_[0].upper() + desde_[1:] + " no salió nada de esta área con "
                          "un documento. ")
                if p_ is None and pc is not None:
                    pc["tx"] = antes_ + "Sus platos no se vendieron sueltos. " + pc["tx"]
                elif p_ is not None:
                    p_["tx"] = antes_ + p_["tx"] + lo_pide(x, f["pide"])
                    P.append(p_)
        if pc is not None:
            P.append(pc)
        # rubro — mismo rubro, al revés, si las cantidades calzan. Un lado
        # puede valer S/ 0 (nunca se compró); si los dos tienen precio, los
        # montos también tienen que calzar.
        ya = {p_.get("r") for p_ in P}
        if x["pk"]:
            cand = []
            for y in por_pk[x["pk"]]:
                if (y["cod"] == c or np.sign(y["q"]) != -sg or y["u"] != x["u"]
                        or y["id"] in ya or max(abs(v), abs(y["v"])) <= 20):
                    continue
                rq = abs(y["q"]) / max(abs(q), 1e-9)
                if not 0.6 <= rq <= 1.6:
                    continue
                if abs(v) > EPS and abs(y["v"]) > EPS and not 0.5 <= abs(y["v"]) / abs(v) <= 2.0:
                    continue
                cand.append((rq, y))
            if cand:
                rq, o = max(cand, key=lambda t_: (abs(t_[1]["v"]), abs(t_[1]["q"])))
                fal, sob = (x, o) if q < 0 else (o, x)
                vendio = sum(m[1] for m in fichas[int(sob["id"])]["sal"]
                             if m[0] == "Descargo de ventas")
                # Lo que falta no tuvo salidas y lo que sobra se vendió sin haber
                # entrado: se vendió uno con el código del otro.
                cambio = (fal["sal"] <= 1e-9 and sob["s"] < 0
                          and sob["ing"] <= 1e-9 and vendio > 0 and 0.8 <= rq <= 1.25)
                us_ = sob["u"] or "und"
                if cambio and q < 0:
                    tx = (f"Del otro lado: {o['producto']} {_q(o['q'], us_)} en "
                          f"{_titulo(o['area'])}, que se vendió {es(vendio)} {us_} sin haber "
                          f"entrado nunca (el sistema quedó en {es(o['s'])}), mientras éste no "
                          "tuvo ninguna salida. Lo más probable: se vendió este producto con el "
                          "código del otro.")
                elif cambio:
                    tx = (f"Del otro lado: {o['producto']} {_q(o['q'], o['u'] or 'und')} en "
                          f"{_titulo(o['area'])}, que no tuvo ninguna salida, mientras éste se "
                          f"vendió {es(vendio)} {us_} sin haber entrado nunca. Lo más probable: "
                          f"se vendió {o['producto']} con el código de éste.")
                else:
                    tx = (f"Del otro lado: {o['producto']} {_q(o['q'], o['u'] or 'und')} en "
                          f"{_titulo(o['area'])}. Las cantidades calzan: puede ser un conteo "
                          "o una receta con el código del otro.")
                P.append({"t": "rubro", "f": int(cambio), "r": int(o["id"]), "tx": tx,
                          "ti": "Vendido con el código del otro" if cambio
                          else "Mismo rubro, al revés"})
        P.sort(key=lambda p_: (-p_["f"], TIPOS.index(p_["t"])))
        f["pistas"] = P

    # ── La tabla ─────────────────────────────────────────────────────
    out = L[["id", "cod", "acod", "producto", "area", "familia", "subfamilia", "u", "s",
             "k", "q", "v", "precio", "t0", "t1", "c0", "ing", "sal", "gap", "sin_ant",
             "t0w", "c0w"]].copy()
    out["area"] = out["area"].map(_titulo)
    P0 = [fichas[i]["pistas"][0] if fichas[i]["pistas"] else None for i in out["id"]]
    out["pista"] = [p_["ti"] if p_ else "" for p_ in P0]
    out["pista_t"] = [p_["t"] if p_ else "" for p_ in P0]
    out["pista_f"] = [bool(p_["f"]) if p_ else False for p_ in P0]
    out["n_pistas"] = [len(fichas[i]["pistas"]) for i in out["id"]]
    out["fuerte"] = [any(p_["f"] for p_ in fichas[i]["pistas"]) for i in out["id"]]
    out["tipos"] = [",".join(sorted({p_["t"] for p_ in fichas[i]["pistas"]}))
                    for i in out["id"]]
    sesion_de = {d: s["nombre"] for s in sesiones for d in s["dias"]}
    out["ses0"] = [sesion_de.get(t.date(), "") if pd.notna(t) else "" for t in out["t0"]]
    return {"lineas": out.reset_index(drop=True), "fichas": fichas,
            "resumen": {"hist": hist_lab, "desde": desde}}


def cobertura(lineas):
    """`(fal, sob, % fal con pista fuerte, % sob con pista fuerte, n sin pista)`
    de un recorte de `lineas`, en soles."""
    if lineas is None or lineas.empty:
        return 0.0, 0.0, 0.0, 0.0, 0
    v = lineas["v"]
    fal, sob = float(-v[v < 0].sum()), float(v[v > 0].sum())
    fu = lineas["fuerte"]
    pf = float(-v[(v < 0) & fu].sum()) / fal if fal else 0.0
    ps = float(v[(v > 0) & fu].sum()) / sob if sob else 0.0
    return fal, sob, pf, ps, int((lineas["n_pistas"] == 0).sum())
