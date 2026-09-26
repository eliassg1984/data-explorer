"""
graficos.ventas_ficha_hora — la «ficha de la hora» de Ventas › Por hora: lo
que abre un CLIC en una celda del mapa día × hora (regla #536).

POR QUÉ EXISTE
    El mapa pinta cuánto se vendió en cada hora, pero una celda oscura no
    dice qué la hizo. Medido en septiembre 2026: en el 48 % de las celdas con
    venta un solo pedido hizo más de la mitad, y dos de las más oscuras del
    mes eran una venta de charcutería de mostrador (mié 23, 9 pm: 86 % Venta
    Interna, sin personas, cobrada en 2 a 11 minutos) y un evento de 16
    personas (jue 24, 7 pm) — con el mismo color que un salón lleno de verdad
    (sáb 5, 7 pm: 12 pedidos, ninguno pasa del 21 %).

    La ficha contesta las dos preguntas que uno trae al ver una celda que
    resalta: ¿qué fue? y ¿es raro? El diseño salió de un mockup con datos
    reales que el usuario aprobó el 2026-09-26.

MESA = PEDIDO DEL LOCAL CON PERSONAS
    El parquet no trae el número de mesa ni cuántas tiene el salón, y no se
    le pide al usuario («no usemos el dato del asiento, sino por mesa»). Una
    mesa es un pedido (`LLAVE LOCAL PEDIDO`) del canal «En el Local», con
    personas y con venta. Quedan fuera Rappi, la Venta Interna y los pedidos
    sin personas: el 6 % de los del local, casi todos compras chicas
    (medido jun–sep 2026: con personas duran 90 min de mediana y ninguno
    menos de 15; sin personas, 24 min, y el 40 % baja de 15). Salen igual en
    la lista de pedidos, marcados, pero no cuentan como mesa.

LO NORMAL = LAS 8 SEMANAS ANTERIORES
    Mismo día de la semana, misma hora: mediana y rango. Va el rango porque
    una misma franja cambia mucho de una semana a otra —su desviación típica
    es dos tercios de su promedio (mediana jun–sep 2026)—, y un promedio solo
    haría parecer rara a cualquier semana. Es una cuenta descriptiva, no un
    estándar, y la app lo dice.

LAS CUENTAS CIERRAN
    Venta en mesas = mesas × venta por mesa; venta por mesa = personas por
    mesa × gasto por persona. Son divisiones, así que la cadena cierra al
    céntimo y dice POR QUÉ una hora vendió más: más mesas o más gasto. La
    «venta por hora de mesa» (lo que dejaron las mesas ÷ las horas que
    estuvieron sentadas) es una variante por mesa del RevPASH de Kimes y
    otros (1998), que divide por asientos DISPONIBLES; ésta, por mesas
    OCUPADAS. Cálculo propio, dicho así en su «i».

MESAS ABIERTAS A LA VEZ
    Una mesa está «abierta» entre la hora del pedido y su último cobro. El
    cobro llega cuando piden la cuenta, no cuando se levantan: es lo más
    cercano que trae el parquet. Todo va en instantes ABSOLUTOS, no en
    «minutos del día», para que la cena que cruza la medianoche no se parta.

DE DÓNDE SALEN LOS DATOS
    No de los tramos del mapa: la ficha necesita las 8 semanas ANTERIORES a
    la celda, que casi nunca están en pantalla. `ventana()` dice qué rango
    traer, y es por PANEL y no por celda: todas las celdas de un mes comparten
    la misma lectura cacheada, en vez de ir a R2 en cada clic a un día nuevo.
"""

import datetime as _dt
from html import escape as _esc

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
import definicion_venta as dv
from graficos import alturas
from graficos.base import _resolver
from tema import (
    ACENTO, GRIS_LINEA, GRIS_TEXTO, GRIS_TEXTO_SUAVE, LAVANDA_FONDO,
    TEXTO_PRINCIPAL,
)

# Los grupos que venden sin ser servicio de salón. El interruptor «Venta
# Interna y Eventos» del mapa los saca con esta misma tupla.
GRUPOS_RAROS = ("Venta Interna", "Eventos")
_VENTA_INTERNA, _EVENTOS = GRUPOS_RAROS
_CANAL_LOCAL = "En el Local"
SEMANAS_NORMAL = 8
# Un pedido «abierto» más de 6 horas es un olvido del POS, no una mesa: sin
# este tope, uno solo estiraba la mediana y la línea de mesas abiertas.
_MAX_MIN_MESA = 360
_TOP_ITEMS = 12
_PASO_MIN = 5
_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado",
         "domingo")
_DIAS_PL = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábados",
            "domingos")
# «Mesas del salón» es opcional y vive dentro de la ficha, que no siempre se
# dibuja: un widget que deja de dibujarse pierde su estado (CLAUDE.md), así
# que el número se guarda aparte y vuelve por `value=`.
_K_SALON = "vh_mesas_salon"
_K_SALON_VALOR = "_vh_mesas_salon_valor"

_INFO = {
    "normal": "Las 8 semanas anteriores, mismo día de la semana y misma "
              "hora: la mediana y el rango, de la menor a la mayor. Es una "
              "cuenta descriptiva, no un estándar.",
    "mesa": "Mesa = pedido del local con personas registradas. Quedan fuera "
            "Rappi, la Venta Interna y los pedidos sin personas. No hace "
            "falta saber cuántas mesas ni asientos tiene el salón.",
    "dur": "Mediana del pedido al último cobro. El cobro llega cuando piden "
           "la cuenta, no cuando se levantan. La duración es una de las dos "
           "palancas de la gestión de ingresos en restaurantes, junto con el "
           "precio (Kimes y otros, 1998).",
    "vxh": "Lo que dejaron las mesas que abrieron a esta hora ÷ las horas "
           "que estuvieron sentadas. Variante por mesa del RevPASH (Kimes y "
           "otros, 1998; Kimes, 1999), que divide por asientos disponibles; "
           "ésta divide por mesas ocupadas. Cálculo propio.",
    "conc": "Mesas con el pedido abierto y sin cobrar, minuto a minuto. Con "
            "«Mesas del salón» pasa a ser la ocupación. Cálculo propio.",
    "meseros": "El mesero que abrió el pedido. «Personas por mesero» es una "
               "cuenta descriptiva.",
}


# ── Datos (funciones puras) ─────────────────────────────────────────────────

def ventana(ini, fin):
    """El rango que hay que traer de R2 para las fichas de un panel: el panel
    entero, las 8 semanas de antes (lo normal) y un día después (la cena que
    se cobra pasada la medianoche)."""
    return (ini - _dt.timedelta(weeks=SEMANAS_NORMAL),
            fin + _dt.timedelta(days=1))


def filas(df, c):
    """Las filas del df con los nombres que usa la ficha, y su celda.

    `c` trae los nombres de columna que ya resolvió el mapa: `tiempo` (la
    hora que decide la celda —la del pedido o la del cobro, la misma que el
    mapa—), `apertura`, `cobro`, `venta`, `pax`, `pedido`, `prod`, `cant` y
    `grupo`. El mesero y el canal se resuelven acá. El df llega como lo ve
    el mapa: con los chips, un ítem una vez y sólo venta (`filtrar_cb`)."""
    if df is None or df.empty:
        return None
    if c.get("tiempo") not in df.columns or c.get("pedido") not in df.columns:
        return None

    def _num(clave):
        col = c.get(clave)
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce").fillna(0.0).values
        return 0.0

    def _txt(col):
        if col not in df.columns:
            return ""
        s = df[col]
        return s.where(s.notna(), "").astype(str).str.strip().values

    def _fecha(col):
        if col not in df.columns:
            return pd.NaT
        return pd.to_datetime(df[col], errors="coerce").values

    _c_doc = dv.columna(df, dv.LLAVE_DOC)
    out = pd.DataFrame({
        "ped": df[c["pedido"]].astype(str).values,
        # El comprobante, para que la nota de crédito reste personas sin
        # descontar a la mesa que sí vino (`definicion_venta.pax_por`).
        "doc": df[_c_doc].astype(str).values if _c_doc else "",
        "t": pd.to_datetime(df[c["tiempo"]], errors="coerce").values,
        "abre": _fecha(c.get("apertura")),
        "cobra": _fecha(c.get("cobro")),
        "venta": _num("venta"),
        "pax": (pd.to_numeric(df[c["pax"]], errors="coerce").values
                if c.get("pax") in df.columns else np.nan),
        "cant": _num("cant"),
        "prod": _txt(c.get("prod")),
        "grupo": _txt(c.get("grupo")),
        "mesero": _txt(_resolver(df, ["Nombre Mesero", "Nomb Mesero"])),
        "canal": _txt(_resolver(df, ["Canal Venta", "Canal_Venta",
                                     "Nomb Canal Venta", "Canal"])),
    }, index=df.index)
    out = out[out["t"].notna()].copy()
    for col in ("t", "abre", "cobra"):
        out[col] = pd.to_datetime(out[col]).astype("datetime64[ns]")
    out["dia"] = out["t"].dt.normalize()
    out["hora"] = out["t"].dt.hour.astype("int64")
    return out


def pedidos(fl):
    """Una fila por pedido, con lo que es del PEDIDO y no del ítem: cuándo
    abrió y cuándo se cobró, cuántas personas, quién lo abrió, si trae Venta
    Interna o Eventos, y si es una mesa (ver el docstring del módulo)."""
    if fl is None or fl.empty:
        return None
    x = fl.assign(_vi=fl["grupo"].eq(_VENTA_INTERNA),
                  _ev=fl["grupo"].eq(_EVENTOS))
    g = x.groupby("ped", sort=False)
    p = pd.DataFrame({
        "abre": g["abre"].min(),
        "cobra": g["cobra"].max(),
        "venta": g["venta"].sum(),
        "mesero": g["mesero"].first(),
        "canal": g["canal"].first(),
        "vi": g["_vi"].any(),
        "ev": g["_ev"].any(),
    })
    # Personas: una vez por pedido y la nota de crédito resta, con la misma
    # regla que el mapa (`definicion_venta.pax_por`). El `por` es el mismo
    # pedido con otro nombre, así que devuelve el neto de cada uno.
    tp = x.dropna(subset=["pax"]).assign(_ped_por=lambda t: t["ped"])
    con_doc = "doc" if tp["doc"].ne("").any() else None
    pax = (dv.pax_por(tp, "ped", "pax", doc=con_doc, por="_ped_por")
           if not tp.empty else pd.Series(dtype=float))
    p["pax"] = pax.reindex(p.index).fillna(0.0).clip(lower=0)
    p["min"] = (p["cobra"] - p["abre"]).dt.total_seconds() / 60
    p.loc[(p["min"] < 0) | (p["min"] > _MAX_MIN_MESA), "min"] = np.nan
    # Sin columna de canal (el demo) todo es del local.
    local = p["canal"].eq(_CANAL_LOCAL) | p["canal"].eq("")
    p["mesa"] = local & (p["pax"] > 0) & (p["venta"] > 0) & ~p["vi"]
    return p.rename_axis("ped").reset_index()


def de_la_celda(fl, peds, dia, hora, con_items=False):
    """Los pedidos de UNA celda con la venta que cayó en ella (`v`), del más
    grande al más chico; y, con `con_items`, lo que pidió cada uno."""
    x = fl[(fl["dia"] == pd.Timestamp(dia)) & (fl["hora"] == int(hora))]
    if x.empty:
        return peds.iloc[0:0].assign(v=0.0), {}
    v = x.groupby("ped")["venta"].sum().rename("v")
    pc = (peds.set_index("ped").join(v, how="inner")
          .rename_axis("ped").reset_index()
          .sort_values("v", ascending=False, kind="stable"))
    items = {}
    if con_items:
        it = x.groupby(["ped", "prod"], as_index=False).agg(
            cant=("cant", "sum"), venta=("venta", "sum"))
        it = it[it["venta"].abs() > 0.004]
        for p, gi in it.groupby("ped"):
            top = gi.sort_values("venta", ascending=False).head(_TOP_ITEMS)
            items[p] = list(zip(top["prod"], top["cant"], top["venta"]))
    return pc, items


def metricas(pc):
    """Las cuentas por mesa de una celda, o None si no se abrió ninguna."""
    if pc is None or pc.empty:
        return None
    m = pc[pc["mesa"]]
    n = len(m)
    if not n:
        return None
    v, pax = float(m["v"].sum()), float(m["pax"].sum())
    ct = m.dropna(subset=["min"])
    horas_mesa = float(ct["min"].sum()) / 60
    return {
        "mesas": n, "v": v, "pax": pax, "vxm": v / n, "pxm": pax / n,
        "gxp": v / pax if pax else None,
        "dur": float(ct["min"].median()) if len(ct) else None,
        "vxh": float(ct["v"].sum()) / horas_mesa if horas_mesa > 0 else None,
    }


def intervalos(peds):
    """(aperturas, cobros) de las mesas, cada uno ORDENADO por separado:
    es lo que pide `abiertas`."""
    if peds is None or peds.empty:
        vacio = np.array([], dtype="datetime64[ns]")
        return vacio, vacio
    m = peds[peds["mesa"] & peds["abre"].notna() & peds["min"].notna()]
    return (np.sort(m["abre"].values.astype("datetime64[ns]")),
            np.sort(m["cobra"].values.astype("datetime64[ns]")))


def abiertas(ini, fin, instantes):
    """Cuántas mesas había abiertas en cada instante: las que abrieron hasta
    ahí menos las que ya se cobraron. Una mesa cobrada a las 9:00 ya no
    cuenta a las 9:00."""
    t = np.asarray(instantes, dtype="datetime64[ns]")
    return (np.searchsorted(ini, t, side="right")
            - np.searchsorted(fin, t, side="right"))


def pico(ini, fin, t0, t1):
    """Lo más que hubo abierto en [t0, t1). La cuenta sube sólo cuando abre
    una mesa, así que basta mirarla al arranque y en cada apertura."""
    t0 = pd.Timestamp(t0).to_datetime64().astype("datetime64[ns]")
    t1 = pd.Timestamp(t1).to_datetime64().astype("datetime64[ns]")
    t = np.concatenate([[t0], ini[(ini >= t0) & (ini < t1)]])
    return int(abiertas(ini, fin, t).max()) if len(ini) else 0


def bloque(horas, hora):
    """Las horas del servicio (almuerzo, cena) al que pertenece `hora`: el
    tramo de `horas` —que llega en orden de servicio— sin saltos de más de
    una hora."""
    tramos, actual = [], []
    for h in horas:
        if actual and (int(h) - actual[-1]) % 24 > 1:
            tramos.append(actual)
            actual = []
        actual.append(int(h))
    if actual:
        tramos.append(actual)
    return next((t for t in tramos if int(hora) in t), [int(hora)])


def ventana_servicio(dia, horas, hora):
    """(t0, t1, h0, h1) en instantes absolutos: el servicio de la celda —de
    media hora antes de su primera hora a una hora después de la última— y
    la hora clicada.

    Las horas de después de la medianoche siguen a la víspera: la celda de
    las 12 am del 6 es el final de la cena del 5, y su línea arranca el 5."""
    b = bloque(horas, hora)
    ajuste, mas, prev = [], 0, None
    for h in b:
        if prev is not None and h < prev:
            mas = 24
        ajuste.append(h + mas)
        prev = h
    h_clic = ajuste[b.index(int(hora))] if int(hora) in b else int(hora)
    base = pd.Timestamp(dia) - pd.Timedelta(days=1 if h_clic >= 24 else 0)
    t0 = base + pd.Timedelta(hours=ajuste[0]) - pd.Timedelta(minutes=30)
    t1 = base + pd.Timedelta(hours=ajuste[-1] + 2)
    h0 = base + pd.Timedelta(hours=h_clic)
    return t0, t1, h0, h0 + pd.Timedelta(hours=1)


def linea(ini, fin, t0, t1):
    """Mesas abiertas cada 5 minutos entre t0 y t1."""
    t = pd.date_range(t0, t1, freq=f"{_PASO_MIN}min")
    return t, abiertas(ini, fin, t.values)


def tipica(ini, fin, t0, t1):
    """La línea de un día normal: la mediana, instante por instante, de las
    8 semanas anteriores."""
    series = [linea(ini, fin, t0 - pd.Timedelta(weeks=s),
                    t1 - pd.Timedelta(weeks=s))[1]
              for s in range(1, SEMANAS_NORMAL + 1)]
    return np.median(np.vstack(series), axis=0)


def normal(fl, peds, dia, hora, ini, fin):
    """Las 8 semanas anteriores, mismo día y misma hora: por cada una, la
    venta de la celda, sus cuentas por mesa y lo más que hubo abierto."""
    out = []
    for s in range(SEMANAS_NORMAL, 0, -1):
        dd = pd.Timestamp(dia) - pd.Timedelta(weeks=s)
        pc, _it = de_la_celda(fl, peds, dd, hora)
        m = metricas(pc) or {}
        t0 = dd + pd.Timedelta(hours=int(hora))
        out.append({
            "dia": dd, "v": float(pc["v"].sum()) if len(pc) else 0.0,
            "mesas": m.get("mesas", 0), "v_mesas": m.get("v", 0.0),
            "vxm": m.get("vxm"), "pxm": m.get("pxm"), "gxp": m.get("gxp"),
            "dur": m.get("dur"), "vxh": m.get("vxh"),
            "conc": pico(ini, fin, t0, t0 + pd.Timedelta(hours=1)),
        })
    return out


def mediana(valores):
    """Mediana de los que no faltan, o None."""
    x = [float(v) for v in valores if v is not None and not pd.isna(v)]
    return float(np.median(x)) if x else None


def frase_normal(v, previas, dow, hora):
    """«La más alta de 9 sábados a las 7 pm»: dónde cae la celda entre ella
    y sus 8 semanas anteriores."""
    a = (f"a {'la' if (int(hora) % 12 or 12) == 1 else 'las'} "
         f"{cortes.etiqueta_hora(hora)}")
    pl, n = _DIAS_PL[dow], len(previas) + 1
    if not previas:
        return "Sin semanas anteriores para comparar"
    if v == 0 and max(previas) == 0:
        return f"Ni esta ni las {len(previas)} semanas anteriores vendieron {a}"
    if all(x < v - 0.5 for x in previas):
        return f"La más alta de {n} {pl} {a}"
    if all(x > v + 0.5 for x in previas):
        return f"La más baja de {n} {pl} {a}"
    k = sum(1 for x in previas if x > v + 0.5) + 1
    return f"La {k}.ª más alta de {n} {pl} {a}"


# ── Formato ─────────────────────────────────────────────────────────────────

def _soles(v):
    return "—" if v is None or pd.isna(v) else f"S/ {v:,.0f}"


def _soles2(v):
    return "—" if v is None or pd.isna(v) else f"S/ {v:,.2f}"


def _dur(m):
    if m is None or pd.isna(m):
        return "—"
    m = int(round(m))
    return f"{m // 60} h {m % 60:02d}" if m >= 60 else f"{m} min"


def _reloj(ts):
    """«7:05 pm»."""
    if ts is None or pd.isna(ts):
        return "—"
    h, mi = int(ts.hour), int(ts.minute)
    return f"{h % 12 or 12}:{mi:02d} {'am' if h < 12 else 'pm'}"


def _corto(nombre):
    """«Luis A.»: en una lista de tres o cuatro, basta para saber quién."""
    p = [x for x in str(nombre or "").replace(",", " ").split() if x]
    if not p:
        return "—"
    return p[0].title() + (f" {p[1][0].upper()}." if len(p) > 1 else "")


def _info(clave):
    t = _esc(_INFO[clave], quote=True)
    return f'<span class="vhh-info" title="{t}" aria-label="{t}">i</span>'


def _chip(actual, normal_, neutro=False):
    """▲ 18 % / ▼ 12 % / ≈ normal contra la mediana. Verde y rojo sólo donde
    subir es bueno para la venta; el tiempo y las mesas a la vez van en gris
    (una mesa que dura más no es buena ni mala por sí sola)."""
    if actual is None or normal_ is None or not normal_ or pd.isna(actual):
        return ""
    pct = (actual - normal_) / normal_
    if abs(pct) < 0.05:
        return '<span class="vhh-chip neutro">≈ normal</span>'
    arriba = pct > 0
    cls = "neutro" if neutro else ("sube" if arriba else "baja")
    return (f'<span class="vhh-chip {cls}">{"▲" if arriba else "▼"} '
            f'{abs(pct) * 100:,.0f}%</span>')


def _factor(etiqueta, valor, actual, normal_, fmt, total=False, neutro=False,
            info=None):
    nor = (f"normal {fmt(normal_)}" if normal_ is not None
           else "sin semanas para comparar")
    return (f'<div class="vhh-factor{" total" if total else ""}">'
            f'<span class="vhh-flab">{etiqueta}{" " + _info(info) if info else ""}'
            f'</span><span class="vhh-fval">{valor}</span>'
            f'<span class="vhh-fnor">{nor}</span>'
            f'{_chip(actual, normal_, neutro)}</div>')


# ── HTML de cada bloque ─────────────────────────────────────────────────────

def _html_normal(v, previas, dow, hora):
    vb = [p["v"] for p in previas]
    med = mediana(vb)
    html = [f'<p class="vhh-h3">Contra lo normal {_info("normal")}</p>',
            f'<p class="vhh-frase">{frase_normal(v, vb, dow, hora)}</p>']
    # Sin semanas, o con todo en cero, la frase ya lo dijo: una tira de nueve
    # puntos apilados en S/ 0 no agrega nada.
    if not vb or (not v and not max(vb)):
        return "".join(html)
    tope = max([v] + vb) or 1.0
    x = (lambda val: 100.0 * val / tope)   # noqa: E731
    puntos, puestos = [], []
    for p in sorted(previas, key=lambda q: q["v"]):
        xp = x(p["v"])
        # Carriles: dos puntos que caen casi en el mismo lugar se apilan
        # arriba y abajo en vez de taparse.
        off = next((o for o in (0, -8, 8, -15, 15)
                    if not any(q == o and abs(xq - xp) < 2.6
                               for xq, q in puestos)), 0)
        puestos.append((xp, off))
        f = p["dia"]
        tit = _esc(f"{cortes.DIAS_ABR_ES[f.weekday()]} {f.day} "
                   f"{cortes.MESES_ABR_ES[f.month - 1]} · {_soles(p['v'])}")
        puntos.append(f'<span class="vhh-punto" title="{tit}" '
                      f'style="left:{xp:.1f}%;top:{26 + off}px"></span>')
    xa = x(v)
    lado = " der" if xa > 85 else (" izq" if xa < 12 else "")
    tira = ('<div class="vhh-tira"><span class="vhh-eje"></span>'
            + (f'<span class="vhh-med" style="left:{x(med):.1f}%"></span>'
               if med is not None else "")
            + "".join(puntos)
            + f'<span class="vhh-punto act" style="left:{xa:.1f}%;top:26px" '
              f'title="esta hora · {_soles(v)}"></span>'
            + f'<span class="vhh-valor{lado}" style="left:{xa:.1f}%">'
              f'{_soles(v)}</span>'
            + '<span class="vhh-tick izq" style="left:0%">S/ 0</span>'
            + f'<span class="vhh-tick der" style="left:100%">{_soles(tope)}'
              '</span></div>')
    pct = (v - med) / med if med else None
    html += [tira,
             '<p class="vhh-ley"><span><i class="pt act"></i>esta hora</span>'
             '<span><i class="pt"></i>las 8 semanas anteriores</span>'
             '<span><i class="tk"></i>mediana</span></p>',
             f'<p class="vhh-nota"><b>{_soles(v)}</b> contra una mediana de '
             f'<b>{_soles(med)}</b> (de {_soles(min(vb))} a {_soles(max(vb))})'
             + (f" · {'+' if pct >= 0 else '−'}{abs(pct) * 100:,.0f}%"
                if pct is not None else "") + ".</p>"]
    return "".join(html)


def _html_mesa(met, previas, v_hora, conc, dow, hora, n_pedidos):
    html = [f'<p class="vhh-h3">Por mesa {_info("mesa")}</p>']
    con = [p for p in previas if p["mesas"]]
    nb = (lambda k: mediana(p[k] for p in con))   # noqa: E731
    n_mesas = mediana(p["mesas"] for p in previas)
    if not met:
        txt = ("Ningún pedido de esta hora ocupó una mesa: son Venta Interna, "
               "Rappi o pedidos sin personas." if n_pedidos else
               "Ninguna mesa se abrió a esta hora.")
        if n_mesas:
            txt += (f" Un {_DIAS[dow]} normal abre {n_mesas:,.0f} a esta "
                    "hora.")
        return "".join(html) + f'<p class="vhh-nota">{txt}</p>'
    uno = lambda v: f"{v:,.0f}"    # noqa: E731
    dec = lambda v: f"{v:,.1f}"    # noqa: E731
    html.append(
        '<div class="vhh-cadena">'
        + _factor("Venta en mesas", _soles(met["v"]), met["v"],
                  mediana(p["v_mesas"] for p in previas), _soles, total=True)
        + '<span class="vhh-op">=</span>'
        + _factor("Mesas", uno(met["mesas"]), met["mesas"], n_mesas, uno)
        + '<span class="vhh-op">×</span>'
        + _factor("Venta por mesa", _soles(met["vxm"]), met["vxm"], nb("vxm"),
                  _soles)
        + "</div>")
    html.append(
        '<div class="vhh-cadena">'
        f'<span class="vhh-intro">{_soles(met["vxm"])} por mesa =</span>'
        + _factor("Personas por mesa", dec(met["pxm"]), met["pxm"], nb("pxm"),
                  dec)
        + '<span class="vhh-op">×</span>'
        + _factor("Gasto por persona", _soles(met["gxp"]), met["gxp"],
                  nb("gxp"), _soles)
        + "</div>")
    html.append(
        '<div class="vhh-cadena">'
        + _factor("Tiempo en la mesa", _dur(met["dur"]), met["dur"],
                  nb("dur"), _dur, neutro=True, info="dur")
        + _factor("Venta por hora de mesa", _soles(met["vxh"]), met["vxh"],
                  nb("vxh"), _soles, info="vxh")
        + _factor("Mesas a la vez, máx.", uno(conc), conc,
                  mediana(p["conc"] for p in previas), uno, neutro=True,
                  info="conc")
        + "</div>")
    fuera = v_hora - met["v"]
    html.append(
        f'<p class="vhh-nota">La hora vendió <b>{_soles(v_hora)}</b>: '
        f'{_soles(fuera)} no pasaron por una mesa (Venta Interna, Rappi o '
        'pedidos sin personas).</p>' if fuera > 1 else
        '<p class="vhh-nota">Toda la venta de esta hora pasó por mesas.</p>')
    return "".join(html)


def _html_meseros(pc, met):
    html = [f'<p class="vhh-h3">Quién atendió {_info("meseros")}</p>']
    m = pc[pc["mesa"]] if pc is not None and len(pc) else None
    if m is None or m.empty:
        return "".join(html) + '<p class="vhh-nota">Sin mesas a esta hora.</p>'
    q = (m.assign(nom=m["mesero"].map(_corto))
         .groupby("nom", as_index=False)
         .agg(mesas=("ped", "size"), pax=("pax", "sum"), v=("v", "sum"))
         .sort_values("v", ascending=False, kind="stable"))
    filas_ = "".join(
        f'<tr><td>{_esc(r.nom)}</td><td class="n">{int(r.mesas)}</td>'
        f'<td class="n">{int(r.pax)}</td><td class="n">{_soles(r.v)}</td></tr>'
        for r in q.itertuples(index=False))
    n = len(q)
    top = q.iloc[0]
    nota = (f"{n} {'mesero' if n == 1 else 'meseros'} · "
            f"<b>{q['pax'].sum() / n:,.1f}</b> personas por mesero")
    # Quién cargó la hora, sólo si alguien la cargó: con una mesa cada uno,
    # «llevó 1 de 2» no dice nada.
    if n > 1 and top["mesas"] > max(1, int(q["mesas"].iloc[1])):
        nota += (f" · {_esc(top['nom'])} llevó {int(top['mesas'])} de "
                 f"{met['mesas']} mesas")
    return "".join(html) + (
        '<table class="vhh-tabla"><thead><tr><th>Mesero</th>'
        '<th class="n">Mesas</th><th class="n">Personas</th>'
        f'<th class="n">Venta</th></tr></thead><tbody>{filas_}</tbody></table>'
        f'<p class="vhh-nota">{nota}.</p>')


def _html_pedidos(pc, items):
    total = float(pc["v"].sum()) if len(pc) else 0.0
    resumen = ""
    if len(pc) and total > 0:
        resumen = (f"<em>· {len(pc)} {'pedido' if len(pc) == 1 else 'pedidos'}"
                   f" · el más grande hizo el {100 * pc['v'].iloc[0] / total:,.0f}%"
                   " de la hora</em>")
    html = [f'<p class="vhh-h3">Los pedidos de esa hora {resumen}</p>']
    if not len(pc):
        return "".join(html) + '<p class="vhh-nota">Ningún pedido a esta hora.</p>'
    html.append(
        '<div class="vhh-peds"><div class="vhh-fila vhh-cab"><span>Abrió</span>'
        '<span>Cobró</span><span class="n">En la mesa</span>'
        '<span class="n">Personas</span><span>Mesero</span>'
        '<span class="n">Venta</span><span>Parte de la hora</span>'
        '<span>Lo que más pesó</span></div>')
    for r in pc.itertuples(index=False):
        tag = ("Venta Interna" if r.vi else "Evento" if r.ev else
               "Rappi" if r.canal not in ("", _CANAL_LOCAL) else
               "" if r.mesa else "sin personas")
        cls_tag = "ambar" if tag in ("Venta Interna", "Evento") else "gris"
        tag_html = f'<span class="vhh-tag {cls_tag}">{tag}</span>' if tag else ""
        parte = max(0.0, 100 * r.v / total) if total > 0 else 0.0
        its = items.get(r.ped, [])
        top = _esc(its[0][0]) if its else "—"
        mas = (f' <span class="vhh-mas">+{len(its) - 1}</span>'
               if len(its) > 1 else "")
        lista = "".join(
            f'<li><span>{_esc(nom)} <small>× {cant:,.0f}</small></span>'
            f'<span>{_soles(val)}</span></li>' for nom, cant, val in its
        ) or "<li>Sin detalle</li>"
        html.append(
            f'<details class="vhh-ped{"" if r.mesa else " nomesa"}"><summary '
            'class="vhh-fila">'
            f'<span>{_reloj(r.abre)}</span><span>{_reloj(r.cobra)}</span>'
            f'<span class="n">{_dur(r.min)}</span>'
            f'<span class="n">{int(r.pax) if r.pax else "—"}</span>'
            f'<span>{_esc(_corto(r.mesero))}</span>'
            f'<span class="n">{_soles(r.v)}</span>'
            f'<span class="vhh-parte"><span class="vhh-barra">'
            f'<i style="width:{min(100.0, parte):.1f}%"></i></span>'
            f'{parte:,.0f}%</span>'
            f'<span>{tag_html}{top}{mas}</span></summary>'
            f'<ul class="vhh-items">{lista}</ul></details>')
    html.append("</div>")
    return "".join(html)


# ── Figura ──────────────────────────────────────────────────────────────────

def _fig_abiertas(t, serie, normal_, ref, h0, h1, horas_eje):
    """La línea de mesas abiertas del servicio: este día contra un día normal,
    con la hora clicada sombreada y la referencia de capacidad."""
    fig = go.Figure()
    fig.add_vrect(x0=h0, x1=h1, fillcolor=LAVANDA_FONDO, line_width=0,
                  layer="below")
    if normal_ is not None:
        fig.add_trace(go.Scatter(
            x=t, y=normal_, mode="lines", name="un día normal",
            line=dict(color=GRIS_TEXTO_SUAVE, width=1.5),
            hovertemplate="normal: %{y:.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=t, y=serie, mode="lines", name="este día",
        line=dict(color=ACENTO, width=2, shape="hv"),
        hovertemplate="este día: %{y} mesas<extra></extra>"))
    fig.add_hline(y=ref, line=dict(color=GRIS_TEXTO, width=1, dash="dot"))
    fig.update_layout(
        height=alturas.FICHA_HORA_MESAS,
        margin=dict(l=8, r=8, t=6, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL,
                  size=11),
        showlegend=False, hovermode="x unified", dragmode=False)
    # Rótulos explícitos: Plotly escribiría «7 PM» en inglés (regla #241).
    fig.update_xaxes(fixedrange=True, showgrid=False, hoverformat="%H:%M",
                     tickvals=[x for x, _e in horas_eje],
                     ticktext=[e for _x, e in horas_eje],
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    fig.update_yaxes(fixedrange=True, rangemode="tozero", gridcolor=GRIS_LINEA,
                     tickfont=dict(size=10, color=GRIS_TEXTO), tickformat=",d",
                     range=[0, max(ref, float(np.max(serie)) if len(serie) else 0,
                                   float(np.max(normal_)) if normal_ is not None
                                   and len(normal_) else 0) * 1.12 + 1])
    return fig


# ── La ficha ────────────────────────────────────────────────────────────────

def dibujar(dia, hora, fl, horas, *, modo, celda, al_cerrar):
    """La ficha de la celda (`dia`, `hora`).

    `fl` son las filas de `filas()` sobre la ventana del panel; `horas`, las
    del mapa en orden de servicio; `modo`, «pedido» o «cobro» (qué hora
    decide la celda); `celda`, `(venta, pax)` tal como los pinta el mapa,
    para que la cabecera diga lo mismo que el tooltip; `al_cerrar`, el
    callback del botón que la cierra."""
    dia = pd.Timestamp(dia)
    dow, h12 = dia.weekday(), (int(hora) % 12 or 12)
    peds = pedidos(fl)
    if peds is None:
        st.caption("Sin datos para esta hora.")
        return
    pc, items = de_la_celda(fl, peds, dia, hora, con_items=True)
    met = metricas(pc)
    ini, fin = intervalos(peds)
    previas = normal(fl, peds, dia, hora, ini, fin)
    v_hora, pax_hora = celda if celda else (float(pc["v"].sum()), 0.0)
    n = len(pc)

    la = "la" if h12 == 1 else "las"
    ampm = "am" if int(hora) % 24 < 12 else "pm"
    verbo = "abiertos" if modo == "pedido" else "con cobro"
    sub = (f"{n} {'pedido' if n == 1 else 'pedidos'} {verbo} entre {la} "
           f"{h12}:00 y {la} {h12}:59 {ampm}" if n else
           "Ningún pedido a esta hora")
    # columnas-internas: el título de la ficha y su botón de cerrar
    c_t, c_x = st.columns([10, 1.3], vertical_alignment="top")
    with c_t:
        st.markdown(
            f'<p class="vhh-tit">{_DIAS[dow].capitalize()} {dia.day} '
            f'{cortes.MESES_ABR_ES[dia.month - 1]} · '
            f'{cortes.etiqueta_hora(hora)}</p><p class="vhh-sub">{sub}</p>'
            f'<p class="vhh-kpis"><span>Venta<b>{_soles(v_hora)}</b></span>'
            f'<span>Pax<b>{pax_hora:,.0f}</b></span><span>Ticket<b>'
            f'{_soles2(v_hora / pax_hora) if pax_hora else "—"}</b></span></p>',
            unsafe_allow_html=True)
    with c_x:
        st.button("Cerrar", key="vh_foco_cerrar", icon=":material/close:",
                  on_click=al_cerrar, use_container_width=True)

    raros = []
    if n:
        _vi = float(pc.loc[pc["vi"], "v"].sum())
        _ev = float(pc.loc[pc["ev"] & ~pc["vi"], "v"].sum())
        if _vi > 0:
            raros.append(f"{_soles(_vi)} de Venta Interna, que no tiene "
                         "personas ni ocupa mesa")
        if _ev > 0:
            raros.append(f"{_soles(_ev)} de Eventos")
    if raros:
        st.markdown(
            f'<div class="vhh-aviso">Esta hora incluye {" y ".join(raros)}. '
            'El interruptor «Venta Interna y Eventos» los saca del mapa.'
            '</div>', unsafe_allow_html=True)

    t0, t1, h0, h1 = ventana_servicio(dia, horas, hora)
    conc = pico(ini, fin, h0, h1)
    salon = st.session_state.get(_K_SALON_VALOR) or 0

    # columnas-internas: lo normal y las cuentas por mesa, como el mockup
    c_a, c_b = st.columns([5, 7], gap="large")
    with c_a:
        st.markdown(_html_normal(v_hora, previas, dow, hora),
                    unsafe_allow_html=True)
    with c_b:
        st.markdown(_html_mesa(met, previas, v_hora, conc, dow, hora, n),
                    unsafe_allow_html=True)
        salon = st.number_input(
            "Mesas del salón (opcional)", min_value=0, max_value=300, step=1,
            value=int(salon), key=_K_SALON,
            help="Si lo escribes, «mesas a la vez» pasa a ser la ocupación. "
                 "Sin este dato, la referencia es lo más que se vio abierto "
                 "en las semanas cargadas.")
        st.session_state[_K_SALON_VALOR] = int(salon or 0)
        if salon:
            st.markdown(
                f'<p class="vhh-nota">Ocupación en la hora: <b>{conc} de '
                f'{int(salon)}</b> mesas ({100 * conc / salon:,.0f}%) · venta '
                f'por mesa del salón: <b>{_soles(v_hora / salon)}</b>.</p>',
                unsafe_allow_html=True)

    # columnas-internas: la línea de mesas abiertas y quién atendió
    c_c, c_d = st.columns([7, 5], gap="large")
    with c_c:
        t, serie = linea(ini, fin, t0, t1)
        nor = tipica(ini, fin, t0, t1) if len(ini) else None
        visto = int(abiertas(ini, fin, ini).max()) if len(ini) else 0
        ref = int(salon) or visto
        desde = fl["dia"].min()
        etq_ref = (f"mesas del salón ({ref})" if salon else
                   f"lo más visto desde el {desde.day} "
                   f"{cortes.MESES_ABR_ES[desde.month - 1]} ({ref})")
        st.markdown(
            f'<p class="vhh-h3">Mesas abiertas a la vez {_info("conc")}</p>'
            '<p class="vhh-ley"><span><i class="ln"></i>este día</span>'
            f'<span><i class="ln nor"></i>un {_DIAS[dow]} normal (mediana de '
            f'8 semanas)</span><span><i class="ln ref"></i>{etq_ref}</span>'
            '</p>', unsafe_allow_html=True)
        if len(ini) and fl["abre"].notna().any():
            eje = []
            h = t0.ceil("h")
            while h <= t1:
                eje.append((h, cortes.etiqueta_hora(h.hour)))
                h += pd.Timedelta(hours=1)
            st.plotly_chart(
                _fig_abiertas(t, serie, nor, ref, h0, h1, eje),
                key="vh_hora_abiertas", use_container_width=True,
                config={"displaylogo": False, "displayModeBar": False})
            en_servicio = serie if len(serie) else np.array([0])
            i_pico = int(np.argmax(en_servicio))
            st.markdown(
                f'<p class="vhh-nota">Durante las {cortes.etiqueta_hora(hora)} '
                f'llegó a <b>{conc}</b> mesas a la vez; el pico del servicio '
                f'fue <b>{int(en_servicio[i_pico])}</b> a las '
                f'{_reloj(t[i_pico]) if len(t) else "—"}.</p>',
                unsafe_allow_html=True)
        else:
            st.caption("Sin la hora de apertura del pedido no se puede contar "
                       "cuántas mesas había a la vez.")
    with c_d:
        st.markdown(_html_meseros(pc, met), unsafe_allow_html=True)

    st.markdown(_html_pedidos(pc, items), unsafe_allow_html=True)
    st.caption("Clic en un pedido para ver lo que se pidió. Arrastrar sobre "
               "el mapa sigue armando marcas: su tabla y el detalle por grupo "
               "y plato salen debajo.")
