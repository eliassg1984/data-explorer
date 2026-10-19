"""Portada mensual de ventas y consumo/costo; reportes completos en otra pestaña."""

import datetime as dt
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import convenios_descuento
import costo_ventas
import data
import definicion_venta as dv
import resumen_ejecutivo as resumen
from cortes import MESES_LARGOS_ES
from graficos.base import (
    _render_rail, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
)

_RESUMEN_RAIL_CATEGORIAS = rail_sin_tablas((
    ("Resumen", (("Resumen ejecutivo", "Resumen ejecutivo", ":material/dashboard:"),)),
))
_PILA = pila_sin_tablas(())
_ARCHIVOS = ("ajusteinventario.parquet", "compras.parquet", "salidas.parquet",
             "ventas.parquet", "notascreditocompras.parquet")
_AQUI = Path(__file__).parent
_COMPONENTE = st.components.v2.component(
    "resumen_ejecutivo",
    css=(_AQUI / "resumen_ejecutivo.css").read_text(encoding="utf-8"),
    js=(_AQUI / "resumen_ejecutivo.js").read_text(encoding="utf-8"),
)
_LOG = logging.getLogger(__name__)


@st.cache_data(ttl=3600, show_spinner=False)
def _meses_costos(_ajuste, _grupos, sellos, version, convenios):
    """Sólo mensual: evita cargar el kardex de semanas y quincenas.

    Sellos y versiones identifican los DataFrames excluidos del hash. Un
    fallo de una fuente lanza para que nunca se guarde un cero ficticio.
    """
    compras, salidas = data.cargar("compras.parquet"), data.cargar("salidas.parquet")
    if compras is None or salidas is None:
        raise RuntimeError("No se pudieron cargar compras o salidas")
    return costo_ventas.armar(_ajuste, compras, salidas, _grupos, convenios)


def _rotulo(mes):
    p = pd.Period(mes, freq="M")
    return f"{MESES_LARGOS_ES[p.month - 1].capitalize()} {p.year}"


def renderizar_graficos_resumen(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    _render_rail(_RESUMEN_RAIL_CATEGORIAS, "resumen_graf_tipo", secciones=_PILA)
    hoy = dt.datetime.now(ZoneInfo("America/Lima")).date()
    with st.spinner("Preparando el resumen de ventas y consumo…"):
        grupos = data.venta_por_grupo_dia()
    if grupos is None or grupos.empty:
        st.warning("No se pudo leer la venta por día. Reintentá en unos segundos.")
        return
    fechas = pd.to_datetime(grupos["dia"], errors="coerce").dropna()
    if fechas.empty:
        st.info("Todavía no hay fechas de venta para armar el resumen.")
        return
    hasta = min(hoy - dt.timedelta(days=1), fechas.max().date())
    desde = fechas.min().date()
    if desde > hasta:
        st.info("El resumen estará disponible al terminar el primer día de ventas.")
        return
    meses = [str(m) for m in pd.period_range(desde, hasta, freq="M")][::-1]
    costos, error_costos = None, None
    try:
        with st.spinner("Calculando el consumo mensual…"):
            ajuste = df_full if df_full is not None else df_f
            costos = _meses_costos(
                ajuste, grupos, tuple(data.sello_datos(a) for a in _ARCHIVOS),
                (resumen.VERSION, costo_ventas.VERSION, dv.VERSION,
                 data._version_preparar("compras.parquet")),
                convenios_descuento.leer())
    except Exception:
        _LOG.exception("No se pudo calcular el costo del resumen")
        error_costos = "No se pudieron leer las fuentes del costo. Reintentá en unos segundos."
    cerrados = {p["k"] for p in costos.get("periodos", [])} if costos else set()
    default = next((m for m in meses if m in cerrados and
                    resumen.rango_mes(m)[1] <= hasta), meses[0])
    clave = "resumen_mes"
    mes = st.session_state.get(clave, default)
    if mes not in meses:
        mes = default
    st.session_state[clave] = mes
    ini, fin = resumen.rango_mes(mes, hasta)
    ant_ini, ant_fin = resumen.rango_anterior(ini, fin)
    # El parquet no cubre el año pasado: no es una venta de cero.
    cubre_anterior = ant_ini >= desde and ant_fin <= hasta
    with st.spinner("Leyendo los pedidos del período…"):
        actual_df = data.cargar_rango("ventas.parquet", dv.FECHA, ini, fin, turno=True)
        anterior_df = (data.cargar_rango("ventas.parquet", dv.FECHA, ant_ini, ant_fin,
                                         turno=True) if cubre_anterior else None)
    try:
        actual = resumen.ventas_del_rango(actual_df, ini, fin)
        anterior = resumen.ventas_del_rango(anterior_df, ant_ini, ant_fin)
    except ValueError as e:
        st.warning(str(e))
        return
    parcial = fin < resumen.rango_mes(mes)[1]
    costo = resumen.costo_del_mes(costos, mes) if not parcial else None
    previo = resumen.costo_del_mes(costos, str(pd.Period(mes, freq="M") - 1))
    cambio_costo = (costo["porcentaje"] - previo["porcentaje"]
                    if costo and previo and costo["porcentaje"] is not None
                    and previo["porcentaje"] is not None else None)
    links = {
        "ventas": resumen.enlace_reporte("Ventas", "resumen_ejecutivo", ini, fin),
        "costos": resumen.enlace_reporte("Costos", "costo_de_ventas", mes=mes),
        "platos": resumen.enlace_reporte("Ventas", "analisis_de_platos", ini, fin),
    }
    payload = {
        "mes": mes, "rotulo": _rotulo(mes),
        "meses": [{"k": m, "nombre": _rotulo(m)} for m in meses],
        "ini": ini.isoformat(), "fin": fin.isoformat(), "parcial": parcial,
        "anterior_rotulo": _rotulo(str(pd.Period(mes, freq="M") - 12)),
        "actual": actual, "anterior": anterior, "costo": costo,
        "cambio_costo": cambio_costo, "links": links,
        "error_costos": error_costos,
        "demo": not data.secrets_disponibles(),
    }

    def al_mes():
        valor = (st.session_state.get("resumen_panel") or {}).get("mes")
        if valor in meses:
            st.session_state[clave] = valor

    _COMPONENTE(key="resumen_panel", data=payload, on_mes_change=al_mes,
                width="stretch")
    hechos = []
    if actual:
        hechos.extend((mes, k, v) for k, v in actual.items() if k != "dias")
    if costo:
        hechos.extend((mes, "costo: " + k, v) for k, v in costo.items()
                      if isinstance(v, (float, int)))
    publicar_contexto_ia(nombre_reporte, pd.DataFrame(
        hechos, columns=["PERIODO", "INDICADOR", "VALOR"]), {
            "alcance": "Ventas: todos los grupos, día del turno. Costos: cuatro "
                       "familias, incluye Eventos, excluye Venta interna; todas "
                       "las salidas salvo bajas se deducen, como el default de Costos.",
            "rango": (ini.isoformat(), fin.isoformat()),
        })
