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
        /* Y SE VE SIEMPRE. La misma key es cromo de la CABECERA en los
           otros ocho reportes, y desde el 2026-09-13 esa cabecera es una
           capa que aparece con el cursor: `_26_rails_scroll.py` deja en
           reposo `opacity: 0; visibility: hidden; pointer-events: none`
           sobre `.st-key-fecha_ajuste_pill` a secas. Acá el pill NO es
           cromo —es EL filtro de la tarjeta, el rango que se le consulta
           al SIRE— y esa regla lo apagaba: se reportó como "se perdió el
           toggle de fecha acá" (2026-09-18) y en el DOM el contenedor
           estaba en su sitio, invisible, con la fila de arriba de la
           tarjeta vacía por la izquierda.
           `!important` y no especificidad: la regla de reposo y la de
           reveal tienen la misma, así que el empate lo rompe el orden del
           fichero y un descendiente sin `!important` perdería contra el
           reposo — que va DESPUÉS del reveal. `transition: none` porque el
           fade de 160ms de esa capa acá no tiene nada que anunciar. Ver
           `arquitectura.md` regla #457. */
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
        transition: none !important;
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

    /* LA TIRA DE KPIs: SEIS GRUPOS APILADOS Y SE VE UNO
       ────────────────────────────────────────────────────────────────
       2026-09-18, a pedido: «que los datos del recuadro rojo sólo
       aparezcan al pasar el cursor sobre sus columnas». Cada grupo resume
       UNA columna de la tabla y se enciende cuando esa columna tiene el
       cursor encima — el reparto columna → grupo vive en
       `documentos_sunat.py::_COL_A_GRUPO_KPI` y quien mueve la clase es
       `inyecciones/hover_kpis.py::inject_hover_kpis_grid`, que escucha el
       hover DENTRO del iframe de AG Grid.

       ESTE CSS NO SABE CÓMO SE LLAMAN LOS GRUPOS, y es deliberado: la
       primera versión tenía una regla
       `[data-activo="X"] [data-grupo="X"]` por grupo, o sea los seis
       nombres escritos también acá — dos listas que se desincronizan el
       día que alguien agregue una columna. Con una clase `kpi-activo` que
       el JS mueve, los nombres viven en UN solo sitio. Ver
       `arquitectura.md` regla #460. */
    .st-key-sunat_card_izq .sunat-kpis-fila {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 14px;
        font-size: 12.5px;
    }
    /* UNA sola celda de grid con los seis grupos dentro. El hueco mide lo
       que el grupo MÁS ALTO (el de los cuatro estados, que envuelve a dos
       renglones), siempre, así que la cabecera no salta al pasar de una
       columna a otra. Con `position: absolute` el contenedor mediría 0 y
       habría que adivinar un alto fijo — y adivinarlo mal recorta el grupo
       más largo justo cuando se lo quiere leer. */
    .st-key-sunat_card_izq .sunat-kpis {
        display: grid;
        justify-items: end;
        align-items: center;
        flex: 1 1 auto;
        min-width: 0;
    }
    .st-key-sunat_card_izq .sunat-kpi-grupo {
        grid-area: 1 / 1;
        /* FLEX Y NO TEXTO CORRIDO. Cada cifra es un `<span>` con
           `white-space: nowrap` y el `·` que las separa es otro span, sin
           un espacio en medio — así que como texto inline NO HAY DÓNDE
           CORTAR: medido, el grupo de los cuatro estados salía de 670px en
           una sola línea dentro de una celda de 368 y se iba por el
           costado. Como flex, cada cifra es un ítem y el salto ocurre
           entre ítems, que es justo donde tiene que ocurrir. Es la misma
           receta que tenía la tira antes de apilarse; lo que cambió es que
           ahora hay una por grupo. */
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        align-items: center;
        gap: 2px 8px;
        /* Invisible pero MIDIENDO: los seis tienen que seguir aportando su
           alto a la celda. `visibility` y no `display: none` por eso —
           `none` los saca del flujo y el hueco se encogería al grupo
           activo, que es exactamente el salto que se quiere evitar. */
        visibility: hidden;
        opacity: 0;
        transition: opacity 120ms linear;
    }
    .st-key-sunat_card_izq .sunat-kpi-grupo.kpi-activo {
        visibility: visible;
        opacity: 1;
    }
    /* El sello de origen («hoy», «faltan los últimos días») va FUERA de la
       pila y siempre visible: no es un total de columna, es la única señal
       de que lo que hay en pantalla puede estar incompleto (regla #197).
       Eso no se esconde detrás de un gesto que hay que descubrir. */
    .st-key-sunat_card_izq .sunat-kpi-sello {
        flex: 0 0 auto;
        white-space: nowrap;
    }
"""
