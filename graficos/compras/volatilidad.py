"""graficos.compras.volatilidad - drill de Volatilidad de insumos.

Ranking de insumos por volatilidad de precio de compra semana a semana,
con drill a un candlestick (una vela = una semana: apertura/máximo/
mínimo/cierre de PRECIO_UNIT) y de ahí a las compras puntuales que
formaron la semana clickeada.

Semáforo de precio: como el dato es un COSTO (no una ganancia), "sube" es
malo (rojo, ERROR) y "baja" es bueno (verde, EXITO) — al revés de la
convención bursátil, a propósito.

`go.Candlestick` no tiene precedente de selección por clic en este
proyecto (a diferencia de go.Bar, que Proveedor ya usa con éxito). Se
asume NO seleccionable de forma confiable, igual que go.Heatmap (regla
#11) y go.Histogram (regla #44): se agrega una traza go.Scatter invisible
(un punto por semana) para capturar el clic, y se ignoran los eventos que
lleguen del candlestick mismo.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cortes import MESES_ABR_ES
from tema import ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO
from graficos.base import (
    _card, _compras_layout, _compras_truncar, _slug,
    preservar_widgets, selector_fecha_tarjeta,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras._comun import (
    CATEGORIA_SEC, GAP_DRILL, PARR, _first_point,
)
from graficos import periodo
from graficos import alturas
from tablas.compras_volatilidad import (
    ALTO_FILA as ALTO_FILA_RANK, CROMO_GRID as CROMO_GRID_VOL,
    renderizar_ranking_volatilidad,
)

_K_VENTANA = "compras_vol_ventana"
"""Dueño de la ventana propia (`graficos/periodo.py`), y NO es clave de widget.

El `selectbox` que la muestra lleva este valor DENTRO de su key
(`compras_vol_periodo_<valor>`), así que cuando la ventana cambia por
afuera —hoy: tocar el segmentador de fecha de la misma cabecera— el widget
que se dibuja es OTRO y nace con su `index` en el valor nuevo. Escribir la
clave del widget no alcanza: el navegador vuelve a mandar el valor viejo y
Streamlit lo re-aplica (arquitectura.md regla #212, medida otra vez acá el
2026-09-06). El espíritu de "sin key dinámica" se respeta igual, con el
mismo argumento que `selector_escala`: el dueño del dato es esta clave, y
el widget es una VISTA que se recalcula de ella en cada render."""

_KEYS_WIDGET = ("compras_vol_q", "compras_vol_ver")
"""Los controles de esta sección que la escalada NO puede llevarse.

La consume `preservar_widgets` en el `st.rerun(scope="app")` de más abajo:
ese rerun aborta la corrida antes de dibujarlos y Streamlit recolecta lo
que no se dibujó, así que sin esto mover la fecha borraba lo escrito en el
buscador de insumos. Ver `graficos/base.py::preservar_widgets` y
`arquitectura.md` regla #373.

La ventana propia NO está en la lista, y eso es lo contrario de un olvido:
esa misma escalada la manda a `HEREDA` a propósito (ver más abajo), y su
dueño es `_K_VENTANA`, que no es clave de widget. El foco del ranking
tampoco: vive en `compras_vol_focus`, por el mismo motivo."""

MIN_SEMANAS = 4          # con menos, un candlestick no dice nada
MAX_SEMANAS = 5
"""Semanas que MIDE el puntaje (y dibuja el candlestick): las 5 más recientes,
o sea 4 variaciones. Desde el 2026-09-12 NO son las que muestra la grilla,
que recorre toda la ventana de la tarjeta hacia atrás; la columna
«Volatilidad» lleva escrito el período para que eso no se lea mal.

Nació como tope de la ventana entera, y NO era un gusto: era el ancho de la
celda.

8 -> 5 el 2026-09-07, a pedido — *"deseo que muestre menos días, no se ve el
precio inicial y el precio final"*. La segunda línea de cada celda (los dos
cierres, «110.17 → 169.41») necesita 81px de columna: 69 del peor caso real
más 12 de cromo. Con el ranking en la columna izquierda de la fila, la
grilla recibe 587px con el rail desplegado, y ahí sólo caben CUATRO columnas
de 81 (150 del insumo + 4x81 + 78 de volatilidad + 17 del scrollbar = 569).
Cuatro columnas de variación son cinco semanas, porque la primera es la
línea de base.

Así el precio inicial y el final se leen en la propia grilla: el `prev` de
la primera columna es el cierre con el que arranca la ventana y el `cur` de
la última, el cierre de hoy.

2026-09-12: la cuenta de ancho de arriba YA NO ATA este número. La grilla
pasó a ocupar el ancho entero de la tarjeta (el drill bajó a la fila de
abajo) y los precios pasaron al costado del %, a 120px por columna: en el
ancho completo entran más de cuatro. Se deja en 5 porque el pedido original
fue «que muestre menos días», no «que entren»; subirlo sería otro pedido, y
reordena el ranking (ver el párrafo de abajo).

Este número manda además sobre el candlestick (cinco velas) y sobre el
score de volatilidad, que es la suma de las variaciones DE LA VENTANA: con
cinco semanas los puntajes bajan y el ranking se reordena. Es consecuencia
del pedido, no un efecto colateral escondido."""
MIN_GASTO = 400.0        # S/ gastados en la ventana; filtra ruido de insumos
MIN_COBERTURA = 0.75     # % de semanas con al menos una compra


# ── Funciones puras (testeadas en test_graficos.py) ─────────────────────────

def _vol_semanas_ventana(fechas, minimo=MIN_SEMANAS, maximo=MAX_SEMANAS):
    """Lunes de cada semana con al menos una fecha en `fechas`, ordenados,
    recortado a las `maximo` MÁS RECIENTES. El rango de fecha lo elige el
    usuario en la franja (puede ser "Todo", años) pero el candlestick solo
    tiene sentido sobre una ventana corta y reciente — más semanas no es
    "más historia útil", es un gráfico ilegible y una volatilidad que
    mezcla huecos de años con movimiento real (ver arquitectura.md).
    None si hay menos de `minimo` semanas distintas en total.

    `maximo=None` no recorta: son TODAS las semanas de la ventana, que es lo
    que recorre la grilla al deslizar hacia atrás (2026-09-12)."""
    fechas = fechas.dropna()
    if fechas.empty:
        return None
    inicios = (fechas - pd.to_timedelta(fechas.dt.weekday, unit="D")).dt.normalize()
    semanas = sorted(pd.to_datetime(inicios.unique()))
    if len(semanas) < minimo:
        return None
    return semanas if maximo is None else semanas[-maximo:]


def _vol_cierres_semanales(d, prods, col_prod, col_punit, col_fecha, semanas):
    """Cierre (el último precio válido de la semana) de cada producto en cada
    una de `semanas`, con relleno hacia adelante en las semanas sin compra.
    Devuelve {producto: [cierre o None, ...]}, pareado con `semanas`; None
    sólo al principio, antes de la primera compra de la serie.

    Es la serie que dibuja la GRILLA y la que mide el puntaje, y tienen que
    ser la misma (2026-09-12). Con la historia a la vista, la primera semana
    de la ventana corta ya no arranca a ciegas: si no hubo compra, su cierre
    es el último precio conocido, de antes. Si el puntaje siguiera midiendo
    la ventana corta aislada, la grilla mostraría «+99%» en una celda que el
    número de «Volatilidad» no cuenta — la tabla contradiciéndose sola.

    EL CIERRE SE SACA IGUAL QUE EN `_vol_candidatos` Y EN EL CANDLESTICK:
    el subconjunto de la semana en su orden original, `sort_values` por
    fecha y `_vol_ohlc_semana`. No es un detalle. Con dos compras el MISMO
    día, «la última» depende del desempate del ordenamiento, y la primera
    versión de esta función (un `sort_values` sobre el DataFrame entero y
    un `groupby().last()`) desempataba distinto: «Cachema Entera» tiene el
    10 Ago una compra a 31.90 y otra a 3.19 —un punto decimal corrido, con
    toda probabilidad— y el cierre salía 3.19 donde la vela decía 31.90; el
    puntaje saltaba de 191.8 a 1659.1. Medido en el navegador, 2026-09-12.
    `groupby` conserva el orden de las filas dentro de cada grupo, así que
    cada semana llega al `sort_values` igual que por el filtro de siempre."""
    out = {p: [None] * len(semanas) for p in prods}
    pos = {s: i for i, s in enumerate(semanas)}
    sub = d[d[col_prod].isin(list(prods))]
    for p, g in sub.groupby(col_prod, sort=False):
        propios = {}
        for sem, gs in g.groupby("_semana", sort=False):
            if sem in pos:
                ohlc = _vol_ohlc_semana(gs.sort_values(col_fecha)[col_punit].tolist())
                if ohlc:
                    propios[pos[sem]] = ohlc["c"]
        prev, cierres = None, []
        for i in range(len(semanas)):
            if i in propios:
                prev = propios[i]
            cierres.append(prev)
        out[p] = cierres
    return out


def _vol_precio_previo(d, prod, col_prod, col_punit, col_fecha, col_moneda,
                       antes_de):
    """Último precio de compra válido de `prod` ANTES de `antes_de`, sobre el
    histórico entero (`d_full`), o None si no compró nunca antes.

    Es el respaldo de `cierre_previo` del candlestick cuando la ventana de la
    tarjeta no trae semanas anteriores — con «Rango», las semanas de la
    historia son sólo las del rango. Sin él, la primera vela de un insumo
    que no compró esa semana se dibujaba en S/ 0 y el eje bajaba a «S/ −10»
    (captura del usuario, 2026-09-12). Mismo filtro de moneda que el drill:
    un precio en dólares no puede ser la base de una serie en soles."""
    g = d[d[col_prod] == prod]
    if col_moneda and col_moneda in g.columns:
        g = g[g[col_moneda].astype(str).str.strip().isin(["01", "1"])]
    s = pd.DataFrame({"f": pd.to_datetime(g[col_fecha], errors="coerce"),
                      "p": pd.to_numeric(g[col_punit], errors="coerce")})
    s = s[(s["f"] < antes_de) & s["p"].notna() & (s["p"] > 0)]
    if s.empty:
        return None
    return float(s.sort_values("f")["p"].iloc[-1])


def _vol_ohlc_semana(precios_ordenados):
    """OHLC de una lista/Serie de precios YA ordenada por fecha ascendente.
    None si está vacía."""
    precios = [p for p in precios_ordenados if pd.notna(p) and p > 0]
    if not precios:
        return None
    return {"o": float(precios[0]), "c": float(precios[-1]),
            "h": float(max(precios)), "l": float(min(precios))}


def _vol_score(cierres):
    """Suma de variaciones % absolutas semana a semana. Ignora huecos (None)
    al principio de la serie (sin cierre previo del que partir)."""
    cierres = list(cierres)
    while cierres and cierres[0] is None:
        cierres = cierres[1:]
    total = 0.0
    for i in range(1, len(cierres)):
        prev, cur = cierres[i - 1], cierres[i]
        if prev and cur is not None:
            total += abs((cur - prev) / prev * 100)
    return round(total, 1)


_MESES_CORTO = tuple(m.capitalize() for m in MESES_ABR_ES)
"""Los meses de `cortes.py` con la inicial en mayúscula, que es como se
rotulan las columnas de esta grilla ("3-9 Ago").

Derivado y no escrito a mano: hasta el 2026-09-07 era una lista literal acá,
o sea la SEGUNDA lista de meses en español del repo — justo lo que la regla
#241 dice que no debe haber. La capitalización es lo único propio de esta
vista."""


def _vol_fmt_semana_cabecera(ini, anio_ref=None):
    """Rótulo de una semana en la grilla Y en el eje del candlestick: «17 Ago –
    23 Ago», el mes escrito en las DOS puntas aunque sea el mismo
    (2026-09-12, a pedido y sobre una maqueta: «17Ago-23Ago»).

    Reemplaza a `_vol_fmt_semana_corta` («10 Ago», sólo el lunes), que nació
    el 2026-09-07 cuando la columna medía ~50px y el rango entero envolvía
    en cuatro renglones. Con columnas de 120px dejó de hacer falta, y tener
    dos rótulos para la misma semana hizo que el usuario preguntara de dónde
    salía el «10 Ago» del gráfico si la tabla no tenía esa columna.

    Si la semana termina en un año que no es `anio_ref` (el de la semana más
    reciente) lleva el año corto: «8 Set – 14 Set ’25». Con la historia a la
    vista la grilla recorre más de un año, y sin eso dos columnas del mismo
    día y mes se leerían como la misma semana. Una semana que cruza al año de
    referencia («29 Dic – 4 Ene») no lo lleva: se lee sola.

    Mide ~95px a 11px en el peor caso, dentro de los 120 de la columna."""
    fin = ini + pd.Timedelta(days=6)
    txt = (f"{ini.day} {_MESES_CORTO[ini.month - 1]} – "
           f"{fin.day} {_MESES_CORTO[fin.month - 1]}")
    if anio_ref is not None and fin.year != anio_ref:
        txt += f" ’{fin.year % 100:02d}"
    return txt


def _vol_fmt_rango_semana(ini):
    """Etiqueta de columna para la semana que empieza el lunes `ini`:
    "15-21 Jun" si cae en un solo mes, "29 Jun - 5 Jul" si cruza de mes."""
    fin = ini + pd.Timedelta(days=6)
    m1, m2 = _MESES_CORTO[ini.month - 1], _MESES_CORTO[fin.month - 1]
    if ini.month == fin.month:
        return f"{ini.day}-{fin.day} {m1}"
    return f"{ini.day} {m1} - {fin.day} {m2}"


def _vol_candidatos(d, col_prod, col_punit, col_fecha, col_valor, semanas,
                    min_gasto=MIN_GASTO, min_cobertura=MIN_COBERTURA):
    """Cierres semanales (con relleno hacia adelante en huecos) por producto,
    solo para los que superan gasto y cobertura mínimos. Devuelve
    {producto: {"cierres": [...], "volatilidad": float}}, ordenable después
    por volatilidad."""
    out = {}
    for prod, g in d.groupby(col_prod):
        gasto = g[col_valor].sum()
        semanas_con_compra = g["_semana"].nunique()
        if gasto < min_gasto or semanas_con_compra < min_cobertura * len(semanas):
            continue
        cierres, prev = [], None
        for sem in semanas:
            sub = g[g["_semana"] == sem].sort_values(col_fecha)
            ohlc = _vol_ohlc_semana(sub[col_punit].tolist())
            c = ohlc["c"] if ohlc else prev
            cierres.append(c)
            if c is not None:
                prev = c
        out[prod] = {"cierres": cierres, "volatilidad": _vol_score(cierres)}
    return out


def _vol_detalle_producto(d, prod, col_prod, col_punit, col_fecha, col_prov,
                          col_cant, semanas, cierre_previo=None):
    """OHLC + filas de compra (fecha, proveedor, cantidad, precio) por
    semana, para UN producto ya elegido.

    `cierre_previo` es el último precio conocido ANTES de la primera de
    `semanas`. Sin él, una primera semana sin compras dibujaba una vela
    plana en S/ 0 —el eje bajaba a «S/ −10» para mostrarla— y el KPI
    «Cambio» se quedaba sin base. Llega de la misma serie que dibuja la
    grilla (`_vol_cierres_semanales`), 2026-09-12."""
    g = d[d[col_prod] == prod]
    weeks = []
    prev_close = cierre_previo
    for sem in semanas:
        sub = g[g["_semana"] == sem].sort_values(col_fecha)
        ohlc = _vol_ohlc_semana(sub[col_punit].tolist())
        rows = []
        for _, r in sub.iterrows():
            precio = r[col_punit]
            if pd.isna(precio) or precio <= 0:
                continue
            rows.append({
                "fecha": r[col_fecha],
                # NOMBRE PROPIO, no el grito del ERP (2026-09-07, a pedido).
                # Es SOLO para mostrar: esta tabla no agrupa ni filtra por
                # proveedor, así que no hay ningún valor canónico que se
                # pueda desalinear. Ver `_etiquetas_proveedor.nombre_propio`,
                # que es la unica desde el 2026-09-11 (arquitectura.md #379:
                # esta tarjeta importaba una copia que escribia distinto).
                "prov": nombre_propio(str(r[col_prov])) if col_prov else "—",
                "cant": r[col_cant] if col_cant else None,
                "precio": float(precio),
            })
        if ohlc is None:
            c = prev_close if prev_close is not None else 0.0
            ohlc = {"o": c, "h": c, "l": c, "c": c}
        weeks.append({**ohlc, "semana": sem, "rows": rows})
        prev_close = ohlc["c"]
    return weeks


# ── Vista principal ──────────────────────────────────────────────────────────

@st.fragment
def _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                               col_valor, col_cant, col_um, col_moneda=None,
                               d_full=None):
    """Ranking de insumos por volatilidad de precio → candlestick semanal
    del insumo elegido → compras de la semana clickeada.

    `col_moneda` es opcional (no resuelto en `__init__.py` hasta que este
    drill lo necesitó): si no llega o no está en `d`, no se filtra por
    moneda — mezclar monedas en una misma serie sería incorrecto, pero es
    preferible a que el drill no abra por falta de la columna (el demo
    local, por ejemplo, no la trae)."""
    if not (col_prod and col_punit and col_fecha and col_valor):
        st.info("Faltan columnas (Producto, Precio unitario, Fecha o Valor) "
                "para calcular volatilidad.")
        return

    # ── Escalada a rerun COMPLETO tras tocar el selector de fecha ────────
    # El filtro que consume el rango canónico vive en `app.py`, fuera de
    # este fragment: sin escalar, el estado cambia y la pantalla no. Mismo
    # mecanismo que `_cp_sem_atajo_pendiente` (semanal.py) y sus dos
    # gemelos de Proveedor/Producto — arquitectura.md #180.
    #
    # LO PROPIO DE ESTA TARJETA es la línea del medio: la ventana vuelve a
    # "Rango". Esta vista tiene DOS controles de fecha (ver más abajo) y
    # mientras la ventana propia mande, la tarjeta ignora la franja — o sea
    # que sin esto el gesto no se vería, que es peor que no tener el
    # control. Elegir un rango a mano ES pedir que mande ese rango.
    #
    # SE ESCRIBE EL DUEÑO, NO LA CLAVE DEL WIDGET, y eso costó una vuelta
    # medida en el navegador (2026-09-06): con `st.session_state[
    # "compras_vol_periodo"] = HEREDA` la píldora de la franja pasaba a
    # "1 ene – 24 ago 2026" —o sea, la escalada corría— y el desplegable
    # seguía marcando "12m". Es la regla #212 tal cual: el valor que manda
    # el NAVEGADOR le gana al que escribe el servidor, así que un widget no
    # se resetea desde `session_state`; hay que cambiarle la KEY. Por eso
    # `_K_VENTANA` es una clave normal (nadie la recolecta) y la key del
    # `selectbox` la lleva adentro, exactamente como el riel de
    # `base.py::selector_escala` lleva su rango.
    #
    # Y `preservar_widgets` por lo de siempre: el rerun aborta ACÁ, antes
    # de que los controles se registren, y Streamlit recolecta el estado de
    # todo widget de este fragment que no se dibujó (ver `_KEYS_WIDGET`).
    if st.session_state.pop("_cp_vol_atajo_pendiente", False):
        st.session_state[_K_VENTANA] = periodo.HEREDA
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")

    # ── VENTANA PROPIA DE ESTA TARJETA ───────────────────────────────────
    # A pedido (2026-08-26): "la visualización de volatilidad debería por
    # defecto mostrar la información del año, creo debería ponerle un
    # selector de fechas".
    #
    # El motivo es estructural, no de gusto: este drill necesita AL MENOS 4
    # semanas con compras para armar un candlestick, y el rango por defecto
    # de la franja son ~3 semanas — o sea que la vista abría en el mensaje
    # de "necesitás al menos 4 semanas" en vez de en un gráfico. Heredar un
    # rango pensado para un ranking no le sirve a una vista que mide
    # variación semana a semana.
    #
    # Se reusa `graficos/periodo.py`, el MISMO control que ya tiene la
    # tarjeta de Evolución (Rango / 3m / 12m / 24m / Todo): recorta sobre
    # `d_full` salteándose el filtro de fecha, salvo que se elija "Rango",
    # que vuelve a heredar la franja. Default 12m = "el año".
    #
    # El tope de `MAX_SEMANAS` sigue mandando: la ventana ancha no dibuja un
    # candlestick de un año, alimenta la elección de las 8 semanas más
    # recientes CON DATOS. Más velas no es más historia útil, es un gráfico
    # ilegible (ver `_vol_semanas_ventana`).

    with _card("compras_vol"):
        # ── LA TABLA ARRIBA A LA IZQUIERDA; TÍTULO Y CONTROLES, A SU DERECHA ─
        # 2026-09-12, a pedido y sobre una maqueta: «el título y los toggles
        # y selectores al lado derecho, y subamos la tabla». Hasta hoy eran
        # una FILA encima de la tabla (título a la izquierda, controles a la
        # derecha, raya debajo): 55px de cabecera medidos antes de la
        # primera fila de la grilla. Ahora la grilla arranca en el borde de
        # la tarjeta y el título con sus controles forman un panel angosto
        # a su derecha (`vol_panel`, 240px — `estilos/_80_cards.py`).
        #
        # Lo que cuesta, medido en la maqueta: con la ventana de 12 meses se
        # ven ~6 semanas de la grilla a la vez en vez de ~8. Se desliza, así
        # que no se pierde nada. Con una ventana corta no cuesta nada: las
        # columnas-semana se estiran hasta llenar.
        #
        # EL ORDEN DEL CÓDIGO NO ES EL DE LA PANTALLA, y es a propósito: el
        # hueco de la tabla se reserva PRIMERO (queda a la izquierda) pero
        # se llena al final, porque la tabla depende de lo que digan los
        # controles (la ventana recorta `d`, el buscador filtra filas).
        # Los mensajes de «no hay datos» van en ese mismo hueco: salen donde
        # iba la tabla, al lado de los controles con los que se arreglan.
        with st.container(key="vol_fila_top"):
            c_tabla = st.container(key="vol_tabla")
            with st.container(key="vol_panel"):
                st.markdown('<p class="chart-card-hdr vol-hdr">Insumos ordenados '
                            'por volatilidad</p>', unsafe_allow_html=True)

                # ── Ventana + fecha, en un renglón ───────────────────────
                # LOS DOS CONTROLES SON UNO SOLO, leídos de izquierda a
                # derecha: la ventana elige el GRANO ("últimos 12 meses") y
                # la fecha elige un rango EXACTO. Por eso el trigger no
                # muestra la fecha de la franja mientras la ventana mande
                # —mostraría un dato que esta tarjeta no está usando— sino la
                # ventana misma, y por eso tocar el panel devuelve la ventana
                # a "Rango" (arriba, en la escalada).
                #
                # El trigger es el MISMO componente que tienen los dos
                # rankings y la vista Semanal (`base.py::selector_fecha_tarjeta`):
                # no es un filtro paralelo, escribe la clave del rango de
                # esta sección (`categoria=`, regla #363).
                with st.container(key="vol_panel_f1"):
                    with st.container(key="vol_hdr_periodo"):
                        _prev_vol = st.session_state.get(_K_VENTANA, "12m")
                        if _prev_vol not in periodo.OPCIONES:
                            _prev_vol = "12m"
                        _op_vol = periodo.selector(
                            f"compras_vol_periodo_{_prev_vol}",
                            default=_prev_vol, widget="lista")
                    st.session_state[_K_VENTANA] = _op_vol
                    if _op_vol != periodo.HEREDA and d_full is not None:
                        d = periodo.recortar(d_full, col_fecha, _op_vol)
                    selector_fecha_tarjeta(
                        "cp_vol", "_cp_vol_atajo_pendiente",
                        label=(periodo.etiqueta(_op_vol).capitalize() or None
                               if _op_vol != periodo.HEREDA else None),
                        categoria=CATEGORIA_SEC["compras_sec_volatilidad"])

                # ── El buscador, a todo el ancho del panel ───────────────
                with st.container(key="vol_hdr_buscar"):
                    _q = st.text_input("Buscar insumo", key="compras_vol_q",
                                       placeholder="Buscar insumo…",
                                       label_visibility="collapsed").strip().lower()

                with st.container(key="vol_panel_f2"):
                    # ── La columna «Volatilidad», a pedido y no siempre ──
                    # 2026-09-12: «que la columna de volatilidad no figure
                    # siempre visible sino sea consultable». Arranca oculta;
                    # esta pastilla la prende y la apaga. Sin ella el puntaje
                    # sigue a mano en el tooltip del nombre del insumo, y el
                    # orden de la tabla no cambia.
                    #
                    # `st.pills` de UNA opción y no un `st.toggle`: se lee
                    # como un botón que queda marcado, que es lo que es. Va
                    # en `_KEYS_WIDGET` por lo de siempre (la escalada de
                    # fecha la borraría, #373).
                    with st.container(key="vol_hdr_ver"):
                        _ver_vol = st.pills(
                            "Mostrar", ["Volatilidad"], key="compras_vol_ver",
                            label_visibility="collapsed") == "Volatilidad"

                    # ── Cómo se lee la vista: un ícono, no dos captions ──
                    # Eran DOS `st.caption` EN FLUJO que sumaban ~83px para
                    # explicar algo que se lee UNA vez; pasaron a un popover
                    # de sólo ícono, exactamente como `vap_hdr_ayuda`.
                    #
                    # La primera línea (período y umbrales) va por un HUECO:
                    # el período se sabe más abajo, cuando ya se recortó `dd`
                    # a las semanas con datos.
                    #
                    # El párrafo de los DOS PRECIOS no es relleno: son
                    # cierres de semanas DISTINTAS —el de la anterior y el
                    # de ésta— y leerlos como si los dos fueran de la semana
                    # del encabezado es la confusión que reportó el usuario
                    # el 2026-09-07 con captura.
                    with st.container(key="vol_hdr_ayuda"):
                        with st.popover(":material/info:",
                                        use_container_width=False):
                            with st.container(key="vol_ayuda_panel"):
                                _ayuda_alcance = st.empty()
                                st.markdown(
                                    "**Volatilidad** = la suma de las "
                                    "variaciones % de una semana a la "
                                    "siguiente, en valor absoluto: mide "
                                    "cuánto se MUEVE el precio, no hacia "
                                    "dónde." + PARR
                                    + "Cada celda compara el **cierre** (la "
                                    "última compra) de esa semana contra el "
                                    "de la semana anterior, así que los dos "
                                    "precios al costado del % son de semanas "
                                    "DISTINTAS — el tooltip de la celda las "
                                    "nombra. El % va redondeado a entero; "
                                    "los precios, no. Las compras "
                                    "intermedias se ven abajo, en el "
                                    "candlestick y en su tabla."
                                    + PARR
                                    + "Deslizá la tabla hacia la izquierda "
                                    "(o usá ‹ › junto a «Insumo») para ver "
                                    "semanas anteriores: son historia, no "
                                    "entran en el puntaje, y el orden no "
                                    "cambia. Las que SÍ suman son las de "
                                    "título resaltado; la semana anterior a "
                                    "la primera de ellas es la base (la "
                                    "primera vela del gráfico). "
                                    "El botón **Volatilidad** "
                                    "muestra la columna del puntaje; sin "
                                    "ella, se consulta pasando el mouse "
                                    "sobre el nombre del insumo."
                                    + PARR
                                    + "Clic en una fila para ver su "
                                    "candlestick; clic en una vela, para "
                                    "las compras de esa semana.")

        dd = d.copy()
        if col_moneda and col_moneda in dd.columns:
            dd = dd[dd[col_moneda].astype(str).str.strip().isin(["01", "1"])]
        dd[col_fecha] = pd.to_datetime(dd[col_fecha], errors="coerce")
        dd[col_punit] = pd.to_numeric(dd[col_punit], errors="coerce")
        dd[col_valor] = pd.to_numeric(dd[col_valor], errors="coerce").fillna(0)
        dd = dd.dropna(subset=[col_fecha, col_prod])
        dd = dd[dd[col_prod].astype(str).str.strip() != ""]

        # ── DOS JUEGOS DE SEMANAS, Y NO SE MEZCLAN ───────────────────────
        # 2026-09-12, a pedido: «que la tabla se pueda deslizar en horizontal
        # para ver períodos de atrás». `semanas_hist` son TODAS las de la
        # ventana de la tarjeta (12m por defecto: 53) y es lo que recorre la
        # grilla; `semanas` son las `MAX_SEMANAS` más recientes, y es lo que
        # MIDEN el puntaje, el filtro de candidatos y el candlestick.
        #
        # Deslizar hacia atrás NO cambia el puntaje ni el orden, a propósito
        # y con el usuario: el deslizamiento pasa en el navegador —el
        # servidor no sabe qué semanas están a la vista— y un orden que se
        # reacomoda mientras se desliza pierde de vista la fila que uno
        # seguía. Medir la ventana entera se evaluó con datos reales y
        # responde otra pregunta: ninguno de los ocho primeros de hoy queda
        # entre los ocho primeros de 12 meses. Por eso la columna
        # «Volatilidad» lleva escrito el período que mide.
        semanas_hist = _vol_semanas_ventana(dd[col_fecha], maximo=None)
        if not semanas_hist:
            c_tabla.info(f"Necesitás al menos 4 semanas de compras en "
                    f"{periodo.etiqueta(_op_vol) or 'el rango elegido'} para "
                    f"armar un candlestick. Probá una ventana más amplia con el "
                    f"selector del título.")
            return
        semanas = semanas_hist[-MAX_SEMANAS:]
        dd["_semana"] = (dd[col_fecha] - pd.to_timedelta(
            dd[col_fecha].dt.weekday, unit="D")).dt.normalize()
        dd_rec = dd[dd["_semana"].isin(semanas)]

        candidatos = _vol_candidatos(dd_rec, col_prod, col_punit, col_fecha,
                                     col_valor, semanas)
        if not candidatos:
            c_tabla.info(f"Ningún insumo tiene compras regulares (≥75% de las "
                    f"semanas) y gasto relevante (≥ S/ 400) en "
                    f"{periodo.etiqueta(_op_vol) or 'el rango elegido'}.")
            return

        # El puntaje se mide sobre la MISMA serie que dibuja la grilla: la
        # de toda la ventana, recortada a sus últimas `MAX_SEMANAS`. Ver
        # `_vol_cierres_semanales` para lo que cambia (una primera semana
        # sin compra ya no arranca a ciegas).
        cierres_hist = _vol_cierres_semanales(dd, list(candidatos), col_prod,
                                              col_punit, col_fecha, semanas_hist)
        for prod, info in candidatos.items():
            info["cierres_hist"] = cierres_hist[prod]
            info["volatilidad"] = _vol_score(cierres_hist[prod][-len(semanas):])

        ranking = sorted(candidatos.items(), key=lambda kv: -kv[1]["volatilidad"])
        puesto = {p: k for k, (p, _) in enumerate(ranking, 1)}

        n_sem = len(semanas)
        _fin_vol = semanas[-1] + pd.Timedelta(days=6)
        periodo_vol = (f"{semanas[0].day} {_MESES_CORTO[semanas[0].month - 1]}"
                       f" – {_fin_vol.day} {_MESES_CORTO[_fin_vol.month - 1]}")
        anio_ref = (semanas_hist[-1] + pd.Timedelta(days=6)).year
        # Una entrada por columna-semana: la columna compara el cierre de
        # `semanas_hist[i + 1]` contra el de `semanas_hist[i]`. El nombre de
        # la columna es la FECHA y no el rótulo: con más de un año a la
        # vista, dos rótulos pueden coincidir, y el nombre es la clave del
        # DataFrame.
        #
        # `mide` marca las columnas que SUMAN el puntaje: las últimas
        # `n_sem - 1` (cinco semanas son cuatro variaciones). La grilla les
        # resalta la cabecera (2026-09-12, a pedido): con la historia a la
        # vista, sin la marca no hay forma de saber qué entra en el número
        # de «Volatilidad» y qué es historia. La semana BASE —la primera de
        # las cinco— no tiene columna propia entre las que miden: su precio
        # es el de la izquierda de la primera columna marcada.
        _n_miden = n_sem - 1
        cols_sem = []
        for i, s in enumerate(semanas_hist[1:]):
            _mide = i >= len(semanas_hist) - 1 - _n_miden
            cols_sem.append({
                "col": f"s_{s:%Y%m%d}",
                "hdr": _vol_fmt_semana_cabecera(s, anio_ref),
                "lp": _vol_fmt_semana_cabecera(semanas_hist[i], anio_ref),
                "lc": _vol_fmt_semana_cabecera(s, anio_ref),
                "mide": _mide,
                "tip": (f"Suma en la volatilidad ({periodo_vol})" if _mide
                        else f"Historia: no entra en la volatilidad, que mide "
                             f"{periodo_vol}"),
            })

        ranking_vista = [(p, info) for p, info in ranking
                         if not _q or _q in str(p).lower()]

        prod_focus = st.session_state.get("compras_vol_focus")
        if prod_focus not in {p for p, _ in ranking}:
            prod_focus = None

        # ── EL RANKING ARRIBA, A TODO EL ANCHO; EL DRILL ABAJO ───────────
        # 2026-09-12, a pedido: «que el cuadro suba y ocupe todo el largo
        # horizontal; que el gráfico de velas y el detalle de semana bajen y
        # compartan a mitad el espacio abajo».
        #
        # Es la TERCERA forma de esta tarjeta y conviene saber por qué
        # cambió cada vez. El 2026-09-07 el drill vivía DEBAJO de la grilla
        # en una sola columna (candlestick, título de la semana y tabla
        # apilados): el alto era la suma de todo y a la grilla le quedaban 6
        # filas. Unas horas después se mudó AL COSTADO (`COLUMNAS_DRILL`),
        # y eso le devolvió alto a la grilla pero le quitó ANCHO: 587px, en
        # los que las celdas sólo aguantaban los dos precios DEBAJO del %.
        #
        # El mismo día de esta mudanza los precios pasaron al COSTADO del %
        # en la celda (`tablas/compras_volatilidad.py::_MIN_ANCHO_COL_SEMANA`),
        # que pide 120px por columna-semana: en 587px eso era scroll
        # horizontal. Con la grilla a todo el ancho entra, y el drill,
        # partido en dos, cuesta el alto de UNA de sus mitades y no el de
        # las tres piezas apiladas — la cuenta está en
        # `alturas.RANKING_CON_DRILL`.
        #
        # Ya no hay `st.columns(COLUMNAS_DRILL)` en esta vista. La fila de
        # abajo es una subdivisión DENTRO de la tarjeta (ver más abajo).
        #
        # (Unas horas después, el mismo día, el título y los controles
        # dejaron de ser una fila ENCIMA de la grilla y pasaron a un panel a
        # su DERECHA — ver el bloque de `vol_fila_top`, arriba. «A todo el
        # ancho» quedó en «todo el ancho menos 240px».)
        if not ranking_vista:
            c_tabla.info(f"Ningún insumo coincide con «{_q}».")
        else:
            filas = []
            for prod, info in ranking_vista:
                cierres = info["cierres_hist"]
                fila = {"Insumo": _compras_truncar(str(prod), 34),
                        "__insumo_full": str(prod),
                        # El tooltip del nombre: con la columna oculta, es
                        # la forma de consultar el puntaje sin prenderla.
                        "__tip_insumo": (
                            f"{prod}\nVolatilidad {info['volatilidad']:.1f}"
                            f" · puesto {puesto[prod]} de {len(ranking)}"
                            f" · {periodo_vol}")}
                for i, c in enumerate(cols_sem):
                    prev, cur = cierres[i], cierres[i + 1]
                    delta = (None if (prev is None or cur is None or not prev)
                             else (cur - prev) / prev * 100)
                    fila[c["col"]] = delta
                    fila[f"__prev_{i}"] = prev
                    fila[f"__cur_{i}"] = cur
                fila["Volatilidad"] = info["volatilidad"]
                filas.append(fila)
            tv = pd.DataFrame(filas)

            # AgGrid devuelve la fila clickeada por CONTENIDO
            # (__insumo_full), no por índice — a diferencia del
            # st.dataframe que tenía este ranking antes, filtrar con el
            # buscador no puede desalinear un índice viejo contra la fila
            # nueva (arquitectura.md regla #130).
            with c_tabla:
                _clicked = renderizar_ranking_volatilidad(
                    tv, cols_sem,
                    altura=alturas.por_filas(len(tv), px_fila=ALTO_FILA_RANK,
                                             extra=CROMO_GRID_VOL, minimo=0,
                                             rol=alturas.RANKING_CON_DRILL),
                    key="compras_vol_rank_grid",
                    ver_vol=_ver_vol, periodo_vol=periodo_vol, n_sem=n_sem,
                )
            if _clicked is not None:
                prod_focus = _clicked
                st.session_state["compras_vol_focus"] = prod_focus

        prod_sel = prod_focus if prod_focus is not None else ranking[0][0]

        if st.session_state.get("compras_vol_prod_prev") != prod_sel:
            st.session_state["compras_vol_prod_prev"] = prod_sel
            st.session_state["compras_vol_semfocus"] = None
            st.session_state["compras_vol_last_click"] = None

        _ayuda_alcance.markdown(
            f"Volatilidad de las **últimas {n_sem} semanas** "
            f"({periodo_vol}), o sea sus {n_sem - 1} variaciones · sólo "
            "insumos con ≥ S/ 400 de gasto y compras en al menos el 75% de "
            "esas semanas.")

        unidad_raw = str(dd_rec.loc[dd_rec[col_prod] == prod_sel, col_um].mode().iat[0]) \
            if col_um and col_um in dd_rec.columns and not dd_rec.loc[dd_rec[col_prod] == prod_sel, col_um].empty \
            else "kg"
        unidad = {"KILOS": "kg", "KG": "kg", "LITROS": "L", "LT": "L", "UND": "und"}.get(
            unidad_raw.upper(), unidad_raw.lower())

        # La base de la primera vela: el cierre de la semana anterior en la
        # historia de la ventana y, si la ventana no la trae (Rango), el
        # último precio del histórico entero.
        _ch = candidatos[prod_sel]["cierres_hist"]
        _cierre_previo = _ch[-len(semanas) - 1] if len(_ch) > len(semanas) else None
        if _cierre_previo is None and d_full is not None:
            _cierre_previo = _vol_precio_previo(
                d_full, prod_sel, col_prod, col_punit, col_fecha, col_moneda,
                antes_de=semanas[0])
        weeks = _vol_detalle_producto(
            dd_rec, prod_sel, col_prod, col_punit, col_fecha, col_prov,
            col_cant, semanas, cierre_previo=_cierre_previo)

        # ── LA FILA DE ABAJO: VELAS | SEMANA, MITAD Y MITAD ──────────────
        # 2026-09-12, a pedido (ver el bloque del ranking, más arriba). Cada
        # mitad es un renglón de título y su bloque: a la izquierda el
        # nombre con sus KPIs y el candlestick, a la derecha la semana en
        # foco y sus compras. Los dos títulos van a la misma altura y los
        # dos bloques miden lo mismo (`MINI_CANDLE_DRILL` y
        # `PANEL_JUNTO_A_FIGURA`), así que la fila termina en una sola
        # línea en vez de en dos.
        #
        # columnas-internas: subdivisión DENTRO de la tarjeta (el gráfico y
        # su tabla), no una fila de drill que tenga que caer en el eje de
        # `COLUMNAS_DRILL`; 1/1 porque se pidió «a mitad».
        col_vela, col_semana = st.columns(2, gap=GAP_DRILL)

        with col_vela:
            # ── El detalle, en la MISMA tarjeta ──────────────────────────────
            # 2026-09-07, a pedido: «no entra en su tarjeta la parte de abajo,
            # el gráfico y su tabla; el usuario no debería hacer scroll en la
            # tarjeta, quizás sólo en la tabla». Acá había un segundo `_card()`.
            #
            # Fusionarlas no es cosmético: dos tarjetas son dos superficies que
            # el encuadre del proyecto («una tarjeta = una pantalla») mide por
            # separado, y apiladas medían 1.039px — dos pantallas. Con una
            # sola, lo único que scrollea es la GRILLA (que ya tenía su scroll
            # interno) y el resto se ve completo. Mismo movimiento que hizo
            # «Vs año pasado» el 2026-09-02, y por el mismo pedido.
            cierres = [w["c"] for w in weeks]
            precio_actual = cierres[-1]
            cambio_total = ((cierres[-1] - cierres[0]) / cierres[0] * 100) if cierres[0] else 0.0
            vol_total = candidatos[prod_sel]["volatilidad"]
            color_cambio = ERROR if cambio_total > 0.05 else (EXITO if cambio_total < -0.05 else GRIS_TEXTO)
            # EL SIGNO SE CALLA CUANDO REDONDEA A CERO, igual que el `_FMT_PCT`
            # de la grilla de arriba: `cierres[-1]` y `cierres[0]` pueden diferir
            # en la séptima cifra (el parquet guarda 110.169492 y 110.169375 para
            # el mismo precio de lista) y con el `>= 0` de antes eso salía como
            # «−0.0%» — un signo que afirma una caída sobre un número que dice
            # que no pasó nada. Medido con «Entraña fina importada x Kg».
            _sig = "" if abs(cambio_total) < 0.05 else ("+" if cambio_total > 0 else "−")
            # NOMBRE Y KPIs EN EL MISMO RENGLON (2026-09-07, a pedido).
            # Los tres KPIs ocupaban 51px en dos lineas propias debajo del
            # nombre; en linea y con las tallas chicas el bloque entero baja
            # a ~22, y esos ~30px son grafico.
            #
            # LOS ROTULOS SE ABREVIAN Y LA VOLATILIDAD PIERDE SU «pts»
            # porque el renglon es un presupuesto MEDIDO: con los rotulos
            # largos el trio mide 473px de contenido nowrap contra los 454
            # que tenia la columna del drill al costado del ranking (la
            # cuenta entera, en `estilos/_80_cards.py`). Desde el 2026-09-12
            # esta mitad mide lo mismo o algo mas, asi que la cuenta sigue
            # valiendo. Lo que se abrevia vuelve en el `title=`, que es un
            # tooltip nativo y no cuesta pixeles.
            #
            # El look lo pone `estilos/_80_cards.py` (.vol-detalle-hdr), no
            # un `style=` inline: son cinco reglas repetidas tres veces.
            st.markdown(
                f'<div class="vol-detalle-hdr">'
                f'<span class="vol-detalle-nom" title="{prod_sel}">'
                f'{_compras_truncar(str(prod_sel), 48)}</span>'
                f'<span class="vol-detalle-kpis">'
                f'<span title="Precio actual: cierre de la ultima semana">'
                f'<i>Precio</i><b>S/ {precio_actual:,.2f} /{unidad}</b></span>'
                f'<span title="Cambio total entre la primera y la ultima semana">'
                f'<i>Cambio</i><b style="color:{color_cambio};">'
                f'{_sig}{abs(cambio_total):.1f}%</b></span>'
                f'<span title="Volatilidad: suma de las variaciones % '
                f'semanales de las ultimas {n_sem} semanas ({periodo_vol})">'
                f'<i>Volatilidad</i><b>{vol_total:.1f}</b></span>'
                f'</span></div>',
                unsafe_allow_html=True,
            )

            # El alto del candlestick sale de un rol propio
            # (`MINI_CANDLE_DRILL`) y no de MINI (240): comparte la tarjeta
            # con el ranking de arriba, que es la lectura principal. La
            # cuenta de la tarjeta entera está en `graficos/alturas.py`.

            # EL HOVER HABLA DE COMPRAS, NO DE BOLSA (2026-09-12, a pedido).
            # Decía «abre S/ 8.50 · cierra S/ 15.52» y la celda de la misma
            # semana en la grilla decía «16.95 → 15.52»: el usuario leyó el
            # 16.95 como la apertura y preguntó por qué no coincidían. No es
            # la apertura — es el CIERRE DE LA SEMANA ANTERIOR; la vela mira
            # sólo lo que pasó dentro de la semana. «Primera compra / última
            # compra» dice qué es cada número sin saber qué es una vela.
            # Una semana sin compras no tiene ni primera ni última: su vela
            # es el precio anterior repetido, y el hover lo dice así.
            def _hover_vela(s, w):
                if not w["rows"]:
                    return (f"Semana del {s:%d/%m} · sin compras · se repite "
                            f"el último precio, S/ {w['c']:.2f}")
                return (f"Semana del {s:%d/%m} · primera compra S/ {w['o']:.2f}"
                        f" · máx S/ {w['h']:.2f} · mín S/ {w['l']:.2f}"
                        f" · última compra S/ {w['c']:.2f}")

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=semanas, open=[w["o"] for w in weeks], high=[w["h"] for w in weeks],
                low=[w["l"] for w in weeks], close=[w["c"] for w in weeks],
                increasing=dict(line=dict(color=ERROR), fillcolor=ERROR),
                decreasing=dict(line=dict(color=EXITO), fillcolor=EXITO),
                hovertext=[_hover_vela(s, w) for s, w in zip(semanas, weeks)],
                hoverinfo="text",
                name="",
            ))
            # Overlay invisible para capturar el clic (go.Candlestick sin
            # precedente de selección confiable en este proyecto — ver rules #11/#44).
            fig.add_trace(go.Scatter(
                x=semanas, y=[(w["h"] + w["l"]) / 2 for w in weeks],
                mode="markers", marker=dict(size=38, opacity=0),
                hoverinfo="skip", showlegend=False,
            ))
            _compras_layout(fig, alto=alturas.MINI_CANDLE_DRILL)
            # EL MARGEN SUPERIOR, A 8: `_compras_layout` reserva 30px arriba
            # para un título que esta figura no tiene —el suyo es el renglón
            # de KPIs de más arriba— y a 160px de alto esos 30 son el 19% de
            # la figura. Bajarlos devuelve casi todo lo que costó el recorte
            # de altura: el área de dibujo queda en ~120px contra los ~140
            # que tenía a 200 con el margen de siempre.
            fig.update_layout(margin=dict(l=10, r=10, t=8, b=10))
            # UNA MARCA POR VELA, EN ESPAÑOL. Sin `tickvals` Plotly elige
            # sus propias fechas y las rotula con su locale por defecto —
            # el inglés: el eje decía "Jul 12 / Jul 26 / Aug 9 / Aug 23"
            # mientras la grilla de arriba, el hover y el título de la
            # tabla de al lado decían "3-9 Ago" (regla #241, la misma que
            # ya arregló el gráfico por fecha de Documentos SUNAT).
            #
            # `ticktext` y no `tickformat`: acá el eje tiene cinco puntos
            # conocidos —los lunes de las cinco semanas— y marcarlos todos
            # es lo que hace que una vela se pueda buscar por su fecha.
            #
            # EL MISMO RÓTULO QUE LA GRILLA (2026-09-12, a pedido). Decía
            # sólo el lunes («10 Ago») mientras la columna de la misma semana
            # decía «10 Ago – 16 Ago», y la pregunta fue literal: «¿de dónde
            # sale el 10?». Es la semana BASE: la primera vela no tiene
            # columna entre las que suman el puntaje, porque una variación
            # necesita la semana anterior. Con el rótulo entero se ve que es
            # la misma semana que la columna, y que la grilla marca las
            # cuatro que miden (`mide` en `cols_sem`). Cinco rótulos de ~95px
            # entran en la mitad de la tarjeta.
            fig.update_layout(
                xaxis=dict(gridcolor=GRIS_BORDE, showgrid=False,
                           rangeslider=dict(visible=False),
                           tickmode="array", tickvals=semanas,
                           ticktext=[_vol_fmt_semana_cabecera(s, anio_ref)
                                     for s in semanas]),
                yaxis=dict(gridcolor=GRIS_BORDE, tickprefix="S/ "),
                showlegend=False,
            )

            _chart_key = f"compras_g_vol_candle_{_slug(str(prod_sel))}"
            _cfg = {"displaylogo": False, "displayModeBar": False}
            evt = st.plotly_chart(fig, use_container_width=True, key=_chart_key,
                                  on_select="rerun", selection_mode="points", config=_cfg)

            # Procesar clic (dedup, patrón de proveedor.py): solo se atiende
            # un punto que venga de la traza 1 (el overlay), no de la 0
            # (las velas).
            _mp = _first_point(evt)
            if _mp is not None and _mp.get("curve_number") == 1:
                _pi = _mp.get("point_index", _mp.get("point_number"))
                if _pi is not None and st.session_state.get("compras_vol_last_click") != _pi:
                    st.session_state["compras_vol_last_click"] = _pi
                    _misma = st.session_state.get("compras_vol_semfocus") == _pi
                    st.session_state["compras_vol_semfocus"] = None if _misma else _pi

            sem_focus = st.session_state.get("compras_vol_semfocus")
            if sem_focus is None or not (0 <= sem_focus < len(weeks)):
                # sin clic: la semana con el mayor movimiento propio (abre→cierra)
                sem_focus = max(range(len(weeks)), key=lambda i: abs(weeks[i]["c"] - weeks[i]["o"]))

            w = weeks[sem_focus]
            ini = semanas[sem_focus]
            fin = ini + pd.Timedelta(days=6)

            # CONTRA QUÉ SE COMPARA, CON EL PRECIO ESCRITO (2026-09-12, a
            # pedido). Decía «−8.5% vs semana anterior» y no se veía de dónde
            # salía: la base es el CIERRE de la semana anterior (su última
            # compra), el mismo número de la izquierda de la celda de la
            # grilla («16.95 → 15.52»), no la primera compra de ésta que
            # muestra la vela. Escribirlo cierra la pregunta.
            #
            # La primera semana también tiene base desde que existe
            # `_cierre_previo` (el cierre anterior a la ventana); antes se
            # quedaba sin comparación.
            #
            # Sin signo cuando redondea a cero, como el `_FMT_PCT` de la
            # grilla y el KPI «Cambio»: decía «+0.0%», un «subió» sobre un
            # número que dice que no pasó nada.
            delta_txt = ""
            _base = weeks[sem_focus - 1]["c"] if sem_focus > 0 else _cierre_previo
            if _base:
                var = (w["c"] - _base) / _base * 100
                _cero = abs(var) < 0.05
                color = GRIS_TEXTO if _cero else (ERROR if var > 0 else EXITO)
                _sig = "" if _cero else ("+" if var > 0 else "−")
                delta_txt = (f' <span style="color:{color}; font-weight:700;">'
                             f'{_sig}{abs(var):.1f}% vs cierre anterior '
                             f'(S/ {_base:,.2f})</span>')
        with col_semana:
            # SIN MARGEN PROPIO: el `gap` de la columna ya separa este
            # renglón de la tabla que va abajo, y sumarle .5rem lo dejaba en
            # 43px para una línea de texto. Los 8px son la mitad de lo que le
            # faltaba a la tarjeta para no sacar barra de scroll.
            st.markdown(
                f'<div>'
                f'<span style="font-weight:600;">Semana del {ini:%d/%m} al {fin:%d/%m}</span>{delta_txt}'
                f'</div>', unsafe_allow_html=True,
            )

            if not w["rows"]:
                st.caption("Sin compras registradas esta semana — precio repetido del último cierre.")
            else:
                tp = pd.DataFrame(w["rows"])
                maxp, minp = tp["precio"].max(), tp["precio"].min()

                def _sty_precio(v):
                    if maxp == minp:
                        return ""
                    if v == maxp:
                        return f"color:{ERROR}; font-weight:700;"
                    if v == minp:
                        return f"color:{EXITO}; font-weight:700;"
                    return ""

                tp = tp.rename(columns={"fecha": "Fecha", "prov": "Proveedor",
                                        "cant": "Cantidad", "precio": f"Precio/{unidad}"})
                fmts = {"Fecha": lambda v: f"{v:%d/%m/%Y}",
                       "Cantidad": lambda v: "—" if pd.isna(v) else f"{v:,.2f} {unidad}",
                       f"Precio/{unidad}": lambda v: f"S/ {v:,.2f}"}
                sty_p = (tp.style.format(fmts)
                         .map(_sty_precio, subset=[f"Precio/{unidad}"])
                         .hide(axis="index"))
                # 35 por fila y 38 de cabecera y bordes: lo que mide un
                # `st.dataframe`, para que con tres compras (el máximo que
                # hay hoy en el parquet para un insumo en una semana) la
                # tabla entre entera en `PANEL_JUNTO_A_FIGURA` sin scroll.
                st.dataframe(sty_p, use_container_width=True, hide_index=True,
                            height=alturas.por_filas(
                                len(tp), px_fila=35, extra=38, minimo=0,
                                rol=alturas.PANEL_JUNTO_A_FIGURA))
