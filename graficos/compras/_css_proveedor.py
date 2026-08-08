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
        /* Popover de proveedores flotando arriba-IZQUIERDA (compacto) */
        .st-key-prov_pop_float {
            position: absolute; top: 14px; left: 16px; z-index: 5;
            width: auto !important;
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
           fila, abajo-derecha, flotando (no suman alto a la tarjeta). El
           key de un container SIN borde ES el stVerticalBlock, por eso la
           direccion FILA se fija aqui directo. Los controles tienen sombra
           leve para leerse como "chips apoyados" sobre el grafico, no como
           pills sueltos. */
        .st-key-win_nav {
            position: absolute; bottom: 4px; right: 10px; z-index: 20;
            width: auto !important;
            display: flex !important; flex-direction: row !important;
            align-items: center !important;
            gap: 2px !important;
            padding: 1px 2px !important;
            background: rgba(255,255,255,0.55) !important;
            backdrop-filter: blur(4px);
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
        /* Toggles en la MISMA fila del título, centrados vertical. */
        .st-key-topn_float {
            position: absolute; top: 0; right: 12px; z-index: 20;
            height: 24px; display: flex; align-items: center;
            width: auto !important;
        }
        .st-key-topn_float > div { width: auto !important; }
        .st-key-topn_pills {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            gap: 6px !important;
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

        /* ── Cápsula segmentada: unir las pills en un solo control ── */
        .st-key-gran_float [data-testid="stButtonGroup"],
        .st-key-topn_float [data-testid="stButtonGroup"],
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] {
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
        .st-key-gran_float [data-testid="stButtonGroup"] button,
        .st-key-topn_float [data-testid="stButtonGroup"] button,
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button {
            border: 0 !important;
            border-radius: 0 !important;
            margin: 0 !important;
        }
        .st-key-gran_float [data-testid="stButtonGroup"] button:not(:first-child),
        .st-key-topn_float [data-testid="stButtonGroup"] button:not(:first-child),
        .st-key-panelb_scope_float [data-testid="stButtonGroup"] button:not(:first-child) {
            border-left: 1px solid rgba(49,51,63,0.15) !important;
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
