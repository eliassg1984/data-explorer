"""
articulos_nuevos.py — las cuentas de Recetas › Nuevo Costeo para lo que el
almacén TODAVÍA NO TIENE, y el «dónde se usa» de lo que sí tiene (regla #597).

Puro: pandas y nada más, sin Streamlit ni R2. Lo prueba
`test_graficos.py::_pruebas_articulos_nuevos` con parquets de mentira; la
pantalla (`formulario_receta.py`) sólo dibuja lo que esto devuelve.

TRES CLASES DE ARTÍCULO NUEVO, las mismas que distingue el almacén por el
prefijo del nombre:

  · insumo de COMPRA — sin código todavía. Su precio lo ESTIMA quien arma la
    receta, y entra al costo con un aviso en el panel de precio (decisión
    del usuario, 2026-10-03).
  · (P) PORCIONADO — sale de porcionar o limpiar un insumo. Se costea POR
    RENDIMIENTO (la otra opción del mockup, el porcionamiento completo, se
    descartó ese mismo día): lo que pesa una unidad ÷ (1 − merma) es lo que
    se gasta del insumo de entrada, y eso por su precio. La merma que se
    propone es la de ESE insumo en sus porcionamientos de los últimos 90
    días, Σ merma ÷ Σ porcionado contando cada porcionamiento UNA vez: la
    cabecera se repite en cada corte y sumarla por fila la infla (regla
    #510).
  · (Rs) RECETA BASE — sus insumos ÷ lo que rinde. El sistema guarda una
    receta base como los insumos de UNA unidad de salida (`RB COSTO` es el
    costo de 1 KILO); acá se deja escribir cuánto rinde la tanda y se
    divide.

Y «dónde se usa» cuenta también lo INDIRECTO (pedido el mismo día): la
Demiglace punteada está en 5 platos, pero además en la Salsa de Pimienta,
que está en el Lomo a la Pimienta — cambiar la Demiglace cambia ese plato
también.
"""

import pandas as pd

# Unidad de KARDEX → (unidad en que la escriben las recetas, cuántas caben
# en una de kardex). La misma que usa el sistema cuando el insumo no aparece
# en ninguna receta (1.255 pares KILOS→GRAMOS y 480 LITROS→MILILITROS con
# FACTOR 1000); `graficos/recetas_comun.py` la importa de acá.
CONVERSION_ESTANDAR = {"KILOS": ("GRAMOS", 1000.0),
                       "LITROS": ("MILILITROS", 1000.0)}

# Unidades de salida que se cuentan por pieza: llevan un peso por unidad.
POR_PIEZA = ("UND", "PORCION")

VENTANA_DIAS = 90
"""Los porcionamientos que cuentan para la merma propuesta. La misma
ventana que usa el consumo según recetas (`consumo_recetas.VENTANA_DIAS`)."""


def unidad_de_costeo(unidad):
    """(unidad en que la usa una receta, cuántas caben en una `unidad`)."""
    u = str(unidad or "").strip().upper()
    return CONVERSION_ESTANDAR.get(u, (u or "UND", 1.0))


# ─── (P) porcionado ──────────────────────────────────────────────────────
def entrada_por_unidad(unidad_entrada, unidad_salida, peso_g, merma_pct):
    """Cuánto insumo de ENTRADA, en su unidad de kardex, se gasta por cada
    unidad que sale del porcionamiento. None si la merma no deja nada.

    Una pieza (UND, PORCION) que sale de algo que se pesa (KILOS, LITROS)
    gasta su peso; lo que sale a granel, una unidad de lo que entró. Las
    dos, divididas por lo que queda después de la merma."""
    m = float(merma_pct or 0) / 100
    if not 0 <= m < 1:
        return None
    pesa = str(unidad_entrada).upper() in CONVERSION_ESTANDAR
    if pesa and str(unidad_salida).upper() in POR_PIEZA:
        base = float(peso_g or 0) / 1000
    else:
        base = 1.0
    return base / (1 - m)


def merma_y_cortes(po, cod, desde=None):
    """Lo que dicen los porcionamientos del insumo `cod` desde `desde`.

    `po` trae las columnas de porcionamientos.parquet (una fila por CORTE).
    Devuelve un dict con `n` (porcionamientos), `porcionado` (Σ de lo que
    entró, en la unidad del insumo), `merma_pct` (None sin porcionamientos)
    y `cortes`: un DataFrame con un renglón por producto que salió —
    `cod`, `nombre`, `unidad`, `n`, `cant`, `peso_x_und` (kg) y
    `entrada_x_und`, lo que se gastó del insumo por unidad de ese corte.

    La entrada se reparte entre los cortes por PESO, que es como lo hace el
    propio Almacén: Σ PESO RESULT = CANT TOT RESUL en 7.657 de 7.660
    porcionamientos y el costo por kilo de salida sale igual en todos sus
    cortes (medido el 2026-09-28)."""
    vacio = {"n": 0, "porcionado": 0.0, "merma_pct": None,
             "cortes": pd.DataFrame(columns=["cod", "nombre", "unidad", "n", "cant",
                                             "peso_x_und", "entrada_x_und"])}
    faltan = {"COD PORC", "COD PROD INIC", "FEC REGIST", "CANT A PORCIONAR",
              "CANT TOT RESUL", "CANT MERMA", "COD PROD FINAL", "PROD FINAL RESULT",
              "CANT RESULT", "UNID PROD FIN", "PESO RESULT"} - set(getattr(po, "columns", []))
    if po is None or po.empty or faltan:
        return vacio
    d = po[po["COD PROD INIC"].astype(str) == str(cod)]
    if desde is not None:
        d = d[pd.to_datetime(d["FEC REGIST"], errors="coerce") >= pd.Timestamp(desde)]
    if d.empty:
        return vacio
    def num(c):
        return pd.to_numeric(d[c], errors="coerce").fillna(0.0)

    d = d.assign(_porc=num("CANT A PORCIONAR"), _tot=num("CANT TOT RESUL"),
                 _merma=num("CANT MERMA"), _cant=num("CANT RESULT"),
                 _peso=num("PESO RESULT"))
    cab = d.drop_duplicates("COD PORC")
    porcionado = float(cab["_porc"].sum())
    merma = float(cab["_merma"].sum())
    d = d[d["_tot"] > 0]
    d = d.assign(_entrada=d["_porc"] * d["_peso"] / d["_tot"])
    g = (d.groupby(["COD PROD FINAL", "PROD FINAL RESULT", "UNID PROD FIN"])
         .agg(n=("COD PORC", "nunique"), cant=("_cant", "sum"),
              peso=("_peso", "sum"), entrada=("_entrada", "sum"))
         .reset_index())
    g = g[g["cant"] > 0]
    cortes = pd.DataFrame({
        "cod": g["COD PROD FINAL"].astype(str),
        "nombre": g["PROD FINAL RESULT"].astype(str),
        "unidad": g["UNID PROD FIN"].astype(str),
        "n": g["n"].astype(int),
        "cant": g["cant"],
        "peso_x_und": g["peso"] / g["cant"],
        "entrada_x_und": g["entrada"] / g["cant"],
    }).sort_values(["n", "nombre"], ascending=[False, True], kind="stable")
    return {"n": int(cab["COD PORC"].nunique()), "porcionado": porcionado,
            "merma_pct": (merma / porcionado * 100) if porcionado > 0 else None,
            "cortes": cortes.reset_index(drop=True)}


# ─── (Rs) receta base ────────────────────────────────────────────────────
def costo_receta_base(lineas, rinde):
    """(costo de la tanda, costo por unidad de salida). `lineas` son dicts
    con `cantidad` y `precio` (en la unidad de costeo de cada insumo)."""
    total = sum(float(l["cantidad"]) * float(l["precio"]) for l in lineas)
    r = float(rinde or 0)
    return total, (total / r if r > 0 else 0.0)


# ─── Dónde se usa ────────────────────────────────────────────────────────
def indice_usos(rv, rb):
    """Lo que hace falta para contestar «dónde se usa» rápido, armado UNA vez.

    `rv`: las líneas de las recetas de venta ACTIVAS, con columnas `plato`
    (código), `nombre`, `ins`, `cant`, `unid`, `pv` y `pct` (el % de costo
    del sistema, sobre el neto). `rb`: las líneas de las recetas base
    ACTIVAS, con `base` (el código del producto que sale), `nombre`, `ins`,
    `cant` y `unid`. Los dos ya filtrados: qué es «activo» lo decide quien
    lee los parquets, con `recetas_comun._activo`.

    Opcionales, para `impacto`: `factor` en las dos (cuántas unidades de
    costeo caben en una de kardex: 1000 gramos en un kilo; sin la columna
    se deduce de la unidad) y `cst` en `rv` (el costo del plato)."""
    def factor_de(r):
        f = float(getattr(r, "factor", 0) or 0)
        if f > 0:
            return f
        return CONVERSION_ESTANDAR.get({"GRAMOS": "KILOS", "MILILITROS": "LITROS"}.get(
            str(r.unid).strip().upper(), ""), ("", 1.0))[1]

    platos = {}
    for r in rv.itertuples(index=False):
        p = platos.setdefault(str(r.plato), {
            "nombre": str(r.nombre), "pv": float(r.pv), "pct": float(r.pct),
            "cst": float(getattr(r, "cst", 0) or 0), "lleva": {}, "factor": {}})
        k = str(r.ins)
        cant, unid = p["lleva"].get(k, (0.0, str(r.unid)))
        p["lleva"][k] = (cant + float(r.cant), unid)
        p["factor"][k] = factor_de(r)
    bases = {}
    for r in rb.itertuples(index=False):
        b = bases.setdefault(str(r.base), {"nombre": str(r.nombre), "lleva": {}, "factor": {}})
        k = str(r.ins)
        cant, unid = b["lleva"].get(k, (0.0, str(r.unid)))
        b["lleva"][k] = (cant + float(r.cant), unid)
        b["factor"][k] = factor_de(r)
    en_platos, en_bases = {}, {}
    for cod, p in platos.items():
        for ins in p["lleva"]:
            en_platos.setdefault(ins, []).append(cod)
    for cod, b in bases.items():
        for ins in b["lleva"]:
            en_bases.setdefault(ins, []).append(cod)
    return {"platos": platos, "bases": bases, "en_platos": en_platos,
            "en_bases": en_bases}


def _cant(par):
    cant, unid = par
    u = {"GRAMOS": "g", "MILILITROS": "ml"}.get(str(unid).upper(), str(unid).lower())
    return f"{round(cant, 3):g} {u}".strip()


def usos_de(indice, cod):
    """Las recetas activas que llevan `cod`, directo o a través de recetas
    base. Una lista de dicts con `receta`, `clase` («Plato» o «Receta
    base»), `via` (vacío si lo lleva directo; si no, la receta base por la
    que le llega), `cant` (lo que lleva de `cod`, o de su vía), `pv` y
    `pct` (sólo los platos). Primero los platos y después las bases; en
    cada grupo, lo directo antes que lo indirecto, y por nombre.

    Se sube por las recetas base a lo ancho, así que la vía de cada receta
    es la del camino MÁS CORTO. Una receta base que se contiene a sí misma
    (no debería, pero el parquet no lo impide) no cuelga la búsqueda: cada
    base se visita una vez."""
    cod = str(cod)
    platos, bases = indice["platos"], indice["bases"]
    # Cada base que lleva `cod`, con el hijo por el que le llega (None si
    # lo lleva ella misma).
    hijo_de = {}
    frente = [(b, None) for b in indice["en_bases"].get(cod, [])]
    while frente:
        siguiente = []
        for b, hijo in frente:
            if b in hijo_de or b == cod:
                continue
            hijo_de[b] = hijo
            siguiente += [(padre, b) for padre in indice["en_bases"].get(b, [])]
        frente = siguiente

    def plato(p, via, de):
        return {"cod": p, "receta": platos[p]["nombre"], "clase": "Plato", "via": via,
                "cant": _cant(platos[p]["lleva"][de]),
                "pv": platos[p]["pv"], "pct": platos[p]["pct"]}

    directos = [plato(p, "", cod) for p in indice["en_platos"].get(cod, [])]
    vistos = set(indice["en_platos"].get(cod, []))
    indirectos = []
    for b in hijo_de:
        for p in indice["en_platos"].get(b, []):
            if p not in vistos:
                vistos.add(p)
                indirectos.append(plato(p, bases[b]["nombre"], b))
    filas = []
    for grupo in (directos, indirectos):
        filas += sorted(grupo, key=lambda f: f["receta"].lower())
    for directa in (True, False):
        grupo = []
        for b, hijo in hijo_de.items():
            if (hijo is None) != directa:
                continue
            de = cod if hijo is None else hijo
            grupo.append({"cod": b, "receta": bases[b]["nombre"], "clase": "Receta base",
                          "via": "" if hijo is None else bases[hijo]["nombre"],
                          "cant": _cant(bases[b]["lleva"][de]), "pv": None, "pct": None})
        filas += sorted(grupo, key=lambda f: f["receta"].lower())
    return filas


def impacto(indice, cod, delta):
    """Cuánto cambia el costo de cada receta activa si el de `cod` cambia en
    `delta` soles por unidad de KARDEX (por kilo, por litro, por unidad).

    Devuelve `{"platos": {cod: Δ costo del plato}, "bases": {cod: Δ por su
    unidad}}`. Sube por las recetas base como lo hace el costeo del
    sistema: una receta base guarda los insumos de UNA unidad de salida, así
    que lo que lleva de un hijo (en su unidad de costeo) ÷ el factor por el
    Δ del hijo es su Δ. Un plato que lo lleva por dos caminos suma los dos:
    los dos son de verdad. Un ciclo (una receta que se contiene) aporta 0."""
    cod = str(cod)
    bases, platos = indice["bases"], indice["platos"]
    alcanzables, frente = set(), list(indice["en_bases"].get(cod, []))
    while frente:
        b = frente.pop()
        if b in alcanzables or b == cod:
            continue
        alcanzables.add(b)
        frente += indice["en_bases"].get(b, [])
    memo, en_curso = {}, set()

    def d(x):
        if x == cod:
            return float(delta)
        if x in memo:
            return memo[x]
        if x in en_curso or x not in bases:
            return 0.0
        en_curso.add(x)
        b = bases[x]
        tot = sum(cant / (b["factor"].get(h) or 1.0) * d(h)
                  for h, (cant, _u) in b["lleva"].items() if h == cod or h in alcanzables)
        en_curso.discard(x)
        memo[x] = tot
        return tot

    afectados = {cod} | alcanzables
    out_platos = {}
    for p, info in platos.items():
        hijos = [h for h in info["lleva"] if h in afectados]
        if hijos:
            out_platos[p] = sum(info["lleva"][h][0] / (info["factor"].get(h) or 1.0) * d(h)
                                for h in hijos)
    return {"platos": out_platos, "bases": {b: d(b) for b in alcanzables}}


def resumen_usos(filas):
    """«11 platos · 7 bases», o «sin usos»: lo que va en la tabla."""
    n_p = sum(1 for f in filas if f["clase"] == "Plato")
    n_b = len(filas) - n_p
    if not filas:
        return "sin usos"
    partes = []
    if n_p:
        partes.append(f"{n_p} {'plato' if n_p == 1 else 'platos'}")
    if n_b:
        partes.append(f"{n_b} {'base' if n_b == 1 else 'bases'}")
    return " · ".join(partes)


# ─── Cómo se dice ────────────────────────────────────────────────────────
def por_unidad(unidad):
    """«el kilo», «la unidad», «el gramo»: para «S/ 74.50 el kilo»."""
    u = str(unidad or "").strip().upper()
    return {"KILOS": "el kilo", "LITROS": "el litro", "UND": "la unidad",
            "PORCION": "la porción", "PORCIÓN": "la porción", "GRAMOS": "el gramo",
            "MILILITROS": "el ml"}.get(u, f"por {u.lower()}" if u else "por unidad")


def describir(d):
    """Una línea que dice qué es un artículo nuevo y de dónde sale su costo.
    `d` es lo que guarda la propuesta (`formulario_receta._detalle_nuevos`);
    la usan el visor de Guardadas, el PDF, el Excel y el correo."""
    n, clase = d.get("nombre", "?"), d.get("clase")
    if clase == "p":
        if not d.get("costo_por_unidad"):
            return f"{n}: porcionado nuevo, SIN DETALLE (cuenta S/ 0.00)."
        pieza = (f"{d['peso_g']:g} g por unidad, " if d.get("salida") in POR_PIEZA
                 and str(d.get("sale_de_unidad", "")).upper() in CONVERSION_ESTANDAR else "")
        origen = "nuevo" if d.get("sale_de_nuevo") else d.get("sale_de")
        return (f"{n}: porcionado nuevo. Sale de {d.get('sale_de_nombre')} "
                f"({origen}, S/ {d.get('sale_de_precio', 0):,.2f} "
                f"{por_unidad(d.get('sale_de_unidad'))}); {pieza}merma "
                f"{d.get('merma_pct') or 0:.1f} % → {d.get('entrada_por_unidad', 0):.3f} "
                f"{str(d.get('sale_de_unidad', '')).lower()} por unidad, "
                f"S/ {d['costo_por_unidad']:,.2f} {por_unidad(d.get('salida'))}.")
    if clase == "rs":
        lineas = d.get("lineas") or []
        if not d.get("costo_por_unidad"):
            return f"{n}: receta base nueva, SIN DETALLE (cuenta S/ 0.00)."
        insumos = ", ".join(f"{l['nombre']} {cantidad_en(l['cantidad'], l['unidad'])}"
                            + (" (nuevo)" if l.get("tipo") == "nuevo" else "")
                            for l in lineas)
        return (f"{n}: receta base nueva ({d.get('area', '')}). Rinde "
                f"{cantidad_en(d.get('rinde', 1), d.get('unidad_rinde'))} con "
                f"{insumos}; S/ {d['costo_por_unidad']:,.2f} "
                f"{por_unidad(d.get('unidad_rinde'))}.")
    if clase == "producto":
        return f"{n}: producto nuevo, costo ESTIMADO S/ {d.get('precio', 0):,.2f}."
    return (f"{n}: insumo de compra nuevo, precio ESTIMADO S/ "
            f"{d.get('precio_kardex_estimado', d.get('precio', 0)):,.2f} "
            f"{por_unidad(d.get('unidad_kardex') or d.get('unidad'))}.")


_SINGULAR = {"KILOS": "kilo", "LITROS": "litro", "UND": "unidad", "PORCION": "porción",
             "GRAMOS": "g", "MILILITROS": "ml"}
_PLURAL = {"KILOS": "kilos", "LITROS": "litros", "UND": "unidades", "PORCION": "porciones",
           "GRAMOS": "g", "MILILITROS": "ml"}


def cantidad_en(cant, unidad):
    """«1 kilo», «2.5 kilos», «180 g», «1 unidad»: una cantidad para leer."""
    u = str(unidad or "").strip().upper()
    c = float(cant or 0)
    nombre = (_SINGULAR if abs(c - 1) < 1e-9 else _PLURAL).get(u, u.lower())
    return f"{round(c, 3):g} {nombre}".strip()


def nombre_unidad(unidad):
    """«kilo», «unidad», «porción»: la unidad en singular, para «por kilo»."""
    u = str(unidad or "").strip().upper()
    return _SINGULAR.get(u, u.lower() or "unidad")


_ETIQUETA = {"rs": "Receta base nueva", "p": "Porcionado nuevo",
             "compra": "Insumo de compra nuevo", "producto": "Producto nuevo"}


def _n(v):
    return f"{round(float(v or 0), 4):,.4f}".rstrip("0").rstrip(".")


def bloques_detalle(d):
    """El detalle de un artículo nuevo como lo dibujan el PDF y el Excel
    (regla #607): `titulo`, `etiqueta`, `resumen` (una frase), una tabla
    (`cabecera` y `filas`, listas de texto) y un `pie` de (rótulo, valor).
    Una receta base, sus insumos; un porcionado, de dónde sale y su
    rendimiento; una compra, su precio estimado."""
    clase = d.get("clase")
    costo = float(d.get("costo_por_unidad") or 0)
    una = nombre_unidad(d.get("unidad_kardex"))
    etiqueta = _ETIQUETA.get(clase, "Nuevo") + ("" if costo > 0 else " · SIN DETALLE")
    b = {"titulo": d.get("nombre", "?"), "etiqueta": etiqueta, "resumen": "",
         "cabecera": [], "filas": [], "pie": []}
    if clase == "rs":
        b["etiqueta"] += f" · {d.get('area', '')}" if d.get("area") else ""
        b["resumen"] = (f"Rinde {cantidad_en(d.get('rinde', 1), d.get('unidad_rinde'))}. "
                        "Lo marcado NUEVO tampoco está en el almacén: su detalle va aparte.")
        b["cabecera"] = ["Código", "Insumo", "Unidad", "Cant.", "P. unit.", "Subtotal"]
        b["filas"] = [["NUEVO" if l.get("tipo") == "nuevo" else str(l["cod"]),
                       str(l["nombre"]), str(l["unidad"]), _n(l["cantidad"]), _n(l["precio"]),
                       f"{float(l['cantidad']) * float(l['precio']):,.2f}"]
                      for l in d.get("lineas") or []]
        b["pie"] = [(f"Costo de {cantidad_en(d.get('rinde', 1), d.get('unidad_rinde'))}",
                     f"S/ {float(d.get('costo_tanda') or 0):,.2f}"),
                    (f"Costo por {una}", f"S/ {costo:,.2f}")]
    elif clase == "p":
        u_ent = d.get("sale_de_unidad")
        pieza = (d.get("salida") in POR_PIEZA
                 and str(u_ent or "").upper() in CONVERSION_ESTANDAR)
        b["resumen"] = "Costeado por rendimiento: lo que pesa una pieza ÷ (1 − merma)."
        b["cabecera"] = ["Concepto", "Valor"]
        b["filas"] = [
            ["Sale de", f"{d.get('sale_de_nombre') or '—'}"
                        + (" (nuevo)" if d.get("sale_de_nuevo") else
                           f" ({d.get('sale_de')})" if d.get("sale_de") else "")],
            ["Precio de lo que entra",
             f"S/ {float(d.get('sale_de_precio') or 0):,.2f} {por_unidad(u_ent)}"],
            ["Sale en", str(d.get("salida") or "—")],
        ] + ([["Peso por unidad", f"{float(d.get('peso_g') or 0):g} g"]] if pieza else []) + [
            ["Merma", f"{float(d.get('merma_pct') or 0):.1f} %"],
            [f"Insumo por {una}", cantidad_en(d.get("entrada_por_unidad") or 0, u_ent)
             if d.get("entrada_por_unidad") else "—"],
        ]
        b["pie"] = [(f"Costo por {una}", f"S/ {costo:,.2f}")]
    elif clase == "producto":
        b["resumen"] = f"Costo ESTIMADO S/ {float(d.get('precio') or 0):,.2f} por porción."
    else:
        b["resumen"] = (f"Precio ESTIMADO S/ {costo:,.2f} "
                        f"{por_unidad(d.get('unidad_kardex'))}, hasta que el almacén lo cree.")
    return b


def _recorte(texto, n):
    return texto if len(texto) <= n else texto[:n - 1].rstrip() + "…"


def bloque_impacto(filas, base):
    """«A quién afecta» una receta base modificada, como bloque del PDF y
    del Excel (mismo formato que `bloques_detalle`). `filas` las arma
    `formulario_receta._calculo_base`."""
    una = nombre_unidad(base.get("unidad"))

    def pct(v, combo):
        return "en combo" if combo else ("—" if v is None else f"{v:.1f} %")

    def signo(v):
        return f"{float(v):+,.2f}".replace("-", "−")

    return {
        "titulo": "A quién afecta",
        "etiqueta": "recetas activas que la llevan",
        "resumen": (f"Por {una}: S/ {float(base.get('actual') or 0):,.2f} en el sistema → "
                    f"S/ {float(base.get('por') or 0):,.2f} con esta propuesta. En un plato, "
                    "Δ es por plato; en una receta base, por su unidad."),
        "cabecera": ["Receta", "Es", "% hoy", "% nuevo", "Δ costo"],
        "filas": [[_recorte(str(r["receta"]) + (f" (por {r['via']})" if r.get("via") else ""),
                            58),
                   r["es"], pct(r["pct_actual"], r["combo"]), pct(r["pct_nuevo"], r["combo"]),
                   signo(r["delta"])] for r in filas],
        "pie": [],
    }
