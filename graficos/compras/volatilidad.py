"""Compras > Volatilidad como pieza propia (regla #718).

Ranking y cierres de cinco semanas, búsqueda fuera del ranking, velas por
semana y puntos por compra. El navegador añade selección de tramos,
proveedores, prioridad por impacto y puente precio/cantidad; sólo la fecha
vuelve a Python. Los ayudantes originales siguen como referencia de tests.
"""

from graficos.movil import css_movil, js_movil
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cortes import MESES_ABR_ES
from tema import (
    GRIS_BORDE, GRIS_TEXTO, GRIS_TEXTO_SUAVE, PALETA_SERIES, TEXTO_PRINCIPAL,
)
from graficos.base import (
    _compras_layout,
    preservar_widgets, selector_fecha_tarjeta,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras._comun import CATEGORIA_SEC
from graficos import periodo
from graficos import alturas

_K_VENTANA = "compras_vol_ventana"
"""Ventana inicial al montar la pieza. La fecha nativa la vuelve a Rango."""

_KEYS_WIDGET = ()
"""Sin widgets nativos en la pieza; el selector de fecha conserva su propia sesión."""

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


_K_CFIN = "compras_vol_cfin"
"""Gemelo de `_K_VFIN` para el grano COMPRA: el ID de la última compra a la
vista, o None (= las más recientes). Una clave APARTE y no la misma con otra
unidad adentro: los dos granos recuerdan su ventana por separado, así ir y
volver no reinterpreta el valor del otro como si fuera propio — una fecha de
lunes leída como id de compra no encuentra nada y la ventana saltaría al
final sin decir por qué."""

_K_GRANO = "compras_vol_grano"
"""El grano de la serie del drill: «Semana» o «Compra» (2026-09-20).

ES CLAVE DE WIDGET, a diferencia de `_K_VENTANA` y `_K_VFIN`, y puede serlo
porque NADIE se lo escribe desde afuera: lo mueve sólo su propio control. La
regla #212 muerde cuando el servidor quiere resetear un widget; acá el
servidor nunca decide el grano.

Va en `_KEYS_WIDGET` por lo de siempre: la escalada de fecha aborta la
corrida antes de dibujarlo y Streamlit lo recolectaría (regla #373)."""

_OP_GRANO = ("Semana", "Compra")
"""Las dos opciones del grano, en este orden. DOS y no tres: «por día» se
evaluó el 2026-09-20 contra el parquet y no llegó a ser una opción — el
96,7% de los días de un insumo tiene una sola compra, así que dibuja el
96,5% de los mismos puntos que el grano Compra, y lo único que hace distinto
es ESCONDER el caso que motivó el cambio (el 16/09 hubo cinco compras de
hielo al mismo proveedor entre S/ 1.95 y S/ 2.97: por día son un punto).
Un tercer estado que cambia el 3% de los puntos y tapa lo interesante no se
agrega."""


def _mover_ventana_compras(key, ids):
    """Gemelo de `_mover_ventana_velas` para el grano Compra."""
    i = st.session_state.get(key)
    if isinstance(i, int) and 0 <= i < len(ids):
        st.session_state[_K_CFIN] = ids[i]
        st.session_state["compras_vol_cfocus"] = None


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
COMPRAS_A_LA_VISTA = 8
"""Gemelo de `VELAS_A_LA_VISTA` para el grano Compra (2026-09-20).

OCHO y no cuatro porque el rótulo mide otra cosa: la vela lleva la semana
entera escrita («24 Ago – 30 Ago», ~95px) y la compra lleva su fecha
(«25/08», ~33px a 11px). Con el área de dibujo en ~440px son 55px por
punto, y entran los dos glifos con aire.

Medido sobre el parquet: un insumo del ranking compra 7,2 veces cada 5
semanas (337 compras / 47 insumos), así que ocho compras son
aproximadamente el mismo tramo de calendario que las cuatro velas. Los dos
granos abren mirando lo mismo, que es lo que hace que alternar se lea como
un zoom y no como un salto."""

MIN_COMPRAS_CV = 5
"""Piso de compras para calcular la dispersión de un insumo.

El mismo de `graficos/compras/__init__.py::_kpis_vistas`, que ya publica
este número en el KPI del rail («su precio varía ±122%»), y por su mismo
motivo: con dos o tres compras el coeficiente de variación es ruido. Que
sean el mismo número no es casualidad ni copia — es que a partir de hoy la
columna «Dispersión» de la tabla y el rótulo del rail miden LO MISMO, que
es lo que cierra la divergencia que el propio comentario de `_kpis_vistas`
admitía («el producto que nombra el rail puede no ser el primero de la
tabla»). Medido el 2026-09-20: coincidían 5 de 8."""

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
    cada semana llega al `sort_values` igual que por el filtro de siempre.

    DESDE EL 2026-09-26 NO HAY BUCLE (regla #537). Eran dos `groupby`
    anidados —producto, y adentro semana— con un `sort_values` por celda:
    el 57 % de la sección, 2,5-3,5 s en la laptop. Ahora es UN orden de
    todas las filas y un `last()` por (producto, semana): 25 ms, el mismo
    resultado sobre el parquet real. El desempate de arriba se conserva a
    propósito: el orden es ESTABLE (compras del mismo día, en el orden del
    parquet), que es lo que hacía el `sort_values` de un grupo chico
    —numpy ordena por inserción debajo de 17 elementos— y lo que hace la
    vela (`_vol_detalle_producto`, que desde ese día lo pide explícito).
    El error de la primera versión no era vectorizar: era ordenar todo con
    un algoritmo que NO respeta el orden de los empates."""
    prods = list(prods)
    tabla = _tabla_cierres(d[d[col_prod].isin(prods)], col_prod, col_punit,
                           col_fecha, semanas)
    return {p: _fila_cierres(tabla, p, len(semanas)) for p in prods}


def _tabla_cierres(d, col_prod, col_punit, col_fecha, semanas):
    """DataFrame producto × semana con el CIERRE de cada semana —el último
    precio válido (> 0) por fecha; mismo día: orden del parquet— y relleno
    hacia adelante en las semanas sin compra. Lo comparten la grilla
    (`_vol_cierres_semanales`) y el ranking (`_vol_candidatos`): tienen
    que medir sobre la MISMA serie (ver el docstring de la primera)."""
    col = pd.Index(semanas)
    v = d[[col_prod, "_semana", col_fecha, col_punit]]
    v = v[v["_semana"].isin(col) & v[col_punit].notna()]
    v = v[v[col_punit] > 0]
    if v.empty:
        return pd.DataFrame(columns=col, dtype=float)
    v = v.sort_values([col_prod, "_semana", col_fecha], kind="stable")
    ultimo = v.groupby([col_prod, "_semana"], sort=False)[col_punit].last()
    return ultimo.unstack("_semana").reindex(columns=col).ffill(axis=1)


def _fila_cierres(tabla, p, n):
    """La fila de un producto como lista, con None donde todavía no hubo
    compra (antes de la primera). Sin fila: n veces None."""
    if p not in tabla.index:
        return [None] * n
    return [None if pd.isna(x) else float(x) for x in tabla.loc[p].tolist()]


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


def _vol_dispersion(precios, minimo=MIN_COMPRAS_CV):
    """Coeficiente de variación (desvío / promedio) de los precios de N
    compras, o None con menos de `minimo` compras válidas.

    ES OTRA PREGUNTA QUE `_vol_score`, no una versión fina de la misma
    (2026-09-20). Aquélla suma las variaciones de un cierre semanal al
    siguiente: mide cuánto se MUEVE el precio en el tiempo. Ésta mide cuánto
    se APARTAN entre sí los precios que se pagaron, sin importar cuándo —
    así que ve lo que la otra no puede ver por construcción: el insumo que
    cierra todas las semanas en el mismo número y adentro se compró a dos
    precios. Medido sobre el parquet: «Limón Criollo» puntúa 0.0 de
    volatilidad semanal y 58% de dispersión, y con el orden de hoy queda
    último de 47.

    El desvío es el MUESTRAL (ddof=1, el default de pandas), para que el
    número sea exactamente el del KPI del rail — ver `MIN_COMPRAS_CV`.

    Devuelve una FRACCIÓN (0.58), no un porcentaje: quien la muestra decide
    cómo escribirla."""
    s = pd.Series([p for p in precios if pd.notna(p) and p > 0], dtype="float64")
    if len(s) < minimo:
        return None
    media = s.mean()
    if not media:
        return None
    return float(s.std() / media)


def _vol_ids_compras(compras):
    """Un id estable por compra: su fecha más el orden dentro de ese día
    («20260901#1»). Devuelve la lista de ids, pareada con `compras`.

    Es el gemelo del "la fecha de la semana, no su posición" de la ventana
    de las velas (2026-09-13), y por el mismo motivo: la POSICIÓN de una
    compra depende de la ventana de la tarjeta y de dónde arranca la serie
    del insumo, así que pasar de 12m a 3m le corría el foco a otra compra.
    La fecha sola no alcanza —el 3,3% de los días tiene más de una compra y
    el 16/09 hubo cinco del mismo proveedor— y el documento tampoco: una
    misma factura puede traer dos líneas del mismo producto."""
    ids, vistos = [], {}
    for r in compras:
        dia = f"{pd.Timestamp(r['fecha']):%Y%m%d}"
        k = vistos.get(dia, 0)
        vistos[dia] = k + 1
        ids.append(f"{dia}#{k}")
    return ids


def _vol_x_compras(fechas):
    """Posición X de cada compra sobre el eje de FECHAS, separando las del
    mismo día para que no se dibujen una encima de otra.

    EL EJE SIGUE SIENDO EL CALENDARIO, y eso es la decisión (2026-09-20). Un
    eje ordinal —una ranura por compra— separaría los grupos gratis, pero
    borra los huecos: tres compras de un martes y la siguiente quince días
    después quedarían a la misma distancia, y esta vista es justamente la
    que se mira para saber cada cuánto se compra.

    El corrimiento NO se mide en horas (el parquet no las trae) ni en una
    fracción fija del día: se mide contra el PASO de la ventana, o sea la
    distancia típica entre dos días con compra. Con ~2,5 días de paso, cinco
    compras del mismo día se reparten ~9px; con una fracción fija del día
    serían 2,6px y volverían a pisarse. El tope de un día es para que un
    grupo nunca invada la fecha vecina."""
    fs = [pd.Timestamp(f).normalize() for f in fechas]
    distintas = sorted(set(fs))
    if len(distintas) > 1:
        pasos = [(b - a).days for a, b in zip(distintas, distintas[1:])]
        pasos = [p for p in pasos if p > 0]
        paso = float(sorted(pasos)[len(pasos) // 2]) if pasos else 1.0
    else:
        paso = 1.0
    ancho = min(0.7 * paso, 1.0)
    cuantas = {}
    for f in fs:
        cuantas[f] = cuantas.get(f, 0) + 1
    vistos, out = {}, []
    for f in fs:
        n = cuantas[f]
        k = vistos.get(f, 0)
        vistos[f] = k + 1
        off = 0.0 if n < 2 else (k - (n - 1) / 2) / (n - 1) * ancho
        out.append(f + pd.Timedelta(days=off))
    return out


def _vol_sobrecosto(compras):
    """Cuánto costó de más comprar a distintos precios, contra el MEJOR
    precio del período: `Σ (precio − mínimo) × cantidad`. Devuelve
    `(sobrecosto, gasto, pct)`, o `(0.0, 0.0, 0.0)` sin datos.

    Es la forma del *price variance* del costeo estándar —«material price
    variance» en la terminología de CIMA, «purchase price variance» en el
    diccionario de ASCM/APICS: (precio real − precio estándar) × cantidad—,
    con una diferencia que hay que decir donde se muestre: el estándar del
    libro es un precio PRESUPUESTADO y acá la base es el mejor precio que se
    pagó de verdad en el período. Por eso es un TECHO y no un ahorro:
    supone que ese precio estaba disponible siempre, e ignora calidad,
    presentación, urgencia y escala. Medido sobre las 5 semanas al
    16/09/2026: S/ 4.655 sobre S/ 99.674 (4,7%), de los que el 68% está en
    insumos que se le compran a dos proveedores o más."""
    filas = [(float(r["precio"]), float(r["cant"] or 0))
             for r in compras
             if r.get("precio") and pd.notna(r["precio"])
             and r.get("cant") is not None and pd.notna(r["cant"])]
    if not filas:
        return 0.0, 0.0, 0.0
    pmin = min(p for p, _ in filas)
    gasto = sum(p * q for p, q in filas)
    sobre = sum((p - pmin) * q for p, q in filas)
    return sobre, gasto, (sobre / gasto * 100 if gasto else 0.0)


_MESES_CORTO = tuple(m.capitalize() for m in MESES_ABR_ES)
"""Los meses de `cortes.py` con la inicial en mayúscula, que es como se
rotulan las columnas de esta grilla ("3-9 Ago").

Derivado y no escrito a mano: hasta el 2026-09-07 era una lista literal acá,
o sea la SEGUNDA lista de meses en español del repo — justo lo que la regla
#241 dice que no debe haber. La capitalización es lo único propio de esta
vista."""


def _vol_colores_proveedor(compras):
    """{proveedor: color} para la serie por compra, en orden de GASTO
    descendente (no alfabético ni de aparición): el proveedor al que más se
    le compra se lleva el morado de la marca, que es el color con el que el
    resto de la app dibuja «lo principal».

    Con más de `len(PALETA_SERIES)` proveedores los últimos repiten color. No
    pasa hoy —el máximo medido en una ventana son tres— y si pasara, el
    proveedor exacto sigue en el hover y en la tabla de al lado."""
    gasto = {}
    for r in compras:
        p = r.get("prov") or "—"
        gasto[p] = gasto.get(p, 0.0) + float(r.get("monto") or 0.0)
    orden = sorted(gasto, key=lambda p: (-gasto[p], p))
    return {p: PALETA_SERIES[i % len(PALETA_SERIES)] for i, p in enumerate(orden)}


def _vol_etiquetas_precio(precios, rango, umbral=0.11):
    """Cuáles de los N puntos llevan su precio escrito al lado: el primero,
    el último, y cualquiera que se aparte del último rotulado en más de
    `umbral` del rango a la vista. Devuelve una lista de bool.

    Es la MISMA regla que ya decide si una vela muestra sus dos precios
    (11% del alto útil ≈ 12px de los ~110 que mide el área de dibujo): dos
    etiquetas más juntas que eso se tocan. Acá hace más falta todavía —
    seis de las ocho compras de un insumo suelen tener el mismo precio, y
    rotularlas todas escribe «7.00» seis veces."""
    if not precios:
        return []
    rng = rango or 1.0
    out = [False] * len(precios)
    ultimo = None
    for i, p in enumerate(precios):
        if ultimo is None or abs(p - ultimo) >= umbral * rng:
            out[i] = True
            ultimo = p
    out[0] = True
    out[-1] = True
    return out


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
    por volatilidad.

    Sin bucle producto × semana desde el 2026-09-26: los cierres salen de la
    misma `_tabla_cierres` que la grilla (regla #537). Era el 25 % de la
    sección —un filtro y un `sort_values` por cada celda— y ahora son 25 ms.
    """
    if d is None or d.empty:
        return {}
    g = d.groupby(col_prod)                     # claves ordenadas, sin NaN
    gasto = g[col_valor].sum()
    semanas_con_compra = g["_semana"].nunique()
    entra = ((gasto >= min_gasto)
             & (semanas_con_compra >= min_cobertura * len(semanas)))
    prods = gasto.index[entra.to_numpy()]
    tabla = _tabla_cierres(d[d[col_prod].isin(prods)], col_prod, col_punit,
                           col_fecha, semanas)
    out = {}
    for prod in prods:
        cierres = _fila_cierres(tabla, prod, len(semanas))
        out[prod] = {"cierres": cierres, "volatilidad": _vol_score(cierres)}
    return out


def _vol_fuera_del_ranking(d, d_rec, q, dentro, col_prod, col_valor,
                           n_semanas, min_gasto=MIN_GASTO,
                           min_cobertura=MIN_COBERTURA):
    """Los insumos que el BUSCADOR encuentra y el ranking deja afuera, con el
    motivo escrito. {producto: {"gasto", "semanas", "motivo"}}, ordenado por
    lo gastado en la ventana entera (`d`), de mayor a menor.

    2026-09-26, a pedido: «que el buscador encuentre cualquier insumo». El
    ranking responde «¿qué se está moviendo?» y para eso pide compras
    regulares y un gasto que importe (`_vol_candidatos`); el buscador
    responde «¿cómo viene el precio de ESTO?», y ahí un piso no tiene nada
    que hacer: «Chocolate 72% Cacao» compró 2 de 5 semanas por S/ 364 y no
    había forma de ver su serie. Los encontrados van DEBAJO del ranking y
    marcados, así el orden de arriba sigue diciendo lo mismo.

    `gasto` y `semanas` se miden sobre `d_rec` —las semanas que mide el
    puntaje— y con la MISMA cuenta que `_vol_candidatos`, porque son la
    respuesta a «¿por qué no está?»: tienen que ser los números que el filtro
    miró. `dentro` son los que sí entraron (no se repiten)."""
    if not q or d is None or d.empty:
        return {}
    hallados = [p for p in d[col_prod].unique()
                if q in str(p).lower() and p not in dentro]
    if not hallados:
        return {}
    rec = d_rec[d_rec[col_prod].isin(hallados)].groupby(col_prod)
    gasto_rec = rec[col_valor].sum()
    semanas_rec = rec["_semana"].nunique()
    gasto_ventana = d[d[col_prod].isin(hallados)].groupby(col_prod)[col_valor].sum()
    # El mismo umbral que `_vol_candidatos` (`>= min_cobertura * n`), escrito
    # como un entero: «4 de 5», no «3,75».
    pide = math.ceil(min_cobertura * n_semanas - 1e-9)
    out = {}
    for p in sorted(hallados, key=lambda p: (-float(gasto_ventana.get(p, 0.0)),
                                             str(p))):
        gasto = float(gasto_rec.get(p, 0.0))
        k = int(semanas_rec.get(p, 0))
        if k == 0:
            motivo = f"sin compras en las últimas {n_semanas} semanas"
        else:
            partes = []
            if k < pide:
                partes.append(f"compró {k} de las {n_semanas} semanas "
                              f"(pide {pide})")
            if gasto < min_gasto:
                partes.append(f"S/ {gasto:,.0f} de gasto "
                              f"(pide S/ {min_gasto:,.0f})")
            motivo = " y ".join(partes)
        out[p] = {"gasto": gasto, "semanas": k, "motivo": motivo}
    return out


def _vol_sin_coincidencias(q, d_full, col_prod, opcion):
    """El aviso de una búsqueda que no encontró nada en la ventana. Distingue
    «no existe» de «existe, pero no se compró en esta ventana»: desde que el
    buscador encuentra cualquier insumo, lo segundo es lo único que puede
    esconder a uno que sí se compró, y se arregla con el desplegable."""
    if d_full is not None and col_prod in d_full.columns and (
            d_full[col_prod].astype(str).str.lower()
            .str.contains(q, regex=False).any()):
        ventana = periodo.etiqueta(opcion) or "el rango elegido"
        if ventana.startswith("últimos"):
            ventana = f"los {ventana}"
        return (f"Ningún insumo con «{q}» se compró en {ventana}. Probá una "
                f"ventana más amplia con el selector del título.")
    return f"Ningún insumo coincide con «{q}»."


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
        # `kind="stable"`: el mismo desempate que la grilla, SIEMPRE. Sin
        # pedirlo, una semana con 17 compras o más del mismo insumo quedaba
        # a merced del quicksort y la vela podía cerrar distinto que la
        # celda (regla #537, y la trampa de «Cachema Entera» del docstring de
        # `_vol_cierres_semanales`).
        sub = g[g["_semana"] == sem].sort_values(col_fecha, kind="stable")
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

def _fig_serie_compras(compras, xs, i0, i1, foco, colores, unidad, y0, y1):
    """La figura del grano COMPRA: un punto por compra, en su fecha.

    `compras` y `xs` son la serie ENTERA del insumo y `i0`/`i1` la ventana a
    la vista; `foco` es un índice absoluto. Recibe todo y dibuja un tramo a
    propósito, por la misma razón que el candlestick dibuja toda la historia
    y mueve el rango del eje (#412): así el `point_index` que devuelve un
    clic es la posición en la SERIE y no en la ventana. Medido en el
    navegador el 2026-09-20 con la primera versión, que sólo recibía el
    tramo: el clic en la última compra a la vista enfocaba la octava compra
    del insumo — y peor, un clic viejo que sobrevive en el estado (la
    selección de `on_select` persiste entre reruns) se re-interpretaba
    contra una ventana distinta después de mover el deslizador.

    Lo que SÍ se mide sobre el tramo, y no sobre la serie: el tamaño de los
    puntos, el rango del eje Y y qué precios llevan rótulo. Son lecturas de
    lo que se ve — con el máximo de la serie entera, una compra grande de
    hace un año dejaría a las ocho de la ventana del mismo tamaño.

    Nació el 2026-09-20 y NO es el candlestick con otro `x`: una compra tiene
    UN precio, así que su vela sería plana siempre. Medido sobre el parquet,
    el 86% de las velas que dibuja el grano Semana ya sale sin cuerpo (el 68%
    entre los ocho primeros del ranking, que es lo que se mira); con el grano
    por compra serían el 100%. Cambiar de grano cambia el MARK, o el gráfico
    dibuja una forma que promete una información que el dato no tiene.

    Lo que codifica cada canal, y por qué:

    · **Posición Y** — el precio unitario, como siempre.
    · **Posición X** — la FECHA REAL, no una ranura por compra. Ver
      `_vol_x_compras`: los huecos entre compras son dato.
    · **Color** — el PROVEEDOR. El 45% de los insumos del ranking le compra
      a dos o más en la misma ventana, con un spread mediano del 27% entre
      los precios medianos de cada uno: sin este canal, el zigzag de
      «Chirimoya» (S/ 7.00 de La Cesta contra S/ 11.48 de Food Retail,
      alternándose) se lee como un precio que se mueve, cuando lo que dice
      es que se le compra lo mismo a dos precios.
    · **Tamaño** — el MONTO de la compra. Sin él, la compra de 1,055 kg de
      «Limón Criollo» a S/ 12.70 (S/ 13 en total) grita igual que una de 50
      kg, y el 16% del sobrecosto medido sale de compras que pesan menos del
      5% de la cantidad del período. El tamaño no es decoración: es lo que
      separa un problema de un caso raro.

    Las cuatro trazas, en orden (la 0 no es negociable: de ella cuelga el
    clic, ver `_compras_volatilidad_drill`):

      0. el BLANCO DEL CLIC — una barra invisible por compra, del ancho de
         su hueco y del alto del área de dibujo, con el hover. Un marcador
         de 8px se clickea peor que una vela plana, que es lo que motivó
         esta traza en el candlestick (2026-09-12).
      1. la línea ESCALONADA (`hv`) que une los puntos: el precio vigente
         hasta la compra siguiente. Punteada y gris — es guía de lectura,
         no un dato medido entre compra y compra.
      2. los PUNTOS.
      3. los PRECIOS escritos (ver `_vol_etiquetas_precio`).

    `y0`/`y1` los calcula el llamador porque son los de la VENTANA a la
    vista, igual que en el candlestick (regla #413)."""
    fig = go.Figure()
    precios = [float(r["precio"]) for r in compras]
    montos = [float(r.get("monto") or 0.0) for r in compras]
    _vis = list(range(i0, i1 + 1))
    _max_monto = max((montos[i] for i in _vis), default=0.0) or 1.0

    # El ancho del blanco del clic: el hueco MÁS CHICO que tiene cada punto
    # con sus vecinos, para que dos barras no se solapen (una compra del
    # mismo día está a una fracción de día de la de al lado). El piso de
    # 0.35 días es para que un punto aislado siga teniendo dónde clickear.
    _anchos = []
    for i, x in enumerate(xs):
        huecos = []
        if i > 0:
            huecos.append((x - xs[i - 1]).total_seconds() / 86400)
        if i < len(xs) - 1:
            huecos.append((xs[i + 1] - x).total_seconds() / 86400)
        _anchos.append(max(min(huecos, default=1.0) * 0.9, 0.35))

    def _hover(r):
        _cant = ("" if r.get("cant") is None or pd.isna(r["cant"])
                 else f" · {r['cant']:,.2f} {unidad}")
        _doc = f" · {r['doc']}" if r.get("doc") and r["doc"] != "—" else ""
        return (f"{pd.Timestamp(r['fecha']):%d/%m/%Y} · S/ {r['precio']:,.2f}"
                f"/{unidad}{_cant}<br>{r.get('prov') or '—'}{_doc}")

    fig.add_trace(go.Bar(
        x=xs, base=[y0] * len(xs), y=[y1 - y0] * len(xs),
        width=[a * 24 * 3600 * 1000 for a in _anchos],
        marker=dict(color="rgba(0,0,0,0)", line=dict(width=0)),
        hovertext=[_hover(r) for r in compras],
        hoverinfo="text", showlegend=False, name="",
    ))
    fig.add_trace(go.Scatter(
        x=[xs[i] for i in _vis], y=[precios[i] for i in _vis],
        mode="lines", line_shape="hv",
        line=dict(color=GRIS_TEXTO_SUAVE, width=1.2, dash="dot"),
        hoverinfo="skip", showlegend=False,
    ))
    # UNA SOLA TRAZA CON COLOR POR PUNTO, y no una por proveedor: la leyenda
    # no sale de Plotly (vive en la fila del deslizador, en HTML, donde no
    # cuesta alto de figura) y una traza por proveedor le cambiaría el
    # número a `curve_number`, del que cuelga el clic.
    fig.add_trace(go.Scatter(
        x=[xs[i] for i in _vis], y=[precios[i] for i in _vis], mode="markers",
        marker=dict(
            color=[colores.get(compras[i].get("prov") or "—", PALETA_SERIES[0])
                   for i in _vis],
            size=[7 + 11 * (montos[i] / _max_monto) ** 0.5 for i in _vis],
            line=dict(
                color=[TEXTO_PRINCIPAL if i == foco else "rgba(0,0,0,0)"
                       for i in _vis],
                width=[1.8 if i == foco else 0 for i in _vis]),
        ),
        hoverinfo="skip", showlegend=False,
    ))
    _rotular = _vol_etiquetas_precio([precios[i] for i in _vis], (y1 - y0))
    _dx = pd.Timedelta(days=max(_anchos[i0], 0.35) * 0.8)
    _lx = [xs[i] + _dx for i, m in zip(_vis, _rotular) if m]
    _ly = [precios[i] for i, m in zip(_vis, _rotular) if m]
    _lt = [f"<b>{precios[i]:,.2f}</b>" for i, m in zip(_vis, _rotular) if m]
    fig.add_trace(go.Scatter(
        x=_lx, y=_ly, text=_lt, mode="text", textposition="middle right",
        textfont=dict(size=11, color=GRIS_TEXTO),
        hoverinfo="skip", showlegend=False, cliponaxis=True,
    ))

    _compras_layout(fig, alto=alturas.MINI_CANDLE_DRILL)
    fig.update_layout(margin=dict(l=10, r=10, t=8, b=2, pad=2))

    # UNA MARCA POR DÍA CON COMPRA, no una por compra: cinco compras del
    # mismo día comparten fecha, y cinco veces «16/09» debajo del mismo
    # grupo no dice nada. En español por `ticktext`, como todo eje de fecha
    # del repo (regla #241).
    _dias = sorted({pd.Timestamp(compras[i]["fecha"]).normalize()
                    for i in _vis})
    _x0, _x1 = xs[i0], xs[i1]
    _span = max((_x1 - _x0).total_seconds() / 86400, 1.0)
    fig.update_layout(
        xaxis=dict(
            gridcolor=GRIS_BORDE, showgrid=False, fixedrange=True,
            # A la derecha, sitio para la etiqueta del último punto: el
            # mismo problema que el candlestick resolvió estirando el rango
            # (2026-09-13), y la misma solución.
            range=[_x0 - pd.Timedelta(days=_span * 0.05 + 0.3),
                   _x1 + pd.Timedelta(days=_span * 0.14 + 0.5)],
            tickmode="array", tickvals=_dias,
            ticktext=[f"{d:%d/%m}" for d in _dias],
            tickfont=dict(size=11), tickangle=0, automargin=True),
        yaxis=dict(gridcolor=GRIS_BORDE, tickprefix="S/ ",
                   range=[y0, y1], fixedrange=True),
        dragmode=False, showlegend=False,
    )
    return fig



# La fecha sigue siendo el control compartido; el resto vive en la pieza.
from pathlib import Path
from graficos.base import rango_tarjeta

_PIEZA = st.components.v2.component(
    "compras_volatilidad",
    css=css_movil((Path(__file__).parent / "volatilidad.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent.parent / "_xlsx.js").read_text(encoding="utf-8")
    + (Path(__file__).parent / "volatilidad.js").read_text(encoding="utf-8")),
)
_K_CACHE = "_cp_vol_pieza_cache"


@st.fragment
def _compras_volatilidad_drill(d, col_prod, col_prov, col_punit, col_fecha,
                               col_valor, col_cant, col_um, col_moneda=None,
                               d_full=None, col_docu=None):
    """Firma conservada (#357); sólo la fecha pide otra corrida (#718)."""
    from graficos.compras import volatilidad_datos as datos

    if not (col_prod and col_punit and col_fecha and col_valor):
        st.info("Faltan columnas (Producto, Precio unitario, Fecha o Valor) para calcular volatilidad.")
        return
    if st.session_state.pop("_cp_vol_atajo_pendiente", False):
        st.session_state[_K_VENTANA] = periodo.HEREDA
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")
    with st.container(key="cp_vol_pieza_wrap"):
        with st.container(key="cp_vol_fecha"):
            ctx = selector_fecha_tarjeta(
                "cp_vol", "_cp_vol_atajo_pendiente", label="Elegir fechas",
                categoria=CATEGORIA_SEC["compras_sec_volatilidad"])
        rango = rango_tarjeta(CATEGORIA_SEC["compras_sec_volatilidad"], ctx) if ctx else None
        cols = dict(prod=col_prod, prov=col_prov, precio=col_punit, fecha=col_fecha,
                    valor=col_valor, cant=col_cant, um=col_um, moneda=col_moneda, doc=col_docu)
        filtros = {rot: [str(v) for v in (st.session_state.get(k) or [])]
                   for rot, k in (("Familia", "compras_graf_filtro_fam"),
                                  ("Subfamilia", "compras_graf_filtro_sub"))}
        firma = (id(d), d.shape, id(d_full), None if d_full is None else d_full.shape,
                 str(rango), tuple(cols.items()), repr(filtros),
                 st.session_state.get(_K_VENTANA, "12m"))
        cache = st.session_state.get(_K_CACHE)
        if cache is None or cache[0] != firma:
            mensaje = datos.armar(d, d_full, cols, rango, firma[-1], filtros=filtros)
            st.session_state[_K_CACHE] = (firma, mensaje)
        else:
            mensaje = cache[1]
        if mensaje is None:
            st.info("Sin fechas válidas para comparar precios.")
            return
        _PIEZA(key="cp_vol_pieza", data=mensaje, width="stretch")
