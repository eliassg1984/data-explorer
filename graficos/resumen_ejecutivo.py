"""Portada mensual de Inicio: el mes con su contexto (regla #745).

Una frase dice cómo fue el mes; cinco indicadores con sus doce meses
eligen lo que dibuja el gráfico grande; «Para revisar» junta las señales del
mes y las de Pendientes en una lista; debajo, el costo por familia y el
puente de lo sin explicar. Las cuentas son las de `resumen_ejecutivo.py`
(puro); los enlaces entran al reporte en la MISMA pestaña, con «Volver».
"""

from graficos.movil import css_movil, js_movil
import datetime as dt
import logging
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import convenios_descuento
import costo_ventas
import data
import definicion_venta as dv
import presupuesto_ventas
import resumen_ejecutivo as resumen
from cortes import MESES_ABR_ES, MESES_LARGOS_ES
from estado_rango import aplicar_atajo, clave_rango
from graficos.base import (
    _render_rail, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    seccion_perezosa,
)

# INICIO: la portada del mes y, debajo, los Pendientes del período
# (2026-10-23, regla #711). Hasta ese día la portada era la única vista y
# la página no tenía pila (`_PILA` vacía, un destino aparte); con dos vistas
# se lee bajando, como los demás reportes, y la portada sigue siendo la
# primera: lo que se ve al entrar no cambió.
_RESUMEN_RAIL_CATEGORIAS = rail_sin_tablas((
    ("Resumen", (("Resumen ejecutivo", "Resumen ejecutivo", ":material/dashboard:"),
                 ("Pendientes del período", "Pendientes del período", ":material/flag:"))),
))
_PILA = pila_sin_tablas((
    ("res_sec_resumen",    "Resumen ejecutivo"),
    ("res_sec_pendientes", "Pendientes del período"),
))
_ARCHIVOS = ("ajusteinventario.parquet", "compras.parquet", "salidas.parquet",
             "ventas.parquet", "notascreditocompras.parquet")
_AQUI = Path(__file__).parent
_COMPONENTE = st.components.v2.component(
    "resumen_ejecutivo",
    css=css_movil((_AQUI / "resumen_ejecutivo.css").read_text(encoding="utf-8")),
    js=js_movil((_AQUI / "resumen_ejecutivo.js").read_text(encoding="utf-8")),
)
_LOG = logging.getLogger(__name__)

_K_PANEL = "resumen_panel"
_K_MES = "resumen_mes"
_K_DESTINOS = "_res_destinos"
_K_RECARGAR = "_res_recargar"

_DESTINOS = {
    # id: (reporte, clave del rail, vista, cómo se nombra)
    "ventas": ("Ventas", "ventas_graf_tipo", "Resumen ejecutivo", "Ventas › Venta por Periodo"),
    "comparativo": ("Ventas", "ventas_graf_tipo", "Comparativo vs Año Pasado",
                    "Ventas › Comparación Año Pasado"),
    "platos": ("Ventas", "ventas_graf_tipo", "Análisis de platos", "Ventas › Análisis de Platos"),
    "costos": ("Costos", "costos_graf_tipo", "Costo de ventas", "Costos › Costo de ventas"),
}
"""Adónde lleva cada señal de la portada. Ventas abre con el rango del mes y
Costos en el mes, con el ámbito de la portada."""


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


def _corto(mes):
    """«set 2025»: entra en el renglón de una tarjeta de 190px."""
    p = pd.Period(mes, freq="M")
    return f"{MESES_ABR_ES[p.month - 1].lower()} {p.year}"


def _costos(ajuste, grupos):
    """Los meses de costo de la portada (`_meses_costos`), con la clave que
    los identifica. La piden la portada y los Pendientes, que así leen la
    MISMA caché. LANZA si no se pudo."""
    return _meses_costos(
        ajuste, grupos, tuple(data.sello_datos(a) for a in _ARCHIVOS),
        (resumen.VERSION, costo_ventas.VERSION, dv.VERSION,
         data._version_preparar("compras.parquet")),
        convenios_descuento.leer())


def renderizar_graficos_resumen(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    _render_rail(_RESUMEN_RAIL_CATEGORIAS, "resumen_graf_tipo", secciones=_PILA)
    ajuste = df_full if df_full is not None else df_f

    def _dib_pendientes():
        from graficos import pendientes
        grupos = data.venta_por_grupo_dia()
        try:
            costos = _costos(ajuste, grupos) if grupos is not None else None
        except Exception:
            costos = None
        pendientes.renderizar(ajuste, costos, _rotulo)

    _dibujantes = {
        "res_sec_resumen": lambda: _portada(df_f, nombre_reporte, ajuste),
        "res_sec_pendientes": _dib_pendientes,
    }
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _dibujantes[_clave],
                             activa_de_entrada=(_i == 0))


def _limpio(v):
    """El payload sin NaN ni infinitos (JSON no los tiene) ni tipos de numpy."""
    if isinstance(v, dict):
        return {str(k): _limpio(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_limpio(x) for x in v]
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(f):
        return None
    return int(f) if isinstance(v, int) else f


def _al_mes():
    valor = (st.session_state.get(_K_PANEL) or {}).get("mes")
    if isinstance(valor, str) and valor in (st.session_state.get("_res_meses") or ()):
        st.session_state[_K_MES] = valor


def _al_ir():
    """Entra al reporte de la señal en la MISMA pestaña, guardando de dónde
    salió («Volver», regla #742). Sólo destinos que armó Python."""
    clave = (st.session_state.get(_K_PANEL) or {}).get("ir")
    d = (st.session_state.get(_K_DESTINOS) or {}).get(clave) if isinstance(clave, str) else None
    if not d:
        return
    import navegacion
    from navegacion_retorno import capturar_origen
    capturar_origen()
    if d.get("desde"):
        aplicar_atajo(clave_rango(d["r"], usa_carga_rango=True),
                      (dt.date.fromisoformat(d["desde"]), dt.date.fromisoformat(d["hasta"])),
                      reporte=d["r"], usa_carga_rango=True)
    if d.get("mes"):
        from graficos.costos import K_MES_DESDE_RESUMEN
        st.session_state[K_MES_DESDE_RESUMEN] = d["mes"]
    if d.get("abrir"):
        from graficos.pendientes import K_ABRIR_CONSISTENCIA
        st.session_state[K_ABRIR_CONSISTENCIA] = d["abrir"]
    navegacion._ir_a_vista(d["r"], d["sk"], d["v"])
    st.session_state[_K_RECARGAR] = True


def _al_calcular():
    from graficos import pendientes
    pendientes.pedir_calculo()
    st.session_state[_K_RECARGAR] = True


def _destinos(ini, fin, mes, pend):
    """Los destinos de la portada y de cada fila de Pendientes que entra en
    su lista. Quedan en la sesión: el navegador sólo devuelve el id."""
    out = {}
    for k, (r, sk, v, rot) in _DESTINOS.items():
        d = {"r": r, "sk": sk, "v": v, "rot": rot}
        if r == "Ventas":
            d.update(desde=ini.isoformat(), hasta=fin.isoformat())
        else:
            d["mes"] = mes
        out[k] = d
    for i, it in enumerate(pend):
        if it.get("destino"):
            out[f"p{i}"] = dict(it["destino"], rot=it.get("rot") or "")
    return out


def _portada(df_f, nombre_reporte, ajuste):
    """La portada del mes, en un solo componente."""
    ss = st.session_state
    if ss.pop(_K_RECARGAR, None):
        st.rerun(scope="app")
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
    ss["_res_meses"] = tuple(meses)
    costos, error_costos = None, None
    try:
        with st.spinner("Calculando el consumo mensual…"):
            costos = _costos(ajuste, grupos)
    except Exception:
        _LOG.exception("No se pudo calcular el costo del resumen")
        error_costos = "No se pudieron leer las fuentes del costo. Reintentá en unos segundos."
    cerrados = {p["k"] for p in costos.get("periodos", [])} if costos else set()
    default = next((m for m in meses if m in cerrados and
                    resumen.rango_mes(m)[1] <= hasta), meses[0])
    mes = ss.get(_K_MES, default)
    if mes not in meses:
        mes = default
    ss[_K_MES] = mes
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
    with st.spinner("Preparando los últimos doce meses… la primera vez de los "
                    "datos de hoy tarda medio minuto."):
        ventas_mes = data.ventas_por_mes()
    parcial = fin < resumen.rango_mes(mes)[1]
    costo = resumen.costo_del_mes(costos, mes) if not parcial else None
    previo = resumen.costo_del_mes(costos, str(pd.Period(mes, freq="M") - 1))
    costo_ap = resumen.costo_del_mes(costos, str(pd.Period(mes, freq="M") - 12))

    ppto_mes = resumen.presupuesto_por_mes(presupuesto_ventas.leer())
    ppto_dias = (resumen.presupuesto_dias(presupuesto_ventas.diario(), ini, fin)
                 if ppto_mes else None)
    hist = resumen.historia(mes, ventas_mes, costos, ppto_mes, actual, anterior,
                            ppto_dias, parcial)
    ap_ini, ap_fin = resumen.alinear_ano_pasado(ini, fin)
    diario = {"ini": ini.isoformat(), "ap_ini": ap_ini.isoformat(),
              "actual": resumen.venta_diaria(grupos, ini, fin),
              "ap": resumen.venta_diaria(grupos, ap_ini, ap_fin), "ppto": ppto_dias}
    costos_meses = []
    for p in sorted((costos or {}).get("periodos", []), key=lambda p: p["k"]):
        c = resumen.costo_del_mes(costos, p["k"]) if p["k"] <= mes else None
        if c:
            costos_meses.append((p["k"], float(c["faltante"]), float(c["venta_base"])))

    senales = resumen.para_revisar(mes, hist, actual, costo, previo, costos_meses, parcial)
    try:
        from graficos import pendientes as vista_pend
        armado = vista_pend.armar(ajuste, costos, _rotulo)
    except Exception:
        _LOG.exception("No se pudieron leer los Pendientes para la portada")
        armado = None
    pend, al_dia, sin_calcular = resumen.de_pendientes(armado)
    destinos = _destinos(ini, fin, mes, pend)
    ss[_K_DESTINOS] = destinos
    items = [dict(s, ir=s["ir"] if s["ir"] in destinos else None) for s in senales]
    items += [{"nivel": p["nivel"], "t": p["t"], "chip": p["chip"], "det": p["det"],
               "serie": None, "forma": "pct", "ir": f"p{i}" if f"p{i}" in destinos else None}
              for i, p in enumerate(pend)]
    items.sort(key=lambda x: {resumen.ROJO: 0, resumen.AMBAR: 1}.get(x["nivel"], 2))
    al_dia = [s["t"] for s in senales if s["nivel"] == resumen.VERDE] + al_dia
    items = [x for x in items if x["nivel"] != resumen.VERDE]

    costo_payload = None
    if costo:
        costo_payload = {k: v for k, v in costo.items() if k != "observaciones"}
    payload = _limpio({
        "mes": mes, "rotulo": _rotulo(mes),
        "meses": [{"k": m, "nombre": _rotulo(m)} for m in meses],
        "ini": ini.isoformat(), "fin": fin.isoformat(), "parcial": parcial,
        "anterior_corto": _corto(str(pd.Period(mes, freq="M") - 12)),
        "previo_corto": _corto(str(pd.Period(mes, freq="M") - 1)),
        "actual": {k: (actual or {}).get(k) for k in resumen.CIFRAS} if actual else None,
        "anterior": {k: anterior.get(k) for k in resumen.CIFRAS} if anterior else None,
        "costo": costo_payload,
        "previo": {"porcentaje": previo["porcentaje"]} if previo else None,
        "costo_ap": ({"porcentaje": costo_ap["porcentaje"],
                      "porcentaje_pos": costo_ap["porcentaje_pos"]} if costo_ap else None),
        "hist": hist, "diario": diario,
        "titular": resumen.titular(mes, hist, costo, previo, parcial, fin),
        "habitual": {k: resumen.habitual(hist, k) for k in ("ticket", "clientes")},
        "items": items, "al_dia": al_dia, "sin_calcular": sin_calcular,
        "calculable": bool((armado or {}).get("calculable")),
        "destinos": {k: d["rot"] for k, d in destinos.items()},
        "error_costos": error_costos,
        "demo": not data.secrets_disponibles(),
    })
    _COMPONENTE(key=_K_PANEL, data=payload, on_mes_change=_al_mes,
                on_ir_change=_al_ir, on_calcular_change=_al_calcular, width="stretch")
    hechos = []
    if actual:
        hechos.extend((mes, k, v) for k, v in actual.items()
                      if isinstance(v, (float, int)))
    if costo:
        hechos.extend((mes, "costo: " + k, v) for k, v in costo.items()
                      if isinstance(v, (float, int)))
    for h in hist:
        if h.get("venta") is not None:
            hechos.append((h["k"], "venta del mes", h["venta"]))
        if h.get("ppto") is not None:
            hechos.append((h["k"], "presupuesto del mes", h["ppto"]))
    publicar_contexto_ia(nombre_reporte, pd.DataFrame(
        hechos, columns=["PERIODO", "INDICADOR", "VALOR"]), {
            "alcance": "Ventas: todos los grupos, día del turno. Costos: cuatro "
                       "familias, incluye Eventos, excluye Venta interna (lo que va a "
                       "Mayta se descuenta una vez como salida); todas las "
                       "salidas salvo bajas se deducen, como el default de Costos. "
                       "Presupuesto: el neto cargado en Costos, todos los servicios.",
            "rango": (ini.isoformat(), fin.isoformat()),
        })
