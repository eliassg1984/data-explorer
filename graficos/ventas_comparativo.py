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

En SEMANA y MES la pregunta se disuelve sola: una semana completa siempre
trae un lunes, un viernes y un sábado, y un mes también — el ruido de
día-de-semana se cancela al sumar. La semana se compara contra la de 364
días antes y el mes contra el mismo mes.

364 DÍAS Y NO «LA MISMA SEMANA ISO» (regla #614): hasta el 2026-10-05 el
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
from data import REPORTES, cargar_rango
from tema import (
    ACENTO, ADVERTENCIA_TEXTO, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO,
    LAVANDA_BORDE, PALETA_SERIES,
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
_DIAS_ES = tuple(_d.capitalize() for _d in cortes.DIAS_ABR_ES)
_FERIADOS_FIJOS_PE = cortes.FERIADOS_FIJOS_PE
_pascua = cortes.pascua
_feriados_peru = cortes.feriados_peru
_feriados_entre = cortes.feriados_entre

_MESES_ES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")

_UN_ANO_DE_SEMANAS = _dt.timedelta(days=364)
"""El «mismo día de semana del año pasado»: 52 semanas justas (regla #614)."""


def _fecha_equivalente(f, modo):
    """Fecha del año pasado equivalente a `f` (un `date`). Sólo aplica a
    granularidad día — semana y mes se alinean por su propia clave.

    modo="calendario": mismo día/mes del año anterior. El 29 de febrero no
        existe en un año no bisiesto → cae al 28.
    modo="semana": 364 días antes, el mismo día de la semana. Es la cuenta
        de `ventas_mix.rango_ano_pasado` y `ventas_horario._ano_pasado`, y
        `test_graficos.py` vigila que sigan siendo la misma (regla #614).
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
    (regla #614). Mes: el mismo mes un año antes."""
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
    regla #614), y un hover que dice «S19» sobre la barra «S18» se lee
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
    """({clave: venta}, {clave: pax}, {clave: venta del ticket}, total) para
    cada `(clave, ini, fin)` de `rangos`, con UNA sola carga de R2 que los
    cubre a todos. La venta del ticket es la de los canales que registran
    clientes (`definicion_venta.con_clientes`, regla #591): sin Rappi.

    `total` es el de la VENTANA entera (regla #614): `{"venta", "pax",
    "cli"}`, con `pax`/`cli` en None si no hay clientes. Se cuenta sobre la
    UNIÓN de los rangos y no sumando las barras: en «Misma fecha» el 28 y el
    29 de febrero de un bisiesto caen los dos en el 28 del año anterior, y
    un pedido cuya cuenta se partió entre dos días es un solo pedido.

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
    for clave, ini, fin in rangos:
        m = (fechas >= ini) & (fechas <= fin)
        en_ventana |= m
        ventas[clave] = float(base.loc[m, "venta"].sum())
        if hay_pax:
            ventas_cli[clave] = float(base.loc[m & base["cli"], "venta"].sum())
            paxes[clave] = _pax(m)
    total = {
        "venta": float(base.loc[en_ventana, "venta"].sum()),
        "pax": _pax(en_ventana) if hay_pax else None,
        "cli": (float(base.loc[en_ventana & base["cli"], "venta"].sum())
                if hay_pax else None),
    }
    return ventas, paxes, ventas_cli, total


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


def _explica_diferencia(t, top=15):
    """Qué productos explican la diferencia de UN período contra el año
    pasado: los `top` que más pesaron, de mayor a menor |Δ S/|, y los demás
    juntos en una fila «Resto» (regla #614).

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

    return _explica_diferencia(t, top=top)


def _titulo_comparativo(grano, modo, es_desc):
    """Título de la cabecera. Función y no inline porque se pinta DOS veces:
    una provisional apenas se conocen los controles (para que la cabecera no
    aparezca vacía mientras se cargan los datos) y otra al final con el valor
    real de `vista`. Ver arquitectura.md regla #108."""
    _sufijo = {"Día": "día a día", "Semana": "semana a semana",
               "Mes": "mes a mes"}[grano]
    if es_desc:
        return f"¿Por qué cambió la venta? — {_sufijo} vs. año pasado"
    titulo = f"Comparativo {_sufijo} vs. año pasado"
    if grano == "Día":
        titulo += (" — alineado por día de semana" if modo == "semana"
                   else " — alineado por fecha calendario")
    return titulo



def _html_totales(tot_act, tot_ap, es_desc, tramo_act, tramo_ap):
    """La fila del TOTAL DE LA VENTANA (regla #614), con el dibujo de los KPI
    de Ventas (`.vt-kpis`, `estilos/_80_cards.py`).

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
    texto de los días sumados, para el tooltip."""
    def _k(rot, val, sub="", color_val=None, color_sub=None, muestra=None,
           tip=""):
        _st = f' style="--vt-kpi-color:{muestra}"' if muestra else ""
        _cv = f' style="color:{color_val}"' if color_val else ""
        _cs = f' style="color:{color_sub}"' if color_sub else ""
        _sub = (f'<span class="vt-kpi-sub"{_cs}>{escape(sub)}</span>'
                if sub else "")
        return (f'<div class="vt-kpi"{_st} title="{escape(tip or rot)}">'
                f'<span class="vt-kpi-rot">{escape(rot)}</span>'
                f'<span class="vt-kpi-val"{_cv}>{escape(val)}{_sub}</span>'
                '</div>')

    act = tot_act or {}
    ap = tot_ap or {}
    v_act, v_ap = act.get("venta") or 0.0, ap.get("venta") or 0.0
    partes = []
    if v_ap:
        partes.append(_k("Año pasado", fmt_k(v_ap),
                         muestra=None if es_desc else LAVANDA_BORDE,
                         tip=f"Año pasado: S/ {v_ap:,.2f} · {tramo_ap}"))
    partes.append(_k("Actual", fmt_k(v_act),
                     muestra=None if es_desc else ACENTO,
                     tip=f"Actual: S/ {v_act:,.2f} · {tramo_act}"))
    if v_ap:
        _d = v_act - v_ap
        _txt, _col = _var_txt(_d / v_ap * 100)
        _signo = "+" if _d > 0 else ("−" if _d < 0 else "")
        partes.append(_k(
            "Diferencia", _txt, f"{_signo}{fmt_k(abs(_d))}", color_val=_col,
            tip=(f"Actual contra el año pasado, los mismos días: "
                 f"{_signo}S/ {abs(_d):,.2f} ({_txt})")))
    p_act, p_ap = act.get("pax"), ap.get("pax")
    if p_act:
        _sub, _col = (_var_txt((p_act / p_ap - 1) * 100) if p_ap
                      else ("", None))
        partes.append(_k(
            "Clientes", f"{p_act:,.0f}", _sub, color_sub=_col,
            muestra=PALETA_SERIES[1] if es_desc else None,
            tip=(f"Clientes (adultos): {p_act:,.0f}"
                 + (f" contra {p_ap:,.0f} el año pasado" if p_ap else ""))))
        t_act = (act.get("cli") or 0.0) / p_act
        t_ap = (ap.get("cli") or 0.0) / p_ap if p_ap else None
        _sub, _col = (_var_txt((t_act / t_ap - 1) * 100) if t_ap
                      else ("", None))
        partes.append(_k(
            "Ticket", f"S/ {t_act:,.2f}", _sub, color_sub=_col,
            muestra=PALETA_SERIES[2] if es_desc else None,
            tip=("Ticket: venta de los canales que registran clientes ÷ "
                 f"clientes (sin Rappi). S/ {t_act:,.2f}"
                 + (f" contra S/ {t_ap:,.2f} el año pasado" if t_ap else ""))))
    return '<div class="vt-kpis">' + "".join(partes) + "</div>"


@st.fragment
def _ventas_comparativo(d, col_venta, col_fecha, col_pax=None, col_pedido=None,
                        col_prod=None, col_cant=None, col_fam=None,
                        col_sub=None, filtrar_cb=None):
    """Comparativo Año Pasado vs Actual por día, semana o mes — en montos o
    descompuesto en pax × ticket, con el total de la ventana arriba y, al
    clickear un período, qué productos explican su diferencia (#614)."""
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
        # #614). Hasta el 2026-10-05 eran `st.columns([1.3, 1.6, 2.1, 0.5,
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
            st.session_state.get("ventas_comp_vista") == "Descomposición"))
        # Línea INFERIOR de la franja de controles. Los -18px + width:calc(100% + 36px)
        # compensan el padding horizontal de la tarjeta para que toque el
        # borde real, igual que en Por día (arquitectura.md #104).
        st.markdown(
            f'<hr style="border:none;border-top:2px solid {GRIS_BORDE};'
            'margin:-6px -18px 12px;width:calc(100% + 36px);">',
            unsafe_allow_html=True)
        # El TOTAL DE LA VENTANA (regla #614): se reserva acá —entre la franja
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
    serie_act, pax_act_d, cli_act_d, tot_act = _series_por_rangos(
        _arch, _colp, col_fecha, col_venta, col_pax, col_pedido,
        rangos_act, filtrar_cb)
    serie_ap, pax_ap_d, cli_ap_d, tot_ap = _series_por_rangos(
        _arch, _colp, col_fecha, col_venta, col_pax, col_pedido,
        rangos_ap, filtrar_cb)

    y_act = [float(serie_act.get(k, 0.0)) for k in claves]
    y_ap = [float(serie_ap.get(k, 0.0)) for k in claves_ap]
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
    p_ap = [float(pax_ap_d.get(k, 0.0)) for k in claves_ap]
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
    _txt_ap = [_fmt_soles_compacto(v) for v in y_ap] if mostrar_etq else None
    _txt_act = [_fmt_soles_compacto(v) for v in y_act] if mostrar_etq else None

    es_desc = vista == "Descomposición"

    # El total de la ventana, en el hueco que dejó la franja (regla #614).
    def _tramo(rangos):
        return f"{rangos[0][1]:%d/%m/%Y} al {rangos[-1][2]:%d/%m/%Y}"
    _ph_tot.markdown(
        _html_totales(tot_act, tot_ap if hay_ap else None, es_desc,
                      _tramo(rangos_act), _tramo(rangos_ap)),
        unsafe_allow_html=True)

    d_venta = [_pct(a, b) for a, b in zip(y_act, y_ap)]
    d_pax = [_pct(a, b) for a, b in zip(p_act, p_ap)]
    # Ticket = venta de los canales con clientes ÷ pax (regla #591): la de
    # Rappi, que no carga pax, queda afuera. Si falta cualquiera de los dos
    # lados, el ticket de ese período no existe (None) y la línea corta ahí
    # en vez de inventar.
    c_act = [float(cli_act_d.get(k, 0.0)) for k in claves]
    c_ap = [float(cli_ap_d.get(k, 0.0)) for k in claves_ap]
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
    # Sin legend nativo desde el 2026-10-05 (regla #614): la leyenda es la
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
                font=dict(size=10, color=ADVERTENCIA_TEXTO))

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
        # (y=1.0 paper): el legend se fue a la fila del total (#614) y las
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
        # Rango FIJO en Montos (regla #614): las etiquetas de valor, el %Var
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

    titulo = _titulo_comparativo(grano, modo, es_desc)

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
            _expl = (
                "Cada semana se compara contra la de 52 semanas antes. A esta "
                "escala el día de semana ya no importa: una semana completa "
                "trae todos los días, así que ese ruido se cancela solo."
                if grano == "Semana" else
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
    # Hasta el 2026-10-05 era el top 15 por venta ACTUAL (regla #614).
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
            rk = _ranking_platos(_arch, _colp, col_fecha, col_venta, col_prod,
                                 col_cant, _r_act, _r_ap, filtrar_cb,
                                 col_fam=col_fam, col_sub=col_sub)
            if rk is None or rk[0].empty:
                st.info("Sin ventas de productos en ese período.")
            else:
                rk, _res = rk
                # Jerarquía primero (Grupo → Sub Grupo → Producto, el orden
                # de la carta), después la plata —con el Δ, que es lo que
                # ordena— y las cantidades al final: son la lectura de apoyo.
                _cols = {"fam": "Grupo", "sub": "Sub Grupo", "prod": "Producto",
                         "venta_ap": "Venta AP", "venta": "Venta actual",
                         "d": "Δ S/", "var": "%Var", "cant_ap": "Cant AP",
                         "cant": "Cant actual"}
                _orden = [c for c in ("fam", "sub", "prod", "venta_ap",
                                      "venta", "d", "var", "cant_ap", "cant")
                          if c in rk.columns]
                tv = rk[_orden].rename(columns=_cols)
                _es_resto = rk["resto"].to_numpy()

                # El signo y el color salen del monto como se VE: un Δ de
                # céntimos se escribe «S/ 0», sin signo y en gris.
                def _fmt_d(v):
                    _r = round(v)
                    _s = "+" if _r > 0 else ("−" if _r < 0 else "")
                    return f"{_s}S/ {abs(v):,.0f}"

                # Sin vacíos en la tabla (regla #529): ±∞ marca «sin venta el
                # año pasado» y el formateador lo escribe.
                def _fmt_var(v):
                    if v == float("inf"):
                        return "nuevo"
                    return "—" if v == float("-inf") else _var_txt(v)[0]

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
                        "Cant actual": "{:,.0f}"}
                _fmt = {k: v for k, v in _fmt.items() if k in tv.columns}
                _gris = [c for c in ("Venta AP", "Cant AP") if c in tv.columns]
                sty = (tv.style.format(_fmt)
                       .map(_sty_var, subset=["%Var"])
                       .map(_sty_d, subset=["Δ S/"])
                       .set_properties(subset=_gris, color=GRIS_TEXTO)
                       .apply(_sty_resto, axis=1))
                st.dataframe(sty, use_container_width=True, hide_index=True,
                             height=alturas.por_filas(len(tv), px_fila=34,
                                                      extra=60, minimo=0))
                _ap_tot = float(rk["venta_ap"].sum())
                _pct_tot = (f" ({_var_txt(_res['d_total'] / _ap_tot * 100)[0]})"
                            if _ap_tot else "")
                _n_top = len(rk) - int(bool(_res["n_resto"]))
                _pie = (f"Diferencia del período: {_fmt_d(_res['d_total'])}"
                        f"{_pct_tot}. Ordenados por cuánto pesaron, para "
                        "arriba o para abajo")
                if _res["n_resto"]:      # nunca 1: ver `_explica_diferencia`
                    _pie += (f": estos {_n_top} explican "
                             f"{_fmt_d(_res['d_top'])} y los otros "
                             f"{_res['n_resto']}, "
                             f"{_fmt_d(_res['d_total'] - _res['d_top'])}")
                st.caption(_pie + ". «nuevo» en %Var: no se vendió en esos "
                           "días del año pasado.")
