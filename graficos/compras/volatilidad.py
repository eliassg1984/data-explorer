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
    _card, _compras_layout, _compras_truncar, _slug, nombre_propio,
    preservar_widgets, selector_fecha_tarjeta,
)
from graficos.compras._comun import (
    CATEGORIA_SEC, COLUMNAS_DRILL, GAP_DRILL, PARR, _first_point,
)
from graficos import periodo
from graficos import alturas
from tablas.compras_volatilidad import (
    ALTO_FILA as ALTO_FILA_RANK, renderizar_ranking_volatilidad,
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

_KEYS_WIDGET = ("compras_vol_q",)
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
"""Tope de semanas de la ventana, y NO es un gusto: es el ancho de la celda.

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
    None si hay menos de `minimo` semanas distintas en total."""
    fechas = fechas.dropna()
    if fechas.empty:
        return None
    inicios = (fechas - pd.to_timedelta(fechas.dt.weekday, unit="D")).dt.normalize()
    semanas = sorted(pd.to_datetime(inicios.unique()))
    if len(semanas) < minimo:
        return None
    return semanas[-maximo:]


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


def _vol_fmt_semana_corta(ini):
    """La semana nombrada por su lunes: "27 Jul". Es la etiqueta de la
    CABECERA de la grilla y también la del eje X del candlestick — el mismo
    texto en los dos sitios, a propósito.

    Nació el 2026-09-07, al mudar el drill al costado: con la columna en
    ~50px, "27 Jul - 2 Ago" envolvía en CUATRO renglones y la cabecera de la
    grilla pasaba de 45 a 96px — 51px que salían de las filas. El rango
    entero sigue estando en el tooltip de cada celda, que es donde hace
    falta leerlo con precisión."""
    return f"{ini.day} {_MESES_CORTO[ini.month - 1]}"


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
                          col_cant, semanas):
    """OHLC + filas de compra (fecha, proveedor, cantidad, precio) por
    semana, para UN producto ya elegido."""
    g = d[d[col_prod] == prod]
    weeks = []
    prev_close = None
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
                # pueda desalinear. Ver `base.py::nombre_propio`.
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

    # ── Tabla ranking (semáforo, buscador, tooltip + clic en fila) ───────
    # El selector de ventana comparte RENGLÓN con el título (2026-09-05, a
    # pedido). Vivía en una fila propia arriba de la tarjeta: un renglón
    # entero para un control de 90px. Es el mismo patrón que la cabecera de
    # «Vs año pasado» (`vap_fila_hdr`): el título deja de salir por
    # `_card(titulo_arriba=True)` y pasa a ser el primer ítem de una fila
    # flex, con la raya divisoria mudada del `<p>` a la fila — las reglas
    # genéricas las comparten las dos en `estilos/_80_cards.py`.
    #
    # Por eso el CÁLCULO entero se mudó ADENTRO de la tarjeta: la ventana
    # hay que leerla antes de recortar `d`, y el widget que la lee ahora se
    # dibuja acá. Los `return` tempranos quedan dentro de la tarjeta, que de
    # paso es mejor: el mensaje sale bajo la cabecera que tiene el selector
    # con el que se arregla, y no en un bloque suelto sin contexto.
    with _card("compras_vol"):
        with st.container(key="vol_fila_hdr"):
            st.markdown('<p class="chart-card-hdr vol-hdr">Insumos ordenados '
                        'por volatilidad</p>', unsafe_allow_html=True)
            with st.container(key="vol_hdr_periodo"):
                _prev_vol = st.session_state.get(_K_VENTANA, "12m")
                if _prev_vol not in periodo.OPCIONES:
                    _prev_vol = "12m"
                _op_vol = periodo.selector(f"compras_vol_periodo_{_prev_vol}",
                                           default=_prev_vol, widget="lista")
            st.session_state[_K_VENTANA] = _op_vol
            if _op_vol != periodo.HEREDA and d_full is not None:
                d = periodo.recortar(d_full, col_fecha, _op_vol)

            # ── El buscador, también en la fila del título ───────────────
            # 2026-09-07: vivía en un renglón propio debajo de la cabecera,
            # un `st.columns([1, 2])[0]` que gastaba 56px (40 del campo +
            # 16 de gap) para un input de un tercio de ancho. Mismo
            # movimiento —y mismo motivo— que el buscador de «Vs año
            # pasado» (`vap_hdr_buscar`, 2026-09-02): esta vista tiene que
            # entrar ENTERA en una pantalla y cada renglón de cromo se lo
            # come al ranking.
            with st.container(key="vol_hdr_buscar"):
                _q = st.text_input("Buscar insumo", key="compras_vol_q",
                                   placeholder="Buscar insumo…",
                                   label_visibility="collapsed").strip().lower()

            # ── Cómo se lee la vista: un ícono, no dos captions ──────────
            # Acá había DOS `st.caption` EN FLUJO —uno bajo la grilla y
            # otro bajo el candlestick— que sumaban ~83px con sus gaps para
            # explicar algo que se lee UNA vez. Pasan a un popover de sólo
            # ícono, exactamente como `vap_hdr_ayuda`.
            #
            # La primera línea (familia, nº de semanas y los dos umbrales)
            # va por un HUECO: `n_sem` se sabe ~40 líneas más abajo, cuando
            # ya se recortó `dd` a las semanas con datos. Mismo mecanismo
            # que el aviso del mes parcial de vs_ano_pasado.py.
            #
            # El párrafo de los DOS PRECIOS no es relleno: la segunda
            # línea de cada celda («110.17 → 169.41») son cierres de semanas
            # DISTINTAS —el de la anterior y el de ésta— y leerlos como si
            # los dos fueran de la semana del encabezado es la confusión que
            # reportó el usuario el 2026-09-07 con captura.
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
                            "anterior, así que los dos precios de la segunda "
                            "línea son de semanas DISTINTAS — el tooltip de "
                            "la celda las nombra. El % va redondeado a "
                            "entero; los precios, no. Las compras "
                            "intermedias se ven a la derecha, en el "
                            "candlestick y en su tabla."
                            + PARR
                            + "Clic en una fila para ver su candlestick; "
                            "clic en una vela, para las compras de esa "
                            "semana.")

            # ── El segmentador de fecha, último ítem de la fila ──────────
            # 2026-09-06, a pedido. Es el MISMO componente que ya tienen
            # los dos rankings y la vista Semanal
            # (`base.py::selector_fecha_tarjeta`): trigger con el rango
            # escrito + panel con los cuatro atajos y la escala de tiempo
            # (Días/Meses/Años + riel). No es un filtro paralelo — escribe
            # la clave canónica del rango, así que mover la fecha acá la
            # mueve en toda la página apilada.
            #
            # Va ÚLTIMO en la fila: en las otras tres tarjetas la fecha es
            # el ancla derecha, y que sea la misma cosa en las cuatro es
            # justamente lo que hace que se lea como un solo control.
            #
            # LOS DOS CONTROLES SON UNO SOLO, leídos de izquierda a
            # derecha: la ventana elige el GRANO ("últimos 12 meses") y la
            # fecha elige un rango EXACTO. Por eso el trigger no muestra la
            # fecha de la franja mientras la ventana mande —mostraría un
            # dato que esta tarjeta no está usando— sino la ventana misma,
            # y por eso tocar el panel devuelve la ventana a "Rango"
            # (arriba, en la escalada). Con eso las dos mitades nunca dicen
            # cosas distintas.
            selector_fecha_tarjeta(
                "cp_vol", "_cp_vol_atajo_pendiente",
                label=(periodo.etiqueta(_op_vol).capitalize() or None
                       if _op_vol != periodo.HEREDA else None),
                categoria=CATEGORIA_SEC["compras_sec_volatilidad"])

        dd = d.copy()
        if col_moneda and col_moneda in dd.columns:
            dd = dd[dd[col_moneda].astype(str).str.strip().isin(["01", "1"])]
        dd[col_fecha] = pd.to_datetime(dd[col_fecha], errors="coerce")
        dd[col_punit] = pd.to_numeric(dd[col_punit], errors="coerce")
        dd[col_valor] = pd.to_numeric(dd[col_valor], errors="coerce").fillna(0)
        dd = dd.dropna(subset=[col_fecha, col_prod])
        dd = dd[dd[col_prod].astype(str).str.strip() != ""]

        semanas = _vol_semanas_ventana(dd[col_fecha])
        if not semanas:
            st.info(f"Necesitás al menos 4 semanas de compras en "
                    f"{periodo.etiqueta(_op_vol) or 'el rango elegido'} para "
                    f"armar un candlestick. Probá una ventana más amplia con el "
                    f"selector del título.")
            return
        dd["_semana"] = (dd[col_fecha] - pd.to_timedelta(
            dd[col_fecha].dt.weekday, unit="D")).dt.normalize()
        dd = dd[dd["_semana"].isin(semanas)]

        candidatos = _vol_candidatos(dd, col_prod, col_punit, col_fecha, col_valor, semanas)
        if not candidatos:
            st.info(f"Ningún insumo tiene compras regulares (≥75% de las "
                    f"semanas) y gasto relevante (≥ S/ 400) en "
                    f"{periodo.etiqueta(_op_vol) or 'el rango elegido'}.")
            return

        ranking = sorted(candidatos.items(), key=lambda kv: -kv[1]["volatilidad"])

        n_sem = len(semanas)
        labels_todas = [_vol_fmt_rango_semana(s) for s in semanas]
        cols_sem = labels_todas[1:]

        ranking_vista = [(p, info) for p, info in ranking
                         if not _q or _q in str(p).lower()]

        prod_focus = st.session_state.get("compras_vol_focus")
        if prod_focus not in {p for p, _ in ranking}:
            prod_focus = None

        # ── EL RANKING A LA IZQUIERDA, EL DRILL A LA DERECHA ─────────────
        # 2026-09-07, a pedido y sobre una maqueta a escala. Apilados, el
        # alto de la tarjeta era la SUMA de los dos y el ranking tenía que
        # encogerse a 6 filas para que el candlestick entrara en la
        # pantalla. Al lado, el alto es el MÁXIMO de los dos: los ~290px
        # que ocupaba el drill vuelven a la grilla, que pasa a mostrar 10.
        #
        # `COLUMNAS_DRILL` y no un literal: es la proporción con la que
        # parten sus filas los drills de Proveedor y de Producto, y las
        # tres vistas se leen apiladas en la misma página. Un eje distinto
        # a media página es el bug que hizo nacer la constante (regla #145).
        #
        # El precio de esta fila está medido y es real: la columna-semana
        # baja de 85 a ~50px, así que la segunda línea de la celda (los dos
        # cierres) sólo se dibuja donde entra — lo decide la propia celda
        # en `tablas/compras_volatilidad.py`, no este módulo.
        col_rank, col_drill = st.columns(COLUMNAS_DRILL, gap=GAP_DRILL)

        if not ranking_vista:
            st.info(f"Ningún insumo coincide con «{_q}».")
        else:
            filas = []
            for prod, info in ranking_vista:
                cierres = info["cierres"]
                fila = {"Insumo": _compras_truncar(str(prod), 34),
                        "__insumo_full": str(prod)}
                for i, col in enumerate(cols_sem):
                    prev, cur = cierres[i], cierres[i + 1]
                    delta = (None if (prev is None or cur is None or not prev)
                             else (cur - prev) / prev * 100)
                    fila[col] = delta
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
            with col_rank:
                _clicked = renderizar_ranking_volatilidad(
                    tv, cols_sem, labels_todas[:-1],
                    [_vol_fmt_semana_corta(s) for s in semanas[1:]],
                    altura=alturas.por_filas(len(tv), px_fila=ALTO_FILA_RANK,
                                             extra=40, minimo=0,
                                             rol=alturas.RANKING_CON_DRILL),
                    key="compras_vol_rank_grid",
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
            f"Familia Alimentos · **{n_sem} semanas** · sólo insumos con "
            "≥ S/ 400 de gasto y compras en al menos el 75% de las semanas "
            "del rango.")

        unidad_raw = str(dd.loc[dd[col_prod] == prod_sel, col_um].mode().iat[0]) \
            if col_um and col_um in dd.columns and not dd.loc[dd[col_prod] == prod_sel, col_um].empty \
            else "kg"
        unidad = {"KILOS": "kg", "KG": "kg", "LITROS": "L", "LT": "L", "UND": "und"}.get(
            unidad_raw.upper(), unidad_raw.lower())

        weeks = _vol_detalle_producto(dd, prod_sel, col_prod, col_punit, col_fecha,
                                      col_prov, col_cant, semanas)

        with col_drill:
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
            # de la columna (la cuenta entera, en `estilos/_80_cards.py`).
            # Lo que se abrevia vuelve en el `title=`, que es un tooltip
            # nativo y no cuesta pixeles.
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
                f'<span title="Volatilidad: suma de las variaciones % semanales">'
                f'<i>Volatilidad</i><b>{vol_total:.1f}</b></span>'
                f'</span></div>',
                unsafe_allow_html=True,
            )

            # El candlestick y la tabla de la semana, APILADOS: los dos son la
            # columna derecha de la fila, así que ya no compiten por el ancho
            # entre sí sino con el ranking. El alto sale de un rol propio
            # (`MINI_CANDLE_DRILL`, 200) y no de MINI (240): además de
            # apoyar a una tabla, es el tercero de CUATRO bloques apilados
            # en media columna. La cuenta de esa columna está en
            # `graficos/alturas.py`.

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=semanas, open=[w["o"] for w in weeks], high=[w["h"] for w in weeks],
                low=[w["l"] for w in weeks], close=[w["c"] for w in weeks],
                increasing=dict(line=dict(color=ERROR), fillcolor=ERROR),
                decreasing=dict(line=dict(color=EXITO), fillcolor=EXITO),
                hovertext=[f"Semana del {s:%d/%m} · abre S/ {w['o']:.2f} · máx S/ {w['h']:.2f} "
                          f"· mín S/ {w['l']:.2f} · cierra S/ {w['c']:.2f}"
                          for s, w in zip(semanas, weeks)],
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
            # `ticktext` y no `tickformat`: acá el eje tiene ocho puntos
            # conocidos —los lunes de las ocho semanas— y marcarlos todos
            # es lo que hace que una vela se pueda buscar por su fecha.
            fig.update_layout(
                xaxis=dict(gridcolor=GRIS_BORDE, showgrid=False,
                           rangeslider=dict(visible=False),
                           tickmode="array", tickvals=semanas,
                           ticktext=[_vol_fmt_semana_corta(s) for s in semanas]),
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

            delta_txt = ""
            if sem_focus > 0 and weeks[sem_focus - 1]["c"]:
                var = (w["c"] - weeks[sem_focus - 1]["c"]) / weeks[sem_focus - 1]["c"] * 100
                color = ERROR if var > 0 else (EXITO if var < 0 else GRIS_TEXTO)
                delta_txt = (f' <span style="color:{color}; font-weight:700;">'
                            f'{"+" if var >= 0 else "−"}{abs(var):.1f}% vs semana anterior</span>')
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
                st.dataframe(sty_p, use_container_width=True, hide_index=True,
                            height=alturas.por_filas(
                                len(tp), px_fila=34, extra=60, minimo=0,
                                rol=alturas.PANEL_BAJO_FIGURA))
