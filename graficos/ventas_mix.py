"""
graficos.ventas_mix — vista «Mix de carta» del dashboard de Ventas: la venta
por período partida por lo que se vendió —Grupo › Sub Grupo › Producto—, con
un mapa de calor debajo y el Detalle de qué movió cada período.

Nació el 2026-09-25 de un mockup aprobado (regla #527) y ese mismo día se
fueron dos vistas: «Venta por día» (su lectura la da el Resumen ejecutivo en
granularidad Día) y «Familia/Subfamilia semanal» (la barra semanal partida
por familia, top 8 y sin bajar de nivel: ésta es esa barra con drill).

EL MISMO ESQUELETO QUE EL RESUMEN EJECUTIVO, a propósito: granularidad, una
barra por período con su total y su variación encima (el plan de etiquetas
de «Compras por período»), y el clic en una barra abre el Detalle. Cambia de
qué está hecha la barra: por Grupo en vez de por Canal, y un nombre de la
columna de la derecha —o una fila de la tabla— baja un nivel.

TRES COSAS QUE NO SON OBVIAS:

  · TODOS LOS CLICS SE LEEN ARRIBA DE TODO (regla #399). La barra, las filas
    de la tabla, las barras del Detalle y la tabla de productos son widgets
    cuya selección persiste entre corridas: cada uno lleva un contador en la
    key, y el clic de la corrida anterior se lee —y el contador sube— antes
    de dibujar nada. Leído abajo, donde se dibuja cada uno, el drill quedaba
    una corrida atrasado: el gráfico ya se había dibujado con el nivel viejo.
    Para eso cada widget deja anotado en `session_state` qué había en cada
    fila la última vez que se dibujó.
  · EL NIVEL SE GUARDA POR NOMBRE (`vt_mix_ruta`), no por posición: un chip
    de la franja cambia qué grupos hay, y una posición guardada apuntaría a
    otro.
  · «RESTO» Y NO «OTROS»: en `ventas.parquet` hay un Grupo que se llama
    «Otros», y un tramo que juntara a los chicos con ese nombre se leía como
    si fuera él.
"""

from datetime import date, timedelta
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cortes import MESES_ABR_ES
from data import REPORTES
from tema import (ACENTO, AJUSTE_NEG, AJUSTE_NEG_TEXTO, AJUSTE_POS,
                  AJUSTE_POS_TEXTO, GRIS_TEXTO, LAVANDA_FONDO, PALETA_SERIES,
                  SCROLL_THUMB, TEXTO_PRINCIPAL)
from graficos import alturas
from graficos.base import (_compras_layout, _compras_truncar, _resolver,
                           preservar_widgets, selector_fecha_tarjeta)
from graficos.compras._comun import (_first_point, _limites_periodo,
                                     _periodo_serie, _variaciones)
from graficos.compras.semanal import (
    _ETQ_FUENTE, _ETQ_SEP, _LIENZO_PX, _etiqueta_en_la_punta,
    _plan_etiquetas, _rotulo_periodo,
)
from graficos.ventas_comparativo import _cargar_tramo
from graficos.ventas_resumen import (MAX_DIAS, _ATENUADO, _con_alpha,
                                     _fmt_dia, _fmt_var_venta)
from utils import fmt_k

_GRAN_OPCIONES = ("Día", "Semana", "Mes", "Año")
_GRAN_DEFAULT = "Semana"
"""Las granularidades del Resumen ejecutivo. Abre en Semana y no en Día: con
el mes corrido con que abre Ventas son cuatro o cinco barras, y una barra
diaria partida en siete tramos no se lee."""

_MEDIDAS = ("Soles", "Unidades")
_ESCALAS = ("Monto", "% del período")
_ZONA_RESUMEN, _ZONA_DETALLE = "Resumen", "Detalle"
_COMP_ANT, _COMP_AP = "Período anterior", "Año pasado"
_CAMBIO_MONTO, _CAMBIO_MIX = "Monto", "Mix (pp)"

_NIVELES = ("Grupos", "Subgrupos", "Productos")
_NIVEL_SING = ("grupo", "subgrupo", "producto")
_COL_NIVEL = ("grupo", "sub", "prod")
_TODOS = "Todos los grupos"

_MAX_TRAMOS = 7
"""Tramos con color en la barra; el resto va junto. Con 8 se muestran los 8:
juntar uno solo en «Resto (1)» es esconderlo sin ganar nada."""

_COLORES = tuple(PALETA_SERIES[:_MAX_TRAMOS])
"""Uno por tramo, en orden de venta. Su espejo CSS son `--serie-0…6`
(`estilos/_00_base.py`): pintan la muestra de cada nombre de la columna de
la derecha, que es un botón y no sabe su color."""

_COLOR_RESTO = SCROLL_THUMB
"""El gris del tramo «Resto». Su espejo es `--scroll-thumb`."""

_TOP_DETALLE = 10
_TOP_PRODUCTOS = 12
_MARGEN_ARRIBA = 14
_PIE_EJE = 26
_ANCHO_GRAFICO = 0.76
"""La parte de `_LIENZO_PX` que le queda al gráfico al lado de la columna de
navegación (`st.columns([3.3, 1])`, menos el gap)."""

_KEYS_WIDGET_MIX = ("vt_mix_gran", "vt_mix_medida", "vt_mix_escala",
                    "vt_mix_zona", "vt_mix_comp", "vt_mix_cambio",
                    "vt_mix_buscar")
"""Los controles de la vista, para que la recarga de fecha
(`st.rerun(scope="app")`) no se los lleve: mismo mecanismo que
`ventas_resumen._KEYS_WIDGET_RESUMEN` (regla #373)."""


# ===========================================================================
# LOS DATOS
# ===========================================================================

def columnas(d):
    """Las columnas que usa la vista, resueltas contra `d`. `costo` es el de
    la LÍNEA que arma `definicion_venta` (el unitario suelto daba un % de
    costo de 24 donde era 34,5: regla #524)."""
    return {
        "fecha": _resolver(d, ["Fec Reg Documento", "Fecha Registro", "FECHA"]),
        "grupo": _resolver(d, ["Grupo"]),
        "sub": _resolver(d, ["Sub Grupo", "Sub_Grupo", "Subgrupo"]),
        "prod": _resolver(d, ["Nomb Item Venta", "Nombre Producto",
                              "Producto", "Descripcion"]),
        "venta": _resolver(d, ["Venta Item Ddocumento", "Venta"]),
        "cant": _resolver(d, ["Cantidad Item Ddocumento", "Cantidad"]),
        "costo": _resolver(d, ["Costo Venta", "Costo Item Ddocumento"]),
        "neto": _resolver(d, ["Neto Total Item Ddocumento"]),
    }


def base(d, cols):
    """Una fila por ítem vendido con los tres niveles de la carta y las
    cuatro sumas, con nombres FIJOS: todo lo de abajo agrupa por columna de
    verdad y renombra por nombre (regla #481, pandas 2 contra pandas 3).

    Un nivel vacío se nombra («(sin grupo)») en vez de caerse: esa venta
    existe y tiene que sumar en algún lado."""
    def _num(col):
        if not col or col not in d.columns:
            return pd.Series(0.0, index=d.index)
        return pd.to_numeric(d[col], errors="coerce").fillna(0.0)

    def _txt(col, vacio):
        if not col or col not in d.columns:
            return pd.Series(vacio, index=d.index)
        s = d[col].astype("object")
        s = s.where(s.notna(), vacio).astype(str).str.strip()
        return s.where(s != "", vacio)

    b = pd.DataFrame({
        "fecha": pd.to_datetime(d[cols["fecha"]], errors="coerce"),
        "grupo": _txt(cols["grupo"], "(sin grupo)"),
        "sub": _txt(cols["sub"], "(sin subgrupo)"),
        "prod": _txt(cols["prod"], "(sin nombre)"),
        "venta": _num(cols["venta"]),
        "cant": _num(cols["cant"]),
        "costo": _num(cols["costo"]),
        "neto": _num(cols["neto"]),
    })
    return b.dropna(subset=["fecha"])


def alcance(b, ruta):
    """`b` recortado al nivel en pantalla: `ruta` es `()`, `(grupo,)` o
    `(grupo, sub)`, por nombre."""
    if len(ruta) >= 1:
        b = b[b["grupo"] == ruta[0]]
    if len(ruta) >= 2:
        b = b[b["sub"] == ruta[1]]
    return b


def ruta_valida(b, ruta):
    """La parte de `ruta` que sigue existiendo en `b`. Un chip de la franja
    puede sacar el grupo en el que el usuario estaba parado."""
    ruta = tuple(ruta or ())[:2]
    if ruta and ruta[0] not in set(b["grupo"]):
        return ()
    if len(ruta) == 2 and ruta[1] not in set(
            b.loc[b["grupo"] == ruta[0], "sub"]):
        return ruta[:1]
    return ruta


def matriz(b, col, claves):
    """Por miembro del nivel (`col`) y período: `{medida: DataFrame}`, con los
    miembros en filas y las claves de período en columnas, EN ORDEN y con
    cero donde no hubo venta. Agrupa por dos columnas de verdad y arma cada
    tabla por nombre (regla #481)."""
    ag = (b.groupby([col, "clave"], as_index=False)
          [["venta", "cant", "costo", "neto"]].sum())
    salida = {}
    for m in ("venta", "cant", "costo", "neto"):
        t = ag.pivot_table(index=col, columns="clave", values=m,
                           aggfunc="sum")
        salida[m] = t.reindex(columns=list(claves)).fillna(0.0)
    return salida


def tramos(orden, prod_foco=None, sub=None):
    """Cómo se parte la barra: `[(nombre, miembros, es_resto)]` de abajo hacia
    arriba. Siete con nombre y los demás en «Resto (N)»; con un producto en
    foco, ese producto contra el resto de su subgrupo."""
    orden = list(orden)
    if prod_foco is not None and prod_foco in orden:
        resto = [n for n in orden if n != prod_foco]
        salida = [(prod_foco, [prod_foco], False)]
        if resto:
            salida.append((f"Resto de {sub}" if sub else "Resto", resto, True))
        return salida
    if len(orden) <= _MAX_TRAMOS + 1:
        return [(n, [n], False) for n in orden]
    resto = orden[_MAX_TRAMOS:]
    return ([(n, [n], False) for n in orden[:_MAX_TRAMOS]]
            + [(f"Resto ({len(resto)})", resto, True)])


def rango_ano_pasado(clave, gran, rango):
    """`(ini, fin)` del mismo período un año antes, recortado a los días que
    el rango cubre de ESTE: un mes en curso (1–23 set) se compara contra el
    1–23 set del año pasado, no contra el mes entero.

    Día y Semana corren 364 días —el mismo día de la semana, que en un
    restaurante es lo que manda (`ventas_comparativo.py`, «Mismo día»)—; Mes
    y Año, la misma fecha del calendario."""
    ini, fin = _limites_periodo(clave, gran)
    if rango:
        ini, fin = max(ini, rango[0]), min(fin, rango[1])
    if gran in ("Día", "Semana"):
        return ini - timedelta(days=364), fin - timedelta(days=364)

    def _un_ano_antes(x):
        try:
            return x.replace(year=x.year - 1)
        except ValueError:                 # 29 de febrero
            return date(x.year - 1, x.month, 28)
    return _un_ano_antes(ini), _un_ano_antes(fin)


def _rotulos(claves, gran):
    """`(eje, largo)`: cómo se nombra cada período en el eje y en el hover.
    Los de Semana y Mes son los de Compras; Día, los del Resumen."""
    if gran == "Día":
        dias = [pd.Timestamp(c) for c in claves]
        return ([f"{x:%d/%m}" for x in dias],
                [f"{_fmt_dia(x)}/{x.year}" for x in dias])
    rot = [_rotulo_periodo(c, gran) for c in claves]
    return [r[0] for r in rot], [r[1] for r in rot]


def _nombre_rango(ini, fin):
    """«15–21 set 2025», «31 ago–6 set 2026», «20 set 2025»: los días de un
    tramo, con el año, como los nombra el eje de Compras. Es lo que dice el
    Detalle cuando compara contra el año pasado: ahí el período NO es el del
    eje, son sus mismos días un año antes."""
    m = MESES_ABR_ES
    if ini == fin:
        return f"{ini.day} {m[ini.month - 1]} {ini.year}"
    if (ini.year, ini.month) == (fin.year, fin.month):
        return f"{ini.day}–{fin.day} {m[fin.month - 1]} {fin.year}"
    if ini.year == fin.year:
        return (f"{ini.day} {m[ini.month - 1]}–{fin.day} {m[fin.month - 1]} "
                f"{fin.year}")
    return (f"{ini.day} {m[ini.month - 1]} {ini.year}–{fin.day} "
            f"{m[fin.month - 1]} {fin.year}")


def _unid(v):
    """Unidades compactas: «845 u», «1.2k u»."""
    a = abs(v)
    if a >= 1000:
        return f"{v / 1000:,.1f}k u"
    return f"{v:,.0f} u"


def _fmt(v, unidades):
    return _unid(v) if unidades else fmt_k(v)


def _con_signo(txt, v):
    """«+S/ 4.0k», «−S/ 1.2k»: el signo afuera y el menos tipográfico."""
    txt = txt.replace("-", "").replace("−", "")
    return ("+" if v > 0 else "−" if v < 0 else "") + txt


def _pct(p, dec=1):
    return ("+" if p > 0 else "−" if p < 0 else "") + f"{abs(p) * 100:.{dec}f}%"


def _relativo(a, b):
    """El cambio relativo de un miembro. Contra casi nada un porcentaje grita
    (+2521 %): de +200 % para arriba se dice cuántas veces, y sin base,
    «nuevo»."""
    if not b:
        return "nuevo" if a else "—"
    p = (a - b) / abs(b)
    if p > 2:
        return f"×{a / b:.1f}"
    return _pct(p, 0)


def _renglones(total, var, unidades):
    """Los renglones de la etiqueta de una barra, `(plano, html)`: el total y
    la variación contra la barra anterior, como `ventas_resumen.
    _renglones_barra` pero también en unidades."""
    if not total:
        return []
    t = _fmt(total, unidades)
    salida = [(t, t)]
    estado, pct, _ = var
    if estado == "ok":
        v, c = _fmt_var_venta(pct)
        salida.append((v, f"<span style='color:{c}'><b>{v}</b></span>"))
    elif estado == "parcial":
        salida.append(("parcial", f"<span style='color:{GRIS_TEXTO}'>"
                                  "<i>parcial</i></span>"))
    return salida


# ===========================================================================
# LOS CLICS (regla #399): se leen ARRIBA, con un contador en la key
# ===========================================================================

def _key(base_key):
    return f"{base_key}_{st.session_state.get('_' + base_key + '_n', 0)}"


def _clic(base_key, extraer):
    """El clic que dejó la corrida anterior en el widget `base_key`, o None.
    Si hubo, sube el contador: el widget se dibuja en ESTA corrida con una
    key nueva, sin la selección vieja, y el próximo clic cae donde se lo va
    a buscar."""
    valor = extraer(st.session_state.get(_key(base_key)))
    if valor is not None:
        _n = "_" + base_key + "_n"
        st.session_state[_n] = st.session_state.get(_n, 0) + 1
    return valor


def _punto(evt):
    p = _first_point(evt)
    if p is None:
        return None
    i = p.get("point_index", p.get("point_number"))
    return i if isinstance(i, int) else None


def _fila(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _bajar(nivel, ruta, nombre):
    """Tocar un nombre: en Grupos y Subgrupos baja un nivel; en Productos
    pone ese producto en foco contra el resto de su subgrupo (o lo suelta)."""
    if nivel < 2:
        st.session_state["vt_mix_ruta"] = tuple(ruta) + (nombre,)
        st.session_state["vt_mix_prod"] = None
    else:
        st.session_state["vt_mix_prod"] = (
            None if st.session_state.get("vt_mix_prod") == nombre else nombre)


def _ir_a(ruta):
    st.session_state["vt_mix_ruta"] = tuple(ruta)
    st.session_state["vt_mix_prod"] = None


def _al_buscar():
    """El buscador salta al subgrupo del producto y lo pone en foco. Se vacía
    solo: es un atajo, no un filtro que quede puesto."""
    elegido = st.session_state.get("vt_mix_buscar")
    donde = st.session_state.get("_vt_mix_buscar_mapa", {}).get(elegido)
    if donde:
        _g, _s, _p = donde
        st.session_state["vt_mix_ruta"] = (_g, _s)
        st.session_state["vt_mix_prod"] = _p
    st.session_state["vt_mix_buscar"] = None


def _leer_clics():
    """Los cuatro widgets con selección, leídos antes de dibujar nada."""
    ss = st.session_state
    i = _clic("vt_mix_g", _punto)
    claves = ss.get("_vt_mix_claves", [])
    if i is not None and 0 <= i < len(claves):
        clave = claves[i]
        if ss.get("vt_mix_foco") == clave and ss.get("vt_mix_zona") == _ZONA_DETALLE:
            # La misma barra otra vez: vuelve al Resumen.
            ss["vt_mix_foco"] = None
            ss["vt_mix_zona"] = _ZONA_RESUMEN
        else:
            # Desde el Resumen el clic ABRE el Detalle, como en la primera
            # vista: el gesto es «mostrame ésta».
            ss["vt_mix_foco"] = clave
            ss["vt_mix_zona"] = _ZONA_DETALLE
            ss["_vt_mix_parcial_foco"] = True

    for base_key, filas_key in (("vt_mix_tabla", "_vt_mix_filas_tabla"),
                                ("vt_mix_puente", "_vt_mix_filas_puente")):
        extraer = _fila if base_key == "vt_mix_tabla" else _punto
        j = _clic(base_key, extraer)
        filas, nivel, ruta = ss.get(filas_key, ([], 0, ()))
        if j is not None and 0 <= j < len(filas) and filas[j] is not None:
            _bajar(nivel, ruta, filas[j])

    j = _clic("vt_mix_top", _fila)
    filas = ss.get("_vt_mix_filas_top", [])
    if j is not None and 0 <= j < len(filas):
        _g, _s, _p = filas[j]
        ss["vt_mix_ruta"] = (_g, _s)
        ss["vt_mix_prod"] = _p


# ===========================================================================
# LA VISTA
# ===========================================================================

@st.fragment
def _ventas_mix(d, filtrar_cb=None):
    """«Mix de carta»: la venta por período partida por Grupo › Sub Grupo ›
    Producto. `d` es el df de la vista —sólo venta, un ítem una vez, con los
    chips de la franja—, y `filtrar_cb` lo que se le aplica al df del año
    pasado que la vista trae aparte de R2 (el `_filtrar_items` de
    `ventas.py`), para que los dos lados se comparen igual filtrados."""
    # ── 0) La fecha cambió: recargar el parquet del rango nuevo ──────────
    # Igual que el Resumen: el selector escribe la clave CANÓNICA del rango
    # (`categoria=None`), y el `d` que llegó es el del rango viejo.
    if st.session_state.pop("vt_mix_fecha_flag", False):
        preservar_widgets(_KEYS_WIDGET_MIX)
        st.rerun(scope="app")

    cols = columnas(d)
    if not (cols["fecha"] and cols["venta"] and cols["grupo"]):
        st.info("Faltan columnas (Fecha, Venta, Grupo) para el mix de carta.")
        return

    ss = st.session_state
    # La zona y el cambio los escribe Python (al tocar una barra, al tocar un
    # período incompleto), así que nacen acá y el widget va SIN `default=`:
    # con los dos, Streamlit avisa que el valor llegó por dos lados.
    ss.setdefault("vt_mix_zona", _ZONA_RESUMEN)
    ss.setdefault("vt_mix_cambio", _CAMBIO_MONTO)
    _leer_clics()

    # ── 1) El renglón del título se crea ARRIBA y se llena después ───────
    # Los KPI dependen del período en foco y del nivel, que se deciden más
    # abajo; en Streamlit el orden de ejecución es el orden en que se leen
    # los valores, así que el lugar se reserva primero.
    cab = st.container(key="vt_mix_cabfila")

    # columnas-internas: la fila de controles de la tarjeta
    ctrl = st.columns([1.7, 1.25, 1.55, 2.2, 2.0],
                      vertical_alignment="center")
    with ctrl[0]:
        gran = st.segmented_control(
            "Agrupar por", _GRAN_OPCIONES, default=_GRAN_DEFAULT,
            required=True, key="vt_mix_gran",
            label_visibility="collapsed") or _GRAN_DEFAULT
    with ctrl[1]:
        medida = st.segmented_control(
            "Medir", _MEDIDAS, default=_MEDIDAS[0], required=True,
            key="vt_mix_medida", label_visibility="collapsed",
            help="Unidades suma platos, copas y botellas: se lee mejor "
                 "desde un grupo.") or _MEDIDAS[0]
    with ctrl[2]:
        escala = st.segmented_control(
            "Escala", _ESCALAS, default=_ESCALAS[0], required=True,
            key="vt_mix_escala", label_visibility="collapsed",
            help="«% del período»: cuánto pesa cada uno en su barra. Deja "
                 "ver si cambió el reparto aunque el total suba o baje."
        ) or _ESCALAS[0]
    unidades = medida == "Unidades"
    pct_modo = escala == "% del período"
    med = "cant" if unidades else "venta"

    b_todo = base(d, cols)
    if b_todo.empty:
        st.info("Sin ventas en el rango cargado.")
        return

    with ctrl[3]:
        _prods = (b_todo.groupby(["grupo", "sub", "prod"], as_index=False)
                  ["venta"].sum().sort_values("venta", ascending=False))
        _mapa = {f"{r.prod} · {r.sub}": (r.grupo, r.sub, r.prod)
                 for r in _prods.itertuples(index=False)}
        ss["_vt_mix_buscar_mapa"] = _mapa
        st.selectbox("Buscar un producto", list(_mapa), index=None,
                     key="vt_mix_buscar", placeholder="Buscar un producto…",
                     label_visibility="collapsed", on_change=_al_buscar)
    with ctrl[4]:
        # «vt_mixf» y no «vt_mix»: el selector arma SUS keys con ese prefijo
        # (`_escala`, `_fila`, `_atajo_sel`…), y `vt_mix_escala` ya es el
        # control de escala de esta vista — StreamlitDuplicateElementKey.
        selector_fecha_tarjeta("vt_mixf", "vt_mix_fecha_flag", categoria=None)

    # ── 2) Períodos ──────────────────────────────────────────────────────
    # En Día, los últimos `MAX_DIAS` días con ventas, como el Resumen: más
    # barras que eso no se leen, y una por día con un año cargado congelaba
    # la página (regla #523).
    b_todo = b_todo.assign(clave=_periodo_serie(b_todo["fecha"], gran))
    _nota = ""
    if gran == "Día":
        dias = sorted(b_todo["fecha"].dt.normalize().unique())
        if len(dias) > MAX_DIAS:
            b_todo = b_todo[b_todo["fecha"] >= dias[-MAX_DIAS]]
            _nota = f" Los últimos {MAX_DIAS} días con ventas."
    claves = sorted(b_todo["clave"].unique())
    n_per = len(claves)
    eje, largo = _rotulos(claves, gran)
    rango = (b_todo["fecha"].min().date(), b_todo["fecha"].max().date())

    # ── 3) El nivel en pantalla ──────────────────────────────────────────
    ruta = ruta_valida(b_todo, ss.get("vt_mix_ruta", ()))
    ss["vt_mix_ruta"] = ruta
    nivel = len(ruta)
    col = _COL_NIVEL[nivel]
    b = alcance(b_todo, ruta)
    M = matriz(b, col, claves)
    orden = M[med].sum(axis=1)
    orden = orden[(M["venta"].abs().sum(axis=1) > 0)
                  | (M["cant"].abs().sum(axis=1) > 0)]
    orden = orden.sort_values(ascending=False).index.tolist()
    if not orden:
        st.info("Sin ventas para este nivel en el rango.")
        return
    prod_foco = ss.get("vt_mix_prod") if nivel == 2 else None
    if prod_foco not in orden:
        prod_foco = None
    ss["vt_mix_prod"] = prod_foco

    tr = tramos(orden, prod_foco, ruta[1] if nivel == 2 else None)
    colores, _i = [], 0
    for _n, _miembros, es_resto in tr:
        if es_resto:
            colores.append(_COLOR_RESTO)
        else:
            colores.append(_COLORES[_i % len(_COLORES)])
            _i += 1
    valores = [M[med].loc[m].sum(axis=0).to_numpy(dtype=float)
               for _n, m, _r in tr]
    tot = M[med].sum(axis=0).to_numpy(dtype=float)
    vars_ = _variaciones(claves, [float(x) for x in tot], gran, rango)

    # ── 4) El foco: la CLAVE del período, que sobrevive al drill ─────────
    foco = ss.get("vt_mix_foco")
    foco_ix = claves.index(foco) if foco in claves else None
    if foco_ix is None:
        ss["vt_mix_foco"] = None
    # El Detalle sin barra elegida mira el último período COMPLETO.
    i_det = foco_ix
    if i_det is None:
        _comp = [k for k, v in enumerate(vars_) if v[0] != "parcial"]
        i_det = _comp[-1] if _comp else n_per - 1
    # Un período cortado por el rango se compara en puntos de mix: 23 días
    # de septiembre contra un agosto entero no dicen nada en soles. Se
    # decide al TOCAR la barra; después manda lo que el usuario elija.
    if ss.pop("_vt_mix_parcial_foco", False) and foco_ix is not None:
        ss["vt_mix_cambio"] = (
            _CAMBIO_MIX if vars_[foco_ix][0] in ("parcial", "ant_parcial")
            else _CAMBIO_MONTO)

    # ── 5) El renglón del título ─────────────────────────────────────────
    with cab:
        st.markdown(_html_cab(
            gran, medida, pct_modo, M, b_todo, b, claves, eje, rango,
            foco_ix, ruta), unsafe_allow_html=True)

    # ── 6) El gráfico y, al costado, dónde estás y a dónde bajar ─────────
    # columnas-internas: el gráfico y su columna de navegación
    c_graf, c_nav = st.columns([3.3, 1], gap="small")
    with c_graf:
        _grafico(tr, valores, colores, tot, claves, eje, largo, vars_,
                 foco_ix, unidades, pct_modo, n_per)
    with c_nav:
        _navegacion(tr, valores, ruta, nivel, foco_ix, eje, unidades,
                    len(orden), prod_foco)

    # ── 7) La fila que elige qué se ve abajo ─────────────────────────────
    with st.container(horizontal=True, gap="small",
                      vertical_alignment="center", key="vt_mix_pie"):
        zona = st.segmented_control(
            "Qué se ve abajo", (_ZONA_RESUMEN, _ZONA_DETALLE),
            required=True, key="vt_mix_zona",
            label_visibility="collapsed",
            help="**Resumen**: una fila por cada uno del nivel y una "
                 "columna por período. **Detalle**: qué movió el período "
                 "que toques, y lo más vendido en él.") or _ZONA_RESUMEN
        if zona == _ZONA_DETALLE:
            comp = st.segmented_control(
                "Comparar con", (_COMP_ANT, _COMP_AP), default=_COMP_ANT,
                required=True, key="vt_mix_comp",
                label_visibility="collapsed",
                help="**Año pasado** compara los mismos días un año antes: "
                     "un mes en curso contra el mismo tramo del año pasado."
            ) or _COMP_ANT
            cambio = st.segmented_control(
                "Medir el cambio en", (_CAMBIO_MONTO, _CAMBIO_MIX),
                required=True, key="vt_mix_cambio",
                label_visibility="collapsed",
                help="**Mix (pp)**: cuántos puntos del total ganó o perdió "
                     "cada uno. Sirve aunque los dos períodos no midan lo "
                     "mismo.") or _CAMBIO_MONTO
        pie = st.empty()

    if zona == _ZONA_RESUMEN:
        _zona_resumen(M, med, orden, eje, [v[0] == "parcial" for v in vars_],
                      foco_ix, pct_modo, unidades, nivel, ruta)
        _siguiente = (f"una fila para ver sus {_NIVELES[nivel + 1].lower()}"
                      if nivel < 2 else "un producto para seguirlo")
        pie.caption(f"Tocá una barra para ver qué la movió · {_siguiente}."
                    + _nota)
    else:
        _zona_detalle(M, med, orden, claves, eje, largo, i_det, comp, cambio,
                      gran, rango, vars_, ruta, nivel, unidades, b,
                      filtrar_cb, pie)


# ===========================================================================
# LAS PIEZAS
# ===========================================================================

def _html_cab(gran, medida, pct_modo, M, b_todo, b, claves, eje, rango,
              foco_ix, ruta):
    """Título + KPI en un renglón: el dibujo de la cabecera del Resumen
    (`.vt-cab`, `.vt-kpis`), sobre el período en foco o el rango entero."""
    def _tarjeta(rot, val, sub="", clase="", tip=""):
        return (f'<div class="vt-kpi {clase}" title="{escape(tip or rot)}">'
                f'<span class="vt-kpi-rot">{escape(rot)}</span>'
                f'<span class="vt-kpi-val">{escape(val)}'
                f'<span class="vt-kpi-sub">{escape(sub)}</span></span></div>')

    per = {"Día": "día", "Semana": "semana", "Mes": "mes", "Año": "año"}[gran]
    i = foco_ix
    _sel = (lambda s: float(s.sum())) if i is None else (
        lambda s: float(s.iloc[i]))
    v = _sel(M["venta"].sum(axis=0))
    q = _sel(M["cant"].sum(axis=0))
    c = _sel(M["costo"].sum(axis=0))
    n = _sel(M["neto"].sum(axis=0))
    cuando = (f"{len(claves)} {per}" + ("" if len(claves) == 1 else
                                         ("es" if per == "mes" else "s"))
              if i is None else eje[i])
    partes = [_tarjeta(f"Venta · {cuando}", fmt_k(v), "", "vt-kpi-total",
                       f"Venta: S/ {v:,.2f}")]
    # Siempre sobre la VENTA, mida lo que mida el gráfico: los KPI son la
    # foto del período, no de la barra.
    _tv = [float(x) for x in M["venta"].sum(axis=0)]
    _vars = _variaciones(claves, _tv, gran, rango)
    if i is None:
        _ok = [k for k, x in enumerate(_vars) if x[0] != "parcial"]
        if _ok:
            prom = float(np.mean([_tv[k] for k in _ok]))
            partes.append(_tarjeta(f"Promedio por {per}", fmt_k(prom), "",
                                   tip="Sólo períodos completos"))
    else:
        estado, p, _ = _vars[i]
        if estado == "ok":
            txt = _fmt_var_venta(p)[0]
        elif estado == "parcial":
            txt = "parcial"
        else:
            txt = "—"
        partes.append(_tarjeta(f"vs {per} anterior", txt))
    partes.append(_tarjeta(
        "% costo", f"{c / n:.1%}" if n else "—", "",
        tip="Costo de la línea ÷ venta neta, como el Resumen"))
    partes.append(_tarjeta("Unidades", f"{q:,.0f}"))
    _bp = b if i is None else b[b["clave"] == claves[i]]
    n_prod = int((_bp.groupby(["sub", "prod"])["venta"].sum() > 0).sum())
    partes.append(_tarjeta("Productos con venta", f"{n_prod:,}"))
    if ruta:
        _bt = b_todo if i is None else b_todo[b_todo["clave"] == claves[i]]
        v_all = float(_bt["venta"].sum())
        partes.append(_tarjeta("Del total del local",
                               f"{v / v_all:.1%}" if v_all else "—"))
    titulo = (("Unidades" if medida == "Unidades" else "Venta")
              + f" por {per}" + (" · % del período" if pct_modo else ""))
    return (f'<div class="vt-cab"><span class="vt-cab-tit">'
            f'{escape(titulo)}</span><div class="vt-kpis">'
            + "".join(partes) + "</div></div>")


def _grafico(tr, valores, colores, tot, claves, eje, largo, vars_,
             foco_ix, unidades, pct_modo, n_per):
    """La barra por período, partida en los tramos del nivel."""
    alto_fig = alturas.VENTAS_MIX_FIG
    ss = st.session_state
    ss["_vt_mix_claves"] = list(claves)
    xs = list(range(n_per))

    # La etiqueta de encima (total + variación), con el plan de Compras. En
    # «% del período» todas las barras miden 100: no hay total que escribir.
    reng = ([_renglones(t, v, unidades) for t, v in zip(tot, vars_)]
            if not pct_modo else [[] for _ in claves])
    plan, k_etq, alto_etq = _plan_etiquetas(
        n_per, [[p for p, _ in r] for r in reng], alto_fig)
    textos = [None] * n_per
    if plan:
        _sep = _ETQ_SEP if plan == "unida" else "<br>"
        textos = [(_sep.join(h for _, h in r[:k_etq]) or None) for r in reng]
    textos_tr = (_etiqueta_en_la_punta(
        [pd.DataFrame({"valor": v}) for v in valores], textos)
        if plan else [[None] * n_per for _ in valores])
    estilo_etq = dict(
        textposition="outside", cliponaxis=False, constraintext="none",
        textangle=-90 if plan in ("girada", "unida") else 0,
        textfont=dict(size=_ETQ_FUENTE, color=TEXTO_PRINCIPAL))

    fig = go.Figure()
    tot_txt = [_fmt(t, unidades) for t in tot]
    for i, ((nombre, _m, _r), vals, color) in enumerate(
            zip(tr, valores, colores)):
        share = [vals[j] / tot[j] if tot[j] else 0.0 for j in range(n_per)]
        y = [s * 100 for s in share] if pct_modo else vals
        # El foco se atenúa por COLOR, nunca con `marker.opacity` por punto:
        # esa lista sobre barras con texto crashea Plotly (regla #476).
        _c = ([color if j == foco_ix else _con_alpha(color, _ATENUADO)
               for j in range(n_per)] if foco_ix is not None else color)
        fig.add_trace(go.Bar(
            x=xs, y=y, name=nombre, marker=dict(color=_c),
            customdata=list(zip(largo, [_fmt(x, unidades) for x in vals],
                                [f"{s:.1%}" for s in share], tot_txt)),
            hovertemplate=(
                "%{customdata[0]}<br><b>" + escape(nombre)
                + "</b>: %{customdata[1]} · %{customdata[2]} del período"
                "<br>Total: %{customdata[3]}<extra></extra>"),
        ))
        if plan and not pct_modo:
            fig.data[-1].update(text=textos_tr[i], **estilo_etq)

    _compras_layout(fig, alto=alto_fig)
    # El techo con el área real, como el Resumen (regla #521): lo que la
    # etiqueta ocupa arriba, sin reservar de más.
    rng_y = None
    if plan and not pct_modo:
        area = alto_fig - _MARGEN_ARRIBA - _PIE_EJE
        etq = min(alto_etq * 0.8, area * 0.45)
        pos = np.sum([np.clip(v, 0, None) for v in valores], axis=0)
        hi = float(np.nanmax(pos)) if n_per else 0.0
        if hi > 0 and area > etq:
            rng_y = [0.0, hi * area / (area - etq)]
    elif pct_modo:
        rng_y = [0.0, 100.0]
    fig.update_layout(
        barmode="relative", showlegend=False, bargap=0.3,
        margin=dict(l=10, r=10, t=_MARGEN_ARRIBA, b=4),
        yaxis=dict(
            tickprefix="" if (unidades or pct_modo) else "S/ ",
            ticksuffix="%" if pct_modo else "", tickformat=",.0f",
            **({"range": rng_y} if rng_y else {})),
        # MODO CLIC (regla #388): con `on_select`, Streamlit deja el dragmode
        # en «select» y un clic suelto no selecciona nada.
        dragmode="pan",
    )
    # El eje es LINEAL por índice, como el del Resumen: una clave como
    # «2025» en un eje de categorías Plotly la lee como número (#448).
    lienzo = _LIENZO_PX * _ANCHO_GRAFICO
    caben = max(1, int(lienzo // (max(map(len, eje)) * 6.3 + 12)))
    paso = max(1, -(-n_per // caben))
    tv = list(range(0, n_per, paso))
    fig.update_xaxes(type="linear", tickmode="array", tickvals=tv,
                     ticktext=[eje[j] for j in tv], range=[-0.5, n_per - 0.5],
                     tickangle=0, tickfont=dict(size=10), fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    st.plotly_chart(
        fig, key=_key("vt_mix_g"),
        on_select="rerun", selection_mode="points",
        config={"displaylogo": False, "displayModeBar": False})


def _navegacion(tr, valores, ruta, nivel, foco_ix, eje, unidades,
                n_miembros, prod_foco):
    """La columna de la derecha: dónde estás (las migas suben) y los tramos
    de la barra, cada uno un botón que baja un nivel. Hace de leyenda: la
    muestra de color de cada botón la pinta el CSS por su key
    (`vt_mix_ley_<i>`), con los `--serie-<i>` espejo de `_COLORES`."""
    with st.container(key="vt_mix_nav", gap=None):
        antes = [(_TODOS, ())] + [(ruta[k], ruta[:k + 1])
                                  for k in range(len(ruta) - 1)]
        if ruta:
            for k, (txt, destino) in enumerate(antes):
                st.button(f"‹ {txt}", key=f"vt_mix_miga_{k}", type="tertiary",
                          on_click=_ir_a, args=(destino,),
                          help=f"Volver a {txt}")
        actual = ruta[-1] if ruta else _TODOS
        cuando = "todo el rango" if foco_ix is None else eje[foco_ix]
        st.markdown(
            f'<div class="vt-mix-nivel"><b>{escape(actual)}</b> · '
            f'{n_miembros} {_NIVELES[nivel].lower()} · {escape(cuando)}</div>',
            unsafe_allow_html=True)

        total = sum(float(v.sum() if foco_ix is None else v[foco_ix])
                    for v in valores)
        _i = 0
        for (nombre, miembros, es_resto), vals in zip(tr, valores):
            x = float(vals.sum() if foco_ix is None else vals[foco_ix])
            share = x / total if total else 0.0
            etq = f"{_compras_truncar(nombre, 22)} · {share:.0%}" \
                if share >= 0.1 else f"{_compras_truncar(nombre, 22)} · {share:.1%}"
            if es_resto:
                st.button(etq, key="vt_mix_ley_resto", type="tertiary",
                          disabled=True,
                          help="Cada uno está en la tabla de abajo.")
                continue
            if nivel < 2:
                ayuda = f"Ver los {_NIVELES[nivel + 1].lower()} de {nombre}"
            elif prod_foco == nombre:
                ayuda = "Soltar el foco"
            else:
                ayuda = f"Seguir {nombre} contra el resto de su subgrupo"
            st.button(etq, key=f"vt_mix_ley_{_i}", type="tertiary",
                      on_click=_bajar, args=(nivel, ruta, nombre),
                      help=ayuda)
            _i += 1
        if unidades and nivel == 0:
            st.caption("Unidades suma platos, copas y botellas.")


def _heat(fila):
    """El fondo de cada celda de una fila: más oscuro donde la fila es más
    fuerte. Compara la fila CONSIGO MISMA, así se ve la estacionalidad de
    cada uno aunque venda la décima parte que el de arriba."""
    vals = pd.to_numeric(fila, errors="coerce").fillna(0.0)
    mx = float(vals.max())
    if mx <= 0:
        return [""] * len(vals)
    return [f"background-color: {_con_alpha(ACENTO, 0.04 + 0.34 * v / mx)}"
            if v > 0 else "" for v in vals]


def _zona_resumen(M, med, orden, eje, parciales, foco_ix, pct_modo,
                  unidades, nivel, ruta):
    """El mapa de calor: una fila por cada uno del nivel, una columna por
    período, y el total, el mix, el % de costo y la tendencia al final. Un
    clic en una fila hace lo mismo que su nombre en la columna de la
    derecha."""
    vals = M[med].loc[orden]
    tot = vals.sum(axis=0)
    # El período en foco lleva «●» y uno cortado por el rango, «*»: el
    # nombre de la columna es lo único de la cabecera que se puede marcar.
    per_cols = [("● " if j == foco_ix else "") + e
                + ("*" if parciales[j] else "") for j, e in enumerate(eje)]
    cuerpo = (vals.div(tot.replace(0, np.nan), axis=1).fillna(0.0)
              if pct_modo else vals)
    tabla = pd.DataFrame(cuerpo.to_numpy(), columns=per_cols)
    tabla.insert(0, _NIVELES[nivel], list(orden))
    t_fila = vals.sum(axis=1)
    tabla["Total"] = t_fila.to_numpy()
    tabla["Mix"] = (t_fila / float(tot.sum())).to_numpy() if tot.sum() else 0.0
    _c = M["costo"].loc[orden].sum(axis=1)
    _n = M["neto"].loc[orden].sum(axis=1)
    # Sin costo cargado no es «0 % de costo»: es no saberlo (regla #524,
    # la venta sin costo del Resumen). Va «—».
    tabla["% costo"] = (_c.where(_c > 0) / _n.replace(0, np.nan)).to_numpy()
    tabla["Tendencia"] = [list(map(float, r)) for r in vals.to_numpy()]
    fila_total = {_NIVELES[nivel]: "Total",
                  **{c: (1.0 if pct_modo else float(t))
                     for c, t in zip(per_cols, tot)},
                  "Total": float(tot.sum()), "Mix": 1.0,
                  "% costo": (float(M["costo"].loc[orden].to_numpy().sum())
                              / float(M["neto"].loc[orden].to_numpy().sum())
                              if float(M["neto"].loc[orden].to_numpy().sum())
                              else np.nan),
                  "Tendencia": list(map(float, tot))}
    tabla = pd.concat([pd.DataFrame([fila_total]), tabla], ignore_index=True)
    st.session_state["_vt_mix_filas_tabla"] = (
        [None] + list(orden), nivel, tuple(ruta))

    def _num(v):
        # Un cero se escribe «—»: en una fila donde casi todo es cero, lo que
        # tiene que verse es lo que no (el mismo criterio que el Cuadre del
        # Resumen, regla #525).
        if pd.isna(v) or v == 0:
            return "—"
        if pct_modo:
            return f"{v:.1%}"
        return _unid(v) if unidades else fmt_k(v).replace("S/ ", "")

    def _total_fila(fila):
        return ([f"background-color: {LAVANDA_FONDO}"] * len(fila)
                if fila.name == 0 else [""] * len(fila))

    sty = (tabla.style
           .apply(_heat, axis=1, subset=pd.IndexSlice[1:, per_cols])
           .apply(_total_fila, axis=1)
           .format(_num, subset=per_cols)
           .format(lambda v: "—" if pd.isna(v) else _fmt(v, unidades),
                   subset=["Total"])
           .format(lambda v: "—" if pd.isna(v) else f"{v:.1%}",
                   subset=["Mix", "% costo"]))
    st.dataframe(
        sty, key=_key("vt_mix_tabla"), on_select="rerun",
        selection_mode="single-row", hide_index=True, row_height=27,
        height=alturas.VENTAS_MIX_TABLA,
        column_config={
            _NIVELES[nivel]: st.column_config.TextColumn(
                _NIVELES[nivel], pinned=True, width="medium"),
            "% costo": st.column_config.Column(
                "% costo", help="Costo de la línea ÷ venta neta, como el "
                "Resumen. «—»: sin costo cargado."),
            "Tendencia": st.column_config.LineChartColumn(
                "Tendencia", width="small", y_min=0, color=ACENTO),
        })


def _zona_detalle(M, med, orden, claves, eje, largo, i, comp, cambio, gran,
                  rango, vars_, ruta, nivel, unidades, b, filtrar_cb, pie):
    """Qué movió el período `i`: el cambio de cada uno del nivel contra el
    período anterior (o el mismo tramo del año pasado), ordenado por cuánto
    pesó, y al lado lo más vendido en el período."""
    col = _COL_NIVEL[nivel]
    # El nombre del EJE en Día y Semana («14–20 set»): el largo («Semana del
    # lun 14 al dom 20 set 2026») no entra en el renglón de los controles.
    corto = [e if gran in ("Día", "Semana") else lg
             for e, lg in zip(eje, largo)]
    a = M[med][claves[i]]
    nombre_b, b_ser = None, None
    if comp == _COMP_AP:
        ini, fin = rango_ano_pasado(claves[i], gran, rango)
        cfg = REPORTES.get("Ventas", {})
        df_ap = _cargar_tramo(cfg.get("archivo", "ventas.parquet"),
                              cfg.get("carga_por_rango", "FEC REG DOCUMENTO"),
                              ini, fin, filtrar_cb)
        if df_ap is not None:
            b_ap = alcance(base(df_ap, columnas(df_ap)), ruta)
            b_ap = b_ap[(b_ap["fecha"].dt.date >= ini)
                        & (b_ap["fecha"].dt.date <= fin)]
            b_ser = b_ap.groupby(col)[med].sum()
        else:
            b_ser = pd.Series(dtype=float)
        _ld = _limites_periodo(claves[i], gran)
        nombre_a = _nombre_rango(max(_ld[0], rango[0]), min(_ld[1], rango[1]))
        nombre_b = _nombre_rango(ini, fin)
    elif i > 0:
        b_ser = M[med][claves[i - 1]]
        nombre_b, nombre_a = corto[i - 1], corto[i]
    else:
        nombre_a = corto[i]

    if b_ser is None:
        pie.caption(f"{nombre_a[:1].upper()}{nombre_a[1:]} es el primer "
                    "período del rango: no hay con qué compararlo.")
        return

    miembros = sorted(set(a.index) | set(b_ser.index))
    a = a.reindex(miembros).fillna(0.0)
    b_ser = b_ser.reindex(miembros).fillna(0.0)
    t_a, t_b = float(a.sum()), float(b_ser.sum())
    filas = pd.DataFrame({
        "nombre": miembros, "a": a.to_numpy(), "b": b_ser.to_numpy()})
    filas["d"] = filas["a"] - filas["b"]
    filas["pp"] = ((filas["a"] / t_a if t_a else 0.0)
                   - (filas["b"] / t_b if t_b else 0.0))
    usa_pp = cambio == _CAMBIO_MIX
    k = "pp" if usa_pp else "d"
    filas = filas.reindex(filas[k].abs().sort_values(ascending=False).index)

    # El caption de la fila de controles dice qué se compara y el resultado.
    d_tot = t_a - t_b
    _res = (f"{_con_signo(_fmt(d_tot, unidades), d_tot)}"
            + (f" ({_pct(d_tot / abs(t_b))})" if t_b else ""))
    # Un período que el rango corta —éste o el anterior— contra uno entero:
    # el monto no dice nada (tres días contra siete). Contra el año pasado
    # sí es parejo: se comparan los mismos días.
    _estado = vars_[i][0]
    if comp == _COMP_ANT and _estado in ("parcial", "ant_parcial"):
        _cual = nombre_a if _estado == "parcial" else nombre_b
        _txt = (f"{nombre_a} contra {nombre_b}. {_cual[:1].upper()}"
                f"{_cual[1:]} está incompleto en el rango: ")
        _txt += ("se compara el reparto, no el monto." if usa_pp
                 else f"{_res}, pero el monto no se compara parejo; el mix sí.")
    else:
        _txt = f"{nombre_a} contra {nombre_b}: {_res}."
    pie.caption(_txt)

    top = filas.head(_TOP_DETALLE)
    resto = filas.iloc[_TOP_DETALLE:]
    if len(resto):
        top = pd.concat([top, pd.DataFrame([{
            "nombre": f"Resto ({len(resto)})", "a": resto["a"].sum(),
            "b": resto["b"].sum(), "d": resto["d"].sum(),
            "pp": resto["pp"].sum()}])], ignore_index=True)
    top = top.iloc[::-1].reset_index(drop=True)      # el mayor, arriba
    es_resto = [str(n).startswith("Resto (") and n not in miembros
                for n in top["nombre"]]
    st.session_state["_vt_mix_filas_puente"] = (
        [None if r else n for n, r in zip(top["nombre"], es_resto)],
        nivel, tuple(ruta))

    # columnas-internas: el puente del período y lo más vendido en él
    c_izq, c_der = st.columns([1.25, 1], gap="medium")
    with c_izq:
        if usa_pp:
            txt = [f"{_pct(p).rstrip('%')} pp · "
                   f"{(a_ / t_a if t_a else 0):.0%}"
                   for p, a_ in zip(top["pp"], top["a"])]
            xv = top["pp"] * 100
        else:
            txt = [f"{_con_signo(_fmt(d_, unidades), d_)} · "
                   f"{_relativo(a_, b_)}"
                   for d_, a_, b_ in zip(top["d"], top["a"], top["b"])]
            xv = top["d"]
        fig = go.Figure(go.Bar(
            x=xv, y=[_compras_truncar(n, 24) for n in top["nombre"]],
            orientation="h", text=txt, textposition="outside",
            cliponaxis=False, textfont=dict(size=10),
            marker=dict(color=[AJUSTE_POS if x >= 0 else AJUSTE_NEG
                               for x in xv]),
            customdata=list(zip(top["nombre"],
                                [_fmt(x, unidades) for x in top["b"]],
                                [_fmt(x, unidades) for x in top["a"]])),
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]} → "
                           "%{customdata[2]}<extra></extra>"),
        ))
        _compras_layout(fig, alto=alturas.VENTAS_MIX_TABLA)
        _mx = float(np.nanmax(np.abs(xv))) if len(xv) else 1.0
        fig.update_layout(
            showlegend=False, bargap=0.25, dragmode="pan",
            margin=dict(l=10, r=10, t=4, b=4),
            xaxis=dict(visible=False, fixedrange=True,
                       range=[-_mx * 1.9, _mx * 1.9]),
            yaxis=dict(showticklabels=True, automargin=True, fixedrange=True,
                       tickfont=dict(size=11)),
        )
        fig.add_vline(x=0, line_width=1, line_color=GRIS_TEXTO, opacity=0.4)
        for _t in fig.data:
            _t.textfont.color = [AJUSTE_POS_TEXTO if x >= 0
                                 else AJUSTE_NEG_TEXTO for x in xv]
        st.plotly_chart(
            fig, key=_key("vt_mix_puente"),
            on_select="rerun", selection_mode="points",
            config={"displaylogo": False, "displayModeBar": False})

    with c_der:
        bp = b[b["clave"] == claves[i]]
        prods = (bp.groupby(["grupo", "sub", "prod"], as_index=False)
                 [["venta", "cant", "costo", "neto"]].sum())
        prods = prods[(prods["venta"] > 0) | (prods["cant"] > 0)]
        prods = prods.sort_values(med, ascending=False).head(_TOP_PRODUCTOS)
        st.session_state["_vt_mix_filas_top"] = list(
            zip(prods["grupo"], prods["sub"], prods["prod"]))
        tabla = pd.DataFrame({
            "Producto": prods["prod"].to_numpy(),
            "Subgrupo": prods["sub"].to_numpy(),
            "Unid.": prods["cant"].to_numpy(),
            "Venta": prods["venta"].to_numpy(),
            "% costo": (prods["costo"].where(prods["costo"] > 0)
                        / prods["neto"].replace(0, np.nan)).to_numpy(),
        })
        if nivel == 2:
            tabla = tabla.drop(columns=["Subgrupo"])
        st.dataframe(
            tabla, key=_key("vt_mix_top"), on_select="rerun",
            selection_mode="single-row", hide_index=True, row_height=27,
            height=alturas.VENTAS_MIX_TABLA,
            column_config={
                "Producto": st.column_config.TextColumn(
                    f"Lo más vendido · {corto[i]}", width="medium"),
                "Subgrupo": st.column_config.TextColumn(width="small"),
                "Unid.": st.column_config.NumberColumn(
                    format="%.0f", width="small"),
                "Venta": st.column_config.NumberColumn(
                    format="S/ %,.0f", width="small"),
                "% costo": st.column_config.NumberColumn(
                    format="percent", width="small",
                    help="Costo de la línea ÷ venta neta. Vacío: sin costo "
                         "cargado."),
            })
