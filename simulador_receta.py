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

import pandas as pd

VERSION = 1

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


def alza(exposiciones, carta, insumo, pct):
    """Cada plato que lleva `insumo`, con su costo y su % de costo si el
    insumo sube `pct` %. `carta`: DataFrame con Cod, Producto, Grupo,
    Subgrupo, Precio, Neto, Costo y, si se cargaron, Vendidos (90 días).
    Devuelve un DataFrame ordenado por el costo de más al mes."""
    cols = ["Cod", "Producto", "Grupo", "Subgrupo", "Lleva", "Parte", "Precio",
            "Neto", "Costo", "CostoNuevo", "PctHoy", "PctNuevo",
            "PrecioMantener", "Vendidos", "DeltaMes"]
    if carta is None or carta.empty:
        return pd.DataFrame(columns=cols)
    k = pct / 100.0
    filas = []
    for r in carta.itertuples(index=False):
        e = exposiciones.get(str(r.Cod).strip(), {}).get(insumo, 0.0)
        if e <= 0 or not r.Neto or r.Neto <= 0:
            continue
        costo = float(r.Costo) if r.Costo and r.Costo > 0 else sum(
            exposiciones.get(str(r.Cod).strip(), {}).values())
        nuevo = costo + e * k
        vend = float(getattr(r, "Vendidos", 0.0) or 0.0)
        filas.append({
            "Cod": r.Cod, "Producto": r.Producto, "Grupo": r.Grupo,
            "Subgrupo": r.Subgrupo, "Lleva": e,
            "Parte": e / costo * 100 if costo else 0.0,
            "Precio": float(r.Precio), "Neto": float(r.Neto), "Costo": costo,
            "CostoNuevo": nuevo, "PctHoy": costo / r.Neto * 100,
            "PctNuevo": nuevo / r.Neto * 100,
            "PrecioMantener": float(r.Precio) * nuevo / costo if costo else float(r.Precio),
            "Vendidos": vend, "DeltaMes": e * k * vend / 3.0,
        })
    out = pd.DataFrame(filas, columns=cols)
    if out.empty:
        return out
    return out.sort_values(["DeltaMes", "Lleva"], ascending=False,
                           key=lambda s: s.abs()).reset_index(drop=True)
