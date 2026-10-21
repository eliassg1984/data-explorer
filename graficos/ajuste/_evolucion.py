"""graficos.ajuste._evolucion - la categoria Tiempo de Ajuste, en UNA vista.

Hasta el 2026-09-23 la categoria Tiempo eran TRES items del rail que
miraban el mismo cubo de datos —ajuste valorizado x tiempo x familia/
producto— con tres formas distintas:

    Evolucion             lineas, una por familia, por fecha de apertura
    Comparativa mensual   barras del neto por mes (sin comparar nada)
    Por fecha de corte    la tabla pivote, con el año en curso FIJO

Comparativa era la fila Total de la tabla con «Mes»; Evolucion, su nivel
Familia con «Corte». Y las tres sumaban el NETO: un mes con +S/ 105k de
sobrante y -S/ 116k de faltante (set 2026, medido) salia como -S/ 11k, o
sea como un mes tranquilo, cuando es el peor del año. Se fusionaron a
pedido («creo que dan similar informacion») en esta vista:

    1. La SERIE: sobrante hacia arriba, faltante hacia abajo y el neto como
       linea encima. Lo que se cancela se VE.
    2. Debajo, quien la explica: hasta el 2026-10-21 los MINI-GRAFICOS por
       familia; desde ese dia la MATRIZ familia × mes (regla #692).
    3. La TABLA pivote de siempre (`_pivote.py`), con los MISMOS periodos
       (`periodos_ajuste`, de aca).

Serie y familias van en UNA tarjeta, con el grano en su cabecera; la tabla,
desde el mismo dia, es su propia vista del rail («Detalle por producto»),
con su propio grano (regla #504).

DESDE EL 2026-10-21 ES UNA PIEZA PROPIA (regla #692): el boceto aprobado
(https://claude.ai/artifact/TNvQPfrb4Ty7RQVHvUtPjF), en
`evolucion_ajuste.js`. Rojo y verde de entrada, y «Explicar con» suma de a
uno los POSIBLES ORIGENES (la primera pista de cada linea en «Analisis de
diferencias»): a pedido, «que los colores no se muestren todos a la vez».

EL «%» QUE SE DESCARTO EL 2026-09-23, Y EL QUE ENTRO. Un «% de merma» sobre
el valor del periodo se midio contra el parquet real y daba cualquier cosa:
sobre lo CONTADO, ago 26 -65 % (si falta casi todo, lo contado es casi
cero); sobre el sistema ENTERO, set 26 -99 %, porque 10.188 filas tienen
stock NEGATIVO y restan del denominador. El 2026-10-21 el usuario lo pidio
con su ejemplo («tenia 1 kg de harina a 2 soles, se ajusto -0,5 kg: perdi
el 50 %»), y entro con dos cambios que lo hacen creible
(`sistema_por_periodo`): la base es sólo el stock POSITIVO del sistema, y
el ajuste de lo que estaba en cero o en negativo va APARTE, en soles. Junto
a el va el neto como % del CONSUMO del mes (`pct_consumo`), que mide otra
cosa: cuanto se perdio de lo que paso por el restaurante.
"""

import math
from pathlib import Path

import pandas as pd
import streamlit as st

import costo_ventas
import data
import definicion_venta
import diferencias_ajuste
from cortes import sesiones_inventario
from tema import (
    AJUSTE_ALERTA_TEXTO, AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_ORIGEN_NEG,
    AJUSTE_ORIGEN_PRO, AJUSTE_ORIGEN_REG, AJUSTE_ORIGEN_VEN, AJUSTE_POS,
    AJUSTE_POS_TEXTO, GRIS_TEXTO_SUAVE, TEXTO_PRINCIPAL,
)
from graficos.base import publicar_contexto_ia
from graficos import alturas
from graficos.ajuste._comun import (
    FAMILIAS_DE_ENTRADA, _MESES_ABR_ES, _periodo_pivote_ajuste,
    css_filtros_vista, ctx_meses, fechas_del_mes, filtro_area_en_titulo,
    mes_operativo_activo, rango_meses, recortar_meses, selector_meses,
)
from utils import fmt_k

# SIN «Semana» desde el 2026-10-02 (regla #585). El ajuste no pasa EN una
# semana: aparece el día en que se cuenta y mide lo acumulado desde el
# conteo anterior. Por semana, el eje juntaba barras separadas por una o
# por ocho semanas como si fueran vecinas, una sesión que cruzaba el lunes
# salía partida en dos, y lo demás era «Corte» con un rótulo peor.
GRANOS = ("Corte", "Mes")

_K_GRAN = "ajuste_evo_gran"

# Desde cuántos soles el neto según el kardex «difiere» del del cierre: por
# debajo es redondeo del precio promedio (regla #612).
TOL_KARDEX = 1.0

# Lo que dice el `title` de la leyenda y de la columna del kardex. Va en un
# atributo HTML entre comillas simples: sin apóstrofos.
AYUDA_KARDEX = (
    "El neto de los mismos conteos según el kardex del Almacén: el reporte "
    "«Movimientos por artículo», movimiento «Ajuste Inventarios». El de "
    "las barras es el del «Cierre y Ajuste de Inventario». Coinciden desde "
    "septiembre de 2025; antes, el stock al cierre de ese reporte quedó "
    "escrito como lo contado ±5 o ±10 %, y el ajuste que de verdad movió el "
    "stock es el del kardex. "
    "Donde coinciden, la línea punteada queda debajo de la del neto.")


# ── DATOS (puros: sin Streamlit, los prueba test_graficos.py) ────────────

def periodos_ajuste(d, col_fecha, gran, operativo=False):
    """Asigna a cada fila su periodo y arma la lista ORDENADA de periodos.

    Devuelve `(d_con_clave, orden)`: `d` con la columna `_clave`, y un
    DataFrame con `_clave`, `etq` (rotulo corto: la cabecera de la tabla,
    que ya dice el año en su grupo de columnas), `eje` (rotulo del eje de la
    serie: lleva el año cuando el rango cruza de año, porque «2 set» de 2025
    y de 2026 serian la MISMA categoria) y `anio`.

    En «Mes» se rellenan los meses sin conteo entre el primero y el ultimo:
    un mes sin sesion de inventario es un dato («no se conto»), y saltearlo
    pegaria dos meses que no son vecinos. En Corte no: cada periodo ES un
    conteo, y entre dos no hay nada que rellenar.

    `operativo`: el «Mes» de cada fila es su mes OPERATIVO —un cierre
    registrado del 1 al 6 es del mes anterior— (regla #613). Los cortes
    siguen con sus días de verdad.
    """
    d = d.copy()
    d[col_fecha] = pd.to_datetime(d[col_fecha], errors="coerce")
    d = d.dropna(subset=[col_fecha])
    cols = ["_clave", "etq", "eje", "anio"]
    if d.empty:
        return d.assign(_clave=pd.Series(dtype=str)), pd.DataFrame(columns=cols)

    f_mes = fechas_del_mes(d[col_fecha], operativo and gran == "Mes")
    clave, etq = _periodo_pivote_ajuste(f_mes, gran)
    d["_clave"] = clave.astype(str).values
    d["_etq"] = etq.astype(str).values

    # El año de un periodo es el de su ULTIMO dia: un corte de fin de
    # diciembre que termina en enero es un conteo de enero.
    orden = (d.groupby("_clave", as_index=False)
              .agg(etq=("_etq", "first"), fin=(col_fecha, "max")))
    orden["anio"] = orden["fin"].dt.year.astype(int)

    if gran == "Mes":
        meses = pd.period_range(f_mes.min().to_period("M"),
                                f_mes.max().to_period("M"), freq="M")
        orden = pd.DataFrame({
            "_clave": [str(m) for m in meses],
            "etq": [_MESES_ABR_ES[m.month - 1] for m in meses],
            "anio": [int(m.year) for m in meses],
        })
    else:
        orden = orden.sort_values("_clave").reset_index(drop=True)

    varios_anios = orden["anio"].nunique() > 1
    orden["eje"] = [f"{e} {str(a)[2:]}" if varios_anios else e
                    for e, a in zip(orden["etq"], orden["anio"])]
    return d.drop(columns=["_etq"]), orden[cols].reset_index(drop=True)


def serie_ajuste(d, orden, col_ajuste_val, col_valorizado=None, col_grupo=None,
                 col_kardex=None):
    """Sobrante, faltante, neto y valor contado por periodo (y por grupo).

    Una fila por periodo de `orden` —o por periodo x grupo—, INCLUIDOS los
    periodos sin datos (con NaN: la barra no se dibuja y la linea se corta,
    que es lo honesto). `contado` es la suma de `VALORIZADO TOTAL` (stock
    declarado x precio) de las filas contadas: contexto para el hover, NO
    el inventario del local — sumado sobre un mes con cuatro sesiones cuenta
    el stock cuatro veces.

    Con `col_kardex` (el ajuste valorizado que registró el kardex por cada
    línea, regla #612) suma además `kardex`: el neto de los MISMOS conteos
    según el kardex. NaN si ninguna línea del periodo tiene dato del kardex.

    Se agrupa por COLUMNAS con nombre y se devuelve por nombre: una clave
    suelta en el groupby da otra forma en pandas 2 que en 3 (regla #481).
    """
    base = ["_clave", "etq", "eje", "anio"]
    medidas = ["sobrante", "faltante", "neto", "contado"]
    v = pd.to_numeric(d[col_ajuste_val], errors="coerce").fillna(0.0)
    x = pd.DataFrame({
        "_clave": d["_clave"].values,
        "sobrante": v.clip(lower=0).values,
        "faltante": v.clip(upper=0).values,
        "neto": v.values,
        "contado": (pd.to_numeric(d[col_valorizado], errors="coerce")
                    .fillna(0.0).values
                    if col_valorizado and col_valorizado in d.columns
                    else 0.0),
    })
    if col_kardex and col_kardex in d.columns:
        # Sin `fillna`: una línea sin dato del kardex NO es un kardex en
        # cero, y el `min_count` de abajo lo deja en NaN.
        x["kardex"] = pd.to_numeric(d[col_kardex], errors="coerce").values
        medidas.append("kardex")
    llaves = ["_clave"]
    if col_grupo:
        x["grupo"] = d[col_grupo].astype(str).values
        # 122 filas del parquet no traen familia: sin esto serian un panel
        # «Nan».
        x = x[d[col_grupo].notna().values]
        llaves.append("grupo")
    agg = x.groupby(llaves, as_index=False)[medidas].sum(min_count=1)

    esqueleto = orden[base]
    if col_grupo:
        grupos = pd.DataFrame({"grupo": sorted(agg["grupo"].unique())})
        esqueleto = esqueleto.merge(grupos, how="cross")
    s = esqueleto.merge(agg, on=llaves, how="left")
    return s[base + (["grupo"] if col_grupo else []) + medidas]


def _fmt(v, signo=False):
    """Rotulo compacto del neto: «S/ -11.2k» (con `signo`, «S/ +5.5k»)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    txt = fmt_k(v)
    return txt.replace("S/ ", "S/ +", 1) if signo and v > 0 else txt


def con_kardex(s):
    """`True` si la serie trae el neto según el kardex en algún periodo."""
    return "kardex" in s.columns and bool(s["kardex"].notna().any())


def difiere_kardex(s):
    """Por periodo, `True` si el kardex dice otra cosa que el cierre (más de
    `TOL_KARDEX`). Un periodo sin dato del kardex no difiere: no se sabe."""
    if "kardex" not in s.columns:
        return pd.Series(False, index=s.index)
    return ((s["kardex"] - s["neto"]).abs() > TOL_KARDEX).fillna(False)


def nota_kardex(s, gran):
    """El remate del rótulo de abajo: en cuántos periodos de la serie el
    kardex dice otra cosa —en ámbar, con la explicación en el `title`—, o
    «igual al kardex» en gris si en ninguno. Vacío sin dato del kardex."""
    if not con_kardex(s):
        return ""
    n = int(difiere_kardex(s).sum())
    if n == 0:
        return (f" · <span style='color:{GRIS_TEXTO_SUAVE}' "
                f"title='{AYUDA_KARDEX}'>igual al kardex</span>")
    m = int(s["kardex"].notna().sum())
    unidad = ("cortes" if m > 1 else "corte") if gran == "Corte" else (
        "meses" if m > 1 else "mes")
    return (f" · <span style='color:{AJUSTE_ALERTA_TEXTO};font-weight:600;"
            f"cursor:help' title='{AYUDA_KARDEX}'>el kardex difiere en {n} "
            f"de {m} {unidad}</span>")


def orden_familias(sf):
    """Las familias en el orden en que se leen las filas de la matriz.

    Primero las de `FAMILIAS_DE_ENTRADA`, en SU orden —Alimentos, las dos
    bebidas, Vinos, Envases—, a pedido (2026-09-23: «mostrando primero
    alimentos, luego bebidas y luego vinos»): es el orden en que se piensa
    el negocio. Las demás (Costos producción, si el filtro la trae) van
    después, de mayor a menor ajuste BRUTO (|sobrante| + |faltante|)."""
    presentes = set(sf["grupo"])
    fijas = [f for f in FAMILIAS_DE_ENTRADA if f in presentes]
    resto = (sf[~sf["grupo"].isin(fijas)]
             .assign(_b=lambda x: x["sobrante"].fillna(0) - x["faltante"].fillna(0))
             .groupby("grupo", as_index=False)["_b"].sum()
             .sort_values("_b", ascending=False)["grupo"].tolist())
    return fijas + resto


# ── EL «% DEL SISTEMA» Y LOS POSIBLES ORÍGENES (regla #692) ────────────────

# Las columnas del parquet de ajuste que piden el % del sistema y el
# «sistema en negativo». Sin alguna, esas dos piezas no se dibujan.
COL_SISTEMA = "STOCK AL CIERRE"
COL_CONTADO = "STOCK DECLARADO"
COL_PRECIO = "PRECIO PROMEDIO"

# De la PRIMERA pista de cada línea de «Análisis de diferencias» a su
# posible origen. «neg» no está: el sistema en negativo es un HECHO de la
# línea (stock en el sistema < 0 y sobrante), y sale del propio parquet de
# ajuste (`negativo_por_periodo`) sin calcular ninguna pista. Lo que no
# está acá —«nada», «nadie», sin pista— es «sin pista».
ORIGEN_DE_PISTA = {
    "lote": "ven", "desc": "ven", "combo": "ven", "receta": "ven",
    "prod": "pro",
    "area": "reg", "rubro": "reg", "rev": "reg", "sinent": "reg",
    "sunat": "reg", "req": "reg", "uso": "reg",
}
ORIGENES = ("ven", "pro", "reg")


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def tiene_sistema(d):
    return all(c in d.columns for c in (COL_SISTEMA, COL_CONTADO, COL_PRECIO))


def negativo_por_periodo(dp, col_ajuste_val):
    """El sobrante de las líneas que el sistema tenía en NEGATIVO, por
    periodo: `{clave: soles}`. No es mercadería que apareció: es el conteo
    corrigiendo un descargo hecho sin ingreso. Barato —una cuenta sobre el
    mismo `dp` de la serie—, así que el botón «Sistema en negativo» de
    «Explicar con» no espera a ninguna pista."""
    if COL_SISTEMA not in dp.columns or dp.empty:
        return {}
    v = _num(dp[col_ajuste_val])
    m = (v > 0) & (_num(dp[COL_SISTEMA]) < 0)
    x = pd.DataFrame({"_clave": dp["_clave"].values, "v": v.where(m, 0.0).values})
    g = x.groupby("_clave", as_index=False)["v"].sum()
    return {k: round(float(v_), 2) for k, v_ in zip(g["_clave"], g["v"])}


def sistema_por_periodo(dp, col_fecha, col_ajuste_val, col_grupo, gran):
    """El ajuste como % de lo que el SISTEMA decía, por periodo y familia.

    `{grupo | "TOTAL": {clave: [sistema, faltante, sobrante, en_cero,
    negativo]}}` en soles, sobre UNA foto: en «Mes», sólo las líneas del
    CIERRE del mes (las sesiones `tipo == "cierre"` de
    `cortes.sesiones_inventario`); en «Corte», las de cada sesión. Sumar
    las parciales mezclaría el stock de días distintos.

    LA BASE ES EL STOCK POSITIVO del sistema (stock al cierre × precio de
    las líneas con stock > 0): de algo negativo no hay porcentaje, y con
    esas líneas restando el denominador agosto 2026 daba −147 %. El ajuste
    de las líneas en cero o en negativo va aparte (`negativo`), en soles.
    `en_cero` es la parte del faltante de líneas CONTADAS en cero: «se
    acabó sin registrarse» o «no se contó», dos problemas distintos.

    Es lo que la docstring del módulo descartaba hasta el 2026-10-21 («sin
    modo %»): el % sobre el sistema daba −99 % porque usaba el stock entero.
    Con la base positiva y lo negativo aparte el número se puede creer."""
    if not tiene_sistema(dp) or dp.empty:
        return {}
    ses = sesiones_inventario(pd.to_datetime(dp[col_fecha], errors="coerce"))
    if gran == "Mes":
        ses = [s for s in ses if s["tipo"] == "cierre"]
    dias = set()
    for s in ses:
        dias.update(s["dias"])
    dia = pd.to_datetime(dp[col_fecha], errors="coerce").dt.date
    x = dp[dia.isin(dias).values]
    if x.empty:
        return {}
    p = _num(x[COL_PRECIO])
    sis = _num(x[COL_SISTEMA]) * p
    cero = _num(x[COL_CONTADO]) == 0
    v = _num(x[col_ajuste_val])
    pos = sis > 0
    t = pd.DataFrame({
        "_clave": x["_clave"].values,
        "grupo": (x[col_grupo].astype(str).values if col_grupo else "TOTAL"),
        "sp": sis.where(pos, 0.0).values,
        "fp": v.clip(upper=0).where(pos, 0.0).values,
        "sb": v.clip(lower=0).where(pos, 0.0).values,
        "c0": v.where(pos & cero, 0.0).values,
        "ng": v.where(~pos, 0.0).values,
    })
    if col_grupo:
        t = t[x[col_grupo].notna().values]
    med = ["sp", "fp", "sb", "c0", "ng"]
    out = {}
    tot = t.groupby("_clave", as_index=False)[med].sum()
    out["TOTAL"] = {r["_clave"]: [round(float(r[m]), 2) for m in med]
                    for r in tot.to_dict("records")}
    if col_grupo:
        g = t.groupby(["grupo", "_clave"], as_index=False)[med].sum()
        for r in g.to_dict("records"):
            out.setdefault(r["grupo"], {})[r["_clave"]] = [
                round(float(r[m]), 2) for m in med]
    return out


def origenes_de_lineas(lineas):
    """Las líneas de UNA sesión de «Análisis de diferencias», sumadas por
    familia, área, posible origen y lado. Sólo los tres orígenes que salen
    de una pista (`ORIGENES`): el sistema en negativo y lo que queda «sin
    pista» se calculan aparte, por diferencia, y así las barras suman
    siempre lo mismo que el ajuste. Las líneas con el sistema en negativo y
    sobrante no entran: son «sistema en negativo», tenga la pista que
    tenga."""
    cols = ["familia", "area", "origen", "lado", "v"]
    if lineas is None or len(lineas) == 0:
        return pd.DataFrame(columns=cols)
    L = lineas
    v = _num(L["v"])
    neg = (v > 0) & (_num(L["s"]) < 0)
    origen = L["pista_t"].map(ORIGEN_DE_PISTA)
    x = pd.DataFrame({
        "familia": L["familia"].astype(str).str.strip().str.upper().values,
        "area": L["area"].astype(str).str.strip().str.upper().values,
        "origen": origen.values,
        "lado": pd.Series(v.values).gt(0).map({True: "s", False: "f"}).values,
        "v": v.values,
    })
    x = x[(~neg).values & x["origen"].notna().values]
    return x.groupby(["familia", "area", "origen", "lado"], as_index=False)["v"].sum()[cols]


def origenes_por_periodo(por_sesion, dia_a_clave, familias=None, areas=None):
    """`{clave: {"ven": [s, f], "pro": [s, f], "reg": [s, f]}}` en soles.

    `por_sesion` es `[(sesión, origenes_de_lineas(...)), ...]`; cada sesión
    cae en el periodo de su primer día que la serie tenga (`dia_a_clave`,
    de `dp`): así vale igual para «Mes» —con o sin mes operativo— que para
    «Corte». `familias` y `areas` filtran como lo hace la serie (sin
    distinguir mayúsculas)."""
    out = {}
    fams = {str(f).strip().upper() for f in familias} if familias else None
    ars = {str(a).strip().upper() for a in areas} if areas else None
    for ses, agg in por_sesion:
        clave = next((dia_a_clave[d] for d in sorted(ses["dias"]) if d in dia_a_clave), None)
        if clave is None or agg is None or len(agg) == 0:
            continue
        a = agg
        if fams is not None:
            a = a[a["familia"].isin(fams)]
        if ars is not None:
            a = a[a["area"].isin(ars)]
        dst = out.setdefault(clave, {o: [0.0, 0.0] for o in ORIGENES})
        for r in a.to_dict("records"):
            dst[r["origen"]][0 if r["lado"] == "s" else 1] += float(r["v"])
    return {k: {o: [round(x, 2) for x in par] for o, par in v.items()}
            for k, v in out.items()}


# Desde qué mes el ajuste del cierre es el que de verdad movió el stock: antes
# de setiembre 2025 el cierre lo escribía como lo contado ±5-10 % (regla
# #612), y esos meses no entran en la banda de lo habitual.
DESDE_BANDA = "2025-09"


def pct_consumo(neto_por_clave, consumo_por_clave, cerrados):
    """El neto como % del consumo operativo de su mes, y la banda de lo
    habitual: la mitad central de los meses (cuartiles) y, por fuera, las
    cercas de Tukey (1,5 × rango intercuartil; J. W. Tukey, «Exploratory
    Data Analysis», 1977). Para la banda cuentan sólo los meses CERRADOS
    desde `DESDE_BANDA`. Devuelve `{"pct": {clave: % | None}, "q1", "q3",
    "med", "ci", "cs"}`; sin cuatro meses para la banda, sin banda."""
    pct = {}
    for k, n in neto_por_clave.items():
        c = consumo_por_clave.get(k)
        pct[k] = (round(100.0 * n / c, 2)
                  if c and c > 0 and n is not None and not pd.isna(n) else None)
    base = sorted(v for k, v in pct.items()
                  if v is not None and k in cerrados and k >= DESDE_BANDA)
    out = {"pct": pct}
    if len(base) >= 4:
        q1, med, q3 = (float(pd.Series(base).quantile(q)) for q in (0.25, 0.5, 0.75))
        iqr = q3 - q1
        out.update(q1=round(q1, 2), q3=round(q3, 2), med=round(med, 2),
                   ci=round(q1 - 1.5 * iqr, 2), cs=round(q3 + 1.5 * iqr, 2),
                   n=len(base))
    return out


def datos_pieza(s, sf, gran, *, sistema=None, negativo=None, origen=None,
                origen_estado="no", consumo=None, consumo_estado="no",
                consumo_nota=""):
    """Lo que recibe `evolucion_ajuste.js`. Pura (la prueba
    `test_graficos.py`): los periodos con sus tres medidas, las familias en
    el orden de la matriz, el % del sistema, el sistema en negativo y, si
    ya se pidieron, los posibles orígenes y el % del consumo. Un periodo sin
    conteo va con `None`: es un dato («no se contó»), no un cero."""
    def _v(x):
        return None if x is None or pd.isna(x) else round(float(x), 2)

    kx = con_kardex(s)
    dif = difiere_kardex(s) if kx else pd.Series(False, index=s.index)
    periodos = [{
        "k": r["_clave"], "eje": r["eje"], "s": _v(r["sobrante"]),
        "f": _v(r["faltante"]), "n": _v(r["neto"]), "contado": _v(r["contado"]),
        "kx": _v(r["kardex"]) if kx else None, "dkx": bool(dif.loc[i]),
    } for i, r in s.iterrows()]
    claves = [p["k"] for p in periodos]
    familias = []
    if sf is not None and len(sf):
        for g in orden_familias(sf):
            x = sf[sf["grupo"] == g].set_index("_clave")
            familias.append({
                "id": g, "nombre": g.capitalize(),
                "s": [_v(x["sobrante"].get(k)) for k in claves],
                "f": [_v(x["faltante"].get(k)) for k in claves]})
    sis = {}
    for g, por in (sistema or {}).items():
        sis[g] = [por.get(k) for k in claves]
    return {
        "gran": gran, "kardex": kx, "periodos": periodos, "familias": familias,
        "sistema": sis,
        "neg": [round(float((negativo or {}).get(k, 0.0)), 2) for k in claves],
        "origen": ([(origen or {}).get(k) for k in claves]
                   if origen_estado == "listo" else None),
        "origen_estado": origen_estado,
        "consumo": consumo, "consumo_estado": consumo_estado,
        "consumo_nota": consumo_nota,
    }


# ── LA VISTA ─────────────────────────────────────────────────────────────

def kpis_rango_html(s):
    """Los totales del rango —sobrante, faltante y neto— en UNA línea, para
    ir debajo del título (regla #631). Va en la columna del título y no en
    una fila propia: la tarjeta tiene que entrar en la laptop."""
    def _item(nombre, v, color):
        return (f"<span>{nombre} <b style='color:{color};font-weight:600'>"
                f"{_fmt(v, signo=True) or '—'}</b></span>")
    tot = {c: float(s[c].sum()) for c in ("sobrante", "faltante", "neto")}
    return ("<div class='ajevo-kpis' title='Total del rango de fechas y del "
            "área elegidos'>"
            + _item("Sobrante", tot["sobrante"], AJUSTE_POS_TEXTO)
            + _item("Faltante", tot["faltante"], AJUSTE_NEG_TEXTO)
            + _item("Neto", tot["neto"], TEXTO_PRINCIPAL)
            + "</div>")


# UNA PIEZA PROPIA (regla #692), como la lista de «Análisis de diferencias»:
# `evolucion_ajuste.js` + `.css`, un `st.components.v2` sin iframe. Dibuja
# la serie, el panel del período, la matriz familia × mes, «¿Es mucho?» y
# la tabla de resumen. Elegir un mes, prender un origen, abrir una familia
# o cambiar de modo es del navegador: no cuesta una corrida. A Python le
# llega sólo el trigger «pedir» —{que: "origen" | "consumo"}— cuando hace
# falta un dato caro que todavía no se calculó.
_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "evolucion_ajuste",
    css=(_AQUI / "evolucion_ajuste.css").read_text(encoding="utf-8"),
    js=(_AQUI / "evolucion_ajuste.js").read_text(encoding="utf-8"),
)
_K_PIEZA = "ajevo_pieza"
_K_AREA = "ajuste_evo_filtro_area"
# Lo que ya se pidió en esta sesión: los orígenes y el consumo se calculan
# desde el primer pedido y quedan para las corridas siguientes.
_K_QUIERE_ORIGEN = "ajuste_evo_quiere_origen"
_K_QUIERE_CONSUMO = "ajuste_evo_quiere_consumo"
# `(llave, [(sesión, suma)], faltan)`: los orígenes ya calculados para las
# sesiones de la llave (sus claves, el sello del parquet y la versión).
_K_ORIGEN_RES = "ajuste_evo_origen_res"


def _al_pedir():
    a = (st.session_state.get(_K_PIEZA) or {}).get("pedir") or {}
    if a.get("que") == "origen":
        st.session_state[_K_QUIERE_ORIGEN] = True
    elif a.get("que") == "consumo":
        st.session_state[_K_QUIERE_CONSUMO] = True


@st.cache_data(ttl=3600, show_spinner=False)
def _origen_de_sesion(clave, sello, version):
    """Los posibles orígenes de UNA sesión, ya sumados (`origenes_de_lineas`).
    `sello` y `version` son la clave: la de disco de `data` ya guarda la
    cuenta pesada. Si no se pudo calcular, LANZA: no se cachea un vacío."""
    r = data.diferencias_ajuste_sesion(clave)
    if r is None:
        raise RuntimeError(f"sin diferencias para {clave}")
    return origenes_de_lineas(r["lineas"])


@st.cache_data(ttl=3600, show_spinner=False)
def _consumo_mensual(_ajuste, sellos, version):
    """El consumo operativo de cada mes con cierres —inventario inicial +
    compras − inventario final, por cubeta—, la MISMA cuenta del reporte
    Costos (`costo_ventas.armar`, regla #676). `_ajuste` no entra en la
    clave: la dicen los sellos. Si falta un parquet, LANZA."""
    compras = data.cargar("compras.parquet")
    salidas = data.cargar("salidas.parquet")
    ventas = data.venta_por_grupo_dia()
    if compras is None or salidas is None or ventas is None:
        raise RuntimeError("no se pudo leer compras, salidas o ventas")
    cv = costo_ventas.armar(_ajuste, compras, salidas, ventas)
    fl = cv["filas"]
    return {p["k"]: {c: fl["inv_inicial"][c][i] + fl["compras"][c][i]
                     - fl["inv_final"][c][i] for c in costo_ventas.CUBETAS}
            for i, p in enumerate(cv["periodos"])}


def _calcular_origen(ses):
    """Los posibles orígenes de cada sesión, con una barra de avance DEBAJO
    de la pieza (que ya se dibujó con «calculando»): la primera vez de cada
    sesión son ~30 s —la cuenta de «Análisis de diferencias»—, y después
    salen de la caché de disco de `data`. Devuelve `[(sesión, suma)]` y
    cuántas no se pudieron calcular."""
    sello = data.sello_datos("ajusteinventario.parquet")
    version = diferencias_ajuste.VERSION
    por_sesion, faltan = [], 0
    barra = st.progress(0.0, text="Buscando los posibles orígenes…")
    try:
        for i, s_ in enumerate(ses):
            barra.progress(i / max(len(ses), 1),
                           text=f"Buscando los posibles orígenes · {s_['nombre']} "
                                f"({i + 1} de {len(ses)}). La primera vez son ~30 s "
                                "por sesión; después queda guardado.")
            try:
                por_sesion.append((s_, _origen_de_sesion(s_["clave"], sello, version)))
            except Exception:
                faltan += 1
    finally:
        barra.empty()
    return por_sesion, faltan


def vista_evolucion_ajuste(d, col_fecha, col_familia, col_area,
                           col_ajuste_val, col_valorizado, col_kardex=None,
                           d_full=None):
    """UNA tarjeta: la serie y, debajo, quien la explica (regla #504).

    Desde el 2026-10-21 (regla #692) es el boceto aprobado: la serie en rojo
    y verde con «Explicar con» para sumar posibles orígenes de a uno, el
    panel del período al costado, y abajo la matriz familia × mes (en soles
    o como % del sistema, con filas que se despliegan), «¿Es mucho?» (el
    neto como % del consumo, con la banda de lo habitual) y la tabla de
    resumen. Entra en una pantalla de 1323×619.

    `d` llega ENTERO, con la Familia del compartimento de arriba de la pila:
    los meses los elige la propia vista (regla #632), y el Área también.
    `d_full` es el parquet sin filtros, para el consumo (la cuenta de
    Costos lo necesita entero). `col_kardex`, el ajuste del kardex (#612).
    """
    if not col_fecha or col_fecha not in d.columns:
        st.info("Sin columna de fecha: no se puede armar la evolución.")
        return

    st.markdown(f"<style>{css_filtros_vista('ajevo_ctrl_', 'ajevo_corte_')}"
                "</style>", unsafe_allow_html=True)

    # Sin techo de alto (`estilos/_80_cards.py`): si la ventana es más baja
    # que una laptop, lo que sobra lo scrollea la PÁGINA y no la tarjeta.
    with st.container(border=True, key="ajuste_graf_card_izq_evo"):
        # Los controles se dibujan ANTES de calcular nada: en Streamlit el
        # orden de ejecucion es el orden en que se leen los valores.
        c_tit, c_fecha, c_area, c_gran = st.columns(
            # columnas-internas: titulo | meses | area | grano
            [3.7, 1.45, 0.95, 1.1],
            vertical_alignment="center")
        with c_gran:
            # Una sesión vieja puede traer «Semana» guardada (regla #585):
            # un valor que no está en las opciones no se dibuja marcado.
            if st.session_state.get(_K_GRAN) not in (None, *GRANOS):
                del st.session_state[_K_GRAN]
            gran = st.segmented_control(
                "Agrupar por", GRANOS, default="Mes", key=_K_GRAN,
                label_visibility="collapsed",
                help="Agrupa la serie y la matriz por mes o por sesión de "
                     "inventario («Corte»).",
            ) or "Mes"
        ctx_m = ctx_meses("evo", d[col_fecha])
        with c_fecha:
            selector_meses("ajf_evo", ctx_m)
        d = recortar_meses(d, col_fecha, rango_meses(ctx_m))
        d = filtro_area_en_titulo(c_area, d, col_area, col_ajuste_val,
                                  _K_AREA, "ajevo_ctrl_area")
        publicar_contexto_ia("Ajuste de Inventario", d, {
            "Familia": st.session_state.get("ajuste_graf_filtro_familia"),
            "Área": st.session_state.get(_K_AREA)})

        operativo = mes_operativo_activo()
        dp, orden = periodos_ajuste(d, col_fecha, gran, operativo=operativo)
        if orden.empty:
            with c_tit:
                st.markdown("<div style='font-size:14px;font-weight:600'>"
                            "Sobrante, faltante y neto</div>", unsafe_allow_html=True)
            st.info("Sin datos en el rango y el área seleccionados.")
            return

        s = serie_ajuste(dp, orden, col_ajuste_val, col_valorizado,
                         col_kardex=col_kardex)
        with c_tit:
            st.markdown(
                f"<div style='font-size:14px;font-weight:600;color:{TEXTO_PRINCIPAL};"
                "line-height:1.3;white-space:nowrap'>Sobrante, faltante y neto</div>"
                + kpis_rango_html(s), unsafe_allow_html=True)

        hay_fam = bool(col_familia and col_familia in dp.columns)
        sf = (serie_ajuste(dp, orden, col_ajuste_val, col_valorizado,
                           col_grupo=col_familia) if hay_fam else None)
        # Con un área elegida, los orígenes se filtran por las áreas que
        # quedaron en `dp`; sin ninguna, todas.
        areas = (sorted(dp[col_area].dropna().astype(str).str.strip().unique())
                 if st.session_state.get(_K_AREA) and col_area in dp.columns
                 else None)
        familias = (sorted(dp[col_familia].dropna().astype(str).unique())
                    if hay_fam else None)

        # LOS POSIBLES ORÍGENES, sólo si alguien prendió uno. El cálculo de
        # todas las sesiones del rango se guarda en la sesión del usuario:
        # si ya está, se usa; si no, la pieza se dibuja primero con
        # «calculando», la barra de avance va DEBAJO, y al terminar una
        # corrida más la redibuja con los datos. Con la barra arriba, la
        # vista entera desaparecía durante el cálculo (medido: ~30 s por
        # sesión la primera vez, 22 sesiones en 12 meses).
        origen, origen_estado, pendiente = None, "no", None
        if st.session_state.get(_K_QUIERE_ORIGEN):
            fechas = pd.to_datetime(dp[col_fecha], errors="coerce")
            ses = sesiones_inventario(fechas)
            llave = (tuple(s_["clave"] for s_ in ses),
                     data.sello_datos("ajusteinventario.parquet"),
                     diferencias_ajuste.VERSION)
            guardado = st.session_state.get(_K_ORIGEN_RES)
            if guardado and guardado[0] == llave:
                origen = origenes_por_periodo(
                    guardado[1], dict(zip(fechas.dt.date, dp["_clave"])),
                    familias, areas)
                origen_estado = "listo"
                if guardado[2]:
                    st.caption(f"{guardado[2]} sesión(es) sin «Análisis de "
                               "diferencias»: su parte queda «sin pista».")
            else:
                origen_estado, pendiente = "calculando", (ses, llave)

        consumo, consumo_estado, consumo_nota = None, "no", ""
        if gran != "Mes":
            consumo_estado, consumo_nota = "no_aplica", (
                "El consumo es mensual: elegí «Mes» arriba para compararlo.")
        elif areas:
            consumo_estado, consumo_nota = "no_aplica", (
                "El consumo no se lleva por área: con un área elegida no hay "
                "con qué compararlo.")
        elif st.session_state.get(_K_QUIERE_CONSUMO):
            try:
                with st.spinner("Calculando el consumo de cada mes…"):
                    base = d_full if d_full is not None else d
                    cons = _consumo_mensual(
                        base, (data.sello_datos("ajusteinventario.parquet"),
                               *(data.sello_datos(a) for a in (
                                   "compras.parquet", "salidas.parquet",
                                   "ventas.parquet", "notascreditocompras.parquet"))),
                        (costo_ventas.VERSION, definicion_venta.VERSION))
                consumo = consumo_vs_neto(sf, s, cons, familias)
                consumo_estado = "listo"
            except Exception as e:
                consumo_estado, consumo_nota = "error", (
                    f"No se pudo calcular el consumo ({e}).")

        _PIEZA(key=_K_PIEZA, data={
            **datos_pieza(
                s, sf, gran,
                sistema=(sistema_por_periodo(dp, col_fecha, col_ajuste_val,
                                             col_familia if hay_fam else None, gran)
                         if tiene_sistema(dp) else None),
                negativo=negativo_por_periodo(dp, col_ajuste_val),
                origen=origen, origen_estado=origen_estado,
                consumo=consumo, consumo_estado=consumo_estado,
                consumo_nota=consumo_nota),
            "nota_kx": nota_kardex(s, gran).strip(" ·"),
            "ayuda_kx": AYUDA_KARDEX,
            "alto": {"graf": alturas.EVO_GRAFICO, "abajo": alturas.EVO_ABAJO},
            "col": {"pos": AJUSTE_POS, "neg": AJUSTE_NEG,
                    "post": AJUSTE_POS_TEXTO, "negt": AJUSTE_NEG_TEXTO,
                    "alerta": AJUSTE_ALERTA_TEXTO, "ven": AJUSTE_ORIGEN_VEN,
                    "pro": AJUSTE_ORIGEN_PRO, "reg": AJUSTE_ORIGEN_REG,
                    "gneg": AJUSTE_ORIGEN_NEG},
        }, on_pedir_change=_al_pedir, width="stretch")
        if pendiente:
            por_sesion, faltan = _calcular_origen(pendiente[0])
            st.session_state[_K_ORIGEN_RES] = (pendiente[1], por_sesion, faltan)
            st.rerun()


def consumo_vs_neto(sf, s, cons, familias):
    """El neto como % del consumo de cada mes, con la banda (`pct_consumo`).

    El consumo viene por CUBETA de Costos (Alimentos, Bebidas, Vinos,
    Envases); el neto se toma de las familias que caen en las cubetas
    elegidas, y el consumo, de esas mismas cubetas: Costos producción no
    tiene consumo propio y no entra. Un mes sin consumo calculado (el que
    está en curso, uno sin cierre) queda sin %."""
    if sf is not None and len(sf):
        x = sf.assign(_cub=sf["grupo"].map(costo_ventas.FAMILIAS))
        x = x[x["_cub"].notna()]
        cubetas = sorted(x["_cub"].unique())
        neto = x.groupby("_clave", as_index=False)["neto"].sum(min_count=1)
        neto_k = dict(zip(neto["_clave"], neto["neto"]))
    else:
        cubetas = list(costo_ventas.CUBETAS)
        neto_k = dict(zip(s["_clave"], s["neto"]))
    cons_k = {k: sum(v.get(c, 0.0) for c in cubetas) for k, v in cons.items()}
    claves = list(s["_clave"])
    r = pct_consumo({k: neto_k.get(k) for k in claves}, cons_k, set(cons_k))
    r["pct"] = [r["pct"].get(k) for k in claves]
    r["banda_desde"] = DESDE_BANDA
    return r
