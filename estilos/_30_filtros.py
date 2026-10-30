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

    /* LA CABECERA DE DOCUMENTOS SUNAT (regla #762): dos filas de controles del
       tamaño de su texto, que envuelven si no entran. Los bloques de Streamlit
       nacen a todo el ancho: acá van `auto`, con la fecha empujada a la derecha.
       Los dos filtros llevan su caja (`role="group"` en la 1.64 de Cloud,
       `data-baseweb` en la 1.59 de la laptop). */
    .st-key-sunat_cab_fila1, .st-key-sunat_cab_filtros {
        flex-wrap: wrap !important;
        gap: 6px 8px !important;
        width: 100% !important;
        align-items: center !important;
    }
    .st-key-sunat_cab_fila1 > *, .st-key-sunat_cab_filtros > *,
    .st-key-sunat_cab_vistas > * {
        width: auto !important;
        flex: 0 0 auto !important;
        min-width: 0 !important;
    }
    /* Un contenedor con key va envuelto en otro nodo: el que se empuja es ése. */
    .st-key-sunat_cab_fila1 > :has(.st-key-sunat_cab_fecha),
    .st-key-sunat_cab_fila1 > .st-key-sunat_cab_fecha {
        margin-left: auto !important;
    }
    .st-key-sunat_cab_fecha {
        width: auto !important;
        flex: 0 0 auto !important;
    }
    .st-key-sunat_cab_vistas {
        flex: 0 0 auto !important;
        width: auto !important;
        flex-wrap: nowrap !important;
        gap: 0 !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        background: var(--bg-card) !important;
    }
    .st-key-sunat_cab_vistas button {
        border: 0 !important;
        border-right: 1px solid var(--border) !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        min-height: 30px !important;
        height: 30px !important;
        padding: 0 12px !important;
    }
    .st-key-sunat_cab_vistas button p {
        font-size: 13px !important;
        color: var(--text-secondary) !important;
        white-space: nowrap !important;
    }
    .st-key-sunat_cab_vistas > *:last-child button { border-right: 0 !important; }
    .st-key-sunat_cab_vistas button:hover { background: var(--accent-tint) !important; }
    .st-key-sunat_cab_vistas button[kind="primary"],
    .st-key-sunat_cab_vistas button[data-testid="stBaseButton-primary"] {
        background: var(--accent-tint) !important;
    }
    .st-key-sunat_cab_vistas button[kind="primary"] p,
    .st-key-sunat_cab_vistas button[data-testid="stBaseButton-primary"] p {
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
    }
    .st-key-sunat_sello_ojo button, .st-key-sunat_sello_grave button, .st-key-sunat_sello_ok button {
        border-radius: 8px !important;
        min-height: 30px !important;
        height: 30px !important;
        padding: 0 10px !important;
    }
    .st-key-sunat_sello_ojo button, .st-key-sunat_sello_grave button {
        border: 1px solid var(--warning-border) !important;
        background: var(--warning-bg) !important;
    }
    .st-key-sunat_sello_ok button {
        border: 1px solid var(--success-text) !important;
        background: var(--success-bg) !important;
    }
    .st-key-sunat_sello_ojo button p, .st-key-sunat_sello_grave button p {
        color: var(--warning-text) !important;
        font-size: 12px !important;
        white-space: nowrap !important;
    }
    .st-key-sunat_sello_grave button p { font-weight: 700 !important; }
    .st-key-sunat_sello_ok button p {
        color: var(--success-text) !important;
        font-size: 12px !important;
        white-space: nowrap !important;
    }
    .st-key-sunat_mes_sunat { width: 205px !important; }
    .st-key-sunat_prov { width: 290px !important; max-width: 100% !important; }
    .st-key-sunat_card_izq .st-key-sunat_mes_sunat [data-testid="stSelectbox"] div[role="group"],
    .st-key-sunat_card_izq .st-key-sunat_prov [data-testid="stSelectbox"] div[role="group"],
    .st-key-sunat_card_izq .st-key-sunat_mes_sunat [data-baseweb="select"] > div,
    .st-key-sunat_card_izq .st-key-sunat_prov [data-baseweb="select"] > div {
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        background: var(--bg-card) !important;
        min-height: 30px !important;
        height: 30px !important;
        padding-left: 6px !important;
    }
    .st-key-sunat_actualizar, .st-key-sunat_dl_xlsx { width: 34px !important; }
    .st-key-sunat_actualizar button, .st-key-sunat_dl_xlsx button {
        min-height: 30px !important;
        height: 30px !important;
        width: 34px !important;
        padding: 0 !important;
    }
    /* En el celular las vistas ya están en la barra de abajo, y apiladas se comían
       media pantalla: la cabecera deja el aviso y un control por renglón, con los dos
       botones juntos al final. */
    @media (max-width: 768px) {
        .st-key-sunat_cab_fila1 > :has(.st-key-sunat_cab_vistas),
        .st-key-sunat_cab_vistas {
            display: none !important;
        }
        .st-key-sunat_cab_fila1, .st-key-sunat_cab_filtros {
            flex-direction: row !important;
            justify-content: flex-start !important;
        }
        .st-key-sunat_cab_fila1 > *,
        .st-key-sunat_cab_fecha,
        .st-key-sunat_cab_filtros > :has(.st-key-sunat_mes_sunat),
        .st-key-sunat_cab_filtros > :has(.st-key-sunat_prov),
        .st-key-sunat_cab_filtros > .st-key-sunat_mes_sunat,
        .st-key-sunat_cab_filtros > .st-key-sunat_prov,
        .st-key-sunat_mes_sunat, .st-key-sunat_prov {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-left: 0 !important;
        }
        .st-key-sunat_mes_sunat, .st-key-sunat_prov,
        .st-key-sunat_card_izq .st-key-sunat_mes_sunat [data-testid="stSelectbox"] input,
        .st-key-sunat_card_izq .st-key-sunat_prov [data-testid="stSelectbox"] input,
        .st-key-sunat_card_izq .st-key-sunat_mes_sunat [data-testid="stSelectbox"] .react-aria-ComboBox,
        .st-key-sunat_card_izq .st-key-sunat_prov [data-testid="stSelectbox"] .react-aria-ComboBox {
            height: 38px !important;
        }
        .st-key-sunat_card_izq .st-key-sunat_mes_sunat [data-testid="stSelectbox"] div[role="group"],
        .st-key-sunat_card_izq .st-key-sunat_prov [data-testid="stSelectbox"] div[role="group"],
        .st-key-sunat_card_izq .st-key-sunat_mes_sunat [data-baseweb="select"] > div,
        .st-key-sunat_card_izq .st-key-sunat_prov [data-baseweb="select"] > div {
            height: 40px !important;
            min-height: 40px !important;
        }
        .st-key-sunat_sello_ojo button, .st-key-sunat_sello_grave button, .st-key-sunat_sello_ok button {
            width: 100% !important;
            height: auto !important;
            padding: 6px 10px !important;
        }
        .st-key-sunat_sello_ojo button p, .st-key-sunat_sello_grave button p, .st-key-sunat_sello_ok button p {
            white-space: normal !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }
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
