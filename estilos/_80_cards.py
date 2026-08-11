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
    div[class*="st-key-ventas_resumen_kpi_"] {
        border-radius: 12px !important;
        padding: 8px 12px !important;
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
        font-size: 15px !important;
        line-height: 1.15 !important;
    }
    div[class*="st-key-ventas_resumen_kpi_"] [data-testid="stMetricLabel"] {
        font-size: 9px !important;
        white-space: nowrap !important;
    }
"""
