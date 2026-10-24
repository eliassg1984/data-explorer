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

2026-10-08 — «PARTIR POR» (regla #620). La barra deja de partirse en tres
tramos por tamaño de compra y se parte por lo que se elige: subfamilia (de
entrada), proveedor o precio —lo pagado al precio habitual, lo pagado de
más y lo que no tiene precio previo—. El selector vive en el renglón del
título del gráfico, que pasó a HTML junto con la leyenda.
"""


from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import cortes
import definicion_compra
from tema import (
    ADVERTENCIA_TEXTO, ERROR, GRIS_BORDE, GRIS_TEXTO, GRIS_TEXTO_SUAVE,
    SERIE_PRINCIPAL, SERIE_TRAMOS,
)
from graficos import alturas
from graficos.base import (
    _compras_truncar, preservar_widgets, rango_tarjeta,
)
# Las cinco de la variación contra la barra anterior (#470) NACIERON acá y
# se mudaron a `_comun.py` el 2026-09-20, cuando la Evolución de Producto
# pidió lo mismo: «que las barras tengan el % de variación respecto a la
# barra anterior». Se importan con su nombre de siempre, así que el resto
# de este módulo no se enteró de la mudanza — y no hay dos definiciones de
# qué es un período PARCIAL, que es lo que la regla vigila.
from graficos.compras._comun import (
    _fmt_variacion, _limites_periodo,
    _variaciones,  # noqa: F401 — la importa test_graficos.py como `semanal._variaciones`
)
from graficos.compras._comun import (
    CATEGORIA_SEC, colores_estables,
    documento_legible, selector_fecha_tarjeta,
)
# Documento y Montos (regla #621), propios de ESTA tarjeta desde el
# 2026-10-10 (regla #624).
from graficos.compras._comun import (
    DOC_TODOS,
    filtrar_documento, tipo_corto,
)
# EL NOMBRE DEL PROVEEDOR SE ESCRIBE COMO NOMBRE PROPIO, no como lo grita el
# ERP (2026-09-20, a pedido: «pongamos el nombre del proveedor en
# minúscula»). Es la ÚNICA del repo y es sólo para MOSTRAR: la clave con la
# que esta vista compara (`dd["compra"]`) sigue llevando el nombre crudo.
# Ver `_etiquetas_proveedor.nombre_propio` y `arquitectura.md` #379.
from graficos.compras._etiquetas_proveedor import nombre_propio
from graficos.compras._css_proveedor import CSS as CSS_PROVEEDOR
# Las formas jurídicas sin punto («SAC», «EIRL»): `_rotulo_proveedor` las saca
# del final del nombre en la leyenda de «Partir por» (regla #620).
from graficos.compras._etiquetas_proveedor import _SIGLAS_RAZON_SOCIAL
from utils import fmt_k


# ===========================================================================
# CENTINELAS DE LOS DOS SELECTORES
# ===========================================================================
# Son CENTINELAS, no valores del parquet: se comparan por igualdad contra lo
# que devuelve el widget. Mismo criterio —y misma trampa— que `_FAM_TODAS` de
# `vs_ano_pasado.py`: una familia que se llamara literalmente "Todas" lo
# rompería, y por eso el texto lleva el sustantivo. Ninguna familia ni
# producto del parquet empieza con "Todas las" ni con "Top ".
#
# Desde el 2026-10-10 (regla #623) ya no son valores: los cuatro filtros son
# `st.multiselect` y «nada elegido» es «todos». Quedan como el PLACEHOLDER
# del campo vacío, que es donde siguen diciendo qué está haciendo.
_FAM_TODAS = "Todas las familias"
_SUB_TODAS = "Todas las subfamilias"
_PROV_TODOS = "Todos los proveedores"
_PROD_TODOS = "Todos los productos"

# Las keys de los cuatro filtros. En PLURAL a propósito: hasta el 2026-10-10
# eran `st.selectbox` con keys en singular que guardaban un string, y una
# sesión abierta de antes del cambio traería ese string a un multiselect, que
# exige una lista. Con otra key el valor viejo queda huérfano y no estorba.
_K_FAM = "compras_sem_familias"
_K_SUB = "compras_sem_subfamilias"
_K_PROV = "compras_sem_proveedores"
_K_PROD = "compras_sem_productos"

# DOCUMENTO Y MONTOS, DE ESTA TARJETA (2026-10-10, regla #624, a pedido:
# «dentro de la tarjeta, como una línea para seleccionar, no en la franja de
# arriba»). Hasta ese día vivían en «Filtros» y mandaban sobre todo Compras
# (regla #621); se eligió que fueran sólo de esta tarjeta, así que las otras
# vistas miden siempre todos los documentos y sin IGV.
_K_DOCUMENTO = "compras_sem_documento"
_K_MONTOS = "compras_sem_montos"


def _eleccion(key, opciones, default):
    """El valor de uno de los dos toggles, LEÍDO ANTES de dibujarlo: filtra
    el `d` del que salen hasta las listas de la cabecera. Se siembra acá y
    el widget va sin `default=`, como «Partir por»."""
    v = st.session_state.get(key)
    if v not in opciones:
        v = default
        st.session_state[key] = v
    return v


# Qué queda elegido y qué se ofrece lo decide `base.seleccion_multiple`, la
# regla compartida con las tarjetas «por período» de Movimientos (#625).

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
_MODO_RESUMEN = "Resumen Total"
_MODO_PROVS = "Resumen del Período"
_MODO_OPCIONES = (_MODO_RESUMEN, _MODO_PROVS, _MODO_DETALLE)
_MODO_DEFAULT = _MODO_RESUMEN
"""Los TRES modos de la zona de abajo, en el orden del toggle.

Desde el 2026-10-01 (regla #580), a pedido: «que la vista predeterminada
sea Resumen, pero que ahora se llame Resumen Total; al costado, como un
toggle del medio, otro llamado Resumen del Período, con los nombres de los
proveedores, cantidad de documentos, % del valor total del período y
cantidad de ítems distintos; y al hacer clic en una de las filas, que te
lleve a Detalle, que estará al lado, como tercero». Así el toggle se lee de
lo general a lo particular: todas las barras → los proveedores del rango →
los documentos.

«Resumen del Período» mira el rango ENTERO de la tarjeta (el «Del… al…»
del caption), no una barra: es la pregunta «¿a quién le compré en este
período?». Un clic en un proveedor abre Detalle con el ÁMBITO de ese
proveedor —sus compras de todo el rango— en vez del de una barra
(`compras_sem_prov_det`); un clic en una barra vuelve al ámbito de la barra.

Debajo, la historia de los dos modos que había hasta ese día — «Resumen»
se llamaba así y el default era Detalle.

Los dos modos de la zona de abajo (2026-09-19, regla #476).

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
    "Qué se ve debajo del gráfico. **Resumen Total**: una fila por barra "
    "—con su total, su % de la vista, sus documentos y su variación— más el "
    "total de todas. **Resumen del Período**: una fila por proveedor del "
    "rango, con sus documentos, su % del valor y sus ítems distintos; un "
    "clic en uno abre su Detalle. **Detalle**: los documentos de la barra "
    "que toques (o del proveedor que elijas) y las líneas del que elijas."
)

# Escritas a mano y no con `_K_FAM`…: `test_graficos.py` las lee con `ast`
# y sólo ve literales.
_KEYS_WIDGET = ()
# (La tabla de «Resumen del Período» no va: su selección se CONSUME en la
# corrida del clic —estrena la key con un contador—, así que no hay nada
# que preservar.)
"""Los controles de la tarjeta, para que la escalada no se los lleve.

Eran tres hasta el 2026-09-19, cuando se sumaron Subfamilia y Proveedor;
el sexto, el modo de la zona de abajo, llegó el mismo día, y el séptimo,
«Partir por», el 2026-10-08 (regla #620). Los cinco primeros viven en la
cabecera, el modo debajo del gráfico y «Partir por» en el renglón de su
título: lo que los junta acá no es dónde están sino de quién son — todos
son widgets de ESTE fragment, y el `rerun` los recolecta a todos por igual.

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


def _con_alpha(_hex, _a):
    """`#rrggbb` → `rgba(r,g,b,a)`. El foco se atenúa por COLOR y no con
    `marker.opacity` por punto: esa lista sobre barras con texto `outside`
    crashea Plotly en el navegador («Cannot read properties of undefined
    (reading 'textfont')»). Ver `arquitectura.md` regla #476."""
    _h = _hex.lstrip("#")
    _r, _g, _b = (int(_h[_i:_i + 2], 16) for _i in (0, 2, 4))
    return f"rgba({_r},{_g},{_b},{_a})"

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
#
# Y la fila de KPI que se fue el 2026-10-01 le devuelve a la FIGURA lo que
# medía, en los dos estados (`alturas.FRANJA_KPI_SEMANAL`): a pedido, «las
# barras deben subir un poco más».
#
# Y la línea de Documento y Montos (2026-10-10, regla #624) se la cobra a la
# figura, en los dos estados (`alturas.FRANJA_DOC_SEMANAL`).
_ALTO_FIG_SOLO = (alturas.SEMANAL_SOLO - alturas.FRANJA_MODO_SEMANAL
                  + alturas.FRANJA_KPI_SEMANAL - alturas.FRANJA_DOC_SEMANAL)
_ALTO_FIG_CON_TABLA = (alturas.COMPACTO + alturas.FRANJA_KPI_SEMANAL
                       - alturas.FRANJA_DOC_SEMANAL)
_ALTO_TABLA = alturas.SEMANAL_TABLA - alturas.FRANJA_MODO_SEMANAL


# ===========================================================================
# DE QUÉ ESTÁ HECHA CADA BARRA: «PARTIR POR» (2026-10-08, regla #620)
# ===========================================================================
# A pedido, mirando los tres tonos de la barra: «el color no me serviría
# mucho, quisiera usar el espacio de la barra para que muestre alguna otra
# información relevante». La barra se parte ahora por lo que se elija en un
# selector de la propia tarjeta —en el renglón del título del gráfico, que
# estaba vacío—, con tres respuestas:
#
#   · SUBFAMILIA (de entrada): en qué se fue la plata. Medido en los últimos
#     12 meses con las cinco familias con que abre Compras (S/ 1,63 millones):
#     Carnes 39 %, Abarrotes 13 %, Verduras 9 %, Pescados y mariscos 9 %,
#     Lácteos y quesos 8 % — juntas casi el 80 %. Y son las que más se mueven
#     de una semana a otra (aves ±74 %, pescados ±50 %, carnes ±46 %): una
#     semana alta se explica a la vista. Por FAMILIA no servía: Alimentos es
#     el 87 % y las barras salían de un solo color.
#   · PROVEEDOR: de quién se depende. Los cinco mayores son el 43 % de 138.
#   · PRECIO: cuánto de cada barra se pagó por ENCIMA del precio habitual
#     (`precio_habitual`). Es un cálculo propio, no un indicador estándar, y
#     el hover lo dice. Del 1 de agosto al 7 de octubre de 2026: S/ 12.575
#     pagados de más y S/ 14.627 de menos —neto, S/ 2.052 por debajo—, con
#     referencia para el 96 % del gasto.
#
# LAS DOS PRIMERAS VAN CON LAS `_PARTES_N` MAYORES DE LA VISTA y el resto en
# gris, cada una con el color de su puesto en el HISTÓRICO
# (`_comun.colores_estables`): mover la fecha no repinta Carnes de otro color.
# El hover nombra TODAS las partes de la barra juntas, con la que está bajo
# el cursor en negrita — la pregunta es por la barra, no por el tramo.
#
# Y EL RESTO DE LA TARJETA NO CAMBIA: la etiqueta de arriba (total, docs,
# variación), el clic, el foco y la tabla de abajo, que sigue dando una
# columna por FAMILIA. El desglose por familia de cada barra salió del hover
# (un hover de 16 renglones no entraba en la figura) y vive en esa tabla, que
# tiene una fila por barra.
#
# LO DE ANTES (2026-09-17 → 2026-10-08, regla #453): la barra se partía en
# tres tramos por TAMAÑO de compra —la mayor, la 2ª y 3ª, el resto— con tres
# tonos del morado de la marca. Decía de qué estaba hecho el período (una
# compra grande o muchas medianas), pero sólo dos renglones del hover
# cambiaban de un tramo a otro y el reparto casi no variaba entre semanas:
# era color sin respuesta.

_GRAN_PARTIDA = ("Día", "Semana", "Mes", "Año")
"""Granularidades cuya barra se parte según «Partir por»: todas menos «Por
documento», donde la barra YA es una compra y hay miles — ahí el selector
se apaga (sigue dibujado: un widget que deja de dibujarse pierde su valor).

Sumar una es sumarla acá y darle su entrada en `_TOTAL_DEL_PERIODO`, que es
lo que evita que el hover diga «Total del día» sobre una semana."""

_TOTAL_DEL_PERIODO = {"Día": "Total del día", "Semana": "Total de la semana",
                      "Mes": "Total del mes", "Año": "Total del año"}
"""Cómo nombra el hover al total del período, por granularidad.

Era el literal «Total del día» mientras la barra partida vivía sólo en Día.
Al sumar Semana pasó a ser falso sin dar ningún error: el número era el de
la semana y el rótulo decía día."""

_PARTIR_SUBFAMILIA = "Subfamilia"
_PARTIR_PROVEEDOR = "Proveedor"
_PARTIR_PRECIO = "Precio"
_PARTIR_OPCIONES = (_PARTIR_SUBFAMILIA, _PARTIR_PROVEEDOR, _PARTIR_PRECIO)
_PARTIR_DEFAULT = _PARTIR_SUBFAMILIA
"""Las tres formas de partir la barra, en el orden del selector. Se ofrecen
las que el parquet permite: sin columna de subfamilia, de proveedor o de
cantidad, la suya no aparece (`_partir_disponibles`)."""

_PARTES_N = 5
"""Subfamilias o proveedores con color propio; el resto va junto, en gris.
Con una más que esto en la vista van todas: un «resto» de una sola sería
esa misma con otro nombre. Cinco subfamilias son casi el 80 % del gasto."""

_VENTANA_PRECIO = 90
"""Días hacia atrás que mira el precio habitual de cada compra."""

_PRODUCTOS_HOVER = 3
"""Productos que nombra el hover de «Precio» entre los pagados de más."""

_A_PRECIO_HABITUAL = "A precio habitual"
_PAGADO_DE_MAS = "Pagado de más"
_SIN_PRECIO_PREVIO = "Sin precio previo"

_TITULO_PRECIO = (f"Contra el precio habitual · mediana de los "
                  f"{_VENTANA_PRECIO} días anteriores")
"""El renglón gris que abre las partes en el hover de «Precio»: quien lee
«pagado de más» tiene que poder saber contra qué. Va en el hover y no en un
`help=` del selector (con el rótulo oculto el «?» no se ve, regla #555) ni
en un `title` de la leyenda (el contenedor de Plotly la tapa)."""


def _partir_disponibles(hay_sub, hay_prov, hay_cant):
    """Las opciones del selector que el parquet permite, en su orden."""
    return [op for op, hay in ((_PARTIR_SUBFAMILIA, hay_sub),
                               (_PARTIR_PROVEEDOR, hay_prov),
                               (_PARTIR_PRECIO, hay_cant)) if hay]


def precio_habitual(prod, fecha, valor, cant, dias=_VENTANA_PRECIO):
    """El PRECIO HABITUAL de cada línea, alineado a `prod`: la mediana del
    precio unitario (valor ÷ cantidad) del mismo producto en los `dias` días
    ANTERIORES a su fecha, sin contar ese mismo día. NaN si en esa ventana no
    hubo ninguna compra con precio.

    Sin el mismo día a propósito: dos compras de una misma mañana no son una
    la referencia de la otra. Las líneas sin cantidad o sin valor positivo no
    dan precio, pero sí reciben el suyo. La mediana y no el promedio: una
    compra de 200 g a un precio raro no mueve la referencia de un producto
    que se compra por decenas de kilos.

    Vectorizado: UN `groupby().rolling()` sobre todas las líneas, no un
    recorrido por producto (regla #537). Medido sobre el histórico de las
    cinco familias de entrada (45.026 líneas): 0,46 s; sobre un rango de dos
    meses más su ventana, 0,13 s. La salida del rolling viene en el orden de
    sus grupos, así que se devuelve por POSICIÓN —la columna `pos`— y no por
    el índice, que en pandas 2 y 3 sale distinto (regla #481) y en el parquet
    puede repetirse."""
    n = len(prod)
    valor = pd.to_numeric(valor, errors="coerce")
    cant = pd.to_numeric(cant, errors="coerce")
    pu = (valor / cant).where((cant > 0) & (valor > 0))
    t = pd.DataFrame({
        "prod": prod.astype(str).to_numpy(),
        "fecha": pd.to_datetime(fecha, errors="coerce").dt.normalize().to_numpy(),
        "pu": pu.to_numpy(dtype=float, na_value=np.nan),
        "pos": np.arange(n),
    }).dropna(subset=["fecha"])
    out = np.full(n, np.nan)
    if t.empty:
        return pd.Series(out, index=prod.index)
    t = t.sort_values(["prod", "fecha"], kind="stable")
    med = (t.groupby("prod", sort=True)
             .rolling(f"{int(dias)}D", on="fecha", closed="left")["pu"]
             .median())
    out[t["pos"].to_numpy()] = med.to_numpy(dtype=float, na_value=np.nan)
    return pd.Series(out, index=prod.index)


def partes_por_columna(dd, col, ord_claves, orden=(), n=_PARTES_N,
                       resto="Otras", nombrar=str):
    """Las partes de cada barra según la columna `col` de `dd` (subfamilia o
    proveedor), como `[(rótulo, color, [valor por período]), …]` alineadas a
    `ord_claves`, en el orden de lectura —la mayor primero— que es también
    el de la pila, de abajo hacia arriba.

    Las `n` mayores de la VISTA, con el color de su puesto en `orden` —el
    histórico—, y arriba «Otras (k)» en gris con lo que falta para el total
    de cada barra: el resto no se vuelve a sumar por categoría, así la barra
    cierra por construcción. Con `n + 1` o menos van todas. Una categoría
    que no suma nada positivo en la vista no tiene parte. Pura."""
    tot = (dd.groupby(col)["valor"].sum()
             .sort_values(ascending=False, kind="stable"))
    tot = tot[tot > 0]
    if tot.empty:
        return []
    por = (dd.groupby(["clave", col])["valor"].sum().unstack(col)
             .reindex(ord_claves).fillna(0.0))
    nombres = (list(tot.index) if len(tot) <= n + 1
               else list(tot.index[:n]))
    color = colores_estables(list(orden), nombres)
    partes = [(nombrar(c), color[c], [float(v) for v in por[c]])
              for c in nombres]
    if len(nombres) < len(tot):
        totales = (dd.groupby("clave")["valor"].sum()
                     .reindex(ord_claves).fillna(0.0))
        acum = por[nombres].sum(axis=1)
        partes.append((f"{resto} ({len(tot) - len(nombres)})",
                       GRIS_TEXTO_SUAVE,
                       [max(float(t) - float(a), 0.0)
                        for t, a in zip(totales, acum)]))
    return partes


def partes_por_precio(dd, ord_claves):
    """`(partes, pila, extra)` de «Partir por» Precio.

    `dd` trae `valor`, `cant`, `prod`, `clave` y `ref` —el precio habitual de
    cada línea, de `precio_habitual`—. Cada línea con referencia se parte en
    lo que habría costado a ese precio (tope: lo pagado) y lo que se pagó
    por encima; la que no tiene, va entera a «Sin precio previo». Las tres
    partes suman el total de la barra por construcción.

    `partes` viene en el orden de lectura (el de la leyenda y el hover):
    habitual, de más, sin precio. `pila` es el orden de abajo hacia arriba
    —sin precio, habitual, de más—, para que el rojo quede ARRIBA de la
    barra, que es donde se lo busca. Una parte que es cero en toda la vista
    no se dibuja.

    `extra` es, por clave, el texto del hover que no es una parte: lo pagado
    de MENOS, el neto contra el precio habitual y los productos que más se
    pagaron de más. Pura."""
    v = dd["valor"].astype(float)
    con = dd["ref"].notna() & (dd["cant"] > 0) & (v > 0)
    hab = (dd["cant"] * dd["ref"]).where(con, 0.0)
    de_mas = (v - hab).clip(lower=0).where(con, 0.0)
    t = pd.DataFrame({
        "clave": dd["clave"],
        "sin": v.where(~con, 0.0),
        "habitual_parte": (v - de_mas).where(con, 0.0),
        "de_mas": de_mas,
        "de_menos": (hab - v).clip(lower=0).where(con, 0.0),
        "habitual": hab,
        "pagado": v.where(con, 0.0),
    })
    g = (t.groupby("clave")[["sin", "habitual_parte", "de_mas", "de_menos",
                             "habitual", "pagado"]].sum()
           .reindex(ord_claves).fillna(0.0))
    todas = [(_A_PRECIO_HABITUAL, SERIE_PRINCIPAL, "habitual_parte", 1),
             (_PAGADO_DE_MAS, ERROR, "de_mas", 2),
             (_SIN_PRECIO_PREVIO, GRIS_TEXTO_SUAVE, "sin", 0)]
    vivas = [p for p in todas if float(g[p[2]].abs().sum()) > 0]
    partes = [(rot, color, [float(x) for x in g[campo]])
              for rot, color, campo, _ in vivas]
    pila = sorted(range(len(vivas)), key=lambda i: vivas[i][3])

    # Los productos pagados de más, por período: los `_PRODUCTOS_HOVER`
    # mayores, con el % que se pagó por encima EN ESAS LÍNEAS. Un groupby
    # sobre todas las filas, no un recorrido por período (#537).
    sobre = con & (de_mas > 0)
    pr = pd.DataFrame({"clave": dd.loc[sobre, "clave"],
                       "prod": dd.loc[sobre, "prod"].astype(str),
                       "de_mas": de_mas[sobre], "habitual": hab[sobre]})
    pr = pr.groupby(["clave", "prod"], as_index=False)[
        ["de_mas", "habitual"]].sum()
    pr = pr.sort_values(["clave", "de_mas", "prod"],
                        ascending=[True, False, True], kind="stable")
    pr["k"] = pr.groupby("clave").cumcount()
    pr = pr[pr["k"] < _PRODUCTOS_HOVER]
    pr["txt"] = [f"{escape(_compras_truncar(p, 30))}: +S/ {m:,.2f} "
                 f"(+{_pct_parte(m / h if h else 0.0)})"
                 for p, m, h in zip(pr["prod"], pr["de_mas"], pr["habitual"])]
    prods = pr.groupby("clave")["txt"].agg("<br>".join)

    # Un texto por PERÍODO (decenas, a lo sumo un millar en «Día» sobre el
    # histórico), armado con `zip` sobre las columnas ya sumadas.
    prods = prods.to_dict()
    extra = {}
    for c, menos, habitual, pagado in zip(g.index, g["de_menos"],
                                          g["habitual"], g["pagado"]):
        renglones = []
        if menos:
            renglones.append(f"Pagado de menos: S/ {menos:,.2f}")
        if habitual:
            neto = pagado - habitual
            txt_pct, color = _fmt_variacion(neto / habitual * 100)
            signo = "+" if neto > 0 else ("−" if neto < 0 else "")
            renglones.append(
                f"Neto: <span style='color:{color}'><b>{signo}S/ "
                f"{abs(neto):,.2f} ({txt_pct})</b></span> contra el precio "
                "habitual")
        if c in prods:
            renglones.append(f"<span style='color:{GRIS_TEXTO}'>Lo que más "
                             f"se pagó de más</span><br>{prods[c]}")
        extra[c] = "".join(f"<br>{x}" for x in renglones)
    return partes, pila, extra


def _orden_historico(d, d_full, col, col_valor):
    """Las categorías de `col` de mayor a menor en el HISTÓRICO (`d_full`,
    con los chips de la franja; `d` si no viene): el orden estable con el que
    `colores_estables` reparte los colores."""
    src = (d_full if (d_full is not None and col in d_full.columns
                      and col_valor in d_full.columns) else d)
    return (pd.to_numeric(src[col_valor], errors="coerce").fillna(0)
              .groupby(src[col].astype(str)).sum()
              .sort_values(ascending=False, kind="stable").index.tolist())


def _vacio(s):
    """True si una categoría viene vacía: `astype(str)` escribe «nan»."""
    return str(s).strip() in ("", "nan", "None", "<NA>")


def _rotulo_subfamilia(s):
    """«PESCADOS Y MARISCOS» → «Pescados y mariscos», como las familias."""
    return "Sin subfamilia" if _vacio(s) else _nombre_familia(s)


def _rotulo_proveedor(p):
    """El proveedor como nombre propio, sin la forma jurídica del final
    («S.A.C.», «EIRL») y corto: es una ficha de la leyenda, y cinco nombres
    enteros no entraban en el renglón del título."""
    if _vacio(p):
        return "Sin proveedor"
    pal = nombre_propio(p).split()
    while (len(pal) > 1
           and pal[-1].replace(".", "").upper() in _SIGLAS_RAZON_SOCIAL):
        pal.pop()
    return _compras_truncar(" ".join(pal), 20)


def _precio_habitual_de(dd, d, d_full, col_prod, col_fecha, col_valor,
                        col_cant):
    """`precio_habitual` de cada fila de `dd`, como array alineado a ella.

    SALE DEL HISTÓRICO, no del rango: la primera compra del rango también
    tiene sus 90 días previos. Sólo los productos de la vista y sólo la
    ventana que hace falta. Y es del producto y del DÍA —todas las líneas de
    un producto en un mismo día comparten la suya—, así que viaja por
    (producto, día) y no por índice de fila, que en el parquet puede
    repetirse."""
    src = (d_full if (d_full is not None and all(
               c in d_full.columns
               for c in (col_prod, col_fecha, col_valor, col_cant))) else d)
    f_src = pd.to_datetime(src[col_fecha], errors="coerce")
    p_src = src[col_prod].astype(str)
    lo = dd["fecha"].min().normalize() - pd.Timedelta(days=_VENTANA_PRECIO)
    m = (f_src >= lo) & (f_src <= dd["fecha"].max()) & p_src.isin(set(dd["prod"]))
    ref = precio_habitual(p_src[m], f_src[m], src.loc[m, col_valor],
                          src.loc[m, col_cant])
    ref = pd.Series(ref.to_numpy(), index=pd.MultiIndex.from_arrays(
        [p_src[m].to_numpy(), f_src[m].dt.normalize().to_numpy()]))
    ref = ref[~ref.index.duplicated()]
    return ref.reindex(pd.MultiIndex.from_arrays(
        [dd["prod"].to_numpy(), dd["fecha"].dt.normalize().to_numpy()])
    ).to_numpy()


def _pct_parte(p):
    """La parte de un total como «4.3%» o «39%»: un decimal por debajo del
    10 %, como `_fmt_variacion`. Sin signo — es una parte, no un cambio."""
    pct = p * 100
    return f"{pct:.1f}%" if abs(pct) < 10 else f"{pct:.0f}%"


def _hover_partes(partes, tot, titulo, marcada=None):
    """El bloque del hover que nombra TODAS las partes de cada barra —la
    pregunta es por la barra—, con la resaltada (`marcada`, su índice en
    `partes`) en negrita. Un texto por período; las partes que en esa barra
    valen cero no se nombran. Empieza con `<br>` para colgarse de un
    `hovertemplate`.

    Hasta la regla #621 devolvía una lista POR PARTE, con la parte bajo el
    cursor en negrita: cada franja tenía su hover. Desde que el cursor
    responde en la barra entera hay un solo hover por barra, y lo que se
    marca es lo resaltado."""
    cab = f"<br><span style='color:{GRIS_TEXTO}'>{titulo}</span>"
    salida = []
    for j, total in enumerate(tot):
        renglones = []
        for k, (rot, _c, vals) in enumerate(partes):
            if not vals[j]:
                continue
            txt = (f"{escape(rot)}: S/ {vals[j]:,.2f} · "
                   f"{_pct_parte(vals[j] / total if total else 0.0)}")
            renglones.append(f"<br><b>{txt}</b>" if k == marcada
                             else f"<br>{txt}")
        salida.append(cab + "".join(renglones))
    return salida


_K_RESALTADO = "compras_sem_resaltado"
"""`{«Partir por»: lo resaltado, o None}` — una entrada por forma de partir,
así volver de Proveedor a Subfamilia encuentra la misma subfamilia. Es una
clave PROPIA y no la del widget: ver «QUÉ SE RESALTA» en el drill."""


def _guias_por_clave(dd, ord_claves, igv=False, solo_guias=False):
    """El renglón del hover que dice cuánto de cada barra es guía de
    remisión sin canjear (regla #621), alineado a `ord_claves`; vacío donde
    no hubo guías. Con «Con IGV» suma que la guía todavía no lo lleva; con
    el filtro en «Guías sin canjear» lo dice una vez por barra, sin cifra:
    la barra entera es guía."""
    g = (dd[dd["tipo"] == "G"].groupby("clave")
           .agg(v=("valor", "sum"), n=("compra", "nunique")))
    nota = " · sin IGV todavía: lo trae la factura" if igv else ""
    salida = []
    for c in ord_claves:
        if c not in g.index:
            salida.append("")
            continue
        n, v = int(g.at[c, "n"]), float(g.at[c, "v"])
        txt = ("Guías de remisión sin canjear" + nota if solo_guias else
               f"Incluye {n} guía{'' if n == 1 else 's'} de remisión sin "
               f"canjear: S/ {v:,.2f}{nota}")
        salida.append(f"<br><span style='color:{ADVERTENCIA_TEXTO}'>{txt}"
                      "</span>")
    return salida


# ── LAS NOTAS DE CRÉDITO DE LA VISTA (regla #628) ─────────────────────────
_NOTA_DOC = ('<div class="cp-sem-doc-nota">Sólo esta tarjeta · «Todos» es lo '
             'que suman los reportes de ingresos del Almacén, menos las notas '
             'de crédito</div>')
"""La nota de la línea de Documento. Hasta el 2026-10-10 decía «lo que suman
los reportes de ingresos del Almacén» a secas, que dejó de ser cierto el
2026-10-04 (regla #603): el Resumen de Ingresos no resta las notas, y la
app sí. Cuánto restaron lo dice la tabla (regla #628)."""

_NC_MINIMO = 0.005
"""Desde cuánto lo restado se dice: medio céntimo. Una nota que no toca lo
que se muestra suma 0, y una columna de «−S/ 0.00» sería ruido."""

_TIPO_NC = "N"
"""El `tipo` de una nota de crédito en las filas del Detalle, junto a los
de `tipo_corto` («F», «G», «O»)."""


def _lineas_nc(d_nc, col_fecha, col_prod, col_prov, col_docu, col_fam,
               col_subfam, col_neto, col_igv, col_tipo_doc, documento,
               col_cant=None, col_punit=None, col_moneda=None):
    """Las líneas que restó una nota de crédito (`d_nc`, con las columnas de
    compras), con los nombres de `dd` para que les apliquen los mismos
    filtros: `fecha` (la de la factura), `prod`, `prov`, `docn`, `fam`,
    `sub`, `compra` (la misma clave que en `dd`), `neto`, `igv` y `cant`
    (lo restado), `punit`, `tipo` y `usd` de la factura, y `nota` y
    `fecha_nc`. Vacío si no hay notas o falta alguna columna — el demo, sin
    parquet de notas."""
    cols = ("fecha", "prod", "prov", "docn", "fam", "sub", "neto", "igv",
            "cant", "punit", "tipo", "usd", "nota", "fecha_nc", "compra")
    if (d_nc is None or d_nc.empty or not col_fecha or not col_prod
            or not col_neto or any(c not in d_nc.columns
                                   for c in (col_fecha, col_prod, col_neto,
                                             definicion_compra.COL_NOTA))):
        return pd.DataFrame(columns=cols)
    d_nc = filtrar_documento(d_nc, col_tipo_doc, documento)

    def _txt(col):
        return (d_nc[col].astype(str) if col and col in d_nc.columns
                else pd.Series("", index=d_nc.index))

    def _num(col):
        return (pd.to_numeric(d_nc[col], errors="coerce").fillna(0.0)
                if col and col in d_nc.columns
                else pd.Series(0.0, index=d_nc.index))

    fecha = pd.to_datetime(d_nc[col_fecha], errors="coerce")
    fecha_nc = (pd.to_datetime(d_nc[definicion_compra.COL_FECHA_NC],
                               errors="coerce")
                if definicion_compra.COL_FECHA_NC in d_nc.columns
                else pd.Series(pd.NaT, index=d_nc.index))
    n = pd.DataFrame({
        "fecha": fecha,
        "prod": _txt(col_prod), "prov": _txt(col_prov), "docn": _txt(col_docu),
        "fam": _txt(col_fam), "sub": _txt(col_subfam),
        "neto": _num(col_neto), "igv": _num(col_igv), "cant": _num(col_cant),
        "punit": (pd.to_numeric(d_nc[col_punit], errors="coerce")
                  if col_punit and col_punit in d_nc.columns
                  else pd.Series(np.nan, index=d_nc.index)),
        "tipo": (tipo_corto(d_nc[col_tipo_doc])
                 if col_tipo_doc and col_tipo_doc in d_nc.columns
                 else pd.Series("F", index=d_nc.index)),
        "usd": (_txt(col_moneda).str.strip() == "02"),
        "nota": d_nc[definicion_compra.COL_NOTA].astype(str),
        # Sin fecha de la nota (un parquet de notas sin esa columna), la de
        # su factura: es donde la nota se resta.
        "fecha_nc": fecha_nc.fillna(fecha),
    }).dropna(subset=["fecha"])
    # La clave de COMPRA de `dd` (fecha·proveedor·documento): la de la
    # factura que la nota corrige.
    n["compra"] = (n["fecha"].dt.strftime("%Y-%m-%d") + "·" + n["prov"]
                   + "·" + n["docn"])
    return n[list(cols)]


def _renglones_nc(ncd, por=("clave",)):
    """Qué notas de crédito restaron en `ncd` y cuánto, agrupado por `por`:
    un texto por grupo con un renglón por nota (su proveedor y la factura
    que corrige), de la mayor a la menor. Un solo `groupby`, sin recorrer
    grupos (regla #537)."""
    por = list(por)
    t = (ncd.groupby(por + ["nota", "prov", "docn"], sort=False)
            .agg(valor=("valor", "sum"), fecha=("fecha", "min"))
            .reset_index().sort_values("valor", ascending=False))
    doc = documento_legible(t["docn"])
    t["txt"] = (t["nota"] + " · " + t["prov"].map(nombre_propio) + " · sobre "
                + doc.where(doc.astype(bool), t["docn"]) + " del "
                + t["fecha"].dt.strftime("%d/%m/%Y") + ": −S/ "
                + t["valor"].map("{:,.2f}".format))
    return t.groupby(por, sort=False).agg(
        txt=("txt", "\n".join), valor=("valor", "sum"))


def detalle_con_notas(dd, ncd, lbl_de=None):
    """`dd` para el DETALLE (regla #628): cada factura que tocó una nota de
    crédito, como se FACTURÓ, y la nota como un documento más, en negativo
    y en su fecha. Las dos se cancelan, así que lo que suma el período no
    cambia: lo que cambia es que se ve qué pasó.

    La factura se rearma sumando a sus líneas de `dd` lo que la nota les
    restó (`ncd`), por producto — la devuelta ENTERA no tiene ninguna en
    `dd` y vuelve entera. La nota toma las mismas líneas con el signo al
    revés, su número como documento y `tipo` «N»; queda en el período de
    su factura, que es donde la tarjeta la resta. `lbl_de` ({clave: rótulo
    del eje}) le pone el rótulo a la factura que no tenía filas en `dd`.
    `dd` sin tocar si no hay notas."""
    if ncd is None or ncd.empty:
        return dd
    cols = list(dd.columns)
    num = ["cant", "valor", "neto", "igv"]
    ncd = ncd.assign(doc=documento_legible(ncd["docn"]),
                     lbl=ncd["clave"].map(lbl_de or {}))
    tocadas = set(ncd["compra"])
    fact = pd.concat([dd[dd["compra"].isin(tocadas)],
                      ncd.reindex(columns=cols)], ignore_index=True)
    fact = (fact.groupby(["compra", "prod"], as_index=False, sort=False)
                .agg({**{c: "sum" for c in num},
                      **{c: "first" for c in cols
                         if c not in num + ["compra", "prod"]}}))
    nota = ncd.assign(**{c: -ncd[c] for c in num})
    nota = nota.assign(
        docn=nota["nota"].str.split(", ").str[0], fecha=nota["fecha_nc"],
        tipo=_TIPO_NC, usd=False)
    # El número de la nota viene codificado como el de la factura, con «N0»
    # delante en vez de «F0» (`N0E001000000068` = E001-68): se decodifica
    # con la misma función prestándole la «F».
    _n15 = nota["docn"].str.startswith("N0") & (nota["docn"].str.len() == 15)
    nota = nota.assign(
        doc=documento_legible(nota["docn"].where(
            ~_n15, "F" + nota["docn"].str[1:])),
        compra="NC·" + nota["docn"] + "·" + nota["prov"])
    return pd.concat([dd[~dd["compra"].isin(tocadas)],
                      fact.reindex(columns=cols), nota.reindex(columns=cols)],
                     ignore_index=True)


def _es_resto(nombre):
    """True si la parte es el «Otras (k)» / «Otros (k)» de
    `partes_por_columna`: no se ofrece para resaltar."""
    return str(nombre).startswith(("Otras (", "Otros ("))


def opciones_resaltar(partes, partir):
    """Lo que se puede resaltar en la barra (regla #621): las subfamilias o
    proveedores con nombre —el resto no— o, en «Precio», lo pagado de más.
    En el orden de la leyenda, que es el de las partes."""
    if partir == _PARTIR_PRECIO:
        return [r for r, _c, _v in partes if r == _PAGADO_DE_MAS]
    return [r for r, _c, _v in partes if not _es_resto(r)]


def renglon_resaltado(valor, total, precio=False):
    """`(plano, html)` del segundo renglón de la etiqueta de una barra con
    una parte resaltada, en lugar de los documentos (que siguen en el
    hover): «S/ 11.8k · 41%» en el tono de la parte o, en «Precio»,
    «+S/ 1.3k de más» en rojo. `None` en «Precio» si esa barra no tuvo nada
    pagado de más: ahí el renglón de los documentos se queda."""
    if precio:
        if not valor:
            return None
        txt = f"+{fmt_k(valor)} de más"
        return txt, f"<span style='color:{ERROR}'><b>{txt}</b></span>"
    txt = f"{fmt_k(valor) if valor else 'S/ 0'} · "           f"{_pct_parte(valor / total if total else 0.0)}"
    return txt, f"<span style='color:{SERIE_TRAMOS[0]}'><b>{txt}</b></span>"


def igv_de_linea(neto, igv, tipo):
    """La marca de IGV de una línea de compra: «18 %», «exonerado» (no pagó:
    verduras, pescados, frutas), «guía» (todavía sin IGV: lo trae la
    factura) u otra tasa con un decimal. Vectorizada: recibe tres Series
    alineadas y devuelve otra."""
    n = pd.to_numeric(neto, errors="coerce")
    i = pd.to_numeric(igv, errors="coerce").fillna(0.0)
    tasa = (i / n).where(n > 0)
    otra = (tasa * 100).map(lambda x: f"{x:.1f} %" if pd.notna(x) else "—")
    return pd.Series(
        np.where(tipo == "G", "guía",
                 np.where(i.abs() < 0.005, "exonerado",
                          np.where((tasa - 0.18).abs() < 0.005, "18 %",
                                   otra))),
        index=n.index)


def _etiqueta_en_la_punta(tramos, textos):
    """El texto de cada TRAMO, con la etiqueta del total sólo en el de arriba.

    `tramos` son las partes de la barra de abajo hacia arriba, cada una con
    su `valor` por período (aquí, las de «Partir por»; en Ventas, las suyas)
    y `textos` el total ya formateado de cada período, alineado al eje.
    Devuelve una lista por tramo, con `None` donde no va nada.

    Va en el tramo más alto CON VALOR, no en el último: una semana sin
    compras de la quinta subfamilia no tiene esa parte, y Plotly pone el
    `outside` de una barra apilada sólo
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
#   · la VISTA —rango + filtros de la tarjeta— iba en una fila de KPI dentro
#     de la cabecera, al lado de la fecha, que es lo que la acota;
#   · la BARRA va en su hover, que es el único sitio donde cada barra
#     contesta por sí misma sin ocupar alto.
#
# La fila de KPI se quitó el 2026-10-01, a pedido: «esa información ya me
# la da mi tabla de abajo en Resumen», que trae una columna por familia
# (las mismas de `_familias_de`) y su fila TOTAL. Sus 38px pasaron a la
# figura (`alturas.FRANJA_KPI_SEMANAL`).
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

_KPI_FAMILIAS = 3
"""Familias con columna propia en la tabla de Resumen; el resto va sumado
en una. Ver la medición de arriba. (Nació como las tarjetas de la fila de
KPI de la cabecera, que se fue el 2026-10-01.)

Eran 4 hasta el 2026-10-10 (regla #629): a 1323px la grilla da 1134 y
cuatro familias más «N más» (5 × 94) sobre las fijas pedían 1196 — la
última columna salía cortada, sin barra que avisara. Las tres mayores son
el 94 % del mes medido arriba."""

_HOVER_FAMILIAS = 5
"""Familias que nombra el hover de una barra; el resto va en «N más».

Con 8 de máximo por día, cinco renglones cubren el día típico entero (4) y
dejan el hover de un día raro en siete renglones en vez de diez."""


def _nombre_familia(fam):
    """«COSTOS PRODUCCION» → «Costos produccion». El parquet las trae en
    mayúsculas, y en un hover de seis renglones eso se lee a los gritos."""
    fam = str(fam or "").strip()
    return fam[:1].upper() + fam[1:].lower() if fam else "Sin familia"


def _familias_de(dd, n=_KPI_FAMILIAS):
    """`(total, [(familia, valor, parte), …], (n_resto, valor_resto))` del
    valorizado de `dd` por familia, de mayor a menor.

    `parte` es la fracción del total (0-1). La lista trae las
    `n` mayores (`_KPI_FAMILIAS`) y el resto va sumado aparte, con cuántas
    son.
    Las familias en cero no cuentan: una familia con compras anuladas que
    suman 0 no es una familia de la vista.

    Si el resto es UNA familia, va con su nombre: «1 más» ocupa la misma
    columna y no dice cuál es (regla #629)."""
    total = float(dd["valor"].sum())
    s = dd.groupby("fam")["valor"].sum()
    s = s[s != 0].sort_values(ascending=False)
    if len(s) == n + 1:
        n += 1
    top = [(f, float(v), (float(v) / total) if total else 0.0)
           for f, v in s.iloc[:n].items()]
    resto = s.iloc[n:]
    return total, top, (len(resto), float(resto.sum()))


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
las dos (salen 114 y 76px).

Desde el 2026-10-08 (#620) ninguna de las dos figuras que usan esta cuenta
dibuja la leyenda de Plotly —ni ésta ni las de Movimientos—: el área de
trazo real es MAYOR que la calculada, y la diferencia es aire sobre las
etiquetas. Se deja así a propósito: errar por ese lado no pisa nada."""


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


def _rotulo_periodo(clave, gran, rango=None):
    """`(eje, largo)`: cómo se nombra el período en el eje y en el hover.

        Semana   «lun 14–dom 20 set»      «Semana del lun 14 al dom 20 set 2026»
                 «lun 31 ago–dom 6 set»   «Semana del lun 31 ago al dom 6 set 2026»
                 «sáb 1–dom 2 ago»        «Del sáb 1 al dom 2 ago 2026 · la semana
                  (cortada por el rango)   del lun 27 jul al dom 2 ago 2026 queda
                                           cortada por las fechas»
        Mes      «set 2026»       «Set 2026»
        Año, Día la clave, que ya se lee

    LA SEMANA DICE SUS DÍAS (2026-10-08, a pedido). Con el selector en «1 ago
    – 7 oct», la primera barra se llamaba «27 jul–2 ago» y sumaba sólo el
    sábado 1 y el domingo 2 (S/ 415 de los S/ 14.588 de la semana entera):
    el nombre prometía días que no estaban. Ahora lleva el día de la semana
    de cada punta y, con `rango` (las dos fechas de la tarjeta), una semana
    que el rango corta se nombra por los días que SÍ entran. Es el criterio
    de «Por hora» con un mes a medias (regla #531). Sin `rango`, la semana
    entera. Regla #619.

    El año no va en el rótulo de la semana: lo pone el eje debajo, sólo en
    el primero y cuando cambia (`_anio_semana`), que es como lo hace Plotly
    en un eje de fechas. Repetido en cada semana sería tinta sin dato."""
    _m = cortes.MESES_ABR_ES
    if gran == "Semana":
        ini, fin = _limites_periodo(clave, gran)
        mi, mf = _m[ini.month - 1], _m[fin.month - 1]
        _ai = f" {ini.year}" if ini.year != fin.year else ""
        if ini.month == fin.month:
            semana = (f"Semana del lun {ini.day} al dom {fin.day} {mf} "
                      f"{fin.year}")
        else:
            semana = (f"Semana del lun {ini.day} {mi}{_ai} al dom {fin.day} "
                      f"{mf} {fin.year}")
        a, b = ini, fin
        if rango:
            a, b = max(ini, rango[0]), min(fin, rango[1])
            if a > b:
                a, b = ini, fin
        _d = cortes.DIAS_ABR_ES

        def _dia(x, con_mes):
            return (f"{_d[x.weekday()]} {x.day}"
                    + (f" {_m[x.month - 1]}" if con_mes else ""))

        if a == b:
            eje = _dia(a, True)
        elif a.month == b.month:
            eje = f"{_dia(a, False)}–{_dia(b, True)}"
        else:
            eje = f"{_dia(a, True)}–{_dia(b, True)}"
        if (a, b) == (ini, fin):
            return eje, semana
        dias = (f"{_dia(a, True)} {a.year}" if a == b
                else f"Del {_dia(a, a.month != b.month)} al {_dia(b, True)} "
                     f"{b.year}")
        return (eje, f"{dias[:1].upper()}{dias[1:]} · la "
                     f"{semana[:1].lower()}{semana[1:]} queda cortada por las "
                     "fechas")
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


def _resumen_proveedores(dd):
    """La tabla de «Resumen del Período» (regla #580): una fila por
    proveedor del rango de la vista, de mayor a menor valor, con sus
    documentos (compras), su fracción del valor del período (0-1) y sus
    ítems distintos — los números CRUDOS, que el formato lo pone la grilla
    (`tablas/compras_semanal.py::renderizar_proveedores_periodo`) y así se
    ordenan.

    `__prov` lleva el nombre CRUDO, que es con lo que se filtra Detalle; la
    columna visible va como nombre propio. Columnas por NOMBRE, no por
    posición (regla #481)."""
    g = (dd.groupby("prov", as_index=False)
           .agg(valor=("valor", "sum"), docs=("compra", "nunique"),
                items=("prod", "nunique"))
           .sort_values(["valor", "prov"], ascending=[False, True],
                        kind="stable")
           .reset_index(drop=True))
    tot = float(g["valor"].sum()) or 1.0
    return pd.DataFrame({
        "prov": [nombre_propio(p) for p in g["prov"]],
        "valor": g["valor"].astype(float).round(2),
        "parte": g["valor"].astype(float) / tot,
        "docs": g["docs"].astype(int),
        "items": g["items"].astype(int),
        "__prov": g["prov"],
    })


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


# ===========================================================================
# LA PIEZA PROPIA (2026-10-24, regla #716)
# ===========================================================================
# Desde ese día la tarjeta es `semanal.js` + `semanal.css`, montada con
# `st.components.v2`: el grano, los cuatro filtros, Documento y Montos,
# «Partir por» y lo resaltado, las barras, la zona de abajo con sus tres
# modos y los clics en las tablas los resuelve el navegador. Sólo la fecha
# (el botón de Python, encima de la pieza) pide una corrida. Hasta ese día
# cada clic era una corrida de 1,3 a 2,5 s en la laptop con R2.
#
# Las cuentas de arriba de este módulo SIGUEN siendo las de la vista: el
# `.js` las rehace con las mismas fórmulas (`partes_por_columna`,
# `partes_por_precio`, `_variaciones`, `_rotulo_periodo`, `_plan_etiquetas`,
# `detalle_con_notas`, `_familias_de`, `_resumen_proveedores`), y
# `test_compras_periodo.py` las compara en Chromium. Si se toca una, se toca
# la otra. Además las usan las tarjetas «por período» de Movimientos.

_TIPOS = ("F", "G", "O")
"""El `tipo` de una línea para la pieza (posición en esta tupla): factura,
guía de remisión sin canjear, lo demás (`tipo_corto`)."""


def lineas_pieza(d, cols):
    """Las líneas de compra con nombres FIJOS: `fecha` (el día), `prod`,
    `prov`, `docn` (crudo), `fam`, `sub`, `cant`, `neto` (sin IGV), `igv`,
    `tipo` (F/G/O), `usd` y `punit`. Las categorías como texto, igual que el
    `dd` de la vista de antes (un vacío es «nan»). Sin fecha no entran: no
    caen en ningún período. Pura."""
    (col_prod, col_fecha, col_cant, col_punit, col_prov, col_docu, col_valor,
     col_fam, col_subfam, col_igv, col_tipo_doc, col_moneda) = cols
    n = len(d)

    def _txt(col):
        if col and col in d.columns:
            return d[col].astype(str).to_numpy(dtype=object)
        return np.full(n, "", dtype=object)

    def _num(col):
        if col and col in d.columns:
            return pd.to_numeric(d[col], errors="coerce").fillna(0.0).to_numpy(
                dtype=float)
        return np.zeros(n)

    b = pd.DataFrame({
        "fecha": (pd.to_datetime(d[col_fecha], errors="coerce").dt.normalize()
                  .to_numpy()),
        "prod": _txt(col_prod), "prov": _txt(col_prov), "docn": _txt(col_docu),
        "fam": _txt(col_fam), "sub": _txt(col_subfam),
        "cant": _num(col_cant), "neto": _num(col_valor), "igv": _num(col_igv),
        "tipo": (tipo_corto(d[col_tipo_doc]).to_numpy(dtype=object)
                 if col_tipo_doc and col_tipo_doc in d.columns
                 else np.full(n, "F", dtype=object)),
        "usd": ((d[col_moneda].astype(str).str.strip() == "02").to_numpy()
                if col_moneda and col_moneda in d.columns
                else np.zeros(n, dtype=bool)),
        "punit": (pd.to_numeric(d[col_punit], errors="coerce").to_numpy(
                      dtype=float, na_value=np.nan)
                  if col_punit and col_punit in d.columns
                  else np.full(n, np.nan)),
    })
    return b[b["fecha"].notna()].reset_index(drop=True)


def referencias(b, hist):
    """`(refT, refS)`: el precio habitual de cada línea de `b`, como arrays.

    `refT` sale del histórico de TODOS los documentos y `refS` del de su
    mismo tipo (facturas o guías): es el que la vista de antes calculaba con
    «Documento» en Facturas o en Guías, porque filtraba el histórico antes
    (`_precio_habitual_de`). Una línea de «lo demás» no tiene `refS`: con
    esos filtros no entra. SIEMPRE NETO, como «Precio» (regla #621). Del
    producto y del DÍA: todas las líneas de un producto en un mismo día
    comparten la suya. Pura."""
    nan = np.full(len(b), np.nan)
    if b.empty or hist is None or hist.empty:
        return nan, nan
    lo = b["fecha"].min() - pd.Timedelta(days=_VENTANA_PRECIO)
    h = hist[(hist["fecha"] >= lo) & (hist["fecha"] <= b["fecha"].max())
             & hist["prod"].isin(set(b["prod"]))]
    idx = pd.MultiIndex.from_arrays([b["prod"].to_numpy(), b["fecha"].to_numpy()])

    def _ref(hh):
        if hh.empty:
            return nan
        r = precio_habitual(hh["prod"], hh["fecha"], hh["neto"], hh["cant"])
        s = pd.Series(r.to_numpy(), index=pd.MultiIndex.from_arrays(
            [hh["prod"].to_numpy(), hh["fecha"].to_numpy()]))
        return s[~s.index.duplicated()].reindex(idx).to_numpy(dtype=float)

    ref_t = _ref(h)
    ref_f, ref_g = _ref(h[h["tipo"] == "F"]), _ref(h[h["tipo"] == "G"])
    tipo = b["tipo"].to_numpy()
    return ref_t, np.where(tipo == "F", ref_f,
                           np.where(tipo == "G", ref_g, np.nan))


def _num_json(v, dec):
    return None if v != v else round(float(v), dec)


_VACIO = ("", "nan", "None", "<NA>")


def armar_pieza(b, hist_ops, nc, rango, flags, sello):
    """Lo que recibe la pieza. Pura.

    `b` son las líneas del rango (`lineas_pieza`, de TODOS los documentos:
    «Documento» lo aplica el navegador) con `refT` y `refS`; `hist_ops`, las
    del histórico con los chips de la franja, de donde salen las opciones de
    Familia y Subfamilia y el orden con que se reparten los colores de
    «Partir por»; `nc`, lo que restaron las notas de crédito (`_lineas_nc`).

    Fila de una línea (`lineas`): [día (desde `base`), producto, proveedor,
    documento, familia, subfamilia (índices de sus listas), cantidad, neto,
    IGV, tipo (índice de `_TIPOS`), en dólares (0/1), precio unitario o
    None, habitual de todos los documentos o None, habitual de su tipo o
    None]. La de una nota (`notas`): las doce primeras igual —el día es el
    de la FACTURA que corrige— y después [nota (índice de `nota_txt`), día
    de la nota].

    Neto e IGV con 6 decimales: el neto es el total ÷ 1,18 y trae los
    decimales de la división; redondeado a céntimos por línea —o a cuatro
    decimales— el total de una semana se corría un céntimo del parquet.

    `docs` va ORDENADA por el texto del parquet: el orden de los índices es
    el de los documentos, que es lo que desempata la clave de una compra.

    El orden de los colores de «Partir por» sale del histórico de TODOS los
    documentos y sin IGV: el color sigue a la subfamilia o al proveedor
    aunque se cambie «Documento» o «Montos»."""
    hist = hist_ops if hist_ops is not None and not hist_ops.empty else b
    provs = sorted(set(b["prov"]) | set(nc["prov"]))
    prods = sorted(set(b["prod"]) | set(nc["prod"]))
    docs = sorted(set(b["docn"]) | set(nc["docn"]))
    fams = sorted(set(b["fam"]) | set(nc["fam"]) | set(hist["fam"]))
    subs = sorted(set(b["sub"]) | set(nc["sub"]) | set(hist["sub"]))
    ip = {p: i for i, p in enumerate(provs)}
    ipr = {p: i for i, p in enumerate(prods)}
    idc = {x: i for i, x in enumerate(docs)}
    ifa = {f: i for i, f in enumerate(fams)}
    isu = {s: i for i, s in enumerate(subs)}
    it = {t: i for i, t in enumerate(_TIPOS)}
    base = b["fecha"].min()
    if len(nc):
        base = min(base, nc["fecha"].min(), nc["fecha_nc"].min())

    def _filas(t, extra):
        dia = (t["fecha"] - base).dt.days.tolist()
        return [[dd, ipr[pr], ip[pv], idc[dc], ifa[fa], isu[su],
                 round(c, 4), round(ne, 6), round(ig, 6), it.get(tp, 2),
                 int(bool(us)), _num_json(pu, 4), *ex]
                for dd, pr, pv, dc, fa, su, c, ne, ig, tp, us, pu, ex in zip(
                    dia, t["prod"], t["prov"], t["docn"], t["fam"], t["sub"],
                    t["cant"].tolist(), t["neto"].tolist(), t["igv"].tolist(),
                    t["tipo"], t["usd"], t["punit"].tolist(), extra)]

    lineas = _filas(b, [[_num_json(r, 6), _num_json(s, 6)]
                        for r, s in zip(b["refT"].tolist(), b["refS"].tolist())])
    nota_txt = sorted(set(nc["nota"])) if len(nc) else []
    ino = {x: i for i, x in enumerate(nota_txt)}
    notas = (_filas(nc, [[ino[x], int((f - base).days)]
                         for x, f in zip(nc["nota"], nc["fecha_nc"])])
             if len(nc) else [])
    # El número de la nota viene codificado como el de la factura, con «N0»
    # delante en vez de «F0» (`detalle_con_notas`).
    _pri = pd.Series([x.split(", ")[0] for x in nota_txt], dtype=object)
    nota_doc = []
    if len(_pri):
        _n15 = _pri.str.startswith("N0") & (_pri.str.len() == 15)
        nota_doc = documento_legible(_pri.where(~_n15, "F" + _pri.str[1:])).tolist()
    _con = [x for x in docs if x not in _VACIO]
    _leg = dict(zip(_con, documento_legible(pd.Series(_con, dtype=object))
                    if _con else []))

    def _orden(col):
        return (hist.groupby(col)["neto"].sum()
                .sort_values(ascending=False, kind="stable").index.tolist())

    o_sub, o_prov = _orden("sub"), _orden("prov")
    pos_sub = {s: i for i, s in enumerate(o_sub)}
    pos_prov = {p: i for i, p in enumerate(o_prov)}
    # Las opciones de Familia y Subfamilia, del histórico (regla #623), sin
    # vacíos, como el `dropna` de antes.
    f_ok = hist[~hist["fam"].isin(_VACIO)]
    s_ok = hist[~hist["sub"].isin(_VACIO)]
    fam_subs = {str(ifa[f]): sorted(isu[x] for x in set(g["sub"]))
                for f, g in s_ok.groupby("fam")}
    r0, r1 = (pd.Timestamp(x) for x in rango)
    feriados = sorted(f"{x:%Y-%m-%d}" for a in range(r0.year - 1, r1.year + 1)
                      for x in cortes.feriados_peru(a))
    return {
        "sello": sello, "base": f"{base:%Y-%m-%d}",
        "rango": [f"{r0:%Y-%m-%d}", f"{r1:%Y-%m-%d}"],
        "feriados": feriados, **flags,
        "provs": provs,
        "prov_n": [nombre_propio(p) if p not in _VACIO else "" for p in provs],
        "prov_c": [_rotulo_proveedor(p) for p in provs],
        "prods": prods, "docs": [str(_leg.get(x, "")) for x in docs],
        "fams": fams, "fam_n": [_nombre_familia(f) for f in fams],
        "subs": subs, "sub_n": [_rotulo_subfamilia(s) for s in subs],
        "fam_ops": sorted(ifa[f] for f in set(f_ok["fam"])),
        "sub_ops": sorted(isu[s] for s in set(s_ok["sub"])),
        "fam_subs": fam_subs,
        "ord_sub": [pos_sub.get(s) for s in subs], "n_ord_sub": len(o_sub),
        "ord_prov": [pos_prov.get(p) for p in provs], "n_ord_prov": len(o_prov),
        "lineas": lineas, "notas": notas, "nota_txt": nota_txt,
        "nota_doc": nota_doc, "etq_techo": _ETQ_TECHO,
    }


def sello_pieza(b, nc, hist_ops):
    """La identidad de lo que recibe la pieza: el estado de lo elegido se
    conserva mientras no cambie."""
    partes = [int(pd.util.hash_pandas_object(
        x[["fecha", "prod", "prov", "docn", "neto", "igv"]], index=False).sum())
        for x in (b, nc) if len(x)]
    return (f"{len(b)}-{len(nc)}-{0 if hist_ops is None else len(hist_ops)}-"
            f"{sum(partes) & 0xFFFFFFFFFFFF:x}")


_PIEZA = st.components.v2.component(
    "compras_periodo",
    css=(Path(__file__).parent / "semanal.css").read_text(encoding="utf-8"),
    # El Excel (`libro`, `bajar`, `archivo`) vive en `_xlsx.js`: se antepone.
    js=(Path(__file__).parent.parent / "_xlsx.js").read_text(encoding="utf-8")
    + (Path(__file__).parent / "semanal.js").read_text(encoding="utf-8"),
)
_K_PIEZA = "cp_sem_pieza"
_K_CACHE = "_cp_sem_pieza_cache"
"""`(firma, mensaje)` de la última corrida: el precio habitual sobre el
histórico son ~0,5 s, y un rerun del fragment con el mismo `d` no tiene por
qué volver a pagarlos."""


@st.fragment
def _compras_semanal_drill(d, col_prod, col_fecha, col_cant, col_punit,
                           col_prov, col_docu, col_valor,
                           col_fam=None, d_full=None, col_subfam=None,
                           col_valor_neto=None, col_igv=None,
                           col_tipo_doc=None, col_moneda=None, d_nc=None):
    """«Compras por período»: la fecha (Python) y la pieza. Ver el docstring
    del módulo y `arquitectura.md` regla #716.

    La firma es la de antes (`col_valor_neto` sin usar): en Cloud un commit
    que le cambia la firma a algo ya importado deja el `app.py` nuevo
    hablando con el paquete viejo (regla #357). `d` llega con todos los
    documentos: «Documento» y «Montos» los aplica el navegador."""
    # La escalada del selector de fecha: el filtro que lee el rango vive en
    # app.py, FUERA de este fragment (regla #180).
    if st.session_state.pop("_cp_sem_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")
    with st.container(border=True, key="ajuste_graf_card_izq_sem"):
        # El CSS de la fila del selector de fecha (`cp_sem_fila`) vive en
        # `_css_proveedor.py`, y esta sección se construye antes que las
        # demás que lo inyectan.
        st.markdown(CSS_PROVEEDOR, unsafe_allow_html=True)
        with st.container(key="cp_sem_fecha"):
            _ctx_fecha = selector_fecha_tarjeta(
                "cp_sem", "_cp_sem_atajo_pendiente",
                categoria=CATEGORIA_SEC["compras_sec_semanal"])
        if not (col_prod and col_fecha):
            st.info("No hay columnas suficientes para este gráfico.")
            return
        cols = (col_prod, col_fecha, col_cant, col_punit, col_prov, col_docu,
                col_valor, col_fam, col_subfam, col_igv, col_tipo_doc,
                col_moneda)
        rango = (rango_tarjeta(CATEGORIA_SEC["compras_sec_semanal"], _ctx_fecha)
                 if _ctx_fecha else None)
        firma = (id(d), d.shape, id(d_full), id(d_nc),
                 None if d_nc is None else d_nc.shape, str(rango))
        cache = st.session_state.get(_K_CACHE)
        if cache is not None and cache[0] == firma:
            datos = cache[1]
        else:
            b = lineas_pieza(d, cols)
            if b.empty:
                st.info("Sin compras en el rango seleccionado. Ampliá el rango "
                        "desde la fecha de la tarjeta.")
                return
            hist = lineas_pieza(d_full, cols) if d_full is not None else b
            b["refT"], b["refS"] = referencias(b, hist)
            nc = _lineas_nc(d_nc, col_fecha, col_prod, col_prov, col_docu,
                            col_fam, col_subfam, col_valor, col_igv,
                            col_tipo_doc, DOC_TODOS, col_cant=col_cant,
                            col_punit=col_punit, col_moneda=col_moneda)
            nc = nc.assign(fecha=pd.to_datetime(nc["fecha"]).dt.normalize(),
                           fecha_nc=pd.to_datetime(nc["fecha_nc"]).dt.normalize())
            if not rango or any(x is None for x in rango):
                rango = (b["fecha"].min(), b["fecha"].max())
            flags = {
                "hay_fam": bool(col_fam) and col_fam in d.columns,
                "hay_sub": bool(col_subfam) and col_subfam in d.columns,
                "hay_prov": bool(col_prov) and col_prov in d.columns,
                "hay_cant": bool(col_cant),
                "hay_doc": bool(col_prov and col_docu),
                "hay_tipo": bool(col_tipo_doc) and col_tipo_doc in d.columns,
                "hay_igv": bool(col_igv) and col_igv in d.columns,
            }
            datos = armar_pieza(b, hist, nc, rango, flags,
                                sello_pieza(b, nc, hist))
            st.session_state[_K_CACHE] = (firma, datos)
        _PIEZA(key=_K_PIEZA, data=datos, width="stretch")
