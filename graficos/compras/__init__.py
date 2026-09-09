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
    _resolver, publicar_contexto_ia, recortar_por_tarjeta,
    sembrar_seleccion, seccion_perezosa,
    renderizar_graficos_genericos, vista_activa,
)
from graficos.compras._comun import (  # noqa: F401  (re-export)
    # `CATEGORIA_SEC` la consumen los cinco drills Y este dispatcher; se
    # reexporta acá porque su sitio natural de lectura es al lado de `_PILA`
    # (sus claves son las de esa tupla) aunque viva en `_comun` por el ciclo
    # de imports. `test_graficos.py` verifica que sigan apareadas.
    CATEGORIA_SEC, _es_movil, _first_point, _periodo_serie,
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


def _kpis_vistas(df_de_vista, d_full, col_valor, col_prov, col_fam, col_prod,
                 col_punit, col_docu, col_fecha):
    """`({id_vista: texto}, {id_vista: estado})` para `_render_rail`.

    El segundo dict es el SEMAFORO (2026-09-07, a pedido: "mas KPI"). Es
    lo unico del KPI que sobrevive al riel PLEGADO —en 46px no entra un
    numero, pero si un punto de color— asi que responde de un vistazo la
    pregunta que importa con la columna cerrada: hay algo que mirar?

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

    `d_full` es el mismo df SIN el filtro de fecha: de ahi sale el PERIODO
    ANTERIOR con el que se comparan los KPIs. Sin el no habria flecha — el
    df de una vista es exactamente su rango vigente y no tiene con que
    compararse.
    """
    kpis, estados = {}, {}

    def _prev_de(dv):
        """El periodo ANTERIOR de `dv`: mismo largo, pegado por atras.

        Se deriva del PROPIO `dv` y no del contexto de la franja: asi la
        comparacion sigue al rango que tenga puesto ESA tarjeta, sin que
        este helper sepa de donde salio.
        """
        if not (col_fecha and dv is not None and col_fecha in dv.columns
                and d_full is not None):
            return None
        _f = pd.to_datetime(dv[col_fecha], errors="coerce").dropna()
        if not len(_f):
            return None
        _ini, _fin = _f.min(), _f.max()
        _largo = _fin - _ini
        _ff = pd.to_datetime(d_full[col_fecha], errors="coerce")
        prev = d_full[(_ff >= _ini - _largo - pd.Timedelta(days=1))
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
        return dv, pd.to_numeric(dv[col_valor], errors="coerce"), _prev_de(dv)

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

    def _texto(valor, delta):
        """`:blue[valor] :red[▲12%]` — dos colores a proposito: el dato en
        azul, que lo separa del lavanda del nombre de la vista (fue el
        pedido), y la variacion en verde/rojo por signo."""
        _t = f":blue[{valor}]"
        if delta:
            _t += f" :{delta[2]}[{delta[0]}{delta[1]}]"
        return _t

    # PROVEEDOR: el que mas compro, contra lo que ESE MISMO compro antes.
    d_v, val, prev = _vista("Proveedor")
    _t = _top(d_v, val, col_prov)
    if _t:
        kpis["Proveedor"] = _texto(
            f"{_inic(_t[0])} {fmt_k(_t[1])}",
            _delta(_t[1], _suma(prev, col_prov, _t[0])))

    # PRODUCTO: la familia que mas compro, contra esa misma familia antes.
    d_v, val, prev = _vista("Producto")
    _t = _top(d_v, val, col_fam)
    if _t:
        kpis["Producto"] = _texto(
            f"{str(_t[0])[:3].upper()} {fmt_k(_t[1])}",
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
            _txt_vol = f"{_compras_truncar(str(_p), 14)} ±{cv[_p] * 100:.0f}%"
            if _n_alta > 1:
                _txt_vol += f" · {_n_alta} altos"
                estados["Volatilidad"] = "warning"
            kpis["Volatilidad"] = _texto(_txt_vol, None)

    # DOCUMENTOS: cuantos en el SISTEMA y cuantos en SUNAT (2026-09-01, a
    # pedido). El del sistema sale de aca, que es barato. El de SUNAT no:
    # exige la consulta al SIRE, que hace la propia vista con su rango. Se
    # lo pide prestado por `session_state` —lo publica `documentos_sunat.py`
    # cuando dibuja— asi que aparece recien cuando esa vista se abrio una
    # vez. Preferible eso a disparar una consulta externa para decorar un
    # rotulo de navegacion.
    d_v, val, prev = _vista("Documentos SUNAT")
    if d_v is not None and col_docu and col_docu in d_v.columns:
        _n_sis = int(d_v[col_docu].nunique())
        _cruce = st.session_state.get("_cp_docs_cruce") or {}
        _txt = f"sis {_n_sis:,}".replace(",", ".")
        if _cruce.get("sunat") is not None:
            _txt += f" · sun {_cruce['sunat']:,}".replace(",", ".")
        # Lo que NO cuadra, que es lo unico accionable de esta vista.
        # Viaja por `session_state` desde `documentos_sunat.py` igual que
        # los dos totales de arriba, y por el mismo motivo: el lado SUNAT
        # sale de la consulta al SIRE y el rail no puede dispararla para
        # decorar un rotulo. Hasta que Documentos se abra una vez, no
        # esta — y no estar es correcto: mejor sin numero que con uno
        # inventado.
        _n_rev = _cruce.get("revisar")
        if _n_rev:
            _txt += f" · {_n_rev} a revisar"
            estados["Documentos SUNAT"] = "warning"
        _prev_docs = (int(prev[col_docu].nunique())
                      if prev is not None and col_docu in prev.columns else None)
        kpis["Documentos SUNAT"] = _texto(_txt, _delta(_n_sis, _prev_docs))

    # SEMANAL: la mejor semana del rango, contra la mejor de antes.
    d_v, val, prev = _vista("Semanal")
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
                    f":blue[{str(_ft)[:3].upper()}] "
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
    return kpis, estados


_COMPRAS_RAIL_CATEGORIAS = (
    ("Dimensión", (("Proveedor",        "Proveedor",     ":material/local_shipping:"),
                   ("Producto",         "Producto",      ":material/inventory_2:"))),
    ("Precios",   (("Vs año pasado",    "Vs año pasado", ":material/compare_arrows:"),
                   ("Volatilidad",      "Volatilidad",   ":material/candlestick_chart:"))),
    ("SUNAT",     (("Documentos SUNAT", "Documentos",    ":material/receipt_long:"),)),
    ("Más",       (("Semanal",          "Semanal",       ":material/calendar_view_week:"),
                   ("Tabla",            "Tabla",         ":material/table_rows:"),
                   # El rótulo corto dice «Documentos» a secas y el largo
                   # aclara de qué: en el riel plegado no entra más, y
                   # «Documentos SUNAT» ya se llama así dos grupos más
                   # arriba. Se distinguen por el ícono y por el grupo.
                   ("Documentos por proveedor", "Detalle docs.",
                    ":material/list_alt:"))),
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
#
# 2026-09-09, a pedido («bajemos Detalle de documentos por proveedor»):
# `compras_sec_documentos` entra al FINAL. No es una vista nueva — es la
# tarjeta que cerraba la sección Proveedor, que ahora tiene sitio y botón
# propios. Comparte el rango de Proveedor por `CATEGORIA_SEC`, así que sigue
# hablando del mismo período que el ranking del que sale.
_PILA = (
    ("compras_sec_proveedor",     "Proveedor"),
    ("compras_sec_producto",      "Producto"),
    ("compras_sec_vs_ano_pasado", "Vs año pasado"),
    ("compras_sec_volatilidad",   "Volatilidad"),
    ("compras_sec_semanal",       "Semanal"),
    ("compras_sec_tabla",         "Tabla"),
    ("compras_sec_documentos",    "Documentos por proveedor"),
)

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
# todos queda en cero y NO se vuelven a sembrar.
#
# Efecto lateral medido y aceptado: con Familia elegida la cascada de
# Subfamilia ya no está vacía al abrir — son 33 de las 95 del histórico,
# 428px, o sea el panel de 420 justo. Los 95 que la cascada exigente vino a
# evitar eran 1.688px.
_FAMILIAS_DE_ENTRADA = ("ALIMENTOS", "BEBIDAS CON ALCOHOL",
                        "BEBIDAS SIN ALCOHOL", "VINOS Y ESPUMANTES",
                        "ENVASES Y EMBALAJES")


def bounds_fecha_de_la_vista():
    """`(min, max)` que la vista activa necesita en el calendario, o None.

    La consulta `app.py` antes de sembrar/recortar el rango. Devuelve None
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
    # De entrada, las cuatro familias del negocio (ver _FAMILIAS_DE_ENTRADA).
    sembrar_seleccion(_ops_src, col_fam, "compras_graf_filtro_fam",
                      _FAMILIAS_DE_ENTRADA)
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

    # Data SIN filtro de fecha (para el toggle "Todo el histórico" del Panel B
    # del drill Proveedor). Se le aplican los mismos chips Familia/Subfamilia,
    # que no son de fecha. Si no llega df_full, cae a df_f (mismo comportamiento).
    d_full = df_full if df_full is not None else df_f
    if fam_sel and col_fam and col_fam in d_full.columns:
        d_full = d_full[d_full[col_fam].astype(str).isin(fam_sel)]
    if sub_sel and col_subfam and col_subfam in d_full.columns:
        d_full = d_full[d_full[col_subfam].astype(str).isin(sub_sel)]

    # ── EL `d` DE CADA SECCIÓN ────────────────────────────────────────────
    # Desde el 2026-09-08 cada sección de la pila tiene su propio rango de
    # fecha (ver `CATEGORIA_SEC`), así que ya no hay UN `d` para todos.
    #
    # EL RECORTE PASA ACÁ Y NO ADENTRO DE CADA DRILL, y eso es lo que hizo
    # barato el cambio: los cinco drills reciben un `d` y lo usan en cientos
    # de líneas cada uno. Cambiándoles la FUENTE —de "el df que ya filtró
    # `app.py`" a "el df del rango de esta tarjeta"— siguen recibiendo
    # exactamente lo que esperan y no hubo que tocarles el cuerpo.
    # `proveedor.py` solo son 1.786 líneas.
    #
    # Se parte de `d_full` (chips SÍ, fecha NO) y no de `d` (chips + rango
    # canónico): recortar sobre `d` sería una INTERSECCIÓN de dos rangos, o
    # sea que una tarjeta nunca podría ampliar más allá de lo que dejó pasar
    # `app.py`. Ese techo invisible es justo lo que hoy le pasa a la sección
    # Tabla con su propio selector de período.
    #
    # Una sección SIN categoría (Vs año pasado, Tabla) se queda con `d`, el
    # de siempre: su control de fecha es el desplegable de
    # `graficos/periodo.py`, que ya era por tarjeta.
    _cache_sec = {}

    def _d_sec(clave_sec):
        """El `d` de una sección, memoizado por render.

        La memoización no es prematura: `_kpis_vistas` pide el df de las
        seis vistas y después cada `seccion_perezosa` vuelve a pedir el
        suyo, así que sin caché el mismo recorte corre dos veces. Sobre
        `d_full` (~44k filas) cada uno cuesta unos 16 ms.
        """
        _cat = CATEGORIA_SEC.get(clave_sec)
        if not _cat:
            return d
        if _cat not in _cache_sec:
            _cache_sec[_cat] = recortar_por_tarjeta(d_full, col_fecha, _cat)
        return _cache_sec[_cat]

    # Vista del rail → sección de la pila. Sale de `_PILA`, que es la que ya
    # aparea las dos cosas: una tabla aparte se desincronizaría.
    _SEC_DE_VISTA = {_vista: _clave for _clave, _vista in _PILA}

    def _df_de_vista(nombre):
        """El df de una VISTA del rail, para su KPI.

        «Documentos SUNAT» no está en `_PILA` (es un destino aparte, fuera
        de la pila) así que cae a `d`, que es lo que usaba antes — su rango
        propio es el pill que dibuja adentro de su tarjeta.
        """
        return _d_sec(_SEC_DE_VISTA.get(nombre))

    _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)

    opciones = ["Proveedor", "Producto", "Vs año pasado", "Volatilidad",
                "Documentos SUNAT", "Semanal", "Tabla",
                "Documentos por proveedor"]

    # Rail vertical fijo al borde DERECHO (componente compartido _render_rail):
    # selector de tipo de gráfico agrupado por categoría. El activo se marca
    # con type="primary"; la selección se persiste en compras_graf_tipo.
    # `secciones`: la pila de esta página. Con eso el rail vertical de la
    # izquierda sabe qué botón encender según lo que haya en pantalla, y
    # aparece a partir de la segunda sección. Ver `base.py::_render_rail`.
    _kpis_rail, _estados_rail = _kpis_vistas(_df_de_vista, d_full, col_valor,
                                             col_prov, col_fam, col_prod,
                                             col_punit, col_docu, col_fecha)
    graf = _render_rail(_COMPRAS_RAIL_CATEGORIAS, "compras_graf_tipo",
                        secciones=_PILA,
                        kpis=_kpis_rail, estados=_estados_rail)
    if graf not in opciones:
        graf = opciones[0]

    # ── Quien dibuja el selector de fecha ────────────────────────────────
    # ACA VIVIA UNA RECONCILIACION, y se fue el 2026-09-06 con el
    # calendario de la franja. Existia porque la franja de `app.py` se
    # dibuja mucho antes que este rail y `_render_contenido` es un
    # `@st.fragment`: un clic aca NO re-ejecuta `app.py`, asi que en ese
    # rerun parcial la franja seguia con la decision de la vista ANTERIOR
    # —entrando a SUNAT, dos widgets con la misma key; saliendo, ninguno—
    # y habia que forzar un rerun completo al cruzar esa frontera.
    #
    # Sin fecha en la franja de Compras no hay frontera que cruzar: el
    # unico que puede dibujar el pill es Documentos SUNAT, y lo dibuja
    # dentro de su propia tarjeta. Que la negociacion desaparezca —en vez
    # de quedar con un lado fijo en `False`— es lo que evita el bucle: la
    # condicion vieja era "los dos coinciden", y con la franja SIEMPRE en
    # `False` cualquier vista que no fuera SUNAT la cumplia en cada render.

    # Tabla: usa el mismo AgGrid de la vista Tabla, pero como una opción más
    # del selector. `d` ya viene filtrado por los chips Familia/Subfamilia.
    # ── Vistas que siguen siendo un DESTINO propio ───────────────────────
    # Una excepción a la pila de abajo: Documentos SUNAT dibuja el pill de
    # fecha completo (`franja_fecha.render()`, la misma función que llamaba
    # `app.py`), y es la única del reporte que lo hace. Entra a la pila
    # cuando tenga rango propio; hasta entonces sigue siendo un destino
    # aparte, porque dos widgets con esa key son una excepción.
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

    # ── SIN FILAS TRAS LOS CHIPS: un CARTEL, no una salida ───────────────
    # Desde el 2026-09-02 este cartel es alcanzable a propósito: las
    # opciones de Familia/Subfamilia salen del histórico, así que se puede
    # elegir una que no compró nada en el rango de la píldora. Por eso el
    # texto nombra a los DOS filtros y no sólo "los filtros".
    #
    # TRES ACTOS DE LA MISMA GUARDA, y conviene leerlos juntos:
    #
    #   1. Vivía ARRIBA DE TODO. Cortar antes del rail apagaba la pantalla
    #      ENTERA y se llevaba puesta a «Documentos SUNAT», que no mira `d`
    #      (recibe `df_full` para que los chips no la toquen, regla #301):
    #      61 comprobantes esperando y la página en blanco. Regla #329.
    #   2. Bajó hasta acá (2026-09-06) y dejó el rail vivo… pero seguía
    #      terminando en `return`, o sea que se llevaba LA PILA ENTERA.
    #   3. 2026-09-07, reportado con captura desde la vista Semanal: el
    #      `return` ya no está. Dos motivos medidos, no de gusto:
    #
    #      · DOS de las seis secciones NO dependen de `d`. «Vs año pasado»
    #        (ventana propia, abre en "Todo") y «Volatilidad» (abre en 12
    #        meses) calculan sobre `d_full` — con el rango vacío siguen
    #        mostrando el histórico entero. Apagarlas era la #329 otra vez,
    #        un piso más abajo.
    #      · Y sobre todo: LA SALIDA ESTABA ADENTRO DE LO QUE SE APAGABA.
    #        Desde que la franja no tiene calendario (2026-09-06) el único
    #        control de rango son los selectores de fecha de las CABECERAS
    #        de las tarjetas. Sin pila no hay cabeceras, así que el cartel
    #        decía "ampliá el rango desde cualquier tarjeta" con la pantalla
    #        vacía detrás: un callejón sin salida del que sólo se volvía
    #        soltando el filtro de Familia a ciegas. Ver regla #354.
    #
    # Lo que hay debajo tolera un `d` vacío — se verificó sección por
    # sección en el navegador. Y el CARTEL TAMBIÉN SE FUE DE ACÁ: ahora lo
    # dibuja cada sección DENTRO de su tarjeta, junto al selector de fecha
    # de la cabecera, que es el control con el que se arregla.
    #
    # No es sólo prolijidad: un `st.info` suelto arriba de la pila NO CABE.
    # El jalón de `-104px` que sube la primera tarjeta bajo la franja
    # (`estilos/_20_compras_rail.py`) está medido contra los CINCO bloques
    # de alto cero que hay entre el borde del contenedor y esa tarjeta; un
    # sexto bloque con alto de verdad se lo come el jalón y el cartel sale
    # ENCIMA de la tarjeta. Medido en el navegador el 2026-09-07, con el
    # cartel pisando el título "Ranking de proveedores".

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
                _compras_proveedor_drill(_d_sec("compras_sec_proveedor"),
                                         col_prov, col_prod, col_cant, col_valor,
                                         col_punit, col_um, col_fecha, col_docu,
                                         d_full=d_full)

    def _dib_producto():
            with st.container(key="compras_prod_drill_wrap"):
                _compras_producto_drill(_d_sec("compras_sec_producto"),
                                        col_prod, col_fam, col_valor, col_cant,
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
                _compras_volatilidad_drill(_d_sec("compras_sec_volatilidad"),
                                           col_prod, col_prov, col_punit, col_fecha,
                                           col_valor, col_cant, col_um, col_moneda,
                                           d_full=d_full)

    def _dib_semanal():
            # Drill "Semanal": una barra por período + el detalle del
            # período en foco. Vive en su propio módulo Y en su propio
            # `@st.fragment` — ver el docstring de `semanal.py`, que
            # explica por qué el fragment de `seccion_perezosa` no
            # alcanzaba desde que la tarjeta tiene selector de fecha.
            #
            # `col_fam` y `d_full` son de sus dos filtros propios
            # (2026-09-08): la tarjeta acota por Familia y por Producto
            # encima de los chips de la franja. `d_full` es sólo para las
            # OPCIONES del selector de familia — sacarlas del rango las
            # hace desaparecer al angostar la fecha, y Streamlit borra la
            # selección en silencio (el bug medido del bloque de chips, más
            # arriba). Los datos que se grafican siguen saliendo de `d`.
            _compras_semanal_drill(_d_sec("compras_sec_semanal"),
                                   col_prod, col_fecha, col_cant,
                                   col_punit, col_prov, col_docu,
                                   col_valor, col_fam=col_fam,
                                   d_full=d_full)

    def _dib_tabla():
            # Cierra la página con el detalle: el mismo AgGrid de la vista
            # Tabla. `d` ya viene filtrado por los chips Familia/Subfamilia.
            from tablas import renderizar_aggrid_compras as _render_tabla_compras
            from estilos import TAM_FUENTE

            # ── LA ÚNICA VISTA CUYO COSTO CRECE CON LAS FILAS ────────────
            # Desde que Compras abre en todo el histórico (2026-09-06, al
            # sacarle el calendario a la franja) ésta es la sección que hay
            # que poder acotar, y la única que no tenía con qué. Los
            # gráficos agregan —un top-10 sobre 43.827 filas dibuja las
            # mismas 10 barras que sobre 1.083, y el groupby cuesta 15 ms—,
            # pero la tabla MANDA CADA FILA al navegador. Medido contra el
            # parquet real, con las cinco familias que vienen marcadas:
            #
            #     un mes    1.083 filas  ->   0,94 MB
            #     12 meses 11.324 filas  ->   9,76 MB
            #     todo     43.827 filas  ->  37,81 MB   (4,8 s de serializar)
            #
            # El default sigue siendo "Todo", que es lo que se pidió: la
            # tabla de detalle muestra el detalle. Lo que agrega el selector
            # es la salida — y se paga sólo al llegar acá, porque la pila
            # es perezosa y esta sección no se construye hasta que uno baja
            # (`seccion_perezosa`, regla #211). Desde el 2026-09-09 ya no es
            # la última: debajo va «Documentos por proveedor».
            with st.container(key="tabla_fila_hdr"):
                _op_tab = periodo.selector("compras_tabla_periodo",
                                           default="Todo", widget="lista")
            _d_tab = periodo.recortar(d, col_fecha, _op_tab)
            _font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam", "Mediano"), 14)
            _render_tabla_compras(_d_tab, _font_px)

    def _dib_documentos():
            # «Detalle de documentos por proveedor». Era la última fila del
            # drill de Proveedor hasta el 2026-09-09; hoy cierra la página.
            #
            # Recibe el `d` de la categoría `sec_proveedor` —la MISMA que el
            # ranking del que sale— y no uno propio: ver `CATEGORIA_SEC`.
            # `_d_sec` memoiza por categoría, así que este recorte ya está
            # hecho y no se paga dos veces.
            with st.container(key="compras_docs_wrap"):
                _docs_seccion(_d_sec("compras_sec_documentos"),
                              col_prov, col_prod, col_cant, col_valor,
                              col_punit, col_um, col_fecha, col_docu)

    _DIBUJANTES = {
        "compras_sec_proveedor":     _dib_proveedor,
        "compras_sec_producto":      _dib_producto,
        "compras_sec_vs_ano_pasado": _dib_vs_ano_pasado,
        "compras_sec_volatilidad":   _dib_volatilidad,
        "compras_sec_semanal":       _dib_semanal,
        "compras_sec_tabla":         _dib_tabla,
        "compras_sec_documentos":    _dib_documentos,
    }

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
    # sí (`compras_vap_foco`). Acá sección ≡ wrap ≡ tarjeta, uno a uno, así
    # que filtrar el bucle ya es "maximizar la tarjeta" sin inventar
    # ninguna unidad nueva.
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
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
