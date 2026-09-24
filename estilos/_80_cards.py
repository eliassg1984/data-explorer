"""estilos._80_cards - Tarjetas de los dashboards: .chart-card, wrappers ajuste_graf_card_* y bloques compras_prov_card_*/compras_prod_card_* de los drills de Proveedor y Producto.

Extraido de estilos.py (lineas 1345-1498 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* CARDS DE GRÁFICOS — contenedor blanco con bordes redondeados         */
    /* =================================================================== */
    /* .chart-card / .chart-card-title vivian aqui hasta el 2026-08-08:
       ningun Python emite esas clases. graficos/base.py::_card envuelve
       en un st.container(border=True, key="chartcard_...") y solo emite
       .chart-card-hdr (titulo arriba) o .chart-card-pie (al pie). Ver
       arquitectura.md #49. */

    /* Título al PIE de _card() -- el default cuando no se pide
       titulo_arriba. La clase la emitía graficos/base.py::_card desde
       siempre pero no tenía estilo (nadie la usaba: los tres callers de
       Compras pasan titulo_arriba=True), así que salía como un párrafo
       suelto. Estrenada 2026-08-07 por el mapa de calor de Ajuste. */
    .chart-card-pie {
        margin: 0.55rem 0 0;
        padding-top: 0.5rem;
        border-top: 1px solid var(--border);
        /* !important SOLO en font-size: Streamlit trae una regla
           `.stMarkdown p` (0,1,1) que le gana a esta clase (0,1,0) y
           dejaba el título en 16px. El resto de propiedades no las toca
           nadie, así que van sin forzar. Mismo tamaño que
           .chart-card-hdr para que los títulos arriba y al pie estén en
           la misma escala. */
        font-size: 13px !important;
        font-weight: 600;
        letter-spacing: 0.02em;
        color: var(--accent-deep);
        text-align: center;
    }

    /* Cabecera de _card(titulo_arriba=True): título arriba + divisoria.
       Solo se emite en las tarjetas de Compras que lo piden; el resto
       de dashboards conserva su título al pie (.chart-card-pie). */
    .chart-card-hdr {
        margin: 0 0 0.55rem;
        padding: 0.1rem 0 0.5rem;
        border-bottom: 1px solid var(--border);
        font-size: 13px;
        font-weight: 600;
        line-height: 1.35;
        color: var(--accent-deep);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* ── VS AÑO PASADO: CUATRO TARJETAS (2026-09-14, regla #420) ──────
       Hasta ese día era UNA superficie, `chartcard_compras_vap` (la de
       `graficos/base.py::_card`), que desde el 2026-09-02 tomaba acá el
       look de tarjeta —fondo, radio, sombra— con un bloque copiado del de
       Producto. Se partió como Volatilidad (#415): las superficies son
       `compras_vap_card_hdr`, `_serie`, `_puente` y `_tabla`, y el look lo
       pone la MISMA regla de Producto y Volatilidad (más abajo, en
       «TARJETAS DEL DRILL DE PRODUCTO»): el selector se sumó a esa regla,
       no se copió. Acá queda el hueco entre las tarjetas, que es el `gap`
       del cuerpo transparente: 16px, el de todos los drills de Compras. */
    .st-key-compras_vap_cuerpo {
        gap: 16px !important;
    }

    /* La cabecera de ESTA tarjeta lleva, en UN renglón: el nombre de la
       vista, el ámbito (lo que antes era el `title` de la figura) y, desde
       el 2026-09-02, los dos controles que vivían en la tarjeta de la
       tabla — el agrupador y el buscador de ítems. Al fusionarse las dos
       tarjetas, esta fila es la única cabecera que queda.

       La RAYA divisoria se muda del `<p>` a la FILA: con el `<p>` como un
       flex item más, su `border-bottom` subrayaba sólo el título y dejaba
       los controles colgando de nada. */
    /* `vol_fila_hdr` es la cabecera de Volatilidad, y es la MISMA fila:
       desde el 2026-09-05, con un intervalo de unas horas del 2026-09-12 en
       que fue un panel a la derecha de la tabla (`vol_panel`). Volvió a
       ser fila a pedido —«como la vista Vs año pasado»—, así que comparte
       estas reglas de layout en vez de tener un juego propio (#394). */
    .st-key-vap_fila_hdr,
    .st-key-vol_fila_hdr {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        align-items: center !important;
        gap: 10px !important;
        margin: 0 0 0.35rem !important;
        padding-bottom: 0.3rem !important;
        border-bottom: 1px solid var(--border);
    }
    /* Más delgada desde el 2026-09-17, a pedido («hagamos más delgada
       verticalmente esa franja»): el margen baja de 0.55rem a 0.35 y el
       padding de 0.5 a 0.3, o sea 6px menos de aire — que se suman a los
       13 del `padding-top` que se fue con los rótulos de tramo. La raya de
       abajo se queda: es lo que separa la cabecera de las tarjetas. */
    /* El TÍTULO cede, los controles no. `min-width: 0` es obligatorio: sin
       él un flex item nunca baja de su contenido, así que un ítem en foco
       de nombre largo empujaría el buscador fuera de la tarjeta en vez de
       truncar. */
    .st-key-vap_fila_hdr > [data-testid="stElementContainer"]:first-child,
    .st-key-vol_fila_hdr > [data-testid="stElementContainer"]:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
    }
    /* `st.container(key=…)` pone la key en el `stVerticalBlock` de ADENTRO:
       el ítem de la fila es el `stLayoutWrapper` anónimo que lo envuelve,
       que nace con `width: 100%`. Estilar sólo la key de adentro no
       alcanza — el que reparte es el padre (regla #272). */
    /* 2026-09-02: la fila pasó de tres elementos a SEIS —título, métrica,
       ventana, agrupador, buscador e info— al subir los dos controles que
       vivían en el renglón de abajo.

       2026-09-05, a pedido ("hacer más cortos los campos de los selectores
       y poner uno de familia"): entra un SÉPTIMO, el filtro de Familia, y
       los otros se recortan al ancho que de verdad necesitan.

       LOS ANCHOS NO SON A OJO. Cada uno es el TEXTO MÁS LARGO QUE PUEDE
       MOSTRAR + 50px de cromo, y esos 50 se midieron en el navegador, no
       se estimaron: 34 de la caja (`cajaW − input.clientWidth`, o sea
       padding del combobox + chevron) y 16 más de padding propio del
       `<input>`, que es lo que separa `scrollWidth` del texto medido con
       `measureText`. La primera vuelta de este cambio usó sólo los 34 y
       los tres campos cortos quedaron clipeando su propio valor —
       "Producto" en 96px se veía "Product". Medido el 2026-09-05, fuente
       real de la fila (DM Sans 12px):
         modo     "Cantidad"   54 → 104, +2 de holgura = 106
         ventana  "Rango"      35 →  85, +3 =  88
         agrupar  "Subfamilia" 60 → 110, +2 = 112
         buscar   placeholder "Buscar ítem…" 75 → 104 (deja lugar para
                  ver lo tipeado; el mínimo para el placeholder es 93)
       La holgura de 2-3px es contra el redondeo: el ancho exacto deja
       `scrollWidth == clientWidth` y cualquier fracción lo vuelve recorte.
       Ojo: el texto que hay que medir es el de la LISTA, no el del valor
       de hoy. El desplegable de un `st.selectbox` mide lo mismo que su
       trigger (medido: trigger 168 → listbox 166 → caja de la opción 156)
       y recorta con `text-overflow: clip`, sin puntos suspensivos, así
       que angostar el campo corta las OPCIONES en silencio. Regla #318.

       Suman 600 de selectores + 51 de los dos íconos + 70 de gaps y dejan
       110px de los 831 de la fila (viewport 1280) para el título, que sin
       ámbito mide 98: entra en UN renglón con 12px de aire.

       Con un ítem en foco el ámbito entra en el título y la fila pasa a
       DOS renglones. No es una regresión de este cambio: el `<p>` es
       `flex: 1 1 auto` con `flex-basis: auto`, y el reparto en líneas de
       un flex mira el tamaño hipotético (el del contenido) ANTES de
       encoger, así que un ámbito de 242px ya hacía saltar el renglón con
       los seis controles de antes. Y es mejor así — el ámbito se lee
       entero en vez de truncarse. El `text-overflow: ellipsis` de más
       abajo queda como red para el renglón ya partido.
       `flex-wrap` en la fila (arriba) es esa red: si el viewport se
       angosta, los controles bajan de renglón en vez de desbordar. */
    /* La ventana pasó de "12m" a "📅 Últimos 12 meses" el 2026-09-07
       (`vs_ano_pasado._ETIQ_VENTANA`: era el único control de la fila que
       nombra un período y con el nombre corto no se distinguía de los otros
       cuatro desplegables sin etiqueta). Los 88px de antes eran para "Todo
       el hi…" — el texto largo hay que pagarlo en ancho. El hueco sale del
       lado del TÍTULO, que en esta fila es el elástico: "Vs año pasado"
       mide ~110 de los ~495 que le tocaban.
       Sigue el mismo criterio MEDIDO que el filtro de Familia de acá abajo
       (`scrollWidth` del input ya renderizado, no un `<span>` clonado con
       la misma fuente), y por la misma razón: el `<span>` daba 119 para el
       valor más largo y el input real pide 135 — 16px que no se ven en la
       cuenta. Medido el 2026-09-07 con la fila renderizada:

           📅 Rango             118      📅 Últimos 24 meses  135  ← el peor
           📅 Últimos 3 meses   128      📅 Todo el histórico  129
           📅 Últimos 12 meses  132

       El cromo del desplegable (chevron + padding) come 34, así que 135+34
       = 169 → 172 con holgura, y el input queda en 138. Con los 88 de antes
       el input medía 54: entraba "📅 Rango" y nada más.
       La fila sigue en UN renglón (36px, verificado): los 20px salen del
       hueco del título, que baja de 254 a 234 para un texto de ~110. */
    /* CON QUÉ EJE SE PARTE EL Δ de la cascada ("Por qué" / "Quién" /
       "Cuándo"), agregado el 2026-09-16 con la regla #443. Es el OCTAVO
       control de la fila. Vivió acá un día: el 2026-09-17 bajó, con `Ver`,
       a la tarjeta de la serie — ver `vap_serie_hdr` al final de este
       bloque. Sus anchos MEDIDOS se fueron con ellos (106 para "Cantidad",
       100 para "Por qué"), y siguen siendo el mismo criterio: el texto más
       largo que puede mostrar + los 50 de cromo del desplegable. */
    .st-key-vap_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vap_hdr_ventana) {
        flex: 0 0 auto !important;
        width: 172px !important;
    }
    /* El más ancho de la fila, y no por capricho: sus opciones son nombres
       REALES del parquet, y el más largo ("BEBIDAS CON ALCOHOL") mide 136
       en la fila → 186 con el cromo, MEDIDO sobre el campo ya renderizado
       (`scrollWidth` del input) y no estimado: `measureText` daba 132 y
       ese ancho entraba justo, con cero holgura. 190 es eso más 4, y de
       paso cubre la LISTA, que se dibuja en un portal fuera de esta fila
       y por lo tanto en la fuente de 14px, no en la de 12.
       La única que no entra es "GASTOS ADMINISTRATIVOS" — gasto indirecto,
       que los chips de la franja dejan afuera de entrada. */
    .st-key-vap_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vap_hdr_familia) {
        flex: 0 0 auto !important;
        width: 190px !important;
    }
    .st-key-vap_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vap_hdr_agrupar) {
        flex: 0 0 auto !important;
        width: 112px !important;
    }
    .st-key-vap_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vap_hdr_buscar) {
        flex: 0 0 auto !important;
        width: 104px !important;
    }
    /* El ícono de ayuda mide su contenido, no lo que sobre. Sin esta regla
       su `stLayoutWrapper` nace con `width: 100%` como los otros dos y se
       queda con TODO el hueco que dejaba el título: medido, 394px de
       wrapper para un botón de 180 — y el ámbito del título truncaba a
       "Tod…". */
    .st-key-vap_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vap_hdr_ayuda) {
        flex: 0 0 auto !important;
        width: auto !important;
    }
    .st-key-vap_hdr_ayuda [data-testid="stPopoverButton"] {
        min-height: 26px !important;
        height: 26px !important;
        min-width: 0 !important;
        padding: 0 6px !important;
    }
    /* El CHEVRON de Streamlit, mismo trato que en `cp_rank_escala`: se
       esconde el WRAPPER y no el glifo. Acá se puede apuntar al
       `stIconMaterial` sin miedo a llevarse el ícono del label, porque ese
       entra por el shortcode del LABEL y sale como `stMarkdownContainer`
       — son dos nodos distintos (medido: label 14x22, chevron 16x16). */
    .st-key-vap_hdr_ayuda button > div > div:last-child:not(:first-child) {
        display: none !important;
    }
    /* (ACÁ VIVÍAN LAS TRES REGLAS DEL ⛶ "sola en la página" — el ancho
       auto de su wrapper, el alto del botón y la defensa anti-tooltip-
       fantasma de la regla #164. El botón se quitó de la cabecera el
       2026-09-17, a pedido, y el mecanismo `compras_pila_solo` quedó sin
       nadie que lo encienda: ver el hueco que dejó en
       `vs_ano_pasado.py`. Si vuelve, vuelven estas tres — sobre todo la
       última, sin la cual el ícono sale DUPLICADO por llevar `help=`. */

    /* ── LOS TRAMOS DE LA FILA (reglas #444 y #449) ─────────────────────
       El orden lo pone Python; acá sólo se PINTA la separación, y a
       propósito con un pseudo-elemento: un `<hr>` sería un ítem del flex,
       se cobraría su `gap: 10px` y podría desordenarse si alguien mueve un
       control de tramo. Un `::after` no ocupa sitio en el flujo y viaja
       pegado a su control.

       LOS RÓTULOS DE TRAMO SE FUERON el 2026-09-17, a pedido: «quitemos
       los textos "Qué entra" y "El detalle" y hagamos más delgada
       verticalmente esa franja». Eran dos `::before` y los 13px de
       `padding-top` que les hacían sitio — la fila baja de 40 a 27. La
       línea se queda: separa los tramos sin gastar un renglón, que era lo
       que los rótulos costaban.

       La línea va sobre el PRIMERO de cada tramo y no sobre el último del
       anterior: «Partir por» ya no vive en esta fila, pero el criterio
       vale igual para cualquier control que aparezca y desaparezca. */
    .st-key-vap_fila_hdr > [data-testid="stLayoutWrapper"] {
        position: relative !important;
    }
    .st-key-vap_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vap_hdr_agrupar)::after {
        content: "";
        position: absolute;
        left: -6px;
        top: 0;
        bottom: 0;
        width: 1px;
        background: var(--border);
        pointer-events: none;
    }

    /* ── LOS TRES RENGLONES DE LA TARJETA DE LA CASCADA (regla #449) ────
       nombre · (rótulo+monto | corte) · % · figura. Son CUATRO bloques de
       Streamlit, y su `gap: 16px` por defecto daría 48px de aire entre
       cuatro cosas que se leen como una sola ficha. Se baja acá, en la
       tarjeta, y no con márgenes negativos uno por uno: el margen hay que
       calibrarlo por bloque y se descalibra en cuanto uno cambia de
       tamaño; el `gap` vale para todos y sobra para el que venga. */
    .st-key-compras_vap_card_puente {
        gap: 4px !important;
    }

    /* ── El toggle Gráfico/Tabla de la tarjeta de la cascada (regla    */
    /*    #484). A la altura de sus vecinos (26px, como el corte y el    */
    /*    buscador) y sin el ancho suelto del stButtonGroup, que si no   */
    /*    empuja al corte fuera de la fila. Son dos botones de ícono.    */
    .st-key-vap_puente_vista [data-testid="stButtonGroup"] {
        min-height: 26px !important;
        gap: 0 !important;
    }
    .st-key-vap_puente_vista [data-testid="stButtonGroup"] button {
        min-height: 26px !important;
        height: 26px !important;
        padding: 0 8px !important;
    }
    .st-key-vap_puente_vista [data-testid="stButtonGroup"]
        button [data-testid="stIconMaterial"] {
        font-size: 16px !important;
    }

    /* ── La tabla mes a mes que ALTERNA con el waterfall (regla #484).  */
    /*    Ocupa el alto del waterfall (139px, `_ALTO_CASCADA`) y lo que  */
    /*    no entra scrollea DENTRO, para que la tarjeta no cambie de     */
    /*    tamaño al alternar y siga terminando en la línea de la serie   */
    /*    (regla #145). Los colores del Δ los pinta Python inline (desde */
    /*    `tema.py`), como el resto del veredicto.                       */
    .st-key-compras_vap_card_puente .vap-tbl-wrap {
        /* Alto FIJO = el del waterfall (`_ALTO_CASCADA`/`stPlotlyChart`,
           medido 139px), no `max-height`: con pocos meses una tabla más
           baja encogía la tarjeta y la fila SALTABA ~30px al alternar
           (medido 2026-09-21). Con alto fijo la tarjeta mide igual en los
           dos modos; lo que no entra scrollea dentro. */
        height: 139px;
        overflow-y: auto;
        overflow-x: hidden;
    }
    .st-key-compras_vap_card_puente .vap-tbl {
        width: 100%;
        border-collapse: collapse;
        font: 400 11.5px/1.2 "DM Sans", sans-serif;
        color: var(--text-primary);
        table-layout: fixed;
    }
    .st-key-compras_vap_card_puente .vap-tbl th,
    .st-key-compras_vap_card_puente .vap-tbl td {
        text-align: right;
        padding: 2.5px 6px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-variant-numeric: tabular-nums;
    }
    .st-key-compras_vap_card_puente .vap-tbl thead th {
        position: sticky;
        top: 0;
        z-index: 1;
        background: var(--bg-card);
        font-weight: 600;
        color: var(--text-secondary);
        border-bottom: 1px solid var(--border);
    }
    .st-key-compras_vap_card_puente .vap-tbl td {
        border-bottom: 1px solid var(--line-soft);
    }
    .st-key-compras_vap_card_puente .vap-tbl .vap-tbl-mes {
        text-align: left;
    }
    .st-key-compras_vap_card_puente .vap-tbl .vap-tbl-aa {
        color: var(--text-secondary);
    }
    .st-key-compras_vap_card_puente .vap-tbl-vacia {
        font: 400 12px "DM Sans", sans-serif;
        color: var(--text-secondary);
        text-align: center;
        padding: 24px 0;
    }

    .st-key-vap_serie_modo,
    .st-key-vap_puente_corte,
    .st-key-vap_puente_vista,
    .st-key-vap_hdr_ventana,
    .st-key-vap_hdr_familia,
    .st-key-vap_hdr_agrupar,
    .st-key-vap_hdr_buscar { width: 100% !important; }
    /* Y el contenedor de elemento de adentro TAMBIÉN, o el campo no llena
       el ancho que se le reservó arriba. Medido el 2026-09-05 con el
       filtro de Familia: hueco de 186px, campo de 178, y "BEBIDAS CON
       ALCOHOL" recortada — con los 8px que faltaban entra.
       El culpable es la regla de `width: auto` de más abajo, que existe
       para que el TÍTULO mida su texto: en un `stVerticalBlock` (que es
       flex column con `align-items: start`) `auto` deja de estirar y pasa
       a ser `fit-content`, o sea el ancho INTRÍNSECO del widget. Para el
       título es lo que se quiere; para un campo con ancho reservado, no:
       queda un tope invisible que ninguna de las reglas de arriba puede
       superar, y agrandar el hueco no hace nada. */
    .st-key-vap_serie_modo > [data-testid="stElementContainer"],
    .st-key-vap_puente_corte > [data-testid="stElementContainer"],
    .st-key-vap_hdr_ventana > [data-testid="stElementContainer"],
    .st-key-vap_hdr_familia > [data-testid="stElementContainer"],
    .st-key-vap_hdr_agrupar > [data-testid="stElementContainer"],
    .st-key-vap_hdr_buscar > [data-testid="stElementContainer"] {
        width: 100% !important;
    }
    /* Los dos controles, a la altura de una píldora de fila, como los de la
       tarjeta de Ranking. El default de Streamlit es 40px.

       OJO CON EL SELECTOR DEL SELECTBOX (2026-09-02, medido): en esta
       versión de Streamlit NO es `[data-baseweb="select"]` sino
       `.react-aria-ComboBox`. Con el selector viejo la regla no matcheaba
       nada y el desplegable seguía en 40 mientras el buscador —que sí
       matcheaba por `stTextInputRootElement`— bajaba a 26: la fila entera
       medía lo que el más alto, 49px con el padding y el borde. El
       `st.text_input` y el `st.selectbox` de la MISMA fila necesitan dos
       ganchos distintos; no se puede asumir que comparten API. */
    .st-key-vap_fila_hdr .react-aria-ComboBox,
    .st-key-vap_serie_hdr .react-aria-ComboBox,
    .st-key-vap_puente_corte .react-aria-ComboBox,
    .st-key-vap_puente_corte .react-aria-ComboBox > div,
    .st-key-vap_serie_hdr .react-aria-ComboBox > div,
    .st-key-vap_fila_hdr .react-aria-ComboBox > div,
    .st-key-vap_fila_hdr [data-baseweb="select"] > div,
    .st-key-vap_fila_hdr [data-testid="stTextInputRootElement"],
    .st-key-vol_fila_hdr .react-aria-ComboBox,
    .st-key-vol_fila_hdr .react-aria-ComboBox > div,
    .st-key-vol_fila_hdr [data-baseweb="select"] > div {
        min-height: 26px !important;
        height: 26px !important;
        font-size: 12px !important;
    }
    .st-key-vap_fila_hdr .react-aria-ComboBox [role="button"],
    .st-key-vap_serie_hdr .react-aria-ComboBox [role="button"],
    .st-key-vap_puente_corte .react-aria-ComboBox [role="button"],
    .st-key-vap_puente_corte .react-aria-ComboBox input,
    .st-key-vap_serie_hdr .react-aria-ComboBox input,
    .st-key-vap_fila_hdr .react-aria-ComboBox input,
    .st-key-vol_fila_hdr .react-aria-ComboBox [role="button"],
    .st-key-vol_fila_hdr .react-aria-ComboBox input {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        font-size: 12px !important;
    }
    /* El TÍTULO deja de caer 13px por debajo de los controles.
       `st.markdown` con HTML de BLOQUE le pone `margin-bottom: -16px` a su
       contenedor (regla #162), así que la caja que el flex alinea medía 5,6px
       mientras el texto ocupaba 21,6 y desbordaba hacia abajo: con
       `align-items: center` se centraba la caja chica y el texto quedaba
       colgando. Se vio primero como un arrastre de `translate(0,-13px)` en el
       modo diseño — o sea, exactamente los 16 de margen menos los 3 que ya
       compensaba el centrado. Anulando el margen la caja vuelve a medir su
       texto y el centrado del flex hace lo suyo, sin transform. */
    .st-key-vap_fila_hdr [data-testid="stMarkdownContainer"],
    .st-key-vap_serie_hdr [data-testid="stMarkdownContainer"],
    .st-key-vol_fila_hdr [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    .st-key-vap_fila_hdr [data-testid="stTextInputRootElement"] input {
        padding: 0 8px !important;
        font-size: 12px !important;
    }
    .st-key-vap_fila_hdr [data-testid="stElementContainer"] {
        width: auto;
    }

    /* ── LA CABECERA DE LA TARJETA DE LAS BARRAS (reglas #445, #449) ─────
       UN renglón desde el 2026-09-22 (a pedido: «el gráfico es muy corto
       verticalmente, subamos el selector para que figure en la fila del
       título»): el NOMBRE del ítem —centrado en la tarjeta y azul, igual que
       la cascada de al lado (`_nombre_serie_html`)— y el toggle «Ver» en la
       MISMA fila.

       Entre el 2026-09-21 y hoy eran DOS renglones apilados: se partieron
       porque un nombre no se centra en la TARJETA si comparte fila con un
       widget EN EL FLUJO — se centra en su columna y queda corrido (regla
       #449). La vuelta a un renglón conserva el centrado esquivando eso: el
       nombre ocupa el ancho entero de la tarjeta y el toggle va SUPERPUESTO
       a la izquierda (`position: absolute`), fuera del flujo, así que no le
       corre el centro. El renglón que se ahorra vuelve a la figura
       (`alturas.FRANJA_CTRL_SERIE`, sin `FRANJA_NOMBRE_CASCADA`).

       `position: relative` para anclar el toggle; `align-items: center`
       para centrarlo verticalmente contra el nombre; `min-height` = alto
       del desplegable (26px), o sin foco el renglón colapsa al nombre y el
       toggle se sale por arriba. */
    .st-key-vap_serie_hdr {
        position: relative !important;
        display: flex !important;
        align-items: center !important;
        min-height: 26px !important;
        margin: 0 0 0.3rem !important;
    }
    /* El nombre, a todo el ancho para centrarse EN LA TARJETA. */
    .st-key-vap_serie_hdr > [data-testid="stElementContainer"]:first-child {
        width: 100% !important;
    }
    /* El toggle «Ver», SUPERPUESTO a la izquierda: fuera del flujo, no le
       compite ancho ni centro al nombre. Ancho para «Cantidad Comprada» —el
       rótulo más largo desde el rename (#484)— más el cromo del desplegable.
       `top: 50%` + `translateY` lo centra en el renglón sea cual sea el alto
       exacto del desplegable. */
    .st-key-vap_serie_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vap_serie_modo) {
        position: absolute !important;
        left: 0 !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        width: 176px !important;
        z-index: 2 !important;
    }
    /* El hueco del nombre existe aunque esté VACÍO (sin foco): es un
       `st.empty()`, y si colapsara a cero el renglón mediría menos. La
       cabecera mide siempre lo mismo. */
    .st-key-vap_serie_hdr [data-testid="stMarkdownContainer"] {
        min-height: 17px !important;
    }

    /* El `<p>` ya no pone la raya ni el margen: los pone la fila. Se queda
       con el reparto de sus dos textos. */
    /* ── VOLATILIDAD: el selector de ventana, en la linea del titulo ──
       2026-09-05, a pedido. El `<p>` deja de poner la raya y el margen
       (los pone la fila, arriba) y se queda con el texto; el desplegable
       mide lo suyo, 90px como el gemelo de vap — su valor mas largo es
       "Todo". Sin `flex: 0 0 auto` su `stLayoutWrapper` nace con
       `width: 100%` y se come el renglon entero (regla #272). */
    .chart-card-hdr.vol-hdr {
        margin: 0 !important;
        padding: 0 !important;
        border-bottom: none !important;
        /* `!important` en el TAMANO, medido 2026-09-05: envolver el `<p>`
           en un `st.container(key=...)` suma un nivel de emotion, y su
           regla `.st-emotion-cache-XXX p { font-size: inherit }` (0,2,1)
           le gana a `.chart-card-hdr` (0,1,0). Fue 13px hasta el
           2026-09-12; desde que la cabecera es la fila de «Vs año pasado»
           (#394) mide lo mismo que su título, 16 medidos. */
        font-size: 16px !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .st-key-vol_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vol_hdr_periodo) {
        flex: 0 0 auto !important;
        width: 90px !important;
    }
    /* LA TABLA PEGADA A LA CABECERA (2026-09-12, a pedido, del modo diseño
       como `translate(0, -20px)` sobre la grilla): entre la raya de la fila
       y la grilla había 18.8px — el margen de la fila (8.8) y el `gap` de 10
       de la tarjeta. Un `transform` sólo corre el DIBUJO: el hueco se queda
       abajo y la grilla tapa la fila. Acá se cierra de verdad.

       `margin-bottom: -10px` y no 0: se come también el `gap` de la
       tarjeta, que es de TODOS sus hijos (`compras_vol_card_rank`) y no se
       puede sacar sólo para este par. Y sin la raya de la fila: la grilla
       arranca con su propio borde de 3px (`tablas/compras_volatilidad.py`),
       que ES la separación — con las dos, se leían 4px de línea. En la
       vista previa del modo diseño la grilla tapaba justo esa raya.
       Va DESPUÉS de la regla compartida con vap y con la misma
       especificidad: gana por orden. Regla #395. */
    .st-key-vol_fila_hdr {
        margin-bottom: -10px !important;
        border-bottom: none !important;
    }
    /* Y la de vap, desde que va SOLA en su tarjeta (2026-09-14, #420): la
       raya y los 17px de margen y padding de abajo separaban la cabecera de
       la serie, que ahora está en OTRA tarjeta — esa separación la pone el
       gris de la app. Con la raya, la tarjeta cerraba con una línea a 8px
       de su borde de abajo. Misma especificidad que la regla compartida de
       arriba: gana por orden. */
    .st-key-vap_fila_hdr {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
        border-bottom: none !important;
    }
    .st-key-vol_hdr_periodo { width: 100% !important; }

    /* ── VOLATILIDAD: TRES TARJETAS (2026-09-13, regla #415) ───────────
       Hasta ese día era UNA superficie (`ajuste_graf_card_izq_vol`) con
       una tarjeta transparente adentro (`chartcard_compras_vol`), y los
       gaps de acá eran de esa tarjeta: 10px entre sus bloques (desde el
       2026-09-07, para que entrara en una pantalla) y 18 dentro de cada
       mitad de la fila de abajo. Se mudaron a las keys nuevas:

       · El cuerpo (`compras_vol_cuerpo`, transparente) separa la tarjeta
         del ranking de la fila de abajo con los 16px del resto de los
         drills de Compras.
       · La tarjeta del ranking, 10 entre la cabecera y la grilla: es el
         número que se come el `margin-bottom: -10px` de `vol_fila_hdr`
         (arriba, #395) para dejarlas pegadas.
       · Las dos de abajo, 18 entre su título y lo suyo (a pedido: «más
         espacio entre el título y el gráfico de velas, y entre "Semana
         del … al …" y la tabla»). El look de tarjeta —fondo, radio,
         sombra, padding— es el de Producto, más abajo. */
    .st-key-compras_vol_cuerpo {
        gap: 16px !important;
    }
    /* Y 16px MÁS ARRIBA de toda la sección (2026-09-14, a pedido: «que
       entre la tarjeta de Vs año pasado y la de volatilidad haya un poco
       más de espacio, se ven muy pegadas»). Entre secciones de la pila
       quedan los 16px de su `gap`; con esto, las dos quedan a 32. Sólo
       este par, que es el que se pidió: si el aire tiene que crecer entre
       TODAS las secciones, el lugar es el `gap` de la pila, no esto. */
    .st-key-compras_vol_drill_wrap {
        margin-top: 16px !important;
    }
    .st-key-compras_vol_card_rank {
        gap: 10px !important;
    }
    .st-key-compras_vol_card_velas,
    .st-key-compras_vol_card_semana {
        gap: 18px !important;
    }

    /* ── VOLATILIDAD: la cabecera es una FILA, como la de vap ──────────
       2026-09-12, a pedido (#394): «el título arriba, al lado izquierdo, y
       los toggles y demás en la misma fila, como la vista Vs año pasado;
       la tabla, a todo el largo de la tarjeta». El layout de la fila lo
       ponen las reglas compartidas con `vap_fila_hdr` (arriba); acá van
       los anchos de SUS ítems, uno por uno, con el mismo criterio medido
       (texto más largo + 50 de cromo).

       Unas horas antes esta cabecera era un panel de 240px a la derecha
       de la tabla (`vol_panel`, con `vol_fila_top` como fila de dos
       columnas). Sus reglas se fueron con él.

       El buscador, 118px y no los 104 de vap: el placeholder es «Buscar
       insumo…», dos caracteres más largo que «Buscar ítem…». */
    .st-key-vol_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vol_hdr_buscar) {
        flex: 0 0 auto !important;
        width: 118px !important;
    }
    .st-key-vol_hdr_buscar { width: 100% !important; }
    .st-key-vol_hdr_buscar > [data-testid="stElementContainer"] {
        width: 100% !important;
    }
    /* El `st.text_input` NO comparte gancho con el `st.selectbox` de al
       lado (ver el bloque de vap: uno es `.react-aria-ComboBox`, el otro
       `stTextInputRootElement`). Sin esta regla el campo se queda en los
       40px del default y la fila entera mide lo que el más alto. */
    .st-key-vol_fila_hdr [data-testid="stTextInputRootElement"] {
        min-height: 26px !important;
        height: 26px !important;
        font-size: 12px !important;
    }
    .st-key-vol_fila_hdr [data-testid="stTextInputRootElement"] input {
        padding: 0 8px !important;
        font-size: 12px !important;
    }
    /* El ícono mide su contenido: sin esto su `stLayoutWrapper` nace con
       `width: 100%` y se queda con todo el hueco que dejaba el título
       (regla #272, y el mismo caso que documenta `vap_hdr_ayuda`). */
    .st-key-vol_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vol_hdr_ayuda) {
        flex: 0 0 auto !important;
        width: auto !important;
    }
    .st-key-vol_hdr_ayuda [data-testid="stPopoverButton"] {
        min-height: 26px !important;
        height: 26px !important;
        min-width: 0 !important;
        padding: 0 6px !important;
    }
    /* El CHEVRON del popover, igual que en `vap_hdr_ayuda`: se esconde el
       WRAPPER, no el glifo — el ícono del label entra por el shortcode y
       sale como `stMarkdownContainer`, que es otro nodo. */
    .st-key-vol_hdr_ayuda button > div > div:last-child:not(:first-child) {
        display: none !important;
    }
    /* ── VOLATILIDAD: la pastilla que muestra la columna del puntaje ──
       2026-09-12, a pedido: la columna «Volatilidad» arranca oculta y este
       `st.pills` de una sola opción la prende. Mide su contenido (sin esto
       su `stLayoutWrapper` nace en `width: 100%`, regla #272) y baja a los
       26px del resto de la fila: el buscador, el desplegable y el ícono de
       ayuda de al lado miden eso, y una pastilla de 32 haría crecer la fila
       entera. Acotado a SU key, no a `vol_fila_hdr`: el aviso de CLAUDE.md
       sobre reglas del contenedor que capturan widgets futuros. */
    .st-key-vol_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-vol_hdr_ver) {
        flex: 0 0 auto !important;
        width: auto !important;
    }
    .st-key-vol_hdr_ver [data-testid="stButtonGroup"] button {
        min-height: 26px !important;
        height: 26px !important;
        padding: 0 10px !important;
        font-size: 12px !important;
    }

    /* ── VOLATILIDAD: la cabecera del DETALLE ─────────────────────────
       Nombre a la izquierda, los tres KPI a la derecha, TODO en un renglón
       (2026-09-07, a pedido: «reducir el tamaño de los kpis y ponerlos en
       línea con el título»).

       Es el tercer intento del mismo día y los tres están medidos, así que
       vale dejar la cuenta: el trío con las tallas de antes (rótulo .64rem,
       cifra 1rem) mide 473px de contenido nowrap — por eso el intento
       anterior no entró en los ~361px de la columna y volvió a
       rótulo-arriba/cifra-abajo. Con rótulo .55rem, cifra .8rem, rótulos
       cortos y la volatilidad sin su «pts», el trío baja a ~305px: con la
       columna del drill en 454px (ventana 1400 y rail plegado) al nombre le
       quedan ~137, y a partir de ~1600px de ventana entra entero.

       El NOMBRE es el que cede, pero con PISO: `flex: 1 1 130px` (unos 17
       caracteres) + ellipsis. El piso va en la BASE del flex y no en
       `min-width`: quién se va a otro renglón se decide con la base —el
       ancho del contenido si la base es `auto`, o sea el nombre entero—,
       y el `min-width` recién se mira después, cuando ya hay línea. Con
       `auto` la fila envolvía igual (169 + 10 + 303 = 482 > 454) y el
       nombre se quedaba con la línea entera para él. Sin el piso, con el rail desplegado —columna
       de 364px— al nombre le quedaban 51px y el título del drill salía
       «Vin…». Con él, cuando no entran los dos, el `flex-wrap` baja el trío
       de KPIs a su propio renglón: la fila mide 20px más, que es
       exactamente lo que costaba antes de este cambio, y ninguna de las dos
       mitades miente. El umbral cae en ~443px de columna, o sea que en la
       ventana del pedido (454) entra en línea y en la de al lado no.

       El nombre completo sigue a un golpe de vista en la fila marcada de la
       grilla de al lado, y el `title=` de cada KPI (lo pone
       `volatilidad.py`) recupera el rótulo largo que acá se abrevia.

       `align-items: baseline` y no `center`: rótulo y cifra tienen tallas
       distintas y lo que alinea a la vista es la línea de base del texto,
       no el centro de sus cajas. */
    .vol-detalle-hdr {
        display: flex;
        flex-flow: row wrap;
        align-items: baseline;
        justify-content: space-between;
        column-gap: 10px;
        row-gap: 2px;
        margin: 0;
        min-width: 0;
    }
    /* LOS DOS TÍTULOS DE LA FILA DE ABAJO —el insumo y «Semana del … al
       …»— con MENOS NOTORIEDAD (2026-09-13, a pedido): de .95rem en negrita
       700 a .85rem en 500 y gris. Son rótulos de lo que va debajo, no la
       lectura; la lectura son los KPIs, que siguen en negrita. Los dos usan
       esta clase, así que no se pueden desparejar. */
    .vol-detalle-nom {
        font-size: .85rem;
        font-weight: 500;
        color: var(--text-secondary);
        flex: 1 1 130px;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .vol-detalle-kpis {
        display: flex;
        align-items: baseline;
        flex: 0 0 auto;
        gap: 10px;
        white-space: nowrap;
    }
    .vol-detalle-kpis > span {
        display: flex;
        align-items: baseline;
        gap: 4px;
    }
    .vol-detalle-kpis i {
        font-style: normal;
        font-size: .55rem;
        font-weight: 700;
        letter-spacing: .04em;
        text-transform: uppercase;
        color: var(--text-secondary);
    }
    .vol-detalle-kpis b {
        font-size: .8rem;
        font-weight: 700;
    }
    /* El «±x% vs cierre anterior» del título de la semana: lleva el color
       del semáforo inline (lo decide Python) y acá sólo el cuerpo. Era
       negrita 700 a 1rem, más fuerte que el propio título. */
    .vol-detalle-delta {
        flex: 0 0 auto;
        font-size: .8rem;
        font-weight: 600;
        white-space: nowrap;
    }

    /* ── VOLATILIDAD: título de la semana + «1 semana | 5 semanas» ─────
       2026-09-13. Una fila: el título (un `st.empty` con markdown) se
       estira y el control mide lo suyo. El control, con el alto y la
       letra de la píldora «Volatilidad» de la cabecera (`vol_hdr_ver`,
       arriba), para que no parezca otro componente. Acotado a SUS keys:
       el aviso de CLAUDE.md sobre reglas del contenedor. Regla #412. */
    /* Los DOS títulos de la fila de abajo sin el `margin-bottom: -16px` de
       la regla #162 (el mismo arreglo que `vol_fila_hdr`, arriba). Medido:
       el de la izquierda se comía 16 de los 18px de aire que lo separan
       del gráfico —quedaban 2—, y el de la derecha medía 6px de caja con
       21 de texto, así que al centrarlo contra el selector el texto
       colgaba por debajo del botón. */
    .st-key-compras_vol_cuerpo
        [data-testid="stMarkdownContainer"]:has(.vol-detalle-hdr) {
        margin-bottom: 0 !important;
    }
    .st-key-vol_sem_hdr {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 10px !important;
    }
    .st-key-vol_sem_hdr > [data-testid="stElementContainer"]:first-child {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        width: auto !important;
    }
    /* Por PREFIJO: la key lleva el número de velas a la vista
       (`compras_vol_tabla_modo_4`), para que cambiarlo no deje una sesión
       abierta con una opción que ya no existe. */
    .st-key-vol_sem_hdr > [class*="st-key-compras_vol_tabla_modo_"] {
        flex: 0 0 auto !important;
        width: auto !important;
    }
    [class*="st-key-compras_vol_tabla_modo_"] [data-testid="stButtonGroup"] button {
        min-height: 26px !important;
        height: 26px !important;
        padding: 0 10px !important;
        font-size: 12px !important;
    }
    /* ── VOLATILIDAD: LA FILA DE LA SERIE ─────────────────────────────
       2026-09-20. Un renglón para los controles de la SERIE: el grano
       (`Semana | Compra`), el deslizador de la ventana y, en el grano
       Compra, la leyenda de proveedores.

       LOS TRES EN UNA FILA Y NO EN TRES RENGLONES porque el presupuesto de
       esta tarjeta ya estaba cerrado: la figura mide 180px
       (`alturas.MINI_CANDLE_DRILL`) y la fila de los KPIs de arriba mide
       473px de contenido nowrap contra los 454 de la columna. El
       deslizador ya vivía acá siendo una raya de 6px; el toggle y la
       leyenda se le suman al costado y la fila entera cuesta ~20px.

       El deslizador es el ELÁSTICO: mide lo que sobra. Los otros dos miden
       su contenido. Y el `margin-bottom: -10px` con el que el deslizador
       se pegaba a las velas ahora lo lleva la FILA, no él: adentro de un
       flex, un margen negativo en un ítem le corre la línea de base a sus
       vecinos. */
    .st-key-vol_grano_fila {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 10px !important;
        margin-bottom: -10px !important;
    }
    .st-key-vol_grano_fila > [data-testid="stElementContainer"] {
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: 0 !important;
        margin-bottom: 0 !important;
    }
    .st-key-vol_grano_fila [class*="st-key-compras_vol_vslider_"] {
        flex: 1 1 auto !important;
        min-width: 60px !important;
        margin-bottom: 0 !important;
    }
    .st-key-vol_grano_fila [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    /* El toggle del grano, con el alto y la letra de las otras dos
       botoneras de la vista (`compras_vol_tabla_modo_`, `vol_hdr_ver`):
       tres controles del mismo tamaño no se leen como tres componentes
       distintos. */
    .st-key-compras_vol_grano [data-testid="stButtonGroup"] button {
        min-height: 26px !important;
        height: 26px !important;
        padding: 0 10px !important;
        font-size: 12px !important;
    }
    /* La leyenda de proveedores del grano Compra. El color del punto llega
       INLINE en `--punto` (lo escribe `volatilidad.py::
       _vol_colores_proveedor`, que lo saca de `tema.PALETA_SERIES`): es un
       dato, no un estilo, y por eso no puede vivir acá — cuál proveedor se
       lleva cuál color depende de a quién se le compró más. */
    .vol-leyenda {
        display: flex;
        align-items: center;
        gap: 9px;
        white-space: nowrap;
        overflow: hidden;
        font-size: 10px;
        color: var(--text-secondary);
    }
    .vol-leyenda > span {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .vol-leyenda > span::before {
        content: "";
        flex: 0 0 auto;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--punto, var(--accent));
    }

    /* El deslizador de la ventana (`volatilidad.py::_K_VFIN` en el grano
       Semana, `_K_CFIN` en el de Compra — los dos llevan el mismo prefijo
       de key a propósito, para que este bloque no tenga que duplicarse):
       la etiqueta sobre el tirador, a la talla de los rótulos del eje del
       gráfico que tiene encima, no a la del cuerpo. */
    [class*="st-key-compras_vol_vslider_"] [data-testid="stSliderThumbValue"] {
        font-size: 11px !important;
    }
    /* SIN LAS FECHAS DE LAS PUNTAS (2026-09-13, a pedido). Con ellas la
       vista mostraba TRES fechas —el eje del gráfico, la etiqueta del
       tirador y los dos extremos del recorrido— y la pregunta fue
       «explicame esto, veo hasta 3 datos de fecha». Los extremos son lo
       que menos se usa: el tirador ya dice a dónde va, y el eje, lo que
       se ve. Regla #412. */
    [class*="st-key-compras_vol_vslider_"] [data-testid="stSliderTickBar"] {
        display: none !important;
    }
    /* LA LÍNEA-BOTÓN (2026-09-13, a pedido: «hacer minimalista ese
       deslizador; no me parece que ocupe una fila abajo de todo, quizás
       arriba con una línea botón»). Python lo dibuja entre el título del
       insumo y el gráfico, y acá queda en una raya y un punto:

       · SIN RELLENO. Streamlit pinta el riel con un degradado que colorea
         desde el inicio hasta el punto, que dice «cuánto» — y una ventana
         no es una cantidad. El riel entero va en el gris de las líneas.
       · El TRAMO sólo al pasarle el mouse o con el foco (o sea, mientras
         se arrastra): quieto, lo dice el eje X del gráfico de abajo.
       · ALINEADA CON EL ÁREA DE DIBUJO: 35px a la izquierda (lo que miden
         los rótulos «S/ 20» del eje Y) y 10 a la derecha (el margen de la
         figura), para que se lea como parte del gráfico.
       · 6px de caja arriba y abajo y no 20: esos 20 eran el sitio del
         rótulo y de las puntas, que ya no ocupan lugar. Y se come 10 del
         `gap` de abajo, para quedar pegada a las velas.

       El riel es el primer hijo del div con padding, sin testid propio
       (medido en Streamlit 1.59). Regla #412. */
    /* El `-10px` con el que se pegaba a las velas se mudó a la FILA
       (`.st-key-vol_grano_fila`, arriba) el 2026-09-20: adentro de un flex
       le corría la línea de base al toggle y a la leyenda. */
    [class*="st-key-compras_vol_vslider_"] [role="group"] {
        padding: 0 10px 0 35px !important;
    }
    [class*="st-key-compras_vol_vslider_"] [role="group"] > div {
        padding: 6px 0 !important;
    }
    [class*="st-key-compras_vol_vslider_"] [role="group"] > div > div:first-child {
        background-image: none !important;
        background-color: var(--border) !important;
    }
    [class*="st-key-compras_vol_vslider_"] [data-testid="stSliderThumbValue"] {
        opacity: 0;
        transition: opacity .15s ease;
    }
    [class*="st-key-compras_vol_vslider_"]:hover [data-testid="stSliderThumbValue"],
    [class*="st-key-compras_vol_vslider_"]:focus-within [data-testid="stSliderThumbValue"] {
        opacity: 1;
    }

    /* ── VOLATILIDAD: la grilla ocupa SU columna, siempre ─────────────
       Streamlit le escribe al iframe de un componente el ancho que la
       columna medía CUANDO se renderizó, como atributo HTML
       (`width="587.0625"`), y no lo vuelve a tocar hasta el siguiente
       rerun. Plegar el rail de la izquierda ensancha la columna a 731px sin
       rerun: la grilla se quedaba dibujada en 587 con ~190px de vacío al
       lado, y sus siete columnas-semana apretadas en 46px. Medido en el
       navegador el 2026-09-07 — es la mitad del "se ven apretadas" que
       reportó el usuario con captura.

       Un atributo de presentación lo gana cualquier regla CSS, así que con
       esto el iframe sigue a su columna. La otra mitad —el div de adentro,
       que st_aggrid dibuja con el mismo ancho escrito a mano— y el
       re-reparto de las columnas viven en `tablas/compras_volatilidad.py`
       (`#gridContainer` en su `custom_css` y `_REPARTIR_ANCHO`): tres
       piezas para un solo gesto, porque el iframe parte el CSS en dos
       documentos.

       Desde el 2026-09-12 vale también para la tabla de compras de la
       semana, que pasó de `st.dataframe` a AgGrid (regla #396) y tiene el
       mismo iframe con el mismo ancho escrito a mano. */
    .st-key-compras_vol_rank_grid iframe,
    [class*="st-key-compras_vol_semana_grid_"] iframe,
    /* Y las dos del detalle de Semanal (documentos | líneas), desde el
       2026-09-14 (#440): el mismo componente, el mismo ancho escrito a mano.
       Por PREFIJO: su key lleva el período y la compra elegida. */
    [class*="st-key-compras_sem_docs_grid_"] iframe,
    [class*="st-key-compras_sem_lineas_grid_"] iframe {
        width: 100% !important;
    }
    /* Y en BLOQUE, las dos de Semanal: el iframe de un componente nace
       `display: inline`, apoyado en la línea de base, y su contenedor le
       suma debajo el hueco de los descendentes (line-height 25.6px). Medido
       (2026-09-14, #440): iframe 192, contenedor 200 — la tarjeta pasaba de
       571 a 578 al abrir el detalle, y tiene que medir lo mismo con foco o
       sin él (#398). Sólo estas dos: las de Volatilidad miden contra ese
       hueco desde hace días y moverlas es otro cambio. */
    [class*="st-key-compras_sem_docs_grid_"] iframe,
    [class*="st-key-compras_sem_lineas_grid_"] iframe {
        display: block !important;
    }

    /* ── TABLA: el selector de ventana, pegado a la derecha ────────────
       2026-09-06. La sección «Tabla» de Compras no tiene cabecera (el
       nombre lo pone el rail), así que su selector no comparte renglón con
       nada: va solo, alineado con el borde derecho de la grilla que
       encabeza. Mismo ancho (90px) y mismo alto (26px) que el gemelo de
       Volatilidad — son el MISMO control y tienen que verse igual. */
    .st-key-tabla_fila_hdr {
        display: flex !important;
        flex-direction: row !important;
        justify-content: flex-end !important;
        width: 100% !important;
        margin: 0 0 6px !important;
    }
    .st-key-tabla_fila_hdr > [data-testid="stElementContainer"],
    .st-key-tabla_fila_hdr > [data-testid="stLayoutWrapper"] {
        flex: 0 0 auto !important;
        width: 90px !important;
    }
    .st-key-tabla_fila_hdr [data-testid="stElementToolbar"] { display: none; }
    .st-key-tabla_fila_hdr .react-aria-ComboBox,
    .st-key-tabla_fila_hdr .react-aria-ComboBox > div,
    .st-key-tabla_fila_hdr [data-baseweb="select"] > div {
        min-height: 26px !important;
        height: 26px !important;
        font-size: 12px !important;
    }
    .st-key-tabla_fila_hdr .react-aria-ComboBox [role="button"],
    .st-key-tabla_fila_hdr .react-aria-ComboBox input {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        font-size: 12px !important;
    }
    /* ── VOLATILIDAD: el segmentador de fecha, tercer item de la fila ──
       2026-09-06, a pedido. Lo dibuja `base.py::selector_fecha_tarjeta`,
       que trae su PROPIA fila (`cp_vol_fila`) — pensada para ser LA
       cabecera de una tarjeta, con `width: 100%` y `space-between`. Aca
       esa fila cae DENTRO de otra, asi que se la devuelve a su contenido:
       si no, se come el renglon y el titulo salta abajo.

       Van las dos mitades: el `stLayoutWrapper` anonimo que Streamlit mete
       entre el flex y el container (nace en `width: 100%`, regla #272) y
       el `stVerticalBlock` que lleva la key. El resto del look del control
       —pildora, panel, riel— vive en `graficos/compras/_css_proveedor.py`
       con los otros tres prefijos, que es donde tiene que estar por
       posicion en la cascada (regla #320). */
    .st-key-vol_fila_hdr
        > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_vol_fila) {
        flex: 0 0 auto !important;
        width: auto !important;
    }
    .st-key-cp_vol_fila {
        width: auto !important;
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        margin: 0 !important;
    }

    .chart-card-hdr.vap-hdr {
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin: 0 !important;
        padding: 0 !important;
        border-bottom: none !important;
    }
    .chart-card-hdr.vap-hdr > span {
        margin-left: auto;
        font-weight: 500;
        color: var(--text-secondary);
        /* El ámbito CEDE: el nombre de la vista es fijo y corto, el ítem
           en foco puede ser una razón social larga. `min-width: 0` es
           obligatorio o un flex item no baja de su contenido y empujaría
           el renglón fuera de la tarjeta en vez de truncar. */
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* ============================================================
       CARDS EXTERIORES DE LOS DASHBOARDS DE GRÁFICOS

       Convención en Python: `st.container(border=True, key="ajuste_graf_
       card_...")` para envolver cada dashboard. Aquí en CSS reemplazamos
       ese borde por un look plano (fondo blanco + radius grande + sombra
       tenue) y anulamos también los bordes internos que _card() añade a
       los paneles hijos (para no doble-marcar).

       Efecto neto: el usuario ve UNA card grande sin líneas internas,
       no una malla de cajas anidadas.

       EXCEPCIÓN (dashboard de Compras / drill Proveedor):
       Ahí SÍ queremos ver cada bloque bordeado (gráfico, paneles A/B,
       tabla) — el usuario lo pidió así (2026-07-25). Por eso el
       container externo de ese caso se declara SIN `border=True` en
       graficos/compras/proveedor.py, y cada bloque interno lleva su propio
       `border=True`. Así las reglas de abajo no le aplican (no hay
       nada que anular).

       Al modificar: pensar primero si el cambio afecta a los cards
       "clásicos" (Volatilidad, Vs año pasado, ...) o a los del drill
       Proveedor.
       ============================================================ */
    div[class*="st-key-ajuste_graf_card_"] {
        background: var(--bg-card) !important;
        border: none !important;                    /* look plano: sin borde de Streamlit */
        border-radius: 20px !important;
        /* Padding vertical 16 -> 8 el 2026-08-15. Medido: entre el final de la
           franja (y=36) y el título de la tarjeta había 56px, y 16 de ellos
           eran este padding. El horizontal NO se toca: la línea de la franja
           interna lo compensa con -18px y moverlo la dejaría corta.
           `_PADDING_TARJETA` en graficos/alturas.py cuenta lo mismo. */
        padding: 8px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);  /* sombra tenue reemplaza al borde */
    }
    /* Anula el borde que Streamlit pinta en el hijo directo del container
       (stVerticalBlockBorderWrapper) cuando border=True está activo. */
    div[class*="st-key-ajuste_graf_card_"] > div {
        border: none !important;
    }

    /* AJUSTE › EVOLUCIÓN (regla #504): la línea que separa la serie de los
       mini-gráficos DENTRO de la misma tarjeta — una tarjeta con dos
       lecturas, no dos tarjetas —, y la pastilla «jul 26 ✕» que dice qué
       período está resaltado. Las dos por su key/clase exacta. */
    .ajevo-divisor {
        border-top: 1px solid var(--border);
        padding-top: 6px;
        font-size: 12px;
        color: var(--text-secondary);
    }
    /* La fila de mini-gráficos se desliza de costado (regla #505): el
       ancho de la figura lo fuerza un <style> por render desde
       `_evolucion.py` (n familias × PX_PANEL). QUIEN DESLIZA NO ES
       `ajevo_multiplos` sino el `stElementContainer` de la figura, que ya
       nace con `overflow-x: auto` (medido: 1204 de ancho, 2000 de
       contenido). Acá sólo se le afina la barra. */
    .st-key-ajevo_multiplos [data-testid="stElementContainer"]::-webkit-scrollbar {
        height: 6px;
    }
    .st-key-ajevo_multiplos [data-testid="stElementContainer"]::-webkit-scrollbar-thumb {
        background: var(--scroll-thumb);
        border-radius: 3px;
    }
    .st-key-ajuste_evo_soltar button {
        min-height: 0 !important;
        padding: 3px 10px !important;
        border-radius: 999px !important;
        border: 1px solid var(--accent) !important;
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    .st-key-ajuste_evo_soltar button p {
        font-size: 12px !important;
        font-weight: 600 !important;
    }
    .st-key-ajuste_evo_soltar button:hover {
        background: var(--accent-light) !important;
    }
    /* Cards internos (Paneles A/B via `_card()`): dejar transparentes para
       que no se doble-marquen dentro del contenedor externo. */
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"],
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"] > div,
    div[class*="st-key-ajuste_graf_card_"] [class*="st-key-chartcard_"]
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* ─────────────────────────────────────────────────────────────── */
    /* LAS DOS MITADES DEL CONVERSOR SUNAT-SISTEMA                      */
    /*                                                                  */
    /* Key `sunat_conv_` a propósito, NO `sunat_card_`: aquélla es la   */
    /* familia que el bloque de arriba clampea a `--alto-util` con      */
    /* scroll propio, y estas dos viven DENTRO de una de ellas          */
    /* (`sunat_card_conversor`). Con el prefijo de la familia grande    */
    /* heredarían un segundo scroll anidado adentro del de la tarjeta   */
    /* que las contiene. Es la regla de CLAUDE.md ("antes de agregar    */
    /* un widget dentro de una tarjeta: grep estilos/") leída al revés: */
    /* elegir el prefijo que NO matchea.                                */
    /*                                                                  */
    /* BLANCAS, como su tarjeta madre y como todo Compras (a pedido     */
    /* 2026-08-27). Nacieron con el gris `--bg-card-tenue`, que es el   */
    /* MISMO `#faf9fb` del lienzo de la app: con la madre todavía       */
    /* transparente, eso dejaba dos cajas grises sobre gris. Ahora la   */
    /* madre es blanca y estas dos también; lo único que las separa es  */
    /* la línea de 1px, que alcanza para que el ojo agrupe cada tabla   */
    /* con su cabecera y lea las dos como los dos lados de una          */
    /* comparación. Sin sombra a propósito: anidar sombras dentro de la */
    /* sombra de la tarjeta madre ensucia el borde.                     */
    /*                                                                  */
    /* Y ESTE es el único marco que llevan las mitades: las tablas de   */
    /* adentro se dibujan con `_css_grid(..., marco=False)`, sin borde  */
    /* ni radio ni sombra propios. Si las dos cosas se marcan, quedan   */
    /* dos líneas de 1px con el mismo radio a diez píxeles una de otra. */
    /* Ver `_detalle_sistema` en graficos/compras/documentos_sunat.py.  */
    /* ─────────────────────────────────────────────────────────────── */
    /* `_izq`/`_der` COMPLETOS en el selector, no la familia `sunat_conv_`  */
    /* a secas. Las dos tablas de adentro tienen key                        */
    /* `sunat_conv_sunat_<doc>` y `sunat_conv_sistema_<doc>`, que CONTIENEN */
    /* la subcadena `st-key-sunat_conv_`: con el wildcard corto, este       */
    /* bloque le pegaba también a ellas y cada tabla nacía con su propia    */
    /* caja blanca redondeada de 10/12/4 de padding. Es la trampa que       */
    /* documenta CLAUDE.md («el CSS matchea por PREFIJO de key, no por      */
    /* widget») mordiendo desde adentro de la propia familia. Reportado el  */
    /* 2026-08-28 como "tarjetas dentro de tarjeta, dentro de tarjetas" y   */
    /* confirmado con el inspector, que lista esta regla entre las que      */
    /* matchean el AgGrid.                                                  */
    div[class*="st-key-sunat_conv_izq"],
    div[class*="st-key-sunat_conv_der"] {
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 10px 12px 4px !important;
        background: var(--bg-card);
    }
    /* Streamlit pinta SU borde en el hijo directo cuando border=True;
       con el de arriba puesto, serían dos líneas a 1px de distancia. */
    div[class*="st-key-sunat_conv_izq"] > div,
    div[class*="st-key-sunat_conv_der"] > div {
        border: none !important;
    }

    /* =================================================================== */
    /* ENCUADRE: UNA TARJETA = UNA PANTALLA (desktop)                        */
    /*                                                                       */
    /* Nació el 2026-08-13. Medido: 19 de 24 vistas obligaban a scrollear en */
    /* un laptop de 1366x768 porque el alto de cada tarjeta era la suma de   */
    /* píxeles fijos de sus gráficos, sin relación con la pantalla.          */
    /*                                                                       */
    /* max-height y NO height, por dos razones distintas:                    */
    /*   1. Con `height` las tarjetas CORTAS se estirarían a pantalla        */
    /*      completa dejando un vacío enorme (Volatilidad mide 88px).        */
    /*   2. `height` directamente NO APLICA: los bloques de Streamlit son    */
    /*      flex items con `flex: 1 1 0%`, y en un contenedor flex de        */
    /*      columna el tamaño principal lo fija flex-basis, no height        */
    /*      (verificado en el navegador: con height puesto seguía midiendo   */
    /*      406px en vez de 501). `max-height` sí clampea al flex item.      */
    /*      Ver arquitectura.md regla #101.                                  */
    /*                                                                       */
    /* Lo que no entra scrollea DENTRO de la tarjeta, así que el marco       */
    /* siempre se ve completo. El alto sale de --alto-util (_00_base.py),    */
    /* que deriva de la franja superior e inferior: si alguna cambia de      */
    /* alto, esto la sigue solo.                                             */
    /*                                                                       */
    /* Solo desktop: en móvil el cromo es otro (nav inferior propia) y el    */
    /* patrón correcto es el scroll de página. Mismo breakpoint que          */
    /* _99_movil.py.                                                         */
    /* =================================================================== */
    @media screen and (min-width: 769px) {
        /* `compras_prod_card_` SALIÓ de esta lista el 2026-09-12, a pedido:  */
        /* «las tarjetas no deben deslizarse internamente […] como que el     */
        /* contenedor es muy pequeño […] solo para uso interno de la tabla». */
        /* Su tarjeta de tablas lleva DOS niveles —Familia | Subfamilia y el  */
        /* Ranking debajo— y mide ~600px: en una pantalla más baja que 768    */
        /* el techo la cortaba y le salía barra propia, además de la de cada  */
        /* grid. Dos barras anidadas se leen como una caja rota. Sin el techo */
        /* la tarjeta mide su contenido y lo que sobra lo scrollea la PÁGINA; */
        /* dentro, sólo scrollean los grids, que tienen su propio tope de     */
        /* filas. Ver regla #382.                                             */
        /*                                                                    */
        /* `ajuste_graf_card_izq_vol` (Volatilidad) salió el mismo día, por   */
        /* el mismo motivo y a pedido: «que la tarjeta mida igual que la de   */
        /* Vs año pasado», que nunca tuvo techo (no es de esta familia). Con  */
        /* la cabecera de vuelta ENCIMA de la grilla la tarjeta mide ~560, y  */
        /* con el techo, en una pantalla baja, salía la barra propia que ya   */
        /* se había pedido quitar. Va con `:not()` y no sacando el prefijo,   */
        /* que es de las tarjetas de los otros siete reportes. Regla #394.    */
        /* (Desde el 2026-09-13 esa tarjeta no existe: Volatilidad son tres   */
        /* `compras_vol_card_`, que nunca estuvieron en esta lista. #415.)    */
        /*                                                                    */
        /* `ajuste_graf_card_izq_sem` (Semanal) salió el 2026-09-13, con el   */
        /* mismo pedido en otras palabras: «que su tarjeta sea del tamaño de  */
        /* la de vs año anterior, ya que es muy larga cuando aparece el       */
        /* detalle». Con techo, la tabla del detalle la estiraba hasta        */
        /* `--alto-util` y le sacaba barra propia; ahora la figura cede su    */
        /* sitio a la tabla y la tarjeta mide lo mismo con foco o sin él.     */
        /* Regla #398.                                                        */
        /*                                                                    */
        /* El Mapa de calor YA NO ESTÁ en esta lista, y no por un `:not()`:   */
        /* desde el 2026-09-22 no tiene una card única (`ajuste_graf_card_    */
        /* izq_heatmap` desapareció) — dibuja sus propias tarjetas como la    */
        /* Cascada (la tabla y sus dos detalles, ver `graficos/ajuste/        */
        /* _heatmap.py`), ninguna con este prefijo. Antes iba excluido con    */
        /* `:not(...izq_heatmap)` por dos motivos que siguen valiendo para su */
        /* nueva tabla `chartcard_heatmap`: la grilla lleva `overflow-x:auto` */
        /* (las áreas se scrollean en X) y un eje en `auto` computa el otro a */
        /* `auto`, así que con techo la tabla se volvía ÉL el scroller y la   */
        /* fila Total se partía (reportado con captura); y el detalle abre    */
        /* DENTRO, con lo que un techo le daría barra propia. Regla #468.     */
        /*                                                                    */
        /* `ajuste_graf_card_izq_mov_periodo` (Movimientos › Requerimientos   */
        /* por período) salió al nacer, el 2026-09-23: es la gemela de        */
        /* Semanal y mide lo que ella (`alturas.SEMANAL_*`), con la figura    */
        /* cediéndole su sitio a la tabla. Regla #508. Y su hermana de        */
        /* salidas, `…_mov_sal_periodo`, el mismo día. Regla #509. Y la de    */
        /* porcionamientos, `…_mov_porc_periodo`, el 2026-09-24. Regla #510.  */
        /* Y `…_izq_ventas_resumen` (Ventas › Resumen ejecutivo) el mismo     */
        /* día: su barra por período ahora es la de Compras, con la tabla     */
        /* DENTRO de la tarjeta; con el techo sacaba barra propia. #516.      */
        div[class*="st-key-ajuste_graf_card_"]:not(.st-key-ajuste_graf_card_izq_sem):not(.st-key-ajuste_graf_card_izq_evo):not(.st-key-ajuste_graf_card_izq_mov_periodo):not(.st-key-ajuste_graf_card_izq_mov_sal_periodo):not(.st-key-ajuste_graf_card_izq_mov_porc_periodo):not(.st-key-ajuste_graf_card_izq_ventas_resumen),
        div[class*="st-key-compras_prov_card_"],
        div[class*="st-key-sunat_card_"] {
            max-height: var(--alto-util);
            overflow-y: auto;
            overflow-x: hidden;
        }
        /* (Acá vivía el padding propio de `ajuste_graf_card_izq_vol` —11     */
        /* arriba y 16 abajo, para medir lo que vap, #394/#395—. Se fue con   */
        /* la tarjeta el 2026-09-13: las tres de Volatilidad llevan el        */
        /* padding de las de Producto. #415.)                                  */
        /* Semanal, el mismo padding que vap por el mismo motivo (#398): 8   */
        /* de la familia contra 16 de vap son píxeles de diferencia que no   */
        /* son contenido. Sin tarjeta interna, acá no hay 5px que restar.    */
        div.st-key-ajuste_graf_card_izq_sem,
        div.st-key-ajuste_graf_card_izq_mov_periodo,
        div.st-key-ajuste_graf_card_izq_mov_sal_periodo,
        div.st-key-ajuste_graf_card_izq_mov_porc_periodo {
            padding-top: 16px !important;
            padding-bottom: 16px !important;
        }
        /* `ajuste_graf_card_izq_evo` (Ajuste › Evolución) salió el         */
        /* 2026-09-23: es UNA tarjeta con la serie y los mini-gráficos por   */
        /* familia debajo (~800px), a pedido, para que se vea que dependen   */
        /* una de otra. Con el techo de una pantalla sacaba barra propia; sin */
        /* él mide su contenido y lo que sobra lo scrollea la PÁGINA, igual  */
        /* que las de Producto (#382). Regla #504.                            */
        /* Barra fina y discreta, igual criterio que el panel del asistente
           (_85_asistente.py): la tarjeta ya es un marco, la barra no tiene
           que competir con el contenido. */
        div[class*="st-key-ajuste_graf_card_"]::-webkit-scrollbar,
        div[class*="st-key-compras_prov_card_"]::-webkit-scrollbar,
        div[class*="st-key-sunat_card_"]::-webkit-scrollbar {
            width: 6px;
        }
        div[class*="st-key-ajuste_graf_card_"]::-webkit-scrollbar-thumb,
        div[class*="st-key-compras_prov_card_"]::-webkit-scrollbar-thumb,
        div[class*="st-key-sunat_card_"]::-webkit-scrollbar-thumb {
            background: var(--scroll-thumb);
            border-radius: 3px;
        }

        /* ─────────────────────────────────────────────────────────────── */
        /* DOS TARJETAS EN UNA FILA MIDEN LO MISMO                          */
        /*                                                                  */
        /* La otra mitad del encuadre de arriba: aquél pone el TECHO, éste  */
        /* el PISO. Sin él, en una fila de dos columnas la tarjeta con      */
        /* menos contenido se queda corta y el borde inferior de la fila    */
        /* sale en escalón. Medido el 2026-08-21 en el drill de Proveedor,  */
        /* viewport 1536x864: Productos 393px contra Proveedores-del-       */
        /* producto 182px — 211px de escalón, y cambiando en cada clic      */
        /* porque el panel de la derecha es una lista elástica.             */
        /*                                                                  */
        /* Por qué hace falta una regla y no basta el flexbox de Streamlit: */
        /* las columnas SÍ se estiran solas (`stHorizontalBlock` tiene      */
        /* `align-items: stretch`, medido: las dos miden 393). Lo que no se */
        /* estira es el contenedor de ELEMENTO que Streamlit mete entre la  */
        /* columna y la tarjeta: nace con `flex: 0 1 auto`, o sea se ajusta */
        /* al contenido. La tarjeta ya trae `flex: 1 1 0%`, así que en      */
        /* cuanto ese contenedor crece, la tarjeta lo sigue sola.           */
        /*                                                                  */
        /* `:has()` para alcanzar al PADRE de la tarjeta, que es el único   */
        /* que se puede seleccionar por su hijo. Un navegador sin `:has()`  */
        /* ignora la regla y vuelve al escalón — degrada, no rompe.         */
        /*                                                                  */
        /* Las tarjetas van ENUMERADAS por su key exacta desde el           */
        /* 2026-09-18, y no por prefijo (`[class*="st-key-compras_prov_     */
        /* card_"]`): un atributo adentro de un `:has()` hace que cada      */
        /* cambio de clase de la página recalcule los estilos enteros —     */
        /* ~100 ms por cambio en la laptop del usuario, regla #469. Una     */
        /* tarjeta nueva de estas familias tiene que sumarse acá: lo vigila */
        /* `test_graficos.py::_pruebas_has_solo_clases`.                    */
        /*                                                                  */
        /* `sunat_card_` se sumó el 2026-08-28, al ganar Documentos SUNAT  */
        /* su primera fila de dos columnas (ficha | gráfico). Medido ahí   */
        /* mismo: la ficha llegaba a su techo de 576px y el gráfico se     */
        /* quedaba en 407 — 169px de escalón, exactamente el síntoma que   */
        /* describe el bloque de arriba. `ajuste_graf_card_` sigue afuera: */
        /* sus tarjetas no comparten fila, así que no hay nada que igualar.*/
        /* ─────────────────────────────────────────────────────────────── */
        .stColumn > .stVerticalBlock
        > div:has(> .st-key-compras_prov_card_docs, > .st-key-compras_prov_card_evo, > .st-key-compras_prov_card_prods, > .st-key-compras_prov_card_provde, > .st-key-compras_prov_card_ranking, > .st-key-compras_prov_card_vacio),
        .stColumn > .stVerticalBlock
        > div:has(> .st-key-sunat_card_conversor, > .st-key-sunat_card_doc, > .st-key-sunat_card_graf, > .st-key-sunat_card_izq, > .st-key-sunat_card_sis),
        /* Las dos mitades del conversor entraron acá el 2026-08-29, al   */
        /* ganar cada una un pie de totales de largo distinto: la de      */
        /* SUNAT medía 388px y la del sistema 349 en el documento de      */
        /* MAPFRE, porque una llevaba un aviso de descuadre y la otra no. */
        /* Mientras los dos lados tuvieron contenido simétrico el piso no */
        /* hizo falta; en cuanto uno pudo crecer solo, sí.                */
        .stColumn > .stVerticalBlock
        > div:has(> .st-key-sunat_conv_izq, > .st-key-sunat_conv_der),
        /* `compras_prod_card_` entró el 2026-09-02, cuando el Ranking de   */
        /* Productos partió su tarjeta única en dos (tabla | gráfico) y     */
        /* pasó a tener, por primera vez, una FILA de dos tarjetas. Sin el  */
        /* piso, el gráfico y la tabla cierran en alturas distintas y el    */
        /* borde inferior de la fila sale en escalón — el mismo síntoma que */
        /* originó esta regla. Desde el 2026-09-12 la tarjeta del ranking   */
        /* lleva ADEMÁS los paneles de Familia/Subfamilia (antes eran una   */
        /* tarjeta de ancho completo, arriba), y la Evolución se dimensiona */
        /* contra ella (`_ALTO_EVO` en graficos/compras/producto.py): este  */
        /* piso queda de red, igual que en Proveedor.                       */
        .stColumn > .stVerticalBlock
        > div:has(> .st-key-compras_prod_card_evo, > .st-key-compras_prod_card_ranking, > .st-key-compras_prod_card_vacio),
        /* Las dos tarjetas de abajo de Volatilidad (velas | compras de la  */
        /* semana), desde que se separaron el 2026-09-13 (#415): la tabla   */
        /* de la semana mide lo que tenga filas y sin piso cerraba más      */
        /* arriba que el gráfico.                                            */
        .stColumn > .stVerticalBlock
        > div:has(> .st-key-compras_vol_card_rank, > .st-key-compras_vol_card_semana, > .st-key-compras_vol_card_velas),
        /* Y las dos del medio de Vs año pasado (serie | puente), desde el   */
        /* 2026-09-14 (#420). Hoy nacen del mismo alto (`_ALTO_FIG_VAP`, el */
        /* puente le resta su veredicto); el piso queda de red.             */
        .stColumn > .stVerticalBlock
        > div:has(> .st-key-compras_vap_card_hdr, > .st-key-compras_vap_card_puente, > .st-key-compras_vap_card_serie, > .st-key-compras_vap_card_tabla),
        /* Los cinco cuadros de Movimientos › «Detalle de salidas»          */
        /* (2026-09-24, regla #511), tres arriba y dos abajo. Cada grilla   */
        /* mide las filas que trae hasta ocho, así que sin piso la fila de  */
        /* arriba cerraba en escalón: 7 tipos de baja, 10 áreas, 6          */
        /* familias. Son la primera fila de `ajuste_graf_card_` que entra   */
        /* acá; las de la cadena de Inventario y de «Por sub almacén»       */
        /* siguen sin piso (#411). Las keys las arma                        */
        /* `drill_tablas.claves_tarjetas_cuadros`, y                        */
        /* `test_graficos.py::_pruebas_detalle_salidas` exige verlas acá.   */
        .stColumn > .stVerticalBlock
        > div:has(> .st-key-ajuste_graf_card_izq_mov_detsal, > .st-key-ajuste_graf_card_der_mov_detsal, > .st-key-ajuste_graf_card_der_mov_detsal_n2, > .st-key-ajuste_graf_card_der_mov_detsal_n3, > .st-key-ajuste_graf_card_der_mov_detsal_n4) {
            flex: 1 1 auto;
        }

        /* Acá vivió, durante un rato del 2026-09-01, una EXCEPCIÓN para    */
        /* `compras_prov_card_ranking` (`flex: 0 1 auto`): el piso lo       */
        /* estiraba a los 383px de la Evolución de al lado y esos px eran   */
        /* blanco, porque su tabla tiene tope propio y no tiene con qué     */
        /* llenarlos. Se fue el mismo día, al pedirse que las dos tarjetas  */
        /* midieran igual: el arreglo correcto no era eximir al Ranking     */
        /* sino que la Evolución dejara de pedir un alto que no sale de los */
        /* datos. Hoy su figura se calcula RESTÁNDOLE su cromo al alto de   */
        /* la tarjeta del Ranking (`_ALTO_EVO` en                           */
        /* graficos/compras/proveedor.py), así que las dos nacen iguales y  */
        /* este piso no tiene nada que estirar — queda de red para el       */
        /* único caso en que difieren, el piso de la figura con 4           */
        /* proveedores o menos. Ver regla #276.                             */
    }

    /* =================================================================== */
    /* TARJETAS DEL DRILL DE PROVEEDOR (Compras)                             */
    /*                                                                       */
    /* Convención independiente de `ajuste_graf_card_*`: el drill de         */
    /* Proveedor NO usa un wrapper blanco único, sino 3 bloques separados    */
    /* por el gris del app. Cada bloque declara su key con prefijo           */
    /* `compras_prov_card_` y esta regla les pinta el fondo blanco propio.   */
    /*                                                                       */
    /* No tocar sin revisar `_compras_proveedor_drill` en graficos/compras/proveedor.py*/
    /* =================================================================== */
    div[class*="st-key-compras_prov_card_"] {
        background: var(--bg-card) !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
    }
    /* Anula el borde interno que Streamlit pinta cuando border=True. */
    div[class*="st-key-compras_prov_card_"] > div {
        border: none !important;
    }
    /* Cards internos (Paneles A/B via `_card()`): transparentes para
       no doble-marcar dentro de la tarjeta blanca del bloque. */
    div[class*="st-key-compras_prov_card_"] [class*="st-key-chartcard_"],
    div[class*="st-key-compras_prov_card_"] [class*="st-key-chartcard_"] > div,
    div[class*="st-key-compras_prov_card_"] [class*="st-key-chartcard_"]
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: transparent !important;
        box-shadow: none !important;
    }

    /* =================================================================== */
    /* TARJETAS DEL DRILL DE PRODUCTO (Compras)                              */
    /*                                                                       */
    /* Misma convención que el bloque de Proveedor de arriba: 2 bloques      */
    /* separados por el gris del app (familia+subfamilia+ranking |           */
    /* evolución), cada uno con key con prefijo `compras_prod_card_`.        */
    /*                                                                       */
    /* No tocar sin revisar `_compras_producto_drill` en graficos/compras/producto.py */
    /* =================================================================== */
    /* Las tres de Volatilidad (`compras_vol_card_`) llevan el MISMO look   */
    /* desde el 2026-09-13, cuando su tarjeta única se partió en tres. #415 */
    /* Y las cuatro de Vs año pasado (`compras_vap_card_`), desde el        */
    /* 2026-09-14, por el mismo pedido. #420                                */
    div[class*="st-key-compras_prod_card_"],
    div[class*="st-key-compras_vol_card_"],
    div[class*="st-key-compras_vap_card_"] {
        background: var(--bg-card) !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
    }
    div[class*="st-key-compras_prod_card_"] > div,
    div[class*="st-key-compras_vol_card_"] > div,
    div[class*="st-key-compras_vap_card_"] > div {
        border: none !important;
    }
    div[class*="st-key-compras_prod_card_"] + div[class*="st-key-compras_prod_card_"] {
        margin-top: 16px;
    }

    /* =================================================================== */
    /* TARJETAS DEL DRILL DE DOCUMENTOS SUNAT (Compras)                      */
    /*                                                                       */
    /* Misma convención y los MISMOS valores que los dos bloques de arriba   */
    /* (Proveedor y Producto): 3 bloques apilados —tabla, ficha+original,    */
    /* conversor— separados por el gris del app, cada uno blanco con su      */
    /* sombra tenue. A pedido 2026-08-27: hasta ese día estas tres eran las  */
    /* únicas tarjetas de Compras que se quedaban con el marco POR DEFECTO   */
    /* de `st.container(border=True)` — fondo transparente y una línea gris  */
    /* de Streamlit (medido: `rgba(49,51,63,.2)`, radio 8px, sin sombra) —,  */
    /* así que el reporte cambiaba de idioma visual al llegar a Documentos.  */
    /*                                                                       */
    /* El cromo vertical NO cambia y por eso no hay que retocar ningún alto: */
    /* antes eran 15px de padding + 1px de borde = 16 por lado; ahora son    */
    /* 16 de padding + 0 de borde. Mismo total.                              */
    /*                                                                       */
    /* No tocar sin revisar `renderizar_documentos_sunat` en                 */
    /* graficos/compras/documentos_sunat.py                                  */
    /* =================================================================== */
    div[class*="st-key-sunat_card_"] {
        background: var(--bg-card) !important;
        border: none !important;
        border-radius: 20px !important;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
    }
    /* Anula el borde interno que Streamlit pinta cuando border=True. */
    div[class*="st-key-sunat_card_"] > div {
        border: none !important;
    }

    /* =================================================================== */
    /* «Nueva receta» (Recetas y Costos): DOS tarjetas                      */
    /*                                                                       */
    /* Desde el 2026-09-24 (mockup aprobado ese día) la vista son dos       */
    /* tarjetas lado a lado: «Receta» (form_receta_card_receta) y «Precio   */
    /* de venta» (form_receta_card_precio). El `rec_card_nueva` que pone el */
    /* dispatcher sigue envolviéndolas, pero ya no pinta nada: si llevara   */
    /* el fondo blanco, las dos tarjetas se leerían como una caja con dos   */
    /* cajas adentro. Las dos miden al menos una pantalla (`--alto-util`)   */
    /* en escritorio; el alto de la tabla de insumos y de la torta lo pone  */
    /* Python para que ese mínimo sea también lo justo. Regla #512.         */
    /* =================================================================== */
    div.st-key-rec_card_nueva {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
        box-shadow: none !important;
    }
    div.st-key-rec_card_nueva > div {
        border: none !important;
    }
    .st-key-form_receta_card_receta,
    .st-key-form_receta_card_precio {
        background: var(--bg-card);
        border-radius: 20px;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
        gap: 12px !important;
    }
    @media screen and (min-width: 769px) {
        .st-key-form_receta_card_receta,
        .st-key-form_receta_card_precio {
            min-height: var(--alto-util);
        }
    }
    /* Nada adentro se encoge: si el contenido pasa del alto de la tarjeta,
       Streamlit aplasta sus hijos (`flex: 0 1 auto`) y la tabla de precios
       se recortaba por abajo en vez de crecer la tarjeta. */
    .st-key-form_receta_card_receta > *,
    .st-key-form_receta_card_precio > *,
    .st-key-form_receta_ptabla > * {
        flex-shrink: 0 !important;
    }
    /* Streamlit le pone `margin-bottom: -1rem` al stMarkdownContainer para
       comerse el margen del último <p>. Acá los st.markdown son <div>, sin
       ese margen: el -16 montaba cada fila sobre la siguiente (la del
       precio de venta tapaba la del costo). Regla #162. */
    .st-key-form_receta_card_receta [data-testid="stMarkdownContainer"],
    .st-key-form_receta_card_precio [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    /* El pie (Guardar, PDF, Excel, correo) va contra el borde de abajo de
       la tarjeta aunque en una pantalla grande sobre alto. */
    .st-key-form_receta_pie {
        margin-top: auto;
        padding-top: 12px;
        border-top: 1px solid var(--line-soft);
    }
    /* Botón "+" al costado del buscador: alto igual al selectbox
       (~40px) y ancho fijo por su glifo. Las keys (2) las escribe
       `formulario_receta._key(modo, "add_sel"/"add_nuevo")`. */
    div[class^="st-key-form_receta_"][class$="_add_sel"] button,
    div[class^="st-key-form_receta_"][class$="_add_nuevo"] button {
        min-height: 38px !important;
        padding: 0 10px !important;
    }

    /* Rótulos sueltos de las dos tarjetas (los escribe formulario_receta
       como HTML en st.markdown). */
    .fr-titulo {
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
    }
    .fr-titulo-2 {
        font-size: 13.5px;
        font-weight: 600;
        color: var(--text-primary);
    }
    .fr-cab {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        min-height: 32px;
    }
    .fr-sub, .fr-pista, .fr-nota {
        font-size: 12px;
        color: var(--text-muted);
    }
    .fr-resumen {
        text-align: right;
        white-space: nowrap;
        font-size: 12.5px;
        color: var(--text-secondary);
        font-variant-numeric: tabular-nums;
    }
    .fr-chip {
        display: inline-block;
        max-width: 100%;
        box-sizing: border-box;
        height: 26px;
        line-height: 26px;
        padding: 0 10px;
        border-radius: 999px;
        background: var(--accent-tint);
        color: var(--accent-deep);
        font-size: 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-variant-numeric: tabular-nums;
    }
    /* El hueco de una tabla o de la torta sin datos: mide lo mismo que lo
       que reemplaza, para que la tarjeta no salte. */
    .fr-vacio {
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        padding: 24px;
        border: 1px dashed var(--border);
        border-radius: 8px;
        text-align: center;
        font-size: 13px;
        line-height: 1.5;
        color: var(--text-muted);
    }
    .fr-perdida {
        padding: 10px 12px;
        border: 1px solid var(--warning-border);
        border-radius: 8px;
        background: var(--warning-bg);
        color: var(--warning-text);
        font-size: 13px;
        line-height: 1.45;
    }
    .fr-punto {
        display: inline-block;
        width: 8px;
        height: 8px;
        flex-shrink: 0;
        border-radius: 50%;
    }

    /* TABLA DE PRECIOS. HTML, salvo la fila del precio de venta, que es un
       st.number_input dentro de `form_receta_prow` (st.columns sin gap con
       las MISMAS proporciones que estas grillas: 2.3/1.4 con una columna
       de montos y 2.3/1/1.2 con Actual y Nuevo). Si cambia una, cambia la
       otra, o la celda editable deja de caer bajo su cabecera. */
    .st-key-form_receta_ptabla {
        flex: 0 0 auto !important;
        gap: 0 !important;
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
    }
    .fr-p-fila {
        display: grid;
        grid-template-columns: 2.3fr 1.4fr;
        align-items: center;
        height: 32px;
        border-bottom: 1px solid var(--line-soft);
        font-size: 13.5px;
        color: var(--text-primary);
        font-variant-numeric: tabular-nums;
    }
    .fr-p-dos .fr-p-fila {
        grid-template-columns: 2.3fr 1fr 1.2fr;
    }
    .fr-p-fila > div {
        min-width: 0;
        padding: 0 10px;
    }
    .fr-p-dos .fr-p-fila > div:nth-child(2) {
        color: var(--text-secondary);
    }
    .fr-p-cab {
        background: var(--bg-primary);
        border-bottom-color: var(--border);
        font-size: 12px;
        font-weight: 500;
        color: var(--text-secondary);
    }
    .fr-p-una > .fr-p-fila:last-child,
    .fr-p-dos > .fr-p-fila:last-child {
        border-bottom: none;
    }
    .fr-p-num {
        text-align: right;
    }
    .fr-p-neg {
        color: var(--danger-text) !important;
    }
    .fr-p-concepto {
        display: flex;
        align-items: center;
        gap: 8px;
        white-space: nowrap;
        overflow: hidden;
    }
    .fr-p-concepto > span:last-child {
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .st-key-form_receta_prow {
        height: 36px;
        justify-content: center;
        background: var(--rail-fondo);
        border-bottom: 1px solid var(--line-soft);
        font-size: 13.5px;
        font-weight: 600;
        color: var(--text-primary);
        font-variant-numeric: tabular-nums;
    }
    .st-key-form_receta_prow .fr-p-concepto,
    .st-key-form_receta_prow .fr-p-num {
        padding: 0 10px;
    }
    .st-key-form_receta_prow .fr-p-num {
        font-weight: 400;
        color: var(--text-secondary);
    }
    .st-key-form_receta_prow [data-testid="stNumberInputStepDown"],
    .st-key-form_receta_prow [data-testid="stNumberInputStepUp"] {
        display: none !important;
    }
    .st-key-form_receta_prow [data-testid="stNumberInputContainer"] {
        height: 28px !important;
        margin-right: 6px;
        border-color: var(--focus-lavender) !important;
        border-radius: 6px !important;
    }
    .st-key-form_receta_prow input {
        text-align: right;
        font-weight: 600;
        font-size: 13.5px !important;
        padding: 0 8px !important;
    }

    /* Semáforo del % de costo y leyenda de la torta. */
    .fr-semaforo {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        font-size: 12.5px;
        color: var(--text-secondary);
    }
    .fr-semaforo b {
        font-weight: 600;
        color: var(--text-primary);
        font-variant-numeric: tabular-nums;
    }
    .fr-flecha {
        color: var(--text-muted);
    }
    .fr-ley-fila {
        display: grid;
        grid-template-columns: 10px minmax(0, 1fr) auto 44px;
        align-items: center;
        gap: 6px;
        padding: 4px 6px;
        font-size: 13px;
        font-variant-numeric: tabular-nums;
    }
    .fr-ley-fila .fr-punto {
        width: 10px;
        height: 10px;
    }
    .fr-ley-rot {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: var(--text-primary);
    }
    .fr-ley-num {
        text-align: right;
        color: var(--text-primary);
    }
    .fr-ley-pct {
        text-align: right;
        color: var(--text-secondary);
    }
    .fr-ley-total {
        margin-top: 4px;
        padding-top: 8px;
        border-top: 1px solid var(--border);
        font-weight: 600;
    }
    .fr-ley-total .fr-ley-pct {
        font-weight: 400;
    }

    /* =================================================================== */
    /* KPI "Valorizado total" DE INVENTARIO — minimalista                    */
    /*                                                                       */
    /* Único st.metric de esa tarjeta (.st-key-ajuste_graf_card_izq_inv,     */
    /* clase EXACTA, no el prefijo wildcard de arriba: no tocar el metric    */
    /* de Salidas ni ningún otro). Con el ranking ya achicado en foco        */
    /* (graficos/inventario.py — click-drill), el número gigante por         */
    /* default de Streamlit competía por atención con el gráfico que el      */
    /* usuario acaba de pedir con el clic.                                   */
    /* =================================================================== */
    .st-key-ajuste_graf_card_izq_inv [data-testid="stMetricValue"] {
        font-size: 22px !important;
        line-height: 1.25 !important;
    }
    .st-key-ajuste_graf_card_izq_inv [data-testid="stMetricLabel"] {
        font-size: 11px !important;
    }
    .st-key-ajuste_graf_card_izq_inv [data-testid="stMetric"] {
        gap: 2px !important;
    }

    /* =================================================================== */
    /* KPIs del "Resumen ejecutivo" de Ventas — 5 cajas chicas en fila       */
    /*                                                                       */
    /* Wildcard por prefijo de key (graficos/ventas_resumen.py): cada KPI   */
    /* es su propio st.container(border=True, key="ventas_resumen_kpi_..."). */
    /* Sin este bloque quedaban al tamaño default de Streamlit — grandes y   */
    /* compitiendo por atención con el candlestick de abajo, que es el       */
    /* protagonista real de la vista. Sin ícono (se sacó del label en       */
    /* Python): con la caja ya chica, el emoji quedaba desproporcionado.    */
    /* =================================================================== */
    /* width: fit-content — sin esto, el container de Streamlit ocupa el
       100% de su columna (~1/5 del ancho de la card) aunque el texto sea
       corto, y la caja sale como una barra larga con aire de sobra. */
    div[class*="st-key-ventas_resumen_kpi_"] {
        border-radius: 10px !important;
        padding: 6px 10px !important;
        width: fit-content !important;
        max-width: 100% !important;
    }
    /* Label + valor en la MISMA línea. stMetric NO tiene label/valor como
       hijos directos: envuelve todo en UN div intermedio (sin data-testid
       propio, clase emotion-cache no estable) que es el que hay que poner
       en flex-row — ponerlo en stMetric no hace nada porque stMetric solo
       tiene ESE div como único hijo. `> div` apunta a ese wrapper por
       estructura, no por clase generada. */
    div[class*="st-key-ventas_resumen_kpi_"] [data-testid="stMetric"] > div {
        display: flex !important;
        flex-direction: row !important;
        align-items: baseline !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }
    div[class*="st-key-ventas_resumen_kpi_"] [data-testid="stMetricValue"] {
        font-size: 13px !important;
        line-height: 1.15 !important;
    }
    div[class*="st-key-ventas_resumen_kpi_"] [data-testid="stMetricLabel"] {
        font-size: 8px !important;
        white-space: nowrap !important;
    }

    /* Fila de KPI de «Tendencia diaria de venta» (2026-09-24, regla #515):
       el total de la vista y lo de cada canal. Es el mismo dibujo que la
       `.sem-kpis` de «Compras por período» (`_css_proveedor.py`), con una
       marca de color por canal —la de su tramo en la barra— para que la
       fila haga también de leyenda. Vive acá y no allá porque ese CSS sólo
       se inyecta en Compras. */
    .st-key-vt_resumen_kpi [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    /* El título y los KPI en un renglón (regla #519): el look de
       `.chart-card-hdr` —mismo cuerpo, peso y color, y la línea abajo— pero
       compartiendo el flex con los KPI. */
    .st-key-vt_resumen_kpi .vt-cab {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 4px 22px;
        padding: 0 0 6px;
        border-bottom: 1px solid var(--border);
    }
    .st-key-vt_resumen_kpi .vt-cab-tit {
        font-size: 13px;
        font-weight: 600;
        line-height: 1.35;
        color: var(--accent-deep);
        white-space: nowrap;
    }
    .st-key-vt_resumen_kpi .vt-kpis {
        display: flex;
        flex-wrap: wrap;
        align-items: stretch;
        gap: 2px 0;
    }
    .st-key-vt_resumen_kpi .vt-kpi {
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-width: 0;
        max-width: 132px;
        padding: 0 12px;
        line-height: 1.2;
        border-left: 1px solid var(--border);
    }
    .st-key-vt_resumen_kpi .vt-kpi:first-child {
        padding-left: 0;
        border-left: none;
        max-width: none;
    }
    .st-key-vt_resumen_kpi .vt-kpi-rot {
        font-size: 10px;
        color: var(--text-secondary);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .st-key-vt_resumen_kpi .vt-kpi[style] .vt-kpi-rot::before {
        content: "";
        display: inline-block;
        width: 8px;
        height: 8px;
        margin-right: 4px;
        border-radius: 2px;
        background: var(--vt-kpi-color);
    }
    .st-key-vt_resumen_kpi .vt-kpi-val {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary);
        white-space: nowrap;
    }
    .st-key-vt_resumen_kpi .vt-kpi-sub {
        margin-left: 4px;
        font-size: 10px;
        font-weight: 400;
        color: var(--text-secondary);
    }
    .st-key-vt_resumen_kpi .vt-kpi-total .vt-kpi-val {
        color: var(--accent-deep);
        font-weight: 700;
    }
    .st-key-vt_resumen_kpi .vt-kpi-alerta .vt-kpi-val {
        color: var(--warning-text);
    }

    /* La zona de abajo de «Tendencia diaria de venta» (2026-09-24, regla
       #516): la de «Compras por período» (`cp_sem_*` en
       `graficos/compras/_css_proveedor.py`, que sólo se inyecta en
       Compras). Los dos toggles —granularidad arriba, modo abajo— a 32px y
       acotados a SU key; la fila de modo con su caption centrado y sin el
       `margin-bottom: -16px` de la regla #162; y las grillas en BLOQUE: el
       iframe de un componente nace inline y su contenedor le suma el hueco
       del descendente (7.6px medidos en Compras), que haría crecer la
       tarjeta al abrir la tabla. */
    .st-key-vt_resumen_gran [data-testid="stButtonGroup"] button,
    .st-key-vt_resumen_modo [data-testid="stButtonGroup"] button {
        min-height: 32px !important;
        height: 32px !important;
        padding: 0 12px !important;
        font-size: 12px !important;
    }
    /* LA FILA DE CONTROLES, A 32px (2026-09-24, a pedido: «adelgazar los
       cuadrantes de las listas desplegables de arriba … y subir así el
       título, el gráfico»). Medido antes: los cuatro multiselect en 42px y
       el trigger de la fecha en 52 (relleno 14px arriba y abajo), que era
       el que le daba el alto a la fila entera. Ahora los seis miden lo
       que el toggle de granularidad: 32. Regla #519.
       Acotado a CADA key (CLAUDE.md: una regla colgada del contenedor
       captura los widgets que vengan después). */
    .st-key-vt_resumen_grupo [data-baseweb="select"] > div,
    .st-key-vt_resumen_serv [data-baseweb="select"] > div,
    .st-key-vt_resumen_canal [data-baseweb="select"] > div,
    .st-key-vt_resumen_tdoc [data-baseweb="select"] > div {
        min-height: 28px !important;
        height: 28px !important;
        font-size: 12px !important;
    }
    .st-key-vt_resumen_grupo [data-baseweb="select"] > div > div,
    .st-key-vt_resumen_serv [data-baseweb="select"] > div > div,
    .st-key-vt_resumen_canal [data-baseweb="select"] > div > div,
    .st-key-vt_resumen_tdoc [data-baseweb="select"] > div > div {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        max-height: 26px !important;
        overflow: hidden !important;
    }
    /* Segunda pasada, el mismo día: «es muy grueso, hagámoslo más
       delgado». De 32 a 28, y el toggle de granularidad con ellos: seis
       controles en una fila tienen que medir lo mismo. */
    .st-key-vt_resumen_gran [data-testid="stButtonGroup"] button {
        min-height: 28px !important;
        height: 28px !important;
        padding: 0 12px !important;
        font-size: 12px !important;
    }
    .st-key-vt_resumen_escala button {
        min-height: 28px !important;
        height: 28px !important;
        padding: 0 14px !important;
        font-size: 12px !important;
    }
    .st-key-vt_resumen_sub [data-testid="stButtonGroup"] button {
        min-height: 32px !important;
        height: 32px !important;
        padding: 0 10px !important;
        font-size: 12px !important;
    }
    .st-key-vt_resumen_pie { align-items: center !important; }
    .st-key-vt_resumen_pie [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    .st-key-vt_resumen_resumen .stCustomComponentV1,
    .st-key-vt_resumen_detalle .stCustomComponentV1 {
        display: block !important;
    }
    [class*="st-key-vt_resumen_res_grid_"] iframe,
    [class*="st-key-vt_resumen_ped_grid_"] iframe,
    [class*="st-key-vt_resumen_lin_grid_"] iframe {
        width: 100% !important;
    }

    /* =================================================================== */
    /* Panel "Detalle" del comparativo de Ventas (graficos/ventas_comparativo)*/
    /*                                                                       */
    /* El propio switch ES el indicador de color de la serie: no hay swatch  */
    /* de HTML aparte (antes eran dos cosas — un <span> pintado y un         */
    /* checkbox al lado — y el usuario pidió una sola pieza).                */
    /* 2026-08-13: pasó de checkbox cuadrado a `st.toggle` (referencia: el   */
    /* panel "Comparar con" de un gráfico de índices, switch en vez de       */
    /* tilde) — sigue siendo UN solo widget, no se sumó un botón "quitar"    */
    /* aparte a propósito, por la misma razón de la línea de arriba.         */
    /*                                                                       */
    /* TRAMPA verificada en el DOM real (no en la documentación): `st.toggle`*/
    /* emite el MISMO data-testid="stCheckbox" que `st.checkbox` — Streamlit */
    /* no tiene un testid "stToggle" propio. Lo único que cambia es          */
    /* <input role="switch"> y la estructura interna: track + thumb          */
    /* anidados en vez de un cuadrado único con SVG de tilde. Por eso estos  */
    /* selectores no necesitaron cambiar de testid, sólo de forma.           */
    /*                                                                       */
    /* La caja visual (el "track") es el ÚNICO <div> hijo del <label> que    */
    /* NO tiene data-testid (el otro es stWidgetLabel); el "thumb" es su     */
    /* único <div> hijo. Se ancla por estructura y no por la clase emotion,  */
    /* que lleva hash y cambia de versión a versión. Streamlit posiciona su  */
    /* thumb con un transform propio (esa clase con hash); lo anulamos y     */
    /* reposicionamos con justify-content en el track, que no depende de     */
    /* esa clase ni de calcular un translateX en píxeles.                    */
    /*                                                                       */
    /* El color entra por --sw-color, que fija el container de cada fila.    */
    /* Venta tiene DOS variantes porque su color sigue el signo del %Δ       */
    /* (igual que la barra del gráfico): _pos verde, _neg rojo.              */
    /* =================================================================== */
    div[class*="st-key-ventas_comp_sw_venta_pos"] { --sw-color: var(--success); }
    div[class*="st-key-ventas_comp_sw_venta_neg"] { --sw-color: var(--danger); }
    div[class*="st-key-ventas_comp_sw_pax"]       { --sw-color: var(--serie-pax); }
    div[class*="st-key-ventas_comp_sw_ticket"]    { --sw-color: var(--serie-ticket); }

    /* Track: pill de 20×11. Apagado = sólo contorno (mismo look que el
       checkbox de antes, con esquinas redondeadas); prendido = relleno
       sólido del color de la serie. Misma lectura que un legend: color
       sólido = se ve. */
    div[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"]
        label > div:not([data-testid]) {
        width: 20px !important;
        height: 11px !important;
        min-width: 20px !important;
        border-radius: 9999px !important;
        border: 1.5px solid var(--sw-color) !important;
        background-color: transparent !important;
        box-shadow: none !important;
        /* Streamlit le pone `margin-top: 2.5px` al track (pensado para
           alinearlo con un label de texto al lado, que acá va
           `collapsed`). Sin anularlo el switch queda pegado al fondo de
           su caja — 1.25px bajo el centro — y desalineado contra el
           texto de su fila. El centrado real lo hace el
           `align-items:center` del label. */
        margin: 0 !important;
        padding: 0 1.5px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        transition: background-color 0.15s ease !important;
    }
    /* Prendido. `data-on` lo pone `ventas_comparativo.py::_JS_ESPEJO_SWITCH`
       — hasta el 2026-09-18 esto era `label:has(input:checked)`, y una
       pseudo-clase adentro de un `:has()` recalcula la página entera en
       cada inserción, en todos los reportes (regla #469). */
    div[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"]
        label[data-on] > div:not([data-testid]) {
        background-color: var(--sw-color) !important;
        justify-content: flex-end !important;
    }
    /* Thumb: punto de 7px. Apagado = color de la serie (se lee el color aun
       con la serie oculta); prendido = blanco sobre el track ya relleno —
       mismo contraste que el pulgar de un switch nativo. --bg-secondary es
       el blanco de la paleta (tema.py / _00_base.py), no un #hex suelto. */
    div[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"]
        label > div:not([data-testid]) > div {
        width: 7px !important;
        height: 7px !important;
        border-radius: 9999px !important;
        background-color: var(--sw-color) !important;
        transform: none !important;
        transition: none !important;
    }
    div[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"]
        label[data-on] > div:not([data-testid]) > div {
        background-color: var(--bg-secondary) !important;
    }
    /* El alto mínimo de 24px del checkbox es lo que estiraba cada fila:
       con el switch de 11px sobra la mitad. */
    div[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"] {
        min-height: 0 !important;
    }
    div[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"] label {
        min-height: 0 !important;
        align-items: center !important;
    }

    /* =================================================================== */
    /* Panel "Detalle" — tarjeta FLOTANTE sobre el gráfico (2026-08-14)      */
    /*                                                                       */
    /* 1ra vuelta (el mismo día): st.popover. Se descartó — un popover      */
    /* SIEMPRE se ve como DOS piezas: un botón-cápsula y, con un hueco,     */
    /* un panel aparte (`stPopoverBody` es un portal con su propio offset  */
    /* y sombra). Reportado con captura: "como un toggle del cual sale     */
    /* otro toggle". La referencia es UNA sola tarjeta sin costura          */
    /* (título y filas en el mismo rectángulo).                             */
    /*                                                                       */
    /* 2da vuelta (esta): patrón manual. TODO —el botón-título con el       */
    /* chevron Y las filas— vive dentro del MISMO                           */
    /* `st.container(key="ventas_comp_detalle_float")`, que es              */
    /* `position:absolute` sobre `_slot_graf` (ancla `position:relative`,   */
    /* key `ventas_comp_chart_slot_<grano>` para no depender de cuánto      */
    /* mida la franja de controles de arriba) TANTO abierto como cerrado.   */
    /* Al no cambiar de posición ni salir del flujo normal en ningún        */
    /* estado, expandirlo (Python agrega las 3 filas adentro del MISMO      */
    /* contenedor) no mueve nada a su alrededor — mismo resultado que el    */
    /* portal del popover, pero sin la costura de dos piezas separadas.     */
    /* =================================================================== */
    div[class*="st-key-ventas_comp_chart_slot_"] { position: relative; }
    div[class*="st-key-ventas_comp_chart_slot_"] .st-key-ventas_comp_detalle_float {
        position: absolute;
        top: 6px; left: 8px; z-index: 5;
        /* Ancho FIJO, no `auto` — cerrado medía 138px (se encogía al
           texto) y abierto 280px: el ancho saltaba en cada clic. En la
           referencia la barra colapsada es igual de ancha que el panel
           abierto; sólo crece HACIA ABAJO. De paso arregla el "se ve
           regordete, como un gusano": una cápsula corta y gruesa pasa a
           ser una barra larga y fina, que es la proporción del ejemplo. */
        width: 280px !important;
        overflow: hidden;
        /* Simétrico (2px arriba Y abajo) — reportado "se ve descuadrado"
           con el panel cerrado: era `2px 0 5px` (5 abajo, no 2), y sumado
           al padding propio del botón (3px 10px, parejo) el texto
           quedaba con 6px arriba pero 9px abajo — 3px de más SÓLO abajo,
           notorio en una tarjeta de una sola línea. El aire extra que
           necesitan las filas cuando está ABIERTO ahora es
           padding-bottom del panel (`ventas_comp_detalle_panel` más
           abajo), no de acá, para no desequilibrar el estado cerrado
           (el más visto: por defecto arranca cerrado). 1px y no 2:
           reportado "muy grueso" — cada px de acá se suma DOS veces al
           alto de una tarjeta que cerrada es una sola línea. */
        padding: 1px 0;
        /* El default de Streamlit para un stVerticalBlock es
           gap:16px — invisible con un solo hijo (cerrado), pero al
           abrirse (botón + panel de filas, dos hijos) metía un salto de
           16px entre el título y la primera fila. 0: las filas quedan
           pegadas al título, y el padding-top del panel de abajo pone
           el aire que corresponde. */
        gap: 0 !important;
        /* Gris translúcido — 2da vuelta (2026-08-14): la 1ra usaba
           --bg-primary (#faf9fb, "lienzo general") al 92%, y el usuario
           reportó "no lo veo que tenga nada de transparencia" incluso
           DESPUÉS del fallback rgba. Es el MISMO bug que ya está
           documentado en _40_ajuste_franja.py: un tinte casi-blanco al
           92% sobre una tarjeta que YA es casi blanca (--bg-card) es
           indistinguible del blanco opaco — no hay suficiente contraste
           para que el ojo note la transparencia, más allá de que la
           declaración esté aplicándose bien. La franja resolvió esto
           cambiando de tinte (blanco → --accent-tint), pero acá el
           pedido explícito era GRIS, no lavanda — así que en vez de
           cambiar de color se usa uno con más cuerpo: --text-secondary
           (#71717a, gris medio) a SÓLO 8%, no 92%. Con eso el efecto
           esmerilado (blur) sí se nota, y el tono se lee gris de
           verdad, no blanco con un nombre de variable gris.
           Bajó en dos pedidos seguidos del usuario: 16% → 12% (8va
           vuelta) → 8% (9na). El blur se mantiene en 14px en las dos:
           es lo que sostiene la legibilidad del texto cuando el tinte
           se aclara, así que bajar tinte y blur juntos sería restar dos
           veces lo mismo, y además se cambia UNA variable por vuelta
           para saber cuál movió la aguja.
           OJO si se sigue bajando: el límite ya no es estético sino
           FUNCIONAL — este panel muestra cifras (S/ 7,143, −52%) sobre
           barras de colores fuertes, y a partir de acá lo que se pierde
           es la lectura de los números, no "el efecto". Si hace falta
           más transparencia, el próximo movimiento es SUBIR el blur
           (14px → 18px) para compensar, no seguir restando tinte solo.
           Fallback plano ANTES del color-mix(): si el navegador no
           soporta esa función la declaración es inválida y SE IGNORA
           ENTERA — sin nada previo válido el fondo cae al blanco opaco
           default de Streamlit. rgba(113,113,122,...) es el mismo
           --text-secondary (#71717a) escrito a mano: CSS no permite
           sacarle los canales R/G/B a una var() sin relative color
           syntax (aún menos soportada que color-mix()) — si
           --text-secondary cambia, actualizar también este rgba().
           border-radius 10px, NO 999px (cápsula): la referencia es una
           tarjeta de esquinas suaves, no un chip. */
        background: rgba(113, 113, 122, 0.08) !important;
        background: color-mix(in srgb, var(--text-secondary) 8%, transparent) !important;
        /* SIN blur (11na vuelta) — y acá está la causa real de las
           cuatro rondas de "no se ve más transparente".
           El fondo ya era 92% transparente (tinte al 8%), pero
           `backdrop-filter: blur(14px)` desenfoca lo que hay detrás con
           un radio MAYOR que el tamaño del propio contenido: la
           anotación "feriado" mide ~10px de alto, así que 14px de blur
           la convierte en una mancha uniforme. El tinte nunca fue el
           problema; el blur borraba el fondo por completo, y por eso
           bajarlo de 16% a 12% a 8% no cambió nada visible.
           Medido con el panel ABIERTO: dentro de su rectángulo caen el
           texto "feriado" (x=76,y=49), el "50%" del eje (x=14,y=70) y 2
           bandas de `shapelayer`. O sea que SÍ hay contenido detrás —
           lo que invalida la nota de la vuelta anterior, que decía "no
           hay nada que transparentar" mirando sólo el estado CERRADO
           (ahí es cierto: la barra de 26px no llega al área de datos).
           Queda `saturate` solo: da el matiz de vidrio sin tocar la
           nitidez de lo que pasa por detrás. */
        backdrop-filter: saturate(1.15) !important;
        -webkit-backdrop-filter: saturate(1.15) !important;
        /* Borde y sombra apenas insinuados (10na vuelta): un borde de
           1px SÓLIDO y una sombra media dibujan una tarjeta APOYADA;
           con el borde casi transparente y la sombra difusa se lee como
           una lámina flotando, que es el efecto buscado.
           OJO — la 10na vuelta además diagnosticó "detrás del panel no
           hay nada que transparentar" y eso es FALSO en general: se
           midió con el panel CERRADO, y ahí sí es cierto (la barra de
           26px no baja hasta el área de datos, sólo pisa el margen
           superior de la figura, que es transparente sobre tarjeta
           blanca). Abierto mide 75px y sí alcanza contenido real —ver
           la nota del `backdrop-filter` más arriba—, así que la
           conclusión de aquella vuelta no se puede generalizar.
           Lección: medir el estado que el usuario está mirando, no el
           que quedó abierto en el navegador. */
        border: 1px solid rgba(113, 113, 122, 0.12) !important;
        border: 1px solid color-mix(in srgb, var(--text-secondary) 12%, transparent) !important;
        /* 6px, no 10: con una tarjeta CERRADA de ~26px de alto, 10px de
           radio la redondea casi a cápsula ("como un gusano"). 6px la
           deja como barra de esquinas suaves, igual que la referencia,
           y sigue leyéndose bien abierta (que es más alta). */
        border-radius: 6px !important;
        box-shadow: 0 2px 10px rgba(16, 16, 20, 0.05) !important;
    }
    .st-key-ventas_comp_detalle_float [data-testid="stElementToolbar"] {
        display: none;
    }
    /* El botón-título: se ve como TEXTO clickeable dentro de la tarjeta,
       no como un botón aparte propio — sin fondo, sin borde, sin sombra
       (hereda el vidrio del contenedor). El chevron es la única señal de
       que se puede abrir/cerrar, igual que la referencia; lo manda
       Python vía `icon=` (keyboard_arrow_down/_up según
       `ventas_comp_detalle_abierto`), no CSS. */
    .st-key-ventas_comp_detalle_float [data-testid="stButton"] button {
        width: 100% !important;
        min-width: 0 !important;
        min-height: 0 !important;
        height: auto !important;
        /* `flex` (block-level), NO el inline-flex que trae Streamlit.
           ESTE era el "la letra parece no estar centrada": un hijo
           inline-block deja el hueco de descendente (baseline gap) de
           la línea DEBAJO suyo — medido, 3px arriba contra 4.5px abajo,
           así que el texto se veía corrido hacia arriba dentro de la
           barra. En block-level no hay línea que lo genere. Es el mismo
           1.5px que en la vuelta anterior atribuí a un margen sin
           identificar y dejé pasar: no era margen, era el baseline. */
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        /* 1.35 en vez del 1.6 heredado: el alto de la barra cerrada es
           casi todo la caja de línea del texto (12px × 1.6 = 19.2px),
           así que bajar el interlineado es lo que MÁS adelgaza sin
           tocar el tamaño de letra. */
        line-height: 1.35 !important;
        gap: 4px !important;
        padding: 3px 10px !important;
        margin: 0 !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        color: var(--text-primary) !important;
    }
    .st-key-ventas_comp_detalle_float [data-testid="stButton"] button:hover {
        background: color-mix(in srgb, var(--text-primary) 5%, transparent) !important;
        color: var(--accent-deep) !important;
    }
    .st-key-ventas_comp_detalle_float [data-testid="stButton"] button p {
        font-size: 12px !important;
        font-weight: 600 !important;
        margin: 0 !important;
    }
    /* Chevron: reportado "casi imperceptible". Eran DOS cosas juntas —
       13px (más chico que el propio texto de 12px sólo por 1px, o sea
       sin jerarquía visual) y pintado en --accent, un violeta que sobre
       el vidrio gris translúcido pierde contraste. Ahora 17px y del
       mismo negro del texto (--text-primary), que es como se ve en la
       referencia: el chevron es la señal de "esto se abre", tiene que
       leerse antes que el label, no después. `wght` sube el grosor del
       trazo — Material Symbols es una fuente VARIABLE, así que el eje
       existe; si Streamlit cambiara a la versión estática, esta línea
       se ignora sola y quedan el tamaño y el color, que ya alcanzan. */
    .st-key-ventas_comp_detalle_float [data-testid="stButton"]
        [data-testid="stIconMaterial"] {
        font-size: 17px !important;
        color: var(--text-primary) !important;
        font-variation-settings: 'wght' 600 !important;
    }
    /* Filas: mismo ancho angosto que antes (`width=260` en Python, ver
       ventas_comparativo.py — heredaba 400 del expander viejo, que
       flotando salía casi la mitad de la tarjeta del gráfico). Sin fondo
       propio: ya lo pone el contenedor; sólo el padding horizontal para
       alinear con el botón-título de arriba.
       top:4px / bottom:6px: con `gap:0` en el contenedor (arriba, misma
       hoja) el panel queda pegado AL BOTÓN sin nada de aire — el 4px de
       acá es toda la separación título↔filas que queda. El 6px de abajo
       replica el mismo total (~6px) que el estado cerrado tiene entre
       el texto y el borde inferior de la tarjeta, para que abierta y
       cerrada respiren igual, no que abrirla la deje más apretada. */
    .st-key-ventas_comp_detalle_float .st-key-ventas_comp_detalle_panel {
        padding: 4px 10px 6px !important;
    }
    /* Switch y textos de una misma fila, en la MISMA línea óptica.
       Reportado "las filas de detalle y el switch se ven no alineados
       entre sí"; medido: el track quedaba 6.75px POR ENCIMA del centro
       del texto, idéntico en las tres filas (sistemático, no una fila
       rara). Dos causas SUMADAS, ninguna evidente sin medir la cadena
       de padres entera — la primera hipótesis (que el texto heredaba
       `line-height: 1.6` y su caja de 20.8px desbordaba la fila de
       13.5px) era cierta PERO no era la causa: al bajarlo a 1 la caja
       pasó a 13px y el delta siguió clavado en -6.75.

       1. `stMarkdownContainer` trae `margin-bottom: -16px` de
          Streamlit — un negativo del tamaño de su propia línea, con lo
          que la COLUMNA ENTERA del texto colapsa a `height: 0`
          (verificado: stColumn/stVerticalBlock/stElementContainer/
          stMarkdown todos en 0). Una caja de alto 0 centrada por
          `align-items:center` queda clavada en el centro de la fila, y
          el texto se pinta DESDE ahí hacia abajo — de ahí que el texto
          apareciera medio renglón más abajo que el switch. Ponerlo en 0
          le devuelve su altura real y el centrado empieza a funcionar.
       2. El track del switch tiene `margin-top: 2.5px` propio (queda
          pegado al fondo de su caja de 13.5px, o sea 1.25px bajo el
          centro). Con la caja del texto ya sana, ese 1.25px era el
          residuo que quedaba.
       `line-height: 1` se queda igual: no era la causa, pero sin él la
       caja del texto mide 20.8px contra 13.5 de la fila y el panel
       crece de gusto. */
    .st-key-ventas_comp_detalle_panel [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    .st-key-ventas_comp_detalle_panel [data-testid="stMarkdownContainer"],
    .st-key-ventas_comp_detalle_panel [data-testid="stMarkdownContainer"] div {
        line-height: 1 !important;
    }
    .st-key-ventas_comp_detalle_panel [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    /* Móvil: el plot es angosto y una tarjeta absoluta sobre la esquina
       tapa barras, así que >640px flota y <=640px fluye.
       (Acá se citaba a `prov_pop_float`/`gran_float` de
       `graficos/compras/_css_proveedor.py` como el mismo criterio; los dos
       DEJARON de flotar —`gran_float` el 2026-08-23, `prov_pop_float` el
       2026-09-01, que entró en la fila del título del Ranking— así que la
       cita apuntaba a dos elementos que ya no hacen esto. Este de acá es
       hoy el único caso vivo del patrón.)
       Expandirla sigue sin empujar nada (sigue siendo el mismo
       contenedor, sólo que ahora en flujo); nada más cambia. */
    @media (max-width: 640px) {
        div[class*="st-key-ventas_comp_chart_slot_"] .st-key-ventas_comp_detalle_float {
            position: static !important;
            width: 100% !important;
            max-width: none !important;
            margin: 0 0 6px !important;
        }
    }

    /* =================================================================== */
    /* Toggle "Venta/Costo/Pax/Pax·Venta" de Ventas › Por día — de cápsula   */
    /* a tab de texto con subrayado, pedido explícito (referencia: pestañas */
    /* de un extracto financiero, texto plano + línea de color abajo del    */
    /* activo, sin fondo relleno). `data-variant="pills"` + `aria-pressed`  */
    /* son atributos reales de Streamlit (no clases con hash), así que el   */
    /* selector no se rompe con la próxima versión que cambie los hashes.   */
    /* =================================================================== */
    /* Sube SÓLO el toggle, no la tarjeta. El ancla es la key del PROPIO
       widget: `st.pills(key="ventas_dia_metricas")` emite esa clase en su
       element container, así que no hace falta (ni conviene) envolverlo en
       un st.container extra — ver arquitectura.md regla #90.

       Este margen come el gap del bloque vertical de Streamlit entre la
       CABECERA de la franja (título + línea superior, en graficos/ventas.py)
       y los tabs. Es el aire que queda entre la línea de arriba y el texto
       de los tabs: si se toca, medir en el navegador — el <hr> de abajo y
       el padding de la cabecera están calculados contra este número. */
    div[class*="st-key-ventas_dia_metricas"] {
        margin-top: 6px !important;
    }
    /* El gap real no va en stButtonGroup: ese es display:block (verificado
       en el navegador, no a ojo). El flex de verdad es su hijo directo, un
       <div> sin testid propio — de ahí el "> div". */
    div[class*="st-key-ventas_dia_metricas"] [data-testid="stButtonGroup"] > div {
        gap: 28px !important;
    }
    div[class*="st-key-ventas_dia_metricas"] [data-testid="stButtonGroup"]
        button[data-variant="pills"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        padding: 4px 1px !important;
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
        font-size: 17px !important;
    }
    div[class*="st-key-ventas_dia_metricas"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][aria-pressed="true"] {
        border-bottom-color: var(--accent) !important;
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
    }
    div[class*="st-key-ventas_dia_metricas"] [data-testid="stButtonGroup"]
        button[data-variant="pills"]:hover {
        color: var(--accent) !important;
    }

    /* Reserva de alto de la tarjeta de Año Pasado, para que NO colapse
       mientras se cargan los datos. El gráfico se dibuja al final del script
       (después de traer las dos series de R2), así que entre el render de la
       franja y su llegada la tarjeta se quedaba con 90px de alto y volvía a
       subir después — mitad del "sube y baja" que se ve en cada clic (ver
       regla #108).
       El número sale de las piezas reales: 32 de padding + 52 de franja de
       controles + 340 de figura = 424. Es min-height, no height: el caption
       y el panel "Detalle" pueden hacerla más alta sin problema.
       2026-08-15: el término "42 de cabecera" que este número traía se sacó
       — el título se mudó a la franja superior (fuera de la tarjeta, ver
       ventas_comp_titulo_franja en estilos/_50_fecha.py), así que la
       tarjeta ya no reserva alto para él.
       Sólo desktop — en móvil la figura mide 260 y el patrón es scroll de
       página, mismo criterio que el resto del encuadre. */
    @media screen and (min-width: 769px) {
        div[class*="st-key-chartcard_ventas_comparativo"] {
            min-height: 424px;
        }
    }

    /* `ventas_comp_titulo_franja` (el título que se mudó a la franja
       superior, ver estilos/_50_fecha.py) se dibuja como HERMANO, justo
       antes de esta tarjeta — y aunque es position:fixed y colapsa a 0px
       de alto, su wrapper de Streamlit sigue contando como flex item del
       bloque vertical que los contiene: el `gap:16px` de ese flex se
       aplica IGUAL entre "un item de 0px" y el siguiente, así que la
       tarjeta quedaba 16px más abajo de lo que estaba antes de que el
       título tuviera un hermano invisible.
       2026-08-15, 2da pasada (inspector: "esto debe subir" + "así como
       los controles arriba"): -16px solo cancelaba el gap del flex. El
       padre real, `ajuste_graf_card_izq_ventas`, es OTRA tarjeta —
       redondeada, con su propio padding-top:8px (estilos/_80_cards.py,
       regla de familia `st-key-ajuste_graf_card_*` — el inspector avisa
       que es wildcard, así que NO se toca esa: movería las tarjetas de
       los otros 7 reportes). Esos 8px se suman al gap ya cancelado:
       -16 - 8 = -24px, medido en vivo hasta que el borde de esta tarjeta
       quedó pegado al de su padre (que a su vez ya está pegado a la
       franja por el -48px de _20_compras_rail.py). Con eso suben juntos
       la tarjeta Y los controles de adentro (Día/Semana/Mes, Ventana,
       Vista) — son el mismo elemento, no hace falta una regla aparte. */
    div[class*="st-key-chartcard_ventas_comparativo"] {
        margin-top: -24px !important;
    }

    /* =================================================================== */
    /* FRANJA DE CONTROLES DE VENTAS › AÑO PASADO                            */
    /*                                                                       */
    /* Cuatro grupos independientes (no tabs de la misma cosa) en una fila.  */
    /* Mismo look de tab que Por día, y separadores verticales entre los     */
    /* tres de la izquierda. Ver arquitectura.md regla #107.                 */
    /* =================================================================== */
    div[class*="st-key-ventas_comp_grano"] [data-testid="stButtonGroup"]
        button[data-variant="pills"],
    div[class*="st-key-ventas_comp_ventana_"] [data-testid="stButtonGroup"]
        button[data-variant="pills"],
    div[class*="st-key-ventas_comp_modo"] [data-testid="stButtonGroup"]
        button[data-variant="pills"],
    div[class*="st-key-ventas_comp_vista"] [data-testid="stButtonGroup"]
        button[data-variant="pills"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        padding: 3px 1px !important;
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
        /* 15px y no los 17px de Por día: son CUATRO grupos en una fila y a
           17px envuelven a dos líneas en un laptop de 1366. Medido. */
        font-size: 15px !important;
    }
    /* [data-selected="true"], NO [aria-pressed="true"]: los cuatro pills de
       esta franja son single-select (sin `selection_mode=` en el .py, que
       por defecto es "single"). Streamlit marca single-select con
       `role="radio"` + `aria-checked` + `data-selected`; `aria-pressed` es
       el marcado de MULTI-select (así rinde "Métricas" en Por día, de donde
       se copió esta regla). Con el selector viejo el CSS nunca matcheaba:
       verificado con outerHTML en el navegador — el botón activo ("Día",
       default) no tenía `aria-pressed` en ningún valor, así que el estado
       "activo" (negrita + color + subrayado) jamás se pintó, desde el
       primer commit de esta franja. */
    div[class*="st-key-ventas_comp_grano"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"],
    div[class*="st-key-ventas_comp_ventana_"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"],
    div[class*="st-key-ventas_comp_modo"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"],
    div[class*="st-key-ventas_comp_vista"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"] {
        border-bottom-color: var(--accent) !important;
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
    }
    /* El gap real no va en stButtonGroup (es display:block): va en su hijo
       directo, un <div> sin testid propio — mismo hallazgo que en Por día. */
    div[class*="st-key-ventas_comp_grano"] [data-testid="stButtonGroup"] > div,
    div[class*="st-key-ventas_comp_ventana_"] [data-testid="stButtonGroup"] > div,
    div[class*="st-key-ventas_comp_modo"] [data-testid="stButtonGroup"] > div,
    div[class*="st-key-ventas_comp_vista"] [data-testid="stButtonGroup"] > div {
        gap: 18px !important;
    }
    /* "Vista" NUNCA apila verticalmente. Medido: el contenedor se
       shrink-wrappea a su contenido (165px = "Montos" + gap + "Descomposición"
       exactos, SIN margen) — si la columna que lo aloja mide un pixel menos
       (ventana más angosta, u otro navegador con métricas de fuente
       distintas), el ajuste al pixel se rompe y las dos opciones caen en
       líneas separadas: la franja pasa de 52px a ~100px. Con `nowrap`, en
       vez de apilar, sale de la columna hacia la derecha — controlado
       porque "Vista" ya es el grupo más a la derecha de la franja. */
    div[class*="st-key-ventas_comp_vista"] [data-testid="stButtonGroup"] > div {
        flex-wrap: nowrap !important;
    }
    div[class*="st-key-ventas_comp_vista"] [data-testid="stButtonGroup"]
        button[data-variant="pills"] {
        white-space: nowrap !important;
    }
    /* SEPARADORES. Cada grupo dibuja el suyo a su IZQUIERDA, nunca una regla
       por posición: "alinear por" sólo existe en granularidad Día, así que
       con una regla posicional quedaría una hairline suelta anunciando un
       grupo que no está. Colgado de la key, el separador se va con su grupo.
       El primero (grano) no lleva, y "vista" tampoco: es el otro eje y se
       separa con espacio, no con línea — una línea diría "otro grupo de lo
       mismo", y no lo es. */
    /* Aire entre la línea SUPERIOR y los controles. Sin esto los tabs
       arrancan pegados a la línea (medido: 0px) — el bloque de columnas cae
       exactamente donde termina el border-bottom de la cabecera. Va acoplado
       al margin-top del <hr> en ventas_comparativo.py: 6 arriba / 10 abajo. */
    div[class*="st-key-ventas_comp_grano"],
    div[class*="st-key-ventas_comp_ventana_"],
    div[class*="st-key-ventas_comp_modo"],
    div[class*="st-key-ventas_comp_vista"] {
        margin-top: 6px !important;
    }
    /* "Vista" va a la DERECHA de la franja (es el otro eje). NO se intenta
       con `justify-content: flex-end`: probado en el navegador, el div flex
       interno del stButtonGroup se queda en su ancho de contenido (165px)
       aunque se le fuerce `width: 100% !important` en los tres niveles de la
       cadena — element container, stButtonGroup y el propio div. Lo empuja
       una columna espaciadora vacía en ventas_comparativo.py. */
    div[class*="st-key-ventas_comp_ventana_"],
    div[class*="st-key-ventas_comp_modo"] {
        position: relative;
        padding-left: 17px !important;
    }
    div[class*="st-key-ventas_comp_ventana_"]::before,
    div[class*="st-key-ventas_comp_modo"]::before {
        content: "";
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 1px;
        height: 18px;
        background: var(--border);
    }

    /* =================================================================== */
    /* ALTO ELÁSTICO — el CSS es el dueño del alto de esta figura            */
    /*                                                                       */
    /* Va con `alturas.ELASTICO` en graficos/ventas.py: la figura sale SIN    */
    /* `fig.layout.height` y Plotly toma el alto de este contenedor al        */
    /* MONTAR. Antes el alto era una constante de Python (373px) calibrada    */
    /* para el laptop de 1366x768: correcta ahí y desperdiciando 343px en un  */
    /* monitor de 1920x1080. Ver arquitectura.md regla #106.                  */
    /*                                                                       */
    /* El ancla es `:has()` sobre la key del PROPIO gráfico, no la key de la  */
    /* tarjeta: `ajuste_graf_card_izq_ventas` la comparten TODAS las vistas   */
    /* de Ventas, y darle alto fijo estiraría también el Resumen ejecutivo    */
    /* (1364px, largo a propósito). Así sólo se estira la tarjeta que de      */
    /* verdad contiene este gráfico.                                         */
    /* =================================================================== */
    /* TODO el bloque elástico va dentro del mismo @media que el encuadre de
       arriba. En móvil el cromo es otro y el patrón correcto es el scroll de
       página: fijarle el alto a la tarjeta ahí rompería justamente eso.
       Consecuencia conocida en móvil: sin alto de CSS ni de Python, Plotly
       cae a su default de 450px, que con scroll de página es aceptable. */
    @media screen and (min-width: 769px) {
    div[class*="st-key-ajuste_graf_card_"]:has(.st-key-ventas_g_dia) {
        /* flex: 0 0 auto es OBLIGATORIO: los bloques de Streamlit son flex
           items con `flex: 1 1 0%` y ahí `height` se ignora en silencio
           (regla #101). Sin esto, la regla de abajo no hace nada. */
        flex: 0 0 auto !important;
        height: var(--alto-util) !important;
    }
    /* La cadena hasta el gráfico: si un solo nivel queda en `auto`, el
       `height: 100%` de abajo se resuelve contra un padre sin alto y Plotly
       cae a su default de 450px. Los dos niveles son reales, medidos en el
       navegador: la tarjeta envuelve un stLayoutWrapper y ese un
       stVerticalBlock. */
    div[class*="st-key-ajuste_graf_card_"]:has(.st-key-ventas_g_dia)
        > [data-testid="stLayoutWrapper"],
    div[class*="st-key-ajuste_graf_card_"]:has(.st-key-ventas_g_dia)
        > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {
        height: 100% !important;
    }
    /* El gráfico se come lo que sobra después de la franja de controles.
       Streamlit le pone `flex: 0 0 <alto>px` derivado del alto de Plotly;
       hay que reemplazarlo. `min-height: 0` es imprescindible: sin él, el
       min-height:auto de un flex item impide que se ENCOJA por debajo de su
       contenido y la tarjeta desborda en pantallas chicas.
       OJO: acotado a la key del gráfico, NUNCA a los hijos del contenedor.
       Con `> div` el flex reparte el alto entre los TRES hijos por igual
       (título, tabs y gráfico) — medido en el banco: 214.7px cada uno. */
    div[class*="st-key-ventas_g_dia"] {
        flex: 1 1 auto !important;
        min-height: 0 !important;
    }
    div[class*="st-key-ventas_g_dia"] [data-testid="stFullScreenFrame"],
    div[class*="st-key-ventas_g_dia"] [data-testid="stPlotlyChart"],
    div[class*="st-key-ventas_g_dia"] .js-plotly-plot {
        height: 100% !important;
    }
    }

    /* Botón "Cerrar" del drill de Platos (Ventas › Año Pasado): ícono solo,
       sin relleno — a pedido, el botón secundario ancho (127×40,
       use_container_width) "es muy grande para desktop" y comparte fila
       con el título "Platos · …" (ver graficos/ventas_comparativo.py).
       `vertical_alignment="center"` de st.columns no alcanzó (medido:
       align-items quedaba en "stretch", no en "center"), así que se fuerza
       acá. Con eso puesto TODAVÍA quedaban 8px de diferencia entre los
       centros de título y botón (medido con getBoundingClientRect: el
       `help=` del botón agrega algo invisible a su columna que corre su
       centro de alineación) — el margin-top de abajo es ese resto, medido
       en vivo hasta que los dos centros coincidieron, no a ojo. */
    [data-testid="stHorizontalBlock"]:has(.st-key-ventas_comp_cerrar) {
        align-items: center !important;
    }
    .st-key-ventas_comp_cerrar button {
        min-width: 0 !important;
        width: auto !important;
        height: auto !important;
        min-height: 0 !important;
        padding: 4px !important;
        margin-top: 12px !important;
        border: none !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
    }
    .st-key-ventas_comp_cerrar button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }

    /* =================================================================== */
    /* FRANJA DE CONTROLES DE VENTAS › POR HORA                             */
    /*                                                                       */
    /* Igual que Familia y Año Pasado —tabs de texto con subrayado— con una  */
    /* diferencia que pidió el usuario el 2026-08-14 mirando la barra de     */
    /* TradingView: acá el TÍTULO comparte la fila con los controles en vez  */
    /* de llevarse una propia. A su derecha sobraban ~600px vacíos, y las    */
    /* otras vistas gastan ahí una fila entera más su hairline.              */
    /*                                                                       */
    /* [data-selected="true"] y NO [aria-pressed="true"]: los dos pills son  */
    /* single-select, y Streamlit los marca con role="radio" +               */
    /* data-selected (aria-pressed es el marcado del MULTI-select). Es la    */
    /* trampa que dejó muerto el selector de Año Pasado desde su primer      */
    /* commit — ver arquitectura.md #107.                                    */
    /* =================================================================== */
    .vh-titulo {
        margin: 0 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        line-height: 1.3 !important;
        color: var(--text) !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    /* El período (·  Ago 26) cuando hay UN solo panel: mismo renglón, menos
       peso. Es un dato, no un rótulo — y en 13px cabe en la misma columna. */
    .vh-titulo span {
        font-size: 13px !important;
        font-weight: 400 !important;
        color: var(--text-secondary) !important;
    }
    /* Gap de 8px (default 16) SÓLO en la franja de esta tarjeta: con el
       período en el título, los cuatro grupos piden 859px sobre 825
       disponibles. Los 24px de los tres huecos son la diferencia. */
    div[class*="st-key-chartcard_ventas_horario_"]
        [data-testid="stHorizontalBlock"] {
        gap: 8px !important;
    }
    div[class*="st-key-vh_grano"] [data-testid="stButtonGroup"]
        button[data-variant="pills"],
    div[class*="st-key-vh_medida_mapa"] [data-testid="stButtonGroup"]
        button[data-variant="pills"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        /* La caja se ajusta al TEXTO: los pills de Streamlit traen
           `min-height: 32px` y con texto de 14px eso deja ~9px de aire entre
           la palabra y el subrayado, que se lee como una línea suelta. Con
           `min-height: 0` + padding chico, la línea queda a 3px de la base
           de la letra — que es donde la ponen TradingView y cualquier tab
           bien hecha. */
        min-height: 0 !important;
        height: auto !important;
        padding: 1px 1px 1px !important;
        /* line-height 1.2 y no el 1.6 que hereda: con 14px, el 1.6 deja la
           caja del TEXTO en 22px mientras las letras miden ~10, o sea ~6px
           de aire DENTRO del renglón que ningún padding puede quitar. Lo
           cazó el inspector, en su sección de conflictos. */
        line-height: 1.2 !important;
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
        font-size: 14px !important;
    }
    div[class*="st-key-vh_grano"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"],
    div[class*="st-key-vh_medida_mapa"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"] {
        border-bottom-color: var(--accent) !important;
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
    }
    /* El gap real va en el hijo directo de stButtonGroup (que es
       display:block), no en él — mismo hallazgo que en Ventas › Por día. */
    div[class*="st-key-vh_grano"] [data-testid="stButtonGroup"] > div,
    div[class*="st-key-vh_medida_mapa"] [data-testid="stButtonGroup"] > div {
        gap: 16px !important;
        flex-wrap: nowrap !important;
    }
    /* Separador colgado de cada grupo a su IZQUIERDA, no por posición: el
       título es el primero y no lleva. */
    div[class*="st-key-vh_grano"],
    div[class*="st-key-vh_medida_mapa"] {
        position: relative;
        padding-left: 16px !important;
    }
    div[class*="st-key-vh_grano"]::before,
    div[class*="st-key-vh_medida_mapa"]::before,
    div[class*="st-key-vh_btn_selector"]::before {
        content: "";
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 1px;
        height: 18px;
        background: var(--border);
    }
    /* "Comparar" es un botón normal (abre una lista, no alterna un valor),
       así que no lleva subrayado — pero sí tiene que dejar de ser una
       cápsula, o desentona en una fila de tabs. Y sobre todo: medía 55px de
       alto y era ÉL quien fijaba el alto de la fila entera; con 32 la franja
       mide lo que miden los tabs. */
    div[class*="st-key-vh_btn_selector"] {
        position: relative;
        padding-left: 16px !important;
    }
    div[class*="st-key-vh_btn_selector"] button {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        color: var(--text-secondary) !important;
        font-size: 14px !important;
        font-weight: 400 !important;
        min-height: 32px !important;
        padding: 3px 4px !important;
    }
    div[class*="st-key-vh_btn_selector"] button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    /* FRANJA DELGADA. Medido dentro de la tarjeta: la fila de controles mide
       32px y la franja entera ocupaba 80 — 16px de padding arriba, 14 de
       hueco entre la fila y el hairline (el gap por defecto del bloque
       vertical de Streamlit), 2 de línea y 16 abajo. O sea 48px de aire
       alrededor de 32px de control.

       El margen negativo del hairline es lo que se come el hueco: su valor
       inline lo pone `franja_linea_inferior()` (-6px), y acá se pisa con
       !important porque un estilo inline sin !important pierde contra uno
       con él. Los -18px horizontales NO se tocan: son los que hacen que la
       línea toque el borde real de la tarjeta. */
    div[class*="st-key-chartcard_ventas_horario_"] {
        padding-top: 2px !important;
        padding-bottom: 4px !important;
    }
    /* El hueco de verdad NO era el margen del hairline sino el `gap: 16px`
       del bloque vertical de la tarjeta: Streamlit separa así CADA bloque
       (fila de controles, hairline, gráfico, pastillas, caption), y con
       cinco bloques son 64px sólo de aire. Medido: bajar el margen negativo
       del hr de -6 a -14 movió la línea 3px, porque el gap seguía mandando.
       Con 6px la franja pasa de 81 a ~57 y el resto de la tarjeta también
       respira menos. */
    /* OJO con el selector: el elemento que lleva la key ES el
       stVerticalBlock (`st.container(key=...)` la pone sobre él), no un
       ancestro suyo. La primera versión de esta regla apuntaba sólo a los
       stVerticalBlock DESCENDIENTES y no movió nada — medido: el gap seguía
       en 16px. Van los dos: el propio y los de adentro. */
    div[class*="st-key-chartcard_ventas_horario_"],
    div[class*="st-key-chartcard_ventas_horario_"] [data-testid="stVerticalBlock"] {
        gap: 4px !important;
    }
    div[class*="st-key-chartcard_ventas_horario_"] hr {
        /* -5 arriba (no más: con el gap de 4px del bloque, a -6 la línea
           se monta sobre la fila de controles) y 2 abajo. Los -18px
           horizontales NO se tocan: son los que la hacen llegar al borde
           real de la tarjeta. */
        margin: -5px -18px 2px !important;
    }

    /* =================================================================== */
    /* REPARTO ADAPTATIVO — el panel del drill toma el alto que sobra        */
    /*                                                                       */
    /* El alto del panel lo calcula Python (`alturas.reparto`) contra la      */
    /* pantalla OBJETIVO, 1366x768. En un monitor más alto eso deja la        */
    /* tarjeta corta y un vacío grande debajo: reportado con captura el       */
    /* 2026-08-14 — ventana de ~1000px de alto, tarjeta de 544 y el detalle   */
    /* mostrando cuatro filas en 150px mientras sobraban 350 de ventana.      */
    /*                                                                       */
    /* Python no puede saber el alto de la ventana (no hay round-trip de JS)  */
    /* pero el CSS sí. Así que: la tarjeta pasa a `height` fijo —la pantalla  */
    /* entera— y el panel toma lo que sobre con `flex: 1 1 0`. El alto de     */
    /* Python queda de PISO, que es lo que vale si esto no aplica.            */
    /*                                                                       */
    /* Sólo con el drill ABIERTO (`_on`), y por eso la key lleva el estado:   */
    /* estirar siempre la tarjeta dejaría el vacío enorme que el proyecto     */
    /* evitó a propósito al elegir `max-height` (ver ENCUADRE, arriba).       */
    /* =================================================================== */
    /* =================================================================== */
    /* PANEL DEL DRILL — la resta la hace el NAVEGADOR                       */
    /*                                                                       */
    /* `--vh-alto-arriba` la publica Python en cada render                   */
    /* (graficos/base.py::publicar_alto_css): es lo que ocupan la franja de   */
    /* controles, el mapa y las pastillas de marcas — las tres cosas que      */
    /* Python sí conoce, porque el alto del mapa lo decide él.                */
    /*                                                                       */
    /* Lo que Python NO puede saber es el alto de la ventana, y por eso la    */
    /* resta vive acá: `--alto-util` es `100dvh` menos el cromo, o sea el     */
    /* alto REAL de la tarjeta en la pantalla de cada usuario. Antes esta     */
    /* cuenta la hacía Python contra `VIEWPORT_OBJETIVO` (1366x768) y el      */
    /* panel salía de 150px con 350 libres debajo en un monitor grande.       */
    /*                                                                       */
    /* El fallback de la `calc` no es decorativo: si algún día alguien borra  */
    /* la publicación del alto, el panel queda usable en vez de invisible.    */
    /* =================================================================== */
    @media screen and (min-width: 769px) {
        div[class*="st-key-vh_panel_drill"] {
            max-height: calc(var(--alto-util)
                             - var(--vh-alto-arriba, 400px)) !important;
            min-height: var(--vh-panel-min, 0px) !important;
            overflow-y: auto !important;
        }
    }

    /* INTENTO FALLIDO, DOCUMENTADO PARA NO REPETIRLO (2026-08-14).
       El alto del panel del drill lo calcula Python contra la pantalla
       objetivo (1366x768), así que en un monitor más alto sobra sitio: con
       ventana de 1000px la tarjeta llegaba a 876 y el panel se quedaba en
       150. La idea era estirarlo por CSS, que sí sabe el alto real.

       NO SE PUEDE con esta cadena de DOM, y se midió paso por paso:
         · `height: var(--alto-util)` en la tarjeta no mueve nada — los
           bloques de Streamlit son flex items con `flex: 1 1 0%` y el
           tamaño lo fija flex-basis (regla #101). Con `min-height` sí:
           la tarjeta pasó de 544 a 876.
         · Aún así el panel seguía en 150, porque su wrapper trae
           `flex: 0 0 150px` (la traducción del `height=` de Python) y el
           wrapper EXTERNO `flex: 0 1 auto`.
         · Al soltar los dos, el bloque intermedio pasó a medir 1.402px:
           crece con el CONTENIDO en vez de repartir el alto del padre. La
           cadena entera está dimensionada por contenido, así que no hay
           dónde apoyar un `flex: 1 1 0`.

       Queda como está: el alto sale de `alturas.reparto()` y en pantallas
       grandes sobran ~50px al pie. Para resolverlo de verdad hace falta que
       Python conozca el alto de la ventana — hoy sólo se lee el User-Agent
       (`_es_movil`), no las dimensiones. */

    /* =================================================================== */
    /* MEDIDAS DEL ÁRBOL — tabs, no pastillas                               */
    /*                                                                       */
    /* Nació para DOS selectores: el de la tabla de marcas y el del árbol.   */
    /* El primero se eliminó el 2026-08-15 (la tabla muestra todas las       */
    /* medidas de entrada), así que hoy el único consumidor es               */
    /* `vh_medidas_arbol` — y por eso el selector se acotó a esa key en vez  */
    /* de seguir con el comodín `[class*="st-key-vh_medidas"]`, que ya no    */
    /* tiene un segundo miembro al que aplicarse (regla #6).                 */
    /*                                                                       */
    /* Pedido del usuario el 2026-08-15: "los toggles se ven bonitos pero    */
    /* ocupan mucho espacio en desktop, me parecen más para móvil". Tiene    */
    /* razón y el argumento no es estético: la pastilla es un TOUCH TARGET   */
    /* (44px es la recomendación de Apple y Google para el dedo). Con mouse  */
    /* el target útil baja a ~24px, así que en desktop se paga el doble de   */
    /* alto por la misma decisión. Cuatro filas de pastillas eran ~140px de  */
    /* cromo antes del primer dato.                                          */
    /*                                                                       */
    /* [aria-pressed="true"] y NO [data-selected]: estas dos son             */
    /* MULTI-select (`selection_mode="multi"`), y ahí Streamlit marca el     */
    /* estado con aria-pressed. El data-selected es el marcado de las        */
    /* single-select (la granularidad y la medida del mapa, más arriba en    */
    /* este mismo archivo). Confundirlos deja el selector mudo — le pasó a   */
    /* Año Pasado durante meses, arquitectura.md #107.                       */
    /*                                                                       */
    /* Sólo desktop: en móvil la pastilla es LA respuesta correcta y se      */
    /* queda como está (mismo breakpoint que _99_movil.py).                  */
    /* =================================================================== */
    @media screen and (min-width: 769px) {
        div[class*="st-key-vh_medidas_arbol"] [data-testid="stButtonGroup"]
            button[data-variant="pills"] {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            /* Misma cuenta que arriba: la caja al texto, no al touch target. */
            min-height: 0 !important;
            height: auto !important;
            padding: 1px 1px 1px !important;
            line-height: 1.2 !important;
            color: var(--text-secondary) !important;
            font-weight: 400 !important;
            font-size: 13.5px !important;
        }
        div[class*="st-key-vh_medidas_arbol"] [data-testid="stButtonGroup"]
            button[data-variant="pills"][aria-pressed="true"] {
            border-bottom-color: var(--accent) !important;
            color: var(--accent-deep) !important;
            font-weight: 600 !important;
        }
        div[class*="st-key-vh_medidas_arbol"] [data-testid="stButtonGroup"] > div {
            gap: 16px !important;
            flex-wrap: wrap !important;
        }
    }

    /* El título comparte fila con los tabs, así que tiene que compartir su
       línea de base: el contenedor de markdown trae margen propio y lo
       dejaba 8px más abajo que las pastillas (medido). */
    div[data-testid="stMarkdownContainer"]:has(> .vh-titulo),
    div[data-testid="stMarkdown"]:has(.vh-titulo) {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1 !important;
    }

    /* 2026-08-23 — "COMPRAS: PÁGINA BLANCA, TARJETAS TENUES" (y el tinte de
       stElementToolbarButtonContainer que dependía de ella) se REVIRTIÓ
       acá, a pedido ("apliquemos el mismo color de fondo del reporte de
       Ajuste, para todos los reportes"). Esta era la mitad "tarjetas" de
       la inversión; la mitad "página" vivía en estilos/_50_fecha.py y se
       revirtió junto con esto — son un par, no se puede sacar una sin la
       otra. Detalle en arquitectura.md regla #177. */
"""
