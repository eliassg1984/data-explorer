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
"""

import hashlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
from tema import (
    ADVERTENCIA_TEXTO, BLANCO, GRIS_BORDE, GRIS_TEXTO, SERIE_PRINCIPAL,
    TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import (
    _compras_layout, _compras_truncar, preservar_widgets, scope_rerun,
)
from graficos.compras._comun import (
    CATEGORIA_SEC, GAP_DRILL, _first_point, _periodo_serie, documento_legible,
    selector_fecha_tarjeta,
)
from tablas.compras_semanal import (
    renderizar_documentos_semanal, renderizar_lineas_semanal,
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
_PROD_TODOS = "Todos los productos"

_GRAN_DEFAULT = "Por documento"
"""Con qué granularidad abre la vista, y a qué vuelve si se suelta la
píldora activa (Streamlit devuelve `None` al des-elegir un `st.pills`).

«Por documento» desde el 2026-09-12, a pedido («debe aparecer
inicialmente seleccionado "Por documento"»), junto con abrir en el mes en
curso (`SEC_ABRE_EN_EL_MES` en `_comun.py`): las dos cosas van juntas, un
mes por documento son ~30-60 barras legibles; doce meses por documento
serían cientos. Antes era «Semana».

UNA constante para los dos usos a propósito: con el default en el widget y
el fallback escrito aparte, soltar la píldora mostraba otra granularidad
que la del arranque."""

_KEYS_WIDGET = ("compras_sem_gran", "compras_sem_familia",
                "compras_sem_producto")
"""Los tres controles de la cabecera, para que la escalada no se los lleve.

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

_ANCHO_SLOT = 0.62

# Opacidad de lo que NO está en foco cuando hay un detalle abierto: la misma
# con que Plotly atenúa lo no seleccionado (`DESELECTDIM`), porque la marca
# a mano reemplaza a la selección de Plotly (ver «EL FOCO SE MARCA A MANO»).
_ATENUADO = 0.2
"""Fracción del slot de la categoría que ocupa el reparto de los puntos.

La barra mide 0.8 del slot (el `bargap` de 0.2 por defecto), así que 0.62
—o sea ±0.31 alrededor del centro— los deja adentro de la barra con aire a
los dos lados.

El reparto va por ORDEN DE FECHA dentro del período y es EQUIESPACIADO, no
proporcional al día. Proporcional conservaría más información (se vería en
qué día de la semana cayó cada compra) pero permite que dos compras del
mismo día vuelvan a taparse, que es exactamente el bug que este reparto
existe para arreglar. La fecha exacta la da el hover."""

_TOPE_PUNTOS = 8
"""Techo de compras dibujadas por período: las mayores por valor.

Ver el docstring del módulo, que trae la medición: la mediana son 69 por
semana y el amontonamiento es contra el cero, así que el tope no esconde
nada que se pudiera clickear. Lo que recorta sigue DENTRO de la barra, que
es la suma de TODO el período — el tope es de puntos, no de datos. Y cuando
recorta, la leyenda lo dice.

Es un TECHO, no el tope real: el de verdad lo calcula `_tope_puntos()`
contra los píxeles que hay."""

_LIENZO_PX = 820
"""Ancho útil del lienzo de esta figura, en píxeles. MEDIDO, no estimado.

Con la tarjeta a todo el ancho de la fila del drill, leyendo
`xaxis._length` de la figura ya montada en el navegador:

    viewport 1280   tarjeta 915px   ->  lienzo 818  (la laptop)
    viewport 1440   tarjeta 1049px  ->  lienzo 988

Se toma el caso chico, que es donde se mira la app. Existe porque el
servidor no sabe el ancho del cliente —`_es_movil` distingue móvil de
escritorio por User-Agent, no da píxeles— y `_tope_puntos()` necesita un
número para decidir cuántos marcadores caben. Errar por defecto es lo
barato: sobra aire entre puntos, no se pisan."""

_PASO_PUNTO_PX = 12
"""Píxeles que ocupa un punto: los 10 del marcador más 2 de aire.

Dos marcadores a menos de esto no son dos blancos, son una mancha."""


def _tope_puntos(n_periodos):
    """Cuántas compras por período CABEN, no cuántas se querrían mostrar.

    Nació de una medición que tiró abajo la premisa del reparto dentro del
    slot (2026-09-08). Con la franja en 53 semanas y el tope fijo en 8:

        px por slot        18,6      (988px de lienzo / 53)
        reparto            11,5px    (el 62% del slot)
        entre dos puntos    1,7px    con marcadores de 10

    O sea el reparto existía y no separaba nada — ocho manchas de 10px en
    15px de barra. El tope tiene que salir de los píxeles disponibles, no
    de un número lindo:

        53 períodos ->  1 punto     20 ->  2      8 ->  5
        12 períodos ->  3 puntos     5 ->  8 (el techo)

    Con 1 punto la vista no pierde el sentido, lo AFILA: es la compra MAYOR
    de cada período, que es la que se quiere mirar, y a 18px de slot es un
    blanco cómodo. El resto sigue sumado en la barra, y la leyenda dice qué
    se está viendo."""
    px_slot = _LIENZO_PX / max(int(n_periodos), 1)
    caben = int(px_slot * _ANCHO_SLOT // _PASO_PUNTO_PX)
    return max(1, min(_TOPE_PUNTOS, caben))


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
# contra el mismo `_LIENZO_PX` que decide cuántos puntos caben.

_GRAN_CON_ETIQUETA = ("Semana", "Mes", "Año")

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


def _plan_etiquetas(n_periodos, largo_max):
    """`"derecha"`, `"girada"` o `None`: cómo se escriben los totales de
    `n_periodos` barras cuya etiqueta más larga tiene `largo_max`
    caracteres.

    El apretón que manda es la distancia entre dos etiquetas VECINAS, que
    es el slot entero del período (una sola serie: no hay otra barra en el
    mismo slot, como sí en «Vs año pasado»). Derecha si la etiqueta entra en
    el slot; si no, girada, que ocupa una línea de ancho; si ni así, nada —
    el total sigue en el hover. Con el mes corrido de entrada (4-5 semanas)
    sale derecha; con 12 meses por semana (53), nada."""
    if n_periodos <= 0 or largo_max <= 0:
        return None
    px_slot = _LIENZO_PX / n_periodos
    if largo_max * _ETQ_PX_CARACTER + _ETQ_AIRE <= px_slot:
        return "derecha"
    if _ETQ_ALTO_LINEA + _ETQ_AIRE <= px_slot:
        return "girada"
    return None


def _techo_etiquetas(hi, lo, alto_fig, alto_etq):
    """`[ymin, ymax]` del eje Y con lugar para `alto_etq` px de etiqueta
    encima de la barra más alta.

    `textposition="outside"` NO agranda el rango solo: la etiqueta de la
    barra más alta queda contra el borde y se corta. La cuenta es en
    píxeles, la misma de `vs_ano_pasado._techo_con_etiquetas`: si el área de
    trazo mide `alto_plot` y la etiqueta necesita `alto_etq`, el dato tiene
    que ocupar `alto_plot − alto_etq`."""
    alto_plot = _alto_area_trazo(alto_fig)
    alto_etq = min(alto_etq, alto_plot * 0.45)
    base = min(0.0, lo)
    span = hi - base
    if span <= 0:
        return None
    return [base, base + span * alto_plot / (alto_plot - alto_etq)]


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
                           col_fam=None, d_full=None):
    """Compra por período (día/semana/mes/año o por documento) + detalle.

    `col_valor` entra como NOMBRE de columna y la serie numérica se arma
    acá: el dispatcher ya tenía una (`_valor`), pero pasar el Series
    ataría la firma a que el llamador la haya calculado antes.

    `col_fam` y `d_full` entran por palabra clave y con default a propósito.
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
        _mask_fam = (d[col_fam].astype(str) == _fam_prev
                     if (_hay_fam and _fam_prev != _FAM_TODAS)
                     else pd.Series(True, index=d.index))
        _val_prod = (_valor[_mask_fam]
                     .groupby(d.loc[_mask_fam, col_prod].astype(str))
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

        # ── La fila de cabecera: granularidad + los dos filtros + fecha ──
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
        # ESTIRA solo al ancho del contenedor). `st.pills` no se estira
        # —mide su propio contenido— y una columna lo apretaba a 157px,
        # forzando que "Por documento" envuelva a una segunda línea sin
        # necesidad. Medido con el inspector (`?debug=1&diseno=1`) el
        # 2026-09-03.
        _box = {}

        def _controles():
            with st.container(horizontal=True, gap="small",
                              key="cp_sem_filtros"):
                _box["gran"] = st.pills(
                    "Agrupar por",
                    ["Día", "Semana", "Mes", "Año", "Por documento"],
                    default=_GRAN_DEFAULT, key="compras_sem_gran",
                    label_visibility="collapsed")
                if _hay_fam and len(_ops_fam) > 1:
                    with st.container(key="cp_sem_hdr_familia"):
                        _box["fam"] = st.selectbox(
                            "Familia", _ops_fam, key="compras_sem_familia",
                            label_visibility="collapsed",
                            help="Acota ESTA tarjeta a una familia, encima "
                                 "de los chips de la franja. La lista "
                                 "ofrece sólo las que los chips dejan "
                                 "pasar.")
                with st.container(key="cp_sem_hdr_producto"):
                    _box["prod"] = st.selectbox(
                        "Producto", _ops_prod, key="compras_sem_producto",
                        label_visibility="collapsed",
                        help="Ordenados por VALOR de compra en el rango: el "
                             "primero es el que más compraste. «Top N por "
                             "valor» suma los N mayores en una sola serie. "
                             "Se puede escribir para buscar.")

        if selector_fecha_tarjeta(
                "cp_sem", "_cp_sem_atajo_pendiente", extra=_controles,
                categoria=CATEGORIA_SEC["compras_sec_semanal"]) is None:
            # El selector no dibuja NADA si la franja todavia no publico su
            # contexto, y con el se irian tambien los tres controles de la
            # izquierda, que son de esta vista y no de la fecha. En ese caso
            # se dibujan sueltos.
            _controles()
        gran = _box.get("gran") or _GRAN_DEFAULT
        fam_sel = _box.get("fam") or _FAM_TODAS
        prod_sel = _box.get("prod") or _PROD_TODOS

        # Cambiar de granularidad invalida el foco: una clave de "Semana" no
        # existe en el espacio de "Mes". Y cambiar de familia o de producto
        # invalida además el foco de COMPRA, que puede haber desaparecido
        # del recorte. Mismo guard que `compras_vol_prod_prev` en
        # volatilidad.py al cambiar de producto, con las tres cosas en una
        # tupla: son tres motivos para lo mismo.
        _ctx = (gran, fam_sel, prod_sel)
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
        }).dropna(subset=["fecha"])

        # Los dos filtros de la tarjeta, en el orden en que se leen.
        if _hay_fam and fam_sel != _FAM_TODAS:
            dd = dd[dd["fam"] == fam_sel]
        if prod_sel in _etiq_top:
            dd = dd[dd["prod"].isin(_prods[:_etiq_top[prod_sel]])]
        elif prod_sel != _PROD_TODOS:
            dd = dd[dd["prod"] == prod_sel]

        # El ÁMBITO va al título de la figura: con dos filtros propios más
        # los chips de la franja, un gráfico que dice sólo "Compra por
        # semana" no deja saber de qué son esas barras.
        _amb = [_a for _a in (None if fam_sel == _FAM_TODAS else fam_sel,
                              None if prod_sel == _PROD_TODOS else prod_sel)
                if _a]
        _tit_gran = {"Día": "por día", "Semana": "por semana",
                    "Mes": "por mes", "Año": "por año",
                    "Por documento": "por documento"}[gran]
        _titulo = (f"Compra {_tit_gran}"
                   + (" · " + " · ".join(_amb) if _amb else ""))

        if dd.empty:
            # El caso que hace el PIN de más arriba: el producto sigue
            # elegido y no tiene compras en este rango. El cartel nombra las
            # dos salidas porque las dos son válidas.
            st.info(f"**{_titulo}** — sin compras que mostrar. Ampliá el "
                    "rango de fechas (arriba a la derecha) o volvé a «Todos "
                    "los productos».")
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
        # El eje va por ÍNDICE, no por texto — ver el comentario largo del
        # `update_xaxes`, más abajo, que trae la medición de por qué.
        _ix = {_c: _i for _i, _c in enumerate(_ord_claves)}
        # Cuántos períodos hay decide dos cosas: cuántos puntos caben en una
        # barra (`_tope_puntos`) y cada cuánto se rotula el eje.
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
        # `%{x}`: la x de las dos trazas es un ÍNDICE (ver el
        # `update_xaxes`), así que `%{x}` diría "17" en vez de "2026-S17".
        g["ix"] = g["clave"].map(_ix)
        g["lbl"] = g["clave"].map(dict(zip(_ord_claves, _ord_lbls)))

        # El ENCABEZADO del hover, que no es la etiqueta del eje. En grano
        # diario el eje tiene que ser corto («Sáb» sobre «15/08»); el hover
        # no compite con nadie por el ancho, así que ahí va el día completo
        # con año — y en «Por documento», además, QUIÉN y CUÁL, que es lo
        # que el eje no puede decir con una barra por documento. Es el mismo
        # número de documento de la tabla y del caption: uno solo en toda la
        # vista, salido de `dd["doc"]`.
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
                                        .map(_compras_truncar))
        else:
            g["hov"] = g["lbl"]

        fig = go.Figure()
        fig.add_bar(
            x=g["ix"], y=g["valor"], name="Valor total",
            marker=dict(color=SERIE_PRINCIPAL),
            customdata=g[["hov", "cant"]].to_numpy(),
            hovertemplate=("%{customdata[0]}<br>Valor: S/ %{y:,.2f}"
                           "<br>Cantidad: %{customdata[1]:,.1f}"
                           "<extra></extra>"),
        )

        # ── El total, escrito encima de cada barra (2026-09-14, #440) ────
        # Sólo cuando entra: ver `_plan_etiquetas`. El techo del eje que
        # necesita se pone más abajo, cuando se sabe el alto de la figura.
        # `constraintext="none"`: sin él Plotly ENCOGE la etiqueta que no
        # entra en la barra en vez de dejarla afuera a su tamaño.
        _plan_etq, _largo_etq = None, 0
        if gran in _GRAN_CON_ETIQUETA:
            _etq = [fmt_k(v) if v else None for v in g["valor"]]
            _largo_etq = max((len(t) for t in _etq if t), default=0)
            _plan_etq = _plan_etiquetas(_n_per, _largo_etq)
            if _plan_etq:
                fig.data[0].update(
                    text=_etq, textposition="outside", cliponaxis=False,
                    constraintext="none",
                    textangle=-90 if _plan_etq == "girada" else 0,
                    textfont=dict(size=_ETQ_FUENTE, color=TEXTO_PRINCIPAL))

        # ── Los puntos: una COMPRA, no una línea de producto ─────────────
        # Una orden de 5 líneas es un solo punto, no cinco. Se omiten en
        # "Por documento": ahí cada barra YA es una compra y el punto caería
        # pegado a su propia punta, sin sumar información.
        #
        # 2026-09-08, y es el corazón del cambio (la medición está en el
        # docstring del módulo): TOPE por período + REPARTO dentro del slot.
        # Sin las dos, 69 puntos por semana caen todos en la misma x y no
        # hay puntería que alcance.
        #
        # La x va NUMÉRICA (índice del período ± el desplazamiento), y por
        # eso el eje es LINEAL — ver el `update_xaxes` de más abajo, que
        # trae la medición del intento anterior. Consecuencia: lo que el
        # clic devuelve en ESTA traza no es una clave sino un float, de ahí
        # que la compra se resuelva por `point_index` contra `_pts` y no por
        # la x. Que además es lo correcto: el índice identifica LA COMPRA, y
        # la x sólo su período.
        _pts = dd.iloc[0:0]
        _recorta = False
        if gran != "Por documento":
            docs_g = (dd.groupby(["clave", "compra"], as_index=False)
                     .agg(valor=("valor", "sum"), fecha=("fecha", "min"),
                          prov=("prov", "first"), lineas=("valor", "size")))
            # Tope: las N mayores de cada período, con N = cuántas CABEN
            # (ver `_tope_puntos`, que trae la medición). Con muchos
            # períodos N cae a 1 y el punto es la compra mayor del período.
            _tope = _tope_puntos(_n_per)
            docs_g = docs_g.sort_values(["clave", "valor"],
                                        ascending=[True, False])
            _recorta = bool(
                (docs_g.groupby("clave")["compra"].transform("size")
                 > _tope).any())
            _pts = docs_g[docs_g.groupby("clave").cumcount() < _tope].copy()
            # Reparto: por orden de fecha dentro del período, equiespaciado.
            # `compra` entra en el sort como desempate para que el orden sea
            # ESTABLE entre reruns — si no, dos compras del mismo día pueden
            # intercambiarse y el `point_index` del clic apuntaría a otra.
            _pts = (_pts.sort_values(["clave", "fecha", "compra"])
                        .reset_index(drop=True))
            _k = _pts.groupby("clave").cumcount()
            _tot = _pts.groupby("clave")["compra"].transform("size")
            # `_tot - 1` es el divisor, y con un solo punto en el período
            # sería 0: el `.where` de los dos lados lo deja en el centro
            # (offset 0) sin pasar por la división.
            _den = (_tot - 1).where(_tot > 1, 1)
            _off = (-_ANCHO_SLOT / 2
                    + _ANCHO_SLOT * _k / _den).where(_tot > 1, 0.0)
            _pts["x"] = _pts["clave"].map(_ix).astype(float) + _off

            fig.add_scatter(
                x=_pts["x"], y=_pts["valor"], mode="markers",
                # La leyenda dice QUÉ se está viendo, que con tope variable
                # cambia: todas, la mayor, o las N mayores. Sin esto un
                # punto por barra se leería como "hubo una sola compra".
                name=("Compra individual" if not _recorta
                      else ("Compra mayor de cada período" if _tope == 1
                            else f"Las {_tope} compras mayores de cada "
                                 "período")),
                # 10 y no 8: el marcador ES el blanco del clic. El tope de
                # arriba garantiza que a este tamaño no se pisen.
                marker=dict(size=10, color=TEXTO_PRINCIPAL,
                            line=dict(color=BLANCO, width=1.5)),
                customdata=pd.DataFrame({
                    "f": _pts["fecha"].dt.strftime("%d/%m/%Y"),
                    "prov": _pts["prov"], "lineas": _pts["lineas"],
                }).to_numpy(),
                hovertemplate=("Compra · %{customdata[1]}<br>%{customdata[0]}"
                               "<br>Valor: S/ %{y:,.2f}"
                               "<br>%{customdata[2]} líneas"
                               "<br><i>clic: ver su detalle</i>"
                               "<extra></extra>"),
            )

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
            if _pt.get("curve_number") == 1 and not _pts.empty:
                # Traza 1 = los puntos. `point_index` contra `_pts`, que se
                # construyó con `reset_index` justo para esto.
                _pi = _pt.get("point_index", _pt.get("point_number"))
                if _pi is not None and 0 <= _pi < len(_pts):
                    _c = _pts["compra"].iloc[_pi]
                    st.session_state["compras_sem_doc"] = (
                        None if _doc_antes == _c else _c)
                    st.session_state["compras_sem_focus"] = (
                        _pts["clave"].iloc[_pi])
            else:
                # Traza 0 = las barras. Su x es el ÍNDICE del período (eje
                # lineal), así que hay que traducirla: el foco se guarda
                # como CLAVE, que es lo que compara la tabla de abajo.
                _clic = _clave_del_clic(_pt.get("x"), _ord_claves)
                # Con una compra en foco, la barra SUBE un nivel (vuelve al
                # período entero) en vez de apagarlo todo: apagar obligaría
                # a dos clics para deshacer uno.
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
        if _con_detalle:
            fig.data[0].marker.opacity = [
                1.0 if _c == _focus else _ATENUADO for _c in g["clave"]]
            if len(fig.data) > 1:
                # Los puntos: la compra en foco, o las del período en foco.
                fig.data[1].marker.opacity = [
                    1.0 if (_c == _doc if _doc_ok else _k == _focus)
                    else _ATENUADO
                    for _c, _k in zip(_pts["compra"], _pts["clave"])]

        _alto_fig = (alturas.COMPACTO if _con_detalle
                     else alturas.SEMANAL_SOLO)
        _compras_layout(fig, alto=_alto_fig)
        if _plan_etq:
            # Girada ocupa su LARGO hacia arriba; derecha, una línea.
            _alto_etq = ((_largo_etq * _ETQ_PX_CARACTER
                          if _plan_etq == "girada" else _ETQ_ALTO_LINEA)
                         + _ETQ_AIRE)
            _rng = _techo_etiquetas(float(g["valor"].max()),
                                    float(g["valor"].min()),
                                    _alto_fig, _alto_etq)
            if _rng:
                fig.update_yaxes(range=_rng)
        fig.update_layout(
            title=_titulo,
            # `y` sale de `_LEYENDA_Y`: la cuenta del techo de las etiquetas
            # depende de dónde va la leyenda.
            legend=dict(orientation="h", y=-_LEYENDA_Y, x=0,
                        font=dict(size=10)),
            # EXPLÍCITO: con barras y puntos superpuestos, `closest` es lo
            # que hace que el hover de un punto le gane a la barra que tiene
            # abajo. Es el default de Plotly, pero el default de una figura
            # que mezcla trazas no conviene dejarlo implícito justo en la
            # vista donde apuntar es el problema.
            hovermode="closest",
        )
        # ── EL EJE ES LINEAL, Y NO POR GUSTO ────────────────────────────
        # Era `type="category"` con `categoryarray=_ord_claves` hasta el
        # 2026-09-08. Con eso, los puntos desplazados a media categoría no
        # se pueden dibujar: Plotly NO interpreta una x numérica como
        # posición dentro del slot, la agrega como UNA CATEGORÍA MÁS.
        # Medido en el navegador con datos reales (53 semanas, 424 puntos):
        #
        #     xaxis._categories.length   477   (= 53 + 424, uno por punto)
        #     xaxis.range                [-0.5, 504.5]
        #     px por slot                1,94   sobre 978px de lienzo
        #
        # O sea las 53 barras aplastadas contra el borde izquierdo y los
        # puntos en 424 categorías propias a la derecha. Los offsets en sí
        # salían perfectos (-0.31, -0.22, …, +0.31); lo que no funciona es
        # el eje.
        #
        # Con eje lineal las dos trazas hablan el mismo idioma —el índice
        # del período— y el desplazamiento es aritmética. El precio es que
        # las etiquetas hay que ponerlas a mano (`tickmode="array"`), que es
        # lo que este bloque ya hacía. `range` explícito porque el
        # autorange de un eje lineal pone su propio aire a los costados y
        # la primera y la última barra quedaban flotando media barra
        # adentro del margen.
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
        # las que se le den —no las adelgaza como el modo automático— y
        # "2026-S17" mide ~55px, así que a partir de ~17 por lienzo se
        # pisan entre sí. El paso mantiene el primero y va salteando.
        if _ticks is None:
            _paso = max(1, -(-_n_per // 17))
            _ticks = (list(range(0, _n_per, _paso)), _ord_lbls[::_paso])
        fig.update_xaxes(
            type="linear", tickmode="array",
            tickvals=_ticks[0], ticktext=_ticks[1],
            range=[-0.5, _n_per - 0.5])

        # Clic en una barra o un punto -> foco de la tabla de abajo. La
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
        # `st.dataframe` (regla #440), y la receta del hueco sigue igual: es
        # suyo, y se vacía con `.empty()` explícito cuando no hay foco.
        _hueco_tabla = st.empty()
        if not _con_detalle:
            st.caption("Tocá una barra para ver sus documentos, o un punto "
                      "para ver una compra.")
            _hueco_tabla.empty()
            return

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

        # QUÉ COMPRA muestra la de la derecha: la elegida —con un clic en la
        # tabla o en un punto del gráfico—; en «Por documento», la de la
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

        _tp_docs = pd.DataFrame({
            "fecha": _docs["fecha"].dt.strftime("%d/%m/%Y"),
            "doc": _docs["doc"].fillna("").map(lambda v: v or "—"),
            "prov": _docs["prov"],
            "lineas": _docs["lineas"].astype(int).astype(str),
            "valor": _docs["valor"].map(lambda v: f"S/ {v:,.2f}"),
            "__compra": _docs["compra"],
            "__sel": _docs["compra"] == _sel,
        })
        _tp_lin = pd.DataFrame({
            "prod": _lin["prod"],
            "cant": _lin["cant"].map(lambda v: f"{v:,.1f}"),
            "punit": _lin["punit"].map(
                lambda v: "—" if pd.isna(v) else f"S/ {v:,.2f}"),
            "valor": _lin["valor"].map(lambda v: f"S/ {v:,.2f}"),
        })

        with _hueco_tabla.container():
            # columnas-internas: las dos tablas del detalle, DENTRO de la
            # tarjeta de la vista; no es una fila de drill que tenga que caer
            # en el eje de `COLUMNAS_DRILL`. La de documentos lleva cinco
            # columnas contra cuatro, de ahí el 1.15.
            _c_docs, _c_lin = st.columns([1.15, 1], gap=GAP_DRILL)
            with _c_docs:
                # LA KEY LLEVA EL PERÍODO Y LA COMPRA ELEGIDA: cada cambio
                # estrena grilla, que nace sin selección y marca la fila por
                # su dato `__sel`. Ver el docstring de
                # `tablas/compras_semanal.py`.
                _clic = renderizar_documentos_semanal(
                    _tp_docs, altura=alturas.SEMANAL_TABLA,
                    key=f"compras_sem_docs_grid_{_clave_grilla(gran, _id_amb, _sel)}",
                    ver_fecha=gran != "Por documento",
                    ver_doc=bool(col_docu))
            with _c_lin:
                renderizar_lineas_semanal(
                    _tp_lin, altura=alturas.SEMANAL_TABLA,
                    key=f"compras_sem_lineas_grid_{_clave_grilla(_sel)}")

        _n_docs = len(_docs)
        _n_txt = f"{_n_docs} compra" + ("" if _n_docs == 1 else "s")
        if gran == "Por documento":
            _nombre_amb = (f"{cortes.DIAS_ABR_ES[_dia.weekday()].capitalize()} "
                           f"{_dia:%d/%m/%Y}")
            _n_txt += " del día"
        else:
            _nombre_amb = _amb["lbl"].iloc[0]
        st.caption(f"**{_nombre_amb}** · {_n_txt} · "
                   f"S/ {_docs['valor'].sum():,.2f} — clic en una compra "
                   "para ver sus líneas al costado.")

        # ── El clic en la tabla de documentos ────────────────────────────
        # Como la grilla nace sin selección, un valor es siempre un clic de
        # esta vuelta. Volver a clickear la fila MARCADA la suelta: en «Por
        # documento» cierra el detalle (es lo mismo que volver a tocar su
        # barra) y en las otras vuelve a la compra mayor.
        #
        # En «Por documento» el clic mueve el FOCO y no `compras_sem_doc`:
        # ahí la barra es la compra, así que el gráfico marca la nueva y un
        # segundo clic en su barra la cierra, como siempre.
        #
        # El `rerun` hace falta porque el gráfico de ARRIBA ya se dibujó con
        # la marca vieja. Scope decidido y no fijo (regla #306).
        if _clic is None or _clic not in set(_docs["compra"]):
            return
        if gran == "Por documento":
            st.session_state["compras_sem_focus"] = (
                None if _clic == _sel else _clic)
        elif _clic == _sel:
            if not _doc_ok:
                return  # ya era la que se mostraba por defecto
            st.session_state["compras_sem_doc"] = None
        else:
            st.session_state["compras_sem_doc"] = _clic
        st.rerun(scope=scope_rerun())
