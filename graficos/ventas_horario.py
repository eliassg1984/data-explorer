"""
graficos.ventas_horario — vista «Por hora» del dashboard de Ventas: mapa de
calor DÍA × HORA de hasta cuatro períodos comparados, con marcas
rectangulares hechas a mano y drill al detalle de cada marca.

QUÉ ES UNA COLUMNA Y QUÉ ES UN PANEL
    La granularidad decide las dos cosas a la vez. Cada período elegido es un
    PANEL (una franja del mapa) y dentro de él las COLUMNAS son:

      · Día     1 columna  (el día entero)
      · Semana  7 columnas (lun → dom)
      · Mes     28-31      (día del mes)
      · Año     12         (mes)

    El eje Y son siempre las horas con dato — no 0-23 fijo: un local que abre
    a las 11 no gana nada mostrando doce filas vacías.

LOS CUATRO PANELES SE ELIGEN A MANO
    La franja de fecha del reporte define UN rango; acá hacen falta hasta
    cuatro períodos que pueden estar fuera de él (julio contra abril). Por eso
    cada panel se trae con `data.cargar_rango` — un tramo por panel, cacheado —
    y se le aplican LOS MISMOS chips vía `filtrar_cb`, igual que en
    ventas_comparativo: sin eso el mapa contradice los chips de la pantalla.

    En Mes y Año la celda es la SUMA del período (decisión del usuario,
    2026-08-14): "los viernes 19h de todo julio" es plata que entró, no un
    promedio. La consecuencia está avisada en el pie: bloques de distinto
    tamaño no se comparan por el total sino por «venta por celda».

LAS MARCAS SON RECTÁNGULOS, Y SIEMPRE
    Una marca es `(panel, col0..col1, hora0..hora1)`. La celda suelta es un
    rectángulo 1×1, "todo el viernes" es una columna entera y "las 19h de la
    semana" es una fila: un solo concepto en vez de tres modos de clic.

    Un arrastre que cruza de un panel al siguiente se PARTE en una marca por
    panel (opción A, elegida por el usuario el 2026-08-14): el gesto de
    arrastrar sobre dos semanas *es* la comparación, y dejarla armada de una
    pasada ahorra la mitad de los clics. Con más de cuatro se descartan las
    más viejas.

TRES TRAMPAS QUE YA ESTÁN RESUELTAS ACÁ (y que muerden si alguien las toca)

  1. `go.Heatmap` NO es seleccionable en Plotly: el box-select no emite nada
     sobre un heatmap. Por eso encima va una capa `go.Scatter` transparente,
     un marcador por celda, que sí soporta box/lasso y devuelve en su
     `customdata` a qué panel/columna/hora corresponde cada punto. Es también
     la que lleva el hover.

  2. Selección VACÍA no significa "borrá las marcas". Con `dragmode="select"`
     un clic al vacío devuelve una selección vacía; si las marcas se
     derivaran del evento en vez de acumularse en `session_state`, un clic
     torpe limpiaría el panel entero.

  3. La misma selección se re-procesa en CADA rerun mientras el widget siga
     montado (CLAUDE.md § Streamlit): sin defensa, la marca se vuelve a
     aplicar sola en bucle. La defensa es la HUELLA (`_K_SEL`): se guarda la
     de la última selección atendida y se ignora si vuelve igual.

     Hasta el 2026-08-15 la defensa era otra: meter la firma de las marcas
     en la `key`, para que el widget se re-montara y llegara sin selección.
     Funcionaba, pero re-montar es tirar el componente y construir otro, y
     Plotly repinta de cero — eso era el PARPADEO al seleccionar (medido: el
     nodo del `.js-plotly-plot` se reemplazaba por otro en cada arrastre).
     Con la huella la key queda quieta, Streamlit actualiza en vez de
     remontar y el mapa no pestañea.

     Lo que hizo falta para poder soltar la key: que ningún arrastre se
     quede sin puntos. Con la capa de selección cubriendo TODAS las celdas
     (ver `_fig_mapa`), Plotly limpia solo su rectángulo punteado al soltar,
     que era la otra cosa que arreglaba el remonte.

     Corolario que NO se puede evitar: re-arrastrar sobre una marca
     existente no la quita —`on_select` sólo dispara cuando la selección
     CAMBIA—, así que quitar marcas es cosa del selector de períodos, no del
     mapa.
"""

import calendar as _cal
import datetime as _dt
import zlib as _zlib
from collections import namedtuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
import definicion_venta as dv
from data import REPORTES, cargar_rango, rango_fechas
from tema import (
    ACENTO, ADVERTENCIA, ADVERTENCIA_TEXTO, AJUSTE_NEG, AJUSTE_POS, BLANCO,
    ERROR, ESCALA_CONTINUA, EXITO, GRIS_CUADRICULA, GRIS_LINEA, GRIS_TEXTO,
    PALETA_SERIES, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos import ventas_ficha_hora as _fh
from inyecciones._iframe import inyectar_html
from graficos.base import (
    _card, _resolver, ctx_rango_propio, franja_linea_inferior, paso_etiquetas,
    publicar_var_px, rango_tarjeta, selector_fecha_tarjeta,
)
from graficos.compras._comun import _first_point
# Los helpers de calendario NO se duplican: son los mismos que usa la vista
# "Año Pasado" y ya están cubiertos por test_graficos.py. Acá sólo se extienden
# para la granularidad Año, que allá no existe (comparar 2025 contra 2024 es
# justamente lo que esa vista hace por su cuenta).
from graficos.ventas_comparativo import (
    _DIAS_ES,
    _MESES_ES,
    _clave_de_fecha as _clave_de_fecha_cmp,
    _claves_hacia_atras as _claves_cmp,
    _etiqueta_clave as _etiqueta_cmp,
    _feriados_peru,
    _rango_de_clave as _rango_cmp,
)

GRANOS = ("Día", "Semana", "Mes", "Año")
MAX_MARCAS = 4

# Cuántos períodos ofrece el selector hacia atrás por granularidad. Más días
# que semanas a propósito: "los últimos 10 días" es una lista que se lee de un
# vistazo, "los últimos 10 años" es una lista que no existe en los datos.
_N_LISTA = {"Día": 10, "Semana": 8, "Mes": 9, "Año": 5}

# Color de cada marca. Salen de PALETA_SERIES (nunca un #hex suelto, CLAUDE.md)
# y están elegidos para que las cuatro se distingan entre sí SOBRE el azul del
# mapa: violeta, naranja, verde y cian.
_COLOR_MARCA = (PALETA_SERIES[0], PALETA_SERIES[3],
                PALETA_SERIES[4], PALETA_SERIES[1])

# id → (etiqueta, formato). El orden es el CANÓNICO de las filas/columnas del
# drill: no se reordena por orden de clic, que haría bailar la tabla bajo el
# cursor en cada pastilla que se toca.
_MEDIDAS = (
    ("venta",  "Venta"),
    ("pax",    "Pax"),
    ("cant",   "Cantidad"),
    ("ticket", "Ticket promedio"),
    ("desc",   "Descuento"),
)
_MED_LABEL = dict(_MEDIDAS)
# Etiqueta corta para la franja del MAPA, donde los controles comparten fila
# con el título. Sólo cambia lo que no entra; el drill usa el nombre entero.
_MED_CORTO = {"ticket": "Ticket"}
_MED_FMT = {
    "venta": "S/ {:,.0f}", "pax": "{:,.0f}", "cant": "{:,.0f}",
    "ticket": "S/ {:,.2f}", "desc": "S/ {:,.0f}",
}

# Medidas que puede mostrar el ÁRBOL. Pax y ticket quedan fuera a propósito:
# a nivel de plato no existen (un pedido de 4 pax no reparte "1 pax" por
# plato), y una columna que miente es peor que una columna que falta.
_MED_ARBOL = ("venta", "cant", "desc")

# Tope de columnas numéricas del árbol. Con 4 marcas × 3 medidas serían 12
# columnas de números: ilegible en cualquier pantalla. Pasado el tope, el
# árbol se queda con la primera medida y lo dice.
_MAX_COLS_ARBOL = 8

# Geometría del mapa. El alto de la figura sigue al NÚMERO DE HORAS con dato
# (`alturas.por_filas`) en vez de estirarse siempre al techo de la tarjeta: un
# turno corto repartía el mismo alto entre menos filas y salían bandas con más
# aire que dato. 22px por hora es la fila compacta; el techo lo sigue poniendo
# `alturas.con_franja()`, así que un turno largo no desborda la pantalla.
_PX_HORA = 22
# Lo que la figura reserva ADEMÁS de las filas. Con varios paneles hay que
# dejar sitio para sus rótulos (34px de margen superior); con uno solo ese
# rótulo se fue al título de la tarjeta y el aire sobrante era espacio muerto
# entre las celdas y los números de día. Medido: 26px entre la última celda y
# la etiqueta, más 10 bajo ella.
_AIRE_MAPA = 66        # con varios paneles
_AIRE_MAPA_SOLO = 42   # con uno
_ALTO_MIN = 170    # con 3-4 horas la figura no se convierte en una cinta

# Con el DRILL ABIERTO el mapa se encoge para que los dos entren en la misma
# pantalla (ver `alturas.reparto`). 15px por hora contra los 22 de reposo: la
# celda sigue siendo un rectángulo legible y el mapa NO se va de la vista, que
# es de lo que se trata — comparar el detalle contra el gráfico sin scrollear.
_PX_HORA_DRILL = 15
# 2026-08-15: aquí vivía `_AIRE_MARCAS = 44`, la fila de pastillas de marcas
# que iba entre el mapa y la tabla del drill. Esa fila ya no existe (la tabla
# muestra todas las medidas de entrada), así que el término sale del
# presupuesto de `vh-alto-arriba` y esos 44px se los queda el panel.
# Padding y gaps de la tarjeta del mapa (8+8 de padding, tres gaps de 6, los
# márgenes del hairline). Medido: publicar sin esto daba 351 contra un bloque
# real de 390, y el panel se pasaba justo esos 39px.
_CROMO_TARJETA = 39
# Piso del panel del drill: menos que esto no se lee.
_PANEL_MIN = 150

# El arranque es UN solo panel: el mes EN CURSO. Comparar es una decisión
# explícita del usuario y tiene su botón (pedido del 2026-08-14). La versión
# anterior abría con cuatro paneles y obligaba a leer cuatro trozos para
# responder "¿cómo va esto?", que es la pregunta que uno trae al abrir. Desde
# el 2026-09-25 el mes sale del rango con que abre el selector de fecha de
# la vista (regla #531), que es el mes en curso hasta el último día con datos.
_GRANO_DEF = "Mes"

# Cuánto ancho se supone disponible para el eje X. Es una ESTIMACIÓN, y es la
# única que queda en este módulo: el ancho real lo sabe el navegador, no
# Python (regla #117 — la resta contra una pantalla supuesta). No se puede
# publicar como variable CSS porque quien la necesita es Plotly, que dibuja
# en el servidor.
#
# Es el ÁREA DE DIBUJO, no la figura: a 1280px con los dos rails abiertos la
# figura mide 889 y el área 769 (46px de eje de horas a la izquierda, 74 de
# barra de color a la derecha). Confundir las dos infla el hueco de la
# derecha, porque un `ancho` de más pide más columnas de reserva.
# 2026-08-15: 740 → 770, en sync con la tarjeta, que creció de 879 a 947px
# (y a 1083 con los rails plegados, así que 770 sigue siendo el extremo
# estrecho y por lo tanto el conservador).
_ANCHO_UTIL = 770

# Ancho máximo de una celda, y de ahí sale el hueco de la derecha (`_rango_x`).
# Ya no es un número suelto sino una PROPORCIÓN contra el alto de fila: una
# celda puede ser hasta tres veces más ancha que alta, y pasado eso deja de
# leerse como celda y se lee como bandera. Atado a `_PX_HORA` para que las
# dos medidas de la celda se muevan juntas — con el 44 fijo de antes, subir
# la altura de fila habría hecho las celdas más altas que anchas sin que
# nadie lo pidiera.
_RATIO_MAX_CELDA = 3

_SIN_DSCTO = "Sin descuento"

# LA FECHA ES DE LA VISTA (2026-09-25, regla #531): el selector de la
# cabecera escribe `rango_cat_Ventas_vt_hora`, no la fecha de arriba. Los
# paneles salen de ese rango partido por la granularidad; «Comparar» suma
# períodos SUELTOS (`_K_EXTRAS`), como el mismo mes del año pasado.
_CAT_RANGO = "vt_hora"
_K_EXTRAS = "vh_extras"      # períodos sueltos de «Comparar» (lista de claves)
_K_FIRMA_PANELES = "vh_paneles_firma"  # qué paneles había en la corrida previa
_K_MARCAS = "vh_marcas"      # marcas (lista de dicts)
_K_SELECTOR = "vh_selector"  # ¿está abierto el selector de períodos?
# Huella de la última selección ATENDIDA. Es lo que evita re-aplicarla en
# cada rerun sin tener que remontar el chart. Ver la trampa 3 del docstring.
_K_SEL = "vh_sel_huella"
# La celda del CLIC, la que abre la ficha de la hora (regla #536): un dict
# `{"sel", "c", "h"}` como una marca de 1×1, pero no es una marca.
_K_FOCO = "vh_foco"
# «Venta Interna y Eventos»: el interruptor sólo existe en «Días × horas» y
# se esconde en «Platos»/«Grupos»; su valor vive aparte para que volver no
# lo resetee (un widget que no se dibuja pierde su estado, CLAUDE.md).
_K_RAROS = "vh_raros"
_K_RAROS_VALOR = "_vh_raros_valor"

# EL CLIC SUELTO LO TRAE ESTE PUENTE (regla #536). Con `dragmode="select"`
# Streamlit fuerza `clickmode="event"` y descarta el clic —también en la
# 1.64 de Cloud: su `handleClickEvent` sólo atiende treemap y sunburst—
# (regla #388). Plotly igual emite `plotly_click`; este script lo escucha
# y lo reenvía como una SELECCIÓN de un punto (`plotly_selected`), que es
# lo que Streamlit sí lee. Tres cosas que no son adorno:
#   · el punto va LIMPIO: el del evento trae `data`, `fullData` y los ejes,
#     con referencias circulares, y el `JSON.stringify` de Streamlit
#     reventaría. `data: {}` porque Streamlit lee `data.legendgroup`;
#   · su `customdata` lleva «clic», para que Python lo distinga de un
#     arrastre sobre una celda (ése trae `box` y sigue armando marcas);
#   · y la hora del clic, para que volver a tocar la misma celda sea una
#     selección NUEVA: Streamlit no avisa si la selección no cambió, y
#     después de cerrar la ficha no habría forma de reabrirla.
# Cada inyección le saca el oyente a la anterior y se engancha ella (el
# iframe que lo instaló puede no existir más), y un gráfico remontado —otra
# key— se engancha en la vuelta siguiente del reloj.
_JS_CLIC_MAPA = """<script>
(function () {
  var w = window.parent, doc = w.document, yo = {};
  var SEL = '[class*="st-key-vh_mapa_"] .js-plotly-plot';
  function alClic(gd) {
    return function (ev) {
      var pts = (ev && ev.points) || [];
      for (var i = 0; i < pts.length; i++) {
        var p = pts[i], cd = p.customdata;
        if (!cd || cd.length < 3) continue;
        gd.emit("plotly_selected", {points: [{
          curveNumber: p.curveNumber, pointNumber: p.pointNumber,
          pointIndex: p.pointIndex, x: p.x, y: p.y,
          customdata: [cd[0], cd[1], cd[2], "clic", Date.now()],
          data: {}, fullData: {}
        }]});
        return;
      }
    };
  }
  function enganchar() {
    var gds = doc.querySelectorAll(SEL);
    for (var i = 0; i < gds.length; i++) {
      var gd = gds[i];
      if (gd.__vhClicDueno === yo || typeof gd.on !== "function") continue;
      try {
        if (gd.__vhClicFn) gd.removeListener("plotly_click", gd.__vhClicFn);
      } catch (e) {}
      gd.__vhClicFn = alClic(gd);
      gd.__vhClicDueno = yo;
      gd.on("plotly_click", gd.__vhClicFn);
    }
  }
  try { if (w.__vhClicApagar) w.__vhClicApagar(); } catch (e) {}
  var reloj = setInterval(enganchar, 700);
  w.__vhClicApagar = function () { clearInterval(reloj); };
  enganchar();
})();
</script>"""


# ── Funciones puras (calendario) ────────────────────────────────────────────

# UN PANEL QUE EL RANGO CORTA (regla #531): el trozo [desde, hasta] de un
# período. Del 26 al 31 de agosto, en Mes, es `_Tramo((2026, 8), 26-ago,
# 31-ago)`. Un período ENTERO sigue siendo su clave de siempre (una tupla,
# una fecha o un año), así que lo que sólo conoce claves —«Comparar»,
# «Análisis de platos», el comparativo— no se entera de que esto existe.
# Las funciones de calendario de abajo aceptan las dos formas.
_Tramo = namedtuple("_Tramo", "clave desde hasta")


def _base_clave(k):
    """La clave del período entero al que pertenece `k`."""
    return k.clave if isinstance(k, _Tramo) else k


def _offset(k, grano):
    """Cuántas columnas del período quedan a la IZQUIERDA del tramo: el del
    26 al 31 de agosto arranca en la columna 25. Cero en un período entero.

    Es lo que mantiene honestas dos cosas: que el panel no dibuje del 1 al 25
    vacíos (se leerían como días sin venta) y que la «Diferencia» reste la
    misma columna del CALENDARIO —el miércoles con el miércoles— aunque un
    panel arranque a mitad de semana."""
    if not isinstance(k, _Tramo):
        return 0
    return int(_columna_de_fecha(pd.Series([pd.Timestamp(k.desde)]),
                                 grano).iat[0])


def _fmt_tramo(desde, hasta):
    """«27–31 Ago 26», «27 Ago – 2 Sep 26», «28 Dic 25 – 3 Ene 26»: el nombre
    de un trozo de período, con el mes y el año como «Ago 26», que es como se
    llaman los paneles enteros de al lado. El año NO es opcional: con «Año
    pasado» en «Comparar», el trozo de este año y el del anterior se
    llamarían igual."""
    def _m(f):
        return _MESES_ES[f.month - 1]
    if desde == hasta:
        return f"{desde.day} {_m(desde)} {desde:%y}"
    if (desde.year, desde.month) == (hasta.year, hasta.month):
        return f"{desde.day}–{hasta.day} {_m(hasta)} {hasta:%y}"
    if desde.year == hasta.year:
        return f"{desde.day} {_m(desde)} – {hasta.day} {_m(hasta)} {hasta:%y}"
    return (f"{desde.day} {_m(desde)} {desde:%y} – "
            f"{hasta.day} {_m(hasta)} {hasta:%y}")


def _fmt_rango_corto(ini, fin):
    """El texto del selector de fecha de la vista: «1–24 sep 2026» y no
    «1 sep – 24 sep 2026». Seis caracteres menos son ~40px, y es lo que deja
    entrar la fila de la cabecera con la columna de la izquierda fijada a
    1366px (medido: 992px de fila contra 1020 que pedía con el largo). En
    minúscula y con el año entero, como el resto de los selectores de fecha
    (`franja_fecha.fmt_rango_es`)."""
    def _m(f):
        return _MESES_ES[f.month - 1].lower()
    if ini.year != fin.year:
        return (f"{ini.day} {_m(ini)} {ini.year} – "
                f"{fin.day} {_m(fin)} {fin.year}")
    if ini == fin:
        return f"{ini.day} {_m(ini)} {ini.year}"
    if ini.month == fin.month:
        return f"{ini.day}–{fin.day} {_m(fin)} {fin.year}"
    return f"{ini.day} {_m(ini)} – {fin.day} {_m(fin)} {fin.year}"


def _paneles_del_rango(ini, fin, grano, ultimo=None):
    """Los paneles que dibuja el rango [ini, fin]: un período de `grano` por
    panel, cronológicos, cada uno recortado al rango (regla #531).

    Un período queda ENTERO —su clave de siempre, «Ago 26»— si el rango lo
    cubre de punta a punta, y también si lo corta el último día CON DATOS
    (`ultimo`): el mes en curso hasta el 24 sigue siendo «Sep 26», como
    siempre fue. Si el rango lo corta por otro lado es un `_Tramo`."""
    if not ini or not fin or ini > fin:
        return []
    out, dia = [], ini
    while dia <= fin:
        k = _clave_de_fecha(dia, grano)
        p0, p1 = _rango_de_clave(k, grano)
        desde, hasta = max(p0, ini), min(p1, fin)
        tope = min(p1, ultimo) if ultimo else p1
        out.append(k if (desde == p0 and hasta >= tope)
                   else _Tramo(k, desde, hasta))
        dia = p1 + _dt.timedelta(days=1)
    return out


def _claves_hacia_atras(ancla, grano, n):
    """Las `n` claves de período que terminan en el período de `ancla`."""
    if grano == "Año":
        return list(range(ancla.year - n + 1, ancla.year + 1))
    return _claves_cmp(ancla, grano, n)


def _rango_de_clave(clave, grano):
    """(primer_día, último_día) del período, o del trozo si es un `_Tramo`."""
    if isinstance(clave, _Tramo):
        return clave.desde, clave.hasta
    if grano == "Año":
        return _dt.date(clave, 1, 1), _dt.date(clave, 12, 31)
    return _rango_cmp(clave, grano)


def _etiqueta_clave(clave, grano):
    """Etiqueta corta del período — la que titula su panel."""
    if isinstance(clave, _Tramo):
        return _fmt_tramo(clave.desde, clave.hasta)
    if grano == "Año":
        return str(clave)
    return _etiqueta_cmp(clave, grano)


def _clave_de_fecha(f, grano):
    """Clave del período al que pertenece la fecha `f`. Es lo que convierte
    "elegí el 14 de febrero" en el período que hay que dibujar, sea el día,
    su semana, su mes o su año."""
    if grano == "Año":
        return f.year
    return _clave_de_fecha_cmp(f, grano)


# «7 pm» y no «19h». Vive en `cortes.py` desde el 2026-09-26 (la pidió la
# ficha de la hora); el alias conserva el nombre que usan este módulo y
# test_graficos.py.
_etiqueta_hora = cortes.etiqueta_hora


def _tramo_horas(h0, h1):
    """«7 pm – 9 pm», o «7 pm» si es una sola."""
    return (_etiqueta_hora(h0) if h0 == h1
            else f"{_etiqueta_hora(h0)}–{_etiqueta_hora(h1)}")


def _fecha_de_columna(clave, grano, i):
    """Fecha del día que representa la columna `i`, o None si la columna no
    es un día (granularidad Año: cada columna es un mes entero)."""
    if isinstance(clave, _Tramo):
        return _fecha_de_columna(clave.clave, grano,
                                 int(i) + _offset(clave, grano))
    if grano == "Día":
        return clave
    if grano == "Semana":
        return _rango_de_clave(clave, grano)[0] + _dt.timedelta(days=int(i))
    if grano == "Mes":
        y, m = clave
        n = _cal.monthrange(y, m)[1]
        return _dt.date(y, m, min(int(i) + 1, n))
    return None


def _marca_dia(fecha, feriados):
    """Qué tiene de especial ese día: '' | 'finde' | 'feriado'.

    El feriado gana al fin de semana cuando caen juntos: un domingo feriado
    ya se leía como domingo, lo que no se ve es que además era feriado."""
    if fecha is None:
        return ""
    if fecha in feriados:
        return "feriado"
    return "finde" if fecha.weekday() >= 5 else ""


def _feriados_de(claves, grano):
    """Feriados peruanos de los años que tocan las claves elegidas.

    Reusa el calendario de `ventas_comparativo` — el mismo que ya pinta las
    bandas de la vista "Año Pasado", para que un 28 de julio no sea feriado
    en un gráfico y un día común en el de al lado. Ojo con lo que ese módulo
    ya avisa: es el calendario NACIONAL, no sabe de cierres del local."""
    anios = set()
    for k in claves:
        ini, fin = _rango_de_clave(k, grano)
        anios.update({ini.year, fin.year})
    out = set()
    for a in anios:
        out |= set(_feriados_peru(a))
    return out


def _columnas(clave, grano, hasta=None):
    """(n_columnas, etiquetas) dentro de un período.

    En Mes el número depende del mes concreto (28/29/30/31): febrero no tiene
    31 columnas vacías al final, que se leerían como "cayó la venta".

    `hasta` recorta el período EN CURSO al último día con datos, por lo mismo:
    el 14 de agosto, "agosto" son 14 columnas, no 31 con diecisiete vacías a
    la derecha. Es la versión visual del recorte que `ventas_comparativo`
    hace sobre los totales (`_rangos_comparables`): un período a medias se
    muestra hasta donde llegó, no hasta donde llegará.

    Un `_Tramo` se recorta por los DOS lados: del 26 al 31 de agosto son 6
    columnas rotuladas 26…31, no 31 con las 25 primeras vacías."""
    if isinstance(clave, _Tramo):
        _n, etiquetas = _columnas(clave.clave, grano)
        fin = clave.hasta if hasta is None else min(clave.hasta, hasta)
        ult = int(_columna_de_fecha(pd.Series([pd.Timestamp(fin)]),
                                    grano).iat[0])
        etiquetas = etiquetas[_offset(clave, grano):ult + 1]
        return len(etiquetas), etiquetas
    if grano == "Día":
        return 1, [""]
    if grano == "Semana":
        n, etiquetas = 7, list(_DIAS_ES)
    elif grano == "Mes":
        n = _cal.monthrange(clave[0], clave[1])[1]
        etiquetas = [str(i) for i in range(1, n + 1)]
    else:
        n, etiquetas = 12, list(_MESES_ES)
    if hasta is not None:
        ini, fin = _rango_de_clave(clave, grano)
        if ini <= hasta < fin:
            n = min(n, _columna_de_fecha(
                pd.Series([pd.Timestamp(hasta)]), grano).iat[0] + 1)
            etiquetas = etiquetas[:n]
    return n, etiquetas


def _columna_de_fecha(fechas, grano):
    """Índice de columna (0-based) de cada fecha dentro de su período."""
    if grano == "Día":
        return pd.Series(0, index=fechas.index, dtype="int64")
    if grano == "Semana":
        return fechas.dt.weekday
    if grano == "Mes":
        return fechas.dt.day - 1
    return fechas.dt.month - 1


def _orden_horas(horas):
    """Las horas con dato, ordenadas por DÍA DE SERVICIO y no por número.

    Un restaurante que cierra a la 1 de la mañana tiene ventas a las 00h, y
    esas 00h son el final de la noche anterior, no el principio del día. Con
    el orden numérico crudo salían primero (00h arriba de todo, antes de las
    13h) y además el eje numérico dejaba doce filas vacías entre medio —
    medido en la app con datos reales de R2 el 2026-08-14: el eje traía
    [0, 13, 14, …, 23].

    El corte se busca solo: se arranca justo DESPUÉS del hueco más grande del
    círculo de 24 horas. Con {0, 13..23} el hueco mayor es 01h→12h, así que
    el orden sale 13, 14, …, 23, 0 — el turno tal como se vive.
    """
    hs = sorted({int(h) % 24 for h in horas})
    if len(hs) <= 1:
        return hs
    # Hueco entre cada hora y la siguiente, cerrando el círculo al final.
    saltos = [((hs[(i + 1) % len(hs)] - h) % 24, i) for i, h in enumerate(hs)]
    _mayor, i = max(saltos)
    corte = (i + 1) % len(hs)
    return hs[corte:] + hs[:corte]


def _horas_entre(orden, h0, h1):
    """Las horas del tramo que va de `h0` a `h1` SEGÚN el orden de servicio.

    No es `range(h0, h1+1)`: en un turno que cruza la medianoche, "23h a 0h"
    son dos horas, y con la comparación numérica cruda serían las veinticuatro
    (0 ≤ h ≤ 23). Esa cuenta silenciosa habría inflado cualquier marca que
    tocara la medianoche."""
    if h0 not in orden or h1 not in orden:
        return [h for h in orden if min(h0, h1) <= h <= max(h0, h1)]
    p0, p1 = orden.index(h0), orden.index(h1)
    if p0 > p1:
        p0, p1 = p1, p0
    return orden[p0:p1 + 1]


def _etiqueta_columnas(pin, clave, grano):
    """Trozo 'vie–dom' / 'día 3–9' / 'ago–oct' de la etiqueta de una marca.
    Vacío en granularidad Día: ahí la columna ES el período, y repetirlo
    daría 'vie 08/08 · vie'."""
    if grano == "Día":
        return ""
    _n, etiquetas = _columnas(clave, grano)
    c0 = etiquetas[min(pin["c0"], _n - 1)]
    c1 = etiquetas[min(pin["c1"], _n - 1)]
    if grano == "Mes":
        return f"día {c0}" if c0 == c1 else f"días {c0}–{c1}"
    return c0 if c0 == c1 else f"{c0}–{c1}"


# ── Funciones puras (marcas) ────────────────────────────────────────────────

def _marca_de_puntos(sel, cols, horas, orden):
    """Rectángulo que ENVUELVE a los puntos seleccionados de un panel.

    Una selección de caja es rectangular por construcción, así que el
    envolvente no inventa nada: es exactamente lo que el usuario encerró. Los
    extremos de hora se toman por POSICIÓN en el orden de servicio, no por
    número: en un turno que cruza la medianoche, min/max numérico de
    {23, 0} daría "de 0h a 23h", o sea el día entero."""
    pos = [orden.index(h) for h in horas if h in orden] or [0]
    return {"sel": int(sel),
            "c0": int(min(cols)), "c1": int(max(cols)),
            "h0": int(orden[min(pos)]), "h1": int(orden[max(pos)])}


def _marcas_de_seleccion(puntos, orden):
    """Las marcas que sale de UNA selección, partida por panel (opción A).

    `puntos` son tuplas `(panel, columna, hora)`. Un arrastre que cruza de un
    panel al siguiente deja una marca en cada uno, con las coordenadas que le
    tocaron a cada lado — que no tienen por qué ser las mismas: el borde
    derecho de un mes de 31 días y el de uno de 30 no caen en el mismo sitio.
    """
    por_panel = {}
    for sel, col, hora in puntos:
        por_panel.setdefault(int(sel), []).append((int(col), int(hora)))
    out = []
    for sel in sorted(por_panel):
        cols = [c for c, _h in por_panel[sel]]
        horas = [h for _c, h in por_panel[sel]]
        out.append(_marca_de_puntos(sel, cols, horas, orden))
    return out


def _agregar_marcas(marcas, nuevas, tope=MAX_MARCAS):
    """Suma `nuevas` a `marcas` sin repetir y respetando el tope.

    Cuando se pasa del tope se van las MÁS VIEJAS, no las nuevas: un arrastre
    sobre los cuatro paneles tiene que dejar esas cuatro marcas, no las dos
    que quedaban de antes más dos de éstas."""
    out = list(marcas)
    for m in nuevas:
        if m not in out:
            out.append(m)
    return out[-tope:]


def _etiqueta_marca(pin, claves, grano):
    """'Sem 33 · vie–dom · 18–21h' — el nombre de una marca en pastillas,
    cabeceras de tabla y anotaciones del mapa. Uno solo, para que la misma
    marca no se llame de dos formas distintas en dos sitios."""
    clave = claves[pin["sel"]] if pin["sel"] < len(claves) else None
    per = _etiqueta_clave(clave, grano) if clave is not None else "?"
    cols = _etiqueta_columnas(pin, clave, grano) if clave is not None else ""
    return " · ".join(
        x for x in (per, cols, _tramo_horas(pin["h0"], pin["h1"])) if x)


def _celdas_de_marca(pin, orden):
    """Cuántas celdas (columna × hora) encierra la marca. Es el denominador de
    «venta por celda», la única lectura honesta cuando las marcas no miden lo
    mismo."""
    return (pin["c1"] - pin["c0"] + 1) * len(
        _horas_entre(orden, pin["h0"], pin["h1"]))


def _firma(grano, claves, medida):
    """Firma del estado que define QUÉ MAPA es éste. Va en la `key` del chart.

    NO lleva las marcas, y ése es el punto: las marcas cambian con cada
    arrastre, y una key que cambia obliga a Streamlit a remontar el
    componente —Plotly repinta de cero y el mapa pestañea—. Lleva las cosas
    que cambian el mapa de verdad: la granularidad, cuántos/cuáles períodos
    y qué medida. Ahí el remonte SÍ es lo correcto: la selección vieja
    apunta a coordenadas de otro mapa.

    Para que la selección no se re-procese en bucle con la key quieta está
    la huella (`_K_SEL`, trampa 3 del docstring).

    Los paneles van TODOS, como un número (crc32 de su `repr`): desde que el
    rango los parte (regla #531) dos rangos distintos pueden coincidir en el
    primero y en cuántos son, y un `_Tramo` escrito tal cual metería
    espacios y paréntesis en la key."""
    return (f"{grano}_{len(claves)}_{_zlib.crc32(repr(claves).encode())}"
            f"_{medida}")


# ── Datos ───────────────────────────────────────────────────────────────────

def _prep_tramo(df, c, grano, ini, fin):
    """Filas de un tramo con lo que necesitan el mapa Y el drill.

    Se prepara UNA vez y se usa dos: agregando por (columna, hora) sale el
    mapa; recortando al rectángulo de una marca y agrupando por
    grupo/subgrupo/plato/tipo sale el árbol.

    El recorte por fecha se re-aplica en pandas aunque `cargar_rango` filtre en
    DuckDB, por el mismo motivo que en ventas_comparativo: en modo demo (sin
    secrets de R2) el loader devuelve el df entero."""
    if df is None or df.empty or c["fecha"] not in df.columns:
        return None
    fe = pd.to_datetime(df[c["fecha"]], errors="coerce")
    m = fe.notna() & (fe.dt.date >= ini) & (fe.dt.date <= fin)
    if not m.any():
        return None
    fe = fe[m]
    # La columna se cuenta desde `ini`, no desde el arranque del período: en
    # un `_Tramo` que empieza el 26, el 26 es la columna 0 (regla #531). En un
    # período entero `ini` ES el arranque y esto resta cero.
    _off = int(_columna_de_fecha(pd.Series([pd.Timestamp(ini)]), grano).iat[0])
    out = pd.DataFrame({
        "col":  (_columna_de_fecha(fe, grano) - _off).astype("int64").values,
        "hora": fe.dt.hour.astype("int64").values,
        # El día de semana y la fecha los usan las filas «Platos» y «Grupos»
        # (columnas por día de semana, y «Por día»), regla #530.
        "dow":  fe.dt.weekday.astype("int64").values,
        "dia":  fe.dt.normalize().values,
        "venta": pd.to_numeric(df.loc[m, c["venta"]],
                               errors="coerce").fillna(0.0).values,
    })
    for _id, _col in (("cant", "cant"), ("desc", "desc")):
        if c.get(_col) and c[_col] in df.columns:
            out[_id] = pd.to_numeric(df.loc[m, c[_col]],
                                     errors="coerce").fillna(0.0).values
        else:
            out[_id] = 0.0
    # Pax NO se suma línea a línea: `Cant Pax` se repite en cada línea del
    # pedido. Se guarda a nivel de fila y se deduplica por pedido al agregar
    # (mismo criterio que ventas_resumen y el comparativo).
    if c.get("pax") and c.get("pedido") \
            and c["pax"] in df.columns and c["pedido"] in df.columns:
        out["pax"] = pd.to_numeric(df.loc[m, c["pax"]], errors="coerce").values
        out["ped"] = df.loc[m, c["pedido"]].astype(str).values
        # El comprobante, para que la nota de crédito reste sin descontar a
        # la mesa que sí vino (`definicion_venta.pax_por`).
        _c_doc = dv.columna(df, dv.LLAVE_DOC)
        if _c_doc:
            out["doc"] = df.loc[m, _c_doc].astype(str).values
    for _id, _col in (("grupo", "fam"), ("sub", "sub"), ("prod", "prod")):
        if c.get(_col) and c[_col] in df.columns:
            out[_id] = df.loc[m, c[_col]].astype(str).values
    if c.get("tipo_desc") and c["tipo_desc"] in df.columns:
        # El `fillna` va ANTES del `astype(str)` y no es paranoia: desde
        # pandas 2.1 `astype(str)` PRESERVA los nulos en vez de escribir
        # "None", así que sin esto la línea sin descuento se quedaba con NaN
        # y en el árbol habría colgado de un nodo fantasma en vez de caer en
        # «Sin descuento» (lo cazó test_graficos.py al construirlo).
        _t = df.loc[m, c["tipo_desc"]]
        _t = _t.where(_t.notna(), "").astype(str).str.strip()
        out["tipo"] = _t.mask(_t.str.lower().isin(("", "nan", "none")),
                              _SIN_DSCTO).values
    else:
        out["tipo"] = _SIN_DSCTO
    return out


def _celdas(tramo):
    """Agregado por celda: (col, hora) → venta, cant, desc, pax."""
    if tramo is None or tramo.empty:
        return None
    agg = {"venta": ("venta", "sum"), "cant": ("cant", "sum"),
           "desc": ("desc", "sum")}
    g = tramo.groupby(["col", "hora"], as_index=False).agg(**agg)
    if "pax" in tramo.columns:
        _t = tramo.dropna(subset=["pax"])
        if not _t.empty:
            # Un valor por pedido y la nota de crédito resta (regla #524).
            _p = (dv.pax_por(_t, "ped", "pax",
                             doc="doc" if "doc" in _t.columns else None,
                             por=["col", "hora"])
                  .rename("pax").reset_index())
            g = g.merge(_p, on=["col", "hora"], how="left")
    if "pax" not in g.columns:
        g["pax"] = np.nan
    g["pax"] = g["pax"].fillna(0.0)
    # Ticket = venta/pax, la MISMA definición que ventas_resumen.py y el
    # comparativo. Sin pax no hay ticket (NaN), no un cero que se leería como
    # "mesas gratis".
    g["ticket"] = g["venta"] / g["pax"].replace(0, np.nan)
    # Lo que vendieron la Venta Interna y los Eventos en la celda: el mapa le
    # pone un triángulo y el tooltip lo dice (regla #536).
    if "grupo" in tramo.columns:
        _r = (tramo[tramo["grupo"].isin(_fh.GRUPOS_RAROS)]
              .groupby(["col", "hora"], as_index=False)["venta"].sum()
              .rename(columns={"venta": "raro"}))
        g = g.merge(_r, on=["col", "hora"], how="left")
    if "raro" not in g.columns:
        g["raro"] = 0.0
    g["raro"] = g["raro"].fillna(0.0)
    return g


def _filas_de_marca(tramo, pin, orden):
    """Filas del tramo que caen DENTRO del rectángulo de la marca.

    El corte de horas va por `isin` sobre el orden de servicio y no por
    `h0 <= hora <= h1`: ver `_horas_entre`."""
    horas = _horas_entre(orden, pin["h0"], pin["h1"])
    return tramo[(tramo["col"] >= pin["c0"]) & (tramo["col"] <= pin["c1"])
                 & (tramo["hora"].isin(horas))]


def _agregar_marca(tramo, pin, orden):
    """Totales de una marca sobre su tramo (venta, cant, desc, pax, ticket)."""
    if tramo is None or tramo.empty:
        return {}
    t = _filas_de_marca(tramo, pin, orden)
    if t.empty:
        return {"venta": 0.0, "cant": 0.0, "desc": 0.0, "pax": 0.0,
                "ticket": np.nan}
    out = {
        "venta": float(t["venta"].sum()),
        "cant":  float(t["cant"].sum()),
        "desc":  float(t["desc"].sum()),
    }
    if "pax" in t.columns:
        _t = t.dropna(subset=["pax"])
        out["pax"] = (dv.pax_por(_t, "ped", "pax",
                                 doc="doc" if "doc" in _t.columns else None)
                      if not _t.empty else 0.0)
    else:
        out["pax"] = 0.0
    out["ticket"] = (out["venta"] / out["pax"]) if out["pax"] else np.nan
    return out


def _detalle_marca(tramo, pin, orden):
    """Filas grupo/subgrupo/plato/tipo-de-descuento de una marca.

    El cuarto nivel (tipo) sale de `NOMBRE DESCUENTO`, que vive en la MISMA
    línea que el plato: relacionar un plato con el descuento que se le hizo no
    necesita ningún join. Las líneas sin descuento caen en «Sin descuento», y
    eso no es relleno: es la parte del plato que se vendió a precio de lista.
    """
    if tramo is None or tramo.empty or "prod" not in tramo.columns:
        return None
    t = _filas_de_marca(tramo, pin, orden)
    if t.empty:
        return None
    llaves = [k for k in ("grupo", "sub", "prod", "tipo") if k in t.columns]
    return t.groupby(llaves, as_index=False).agg(
        venta=("venta", "sum"), cant=("cant", "sum"), desc=("desc", "sum"))


# ── Figura ──────────────────────────────────────────────────────────────────

def _rango_x(total_columnas, ancho=None, ancho_max=None):
    """Rango del eje X: `[x0, x1]` en coordenadas de columna.

    Con muchas columnas es el rango justo. Con POCAS, el heatmap estiraría
    cada celda hasta llenar la tarjeta: medido el 2026-08-14, la semana en
    curso un martes son 2 columnas de 376px de ancho por 21 de alto — dos
    banderas, no un mapa. Y un lunes sería UNA celda de 740px.

    Así que la celda tiene un ancho máximo y el sobrante va TODO A LA
    DERECHA. La primera versión lo repartía a los dos lados para que el
    contenido quedara centrado, y eso metía un hueco enorme entre el eje de
    horas y la primera celda — 132px medidos con 11 columnas, reportado al
    toque. Además de feo era menos significativo: el hueco a la derecha ES
    el resto del período (agosto tiene 11 días cargados y el mes sigue),
    mientras que a la izquierda no quería decir nada."""
    ancho = _ANCHO_UTIL if ancho is None else ancho
    ancho_max = (_RATIO_MAX_CELDA * _PX_HORA) if ancho_max is None else ancho_max
    total = max(1, int(total_columnas))
    minimo = max(1, ancho // ancho_max)
    return [-0.5, max(total, minimo) - 0.5]


def _tick_marcado(texto, marca):
    """La etiqueta del eje X con su marca de fin de semana o feriado.

    Plotly acepta un subconjunto de HTML en `ticktext` (`<b>` y
    `<span style="color:…">`), así que la marca es tipográfica y no ocupa
    ni un pixel de más — importa, porque en granularidad Mes hay 31 de
    estas etiquetas en una franja de 10px de alto."""
    if marca == "feriado":
        return f'<span style="color:{ADVERTENCIA_TEXTO}"><b>{texto}</b></span>'
    if marca == "finde":
        return f'<span style="color:{TEXTO_PRINCIPAL}">{texto}</span>'
    return texto


def _alto_mapa(n_horas, con_drill=False, varios=False):
    """Alto de la figura. Sigue al NÚMERO DE FILAS y no al techo de la
    tarjeta: con un alto fijo, un turno de 8 horas repartía 373px entre 8
    filas y salían bandas de 46px de alto por 28 de ancho — más aire que dato.

    Con el drill abierto la fila se comprime (22px → 15) para que el mapa y
    el detalle entren en la MISMA pantalla. Es la pieza que evita que abrir
    un bloque empuje el gráfico fuera de la vista."""
    return alturas.por_filas(
        n_horas, px_fila=(_PX_HORA_DRILL if con_drill else _PX_HORA),
        extra=(_AIRE_MAPA if varios else _AIRE_MAPA_SOLO),
        rol=alturas.con_franja(), minimo=_ALTO_MIN)


def _paso_etiquetas(total_columnas, largo_etiqueta, ancho=None):
    """Cada cuántas columnas se escribe una etiqueta en el eje X, con el
    ancho de ESTE mapa (`_ANCHO_UTIL`) por defecto.

    El cálculo se mudó a `graficos.base.paso_etiquetas` el 2026-08-22: lo
    necesitaba también el drill de Proveedor y había que arreglarle un
    redondeo de más (ver su docstring y arquitectura.md #161). Acá queda
    sólo el default del ancho, que sí es propio de este módulo.

    Reemplaza a los umbrales por panel (`1 si n<=12, 2 si n<=16, si no 5`) que
    tenían el defecto de mirar UN panel: un mes en curso de 13 días saltaba
    un día de por medio con medio gráfico vacío al lado."""
    return paso_etiquetas(total_columnas, largo_etiqueta,
                          _ANCHO_UTIL if ancho is None else ancho)


def _fmt_delta(d, medida):
    """«+S/ 1,240», «−3», «+S/ 12.50»: la resta de una celda, con su signo."""
    s = "+" if d > 0 else "−" if d < 0 else ""
    a = abs(d)
    if medida in ("venta", "desc"):
        return f"{s}S/ {a:,.0f}"
    if medida == "ticket":
        return f"{s}S/ {a:,.2f}"
    return f"{s}{a:,.0f}"


def _heatmap_dif(z, x, y, **kw):
    """La capa de las RESTAS: rojo lo que bajó, verde lo que subió, blanco
    lo igual. La escala la pone el percentil 90 de las restas y no la
    mayor: un solo caso extremo dejaba todo lo demás casi blanco (medido
    en el mockup). Lo que pasa de ahí sale con el color entero."""
    v = np.abs(z[~np.isnan(z)])
    lim = float(np.percentile(v, 90)) if v.size else 1.0
    lim = lim or (float(v.max()) if v.size else 1.0) or 1.0
    return go.Heatmap(
        z=z, x=x, y=y, zmin=-lim, zmax=lim, zmid=0, hoverinfo="skip",
        colorscale=[[0.0, AJUSTE_NEG], [0.5, BLANCO], [1.0, AJUSTE_POS]],
        colorbar=dict(thickness=10, outlinewidth=0, len=0.42, y=0.22,
                      title=dict(text="Δ", font=dict(size=10)),
                      tickfont=dict(size=10, color=GRIS_TEXTO)), **kw)


def _fig_mapa(paneles, claves, grano, medida, marcas, horas, ancla=None,
              alto=None, dif=False, foco=None, raros=True):
    """Mapa de calor de los N paneles en una sola figura, con la capa de
    selección transparente encima y un rectángulo por marca.

    Los paneles se concatenan en el eje X con UNA columna de hueco entre
    ellos (NaN, que Plotly deja sin pintar): así el eje de horas es uno solo
    a la izquierda y comparar es barrer la vista, sin tener que emparejar
    cuatro ejes distintos.

    Con `dif` (regla #530) cada panel desde el segundo se pinta como su
    RESTA contra el primero, celda por celda —la misma columna y la misma
    hora—, en rojo y verde; el primero sigue en azul. Sólo tiene sentido con
    columnas que se corresponden, y por eso el llamador no la pide en Mes."""
    n_horas = len(horas)
    h_idx = {h: i for i, h in enumerate(horas)}
    # Eje Y CATEGÓRICO y no numérico: `horas` viene ordenado por día de
    # servicio (ver _orden_horas) y puede saltar de las 23h a las 00h. En un
    # eje numérico ese salto se dibuja como doce filas vacías; en uno
    # categórico las filas son las que hay, en el orden que se les dio.
    y_cat = [_etiqueta_hora(h) for h in horas]

    # Geometría PRIMERO, etiquetas después. El paso de las etiquetas ("una de
    # cada cuántas columnas se escribe") depende del ancho que le toca a cada
    # columna, y eso sale del total de columnas del gráfico ENTERO — no de las
    # que tenga un panel. Calcularlo por panel, como estaba hasta el
    # 2026-08-14, hacía que un solo mes de 13 días saltease un día de por
    # medio pese a que sobraba sitio (13 > 12 disparaba el paso 2), mientras
    # que cuatro meses de 31 (124 columnas de 6px) usaban el mismo paso 5 que
    # un mes suelto.
    geo = [_columnas(clave, grano, ancla) for clave in claves]

    # En granularidad Mes la etiqueta del eje lleva el MES pegado al día
    # ("1 Ago", no "1"): el mes sólo estaba en el título del panel, arriba de
    # todo, así que para saber de qué agosto hablaba una columna había que
    # levantar la vista y volver (pedido 2026-08-15). Sólo en Mes: en Semana
    # las columnas ya son "Lun/Mar/…" y en Año son los meses mismos.
    # NO se toca `_columnas`: sus etiquetas también arman el nombre de una
    # marca (`_etiqueta_columnas`), donde el mes ya viene por otro lado y
    # esto daría "días 7 Ago–8 Ago".
    def _rotulo(s, et):
        if grano != "Mes" or not et:
            return et
        return f"{et} {_MESES_ES[_base_clave(claves[s])[1] - 1]}"

    rotulos = [[_rotulo(s, e) for e in ets] for s, (_n, ets) in enumerate(geo)]
    total = sum(n for n, _e in geo) + max(0, len(geo) - 1)
    # El paso se mide sobre la etiqueta QUE SE VE, no sobre la cruda: "1 Ago"
    # ocupa el triple que "1" y con el largo viejo se solapaban.
    paso = _paso_etiquetas(
        total, max((len(e) for ets in rotulos for e in ets if e), default=1))

    # Fin de semana y feriado se marcan en la ETIQUETA del día, no con una
    # banda: el mapa ya usa el color para el dato, y una banda encima de las
    # celdas competiría con lo único que importa mirar. El feriado además se
    # escribe SIEMPRE aunque el paso lo saltease — es justo el día que uno
    # busca cuando una columna se sale de la norma.
    feriados = _feriados_de(claves, grano) if grano != "Año" else set()
    marcas_dia = {}          # posición del eje X → 'finde' | 'feriado'

    offs, ticks_pos, ticks_txt, titulos = [], [], [], []
    pos = 0
    for s, (n, etiquetas) in enumerate(geo):
        offs.append(pos)
        for i, et in enumerate(rotulos[s]):
            _m = _marca_dia(_fecha_de_columna(claves[s], grano, i), feriados)
            if _m:
                marcas_dia[pos + i] = _m
            if et and (i % paso == 0 or _m == "feriado"):
                ticks_pos.append(pos + i)
                ticks_txt.append(_tick_marcado(et, _m))
        titulos.append((pos + (n - 1) / 2, _etiqueta_clave(claves[s], grano)))
        pos += n + 1            # +1 = la columna de hueco
    total = max(total, 1)

    z = np.full((n_horas, total), np.nan)
    dif = dif and len(paneles) > 1
    z_dif = np.full((n_horas, total), np.nan)

    def _num(v):
        return 0.0 if v is None or pd.isna(v) else float(v)
    # La resta va por columna del CALENDARIO (la de la celda + lo que el
    # tramo deja a su izquierda, `_offset`): un panel que arranca el
    # miércoles resta su miércoles del miércoles de la base, no de su lunes.
    _off = [_offset(k, grano) for k in claves]
    base = ({(int(f.col) + _off[0], int(f.hora)):
             _num(getattr(f, medida, np.nan))
             for f in paneles[0].itertuples(index=False)}
            if dif and paneles[0] is not None and not paneles[0].empty else {})
    xs, ys, cd, dtxt, rtxt, raras = [], [], [], [], [], []
    _et_base = _etiqueta_clave(claves[0], grano) if claves else ""
    for s, celdas in enumerate(paneles):
        if celdas is None or celdas.empty:
            celdas = pd.DataFrame(columns=["col", "hora"])
        n, _et = _columnas(claves[s], grano, ancla)
        vistos = set()
        for fila in celdas.itertuples(index=False):
            if fila.hora not in h_idx or fila.col >= n:
                continue
            x = offs[s] + int(fila.col)
            valor = getattr(fila, medida, np.nan)
            _abs = (int(fila.col) + _off[s], int(fila.hora))
            vistos.add(_abs)
            # La Venta Interna y los Eventos de la celda (regla #536): un
            # triángulo en su esquina y una línea en el tooltip. Con el
            # interruptor apagado ya no están en el tramo y `raro` da 0.
            _raro = _num(getattr(fila, "raro", 0.0))
            if raros and _raro > 0.5:
                raras.append((x, h_idx[fila.hora]))
                rtxt.append(f'<br><span style="color:{ADVERTENCIA_TEXTO}">'
                            f"Incluye S/ {_raro:,.0f} de Venta Interna o "
                            "Eventos</span>")
            else:
                rtxt.append("")
            if dif and s > 0:
                _d = _num(valor) - base.get(_abs, 0.0)
                z_dif[h_idx[fila.hora], x] = _d
                dtxt.append(f"<br><b>Δ vs {_et_base}: "
                            f"{_fmt_delta(_d, medida)}</b>")
            else:
                z[h_idx[fila.hora], x] = valor
                dtxt.append("")
            xs.append(x)
            ys.append(y_cat[h_idx[fila.hora]])
            cd.append([s, int(fila.col), int(fila.hora),
                       float(fila.venta), float(fila.pax),
                       float(fila.cant), float(fila.desc),
                       float(fila.ticket) if pd.notna(fila.ticket) else 0.0])
        if dif and s > 0:
            for (col_a, hora), bv in base.items():
                _loc = col_a - _off[s]
                if (col_a, hora) not in vistos and 0 <= _loc < n \
                        and hora in h_idx and bv:
                    z_dif[h_idx[hora], offs[s] + _loc] = -bv

    fig = go.Figure()

    # BANDAS POR HORA (2026-08-14, pedido del usuario). Van DEBAJO de las
    # celdas, así que sólo se ven donde el heatmap no pinta — que es
    # justamente donde hacen falta: el mapa tiene muchas celdas vacías (una
    # hora sin ventas ese día) y sin nada detrás, seguir una hora a lo ancho
    # de cuatro paneles era saltar por huecos blancos. Una de cada dos filas
    # lleva un gris apenas perceptible, como el rayado de una planilla.
    # Las bandas llegan hasta el ÚLTIMO DÍA CON COLUMNA, no hasta el final
    # del rango. El rango puede ser más ancho (ver `_rango_x`: con pocas
    # columnas se reserva sitio para que la celda no se estire), y una banda
    # gris estirada sobre ese sobrante se lee como una fila de la tabla que
    # está vacía en vez de como espacio libre — fue justo lo que se reportó
    # el 2026-08-15 con un mes en curso de 13 días. Cruzar el hueco ENTRE
    # paneles sí es a propósito: seguir una hora de punta a punta es para lo
    # que se pidieron las bandas.
    _x0, _x1 = _rango_x(total)
    _x1 = min(_x1, offs[-1] + geo[-1][0] - 0.5) if geo else _x1
    for i in range(0, n_horas, 2):
        fig.add_shape(type="rect", x0=_x0, x1=_x1, y0=i - 0.5, y1=i + 0.5,
                      line=dict(width=0), fillcolor=GRIS_LINEA,
                      layer="below")

    fig.add_trace(go.Heatmap(
        z=z, x=list(range(total)), y=y_cat,
        colorscale=ESCALA_CONTINUA, hoverinfo="skip",
        # ygap 2 y no 1: el hueco entre filas ES el separador (el fondo se ve
        # a través), así que un píxel más de aire vertical convierte cada
        # hora en una franja legible sin dibujar una sola línea.
        xgap=1, ygap=2,
        colorbar=dict(thickness=10, outlinewidth=0,
                      len=0.42 if dif else 0.85, y=0.78 if dif else 0.5,
                      tickfont=dict(size=10, color=GRIS_TEXTO)),
    ))
    if dif:
        fig.add_trace(_heatmap_dif(z_dif, list(range(total)), y_cat,
                                   xgap=1, ygap=2))
    # CUADRÍCULA (2026-08-15, pedido: "una ligera cuadrícula para tener
    # referencia de la fecha y hora"). Las líneas caen en los BORDES de la
    # celda (i ± 0.5), nunca en su centro: ahí es donde el xgap/ygap del
    # heatmap ya deja 1-2px de junta, así que la línea entra en el hueco en
    # vez de partir un día por la mitad.
    #
    # POR QUÉ UN SHAPE Y NO LA GRILLA DEL EJE. Se probaron las dos:
    #   · La grilla MAYOR va en los ticks, o sea en el centro de la celda.
    #     Descartada de entrada.
    #   · La grilla MENOR (`minor=dict(tickvals=…)`) sí acepta los bordes,
    #     pero se dibuja en `minor-gridlayer`, que Plotly monta ANTES de
    #     `overplot`, y `layer="above traces"` (que mueve la mayor) no la
    #     alcanza. Verificado en el DOM: el <image> del heatmap quedaba
    #     encima y la cuadrícula sólo asomaba por las celdas vacías —
    #     justo al revés de lo que hace falta, porque lo que uno quiere
    #     rastrear hasta su día es la celda CARGADA.
    # Un shape con `layer="above"` sí queda encima de todo. Y va como UN
    # solo `type="path"` con muchos subtrazos en vez de una línea por corte:
    # cuatro meses comparados son ~180 segmentos, que como shapes sueltos
    # serían 180 objetos en el JSON de la figura.
    _rejilla = []
    for s, (n, _e) in enumerate(geo):
        _a, _b = offs[s] - 0.5, offs[s] + n - 0.5
        # Verticales: un corte por día, más los dos bordes del panel. El
        # hueco ENTRE paneles queda cerrado a ambos lados y sin líneas
        # dentro — cruzarlo sugeriría que ahí hay días.
        for i in range(n + 1):
            _rejilla.append(f"M{offs[s] + i - 0.5},-0.5"
                            f"L{offs[s] + i - 0.5},{n_horas - 0.5}")
        # Horizontales: sólo a lo ancho del panel, no del rango entero (a la
        # derecha sobra el resto del mes, que no tiene celdas que separar).
        for j in range(n_horas + 1):
            _rejilla.append(f"M{_a},{j - 0.5}L{_b},{j - 0.5}")
    if _rejilla:
        fig.add_shape(type="path", path="".join(_rejilla), layer="above",
                      line=dict(color=GRIS_CUADRICULA, width=1))

    # ── Capa de selección: TODAS las celdas, tengan venta o no ──────────
    # Va aparte de la capa de hover de abajo, y la diferencia importa.
    #
    # Hasta el 2026-08-15 sólo había puntos donde HABÍA datos, y eso tenía
    # dos consecuencias feas. La primera, visible: un arrastre sobre celdas
    # vacías no devolvía ningún punto, Streamlit no veía cambio, no había
    # rerun — y el rectángulo punteado de Plotly se quedaba dibujado para
    # siempre (reportado con captura, y reproducido después arrastrando 6px
    # en una esquina). La segunda, silenciosa: la marca se calcula como el
    # envolvente de los puntos tomados, así que si arrastrabas un rectángulo
    # con los bordes vacíos, la marca se encogía hasta el último día con
    # venta sin decir nada.
    #
    # Con un punto por celda las dos se van juntas: cualquier arrastre
    # dentro del mapa devuelve algo, y la marca es EXACTAMENTE lo que
    # encerraste. Que se pueda marcar una zona sin ventas no es un efecto
    # colateral: "el martes a las 4 pm no vendimos nada" es una respuesta.
    #
    # `hoverinfo="skip"` es lo que la mantiene invisible al pasar el cursor:
    # el hover con los números lo sigue dando la capa de datos.
    def _nombre_celda(s, col):
        """«Sep 26 · 5 · fin de semana»: el nombre de una celda en el hover."""
        _n, _et = _columnas(claves[s], grano, ancla)
        _c = _et[col] if col < len(_et) and _et[col] else ""
        _m = _marca_dia(_fecha_de_columna(claves[s], grano, col), feriados)
        return " · ".join(
            x for x in (_etiqueta_clave(claves[s], grano), _c,
                        {"feriado": "feriado",
                         "finde": "fin de semana"}.get(_m, "")) if x)

    _sx, _sy, _scd = [], [], []
    for s, (n, _e) in enumerate(geo):
        for c in range(n):
            for i, h in enumerate(horas):
                _sx.append(offs[s] + c)
                _sy.append(y_cat[i])
                _scd.append([s, c, int(h)])
    if _sx:
        fig.add_trace(go.Scatter(
            x=_sx, y=_sy, mode="markers",
            marker=dict(size=13, color="rgba(0,0,0,0)", line=dict(width=0)),
            customdata=_scd, showlegend=False, hoverinfo="skip",
        ))

    if xs:
        # Capa de HOVER: sólo las celdas con datos, y es la que lleva los
        # números. Un heatmap no emite eventos, así que el tooltip rico
        # (venta, pax, ticket, cantidad, descuento) tiene que colgar de un
        # scatter; en el heatmap sólo habría `z`.
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers",
            marker=dict(size=13, color="rgba(0,0,0,0)",
                        line=dict(width=0)),
            customdata=cd, showlegend=False,
            hovertemplate=(
                "<b>%{customdata[8]}</b> · %{y}<br>"
                "Venta: S/ %{customdata[3]:,.0f}<br>"
                "Pax: %{customdata[4]:,.0f} · "
                "Ticket: S/ %{customdata[7]:,.2f}<br>"
                "Cantidad: %{customdata[5]:,.0f} · "
                "Dscto: S/ %{customdata[6]:,.0f}%{customdata[9]}"
                "<extra></extra>"),
        ))
        # El nombre legible de cada punto (panel + columna) va como noveno
        # campo del customdata: armarlo acá evita que el hover tenga que
        # entender de calendarios. El décimo es la línea de Venta Interna y
        # Eventos, y el ÚLTIMO, la resta de «Diferencia» (test_graficos.py
        # la busca ahí).
        fig.data[-1].customdata = [
            c + [_nombre_celda(c[0], c[1]), rt, dt]
            for c, dt, rt in zip(cd, dtxt, rtxt)]
        if dif:
            fig.data[-1].hovertemplate = fig.data[-1].hovertemplate.replace(
                "<extra></extra>", "%{customdata[10]}<extra></extra>")

    # Capa de CLIC de las celdas VACÍAS (regla #536). El clic suelto viaja
    # por `plotly_click` (ver `_JS_CLIC_MAPA`), y Plotly lo emite sólo sobre
    # un punto con hover: la capa de selección lleva `"skip"` a propósito
    # (con hover le robaría el tooltip a la de datos, regla #388). Sin esta
    # capa, una hora sin ventas no abriría su ficha — y «no se vendió nada,
    # pero un martes normal sí» es una respuesta. Va DESPUÉS de la de datos:
    # test_graficos.py toma la primera capa con hover como la de los números.
    _con_dato = {(c[0], c[1], c[2]) for c in cd}
    _vx, _vy, _vcd = [], [], []
    for x_, y_, c_ in zip(_sx, _sy, _scd):
        if tuple(c_) not in _con_dato:
            _vx.append(x_)
            _vy.append(y_)
            _vcd.append(c_ + [_nombre_celda(c_[0], c_[1])])
    if _vx:
        fig.add_trace(go.Scatter(
            x=_vx, y=_vy, mode="markers",
            marker=dict(size=13, color="rgba(0,0,0,0)", line=dict(width=0)),
            customdata=_vcd, showlegend=False,
            hovertemplate="<b>%{customdata[3]}</b> · %{y}<br>Sin ventas"
                          "<extra></extra>"))

    # El triángulo de la Venta Interna y los Eventos, en la esquina de arriba
    # a la derecha de su celda (el eje de horas va invertido: `y - 0.5` es el
    # borde de ARRIBA). Un solo shape con un subtrazo por celda, como la
    # cuadrícula.
    if raras:
        fig.add_shape(
            type="path", layer="above", line=dict(width=0),
            fillcolor=ADVERTENCIA,
            path="".join(f"M{x + 0.5},{y - 0.5}L{x + 0.2},{y - 0.5}"
                         f"L{x + 0.5},{y - 0.05}Z" for x, y in raras))

    # La celda del clic, como la celda activa de una planilla: borde oscuro
    # y un filo blanco adentro. No es violeta a propósito: el violeta es de
    # las marcas del arrastre, y la ficha no es una marca.
    if foco and 0 <= foco.get("sel", -1) < len(geo) \
            and 0 <= foco.get("c", -1) < geo[foco["sel"]][0] \
            and foco.get("h") in h_idx:
        _xf, _yf = offs[foco["sel"]] + int(foco["c"]), h_idx[foco["h"]]
        fig.add_shape(type="rect", x0=_xf - 0.5, x1=_xf + 0.5,
                      y0=_yf - 0.5, y1=_yf + 0.5, layer="above",
                      line=dict(color=TEXTO_PRINCIPAL, width=2.5),
                      fillcolor="rgba(0,0,0,0)")
        fig.add_shape(type="rect", x0=_xf - 0.4, x1=_xf + 0.4,
                      y0=_yf - 0.36, y1=_yf + 0.36, layer="above",
                      line=dict(color=BLANCO, width=1),
                      fillcolor="rgba(0,0,0,0)")

    # El rótulo del panel se dibuja SÓLO si hay más de uno: con varios es lo
    # único que dice cuál banda es cuál, pero con uno solo repite el título de
    # la tarjeta y se lleva 24px de alto del gráfico. Con un panel, ese
    # nombre viaja al título (ver `_ventas_horario`).
    if len(claves) > 1:
        for s, (x, txt) in enumerate(titulos):
            if dif and s > 0:
                txt = f"{txt} − {_et_base}"
            fig.add_annotation(x=x, y=1.0, xref="x", yref="paper",
                               yanchor="bottom", showarrow=False, text=txt,
                               font=dict(size=12, color=TEXTO_PRINCIPAL))

    for i, pin in enumerate(marcas):
        if pin["sel"] >= len(claves):
            continue
        _hs = [h_idx[h] for h in _horas_entre(horas, pin["h0"], pin["h1"])
               if h in h_idx]
        if not _hs:
            continue
        x0 = offs[pin["sel"]] + pin["c0"] - 0.5
        x1 = offs[pin["sel"]] + pin["c1"] + 0.5
        # En un eje categórico las coordenadas numéricas son ÍNDICES de
        # categoría: 0 es el centro de la primera fila, así que ±0.5 son sus
        # bordes. Por eso el rectángulo se dibuja con posiciones y no con la
        # hora, que en este eje no significa nada.
        y0 = min(_hs) - 0.5
        y1 = max(_hs) + 0.5
        color = _COLOR_MARCA[i % len(_COLOR_MARCA)]
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(color=color, width=2), fillcolor="rgba(0,0,0,0)",
                      layer="above")
        fig.add_annotation(x=x0, y=y0, text=f" {i + 1} ", showarrow=False,
                           xanchor="left", yanchor="bottom",
                           font=dict(size=11, color="#ffffff"),
                           bgcolor=color, borderpad=1)

    fig.update_layout(
        # El alto SIGUE A LAS FILAS en vez de estirarse siempre al techo: con
        # `con_franja()` fijo, un turno de 8 horas repartía 373px entre 8
        # filas y salían bandas de 46px de alto por 28 de ancho — ladrillos
        # verticales con más aire que dato. `por_filas` clampea igual al
        # techo cuando hay muchas horas.
        height=alto or _alto_mapa(n_horas, varios=len(claves) > 1),
        # `t` reserva el sitio de los rótulos de panel; sin ellos el gráfico
        # sube esos 24px.
        # b=2: las etiquetas de día ya no llevan marca de tick, así que no
        # hay nada que separar del eje. Eran 10px de aire bajo los números.
        margin=dict(l=10, r=10, t=(34 if len(claves) > 1 else 10), b=2),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=12),
        dragmode="select",     # sin esto el arrastre hace zoom, no selección
        showlegend=False,
        # El rectángulo MIENTRAS se arrastra. El default de Plotly es un
        # punteado gris fino de herramienta de dibujo; acá el gesto es
        # "estoy eligiendo un rango de celdas", que es el de Excel, así que
        # se viste como tal: línea llena del color de acento y relleno
        # translúcido del mismo tono. El relleno lo pone `activeselection`
        # (`newselection` sólo sabe de la línea).
        newselection=dict(line=dict(color=ACENTO, width=1.5, dash="solid")),
        # Se ve un instante, entre que se suelta el botón y el rerun que
        # remonta el chart (ver `_K_GESTO`). Vale la pena igual: es el
        # acuse de recibo de que el rango quedó tomado.
        activeselection=dict(fillcolor=ACENTO, opacity=0.12),
    )
    # `fixedrange`: apaga el zoom y el paneo de los ejes. Plotly dibuja
    # alrededor del área del gráfico unas bandas invisibles para eso
    # (`ewdrag` bajo el eje X, `nsdrag` junto al Y, más sus esquinas
    # `wdrag`/`edrag`), y cada una cambia el cursor a flecha de
    # redimensionar. Acá sobran y además estorban: el único gesto de este
    # mapa es arrastrar para marcar un bloque, y agarrar tres píxeles por
    # debajo del eje movía el rango sin querer. Con esto desaparecen las
    # bandas y queda sólo `nsewdrag`, que es la que selecciona.
    fig.update_xaxes(fixedrange=True, ticks="", ticklen=0)
    fig.update_yaxes(fixedrange=True)
    fig.update_xaxes(tickvals=ticks_pos, ticktext=ticks_txt, showgrid=False,
                     zeroline=False, range=_rango_x(total),
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    # Horas de arriba hacia abajo: el turno empieza arriba y termina abajo,
    # como se lee un horario. `reversed` sobre un eje de categorías pone la
    # PRIMERA categoría arriba, que es justo el arranque del servicio.
    fig.update_yaxes(type="category", autorange="reversed",
                     showgrid=False, zeroline=False, showticklabels=True,
                     automargin=True, tickfont=dict(size=10, color=GRIS_TEXTO),
                     # Spike horizontal: al pasar el cursor por una celda, la
                     # FILA entera se marca de punta a punta. Es la tercera
                     # pata del pedido "ver la hora como una franja" — las
                     # bandas y el `ygap` ayudan a leer en reposo; el spike
                     # contesta "¿qué pasó a las 8 pm en todos los paneles?"
                     # sin tener que seguir el renglón con el dedo.
                     showspikes=True, spikemode="across", spikesnap="data",
                     spikethickness=1, spikedash="dot", spikecolor=ACENTO)
    return fig


def _puntos_de_evento(evt):
    """Tuplas `(panel, columna, hora)` de la selección de `st.plotly_chart`.

    Tolerante a formatos (objeto o dict) como `_first_point`, y a puntos sin
    customdata: los del heatmap no lo llevan y hay que ignorarlos en vez de
    reventar."""
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        pts = (sel or {}).get("points", []) or []
    except Exception:
        return []
    out = []
    for p in pts:
        cd = p.get("customdata") if isinstance(p, dict) else None
        if not cd or len(cd) < 3:
            continue
        out.append((cd[0], cd[1], cd[2]))
    return out


def _clic_de_evento(evt):
    """`(panel, columna, hora, sello)` si la selección es un CLIC traído por
    `_JS_CLIC_MAPA`, o None.

    Un clic llega como un solo punto con «clic» en su customdata y SIN caja;
    un arrastre, aunque sea sobre una sola celda, trae `box` y sigue armando
    marcas. El sello (la hora del clic en el navegador) es lo que hace que
    tocar dos veces la misma celda sean dos clics."""
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        sel = sel or {}
        if sel.get("box") or sel.get("lasso"):
            return None
        pts = sel.get("points", []) or []
    except Exception:
        return None
    for p in pts:
        cd = p.get("customdata") if isinstance(p, dict) else None
        if cd and len(cd) >= 5 and cd[3] == "clic":
            return int(cd[0]), int(cd[1]), int(cd[2]), cd[4]
    return None


# ── Filas «Platos» y «Grupos» (2026-09-25, regla #530) ──────────────────────
# El mismo mapa, con otra pregunta. «Días × horas» (el de siempre) mide la
# AFLUENCIA: cuánta gente llega y cuánto gasta, día por día y hora por hora.
# «Platos» y «Grupos» miden PREFERENCIAS: qué se pide y cuándo. Por eso Pax
# y Ticket no existen ahí —son del pedido, no del plato: una mesa de cuatro
# no le reparte «un pax» a cada plato— y el mapa cae a Venta y lo dice.

_FILAS = ("Días × horas", "Platos", "Grupos")
_COLS_FILAS = ("Por hora", "Por día de semana")
_HORA_OP = ("Hora del pedido", "Hora del cobro")
_LECTURAS = ("Lado a lado", "Diferencia")
_ESCALAS = ("Suma", "Por día")
_TOP_PLATOS = 20
_MED_FILAS = ("venta", "cant", "desc")
_NOCHE_DESDE = 18
_K_FICHA = "vh_ficha"
# Lo que ocupa la segunda fila de controles (la de «Filas», «Hora»…) con el
# gap de la tarjeta. Entra en la resta del panel de abajo (`vh-alto-arriba`).
_FILA_CONTROLES = 30


def _items_filas(tramos, que):
    """Las filas del mapa: los 20 platos que más vendieron en el período MÁS
    NUEVO de los elegidos, o todos los grupos por venta. Las mismas filas en
    todos los paneles: si no, «Diferencia» restaría platos distintos."""
    con = [x for x in tramos if x is not None and not x.empty
           and que in x.columns]
    if not con:
        return []
    if que == "prod":
        return (con[-1].groupby("prod")["venta"].sum()
                .nlargest(_TOP_PLATOS).index.tolist())
    return (pd.concat(con).groupby(que)["venta"].sum()
            .sort_values(ascending=False).index.tolist())


def _matriz_filas(tramo, que, items, por_hora, medida, horas, por_dia):
    """Filas × columnas de UN período: las horas (en orden de servicio) o
    los siete días de semana. Con `por_dia`, dividido por los días CON
    VENTA del período (o por cuántos lunes, martes… tuvo), para comparar un
    mes entero con uno en curso."""
    n_col = len(horas) if por_hora else 7
    m = np.zeros((len(items), n_col))
    if tramo is None or tramo.empty or que not in tramo.columns or not items:
        return m
    col = "hora" if por_hora else "dow"
    pos = {h: i for i, h in enumerate(horas)} if por_hora else None
    ix = {n: i for i, n in enumerate(items)}
    g = (tramo[tramo[que].isin(ix)]
         .groupby([que, col], as_index=False)[medida].sum())
    for f in g.itertuples(index=False):
        c = int(getattr(f, col))
        c = pos.get(c) if por_hora else c
        if c is not None:
            m[ix[getattr(f, que)], c] = float(getattr(f, medida))
    if por_dia:
        if por_hora:
            n = tramo["dia"].nunique()
            m = m / n if n else m
        else:
            cuenta = tramo.drop_duplicates("dia")["dow"].value_counts()
            den = np.array([cuenta.get(w, 0) for w in range(7)], dtype=float)
            m = np.divide(m, den, out=np.zeros_like(m), where=den > 0)
    return m


def _fmt_valor(v, medida, por_dia):
    etq = {"venta": "Venta", "cant": "Cantidad", "desc": "Descuento"}[medida]
    txt = (f"S/ {v:,.0f}" if medida in ("venta", "desc")
           else f"{v:,.1f}" if por_dia else f"{v:,.0f}")
    return f"{etq}: {txt}" + (" por día" if por_dia else "")


def _fig_filas(items, mats, etq_cols, claves, grano, medida, dif, foco,
               por_dia):
    """El mapa de «Platos»/«Grupos»: una fila por plato (o grupo), una
    columna por hora (o día de semana), un panel por período, concatenados
    como en `_fig_mapa`. Encima, la capa de hover y CLIC —un heatmap no
    emite eventos (trampa 1 del docstring)—, que abre la ficha de la fila."""
    n_it, n_c = len(items), len(etq_cols)
    dif = dif and len(mats) > 1
    offs = [s * (n_c + 1) for s in range(len(mats))]
    total = len(mats) * (n_c + 1) - 1
    z = np.full((n_it, total), np.nan)
    z_dif = np.full((n_it, total), np.nan)
    for s, m in enumerate(mats):
        for i in range(n_it):
            for c in range(n_c):
                v = m[i, c]
                if dif and s > 0:
                    z_dif[i, offs[s] + c] = v - mats[0][i, c]
                elif v:
                    z[i, offs[s] + c] = v
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=z, x=list(range(total)), y=items, colorscale=ESCALA_CONTINUA,
        hoverinfo="skip", xgap=1, ygap=2,
        colorbar=dict(thickness=10, outlinewidth=0,
                      len=0.42 if dif else 0.85, y=0.78 if dif else 0.5,
                      tickfont=dict(size=10, color=GRIS_TEXTO))))
    if dif:
        fig.add_trace(_heatmap_dif(z_dif, list(range(total)), items,
                                   xgap=1, ygap=2))
    _base = _etiqueta_clave(claves[0], grano)
    xs, ys, cd = [], [], []
    for s, m in enumerate(mats):
        per = _etiqueta_clave(claves[s], grano)
        for i, n in enumerate(items):
            for c in range(n_c):
                v = m[i, c]
                d = (f"<br><b>Δ vs {_base}: "
                     f"{_fmt_delta(v - mats[0][i, c], medida)}</b>"
                     if dif and s > 0 else "")
                xs.append(offs[s] + c)
                ys.append(n)
                cd.append([n, per, etq_cols[c],
                           _fmt_valor(v, medida, por_dia), d])
    # `hoverinfo` NO es «skip»: eso apaga también el clic (#388). La
    # etiqueta la da el hovertemplate.
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="markers", showlegend=False,
        marker=dict(size=13, color="rgba(0,0,0,0)", line=dict(width=0)),
        customdata=cd,
        hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]} · "
                       "%{customdata[2]}<br>%{customdata[3]}"
                       "%{customdata[4]}<extra></extra>")))
    paso = _paso_etiquetas(total, max(len(e) for e in etq_cols))
    tv, tt = [], []
    for s in range(len(mats)):
        for c in range(0, n_c, paso):
            tv.append(offs[s] + c)
            tt.append(etq_cols[c])
    if len(claves) > 1:
        for s in range(len(mats)):
            txt = _etiqueta_clave(claves[s], grano)
            if dif and s > 0:
                txt = f"{txt} − {_base}"
            fig.add_annotation(x=offs[s] + (n_c - 1) / 2, y=1.0, xref="x",
                               yref="paper", yanchor="bottom",
                               showarrow=False, text=txt,
                               font=dict(size=12, color=TEXTO_PRINCIPAL))
    if foco in items:
        i = items.index(foco)
        fig.add_shape(type="rect", x0=-0.5, x1=total - 0.5, y0=i - 0.5,
                      y1=i + 0.5, layer="above", fillcolor="rgba(0,0,0,0)",
                      line=dict(color=ACENTO, width=2))
    varios = len(claves) > 1
    fig.update_layout(
        height=alturas.por_filas(
            n_it, px_fila=_PX_HORA, rol=alturas.PROTAGONISTA,
            extra=(_AIRE_MAPA if varios else _AIRE_MAPA_SOLO),
            minimo=_ALTO_MIN),
        margin=dict(l=10, r=10, t=(34 if varios else 10), b=2),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL,
                  size=12),
        # MODO CLIC (#388): con «select» un clic suelto no selecciona nada.
        dragmode="pan", showlegend=False)
    fig.update_xaxes(fixedrange=True, ticks="", tickvals=tv, ticktext=tt,
                     showgrid=False, zeroline=False,
                     range=[-0.5, total - 0.5],
                     tickfont=dict(size=10, color=GRIS_TEXTO))
    fig.update_yaxes(type="category", autorange="reversed", fixedrange=True,
                     showgrid=False, zeroline=False, automargin=True,
                     tickfont=dict(size=10.5, color=TEXTO_PRINCIPAL))
    return fig


def _punto_fila(evt):
    """El nombre de la fila (plato o grupo) de un clic en `_fig_filas`."""
    p = _first_point(evt)
    cd = p.get("customdata") if isinstance(p, dict) else None
    return cd[0] if cd else None


def _clic_filas(base_key):
    """El clic de la corrida anterior, leído ANTES de dibujar y con un
    contador en la key (regla #399): la ficha tiene que abrir en la MISMA
    corrida que el clic, y el mapa se dibuja con la key nueva."""
    n = st.session_state.get(f"_{base_key}_n", 0)
    nombre = _punto_fila(st.session_state.get(f"{base_key}_{n}"))
    if nombre is not None:
        st.session_state[f"_{base_key}_n"] = n + 1
        st.session_state[_K_FICHA] = (
            None if st.session_state.get(_K_FICHA) == nombre else nombre)
    return f"{base_key}_{st.session_state.get(f'_{base_key}_n', 0)}"


def _a_dias_horas():
    """El atajo del aviso de Pax y Ticket: los lleva a donde sí existen."""
    st.session_state["vh_op_filas"] = _FILAS[0]


def _ficha_filas(tramos, claves, grano, que, nombre, medida, horas):
    """La ficha de una fila de «Platos»/«Grupos»: en cada período, cuánto,
    cuánto por día, su puesto, su hora pico, cuánto vende de noche y de
    viernes a domingo; y su curva por hora y por día de semana."""
    etq = {"venta": "venta", "cant": "unidades", "desc": "descuento"}[medida]
    st.markdown(
        f'<p class="vh-ficha-tit"><b>{nombre}</b> · {etq} en cada período '
        f'elegido</p>', unsafe_allow_html=True)
    filas, curvas, semanas = [], [], []
    for s, (k, tr) in enumerate(zip(claves, tramos)):
        per = _etiqueta_clave(k, grano)
        if tr is None or tr.empty or que not in tr.columns:
            continue
        x = tr[tr[que] == nombre]
        n_dias = tr["dia"].nunique() or 1
        tot = float(x[medida].sum())
        ph = x.groupby("hora")[medida].sum().reindex(horas, fill_value=0.0)
        pw = x.groupby("dow")[medida].sum().reindex(range(7), fill_value=0.0)
        cuenta = tr.drop_duplicates("dia")["dow"].value_counts()
        den = np.array([cuenta.get(w, 0) for w in range(7)], dtype=float)
        puesto = "—"
        if tot:
            _rk = tr.groupby(que)["venta"].sum().rank(ascending=False,
                                                      method="min")
            puesto = f"#{int(_rk.get(nombre))}" if nombre in _rk else "—"
        noche = (float(ph[[h for h in horas if h >= _NOCHE_DESDE or h < 6]]
                       .sum()) / tot if tot else 0.0)
        finde = float(pw[[4, 5, 6]].sum()) / tot if tot else 0.0
        pico = _etiqueta_hora(int(ph.idxmax())) if tot else "—"
        _v = (lambda v: f"S/ {v:,.0f}") if medida != "cant" else (
            lambda v: f"{v:,.0f}")
        filas.append({"Período": per, "Total": _v(tot),
                      "Por día": _v(tot / n_dias), "Puesto": puesto,
                      "Pico": pico, "Noche (6 pm+)": f"{noche:.0%}",
                      "Vie–Dom": f"{finde:.0%}"})
        color = _COLOR_MARCA[s % len(_COLOR_MARCA)]
        curvas.append(go.Scatter(
            x=[_etiqueta_hora(h) for h in horas], y=ph.values / n_dias,
            mode="lines+markers", name=per, line=dict(color=color, width=2),
            marker=dict(size=5),
            hovertemplate=f"{per} · %{{x}}<br>%{{y:,.0f}} por día"
                          "<extra></extra>"))
        semanas.append(go.Bar(
            x=list(_DIAS_ES), y=np.divide(pw.values, den,
                                          out=np.zeros(7), where=den > 0),
            name=per, marker=dict(color=color),
            hovertemplate=f"{per} · %{{x}}<br>%{{y:,.0f}} por día"
                          "<extra></extra>"))
    if not filas:
        st.caption("Sin ventas de esa fila en los períodos elegidos.")
        return
    st.dataframe(pd.DataFrame(filas), hide_index=True, row_height=27,
                 height=alturas.por_filas(len(filas), px_fila=27, extra=40,
                                          rol=alturas.MINI, minimo=70))
    # columnas-internas: la curva por hora y la de día de semana
    c1, c2 = st.columns([1.6, 1], gap="small")
    for col, trazas, titulo in ((c1, curvas, "Por hora · promedio por día"),
                                (c2, semanas, "Por día de semana · "
                                              "promedio")):
        with col:
            f = go.Figure(trazas)
            _compras_layout_min(f, titulo)
            st.plotly_chart(f, key=f"vh_ficha_{titulo[:9]}",
                            config={"displaylogo": False,
                                    "displayModeBar": False})


def _compras_layout_min(fig, titulo):
    """El layout de los dos mini gráficos de la ficha."""
    fig.update_layout(
        height=alturas.MINI, margin=dict(l=10, r=10, t=26, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL,
                  size=11),
        showlegend=False, barmode="group", bargap=0.25, dragmode=False,
        title=dict(text=titulo, font=dict(size=12), x=0, xanchor="left"))
    fig.update_xaxes(fixedrange=True, type="category",
                     tickfont=dict(size=9.5, color=GRIS_TEXTO))
    fig.update_yaxes(fixedrange=True, gridcolor=GRIS_CUADRICULA,
                     tickfont=dict(size=9.5, color=GRIS_TEXTO),
                     tickformat=",.0f")


# ── UI: selector de períodos ────────────────────────────────────────────────

def _toggle_selector():
    st.session_state[_K_SELECTOR] = not st.session_state.get(_K_SELECTOR, False)


def _boton_selector(n_extras):
    """Sólo el botón que abre/cierra «Comparar». Va en la franja, en su
    columna angosta.

    Está separado del PANEL a propósito: el panel es una grilla de cinco
    columnas y dibujarlo dentro de esta columna —168px medidos— le daba 30px
    a cada botón, así que "Ago 26" salía partido letra por letra, en
    vertical. El panel se dibuja a lo ancho de la tarjeta con
    `_panel_comparar`.

    Cuenta sólo los períodos SUELTOS: los del rango ya los dice el selector
    de fecha de al lado (regla #531)."""
    st.button("Comparar" + (f" · {n_extras}" if n_extras else ""),
              key="vh_btn_selector", on_click=_toggle_selector,
              icon=(":material/keyboard_arrow_up:"
                    if st.session_state.get(_K_SELECTOR) else
                    ":material/keyboard_arrow_down:"))


def _ano_pasado(k, grano):
    """El mismo panel un año antes. En Día y Semana, 364 días atrás —el mismo
    día de SEMANA, que es lo que se compara en un restaurante y lo que
    alinea las columnas Lun…Dom—; en Mes y Año, la misma fecha del
    calendario, que es lo que alinea las columnas 1…31 y Ene…Dic. Un
    `_Tramo` se mueve entero: del 26 al 31 de agosto contra lo mismo del año
    anterior, no contra agosto entero."""
    def _mover(f):
        if grano in ("Día", "Semana"):
            return f - _dt.timedelta(days=364)
        try:
            return f.replace(year=f.year - 1)
        except ValueError:          # 29 de febrero
            return f.replace(year=f.year - 1, day=28)
    if isinstance(k, _Tramo):
        d0, d1 = _mover(k.desde), _mover(k.hasta)
        return _Tramo(_clave_de_fecha(d0, grano), d0, d1)
    return _clave_de_fecha(_mover(_rango_de_clave(k, grano)[0]), grano)


def _poner_extras(nuevos, grano):
    """Guarda los períodos sueltos, en orden cronológico, y re-corre la
    tarjeta. Las marcas NO se limpian acá: lo hace `_ventas_horario` cada
    vez que cambian los paneles, venga el cambio de donde venga."""
    st.session_state[_K_EXTRAS] = sorted(
        nuevos, key=lambda x: _rango_de_clave(x, grano)[0])
    st.rerun(scope="fragment")


def _panel_comparar(ancla, grano, del_rango, extras):
    """«Comparar»: períodos SUELTOS que se suman a los del rango (regla
    #531). Se dibuja FUERA de las columnas de la franja, a lo ancho de la
    tarjeta (ver `_boton_selector`).

    Hasta el 2026-09-25 esto elegía TODOS los paneles; desde que la vista
    tiene selector de fecha propio, los paneles salen del rango partido por
    la granularidad y acá queda lo que un rango no puede decir: «y además
    el mismo mes del año pasado». Por eso los dos atajos son «Año pasado» y
    «Período anterior», y la lista no ofrece lo que el rango ya muestra.

    NO usa `st.popover`: el patrón manual (botón + `session_state` + contenido
    en flujo) es el que ya eligió este proyecto para el panel "Detalle" del
    comparativo, y por el mismo motivo — acá además cada clic dispara un
    rerun, y un popover que se cierra en cada clic obligaría a reabrirlo
    para cada período.

    Los períodos NO tienen que ser consecutivos ni recientes: la lista es el
    atajo para lo de siempre y el `date_input` de abajo abre el calendario
    entero (pedido del usuario 2026-08-14, "elegir días o meses de manera
    aleatoria")."""
    if not st.session_state.get(_K_SELECTOR):
        return
    en_rango = {_base_clave(k) for k in del_rango}
    libres = MAX_MARCAS - len(del_rango)
    lleno = len(extras) >= libres
    # Los elegidos van SIEMPRE en la lista aunque caigan fuera de la ventana
    # reciente: si no, un mes de hace un año se quedaba seleccionado y sin
    # botón con el cual sacarlo.
    disponibles = sorted(
        {k for k in _claves_hacia_atras(ancla, grano, _N_LISTA[grano])
         if k not in en_rango} | set(extras),
        key=lambda k: _rango_de_clave(k, grano)[0], reverse=True)

    with st.container(key="vh_selector_panel"):
        _c1, _c2, _c3 = st.columns([1, 1.2, 3.8])
        with _c1:
            # Uno por panel del rango, mientras quepan.
            _ap = [x for x in (_ano_pasado(k, grano) for k in del_rango)
                   if x not in extras
                   and _base_clave(x) not in en_rango][:max(0, libres
                                                           - len(extras))]
            if st.button("Año pasado", key="vh_preset_ap",
                         use_container_width=True, disabled=not _ap,
                         help="Suma los mismos períodos un año antes: en Día "
                              "y Semana, el mismo día de la semana."):
                _poner_extras(list(extras) + _ap, grano)
        with _c2:
            _prev = (_clave_de_fecha(
                _rango_de_clave(_base_clave(del_rango[0]), grano)[0]
                - _dt.timedelta(days=1), grano) if del_rango else None)
            if st.button("Período anterior", key="vh_preset_ant",
                         use_container_width=True,
                         disabled=(_prev is None or lleno or _prev in extras)):
                _poner_extras(list(extras) + [_prev], grano)

        cols = st.columns(5)
        for i, k in enumerate(disponibles):
            on = k in extras
            with cols[i % 5]:
                if st.button(("✓ " if on else "") + _etiqueta_clave(k, grano),
                             key=f"vh_per_{grano}_{i}",
                             use_container_width=True,
                             type="primary" if on else "secondary",
                             disabled=(not on and lleno)):
                    _poner_extras([x for x in extras if x != k] if on
                                  else list(extras) + [k], grano)
        # ── Cualquier fecha, no sólo las recientes ──────────────────────
        # La lista de arriba cubre el 90% ("las últimas semanas"), pero deja
        # fuera "quiero ver el 14 de febrero". El date_input traduce la fecha
        # al período de la granularidad activa: en Mes, cualquier día de
        # febrero agrega febrero.
        _f1, _f2 = st.columns([2, 1])
        with _f1:
            _fecha = st.date_input(
                "Otra fecha", value=None, max_value=ancla, format="DD/MM/YYYY",
                key=f"vh_otra_{grano}", label_visibility="collapsed")
        with _f2:
            _agregar = st.button("Agregar", key=f"vh_add_{grano}",
                                 use_container_width=True, disabled=lleno)
        if _agregar:
            if _fecha is None:
                st.warning("Elegí una fecha primero.")
            else:
                _k = _clave_de_fecha(_fecha, grano)
                if _k in en_rango or _k in extras:
                    st.info(f"{_etiqueta_clave(_k, grano)} ya está en el "
                            "mapa.")
                else:
                    _poner_extras(list(extras) + [_k], grano)
        st.caption(
            (f"Ya hay {MAX_MARCAS} paneles: quitá uno para sumar otro. "
             if lleno else "")
            + "Suma períodos sueltos a los del rango de fechas —el mismo mes "
            "del año pasado, uno de hace meses—. Para uno que no esté en la "
            "lista, elegí cualquier fecha suya arriba.")


# ── UI: drill ───────────────────────────────────────────────────────────────

def _cerrar_foco():
    """El botón «Cerrar» de la ficha de la hora. Corre antes del rerun, así
    que la ficha ya no se dibuja en esa misma pasada."""
    st.session_state.pop(_K_FOCO, None)


def _ficha_de_la_hora(foco, claves, grano, ancla, filtrar_cb, raros, horas,
                      paneles, modo, cfh):
    """Trae de R2 la ventana del panel de la celda —el panel y sus 8 semanas
    anteriores, `ventas_ficha_hora.ventana`— filtrada como el mapa, y dibuja
    la ficha (regla #536). La cabecera repite la venta y el pax de la celda
    tal como los pintó el mapa, para que no difiera del tooltip."""
    k = claves[foco["sel"]]
    dia = _fecha_de_columna(k, grano, foco["c"])
    if dia is None:
        st.caption("La ficha es de un día, y en «Año» cada columna es un mes "
                   "entero: elegí Día, Semana o Mes para abrirla.")
        return
    ini, fin = _rango_de_clave(k, grano)
    ini_v, fin_v = _fh.ventana(ini, min(fin, ancla))
    cfg = REPORTES.get("Ventas", {})
    with st.spinner("Armando la ficha de la hora…"):
        df = cargar_rango(cfg.get("archivo", "ventas.parquet"),
                          cfg.get("carga_por_rango", "FEC REG DOCUMENTO"),
                          ini_v, fin_v)
        if df is not None and not df.empty and filtrar_cb is not None:
            df = filtrar_cb(df)
        if not raros and df is not None and cfh.get("grupo") in df.columns:
            df = df[~df[cfh["grupo"]].isin(_fh.GRUPOS_RAROS)]
        fl = _fh.filas(df, cfh)
    if fl is None or fl.empty:
        st.caption("Sin ventas cargadas alrededor de esta hora.")
        return
    celda = None
    p = paneles[foco["sel"]] if foco["sel"] < len(paneles) else None
    if p is not None and not p.empty:
        r = p[(p["col"] == foco["c"]) & (p["hora"] == foco["h"])]
        celda = ((float(r["venta"].sum()), float(r["pax"].sum()))
                 if len(r) else (0.0, 0.0))
    _fh.dibujar(dia, foco["h"], fl, horas, modo=modo, celda=celda,
                al_cerrar=_cerrar_foco)


def _tabla_medidas(marcas, tramos, claves, grano, orden, medidas, ver_var):
    """Pivote marca × medida. Una fila por marca (así la tabla es ordenable y
    no crece a lo ancho con cada marca nueva) y una columna por medida activa,
    con su Δ contra la marca base al lado si el toggle está puesto.

    Cuando las marcas NO encierran el mismo número de celdas aparece la
    columna «Venta/celda». Hasta el 2026-08-15 aparecía además un aviso
    debajo de la tabla explicándolo; se quitó a pedido. La columna es el
    aviso: sale sólo en ese caso y es la comparación honesta —un rectángulo
    de 12 celdas le gana siempre por total a uno de 3.
    """
    filas, celdas = [], []
    for i, pin in enumerate(marcas):
        tot = _agregar_marca(tramos[pin["sel"]], pin, orden)
        tot["celdas"] = _celdas_de_marca(pin, orden)
        tot["venta_celda"] = (tot.get("venta", 0.0) / tot["celdas"]
                              if tot["celdas"] else np.nan)
        _d = tot.get("desc", 0.0)
        _v = tot.get("venta", 0.0)
        tot["pct_desc"] = (100 * _d / (_v + _d)) if (_v + _d) else np.nan
        filas.append(f"{i + 1} · {_etiqueta_marca(pin, claves, grano)}")
        celdas.append(tot)

    base = celdas[0] if celdas else {}
    datos = {}
    for mid, lab in _MEDIDAS:
        if mid not in medidas:
            continue
        datos[lab] = [c.get(mid, np.nan) for c in celdas]
        if ver_var:
            _b = base.get(mid)
            datos[f"Δ {lab}"] = [
                (100 * (c.get(mid, np.nan) - _b) / _b)
                if (_b not in (None, 0) and pd.notna(_b)
                    and pd.notna(c.get(mid, np.nan))) else np.nan
                for c in celdas]
        if mid == "desc":
            datos["% lista"] = [c.get("pct_desc", np.nan) for c in celdas]
    datos["Celdas"] = [c.get("celdas", 0) for c in celdas]
    mismo = len({c.get("celdas") for c in celdas}) <= 1
    if not mismo:
        datos["Venta/celda"] = [c.get("venta_celda", np.nan) for c in celdas]

    tv = pd.DataFrame(datos, index=filas)
    fmt = {}
    for mid, lab in _MEDIDAS:
        if lab in tv.columns:
            fmt[lab] = _MED_FMT[mid]
        if f"Δ {lab}" in tv.columns:
            fmt[f"Δ {lab}"] = "{:+.0f}%"
    fmt.update({"% lista": "{:.1f}%", "Celdas": "{:,.0f}",
                "Venta/celda": "S/ {:,.0f}"})
    fmt = {k: v for k, v in fmt.items() if k in tv.columns}

    def _sty_var(v):
        if pd.isna(v):
            return f"color:{GRIS_TEXTO}"
        return f"color:{EXITO}" if v >= 0 else f"color:{ERROR}"

    _cols_var = [c for c in tv.columns if c.startswith("Δ ")]
    sty = tv.style.format(fmt, na_rep="—")
    if _cols_var:
        sty = sty.map(_sty_var, subset=_cols_var)
    st.dataframe(sty, use_container_width=True,
                 height=alturas.por_filas(len(tv), px_fila=35, extra=48,
                                          minimo=0, rol=alturas.MINI))


def _tabla_arbol(marcas, tramos, claves, grano, orden, medidas_arbol,
                 expandir=False, colapsar=False):
    """Árbol Grupo › Sub Grupo › Plato › Tipo de descuento, una columna por
    marca y medida.

    AgGrid y no HTML: el agrupamiento con expandir/colapsar la grilla lo da
    hecho, y reimplementarlo a mano sería reescribir gratis lo que ya trae. El tinte va por `cellStyle`, NUNCA por
    `cellRenderer` devolviendo HTML — acá eso se ve como texto escapado
    (arquitectura.md regla #25)."""
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode  # noqa: E402

    detalles = [_detalle_marca(tramos[p["sel"]], p, orden) for p in marcas]
    if all(d is None or d.empty for d in detalles):
        st.info("Sin ventas de productos en las marcas elegidas.")
        return

    llaves = ["grupo", "sub", "prod", "tipo"]
    wide = None
    for i, det in enumerate(detalles):
        if det is None or det.empty:
            continue
        _ll = [k for k in llaves if k in det.columns]
        d2 = det.rename(columns={m: f"{m}_{i}" for m in _MED_ARBOL})
        wide = d2 if wide is None else wide.merge(d2, on=_ll, how="outer")
    if wide is None or wide.empty:
        st.info("Sin ventas de productos en las marcas elegidas.")
        return
    for k in llaves:
        if k not in wide.columns:
            wide[k] = "—"
        wide[k] = wide[k].fillna("—")
    for i in range(len(marcas)):
        for m in _MED_ARBOL:
            col = f"{m}_{i}"
            if col not in wide.columns:
                wide[col] = 0.0
            wide[col] = pd.to_numeric(wide[col], errors="coerce").fillna(0.0)

    activas = [m for m in _MED_ARBOL if m in medidas_arbol] or ["venta"]
    recortado = len(marcas) * len(activas) > _MAX_COLS_ARBOL
    if recortado:
        activas = activas[:1]

    gb = GridOptionsBuilder.from_dataframe(wide)
    gb.configure_default_column(resizable=True, sortable=False, filter=False,
                                suppressMenu=True)
    gb.configure_column("grupo", header_name="Grupo", rowGroup=True, hide=True)
    gb.configure_column("sub", header_name="Sub Grupo", rowGroup=True, hide=True)
    gb.configure_column("prod", header_name="Plato", rowGroup=True, hide=True)
    gb.configure_column("tipo", header_name="Descuento", hide=True)

    fmt_soles = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '';
          return 'S/ '+Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:0});}
    """)
    fmt_num = JsCode("""
        function(p){ if(p.value==null||isNaN(p.value))return '';
          return Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:0});}
    """)

    # rgb del acento, calculado desde tema.py y no escrito a mano: la regla
    # «nunca un #hex suelto» vale también dentro de un blob de JS.
    _rgb = ",".join(str(int(ACENTO.lstrip("#")[i:i + 2], 16))
                    for i in (0, 2, 4))

    def _heat_fila(campos):
        """Tinte que compara la FILA entre marcas (no la columna entre filas):
        la pregunta del árbol es «este plato, ¿cómo le fue en cada marca?».
        `aggData` es lo que traen las filas de grupo — sin ese fallback, los
        niveles agrupados salen sin tinte."""
        _f = "[" + ",".join(f"'{c}'" for c in campos) + "]"
        return JsCode(f"""
            function(p){{
              var f={_f};
              var d=p.data||(p.node&&p.node.aggData)||{{}};
              var mx=0;
              for(var i=0;i<f.length;i++){{
                var v=Number(d[f[i]]||0); if(v>mx)mx=v;
              }}
              var v=Number(p.value||0);
              if(!(mx>0)||!(v>0))return null;
              var q=v/mx;
              var a=q>=0.999?0.26:(q>=0.66?0.17:(q>=0.33?0.10:0.05));
              return {{backgroundColor:'rgba({_rgb},'+a+')'}};
            }}
        """)

    columnDefs = []
    for i, pin in enumerate(marcas):
        hijos = []
        for m in activas:
            campos = [f"{m}_{j}" for j in range(len(marcas))]
            hijos.append({
                "field": f"{m}_{i}",
                "headerName": {"venta": "Venta", "cant": "Cant",
                               "desc": "Dscto"}[m],
                "type": "numericColumn", "width": 108, "aggFunc": "sum",
                "valueFormatter": fmt_num if m == "cant" else fmt_soles,
                "cellStyle": _heat_fila(campos),
            })
        columnDefs.append({
            "headerName": f"{i + 1} · {_etiqueta_marca(pin, claves, grano)}",
            "children": hijos,
        })

    opciones = gb.build()
    _base_defs = [c for c in opciones.get("columnDefs", [])
                  if c.get("field") in llaves]
    opciones["columnDefs"] = _base_defs + columnDefs
    opciones["groupDisplayType"] = "singleColumn"
    opciones["groupDefaultExpanded"] = 1
    opciones["animateRows"] = True
    opciones["suppressAggFuncInHeader"] = True
    opciones["autoGroupColumnDef"] = {
        "headerName": "Grupo / Sub Grupo / Plato / Descuento",
        "field": "tipo", "pinned": "left", "minWidth": 300,
        "cellRendererParams": {"suppressCount": False},
    }

    if expandir:
        opciones["groupDefaultExpanded"] = -1
    elif colapsar:
        opciones["groupDefaultExpanded"] = 0

    AgGrid(wide, gridOptions=opciones, allow_unsafe_jscode=True,
           theme="streamlit", height=alturas.PROTAGONISTA,
           enable_enterprise_modules=True,
           key=f"vh_arbol_{len(marcas)}_{'_'.join(activas)}",
           reload_data=False)
    st.caption(
        ("Sólo se muestra la primera medida: con "
         f"{len(marcas)} marcas, más de una no entra a lo ancho. "
         if recortado else "")
        + "El último nivel es el tipo de descuento aplicado a ese plato "
        "(«Sin descuento» = lo que se vendió a precio de lista). El tinte "
        "compara cada fila ENTRE marcas.")


def _dibujar_filas(tramos, claves, grano, medida, filas, cols_filas, lectura,
                   escala, horas):
    """El mapa de «Platos» o «Grupos». Devuelve el alto de la figura, que
    entra en la resta del panel de abajo."""
    que = "prod" if filas == "Platos" else "grupo"
    if medida not in _MED_FILAS:
        # PAX Y TICKET SON DEL PEDIDO (regla #530): no se apagan en
        # silencio, se dice por qué y se ofrece el camino a donde sí están.
        # columnas-internas: el aviso y su atajo
        _a, _b = st.columns([3.2, 1], vertical_alignment="center")
        with _a:
            st.caption(f"{_MED_LABEL[medida]} es del pedido, no del "
                       f"{'plato' if que == 'prod' else 'grupo'}: una mesa "
                       "de cuatro no le reparte un pax a cada plato. El mapa "
                       "muestra la venta.")
        with _b:
            st.button("Ver en Días × horas", key="vh_btn_a_dias",
                      on_click=_a_dias_horas, use_container_width=True)
        medida = "venta"
    items = _items_filas(tramos, que)
    if not items:
        st.info("Sin ventas con plato en los períodos elegidos.")
        return _ALTO_MIN
    por_hora = cols_filas == _COLS_FILAS[0]
    por_dia = escala == _ESCALAS[1]
    mats = [_matriz_filas(x, que, items, por_hora, medida, horas, por_dia)
            for x in tramos]
    etq = ([_etiqueta_hora(h) for h in horas] if por_hora
           else list(_DIAS_ES))
    dif = lectura == _LECTURAS[1] and len(claves) > 1
    if lectura == _LECTURAS[1] and len(claves) < 2:
        st.caption("La diferencia pide otro panel: ampliá el rango de "
                   "fechas o sumá uno en «Comparar».")
    elif dif and not por_dia:
        st.caption("En «Suma», un período en curso sale rojo aunque nada haya "
                   "cambiado: «Por día» lo compara parejo.")
    key = _clic_filas(f"vh_filas_g_{que}_{grano}")
    fig = _fig_filas(items, mats, etq, claves, grano, medida, dif,
                     st.session_state.get(_K_FICHA), por_dia)
    st.plotly_chart(fig, key=key, on_select="rerun", selection_mode="points",
                    config={"displaylogo": False, "displayModeBar": False})
    return int(fig.layout.height)


# ── Vista ───────────────────────────────────────────────────────────────────

@st.fragment
def _ventas_horario(d, col_venta, col_fecha, col_pax=None, col_pedido=None,
                    col_prod=None, col_cant=None, col_fam=None, col_sub=None,
                    filtrar_cb=None):
    """Mapa de calor día × hora de hasta 4 períodos, con marcas y drill."""
    if not (col_venta and col_fecha):
        st.info("Faltan columnas (Venta, Fecha) para el mapa por hora.")
        return

    _fe = pd.to_datetime(d[col_fecha], errors="coerce").dropna()
    if _fe.empty:
        st.info("Sin fechas válidas en el rango cargado.")
        return
    # EL ÚLTIMO DÍA CON DATOS ES EL DEL PARQUET, no el del rango de arriba
    # (regla #531). Hasta el 2026-09-25 era `_fe.max()`: la vista tomaba de
    # la fecha de arriba sólo su último día, y moverla con la vista abierta
    # dejaba el panel del mes en curso cortado a una fecha anterior a su
    # primer día — vacío. Mismo criterio que «Análisis de platos».
    _cfg_v = REPORTES.get("Ventas", {})
    _lim = rango_fechas(_cfg_v.get("archivo", "ventas.parquet"),
                        _cfg_v.get("carga_por_rango", "FEC REG DOCUMENTO"))
    ancla = _lim[1] if _lim else _fe.max().date()

    # Descuento: dos columnas distintas y sólo una es el MONTO.
    # `DESCUENTO ITEM DDOCUMENTO` es el descuento de la línea (ya
    # multiplicado por la cantidad); `PRECIO DESCUENTO ITEM DDOCUMENTO` es el
    # UNITARIO y sumarlo da de menos — verificado contra R2 el 2026-08-14:
    # PRECIO OFICIAL × CANTIDAD = VENTA + DESCUENTO da exacto, o sea que
    # `VENTA ITEM DDOCUMENTO` ya viene NETA y el descuento se suma aparte,
    # nunca se resta otra vez.
    col_desc = _resolver(d, ["Descuento Item Ddocumento", "Descuento"])
    col_tipo = _resolver(d, ["Nombre Descuento"])

    cols = {"fecha": col_fecha, "venta": col_venta, "pax": col_pax,
            "pedido": col_pedido, "prod": col_prod, "cant": col_cant,
            "fam": col_fam, "sub": col_sub, "desc": col_desc,
            "tipo_desc": col_tipo}
    # LA HORA DEL PEDIDO (regla #530). `FEC REG DOCUMENTO` es la del COBRO,
    # que llega 1 h 38 min después (mediana, medido el 2026-09-25) y corría
    # el pico de la noche de las 7 pm a las 10 pm. La del pedido es cuando
    # se ABRIÓ la mesa: un postre pedido después queda en esa misma hora.
    col_hora_ped = _resolver(d, ["Fecha Registro Pedido"])
    st.session_state.setdefault("vh_op_filas", _FILAS[0])

    _grano_prev = st.session_state.get("vh_grano") or _GRANO_DEF
    with _card(f"ventas_horario_{_grano_prev}"):
        # TÍTULO Y CONTROLES EN LA MISMA LÍNEA (2026-08-14, pedido del
        # usuario con la barra de TradingView como referencia: ahí el símbolo
        # y la temporalidad conviven en una sola fila).
        #
        # El patrón de las otras vistas es «título → línea → controles →
        # línea» (reglas #104/#107): dos filas y dos hairlines. Acá el título
        # es FIJO —no depende de ningún control, así que tampoco hace falta
        # el placeholder de la regla #108— y a su derecha sobraban ~600px
        # vacíos. Fusionarlas ahorra una fila entera y una línea.
        #
        # Anchos medidos como TABS (que son más angostos que las pastillas:
        # sin borde ni relleno): título 185 · granularidad 184 · medida 298 ·
        # comparar 154, sobre 873px útiles. Desde el 2026-09-25 se suma la
        # FECHA (regla #531) y el período sale del título: lo dice el
        # selector.
        # La fecha y «Comparar» comparten la última columna en una fila
        # flexible (`vh_tiempo`): el texto del rango cambia de largo con el
        # rango, y en columnas fijas uno largo se montaba sobre Comparar.
        # columnas-internas: la primera fila de la franja
        c0, c1, c2, c3 = st.columns([1.75, 1.9, 3.05, 2.9],
                                    vertical_alignment="center")
        with c0:
            # `_ph_titulo` se pinta DESPUÉS de conocer las filas (regla #108:
            # el título depende de un control que vive en esta misma franja).
            _ph_titulo = st.empty()
        with c1:
            grano = st.pills("Granularidad", list(GRANOS),
                             default=_GRANO_DEF, key="vh_grano",
                             label_visibility="collapsed") or _GRANO_DEF
        with c2:
            # Medida del MAPA: control propio y no "la primera del drill"
            # (decisión del usuario, 2026-08-14). El color sólo puede
            # codificar una cosa, y cuál es cambia el mapa por completo: por
            # venta manda el volumen, por ticket aparecen las horas de mesas
            # caras, que son otras.
            #
            # Etiquetas CORTAS acá y sólo acá: "Ticket promedio" pide 124px y
            # en una fila que ahora comparte con el título no entra. En el
            # drill, donde hay sitio, sigue con su nombre entero.
            _op_mapa = [_MED_CORTO.get(mid, lab) for mid, lab in _MEDIDAS
                        if mid != "desc" or col_desc]
            medida_lab = st.pills("Color", _op_mapa, default="Venta",
                                  key="vh_medida_mapa",
                                  label_visibility="collapsed") or "Venta"
        medida = next(mid for mid, lab in _MEDIDAS
                      if _MED_CORTO.get(mid, lab) == medida_lab)

        # Si cambió la granularidad, los períodos sueltos dejan de significar
        # lo mismo (una columna de "Semana" no es una de "Mes").
        if st.session_state.get("vh_grano_aplicado") != grano:
            st.session_state["vh_grano_aplicado"] = grano
            st.session_state[_K_EXTRAS] = []

        # ── LA FECHA DE LA VISTA (regla #531) ───────────────────────────
        # El mismo selector que el Resumen, Mix de carta y las tarjetas de
        # Compras, pero con rango PROPIO: `ctx_rango_propio` saca la clave de
        # la del loader de Ventas, así que mover esta fecha no toca la de
        # arriba ni recarga el parquet del reporte. Abre en el mes en curso
        # hasta el último día con datos —el default del reporte—, que es
        # donde la vista abrió siempre.
        _ctx_h = ctx_rango_propio()
        # La bandera avisa que la fecha cambió; acá no hay nada que escalar:
        # los paneles se traen de R2 dentro de esta misma tarjeta. El rango
        # se lee ANTES de dibujar el selector: su callback ya corrió.
        st.session_state.pop("vh_fecha_cambio", None)
        _rng = (rango_tarjeta(_CAT_RANGO, _ctx_h) if _ctx_h else None) \
            or (ancla.replace(day=1), ancla)
        del_rango = _paneles_del_rango(_rng[0], min(_rng[1], ancla), grano,
                                       ancla)
        _n_rango = len(del_rango)
        del_rango = del_rango[-MAX_MARCAS:]
        _bases = {_base_clave(k) for k in del_rango}
        extras = [k for k in st.session_state.get(_K_EXTRAS) or []
                  if _base_clave(k) not in _bases
                  ][:MAX_MARCAS - len(del_rango)]
        # Orden cronológico SIEMPRE: los paneles se leen de izquierda (más
        # viejo) a derecha, y la base de la «Diferencia» y del drill es el
        # primero — con «Año pasado», el del año pasado.
        claves = sorted(del_rango + extras,
                        key=lambda k: _rango_de_clave(k, grano)[0])
        # Las marcas apuntan a un panel por ÍNDICE: si cambian los paneles
        # —el rango, la granularidad, «Comparar»—, el índice deja de
        # significar lo mismo. Se limpian en vez de mentir.
        _fp = f"{grano}|{claves!r}"
        if st.session_state.get(_K_FIRMA_PANELES) != _fp:
            st.session_state[_K_FIRMA_PANELES] = _fp
            st.session_state[_K_MARCAS] = []
            st.session_state[_K_SEL] = None
            st.session_state.pop(_K_FOCO, None)

        with c3:
            with st.container(horizontal=True, gap="small", key="vh_tiempo"):
                if _ctx_h:
                    selector_fecha_tarjeta(
                        "vh_fecha", "vh_fecha_cambio", categoria=_CAT_RANGO,
                        ctx=_ctx_h, label=_fmt_rango_corto(*_rng))
                _boton_selector(len(extras))
        # ── LA SEGUNDA FILA: qué mira el mapa (2026-09-25, regla #530) ──
        # Mismo idioma que la primera (pestañas subrayadas, `vh_op_*` en
        # estilos/_80_cards.py). «Filas» decide la pregunta: «Días × horas»
        # es la afluencia de siempre; «Platos» y «Grupos», qué se pide y
        # cuándo. «Columnas» y «Escala» sólo existen para esas dos: en «Días
        # × horas» las columnas las pone la granularidad y cada celda ya es
        # un día.
        # columnas-internas: la segunda fila de controles de la franja
        f1, f2, f3, f4, f5 = st.columns([2.3, 2.1, 2.2, 2.3, 1.5],
                                        vertical_alignment="center")
        with f1:
            filas = st.pills("Filas", list(_FILAS), key="vh_op_filas",
                             label_visibility="collapsed") or _FILAS[0]
        en_filas = filas != _FILAS[0]
        with f2:
            hora = (st.pills(
                "Hora", list(_HORA_OP), default=_HORA_OP[0], key="vh_op_hora",
                label_visibility="collapsed",
                help="**Hora del pedido**: cuando se abrió la mesa, que es "
                     "cuando la cocina trabaja. **Hora del cobro**: cuando se "
                     "pagó, 1 h 38 min después (mediana).") or _HORA_OP[0]
                    ) if col_hora_ped else _HORA_OP[1]
        with f3:
            lectura = st.pills(
                "Leer", list(_LECTURAS), default=_LECTURAS[0],
                key="vh_op_lect", label_visibility="collapsed",
                help="**Diferencia**: cada período contra el primero, celda "
                     "por celda, en verde lo que subió y en rojo lo que "
                     "bajó.") or _LECTURAS[0]
        cols_filas, escala = _COLS_FILAS[0], _ESCALAS[0]
        if en_filas:
            with f4:
                cols_filas = st.pills(
                    "Columnas", list(_COLS_FILAS), default=_COLS_FILAS[0],
                    key="vh_op_cols",
                    label_visibility="collapsed") or _COLS_FILAS[0]
            with f5:
                escala = st.pills(
                    "Escala", list(_ESCALAS), default=_ESCALAS[0],
                    key="vh_op_esc", label_visibility="collapsed",
                    help="**Por día**: divide por los días con venta, para "
                         "comparar un mes entero con uno en curso.") \
                    or _ESCALAS[0]
        # «Venta Interna y Eventos» (regla #536): sólo en «Días × horas», que
        # mide la AFLUENCIA. En «Platos»/«Grupos» esos grupos son filas como
        # cualquier otra y conviene verlos.
        raros = True
        if not en_filas:
            with f4:
                raros = st.toggle(
                    "Venta Interna y Eventos",
                    value=bool(st.session_state.get(_K_RAROS_VALOR, True)),
                    key=_K_RAROS,
                    help="Apagado, el mapa y su detalle dejan fuera la Venta "
                         "Interna (charcutería de mostrador: sin personas, "
                         "cobrada en minutos) y los Eventos, y queda el "
                         "servicio de salón. El triángulo naranja marca las "
                         "horas que los tienen.")
            st.session_state[_K_RAROS_VALOR] = raros
        cols["fecha"] = col_hora_ped if hora == _HORA_OP[0] else col_fecha
        # Cambiar la hora cambia a qué CELDA va cada venta: las marcas viejas
        # apuntarían a otras. Y cambiar de filas cambia de qué es la ficha.
        if st.session_state.get("vh_hora_aplicada") != hora:
            st.session_state["vh_hora_aplicada"] = hora
            st.session_state[_K_MARCAS] = []
            st.session_state[_K_SEL] = None
            st.session_state.pop(_K_FOCO, None)
        # El salto desde «Análisis de platos» («Ver a qué hora se vende»)
        # deja pedida la ficha de su plato.
        _pedida = st.session_state.pop("_vh_ficha_pedida", None)
        if st.session_state.get("vh_filas_aplicada") != filas or _pedida:
            st.session_state["vh_filas_aplicada"] = filas
            st.session_state[_K_FICHA] = _pedida
            st.session_state.pop(_K_FOCO, None)

        # El PANEL va fuera de las columnas, a lo ancho de la tarjeta: dentro
        # de una columna de la franja (168px) sus cinco columnas daban 30px
        # por botón y los períodos salían escritos en vertical.
        _panel_comparar(ancla, grano, del_rango, extras)
        if _n_rango > MAX_MARCAS:
            _uni = {"Día": "días", "Semana": "semanas", "Mes": "meses",
                    "Año": "años"}[grano]
            # La granularidad más fina en la que el rango SÍ entra, medida
            # (un mes son cuatro o cinco semanas: «Semana» no siempre alcanza).
            _mayor = next(
                (g for g in GRANOS[GRANOS.index(grano) + 1:]
                 if len(_paneles_del_rango(_rng[0], min(_rng[1], ancla), g,
                                           ancla)) <= MAX_MARCAS), None)
            st.caption(
                f"El rango tiene {_n_rango} {_uni}: se ven los últimos "
                f"{MAX_MARCAS}."
                + (f" Con «{_mayor}» entra entero." if _mayor else ""))

        _nombre = ("Mapa por día y hora" if not en_filas else
                   f"{filas} por " + ("hora" if cols_filas == _COLS_FILAS[0]
                                      else "día de semana"))
        _ph_titulo.markdown(f'<p class="vh-titulo">{_nombre}</p>',
                            unsafe_allow_html=True)

        # Una sola línea al pie de la franja, no dos: el título ya no tiene
        # la suya porque comparte fila con los controles.
        franja_linea_inferior()

        # ── Datos: un tramo por panel ───────────────────────────────────
        cfg = REPORTES.get("Ventas", {})
        _arch = cfg.get("archivo", "ventas.parquet")
        _colp = cfg.get("carga_por_rango", "FEC REG DOCUMENTO")
        # El spinner NO es decoración: cada panel es una consulta a R2 y en
        # frío el primer tramo tarda lo suyo. Sin él, la franja de controles
        # ya está pintada y debajo no hay NADA — la pantalla se lee como
        # colgada, que es exactamente como la reportó el usuario el
        # 2026-08-14. Va DENTRO de la tarjeta y después de la franja para que
        # el mensaje aparezca donde va a aparecer el mapa.
        tramos, paneles = [], []
        _n = len(claves)
        _msg = ("Cargando el período…" if _n == 1
                else f"Cargando {_n} períodos…")
        with st.spinner(_msg):
            for k in claves:
                ini, fin = _rango_de_clave(k, grano)
                fin = min(fin, ancla)
                df = cargar_rango(_arch, _colp, ini, fin)
                if df is not None and not df.empty and filtrar_cb is not None:
                    df = filtrar_cb(df)
                if not raros and df is not None and col_fam in df.columns:
                    df = df[~df[col_fam].isin(_fh.GRUPOS_RAROS)]
                t = _prep_tramo(df, cols, grano, ini, fin)
                tramos.append(t)
                paneles.append(_celdas(t))

        # Ordenadas por día de servicio, no por número: ver _orden_horas.
        horas = _orden_horas({int(h) for c in paneles if c is not None
                              for h in c["hora"].unique()})
        if not horas:
            st.info("Sin ventas con hora en los períodos elegidos.")
            return

        if en_filas:
            marcas, foco = [], None
            _alto = _dibujar_filas(tramos, claves, grano, medida, filas,
                                   cols_filas, lectura, escala, horas)
        else:
            # ── La selección se lee ANTES de dibujar, no después ─────────────
            # Un arrastre costaba DOS pasadas del script: la que dispara
            # `on_select="rerun"`, que dibujaba el mapa todavía sin la marca y
            # recién al final la guardaba, y la de `st.rerun()` que hacía falta
            # para volver a dibujarlo con la marca puesta. Dos pasadas son dos
            # veces que Streamlit apaga y repinta la tarjeta — eso era el
            # parpadeo que se reportó el 2026-08-15.
            #
            # Con la key quieta (ver `_firma`) la key se puede calcular ANTES del
            # widget, y con ella se lee del `session_state` la selección que dejó
            # el render anterior. Así la marca ya está decidida cuando se arma la
            # figura y una sola pasada alcanza.
            #
            # La HUELLA sigue siendo imprescindible: mientras el widget siga
            # montado, esa misma selección vuelve en CADA rerun (los del rail,
            # los de los chips, los del propio drill), y sin ella la marca se
            # re-aplicaría sola una y otra vez.
            # «Diferencia» pide columnas que se correspondan: en Mes el 1 de
            # un mes no es el mismo día de semana que el 1 del otro.
            _dif = (lectura == _LECTURAS[1] and grano != "Mes"
                    and len(claves) > 1)
            if lectura == _LECTURAS[1] and not _dif:
                st.caption(
                    "«Diferencia» no está en Mes: el 1 de un mes no es el mismo "
                    "día de semana que el 1 del otro. En Semana o Año las "
                    "columnas sí se corresponden." if grano == "Mes" else
                    "La diferencia pide otro panel: ampliá el "
                    "rango de fechas o sumá uno en «Comparar».")
            # La hora y la diferencia van en la key: cambian QUÉ mapa es (las
            # coordenadas de una selección vieja serían de otro).
            _clave_mapa = (f"vh_mapa_{_firma(grano, claves, medida)}"
                           f"_{'p' if hora == _HORA_OP[0] else 'c'}"
                           f"{'_d' if _dif else ''}")
            # Un CLIC abre la ficha de la hora; un ARRASTRE, aunque sea sobre
            # una sola celda, sigue armando marcas (regla #536). Los dos pasan
            # por la misma huella: el clic con su sello, que cambia en cada uno.
            _evt = st.session_state.get(_clave_mapa)
            _clic = _clic_de_evento(_evt)
            if _clic is not None:
                _huella = f"clic|{_clic[3]}"
                if _huella != st.session_state.get(_K_SEL):
                    st.session_state[_K_SEL] = _huella
                    st.session_state[_K_FOCO] = {"sel": _clic[0],
                                                 "c": _clic[1], "h": _clic[2]}
            else:
                puntos = _puntos_de_evento(_evt)
                _huella = repr(sorted(puntos))
                if puntos and _huella != st.session_state.get(_K_SEL):
                    st.session_state[_K_SEL] = _huella
                    st.session_state[_K_MARCAS] = _agregar_marcas(
                        [m for m in st.session_state.get(_K_MARCAS, [])
                         if m["sel"] < len(claves)],
                        _marcas_de_seleccion(puntos, horas))

            marcas = [m for m in st.session_state.get(_K_MARCAS, [])
                      if m["sel"] < len(claves)]
            foco = st.session_state.get(_K_FOCO)
            if foco and (foco.get("sel", len(claves)) >= len(claves)
                         or foco.get("h") not in horas):
                foco = None
            # REPARTO. Con marcas puestas el mapa se comprime y el detalle ocupa
            # el resto de la pantalla con scroll propio, en vez de apilarse
            # debajo y empujar el gráfico fuera de la vista (1.312px de scroll
            # medidos antes de esto). El objetivo del usuario, textual: "que no
            # pierda enfoque en el gráfico principal y que haga el mínimo scroll".
            # La ficha de la hora vive en el mismo panel: cuenta igual.
            _alto = _alto_mapa(len(horas), con_drill=bool(marcas or foco),
                               varios=len(claves) > 1)
            fig = _fig_mapa(paneles, claves, grano, medida, marcas, horas, ancla,
                            alto=_alto, dif=_dif, foco=foco, raros=raros)
            st.plotly_chart(
                fig, use_container_width=True, key=_clave_mapa,
                on_select="rerun", selection_mode=("points", "box"),
                config={"displaylogo": False, "displayModeBar": False})
            # El puente que convierte el clic suelto en una selección.
            inyectar_html(_JS_CLIC_MAPA)

        # ── Pastillas de marcas: deseleccionar una la quita ─────────────
        # Las pastillas de marcas YA NO viven acá: se mudaron a la primera
        # fila del drill (2026-08-15, a pedido). El motivo es que su etiqueta
        # larga —"1 · Ago 26 · día 7 · 4 pm"— estaba DUPLICADA: ya es la
        # primera columna de la tabla de medidas y la cabecera de cada grupo
        # del árbol. Lo único que no se repetía era el ✕, así que abajo
        # quedan como número + ✕, que ocupa una fracción y va donde se usa.
        # SIN caption de ayuda (quitado a pedido, 2026-08-14). Ocupaba tres
        # líneas —~60px— explicando el arrastre y el código de colores del eje
        # de días. Lo que decía sigue estando en el docstring de este módulo,
        # y el gesto se descubre solo: arrastrar sobre un mapa es lo que uno
        # intenta primero. Si algún día hace falta para usuarios nuevos, un
        # ícono de ayuda al lado del título cuesta cero píxeles de alto.

    # ── Drill ───────────────────────────────────────────────────────────
    # Va DENTRO de un contenedor con alto fijo, que en Streamlit scrollea por
    # dentro: es la mitad de abajo del reparto. Así el detalle puede ser tan
    # largo como quiera (la tabla de medidas y el árbol suman ~720px) sin
    # empujar ni un pixel al mapa, que se queda arriba, siempre visible.
    #
    # Sin marcas no hay panel ni alto fijo: un contenedor vacío de 200px sería
    # un agujero en la tarjeta.
    # El alto del panel NO se calcula acá. Python publica lo único que sabe
    # —cuánto ocupa todo lo que va ARRIBA del panel dentro de la tarjeta— y el
    # CSS hace la resta contra la ventana REAL (estilos/_80_cards.py). Antes
    # esto era `st.container(height=alturas.reparto(...))`, que restaba contra
    # una pantalla supuesta: correcto en el laptop objetivo, y 350px de más en
    # un monitor grande. Ver `alturas.py` § LA RESTA NO SE HACE ACÁ.
    publicar_var_px(
        "vh-alto-arriba",
        alturas.FRANJA_UNA_LINEA + _FILA_CONTROLES + _alto + _CROMO_TARJETA)
    # El piso del panel también se publica en vez de vivir suelto en el CSS:
    # con marcas evita que en una pantalla apretada quede una tira ilegible;
    # SIN marcas tiene que ser 0, o el panel vacío se come 150px de tarjeta.
    _ficha = en_filas and st.session_state.get(_K_FICHA)
    publicar_var_px("vh-panel-min",
                    _PANEL_MIN if (marcas or _ficha or foco) else 0)
    # Key ESTABLE, sin `_on`/`_off`. Alternarla dejaba el contenedor viejo
    # huérfano en el DOM (regla #70) y no hace falta: con el panel vacío el
    # `max-height` no molesta a nadie.
    _panel = st.container(key="vh_panel_drill", border=False)

    with _panel:
        # ── La ficha de la hora: lo que abre un CLIC (regla #536) ───────
        # Primera del panel, pegada al mapa: es la respuesta a «¿qué fue
        # esto?» sobre la celda que se acaba de tocar. Se abre SIEMPRE, vacía
        # sin clic, por la misma regla #70 que las de abajo.
        with _card("ventas_horario_hora", "", titulo_arriba=True):
            if foco:
                _ficha_de_la_hora(
                    foco, claves, grano, ancla, filtrar_cb, raros, horas,
                    paneles, "pedido" if hora == _HORA_OP[0] else "cobro",
                    {"tiempo": cols["fecha"], "apertura": col_hora_ped,
                     "cobro": col_fecha, "venta": col_venta, "pax": col_pax,
                     "pedido": col_pedido, "prod": col_prod,
                     "cant": col_cant, "grupo": col_fam})

        # Las dos tarjetas se abren SIEMPRE, aunque no haya marcas, y por
        # dentro deciden si tienen algo que decir. NO es cosmético: un
        # `st.container(key=...)` que deja de renderizarse RETIENE sus hijos
        # (arquitectura.md regla #70). Medido acá el 2026-08-14: al cambiar la
        # granularidad las marcas se limpian, el `return` temprano se saltaba
        # estas dos tarjetas... y seguían en pantalla con los números de la
        # granularidad anterior. Vacías no se ven —el CSS de
        # estilos/_80_cards.py les quita borde y sombra dentro de la card de
        # Ventas—, así que dibujarlas siempre no cuesta un pixel.
        # SIN fila de controles (pedido 2026-08-15). Tenía las pastillas de
        # marcas, el selector de medidas, el toggle de % y el título — una
        # franja de ~44px por encima de la tabla, que es el dato. Ahora la
        # tabla arranca directamente y muestra TODAS las medidas que el
        # parquet permite calcular: es la respuesta a "¿qué diferencia hay
        # entre estas marcas?" sin tener que pedirla columna por columna.
        # Lo que se perdió, y es aceptado: quitar UNA marca suelta. Se
        # cambian desde «Comparar» o volviendo a marcar en el mapa (el tope
        # de 4 es FIFO, así que la quinta desplaza a la más vieja).
        with _card("ventas_horario_medidas", "", titulo_arriba=True):
            if marcas:
                medidas = {mid for mid, _ in _MEDIDAS
                           if (mid != "desc" or col_desc)
                           and (mid not in ("pax", "ticket")
                                or (col_pax and col_pedido))}
                # El Δ contra la marca base va SIEMPRE: sin él la tabla es
                # una lista de totales y la pregunta era la comparación.
                _tabla_medidas(marcas, tramos, claves, grano, horas,
                               medidas, True)

        # ── Drill: árbol Grupo › Sub Grupo › Plato › Descuento ──────────
        with _card("ventas_horario_arbol",
                   ("Detalle por grupo, subgrupo y plato"
                    if (marcas and col_prod) else ""), titulo_arriba=True):
            if marcas and col_prod:
                _opa = [_MED_LABEL[m] for m in _MED_ARBOL
                        if m != "desc" or col_desc]
                # Las medidas del árbol comparten fila con Expandir/Colapsar,
                # que antes vivían en su propia línea dentro de `_tabla_arbol`.
                _c_ma, _c_exp, _c_col = st.columns(
                    [3, 1.1, 1], vertical_alignment="center")
                with _c_ma:
                    _sela = st.pills("Detalle por", _opa,
                                     selection_mode="multi",
                                     default=[_MED_LABEL["venta"]],
                                     key="vh_medidas_arbol",
                                     label_visibility="collapsed")
                with _c_exp:
                    _exp = st.button("⤢ Expandir", key="vh_arbol_exp",
                                     use_container_width=True)
                with _c_col:
                    _col = st.button("⤡ Colapsar", key="vh_arbol_col",
                                     use_container_width=True)
                medidas_arbol = {m for m in _MED_ARBOL
                                 if _MED_LABEL[m] in (_sela or [])} or {"venta"}
                _tabla_arbol(marcas, tramos, claves, grano, horas,
                             medidas_arbol, expandir=_exp, colapsar=_col)

        # ── La ficha de una fila de «Platos»/«Grupos» (regla #530) ──────
        # Se abre SIEMPRE, vacía cuando no hay ficha, por la regla #70: un
        # contenedor con key que deja de dibujarse retiene a sus hijos.
        with _card("ventas_horario_ficha", "", titulo_arriba=True):
            if _ficha:
                _ficha_filas(tramos, claves, grano,
                             "prod" if filas == "Platos" else "grupo",
                             st.session_state[_K_FICHA],
                             medida if medida in _MED_FILAS else "venta",
                             horas)
