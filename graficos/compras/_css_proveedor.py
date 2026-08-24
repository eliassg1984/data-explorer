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
        .st-key-compras_prov_marco { position: relative; }
        /* El marco RESERVA arriba la banda donde flota el ÚNICO flotante que
           le queda (el popover de Proveedores) — hasta el 2026-08-23 también
           flotaban acá `gran_float` y `win_nav`, mudados adentro de la
           tarjeta de Evolución a pedido (ver ese bloque, más abajo en este
           archivo). Con un solo flotante más bajo que antes, este
           padding-top probablemente pueda bajar de 16px, pero se deja igual
           hasta remedir en vivo — de más no rompe nada, solo deja algo de
           aire de sobra. */
        .st-key-compras_prov_marco { padding-top: 16px !important; }
        /* 2026-08-23: `gran_float` DEJÓ de flotar acá — se mudó DENTRO de la
           tarjeta de Evolución (compras_prov_card_evo), a pedido ("que no
           estén arriba de Evolución sino dentro"). El nombre de la key se
           mantiene (mismo criterio que --rail-der-* tras el flip de lado).
           Más tarde el mismo día dejó de ser pills: hoy es un `st.selectbox`
           aplanado a texto, compartiendo renglón con `cp_evo_periodo` dentro
           de `cp_evo_ctrl` (ver ese bloque, más abajo, que es el que le da
           el ancho y el aspecto). Acá queda sólo el aplanado del cromo que
           Streamlit mete alrededor. */
        .st-key-gran_float {
            /* Aplanar todo lo que Streamlit mete arriba del widget (label
               oculto, padding del stElementContainer). Sin esto el control
               queda ~14px más abajo que su vecino de renglón.
               OJO: acá había además un `line-height: 0`, que sobre las pills
               era inofensivo pero le rompe el alto al `<input>` del
               selectbox — se sacó al hacer el cambio, no volver a ponerlo. */
            padding: 0 !important; margin: 0 !important;
        }
        .st-key-gran_float [data-testid="stElementContainer"],
        .st-key-gran_float [data-testid="stElementContainer"] > div,
        .st-key-gran_float [data-testid="stVerticalBlock"] {
            padding: 0 !important; margin: 0 !important; gap: 0 !important;
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
               301 (left de los chips) + 492 (su ancho: 230*2 + 32 de gaps)
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
                top: calc(var(--nav-top-alto) + 8px) !important;
                left: auto !important;
                bottom: auto !important;
                /* Era `calc(var(--rail-der-res) + 10px)`: se derivaba del
                   rail para seguirlo al plegarse. Con el rail a la IZQUIERDA
                   (2026-08-18) esa variable dejó de decir nada sobre este
                   borde — y el borde derecho ya no se mueve cuando el rail se
                   pliega, así que tampoco hace falta que lo siga.
                   90 = 80 de padding del contenedor + 10 de BARRA DE SCROLL.
                   Los 10 no son un fudge: este elemento es `position: fixed`,
                   así que se posiciona contra el VIEWPORT (1440 medido),
                   mientras que la tarjeta con la que alinea vive dentro del
                   contenedor, que mide lo que queda descontada la barra
                   (1430). Sin ese sumando el pill sobresale exactamente el
                   ancho de la barra. Si algún día se saca el scroll de
                   página, este número vuelve a 80. */
                right: 90px !important;
                z-index: 23 !important;
            }
        }
        /* Nombre de la vista ("Proveedor") PRIMERO en la franja, pegado a
           la izquierda y ANTES del pill de fecha — igual que en Compras >
           Familia (2da vuelta: nacio a la derecha del pill y se movio a
           pedido). El pill y los chips se corren para hacerle sitio.
           Cadena de numeros acoplada, medida en vivo:
              85 = el left original del pill -> ahi va ahora el titulo.
             100 = ancho reservado para la palabra "Proveedor" a 14px/700.
             197 = 85 + 100 + 12 de aire -> nuevo left del PILL.
             413 = 197 + 210 (ancho fijo del pill) + 6 -> left de los chips.
           2026-08-18: la cadena entera bajo 90px al retirarse el rail
           izquierdo (hoy franja superior). Los umbrales de @media NO se
           tocaron: son anchos de viewport, no coordenadas.
           Mover uno descoloca la fila entera. Ojo: el 503 de los chips es
           el MISMO que cuando el titulo estaba a la derecha del pill — el
           ancho total ocupado no cambia, solo el orden — asi que el umbral
           de abajo tampoco se movio:
             413 + 492 (chips) + 12 + 165 (prov_pop) + 163 = 1245, pero el
             umbral se DEJA en 1340: bajarlo es una decision de diseno
             aparte (mas ancho util no significa que el titulo se lea bien)
             y este cambio no la toma.
           Los DOS bloques (este y el de prov_pop_float) tienen que entrar
           o salir juntos, si no el titulo se superpondria con unos chips
           que no se corrieron: por eso el `right` de prov_pop_float se
           repite aca, para que en la banda 1230-1339 (titulo oculto, pill
           y chips sin correr) siga con su propia cuenta, que ahi da. */
        .st-key-compras_prov_titulo_franja {
            position: fixed !important;
            top: calc(var(--nav-top-alto) + 8px) !important;
            left: var(--rail-der-res) !important;   /* ancla comun de la franja */
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
                left: calc(var(--rail-der-res) + 112px) !important;
            }
            /* Los chips arrancan despues del pill corrido: 197 + 210 + 6.
               Da el MISMO 413 que antes (el titulo solo cambio de lugar
               dentro de la fila, no agrego ancho). */
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
                left: calc(var(--rail-der-res) + 328px) !important;
                max-width: calc(100vw - (var(--rail-der-res) + 328px)
                                - 58px) !important;
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
            padding-left: 0;
            /* Sin margen superior: la columna arranca a la misma altura que
               el gráfico de al lado, no 6px más abajo. */
            margin: 0 0 4px;
        }
        /* 2026-08-19: de 2x2 a UNA columna. El resumen dejó de ir debajo
           del gráfico y pasó a su costado (proveedor.py), así que ahora tiene
           ~130px de ancho y todo el alto: cuatro cifras apiladas se leen de un
           barrido vertical, sin el zigzag del 2x2.
           El motivo del 2x2 ya no aplica —era que cuatro celdas EN LINEA
           dejaban ~90px para "S/ 20,711" y se cortaba—: apiladas, cada una
           tiene la columna entera. `white-space: nowrap` en el <b> sigue
           siendo la red por si una cifra crece. */
        .cp-evo-kpis {
            display: grid;
            grid-template-columns: 1fr;
            gap: 6px;
            padding-left: 0;
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
        /* Título sobre la tabla-ranking (columna izquierda). Mismo lenguaje
           que `.cp-evo-tit` de al lado (markdown, no `_card(titulo_arriba=)`
           — ese helper dibuja una divisoria que acá no hace falta). */
        .cp-rank-tit {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-primary);
            padding-left: 2px;
            margin: 0 0 4px;
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
        .st-key-compras_prov_marco [data-testid="stElementToolbar"] { display: none; }
        /* Aplanado para no meter aire extra dentro de la tarjeta. */
        .st-key-cp_chart_wrap {
            padding: 0 !important; margin: 0 !important; gap: 0 !important;
        }
        /* min-width por columna (ranking-tabla / evolución, ver
           proveedor.py). Sin esto, `flex-wrap: wrap` (default de Streamlit
           en stHorizontalBlock) las deja apretarse hasta ilegibles ANTES
           de apilarlas — medido en vivo con el layout de 3 columnas que
           hubo antes de unir ranking+tabla (2026-08-17): a 800-850px de
           viewport quedaban en ~186-200px. 300px es el piso para que se
           lean bien; por debajo, mejor apiladas a ancho completo (más
           alto, pero legible) que apretadas. */
        .st-key-cp_chart_wrap [data-testid="stColumn"] {
            min-width: 300px !important;
        }
        /* ...pero ese selector es DESCENDIENTE, así que captura también las
           columnas que se agreguen ADENTRO de los dos bloques. Al partir la
           evolución en gráfico + resumen (2026-08-19) las dos columnas nuevas
           heredaron el piso de 300px: 600 de mínimo en 378 disponibles → el
           `flex-wrap` de Streamlit las apiló y el resumen volvió a quedar
           DEBAJO del gráfico, que es justo lo que el cambio venía a evitar.
           No se vio como un error: se vio como "el cambio no hizo nada".
           Es el caso que documenta CLAUDE.md (§ "antes de agregar un widget
           dentro de una tarjeta, grep estilos/"), en su versión CSS.
           El piso de 300 es para las columnas de PRIMER nivel (ranking vs
           evolución); adentro de un bloque no aplica. Va después para ganar
           por orden: misma especificidad, ambas con !important. */
        .st-key-compras_prov_card_evo [data-testid="stColumn"],
        .st-key-compras_prov_card_ranking [data-testid="stColumn"] {
            min-width: 0 !important;
        }

        /* Navegacion de ventana: flechas ‹ › + pills de tamano en una fila.
           El key de un container SIN borde ES el stVerticalBlock, por eso
           la direccion FILA se fija aqui directo.
           2026-08-23: dejó de flotar sobre `compras_prov_marco` — se mudó
           DENTRO de la tarjeta de Evolución, debajo de `gran_float`, a
           pedido ("que no estén arriba de Evolución sino dentro"). Toda la
           coordinación de `top`/`right` contra `gran_float` y contra la
           franja sticky (que existía porque los dos flotaban con
           `position:absolute` sobre el mismo marco) dejó de aplicar: en
           flujo normal, dentro de su propia tarjeta, no hay nada que
           coordinar. El nombre de la key se mantiene (mismo criterio que
           --rail-der-* tras el flip de lado). */
        .st-key-win_nav {
            width: auto !important;
            display: flex !important; flex-direction: row !important;
            align-items: center !important;
            gap: 2px !important;
            padding: 1px 2px !important;
            margin: 0 0 8px !important;
            background: transparent !important;
            border-radius: 6px !important;
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
        /* 2026-08-23, a pedido ("agregalos de manera minimalista dentro
           de la tarjeta"): atajos de fecha (Esta semana/Este mes/Últimos
           30 días/Este año) dentro de la tarjeta de Ranking — mismo
           lenguaje visual que win_nav (chips chicos, sombra leve, sin
           estado "activo" — el original de franja_fecha.py tampoco lo
           marca) para leerse como de la misma familia de controles. */
        .st-key-compras_prov_rank_atajos {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
            margin: 2px 0 10px !important;
        }
        .st-key-compras_prov_rank_atajos [data-testid="stElementContainer"] {
            width: auto !important;
        }
        .st-key-compras_prov_rank_atajos [data-testid="stElementToolbar"] {
            display: none;
        }
        .st-key-compras_prov_rank_atajos button {
            min-width: 0 !important;
            height: 22px !important;
            min-height: 22px !important;
            padding: 0 10px !important;
            border-radius: 999px !important;
            border: 0.5px solid rgba(0,0,0,0.08) !important;
            background: #ffffff !important;
            color: #5a5a6a !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            line-height: 1 !important;
            box-shadow: 0 1px 2px rgba(15,15,30,0.06) !important;
            transition: background .12s, color .12s !important;
        }
        .st-key-compras_prov_rank_atajos button:hover {
            background: #f0edfe !important;
            color: #4d3fb3 !important;
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

        /* 2026-08-23 (3): acá vivía la "cápsula segmentada" que unía las
           pills de `gran_float` en un solo control con forma de píldora.
           Se fue entera cuando la granularidad pasó a `st.selectbox`: ya no
           hay ButtonGroup que encapsular. Su aspecto de hoy lo fija el
           bloque `cp_evo_ctrl`, más abajo. */

        /* ── Encabezados de panel: TABS DE TEXTO, no pastillas ────────────
           Mismo lenguaje que ya usan las franjas de control de Ventas (Por
           dia, Ano Pasado) y Compras > Familia en estilos/_80_cards.py: el
           activo se marca con un subrayado de acento, no con un relleno.
           `[data-selected="true"]` y NO `[aria-pressed="true"]`: los dos
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

        /* ── Controles de tiempo de la EVOLUCIÓN: UNA sola línea ──────────
           2026-08-23 (3), a pedido ("que sea una lista desplegable, pero
           minimalista... y que esté en una línea, no una debajo de otra"):
           `cp_evo_periodo` (la ventana, graficos/periodo.py) y `gran_float`
           (la granularidad) eran DOS filas de pills apiladas; pasan a dos
           `st.selectbox` aplanados a TEXTO, compartiendo un renglón.

           El alto total de la fila está presupuestado en
           `alturas.FRANJA_CTRL_EVO` y la figura de al lado ya se lo restó:
           si se le agrega aire acá, hay que cambiar esa constante o la
           tarjeta empuja su borde.

           Por qué un flex y no `st.columns`: la proporción de las columnas
           de un drill sale de `COLUMNAS_DRILL` (CLAUDE.md), y esto es una
           subdivisión DENTRO de una tarjeta. Mismo recurso que `win_nav` un
           renglón más abajo — el key de un container SIN borde ES el
           stVerticalBlock, así que la dirección FILA se fija acá directo. */
        .st-key-cp_evo_ctrl {
            display: flex !important; flex-direction: row !important;
            align-items: center !important;
            gap: 8px !important;
            width: auto !important;
            margin: 0 0 6px !important; padding: 0 !important;
        }
        /* OJO con el `>`: `cp_evo_periodo` SÍ es hijo directo del flex (es un
           stElementContainer), pero `gran_float` NO — al ser un container
           anidado, Streamlit le mete un `stLayoutWrapper` en el medio. Un
           `> .st-key-gran_float` no matchea nada y el control se estira a
           todo el espacio libre (medido: 171px en vez de 104). */
        .st-key-cp_evo_ctrl > .st-key-cp_evo_periodo,
        .st-key-cp_evo_ctrl > [data-testid="stLayoutWrapper"] {
            flex: 0 0 auto !important;
            margin: 0 !important; padding: 0 !important;
        }
        .st-key-cp_evo_ctrl > [data-testid="stLayoutWrapper"] {
            width: auto !important;
        }
        /* La CAJA del selectbox (borde 1px + fondo + 40px de alto) no la
           lleva ni el `stSelectbox` ni el `input`, sino el `div[role=group]`
           que hay entre los dos — misma receta, mismo hallazgo medido en el
           navegador, que los dos selectores de Documentos SUNAT en
           estilos/_30_filtros.py. Estilar el ancestro no alcanza. */
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] div[role="group"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            min-height: 0 !important;
        }
        /* El alto lo fija el `input` (los 40px de la altura de control de
           Streamlit), no el grupo — bajarlo ahí es lo que convierte la caja
           en una línea de texto. */
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] input,
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] div[role="group"],
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] .react-aria-ComboBox {
            height: 24px !important;
            min-height: 0 !important;
        }
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] input {
            padding: 0 !important;
            height: auto !important;
            /* 11px y no 12: al entrar el TERCER desplegable (ver abajo) los
               textos a 12px sumaban ~289px en una fila de 279.5. Además es
               la escala real de esta tarjeta — el título es 11px y las
               flechas 10.5. Los 12px eran el número raro. */
            font-size: 11px !important;
            font-weight: 600 !important;
            color: var(--text-primary) !important;
            cursor: pointer !important;
            text-overflow: ellipsis !important;
        }
        /* El chevron se CONSERVA, y en acento: sin ninguna affordance un
           texto que despliega una lista no se distingue de una etiqueta
           muerta (misma decisión que en Documentos SUNAT). Es lo único que
           dice "esto se puede tocar" ahora que no hay caja ni pastilla. */
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] svg {
            width: 14px !important; height: 14px !important;
            fill: var(--accent) !important;
            color: var(--accent) !important;
        }
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"]:hover input {
            color: var(--accent-deep) !important;
        }
        /* El botón ✕ "Clear value" aparece SOLO en el selector de cuántos
           períodos, y no por capricho: su lista incluye `None` (la opción
           "Auto"), y con un `None` entre las opciones Streamlit considera al
           widget vaciable. Acá esa ✕ es redundante —vaciarlo deja `None`,
           que es exactamente "Auto", una opción que ya está en la lista— y
           encima cobraba caro: entre la ✕ (24px) y el chevron (26px) le
           dejaban 14px al texto en un control de 64, así que "Auto 4" salía
           cortado (medido). Fuera.

           Y el botón del chevron se achica: 26px de ancho para un ícono de
           14 son ~10px de padding que en esta fila no sobran. Se identifican
           por `aria-label`/`aria-haspopup` y NO por su clase: las de emotion
           cambian entre builds (regla vieja de este proyecto). */
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"]
            button[aria-label="Clear value"] {
            display: none !important;
        }
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] button[aria-haspopup] {
            width: 16px !important;
            min-width: 0 !important;
            padding: 0 !important;
            flex: 0 0 auto !important;
        }
        /* Anchos EXPLÍCITOS, uno por control. Un input de react-aria no se
           auto-dimensiona: sin esto pide el 100% del contenedor y el chevron
           termina contra el borde derecho de la tarjeta, a ~300px de su
           propio texto (el `width: auto` que ya tenía `gran_float` le ganaba
           al 100% en el contenedor, pero no en el input). Están medidos
           sobre la opción MÁS LARGA de cada lista — "Rango", "Por semana" y
           "Todo NN"/"Auto NN"; si se agregan opciones, revisarlos.

           El presupuesto HORIZONTAL de la fila, medido con `measureText` a
           11px/600 sobre 279.5px de ancho útil:
               56 (ventana) + 84 (grano) + 64 (cuántos) + ~46 (flechas)
             + 3 huecos de 8  =  ~274.
           Queda poco margen a propósito: es lo que costó meter las tres
           filas de controles en una. Si algo tiene que crecer, primero
           medir de nuevo — con el emoji 📅 en la primera opción ya NO
           entraba (se pasaba ~18px, por eso se fue). */
        .st-key-cp_evo_ctrl > .st-key-cp_evo_periodo { width: 56px !important; }
        .st-key-cp_evo_ctrl .st-key-gran_float { width: 84px !important; }
        .st-key-cp_evo_ctrl .st-key-win_size { width: 64px !important; }
        .st-key-cp_evo_ctrl [data-testid="stSelectbox"] { width: 100% !important; }
        /* Las flechas ‹ › entran al renglón compartido: pierden el margen
           inferior que tenían cuando eran una fila propia, y se pegan al
           final de la línea. Todo su ASPECTO (tamaño, sombra, hover) sigue
           saliendo del bloque `.st-key-win_nav` de más arriba — acá sólo se
           corrige lo que cambió al mudarse. */
        .st-key-cp_evo_ctrl .st-key-win_nav {
            margin: 0 !important;
            flex: 0 0 auto !important;
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
        /* 2026-08-21: eran UNA tarjeta (`compras_prov_card_paneles`) y pasaron
           a ser DOS bloques hermanos, uno por columna, para que caigan sobre
           la misma grilla que la fila de arriba. La animación se aplica a los
           dos: entran juntos, que es lo que hacía la tarjeta única. */
        .st-key-compras_prov_card_prods,
        .st-key-compras_prov_card_provde {
            animation: unfoldRight 0.32s cubic-bezier(0.4, 0, 0.2, 1) backwards;
        }
        /* 2026-08-21: acá vivía el PESTILLO del detalle de documentos
           (`latch_docs`): un pill donde el botón ERA el título y un icono de
           carrete en ::before que giraba 180deg al abrir. La tabla pasó a
           estar siempre visible, así que se fue el botón y con él sus ~55
           líneas de CSS. Lo que queda es sólo la separación del bloque. */
        .st-key-docs_row {
            margin: 8px 0 6px;
        }
        /* El detalle A/B va PEGADO al chart (es su continuacion, no un bloque
           aparte). El margen negativo se come parte del gap de 1rem que el
           bloque vertical de Streamlit mete entre hermanos. */
        .st-key-paneles_row {
            margin: -10px 0 6px !important;
        }

        /* ══════════════════════════════════════════════════════════════
           MÓVIL: los controles flotantes de este drill son position:absolute
           sobre las tarjetas — pensados para desktop. En viewport angosto se
           enciman con el título de su tarjeta o desbordan el ancho. Se sacan
           del posicionamiento absoluto y fluyen como una fila propia bajo el
           título/gráfico. Nada se encima; a cambio la tarjeta crece un poco
           en alto, barato en móvil.
           ── Dos breakpoints, por qué distintos:
           · Paneles A/B viven en `st.columns(COLUMNAS_DRILL)`, que colapsa a
             1 columna recién por debajo de ~640px. ENTRE 640 y 900px cada
             panel es media pantalla y su título + los 5 pills ya no caben en
             la cabecera → el fix de topn_float/panelb_scope_float aplica
             desde 900px.
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
            /* Navegación de periodos: ya vive en flujo normal (2026-08-23,
               dentro de la tarjeta de Evolución — ver más arriba), así que
               acá solo queda el ancho completo + wrap para que quepa en una
               pantalla angosta, sin el `position:static` que hacía falta
               cuando todavía flotaba. */
            .st-key-win_nav {
                width: 100% !important;
                margin: 4px 0 0 0 !important;
                flex-wrap: wrap !important;
                justify-content: flex-start !important;
            }
            /* Popover de Proveedores: en desktop flota absoluto sobre la
               esquina del plot; en 375px su ancho se cruzaba con el resto.
               En móvil deja de flotar y fluye como fila de controles ARRIBA
               del gráfico. */
            .st-key-prov_pop_float {
                position: static !important;
                top: auto !important; left: auto !important; right: auto !important;
                width: 100% !important;
                margin: 0 0 6px 0 !important;
            }
            /* Los tres selectores de tiempo + las flechas: en 375px la
               tarjeta tiene 291px de ancho útil y los anchos de desktop
               suman ~274, así que ENTRAN tal cual — no hace falta
               repartirlos. Hubo una vuelta con `flex: 1 1 0` (tercios
               iguales) cuando eran dos controles; con tres deja 57px de
               texto y "Por semana" (64px a 11px/600, medido) salía cortado.
               Lo único que cambia en móvil es el alto: 24px es cómodo con
               mouse, no con el dedo. */
            .st-key-cp_evo_ctrl {
                width: 100% !important;
            }
            .st-key-cp_evo_ctrl [data-testid="stSelectbox"] input,
            .st-key-cp_evo_ctrl [data-testid="stSelectbox"] div[role="group"],
            .st-key-cp_evo_ctrl [data-testid="stSelectbox"] .react-aria-ComboBox {
                height: 32px !important;
            }
        }

        /* 2026-08-23, a pedido ("eliminemos el widget de fecha... que ya
           no sea visible"): el pill de fecha de la franja superior
           (fecha_ajuste_pill, franja_fecha.py) se oculta SOLO en este
           drill — este bloque se inyecta nada más que cuando el drill de
           Proveedor se dibuja (ver el docstring del módulo), así que en
           cualquier otra vista/pestaña de Compras el pill sigue como
           siempre. Se oculta con CSS, no se deja de LLAMAR
           `franja_fecha.render()`: el date_input de adentro es el DUEÑO
           del rango (su key ES la clave canónica), y un widget que deja
           de renderizarse pierde su estado (CLAUDE.md § Streamlit). El
           rango se sigue pudiendo cambiar desde cualquier otra vista. */
        .st-key-fecha_ajuste_pill { display: none !important; }

        /* 2026-08-23 (2), a pedido ("que sea como el segundo" — o sea con
           clic, como un popover, no el help= hover-only del primer
           intento): ícono de ayuda de Ranking de proveedores, discreto
           hasta que se busca — mismo espíritu que .st-key-rail_pestillo
           button (estilos/_25_rails_pestillo.py). Acotado a SU propia key
           (CLAUDE.md: estilar el widget puntual, no el contenedor). */
        .st-key-compras_prov_rank_ayuda button {
            min-width: 0 !important;
            min-height: 0 !important;
            padding: 2px !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            color: var(--text-muted) !important;
            /* Sin esto el line-height default (24px) infla el boton por
               encima del icono de 16px y lo descentra ~5px contra el
               titulo (medido en vivo). */
            line-height: 1 !important;
        }
        .st-key-compras_prov_rank_ayuda button:hover {
            background: var(--accent-tint) !important;
            color: var(--accent-deep) !important;
        }
        .st-key-compras_prov_rank_ayuda [data-testid="stIconMaterial"] {
            font-size: 16px !important;
        }
        /* Fila título + ícono: st.columns por defecto alinea arriba, y el
           botón (más alto que el texto de 16px del título) queda pegado
           al techo de su columna en vez de centrado contra el texto. */
        .st-key-compras_prov_card_ranking [data-testid="stHorizontalBlock"] {
            align-items: center !important;
        }
        </style>
"""
