"""graficos.compras._css_proveedor - CSS del drill de Proveedor.

Bloque estatico (sin interpolacion) que estaba embebido como un
st.markdown de 529 lineas DENTRO de _compras_proveedor_drill, donde
tapaba la logica. Se saco a este modulo el 2026-08-08.

Por que NO vive en `estilos/` pese a la regla de CLAUDE.md: estas reglas
estan scopeadas a las keys de este drill y solo tienen sentido cuando el
drill se dibuja. `estilos/` se inyecta en TODAS las paginas via
inject_css(); moverlo ahi lo aplicaria siempre, que es un cambio de
comportamiento, no una reorganizacion. El drill lo inyecta cuando toca.
"""

CSS = """        <style>
        .st-key-compras_prov_card_chart { position: relative; }
        /* La leyenda se movió a la derecha (vertical); la banda superior solo
           tiene popover (izq) + toggle (der), alineados arriba. */
        .st-key-gran_float {
            position: absolute; top: 14px; right: 16px; z-index: 5;
            width: auto !important;
            /* Aplanar todo lo que Streamlit mete arriba del ButtonGroup
               (label oculto, padding del stElementContainer). Sin esto el
               grupo de pills queda ~14px más abajo que la fila de proveedores. */
            padding: 0 !important; margin: 0 !important;
            line-height: 0 !important;
        }
        .st-key-gran_float [data-testid="stElementContainer"],
        .st-key-gran_float [data-testid="stElementContainer"] > div,
        .st-key-gran_float [data-testid="stVerticalBlock"] {
            padding: 0 !important; margin: 0 !important; gap: 0 !important;
        }
        /* Contenedor de las pills Día/Semana/Mes/Año: solo más delgado,
           sin tocar la fuente ni la ubicación originales. */
        .st-key-gran_float [data-testid="stButtonGroup"] {
            margin: 0 !important; padding: 0 !important;
        }
        .st-key-gran_float [data-testid="stButtonGroup"] button {
            min-height: 0 !important;
            height: auto !important;
            padding-top: 1px !important;
            padding-bottom: 1px !important;
            line-height: 1.3 !important;
        }
        /* Popover de proveedores flotando arriba-IZQUIERDA (compacto).
           Es el fallback para 641-900px; en desktop sube a la franja (ver
           el bloque min-width:901px de aca abajo) y en <=640px pasa a
           static (media query al final del archivo). */
        .st-key-prov_pop_float {
            position: absolute; top: 14px; left: 16px; z-index: 5;
            width: auto !important;
        }
        /* DESKTOP: el filtro de proveedores sube a la FRANJA superior, a la
           derecha — misma fila que fecha / Familia / Subfamilia (a pedido).
           Mismo truco que ya usan fecha_ajuste_pill, chips_ajuste_tabla y
           los titulos fantasma (arquitectura.md regla #120): position:fixed
           lo saca de la tarjeta y lo ancla a la franja, sin importar donde
           viva en el DOM.
           · top:8px es el mismo que usan el pill y los chips.
           · El `right` lo alinea con el borde derecho de la tarjeta que
             queda justo abajo: --rail-der-res es lo que el contenido le
             reserva al rail derecho, +10px del margen exterior de
             Streamlit (los mismos 163px que documenta
             estilos/_40_ajuste_franja.py). Se deriva de la variable en vez
             de un px suelto para que siga al rail cuando se pliega.
           · z-index 23 = el de sus vecinos de la franja.
           · left/bottom a auto: sin eso el left:16px de la regla de arriba
             seguiria activo y lo estiraria de lado a lado.
           El umbral es 1230px y NO los 901px del resto de la franja: abajo
           de ~1223px este popover se monta sobre los chips Familia/
           Subfamilia, que no pueden ceder ancho porque llevan
           min-width:230px cada uno (el addendum de Compras/Inventario/
           Salidas en estilos/_50_fecha.py). La cuenta del ancho minimo en
           el que entran los cuatro:
               391 (left de los chips) + 492 (su ancho: 230*2 + 32 de gaps)
               + 12 de aire + 165 (este popover) + 163 (su margen derecho)
               = 1223  ->  se redondea a 1230.
           Abajo de eso cae al fallback de arriba (dentro de la tarjeta),
           que es justo lo que ya hacen los titulos fantasma de Ventas
           (1220px) y Compras > Familia (1310px): antes que apilar
           controles ilegibles, se vuelve a la posicion previa.
           Compras no tiene cortes, asi que `fecha_corte_nav` —el otro
           inquilino de esta esquina— nunca se renderiza aca: sin colision. */
        @media (min-width: 1230px) {
            .st-key-prov_pop_float {
                position: fixed !important;
                top: 8px !important;
                left: auto !important;
                bottom: auto !important;
                right: calc(var(--rail-der-res) + 10px) !important;
                z-index: 23 !important;
            }
        }
        /* Nombre de la vista ("Proveedor") PRIMERO en la franja, pegado a
           la izquierda y ANTES del pill de fecha — igual que en Compras >
           Familia (2da vuelta: nacio a la derecha del pill y se movio a
           pedido). El pill y los chips se corren para hacerle sitio.
           Cadena de numeros acoplada, medida en vivo:
             175 = el left original del pill -> ahi va ahora el titulo.
             100 = ancho reservado para la palabra "Proveedor" a 14px/700.
             287 = 175 + 100 + 12 de aire -> nuevo left del PILL.
             503 = 287 + 210 (ancho fijo del pill) + 6 -> left de los chips.
           Mover uno descoloca la fila entera. Ojo: el 503 de los chips es
           el MISMO que cuando el titulo estaba a la derecha del pill — el
           ancho total ocupado no cambia, solo el orden — asi que el umbral
           de abajo tampoco se movio:
             503 + 492 (chips) + 12 + 165 (prov_pop) + 163 = 1335 -> 1340.
           Los DOS bloques (este y el de prov_pop_float) tienen que entrar
           o salir juntos, si no el titulo se superpondria con unos chips
           que no se corrieron: por eso el `right` de prov_pop_float se
           repite aca, para que en la banda 1230-1339 (titulo oculto, pill
           y chips sin correr) siga con su propia cuenta, que ahi da. */
        .st-key-compras_prov_titulo_franja {
            position: fixed !important;
            top: 8px !important;
            left: 175px !important;
            right: auto !important;
            bottom: auto !important;
            width: 100px !important;
            z-index: 23 !important;
            margin: 0 !important;
            display: none !important;   /* oculto por defecto; ver abajo */
        }
        @media (min-width: 1340px) {
            .st-key-compras_prov_titulo_franja { display: block !important; }
            .st-key-compras_prov_titulo_franja [data-testid="stMarkdownContainer"] p {
                margin: 0 !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
                font-size: 14px !important;
                font-weight: 700 !important;
                line-height: calc(var(--cab-altura) - 8px) !important;
                color: var(--text-primary) !important;
            }
            /* El pill de fecha cede los 112px que ocupa el titulo delante
               suyo. Clase TRIPLICADA para ganarle a la regla desktop de
               estilos/_50_fecha.py, que ya usa la key duplicada (0,2,0),
               sin depender del orden en que se inyecten los archivos. */
            .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill {
                left: 287px !important;
            }
            /* Los chips arrancan despues del pill corrido: 287 + 210 + 6.
               Da el MISMO 503 que antes (el titulo solo cambio de lugar
               dentro de la fila, no agrego ancho). */
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
                left: 503px !important;
                max-width: calc(100vw - 503px
                                - (var(--rail-der-res) - 22px)) !important;
            }
        }
        /* ── CUADRO DE CONTROL DE PROVEEDORES (reemplaza la leyenda) ──────
           2026-08-16, 3ra vuelta: dejo de FLOTAR sobre el plot y paso a ser
           una COLUMNA propia a su izquierda (st.columns en proveedor.py).
           Las dos vueltas anteriores lo movieron dentro del grafico —
           primero abajo, despues pegado al borde— hasta que quedo claro que
           el problema no era DONDE flotaba sino QUE flotaba: encima de las
           barras siempre tapa alguna.
           Se van con el flotado todos sus artificios: position/top/left,
           z-index, el ancho fijo de 250px (ahora lo manda la columna), el
           vidrio translucido con saturate y la sombra. Lo que era una
           lamina apoyada sobre el grafico pasa a ser una region de la
           tarjeta, y una region se separa con una LINEA, que ademas es el
           lenguaje plano que ya usa el resto del reporte. */
        /* Titulo del grafico de evolucion (columna derecha). Va como markdown
           y no con `_card(titulo_arriba=)` porque comparte fila con el
           ranking y tiene que quedar a su misma altura, sin la divisoria
           que ese helper dibuja. */
        .cp-evo-tit {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-primary);
            padding-left: 8px;
            margin: 0 0 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        /* "· todo el histórico": avisa que este gráfico NO está mirando el
           mismo rango que el ranking de al lado. Va en el mismo renglón y
           apagado — es una aclaración, no un dato. */
        .cp-evo-tit span {
            font-weight: 400;
            color: var(--text-secondary);
        }
        /* Resumen del ultimo periodo, debajo de la linea. El encabezado dice
           QUE periodo se esta resumiendo: sin eso las cifras no tienen
           contra que leerse. */
        .cp-evo-kpis-tit {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-secondary);
            padding-left: 8px;
            margin: 6px 0 4px;
        }
        /* 2x2 y no una fila de 4: la columna mide ~380px y cuatro celdas en
           linea dejaban ~90px para "S/ 20,711", que se cortaba. */
        .cp-evo-kpis {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            padding-left: 8px;
        }
        .cp-evo-kpis > div {
            display: flex;
            flex-direction: column;
            gap: 1px;
            padding: 5px 8px;
            border-radius: 6px;
            background: color-mix(in srgb, var(--text-secondary) 6%, transparent);
        }
        .cp-evo-kpis span {
            font-size: 10px;
            color: var(--text-secondary);
            line-height: 1.2;
        }
        .cp-evo-kpis b {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
            line-height: 1.25;
            white-space: nowrap;
        }
        /* Scroll horizontal del plot. Solo entra en juego cuando Python le
           forzo un ancho mayor al disponible (ver `_scroll_x` en
           proveedor.py): con muchas series en pocos periodos las barras se
           achicaban hasta ser ilegibles, y ahora se les exige un piso de
           px por barra. Cuando el ancho entra, el figure sigue siendo
           responsive y esta regla no hace nada. */
        .st-key-cp_chart_scroll {
            overflow-x: auto !important;
            overflow-y: hidden !important;
        }
        /* El ancho minimo lo publica Python como variable (`cp-plot-min`,
           ver proveedor.py). Vale 0 cuando todo entra, y ahi esta regla no
           hace nada. Va en el hijo y no en el contenedor: el que scrollea
           tiene que quedarse en el ancho de la columna, y el que se estira
           es su contenido. */
        .st-key-cp_chart_scroll [data-testid="stPlotlyChart"],
        .st-key-cp_chart_scroll [data-testid="stFullScreenFrame"] {
            min-width: var(--cp-plot-min, 0px) !important;
        }
        /* El que TERMINA scrolleando no es el contenedor de arriba sino el
           `stElementContainer` que Streamlit mete adentro — medido: el de
           afuera queda en 829/829 y el de adentro en 829/1676, con 847px de
           recorrido. Por eso el overflow y la barra se declaran tambien en
           el hijo; el de afuera se deja por si esa estructura interna
           cambia en una version futura. */
        .st-key-cp_chart_scroll > [data-testid="stElementContainer"] {
            overflow-x: auto !important;
            overflow-y: hidden !important;
        }
        .st-key-cp_chart_scroll::-webkit-scrollbar,
        .st-key-cp_chart_scroll [data-testid="stElementContainer"]::-webkit-scrollbar {
            height: 8px;
        }
        .st-key-cp_chart_scroll::-webkit-scrollbar-thumb,
        .st-key-cp_chart_scroll [data-testid="stElementContainer"]::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        .st-key-cp_chart_scroll [data-testid="stElementContainer"]::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }
        .st-key-cp_leyenda_float [data-testid="stElementToolbar"] { display: none; }
        /* El boton-titulo se lee como TEXTO clickeable de la tarjeta, no
           como un boton propio: hereda el vidrio del contenedor. `display:
           flex` (block-level) y no el inline-flex de Streamlit — el inline
           deja el hueco de descendente debajo y el texto se ve corrido
           hacia arriba (bug ya diagnosticado en el panel de Ventas). */
        .st-key-cp_leyenda_toggle button {
            width: 100% !important;
            min-width: 0 !important; min-height: 0 !important;
            height: auto !important;
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
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
        .st-key-cp_leyenda_toggle button:hover {
            background: color-mix(in srgb, var(--text-primary) 5%, transparent) !important;
            color: var(--accent-deep) !important;
        }
        .st-key-cp_leyenda_toggle button p {
            font-size: 12px !important; font-weight: 600 !important;
            margin: 0 !important;
        }
        .st-key-cp_leyenda_toggle button [data-testid="stIconMaterial"] {
            font-size: 17px !important;
            color: var(--text-primary) !important;
        }
        .st-key-cp_leyenda_panel {
            padding: 0 0 5px 2px !important;
            gap: 0 !important;
            /* Con "todos los proveedores" por defecto la lista puede ser
               larga; se le pone techo y scroll propio para que el cuadro no
               estire la tarjeta a un alto arbitrario. El techo se ata al
               alto del grafico, no a un px suelto. */
            max-height: 330px !important;
            overflow-y: auto !important;
        }
        /* Cada fila apila nombre y monto (antes eran dos columnas). El
           bloque de la fila no debe meter aire entre esas dos lineas. */
        .st-key-cp_leyenda_panel [class*="st-key-cp_leg_row_"] {
            gap: 0 !important;
            margin-bottom: 4px !important;
        }
        /* SIN esto las filas se PISAN entre si (reportado con captura: el
           monto de una encima del nombre de la siguiente). Streamlit le mete
           `margin-bottom: -16px` al stMarkdownContainer —un negativo del alto
           de su propia linea— y con eso la caja del monto colapsa a height:0:
           medido, el wrapper daba 0px mientras su texto ocupaba 13px, asi que
           la fila solo contaba el boton (16px) y el monto se derramaba sobre
           la fila de abajo. Es EXACTAMENTE el mismo bug que ya documenta
           estilos/_80_cards.py para el panel "Detalle" de Ventas; alla costo
           medir la cadena de padres entera para encontrarlo. */
        .st-key-cp_leyenda_panel [class*="st-key-cp_leg_row_"]
            [data-testid="stMarkdownContainer"] {
            margin-bottom: 0 !important;
        }
        /* Fila = boton con el swatch de color en un ::before. El color entra
           por --cp-leg-color, que Python publica por key (no puede ir inline:
           un pseudo-elemento no acepta style=""). */
        .st-key-cp_leyenda_panel [class*="st-key-cp_leg_row_"] button {
            width: 100% !important;
            min-width: 0 !important; min-height: 0 !important;
            height: auto !important;
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
            gap: 6px !important;
            padding: 1px 2px !important;
            margin: 0 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 3px !important;
            color: var(--text-primary) !important;
            line-height: 1.3 !important;
        }
        .st-key-cp_leyenda_panel [class*="st-key-cp_leg_row_"] button::before {
            content: "";
            flex: 0 0 auto;
            width: 9px; height: 9px;
            border-radius: 2px;
            background: var(--cp-leg-color, var(--text-secondary));
        }
        .st-key-cp_leyenda_panel [class*="st-key-cp_leg_row_"] button p {
            font-size: 11px !important; font-weight: 500 !important;
            margin: 0 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
        }
        .st-key-cp_leyenda_panel [class*="st-key-cp_leg_row_"] button:hover:not(:disabled) {
            background: color-mix(in srgb, var(--text-primary) 6%, transparent) !important;
        }
        /* "Otros" no es un proveedor real: su fila va apagada pero se sigue
           viendo (el swatch gris explica las barras grises del grafico). */
        .st-key-cp_leyenda_panel [class*="st-key-cp_leg_row_"] button:disabled {
            opacity: .75 !important;
            cursor: default !important;
        }
        /* Monto + %: segunda linea de la fila, sangrada para alinearse con
           el NOMBRE y no con el swatch (9px de swatch + 6px de gap = 15px,
           +2px del padding del boton). A la izquierda, no a la derecha:
           apilada bajo el nombre, alinearla a la derecha la dejaba flotando
           lejos del texto al que pertenece. */
        .cp-leg-val {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-primary);
            white-space: nowrap;
            line-height: 1.25;
            padding-left: 17px;
        }
        .cp-leg-val span {
            font-weight: 400;
            color: var(--text-secondary);
            margin-left: 5px;
        }

        /* Variante "outline en tinte" (violeta claro con borde y texto oscuros).
           Contraste bajo: fondo casi blanco con leve tinte, borde tenue. */
        .st-key-prov_pop_float [data-testid="stPopover"] button {
            min-width: 0 !important;
            min-height: 0 !important;
            padding: 2px 10px !important;    /* contenedor un poco más delgado */
            font-size: 11px !important;      /* fuente igual que antes */
            font-weight: 500 !important;
            line-height: 1.35 !important;
            border-radius: 4px !important;   /* cuadrado, no cápsula */
            background: #F7F6FE !important;
            color: #534AB7 !important;
            border: 1px solid #E4E1F5 !important;
            box-shadow: none !important;
            transition: background .12s, border-color .12s !important;
        }
        .st-key-prov_pop_float [data-testid="stPopover"] button:hover {
            background: #DED9FA !important;
            border-color: #7F77DD !important;
        }
        .st-key-prov_pop_float [data-testid="stPopover"] button[aria-expanded="true"] {
            background: #DED9FA !important;
            border-color: #534AB7 !important;
        }
        /* Icono material (grupos) del popover: color acento */
        .st-key-prov_pop_float [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
            color: #7F77DD !important;
            font-size: 14px !important;
            margin-right: 4px !important;
        }
        /* Badge con el numero de proveedores: se inyecta el valor via
           ::after con content dinamico desde Python (ver _cp_badge_count) */
        .st-key-prov_pop_float [data-testid="stPopover"] button
            [data-testid="stMarkdownContainer"] p::after {
            content: var(--cp-prov-count, "");
            background: #534AB7;
            color: #EEEDFE;
            border-radius: 3px;
            padding: 1px 8px;
            font-size: 11px;
            font-weight: 500;
            margin-left: 8px;
            line-height: 1.4;
        }
        .st-key-gran_float [data-testid="stElementToolbar"] { display: none; }
        /* Ocultar la barra de herramientas del propio gráfico (fullscreen).
           Sin `> div >`: el chart vive dentro de cp_chart_wrap (un nivel más
           abajo) y el selector directo dejaba de matchear. */
        .st-key-compras_prov_card_chart [data-testid="stElementToolbar"] { display: none; }
        /* Wrapper del chart: solo existe para animar el alto (ver más abajo).
           Aplanado para no meter aire extra dentro de la tarjeta. */
        .st-key-cp_chart_wrap {
            padding: 0 !important; margin: 0 !important; gap: 0 !important;
        }

        /* Leyenda del gráfico Plotly: totalmente transparente en reposo. Solo
           se hace opaca cuando el cursor pasa DIRECTO sobre la leyenda (no
           al hover de toda la tarjeta). Sigue interactuable porque opacity:0
           conserva pointer-events. */
        .st-key-compras_prov_card_chart .js-plotly-plot .legend {
            opacity: 0.1 !important;
            transition: opacity .22s ease-in-out !important;
        }
        .st-key-compras_prov_card_chart .js-plotly-plot .legend:hover {
            opacity: 1 !important;
        }

        /* Navegacion de ventana: flechas ‹ › + pills de tamano en la misma
           fila, flotando (no suman alto a la tarjeta). El key de un
           container SIN borde ES el stVerticalBlock, por eso la direccion
           FILA se fija aqui directo.
           2026-08-16, a pedido: subio de abajo-derecha (bottom:4px) a la
           MISMA fila que la granularidad Dia/Semana/Mes/Ano, a su
           izquierda. Los tres numeros van acoplados y salen de medir en
           vivo, no a ojo:
             · gran_float esta en right:16px y mide 227px de ancho, asi que
               su borde izquierdo cae a 243px del borde derecho de la
               tarjeta; +12px de aire => right:255px para win_nav.
             · gran_float esta en top:14px y mide 22px de alto (centro a
               25px); win_nav mide 28px, asi que top = 25 - 14 = 11px lo
               deja centrado contra el.
           Si cambian las opciones de granularidad (hoy 4 fijas) cambia su
           ancho y hay que recalcular el right de aca.
           `bottom:auto` es obligatorio: sin el, top Y bottom activos a la
           vez estiran el contenedor de arriba a abajo de la tarjeta.
           Ya no lleva fondo translucido ni blur: eso existia para leerse
           como "chip apoyado" SOBRE el grafico; en la banda superior se
           apoya en el fondo de la tarjeta y el translucido era invisible
           (blanco 55% sobre blanco) pagando el costo de pintado del blur.
           z-index 6 y NO 20 (era 20, reportado: "al hacer scroll se
           superpone a la franja superior"): la franja `fila_ajuste_top` es
           sticky con z-index 20, y la tarjeta que contiene a win_nav no
           crea contexto de apilado propio (position:relative con z-index
           auto), asi que el 20 de win_nav competia DE IGUAL A IGUAL con el
           de la franja — y a igual z-index gana el que va despues en el
           DOM, que es la tarjeta. Al scrollear, la nav de periodos pasaba
           por encima de la franja en vez de por debajo. 6 lo deja sobre el
           grafico y debajo de la franja, alineado con la convencion de sus
           vecinos flotantes (gran_float y prov_pop_float usan 5,
           cp_leyenda_float usa 6). */
        .st-key-win_nav {
            position: absolute; top: 11px; right: 255px; bottom: auto;
            z-index: 6;
            width: auto !important;
            display: flex !important; flex-direction: row !important;
            align-items: center !important;
            gap: 2px !important;
            padding: 1px 2px !important;
            background: transparent !important;
            border-radius: 6px !important;
        }
        /* Banda 641-768px: el `right` de arriba deja de servir porque
           STREAMLIT (no este CSS) ensancha sus pills abajo de 768px —
           padding 12px -> 16px, medido en vivo: gran_float pasa de 227px a
           259px y win_nav se le encimaba 20px. Mismo breakpoint que usa
           estilos/_99_movil.py. El limite inferior es 641px porque de ahi
           para abajo win_nav ya deja de flotar (position:static, mas
           abajo en este archivo) y el right no aplica.
           right = 16 (el de gran_float) + 259 (su ancho aca) + 12 de aire. */
        @media (max-width: 768px) and (min-width: 641px) {
            .st-key-win_nav { right: 287px !important; }
        }
        .st-key-win_nav [data-testid="stElementToolbar"] { display: none; }
        .st-key-win_nav [data-testid="stElementContainer"] { width: auto !important; }
        /* Estilo base compartido: rectangulo con esquinas suaves + sombra
           leve. Mismo alto para flechas y pills → se leen como una sola
           barra homogenea. Compacto verticalmente (18px) para no invadir
           la fila de las etiquetas del eje X. */
        .st-key-win_nav button {
            min-width: 20px !important; width: auto !important;
            height: 17.5px !important;
            min-height: 17.5px !important;
            padding: 0 6px !important;
            border-radius: 4px !important;
            border: 0.5px solid rgba(0,0,0,0.06) !important;
            background: #ffffff !important;
            color: #5a5a6a !important;
            font-size: 10.5px !important; font-weight: 400 !important;
            line-height: 1 !important;
            box-shadow: 0 1px 2px rgba(15,15,30,0.06),
                        0 1px 1px rgba(15,15,30,0.04) !important;
            transition: background .12s, color .12s, box-shadow .12s !important;
        }
        .st-key-win_nav button:hover:not(:disabled) {
            background: #f0edfe !important;
            color: #4d3fb3 !important;
            box-shadow: 0 2px 4px rgba(76,60,180,0.14) !important;
        }
        .st-key-win_nav button:disabled {
            opacity: .35 !important;
            box-shadow: none !important;
        }
        /* Flechas: mas chicas en X, glifo mas grande. */
        .st-key-cp_win_prev button,
        .st-key-cp_win_next button {
            width: 20px !important;
            padding: 0 !important;
            color: #6c5ce7 !important;
            font-size: 12px !important;
        }

        /* Panel A — controles flotantes en la cabecera (Opción 1): DOS flotantes
           absolutos apilados a la derecha — un texto chico con la selección
           (período) ARRIBA y, justo debajo, Ámbito + Top N en una FILA. Al ser
           absolutos no empujan el gráfico. El key de un st.container SIN borde ES
           el stVerticalBlock, por eso la dirección FILA se fija sobre .st-key-...
           directamente (no sobre un bloque anidado). Valores verificados. */
        .st-key-chartcard_prov_prods { position: relative; }
        /* MATAR TODO espacio vertical entre header y gráfico: Streamlit
           inyecta gap en stVerticalBlock + margins en cada stElementContainer
           (uno para el markdown del título, otro para el plotly). */
        .st-key-chartcard_prov_prods,
        .st-key-chartcard_prov_prods [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            row-gap: 0 !important;
        }
        .st-key-chartcard_prov_prods [data-testid="stElementContainer"],
        .st-key-chartcard_prov_prods [data-testid="stMarkdownContainer"],
        .st-key-chartcard_prov_prods [data-testid="stPlotlyChart"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Reducir el padding interior de la card (era 15px por defecto).
           Padding-top mínimo para que el título quede alineado con los
           botones absolutos de la derecha (que están anclados al top). */
        .st-key-chartcard_prov_prods {
            padding: 2px 12px 8px 12px !important;
        }
        /* Tooltip del período: aparece al posar el cursor sobre el botón
           "Selección" (2º botón del primer button group). El valor viene de
           la CSS variable --periodo-selec inyectada desde Python. */
        .st-key-topn_pills > div:first-child [data-testid="stButtonGroup"]
        button:nth-child(2) { position: relative; }
        .st-key-topn_pills > div:first-child [data-testid="stButtonGroup"]
        button:nth-child(2):hover::after {
            content: var(--periodo-selec, "");
            position: absolute; top: calc(100% + 4px); right: 0;
            background: var(--text-primary);
            color: var(--bg-card);
            padding: 4px 8px; border-radius: 4px;
            font-size: 11px; line-height: 1.2; white-space: nowrap;
            z-index: 100; pointer-events: none;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        }
        /* Toggles en la MISMA fila del título, centrados vertical.
           z-index 6 y no 20 por el mismo motivo que win_nav (ver su regla):
           su bloque contenedor no crea contexto de apilado, asi que un 20
           empataba con la franja sticky y ganaba por orden de DOM,
           montandosele encima al scrollear. Aca todavia no se habia
           reportado —el Panel A queda mas abajo, hay que scrollear mas para
           cruzarlo con la franja— pero es el mismo bug latente. */
        .st-key-topn_float {
            position: absolute; top: 0; right: 12px; z-index: 6;
            height: 24px; display: flex; align-items: center;
            width: auto !important;
        }
        .st-key-topn_float > div { width: auto !important; }
        /* Clase DUPLICADA a proposito: `.st-key-chartcard_prov_prods
           [data-testid="stVerticalBlock"] { gap:0 !important }` (mas arriba)
           mata el gap de TODOS los bloques anidados —existe para juntar el
           titulo con el grafico, en vertical— y de paso aplastaba tambien
           esta fila, que es horizontal. Con una sola clase (0,1,0) perdia
           contra esa regla (0,2,0); duplicada empata en especificidad y
           gana por ir despues.
           Medido: el `gap: 6px` que habia aca NUNCA se aplico (computaba
           0px). No se notaba porque cada grupo era una capsula con borde
           propio, que ya marcaba donde terminaba uno y empezaba el otro. Al
           pasar a tabs de texto esa frontera la tiene que dar el aire, y
           con 0 los dos grupos quedaban pegados ("Seleccion" terminaba en
           el mismo pixel donde arrancaba "5"). 20px > los 14px de
           separacion DENTRO de cada grupo, para que se lean como dos
           clusters y no como una lista pareja de cinco opciones. */
        .st-key-topn_pills.st-key-topn_pills {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            gap: 20px !important;
            column-gap: 20px !important;
            width: auto !important;
        }
        .st-key-topn_pills > div { width: auto !important; }
        /* Cabecera compacta: título y controles en una sola línea. Se reduce
           min-height y padding vertical para acercar el gráfico al título. */
        .st-key-chartcard_prov_prods .chart-card-hdr {
            padding: 0 200px 0 4px;
            min-height: 22px;
            margin: 0 !important;
            font-size: 13px;
            line-height: 1.25;
            display: flex;
            align-items: center;
            border-bottom: none;
        }
        .st-key-topn_float [data-testid="stElementToolbar"] { display: none; }
        /* Encoger los botones de los pills (Rango/Selección y 5/10/20). */
        .st-key-topn_float [data-testid="stButtonGroup"] button {
            min-height: 22px !important;
            height: 22px !important;
            padding: 0 8px !important;
            font-size: 11px !important;
            line-height: 1 !important;
        }

        /* Ámbito de fecha (En rango / Todo) — en la cabecera del Panel B.
           Se replican las mismas reglas de compactación del Panel A para
           que titulo, toggles y contenido queden a la misma altura. */
        .st-key-chartcard_prov_prov_de_prod { position: relative; }
        .st-key-chartcard_prov_prov_de_prod,
        .st-key-chartcard_prov_prov_de_prod [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            row-gap: 0 !important;
        }
        .st-key-chartcard_prov_prov_de_prod [data-testid="stElementContainer"],
        .st-key-chartcard_prov_prov_de_prod [data-testid="stMarkdownContainer"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        .st-key-chartcard_prov_prov_de_prod {
            padding: 2px 12px 8px 12px !important;
        }
        .st-key-chartcard_prov_prov_de_prod .chart-card-hdr {
            padding: 0 140px 0 4px;
            min-height: 22px;
            margin: 0 !important;
            font-size: 13px;
            line-height: 1.25;
            display: flex;
            align-items: center;
            border-bottom: none;
        }
        .st-key-panelb_scope_float {
            position: absolute; top: 0; right: 12px; z-index: 5;
            height: 24px; display: flex; align-items: center;
            width: auto !important;
        }
        .st-key-panelb_scope_float > div { width: auto !important; }
        .st-key-panelb_scope_float [data-testid="stElementToolbar"] { display: none; }
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button {
            min-height: 22px !important;
            height: 22px !important;
            padding: 0 8px !important;
            font-size: 11px !important;
            line-height: 1 !important;
        }

        /* ── Cápsula segmentada: unir las pills en un solo control ──
           2026-08-16: la capsula quedo SOLO para `gran_float` (la barra de
           granularidad del grafico, que convive con los chips de win_nav y
           mantiene ese lenguaje). Los dos encabezados de PANEL —topn_float
           (Rango/Seleccion + 5/10/20) y panelb_scope_float (En rango/Todo)—
           salieron de aca a pedido ("que esto no sea toggle, sino que sea
           texto") y pasan a tabs de texto subrayado, mas abajo. */
        .st-key-gran_float [data-testid="stButtonGroup"] {
            gap: 0 !important;
            border: 1px solid rgba(49,51,63,0.2);
            border-radius: 999px;
            overflow: hidden;
            /* Antes: var(--background-color), que NO existe en el :root de
               este proyecto (es un nombre del tema de Streamlit). La
               propiedad quedaba invalida y la capsula salia transparente en
               vez de solida. Sin verificar en local: los datos demo de
               compras.parquet no traen Proveedor/Valor, asi que este drill
               no se puede abrir sin R2. */
            background: var(--bg-card);
        }
        .st-key-gran_float [data-testid="stButtonGroup"] button {
            border: 0 !important;
            border-radius: 0 !important;
            margin: 0 !important;
        }
        .st-key-gran_float [data-testid="stButtonGroup"] button:not(:first-child) {
            border-left: 1px solid rgba(49,51,63,0.15) !important;
        }

        /* ── Encabezados de panel: TABS DE TEXTO, no pastillas ────────────
           Mismo lenguaje que ya usan las franjas de control de Ventas (Por
           dia, Ano Pasado) y Compras > Familia en estilos/_80_cards.py: el
           activo se marca con un subrayado de acento, no con un relleno.
           `[data-selected="true"]` y NO `[aria-pressed="true"]`: los cuatro
           grupos de aca son single-select (st.pills sin selection_mode), y
           Streamlit los marca con role="radio" + data-selected; aria-pressed
           es el marcado de los MULTI-select. Ese error ya costo un selector
           muerto durante varios commits en Ano Pasado (arquitectura.md
           #107, 2do addendum). */
        .st-key-topn_float [data-testid="stButtonGroup"],
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] {
            border: none !important;
            border-radius: 0 !important;
            background: transparent !important;
            overflow: visible !important;
        }
        /* El gap REAL va en el hijo directo del stButtonGroup (que es
           display:block), no en el grupo — mismo hallazgo que en Ventas y
           Familia. Sin capsula que los una, el aire es lo unico que separa
           una opcion de la otra. */
        .st-key-topn_float [data-testid="stButtonGroup"] > div,
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] > div {
            gap: 14px !important;
            flex-wrap: nowrap !important;
        }
        .st-key-topn_float [data-testid="stButtonGroup"] button[data-variant="pills"],
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button[data-variant="pills"] {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            margin: 0 !important;
            padding: 2px 1px !important;
            min-height: 0 !important;
            height: auto !important;
            color: var(--text-secondary) !important;
            font-weight: 400 !important;
            line-height: 1.3 !important;
        }
        .st-key-topn_float [data-testid="stButtonGroup"]
            button[data-variant="pills"][data-selected="true"],
        .st-key-panelb_scope_float [data-testid="stButtonGroup"]
            button[data-variant="pills"][data-selected="true"] {
            border-bottom-color: var(--accent) !important;
            color: var(--accent-deep) !important;
            font-weight: 600 !important;
        }
        .st-key-topn_float [data-testid="stButtonGroup"]
            button[data-variant="pills"]:hover,
        .st-key-panelb_scope_float [data-testid="stButtonGroup"]
            button[data-variant="pills"]:hover {
            color: var(--accent) !important;
        }

        /* ── Panel B: tarjetas por proveedor (reemplaza el st.dataframe) ──
           Reemplaza la tabla de 5 columnas por un stack de tarjetas: swatch
           del color del proveedor (matchea con la barra del chart principal)
           + nombre + total S/, y debajo un grid con las 4 metricas
           (Últ. compra, Precio unit., Cantidad, UM). En mobile el grid pasa a
           2 columnas; en desktop cabe en fila. La tarjeta con el menor precio
           lleva un borde izquierdo verde y el precio en verde. */
        .pb-cards {
            display: flex; flex-direction: column; gap: 6px;
            margin: 4px 0 8px;
        }
        .pb-card {
            background: #fff; border: 0.5px solid #e6e6ea;
            border-left: 3px solid transparent;
            border-radius: 6px; padding: 7px 10px;
        }
        .pb-card.is-min { border-left-color: #15803d; }
        .pb-card .line1 {
            display: flex; align-items: center; gap: 6px; margin-bottom: 4px;
        }
        .pb-card .sw {
            width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0;
        }
        .pb-card .name {
            flex: 1; min-width: 0;
            color: #18181d; font-size: 12px; font-weight: 500;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .pb-card .total {
            color: #534AB7; font-size: 11.5px; font-weight: 500;
            font-variant-numeric: tabular-nums; flex-shrink: 0;
        }
        .pb-card .grid {
            display: grid; grid-template-columns: repeat(4, 1fr);
            gap: 4px 10px; font-size: 11px;
        }
        .pb-card .cell {
            display: flex; align-items: baseline; gap: 5px; min-width: 0;
        }
        .pb-card .cell .lab {
            color: #a2a2ad; text-transform: uppercase;
            letter-spacing: 0.03em; font-size: 9.5px; flex-shrink: 0;
        }
        .pb-card .cell .val {
            color: #18181d; font-variant-numeric: tabular-nums;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .pb-card .pu { font-weight: 500; }
        .pb-card .pu.pu-min { color: #15803d; font-weight: 600; }
        /* Grid a 2 columnas en anchos chicos: cuando la card mide <= 380px
           (mockup mobile). Container query, con fallback por ancho de
           viewport para navegadores sin soporte. */
        @container (max-width: 380px) {
            .pb-card .grid { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 900px) {
            .pb-card .grid { grid-template-columns: 1fr 1fr; }
        }

        /* ── TARJETAS COLAPSABLES: animacion unfold (drill Proveedor) ──
           IMPORTANTE: NO usar scaleX/scaleY/rotate en el contenedor. Al
           remontar plotly/aggrid/dataframe con key nueva, esos componentes
           miden el ancho durante la animacion; si el transform reduce el
           tamano visual, el getBoundingClientRect devuelve ~0 y el
           componente renderiza con columnas/chart colapsados. Usamos solo
           opacity + translate para que el ancho real del contenedor
           permanezca intacto durante toda la animacion. */
        @keyframes unfoldDown {
            0%   { opacity: 0; transform: translateY(-8px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        /* La animacion se aplica DIRECTO a la tarjeta por su key estable.
           Streamlit reutiliza el nodo DOM mientras sigue abierta, asi que el
           unfold solo corre al montarse (oculta->visible), no en cada rerun.
           fill-mode backwards: arranca invisible y al terminar no deja
           transform residual. NO usamos <script> porque st.markdown NO
           ejecuta JS. */
        /* Bloque docs: se despliega hacia ABAJO. */
        .st-key-compras_prov_card_docs {
            animation: unfoldDown 0.32s cubic-bezier(0.4, 0, 0.2, 1) backwards;
        }
        /* Bloque paneles: entra deslizando desde la izquierda al enfocar. */
        @keyframes unfoldRight {
            0%   { opacity: 0; transform: translateX(-14px); }
            100% { opacity: 1; transform: translateX(0); }
        }
        .st-key-compras_prov_card_paneles {
            animation: unfoldRight 0.32s cubic-bezier(0.4, 0, 0.2, 1) backwards;
        }
        /* ── PESTILLO como PILL: solo queda el de "Detalle de documentos por
           proveedor" (latch_docs). El boton ES el titulo: clic en cualquier
           parte del pill abre/cierra. El icono (carrete SVG) va como
           background-image en ::before, a la izquierda del label, y gira
           180deg cuando el bloque esta abierto (rotacion inyectada desde
           Python con <style>). El detalle A/B ya no tiene pestillo ni boton
           de cerrar: lo abre y lo cierra el clic en la barra. */
        .st-key-docs_row {
            margin: 8px 0 6px;
        }
        /* El detalle A/B va PEGADO al chart (es su continuacion, no un bloque
           aparte). El margen negativo se come parte del gap de 1rem que el
           bloque vertical de Streamlit mete entre hermanos. */
        .st-key-paneles_row {
            margin: -10px 0 6px !important;
        }
        .st-key-latch_docs {
            width: auto !important;
            margin: 0 0 8px 0 !important;
            display: inline-block;
        }
        .st-key-latch_docs button {
            display: inline-flex !important;
            align-items: center; justify-content: flex-start;
            gap: 8px !important;
            width: auto !important; min-width: 0 !important;
            height: auto !important; min-height: 0 !important;
            padding: 6px 16px 6px 10px !important;
            margin: 0 !important;
            border: 0.5px solid #d4cdf7 !important;
            border-radius: 999px !important;
            background: #f0edfe !important; box-shadow: none !important;
            cursor: pointer !important;
            transition: background .15s, border-color .15s !important;
        }
        .st-key-latch_docs button:hover {
            background: #e5e0fc !important;
            border-color: #b9adf1 !important;
        }
        .st-key-latch_docs button:focus,
        .st-key-latch_docs button:active {
            outline: none !important; box-shadow: none !important;
        }
        /* Label del boton (el <p> que Streamlit inserta): tipografia del titulo. */
        .st-key-latch_docs button p {
            display: inline !important;
            font-size: 13px !important; font-weight: 500 !important;
            line-height: 1 !important;
            color: #4d3fb3 !important;
            margin: 0 !important; padding: 0 !important;
        }
        /* Icono de carrete: solo el pestillo de documentos (la X del detalle
           A/B no lo lleva). */
        .st-key-latch_docs button::before {
            content: ""; display: inline-block;
            width: 16px; height: 16px; flex-shrink: 0;
            background: center / contain no-repeat
                url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 22 22' fill='none'><circle cx='11' cy='11' r='3' fill='%236c5ce7'/><ellipse cx='11' cy='4' rx='5' ry='2.5' fill='%236c5ce7' opacity='.85'/><ellipse cx='11' cy='18' rx='5' ry='2.5' fill='%236c5ce7' opacity='.85'/><rect x='8' y='4' width='6' height='14' fill='%236c5ce7' opacity='.45' rx='1'/><line x1='11' y1='4' x2='11' y2='18' stroke='%23ffffff' stroke-width='1' opacity='.4'/><line x1='11' y1='4' x2='6.5' y2='3' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='4' x2='15.5' y2='3' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='18' x2='6.5' y2='19' stroke='%23ffffff' stroke-width='.8' opacity='.5'/><line x1='11' y1='18' x2='15.5' y2='19' stroke='%23ffffff' stroke-width='.8' opacity='.5'/></svg>");
            transition: transform .55s cubic-bezier(.4, 0, .2, 1);
        }

        /* ══════════════════════════════════════════════════════════════
           MÓVIL: los controles flotantes de este drill son position:absolute
           sobre las tarjetas — pensados para desktop. En viewport angosto se
           enciman con el título de su tarjeta o desbordan el ancho. Se sacan
           del posicionamiento absoluto y fluyen como una fila propia bajo el
           título/gráfico. Nada se encima; a cambio la tarjeta crece un poco
           en alto, barato en móvil.
           ── Dos breakpoints, por qué distintos:
           · Paneles A/B viven en st.columns(2), que colapsa a 1 columna recién
             por debajo de ~640px. ENTRE 640 y 900px cada panel es media
             pantalla y su título + los 5 pills ya no caben en la cabecera →
             el fix de topn_float/panelb_scope_float aplica desde 900px.
           · El gráfico principal (y su win_nav / floats de tope) es de ancho
             completo: solo se aprieta de verdad por debajo de ~640px.
           ══════════════════════════════════════════════════════════════ */
        @media (max-width: 900px) {
            /* Panel A: Rango/Selección + 5/10/20 — bajo el título.
               Panel B: En rango/Todo — bajo el título. */
            .st-key-topn_float,
            .st-key-panelb_scope_float {
                position: static !important;
                height: auto !important;
                width: 100% !important;
                margin: 2px 0 6px !important;
                justify-content: flex-start !important;
            }
        }
        @media (max-width: 640px) {
            /* Navegación de periodos: fluye bajo el gráfico y puede envolver
               en dos filas en vez de cortarse. */
            .st-key-win_nav {
                position: static !important;
                width: 100% !important;
                margin: 4px 0 0 0 !important;
                flex-wrap: wrap !important;
                justify-content: flex-start !important;
            }
            /* Controles del tope del gráfico. En desktop flotan absolutos
               sobre la esquina del plot (Proveedores a la izq., pills de
               periodo a la der.); en 375px sus anchos se cruzan y se solapan.
               En móvil dejan de flotar y fluyen como fila de controles ARRIBA
               del gráfico, apilados: Proveedores en su línea, y la
               granularidad como segmentado a ancho completo (4 segmentos
               iguales = tap targets grandes). Nada se encima; el plot baja un
               poco, que en móvil es barato. */
            .st-key-prov_pop_float,
            .st-key-gran_float {
                position: static !important;
                top: auto !important; left: auto !important; right: auto !important;
                width: 100% !important;
                margin: 0 0 6px 0 !important;
            }
            /* Granularidad Día/Semana/Mes/Año a ancho completo, segmentos que
               se reparten el ancho por igual. */
            .st-key-gran_float [data-testid="stButtonGroup"] {
                width: 100% !important;
                display: flex !important;
            }
            .st-key-gran_float [data-testid="stButtonGroup"] button {
                flex: 1 1 0 !important;
                min-width: 0 !important;
            }
        }
        </style>
"""
