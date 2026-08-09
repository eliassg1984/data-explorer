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
           superior derecha. Si se cambia uno, medir el otro. */
        top: 66px !important;
        right: 15px !important;            /* despega del scrollbar del navegador */
        bottom: 0 !important;
        height: calc(100vh - 66px) !important;   /* = 100vh - el top de arriba */
        z-index: 900 !important;
        width: 84px !important;
        overflow-x: hidden !important;
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
        padding-right: 153px !important;   /* rail 116 + 22px de aire + 15px offset del rail */
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
       números (top del rail, estos dos margin) van juntos. */
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) .st-key-compras_prov_drill_wrap {
        margin-top: -51px !important;
    }
    [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) [class*="st-key-ajuste_graf_card_izq_"] {
        margin-top: -56px !important;
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
        /* El contenido recupera el ancho: fuera la reserva del rail. */
        [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row),
        .block-container:has(.st-key-compras_tabs_row) {
            padding-right: 1rem !important;
        }
        /* Rail: de columna fija a tira horizontal en el flujo del documento. */
        .st-key-compras_tabs_row {
            position: static !important;
            width: 100% !important;
            height: auto !important;
            top: auto !important; right: auto !important; bottom: auto !important;
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
        [data-testid="stMainBlockContainer"]:has(.st-key-compras_tabs_row) [class*="st-key-ajuste_graf_card_izq_"] {
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
"""
