"""graficos.compras - dashboard de Compras (5 drills).

Este modulo era un unico compras.py de 2.835 lineas; desde el refactor de
2026-08-01 es un paquete con un drill por archivo, igual que graficos/ tiene
un dashboard por archivo.

    _comun.py         helpers compartidos (movil, seleccion, mini barras)
    proveedor.py      drill de Proveedor (el mas grande)
    producto.py       drill de Producto: ranking + precio/cantidad/valor
                      (incluye el ranking por Familia — ver docstring propio)
    volatilidad.py    drill de Volatilidad: ranking (AgGrid, tooltip +
                      clic en fila) + candlestick + compras de la semana
    vs_ano_pasado.py  drill "Vs año pasado": Precio o Cantidad de un
                      producto en comun, o Valor por Familia (sin
                      selector), cada uno contra su serie del año
                      pasado/anterior

Punto de entrada publico: renderizar_graficos_compras (lo consume el
dispatcher de graficos/__init__.py). Vive aca abajo junto a la config del
rail derecho, que es lo que decide que drill se muestra.

_first_point y _periodo_serie se re-exportan porque test_graficos.py los
importa desde graficos.compras.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import SERIE_PRINCIPAL, TEXTO_PRINCIPAL, BLANCO
from utils import _norm, fmt_k
from graficos.base import (
    compartimento_filtros, contar_filtros, filtro_pills,
    _compras_layout, _compras_truncar, _render_rail,
    _resolver, publicar_contexto_ia, seccion_perezosa,
    renderizar_graficos_genericos, vista_activa,
)
from graficos.compras._comun import (  # noqa: F401  (re-export)
    _es_movil, _first_point, _periodo_serie,
)
from graficos.compras.proveedor import _compras_proveedor_drill
from graficos.compras.producto import _compras_producto_drill
from graficos.compras.volatilidad import _compras_volatilidad_drill
from graficos.compras.vs_ano_pasado import _compras_vs_ano_pasado_drill
from graficos import alturas




# Rail de Compras — cabecera "Compras / Gráficos" + secciones agrupadas por
# categoría (variante 2). Cada tupla es (id, label, icono):
#   · id     — el string que consume el resto del dashboard.
#   · label  — lo que se pinta en el botón del rail.
#   · icono  — shortcode Material que va al `icon=` de st.button.
# El icono es el TERCER elemento y `_render_rail` lo trata como opcional, así
# que los otros rails (Ajuste) siguen con tuplas de 2 sin enterarse. Nombres
# validados contra `streamlit.string_util.validate_material_icon`: si uno no
# existe, Streamlit tira StreamlitAPIException al dibujar el rail, o sea la
# pantalla entera. Ver arquitectura.md regla #147.

# ── KPI POR VISTA, para la franja superior ────────────────────────────────
# 2026-09-01, a pedido: cada vista lleva en línea el dato que la resume, y
# Tabla no ("todos, pero a Tabla no").
#
# Salen del df POST-CHIPS que ya tiene la vista, no de una consulta nueva:
# son seis `groupby` sobre datos en memoria. Si el usuario filtra por
# familia, el KPI sigue al filtro — que es lo que uno espera de un número
# que vive al lado del nombre de la vista.
#
# Cada uno es defensivo por separado: si falta su columna o no hay filas, esa
# vista se queda sin KPI y las demás no se enteran. Un KPI es decoración
# informativa; ninguno vale romper la navegación.

def _inic(nombre, n=5):
    """Las iniciales de un nombre largo de proveedor, para que entre en la
    franja. `VIBEJ COLIBRI SAC` -> `VIBEJ`. Se corta la PRIMERA palabra en
    vez de armar una sigla con las iniciales de todas: medido sobre los
    proveedores reales, la sigla ("VCS", "DGR") es irreconocible y la primera
    palabra casi siempre alcanza para identificarlos."""
    return str(nombre).strip().split()[0][:n].upper() if str(nombre).strip() else ""


def _delta(hoy, ant):
    """`(flecha, texto, color)` de una variacion, o None si no hay con que
    comparar. La convencion de color es la MISMA que usa el drill Vs año
    pasado (`vs_ano_pasado.py`, `ERROR if delta > 0 else EXITO`): en Compras
    GASTAR MAS es rojo. No se reinventa aca para que dos sitios de la misma
    pantalla no digan lo contrario del mismo signo."""
    if not ant or ant <= 0 or hoy is None:
        return None
    var = (hoy - ant) / ant * 100
    if abs(var) < 0.5:                     # ruido: ni flecha
        return None
    return ("▲" if var > 0 else "▼", f"{abs(var):.0f}%",
            "red" if var > 0 else "green")


def _kpis_vistas(d, d_full, col_valor, col_prov, col_fam, col_prod, col_punit,
                 col_docu, col_fecha):
    """`{id_vista: texto}` para `_render_rail(kpis=...)`.

    `d_full` es el mismo df SIN el filtro de fecha: de ahi sale el PERIODO
    ANTERIOR con el que se comparan los KPIs. Sin el no habria flecha — `d`
    es exactamente el rango vigente y no tiene con que compararse.
    """
    kpis = {}
    if d is None or getattr(d, "empty", True) or not col_valor:
        return kpis
    val = pd.to_numeric(d[col_valor], errors="coerce")

    # ── El periodo ANTERIOR: mismo largo, pegado por atras ───────────────
    # Se deriva del propio `d` y no del contexto de la franja: asi la
    # comparacion sigue al rango que el usuario tenga puesto, venga de la
    # franja o de una tarjeta, sin que este helper sepa cual es cual.
    prev = None
    if col_fecha and col_fecha in d.columns and d_full is not None:
        _f = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
        if len(_f):
            _ini, _fin = _f.min(), _f.max()
            _largo = _fin - _ini
            _ff = pd.to_datetime(d_full[col_fecha], errors="coerce")
            prev = d_full[(_ff >= _ini - _largo - pd.Timedelta(days=1))
                          & (_ff < _ini)]
            if prev.empty:
                prev = None

    def _suma(df_, col, clave):
        """Lo que sumo UN grupo puntual en ese df."""
        if df_ is None or col is None or col not in df_.columns:
            return None
        v = pd.to_numeric(df_[col_valor], errors="coerce")
        m = df_[col].astype(str) == clave
        return float(v[m].sum()) if m.any() else 0.0

    def _top(col):
        if not col or col not in d.columns:
            return None
        s = val.groupby(d[col].astype(str)).sum().dropna()
        s = s[s > 0]
        return (s.idxmax(), float(s.max())) if len(s) else None

    def _texto(valor, delta):
        """`:blue[valor] :red[▲12%]` — dos colores a proposito: el dato en
        azul, que lo separa del lavanda del nombre de la vista (fue el
        pedido), y la variacion en verde/rojo por signo."""
        _t = f":blue[{valor}]"
        if delta:
            _t += f" :{delta[2]}[{delta[0]}{delta[1]}]"
        return _t

    # PROVEEDOR: el que mas compro, contra lo que ESE MISMO compro antes.
    _t = _top(col_prov)
    if _t:
        kpis["Proveedor"] = _texto(
            f"{_inic(_t[0])} {fmt_k(_t[1])}",
            _delta(_t[1], _suma(prev, col_prov, _t[0])))

    # PRODUCTO: la familia que mas compro, contra esa misma familia antes.
    _t = _top(col_fam)
    if _t:
        kpis["Producto"] = _texto(
            f"{str(_t[0])[:3].upper()} {fmt_k(_t[1])}",
            _delta(_t[1], _suma(prev, col_fam, _t[0])))

    # VOLATILIDAD: QUE producto y cuanto (2026-09-01, a pedido: antes iba
    # solo el numero y no se sabia de que producto hablaba). Coeficiente de
    # variacion (desvio / media) y no el desvio pelado: un producto caro
    # tiene desvios grandes por escala, no por volatilidad. Piso de 5
    # compras porque con dos el CV es ruido.
    if col_punit and col_punit in d.columns and col_prod and col_prod in d.columns:
        pu = pd.to_numeric(d[col_punit], errors="coerce")
        g = pu.groupby(d[col_prod].astype(str))
        cv = (g.std() / g.mean().replace(0, pd.NA)).dropna()
        cv = cv[g.count() >= 5]
        if len(cv):
            _p = cv.idxmax()
            kpis["Volatilidad"] = _texto(
                f"{_compras_truncar(str(_p), 14)} ±{cv[_p] * 100:.0f}%", None)

    # DOCUMENTOS: cuantos en el SISTEMA y cuantos en SUNAT (2026-09-01, a
    # pedido). El del sistema sale de aca, que es barato. El de SUNAT no:
    # exige la consulta al SIRE, que hace la propia vista con su rango. Se
    # lo pide prestado por `session_state` —lo publica `documentos_sunat.py`
    # cuando dibuja— asi que aparece recien cuando esa vista se abrio una
    # vez. Preferible eso a disparar una consulta externa para decorar un
    # rotulo de navegacion.
    if col_docu and col_docu in d.columns:
        _n_sis = int(d[col_docu].nunique())
        _cruce = st.session_state.get("_cp_docs_cruce") or {}
        _txt = f"sis {_n_sis:,}".replace(",", ".")
        if _cruce.get("sunat") is not None:
            _txt += f" · sun {_cruce['sunat']:,}".replace(",", ".")
        _prev_docs = (int(prev[col_docu].nunique())
                      if prev is not None and col_docu in prev.columns else None)
        kpis["Documentos SUNAT"] = _texto(_txt, _delta(_n_sis, _prev_docs))

    # SEMANAL: la mejor semana del rango, contra la mejor de antes.
    if col_fecha and col_fecha in d.columns:
        f = pd.to_datetime(d[col_fecha], errors="coerce")
        s = val.groupby(f.dt.to_period("W")).sum().dropna()
        if len(s):
            _ant = None
            if prev is not None:
                _fp = pd.to_datetime(prev[col_fecha], errors="coerce")
                _vp = pd.to_numeric(prev[col_valor], errors="coerce")
                _sp = _vp.groupby(_fp.dt.to_period("W")).sum().dropna()
                _ant = float(_sp.max()) if len(_sp) else None
            kpis["Semanal"] = _texto(fmt_k(float(s.max())),
                                     _delta(float(s.max()), _ant))

    # VS AÑO PASADO: la familia que mas vario. El año pasado NO sale de este
    # df —esta filtrado por el rango vigente, que es justo lo que esa vista
    # compara— asi que se usa la columna `VALOR_ANO_ANTERIOR` del parquet. Y
    # se usa con el cuidado que pide CLAUDE.md: NO es un dato por fila, es el
    # total del producto en ese MES repetido en cada fila, asi que sumarla
    # derecho la infla (medido en su dia: x4.9). Se deduplica por
    # producto-mes con un `max` antes de sumar.
    #
    # Aca la flecha va DENTRO del KPI y no como delta aparte: el dato ya ES
    # una variacion, y una flecha sobre una variacion se leeria como la
    # variacion de la variacion.
    _col_ant = _resolver(d, ["Valor_ano_anterior", "Valor año anterior",
                             "VALOR_ANO_ANTERIOR"])
    if (_col_ant and col_fam and col_fecha and col_prod
            and all(c in d.columns
                    for c in (_col_ant, col_fam, col_fecha, col_prod))):
        _f = pd.to_datetime(d[col_fecha], errors="coerce")
        _base = pd.DataFrame({
            "fam": d[col_fam].astype(str),
            "prod": d[col_prod].astype(str),
            "mes": _f.dt.to_period("M"),
            "hoy": val,
            "ant": pd.to_numeric(d[_col_ant], errors="coerce"),
        }).dropna(subset=["mes"])
        if len(_base):
            _sant = (_base.groupby(["fam", "prod", "mes"])["ant"].max()
                     .groupby("fam").sum())
            _shoy = _base.groupby("fam")["hoy"].sum()
            _cmp = pd.concat([_shoy, _sant], axis=1).dropna()
            _cmp = _cmp[_cmp["ant"] > 0]
            if len(_cmp):
                _var = (_cmp["hoy"] - _cmp["ant"]) / _cmp["ant"] * 100
                _ft = _var.abs().idxmax()
                _sube = _var[_ft] > 0
                kpis["Vs año pasado"] = (
                    f":blue[{str(_ft)[:3].upper()}] "
                    f":{'red' if _sube else 'green'}"
                    f"[{'▲' if _sube else '▼'}{abs(_var[_ft]):.0f}%]")
    return kpis

_COMPRAS_RAIL_CATEGORIAS = (
    ("Dimensión", (("Proveedor",        "Proveedor",     ":material/local_shipping:"),
                   ("Producto",         "Producto",      ":material/inventory_2:"))),
    ("Precios",   (("Vs año pasado",    "Vs año pasado", ":material/compare_arrows:"),
                   ("Volatilidad",      "Volatilidad",   ":material/candlestick_chart:"))),
    ("SUNAT",     (("Documentos SUNAT", "Documentos",    ":material/receipt_long:"),)),
    ("Más",       (("Semanal",          "Semanal",       ":material/calendar_view_week:"),
                   ("Tabla",            "Tabla",         ":material/table_rows:"))),
)

# Vistas de Compras que se quedan el selector de fecha DENTRO de su tarjeta
# en vez de dejarlo en la franja superior. Hoy solo Documentos SUNAT: ahi la
# fecha no es contexto global sino EL filtro de la tabla (es el rango que se
# le consulta al SIRE), asi que vivia lejos de lo que filtra.
#
# `Semanal` estuvo aca un dia (2026-08-24) con un calendario propio de dos
# meses, y se saco al apilar las vistas: con las seis dibujandose en la MISMA
# corrida, dos duenos de la clave del rango no pueden convivir —
# `st.session_state` no se puede reescribir despues de que el widget de esa
# key ya se instancio— y Compras reventaba en cada carga. Ver regla #203.
#
# La leccion general, y el motivo de que la lista siga teniendo un solo
# miembro: en una pagina APILADA el rango es del REPORTE, no de la vista.
# Ver el analisis de la regla #210.
_VISTAS_CON_FECHA_PROPIA = {"Documentos SUNAT"}

# Subconjunto del anterior: las que ademas necesitan OTROS topes de
# calendario que los del parquet de Compras. Se separa a proposito — atar
# los bounds a `_VISTAS_CON_FECHA_PROPIA` haria que cualquier vista nueva
# que se quede la fecha heredara los limites del SIRE sin pedirlos.
_VISTAS_CON_BOUNDS_SUNAT = {"Documentos SUNAT"}

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail.
#
# Los dos datos viven en la MISMA tupla a propósito. El scrollspy tiene que
# saber qué botón encender cuando una sección entra en pantalla, y la
# tentación es deducirlo del nombre (`compras_sec_<slug>` ↔ `graf_btn_lat_
# <slug>`). No sirve: `_slug("Vs año pasado")` conserva la ñ y da
# `vs_año_pasado`, así que el que escribe la clave de la sección a mano
# escribe `vs_ano_pasado` y el apareo se rompe en silencio — sólo en esa
# vista, sólo en el resaltado. Emparejando acá, el slug del botón lo calcula
# quien lo dibuja y nadie tiene que adivinarlo.
#
# Fuera de la pila: `Documentos SUNAT`, que se lleva prestado el único
# selector de fecha de la app.
_PILA = (
    ("compras_sec_proveedor",     "Proveedor"),
    ("compras_sec_producto",      "Producto"),
    ("compras_sec_vs_ano_pasado", "Vs año pasado"),
    ("compras_sec_volatilidad",   "Volatilidad"),
    ("compras_sec_semanal",       "Semanal"),
    ("compras_sec_tabla",         "Tabla"),
)


def vista_quiere_fecha_propia():
    """True si la vista activa de Compras se queda el pill de fecha.

    La consulta `app.py` ANTES de dibujar la franja, para saber si le toca
    dibujarlo a el o al drill — el widget no se puede duplicar (su key es la
    clave canonica del rango, ver `franja_fecha`). Se resuelve sin dibujar el
    rail con `vista_activa`, que usa el mismo criterio que el rail usara
    despues, deep-link incluido.
    """
    return vista_activa(_COMPRAS_RAIL_CATEGORIAS,
                        "compras_graf_tipo") in _VISTAS_CON_FECHA_PROPIA


def bounds_fecha_de_la_vista():
    """`(min, max)` que la vista activa necesita en el calendario, o None.

    Gemela de `vista_quiere_fecha_propia` y con el mismo cliente: la
    consulta `app.py` antes de sembrar/recortar el rango. Devuelve None
    para el resto de las vistas — cada una se queda con los topes de su
    propio dato, incluida la Semanal, que filtra el parquet de Compras
    como todas las demas y por lo tanto NO quiere los topes del SIRE.

    Documentos SUNAT es la excepción porque no filtra el parquet de
    Compras: le pregunta al SIRE. Y los dos extremos salen de sitios
    distintos a propósito:

      · el PISO, de `sunat.limites_registro()` — antes de la primera
        factura del registro no hay nada que pedir;
      · el TECHO, de HOY — no del tope del parquet. Un techo puesto en
        "hasta donde llegó el último sync" siempre atrasa lo que tarde en
        correr el sync, así que el día de HOY nunca se puede elegir. Eso
        fue el bug: 2026-08-24, con comprobantes del 24 ya visibles en
        SUNAT, el calendario cortaba en el 21. `comprobantes_rango` sabe
        pedir en vivo los días que el parquet todavía no trajo. Ver
        `arquitectura.md` regla #197.
    """
    if vista_activa(_COMPRAS_RAIL_CATEGORIAS,
                    "compras_graf_tipo") not in _VISTAS_CON_BOUNDS_SUNAT:
        return None
    import datetime
    import zoneinfo

    import sunat

    # HOY en Lima, no en UTC: Streamlit Cloud corre en UTC y a partir de
    # las 19:00 de Perú ya está en el día siguiente — el calendario
    # ofrecería un mañana que SUNAT todavía no puede tener.
    hoy = datetime.datetime.now(zoneinfo.ZoneInfo("America/Lima")).date()
    limites = sunat.limites_registro()
    return (limites[0] if limites else None), hoy


def renderizar_graficos_compras(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard dedicado de Compras: 5 gráficos con pestañas + 5 mini-tops.

    `tabla_cb` se acepta por uniformidad de firma con el resto de
    dashboards (ver graficos/__init__.py) pero NO se usa: la vista Tabla
    de Compras es un item más de su propio rail y la arma este módulo,
    con los mismos chips Familia/Subfamilia que los gráficos."""
    col_fam    = _resolver(df_f, ["Familia", "Nombre Familia"])
    col_subfam = _resolver(df_f, ["Subfamilia", "Nombre Subfamilia"])
    col_prov   = _resolver(df_f, ["Nombre_proveedor", "Nombre proveedor", "Proveedor"])
    col_prod   = _resolver(df_f, ["Nombre_producto", "Nombre producto", "Producto"])
    col_um     = _resolver(df_f, ["Unidad de Ingreso", "Unidad_de_ingreso",
                                  "Unidad Ingreso", "Unidad Kardex", "Unidad_medida",
                                  "Unidad medida", "Unidad de medida", "Unidad_compra",
                                  "Unidad compra", "Unidad", "UM", "Und"])
    col_cant   = _resolver(df_f, ["Cantidad_compra", "Cantidad compra", "Cantidad"])
    col_valor  = _resolver(df_f, ["Valor_compra", "Valor compra", "Importe Total", "Valorizado"])
    col_punit  = _resolver(df_f, ["Precio_unit", "Precio unit", "Precio Unitario"])
    col_fecha  = _resolver(df_f, ["Fecha_documento", "Fecha documento",
                                  "Fecha_registro", "Fecha registro", "FECHA"])
    col_docu   = _resolver(df_f, ["Num Documento", "Num_Documento",
                                  "Numero Documento", "Numero_documento",
                                  "Nro Documento", "Nro_Documento", "Num Doc",
                                  "N Documento", "Documento", "Comprobante"])
    # Solo la usa el drill Volatilidad (mezclar monedas en una misma serie de
    # precio sería incorrecto). Ninguna otra vista de Compras la resuelve, y
    # el demo local no la trae — por eso el drill la trata como opcional.
    col_moneda = _resolver(df_f, ["Tipo_moneda", "Tipo Moneda", "Moneda"])
    if not col_fecha:
        for _c in df_f.columns:
            if pd.api.types.is_datetime64_any_dtype(df_f[_c]) or "fecha" in _norm(str(_c)):
                col_fecha = _c
                break

    if not col_valor:
        st.warning("No se encontró la columna de valor de compra. "
                   "Mostrando explorador genérico.")
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── Filtros Familia / Subfamilia: compartimento único de la franja ───
    # LAS OPCIONES SALEN DEL HISTÓRICO, NO DEL RANGO (2026-09-02, a pedido).
    #
    # Hasta hoy la lista se armaba con `df_f`, o sea con lo que dejaba pasar
    # la píldora de fecha, y eso tenía una consecuencia que nadie había
    # medido: al angostar el rango, una familia elegida podía dejar de estar
    # entre las opciones, y Streamlit la borra de la selección EN SILENCIO —
    # sin excepción, sin aviso, y sin devolverla cuando el rango se vuelve a
    # ampliar. Medido paso a paso en el navegador:
    #   · rango 4–24 ago → 8 familias ofrecidas; elegidas ENVASES + VINOS.
    #   · rango 24 ago (un día) → 3 ofrecidas; la selección queda en ENVASES.
    #   · rango 4–24 ago otra vez → 8 ofrecidas, la selección sigue en
    #     ENVASES. VINOS se perdió para siempre.
    # Lo único que lo delataba era el contador del compartimento pasando de
    # 2 a 1.
    #
    # Con el histórico como fuente la lista deja de moverse, así que no hay
    # nada que se pueda caer. El precio, asumido a sabiendas: ahora se puede
    # elegir una familia que no compró NADA en el rango y la vista sale
    # vacía. Eso ya tiene su cartel unas líneas más abajo, y es un estado
    # que el usuario provocó y puede deshacer — muy distinto de un filtro
    # que se borra solo.
    #
    # `df_full` puede no llegar (llamadores viejos): ahí cae a `df_f` y el
    # comportamiento es el de antes.
    fam_sel, sub_sel = [], []
    _ops_src = df_full if df_full is not None else df_f
    with compartimento_filtros(contar_filtros("compras_graf_filtro_fam",
                                              "compras_graf_filtro_sub")):
        _, fam_sel = filtro_pills(_ops_src, col_fam,
                                  "compras_graf_filtro_fam", "Familia")
        # CASCADA: Subfamilia sólo ofrece las que quedan bajo la Familia
        # elegida. Por eso el df recortado va aparte y no se reusa el que
        # devuelve el filtro de arriba — ése ya viene filtrado, pero el
        # recorte tiene que hacerse con la selección de ESTE rerun.
        #
        # Y desde el 2026-09-02 la cascada es EXIGENTE: sin Familia no hay
        # lista. Antes el rango de fechas la acotaba de hecho (con la franja
        # en un día eran 3 chips); al pasar las opciones al histórico esa
        # cota desapareció y el bloque saltó a 95 chips — medido: 1.688px de
        # subfamilias dentro de un panel de 420 con scroll, o sea 1.943px de
        # recorrido para un filtro que se usa de pasada. Noventa y cinco
        # opciones sin buscador no son un filtro, son una lista.
        #
        # No se esconde el bloque entero: queda el rótulo con un caption que
        # dice qué hacer. Un compartimento que aparece y desaparece según lo
        # que elegiste arriba se lee como que la app perdió el filtro.
        _d_sub = _ops_src
        if fam_sel and col_fam:
            _d_sub = _d_sub[_d_sub[col_fam].astype(str).isin(fam_sel)]
            _, sub_sel = filtro_pills(_d_sub, col_subfam,
                                      "compras_graf_filtro_sub", "Subfamilia")
        elif col_subfam and col_subfam in _ops_src.columns:
            # La clave se borra a mano y no se deja morir sola. Streamlit
            # recolecta el estado de un widget que dejó de dibujarse, pero
            # `contar_filtros` (arriba, en la etiqueta del compartimento) lee
            # session_state ANTES de que eso pase: sin este `pop`, al soltar
            # la Familia el badge diría "1" durante un rerun por una
            # Subfamilia que ya no filtra nada.
            st.session_state.pop("compras_graf_filtro_sub", None)
            st.markdown('<div class="filtro-rotulo">Subfamilia</div>',
                        unsafe_allow_html=True)
            st.caption("Elegí una Familia para ver sus subfamilias.")

    d = df_f
    if fam_sel and col_fam:
        d = d[d[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_subfam:
        d = d[d[col_subfam].astype(str).isin(sub_sel)]

    # El asistente IA tiene que ver ESTO (post-chips), no el df_f de app.py.
    publicar_contexto_ia("Compras", d,
                         {"Familia": fam_sel, "Subfamilia": sub_sel})

    if d is None or d.empty:
        # Desde el 2026-09-02 este cartel es alcanzable a propósito: las
        # opciones de Familia/Subfamilia salen del histórico, así que se
        # puede elegir una que no compró nada en el rango de la píldora. Por
        # eso el texto nombra a los DOS filtros y no sólo "los filtros".
        st.info("No hay compras con esta Familia/Subfamilia en el rango de "
                "fechas elegido. Ampliá el rango o soltá el filtro.")
        return

    # Data SIN filtro de fecha (para el toggle "Todo el histórico" del Panel B
    # del drill Proveedor). Se le aplican los mismos chips Familia/Subfamilia,
    # que no son de fecha. Si no llega df_full, cae a df_f (mismo comportamiento).
    d_full = df_full if df_full is not None else df_f
    if fam_sel and col_fam and col_fam in d_full.columns:
        d_full = d_full[d_full[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_subfam and col_subfam in d_full.columns:
        d_full = d_full[d_full[col_subfam].astype(str).isin(sub_sel)]

    _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)

    opciones = ["Proveedor", "Producto", "Vs año pasado", "Volatilidad",
                "Documentos SUNAT", "Semanal", "Tabla"]

    # Rail vertical fijo al borde DERECHO (componente compartido _render_rail):
    # selector de tipo de gráfico agrupado por categoría. El activo se marca
    # con type="primary"; la selección se persiste en compras_graf_tipo.
    # `secciones`: la pila de esta página. Con eso el rail vertical de la
    # izquierda sabe qué botón encender según lo que haya en pantalla, y
    # aparece a partir de la segunda sección. Ver `base.py::_render_rail`.
    graf = _render_rail(_COMPRAS_RAIL_CATEGORIAS, "compras_graf_tipo",
                        secciones=_PILA,
                        kpis=_kpis_vistas(d, d_full, col_valor, col_prov,
                                          col_fam, col_prod, col_punit,
                                          col_docu, col_fecha))
    if graf not in opciones:
        graf = opciones[0]

    # ── Quien dibuja el selector de fecha: la franja o el drill ─────────
    # Hay DOS vistas que se lo quedan (Documentos SUNAT y Semanal, ver
    # `_VISTAS_CON_FECHA_PROPIA`). El problema es de
    # ORDEN: la franja de `app.py` se dibuja mucho antes que este rail, y
    # ademas `_render_contenido` es un `@st.fragment`, asi que un clic aca
    # NO re-ejecuta `app.py`. En ese rerun parcial la franja sigue con la
    # decision de la vista ANTERIOR:
    #   · entrando a SUNAT  -> la franja ya dibujo la fecha Y el drill la
    #     dibujaria de nuevo: dos widgets con la misma key -> excepcion.
    #   · saliendo de SUNAT -> no la dibujo ninguno de los dos y la vista
    #     se queda sin selector de fecha (medido: eso pasaba).
    # Cuando no coinciden se fuerza un rerun COMPLETO, que es la unica
    # forma de que `app.py` vuelva a decidir. Cuesta un render extra al
    # cruzar esa frontera y nada el resto del tiempo.
    _quiere_propia = graf in _VISTAS_CON_FECHA_PROPIA
    if st.session_state.get("_franja_dibujo_fecha", True) == _quiere_propia:
        st.rerun(scope="app")

    # Tabla: usa el mismo AgGrid de la vista Tabla, pero como una opción más
    # del selector. `d` ya viene filtrado por los chips Familia/Subfamilia.
    # ── Vistas que siguen siendo un DESTINO propio ───────────────────────
    # Una excepción a la pila de abajo: Documentos SUNAT se lleva prestado
    # el ÚNICO selector de fecha de la app (`franja_fecha.render()`, la
    # misma función que llama `app.py`). Si estuviera siempre en pantalla,
    # las demás vistas se quedarían sin control de fecha arriba. Entra a la
    # pila cuando tenga rango propio — ver `vista_quiere_fecha_propia`.
    if graf == "Documentos SUNAT":
        # Import local a propósito: arrastra `sunat.py` y, con él,
        # `requests` — no hay por qué pagarlo al importar Compras si nadie
        # abre esta vista.
        from graficos.compras.documentos_sunat import renderizar_documentos_sunat
        with st.container(key="compras_sunat_drill_wrap"):
            # `df_full`, NO `d` -- `d` viene filtrado por los chips
            # Familia/Subfamilia (línea de arriba) y ese filtro no tiene
            # que tocar la vista "Cruce": SUNAT no sabe de familias (es
            # taxonomía nuestra, del maestro de productos — ver el
            # docstring del módulo), así que filtrar por familia ANTES de
            # cruzar hacía que un documento con TODAS sus líneas en una
            # familia no elegida desapareciera entero de `compras.parquet`
            # y saliera "Solo SUNAT" siendo falso — reportado en vivo
            # 2026-09-03 con un documento real (FA28-2312219, COMPAÑIA
            # FOOD RETAIL) que sí estaba en el parquet, mismo RUC y mismo
            # total que SUNAT. `_parquet_agrupado_por_documento` ya acota
            # por FECHA sola (`fecha_ini`/`fecha_fin`, el rango propio de
            # este drill) — no hace falta que además venga acotado por
            # familia. `df_full` puede ser `None` en llamadores viejos,
            # de ahí el fallback a `d`. Ver arquitectura.md regla #301.
            renderizar_documentos_sunat(
                df_full if df_full is not None else d, col_fecha)
        return

    # ══ LA PILA ══════════════════════════════════════════════════════════
    # Las vistas de Compras no se reemplazan: se apilan y se leen bajando.
    # El rail de la izquierda deja de ELEGIR contenido y pasa a MARCAR la
    # sección que está en pantalla (scrollspy, ver `base.py::_render_rail`).
    #
    # Cada sección va envuelta en `compras_sec_<slug>`, y ese slug es el
    # mismo que el de su botón del rail (`_slug` sobre el id de la vista):
    # así el observador de JS puede aparear sección con botón sin una tabla
    # de correspondencias que se desincronice.
    #
    # Sobre el costo: cada drill es un `@st.fragment`, así que construirlos
    # todos se paga UNA vez al entrar — un clic dentro de Proveedor
    # re-ejecuta su fragment y no toca a los demás.
    #
    # OJO con las keys de tarjeta: Volatilidad y Semanal usaban las dos
    # `ajuste_graf_card_izq_compras`. No chocaban porque nunca coexistían;
    # apiladas serían dos widgets con la misma key, que en Streamlit es una
    # excepción. Cada una lleva ahora su sufijo, y el prefijo
    # `ajuste_graf_card_` se conserva porque de él cuelga el CSS de tarjeta
    # (el clamp de una pantalla en `estilos/_80_cards.py`).

    # ── LA PILA, PEREZOSA ────────────────────────────────────────────────
    # Cada sección se dibuja en su propio `@st.fragment` y arranca en
    # ESQUELETO. El `IntersectionObserver` de `base.py::_render_rail` aprieta
    # su botón invisible cuando te acercás, y sólo ese fragment se
    # re-ejecuta — las otras cinco no se tocan.
    #
    # Por qué no se construyen todas de una, que era la versión anterior:
    # saturaba el hilo principal del navegador (~10 Plotly + 2 AgGrid a la
    # vez) y en Cloud salía "la página no responde". El servidor nunca fue el
    # problema. Ver `base.py::seccion_perezosa` y arquitectura.md #211.
    #
    # Los `def` de acá abajo son closures sobre las columnas ya resueltas:
    # el fragment necesita poder llamarlas MÁS TARDE, en su propio rerun,
    # cuando el cuerpo del dispatcher ya terminó.

    def _dib_proveedor():
            # Drill Proveedor→productos→proveedores del prod. Sin borde externo:
            # cada uno de sus 4 bloques internos lleva el suyo.
            with st.container(key="compras_prov_drill_wrap"):
                _compras_proveedor_drill(d, col_prov, col_prod, col_cant, col_valor,
                                         col_punit, col_um, col_fecha, col_docu,
                                         d_full=d_full)

    def _dib_producto():
            with st.container(key="compras_prod_drill_wrap"):
                _compras_producto_drill(d, col_prod, col_fam, col_valor, col_cant,
                                        col_punit, col_um, col_fecha, col_prov,
                                        d_full=d_full)

    def _dib_vs_ano_pasado():
            # Serie mensual + puente precio/cantidad + tabla de detalle. Es el
            # ÚNICO drill que recibe `d_full` además de `d`: su ventana de tiempo
            # es propia (arranca en "Todo") y el año pasado lo calcula
            # desplazando 12 meses su propio histórico, así que necesita el
            # histórico entero aunque la franja esté en un rango corto. Ver el
            # docstring del módulo, decisiones 1 y 2.
            with st.container(key="compras_vap_drill_wrap"):
                _compras_vs_ano_pasado_drill(d, col_prod, col_cant, col_fecha,
                                             col_valor, col_fam=col_fam,
                                             col_subfam=col_subfam, col_um=col_um,
                                             d_full=d_full)

    def _dib_volatilidad():
            with st.container(border=True, key="ajuste_graf_card_izq_vol"):
                _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                                           col_valor, col_cant, col_um, col_moneda,
                                           d_full=d_full)

    def _dib_semanal():
            # Tarjeta única a todo el ancho de la fila del drill — SIN
            # COLUMNAS_DRILL. Hasta el 2026-09-03 esto partía en col_izq
            # (el gráfico) / col_der (un panel de 5 mini-rankings:
            # Prod. valor/Proveedores/Cantidad/Frecuencia/Alzas precio).
            # Se sacó el panel derecho por redundante — a pedido, viendo el
            # inspector propio del proyecto: esos mismos rankings, pero
            # COMPLETOS y con su propio drill, ya viven un scroll más
            # arriba en la misma página apilada (secciones Proveedor y
            # Producto). Repetir un top-10 de paso acá no sumaba nada, y
            # el gráfico —ahora una serie única, no apilada por
            # producto— aprovecha mejor el ancho entero.
            with st.container(border=True, key="ajuste_graf_card_izq_sem"):
                if col_prod and col_fecha:
                    # Agrupar por: el mismo control que Proveedor/Salidas/
                    # Requerimientos (Día/Semana/Mes/Año sobre
                    # `_periodo_serie`), más una quinta opción propia de
                    # esta vista. "Por documento" no agrupa por FECHA,
                    # agrupa por COMPRA (fecha+proveedor+Nº documento):
                    # una orden con 5 líneas es una compra, no cinco —
                    # mismo criterio que `documentos_sunat.py` para no
                    # colisionar entre proveedores que reusan su propia
                    # numeración (regla #143). 2026-09-03, a pedido: antes
                    # esta tarjeta sólo sabía agrupar por semana, con un
                    # selector de "la semana empieza en" que se fue con
                    # este cambio — la ISO-semana de `_periodo_serie` es
                    # la misma que ya usa el resto de la app.
                    # Sin `st.columns` alrededor a propósito: eso era del
                    # `st.selectbox` que este control reemplazó (un
                    # dropdown SE ESTIRA solo al ancho del contenedor,
                    # así que 1/3.2 de la tarjeta lo achicaba a propósito
                    # para sus 3 opciones). `st.pills` no se estira —
                    # mide su propio contenido — y esa misma columna lo
                    # apretaba a 157px, forzando que "Por documento"
                    # envuelva a una segunda línea sin necesidad. Medido
                    # con el inspector (`?debug=1&diseno=1`) el
                    # 2026-09-03.
                    gran = st.pills(
                        "Agrupar por",
                        ["Día", "Semana", "Mes", "Año", "Por documento"],
                        default="Semana", key="compras_sem_gran",
                        label_visibility="collapsed") or "Semana"

                    # Cambiar de granularidad invalida el foco: una clave
                    # de "Semana" no existe en el espacio de "Mes". Mismo
                    # guard que `compras_vol_prod_prev` en volatilidad.py
                    # al cambiar de producto.
                    if st.session_state.get("compras_sem_gran_prev") != gran:
                        st.session_state["compras_sem_gran_prev"] = gran
                        st.session_state["compras_sem_focus"] = None

                    _fe   = pd.to_datetime(d[col_fecha], errors="coerce")
                    _cnt  = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                            if col_cant else pd.Series(0, index=d.index))
                    _pu   = (pd.to_numeric(d[col_punit], errors="coerce")
                            if col_punit else pd.Series(pd.NA, index=d.index))
                    _prvs = d[col_prov].astype(str) if col_prov else pd.Series("", index=d.index)
                    _docn = d[col_docu].astype(str) if col_docu else pd.Series("", index=d.index)

                    dd = pd.DataFrame({
                        "fecha": _fe, "prod": d[col_prod].astype(str), "prov": _prvs,
                        "docn": _docn, "cant": _cnt, "punit": _pu, "valor": _valor,
                    }).dropna(subset=["fecha"])

                    # Clave de COMPRA: fecha+proveedor+documento, no el Nº
                    # de documento solo (se repite entre proveedores que
                    # reusan su propia numeración). Sin proveedor o
                    # documento resuelto, cada FILA es su propia compra —
                    # fallback defensivo, no bloquea la vista.
                    _con_doc = bool(col_prov and col_docu)
                    dd["compra"] = (
                        dd["fecha"].dt.strftime("%Y-%m-%d") + "·" + dd["prov"] + "·" + dd["docn"]
                        if _con_doc else dd.index.astype(str))

                    if gran == "Por documento":
                        dd["clave"] = dd["compra"]
                        dd["lbl"] = dd["fecha"].dt.strftime("%d/%m")
                    else:
                        dd["clave"] = _periodo_serie(dd["fecha"], gran)
                        dd["lbl"] = dd["clave"]

                    _orden = (dd.drop_duplicates("clave")[["clave", "lbl"]]
                             .sort_values("clave"))
                    _ord_claves = _orden["clave"].tolist()
                    _ord_lbls = _orden["lbl"].tolist()

                    # Con una sola barra, "evolución" no se ve —el
                    # cuadro no miente, pero tampoco explica por qué
                    # hay tan poco. La causa casi siempre es el rango
                    # de fechas de la franja (arriba de TODO Compras,
                    # no de esta tarjeta): su default "1º del mes ->
                    # hoy" (app.py) se aplasta contra los bounds reales
                    # del parquet cuando el dato todavía no llega a
                    # "hoy" (mismo síntoma que arquitectura.md #293).
                    # 2026-09-03, a pedido ("para indicarle al
                    # usuario").
                    if len(_ord_claves) == 1:
                        st.caption("Sólo hay compras en un período "
                                  "dentro del rango de fechas activo "
                                  "(arriba) — ampliá el rango para ver "
                                  "la evolución.")

                    # UNA sola serie, no apilada por producto. La
                    # apilada (top 8 + Otros) mostraba 9 colores por
                    # barra que se pisaban con los puntos de "Compra
                    # individual" encima; el desglose por producto vive
                    # en el ranking completo de la sección Producto, un
                    # scroll más arriba. 2026-09-03, a pedido ("la
                    # apilada no es buena para esto").
                    g = dd.groupby("clave", as_index=False)[["valor", "cant"]].sum()

                    fig = go.Figure()
                    fig.add_bar(
                        x=g["clave"], y=g["valor"], name="Valor total",
                        marker=dict(color=SERIE_PRINCIPAL),
                        customdata=g["cant"],
                        hovertemplate=("%{x}<br>Valor: S/ %{y:,.2f}"
                                       "<br>Cantidad: %{customdata:,.1f}"
                                       "<extra></extra>"),
                    )

                    # Puntos superpuestos: una COMPRA, no una línea de
                    # producto — una orden de 5 líneas es un solo punto,
                    # no cinco. Se omiten en "Por documento": ahí cada
                    # barra YA es una compra y el punto caería pegado a
                    # su propia punta, sin sumar información. 2026-09-03,
                    # a pedido.
                    if gran != "Por documento":
                        docs_g = (dd.groupby(["clave", "compra"], as_index=False)
                                 .agg(valor=("valor", "sum"), fecha=("fecha", "min"),
                                      prov=("prov", "first")))
                        _cd_docs = docs_g[["fecha", "prov"]].assign(
                            fecha=docs_g["fecha"].dt.strftime("%d/%m/%Y")).to_numpy()
                        fig.add_scatter(
                            x=docs_g["clave"], y=docs_g["valor"], mode="markers",
                            name="Compra individual",
                            marker=dict(size=8, color=TEXTO_PRINCIPAL,
                                        line=dict(color=BLANCO, width=1.5)),
                            customdata=_cd_docs,
                            hovertemplate=("Compra · %{customdata[1]}<br>%{customdata[0]}"
                                           "<br>Valor: S/ %{y:,.2f}<extra></extra>"),
                        )

                    _compras_layout(fig, alto=alturas.PROTAGONISTA)
                    _tit_gran = {"Día": "por día", "Semana": "por semana",
                                "Mes": "por mes", "Año": "por año",
                                "Por documento": "por documento"}[gran]
                    fig.update_layout(
                        title=f"Compra {_tit_gran}",
                        legend=dict(orientation="h", y=-0.22, x=0,
                                    font=dict(size=10)),
                    )
                    fig.update_xaxes(type="category", categoryorder="array",
                                     categoryarray=_ord_claves,
                                     tickvals=_ord_claves, ticktext=_ord_lbls)

                    # Clic en una barra o un punto -> foco de la tabla de
                    # abajo. La key lleva el foco DE ANTES del clic: la
                    # selección de on_select persiste mientras la key no
                    # cambie, así que con key estática cada rerun re-lee
                    # el mismo punto y togglea para siempre (parpadeo).
                    # Mismo patrón que el click-drill de Por área/Por
                    # familia — ver CLAUDE.md y arquitectura.md #76.
                    _foco_antes = st.session_state.get("compras_sem_focus")
                    evt = st.plotly_chart(
                        fig, use_container_width=True, on_select="rerun",
                        selection_mode="points",
                        key=f"compras_g_semanal_{gran}_{_foco_antes or 'none'}")
                    _pt = _first_point(evt)
                    if _pt is not None:
                        _clic = _pt.get("x")
                        st.session_state["compras_sem_focus"] = (
                            None if _foco_antes == _clic else _clic)

                    # El CAPTION es un elemento simple: un `if/else`
                    # desnudo lo reconcilia bien (mismo conteo de
                    # elementos en los dos branches, sólo cambia el
                    # texto). La TABLA es otra cosa — medido en vivo
                    # (2026-09-03): con la tabla DENTRO de un
                    # `st.empty().container()` que en el branch "sin
                    # foco" se rellena con sólo el caption, el
                    # `st.dataframe` (glide-data-grid) sobrevivía
                    # igual, visible y con datos del foco anterior.
                    # `st.empty()` + `with hueco.container():` es la
                    # cura para el HUÉRFANO documentada en
                    # arquitectura.md regla #70, pero ese caso probado
                    # (chips de bienvenida de `asistente.py`) nunca
                    # REEMPLAZA el contenido por otra cosa — lo deja
                    # sin llenar. Acá el hueco de la tabla se vacía con
                    # `.empty()` EXPLÍCITO en el branch que no la
                    # necesita, dedicado sólo a la tabla, igual que el
                    # segundo caso de `asistente.py` (el hueco de
                    # "Consultando tus datos…", que se limpia con
                    # `hueco.empty()` antes de escribir la respuesta
                    # aparte) — no se reutiliza el mismo hueco para el
                    # caption.
                    _focus = st.session_state.get("compras_sem_focus")
                    _hueco_tabla = st.empty()
                    if _focus in set(dd["clave"]):
                        _det = dd[dd["clave"] == _focus].sort_values(
                            "valor", ascending=False)
                        _et = _det["lbl"].iloc[0]
                        st.caption(f"**{_et}** · {_det['compra'].nunique()} "
                                  f"compras · S/ {_det['valor'].sum():,.2f}")
                        tp = _det[["fecha", "prov", "prod", "cant", "punit",
                                  "valor"]].rename(columns={
                            "fecha": "Fecha", "prov": "Proveedor",
                            "prod": "Producto", "cant": "Cantidad",
                            "punit": "P. unit.", "valor": "Valor"})
                        fmts = {
                            "Fecha": lambda v: f"{v:%d/%m/%Y}",
                            "Cantidad": lambda v: f"{v:,.1f}",
                            "P. unit.": lambda v: ("—" if pd.isna(v)
                                                   else f"S/ {v:,.2f}"),
                            "Valor": lambda v: f"S/ {v:,.2f}",
                        }
                        with _hueco_tabla.container():
                            st.dataframe(
                                tp.style.format(fmts).hide(axis="index"),
                                use_container_width=True, hide_index=True,
                                height=alturas.por_filas(len(tp), px_fila=34,
                                                         extra=60, minimo=0,
                                                         rol=alturas.MINI))
                    else:
                        st.caption("Tocá una barra o un punto para "
                                  "ver el detalle.")
                        _hueco_tabla.empty()

                else:
                    st.info("No hay columnas suficientes para este gráfico.")

    def _dib_tabla():
            # Cierra la página con el detalle: el mismo AgGrid de la vista
            # Tabla. `d` ya viene filtrado por los chips Familia/Subfamilia.
            from tablas import renderizar_aggrid_compras as _render_tabla_compras
            from estilos import TAM_FUENTE
            _font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam", "Mediano"), 14)
            _render_tabla_compras(d, _font_px)

    _DIBUJANTES = {
        "compras_sec_proveedor":     _dib_proveedor,
        "compras_sec_producto":      _dib_producto,
        "compras_sec_vs_ano_pasado": _dib_vs_ano_pasado,
        "compras_sec_volatilidad":   _dib_volatilidad,
        "compras_sec_semanal":       _dib_semanal,
        "compras_sec_tabla":         _dib_tabla,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje. Si llevara la key el fragment, cada
    # activación reemplazaría el nodo observado y los dos observadores se
    # quedarían mirando un elemento que ya no está en el documento.
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
