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
import plotly.graph_objects as go
import streamlit as st

import cortes
import definicion_venta as dv
import presupuesto_ventas
from data import REPORTES, cargar_rango, rango_fechas, sello_datos, venta_por_turno
from tema import (
    ACENTO, ADVERTENCIA, ADVERTENCIA_TEXTO, ERROR, EXITO, GRIS_BORDE,
    GRIS_TEXTO, LAVANDA_BORDE, PALETA_SERIES,
)
from graficos.base import _card, _es_movil, franja_cabecera
from inyecciones._iframe import inyectar_html
from graficos.compras._comun import _first_point, _fmt_variacion
from graficos import alturas
from utils import fmt_k


# Los switches del panel «Detalle» pintan su pista con el color de la serie
# cuando están PRENDIDOS (`estilos/_80_cards.py`). Hasta el 2026-09-18 el CSS
# lo preguntaba con `label:has(input:checked)`: una pseudo-clase adentro de
# un `:has()` hace que cada elemento que un rerun inserta —en CUALQUIER
# reporte, porque la regla es global— recalcule los estilos de la página
# entera (regla #469). No hay combinador que llegue sin `:has()`: el
# `input` vive adentro de un `span` y la pista es hermana del `span`. Así
# que este script copia el estado a `label[data-on]`, en el cambio y cada
# 300 ms (Python también los reescribe en un rerun), y escribe sólo si
# cambió.
_JS_ESPEJO_SWITCH = """<script>
(function () {
  var w = window.parent, doc = w.document;
  var SEL = '[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"] input[type="checkbox"]';
  function espejar() {
    var ins = doc.querySelectorAll(SEL);
    for (var i = 0; i < ins.length; i++) {
      var lab = ins[i].closest("label");
      if (!lab || lab.hasAttribute("data-on") === ins[i].checked) continue;
      if (ins[i].checked) lab.setAttribute("data-on", "");
      else lab.removeAttribute("data-on");
    }
  }
  try { if (w.__switchApagar) w.__switchApagar(); } catch (e) {}
  function pronto() { setTimeout(espejar, 0); }
  doc.addEventListener("change", pronto, true);
  doc.addEventListener("click", pronto, true);
  var reloj = setInterval(espejar, 300);
  w.__switchApagar = function () {
    doc.removeEventListener("change", pronto, true);
    doc.removeEventListener("click", pronto, true);
    clearInterval(reloj);
  };
  espejar();
})();
</script>"""

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


@st.fragment
def _ventas_comparativo(d, col_venta, col_fecha, col_pax=None, col_pedido=None,
                        col_prod=None, col_cant=None, col_fam=None,
                        col_sub=None, filtrar_cb=None, col_neto=None,
                        filtros=None):
    """Comparativo Año Pasado vs Actual por día, semana o mes — en montos o
    descompuesto en pax × ticket, con el total de la ventana arriba y, al
    clickear un período, qué productos explican su diferencia (#659).

    `filtros` son los chips de la franja (`{"Grupo": [...], ...}`): con
    uno de grupo, subgrupo o canal el presupuesto no aplica (#669)."""
    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el comparativo.")
        return

    _fe = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
    if _fe.empty:
        st.info("Sin fechas válidas en el rango cargado.")
        return
    ancla = _fe.max().date()

    # ── Título → línea → controles → línea → gráfico, TODO dentro de la
    # tarjeta ── Del 2026-08-15 al 2026-09-25 el título vivió afuera, en un
    # contenedor `position: fixed` anclado a la franja de arriba. Con la
    # pila (la sección se construye mientras se mira la de al lado) y la
    # franja que se esconde (#473), quedaba flotando encima de OTRA sección.
    # En una pila cada sección lleva su título adentro. Ver arquitectura.md
    # regla #526.
    #
    # Misma forma que Ventas › Por día (arquitectura.md #104), con una
    # diferencia que cambia el diseño: acá son CUATRO grupos independientes,
    # no cuatro tabs de la misma cosa. Se agrupan por eje — a la izquierda
    # "cómo corto el tiempo" (granularidad → ventana → alineación), a la
    # derecha "qué muestro" (Montos/Descomposición) — y los tres de la
    # izquierda se separan con hairlines verticales. El separador lo dibuja
    # cada grupo a su IZQUIERDA (estilos/_80_cards.py), NO una regla por
    # posición: así "alinear por" se lleva el suyo cuando desaparece en
    # granularidad Semana/Mes. Con una regla por posición quedaría una línea
    # suelta anunciando un grupo vacío.
    #
    # La tarjeta se abre ACÁ, y no en el `with` de más abajo, porque la franja
    # de controles tiene que quedar DENTRO. Para no re-indentar las ~400
    # líneas de cálculo que hay en el medio, se reservan tres huecos que se
    # rellenan cuando ya hay con qué:
    #   · `_ph_hdr`    el título, que nombra la granularidad y la alineación
    #                  que eligen los controles de abajo (regla #108).
    #   · `_ph_vista`  "Vista" depende de `hay_pax`, que depende de los datos,
    #                  que dependen de los controles de esta MISMA franja.
    #   · `_slot_graf` el gráfico, que se arma al final.
    # Se lee de session_state y no de `grano` porque `grano` sale del pills que
    # va DENTRO de estas columnas — hay que decidir antes de crearlas. En el
    # rerun el estado del widget ya está actualizado, así que coincide; en el
    # primer run no hay estado y el default ("Día") es el mismo del pills.
    _grano_layout = st.session_state.get("ventas_comp_grano") or "Día"
    # La granularidad va en la KEY de la tarjeta, y no es cosmético: es la
    # regla #70. Un `st.container(key=...)` tiene identidad estable y RETIENE
    # los hijos huérfanos de la vista anterior. Con una key fija, al pasar de
    # Día a Semana el título y las opciones de Ventana se actualizaban bien
    # (Python estaba correcto) pero en el DOM quedaban las CINCO columnas del
    # layout de Día y el pills de "alinear por" seguía ahí, huérfano y
    # envolviendo a dos filas — franja de 156px en vez de 52. Medido y
    # reproducido con Semana y con Mes. Al variar la key, la tarjeta remonta
    # limpia en cada cambio de granularidad.
    with _card(f"ventas_comparativo_{_grano_layout}"):
        _ph_hdr = st.empty()
        # UNA FILA HORIZONTAL, cada grupo a su ancho de contenido (regla
        # #659). Hasta el 2026-10-05 eran `st.columns([1.3, 1.6, 2.1, 0.5,
        # 1.5])`: cada columna medía más que su grupo, todo el sobrante caía
        # a la DERECHA del grupo, y la línea —que cada grupo dibuja a su
        # izquierda— quedaba a 102-113px del grupo anterior y a 17 del
        # siguiente (medido a 1440): se leía como el borde del grupo de la
        # derecha, no como un separador. Y «Vista» no llegaba al borde: 108px
        # de aire a la derecha contra 16 a la izquierda.
        #
        # Sin `gap`: el aire lo pone el `padding-left` de cada envoltorio y la
        # línea va en la mitad de ese padding (`estilos/_80_cards.py`), así
        # que es el mismo a los dos lados; y la fila es un container query
        # que lo achica cuando ELLA es angosta (con la columna fijada
        # también). `st.space("stretch")` empuja «Vista» contra el borde — lo
        # que la #107 no logró con `justify-content`: allá se empujaba el div
        # interno del stButtonGroup; acá se acomoda el envoltorio del grupo.
        # Los envoltorios llevan `_g_` en la key para que no los atrapen los
        # `[class*="st-key-ventas_comp_grano"]` (y demás) de los pills.
        with st.container(horizontal=True, gap=None,
                          key=f"ventas_comp_ctrl_{_grano_layout}"):
            c1 = st.container(width="content", key="ventas_comp_g_grano")
            c2 = st.container(width="content", key="ventas_comp_g_ventana")
            c3 = (st.container(width="content", key="ventas_comp_g_modo")
                  if _grano_layout == "Día" else None)
            st.space("stretch")
            # Venta | Neto (regla #660): sólo si el parquet trae el neto.
            c5 = (st.container(width="content", key="ventas_comp_g_monto")
                  if col_neto else None)
            c4 = st.container(width="content", key="ventas_comp_g_vista")
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
        # `c3 is not None` protege el caso raro en que la fila se armó con un
        # grano y el widget devolvió otro: sin la guarda sería un
        # AttributeError sobre None en vez de una franja sin «alinear por».
        if grano == "Día" and c3 is not None:
            with c3:
                modo_lbl = st.pills(
                    "Alinear por", ["Mismo día de semana", "Misma fecha"],
                    default="Mismo día de semana", key="ventas_comp_modo",
                    label_visibility="collapsed",
                ) or "Mismo día de semana"
            modo = "semana" if modo_lbl.startswith("Mismo día") else "calendario"
        neto = False
        if c5 is not None:
            with c5:
                # La key empieza con `ventas_comp_vista` A PROPÓSITO: hereda
                # el dibujo de los pills de «Vista» (estilos/_80_cards.py
                # matchea por prefijo), que es el que tiene que tener.
                neto = (st.pills(
                    "Monto", ["Venta", "Neto"], default="Venta",
                    key="ventas_comp_vista_monto", label_visibility="collapsed")
                    or "Venta") == "Neto"
        col_m = col_neto if neto else col_venta
        with c4:
            _ph_vista = st.empty()
        # CABECERA PROVISIONAL, ya. No esperar al final: `st.empty()` BORRA su
        # contenido al crearse, así que dejarlo vacío durante la carga de
        # datos hacía que la tarjeta perdiera la fila del título y la
        # recuperara al terminar — el "sube y baja" de cada clic. `vista`
        # todavía no existe acá, pero su valor del rerun anterior sí está en
        # session_state y es el que va a salir el 99% de las veces; al final
        # se reescribe con el real y, si coincide, Streamlit no toca el DOM.
        # Ver arquitectura.md regla #108.
        franja_cabecera(_ph_hdr, _titulo_comparativo(
            grano, modo,
            st.session_state.get("ventas_comp_vista") == "Descomposición",
            neto=neto))
        # Línea INFERIOR de la franja de controles. Los -18px + width:calc(100% + 36px)
        # compensan el padding horizontal de la tarjeta para que toque el
        # borde real, igual que en Por día (arquitectura.md #104).
        st.markdown(
            f'<hr style="border:none;border-top:2px solid {GRIS_BORDE};'
            'margin:-6px -18px 12px;width:calc(100% + 36px);">',
            unsafe_allow_html=True)
        # El TOTAL DE LA VENTANA (regla #659): se reserva acá —entre la franja
        # y el gráfico, fuera del slot, porque adentro lo taparía el panel
        # «Detalle» flotante— y se llena cuando ya están los datos. El CSS le
        # da un alto mínimo para que la tarjeta no salte mientras carga (#108).
        _ph_tot = st.container(key="ventas_comp_tot").empty()
        # Key propia (no sólo `st.container()` a secas): el CSS necesita
        # un ancla `position: relative` scopeada AL PLOT, no a toda la
        # tarjeta (que incluye la franja de controles de arriba) — así
        # el panel "Detalle" flotante (`ventas_comp_detalle_float`) queda
        # pegado al borde superior del gráfico sin importar cuánto mida
        # esa franja. Prefijo por `_grano_layout` como el resto de esta
        # función (regla #70): remonta limpio al cambiar de granularidad.
        _slot_graf = st.container(key=f"ventas_comp_chart_slot_{_grano_layout}")

    claves = _claves_hacia_atras(ancla, grano, ventana)
    claves_ap = [_clave_ap(k, grano, modo) for k in claves]
    rangos_act, rangos_ap, parciales = _rangos_comparables(
        claves, claves_ap, grano, ancla)

    cfg = REPORTES.get("Ventas", {})
    _arch = cfg.get("archivo", "ventas.parquet")
    _colp = cfg.get("carga_por_rango", "FEC REG DOCUMENTO")
    # Los períodos cuyo año pasado cae antes del primer día del parquet no
    # son «cero ventas», son «no hay dato» (regla #660): fuera del total, de
    # los dos lados, y sin barra del año pasado.
    _rf = rango_fechas(_arch, _colp)
    ok = _comparables(rangos_ap, _rf[0] if _rf else None)
    _extra = dict(en_total=ok, col_neto=None if neto else col_neto,
                  col_grupo=col_fam)
    serie_act, pax_act_d, cli_act_d, tot_act = _series_por_rangos(
        _arch, _colp, col_fecha, col_m, col_pax, col_pedido,
        rangos_act, filtrar_cb, **_extra)
    serie_ap, pax_ap_d, cli_ap_d, tot_ap = _series_por_rangos(
        _arch, _colp, col_fecha, col_m, col_pax, col_pedido,
        rangos_ap, filtrar_cb, **_extra)

    y_act = [float(serie_act.get(k, 0.0)) for k in claves]
    y_ap = [float(serie_ap.get(k, 0.0)) if b else 0.0
            for k, b in zip(claves_ap, ok)]
    if not any(y_act) and not any(y_ap):
        st.info("Sin datos de venta en la ventana elegida.")
        return
    hay_ap = any(y_ap)

    # Descomposición: Venta ≈ Pax × Ticket (sin la venta de los canales sin
    # clientes, regla #591), así que %Δventa, %Δpax y %Δticket
    # viven en el MISMO eje de % y contestan "¿vino menos gente o gastaron
    # menos?" — la pregunta que sigue a cualquier caída. Sólo se ofrece si
    # hay pax deduplicable por pedido (ver _series_por_rangos).
    p_act = [float(pax_act_d.get(k, 0.0)) for k in claves]
    p_ap = [float(pax_ap_d.get(k, 0.0)) if b else 0.0
            for k, b in zip(claves_ap, ok)]
    hay_pax = bool(pax_act_d) and any(p_ap) and any(p_act)
    vista = "Montos"
    if hay_pax and hay_ap:
        # Se dibuja en el hueco que la franja de arriba dejó reservado. No se
        # puede declarar allá directamente: depende de `hay_pax`, que sale de
        # los datos, que salen de grano/ventana — sus vecinos de la MISMA
        # franja. El placeholder es lo que rompe esa circularidad.
        vista = _ph_vista.pills(
            "Vista", ["Montos", "Descomposición"], default="Montos",
            key="ventas_comp_vista", label_visibility="collapsed") or "Montos"

    etiquetas = [_etiqueta_clave(k, grano) for k in claves]
    # Con más de MAX_ETIQUETAS barras, valor + %Var + "en curso" apilados se
    # pisan entre sí (y contra los de la categoría vecina) — mismo umbral
    # que ya usaba el %Var, ahora también gobierna las etiquetas de valor.
    mostrar_etq = len(claves) <= MAX_ETIQUETAS
    _txt_ap = ([_fmt_soles_compacto(v) if b else "" for v, b in zip(y_ap, ok)]
               if mostrar_etq else None)
    _txt_act = [_fmt_soles_compacto(v) for v in y_act] if mostrar_etq else None

    es_desc = vista == "Descomposición"

    # El presupuesto de cada período, sobre los MISMOS días que la barra
    # actual (un período en curso, hasta el último día con venta). Sólo en
    # Montos y sin filtros que parten la venta (#669).
    ppto = [None] * len(claves)
    if not es_desc and presupuesto_ventas.aplica(filtros):
        ppto = presupuesto_ventas.en_rangos(
            presupuesto_ventas.diario(), [(i, f) for (_k, i, f) in rangos_act],
            neto=neto, servicios=(filtros or {}).get("Servicio"))
    hay_ppto = any(v is not None for v in ppto)

    # El total de la ventana, en el hueco que dejó la franja (regla #659).
    def _tramo(rangos):
        return f"{rangos[0][1]:%d/%m/%Y} al {rangos[-1][2]:%d/%m/%Y}"
    # Cuánto de cada barra es calendario (regla #660): los días de semana
    # de más o de menos. Por período para la marca de la barra y, sumado en
    # soles, para la línea «Por qué».
    _dias_ap = (tot_ap or {}).get("dias") or {}
    efecto_cal = [(_efecto_calendario(ra[1:], rp[1:], _dias_ap) if b else None)
                  for ra, rp, b in zip(rangos_act, rangos_ap, ok)]
    _v_ap_ok = sum(v for v, b in zip(y_ap, ok) if b)
    _cal_tot = (sum((e or 0.0) / 100 * v for e, v in zip(efecto_cal, y_ap))
                / _v_ap_ok * 100 if _v_ap_ok else None)
    _sin_dato = _texto_sin_dato(claves_ap, ok, grano)
    _alf = []
    if hay_ap:
        _firma = (len(d), round(float(pd.to_numeric(
            d[col_venta], errors="coerce").sum()), 2))
        for _rot, _tipo in (("Mes a la fecha", "mes"), ("Año a la fecha", "año")):
            _i, _f, _ip, _fp = _a_la_fecha(ancla, _tipo)
            if _rf and _ip < _rf[0]:
                continue
            _ta = _total_memo(_arch, _colp, col_fecha, col_m, _i, _f,
                              filtrar_cb, _firma)
            _tp = _total_memo(_arch, _colp, col_fecha, col_m, _ip, _fp,
                              filtrar_cb, _firma)
            _alf.append(_kpi_a_la_fecha(
                _rot, _ta, _tp, f"{_i:%d/%m} al {_f:%d/%m/%Y} contra "
                f"{_ip:%d/%m} al {_fp:%d/%m/%Y}", neto=neto))
        _alf = [k for k in _alf if k]
    if hay_ppto:
        _alf.insert(0, _kpi_ppto(
            sum(v for v in ppto if v is not None),
            sum(a for a, v in zip(y_act, ppto) if v is not None),
            sum(v is not None for v in ppto), len(ppto), neto=neto))
    _ph_tot.markdown(
        _html_totales(tot_act, tot_ap if hay_ap else None, es_desc,
                      _tramo(rangos_act), _tramo(rangos_ap), neto=neto,
                      sin_dato=_sin_dato, n_ok=sum(ok), n_tot=len(ok),
                      a_la_fecha=_alf,
                      lectura=(_lectura(tot_act, tot_ap, neto=neto,
                                        calendario=_cal_tot)
                               if hay_ap else ())),
        unsafe_allow_html=True)

    d_venta = [_pct(a, b) for a, b in zip(y_act, y_ap)]
    d_pax = [_pct(a, b) for a, b in zip(p_act, p_ap)]
    # Ticket = venta de los canales con clientes ÷ pax (regla #591): la de
    # Rappi, que no carga pax, queda afuera. Si falta cualquiera de los dos
    # lados, el ticket de ese período no existe (None) y la línea corta ahí
    # en vez de inventar.
    c_act = [float(cli_act_d.get(k, 0.0)) for k in claves]
    c_ap = [float(cli_ap_d.get(k, 0.0)) if b else 0.0
            for k, b in zip(claves_ap, ok)]
    t_act = [(v / p if p else None) for v, p in zip(c_act, p_act)]
    t_ap = [(v / p if p else None) for v, p in zip(c_ap, p_ap)]
    d_ticket = [(_pct(a, b) if (a is not None and b) else None)
                for a, b in zip(t_act, t_ap)]

    # Qué series se dibujan en Descomposición. Los checkboxes viven en el
    # panel "Detalle" (abajo, DESPUÉS del gráfico) pero la figura se arma
    # ACÁ, así que el valor se lee de session_state — que es donde el widget
    # dejó lo elegido en el rerun anterior.
    #
    # El default NO se siembra con `setdefault`: se probó y el checkbox lo
    # IGNORA (se dibujaba destildado mientras la figura mostraba las tres
    # series — widget y gráfico diciendo cosas distintas). El default va
    # donde Streamlit lo respeta, en `value=True` del propio widget, y acá
    # se lee con `.get(..., True)` para el primer render, cuando la clave
    # todavía no existe. Un solo dueño del valor: el widget.
    _SERIES_DESC = ("venta", "pax", "ticket")
    _ver = {s: bool(st.session_state.get(f"ventas_comp_ver_{s}", True))
            for s in _SERIES_DESC}
    # Sin legend nativo desde el 2026-10-05 (regla #659): la leyenda es la
    # fila del total (`_html_totales`), que pinta con el color de cada serie
    # lo que se dibuja y además dice su cifra. En Descomposición, encima, el
    # control son los switches del panel "Detalle".

    fig = go.Figure()
    if es_desc:
        _col_barra = [(EXITO if (v is not None and v >= 0) else ERROR)
                      for v in d_venta]
        fig.add_bar(
            x=etiquetas, y=d_venta, name="%Δ venta",
            marker=dict(color=_col_barra), opacity=0.82,
            text=([None if v is None else _var_txt(v)[0] for v in d_venta]
                  if mostrar_etq else None),
            textposition="outside", cliponaxis=False, textfont=dict(size=11),
            visible=_ver["venta"],
            customdata=[_texto_periodo(k, grano, fin) for (k, _i, fin) in rangos_act],
            hovertemplate="%{customdata}<br>Venta: %{y:+.1f}%<extra></extra>",
        )
        fig.add_trace(go.Scatter(
            x=etiquetas, y=d_pax, name="%Δ pax", mode="lines+markers",
            line=dict(color=PALETA_SERIES[1], width=2),
            marker=dict(size=7, line=dict(color="white", width=1.5)),
            visible=_ver["pax"],
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
            visible=_ver["ticket"],
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
            textfont=dict(size=11, color=GRIS_TEXTO),
            customdata=[_texto_periodo(k, grano, fin, con_numero=False)
                        for (k, _i, fin) in rangos_ap],
            hovertemplate="Año pasado · %{customdata}<br>S/ %{y:,.0f}<extra></extra>",
        )
        fig.add_bar(
            x=etiquetas, y=y_act, name="Actual",
            marker=dict(color=ACENTO),
            text=_txt_act, textposition="outside", cliponaxis=False,
            textfont=dict(size=11, color=ACENTO),
            customdata=[_texto_periodo(k, grano, fin) for (k, _i, fin) in rangos_act],
            hovertemplate="Actual · %{customdata}<br>S/ %{y:,.0f}<extra></extra>",
        )
        if hay_ppto:
            # Una raya sobre el par de barras: la meta del período (#669).
            fig.add_trace(go.Scatter(
                x=etiquetas, y=ppto, name="Presupuesto", mode="markers",
                marker=dict(symbol="line-ew", size=46, color=ADVERTENCIA,
                            line=dict(width=3, color=ADVERTENCIA)),
                customdata=[[_texto_periodo(k, grano, fin),
                             (a / v * 100 if v else 0.0)]
                            for (k, _i, fin), a, v in zip(
                                rangos_act, y_act, [x or 0.0 for x in ppto])],
                hovertemplate=("Presupuesto · %{customdata[0]}<br>S/ %{y:,.0f}"
                               " · cumplido %{customdata[1]:.0f} %"
                               "<extra></extra>"),
            ))
    # El período en curso se marca: aunque el año pasado ya viene recortado
    # al mismo tramo (comparación justa), el usuario tiene que saber que esa
    # barra no es un mes/semana entero — si no, la lee como cerrada. Offset
    # en unidades de dato (no yshift en píxeles) para apilar en el mismo
    # sistema que el %Var de abajo, arriba de las etiquetas de valor.
    # Sólo las series VISIBLES entran en la escala: si se destildó una en el
    # panel "Detalle", dejar su máximo acá reservaría aire para una curva que
    # ya no se dibuja y las que quedan se verían aplastadas.
    _vis_desc = [d for d, _on in ((d_venta, _ver["venta"]), (d_pax, _ver["pax"]),
                                  (d_ticket, _ver["ticket"])) if _on]
    if es_desc:
        _vals = [v for d in _vis_desc for v in d if v is not None]
        _tope = (max(abs(v) for v in _vals) if _vals else 1) or 1
    else:
        _tope = max(max(y_act, default=0), max(y_ap, default=0)) or 1
    for i in parciales:
        _base = (max([d[i] for d in _vis_desc if d[i] is not None] or [0])
                 if es_desc else max(y_act[i], y_ap[i]))
        fig.add_annotation(
            x=i, y=_base + _tope * (0.24 if mostrar_etq else 0.04),
            showarrow=False, text="en curso",
            font=dict(size=10, color=GRIS_TEXTO))

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
                    font=dict(size=10, color=ADVERTENCIA_TEXTO))
        for i, f in enumerate(claves):
            if not ok[i]:
                fig.add_annotation(
                    x=i, y=1.0, yref="paper", yanchor="bottom",
                    showarrow=False, text="sin dato AP",
                    font=dict(size=10, color=GRIS_TEXTO))
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
        # Y desde el 2026-10-16 (regla #660) el calendario: un mes trae
        # días de semana de más o de menos —un sábado de más pesa—, y la
        # marca dice cuánto de su %Var es eso, si llega a un punto.
        for i, k in enumerate(claves):
            _marcas = []
            n_act = _feriados_entre(*_rango_de_clave(k, grano))
            n_ap = _feriados_entre(*_rango_de_clave(claves_ap[i], grano))
            if n_act != n_ap:
                _dif = n_act - n_ap
                _marcas.append(f"{'+' if _dif > 0 else '−'}{abs(_dif)} fer.")
            _e = efecto_cal[i]
            if _e is not None and abs(_e) >= 1 and mostrar_etq:
                _marcas.append(f"cal. {_var_txt(_e)[0]}")
            if not ok[i]:
                _marcas = ["sin dato AP"]
            if not _marcas:
                continue
            fig.add_annotation(
                x=i, y=1.0, yref="paper", yanchor="bottom", showarrow=False,
                text=" · ".join(_marcas),
                font=dict(size=10, color=(GRIS_TEXTO if not ok[i]
                                          else ADVERTENCIA_TEXTO)))

    # El %Var sólo se anota aparte en Montos: en Descomposición la barra YA
    # es el %Δ de venta y lleva su propia etiqueta (`text=` de la traza).
    if hay_ap and mostrar_etq and not es_desc:
        for i, (a, b) in enumerate(zip(y_act, y_ap)):
            if not b:
                continue
            _txt, _col = _var_txt((a - b) / b * 100)
            fig.add_annotation(
                x=i, y=max(a, b) + _tope * 0.14, showarrow=False,
                text=_txt, font=dict(size=11, color=_col))

    fig.update_layout(
        barmode="group", bargap=0.28, bargroupgap=0.08,
        # Los altos viven en `alturas.py` (con el porqué de cada número).
        height=(alturas.VENTAS_COMP_FIG_MOVIL if _es_movil()
                else alturas.VENTAS_COMP_FIG),
        # Arriba sólo queda la franja de los rótulos «feriado»/«±1 fer.»
        # (y=1.0 paper): el legend se fue a la fila del total (#659) y las
        # etiquetas de Montos caen DENTRO del área por el rango del eje Y de
        # abajo. En Descomposición, además, el panel «Detalle» flota en la
        # esquina de arriba: con 50 no le tapa nada.
        margin=dict(l=10, r=10, t=(50 if es_desc else 30), b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=GRIS_TEXTO, size=12),
        showlegend=False,
        hovermode="x unified",
    )
    # Fechas HORIZONTALES (no en diagonal). Dos cosas hacen que entren:
    #  · en día y semana, el prefijo ("Mié", "S32") baja a su propia línea:
    #    de lado, "Mié 29/07" mide ~56px y a 14 barras se pisa con la vecina;
    #    partido mide la mitad. El texto del eje se arma aparte de `etiquetas`
    #    (que siguen siendo la categoría real) para no meter <br> en el hover.
    #  · con muchas barras se muestra una cada `_paso` — a lo sumo
    #    ~MAX_ETIQUETAS etiquetas en el eje.
    _paso = max(1, -(-len(claves) // MAX_ETIQUETAS))
    _tickvals = [e for i, e in enumerate(etiquetas) if i % _paso == 0]
    _ticktext = [(e.replace(" ", "<br>", 1) if grano in ("Día", "Semana") else e)
                 for e in _tickvals]
    fig.update_xaxes(type="category", tickangle=0, tickfont=dict(size=12),
                     showgrid=False, tickmode="array",
                     tickvals=_tickvals, ticktext=_ticktext)
    if es_desc:
        fig.update_yaxes(ticksuffix="%", tickformat=",.0f",
                         gridcolor=GRIS_BORDE, zeroline=False)
    else:
        # Rango FIJO en Montos (regla #659): las etiquetas de valor, el %Var
        # (+14 % del tope) y «en curso» (+24 %) son anotaciones, y el
        # autorange no las ve. Con el margen de 95 que tenía el legend se
        # salían hacia ese aire; sin él, el rango les hace lugar adentro —
        # el de «en curso» sólo si hay un período en curso (medio renglón
        # de texto arriba de cada uno: ~0.05 del tope).
        # Abajo, lo mismo cuando hay un día negativo (sólo notas de
        # crédito): sin aire, su etiqueta «outside» caía bajo el eje.
        _min = min(y_act + y_ap, default=0.0)
        _esc = max(_tope, -_min)
        _piso = ((_min - _esc * (0.14 if mostrar_etq else 0.04))
                 if _min < 0 else 0.0)
        _techo = ((1.30 if parciales else 1.22) if mostrar_etq else 1.10)
        fig.update_yaxes(tickprefix="S/ ", tickformat=",.0f",
                         gridcolor=GRIS_BORDE, zeroline=False,
                         range=[_piso, _tope * _techo])

    titulo = _titulo_comparativo(grano, modo, es_desc, neto=neto)

    foco = st.session_state.get("ventas_comp_foco")
    if foco is not None and not (0 <= foco < len(claves)):
        foco = None

    # Reescritura con el `vista` REAL. Casi siempre es idéntico al provisional
    # que ya se pintó arriba, y ahí Streamlit no toca el DOM; sólo cambia algo
    # cuando el valor de session_state no era válido para estos datos (por
    # ejemplo "Descomposición" guardado y un rango sin pax).
    franja_cabecera(_ph_hdr, titulo)

    with _slot_graf:
        # La selección de plotly_chart PERSISTE entre reruns: con una key
        # estática el mismo clic se re-procesa en cada rerun y el drill
        # parpadea abriéndose y cerrándose. El foco va en la key (CLAUDE.md).
        evt = st.plotly_chart(
            fig, use_container_width=True,
            key=f"ventas_g_comparativo_{vista}_{grano}_{foco if foco is not None else 'none'}",
            on_select="rerun", selection_mode="points",
            config={"displaylogo": False, "displayModeBar": False})
        if es_desc and not any(_ver.values()):
            st.caption("Ninguna medida seleccionada: marcá al menos una en "
                       "«Detalle» para ver el gráfico.")
        # Panel "Detalle": es el legend de esta vista. Cada fila prende o
        # apaga su serie (switch) y además muestra el valor ABSOLUTO del
        # último período, que el legend de Plotly no puede mostrar.
        # 2026-08-14, 2da vuelta: el `st.popover` (1ra vuelta) resolvía
        # "no empuja el gráfico" pero se veía como DOS piezas flotantes
        # separadas — un botón-cápsula arriba y, con un hueco, un panel
        # aparte abajo (reportado con captura: "como un toggle del cual
        # sale otro toggle"). La referencia es UNA sola tarjeta: el
        # título y las filas viven en el MISMO rectángulo, sin costura.
        # Un popover no puede dar eso — su contenido SIEMPRE se renderiza
        # en un portal aparte (`stPopoverBody`), con su propio offset y
        # sombra. Se volvió al patrón manual: un `st.button` que hace de
        # título+chevron (con CSS para que no se vea a sí mismo como
        # botón) y `st.session_state` guardando si está abierto; las
        # filas se dibujan o no DENTRO del mismo `st.container(key=
        # "ventas_comp_detalle_float")` que ya es `position:absolute`
        # sobre `_slot_graf` (estilos/_80_cards.py). Ese contenedor NO
        # cambia de posición al abrirse/cerrarse —sigue fuera del flujo—
        # así que el gráfico sigue sin moverse, sin necesitar un portal.
        if es_desc:
            _etq_ultimo = _etiqueta_clave(claves[-1], grano)

            def _toggle_detalle():
                # on_click, no el return de st.button: el return sólo se
                # sabe DESPUÉS de que el botón ya se dibujó con el ícono
                # viejo en esta misma pasada — el chevron quedaría un
                # clic atrasado (probado: abría el panel pero seguía
                # mostrando la flecha "cerrado"). on_click corre ANTES
                # de que el script vuelva a correr desde arriba, así que
                # para cuando se arma el botón de nuevo session_state ya
                # tiene el valor nuevo.
                st.session_state["ventas_comp_detalle_abierto"] = (
                    not st.session_state.get(
                        "ventas_comp_detalle_abierto", False))

            with st.container(key="ventas_comp_detalle_float"):
                _abierto = st.session_state.get(
                    "ventas_comp_detalle_abierto", False)
                _chevron = "keyboard_arrow_up" if _abierto else "keyboard_arrow_down"
                st.button(f"Detalle · {_etq_ultimo}",
                          key="ventas_comp_detalle_toggle",
                          icon=f":material/{_chevron}:",
                          on_click=_toggle_detalle)
                if _abierto:
                    with st.container(key="ventas_comp_detalle_panel"):
                        # La variante de color de Venta sigue el SIGNO,
                        # igual que su barra en el gráfico; pax y ticket
                        # tienen color fijo. El color en sí lo pone el CSS
                        # (estilos/_80_cards.py) leyendo esta variante del
                        # key del container — no va inline acá, porque el
                        # cuadradito ahora es el switch y su caja la
                        # dibuja Streamlit, no nosotros.
                        _v_venta = ("venta_pos"
                                    if (d_venta[-1] is not None
                                        and d_venta[-1] >= 0)
                                    else "venta_neg")
                        _filas = [
                            ("venta", _v_venta, "Venta",
                             f"S/ {y_act[-1]:,.0f}", d_venta[-1]),
                            ("pax", "pax", "Pax", f"{p_act[-1]:,.0f}",
                             d_pax[-1]),
                            ("ticket", "ticket", "Ticket promedio",
                             (f"S/ {t_act[-1]:,.2f}"
                              if t_act[-1] is not None else "—"),
                             d_ticket[-1]),
                        ]
                        # Una fila = [switch | nombre | valor | %Δ].
                        # `gap=None` en el container es lo que las junta:
                        # el gap por defecto entre bloques metía 16px
                        # entre fila y fila, más que el alto de la fila
                        # misma. `width` las mantiene angostas — sin él
                        # las columnas reparten TODO el ancho de la
                        # tarjeta flotante (260, ver estilos/_80_cards.py
                        # para por qué no es 400 como el expander viejo).
                        with st.container(gap=None, width=260):
                            for _k, _variante, _label, _val, _pv in _filas:
                                _pt, _pc = (("—", GRIS_TEXTO) if _pv is None
                                            else _var_txt(_pv))
                                _c = st.columns([0.6, 3, 2, 1.4],
                                                vertical_alignment="center")
                                with _c[0]:
                                    # El container sólo existe para
                                    # colgarle el color al CSS: la key
                                    # del switch tiene que quedar ESTABLE
                                    # (si el signo entrara en su key,
                                    # cambiar de signo le borraría el
                                    # estado al widget). st.toggle en vez
                                    # de st.checkbox (2026-08-13,
                                    # referencia: panel "Comparar con" de
                                    # un gráfico de índices) — mismo
                                    # bool, misma key; ver
                                    # estilos/_80_cards.py para la trampa
                                    # del testid compartido.
                                    with st.container(
                                            key=f"ventas_comp_sw_{_variante}"):
                                        st.toggle(
                                            _label, value=True,
                                            key=f"ventas_comp_ver_{_k}",
                                            label_visibility="collapsed")
                                with _c[1]:
                                    st.markdown(
                                        f'<div style="font-size:13px;'
                                        f'color:#3f3f46;">{_label}</div>',
                                        unsafe_allow_html=True)
                                with _c[2]:
                                    st.markdown(
                                        f'<div style="font-size:13px;'
                                        f'text-align:right;'
                                        f'color:{GRIS_TEXTO};">{_val}</div>',
                                        unsafe_allow_html=True)
                                with _c[3]:
                                    st.markdown(
                                        f'<div style="font-size:13px;'
                                        f'font-weight:600;text-align:right;'
                                        f'color:{_pc};">{_pt}</div>',
                                        unsafe_allow_html=True)
                            # El estado del switch, espejado en su `label`.
                            inyectar_html(_JS_ESPEJO_SWITCH)
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
                     "año pasado (52 semanas antes): la fecha se corre 1 o 2 "
                     "días, pero un sábado se compara contra un sábado."
                     if modo == "semana" else
                     "Cada día se compara contra la misma fecha del año "
                     "pasado. Ojo: el día de semana no coincide — un "
                     "miércoles puede quedar comparado contra un martes.")
            _cal_txt = (" Banda gris = fin de semana · banda ámbar = feriado "
                        "nacional (Perú); «feriado AP» marca el caso en que "
                        "el feriado cae del lado del año pasado, no de este.")
        else:
            # Semana sí cancela el día de semana (364 días: los mismos siete);
            # el mes NO — hasta el 2026-10-16 el texto decía que sí (#660).
            _expl = (
                "Cada semana se compara contra la de 52 semanas antes: los "
                "mismos siete días de semana de los dos lados."
                if grano == "Semana" else
                "Cada mes se compara contra el mismo mes del año pasado, que "
                "puede traer un sábado o un domingo más o menos: «cal.» dice "
                "cuánto del %Var es sólo eso.")
            _cal_txt = (" «±1 fer.»: el período no tiene los mismos feriados "
                        "que su equivalente (Semana Santa cambia de mes).")
        _lbl = ("" if not hay_ap or len(claves) <= MAX_ETIQUETAS else
                f" Con más de {MAX_ETIQUETAS} barras el %Var no se dibuja "
                "sobre ellas (se pisaría); está en el hover.")
        if parciales:
            _lbl += (" El período marcado «en curso» todavía no terminó: se "
                     "compara contra el MISMO tramo del año pasado (no contra "
                     "el período entero), así que el %Var es justo.")
        if es_desc:
            _expl = ("Venta ≈ pax × ticket (el ticket deja afuera la venta "
                     "de los canales sin clientes, como Rappi), así que los "
                     "tres %Δ comparten un "
                     "mismo eje. Si la venta cae y el ticket queda plano, "
                     "faltó gente; si cae el ticket y el pax no, vinieron "
                     "igual pero gastaron menos. " + _expl)
        _plural = {"Día": "días", "Semana": "semanas", "Mes": "meses"}[grano]
        _texto_caption = (
            f"Ventana: {ventana} {_plural} hasta {ancla:%d/%m/%Y}. "
            + _expl + _cal_txt + _lbl
            + (" Tocá una barra para ver qué explica su diferencia."
               if col_prod else ""))
        # Móvil: este texto junta ventana + método + feriados + notas en un
        # solo párrafo — a 335px de ancho de card mide ~224px de alto, más de
        # un cuarto de la card entera (medido en 375x812, ver CLAUDE.md). En
        # desktop se queda visible tal cual (ahí entra en 1-2 líneas); en
        # móvil se pliega detrás del mismo patrón "compact" que ya usa
        # "Detalle" un poco más arriba, así sigue a un toque en vez de
        # forzar scroll para llegar al gráfico de abajo.
        if _es_movil():
            with st.expander("Cómo leer este comparativo", expanded=False,
                             type="compact"):
                st.caption(_texto_caption)
        else:
            st.caption(_texto_caption)

    # ── Drill: qué productos explican la diferencia del período ──────────
    # Hasta el 2026-10-05 era el top 15 por venta ACTUAL (regla #659).
    # El clic NO lleva a Mix › Detalle › «Año pasado», aunque esa vista
    # contesta lo mismo: Mix sólo ve el rango de la franja (con el de por
    # defecto, 9 de las 14 barras de Día caen afuera) y llevarlo obligaba a
    # cambiarle la fecha a todo el reporte. Acá el drill ya carga sus dos
    # tramos y responde con el mismo criterio que el puente de Mix.
    if foco is not None and col_prod:
        k = claves[foco]
        _r_act = (rangos_act[foco][1], rangos_act[foco][2])
        _r_ap = (rangos_ap[foco][1], rangos_ap[foco][2])
        _texto_ap = _texto_periodo(claves_ap[foco], grano, rangos_ap[foco][2],
                                   con_numero=False)
        _titulo_platos = (
            "Qué explica la diferencia · "
            f"{_texto_periodo(k, grano, rangos_act[foco][2])} vs. {_texto_ap}")
        # Título propio (no `_card(titulo_arriba=True)`): ese helper dibuja
        # el título en su PROPIA fila, de borde a borde — acá va compartiendo
        # fila con el botón de cerrar, así que el título entra manual (misma
        # clase `.chart-card-hdr`, sin su margen/borde-inferior porque ese
        # ahora lo pone el <hr> de abajo, a lo ancho de las DOS columnas) y
        # "Cerrar" pasa de botón ancho (127×40, a pedido: "muy grande para
        # desktop") a ícono solo, sin relleno — mismo lenguaje minimalista
        # que el resto de controles de esta vista.
        with _card("ventas_comp_platos"):
            _c1, _c2 = st.columns([0.94, 0.06], vertical_alignment="center")
            with _c1:
                st.markdown(
                    f'<p class="chart-card-hdr" style="margin:0;padding:0;'
                    f'border-bottom:none;">{_titulo_platos}</p>',
                    unsafe_allow_html=True)
            with _c2:
                if st.button(":material/close:", key="ventas_comp_cerrar",
                             help="Cerrar"):
                    st.session_state["ventas_comp_foco"] = None
                    st.session_state["ventas_comp_click"] = None
                    st.rerun(scope="fragment")
            st.markdown(
                f'<hr style="border:none;border-top:1px solid {GRIS_BORDE};'
                'margin:0 0 0.55rem;">', unsafe_allow_html=True)
            # El resumen del PERÍODO (regla #660): los KPI de la fila del
            # total y su línea «Por qué», ahora de esta barra sola.
            _firma = (len(d), round(float(pd.to_numeric(
                d[col_venta], errors="coerce").sum()), 2))
            _kw = dict(col_pax=col_pax, col_pedido=col_pedido,
                       col_neto=None if neto else col_neto, col_grupo=col_fam)
            _pa = _total_memo(_arch, _colp, col_fecha, col_m, *_r_act,
                              filtrar_cb, _firma, **_kw)
            _pp = (_total_memo(_arch, _colp, col_fecha, col_m, *_r_ap,
                               filtrar_cb, _firma, **_kw) if ok[foco] else None)
            _txt_a = f"{_r_act[0]:%d/%m/%Y} al {_r_act[1]:%d/%m/%Y}"
            _txt_p = f"{_r_ap[0]:%d/%m/%Y} al {_r_ap[1]:%d/%m/%Y}"
            _html_p = ('<div class="vt-kpis">' + "".join(_kpis_totales(
                _pa, _pp, False, _txt_a, _txt_p, neto=neto)) + "</div>")
            _lec_p = _lectura(_pa, _pp, neto=neto,
                              calendario=efecto_cal[foco])
            if _lec_p:
                _html_p += ('<div class="vt-lectura">' + "".join(
                    f'<span title="{escape(tip)}">{escape(txt)}</span>'
                    for txt, tip in _lec_p) + "</div>")
            with st.container(key="ventas_comp_platos_kpi"):
                st.markdown(_html_p, unsafe_allow_html=True)
            rk = _ranking_platos(_arch, _colp, col_fecha, col_m, col_prod,
                                 col_cant, _r_act, _r_ap, filtrar_cb,
                                 col_fam=col_fam, col_sub=col_sub)
            if rk is None or rk[0].empty:
                st.info("Sin ventas de productos en ese período.")
            else:
                rk, _res = rk
                _drill_detalle(rk, _res)


def _fig_delta(t, col, n=8):
    """Barras horizontales del Δ S/ por `col` (Grupo o Canal), de mayor a
    menor |Δ|, verdes las que suben y rojas las que bajan; los que no
    entran, juntos en «Otros». Con su venta de los dos lados en el hover."""
    t = t[(t["venta"].abs() >= 1) | (t["venta_ap"].abs() >= 1)].copy()
    t = t.loc[t["d"].abs().sort_values(ascending=False, kind="stable").index]
    if len(t) > n + 1:
        _o = t.iloc[n:]
        t = pd.concat([t.head(n), pd.DataFrame([{
            col: f"Otros · {len(_o)}", "venta": _o["venta"].sum(),
            "venta_ap": _o["venta_ap"].sum(), "d": _o["d"].sum()}])],
            ignore_index=True)
    t = t.iloc[::-1]
    _nom = [str(x).title() if str(x).isupper() else str(x) for x in t[col]]
    fig = go.Figure(go.Bar(
        x=t["d"], y=_nom, orientation="h",
        marker=dict(color=[(EXITO if v >= 0 else ERROR) for v in t["d"]]),
        opacity=0.85, text=[_signo_k(v) for v in t["d"]],
        textposition="outside", cliponaxis=False, textfont=dict(size=11),
        customdata=list(zip(t["venta_ap"], t["venta"])),
        hovertemplate=("%{y}<br>Año pasado S/ %{customdata[0]:,.0f} → "
                       "actual S/ %{customdata[1]:,.0f}<br>"
                       "Δ S/ %{x:+,.0f}<extra></extra>")))
    _tope = float(t["d"].abs().max() or 1)
    fig.update_layout(
        height=alturas.por_filas(len(t), px_fila=24, minimo=0,
                                 rol=alturas.COMPACTO, extra=16),
        margin=dict(l=10, r=10, t=4, b=4), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=GRIS_TEXTO, size=12),
        bargap=0.3)
    fig.update_xaxes(visible=False, range=[-_tope * 1.45, _tope * 1.45])
    fig.update_yaxes(showticklabels=True, automargin=True, type="category",
                     tickfont=dict(size=12))
    fig.add_vline(x=0, line=dict(color=GRIS_BORDE, width=1))
    return fig


def _drill_detalle(rk, _res):
    """Lo de abajo de la tarjeta del drill (regla #660): dónde cambió la
    venta —por Grupo y por Canal— y la tabla de productos con el puente
    precio × cantidad de cada uno. Hasta el 2026-10-16 era sólo la tabla:
    «muy pobre para ser una comparación», con razón — decía cuánto cambió
    cada plato, no si fue porque se vendió menos o porque costó distinto."""
    _g, _c = _res.get("grupos"), _res.get("canales")
    _hay_c = _c is not None and len(_c[(_c["venta"].abs() >= 1)
                                       | (_c["venta_ap"].abs() >= 1)]) > 1
    _paneles = [x for x in (("Por grupo", _g, "fam") if _g is not None
                            and len(_g) > 1 else None,
                            ("Por canal", _c, "canal") if _hay_c else None) if x]
    if _paneles:
        # columnas-internas: los dos paneles de la tarjeta del drill, a medias
        # aunque haya uno solo: a todo el ancho, cuatro barras de grupo se
        # leen como un gráfico vacío.
        _cols = st.columns(2, gap="medium")
        for _col, (_tit, _t, _k) in zip(_cols, _paneles):
            with _col:
                st.markdown(f'<div class="vt-drill-tit">{_tit} · Δ S/</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(_fig_delta(_t, _k), use_container_width=True,
                                key=f"ventas_comp_drill_{_k}",
                                config={"displaylogo": False,
                                        "displayModeBar": False})
    _con_pq = "que" in rk.columns
    _cols = {"fam": "Grupo", "prod": "Producto", "que": "Qué cambió",
             "venta_ap": "Venta AP", "venta": "Venta actual", "d": "Δ S/",
             "var": "%Var", "ef_cant": "Por cantidad", "ef_precio": "Por precio",
             "cant_ap": "Cant AP", "cant": "Cant actual",
             "precio_ap": "Precio AP", "precio": "Precio actual"}
    # Qué y cuánto primero; el puente después, y los datos crudos al final.
    _orden = [c for c in ("fam", "prod", "que", "d", "var", "ef_cant",
                          "ef_precio", "venta_ap", "venta", "cant_ap", "cant",
                          "precio_ap", "precio") if c in rk.columns]
    tv = rk[_orden].rename(columns=_cols)
    _es_resto = rk["resto"].to_numpy()

    # El signo y el color salen del monto como se VE: un Δ de céntimos se
    # escribe «S/ 0», sin signo y en gris.
    def _fmt_d(v):
        _r = round(v)
        _s = "+" if _r > 0 else ("−" if _r < 0 else "")
        return f"{_s}S/ {abs(v):,.0f}"

    # Sin vacíos en la tabla (regla #529): ±∞ marca «sin venta el año
    # pasado» y el formateador lo escribe; un precio 0 es «—».
    def _fmt_var(v):
        if v == float("inf"):
            return "nuevo"
        return "—" if v == float("-inf") else _var_txt(v)[0]

    def _fmt_precio(v):
        return "—" if not v else f"S/ {v:,.2f}"

    def _sty_var(v):
        if v == float("inf"):
            return f"color:{EXITO}"
        if v == float("-inf"):
            return f"color:{GRIS_TEXTO}"
        return f"color:{_var_txt(v)[1]}"

    def _sty_d(v):
        _r = round(v)
        return (f"color:{GRIS_TEXTO}" if _r == 0
                else f"color:{EXITO if _r > 0 else ERROR}")

    def _sty_resto(fila):
        _css = (f"color:{GRIS_TEXTO};font-style:italic"
                if _es_resto[fila.name] else "")
        return [_css] * len(fila)

    _fmt = {"Venta AP": "S/ {:,.0f}", "Venta actual": "S/ {:,.0f}",
            "Δ S/": _fmt_d, "%Var": _fmt_var, "Cant AP": "{:,.0f}",
            "Cant actual": "{:,.0f}", "Por cantidad": _fmt_d,
            "Por precio": _fmt_d, "Precio AP": _fmt_precio,
            "Precio actual": _fmt_precio}
    _fmt = {k: v for k, v in _fmt.items() if k in tv.columns}
    _gris = [c for c in ("Venta AP", "Cant AP", "Precio AP") if c in tv.columns]
    sty = (tv.style.format(_fmt)
           .map(_sty_var, subset=["%Var"])
           .map(_sty_d, subset=[c for c in ("Δ S/", "Por cantidad",
                                            "Por precio") if c in tv.columns])
           .set_properties(subset=_gris, color=GRIS_TEXTO)
           .apply(_sty_resto, axis=1))
    st.dataframe(
        sty, use_container_width=True, hide_index=True,
        height=alturas.por_filas(len(tv), px_fila=34, extra=60, minimo=0),
        column_config={
            "Qué cambió": st.column_config.TextColumn(
                help="Lo que más pesó en su diferencia: vendió más o menos "
                     "unidades, o su precio promedio fue más alto o más bajo."),
            "Por cantidad": st.column_config.TextColumn(
                help="Lo que vendió de más o de menos, al precio del año "
                     "pasado."),
            "Por precio": st.column_config.TextColumn(
                help="Lo que puso el precio promedio más alto o más bajo, "
                     "sobre lo vendido hoy. Por cantidad + por precio = Δ S/."),
        })
    _ap_tot = float(rk["venta_ap"].sum())
    _pct_tot = (f" ({_var_txt(_res['d_total'] / _ap_tot * 100)[0]})"
                if _ap_tot else "")
    _n_top = len(rk) - int(bool(_res["n_resto"]))
    _pie = (f"Diferencia del período: {_fmt_d(_res['d_total'])}{_pct_tot}")
    if _con_pq:
        _pie += (f" = {_fmt_d(_res['ef_cant'])} por cantidad y "
                 f"{_fmt_d(_res['ef_precio'])} por precio")
    _pie += ". Ordenados por cuánto pesaron, para arriba o para abajo"
    if _res["n_resto"]:      # nunca 1: ver `_explica_diferencia`
        _pie += (f": estos {_n_top} explican {_fmt_d(_res['d_top'])} y los "
                 f"otros {_res['n_resto']}, "
                 f"{_fmt_d(_res['d_total'] - _res['d_top'])}")
    st.caption(_pie + ".")
