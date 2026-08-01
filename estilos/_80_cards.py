"""estilos._80_cards - Tarjetas de los dashboards: .chart-card, wrappers ajuste_graf_card_* y bloques compras_prov_card_* del drill de Proveedor.

Extraido de estilos.py (lineas 1345-1498 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* CARDS DE GRÁFICOS — contenedor blanco con bordes redondeados         */
    /* =================================================================== */
    .chart-card {
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.25rem 1.5rem 0.75rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(16, 16, 20, 0.06);
        position: relative;
        padding-bottom: 2.5rem;  /* espacio para el pie */
    }

    .chart-card-title {
        position: absolute;
        left: 0; right: 0; bottom: 0;
        font-size: 11px;
        font-weight: 600;
        color: var(--accent);
        background: var(--accent-tint, #EEEDFE);
        border-top: 1px solid var(--accent, #7F77DD);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 8px 1.5rem;
        margin: 0;
        line-height: 1;
        border-bottom-left-radius: inherit;
        border-bottom-right-radius: inherit;
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

    .streamlit-expanderContent .chart-card {
        border: none !important;
        box-shadow: none !important;
        padding: 0.25rem 0 0 !important;
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
        background: var(--surface-2, #ffffff) !important;
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
        background: var(--surface-2, #ffffff) !important;
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
"""
