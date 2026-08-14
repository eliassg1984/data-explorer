"""estilos._80_cards - Tarjetas de los dashboards: .chart-card, wrappers ajuste_graf_card_* y bloques compras_prov_card_* del drill de Proveedor.

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
       "clásicos" (Familia/Evolución) o a los del drill Proveedor.
       ============================================================ */
    div[class*="st-key-ajuste_graf_card_"] {
        background: var(--bg-card) !important;
        border: none !important;                    /* look plano: sin borde de Streamlit */
        border-radius: 20px !important;
        padding: 16px 18px;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);  /* sombra tenue reemplaza al borde */
    }
    /* Anula el borde que Streamlit pinta en el hijo directo del container
       (stVerticalBlockBorderWrapper) cuando border=True está activo. */
    div[class*="st-key-ajuste_graf_card_"] > div {
        border: none !important;
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
        div[class*="st-key-ajuste_graf_card_"],
        div[class*="st-key-compras_prov_card_"] {
            max-height: var(--alto-util);
            overflow-y: auto;
            overflow-x: hidden;
        }
        /* Barra fina y discreta, igual criterio que el panel del asistente
           (_85_asistente.py): la tarjeta ya es un marco, la barra no tiene
           que competir con el contenido. */
        div[class*="st-key-ajuste_graf_card_"]::-webkit-scrollbar,
        div[class*="st-key-compras_prov_card_"]::-webkit-scrollbar {
            width: 6px;
        }
        div[class*="st-key-ajuste_graf_card_"]::-webkit-scrollbar-thumb,
        div[class*="st-key-compras_prov_card_"]::-webkit-scrollbar-thumb {
            background: var(--scroll-thumb);
            border-radius: 3px;
        }
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
        padding: 0 1.5px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        transition: background-color 0.15s ease !important;
    }
    div[class*="st-key-ventas_comp_sw_"] [data-testid="stCheckbox"]
        label:has(input:checked) > div:not([data-testid]) {
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
        label:has(input:checked) > div:not([data-testid]) > div {
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
    /* Panel "Detalle" — trigger FLOTANTE sobre el gráfico (2026-08-14)      */
    /*                                                                       */
    /* Antes vivía en un st.expander EN FLUJO, debajo del gráfico: abrirlo   */
    /* empujaba la explicación de "Ventana: ..." que sigue después. Pedido  */
    /* del usuario con referencia visual: el panel "Comparar con" de un     */
    /* gráfico de índices, que flota arriba-izquierda del plot y no mueve   */
    /* nada al abrirse.                                                      */
    /*                                                                       */
    /* Un st.popover ya resuelve la mitad sólo: el contenido abierto        */
    /* (`stPopoverBody`) se renderiza en un PORTAL fuera de este árbol —     */
    /* mismo mecanismo que `ai_float_wrap` (_85_asistente.py) y             */
    /* `fecha_panel` (_50_fecha.py) — así que NUNCA empuja layout, esté el   */
    /* trigger flotando o no. La otra mitad (que el TRIGGER quede pegado    */
    /* arriba-izquierda del plot en vez de debajo) es este bloque: ancla    */
    /* `position: relative` en `_slot_graf` —el contenedor directo del      */
    /* gráfico, con key `ventas_comp_chart_slot_<grano>`, NO toda la        */
    /* tarjeta— para que el `top`/`left` no dependan de cuánto mida la      */
    /* franja de controles (grano/ventana/alinear/vista) de arriba.         */
    /* =================================================================== */
    div[class*="st-key-ventas_comp_chart_slot_"] { position: relative; }
    div[class*="st-key-ventas_comp_chart_slot_"] .st-key-ventas_comp_detalle_float {
        position: absolute;
        top: 6px; left: 8px; z-index: 5;
        width: auto !important;
    }
    .st-key-ventas_comp_detalle_float [data-testid="stElementToolbar"] {
        display: none;
    }
    /* Gris translúcido: --bg-primary es el "lienzo general" de la paleta
       (_00_base.py), el único tono gris neutro que ya existe — no se
       inventa un #hex nuevo para el pedido de "cierto tono gris
       transparente". El blur es el mismo recurso que la franja superior
       "cristal esmerilado" (_40_ajuste_franja.py): sin él, un fondo
       semi-transparente sobre las barras del gráfico se lee sucio en vez
       de vidrio esmerilado. */
    .st-key-ventas_comp_detalle_float [data-testid="stPopover"] button {
        min-width: 0 !important;
        min-height: 0 !important;
        padding: 4px 12px !important;
        font-size: 11.5px !important;
        font-weight: 500 !important;
        border-radius: 999px !important;
        background: color-mix(in srgb, var(--bg-primary) 88%, transparent) !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        box-shadow: var(--shadow) !important;
        transition: border-color 0.12s, color 0.12s !important;
    }
    .st-key-ventas_comp_detalle_float [data-testid="stPopover"] button:hover,
    .st-key-ventas_comp_detalle_float [data-testid="stPopover"] button[aria-expanded="true"] {
        border-color: var(--accent) !important;
        color: var(--accent-deep) !important;
    }
    /* Panel abierto: portal fuera de `_slot_graf`, así que NO se puede
       scopear por ancestro — se busca por el container-key propio que
       ventas_comparativo.py dibuja adentro (`ventas_comp_detalle_panel`),
       mismo truco que `fecha_panel` / `ai_panel`. Mismo tono gris
       translúcido que el trigger, para que se lea como una sola pieza de
       vidrio (chip + panel), no dos superficies distintas. */
    [data-testid="stPopoverBody"]:has(.st-key-ventas_comp_detalle_panel) {
        background: color-mix(in srgb, var(--bg-primary) 92%, transparent) !important;
        backdrop-filter: blur(10px) saturate(1.3) !important;
        -webkit-backdrop-filter: blur(10px) saturate(1.3) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: var(--shadow-md) !important;
    }
    /* Móvil: el plot es angosto y un chip absoluto sobre la esquina tapa
       barras — mismo criterio que prov_pop_float/gran_float en
       graficos/compras/_css_proveedor.py (>640px flota, <=640px fluye).
       El popover sigue sin empujar nada al abrirse; sólo cambia dónde
       vive el trigger cuando está cerrado. */
    @media (max-width: 640px) {
        div[class*="st-key-ventas_comp_chart_slot_"] .st-key-ventas_comp_detalle_float {
            position: static !important;
            width: 100% !important;
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
       ~470: eso es la mitad del "sube y baja" que se ve en cada clic (la
       otra mitad era la cabecera vacía, ver regla #108).
       El número sale de las piezas reales: 32 de padding + 42 de cabecera +
       52 de franja + 340 de figura = 466. Es min-height, no height: el
       caption y el panel "Detalle" pueden hacerla más alta sin problema.
       Sólo desktop — en móvil la figura mide 260 y el patrón es scroll de
       página, mismo criterio que el resto del encuadre. */
    @media screen and (min-width: 769px) {
        div[class*="st-key-chartcard_ventas_comparativo"] {
            min-height: 466px;
        }
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
    div[class*="st-key-ajuste_graf_card_"]:has([class*="st-key-ventas_g_dia"]) {
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
    div[class*="st-key-ajuste_graf_card_"]:has([class*="st-key-ventas_g_dia"])
        > [data-testid="stLayoutWrapper"],
    div[class*="st-key-ajuste_graf_card_"]:has([class*="st-key-ventas_g_dia"])
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

    /* =================================================================== */
    /* FRANJA DE CONTROLES DE COMPRAS › FAMILIA                              */
    /*                                                                       */
    /* Mismo patrón que Ventas (Por día #104, Año Pasado #107): tabs de       */
    /* texto con subrayado en el activo, no pastillas. Tres grupos afines    */
    /* ("Agrupar por" · "Vista" · "Top") separados por hairlines — a          */
    /* diferencia de Año Pasado, acá los CUATRO controles (incluido el        */
    /* popover de series) responden a la misma pregunta ("cómo se ve ESTE    */
    /* gráfico"), no dos ejes distintos: no hace falta separar con espacio   */
    /* ni columna espaciadora, los cuatro van en fila con línea entre cada    */
    /* uno.                                                                  */
    /*                                                                       */
    /* [data-selected="true"], NO [aria-pressed="true"]: los tres pills son   */
    /* single-select (sin `selection_mode=`) — Streamlit los marca con        */
    /* `role="radio"` + `data-selected`, no con `aria-pressed` (ese es el     */
    /* marcado de MULTI-select). Se aprendió esta vez a la primera: en        */
    /* Año Pasado el selector viejo estuvo muerto desde el primer commit      */
    /* (arquitectura.md #107, segundo addendum).                             */
    /* =================================================================== */
    div[class*="st-key-compras_fam_gran"] [data-testid="stButtonGroup"]
        button[data-variant="pills"],
    div[class*="st-key-compras_fam_vista"] [data-testid="stButtonGroup"]
        button[data-variant="pills"],
    div[class*="st-key-compras_fam_topn"] [data-testid="stButtonGroup"]
        button[data-variant="pills"] {
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        padding: 3px 1px !important;
        color: var(--text-secondary) !important;
        font-weight: 400 !important;
        font-size: 15px !important;
    }
    div[class*="st-key-compras_fam_gran"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"],
    div[class*="st-key-compras_fam_vista"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"],
    div[class*="st-key-compras_fam_topn"] [data-testid="stButtonGroup"]
        button[data-variant="pills"][data-selected="true"] {
        border-bottom-color: var(--accent) !important;
        color: var(--accent-deep) !important;
        font-weight: 600 !important;
    }
    /* El gap real va en el hijo directo de stButtonGroup (que es
       display:block), no en él — mismo hallazgo que en Ventas. `nowrap`
       preventivo: aprendido de Año Pasado (regla #107, addendum) que un
       ajuste sin margen apila con cualquier ventana un poco más angosta.
       Acá el texto es corto ("Semana", "Agrupado", "20") y hay bastante
       margen, pero la protección no cuesta nada. */
    div[class*="st-key-compras_fam_gran"] [data-testid="stButtonGroup"] > div,
    div[class*="st-key-compras_fam_vista"] [data-testid="stButtonGroup"] > div,
    div[class*="st-key-compras_fam_topn"] [data-testid="stButtonGroup"] > div {
        gap: 18px !important;
        flex-wrap: nowrap !important;
    }
    /* Separadores: cada grupo dibuja el suyo a su IZQUIERDA (colgado de su
       key, no de una posición) — "Agrupar por" es el primero y no lleva. */
    div[class*="st-key-compras_fam_vista"],
    div[class*="st-key-compras_fam_topn"],
    div[class*="st-key-compras_fam_ser_pop"] {
        position: relative;
        padding-left: 17px !important;
    }
    div[class*="st-key-compras_fam_vista"]::before,
    div[class*="st-key-compras_fam_topn"]::before,
    div[class*="st-key-compras_fam_ser_pop"]::before {
        content: "";
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 1px;
        height: 18px;
        background: var(--border);
    }
    /* El popover de series es un control DISTINTO (abre una lista, no
       alterna un valor): no lleva el tratamiento de tab/subrayado, sólo se
       alinea verticalmente con la fila de pills — su botón trae su propio
       padding (definido inline en familia.py) y por defecto queda un poco
       más alto que los pills de texto plano. */
    div[class*="st-key-compras_fam_ser_pop"] {
        margin-top: 4px !important;
    }
"""
