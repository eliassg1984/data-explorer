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
    lee los parquets, con `recetas_comun._activo`."""
    platos = {}
    for r in rv.itertuples(index=False):
        p = platos.setdefault(str(r.plato), {"nombre": str(r.nombre), "pv": float(r.pv),
                                             "pct": float(r.pct), "lleva": {}})
        k = str(r.ins)
        cant, unid = p["lleva"].get(k, (0.0, str(r.unid)))
        p["lleva"][k] = (cant + float(r.cant), unid)
    bases = {}
    for r in rb.itertuples(index=False):
        b = bases.setdefault(str(r.base), {"nombre": str(r.nombre), "lleva": {}})
        k = str(r.ins)
        cant, unid = b["lleva"].get(k, (0.0, str(r.unid)))
        b["lleva"][k] = (cant + float(r.cant), unid)
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
        return {"receta": platos[p]["nombre"], "clase": "Plato", "via": via,
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
            grupo.append({"receta": bases[b]["nombre"], "clase": "Receta base",
                          "via": "" if hijo is None else bases[hijo]["nombre"],
                          "cant": _cant(bases[b]["lleva"][de]), "pv": None, "pct": None})
        filas += sorted(grupo, key=lambda f: f["receta"].lower())
    return filas


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
        return (f"{n}: porcionado nuevo. Sale de {d.get('sale_de_nombre')} "
                f"({d.get('sale_de')}, S/ {d.get('sale_de_precio', 0):,.2f} "
                f"{por_unidad(d.get('sale_de_unidad'))}); {pieza}merma "
                f"{d.get('merma_pct') or 0:.1f} % → {d.get('entrada_por_unidad', 0):.3f} "
                f"{str(d.get('sale_de_unidad', '')).lower()} por unidad, "
                f"S/ {d['costo_por_unidad']:,.2f} {por_unidad(d.get('salida'))}.")
    if clase == "rs":
        lineas = d.get("lineas") or []
        if not d.get("costo_por_unidad"):
            return f"{n}: receta base nueva, SIN DETALLE (cuenta S/ 0.00)."
        insumos = ", ".join(f"{l['nombre']} {round(l['cantidad'], 3):g} {l['unidad'].lower()}"
                            for l in lineas)
        return (f"{n}: receta base nueva ({d.get('area', '')}). Rinde "
                f"{d.get('rinde', 1):g} {str(d.get('unidad_rinde', '')).lower()} con "
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
