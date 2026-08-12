"""
graficos.ventas_comparativo — vista "Año Pasado" del dashboard de Ventas:
barras agrupadas Año Pasado vs Actual con %Var por período, en tres
granularidades (día / semana / mes).

ALINEACIÓN — sólo es una pregunta abierta en granularidad DÍA, y por eso el
toggle aparece nada más ahí:

  · "Mismo día"    miércoles de la semana ISO 32 de 2026 ↔ miércoles de la
                   semana ISO 32 de 2025. El día de semana coincide siempre;
                   la fecha se corre ±3 días. En un restaurante —donde
                   viernes y sábado mandan— esta es la que no miente.
  · "Misma fecha"  05/08/2026 ↔ 05/08/2025. Las fechas coinciden, los días
                   de semana NO.

En SEMANA y MES la pregunta se disuelve sola: una semana ISO completa
siempre trae un lunes, un viernes y un sábado, y un mes también — el ruido
de día-de-semana se cancela al sumar. Semana 32 contra semana 32, agosto
contra agosto, y no hay una segunda lectura razonable.

FERIADOS: en día se pintan como banda (un feriado explica ESE día). En
semana/mes no hay día que sombrear, pero el feriado NO deja de importar:
si un período tiene un feriado que su equivalente no tenía, el %Var lo está
midiendo con la vara torcida. El caso clásico es Semana Santa, que se mueve
entre marzo y abril según el año. Por eso, en vez de descartarlos, se marca
el DESBALANCE (`+1 fer.` / `−1 fer.`) sobre el par afectado.

DE DÓNDE SALEN LOS DATOS: los DOS lados se traen con `data.cargar_rango()`,
no del `d` que está en memoria. `d` viene acotado al rango de la franja
(Ventas usa `carga_por_rango`, ver data.py::REPORTES): con el rango por
defecto —1 del mes a hoy— pedir 12 meses habría mostrado un mes y medio.
El ancla es la última fecha con datos de `d`, así que la vista sigue
mirando donde mira el usuario, pero la ventana la manda el selector. A
ambos lados se les aplican LOS MISMOS chips vía `filtrar_cb`: sin eso se
comparan barras filtradas contra barras sin filtrar (misma clase de bug que
la regla #58 / publicar_contexto_ia).
"""

import calendar as _cal
import datetime as _dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import REPORTES, cargar_rango
from tema import (
    ACENTO, ADVERTENCIA_TEXTO, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO,
    LAVANDA_BORDE, PALETA_SERIES,
)
from graficos.base import _card
from graficos.compras._comun import _first_point

GRANOS = ("Día", "Semana", "Mes")
VENTANAS = {"Día": (7, 14, 30), "Semana": (4, 8, 13), "Mes": (3, 6, 12)}
VENTANA_DEF = {"Día": 14, "Semana": 8, "Mes": 6}
MAX_ETIQUETAS = 14   # con más barras el %Var se pisa: queda sólo en el hover

_DIAS_ES = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
_MESES_ES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")

# Feriados nacionales de Perú de fecha FIJA (mes, día). Los movibles
# (Jueves/Viernes Santo) dependen de Pascua y se calculan en _feriados_peru.
#
# OJO: es el calendario NACIONAL. No sabe de cierres propios del local,
# aniversarios ni feriados regionales — si eso hace falta, esto tiene que
# pasar a ser un dato mantenido por el negocio, no una constante acá.
_FERIADOS_FIJOS_PE = (
    (1, 1),    # Año Nuevo
    (5, 1),    # Día del Trabajo
    (6, 29),   # San Pedro y San Pablo
    (7, 28),   # Fiestas Patrias
    (7, 29),   # Fiestas Patrias
    (8, 6),    # Batalla de Junín
    (8, 30),   # Santa Rosa de Lima
    (10, 8),   # Combate de Angamos
    (11, 1),   # Todos los Santos
    (12, 8),   # Inmaculada Concepción
    (12, 9),   # Batalla de Ayacucho
    (12, 25),  # Navidad
)


# ── Funciones puras (testeadas en test_graficos.py) ─────────────────────────

def _pascua(anio):
    """Domingo de Pascua de `anio` (algoritmo gregoriano anónimo/Meeus).
    Hace falta para Jueves y Viernes Santo, los dos únicos feriados peruanos
    que cambian de fecha cada año — y los que mueven Semana Santa entre
    marzo y abril, distorsionando cualquier comparativo mensual."""
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lo = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lo) // 451
    mes, dia = divmod(h + lo - 7 * m + 114, 31)
    return _dt.date(anio, mes, dia + 1)


def _feriados_peru(anio):
    """set de `date` con los feriados nacionales de Perú de `anio`:
    los fijos de _FERIADOS_FIJOS_PE + Jueves y Viernes Santo."""
    fer = {_dt.date(anio, m, d) for m, d in _FERIADOS_FIJOS_PE}
    p = _pascua(anio)
    fer.add(p - _dt.timedelta(days=3))   # Jueves Santo
    fer.add(p - _dt.timedelta(days=2))   # Viernes Santo
    return fer


def _feriados_entre(ini, fin):
    """Cuántos feriados nacionales caen en [ini, fin] (inclusive)."""
    fer = set()
    for a in range(ini.year, fin.year + 1):
        fer |= _feriados_peru(a)
    return sum(1 for f in fer if ini <= f <= fin)


def _fecha_equivalente(f, modo):
    """Fecha del año pasado equivalente a `f` (un `date`). Sólo aplica a
    granularidad día — semana y mes se alinean por su propia clave.

    modo="calendario": mismo día/mes del año anterior. El 29 de febrero no
        existe en un año no bisiesto → cae al 28.
    modo="semana": misma semana ISO y mismo día de semana del año ISO
        anterior. Si ese año no llega a la semana 53, cae a la 52.
    """
    if modo == "calendario":
        try:
            return f.replace(year=f.year - 1)
        except ValueError:      # 29-feb → año anterior no bisiesto
            return f.replace(year=f.year - 1, day=28)
    iso = f.isocalendar()
    try:
        return _dt.date.fromisocalendar(iso[0] - 1, iso[1], iso[2])
    except ValueError:          # el año ISO anterior no llega a la semana 53
        return _dt.date.fromisocalendar(iso[0] - 1, 52, iso[2])


def _claves_hacia_atras(ancla, grano, n):
    """Las `n` claves de período que TERMINAN en el período de `ancla`, en
    orden cronológico. Clave: un `date` (día), `(año_iso, semana)` (semana)
    o `(año, mes)` (mes)."""
    if grano == "Día":
        return [ancla - _dt.timedelta(days=i) for i in range(n - 1, -1, -1)]
    if grano == "Semana":
        lunes = ancla - _dt.timedelta(days=ancla.weekday())
        out = []
        for i in range(n - 1, -1, -1):
            iso = (lunes - _dt.timedelta(weeks=i)).isocalendar()
            out.append((iso[0], iso[1]))
        return out
    out, y, m = [], ancla.year, ancla.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def _clave_ap(clave, grano, modo):
    """Clave equivalente del año pasado. En semana/mes es el mismo número de
    período un año antes — no hay ambigüedad que resolver, por eso `modo`
    sólo se usa en día."""
    if grano == "Día":
        return _fecha_equivalente(clave, modo)
    y, p = clave
    if grano == "Semana":
        try:
            _dt.date.fromisocalendar(y - 1, p, 1)
        except ValueError:      # el año anterior no tiene semana 53
            return (y - 1, 52)
    return (y - 1, p)


def _rango_de_clave(clave, grano):
    """(primer_día, último_día) del período que identifica `clave`."""
    if grano == "Día":
        return clave, clave
    y, p = clave
    if grano == "Semana":
        return (_dt.date.fromisocalendar(y, p, 1),
                _dt.date.fromisocalendar(y, p, 7))
    return _dt.date(y, p, 1), _dt.date(y, p, _cal.monthrange(y, p)[1])


def _clave_de_fecha(f, grano):
    """Clave del período al que pertenece la fecha `f`."""
    if grano == "Día":
        return f
    if grano == "Semana":
        iso = f.isocalendar()
        return (iso[0], iso[1])
    return (f.year, f.month)


def _etiqueta_clave(clave, grano):
    """Etiqueta del eje X. Describe SIEMPRE el período actual (el del año
    pasado va en el hover), igual que en las otras vistas del dashboard.

    En día lleva el día de semana a propósito: en modo "misma fecha" es
    justo lo que deja ver que estás comparando un miércoles contra un
    martes, en vez de esconderlo."""
    if grano == "Día":
        return f"{_DIAS_ES[clave.weekday()]} {clave:%d/%m}"
    y, p = clave
    if grano == "Semana":
        return f"S{p:02d} {_rango_de_clave(clave, grano)[0]:%d/%m}"
    return f"{_MESES_ES[p - 1]} {y % 100:02d}"


def _fmt_soles_compacto(v):
    """'S/ 636k' arriba de 1000, 'S/ 480' abajo — para la etiqueta ENCIMA de
    la barra (el valor exacto ya está en el hover). Sin esto, "S/ 636,448"
    en 9px sobre una barra angosta se corta o se pisa con la vecina."""
    if v >= 1000:
        return f"S/ {v / 1000:,.0f}k"
    return f"S/ {v:,.0f}"


def _texto_periodo(clave, grano, fin_real=None):
    """Período en texto largo, para el hover (ahí sí importa el año).
    `fin_real` acorta el texto cuando el período está recortado por estar
    en curso — el hover tiene que decir el tramo que REALMENTE se sumó."""
    ini, fin = _rango_de_clave(clave, grano)
    if fin_real is not None:
        fin = fin_real
    if grano == "Día":
        return f"{ini:%d/%m/%Y}"
    if grano == "Semana":
        return f"S{clave[1]:02d} · {ini:%d/%m} al {fin:%d/%m/%Y}"
    return f"{_MESES_ES[clave[1] - 1]} {clave[0]} · {ini:%d/%m} al {fin:%d/%m}"


def _rangos_comparables(claves, claves_ap, grano, ancla):
    """Rangos de fecha a sumar en cada lado, recortando el período EN CURSO.

    El último período casi nunca está terminado: con datos hasta el 09/08,
    "agosto" son 9 días. Compararlo contra un agosto entero del año pasado
    da un −83% que no es una caída, es un artefacto del calendario. Así que
    cuando el período actual se pasa del ancla, se recorta —y se recorta el
    del año pasado a la MISMA cantidad de días—, que es el "mes a la fecha
    vs. mismo tramo del año pasado" de cualquier BI serio.

    Devuelve (rangos_act, rangos_ap, parciales): dos listas de
    `(clave, ini, fin)` y el set de índices con período incompleto.
    """
    rangos_act, rangos_ap, parciales = [], [], set()
    for i, (k, kap) in enumerate(zip(claves, claves_ap)):
        ini_a, fin_a = _rango_de_clave(k, grano)
        ini_p, fin_p = _rango_de_clave(kap, grano)
        if fin_a > ancla:
            parciales.add(i)
            fin_a = ancla
            fin_p = min(fin_p, ini_p + (fin_a - ini_a))
        rangos_act.append((k, ini_a, fin_a))
        rangos_ap.append((kap, ini_p, fin_p))
    return rangos_act, rangos_ap, parciales


# ── Vista ────────────────────────────────────────────────────────────────────

def _cargar_tramo(archivo, col_parquet, ini, fin, filtrar_cb):
    """df de ventas de [ini, fin] con los chips ya aplicados, o None.

    El acotado por fecha se re-aplica en pandas aunque `cargar_rango` ya
    filtre en DuckDB: en modo demo (sin secrets R2) el loader devuelve el df
    entero sin filtrar —la columna de fecha del demo no se llama igual— y
    sin esta guarda se sumarían filas de fuera de la ventana."""
    df = cargar_rango(archivo, col_parquet, ini, fin)
    if df is None or df.empty:
        return None
    if filtrar_cb is not None:
        df = filtrar_cb(df)
    return df if (df is not None and not df.empty) else None


def _series_por_rangos(archivo, col_parquet, col_fecha, col_venta, col_pax,
                       col_pedido, rangos, filtrar_cb):
    """({clave: venta}, {clave: pax}) para cada `(clave, ini, fin)` de
    `rangos`, con UNA sola carga de R2 que los cubre a todos.

    Se suma por RANGO y no por clave de período justamente para que el
    recorte del período en curso (ver `_rangos_comparables`) funcione: la
    clave del año pasado sigue siendo "agosto", pero sólo se suman sus
    primeros 9 días.

    Pax NO se suma línea a línea: `Cant Pax` se repite en cada línea del
    pedido, así que sumarla cuenta la misma mesa una vez por plato. Se toma
    un valor por pedido (`max`) y recién ahí se suma — mismo criterio que
    `ventas_resumen.py`. Sin columna de pedido no hay forma de deduplicar,
    así que pax queda vacío en vez de devolver un número inflado."""
    ini_g = min(r[1] for r in rangos)
    fin_g = max(r[2] for r in rangos)
    df = _cargar_tramo(archivo, col_parquet, ini_g, fin_g, filtrar_cb)
    if df is None or col_fecha not in df.columns or col_venta not in df.columns:
        return {}, {}
    cols = {
        "f": pd.to_datetime(df[col_fecha], errors="coerce").dt.normalize(),
        "venta": pd.to_numeric(df[col_venta], errors="coerce"),
    }
    hay_pax = bool(col_pax and col_pedido
                   and col_pax in df.columns and col_pedido in df.columns)
    if hay_pax:
        cols["pax"] = pd.to_numeric(df[col_pax], errors="coerce")
        cols["ped"] = df[col_pedido].astype(str)
    base = pd.DataFrame(cols).dropna(subset=["f", "venta"])
    if base.empty:
        return {}, {}
    fechas = base["f"].dt.date
    ventas, paxes = {}, {}
    for clave, ini, fin in rangos:
        m = (fechas >= ini) & (fechas <= fin)
        ventas[clave] = float(base.loc[m, "venta"].sum())
        if hay_pax:
            _t = base.loc[m, ["ped", "pax"]].dropna(subset=["pax"])
            paxes[clave] = (float(_t.groupby("ped")["pax"].max().sum())
                            if not _t.empty else 0.0)
    return ventas, paxes


def _pct(actual, previo):
    """%Δ de `actual` contra `previo`, o None si no hay base con la que
    comparar. Devolver None y no 0 es deliberado: un período sin dato del
    año pasado deja un HUECO en la línea, no un punto en cero que se leería
    como "no cambió"."""
    if not previo:
        return None
    return (actual - previo) / previo * 100


def _ranking_platos(archivo, col_parquet, col_fecha, col_venta, col_prod,
                    col_cant, rango_act, rango_ap, filtrar_cb, top=15,
                    col_fam=None, col_sub=None):
    """Ranking de productos de UN período, Actual vs Año Pasado.

    Carga sólo los dos tramos del período clickeado (no la ventana entera),
    así que el drill cuesta dos consultas acotadas. Ordena por venta actual
    y se queda con el top; los productos que existen en un año y no en el
    otro se conservan con 0 del lado que falta — que un plato haya
    desaparecido de la carta es justamente lo que se quiere ver.

    Grupo/Sub Grupo se resuelven por PRODUCTO (el valor más frecuente), no
    se agregan a la clave del groupby: si un plato cambió de grupo entre los
    dos años, agrupar por los tres campos lo partiría en dos filas que no se
    comparan entre sí — justo lo contrario de lo que se busca acá. Se toma
    del período actual y, si el plato ya no existe hoy, del año pasado.

    Devuelve un DataFrame ya listo para mostrar, o None si no hay datos.
    """
    _jer = bool(col_fam) or bool(col_sub)

    def _agg(rango):
        _ini, _fin = rango
        df = _cargar_tramo(archivo, col_parquet, _ini, _fin, filtrar_cb)
        if df is None or col_fecha not in df.columns \
                or col_venta not in df.columns or col_prod not in df.columns:
            return None, None
        _fe = pd.to_datetime(df[col_fecha], errors="coerce").dt.normalize()
        cols = {"f": _fe, "prod": df[col_prod].astype(str),
                "venta": pd.to_numeric(df[col_venta], errors="coerce")}
        if col_cant and col_cant in df.columns:
            cols["cant"] = pd.to_numeric(df[col_cant], errors="coerce").fillna(0)
        if col_fam and col_fam in df.columns:
            cols["fam"] = df[col_fam].astype(str)
        if col_sub and col_sub in df.columns:
            cols["sub"] = df[col_sub].astype(str)
        b = pd.DataFrame(cols).dropna(subset=["f", "venta"])
        b = b[(b["f"].dt.date >= _ini) & (b["f"].dt.date <= _fin)]
        if b.empty:
            return None, None
        agg = {"venta": ("venta", "sum")}
        if "cant" in b.columns:
            agg["cant"] = ("cant", "sum")
        res = b.groupby("prod", as_index=False).agg(**agg)
        # Jerarquía por producto: la moda (valor más frecuente), no el
        # primero — una fila suelta mal cargada no debería decidir el grupo.
        jer = None
        _cj = [c for c in ("fam", "sub") if c in b.columns]
        if _cj:
            jer = (b.groupby("prod")[_cj]
                   .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "")
                   .reset_index())
        return res, jer

    (a, jer_a), (p, jer_p) = _agg(rango_act), _agg(rango_ap)
    if a is None and p is None:
        return None
    if a is None:
        a = pd.DataFrame({"prod": [], "venta": []})
    if p is None:
        p = pd.DataFrame({"prod": [], "venta": []})

    _pcols = ["prod", "venta"] + (["cant"] if "cant" in p.columns else [])
    t = a.merge(p[_pcols].rename(columns={"venta": "venta_ap",
                                          "cant": "cant_ap"}),
                on="prod", how="outer")
    for _c in ("venta", "venta_ap", "cant", "cant_ap"):
        if _c in t.columns:
            t[_c] = t[_c].fillna(0)
    # float con NaN, no una lista con None: en una columna `object` el Styler
    # no aplica el formateador a los None y los pinta como el literal "None".
    t["var"] = pd.to_numeric(
        pd.Series([_pct(x, y) for x, y in zip(t["venta"], t["venta_ap"])],
                  index=t.index, dtype="object"), errors="coerce")

    if _jer:
        jer = jer_a if jer_a is not None else jer_p
        if jer_a is not None and jer_p is not None:
            # Los que ya no existen hoy conservan la jerarquía del año pasado.
            _falta = jer_p[~jer_p["prod"].isin(jer_a["prod"])]
            jer = pd.concat([jer_a, _falta], ignore_index=True)
        if jer is not None:
            t = t.merge(jer, on="prod", how="left")
            for _c in ("fam", "sub"):
                if _c in t.columns:
                    t[_c] = t[_c].fillna("—")

    t = t.sort_values("venta", ascending=False).head(top).reset_index(drop=True)
    return t


@st.fragment
def _ventas_comparativo(d, col_venta, col_fecha, col_pax=None, col_pedido=None,
                        col_prod=None, col_cant=None, col_fam=None,
                        col_sub=None, filtrar_cb=None):
    """Comparativo Año Pasado vs Actual por día, semana o mes — en montos o
    descompuesto en pax × ticket, con drill al ranking de platos del período
    que se clickee."""
    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el comparativo.")
        return

    _fe = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
    if _fe.empty:
        st.info("Sin fechas válidas en el rango cargado.")
        return
    ancla = _fe.max().date()

    c1, c2, c3 = st.columns([1.5, 1.5, 2.2])
    with c1:
        grano = st.pills("Granularidad", list(GRANOS), default="Día",
                         key="ventas_comp_grano",
                         label_visibility="collapsed") or "Día"
    with c2:
        # Key por granularidad: las opciones cambian con el grano y un
        # st.pills que conserva un valor fuera de su lista nuevo se queda
        # sin selección (regla #9 — instance id en la key).
        ventana = st.pills(
            "Ventana", list(VENTANAS[grano]), default=VENTANA_DEF[grano],
            key=f"ventas_comp_ventana_{grano}",
            format_func=lambda v: f"{v} {'días' if grano == 'Día' else ('semanas' if grano == 'Semana' else 'meses')}",
            label_visibility="collapsed",
        ) or VENTANA_DEF[grano]
    modo = "semana"
    if grano == "Día":
        with c3:
            modo_lbl = st.pills(
                "Alinear por", ["Mismo día de semana", "Misma fecha"],
                default="Mismo día de semana", key="ventas_comp_modo",
                label_visibility="collapsed",
            ) or "Mismo día de semana"
        modo = "semana" if modo_lbl.startswith("Mismo día") else "calendario"

    claves = _claves_hacia_atras(ancla, grano, ventana)
    claves_ap = [_clave_ap(k, grano, modo) for k in claves]
    rangos_act, rangos_ap, parciales = _rangos_comparables(
        claves, claves_ap, grano, ancla)

    cfg = REPORTES.get("Ventas", {})
    _arch = cfg.get("archivo", "ventas.parquet")
    _colp = cfg.get("carga_por_rango", "FEC REG DOCUMENTO")
    serie_act, pax_act_d = _series_por_rangos(
        _arch, _colp, col_fecha, col_venta, col_pax, col_pedido,
        rangos_act, filtrar_cb)
    serie_ap, pax_ap_d = _series_por_rangos(
        _arch, _colp, col_fecha, col_venta, col_pax, col_pedido,
        rangos_ap, filtrar_cb)

    y_act = [float(serie_act.get(k, 0.0)) for k in claves]
    y_ap = [float(serie_ap.get(k, 0.0)) for k in claves_ap]
    if not any(y_act) and not any(y_ap):
        st.info("Sin datos de venta en la ventana elegida.")
        return
    hay_ap = any(y_ap)

    # Descomposición: Venta = Pax × Ticket, así que %Δventa, %Δpax y %Δticket
    # viven en el MISMO eje de % y contestan "¿vino menos gente o gastaron
    # menos?" — la pregunta que sigue a cualquier caída. Sólo se ofrece si
    # hay pax deduplicable por pedido (ver _series_por_rangos).
    p_act = [float(pax_act_d.get(k, 0.0)) for k in claves]
    p_ap = [float(pax_ap_d.get(k, 0.0)) for k in claves_ap]
    hay_pax = bool(pax_act_d) and any(p_ap) and any(p_act)
    vista = "Montos"
    if hay_pax and hay_ap:
        vista = st.pills(
            "Vista", ["Montos", "Descomposición"], default="Montos",
            key="ventas_comp_vista", label_visibility="collapsed") or "Montos"

    etiquetas = [_etiqueta_clave(k, grano) for k in claves]
    # Con más de MAX_ETIQUETAS barras, valor + %Var + "en curso" apilados se
    # pisan entre sí (y contra los de la categoría vecina) — mismo umbral
    # que ya usaba el %Var, ahora también gobierna las etiquetas de valor.
    mostrar_etq = len(claves) <= MAX_ETIQUETAS
    _txt_ap = [_fmt_soles_compacto(v) for v in y_ap] if mostrar_etq else None
    _txt_act = [_fmt_soles_compacto(v) for v in y_act] if mostrar_etq else None

    es_desc = vista == "Descomposición"
    d_venta = [_pct(a, b) for a, b in zip(y_act, y_ap)]
    d_pax = [_pct(a, b) for a, b in zip(p_act, p_ap)]
    # Ticket = venta/pax. Si falta cualquiera de los dos lados, el ticket de
    # ese período no existe (None) y la línea corta ahí en vez de inventar.
    t_act = [(v / p if p else None) for v, p in zip(y_act, p_act)]
    t_ap = [(v / p if p else None) for v, p in zip(y_ap, p_ap)]
    d_ticket = [(_pct(a, b) if (a is not None and b) else None)
                for a, b in zip(t_act, t_ap)]

    fig = go.Figure()
    if es_desc:
        _col_barra = [(EXITO if (v is not None and v >= 0) else ERROR)
                      for v in d_venta]
        fig.add_bar(
            x=etiquetas, y=d_venta, name="%Δ venta",
            marker=dict(color=_col_barra), opacity=0.82,
            text=([None if v is None else f"{v:+.0f}%" for v in d_venta]
                  if mostrar_etq else None),
            textposition="outside", cliponaxis=False, textfont=dict(size=9),
            customdata=[_texto_periodo(k, grano, fin) for (k, _i, fin) in rangos_act],
            hovertemplate="%{customdata}<br>Venta: %{y:+.1f}%<extra></extra>",
        )
        fig.add_trace(go.Scatter(
            x=etiquetas, y=d_pax, name="%Δ pax", mode="lines+markers",
            line=dict(color=PALETA_SERIES[1], width=2),
            marker=dict(size=7, line=dict(color="white", width=1.5)),
            customdata=[[a, b] for a, b in zip(p_act, p_ap)],
            hovertemplate=("Pax: %{y:+.1f}% "
                           "(%{customdata[0]:,.0f} vs %{customdata[1]:,.0f})"
                           "<extra></extra>"),
        ))
        fig.add_trace(go.Scatter(
            x=etiquetas, y=d_ticket, name="%Δ ticket", mode="lines+markers",
            line=dict(color=PALETA_SERIES[2], width=2, dash="dash"),
            marker=dict(size=7, symbol="square",
                        line=dict(color="white", width=1.5)),
            customdata=[[(0 if a is None else a), (0 if b is None else b)]
                        for a, b in zip(t_act, t_ap)],
            hovertemplate=("Ticket: %{y:+.1f}% "
                           "(S/ %{customdata[0]:,.0f} vs S/ %{customdata[1]:,.0f})"
                           "<extra></extra>"),
        ))
        fig.add_hline(y=0, line=dict(color=GRIS_TEXTO, width=1))
    else:
        fig.add_bar(
            x=etiquetas, y=y_ap, name="Año pasado",
            marker=dict(color=LAVANDA_BORDE),
            text=_txt_ap, textposition="outside", cliponaxis=False,
            textfont=dict(size=9, color=GRIS_TEXTO),
            customdata=[_texto_periodo(k, grano, fin) for (k, _i, fin) in rangos_ap],
            hovertemplate="Año pasado · %{customdata}<br>S/ %{y:,.0f}<extra></extra>",
        )
        fig.add_bar(
            x=etiquetas, y=y_act, name="Actual",
            marker=dict(color=ACENTO),
            text=_txt_act, textposition="outside", cliponaxis=False,
            textfont=dict(size=9, color=ACENTO),
            customdata=[_texto_periodo(k, grano, fin) for (k, _i, fin) in rangos_act],
            hovertemplate="Actual · %{customdata}<br>S/ %{y:,.0f}<extra></extra>",
        )
    # El período en curso se marca: aunque el año pasado ya viene recortado
    # al mismo tramo (comparación justa), el usuario tiene que saber que esa
    # barra no es un mes/semana entero — si no, la lee como cerrada. Offset
    # en unidades de dato (no yshift en píxeles) para apilar en el mismo
    # sistema que el %Var de abajo, arriba de las etiquetas de valor.
    if es_desc:
        _vals = [v for v in (d_venta + d_pax + d_ticket) if v is not None]
        _tope = (max(abs(v) for v in _vals) if _vals else 1) or 1
    else:
        _tope = max(max(y_act, default=0), max(y_ap, default=0)) or 1
    for i in parciales:
        _base = (max([v for v in (d_venta[i], d_pax[i], d_ticket[i])
                      if v is not None] or [0]) if es_desc
                 else max(y_act[i], y_ap[i]))
        fig.add_annotation(
            x=i, y=_base + _tope * (0.24 if mostrar_etq else 0.04),
            showarrow=False, text="en curso",
            font=dict(size=8, color=GRIS_TEXTO))

    if grano == "Día":
        # Calendario del día: banda por fin de semana / feriado + punteada
        # al inicio de semana. Eje CATEGÓRICO (una categoría por período),
        # así que la banda de la categoría i va de i-0.5 a i+0.5.
        feriados = set()
        for _a in {k.year for k in claves} | {k.year for k in claves_ap}:
            feriados |= _feriados_peru(_a)
        # Un día se marca feriado si lo es ESTE año o si lo era el día contra
        # el que se compara — las dos cosas explican una barra rara, pero
        # barras DISTINTAS (la morada o la lavanda), así que la etiqueta lo
        # dice. Sin esa distinción, un sábado común marcado en ámbar porque
        # su equivalente de 2025 fue feriado se lee como feriado de hoy.
        for i, f in enumerate(claves):
            fer_act, fer_ap = f in feriados, claves_ap[i] in feriados
            es_finde = f.weekday() >= 5
            if not (fer_act or fer_ap or es_finde):
                continue
            fig.add_vrect(
                x0=i - 0.5, x1=i + 0.5, layer="below", line_width=0,
                fillcolor=(ADVERTENCIA_TEXTO if (fer_act or fer_ap) else GRIS_TEXTO),
                opacity=(0.10 if (fer_act or fer_ap) else 0.07),
            )
            if fer_act or fer_ap:
                fig.add_annotation(
                    x=i, y=1.0, yref="paper", yanchor="bottom", showarrow=False,
                    text=("feriado" if fer_act else "feriado AP"),
                    font=dict(size=8, color=ADVERTENCIA_TEXTO))
        for i, f in enumerate(claves):
            if f.weekday() == 0 and i > 0:
                fig.add_shape(
                    type="line", xref="x", yref="paper",
                    x0=i - 0.5, x1=i - 0.5, y0=0, y1=1,
                    line=dict(color=GRIS_BORDE, width=1, dash="dot"),
                    layer="below")
    else:
        # Semana/mes: no hay día que sombrear, pero un feriado que está de un
        # lado y no del otro sí tuerce el %Var (Semana Santa se muda de mes
        # según el año). Se marca el DESBALANCE, no el feriado.
        for i, k in enumerate(claves):
            n_act = _feriados_entre(*_rango_de_clave(k, grano))
            n_ap = _feriados_entre(*_rango_de_clave(claves_ap[i], grano))
            if n_act == n_ap:
                continue
            _dif = n_act - n_ap
            fig.add_annotation(
                x=i, y=1.0, yref="paper", yanchor="bottom", showarrow=False,
                text=f"{'+' if _dif > 0 else '−'}{abs(_dif)} fer.",
                font=dict(size=8, color=ADVERTENCIA_TEXTO))

    # El %Var sólo se anota aparte en Montos: en Descomposición la barra YA
    # es el %Δ de venta y lleva su propia etiqueta (`text=` de la traza).
    if hay_ap and mostrar_etq and not es_desc:
        for i, (a, b) in enumerate(zip(y_act, y_ap)):
            if not b:
                continue
            var = (a - b) / b * 100
            fig.add_annotation(
                x=i, y=max(a, b) + _tope * 0.14, showarrow=False,
                text=f"{var:+.0f}%",
                font=dict(size=9, color=(EXITO if var >= 0 else ERROR)))

    fig.update_layout(
        barmode="group", bargap=0.28, bargroupgap=0.08,
        height=340, margin=dict(l=10, r=10, t=(70 if mostrar_etq else 30), b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=GRIS_TEXTO, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        showlegend=True,  # nativo: da el clic-para-ocultar/mostrar serie
                          # gratis. El panel "Detalle" (abajo) complementa
                          # con el valor absoluto, que el legend no muestra.
        hovermode="x unified",
    )
    fig.update_xaxes(type="category", tickangle=-45, tickfont=dict(size=10),
                     showgrid=False)
    if es_desc:
        fig.update_yaxes(ticksuffix="%", tickformat=",.0f",
                         gridcolor=GRIS_BORDE, zeroline=False)
    else:
        fig.update_yaxes(tickprefix="S/ ", tickformat=",.0f",
                         gridcolor=GRIS_BORDE, zeroline=False)

    _sufijo = {"Día": "día a día", "Semana": "semana a semana",
               "Mes": "mes a mes"}[grano]
    if es_desc:
        titulo = f"¿Por qué cambió la venta? — {_sufijo} vs. año pasado"
    else:
        titulo = f"Comparativo {_sufijo} vs. año pasado"
        if grano == "Día":
            titulo += (" — alineado por día de semana" if modo == "semana"
                       else " — alineado por fecha calendario")

    foco = st.session_state.get("ventas_comp_foco")
    if foco is not None and not (0 <= foco < len(claves)):
        foco = None

    with _card("ventas_comparativo", titulo, titulo_arriba=True):
        # La selección de plotly_chart PERSISTE entre reruns: con una key
        # estática el mismo clic se re-procesa en cada rerun y el drill
        # parpadea abriéndose y cerrándose. El foco va en la key (CLAUDE.md).
        evt = st.plotly_chart(
            fig, use_container_width=True,
            key=f"ventas_g_comparativo_{vista}_{grano}_{foco if foco is not None else 'none'}",
            on_select="rerun", selection_mode="points",
            config={"displaylogo": False, "displayModeBar": False})
        # Panel "Detalle": el legend nativo (showlegend=True arriba) ya da
        # el clic-para-ocultar/mostrar serie; esto complementa con el valor
        # ABSOLUTO de la última barra, que el legend no muestra. Va DESPUÉS
        # del gráfico a propósito: si fuera antes, abrirlo/cerrarlo movería
        # el gráfico en vez de sólo lo que viene debajo.
        if es_desc:
            _etq_ultimo = _etiqueta_clave(claves[-1], grano)
            # type="compact": el default de st.expander estira a todo el
            # ancho del card aunque el label sea corto (la barra vacía que
            # se ve en la franja "Detalle · Ago 26") — "compact" lo rinde
            # como un toggle inline, sin la caja ni el ancho completo.
            with st.expander(f"Detalle · {_etq_ultimo}", expanded=False,
                             type="compact"):
                _filas = [
                    ("Venta", f"S/ {y_act[-1]:,.0f}", d_venta[-1],
                     EXITO if (d_venta[-1] is not None and d_venta[-1] >= 0)
                     else ERROR),
                    ("Pax", f"{p_act[-1]:,.0f}", d_pax[-1], PALETA_SERIES[1]),
                    ("Ticket promedio",
                     (f"S/ {t_act[-1]:,.2f}" if t_act[-1] is not None else "—"),
                     d_ticket[-1], PALETA_SERIES[2]),
                ]
                # Filas en UN solo st.markdown, envueltas en max-width: cada
                # `st.markdown` separado es su propio contenedor de ancho
                # completo, así que el `flex:1` del label empujaba el valor
                # hasta el borde de la tarjeta (~1500px) en vez de quedar
                # junto a él, como el legend de referencia (panel angosto).
                _filas_html = []
                for _label, _val, _pv, _sw in _filas:
                    _pt = "—" if _pv is None else f"{_pv:+.0f}%"
                    _pc = GRIS_TEXTO if _pv is None else (EXITO if _pv >= 0 else ERROR)
                    _filas_html.append(
                        '<div style="display:flex;align-items:center;gap:8px;'
                        'padding:5px 2px;">'
                        f'<span style="width:10px;height:10px;border-radius:2px;'
                        f'background:{_sw};flex-shrink:0;"></span>'
                        f'<span style="font-size:12px;color:#3f3f46;flex:1;">'
                        f'{_label}</span>'
                        f'<span style="font-size:12px;color:{GRIS_TEXTO};">'
                        f'{_val}</span>'
                        f'<span style="font-size:12px;font-weight:600;width:52px;'
                        f'text-align:right;color:{_pc};">{_pt}</span></div>')
                st.markdown(
                    '<div style="max-width:280px;">'
                    + "".join(_filas_html) + '</div>',
                    unsafe_allow_html=True)
        _mp = _first_point(evt)
        if _mp is not None:
            _pi = _mp.get("point_index", _mp.get("point_number"))
            if _pi is not None and st.session_state.get("ventas_comp_click") != _pi:
                st.session_state["ventas_comp_click"] = _pi
                st.session_state["ventas_comp_foco"] = None if foco == _pi else _pi
                st.rerun(scope="fragment")
        if not hay_ap:
            st.caption(
                "No hay ventas registradas en el tramo equivalente del año "
                "pasado — sólo se muestran las barras del período actual.")
        if grano == "Día":
            _expl = ("Cada día se compara contra el MISMO día de semana del "
                     "año pasado (misma semana ISO): la fecha se corre unos "
                     "días, pero un sábado se compara contra un sábado."
                     if modo == "semana" else
                     "Cada día se compara contra la misma fecha del año "
                     "pasado. Ojo: el día de semana no coincide — un "
                     "miércoles puede quedar comparado contra un martes.")
            _cal_txt = (" Banda gris = fin de semana · banda ámbar = feriado "
                        "nacional (Perú); «feriado AP» marca el caso en que "
                        "el feriado cae del lado del año pasado, no de este.")
        else:
            _expl = (
                "Cada semana se compara contra la misma semana ISO del año "
                "pasado. A esta escala el día de semana ya no importa: una "
                "semana completa trae todos los días, así que ese ruido se "
                "cancela solo." if grano == "Semana" else
                "Cada mes se compara contra el mismo mes del año pasado. A "
                "esta escala el día de semana ya no importa: un mes completo "
                "trae todos los días, así que ese ruido se cancela solo.")
            _cal_txt = (" «+1 fer.» / «−1 fer.» marca los períodos que NO "
                        "tienen la misma cantidad de feriados que su "
                        "equivalente — ahí el %Var compara con la vara "
                        "torcida (Semana Santa, por ejemplo, cambia de mes "
                        "según el año).")
        _lbl = ("" if not hay_ap or len(claves) <= MAX_ETIQUETAS else
                f" Con más de {MAX_ETIQUETAS} barras el %Var no se dibuja "
                "sobre ellas (se pisaría); está en el hover.")
        if parciales:
            _lbl += (" El período marcado «en curso» todavía no terminó: se "
                     "compara contra el MISMO tramo del año pasado (no contra "
                     "el período entero), así que el %Var es justo.")
        if es_desc:
            _expl = ("Venta = pax × ticket, así que los tres %Δ comparten un "
                     "mismo eje. Si la venta cae y el ticket queda plano, "
                     "faltó gente; si cae el ticket y el pax no, vinieron "
                     "igual pero gastaron menos. " + _expl)
        _plural = {"Día": "días", "Semana": "semanas", "Mes": "meses"}[grano]
        st.caption(f"Ventana: {ventana} {_plural} hasta {ancla:%d/%m/%Y}. "
                   + _expl + _cal_txt + _lbl
                   + (" Tocá una barra para ver los platos de ese período."
                      if col_prod else ""))

    # ── Drill: ranking de platos del período clickeado ───────────────────
    if foco is not None and col_prod:
        k = claves[foco]
        _r_act = (rangos_act[foco][1], rangos_act[foco][2])
        _r_ap = (rangos_ap[foco][1], rangos_ap[foco][2])
        with _card("ventas_comp_platos",
                   f"Platos · {_texto_periodo(k, grano, rangos_act[foco][2])} "
                   f"vs. {_texto_periodo(claves_ap[foco], grano, rangos_ap[foco][2])}",
                   titulo_arriba=True):
            _c1, _c2 = st.columns([6, 1])
            with _c2:
                if st.button("Cerrar", key="ventas_comp_cerrar",
                             use_container_width=True):
                    st.session_state["ventas_comp_foco"] = None
                    st.session_state["ventas_comp_click"] = None
                    st.rerun(scope="fragment")
            rk = _ranking_platos(_arch, _colp, col_fecha, col_venta, col_prod,
                                 col_cant, _r_act, _r_ap, filtrar_cb,
                                 col_fam=col_fam, col_sub=col_sub)
            if rk is None or rk.empty:
                st.info("Sin ventas de productos en ese período.")
            else:
                # Jerarquía primero (Grupo → Sub Grupo → Producto, como la
                # Matriz agrupada), después la plata con su %Var, y las
                # cantidades al final: son la lectura de apoyo, no la
                # principal — y así los dos pares AP/Actual no se intercalan.
                _cols = {"fam": "Grupo", "sub": "Sub Grupo", "prod": "Producto",
                         "venta_ap": "Venta AP", "venta": "Venta actual",
                         "var": "%Var", "cant_ap": "Cant AP",
                         "cant": "Cant actual"}
                _orden = [c for c in ("fam", "sub", "prod", "venta_ap",
                                      "venta", "var", "cant_ap", "cant")
                          if c in rk.columns]
                tv = rk[_orden].rename(columns=_cols)

                def _sty_var(v):
                    if pd.isna(v):
                        return f"color:{GRIS_TEXTO}"
                    return f"color:{EXITO}" if v >= 0 else f"color:{ERROR}"

                _fmt = {"Venta AP": "S/ {:,.0f}", "Venta actual": "S/ {:,.0f}",
                        "%Var": "{:+.0f}%", "Cant AP": "{:,.0f}",
                        "Cant actual": "{:,.0f}"}
                _fmt = {k: v for k, v in _fmt.items() if k in tv.columns}
                _gris = [c for c in ("Venta AP", "Cant AP") if c in tv.columns]
                # na_rep gobierna los NaN (productos sin equivalente el año
                # pasado): sin él, el Styler pinta el literal "None".
                sty = (tv.style.format(_fmt, na_rep="—")
                       .map(_sty_var, subset=["%Var"])
                       .set_properties(subset=_gris, color=GRIS_TEXTO))
                st.dataframe(sty, use_container_width=True, hide_index=True,
                             height=min(430, 60 + 34 * len(tv)))
                st.caption(
                    "Top 15 por venta actual. Un producto con «—» en %Var no "
                    "se vendió en el período equivalente del año pasado "
                    "(entró a la carta después, o no estaba disponible).")
