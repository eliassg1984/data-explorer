"""
costo_ventas — el COSTO DE VENTAS por mes operativo (reporte «Costos»).

Nació el 2026-10-09 de un boceto aprobado con datos reales
(https://claude.ai/artifact/3NYnyS7axe6u5woDiyiZBD) y de la planilla con
que el usuario ya lo llevaba a mano («Consumo Operativo», «Consumo Carta»).
Regla #622.

LA CUENTA, mes por mes y por familia:

    Consumo operativo = inventario inicial + compras − inventario final
    Consumo carta     = consumo operativo − bajas − costo de cortesías
                        − las otras salidas que se elijan en pantalla

El consumo operativo es todo lo que salió del almacén; el consumo carta, lo
que costó lo vendido, y es el que se compara con el costo que dice el POS
(el del Paloteo de Producción › Comparativo › «(a) Ventas en el rango»).
Las restas que se eligen en pantalla las hace el navegador
(`graficos/costos_tabla.js`): acá se arman las series de cada fila.

DE DÓNDE SALE CADA FILA (las definiciones del usuario):

  · Inventario inicial y final: el del MES OPERATIVO. El cierre de fin de
    mes se registra del 1 al 6 del siguiente (`cortes.fecha_operativa`,
    regla #613), así que el «cierre de setiembre» lleva fecha de octubre.
    Por área, el ÚLTIMO cierre cuya fecha operativa cae en el mes, valorizado
    como se contó (`VALORIZADO TOTAL` = stock declarado × precio promedio).
    El inicial de un mes es el final del anterior.
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

import pandas as pd

from cortes import fecha_operativa

VERSION = 1
"""Subirla cuando cambie QUÉ se calcula."""

DESDE = pd.Period("2025-10", freq="M")
"""El primer mes que se muestra: antes los cierres no sirven (regla #612)."""

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


def _por_mes_y_cubeta(meses, cubetas, valores):
    """Suma `valores` por (mes, cubeta) → DataFrame mes × CUBETAS."""
    b = pd.DataFrame({"mes": meses, "cubeta": cubetas, "v": valores}).dropna(
        subset=["mes", "cubeta"])
    if b.empty:
        return pd.DataFrame(columns=list(CUBETAS), dtype=float)
    return (b.groupby(["mes", "cubeta"])["v"].sum().unstack("cubeta")
            .reindex(columns=list(CUBETAS)).fillna(0.0))


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
    inv = _por_mes_y_cubeta(b["mes"], b["cubeta"], b["v"])
    areas = {}
    con = b[b["cubeta"].notna()]
    for (mes, nombre), g in con.groupby(["mes", "nombre"]):
        valor = float(g["v"].sum())
        if abs(valor) > 0.5:
            areas.setdefault(mes, {})[nombre] = (g["f"].max().date(), valor)
    return inv, areas


def compras_por_mes(compras):
    """Lo comprado por mes y cubeta (neto, notas de crédito ya restadas)."""
    if compras is None or compras.empty:
        return pd.DataFrame(columns=list(CUBETAS), dtype=float)
    c_f = _col(compras, "FECHA_EMISION_DOC", "Fecha documento")
    c_fam = _col(compras, "FAMILIA")
    c_val = _col(compras, "VALOR_COMPRA", "Valor compra")
    if not (c_f and c_fam and c_val):
        return pd.DataFrame(columns=list(CUBETAS), dtype=float)
    return _por_mes_y_cubeta(
        pd.to_datetime(compras[c_f], errors="coerce").dt.to_period("M"),
        compras[c_fam].map(lambda x: FAMILIAS.get(_norm(x))),
        _num(compras[c_val]))


def salidas_por_mes(salidas):
    """`{tipo de descargo: DataFrame mes × CUBETAS}` de las notas de salida
    PROCESADAS, a su valor neto, por fecha de registro (regla #614). Ordenado
    de mayor a menor total, con «Bajas» primero."""
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
    mes = pd.to_datetime(s[c_f], errors="coerce").dt.to_period("M")
    cub = s[c_fam].map(lambda x: FAMILIAS.get(_norm(x)))
    val = _num(s[c_val])
    out = {}
    for t in tipo.unique():
        if _norm(t) in _TIPOS_FUERA:
            continue
        m = tipo == t
        out[t] = _por_mes_y_cubeta(mes[m], cub[m], val[m])
    orden = sorted(out, key=lambda t: (t != BAJAS, -float(out[t].to_numpy().sum())))
    return {t: out[t] for t in orden}


def ventas_por_mes(por_grupo_dia):
    """De `definicion_venta.por_grupo_dia`: `(venta, costo_pos, cortesias,
    venta_aparte, costo_aparte)`. Las tres primeras, mes × CUBETAS; las dos
    últimas, mes × grupo aparte (Eventos, Venta interna)."""
    vacio = pd.DataFrame(columns=list(CUBETAS), dtype=float)
    if por_grupo_dia is None or por_grupo_dia.empty:
        return vacio, vacio, vacio, pd.DataFrame(), pd.DataFrame()
    d = por_grupo_dia
    mes = pd.to_datetime(d["dia"], errors="coerce").dt.to_period("M")
    grupo = d["grupo"].map(_norm)
    cub = grupo.map(GRUPOS_VENTA)
    cort = d["clase"].astype(str).str.upper().str.startswith("CORTES")
    neto, costo = _num(d["neto"]), _num(d["costo"])
    venta = _por_mes_y_cubeta(mes[~cort], cub[~cort], neto[~cort])
    pos = _por_mes_y_cubeta(mes[~cort], cub[~cort], costo[~cort])
    cortesias = _por_mes_y_cubeta(mes[cort], cub[cort], costo[cort])
    ap = grupo.map(GRUPOS_APARTE)
    m = ap.notna() & ~cort
    b = pd.DataFrame({"mes": mes[m], "g": ap[m], "neto": neto[m], "costo": costo[m]})
    if b.empty:
        return venta, pos, cortesias, pd.DataFrame(), pd.DataFrame()
    v_ap = b.groupby(["mes", "g"])["neto"].sum().unstack("g").fillna(0.0)
    c_ap = b.groupby(["mes", "g"])["costo"].sum().unstack("g").fillna(0.0)
    return venta, pos, cortesias, v_ap, c_ap


def meses_del_reporte(inv):
    """Los meses con inventario al cierre del mes Y del anterior, desde
    `DESDE`: sin las dos puntas no hay consumo que calcular."""
    hay = set(inv.index)
    return [m for m in sorted(hay) if m >= DESDE and (m - 1) in hay]


def armar(ajuste, compras, salidas, por_grupo_dia):
    """Todo lo que dibuja la tabla, listo para mandar al navegador.

    Devuelve un dict con `meses` («2025-10», …) y las series por cubeta de
    cada fila (`filas`), una por tipo de salida (`salidas`), lo de Eventos y
    Venta interna (`venta_extra`, `costo_extra`) y las áreas de cada cierre
    (`cierres`). Sin meses (no hay dos cierres seguidos) `meses` va vacío."""
    inv, areas = inventario_por_mes(ajuste)
    meses = meses_del_reporte(inv)
    venta, pos, cortesias, v_ap, c_ap = ventas_por_mes(por_grupo_dia)
    sal = salidas_por_mes(salidas)

    def serie(df, desfase=0):
        idx = [m - desfase for m in meses]
        r = df.reindex(idx).reindex(columns=list(CUBETAS)).fillna(0.0)
        return {c: [round(float(x), 2) for x in r[c]] for c in CUBETAS}

    def plana(df, col):
        if df is None or df.empty or col not in df.columns:
            return [0.0] * len(meses)
        return [round(float(x), 2) for x in df[col].reindex(meses).fillna(0.0)]

    return {
        "version": VERSION,
        "meses": [str(m) for m in meses],
        "filas": {
            "inv_inicial": serie(inv, desfase=1),
            "compras": serie(compras_por_mes(compras)),
            "inv_final": serie(inv),
            "venta": serie(venta),
            "costo_pos": serie(pos),
            "cortesias": serie(cortesias),
        },
        "salidas": {t: serie(df) for t, df in sal.items()},
        "venta_extra": {g: plana(v_ap, g) for g in GRUPOS_APARTE.values()},
        "costo_extra": {g: plana(c_ap, g) for g in GRUPOS_APARTE.values()},
        "cierres": {str(m): {n: [str(f), round(v, 2)] for n, (f, v) in
                             sorted(areas.get(m, {}).items())}
                    for m in meses},
    }


def tabla_larga(datos):
    """Las series de `armar` como filas (mes, familia, concepto, soles), para
    el asistente IA: le alcanza un `SUM` por concepto para contestar."""
    filas = []
    for i, mes in enumerate(datos.get("meses", [])):
        for concepto, por_cub in datos["filas"].items():
            for cub, vals in por_cub.items():
                filas.append((mes, cub, concepto, vals[i]))
        for tipo, por_cub in datos["salidas"].items():
            for cub, vals in por_cub.items():
                filas.append((mes, cub, f"salida: {tipo}", vals[i]))
    return pd.DataFrame(filas, columns=["MES", "FAMILIA", "CONCEPTO", "SOLES"])
