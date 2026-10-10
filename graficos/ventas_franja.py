"""
graficos.ventas_franja — el modo «A medida» de Ventas › Análisis por Hora
(2026-10-10, regla #627): el interruptor «Mapa | A medida» del renglón del
título de esa tarjeta alterna el mapa de calor y esto.

Responde la pregunta que llega suelta y nunca con la misma forma: «cuánto se
vendió por Rappi los últimos 4 domingos de 5:30 pm a 11:30 pm», «los
viernes y sábados de agosto en el almuerzo», «del 3 al 9 de setiembre de 8
a 10 de la noche». Tres preguntas y un mismo formulario:

    QUÉ DÍAS     un rango de fechas y, adentro, los días de la semana que
                 entran — o los días SUELTOS que se marquen uno por uno
    QUÉ HORARIO  desde / hasta, por media hora; si «hasta» es antes que
                 «desde», cruza la medianoche
    QUÉ VENTA    el canal y el ámbito (toda la carta, un grupo o un
                 subgrupo); los Filtros de la franja aplican además

y la respuesta: el TOTAL arriba, una fila por día elegido —también los que
no vendieron, que son parte de la respuesta— y una por plato.

Por qué es un MODO y no más controles del mapa: el mapa compara PERÍODOS
dibujando rectángulos (hasta cuatro, de horas enteras); esto es un filtro
con un total, sin tope de días y con minutos. Estirar el mapa para esto lo
complicaba sin quitarle ninguno de los dos topes. Nació como vista propia
y el mismo día pasó a ser un modo de la tarjeta, a pedido: las dos
responden «cuándo se vende», como el Ranking y la Ingeniería de menú
comparten la de «Análisis de platos» (regla #569). El código sigue aparte:
`ventas_horario` sólo llama a `cuerpo`.

TRES COSAS QUE NO SON OBVIAS:

  · LA HORA ES LA DEL PEDIDO (`FECHA REGISTRO PEDIDO`), cuando se abrió la
    mesa o entró el pedido de Rappi, como el default de «Por hora» (regla
    #530): la del cobro llega 1 h 38 min después. Y se CARGA por esa misma
    fecha (regla #552): cargado por el cobro, un pedido del último día
    cobrado pasada la medianoche no entraría.
  · UN HORARIO QUE CRUZA LA MEDIANOCHE ES DEL DÍA EN QUE EMPEZÓ: con
    «20:00 → 01:00», el pedido del domingo a las 00:30 es de la noche del
    SÁBADO, como lo cierra la caja. Por eso se carga un día de más.
  · «HASTA» NO SE INCLUYE: «17:30 → 22:00» es de 17:30 a 21:59, para que
    dos horarios seguidos («→ 22:00» y «22:00 →») no cuenten dos veces el
    pedido de las 22:00.

Los combos cuentan como UNA unidad (la línea del combo): los platos que van
adentro no están en `ventas.parquet` (pendiente).
"""

import datetime as _dt
from html import escape

import pandas as pd
import streamlit as st

import cortes
from data import REPORTES, cargar_rango, rango_fechas
from estado_rango import atajos_tarjeta
from graficos import alturas
from graficos.base import (_resolver, ctx_rango_propio, rango_tarjeta,
                           selector_fecha_tarjeta)
from graficos.ventas_platos import TODA_LA_CARTA, opciones_ambito
from tema import GRIS_TEXTO_SUAVE

CATEGORIA = "vt_franja"
"""La clave del rango PROPIO de la tarjeta (`ctx_rango_propio`, regla
#531): mover su fecha no toca la de la franja ni recarga el reporte."""

MODOS = ("Días de la semana", "Días sueltos")
DIAS = tuple(d.capitalize() for d in cortes.DIAS_ABR_ES)
"""Lun … Dom, en el orden de `date.weekday()`."""
HORAS = tuple(f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30))
HORAS_HASTA = HORAS[1:] + ("24:00",)
AGRUPAR = ("Plato", "Subgrupo", "Grupo")

_KEYS_WIDGET = ("vt_frj_modo", "vt_frj_dias", "vt_frj_sueltos", "vt_frj_desde",
         "vt_frj_hasta", "vt_frj_canal", "vt_frj_amb", "vt_frj_agrupar")
"""Los controles de este modo, para que el mapa los conserve mientras está
en pantalla (`base.preservar_widgets`): un widget que no se dibuja en una
corrida pierde su valor."""


# ===========================================================================
# LAS CUENTAS (puras: las prueba test_graficos.py)
# ===========================================================================

def a_minutos(hhmm):
    """«17:30» → 1050. «24:00» → 1440 (el fin del día, sólo como «hasta»)."""
    h, m = str(hhmm).split(":")
    return int(h) * 60 + int(m)


def cruza_medianoche(desde, hasta):
    """¿El horario sigue al día siguiente? («20:00 → 01:00»)."""
    return hasta <= desde


def dias_elegidos(ini, fin, dias_semana):
    """Las fechas de `ini` a `fin` (inclusive) cuyo día de la semana
    (0 = lunes) está en `dias_semana`, en orden."""
    if ini is None or fin is None or ini > fin:
        return []
    quiero = set(dias_semana)
    return [d.date() for d in pd.date_range(ini, fin)
            if d.weekday() in quiero]


def en_horario(ts, desde, hasta):
    """`(dentro, dia)` de una Series de fecha-hora contra el horario
    `desde`–`hasta` (minutos; `hasta` no se incluye).

    `dia` es el día al que PERTENECE cada fila: el de su fecha, salvo en un
    horario que cruza la medianoche, donde lo de después de las 00:00 es del
    día anterior. Sin hora (NaT), afuera."""
    t = pd.to_datetime(ts, errors="coerce")
    minuto = t.dt.hour * 60 + t.dt.minute
    dia = t.dt.normalize()
    if cruza_medianoche(desde, hasta):
        madrugada = minuto < hasta
        dentro = (minuto >= desde) | madrugada
        dia = dia.where(~madrugada, dia - pd.Timedelta(days=1))
    else:
        dentro = (minuto >= desde) & (minuto < hasta)
    return (dentro & t.notna()).fillna(False).astype(bool), dia


def por_dia(b, dias):
    """Una fila por día ELEGIDO, también los que no vendieron: «4 domingos»
    con uno en cero es parte de la respuesta. `b` trae `dia`, `venta`,
    `cant` y `pedido`."""
    idx = pd.DatetimeIndex(pd.to_datetime(list(dias)), name="dia")
    if b is None or b.empty:
        return pd.DataFrame({"venta": 0.0, "cant": 0.0, "pedidos": 0},
                            index=idx)
    a = b.groupby("dia")[["venta", "cant"]].sum()
    a["pedidos"] = b.groupby("dia")["pedido"].nunique()
    return a.reindex(idx).fillna(0)


def por_grupo(b, nivel):
    """Venta y unidades por plato, subgrupo o grupo (`nivel` ∈ AGRUPAR), de
    la que más vende a la que menos. Agrupa por columnas de verdad y
    renombra por nombre (regla #481)."""
    claves = {"Plato": ["grupo", "sub", "prod"], "Subgrupo": ["grupo", "sub"],
              "Grupo": ["grupo"]}[nivel]
    if b is None or b.empty:
        return pd.DataFrame(columns=claves + ["cant", "venta"])
    a = (b.groupby(claves, as_index=False)[["cant", "venta"]].sum()
         .sort_values("venta", ascending=False, kind="stable"))
    return a.reset_index(drop=True)


# ===========================================================================
# LOS DATOS
# ===========================================================================

def _columnas(df):
    return {
        "hora": _resolver(df, ["Fecha Registro Pedido"]),
        "cobro": _resolver(df, ["Fec Reg Documento", "Fecha Registro"]),
        "grupo": _resolver(df, ["Grupo"]),
        "sub": _resolver(df, ["Sub Grupo", "Sub_Grupo", "Subgrupo"]),
        "prod": _resolver(df, ["Nomb Item Venta", "Nombre Producto",
                               "Producto"]),
        "venta": _resolver(df, ["Venta Item Ddocumento", "Venta"]),
        "cant": _resolver(df, ["Cantidad Item Ddocumento", "Cantidad"]),
        "pedido": _resolver(df, ["Llave Local Pedido", "Codigo Pedido "
                                 "Ddocumento", "Nro Pedido"]),
        "canal": _resolver(df, ["Canal Venta", "Canal_Venta", "Canal"]),
    }


def _base(df, cols, col_hora):
    """Una fila por ítem con nombres FIJOS."""
    def _num(c):
        if not c or c not in df.columns:
            return pd.Series(0.0, index=df.index)
        return pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    def _txt(c, vacio):
        if not c or c not in df.columns:
            return pd.Series(vacio, index=df.index)
        s = df[c].astype("object")
        s = s.where(s.notna(), vacio).astype(str).str.strip()
        return s.where(s != "", vacio)

    return pd.DataFrame({
        "ts": pd.to_datetime(df[col_hora], errors="coerce"),
        "grupo": _txt(cols["grupo"], "(sin grupo)"),
        "sub": _txt(cols["sub"], "(sin subgrupo)"),
        "prod": _txt(cols["prod"], "(sin nombre)"),
        "canal": _txt(cols["canal"], "(sin canal)"),
        "pedido": _txt(cols["pedido"], ""),
        "venta": _num(cols["venta"]),
        "cant": _num(cols["cant"]),
    })


def _cargar(ini, fin, cruza, filtrar_cb, d_demo):
    """El tramo de R2 por la fecha del PEDIDO (regla #552), con un día de
    más si el horario cruza la medianoche, y filtrado como el resto de
    Ventas (`filtrar_cb`: los chips, un ítem una vez y sólo venta)."""
    cfg = REPORTES.get("Ventas", {})
    archivo = cfg.get("archivo", "ventas.parquet")
    cols_d = _columnas(d_demo) if d_demo is not None else {}
    col_carga = cols_d.get("hora") or cfg.get("carga_por_rango",
                                              "FEC REG DOCUMENTO")
    fin_carga = fin + _dt.timedelta(days=1) if cruza else fin
    df = cargar_rango(archivo, col_carga, ini, fin_carga)
    if df is None or df.empty:
        df = d_demo     # modo demo: el loader no trae nada
    elif filtrar_cb is not None:
        df = filtrar_cb(df)
    return df


# ===========================================================================
# LA VISTA
# ===========================================================================

def _fecha_corta(d):
    return (f"{DIAS[d.weekday()].lower()} {d.day} "
            f"{cortes.MESES_ABR_ES[d.month - 1].lower()}")


def _lista_dias(dias, tope=6):
    """«13 set, 20 set, 27 set y 4 oct», o los primeros y «… (+N)»."""
    txt = [f"{d.day} {cortes.MESES_ABR_ES[d.month - 1].lower()}" for d in dias]
    if len(txt) > tope:
        return ", ".join(txt[:tope]) + f" … (+{len(txt) - tope})"
    return ", ".join(txt[:-1]) + (" y " if len(txt) > 1 else "") + txt[-1]


def _que_dias(dias, modo, dias_semana):
    """«4 domingos», «12 viernes y sábados», «3 días»."""
    n = len(dias)
    if modo == MODOS[0] and len(dias_semana) == 1:
        nombre = cortes.DIAS_ABR_ES[dias_semana[0]]
        largo = {"lun": "lunes", "mar": "martes", "mié": "miércoles",
                 "jue": "jueves", "vie": "viernes", "sáb": "sábado",
                 "dom": "domingo"}.get(nombre.lower(), nombre)
        if n != 1 and not largo.endswith("s"):
            largo += "s"
        return f"{n} {largo}"
    return f"{n} día" + ("" if n == 1 else "s")


def _html_cab(tit, kpis):
    def _k(rot, val, clase="", tip=""):
        return (f'<div class="vt-kpi {clase}" title="{escape(tip or rot)}">'
                f'<span class="vt-kpi-rot">{escape(rot)}</span>'
                f'<span class="vt-kpi-val">{escape(val)}</span></div>')
    partes = [_k(*k) for k in kpis]
    return (f'<div class="vt-cab"><span class="vt-cab-tit">{escape(tit)}'
            f'</span><div class="vt-kpis">{"".join(partes)}</div></div>')


def cuerpo(d, filtrar_cb=None, interruptor=None):
    """El modo «A medida»: un total de venta, unidades y pedidos para los
    días y el horario que se elijan, con el detalle por día y por plato.

    Se dibuja ADENTRO de la tarjeta y del fragment de «Por hora»;
    `interruptor` es el «Mapa | A medida» de esa tarjeta, que va primero en
    el renglón del título."""
    ss = st.session_state
    cfg = REPORTES.get("Ventas", {})
    cols_d = _columnas(d)
    col_hora = cols_d["hora"] or cols_d["cobro"]
    if not (col_hora and cols_d["venta"]):
        st.info("Faltan columnas (fecha del pedido, venta) para esta vista.")
        return
    lim = rango_fechas(cfg.get("archivo", "ventas.parquet"),
                       cfg.get("carga_por_rango", "FEC REG DOCUMENTO"))
    _fd = pd.to_datetime(d[col_hora], errors="coerce").dropna()
    primer, ancla = lim if lim else (_fd.min().date(), _fd.max().date())

    # ── El renglón del título: el interruptor y, a su derecha, los KPI,
    # que se escriben al final ─────────────────────────────────────────
    cab = st.container(horizontal=True, gap="medium",
                       vertical_alignment="center", key="vt_frj_cabfila")
    if interruptor is not None:
        with cab:
            interruptor()

    # ── La fila de controles: fecha · días · horario ─────────────────
    # Abre en «Últimos 30 días» hasta el último día con venta, el
    # mínimo de un mes de todas las tarjetas (regla #616).
    ctx = ctx_rango_propio()
    if ctx:
        _d30 = dict((c, r) for c, _n, _g, r in
                    atajos_tarjeta(ancla, (primer, ancla))).get("d30")
        if _d30:
            ctx = {**ctx, "rango_default_cat": {
                **(ctx.get("rango_default_cat") or {}), CATEGORIA: _d30}}
    ss.pop("vt_frj_fecha_flag", None)
    rng = (rango_tarjeta(CATEGORIA, ctx) if ctx else None) or (
        ancla - _dt.timedelta(days=29), ancla)
    ini, fin = rng[0], min(rng[1], ancla)

    # ── Los controles, en DOS filas compactas como la del mapa ─────────
    # Hasta el 2026-10-10 eran columnas con los controles de Streamlit a su
    # tamaño (40 px de alto, la fecha como cápsula de 50) y el modo se veía
    # desproporcionado al lado del mapa, que usa desplegables sin caja de
    # 28 px (regla #627). Las dos filas se crean juntas y la segunda se
    # llena después de cargar: sus opciones dependen de lo cargado.
    fila1 = st.container(horizontal=True, gap="small",
                         vertical_alignment="center", key="vt_frj_fila")
    fila2 = st.container(horizontal=True, gap="small",
                         vertical_alignment="center", key="vt_frj_fila2")
    with fila1:
        if ctx:
            selector_fecha_tarjeta("vt_frjf", "vt_frj_fecha_flag",
                                   categoria=CATEGORIA, ctx=ctx)
        if ss.get("vt_frj_modo") not in MODOS:
            ss["vt_frj_modo"] = MODOS[0]
        modo = st.selectbox("Días", MODOS, key="vt_frj_modo",
                            label_visibility="collapsed", width=150)
        # ── Qué días, según el modo ──────────────────────────────────
        if modo == MODOS[0]:
            sel = st.pills("Días de la semana", DIAS, selection_mode="multi",
                           default=list(DIAS), key="vt_frj_dias",
                           label_visibility="collapsed") or []
            dias_semana = [DIAS.index(x) for x in sel]
            dias = dias_elegidos(ini, fin, dias_semana)
        else:
            dias_semana = []
            todas = list(reversed(dias_elegidos(ini, fin, range(7))))
            _validos = [x for x in (ss.get("vt_frj_sueltos") or [])
                        if x in todas]
            ss["vt_frj_sueltos"] = _validos
            dias = sorted(st.multiselect(
                "Días sueltos", todas, key="vt_frj_sueltos",
                format_func=_fecha_corta, label_visibility="collapsed",
                placeholder="Elegí los días…", width=300))
        # El horario: «de 17:30» «a 23:30». La palabra va en el valor y no
        # en un rótulo: con el rótulo oculto, un `help=` no se ve (#555).
        desde_t = st.selectbox("Desde", HORAS, index=HORAS.index("00:00"),
                               key="vt_frj_desde",
                               format_func=lambda h: f"de {h}",
                               label_visibility="collapsed", width=96)
        hasta_t = st.selectbox("Hasta", HORAS_HASTA,
                               index=HORAS_HASTA.index("24:00"),
                               key="vt_frj_hasta",
                               format_func=lambda h: f"a {h}",
                               label_visibility="collapsed", width=96)
    desde, hasta = a_minutos(desde_t), a_minutos(hasta_t)
    cruza = cruza_medianoche(desde, hasta)

    if not dias:
        with cab:
            st.markdown(_html_cab("Días y horario a medida", []),
                        unsafe_allow_html=True)
        st.info("Elegí al menos un día." if modo == MODOS[1] else
                "Ningún día de las fechas elegidas cae en los días "
                "marcados.")
        return

    with st.spinner("Cargando las ventas…"):
        df = _cargar(dias[0], dias[-1], cruza, filtrar_cb, d)
    if df is None or df.empty:
        b = None
    else:
        cols = _columnas(df)
        b = _base(df, cols, cols["hora"] or cols["cobro"])
        dentro, dia = en_horario(b["ts"], desde, hasta)
        b = b.assign(dia=dia)[dentro]
        b = b[b["dia"].dt.date.isin(set(dias))]

    # ── Canal, ámbito y detalle, sobre lo que hay en esos días ─────────
    canales = (sorted(b["canal"].unique()) if b is not None
               and not b.empty else [])
    with fila2:
        # Sin ninguno marcado, todos: un «Todos» como pastilla más se
        # quedaba prendido al marcar Rappi y había que apagarlo a mano.
        _prev = [x for x in (ss.get("vt_frj_canal") or []) if x in canales]
        ss["vt_frj_canal"] = _prev
        canal_sel = st.pills("Canal", canales, selection_mode="multi",
                             key="vt_frj_canal",
                             label_visibility="collapsed") or []
        if b is not None and canal_sel:
            b = b[b["canal"].isin(canal_sel)]
        amb_ops = opciones_ambito(b if b is not None and not b.empty
                                  else None)
        if ss.get("vt_frj_amb") not in amb_ops:
            ss["vt_frj_amb"] = TODA_LA_CARTA
        amb = st.selectbox("Ámbito", list(amb_ops), key="vt_frj_amb",
                           label_visibility="collapsed",
                           width=210) or TODA_LA_CARTA
        nivel = st.segmented_control(
            "Detalle por", AGRUPAR, default=AGRUPAR[0], required=True,
            key="vt_frj_agrupar", label_visibility="collapsed"
        ) or AGRUPAR[0]
    col_amb, cual = amb_ops[amb]
    if b is not None and col_amb is not None:
        b = b[b[col_amb] == cual]

    # ── Las cuentas ──────────────────────────────────────────────────
    pd_dia = por_dia(b, dias)
    venta = float(pd_dia["venta"].sum())
    cant = float(pd_dia["cant"].sum())
    pedidos = int(b["pedido"].replace("", pd.NA).nunique()
                  ) if b is not None and not b.empty else 0
    con_venta = int((pd_dia["venta"] != 0).sum())
    que = _que_dias(dias, modo, dias_semana)
    horario = ("todo el día" if desde == 0 and hasta == 1440 else
               f"{desde_t} → {hasta_t}" + (" (día siguiente)"
                                           if cruza else ""))
    with cab:
        st.markdown(_html_cab(f"{que} · {horario}", [
            ("Venta", f"S/ {venta:,.0f}", "vt-kpi-total",
             f"Venta de {que}, {horario}, con IGV"),
            ("Unidades", f"{cant:,.0f}", "",
             "Unidades vendidas; un combo cuenta como una"),
            ("Pedidos", f"{pedidos:,}", "",
             "Pedidos distintos con al menos un ítem en el horario"),
            ("Por día", f"S/ {venta / len(dias):,.0f}", "",
             f"Venta ÷ {len(dias)} días elegidos (también los que no "
             "vendieron)"),
            ("Días con venta", f"{con_venta} de {len(dias)}", "", ""),
        ]), unsafe_allow_html=True)

    # ── El detalle: por día y por plato ──────────────────────────────
    # Con la barra del peso de cada fila adentro de la celda, como la
    # Carta costeada: así el mejor domingo y el plato que manda se ven sin
    # leer números. `st.dataframe` y no AgGrid: cada grilla cuesta 1,28 MB
    # (regla #540). Los anchos van en píxeles, medidos a 1323.
    # columnas-internas: las dos tablas del detalle
    t_dia, t_grp = st.columns([1, 1.45], gap="medium")
    with t_dia:
        peso = (pd_dia["venta"] / venta * 100 if venta
                else pd_dia["venta"] * 0).to_numpy(dtype=float)
        ped = pd_dia["pedidos"].to_numpy(dtype=float)
        t = pd.DataFrame({
            "Día": [_fecha_corta(x) for x in pd_dia.index],
            "Venta": pd_dia["venta"].to_numpy(dtype=float),
            "% del total": peso,
            "Pedidos": ped,
            # Sin vacíos: un NaN se pinta «None» (regla #529); 0 → «—».
            "Ticket": [v / p if p else 0.0
                       for v, p in zip(pd_dia["venta"], ped)],
        }).iloc[::-1]
        sin_venta = (t["Venta"] == 0).to_numpy()
        sty = (t.style
               .format(lambda v: f"S/ {v:,.0f}" if v else "—",
                       subset=["Venta", "Ticket"])
               .format(lambda v: f"{v:,.0f}" if v else "—",
                       subset=["Pedidos"])
               # Los días sin venta, en gris: son parte de la respuesta,
               # pero no se tienen que leer como una fila más.
               .apply(lambda c: [f"color: {GRIS_TEXTO_SUAVE}" if x else ""
                                 for x in sin_venta],
                      subset=["Día", "Venta", "Pedidos", "Ticket"]))
        st.dataframe(
            sty, hide_index=True, height=alturas.VENTAS_PLATOS_TABLA,
            row_height=27, key="vt_frj_tdia",
            column_config={
                "Día": st.column_config.TextColumn(width=84, pinned=True),
                "Venta": st.column_config.Column(width=78),
                "% del total": st.column_config.ProgressColumn(
                    format="%.1f%%", min_value=0,
                    max_value=max(float(peso.max()), 1.0), width=96,
                    help="Cuánto del total de los días elegidos se vendió "
                         "ese día. La barra más larga es el mejor día."),
                "Pedidos": st.column_config.Column(width=58),
                "Ticket": st.column_config.Column(
                    width=66, help="Venta ÷ pedidos de ese día, en el "
                                   "horario elegido"),
            })
    with t_grp:
        g = por_grupo(b, nivel)
        nombre = {"Plato": "prod", "Subgrupo": "sub",
                  "Grupo": "grupo"}[nivel]
        pct = (g["venta"] / venta * 100 if venta
               else g["venta"] * 0).to_numpy(dtype=float)
        tg = pd.DataFrame({
            nivel: g[nombre].to_numpy(),
            "Unidades": g["cant"].to_numpy(dtype=float),
            "Por día": (g["cant"] / len(dias)).to_numpy(dtype=float),
            "Venta": g["venta"].to_numpy(dtype=float),
            "% venta": pct,
        })
        if nivel == "Plato":
            tg.insert(1, "Subgrupo", g["sub"].to_numpy())
        cfg = {
            nivel: st.column_config.TextColumn(
                width=190 if nivel == "Plato" else 230, pinned=True),
            "Unidades": st.column_config.Column(width=66),
            "Por día": st.column_config.Column(
                width=60, help=f"Unidades ÷ {len(dias)} días elegidos: "
                               "cuántos salen en promedio cada día"),
            "Venta": st.column_config.Column(width=82),
            "% venta": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0,
                max_value=max(float(pct.max()) if len(pct) else 0.0, 1.0),
                width=104, help="Parte de la venta total del horario"),
        }
        if nivel == "Plato":
            cfg["Subgrupo"] = st.column_config.TextColumn(width=110)
        st.dataframe(
            tg.style.format(lambda v: f"S/ {v:,.0f}", subset=["Venta"])
            .format(lambda v: f"{v:,.0f}", subset=["Unidades"])
            .format(lambda v: f"{v:,.1f}", subset=["Por día"]),
            hide_index=True, height=alturas.VENTAS_PLATOS_TABLA,
            row_height=27, key="vt_frj_tgrp", column_config=cfg)

    notas = [f"{que.capitalize()}: {_lista_dias(dias)}.",
             "Por la hora del PEDIDO; la hora de «a» no se incluye "
             "(«a 22:00» llega a las 21:59) y, si es antes que la de "
             "«de», el horario cruza la medianoche."]
    if cruza:
        notas.append("Lo de después de medianoche cuenta en el día "
                     "anterior.")
    notas.append(("Canal: " + ", ".join(canal_sel) + ".") if canal_sel
                 else "Todos los canales.")
    if cols_d["hora"] is None:
        notas.append("Sin la hora del pedido en el parquet: va por la "
                     "del cobro.")
    notas.append("Los Filtros de arriba también aplican. Un combo cuenta "
                 "como una unidad.")
    st.caption(" ".join(notas))
