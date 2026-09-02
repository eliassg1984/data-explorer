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
# 2026-08-14: 58 y 66 pasaron a 44 y 48 tras MEDIR el aire muerto en el
# navegador — 37px entre el último chip de la franja y el borde de la tarjeta,
# 24px de reserva inferior sobre una franja que mide 42. El presupuesto sube
# de 501 a 533px sin que se mueva ni un control de sitio.
# 2026-08-18: 40 -> 80. El rail de navegación dejó de comerse 90px de ANCHO a
# la izquierda y pasó a comerse 40px de ALTO arriba (la franja superior,
# --nav-top-alto). Las tarjetas ganaron ancho y perdieron ese alto: el
# presupuesto vertical baja de 553 a 513px.
_CAB_OFFSET = 128   # padding-top del block-container   (_00_base.py, --cab-offset-contenido)
                    # 2026-08-31: 80 -> 118, los 38px de la franja de reportes
                    # 2026-09-01: 118 -> 128, la franja paso de 38 a 48
_MARGEN_SUP = 8     # margen del bloque hasta la tarjeta (Streamlit)
_FRANJA_INF = 48    # padding-bottom que reserva la franja (_90_franja_inferior.py)
_MARGEN_INF = 8     # margen bajo la tarjeta             (Streamlit)

CROMO = _CAB_OFFSET + _MARGEN_SUP + _FRANJA_INF + _MARGEN_INF   # 104

# Alto máximo que puede medir una tarjeta sin obligar a scrollear la página.
# Verificado dos veces contra el navegador: en viewport 864 el presupuesto da
# 708 y la vista «Matriz» (742px) desbordaba exactamente 34px; en viewport
# 657 da 501 y «Por día» (584px) desbordaba exactamente 83px.
PRESUPUESTO = VIEWPORT_OBJETIVO - CROMO                          # 553

# Padding propio de la tarjeta (`padding: 8px 18px` en estilos/_80_cards.py;
# vertical bajado de 16 a 8 el 2026-08-15). Lo que queda es el sitio real
# para el contenido.
_PADDING_TARJETA = 8 * 2
CONTENIDO = PRESUPUESTO - _PADDING_TARJETA                       # 537


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

# Gráfico de una vista que se lee APILADA: no comparte fila con otro, manda
# en su tarjeta, pero arriba o abajo tiene un segundo bloque del mismo peso
# (una tabla, otra figura) y el PAR tiene que poder recorrerse sin sentir que
# la vista no termina más.
#
# Nació el 2026-09-02 para «Vs año pasado», a pedido y en SEGUNDA vuelta: el
# 2026-08-26 ya se había bajado su tabla de MARCO (553) a APOYO por "es muy
# largo", y con los dos bloques en APOYO la sección seguía midiendo 1.155px
# medidos — 1,9 pantallas de 1366x700.
#
# TERCERA vuelta, el 2026-09-02: 300 -> 250, en el mismo pedido que fusionó
# las dos tarjetas en una. Con los dos bloques ya dentro de la misma
# superficie, el "par" del que habla este rol dejó de ser una metáfora — y a
# 300 la sección medía 899px. A 250 mide ~799.
#
# CUARTA, el mismo día: 250 -> 240, otra vez a pedido ("reducir
# verticalmente mis gráficos"). El primer intento fue 220 y lo frenó
# `test_graficos.py`: dejaba COMPACTO por DEBAJO de MINI, o sea el gráfico
# principal de una vista más chico que el rol de las sparklines. El test
# comprueba el orden de los roles justamente porque ese orden ES la
# semántica; romperlo no habría fallado en pantalla, habría dejado el
# vocabulario mintiendo.
#
# Así que 240 = MINI es el PISO de este rol, y conviene decirlo acá: por
# debajo, lo que corresponde no es seguir bajando el número sino admitir
# que la figura dejó de ser la lectura principal de su vista. En «Vs año
# pasado» la serie lleva leyenda arriba y etiquetas de mes ROTADAS abajo,
# que se comen ~90px fijos: a 240 le quedan ~150 de trazo.
#
# Por qué un rol nuevo y no MINI (240): MINI dice "existe para apoyar una
# lectura, no para leerse solo", y la serie mensual de Vs año pasado ES la
# lectura principal de su vista. El vocabulario tiene que seguir diciendo la
# verdad; bajarla a MINI la habría hecho caber mintiendo sobre su papel.
COMPACTO = 240

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


# ===========================================================================
# REPARTO: LA FIGURA Y SU PANEL, EN LA MISMA PANTALLA
# ===========================================================================
# Nació el 2026-08-14 con Ventas › Por hora. El drill vivía APILADO debajo
# del mapa, así que abrirlo empujaba el mapa fuera de la pantalla: 1.312px de
# scroll medidos en el navegador, y el usuario perdía de vista el gráfico
# justo cuando estaba comparando contra él.
#
# El modelo es el de cualquier terminal bursátil: el gráfico y el panel de
# abajo se REPARTEN el alto y cada uno scrollea por dentro. El gráfico se
# encoge, no se va.

FRANJA_UNA_LINEA = 61
"""Alto de una franja de controles que fusiona el título con los controles en
UNA fila (Ventas › Por hora). Medida en el navegador el 2026-08-14, contra
los 96 de `FRANJA_CONTROLES`, que es la de dos filas y dos hairlines."""


CROMO_TARJETA = 18
"""Alto que se come el marco de UNA tarjeta `compras_prov_card_*`: 16 de
padding vertical (`padding: 16px 18px` en estilos/_80_cards.py) + 2 de la
línea que Streamlit pinta con `border=True`.

Distinto de `_PADDING_TARJETA`, que cuenta el padding de la tarjeta ÚNICA de
una vista (8px). Éste es el precio de ANIDAR: cuando una figura pasa a vivir
dentro de su propio bloque, sale de su alto — si no, el bloque crece y su eje
X termina debajo del borde.
"""

FRANJA_CTRL_EVO = 30
"""Alto de la fila de controles de tiempo (`cp_evo_ctrl`) de la tarjeta de
Evolución de Compras › Proveedor: la ventana (`cp_evo_periodo`) y la
granularidad (`gran_float`), los DOS en el mismo renglón.

MEDIDO en el navegador el 2026-08-23. Reemplaza a las TRES constantes que
hubo ese día — `FRANJA_PILLS` (30), `FRANJA_GRAN` (30) y `FRANJA_WIN_NAV`
(36), que eran tres filas apiladas de controles: al pasar los selectores a
`st.selectbox` aplanado a texto entraron los tres en una línea sola (con las
flechas ‹ › al final) y los ~66px de las dos filas que sobraban volvieron a
la figura.

Existe por lo mismo que existían aquellas: estos controles viven DENTRO de
una tarjeta que ya estaba llena, así que los píxeles que ocupan hay que
restárselos a la figura, o la tarjeta crece y su eje X termina debajo del
borde (el modo de fallo de `FRANJA_CONTROLES`)."""

FRANJA_VEREDICTO = 38
"""Alto de una línea de VEREDICTO —una cifra grande con su porcentaje y el
efecto que manda, todo en UN renglón— puesta encima de una figura, más el
hueco que Streamlit deja entre bloques. MEDIDO en el navegador.

2026-08-24: 47 = bloque 31 + gap 16, cuando el veredicto eran DOS renglones.
2026-09-02: 38 = bloque 22 + gap 16, al compactarlo a uno solo a pedido
("más minimalista"). La resta y el bloque son las dos caras del mismo
número: si el veredicto vuelve a crecer, este 38 crece con él o la figura
de abajo se pasa de largo y las dos columnas de la fila dejan de terminar
en la misma línea.

Existe por lo mismo que las FRANJA_* de arriba, pero con un matiz: acá los
píxeles no se le restan a la figura para que la TARJETA no crezca, sino para
que las DOS figuras de la fila terminen en la misma línea. Sin la resta, la
de la derecha arranca 47px más abajo, termina 47px más abajo, y la fila deja
de leerse como una grilla — el mismo defecto que `COLUMNAS_DRILL` arregla en
el eje horizontal."""

FRANJA_ATAJOS = 24
"""Alto de la fila de atajos de fecha (Esta semana/Este mes/Últimos 30
días/Este año) agregada DENTRO de la tarjeta de Ranking de Compras ›
Proveedor, MEDIDO en el navegador el 2026-08-23 (tarjeta: 436px sin la
fila, 460px con ella). A diferencia de `FRANJA_CTRL_EVO` (que se resta de
una FIGURA), ésta se resta de la `height=` del AgGrid
del ranking — mismo motivo: la fila es nueva, nadie le había hecho lugar
todavía."""


# ── LA RESTA NO SE HACE ACÁ ────────────────────────────────────────────────
# Acá vivió `reparto(alto_figura, ...)` durante un día: devolvía el alto del
# panel que comparte la tarjeta con una figura, restando contra CONTENIDO.
# Se borró el 2026-08-15 porque era la trampa hecha API.
#
# El problema no fue el cálculo sino CONTRA QUÉ restaba: `CONTENIDO` sale de
# `VIEWPORT_OBJETIVO`, una pantalla SUPUESTA. La resta daba bien en el laptop
# de 1366x768 y mal en todas las demás — reportado con captura en una ventana
# de 1000px: el panel se quedaba en 150 con 350 libres debajo.
#
# La regla que lo reemplaza, y que vale para cualquier vista nueva:
#
#     Python emite alturas de CONTENIDO (filas × px: `por_filas`, `apilado`).
#     Las RESTAS las hace el CSS, que es el único que conoce la ventana real.
#     Para que pueda, Python PUBLICA lo que sabe como variable CSS con
#     `graficos.base.publicar_alto_css()`.
#
# El único caso donde Python no puede evitar suponer la pantalla es ACOTAR
# una figura (`con_franja()`, el `rol=` de `por_filas`), porque Plotly ignora
# su contenedor y sólo obedece a `fig.layout.height`. Ese es el residuo
# honesto de esta suposición, y el único argumento para leer el viewport
# real algún día. Todo lo demás no lo necesita.
#
# `test_graficos.py` verifica que nadie vuelva a dimensionar un CONTENEDOR
# desde Python (`st.container(height=...)` en `graficos/`).


class _Elastico:
    """Sentinela para `alto=`: el alto NO lo decide Python, lo decide el CSS.

    No es un número y no debe entrar en ninguna cuenta: si aparece en una
    suma, es que alguien lo trató como un rol. Su `repr` lo dice para que el
    traceback sea legible."""

    def __repr__(self):
        return "alturas.ELASTICO"


ELASTICO = _Elastico()
"""Pedido de alto ELÁSTICO: la figura sale sin `fig.layout.height` y toma el
alto de su contenedor CSS al montar.

Medido el 2026-08-13 en un banco aparte (Streamlit 1.59 + Plotly 6.9), y
corrige la regla #102, que daba esto por imposible:

  · SIN `fig.layout.height`, el SVG SÍ toma el alto del contenedor CSS al
    MONTAR. Verificado en tres viewports: 1920x1000 → 602px, 1600x950 →
    544px, 1366x657 → 251px, siguiendo al hueco disponible en cada uno.
  · Lo lee UNA sola vez. Ningún camino lo recalcula después: ni el evento
    `resize`, ni `config={'responsive': True}`, ni `Plotly.Plots.resize()`,
    ni `Plotly.relayout(gd, {height: N})` (que la regla #102 daba por
    funcional y HOY es un no-op), ni un rerun de Streamlit.

Consecuencia práctica: el alto sale bien al ABRIR la app en cualquier
pantalla, y queda viejo si se redimensiona la ventana en el medio. Para eso
hace falta REMONTAR el componente (cambiar su `key`), que es el paso 2 —
mientras no esté, ELASTICO es correcto al cargar y desactualizado al
arrastrar entre pantallas."""


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
