"""graficos.compras._css_proveedor - CSS del drill de Proveedor.

Bloque estatico (sin interpolacion) que estaba embebido como un
st.markdown de 529 lineas DENTRO de _compras_proveedor_drill, donde
tapaba la logica. Se saco a este modulo el 2026-08-08.

Por que NO vive en `estilos/` pese a la regla de CLAUDE.md: estas reglas
estan scopeadas a las keys de este drill y solo tienen sentido cuando el
drill se dibuja. `estilos/` se inyecta en TODAS las paginas via
inject_css(); moverlo ahi lo aplicaria siempre, que es un cambio de
comportamiento, no una reorganizacion. El drill lo inyecta cuando toca.

TRES exports, y el primero NO es la misma clase de cosa que los otros:
  · `CSS` — el `<style>` del documento PADRE, el de siempre.
  · `CSS_RANKING_GRID` y `CSS_PIVOTE_DOCS` — dicts para el `custom_css=`
    de `AgGrid(...)`, que es la ÚNICA vía de estilar un grid: vive en un
    iframe propio y nada del padre lo alcanza (lo mismo que ya obliga a
    que los colores de la barra de "Valor" salgan de `tema.py` y no de
    `var(--acento)`). Uno por grid, porque son dos tablas distintas: el
    ranking de arriba y el pivote de documentos de abajo.
"""

from tema import (ACENTO_TEXTO, ACENTO_TEXTO_OSCURO, BLANCO, GRIS_BORDE,
                  GRIS_LINEA_GRILLA, GRIS_TEXTO_MEDIO)

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

           Se conserva la key `cp_prov_pop_float` aunque ya no flote: es el
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
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_prov_pop_float),
        .st-key-cp_prov_pop_float,
        .st-key-cp_prod_fila
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_prod_prov_pop_float),
        .st-key-cp_prod_prov_pop_float {
            flex: 0 0 auto !important;
            width: auto !important;
        }
        /* 2026-09-26: se fue el CSS de `compras_prov_titulo_franja` —el
           nombre de la vista, `position: fixed` en la franja desde 1340px—
           junto con el `left` + 112px que le corria el pill de fecha para
           hacerle sitio. Ningun `.py` dibujaba ya ese contenedor, y el pill
           de la franja no existe en Compras desde el 2026-09-06. Mismo
           patron que el titulo de Ventas › Comparativo: en una pila, un
           `fixed` flota sobre las otras secciones. Ver `arquitectura.md`
           regla #526. */
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
            /* Sin `margin-bottom`: desde el 2026-09-09 esta clase NO es una
               fila, es la mitad izquierda de una (`cp_evo_cab`), y el aire
               de abajo lo pone la fila entera. Ojo con el margen NEGATIVO
               que Streamlit le mete al `stMarkdown` con HTML de bloque
               (regla #162): lo neutraliza `cp_evo_cab`, abajo. */
            margin: 0;
            /* 24px CLAVADOS, el mismo alto que los desplegables de al lado.
               Es lo que hace que la cabecera mida 24 tanto en un renglón
               como en dos, y por eso `_CROMO_CARD_EVO` (proveedor.py) puede
               ser un número: con `line-height: normal` el título pedía 26 y
               la figura perdía 2px cada vez. */
            line-height: 24px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        /* ── La CABECERA de la tarjeta de Evolución: título + controles ───
           2026-09-09, a pedido ("el selector de tiempo y la granularidad
           debe subir a la fila del título, alineado al lado derecho").

           `cp_evo_cab` ENVUELVE a `cp_evo_ctrl` en vez de reemplazarlo: el
           reparto horizontal de los tres desplegables está medido al píxel
           (ver su bloque, más abajo) y no se toca nada de eso — acá sólo se
           agrega un nivel que pone el título a la izquierda y esa fila,
           entera, contra el borde derecho.

           `flex-wrap: wrap` + el título como PRIMER ítem no es decoración:
           es lo que resuelve el tramo angosto sin un `@media`. Medido en el
           navegador: la fila útil de esta tarjeta mide 398px a 1280 de
           viewport (entra todo: 68 del título + 274 de los controles + los
           huecos) pero baja a 290px alrededor de 1000, donde ya no entra.
           Ahí `cp_evo_ctrl` —que es UN solo ítem flex, no cuatro— cae
           entero al renglón de abajo y sigue pegado a la derecha, que es
           exactamente el layout que había antes de este cambio. Sin el
           `wrap` se desbordaba la tarjeta; con `wrap` pero sin agrupar los
           controles, bajaban de a uno y la fila quedaba rota en dos mitades
           desparejas.
           (Por debajo de ~850px las columnas del drill se apilan y la
           tarjeta pasa a ancho completo, así que ahí vuelve a entrar todo
           en un renglón.) */
        .st-key-cp_evo_cab {
            display: flex !important;
            flex-flow: row wrap !important;
            align-items: center !important;
            /* `0 8px`: sin hueco entre renglones cuando envuelve — los 6px
               de abajo son de la fila entera, no de cada línea. */
            gap: 0 8px !important;
            width: auto !important;
            margin: 0 0 6px !important;
            padding: 0 !important;
        }
        /* El título. Es un `stMarkdown` suelto (no un container), así que su
           hijo directo del flex es un `stElementContainer` SIN key propia:
           se lo identifica por lo que trae adentro y no por un `:not(...)`,
           que se rompería el día que se agregue otro markdown a la fila. */
        .st-key-cp_evo_cab > [data-testid="stElementContainer"]:has(.cp-evo-tit) {
            flex: 0 1 auto !important;
            min-width: 0 !important;
            width: auto !important;
            margin: 0 !important;
        }
        /* Y el margen NEGATIVO de adentro, que es el que muerde: un
           `st.markdown` con HTML de bloque se lleva un `margin-bottom: -16px`
           en su `stMarkdownContainer` (regla #162). En una fila normal no se
           nota; acá SÍ, y sólo cuando la cabecera envuelve — el -16 se le
           resta al alto de la primera línea, así que la segunda se le sube
           encima. Medido a 1000px de viewport antes del arreglo: el título
           ocupaba de 80 a 106 y los controles arrancaban en 90. */
        .st-key-cp_evo_cab [data-testid="stMarkdownContainer"] {
            margin-bottom: 0 !important;
        }
        /* La fila de controles, contra el borde derecho. Es un container
           anidado, así que el hijo directo es su `stLayoutWrapper` (mismo
           detalle que documenta el bloque de `cp_evo_ctrl`, más abajo). */
        .st-key-cp_evo_cab > [data-testid="stLayoutWrapper"] {
            flex: 0 0 auto !important;
            width: auto !important;
            margin: 0 0 0 auto !important;
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
        /* Las cuatro cifras siguen al cursor sobre el gráfico
           (`inyecciones/hover_kpis.py`, 2026-09-09). Mientras muestran un
           punto que NO es el de reposo, el encabezado se enciende en acento:
           sin ninguna señal, cuatro números que cambian solos se leen como
           un parpadeo, y el usuario no sabe si está viendo el último período
           o el que tiene debajo del mouse. El encabezado ya DICE cuál es —
           esto sólo lo hace mirar. El color NO se pone con `!important` ni
           se anima: es un cambio que ocurre a 60fps mientras se barre la
           línea, y una transición lo dejaría siempre a medio camino. */
        .cp-evo-kpis-tit.cp-kpis-hover {
            color: var(--accent-deep);
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
        .st-key-cp_prov_pop_float [data-testid="stPopover"] button,
        .st-key-cp_prod_prov_pop_float [data-testid="stPopover"] button {
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
        .st-key-cp_prov_pop_float [data-testid="stPopover"] button [data-testid="stIconMaterial"],
        .st-key-cp_prod_prov_pop_float [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
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
        .st-key-cp_prov_pop_float [data-testid="stPopover"] button
            [data-testid="stMarkdownContainer"] p::after,
        .st-key-cp_prod_prov_pop_float [data-testid="stPopover"] button
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
           (fuera de `cp_prov_pop_float`), el mismo motivo por el que el panel
           de la escala y los de Familia/Subfamilia se alcanzan así. Sin
           ese `:has()` esto apretaría TODOS los popovers de la app —el
           error contra el que avisa CLAUDE.md—, incluido el de la escala,
           que ya trae su propio bloque compacto más abajo. */
        [data-testid="stPopoverBody"]:has(.st-key-cp_prov_lista),
        [data-testid="stPopoverBody"]:has(.st-key-cp_prod_prov_lista) {
            width: 250px !important;
            min-width: 250px !important;
            max-width: 250px !important;
            padding: 10px 12px !important;
        }
        [data-testid="stPopoverBody"]:has(.st-key-cp_prov_lista)
            [data-testid="stVerticalBlock"],
        [data-testid="stPopoverBody"]:has(.st-key-cp_prod_prov_lista)
            [data-testid="stVerticalBlock"] {
            gap: 7px !important;
        }
        /* Atajos: `type="tertiary"` ya les saca el marco; acá se les saca
           el tamaño de botón de página (40px de alto, 0.25rem/0.75rem de
           padding). Quedan como una línea de enlaces de 11px.
           Se estilan por su ANCLA PROPIA (la fila `cp_prov_atajos`) y no
           por el panel: en el panel también hay checkboxes y un toggle,
           que no tienen por qué heredar esto. */
        .st-key-cp_prov_atajos,
        .st-key-cp_prod_prov_atajos { gap: 2px !important; }
        .st-key-cp_prov_atajos button,
        .st-key-cp_prod_prov_atajos button {
            min-height: 0 !important;
            height: auto !important;
            padding: 2px 6px !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            line-height: 1.3 !important;
            border-radius: 4px !important;
            color: var(--text-secondary) !important;
        }
        .st-key-cp_prov_atajos button:hover,
        .st-key-cp_prod_prov_atajos button:hover {
            background: var(--accent-tint) !important;
            color: var(--accent-deep) !important;
        }
        /* Buscador: alto de campo de caja, no de formulario. Van DOS
           reglas: apretar el `input` lo baja a 24px pero su
           `stTextInputRootElement` sigue midiendo 40 (medido) — el marco
           es el que trae el alto, no el campo, y sin la segunda regla el
           buscador quedaba de lejos la pieza más alta del panel. */
        [data-testid="stPopoverBody"]:has(.st-key-cp_prov_lista)
            [data-testid="stTextInput"] input,
        [data-testid="stPopoverBody"]:has(.st-key-cp_prod_prov_lista)
            [data-testid="stTextInput"] input {
            padding: 3px 8px !important;
            font-size: 12px !important;
            line-height: 1.3 !important;
        }
        [data-testid="stPopoverBody"]:has(.st-key-cp_prov_lista)
            [data-testid="stTextInputRootElement"],
        [data-testid="stPopoverBody"]:has(.st-key-cp_prod_prov_lista)
            [data-testid="stTextInputRootElement"] {
            min-height: 0 !important;
            height: 28px !important;
        }
        /* La LISTA. El alto lo pone Python (dinámico, ver proveedor.py);
           acá va sólo lo que no depende del contenido. El `padding-right`
           deja sitio a la barra de scroll para que no tape el último
           carácter del nombre más largo. */
        .st-key-cp_prov_lista,
        .st-key-cp_prod_prov_lista {
            padding-right: 4px !important;
            gap: 2px !important;
        }
        /* Filas de 22px en vez de 24+16 de gap. El nombre del proveedor es
           LARGO (razones sociales completas): con 226px de ancho útil hay
           que dejarlo envolver o se corta, así que el `white-space` queda
           en normal y lo que se aprieta es el interlineado. */
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label,
        .st-key-cp_prod_prov_lista [data-testid="stCheckbox"] label {
            gap: 6px !important;
            align-items: flex-start !important;
        }
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label > div:last-child,
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label p,
        .st-key-cp_prod_prov_lista [data-testid="stCheckbox"] label > div:last-child,
        .st-key-cp_prod_prov_lista [data-testid="stCheckbox"] label p {
            font-size: 12px !important;
            line-height: 1.25 !important;
        }
        /* Hover de FILA. Va junto con el `width="stretch"` del checkbox
           (proveedor.py): sin el uno, el otro no se nota — el realce
           marcaría 110px de los 226, que es peor que no marcar nada. */
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label,
        .st-key-cp_prod_prov_lista [data-testid="stCheckbox"] label {
            padding: 1px 4px !important;
            border-radius: 4px !important;
            /* El `width="stretch"` de Python estira el CONTENEDOR del
               widget (210px, medido) pero el `<label>` de adentro sigue
               midiendo su texto (118px) — o sea el realce marcaría media
               fila. El blanco es la fila entera o no es un blanco. */
            width: 100% !important;
        }
        .st-key-cp_prov_lista [data-testid="stCheckbox"] label:hover,
        .st-key-cp_prod_prov_lista [data-testid="stCheckbox"] label:hover {
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
        /* 2026-10-01: la fila de ABAJO (`paneles_row`) también lleva piso.
           Desde ese día son TRES columnas —Documentos | Evolución |
           Proveedores de— y sin piso, en una ventana angosta, se apretaban
           hasta ilegibles; con él, la tercera baja a un renglón propio.
           260 y no los 300 de arriba: medido con Playwright, a 1100px de
           ventana las de los costados miden ~285 y con 300 la tercera ya
           saltaba de renglón, cuando la tabla de documentos (fecha, número,
           valor) y la lista del Panel B entran enteras. Regla #578. */
        .st-key-paneles_row [data-testid="stColumn"] {
            min-width: 260px !important;
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
        /* 2026-09-02: `cp_prod_fila` (Ranking de PRODUCTOS) entra a este
           bloque, a pedido ("alineemos el toggle de fecha... para que quede
           alineado con el título, así como está en Ranking de Proveedores").
           Venía del estado ANTERIOR de esta misma fila: `position: absolute;
           top: 16px; right: 18px`, o sea el control flotando sobre la
           esquina de la tarjeta y el título gastando un renglón entero
           debajo. Comparte las reglas en vez de tener las suyas porque el
           pedido es literalmente "que se vea como aquélla": dos bloques
           gemelos son dos sitios donde arreglar el próximo detalle. */
        /* 2026-09-04: `cp_sem_fila` (vista Semanal) entra a este bloque,
           a pedido ("el mismo selector de fecha, arriba, alineado con los
           toggles de dia/semana/mes y pegado a la derecha"). Con una
           diferencia: esta fila NO lleva titulo —el nombre de la seccion
           lo pone el rail— asi que sus dos items son el `st.pills` de
           granularidad y el trigger de fecha, y el `space-between` los
           manda a los dos bordes sin necesidad del `flex: 1 1 auto` que
           aca abajo reparte el hueco entre el titulo y el control.
           OJO, lo que NO comparte: las reglas de `... fila button`, mas
           abajo. Esas pintan de pildora blanca a TODO boton descendiente,
           y en esta fila el descendiente de al lado es el ButtonGroup de
           la granularidad — es exactamente el caso que advierte CLAUDE.md
           (una regla colgada del contenedor captura widgets que el .py no
           insinua). Su trigger las repite acotadas a `cp_sem_escala`. */
        /* 2026-09-06: `cp_vol` (Volatilidad) es el CUARTO consumidor, y el
           unico que NO entra a este bloque de fila. Su cabecera ya existia
           —la fila `vol_fila_hdr` (con unas horas del 2026-09-12 como panel
           a la derecha de la tabla, `vol_panel`), en
           estilos/_80_cards.py— asi que el helper dibuja su `cp_vol_fila`
           ADENTRO de aquella: es un item mas de un flex ajeno, no la fila.
           Lo que se le hace medir su contenido esta alla, pegado al resto
           de las reglas de esa cabecera. Todo lo demas —pildora del
           trigger y panel— si lo comparte, con las reglas
           colgadas de `cp_vol_escala` y no de la fila, por el mismo motivo
           que `cp_sem`. */
        .st-key-cp_rank_fila,
        .st-key-cp_prod_fila,
        .st-key-cp_sem_fila {
            position: static !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: space-between !important;
            gap: 10px !important;
            margin: 0 0 4px !important;
        }
        /* ── LOS DOS FILTROS DE LA VISTA SEMANAL (2026-09-08) ───────────
           `cp_sem_filtros` es el grupo de la izquierda (granularidad +
           Familia + Producto) y existe para que la fila de arriba siga
           teniendo DOS items: con cuatro, el `space-between` reparte el
           hueco entre todos y los deja desperdigados a lo ancho de la
           tarjeta en vez de agrupados a la izquierda.

           `flex-wrap` es la RED, no el plan. Medido en el navegador con la
           tarjeta a todo el ancho:

               viewport 1280   fila 869px   ->  no entra, baja un renglon
               viewport 1440   fila 1029px  ->  un solo renglon

           porque la suma no cede: pildoras 354 + Familia 190 + Producto
           210 + fecha 154 + 30 de gaps = 938. Sin wrap, lo que sobra
           desborda la tarjeta; con wrap, la fecha baja un renglon (fila de
           68px en vez de 40, verificado). Mismo criterio —y misma red— que
           `vap_fila_hdr` en `estilos/_80_cards.py`.

           El `margin-left: auto` de la fecha NO es de adorno: un item que
           WRAPEA arranca el renglon nuevo, asi que `space-between` deja de
           alcanzar y la fecha quedaba pegada a la IZQUIERDA — visto en
           pantalla. Con el `auto` se come el hueco del renglon y vuelve al
           borde derecho, que es donde esta en las otras tres tarjetas que
           usan este mismo selector.

           OJO (2026-09-17): este comentario se cerraba ACA, antes del
           parrafo de abajo, y ese parrafo quedaba afuera como si fuera un
           selector. Un selector invalido invalida la regla ENTERA, asi que
           el `flex-wrap: wrap` de la fila nunca llego al navegador — medido
           en el CSSOM: la unica regla con `flex-wrap` sobre la fila era la
           `nowrap` de Streamlit. La fila no bajaba de renglon: apretaba.

           LOS ANCHOS SON MEDIDOS, con el mismo metodo que documenta el
           bloque de `vap_hdr_*`: texto del PEOR caso + 50px de cromo (34
           de la caja del combobox + 16 de padding propio del `<input>`).
           A DM Sans 12px son ~7,16px por caracter:

               Familia   "BEBIDAS CON ALCOHOL"  19 ch  136 -> 190
               Producto  "Todos los productos"  19 ch  136 -> 190, +20
                         de aire para que el nombre de un producto real
                         (los del top miden 21,6 ch de media) entre casi
                         siempre -> 210

           Lo que NO entra son los nombres largos de la cola (el peor del
           parquet mide 58 caracteres) y es un recorte ACEPTADO: la lista
           de un `st.selectbox` recorta con `text-overflow: clip`, sin
           puntos suspensivos (regla #318), y truncar en el `format_func`
           lo arreglaria a la vista pero romperia el BUSCADOR — Streamlit
           filtra sobre la etiqueta formateada, asi que un nombre cortado
           en 28 caracteres deja de encontrarse escribiendo el final. Se
           prefiere buscar entero y ver cortado. */
        .st-key-cp_sem_fila { flex-wrap: wrap !important; }
        /* Los dos selectores porque el item del flex es el popover MISMO
           (medido: el segundo hijo de la fila ya trae la clase de la key),
           y el `:has` cubre el caso de que una version de Streamlit lo
           envuelva. */
        .st-key-cp_sem_fila > .st-key-cp_sem_escala,
        .st-key-cp_sem_fila > *:has(> .st-key-cp_sem_escala) {
            margin-left: auto !important;
        }
        .st-key-cp_sem_filtros {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            gap: 10px !important;
            width: auto !important;
        }
        /* `st.container(key=…)` pone la key en el `stVerticalBlock` de
           ADENTRO: el item del flex es el `stLayoutWrapper` anonimo que lo
           envuelve, que nace con `width: 100%`. Estilar solo la key de
           adentro no alcanza — el que reparte es el padre (regla #272). */
        .st-key-cp_sem_filtros
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_sem_hdr_familia) {
            flex: 1 1 150px !important;
            min-width: 0 !important;
            width: auto !important;
            max-width: 190px !important;
        }
        .st-key-cp_sem_filtros
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_sem_hdr_producto) {
            flex: 1 1 150px !important;
            min-width: 0 !important;
            width: auto !important;
            max-width: 210px !important;
        }
        /* SUBFAMILIA y PROVEEDOR (2026-09-19, a pedido), con el mismo método
           de arriba —texto del peor caso + 50 de cromo— pero sin llegar al
           peor caso: la fila no da. Toggle 354 + Familia 190 + estos dos +
           Producto 210 + cuatro gaps de 10 tienen que entrar en los 1199px
           de la fila a 1366, que es lo que deja la KPI y la fecha en el
           segundo renglón y NO abre un tercero (la tarjeta mide lo mismo
           que antes, `alturas.SEMANAL_SOLO`). Quedan 399 para los dos:
           Subfamilia 180 y Proveedor 200. Lo que no entra es un recorte
           ACEPTADO, por el mismo motivo que Producto: el buscador filtra
           sobre el nombre entero.

           2026-09-19 (2), a pedido: «reducir horizontalmente los filtros
           para que entre en la misma fila el widget de fecha». Con los
           cuatro a ancho fijo el grupo medía 1131px y la fecha (138) no
           entraba al lado en los 1252 de la fila a 1366: bajaba al renglón
           de la KPI. Ahora los anchos de arriba son TOPES, no anchos: cada
           desplegable arranca en 150 (`flex-basis`, que es lo que cuenta
           para decidir si el grupo parte renglón) y crece hasta su tope con
           lo que deje la fecha. Medido a 1366: el grupo entra en 1104 y los
           cuatro quedan a ~190, casi su tope. Por debajo de 951 (toggle +
           4 × 150 + gaps) el grupo sí parte renglón, que es la red de
           siempre. Regla #471. */
        .st-key-cp_sem_filtros
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_sem_hdr_subfamilia) {
            flex: 1 1 150px !important;
            min-width: 0 !important;
            width: auto !important;
            max-width: 180px !important;
        }
        .st-key-cp_sem_filtros
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_sem_hdr_proveedor) {
            flex: 1 1 150px !important;
            min-width: 0 !important;
            width: auto !important;
            max-width: 200px !important;
        }
        /* EL GRUPO DE FILTROS TOMA LO QUE DEJA LA FECHA, en el mismo
           renglón. `flex-basis: 0` + `min-width` es lo que lo hace: al
           partir renglones el navegador cuenta el mínimo (620) y no los
           1131 de su contenido, así que la fecha le entra al lado; después
           crece hasta llenar. Si la fila no da ni para el mínimo más la
           fecha, la fecha baja — la misma red de antes. El item del flex es
           el `stLayoutWrapper` que envuelve a la key (regla #272). */
        .st-key-cp_sem_fila
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_sem_filtros) {
            flex: 1 1 0 !important;
            /* `min()` por el celular: 620 fijos desbordarían una fila
               de 340. */
            min-width: min(620px, 100%) !important;
            width: auto !important;
        }
        /* Y el contenedor de elemento de adentro TAMBIEN, o el campo no
           llena el ancho reservado: la regla `width: auto` de mas abajo
           —que existe para que cada item mida su contenido— en un
           `stVerticalBlock` (flex column con `align-items: start`) deja de
           estirar y pasa a ser `fit-content`, un tope invisible que
           agrandar el hueco no supera. Es la misma trampa medida que
           documenta el bloque de `vap_hdr_*`. */
        .st-key-cp_sem_hdr_familia,
        .st-key-cp_sem_hdr_subfamilia,
        .st-key-cp_sem_hdr_proveedor,
        .st-key-cp_sem_hdr_producto { width: 100% !important; }
        /* CON EL `.st-key-cp_sem_filtros` DELANTE (2026-10-10, regla #624):
           sin él empataba en especificidad con el `width: auto` de
           `.st-key-cp_sem_fila [data-testid="stElementContainer"]`, y este
           CSS se inyecta DOS veces (la sección y el drill de Proveedor):
           la copia de abajo ganaba y el contenedor medía 37px. El selectbox
           de antes lo tapaba con su ancho mínimo propio; el multiselect no
           tiene, y el «Todas las familias» quedaba en una caja de 5px. */
        .st-key-cp_sem_filtros .st-key-cp_sem_hdr_familia > [data-testid="stElementContainer"],
        .st-key-cp_sem_filtros .st-key-cp_sem_hdr_subfamilia > [data-testid="stElementContainer"],
        .st-key-cp_sem_filtros .st-key-cp_sem_hdr_proveedor > [data-testid="stElementContainer"],
        .st-key-cp_sem_filtros .st-key-cp_sem_hdr_producto > [data-testid="stElementContainer"] {
            width: 100% !important;
        }
        /* A la altura de las pildoras de granularidad, que en esta fila
           miden 32px (no 22: `cp_sem_fila` no comparte las reglas de
           `... fila button` — ver el aviso de mas arriba). El default de un
           `st.selectbox` es 40, y los 8px de diferencia se veian como un
           escalon en la fila.

           OJO CON EL SELECTOR (medido, 2026-09-02, y sigue valiendo): en
           esta version de Streamlit el combobox NO es
           `[data-baseweb="select"]` sino `.react-aria-ComboBox`. */
        .st-key-cp_sem_hdr_familia .react-aria-ComboBox,
        .st-key-cp_sem_hdr_subfamilia .react-aria-ComboBox,
        .st-key-cp_sem_hdr_proveedor .react-aria-ComboBox,
        .st-key-cp_sem_hdr_producto .react-aria-ComboBox {
            min-height: 32px !important;
            height: 32px !important;
        }
        /* Y LA CAJA QUE SE VE, que no es la de arriba (2026-09-20,
           regla #477). La
           regla de acá arriba achicaba el ENVOLTORIO y el escalón seguía
           en pantalla: reportado como «que los casilleros de los filtros
           tengan el mismo alto que los selectores Día/Semana/Mes…».
           Medido en el navegador: `.react-aria-ComboBox` daba 32 —la regla
           sí entraba— pero su hijo directo, el div con el borde y el fondo
           blanco, medía 40 y SOBRESALÍA 8px de su padre, que es lo que se
           ve y lo que estiraba la fila a 40. El alto de ese div lo pone su
           contenido: el `<input>` mide 38 (22 de línea + 8+8 de padding)
           más 1+1 de borde.

           Por eso van los tres: la caja a 32, y el input y el botón de la
           flecha a 30 (32 menos los dos bordes) con el padding vertical en
           cero. Al hijo se llega por `> div` y no por su clase, que es
           generada (`st-emotion-cache-…`) y cambia con la versión. */
        .st-key-cp_sem_hdr_familia .react-aria-ComboBox > div,
        .st-key-cp_sem_hdr_subfamilia .react-aria-ComboBox > div,
        .st-key-cp_sem_hdr_proveedor .react-aria-ComboBox > div,
        .st-key-cp_sem_hdr_producto .react-aria-ComboBox > div {
            min-height: 32px !important;
            height: 32px !important;
        }
        .st-key-cp_sem_hdr_familia .react-aria-ComboBox input,
        .st-key-cp_sem_hdr_subfamilia .react-aria-ComboBox input,
        .st-key-cp_sem_hdr_proveedor .react-aria-ComboBox input,
        .st-key-cp_sem_hdr_producto .react-aria-ComboBox input,
        .st-key-cp_sem_hdr_familia .react-aria-ComboBox > div > button,
        .st-key-cp_sem_hdr_subfamilia .react-aria-ComboBox > div > button,
        .st-key-cp_sem_hdr_proveedor .react-aria-ComboBox > div > button,
        .st-key-cp_sem_hdr_producto .react-aria-ComboBox > div > button {
            height: 30px !important;
            min-height: 30px !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        .st-key-cp_sem_hdr_familia .react-aria-ComboBox input,
        .st-key-cp_sem_hdr_subfamilia .react-aria-ComboBox input,
        .st-key-cp_sem_hdr_proveedor .react-aria-ComboBox input,
        .st-key-cp_sem_hdr_producto .react-aria-ComboBox input {
            font-size: 12px !important;
        }
        /* DESDE EL 2026-10-10 SON `st.multiselect` (regla #623), y el de
           Streamlit tiene DOS formas, como en la fila de Ventas › Por
           período (`estilos/_80_cards.py`, regla #519): en la 1.64 de Cloud
           es el `.react-aria-ComboBox` de arriba, pero con las fichas en un
           `stMultiSelectTagsContainer` de 38px con relleno, que estiraba la
           caja otra vez a 40; en la 1.59 de esta máquina es un
           `[data-baseweb="select"]`. Las dos a los 32 de la fila. Lo que no
           entra en un renglón se recorta —la lista abierta dice todo lo
           elegido, y el título de la figura lo cuenta—: una caja que crece
           con cada ficha correría el gráfico de abajo. */
        .st-key-cp_sem_hdr_familia [data-testid="stMultiSelectTagsContainer"],
        .st-key-cp_sem_hdr_subfamilia [data-testid="stMultiSelectTagsContainer"],
        .st-key-cp_sem_hdr_proveedor [data-testid="stMultiSelectTagsContainer"],
        .st-key-cp_sem_hdr_producto [data-testid="stMultiSelectTagsContainer"] {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            height: 30px !important;
            min-height: 0 !important;
            align-items: center !important;
            overflow: hidden !important;
        }
        .st-key-cp_sem_hdr_familia [data-baseweb="select"] > div,
        .st-key-cp_sem_hdr_subfamilia [data-baseweb="select"] > div,
        .st-key-cp_sem_hdr_proveedor [data-baseweb="select"] > div,
        .st-key-cp_sem_hdr_producto [data-baseweb="select"] > div {
            min-height: 32px !important;
            height: 32px !important;
            font-size: 12px !important;
        }
        .st-key-cp_sem_hdr_familia [data-baseweb="select"] > div > div,
        .st-key-cp_sem_hdr_subfamilia [data-baseweb="select"] > div > div,
        .st-key-cp_sem_hdr_proveedor [data-baseweb="select"] > div > div,
        .st-key-cp_sem_hdr_producto [data-baseweb="select"] > div > div {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            max-height: 30px !important;
            overflow: hidden !important;
        }
        /* ── LA LÍNEA DE DOCUMENTO Y MONTOS (2026-10-10, regla #624) ─────
           Una fila propia debajo de la cabecera: rótulo + toggle, dos
           veces, y una nota a la derecha. Más baja que la cabecera (26px)
           porque es secundaria y la paga la figura
           (`alturas.FRANJA_DOC_SEMANAL`). Acotado a SUS keys. */
        .st-key-cp_sem_doc_fila {
            gap: 8px !important;
            align-items: center !important;
            flex-wrap: wrap !important;
        }
        .st-key-cp_sem_doc_fila > [data-testid="stElementContainer"],
        .st-key-cp_sem_doc_fila > [data-testid="stLayoutWrapper"] {
            width: auto !important;
            flex: 0 0 auto !important;
        }
        .cp-sem-doc-rot {
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--text-muted);
            white-space: nowrap;
        }
        .cp-sem-doc-rot-2 { margin-left: 10px; }
        /* El `margin-bottom: -16px` de un `st.markdown` con HTML de bloque
           (regla #162) dejaba su contenedor en 0,8px y el rótulo colgando
           8px por debajo del centro de los botones (medido). Acá no hay
           gap vertical que comerse: la fila es horizontal. */
        .st-key-cp_sem_doc_fila [data-testid="stMarkdownContainer"] {
            margin-bottom: 0 !important;
        }
        .cp-sem-doc-nota {
            font-size: 11px;
            color: var(--text-muted);
            white-space: nowrap;
            margin-left: 6px;
        }
        .st-key-compras_sem_documento [data-testid="stButtonGroup"] button,
        .st-key-compras_sem_montos [data-testid="stButtonGroup"] button {
            min-height: 26px !important;
            height: 26px !important;
            padding: 0 10px !important;
            font-size: 11.5px !important;
        }
        /* ── LA GRANULARIDAD, UN TOGGLE LINEAL (2026-09-17) ─────────────
           Era `st.pills`; pasó a `st.segmented_control` a pedido («agrupado
           en un solo toggle que se vea lineal»). Acotado a SU key y no a
           `cp_sem_filtros`: el aviso de CLAUDE.md sobre reglas del
           contenedor. A los 32px de los dos desplegables de al lado. */
        .st-key-compras_sem_gran [data-testid="stButtonGroup"] button {
            min-height: 32px !important;
            height: 32px !important;
            padding: 0 12px !important;
            font-size: 12px !important;
        }
        /* ── LA FILA QUE ELIGE QUÉ SE VE ABAJO (2026-09-19, regla #476) ──
           Detalle/Resumen a la izquierda y, al lado, el caption que nombra
           el ámbito — que hasta hoy vivía al pie de la tarjeta y ahora es
           el título de las tablas. Comparten renglón para que la fila
           cueste 10px de figura y no 47 (`alturas.FRANJA_MODO_SEMANAL`).

           El toggle a los mismos 32px que el de la granularidad: son el
           mismo widget haciendo el mismo trabajo, uno arriba y otro abajo
           de la figura. El caption, centrado contra él y sin el
           `margin-bottom: -16px` de la regla #162, que en una fila flex
           deja de ser un margen de abajo y se vuelve un desbalance. */
        .st-key-compras_sem_modo [data-testid="stButtonGroup"] button {
            min-height: 32px !important;
            height: 32px !important;
            padding: 0 12px !important;
            font-size: 12px !important;
        }
        .st-key-cp_sem_pie { align-items: center !important; }
        .st-key-cp_sem_pie [data-testid="stMarkdownContainer"] {
            margin-bottom: 0 !important;
        }
        /* UN IFRAME ES INLINE, y por eso se apoya en la línea base: debajo
           le queda el hueco del descendente. Medido: la grilla de Resumen
           pedía 191px y su contenedor daba 198.6, y esos 7.6 se le sumaban
           a la tarjeta. Las dos grillas del modo Detalle no lo tienen
           porque viven dentro de un `st.columns`, que es flex — y en un
           flex los hijos dejan de ser inline. Acá la grilla es hija de un
           bloque normal, así que se le dice `block` a mano. */
        .st-key-cp_sem_resumen .stCustomComponentV1 {
            display: block !important;
        }
        /* ── EL RENGLÓN DEL TÍTULO DEL GRÁFICO (2026-10-08, regla #620) ──
           El título, el selector «Partir por» y la leyenda de las partes,
           ENCIMA de la figura: en sus 30px de margen de arriba, que eran
           del título de Plotly, así que no le agregan un píxel a la
           tarjeta. Lo que sale del flujo es el `stLayoutWrapper` que
           envuelve a la key —el item del flex es él, regla #272—, y un
           hijo `absolute` de un flex no cobra el `gap`. El `right` deja
           libre la esquina donde Plotly pone su barrita de zoom y foto
           (224px medidos a 1323).

           VA POR DEBAJO DEL GRÁFICO, MENOS EL SELECTOR. Sin `z-index`, el
           gráfico —que viene después— se pinta encima, y como su fondo es
           transparente el renglón se sigue viendo; así el cuadro del hover
           tapa al título y a la leyenda y no al revés (con el renglón
           encima, las fichas de la leyenda se pintaban sobre la primera
           línea del hover). Pero el `div.svg-container` de Plotly cubre la
           figura entera y se queda con los clics: medido, el del selector
           no llegaba. Por eso el selector, y sólo él, sube con su propio
           `z-index` — el envoltorio no arma un contexto de apilamiento, así
           que compite directo con el gráfico. */
        .st-key-cp_sem_graf { position: relative !important; }
        .st-key-cp_sem_graf
            > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_sem_cab_graf) {
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            right: 232px !important;
            width: auto !important;
            height: 30px !important;
        }
        .st-key-cp_sem_cab_graf {
            height: 30px !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            gap: 14px !important;
            overflow: hidden !important;
        }
        /* El selector no cede; el título y la leyenda sí (con «…» el
           título, recortada la leyenda: el hover nombra todas las partes). */
        .st-key-cp_sem_cab_graf > [data-testid="stElementContainer"] {
            width: auto !important;
            flex: 0 1 auto !important;
            min-width: 0 !important;
        }
        .st-key-cp_sem_cab_graf > .st-key-compras_sem_partir {
            flex: 0 0 auto !important;
            position: relative !important;
            z-index: 3 !important;
        }
        /* El título mide lo suyo hasta el 40 % del renglón: con cinco
           proveedores la leyenda parte en dos y, sin este tope, el que
           cedía primero era el título («Compra por sema…»). */
        .st-key-cp_sem_cab_graf > [data-testid="stElementContainer"]:first-child {
            flex: 0 0 auto !important;
            max-width: 40% !important;
        }
        .st-key-cp_sem_cab_graf [data-testid="stMarkdownContainer"] {
            margin-bottom: 0 !important;
        }
        /* El título, como lo escribía Plotly: 16px y sin negrita. */
        .st-key-cp_sem_cab_graf .cp-sem-tit {
            font-size: 16px;
            font-weight: 400;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-left: 4px;
        }
        /* El sufijo del título («· sin IGV», regla #621), más chico y gris:
           dice cómo mide la barra, no qué es. */
        .st-key-cp_sem_cab_graf .cp-sem-tit small {
            font-size: 12px;
            color: var(--text-secondary);
            margin-left: 4px;
        }
        /* LAS FICHAS QUE ELIGEN QUÉ SE RESALTA (regla #621), en el lugar
           de la leyenda. Suben con el selector por encima del gráfico, que
           si no se come sus clics (ver arriba), y no parten renglón: lo que
           no entra se recorta y el hover nombra todas las partes. La key
           lleva la firma de sus opciones, de ahí el `[class*=...]` — afuera
           de todo `:has()`. */
        .st-key-cp_sem_cab_graf > [class*="st-key-compras_sem_res_"] {
            position: relative !important;
            z-index: 3 !important;
            overflow: hidden !important;
        }
        /* El que envuelve es el `div` de ADENTRO del `stButtonGroup`, que es
           `block` (medido: con la regla sólo en éste, cinco subfamilias
           salían en dos renglones de 52px). */
        [class*="st-key-compras_sem_res_"] [data-testid="stButtonGroup"],
        [class*="st-key-compras_sem_res_"] [data-testid="stButtonGroup"] > div {
            flex-wrap: nowrap !important;
            overflow: hidden !important;
            gap: 6px !important;
        }
        [class*="st-key-compras_sem_res_"] [data-testid="stButtonGroup"] button {
            min-height: 24px !important;
            height: 24px !important;
            padding: 0 10px !important;
            font-size: 11.5px !important;
            border-radius: 999px !important;
            white-space: nowrap !important;
            flex: 0 0 auto !important;
        }
        [class*="st-key-compras_sem_res_"] button[aria-checked="true"] {
            background: var(--accent) !important;
            border-color: var(--accent) !important;
            color: var(--bg-card) !important;
        }
        [class*="st-key-compras_sem_res_precio"] button[aria-checked="true"] {
            background: var(--danger) !important;
            border-color: var(--danger) !important;
        }
        [class*="st-key-compras_sem_res_"] button[aria-checked="true"] p {
            color: var(--bg-card) !important;
        }
        /* Más chico que los toggles de la cabecera (32px): manda sobre el
           gráfico, no sobre la tarjeta, y tiene que entrar en los 30px. */
        .st-key-compras_sem_partir [data-testid="stButtonGroup"] button {
            min-height: 24px !important;
            height: 24px !important;
            padding: 0 10px !important;
            font-size: 11.5px !important;
        }
        /* En el celular el renglón vuelve al flujo y parte en dos: no hay
           ancho para las tres cosas en uno, y encima tapaban las barras. */
        @media (max-width: 768px) {
            .st-key-cp_sem_graf
                > [data-testid="stLayoutWrapper"]:has(> .st-key-cp_sem_cab_graf) {
                position: static !important;
                height: auto !important;
            }
            .st-key-cp_sem_cab_graf {
                height: auto !important;
                flex-wrap: wrap !important;
            }
            /* Con el renglón partido, el título tiene el suyo entero. */
            .st-key-cp_sem_cab_graf
                > [data-testid="stElementContainer"]:first-child {
                max-width: none !important;
            }
        }
        /* (Acá vivía la fila de KPI de la vista, `.st-key-cp_sem_kpi`,
           regla #454. Se quitó el 2026-10-01, a pedido: la tabla de
           Resumen ya da el total y lo de cada familia. Sus 38px son de la
           figura: `alturas.FRANJA_KPI_SEMANAL`.) */
        /* El TITULO cede, el control no. El `min-width: 0` no es
           decorativo: sin el, un flex item nunca se encoge por debajo de
           su contenido, asi que un nombre largo empujaria al control fuera
           de la tarjeta en vez de truncar. */
        .st-key-cp_rank_fila > [data-testid="stElementContainer"]:first-child,
        .st-key-cp_prod_fila > [data-testid="stElementContainer"]:first-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            width: auto !important;
        }
        .st-key-cp_rank_fila .cp-rank-tit,
        .st-key-cp_prod_fila .cp-prod-rank-tit {
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            margin: 0 !important;
        }
        .st-key-cp_rank_fila .st-key-cp_rank_escala,
        .st-key-cp_prod_fila .st-key-cp_prod_escala,
        .st-key-cp_sem_fila .st-key-cp_sem_escala {
            flex: 0 0 auto !important;
        }
        /* (Acá vivía el bloque `position: absolute; top:16px; right:18px`
           de `cp_prod_fila`, con su `width: fit-content` para no estirarse.
           Se fue el 2026-09-02: la fila entró en el flujo, arriba.) */
        .st-key-cp_rank_fila [data-testid="stElementContainer"],
        .st-key-cp_prod_fila [data-testid="stElementContainer"],
        .st-key-cp_sem_fila [data-testid="stElementContainer"] {
            width: auto !important;
        }
        .st-key-cp_rank_fila [data-testid="stElementToolbar"],
        .st-key-cp_prod_fila [data-testid="stElementToolbar"],
        .st-key-cp_sem_fila [data-testid="stElementToolbar"],
        .st-key-cp_vol_fila [data-testid="stElementToolbar"] {
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
        /* La MISMA pildora, pero en Semanal colgada de la key del trigger
           y no de la fila: ahi el otro hijo de la fila es el
           `stButtonGroup` de la granularidad, que tiene su propio look de
           toggle y no quiere ser cinco pildoras blancas. Se repite en vez
           de sumarse al selector de arriba justamente por eso. */
        .st-key-cp_sem_escala button,
        .st-key-cp_vol_escala button {
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
        .st-key-cp_sem_escala button:hover,
        .st-key-cp_vol_escala button:hover {
            background: #f0edfe !important;
            color: #4d3fb3 !important;
        }
        /* El trigger del selector de fecha: desde el 2026-08-26 su label
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
        .st-key-cp_prod_escala button,
        .st-key-cp_sem_escala button,
        .st-key-cp_vol_escala button {
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
        .st-key-cp_rank_escala button > div > div:last-child:not(:first-child),
        .st-key-cp_sem_escala button > div > div:last-child:not(:first-child),
        .st-key-cp_vol_escala button > div > div:last-child:not(:first-child) {
            display: none !important;
        }

        /* El PANEL. `stPopoverBody` es un PORTAL: se dibuja al final del
           body, fuera de la tarjeta —por eso escapa su `overflow: hidden
           auto`— y por eso hay que alcanzarlo con `:has()` en vez de
           colgarlo del contenedor. Mismo patron que el panel de fecha de
           la franja (estilos/_50_fecha.py) y el del asistente. */
        [data-testid="stPopoverBody"]:has(.st-key-cp_rank_escala_panel),
        [data-testid="stPopoverBody"]:has(.st-key-cp_prod_escala_panel),
        [data-testid="stPopoverBody"]:has(.st-key-cp_sem_escala_panel),
        [data-testid="stPopoverBody"]:has(.st-key-cp_vol_escala_panel) {
            /* El ancho lo pone el panel (graficos/panel_fecha.css, regla
               #616). Hasta el 2026-10-08 iba fijo en 290px, el mínimo útil
               del riel de la escala de tiempo que el panel reemplazó. */
            width: auto !important;
            min-width: 0 !important;
            padding: 12px 14px !important;
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
        .st-key-chartcard_prov_prods,
        .st-key-chartcard_prov_docsprov { position: relative; }
        /* MATAR TODO espacio vertical entre header y gráfico: Streamlit
           inyecta gap en stVerticalBlock + margins en cada stElementContainer
           (uno para el markdown del título, otro para el plotly). */
        /* `chartcard_prov_docsprov` (la tarjeta de Documentos, 2026-10-01,
           regla #578) entra a las cuatro reglas de compactación del Panel A:
           sin ellas su título caía 13px más abajo que el de las tarjetas
           vecinas (15px de padding y 32 de cabecera, contra 2 y 22). */
        .st-key-chartcard_prov_prods,
        .st-key-chartcard_prov_prods [data-testid="stVerticalBlock"],
        .st-key-chartcard_prov_docsprov,
        .st-key-chartcard_prov_docsprov [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            row-gap: 0 !important;
        }
        .st-key-chartcard_prov_prods [data-testid="stElementContainer"],
        .st-key-chartcard_prov_prods [data-testid="stMarkdownContainer"],
        .st-key-chartcard_prov_prods [data-testid="stPlotlyChart"],
        .st-key-chartcard_prov_docsprov [data-testid="stElementContainer"],
        .st-key-chartcard_prov_docsprov [data-testid="stMarkdownContainer"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Reducir el padding interior de la card (era 15px por defecto). */
        .st-key-chartcard_prov_prods,
        .st-key-chartcard_prov_docsprov {
            padding: 2px 12px 8px 12px !important;
        }
        /* Cabecera compacta: se reduce min-height y padding vertical para
           acercar la tabla al título.
           El `padding-right` era 200px: la reserva para los dos grupos de
           pastillas que flotaban acá (Rango/Selección y Top 5/10/20). Se
           fueron el 2026-09-11 —la tarjeta obedece al selector de fecha de
           arriba y lista todos los productos— y con ellos la reserva, que
           le comía al título 200 de sus ~560px por nada. Ver regla #378. */
        /* 2026-10-01: la reserva VUELVE, por otras pastillas — las de
           modo de las dos tarjetas (`cp_modo_*`: «Total del rango | Por
           mes» y «Por documento | Por mes», regla #579), que flotan en
           este renglón a la derecha. Y la cabecera pasa a BLOQUE, porque el
           `ellipsis` de `.chart-card-hdr` sólo recorta un bloque (ver el
           mismo hallazgo en la del Panel B, regla #317). */
        .st-key-chartcard_prov_prods .chart-card-hdr,
        .st-key-chartcard_prov_docsprov .chart-card-hdr {
            padding: 0 196px 0 4px;
            min-height: 22px;
            margin: 0 !important;
            font-size: 13px;
            line-height: 22px;
            display: block;
            border-bottom: none;
        }
        /* Las PASTILLAS DE MODO de Productos y Documentos (`cp_modo_*`,
           2026-10-01, regla #579). Heredan el look de las «Año actual |
           Todo» de la tarjeta «Proveedores de», que se fue ese día: tabs de
           texto con subrayado, flotando a la derecha de la fila del
           título. Wildcard por FAMILIA a propósito: son exactamente esas
           dos, y fuera de un `:has()` no cuesta nada (regla #469). */
        div[class*="st-key-cp_modo_"] {
            position: absolute; top: 0; right: 12px; z-index: 5;
            height: 24px; display: flex; align-items: center;
            width: auto !important;
        }
        /* La medida de los Productos «por período» (regla #579) va un
           renglón más abajo que las otras pastillas: en el de la NOTA, que
           le reserva su lugar a la derecha (`.cp-modo-nota.con-medida`). */
        div[class*="st-key-cp_modo_"].st-key-cp_modo_medida {
            top: 22px; height: 18px;
        }
        .st-key-cp_modo_medida [data-testid="stButtonGroup"] > div {
            gap: 10px !important;
        }
        .st-key-cp_modo_medida [data-testid="stButtonGroup"] button {
            min-height: 18px !important; height: 18px !important;
            font-size: 10.5px !important;
        }
        .cp-modo-nota.con-medida { padding-right: 190px; }
        /* En la fila del título y a la derecha: el título cede (ellipsis,
           con la reserva de `padding-right` de su cabecera) y las pastillas
           no se mueven. Por debajo de 900px bajan a un renglón propio (el
           `@media` del bloque de MÓVIL, al final). */
        div[class*="st-key-cp_modo_"] > div { width: auto !important; }
        div[class*="st-key-cp_modo_"] [data-testid="stElementToolbar"] { display: none; }
        div[class*="st-key-cp_modo_"] [data-testid="stButtonGroup"] button {
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
        div[class*="st-key-cp_modo_"] [data-testid="stButtonGroup"] {
            border: none !important;
            border-radius: 0 !important;
            background: transparent !important;
            overflow: visible !important;
        }
        /* El gap REAL va en el hijo directo del stButtonGroup (que es
           display:block), no en el grupo — mismo hallazgo que en Ventas y
           Familia. Sin capsula que los una, el aire es lo unico que separa
           una opcion de la otra. */
        div[class*="st-key-cp_modo_"] [data-testid="stButtonGroup"] > div {
            gap: 14px !important;
            flex-wrap: nowrap !important;
        }
        div[class*="st-key-cp_modo_"] [data-testid="stButtonGroup"] button[data-variant="pills"] {
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
        div[class*="st-key-cp_modo_"] [data-testid="stButtonGroup"]
            button[data-variant="pills"][data-selected="true"] {
            border-bottom-color: var(--accent) !important;
            color: var(--accent-deep) !important;
            font-weight: 600 !important;
        }
        div[class*="st-key-cp_modo_"] [data-testid="stButtonGroup"]
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
            /* Sin margen: desde el 2026-09-09 esta fila vive dentro de
               `cp_evo_cab` (arriba), que es quien separa la cabecera del
               gráfico. */
            margin: 0 !important; padding: 0 !important;
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
        /* La medida de la Evolución (Soles / Cantidad / Precio, regla #579):
           «Cantidad» es la más larga, 74px con su chevron. */
        .st-key-cp_evo_ctrl .st-key-evo_medida { width: 78px !important; }
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
            display: flex; flex-direction: column; gap: 0;
            margin: 2px 0 4px;
            /* Sin techo propio desde el 2026-10-01: la lista vive adentro
               del desplegable de su producto, y el que scrollea es la
               tabla de productos entera (`.cp-pl-lista`). Hasta ese día
               era la tarjeta «Proveedores de» y se capaba al alto de la
               tabla de al lado (`--cp-prov-alto-paneles`). Regla #579. */
        }
        .pb-cards::-webkit-scrollbar { width: 6px; }
        .pb-cards::-webkit-scrollbar-thumb {
            background: var(--scroll-thumb);
            border-radius: 3px;
        }
        /* FILA, no tarjeta (2026-09-11, a pedido: «estas tarjetas son
           muy grandes»). Cada proveedor entra en un renglón de ~28px con
           lo que se mira de un vistazo —nombre, precio unitario y última
           compra— y el resto (la cantidad con su unidad, y el total) vive
           en un `<details>` que se abre al clic. Antes eran 78px por
           proveedor —dos líneas más una grilla de 4 métricas—, de los que
           entraban 3 de 11 en el panel; ahora entran 10.

           POR QUÉ `<details>` Y NO JS: `st.markdown` no ejecuta `<script>`
           (CLAUDE.md), así que un desplegable con JS no era opción. El
           nativo no lo necesita y además NO pasa por el server: abre al
           instante, en vez de esperar los 3-6s de un rerun. Verificado
           contra Streamlit real — el sanitizer deja pasar
           `<details>`/`<summary>`. Ver regla #377. */
        .pb-row {
            border-bottom: 0.5px solid var(--border);
            border-left: 2px solid transparent;
        }
        .pb-row:last-child { border-bottom: none; }
        /* Verde del precio más bajo. Es el mismo hex que ya tenía la
           tarjeta: `--success` (#16a34a) es un tono más claro y sobre
           blanco pierde contraste en un cuerpo de 12.5px. */
        .pb-row.is-min { border-left-color: #15803d; }
        .pb-row > summary {
            display: grid;
            grid-template-columns: 9px minmax(0, 1fr) auto auto 10px;
            align-items: center; gap: 7px;
            padding: 6px 8px;
            cursor: pointer; position: relative; list-style: none;
            /* El `line-height: 1.6` de Streamlit se hereda como NUMERO, asi
               que un cuerpo de 12.5px se lleva 20px de renglon y la fila
               mide 32px en vez de 27 — medido en la app. En una lista de 17
               proveedores eso son 85px, o sea una fila y media que se deja
               de ver. */
            line-height: 1.25;
        }
        /* Las dos líneas hacen falta: `list-style` mata el marcador
           estándar y el pseudo de -webkit el de los Chrome viejos. Sin
           esto queda el triangulito nativo pisando el swatch de color. */
        .pb-row > summary::-webkit-details-marker { display: none; }
        .pb-row > summary:hover { background: var(--bg-primary); }
        /* BARRA DE PESO — el total dejó el renglón colapsado y la lista
           sigue ordenada por él: sin una señal, el orden queda sin
           explicación a la vista. Va de FONDO porque así no cuesta ancho,
           que es justo lo que no sobra en un panel de 337px. */
        .pb-row .peso {
            position: absolute; left: 0; top: 0; bottom: 0;
            background: var(--accent-tint); z-index: 0;
        }
        .pb-row > summary > *:not(.peso) { position: relative; z-index: 1; }
        .pb-row .sw { width: 9px; height: 9px; border-radius: 2px; }
        .pb-row .name {
            color: var(--text-primary); font-size: 12.5px;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .pb-row .pu {
            color: var(--text-primary); font-size: 12.5px; font-weight: 500;
            font-variant-numeric: tabular-nums;
        }
        .pb-row .pu.pu-min { color: #15803d; }
        .pb-row .fec {
            color: var(--text-secondary); font-size: 11.5px;
            font-variant-numeric: tabular-nums;
        }
        /* Chevron dibujado con dos bordes de una caja de 5px, rotados.
           No es un carácter: un «⌄» de texto cambia de forma con la
           fuente y no se puede rotar con `transform`. */
        .pb-row > summary::after {
            content: ""; width: 5px; height: 5px; justify-self: end;
            border-right: 1.5px solid var(--text-muted);
            border-bottom: 1.5px solid var(--text-muted);
            transform: translateY(-2px) rotate(45deg);
            transition: transform 0.15s;
        }
        .pb-row[open] > summary::after {
            transform: translateY(1px) rotate(-135deg);
        }
        .pb-row .mas {
            display: flex; gap: 16px; font-size: 12px;
            line-height: 1.25;
            padding: 4px 8px 7px 25px;
            background: var(--accent-tint);
        }
        .pb-row .mas .cell {
            display: flex; align-items: baseline; gap: 5px; min-width: 0;
        }
        .pb-row .mas .lab {
            color: var(--text-muted); text-transform: uppercase;
            letter-spacing: 0.03em; font-size: 10.5px; flex-shrink: 0;
        }
        .pb-row .mas .val {
            color: var(--text-primary); font-variant-numeric: tabular-nums;
        }
        .pb-row .mas .val.tot {
            color: var(--accent-deep); font-weight: 500;
        }


        /* ── PRODUCTOS: la tabla con los proveedores desplegables ───────────
           2026-10-01 (regla #579). Era una AgGrid y su tarjeta hermana,
           «Proveedores de», mostraba los proveedores del producto
           clickeado. Ahora es HTML: una FILA por producto que es el
           `<summary>` de un `<details>`, y adentro, la lista de proveedores
           con las mismas filas `.pb-row` de aquella tarjeta. Las columnas
           y el look copian a la tabla del Ranking de al lado (24px por
           fila, nombre en violeta, la barra de valor pintada detrás del
           monto hasta el 62 %). */
        .cp-modo-nota {
            font-size: 11px; color: var(--text-secondary);
            line-height: 18px; height: 18px; padding: 0 4px;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .cp-pl, .cp-pm { font-size: 12px; line-height: 1.25; }
        /* El TOTAL al pie de la tabla de Documentos: la fila TOTAL del
           Ranking (lavanda, negrita, violeta oscuro), fuera de la grilla
           porque `st.dataframe` no tiene fila fija. Regla #579. */
        .cp-docs-total {
            display: flex; justify-content: space-between; align-items: center;
            height: 22px; margin-top: 2px; padding: 0 10px;
            background: var(--accent-tint); color: var(--accent-deep);
            font-size: 12px; font-weight: 700; border-radius: 4px;
            font-variant-numeric: tabular-nums;
        }
        .cp-pl-head, .cp-pl-row > summary {
            display: grid; align-items: center; column-gap: 8px;
            grid-template-columns: minmax(0, 1.5fr) minmax(0, 1.3fr) 40px 52px 56px 10px;
        }
        .cp-pl-head, .cp-pm-head, .cp-dl-head {
            height: 28px; padding: 0 8px;
            font-size: 11.5px; color: var(--text-secondary);
            border-top: 3px solid var(--border);
            border-bottom: 1px solid var(--border);
        }
        .cp-pl-head .r, .cp-pm-head .r, .cp-dl-head .r { text-align: right; }
        .cp-pl-lista {
            overflow-y: auto; overflow-x: hidden;
        }
        .cp-pl-lista::-webkit-scrollbar { width: 6px; }
        .cp-pl-lista::-webkit-scrollbar-thumb {
            background: var(--scroll-thumb); border-radius: 3px;
        }
        .cp-pl-row { border-bottom: 1px solid var(--border); }
        .cp-pl-row > summary {
            height: 24px; padding: 0 8px; cursor: pointer; list-style: none;
            color: var(--accent-deep);
        }
        .cp-pl-row > summary::-webkit-details-marker { display: none; }
        .cp-pl-row > summary:hover { background: var(--bg-primary); }
        .cp-pl-row[open] > summary { background: var(--accent-tint); }
        /* El producto EN FOCO —el que dibuja la Evolución de abajo— lleva
           el nombre en negrita y un filete de acento a la izquierda, en las
           dos vistas de la tabla. Regla #579. */
        .cp-pl-row.foco > summary,
        .cp-pm-fila.foco { box-shadow: inset 3px 0 0 var(--accent); }
        .cp-pl-row.foco > summary .nm,
        .cp-pm-fila.foco .nm { font-weight: 700; }
        .cp-pm-fila { cursor: pointer; }
        .cp-pm-fila:hover { background: var(--bg-primary); }
        .cp-pm-fila.foco { background: var(--accent-tint); }
        /* El relevo del clic (`cp_prov_prod_relevo`): invisible pero
           PRESENTE, como los botones `pila_go_` de estilos/_27_pila.py — un
           widget con `display:none` no existe para Streamlit. */
        .st-key-cp_prov_prod_relevo {
            position: absolute !important;
            width: 1px !important; height: 1px !important;
            overflow: hidden !important; opacity: 0 !important;
            margin: 0 !important; padding: 0 !important;
        }
        .cp-pl-row .nm {
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .cp-pl-row .vb {
            position: relative; height: 100%;
            display: flex; align-items: center; justify-content: flex-end;
        }
        .cp-pl-row .vb .bar {
            position: absolute; left: 0; top: 0; bottom: 0;
            background: var(--accent);
        }
        .cp-pl-row .vb .v {
            position: relative; color: var(--text-primary);
            font-variant-numeric: tabular-nums;
        }
        .cp-pl-row .n { text-align: right; font-variant-numeric: tabular-nums; }
        .cp-pl-row .um { white-space: nowrap; overflow: hidden; }
        /* El chevron, como el de las filas `.pb-row`: dos bordes de una
           caja de 5px, girados. */
        .cp-pl-row > summary::after {
            content: ""; width: 5px; height: 5px; justify-self: end;
            border-right: 1.5px solid var(--text-muted);
            border-bottom: 1.5px solid var(--text-muted);
            transform: translateY(-2px) rotate(45deg);
            transition: transform 0.15s;
        }
        .cp-pl-row[open] > summary::after {
            transform: translateY(1px) rotate(-135deg);
            border-color: var(--accent);
        }
        .cp-pl-provs {
            padding: 4px 0 6px 18px;
            background: var(--bg-primary);
            border-top: 1px solid var(--border);
        }
        /* Las filas de los proveedores, MÁS DELGADAS que la del producto
           que las abre (2026-10-01, a pedido, con captura: «deben ser más
           delgadas que la del mismo producto, ahora están más gruesas»).
           Heredadas de la tarjeta «Proveedores de» medían ~28px —6 de
           padding arriba y abajo y un cuerpo de 12.5— contra los 24 de la
           fila del producto, y lo que cuelga de una fila se leía más
           importante que ella. Acá van a 19px y más chicas: se leen como
           el detalle de su producto. Sólo DENTRO del despliegue
           (`.cp-pl-provs`), regla #579. */
        .cp-pl-provs .pb-row > summary {
            padding: 0 8px; height: 19px; gap: 6px;
        }
        /* Y MENOS NOTORIAS (2026-10-01, segunda vuelta, con captura: «me
           parecen más notorios que el producto»). Además de delgadas:
           texto GRIS y no negro, un punto más chico, el precio sin
           negrita y la barra de peso a media tinta. El producto conserva su violeta y sus 12px: la
           jerarquía la da el contraste, no sólo el alto. El verde del
           precio más bajo se queda —es la señal de la lista—, pero sin
           negrita como los demás. */
        .cp-pl-provs .pb-row .name {
            font-size: 11.5px; color: var(--text-secondary);
        }
        .cp-pl-provs .pb-row .pu {
            font-size: 11.5px; font-weight: 400; color: var(--text-secondary);
        }
        .cp-pl-provs .pb-row .pu.pu-min { color: var(--success-text); }
        .cp-pl-provs .pb-row .fec { font-size: 11px; color: var(--text-muted); }
        .cp-pl-provs .pb-row .peso { opacity: 0.5; }
        .cp-pl-provs .pb-row .sw { width: 7px; height: 7px; }
        .cp-pl-provs .pb-row > summary:hover .name,
        .cp-pl-provs .pb-row > summary:hover .pu { color: var(--text-primary); }
        .cp-pl-provs .pb-row .mas { padding: 2px 8px 4px 22px; font-size: 10.5px; }
        .cp-pl-sub, .cp-pl-todo > summary {
            font-size: 10px; letter-spacing: 0.03em; text-transform: uppercase;
            color: var(--text-muted); padding: 2px 8px; line-height: 16px;
        }
        .cp-pl-vacio { font-size: 11.5px; color: var(--text-muted); padding: 2px 8px 6px; }
        .cp-pl-todo > summary {
            cursor: pointer; list-style: none; color: var(--accent);
        }
        .cp-pl-todo > summary::-webkit-details-marker { display: none; }
        .cp-pl-todo > summary::before { content: "+ "; }
        .cp-pl-todo[open] > summary::before { content: "− "; }

        /* ── PRODUCTOS POR PERÍODO: cómo varió cada uno ─────────────────
           Mismo renglón de 24px. Cada celda de período lleva un fondo
           violeta tanto más fuerte cuanto más se compró en ella (`--t`,
           contra el mayor de SU fila); la tendencia es una tira de
           barritas, y la variación va en rojo si subió el gasto y en verde
           si bajó — el código de color de todo Compras. */
        .cp-pm-head, .cp-pm-fila {
            display: grid; align-items: center; column-gap: 2px;
            grid-template-columns: minmax(0, 1.4fr) 54px
                repeat(var(--n), minmax(0, 1fr)) 66px;
        }
        .cp-pm-fila {
            height: 24px; padding: 0 8px;
            border-bottom: 1px solid var(--border);
        }
        .cp-pm-fila .nm {
            color: var(--accent-deep);
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .cp-pm-fila .sp {
            display: flex; align-items: flex-end; gap: 2px;
            height: 16px; padding-right: 8px;
        }
        .cp-pm-fila .sp i {
            flex: 1 1 0; background: var(--accent); border-radius: 1px;
        }
        .cp-pm-fila .sp i.z { background: var(--border); }
        .cp-pm-fila .c {
            height: 100%; display: flex; align-items: center;
            justify-content: flex-end; padding-right: 6px;
            font-variant-numeric: tabular-nums; color: var(--text-primary);
            background: color-mix(in srgb, var(--accent) var(--t), transparent);
        }
        .cp-pm-fila .c.z { color: var(--text-muted); }
        .cp-pm-fila .var {
            text-align: right; font-size: 11.5px; font-weight: 600;
            color: var(--text-secondary); font-variant-numeric: tabular-nums;
        }
        .cp-pm-fila .var.sube, .cp-dl .var.sube { color: var(--danger-text); }
        .cp-pm-fila .var.baja, .cp-dl .var.baja { color: var(--success-text); }
        /* La unidad al lado del nombre, en Cantidad y Precio. */
        .cp-pm-fila .nm small {
            margin-left: 5px; font-size: 10px; font-weight: 400;
            color: var(--text-muted);
        }

        /* ── DOCUMENTOS: la tabla que se despliega ──────────────────────
           2026-10-01 (regla #579). Era un `st.dataframe`; pasó a HTML para
           que cada fila se abra: un documento en sus productos (cantidad,
           precio unitario y valor) y un período en sus documentos (fecha,
           número, filas y total). El renglón es de 26px —el que tenía en
           `st.dataframe` era de 28— y lo de adentro va como las filas de
           proveedores de Productos: más chico y en gris, porque es el
           detalle de la fila que lo abre. */
        .cp-dl { font-size: 12px; line-height: 1.25; }
        .cp-dl-doc .cp-dl-head, .cp-dl-doc .cp-dl-row > summary {
            display: grid; align-items: center; column-gap: 8px;
            grid-template-columns: 62px minmax(0, 1fr) 40px 76px 70px 10px;
        }
        .cp-dl-per .cp-dl-head, .cp-dl-per .cp-dl-row > summary {
            display: grid; align-items: center; column-gap: 8px;
            grid-template-columns: minmax(0, 1fr) 44px 90px 70px 10px;
        }
        .cp-dl-head .ayuda {
            cursor: help; text-decoration: underline dotted;
            text-underline-offset: 3px;
        }
        .cp-dl-row { border-bottom: 1px solid var(--border); }
        .cp-dl-row > summary {
            height: 26px; padding: 0 8px; cursor: pointer; list-style: none;
            color: var(--text-primary); font-variant-numeric: tabular-nums;
        }
        .cp-dl-row > summary::-webkit-details-marker { display: none; }
        .cp-dl-row > summary:hover { background: var(--bg-primary); }
        .cp-dl-row[open] > summary { background: var(--accent-tint); }
        .cp-dl-row .nm {
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .cp-dl-row .r, .cp-dl-lin .r { text-align: right; }
        .cp-dl .var { text-align: right; font-size: 11.5px; font-weight: 600;
                      color: var(--text-secondary); }
        .cp-dl-row > summary::after {
            content: ""; width: 5px; height: 5px; justify-self: end;
            border-right: 1.5px solid var(--text-muted);
            border-bottom: 1.5px solid var(--text-muted);
            transform: translateY(-2px) rotate(45deg);
            transition: transform 0.15s;
        }
        .cp-dl-row[open] > summary::after {
            transform: translateY(1px) rotate(-135deg);
            border-color: var(--accent);
        }
        .cp-dl-det {
            padding: 2px 0 4px 16px;
            background: var(--bg-primary);
            border-top: 1px solid var(--border);
        }
        .cp-dl-lin {
            display: grid; align-items: center; column-gap: 8px;
            grid-template-columns: minmax(0, 1fr) 72px 72px 64px;
            height: 19px; padding: 0 8px;
            font-size: 11.5px; color: var(--text-secondary);
            font-variant-numeric: tabular-nums;
            border-bottom: 0.5px solid var(--border);
        }
        .cp-dl-lin:last-child { border-bottom: none; }
        .cp-dl-lin.per {
            grid-template-columns: 62px minmax(0, 1fr) 40px 76px;
        }
        .cp-dl-lin.cab {
            font-size: 10px; letter-spacing: 0.03em; text-transform: uppercase;
            color: var(--text-muted); height: 18px;
        }
        .cp-dl-lin .nm {
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        /* Una tarjeta ANGOSTA saca la Tendencia y le da su lugar al nombre
           del producto. Es el ancho de la TARJETA, no el de la ventana: la
           misma ventana deja la tarjeta en ~580px con la columna de la
           izquierda fija y en ~450 con ella plegada, así que un `@media` no
           distingue los dos casos (regla #317). Las barritas repiten lo que
           ya dicen los números de al lado; el nombre no lo dice nadie más.
           Va AL FINAL del bloque: `.cp-pm-fila .sp` pesa lo mismo y, antes,
           le ganaba por orden (medido: la cabecera perdía la columna y las
           filas no, y la grilla salía corrida). */
        .st-key-chartcard_prov_prods {
            container-type: inline-size;
            container-name: cpprods;
        }
        @container cpprods (max-width: 480px) {
            .cp-pm-head, .cp-pm-fila {
                grid-template-columns: minmax(0, 1.4fr)
                    repeat(var(--n), minmax(0, 1fr)) 62px;
            }
            .cp-pm .sp { display: none; }
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
            0% { opacity: 0; transform: translateY(-8px); }
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
        /* Bloque paneles: entra deslizando desde la izquierda. Antes sólo
           existía al enfocar un proveedor; desde 2026-09-03 los paneles se ven
           siempre, así que la animación corre una vez al montar la vista. */
        @keyframes unfoldRight {
            0% { opacity: 0; transform: translateX(-14px); }
            100% { opacity: 1; transform: translateX(0); }
        }
        /* 2026-08-21: eran UNA tarjeta (`compras_prov_card_paneles`) y pasaron
           a ser DOS bloques hermanos, uno por columna, para que caigan sobre
           la misma grilla que la fila de arriba. La animación se aplica a los
           dos: entran juntos, que es lo que hacía la tarjeta única. */
        .st-key-compras_prov_card_docsprov,
        .st-key-compras_prov_card_prods {
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
           · Productos y Documentos viven en dos columnas que colapsan a una
             recién por debajo de ~640px. ENTRE 640 y 900px cada tarjeta es
             media pantalla y su título + las pastillas de modo ya no caben
             en la cabecera → el fix de `cp_modo_*` aplica desde 900px.
           · El gráfico principal (y su win_nav / floats de tope) es de ancho
             completo: solo se aprieta de verdad por debajo de ~640px.
           ══════════════════════════════════════════════════════════════ */
        @media (max-width: 900px) {
            /* Pastillas de modo de Productos y Documentos: bajo el título. */
            div[class*="st-key-cp_modo_"] {
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

        /* 2026-09-27: se fue el `.st-key-fecha_ajuste_pill { display: none }`
           del 2026-08-23, que escondía el pill de fecha de la franja en este
           drill. Ese pill no existe en Compras desde el 2026-09-06 (`app.py`
           no llama a `franja_fecha.render()` en Compras), y la regla, sin
           contenedor, apagaba el ÚNICO que queda: el de la tarjeta de
           Documentos SUNAT, que es la misma key. Este CSS sigue en la
           página mientras corre la vista siguiente (Streamlit borra lo
           viejo al TERMINAR la corrida). Ver `arquitectura.md` regla #457. */

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
           no pelea con nada.

           2026-09-02: de este bloque queda el comentario. El `static` y el
           `margin` los declara ahora el bloque compartido con
           `cp_rank_fila`, mas arriba, y el `width: fit-content` tuvo que
           IRSE — llegaba despues y le ganaba al `width: 100%` de aquel, o
           sea la fila medía lo que su contenido y el `space-between` no
           tenia hueco que repartir: el rango quedaba pegado al titulo en
           vez de al borde derecho de la tarjeta. */
        /* El CHEVRON de Streamlit, mismo trato que en `cp_rank_escala`: se
           esconde el WRAPPER y no el glifo (apagar solo el span deja su
           div padre ocupando 16px y el boton sigue desbordando). Esta
           regla no se pudo generar duplicando la de arriba porque su
           selector se parte en varias lineas. */
        .st-key-cp_prod_escala button > div > div:last-child:not(:first-child) {
            display: none !important;
        }

        </style>
"""


def clonar_prefijo(css, origen, destino, extra=()):
    """Las reglas de `css` que nombran `origen`, reescritas para `destino`.

    Por que existe. Las dos tarjetas que ya usan `selector_fecha_tarjeta`
    + `filtro_proveedores` -Ranking de proveedores (`cp_rank`) y Ranking
    de productos (`cp_prod`)- tienen su CSS listado EXPLICITO, prefijo por
    prefijo, sin wildcards por familia (el aviso de CLAUDE.md). Son 41
    reglas donde los dos nombres aparecen apareados.

    El 2026-09-04 se pidio el mismo par de controles para una TERCERA
    tarjeta (Detalle de documentos por proveedor). Con dos prefijos, pegar
    el tercero a mano en 41 grupos es tedioso; con tres deja de ser
    sostenible, y sobre todo abre lo que este repo ya escarmento dos veces:
    dos sitios donde arreglar el proximo detalle. Es el mismo argumento que
    llevo el popover de proveedores a `_comun.py::filtro_proveedores` y el
    selector de fecha a `base.py::selector_fecha_tarjeta`, aplicado al CSS.

    Clonar en vez de generalizar el selector es a proposito: la promesa de
    "nada de wildcards" se mantiene -lo que sale son selectores literales,
    uno por regla- y el prefijo nuevo hereda cualquier retoque futuro de su
    modelo sin que nadie se acuerde de copiarlo.

    Como parsea, y por que alcanza con esto: recorre contando llaves y
    SALTA los bloques de at-rule (`@media`, `@container`, `@keyframes`)
    enteros. Verificado sobre este fichero el 2026-09-04: las 41 reglas con
    `cp_prod` estan todas en el nivel de arriba, ninguna adentro de un
    at-rule. Si algun dia una se muda a un `@media`, esta funcion la ignora
    en silencio -- de ahi la guarda de `test_graficos.py`, que cuenta
    cuantas clona.

    `extra` son pares `(de, a)` que se aplican DESPUES del prefijo: hoy solo
    la clase del titulo, que no sigue la convencion de las keys
    (`cp-prod-rank-tit` es de Productos; el clon usa la generica
    `cp-rank-tit`).
    """
    fuera = []
    pila_at = []      # True por cada nivel de llaves que es un at-rule
    cabeza = []       # texto acumulado desde la ultima llave
    regla = []        # la regla que se esta copiando, si toca
    for ch in css:
        if ch == "{":
            txt = "".join(cabeza)
            sel = _selector(txt)
            es_at = sel.startswith("@")
            if not es_at and not any(pila_at) and origen in sel:
                regla = [sel, " {"]
            pila_at.append(es_at)
            cabeza = []
        elif ch == "}":
            if regla:
                regla.append("}")
                fuera.append("".join(regla))
                regla = []
            if pila_at:
                pila_at.pop()
            cabeza = []
        else:
            cabeza.append(ch)
            if regla:
                regla.append(ch)
    fuera = [_solo_de(sel_cuerpo, origen) for sel_cuerpo in fuera]
    fuera = [r for r in fuera if r]
    txt = ("\n").join(fuera)
    txt = txt.replace(origen, destino)
    for de, a in extra:
        txt = txt.replace(de, a)
    return txt


def _partir_selectores(sel):
    """`sel` partido por comas, ignorando las que van dentro de `(...)`.

    `:has(> .x)` no trae comas hoy, pero `:is(a, b)` si las traeria y
    partir a lo bruto rompe el selector en dos mitades invalidas.
    """
    partes, buf, prof = [], [], 0
    for ch in sel:
        if ch == "(":
            prof += 1
        elif ch == ")":
            prof -= 1
        if ch == "," and prof == 0:
            partes.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    partes.append("".join(buf))
    return [x.strip() for x in partes if x.strip()]


def _solo_de(regla, origen):
    """La misma regla con SOLO los selectores que nombran `origen`.

    Sin esto el clon se lleva puestos los selectores hermanos: las reglas
    de este fichero agrupan `cp_rank`, `cp_prod` y `cp_sem` en la misma
    lista, asi que clonar una tal cual re-declara tambien las otras dos —
    al FINAL de la hoja, o sea pisando cualquier regla posterior que las
    hubiera sobrescrito. El clon tiene que hablar solo de su prefijo.
    """
    cabeza, _, cuerpo = regla.partition("{")
    quedan = [x for x in _partir_selectores(cabeza) if origen in x]
    if not quedan:
        return ""
    return (",\n").join(quedan) + " {" + cuerpo

def _selector(txt):
    """El selector que precede a una `{`: lo que sigue al ultimo comentario.

    Un selector puede ocupar VARIAS lineas (los hay con `:has(...)` partido
    en dos), asi que quedarse con la ultima no alcanza. Lo que si es fiable
    es que el comentario de arriba termina en `*/` y que despues de eso ya
    no hay nada que no sea selector.
    """
    resto = txt.rsplit("*/", 1)[-1]
    lineas = [ln.strip() for ln in resto.split("\n") if ln.strip()]
    return ("\n").join(lineas)


# -- El tercer prefijo: la tarjeta «Detalle de documentos por proveedor» --
# Pedido 2026-09-04 ("anadamos el selector de fecha, asi como el filtro
# minimalista de proveedor"). Sus controles son los MISMOS componentes que
# los de las otras dos tarjetas, asi que su CSS tambien: se clona del de
# Productos, que es el que ya tiene las dos piezas (fecha + filtro de
# proveedores) y ninguna regla propia de su grafico.
#
# OJO desde el 2026-09-12: el Ranking de productos YA NO TIENE filtro de
# proveedores (se pidió fuera de esa sección, regla #382), pero las reglas
# `cp_prod_prov_*` de este fichero se quedan a propósito. Son el MOLDE: de
# ellas sale todo el CSS del filtro de «Detalle de documentos»
# (`cp_docs_prov_*`), que sigue vivo. Parecen muertas —ningún `.py` dibuja
# ya una key `cp_prod_prov`— y borrarlas por limpieza deja ese filtro sin
# estilo, sin error y en otra sección. Si algún día molestan, el arreglo es
# mudar el molde a `cp_docs` y dejar de clonar, no borrar.
CSS_CP_DOCS = clonar_prefijo(
    CSS, "cp_prod", "cp_docs",
    extra=(("cp-prod-rank-tit", "cp-rank-tit"),))
CSS = CSS.replace("        </style>",
                  CSS_CP_DOCS + "\n        </style>")


# ── El AgGrid del ranking de proveedores ────────────────────────────
# Se estila por las VARIABLES del tema (`--ag-*`) y no por selectores
# propios, por una razon medida y no por gusto: `theme="streamlit"` declara
# las suyas dentro de un `:where(.ag-theme-params-1)`, y `:where()` tiene
# especificidad CERO. O sea que cualquier regla nuestra le gana sin un solo
# `!important`, y de paso se mueve la misma palanca que usa el tema en vez
# de pelearle sus reglas una por una.
CSS_RANKING_GRID = {
    ".ag-root-wrapper": {
        # ── El ALTO, que no es decorativo ────────────────────────────
        # Sin esto el wrapper computa `height: auto` y mide TODO su
        # contenido, se desborda del contenedor que el componente
        # dimensiono con el `height=` de Python, y st_aggrid le reporta a
        # Streamlit ese alto desbordado: el iframe sale con un
        # `style.height` inline que pisa su propio atributo `height`.
        #
        # Medido el 2026-09-13 en Inventario > Por area, que es donde se
        # vio: Python pedia 255px (8 filas), el iframe salia con
        # `height="255"` y `style="height: 508px"` — las 21 areas
        # completas—, y su tarjeta media 554 contra los 308 de las dos
        # vecinas. El grid de al lado, con el MISMO codigo y menos filas,
        # computaba 255: por eso se leia como un problema de datos y no de
        # CSS. Reportado como "veo que es mas larga verticalmente".
        #
        # Va en el dict COMPARTIDO y no en el llamador: cualquier
        # tabla-ranking con `height=` fijo tiene el mismo agujero, y las
        # que hoy andan bien ya miden 100% — ponerselo no les cambia nada.
        "height": "100% !important",
        "max-height": "100% !important",
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
        # ── 2026-09-09: el marco, copiado del modo diseno ────────────
        # La tabla deja de ser una CAJA y pasa a ser una franja: se van
        # los bordes de los costados y quedan dos lineas de 3px, arriba y
        # abajo, del mismo gris que ya separa las filas. Con los lados
        # abiertos la tabla respira dentro de la tarjeta en vez de
        # dibujar un recuadro adentro de otro (la tarjeta ya trae el
        # suyo, redondeado).
        "border-top": f"3px solid {GRIS_LINEA_GRILLA} !important",
        "border-bottom": f"3px solid {GRIS_LINEA_GRILLA} !important",
        "border-right": "none !important",
        "border-left": "none !important",
        # Sin lineas verticales: lo que separa una columna de la otra es
        # el aire, igual que en el pivote de Documentos de mas abajo.
        # Estas dos variables gobiernan la cabecera (que la dibuja el
        # tema) y el cuerpo; a las celdas las apaga el `border-right` de
        # mas abajo.
        "--ag-header-column-border": "none",
        "--ag-column-border": "none",
        # La linea que el TEMA dibuja sobre el contenedor de la fila
        # fijada. La otra mitad —la que Python escribia inline sobre la
        # fila— se saco de `_js_fila_total` en proveedor.py, que es el
        # sitio limpio: eran dos lineas apiladas de distinto color.
        "--ag-pinned-row-border": "none",
    },
    # 2026-09-09, a pedido (llego como captura del modo diseno): el texto de
    # las celdas en violeta, no en el gris casi negro del tema.
    #
    # SIN `!important`, y NO es un olvido -- es lo que hace que la tabla
    # quede como en la captura. Las dos excepciones que se ven ahi salen
    # gratis solo mientras esta regla sea normal:
    #
    #   · La columna "Valor" sigue OSCURA. Su color lo pone `_js_barra`
    #     (proveedor.py) como `cellStyle`, o sea un estilo INLINE sobre la
    #     celda. Un inline le gana a una regla normal y pierde contra una
    #     con `!important`: poniendoselo, los montos se irian a violeta
    #     encima de sus propias barras.
    #   · La fila TOTAL conserva su paleta. Su color es inline sobre la
    #     FILA (`_js_fila_total`), asi que las celdas lo heredan -- y la
    #     herencia pierde contra cualquier regla que apunte a la celda.
    #     Por eso hace falta el selector de abajo, que le gana a este por
    #     especificidad sin necesitar `!important` tampoco.
    #
    # Alcanza a Proveedor, Docs y % (las tres columnas sin cellStyle).
    ".ag-cell": {"color": ACENTO_TEXTO},
    # Misma pareja de selectores que usa el modo diseno para la fila de
    # cierre (`.ag-row-pinned, .ag-row-footer`): esta tabla arma su TOTAL
    # con `pinnedBottomRowData`, pero el dia que alguna use el total nativo
    # el `footer` ya esta cubierto.
    ".ag-row-pinned .ag-cell, .ag-row-footer .ag-cell": {
        "color": ACENTO_TEXTO_OSCURO},
    ".ag-cell, .ag-header-cell": {"border-right": "none !important"},
    # El separador de filas queda EXPLICITO aunque hoy coincida con el
    # default del tema: es el que le da la escala al marco de 3px de
    # arriba (uno es el triple del otro, no dos grosores sueltos).
    ".ag-row": {"border-bottom": f"1px solid {GRIS_LINEA_GRILLA} !important"},
}
# OJO, para el que venga a bajar estos nombres a minuscula por CSS: ya se
# intento y no se puede. Aca vivio un `text-transform: lowercase` sobre la
# columna de nombres, y duro horas: el pedido no era "minuscula" sino
# "minuscula pero como NOMBRE PROPIO", y eso CSS no lo hace sobre un texto
# que ya viene en mayusculas -- `capitalize` no baja el resto de la palabra,
# y dos `text-transform` no se encadenan sobre el mismo texto. Lo resuelve
# `_etiquetas_proveedor.nombre_propio`, que ademas es pura y testeable.


# ── La cabecera del pivote de Documentos ────────────────────────────
# Ese grid era el UNICO AgGrid del repo que se dibujaba sin `custom_css`:
# los demas pasan por `tablas/_css.py` o por `CSS_RANKING_GRID`, y este se
# habia quedado con el `theme="streamlit"` tal cual salio de fabrica. Se
# noto por lo que pesaba la cabecera, medido en el navegador el 2026-09-06:
#
#   · 77px de cabecera (dos niveles de 38) contra 23px de fila de dato,
#     o sea 3,3 filas gastadas en rotular.
#   · rotulos en 12px `bold` (700) -- el MISMO cuerpo que el dato, pero en
#     negrita, que es lo que la hacia leerse mas fuerte que la tabla.
#   · una linea vertical entre cada par de columnas, en los dos niveles.
#
# Se estila por las VARIABLES del tema por la misma razon medida que
# `CSS_RANKING_GRID` (ver el comentario de arriba): `theme="streamlit"`
# declara las suyas dentro de un `:where(...)`, que tiene especificidad
# CERO, asi que alcanza con redeclararlas.
#
# Lo que este dict NO toca son los ALTOS: salen de `headerHeight` y
# `groupHeaderHeight` en el `gridOptions`, porque el marco del iframe se
# dimensiona en Python a partir de esos mismos numeros. Cambiarlos aca
# desincronizaria las dos mitades -- misma trampa que ya documenta
# `_ALTO_FILA_PIVOT`.
CSS_PIVOTE_DOCS = {
    ".ag-root-wrapper": {
        "--ag-header-background-color": BLANCO,
        # Lo que separa una columna de la otra en la cabecera es el mismo
        # aire que las separa en el cuerpo. La linea de abajo (una sola,
        # la de `.ag-header`) alcanza para que siga leyendose cabecera.
        "--ag-header-column-border": "none",
        "--ag-header-row-border": "none",
        "--ag-header-font-size": "11px",
        "--ag-header-font-weight": "500",
        "--ag-header-text-color": GRIS_TEXTO_MEDIO,
    },
    ".ag-header": {"border-bottom": f"1px solid {GRIS_BORDE} !important"},
}
