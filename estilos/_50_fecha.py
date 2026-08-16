"""estilos._50_fecha - Pill de fecha del header, para TODOS los reportes.

Fecha a la izquierda (pill sólido color acento) + chips centrados con
fondo blanco es el comportamiento por DEFECTO en desktop (min-width:901px)
desde 2026-08-04 — antes solo corría en Compras/Ajuste via overrides
:has() por separado; se generalizó porque los 8 reportes comparten los
mismos containers (fila_ajuste_top, fecha_ajuste_pill, chips_ajuste_tabla,
ver app.py). El estilo "tab" original (degradado + borde inferior) es la
regla BASE de este módulo, y desde 2026-08-05 solo se ve en la franja
769-900px: móvil (<=768px) replica el pill sólido acento en _99_movil.py
con sus propias medidas (34px de alto en vez de 28px — allá no hay chips
vecinos con los que emparejar). Si algún día se cubre esa franja de tablet,
la regla base queda muerta.

2026-08-07: el `top:3px` del bloque desktop (antes 8px) — Compras lo
estrenó para su franja de 34px, gustó, y se universalizó junto con el
alto de la franja (ver _40_ajuste_franja.py::before, también 34px ahora
en los 8 reportes). Antes de esto el bloque desktop solo tocaba
left/right/transform/max-width; top:8px venía sin tocar de la regla BASE
de arriba (pensada para la franja "tab" de 769-900px, no para el pill
sólido de escritorio). Si se vuelve a tocar la altura de la franja,
recordar que top:3px y esa altura están acoplados — no cambiar una sin
la otra (ver arquitectura.md regla #17).

Compras, Inventario Valorizado y Salidas comparten un addendum propio
(scopeado :has(.st-key-app_reporte_<slug>), uno por reporte): min-width:230px
en sus chips porque los tres saben que tienen EXACTAMENTE 2 chips de filtro
(Compras: Familia/Subfamilia; Inventario: Área/Familia; Salidas: Sub
Almacén/Familia — el toggle de Métrica de Salidas no es un chip-popover, así
que el selector `[data-testid="stPopover"] button` no lo alcanza y queda
afuera). El resto de reportes deja que los chips midan su contenido —
pueden ser más de 2 (ej. Ajuste con Área/Familia/Ajuste/Ajuste Valorizado,
o Ventas con Grupo/Sub Grupo/Canal/Servicio) y forzar un ancho fijo ahí
desbordaría. Ninguno usa la key del rail (compras_tabs_row) — esa es
compartida entre reportes y filtraba mal. Ver arquitectura.md regla #16.
Antes de sumar un reporte nuevo a esta lista: contar cuántos
`st.popover(...)` de chip tiene en su franja — si son más de 2, NO
agregarlo (ver regla #21 en arquitectura.md).

2026-08-09: los chips dejaron de ir CENTRADOS en el ancho util y pasaron a
ir pegados a la derecha del pill de fecha (left fijo de 391px). Para que
ese numero sea estable el pill tomo ANCHO FIJO (210px) y el label se
abrevio en app.py::_fmt_rango_es. Son tres piezas de un mismo cambio — el
left de los chips, el ancho del pill y el formato del label — y tocar una
sola rompe la alineacion. Va junto con la barra tintada de
_40_ajuste_franja.py (5ta vuelta) y el top:6px de los dos contenedores
fijos (antes 3px, por la barra de 40px en vez de 34px).

2026-08-09, 2da pasada del mismo dia: el pill dejo de ser RELLENO acento y
paso a OUTLINE (fondo blanco, borde de 1.5px, texto --accent-deep, icono
acento, radio de 4px como los chips). Con la barra ya tintada, el relleno
solido era el unico bloque lleno de la pantalla y chocaba con el resto de
controles, que son todos outline. Movil NO se toco a proposito: alla el
pill sigue siendo solido acento (ver _99_movil.py) porque esta solo en la
barra, sin chips outline al lado con los que desentonar, y el relleno le
da mejor area de toque visual. Es la primera vez que movil y escritorio
divergen en el ASPECTO del pill, no solo en las medidas.

Extraido de estilos.py (lineas 1084-1280 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* FECHA EN EL HEADER — texto del rango a la DERECHA de la franja,      */
    /* alineado con el borde derecho de la tarjeta (padding-right: 138px    */
    /* en Compras). Es el TRIGGER de un popover: atajos + calendario.       */
    /* =================================================================== */
.st-key-fecha_ajuste_pill {
    position: fixed !important;
    top: 8px !important;
    left: auto !important;
    right: calc(var(--rail-der-res) - 15px) !important;  /* borde de la tarjeta */
    width: fit-content !important;
    z-index: 23 !important;
    margin: 0 !important;
}

    /* Trigger: anula la regla GLOBAL de pill (BOTÓN FILTROS, arriba) SOLO
       aquí → texto sobre tinte violeta claro (gradient que sube desde
       la base) + barra sólida 2px acento pegada al borde INFERIOR de
       la franja. Se lee como "pestaña activa" muy sutil. min-height =
       --cab-altura - top(8px) + box-sizing border-box → el border
       aterriza justo en el borde de la franja en todos los reportes. */
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
        box-sizing: border-box !important;
        min-width: 0 !important;
        padding: 0 18px !important;
        border: none !important;
        border-bottom: 3px solid #534AB7 !important;
        border-radius: 6px 6px 0 0 !important;
        background: linear-gradient(to top,
            #C7C0F5 0%, rgba(199,192,245,0) 78%) !important;
        box-shadow: none !important;
        color: #1B1745 !important;
        font-weight: 800 !important;
        font-size: 22px !important;
        letter-spacing: -0.01em !important;
        line-height: 1.15 !important;
        white-space: nowrap !important;
        min-height: calc(var(--cab-altura) - 8px) !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    /* Icono material (calendar_month) del popover: color acento + tamano */
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
        color: #534AB7 !important;
        font-size: 22px !important;
    }
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button:hover {
        border: none !important;
        border-bottom: 2px solid #534AB7 !important;
        background: linear-gradient(to top,
            #DED9FA 0%, rgba(222,217,250,0) 70%) !important;
        color: var(--accent-deep) !important;
    }
    .st-key-fecha_ajuste_pill [data-testid="stPopover"] button[aria-expanded="true"] {
        border-bottom: 2px solid #26215C !important;
        background: linear-gradient(to top,
            #DED9FA 0%, rgba(222,217,250,0) 75%) !important;
    }
    /* ================================================================== */
    /* DESKTOP (todos los reportes): fecha a la IZQUIERDA como pill        */
    /* OUTLINE (reemplaza el "tab" de arriba; era relleno acento hasta la  */
    /* 2da pasada del 2026-08-09) + chips pegados a su derecha, también    */
    /* outline. Ver docstring del módulo — por qué es el default y por qué */
    /* Compras tiene su propio addendum más abajo.                         */
    /*                                                                     */
    /* Selectores con clase duplicada (.st-key-X.st-key-X) para subir la   */
    /* especificidad por encima de la regla "tab" de arriba SIN depender   */
    /* del orden de fuente dentro del archivo (mismo idioma que ya usaba   */
    /* el reset móvil de Compras). Todo el bloque va detrás de un          */
    /* min-width:901px — abajo de eso no se toca nada (el móvil de cada    */
    /* reporte sigue como estaba, con la posición de _99_movil.py).        */
    /* ================================================================== */
    @media (min-width: 901px) {
        /* top:3px (antes 8px, heredado de la regla base de arriba): antes
           SOLO Compras lo tenía, junto con su franja de 34px (el default
           de 50px no lo necesitaba — con top:8px sobraban 14px abajo). El
           2026-08-07 se universalizaron LOS DOS JUNTOS (acá el top, en
           _40_ajuste_franja.py::before el alto de 34px) porque el look
           más ceñido de Compras gustó más que el margen suelto del
           default viejo. No se probó top:3px solo contra la franja de
           50px — van acoplados, no cambiar uno sin el otro. Ver docstring
           del módulo y arquitectura.md regla #17. */
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill {
            /* (46px de barra - 2px de border-bottom - 28px de pill) / 2.
               El borde va DENTRO del alto (el ::before es border-box), por
               eso se resta: sin restarlo salen 4px abajo contra 6 arriba y
               el control se ve apretado contra la línea inferior — fue
               justo el bug de la pasada anterior. Ver _40_ajuste_franja.py. */
            top: 8px !important;
            left: 175px !important;
            right: auto !important;
        }
        /* ANCHO FIJO, no fit-content. Los chips se anclan a la derecha del
           pill con un left: en px (más abajo), y eso solo funciona si el
           ancho del pill NO depende del texto. 210px = el peor caso del
           label abreviado ("30 sep 2025 – 31 dic 2026"); el ellipsis está
           por si algún día vuelve un formato más largo — ver
           app.py::_fmt_rango_es, que documenta el acoplamiento del otro
           lado. Con rangos cortos sobra ancho dentro del pill: se nota
           mucho menos desde que el fondo es blanco (ver abajo) que cuando
           era acento sólido.
           2026-08-09, 2da pasada — OUTLINE, no relleno sólido. El pill
           venía relleno de var(--accent) desde que la franja era casi
           invisible y era lo único que se veía. Con la barra tintada pasó
           a ser el ÚNICO elemento relleno de la pantalla (reportado con
           captura de Compras: "el diseño de la fecha desentona") — los
           chips vecinos y los segmentados del dashboard son todos
           outline, y encima quedaba morado sobre morado contra el fondo
           lavanda de la barra. Ahora comparte el lenguaje de los chips
           (fondo blanco, radio de 4px) y la jerarquía la dan tres cosas
           que NO son el relleno: borde de 1.5px en vez de 1px, icono en
           acento y texto en --accent-deep. El borde sale de mezclar la
           paleta, no de un hex suelto (ver CLAUDE.md § Colores): entre
           --border-lavender (el de los chips) y --accent, más cerca del
           segundo. OJO con el 1.5px: medido en el preview, Chrome a
           DPR=1 lo redondea a 1px (getComputedStyle devuelve "1px"), así
           que en pantallas sin escalado el borde pesa lo MISMO que el de
           los chips y la diferencia la carga el color — por eso la mezcla
           va al 80% de acento y no al 50%. En pantallas con escalado
           (125% de Windows, retina) sí se ve el medio píxel. */
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button {
            min-height: 28px !important;   /* alto real de los chips vecinos (con su borde de 1px) */
            width: 210px !important;
            justify-content: flex-start !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
            padding: 0 12px !important;
            border: 1.5px solid color-mix(in srgb, var(--accent) 80%, var(--accent-light)) !important;
            border-radius: 4px !important;   /* mismo radio que los chips */
            background: #ffffff !important;
            box-shadow: none !important;
            color: var(--accent-deep) !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            letter-spacing: normal !important;
        }
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
            color: var(--accent) !important;
            font-size: 15px !important;
        }
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button:hover {
            border: 1.5px solid var(--accent) !important;
            background: var(--accent-tint) !important;
            color: var(--accent-deep) !important;
        }
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button[aria-expanded="true"] {
            border: 1.5px solid var(--accent-deep) !important;
            background: var(--accent-light) !important;
        }
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button p {
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
        }
        /* Chips PEGADOS a la derecha del pill de fecha, no centrados en el
           ancho útil. El centrado (hasta 2026-08-09) dejaba un hueco muerto
           entre la fecha y los chips que crecía con el monitor — el motivo
           por el que la franja "no se veía" tanto como el fondo blanco.
           391px = 175px (left del pill) + 210px (su ancho fijo) + 6px de
           aire. Los tres números están acoplados: si cambia el left o el
           ancho del pill, este left cambia también. No hay forma de
           resolverlo con flex: fecha y chips viven en contenedores
           Streamlit distintos (app.py vs. el módulo de cada dashboard) y
           los dos son position:fixed. */
        .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
            top: 8px !important;   /* mismo cálculo que el pill, ver arriba */
            left: 391px !important;
            right: auto !important;
            transform: none !important;
            /* Hasta el 2026-08-15 esta cuenta llevaba un sumando más, 255px,
               que le reservaban el sitio a `atajos_franja` — anclado a la
               derecha en esta misma línea y, como los chips, position:fixed,
               así que ninguno empujaba al otro y sin la reserva se
               solapaban entre 901 y 1200px. Los atajos se fueron (están en
               el popover del calendario), así que los chips se quedan con
               ese ancho. */
            max-width: calc(100vw - 391px
                            - (var(--rail-der-res) - 22px)) !important;
        }
        .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button {
            background: #ffffff !important;
            padding-right: 22px !important;
            justify-content: flex-start !important;
        }
        .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button:hover {
            background: var(--accent-tint) !important;
        }
        /* Addendum de los reportes con EXACTAMENTE 2 chips de filtro
           (Compras, Inventario Valorizado, Salidas): ancho uniforme parejo
           al de la fecha. El resto deja que cada chip mida su contenido
           (pueden ser más de 2 — ej. Ajuste con 4, Ventas con 4). */
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_compras)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button,
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_inventario_valorizado)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button,
        [data-testid="stAppViewContainer"]:has(.st-key-app_reporte_salidas)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button {
            min-width: 230px !important;
        }

        /* ============================================================== */
        /* FRANJA PLANA (2026-08-14) — barra de herramientas, no cápsulas  */
        /*                                                                 */
        /* Pedido con una referencia concreta (la barra de TradingView) y  */
        /* con el argumento correcto: cinco cápsulas con borde propio son  */
        /* cinco rectángulos compitiendo, y ninguna distingue un filtro    */
        /* que ESTÁ filtrando de uno que no — el único indicio era el      */
        /* badge del número.                                               */
        /*                                                                 */
        /* No se inventa lenguaje: es el mismo tab-subrayado que ya usan   */
        /* las franjas de control DENTRO de las tarjetas (_80_cards.py,    */
        /* Año Pasado y Compras › Familia). Ahora la franja de arriba y    */
        /* las de adentro hablan igual.                                    */
        /*                                                                 */
        /* El ancho de 210px del pill NO se toca aunque ya no haya         */
        /* cápsula: los chips siguen anclados a `left: 391px` = 175 + 210  */
        /* + 6. Aplanar el aspecto es gratis; soltar el ancho movería esa  */
        /* aritmética de tres números acoplados.                           */
        /* ============================================================== */
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button {
            border: none !important;
            border-radius: 0 !important;
            /* La fecha SIEMPRE filtra: su subrayado es permanente. */
            border-bottom: 2px solid var(--accent) !important;
            background: transparent !important;
            /* Caja al texto: con el `min-height: 28px` que traía, el
               subrayado quedaba ~7px por debajo de la palabra. */
            min-height: 0 !important;
            height: auto !important;
            padding: 1px 6px 1px !important;
            line-height: 1.2 !important;
            font-weight: 600 !important;
            font-size: 13.5px !important;
        }
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button:hover,
        .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill
            [data-testid="stPopover"] button[aria-expanded="true"] {
            border: none !important;
            border-bottom: 2px solid var(--accent-deep) !important;
            background: var(--accent-tint) !important;
        }
        /* Chips: planos y APAGADOS mientras no filtren. */
        .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            border-bottom: 2px solid transparent !important;
            color: var(--text-secondary) !important;
            font-weight: 400 !important;
            min-height: 0 !important;
            height: auto !important;
            padding: 1px 8px 1px 0 !important;
            line-height: 1.2 !important;
        }
        /* ACTIVO: subrayado de acento. Sustituye al relleno sólido de
           _40_ajuste_franja.py (que gana por orden de sección, así que hace
           falta la clase duplicada para pasarle por encima). */
        .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [class*="st-key-chipwrap_"][class*="_on"]
            [data-testid="stPopover"] button {
            background: transparent !important;
            border-bottom: 2px solid var(--accent) !important;
            color: var(--accent-deep) !important;
            font-weight: 600 !important;
        }
        .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button:hover {
            background: var(--accent-tint) !important;
        }
    }

    /* Panel del popover: se renderiza en un portal (fuera del contenedor),
       así que lo scopeamos por el contenedor keyed interno con :has(). */
    [data-testid="stPopoverBody"]:has(.st-key-fecha_panel) {
        min-width: 380px !important;
    }
    /* Botones de atajo: compactos, alineados a la izquierda.
       OJO — esta regla cuelga del CONTENEDOR, así que también captura los
       botones de la lista de CORTES (misma primera columna, ver
       app.py::modo Cortes). Es intencional: los dos son listas de un clic
       y tienen que verse igual. El corte activo se distingue por el
       type="primary" de Streamlit (relleno acento), que esta regla no
       toca. Si algún día hay que diferenciarlos, acotar por key
       (st-key-atajo_ / st-key-corte_), no agregar otra regla al
       contenedor. Ver CLAUDE.md § "grep estilos/ antes de agregar un
       widget". */
    .st-key-fecha_panel [data-testid="stColumn"]:first-child button {
        min-width: 0 !important;
        padding: 6px 10px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }
    /* Segmentado Rango/Corte/Comparar: vive ARRIBA de las columnas, así
       que la regla de los atajos no lo alcanza — se estiliza aparte y
       compacto (3 opciones tienen que entrar en los 380px del panel sin
       partirse en dos filas). */
    .st-key-fecha_panel [data-testid="stButtonGroup"] button {
        padding: 3px 10px !important;
        font-size: 12.5px !important;
    }

    /* =================================================================== */
    /* STEPPER DEL CORTE ACTIVO — ‹ 3/8 · 4 días ›                          */
    /* =================================================================== */
    /* Ocupa el hueco de `right: 138px`, que quedó libre cuando el pill de
       fecha se mudó a `left: 175px` en el bloque de desktop de arriba. NO
       va dentro de .st-key-fecha_ajuste_pill: ese pill tiene ancho FIJO de
       210px y los chips se anclan a `left: 391px` (= 175 + 210 + 6). Meter
       botones ahí adentro rompe esos tres números acoplados.
       Solo se renderiza con un corte activo (app.py), así que aparecer y
       desaparecer no mueve nada más de la franja.
       Oculto por defecto y visible recién a partir de 1400px: entre 901 y
       1400 los chips (que arrancan en 391px y crecen con el reporte) le
       llegarían encima. Abajo de ese ancho la navegación entre cortes vive
       en el panel, que siempre tiene la lista completa. */
    .st-key-fecha_corte_nav {
        display: none !important;
    }
    @media (min-width: 1400px) {
        .st-key-fecha_corte_nav {
            display: block !important;
            position: fixed !important;
            top: 8px !important;
            right: calc(var(--rail-der-res) - 15px) !important;
            left: auto !important;
            width: 176px !important;
            z-index: 23 !important;
            margin: 0 !important;
        }
        .st-key-fecha_corte_nav [data-testid="stHorizontalBlock"] {
            gap: 2px !important;
        }
        .st-key-fecha_corte_nav button {
            min-width: 0 !important;
            width: 100% !important;
            min-height: 28px !important;   /* mismo alto que el pill y los chips */
            padding: 0 !important;
            border: 1.5px solid color-mix(in srgb, var(--accent) 80%, var(--accent-light)) !important;
            border-radius: 4px !important;
            background: #ffffff !important;
            color: var(--accent-deep) !important;
            font-size: 15px !important;
            font-weight: 600 !important;
            line-height: 1 !important;
        }
        .st-key-fecha_corte_nav button:hover:not(:disabled) {
            background: var(--accent-tint) !important;
            border-color: var(--accent) !important;
        }
        .st-key-fecha_corte_nav button:disabled {
            border-color: var(--border) !important;
            color: var(--text-muted) !important;
        }
        /* Etiqueta central: no es un widget, es markdown — se centra a
           mano contra el alto de 28px de los botones vecinos. */
        .corte-nav-etq {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 28px;
            font-size: 12px;
            font-weight: 600;
            color: var(--accent-deep);
            white-space: nowrap;
        }
        .corte-nav-etq span {
            font-weight: 400;
            color: var(--text-secondary);
        }
    }

    /* =================================================================== */
    /* TÍTULO DE VENTAS › COMPARATIVO EN LA FRANJA (2026-08-15)             */
    /*                                                                      */
    /* `ventas_comp_titulo_franja` (graficos/ventas_comparativo.py) vive    */
    /* FUERA de la tarjeta pero se ancla acá con el mismo truco que la      */
    /* fecha/los chips: position:fixed, ajeno a su lugar real en el DOM.    */
    /* Solo esta vista dibuja ese contenedor, así que scopear por su        */
    /* PRESENCIA — vía :has() sobre el prefijo de key que arma `_card()`    */
    /* (graficos/base.py: `chartcard_` + key), o sea                       */
    /* `chartcard_ventas_comparativo_<grano>` — alcanza para no tocar el    */
    /* resto de reportes/vistas. left:175px = el mismo punto donde          */
    /* arrancaba el pill de fecha antes de este cambio; el pill y los       */
    /* chips se corren a la derecha lo que el título reserva (260px +       */
    /* 16px de aire) SOLO en esta vista — los otros 7 reportes (y el        */
    /* resto de Ventas) no lo ven.                                          */
    /* Los tres números de abajo (título:260, pill:451, chips:667) son la   */
    /* MISMA cadena acoplada de siempre (ver el bloque de arriba): mover    */
    /* uno sin los otros dos rompe la alineación.                           */
    /* 260px (no 380: el ancho del título más largo) es a propósito — Ventas */
    /* ya tiene 4 chips (Grupo/Sub Grupo/Canal/Servicio, ~430px de contenido */
    /* real) y reservarle al título su ancho completo los hacía chocar: a   */
    /* 1024px de viewport la fila de chips medía menos que su propio        */
    /* contenido (superposición medida en vivo). Con 260px los títulos      */
    /* largos truncan con ellipsis (el `title=` del span da el tooltip      */
    /* completo). Con TODO y eso, el corrimiento sigue sin caber cómodo     */
    /* por debajo de ~1220px (medido: ~410px de contenido de chips contra   */
    /* un max-width que a esa altura ya no alcanza) — por eso el bloque de  */
    /* abajo arranca en 1220px, no en los 901px que usa el resto de la      */
    /* franja: bajo ese umbral el título se oculta y la fecha/chips vuelven */
    /* a su posición de siempre (sin :has(), la regla base de arriba). Sin  */
    /* título en pantallas angostas es mejor que chips ilegibles — mismo    */
    /* criterio que ya usa fecha_corte_nav (oculto hasta 1400px) más abajo. */
    /* =================================================================== */
    .st-key-ventas_comp_titulo_franja {
        position: fixed !important;
        top: 8px !important;
        left: 175px !important;
        width: 260px !important;
        z-index: 22 !important;
        margin: 0 !important;
        display: none !important;   /* oculto por defecto; ver abajo */
    }
    @media (min-width: 1220px) {
        [data-testid="stAppViewContainer"]:has([class*="st-key-chartcard_ventas_comparativo_"])
            .st-key-ventas_comp_titulo_franja {
            display: block !important;
        }
        [data-testid="stAppViewContainer"]:has([class*="st-key-chartcard_ventas_comparativo_"])
            .st-key-ventas_comp_titulo_franja [data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            line-height: calc(var(--cab-altura) - 8px) !important;
            color: var(--text-primary) !important;
        }
        [data-testid="stAppViewContainer"]:has([class*="st-key-chartcard_ventas_comparativo_"])
            .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill {
            left: 451px !important;   /* 175 (título) + 260 (su ancho) + 16 de aire */
        }
        [data-testid="stAppViewContainer"]:has([class*="st-key-chartcard_ventas_comparativo_"])
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
            left: 667px !important;   /* 451 (pill) + 210 (su ancho) + 6, igual que la cuenta base */
            max-width: calc(100vw - 667px - (var(--rail-der-res) - 22px)) !important;
        }
    }

    /* =================================================================== */
    /* TÍTULO DE COMPRAS › FAMILIA EN LA FRANJA (2026-08-16)                */
    /*                                                                      */
    /* Mismo mecanismo que el título de Ventas › Comparativo de arriba —    */
    /* ver ese bloque para el porqué de cada número. Acá se scopea por la   */
    /* PRESENCIA del propio título (`compras_fam_titulo_franja`) en vez del */
    /* key de una tarjeta interna: Compras › Familia no tiene una tarjeta   */
    /* propia distinta del wrapper compartido `ajuste_graf_card_izq_        */
    /* compras` (que usan TODAS las vistas de Compras), así que no hay un   */
    /* key único de tarjeta para anclar el :has() — pero el título sí es    */
    /* único de esta vista, y alcanza igual.                                */
    /* Compras tiene solo 2 chips (Familia/Subfamilia) — MENOS que los 4 de */
    /* Ventas — pero cada uno lleva min-width:230px forzado (ver el         */
    /* addendum de arriba, "Compras/Inventario/Salidas"), así que el        */
    /* contenido real (230+230+8=468px) es MÁS ancho que el de Ventas       */
    /* (~410px sin forzar). Por eso el umbral de abajo es más alto: 1220px  */
    /* no alcanzaba (medido: los 2 chips se superponían), 1310px sí.        */
    /* =================================================================== */
    .st-key-compras_fam_titulo_franja {
        position: fixed !important;
        top: 8px !important;
        left: 175px !important;
        width: 260px !important;
        z-index: 22 !important;
        margin: 0 !important;
        display: none !important;
    }
    @media (min-width: 1310px) {
        [data-testid="stAppViewContainer"]:has(.st-key-compras_fam_titulo_franja)
            .st-key-compras_fam_titulo_franja {
            display: block !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-compras_fam_titulo_franja)
            .st-key-compras_fam_titulo_franja [data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            white-space: nowrap !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            line-height: calc(var(--cab-altura) - 8px) !important;
            color: var(--text-primary) !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-compras_fam_titulo_franja)
            .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill {
            left: 451px !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-compras_fam_titulo_franja)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
            left: 667px !important;
            max-width: calc(100vw - 667px - (var(--rail-der-res) - 22px)) !important;
        }
    }

    /* PROTOTIPO (2026-08-16), 2da vuelta — "fusionar" de verdad, referencia
       Google Finance: NADA de tarjeta (ni sombra ni esquinas, en ningún
       lado), toda la superficie de un color, de borde a borde. La 1ra
       vuelta solo sacaba la línea + esquinas SUPERIORES y dejaba la
       sombra + esquinas inferiores tal cual — el resultado se leía como
       "la franja se ensanchó" (sin nada que marque un límite, no como
       "franja y tarjeta fundidas en una forma"). Acotado a Compras ›
       Familia via :has(). Si gusta, generalizar sacando el :has() (afecta
       a los 8 reportes, son las mismas reglas wildcard que ya documenta
       CLAUDE.md/arquitectura.md). */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_fam_titulo_franja)
        .st-key-fila_ajuste_top::before {
        border-bottom: none !important;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-compras_fam_titulo_franja)
        .st-key-ajuste_graf_card_izq_compras {
        border-radius: 0 !important;
        box-shadow: none !important;
    }
"""
