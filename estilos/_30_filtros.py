"""estilos._30_filtros - Boton de filtros (popover) con contorno indigo.

Extraido de estilos.py (lineas 880-897 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* BOTÓN FILTROS (popover) — a juego, grande y con contorno índigo      */
    /* =================================================================== */
    [data-testid="stPopover"] button {
        min-width: 180px !important;
        padding: 14px 26px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 999px !important;
        transition: all .15s ease !important;
    }
    [data-testid="stPopover"] button:hover {
        border-color: var(--accent-hover) !important;
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }

    /* =================================================================== */
    /* DOCUMENTOS SUNAT — LOS DOS SELECTORES, COMO TEXTO                     */
    /*                                                                       */
    /* A pedido 2026-08-21: "mas minimalista, una encima de la otra, pero    */
    /* como si fuesen textos". Un `st.selectbox` de Streamlit 1.59 se pinta  */
    /* con react-aria, y la CAJA (borde 1px + fondo blanco + 40px de alto)   */
    /* no la lleva ni el `stSelectbox` ni el `input`, sino el                */
    /* `div[role="group"]` que hay entre los dos — medido en el navegador,   */
    /* porque por el nombre de la clase (emotion, cambia entre builds) no    */
    /* se puede adivinar. Estilar el ancestro no alcanza: hay que ir a ese   */
    /* nodo.                                                                 */
    /*                                                                       */
    /* Se conserva el chevron: sin ninguna affordance, un texto que despliega */
    /* una lista al hacer clic no se distingue de una etiqueta muerta.       */
    /* =================================================================== */
    .st-key-sunat_card_izq [data-testid="stSelectbox"] div[role="group"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        min-height: 0 !important;
    }
    .st-key-sunat_card_izq [data-testid="stSelectbox"] input {
        padding: 0 !important;
        height: auto !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
        cursor: pointer !important;
    }
    /* El alto lo fija el `input` (40px de la altura de control de
       Streamlit), no el grupo — bajarlo ahi es lo que convierte la caja en
       una linea de texto. */
    .st-key-sunat_card_izq [data-testid="stSelectbox"] input,
    .st-key-sunat_card_izq [data-testid="stSelectbox"] div[role="group"],
    .st-key-sunat_card_izq [data-testid="stSelectbox"] .react-aria-ComboBox {
        height: 26px !important;
    }
    /* ACÁ VIVIÓ el `gap: 2px` que juntaba los DOS renglones de filtros
       —fecha arriba, los selectores debajo— cuando el bloque vertical de
       Streamlit los separaba 1rem como si fueran dos secciones distintas.
       Se retiró el 2026-09-18: los cuatro filtros pasaron a compartir UN
       renglón (regla #464), así que ya no hay dos bloques que juntar y ese
       `:has()` sólo alcanzaba a bloques de un hijo, donde el gap no pinta
       nada. Lo que sí hace falta ahora está tres reglas más abajo, sobre
       la tarjeta: apretar el renglón de filtros contra la tira y la tira
       contra la tabla. Se anota en vez de borrarse en silencio porque el
       CSS huérfano es la regla #49. */

    /* LOS CINCO CONTROLES DE LA CABECERA, EN UN RENGLÓN — Y SU PISO
       ────────────────────────────────────────────────────────────────
       Desde el 2026-09-18 el pill de fecha y los tres filtros comparten
       fila (regla #464). En 1358 y en 1280 entran de sobra; medido en
       **1024**, que es el ancho útil de la laptop objetivo, NO entraban y
       el fallo no era cosmético: el pill se plantaba en sus 210px dentro
       de una columna de 176 y se montaba 18px SOBRE el filtro de al lado,
       y «Todos los estados (4,619)» salía cortado.

       Se arregla con un PISO por columna, no apretando: `stHorizontalBlock`
       ya viene con `flex-wrap: wrap` de fábrica y las columnas con
       `min-width: auto`, así que basta darle a cada una lo que de verdad
       necesita para que, cuando no quepan, BAJEN en vez de pisarse.

       Los cinco números salen de medir el peor contenido de cada control,
       no de repartir el ancho: el pill 200 (16 del ícono + 151 de
       «17 sep 2025 – 16 sep 2026» + 16 del chevron + los gaps), «Mes en
       SUNAT» 135 («Mes presentado» + 32 de cromo del selectbox), el de
       proveedor 195 (su piso histórico, ver `_opciones_proveedor`), el de
       estado 192 («Todos los estados (4,646)» + cromo) y la botonera 78.
       Suman 800.

       Y EL GAP DE LA FILA BAJA A 10 (de los 16 de fábrica): 24px menos de
       aire entre cuatro filtros de la MISMA tabla, que no son cuatro
       secciones. Ayuda al reparto y de paso se leen como un grupo.

       DÓNDE ENVUELVE, medido y no deducido: a 1366 y a 1280 va en UN
       renglón, con los cuatro controles a 275/187/380/249 y 75px de holgura
       sobre el pill. A **1024 envuelve** —pill/mes/proveedor arriba, estado
       y la botonera debajo— y ahí está bien: nada se corta y nada se pisa,
       que era el bug. No se persiguió el renglón único a 1024 porque el
       corte NO lo decide el piso sino la BASE: Streamlit le da a cada
       columna `flex: 1 1 calc(<su %> - 16px)`, el % sale de los números de
       `st.columns`, y flexbox rompe la línea con la base ya clampeada por
       el `min-width` pero ANTES de encoger a nadie. Con el reparto de
       Python el de proveedor pide 245 de base —más que sus 195 de piso—,
       así que la suma hipotética da 890 contra 857 y el último ítem baja.
       Forzarlo sería fijarle `flex-basis` a las cuatro columnas, y con eso
       los números de `st.columns` dejarían de significar nada: el ancho lo
       decidiría entero este fichero y el `.py` mentiría. Ver regla #464. */
    .st-key-sunat_card_izq
    [data-testid="stHorizontalBlock"]:has(.st-key-sunat_f_fila) {
        gap: 8px 10px !important;
    }
    .st-key-sunat_card_izq [data-testid="stColumn"]:has(.st-key-sunat_f_fila) {
        /* 260 y no 200: el botón dice el atajo Y sus fechas («Últimos 12
           meses · 12 oct 2025 – 11 oct 2026», 262px medidos a 1323 de ancho). */
        min-width: 270px !important;
    }
    .st-key-sunat_card_izq [data-testid="stColumn"]:has(.st-key-sunat_mes_sunat) {
        min-width: 135px !important;
    }
    .st-key-sunat_card_izq [data-testid="stColumn"]:has(.st-key-sunat_prov) {
        min-width: 195px !important;
    }
    .st-key-sunat_card_izq [data-testid="stColumn"]:has(.st-key-sunat_estado) {
        min-width: 192px !important;
    }
    /* La BOTONERA no compite por ancho: 78px fijos (dos glifos de 31 y su
       gap) y sin `flex-grow`. Dos motivos: son dos íconos y no necesitan
       los 61px que les daba el reparto proporcional, y siendo el ÚLTIMO
       ítem de la fila es el primero que envolvería — estirado al ancho de
       una línea entera quedaría como un error, y clavado en 78 baja como lo
       que es, una botonera.

       LOS DOS `:has()` SON OBLIGATORIOS, y el primer intento llevaba uno.
       Adentro de esta columna hay OTRO `st.columns(2)` —un ícono cada uno—
       y sus columnas también contienen `st-key-sunat_actualizar`, así que
       un solo `:has()` les clavaba los 78px a ellas: el par se quedaba sin
       sitio, envolvía, y los iconos salían UNO DEBAJO DEL OTRO con la fila
       de la cabecera en 76px de alto en vez de 30 (medido). Pidiendo las
       DOS keys a la vez sólo matchea la columna de afuera, que es la única
       que tiene los dos botones adentro. */
    .st-key-sunat_card_izq [data-testid="stColumn"]:has(.st-key-sunat_actualizar):has(.st-key-sunat_dl_xlsx) {
        flex: 0 0 125px !important;
        min-width: 125px !important;
    }
    /* 125 y no 78 desde el 2026-10-19: un TERCER ícono, el pedido en lote
       de los XML que faltan (`sunat_lote_btn`, regla #675). Tres glifos de 31
       y dos gaps de 16. */
    /* El GAP de la tarjeta: 6px y no el 1rem de Streamlit. Sus hijos son
       tres —el renglón de filtros, la tira de KPIs y la tabla— y los tres
       hablan de lo mismo, así que un rem entre cada par son 32px de aire
       muerto en una tarjeta que se pidió compacta. La key es la del propio
       bloque vertical (Streamlit le pone la clase AL bloque, no a un
       padre), así que el selector no lleva `>`. */
    .st-key-sunat_card_izq {
        gap: 6px !important;
    }
    /* Los dos iconos de accion (refrescar / exportar) a la altura del texto
       y sin el marco de boton de Streamlit. */
    .st-key-sunat_actualizar button,
    .st-key-sunat_lote_btn button,
    .st-key-sunat_dl_xlsx button {
        min-height: 0 !important;
        height: 30px !important;
        padding: 0 !important;
        border: 1px solid var(--border) !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
    }
    /* La confirmación del pedido en lote: UN renglón arriba de la tabla
       (regla #675). Sin el margen de -16px del markdown (regla #162) el
       texto no queda alineado con los botones, y los botones van del alto
       de los íconos de la botonera. */
    .st-key-sunat_lote_panel [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
    .st-key-sunat_lote_pedir button,
    .st-key-sunat_lote_cancelar button {
        min-height: 0 !important;
        height: 28px !important;
        padding: 0 12px !important;
        font-size: 12px !important;
    }
    .st-key-sunat_actualizar button:hover,
    .st-key-sunat_lote_btn button:hover,
    .st-key-sunat_dl_xlsx button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
        border-color: var(--accent-light) !important;
    }

    /* La FECHA de la tarjeta: el botón de `selector_fecha_tarjeta`, con
       la píldora de las tarjetas de Compras y Movimientos (regla #633).
       Hasta el 2026-10-11 era el pill de la franja (`franja_fecha.render()`)
       traído al flujo, con su propio panel de atajos + `date_input`.
       El botón cede con «…» si la columna no le alcanza: el texto entero
       («Últimos 12 meses · 12 oct 2025 – 11 oct 2026») es más ancho que el
       piso de la columna. */
    .st-key-sunat_f_fila {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        width: 100% !important;
        min-width: 0 !important;
    }
    .st-key-sunat_f_fila > [data-testid="stElementContainer"],
    .st-key-sunat_f_escala {
        min-width: 0 !important;
        max-width: 100% !important;
    }
    .st-key-sunat_f_escala button {
        min-width: 0 !important;
        max-width: 100% !important;
        height: 28px !important;
        min-height: 28px !important;
        padding: 0 12px !important;
        border-radius: 999px !important;
        border: 1px solid var(--border) !important;
        background: var(--bg-card) !important;
        color: var(--text-secondary) !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        line-height: 1 !important;
        white-space: nowrap !important;
        box-shadow: var(--shadow) !important;
    }
    .st-key-sunat_f_escala button p {
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }
    .st-key-sunat_f_escala button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    /* El chevron de Streamlit: el WRAPPER, como en `cp_rank_escala`. */
    .st-key-sunat_f_escala button > div > div:last-child:not(:first-child) {
        display: none !important;
    }

    /* (Acá vivía la TIRA DE KPIs de la tabla de Documentos SUNAT: seis
       grupos apilados que se encendían con el cursor sobre su columna,
       reglas #460 y #464. Se fue el 2026-10-02, a pedido, para que la
       tabla suba un renglón: sus conteos son ahora el modo «Resumen del
       cruce» de la tarjeta de abajo. Regla #586.) */
"""
