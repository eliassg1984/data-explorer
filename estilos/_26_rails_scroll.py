"""Intercambio de rails al hacer scroll (2026-08-24).

Desde el 2026-09-18 el modulo tiene TRES disparadores, y hacen cosas
distintas:

  · el SCROLL (todo lo de abajo) elige QUE va en la columna izquierda y en
    la banda que hay bajo la franja de reportes: arriba de todo los
    reportes y las vistas, al bajar las vistas y los KPIs del reporte;
  · el HOVER sobre la cabecera elige SI se ve algo en esa banda — en reposo
    esta vacia y el contenido ocupa su sitio. Ver "LA CAPA DE LA CABECERA";
  · el HOVER sobre el borde IZQUIERDO elige si se ve la columna, con el
    mismo mecanismo girado 90 grados. Ver "LA CAPA DE LA COLUMNA".

Comparten modulo porque comparten elemento: los tres apagan y prenden las
mismas franjas, y dos modulos declarando `opacity` sobre el mismo elemento
es el bug que advierte el indice de `estilos/__init__.py`.

La columna izquierda muestra DOS cosas distintas segun donde estes:

  · arriba de todo  -> el rail de REPORTES (`compras_tabs_row`): Compras,
    Movimientos, Recetas, Ajuste...
  · al bajar        -> el rail de VISTAS (`nav_rail_lateral`): Proveedor,
    Producto, Vs ano pasado...

El razonamiento: los nombres de reporte son navegacion de PRIMER nivel y
solo hacen falta al llegar. Una vez que estas leyendo un reporte, lo que
queres a mano es moverte entre SUS vistas, no saltar a otro reporte. Asi
que la columna cambia de trabajo a medida que bajas.

EL DISPARADOR: UNA CLASE QUE PONE JS
-----------------------------------
`graficos/base.py::_render_rail` monta un iframe de alto 0 con un
temporizador que mide geometria: pone `rails-scrolled` en el <html> del
documento PADRE cuando la seccion mas visible ya no es la PRIMERA de la
pila. Todo el CSS de abajo cuelga de esa clase.

O sea que la columna cambia en cuanto dejas atras la primera vista, sin
umbrales en px — el alto de cada seccion cambia con los datos.

Por que no `st.markdown` con `<script>`: no lo ejecuta (ver CLAUDE.md).
`components.html` SI, porque es un iframe de verdad — el inspector del
proyecto ya se apoya en eso.

Por que no animaciones por scroll (`animation-timeline`), que serian CSS
puro y fue el primer intento: la `ScrollTimeline` queda INACTIVA. Medido
el 2026-08-24 en Chrome 148 — el soporte esta, y una timeline declarada
DESPUES de que la pagina asienta funciona; pero la que se declara con el
CSS inicial se crea cuando `stMain` todavia no scrollea y no se reactiva
sola cuando el contenido crece. `currentTime` se queda en null para
siempre. Si algun dia eso se arregla en el motor, volver a CSS puro es
sacar el gancho y colgar las mismas reglas de un `animation-range`.

Otros dos detalles que conviene no volver a pisar:

  1. QUIEN SCROLLEA no es la ventana sino `[data-testid="stMain"]`. La
     ventana no scrollea nunca (el layout es de alto fijo). El listener va
     en fase de CAPTURA sobre el documento, porque `scroll` no burbujea.

  2. La franja horizontal tiene su `top/left/width` fijados con
     `!important` en `navegacion.py::_CSS_FRANJA_VISTAS`, asi que no se la
     puede "mover" a la columna con CSS. Por eso hay un SEGUNDO rail
     vertical (`_render_rail`) y lo unico que cambia es cual se ve.

Un modulo de `estilos/` NUNCA lleva `<style>` propio: `_00_base` abre la
etiqueta y `_99_movil` la cierra, y todo lo del medio va pelado. Un
`<style>` anidado es sintaxis invalida y el parser DESCARTA ese modulo y
TODOS los siguientes — se perdieron los estilos moviles enteros hasta que
se encontro. Paso aca el 2026-08-24.

Solo escritorio: en movil el cromo es otro (nav inferior propia, ver
`_99_movil.py`) y ahi la columna izquierda no existe. Mismo breakpoint que
el resto del proyecto.
"""

# Duracion del cruce. Corta a proposito: es un intercambio, no un efecto.
_TRANS = "160ms"

# Cuanto espera la franja antes de irse cuando el cursor la deja (solo el
# disparador de HOVER; el del scroll no espera). No es estetica: el camino
# natural del cursor —de la franja de reportes a una vista— pasa por el borde
# entre las dos, y sin gracia un temblor de 1px la cierra en la cara del
# usuario. Al entrar no hay espera, ver esa seccion.
_ESPERA = "220ms"

# QUE ABRE LA CAPA DE LA CABECERA. Se declara una sola vez porque la
# comparten las TRES reglas de reveal (vistas, KPIs y los controles del
# reporte): tres listas copiadas es la garantia de que un dia se
# desincronizan. Va en `:has()`, que acepta una lista de selectores.
#
#   · la botonera de reportes  -> el pedido literal;
#   · la capa misma            -> sin esto se cierra en cuanto el cursor
#                                 baja a tocarla, o sea justo cuando se la
#                                 va a usar;
#   · un popover suyo ABIERTO  -> su panel es un portal a nivel de `body`,
#                                 asi que hoverearlo NO cuenta como
#                                 hoverear la franja, y un panel de filtros
#                                 abierto con su boton desvanecido es un
#                                 panel huerfano;
#   · el foco de TECLADO en la  -> desde el 2026-09-13 la franja de reportes
#     franja de reportes           es capa y en reposo no se ve: tabular a
#                                 sus botones seria operar uno invisible.
#                                 `:focus-visible` y NO `:focus`: tras un
#                                 CLIC el boton se queda con el foco, y con
#                                 `:focus` la franja no se cerraria hasta
#                                 hacer clic en otro lado.
#
# NO ESTA la franja de KPIs, y no es un olvido: `_20_compras_rail.py` le pone
# `pointer-events: none !important` a proposito ("es un rotulo, no un
# control"), y un elemento que el navegador no hit-testea no puede estar
# :hover NUNCA. Ponerla en esta lista seria un selector que no matchea jamas.
# No hace falta: la franja de reportes esta pegada encima —desde el
# 2026-09-13 tambien aparece con el cursor, pero la capa entera se abre y se
# cierra junta—, y sobre un rotulo no hay nada que ir a tocar.
#
# Y EL PILL DE FECHA VA ACOTADO A `fila_ajuste_top`, que es el contenedor de
# la franja (`app.py` lo dibuja adentro). La MISMA key la usa una tarjeta:
# Compras > Documentos SUNAT llama a `franja_fecha.render()` dentro de
# `sunat_card_izq`, donde el pill no es cromo sino EL filtro de la tabla.
# Sin acotar, pasar el cursor por ese control —o abrir su calendario, que
# deja `aria-expanded="true"` puesto todo el rato— abría la capa de la
# cabecera desde el medio de la página. Ver regla #457.
# QUE ABRE LA CAPA DE LA COLUMNA (2026-09-18). La gemela de _DISPARADORES,
# para el otro eje. Se declara aparte y no se suma a aquella porque son dos
# capas independientes: pasar por la franja de reportes no tiene por que
# desplegar la columna encima de la primera tarjeta.
#
#   · los dos railes    -> son los que ocupan la columna, por turnos. En
#                          reposo estan recortados a la tira del borde, asi
#                          que hoverear "el rail" es hoverear esa tira;
#   · el PESTILLO       -> vive por encima de los dos (z-index 902), asi que
#                          pararse en el NO cuenta como pararse en el rail.
#                          Sin esto, ir a plegar la columna la cierra en el
#                          camino;
#   · el foco de TECLADO-> mismo motivo que en la franja de reportes:
#                          tabular a un boton no puede dejar operando uno
#                          invisible. `:focus-visible` y no `:focus`, para
#                          que un clic no deje la columna abierta.
#
# NO ESTA el rotulo ("Reportes"): `_20_compras_rail.py` le pone
# `pointer-events: none` a proposito —es un rotulo, no un control— y un
# elemento que el navegador no hit-testea no puede estar :hover NUNCA.
# Mismo caso que la franja de KPIs en la lista de abajo.
_DISP_COLUMNA = """.st-key-compras_tabs_row:hover,
            .st-key-nav_rail_lateral:hover,
            .st-key-rail_pestillo_abierto:hover,
            .st-key-rail_pestillo_plegado:hover,
            .st-key-compras_tabs_row :focus-visible,
            .st-key-nav_rail_lateral :focus-visible"""

_DISPARADORES = """.st-key-nav_franja_rep:hover,
            .st-key-nav_franja_rep :focus-visible,
            .st-key-nav_rail:hover,
            .st-key-chips_ajuste_tabla:hover,
            .st-key-fila_ajuste_top .st-key-fecha_ajuste_pill:hover,
            .st-key-fecha_corte_nav:hover,
            .st-key-chips_ajuste_tabla [aria-expanded="true"],
            .st-key-fila_ajuste_top .st-key-fecha_ajuste_pill [aria-expanded="true"]"""

CSS = f"""
@media screen and (min-width: 769px) {{

    /* ── LOS HIJOS SIGUEN AL RAIL ─────────────────────────────────────
       `visibility` se hereda, pero Streamlit la RE-DECLARA: el wrapper que
       mete adentro de cada `stMarkdown` trae un `visibility: visible` propio
       (medido 2026-09-01; la unica clase que lo lleva es un hash de emotion
       — `.st-emotion-cache-6c7yup` ese dia — asi que no se lo puede nombrar,
       cambia entre versiones de Streamlit). Resultado: con el rail lateral
       en `visibility: hidden`, su CABECERA se seguia leyendo — `innerText`
       devolvia "Compras / S/ 71.3k / 153 docs" y Ctrl+F la encontraba.

       `inherit` y no `hidden`: asi los hijos siguen SIEMPRE al rail, en los
       dos estados, y no hay que gatillar esta regla con `.rails-scrolled`
       ni repetirla por cada clase interna que aparezca. Y sigue respetando
       la degradacion segura de mas abajo: si algun dia una animacion vuelve
       a poner el rail visible, los hijos heredan eso.

       Descendiente amplio A PROPOSITO (el caso que CLAUDE.md pide evitar,
       al reves): lo que se quiere justamente es que capture a los widgets
       que se agreguen despues. */
    .st-key-compras_tabs_row *,
    .st-key-nav_rail *,
    .st-key-nav_rail_lateral *,
    .st-key-rail_rotulo_rep *,
    .st-key-nav_franja_kpis * {{
        visibility: inherit;
    }}

    /* ── El gancho ────────────────────────────────────────────────────
       `graficos/base.py::_render_rail` monta un `components.html` que
       pone/saca la clase `rails-scrolled` en el <html> del documento
       padre segun el scroll de `stMain`. Todo lo de aca abajo cuelga de
       esa clase. */

    /* ── LA FRANJA DE VISTAS NO ESTA: APARECE CON EL CURSOR ────────────
       2026-09-07, a pedido: *"debe desaparecer la franja, no solo los
       iconos y el texto sino la franja como tal, y solo aparecer cuando el
       cursor se pose sobre la botonera del reporte... deseo aprovechar el
       espacio del lienzo, para poder subir mas las tarjetas"*.

       O sea que la franja dejo de RESERVAR sitio: `--franja-vistas-reserva`
       vale 0 (`_00_base.py`), `--cab-offset-contenido` bajo de 128 a 88 y
       el contenido subio esos 40px. Aca queda su reposo —oculta—; el reveal
       vive en la seccion "LA CAPA DE LA CABECERA", mas abajo.

       ESTO REEMPLAZA AL DESLIZAMIENTO DEL 2026-09-01, que la sacaba al
       scrollear con un `transform: translateY(-40px)` y la dejaba puesta
       arriba de todo. Ya no hace falta: no esta nunca, asi que no hay de
       donde sacarla. Su guarda `:has(.st-key-nav_rail_lateral)` —"la franja
       solo puede irse si las vistas tienen donde vivir"— se fue con ella, y
       el peligro que cubria tambien: hoy las vistas vuelven con el cursor en
       cualquier dashboard, tenga rail lateral o no.

       Y con ella se fue la razon por la que antes se apagaban los BOTONES y
       no la franja —que el contenido se veia pasar por detras del hueco—:
       ese hueco ya no existe. La franja de REPORTES (opaca, de borde a
       borde, 0..48) es el techo, y el contenido pasa por debajo de ella
       como por debajo de cualquier cabecera fija.
       (2026-09-13: ya no. La franja de reportes siguio el mismo camino y
       es capa tambien — ver el punto 0 de "LA CAPA DE LA CABECERA". En
       reposo el techo es su tira de `--franja-rep-reserva`.) */
    .st-key-nav_rail {{
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        transition: opacity {_TRANS} linear {_ESPERA},
                    visibility 0s linear calc({_TRANS} + {_ESPERA});
    }}

    /* ── LOS DOS RAILES SUBEN, Y LA CABECERA SE VA CON LA FRANJA ──────
       Al irse la franja de vistas (40px) y la cabecera (33), la columna
       tiene 73px libres arriba: sube a tocar la franja de REPORTES, que es
       lo unico que queda del cromo superior.

       El `top` se anima en los DOS railes a la vez, no en el que se ve. Si
       cada uno tuviera su propia altura —el de Reportes abajo, el de Vistas
       arriba— durante los 160ms del cruce se verian los dos en sitios
       distintos y el efecto seria un salto, no un ascenso. Con el mismo
       `top` animado, la columna SUBE mientras cambia de contenido, que es
       lo que se pidio.

       Mismo `:has()` que la franja: si no hay rail lateral, la franja no se
       va y entonces la columna tampoco tiene por que subir. */
    .st-key-compras_tabs_row,
    .st-key-nav_rail_lateral {{
        transition: top {_TRANS} cubic-bezier(.4,0,.2,1),
                    max-height {_TRANS} cubic-bezier(.4,0,.2,1),
                    opacity {_TRANS} linear,
                    visibility 0s linear 0s;
    }}
    :root.rails-scrolled
        [data-testid="stAppViewContainer"]:has(.st-key-nav_rail_lateral)
        .st-key-compras_tabs_row,
    :root.rails-scrolled
        [data-testid="stAppViewContainer"]:has(.st-key-nav_rail_lateral)
        .st-key-nav_rail_lateral {{
        /* La RESERVA y no el alto (2026-09-13): la franja de reportes es
           capa desde ese dia y en reposo solo ocupa su tira de arriba. */
        top: var(--franja-rep-reserva) !important;
        max-height: calc(100vh - var(--franja-rep-reserva) - 8px) !important;
    }}
    /* Y la cabecera se va con ellos: al pegarse el rail a la franja de
       reportes ya no hay banda donde ponerla, y el nombre del reporte lo
       dice la franja de KPIs que acaba de entrar. Esto es, de paso, lo que
       resuelve el pedido original — sacar el rotulo «Vistas», que era el
       unico que se veia en este estado. */
    :root.rails-scrolled
        [data-testid="stAppViewContainer"]:has(.st-key-nav_rail_lateral)
        .st-key-rail_rotulo_rep {{
        opacity: 0;
        visibility: hidden;
    }}

    /* El rail de REPORTES se va. */
    .st-key-compras_tabs_row {{
        transition: opacity {_TRANS} linear,
                    visibility 0s linear 0s;   /* vuelve visible YA */
    }}
    :root.rails-scrolled .st-key-compras_tabs_row {{
        opacity: 0;
        visibility: hidden;                    /* ver OCULTO DE VERDAD */
        pointer-events: none;
        transition: opacity {_TRANS} linear,
                    visibility 0s linear {_TRANS};  /* se esconde al final del fundido */
    }}

    /* ── LA FRANJA DE ARRIBA TAMBIÉN CRUZA (2026-09-01, a pedido) ─────
       "Que al bajar la franja de vistas se vaya y en su lugar aparezca
       otra con el nombre del reporte y sus KPIs". Es el TERCER par que
       cuelga de este mismo gancho, después de los dos railes y sus dos
       rótulos: no hay mecanismo nuevo.

       2026-09-07, a pedido ("también la franja que muestra los kpis del
       reporte, cuando el usuario hace scroll"): el cruce sigue, pero sus
       DOS mitades son ahora una CAPA que sólo se ve con el cursor encima.
       El gancho dejó de decidir SI se ve algo en esa banda y pasó a decidir
       QUÉ se ve cuando la capa se abre: arriba de todo, las vistas;
       habiendo bajado, el nombre del reporte y sus números. El reveal de
       las dos está junto, en "LA CAPA DE LA CABECERA".

       Acá vivía además el reposo de los BOTONES de vista, que se apagaban
       sin apagar su franja (su fondo tenía que quedarse para tapar el
       contenido que pasaba por detrás). Se retiró: hoy se apaga la franja
       ENTERA unas líneas más arriba, y los botones la siguen solos por el
       `visibility: inherit` del bloque de accesibilidad. */
    /* Reposo OCULTO y sin `!important`, por el mismo motivo que el rail
       lateral (ver "DEGRADACION SEGURA"): si el gancho no llega a
       montarse, el peor caso es que no pase nada — no una franja de KPIs
       tapando a las vistas de forma permanente. */
    .st-key-nav_franja_kpis {{
        opacity: 0;
        visibility: hidden;
        transition: opacity {_TRANS} linear {_ESPERA},
                    visibility 0s linear calc({_TRANS} + {_ESPERA});
    }}

    /* Y su RÓTULO con él: la tarjeta cambia de contenido, así que el
       "Reportes" de arriba tiene que cambiar a "Vistas" en el mismo gesto.
       Si sólo cruzaran los railes, el rótulo mentiría justo mientras dura
       el cruce — que es cuando se lo mira. Geometría de los dos en
       `estilos/_20_compras_rail.py`. */
    .st-key-rail_rotulo_rep {{
        transition: opacity {_TRANS} linear,
                    visibility 0s linear 0s;
    }}
    :root.rails-scrolled .st-key-rail_rotulo_rep {{
        opacity: 0;
        visibility: hidden;                    /* ver OCULTO DE VERDAD */
        transition: opacity {_TRANS} linear,
                    visibility 0s linear {_TRANS};
    }}

    /* ══ LA CAPA DE LA CABECERA ════════════════════════════════════════
       2026-09-07, dos pedidos del mismo dia: *"que la franja que esta
       debajo de la franja de reportes solo aparezca cuando el cursor se
       posa sobre la botonera del reporte"*, y despues *"debe desaparecer la
       franja, no solo los iconos y el texto sino la franja como tal...
       deseo aprovechar el espacio del lienzo, para poder subir mas las
       tarjetas"* y *"tambien la franja que muestra los kpis del reporte"*.

       Los 40px bajo la franja de reportes dejaron de ser una FILA y pasaron
       a ser una CAPA. La diferencia es de layout, no de estetica: una fila
       reserva su alto y empuja a todo lo de abajo, una capa se dibuja
       ENCIMA y no le quita sitio a nadie. Por eso el cambio no es solo esta
       seccion — `--franja-vistas-reserva` (0) y `--cab-offset-contenido`
       (128 -> 88) en `_00_base.py`, con `graficos/alturas.py::_CAB_OFFSET`
       en sync, son la otra mitad y son las que devuelven los 40px.

       QUE HAY EN LA CAPA, que no es una cosa sino tres, y no se ven las
       tres a la vez:

         1. los controles del REPORTE (filtros y fecha), en los dos estados;
         2. las VISTAS, solo arriba de todo;
         3. los KPIs del reporte, solo habiendo bajado.

       Las (2) y (3) son las dos mitades del cruce por scroll que ya existia
       (ver arriba): el gancho sigue eligiendo cual de las dos, y esto elige
       si se ve alguna. Se excluyen por `:not(.rails-scrolled)` / .`rails-
       scrolled` y no por especificidad — dos mecanicas sobre el mismo hueco
       tienen que excluirse por construccion, o el dia que alguien toque un
       selector se pisan calladas.

       EL DISPARADOR ES `:has(... :hover)` EN `:root`, no un `>` ni un `~`:
       la franja de reportes no es ni ancestro ni hermana de las otras dos
       —una la dibuja `inject_navegacion` ANTES del fragment y las otras
       `_render_rail` adentro—, asi que la unica forma de que el hover de
       una alcance a las otras es subir el estado a la raiz y bajar desde
       ahi. Sin JS y sin clase que poner, a diferencia del cruce.

       COMO SE VERIFICA: en el navegador automatizado las transiciones no
       avanzan y `getComputedStyle(...).opacity` devuelve 0 con la regla
       aplicando perfecto. Medir `pointer-events`, que cambia en el mismo
       par de reglas y no tiene transicion. Ver arquitectura.md #353. */

    /* 0. LA FRANJA DE REPORTES MISMA (2026-09-13, a pedido: *"que la
          franja superior de reportes aparezca cuando el cursor se ponga
          sobre su lugar y que inicialmente este oculta... para aprovechar
          espacio vertical"*). Hasta hoy era la unica pieza fija de la
          cabecera y el disparador de las otras; ahora es una mas de la capa
          y sigue siendo la que la abre.

          EN REPOSO NO PUEDE IRSE ENTERA, y ese es todo el truco. Con
          `visibility: hidden` el navegador no la hit-testea, asi que no
          podria estar `:hover` NUNCA y no tendria como volver. Se queda con
          `opacity: 0` (invisible pero hit-testeable) y un `clip-path` que la
          RECORTA a la tira de `--franja-rep-reserva`. El recorte recorta
          tambien el hit-testing: en reposo solo los 12px de arriba la
          despiertan, y lo que quedo debajo al subir el contenido 24px —el
          rail, el pestillo, la fila de controles de la primera tarjeta—
          sigue recibiendo sus clics. Sin el recorte, los 36px serian una
          tapa invisible sobre todo eso.

          El `clip-path` se suelta AL INSTANTE al abrir —la franja entera
          pasa a ser zona de hover, asi que bajar el cursor hacia un nombre
          no la cierra— y se vuelve a poner al FINAL del fundido de salida.
          Es el `visibility` de las otras tres piezas, con otro nombre.

          Lo que se pierde: los nombres de los reportes siguen en el arbol de
          accesibilidad aunque no se vean. Es el precio de que la franja
          pueda despertar sola. A cambio, el foco de TECLADO la abre (esta en
          `_DISPARADORES`): tabular a un boton no deja operando uno invisible.

          COMO SE VERIFICA: igual que el resto de la capa, por
          `document.elementFromPoint` y no por la opacidad (#353): con el
          recorte puesto, a y=20 tiene que devolver lo que hay DEBAJO. */
    .st-key-nav_franja_rep {{
        opacity: 0;
        clip-path: inset(0 0 calc(100% - var(--franja-rep-reserva)) 0);
        transition: opacity {_TRANS} linear {_ESPERA},
                    clip-path 0s linear calc({_TRANS} + {_ESPERA});
    }}
    :root:has({_DISPARADORES}
        ) .st-key-nav_franja_rep {{
        opacity: 1;
        clip-path: inset(0);
        transition: opacity {_TRANS} linear,
                    clip-path 0s linear 0s;
    }}
    /* Y el sello de «Ultima actualizacion» con ella. Es un div `fixed`
       colgado del body (`inyecciones/varios.py`), no un hijo de la franja,
       asi que no hereda su opacidad; y en escritorio no tiene fondo propio
       —se apoyaba en el blanco de la franja—, asi que en reposo quedaria
       flotando sobre el contenido que pasa por debajo. Ya es
       `pointer-events: none`: no hace falta recortarlo. */
    #sello-actualizacion {{
        opacity: 0;
        transition: opacity {_TRANS} linear {_ESPERA};
    }}
    :root:has({_DISPARADORES}
        ) #sello-actualizacion {{
        opacity: 1;
        transition: opacity {_TRANS} linear;
    }}

    /* 1. LOS CONTROLES DEL REPORTE. Se ven en los dos estados: no dependen
          de donde estes en la pagina, y hasta hoy seguian pinchados arriba
          tambien al scrollear. */
    :root:has({_DISPARADORES}
        ) :is(.st-key-chips_ajuste_tabla, .st-key-fecha_ajuste_pill,
              .st-key-fecha_corte_nav) {{
        opacity: 1;
        visibility: visible;
        pointer-events: auto;
        transition: opacity {_TRANS} linear,
                    visibility 0s linear 0s;
    }}

    /* 2. LAS VISTAS, arriba de todo. */
    :root:not(.rails-scrolled):has({_DISPARADORES}
        ) .st-key-nav_rail {{
        opacity: 1;
        visibility: visible;
        pointer-events: auto;
        /* Al ENTRAR no hay espera: aparecer tarde se siente roto. La espera
           vive en el reposo (`_ESPERA`), que es el lado que la necesita. */
        transition: opacity {_TRANS} linear,
                    visibility 0s linear 0s;
    }}

    /* 3. LOS KPIs, habiendo bajado. Sin `pointer-events`: son un ROTULO y
          `_20_compras_rail.py` se los quita con `!important` a proposito
          (ver la nota de `_DISPARADORES`). */
    :root.rails-scrolled:has({_DISPARADORES}
        ) .st-key-nav_franja_kpis {{
        opacity: 1;
        visibility: visible;
        transition: opacity {_TRANS} linear,
                    visibility 0s linear 0s;
    }}

    /* El reposo de los controles del reporte. El de las dos franjas vive
       arriba, cada uno con su bloque, porque los dos tienen ademas su
       propia historia con el cruce por scroll. */
    .st-key-chips_ajuste_tabla,
    .st-key-fecha_ajuste_pill,
    .st-key-fecha_corte_nav {{
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        transition: opacity {_TRANS} linear {_ESPERA},
                    visibility 0s linear calc({_TRANS} + {_ESPERA});
    }}

    /* ── El rail de VISTAS entra ──────────────────────────────────────
       GEOMETRIA ACOPLADA: estos cuatro valores son los mismos que
       `estilos/_20_compras_rail.py` le da a `.st-key-compras_tabs_row`,
       porque los dos ocupan EL MISMO hueco y el cambio tiene que verse
       como que la columna cambio de contenido, no como que se movio. Si
       alla se corre el rail, aca hay que correrlo igual.

       2026-08-26: `top` a `0` y `max-height` sin el termino
       `- var(--nav-top-alto)` — mismo cambio y mismo motivo que
       `_20_compras_rail.py` (ver el comentario largo ahi). Se repite acá
       en vez de derivarlo con una variable compartida porque las CUATRO
       propiedades son literales duplicados a proposito desde que nacio
       este rail (2026-08-24) — es el precio ya asumido de la geometria
       acoplada, no algo nuevo de este cambio.

       2026-08-31: `top` a `47px`, `max-height` recupera ese termino y
       `border-radius` a 0 — la cuarta vuelta de la serie, explicada
       entera en `_20_compras_rail.py`. */
    .st-key-nav_rail_lateral {{
        position: fixed !important;
        top: calc(var(--franja-rep-reserva) + var(--franja-vistas-reserva)
                  + var(--rail-cab-alto)) !important;   /* == _20_compras_rail.py */
        left: 19px !important;                        /* == _20_compras_rail.py */
        width: var(--rail-der-w) !important;          /* nombre historico: es el IZQUIERDO */
        max-height: calc(100vh - var(--franja-rep-reserva)
                               - var(--franja-vistas-reserva)
                               - var(--rail-cab-alto) - 8px) !important;  /* == _20_compras_rail.py */
        overflow-y: auto !important;
        overflow-x: hidden !important;
        scrollbar-width: none !important;
        z-index: 901 !important;                      /* 1 por encima del de reportes (900) */
        margin: 0 !important;
        padding: 8px 0 16px 0 !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 0 !important;                  /* == _20_compras_rail.py */
        box-shadow: none !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 0 !important;
        /* ── DEGRADACION SEGURA ───────────────────────────────────────
           Estado de reposo OCULTO, y sin `!important` a proposito: una
           animacion le gana a una declaracion normal, asi que cuando la
           timeline esta activa manda el keyframe, y cuando NO lo esta
           manda esto.
           Hace falta porque la timeline no siempre arranca: si se declara
           mientras `stMain` todavia no scrollea, queda inactiva y no se
           reactiva sola (medido 2026-08-24; una timeline declarada DESPUES
           de que la pagina asiente si activa). Sin este reposo, la
           inactividad dejaba el rail lateral a opacidad 1 ENCIMA del de
           Reportes: los dos visibles, superpuestos. Con esto, el peor caso
           es que la funcion no ocurra y la pantalla se vea como siempre. */
        /* ── OCULTO DE VERDAD ─────────────────────────────────────────
           `opacity: 0` no saca del arbol de accesibilidad NI del orden de
           tabulacion. Medido el 2026-08-31 (1280x800, Compras): con el rail
           en reposo sus 7 `<button>` seguian con `tabIndex >= 0` y sin
           `disabled`, o sea TABBABLES, y su `innerText` seguia ahi — asi que
           tabulando el foco caia en siete botones invisibles que ademas
           tienen `pointer-events: none`, y Ctrl+F encontraba texto que no
           se ve. Lo mismo del otro lado: el rail de Reportes al bajar.

           `visibility: hidden` si saca de las dos cosas, y a diferencia de
           `display: none` NO borra la caja — el rail es `position: fixed` y
           el scrollspy le lee `getBoundingClientRect()`, que con
           `visibility` sigue diciendo la verdad.

           El truco de las dos transiciones es lo que salva el fundido:
           `visibility` no interpola (es discreta), asi que se conmuta con
           `0s` y un `transition-delay`. Al SALIR el delay es el largo del
           fundido, para que se esconda recien cuando ya no se ve; al ENTRAR
           es `0s`, para que aparezca antes de empezar a subir la opacidad.
           Sin el delay de entrada —o sea heredando el de esta regla— el rail
           se quedaria invisible los 160ms del fundido y despues apareceria
           de golpe.

           Sigue todo SIN `!important`, por el motivo de arriba. */
        opacity: 0;
        visibility: hidden;
        pointer-events: none;
        transition: opacity {_TRANS} linear,
                    visibility 0s linear {_TRANS};
    }}
    .st-key-nav_rail_lateral::-webkit-scrollbar {{ display: none !important; }}

    /* ══ LA CAPA DE LA COLUMNA ═════════════════════════════════════════
       2026-09-18, a pedido: *"hagamos que esa franja este oculta desde el
       inicio y solo aparezca al pasar el cursor, como actualmente es la
       barra superior de reporte"*. Es EL MISMO mecanismo del punto 0 de
       "LA CAPA DE LA CABECERA", girado 90 grados: lo que alla es una tira
       de `--franja-rep-reserva` en el borde de arriba, aca es una tira de
       `--rail-reserva` en el borde izquierdo.

       Y trae la misma consecuencia de layout que aquel: la columna dejo de
       RESERVAR su ancho. `--rail-der-res` bajo a `--rail-reserva` + el
       canal (`_00_base.py`), o sea que las tarjetas arrancan en x=36 en vez
       de 89 (plegada) o 323 (abierta) y el rail se dibuja ENCIMA cuando
       aparece. De paso deja sin sentido el default del pestillo, que
       plegaba para ganar ese ancho: desde hoy la columna abre desplegada
       (`navegacion.py`).

       EN REPOSO NO PUEDE IRSE ENTERA, y ese es todo el truco, igual que
       arriba: con `visibility: hidden` el navegador no la hit-testea, asi
       que no podria estar `:hover` NUNCA y no tendria como volver. Se queda
       con `opacity: 0` (invisible pero hit-testeable) y un `clip-path` que
       la recorta a esa tira. El recorte recorta tambien el hit-testing: sin
       el, los 280px del rail serian una tapa invisible sobre la tarjeta.

       TRES COSAS QUE NO SON DECORACION

       · LA CAJA LLEGA AL VIDRIO Y NO SE MUEVE NUNCA (`left: 0` + 19px de
         BORDE IZQUIERDO TRANSPARENTE). El rail se dibuja en x=19; si la
         tira empezara ahi, los 19px pegados al borde de la ventana no
         despertarian nada — y ahi es justo donde termina el cursor cuando
         uno lo tira contra el vidrio.

         El primer intento fue correr el `left` de 0 a 19 al abrir, y NO
         SIRVE: medido el 2026-09-18, el rail se corre 19px a la derecha en
         el mismo instante en que aparece, o sea que se va de abajo del
         cursor que lo acaba de abrir — `:hover` se apaga solo y la capa
         parpadea. LO QUE ABRE UNA CAPA NO PUEDE MOVERSE AL ABRIRSE.

         La caja se queda entonces en x=0 con 19px de mas de ANCHO, y esos
         19px son un `border-left` TRANSPARENTE: cuentan para el
         hit-testing y no pintan nada. El fondo se recorta con
         `background-clip: padding-box` para que no se meta abajo de ese
         borde, y la linea de 1px que el borde reemplaza vuelve como
         `box-shadow: inset`. Lo que se VE queda exactamente donde estaba
         —x=19, alineado con la cabecera, el rotulo y el pestillo, que no se
         tocan— y lo que se TOCA llega al vidrio.
       · `bottom: 8px` EN REPOSO. El rail mide su CONTENIDO (`height: auto`,
         ~550px de los ~800 de la ventana): sin esto, la mitad de abajo del
         borde no despierta nada y el gesto funciona o no segun a que altura
         pases. Estirado, la tira es el borde ENTERO.
       · LOS DOS RAILES, cada uno en SU estado. `compras_tabs_row` (Reportes)
         es el activo arriba de todo y `nav_rail_lateral` (Vistas) al bajar;
         el otro sigue con su `visibility: hidden` de siempre, porque un
         rail que no es el de este scroll no tiene que poder despertar.

       LO QUE SE PIERDE: los items del rail activo siguen en el arbol de
       accesibilidad y en el orden de tabulacion aunque no se vean, que es
       justo lo que evitaba el `visibility: hidden` (ver "OCULTO DE VERDAD"
       aca arriba, que sigue valiendo para el rail INACTIVO). Es el precio
       de que la columna pueda despertar sola, el mismo que ya paga la
       franja de reportes. A cambio, el foco de TECLADO la abre.

       COMO SE VERIFICA: por `document.elementFromPoint` y no por la
       opacidad (#353) — con el recorte puesto, a x=200 tiene que devolver
       la tarjeta, y a x=5 el rail. Ver regla #465. */
    /* LA CAJA, IGUAL EN LOS DOS ESTADOS (ver "LA CAJA LLEGA AL VIDRIO").
       El 19px es el `left` que tenian los dos railes y que ahora es su
       borde: el mismo literal duplicado a proposito que ya documentan
       `_20_compras_rail.py` y la geometria acoplada de mas abajo. Va
       DESPUES de las dos reglas que lo declaraban —la de `_20` para
       Reportes y la de este fichero para Vistas—, que es como gana: misma
       especificidad, mas tarde en la cascada. */
    .st-key-compras_tabs_row,
    .st-key-nav_rail_lateral {{
        left: 0 !important;
        width: calc(var(--rail-der-w) + 19px) !important;
        border-left: 19px solid transparent !important;
        background-clip: padding-box !important;
        box-shadow: inset 1px 0 0 0 var(--border) !important;
    }}

    :root.rails-scrolled .st-key-nav_rail_lateral {{
        opacity: 0;
        visibility: visible;
        pointer-events: auto;
        bottom: 8px !important;
        clip-path: inset(0 calc(100% - 19px - var(--rail-reserva)) 0 0);
        transition: opacity {_TRANS} linear {_ESPERA},
                    top {_TRANS} cubic-bezier(.4,0,.2,1),
                    visibility 0s linear 0s,
                    clip-path 0s linear calc({_TRANS} + {_ESPERA}),
                    bottom 0s linear calc({_TRANS} + {_ESPERA});
    }}
    :root.rails-scrolled:has({_DISP_COLUMNA}
        ) .st-key-nav_rail_lateral {{
        opacity: 1;
        bottom: auto !important;
        clip-path: inset(0);
        /* Al ENTRAR no hay espera, misma razon que la capa de la cabecera:
           aparecer tarde se siente roto. La espera vive en el reposo. */
        transition: opacity {_TRANS} linear,
                    top {_TRANS} cubic-bezier(.4,0,.2,1),
                    clip-path 0s linear 0s,
                    bottom 0s linear 0s;
    }}

    /* El rail de REPORTES, que es el activo arriba de todo, con el MISMO
       reposo. Acotado con `:not(.rails-scrolled)` y no por especificidad:
       habiendo bajado ya lo esconde su propia regla (unas lineas mas
       arriba), y dos mecanicas sobre el mismo elemento tienen que
       excluirse por construccion. */
    :root:not(.rails-scrolled) .st-key-compras_tabs_row {{
        opacity: 0;
        bottom: 8px !important;
        clip-path: inset(0 calc(100% - 19px - var(--rail-reserva)) 0 0);
        transition: opacity {_TRANS} linear {_ESPERA},
                    clip-path 0s linear calc({_TRANS} + {_ESPERA}),
                    bottom 0s linear calc({_TRANS} + {_ESPERA});
    }}
    :root:not(.rails-scrolled):has({_DISP_COLUMNA}
        ) .st-key-compras_tabs_row {{
        opacity: 1;
        bottom: auto !important;
        clip-path: inset(0);
        transition: opacity {_TRANS} linear,
                    clip-path 0s linear 0s,
                    bottom 0s linear 0s;
    }}

    /* Y EL ROTULO CON ELLOS. No hace falta recortarlo —ya es
       `pointer-events: none`, mismo caso que el sello de
       «Ultima actualizacion»— asi que le alcanza con la opacidad. Va
       acotado a `:not(.rails-scrolled)` porque al bajar lo esconde su
       propia regla: la columna sube a tocar la franja de reportes y la
       banda donde vivia deja de existir. */
    :root:not(.rails-scrolled) .st-key-rail_rotulo_rep {{
        opacity: 0;
        transition: opacity {_TRANS} linear {_ESPERA};
    }}
    :root:not(.rails-scrolled):has({_DISP_COLUMNA}
        ) .st-key-rail_rotulo_rep {{
        opacity: 1;
        transition: opacity {_TRANS} linear;
    }}

    /* ── LA TIRA DESPIERTA, PERO NO NAVEGA ────────────────────────────
       Medido el 2026-09-18 con `elementFromPoint(5, 400)`: lo que hay bajo
       la tira no es "el rail", es el BOTON de un reporte — los items
       arrancan en x=0 y el recorte no los corta, los recorta. O sea que un
       clic contra el borde izquierdo, con la columna todavia invisible,
       cambiaba de reporte. Arriba el mismo mecanismo se lo permite (su tira
       son 12px y sus botones estan ahi), pero aca la tira mide 850px de
       alto y pasa por encima de NUEVE botones: lo que alla es raro, aca
       pasa sola.

       `pointer-events: none` en los HIJOS y no en el rail: el hit-test cae
       entonces en el contenedor, que sigue en `auto`, asi que la tira sigue
       despertando la capa — lo unico que se pierde es poder activar a
       ciegas lo que todavia no se ve.

       Y en los hijos TODOS (`*`) y no en el `button`, que fue el primer
       intento: con `help=` puesto, Streamlit envuelve al boton en un
       `stTooltipHoverTarget` que NO es descendiente suyo sino su padre, y
       el punto medido caia justo ahi. Descendiente amplio a proposito, el
       mismo criterio que el bloque de `visibility: inherit` de arriba: lo
       que se quiere es capturar tambien a los widgets que se agreguen
       despues. */
    :root:not(.rails-scrolled) .st-key-compras_tabs_row *,
    :root.rails-scrolled .st-key-nav_rail_lateral * {{
        pointer-events: none;
    }}
    :root:has({_DISP_COLUMNA}
        ) :is(.st-key-compras_tabs_row, .st-key-nav_rail_lateral) * {{
        pointer-events: auto;
    }}

    /* EL PESTILLO TAMBIEN, en los dos estados del scroll: es la cabecera de
       la columna, no cromo suelto, y dejarlo encendido sobre el lienzo
       seria un boton flotando sin nada de que colgar.

       `pointer-events: none` en reposo y no un `clip-path`: el pestillo
       mide 33x33 y no tiene una tira que dejar viva —no es el que despierta
       la capa, la despierta el borde—, asi que lo unico que hace falta es
       que no se coma los clics de la tarjeta que tiene debajo. Y cuando la
       capa esta abierta vuelve a ser hit-testeable, que es lo que lo pone
       en `_DISP_COLUMNA`: sin eso, ir a plegar la columna la cerraria en el
       camino. */
    .st-key-rail_pestillo_abierto,
    .st-key-rail_pestillo_plegado {{
        opacity: 0;
        pointer-events: none;
        transition: opacity {_TRANS} linear {_ESPERA};
    }}
    :root:has({_DISP_COLUMNA}
        ) :is(.st-key-rail_pestillo_abierto,
              .st-key-rail_pestillo_plegado) {{
        opacity: 1;
        pointer-events: auto;
        transition: opacity {_TRANS} linear;
    }}

    /* Reposo OCULTO y sin `!important`, por el mismo motivo que el rail que
       encabeza (ver "DEGRADACION SEGURA" acá arriba): si el gancho no llega
       a montarse, el peor caso es que no pase nada — no dos rótulos
       superpuestos. */

    /* ── Los items del lateral ────────────────────────────────────────
       `navegacion.py` estila `.st-key-nav_rail` con clase EXACTA, asi que
       nada de aquello alcanza a `nav_rail_lateral`: su aspecto se define
       entero aca. Es un menu vertical, no una fila de tabs, asi que el
       activo se marca con una barra a la IZQUIERDA (no un subrayado). */
    .st-key-nav_rail_lateral [data-testid="stVerticalBlock"] {{
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        width: 100% !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stElementContainer"],
    .st-key-nav_rail_lateral [data-testid="stButton"] {{
        width: 100% !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button {{
        width: 100% !important;
        /* min-height y no height: el texto tiene que poder centrarse
           verticalmente adentro (align-items:center), no solo caber. Con
           height a secas el label quedaba pegado arriba del hueco. */
        min-height: 62px !important;              /* == navitem_ de Reportes, medido */
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
        margin: 0 !important;
        padding: 0 14px !important;
        border: none !important;
        border-radius: 0 !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
        box-shadow: none !important;
        font-weight: 400 !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button:hover {{
        background: var(--accent-tint) !important;
        color: var(--accent) !important;
    }}
    /* 2026-08-26, a pedido ("estar pegados a la izquierda, como el rail de
       reportes"): Streamlit mete un `div` interno entre el `<button>` y el
       `stMarkdownContainer` con `display:flex; justify-content:center` por
       default -- el MISMO wrapper que ya documenta y aplana
       `_20_compras_rail.py` para Reportes ("hay que aplanar TODOS los div
       descendientes del botón"), pero acá nunca se había hecho porque este
       rail nació sin ícono (sólo texto) y el centrado no se notaba con una
       sola palabra corta.
       Medido el bug real: con ícono + label, ese wrapper (250px) centraba
       su contenido (96px) empujando el ícono a 91px del borde izquierdo del
       botón — "Producto" arrancaba casi a mitad de fila en vez de pegado a
       la izquierda. `display:block` deja que el contenido tome su propio
       ancho en vez de estirarse a ocupar la fila entera para luego
       centrarse en ella. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button > div,
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stMarkdownContainer"] {{
        display: block !important;
        width: auto !important;
        max-width: 100% !important;
    }}
    /* El ITEM EN PANTALLA. La clase la pone el scrollspy de
       `base.py::_render_rail`, no `type="primary"`: lo que se marca es
       donde ESTAS, no el ultimo clic. Los botones se dibujan todos
       `secondary` justamente para que no haya dos marcas discutiendo.
       Barra por `inset` y no por `border-left`: no participa del box
       model, asi que el texto no se corre al activarse — mismo recurso
       que el subrayado de la franja horizontal. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla {{
        /* Mismo `--accent-light` que el activo del rail de Reportes
           (`_20_compras_rail.py`): las dos columnas ocupan el MISMO hueco y
           se turnan, asi que marcar distinto se leeria como dos componentes
           en vez de uno que cambio de contenido. */
        background: var(--accent-light) !important;
        color: var(--accent-deep) !important;
        box-shadow: inset 3px 0 0 0 var(--accent) !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button.vista-en-pantalla p {{
        font-weight: 500 !important;
    }}
    /* ── CABECERA: el reporte que estas viendo ────────────────────────
       Esta columna reemplaza a la lista de Reportes al bajar, y con ella se
       iba el nombre del reporte. La cabecera lo devuelve con sus KPIs —
       mismo patron que las fichas de MSN Dinero, que encabezan su rail con
       la entidad y debajo listan sus secciones.
       El separador es un `border-bottom` y no un `<hr>`: no agrega un nodo
       que despues haya que espaciar. */
    .st-key-nav_rail_lateral .rail-cab {{
        /* MISMO ALTO que un item de vista (62px medidos, 2026-08-25, a
           pedido). Se consigue con los interlineados de abajo, no con un
           `height`: las tres lineas traian el line-height por defecto
           (21+22+19 = 62 solo de texto) y el bloque se iba a 80px. */
        padding: 2px 14px 10px 14px !important;
        margin-bottom: 8px !important;
        border-bottom: 1px solid var(--border) !important;
    }}
    .st-key-nav_rail_lateral .rail-cab-nom {{
        /* 1rem = 16px, el MISMO cuerpo que los items de vista de abajo
           (2026-08-25, a pedido: "se ve muy grande"). Lo que la separa como
           cabecera es el peso y el hairline de abajo, no el tamaño — con
           16.8px se leia como otro nivel de jerarquia y competia con el
           contenido. */
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        line-height: 1.2 !important;
    }}
    /* Los KPIs en su propio renglon, chicos y apagados: son contexto, no el
       titulo. Mismo criterio que el segundo renglon de los items de
       Reportes (`navegacion.py::_CSS_KPIS`). */
    .st-key-nav_rail_lateral .rail-cab-kpi {{
        /* `block` y no `inline-block`: un inline-block se sienta sobre una
           linea de texto y arrastra el espacio de los descendentes — 10px
           fantasma que no aparecen en la suma de las piezas y hacian que el
           bloque midiera 71 en vez de 62 (medido 2026-08-25). Igual va en su
           propio renglon, asi que no se pierde nada. */
        display: block !important;
        font-size: .85rem !important;
        font-weight: 600 !important;
        color: var(--accent-deep) !important;
        line-height: 1.15 !important;
        margin-top: 1px !important;
    }}
    .st-key-nav_rail_lateral .rail-cab-kpi.kpi-neg {{
        color: var(--danger-text) !important;
    }}
    .st-key-nav_rail_lateral .rail-cab-kpi2 {{
        display: block !important;
        font-size: .74rem !important;
        color: var(--text-secondary) !important;
        line-height: 1.1 !important;
    }}

    /* El icono material del item. Hereda el color del boton (o sea que
       sigue solo al estado activo/reposo/hover) y va un punto mas chico que
       el del rail de Reportes, que tiene el icono ARRIBA del texto y puede
       permitirselo mas grande; aca van en linea. */
    .st-key-nav_rail_lateral [data-testid="stButton"] button [data-testid="stIconMaterial"] {{
        font-size: 19px !important;
        margin-right: 10px !important;
        color: inherit !important;
        flex: 0 0 auto !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stButton"] button p {{
        margin: 0 !important;
        /* 1rem = 16px, el mismo cuerpo que los items del rail de Reportes
           (medido en el navegador). Venia en .82rem y se leia mas chica
           justo cuando la columna cambia de contenido, que es cuando el
           salto se nota. */
        font-size: 1rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }}
    /* ── HAIRLINE entre cada ítem ──────────────────────────────────────
       2026-08-26, a pedido ("tambien debe tener lineas que lo separan...
       como el rail de reportes"): mismo recurso que `.st-key-
       graf_tipo_chips > div` en `_20_compras_rail.py` — un hairline por
       ítem, apagado en el último. La diferencia de selector (`:has(...)`
       en vez de `> div`) es porque acá los ítems NO están envueltos en un
       `navitem_<slug>` propio (Reportes sí); el `stElementContainer` del
       propio `st.button` hace de unidad. `:has([data-testid="stButton"])`
       excluye a la cabecera (`.rail-cab`, un `st.markdown` sin botón) y al
       separador de "destino aparte" de abajo (tampoco tiene botón), que
       ya ponen su propia línea y no necesitan una segunda. */
    .st-key-nav_rail_lateral [data-testid="stElementContainer"]:has([data-testid="stButton"]) {{
        border-bottom: 1px solid var(--border) !important;
    }}
    .st-key-nav_rail_lateral [data-testid="stElementContainer"]:has([data-testid="stButton"]):last-child {{
        border-bottom: none !important;
    }}
    /* ── SEPARADOR: scroll-to vs destino aparte ───────────────────────
       2026-08-26, a pedido ("el reporte de documentos sunat no aparece
       al hacer scroll"): no era un bug, era que el rail no avisaba que
       Documentos SUNAT es un DESTINO APARTE (`base.py::_render_rail` lo
       dibuja cuando la membresía a `secciones` cambia de un ítem al
       siguiente). Con el hairline de arriba ahora separando TODOS los
       ítems por igual, este separador extra es lo único que sigue
       marcando esa frontera como distinta — sin él, Documentos se leería
       como un ítem más de la pila. Mismo recurso que `.rail-cab`: un
       `border-top` en un div vacío, no un `<hr>` que después haya que
       espaciar. */
    .st-key-nav_rail_lateral .nav-rail-lat-sep {{
        border-top: 1px solid var(--border) !important;
        margin: 6px 14px !important;
    }}
}}

/* ── LOS ENVOLTORIOS NO APORTAN GAP ───────────────────────────────────
   Los CUATRO cromos fijos de la cabecera —la franja de vistas
   (`nav_rail`), los chips de Familia/Subfamilia (`chips_ajuste_tabla`), el
   rail lateral y el gancho— no dibujan NADA en el flujo: son
   `position: fixed`, verificado uno por uno. Pero Streamlit los envuelve en
   un `stLayoutWrapper` y el bloque vertical padre le da a cada uno sus 16px
   de `gap`. Cuatro envoltorios de alto 0 = 64px de aire empujando la
   primera tarjeta hacia abajo — medido 2026-08-25: la seccion arrancaba en
   y=176 con la franja terminando en 96.

   Los dos ultimos son cromo COMPARTIDO por los 9 reportes; se incluyen
   igual porque la condicion que los hace elegibles (contenido fuera del
   flujo) vale en todos, no solo en Compras.

   `display: contents` y no `display: none`: none BORRA el subarbol y con el
   el rail, que si tiene que dibujarse (sale del flujo por su
   `position: fixed`, no por estar oculto). `contents` hace desaparecer la
   CAJA del envoltorio dejando vivos a los hijos: sin caja no hay flex item,
   y sin flex item no hay gap. */
/* Por `data-testid` y NO por `.stLayoutWrapper`: el envoltorio lleva ese
   testid pero su `class` son hashes de emotion, que cambian entre versiones
   de Streamlit. Apuntar a la clase no matcheaba nada (primer intento). */
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-nav_rail_lateral"]),
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-rail_scroll_hook"]),
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-nav_rail"]),
[data-testid="stLayoutWrapper"]:has(> [class*="st-key-chips_ajuste_tabla"]) {{
    display: contents !important;
}}

/* El contenedor del gancho no pinta nada: es un iframe de alto 0 que solo
   existe para correr el JS. Va FUERA de los @media —en los dos anchos— y no
   dentro del de escritorio, que fue el primer intento: en movil quedaba un
   contenedor de 327px de ancho en el flujo. Mide 0 de alto, asi que no se
   veia; se encontro midiendo, no mirando. */
.st-key-rail_scroll_hook {{
    display: none !important;
}}

/* ── ESCRITORIO: LA FRANJA DE VISTAS NO SE DIBUJA (2026-09-14) ───────
   A pedido, con captura de Movimientos: «eliminemos la segunda franja
   superior, donde salen las vistas y sus kpis, ojo solo la franja, no las
   vistas» — y la de reportes se queda. Se van las DOS mitades del cruce
   que ocupaban la banda de 40px bajo la de reportes: las vistas
   (`nav_rail`) y los KPIs del reporte (`nav_franja_kpis`). Las vistas no
   se pierden: son las secciones de la pila, y su lista vive en el rail
   lateral, que toma la columna al bajar.

   Lo que vivia en esa banda sin ser ella —la fecha, Filtros, el stepper
   del corte— subio a la franja de reportes (`_50_fecha.py`). Y la vista
   que no tenia mas salida que esta franja —un destino aparte como
   Documentos SUNAT, sin pila que scrollear— pasa sola la columna a Vistas
   (`base.py::_render_rail`, el `FUERA` del gancho).

   `display: none` y no el reposo de la capa: ya no hay estado en que se
   vean, asi que no hay transicion que cuidar. Desde 901 y no desde 769:
   entre los dos la franja de reportes ocupa el ancho entero, la fecha y
   Filtros no tienen donde subir, y ahi la franja se queda como estaba —
   con las reglas de la capa de mas arriba. Regla #419. */
/* La clase DUPLICADA no es un descuido: `navegacion.py::_CSS_FRANJA_VISTAS`
   le pone `display:flex !important` a `.st-key-nav_rail` con la misma
   especificidad, y se inyecta DESPUES que `estilos/` (lo emite
   `_render_rail` en cada render), asi que con clase simple ganaba ella.
   Medido: la franja seguia en `display: flex` con esta regla aplicando. */
@media screen and (min-width: 901px) {{
    .st-key-nav_rail.st-key-nav_rail,
    .st-key-nav_franja_kpis.st-key-nav_franja_kpis {{
        display: none !important;
    }}
}}

/* En movil no hay columna izquierda: el lateral no se dibuja nunca. El
   rail de vistas sigue siendo la franja de arriba, como hasta ahora. */
@media screen and (max-width: 768px) {{
    .st-key-nav_rail_lateral {{ display: none; }}
}}
"""
