"""
costo_ventas — el COSTO DE VENTAS por período (reporte «Costos»).

Nació el 2026-10-09 de un boceto aprobado con datos reales
(https://claude.ai/artifact/3NYnyS7axe6u5woDiyiZBD) y de la planilla con
que el usuario ya lo llevaba a mano («Consumo Operativo», «Consumo Carta»).
Regla #622.

LA CUENTA, período por período y por familia:

    Consumo operativo = inventario inicial + compras − inventario final
    Consumo carta     = consumo operativo − bajas − costo de cortesías
                        − las demás salidas (entran todas; en pantalla
                          se puede quitar una)

El consumo operativo es todo lo que salió del almacén; el consumo carta, lo
que costó lo vendido, y es el que se compara con el costo que dice el
Sistema Restaurante (el POS: el Paloteo de Producción › Comparativo › «(a)
Ventas en el rango»). Las restas que se eligen en pantalla las hace el
navegador (`graficos/costos_tabla.js`): acá se arman las series de cada fila.

TRES GRANOS, DOS INVENTARIOS:

  · Mes: el inventario es el del MES OPERATIVO. El cierre de fin de mes se
    registra del 1 al 6 del siguiente (`cortes.fecha_operativa`, regla
    #613), así que el «cierre de setiembre» lleva fecha de octubre. Por
    área, el ÚLTIMO cierre cuya fecha operativa cae en el mes, valorizado
    como se contó (`VALORIZADO TOTAL` = stock declarado × precio promedio).
  · Quincena y semana: no hay conteo en esas fechas. El inventario es el
    del KARDEX al final del último día (`inventario_en_momentos`, la regla
    del Histórico del POS de `kardex.sql_stock_al`), sólo de lo activo. No
    es lo contado: el ajuste de cada cierre cae entero en el período del
    cierre, y por eso las semanas de un mes no suman el mes.

  En los tres, el inventario inicial de un período es el final del anterior.

DE DÓNDE SALE EL RESTO (las definiciones del usuario):

  · Compras: `VALOR_COMPRA` (neto, sin IGV) con las notas de crédito ya
    restadas por `data.cargar` (regla #603), por fecha del documento.
  · Salidas: las notas de salida PROCESADAS, a su `VALOR NETO`, por fecha de
    REGISTRO —la «Relación de Notas de Salidas» del Almacén, regla #614—,
    una serie por tipo de descargo. «Bajas» va siempre; las otras se suman
    desde la pantalla.
  · Venta neta, costo según el POS y costo de las cortesías: de
    `definicion_venta.por_grupo_dia` (regla #524), por el día del turno.

LAS FAMILIAS. Inventario, compras y salidas: Alimentos, Bebidas (con y sin
alcohol), Vinos y Espumantes, y Envases y Embalajes; Costos de producción
queda fuera. La venta: Alimentos, Bebidas (con alcohol, sin alcohol y
calientes) y Vinos. Todo se agrupa en cuatro CUBETAS para que la pantalla
filtre de a familia: Alimentos, Bebidas, Vinos y Envases (que no tiene
venta: el POS no costea los envases).

EVENTOS Y VENTA INTERNA gastan inventario y no están en la venta de la
definición. Viajan aparte (`venta_extra`, `costo_extra`) y la pantalla los
suma a Alimentos con un interruptor.

DESDE OCTUBRE 2025. Antes, los cierres y el kardex no cuadran: setiembre
2025 tuvo un ajuste de S/ 627 mil al limpiar el inventario (regla #612), y
el costo de mayo 2025 salía negativo.

Puro pandas, sin streamlit. Lo vigila `test_costo_ventas.py`.
"""

import datetime as dt

import numpy as np
import pandas as pd

from cortes import MESES_ABR_ES, fecha_operativa

VERSION = 3
"""Subirla cuando cambie QUÉ se calcula. 2: semanas y quincenas. 3: los
rótulos de los períodos sin «cierre»/«kardex» (lo dice la cabecera)."""

DESDE = pd.Period("2025-10", freq="M")
"""El primer mes que se muestra: antes los cierres no sirven (regla #612)."""

GRANOS = ("mes", "quincena", "semana")

CUBETAS = ("Alimentos", "Bebidas", "Vinos", "Envases")

FAMILIAS = {
    "ALIMENTOS": "Alimentos",
    "BEBIDAS CON ALCOHOL": "Bebidas",
    "BEBIDAS SIN ALCOHOL": "Bebidas",
    "VINOS Y ESPUMANTES": "Vinos",
    "ENVASES Y EMBALAJES": "Envases",
}
"""Las familias del Almacén que entran (inventario, compras y salidas)."""

GRUPOS_VENTA = {
    "ALIMENTOS": "Alimentos",
    "BEBIDAS C/ ALCOHOL": "Bebidas",
    "BEBIDAS S/ ALCOHOL": "Bebidas",
    "BEBIDAS CALIENTES": "Bebidas",
    "VINOS Y ESPUMANTES": "Vinos",
}
"""Los grupos de carta que son la venta del reporte."""

GRUPOS_APARTE = {"EVENTOS": "Eventos", "VENTA INTERNA": "Venta interna"}
"""Grupos que gastan inventario y no son la venta: viajan aparte."""

BAJAS = "Bajas"
_TIPOS_FUERA = {"", "---", "NAN", "NONE"}


def _norm(s):
    return str(s).strip().upper().replace("_", " ")


def _col(df, *nombres):
    """El nombre real de la primera columna de `nombres` que exista en `df`."""
    mapa = {_norm(c): c for c in df.columns}
    for n in nombres:
        if _norm(n) in mapa:
            return mapa[_norm(n)]
    return None


def _num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def _texto(s):
    return s.astype("string").fillna("").str.strip()


def _por_clave_y_cubeta(claves, cubetas, valores):
    """Suma `valores` por (período, cubeta) → DataFrame período × CUBETAS."""
    b = pd.DataFrame({"k": claves, "cubeta": cubetas, "v": valores}).dropna(
        subset=["k", "cubeta"])
    if b.empty:
        return pd.DataFrame(columns=list(CUBETAS), dtype=float)
    return (b.groupby(["k", "cubeta"])["v"].sum().unstack("cubeta")
            .reindex(columns=list(CUBETAS)).fillna(0.0))


# ── Los períodos ─────────────────────────────────────────────────────────

def clave_mes(fechas):
    """El mes calendario de cada fecha (lo que suman compras, salidas y venta
    en el grano Mes)."""
    return pd.to_datetime(fechas, errors="coerce").dt.to_period("M")


def periodos(grano, desde, hasta):
    """Las quincenas (1–15, 16–fin) o semanas (lunes a domingo) ENTERAS
    entre `desde` y `hasta` (fechas, inclusive): `[(ini, fin), …]`. Una que
    `hasta` corta no entra: su inventario final todavía no existe."""
    out = []
    if grano == "semana":
        ini = desde + dt.timedelta(days=(7 - desde.weekday()) % 7)
        while ini + dt.timedelta(days=6) <= hasta:
            out.append((ini, ini + dt.timedelta(days=6)))
            ini += dt.timedelta(days=7)
    elif grano == "quincena":
        ini = desde if desde.day in (1, 16) else (
            desde.replace(day=16) if desde.day < 16
            else (desde.replace(day=28) + dt.timedelta(days=4)).replace(day=1))
        while True:
            if ini.day == 1:
                fin = ini.replace(day=15)
            else:
                fin = (ini.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
            if fin > hasta:
                break
            out.append((ini, fin))
            ini = fin + dt.timedelta(days=1)
    return out


def clave_de(pers):
    """Una función fecha → inicio de su período (`Timestamp`), o NaT si cae
    fuera de todos. Para sumar compras, salidas y venta por semana o
    quincena."""
    ini = np.array([np.datetime64(a) for a, _ in pers], dtype="datetime64[D]")
    fin = np.array([np.datetime64(b) for _, b in pers], dtype="datetime64[D]")

    def clave(fechas):
        d = pd.to_datetime(fechas, errors="coerce").dt.normalize()
        vals = d.to_numpy(dtype="datetime64[D]")
        i = np.searchsorted(ini, vals, side="right") - 1
        ok = (i >= 0) & ~np.isnat(vals)
        i = np.clip(i, 0, max(len(ini) - 1, 0))
        ok &= (vals <= fin[i]) if len(fin) else False
        res = pd.Series(pd.NaT, index=d.index, dtype="datetime64[ns]")
        if len(ini):
            res[ok] = pd.to_datetime(ini[i[ok]])
        return res
    return clave


def _dia_mes(d):
    return f"{d.day} {MESES_ABR_ES[d.month - 1]}"


def rotulo_periodo(ini, fin):
    """«1–15 set», «16–30 set», «29 set–5 oct»."""
    if ini.month == fin.month:
        return f"{ini.day}–{fin.day} {MESES_ABR_ES[fin.month - 1]}"
    return f"{_dia_mes(ini)}–{_dia_mes(fin)}"


# ── Las fuentes ──────────────────────────────────────────────────────────

def inventario_por_mes(ajuste):
    """El inventario al cierre de cada mes OPERATIVO, por cubeta, y las áreas
    que entraron: `(DataFrame mes × CUBETAS, {mes: {área: (fecha, valor)}})`.

    Por área, el último cierre del mes operativo: un área puede contar a mitad
    de mes y otra vez el día 1, y el que dice cómo terminó el mes es el
    segundo. Se valoriza lo contado (`VALORIZADO TOTAL`)."""
    vacio = pd.DataFrame(columns=list(CUBETAS), dtype=float), {}
    if ajuste is None or ajuste.empty:
        return vacio
    c_f = _col(ajuste, "FECHA APERTURA INVENTARIO")
    c_area = _col(ajuste, "CODIGO AREA")
    c_nom = _col(ajuste, "AREA") or c_area
    c_fam = _col(ajuste, "FAMILIA")
    c_val = _col(ajuste, "VALORIZADO TOTAL")
    if not (c_f and c_area and c_fam and c_val):
        return vacio
    f = pd.to_datetime(ajuste[c_f], errors="coerce")
    b = pd.DataFrame({
        "f": f,
        "mes": fecha_operativa(f).dt.to_period("M"),
        "area": ajuste[c_area].astype(str).str.strip(),
        "nombre": ajuste[c_nom].astype(str).str.strip(),
        "cubeta": ajuste[c_fam].map(lambda x: FAMILIAS.get(_norm(x))),
        "v": _num(ajuste[c_val]),
    }).dropna(subset=["f", "mes"])
    ultimo = b.groupby(["mes", "area"])["f"].transform("max")
    b = b[b["f"] == ultimo]
    inv = _por_clave_y_cubeta(b["mes"], b["cubeta"], b["v"])
    areas = {}
    con = b[b["cubeta"].notna()]
    for (mes, nombre), g in con.groupby(["mes", "nombre"]):
        valor = float(g["v"].sum())
        if abs(valor) > 0.5:
            areas.setdefault(mes, {})[nombre] = (g["f"].max().date(), valor)
    return inv, areas


def base_activa(maestro):
    """De las filas ACTIVAS del maestro (`inventariovalorizado.parquet` ya
    pasado por `separar_activos`, regla #598): área × producto → cubeta.
    Es el ámbito del inventario del kardex."""
    vacio = pd.DataFrame(columns=["area", "cod", "cubeta"])
    if maestro is None or maestro.empty:
        return vacio
    c_area, c_cod = _col(maestro, "CODIGO AREA"), _col(maestro, "CODIGO PRODUCTO")
    c_fam = _col(maestro, "NOMBRE FAMILIA", "FAMILIA")
    if not (c_area and c_cod and c_fam):
        return vacio
    b = pd.DataFrame({
        "area": _texto(maestro[c_area]), "cod": _texto(maestro[c_cod]),
        "cubeta": maestro[c_fam].map(lambda x: FAMILIAS.get(_norm(x))),
    }).dropna(subset=["cubeta"])
    return b.drop_duplicates(["area", "cod"])


def inventario_en_momentos(fotos, base, momentos):
    """El valor del stock por cubeta en cada momento de `momentos`
    (`datetime`, hora entera como `kardex.momento`): DataFrame momento ×
    CUBETAS.

    La regla es la de `kardex.sql_stock_al` —por área y producto, la foto
    del movimiento de mayor correlativo hasta ese momento—, aplicada a todos
    los momentos sobre UNA lectura del kardex (`kardex.sql_fotos`) en vez de
    una consulta por momento. Sólo lo de `base` (`base_activa`)."""
    if fotos is None or fotos.empty or base is None or base.empty or not momentos:
        return pd.DataFrame(0.0, index=list(momentos), columns=list(CUBETAS))
    f = pd.DataFrame({
        "area": _texto(fotos["area"]), "cod": _texto(fotos["cod"]),
        "fecha": pd.to_datetime(fotos["fecha"], errors="coerce"),
        "correlativo": pd.to_numeric(fotos["correlativo"], errors="coerce"),
        "v": _num(fotos["stock"]) * _num(fotos["precio"]),
    }).merge(base, on=["area", "cod"], how="inner").dropna(subset=["fecha"])
    f = f.sort_values(["area", "cod", "correlativo", "fecha"], kind="stable")
    filas = {}
    for m in momentos:
        ultimo = f[f["fecha"] <= pd.Timestamp(m)].drop_duplicates(
            ["area", "cod"], keep="last")
        filas[m] = ultimo.groupby("cubeta")["v"].sum()
    return (pd.DataFrame(filas).T.reindex(index=list(momentos), columns=list(CUBETAS))
            .fillna(0.0))


def compras_por(compras, clave):
    """Lo comprado por período (`clave`: fecha → período) y cubeta."""
    if compras is None or compras.empty:
        return pd.DataFrame(columns=list(CUBETAS), dtype=float)
    c_f = _col(compras, "FECHA_EMISION_DOC", "Fecha documento")
    c_fam = _col(compras, "FAMILIA")
    c_val = _col(compras, "VALOR_COMPRA", "Valor compra")
    if not (c_f and c_fam and c_val):
        return pd.DataFrame(columns=list(CUBETAS), dtype=float)
    return _por_clave_y_cubeta(
        clave(compras[c_f]),
        compras[c_fam].map(lambda x: FAMILIAS.get(_norm(x))),
        _num(compras[c_val]))


def salidas_por(salidas, clave):
    """`{tipo de descargo: DataFrame período × CUBETAS}` de las notas de
    salida PROCESADAS, a su valor neto, por fecha de registro (regla #614).
    Ordenado de mayor a menor total, con «Bajas» primero."""
    if salidas is None or salidas.empty:
        return {}
    c_f = _col(salidas, "FECHA REGISTRO")
    c_est = _col(salidas, "NOMBRE ESTADO SALIDA")
    c_tipo = _col(salidas, "TIPO DESCARGO")
    c_fam = _col(salidas, "NOMBRE FAMILIA", "FAMILIA")
    c_val = _col(salidas, "VALOR NETO")
    if not (c_f and c_tipo and c_fam and c_val):
        return {}
    s = salidas
    if c_est:
        s = s[s[c_est].astype(str).str.strip().str.upper() == "PROCESADO"]
    tipo = s[c_tipo].astype(str).str.strip()
    k = clave(s[c_f])
    cub = s[c_fam].map(lambda x: FAMILIAS.get(_norm(x)))
    val = _num(s[c_val])
    out = {}
    for t in tipo.unique():
        if _norm(t) in _TIPOS_FUERA:
            continue
        m = tipo == t
        out[t] = _por_clave_y_cubeta(k[m], cub[m], val[m])
    orden = sorted(out, key=lambda t: (t != BAJAS, -float(out[t].to_numpy().sum())))
    return {t: out[t] for t in orden}


def ventas_por(por_grupo_dia, clave):
    """De `definicion_venta.por_grupo_dia`: `(venta, costo_pos, cortesias,
    venta_aparte, costo_aparte)`. Las tres primeras, período × CUBETAS; las
    dos últimas, período × grupo aparte (Eventos, Venta interna)."""
    vacio = pd.DataFrame(columns=list(CUBETAS), dtype=float)
    if por_grupo_dia is None or por_grupo_dia.empty:
        return vacio, vacio, vacio, pd.DataFrame(), pd.DataFrame()
    d = por_grupo_dia
    k = clave(d["dia"])
    grupo = d["grupo"].map(_norm)
    cub = grupo.map(GRUPOS_VENTA)
    cort = d["clase"].astype(str).str.upper().str.startswith("CORTES")
    neto, costo = _num(d["neto"]), _num(d["costo"])
    venta = _por_clave_y_cubeta(k[~cort], cub[~cort], neto[~cort])
    pos = _por_clave_y_cubeta(k[~cort], cub[~cort], costo[~cort])
    cortesias = _por_clave_y_cubeta(k[cort], cub[cort], costo[cort])
    ap = grupo.map(GRUPOS_APARTE)
    m = ap.notna() & ~cort
    b = pd.DataFrame({"k": k[m], "g": ap[m], "neto": neto[m], "costo": costo[m]}).dropna(
        subset=["k"])
    if b.empty:
        return venta, pos, cortesias, pd.DataFrame(), pd.DataFrame()
    v_ap = b.groupby(["k", "g"])["neto"].sum().unstack("g").fillna(0.0)
    c_ap = b.groupby(["k", "g"])["costo"].sum().unstack("g").fillna(0.0)
    return venta, pos, cortesias, v_ap, c_ap


# Los nombres por mes, que usan el test y quien quiera una serie suelta.
def compras_por_mes(compras):
    return compras_por(compras, clave_mes)


def salidas_por_mes(salidas):
    return salidas_por(salidas, clave_mes)


def ventas_por_mes(por_grupo_dia):
    return ventas_por(por_grupo_dia, clave_mes)


def meses_del_reporte(inv):
    """Los meses con inventario al cierre del mes Y del anterior, desde
    `DESDE`: sin las dos puntas no hay consumo que calcular."""
    hay = set(inv.index)
    return [m for m in sorted(hay) if m >= DESDE and (m - 1) in hay]


# ── La tabla ─────────────────────────────────────────────────────────────

def _tabla(claves, inv_ini, inv_fin, compras, salidas, por_grupo_dia, clave):
    """Lo común a los tres granos: las series de cada fila en el orden de
    `claves`, con los inventarios ya calculados."""
    venta, pos, cortesias, v_ap, c_ap = ventas_por(por_grupo_dia, clave)

    def serie(df):
        r = df.reindex(claves).reindex(columns=list(CUBETAS)).fillna(0.0)
        return {c: [round(float(x), 2) for x in r[c]] for c in CUBETAS}

    def plana(df, col):
        if df is None or df.empty or col not in df.columns:
            return [0.0] * len(claves)
        return [round(float(x), 2) for x in df[col].reindex(claves).fillna(0.0)]

    return {
        "filas": {
            "inv_inicial": serie(inv_ini),
            "compras": serie(compras_por(compras, clave)),
            "inv_final": serie(inv_fin),
            "venta": serie(venta),
            "costo_pos": serie(pos),
            "cortesias": serie(cortesias),
        },
        "salidas": {t: serie(df) for t, df in salidas_por(salidas, clave).items()},
        "venta_extra": {g: plana(v_ap, g) for g in GRUPOS_APARTE.values()},
        "costo_extra": {g: plana(c_ap, g) for g in GRUPOS_APARTE.values()},
    }


def armar(ajuste, compras, salidas, por_grupo_dia):
    """El grano MES, con el inventario de los cierres. Devuelve `grano`,
    `inventario` («cierre»), `periodos` (`k` «2025-10», `rot` «oct 25»,
    `sub` con la fecha del cierre) y las series de `_tabla`. Sin dos cierres
    seguidos, `periodos` va vacío."""
    inv, areas = inventario_por_mes(ajuste)
    meses = meses_del_reporte(inv)
    prev = inv.copy()
    prev.index = [m + 1 for m in prev.index]
    out = {"grano": "mes", "inventario": "cierre", "periodos": []}
    for m in meses:
        fechas = sorted(f for f, _ in areas.get(m, {}).values())
        sub = ""
        if fechas:
            a, z = fechas[0], fechas[-1]
            # «cierre» lo dice una vez la columna de conceptos.
            sub = _dia_mes(a) if a == z else f"{a.day}–{_dia_mes(z)}"
        out["periodos"].append({"k": str(m), "rot": f"{MESES_ABR_ES[m.month - 1]} {str(m.year)[2:]}",
                                "sub": sub})
    out.update(_tabla(meses, prev, inv, compras, salidas, por_grupo_dia, clave_mes))
    return out


def armar_kardex(grano, fotos, base, compras, salidas, por_grupo_dia, hasta):
    """El grano QUINCENA o SEMANA, con el inventario del kardex al final de
    cada período. `hasta` es el último día con datos completos: un período
    que lo pasa no entra. Misma forma que `armar`, con `inventario`
    «kardex»."""
    out = {"grano": grano, "inventario": "kardex", "periodos": []}
    pers = periodos(grano, DESDE.start_time.date(), hasta)
    vacio = _tabla([], pd.DataFrame(), pd.DataFrame(), None, None, None, clave_mes)
    if not pers:
        out.update(vacio)
        return out
    claves = [pd.Timestamp(a) for a, _ in pers]
    momentos = [dt.datetime.combine(pers[0][0] - dt.timedelta(days=1), dt.time(23))]
    momentos += [dt.datetime.combine(b, dt.time(23)) for _, b in pers]
    inv = inventario_en_momentos(fotos, base, momentos)
    inv_fin = inv.iloc[1:].set_axis(claves)
    inv_ini = inv.iloc[:-1].set_axis(claves)
    for a, b in pers:
        out["periodos"].append({"k": a.isoformat(), "rot": rotulo_periodo(a, b),
                                "sub": f"al {_dia_mes(b)}"})
    out.update(_tabla(claves, inv_ini, inv_fin, compras, salidas, por_grupo_dia,
                      clave_de(pers)))
    return out


def tabla_larga(datos):
    """Las series de `armar` como filas (período, familia, concepto, soles),
    para el asistente IA: le alcanza un `SUM` por concepto para contestar."""
    filas = []
    for i, p in enumerate(datos.get("periodos", [])):
        for concepto, por_cub in datos["filas"].items():
            for cub, vals in por_cub.items():
                filas.append((p["k"], cub, concepto, vals[i]))
        for tipo, por_cub in datos["salidas"].items():
            for cub, vals in por_cub.items():
                filas.append((p["k"], cub, f"salida: {tipo}", vals[i]))
    return pd.DataFrame(filas, columns=["PERIODO", "FAMILIA", "CONCEPTO", "SOLES"])
