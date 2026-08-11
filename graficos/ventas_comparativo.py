"""
graficos.ventas_comparativo — vista "Año Pasado" del dashboard de Ventas:
barras agrupadas día a día (Año Pasado vs Actual) con %Var por día, y el
calendario marcado encima (inicio de semana, fin de semana, feriados).

DOS MODOS DE ALINEACIÓN, y la diferencia importa (por eso es un toggle
visible, no una decisión escondida en el código):

  · "Misma fecha"     05/08/2026 ↔ 05/08/2025. Las fechas coinciden, los
                      días de semana NO — podés terminar comparando un
                      miércoles contra un martes. Es lo que hace un
                      comparativo de calendario clásico.
  · "Mismo día"       miércoles de la semana ISO 32 de 2026 ↔ miércoles de
                      la semana ISO 32 de 2025. El día de semana coincide
                      siempre; la fecha se corre ±3 días. En un restaurante
                      —donde viernes y sábado mandan— esta es la que no
                      miente.

El dato del año pasado NO sale del `d` que ya está en memoria: `d` viene
filtrado por el rango de la franja (Ventas usa `carga_por_rango`, ver
data.py::REPORTES), así que el año pasado directamente no está ahí salvo
que el usuario ensanche el rango a mano. Se trae con `data.cargar_rango()`
—una consulta acotada a las ~2 semanas equivalentes, no el parquet
entero— y se le aplican LOS MISMOS chips que a la vista actual vía
`filtrar_cb`: sin eso, filtrar por Grupo daría barras actuales filtradas
contra barras de año pasado SIN filtrar, o sea dos números que no se
pueden comparar (misma clase de bug que la regla #58 / publicar_contexto_ia).
"""

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

VENTANAS = (7, 14, 30)
VENTANA_DEF = 14
MAX_ETIQUETAS = 14   # con más días, el %Var por barra se pisa: queda en el hover

_DIAS_ES = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")

# Feriados nacionales de Perú de fecha FIJA (mes, día). No incluye los
# movibles (Jueves/Viernes Santo), que dependen de Pascua y se calculan
# aparte en _feriados_peru.
#
# OJO: es el calendario NACIONAL. No sabe de cierres propios del local,
# aniversarios ni feriados regionales — si algún día hacen falta, esto
# tiene que pasar a ser un dato mantenido por el negocio, no una constante.
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
    Se necesita para Jueves y Viernes Santo, los dos únicos feriados
    peruanos que se mueven de fecha cada año."""
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


def _fecha_equivalente(f, modo):
    """Fecha del año pasado equivalente a `f` (un `date`).

    modo="calendario": mismo día/mes del año anterior. El 29 de febrero no
        existe en un año no bisiesto → cae al 28.
    modo="semana": misma semana ISO y mismo día de semana del año ISO
        anterior — la fecha se corre unos días pero el día de semana
        coincide. Si el año ISO anterior no tiene semana 53 (la mayoría no
        la tiene), cae a la 52.
    """
    if modo == "calendario":
        try:
            return f.replace(year=f.year - 1)
        except ValueError:      # 29-feb → año anterior no bisiesto
            return f.replace(year=f.year - 1, day=28)
    anio_iso, semana, dia_sem = f.isocalendar()[0], f.isocalendar()[1], f.isocalendar()[2]
    try:
        return _dt.date.fromisocalendar(anio_iso - 1, semana, dia_sem)
    except ValueError:          # el año ISO anterior no llega a la semana 53
        return _dt.date.fromisocalendar(anio_iso - 1, 52, dia_sem)


def _etiqueta_dia(f):
    """'Mié 05/08' — día de semana + fecha. El día de semana va SIEMPRE,
    en los dos modos: en "misma fecha" es justo lo que deja ver que estás
    comparando días de semana distintos."""
    return f"{_DIAS_ES[f.weekday()]} {f:%d/%m}"


# ── Vista ────────────────────────────────────────────────────────────────────

@st.fragment
def _ventas_comparativo(d, col_venta, col_fecha, filtrar_cb=None):
    """Barras agrupadas Año Pasado vs Actual, día a día, sobre los últimos
    N días con ventas del rango cargado."""
    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el comparativo.")
        return

    _fe = pd.to_datetime(d[col_fecha], errors="coerce").dt.normalize()
    _vt = pd.to_numeric(d[col_venta], errors="coerce")
    act = (pd.DataFrame({"dia": _fe, "venta": _vt}).dropna(subset=["dia", "venta"])
           .groupby("dia", as_index=False)["venta"].sum())
    if act.empty:
        st.info("Sin datos en el rango cargado.")
        return

    c1, c2, _ = st.columns([2.2, 1.4, 2])
    with c1:
        modo_lbl = st.pills(
            "Alinear por", ["Mismo día de semana", "Misma fecha"],
            default="Mismo día de semana", key="ventas_comp_modo",
            label_visibility="collapsed",
        ) or "Mismo día de semana"
    with c2:
        ventana = st.pills(
            "Días", list(VENTANAS), default=VENTANA_DEF,
            key="ventas_comp_ventana", format_func=lambda v: f"{v} días",
            label_visibility="collapsed",
        ) or VENTANA_DEF
    modo = "semana" if modo_lbl.startswith("Mismo día") else "calendario"

    act = act.sort_values("dia").tail(ventana).reset_index(drop=True)
    dias_act = [f.date() for f in act["dia"]]
    dias_ap = [_fecha_equivalente(f, modo) for f in dias_act]

    # ── Año pasado: consulta propia acotada al tramo equivalente ─────────
    cfg = REPORTES.get("Ventas", {})
    df_ap = cargar_rango(cfg.get("archivo", "ventas.parquet"),
                         cfg.get("carga_por_rango", "FEC REG DOCUMENTO"),
                         min(dias_ap), max(dias_ap))
    serie_ap = {}
    if df_ap is not None and not df_ap.empty:
        if filtrar_cb is not None:
            df_ap = filtrar_cb(df_ap)
        if df_ap is not None and not df_ap.empty \
                and col_fecha in df_ap.columns and col_venta in df_ap.columns:
            _fa = pd.to_datetime(df_ap[col_fecha], errors="coerce").dt.normalize()
            _va = pd.to_numeric(df_ap[col_venta], errors="coerce")
            _g = (pd.DataFrame({"dia": _fa, "venta": _va})
                  .dropna(subset=["dia", "venta"])
                  .groupby("dia", as_index=False)["venta"].sum())
            serie_ap = {f.date(): v for f, v in zip(_g["dia"], _g["venta"])}

    y_ap = [float(serie_ap.get(f, 0.0)) for f in dias_ap]
    y_act = [float(v) for v in act["venta"]]
    hay_ap = any(v > 0 for v in y_ap)

    etiquetas = [_etiqueta_dia(f) for f in dias_act]
    feriados = set()
    for _a in {f.year for f in dias_act} | {f.year for f in dias_ap}:
        feriados |= _feriados_peru(_a)

    # ── Figura ───────────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_bar(
        x=etiquetas, y=y_ap, name="Año pasado",
        marker=dict(color=LAVANDA_BORDE),
        customdata=[f"{f:%d/%m/%Y}" for f in dias_ap],
        hovertemplate="Año pasado · %{customdata}<br>S/ %{y:,.0f}<extra></extra>",
    )
    fig.add_bar(
        x=etiquetas, y=y_act, name="Actual",
        marker=dict(color=ACENTO),
        customdata=[f"{f:%d/%m/%Y}" for f in dias_act],
        hovertemplate="Actual · %{customdata}<br>S/ %{y:,.0f}<extra></extra>",
    )

    # Bandas de calendario: fin de semana (gris) y feriado (ámbar). Eje
    # CATEGÓRICO (una categoría por día), así que la banda de la categoría i
    # va de i-0.5 a i+0.5 — con eje de fechas habría que andar sumando
    # medias jornadas y las dos barras del par no quedarían centradas.
    # Un día se marca feriado si lo es ESTE año o si lo era el día contra el
    # que se lo compara — las dos cosas explican una barra fuera de lo normal,
    # pero explican barras DISTINTAS (la morada o la lavanda), así que la
    # etiqueta lo dice: "feriado" vs "feriado AP". Sin esa distinción, un
    # sábado común marcado en ámbar porque SU equivalente de 2025 fue feriado
    # se lee como si el feriado fuera hoy.
    for i, f in enumerate(dias_act):
        fer_act = f in feriados
        fer_ap = dias_ap[i] in feriados
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
                font=dict(size=8, color=ADVERTENCIA_TEXTO),
            )
    # Inicio de semana: línea punteada ANTES de cada lunes (igual que la
    # tendencia diaria del resumen). Se salta el lunes del borde izquierdo.
    for i, f in enumerate(dias_act):
        if f.weekday() == 0 and i > 0:
            fig.add_shape(
                type="line", xref="x", yref="paper",
                x0=i - 0.5, x1=i - 0.5, y0=0, y1=1,
                line=dict(color=GRIS_BORDE, width=1, dash="dot"), layer="below",
            )

    # %Var por día, arriba del par. Solo si entran sin pisarse; con ventanas
    # largas el dato sigue disponible en el hover (y se avisa en el caption).
    if hay_ap and len(dias_act) <= MAX_ETIQUETAS:
        _tope = max(max(y_act, default=0), max(y_ap, default=0)) or 1
        for i, (a, b) in enumerate(zip(y_act, y_ap)):
            if not b:
                continue
            var = (a - b) / b * 100
            fig.add_annotation(
                x=i, y=max(a, b) + _tope * 0.04, showarrow=False,
                text=f"{var:+.0f}%", font=dict(
                    size=9, color=(EXITO if var >= 0 else ERROR)),
            )

    fig.update_layout(
        barmode="group", bargap=0.28, bargroupgap=0.08,
        height=340, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=GRIS_TEXTO, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(type="category", tickangle=-45, tickfont=dict(size=10),
                     showgrid=False)
    fig.update_yaxes(tickprefix="S/ ", tickformat=",.0f", gridcolor=GRIS_BORDE,
                     zeroline=False)

    titulo = ("Día a día vs. año pasado — alineado por día de semana"
              if modo == "semana" else
              "Día a día vs. año pasado — alineado por fecha calendario")
    with _card("ventas_comparativo", titulo, titulo_arriba=True):
        st.plotly_chart(fig, use_container_width=True, key="ventas_g_comparativo")
        if not hay_ap:
            st.caption(
                "No hay ventas registradas en el tramo equivalente del año "
                "pasado — solo se muestran las barras del período actual.")
        _expl = ("Cada día se compara contra el MISMO día de semana del año "
                 "pasado (misma semana ISO): la fecha se corre unos días, "
                 "pero un sábado se compara contra un sábado."
                 if modo == "semana" else
                 "Cada día se compara contra la misma fecha del año pasado. "
                 "Ojo: el día de semana no coincide — un miércoles puede "
                 "quedar comparado contra un martes.")
        _lbl = ("" if not hay_ap or len(dias_act) <= MAX_ETIQUETAS else
                f" Con más de {MAX_ETIQUETAS} días el %Var no se dibuja "
                "sobre las barras (se pisaría); está en el hover.")
        st.caption(
            _expl + " Banda gris = fin de semana · banda ámbar = feriado "
            "nacional (Perú); «feriado AP» marca el caso en que el feriado "
            "cae del lado del año pasado, no de este." + _lbl)
