"""graficos.compras.volatilidad - drill de Volatilidad de insumos.

Ranking de insumos por volatilidad de precio de compra semana a semana,
con drill a un candlestick (una vela = una semana: apertura/máximo/
mínimo/cierre de PRECIO_UNIT) y de ahí a las compras puntuales que
formaron la semana clickeada.

Semáforo de precio: como el dato es un COSTO (no una ganancia), "sube" es
malo (rojo, ERROR) y "baja" es bueno (verde, EXITO) — al revés de la
convención bursátil, a propósito.

El clic en una vela lo recibe `go.Candlestick` MISMO (traza 0). Hasta el
2026-09-12 se lo suponía no seleccionable —como go.Heatmap (regla #11) y
go.Histogram (regla #44)— y se capturaba con un go.Scatter invisible encima,
descartando los eventos de la vela. Pero ese scatter llevaba
`hoverinfo="skip"`, que en Plotly apaga también los clics: nunca recibió
uno, y la vela clickeada quedaba marcada sin que la tabla de la semana la
siguiera. Ver regla #388.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cortes import MESES_ABR_ES
from tema import (
    CELDA_POS_TEXTO, ERROR, ERROR_TEXTO, EXITO, GRIS_BORDE, GRIS_TEXTO,
    GRIS_TEXTO_SUAVE, LAVANDA_FONDO,
)
from graficos.base import (
    _compras_layout, _compras_truncar, _slug,
    preservar_widgets, selector_fecha_tarjeta,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras._comun import (
    CATEGORIA_SEC, GAP_DRILL, PARR, _first_point, documento_legible,
    unidad_corta,
)
from graficos import periodo
from graficos import alturas
from tablas.compras_volatilidad import (
    ALTO_FILA as ALTO_FILA_RANK, CROMO_GRID as CROMO_GRID_VOL,
    CROMO_SEMANA as CROMO_SEMANA_VOL,
    renderizar_compras_semana, renderizar_ranking_volatilidad,
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

_KEYS_WIDGET = ("compras_vol_q", "compras_vol_ver", "compras_vol_tabla_modo_*",
                "compras_vol_vslider_*")
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

_K_VFIN = "compras_vol_vfin"
"""Dueño de la VENTANA del candlestick: el lunes de la última semana a la
vista, o None (= las más recientes). NO es clave de widget, por lo mismo que
`_K_VENTANA`: el deslizador que la muestra lleva este valor DENTRO de su key
(`compras_vol_vslider_<insumo>_<n>_<fecha>`), así que cuando la ventana
cambia por afuera —otro insumo, otra ventana de la tarjeta— el widget que se
dibuja es otro y nace en el valor nuevo. Escribirle la key al widget no
alcanza: el navegador le vuelve a mandar el valor viejo (regla #212).

La escribe `_mover_ventana_velas`, el callback del deslizador, que corre
ANTES de la corrida: la ventana ya se usó —rango del eje, foco, título y
tabla— cuando se llega a dibujar el deslizador, así que leyendo su valor de
retorno llegaría una corrida tarde."""


def _mover_ventana_velas(key, semanas):
    """Callback del deslizador de las velas: pasa el índice elegido a la fecha
    de `_K_VFIN` y suelta la vela elegida, que puede haber quedado fuera de
    la ventana nueva — el foco vuelve a elegirse solo entre las que se ven."""
    i = st.session_state.get(key)
    if isinstance(i, int) and 0 <= i < len(semanas):
        st.session_state[_K_VFIN] = semanas[i]
        st.session_state["compras_vol_semfocus"] = None


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
VELAS_A_LA_VISTA = 4
"""Cuántas velas muestra el candlestick a la vez (2026-09-13). El gráfico
dibuja toda la historia de la grilla (`semanas_hist`) y el deslizador corre
esta ventana. Es otro número que `MAX_SEMANAS` a propósito: aquél es lo que
MIDE el puntaje, éste lo que entra legible en media tarjeta.

5 -> 4 el mismo día, a pedido: «si solo mostramos 4, que el texto de la
semana que está abajo de la vela salga en una sola línea». Con 5, cada
semana tenía ~96px de eje y el rótulo («17 Ago – 23 Ago», ~95px) iba en
dos renglones; con 4 son ~120 y entra en uno. De yapa, al abrir, las 4
velas son exactamente las 4 columnas resaltadas de la grilla (las que
suman el puntaje): la semana base, la primera de `MAX_SEMANAS`, queda un
paso a la izquierda."""
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


def _vol_fmt_ventana(ini, ult, anio_ref=None):
    """Rótulo de la ventana del candlestick en su deslizador: del lunes `ini`
    al domingo de la semana `ult` («10 Ago – 13 Set»), con el año corto si
    termina en otro que `anio_ref` — el mismo criterio que
    `_vol_fmt_semana_cabecera`."""
    fin = ult + pd.Timedelta(days=6)
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
                          col_cant, semanas, cierre_previo=None, col_docu=None):
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
                # El número CRUDO del parquet («F0E001000001703»); lo pasa a
                # «E001-1703» la tabla, con `documento_legible` (2026-09-12).
                "doc": (str(r[col_docu]) if col_docu and pd.notna(r[col_docu])
                        else "—"),
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
def _tarjeta_compras_semana(filas_semana, filas_ventana, titulo_semana,
                            titulo_ventana, delta_txt, unidad, ver_doc):
    """La tarjeta de documentos de Volatilidad: título, «1 semana | 4
    semanas» y la tabla de compras.

    UN FRAGMENT DENTRO DEL FRAGMENT DEL DRILL (2026-09-13, a pedido: «¿por
    qué cuando hago un cambio en un toggle de una tarjeta se actualizan las
    tres?»). Las tres tarjetas eran tres SUPERFICIES (#415) pero un solo
    `@st.fragment`: cualquier control de adentro re-corría la sección entera
    —el ranking de 12 meses, el candlestick y las dos tablas— y el velo de
    `data-stale` (#366) cubría las tres. El selector de esta tarjeta es el
    único control que no le cambia nada a las otras dos, así que corre solo:
    Streamlit re-ejecuta esta función con los argumentos de la última
    corrida del drill, que es exactamente lo que hace falta.

    Lo que SÍ tiene que refrescar las tres sigue en el drill: elegir otro
    insumo (cambia todo), mover la ventana o clickear una vela (la tabla
    sigue a las velas). Cada vez que el drill corre, vuelve a llamar a esta
    función con los datos nuevos.

    Su key (`compras_vol_tabla_modo_*`) sigue en `_KEYS_WIDGET` del drill: la
    escalada de fecha (`st.rerun(scope="app")`) aborta la corrida antes de
    que esta tarjeta registre su control, y sin eso se lo llevaría.

    `filas_*` son las filas de `_vol_detalle_producto` (fecha, prov, doc,
    cant, precio) SIN formatear; `delta_txt` es el HTML del «±x% vs cierre
    anterior», que sólo va con «1 semana». Regla #417."""
    # ── «1 SEMANA | 4 SEMANAS» (2026-09-13, a pedido) ────────────────────
    # «una opción minimalista de mostrar varias semanas en la tabla de
    # documentos del costado, para que pueda estar alineada con el gráfico de
    # velas». Con «4 semanas» la tabla lista las compras de TODAS las velas a
    # la vista — la misma ventana del deslizador, que por eso pasó a ser del
    # servidor (ver `_K_VFIN`). Con «1 semana», la de la vela elegida.
    #
    # El título y el control van en UNA fila (`vol_sem_hdr`,
    # `estilos/_80_cards.py`). El título se escribe DESPUÉS del control —dice
    # una cosa u otra según lo elegido— en un hueco reservado antes, así en
    # pantalla va primero. Con las clases del título del insumo
    # (`.vol-detalle-hdr` / `.vol-detalle-nom`), para que los dos títulos no
    # se puedan desparejar.
    _op_modo = ("1 semana", f"{VELAS_A_LA_VISTA} semanas")
    with st.container(key="vol_sem_hdr"):
        _hdr_semana = st.empty()
        # La key lleva el número: si cambia `VELAS_A_LA_VISTA` (pasó de 5 a 4
        # el 2026-09-13), una sesión abierta con «5 semanas» guardado no
        # choca contra opciones que ya no lo tienen — nace otro widget.
        _varias = st.segmented_control(
            "Compras de", _op_modo,
            key=f"compras_vol_tabla_modo_{VELAS_A_LA_VISTA}",
            default=_op_modo[0],
            label_visibility="collapsed") == _op_modo[1]
    if _varias:
        _hdr_semana.markdown(
            f'<div class="vol-detalle-hdr">'
            f'<span class="vol-detalle-nom">{titulo_ventana}</span>'
            f'</div>', unsafe_allow_html=True)
        _filas = filas_ventana
    else:
        _hdr_semana.markdown(
            f'<div class="vol-detalle-hdr">'
            f'<span class="vol-detalle-nom">{titulo_semana}</span>{delta_txt}'
            f'</div>', unsafe_allow_html=True)
        _filas = filas_semana

    if not _filas:
        st.caption("Sin compras registradas esta semana — precio repetido "
                   "del último cierre." if not _varias
                   else "Sin compras registradas en estas semanas.")
        return

    tp = pd.DataFrame(_filas)
    maxp, minp = tp["precio"].max(), tp["precio"].min()
    # EL SEMÁFORO DEL PRECIO viaja como DATO en la fila (`__tono`) y no como
    # estilo: la grilla corre en un iframe y su `cellStyle` sólo ve lo que
    # trae la fila. La compra más cara en rojo, la más barata en verde; con
    # un solo precio, ninguna. Con «4 semanas», las del tramo entero.
    tp["__tono"] = [
        "" if maxp == minp
        else "max" if p == maxp else "min" if p == minp else ""
        for p in tp["precio"]]

    # EL DOCUMENTO, AL LADO DE LA FECHA (2026-09-12, a pedido): «E001-1703»,
    # como se lee en el papel, y no el código de 15 caracteres del parquet —
    # `documento_legible` es la misma que usan las tablas de Documentos. Sin
    # columna de documento (el demo local) la columna va oculta.
    if ver_doc:
        tp["doc"] = documento_legible(tp["doc"])
    tp["fecha"] = tp["fecha"].map(lambda v: f"{v:%d/%m/%Y}")
    tp["cant"] = tp["cant"].map(
        lambda v: "—" if pd.isna(v) else f"{v:,.2f} {unidad}")
    tp["precio"] = tp["precio"].map(lambda v: f"S/ {v:,.2f}")

    # EN AGGRID Y NO EN `st.dataframe` (2026-09-12, a pedido: «el mismo
    # tamaño de filas y diseño» que el ranking de arriba): `st.dataframe`
    # dibuja sus celdas en un canvas y ni el modo diseño ni `estilos/`
    # alcanzan sus filas. Regla #396. LA KEY LLEVA EL ALTO (medido):
    # st_aggrid no le cambia el alto al IFRAME cuando la misma key recibe
    # otro `height`, y de la tercera compra en adelante no se veían.
    _alto_tabla = alturas.por_filas(
        len(tp), px_fila=ALTO_FILA_RANK, extra=CROMO_SEMANA_VOL,
        minimo=0, rol=alturas.PANEL_JUNTO_A_FIGURA)
    renderizar_compras_semana(
        tp[["fecha", "doc", "prov", "cant", "precio", "__tono"]],
        titulo_precio=f"Precio/{unidad}", altura=_alto_tabla,
        key=f"compras_vol_semana_grid_{_alto_tabla}", ver_doc=ver_doc)


@st.fragment
def _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                               col_valor, col_cant, col_um, col_moneda=None,
                               d_full=None, col_docu=None):
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

    # TRES TARJETAS Y NO UNA (2026-09-13, a pedido: «dividir la tarjeta de
    # volatilidad en 3 tarjetas: la tabla arriba, el gráfico de velas abajo
    # y la tabla de producto al costado, en tarjetas individuales»). El
    # contenedor de afuera es transparente; las superficies son
    # `compras_vol_card_rank` (cabecera + ranking), `_velas` y `_semana`,
    # con el look de las de Producto (`estilos/_80_cards.py`). Cada parte se
    # cuelga de SU tarjeta sin re-indentar el drill: la cabecera y el hueco
    # de la tabla con `_tarj_rank.container(...)`, las dos de abajo con
    # `with col_x, st.container(...)`. Regla #415.
    with st.container(key="compras_vol_cuerpo"):
        _tarj_rank = st.container(key="compras_vol_card_rank")
        # ── TÍTULO Y CONTROLES EN UNA FILA ARRIBA; LA TABLA, A TODO EL ANCHO ─
        # 2026-09-12, a pedido: «cambiar el título a "Volatilidad de Insumos"
        # y ponerlo arriba, al lado izquierdo, y los toggles y demás en la
        # misma fila, como la vista "Vs año pasado"; la tabla pasa a medir
        # todo el largo horizontal de la tarjeta» (regla #394). Es el mismo
        # idioma que `vap_fila_hdr`: el título es el elástico de la fila y
        # los controles miden lo suyo, y la raya va debajo de la fila.
        #
        # Esta forma YA EXISTIÓ (hasta unas horas antes, el mismo día): la
        # cabecera se había ido a un panel de 240px a la DERECHA de la tabla
        # (`vol_panel`), para que la grilla arrancara en el borde de la
        # tarjeta. Volvió arriba porque ese panel le robaba 240px de ancho a
        # una grilla que se lee de izquierda a derecha, semana por semana.
        # Los 55px de alto que cuesta la fila los paga la TARJETA —que ahora
        # mide lo mismo que la de «Vs año pasado», a pedido—, no la grilla.
        with _tarj_rank.container(key="vol_fila_hdr"):
            st.markdown('<p class="chart-card-hdr vol-hdr">Volatilidad de '
                        'Insumos</p>', unsafe_allow_html=True)

            # ── Ventana + fecha, lado a lado ─────────────────────────────
            # LOS DOS CONTROLES SON UNO SOLO, leídos de izquierda a derecha:
            # la ventana elige el GRANO ("últimos 12 meses") y la fecha
            # elige un rango EXACTO. Por eso el trigger no muestra la fecha
            # de la franja mientras la ventana mande —mostraría un dato que
            # esta tarjeta no está usando— sino la ventana misma, y por eso
            # tocar el panel devuelve la ventana a "Rango" (arriba, en la
            # escalada).
            #
            # El trigger es el MISMO componente que tienen los dos rankings
            # y la vista Semanal (`base.py::selector_fecha_tarjeta`): no es
            # un filtro paralelo, escribe la clave del rango de esta sección
            # (`categoria=`, regla #363). Dibuja su propio contenedor,
            # `cp_vol_fila`, que es el ítem de esta fila.
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

            with st.container(key="vol_hdr_buscar"):
                _q = st.text_input("Buscar insumo", key="compras_vol_q",
                                   placeholder="Buscar insumo…",
                                   label_visibility="collapsed").strip().lower()

            # ── La columna «Volatilidad», a pedido y no siempre ──────────
            # 2026-09-12: «que la columna de volatilidad no figure siempre
            # visible sino sea consultable». Arranca oculta; esta pastilla la
            # prende y la apaga. Sin ella el puntaje sigue a mano en el
            # tooltip del nombre del insumo, y el orden de la tabla no cambia.
            #
            # `st.pills` de UNA opción y no un `st.toggle`: se lee como un
            # botón que queda marcado, que es lo que es. Va en `_KEYS_WIDGET`
            # por lo de siempre (la escalada de fecha la borraría, #373).
            with st.container(key="vol_hdr_ver"):
                _ver_vol = st.pills(
                    "Mostrar", ["Volatilidad"], key="compras_vol_ver",
                    label_visibility="collapsed") == "Volatilidad"

            # ── Cómo se lee la vista: un ícono, no dos captions ──────────
            # Eran DOS `st.caption` EN FLUJO que sumaban ~83px para explicar
            # algo que se lee UNA vez; pasaron a un popover de sólo ícono,
            # exactamente como `vap_hdr_ayuda`.
            #
            # La primera línea (período y umbrales) va por un HUECO: el
            # período se sabe más abajo, cuando ya se recortó `dd` a las
            # semanas con datos.
            #
            # El párrafo de los DOS PRECIOS no es relleno: son cierres de
            # semanas DISTINTAS —el de la anterior y el de ésta— y leerlos
            # como si los dos fueran de la semana del encabezado es la
            # confusión que reportó el usuario el 2026-09-07 con captura.
            with st.container(key="vol_hdr_ayuda"):
                with st.popover(":material/info:", use_container_width=False):
                    with st.container(key="vol_ayuda_panel"):
                        _ayuda_alcance = st.empty()
                        st.markdown(
                            "**Volatilidad** = la suma de las variaciones % "
                            "de una semana a la siguiente, en valor "
                            "absoluto: mide cuánto se MUEVE el precio, no "
                            "hacia dónde." + PARR
                            + "Cada celda compara el **cierre** (la última "
                            "compra) de esa semana contra el de la semana "
                            "anterior, así que los dos precios al costado "
                            "del % son de semanas DISTINTAS — el tooltip de "
                            "la celda las nombra. El % va redondeado a "
                            "entero; los precios, no. Las compras "
                            "intermedias se ven abajo, en el candlestick y "
                            "en su tabla."
                            + PARR
                            + "Deslizá la tabla hacia la izquierda (o usá "
                            "‹ › junto a «Insumo») para ver semanas "
                            "anteriores: son historia, no entran en el "
                            "puntaje, y el orden no cambia. Las que SÍ "
                            "suman son las de título resaltado; la semana "
                            "anterior a la primera de ellas es la base. El "
                            "gráfico de velas recorre las mismas semanas: "
                            "movelo con la línea que tiene arriba (al "
                            "pasarle el mouse dice qué tramo es) para ir "
                            f"hacia atrás, y con «1 semana | "
                            f"{VELAS_A_LA_VISTA} semanas» la "
                            "tabla "
                            "de al lado lista las compras de la vela "
                            "elegida o las de todas las que se ven. El "
                            "botón "
                            "**Volatilidad** muestra la columna del "
                            "puntaje; sin ella, se consulta pasando el "
                            "mouse sobre el nombre del insumo."
                            + PARR
                            + "Clic en una fila para ver su candlestick; "
                            "clic en una vela, para las compras de esa "
                            "semana.")

        # El hueco de la tabla, a todo el ancho. Se llena más abajo (depende
        # de lo que digan los controles), y los mensajes de «no hay datos»
        # van en él: salen donde iba la tabla.
        c_tabla = _tarj_rank.container(key="vol_tabla")

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
        # que pide 120px por columna-semana (130 desde el punto de alarma,
        # regla #391): en 587px eso era scroll
        # horizontal. Con la grilla a todo el ancho entra, y el drill,
        # partido en dos, cuesta el alto de UNA de sus mitades y no el de
        # las tres piezas apiladas — la cuenta está en
        # `alturas.RANKING_CON_DRILL`.
        #
        # Ya no hay `st.columns(COLUMNAS_DRILL)` en esta vista. La fila de
        # abajo es una subdivisión DENTRO de la tarjeta (ver más abajo).
        #
        # (Unas horas después, el mismo día, el título y los controles
        # pasaron a un panel a la DERECHA de la grilla y «a todo el ancho»
        # quedó en «todo el ancho menos 240px»; más tarde volvieron a una
        # fila encima, y la grilla recuperó el ancho entero — ver
        # `vol_fila_hdr`, arriba, y la regla #394.)
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
            st.session_state[_K_VFIN] = None

        _ayuda_alcance.markdown(
            f"Volatilidad de las **últimas {n_sem} semanas** "
            f"({periodo_vol}), o sea sus {n_sem - 1} variaciones · sólo "
            "insumos con ≥ S/ 400 de gasto y compras en al menos el 75% de "
            "esas semanas.")

        unidad_raw = str(dd_rec.loc[dd_rec[col_prod] == prod_sel, col_um].mode().iat[0]) \
            if col_um and col_um in dd_rec.columns and not dd_rec.loc[dd_rec[col_prod] == prod_sel, col_um].empty \
            else "kg"
        # El mapa vive en `_comun.py` desde el 2026-09-13: «Vs año pasado»
        # también escribe unidades, y dos copias se desincronizan.
        unidad = unidad_corta(unidad_raw)

        # ── LAS VELAS RECORREN LA MISMA HISTORIA QUE LA GRILLA ───────────
        # 2026-09-13, a pedido: «que en el gráfico de velas el usuario pueda
        # hacer scroll horizontal y ver semanas anteriores; que muestre las
        # semanas que figuran en la tabla superior». Hasta ese día el
        # candlestick dibujaba sólo `semanas` (las cinco que miden el
        # puntaje); ahora dibuja `semanas_hist` entera y ABRE mostrando
        # `VELAS_A_LA_VISTA` — ver el eje X, más abajo. Lo que NO cambia:
        # los KPIs y el puntaje siguen midiendo las cinco de `semanas`.
        #
        # La base de la primera vela es el último precio ANTES de la
        # ventana, sobre el histórico entero: con la historia a la vista, la
        # primera vela es la de hace un año, no la de hace cinco semanas.
        _cierre_previo = None
        if d_full is not None:
            _cierre_previo = _vol_precio_previo(
                d_full, prod_sel, col_prod, col_punit, col_fecha, col_moneda,
                antes_de=semanas_hist[0])
        weeks = _vol_detalle_producto(
            dd, prod_sel, col_prod, col_punit, col_fecha, col_prov,
            col_cant, semanas_hist, cierre_previo=_cierre_previo,
            col_docu=col_docu)
        # Las semanas de ANTES de la primera compra del insumo no tienen
        # precio que dibujar: sin recortarlas, `_vol_detalle_producto` las
        # llena con S/ 0 y el eje baja a cero (el mismo bug que la primera
        # vela en «S/ −10», 2026-09-12).
        _k0 = next((i for i, w in enumerate(weeks) if w["rows"] or w["c"] > 0), 0)
        semanas_v, weeks = semanas_hist[_k0:], weeks[_k0:]
        # Dónde empiezan, dentro de `weeks`, las semanas que MIDEN.
        _i_mide = max(0, len(weeks) - n_sem)

        # ── LA FILA DE ABAJO: VELAS | SEMANA, MITAD Y MITAD ──────────────
        # 2026-09-12, a pedido (ver el bloque del ranking, más arriba). Cada
        # mitad es un renglón de título y su bloque: a la izquierda el
        # nombre con sus KPIs y el candlestick, a la derecha la semana en
        # foco y sus compras. Los dos títulos van a la misma altura y los
        # dos bloques miden lo mismo (`MINI_CANDLE_DRILL` y
        # `PANEL_JUNTO_A_FIGURA`), así que la fila termina en una sola
        # línea en vez de en dos.
        #
        # DESDE EL 2026-09-13 ES UNA FILA DE DOS TARJETAS (regla #415), no
        # una subdivisión dentro de una: el hueco entre ellas es `GAP_DRILL`,
        # el de todas las filas de drill de Compras (era "large", 4rem,
        # mientras las dos mitades compartían superficie y el aire lo tenía
        # que poner el gap). La proporción sigue en 1/1, y NO es
        # `COLUMNAS_DRILL` (1.6/1) a sabiendas: en la mitad chica la tabla de
        # la semana quedaba en ~380px útiles contra los 456 que piden sus
        # columnas (Fecha, Documento, Cantidad y Precio fijos + el mínimo de
        # Proveedor). Es el «1/1 en volatilidad.py» que ya lista el PENDIENTE
        # de `test_graficos.py::_pruebas_grilla_horizontal`.
        col_vela, col_semana = st.columns(2, gap=GAP_DRILL)

        with col_vela, st.container(key="compras_vol_card_velas"):
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
            # Sobre las semanas que MIDEN, no sobre toda la historia que
            # ahora dibuja el gráfico: «Cambio» y «Volatilidad» hablan del
            # mismo período, el de `periodo_vol`.
            cierres = [w["c"] for w in weeks[_i_mide:]]
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
                f'<span title="Cambio entre la primera y la ultima de las '
                f'{n_sem} semanas que miden ({periodo_vol})">'
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

            # ── EL CLIC SE LEE ANTES DE DIBUJAR ───────────────────────────────
            # 2026-09-12, a pedido: «cuando hay un solo documento, la vela se
            # reduce y es casi imposible de clickearle». Con una sola compra
            # la vela es una raya de 1-2px. Darle un tamaño MÍNIMO se
            # descartó: una semana plana dibujada con cuerpo parecería una
            # semana que se movió. Lo que crece es el BLANCO DEL CLIC, no la
            # vela: una barra invisible por semana, del ancho de su columna y
            # del alto entero del gráfico (traza 0, más abajo).
            #
            # Y la semana elegida se marca con una BANDA detrás de su vela, no
            # con la atenuación de Plotly: esa atenuación la pinta la
            # selección del gráfico, y la selección ahora es de la barra
            # invisible. Para dibujar la banda en la MISMA corrida del clic,
            # el clic se lee del estado del gráfico ANTES de dibujarlo
            # (`st.session_state[key]` ya trae la selección de la corrida
            # anterior), y el gráfico se dibuja con una key NUEVA después de
            # cada clic (`compras_vol_nclic`): así nace sin selección —sin
            # nada atenuado— y un clic sobre la semana que ya estaba elegida
            # también se atiende. Es la receta de CLAUDE.md para la selección
            # que persiste entre reruns, con un contador en vez del foco.
            _nclic = st.session_state.get("compras_vol_nclic", 0)
            _key_base = f"compras_g_vol_candle_{_slug(str(prod_sel))}"
            _mp = _first_point(st.session_state.get(f"{_key_base}_{_nclic}"))
            if _mp is not None and _mp.get("curve_number") == 0:
                _pi = _mp.get("point_index", _mp.get("point_number"))
                if _pi is None and _mp.get("x") is not None:
                    try:
                        _xs = pd.Timestamp(_mp["x"]).normalize()
                        _pi = next((i for i, s in enumerate(semanas_v)
                                    if s == _xs), None)
                    except (ValueError, TypeError):
                        _pi = None
                if _pi is not None and 0 <= _pi < len(weeks):
                    # LA FECHA DE LA SEMANA, NO SU POSICIÓN (2026-09-13): con
                    # la historia en el gráfico, la posición depende de la
                    # ventana de la tarjeta y de dónde arranca la serie del
                    # insumo — pasar de 12m a 3m corría el foco a otra semana.
                    st.session_state["compras_vol_semfocus"] = semanas_v[_pi]
                    _nclic += 1
                    st.session_state["compras_vol_nclic"] = _nclic
            _chart_key = f"{_key_base}_{_nclic}"

            # ── LA VENTANA A LA VISTA LA DECIDE EL SERVIDOR ──────────────
            # 2026-09-13, a pedido: «la barra deslizante del gráfico de velas
            # no es muy funcional». Era el `rangeslider` de Plotly, que mueve
            # la ventana EN EL NAVEGADOR: arrastrando cerca de una punta la
            # achicaba en vez de correrla (sus manijas de zoom estaban
            # escondidas, no apagadas) y dejaba una vela estirada de borde a
            # borde, sin un solo rótulo — la captura del usuario. Y lo que
            # el navegador mueve, el servidor no lo sabe: la tabla de al lado
            # no podía seguir a las velas, que fue el otro pedido del día.
            #
            # Ahora la ventana es estado (`_K_VFIN`) y la mueve un
            # `st.select_slider` —una línea entre el título y el gráfico—. El eje X va fijo: sin
            # arrastre ni zoom, lo que se ve es siempre lo que el servidor
            # cree que se ve. Cuesta un rerun del fragment por movimiento.
            _n_v = min(VELAS_A_LA_VISTA, len(weeks))
            _vfin = st.session_state.get(_K_VFIN)
            _iv1 = next((i for i, s in enumerate(semanas_v) if s == _vfin),
                        len(weeks) - 1)
            _iv1 = max(_n_v - 1, _iv1)
            _iv0 = _iv1 - _n_v + 1

            # El foco, DENTRO de la ventana. Una vela sólo se puede clickear
            # si se ve, así que el clic siempre cae adentro; lo que la saca
            # de la ventana es moverla, y ahí vale lo mismo que sin clic.
            _foco = st.session_state.get("compras_vol_semfocus")
            sem_focus = next((i for i in range(_iv0, _iv1 + 1)
                              if semanas_v[i] == _foco), None)
            if sem_focus is None:
                # sin clic: la del mayor movimiento propio (abre→cierra)
                # entre las que se ven — al abrir, las que MIDEN.
                sem_focus = max(range(_iv0, _iv1 + 1),
                                key=lambda i: abs(weeks[i]["c"] - weeks[i]["o"]))

            # El rango de Y, a mano: la barra invisible tiene que ir de
            # borde a borde del área de dibujo, y para eso hace falta saber
            # dónde están los bordes. 12% de aire, como el automático; con
            # un precio que no se movió en ninguna semana, un aire mínimo
            # para que la raya no quede pegada al borde.
            #
            # SOBRE LAS SEMANAS A LA VISTA (2026-09-13, a pedido y con
            # captura: «¿por qué el eje vertical dice 20 soles?», en una
            # ventana donde el azúcar se movía entre 2.97 y 3.40). Fue el
            # rango de TODA la historia mientras la ventana se deslizaba en
            # el navegador (#402): Plotly no reacomoda el eje Y al correr el
            # X, y un rango de las cinco a la vista dejaba cortadas las velas
            # que entraban. Desde que la ventana la mueve el servidor (#412)
            # cada posición es una corrida nueva, y ese motivo se fue — el
            # rango de la historia sólo servía para que el pico de una semana
            # de agosto (19.07) aplastara a todas las demás. Regla #413.
            _lo = min(weeks[i]["l"] for i in range(_iv0, _iv1 + 1))
            _hi = max(weeks[i]["h"] for i in range(_iv0, _iv1 + 1))
            _pad = max((_hi - _lo) * 0.12, abs(_hi) * 0.04, 0.5)
            _y0, _y1 = _lo - _pad, _hi + _pad

            fig = go.Figure()
            # Traza 0: el BLANCO DEL CLIC. Invisible, una barra por semana
            # de 7 días de ancho —la columna entera de la vela, sin huecos—
            # y del alto del área de dibujo. Lleva el hover de la semana
            # (`hoverinfo="text"`, NO "skip": con "skip" Plotly apaga
            # también el clic, regla #388).
            fig.add_trace(go.Bar(
                x=semanas_v, base=[_y0] * len(weeks), y=[_y1 - _y0] * len(weeks),
                width=[7 * 24 * 3600 * 1000] * len(weeks),
                marker=dict(color="rgba(0,0,0,0)", line=dict(width=0)),
                hovertext=[_hover_vela(s, w) for s, w in zip(semanas_v, weeks)],
                hoverinfo="text", showlegend=False, name="",
            ))
            # Traza 1: la vela, sólo para VER. `hoverinfo="skip"` a
            # propósito: el hover y el clic los da la barra de atrás, y dos
            # hovers de la misma semana competirían por quién se muestra.
            fig.add_trace(go.Candlestick(
                x=semanas_v, open=[w["o"] for w in weeks], high=[w["h"] for w in weeks],
                low=[w["l"] for w in weeks], close=[w["c"] for w in weeks],
                increasing=dict(line=dict(color=ERROR), fillcolor=ERROR),
                decreasing=dict(line=dict(color=EXITO), fillcolor=EXITO),
                hoverinfo="skip", name="",
            ))
            # La semana elegida: una banda lavanda detrás de su vela.
            fig.add_vrect(
                x0=semanas_v[sem_focus] - pd.Timedelta(days=3.5),
                x1=semanas_v[sem_focus] + pd.Timedelta(days=3.5),
                fillcolor=LAVANDA_FONDO, opacity=1, line_width=0, layer="below")

            # ── LOS PRECIOS, ESCRITOS AL COSTADO DE CADA VELA ────────────
            # 2026-09-12, a pedido y sobre una maqueta con datos reales: la
            # primera y la última compra de la semana, siempre visibles, sin
            # tener que pasar el mouse. Van en trazas de TEXTO aparte, con
            # `hoverinfo="skip"` —que, justamente, las deja fuera del clic:
            # el clic lo recibe sólo la barra invisible (traza 0)—.
            #
            # AL COSTADO Y A LA ALTURA DE SU PRECIO, no arriba o abajo de la
            # vela: así una etiqueta en el precio más alto o más bajo no se
            # corta contra el borde de un gráfico de 150px, y no hubo que
            # agrandarlo. El corrimiento es en DÍAS (`_dx`), no en píxeles: el
            # ancho de la vela también se mide en días, así que la etiqueta
            # queda pegada a la vela en cualquier ancho de pantalla.
            #
            # La ÚLTIMA compra va en negrita y en el tono oscuro del color de
            # su vela —el mismo de los precios de la grilla—; es el número de
            # la derecha de la celda de esa semana. Una semana SIN compras la
            # lleva en gris: es el precio anterior repetido. La PRIMERA sólo
            # aparece si hubo compras, si difiere de la última y si las dos
            # no se pisan (11% del rango ≈ 12px de los ~110 de alto útil); en
            # una vela plana hay una sola etiqueta.
            #
            # El color de una vela plana (primera == última) no lo decide su
            # cuerpo sino el cierre ANTERIOR, que es lo que hace Plotly: sube
            # si cerró más alto, baja si cerró más bajo, y si repite, sigue
            # la dirección de la vela previa. Se replica acá para que la
            # etiqueta tenga el color de su vela.
            # 2.1 días: medido, la vela mide ~1.7 días de medio ancho (49px
            # de cuerpo cada 100px de semana), así que la etiqueta arranca
            # ~6px después del borde. Con 2.5 quedaba a 13px y se leía suelta.
            _dx = pd.Timedelta(days=2.1)
            # El mismo rango que el eje (el de la ventana): el 11% que decide
            # si las dos etiquetas de una vela se pisan es 11% del ALTO que
            # se ve, no del de la historia.
            _rng = (_hi - _lo) or 1.0
            _ult_x, _ult_y, _ult_t, _ult_c = [], [], [], []
            _pri_x, _pri_y, _pri_t = [], [], []
            _dir_prev, _c_prev = "sube", None
            for s, w in zip(semanas_v, weeks):
                if w["c"] > w["o"]:
                    _dir = "sube"
                elif w["c"] < w["o"]:
                    _dir = "baja"
                elif _c_prev is None:
                    _dir = "sube"
                else:
                    _dir = ("sube" if w["c"] > _c_prev
                            else "baja" if w["c"] < _c_prev else _dir_prev)
                _dir_prev, _c_prev = _dir, w["c"]
                _ult_x.append(s + _dx)
                _ult_y.append(w["c"])
                _ult_t.append(f"<b>{w['c']:,.2f}</b>")
                _ult_c.append(GRIS_TEXTO_SUAVE if not w["rows"]
                              else ERROR_TEXTO if _dir == "sube" else CELDA_POS_TEXTO)
                if w["rows"] and abs(w["o"] - w["c"]) >= 0.11 * _rng:
                    _pri_x.append(s + _dx)
                    _pri_y.append(w["o"])
                    _pri_t.append(f"{w['o']:,.2f}")
            fig.add_trace(go.Scatter(
                x=_ult_x, y=_ult_y, text=_ult_t, mode="text",
                textposition="middle right",
                textfont=dict(size=11, color=_ult_c),
                # RECORTADAS AL ÁREA DE DIBUJO desde que el gráfico se
                # desliza (2026-09-13): con `cliponaxis=False` las etiquetas
                # de las semanas fuera de la vista se dibujaban igual, encima
                # del eje Y y de los márgenes. La de la última vela sigue
                # entrando: el eje llega 6 días más allá de ella.
                hoverinfo="skip", showlegend=False, cliponaxis=True,
            ))
            if _pri_x:
                fig.add_trace(go.Scatter(
                    x=_pri_x, y=_pri_y, text=_pri_t, mode="text",
                    textposition="middle right",
                    textfont=dict(size=10.5, color=GRIS_TEXTO),
                    hoverinfo="skip", showlegend=False, cliponaxis=True,
                ))
            _compras_layout(fig, alto=alturas.MINI_CANDLE_DRILL)
            # EL MARGEN SUPERIOR, A 8: `_compras_layout` reserva 30px arriba
            # para un título que esta figura no tiene —el suyo es el renglón
            # de KPIs de más arriba— y a 160px de alto esos 30 son el 19% de
            # la figura. Bajarlos devuelve casi todo lo que costó el recorte
            # de altura: el área de dibujo queda en ~120px contra los ~140
            # que tenía a 200 con el margen de siempre.
            #
            # Y EL DE ABAJO A 2, CON `pad` A 2 (2026-09-13): nacieron para
            # hacerle sitio al `rangeslider` que tuvo este gráfico unas horas
            # (ver `_K_VFIN`); se quedan porque el `pad` (8, del tema de
            # Streamlit) y el margen inferior son alto que no dibuja nada.
            fig.update_layout(margin=dict(l=10, r=10, t=8, b=2, pad=2))
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
                # El rango de X, a mano: la etiqueta de la ÚLTIMA vela queda
                # a la derecha de todo, y con el rango automático el texto
                # se salía por el margen de 10px.
                xaxis=dict(gridcolor=GRIS_BORDE, showgrid=False,
                           rangeslider=dict(visible=False), fixedrange=True,
                           # Y arranca 2 días antes de la primera vela y no
                           # 3.5 (2026-09-13, captura del usuario): con 3.5
                           # asomaba en el borde el FINAL de la etiqueta de
                           # la semana anterior a la ventana («…8»), cortada
                           # por el clip del área de dibujo. El cuerpo de la
                           # vela mide ~1.7 días de medio ancho: entra igual.
                           #
                           # Y TERMINA 5.2 DÍAS DESPUÉS DE LA ÚLTIMA, no 6
                           # (2026-09-13, captura del usuario): con la
                           # ventana en medio de la historia, a 6 días
                           # asomaba en el borde derecho un pedazo de la
                           # vela de la semana SIGUIENTE, que empieza a los
                           # 7 - 1.7 = 5.3. La etiqueta de la última vela
                           # sigue entrando: arranca a 2.1 días y a ~13px
                           # por día llega hasta ~40px de texto.
                           range=[semanas_v[_iv0] - pd.Timedelta(days=2),
                                  semanas_v[_iv1] + pd.Timedelta(days=5.2)],
                           tickmode="array", tickvals=semanas_v,
                           # UN RENGLÓN (2026-09-13, a pedido), a 11px: con
                           # `VELAS_A_LA_VISTA` en 4 cada semana tiene ~120px
                           # de eje, y el peor rótulo —con año, «8 Set – 14
                           # Set ’25»— mide ~113. Hasta ese día iba partido
                           # en el guion en DOS renglones (2026-09-12,
                           # captura del usuario): con cinco velas los
                           # rótulos no entraban en uno y Plotly los torcía
                           # a 45°. `tickangle=0` sigue para que no los
                           # tuerza nunca. La semana elegida, en negrita.
                           ticktext=[
                               ("<b>{}</b>" if i == sem_focus else "{}").format(
                                   _vol_fmt_semana_cabecera(s, anio_ref))
                               for i, s in enumerate(semanas_v)],
                           tickfont=dict(size=11),
                           tickangle=0, automargin=True),
                yaxis=dict(gridcolor=GRIS_BORDE, tickprefix="S/ ",
                           range=[_y0, _y1], fixedrange=True),
                # SIN ARRASTRE: la ventana la mueve el deslizador de abajo, y
                # un gráfico que se corre por su cuenta deja a la tabla de al
                # lado mostrando otras semanas. Lo que lo impide son los dos
                # ejes en `fixedrange`, no esto: medido, `_fullLayout.
                # dragmode` sigue en "pan" (lo pone Streamlit en un gráfico
                # con `on_select`). El clic sobre una vela sigue eligiéndola.
                dragmode=False,
                showlegend=False,
            )

            # ── EL DESLIZADOR DE LA VENTANA: UNA LÍNEA, ARRIBA ───────────
            # Uno por posición de la ventana: su valor es la ÚLTIMA semana a
            # la vista, rotulado con el tramo entero («10 Ago – 13 Set»).
            # La key lleva el insumo, cuántas semanas hay y la ventana
            # vigente: ver `_K_VFIN` para por qué. Sólo si hay más semanas
            # que las que entran.
            #
            # Se dibuja ANTES que el gráfico (2026-09-13, a pedido: «no me
            # parece que ocupe una fila abajo de todo, quizás arriba con una
            # línea botón»): queda entre el título del insumo y las velas, y
            # `estilos/_80_cards.py` lo reduce a una raya con un punto,
            # alineada con el área de dibujo, con el tramo escrito sólo al
            # pasarle el mouse o al arrastrarlo.
            if len(weeks) > _n_v:
                _k_sl = (f"compras_vol_vslider_{_slug(str(prod_sel))}_"
                         f"{len(weeks)}_{semanas_v[_iv1]:%Y%m%d}")
                st.select_slider(
                    "Semanas a la vista",
                    options=list(range(_n_v - 1, len(weeks))), value=_iv1,
                    key=_k_sl, label_visibility="collapsed",
                    format_func=lambda i: _vol_fmt_ventana(
                        semanas_v[i - _n_v + 1], semanas_v[i], anio_ref),
                    on_change=_mover_ventana_velas,
                    args=(_k_sl, tuple(semanas_v)))

            _cfg = {"displaylogo": False, "displayModeBar": False}
            st.plotly_chart(fig, use_container_width=True, key=_chart_key,
                            on_select="rerun", selection_mode="points", config=_cfg)

            w = weeks[sem_focus]
            ini = semanas_v[sem_focus]
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
                delta_txt = (f'<span class="vol-detalle-delta" '
                             f'style="color:{color};">'
                             f'{_sig}{abs(var):.1f}% vs cierre anterior '
                             f'(S/ {_base:,.2f})</span>')
        with col_semana, st.container(key="compras_vol_card_semana"):
            # SU PROPIO FRAGMENT (ver `_tarjeta_compras_semana`): se le pasa
            # todo lo que puede mostrar ya calculado —las compras de la vela
            # elegida y las de toda la ventana, y los dos títulos—, así el
            # «1 semana | 4 semanas» decide adentro sin volver a correr esto.
            _fin_v = semanas_v[_iv1] + pd.Timedelta(days=6)
            _tarjeta_compras_semana(
                filas_semana=w["rows"],
                filas_ventana=[r for i in range(_iv0, _iv1 + 1)
                               for r in weeks[i]["rows"]],
                titulo_semana=f"Semana del {ini:%d/%m} al {fin:%d/%m}",
                titulo_ventana=(f"Semanas del {semanas_v[_iv0]:%d/%m} al "
                                f"{_fin_v:%d/%m}"),
                delta_txt=delta_txt, unidad=unidad, ver_doc=bool(col_docu))
