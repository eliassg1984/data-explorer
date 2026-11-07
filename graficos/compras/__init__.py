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
    documentos_sunat.py  el drill del REPORTE «Documentos SUNAT»: vive
                      aca pero ya no es una vista de Compras — lo
                      despacha graficos/sunat_reporte.py (2026-09-30,
                      regla #577)

Punto de entrada publico: renderizar_graficos_compras (lo consume el
dispatcher de graficos/__init__.py). Vive aca abajo junto a la config del
rail derecho, que es lo que decide que drill se muestra.

_first_point y _periodo_serie se re-exportan porque test_graficos.py los
importa desde graficos.compras.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
from tema import SERIE_PRINCIPAL, TEXTO_PRINCIPAL, BLANCO
from utils import _norm, fmt_k
from graficos.base import (
    _compras_layout, _compras_truncar, _render_rail,
    _resolver, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
    recortar_por_tarjeta, seccion_perezosa,
    renderizar_graficos_genericos,
)
from graficos.compras._filtros_vista import (
    filtros_vista, panel_filtros_vista, preparar_filtros_vista, recortar_filtros_vista,
)
from graficos.compras._comun import (  # noqa: F401  (re-export)
    # `CATEGORIA_SEC` la consumen los cinco drills Y este dispatcher; se
    # reexporta acá porque su sitio natural de lectura es al lado de `_PILA`
    # (sus claves son las de esa tupla) aunque viva en `_comun` por el ciclo
    # de imports. `test_graficos.py` verifica que sigan apareadas.
    # `SEC_ABRE_EN_EL_MES` no la usa este módulo: la lee `app.py`, que es
    # quien arma los defaults publicados. Se reexporta para que `app.py`
    # hable con el paquete y no con un privado (`_comun`).
    CATEGORIA_SEC, SEC_ABRE_EN_EL_MES,
    _es_movil, _first_point, _periodo_serie, familias_de_tarjeta,
)
from graficos.compras.proveedor import _compras_proveedor_drill
from graficos.compras._documentos_proveedor import (
    render_seccion as _docs_seccion,
)
from graficos.compras.producto import _compras_producto_drill
from graficos.compras.volatilidad import _compras_volatilidad_drill
from graficos.compras.vs_ano_pasado import _compras_vs_ano_pasado_drill
from graficos.compras.semanal import _compras_semanal_drill
from graficos import alturas
from graficos import periodo




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


def _kpis_vistas(df_de_vista, d_full, col_valor, col_prov, col_fam, col_prod,
                 col_punit, col_docu, col_fecha):
    """`({id_vista: texto}, {id_vista: estado})`; hoy se usa el SEGUNDO.

    El segundo dict es el SEMAFORO (2026-09-07, a pedido: "mas KPI"). Nacio
    como lo unico del KPI que sobrevivia al riel PLEGADO —en 46px no entra
    un numero, pero si un punto de color— y desde el 2026-09-18 es lo unico
    que sobrevive y punto: el texto ya no se dibuja en el rail (#465). Se
    sigue calculando porque el punto SE DERIVA de el; responde de un vistazo
    la pregunta que importa con la columna cerrada: hay algo que mirar?

    Los valores son NOMBRES DE VARIABLE CSS (`success`/`danger`/
    `warning`), no colores ni estados propios: `_render_rail` los mete
    tal cual en un `var(--…)`. Sin tabla de traduccion en el medio no hay
    dos sitios que se puedan desincronizar.

    Y se DERIVAN DEL TEXTO ya armado, no en paralelo: el KPI trae
    `:red[▲…]` o `:green[▼…]`, asi que el punto dice por construccion lo
    mismo que el numero de al lado. Calcularlos por separado seria abrir
    la puerta a un punto verde junto a una flecha roja.

    `df_de_vista` ES UN CALLABLE Y NO UN DATAFRAME desde el 2026-09-08, y
    ese es todo el cambio de esta funcion. Antes recibia UN `d`: el rango
    era uno solo para todo el reporte, asi que los seis KPI hablaban del
    mismo periodo por construccion. Ahora cada seccion de la pila tiene su
    propio rango (ver `CATEGORIA_SEC`), y un KPI calculado sobre otro
    periodo que el de su tarjeta seria peor que no tenerlo: el rail diria
    un numero y la tarjeta de al lado otro, sin nada que explique la
    diferencia. Cada bloque de aca abajo pide EL DF DE SU VISTA.

    `d_full` es el histórico de cada vista, obtenido por nombre si es callable.
    De ahi sale el PERIODO
    ANTERIOR con el que se comparan los KPIs. Sin el no habria flecha — el
    df de una vista es exactamente su rango vigente y no tiene con que
    compararse.
    """
    kpis, estados = {}, {}

    def _prev_de(dv, historico):
        """El periodo ANTERIOR de `dv`: mismo largo, pegado por atras.

        Se deriva del PROPIO `dv` y no del contexto de la franja: asi la
        comparacion sigue al rango que tenga puesto ESA tarjeta, sin que
        este helper sepa de donde salio.
        """
        if not (col_fecha and dv is not None and col_fecha in dv.columns
                and historico is not None):
            return None
        _f = pd.to_datetime(dv[col_fecha], errors="coerce").dropna()
        if not len(_f):
            return None
        _ini, _fin = _f.min(), _f.max()
        _largo = _fin - _ini
        _ff = pd.to_datetime(historico[col_fecha], errors="coerce")
        prev = historico[(_ff >= _ini - _largo - pd.Timedelta(days=1))
                         & (_ff < _ini)]
        return None if prev.empty else prev

    def _vista(nombre):
        """`(df, valores, prev)` de una vista, o `(None, None, None)`.

        Las tres cosas juntas porque los bloques de abajo necesitan las
        tres, y pedirlas sueltas invitaria a que uno mezclara el `val` de
        una vista con el `df` de otra — que es exactamente el cruce que
        este cambio vino a sacar.
        """
        dv = df_de_vista(nombre)
        if (dv is None or getattr(dv, "empty", True) or not col_valor
                or col_valor not in dv.columns):
            return None, None, None
        historico = d_full(nombre) if callable(d_full) else d_full
        return dv, pd.to_numeric(dv[col_valor], errors="coerce"), _prev_de(dv, historico)

    def _suma(df_, col, clave):
        """Lo que sumo UN grupo puntual en ese df."""
        if df_ is None or col is None or col not in df_.columns:
            return None
        v = pd.to_numeric(df_[col_valor], errors="coerce")
        m = df_[col].astype(str) == clave
        return float(v[m].sum()) if m.any() else 0.0

    def _top(dv, val, col):
        if dv is None or not col or col not in dv.columns:
            return None
        s = val.groupby(dv[col].astype(str)).sum().dropna()
        s = s[s > 0]
        return (s.idxmax(), float(s.max())) if len(s) else None

    def _texto(que, valor, delta, contra="el período anterior"):
        """El texto del TOOLTIP de la vista: qué se mide, el número y contra
        qué se compara, en una frase que se entienda sola.

        Hasta el 2026-09-18 esto era la etiqueta en línea del rail
        (`:blue[VIBEJ S/ 25.9k] :red[▲12%]`, iniciales incluidas para que
        entrara en la fila). Se retiró del rail (#465) y desde el
        2026-09-19 vuelve como tooltip de la vista: el punto de color de la
        fila sale de este mismo texto, y sin él no había forma de saber qué
        decía — se reportó así: «veo que algunas vistas tienen un punto
        rojo, eso qué significa?». En un tooltip hay sitio, así que va el
        nombre COMPLETO y no las iniciales.

        La variación sigue en `:red[…]`/`:green[…]`, que es de donde se
        derivan los `estados` más abajo."""
        _t = f"**{que}:** {valor}"
        if delta:
            _t += (f" · :{delta[2]}[{delta[0]}{delta[1]}] contra {contra}")
        return _t

    # PROVEEDOR: el que mas compro, contra lo que ESE MISMO compro antes.
    d_v, val, prev = _vista("Proveedor")
    _t = _top(d_v, val, col_prov)
    if _t:
        kpis["Proveedor"] = _texto(
            "Proveedor al que más le compraste", f"{_t[0]} — {fmt_k(_t[1])}",
            _delta(_t[1], _suma(prev, col_prov, _t[0])),
            "lo que le compraste en el período anterior")

    # PRODUCTO: la familia que mas compro, contra esa misma familia antes.
    d_v, val, prev = _vista("Producto")
    _t = _top(d_v, val, col_fam)
    if _t:
        kpis["Producto"] = _texto(
            "Familia que más se compró", f"{_t[0]} — {fmt_k(_t[1])}",
            _delta(_t[1], _suma(prev, col_fam, _t[0])))

    # VOLATILIDAD: QUE producto y cuanto (2026-09-01, a pedido: antes iba
    # solo el numero y no se sabia de que producto hablaba). Coeficiente de
    # variacion (desvio / media) y no el desvio pelado: un producto caro
    # tiene desvios grandes por escala, no por volatilidad. Piso de 5
    # compras porque con dos el CV es ruido.
    d_v, val, prev = _vista("Volatilidad")
    if (d_v is not None and col_punit and col_punit in d_v.columns
            and col_prod and col_prod in d_v.columns):
        pu = pd.to_numeric(d_v[col_punit], errors="coerce")
        g = pu.groupby(d_v[col_prod].astype(str))
        cv = (g.std() / g.mean().replace(0, pd.NA)).dropna()
        cv = cv[g.count() >= 5]
        if len(cv):
            _p = cv.idxmax()
            # CUANTOS, no solo el peor (2026-09-07, a pedido). El corte es
            # CV >= 1, o sea el desvio iguala o supera al promedio — no es
            # un umbral tuneado sino el punto donde el precio deja de
            # tener un valor "tipico". Si hay varios, es lo accionable: el
            # peor solo dice que existe UN caso raro.
            #
            # OJO con una divergencia que ya estaba y este contador hace
            # mas visible: aca la volatilidad es el CV del precio unitario
            # y la VISTA rankea por `_vol_score` (suma de variaciones
            # semana a semana, volatilidad.py). Son dos metricas, asi que
            # el producto que nombra el rail puede no ser el primero de la
            # tabla. Unificarlas es un cambio aparte.
            _n_alta = int((cv >= 1.0).sum())
            _txt_vol = f"{_p} (su precio varía ±{cv[_p] * 100:.0f}%)"
            if _n_alta > 1:
                _txt_vol += (f" · {_n_alta} productos con un precio que varía "
                             "tanto como vale")
                estados["Volatilidad"] = "warning"
            kpis["Volatilidad"] = _texto("Precio más inestable", _txt_vol, None)

    # (Acá vivía el KPI de «Documentos SUNAT»: cuántos en el sistema, cuántos
    # en SUNAT y cuántos a revisar. Se fue con la vista el 2026-09-30, cuando
    # pasó a ser un reporte propio; lo arma ahora
    # `graficos/sunat_reporte.py::_kpi_de_la_vista`. Regla #577.)

    # COMPRAS POR PERÍODO (la vieja «Semanal», renombrada el 2026-09-19): la
    # mejor semana del rango, contra la mejor de antes.
    d_v, val, prev = _vista("Compras por período")
    if d_v is not None and col_fecha and col_fecha in d_v.columns:
        f = pd.to_datetime(d_v[col_fecha], errors="coerce")
        s = val.groupby(f.dt.to_period("W")).sum().dropna()
        if len(s):
            _ant = None
            if prev is not None:
                _fp = pd.to_datetime(prev[col_fecha], errors="coerce")
                _vp = pd.to_numeric(prev[col_valor], errors="coerce")
                _sp = _vp.groupby(_fp.dt.to_period("W")).sum().dropna()
                _ant = float(_sp.max()) if len(_sp) else None
            kpis["Compras por período"] = _texto(
                "Mejor semana", fmt_k(float(s.max())),
                _delta(float(s.max()), _ant),
                "la mejor semana del período anterior")

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
    d_v, val, prev = _vista("Vs año pasado")
    _col_ant = (_resolver(d_v, ["Valor_ano_anterior", "Valor año anterior",
                                "VALOR_ANO_ANTERIOR"])
                if d_v is not None else None)
    if (_col_ant and col_fam and col_fecha and col_prod
            and all(c in d_v.columns
                    for c in (_col_ant, col_fam, col_fecha, col_prod))):
        _f = pd.to_datetime(d_v[col_fecha], errors="coerce")
        _base = pd.DataFrame({
            "fam": d_v[col_fam].astype(str),
            "prod": d_v[col_prod].astype(str),
            "mes": _f.dt.to_period("M"),
            "hoy": val,
            "ant": pd.to_numeric(d_v[_col_ant], errors="coerce"),
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
                    f"**Familia que más cambió contra el año pasado:** {_ft} · "
                    f":{'red' if _sube else 'green'}"
                    f"[{'▲' if _sube else '▼'}{abs(_var[_ft]):.0f}%]")
    # El semaforo, derivado del texto que se acaba de armar. La excepcion
    # (ambar) GANA sobre la direccion: "3 documentos a revisar" pide una
    # accion y "subio 6%" no, asi que ya viene puesta desde arriba y aca
    # solo se rellenan las que faltan.
    #
    # `:red[` es GASTAR MAS, y por eso mapea a `danger`: es la misma
    # convencion de `_delta` y del drill Vs año pasado, donde en Compras
    # el rojo es el gasto que sube. No se reinventa aca.
    for _vista, _t in kpis.items():
        if estados.get(_vista):
            continue
        if ":red[" in _t:
            estados[_vista] = "danger"
        elif ":green[" in _t:
            estados[_vista] = "success"
    # Y el tooltip termina diciendo qué significa SU punto. En Compras el
    # rojo es GASTAR MÁS (ver arriba): sin decirlo, un punto rojo junto a
    # «la mejor semana» se lee como una alarma y no como «subió».
    _que_dice = {
        "danger": ":red[●] **rojo:** subió — en Compras, se gastó más",
        "success": ":green[●] **verde:** bajó — en Compras, se gastó menos",
        "warning": ":orange[●] **ámbar:** hay algo que revisar",
    }
    for _vista in kpis:
        if estados.get(_vista) in _que_dice:
            kpis[_vista] += "\n\n" + _que_dice[estados[_vista]]
    return kpis, estados


# «Compras por período» va PRIMERA, en Dimensión (2026-09-19, a pedido: «que
# la vista por semana figure como la primera vista, y dado que tiene más
# detalle que sólo la vista semanal, sugiéreme un nombre»). Se llamaba
# «Semanal» y ya no era sólo semanal —día, semana, mes, año o por documento,
# con el detalle hasta las líneas—. Va en Dimensión y no en un grupo propio
# porque el TIEMPO es la tercera forma de partir las compras, al lado de
# Proveedor y Producto. El nombre interno sigue siendo «semanal»
# (`compras_sec_semanal`, `semanal.py`, las keys `compras_sem_*`): cambiarlo
# era renombrar estado de sesión y CSS para que nadie lo vea.
# LOS RÓTULOS (2º elemento) SON LO QUE VE EL USUARIO; el id (1º) es lo que
# consume el resto del código (keys, slug del scrollspy, `_PILA`, los dicts de
# KPI/estado). Por eso renombrar la etiqueta del rail es un cambio de una sola
# columna: 2026-09-21, a pedido, se alargaron cinco —«Por Proveedor», «Por
# Producto», «Comparación Año Pasado», «Volatilidad de Precios», «Documentos
# SUNAT»— sin tocar ningún id. (La última ya no está: desde el 2026-09-30
# «Documentos SUNAT» es un reporte propio, `graficos/sunat_reporte.py`,
# regla #577.) Entran en la columna desplegada (~183px al
# rótulo, 13px de fuente) con el `text-overflow: ellipsis` de `_28_arbol.py`
# como red; plegada sólo se ve el ícono.
#
# La «Tabla» de «Más» está OCULTA desde el 2026-09-23, con las de los demás
# reportes: `rail_sin_tablas` acá y `pila_sin_tablas` en `_PILA`, siempre de
# a par (regla #507). «Detalle docs.» se queda: no es la Tabla.
_COMPRAS_RAIL_CATEGORIAS = rail_sin_tablas((
    ("Dimensión", (("Compras por período", "Por período",   ":material/calendar_view_week:"),
                   ("Proveedor",           "Por Proveedor", ":material/local_shipping:"),
                   ("Producto",            "Por Producto",  ":material/inventory_2:"))),
    ("Análisis",  (("Volatilidad",   "Precios", ":material/price_change:"),
                   ("Vs año pasado", "Comparación Año Pasado", ":material/compare_arrows:"))),
    ("Más",       (("Tabla",                     "Tabla",         ":material/table_rows:"),
                   # «Detalle docs.» (id «Documentos por proveedor») NO es
                   # «Documentos SUNAT», que desde el 2026-09-30 es otro
                   # reporte: aquélla son los comprobantes del SIRE; ésta, el
                   # detalle por proveedor que sale del parquet.
                   ("Documentos por proveedor", "Detalle docs.", ":material/list_alt:"))),
))

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
# Hasta el 2026-09-30 quedaba una vista FUERA de la pila: «Documentos
# SUNAT», un destino aparte con el calendario entero dentro de su tarjeta.
# Hoy es un reporte propio (`graficos/sunat_reporte.py`, regla #577) y toda
# vista de Compras es una sección de esta tupla.
#
# 2026-09-09, a pedido («bajemos Detalle de documentos por proveedor»):
# `compras_sec_documentos` entra al FINAL. No es una vista nueva — es la
# tarjeta que cerraba la sección Proveedor, que ahora tiene sitio y botón
# propios. Comparte el rango de Proveedor por `CATEGORIA_SEC`, así que sigue
# hablando del mismo período que el ranking del que sale.
#
# 2026-09-19, a pedido: «Compras por período» (la vieja «Semanal») sube a la
# PRIMERA sección. La primera es la que se construye al abrir el reporte
# (`activa_de_entrada`); las demás esperan a que uno se acerque. Ninguna
# depende de que Proveedor se construya antes: «Documentos por proveedor»
# recorta con el mismo rango (`CATEGORIA_SEC`), no con estado de sesión.
_PILA = pila_sin_tablas((
    ("compras_sec_semanal",       "Compras por período"),
    ("compras_sec_proveedor",     "Proveedor"),
    ("compras_sec_producto",      "Producto"),
    ("compras_sec_volatilidad",   "Volatilidad"),
    ("compras_sec_vs_ano_pasado", "Vs año pasado"),
    ("compras_sec_tabla",         "Tabla"),
    ("compras_sec_documentos",    "Documentos por proveedor"),
))

# ── Con qué familias abre Compras ─────────────────────────────────────────
# 2026-09-05, a pedido: "alimentos, bebidas, vinos y envases". Son los
# nombres REALES del parquet, no etiquetas — "bebidas" son DOS familias y
# "envases" se llama ENVASES Y EMBALAJES. Las ocho, medidas contra R2 ese
# día (filas / valorizado):
#   ALIMENTOS           36.584  S/5,64M   ← entra
#   COSTOS PRODUCCION    7.183  S/3,51M
#   GASTOS ADMINISTRAT.    292  S/657k
#   VINOS Y ESPUMANTES   1.447  S/447k    ← entra
#   BEBIDAS CON ALCOHOL  2.353  S/236k    ← entra
#   ENVASES Y EMBALAJES  1.309  S/196k    ← entra
#   GASTOS VENTAS          268  S/174k
#   BEBIDAS SIN ALCOHOL  2.134  S/135k    ← entra
# O sea: la vista abre con 43.827 de 51.570 filas y S/6,65M de S/10,99M.
# Lo que queda afuera es gasto/costo indirecto, no mercadería.
#
# Es un PUNTO DE PARTIDA, no un piso: los chips se sueltan como cualquier
# otro filtro y el badge del compartimento dice "1" desde la primera carga
# (por eso la siembra va antes de `contar_filtros`, ver
# `base.sembrar_seleccion`). Verificado en el navegador el 2026-09-05: la
# primera carga trae los cinco chips prendidos y el badge en 1; al soltarlos
# todos queda en cero y NO se vuelven a sembrar. Ese «prendidos» valía sólo
# hasta la primera corrida completa: después de un atajo de fecha el panel
# abría con los ocho chips apagados y el filtro aplicando igual (regla #467,
# arreglado en `base.seleccion_en_panel`).
#
# Efecto lateral medido y aceptado: con Familia elegida la cascada de
# Subfamilia ya no está vacía al abrir — son 33 de las 95 del histórico,
# 428px, o sea el panel de 420 justo. Los 95 que la cascada exigente vino a
# evitar eran 1.688px.
_FAMILIAS_DE_ENTRADA = ("ALIMENTOS", "BEBIDAS CON ALCOHOL",
                        "BEBIDAS SIN ALCOHOL", "VINOS Y ESPUMANTES",
                        "ENVASES Y EMBALAJES")


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
    # Las de Documento y Montos de «Compras por período» (reglas #621 y
    # #624). Sin ellas (el
    # demo) los controles no filtran nada.
    col_tipo_doc = _resolver(df_f, ["Tipo_documento", "Tipo documento"])
    col_igv = _resolver(df_f, ["Valor_igv_compra_mn", "Valor igv compra mn"])
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

    # Las opciones salen del histórico, independientemente del rango de cada vista.
    _ops_src = df_full if df_full is not None else df_f
    _op_fam = sorted(_ops_src[col_fam].dropna().astype(str).unique()) if col_fam in _ops_src.columns else []
    _mapa_sub = {}
    if col_fam in _ops_src.columns and col_subfam in _ops_src.columns:
        pares = _ops_src[[col_fam, col_subfam]].dropna().astype(str).drop_duplicates()
        _mapa_sub = {f: tuple(grupo[col_subfam]) for f, grupo in pares.groupby(col_fam)}
    _selecciones = {clave: preparar_filtros_vista(clave, _op_fam, _mapa_sub, _FAMILIAS_DE_ENTRADA)
                    for clave, _ in _PILA}
    _cache_hist, _cache_sec = {}, {}

    def _hist_sec(clave):
        seleccion = _selecciones.get(clave, ((), ()))
        if seleccion not in _cache_hist:
            _cache_hist[seleccion] = recortar_filtros_vista(_ops_src, col_fam, col_subfam, seleccion)
        return _cache_hist[seleccion]

    def _d_sec(clave):
        categoria = CATEGORIA_SEC.get(clave)
        seleccion = _selecciones.get(clave, ((), ()))
        cache_key = (categoria, seleccion)
        if cache_key not in _cache_sec:
            _cache_sec[cache_key] = (
                recortar_por_tarjeta(_hist_sec(clave), col_fecha, categoria) if categoria
                else recortar_filtros_vista(df_f, col_fam, col_subfam, seleccion)
            )
        return _cache_sec[cache_key]

    _SEC_DE_VISTA = {vista: clave for clave, vista in _PILA}

    def _df_de_vista(nombre):
        return _d_sec(_SEC_DE_VISTA.get(nombre))

    # Rail vertical fijo al borde DERECHO (componente compartido _render_rail):
    # selector de tipo de gráfico agrupado por categoría. El activo se marca
    # con type="primary"; la selección se persiste en compras_graf_tipo.
    # `secciones`: la pila de esta página. Con eso el rail vertical de la
    # izquierda sabe qué botón encender según lo que haya en pantalla, y
    # aparece a partir de la segunda sección. Ver `base.py::_render_rail`.
    # DEL PAR SOLO VIAJA EL SEMAFORO (2026-09-18, a pedido: "quitemos todos
    # los KPIs de las vistas del rail lateral"). El texto se sigue armando
    # porque el punto de color se DERIVA de el —es lo que garantiza que el
    # punto no diga verde donde el numero decia rojo— pero ya no se dibuja.
    # Ver regla #465.
    _kpis_rail, _estados_rail = _kpis_vistas(
        _df_de_vista, lambda vista: _hist_sec(_SEC_DE_VISTA.get(vista)), col_valor,
        col_prov, col_fam, col_prod, col_punit, col_docu, col_fecha)
    graf = _render_rail(_COMPRAS_RAIL_CATEGORIAS, "compras_graf_tipo",
                        secciones=_PILA, estados=_estados_rail,
                        kpis=_kpis_rail)
    clave_activa = _SEC_DE_VISTA.get(graf, _PILA[0][0])
    publicar_contexto_ia("Compras", _d_sec(clave_activa), filtros_vista(clave_activa))

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

    def _familias_de(clave):
        categoria = CATEGORIA_SEC.get(clave)
        base = recortar_por_tarjeta(_ops_src, col_fecha, categoria) if categoria else _ops_src
        familias, subfamilias = _selecciones[clave]
        base = recortar_filtros_vista(base, col_fam, col_subfam, ((), subfamilias))
        opciones = familias_de_tarjeta(base, col_fam, col_valor, familias)
        if opciones is not None:
            opciones["en_panel"] = True
        return opciones

    def _dib_proveedor():
        clave = "compras_sec_proveedor"
        with st.container(key="compras_prov_drill_wrap"):
            _compras_proveedor_drill(
                _d_sec(clave), col_prov, col_prod, col_cant, col_valor,
                col_punit, col_um, col_fecha, col_docu,
                d_full=_hist_sec(clave), familias=_familias_de(clave))

    def _dib_producto():
        clave = "compras_sec_producto"
        with st.container(key="compras_prod_drill_wrap"):
            _compras_producto_drill(
                _d_sec(clave), col_prod, col_fam, col_valor, col_cant,
                col_punit, col_um, col_fecha, col_prov,
                d_full=_hist_sec(clave), col_subfam=col_subfam,
                col_docu=col_docu, familias=_familias_de(clave))

    def _dib_vs_ano_pasado():
        clave = "compras_sec_vs_ano_pasado"
        # El navegador aplica Familia y conserva el contexto de lo excluido.
        todas = recortar_filtros_vista(_ops_src, col_fam, col_subfam, ((), _selecciones[clave][1]))
        with st.container(key="compras_vap_drill_wrap"):
            _compras_vs_ano_pasado_drill(
                _d_sec(clave), col_prod, col_cant, col_fecha, col_valor,
                col_fam=col_fam, col_subfam=col_subfam, col_um=col_um,
                d_full=_hist_sec(clave), d_todas=todas, familias=_familias_de(clave))

    def _dib_volatilidad():
        clave = "compras_sec_volatilidad"
        with st.container(key="compras_vol_drill_wrap"):
            _compras_volatilidad_drill(
                _d_sec(clave), col_prod, col_prov, col_punit, col_fecha,
                col_valor, col_cant, col_um, col_moneda,
                d_full=_hist_sec(clave), col_docu=col_docu, col_fam=col_fam, col_subfam=col_subfam)

    def _dib_semanal():
        clave = "compras_sec_semanal"
        notas = recortar_filtros_vista(data.notas_restadas_compras(), col_fam, col_subfam, _selecciones[clave])
        if notas is not None and not notas.empty:
            notas = recortar_por_tarjeta(notas, col_fecha, CATEGORIA_SEC[clave])
        _compras_semanal_drill(
            _d_sec(clave), col_prod, col_fecha, col_cant, col_punit, col_prov, col_docu,
            col_valor, col_fam=col_fam, d_full=_hist_sec(clave), col_subfam=col_subfam,
            col_igv=col_igv, col_tipo_doc=col_tipo_doc, col_moneda=col_moneda,
            d_nc=notas, col_um=col_um, familias=_familias_de(clave))

    def _dib_tabla():
        from tablas import renderizar_aggrid_compras as _render_tabla_compras
        from estilos import TAM_FUENTE

        with st.container(key="tabla_fila_hdr"):
            op_tab = periodo.selector("compras_tabla_periodo", default="Todo", widget="lista")
        d_tab = periodo.recortar(_d_sec("compras_sec_tabla"), col_fecha, op_tab)
        font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam", "Mediano"), 14)
        _render_tabla_compras(d_tab, font_px)

    def _dib_documentos():
        clave = "compras_sec_documentos"
        # El detalle de un comprobante conserva las líneas de otras familias.
        todas = recortar_filtros_vista(_ops_src, col_fam, col_subfam, ((), _selecciones[clave][1]))
        with st.container(key="compras_docs_wrap"):
            _docs_seccion(
                _d_sec(clave), col_prov, col_prod, col_cant, col_valor,
                col_punit, col_um, col_fecha, col_docu,
                extra=dict(fam=col_fam, igv=col_igv, tipo=col_tipo_doc,
                           proc=_resolver(_ops_src, ["Fecha_proceso_doc", "Fecha proceso doc"]),
                           nc=_resolver(_ops_src, ["Valor_nc", "Valor nc"])),
                d_historia=todas, familias=_familias_de(clave))

    _DIBUJANTES = {
        "compras_sec_proveedor":     _dib_proveedor,
        "compras_sec_producto":      _dib_producto,
        "compras_sec_vs_ano_pasado": _dib_vs_ano_pasado,
        "compras_sec_volatilidad":   _dib_volatilidad,
        "compras_sec_semanal":       _dib_semanal,
        "compras_sec_tabla":         _dib_tabla,
        "compras_sec_documentos":    _dib_documentos,
    }

    def _dibujar_vista(clave):
        if not _op_fam:
            _DIBUJANTES[clave]()
            return
        actual = preparar_filtros_vista(clave, _op_fam, _mapa_sub, _FAMILIAS_DE_ENTRADA)
        if actual != _selecciones[clave]:
            # El cambio llega al fragmento de una tarjeta. El rail y su
            # histórico se vuelven a calcular con esa selección en la app.
            st.rerun(scope="app")
        slug = clave.removeprefix("compras_sec_")
        with st.container(key=f"cp_con_filtro_{slug}", gap=None):
            panel_filtros_vista(clave, _op_fam, _mapa_sub)
            _DIBUJANTES[clave]()

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje. Si llevara la key el fragment, cada
    # activación reemplazaría el nodo observado y los dos observadores se
    # quedarían mirando un elemento que ya no está en el documento.
    # ── MODO SOLO: una sección se queda con la página ────────────────────
    # `compras_pila_solo` guarda la clave de UNA sección; mientras esté
    # puesta, las otras cinco no se dibujan. Lo escribe el ⛶ de la cabecera
    # de la tarjeta (hoy sólo «Vs año pasado», ver su `vap_hdr_solo`).
    #
    # Por qué esto y no el ⛶ nativo de Streamlit: el nativo maximiza un
    # ELEMENTO (la figura, la tabla), y en «Vs año pasado» la información
    # completa es la TARJETA — cabecera con métrica/ventana/agrupador,
    # serie mensual, puente y tabla de detalle, que además se enfocan entre
    # sí (`compras_vap_foco`). Acá sección ≡ wrap, uno a uno, así que
    # filtrar el bucle ya es "maximizar la vista" sin inventar ninguna
    # unidad nueva. (Hasta el 2026-09-14 el wrap era además UNA tarjeta;
    # desde entonces son cuatro, #420, y el ⛶ se las lleva a las cuatro.)
    #
    # Lo que gana es ANCHO, no alto: la tarjeta ya está clampeada a
    # `--alto-util` y ocupa casi una pantalla, pero se parte en dos con
    # `COLUMNAS_DRILL` y vive en 867px de los 1280 del viewport porque el
    # contenido le reserva `--rail-der-res` (323px) al rail. Sin rail, ese
    # padding se suelta: ver las reglas de `estilos/_20_compras_rail.py`
    # que cuelgan de `.st-key-compras_solo_on`.
    #
    # El marcador va en `display: none` A PROPÓSITO (misma regla): un
    # `st.container` vacío sigue siendo un flex item de alto cero y se
    # cobraría el `gap: 16px` del contenedor — el mismo hueco fantasma que
    # documenta el -104px de `compras_prov_drill_wrap`. Con `display: none`
    # sale del layout y `:has()` lo sigue matcheando igual.
    _solo = st.session_state.get("compras_pila_solo")
    if _solo not in _DIBUJANTES:
        # Valor viejo de otra sesión, o de una sección que ya no existe.
        _solo = None
        st.session_state.pop("compras_pila_solo", None)
    if _solo:
        # EL MARCADOR NECESITA UN HIJO, y esto no es cosmético: un
        # `st.container(key=…)` VACÍO se dibuja la primera vez y DESAPARECE
        # del DOM en el render siguiente (Streamlit poda el bloque que no
        # tiene contenido). Medido en Cloud el 2026-09-04, muestreando cada
        # 3s después del clic en el ⛶:
        #
        #     +3s   marcador sí · tarjeta 1100px · --rail-der-res 90px
        #     +6s   marcador NO · tarjeta  867px · --rail-der-res 323px
        #
        # …con la pila ya filtrada a UNA sección en los dos momentos. O sea
        # que el modo entraba bien y lo que volvía atrás era sólo el CSS,
        # que cuelga entero de `:has(.st-key-compras_solo_on)`. Se veía como
        # "maximiza y se vuelve a achicar solo".
        with st.container(key="compras_solo_on"):
            st.markdown("<span></span>", unsafe_allow_html=True)
    _secciones = [_s for _s in _PILA if _s[0] == _solo] if _solo else _PILA

    for _i, (_clave, _vista) in enumerate(_secciones):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, lambda clave=_clave: _dibujar_vista(clave),
                             activa_de_entrada=(_i == 0))
