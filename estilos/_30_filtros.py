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
    /* Las dos filas, juntas: el bloque vertical de Streamlit mete 1rem de
       GAP (no margen — por eso hay que atacar al padre, no al widget) y
       separaba los selectores como si fueran dos secciones distintas, en
       vez de dos lineas de la misma lista. El `:has()` acota al bloque que
       de verdad contiene los selectores: sin el, cualquier otra pila de la
       tarjeta se comprimiria tambien. */
    .st-key-sunat_card_izq [data-testid="stVerticalBlock"]:has(
        > [data-testid="stElementContainer"] > [data-testid="stSelectbox"]) {
        gap: 2px !important;
    }
    /* Los dos iconos de accion (refrescar / exportar) a la altura del texto
       y sin el marco de boton de Streamlit. */
    .st-key-sunat_actualizar button,
    .st-key-sunat_dl_xlsx button {
        min-height: 0 !important;
        height: 30px !important;
        padding: 0 !important;
        border: 1px solid var(--border) !important;
        background: transparent !important;
        color: var(--text-secondary) !important;
    }
    .st-key-sunat_actualizar button:hover,
    .st-key-sunat_dl_xlsx button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
        border-color: var(--accent-light) !important;
    }

    /* El pill de FECHA, cuando lo dibuja el drill dentro de su tarjeta.
       ────────────────────────────────────────────────────────────────
       Es el MISMO widget de la franja (`franja_fecha.render()`), sólo que
       llamado desde otro sitio — no una copia. Y por eso arrastra el
       `position: fixed` + coordenadas que le ponen `_40_ajuste_franja.py`
       y `_50_fecha.py` para anclarlo arriba a la izquierda: sin devolverlo
       al flujo normal se quedaría flotando sobre la franja, que es justo
       de donde lo sacamos.

       Scopeado por `sunat_card_izq`: la MISMA key `fecha_ajuste_pill` sigue
       viviendo en la franja en todos los demás reportes y vistas, con su
       posicionamiento intacto. */
    .st-key-sunat_card_izq .st-key-fecha_ajuste_pill {
        position: static !important;
        top: auto !important; left: auto !important;
        right: auto !important; bottom: auto !important;
        width: 100% !important;
        max-width: none !important;
        margin: 0 0 2px 0 !important;
        z-index: auto !important;
    }
    /* El trigger, con el mismo lenguaje que los dos selectores de al lado:
       texto + icono, sin caja. Sin esto entra con el marco de 210px de
       ancho fijo que necesita la franja para anclar los chips a su
       derecha (esa aritmética de tres números vive en _50_fecha.py). */
    .st-key-sunat_card_izq .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
        min-width: 0 !important;
        width: 100% !important;
        justify-content: flex-start !important;
        height: 26px !important;
        min-height: 0 !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
    }
    .st-key-sunat_card_izq .st-key-fecha_ajuste_pill
    [data-testid="stPopover"] button:hover {
        background: transparent !important;
        color: var(--accent-deep) !important;
    }
"""
