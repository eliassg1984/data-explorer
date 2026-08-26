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
                /* FILA 1, con Familia/Subfamilia (2026-08-25, a pedido).
                   Estaba en `calc(var(--nav-top-alto) + 8px)`, que era la
                   banda de filtros hasta que la franja de VISTAS se mudo
                   ahi (`navegacion.py`): desde entonces compartia renglon
                   con las pestanas. Los 7px son los mismos que usan los
                   chips (`_40_ajuste_franja.py`), no un numero suelto. */
                top: 7px !important;
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
            /* Ver la nota de `.cp-rank-tit`: se mueven juntas. */
            font-size: 16px;
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
            /* 16px (2026-08-25, a pedido, probado antes en el modo
               diseno). Las tres clases hermanas —`cp-rank-tit`,
               `cp-evo-tit` y `cp-prod-rank-tit`— se mueven JUNTAS:
               comparten lenguaje visual a proposito (ver sus
               comentarios) y dos de ellas se leen lado a lado en la
               misma fila, asi que una sola en 16 se veria como un
               error. */
            font-size: 16px;
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

        /* 2026-08-26, a pedido ("hagamos el filtro de proveedores, similar
           a los de familia y subfamilia, visualmente"): este chip nació con
           su propia paleta hardcodeada (#F7F6FE/#534AB7/#E4E1F5) — una caja
           coloreada con borde. Casi los calca `_40_ajuste_franja.py`, PERO
           ese look de Familia/Subfamilia está MUERTO: `_50_fecha.py` carga
           DESPUÉS (mismo criterio "gana la regla que aparece después" de
           CLAUDE.md) y los aplana a texto plano y apagado, sin caja ni
           borde. Medido en vivo antes de tocar nada (Familia: 22px de alto,
           fondo transparente) — si hubiera calcado el `_40_ajuste_franja.py`
           original, Proveedores hubiera quedado pareja a un look que
           Familia/Subfamilia ya NO tienen. Los valores de abajo son los de
           `_50_fecha.py`, que es lo que de verdad se ve en pantalla. */
        .st-key-prov_pop_float [data-testid="stPopover"] button {
            min-width: 0 !important;
            min-height: 0 !important;
            height: auto !important;
            padding: 1px 8px 1px 0 !important;
            font-size: 12px !important;
            font-weight: 400 !important;
            line-height: 1.2 !important;
            border-radius: 0 !important;
            background: transparent !important;
            color: var(--text-secondary) !important;
            border: none !important;
            border-bottom: 2px solid transparent !important;
            box-shadow: none !important;
            gap: 6px !important;
            transition: background .12s !important;
        }
        .st-key-prov_pop_float [data-testid="stPopover"] button:hover,
        .st-key-prov_pop_float [data-testid="stPopover"] button[aria-expanded="true"] {
            background: var(--accent-tint) !important;
        }
        /* SIN un estado "filtrado" propio (el subrayado de acento que
           tendría Familia/Subfamilia vía `chipwrap_..._on`): ese mecanismo
           depende de un wrapper que el código actual de esos dos chips no
           arma —muerto, igual que su look de caja—, así que replicarlo acá
           sería copiar un bug, no una convención viva. El BADGE (más abajo)
           ya dice "N proveedores elegidos" con más precisión que un
           subrayado. */
        /* Icono material (grupos) del popover: mismo tamaño que Familia/
           Subfamilia (15px) y color heredado del botón en vez de un lila
           propio — ahí también los dos chips divergían. */
        .st-key-prov_pop_float [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
            color: inherit !important;
            font-size: 15px !important;
            margin-right: 0 !important;      /* el gap:6px de arriba ya separa */
        }
        /* Badge con el numero de proveedores: se inyecta el valor via
           ::after con content dinamico desde Python (ver _cp_badge_count).
           Mismos valores que el `:violet-badge` nativo de Familia/
           Subfamilia (stBadge, _40_ajuste_franja.py) — antes tenía su
           propia paleta y tamaño de fuente (11px/500), un punto más grande
           y más flojo que el de al lado. */
        .st-key-prov_pop_float [data-testid="stPopover"] button
            [data-testid="stMarkdownContainer"] p::after {
            content: var(--cp-prov-count, "");
            background: var(--accent);
            color: #ffffff;
            border-radius: 3px;
            padding: 1px 6px;
            font-size: 10px;
            font-weight: 700;
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
        /* Los atajos van EN LA LINEA DEL TITULO, no debajo (2026-08-25, a
           pedido). Se sacan del flujo y se anclan a la esquina superior
           derecha de la tarjeta: asi comparten renglon con "Ranking de
           proveedores" y, de paso, la tabla sube los ~36px que ocupaban.

           `position: absolute` contra la tarjeta —que se vuelve `relative`
           abajo— y NO un `margin-top` negativo: el alto del titulo acaba de
           cambiar (11px -> 16px) y volveria a cambiar con cualquier ajuste
           de tipografia, dejando el tiro desincronizado. Anclado a la
           esquina no depende de cuanto mida el titulo.

           Los 16/18px son el padding de la propia tarjeta
           (`estilos/_80_cards.py`), asi que los atajos caen a ras del
           contenido, alineados con el titulo de su izquierda. */
        .st-key-compras_prov_card_ranking {
            position: relative !important;
        }
        .st-key-compras_prov_rank_atajos {
            position: absolute !important;
            top: 16px !important;
            right: 18px !important;
            /* `fit-content` o se estira: el stVerticalBlock de Streamlit
               trae `width: 100%`, que en un elemento absoluto se resuelve
               contra la tarjeta — 572px para tres botones chicos, y el
               bloque terminaba invadiendo el sitio del titulo por la
               izquierda (medido 2026-08-25). */
            width: fit-content !important;
            margin: 0 !important;
            z-index: 2 !important;
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
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
        /* El trigger de la escala de tiempo NO necesita reglas propias:
           `.st-key-compras_prov_rank_atajos button` de arriba es un
           selector descendiente y ya lo dejo como los otros atajos. Solo
           se le saca el padding lateral, que sobra en un boton de puro
           icono, y se centra el glifo. */
        .st-key-compras_prov_rank_atajos
            [data-testid="stPopover"]:has(.st-key-cp_rank_escala) button,
        .st-key-cp_rank_escala button {
            padding: 0 !important;
            width: 24px !important;
            justify-content: center !important;
            color: #6c5ce7 !important;
        }
        /* El CHEVRON de Streamlit. En un trigger de puro icono son dos
           glifos apretados en 24px (medido: scrollWidth 30 sobre
           clientWidth 22, o sea desbordaba), y el `date_range` ya dice
           "esto abre algo".
           Es el UNICO `stIconMaterial` del boton porque el icono de la
           izquierda entra como LABEL en shortcode (`st.popover(
           ":material/date_range:")`, el patron de `pestillos.py`), que
           Streamlit renderiza por markdown. OJO: si alguien lo cambia al
           parametro `icon=` —como hace la pildora de la franja— ese icono
           TAMBIEN pasa a ser `stIconMaterial` y esta regla se lo lleva
           puesto. Verificado en el DOM 2026-08-25. */
        /* Se esconde el WRAPPER, no el glifo: apagar solo el span dejaba
           su div padre ocupando 16px y el boton seguia desbordando
           (scrollWidth 30 sobre clientWidth 22, medido). De ahi el
           `:has()`. */
        .st-key-cp_rank_escala button > div > div:has(
            [data-testid="stIconMaterial"]) {
            display: none !important;
        }

        /* El PANEL. `stPopoverBody` es un PORTAL: se dibuja al final del
           body, fuera de la tarjeta —por eso escapa su `overflow: hidden
           auto`— y por eso hay que alcanzarlo con `:has()` en vez de
           colgarlo del contenedor. Mismo patron que el panel de fecha de
           la franja (estilos/_50_fecha.py) y el del asistente. */
        [data-testid="stPopoverBody"]:has(.st-key-cp_rank_escala_panel) {
            /* 290px es el ancho MINIMO util del riel: con menos, las
               etiquetas de las paradas de "Meses" (ene 24 ... ago 26) se
               encabalgan y el slider deja de leerse. */
            width: 290px !important;
            min-width: 290px !important;
            padding: 12px 14px !important;
        }
        /* La granularidad ocupa el ancho y reparte en tres. Sin esto el
           segmented_control mide su contenido y queda un bloque chico
           pegado a la izquierda, desalineado del riel de abajo (medido:
           191px contra los 250px del slider).
           Van DOS reglas y no una: el `stVerticalBlock` del panel nace con
           `align-items: start`, asi que su hijo queda `flex: 0 1 auto` y
           encogido — el `width:100%` del ButtonGroup se resolvia contra un
           padre que ya media 191px. Se ensancha primero el contenedor del
           widget (su ANCLA PROPIA, no el del panel: tocar el panel movería
           tambien al slider y al caption). */
        .st-key-cp_rank_esc_gran {
            width: 100% !important;
        }
        /* `display: flex` explicito: el ButtonGroup nace BLOCK (medido), y
           sobre un padre block el `flex: 1 1 0` de los botones no hace
           nada — quedaban tres botones de 64px pegados a la izquierda de
           un contenedor de 250.
           El `> div` tampoco es paranoia: entre el ButtonGroup y los
           botones hay un div SIN testid ni clase estable que nace en
           `fit-content` (191px). Ensanchar solo el ButtonGroup no
           alcanzaba porque el `flex:1` de los botones se repartia ese 191
           y no el 250. Se descubrio midiendo `button.parentElement`, que
           no aparece en ningun selector del proyecto.
           Y es `> div` y NO `> *` porque el otro hijo del ButtonGroup es
           el `<label>` del widget, que sigue en el DOM aunque este
           `label_visibility="collapsed"`: con `> *` se llevaba la mitad
           del ancho (125 y 125) y los botones quedaban en 42px. */
        .st-key-cp_rank_esc_gran [data-testid="stButtonGroup"],
        .st-key-cp_rank_esc_gran [data-testid="stButtonGroup"] > div {
            display: flex !important;
            width: 100% !important;
            /* El `width` solo no alcanza: la clase de emotion del div
               interno trae `max-width: fit-content`, que lo volvia a
               clampear en 191px aunque el 100% ganara la cascada. Un
               ancho que "gana" y no se ve es casi siempre esto. */
            max-width: none !important;
        }
        .st-key-cp_rank_esc_gran [data-testid="stButtonGroup"] button {
            flex: 1 1 0 !important;
        }
        /* El caption del total de dias: al ras del riel, no como parrafo. */
        .st-key-cp_rank_escala_panel [data-testid="stCaptionContainer"] {
            margin-top: -4px !important;
            font-size: 11px !important;
        }
        /* ── REGLA DE AÑOS del riel de Días ──────────────────────────────
           2026-08-26, a pedido ("la línea no tiene ninguna indicación de
           qué día o mes estoy seleccionando"). Fila propia DEBAJO del
           riel (no overlay: ver el comentario largo en
           graficos/base.py::selector_escala) — mismo ancho que el
           `st.slider`, así que el 0%-100% de acá coincide con el suyo.
           `position:relative` + hijos `position:absolute; left:X%` es la
           misma técnica que ya usa el riel de select_slider para sus
           propias paradas (más abajo, la granularidad). */
        .cp-riel-regla {
            position: relative;
            height: 14px;
            margin: 2px 0 0;
        }
        .cp-riel-regla span {
            position: absolute;
            top: 0;
            transform: translateX(-50%);
            font-size: 9px;
            color: var(--text-muted);
            white-space: nowrap;
        }
        /* El primero y el último se pinean al borde sin centrarse: a mitad
           de camino fuera del riel se leerían cortados contra el padding
           del popover. */
        .cp-riel-regla span:first-child { transform: translateX(0); }
        .cp-riel-regla span:last-child { transform: translateX(-100%); }
        /* 2026-08-26, a pedido ("no es necesario ver en la línea los días
           del 2023 2024 si mi selección es de días"): el `stSliderTickBar`
           NATIVO de Streamlit (min/max absolutos, "01/01/23 — 24/08/26")
           queda redundante apenas se agrega `.cp-riel-regla` arriba — el
           "2023" del extremo izquierdo ya lo dice el propio ruler, y el
           extremo derecho ya lo dicen las etiquetas de la selección
           VIGENTE (más útiles: son la selección actual, no el límite de
           todo el histórico). Acotado al prefijo `cp_rank_esc_dias_` para
           no afectar Meses/Años, que no usan este riel. */
        [class*="st-key-cp_rank_esc_dias_"] [data-testid="stSliderTickBar"] {
            display: none !important;
        }

        /* Relevo oculto del arrastre "como Excel" (graficos/base.py::
           _aplicar_pan_riel). Mismo patrón que `.st-key-pila_go_*`
           (estilos/_27_pila.py): invisible pero PRESENTE, nunca
           `display:none` — un widget que no se dibuja no existe para
           Streamlit. Acotado por PREFIJO (cp_rank_esc_) Y sufijo (_pan):
           sin el prefijo, un `[class*="_pan"]` suelto también apaga
           `cp_prov_prods_tab_{_pan_inst}` de esta misma vista y los
           `{key_prefix}_pan_topn/_pan_rango` de recetas_comun.py — los
           tres traen "_pan" de casualidad, sin relación con este. */
        [class*="st-key-cp_rank_esc_"][class*="_pan"] {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            opacity: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* ── Atajos del Ranking: de TRES píldoras a UN desplegable ──────────
           2026-08-25, a pedido ("esto ocupa mucho espacio... una lista
           desplegable minimalista"): mismas palabras y misma receta que ya
           resolvió `cp_evo_ctrl`/`gran_float` más abajo (2026-08-23) —
           `st.selectbox` aplanado a TEXTO, sin caja ni sombra, con el
           chevron como única affordance de "esto despliega".

           2026-08-25, 2da vuelta ("podemos unificar estas dos?"): el
           desplegable se MUDA de ser un tercer hijo de
           `compras_prov_rank_atajos` a vivir DENTRO del panel de escala
           (`cp_rank_escala_panel`) — un solo popover para "elegí un
           atajo" y "afiná a mano", no dos triggers para el mismo dato.
           El reset del botón-chevron de más abajo NACIÓ para ganarle a
           `.st-key-compras_prov_rank_atajos button` (la píldora blanca
           con sombra de la fila) — esa regla ya NO alcanza a este
           selectbox (vive en el portal de `stPopoverBody`, fuera de esa
           fila), pero se deja igual: es una base limpia y no depende de
           qué otra cosa ande suelta por ese lado. */
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"] div[role="group"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            min-height: 0 !important;
        }
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"] input,
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"] div[role="group"],
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"] .react-aria-ComboBox {
            height: 22px !important;
            min-height: 0 !important;
        }
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"] input {
            padding: 0 !important;
            height: auto !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            color: #5a5a6a !important;
            cursor: pointer !important;
            text-overflow: ellipsis !important;
        }
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"]:hover input {
            color: #4d3fb3 !important;
        }
        /* El chevron se CONSERVA (en acento): sin ninguna affordance, un
           texto que despliega una lista no se distingue de una etiqueta
           muerta — misma decisión que `cp_evo_ctrl` y Documentos SUNAT. */
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"] svg {
            width: 13px !important;
            height: 13px !important;
            fill: #6c5ce7 !important;
            color: #6c5ce7 !important;
        }
        /* Reset del boton-chevron: sin esto hereda la pildora blanca con
           sombra de `.st-key-compras_prov_rank_atajos button`. */
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"]
            button[aria-haspopup] {
            width: 16px !important;
            min-width: 0 !important;
            height: 22px !important;
            min-height: 0 !important;
            padding: 0 !important;
            border: none !important;
            border-radius: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            flex: 0 0 auto !important;
        }
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"]
            button[aria-haspopup]:hover {
            background: transparent !important;
        }
        /* Ancho: 100% del PANEL (290px, `_css_proveedor.py` § escala), no
           los 128px fijos de cuando vivía suelto en la fila angosta de
           afuera — acá tiene todo el ancho del popover para sí, igual
           que la granularidad y el riel de más abajo. Iguala el criterio
           de `.st-key-cp_rank_esc_gran`: mismo `max-width: none` por el
           mismo motivo (la clase de emotion del div interno trae
           `max-width: fit-content` y clampea el 100% si no se anula). */
        .st-key-cp_rank_atajo_sel {
            width: 100% !important;
            max-width: none !important;
            margin-bottom: 8px !important;
        }
        .st-key-cp_rank_atajo_sel [data-testid="stSelectbox"] {
            width: 100% !important;
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
            /* 2026-08-25, a pedido: capado al mismo alto que la tabla de
               Panel A (`--cp-prov-alto-paneles`, publicada por Python
               desde `_ALTO_FRAME` — proveedor.py). Sin este techo, un
               producto con muchos proveedores estira la lista mucho más
               que el panel de al lado, y el `:has()` de _80_cards.py
               ("dos tarjetas de la fila miden lo mismo") terminaba
               estirando TAMBIÉN a Panel A para igualar ese exceso — un
               gráfico chico con medio panel de aire abajo. Lo que no
               entra scrollea DENTRO, mismo idioma que la tarjeta entera
               (regla de "una tarjeta = una pantalla" más arriba). */
            max-height: var(--cp-prov-alto-paneles);
            overflow-y: auto;
            overflow-x: hidden;
        }
        .pb-cards::-webkit-scrollbar { width: 6px; }
        .pb-cards::-webkit-scrollbar-thumb {
            background: var(--scroll-thumb);
            border-radius: 3px;
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
           hasta que se busca — mismo espíritu que un botón-lengüeta:
           opacidad baja en reposo, sube al pasar el cursor. Acotado a SU
           propia key (CLAUDE.md: estilar el widget puntual, no el
           contenedor).

           2026-08-25: el widget se MUDÓ de su propia columna
           (`st.columns([16, 1])`, pegada al borde derecho de la tarjeta
           y chocando ahí con la fila de atajos) a ser el primer hijo de
           `compras_prov_rank_atajos` — ver el comentario largo en
           proveedor.py. Esta regla sigue intacta porque acota por la
           KEY del widget, no por su contenedor: no le importa en qué
           `with` vive. */
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
        </style>
"""
