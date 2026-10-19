"""
simulador_receta — la cuenta del simulador de Recetas y Costos (2026-10-15).

Dos preguntas, una por herramienta:

  · «Simular» un plato (`graficos/simulador_plato.py`): su receta como un
    ÁRBOL —las recetas base abiertas y editables por dentro—, cada línea con
    su cantidad en la unidad de la receta (170 g, 30 ml, 1 und) y su precio en
    la unidad en que se COMPRA (S/ por kg). Los cortes porcionados llevan la
    merma y el peso por corte de su último porcionamiento.
  · «¿Y si sube un insumo?» (`graficos/recetas_alza.py`): cuánto de cada
    INSUMO DE COMPRA lleva cada plato, contando lo que está dentro de sus
    recetas base y los cortes porcionados de ese insumo.

Pura: sin Streamlit, sin R2. Recibe los parquets ya cargados y devuelve
listas y diccionarios. El navegador hace las cuentas del simulador en vivo
(`graficos/simulador_plato.js`); `costo_arbol` es la MISMA cuenta en Python,
para que el test la vigile y para que lo que se guarda como propuesta salga
de Python y no de lo que diga el navegador.

LA CUENTA DE CADA LÍNEA
-----------------------
    insumo comprado   cantidad × precio de compra ÷ factor
    receta base       Σ de sus líneas, proporcionadas a la cantidad que usa
                      el plato (cantidad ÷ factor unidades de la base)
    corte porcionado  cantidad × precio del insumo de origen ÷ (1 − merma)
                      × peso por corte          (regla #647)

`factor` es cuántas unidades de la receta hay en una de compra (1.000 g en
un kg; 32 oz en un litro; 1 und en una und). Es el de la receta
(`FACTOR`, `FACTOR INS`), el mismo con que el POS divide su precio promedio
(`ALMACEN.DBO.Sp_ActualizaReceta`).

El costo de cada línea se REESCALA para que el árbol sume, línea por línea,
lo que la receta dice que cuesta: la receta base guarda su costo de la
última vez que corrió `Sp_ActualizaReceta`, y sus líneas pueden haberse
movido desde entonces. Sin el reescalado, abrir una receta base cambiaría el
costo del plato sin haber tocado nada.

Tocar la cuenta es subir `VERSION`: va en la clave de la caché.
"""

import math

import numpy as np
import pandas as pd

VERSION = 3

UNIDADES = {
    "GRAMOS": "g", "GRAMO": "g", "MILILITROS": "ml", "MILILITRO": "ml",
    "ONZAS": "oz", "ONZA": "oz", "KILOS": "kg", "KILO": "kg",
    "LITROS": "l", "LITRO": "l", "UND": "und", "UNIDAD": "und",
    "UNIDADES": "und", "PORCION": "porc", "PORCIONES": "porc",
}
"""La unidad de la receta, como se escribe al lado de la cantidad."""

UNIDAD_COMPRA = {"g": "kg", "ml": "l", "oz": "l", "kg": "kg", "l": "l",
                 "und": "und", "porc": "porc"}
"""En qué se compra lo que la receta pide en esa unidad: el precio del
simulador va por esta unidad (S/ por kg y no por gramo)."""

NIVELES = 3
"""Hasta cuántos niveles se abren las recetas base. Medido el 2026-10-15:
ningún plato activo pasa de tres (la Salsa de Lomo › el Demiglace › el
Colágeno)."""

DIAS_PROMEDIO = 90
"""La ventana del «promedio de 90 días» de compras."""


def _txt(s):
    return s.astype("string").fillna("").str.strip()


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def unidad(texto):
    """«GRAMOS» → «g». Lo que no conoce lo deja en minúsculas."""
    t = str(texto or "").strip().upper()
    return UNIDADES.get(t, t.lower())


# ─── Lo que se lee de cada parquet ────────────────────────────────────────
def lineas_de_bases(df_rb):
    """{código de la receta base: [línea, …]} de recetabase.parquet, con lo
    que lleva UNA unidad de la base. Cada línea: cod, ins, cant, unid,
    factor, costo. Y aparte `info`: {código: {nombre, unid, fecha}}."""
    if df_rb is None or df_rb.empty:
        return {}, {}
    need = ("COD PROD RB", "COD INS RB", "INSUMO", "CANT", "FACTOR INS",
            "CST SUBT INS")
    if not all(c in df_rb.columns for c in need):
        return {}, {}
    d = pd.DataFrame({
        "base": _txt(df_rb["COD PROD RB"]),
        "cod": _txt(df_rb["COD INS RB"]),
        "ins": _txt(df_rb["INSUMO"]),
        "cant": _num(df_rb["CANT"]),
        "unid": (_txt(df_rb["UNID"]) if "UNID" in df_rb.columns else ""),
        "factor": _num(df_rb["FACTOR INS"]),
        "costo": _num(df_rb["CST SUBT INS"]),
    })
    d = d[(d["base"] != "") & (d["cod"] != "")]
    lineas = {}
    for base, g in d.groupby("base", sort=False):
        lineas[base] = [
            {"cod": r.cod, "ins": r.ins, "cant": float(r.cant),
             "unid": unidad(r.unid), "factor": float(r.factor) or 1.0,
             "costo": float(r.costo)}
            for r in g.itertuples(index=False)]
    info = {}
    cab = df_rb.drop_duplicates("COD PROD RB")
    for _, r in cab.iterrows():
        cod = str(r["COD PROD RB"]).strip()
        fecha = pd.to_datetime(r.get("FECH REG"), errors="coerce")
        info[cod] = {
            "nombre": str(r.get("RB NOMBRE") or "").strip(),
            "unid": unidad(r.get("RB UNID")),
            # FECH REG es la del ÚLTIMO guardado (confirmado con
            # MRECETABASE_LOG el 2026-10-15): se puede decir «actualizada».
            "fecha": fecha.strftime("%Y-%m-%d") if pd.notna(fecha) else "",
        }
    return lineas, info


def porcionamientos_vigentes(df_po):
    """{código del corte: datos de su ÚLTIMO porcionamiento}: de qué sale
    (`origen`, `cod_origen`), la merma en %, el peso por corte en la unidad
    de lo que se porciona (kg) y el precio con que salió el corte.

    El parquet trae una fila por CORTE con la cabecera repetida (regla
    #510): la merma es la de la cabecera, el peso el de la fila del corte."""
    if df_po is None or df_po.empty:
        return {}
    need = ("COD PORC", "COD PROD INIC", "PROD INICIAL", "FEC REGIST",
            "CANT A PORCIONAR", "CANT TOT RESUL", "COD PROD FINAL",
            "CANT RESULT", "PESO RESULT", "PREC PROM PROD FIN")
    if not all(c in df_po.columns for c in need):
        return {}
    d = df_po.assign(_f=pd.to_datetime(df_po["FEC REGIST"], errors="coerce"))
    d = d.sort_values("_f")
    out = {}
    for cod, g in d.groupby(_txt(d["COD PROD FINAL"]), sort=False):
        u = g.iloc[-1]
        ini, res = float(u["CANT A PORCIONAR"] or 0), float(u["CANT TOT RESUL"] or 0)
        cant, peso = float(u["CANT RESULT"] or 0), float(u["PESO RESULT"] or 0)
        if not (ini > 0 and cant > 0 and peso > 0 and res > 0):
            continue
        out[cod] = {
            "po": str(u["COD PORC"]),
            "fecha": u["_f"].strftime("%Y-%m-%d") if pd.notna(u["_f"]) else "",
            "origen": str(u["PROD INICIAL"]).strip(),
            "cod_origen": str(u["COD PROD INIC"]).strip(),
            "merma": round((ini - res) / ini * 100, 2),
            "peso": peso / cant,
            "unid_origen": unidad(u.get("UNID PROD INIC", "KILOS")),
            "precio_corte": float(u["PREC PROM PROD FIN"] or 0),
        }
    return out


def precios_compra(df_compras, dias=DIAS_PROMEDIO):
    """{código: {ult, fult, p90, unid}}: el precio unitario de la ÚLTIMA
    compra y el promedio ponderado de los últimos `dias` días de compras de
    ese artículo (Σ valor ÷ Σ cantidad, sin IGV, como `VALOR_COMPRA`)."""
    if df_compras is None or df_compras.empty:
        return {}
    need = ("COD_PRODUCTO", "FECHA_EMISION_DOC", "PRECIO_UNIT",
            "VALOR_COMPRA", "CANTIDAD_COMPRA")
    if not all(c in df_compras.columns for c in need):
        return {}
    d = pd.DataFrame({
        "cod": _txt(df_compras["COD_PRODUCTO"]),
        "f": pd.to_datetime(df_compras["FECHA_EMISION_DOC"], errors="coerce"),
        "pu": _num(df_compras["PRECIO_UNIT"]),
        "valor": _num(df_compras["VALOR_COMPRA"]),
        "cant": _num(df_compras["CANTIDAD_COMPRA"]),
        "unid": (_txt(df_compras["UNIDAD_DE_INGRESO"])
                 if "UNIDAD_DE_INGRESO" in df_compras.columns else ""),
    }).dropna(subset=["f"])
    d = d[(d["cant"] > 0) & (d["pu"] > 0)].sort_values("f", kind="stable")
    if d.empty:
        return {}
    ult = d.groupby("cod").tail(1).set_index("cod")
    tope = d.groupby("cod")["f"].transform("max") - pd.Timedelta(days=dias)
    v = d[d["f"] >= tope].groupby("cod")[["valor", "cant"]].sum()
    p90 = (v["valor"] / v["cant"]).to_dict()
    return {cod: {"ult": float(r.pu), "fult": r.f.strftime("%Y-%m-%d"),
                  "p90": float(p90.get(cod, r.pu)), "unid": unidad(r.unid)}
            for cod, r in ult.iterrows()}


# ─── El árbol de un plato ─────────────────────────────────────────────────
def _nodo(cod, ins, cant, unid, factor, costo, bases, info, porcs, compras,
          nivel):
    n = {"cod": cod, "ins": ins, "cant": float(cant), "unid": unid,
         "factor": float(factor) or 1.0, "costo": float(costo)}
    if cod in compras:
        n["compra"] = compras[cod]
    if cod in bases and nivel < NIVELES and n["cant"] > 0:
        escala = n["cant"] / n["factor"]
        hijos = [_nodo(l["cod"], l["ins"], l["cant"] * escala, l["unid"],
                       l["factor"], l["costo"] * escala, bases, info, porcs,
                       compras, nivel + 1)
                 for l in bases[cod]]
        suma = sum(h["costo"] for h in hijos)
        if hijos and suma > 0 and n["costo"] > 0:
            k = n["costo"] / suma
            for h in hijos:
                _reescalar(h, k)
        n["base"] = info.get(cod, {"nombre": ins, "unid": "", "fecha": ""})
        n["hijos"] = sorted(hijos, key=lambda h: -h["costo"])
    elif cod in porcs:
        p = dict(porcs[cod])
        if p["cod_origen"] in compras:
            p["compra_origen"] = compras[p["cod_origen"]]
        n["porc"] = p
    return n


def _reescalar(n, k):
    """El costo de `n` y de todo lo que cuelga de él, por `k`."""
    n["costo"] *= k
    for h in n.get("hijos", ()):
        _reescalar(h, k)


def arbol_plato(df_rv, cod_plato, bases, info, porcs, compras):
    """La receta de `cod_plato` como árbol (lista de nodos, de más caro a
    más barato). Cada nodo: cod, ins, cant, unid, factor, costo y, según el
    caso, `hijos` + `base` (receta base), `porc` (corte porcionado) o
    `compra` (precios de compra). Vacía si el plato no tiene receta."""
    if df_rv is None or df_rv.empty or "COD PLATO" not in df_rv.columns:
        return []
    d = df_rv[_txt(df_rv["COD PLATO"]) == str(cod_plato).strip()]
    return _arbol_de_filas(d, bases, info, porcs, compras)


def _arbol_de_filas(d, bases, info, porcs, compras):
    nodos = []
    for _, r in d.iterrows():
        cod = str(r.get("COD INS") or "").strip()
        if not cod:
            continue
        nodos.append(_nodo(
            cod, str(r.get("INS RV") or cod).strip(),
            float(pd.to_numeric(r.get("CANTIDAD"), errors="coerce") or 0),
            unidad(r.get("UNID COSTO")),
            float(pd.to_numeric(r.get("FACTOR"), errors="coerce") or 0) or 1.0,
            float(pd.to_numeric(r.get("TOTAL"), errors="coerce") or 0),
            bases, info, porcs, compras, 0))
    return sorted(nodos, key=lambda n: -n["costo"])


# ─── La cuenta, igual que en el navegador ─────────────────────────────────
def precio_hoy(n):
    """El precio de compra de HOY de una línea: el que despeja su costo."""
    return n["costo"] / n["cant"] * n["factor"] if n["cant"] else 0.0


def precio_origen_hoy(n):
    """El precio de HOY del insumo de origen de un corte, despejado del
    costo del corte: corte = P ÷ (1 − merma) × peso."""
    p = n["porc"]
    corte = n["costo"] / (n["cant"] or 1.0)
    return corte * (1 - p["merma"] / 100) / p["peso"] if p["peso"] else 0.0


def _precio_modo(hoy, compra, modo):
    """El precio según `modo`: «hoy», «ult» (última compra) o «p90». Si la
    compra está en otra unidad que la receta —el precio se va a más de 3
    veces del de hoy—, queda el de hoy: es otra unidad, no otro precio."""
    if modo == "hoy" or not compra:
        return hoy
    v = compra.get("ult" if modo == "ult" else "p90")
    if not v or not hoy or not (1 / 3 < v / hoy < 3):
        return hoy
    return float(v)


def es_porcionado(n):
    return (not n.get("hijos") and bool(n.get("porc"))
            and n["porc"].get("peso", 0) > 0
            and 0 <= n["porc"].get("merma", 100) < 100)


def costo_nodo(n, ruta, k=1.0, estado=None, modo="hoy"):
    """El costo de la línea `n` (y de lo que cuelga de ella) con las
    ediciones de `estado` ({ruta: {cant, P, merma, peso}}). `k` es cuánto
    se escaló su receta base madre. La MISMA cuenta que
    `simulador_plato.js::costo`."""
    s = (estado or {}).get(ruta, {})
    cant = s.get("cant", n["cant"]) * k
    if n.get("hijos"):
        k2 = cant / n["cant"] if n["cant"] else 0.0
        return sum(costo_nodo(h, f"{ruta}.{i}", k2, estado, modo)
                   for i, h in enumerate(n["hijos"]))
    if es_porcionado(n):
        p = n["porc"]
        P = s.get("P", _precio_modo(precio_origen_hoy(n), p.get("compra_origen"), modo))
        m = s.get("merma", p["merma"])
        peso = s.get("peso", p["peso"])
        return cant * P / (1 - m / 100) * peso
    P = s.get("P", _precio_modo(precio_hoy(n), n.get("compra"), modo))
    return cant * P / n["factor"] if n["factor"] else 0.0


def costo_arbol(nodos, estado=None, modo="hoy"):
    return sum(costo_nodo(n, str(i), 1.0, estado, modo)
               for i, n in enumerate(nodos))


def precio_sugerido(costo, pct_objetivo, divisor):
    """El precio de venta (con IGV y recargo) con que `costo` queda en
    `pct_objetivo` % del neto. `divisor` es el de `recetas_comun.divisor_neto`."""
    if not pct_objetivo or pct_objetivo <= 0:
        return math.nan
    return costo / (pct_objetivo / 100) * divisor


# ─── Exposición: cuánto de cada insumo de compra lleva cada plato ──────────
def origen_de_cortes(porcs):
    """{corte: insumo de compra del que sale}, siguiendo la cadena (un corte
    de un corte: el lomo cabeza sale del lomo fino)."""
    directo = {c: p["cod_origen"] for c, p in porcs.items()}

    def raiz(c, vistos=()):
        o = directo.get(c)
        if o and o != c and o not in vistos:
            return raiz(o, vistos + (c,))
        return c
    return {c: raiz(c) for c in directo}


def exposicion_plato(nodos, origen):
    """{insumo de compra: soles por plato} de un árbol ya armado. Un corte
    porcionado cuenta para el insumo de su origen: si el lomo fino sube 10 %,
    el corte sube 10 % (su precio es proporcional al del insumo)."""
    acc = {}

    def bajar(n):
        if n.get("hijos"):
            for h in n["hijos"]:
                bajar(h)
            return
        c = origen.get(n["cod"], n["cod"])
        acc[c] = acc.get(c, 0.0) + n["costo"]
    for n in nodos:
        bajar(n)
    return acc


def exposicion_carta(df_rv, df_rb, df_po, platos=None):
    """{plato: {insumo de compra: soles por plato}} para todos los platos
    con receta de recetaventa.parquet (o sólo los de `platos`). La suma de
    cada plato es su costo de receta."""
    if df_rv is None or df_rv.empty or "COD PLATO" not in df_rv.columns:
        return {}
    bases, info = lineas_de_bases(df_rb)
    porcs = porcionamientos_vigentes(df_po)
    origen = origen_de_cortes(porcs)
    quiero = None if platos is None else {str(p).strip() for p in platos}
    out = {}
    for cod, d in df_rv.groupby(_txt(df_rv["COD PLATO"]), sort=False):
        if quiero is not None and cod not in quiero:
            continue
        nodos = _arbol_de_filas(d, bases, info, {}, {})
        e = exposicion_plato(nodos, origen)
        if e:
            out[cod] = e
    return out


def alzas(exposiciones, carta, cambios):
    """Impacto conjunto de {insumo: cambio %} sobre las ventas del período.

    Cada plato aparece una vez, incluso si lleva varios insumos elegidos.
    Vendidos y VendidoNeto vienen de `carta_costeada.con_ventas`: el neto
    conserva descuentos y canales. Los costos son los de la receta actual,
    no el costo histórico al vender. Sin ventas se conserva la simulación
    por unidad, con impacto del período cero.
    """
    cols = ["Cod", "Producto", "Grupo", "Subgrupo", "Lleva", "Parte", "Precio",
            "Neto", "Costo", "CostoNuevo", "PctHoy", "PctNuevo",
            "PrecioMantener", "Vendidos", "DeltaUnitario", "DeltaPeriodo",
            "CostoPeriodo", "CostoNuevoPeriodo", "NetoPeriodo",
            "MargenPeriodo", "MargenNuevoPeriodo"]
    cambios = {str(c).strip(): float(p) / 100 for c, p in cambios.items()}
    if any(not math.isfinite(p) or p < -1 for p in cambios.values()):
        raise ValueError("El cambio de precio debe ser finito y no menor que −100 %.")
    if carta is None or carta.empty or not cambios:
        return pd.DataFrame(columns=cols)
    filas = []
    for r in carta.itertuples(index=False):
        exposicion = exposiciones.get(str(r.Cod).strip(), {})
        lleva = sum(exposicion.get(c, 0.0) for c in cambios)
        if lleva <= 0 or not math.isfinite(r.Neto) or r.Neto <= 0:
            continue
        costo = float(r.Costo) if pd.notna(r.Costo) and r.Costo > 0 else sum(exposicion.values())
        delta = sum(exposicion.get(c, 0.0) * p for c, p in cambios.items())
        nuevo = costo + delta
        vend = getattr(r, "Vendidos", 0.0)
        vend = float(vend) if pd.notna(vend) else 0.0
        neto = getattr(r, "VendidoNeto", 0.0)
        neto = float(neto) if pd.notna(neto) else 0.0
        filas.append({
            "Cod": r.Cod, "Producto": r.Producto, "Grupo": r.Grupo,
            "Subgrupo": r.Subgrupo, "Lleva": lleva,
            "Parte": lleva / costo * 100 if costo else 0.0,
            "Precio": float(r.Precio), "Neto": float(r.Neto), "Costo": costo,
            "CostoNuevo": nuevo, "PctHoy": costo / r.Neto * 100,
            "PctNuevo": nuevo / r.Neto * 100,
            "PrecioMantener": float(r.Precio) * nuevo / costo if costo else float(r.Precio),
            "Vendidos": vend, "DeltaUnitario": delta, "DeltaPeriodo": delta * vend,
            "CostoPeriodo": costo * vend, "CostoNuevoPeriodo": nuevo * vend,
            "NetoPeriodo": neto, "MargenPeriodo": neto - costo * vend,
            "MargenNuevoPeriodo": neto - nuevo * vend,
        })
    out = pd.DataFrame(filas, columns=cols)
    return out.sort_values(["DeltaPeriodo", "Lleva"], ascending=False,
                           key=lambda s: s.abs()).reset_index(drop=True)


def resumen_alzas(carta, impacto):
    """Costo y margen de toda la carta evaluada, incluyendo lo no afectado.

    Es margen de recetas (neto vendido menos costo teórico); no utilidad
    final: no descuenta personal, alquiler ni otros gastos.
    """
    costo = float((carta["Costo"] * carta["Vendidos"]).sum())
    neto = float(carta["VendidoNeto"].sum())
    delta = float(impacto["DeltaPeriodo"].sum())
    return {"neto": neto, "costo": costo, "costo_nuevo": costo + delta,
            "delta": delta, "margen": neto - costo,
            "margen_nuevo": neto - costo - delta}


def alza(exposiciones, carta, insumo, pct):
    """Cada plato que lleva `insumo`, con su costo y su % de costo si el
    insumo sube `pct` %. `carta`: DataFrame con Cod, Producto, Grupo,
    Subgrupo, Precio, Neto, Costo y, si se cargaron, Vendidos (90 días).
    Devuelve un DataFrame ordenado por el costo de más al mes."""
    cols = ["Cod", "Producto", "Grupo", "Subgrupo", "Lleva", "Parte", "Precio",
            "Neto", "Costo", "CostoNuevo", "PctHoy", "PctNuevo",
            "PrecioMantener", "Vendidos", "DeltaMes"]
    out = alzas(exposiciones, carta, {insumo: pct})
    out["DeltaMes"] = out["DeltaPeriodo"] / 3.0
    return out[cols]


# ─── El log de las recetas base (MRECETABASE_LOG / DRECETABASE_LOG) ──────
# El Almacén guarda en el log la receta base COMO ESTABA ANTES de cada
# guardado (medido el 2026-10-15: la Milanesa de lomo del 13/10 a las
# 17:23:47 guarda el insumo de S/ 20,28 que se quitó). La versión nueva es la
# fila siguiente del log, o la receta de hoy. `FECH REG` de recetabase es la
# hora del último guardado. Las recetas de PLATO no tienen log.
ARCHIVO_LOG = "recetabaselog.parquet"
ARCHIVO_LOG_DET = "recetabaselogdet.parquet"

JUNTAR_GUARDADOS = pd.Timedelta(hours=2)
"""Guardados seguidos de la misma receta base, a menos de esto, son UNA
edición: se guarda, se corrige un número, se vuelve a guardar."""


def consulta_sheet_log():
    """El SQL de la fila `recetabaselog` del Sheet (la cabecera del log), con
    los nombres completos que usa el usuario (sin apodos de tabla)."""
    return """SELECT
    ALMACEN.DBO.MRECETABASE_LOG.tRecetaBase AS [COD RB],
    ALMACEN.DBO.MRECETABASE_LOG.tCodigoProducto AS [COD PROD RB],
    ALMACEN.DBO.MRECETABASE_LOG.tDescripcion AS [RB NOMBRE],
    ALMACEN.DBO.MRECETABASE_LOG.nTotalCosto AS [COSTO],
    ALMACEN.DBO.MRECETABASE_LOG.fRegistro AS [FECH REG],
    ALMACEN.DBO.MRECETABASE_LOG.Usuario AS [USUARIO],
    ALMACEN.DBO.MRECETABASE_LOG.fMovimiento AS [FECH MOV]
FROM ALMACEN.DBO.MRECETABASE_LOG"""


def consulta_sheet_log_det():
    """El SQL de la fila `recetabaselogdet` del Sheet (las líneas del log)."""
    return """SELECT
    ALMACEN.DBO.DRECETABASE_LOG.tRecetaBase AS [COD RB],
    ALMACEN.DBO.DRECETABASE_LOG.tItem AS [ITEM],
    ALMACEN.DBO.DRECETABASE_LOG.tCodigoProducto AS [COD INS],
    ALMACEN.DBO.DRECETABASE_LOG.nCantidad AS [CANT],
    ALMACEN.DBO.DRECETABASE_LOG.nPrecio AS [PRECIO],
    ALMACEN.DBO.DRECETABASE_LOG.fMovimiento AS [FECH MOV]
FROM ALMACEN.DBO.DRECETABASE_LOG"""


def ediciones_base(mlog, dlog, df_rb):
    """Cada edición de una receta base, con cuánto movió su costo POR UNIDAD
    de la base, con los MISMOS precios de antes (para que una edición no se
    lleve la suba de precios de los meses que pasaron). Una lista de dicts
    cod_prod, nombre, t, usr, delta, cambios [(cod, nombre, antes, después,
    soles)], por fecha. Vacía si falta el log."""
    need_m = ("COD RB", "COD PROD RB", "RB NOMBRE", "FECH MOV")
    need_d = ("COD RB", "COD INS", "CANT", "PRECIO", "FECH MOV")
    if (mlog is None or dlog is None or mlog.empty or dlog.empty
            or not all(c in mlog.columns for c in need_m)
            or not all(c in dlog.columns for c in need_d)):
        return []
    m = pd.DataFrame({
        "rb": _txt(mlog["COD RB"]), "prod": _txt(mlog["COD PROD RB"]),
        "nombre": _txt(mlog["RB NOMBRE"]),
        "usr": _txt(mlog["USUARIO"]) if "USUARIO" in mlog.columns else "",
        "t": pd.to_datetime(mlog["FECH MOV"], errors="coerce"),
    }).dropna(subset=["t"]).sort_values(["rb", "t"], kind="stable")
    d = pd.DataFrame({
        "rb": _txt(dlog["COD RB"]), "cod": _txt(dlog["COD INS"]),
        "q": _num(dlog["CANT"]), "p": _num(dlog["PRECIO"]),
        "t": pd.to_datetime(dlog["FECH MOV"], errors="coerce"),
    }).dropna(subset=["t"])
    lineas = {rb: g for rb, g in d.groupby("rb", sort=False)}
    actual, nombres = {}, {}
    if df_rb is not None and not df_rb.empty and "COD RB" in df_rb.columns:
        for rb, g in df_rb.groupby(_txt(df_rb["COD RB"]), sort=False):
            actual[rb] = {c: (q, p) for c, q, p in zip(
                _txt(g["COD INS RB"]), _num(g["CANT"]), _num(g["CST UNIT INS"]))}
        nombres = dict(zip(_txt(df_rb["COD INS RB"]), _txt(df_rb["INSUMO"])))

    def foto(rb, t):
        """Las líneas del guardado de `rb` a la hora `t` (a 3 s)."""
        g = lineas.get(rb)
        if g is None:
            return None
        x = g[(g["t"] - t).abs() <= pd.Timedelta(seconds=3)]
        if x.empty:
            return None
        return {c: (float(q), float(p)) for c, q, p in zip(x["cod"], x["q"], x["p"])}

    out = []
    for rb, g in m.groupby("rb", sort=False):
        grupos = []
        for f in g.to_dict("records"):
            if grupos and f["t"] - grupos[-1][-1]["t"] < JUNTAR_GUARDADOS:
                grupos[-1].append(f)
            else:
                grupos.append([f])
        for i, gr in enumerate(grupos):
            antes = foto(rb, gr[0]["t"])
            despues = (foto(rb, grupos[i + 1][0]["t"]) if i + 1 < len(grupos)
                       else actual.get(rb))
            if antes is None or despues is None:
                continue
            ca = sum(q * p for q, p in antes.values())
            cd = sum(q * (antes[c][1] if c in antes else p)
                     for c, (q, p) in despues.items())
            cambios = []
            for c in set(antes) | set(despues):
                qa = antes.get(c, (0.0, 0.0))[0]
                qd = despues.get(c, (0.0, 0.0))[0]
                if abs(qa - qd) > 1e-9:
                    pr = antes[c][1] if c in antes else despues[c][1]
                    cambios.append((c, nombres.get(c, c), qa, qd, (qd - qa) * pr))
            if not cambios:
                continue
            cambios.sort(key=lambda z: -abs(z[4]))
            out.append({"cod_prod": gr[0]["prod"], "nombre": gr[-1]["nombre"],
                        "t": gr[0]["t"], "usr": gr[-1]["usr"],
                        "delta": cd - ca, "cambios": cambios,
                        # Para «Cambios Recetas Base» (regla #671): el costo
                        # de la receta antes y después, los dos con los
                        # precios de ANTES, y cuántos guardados se juntaron.
                        "rb": rb, "antes": ca, "despues": cd,
                        "guardados": len(gr)})
    return sorted(out, key=lambda e: e["t"])


def uso_de_bases(nodos):
    """{código de receta base: unidades de esa base que lleva UN plato}, con
    las bases que están dentro de otras bases."""
    acc = {}

    def bajar(n):
        if n.get("hijos"):
            acc[n["cod"]] = acc.get(n["cod"], 0.0) + (
                n["cant"] / n["factor"] if n["factor"] else 0.0)
            for h in n["hijos"]:
                bajar(h)
    for n in nodos:
        bajar(n)
    return acc


def marcas_plato(nodos, ediciones):
    """Las ediciones de las recetas base que el plato usa HOY, con lo que cada
    una lo movió: dicts t, base, usr, esp (soles por plato), txt, n."""
    uso = uso_de_bases(nodos)
    out = []
    for e in ediciones:
        u = uso.get(e["cod_prod"])
        if not u:
            continue
        c = e["cambios"][0]
        out.append({"t": e["t"], "base": e["nombre"], "usr": e["usr"],
                    "esp": u * e["delta"], "txt": f"{c[1]}: {c[2]:g} → {c[3]:g}",
                    "n": len(e["cambios"])})
    return out


# ─── Los picos del costo al vender ────────────────────────────────────────
PICO_VECES = 2.5
"""Un día es pico si el costo por unidad al vender pasa esto veces la
mediana de los 90 días anteriores, y al menos `PICO_MINIMO` soles más."""
PICO_MINIMO = 3.0
PORC_RARO_VECES = 1.8
"""Un porcionamiento es raro si su costo por corte pasa esto veces la
mediana del mismo corte en los 120 días anteriores (regla #647)."""


def cortes_del_arbol(nodos):
    """Los códigos de las HOJAS del árbol: insumos y cortes."""
    acc = set()

    def bajar(n):
        if n.get("hijos"):
            for h in n["hijos"]:
                bajar(h)
        else:
            acc.add(n["cod"])
    for n in nodos:
        bajar(n)
    return acc


def _causa_porcionamiento(po, ini):
    """El porcionamiento raro de `po` (los de los cortes del plato) que salió
    entre 4 días antes del pico y el día siguiente, contado en una frase."""
    cerca = po[(po["_f"] >= ini - pd.Timedelta(days=4))
               & (po["_f"] <= ini + pd.Timedelta(days=1))]
    for _, x in cerca.drop_duplicates("COD PORC").iterrows():
        hist = po[(po["_corte"] == x["_corte"]) & (po["_f"] < x["_f"])
                  & (po["_f"] >= x["_f"] - pd.Timedelta(days=120))]
        precio = float(x["PREC PROM PROD FIN"] or 0)
        habitual = float(hist["PREC PROM PROD FIN"].median()) if len(hist) >= 3 else 0.0
        if not (habitual and precio >= PORC_RARO_VECES * habitual):
            continue
        ini_c = float(x["CANT A PORCIONAR"] or 0)
        res = float(x["CANT TOT RESUL"] or 0)
        merma = (ini_c - res) / ini_c * 100 if ini_c else 0.0
        usr = str(x.get("USUARIO REG") or "").strip()
        return (f"Posible causa: el porcionamiento {x['COD PORC']} del {x['_f']:%d/%m %H:%M}"
                f"{' · ' + usr if usr else ''}: {ini_c:g} de "
                f"{str(x['PROD INICIAL']).strip()} con {merma:.0f} % de merma; "
                f"cada corte a S/ {precio:,.2f} (lo habitual, S/ {habitual:,.2f}).")
    return ""


def picos_plato(agg, cod, nodos=None, df_po=None, extra_cortes=(),
                cambios=None):
    """Los días seguidos en que el plato se vendió a más de `PICO_VECES` su
    costo habitual: dicts ini, fin, unid, normal, pico, exceso y `causa` (el
    porcionamiento raro de uno de sus cortes, si lo hubo justo antes, y/o el
    cambio de factor o de unidad de uno de sus artículos, de `cambios` —la
    auditoría del POS, `cambios_auditoria`—). De los 50 picos medidos el
    2026-10-15, ninguno grande venía de una compra; el 29 % del costo de
    más, de porcionamientos con merma imposible, y el 59 %, de cambios de
    factor o de unidad sin ajustar las recetas (sobre los 43 picos de ese
    día: 26 % y 61 %, ninguno con las dos causas).

    Los cortes que se miran son los de la receta de HOY, `extra_cortes` (lo
    que descarga un plato directo) y los HERMANOS de todos ellos —los que
    salen del mismo insumo—: la receta pudo apuntar a otro corte cuando fue
    el pico (el Lomo Saltado usaba en agosto «lomo trozos 180 g» y hoy
    «170 g»). Por eso la causa se dice como POSIBLE."""
    if agg is None or agg.empty:
        return []
    a = agg[agg["producto"].astype(str).str.strip() == str(cod).strip()]
    a = a[a["unidades_costeadas"] > 0]
    if a.empty:
        return []
    g = (a.assign(d=pd.to_datetime(a["dia"]))
         .groupby("d")[["costo", "unidades_costeadas"]].sum().sort_index())
    if len(g) < 10:
        return []
    cu = g["costo"] / g["unidades_costeadas"]
    med = cu.rolling("90D", min_periods=8).median().shift(1)
    alto = ((cu > PICO_VECES * med) & (cu - med > PICO_MINIMO)).fillna(False)
    dias = list(cu.index[alto])
    if not dias:
        return []
    grupos = [[dias[0]]]
    for d in dias[1:]:
        if (d - grupos[-1][-1]).days <= 7:
            grupos[-1].append(d)
        else:
            grupos.append([d])
    po = None
    need = ("COD PORC", "COD PROD FINAL", "FEC REGIST", "PREC PROM PROD FIN",
            "CANT A PORCIONAR", "CANT TOT RESUL", "PROD INICIAL")
    if ((nodos or extra_cortes) and df_po is not None and not df_po.empty
            and all(c in df_po.columns for c in need + ("COD PROD INIC",))):
        cortes = cortes_del_arbol(nodos or []) | {str(c).strip() for c in extra_cortes}
        po = df_po.assign(_corte=_txt(df_po["COD PROD FINAL"]),
                          _origen=_txt(df_po["COD PROD INIC"]),
                          _f=pd.to_datetime(df_po["FEC REGIST"], errors="coerce"))
        origenes = set(po.loc[po["_corte"].isin(cortes), "_origen"])
        po = po[po["_corte"].isin(cortes) | po["_origen"].isin(origenes)]
    out = []
    for gr in grupos:
        ini, fin = gr[0], gr[-1]
        normal = float(med.loc[ini])
        unid = g.loc[gr, "unidades_costeadas"]
        causas = [_causa_porcionamiento(po, ini) if po is not None and not po.empty else "",
                  _causa_auditoria(cambios, nodos or [], cod, ini)]
        out.append({
            "ini": ini, "fin": fin, "unid": float(unid.sum()), "normal": normal,
            "pico": float(cu.loc[gr].median()),
            "exceso": float(((cu.loc[gr] - normal) * unid).sum()),
            "causa": " ".join(c for c in causas if c),
        })
    return out


# ─── La auditoría del POS (regla #658) ────────────────────────────────────
# `INFSEGURIDAD.DBO.MMOVIMIENTO` guarda, campo por campo, quién cambió qué en
# las pantallas del POS y del Almacén (desde 2021; las RECETAS no, para eso
# está el log de arriba). De ahí sale la fila `auditoriacostos` del Sheet,
# con sólo los campos que mueven un costo: el factor y las unidades de un
# artículo —cambiarlos sin tocar las recetas que lo piden multiplica su
# costo: la Panceta pasó de factor 1000 a 1 y la receta seguía pidiendo
# gramos—, su precio de costo, y el tipo y el enlace de descargo de un plato.
ARCHIVO_AUDITORIA = "auditoriacostos.parquet"

CAMPOS_ARTICULO = ("Factor", "Unidad de Salida", "Unidad de Kardex")
CAMPO_PRECIO = "Precio de Costo"
CAMPOS_PLATO = ("Tipo Descargo", "Enlace Descargo")
PANTALLA_ARTICULO = "ARTICULOS Y PRECIOS"
PANTALLA_PLATO = "PRODUCTOS"

DIAS_CAUSA_AUDITORIA = 7
"""Un cambio explica un pico si es de hasta 7 días antes de que empiece
(medido: los nueve que explicaban caían entre el mismo día y 4 días antes;
con 30 días se sumaban cuatro de dudosa relación)."""

PRECIO_SALTO = 1.8
"""Un cambio del precio de costo cuenta sólo si se multiplica o divide por
más de esto: casi todos son redondeos (17,74825 → 17,748) o la coma por el
punto."""

TIPOS_DESCARGO = {"R": "receta", "D": "directo", "N": "no aplica"}


def consulta_sheet_auditoria():
    """El SQL de la fila `auditoriacostos` del Sheet. Las unidades llegan con
    su nombre (`vUnidadMedida`), en una subconsulta con nombre por lado."""
    return """SELECT
    INFSEGURIDAD.DBO.MMOVIMIENTO.nCorrelativo AS [CORRELATIVO],
    INFSEGURIDAD.DBO.MMOVIMIENTO.ffecha AS [FECHA],
    INFSEGURIDAD.DBO.MMOVIMIENTO.tUsuario AS [USUARIO],
    INFSEGURIDAD.DBO.MMOVIMIENTO.tTabla AS [PANTALLA],
    INFSEGURIDAD.DBO.MMOVIMIENTO.tId_RegistroUnico AS [CODIGO],
    INFSEGURIDAD.DBO.MMOVIMIENTO.tCampo AS [CAMPO],
    INFSEGURIDAD.DBO.MMOVIMIENTO.tValorAnterior AS [ANTES],
    INFSEGURIDAD.DBO.MMOVIMIENTO.tValorActual AS [DESPUES],
    UNIDAD_ANTES.DESCRIPCION AS [UNIDAD ANTES],
    UNIDAD_DESPUES.DESCRIPCION AS [UNIDAD DESPUES]
FROM INFSEGURIDAD.DBO.MMOVIMIENTO
LEFT JOIN (SELECT ALMACEN.DBO.vUnidadMedida.CODIGO,
                  ALMACEN.DBO.vUnidadMedida.DESCRIPCION
           FROM ALMACEN.DBO.vUnidadMedida) AS UNIDAD_ANTES
    ON UNIDAD_ANTES.CODIGO = INFSEGURIDAD.DBO.MMOVIMIENTO.tValorAnterior
   AND INFSEGURIDAD.DBO.MMOVIMIENTO.tCampo LIKE 'Unidad%'
LEFT JOIN (SELECT ALMACEN.DBO.vUnidadMedida.CODIGO,
                  ALMACEN.DBO.vUnidadMedida.DESCRIPCION
           FROM ALMACEN.DBO.vUnidadMedida) AS UNIDAD_DESPUES
    ON UNIDAD_DESPUES.CODIGO = INFSEGURIDAD.DBO.MMOVIMIENTO.tValorActual
   AND INFSEGURIDAD.DBO.MMOVIMIENTO.tCampo LIKE 'Unidad%'
WHERE INFSEGURIDAD.DBO.MMOVIMIENTO.ffecha >= '20250101'
  AND INFSEGURIDAD.DBO.MMOVIMIENTO.tTabla IN ('ARTICULOS Y PRECIOS', 'PRODUCTOS')
  AND INFSEGURIDAD.DBO.MMOVIMIENTO.tCampo IN ('Factor', 'Unidad de Salida',
      'Unidad de Kardex', 'Precio de Costo', 'Enlace Descargo', 'Tipo Descargo')"""


def _numero(v):
    """«18,158» y «18.158» son el mismo número (la auditoría trae los dos)."""
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return float("nan")


def _vacio(s):
    return (s == "") | (s.str.lower().isin(("nan", "none", "<na>")))


def cambios_auditoria(df):
    """La fila `auditoriacostos` limpia, una fila por guardado de un código:
    t, usr, pantalla, cod, guardado (el `CORRELATIVO`) y `campos`
    ({campo: (antes, después)}, con el nombre de la unidad si lo hay).

    Se van: lo que nació en ese guardado (ANTES vacío: es un artículo nuevo,
    no un cambio), lo que quedó igual, los precios que no saltaron
    `PRECIO_SALTO` veces, y el mismo cambio anotado dos veces (pasa:
    guardados a segundos uno del otro). Pura. DataFrame vacío sin datos."""
    cols = ["t", "usr", "pantalla", "cod", "guardado", "campos"]
    need = ("FECHA", "PANTALLA", "CODIGO", "CAMPO", "ANTES", "DESPUES")
    if df is None or df.empty or not all(c in df.columns for c in need):
        return pd.DataFrame(columns=cols)

    def col(nombre):
        if nombre in df.columns:
            return _txt(df[nombre].astype("string").fillna(""))
        return pd.Series("", index=df.index)
    d = pd.DataFrame({
        "t": pd.to_datetime(df["FECHA"], errors="coerce"),
        "usr": col("USUARIO"), "pantalla": col("PANTALLA").str.upper(),
        "cod": col("CODIGO"), "campo": col("CAMPO"),
        "antes": col("ANTES"), "despues": col("DESPUES"),
        "u_antes": col("UNIDAD ANTES"), "u_despues": col("UNIDAD DESPUES"),
        "guardado": col("CORRELATIVO"),
    }).dropna(subset=["t"])
    for c in ("u_antes", "u_despues", "despues"):
        d.loc[_vacio(d[c]), c] = ""
    d = d[~_vacio(d["antes"]) & (d["antes"] != d["despues"])]
    num = d["campo"].isin(("Factor", CAMPO_PRECIO))
    a_n, d_n = d["antes"].map(_numero), d["despues"].map(_numero)
    igual = num & ((a_n - d_n).abs() <= 1e-9 * (1 + a_n.abs()))
    razon = (d_n / a_n).where((a_n > 0) & (d_n > 0))
    chico = (d["campo"] == CAMPO_PRECIO) & ~((razon >= PRECIO_SALTO)
                                             | (razon <= 1 / PRECIO_SALTO))
    d = d[~igual & ~chico]
    if d.empty:
        return pd.DataFrame(columns=cols)
    d = d.sort_values("t", kind="stable")
    # El mismo cambio anotado dos veces a menos de una hora: el primero.
    clave = ["cod", "campo", "antes", "despues"]
    previo = d.groupby(clave, sort=False)["t"].shift()
    d = d[previo.isna() | ((d["t"] - previo) > pd.Timedelta(hours=1))]
    d = d.assign(_g=np.where(d["guardado"] != "", d["guardado"],
                             d["t"].dt.floor("min").astype(str)))
    out = []
    for (_g, cod), x in d.groupby(["_g", "cod"], sort=False):
        campos = {}
        for r in x.itertuples(index=False):
            ant = r.u_antes or r.antes
            des = r.u_despues or r.despues
            if r.campo == "Tipo Descargo":
                ant = TIPOS_DESCARGO.get(r.antes, r.antes)
                des = TIPOS_DESCARGO.get(r.despues, r.despues)
            campos[r.campo] = (ant, des)
        out.append({"t": x["t"].iloc[0], "usr": x["usr"].iloc[0],
                    "pantalla": x["pantalla"].iloc[0], "cod": cod,
                    "guardado": x["guardado"].iloc[0], "campos": campos})
    return pd.DataFrame(out, columns=cols).sort_values("t").reset_index(drop=True)


def _nombres_del_arbol(nodos):
    """{código: nombre} de todo el árbol: insumos, recetas base y cortes."""
    acc = {}

    def bajar(n):
        acc.setdefault(n["cod"], n.get("ins", n["cod"]))
        for h in n.get("hijos", ()):
            bajar(h)
    for n in nodos:
        bajar(n)
    return acc


def _texto_campos(campos):
    """«factor 1000 → 1, unidad de salida GRAMOS → UND»."""
    partes = []
    for c in CAMPOS_ARTICULO + (CAMPO_PRECIO,) + CAMPOS_PLATO:
        if c in campos:
            a, b = campos[c]
            partes.append(f"{c.lower()} {a or '—'} → {b or '—'}")
    return ", ".join(partes)


def _veces_factor(campos):
    """Cuántas veces sube el costo de una receta que no se tocó: el factor
    de antes ÷ el de después (cantidad × precio ÷ factor). None si no se
    cambió el factor o si baja."""
    if "Factor" not in campos:
        return None
    a, b = (_numero(v) for v in campos["Factor"])
    if not (a > 0 and b > 0) or a <= b:
        return None
    return a / b


def cambios_del_plato(cambios, nodos, cod_plato):
    """Los cambios de la auditoría que tocan al plato: los de factor, unidad
    y precio de los artículos de su receta de HOY (con las recetas base
    abiertas) y los de descargo del plato mismo. Dicts t, usr, cod, nombre,
    txt, veces (o None), del_plato. Pura."""
    if cambios is None or len(cambios) == 0:
        return []
    nombres = _nombres_del_arbol(nodos)
    plato = str(cod_plato).strip()
    out = []
    for r in cambios.itertuples(index=False):
        del_plato = r.pantalla == PANTALLA_PLATO and r.cod == plato
        if not del_plato and not (r.pantalla == PANTALLA_ARTICULO and r.cod in nombres):
            continue
        validos = CAMPOS_PLATO if del_plato else CAMPOS_ARTICULO + (CAMPO_PRECIO,)
        campos = {c: v for c, v in r.campos.items() if c in validos}
        if not campos:
            continue
        out.append({"t": r.t, "usr": r.usr, "cod": r.cod,
                    "nombre": "el plato" if del_plato else nombres[r.cod],
                    "txt": _texto_campos(campos), "veces": _veces_factor(campos),
                    "del_plato": del_plato})
    return out


def _causa_auditoria(cambios, nodos, cod_plato, ini):
    """El cambio de la auditoría que explica un pico: el de factor o de
    unidad de un artículo del plato (o un salto de su precio de costo, o el
    descargo del plato) entre `DIAS_CAUSA_AUDITORIA` días antes del pico y
    el día mismo, contado en una frase. Vacío si no hay."""
    desde = ini - pd.Timedelta(days=DIAS_CAUSA_AUDITORIA)
    hasta = ini + pd.Timedelta(days=1)
    cerca = [c for c in cambios_del_plato(cambios, nodos, cod_plato)
             if desde <= c["t"] < hasta]
    if not cerca:
        return ""
    frases = []
    for c in cerca[-2:]:
        usr = f" · {c['usr']}" if c["usr"] else ""
        veces = (f": una receta que lo pide como antes cuesta {c['veces']:,.0f} "
                 "veces más" if c["veces"] and c["veces"] >= 2 else "")
        frases.append(f"el {c['t']:%d/%m %H:%M}{usr} se cambió {c['nombre']} "
                      f"({c['txt']}){veces}")
    return "Posible causa: " + "; ".join(frases) + "."
