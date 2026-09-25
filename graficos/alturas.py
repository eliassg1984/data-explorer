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
# 2026-09-08: 128 -> 88, a pedido ("deseo aprovechar el espacio del lienzo,
# para poder subir mas las tarjetas"). La franja de VISTAS dejo de reservar
# sus 40px: paso de ser una fila a ser una capa que aparece al pasar el
# cursor (`--franja-vistas-reserva: 0`, estilos/_26_rails_scroll.py). Su
# gemelo CSS es `--cab-offset-contenido`. Junto con los 40 que devolvio la
# franja inferior el mismo dia, el presupuesto sube de 465 a 545.
# 2026-09-19: 52 -> 20, a pedido («que la franja superior se oculte y solo
# salga cuando se ubique el cursor... luego de esto hay que subir la
# tarjeta»). La franja de contexto volvió a ser CAPA y en reposo sólo deja su
# tira de 12px (`--franja-rep-reserva`), así que arriba quedan 12 + 8 de aire
# en vez de 52. Las tarjetas suben esos 32px y el presupuesto los gana.
# Regla #472.
_CAB_OFFSET = 20    # padding-top del block-container   (_00_base.py, --cab-offset-contenido)
                    # 2026-08-31: 80 -> 118, los 38px de la franja de reportes
                    # 2026-09-01: 118 -> 128, la franja paso de 38 a 48
                    # 2026-09-07: 128 -> 88, la franja de vistas no reserva
                    # 2026-09-12: 88 -> 76, la franja de reportes paso de 48 a 36
                    # 2026-09-13: 76 -> 52, la franja de reportes paso a CAPA:
                    #             en reposo solo reserva 12 de sus 36 (#397)
_MARGEN_SUP = 8     # margen del bloque hasta la tarjeta (Streamlit)
# 2026-09-08: 48 -> 8, y `_FRANJA_INF` -> `_AIRE_INF`. Los 48 eran la franja
# blanca fija de abajo (42) más 6 de aire; la franja se eliminó a pedido y su
# texto de «Última actualización» se mudó a la derecha de la franja de
# REPORTES. Abajo ya no hay nada que despejar, sólo aire: 8px. El presupuesto
# vertical gana esos 40px. Su gemelo CSS es `--aire-inferior` (_00_base.py).
_AIRE_INF = 8       # padding-bottom del block-container  (_00_base.py)
_MARGEN_INF = 8     # margen bajo la tarjeta             (Streamlit)

CROMO = _CAB_OFFSET + _MARGEN_SUP + _AIRE_INF + _MARGEN_INF

# Alto máximo que puede medir una tarjeta sin obligar a scrollear la página.
# Verificado dos veces contra el navegador: en viewport 864 el presupuesto da
# 708 y la vista «Matriz» (742px) desbordaba exactamente 34px; en viewport
# 657 da 501 y «Por día» (584px) desbordaba exactamente 83px.
PRESUPUESTO = VIEWPORT_OBJETIVO - CROMO                          # 557

# Padding propio de la tarjeta (`padding: 8px 18px` en estilos/_80_cards.py;
# vertical bajado de 16 a 8 el 2026-08-15). Lo que queda es el sitio real
# para el contenido.
_PADDING_TARJETA = 8 * 2
CONTENIDO = PRESUPUESTO - _PADDING_TARJETA                       # 541


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

# Alto de una figura cuando el usuario pidió AMPLIAR una tarjeta deslizable
# (Ajuste › Distribución, 2026-09-22). A propósito SUPERA el presupuesto de
# una pantalla: mientras está ampliada, la tarjeta sale del techo `--alto-util`
# y lo que no entra lo scrollea la página, igual que las tarjetas ENMARCADAS.
# No entra en los asserts de coherencia de abajo por eso mismo — no es un rol
# que deba caber en el laptop objetivo, es un modo de inspección que el
# usuario enciende y apaga. Ver arquitectura.md regla #494.
AMPLIADO = 620

# (Acá vivió `MINI_PROD_EVO = 270`, el alto de la Evolución de producto en
# Compras. Se fue el 2026-09-12: desde que el Ranking de productos comparte
# tarjeta con los paneles de Familia, la figura se mide contra esa tarjeta
# —`_ALTO_EVO` en graficos/compras/producto.py—, que es el mismo arreglo que
# ya tenía la Evolución de Proveedor. Un rol fijo no puede seguir a una
# vecina que cambió de alto.)

# «Semanal» (compras/semanal.py): la figura de la serie por período SIN foco,
# y la tabla de detalle que aparece al tocar una barra. Con foco la
# figura baja a COMPACTO, que es justo el rol de «figura con un segundo bloque
# del mismo peso debajo».
#
# No se despejan contra el presupuesto sino contra la tarjeta de «Vs año
# pasado», a pedido (2026-09-13, regla #398): «que la vista semanal, su
# tarjeta sea del tamaño de la de vs año anterior, ya que es muy larga cuando
# aparece el detalle». Medido antes: 552 sin foco y ~800 con él, que el techo
# de `--alto-util` cortaba con barra propia. La tarjeta salió del techo
# (`estilos/_80_cards.py`), como Volatilidad (#394), y mide lo que vap en los
# DOS estados: la tabla toma lo que la figura cede. La cuenta, MEDIDA a
# 1366x768 bloque por bloque (vap: 570.6):
#
#     sin foco   padding 16 + controles 32 + 20 + FIGURA 449 + 16
#                + caption 38 (su margen de -16 se come el padding de abajo)
#                = 571
#     con foco   padding 16 + controles 32 + 20 + COMPACTO 240 + 16
#                + TABLA 192 + 16 + caption 38 = 570
#
# 196 fue el primer intento y dio 574: la tabla es la que absorbe el ajuste,
# porque su alto es exacto (la figura se mide con su propio aire).
#
# Si vap cambia de alto, estos dos números se desincronizan EN SILENCIO: nada
# ata las dos tarjetas más que la cuenta. Se vuelve a medir.
#
# Y pasó (2026-09-17, medido a 1366x768, regla #454): vap dejó de ser UNA
# tarjeta y son tres —cabecera 59.2 + 16 + serie/cascada 245.9 + 16 + tabla
# 279.6—, o sea 617 de punta a punta, y Semanal seguía en los 571 de antes.
# El mismo día Semanal sumó su fila de KPI, que a ese ancho abre un segundo
# renglón en la cabecera (+38: 28 del KPI y 10 del gap de la fila), y la
# tarjeta quedó en 609 sin foco y 608 con él. Los 8 y 9 que faltaban los
# ponen la figura y la tabla, cada una en su estado:
#
#     sin foco   609 + 8  (SEMANAL_SOLO  449 → 457) = 617
#     con foco   608 + 9  (SEMANAL_TABLA 192 → 201) = 617
#
# OJO: el segundo renglón de la cabecera depende del ANCHO de la fila
# (medidos a 1366: toggle + filtros 801px, fecha 138, gap 10, base del KPI
# 360). Por debajo de ~950px el renglón ya existía sin el KPI —toggle,
# filtros y fecha no entran juntos— y el KPI se acomoda en él sin sumar
# alto; entre ~950 y ~1320 lo abre el KPI, que es el caso de 1366 (fila de
# 1199); por encima de ~1320 entra todo en uno. Los números de arriba son
# los de 1366, la ventana de referencia de todo este módulo.
SEMANAL_SOLO = 457
SEMANAL_TABLA = 201

FRANJA_MODO_SEMANAL = 10
"""Lo que le cuesta a «Compra por período» la fila que ELIGE qué se ve
abajo — «Detalle» (las dos grillas) o «Resumen» (una fila por barra) —,
MEDIDO en el navegador a 1366x768 el 2026-09-19.

Misma familia —y mismo motivo— que `FRANJA_CTRL_SERIE`: los píxeles salen
de la FIGURA (sin tabla) o de la TABLA (con ella), no del alto de la
tarjeta, que tiene que seguir midiendo lo que la de «Vs año pasado» (617)
en los dos estados. Ver `SEMANAL_SOLO` acá arriba y las dos restas en
`graficos/compras/semanal.py`.

SON 10 Y NO 48, y la diferencia es de dónde sale la fila: el toggle no
abre un renglón nuevo, se mete en el que ya gastaba el caption del ámbito
—que pasó a ser su vecino de fila— y lo único que se paga es la diferencia
de ALTO entre los dos, medida en el navegador: el caption mide 22.4 y el
toggle 32, o sea 9.6, que redondea a 10. Es la misma cuenta que
`FRANJA_ROTULO`: una fila que se comparte cuesta la diferencia, una fila
propia cuesta 47 (`FRANJA_CTRL_SERIE`).

Las dos restas, medidas a 1366x768 con el toggle ya puesto:

    sin tabla   16 + cab 73.6 + fig 447 + pie 32 + hueco 0 + 3 gaps = 616.6
    con tabla   16 + cab 73.6 + fig 240 + pie 32 + tabla 191 + 3 gaps
                + 16 de padding de abajo = 616.6

Los 617 de las dos de antes salían con el caption ÚLTIMO, cuyo
`margin-bottom: -16px` (regla #162) se comía el padding de abajo; ahora el
último es la tabla y ese padding se paga — de ahí que la cuenta con tabla
sume los 16 y la otra no (su último hijo sigue siendo el `st.empty()`)."""

VENTAS_RESUMEN_TABLA = 34 + 8 * 27
"""Alto de las grillas de abajo de Ventas › Resumen ejecutivo (Resumen y las
dos del Detalle): SIETE filas visibles, a pedido (2026-09-24: «las tablas de
abajo que actualmente muestran 5 filas, ahora muestren 7»).

La cuenta es la de las grillas de Compras (`tablas/compras_semanal.CROMO` =
cabecera 32 + bordes 2, filas de `compras_volatilidad.ALTO_FILA` = 27): 34 +
7 filas + la fila TOTAL fija = 34 + 8 × 27 = 250. Hasta ese día usaban
`SEMANAL_TABLA − FRANJA_MODO_SEMANAL` (191), que da cinco. Las 59 que suma
se pagan en parte con la fila de filtros más delgada (regla #519)."""

VENTAS_RESUMEN_FIG = 210
"""Alto de la figura de Ventas › Resumen ejecutivo con la tabla debajo
(2026-09-24, regla #520). Era `COMPACTO` (240) con la leyenda de Plotly al
pie, que se comía 38px de la figura (medido: área de trazo 140 de 240, la
leyenda de 201 a 230). La leyenda pasó a una pastilla flotante arriba
(«Detalle · <día>», como Comparativo › Descomposición) y la figura se
reparte así: la tabla sube 18px y el área de trazo CRECE de 140 a ~160,
a pedido: «no debe reducir tamaño del gráfico, es más, creo que mi gráfico
puede crecer verticalmente hacia arriba un poco».

Y 210 y no 222 desde la pasada siguiente, el mismo día («subir estos dos
cuadrantes y subir algo las tablas»): los márgenes de la figura bajaron de
34/10 a 28/4, y el área de trazo se quedó en los mismos 156."""



FIG_CON_SU_TABLA = 180
"""Piso de una figura que comparte su tarjeta con la TABLA que la describe,
y cuyo alto sale del reparto y no de un rol.

Lo estrenó la Evolución de Producto el 2026-09-20, cuando la tabla «una
fila por barra» bajó adentro de su tarjeta a pedido («la tabla debe estar
debajo del gráfico y formar parte de la tarjeta del gráfico»). Ahí el alto
de la figura es una RESTA —lo que la tarjeta mide menos su cromo y menos la
zona de abajo— y con los números de hoy da 237, tres píxeles por debajo de
`MINI` (240). Subirla a 240 no es gratis: la tarjeta crecería 3px sobre la
del Ranking de al lado y el piso `:has()` de `estilos/_80_cards.py` le
pondría esos 3px de blanco al pie (regla #145). Entre respetar un piso al
píxel y dejar la fila pareja, gana la fila.

Por qué 180 y no 240: `MINI` dice «existe para apoyar una lectura, no para
leerse sola» y sigue siendo el piso de una figura que ocupa su tarjeta
ENTERA. Ésta no: debajo tiene una tabla que dice lo mismo en números, así
que la figura puede bajar más sin dejar a nadie sin respuesta — es el mismo
razonamiento que llevó `MINI_CANDLE_DRILL` de 237 a 180. El piso no es
decorativo: si la tarjeta de al lado se achicara, la resta podría dar un
número que no dibuja nada.

No es el alto de nadie: es el MÍNIMO de una resta. Quien lo use lo hace
con `max(FIG_CON_SU_TABLA, <la resta>)`."""

MINI_CANDLE_DRILL = 180
"""El candlestick de Volatilidad: la mitad izquierda de la fila de abajo de
su tarjeta, al lado de la tabla de la semana (`PANEL_JUNTO_A_FIGURA`, que
mide lo mismo para que la fila termine en una sola línea).

237 -> 180 el mismo 2026-09-13, a pedido y ya con las tres tarjetas
separadas (#415): «reduzcamos verticalmente las tarjetas del gráfico de
velas y de la tabla de documentos». Entre este pedido y el de más abajo el
área de dibujo ganó sitio por otro lado —se fue la barra de Plotly (#412) y
los rótulos de las semanas pasaron a un renglón— y había llegado a 210px;
a 180 queda en ~153, bastante más que los 93 del pedido de «que no se vea
tan aplastado». Las dos tarjetas de abajo bajan ~57px.

165 -> 237 el 2026-09-13, a pedido y con captura: «hacer un poco más larga
la tarjeta para que el gráfico de velas crezca verticalmente y no se vea
tan aplastado», y en el mismo pedido una fila menos al ranking. Son 48px
de tarjeta más los 24 de la fila (`RANKING_CON_DRILL` 250 -> 226), enteros
al gráfico: la barra para deslizarlo (regla #402) le había dejado el área
de dibujo en 93px. La tarjeta vuelve a ~569, lo que medía antes de ese
pedido.

150 -> 165 el 2026-09-12: los rótulos de las semanas pasaron a DOS renglones
(rectos, para que no se tuerzan a 45° en una columna angosta) y se comieron
~15px del área de dibujo, que quedó en 90px medidos a 1160 de ventana. Los
15px vuelven de la tarjeta, que tenía aire: medida a 1366x657, la tarjeta
pasa de 473 a 480 contra 545 y el área de dibujo vuelve a 106px.

2026-09-12: el drill bajó de la columna derecha a una fila propia DEBAJO
del ranking, partida en dos (a pedido). La cuenta de abajo es la de la
columna que dejó de existir; se conserva porque explica el 150. La que
vale hoy está en `RANKING_CON_DRILL`.

Es MINI (240) recortado dos veces, y las dos se pidieron: primero a 200
(«deseo que el gráfico de velas se reduzca de forma vertical») y el mismo día
a 160, cuando se midió que la tarjeta entera no entraba en el presupuesto y
sacaba barra de scroll — ver `RANKING_CON_DRILL`, acá abajo.

Por qué un rol propio y no MINI: MINI es «una figura de apoyo al lado de otra
cosa». Éste apoya y ADEMÁS es el tercero de cuatro bloques apilados en media
columna, que es una restricción distinta y más dura. La cuenta de esa
columna, que es la que fija el número:

    KPIs 31 + gap 10 + candlestick 150 + gap 10
    + título de la semana 35 + gap 10 + tabla <= 110 (PANEL_BAJO_FIGURA)
    = 356, medido en el navegador bloque por bloque

contra los 360 de `RANKING_CON_DRILL` a la izquierda: la fila mide el MÁXIMO
de las dos, o sea 362, y con eso la tarjeta cierra en ~450 contra los 465
del presupuesto. Los gaps son 10 y no el 1rem por defecto porque
`estilos/_80_cards.py` se los baja a las DOS columnas de esta fila: 18px que
se descubrieron midiendo, no leyendo el código.

LO QUE SE COMPENSA POR EL LADO DEL MARGEN: a 160px, los 30 de margen
superior de `_compras_layout` serían el 19% de la figura para un título que
esta figura NO tiene (lo pone el KPI de arriba). El llamador los baja a 8, y
así el área de dibujo queda en ~120px — apenas 20 menos que a 200 con el
margen de siempre. Antes de bajar más este número, mirá si queda margen que
recortar: es más barato que velas más chatas."""

# Ranking (AgGrid) que comparte su tarjeta con el DRILL que abre. Hoy:
# «Insumos ordenados por volatilidad» (compras/volatilidad.py), donde la
# grilla ocupa el ANCHO ENTERO de la tarjeta y debajo va una fila partida en
# dos: el candlestick a la izquierda y la tabla de la semana a la derecha.
#
# 360 -> 276 EL 2026-09-12, con esa mudanza (a pedido: «que el cuadro suba y
# ocupe todo el largo horizontal»). Ahora el alto de la tarjeta vuelve a ser
# una SUMA —grilla + fila de abajo—, pero la fila de abajo cuesta una sola de
# sus mitades. La cuenta, MEDIDA en el navegador a 1366x657 y a 1280x657:
#
#     cromo arriba 13 + cabecera 36 + 19 + GRILLA 276 + 18
#     + fila de abajo 168 (título + candlestick 150) + cromo abajo 13
#     = 543, contra un techo (`--alto-util`) de 545: entra sin barra,
#     con 2px de aire
#
# (Los huecos de 19 y 18 son el gap de 10 de `estilos/_80_cards.py` más
# los contenedores de Streamlit que hay entre bloque y bloque; se midieron
# por posición, no se sumaron del código.)
#
# 276 = cabecera 32 + 8 filas x 30 + 4 de bordes: OCHO FILAS EXACTAS, las
# mismas que mostraba a 360 con filas de 40. No se perdió ninguna fila con la
# mudanza porque el mismo día la fila bajó a 30 (los precios pasaron al
# costado del %, `tablas/compras_volatilidad.py::ALTO_FILA`). El aire es poco
# a propósito: la cabecera de la tarjeta no envuelve ni a 1280, que era para
# lo que se guardaban los 15px de antes. Si algún día envuelve, lo que cede
# es ESTE número, de a 30.
#
# 276 -> 261 EL MISMO DÍA, a pedido: «quitemos la barra del scroll interno
# de la tarjeta; quitemos una fila del cuadro». Los 2px de aire de arriba
# eran de la laptop de 1366x657; en la pantalla del usuario no alcanzaban y
# la tarjeta sacaba barra. Una fila menos son 30px, pero la grilla ganó en
# el mismo cambio una barra de scroll HORIZONTAL (ahora recorre la ventana
# entera hacia atrás): 261 = cabecera 32 + 7 filas x 30 + 4 de bordes + 15
# de la barra — `tablas/compras_volatilidad.py::CROMO_GRID`. El aire neto
# pasa de 2 a ~17px.
#
# 261 -> 273 AL FINAL DEL MISMO DÍA (regla #394), y el número ya no se
# despeja contra el presupuesto sino contra la tarjeta de «Vs año pasado»,
# a pedido: «que la tarjeta mida igual que la de Vs año pasado». Esa tarjeta
# no tiene techo y ésta tampoco desde entonces (`estilos/_80_cards.py`), así
# que lo que no entra lo scrollea la PÁGINA. Medido a 1366x768, las dos con
# la cabecera en un renglón: vap 571, vol 543 con la cabecera de vuelta ARRIBA
# de la grilla (título y controles en una fila, como vap). Los 28 salen 16
# del padding vertical de la tarjeta —8 -> 16, el mismo de vap— y 12 de
# acá: 273 = cromo 55 (`CROMO_GRID`) + 6 filas x 36 + 2 de aire. Seis filas
# ENTERAS: la fila pasó a 36 ese día (look del modo diseño, #393).
#
# Si vap cambia de alto, este número se desincroniza EN SILENCIO: no hay
# nada que ate las dos tarjetas más que esta cuenta. Se vuelve a medir.
#
# 273 -> 298 minutos después (regla #395), y fue exactamente eso: la
# cabecera subió 5px (para quedar a la altura del título de vap) y la grilla
# 19.8 (pegada a la cabecera), o sea la tarjeta perdió ~25px; y la fila bajó
# de 36 a 24. 298 = cromo 55 + 10 filas x 24 + 3 de aire, y devuelve los
# 25px: la tarjeta vuelve a medir lo que vap.
#
# Y MÁS TARDE, EL MISMO DÍA, LA CABECERA SE FUE A LA DERECHA (a pedido: «el
# título y los selectores al lado derecho, y subamos la tabla»). Este número
# no cambió —la grilla sigue en 7 filas—, pero ya no hay 55px de cabecera
# encima: la tarjeta pasa de 528 a 473 medidos a 1366x657. Si algún día se
# quiere la octava fila de vuelta, entra con aire (≈503 contra 545).
#
# LO DE ABAJO ES LA HISTORIA DE LAS DOS FORMAS ANTERIORES.
#
# NACIÓ EN 280, APILADO (2026-09-07). Con el drill DEBAJO de la grilla, el
# alto de la tarjeta era la SUMA de los dos y a la grilla le quedaban 6
# filas. Unas horas después, a pedido y sobre una maqueta a escala, el drill
# se mudó AL LADO: ahí el alto de la fila es el MÁXIMO de las dos columnas,
# no la suma, y los ~290px que ocupaba el drill vuelven enteros a la grilla.
#
# 450 -> 370 EL 2026-09-07, Y ES LA CORRECCIÓN DE UN OLVIDO: 450 salía de
# igualar las dos columnas entre sí, pero nadie las midió contra el
# PRESUPUESTO. La tarjeta terminaba en 545px contra los 465 que caben en el
# laptop objetivo, así que el contenedor la clampeaba y le sacaba barra de
# scroll — reportado con captura, "la tarjeta no debe tener barra deslizando
# al lado". La cuenta que faltaba, con la tarjeta medida en el navegador:
#
#     padding 15+15 + cabecera 36 + gap 10 + FILA <= PRESUPUESTO (465)
#     o sea FILA <= 389; con 360 la tarjeta mide ~450 y quedan 15px de aire
#     para que la cabecera crezca (envuelve en ventanas angostas)
#
# (Ojo: el padding REAL de la tarjeta son 15px por lado, no los 8 que dice
# `_PADDING_TARJETA` — medido. Esa constante la usan los asserts de abajo,
# que son de otra familia de tarjetas; acá se cuenta lo medido.)
#
# Y 360 en la grilla son (360 - 37 de cabecera) / 40 = 8 filas. La fila
# volvió a 40 el mismo día, al volver la segunda línea con los dos precios
# (pedido: "no se ve el precio inicial y el precio final").
#
# ES LA PALANCA: si la vista muestra pocas filas, o si sobra aire debajo del
# candlestick, el número que hay que mover es ÉSTE, y cada 40px es una fila.
# No hay un segundo sitio donde el alto del ranking se decida.
#
# Y VIENE CON EL RESIDUO QUE DOCUMENTA § LA RESTA NO SE HACE ACÁ: es un
# número contra una pantalla supuesta, no contra la ventana real. No se
# puede mudar la resta al CSS como se hizo con `vh_panel_drill`, y eso está
# MEDIDO: `st_aggrid` renderiza en un iframe cuyo alto sale del `height=` de
# Python, y forzarlo por CSS encoge el iframe pero deja el documento de
# adentro en su alto — la grilla queda cortada, con su scroll fuera de la
# vista. Ver arquitectura.md #345.
#
# 298 -> 250 EL 2026-09-13, a pedido: «reducir 2 filas a la tabla principal
# de volatilidad». Cada fila son 24 (`tablas/compras_volatilidad.py::
# ALTO_FILA`), así que son 8 filas a la vista en vez de 10 y la tarjeta baja
# 48px. Con eso deja de medir lo mismo que «Vs año pasado» (la cuenta de la
# regla #394) — a pedido, no por olvido. Regla #402.
#
# 250 -> 226 unas horas después, otra vez a pedido («quitemos también una
# fila al cuadro de volatilidad»): 7 filas a la vista. Los 24px no se pierden:
# van al candlestick, junto con los 48 que creció la tarjeta en el mismo
# pedido — ver `MINI_CANDLE_DRILL`.
#
# 226 -> 241 el mismo día, con el look nuevo del modo diseño (#416): filas de
# 27 y no 24, y la grilla sin sus rayas de 3px (cromo 55 -> 49). Para que
# sigan siendo las 7 filas que se pidieron: 7 x 27 + 49 + 3 de aire (los
# mismos 3 que sobraban antes). La tarjeta del ranking crece 15px.
RANKING_CON_DRILL = 241

PANEL_JUNTO_A_FIGURA = MINI_CANDLE_DRILL
"""Tope de una tabla de detalle que va AL LADO de una figura, en la misma
fila. Hoy: la tabla de compras de la semana de Volatilidad, a la derecha
del candlestick.

Es el alto de la figura y no un número propio: las dos mitades de la fila
llevan un renglón de título encima, así que con el mismo alto terminan en
la misma línea. A 180 entran CINCO compras enteras (24px por fila + 40 de
cabecera y bordes, `tablas/compras_volatilidad.py::CROMO_SEMANA`), y la
semana más cargada de un mismo insumo que hay hoy en el parquet son tres.
Con «4 semanas» (todas las velas a la vista) puede haber más: ahí la tabla
desliza por dentro, que es lo único que se pidió que deslice. (Fueron cinco
a 165 y ocho a 237, las dos el 2026-09-13.)
Eran tres justas mientras la tabla fue un `st.dataframe` de filas de 35; el
2026-09-12 pasó a AgGrid con las filas del ranking de arriba (regla #396).

Se llamaba `PANEL_BAJO_FIGURA` y valía 110 mientras la tabla iba DEBAJO del
candlestick, en la misma columna: ahí cada píxel que crecía lo pagaba la
columna entera y entraban dos compras. Cambió de nombre el 2026-09-12, con
la mudanza al costado — un rol que dice «bajo» sobre algo que está al lado
deja al vocabulario mintiendo."""



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

FILA_MULTIPLOS = 150
"""Alto del trazo + ejes de la fila de mini-gráficos (small multiples) de
Ajuste › Evolución: los paneles por familia. Nació el 2026-09-23 con la
fusión de las tres vistas de Tiempo (regla #501), en una rejilla de tres
por fila; el mismo día pasó a UNA sola fila deslizable para que la tarjeta
entrara en la laptop (regla #505). La figura mide
`por_filas(1, px_fila=FILA_MULTIPLOS, extra=EXTRA_MULTIPLOS)`."""

EXTRA_MULTIPLOS = 34
"""Lo que la fila de mini-gráficos suma a `FILA_MULTIPLOS`: el título de
cada panel (subplot title, 11px) y su margen. Sin leyenda: la leyenda vive
en la fila del título de la tarjeta (regla #505)."""

EVO_SERIE = 270
"""Alto de la serie de sobrante/faltante/neto de Ajuste › Evolución, que
comparte tarjeta con la fila de mini-gráficos (`FILA_MULTIPLOS`) y tiene
que entrar con ella en el `--alto-util` de la laptop objetivo (613px a
1366x768 con el cromo del navegador). Era `con_franja(APOYO,
FRANJA_CTRL_EVO)` = 380 con la leyenda de Plotly adentro; bajó el
2026-09-23 a pedido («es más grande que una pantalla de laptop»), junto
con la leyenda, que se mudó a la fila del título. Regla #505."""

FRANJA_VEREDICTO = 24
"""Alto del renglón del PORCENTAJE de la cascada —«−62.6% vs año pasado ·
por comprar menos»— más el hueco hasta el bloque siguiente. MEDIDO en el
navegador.

2026-09-17: de 34 a 24. Era la cifra GRANDE con su % y su causa en un
renglón; al reordenarse la tarjeta (#449) el monto se fue arriba, al lado
de su rótulo y a 13px, y acá quedó sólo el porcentaje en 11,5. El nombre
de la constante sobrevive porque sigue siendo el renglón del veredicto —
lo que cambió es cuánto veredicto entra en él.

OJO CON REPARTIR ESTOS TRES A OJO: lo que se mide y lo que importa es la
SUMA (75), porque es lo que se le resta a la figura. El primer intento de
recalibrarlos los bajó a 70 «porque las cajas daban eso», y las dos
tarjetas de la fila saltaron de 246 a 251. Los renglones traen aire que no
se ve en `getBoundingClientRect` — line-height, el `margin-bottom: -16px`
de la #162, el redondeo de cada bloque. Si se tocan, se vuelve a medir la
TARJETA, no los renglones.

2026-08-24: 47 = bloque 31 + gap 16, cuando el veredicto eran DOS renglones.
2026-09-02: 38 = bloque 22 + gap 16, al compactarlo a uno solo a pedido
("más minimalista"); y 34 unas horas después, al sacarle el "lo explica"
que lo hacía envolver en pantallas angostas. La resta y el bloque son las dos caras del mismo
número: si el veredicto vuelve a crecer, este 38 crece con él o la figura
de abajo se pasa de largo y las dos columnas de la fila dejan de terminar
en la misma línea.

Existe por lo mismo que las FRANJA_* de arriba, pero con un matiz: acá los
píxeles no se le restan a la figura para que la TARJETA no crezca, sino para
que las DOS figuras de la fila terminen en la misma línea. Sin la resta, la
de la derecha arranca 47px más abajo, termina 47px más abajo, y la fila deja
de leerse como una grilla — el mismo defecto que `COLUMNAS_DRILL` arregla en
el eje horizontal."""

FRANJA_CTRL_SERIE = 45
"""Alto del ÚNICO renglón de cabecera que la SERIE de «Compra Vs Año
Pasado» lleva encima de la figura —el nombre del ítem y el toggle «Ver»
COMPARTEN fila— más el hueco que Streamlit deja hasta la figura. MEDIDO en
el navegador.

2026-09-22: el toggle «Ver» volvió a la fila del nombre (a pedido: «el
gráfico es muy corto verticalmente»), así que esta constante vuelve a
cubrir la cabecera ENTERA y `FRANJA_NOMBRE_CASCADA` deja de restarse. El
nombre sigue centrado en la tarjeta porque el toggle va superpuesto a la
izquierda, fuera del flujo (`position: absolute`, ver el matiz de la regla
#449). Entre el 2026-09-21 y esa fecha fueron DOS renglones (valía lo
mismo, pero se restaba también `FRANJA_NOMBRE_CASCADA`). El alto de la
serie es `_ALTO_CONTENIDO_VAP − FRANJA_CTRL_SERIE`.

45 = la cabecera (el desplegable manda con 26) + `margin-bottom` 0.3rem
(4.8) + el `gap: 16px` que Streamlit deja hasta la figura. Es bookkeeping:
lo que importa es que la TARJETA de la serie dé lo mismo que la cascada
(medido: las dos, 274px). Si se toca el layout de `vap_serie_hdr` en
`estilos/_80_cards.py`, se vuelve a medir la tarjeta, no este renglón.

Ojo con el hermano: la tarjeta de la cascada NO lleva esta fila, así que
su alto se calcula desde `_ALTO_CONTENIDO_VAP` y no desde el de la serie.
Si se restara dos veces, las dos columnas dejarían de terminar en la misma
línea. Ver `arquitectura.md` reglas #445 y #449."""

FRANJA_NOMBRE_CASCADA = 21
"""Alto del renglón con el NOMBRE del ítem que explica la cascada —negro,
centrado, 13px— más su margen. MEDIDO en el navegador el 2026-09-17.

Se resta SIEMPRE, aunque sin foco el renglón esté vacío: así la cascada
mide lo mismo con ítem y sin él. Reservar el sitio cuesta 17px; no
reservarlo hace que la figura salte de tamaño cada vez que se enfoca o se
suelta una fila, que se lee peor que la figura chica. Ver la regla #448."""

FRANJA_ROTULO = 30
"""Alto del RÓTULO que nombra qué magnitud y qué ámbito dibuja una cascada
—«Valorizado de compra · Lomo fino entero nacional x Kg»—, MEDIDO en el
navegador. Fue 17, después 24 y hoy 30, y las tres veces lo movió lo mismo:
QUIÉN manda en el alto de ese renglón. Con el texto solo eran 14px + 3 de
margen; al meterse el selector de «Partir por» pasó a mandar el
desplegable (26px); y con el `gap` de la tarjeta bajado a 4 hay que
sumarle ese aire, porque la constante mide el renglón MÁS lo que lo separa
del siguiente. Medido cada vez contra las dos tarjetas de la fila, que
tienen que dar 246.

NO lleva el gap de 16px de `FRANJA_VEREDICTO`, y ésa es la razón de que sea
tan barato: el rótulo se emite DENTRO del mismo `st.markdown` que el
veredicto (`vs_ano_pasado._resumen_html`), así que Streamlit no mete un
bloque nuevo entre medio. Ponerlo en su propio `st.markdown` costaría 16px
más — la mitad de lo que mide la línea entera — por nada.

Nació con la cascada de «Vs año pasado», que medía soles y no lo decía en
ninguna parte: reportado el 2026-09-16, *«solamente veo un valor en
moneda»*. Ver `arquitectura.md` regla #443."""

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
