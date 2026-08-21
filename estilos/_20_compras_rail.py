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
        top: calc(var(--nav-top-alto) + 8px) !important;
        /* 2026-08-18, a pedido: el rail pasa del borde DERECHO al IZQUIERDO.
           Es el sitio que dejó libre el rail de navegación al convertirse en
           la franja superior (--nav-top-alto) unos commits antes: la columna
           izquierda quedó vacía y el rail de vistas volvió a ella.
           Las variables siguen llamándose `--rail-der-*`: el nombre quedó
           histórico y renombrarlas toca ~15 sitios en 4 ficheros más un
           test. Se dejó anotado en _00_base.py en vez de hacerlo a medias. */
        left: 15px !important;             /* mismo despegue que tenía del scrollbar */
        /* El ancho es VARIABLE desde el 2026-08-15 (pestillo, ver
           _25_rails_pestillo.py). Hasta esa fecha había DOS `width` en este
           mismo bloque, 84px unas líneas más abajo, que ganaba por ir
           después — la variable estaba puesta y no hacía nada. */
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
        max-height: calc(100vh - var(--nav-top-alto) - 8px) !important;
        z-index: 900 !important;
        overflow-y: auto !important;
        margin: 0 !important;
        padding: 8px 0 16px 0 !important;
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;    /* mismas esquinas que la tarjeta */
        box-shadow: none !important;       /* sin sombra: integrada al borde */
        scrollbar-width: none !important;
    }
    .st-key-compras_tabs_row::-webkit-scrollbar { display: none !important; }

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
       el <button> y el texto. Especificidad reforzada duplicando la clase del
       contenedor (.st-key-graf_tipo_chips.st-key-graf_tipo_chips) para ganarle
       a cualquier regla base de Streamlit con clase única + !important. */
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
       activo (activo reemplaza el transparent por accent). */
    .st-key-graf_tipo_chips [data-testid="stButton"] > button,
    .st-key-graf_tipo_chips .stButton > button {
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
    .st-key-graf_tipo_chips [data-testid="stButton"] > button::before,
    .st-key-graf_tipo_chips .stButton > button::before {
        display: none !important;
    }
    /* Wrappers del label — NO expandirse (si crecen con flex:1 el texto queda
       flotando al centro del hueco sobrante). Streamlit mete un <div emotion>
       intermedio entre el <button> y el stMarkdownContainer, con display:flex
       y justify-content:center por default → hay que aplanar TODOS los div
       descendientes del botón. */
    .st-key-graf_tipo_chips [data-testid="stButton"] > button > div,
    .st-key-graf_tipo_chips .stButton > button > div,
    .st-key-graf_tipo_chips [data-testid="stButton"] > button [data-testid="stMarkdownContainer"],
    .st-key-graf_tipo_chips .stButton > button [data-testid="stMarkdownContainer"] {
        display: block !important;             /* deja al <p> tomar su ancho */
        flex: 0 1 auto !important;
        width: auto !important;
        max-width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-graf_tipo_chips [data-testid="stButton"] > button p,
    .st-key-graf_tipo_chips .stButton > button p {
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
    .st-key-graf_tipo_chips [data-testid="stButton"] > button:hover,
    .st-key-graf_tipo_chips .stButton > button:hover {
        background: var(--accent-tint) !important;   /* hover suave */
        color: var(--accent-deep) !important;
    }
    /* Activo: kind="primary" del st.button */
    .st-key-graf_tipo_chips [data-testid="stButton"] > button[kind="primary"],
    .st-key-graf_tipo_chips .stButton > button[kind="primary"] {
        background: var(--accent-light) !important;   /* activo saturado */
        color: var(--accent-deep) !important;
        font-weight: 500 !important;
        border-left-color: var(--accent) !important;  /* pinta el reservado */
    }

    /* =================================================================== */
    /* RAIL EN MÓVIL (<=900px): el rail vertical fijo de 84px + el          */
    /* padding-right de 153px se comen casi la mitad de un viewport de      */
    /* 375px. En móvil el rail deja de estar fijo y se vuelve una tira      */
    /* horizontal scrollable arriba del dashboard; los botones quedan en    */
    /* fila (chips) y el contenido recupera todo el ancho. Scopeado con     */
    /* :has(.st-key-compras_tabs_row) — la key del RAIL COMPARTIDO, asi     */
    /* aplica en Compras y Ajuste (ambos usan el rail) y no en Ventas /     */
    /* Inventario / Requerimientos (que no lo usan). Esto es correcto: es   */
    /* comportamiento "del rail", no "del reporte Compras" — para lo        */
    /* segundo se usa :has(.st-key-app_reporte_compras). Ver regla #16.     */
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
        .st-key-graf_tipo_chips [data-testid="stButton"] > button,
        .st-key-graf_tipo_chips .stButton > button {
            width: auto !important;
            white-space: nowrap !important;
            border-left: none !important;
            border-radius: 999px !important;
            padding: 5px 12px !important;
            background: var(--bg-primary) !important;
        }
        .st-key-graf_tipo_chips [data-testid="stButton"] > button[kind="primary"],
        .st-key-graf_tipo_chips .stButton > button[kind="primary"] {
            border-left: none !important;
        }
        .st-key-graf_tipo_chips [data-testid="stButton"] > button p,
        .st-key-graf_tipo_chips .stButton > button p {
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
    /* COMPRAS: EL RAIL EN FORMATO LISTA (icono + label + chevron)           */
    /*                                                                       */
    /* A pedido 2026-08-21, tomando de referencia el rail de MSN Dinero. El  */
    /* rail de 84px y 11px de fuente era una columna de etiquetas; esto lo    */
    /* convierte en una lista: cada vista es una fila con su icono, su        */
    /* nombre y un chevron, separadas por hairlines.                          */
    /*                                                                       */
    /* Va al FINAL del módulo y dentro de min-width:901px por dos razones     */
    /* distintas: por ORDEN, para ganarle a las reglas de arriba que estilan  */
    /* estos mismos botones; y por MEDIA, para no pisar el bloque móvil       */
    /* (max-width:900px), donde el rail deja de ser columna y pasa a ser una  */
    /* tira horizontal de chips — ahí ni el chevron ni los hairlines tienen   */
    /* sentido.                                                               */
    /*                                                                       */
    /* Scopeado a `app_reporte_compras` y no a `compras_tabs_row`: el rail es */
    /* COMPARTIDO con Ajuste (ver regla #16), y esto es una decisión del      */
    /* reporte, no del componente.                                            */
    /* =================================================================== */
    @media screen and (min-width: 901px) {
        /* El ANCHO de este rail NO se declara aca: vive en _00_base.py,
           junto al valor base. Es la regla de "los anchos de rail tienen un
           solo duenio" (test_graficos.py la verifica) y no es burocracia --
           nacio de que el ancho estaba escrito en seis sitios que se
           derivaban entre si y plegar el rail dejaba la franja flotando. */
        /* La fila: icono, label, chevron y un hairline abajo. */
        :root:has(.st-key-app_reporte_compras) .st-key-graf_tipo_chips
        [data-testid="stButton"] > button {
            padding: 10px 12px 10px 9px !important;
            gap: 10px !important;
            border-bottom: 1px solid var(--border) !important;
        }
        /* El último ítem no lleva línea: quedaría flotando sobre el padding
           inferior del rail, sin nada debajo que separar. */
        :root:has(.st-key-app_reporte_compras) .st-key-graf_tipo_chips
        > div:last-child [data-testid="stButton"] > button {
            border-bottom: none !important;
        }
        /* Con una línea por fila, el separador de categoría la duplica. El
           badge sigue siendo el que agrupa. */
        :root:has(.st-key-app_reporte_compras)
        .st-key-compras_tabs_row .rail-sep { display: none !important; }
        :root:has(.st-key-app_reporte_compras)
        .st-key-compras_tabs_row .rail-cat-badge {
            font-size: 9.5px !important;
            padding: 13px 12px 5px !important;
        }
        /* 11px era el tamaño para una columna de 84px. */
        :root:has(.st-key-app_reporte_compras) .st-key-graf_tipo_chips
        [data-testid="stButton"] > button p {
            font-size: 13px !important;
            white-space: nowrap !important;
        }
        /* El icono de `st.button(icon=...)`. `color: inherit` a propósito:
           así sigue los estados hover/activo del botón sin reglas propias.
           Es un <span>, y la regla que aplana los descendientes del botón
           (más arriba en este archivo) excluye `span` — por eso no hace
           falta deshacer nada acá. */
        :root:has(.st-key-app_reporte_compras) .st-key-graf_tipo_chips
        [data-testid="stButton"] > button [data-testid="stIconMaterial"] {
            font-size: 19px !important;
            color: inherit !important;
            flex: 0 0 auto !important;
            margin: 0 !important;
        }
        /* Chevron. Va en ::after porque ::before ya está ocupado (y anulado)
           por la viñeta vieja. `margin-left:auto` lo empuja al borde
           derecho: funciona porque el wrapper del label es `flex: 0 1 auto`
           y no se estira — si alguien le pone flex:1, el chevron se pega al
           texto y deja de haber margen que repartir. */
        :root:has(.st-key-app_reporte_compras) .st-key-graf_tipo_chips
        [data-testid="stButton"] > button::after {
            content: "›";
            margin-left: auto !important;
            font-size: 17px !important;
            line-height: 1 !important;
            color: var(--text-muted) !important;
            flex: 0 0 auto !important;
        }
        :root:has(.st-key-app_reporte_compras) .st-key-graf_tipo_chips
        [data-testid="stButton"] > button[kind="primary"]::after,
        :root:has(.st-key-app_reporte_compras) .st-key-graf_tipo_chips
        [data-testid="stButton"] > button:hover::after {
            color: inherit !important;
        }
    }
"""
