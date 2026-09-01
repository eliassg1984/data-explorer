"""estilos._20_compras_rail - Rail vertical de Compras (borde derecho, secciones por categoria) y su variante movil, donde el rail pasa a ser tira horizontal.

Extraido de estilos.py (lineas 564-879 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* SECCIONES DE COMPRAS — RAIL VERTICAL (borde derecho, apilado)         */
    /* Variante 2: cabecera neutra "Compras / Gráficos" arriba + secciones    */
    /* agrupadas por categoría (Dimensión, Precios, Cantidad, Más). Cada     */
    /* ítem es un st.button con dot a la izquierda; el activo se marca con   */
    /* type="primary" (accent-light + barra izquierda accent). El contenedor  */
    /* solo existe en Compras: este CSS no afecta otros reportes.            */
    /* =================================================================== */
    .st-key-compras_tabs_row {
        position: fixed !important;
        /* Rail arranca a la altura de la tarjeta (por debajo de la topbar de
           Streamlit + la fila de chips/fecha), no desde el borde superior.
           2026-08-09: 60px -> 66px. Va ACOPLADO con el margin-top negativo
           de la primera tarjeta (más abajo en este mismo archivo): los dos
           tienen que dar el mismo top o la tarjeta y el rail arrancan en
           líneas distintas — pasó con la barra de 46px, la tarjeta quedaba
           en y=57 contra el rail en y=60 y se notaba en la esquina
           superior derecha. Si se cambia uno, medir el otro.
           2026-08-13: 66px -> 74px, a pedido (seguía viéndose pegado a la
           franja superior). Los 3 números acoplados (este top, el
           max-height de abajo, y los margin-top negativos de las tarjetas
           más abajo en este archivo) se corrieron los mismos 8px juntos.
           2026-08-18: los 74px pasan a contarse DESPUÉS de la barra de
           navegación superior (--nav-top-alto), que también es fija y le
           caería encima. En móvil la variable vale 0 y la cuenta vuelve a
           los 74 de siempre. */
        /* 2026-08-19: 74px -> 8px. El rail arranca a la MISMA altura que los
           controles de la franja (que usan este mismo `+ 8px`), no 66px por
           debajo. Es el modelo de MSN Dinero, que motivó el cambio: la barra
           lateral ocupa su columna desde arriba y la franja de contexto vive
           a su derecha, no por encima.
           Esto sólo es posible junto con el cambio hermano de
           _40_ajuste_franja.py: la banda blanca de la franja iba de borde a
           borde (left:0, y=40..90) y el rail se le habría montado encima.
           Ahora esa banda arranca después de la columna del rail. Los dos
           cambios van juntos o no van. */
        /* 2026-08-22: el `+ 8px` baja a `- 2px` (10px mas arriba), a pedido.
           Viene de un `transform: translate(4px,-10px)` del modo diseno, que
           NO se copio tal cual: el rail ya es position:fixed, asi que un
           transform encima seria redundante Y capturaria a sus hijos fixed
           (regla #156). Se traduce al `top`/`left` que ya existen. */
        /* 2026-08-26: `- 2px` -> `0`, a pedido ("que este a esta altura, mas
           arriba"), otra vez a partir de un arrastre en modo diseno
           (transform medido: translate(6px,-40px), redondeado al 0 exacto —
           el -2px de mas que daba el arrastre era overshoot del mouse, no un
           valor buscado). Tercera vuelta de la misma direccion (74->8->-2,
           ver arriba); esta vez llega al borde.
           Medido ANTES de tocarlo: el rail mide 448px de contenido con
           672px de max-height disponibles (sobran 224px) — subirlo no
           gana lugar para mas items, es alineacion pura con el titulo de
           la franja (`Sapiens (Compras)`, que vive en x>=323, fuera del
           ancho de este rail que termina en x=299 — nunca se pisan). Y el
           color de fondo del hueco que se recupera (`--bg-primary`
           #faf9fb) es casi identico al del rail (`--bg-card` #ffffff): no
           hay salto de color que disimular.
           `max-height` pierde el termino `- var(--nav-top-alto)`: ya no
           hay top que "devolver" (el rail arranca en 0, no en
           nav-top-alto), asi que el techo de seguridad pasa a medirse
           desde el borde de arriba de la pantalla directo. */
        /* 2026-08-31: `0` -> `47px`, a pedido, otra vez desde un arrastre en
           modo diseno (`transform: translate(1px,47px)`). Como las dos veces
           anteriores, el transform NO se copia tal cual: el rail ya es
           position:fixed —un transform encima seria redundante Y capturaria
           a sus hijos fixed (regla #156)—, asi que se traduce al `top` que
           ya existe. El 1px de X se descarta por overshoot del mouse, mismo
           criterio que el -2px del 2026-08-26; `left` no se toca.
           Cuarta vuelta de la serie (74 -> 8 -> -2 -> 0 -> 47): esta vez el
           rail BAJA y vuelve a arrancar por debajo de la franja superior.
           Arrastra dos numeros con el:
           · `max-height` recupera el termino del top. Con `100vh - 8px`
             medido desde y=47 el rail podia pasarse 47px del borde de
             abajo; el techo se mide otra vez desde donde arranca.
           · el gemelo `nav_rail_lateral` de _26_rails_scroll.py, que ocupa
             ESTE MISMO hueco cuando se scrollea. Si solo se mueve uno, el
             cruce se ve como que la columna salta 47px en vez de cambiar de
             contenido. */
        top: 47px !important;
        /* 2026-08-18, a pedido: el rail pasa del borde DERECHO al IZQUIERDO.
           Es el sitio que dejó libre el rail de navegación al convertirse en
           la franja superior (--nav-top-alto) unos commits antes: la columna
           izquierda quedó vacía y el rail de vistas volvió a ella.
           Las variables siguen llamándose `--rail-der-*`: el nombre quedó
           histórico y renombrarlas toca ~15 sitios en 4 ficheros más un
           test. Se dejó anotado en _00_base.py en vez de hacerlo a medias. */
        left: 19px !important;             /* 15 + 4 del ajuste del 2026-08-22 (era el translate X) */
        /* El ancho es VARIABLE desde el 2026-08-15 (nació para el pestillo
           que plegaba este rail; retirado 2026-08-26, ver _00_base.py — la
           variable queda, ahora con un solo valor fijo). Hasta esa fecha
           había DOS `width` en este mismo bloque, 84px unas líneas más
           abajo, que ganaba por ir después — la variable estaba puesta y
           no hacía nada. */
        width: var(--rail-der-w) !important;
        overflow-x: hidden !important;
        /* 2026-08-13: de "bottom:0 + height:calc(100vh-66px)" (fuerza el
           rail a ocupar TODO el alto disponible, aunque tenga 3 items) a
           altura de CONTENIDO — mismo pedido y mismo fix que ya se le hizo
           al rail izquierdo (navegacion.py::nav_rail, ver arquitectura.md
           regla #99 y los commits de esta misma fecha): "el rail debe
           reducirse, no ser tan largo". Sin `bottom`, height:auto mide el
           contenido; max-height sigue de red de seguridad si algún día hay
           tantas vistas que no entran (activa el overflow-y:auto de abajo
           en vez de desbordar). */
        height: auto !important;
        max-height: calc(100vh - 47px - 8px) !important;
        z-index: 900 !important;
        overflow-y: auto !important;
        margin: 0 !important;
        padding: 8px 0 16px 0 !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        /* 2026-08-31: 12px -> 0, en el mismo pedido que el `top`. Deja de
           copiar las esquinas de la tarjeta a proposito. Va tambien en el
           gemelo de _26_rails_scroll.py por el mismo motivo que el top. */
        border-radius: 0 !important;
        box-shadow: none !important;       /* sin sombra: integrada al borde */
        scrollbar-width: none !important;
    }
    .st-key-compras_tabs_row::-webkit-scrollbar { display: none !important; }

    /* ── RÓTULO DE LA COLUMNA (2026-08-31) ─────────────────────────────
       "Reportes" / "Vistas" en el hueco de 47px que el rail dejó libre
       arriba al bajar (ver el `top`). Va FUERA de la tarjeta, sobre el
       lienzo, como el "Vistos recientemente" que encabeza la lista de MSN
       Dinero — el mismo modelo del que salió esta columna entera.

       Los DOS rótulos comparten geometría porque los dos railes comparten
       hueco: `rail_rotulo_rep` lo dibuja navegacion.py y `rail_rotulo_vis`
       graficos/base.py, y el cruce entre ambos vive en _26_rails_scroll.py
       con el mismo `rails-scrolled` que cruza a los railes. Tercer par de
       literales acoplados a los del rail (top/left/width): el precio ya
       asumido de esta geometría, igual que el rail lateral.

       `position:fixed` va sobre el CONTENEDOR y no sobre el <div> de
       adentro: así sale del flujo el bloque entero y no queda el hueco de
       un flex item vacío en el main. Mismo recurso que el rail. */
    .st-key-rail_rotulo_rep,
    .st-key-rail_rotulo_vis {
        position: fixed !important;
        /* 14px: el rótulo ocupa y=14..33 y deja 14px de aire hasta el borde
           del rail (y=47), el mismo respiro que tiene por arriba. */
        top: 14px !important;
        left: 19px !important;              /* == el rail */
        width: var(--rail-der-w) !important;
        margin: 0 !important;
        /* 4px de sangría: alinea con el borde interno de la tarjeta (x=20
           medido, el rail no tiene padding horizontal), no con el texto de
           los ítems (x=56, que arranca después del icono). Encabeza la
           COLUMNA, no la lista. */
        padding: 0 4px !important;
        z-index: 902 !important;            /* 1 sobre el rail de Vistas (901) */
        pointer-events: none !important;    /* es un rótulo, no un control */
    }
    .st-key-rail_rotulo_rep .rail-rotulo,
    .st-key-rail_rotulo_vis .rail-rotulo {
        /* Un punto por debajo del ítem del rail (1rem) y con más peso: es
           una etiqueta de la columna, no el primero de sus renglones.
           Mismo criterio que `.rail-cab-nom` en _26_rails_scroll.py. */
        font-size: .9rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        line-height: 1.35 !important;
    }

    /* Reserva el ancho de la franja solo en Compras (no toca otros reportes):
       el :has() detecta el rail dentro del contenedor principal. */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row),
    .block-container:has(.st-key-compras_tabs_row) {
        /* La reserva sigue al rail: era `padding-right` mientras vivía a la
           derecha. El otro lado vuelve solo a los 80px de base. */
        padding-left: var(--rail-der-res) !important;    /* rail + aire + offset (_00_base) */
    }

    /* Badge de categoría + separador entre secciones */
    .st-key-compras_tabs_row .rail-cat-badge {
        font-size: 8.5px !important;
        font-weight: 600 !important;
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        padding: 4px 10px 1px !important;
    }
    .st-key-compras_tabs_row .rail-sep {
        height: 0.5px !important;
        background: var(--border) !important;
        margin: 2px 8px !important;
    }

    /* Subir las TARJETAS (no los chips fijos): recupera el hueco que dejó la
       antigua barra horizontal de pestañas y la franja blanca. Se aplica
       solo a los contenedores que sí viven en el flujo del dashboard de
       Compras. Ahora que la franja es transparente el gap se ve mas, por
       eso -100 en vez de -60. */
    /* Solo la PRIMERA tarjeta sube bajo el rail. En Compras es
       compras_prov_drill_wrap; en Ajuste (ahora APILADO) es la tarjeta izq
       (gráfico principal). La tarjeta der (panel de análisis) NO lleva el
       jalón: va en flujo debajo, y un -68px extra la solaparía con la de
       arriba. Reglas separadas (mismo valor base -60px) para poder afinar
       cada tarjeta por su lado sin mover la otra. */
    /* 2026-08-09: -60 -> -51 y -65 -> -56 (9px menos de jalón cada uno).
       Con la barra superior en 46px la tarjeta quedaba a 11px de ella y,
       peor, 3px MÁS ARRIBA que el rail derecho (tarjeta en y=57, rail en
       y=60) — se veía en la esquina superior derecha. Ahora las dos
       arrancan en y=66: ~20px de aire bajo la barra, que es lo que había
       antes de subirla, y tarjeta y rail en la misma línea. Los tres
       números (top del rail, estos dos margin) van juntos.
       2026-08-13: -51 -> -43 y -56 -> -48 (8px menos de jalón cada uno),
       en sync con el top:66->74 del rail de arriba — las dos siguen
       arrancando en la misma línea, ahora 8px más abajo. */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-compras_prov_drill_wrap {
        margin-top: -43px !important;
    }
    /* 2026-08-17, a pedido: ensanchar la tarjeta para que las columnas de
       proveedor.py (ranking-tabla + evolución; nació pensado para 3 —
       ranking, tabla y evolución separadas — antes de que las dos
       primeras se unieran en una sola tabla el mismo día) entren sin
       apretarse. Medido en vivo (preview local, getBoundingClientRect): lo
       reservado a cada lado es MÁS de lo que hace falta para no pisar el
       rail derecho, que empieza a `--rail-der-res` del borde (deja 64px de
       sobra). Son PX FIJOS, no dependen del viewport, así que valen igual
       en cualquier ancho de escritorio.
       2026-08-18, al retirarse el rail izquierdo: el jalón izquierdo era
       -60px y estaba medido contra ese rail (la tarjeta arrancaba en 170 e
       iba a 110, a 20px del rail que terminaba en x=90). Sin rail, la
       tarjeta arranca ~90px más a la izquierda y ese mismo -60 la dejaba en
       x=20, descolgada de todo lo demás. Ahora el jalón es -16px, que la
       alinea con el borde izquierdo de los chips de la franja (x=64,
       _40_ajuste_franja.py) en vez de con un rail que ya no está.
         margin-left  -16px  (80 -> 64, la línea de los chips)
         width        +60px  (16 del izq. + 44 del der., hasta ~20px del
                              rail der.)
       `max-width` es OBLIGATORIO acá: Streamlit le pone a este mismo nodo
       `max-width:100%` en su propio CSS emotion (sin !important, pero como
       nuestro `width` de abajo tampoco lo pisaba, el ancho quedaba
       clampeado de vuelta a 1107px — medido en vivo, el `width` de acá NO
       alcanzaba solo).
       min-width:901px es OBLIGATORIO: en móvil el padding del contenedor es
       otro y el jalón negativo empuja la tarjeta fuera del viewport. 901 y
       no 769 para quedar del mismo lado que el breakpoint de
       compras_tabs_row (arriba, max-width: 900px) y no abrir una franja
       769-900px sin decidir. */
    @media (min-width: 901px) {
        [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-compras_prov_drill_wrap {
            /* 2026-08-18, al pasar el rail a la izquierda: el jalón vuelve
               a medirse CONTRA EL RAIL, como antes de que el izquierdo se
               retirara. Medido en vivo: con -16 la tarjeta arrancaba en 137
               (38px del rail, que termina en 99) y sobraban 46px a la
               derecha — corrida ~18px respecto del espejo exacto. Con -34
               queda en 119: 20px del rail (los mismos que tenía del lado
               derecho) y 64 hasta el borde (los mismos que tenía a la
               izquierda). El layout es el de antes, reflejado. */
            /* 2026-08-19: el jalon izquierdo SE VA. Existia para ganar
               ancho, y lo ganaba rompiendo la reja: la tarjeta arrancaba
               34px antes que la franja de arriba. Ahora las dos arrancan en
               el borde del contenido (ver el ancla de la franja en
               estilos/_50_fecha.py) y la tarjeta paga esos 34px de ancho.
               Y el ensanche a la derecha tambien: medido, `calc(100% + 16px)`
               no daba el mismo sobrante en 1280 que en 1440 (el `max-width`
               resuelve su 100% contra otra caja), asi que el borde derecho
               de la tarjeta bailaba y nada podia alinearse con el. La
               tarjeta ES la caja de contenido: sin width propio, sus dos
               bordes son los del contenedor en cualquier viewport. */
        }
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) [class*="st-key-ajuste_graf_card_izq_"] {
        margin-top: -48px !important;
    }
    /* La tarjeta der (panel lateral, p.ej. Mayor cantidad/Precio más alto de
       Inventario o los mini-tops de Compras) es hermana de la izq en la
       misma fila — mismo jalón, si no arranca 56px más abajo que su
       hermana y las dos tarjetas quedan escalonadas (se notó en Inventario
       Por área/Por familia: la izq creció con el detalle del click-drill y
       el desnivel saltó a la vista). Reseteada a 0 en el media query de
       abajo, igual que la izq. */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) [class*="st-key-ajuste_graf_card_der_"] {
        margin-top: -48px !important;
    }
    /* Excepción: Salidas mete una fila de KPIs (st.metric x3) EN FLUJO justo
       arriba de esta tarjeta — a diferencia de Ajuste/Compras/Ventas/
       Inventario, donde encima solo hay chips y el -80px recupera un hueco
       vacío. En Salidas no hay tal hueco: el -80px se comía la fila de
       KPIs, y el título del Plotly (p.ej. el donut de "Tipo descargo")
       quedaba pintado ENCIMA de los números de REGISTROS/CANTIDAD/
       VALORIZADO (ver arquitectura.md regla #38). Selector con la MISMA
       especificidad que el de arriba + !important en ambos → gana por ir
       DESPUÉS en el archivo (ver convención de _SECCIONES). */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-ajuste_graf_card_izq_sal {
        margin-top: 0 !important;
    }

/* Compras hereda el cristal esmerilado del DEFAULT
       (estilos/_40_ajuste_franja.py) sin duplicar nada — scopeado con
       :has(.st-key-app_reporte_compras), un marker inyectado desde app.py
       cuando reporte=="Compras". Antes usaba :has(.st-key-compras_tabs_row),
       pero esa key es del rail compartido y matcheaba tambien Ajuste. Ver
       arquitectura.md regla #16. El left:170px/right:163px del default ya
       despegan la tarjeta del rail derecho de Compras (84px + 15px offset
       = 99px) con margen de sobra, así que acá no hace falta tocarlos.

       2026-08-06: Compras tenía acá SUS PROPIOS height:34px (la franja) y
       top:3px (fecha_ajuste_pill/chips_ajuste_tabla, para que no asomaran
       por el borde inferior de esa franja más baja — el default de 50px/
       top:8px dejaba 14px de sobra, pero 34px/top:8px se pasaba por 2px).
       2026-08-07: gustó más que el default de 50px, así que se
       universalizó — los 8 reportes usan 34px/top:3px en desktop ahora
       (ver _40_ajuste_franja.py::before y el bloque @media(min-width:901px)
       de _50_fecha.py). Acá ya no queda nada que duplicar.

       Solo queda 1 ajuste propio de Compras: padding-top de
       fila_ajuste_top (el WRAPPER, no la franja) — más chico porque el
       rail de Compras empieza a los 60px y ya tiene su propia cabecera. */
    [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras) .st-key-fila_ajuste_top {
        padding-top: 2px !important;
    }

    .st-key-graf_tipo_chips {
        margin: 0 !important;
        overflow: visible !important;
        border-bottom: none !important;
        padding: 0 !important;
    }
    /* NUCLEAR: cero margin/padding/gap en TODO descendiente del rail excepto
       el <button> y el texto. Los valores del KPI (navegacion.py,
       .nav-kpis-valores/-primario/-secundario) NO necesitan excepción acá
       pese a llevar su propio CSS en `_CSS_KPIS`: van con `position:
       absolute` (fuera del flujo, el margin/padding de layout no les
       aplica) y `-primario`/`-secundario` son `<span>`, ya cubiertos por
       el `:not(span)` de abajo. Especificidad reforzada duplicando la
       clase del contenedor (.st-key-graf_tipo_chips.st-key-graf_tipo_chips)
       para ganarle a cualquier regla base de Streamlit con clase única +
       !important. */
    .st-key-graf_tipo_chips.st-key-graf_tipo_chips
        *:not(button):not(p):not(span):not(.rail-cat-badge):not(.rail-sep) {
        margin: 0 !important;
        padding: 0 !important;
        gap: 0 !important;
        row-gap: 0 !important;
        min-height: 0 !important;
        min-width: 0 !important;
    }
    /* El wrapper directo del rail también: sin gap entre hijos (categorías +
       botones). Streamlit lo aplica al stVerticalBlock, pero el div raíz
       .st-key-graf_tipo_chips también puede tener display:flex con gap. */
    .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
        display: flex !important;
        flex-direction: column !important;
        gap: 0 !important;
        row-gap: 0 !important;
    }
    /* Cada ítem del rail: botón estilo lista, sin borde ni fondo por defecto.
       Un dot a la izquierda (::before) precede al texto. border-left:3px
       transparent reservado en base = el texto no se corre cuando pasa a
       activo (activo reemplaza el transparent por accent).

       Combinador DESCENDIENTE (` `), no hijo directo (`>`): desde que Reportes
       usa `help=` en cada st.button (navegacion.py, regla #170), Streamlit
       mete `div > span.stTooltipIcon > span.stTooltipHoverTarget` entre
       `.stButton` y el `<button>` real (mismo wrapper que dispara la "copia
       fantasma", ver bloque DEFENSA ANTI-TOOLTIP-FANTASMA más abajo). Con `>`
       NINGUNA de estas reglas matcheaba — ni las del ítem activo — y el rail
       corría con el look default de Streamlit (button[kind] de _00_base.py)
       sin que se notara a simple vista. Se detectó recién cuando el usuario
       pidió `border-radius:0` para todos los ítems: medir en vivo mostró
       10px/8px reales (ni el 0 del activo ni el 0 del inactivo aplicaban).
       Ver arquitectura.md regla #172. */
    .st-key-graf_tipo_chips [data-testid="stButton"] button,
    .st-key-graf_tipo_chips .stButton button {
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
        width: 100% !important;
        min-height: 0 !important;
        border: none !important;
        border-left: 3px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
        padding: 1px 10px 1px 7px !important;   /* 7 + border 3 = 10 alineado */
        gap: 0 !important;
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
        box-shadow: none !important;
        position: relative !important;
        transition: background 0.12s !important;
    }
    /* Viñeta eliminada — la barra izquierda de acento (border-left activo)
       ya marca el ítem seleccionado; el dot sumaba ruido sin agregar info. */
    .st-key-graf_tipo_chips [data-testid="stButton"] button::before,
    .st-key-graf_tipo_chips .stButton button::before {
        display: none !important;
    }
    /* Wrappers del label — NO expandirse (si crecen con flex:1 el texto queda
       flotando al centro del hueco sobrante). Streamlit mete un <div emotion>
       intermedio entre el <button> y el stMarkdownContainer, con display:flex
       y justify-content:center por default → hay que aplanar TODOS los div
       descendientes del botón. */
    .st-key-graf_tipo_chips [data-testid="stButton"] button > div,
    .st-key-graf_tipo_chips .stButton button > div,
    .st-key-graf_tipo_chips [data-testid="stButton"] button [data-testid="stMarkdownContainer"],
    .st-key-graf_tipo_chips .stButton button [data-testid="stMarkdownContainer"] {
        display: block !important;             /* deja al <p> tomar su ancho */
        flex: 0 1 auto !important;
        width: auto !important;
        max-width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] button p,
    .st-key-graf_tipo_chips .stButton button p {
        margin: 0 !important;
        padding: 0 !important;
        display: block !important;
        font-size: 11px !important;
        line-height: 1.15 !important;
        white-space: normal !important;
        text-align: left !important;
        font-weight: inherit !important;
        color: inherit !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] button:hover,
    .st-key-graf_tipo_chips .stButton button:hover {
        background: var(--accent-tint) !important;   /* hover suave */
        color: var(--accent-deep) !important;
    }
    /* Activo: kind="primary" del st.button */
    .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"],
    .st-key-graf_tipo_chips .stButton button[kind="primary"] {
        background: var(--accent-light) !important;   /* activo saturado */
        color: var(--accent-deep) !important;
        font-weight: 500 !important;
        border-left-color: var(--accent) !important;  /* pinta el reservado */
    }

    /* PIE DEL RAIL — Refrescar, la única ACCIÓN (no un ítem del rail). Esta
       regla es de POSICIÓN (key `rail_refresh`), no le importa si el rail
       dibuja Vistas o Reportes — no se tocó en la inversión del 2026-08-22
       (regla #170). Historial: vino de la franja superior de navegación a
       este rail el 2026-08-22 (regla #164, cuando el rail todavía era de
       Vistas); hoy lo dibuja `navegacion.py::inject_navegacion` al pie del
       rail de Reportes, mismo criterio ("la acción vive al pie del rail
       VERTICAL, sea cual sea su contenido"). Fuera de `graf_tipo_chips` a
       propósito (regla #6 — ese contenedor estila TODO lo que cuelga de
       él como ítem de lista; Refrescar no lo es). */
    .st-key-rail_refresh {
        width: 100% !important;
        display: flex !important;
        margin: 2px 0 0 0 !important;
        padding: 0 7px !important;
    }
    .st-key-rail_refresh button {
        width: 100% !important;
        min-height: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 6px !important;
        padding: 5px 3px !important;
        border: none !important;
        border-radius: 6px !important;
        background: transparent !important;
        color: var(--text-muted) !important;
        box-shadow: none !important;
        font-weight: 400 !important;
        transition: background 0.12s !important;
    }
    .st-key-rail_refresh button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    .st-key-rail_refresh button p {
        margin: 0 !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        font-size: 11px !important;
        line-height: 1.15 !important;
        font-weight: inherit !important;
        color: inherit !important;
        white-space: normal !important;
    }
    /* El ícono va INLINE en el label (":material/refresh: Refrescar"), no
       por `icon=` — el shortcode dentro del string. Streamlit
       lo renderiza como `span[role="img"]` dentro del `<p>`, NO como
       `[data-testid="stIconMaterial"]` (ese selector es el de los ítems del
       rail que sí usan `icon=`, ver `graf_tipo_chips` arriba). */
    .st-key-rail_refresh button p span[role="img"] {
        font-size: 15px !important;
        line-height: 1 !important;
    }

    /* =================================================================== */
    /* RAIL EN MÓVIL (<=900px): el rail vertical fijo de 270px + su reserva  */
    /* de ancho se comen casi la mitad de un viewport de 375px. En móvil el */
    /* rail deja de estar fijo y se vuelve una tira horizontal scrollable   */
    /* arriba del dashboard; los botones quedan en fila (chips) y el        */
    /* contenido recupera todo el ancho. Scopeado con                      */
    /* :has(.st-key-compras_tabs_row) — la key del RAIL, que desde el       */
    /* 2026-08-22 dibuja Reportes (antes Vistas, ver arquitectura.md regla  */
    /* #170): aplica siempre, en TODOS los reportes, porque Reportes vive   */
    /* en este contenedor sin excepción — a diferencia de cuando era el     */
    /* rail de Vistas, que sólo dibujaban los dashboards que lo llamaban.   */
    /* =================================================================== */
    @media (max-width: 900px) {
        /* El contenido recupera el ancho: fuera la reserva del rail.
           2026-08-18: esta línea decía `padding-right` porque la reserva
           vivía a la derecha. Al pasar el rail a la izquierda dejó de
           anular nada y los 153px se quedaban puestos en un viewport de
           375 — medido: el contenido arrancaba en x=153, o sea 40% de la
           pantalla comida por un rail que en móvil ni siquiera es una
           columna. Anular AMBOS lados es lo correcto: la regla no tiene
           que volver a tocarse si el rail vuelve a cambiar de borde. */
        [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row),
        .block-container:has(.st-key-compras_tabs_row) {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* Rail: de columna fija a tira horizontal en el flujo del documento. */
        .st-key-compras_tabs_row {
            position: static !important;
            width: 100% !important;
            height: auto !important;
            top: auto !important; bottom: auto !important;
            left: auto !important; right: auto !important;
            z-index: auto !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            padding: 4px !important;
            margin: 0 0 8px 0 !important;
            border-radius: 10px !important;
        }
        /* Botones en fila, ancho por contenido, scroll horizontal. */
        .st-key-graf_tipo_chips.st-key-graf_tipo_chips {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: stretch !important;
            gap: 2px !important;
            overflow-x: auto !important;
        }
        /* Las categorías y separadores verticales no aplican en horizontal. */
        .st-key-compras_tabs_row .rail-cat-badge,
        .st-key-compras_tabs_row .rail-sep {
            display: none !important;
        }
        /* El rótulo encabeza una COLUMNA; acá el rail es una tira
           horizontal en el flujo del documento y no hay columna que
           encabezar — y su `position:fixed` lo dejaría flotando sobre el
           contenido. Mismo criterio que las dos reglas de acá arriba. */
        .st-key-rail_rotulo_rep,
        .st-key-rail_rotulo_vis {
            display: none !important;
        }
        /* Los valores de KPI (navegacion.py, 2026-08-22 — reescrito en su
           segunda vuelta el mismo día: primero fue una línea de texto
           debajo del botón, ahora es un bloque superpuesto a su derecha
           vía `position:absolute`, ver `_CSS_KPIS`) también se ocultan
           acá. Ese `position:absolute` ancla contra `navitem_<slug>`, que
           en mobile pasa a ser un CHIP angosto en una fila horizontal —
           "superponer a la derecha" ahí no tiene ancho donde caer y se ve
           roto. Mismo criterio que categorías/separadores: lo que solo
           tiene sentido en columna no sobrevive el paso a fila.
           Clase DUPLICADA a propósito: navegacion.py::_CSS_KPIS pone
           `display:block` con la MISMA especificidad
           (.st-key-graf_tipo_chips .nav-kpis-valores, 0-2-0-0) y se
           inyecta DESPUÉS en el orden de carga (inject_css() en estilos/
           corre antes que inject_navegacion() en app.py) — a igual
           especificidad gana la que va después, así que esta regla perdía
           en silencio si no se dobla la clase (medido con la versión
           anterior de este bloque). Con (0,3,0,0) gana siempre, sin
           depender del orden de inyección. */
        .st-key-graf_tipo_chips.st-key-graf_tipo_chips .nav-kpis-valores {
            display: none !important;
        }
        /* El bug del "encimado": los verdaderos flex-items de la fila NO son
           los <button>, son los stElementContainer que Streamlit envuelve
           alrededor de cada uno. Con flex-shrink:1 (default) se comprimen a
           casi cero y el texto se corta ("Fa", "P", "Tt"...). Se fijan a
           flex:0 0 auto (no encoger) + width:auto (medir por contenido) para
           que la fila DESBORDE y aparezca el scroll horizontal en su lugar. */
        .st-key-graf_tipo_chips.st-key-graf_tipo_chips > div,
        .st-key-graf_tipo_chips.st-key-graf_tipo_chips
            > [data-testid="stElementContainer"] {
            flex: 0 0 auto !important;
            width: auto !important;
            max-width: none !important;
        }
        /* Cada botón: chip auto-ancho, texto en una línea, sin cortarse. */
        .st-key-graf_tipo_chips [data-testid="stButton"],
        .st-key-graf_tipo_chips .stButton {
            width: auto !important; flex: 0 0 auto !important;
        }
        .st-key-graf_tipo_chips [data-testid="stButton"] button,
        .st-key-graf_tipo_chips .stButton button {
            width: auto !important;
            white-space: nowrap !important;
            border-left: none !important;
            border-radius: 999px !important;
            padding: 5px 12px !important;
            background: var(--bg-primary) !important;
        }
        .st-key-graf_tipo_chips [data-testid="stButton"] button[kind="primary"],
        .st-key-graf_tipo_chips .stButton button[kind="primary"] {
            border-left: none !important;
        }
        .st-key-graf_tipo_chips [data-testid="stButton"] button p,
        .st-key-graf_tipo_chips .stButton button p {
            white-space: nowrap !important;
        }
        /* Sin el rail fijo arriba, la vieja compensación negativa de las
           tarjetas dejaría un solape: se neutraliza. */
        [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-compras_prov_drill_wrap,
        [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) [class*="st-key-ajuste_graf_card_izq_"],
        [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) [class*="st-key-ajuste_graf_card_der_"] {
            margin-top: 0 !important;
        }
        /* La franja superior ya no debe esquivar el rail (que ya no está a
           la derecha): que ocupe todo el ancho. Scopeado a app_reporte_compras
           por el mismo motivo que la regla desktop de arriba. */
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras) .st-key-fila_ajuste_top::before {
            right: 0 !important;
        }

        /* (El fix móvil de los filtros Familia/Subfamilia vive MÁS ABAJO, justo
           después de las reglas de desktop que lo centran/estiran: al tener la
           misma especificidad, debe ir después en el archivo para ganar por
           orden de fuente. Ver bloque "chips_ajuste_tabla — reset móvil".) */
    }

    /* =================================================================== */
    /* EL RAIL EN FORMATO LISTA (icono + label + chevron)                    */
    /*                                                                       */
    /* Nació a pedido 2026-08-21 para Compras, tomando de referencia el      */
    /* rail de MSN Dinero, y estaba scopeado a `app_reporte_compras` — sólo   */
    /* vestía las VISTAS de Compras. El 2026-08-22 se generalizó (regla      */
    /* #170, inversión Reportes↔Vistas): este contenedor pasó a dibujar      */
    /* SIEMPRE Reportes, para TODOS los reportes por igual, así que ya no    */
    /* tiene sentido que el formato dependa de cuál esté activo — se le      */
    /* sacó el scope y aplica siempre. El pedido original de Reportes era    */
    /* "ícono + texto" nomás; se reusa este formato ya hecho (ícono+chevron+  */
    /* hairline) en vez de inventar uno nuevo porque cumple lo pedido y de    */
    /* paso mejor.                                                            */
    /*                                                                       */
    /* Va al FINAL del módulo y dentro de min-width:901px por dos razones     */
    /* distintas: por ORDEN, para ganarle a las reglas de arriba que estilan  */
    /* estos mismos botones; y por MEDIA, para no pisar el bloque móvil       */
    /* (max-width:900px), donde el rail deja de ser columna y pasa a ser una  */
    /* tira horizontal de chips — ahí ni el chevron ni los hairlines tienen   */
    /* sentido.                                                               */
    /* =================================================================== */
    @media screen and (min-width: 901px) {
        /* El ANCHO de este rail NO se declara aca: vive en _00_base.py,
           junto al valor base. Es la regla de "los anchos de rail tienen un
           solo duenio" (test_graficos.py la verifica) y no es burocracia --
           nacio de que el ancho estaba escrito en seis sitios que se
           derivaban entre si y plegar el rail dejaba la franja flotando. */
        /* La fila: icono + label. Ya no hay chevron (ver más abajo, donde se
           explica por qué se sacó) — el hairline NO va en el <button>:
           medido en vivo (2026-08-22), un `button[kind="primary"]` global de
           _00_base.py (`border: none !important`) le gana en especificidad
           a cualquier regla de acá que sólo mencione `button` a secas. */
        .st-key-graf_tipo_chips
        [data-testid="stButton"] button {
            /* Vertical 10px -> 17px (2026-08-23, a pedido: "el largo
               vertical", no el ancho — ver _00_base.py). Horizontal
               sin tocar. */
            padding: 17px 12px 17px 9px !important;
            gap: 10px !important;
        }
        /* El hairline separa UN REPORTE del siguiente. Desde que cada
           reporte es un único `navitem_<slug>` (navegacion.py, 2026-08-22 —
           el botón Y sus valores de KPI envueltos juntos, ver el docstring
           de `_CSS_KPIS`), esto es simple: un hairline por hijo directo de
           `graf_tipo_chips` —que hoy es exactamente un `navitem_` por
           reporte—, apagado sólo en el último (quedaría flotando sobre el
           padding inferior del rail). Va en el CONTENEDOR y no en el
           <button> también por lo de arriba: acá no compite ningún
           `button[kind=...]` de mayor especificidad. */
        .st-key-graf_tipo_chips > div {
            border-bottom: 1px solid var(--border) !important;
        }
        .st-key-graf_tipo_chips > div:last-child {
            border-bottom: none !important;
        }
        /* Con una línea por fila, el separador de categoría la duplica. El
           badge sigue siendo el que agrupa. Nota: ninguno de los dos ya
           aparece en este contenedor (Reportes no dibuja categorías) — se
           dejan por si el día de mañana alguna vista los reintroduce, no
           hacen daño estando inertes. */
        .st-key-compras_tabs_row .rail-sep { display: none !important; }
        .st-key-compras_tabs_row .rail-cat-badge {
            font-size: 9.5px !important;
            padding: 13px 12px 5px !important;
        }
        /* 11px era el tamaño para una columna de 84px; 13px, para 270px.
           2026-08-23: +20% a pedido, junto con el ancho del rail
           (_00_base.py, +30%) y el ícono/KPIs de abajo. */
        .st-key-graf_tipo_chips
        [data-testid="stButton"] button p {
            font-size: 16px !important;
            white-space: nowrap !important;
        }
        /* El icono de `st.button(icon=...)`. `color: inherit` a propósito:
           así sigue los estados hover/activo del botón sin reglas propias.
           Es un <span>, y la regla que aplana los descendientes del botón
           (más arriba en este archivo) excluye `span` — por eso no hace
           falta deshacer nada acá. */
        .st-key-graf_tipo_chips
        [data-testid="stButton"] button [data-testid="stIconMaterial"] {
            font-size: 23px !important;    /* 19px + ~20%, junto con el label */
            color: inherit !important;
            flex: 0 0 auto !important;
            margin: 0 !important;
        }
        /* El chevron (›) que hasta acá vivía en `button::after` SE SACÓ el
           2026-08-22 (regla #170, segunda vuelta): con los valores del KPI
           ahora ocupando la esquina derecha de la fila (navegacion.py,
           `.nav-kpis-valores`, `position:absolute; right:12px`), un
           chevron en el mismo rincón se superponía con el texto del
           monto. Entre los dos, el valor es el que aporta información;
           el chevron sólo indicaba "hay más" — que ya lo dice el propio
           hover/cursor del ítem de una lista de navegación. */
    }

    /* =================================================================== */
    /* DEFENSA ANTI-TOOLTIP-FANTASMA — portada de navegacion.py el           */
    /* 2026-08-22 (regla #170). Reportes usa `help=` en sus botones (para el */
    /* tooltip con el nombre completo del reporte); Vistas nunca lo usó y    */
    /* nunca necesitó esta defensa. Con `help=`, Streamlit envuelve el botón */
    /* en `div > span.stTooltipIcon > span.stTooltipHoverTarget`, y deja     */
    /* además una COPIA FANTASMA suelta sin envolver dentro del mismo        */
    /* `stButton` — invisible mientras nadie le da alto/ancho explícitos,    */
    /* visible (y duplicada) en cuanto algo se los da. Se oculta acotando    */
    /* por la ausencia de tooltip, sólo cuando hay un hermano que sí lo      */
    /* lleva. Ver el detalle completo en el docstring original,             */
    /* arquitectura.md regla #164 (ahí se documentó por primera vez, para    */
    /* la franja horizontal; acá es la misma trampa, mismo mecanismo,        */
    /* aplicada al rail vertical porque Reportes se mudó a él). */
    .st-key-graf_tipo_chips [data-testid="stButton"]:has(.stTooltipIcon)
        > div:not(:has(.stTooltipIcon)) {
        display: none !important;
    }
"""
