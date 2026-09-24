"""graficos.movimientos_periodo - «Requerimientos por período», la primera
tarjeta de Movimientos.

Nació el 2026-09-23, a pedido: «poner en primera vista una tarjeta como la
que tengo para la vista compras por período […] donde el gráfico de barra
sea de los requerimientos. Y abajo pueda alternar entre una vista resumida y
detallado». Reemplaza a «Top productos · requerim.», que se retiró el mismo
día: qué productos se piden más lo contesta ahora el selector de Producto de
esta tarjeta («Top 5/10/20 por valor») y la tabla de productos al pie de
«Por sub almacén».

ES LA GEMELA DE «COMPRAS POR PERÍODO» (graficos/compras/semanal.py), y a
propósito comparte sus cuentas en vez de copiarlas: el plan de las
etiquetas, el techo del eje, los nombres de los períodos, el calendario del
eje en Día y la variación contra la barra anterior salen de allá y de
`graficos/compras/_comun.py`. Si una de esas cambia, cambia en las dos
tarjetas — que es lo que se quiere: se leen igual. También mide lo que
aquélla (`alturas.SEMANAL_*`), con la misma zona de abajo: «Resumen», una
fila por barra, y «Detalle», los requerimientos del período en foco con las
líneas del elegido al costado (`tablas/movimientos_periodo.py`).

LO QUE LA HACE DISTINTA, medido contra `requerimientos.parquet` el
2026-09-23 (`arquitectura.md` regla #508):

  · Cada requerimiento tiene UNA sola área (Sub Almacén), UN estado y UNA
    fecha de registro — los 20.086, sin excepción. El área es al
    requerimiento lo que el proveedor a una compra, y por eso la barra se
    PARTE POR ÁREA (las tres mayores de la vista y «Resto»): la pregunta de
    un requerimiento es quién pidió. El color sigue al área, no a su puesto
    (`colores_area`).
  · Los ANULADOS no suman en barras ni totales y se cuentan en la columna
    Estado, que escribe SÓLO la excepción (regla #239: el 97 % está
    procesado). Valen poco pero no cero: los 20 del último mes, S/ 60 —la
    mitad llega con cantidad 0—; los de 2026, S/ 15.868, el 0,9 % del año.
    Por eso el total de esta tarjeta puede quedar un poco por debajo del de
    «Por sub almacén», que sí los suma (regla #322).
  · Los requerimientos SIN ÍTEMS —una línea sin producto, cantidad ni
    valor: 53 de 550 en el último mes, 49 de ellos de GASTOS, y el 15 % del
    histórico— no se cuentan ni como requerimientos ni como líneas:
    inflarían las dos cuentas sin sumar un sol. Lo dice la fila de KPI.
  · Sin granularidad «Por requerimiento» (el «Por documento» de Compras):
    un mes son ~480 requerimientos, o sea ~480 barras.

NO TIENE FRAGMENT PROPIO, a diferencia de la de Compras: aquélla lo necesita
por su selector de fecha, que escala a una corrida completa (regla #311).
Ésta sigue a la fecha de la franja, así que corre dentro del fragment de su
sección (`seccion_perezosa`) y ningún control suyo escala.

Punto de entrada: `tarjeta_requerimientos_periodo()`. Lo demás son las
piezas puras que lo arman, y que `test_graficos.py` prueba sin navegador.
"""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
from tema import GRIS_TEXTO, GRIS_TEXTO_SUAVE, PALETA_SERIES, TEXTO_PRINCIPAL
from graficos import alturas
from graficos.base import _compras_layout, _compras_truncar, scope_rerun
from graficos.compras._comun import (
    GAP_DRILL, _UNIDAD_GRAN, _clave_grilla, _first_point, _fmt_variacion,
    _hover_variacion, _nota_variacion, _periodo_serie, _variaciones,
)
# LAS CUENTAS DE LA GEMELA. Privadas de allá, y a propósito: esta tarjeta
# tiene que leerse igual que «Compras por período», y dos copias de «cuánto
# entra en la etiqueta de una barra» se separan al primer retoque.
from graficos.compras.semanal import (
    _AGRUPADO_GRAN, _ATENUADO, _ETQ_FUENTE, _ETQ_SEP, _LIENZO_PX,
    _TICK_AIRE, _TICK_PX_CARACTER, _anio_semana, _calendario_del_eje,
    _clave_del_clic, _con_alpha, _del_al, _plan_etiquetas, _rotulo_periodo,
    _techo_etiquetas,
)
from graficos.movimientos_comun import _rango_vigente
from tablas.movimientos_periodo import (
    ESTADO_OK, renderizar_lineas_req, renderizar_periodos_req,
    renderizar_requerimientos,
)
from utils import fmt_k


# ===========================================================================
# CENTINELAS, OPCIONES Y ESTADOS
# ===========================================================================
# Los centinelas se comparan por igualdad contra lo que devuelve el widget,
# como en Compras: ninguna área, familia ni producto del parquet empieza
# con «Todas las», «Todos los» ni «Top ».
_AREA_TODAS = "Todas las áreas"
_FAM_TODAS = "Todas las familias"
_PROD_TODOS = "Todos los productos"
_TOPS = (5, 10, 20)
"""Los «Top N por valor» del selector de producto — los de Compras. Son lo
que reemplaza a la vista «Top productos · requerim.»: el top ya no es un
gráfico aparte sino un recorte de ÉSTE."""

_GRAN_OPCIONES = ("Día", "Semana", "Mes", "Año")
_GRAN_DEFAULT = "Semana"
"""Abre por semana, como Compras (2026-09-20). Sobre el rango de la franja
—por defecto el mes en curso— son cuatro o cinco barras."""

_GRAN_VARIACION = ("Día", "Semana", "Mes")
"""Dónde la etiqueta dice cuánto cambió contra la barra anterior: las de
Compras. Año no: con el rango de entrada es una barra sola."""

_MODO_RESUMEN = "Resumen"
_MODO_DETALLE = "Detalle"
_MODO_OPCIONES = (_MODO_RESUMEN, _MODO_DETALLE)
_MODO_DEFAULT = _MODO_RESUMEN
"""Abre en Resumen, al revés que Compras: el Resumen nunca está vacío y el
Detalle, sin una barra elegida, sí. Una tarjeta NUEVA puede elegir con qué
abre; la de Compras abre en Detalle porque era lo que hacía antes de tener
modos."""

_AYUDA_MODO = (
    "Qué se ve debajo del gráfico. **Resumen**: una fila por barra —sus "
    "requerimientos, líneas, áreas, valorizado, variación y estado— más el "
    "total. **Detalle**: los requerimientos de la barra que toques y, al "
    "costado, las líneas del que elijas."
)

_ANULADO = "ANULADO"
_GENERADO = "GENERADO"
"""Los estados del parquet (`NOMBRE ESTADO REQUERIMIENTO`): PROCESADO,
ANULADO y GENERADO. GENERADO no tiene `FECHA PROCESADO` en ninguna de sus
266 líneas, así que la tarjeta lo llama «sin procesar» — es lo único que se
sabe de él."""

_AREAS_TRAZA = 3
"""Áreas con color propio en la barra; el resto se suma en «Resto». Con
cuatro o menos en la vista van todas, sin «Resto»: sería un tramo de una
sola área con otro nombre. Medido en el último mes: Cocina y Producción
son el 84 % del valorizado y la tercera, Barra, el 5 %."""

_ALTO_FIG_SOLO = alturas.SEMANAL_SOLO - alturas.FRANJA_MODO_SEMANAL
_ALTO_TABLA = alturas.SEMANAL_TABLA - alturas.FRANJA_MODO_SEMANAL
"""La tarjeta mide lo que «Compras por período», con el mismo reparto: la
fila de modo la paga la figura cuando no hay tabla y la tabla cuando la hay
(regla #476)."""


def _oracion(txt, vacio=""):
    """«LIMPIEZA Y MANTENIMIENTO» → «Limpieza y mantenimiento».

    El ERP escribe áreas y familias en mayúsculas, y en una fila de KPI o un
    hover eso se lee a los gritos — el mismo criterio que
    `semanal._nombre_familia`."""
    t = str(txt or "").strip()
    return t[:1].upper() + t[1:].lower() if t else vacio


def _nombre_area(area):
    return _oracion(area, "Sin área")


# ===========================================================================
# LAS PIEZAS PURAS (las prueba `test_graficos.py`, sin Streamlit)
# ===========================================================================

def _texto(d, col, vacio=""):
    """La columna `col` como texto limpio, o `vacio` si falta o viene vacía."""
    if not col or col not in d.columns:
        return pd.Series(vacio, index=d.index, dtype=object)
    s = d[col].fillna("").astype(str).str.strip()
    return s.mask(s == "", vacio)


def lineas_requerimientos(d, *, fecha, req, area, estado, fam, prod, cant,
                          punit, val):
    """Las líneas de `requerimientos.parquet` con los nombres de esta tarjeta.

    Una fila por línea: `fecha`, `req` (el código), `area`, `estado` (en
    mayúsculas), `fam`, `prod`, `cant`, `punit`, `valor` y `vacio` — True
    en la línea SIN PRODUCTO, que es la forma de un requerimiento sin ítems
    (regla #508). Los argumentos son los NOMBRES de columna del parquet, ya
    resueltos; el que falta cae a un valor neutro en vez de romper:
    sin código cada fila es su propio requerimiento, sin estado todos
    cuentan como procesados."""
    idx = d.index
    out = pd.DataFrame({
        "fecha": pd.to_datetime(d[fecha], errors="coerce"),
        "req": (_texto(d, req) if req and req in d.columns
                else pd.Series(idx.astype(str), index=idx)),
        "area": _texto(d, area, "Sin área"),
        "estado": _texto(d, estado, "PROCESADO").str.upper(),
        "fam": _texto(d, fam),
        "prod": _texto(d, prod),
        "cant": (pd.to_numeric(d[cant], errors="coerce") if cant
                 else pd.Series(float("nan"), index=idx)),
        "punit": (pd.to_numeric(d[punit], errors="coerce") if punit
                  else pd.Series(float("nan"), index=idx)),
        "valor": pd.to_numeric(d[val], errors="coerce").fillna(0.0),
    })
    out["vacio"] = out["prod"] == ""
    return out.dropna(subset=["fecha"])


def orden_areas(df, col_area, col_val):
    """Las áreas de `df` de mayor a menor valorizado: el orden ESTABLE con
    el que `colores_area` reparte los colores. Se le pasa el parquet
    entero, no el rango: el color de Cocina no puede cambiar porque un mes
    Producción pidió más."""
    if (df is None or not col_area or not col_val
            or col_area not in df.columns or col_val not in df.columns):
        return []
    t = pd.DataFrame({
        "area": df[col_area].fillna("").astype(str).str.strip(),
        "valor": pd.to_numeric(df[col_val], errors="coerce").fillna(0.0),
    })
    return (t.groupby("area")["valor"].sum().sort_values(ascending=False)
             .index.tolist())


def colores_area(orden, nombres):
    """`{área: color}` para las áreas de `nombres`, con el color que les
    toca por su puesto en `orden` —el histórico— y no por su puesto en la
    vista: filtrar no puede repintar (el color sigue a la entidad). Si dos
    de las que se dibujan juntas caen en el mismo color de la paleta, la
    segunda toma el siguiente libre."""
    ix = {a: i for i, a in enumerate(orden)}
    usados, salida = set(), {}
    for a in nombres:
        i = ix.get(a, len(orden) + len(salida))
        c = PALETA_SERIES[i % len(PALETA_SERIES)]
        while c in usados and len(usados) < len(PALETA_SERIES):
            i += 1
            c = PALETA_SERIES[i % len(PALETA_SERIES)]
        usados.add(c)
        salida[a] = c
    return salida


def resumen_por_periodo(dl):
    """Una fila por período —la columna `clave` de `dl`—, en orden.

    Columnas, por NOMBRE: `valor`, `lineas`, `reqs` y `areas` de las líneas
    VÁLIDAS (sin anulados; `dl` ya viene sin las líneas vacías), y
    `anulados` y `sin_procesar`, que se cuentan en requerimientos. Un
    período que sólo tiene anulados no tiene barra y no sale: sus anulados
    siguen en el total de la fila de KPI."""
    dv = dl[dl["estado"] != _ANULADO]
    g = (dv.groupby("clave")
           .agg(valor=("valor", "sum"), lineas=("valor", "size"),
                reqs=("req", "nunique"), areas=("area", "nunique"))
           .sort_index())
    an = dl[dl["estado"] == _ANULADO].groupby("clave")["req"].nunique()
    sp = dv[dv["estado"] == _GENERADO].groupby("clave")["req"].nunique()
    g["anulados"] = an.reindex(g.index).fillna(0).astype(int)
    g["sin_procesar"] = sp.reindex(g.index).fillna(0).astype(int)
    return g


def trazas_por_area(dv, ord_claves, orden):
    """`[(nombre, color, [valor por período]), …]`: los tramos de la barra.

    Las `_AREAS_TRAZA` mayores de la VISTA, de abajo hacia arriba, y
    «Resto» con lo que falta para el total de cada período — el resto no se
    vuelve a sumar por área, así la barra cierra por construcción. Con
    cuatro áreas o menos van todas y no hay «Resto». Un área que suma 0 no
    tiene tramo (seguiría contando en «Áreas»)."""
    tot = dv.groupby("area")["valor"].sum().sort_values(ascending=False)
    tot = tot[tot > 0]
    if tot.empty:
        return []
    por = (dv.groupby(["clave", "area"])["valor"].sum()
             .unstack("area").reindex(ord_claves).fillna(0.0))
    nombres = (list(tot.index) if len(tot) <= _AREAS_TRAZA + 1
               else list(tot.index[:_AREAS_TRAZA]))
    col = colores_area(orden, nombres)
    trazas = [(a, col[a], [float(v) for v in por[a]]) for a in nombres]
    if len(nombres) < len(tot):
        totales = dv.groupby("clave")["valor"].sum().reindex(ord_claves)
        acum = por[nombres].sum(axis=1)
        trazas.append(("Resto", GRIS_TEXTO_SUAVE,
                       [max(float(t) - float(a), 0.0)
                        for t, a in zip(totales.fillna(0.0), acum)]))
    return trazas


def _texto_estado(anulados, sin_procesar):
    """`(texto, clase)` de la columna Estado: sólo la excepción (#239)."""
    partes = []
    if anulados:
        partes.append(f"{anulados:,} anulado" + ("" if anulados == 1 else "s"))
    if sin_procesar:
        partes.append(f"{sin_procesar:,} sin procesar")
    if not partes:
        return ESTADO_OK, "ok"
    return " · ".join(partes), ("sinp" if sin_procesar else "anul")


def _etiqueta_arriba(trazas, textos):
    """El texto de cada TRAMO, con la etiqueta del total sólo en el de más
    arriba que tenga valor: Plotly pone el `outside` de una barra apilada
    sólo en la que termina la pila (lo mismo que resuelve
    `semanal._etiqueta_en_la_punta` para sus tramos)."""
    salida = [[None] * len(textos) for _ in trazas]
    for j, txt in enumerate(textos):
        for i in range(len(trazas) - 1, -1, -1):
            if trazas[i][2][j]:
                salida[i][j] = txt
                break
    return salida


def _renglones(total, n_req, var, gran):
    """Los renglones de la etiqueta de UNA barra como `(plano, html)`: el
    total, los requerimientos y la variación — la etiqueta de Compras con
    «req.» donde aquélla dice «docs»."""
    if not total:
        return []
    salida = [(total, total)]
    _r = f"{n_req:,} req."
    salida.append((_r, f"<span style='color:{GRIS_TEXTO}'>{_r}</span>"))
    if gran in _GRAN_VARIACION and var:
        estado, pct, _ = var
        if estado == "ok":
            _t, _c = _fmt_variacion(pct)
            salida.append((_t, f"<span style='color:{_c}'><b>{_t}</b></span>"))
        elif estado == "parcial":
            salida.append(("parcial",
                           f"<span style='color:{GRIS_TEXTO}'><i>parcial</i>"
                           "</span>"))
    return salida


def vista_periodos(dl, gran, rango=None, orden=()):
    """Todo lo que la tarjeta dibuja de un recorte, sin dibujar nada.

    `dl` son las líneas ya filtradas (sin las vacías) con su `clave` de
    período; `rango` es `(primer día, último día)` como `date`, para saber
    qué período quedó cortado; `orden`, el de `orden_areas`. Devuelve un
    dict con los períodos en orden (`claves`), sus rótulos (`eje`, `hover`,
    `fila`), el resumen (`res`), los tramos (`trazas`), las variaciones y
    sus notas. Vacío (`claves == []`) si no hay nada válido que dibujar."""
    res = resumen_por_periodo(dl)
    claves = res.index.tolist()
    v = {"claves": claves, "res": res, "gran": gran, "rango": rango}
    if not claves:
        return v
    rot = {c: _rotulo_periodo(c, gran) for c in claves}
    if gran == "Día":
        dias = [pd.Timestamp(c).date() for c in claves]
        fer = set()
        for _a in {d.year for d in dias}:
            fer |= cortes.feriados_peru(_a)
        hover = [f"{cortes.DIAS_ABR_ES[d.weekday()].capitalize()} "
                 f"{d:%d/%m/%Y}" + (" · feriado" if d in fer else "")
                 for d in dias]
        corto = [f"{cortes.DIAS_ABR_ES[d.weekday()].capitalize()} {d:%d/%m}"
                 for d in dias]
        fila = hover
    else:
        dias = None
        hover = [rot[c][1] for c in claves]
        corto = [rot[c][0] for c in claves]
        if gran == "Semana":
            fila = [f"{rot[c][0]} {_anio_semana(c)}" for c in claves]
        else:
            fila = list(hover)
    tot = [float(x) for x in res["valor"]]
    variaciones = (_variaciones(claves, tot, gran, rango)
                   if gran in _GRAN_VARIACION else [None] * len(claves))

    def _ant(var):
        return corto[var[2]] if var and var[2] is not None else ""

    v.update(
        eje=[rot[c][0] for c in claves], hover=hover, corto=corto, fila=fila,
        dias=dias, tot=tot, variaciones=variaciones,
        var_hover=[_hover_variacion(_v, gran, c, _ant(_v), rango,
                                    sustantivo="requerimientos")
                   for c, _v in zip(claves, variaciones)],
        var_nota=[_nota_variacion(_v, gran, c, _ant(_v), rango,
                                  sustantivo="requerimientos")
                  for c, _v in zip(claves, variaciones)],
        trazas=trazas_por_area(dl[dl["estado"] != _ANULADO], claves, orden),
    )
    # Qué áreas pidieron en cada período, de mayor a menor: el tooltip de
    # la columna «Áreas» del Resumen.
    dv = dl[dl["estado"] != _ANULADO]
    _pa = (dv.groupby(["clave", "area"])["valor"].sum().reset_index()
             .sort_values(["clave", "valor"], ascending=[True, False]))
    _nombres = _pa.groupby("clave")["area"].agg(
        lambda s: ", ".join(_nombre_area(a) for a in s))
    v["areas_txt"] = [_nombres.get(c, "") for c in claves]
    return v


def figura_periodos(v, alto_fig, titulo="", foco=None):
    """La figura de la tarjeta a partir de `vista_periodos`.

    `foco` es la clave del período en foco (o None): lo demás se atenúa
    por COLOR, no con `marker.opacity` — esa lista sobre barras con texto
    `outside` crashea Plotly en el navegador (regla #476). El eje es
    LINEAL con los rótulos a mano, como el de Compras: el calendario de
    Día y la traducción del clic hablan en índices."""
    claves, gran = v["claves"], v["gran"]
    n = len(claves)
    res = v["res"]
    fig = go.Figure()
    if not n:
        return fig
    trazas = v["trazas"] or [("Valorizado", PALETA_SERIES[0], v["tot"])]
    reqs = res["reqs"].astype(int).tolist()

    # ── La etiqueta de cada barra: lo que ENTRA (`_plan_etiquetas`) ──────
    reng = [_renglones(fmt_k(t) if t else None, r, var, gran)
            for t, r, var in zip(v["tot"], reqs, v["variaciones"])]
    plan, k_etq, alto_etq = _plan_etiquetas(
        n, [[p for p, _ in r] for r in reng], alto_fig)
    textos = [None] * n
    if plan:
        sep = _ETQ_SEP if plan == "unida" else "<br>"
        textos = [(sep.join(h for _, h in r[:k_etq]) or None) for r in reng]
    txt_tr = (_etiqueta_arriba(trazas, textos) if plan
              else [[None] * n for _ in trazas])
    estilo = dict(textposition="outside", cliponaxis=False,
                  constraintext="none",
                  textangle=-90 if plan in ("girada", "unida") else 0,
                  textfont=dict(size=_ETQ_FUENTE, color=TEXTO_PRINCIPAL))

    # ── El hover: el período, el tramo, el total y lo que lo forma ───────
    det = [f"<br>{r:,} req. · {int(ln):,} línea{'' if ln == 1 else 's'}"
           f" · {int(a):,} área{'' if a == 1 else 's'}"
           for r, ln, a in zip(reqs, res["lineas"], res["areas"])]
    anul = [(f"<br><i>{int(x):,} anulado{'' if x == 1 else 's'} aparte</i>"
             if x else "") for x in res["anulados"]]
    xs = list(range(n))
    for i, (nombre, color, vals) in enumerate(trazas):
        rot = nombre if nombre == "Resto" else _nombre_area(nombre)
        if foco is not None and foco in claves:
            color = [color if c == foco else _con_alpha(color, _ATENUADO)
                     for c in claves]
        fig.add_bar(
            x=xs, y=vals, name=rot, marker=dict(color=color),
            customdata=list(zip(v["hover"], [rot] * n, v["tot"], det,
                                v["var_hover"], anul)),
            hovertemplate=("%{customdata[0]}"
                           "<br><b>%{customdata[1]}</b>: S/ %{y:,.2f}"
                           "<br>Total: S/ %{customdata[2]:,.2f}"
                           "%{customdata[3]}%{customdata[4]}%{customdata[5]}"
                           "<extra></extra>"),
        )
        if plan:
            fig.data[-1].update(text=txt_tr[i], **estilo)
    if len(trazas) > 1:
        fig.update_layout(barmode="stack")

    _compras_layout(fig, alto=alto_fig)
    if plan:
        _y = _techo_etiquetas(max(v["tot"]), min(0.0, min(v["tot"])),
                              alto_fig, alto_etq)
        if _y:
            fig.update_yaxes(range=_y)
    # SIN LEYENDA, a diferencia de Compras: la fila de KPI de la cabecera
    # ya nombra cada tramo con su color, su monto y su % (`_html_kpi`), así
    # que es la leyenda dicha con números. La de Plotly, además, se montaba
    # sobre los rótulos del eje con la figura en COMPACTO (medido: los
    # rótulos de dos renglones de Semana y de Día la alcanzan). Las cuentas
    # de las etiquetas siguen suponiendo la leyenda (`semanal._LEYENDA_Y`),
    # o sea que calculan con un área de trazo MENOR que la real: sobra aire,
    # nada se pisa.
    fig.update_layout(title=titulo, hovermode="closest", showlegend=False)

    # ── El eje: el calendario en Día, un rótulo cada tanto en el resto ───
    ticks = (_calendario_del_eje(fig, v["dias"], sep="semana")
             if gran == "Día" else None)
    if ticks is None:
        eje = v["eje"]
        largo = max((len(t) for t in eje), default=1)
        caben = max(1, int(_LIENZO_PX // (largo * _TICK_PX_CARACTER
                                          + _TICK_AIRE)))
        paso = max(1, -(-n // caben))
        tv = list(range(0, n, paso))
        tt = [eje[i] for i in tv]
        if gran == "Semana":
            ult = None
            for j, i in enumerate(tv):
                a = _anio_semana(claves[i])
                if a != ult:
                    tt[j] += f"<br>{a}"
                    ult = a
        ticks = (tv, tt)
    fig.update_xaxes(type="linear", tickmode="array", tickvals=ticks[0],
                     ticktext=ticks[1], range=[-0.5, n - 0.5])
    return fig


def tabla_resumen(v, foco=None):
    """`(filas, total)` de la grilla del Resumen: una fila por barra."""
    res, gran = v["res"], v["gran"]
    tot_vista = float(sum(v["tot"])) or 0.0
    estados = [_texto_estado(int(a), int(s))
               for a, s in zip(res["anulados"], res["sin_procesar"])]
    filas = pd.DataFrame({
        "periodo": v["fila"],
        "reqs": res["reqs"].astype(int).tolist(),
        "lineas": res["lineas"].astype(int).tolist(),
        "areas": res["areas"].astype(int).tolist(),
        "valor": [round(t, 2) for t in v["tot"]],
        "parte": [(t / tot_vista if tot_vista else 0.0) for t in v["tot"]],
        "variacion": [(_v[1] if _v and _v[0] == "ok" else None)
                      for _v in v["variaciones"]],
        "estado": [e for e, _ in estados],
        "__vtxt": [("parcial" if _v and _v[0] == "parcial" else "—")
                   for _v in v["variaciones"]],
        "__nota": v["var_nota"],
        "__anota": v["areas_txt"],
        "__eclase": [c for _, c in estados],
        "__clave": v["claves"],
        "__sel": [c == foco for c in v["claves"]],
    })
    n = len(v["claves"])
    uni = _UNIDAD_GRAN[gran][0 if n == 1 else 1]
    an_tot = int(res["anulados"].sum())
    sp_tot = int(res["sin_procesar"].sum())
    e_tot, c_tot = _texto_estado(an_tot, sp_tot)
    total = {
        "periodo": f"Total · {n:,} {uni}",
        "reqs": f"{int(res['reqs'].sum()):,}",
        "lineas": f"{int(res['lineas'].sum()):,}",
        "areas": "", "valor": f"S/ {tot_vista:,.2f}", "parte": "100%",
        "variacion": "", "estado": e_tot, "__eclase": c_tot,
    }
    return filas, total


def tabla_requerimientos(amb, sel):
    """`(filas, total)` de la lista de requerimientos del período en foco.

    `amb` son las líneas del período (anulados incluidos: se LISTAN, pero
    no suman en la fila TOTAL, que es la misma cuenta que la barra)."""
    reqs = (amb.groupby("req", as_index=False)
               .agg(fecha=("fecha", "min"), area=("area", "first"),
                    estado=("estado", "first"), lineas=("valor", "size"),
                    valor=("valor", "sum")))
    estado = reqs["estado"].map(
        {_ANULADO: "anulado", _GENERADO: "sin procesar"}).fillna("")
    filas = pd.DataFrame({
        "registro": reqs["fecha"].dt.strftime("%Y-%m-%d %H:%M"),
        "codigo": reqs["req"],
        "area": reqs["area"].map(_nombre_area),
        "lineas": reqs["lineas"].astype(int),
        "valor": reqs["valor"].astype(float).round(2),
        "__estado": estado,
        "__req": reqs["req"],
        "__sel": reqs["req"] == sel,
    })
    validos = estado != "anulado"
    n_val, n_an = int(validos.sum()), int((~validos).sum())
    # El total sale de los valores SIN redondear, como la barra y el
    # Resumen: sumar los de la columna (redondeados a céntimos de a uno)
    # daba 6 céntimos de diferencia con la fila del Resumen en una semana
    # de 150 requerimientos — dos números que tienen que ser el mismo.
    total = {
        "registro": "Total",
        "codigo": f"{n_val:,} req.",
        "area": (f"+{n_an} anulado" + ("" if n_an == 1 else "s")) if n_an
                else "",
        "lineas": f"{int(filas.loc[validos, 'lineas'].sum()):,}",
        "valor": f"S/ {reqs.loc[validos, 'valor'].sum():,.2f}",
    }
    return filas, total


def _mayor_valido(amb):
    """El código del requerimiento válido de mayor valor del período: el que
    la tabla de líneas muestra si nadie eligió otro (el criterio de Compras:
    la de al lado nunca está vacía)."""
    v = amb[amb["estado"] != _ANULADO]
    if v.empty:
        v = amb
    s = v.groupby("req")["valor"].sum().sort_values(ascending=False)
    return s.index[0] if len(s) else None


def _html_kpi(total, n_reqs, trazas, tot_area, nota):
    """La fila de KPI: el total de la vista y una tarjeta por TRAMO de la
    barra, con el color del tramo. Es también la leyenda del gráfico, dicha
    con números. `nota` es `(corto, largo)` de lo que no suma, o None."""
    def _t(rot, val, sub, clase="", tip="", color=None):
        sw = (f'<span class="mp-kpi-sw" style="background:{color}"></span>'
              if color else "")
        return (f'<div class="mp-kpi {clase}" title="{escape(tip or rot)}">'
                f'<span class="mp-kpi-rot">{sw}{escape(rot)}</span>'
                f'<span class="mp-kpi-val">{escape(val)}'
                f'<span class="mp-kpi-sub">{escape(sub)}</span></span></div>')

    _n = f"{n_reqs:,} requerimiento" + ("" if n_reqs == 1 else "s")
    partes = [_t("Total de la vista", fmt_k(total), _n, "mp-kpi-total",
                 f"Total de la vista: S/ {total:,.2f} · {_n}")]
    if len(trazas) > 1:
        for nombre, color, vals in trazas:
            v = float(sum(vals))
            p = v / total if total else 0.0
            if nombre == "Resto":
                n_resto = len(tot_area) - (len(trazas) - 1)
                rot = f"{n_resto} área" + ("" if n_resto == 1 else "s") + " más"
            else:
                rot = _nombre_area(nombre)
            partes.append(_t(rot, fmt_k(v), f"{p:.0%}",
                             tip=f"{rot}: S/ {v:,.2f} · {p:.1%}",
                             color=color))
    if nota:
        partes.append(_t("No suman", nota[0], "", "mp-kpi-nota", nota[1]))
    return '<div class="mp-kpis">' + "".join(partes) + "</div>"


# ===========================================================================
# EL CSS DE LA TARJETA
# ===========================================================================
# Vive acá y no en `estilos/` por lo mismo que el de Compras vive en
# `graficos/compras/_css_proveedor.py`: sus reglas cuelgan de las keys de
# ESTA tarjeta y sólo tienen sentido cuando se dibuja. Se inyecta en cada
# corrida, sin guarda de «una sola vez» (regla #59). Las medidas son las de
# la cabecera de «Compras por período», que es lo que esta tarjeta calca:
# desplegables y toggles a 32px, la fila de KPI en su propio renglón.
_CSS = """<style>
/* La cabecera: el toggle de granularidad y los tres filtros en un flex que
   parte renglón si no entra; la fila de KPI ocupa siempre el suyo. El item
   del flex es el `stLayoutWrapper` que envuelve a cada key (regla #272),
   de ahí el `:has` con la clase de la key adentro, y nada más (#469). */
.st-key-mp_fila {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    gap: 10px !important;
    width: 100% !important;
}
.st-key-mp_fila > [data-testid="stLayoutWrapper"]:has(> .st-key-mp_hdr_area),
.st-key-mp_fila > [data-testid="stLayoutWrapper"]:has(> .st-key-mp_hdr_familia) {
    flex: 1 1 150px !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: 200px !important;
}
.st-key-mp_fila > [data-testid="stLayoutWrapper"]:has(> .st-key-mp_hdr_producto) {
    flex: 1 1 150px !important;
    min-width: 0 !important;
    width: auto !important;
    max-width: 260px !important;
}
.st-key-mp_fila > [data-testid="stLayoutWrapper"]:has(> .st-key-mp_kpi) {
    flex: 1 1 100% !important;
    min-width: 0 !important;
    width: auto !important;
}
.st-key-mp_fila [data-testid="stElementToolbar"] { display: none; }
.st-key-mp_hdr_area,
.st-key-mp_hdr_familia,
.st-key-mp_hdr_producto,
.st-key-mp_kpi { width: 100% !important; }
.st-key-mp_hdr_area > [data-testid="stElementContainer"],
.st-key-mp_hdr_familia > [data-testid="stElementContainer"],
.st-key-mp_hdr_producto > [data-testid="stElementContainer"],
.st-key-mp_kpi > [data-testid="stElementContainer"] { width: 100% !important; }
/* Los desplegables a la altura del toggle, con las tres piezas que mide la
   regla #477: el envoltorio, la caja que se ve y su input y su flecha. */
.st-key-mp_hdr_area .react-aria-ComboBox,
.st-key-mp_hdr_familia .react-aria-ComboBox,
.st-key-mp_hdr_producto .react-aria-ComboBox,
.st-key-mp_hdr_area .react-aria-ComboBox > div,
.st-key-mp_hdr_familia .react-aria-ComboBox > div,
.st-key-mp_hdr_producto .react-aria-ComboBox > div {
    min-height: 32px !important;
    height: 32px !important;
}
.st-key-mp_hdr_area .react-aria-ComboBox input,
.st-key-mp_hdr_familia .react-aria-ComboBox input,
.st-key-mp_hdr_producto .react-aria-ComboBox input,
.st-key-mp_hdr_area .react-aria-ComboBox > div > button,
.st-key-mp_hdr_familia .react-aria-ComboBox > div > button,
.st-key-mp_hdr_producto .react-aria-ComboBox > div > button {
    height: 30px !important;
    min-height: 30px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
.st-key-mp_hdr_area .react-aria-ComboBox input,
.st-key-mp_hdr_familia .react-aria-ComboBox input,
.st-key-mp_hdr_producto .react-aria-ComboBox input { font-size: 12px !important; }
/* Los dos toggles —granularidad arriba, modo abajo— acotados a SU key y no
   al contenedor (CLAUDE.md: una regla colgada del contenedor captura los
   widgets que se agreguen después). */
.st-key-mov_per_gran [data-testid="stButtonGroup"] button,
.st-key-mov_per_modo [data-testid="stButtonGroup"] button {
    min-height: 32px !important;
    height: 32px !important;
    padding: 0 12px !important;
    font-size: 12px !important;
}
/* La fila de KPI: el total y un tramo por tarjeta, con su color. */
.st-key-mp_kpi [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-mp_kpi .mp-kpis {
    display: flex;
    flex-wrap: wrap;
    align-items: stretch;
    gap: 2px 0;
}
.st-key-mp_kpi .mp-kpi {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    max-width: 150px;
    padding: 0 12px;
    line-height: 1.2;
    border-left: 1px solid var(--border);
}
.st-key-mp_kpi .mp-kpi:first-child {
    padding-left: 0;
    border-left: none;
    max-width: none;
}
.st-key-mp_kpi .mp-kpi-rot {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.st-key-mp_kpi .mp-kpi-sw {
    flex: 0 0 auto;
    width: 8px;
    height: 8px;
    border-radius: 2px;
}
.st-key-mp_kpi .mp-kpi-val {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
}
.st-key-mp_kpi .mp-kpi-sub {
    margin-left: 4px;
    font-size: 10px;
    font-weight: 400;
    color: var(--text-secondary);
}
.st-key-mp_kpi .mp-kpi-total .mp-kpi-val {
    color: var(--accent-deep);
    font-weight: 700;
}
.st-key-mp_kpi .mp-kpi-nota { max-width: 260px; }
.st-key-mp_kpi .mp-kpi-nota .mp-kpi-val {
    font-size: 12px;
    font-weight: 400;
    color: var(--text-secondary);
}
/* La fila de modo: el toggle y, al lado, el caption que nombra el ámbito. */
.st-key-mp_pie { align-items: center !important; }
.st-key-mp_pie [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
/* Un iframe es inline y se apoya en la línea base: sin esto la grilla del
   Resumen le suma a la tarjeta el hueco del descendente (medido en Compras:
   7.6px). Las del Detalle viven en un `st.columns`, que es flex. */
.st-key-mp_resumen .stCustomComponentV1 { display: block !important; }
</style>"""


# ===========================================================================
# LA TARJETA
# ===========================================================================

def tarjeta_requerimientos_periodo(d, *, cols, d_hist=None):
    """Requerimientos por período: barras, Resumen y Detalle.

    `d` son las líneas de requerimientos ya recortadas por la fecha de la
    franja y por sus chips (Sub Almacén, Familia); `cols` los nombres de
    columna resueltos (`fecha`, `req`, `area`, `estado`, `fam`, `prod`,
    `cant`, `punit`, `val`); `d_hist` el parquet entero, del que sale el
    orden estable de los colores por área (sin él, el del rango)."""
    with st.container(border=True, key="ajuste_graf_card_izq_mov_periodo"):
        st.markdown(_CSS, unsafe_allow_html=True)
        if not (cols.get("fecha") and cols.get("val")):
            st.info("No hay columnas suficientes para este gráfico.")
            return
        base = lineas_requerimientos(d, **cols)
        lin = base[~base["vacio"]]
        valida = lin["estado"] != _ANULADO

        def _rank(columna, mascara):
            s = (lin.loc[mascara & valida].groupby(columna)["valor"].sum()
                    .sort_values(ascending=False))
            return [x for x in s.index if x]

        # ── Las opciones, ANTES de dibujar los widgets ────────────────────
        # Del valor vigente en `session_state`, que es lo que el widget va a
        # mostrar: cada lista ofrece lo que dejan los filtros de su
        # izquierda, ordenado por valor. Lo elegido que dejó de estar (el
        # rango se angostó) se AGREGA al final en vez de resetearse: la vista
        # sale vacía y un cartel dice por qué — el criterio de Producto en
        # Compras. Los centinelas «Top N» sí se resetean.
        todo = pd.Series(True, index=lin.index)
        ops_area = [_AREA_TODAS] + _rank("area", todo)
        _a_prev = st.session_state.get("mov_per_area")
        if _a_prev is not None and _a_prev not in ops_area:
            ops_area.append(_a_prev)
        m_area = todo.copy()
        if _a_prev not in (None, _AREA_TODAS):
            m_area &= lin["area"] == _a_prev

        ops_fam = [_FAM_TODAS] + _rank("fam", m_area)
        _f_prev = st.session_state.get("mov_per_familia")
        if _f_prev is not None and _f_prev not in ops_fam:
            ops_fam.append(_f_prev)
        m_fam = m_area.copy()
        if _f_prev not in (None, _FAM_TODAS):
            m_fam &= lin["fam"] == _f_prev

        prods = _rank("prod", m_fam)
        etq_top = {f"Top {_n} por valor": _n for _n in _TOPS}
        ops_prod = ([_PROD_TODOS]
                    + [_e for _e, _n in etq_top.items() if _n < len(prods)]
                    + prods)
        _p_prev = st.session_state.get("mov_per_producto")
        if _p_prev is not None and _p_prev not in ops_prod:
            if _p_prev == _PROD_TODOS or _p_prev in etq_top:
                st.session_state["mov_per_producto"] = _PROD_TODOS
            else:
                ops_prod.append(_p_prev)

        # ── La cabecera: granularidad, los tres filtros y la fila de KPI ──
        with st.container(horizontal=True, gap="small", key="mp_fila"):
            gran = st.segmented_control(
                "Agrupar por", _GRAN_OPCIONES, default=_GRAN_DEFAULT,
                required=True, key="mov_per_gran",
                label_visibility="collapsed")
            with st.container(key="mp_hdr_area"):
                area_sel = st.selectbox(
                    "Área", ops_area, key="mov_per_area",
                    format_func=lambda a: (a if a == _AREA_TODAS
                                           else _nombre_area(a)),
                    label_visibility="collapsed",
                    help="Acota ESTA tarjeta al área que pidió, encima de "
                         "los chips de la franja. Ordenadas por valorizado "
                         "requerido en el rango.")
            with st.container(key="mp_hdr_familia"):
                fam_sel = st.selectbox(
                    "Familia", ops_fam, key="mov_per_familia",
                    format_func=lambda f: (f if f == _FAM_TODAS
                                           else _oracion(f)),
                    label_visibility="collapsed",
                    help="Acota la tarjeta a una familia de productos. "
                         "Ofrece las del área elegida.")
            with st.container(key="mp_hdr_producto"):
                prod_sel = st.selectbox(
                    "Producto", ops_prod, key="mov_per_producto",
                    label_visibility="collapsed",
                    help="Ordenados por valorizado requerido en el rango: "
                         "el primero es el que más se pidió. «Top N por "
                         "valor» suma los N mayores en una sola serie. Se "
                         "puede escribir para buscar.")
            with st.container(key="mp_kpi"):
                kpi = st.empty()
        gran = gran or _GRAN_DEFAULT
        area_sel = area_sel or _AREA_TODAS
        fam_sel = fam_sel or _FAM_TODAS
        prod_sel = prod_sel or _PROD_TODOS

        # ── El recorte de la tarjeta ──────────────────────────────────────
        m = todo.copy()
        if area_sel != _AREA_TODAS:
            m &= lin["area"] == area_sel
        if fam_sel != _FAM_TODAS:
            m &= lin["fam"] == fam_sel
        if prod_sel in etq_top:
            m &= lin["prod"].isin(prods[:etq_top[prod_sel]])
        elif prod_sel != _PROD_TODOS:
            m &= lin["prod"] == prod_sel
        dl = lin[m].copy()
        dl["clave"] = _periodo_serie(dl["fecha"], gran)

        _amb = [x for x in (
            None if area_sel == _AREA_TODAS else _nombre_area(area_sel),
            None if fam_sel == _FAM_TODAS else _oracion(fam_sel),
            (None if prod_sel == _PROD_TODOS
             else _compras_truncar(prod_sel)))
            if x]
        # El ÁMBITO va al título, como en Compras: con los filtros de la
        # tarjeta y los chips de la franja, «por semana» a secas no deja
        # saber de qué son esas barras.
        titulo = (f"Valorizado requerido por {_AGRUPADO_GRAN[gran]}"
                  + (" · " + " · ".join(_amb) if _amb else ""))

        rng = _rango_vigente()
        rango = ((rng[0].date(), (rng[1] - pd.Timedelta(days=1)).date())
                 if rng else None)
        v = vista_periodos(dl, gran, rango,
                           orden_areas(d_hist if d_hist is not None else d,
                                       cols.get("area"), cols.get("val")))
        if not v["claves"]:
            st.info(f"**{titulo}** — sin requerimientos que mostrar. Ampliá "
                    "el rango de fechas (en la franja de arriba) o soltá "
                    "algún filtro de la tarjeta.")
            return
        claves = v["claves"]

        # ── Lo que NO suma, dicho en la fila de KPI ───────────────────────
        # Los anulados del recorte, y los requerimientos sin ítems del área
        # —éstos no tienen familia ni producto, así que con esos filtros
        # puestos no son de la vista y no se nombran—.
        n_an = int(dl.loc[dl["estado"] == _ANULADO, "req"].nunique())
        n_vac, vac_area = 0, None
        if fam_sel == _FAM_TODAS and prod_sel == _PROD_TODOS:
            _tod = base.groupby("req")["vacio"].all()
            vac = base[base["req"].isin(_tod[_tod].index)]
            if area_sel != _AREA_TODAS:
                vac = vac[vac["area"] == area_sel]
            n_vac = int(vac["req"].nunique())
            if n_vac:
                _pa = vac.groupby("area")["req"].nunique().sort_values(
                    ascending=False)
                vac_area = (_nombre_area(_pa.index[0]), int(_pa.iloc[0]))
        nota = None
        if n_an or n_vac:
            _c, _l = [], []
            if n_an:
                _c.append(f"{n_an:,} anulado" + ("" if n_an == 1 else "s"))
                _l.append(f"{n_an:,} anulado" + ("" if n_an == 1 else "s")
                          + " (se ven en Estado y en el Detalle)")
            if n_vac:
                _c.append(f"{n_vac:,} sin ítems")
                _l.append(f"{n_vac:,} requerimiento"
                          + ("" if n_vac == 1 else "s")
                          + " sin ítems —vienen sin producto, cantidad ni "
                          "valor" + (f"; {vac_area[1]:,} de {vac_area[0]}"
                                     if vac_area else "") + "—")
            nota = (" · ".join(_c),
                    "No suman en las barras ni en los totales: "
                    + " y ".join(_l) + ".")
        dv = dl[dl["estado"] != _ANULADO]
        kpi.markdown(
            _html_kpi(float(sum(v["tot"])), int(dv["req"].nunique()),
                      v["trazas"],
                      dv.groupby("area")["valor"].sum().loc[lambda s: s > 0],
                      nota),
            unsafe_allow_html=True)

        # ── Foco, modo y clic: se resuelven ANTES de dibujar (#398, #399) ─
        # Todo como en Compras: cambiar la granularidad o un filtro suelta el
        # foco; el modo se lee de `session_state` porque el alto de la
        # figura depende de él; el clic de la barra se lee de la key que se
        # DIBUJÓ la corrida anterior, con un contador en la key.
        ctx = (gran, area_sel, fam_sel, prod_sel)
        if st.session_state.get("mov_per_ctx_prev") != ctx:
            st.session_state["mov_per_ctx_prev"] = ctx
            st.session_state["mov_per_focus"] = None
            st.session_state["mov_per_req"] = None
        # Un clic en una FILA del Resumen pidió abrir su Detalle en la
        # corrida anterior: la grilla se dibuja debajo del toggle de modo, y
        # la key de un widget ya dibujado no se puede escribir — así que el
        # pedido viaja hasta acá, que es antes del toggle.
        _ir = st.session_state.pop("_mov_per_ir_detalle", None)
        if _ir is not None:
            st.session_state["mov_per_focus"] = _ir
            st.session_state["mov_per_req"] = None
            st.session_state["mov_per_modo"] = _MODO_DETALLE
        modo = st.session_state.get("mov_per_modo")
        if modo not in _MODO_OPCIONES:
            modo = _MODO_DEFAULT
        foco_antes = st.session_state.get("mov_per_focus")
        nclic = st.session_state.get("mov_per_nclic", 0)
        key_base = f"mov_per_graf_{gran}"
        pt = _first_point(st.session_state.get(f"{key_base}_{nclic}"))
        if pt is not None:
            nclic += 1
            st.session_state["mov_per_nclic"] = nclic
            clic = _clave_del_clic(pt.get("x"), claves)
            if clic is None:
                pass
            elif modo == _MODO_RESUMEN:
                # Desde Resumen el clic ABRE el Detalle de esa barra (el
                # gesto es «mostrame ésta»), como en Compras (regla #476).
                st.session_state["mov_per_req"] = None
                st.session_state["mov_per_focus"] = clic
                st.session_state["mov_per_modo"] = _MODO_DETALLE
                modo = _MODO_DETALLE
            else:
                st.session_state["mov_per_req"] = None
                st.session_state["mov_per_focus"] = (
                    None if foco_antes == clic else clic)
        foco = st.session_state.get("mov_per_focus")
        foco_ok = foco in set(claves)
        con_tabla = modo == _MODO_RESUMEN or foco_ok
        alto_fig = alturas.COMPACTO if con_tabla else _ALTO_FIG_SOLO

        fig = figura_periodos(
            v, alto_fig, titulo=titulo,
            foco=foco if (foco_ok and modo == _MODO_DETALLE) else None)
        # Lo que devuelve se ignora: el clic ya se leyó arriba.
        st.plotly_chart(fig, use_container_width=True, on_select="rerun",
                        selection_mode="points",
                        key=f"{key_base}_{nclic}")

        with st.container(horizontal=True, gap="small", key="mp_pie"):
            st.segmented_control(
                "Qué se ve abajo", _MODO_OPCIONES, default=_MODO_DEFAULT,
                required=True, key="mov_per_modo",
                label_visibility="collapsed", help=_AYUDA_MODO)
            pie = st.empty()

        # ── RESUMEN: el gráfico escrito como tabla ────────────────────────
        if modo == _MODO_RESUMEN:
            filas, total = tabla_resumen(v, foco if foco_ok else None)
            # La key lleva lo que cambia las FILAS y un contador que se
            # estrena cada vez que un clic en una fila lleva al Detalle: así
            # la grilla vuelve sin la selección vieja (regla #471).
            n_res = st.session_state.get("mov_per_nres", 0)
            with st.container(key="mp_resumen"):
                clic_fila = renderizar_periodos_req(
                    filas, altura=_ALTO_TABLA,
                    key="mov_per_res_grid_" + _clave_grilla(
                        gran, ctx, rango, n_res),
                    rotulo_periodo=_AGRUPADO_GRAN[gran].capitalize(),
                    ver_variacion=gran in _GRAN_VARIACION, total=total)
            pie.caption(
                f"**{_del_al(dv['fecha'])}** · agrupado por "
                f"{_AGRUPADO_GRAN[gran]} — una fila por barra; un clic en "
                "una fila (o en su barra) abre su detalle.")
            if clic_fila in set(claves):
                st.session_state["_mov_per_ir_detalle"] = clic_fila
                st.session_state["mov_per_nres"] = n_res + 1
                st.rerun(scope=scope_rerun())
            return

        # ── DETALLE sin barra elegida: la zona queda vacía y lo dice ──────
        # El `st.empty()` sólo en esta rama, como en Compras (regla #471):
        # borra las grillas al soltar el foco sin re-montarlas en cada
        # corrida mientras hay detalle.
        if not foco_ok:
            st.empty()
            pie.caption("Tocá una barra —o una fila del Resumen— para ver "
                        "sus requerimientos.")
            return
        hueco = st.container(key="mp_detalle")

        # ── DETALLE: los requerimientos del período y las líneas del elegido
        amb = dl[dl["clave"] == foco]
        sel = st.session_state.get("mov_per_req")
        if sel not in set(amb["req"]):
            sel = _mayor_valido(amb)
        filas_req, total_req = tabla_requerimientos(amb, sel)
        lin_sel = amb[amb["req"] == sel].sort_values("valor", ascending=False)
        filas_lin = pd.DataFrame({
            "prod": lin_sel["prod"],
            "cant": pd.to_numeric(lin_sel["cant"], errors="coerce").round(3),
            "punit": pd.to_numeric(lin_sel["punit"], errors="coerce").round(4),
            "valor": lin_sel["valor"].astype(float).round(2),
        })
        _nl = len(filas_lin)
        total_lin = {
            "prod": f"Total · {_nl} línea" + ("" if _nl == 1 else "s"),
            "cant": "", "punit": "",
            "valor": f"S/ {lin_sel['valor'].sum():,.2f}",
        }
        with hueco:
            # columnas-internas: las dos tablas del detalle, DENTRO de la
            # tarjeta, con el reparto de «Compras por período» (la lista
            # lleva cinco columnas contra cuatro).
            c_req, c_lin = st.columns([1.15, 1], gap=GAP_DRILL)
            # La key lleva lo que cambia las FILAS —el período, los filtros,
            # el rango— y el contador de clics del gráfico, no el
            # requerimiento elegido: así el orden que eligió el usuario
            # sobrevive al clic (regla #471).
            k_tablas = _clave_grilla(gran, foco, ctx, rango, nclic)
            with c_req:
                clic_req = renderizar_requerimientos(
                    filas_req, altura=_ALTO_TABLA,
                    key=f"mov_per_req_grid_{k_tablas}", total=total_req)
            with c_lin:
                renderizar_lineas_req(
                    filas_lin, altura=_ALTO_TABLA,
                    key=f"mov_per_lin_grid_{k_tablas}", total=total_lin)
        _i = claves.index(foco)
        pie.caption(f"**{v['hover'][_i]}** — clic en un requerimiento para "
                    "ver sus líneas al costado.")

        # El clic en la lista: la selección VIGENTE, así que se actúa sólo
        # si difiere de la que ya se muestra. El rerun redibuja la marca de
        # la lista y las líneas de al lado (regla #306 para el scope).
        if clic_req is None or clic_req == sel or clic_req not in set(amb["req"]):
            return
        st.session_state["mov_per_req"] = clic_req
        st.rerun(scope=scope_rerun())
