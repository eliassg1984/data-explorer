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
    [data-testid="stHorizontalBlock"]:has(.st-key-fecha_ajuste_pill) {
        gap: 8px 10px !important;
    }
    .st-key-sunat_card_izq [data-testid="stColumn"]:has(.st-key-fecha_ajuste_pill) {
        min-width: 200px !important;
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
        flex: 0 0 78px !important;
        min-width: 78px !important;
    }
    /* Y EL PILL NO PUEDE DESBORDAR SU COLUMNA. Su `width: 100%` de más
       arriba resolvía contra el `stLayoutWrapper` que Streamlit le mete
       alrededor, que nace en `width: fit-content` — o sea 210px, mida lo
       que mida la columna. Con el wrapper al 100% el pill sigue a su
       columna y, si algún día no cabe, el que cede es el texto. */
    .st-key-sunat_card_izq
    [data-testid="stLayoutWrapper"]:has(> .st-key-fecha_ajuste_pill) {
        width: 100% !important;
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
        /* Sin margen: los 2px de abajo eran para despegarlo del renglón de
           selectores que tenía DEBAJO, y desde el 2026-09-18 va al lado de
           ellos, no encima (regla #464). */
        margin: 0 !important;
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
    /* Y SU CAJA TIENE QUE MEDIR LO QUE MIDE. Un `st.markdown` con HTML de
       BLOQUE trae `margin-bottom: -16px` en su `stMarkdownContainer` (regla
       #162, puesto para cancelar el 1rem que Streamlit deja detrás). Desde
       que la tira bajó a su propio renglón (2026-09-18) eso la rompe:
       medido, su contenedor salía de 4px —20 de contenido menos los 16—
       mientras la tira seguía dibujando 20, así que se montaba 10px sobre
       la tabla. Con el gap de la tarjeta en 6px ese -16 ya no cancela
       nada, sobra. Ver regla #464. */
    .st-key-sunat_kpis_fila [data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }
"""
