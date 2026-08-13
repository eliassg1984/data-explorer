"""
graficos.alturas — dueño ÚNICO del presupuesto vertical de las tarjetas.

Hermano de `tema.py` (dueño del color) y de `estado_rango.py` (dueño de los
tres modos del eje temporal). La regla que instaura es la gemela vertical de
«nunca un `#hex` suelto»:

    ────────────────────────────────────────────────────────────
     NUNCA UN ALTO SUELTO. Ningún `alto=430` ni `height=560` en
     un módulo de `graficos/`: se pide un ROL de este fichero.
    ────────────────────────────────────────────────────────────

POR QUÉ EXISTE (2026-08-13)
    Hasta hoy el alto de cada figura era un literal escrito a mano: 41
    números repartidos en 15 ficheros, más 19 fórmulas por nº de filas de
    las cuales 7 no tenían tope superior. Nadie era su dueño, así que nadie
    podía responder «¿entra esta tarjeta en la pantalla?». Medido en el
    navegador: 9 de 24 vistas obligaban a scrollear en 1536x864 y 19 de 24
    en un laptop de 1366x768. Ver arquitectura.md § Presupuesto vertical.

POR QUÉ EL ALTO SE DECIDE EN PYTHON Y NO EN CSS
    Parece que debería resolverlo el navegador con `dvh`, y no puede.
    Medido con un banco de pruebas el 2026-08-13, en Streamlit 1.59 +
    Plotly 6.9:
      · `st.plotly_chart(fig, height="stretch")` estira el WRAPPER de
        Streamlit (medido: 738px) pero el SVG de Plotly se queda en 450.
      · Con `autosize:true`, la cadena de contenedores forzada a `height:
        100%` y un `Plotly.Plots.resize()` explícito: sigue en 450.
      · `Plotly.relayout(gd, {height: 700})` → 700px exactos.
    Es decir: en este stack el ÚNICO control real del alto de una figura es
    `fig.layout.height`, un número que sale de Python. Por eso este módulo
    es Python y no una variable CSS. El CSS sí es dueño del MARCO de la
    tarjeta (ver `--alto-util` en estilos/_00_base.py), que es otra cosa.

LOS DOS REGÍMENES
    No todo tiene que entrar en una pantalla, y forzarlo sería peor: el
    Resumen ejecutivo de Ventas mide 1364px porque son 5 KPIs y 3 gráficos;
    comprimirlo a 501px da tres gráficos de ~150px, ilegibles. Por eso hay
    dos regímenes y cada tarjeta declara el suyo:

      1. ENCUADRADA (el default) — todo su contenido cabe en el
         presupuesto. Sus figuras piden PROTAGONISTA / APOYO / MINI.
      2. ENMARCADA — la tarjeta mide exactamente una pantalla (`MARCO`) y
         su contenido largo scrollea DENTRO de ella. Es para lo que crece
         con los datos (rankings de N filas): ahí la figura puede superar
         el presupuesto a propósito, porque el marco es lo que el usuario
         ve completo. Se pide con `por_filas(..., enmarcada=True)`.
"""

# ===========================================================================
# EL PRESUPUESTO
# ===========================================================================

# Pantalla objetivo: laptop de 1366x768, el caso más exigente del parque.
# 657px es el viewport útil REAL medido en el navegador (768 menos la barra
# de tareas y el cromo de Chrome), no una cuenta de servilleta.
VIEWPORT_OBJETIVO = 657

# Cromo vertical fijo de la app, medido elemento por elemento (2026-08-13).
# Cada sumando tiene su dueño en `estilos/`; si alguno cambia allí, hay que
# cambiarlo aquí (y el test de test_graficos.py avisa si se desincroniza).
_CAB_OFFSET = 58    # padding-top del block-container   (_00_base.py, --cab-offset-contenido)
_MARGEN_SUP = 16    # margen del bloque hasta la tarjeta (Streamlit)
_FRANJA_INF = 66    # padding-bottom que reserva la franja (_90_franja_inferior.py)
_MARGEN_INF = 16    # margen bajo la tarjeta             (Streamlit)

CROMO = _CAB_OFFSET + _MARGEN_SUP + _FRANJA_INF + _MARGEN_INF   # 156

# Alto máximo que puede medir una tarjeta sin obligar a scrollear la página.
# Verificado dos veces contra el navegador: en viewport 864 el presupuesto da
# 708 y la vista «Matriz» (742px) desbordaba exactamente 34px; en viewport
# 657 da 501 y «Por día» (584px) desbordaba exactamente 83px.
PRESUPUESTO = VIEWPORT_OBJETIVO - CROMO                          # 501

# Padding propio de la tarjeta (`padding: 16px 18px` en estilos/_80_cards.py).
# Lo que queda es el sitio real para el contenido.
_PADDING_TARJETA = 16 * 2
CONTENIDO = PRESUPUESTO - _PADDING_TARJETA                       # 469


# ===========================================================================
# LOS ROLES
# ===========================================================================
# Los tres valores están elegidos para COINCIDIR con los altos que la app ya
# usaba (430 era el default de _compras_layout, 380 el de _LAYOUT_BASE): así
# la migración de los 41 literales no mueve nada visualmente y los cambios de
# tamaño se pueden hacer después, de a uno y a la vista.

# Gráfico único que manda en su tarjeta. 430 + 32 de padding = 462 ≤ 501:
# una tarjeta PROTAGONISTA entra completa en el laptop objetivo.
PROTAGONISTA = 430

# Gráfico que comparte la tarjeta con otro (columnas) o que acompaña a un
# protagonista. También el default histórico de _LAYOUT_BASE.
APOYO = 380

# Panel de detalle, sparkline, mini-barras: existe para apoyar una lectura,
# no para leerse solo.
MINI = 240

# Alto de una tarjeta ENMARCADA: exactamente una pantalla. Lo consume el
# `height=` de `st.container()`, que scrollea su contenido por dentro.
MARCO = PRESUPUESTO


# ===========================================================================
# LO QUE LA FIGURA NO ES: LA FRANJA DE CONTROLES
# ===========================================================================
# Una tarjeta no siempre es "sólo la figura". Cuando arriba lleva su propia
# franja de controles (título + tabs + las dos líneas que la cierran), esos
# píxeles salen del MISMO presupuesto y hasta hoy nadie los contaba: el
# assert de abajo verificaba `PROTAGONISTA + padding <= PRESUPUESTO` y daba
# verde mientras la tarjeta real desbordaba.
#
# Medido en el navegador el 2026-08-13 sobre Ventas › Por día, viewport
# 1366x657 (el laptop objetivo): la tarjeta medía 558px contra un
# `--alto-util` de 501 y el eje X quedaba 25.7px POR DEBAJO del borde —
# cortado por el scroll interno, o sea invisible sin scrollear dentro de la
# tarjeta. Es el modo de fallo más caro de todos: el gráfico se ve bien, sólo
# que sin eje.
#
# Desglose de los 96px (graficos/ventas.py::_ventas_grafico_dia):
#   título 21 + su padding 9 + línea 2 + aire 6 + tabs 32 + aire 8.5
#   + línea 2 + margen al gráfico 14  ≈ 95.8  →  96
FRANJA_CONTROLES = 96


def con_franja(rol=PROTAGONISTA, franja=FRANJA_CONTROLES):
    """Alto de una figura que comparte su tarjeta con una franja de controles.

    `rol` es el techo que pediría si mandara sola; lo que devuelve es lo que
    de verdad le queda una vez descontada la franja. Se usa igual que un rol:

        _compras_layout(fig, alto=alturas.con_franja())

    Con los números de hoy: 469 de contenido - 96 de franja = 373px. Es menos
    que APOYO (380) y eso está bien — la figura no manda sola en la tarjeta,
    comparte con los controles."""
    return min(rol, CONTENIDO - franja)


# ===========================================================================
# ALTOS QUE DEPENDEN DE LOS DATOS
# ===========================================================================

def por_filas(n_filas, px_fila=34, minimo=None, rol=PROTAGONISTA,
              extra=60, enmarcada=False):
    """Alto de un gráfico de barras HORIZONTALES, donde el alto depende de
    cuántas filas hay que dibujar.

    Sustituye a las 19 fórmulas `min(900, max(320, 40 * len(g) + 80))` que
    vivían sueltas en los módulos — y a las 7 que sólo tenían `max(...)`, sin
    tope, y por lo tanto crecían sin límite con los datos reales (en modo
    demo no se notaba: hay pocas filas).

    Parámetros
      · n_filas: cuántas barras se van a dibujar.
      · px_fila: píxeles por fila. En horizontales el grosor y la separación
        dependen ambos de este número (ver CLAUDE.md § Plotly), así que es
        la palanca correcta para filas más compactas — no `bargap`.
      · minimo: piso, para que con 2 filas el título no se encime con la
        primera barra. Por defecto, la mitad del rol.
      · rol: el techo cuando la tarjeta es ENCUADRADA.
      · extra: aire para título, leyenda y márgenes del eje.
      · enmarcada: True si la tarjeta que lo contiene es un MARCO con scroll
        interno. Ahí el tope se levanta hasta `_TOPE_ENMARCADA` porque lo que
        el usuario ve completo es el marco, no la figura.
    """
    minimo = rol // 2 if minimo is None else minimo
    tope = _TOPE_ENMARCADA if enmarcada else rol
    return min(tope, max(minimo, px_fila * int(n_filas) + extra))


# Techo de una figura dentro de una tarjeta enmarcada. No es infinito a
# propósito: pasado cierto punto el scroll interno dejaría de ser navegable y
# conviene paginar o filtrar los datos en origen. 900 era el tope que ya
# usaban a mano los dos rankings de inventario.py.
_TOPE_ENMARCADA = 900


def apilado(rol=MINI, filas=2, px_extra_fila=60):
    """Alto de una figura con VARIOS subplots apilados (`make_subplots` con
    `row_heights`). Cada fila extra necesita su propio aire: repartir el alto
    de una sola entre dos deja la de abajo sin sitio para su eje.

    `px_extra_fila=60` reproduce exactamente lo que hacía a mano el resumen
    de Ventas (240 con una fila, 300 con dos)."""
    return min(PROTAGONISTA, rol + px_extra_fila * (int(filas) - 1))


def cabe(alto_total):
    """True si algo de `alto_total` px entra en el presupuesto.

    Lo usa el test guard de test_graficos.py, y sirve en un dashboard para
    decidir sobre la marcha si hace falta enmarcar."""
    return alto_total <= PRESUPUESTO


# ===========================================================================
# GUARDA DE COHERENCIA
# ===========================================================================
# Barata (corre una vez, al importar) y evita el fallo más tonto posible:
# tocar un rol "un poquito" y que deje de entrar en la pantalla objetivo sin
# que nadie se entere hasta verlo en Cloud.
assert PROTAGONISTA + _PADDING_TARJETA <= PRESUPUESTO, (
    f"El rol PROTAGONISTA ({PROTAGONISTA}px) más el padding de la tarjeta "
    f"({_PADDING_TARJETA}px) no entra en el presupuesto ({PRESUPUESTO}px)."
)
assert APOYO <= PROTAGONISTA and MINI <= APOYO, (
    "Los roles deben quedar ordenados: MINI ≤ APOYO ≤ PROTAGONISTA."
)
assert con_franja() + FRANJA_CONTROLES + _PADDING_TARJETA <= PRESUPUESTO, (
    f"Una tarjeta con franja de controles no entra: figura "
    f"({con_franja()}px) + franja ({FRANJA_CONTROLES}px) + padding "
    f"({_PADDING_TARJETA}px) supera el presupuesto ({PRESUPUESTO}px)."
)
