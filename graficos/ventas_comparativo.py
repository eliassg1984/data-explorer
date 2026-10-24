"""
graficos.ventas_comparativo — vista "Año Pasado" del dashboard de Ventas:
barras agrupadas Año Pasado vs Actual con %Var por período, en tres
granularidades (día / semana / mes).

ALINEACIÓN — sólo es una pregunta abierta en granularidad DÍA, y por eso el
toggle aparece nada más ahí:

  · "Mismo día"    el día de 364 días antes (52 semanas justas): miércoles
                   05/08/2026 ↔ miércoles 06/08/2025. El día de semana
                   coincide siempre y la fecha se corre UNO o DOS días. En
                   un restaurante —donde viernes y sábado mandan— esta es la
                   que no miente.
  · "Misma fecha"  05/08/2026 ↔ 05/08/2025. Las fechas coinciden, los días
                   de semana NO.

En SEMANA la pregunta se disuelve sola: se compara contra la de 364 días
antes, que trae los mismos siete días de semana. En MES NO (regla #660;
hasta el 2026-10-16 este texto decía que sí): un mes son cuatro semanas y
uno a tres días sueltos, y esos días cambian de un año al otro — un octubre
con cinco sábados contra uno con cuatro. Se compara contra el mismo mes y
la barra dice cuánto de su %Var es calendario («cal.»,
`_efecto_calendario`).

364 DÍAS Y NO «LA MISMA SEMANA ISO» (regla #659): hasta el 2026-10-05 el
par se buscaba por número de semana ISO. Da lo mismo casi siempre, pero
2026 tiene 53 semanas ISO: desde el 28/12/2026 y durante todo 2027 eso
compara contra 371 días antes, con la fecha corrida SEIS días — el Día de
la Madre de 2027 contra un domingo cualquiera de 2026. Y Mix de Ventas ›
Detalle › «Año pasado» y Por hora ya contaban 364: las vistas habrían
dicho cosas distintas del mismo día.

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
from html import escape

import pandas as pd
import streamlit as st

import cortes
import definicion_venta as dv
import presupuesto_ventas
from data import REPORTES, cargar_rango, rango_fechas, sello_datos, venta_por_turno
from tema import (
    ACENTO, ADVERTENCIA, ADVERTENCIA_TEXTO, ERROR, EXITO,
    GRIS_TEXTO, LAVANDA_BORDE, PALETA_SERIES,
)
from graficos.compras._comun import _fmt_variacion
from graficos import alturas
from utils import fmt_k


GRANOS = ("Día", "Semana", "Mes")
VENTANAS = {"Día": (7, 14, 30), "Semana": (4, 8, 13), "Mes": (3, 6, 12)}
VENTANA_DEF = {"Día": 14, "Semana": 8, "Mes": 6}
MAX_ETIQUETAS = 14   # con más barras el %Var se pisa: queda sólo en el hover

# ── EL CALENDARIO SUBIÓ A `cortes.py` ──────────────────────────────────────
# `_DIAS_ES`, `_FERIADOS_FIJOS_PE`, `_pascua`, `_feriados_peru` y
# `_feriados_entre` nacieron acá y se mudaron a `cortes.py` el 2026-09-08,
# cuando el drill Semanal de Compras pidió lo mismo (bandas de fin de semana
# y de feriado sobre su eje de días). Un import de Compras a Ventas para
# conseguirlas habría atado dos reportes entre sí; `cortes.py` ya era el
# módulo de fechas del proyecto y no importa ni streamlit ni graficos.
#
# Se mantienen los ALIAS con el nombre privado —no se reescribieron los ~10
# usos de más abajo— por dos motivos: `test_graficos.py` los llama por ese
# nombre (`_vc._pascua(2026)`), y renombrar algo que ya está importado es
# justo lo que en Cloud deja la app hablando con el paquete viejo hasta el
# reboot (CLAUDE.md, arquitectura.md #357).
GRUPOS_RAROS = ("Venta Interna", "Eventos")
"""Los grupos del POS que venden sin ser servicio de salón: se venden por
tanda y arman los picos del día y de la hora. Los separa este comparativo y
los dos interruptores de «Análisis por hora» (`ventas_horario`), y es la
misma lista que `consumo_recetas.GRUPOS_NO_SERVICIO` (el test lo vigila).
Vivía en `ventas_ficha_hora.py`, que se fue con la vista vieja (#704)."""

_DIAS_ES = tuple(_d.capitalize() for _d in cortes.DIAS_ABR_ES)
_FERIADOS_FIJOS_PE = cortes.FERIADOS_FIJOS_PE
_pascua = cortes.pascua
_feriados_peru = cortes.feriados_peru
_feriados_entre = cortes.feriados_entre

_MESES_ES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")

_UN_ANO_DE_SEMANAS = _dt.timedelta(days=364)
"""El «mismo día de semana del año pasado»: 52 semanas justas (regla #659)."""


def _fecha_equivalente(f, modo):
    """Fecha del año pasado equivalente a `f` (un `date`). Sólo aplica a
    granularidad día — semana y mes se alinean por su propia clave.

    modo="calendario": mismo día/mes del año anterior. El 29 de febrero no
        existe en un año no bisiesto → cae al 28.
    modo="semana": 364 días antes, el mismo día de la semana. Es la cuenta
        de `ventas_mix.rango_ano_pasado` y `ventas_horario._ano_pasado`, y
        `test_graficos.py` vigila que sigan siendo la misma (regla #659).
    """
    if modo == "calendario":
        try:
            return f.replace(year=f.year - 1)
        except ValueError:      # 29-feb → año anterior no bisiesto
            return f.replace(year=f.year - 1, day=28)
    return f - _UN_ANO_DE_SEMANAS


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
    """Clave equivalente del año pasado. `modo` sólo se usa en día.

    Semana: la que empieza 364 días antes — casi siempre el mismo número de
    semana, pero NO en 2027 (2026 tiene 53 semanas ISO): la S18 de 2027 va
    contra la S19 de 2026, que es la de los mismos días del calendario
    (regla #659). Mes: el mismo mes un año antes."""
    if grano == "Día":
        return _fecha_equivalente(clave, modo)
    if grano == "Semana":
        lunes = _rango_de_clave(clave, grano)[0]
        return _clave_de_fecha(lunes - _UN_ANO_DE_SEMANAS, grano)
    y, p = clave
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


def _texto_periodo(clave, grano, fin_real=None, con_numero=True):
    """Período en texto largo, para el hover (ahí sí importa el año).
    `fin_real` acorta el texto cuando el período está recortado por estar
    en curso — el hover tiene que decir el tramo que REALMENTE se sumó.

    `con_numero=False` calla el número de semana: el del año pasado no
    siempre es el de la barra (la S18 de 2027 va contra la S19 de 2026,
    regla #659), y un hover que dice «S19» sobre la barra «S18» se lee
    como un error. Las fechas sí dicen lo que se sumó."""
    ini, fin = _rango_de_clave(clave, grano)
    if fin_real is not None:
        fin = fin_real
    if grano == "Día":
        return f"{ini:%d/%m/%Y}"
    if grano == "Semana":
        _dias = f"{ini:%d/%m} al {fin:%d/%m/%Y}"
        return f"S{clave[1]:02d} · {_dias}" if con_numero else _dias
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


def _comparables(rangos_ap, inicio):
    """Un bool por período: ¿su lado del año pasado cae entero dentro del
    parquet? (regla #660). El histórico de ventas empieza el 1 de enero de
    2025: con 12 meses hasta noviembre de 2025, noviembre y diciembre de
    2024 no son «cero ventas», son «no hay dato». `inicio` None: no se sabe
    dónde empieza y se comparan todos. Pura."""
    if inicio is None:
        return [True] * len(rangos_ap)
    return [ini >= inicio for (_k, ini, _f) in rangos_ap]


def _texto_sin_dato(claves, ok, grano):
    """«nov y dic 2024» / «4 días»: qué períodos quedaron fuera del total.
    Pura."""
    fuera = [k for k, b in zip(claves, ok) if not b]
    if not fuera:
        return ""
    if grano == "Mes":
        _n = [f"{_MESES_ES[m - 1].lower()} {a}" for a, m in fuera]
        return _n[0] if len(_n) == 1 else ", ".join(_n[:-1]) + " y " + _n[-1]
    _u = "día" if grano == "Día" else "semana"
    return f"{len(fuera)} {_u}{'s' if len(fuera) > 1 else ''}"


def _efecto_calendario(r_act, r_ap, dias_ap):
    """Cuánto de la diferencia de un período es sólo CALENDARIO: qué días
    de semana trae de más o de menos contra el del año pasado, cada uno
    valorizado con lo que ese día de semana vendió en promedio el año
    pasado. En % de la venta del año pasado, o None (regla #660).

    Un mes completo NO trae «todos los días» parejos: 31 días son cuatro
    semanas y tres días sueltos, y esos tres cambian de un año al otro. Un
    octubre con cinco sábados contra uno con cuatro gana un sábado sin
    vender más. La semana (364 días antes) siempre da 0: tiene los mismos
    días de semana. `r_*` son `(ini, fin)`; `dias_ap` el {fecha: venta} del
    año pasado. Pura."""
    def _dias(ini, fin):
        return [ini + _dt.timedelta(days=i) for i in range((fin - ini).days + 1)]
    act, ap = _dias(*r_act), _dias(*r_ap)
    if not ap:
        return None
    v_ap = sum(dias_ap.get(f, 0.0) for f in ap)
    if v_ap <= 0:
        return None
    efecto = 0.0
    for w in range(7):
        n_a = sum(1 for f in act if f.weekday() == w)
        dias_w = [f for f in ap if f.weekday() == w]
        if n_a == len(dias_w) or not dias_w:
            continue
        prom = sum(dias_ap.get(f, 0.0) for f in dias_w) / len(dias_w)
        efecto += (n_a - len(dias_w)) * prom
    return efecto / v_ap * 100


def _por_que(tot_act, tot_ap):
    """La diferencia de la ventana partida en tres que SUMAN la diferencia
    (regla #660): `{"d", "clientes", "ticket", "sin_clientes"}` en soles, o
    None si falta algún lado o no hay clientes.

        Venta = clientes × ticket + canales sin clientes (Rappi…)
        Δ clientes = (clientes hoy − clientes AP) × ticket AP
        Δ ticket   = (ticket hoy − ticket AP) × clientes hoy
        Δ sin cli. = lo de los canales sin clientes, hoy − AP

    El orden (primero clientes al ticket de antes, después el ticket a los
    clientes de hoy) es el de cualquier puente precio × cantidad: los dos
    efectos suman exacto la diferencia de la venta con clientes. Pura."""
    if not tot_act or not tot_ap:
        return None
    p_a, p_p = tot_act.get("pax"), tot_ap.get("pax")
    if not p_a or not p_p:
        return None
    c_a, c_p = tot_act.get("cli") or 0.0, tot_ap.get("cli") or 0.0
    t_a, t_p = c_a / p_a, c_p / p_p
    return {
        "d": tot_act["venta"] - tot_ap["venta"],
        "clientes": (p_a - p_p) * t_p,
        "ticket": (t_a - t_p) * p_a,
        "sin_clientes": ((tot_act["venta"] - c_a) - (tot_ap["venta"] - c_p)),
    }


def _a_la_fecha(ancla, tipo):
    """`(ini, fin, ini_ap, fin_ap)` de «Mes a la fecha» o «Año a la fecha»
    (`tipo` "mes" / "año"): del 1 del mes o del año hasta el último día con
    datos, contra los MISMOS días del calendario un año antes — como lo
    cuenta cualquier cierre contable, no por día de semana. Pura."""
    ini = ancla.replace(day=1) if tipo == "mes" else ancla.replace(month=1, day=1)
    return (ini, ancla, _fecha_equivalente(ini, "calendario"),
            _fecha_equivalente(ancla, "calendario"))


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
                       col_pedido, rangos, filtrar_cb, en_total=None,
                       col_neto=None, col_grupo=None):
    """({clave: venta}, {clave: pax}, {clave: venta del ticket}, total) para
    cada `(clave, ini, fin)` de `rangos`, con UNA sola carga de R2 que los
    cubre a todos. La venta del ticket es la de los canales que registran
    clientes (`definicion_venta.con_clientes`, regla #591): sin Rappi.

    `total` es el de la VENTANA entera (regla #659): `{"venta", "pax",
    "cli"}`, con `pax`/`cli` en None si no hay clientes. Se cuenta sobre la
    UNIÓN de los rangos y no sumando las barras: en «Misma fecha» el 28 y el
    29 de febrero de un bisiesto caen los dos en el 28 del año anterior, y
    un pedido cuya cuenta se partió entre dos días es un solo pedido.

    `en_total` (una lista de bools, uno por rango) deja afuera del total los
    períodos que no se pueden comparar: los del año pasado que caen antes
    del primer día del parquet (regla #660). Sin eso el total contaba esos
    meses como si el año pasado hubiera vendido cero.

    El total trae además lo que necesita la línea «Por qué» (regla #660):
    `neto` (con `col_neto`: la venta sin IGV ni recargo), `raro` (con
    `col_grupo`: Eventos y Venta interna), `canales` ({canal: venta}) y
    `dias` ({fecha: venta} de TODOS los rangos, para el efecto calendario).

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
        return {}, {}, {}, None
    cols = {
        "f": pd.to_datetime(df[col_fecha], errors="coerce").dt.normalize(),
        "venta": pd.to_numeric(df[col_venta], errors="coerce"),
    }
    hay_pax = bool(col_pax and col_pedido
                   and col_pax in df.columns and col_pedido in df.columns)
    if hay_pax:
        cols["pax"] = pd.to_numeric(df[col_pax], errors="coerce")
        cols["ped"] = df[col_pedido].astype(str)
        _c_doc = dv.columna(df, dv.LLAVE_DOC)
        if _c_doc:
            cols["doc"] = df[_c_doc].astype(str)
        cols["cli"] = dv.con_clientes(df, dv.columna(df, dv.CANAL), col_pax)
    if col_neto and col_neto in df.columns:
        cols["neto"] = pd.to_numeric(df[col_neto], errors="coerce").fillna(0.0)
    if col_grupo and col_grupo in df.columns:
        cols["raro"] = df[col_grupo].astype(str).isin(GRUPOS_RAROS)
    _c_canal = dv.columna(df, dv.CANAL)
    if _c_canal:
        cols["canal"] = df[_c_canal].astype(str)
    base = pd.DataFrame(cols).dropna(subset=["f", "venta"])
    if base.empty:
        return {}, {}, {}, None
    fechas = base["f"].dt.date

    def _pax(m):
        _t = base.loc[m, [c for c in ("ped", "pax", "doc")
                          if c in base.columns]].dropna(subset=["pax"])
        # Un valor por pedido y la nota de crédito resta (regla #524).
        return (float(dv.pax_por(_t, "ped", "pax",
                                 doc="doc" if "doc" in _t.columns else None))
                if not _t.empty else 0.0)

    ventas, paxes, ventas_cli = {}, {}, {}
    en_ventana = pd.Series(False, index=base.index)
    en_alguno = pd.Series(False, index=base.index)
    for i, (clave, ini, fin) in enumerate(rangos):
        m = (fechas >= ini) & (fechas <= fin)
        en_alguno |= m
        if en_total is None or en_total[i]:
            en_ventana |= m
        ventas[clave] = float(base.loc[m, "venta"].sum())
        if hay_pax:
            ventas_cli[clave] = float(base.loc[m & base["cli"], "venta"].sum())
            paxes[clave] = _pax(m)
    _w = base.loc[en_ventana]
    total = {
        "venta": float(_w["venta"].sum()),
        "pax": _pax(en_ventana) if hay_pax else None,
        "cli": (float(_w.loc[_w["cli"], "venta"].sum()) if hay_pax else None),
        "neto": float(_w["neto"].sum()) if "neto" in _w.columns else None,
        "raro": (float(_w.loc[_w["raro"], "venta"].sum())
                 if "raro" in _w.columns else None),
        "canales": ({str(k): float(v) for k, v in
                     _w.groupby("canal")["venta"].sum().items()}
                    if "canal" in _w.columns else {}),
        "dias": {k.date(): float(v) for k, v in
                 base.loc[en_alguno].groupby("f")["venta"].sum().items()},
        "n": int(sum(1 for i in range(len(rangos))
                     if en_total is None or en_total[i])),
    }
    return ventas, paxes, ventas_cli, total


def _total_memo(archivo, col_parquet, col_fecha, col_venta, ini, fin,
                filtrar_cb, firma, col_pax=None, col_pedido=None,
                col_neto=None, col_grupo=None):
    """El total de UN tramo (`_series_por_rangos`), recordado en la sesión.

    Lo usan «Mes a la fecha» y «Año a la fecha» (regla #660): el año a la
    fecha son hasta 12 meses por lado, y la vista se vuelve a correr con
    cada clic en una barra. `cargar_rango` ya está en caché, pero la caché
    de Streamlit devuelve una COPIA del df en cada llamada. La clave lleva
    el sello del parquet (regla #367), cómo se fecha la venta (#593) y la
    `firma` de los filtros (filas y venta del `d` de la vista). La tarjeta
    del drill lo usa también para el total de su período, con clientes."""
    clave = (archivo, sello_datos(archivo), venta_por_turno(), col_parquet,
             col_venta, ini, fin, firma, col_pax, col_pedido, col_neto,
             col_grupo)
    memo = st.session_state.setdefault("_ventas_comp_memo", {})
    if clave not in memo:
        if len(memo) >= 16:
            memo.clear()
        memo[clave] = _series_por_rangos(
            archivo, col_parquet, col_fecha, col_venta, col_pax, col_pedido,
            [(None, ini, fin)], filtrar_cb, col_neto=col_neto,
            col_grupo=col_grupo)[3]
    return memo[clave]


def _pct(actual, previo):
    """%Δ de `actual` contra `previo`, o None si no hay base con la que
    comparar. Devolver None y no 0 es deliberado: un período sin dato del
    año pasado deja un HUECO en la línea, no un punto en cero que se leería
    como "no cambió"."""
    if not previo:
        return None
    return (actual - previo) / previo * 100


def _var_txt(pct):
    """`(texto, color)` de una variación de VENTA: «+12%», «−4.7%», «0%».

    El formato de `compras._comun._fmt_variacion` (un decimal debajo del
    10 %, el menos tipográfico, «0%» gris cuando redondea a cero) con el
    color de Ventas, como `ventas_resumen._fmt_var_venta`: acá subir es la
    buena noticia. Hasta el 2026-10-05 la vista escribía `f"{v:+.0f}%"`:
    «+0%» en verde y «-0%» en rojo para un cambio que no hubo."""
    txt, _ = _fmt_variacion(pct)
    if txt == "0%":
        return txt, GRIS_TEXTO
    return txt, (EXITO if pct > 0 else ERROR)


def _var_tabla(actual, previo):
    """%Δ para la tabla del drill, que no puede llevar vacíos: un NaN se ve
    «None» en `st.dataframe` aunque el Styler diga otra cosa (regla #529).
    Sin venta el año pasado: +∞ si hoy vende («nuevo»), −∞ si hoy da
    negativo (sólo notas de crédito) y 0 si ninguno de los dos vendió.

    Con el año pasado NEGATIVO (ese día sólo hubo una nota de crédito del
    producto) se divide por su valor absoluto: dividir por la base negativa
    daba el signo al revés y la celda contradecía al Δ S/ de al lado."""
    if previo:
        return (actual - previo) / abs(previo) * 100
    if actual > 0:
        return float("inf")
    return float("-inf") if actual < 0 else 0.0


def _efectos_producto(v, vp, q, qp):
    """`(por cantidad, por precio, qué cambió)` de UN producto (regla #660).

    El puente precio × cantidad de siempre: lo que vendió de más o de menos
    al precio del año pasado, y lo que el precio promedio de más o de menos
    puso sobre lo vendido hoy. Los dos suman la diferencia. Un producto
    nuevo o que ya no se vende es todo cantidad; sin cantidades que sirvan
    (notas de crédito, cantidad en cero), también. Pura."""
    d = v - vp
    if vp <= 0 < v:
        return d, 0.0, "nuevo"
    if v <= 0 < vp:
        return d, 0.0, "ya no se vende"
    if q > 0 and qp > 0:
        p_a, p_p = v / q, vp / qp
        ef_c, ef_p = (q - qp) * p_p, (p_a - p_p) * q
    else:
        ef_c, ef_p = d, 0.0
    if abs(d) < 1:
        return ef_c, ef_p, "igual"
    if abs(ef_p) > abs(ef_c):
        return ef_c, ef_p, "más caro" if ef_p > 0 else "más barato"
    return ef_c, ef_p, "vende más" if ef_c > 0 else "vende menos"


def _explica_diferencia(t, top=15):
    """Qué productos explican la diferencia de UN período contra el año
    pasado: los `top` que más pesaron, de mayor a menor |Δ S/|, y los demás
    juntos en una fila «Resto» (regla #659).

    `t` trae una fila por producto con `venta` y `venta_ap` (0 del lado en
    que no se vendió) y, si hay, `cant`, `cant_ap`, `fam` y `sub`.

    Hasta el 2026-10-05 el drill ordenaba por venta ACTUAL: era la lista de
    lo más vendido, no la de lo que cambió, y un plato que el año pasado se
    vendía y hoy no —venta actual 0— quedaba siempre último y fuera del
    top, aunque el docstring decía que verlo era el punto. Mismo criterio
    que el puente de Mix › Detalle (`ventas_mix._zona_detalle`).

    Devuelve `(tabla, resumen)`: la tabla con la columna `d` (Δ S/), `var`
    (`_var_tabla`) y `resto` (True en la última fila si hubo resto), y
    `{"d_total", "d_top", "n_resto"}` para el pie."""
    t = t.copy()
    # Un lado vacío llega como columna `object` después del merge.
    for c in ("venta", "venta_ap", "cant", "cant_ap"):
        if c in t.columns:
            t[c] = pd.to_numeric(t[c], errors="coerce").fillna(0.0)
    t["d"] = t["venta"] - t["venta_ap"]
    # Desempate determinista: entre dos con el mismo |Δ|, primero el que más
    # vende hoy y después por nombre (`kind="stable"` lo conserva).
    t = t.sort_values(["venta", "prod"], ascending=[False, True])
    t = t.loc[t["d"].abs().sort_values(ascending=False, kind="stable").index]
    # Se junta sólo si sobran DOS o más: una fila «Resto · 1» ocupa el
    # mismo renglón que el producto con su nombre (criterio de
    # `ventas_mix.tramos`).
    _n = top + 1 if len(t) == top + 1 else top
    filas, resto = t.head(_n).copy(), t.iloc[_n:]
    filas["resto"] = False
    resumen = {"d_total": float(t["d"].sum()), "d_top": float(filas["d"].sum()),
               "n_resto": len(resto)}
    if len(resto):
        fila = {c: float(resto[c].sum()) for c in
                ("venta", "venta_ap", "cant", "cant_ap", "d") if c in t.columns}
        fila.update({"prod": f"Resto · {len(resto)} productos", "resto": True})
        for c in ("fam", "sub"):
            if c in t.columns:
                fila[c] = ""
        filas = pd.concat([filas, pd.DataFrame([fila])], ignore_index=True)
    filas["var"] = [_var_tabla(a, b)
                    for a, b in zip(filas["venta"], filas["venta_ap"])]
    if "cant" in t.columns and "cant_ap" in t.columns:
        # Por cantidad / por precio de cada producto (regla #660); el Resto
        # suma los de sus productos, que también suman su diferencia.
        _ef = [_efectos_producto(a, b, c, e) for a, b, c, e in zip(
            t["venta"], t["venta_ap"], t["cant"], t["cant_ap"])]
        t = t.assign(ef_cant=[x[0] for x in _ef], ef_precio=[x[1] for x in _ef],
                     que=[x[2] for x in _ef])
        _top = t.head(_n)
        _ec, _ep = list(_top["ef_cant"]), list(_top["ef_precio"])
        _qu = list(_top["que"])
        if len(resto):
            _r = t.iloc[_n:]
            _ec.append(float(_r["ef_cant"].sum()))
            _ep.append(float(_r["ef_precio"].sum()))
            _qu.append("")
        filas["ef_cant"], filas["ef_precio"], filas["que"] = _ec, _ep, _qu
        filas["precio"] = [(a / c if c > 0 and a > 0 else 0.0) for a, c
                           in zip(filas["venta"], filas["cant"])]
        filas["precio_ap"] = [(a / c if c > 0 and a > 0 else 0.0) for a, c
                              in zip(filas["venta_ap"], filas["cant_ap"])]
        filas.loc[filas["resto"], ["precio", "precio_ap"]] = 0.0
        resumen["ef_cant"] = float(t["ef_cant"].sum())
        resumen["ef_precio"] = float(t["ef_precio"].sum())
    if "fam" in t.columns:
        resumen["grupos"] = (t.groupby("fam", as_index=False)[["venta", "venta_ap"]]
                             .sum().assign(d=lambda g: g["venta"] - g["venta_ap"]))
    return filas.reset_index(drop=True), resumen


def _ranking_platos(archivo, col_parquet, col_fecha, col_venta, col_prod,
                    col_cant, rango_act, rango_ap, filtrar_cb, top=15,
                    col_fam=None, col_sub=None):
    """Qué productos explican la diferencia de UN período, Actual vs Año
    Pasado (la cuenta y el orden son de `_explica_diferencia`).

    Carga sólo los dos tramos del período clickeado (no la ventana entera),
    así que el drill cuesta dos consultas acotadas. Los productos que existen
    en un año y no en el otro se conservan con 0 del lado que falta — que un
    plato haya desaparecido de la carta es justamente lo que se quiere ver.

    Grupo/Sub Grupo se resuelven por PRODUCTO (el valor más frecuente), no
    se agregan a la clave del groupby: si un plato cambió de grupo entre los
    dos años, agrupar por los tres campos lo partiría en dos filas que no se
    comparan entre sí — justo lo contrario de lo que se busca acá. Se toma
    del período actual y, si el plato ya no existe hoy, del año pasado.

    Devuelve `(tabla, resumen)` de `_explica_diferencia`, o None si no hay
    datos.
    """
    _jer = bool(col_fam) or bool(col_sub)
    canales = {}

    def _agg(rango, lado):
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
        _c_canal = dv.columna(df, dv.CANAL)
        if _c_canal:
            cols["canal"] = df[_c_canal].astype(str)
        b = pd.DataFrame(cols).dropna(subset=["f", "venta"])
        b = b[(b["f"].dt.date >= _ini) & (b["f"].dt.date <= _fin)]
        if b.empty:
            return None, None
        if "canal" in b.columns:
            canales[lado] = b.groupby("canal")["venta"].sum()
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

    (a, jer_a), (p, jer_p) = _agg(rango_act, "act"), _agg(rango_ap, "ap")
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

    tabla, resumen = _explica_diferencia(t, top=top)
    if canales:
        _c = pd.DataFrame({"venta": canales.get("act", pd.Series(dtype=float)),
                           "venta_ap": canales.get("ap", pd.Series(dtype=float))})
        _c = _c.fillna(0.0).rename_axis("canal").reset_index()
        resumen["canales"] = _c.assign(d=_c["venta"] - _c["venta_ap"])
    return tabla, resumen


def _titulo_comparativo(grano, modo, es_desc, neto=False):
    """Título de la cabecera. Función y no inline porque se pinta DOS veces:
    una provisional apenas se conocen los controles (para que la cabecera no
    aparezca vacía mientras se cargan los datos) y otra al final con el valor
    real de `vista`. Ver arquitectura.md regla #108."""
    _sufijo = {"Día": "día a día", "Semana": "semana a semana",
               "Mes": "mes a mes"}[grano]
    _neto = " · neto, sin IGV" if neto else ""
    if es_desc:
        return f"¿Por qué cambió la venta? — {_sufijo} vs. año pasado{_neto}"
    titulo = f"Comparativo {_sufijo} vs. año pasado"
    if grano == "Día":
        titulo += (" — alineado por día de semana" if modo == "semana"
                   else " — alineado por fecha calendario")
    return titulo + _neto



def _signo_k(v):
    """«+S/ 8.1k» / «−S/ 640» / «S/ 0»: un monto con su signo, compacto."""
    _r = round(v)
    _s = "+" if _r > 0 else ("−" if _r < 0 else "")
    return f"{_s}{fmt_k(abs(v))}" if abs(v) >= 1000 else f"{_s}S/ {abs(v):,.0f}"


def _kpi(rot, val, sub="", color_val=None, color_sub=None, muestra=None,
         tip="", clase=""):
    """Un KPI con el dibujo de los de Ventas (`.vt-kpi`)."""
    _st = f' style="--vt-kpi-color:{muestra}"' if muestra else ""
    _cv = f' style="color:{color_val}"' if color_val else ""
    _cs = f' style="color:{color_sub}"' if color_sub else ""
    _sub = (f'<span class="vt-kpi-sub"{_cs}>{escape(sub)}</span>'
            if sub else "")
    _cl = f"vt-kpi {clase}".strip()
    return (f'<div class="{_cl}"{_st} title="{escape(tip or rot)}">'
            f'<span class="vt-kpi-rot">{escape(rot)}</span>'
            f'<span class="vt-kpi-val"{_cv}>{escape(val)}{_sub}</span>'
            '</div>')


def _kpis_totales(tot_act, tot_ap, es_desc, tramo_act, tramo_ap, neto=False,
                  sin_dato="", n_ok=None, n_tot=None):
    """Los KPI de un total (la ventana o un período): Año pasado, Actual,
    Diferencia, Clientes y Ticket. Es la mitad de `_html_totales`, y la
    tarjeta del drill la usa sola para su período. Pura."""
    act = tot_act or {}
    ap = tot_ap or {}
    v_act, v_ap = act.get("venta") or 0.0, ap.get("venta") or 0.0
    _que = "Neto" if neto else "Venta"
    _parcial = bool(sin_dato) and n_ok is not None
    partes = []
    if v_ap:
        partes.append(_kpi(
            "Año pasado", fmt_k(v_ap),
            f"{n_ok} de {n_tot}" if _parcial else "",
            muestra=None if es_desc else LAVANDA_BORDE,
            color_sub=ADVERTENCIA_TEXTO if _parcial else None,
            tip=(f"{_que} del año pasado: S/ {v_ap:,.2f} · {tramo_ap}"
                 + (f". Sin datos del año pasado para {sin_dato}: el total "
                    f"cuenta sólo los {n_ok} períodos que tienen los dos "
                    "lados, también del lado actual." if _parcial else ""))))
    partes.append(_kpi("Actual", fmt_k(v_act),
                       muestra=None if es_desc else ACENTO,
                       tip=f"{_que} actual: S/ {v_act:,.2f} · {tramo_act}"))
    if v_ap:
        _d = v_act - v_ap
        _txt, _col = _var_txt(_d / v_ap * 100)
        partes.append(_kpi(
            "Diferencia", _txt, _signo_k(_d), color_val=_col,
            tip=(f"Actual contra el año pasado, los mismos días: "
                 f"{_signo_k(_d)} ({_txt}) · S/ {_d:+,.2f}")))
    p_act, p_ap = act.get("pax"), ap.get("pax")
    if p_act:
        _sub, _col = (_var_txt((p_act / p_ap - 1) * 100) if p_ap
                      else ("", None))
        partes.append(_kpi(
            "Clientes", f"{p_act:,.0f}", _sub, color_sub=_col,
            muestra=PALETA_SERIES[1] if es_desc else None,
            tip=(f"Clientes (adultos): {p_act:,.0f}"
                 + (f" contra {p_ap:,.0f} el año pasado" if p_ap else ""))))
        t_act = (act.get("cli") or 0.0) / p_act
        t_ap = (ap.get("cli") or 0.0) / p_ap if p_ap else None
        _sub, _col = (_var_txt((t_act / t_ap - 1) * 100) if t_ap
                      else ("", None))
        partes.append(_kpi(
            "Ticket neto" if neto else "Ticket", f"S/ {t_act:,.2f}", _sub,
            color_sub=_col, muestra=PALETA_SERIES[2] if es_desc else None,
            tip=(f"Ticket: {_que.lower()} de los canales que registran "
                 f"clientes ÷ clientes (sin Rappi). S/ {t_act:,.2f}"
                 + (f" contra S/ {t_ap:,.2f} el año pasado" if t_ap else ""))))
    return partes


def _lectura(tot_act, tot_ap, neto=False, calendario=None):
    """La línea «Por qué» debajo de los KPI (regla #660): lo que explica la
    diferencia y lo que la tuerce, cada cosa sólo si aplica. Lista de
    `(texto, tooltip)`. Pura.

    - **Clientes / ticket / canales sin clientes**: `_por_que`, en soles,
      y suman la diferencia.
    - **Sin IGV**: la venta lleva IGV y recargo, y el IGV cambió dos veces
      (18 % → 10 % el 10/06/2025, → 10,5 % el 10/02/2026): con el mismo
      precio de carta la venta bruta cambia sin que se venda más. Se dice
      si la diferencia neta se aparta medio punto o más de la bruta.
    - **Calendario**: `calendario` es el efecto en % de los días de semana
      de más o de menos (`_efecto_calendario`), si llega a medio punto.
    - **Sin Eventos ni Venta interna**: lo que no es la venta de la carta y
      salta de un año al otro (un evento de S/ 58.500 en un día).
    - **Canales de un solo lado**: un canal que vendió en un período y en el
      otro no (Pedidos Ya existió sólo en 2025)."""
    if not tot_act or not tot_ap or not tot_ap.get("venta"):
        return []
    v_a, v_p = tot_act["venta"], tot_ap["venta"]
    items = []
    pq = _por_que(tot_act, tot_ap)
    if pq:
        _pz = [f"clientes {_signo_k(pq['clientes'])}",
               f"ticket {_signo_k(pq['ticket'])}"]
        if abs(pq["sin_clientes"]) >= 1:
            _pz.append(f"canales sin clientes {_signo_k(pq['sin_clientes'])}")
        items.append((
            f"Por qué {_signo_k(pq['d'])}: " + " · ".join(_pz),
            "La diferencia partida en tres que la suman: cuánto pusieron los "
            "clientes de más o de menos (al ticket del año pasado), cuánto "
            "el ticket más alto o más bajo (con los clientes de hoy) y cuánto "
            "los canales que no registran clientes, como Rappi."))
    if not neto and tot_act.get("neto") and tot_ap.get("neto"):
        _pv = (v_a / v_p - 1) * 100
        _pn = (tot_act["neto"] / tot_ap["neto"] - 1) * 100
        # Medio punto de la RELACIÓN, no de los %: con +219 % y +218 % el
        # IGV no explica nada y la marca sería ruido.
        if abs((100 + _pn) / (100 + _pv) - 1) >= 0.005:
            items.append((
                f"Sin IGV: {_var_txt(_pn)[0]}",
                f"Sin IGV ni recargo (neto) la diferencia es {_var_txt(_pn)[0]}"
                f" y no {_var_txt(_pv)[0]}: el IGV no fue el mismo en los dos "
                "lados (bajó del 18 % al 10 % el 10/06/2025 y subió al 10,5 % "
                "el 10/02/2026), y con el mismo precio de carta eso mueve la "
                "venta bruta sin que se venda más. «Neto», arriba a la "
                "derecha, compara todo así."))
    if calendario is not None and abs(calendario) >= 0.5:
        items.append((
            f"Calendario: {_var_txt(calendario)[0]}",
            f"De la diferencia, {_var_txt(calendario)[0]} es sólo calendario: "
            "los días de semana que este lado trae de más o de menos (un mes "
            "con cinco sábados contra uno con cuatro), cada uno valorizado con "
            "lo que ese día de semana vendió el año pasado."))
    r_a, r_p = tot_act.get("raro"), tot_ap.get("raro")
    if r_a is not None and r_p is not None and (abs(r_a) >= 1 or abs(r_p) >= 1) \
            and v_p - r_p > 0:
        _ps = ((v_a - r_a) / (v_p - r_p) - 1) * 100
        items.append((
            f"Sin Eventos ni Venta interna: {_var_txt(_ps)[0]}",
            f"Eventos y Venta interna: S/ {r_a:,.0f} hoy contra S/ {r_p:,.0f} "
            "el año pasado. No son la venta de la carta y saltan de un año al "
            f"otro; sin ellos la diferencia es {_var_txt(_ps)[0]}."))
    c_a, c_p = tot_act.get("canales") or {}, tot_ap.get("canales") or {}
    for canal in sorted(set(c_a) | set(c_p)):
        _a, _p = c_a.get(canal, 0.0), c_p.get(canal, 0.0)
        if (_a >= 1) == (_p >= 1):
            continue
        _lado = "sólo hoy" if _a >= 1 else "sólo el año pasado"
        items.append((
            f"{canal.title()}: {_lado} ({_signo_k(_a - _p)})",
            f"El canal {canal.title()} vendió S/ {max(_a, _p):,.0f} "
            f"{'hoy y nada el año pasado' if _a >= 1 else 'el año pasado y nada hoy'}"
            ": esa parte de la diferencia no es la misma venta haciéndose más "
            "grande o más chica."))
    return items


def _html_totales(tot_act, tot_ap, es_desc, tramo_act, tramo_ap, neto=False,
                  sin_dato="", n_ok=None, n_tot=None, a_la_fecha=(),
                  lectura=()):
    """La fila del TOTAL DE LA VENTANA (regla #659), con el dibujo de los KPI
    de Ventas (`.vt-kpis`, `estilos/_80_cards.py`), y debajo la línea «Por
    qué» (regla #660).

    Hasta el 2026-10-05 la vista no decía en ningún lado la cifra que se
    viene a buscar —¿cuánto más o menos que el año pasado en estos 14
    días?—: había que sumar las barras a ojo. Las cuentas son las de
    `_series_por_rangos`: los mismos días recortados de los dos lados, y el
    ticket es la venta de los canales con clientes ÷ clientes (regla #591).

    ES LA LEYENDA de lo que se dibuja: en Montos, «Año pasado» y «Actual»
    llevan el color de su barra y la figura va sin legend; en
    Descomposición lo llevan «Clientes» y «Ticket», las dos líneas. Se
    pierde el clic en el legend de Plotly para ocultar una serie (#91), a
    cambio de los 95px de margen que el legend pedía arriba (ahora 30).

    `tot_*` son los `total` de `_series_por_rangos` (o None); `tramo_*` el
    texto de los días sumados, para el tooltip; `sin_dato`/`n_ok`/`n_tot`,
    los períodos sin año pasado que quedaron fuera (regla #660);
    `a_la_fecha`, los KPI de «Mes a la fecha» y «Año a la fecha» ya
    armados; `lectura`, los `(texto, tooltip)` de `_lectura`."""
    partes = _kpis_totales(tot_act, tot_ap, es_desc, tramo_act, tramo_ap,
                           neto=neto, sin_dato=sin_dato, n_ok=n_ok,
                           n_tot=n_tot)
    if a_la_fecha:
        partes.append('<div class="vt-kpis-sep"></div>')
        partes.extend(a_la_fecha)
    html = '<div class="vt-kpis">' + "".join(partes) + "</div>"
    if lectura:
        html += ('<div class="vt-lectura">' + "".join(
            f'<span title="{escape(tip)}">{escape(txt)}</span>'
            for txt, tip in lectura) + "</div>")
    return html


def _kpi_ppto(ppto, actual, n_con, n_tot, neto=False):
    """El KPI del presupuesto de la ventana (#669): cuánto se cumplió, sobre
    los períodos que tienen presupuesto cargado."""
    _p = actual / ppto * 100 if ppto else 0.0
    _col = EXITO if _p >= 100 else (ADVERTENCIA_TEXTO if _p >= 90 else ERROR)
    _que = "neto" if neto else "venta bruta"
    return _kpi(
        "Presupuesto", f"{_p:.0f} %", fmt_k(ppto), color_val=_col,
        muestra=ADVERTENCIA,
        tip=(f"Cumplimiento del presupuesto ({_que}): S/ {actual:,.0f} de "
             f"S/ {ppto:,.0f}"
             + (f", en los {n_con} de {n_tot} períodos que tienen presupuesto"
                if n_con < n_tot else "")
             + ". El mes es el cargado; la semana y el día, repartidos según "
               "la venta de cada día de la semana el año anterior. Se edita "
               "en Costos › Presupuesto de venta."))


def _kpi_a_la_fecha(rot, tot_act, tot_ap, tramo, neto=False):
    """El KPI de «Mes a la fecha» / «Año a la fecha»: el % contra los mismos
    días del calendario un año antes y, chico, el monto de hoy. Vacío si
    falta el año pasado. Pura."""
    if not tot_act or not tot_ap or not tot_ap.get("venta"):
        return ""
    v_a, v_p = tot_act["venta"], tot_ap["venta"]
    _txt, _col = _var_txt((v_a / v_p - 1) * 100)
    return _kpi(rot, _txt, fmt_k(v_a), color_val=_col, clase="vt-kpi-alf",
                tip=(f"{rot}, {'neto' if neto else 'venta'}: S/ {v_a:,.0f} "
                     f"contra S/ {v_p:,.0f} los mismos días del calendario un "
                     f"año antes ({tramo}). No depende de la ventana de "
                     "arriba; sí de los filtros."))



# ── Pieza propia: las cuentas de arriba siguen siendo la referencia ─────
from pathlib import Path

_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "ventas_comparativo",
    css=(_AQUI / "ventas_comparativo.css").read_text(encoding="utf-8"),
    js=(_AQUI / "_xlsx.js").read_text(encoding="utf-8")
    + (_AQUI / "ventas_comparativo.js").read_text(encoding="utf-8"),
)
_K_CACHE = "_vt_comparativo_cache"


@st.fragment
def _ventas_comparativo(d, col_venta, col_fecha, col_pax=None, col_pedido=None,
                        col_prod=None, col_cant=None, col_fam=None,
                        col_sub=None, filtrar_cb=None, col_neto=None,
                        filtros=None):
    """Misma firma que antes (#357); controles y detalle en el navegador.

    El ancla y los chips vienen del dispatcher. Se trae una sola vez el
    rango que cubre todas las ventanas y sus equivalentes; no se recarga
    por cambiar Día/Semana/Mes, buscar, elegir barras ni bajar el Excel.
    """
    from graficos import ventas_comparativo_datos as datos

    if not (col_venta and col_fecha) or d is None or d.empty:
        st.info("Sin ventas con fecha para comparar.")
        return
    fechas = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
    if fechas.empty:
        st.info("Sin fechas válidas en el rango cargado.")
        return
    ancla = fechas.max().date()
    cfg = REPORTES.get("Ventas", {})
    archivo = cfg.get("archivo", "ventas.parquet")
    cp = cfg.get("carga_por_rango", "FEC REG DOCUMENTO")
    firma = (id(d), d.shape, sello_datos(archivo), str(ancla),
             repr(filtros), venta_por_turno())
    cache = st.session_state.get(_K_CACHE)
    if cache is None or cache[0] != firma:
        with st.spinner("Preparando el comparativo y sus ventanas…"):
            ini, fin = datos.limites(ancla)
            rf = rango_fechas(archivo, cp)
            inicio = pd.Timestamp(rf[0]).date() if rf and rf[0] is not None else None
            if inicio:
                ini = max(ini, inicio)
            historico = _cargar_tramo(archivo, cp, ini, fin, filtrar_cb)
            if historico is None or historico.empty:
                st.info("No se pudieron cargar las ventas para comparar. Reintentá en unos segundos.")
                return
            cols = {"venta": col_venta, "fecha": col_fecha, "pax": col_pax,
                    "pedido": col_pedido, "prod": col_prod, "cant": col_cant,
                    "fam": col_fam, "sub": col_sub, "neto": col_neto}
            aplica = presupuesto_ventas.aplica(filtros)
            payload = datos.armar(
                historico, cols, ancla, inicio, sello=firma[2],
                diario=presupuesto_ventas.diario() if aplica else None,
                ppto_aplica=aplica, servicios=(filtros or {}).get("Servicio"), filtros=filtros)
            payload["alto_fig"] = alturas.VENTAS_COMP_FIG
            st.session_state[_K_CACHE] = (firma, payload)
    else:
        payload = cache[1]
    _PIEZA(key="vt_comp_pieza", data=payload, width="stretch")
