"""
graficos.ventas_horario — vista «Por hora» del dashboard de Ventas: mapa de
calor DÍA × HORA de hasta cuatro períodos comparados, con marcas
rectangulares hechas a mano y drill al detalle de cada marca.

QUÉ ES UNA COLUMNA Y QUÉ ES UN PANEL
    La granularidad decide las dos cosas a la vez. Cada período elegido es un
    PANEL (una franja del mapa) y dentro de él las COLUMNAS son:

      · Día     1 columna  (el día entero)
      · Semana  7 columnas (lun → dom)
      · Mes     28-31      (día del mes)
      · Año     12         (mes)

    El eje Y son siempre las horas con dato — no 0-23 fijo: un local que abre
    a las 11 no gana nada mostrando doce filas vacías.

LOS CUATRO PANELES SE ELIGEN A MANO
    La franja de fecha del reporte define UN rango; acá hacen falta hasta
    cuatro períodos que pueden estar fuera de él (julio contra abril). Por eso
    cada panel se trae con `data.cargar_rango` — un tramo por panel, cacheado —
    y se le aplican LOS MISMOS chips vía `filtrar_cb`, igual que en
    ventas_comparativo: sin eso el mapa contradice los chips de la pantalla.

    En Mes y Año la celda es la SUMA del período (decisión del usuario,
    2026-08-14): "los viernes 19h de todo julio" es plata que entró, no un
    promedio. La consecuencia está avisada en el pie: bloques de distinto
    tamaño no se comparan por el total sino por «venta por celda».

LAS MARCAS SON RECTÁNGULOS, Y SIEMPRE
    Una marca es `(panel, col0..col1, hora0..hora1)`. La celda suelta es un
    rectángulo 1×1, "todo el viernes" es una columna entera y "las 19h de la
    semana" es una fila: un solo concepto en vez de tres modos de clic.

    Un arrastre que cruza de un panel al siguiente se PARTE en una marca por
    panel (opción A, elegida por el usuario el 2026-08-14): el gesto de
    arrastrar sobre dos semanas *es* la comparación, y dejarla armada de una
    pasada ahorra la mitad de los clics. Con más de cuatro se descartan las
    más viejas.

TRES TRAMPAS QUE YA ESTÁN RESUELTAS ACÁ (y que muerden si alguien las toca)

  1. `go.Heatmap` NO es seleccionable en Plotly: el box-select no emite nada
     sobre un heatmap. Por eso encima va una capa `go.Scatter` transparente,
     un marcador por celda, que sí soporta box/lasso y devuelve en su
     `customdata` a qué panel/columna/hora corresponde cada punto. Es también
     la que lleva el hover.

  2. Selección VACÍA no significa "borrá las marcas". Con `dragmode="select"`
     un clic al vacío devuelve una selección vacía; si las marcas se
     derivaran del evento en vez de acumularse en `session_state`, un clic
     torpe limpiaría el panel entero.

  3. La `key` del chart lleva la firma de las marcas. Con key estática la
     misma selección se re-procesa en cada rerun (CLAUDE.md § Streamlit) y el
     drill parpadea. Corolario que NO se puede evitar: re-arrastrar sobre una
     marca existente no la quita —`on_select` sólo dispara cuando la
     selección CAMBIA—, así que quitar marcas es cosa de las pastillas de
     abajo del mapa, no del mapa.
"""

import calendar as _cal
import datetime as _dt

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import REPORTES, cargar_rango
from tema import (
    ACENTO, ERROR, ESCALA_CONTINUA, EXITO, GRIS_TEXTO,
    PALETA_SERIES, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import _card, _resolver, franja_cabecera, franja_linea_inferior
# Los helpers de calendario NO se duplican: son los mismos que usa la vista
# "Año Pasado" y ya están cubiertos por test_graficos.py. Acá sólo se extienden
# para la granularidad Año, que allá no existe (comparar 2025 contra 2024 es
# justamente lo que esa vista hace por su cuenta).
from graficos.ventas_comparativo import (
    _DIAS_ES,
    _MESES_ES,
    _claves_hacia_atras as _claves_cmp,
    _etiqueta_clave as _etiqueta_cmp,
    _rango_de_clave as _rango_cmp,
)

GRANOS = ("Día", "Semana", "Mes", "Año")
MAX_MARCAS = 4

# Cuántos períodos ofrece el selector hacia atrás por granularidad. Más días
# que semanas a propósito: "los últimos 10 días" es una lista que se lee de un
# vistazo, "los últimos 10 años" es una lista que no existe en los datos.
_N_LISTA = {"Día": 10, "Semana": 8, "Mes": 9, "Año": 5}

# Color de cada marca. Salen de PALETA_SERIES (nunca un #hex suelto, CLAUDE.md)
# y están elegidos para que las cuatro se distingan entre sí SOBRE el azul del
# mapa: violeta, naranja, verde y cian.
_COLOR_MARCA = (PALETA_SERIES[0], PALETA_SERIES[3],
                PALETA_SERIES[4], PALETA_SERIES[1])

# id → (etiqueta, formato). El orden es el CANÓNICO de las filas/columnas del
# drill: no se reordena por orden de clic, que haría bailar la tabla bajo el
# cursor en cada pastilla que se toca.
_MEDIDAS = (
    ("venta",  "Venta"),
    ("pax",    "Pax"),
    ("cant",   "Cantidad"),
    ("ticket", "Ticket promedio"),
    ("desc",   "Descuento"),
)
_MED_LABEL = dict(_MEDIDAS)
_MED_FMT = {
    "venta": "S/ {:,.0f}", "pax": "{:,.0f}", "cant": "{:,.0f}",
    "ticket": "S/ {:,.2f}", "desc": "S/ {:,.0f}",
}

# Medidas que puede mostrar el ÁRBOL. Pax y ticket quedan fuera a propósito:
# a nivel de plato no existen (un pedido de 4 pax no reparte "1 pax" por
# plato), y una columna que miente es peor que una columna que falta.
_MED_ARBOL = ("venta", "cant", "desc")

# Tope de columnas numéricas del árbol. Con 4 marcas × 3 medidas serían 12
# columnas de números: ilegible en cualquier pantalla. Pasado el tope, el
# árbol se queda con la primera medida y lo dice.
_MAX_COLS_ARBOL = 8

# Geometría del mapa. El alto de la figura sigue al NÚMERO DE HORAS con dato
# (`alturas.por_filas`) en vez de estirarse siempre al techo de la tarjeta: un
# turno corto repartía el mismo alto entre menos filas y salían bandas con más
# aire que dato. 22px por hora es la fila compacta; el techo lo sigue poniendo
# `alturas.con_franja()`, así que un turno largo no desborda la pantalla.
_PX_HORA = 22
_AIRE_MAPA = 66    # títulos de panel + etiquetas del eje X + márgenes
_ALTO_MIN = 170    # con 3-4 horas la figura no se convierte en una cinta

# Cuántos períodos trae el arranque, por granularidad. Mes va SOLO: la vista
# por defecto es el mes en curso de corrido (pedido del usuario 2026-08-14 —
# "que sea de 30 días o del mes en curso"), no cuatro trozos que hay que
# volver a coser con la vista. Las otras granularidades sí abren comparando,
# que es para lo que existen.
_N_DEFECTO = {"Día": 4, "Semana": 4, "Mes": 1, "Año": 2}
_GRANO_DEF = "Mes"

_SIN_DSCTO = "Sin descuento"

_K_CLAVES = "vh_claves"      # períodos elegidos (lista de claves)
_K_MARCAS = "vh_marcas"      # marcas (lista de dicts)
_K_SELECTOR = "vh_selector"  # ¿está abierto el selector de períodos?


# ── Funciones puras (calendario) ────────────────────────────────────────────

def _claves_hacia_atras(ancla, grano, n):
    """Las `n` claves de período que terminan en el período de `ancla`."""
    if grano == "Año":
        return list(range(ancla.year - n + 1, ancla.year + 1))
    return _claves_cmp(ancla, grano, n)


def _rango_de_clave(clave, grano):
    """(primer_día, último_día) del período."""
    if grano == "Año":
        return _dt.date(clave, 1, 1), _dt.date(clave, 12, 31)
    return _rango_cmp(clave, grano)


def _etiqueta_clave(clave, grano):
    """Etiqueta corta del período — la que titula su panel."""
    if grano == "Año":
        return str(clave)
    return _etiqueta_cmp(clave, grano)


def _columnas(clave, grano, hasta=None):
    """(n_columnas, etiquetas) dentro de un período.

    En Mes el número depende del mes concreto (28/29/30/31): febrero no tiene
    31 columnas vacías al final, que se leerían como "cayó la venta".

    `hasta` recorta el período EN CURSO al último día con datos, por lo mismo:
    el 14 de agosto, "agosto" son 14 columnas, no 31 con diecisiete vacías a
    la derecha. Es la versión visual del recorte que `ventas_comparativo`
    hace sobre los totales (`_rangos_comparables`): un período a medias se
    muestra hasta donde llegó, no hasta donde llegará."""
    if grano == "Día":
        return 1, [""]
    if grano == "Semana":
        n, etiquetas = 7, list(_DIAS_ES)
    elif grano == "Mes":
        n = _cal.monthrange(clave[0], clave[1])[1]
        etiquetas = [str(i) for i in range(1, n + 1)]
    else:
        n, etiquetas = 12, list(_MESES_ES)
    if hasta is not None:
        ini, fin = _rango_de_clave(clave, grano)
        if ini <= hasta < fin:
            n = min(n, _columna_de_fecha(
                pd.Series([pd.Timestamp(hasta)]), grano).iat[0] + 1)
            etiquetas = etiquetas[:n]
    return n, etiquetas


def _columna_de_fecha(fechas, grano):
    """Índice de columna (0-based) de cada fecha dentro de su período."""
    if grano == "Día":
        return pd.Series(0, index=fechas.index, dtype="int64")
    if grano == "Semana":
        return fechas.dt.weekday
    if grano == "Mes":
        return fechas.dt.day - 1
    return fechas.dt.month - 1


def _orden_horas(horas):
    """Las horas con dato, ordenadas por DÍA DE SERVICIO y no por número.

    Un restaurante que cierra a la 1 de la mañana tiene ventas a las 00h, y
    esas 00h son el final de la noche anterior, no el principio del día. Con
    el orden numérico crudo salían primero (00h arriba de todo, antes de las
    13h) y además el eje numérico dejaba doce filas vacías entre medio —
    medido en la app con datos reales de R2 el 2026-08-14: el eje traía
    [0, 13, 14, …, 23].

    El corte se busca solo: se arranca justo DESPUÉS del hueco más grande del
    círculo de 24 horas. Con {0, 13..23} el hueco mayor es 01h→12h, así que
    el orden sale 13, 14, …, 23, 0 — el turno tal como se vive.
    """
    hs = sorted({int(h) % 24 for h in horas})
    if len(hs) <= 1:
        return hs
    # Hueco entre cada hora y la siguiente, cerrando el círculo al final.
    saltos = [((hs[(i + 1) % len(hs)] - h) % 24, i) for i, h in enumerate(hs)]
    _mayor, i = max(saltos)
    corte = (i + 1) % len(hs)
    return hs[corte:] + hs[:corte]


def _horas_entre(orden, h0, h1):
    """Las horas del tramo que va de `h0` a `h1` SEGÚN el orden de servicio.

    No es `range(h0, h1+1)`: en un turno que cruza la medianoche, "23h a 0h"
    son dos horas, y con la comparación numérica cruda serían las veinticuatro
    (0 ≤ h ≤ 23). Esa cuenta silenciosa habría inflado cualquier marca que
    tocara la medianoche."""
    if h0 not in orden or h1 not in orden:
        return [h for h in orden if min(h0, h1) <= h <= max(h0, h1)]
    p0, p1 = orden.index(h0), orden.index(h1)
    if p0 > p1:
        p0, p1 = p1, p0
    return orden[p0:p1 + 1]


def _etiqueta_columnas(pin, clave, grano):
    """Trozo 'vie–dom' / 'día 3–9' / 'ago–oct' de la etiqueta de una marca.
    Vacío en granularidad Día: ahí la columna ES el período, y repetirlo
    daría 'vie 08/08 · vie'."""
    if grano == "Día":
        return ""
    _n, etiquetas = _columnas(clave, grano)
    c0 = etiquetas[min(pin["c0"], _n - 1)]
    c1 = etiquetas[min(pin["c1"], _n - 1)]
    if grano == "Mes":
        return f"día {c0}" if c0 == c1 else f"días {c0}–{c1}"
    return c0 if c0 == c1 else f"{c0}–{c1}"


# ── Funciones puras (marcas) ────────────────────────────────────────────────

def _marca_de_puntos(sel, cols, horas, orden):
    """Rectángulo que ENVUELVE a los puntos seleccionados de un panel.

    Una selección de caja es rectangular por construcción, así que el
    envolvente no inventa nada: es exactamente lo que el usuario encerró. Los
    extremos de hora se toman por POSICIÓN en el orden de servicio, no por
    número: en un turno que cruza la medianoche, min/max numérico de
    {23, 0} daría "de 0h a 23h", o sea el día entero."""
    pos = [orden.index(h) for h in horas if h in orden] or [0]
    return {"sel": int(sel),
            "c0": int(min(cols)), "c1": int(max(cols)),
            "h0": int(orden[min(pos)]), "h1": int(orden[max(pos)])}


def _marcas_de_seleccion(puntos, orden):
    """Las marcas que sale de UNA selección, partida por panel (opción A).

    `puntos` son tuplas `(panel, columna, hora)`. Un arrastre que cruza de un
    panel al siguiente deja una marca en cada uno, con las coordenadas que le
    tocaron a cada lado — que no tienen por qué ser las mismas: el borde
    derecho de un mes de 31 días y el de uno de 30 no caen en el mismo sitio.
    """
    por_panel = {}
    for sel, col, hora in puntos:
        por_panel.setdefault(int(sel), []).append((int(col), int(hora)))
    out = []
    for sel in sorted(por_panel):
        cols = [c for c, _h in por_panel[sel]]
        horas = [h for _c, h in por_panel[sel]]
        out.append(_marca_de_puntos(sel, cols, horas, orden))
    return out


def _agregar_marcas(marcas, nuevas, tope=MAX_MARCAS):
    """Suma `nuevas` a `marcas` sin repetir y respetando el tope.

    Cuando se pasa del tope se van las MÁS VIEJAS, no las nuevas: un arrastre
    sobre los cuatro paneles tiene que dejar esas cuatro marcas, no las dos
    que quedaban de antes más dos de éstas."""
    out = list(marcas)
    for m in nuevas:
        if m not in out:
            out.append(m)
    return out[-tope:]


def _etiqueta_marca(pin, claves, grano):
    """'Sem 33 · vie–dom · 18–21h' — el nombre de una marca en pastillas,
    cabeceras de tabla y anotaciones del mapa. Uno solo, para que la misma
    marca no se llame de dos formas distintas en dos sitios."""
    clave = claves[pin["sel"]] if pin["sel"] < len(claves) else None
    per = _etiqueta_clave(clave, grano) if clave is not None else "?"
    cols = _etiqueta_columnas(pin, clave, grano) if clave is not None else ""
    horas = (f"{pin['h0']}h" if pin["h0"] == pin["h1"]
             else f"{pin['h0']}–{pin['h1']}h")
    return " · ".join(x for x in (per, cols, horas) if x)


def _celdas_de_marca(pin, orden):
    """Cuántas celdas (columna × hora) encierra la marca. Es el denominador de
    «venta por celda», la única lectura honesta cuando las marcas no miden lo
    mismo."""
    return (pin["c1"] - pin["c0"] + 1) * len(
        _horas_entre(orden, pin["h0"], pin["h1"]))


def _firma(grano, claves, medida, marcas):
    """Firma corta del estado que gobierna el mapa. Va en la `key` del chart:
    mientras no cambie, Streamlit reusa el widget; cuando cambia, lo remonta y
    la selección vieja se va con él (ver trampa 3 del docstring)."""
    _m = "|".join(f"{p['sel']},{p['c0']},{p['c1']},{p['h0']},{p['h1']}"
                  for p in marcas)
    return f"{grano}_{len(claves)}_{claves[0] if claves else '-'}_{medida}_{_m}"


# ── Datos ───────────────────────────────────────────────────────────────────

def _prep_tramo(df, c, grano, ini, fin):
    """Filas de un tramo con lo que necesitan el mapa Y el drill.

    Se prepara UNA vez y se usa dos: agregando por (columna, hora) sale el
    mapa; recortando al rectángulo de una marca y agrupando por
    grupo/subgrupo/plato/tipo sale el árbol.

    El recorte por fecha se re-aplica en pandas aunque `cargar_rango` filtre en
    DuckDB, por el mismo motivo que en ventas_comparativo: en modo demo (sin
    secrets de R2) el loader devuelve el df entero."""
    if df is None or df.empty or c["fecha"] not in df.columns:
        return None
    fe = pd.to_datetime(df[c["fecha"]], errors="coerce")
    m = fe.notna() & (fe.dt.date >= ini) & (fe.dt.date <= fin)
    if not m.any():
        return None
    fe = fe[m]
    out = pd.DataFrame({
        "col":  _columna_de_fecha(fe, grano).astype("int64").values,
        "hora": fe.dt.hour.astype("int64").values,
        "venta": pd.to_numeric(df.loc[m, c["venta"]],
                               errors="coerce").fillna(0.0).values,
    })
    for _id, _col in (("cant", "cant"), ("desc", "desc")):
        if c.get(_col) and c[_col] in df.columns:
            out[_id] = pd.to_numeric(df.loc[m, c[_col]],
                                     errors="coerce").fillna(0.0).values
        else:
            out[_id] = 0.0
    # Pax NO se suma línea a línea: `Cant Pax` se repite en cada línea del
    # pedido. Se guarda a nivel de fila y se deduplica por pedido al agregar
    # (mismo criterio que ventas_resumen y el comparativo).
    if c.get("pax") and c.get("pedido") \
            and c["pax"] in df.columns and c["pedido"] in df.columns:
        out["pax"] = pd.to_numeric(df.loc[m, c["pax"]], errors="coerce").values
        out["ped"] = df.loc[m, c["pedido"]].astype(str).values
    for _id, _col in (("grupo", "fam"), ("sub", "sub"), ("prod", "prod")):
        if c.get(_col) and c[_col] in df.columns:
            out[_id] = df.loc[m, c[_col]].astype(str).values
    if c.get("tipo_desc") and c["tipo_desc"] in df.columns:
        # El `fillna` va ANTES del `astype(str)` y no es paranoia: desde
        # pandas 2.1 `astype(str)` PRESERVA los nulos en vez de escribir
        # "None", así que sin esto la línea sin descuento se quedaba con NaN
        # y en el árbol habría colgado de un nodo fantasma en vez de caer en
        # «Sin descuento» (lo cazó test_graficos.py al construirlo).
        _t = df.loc[m, c["tipo_desc"]]
        _t = _t.where(_t.notna(), "").astype(str).str.strip()
        out["tipo"] = _t.mask(_t.str.lower().isin(("", "nan", "none")),
                              _SIN_DSCTO).values
    else:
        out["tipo"] = _SIN_DSCTO
    return out


def _celdas(tramo):
    """Agregado por celda: (col, hora) → venta, cant, desc, pax."""
    if tramo is None or tramo.empty:
        return None
    agg = {"venta": ("venta", "sum"), "cant": ("cant", "sum"),
           "desc": ("desc", "sum")}
    g = tramo.groupby(["col", "hora"], as_index=False).agg(**agg)
    if "pax" in tramo.columns:
        _t = tramo.dropna(subset=["pax"])
        if not _t.empty:
            _p = (_t.groupby(["col", "hora", "ped"], as_index=False)["pax"].max()
                  .groupby(["col", "hora"], as_index=False)["pax"].sum())
            g = g.merge(_p, on=["col", "hora"], how="left")
    if "pax" not in g.columns:
        g["pax"] = np.nan
    g["pax"] = g["pax"].fillna(0.0)
    # Ticket = venta/pax, la MISMA definición que ventas_resumen.py y el
    # comparativo. Sin pax no hay ticket (NaN), no un cero que se leería como
    # "mesas gratis".
    g["ticket"] = g["venta"] / g["pax"].replace(0, np.nan)
    return g


def _filas_de_marca(tramo, pin, orden):
    """Filas del tramo que caen DENTRO del rectángulo de la marca.

    El corte de horas va por `isin` sobre el orden de servicio y no por
    `h0 <= hora <= h1`: ver `_horas_entre`."""
    horas = _horas_entre(orden, pin["h0"], pin["h1"])
    return tramo[(tramo["col"] >= pin["c0"]) & (tramo["col"] <= pin["c1"])
                 & (tramo["hora"].isin(horas))]


def _agregar_marca(tramo, pin, orden):
    """Totales de una marca sobre su tramo (venta, cant, desc, pax, ticket)."""
    if tramo is None or tramo.empty:
        return {}
    t = _filas_de_marca(tramo, pin, orden)
    if t.empty:
        return {"venta": 0.0, "cant": 0.0, "desc": 0.0, "pax": 0.0,
                "ticket": np.nan}
    out = {
        "venta": float(t["venta"].sum()),
        "cant":  float(t["cant"].sum()),
        "desc":  float(t["desc"].sum()),
    }
    if "pax" in t.columns:
        _t = t.dropna(subset=["pax"])
        out["pax"] = (float(_t.groupby("ped")["pax"].max().sum())
                      if not _t.empty else 0.0)
    else:
        out["pax"] = 0.0
    out["ticket"] = (out["venta"] / out["pax"]) if out["pax"] else np.nan
    return out


def _detalle_marca(tramo, pin, orden):
    """Filas grupo/subgrupo/plato/tipo-de-descuento de una marca.

    El cuarto nivel (tipo) sale de `NOMBRE DESCUENTO`, que vive en la MISMA
    línea que el plato: relacionar un plato con el descuento que se le hizo no
    necesita ningún join. Las líneas sin descuento caen en «Sin descuento», y
    eso no es relleno: es la parte del plato que se vendió a precio de lista.
    """
    if tramo is None or tramo.empty or "prod" not in tramo.columns:
        return None
    t = _filas_de_marca(tramo, pin, orden)
    if t.empty:
        return None
    llaves = [k for k in ("grupo", "sub", "prod", "tipo") if k in t.columns]
    return t.groupby(llaves, as_index=False).agg(
        venta=("venta", "sum"), cant=("cant", "sum"), desc=("desc", "sum"))


# ── Figura ──────────────────────────────────────────────────────────────────

def _fig_mapa(paneles, claves, grano, medida, marcas, horas, ancla=None):
    """Mapa de calor de los N paneles en una sola figura, con la capa de
    selección transparente encima y un rectángulo por marca.

    Los paneles se concatenan en el eje X con UNA columna de hueco entre
    ellos (NaN, que Plotly deja sin pintar): así el eje de horas es uno solo
    a la izquierda y comparar es barrer la vista, sin tener que emparejar
    cuatro ejes distintos."""
    n_horas = len(horas)
    h_idx = {h: i for i, h in enumerate(horas)}
    # Eje Y CATEGÓRICO y no numérico: `horas` viene ordenado por día de
    # servicio (ver _orden_horas) y puede saltar de las 23h a las 00h. En un
    # eje numérico ese salto se dibuja como doce filas vacías; en uno
    # categórico las filas son las que hay, en el orden que se les dio.
    y_cat = [f"{h:02d}h" for h in horas]

    offs, total, ticks_pos, ticks_txt, titulos = [], 0, [], [], []
    for s, clave in enumerate(claves):
        n, etiquetas = _columnas(clave, grano, ancla)
        offs.append(total)
        # Con muchas columnas (Mes) las etiquetas se pisan: se muestra una de
        # cada k. En Día no hay etiqueta de columna — el título del panel ya
        # dice qué día es.
        paso = 1 if n <= 12 else (2 if n <= 16 else 5)
        for i, et in enumerate(etiquetas):
            if et and (i % paso == 0 or n <= 7):
                ticks_pos.append(total + i)
                ticks_txt.append(et)
        titulos.append((total + (n - 1) / 2, _etiqueta_clave(clave, grano)))
        total += n + 1          # +1 = la columna de hueco
    total = max(total - 1, 1)   # el último panel no lleva hueco a la derecha

    z = np.full((n_horas, total), np.nan)
    xs, ys, cd = [], [], []
    for s, celdas in enumerate(paneles):
        if celdas is None or celdas.empty:
            continue
        n, _et = _columnas(claves[s], grano, ancla)
        for fila in celdas.itertuples(index=False):
            if fila.hora not in h_idx or fila.col >= n:
                continue
            x = offs[s] + int(fila.col)
            valor = getattr(fila, medida, np.nan)
            z[h_idx[fila.hora], x] = valor
            xs.append(x)
            ys.append(y_cat[h_idx[fila.hora]])
            cd.append([s, int(fila.col), int(fila.hora),
                       float(fila.venta), float(fila.pax),
                       float(fila.cant), float(fila.desc),
                       float(fila.ticket) if pd.notna(fila.ticket) else 0.0])

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=z, x=list(range(total)), y=y_cat,
        colorscale=ESCALA_CONTINUA, hoverinfo="skip",
        xgap=1, ygap=1,
        colorbar=dict(thickness=10, outlinewidth=0, len=0.85,
                      tickfont=dict(size=10, color=GRIS_TEXTO)),
    ))
    if xs:
        # Capa de selección: invisible, pero es la ÚNICA que Plotly deja
        # seleccionar (un heatmap no emite eventos de selección). También es
        # la que lleva el hover, que por eso puede ser rico: en el heatmap
        # sólo habría `z`.
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(size=13, color="rgba(0,0,0,0)",
                        line=dict(width=0)),
            customdata=cd, showlegend=False,
            hovertemplate=(
                "<b>%{customdata[8]}</b> · %{y}<br>"
                "Venta: S/ %{customdata[3]:,.0f}<br>"
                "Pax: %{customdata[4]:,.0f} · "
                "Ticket: S/ %{customdata[7]:,.2f}<br>"
                "Cantidad: %{customdata[5]:,.0f} · "
                "Dscto: S/ %{customdata[6]:,.0f}<extra></extra>"),
        ))
        # El nombre legible de cada punto (panel + columna) va como noveno
        # campo del customdata: armarlo acá evita que el hover tenga que
        # entender de calendarios.
        _nombres = []
        for s, col, _h, *_r in cd:
            _n, _et = _columnas(claves[s], grano, ancla)
            _c = _et[col] if col < len(_et) and _et[col] else ""
            _nombres.append(" · ".join(
                x for x in (_etiqueta_clave(claves[s], grano), _c) if x))
        fig.data[-1].customdata = [c + [n] for c, n in zip(cd, _nombres)]

    for x, txt in titulos:
        fig.add_annotation(x=x, y=1.0, xref="x", yref="paper",
                           yanchor="bottom", showarrow=False, text=txt,
                           font=dict(size=12, color=TEXTO_PRINCIPAL))

    for i, pin in enumerate(marcas):
        if pin["sel"] >= len(claves):
            continue
        _hs = [h_idx[h] for h in _horas_entre(horas, pin["h0"], pin["h1"])
               if h in h_idx]
        if not _hs:
            continue
        x0 = offs[pin["sel"]] + pin["c0"] - 0.5
        x1 = offs[pin["sel"]] + pin["c1"] + 0.5
        # En un eje categórico las coordenadas numéricas son ÍNDICES de
        # categoría: 0 es el centro de la primera fila, así que ±0.5 son sus
        # bordes. Por eso el rectángulo se dibuja con posiciones y no con la
        # hora, que en este eje no significa nada.
        y0 = min(_hs) - 0.5
        y1 = max(_hs) + 0.5
        color = _COLOR_MARCA[i % len(_COLOR_MARCA)]
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(color=color, width=2), fillcolor="rgba(0,0,0,0)",
                      layer="above")
        fig.add_annotation(x=x0, y=y0, text=f" {i + 1} ", showarrow=False,
                           xanchor="left", yanchor="bottom",
                           font=dict(size=11, color="#ffffff"),
                           bgcolor=color, borderpad=1)

    fig.update_layout(
        # El alto SIGUE A LAS FILAS en vez de estirarse siempre al techo: con
        # `con_franja()` fijo, un turno de 8 horas repartía 373px entre 8
        # filas y salían bandas de 46px de alto por 28 de ancho — ladrillos
        # verticales con más aire que dato. `por_filas` clampea igual al
        # techo cuando hay muchas horas.
        height=alturas.por_filas(n_horas, px_fila=_PX_HORA, extra=_AIRE_MAPA,
                                 rol=alturas.con_franja(), minimo=_ALTO_MIN),
        margin=dict(l=10, r=10, t=34, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
        dragmode="select",     # sin esto el arrastre hace zoom, no selección
        showlegend=False,
    )
    fig.update_xaxes(tickvals=ticks_pos, ticktext=ticks_txt, showgrid=False,
                     zeroline=False, range=[-0.5, total - 0.5],
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    # Horas de arriba hacia abajo: el turno empieza arriba y termina abajo,
    # como se lee un horario. `reversed` sobre un eje de categorías pone la
    # PRIMERA categoría arriba, que es justo el arranque del servicio.
    fig.update_yaxes(type="category", autorange="reversed",
                     showgrid=False, zeroline=False, showticklabels=True,
                     automargin=True, tickfont=dict(size=10, color=GRIS_TEXTO))
    return fig


def _puntos_de_evento(evt):
    """Tuplas `(panel, columna, hora)` de la selección de `st.plotly_chart`.

    Tolerante a formatos (objeto o dict) como `_first_point`, y a puntos sin
    customdata: los del heatmap no lo llevan y hay que ignorarlos en vez de
    reventar."""
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        pts = (sel or {}).get("points", []) or []
    except Exception:
        return []
    out = []
    for p in pts:
        cd = p.get("customdata") if isinstance(p, dict) else None
        if not cd or len(cd) < 3:
            continue
        out.append((cd[0], cd[1], cd[2]))
    return out


# ── UI: selector de períodos ────────────────────────────────────────────────

def _toggle_selector():
    st.session_state[_K_SELECTOR] = not st.session_state.get(_K_SELECTOR, False)


def _selector_periodos(ancla, grano, claves):
    """Lista de períodos para elegir los hasta 4 paneles.

    NO usa `st.popover`: el patrón manual (botón + `session_state` + contenido
    en flujo) es el que ya eligió este proyecto para el panel "Detalle" del
    comparativo, y por el mismo motivo — acá además cada clic dispara un
    rerun, y un popover que se cierra en cada clic obligaría a reabrirlo
    cuatro veces para elegir cuatro períodos.

    Devuelve la lista de claves elegidas (cronológica)."""
    disponibles = _claves_hacia_atras(ancla, grano, _N_LISTA[grano])
    disponibles = list(reversed(disponibles))      # más reciente primero
    elegidas = [k for k in claves if k in disponibles] or claves

    st.button(f"Comparar · {len(elegidas)} de {MAX_MARCAS}",
              key="vh_btn_selector", on_click=_toggle_selector,
              icon=(":material/keyboard_arrow_up:"
                    if st.session_state.get(_K_SELECTOR) else
                    ":material/keyboard_arrow_down:"))
    if not st.session_state.get(_K_SELECTOR):
        return elegidas

    with st.container(key="vh_selector_panel"):
        _c1, _c2, _c3 = st.columns([1, 1, 4])
        with _c1:
            if st.button("Últimos 4", key="vh_preset_ult",
                         use_container_width=True):
                st.session_state[_K_CLAVES] = disponibles[:MAX_MARCAS][::-1]
                st.session_state[_K_MARCAS] = []
                st.rerun(scope="fragment")
        with _c2:
            if st.button("Actual vs anterior", key="vh_preset_dos",
                         use_container_width=True):
                st.session_state[_K_CLAVES] = disponibles[:2][::-1]
                st.session_state[_K_MARCAS] = []
                st.rerun(scope="fragment")

        lleno = len(elegidas) >= MAX_MARCAS
        cols = st.columns(5)
        for i, k in enumerate(disponibles):
            on = k in elegidas
            with cols[i % 5]:
                if st.button(("✓ " if on else "") + _etiqueta_clave(k, grano),
                             key=f"vh_per_{grano}_{i}",
                             use_container_width=True,
                             type="primary" if on else "secondary",
                             disabled=(not on and lleno)):
                    nuevas = ([x for x in elegidas if x != k] if on
                              else elegidas + [k])
                    if not nuevas:
                        st.warning("Elegí al menos un período.")
                    else:
                        # Orden cronológico SIEMPRE, no orden de clic: los
                        # paneles del mapa se leen de izquierda (más viejo) a
                        # derecha, y la marca base del drill es la primera.
                        st.session_state[_K_CLAVES] = sorted(
                            nuevas, key=lambda x: _rango_de_clave(x, grano)[0])
                        # Las marcas apuntan a un panel por ÍNDICE: si cambia
                        # la lista de paneles, el índice deja de significar lo
                        # mismo. Se limpian en vez de mentir.
                        st.session_state[_K_MARCAS] = []
                    st.rerun(scope="fragment")
        if lleno:
            st.caption(f"Ya hay {MAX_MARCAS} períodos: quitá uno para elegir "
                       "otro.")
    return elegidas


# ── UI: drill ───────────────────────────────────────────────────────────────

def _tabla_medidas(marcas, tramos, claves, grano, orden, medidas, ver_var):
    """Pivote marca × medida. Una fila por marca (así la tabla es ordenable y
    no crece a lo ancho con cada marca nueva) y una columna por medida activa,
    con su Δ contra la marca base al lado si el toggle está puesto."""
    filas, celdas = [], []
    for i, pin in enumerate(marcas):
        tot = _agregar_marca(tramos[pin["sel"]], pin, orden)
        tot["celdas"] = _celdas_de_marca(pin, orden)
        tot["venta_celda"] = (tot.get("venta", 0.0) / tot["celdas"]
                              if tot["celdas"] else np.nan)
        _d = tot.get("desc", 0.0)
        _v = tot.get("venta", 0.0)
        tot["pct_desc"] = (100 * _d / (_v + _d)) if (_v + _d) else np.nan
        filas.append(f"{i + 1} · {_etiqueta_marca(pin, claves, grano)}")
        celdas.append(tot)

    base = celdas[0] if celdas else {}
    datos = {}
    for mid, lab in _MEDIDAS:
        if mid not in medidas:
            continue
        datos[lab] = [c.get(mid, np.nan) for c in celdas]
        if ver_var:
            _b = base.get(mid)
            datos[f"Δ {lab}"] = [
                (100 * (c.get(mid, np.nan) - _b) / _b)
                if (_b not in (None, 0) and pd.notna(_b)
                    and pd.notna(c.get(mid, np.nan))) else np.nan
                for c in celdas]
        if mid == "desc":
            datos["% lista"] = [c.get("pct_desc", np.nan) for c in celdas]
    datos["Celdas"] = [c.get("celdas", 0) for c in celdas]
    mismo = len({c.get("celdas") for c in celdas}) <= 1
    if not mismo:
        datos["Venta/celda"] = [c.get("venta_celda", np.nan) for c in celdas]

    tv = pd.DataFrame(datos, index=filas)
    fmt = {}
    for mid, lab in _MEDIDAS:
        if lab in tv.columns:
            fmt[lab] = _MED_FMT[mid]
        if f"Δ {lab}" in tv.columns:
            fmt[f"Δ {lab}"] = "{:+.0f}%"
    fmt.update({"% lista": "{:.1f}%", "Celdas": "{:,.0f}",
                "Venta/celda": "S/ {:,.0f}"})
    fmt = {k: v for k, v in fmt.items() if k in tv.columns}

    def _sty_var(v):
        if pd.isna(v):
            return f"color:{GRIS_TEXTO}"
        return f"color:{EXITO}" if v >= 0 else f"color:{ERROR}"

    _cols_var = [c for c in tv.columns if c.startswith("Δ ")]
    sty = tv.style.format(fmt, na_rep="—")
    if _cols_var:
        sty = sty.map(_sty_var, subset=_cols_var)
    st.dataframe(sty, use_container_width=True,
                 height=alturas.por_filas(len(tv), px_fila=35, extra=48,
                                          minimo=0, rol=alturas.MINI))
    return mismo


def _tabla_arbol(marcas, tramos, claves, grano, orden, medidas_arbol):
    """Árbol Grupo › Sub Grupo › Plato › Tipo de descuento, una columna por
    marca y medida.

    AgGrid y no HTML: el agrupamiento con expandir/colapsar ya existe en este
    proyecto (Matriz agrupada) y reimplementarlo a mano sería reescribir
    gratis lo que la grilla da hecho. El tinte va por `cellStyle`, NUNCA por
    `cellRenderer` devolviendo HTML — acá eso se ve como texto escapado
    (arquitectura.md regla #25)."""
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode  # noqa: E402

    detalles = [_detalle_marca(tramos[p["sel"]], p, orden) for p in marcas]
    if all(d is None or d.empty for d in detalles):
        st.info("Sin ventas de productos en las marcas elegidas.")
        return

    llaves = ["grupo", "sub", "prod", "tipo"]
    wide = None
    for i, det in enumerate(detalles):
        if det is None or det.empty:
            continue
        _ll = [k for k in llaves if k in det.columns]
        d2 = det.rename(columns={m: f"{m}_{i}" for m in _MED_ARBOL})
        wide = d2 if wide is None else wide.merge(d2, on=_ll, how="outer")
    if wide is None or wide.empty:
        st.info("Sin ventas de productos en las marcas elegidas.")
        return
    for k in llaves:
        if k not in wide.columns:
            wide[k] = "—"
        wide[k] = wide[k].fillna("—")
    for i in range(len(marcas)):
        for m in _MED_ARBOL:
            col = f"{m}_{i}"
            if col not in wide.columns:
                wide[col] = 0.0
            wide[col] = pd.to_numeric(wide[col], errors="coerce").fillna(0.0)

    activas = [m for m in _MED_ARBOL if m in medidas_arbol] or ["venta"]
    recortado = len(marcas) * len(activas) > _MAX_COLS_ARBOL
    if recortado:
        activas = activas[:1]

    gb = GridOptionsBuilder.from_dataframe(wide)
    gb.configure_default_column(resizable=True, sortable=False, filter=False,
                                suppressMenu=True)
    gb.configure_column("grupo", header_name="Grupo", rowGroup=True, hide=True)
    gb.configure_column("sub", header_name="Sub Grupo", rowGroup=True, hide=True)
    gb.configure_column("prod", header_name="Plato", rowGroup=True, hide=True)
    gb.configure_column("tipo", header_name="Descuento", hide=True)

    fmt_soles = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '';
          return 'S/ '+Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:0});}
    """)
    fmt_num = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '';
          return Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:0});}
    """)

    # rgb del acento, calculado desde tema.py y no escrito a mano: la regla
    # «nunca un #hex suelto» vale también dentro de un blob de JS.
    _rgb = ",".join(str(int(ACENTO.lstrip("#")[i:i + 2], 16))
                    for i in (0, 2, 4))

    def _heat_fila(campos):
        """Tinte que compara la FILA entre marcas (no la columna entre filas):
        la pregunta del árbol es «este plato, ¿cómo le fue en cada marca?».
        `aggData` es lo que traen las filas de grupo — sin ese fallback, los
        niveles agrupados salen sin tinte."""
        _f = "[" + ",".join(f"'{c}'" for c in campos) + "]"
        return JsCode(f"""
            function(p){{
              var f={_f};
              var d=p.data||(p.node&&p.node.aggData)||{{}};
              var mx=0;
              for(var i=0;i<f.length;i++){{
                var v=Number(d[f[i]]||0); if(v>mx)mx=v;
              }}
              var v=Number(p.value||0);
              if(!(mx>0)||!(v>0))return null;
              var q=v/mx;
              var a=q>=0.999?0.26:(q>=0.66?0.17:(q>=0.33?0.10:0.05));
              return {{backgroundColor:'rgba({_rgb},'+a+')'}};
            }}
        """)

    columnDefs = []
    for i, pin in enumerate(marcas):
        hijos = []
        for m in activas:
            campos = [f"{m}_{j}" for j in range(len(marcas))]
            hijos.append({
                "field": f"{m}_{i}",
                "headerName": {"venta": "Venta", "cant": "Cant",
                               "desc": "Dscto"}[m],
                "type": "numericColumn", "width": 108, "aggFunc": "sum",
                "valueFormatter": fmt_num if m == "cant" else fmt_soles,
                "cellStyle": _heat_fila(campos),
            })
        columnDefs.append({
            "headerName": f"{i + 1} · {_etiqueta_marca(pin, claves, grano)}",
            "children": hijos,
        })

    opciones = gb.build()
    _base_defs = [c for c in opciones.get("columnDefs", [])
                  if c.get("field") in llaves]
    opciones["columnDefs"] = _base_defs + columnDefs
    opciones["groupDisplayType"] = "singleColumn"
    opciones["groupDefaultExpanded"] = 1
    opciones["animateRows"] = True
    opciones["suppressAggFuncInHeader"] = True
    opciones["autoGroupColumnDef"] = {
        "headerName": "Grupo / Sub Grupo / Plato / Descuento",
        "field": "tipo", "pinned": "left", "minWidth": 300,
        "cellRendererParams": {"suppressCount": False},
    }

    _b1, _b2, _b3 = st.columns([1, 1, 5])
    with _b1:
        _exp = st.button("⤢ Expandir todo", key="vh_arbol_exp",
                         use_container_width=True)
    with _b2:
        _col = st.button("⤡ Colapsar", key="vh_arbol_col",
                         use_container_width=True)
    if _exp:
        opciones["groupDefaultExpanded"] = -1
    elif _col:
        opciones["groupDefaultExpanded"] = 0

    AgGrid(wide, gridOptions=opciones, allow_unsafe_jscode=True,
           theme="streamlit", height=alturas.PROTAGONISTA,
           enable_enterprise_modules=True,
           key=f"vh_arbol_{len(marcas)}_{'_'.join(activas)}",
           reload_data=False)
    st.caption(
        ("Sólo se muestra la primera medida: con "
         f"{len(marcas)} marcas, más de una no entra a lo ancho. "
         if recortado else "")
        + "El último nivel es el tipo de descuento aplicado a ese plato "
        "(«Sin descuento» = lo que se vendió a precio de lista). El tinte "
        "compara cada fila ENTRE marcas.")


# ── Vista ───────────────────────────────────────────────────────────────────

@st.fragment
def _ventas_horario(d, col_venta, col_fecha, col_pax=None, col_pedido=None,
                    col_prod=None, col_cant=None, col_fam=None, col_sub=None,
                    filtrar_cb=None):
    """Mapa de calor día × hora de hasta 4 períodos, con marcas y drill."""
    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el mapa por hora.")
        return

    _fe = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
    if _fe.empty:
        st.info("Sin fechas válidas en el rango cargado.")
        return
    ancla = _fe.max().date()

    # Descuento: dos columnas distintas y sólo una es el MONTO.
    # `DESCUENTO ITEM DDOCUMENTO` es el descuento de la línea (ya
    # multiplicado por la cantidad); `PRECIO DESCUENTO ITEM DDOCUMENTO` es el
    # UNITARIO y sumarlo da de menos — verificado contra R2 el 2026-08-14:
    # PRECIO OFICIAL × CANTIDAD = VENTA + DESCUENTO da exacto, o sea que
    # `VENTA ITEM DDOCUMENTO` ya viene NETA y el descuento se suma aparte,
    # nunca se resta otra vez.
    col_desc = _resolver(d, ["Descuento Item Ddocumento", "Descuento"])
    col_tipo = _resolver(d, ["Nombre Descuento"])

    cols = {"fecha": col_fecha, "venta": col_venta, "pax": col_pax,
            "pedido": col_pedido, "prod": col_prod, "cant": col_cant,
            "fam": col_fam, "sub": col_sub, "desc": col_desc,
            "tipo_desc": col_tipo}

    _grano_prev = st.session_state.get("vh_grano") or _GRANO_DEF
    with _card(f"ventas_horario_{_grano_prev}"):
        _ph_hdr = st.empty()
        c1, c2, c3 = st.columns([1.5, 2.2, 1.3])
        with c1:
            grano = st.pills("Granularidad", list(GRANOS),
                             default=_GRANO_DEF, key="vh_grano",
                             label_visibility="collapsed") or _GRANO_DEF
        with c2:
            # Medida del MAPA: control propio y no "la primera del drill"
            # (decisión del usuario, 2026-08-14). El color sólo puede
            # codificar una cosa, y cuál es cambia el mapa por completo: por
            # venta manda el volumen, por ticket aparecen las horas de mesas
            # caras, que son otras.
            _op_mapa = [lab for mid, lab in _MEDIDAS
                        if mid != "desc" or col_desc]
            medida_lab = st.pills("Color", _op_mapa, default="Venta",
                                  key="vh_medida_mapa",
                                  label_visibility="collapsed") or "Venta"
        medida = next(mid for mid, lab in _MEDIDAS if lab == medida_lab)

        # Si cambió la granularidad, las claves y las marcas viejas dejan de
        # significar lo mismo (una columna de "Semana" no es una de "Mes").
        if st.session_state.get("vh_grano_aplicado") != grano:
            st.session_state["vh_grano_aplicado"] = grano
            st.session_state[_K_CLAVES] = None
            st.session_state[_K_MARCAS] = []

        claves = st.session_state.get(_K_CLAVES)
        if not claves:
            claves = _claves_hacia_atras(ancla, grano,
                                         _N_DEFECTO.get(grano, MAX_MARCAS))
            st.session_state[_K_CLAVES] = claves

        with c3:
            claves = _selector_periodos(ancla, grano, claves)

        franja_cabecera(_ph_hdr, "Mapa de venta por día y hora")
        franja_linea_inferior()

        # ── Datos: un tramo por panel ───────────────────────────────────
        cfg = REPORTES.get("Ventas", {})
        _arch = cfg.get("archivo", "ventas.parquet")
        _colp = cfg.get("carga_por_rango", "FEC REG DOCUMENTO")
        tramos, paneles = [], []
        for k in claves:
            ini, fin = _rango_de_clave(k, grano)
            fin = min(fin, ancla)
            df = cargar_rango(_arch, _colp, ini, fin)
            if df is not None and not df.empty and filtrar_cb is not None:
                df = filtrar_cb(df)
            t = _prep_tramo(df, cols, grano, ini, fin)
            tramos.append(t)
            paneles.append(_celdas(t))

        # Ordenadas por día de servicio, no por número: ver _orden_horas.
        horas = _orden_horas({int(h) for c in paneles if c is not None
                              for h in c["hora"].unique()})
        if not horas:
            st.info("Sin ventas con hora en los períodos elegidos.")
            return

        marcas = [m for m in st.session_state.get(_K_MARCAS, [])
                  if m["sel"] < len(claves)]
        fig = _fig_mapa(paneles, claves, grano, medida, marcas, horas, ancla)
        evt = st.plotly_chart(
            fig, use_container_width=True,
            key=f"vh_mapa_{_firma(grano, claves, medida, marcas)}",
            on_select="rerun", selection_mode=("points", "box"),
            config={"displaylogo": False, "displayModeBar": False})

        puntos = _puntos_de_evento(evt)
        if puntos:
            nuevas = _agregar_marcas(marcas, _marcas_de_seleccion(puntos, horas))
            if nuevas != marcas:
                st.session_state[_K_MARCAS] = nuevas
                st.rerun(scope="fragment")

        # ── Pastillas de marcas: deseleccionar una la quita ─────────────
        if marcas:
            etiquetas = [f"{i + 1} · {_etiqueta_marca(p, claves, grano)}"
                         for i, p in enumerate(marcas)]
            # Key por firma (regla #9): las opciones cambian con las marcas y
            # un pills que conserva un valor fuera de su lista nueva se queda
            # sin selección.
            vivos = st.pills(
                "Marcas", etiquetas, selection_mode="multi", default=etiquetas,
                key=f"vh_marcas_pills_{len(marcas)}_{hash(tuple(etiquetas))}",
                label_visibility="collapsed")
            if vivos is not None and len(vivos) != len(etiquetas):
                st.session_state[_K_MARCAS] = [
                    p for e, p in zip(etiquetas, marcas) if e in vivos]
                st.rerun(scope="fragment")
            st.caption(
                "Arrastrá sobre el mapa para marcar un bloque — un arrastre "
                "que cruza de un panel al siguiente deja una marca en cada "
                "uno. Tocá una pastilla para quitarla. La marca 1 es la base "
                "de los % del detalle.")
        else:
            st.caption(
                "Arrastrá sobre el mapa para marcar un bloque de días y horas "
                f"(hasta {MAX_MARCAS}) y compararlos abajo. Un arrastre que "
                "cruza de un panel al siguiente deja una marca en cada uno.")

    # ── Drill ───────────────────────────────────────────────────────────
    # Las dos tarjetas se abren SIEMPRE, aunque no haya marcas, y por dentro
    # deciden si tienen algo que decir. NO es cosmético: un
    # `st.container(key=...)` que deja de renderizarse RETIENE sus hijos
    # (arquitectura.md regla #70). Medido acá el 2026-08-14: al cambiar la
    # granularidad las marcas se limpian, el `return` temprano se saltaba
    # estas dos tarjetas... y seguían en pantalla con los números de la
    # granularidad anterior. Vacías no se ven —el CSS de estilos/_80_cards.py
    # les quita borde y sombra dentro de la card de Ventas—, así que
    # dibujarlas siempre no cuesta un pixel.
    with _card("ventas_horario_medidas",
               "Medidas de cada marca" if marcas else "", titulo_arriba=True):
        if marcas:
            _op = [lab for mid, lab in _MEDIDAS
                   if (mid != "desc" or col_desc)
                   and (mid not in ("pax", "ticket")
                        or (col_pax and col_pedido))]
            _def = [lab for lab in ("Venta", "Pax", "Ticket promedio")
                    if lab in _op]
            _sel = st.pills("Medidas", _op, selection_mode="multi",
                            default=_def, key="vh_medidas",
                            label_visibility="collapsed")
            if not _sel:
                st.caption("Elegí al menos una medida.")
                _sel = _def
            medidas = {mid for mid, lab in _MEDIDAS if lab in _sel}
            ver_var = st.toggle("% variación contra la marca 1", value=True,
                                key="vh_ver_var")
            mismo = _tabla_medidas(marcas, tramos, claves, grano, horas,
                                   medidas, ver_var)
            if not mismo:
                st.caption("⚠️ Las marcas no miden lo mismo: compará por "
                           "«Venta/celda», no por el total — un rectángulo de "
                           "12 celdas gana siempre contra uno de 3.")

    # ── Drill: árbol Grupo › Sub Grupo › Plato › Descuento ──────────────
    with _card("ventas_horario_arbol",
               ("Detalle por grupo, subgrupo y plato"
                if (marcas and col_prod) else ""), titulo_arriba=True):
        if marcas and col_prod:
            _opa = [_MED_LABEL[m] for m in _MED_ARBOL
                    if m != "desc" or col_desc]
            _sela = st.pills("Detalle por", _opa, selection_mode="multi",
                             default=[_MED_LABEL["venta"]],
                             key="vh_medidas_arbol",
                             label_visibility="collapsed")
            medidas_arbol = {m for m in _MED_ARBOL
                             if _MED_LABEL[m] in (_sela or [])} or {"venta"}
            _tabla_arbol(marcas, tramos, claves, grano, horas, medidas_arbol)
