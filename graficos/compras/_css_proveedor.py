"""graficos.compras._css_proveedor - CSS del drill de Proveedor.

Bloque estatico (sin interpolacion) que estaba embebido como un
st.markdown de 529 lineas DENTRO de _compras_proveedor_drill, donde
tapaba la logica. Se saco a este modulo el 2026-08-08.

Por que NO vive en `estilos/` pese a la regla de CLAUDE.md: estas reglas
estan scopeadas a las keys de este drill y solo tienen sentido cuando el
drill se dibuja. `estilos/` se inyecta en TODAS las paginas via
inject_css(); moverlo ahi lo aplicaria siempre, que es un cambio de
comportamiento, no una reorganizacion. El drill lo inyecta cuando toca.

DOS exports, y NO son la misma clase de cosa:
  · `CSS` — el `<style>` del documento PADRE, el de siempre.
  · `CSS_RANKING_GRID` — un dict para el `custom_css=` de `AgGrid(...)`,
    que es la ÚNICA vía de estilar el grid: vive en un iframe propio y
    nada del padre lo alcanza (lo mismo que ya obliga a que los colores
    de la barra de "Valor" salgan de `tema.py` y no de `var(--acento)`).
"""

from tema import BLANCO

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
        /* 2026-09-01: la reserva bajo a 0. El `padding-top` existia para
           la banda donde flotaba el popover de Proveedores; desde que ese
           entro en la fila del titulo (arriba), al marco NO le flota nada
           y los 16px eran un hueco gris entre la franja y las tarjetas. */
        .st-key-compras_prov_marco { padding-top: 0 !important; }
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
        /* ── PROVEEDORES ES UN ITEM MAS DE LA FILA DEL TITULO ───────────
           2026-09-01, a pedido ("integremos ese filtro dentro de la tarjeta
           de Ranking, al mismo nivel que el widget de fecha").

           Historia corta de este elemento, porque explica por que el
           bloque encogio tanto: nacio `position: fixed` anclado a la franja
           superior (con un umbral de 1230px calculado a mano contra los
           chips de Familia/Subfamilia, y un `right: 90px` que habia que
           justificar como "80 de padding + 10 de scrollbar"); el
           2026-08-31 bajo a `position: absolute` sobre la esquina de la
           tarjeta —lo que se llevo el umbral y la cuenta del right—; y hoy
           deja de posicionarse del todo. Cada vuelta borro mas CSS que el
           que agrego, y eso es la señal: el elemento estaba peleando por un
           sitio que un contenedor flex le da gratis.

           Ahora lo dibuja `selector_fecha_tarjeta(extra=...)` DENTRO de
           `cp_rank_fila`, el mismo flex row que el titulo y el rango. De
           ahi que no quede casi nada acá: el `flex: 0 0 auto` (no cede
           ancho, como el trigger de la fecha) y poco mas. La PILDORA
           —altura, borde, fondo, hover— la hereda de
           `.st-key-cp_rank_fila button`, que es justo lo que se pedia con
           "al mismo nivel que el widget de fecha": mismo look sin una sola
           regla propia.

           Se conserva la key `prov_pop_float` aunque ya no flote: es el
           ancla del badge que inyecta Python. Mismo criterio que
           `gran_float`. */
        /* Van DOS selectores y el de arriba es el que importa. `st.popover`
           pone su key en el WRAPPER (por eso a `cp_rank_escala` le alcanza
           con una regla), pero `st.container(key=...)` la pone en el
           `stVerticalBlock` de ADENTRO: el item de la fila es el
           `stLayoutWrapper` que lo envuelve, que nace con `width: 100%` y
           `flex: 0 1 auto`. Medido antes de esto: el trigger media 160px y
           su wrapper 363 — se comia el hueco que le tocaba al titulo, que
           quedaba en 105px sin crecer pese a su `flex-grow: 1`. Estilar
           sólo la key de adentro no lo arregla: el que reparte es el padre. */
        .st-key-cp_rank_fila
            > [data-testid="stLayoutWrapper"]:has(> .st-key-prov_pop_float),
        .st-key-prov_pop_float {
            flex: 0 0 auto !important;
            width: auto !important;
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
            /* 2026-08-31: aca los chips recibian un `left` para arrancar
               despues del pill corrido. El compartimento de filtros se ancla
               por la DERECHA (`_50_fecha.py`), asi que un `left` lo movia al
               medio de la franja. El pill de fecha si se sigue corriendo:
               ese vive a la izquierda y el titulo le come el sitio. */
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
        /* El TRIGGER ya no declara su propio look: hereda la pildora de
           `.st-key-cp_rank_fila button` (22px de alto, borde de 0.5px,
           fondo blanco, hover lavanda), que es literalmente lo que se pidio
           con "al mismo nivel que el widget de fecha".
           Lo que vivia aca eran ~18 declaraciones `!important` calcadas de
           `estilos/_50_fecha.py` para imitar A MANO el chip de
           Familia/Subfamilia mientras el elemento flotaba solo. Estar en la
           fila lo vuelve innecesario: dos reglas peleando por el mismo
           pixel donde ahora alcanza con no escribir ninguna. Solo queda el
           `gap`, que la pildora base no define. */
        .st-key-prov_pop_float [data-testid="stPopover"] button {
            gap: 5px !important;
            /* 12px, los mismos que el trigger de la fecha. Heredar la
               pildora base dejaba este en 11 y el de al lado en 12 —
               dos controles pares de la misma fila con medio punto de
               diferencia, que es peor que dos tamanos a proposito.
               El 12 del rango tenia como motivo ser "el unico texto de la
               fila"; desde hoy no lo es. */
            font-size: 12px !important;
        }
        /* Los dos triggers de la fila, alineados al mismo pixel.
           El desfase no era de contenedores —medidos los dos chains, son
           identicos: un div `block` de 26px con un boton `inline-flex` de
           22 y el mismo `line-height: 25.6px`—. Era de BASELINE: un
           `inline-flex` se apoya en la linea base de su PRIMER hijo, y el
           boton de Proveedores empieza con el glifo de 14px mientras el de
           la fecha empieza con texto de 12. Distinta primera caja, distinta
           base: 197 contra 200, y en un pill de 22px esos 3px se ven.
           Se sale del juego de las lineas base: el div que los contiene
           pasa a `flex` y los centra. Vale para los DOS —el de la fecha se
           mueve 1px— porque dejarlo mitad-y-mitad es volver a atarlo al
           contenido del boton, que es de donde vino el bug. */
        .st-key-cp_rank_fila [data-testid="stPopover"] > div {
            display: flex !important;
            align-items: center !important;
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
            /* 14, no los 15 de cuando imitaba al chip de la franja: la
               pildora de la fila mide 22px de alto contra los 26 de aquel,
               y el glifo tiene que quedar por debajo del texto, no encima. */
            font-size: 14px !important;
            margin-right: 0 !important;      /* el gap de arriba ya separa */
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

        /* ── EL PANEL DE PROVEEDORES, COMPACTO ───────────────────────────
           2026-09-01, a pedido ("muy grande, sobre todo el extenderse").
           MEDIDO antes de tocar nada, con un rango que traía DOS
           proveedores: 430x344px. De esos 344, sólo 169 eran contenido:
             46  padding del panel (23px por lado)
             80  cinco gaps de 16px del `stVerticalBlock` — el default de
                 Streamlit, calibrado para una PÁGINA, no para una caja
             49  un `st.divider()`: 1px de línea con 24 de margen a cada lado
           Y el ancho: los cinco botones de atajo iban en `st.columns(5)`
           con `use_container_width`, o sea cada uno reclamaba un quinto
           ENTERO del panel — 382px de contenido, 430 con el padding.
           Con la lista completa (~20 proveedores) el alto llegaba al techo
           de 651px, el 70% de la pantalla.

           Se acota con `:has()` sobre la key de la LISTA, no colgando del
           contenedor: `stPopoverBody` es un portal al final del body
           (fuera de `prov_pop_float`), el mismo motivo por el que el panel
           de la escala y los de Familia/Subfamilia se alcanzan así. Sin
           ese `:has()` esto apretaría TODOS los popovers de la app —el
           error contra el que avisa CLAUDE.md—, incluido el de la escala,
           que ya trae su propio bloque compacto más abajo. */
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_prov_lista"]) {
            width: 250px !important;
            min-width: 250px !important;
            max-width: 250px !important;
            padding: 10px 12px !important;
        }
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_prov_lista"])
            [data-testid="stVerticalBlock"] {
            gap: 7px !important;
        }
        /* Atajos: `type="tertiary"` ya les saca el marco; acá se les saca
           el tamaño de botón de página (40px de alto, 0.25rem/0.75rem de
           padding). Quedan como una línea de enlaces de 11px.
           Se estilan por su ANCLA PROPIA (la fila `cp_prov_atajos`) y no
           por el panel: en el panel también hay checkboxes y un toggle,
           que no tienen por qué heredar esto. */
        .st-key-cp_prov_atajos { gap: 2px !important; }
        .st-key-cp_prov_atajos button {
            min-height: 0 !important;
            height: auto !important;
            padding: 2px 6px !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            line-height: 1.3 !important;
            border-radius: 4px !important;
            color: var(--text-secondary) !important;
        }
        .st-key-cp_prov_atajos button:hover {
            background: var(--accent-tint) !important;
            color: var(--accent-deep) !important;
        }
        /* Buscador: alto de campo de caja, no de formulario. Van DOS
           reglas: apretar el `input` lo baja a 24px pero su
           `stTextInputRootElement` sigue midiendo 40 (medido) — el marco
           es el que trae el alto, no el campo, y sin la segunda regla el
           buscador quedaba de lejos la pieza más alta del panel. */
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_prov_lista"])
            [data-testid="stTextInput"] input {
            padding: 3px 8px !important;
            font-size: 12px !important;
            line-height: 1.3 !important;
        }
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_prov_lista"])
            [data-testid="stTextInputRootElement"] {
            min-height: 0 !important;
            height: 28px !important;
        }
        /* La LISTA. El alto lo pone Python (dinámico, ver proveedor.py);
           acá va sólo lo que no depende del contenido. El `padding-right`
           deja sitio a la barra de scroll para que no tape el último
           carácter del nombre más largo. */
        .st-key-cp_prov_lista {
            padding-right: 4px !important;
            gap: 2px !important;
        }
        /* Filas de 22px en vez de 24+16 de gap. El nombre del proveedor es
           LARGO (razones sociales completas): con 226px de ancho útil hay
           que dejarlo envolver o se corta, así que el `white-space` queda
           en normal y lo que se aprieta es el interlineado. */
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label {
            gap: 6px !important;
            align-items: flex-start !important;
        }
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label > div:last-child,
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label p {
            font-size: 12px !important;
            line-height: 1.25 !important;
        }
        /* Hover de FILA. Va junto con el `width="stretch"` del checkbox
           (proveedor.py): sin el uno, el otro no se nota — el realce
           marcaría 110px de los 226, que es peor que no marcar nada. */
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label {
            padding: 1px 4px !important;
            border-radius: 4px !important;
            /* El `width="stretch"` de Python estira el CONTENEDOR del
               widget (210px, medido) pero el `<label>` de adentro sigue
               midiendo su texto (118px) — o sea el realce marcaría media
               fila. El blanco es la fila entera o no es un blanco. */
            width: 100% !important;
        }
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label:hover {
            background: var(--accent-tint) !important;
        }
        /* El toggle "Nombres en barras" es la ÚNICA opción de dibujo entre
           puros filtros: la raya que la separaba era un `st.divider()` de
           49px. Un `border-top` cuesta 1px y el aire que se le dé. */
        .st-key-cp_prov_show_names {
            border-top: 1px solid var(--border) !important;
            padding-top: 7px !important;
            margin-top: 1px !important;
        }
        .st-key-cp_prov_show_names label p {
            font-size: 11px !important;
            color: var(--text-secondary) !important;
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
        /* ── LA FILA DEL RANKING DE PROVEEDORES: titulo + control ───────
           2026-09-01, a pedido. Antes el titulo ocupaba un renglon entero
           de ancho completo y el control flotaba absoluto sobre su esquina
           — dos cajas encimadas donde solo el pintado las separaba, que es
           lo que se descubrio midiendo: la caja del titulo media 490px
           para 165 de texto, y el control le caia adentro.
           Ahora `selector_fecha_tarjeta` recibe el titulo y lo mete DENTRO
           de esta fila, que pasa a estar EN EL FLUJO y a repartir: el
           titulo se queda con lo que sobra y el control conserva lo suyo.
           Medido: la grilla sube de y=315 a y=285. */
        .st-key-cp_rank_fila {
            position: static !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 10px !important;
            margin: 0 0 4px !important;
        }
        /* El TITULO cede, el control no. El `min-width: 0` no es
           decorativo: sin el, un flex item nunca se encoge por debajo de
           su contenido, asi que un nombre largo empujaria al control fuera
           de la tarjeta en vez de truncar. */
        .st-key-cp_rank_fila > [data-testid="stElementContainer"]:first-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            width: auto !important;
        }
        .st-key-cp_rank_fila .cp-rank-tit {
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            margin: 0 !important;
        }
        .st-key-cp_rank_fila .st-key-cp_rank_escala {
            flex: 0 0 auto !important;
        }
        .st-key-cp_prod_fila {
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
        .st-key-cp_rank_fila [data-testid="stElementContainer"],
        .st-key-cp_prod_fila [data-testid="stElementContainer"] {
            width: auto !important;
        }
        .st-key-cp_rank_fila [data-testid="stElementToolbar"],
        .st-key-cp_prod_fila [data-testid="stElementToolbar"] {
            display: none;
        }
        .st-key-cp_rank_fila button,
        .st-key-cp_prod_fila button {
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
        .st-key-cp_rank_fila button:hover,
        .st-key-cp_prod_fila button:hover {
            background: #f0edfe !important;
            color: #4d3fb3 !important;
        }
        /* El trigger de la escala de tiempo: desde el 2026-08-26 su label
           es EL RANGO ACTIVO ("1 ago - 24 ago 2026"), no un icono de
           calendario -- ver el comentario largo en proveedor.py. Hereda la
           pildora de `.st-key-cp_rank_fila button` (misma
           altura, mismo borde, mismo hover que el resto de la fila) y solo
           corrige lo que cambio al pasar de un glifo a texto:

             - el `width: 24px` y el `justify-content: center` de la version
               icono se VAN: con texto recortaban el label.
             - la fecha se lee como DATO, no como accion, asi que va en el
               gris del texto y no en el acento -- que es lo que ya hacia
               el `st.caption` que este boton reemplazo. El hover (heredado)
               es el que avisa que se puede apretar.
             - un pelo mas grande que los 11px de la pildora base: es el
               unico texto de la fila y ademas el dato que se viene a
               leer. */
        .st-key-cp_rank_fila
            [data-testid="stPopover"]:has(.st-key-cp_rank_escala) button,
            [data-testid="stPopover"]:has(.st-key-cp_prod_escala) button,
        .st-key-cp_rank_escala button,
        .st-key-cp_prod_escala button {
            padding: 0 10px !important;
            font-size: 12px !important;
            white-space: nowrap !important;
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
        [data-testid="stPopoverBody"]:has(.st-key-cp_rank_escala_panel),
        [data-testid="stPopoverBody"]:has(.st-key-cp_prod_escala_panel) {
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
        .st-key-cp_rank_esc_gran,
        .st-key-cp_prod_esc_gran {
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
        .st-key-cp_prod_esc_gran [data-testid="stButtonGroup"],
        .st-key-cp_rank_esc_gran [data-testid="stButtonGroup"] > div,
        .st-key-cp_prod_esc_gran [data-testid="stButtonGroup"] > div {
            display: flex !important;
            width: 100% !important;
            /* El `width` solo no alcanza: la clase de emotion del div
               interno trae `max-width: fit-content`, que lo volvia a
               clampear en 191px aunque el 100% ganara la cascada. Un
               ancho que "gana" y no se ve es casi siempre esto. */
            max-width: none !important;
        }
        .st-key-cp_rank_esc_gran [data-testid="stButtonGroup"] button,
        .st-key-cp_prod_esc_gran [data-testid="stButtonGroup"] button {
            flex: 1 1 0 !important;
        }
        /* El caption del total de dias: al ras del riel, no como parrafo. */
        .st-key-cp_rank_escala_panel [data-testid="stCaptionContainer"],
        .st-key-cp_prod_escala_panel [data-testid="stCaptionContainer"] {
            margin-top: -4px !important;
            font-size: 11px !important;
        }
        /* ── EL POPOVER DE LA ESCALA, COMPACTO ───────────────────────────
           2026-08-26, tercera vuelta, a pedido ("lo veo muy largo
           verticalmente... quizás apegar más los números a la línea").
           MEDIDO antes de tocar nada: de los 249px que medía el popover,
           88 eran aire — cuatro gaps de 16px del `stVerticalBlock` (el
           default de Streamlit, pensado para una página, no para una caja
           de 250px) más 12+12 de padding. Las cinco piezas de adentro
           sumaban 135px reales.

           Se acota con `:has()` al popover que CONTIENE el selector de
           escala, misma técnica que los popovers de Familia/Subfamilia en
           estilos/_40_ajuste_franja.py. Sin ese `:has()` esto apretaría
           TODOS los popovers de la app, que es justo el error que
           CLAUDE.md advierte de las reglas colgadas de un contenedor. */
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_rank_esc_gran"]),
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_prod_esc_gran"]) {
            padding-top: 8px !important;
            padding-bottom: 8px !important;
        }
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_rank_esc_gran"])
            [data-testid="stVerticalBlock"],
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_prod_esc_gran"])
            [data-testid="stVerticalBlock"] {
            gap: 4px !important;
        }
        /* El desplegable de atajos traía además su propio margen inferior,
           que se sumaba al gap.

           OJO con la coma: las dos mitades tienen que repetir el `:has()`
           del popover ENTERAS. Escrito como
           `…:has(A) [class*=B], [class*=C] {…}` la segunda mitad queda
           SUELTA -- matchea ese widget en cualquier parte de la app, no
           dentro de este popover. Es el error que CLAUDE.md advierte de
           las reglas por familia, y lo cometió el script que duplicó estos
           selectores para el prefijo `cp_prod` (2026-08-26). */
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_rank_esc_gran"])
            [class*="st-key-cp_rank_atajo_sel"],
        [data-testid="stPopoverBody"]:has([class*="st-key-cp_prod_esc_gran"])
            [class*="st-key-cp_prod_atajo_sel"] {
            margin-bottom: 0 !important;
        }
        /* ── CABECERA "‹ AGO 2026 ›" del riel de Días ────────────────────
           2026-08-26, segunda vuelta, a pedido y con la captura del
           selector de fecha de Excel al lado: el riel pasó a mostrar UN
           mes (graficos/base.py::_nav_mes) y necesita decir CUÁL, más las
           dos flechas para cambiarlo. Rótulo centrado entre ellas, igual
           que en la captura.

           Las flechas se acotan por sus keys PROPIAS (`_mes_prev` /
           `_mes_sig`) y no por el contenedor: el popover ya tiene reglas
           colgadas de contenedores —el aviso de CLAUDE.md sobre widgets
           que heredan estilo sin que el .py lo insinúe— y este par no
           tiene por qué arrastrar al `segmented_control` de escala ni al
           desplegable de atajos que viven en la misma caja. */
        .cp-riel-mes {
            text-align: center;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: var(--text-primary);
            line-height: 22px;
        }
        [class*="st-key-cp_rank_esc_mes_prev"] button,
        [class*="st-key-cp_prod_esc_mes_prev"] button,
        [class*="st-key-cp_rank_esc_mes_sig"] button,
        [class*="st-key-cp_prod_esc_mes_sig"] button {
            min-height: 22px !important;
            height: 22px !important;
            padding: 0 !important;
            line-height: 1 !important;
            font-size: 15px !important;
            border-radius: 7px !important;
        }
        /* ── REGLA DE DÍAS del riel de Días ──────────────────────────────
           2026-08-26, a pedido ("la línea no tiene ninguna indicación de
           qué día o mes estoy seleccionando"). Fila propia DEBAJO del
           riel (no overlay: ver el comentario largo en
           graficos/base.py::selector_escala) — mismo ancho que el
           `st.slider`, así que el 0%-100% de acá coincide con el suyo.
           `position:relative` + hijos `position:absolute; left:X%` es la
           misma técnica que ya usa el riel de select_slider para sus
           propias paradas (más abajo, la granularidad).

           Nació rotulando AÑOS (el riel abarcaba todo el histórico) y
           pasó a rotular DÍAS DEL MES el mismo día, cuando el riel se
           acotó a un mes. La clase no cambió de nombre: lo que hace
           —marcas de referencia bajo el riel— es lo mismo. */
        .cp-riel-regla {
            position: relative;
            height: 11px;
            /* Margen NEGATIVO a propósito ("apegar más los números a la
               línea", 2026-08-26). MEDIDO dentro de la caja de 40px del
               `st.slider`: la línea va de 18 a 22, los tiradores de 14 a
               26, y de 26 a 40 no hay NADA — son los 14px que ocupaba el
               `stSliderTickBar`, que acá va oculto. Los -22px meten la
               regla en ese hueco en vez de sumar una banda nueva abajo.
               El número reparte un presupuesto FIJO: lo que se le saca de
               arriba (holgura con el tirador) se le da abajo (holgura con
               el caption, que no se mueve porque su contenedor mide 0).
               Con -22 quedan ~4px de cada lado; con -20 el caption se
               pegaba a 1px. Si algún día se deja de ocultar el tick bar,
               este número miente. */
            margin: -22px 0 0;
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
           NATIVO de Streamlit queda redundante apenas se agrega
           `.cp-riel-regla` arriba. Con la ventana de un mes ya no dice
           "01/01/23 — 24/08/26" sino los bordes del mes, que es justo lo
           que ya rotulan la cabecera `.cp-riel-mes` y las dos marcas
           extremas de la regla — tres veces lo mismo en tres renglones
           seguidos. Acotado al prefijo `cp_rank_esc_dias_` para no
           afectar Meses/Años, que no usan este riel. */
        [class*="st-key-cp_rank_esc_dias_"] [data-testid="stSliderTickBar"],
        [class*="st-key-cp_prod_esc_dias_"] [data-testid="stSliderTickBar"] {
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
        [class*="st-key-cp_rank_esc_"][class*="_pan"],
        [class*="st-key-cp_prod_esc_"][class*="_pan"] {
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
           `cp_rank_fila` a vivir DENTRO del panel de escala
           (`cp_rank_escala_panel`) — un solo popover para "elegí un
           atajo" y "afiná a mano", no dos triggers para el mismo dato.
           2026-08-26, 3ra vuelta ("«Atajos» no significa nada para el
           usuario"): deja de ser un `st.selectbox` y pasa a ser
           `st.pills` APLANADO A TEXTO, con los cuatro atajos a la vista
           separados por "·". El desplegable gastaba 22px en una palabra
           que no era ninguna de las opciones. Se eligió entre tres
           mockups; ganó el de texto por ser el más liviano en ALTO, que
           es el recurso escaso de este panel.

           Vive en el portal de `stPopoverBody`, así que
           `.st-key-cp_rank_fila button` (la píldora blanca de
           la fila de afuera) no lo alcanza — igual se resetea todo a
           mano, para no depender de qué ande suelto por ese lado. */
        .st-key-cp_rank_atajo_sel [data-testid="stButtonGroup"],
        .st-key-cp_prod_atajo_sel [data-testid="stButtonGroup"] {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 0 !important;
            row-gap: 2px !important;
            width: 100% !important;
            max-width: none !important;
        }
        .st-key-cp_rank_atajo_sel [data-testid="stButtonGroup"] button,
        .st-key-cp_prod_atajo_sel [data-testid="stButtonGroup"] button {
            min-width: 0 !important;
            min-height: 0 !important;
            height: auto !important;
            padding: 0 !important;
            border: none !important;
            border-radius: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
            color: var(--accent-deep) !important;
            font-size: 12px !important;
            font-weight: 400 !important;
            line-height: 1.5 !important;
        }
        /* El separador va en un `::after` y no como elemento propio: con
           cuatro atajos serian tres nodos mas que Streamlit no sabe
           dibujar entre las pastillas de un `stButtonGroup`. Y al colgar
           del boton, si un atajo no aplica (los recorta `atajos_rango`
           cuando su rango no toca los datos) su separador se va con el:
           no queda un "·" huerfano al final. */
        .st-key-cp_rank_atajo_sel
            [data-testid="stButtonGroup"] button:not(:last-child)::after {
            content: "·";
            color: var(--text-muted);
            padding: 0 7px;
            font-weight: 400;
        }
        .st-key-cp_rank_atajo_sel
            [data-testid="stButtonGroup"] button:hover {
            text-decoration: underline !important;
        }
        /* Es un MENU DE ACCIONES: el callback devuelve la seleccion a
           `None` en la misma corrida, asi que nada deberia quedar marcado.
           Este reset cubre el parpadeo entre el clic y el rerun -- sin el,
           el atajo apretado se pinta un instante como pastilla activa y el
           texto salta. */
        .st-key-cp_rank_atajo_sel
            [data-testid="stButtonGroup"] button[aria-checked="true"],
        .st-key-cp_rank_atajo_sel
            [data-testid="stButtonGroup"] button[aria-pressed="true"] {
            background: transparent !important;
            color: var(--accent-deep) !important;
        }
        .st-key-cp_rank_atajo_sel,
        .st-key-cp_prod_atajo_sel {
            width: 100% !important;
            max-width: none !important;
            margin-bottom: 8px !important;
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
               desde `_ALTO_PRODS` — proveedor.py; era `_ALTO_FRAME`, un
               fijo de 8 filas, hasta que el 2026-09-02 esa tabla pasó a
               medir sus propias filas). Sin este techo, un
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

        /* ── El selector de fecha del Ranking de PRODUCTOS ───────────────
           2026-08-26, a pedido ("el mismo selector de fecha que la tabla
           de proveedores"). Comparte el componente
           (`_comun.py::selector_fecha_tarjeta`) y casi todo el CSS, que se
           lista arriba con su prefijo propio. Lo que NO puede compartir es
           la POSICION, y el motivo se midio: la fila de Proveedor flota
           con `position:absolute; top:16; right:18` sobre SU tarjeta, que
           declara `position:relative`. La de Producto heredo ese absolute
           sin tener ancestro posicionado propio, asi que se anclo al
           ancestro posicionado mas cercano -- la tarjeta de PROVEEDOR, mas
           arriba en la pila-- y aparecio 1124px por encima de donde
           tenia que estar.

           Se pudo arreglar de dos formas: darle `position:relative` a la
           tarjeta de Producto, o sacarle el absolute a la fila. Va la
           segunda: en Producto la esquina superior derecha ya la ocupa el
           panel de detalle (nombre del producto + ventana + granularidad),
           asi que flotar ahi seria chocar. En flujo, arriba del titulo,
           no pelea con nada. */
        .st-key-cp_prod_fila {
            position: static !important;
            width: fit-content !important;
            margin: 0 0 4px !important;
        }
        /* El CHEVRON de Streamlit, mismo trato que en `cp_rank_escala`: se
           esconde el WRAPPER y no el glifo (apagar solo el span deja su
           div padre ocupando 16px y el boton sigue desbordando). Esta
           regla no se pudo generar duplicando la de arriba porque su
           selector se parte en varias lineas. */
        .st-key-cp_prod_escala button > div > div:has(
            [data-testid="stIconMaterial"]) {
            display: none !important;
        }

        </style>
"""


# ── El AgGrid del ranking de proveedores ────────────────────────────
# Se estila por las VARIABLES del tema (`--ag-*`) y no por selectores
# propios, por una razon medida y no por gusto: `theme="streamlit"` declara
# las suyas dentro de un `:where(.ag-theme-params-1)`, y `:where()` tiene
# especificidad CERO. O sea que cualquier regla nuestra le gana sin un solo
# `!important`, y de paso se mueve la misma palanca que usa el tema en vez
# de pelearle sus reglas una por una.
CSS_RANKING_GRID = {
    ".ag-root-wrapper": {
        # Todo blanco, a pedido (2026-08-28). El rayado del tema es
        # sutilisimo — un #fbfbfb al 50% de alpha — y aun asi se lee como
        # bandas adentro de una tarjeta que ya es blanca. Lo que separa las
        # filas sigue siendo la linea de `.ag-row`, que no depende del
        # rayado. La cabecera va al mismo blanco por lo mismo: su borde
        # inferior de 1px alcanza para que siga leyendose como cabecera.
        #
        # La trampa de la regla #235 (apagar el zebra deja una tabla de
        # SELECCION sin rastro de que se clickeo) NO aplica aca, y se
        # verifico antes de tocar nada: este tema si estila la fila
        # elegida — `.ag-row-selected::before` la pinta con el acento al
        # 12%, que se ve igual de bien sobre blanco.
        "--ag-odd-row-background-color": BLANCO,
        "--ag-header-background-color": BLANCO,
        # Medio punto menos que el default del tema (12px). El fraccionario
        # es a pedido (2026-08-28) despues de ver los 11px en pantalla: 11
        # queda algo chico y 12 es el original. No hay que redondearlo --
        # esto termina en un `font-size` y el navegador resuelve tipografia
        # en subpixel, asi que 11.5px se dibuja distinto de los dos enteros.
        "--ag-data-font-size": "11.5px",
        "--ag-header-font-size": "11.5px",
    },
}
# OJO, para el que venga a bajar estos nombres a minuscula por CSS: ya se
# intento y no se puede. Aca vivio un `text-transform: lowercase` sobre la
# columna de nombres, y duro horas: el pedido no era "minuscula" sino
# "minuscula pero como NOMBRE PROPIO", y eso CSS no lo hace sobre un texto
# que ya viene en mayusculas -- `capitalize` no baja el resto de la palabra,
# y dos `text-transform` no se encadenan sobre el mismo texto. Lo resuelve
# `_etiquetas_proveedor.nombre_propio`, que ademas es pura y testeable.
