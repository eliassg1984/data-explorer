"""graficos.ventas_control — Ventas › «Control de pedidos» (regla #594).

Lo que pasa con los pedidos antes de la venta, que `ventas.parquet` no ve
porque arranca en el COMPROBANTE: los pedidos y los platos que se anularon,
los platos que se pasaron de una cuenta a otra, cuánto dura una mesa y
cuántas mesas hay ocupadas a cada media hora. Nació el 2026-10-03, a
pedido, después de leer tres reportes del POS —«Control de Transacciones»,
«Reporte de Ocupabilidad» y la «Liquidación de Cajero»— y cuadrarlos contra
la base: «creo que agregaría información relacionada y valiosa».

DE DÓNDE SALE. Dos parquets propios, de consultas del Sheet escritas y
probadas contra el POS ese día:

  · `pedidos.parquet` — UNA FILA POR PEDIDO (`MPEDIDO`): apertura, día
    contable, estado, mesa, mesero, adultos, el primer y el último plato,
    la precuenta, el comprobante y, si se anuló, cuándo, quién y por qué.
  · `transacciones.parquet` — UNA FILA POR PLATO ANULADO (`APEDIDO`: el
    POS saca el plato de `DPEDIDO` y lo deja ahí, con si ya se había
    enviado a cocina) O POR TRANSFERENCIA (`TPEDIDO`: de qué pedido e ítem
    a cuál).

Un dato de mesa en el parquet de ventas se repetiría en cada plato y en
cada pago (y sumarlo sin cuidado lo multiplica, x4,9 en Compras): por eso
viven aparte, cada uno con su grano.

CUATRO SUBVISTAS, una tarjeta. La tabla de la izquierda es la del Resumen
(una fila por período, un clic la despliega, «Ver detalle» filtra la lista
de la derecha); la de la derecha, la misma grilla de lectura.

  · Anulaciones — pedidos anulados por motivo (texto libre del POS, que se
    agrupa: mesa vacía, producto agotado, error de precio…) y platos
    anulados separados en lo que se corrigió al digitar (la mitad, en el
    mismo minuto) y lo que ya había salido a cocina.
  · Transferencias — cuentas divididas (al pedido recién abierto), lo que
    pasó a una cuenta que se facturó como CORTESÍA y lo movido entre mesas.
  · Tiempos — apertura → primer plato → último plato → precuenta →
    comprobante, por período y por tamaño de grupo.
  · Ocupación — un mapa día × media hora con las mesas abiertas, la foto
    del «Reporte de Ocupabilidad» con la fecha completa (el del POS compara
    sólo la hora del día y apila los días de un rango), y la venta de cada
    mesa por hora ocupada. Sin asientos: el POS no los maneja.

El día de cada pedido es el del turno (`DIA CONTABLE`) o el de apertura,
según el selector de Ventas (regla #593).
"""

from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import definicion_venta as dv
import franja_fecha
from data import cargar_rango, venta_por_turno
from tema import ACENTO, BLANCO, GRIS_TEXTO, LAVANDA_BORDE
from graficos import alturas
from graficos.base import (
    _compras_layout, preservar_widgets, scope_rerun, selector_fecha_tarjeta,
    una_vez_por_corrida,
)
from graficos.compras._comun import _UNIDAD_GRAN, _periodo_serie
from graficos.compras.semanal import _rotulo_periodo
from graficos.ventas_resumen import _fmt_dia
from tablas.ventas_control import renderizar_lista
from tablas.ventas_resumen import renderizar_dias_venta

ARCH_PEDIDOS = "pedidos.parquet"
ARCH_TRANSACCIONES = "transacciones.parquet"

_GRANOS = ("Día", "Semana", "Mes")
_SUBVISTAS = ("Anulaciones", "Transferencias", "Tiempos", "Ocupación")
_KEYS_WIDGET_CTL = ("vt_ctl_gran", "vt_ctl_sub")
"""Los controles de la vista, para que la recarga de fecha
(`st.rerun(scope="app")`) no se los lleve (regla #373)."""

PLATO_ANULADO, TRANSFERENCIA = "PLATO ANULADO", "TRANSFERENCIA"
SIN_MESA = "SIN MESA"

ESTADO_PEDIDO_ANULADO = "ANULADO"
"""El estado de un PEDIDO anulado en `pedidos.parquet` (`MPEDIDO`, código
03). No es la clase «Anulado» de `definicion_venta`, que es la de un
COMPROBANTE de `ventas.parquet` — y en `MDOCUMENTO` el 03 es POR COBRAR,
o sea venta. Es la única excepción con nombre al candado de la regla #524
(`test_definicion_venta.py`), y sólo se usa en `pedidos()` (#594)."""

_REABIERTA_MIN = 120
"""Minutos entre la apertura y el primer plato a partir de los cuales la
mesa se mide desde el primer plato: hay pedidos abiertos de noche y usados
al día siguiente (el 12-sep a las 22:21, primer plato el 13 a las 13:07)."""

_CORRECCION_MIN = 2
"""Un plato anulado hasta 2 minutos después de pedirlo, sin haber salido a
cocina, es una corrección al digitar: la mitad de los de septiembre de 2026
se anuló en el MISMO minuto."""

_NUEVA_MIN = 5
"""Una transferencia a un pedido abierto hasta 5 minutos antes es una cuenta
dividida: el POS abre el pedido nuevo y le pasa los platos."""


# ===========================================================================
# LAS CUENTAS (puras)
# ===========================================================================

def _col(df, nombre, defecto=np.nan):
    return df[nombre] if nombre in df.columns else pd.Series(defecto,
                                                              index=df.index)


def _txt(s):
    return s.astype(object).where(s.notna(), "").astype(str).str.strip()


def _fecha(s):
    return pd.to_datetime(s, errors="coerce")


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _minutos(a, b):
    """Minutos de `a` a `b`, NaN si falta alguna o si da negativo."""
    m = (b - a).dt.total_seconds() / 60
    return m.where(m >= 0)


def pedidos(df, turno=True):
    """`pedidos.parquet` con nombres cortos. El `dia` es el del turno (día
    contable) o el de apertura (regla #593)."""
    if df is None or df.empty:
        return None
    ap = _fecha(_col(df, "FECHA APERTURA"))
    dia = (_fecha(_col(df, "DIA CONTABLE")).dt.normalize() if turno
           else ap.dt.normalize())
    p = pd.DataFrame({
        "ped": _txt(_col(df, "CODIGO PEDIDO")),
        "apertura": ap,
        "dia": dia.fillna(ap.dt.normalize()),
        "estado": _txt(_col(df, "ESTADO PEDIDO")).str.upper(),
        "canal": _txt(_col(df, "CANAL VENTA")),
        "mesa": _txt(_col(df, "MESA")),
        "mesero": _txt(_col(df, "MESERO")),
        "adultos": _num(_col(df, "ADULTOS")).fillna(0.0),
        "ninos": _num(_col(df, "NINOS")).fillna(0.0),
        "primer": _fecha(_col(df, "PRIMER ITEM")),
        "ultimo": _fecha(_col(df, "ULTIMO ITEM")),
        "platos": _num(_col(df, "PLATOS")).fillna(0.0),
        "monto": _num(_col(df, "MONTO PEDIDO")).fillna(0.0),
        "monto_anulado": _num(_col(df, "MONTO ANULADO")).fillna(0.0),
        "precuenta": _fecha(_col(df, "FECHA PRECUENTA")),
        "n_precuenta": _num(_col(df, "PRECUENTAS")).fillna(0.0),
        "comp": _fecha(_col(df, "ULTIMO COMPROBANTE")),
        "f_anul": _fecha(_col(df, "FECHA ANULACION")),
        "usu_anul": _txt(_col(df, "USUARIO ANULACION")),
        "obs_anul": _txt(_col(df, "MOTIVO ANULACION")),
    }).dropna(subset=["dia"])
    p["anulado"] = p["estado"] == ESTADO_PEDIDO_ANULADO
    p["motivo"] = np.where(p["anulado"], motivo_categoria(p["obs_anul"]), "")
    return p.reset_index(drop=True)


def transacciones(df, turno=True):
    """`transacciones.parquet` con nombres cortos y los minutos entre que se
    pidió el plato y la transacción."""
    if df is None or df.empty:
        return None
    ft = _fecha(_col(df, "FECHA TRANSACCION"))
    dia = (_fecha(_col(df, "DIA CONTABLE")).dt.normalize() if turno
           else ft.dt.normalize())
    t = pd.DataFrame({
        "tipo": _txt(_col(df, "TIPO")).str.upper(),
        "ped": _txt(_col(df, "CODIGO PEDIDO")),
        "destino": _txt(_col(df, "PEDIDO DESTINO")),
        "producto": _txt(_col(df, "PRODUCTO")),
        "cant": _num(_col(df, "CANTIDAD")).fillna(0.0),
        "venta": _num(_col(df, "VENTA")).fillna(0.0),
        "f_item": _fecha(_col(df, "FECHA ITEM")),
        "f_trx": ft,
        "dia": dia.fillna(ft.dt.normalize()),
        "usuario": _txt(_col(df, "USUARIO TRANSACCION")),
        "cocina": _num(_col(df, "ENVIADO A COCINA")).fillna(0.0) > 0,
        "obs": _txt(_col(df, "OBSERVACION")),
    }).dropna(subset=["dia"])
    t["min"] = _minutos(t["f_item"], t["f_trx"])
    return t.reset_index(drop=True)


_MOTIVOS = (
    ("Mesa vacía", r"MES\w*\s*V\w*CIA|MESAVACIA"),
    ("Producto agotado", r"(?:^|\D)86(?:\D|$)"),
    ("Error de precio", r"PRECIO"),
    ("Prueba", r"PRUEBA"),
    ("Error de digitación", r"DIGITA|OPERACI|DOBLE"),
    ("Cliente cambió o canceló", r"CLIENTE"),
)
"""El motivo de un pedido anulado es texto libre (`tMotivoAnulacion` es
siempre «000»): «MESA VACIA», «MESQA VACIA», «PRODUCTO EN 86», «PRODUYCTO
EN 86», «DOBLE DIGITACION / NO SALIO»… Se agrupa por palabra, en este
orden: «POR CAMBIO DE PRECIO / NO SALIO» es un error de precio."""


def motivo_categoria(textos):
    """El motivo de cada pedido anulado, agrupado (`_MOTIVOS`); «Otro» si no
    calza y «Sin motivo» si viene vacío. Pura."""
    t = _txt(textos).str.upper()
    out = pd.Series("Otro", index=t.index, dtype=object)
    for nombre, patron in reversed(_MOTIVOS):
        out[t.str.contains(patron, regex=True)] = nombre
    out[t == ""] = "Sin motivo"
    return out


def clase_plato_anulado(t):
    """Qué fue cada plato anulado: «Ya en cocina» (se había enviado),
    «Corrección al digitar» (anulado a los `_CORRECCION_MIN` minutos o
    antes) o «Anulado después» (más tarde, sin haber salido). Pura."""
    corr = t["min"].fillna(0) <= _CORRECCION_MIN
    return pd.Series(np.where(t["cocina"], "Ya en cocina",
                              np.where(corr, "Corrección al digitar",
                                       "Anulado después")),
                     index=t.index)


def tipo_transferencia(t, p, cortesias=frozenset()):
    """Qué fue cada transferencia: «A cortesía» si el pedido de destino se
    facturó como cortesía, «Cuenta dividida» si el destino se abrió hasta
    `_NUEVA_MIN` minutos antes, y si no «Entre mesas». Pura."""
    ap = t["destino"].map(p.set_index("ped")["apertura"]
                          if p is not None and not p.empty
                          else pd.Series(dtype="datetime64[ns]"))
    nueva = ap.notna() & (ap >= t["f_trx"] - pd.Timedelta(minutes=_NUEVA_MIN))
    cort = t["destino"].isin(set(cortesias))
    return pd.Series(np.where(cort, "A cortesía",
                              np.where(nueva, "Cuenta dividida",
                                       "Entre mesas")),
                     index=t.index)


def tiempos(p):
    """Las mesas que se cobraron, con sus tramos en minutos: `espera`
    (apertura → primer plato), `comida` (primero → último), `sobremesa`
    (último plato → precuenta), `cobro` (precuenta → comprobante) y `total`.

    Sin anulados, sin pedidos «Sin Mesa» (Rappi, venta interna) y sin los
    que no tienen comprobante. Una mesa abierta más de `_REABIERTA_MIN`
    minutos antes de su primer plato se mide desde el primer plato. Pura."""
    if p is None or p.empty:
        return None
    b = p[~p["anulado"] & p["comp"].notna() & (p["mesa"] != "")
          & (p["mesa"].str.upper() != SIN_MESA)].copy()
    if b.empty:
        return None
    espera = (b["primer"] - b["apertura"]).dt.total_seconds() / 60
    b["inicio"] = b["apertura"].where(~(espera > _REABIERTA_MIN), b["primer"])
    b["espera"] = _minutos(b["inicio"], b["primer"])
    b["comida"] = _minutos(b["primer"], b["ultimo"])
    b["sobremesa"] = _minutos(b["ultimo"], b["precuenta"])
    b["cobro"] = _minutos(b["precuenta"], b["comp"])
    b["total"] = _minutos(b["inicio"], b["comp"])
    b["servicio"] = np.where(b["inicio"].dt.hour < 17, "Almuerzo", "Cena")
    return b[b["total"].notna()].reset_index(drop=True)


_GRUPOS = ((1, 1, "1"), (2, 2, "2"), (3, 4, "3–4"), (5, 6, "5–6"),
           (7, 10_000, "7 o más"))


def grupo_de(adultos):
    """«1», «2», «3–4», «5–6», «7 o más»; «Sin dato» con 0 adultos. Pura."""
    a = _num(adultos).fillna(0)
    out = pd.Series("Sin dato", index=a.index, dtype=object)
    for lo, hi, nombre in _GRUPOS:
        out[(a >= lo) & (a <= hi)] = nombre
    return out


_PRIMER_SLOT_MIN = 12 * 60
_N_SLOTS = 28
"""Las fotos de la ocupación: cada media hora de las 12:00 a la 01:30 del
día siguiente (el día es el del pedido: una mesa de las 22:00 cobrada a las
00:25 sigue en su día)."""


def etiquetas_slots():
    return [f"{((_PRIMER_SLOT_MIN + 30 * i) // 60) % 24:02d}:"
            f"{(_PRIMER_SLOT_MIN + 30 * i) % 60:02d}" for i in range(_N_SLOTS)]


def ocupacion(b, dias):
    """Mesas abiertas en cada foto de media hora: una matriz `len(dias) ×
    _N_SLOTS`. Una mesa está en la foto de las H si se abrió a las H o antes
    y su último comprobante es de las H o después — el criterio del
    «Reporte de Ocupabilidad» del POS (`spRep_Ocupabilidad`), pero con la
    fecha entera: el del POS compara sólo la hora del día. Pura."""
    z = np.zeros((len(dias), _N_SLOTS))
    if b is None or b.empty or not len(dias):
        return z
    fila = {pd.Timestamp(d): i for i, d in enumerate(dias)}
    i_dia = b["dia"].map(fila)
    ok = i_dia.notna()
    b, i_dia = b[ok], i_dia[ok].astype(int)
    base = b["dia"] + pd.Timedelta(minutes=_PRIMER_SLOT_MIN)
    desde = np.ceil((b["inicio"] - base).dt.total_seconds() / 1800)
    hasta = np.floor((b["comp"] - base).dt.total_seconds() / 1800)
    desde = desde.clip(lower=0).astype(int).to_numpy()
    hasta = hasta.clip(upper=_N_SLOTS - 1).astype(int).to_numpy()
    for f, a, h in zip(i_dia.to_numpy(), desde, hasta):
        if h >= a:
            z[f, a:h + 1] += 1
    return z


def por_mesa(b):
    """Cada mesa: usos, personas, consumo, horas ocupada, consumo por hora
    ocupada y la duración típica. Pura."""
    if b is None or b.empty:
        return pd.DataFrame(columns=["mesa", "usos", "personas", "consumo",
                                     "minutos", "x_hora", "mediana"])
    g = (b.groupby("mesa", as_index=False)
          .agg(usos=("ped", "size"), personas=("adultos", "sum"),
               consumo=("monto", "sum"), minutos=("total", "sum"),
               mediana=("total", "median")))
    g["x_hora"] = g["consumo"] / (g["minutos"] / 60).replace(0, np.nan)
    return g.sort_values("consumo", ascending=False).reset_index(drop=True)


# ===========================================================================
# LA VISTA
# ===========================================================================

def _rango():
    """`(ini, fin)` del rango de Ventas (el de la fecha de arriba)."""
    ctx = franja_fecha.contexto()
    r = st.session_state.get(ctx["k_rango"]) if ctx else None
    if isinstance(r, (tuple, list)) and len(r) == 2 and all(r):
        return min(r), max(r)
    hoy = pd.Timestamp.today().date()
    return hoy.replace(day=1), hoy


def _cargar(ini, fin, turno, canales):
    """Los dos parquets del rango, preparados. Por día contable o por la
    fecha propia de cada uno, según el selector de Ventas (#593). `canales`
    son los del filtro de Ventas: se aplican a los pedidos, y a las
    transacciones por su pedido."""
    p = pedidos(cargar_rango(ARCH_PEDIDOS,
                             "DIA CONTABLE" if turno else "FECHA APERTURA",
                             ini, fin, turno=False), turno)
    t = transacciones(cargar_rango(ARCH_TRANSACCIONES,
                                   "DIA CONTABLE" if turno
                                   else "FECHA TRANSACCION",
                                   ini, fin, turno=False), turno)
    if canales and p is not None:
        p = p[p["canal"].isin(canales)]
        if t is not None:
            t = t[t["ped"].isin(set(p["ped"]))]
    for x in (p, t):
        if x is not None:
            x.drop(x[(x["dia"] < pd.Timestamp(ini))
                     | (x["dia"] > pd.Timestamp(fin))].index, inplace=True)
    return p, t


def _min_txt(m):
    """«45 min», «1 h 33», «—»."""
    if m is None or pd.isna(m):
        return "—"
    m = int(round(m))
    return f"{m} min" if m < 60 else f"{m // 60} h {m % 60:02d}"


def _soles(v):
    return f"S/ {v:,.0f}"


def _k(rotulo, valor, sub="", tip="", clase=""):
    return (f'<div class="vt-kpi {clase}" title="{escape(tip or rotulo)}">'
            f'<span class="vt-kpi-rot">{escape(rotulo)}</span>'
            f'<span class="vt-kpi-val">{escape(valor)}'
            f'<span class="vt-kpi-sub">{escape(sub)}</span></span></div>')


def _html_cab(p, t, b, pico):
    """El título y la fila de KPI: lo de todo el rango, sin importar la
    subvista."""
    n = len(p) if p is not None else 0
    anul = p[p["anulado"]] if n else p
    pa = t[t["tipo"] == PLATO_ANULADO] if t is not None else None
    tr = t[t["tipo"] == TRANSFERENCIA] if t is not None else None
    partes = [_k("Pedidos", f"{n:,}",
                 f"{len(anul):,} anulados" if n else "", clase="vt-kpi-total",
                 tip=f"{n:,} pedidos abiertos en el rango; {len(anul):,} se "
                     f"anularon enteros (S/ {anul['monto_anulado'].sum():,.0f} "
                     "en platos)" if n else "Pedidos abiertos en el rango")]
    if pa is not None:
        _c = pa[pa["cocina"]]
        partes.append(_k("Platos anulados", f"{len(pa):,}",
                         _soles(pa["venta"].sum()),
                         tip=f"{len(pa):,} platos anulados por "
                             f"S/ {pa['venta'].sum():,.2f}; {len(_c):,} ya "
                             f"habían salido a cocina (S/ "
                             f"{_c['venta'].sum():,.2f})"))
    if tr is not None:
        _ac = tr[tr["clase"] == "A cortesía"]
        partes.append(_k("Transferencias", f"{len(tr):,}",
                         _soles(tr["venta"].sum()),
                         tip=f"{len(tr):,} platos pasados de una cuenta a "
                             f"otra; {len(_ac):,} a una cuenta de cortesía "
                             f"(S/ {_ac['venta'].sum():,.2f})"))
    if b is not None and not b.empty:
        partes.append(_k("Mesa", _min_txt(b["total"].median()),
                         f"sobremesa {_min_txt(b['sobremesa'].median())}",
                         tip="Mediana de la apertura al comprobante; la "
                             "sobremesa va del último plato a la precuenta"))
    if pico:
        partes.append(_k("Pico", f"{pico[0]:.0f} de {pico[1]} mesas", pico[2],
                         tip="El momento con más mesas abiertas del rango, "
                             "sobre las mesas que se usaron en él"))
    return ('<div class="vt-cab"><span class="vt-cab-tit">Control de pedidos'
            '</span><div class="vt-kpis">' + "".join(partes) + "</div></div>")


def _bloque(titulo, grande, fino=""):
    return (f'<div class="vr-b"><span class="vr-cab"><span class="vr-h">'
            f'{escape(titulo)}</span><span class="vr-g">{escape(grande)}'
            f'</span></span><span class="vr-f">{escape(fino)}</span></div>')


def _top(serie, n=3, fmt=lambda v: f"{v:,.0f}"):
    """«Mesa vacía 12 · Producto agotado 4 · …» de una Series ordenada."""
    s = serie[serie > 0].sort_values(ascending=False).head(n)
    return " · ".join(f"{k} {fmt(v)}" for k, v in s.items()) or "—"


def _boton(nombre):
    return (f'<div class="vr-pie"><button class="vr-ver" type="button">Ver '
            f'el detalle de {escape(nombre)} →</button></div>')


def _rotulos(claves, gran, rango=None):
    if gran == "Día":
        return [_fmt_dia(pd.Timestamp(c)) for c in claves]
    # Con `rango`, una semana cortada se nombra por sus días (regla #619).
    return [_rotulo_periodo(c, gran, rango)[1] for c in claves]


def _celda(r, campo, valor, texto, nota=""):
    r[campo] = valor
    r[f"__t_{campo}"] = texto
    if nota:
        r[f"__v_{campo}"], r[f"__vc_{campo}"] = nota, "vr-neutro"


def _filas_anulaciones(p, t, claves, fila):
    pa = t[t["tipo"] == PLATO_ANULADO]
    filas = []
    for c, nom in zip(claves, fila):
        pp, x = p[p["clave"] == c], pa[pa["clave"] == c]
        an = pp[pp["anulado"]]
        coc = x[x["cocina"]]
        consumo = float(pp["monto"].sum())
        anulado = float(x["venta"].sum() + an["monto_anulado"].sum())
        r = {"periodo": nom, "__tip": nom, "__id": c, "__clave": c}
        r["pedidos"] = len(pp)
        _celda(r, "ped_anul", len(an), f"{len(an):,}",
               _soles(an["monto_anulado"].sum()) if len(an) else "")
        _celda(r, "pl_anul", len(x), f"{len(x):,}",
               _soles(x["venta"].sum()) if len(x) else "")
        _celda(r, "pl_cocina", len(coc), f"{len(coc):,}" if len(coc) else "—",
               _soles(coc["venta"].sum()) if len(coc) else "")
        _pct = anulado / (consumo + anulado) if consumo + anulado else 0.0
        _celda(r, "pct", round(_pct, 4), f"{_pct:.1%}")
        r["__html"] = (
            _bloque("Pedidos anulados", f"{len(an):,}",
                    _top(an.groupby("motivo").size()))
            + _bloque("Platos anulados", f"{len(x):,}",
                      _top(x.groupby("clase").size()))
            + _bloque("Quién anula", "",
                      _top(pd.concat([an["usu_anul"], x["usuario"]])
                           .replace("", "—").value_counts()))
            + _bloque("Platos más anulados", "",
                      _top(x.groupby("producto")["venta"].sum(), 3,
                           lambda v: f"S/ {v:,.0f}"))
            + _boton(nom))
        filas.append(r)
    return filas


def _filas_transferencias(t, claves, fila):
    tr = t[t["tipo"] == TRANSFERENCIA]
    filas = []
    for c, nom in zip(claves, fila):
        x = tr[tr["clave"] == c]
        r = {"periodo": nom, "__tip": nom, "__id": c, "__clave": c}
        r["n_tr"] = len(x)
        r["s_tr"] = round(float(x["venta"].sum()), 2)
        r["n_div"] = int((x["clase"] == "Cuenta dividida").sum())
        _ac = x[x["clase"] == "A cortesía"]
        _celda(r, "cort", len(_ac), f"{len(_ac):,}",
               _soles(_ac["venta"].sum()) if len(_ac) else "")
        r["n_mesa"] = int((x["clase"] == "Entre mesas").sum())
        r["__html"] = (
            _bloque("A cortesía", _soles(_ac["venta"].sum()),
                    _top(_ac.groupby("producto").size()))
            + _bloque("Quién transfiere", "",
                      _top(x["usuario"].replace("", "—").value_counts()))
            + _bloque("Lo más movido", "", _top(x["producto"].value_counts()))
            + _boton(nom))
        filas.append(r)
    return filas


_TRAMOS = (("espera", "1er plato"), ("comida", "Comida"),
           ("sobremesa", "Sobremesa"), ("cobro", "Cobro"),
           ("total", "Total"))


def _filas_tiempos(b, claves, fila):
    filas = []
    for c, nom in zip(claves, fila):
        x = b[b["clave"] == c] if b is not None else b
        r = {"periodo": nom, "__tip": nom, "__id": c, "__clave": c}
        r["mesas"] = 0 if x is None else len(x)
        for campo, _ in _TRAMOS:
            m = x[campo].median() if x is not None and len(x) else np.nan
            _celda(r, f"t_{campo}", None if pd.isna(m) else round(float(m), 1),
                   _min_txt(m))
        if x is not None and len(x):
            _srv = x.groupby("servicio")["total"].median()
            r["__html"] = (
                _bloque("Por servicio", "",
                        " · ".join(f"{k} {_min_txt(v)}" for k, v in
                                   _srv.items()))
                + _bloque("Precuentas", f"{(x['n_precuenta'] > 1).sum():,}",
                          "mesas con más de una precuenta")
                + _bloque("La más larga", _min_txt(x["total"].max()),
                          f"mesa {x.loc[x['total'].idxmax(), 'mesa']}")
                + _boton(nom))
        filas.append(r)
    return filas


_COLS = {
    "Anulaciones": [
        ("pedidos", "Pedidos", "entero", 72, "Pedidos abiertos en el período"),
        ("ped_anul", "Ped. anulados", "celda", 118,
         "Pedidos anulados enteros y lo que llevaban"),
        ("pl_anul", "Platos anulados", "celda", 122,
         "Platos anulados en pedidos que siguieron, y lo que valían"),
        ("pl_cocina", "Ya en cocina", "celda", 104,
         "De esos, los que ya se habían enviado a cocina: lo que se pierde"),
        ("pct", "% anulado", "celda", 88,
         "Lo anulado (platos y pedidos) ÷ lo pedido en el período"),
    ],
    "Transferencias": [
        ("n_tr", "Platos", "entero", 68, "Platos pasados de una cuenta a otra"),
        ("s_tr", "Valor", "soles0", 88, "Lo que valían"),
        ("n_div", "Cuenta dividida", "entero", 116,
         "Pasados a un pedido recién abierto: la cuenta se partió"),
        ("cort", "A cortesía", "celda", 112,
         "Pasados a una cuenta que se facturó como cortesía"),
        ("n_mesa", "Entre mesas", "entero", 96,
         "Pasados a otro pedido que ya estaba abierto"),
    ],
    "Tiempos": [
        ("mesas", "Mesas", "entero", 64, "Mesas cobradas en el período"),
        ("t_espera", "1er plato", "celda", 80,
         "De la apertura al primer plato (mediana)"),
        ("t_comida", "Comida", "celda", 80,
         "Del primer al último plato (mediana)"),
        ("t_sobremesa", "Sobremesa", "celda", 92,
         "Del último plato a la precuenta (mediana)"),
        ("t_cobro", "Cobro", "celda", 72,
         "De la precuenta al comprobante (mediana)"),
        ("t_total", "Total", "celda", 80,
         "De la apertura al comprobante (mediana)"),
    ],
}

_AYUDA = {
    "Anulaciones": "Pedidos y platos anulados. Un plato anulado en el mismo "
                   "minuto, sin salir a cocina, es una corrección al digitar.",
    "Transferencias": "Platos pasados de una cuenta a otra: cuentas "
                      "divididas, a cortesía y entre mesas.",
    "Tiempos": "Medianas por mesa. Sin Rappi ni venta interna (sin mesa).",
    "Ocupación": "Mesas abiertas a cada media hora, sobre las que se usaron "
                 "en el rango. El POS no registra asientos.",
}


def _lista(sub, p, t, b, foco):
    """La grilla de la derecha: lo del período en foco o del rango."""
    if sub == "Anulaciones":
        pa = t[t["tipo"] == PLATO_ANULADO]
        an = p[p["anulado"]]
        if foco is not None:
            pa, an = pa[pa["clave"] == foco], an[an["clave"] == foco]
        tp = pd.concat([
            pd.DataFrame({
                "hora": pa["f_trx"].dt.strftime("%Y-%m-%d %H:%M"),
                "que": pa["producto"], "venta": pa["venta"].round(2),
                "usuario": pa["usuario"].replace("", "—"),
                "motivo": np.where(pa["obs"] != "", pa["clase"] + " · "
                                   + pa["obs"], pa["clase"])}),
            pd.DataFrame({
                "hora": an["f_anul"].fillna(an["apertura"])
                          .dt.strftime("%Y-%m-%d %H:%M"),
                "que": "Pedido entero · mesa " + an["mesa"].replace("", "—"),
                "venta": an["monto_anulado"].round(2),
                "usuario": an["usu_anul"].replace("", "—"),
                "motivo": an["motivo"] + np.where(an["obs_anul"] != "",
                                                  " · " + an["obs_anul"], "")}),
        ], ignore_index=True).sort_values(["venta", "hora"],
                                          ascending=[False, False])
        cols = [("hora", "Hora", "hora", 92, "Cuándo se anuló"),
                ("que", "Qué", "texto", 130, "El plato, o el pedido entero"),
                ("venta", "Valor", "soles", 84, "Lo que valía"),
                ("usuario", "Quién", "texto", 80, "Quién lo anuló"),
                ("motivo", "Motivo", "texto", 130,
                 "Agrupado; el texto del POS va después del punto")]
        total = {"hora": f"{len(tp):,}", "venta": f"S/ {tp['venta'].sum():,.0f}"}
        return tp, cols, total
    if sub == "Transferencias":
        tr = t[t["tipo"] == TRANSFERENCIA]
        if foco is not None:
            tr = tr[tr["clave"] == foco]
        tp = pd.DataFrame({
            "hora": tr["f_trx"].dt.strftime("%Y-%m-%d %H:%M"),
            "que": tr["producto"], "venta": tr["venta"].round(2),
            "clase": tr["clase"],
            "__tip_que": (tr["producto"] + " · del pedido " + tr["ped"]
                          + " al " + tr["destino"]),
            "usuario": tr["usuario"].replace("", "—"),
        }).sort_values(["venta", "hora"], ascending=[False, False])
        cols = [("hora", "Hora", "hora", 92, "Cuándo se transfirió"),
                ("que", "Plato", "texto", 130,
                 "El plato transferido; con el cursor, de qué pedido a cuál"),
                ("venta", "Valor", "soles", 84, "Lo que valía"),
                ("clase", "Tipo", "texto", 112,
                 "Cuenta dividida, a cortesía o entre mesas"),
                ("usuario", "Quién", "texto", 80, "Quién lo transfirió")]
        total = {"hora": f"{len(tp):,}", "venta": f"S/ {tp['venta'].sum():,.0f}"}
        return tp, cols, total
    if b is None or b.empty:
        return None, [], None
    if sub == "Tiempos":
        x = b if foco is None else b[b["clave"] == foco]
        x = x.assign(grupo=grupo_de(x["adultos"]))
        g = (x.groupby("grupo")
              .agg(mesas=("ped", "size"), total=("total", "median"),
                   sobremesa=("sobremesa", "median"), consumo=("monto", "sum"),
                   personas=("adultos", "sum")))
        orden = [n for _, _, n in _GRUPOS] + ["Sin dato"]
        g = g.reindex([o for o in orden if o in g.index])
        tp = pd.DataFrame({
            "grupo": g.index, "mesas": g["mesas"].to_numpy(),
            "total": g["total"].round(1).to_numpy(),
            "sobremesa": g["sobremesa"].round(1).to_numpy(),
            "x_mesa": (g["consumo"] / g["mesas"]).round(2).to_numpy(),
            "x_persona": (g["consumo"] / g["personas"].replace(0, np.nan))
                         .round(2).to_numpy(),
        })
        cols = [("grupo", "Personas", "texto", 80, "Adultos de la mesa"),
                ("mesas", "Mesas", "entero", 64, "Mesas cobradas"),
                ("total", "Total", "minutos", 80,
                 "De la apertura al comprobante (mediana)"),
                ("sobremesa", "Sobremesa", "minutos", 96,
                 "Del último plato a la precuenta (mediana)"),
                ("x_mesa", "Por mesa", "soles0", 92, "Consumo por mesa"),
                ("x_persona", "Por persona", "soles0", 96,
                 "Consumo por adulto")]
        total = {"grupo": "Total", "mesas": f"{len(x):,}",
                 "total": f"{_min_txt(x['total'].median())}",
                 "sobremesa": f"{_min_txt(x['sobremesa'].median())}"}
        return tp, cols, total
    # Ocupación: las mesas
    m = por_mesa(b if foco is None else b[b["clave"] == foco])
    tp = pd.DataFrame({
        "mesa": m["mesa"], "usos": m["usos"],
        "personas": m["personas"], "consumo": m["consumo"].round(2),
        "x_hora": m["x_hora"].round(2), "mediana": m["mediana"].round(1)})
    cols = [("mesa", "Mesa", "texto", 70, "La mesa del POS"),
            ("usos", "Usos", "entero", 64, "Pedidos cobrados en ella"),
            ("personas", "Personas", "entero", 84, "Adultos sentados"),
            ("consumo", "Consumo", "soles0", 96, "Lo pedido en ella"),
            ("x_hora", "Por hora", "soles0", 88,
             "Consumo por hora ocupada"),
            ("mediana", "Dura", "minutos", 80, "Duración típica (mediana)")]
    total = {"mesa": f"{len(m):,}", "usos": f"{m['usos'].sum():,}",
             "consumo": f"S/ {m['consumo'].sum():,.0f}"}
    return tp, cols, total


def _total_periodos(sub, p, t, b, n, uni):
    """La fila TOTAL de la tabla por período: las sumas (o las medianas,
    en Tiempos) del rango entero, ya escritas."""
    tot = {"__id": "__total", "periodo": f"Total · {n:,} {uni}"}
    if sub == "Anulaciones":
        pa = t[t["tipo"] == PLATO_ANULADO]
        an = p[p["anulado"]]
        coc = pa[pa["cocina"]]
        anulado = float(pa["venta"].sum() + an["monto_anulado"].sum())
        consumo = float(p["monto"].sum())
        tot.update(pedidos=f"{len(p):,}",
                   ped_anul=f"{len(an):,} · {_soles(an['monto_anulado'].sum())}",
                   pl_anul=f"{len(pa):,} · {_soles(pa['venta'].sum())}",
                   pl_cocina=f"{len(coc):,}",
                   pct=f"{anulado / (consumo + anulado):.1%}"
                   if consumo + anulado else "—")
    elif sub == "Transferencias":
        tr = t[t["tipo"] == TRANSFERENCIA]
        _ac = tr[tr["clase"] == "A cortesía"]
        tot.update(n_tr=f"{len(tr):,}", s_tr=_soles(tr["venta"].sum()),
                   n_div=f"{int((tr['clase'] == 'Cuenta dividida').sum()):,}",
                   cort=f"{len(_ac):,} · {_soles(_ac['venta'].sum())}",
                   n_mesa=f"{int((tr['clase'] == 'Entre mesas').sum()):,}")
    elif b is not None and not b.empty:
        tot["mesas"] = f"{len(b):,}"
        for campo, _ in _TRAMOS:
            tot[f"t_{campo}"] = _min_txt(b[campo].median())
    return tot


def _fig_ocupacion(z, dias, n_mesas):
    """El mapa día × media hora con las mesas abiertas."""
    filas = [_fmt_dia(pd.Timestamp(d)) for d in dias]
    slots = etiquetas_slots()
    hover = [[f"{filas[i]} {slots[j]} · {z[i, j]:.0f} de {n_mesas} mesas"
              for j in range(z.shape[1])] for i in range(z.shape[0])]
    fig = go.Figure(go.Heatmap(
        z=z, x=slots, y=filas, colorscale=[[0, BLANCO], [0.2, LAVANDA_BORDE],
                                            [1, ACENTO]],
        zmin=0, zmax=max(float(z.max()), 1.0), xgap=1, ygap=1,
        text=hover, hoverinfo="text", showscale=False))
    _compras_layout(fig, alturas.VENTAS_RESUMEN_TABLA)
    fig.update_layout(margin=dict(l=4, r=4, t=4, b=4))
    fig.update_xaxes(type="category", tickfont=dict(size=10, color=GRIS_TEXTO),
                     showgrid=False, tickangle=0, dtick=2)
    fig.update_yaxes(type="category", autorange="reversed", showgrid=False,
                     showticklabels=True,
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    return fig


@una_vez_por_corrida
@st.fragment
def _ventas_control(cortesias=frozenset(), canales=()):
    """«Control de pedidos». `cortesias`: los pedidos que se facturaron como
    cortesía en el rango (de `ventas.parquet`), para reconocer lo que se
    pasó a una cuenta de cortesía; `canales`, el filtro de Ventas."""
    ss = st.session_state
    if ss.pop("vt_ctl_fecha_flag", False):
        preservar_widgets(_KEYS_WIDGET_CTL)
        st.rerun(scope="app")

    ini, fin = _rango()
    turno = venta_por_turno()
    with st.container(border=True, key="ajuste_graf_card_izq_ventas_control"):
        cab = st.container(key="vt_ctl_cabfila")
        # columnas-internas: la granularidad, la subvista y la fecha
        c1, c2, c3 = st.columns([1.1, 2.6, 1.1], vertical_alignment="center")
        with c1:
            gran = st.segmented_control(
                "Agrupar por", _GRANOS, default="Día", required=True,
                key="vt_ctl_gran", label_visibility="collapsed") or "Día"
        with c2:
            sub = st.segmented_control(
                "Qué mirar", _SUBVISTAS, default=_SUBVISTAS[0], required=True,
                key="vt_ctl_sub", label_visibility="collapsed") or _SUBVISTAS[0]
        with c3:
            # «vt_ctlf» y no «vt_ctl»: el selector arma SUS keys con ese
            # prefijo (`_escala`, `_fila`…) y no pueden chocar con las de la
            # vista (CLAUDE.md, regla #527).
            selector_fecha_tarjeta("vt_ctlf", "vt_ctl_fecha_flag",
                                   categoria=None)
        with st.spinner("Trayendo los pedidos…"):
            p, t = _cargar(ini, fin, turno, canales)
        if p is None or p.empty:
            with cab:
                st.markdown('<div class="vt-cab"><span class="vt-cab-tit">'
                            'Control de pedidos</span></div>',
                            unsafe_allow_html=True)
            st.info("No hay pedidos en este rango (o falta `pedidos.parquet` "
                    "en R2).")
            return
        if t is None:
            t = pd.DataFrame(columns=["tipo", "ped", "destino", "producto",
                                      "venta", "f_item", "f_trx", "dia",
                                      "usuario", "cocina", "obs", "min"])
        p = p.assign(clave=_periodo_serie(p["dia"], gran))
        t = t.assign(clave=_periodo_serie(t["dia"], gran) if len(t) else "")
        t["clase"] = ""
        _pa = t["tipo"] == PLATO_ANULADO
        if _pa.any():
            t.loc[_pa, "clase"] = clase_plato_anulado(t[_pa])
        _tr = t["tipo"] == TRANSFERENCIA
        if _tr.any():
            t.loc[_tr, "clase"] = tipo_transferencia(t[_tr], p, cortesias)
        b = tiempos(p)
        if b is not None:
            b = b.assign(clave=_periodo_serie(b["dia"], gran))

        dias = pd.date_range(ini, fin, freq="D")
        z = ocupacion(b, dias)
        n_mesas = int(b["mesa"].nunique()) if b is not None else 0
        pico = None
        if z.size and z.max() > 0:
            i, j = np.unravel_index(int(z.argmax()), z.shape)
            pico = (z[i, j], n_mesas,
                    f"{_fmt_dia(dias[i])} {etiquetas_slots()[j]}")
        with cab:
            st.markdown(_html_cab(p, t, b, pico), unsafe_allow_html=True)

        claves = sorted(set(p["clave"]))
        fila = _rotulos(claves, gran, (pd.Timestamp(ini).date(),
                                       pd.Timestamp(fin).date()))
        foco = ss.get("vt_ctl_foco")
        if foco not in set(claves) or ss.get("vt_ctl_foco_ctx") != (gran, ini,
                                                                    fin):
            foco = None
        n_res = ss.get("vt_ctl_nres", 0)

        # columnas-internas: la tabla por período | el detalle
        izq, der = st.columns([1.2, 1], gap="small")
        with izq:
            if sub == "Ocupación":
                if b is None or b.empty:
                    st.info("No hay mesas cobradas en este rango.")
                else:
                    st.plotly_chart(_fig_ocupacion(z, dias, n_mesas),
                                    key=f"vt_ctl_mapa_{gran}",
                                    config={"displayModeBar": False})
            else:
                if sub == "Anulaciones":
                    filas = _filas_anulaciones(p, t, claves, fila)
                elif sub == "Transferencias":
                    filas = _filas_transferencias(t, claves, fila)
                else:
                    filas = _filas_tiempos(b, claves, fila)
                tp = pd.DataFrame(filas)
                tp["__sel"] = tp["__clave"] == foco
                uni = _UNIDAD_GRAN[gran][0 if len(claves) == 1 else 1]
                clic = renderizar_dias_venta(
                    tp, altura=alturas.VENTAS_RESUMEN_TABLA,
                    columnas=_COLS[sub],
                    key=f"vt_ctl_tabla_{sub}_{gran}_{n_res}",
                    rotulo_periodo=gran,
                    total=_total_periodos(sub, p, t, b, len(claves), uni))
                if clic in set(claves) and clic != foco:
                    ss["vt_ctl_foco"] = clic
                    ss["vt_ctl_foco_ctx"] = (gran, ini, fin)
                    ss["vt_ctl_nres"] = n_res + 1
                    st.rerun(scope=scope_rerun())
        with der:
            tp, cols, total = _lista(sub, p, t, b, foco)
            if foco is not None:
                _nom = fila[claves.index(foco)]
                st.button(f"Detalle de {_nom} · ver todo el rango",
                          key="vt_ctl_soltar", icon=":material/close:",
                          on_click=lambda: (ss.update(vt_ctl_foco=None,
                                                      vt_ctl_nres=n_res + 1)))
            if tp is None or tp.empty:
                st.caption("Nada que mostrar.")
            else:
                renderizar_lista(tp, alturas.VENTAS_RESUMEN_TABLA,
                                 key=f"vt_ctl_lista_{sub}_{gran}_{n_res}",
                                 columnas=cols, total=total)
        st.caption(f"**{franja_fecha.fmt_rango_es(ini, fin)}** · "
                   f"{'por día del turno' if turno else 'por fecha'} · "
                   + _AYUDA[sub])


def cortesias_de(d_todo):
    """Los pedidos que se facturaron como cortesía, de las filas de ventas
    con todas las clases (`CLASE VENTA`)."""
    if d_todo is None or d_todo.empty or dv.CLASE not in d_todo.columns:
        return frozenset()
    c = dv.columna(d_todo, "CODIGO PEDIDO DDOCUMENTO")
    if c is None:
        return frozenset()
    x = d_todo.loc[d_todo[dv.CLASE] == dv.CORTESIA, c]
    return frozenset(_txt(x)[lambda s: s != ""])

