"""graficos.compras.semanal - drill "Semanal": una barra por período.

Vivía inline en `graficos/compras/__init__.py` (unas 230 líneas dentro del
dispatcher) hasta el 2026-09-04. Se saca a su propio módulo por el mismo
criterio que el resto —`__init__.py` es el dispatcher, un drill por
fichero— y además por una razón medida: al sumarle el selector de fecha de
la tarjeta hizo falta que el drill fuera un `@st.fragment` PROPIO, no el de
`base.py::seccion_perezosa` que envuelve a cada sección de la pila.

Por qué no alcanzaba un `@st.fragment` anidado dentro del dispatcher:
`st.rerun(scope="app")` disparado desde el fragment de la SECCIÓN aborta el
render de esa misma sección, y el delta que el cliente deja de recibir es
justo el suyo — la franja y las otras dos tarjetas se actualizaban y ésta
se quedaba un gesto atrás, con el rango viejo en el trigger y la barra que
ya no entra todavía dibujada en el gráfico. Con el drill en un fragment
aparte, el que aborta es el de adentro y el que redibuja es el de afuera,
que es como ya funcionaban Proveedor, Producto y Volatilidad.

2026-09-08 — LOS PUNTOS SE PODÍAN VER PERO NO TOCAR, y la causa era el
dato, no el tamaño del marcador. Reportado como "los puntos que son los
documentos son casi imposibles de seleccionar". Medido con DuckDB contra
`compras.parquet` (51.574 filas, 2023-01 a 2026-09) — compras distintas por
semana:

    todas las familias            media 93   p90 122   max 158
    las 5 familias de entrada     media 69   p90  93   max 118
    UN producto elegido           media 1,4            max  18

O sea: 69 puntos apilados sobre la MISMA x (el centro de la categoría), la
mayoría amontonados contra el cero, y con el rango en "todo el histórico"
son 192 barras en el lienzo. Ningún tamaño de marcador arregla eso. Lo que
lo arregla es la última fila de la tabla: con un producto elegido son 1,4
puntos por semana. De ahí que el selector de producto y la selectividad de
los puntos sean el MISMO cambio y no dos, y de ahí estas tres piezas, en
orden de cuánto aportan:

  1. Familia y Producto propios de la tarjeta (el de producto ordena por
     valor de compra y ofrece además "Top N por valor").
  2. Tope de compras dibujadas por período, las mayores por valor — las
     chicas son justamente las que se amontonan contra el cero y las que
     nadie va a querer clickear. Cuántas caben lo decide `_tope_puntos()`
     contra los píxeles que hay, no un número fijo: ver su docstring, que
     trae la segunda medición del día (la que tiró abajo el tope fijo).
  3. Reparto DENTRO del slot de la barra (`_ANCHO_SLOT`): dejan de caer
     todas en el centro, así que dos compras del mismo período ya no se
     tapan entre sí.

Y una cuarta que no es de puntería sino de recompensa: clic en un punto
enfoca ESA compra. Antes hacía exactamente lo mismo que clickear la barra
—las dos trazas devuelven la clave del período—, o sea apuntar al punto no
servía para nada.

2026-09-14 — ETIQUETAS Y DOS TABLAS (regla #440). En Semana, Mes y Año
cada barra lleva su total escrito encima, cuando entra (`_plan_etiquetas`).
Y el detalle de abajo dejó de ser UN `st.dataframe` con todas las líneas
del período: son dos AgGrid, los DOCUMENTOS del período y, al costado, las
LÍNEAS del documento elegido (`tablas/compras_semanal.py`).

2026-09-19 (2) — LA ZONA DE ABAJO SE ALTERNA (regla #476). El detalle del
período dejó de ser lo único que puede aparecer debajo del gráfico: un
toggle —«Detalle» / «Resumen», en el renglón que antes gastaba solo el
caption— cambia las dos grillas por UNA con una fila por BARRA, en el
orden del eje y con lo que dice su etiqueta (total, documentos, variación)
más el % de la vista y las líneas. «Resumen» no necesita foco: son todas
las barras.

2026-09-19 — SIN PUNTOS, CON VARIACIÓN (regla #470). Todo lo de arriba
sobre los puntos es historia: Mes y Año pasaron a la barra partida, como
Día y Semana, y no queda ninguna traza de compras sueltas. La etiqueta de
cada barra suma, debajo del total, cuántos documentos la forman y —en Día,
Semana y Mes— la variación contra la barra anterior, con «parcial» donde
el rango corta el período. La semana se nombra «14–20 set» y no
«2026-S38». Y la cabecera suma dos filtros: Subfamilia y Proveedor.
"""

import hashlib
from datetime import date, timedelta
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
from tema import (
    ADVERTENCIA_TEXTO, ERROR, EXITO, GRIS_BORDE, GRIS_TEXTO, SERIE_PRINCIPAL,
    SERIE_TRAMOS, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import (
    _compras_layout, _compras_truncar, preservar_widgets, rango_tarjeta,
    scope_rerun,
)
from graficos.compras._comun import (
    CATEGORIA_SEC, GAP_DRILL, _first_point, _periodo_serie, documento_legible,
    selector_fecha_tarjeta,
)
# EL NOMBRE DEL PROVEEDOR SE ESCRIBE COMO NOMBRE PROPIO, no como lo grita el
# ERP (2026-09-20, a pedido: «pongamos el nombre del proveedor en
# minúscula»). Es la ÚNICA del repo y es sólo para MOSTRAR: la clave con la
# que esta vista compara (`dd["compra"]`) sigue llevando el nombre crudo.
# Ver `_etiquetas_proveedor.nombre_propio` y `arquitectura.md` #379.
from graficos.compras._etiquetas_proveedor import nombre_propio
from tablas.compras_semanal import (
    renderizar_documentos_semanal, renderizar_lineas_semanal,
    renderizar_periodos_semanal,
)
from utils import fmt_k


# ===========================================================================
# CENTINELAS DE LOS DOS SELECTORES
# ===========================================================================
# Son CENTINELAS, no valores del parquet: se comparan por igualdad contra lo
# que devuelve el widget. Mismo criterio —y misma trampa— que `_FAM_TODAS` de
# `vs_ano_pasado.py`: una familia que se llamara literalmente "Todas" lo
# rompería, y por eso el texto lleva el sustantivo. Ninguna familia ni
# producto del parquet empieza con "Todas las" ni con "Top ".
_FAM_TODAS = "Todas las familias"
_SUB_TODAS = "Todas las subfamilias"
_PROV_TODOS = "Todos los proveedores"
_PROD_TODOS = "Todos los productos"

_GRAN_DEFAULT = "Semana"
"""Con qué granularidad abre la vista.

Desde el 2026-09-17 el control es un `st.segmented_control(required=True)`
y ya no se puede soltar: el `or _GRAN_DEFAULT` del drill quedó como red
para el caso en que la cabecera no llegue a dibujarse.

«Semana» desde el 2026-09-20, a pedido («que inicie con la agrupación por
semana»). Es donde había estado hasta el 2026-09-12, cuando pasó a «Por
documento» junto con abrir en el mes en curso — el argumento de entonces
(un mes por documento son ~30-60 barras legibles, doce meses serían
cientos) sigue siendo cierto y no se pierde: el rango de la tarjeta no
cambia (`SEC_ABRE_EN_EL_MES` en `_comun.py`, un mes corrido), y sobre ese
mes «Semana» son 4-5 barras. Lo que cambia es con qué pregunta abre: en
qué semanas se gastó, no qué documentos entraron.

UNA constante para los dos usos a propósito: con el default en el widget y
el fallback escrito aparte, soltar la píldora (cuando era `st.pills`)
mostraba otra granularidad que la del arranque."""

_GRAN_OPCIONES = ("Día", "Semana", "Mes", "Año", "Por documento")
"""Las granularidades, en el orden en que se leen: de la más fina a la más
gruesa, y el documento al final porque no es un período sino una compra."""

_GRAN_ROTULO = {"Por documento": "Documento"}
"""Lo que el toggle ESCRIBE, cuando no es el valor. «Por documento» sigue
siendo el valor —lo comparan ocho `if` del drill y lo guarda la sesión—,
pero en un toggle lineal el «Por» sobra: los otros cuatro no lo llevan, y
un botón más largo que sus vecinos se lee como otra cosa."""

_MODO_DETALLE = "Detalle"
_MODO_RESUMEN = "Resumen"
_MODO_OPCIONES = (_MODO_DETALLE, _MODO_RESUMEN)
_MODO_DEFAULT = _MODO_DETALLE
"""Los dos modos de la zona de abajo (2026-09-19, regla #476).

«Detalle» son las dos grillas de siempre —los documentos del período que se
toca en el gráfico y las líneas del que se elija—, y necesita una barra en
foco: sin ella la zona está vacía y lo dice. «Resumen» es el GRÁFICO
escrito como tabla: una fila por barra, en el orden del eje, más su TOTAL;
no depende del foco, así que la zona nunca está vacía en ese modo.

Los nombres NO son «Documentos» y «Por período» (el primer intento): en la
granularidad «Por documento» cada barra ES un documento y los dos rótulos
habrían dicho lo mismo. «Detalle» y «Resumen» se sostienen en las cinco.

El default es Detalle porque es lo que la vista hacía hasta hoy: un modo
nuevo no cambia con qué abre una vista que la gente ya conoce."""

_AYUDA_MODO = (
    "Qué se ve debajo del gráfico. **Detalle**: los documentos de la barra "
    "que toques y las líneas del que elijas. **Resumen**: una fila por "
    "barra —con su total, su % de la vista, sus documentos y su "
    "variación— más el total de todas."
)

_KEYS_WIDGET = ("compras_sem_gran", "compras_sem_familia",
                "compras_sem_subfamilia", "compras_sem_proveedor",
                "compras_sem_producto", "compras_sem_modo")
"""Los controles de la tarjeta, para que la escalada no se los lleve.

Eran tres hasta el 2026-09-19, cuando se sumaron Subfamilia y Proveedor;
el sexto, el modo de la zona de abajo, llegó el mismo día. Los cinco
primeros viven en la cabecera y el último debajo del gráfico: lo que los
junta acá no es dónde están sino de quién son — todos son widgets de ESTE
fragment, y el `rerun` los recolecta a todos por igual.

No es una lista decorativa: la consume `preservar_widgets` en el
`st.rerun(scope="app")` de más abajo, y sin ella mover la fecha de la
cabecera devolvía la granularidad a su default —«Semana» entonces, con la
píldora «Por documento» todavía marcada en pantalla— y los dos filtros a
"todas/todos".
Ver `graficos/base.py::preservar_widgets` y `arquitectura.md` regla #373.
`test_graficos.py::_pruebas_widgets_de_fragment_escalado` falla si aparece
un cuarto control acá arriba y nadie lo agrega a esta tupla."""

_TOPS = (5, 10, 20)
"""Los "Top N por valor" que ofrece el selector de producto.

Van DENTRO de la lista de productos y no en un control aparte, que era la
otra forma de leer el pedido ("un buscar o selector de productos
minimalista, con opcion de top por valor de compra"). Un control aparte
serían dos widgets en una fila que ya tiene cuatro items; como opciones de
la misma lista, el mismo desplegable cubre los tres casos —todos, un
conjunto top-N, un producto suelto— y el buscador propio de `st.selectbox`
sigue filtrando sobre él."""

# Opacidad de lo que NO está en foco cuando hay un detalle abierto: la misma
# con que Plotly atenúa lo no seleccionado (`DESELECTDIM`), porque la marca
# a mano reemplaza a la selección de Plotly (ver «EL FOCO SE MARCA A MANO»).
_ATENUADO = 0.2

_LIENZO_PX = 820
"""Ancho útil del lienzo de esta figura, en píxeles. MEDIDO, no estimado.

Con la tarjeta a todo el ancho de la fila del drill, leyendo
`xaxis._length` de la figura ya montada en el navegador:

    viewport 1280   tarjeta 915px   ->  lienzo 818  (la laptop)
    viewport 1440   tarjeta 1049px  ->  lienzo 988

Se toma el caso chico, que es donde se mira la app. Existe porque el
servidor no sabe el ancho del cliente —`_es_movil` distingue móvil de
escritorio por User-Agent, no da píxeles— y tres cuentas necesitan un
número: cuánto entra en la etiqueta de una barra (`_plan_etiquetas`), cada
cuánto se rotula el eje y el calendario de los días. Errar por defecto es
lo barato: sobra aire, nada se pisa.

(Hasta el 2026-09-19 lo usaba además `_tope_puntos`, que decidía cuántos
puntos de compra cabían en una barra de Mes y Año. Se fue con los puntos.)"""

# ── Lo que paga la fila de modo (2026-09-19, regla #476) ───────────────────
# La fila que elige Detalle/Resumen es nueva, así que nadie le había hecho
# lugar: sus píxeles salen de la figura cuando no hay tabla y de la tabla
# cuando la hay, para que la tarjeta siga midiendo lo que la de «Vs año
# pasado» en los dos estados (`alturas.SEMANAL_SOLO`, regla #398). Es el
# mismo mecanismo que `FRANJA_CTRL_SERIE` en «Vs año pasado» y por el mismo
# motivo: restar acá o crecer allá son las dos únicas salidas.
_ALTO_FIG_SOLO = alturas.SEMANAL_SOLO - alturas.FRANJA_MODO_SEMANAL
_ALTO_TABLA = alturas.SEMANAL_TABLA - alturas.FRANJA_MODO_SEMANAL


# ===========================================================================
# LA BARRA SE PARTE EN TRES (2026-09-17, regla #453)
# ===========================================================================
# Reemplaza al punto negro. El punto decía «ésta es la compra mayor» y no
# decía nada más; el reparto del período —una compra grande o quince
# chiquitas— quedaba fuera del gráfico.
#
# DÍA Y SEMANA SÍ, MES Y AÑO NO. Medido con DuckDB contra `compras.parquet`,
# el reparto MEDIO de cada período entre los tres tramos (y el rango del
# primero, que es el que puede quedar fino):
#
#     Día      42,9 / 38,5 / 21,4 %   la mayor entre 18,1 y 73,2   (30 per.)
#     Semana   13,7 / 17,6 / 68,7 %   la mayor entre  6,5 y 28,7   (53 per.)
#     Mes       4,7 / ...                                          — no entra
#
# En Mes la mayor es el 4,7 % de la barra: 3px que no se leen. En Semana el
# peor caso es 6,5 %, pero sobre barras semanales —que son sumas de ~61
# compras y llegan altas— eso sigue dando ~8px. Entra.
#
# LO QUE CAMBIA ENTRE LAS DOS NO ES SI SE VE, ES QUÉ DICE. En Día manda la
# mayor (43 %) y la barra se lee «hubo una compra grande»; en Semana manda la
# cola (69 %) y se lee «la semana son muchas compras medianas». Las dos son
# ciertas y las dos son la misma pregunta —de qué está hecho este período—,
# así que van con el mismo dibujo. Semana se sumó a pedido el 2026-09-17,
# mirando la vista publicada: ahí los 8 puntos caían todos entre 0 y 5k
# contra barras de 28-33k, o sea amontonados contra el cero, que es el bug
# que el tope de `_tope_puntos` vino a mitigar y no a curar.
#
# POR QUÉ TRES Y NO UNA POR COMPRA. El día mediano trae 8,8 compras (mediana
# histórica 13, máximo 46) y la cola a partir de la cuarta vale el 5 % del
# total repartido entre todas: apilar una por compra da segmentos sub-píxel
# y las líneas divisorias se los comen. Tres tramos es el corte más fino que
# los datos sostienen.
#
# EL CLIC NO CAMBIA, y eso NO es una renuncia: la tabla de la derecha ya
# abría en la compra mayor del período (`_sel = _docs["compra"].iloc[0]`),
# así que en Día —donde el tope de puntos daba 1— clickear el punto hacía lo
# mismo que clickear su barra. El punto era redundante justo en la
# granularidad donde más se lo veía. Los tres tramos resuelven como barra.
#
# 2026-09-19: MES Y AÑO TAMBIÉN, a pedido («quitemos los puntos, deseo que
# sea como en las otras opciones de día y semana, o sea partida»). La
# medición de arriba sigue siendo cierta —en Mes la compra mayor es ~5 % de
# la barra, una franja oscura fina contra el piso— y lo que cambió es cómo
# se la lee: igual que en Semana, la barra no promete «ver la mayor», dice
# de qué está hecho el período, y un mes casi todo claro dice «el mes son
# cientos de compras chicas» — que es cierto y es información. Lo que sí se
# fue con esto son los puntos, en todas las granularidades: ya no queda
# ninguna traza de compras sueltas, así que el clic resuelve siempre como
# barra y el `hovermode="closest"` ya no arbitra entre dos trazas.

_GRAN_PARTIDA = ("Día", "Semana", "Mes", "Año")
"""Granularidades cuya barra se parte en tramos: todas menos «Por
documento», donde la barra YA es una compra y no hay nada que partir.

Sumar una es sumarla acá y darle su entrada en `_TOTAL_DEL_PERIODO`, que es
lo que evita que el hover diga «Total del día» sobre una semana."""

_TOTAL_DEL_PERIODO = {"Día": "Total del día", "Semana": "Total de la semana",
                      "Mes": "Total del mes", "Año": "Total del año"}
"""Cómo nombra el hover al total del período, por granularidad.

Era el literal «Total del día» mientras la barra partida vivía sólo en Día.
Al sumar Semana pasó a ser falso sin dar ningún error: el número era el de
la semana y el rótulo decía día."""

_TRAMOS = (
    (0, 0, "La mayor"),
    (1, 2, "2ª y 3ª"),
    (3, None, "El resto"),
)
"""Los tres tramos, como (primer rango, último rango, rótulo de leyenda).

El rango es el puesto de la compra dentro de su período ordenado por valor
descendente, con 0 = la mayor. `None` como tope es «hasta el final»."""


def _tramos_del_periodo(dd, ord_claves):
    """Un DataFrame por tramo, indexado por clave y alineado a `ord_claves`.

    Devuelve una lista de tres DataFrames con las columnas `valor` (la suma
    del tramo), `n` (cuántas compras lo forman) y el `prov`/`doc` de la
    primera de cada tramo —que en el primero es la compra mayor. Las claves
    sin ese tramo —un día de una sola compra no tiene 2ª ni 3ª— salen en 0,
    que es lo que Plotly necesita para que las tres trazas compartan eje."""
    docs = (dd.groupby(["clave", "compra"], as_index=False)
              .agg(valor=("valor", "sum"), prov=("prov", "first"),
                   doc=("doc", "first")))
    # `compra` de desempate para que el orden sea ESTABLE entre reruns, por
    # el mismo motivo que el reparto de los puntos: dos compras del mismo
    # valor no pueden intercambiarse entre una corrida y la siguiente.
    docs = docs.sort_values(["clave", "valor", "compra"],
                            ascending=[True, False, True])
    docs["k"] = docs.groupby("clave").cumcount()

    salida = []
    for desde, hasta, _ in _TRAMOS:
        sel = docs[docs["k"] >= desde]
        if hasta is not None:
            sel = sel[sel["k"] <= hasta]
        agg = (sel.groupby("clave")
                  .agg(valor=("valor", "sum"), n=("compra", "size"),
                       prov=("prov", "first"), doc=("doc", "first")))
        agg = agg.reindex(ord_claves)
        agg["valor"] = agg["valor"].fillna(0.0)
        agg["n"] = agg["n"].fillna(0).astype(int)
        salida.append(agg)
    return salida


def _etiqueta_en_la_punta(tramos, textos):
    """El texto de cada TRAMO, con la etiqueta del total sólo en el de arriba.

    `tramos` son los de `_tramos_del_periodo` (abajo → arriba) y `textos` el
    total ya formateado de cada período, alineado al eje. Devuelve una lista
    por tramo, con `None` donde no va nada.

    Va en el tramo más alto CON VALOR, no en el último: un día de dos compras
    no tiene «el resto», y Plotly pone el `outside` de una barra apilada sólo
    en la que termina la pila (`_outmost` en su `cross_trace_calc`; a las
    demás las trata como `inside`). Colgar la etiqueta siempre del tercer
    tramo la dejaría, en esos días, dependiendo de cómo Plotly trate una
    barra de alto cero — y ahí no hay nada que ver."""
    salida = [[None] * len(textos) for _ in tramos]
    for j, txt in enumerate(textos):
        for i in range(len(tramos) - 1, -1, -1):
            if tramos[i]["valor"].iloc[j]:
                salida[i][j] = txt
                break
    return salida


# ===========================================================================
# EL VALORIZADO POR FAMILIA (2026-09-17, regla #454)
# ===========================================================================
# A pedido: «una mini kpi, interno, que me diga el total de la vista, y el
# total por familia. Y también alguna otra kpi o etiqueta que me muestre el
# total por familia de la barra, puede ser al pasar el cursor».
#
# Son dos preguntas con dos respuestas, y no una respuesta repetida:
#   · la VISTA —rango + filtros de la tarjeta— va en una fila de KPI dentro
#     de la cabecera, al lado de la fecha, que es lo que la acota;
#   · la BARRA va en su hover, que es el único sitio donde cada barra
#     contesta por sí misma sin ocupar alto.
#
# CUÁNTAS FAMILIAS. Medido con DuckDB contra `compras.parquet` (mes corrido
# al 16/09/2026): son 8, y el reparto es muy desparejo —
#
#     ALIMENTOS               S/ 124.0k   79 %
#     COSTOS PRODUCCION        S/ 15.2k   10 %
#     VINOS Y ESPUMANTES        S/ 7.4k    5 %
#     BEBIDAS CON ALCOHOL       S/ 5.3k    3 %
#     las otras cuatro          S/ 4.6k    3 %   (la última, S/ 8)
#
# Las cuatro mayores son el 97 %: una tarjeta por familia gastaría la mitad
# de la fila en montos que no se leen. Por día aparecen 4 en promedio y 8 de
# máximo; por documento, 1,09 — de ahí los dos topes de abajo.

_KPI_FAMILIAS = 4
"""Familias con tarjeta propia en la fila de KPI; el resto va sumado en una.

Ver la medición de arriba. El ancho es el otro techo: el total, cuatro
familias y «N más» tienen que entrar en el renglón que les deja la
cabecera junto a la fecha (ver `.st-key-cp_sem_kpi` en
`_css_proveedor.py`, que trae lo medido)."""

_HOVER_FAMILIAS = 5
"""Familias que nombra el hover de una barra; el resto va en «N más».

Con 8 de máximo por día, cinco renglones cubren el día típico entero (4) y
dejan el hover de un día raro en siete renglones en vez de diez."""


def _nombre_familia(fam):
    """«COSTOS PRODUCCION» → «Costos produccion». El parquet las trae en
    mayúsculas, y en un hover de seis renglones eso se lee a los gritos."""
    fam = str(fam or "").strip()
    return fam[:1].upper() + fam[1:].lower() if fam else "Sin familia"


def _familias_de(dd):
    """`(total, [(familia, valor, parte), …], (n_resto, valor_resto))` del
    valorizado de `dd` por familia, de mayor a menor.

    `parte` es la fracción del total (0-1). La lista trae las
    `_KPI_FAMILIAS` mayores y el resto va sumado aparte, con cuántas son.
    Las familias en cero no cuentan: una familia con compras anuladas que
    suman 0 no es una familia de la vista."""
    total = float(dd["valor"].sum())
    s = dd.groupby("fam")["valor"].sum()
    s = s[s != 0].sort_values(ascending=False)
    top = [(f, float(v), (float(v) / total) if total else 0.0)
           for f, v in s.iloc[:_KPI_FAMILIAS].items()]
    resto = s.iloc[_KPI_FAMILIAS:]
    return total, top, (len(resto), float(resto.sum()))


def _html_kpi_vista(total, n_compras, top, resto):
    """La fila de KPI de la cabecera: el total y las familias mayores.

    Cada tarjeta lleva el nombre COMPLETO en `title`: el rótulo se recorta
    con puntos suspensivos a partir de ~13 caracteres («Vinos y espumantes»
    no entra) y el tooltip nativo es lo que lo devuelve entero. Con una sola
    familia en la vista no se desglosa nada: el total ya es esa familia, y
    el título de la figura la nombra."""
    def _tarjeta(rotulo, valor, sub, clase="", tip=""):
        return (f'<div class="sem-kpi {clase}" title="{escape(tip or rotulo)}">'
                f'<span class="sem-kpi-rot">{escape(rotulo)}</span>'
                f'<span class="sem-kpi-val">{escape(valor)}'
                f'<span class="sem-kpi-sub">{escape(sub)}</span></span></div>')

    _n = f"{n_compras:,} compra" + ("" if n_compras == 1 else "s")
    partes = [_tarjeta("Total de la vista", fmt_k(total), _n, "sem-kpi-total",
                       f"Total de la vista: S/ {total:,.2f} · {_n}")]
    if len(top) + resto[0] > 1:
        for fam, v, p in top:
            nom = _nombre_familia(fam)
            partes.append(_tarjeta(nom, fmt_k(v), f"{p:.0%}",
                                   tip=f"{nom}: S/ {v:,.2f} · {p:.1%}"))
        if resto[0]:
            _p = resto[1] / total if total else 0.0
            partes.append(_tarjeta(
                f"{resto[0]} más", fmt_k(resto[1]), f"{_p:.0%}", "sem-kpi-resto",
                f"{resto[0]} familias más: S/ {resto[1]:,.2f} · {_p:.1%}"))
    return '<div class="sem-kpis">' + "".join(partes) + "</div>"


def _familias_por_clave(dd):
    """`{clave: texto}` con el valorizado por familia de cada período, listo
    para colgar al final de un `hovertemplate` (empieza con `<br>`).

    Vacío si la vista tiene UNA familia: con el filtro de Familia puesto el
    desglose sería un renglón que repite el total. Vectorizado a propósito:
    en «Por documento» con el histórico entero son ~15.000 claves, y un
    bucle de Python por clave tardaba lo que el resto del drill junto."""
    if dd["fam"].nunique() <= 1:
        return {}
    s = dd.groupby(["clave", "fam"], as_index=False)["valor"].sum()
    s = s[s["valor"] != 0]
    s["tot"] = s.groupby("clave")["valor"].transform("sum")
    s = s.sort_values(["clave", "valor"], ascending=[True, False])
    s["k"] = s.groupby("clave").cumcount()

    top = s[s["k"] < _HOVER_FAMILIAS]
    _pct = (top["valor"] / top["tot"].where(top["tot"] != 0)).fillna(0)
    top = top.assign(txt=(
        top["fam"].map(_nombre_familia) + ": S/ "
        + top["valor"].map(lambda v: f"{v:,.2f}")
        + " · " + _pct.map(lambda p: f"{p:.0%}")))
    lineas = top.groupby("clave")["txt"].agg("<br>".join)

    resto = (s[s["k"] >= _HOVER_FAMILIAS].groupby("clave")
               .agg(n=("fam", "size"), v=("valor", "sum")))
    lineas = lineas.to_dict()
    for clave, fila in resto.iterrows():
        lineas[clave] += (f"<br>{int(fila['n'])} más: "
                          f"S/ {fila['v']:,.2f}")
    _tit = f"<br><span style='color:{GRIS_TEXTO}'>Por familia</span><br>"
    return {c: _tit + t for c, t in lineas.items()}


# ===========================================================================
# ETIQUETAS SOBRE LAS BARRAS (2026-09-14, regla #440)
# ===========================================================================
# A pedido: «en la vista semana, la opción de semana, debe mostrar etiquetas
# en las barras». Van en Semana y también en Mes y Año, que son la misma
# clase de barra —la SUMA de un período— y abren con menos barras todavía;
# no en Día ni en «Por documento», donde un mes son 30-60 barras y el número
# no entra ni girado.
#
# «Mostrar» es la palabra que manda, y por eso esto es una CUENTA y no un
# `text=` suelto: Plotly no oculta la etiqueta que no entra, la encima con
# la vecina (regla #91, y la misma cuenta que `vs_ano_pasado._plan_etiquetas`,
# regla #400). La forma sale de los píxeles que le tocan a cada período,
# contra `_LIENZO_PX`.
#
# 2026-09-19: la etiqueta dejó de ser sólo el total — suma los documentos y
# la variación contra la barra anterior (#470), y el plan decide además
# CUÁNTOS de esos renglones entran. Ver `_plan_etiquetas`.
#
# 2026-09-17: TAMBIÉN EN DÍA Y «POR DOCUMENTO», a pedido («necesito que las
# columnas muestren el valorizado»). La exclusión de arriba era una
# suposición —«el número no entra ni girado»— y la cuenta ya la contestaba
# sola, barra por barra: un mes corrido son 30 días, 27px por barra, y
# «S/ 13.4k» (el día más alto de ese mes) entra GIRADO (13 + 4 = 17px). En
# «Por documento» ese mismo mes son 263 barras de 3px y `_plan_etiquetas`
# devuelve `None`: ahí el valor sigue en el hover, como siempre.

_GRAN_CON_ETIQUETA = ("Día", "Semana", "Mes", "Año", "Por documento")

_ETQ_FUENTE = 10
"""Cuerpo de las etiquetas, en px: el de las de «Vs año pasado» y Producto."""

_ETQ_PX_CARACTER = 5.4
"""Ancho medio de un carácter a `_ETQ_FUENTE` en DM Sans, MEDIDO para las
etiquetas de «Vs año pasado» (`vs_ano_pasado._ETQ_PX_CARACTER`), que son
del mismo formato («S/ 107.9k»). Se usa el techo: sobrar un píxel sólo gira
antes una etiqueta que entraba derecha."""

_ETQ_ALTO_LINEA = 13
"""Alto de una línea a `_ETQ_FUENTE` (ascent + descent). Es lo que ocupa una
etiqueta derecha hacia arriba, y lo que ocupa GIRADA hacia el costado."""

_ETQ_AIRE = 4
"""Separación entre etiquetas vecinas, y entre la etiqueta y el borde."""

_MARGEN_Y_FIG = 30 + 10
"""Los márgenes de arriba (el título) y de abajo que pone `_compras_layout`."""

_LEYENDA_Y = 0.22
"""A qué distancia DEBAJO del área de trazo va la leyenda, en fracción de su
alto (`legend.y = -_LEYENDA_Y`). Es la misma constante en el layout y en la
cuenta del alto del área de trazo, porque es la que lo decide: Plotly
agranda el margen de abajo hasta que entre la leyenda, así que lo que la
leyenda pide CRECE con la figura. Medido a 1366x768 (2026-09-14): figura
449 → área 335, figura 240 → área 164. Las dos cierran con
`(alto − _MARGEN_Y_FIG) / (1 + _LEYENDA_Y)`; un cromo fijo no cierra con
las dos (salen 114 y 76px)."""


def _alto_area_trazo(alto_fig):
    """Alto del área de trazo de una figura de `alto_fig`. Ver `_LEYENDA_Y`."""
    return max((alto_fig - _MARGEN_Y_FIG) / (1 + _LEYENDA_Y), 1.0)


_ETQ_TECHO = 0.45
"""Fracción máxima del área de trazo que puede ocupar la etiqueta encima de
la barra más alta. Más que eso y las barras quedan aplastadas contra el piso
para hacerle lugar al texto."""

_ETQ_SEP = " · "
"""Cómo se unen los renglones cuando van en UNA línea girada."""


def _plan_etiquetas(n_periodos, lineas, alto_fig):
    """Cómo se escribe la etiqueta de cada barra: `(forma, k, alto_px)`.

    `lineas` trae, por barra, sus renglones en orden de importancia —el
    total, los documentos, la variación (regla #470)— como texto PLANO, que
    es lo que se mide. `k` es cuántos de esos renglones entran, siempre los
    primeros; `alto_px`, lo que la etiqueta ocupa hacia ARRIBA, para el
    techo del eje. La `forma` es una de tres:

      · "derecha" — los renglones apilados y horizontales. Pide que el más
        largo entre en el slot de la barra.
      · "girada"  — los mismos renglones, girados: cada uno ocupa una línea
        de ANCHO, así que pide `k` líneas en el slot.
      · "unida"   — girada y en UNA sola línea, los renglones unidos por
        « · ». Es la de Día con un mes en pantalla: 27px de slot no dan para
        dos líneas giradas (2 × 13 + 4 = 30), sí para una.

    El apretón de ancho es la distancia entre dos etiquetas VECINAS, que es
    el slot entero del período (una sola serie: no hay otra barra en el
    mismo slot, como sí en «Vs año pasado»). El de alto es `_ETQ_TECHO`:
    sin él, «S/ 13.4k · 12 docs · +12%» girada se comería media figura
    cuando se abre el detalle y la figura baja a COMPACTO. Si con `k`
    renglones no entra ninguna forma, se prueba con uno menos — cae primero
    el último de la lista. `(None, 0, 0)` si ni el total entra: queda en el
    hover, como siempre."""
    lineas = [ls for ls in lineas if ls]
    if n_periodos <= 0 or not lineas:
        return None, 0, 0
    px_slot = _LIENZO_PX / n_periodos
    alto_max = _alto_area_trazo(alto_fig) * _ETQ_TECHO

    def _px(n_car):
        return n_car * _ETQ_PX_CARACTER + _ETQ_AIRE

    for k in range(max(len(ls) for ls in lineas), 0, -1):
        cortas = [ls[:k] for ls in lineas]
        n_lin = max(len(ls) for ls in cortas)
        largo = max(len(t) for ls in cortas for t in ls)
        unida = max(len(_ETQ_SEP.join(ls)) for ls in cortas)
        alto_lin = n_lin * _ETQ_ALTO_LINEA + _ETQ_AIRE
        if _px(largo) <= px_slot and alto_lin <= alto_max:
            return "derecha", k, alto_lin
        if alto_lin <= px_slot and _px(largo) <= alto_max:
            return "girada", k, _px(largo)
        if (n_lin > 1 and _ETQ_ALTO_LINEA + _ETQ_AIRE <= px_slot
                and _px(unida) <= alto_max):
            return "unida", k, _px(unida)
    return None, 0, 0


def _techo_etiquetas(hi, lo, alto_fig, alto_etq):
    """`[ymin, ymax]` del eje Y con lugar para `alto_etq` px de etiqueta
    encima de la barra más alta.

    `textposition="outside"` NO agranda el rango solo: la etiqueta de la
    barra más alta queda contra el borde y se corta. La cuenta es en
    píxeles, la misma de `vs_ano_pasado._techo_con_etiquetas`: si el área de
    trazo mide `alto_plot` y la etiqueta necesita `alto_etq`, el dato tiene
    que ocupar `alto_plot − alto_etq`."""
    alto_plot = _alto_area_trazo(alto_fig)
    alto_etq = min(alto_etq, alto_plot * _ETQ_TECHO)
    base = min(0.0, lo)
    span = hi - base
    if span <= 0:
        return None
    return [base, base + span * alto_plot / (alto_plot - alto_etq)]


# ===========================================================================
# EL PERÍODO CON NOMBRE, SUS DOCUMENTOS Y CUÁNTO CAMBIÓ (2026-09-19, #470)
# ===========================================================================
# Tres pedidos del mismo día, y los tres terminan en la etiqueta de la barra:
#   · «en la opción de día debe mostrar la cantidad de documentos, debajo
#     del total. En la opción por semana, también» — y en Mes y Año, que
#     desde el mismo día son la misma barra partida.
#   · «no debe decir 2026-S37, debe decir por ejemplo Lun13-Dom20 Sept 2026
#     o algo resumido» — el eje dice «14–20 set» (con el año debajo cuando
#     cambia) y el hover y el caption, la semana entera. Mes deja «2026-09»
#     por «set 2026» por el mismo motivo: era el mismo código de máquina.
#   · «la barra pueda mostrar el % variación + o − respecto a la barra
#     anterior», en Día, Semana y Mes.
#
# LA VARIACIÓN NO SE CALCULA CONTRA UN PERÍODO CORTADO. El rango de la
# tarjeta abre en un mes corrido («20 ago – 19 set»), así que por semana la
# primera y la última barra son semanas A MEDIAS, y por mes las dos. Una
# semana de 5 días contra una de 7 da «−30 %» sin que haya cambiado nada, y
# encima en la barra que más se mira: la de la semana en curso. Esas barras
# dicen «parcial» en vez de un porcentaje, la de al lado de una parcial no
# dice nada, y el hover explica cuál de las dos cosas pasó.
#
# «LA BARRA ANTERIOR» ES LA ANTERIOR DIBUJADA, no el período anterior del
# calendario: así lo dice el pedido y así se lee. Un lunes se compara con
# el sábado si el domingo no hubo compras —no hay barra de cero—, y el hover
# NOMBRA contra cuál («vs Sáb 12/09»), así que el salto se ve.
#
# EL COLOR ES EL DE «VS AÑO PASADO»: rojo si se compró más, verde si menos.
# Es la convención de todo Compras (`vs_ano_pasado.py`, sus dos cascadas y
# su veredicto): en un reporte de GASTO, subir no es la buena noticia. El
# signo va escrito igual, así que el color nunca es la única señal.

_GRAN_CON_DOCS = ("Día", "Semana", "Mes", "Año")
"""Granularidades cuya etiqueta dice cuántos documentos suma la barra. No
«Por documento»: ahí cada barra ES uno."""

_GRAN_VARIACION = ("Día", "Semana", "Mes")
"""Granularidades cuya etiqueta dice cuánto cambió contra la barra anterior.
Año no, porque no se pidió: con el rango de entrada es una sola barra."""

_INCOMPLETO = {"Semana": "Semana incompleta", "Mes": "Mes incompleto",
               "Año": "Año incompleto"}
"""Cómo el hover nombra a un período que el rango corta (el género manda)."""

_UNIDAD_GRAN = {"Día": ("día", "días"), "Semana": ("semana", "semanas"),
                "Mes": ("mes", "meses"), "Año": ("año", "años"),
                "Por documento": ("documento", "documentos")}
"""Cómo se cuenta una BARRA en cada granularidad, en singular y plural.

La fila TOTAL del modo Resumen dice «Total · 5 semanas» y no «5 períodos»,
y con eso la tabla ya declara cómo está agrupada: la palabra con la que se
cuentan las filas ES el grano (2026-09-20, a pedido)."""

_AGRUPADO_GRAN = {"Día": "día", "Semana": "semana", "Mes": "mes",
                  "Año": "año", "Por documento": "documento"}
"""Cómo lo dice el caption: «agrupado por semana». Separado de
`_UNIDAD_GRAN` porque ahí la palabra se pluraliza y acá nunca."""


def _del_al(fechas):
    """«Del 17 ago al 16 sep 2026»: qué cubren las BARRAS de la tabla.

    Sale de las compras dibujadas —`dd["fecha"]`, o sea las filas que
    forman las barras— y no del rango de la tarjeta, que es lo que pide el
    pedido: «me refiero a todo el rango de barras que está mostrando la
    tabla resumen» (2026-09-20). Los dos coinciden casi siempre y se
    separan justo donde importa: con el rango abierto más allá del dato, la
    tarjeta promete un mes que la tabla no tiene.

    Y son los días CON COMPRAS, no los bordes del primer y el último
    período: la semana del 14 al 20 set con datos hasta el 16 cierra «al 16
    set», porque es hasta ahí que suma la columna de al lado. Que ese
    período esté cortado ya lo dice su fila, con «parcial».

    El año va una sola vez cuando los dos extremos caen en el mismo, igual
    que `franja_fecha.fmt_rango_es` — de la que se diferencia sólo en las
    palabras, porque el pedido fue literal: «la tabla debe indicar Del…Al».
    """
    if fechas is None or not len(fechas):
        return "Todo el rango"
    ini, fin = fechas.min().date(), fechas.max().date()
    _m = cortes.MESES_ABR_ES
    if ini == fin:
        return f"El {ini.day} {_m[ini.month - 1]} {ini.year}"
    if ini.year == fin.year:
        return (f"Del {ini.day} {_m[ini.month - 1]} al "
                f"{fin.day} {_m[fin.month - 1]} {fin.year}")
    return (f"Del {ini.day} {_m[ini.month - 1]} {ini.year} al "
            f"{fin.day} {_m[fin.month - 1]} {fin.year}")


def _limites_periodo(clave, gran):
    """`(primer día, último día)` del período `clave`, como `date`.

    `clave` es la de `_periodo_serie`: «2026-09-15», «2026-S38», «2026-09» o
    «2026». La semana es ISO —de lunes a domingo, con el año ISO, que en la
    semana 1 puede ser el siguiente al del lunes—, así que se desarma con
    `fromisocalendar` y no sumando días desde el 1º de enero."""
    if gran == "Semana":
        _a, _s = clave.split("-S")
        ini = date.fromisocalendar(int(_a), int(_s), 1)
        return ini, ini + timedelta(days=6)
    if gran == "Mes":
        _a, _m = (int(_x) for _x in clave.split("-"))
        return (date(_a, _m, 1),
                date(_a + _m // 12, _m % 12 + 1, 1) - timedelta(days=1))
    if gran == "Año":
        return date(int(clave), 1, 1), date(int(clave), 12, 31)
    _d = date.fromisoformat(clave)
    return _d, _d


def _rotulo_periodo(clave, gran):
    """`(eje, largo)`: cómo se nombra el período en el eje y en el hover.

        Semana   «14–20 set»      «Semana del lun 14 al dom 20 set 2026»
                 «31 ago–6 set»   «Semana del lun 31 ago al dom 6 set 2026»
        Mes      «set 2026»       «Set 2026»
        Año, Día la clave, que ya se lee

    El año no va en el rótulo de la semana: lo pone el eje debajo, sólo en
    el primero y cuando cambia (`_anio_semana`), que es como lo hace Plotly
    en un eje de fechas. Repetido en cada semana sería tinta sin dato."""
    _m = cortes.MESES_ABR_ES
    if gran == "Semana":
        ini, fin = _limites_periodo(clave, gran)
        mi, mf = _m[ini.month - 1], _m[fin.month - 1]
        if ini.month == fin.month:
            return (f"{ini.day}–{fin.day} {mf}",
                    f"Semana del lun {ini.day} al dom {fin.day} {mf} "
                    f"{fin.year}")
        _ai = f" {ini.year}" if ini.year != fin.year else ""
        return (f"{ini.day} {mi}–{fin.day} {mf}",
                f"Semana del lun {ini.day} {mi}{_ai} al dom {fin.day} {mf} "
                f"{fin.year}")
    if gran == "Mes":
        ini, _ = _limites_periodo(clave, gran)
        txt = f"{_m[ini.month - 1]} {ini.year}"
        return txt, txt[:1].upper() + txt[1:]
    return clave, clave


def _anio_semana(clave):
    """El año que el eje escribe debajo de una semana: «2026», o «2025-26»
    la que va a caballo de dos (lun 29 dic – dom 4 ene)."""
    ini, fin = _limites_periodo(clave, "Semana")
    if ini.year == fin.year:
        return str(fin.year)
    return f"{ini.year}-{fin.year % 100:02d}"


def _cobertura(clave, gran, rango):
    """`(días del período dentro del rango, días del período)`.

    Sin rango conocido el período cuenta como entero: no marcar «parcial»
    es la falla barata — sólo se ve un porcentaje que no se debería."""
    ini, fin = _limites_periodo(clave, gran)
    dias = (fin - ini).days + 1
    if not rango:
        return dias, dias
    a, b = max(ini, rango[0]), min(fin, rango[1])
    return max((b - a).days + 1, 0), dias


def _variaciones(claves, valores, gran, rango):
    """Por barra, `(estado, pct, i_ant)` contra la barra ANTERIOR dibujada.

    `estado` es "ok" (con `pct` en %), "parcial" (el rango corta ESTE
    período), "ant_parcial" (corta el anterior), "primera" o "sin_base" (el
    anterior suma ≤ 0: no hay porcentaje contra cero). `i_ant` es el índice
    de la barra contra la que se comparó, para nombrarla en el hover."""
    parcial = [_c[0] < _c[1] for _c in
               (_cobertura(k, gran, rango) for k in claves)]
    salida = []
    for i, v in enumerate(valores):
        ant = i - 1 if i else None
        if parcial[i]:
            salida.append(("parcial", None, ant))
        elif ant is None:
            salida.append(("primera", None, None))
        elif parcial[ant]:
            salida.append(("ant_parcial", None, ant))
        elif not valores[ant] or valores[ant] <= 0:
            salida.append(("sin_base", None, ant))
        else:
            salida.append(("ok", (v - valores[ant]) / valores[ant] * 100, ant))
    return salida


def _fmt_variacion(pct):
    """`(texto, color)`: «+12%» / «−4.7%» y su color.

    Un decimal por debajo del 10 % y ninguno arriba: «+4.7%» dice algo,
    «+143.2%» no dice más que «+143%». Con signo siempre —el menos
    tipográfico, como el resto de Compras— y «0%» gris cuando redondea a
    cero, que con signo sería un cambio que no hubo."""
    dec = 1 if abs(pct) < 10 else 0
    if round(abs(pct), dec) == 0:
        return "0%", GRIS_TEXTO
    txt = f"{abs(pct):.{dec}f}%"
    return ("+" + txt, ERROR) if pct > 0 else ("−" + txt, EXITO)


def _renglones_etiqueta(total, n_docs, var, gran):
    """Los renglones de la etiqueta de UNA barra, como `(plano, html)` y en
    orden de importancia: el total, los documentos, la variación.

    `total` ya formateado (o `None` si la barra suma cero: sin etiqueta).
    `var` es la tupla de `_variaciones`. El texto plano es lo que mide
    `_plan_etiquetas`; el HTML, lo que se dibuja — el gris de los documentos
    y el color de la variación son `<span>` que Plotly entiende."""
    if not total:
        return []
    salida = [(total, total)]
    if gran in _GRAN_CON_DOCS:
        _d = f"{n_docs:,} doc" + ("" if n_docs == 1 else "s")
        salida.append((_d, f"<span style='color:{GRIS_TEXTO}'>{_d}</span>"))
    if gran in _GRAN_VARIACION and var:
        estado, pct, _ = var
        if estado == "ok":
            _t, _c = _fmt_variacion(pct)
            salida.append((_t, f"<span style='color:{_c}'><b>{_t}</b></span>"))
        elif estado == "parcial":
            salida.append(("parcial",
                           f"<span style='color:{GRIS_TEXTO}'><i>parcial</i>"
                           "</span>"))
    return salida


def _hover_variacion(var, gran, clave, nombre_ant, rango):
    """El renglón del hover que dice la variación, o por qué no la hay.

    Empieza con `<br>` (o es vacío), listo para colgar de un
    `hovertemplate`. Es el único lugar donde una barra «parcial» dice
    CUÁNTO le falta, y donde la de al lado dice por qué calla."""
    if gran not in _GRAN_VARIACION or not var:
        return ""
    estado, pct, _ = var
    if estado == "ok":
        _t, _c = _fmt_variacion(pct)
        return (f"<br>vs {nombre_ant}: "
                f"<span style='color:{_c}'><b>{_t}</b></span>")
    if estado == "parcial":
        _n, _m = _cobertura(clave, gran, rango)
        return (f"<br><i>{_INCOMPLETO.get(gran, 'Período incompleto')} en "
                f"el rango ({_n} de {_m} días): sin variación</i>")
    if estado == "ant_parcial":
        return (f"<br><i>Sin variación: la barra anterior ({nombre_ant}) "
                "está incompleta en el rango</i>")
    if estado == "sin_base":
        return f"<br><i>Sin variación: {nombre_ant} no suma compras</i>"
    return "<br><i>Primera barra del rango: sin anterior para comparar</i>"


def _nota_variacion(var, gran, clave, nombre_ant, rango):
    """Lo mismo que `_hover_variacion`, en texto PLANO: es el tooltip de la
    columna «Variación» de la tabla Resumen (regla #476).

    Dos formatos para el mismo dato porque los dos destinos son distintos:
    el hover de Plotly entiende HTML y el `tooltipField` de AG Grid no —
    ahí un `<br>` se ve escrito. Lo que NO cambia es qué se dice: si la
    tabla callara el motivo, una columna de «parcial» y «—» se leería como
    datos faltantes."""
    if gran not in _GRAN_VARIACION or not var:
        return ""
    estado, pct, _ = var
    if estado == "ok":
        return f"vs {nombre_ant}: {_fmt_variacion(pct)[0]}"
    if estado == "parcial":
        _n, _m = _cobertura(clave, gran, rango)
        return (f"{_INCOMPLETO.get(gran, 'Período incompleto')} en el rango "
                f"({_n} de {_m} días): sin variación")
    if estado == "ant_parcial":
        return (f"Sin variación: la barra anterior ({nombre_ant}) está "
                "incompleta en el rango")
    if estado == "sin_base":
        return f"Sin variación: {nombre_ant} no suma compras"
    return "Primera barra del rango: sin anterior para comparar"


_TICK_PX_CARACTER = 6.3
"""Ancho medio de un carácter del rótulo del eje (DM Sans 12px). Lo usa el
paso del eje fuera del calendario de días: cuántos rótulos entran sale del
más largo, no de un número fijo — «31 ago–6 set» mide el triple que «2026»."""

_TICK_AIRE = 12
"""Aire entre dos rótulos vecinos del eje: un rótulo que mide 60 no entra en
60, entra en 60 más el hueco que lo separa del vecino (#362)."""


# ===========================================================================
# EL CALENDARIO DEL EJE: separación de días, fin de semana y feriado
# ===========================================================================
# Pedido el 2026-09-08, mirando "Por documento": "una leve línea punteada
# vertical que dé una idea de separación visual de días, y añadir algo que
# indique el día, si es finde semana, o si es feriado".
#
# El rótulo del eje era el síntoma. Con 61 documentos en la ventana de la
# captura (6 días), `_paso` dejaba un rótulo cada 4 barras y salía
# «15/08 15/08 15/08 15/08 17/08 …»: cuatro veces la MISMA fecha, y aun así
# sin decir dónde empieza el día siguiente. Un rótulo por DÍA, centrado en su
# tramo de barras, dice las dos cosas con menos tinta.
#
# LA REGLA DE LA PUNTEADA, que vale para las dos granularidades de grano
# diario: la línea marca el cambio de la unidad de ARRIBA de la barra.
#   · «Por documento» — la barra es un documento, arriba está el día  -> una
#     línea en cada cambio de día.
#   · «Día» — la barra YA es un día, arriba está la semana  -> una línea en
#     cada lunes. Es exactamente lo que hace `ventas_comparativo` en su
#     granularidad día, y de ahí sale también la paleta de las bandas.
#
# En Semana/Mes/Año no se dibuja nada: no hay día que sombrear, y un feriado
# adentro de una barra que suma siete días no explica esa barra. (Ventas sí
# marca ahí el DESBALANCE de feriados, pero porque COMPARA dos períodos —
# acá no hay contra qué.)
#
# NO ES CÓSMETICO: un lunes de S/ 0 al lado de un domingo de S/ 8.000 se lee
# como un bache del negocio hasta que la banda dice "domingo". Los feriados
# son la misma historia una vez al mes.

_PX_MIN_DIA_ROTULO = 16
"""Píxeles por día a partir de los cuales el eje admite rótulo y punteada.

Mismo criterio —y mismo `_LIENZO_PX`— que `_tope_puntos`: el número sale de
los píxeles que hay, no de un día lindo. A 16px por día se rotula uno de
cada dos y las punteadas todavía se distinguen entre sí. Con 820px de lienzo
el techo cae en ~51 días, un poco más que el rango por defecto de la franja
(1º del mes → hoy)."""

_PX_MIN_DIA_BANDA = 4
"""Y el piso de las BANDAS, que aguantan mucho más que los rótulos.

Una banda no tiene que leerse una por una: de lejos es un patrón —dos
franjas grises cada cinco huecos— y eso sigue diciendo "fin de semana" a 4px
de ancho. Por eso sobrevive al rótulo y a la punteada en vez de apagarse con
ellos: ~205 días de techo contra ~51. Más allá de eso las BARRAS mismas ya
no llegan al píxel y el gráfico no es de días."""

_ROTULO_DIA_PX = 44
"""Lo que OCUPA un rótulo de día: los 36px que mide más 8 de aire.

Los 36 están medidos en el navegador (figura a 915px de tarjeta, Plotly
3.6): los 14 rótulos de un mes miden entre 30 y 36px. El aire no: es la
corrección de haber usado 36 pelado, que la app en vivo desmintió al primer
intento — con 22 días en 808px de lienzo el paso daba 1 (un rótulo por día,
36,7px de separación) y **7 pares se pisaban**. Un rótulo que mide 36 no
entra en 36: entra en 36 más el hueco que lo separa del vecino.

Con 44 el mismo caso pasa a un rótulo cada dos días —73px de separación,
37 de aire— y en el peor caso que admite `_PX_MIN_DIA_ROTULO` (51 días)
quedan 12. Es el mismo error de la #349: medir el ancho del contenido y
olvidar que el contenido no es lo único que ocupa lugar."""

_MARGEN_SUP_FERIADO = 46
"""Margen superior cuando hay al menos una anotación «feriado».

`_compras_layout` deja 30, que alcanza para el título y nada más. Medido en
el navegador: el título ocupa y=6..28 y la fila de anotaciones y=31..44, así
que con 46 entran las dos sin pisarse."""


def _grupos_de_dia(dias):
    """`[(i0, i1, dia), …]`: tramos CONTIGUOS del eje que caen el mismo día.

    `dias` viene alineado con el eje —un `date` por período dibujado—, así
    que un tramo son las N compras de ese día en «Por documento» y un solo
    índice en «Día». Que los documentos de un día sean contiguos no es
    suerte: `_ord_claves` ordena por la clave de compra, que arranca con la
    fecha (ver `dd["compra"]`).
    """
    grupos = []
    for i, d in enumerate(dias):
        if grupos and grupos[-1][2] == d:
            grupos[-1][1] = i
        else:
            grupos.append([i, i, d])
    return [tuple(g) for g in grupos]


def _rachas(marcados):
    """`[(desde, hasta), …]`: tramos de índices CONSECUTIVOS de `marcados`.

    Los feriados se anotan por racha y no de a uno porque sus bandas se
    tocan: 28 y 29 de julio son dos días y UNA sola franja ámbar, así que
    dos «feriado» encima serían dos rótulos de 34px a 33px de distancia —
    pisados, y diciendo lo mismo dos veces."""
    out = []
    for j in sorted(marcados):
        if out and out[-1][1] == j - 1:
            out[-1][1] = j
        else:
            out.append([j, j])
    return [tuple(r) for r in out]


def _calendario_del_eje(fig, dias, sep):
    """Pinta el calendario sobre `fig` y devuelve `(tickvals, ticktext)`.

    `sep` dice dónde va la punteada: `"dia"` (cambio de día — «Por
    documento») o `"semana"` (cada lunes — «Día»). Ver el comentario de
    arriba, que explica por qué son dos reglas distintas y la misma idea.

    Devuelve `None` cuando no entra un rótulo por día: el llamador vuelve
    entonces a las etiquetas de siempre. Las bandas, que aguantan más, ya
    quedaron dibujadas igual — de ahí que el `None` no signifique "no se
    dibujó nada".
    """
    grupos = _grupos_de_dia(dias)
    px_dia = _LIENZO_PX / max(len(grupos), 1)
    if px_dia < _PX_MIN_DIA_BANDA:
        return None

    feriados = set()
    for _a in {d.year for _, _, d in grupos}:
        feriados |= cortes.feriados_peru(_a)

    # Las BANDAS. `layer="below"` para que la barra siga siendo lo que se
    # mira; el feriado le gana al fin de semana cuando caen juntos (un
    # domingo feriado es, de las dos, la que explica la anomalía).
    _fer_ix = []
    for j, (i0, i1, d) in enumerate(grupos):
        _fer, _finde = d in feriados, d.weekday() >= 5
        if _fer:
            _fer_ix.append(j)
        if not (_fer or _finde):
            continue
        fig.add_vrect(
            x0=i0 - 0.5, x1=i1 + 0.5, layer="below", line_width=0,
            fillcolor=(ADVERTENCIA_TEXTO if _fer else GRIS_TEXTO),
            opacity=(0.10 if _fer else 0.07))

    # La palabra «feriado» va ARRIBA del lienzo, no en el rótulo del eje, y
    # eso se decidió MIDIENDO en el navegador (arquitectura.md #362). Como
    # tercer renglón del rótulo empujaba el eje 14px hacia abajo y se metía
    # encima del legend —que vive en `y=-0.22`—, y de paso engordaba el
    # rótulo de 36 a 47px, con lo que dos días vecinos se pisaban. Acá
    # arriba no compite con nada: es la misma franja que usa
    # `ventas_comparativo` para lo mismo. Sin banda no habría anotación, así
    # que el ámbar y la palabra siempre aparecen juntos.
    for _a, _b in _rachas(_fer_ix):
        fig.add_annotation(
            x=(grupos[_a][0] + grupos[_b][1]) / 2, y=1.0, yref="paper",
            yanchor="bottom", showarrow=False, text="feriado",
            font=dict(size=10, color=ADVERTENCIA_TEXTO))
    if _fer_ix:
        fig.update_layout(margin_t=_MARGEN_SUP_FERIADO)

    if px_dia < _PX_MIN_DIA_ROTULO:
        return None

    # La PUNTEADA. Va en los BORDES de los tramos (i0 - 0.5), o sea entre dos
    # barras y no encima de una.
    for j, (i0, _, d) in enumerate(grupos):
        if j == 0:
            continue
        if sep == "semana" and d.weekday() != 0:
            continue
        fig.add_shape(type="line", xref="x", yref="paper",
                      x0=i0 - 0.5, x1=i0 - 0.5, y0=0, y1=1,
                      line=dict(color=GRIS_BORDE, width=1, dash="dot"),
                      layer="below")

    # Los RÓTULOS, uno por día y centrado en su tramo. Todos miden lo mismo
    # (dos renglones), así que el adelgazado es un paso parejo y no hay que
    # protegerle el lugar a nadie.
    _paso = max(1, -(-len(grupos) // max(1, int(_LIENZO_PX // _ROTULO_DIA_PX))))
    tickvals, ticktext = [], []
    for j, (i0, i1, d) in enumerate(grupos):
        if j % _paso:
            continue
        tickvals.append((i0 + i1) / 2)
        ticktext.append(f"{cortes.DIAS_ABR_ES[d.weekday()].capitalize()}"
                        f"<br>{d:%d/%m}")
    return tickvals, ticktext


def _clave_del_clic(x, ord_claves):
    """Clave del período que corresponde a la x de un clic en una barra.

    El eje es lineal (ver el `update_xaxes` del drill), así que lo que
    devuelve `on_select` es el índice y no la clave. Tolerante a propósito:
    un clic devuelve un float y una x fuera de rango tiene que ser un
    no-op, no una excepción en medio del render."""
    try:
        i = int(round(float(x)))
    except (TypeError, ValueError):
        return None
    return ord_claves[i] if 0 <= i < len(ord_claves) else None


def _clave_grilla(*partes):
    """Sufijo corto y estable para la key de una grilla, a partir de lo que
    tiene que estrenarla cuando cambia (el período, el documento elegido).

    Un hash y no el texto: la clave de una compra lleva fecha, proveedor y
    documento («2026-09-12·DISTRIBUIDORA …·F0E001…»), y como key sería un
    nombre de clase CSS de 80 caracteres con puntos medios adentro."""
    txt = "|".join(str(p) for p in partes)
    return hashlib.md5(txt.encode("utf-8")).hexdigest()[:10]


@st.fragment
def _compras_semanal_drill(d, col_prod, col_fecha, col_cant, col_punit,
                           col_prov, col_docu, col_valor,
                           col_fam=None, d_full=None, col_subfam=None):
    """Compra por período (día/semana/mes/año o por documento) + detalle.

    `col_valor` entra como NOMBRE de columna y la serie numérica se arma
    acá: el dispatcher ya tenía una (`_valor`), pero pasar el Series
    ataría la firma a que el llamador la haya calculado antes.

    `col_fam`, `d_full` y `col_subfam` (2026-09-19, el filtro de Subfamilia)
    entran por palabra clave y con default a propósito.
    En Cloud, un commit que cambia la FIRMA de algo que `app.py` importa deja
    el `app.py` nuevo hablando con el paquete viejo de `sys.modules` (ver
    CLAUDE.md y `arquitectura.md` #357). Acá los dos módulos que cambian son
    del mismo paquete, así que quedan viejos JUNTOS y son consistentes, pero
    el default cuesta cero y cubre igual al llamador que todavía no los pasa.
    """
    _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    # ── Escalada a rerun COMPLETO tras un atajo de fecha ────────
    # La bandera del selector de fecha de esta tarjeta. El filtro
    # que consume ese rango vive en `app.py`, fuera de todo esto:
    # un clic aca re-ejecuta SOLO este fragment, que recibe `d` YA
    # filtrado por el ultimo rerun completo. Sin escalar, el estado
    # cambia y la pantalla no — boton que responde, datos quietos.
    # Va ANTES de dibujar nada para no gastar un render que se va a
    # descartar. Mismo mecanismo que `_cp_rank_atajo_pendiente`
    # (proveedor.py) y `_cp_prod_atajo_pendiente` (producto.py).
    # Ver arquitectura.md #180.
    #
    # OJO con DONDE va, que costo dos intentos medidos en vivo
    # (2026-09-04):
    #   · arriba de `renderizar_graficos_compras` no hace NADA — el
    #     dispatcher no se re-ejecuta en el rerun de una seccion,
    #     porque `seccion_perezosa` ya es un `@st.fragment`;
    #   · dentro del fragment de la SECCION escala bien pero deja
    #     esta tarjeta un gesto atras — ver el comentario del
    #     `@st.fragment` de arriba.
    #
    # Y LO QUE SE DIBUJA DESPUÉS DE ESTA LÍNEA SE PIERDE, que es el bug
    # reportado el 2026-09-09: el `rerun` aborta la corrida antes de que
    # los tres controles de la cabecera se registren, y Streamlit recolecta
    # el estado de todo widget de este fragment que no se dibujó. Se elegía
    # «Por documento», se movía la fecha, y el gráfico volvía a semanas con
    # la píldora todavía marcada. `preservar_widgets` los salva.
    if st.session_state.pop("_cp_sem_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")

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
        if not (col_prod and col_fecha):
            st.info("No hay columnas suficientes para este gráfico.")
            return

        # ── Las opciones de los dos selectores, ANTES de dibujarlos ──────
        # `extra` es un callable (en Streamlit el contenedor se elige
        # ENTRANDO en él), así que la lista tiene que estar armada cuando el
        # hook corre. Y el valor vigente se lee de `session_state`, que es
        # exactamente lo que va a mostrar el widget: una clave con `key`
        # sobrevive al rerun. Es el mismo arreglo que `vs_ano_pasado.py`
        # hizo subiendo sus widgets — leer el valor DESPUÉS de dibujar da el
        # del rerun anterior.
        #
        # FAMILIA: sus opciones salen del HISTÓRICO (`d_full`), no del rango.
        # Con la lista sacada de `d`, una familia elegida puede dejar de
        # estar entre las opciones al angostar la fecha, y Streamlit la
        # borra de la selección EN SILENCIO — el bug medido paso a paso que
        # documenta el bloque de los chips en `compras/__init__.py`. No le
        # disputa nada a esos chips: se aplica ENCIMA, y sus opciones son
        # las que los chips dejaron pasar (`d_full` ya viene filtrado por
        # ellos), así que acá no se puede elegir una familia que arriba está
        # excluida.
        _ops_fam = [_FAM_TODAS]
        _hay_fam = bool(col_fam) and col_fam in d.columns
        if _hay_fam:
            _src_fam = (d_full if (d_full is not None
                                   and col_fam in d_full.columns) else d)
            _ops_fam += sorted(_src_fam[col_fam].dropna().astype(str).unique())
        if st.session_state.get("compras_sem_familia") not in _ops_fam:
            st.session_state["compras_sem_familia"] = _FAM_TODAS
        _fam_prev = st.session_state.get("compras_sem_familia", _FAM_TODAS)

        # SUBFAMILIA (2026-09-19, a pedido): el mismo criterio que Familia
        # —opciones del HISTÓRICO, por el mismo borrado silencioso— y en
        # CASCADA: con una familia elegida ofrece sólo las suyas, igual que
        # los chips de la franja (`compras/__init__.py`). La que deja de
        # estar porque se cambió la familia vuelve a «todas».
        _ops_sub = [_SUB_TODAS]
        _hay_sub = bool(col_subfam) and col_subfam in d.columns
        if _hay_sub:
            _src_sub = (d_full if (d_full is not None
                                   and col_subfam in d_full.columns) else d)
            if (_hay_fam and _fam_prev != _FAM_TODAS
                    and col_fam in _src_sub.columns):
                _src_sub = _src_sub[_src_sub[col_fam].astype(str) == _fam_prev]
            _ops_sub += sorted(
                _src_sub[col_subfam].dropna().astype(str).unique())
        if st.session_state.get("compras_sem_subfamilia") not in _ops_sub:
            st.session_state["compras_sem_subfamilia"] = _SUB_TODAS
        _sub_prev = st.session_state.get("compras_sem_subfamilia", _SUB_TODAS)

        # El recorte que ya se sabe ANTES de dibujar, y del que salen las dos
        # listas ordenadas por valor: Proveedor y Producto. Se va angostando
        # en el orden de la fila, así que cada lista ofrece lo que dejan los
        # filtros de su izquierda.
        _mask = pd.Series(True, index=d.index)
        if _hay_fam and _fam_prev != _FAM_TODAS:
            _mask &= d[col_fam].astype(str) == _fam_prev
        if _hay_sub and _sub_prev != _SUB_TODAS:
            _mask &= d[col_subfam].astype(str) == _sub_prev

        # PROVEEDOR (2026-09-19, a pedido): se porta como Producto y no como
        # Familia — opciones del RANGO, ordenadas por valor de compra, y lo
        # elegido no se pierde al angostar la fecha (ver el párrafo de
        # Producto, que trae el porqué). Son ~200 nombres: el buscador propio
        # de `st.selectbox` es lo que lo hace usable.
        _hay_prov = bool(col_prov) and col_prov in d.columns
        _ops_prov = [_PROV_TODOS]
        if _hay_prov:
            _ops_prov += (_valor[_mask]
                          .groupby(d.loc[_mask, col_prov].astype(str))
                          .sum().sort_values(ascending=False)
                          .index.tolist())
        _prov_prev = st.session_state.get("compras_sem_proveedor")
        if _prov_prev is not None and _prov_prev not in _ops_prov:
            _ops_prov.append(_prov_prev)
        if _hay_prov and _prov_prev not in (None, _PROV_TODOS):
            _mask &= d[col_prov].astype(str) == _prov_prev

        # PRODUCTO: al revés que Familia, sus opciones salen del RANGO (`d`)
        # y ordenadas por valor de compra descendente. Las dos cosas son el
        # pedido: "top por valor de compra" es el top de lo que se está
        # mirando, no del histórico, y ofrecer los 1.588 productos del
        # parquet cuando el rango tiene 60 sería un selector peor (se podría
        # elegir algo sin ni una compra).
        #
        # Y lo elegido NO SE PIERDE cuando el rango se angosta: si el
        # producto vigente no está en la lista nueva se AGREGA al final en
        # vez de resetear. Una de las dos hay que hacer —`st.selectbox`
        # revienta con un valor que no está en `options`— y resetear es la
        # mala: el gráfico vuelve a "todos" sin que nadie lo pida. Así sale
        # vacío y un cartel dice por qué, que es un estado que el usuario
        # provocó y puede deshacer. Los CENTINELAS sí se resetean: "Top 20
        # por valor" no significa nada en un rango donde quedan 8 productos.
        _val_prod = (_valor[_mask]
                     .groupby(d.loc[_mask, col_prod].astype(str))
                     .sum().sort_values(ascending=False))
        _prods = _val_prod.index.tolist()
        _etiq_top = {f"Top {_n} por valor": _n for _n in _TOPS}
        _ops_prod = ([_PROD_TODOS]
                     + [_e for _e, _n in _etiq_top.items() if _n < len(_prods)]
                     + _prods)
        _prod_prev = st.session_state.get("compras_sem_producto")
        if _prod_prev is not None and _prod_prev not in _ops_prod:
            if _prod_prev == _PROD_TODOS or _prod_prev in _etiq_top:
                st.session_state["compras_sem_producto"] = _PROD_TODOS
            else:
                _ops_prod.append(_prod_prev)

        # ── La fila de cabecera: granularidad + los filtros + fecha ──────
        # 2026-09-04: el MISMO componente de fecha que el Ranking de
        # proveedores, no una copia — vive en
        # `base.py::selector_fecha_tarjeta` y escribe la clave canónica del
        # rango, así que mover la fecha acá mueve también a los otros dos
        # rankings. Es la tercera puerta al mismo dato, que es lo correcto
        # en una página apilada: el rango es del REPORTE, no de la vista.
        #
        # 2026-09-08: los tres controles de la IZQUIERDA (granularidad,
        # Familia, Producto) van dentro de UN contenedor horizontal, no
        # sueltos en la fila. La fila es un flex con `space-between`
        # (`_css_proveedor.py`): con cuatro items reparte el hueco entre
        # todos y los deja desperdigados a lo ancho de la tarjeta; con dos
        # vuelve a hacer lo que dice el CSS — el grupo pegado a la
        # izquierda, la fecha a la derecha. Sin `titulo_html`: esta tarjeta
        # no lleva título (el nombre de la sección lo pone el rail).
        #
        # La granularidad sigue sin `st.columns` alrededor a propósito: eso
        # era del `st.selectbox` que este control reemplazó (un dropdown SE
        # ESTIRA solo al ancho del contenedor). El toggle no se estira
        # —mide su propio contenido— y una columna lo apretaba a 157px,
        # forzando que "Por documento" envuelva a una segunda línea sin
        # necesidad. Medido con el inspector (`?debug=1&diseno=1`) el
        # 2026-09-03.
        #
        # 2026-09-17: de `st.pills` a `st.segmented_control`, a pedido («la
        # granularidad agrupada en un solo toggle que se vea lineal»). Las
        # píldoras sueltas se leían como cinco filtros que se suman; un
        # toggle pegado dice «una de cinco». `required=True` porque una
        # granularidad vacía no existe — con las píldoras, tocar la activa
        # la soltaba y la vista caía al default sin que nada lo marcara.
        #
        # Y la fila de KPI de la vista (regla #454) va en el MISMO flex, entre
        # los filtros y la fecha: es la suma de lo que esos dos acotan. Se
        # reserva acá con un `st.empty()` y se llena más abajo, cuando el
        # recorte ya existe — el orden de ejecución no es el de la pantalla.
        _box = {}

        def _controles():
            with st.container(horizontal=True, gap="small",
                              key="cp_sem_filtros"):
                _box["gran"] = st.segmented_control(
                    "Agrupar por", _GRAN_OPCIONES,
                    default=_GRAN_DEFAULT, required=True,
                    format_func=lambda g: _GRAN_ROTULO.get(g, g),
                    key="compras_sem_gran", label_visibility="collapsed")
                if _hay_fam and len(_ops_fam) > 1:
                    with st.container(key="cp_sem_hdr_familia"):
                        _box["fam"] = st.selectbox(
                            "Familia", _ops_fam, key="compras_sem_familia",
                            label_visibility="collapsed",
                            help="Acota ESTA tarjeta a una familia, encima "
                                 "de los chips de la franja. La lista "
                                 "ofrece sólo las que los chips dejan "
                                 "pasar.")
                if _hay_sub and len(_ops_sub) > 1:
                    with st.container(key="cp_sem_hdr_subfamilia"):
                        _box["sub"] = st.selectbox(
                            "Subfamilia", _ops_sub,
                            key="compras_sem_subfamilia",
                            label_visibility="collapsed",
                            help="Acota ESTA tarjeta a una subfamilia. Con "
                                 "una familia elegida ofrece sólo las "
                                 "suyas.")
                if _hay_prov:
                    with st.container(key="cp_sem_hdr_proveedor"):
                        _box["prov"] = st.selectbox(
                            "Proveedor", _ops_prov,
                            key="compras_sem_proveedor",
                            label_visibility="collapsed",
                            help="Ordenados por VALOR de compra en el rango, "
                                 "dentro de la familia y subfamilia "
                                 "elegidas. Se puede escribir para buscar.")
                with st.container(key="cp_sem_hdr_producto"):
                    _box["prod"] = st.selectbox(
                        "Producto", _ops_prod, key="compras_sem_producto",
                        label_visibility="collapsed",
                        help="Ordenados por VALOR de compra en el rango: el "
                             "primero es el que más compraste. «Top N por "
                             "valor» suma los N mayores en una sola serie. "
                             "Se puede escribir para buscar.")
            with st.container(key="cp_sem_kpi"):
                _box["kpi"] = st.empty()

        _ctx_fecha = selector_fecha_tarjeta(
            "cp_sem", "_cp_sem_atajo_pendiente", extra=_controles,
            categoria=CATEGORIA_SEC["compras_sec_semanal"])
        if _ctx_fecha is None:
            # El selector no dibuja NADA si la franja todavia no publico su
            # contexto, y con el se irian tambien los controles de la
            # izquierda, que son de esta vista y no de la fecha. En ese caso
            # se dibujan sueltos.
            _controles()
        gran = _box.get("gran") or _GRAN_DEFAULT
        fam_sel = _box.get("fam") or _FAM_TODAS
        sub_sel = _box.get("sub") or _SUB_TODAS
        prov_sel = _box.get("prov") or _PROV_TODOS
        prod_sel = _box.get("prod") or _PROD_TODOS

        # El RANGO de la tarjeta, como dos `date`: lo necesita la variación
        # contra la barra anterior para saber qué período quedó cortado
        # (#470). Es el mismo que recortó `d` en el dispatcher (`_d_sec`),
        # leído del mismo dueño. Sin contexto de fecha cae a lo que trae el
        # dato, que es a lo sumo más estricto de la cuenta.
        _rng = (rango_tarjeta(CATEGORIA_SEC["compras_sec_semanal"], _ctx_fecha)
                if _ctx_fecha else None)
        if _rng:
            _rng = tuple(pd.Timestamp(_x).date() for _x in _rng)

        # Cambiar de granularidad invalida el foco: una clave de "Semana" no
        # existe en el espacio de "Mes". Y cambiar cualquier filtro invalida
        # además el foco de COMPRA, que puede haber desaparecido del
        # recorte. Mismo guard que `compras_vol_prod_prev` en volatilidad.py
        # al cambiar de producto, con todo en una tupla: son varios motivos
        # para lo mismo.
        _ctx = (gran, fam_sel, sub_sel, prov_sel, prod_sel)
        if st.session_state.get("compras_sem_ctx_prev") != _ctx:
            st.session_state["compras_sem_ctx_prev"] = _ctx
            st.session_state["compras_sem_focus"] = None
            st.session_state["compras_sem_doc"] = None

        _fe   = pd.to_datetime(d[col_fecha], errors="coerce")
        _cnt  = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                if col_cant else pd.Series(0, index=d.index))
        _pu   = (pd.to_numeric(d[col_punit], errors="coerce")
                if col_punit else pd.Series(pd.NA, index=d.index))
        _prvs = d[col_prov].astype(str) if col_prov else pd.Series("", index=d.index)
        _docn = d[col_docu].astype(str) if col_docu else pd.Series("", index=d.index)

        dd = pd.DataFrame({
            # DOS columnas para el mismo dato, y a propósito. `docn` es el
            # valor CRUDO y sólo se usa para la identidad (entra en
            # `compra`, más abajo); `doc` es el que se muestra. En el parquet
            # el número viene codificado —`"F0E001000001328"` son 15
            # caracteres para decir `E001-1328`— y decodificarlo dentro de la
            # clave la ataría a un formateo de pantalla: un cambio ahí
            # invalidaría en silencio el `compras_sem_doc` guardado en
            # `session_state`. Ver `documento_legible` en `_comun.py`.
            "fecha": _fe, "prod": d[col_prod].astype(str), "prov": _prvs,
            "docn": _docn, "doc": documento_legible(_docn),
            "cant": _cnt, "punit": _pu, "valor": _valor,
            "fam": (d[col_fam].astype(str) if _hay_fam
                    else pd.Series("", index=d.index)),
            "sub": (d[col_subfam].astype(str) if _hay_sub
                    else pd.Series("", index=d.index)),
        }).dropna(subset=["fecha"])

        # Los filtros de la tarjeta, en el orden en que se leen.
        if _hay_fam and fam_sel != _FAM_TODAS:
            dd = dd[dd["fam"] == fam_sel]
        if _hay_sub and sub_sel != _SUB_TODAS:
            dd = dd[dd["sub"] == sub_sel]
        if _hay_prov and prov_sel != _PROV_TODOS:
            dd = dd[dd["prov"] == prov_sel]
        if prod_sel in _etiq_top:
            dd = dd[dd["prod"].isin(_prods[:_etiq_top[prod_sel]])]
        elif prod_sel != _PROD_TODOS:
            dd = dd[dd["prod"] == prod_sel]

        # El ÁMBITO va al título de la figura: con los filtros propios más
        # los chips de la franja, un gráfico que dice sólo "Compra por
        # semana" no deja saber de qué son esas barras.
        _amb = [_a for _a in (
                    None if fam_sel == _FAM_TODAS else fam_sel,
                    None if sub_sel == _SUB_TODAS else sub_sel,
                    (None if prov_sel == _PROV_TODOS
                     else _compras_truncar(nombre_propio(prov_sel))),
                    None if prod_sel == _PROD_TODOS else prod_sel)
                if _a]
        _tit_gran = {"Día": "por día", "Semana": "por semana",
                    "Mes": "por mes", "Año": "por año",
                    "Por documento": "por documento"}[gran]
        _titulo = (f"Compra {_tit_gran}"
                   + (" · " + " · ".join(_amb) if _amb else ""))

        if dd.empty:
            # El caso que hace el PIN de más arriba: el producto (o el
            # proveedor) sigue elegido y no tiene compras en este rango, o
            # los filtros se cruzan en vacío. El cartel nombra las dos
            # salidas porque las dos son válidas.
            st.info(f"**{_titulo}** — sin compras que mostrar. Ampliá el "
                    "rango de fechas (arriba a la derecha) o soltá algún "
                    "filtro de la tarjeta.")
            return

        # Clave de COMPRA: fecha+proveedor+documento, no el Nº
        # de documento solo (se repite entre proveedores que
        # reusan su propia numeración). Sin proveedor o
        # documento resuelto, cada FILA es su propia compra —
        # fallback defensivo, no bloquea la vista.
        _con_doc = bool(col_prov and col_docu)
        dd["compra"] = (
            dd["fecha"].dt.strftime("%Y-%m-%d") + "·" + dd["prov"] + "·" + dd["docn"]
            if _con_doc else dd.index.astype(str))

        # La fila de KPI de la cabecera (regla #454). Sale de `dd` ya
        # recortado por los filtros de la tarjeta: es el total de lo que las barras
        # suman, no el de la franja.
        if "kpi" in _box:
            _tot_v, _top_f, _resto_f = _familias_de(dd)
            _box["kpi"].markdown(
                _html_kpi_vista(_tot_v, dd["compra"].nunique(), _top_f,
                                _resto_f),
                unsafe_allow_html=True)

        if gran == "Por documento":
            dd["clave"] = dd["compra"]
            dd["lbl"] = dd["fecha"].dt.strftime("%d/%m")
            _rot_de = {}
        else:
            dd["clave"] = _periodo_serie(dd["fecha"], gran)
            # El NOMBRE del período (#470): «14–20 set» en el eje y «Semana
            # del lun 14 al dom 20 set 2026» en el hover, no «2026-S38». La
            # clave sigue siendo la de siempre —es la que ordena y la que
            # guarda el foco—; esto es sólo cómo se escribe. Por clave y no
            # por fila: son decenas de períodos contra miles de filas.
            _rot_de = {_c: _rotulo_periodo(_c, gran)
                       for _c in dd["clave"].unique()}
            dd["lbl"] = dd["clave"].map(lambda _c: _rot_de[_c][0])

        _orden = (dd.drop_duplicates("clave")[["clave", "lbl"]]
                 .sort_values("clave"))
        _ord_claves = _orden["clave"].tolist()
        _ord_lbls = _orden["lbl"].tolist()
        # El eje va por ÍNDICE, no por texto — ver el comentario largo del
        # `update_xaxes`, más abajo, que trae la medición de por qué.
        _ix = {_c: _i for _i, _c in enumerate(_ord_claves)}
        # Cuántos períodos hay decide cuánto entra en la etiqueta de cada
        # barra (`_plan_etiquetas`) y cada cuánto se rotula el eje.
        _n_per = len(_ord_claves)

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

        # El DÍA de cada período, indexado por clave. Lo piden dos cosas: el
        # calendario del eje (`_calendario_del_eje`, más abajo) y la primera
        # línea del hover. En las dos granularidades de grano diario cada
        # clave cae en un solo día, así que el `min` no promedia nada — es
        # sólo la forma de sacarlo del groupby.
        _dia_de = dd.groupby("clave")["fecha"].min().dt.date

        # La etiqueta del período viaja por `customdata` y no sale de
        # `%{x}`: la x de la traza es un ÍNDICE (ver el `update_xaxes`), así
        # que `%{x}` diría "17" en vez del nombre del período.
        g["ix"] = g["clave"].map(_ix)
        g["lbl"] = g["clave"].map(dict(zip(_ord_claves, _ord_lbls)))

        # El ENCABEZADO del hover, que no es la etiqueta del eje. En grano
        # diario el eje tiene que ser corto («Sáb» sobre «15/08»); el hover
        # no compite con nadie por el ancho, así que ahí va el día completo
        # con año — y en «Por documento», además, QUIÉN y CUÁL, que es lo
        # que el eje no puede decir con una barra por documento. Es el mismo
        # número de documento de la tabla y del caption: uno solo en toda la
        # vista, salido de `dd["doc"]`.
        #
        # `_de_compra` nace acá y lo vuelve a leer la tabla del modo Resumen,
        # que nombra sus filas igual que este hover. Se declara afuera del
        # `if` porque en las otras granularidades no existe, y allá la
        # pregunta «¿hay quién y cuál?» se contesta con `is None` y no
        # dependiendo de qué rama corrió.
        _de_compra = None
        if gran in ("Por documento", "Día"):
            _dias_g = g["clave"].map(_dia_de)
            # El feriado también se dice acá, y no por adorno: la anotación
            # de arriba se adelgaza sola cuando dos feriados son seguidos
            # (una por racha), así que el hover es el único lugar donde cada
            # barra contesta por sí misma.
            _fer = set()
            for _a in {_d.year for _d in _dias_g}:
                _fer |= cortes.feriados_peru(_a)
            g["hov"] = [
                f"{cortes.DIAS_ABR_ES[_d.weekday()].capitalize()} {_d:%d/%m/%Y}"
                + (" · feriado" if _d in _fer else "")
                for _d in _dias_g]
            if gran == "Por documento":
                _de_compra = dd.drop_duplicates("compra").set_index("compra")
                g["hov"] = (g["hov"] + "<br>"
                            + g["clave"].map(_de_compra["doc"]).fillna("")
                            + " · "
                            + g["clave"].map(_de_compra["prov"]).fillna("")
                                        .map(lambda _p: _compras_truncar(
                                            nombre_propio(_p))))
        else:
            g["hov"] = g["clave"].map(lambda _c: _rot_de[_c][1])

        # El desglose por familia de CADA barra, al final de su hover (regla
        # #454). Mismo texto para los tres tramos de un día: la pregunta es
        # por la barra, no por el tramo que quedó bajo el cursor.
        _fam_de = _familias_por_clave(dd)
        g["fam_hov"] = g["clave"].map(_fam_de).fillna("")

        # ── EL CLIC SE RESUELVE ANTES DE DIBUJAR (2026-09-13, #398 y #399) ─
        # La tarjeta mide lo que la de «Vs año pasado» con detalle o sin él,
        # y para eso la FIGURA le cede su sitio a la tabla: su alto depende de
        # si hay foco. Pero el foco lo escribe el clic, y el clic se leía del
        # valor que DEVUELVE `st.plotly_chart` — o sea con la figura ya
        # dibujada. En el rerun del clic, que es el que el usuario está
        # mirando, la tabla aparecía y el gráfico seguía con el alto de antes.
        #
        # Por eso se lee el MISMO evento de `session_state`, donde Streamlit
        # lo deja antes de que corra el script (el estado de un widget con
        # `key` se lee sin dibujarlo). Lo que `st.plotly_chart` devuelve se
        # IGNORA: ya se procesó acá, y procesarlo dos veces es un toggle
        # doble — un clic que no hace nada.
        #
        # Desde el 2026-09-19 va además ANTES DE ARMAR LA FIGURA, no sólo
        # antes del layout: cuánto de la etiqueta entra depende del alto de
        # la figura (`_plan_etiquetas`), y el alto, del foco.
        #
        # LA KEY ES UN CONTADOR, NO EL FOCO (regla #399). Leer antes de
        # dibujar obliga a leer de la key que se DIBUJÓ en la corrida
        # anterior, y con el foco en la key eso no se cumplía: en la corrida
        # del clic la key salía del foco de antes (K_none) y el foco ya era
        # A, así que la corrida siguiente buscaba el clic en K_A —un gráfico
        # que nadie había tocado— y el que el usuario hizo sobre K_none se
        # perdía. Medido: con un detalle abierto se perdía UN CLIC DE CADA
        # DOS. El contador sube con cada evento leído y en la MISMA corrida,
        # así que el gráfico ya se dibuja con la key donde se va a buscar el
        # próximo clic. Es la receta de Volatilidad (`compras_vol_nclic`).
        _foco_antes = st.session_state.get("compras_sem_focus")
        _doc_antes = st.session_state.get("compras_sem_doc")
        _nclic = st.session_state.get("compras_sem_nclic", 0)
        _key_base = f"compras_g_semanal_{gran}"
        _pt = _first_point(st.session_state.get(f"{_key_base}_{_nclic}"))
        if _pt is not None:
            # Todo evento leído se CONSUME, haya movido el foco o no: con la
            # key igual, la corrida siguiente lo volvería a leer.
            _nclic += 1
            st.session_state["compras_sem_nclic"] = _nclic
            # Toda traza es una barra (o un tramo de barra) desde que se
            # fueron los puntos (2026-09-19): su x es el ÍNDICE del período
            # (eje lineal), así que hay que traducirla — el foco se guarda
            # como CLAVE, que es lo que compara la tabla de abajo.
            _clic = _clave_del_clic(_pt.get("x"), _ord_claves)
            # Con una compra en foco, la barra SUBE un nivel (vuelve al
            # período entero) en vez de apagarlo todo: apagar obligaría a
            # dos clics para deshacer uno.
            if _clic is None:
                pass
            elif _doc_antes:
                st.session_state["compras_sem_doc"] = None
                st.session_state["compras_sem_focus"] = _clic
            else:
                st.session_state["compras_sem_focus"] = (
                    None if _foco_antes == _clic else _clic)
        _key_graf = f"{_key_base}_{_nclic}"
        _focus = st.session_state.get("compras_sem_focus")
        _doc = st.session_state.get("compras_sem_doc")
        # Las mismas dos condiciones eligen la rama de la tabla, más abajo:
        # si una dijera que hay tabla y la otra no, la tarjeta cambiaría de
        # alto — que es justo lo que este bloque viene a evitar.
        _doc_ok = _doc is not None and _doc in set(dd["compra"])
        _foco_ok = _focus in set(dd["clave"])
        _con_detalle = _doc_ok or _foco_ok
        # EL MODO SE LEE DE `session_state` Y NO DEL WIDGET, por lo mismo que
        # el clic de acá arriba: el toggle se dibuja DEBAJO de la figura
        # —que es donde gobierna— y el alto de la figura depende de él. Una
        # clave con `key` se lee sin dibujarla, y en la corrida del clic ya
        # trae el valor nuevo, así que leerla acá no atrasa un gesto. El
        # widget de más abajo no devuelve nada distinto: por eso se ignora
        # lo que devuelve, igual que `st.plotly_chart`.
        _modo = st.session_state.get("compras_sem_modo")
        if _modo not in _MODO_OPCIONES:
            _modo = _MODO_DEFAULT
        # Resumen no necesita foco: su tabla son TODAS las barras. Por eso
        # la figura cede su sitio también ahí, y la zona de abajo deja de
        # tener un estado vacío.
        _con_tabla = _con_detalle or _modo == _MODO_RESUMEN
        _alto_fig = (alturas.COMPACTO if _con_tabla else _ALTO_FIG_SOLO)

        # ── LA ETIQUETA DE CADA BARRA (#440, #454 y #470) ────────────────
        # El total, los documentos debajo y la variación contra la barra
        # anterior, y de eso lo que ENTRA: `_plan_etiquetas` decide la forma
        # y cuántos renglones, contra los píxeles del slot y el alto de la
        # figura. Todo alineado al eje (`_ord_claves`); lo que no entra
        # sigue en el hover, que lo dice siempre.
        _de_g = g.set_index("clave")
        _tot = _de_g["valor"].reindex(_ord_claves).tolist()
        _ndocs = (dd.groupby("clave")["compra"].nunique()
                    .reindex(_ord_claves).fillna(0).astype(int).tolist())
        _vars = (_variaciones(_ord_claves, _tot, gran, _rng)
                 if gran in _GRAN_VARIACION else [None] * _n_per)
        # Contra QUIÉN se compara, dicho como lo dice el eje: «Sáb 12/09»,
        # «7–13 set», «ago 2026».
        _nombre_corto = [
            (f"{cortes.DIAS_ABR_ES[_dia_de[_c].weekday()].capitalize()} "
             f"{_dia_de[_c]:%d/%m}") if gran == "Día" else _l
            for _c, _l in zip(_ord_claves, _ord_lbls)]
        _var_hov = [
            _hover_variacion(_v, gran, _c,
                             (_nombre_corto[_v[2]]
                              if _v and _v[2] is not None else ""), _rng)
            for _c, _v in zip(_ord_claves, _vars)]
        _docs_hov = [f" · {_n:,} doc" + ("" if _n == 1 else "s")
                     for _n in _ndocs]

        _textos, _plan_etq, _alto_etq = [None] * _n_per, None, 0
        if gran in _GRAN_CON_ETIQUETA:
            _reng = [_renglones_etiqueta(fmt_k(_v) if _v else None, _n,
                                         _var, gran)
                     for _v, _n, _var in zip(_tot, _ndocs, _vars)]
            _plan_etq, _k_etq, _alto_etq = _plan_etiquetas(
                _n_per, [[_p for _p, _ in _r] for _r in _reng], _alto_fig)
            if _plan_etq:
                _sep = _ETQ_SEP if _plan_etq == "unida" else "<br>"
                _textos = [(_sep.join(_h for _, _h in _r[:_k_etq]) or None)
                           for _r in _reng]
        # `constraintext="none"`: sin él Plotly ENCOGE la etiqueta que no
        # entra en la barra en vez de dejarla afuera a su tamaño.
        _estilo_etq = dict(
            textposition="outside", cliponaxis=False, constraintext="none",
            textangle=-90 if _plan_etq in ("girada", "unida") else 0,
            textfont=dict(size=_ETQ_FUENTE, color=TEXTO_PRINCIPAL))

        fig = go.Figure()
        _partida = gran in _GRAN_PARTIDA
        if _partida:
            # ── La barra partida en tres (ver el bloque de `_TRAMOS`) ────
            # El apilado va de la mayor ABAJO hacia la cola arriba: Plotly
            # apila en el orden en que se agregan las trazas, y el orden del
            # color es el orden del dato.
            _hov = _de_g["hov"].reindex(_ord_claves).tolist()
            _famh = _de_g["fam_hov"].reindex(_ord_claves).tolist()
            _rot_total = _TOTAL_DEL_PERIODO.get(gran, "Total del período")
            _tramos = _tramos_del_periodo(dd, _ord_claves)
            _textos_tr = (_etiqueta_en_la_punta(_tramos, _textos)
                          if _plan_etq else [None] * len(_tramos))
            _xs = list(range(_n_per))
            for _i, (_tr, (_, _, _rot)) in enumerate(zip(_tramos, _TRAMOS)):
                # El detalle del hover es distinto en el primero: ahí hay UNA
                # compra y se la puede nombrar. En los otros dos la pregunta
                # es cuántas son, no cuál.
                if _i == 0:
                    _det = [_compras_truncar(nombre_propio(_p))
                            + (f" · {_d}" if _d else "")
                            for _p, _d in zip(_tr["prov"].fillna(""),
                                              _tr["doc"].fillna(""))]
                else:
                    _det = [f"{_n} compra" + ("" if _n == 1 else "s")
                            for _n in _tr["n"]]
                fig.add_bar(
                    x=_xs, y=_tr["valor"], name=_rot,
                    marker=dict(color=SERIE_TRAMOS[_i]),
                    customdata=list(zip(_hov, _det, _tot, _famh, _docs_hov,
                                        _var_hov)),
                    hovertemplate=("%{customdata[0]}"
                                   f"<br><b>{_rot}</b>: S/ %{{y:,.2f}}"
                                   "<br>%{customdata[1]}"
                                   f"<br>{_rot_total}: "
                                   "S/ %{customdata[2]:,.2f}"
                                   "%{customdata[4]}"
                                   "%{customdata[5]}"
                                   "%{customdata[3]}"
                                   "<extra></extra>"),
                )
                if _plan_etq:
                    fig.data[-1].update(text=_textos_tr[_i], **_estilo_etq)
            # `stack` sólo acá: en «Por documento» la figura tiene una sola
            # traza y apilar no significa nada.
            fig.update_layout(barmode="stack")
        else:
            fig.add_bar(
                x=g["ix"], y=g["valor"], name="Valor total",
                marker=dict(color=SERIE_PRINCIPAL),
                customdata=g[["hov", "cant", "fam_hov"]].to_numpy(),
                hovertemplate=("%{customdata[0]}<br>Valor: S/ %{y:,.2f}"
                               "<br>Cantidad: %{customdata[1]:,.1f}"
                               "%{customdata[2]}"
                               "<extra></extra>"),
            )
            # ── El total, escrito encima de cada barra (#440 y #454) ────
            # Por clave y no por posición: la traza va en el orden de `g`, y
            # `_textos` en el del eje.
            if _plan_etq:
                _txt_de = dict(zip(_ord_claves, _textos))
                fig.data[0].update(text=[_txt_de.get(_c) for _c in g["clave"]],
                                   **_estilo_etq)

        # ── EL FOCO SE MARCA A MANO (regla #399) ────────────────────────
        # Con la key del foco, en la corrida del clic la barra quedaba
        # resaltada: era la selección de Plotly, que atenúa todo lo demás.
        # Con la key nueva el gráfico nace sin selección y esa marca se iba.
        # Se pinta la misma atenuación desde acá, y así además DURA: la de
        # Plotly se borraba en el rerun siguiente con la tabla todavía
        # abierta, porque ahí la key ya cambiaba. NO con `selectedpoints`:
        # una barra que Plotly cree seleccionada se DESELECCIONA al tocarla
        # (`selectOnClick` en su código), eso llega como selección vacía, y
        # el clic para cerrar el detalle no haría nada.
        if _con_detalle and _partida:
            # Las tres trazas comparten el eje `_ord_claves`, así que la
            # misma lista de opacidades sirve para las tres: lo que se marca
            # es el PERÍODO, y un período en foco se ilumina entero.
            _op = [1.0 if _c == _focus else _ATENUADO for _c in _ord_claves]
            for _tr in fig.data:
                _tr.marker.opacity = _op
        elif _con_detalle:
            fig.data[0].marker.opacity = [
                1.0 if _c == _focus else _ATENUADO for _c in g["clave"]]

        _compras_layout(fig, alto=_alto_fig)
        if _plan_etq:
            _rng_y = _techo_etiquetas(float(g["valor"].max()),
                                      float(g["valor"].min()),
                                      _alto_fig, _alto_etq)
            if _rng_y:
                fig.update_yaxes(range=_rng_y)
        fig.update_layout(
            title=_titulo,
            # `y` sale de `_LEYENDA_Y`: la cuenta del techo de las etiquetas
            # depende de dónde va la leyenda.
            legend=dict(orientation="h", y=-_LEYENDA_Y, x=0,
                        font=dict(size=10)),
            # Era explícito por los puntos, que tenían que ganarle el hover a
            # la barra de abajo. Sin puntos no arbitra nada, pero sigue siendo
            # el default de Plotly y el que las trazas apiladas necesitan.
            hovermode="closest",
        )
        # ── EL EJE ES LINEAL, Y NO POR GUSTO ────────────────────────────
        # Era `type="category"` con `categoryarray=_ord_claves` hasta el
        # 2026-09-08. Con eso, los puntos desplazados a media categoría no
        # se podían dibujar: Plotly NO interpreta una x numérica como
        # posición dentro del slot, la agrega como UNA CATEGORÍA MÁS.
        # Medido en el navegador con datos reales (53 semanas, 424 puntos):
        #
        #     xaxis._categories.length   477   (= 53 + 424, uno por punto)
        #     xaxis.range                [-0.5, 504.5]
        #     px por slot                1,94   sobre 978px de lienzo
        #
        # Los puntos se fueron el 2026-09-19 y el eje se quedó lineal: el
        # calendario de los días (bandas, punteadas, `add_vrect` en
        # `i ± 0.5`) y la traducción del clic (`_clave_del_clic`) hablan
        # en índices, y una clave como «2025» en un eje de categorías
        # volvería a hacer que Plotly la lea como número (#448). El precio
        # es que las etiquetas hay que ponerlas a mano (`tickmode="array"`).
        # `range` explícito porque el autorange de un eje lineal pone su
        # propio aire a los costados y la primera y la última barra
        # quedaban flotando media barra adentro del margen.
        # ── El calendario, en las dos granularidades de grano diario ────
        # Dibuja las bandas y las punteadas, y devuelve SUS rótulos (uno por
        # día) para reemplazar a los de abajo. Devuelve `None` cuando el
        # rango es tan ancho que un rótulo por día ya no entra — ahí se cae
        # a las etiquetas de siempre, que es lo correcto: a 200 días la
        # pregunta que se está haciendo no es de qué día es cada barra.
        _ticks = None
        if gran in ("Por documento", "Día"):
            _ticks = _calendario_del_eje(
                fig, [_dia_de[_c] for _c in _ord_claves],
                sep=("dia" if gran == "Por documento" else "semana"))

        # Un tick por período sólo mientras se puedan leer. Con la franja en
        # todo el histórico son 192 semanas: `tickmode="array"` dibuja TODAS
        # las que se le den —no las adelgaza como el modo automático—, así
        # que el paso mantiene el primero y va salteando. Cuántos entran
        # sale del rótulo MÁS LARGO (#470): «31 ago–6 set» pide el triple
        # que «2026», y el 17 fijo de antes se había medido con «2026-S17».
        if _ticks is None:
            _largo_tick = max((len(_t) for _t in _ord_lbls), default=1)
            _caben = max(1, int(_LIENZO_PX // (_largo_tick * _TICK_PX_CARACTER
                                               + _TICK_AIRE)))
            _paso = max(1, -(-_n_per // _caben))
            _tv = list(range(0, _n_per, _paso))
            _tt = [_ord_lbls[_i] for _i in _tv]
            if gran == "Semana":
                # El año, debajo del primer rótulo y cada vez que cambia —
                # como un eje de fechas de Plotly—, y no en cada semana.
                _ult = None
                for _j, _i in enumerate(_tv):
                    _a = _anio_semana(_ord_claves[_i])
                    if _a != _ult:
                        _tt[_j] += f"<br>{_a}"
                        _ult = _a
            _ticks = (_tv, _tt)
        fig.update_xaxes(
            type="linear", tickmode="array",
            tickvals=_ticks[0], ticktext=_ticks[1],
            range=[-0.5, _n_per - 0.5])

        # Clic en una barra -> foco de la tabla de abajo. La
        # selección de on_select persiste mientras la key no cambie, así que
        # con key estática cada rerun re-lee el mismo punto y togglea para
        # siempre (parpadeo). Por eso la key cambia — pero con el CONTADOR de
        # arriba, no con el foco (CLAUDE.md, arquitectura.md #76 y #399).
        #
        # El clic ya se resolvió ARRIBA, antes de armar el layout (ver «EL
        # CLIC SE RESUELVE ANTES DE DIBUJAR»): lo que devuelve esta llamada
        # no se lee, a propósito.
        st.plotly_chart(
            fig, use_container_width=True, on_select="rerun",
            selection_mode="points", key=_key_graf)

        # ── LA FILA QUE ELIGE QUÉ SE VE ABAJO (2026-09-19, regla #476) ───
        # A pedido: «podemos alternar esa zona donde aparecen estas dos
        # tarjetas abajo, con una donde aparezca la información de las
        # columnas pero por fila».
        #
        # VA DEBAJO DEL GRÁFICO Y NO EN LA CABECERA, que es donde gobierna:
        # la cabecera dice QUÉ ENTRA en las barras (fecha, familia,
        # producto) y esta fila dice QUÉ SE LEE de ellas. Mismo criterio que
        # los controles de «Vs año pasado», que bajaron a la tarjeta que
        # mandan (regla #445).
        #
        # Y COMPARTE RENGLÓN CON EL CAPTION del ámbito, que hasta hoy vivía
        # al pie de la tarjeta: un renglón propio habría costado 47px de
        # figura y compartido cuesta 10 (`alturas.FRANJA_MODO_SEMANAL`).
        # De paso el caption pasó a leerse como el título de las tablas, que
        # es lo que siempre fue.
        #
        # El caption se RESERVA acá y se escribe al final: su texto nombra
        # el ámbito, que en modo Detalle sale del período en foco — ochenta
        # líneas más abajo. Mismo `st.empty()` que la fila de KPI de la
        # cabecera, y por lo mismo: el orden de ejecución no es el de la
        # pantalla.
        #
        # Lo que devuelve el toggle se IGNORA a propósito: el modo ya se
        # leyó de `session_state` antes de la figura, porque su alto depende
        # de él (ver «EL MODO SE LEE DE session_state»).
        with st.container(horizontal=True, gap="small", key="cp_sem_pie"):
            st.segmented_control(
                "Qué se ve abajo", _MODO_OPCIONES, default=_MODO_DEFAULT,
                required=True, key="compras_sem_modo",
                label_visibility="collapsed", help=_AYUDA_MODO)
            _pie = st.empty()

        # ── MODO RESUMEN: el gráfico escrito como tabla ──────────────────
        # Una fila por BARRA, en el orden del eje, con lo que dice su
        # etiqueta (total, documentos, variación) más el % de la vista y las
        # líneas — y la fila TOTAL abajo. No depende del foco: son todas las
        # barras, así que esta rama no tiene estado vacío.
        if _modo == _MODO_RESUMEN:
            # EL NOMBRE DE CADA FILA es el de su barra, dicho como lo dice
            # el gráfico y no como lo guarda la clave: la tabla y el eje
            # tienen que poder leerse uno contra el otro. La semana suma el
            # año que el eje escribe aparte (`_anio_semana`), porque en una
            # columna no hay un renglón de abajo donde ponerlo; el día trae
            # el encabezado de su hover, que ya dice «Mar 15/09/2026» y el
            # feriado; y en «Por documento» la barra es una compra, así que
            # se la nombra con fecha, documento y proveedor.
            if gran == "Semana":
                _lbl_fila = [f"{_l} {_anio_semana(_c)}"
                             for _c, _l in zip(_ord_claves, _ord_lbls)]
            elif gran == "Mes":
                _lbl_fila = [_rot_de[_c][1] for _c in _ord_claves]
            elif gran == "Día":
                _hov_de = dict(zip(g["clave"], g["hov"]))
                _lbl_fila = [_hov_de.get(_c, _c) for _c in _ord_claves]
            elif gran == "Por documento" and _de_compra is not None:
                _prov_de = _de_compra["prov"]
                _lbl_fila = [
                    f"{_dia_de[_c]:%d/%m/%Y} · "
                    f"{_de_compra['doc'].get(_c) or '—'} · "
                    f"{_compras_truncar(nombre_propio(_prov_de.get(_c, '')))}"
                    for _c in _ord_claves]
            else:
                _lbl_fila = list(_ord_lbls)

            _nlin = (dd.groupby("clave").size().reindex(_ord_claves)
                       .fillna(0).astype(int).tolist())
            _tot_vista = float(sum(_tot))
            _uni = _UNIDAD_GRAN[gran][0 if _n_per == 1 else 1]

            # ── UNA COLUMNA POR FAMILIA (2026-09-20, a pedido) ───────────
            # «Añadamos los datos por familia a la tabla». Son LAS MISMAS
            # que las tarjetas de KPI de la cabecera —salen de la misma
            # `_familias_de`, o sea las cuatro mayores y el resto sumado—,
            # y eso no es economía de código: la cabecera ya las nombra, y
            # dos listas de familias distintas en la misma tarjeta se leen
            # como dos cosas distintas.
            #
            # Con UNA sola familia en la vista no se desglosa nada, por lo
            # mismo que la KPI no lo hace: la columna repetiría Valorizado.
            _, _top_f, _resto_f = _familias_de(dd)
            _cols_fam, _dat_fam, _tot_fam = [], {}, {}
            if len(_top_f) + _resto_f[0] > 1:
                _por_fam = (dd.groupby(["clave", "fam"])["valor"].sum()
                              .unstack("fam").reindex(_ord_claves)
                              .fillna(0.0))
                _acum = [0.0] * _n_per
                for _i, (_f, _v, _) in enumerate(_top_f):
                    _col = f"fam_{_i}"
                    _serie = (_por_fam[_f] if _f in _por_fam.columns
                              else pd.Series(0.0, index=_por_fam.index))
                    _vals = [float(_x) for _x in _serie]
                    _dat_fam[_col] = _vals
                    _acum = [_a + _x for _a, _x in zip(_acum, _vals)]
                    _cols_fam.append((_col, _nombre_familia(_f)))
                    _tot_fam[_col] = fmt_k(_v)
                if _resto_f[0]:
                    # El resto NO se vuelve a sumar por familia: es lo que
                    # queda del total de la barra, que ya está calculado.
                    # Así la fila cierra por construcción — las columnas
                    # suman Valorizado exacto, sin un centavo de diferencia
                    # por redondeo.
                    _col = f"fam_{len(_top_f)}"
                    _dat_fam[_col] = [max(float(_t) - float(_a), 0.0)
                                      for _t, _a in zip(_tot, _acum)]
                    _cols_fam.append((_col, f"{_resto_f[0]} más"))
                    _tot_fam[_col] = fmt_k(_resto_f[1])
            # La variación viaja como NÚMERO para que la columna se ordene;
            # el motivo de las que no tienen, en dos columnas ocultas (qué
            # escribir y por qué). Mismo criterio que la etiqueta de la
            # barra: «parcial» no es un dato faltante, es una respuesta.
            _notas = [
                _nota_variacion(_v, gran, _c,
                                (_nombre_corto[_v[2]]
                                 if _v and _v[2] is not None else ""), _rng)
                for _c, _v in zip(_ord_claves, _vars)]
            _tp_per = pd.DataFrame({
                "periodo": _lbl_fila,
                "valor": [float(_v) for _v in _tot],
                "parte": [(_v / _tot_vista if _tot_vista else 0.0)
                          for _v in _tot],
                "docs": _ndocs,
                "lineas": _nlin,
                "variacion": [(_v[1] if _v and _v[0] == "ok" else None)
                              for _v in _vars],
                "__vtxt": [("parcial" if _v and _v[0] == "parcial" else "—")
                           for _v in _vars],
                **_dat_fam,
                "__nota": _notas,
                "__sel": [_c == _focus for _c in _ord_claves],
            })
            # LA FILA TOTAL DICE ADEMÁS DE QUÉ HABLA LA TABLA: cuántas
            # filas, con qué grano están agrupadas y qué rango cubren
            # (2026-09-20, a pedido: «la tabla debe indicar Del…Al y cómo
            # está agrupado. No debe agregar alguna fila más, usemos alguna
            # fila que ya exista»). Va acá y en el caption de la fila de
            # modo, que son las dos filas que YA existían; el grano lo dice
            # la unidad («5 semanas»), que es la misma palabra con la que
            # se cuentan las filas.
            _tot_per = {
                "periodo": f"Total · {_n_per:,} {_uni}",
                "valor": f"S/ {_tot_vista:,.2f}",
                # El 100% se escribe entero y no con el decimal de la
                # columna: es la definición del total, no una cuenta que
                # pueda dar 99.9.
                "parte": "100%",
                "docs": f"{sum(_ndocs):,}",
                "lineas": f"{sum(_nlin):,}",
                # Sin variación: sumar los porcentajes de períodos distintos
                # no mide nada, y el total del rango no tiene contra qué
                # compararse acá.
                "variacion": "", "__vtxt": "", "__nota": "", "__sel": False,
                **_tot_fam,
            }
            # La key NO lleva el foco: la fila marcada la pone
            # `rowClassRules` sobre la grilla viva (regla #441), y
            # estrenarla en cada clic le borraría al usuario el orden que
            # acaba de elegir (regla #471). Sí lleva lo que cambia las
            # FILAS: la granularidad, los filtros y el rango.
            with st.container(key="cp_sem_resumen"):
                renderizar_periodos_semanal(
                    _tp_per, altura=_ALTO_TABLA,
                    key=("compras_sem_per_grid_"
                         + _clave_grilla(gran, _ctx, _rng)),
                    rotulo_periodo=("Documento" if gran == "Por documento"
                                    else "Período"),
                    ver_docs=gran in _GRAN_CON_DOCS,
                    ver_variacion=gran in _GRAN_VARIACION,
                    familias=_cols_fam, total=_tot_per)
            _pie.caption(
                f"**{_del_al(dd['fecha'])}** · agrupado por "
                f"{_AGRUPADO_GRAN[gran]} — una fila por barra, en el orden "
                "del eje; un clic en la cabecera lo cambia.")
            return

        # El CAPTION es un elemento simple: un `if/else`
        # desnudo lo reconcilia bien (mismo conteo de
        # elementos en los tres branches, sólo cambia el
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
        # `_focus` y `_doc` ya vienen resueltos de antes de la figura.
        #
        # Desde el 2026-09-14 el hueco lleva DOS grillas y no un
        # `st.dataframe` (regla #440).
        #
        # 2026-09-19: EL `st.empty()` QUEDA SÓLO EN LA RAMA SIN DETALLE, y es
        # lo que hace que las tablas se puedan ordenar (regla #471).
        # `st.empty()` manda en CADA corrida un elemento vacío a su lugar, y
        # ese elemento REEMPLAZA al bloque que había: todo lo de adentro se
        # re-monta. Medido en el navegador marcando los nodos: tras un clic en
        # un documento se reemplazaba el iframe de la grilla —con la MISMA
        # key— y con él se perdía el orden que el usuario acababa de elegir.
        # Ahora, en la misma posición, la rama con detalle pone un
        # `st.container` con key, que entre dos corridas con detalle es el
        # mismo bloque; y la rama sin detalle sigue poniendo el `st.empty()`,
        # que es lo que borra las grillas al cerrar el detalle sin dejar
        # huérfanos (#70). Mismo conteo de elementos en las dos ramas: hueco
        # y caption.
        if not _con_detalle:
            st.empty()
            _pie.caption("Tocá una barra para ver sus documentos.")
            return
        _hueco_tabla = st.container(key="cp_sem_detalle")

        # ── EL DETALLE, EN DOS TABLAS (2026-09-14, a pedido, regla #440) ─
        # «que la tabla de abajo se divida en dos: una que muestre el
        # documento, y al hacer clic muestre en otra tabla del costado el
        # detalle». A la izquierda, una fila por COMPRA del período en foco;
        # a la derecha, las LÍNEAS de la elegida. Las dos miden
        # `SEMANAL_TABLA`, lo que medía la tabla única: la tarjeta sigue
        # midiendo lo mismo con foco o sin él (#398).
        #
        # QUÉ COMPRAS lista la de la izquierda: las del período de la barra.
        # En «Por documento» la barra YA es una compra, y listarla sola sería
        # una tabla de una fila: ahí la lista son las compras de SU DÍA, que
        # es la unidad que el eje agrupa con las punteadas.
        if gran == "Por documento":
            _dia = dd.loc[dd["compra"] == _focus, "fecha"].iloc[0].normalize()
            _amb = dd[dd["fecha"].dt.normalize() == _dia]
            _id_amb = f"{_dia:%Y-%m-%d}"
        else:
            _id_amb = (_focus if _foco_ok
                       else dd.loc[dd["compra"] == _doc, "clave"].iloc[0])
            _amb = dd[dd["clave"] == _id_amb]
        _docs = (_amb.groupby("compra", as_index=False)
                     .agg(fecha=("fecha", "min"), doc=("doc", "first"),
                          prov=("prov", "first"), lineas=("valor", "size"),
                          valor=("valor", "sum"))
                     .sort_values(["valor", "compra"], ascending=[False, True])
                     .reset_index(drop=True))

        # QUÉ COMPRA muestra la de la derecha: la elegida con un clic en la
        # tabla; en «Por documento», la de la
        # barra; y si no hay ninguna, la MAYOR del período, que es la primera
        # fila. Así la tabla de al lado nunca está vacía, el mismo criterio
        # que `drill_tablas.tabla_ranking(abrir_en_mayor=True)`.
        if _doc_ok:
            _sel = _doc
        elif gran == "Por documento":
            _sel = _focus
        else:
            _sel = _docs["compra"].iloc[0]
        _lin = _amb[_amb["compra"] == _sel].sort_values("valor",
                                                        ascending=False)

        # Los números y la fecha viajan CRUDOS (la fecha en ISO) desde el
        # 2026-09-19: las dos tablas se ordenan con clic en la cabecera, y
        # un monto ya formateado se ordena como texto. El formato lo pone la
        # grilla (`tablas/compras_semanal.py`, regla #471).
        _tp_docs = pd.DataFrame({
            "fecha": _docs["fecha"].dt.strftime("%Y-%m-%d"),
            "doc": _docs["doc"].fillna("").map(lambda v: v or "—"),
            # Como nombre propio, que es lo que se MUESTRA; la clave de
            # la compra sigue con el nombre crudo.
            "prov": [nombre_propio(_p) for _p in _docs["prov"]],
            "lineas": _docs["lineas"].astype(int),
            "valor": _docs["valor"].astype(float).round(2),
            "__compra": _docs["compra"],
            "__sel": _docs["compra"] == _sel,
        })
        _tp_lin = pd.DataFrame({
            "prod": _lin["prod"],
            "cant": pd.to_numeric(_lin["cant"], errors="coerce").round(3),
            "punit": pd.to_numeric(_lin["punit"], errors="coerce").round(4),
            "valor": _lin["valor"].astype(float).round(2),
        })

        # ── Las filas TOTAL de las dos tablas (2026-09-17, regla #454) ────
        # A pedido: «la de documentos, totales de líneas y valor, y la de
        # detalle, total de valor». La de líneas NO suma la cantidad: son
        # kilos, litros y unidades en la misma columna, y su suma no mide
        # nada. El rótulo va en la primera columna VISIBLE — en «Por
        # documento» la fecha está oculta, y un «Total» en una columna oculta
        # es una fila sin nombre.
        _n_docs = len(_docs)
        _tot_docs = {
            "fecha": "", "doc": "",
            "prov": f"{_n_docs} compra" + ("" if _n_docs == 1 else "s"),
            "lineas": f"{int(_docs['lineas'].sum()):,}",
            "valor": f"S/ {_docs['valor'].sum():,.2f}",
        }
        _col_rot = ("fecha" if gran != "Por documento"
                    else ("doc" if col_docu else None))
        if _col_rot:
            _tot_docs[_col_rot] = "Total"
        else:
            _tot_docs["prov"] = f"Total · {_tot_docs['prov']}"
        _n_lin = len(_lin)
        _tot_lin = {
            "prod": f"Total · {_n_lin} línea" + ("" if _n_lin == 1 else "s"),
            "cant": "", "punit": "",
            "valor": f"S/ {_lin['valor'].sum():,.2f}",
        }

        with _hueco_tabla:

            # columnas-internas: las dos tablas del detalle, DENTRO de la
            # tarjeta de la vista; no es una fila de drill que tenga que caer
            # en el eje de `COLUMNAS_DRILL`. La de documentos lleva cinco
            # columnas contra cuatro, de ahí el 1.15.
            _c_docs, _c_lin = st.columns([1.15, 1], gap=GAP_DRILL)
            with _c_docs:
                # LA KEY LLEVA LO QUE CAMBIA LAS FILAS, NO LA FILA ELEGIDA
                # (2026-09-19, regla #471): el período, los filtros, el rango
                # y el contador de clics del gráfico. Con la compra elegida
                # adentro —como era hasta ese día— cada clic estrenaba grilla
                # y le borraba al usuario el orden que acababa de elegir. El
                # contador está porque un clic en la barra del MISMO período
                # le devuelve el foco al período entero: sin estrenar la
                # grilla, la selección vieja que ésta sigue devolviendo lo
                # volvería a llevar a la compra de antes.
                _k_tablas = _clave_grilla(gran, _id_amb, _ctx, _rng, _nclic)
                _clic = renderizar_documentos_semanal(
                    _tp_docs, altura=_ALTO_TABLA,
                    key=f"compras_sem_docs_grid_{_k_tablas}",
                    ver_fecha=gran != "Por documento",
                    ver_doc=bool(col_docu), total=_tot_docs)
            with _c_lin:
                # La MISMA key que la de al lado, sin la compra elegida: sus
                # filas cambian con cada clic, pero el orden que el usuario
                # eligió para las líneas (por cantidad, por precio) se
                # mantiene al pasar de un documento a otro. Las filas nuevas
                # y la fila TOTAL las recibe la grilla viva (`st_aggrid` le
                # pasa `rowData` y `gridOptions` sin re-montarla).
                renderizar_lineas_semanal(
                    _tp_lin, altura=_ALTO_TABLA,
                    key=f"compras_sem_lineas_grid_{_k_tablas}",
                    total=_tot_lin)

        # El caption NOMBRA el ámbito y nada más: cuántas compras y cuánto
        # suman lo dicen ahora las filas TOTAL, y dos lugares con el mismo
        # número son dos lugares donde pueden diferir.
        if gran == "Por documento":
            _nombre_amb = (f"{cortes.DIAS_ABR_ES[_dia.weekday()].capitalize()} "
                           f"{_dia:%d/%m/%Y} · las compras del día")
        elif gran == "Día":
            # El encabezado del hover («Mar 15/09/2026») y no la clave
            # («2026-09-15»): es el mismo día dicho como lo dice el gráfico.
            _nombre_amb = dict(zip(g["clave"], g["hov"])).get(
                _id_amb, _amb["lbl"].iloc[0])
        else:
            # «Semana del lun 14 al dom 20 set 2026», no «14–20 set» (#470):
            # el caption no compite por ancho, así que va el nombre largo.
            _nombre_amb = _rot_de.get(_id_amb, (None, _id_amb))[1]
        _pie.caption(f"**{_nombre_amb}** — clic en una compra para ver sus "
                     "líneas al costado.")

        # ── El clic en la tabla de documentos ────────────────────────────
        # Lo que devuelve la grilla es su selección VIGENTE, no un clic de
        # esta vuelta: desde que conserva su key (ver arriba) la sigue
        # devolviendo en cada corrida. Por eso se actúa sólo si difiere de la
        # compra que ya se muestra — si no, cada corrida volvería a aplicar
        # el mismo clic.
        #
        # El precio, aceptado: volver a tocar la fila MARCADA ya no la
        # suelta (AG Grid no deselecciona con un clic simple). Hasta el
        # 2026-09-19 eso cerraba el detalle en «Por documento» y volvía a la
        # compra mayor en las otras; las dos cosas siguen a un clic, en la
        # barra del gráfico.
        #
        # En «Por documento» el clic mueve el FOCO y no `compras_sem_doc`:
        # ahí la barra es la compra, así que el gráfico marca la nueva.
        #
        # El `rerun` hace falta porque el gráfico de ARRIBA ya se dibujó con
        # la marca vieja. Scope decidido y no fijo (regla #306).
        if (_clic is None or _clic == _sel
                or _clic not in set(_docs["compra"])):
            return
        if gran == "Por documento":
            st.session_state["compras_sem_focus"] = _clic
        else:
            st.session_state["compras_sem_doc"] = _clic
        st.rerun(scope=scope_rerun())

