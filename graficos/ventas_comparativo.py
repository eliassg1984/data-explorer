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
    LAVANDA_BORDE,
)
from graficos.base import _card

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

def _serie_por_rangos(archivo, col_parquet, col_fecha, col_venta,
                      rangos, filtrar_cb):
    """{clave: venta} sumando cada `(clave, ini, fin)` de `rangos`, con UNA
    sola carga de R2 que cubre todos. Devuelve {} si no hay datos.

    Se suma por RANGO y no por clave de período justamente para que el
    recorte del período en curso (ver `_rangos_comparables`) funcione: la
    clave del año pasado sigue siendo "agosto", pero sólo se suman sus
    primeros 9 días.

    El acotado por fecha se re-aplica en pandas aunque `cargar_rango` ya
    filtre en DuckDB: en modo demo (sin secrets R2) el loader devuelve el df
    entero sin filtrar —la columna de fecha del demo no se llama igual— y
    sin esta guarda se sumarían filas de fuera de la ventana."""
    ini_g = min(r[1] for r in rangos)
    fin_g = max(r[2] for r in rangos)
    df = cargar_rango(archivo, col_parquet, ini_g, fin_g)
    if df is None or df.empty:
        return {}
    if filtrar_cb is not None:
        df = filtrar_cb(df)
    if df is None or df.empty \
            or col_fecha not in df.columns or col_venta not in df.columns:
        return {}
    _fe = pd.to_datetime(df[col_fecha], errors="coerce").dt.normalize()
    _vt = pd.to_numeric(df[col_venta], errors="coerce")
    base = pd.DataFrame({"f": _fe, "venta": _vt}).dropna(subset=["f", "venta"])
    if base.empty:
        return {}
    fechas = base["f"].dt.date
    out = {}
    for clave, ini, fin in rangos:
        out[clave] = float(base.loc[(fechas >= ini) & (fechas <= fin), "venta"].sum())
    return out


@st.fragment
def _ventas_comparativo(d, col_venta, col_fecha, filtrar_cb=None):
    """Barras agrupadas Año Pasado vs Actual por día, semana o mes."""
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
    serie_act = _serie_por_rangos(_arch, _colp, col_fecha, col_venta,
                                  rangos_act, filtrar_cb)
    serie_ap = _serie_por_rangos(_arch, _colp, col_fecha, col_venta,
                                 rangos_ap, filtrar_cb)

    y_act = [float(serie_act.get(k, 0.0)) for k in claves]
    y_ap = [float(serie_ap.get(k, 0.0)) for k in claves_ap]
    if not any(y_act) and not any(y_ap):
        st.info("Sin datos de venta en la ventana elegida.")
        return
    hay_ap = any(y_ap)

    etiquetas = [_etiqueta_clave(k, grano) for k in claves]
    # Con más de MAX_ETIQUETAS barras, valor + %Var + "en curso" apilados se
    # pisan entre sí (y contra los de la categoría vecina) — mismo umbral
    # que ya usaba el %Var, ahora también gobierna las etiquetas de valor.
    mostrar_etq = len(claves) <= MAX_ETIQUETAS
    _txt_ap = [_fmt_soles_compacto(v) for v in y_ap] if mostrar_etq else None
    _txt_act = [_fmt_soles_compacto(v) for v in y_act] if mostrar_etq else None

    fig = go.Figure()
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
    _tope = max(max(y_act, default=0), max(y_ap, default=0)) or 1
    for i in parciales:
        fig.add_annotation(
            x=i, y=max(y_act[i], y_ap[i]) + _tope * (0.24 if mostrar_etq else 0.04),
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

    if hay_ap and mostrar_etq:
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
        hovermode="x unified",
    )
    fig.update_xaxes(type="category", tickangle=-45, tickfont=dict(size=10),
                     showgrid=False)
    fig.update_yaxes(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE,
                     zeroline=False)

    _sufijo = {"Día": "día a día", "Semana": "semana a semana",
               "Mes": "mes a mes"}[grano]
    titulo = f"Comparativo {_sufijo} vs. año pasado"
    if grano == "Día":
        titulo += (" — alineado por día de semana" if modo == "semana"
                   else " — alineado por fecha calendario")

    with _card("ventas_comparativo", titulo, titulo_arriba=True):
        st.plotly_chart(fig, use_container_width=True, key="ventas_g_comparativo")
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
        _plural = {"Día": "días", "Semana": "semanas", "Mes": "meses"}[grano]
        st.caption(f"Ventana: {ventana} {_plural} hasta {ancla:%d/%m/%Y}. "
                   + _expl + _cal_txt + _lbl)
