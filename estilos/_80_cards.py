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
           --bg-primary (#f6f6f8, "lienzo general") al 92%, y el usuario
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
       tapa barras — mismo criterio que prov_pop_float/gran_float en
       graficos/compras/_css_proveedor.py (>640px flota, <=640px fluye).
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

    /* `compras_fam_titulo_franja` (el título que se mudó a la franja
       superior, ver estilos/_50_fecha.py) se dibuja como HERMANO, justo
       antes de esta fila — y aunque es position:fixed y colapsa a 0px de
       alto, su wrapper de Streamlit sigue contando como flex item del
       bloque vertical que los contiene: el gap del flex se aplica IGUAL
       entre "un item de 0px" y el siguiente. -16px lo cancela — mismo
       hallazgo que en Ventas › Comparativo (arquitectura.md regla #120). */
    .st-key-compras_fam_controles_row {
        margin-top: -16px !important;
        margin-bottom: -10px !important;
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
"""
