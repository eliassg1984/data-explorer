"""graficos.pendientes — Inicio › «Pendientes del período» (regla #711).

La segunda vista de Inicio (el reporte «Resumen ejecutivo»), sobre el
boceto aprobado tal cual: lo que conviene mirar antes de cerrar el mes, una
fila por señal agrupada por área, y un clic lleva a la vista que la
resuelve. Es una pieza propia (`pendientes.js` + `.css`): la forma del
boceto —tres columnas de áreas, filas con punto, contadores, el filtro por
gravedad— no la da una tabla nativa.

Las cuentas de cada señal son de las vistas que ya las hacen (ver
`pendientes.py`, la parte pura). Acá se juntan SIN CALCULAR lo pesado:

  · Consistencia de datos y el Análisis de diferencias del último cierre
    tardan un minuto la primera vez de cada versión de los datos. Se leen
    de lo que ya se calculó en este proceso (`data.consistencia_maestro(
    solo_si_calculado=True)`, `data.recordar`); si no, «sin calcular», y el
    botón «Calcular ahora» los pide —a las MISMAS funciones, que dejan su
    caché para las dos vistas—.
  · Recetas vs Porcionado, lo que esa vista dejó al abrirse.
  · Lo barato se calcula siempre: lo sin explicar del último mes (la misma
    caché que la portada, `resumen_ejecutivo._meses_costos`), el peso por
    unidad raro de los porcionamientos (cacheado por su sello) y la hora de
    cada parquet en R2 (`data._sello_r2`, un minuto).

Un clic en una fila entra al reporte ya parado en su vista
(`navegacion._ir_a_vista`); para Consistencia, además, abierta en el
control de la fila (`costos_consistencia.K_ABRIR`). El clic llega a la
corrida del fragment de la sección, y cambiar de reporte pide la completa:
el mismo patrón que «Recetas vs Porcionado» (`st.rerun(scope="app")`).
"""

from graficos.movil import css_movil, js_movil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

import data
import pendientes
from cortes import sesiones_inventario, ultimo_cierre

_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "pendientes",
    css=css_movil((_AQUI / "pendientes.css").read_text(encoding="utf-8")),
    js=js_movil((_AQUI / "pendientes.js").read_text(encoding="utf-8")),
)
_K_PIEZA = "pendientes_pieza"
_K_IR = "_pend_ir"
_K_CALCULAR = "_pend_calcular"
K_ABRIR_CONSISTENCIA = "_cd_abrir"
"""El control con que abre «Consistencia de datos» al llegar desde acá: lo
lee una vez `costos_consistencia.renderizar`."""

VERSION_PESOS = 1
"""Sube si cambia cómo se cuenta el peso por unidad raro."""


@st.cache_data(ttl=3600, show_spinner=False)
def _pesos_raros(sello, version=VERSION_PESOS):
    """`{"n", "docs"}`: los cortes con peso por unidad fuera de lo habitual en
    los últimos 30 días con porcionamientos, y de cuántos porcionamientos.
    La cuenta es la de Producción › «Para revisar»
    (`movimientos_merma.pesos_por_unidad`, regla #647) sobre el parquet
    entero, que es de donde sale lo habitual. `sello` sólo es la clave."""
    from graficos import movimientos
    from graficos import movimientos_merma as mm
    from graficos.base import _resolver
    d = movimientos._cargar_porcionamientos()
    if d is None or d.empty:
        return None
    cols = {n: _resolver(d, c) for n, c in movimientos._COLS_PORC.items()}
    base, cortes = mm.porcionamientos(d, cols)
    if base.empty:
        return None
    p = mm.pesos_por_unidad(base, cortes)
    fin = pd.to_datetime(base["fecha"]).max().normalize()
    r = p[p["raro"] & (pd.to_datetime(p["fecha"]) >= fin - pd.Timedelta(days=29))]
    return {"n": int(len(r)), "docs": int(r["doc"].nunique())}


def _horas_de_los_parquets():
    """`{archivo: horas}` de cada parquet de los reportes, por su hora en R2
    (`data._sello_r2`, cacheado un minuto). None si no se supo ninguno."""
    archivos = sorted({a for cfg in data.REPORTES.values()
                       for a in (cfg.get("archivo"), *cfg.get("archivos_extra", ())) if a})
    ahora = datetime.now(timezone.utc)
    out = {}
    for a in archivos:
        s = data._sello_r2(a)
        if s:
            out[a] = (ahora - datetime.fromisoformat(s)).total_seconds() / 3600
    return out or None


def _cierre(ajuste):
    """El último cierre de inventario (`cortes.ultimo_cierre`), o None."""
    if ajuste is None or "FECHA APERTURA INVENTARIO" not in getattr(ajuste, "columns", ()):
        return None
    return ultimo_cierre(sesiones_inventario(pd.to_datetime(
        ajuste["FECHA APERTURA INVENTARIO"], errors="coerce")))


def _meses_cerrados(costos, rotulo):
    """`[(rótulo, sin explicar, venta)]` de los meses con cierre, del más
    viejo al más nuevo, con la cuenta de la portada (`costo_del_mes`)."""
    import resumen_ejecutivo as resumen
    if not costos:
        return None
    out = []
    for p in sorted(costos.get("periodos", []), key=lambda p: p["k"]):
        c = resumen.costo_del_mes(costos, p["k"])
        if c:
            out.append((rotulo(p["k"]), float(c["faltante"]), float(c["venta_base"])))
    return out or None


def _al_ir():
    v = (st.session_state.get(_K_PIEZA) or {}).get("ir")
    if not v or not v.get("r"):
        return
    import navegacion
    from navegacion_retorno import capturar_origen
    capturar_origen()
    navegacion._ir_a_vista(v["r"], v["sk"], v["v"])
    if v.get("abrir"):
        st.session_state[K_ABRIR_CONSISTENCIA] = v["abrir"]
    st.session_state[_K_IR] = True


def _al_calcular():
    st.session_state[_K_CALCULAR] = True


def renderizar(ajuste, costos, rotulo):
    """La vista entera, en su tarjeta. `ajuste` es ajusteinventario.parquet
    (el `archivo` de Inicio), `costos` lo de la portada
    (`_meses_costos`, o None) y `rotulo` cómo se nombra un mes."""
    ss = st.session_state
    if ss.pop(_K_IR, None):
        st.rerun(scope="app")
    calcular = bool(ss.pop(_K_CALCULAR, None))
    cierre = _cierre(ajuste)
    with st.container(border=True, key="ajuste_graf_card_izq_pend"):
        if calcular:
            with st.spinner("Calculando lo que faltaba… la primera vez de los "
                            "datos de hoy tarda alrededor de un minuto."):
                consist = data.consistencia_maestro()
                difs = data.diferencias_ajuste_sesion(cierre["clave"]) if cierre else None
        else:
            consist = data.consistencia_maestro(solo_si_calculado=True)
            difs = (data.diferencias_ajuste_sesion(cierre["clave"], solo_si_calculado=True)
                    if cierre else None)
        from graficos import recetas_revisar
        fuentes = {
            "consistencia": consist, "diferencias": difs,
            "cierre": cierre["nombre"] if cierre else None,
            "revisar": data.recordado("revisar_recetas", recetas_revisar.sellos_pendiente()),
            "pesos": _pesos_raros(data.sello_datos("porcionamientos.parquet")),
            "costos": _meses_cerrados(costos, rotulo),
            "horas": _horas_de_los_parquets(),
        }
        armado = pendientes.armar(fuentes, data.HORAS_DATO_VIEJO)
        armado["cierre"] = cierre["nombre"] if cierre else ""
        # «Calcular ahora» sólo si falta algo que ESTE botón calcula: Recetas
        # vs Porcionado se calcula al abrir su vista, no desde acá.
        armado["calculable"] = consist is None or (cierre is not None and difs is None)
        _PIEZA(key=_K_PIEZA, data=armado, width="stretch",
               on_ir_change=_al_ir, on_calcular_change=_al_calcular)
