"""estilos._40_ajuste_franja - Franja superior "cristal esmerilado" (todos
los reportes) y los chips de filtro que viven en ella (Area / Familia /
Ajuste / lo que aplique por reporte).

Extraido de estilos.py (lineas 898-1083 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.

La franja fue transparente por DEFECTO entre 2026-08-04 y 2026-08-06 (antes
de eso solo lo era en Compras/Ajuste via overrides :has() — ver
arquitectura.md regla #16 y el commit que generalizo esto). Se cambio a
"cristal esmerilado" (blanco translucido + backdrop-filter: blur) el
2026-08-06: fecha_ajuste_pill y chips_ajuste_tabla son position:fixed SIN
fondo propio, asi que al hacer scroll quedaban flotando sobre lo que sea
que hubiera debajo (reportado con capturas — se veian "en el aire"). El
blur no necesita JS: al ser la franja position:fixed, el navegador
desenfoca en cada frame lo que este compuesto detras. Fallback en
navegadores sin backdrop-filter: el rgba(255,255,255,.62) de base ya deja
una banda translucida legible, sin blur pero sin romperse. Ver
arquitectura.md regla #17.

Compras tiene su PROPIO override adicional en estilos/_20_compras_rail.py
(achica la franja a 34px) porque ya tiene el rail derecho; el resto de
reportes usa --cab-altura (50px) tal cual. Ese override solo toca height —
el fondo lo hereda de la regla base de aca abajo, asi que Compras recibe
el cristal esmerilado sin duplicar nada.

2026-08-06, 2da vuelta (mismo dia): el cristal esmerilado gusto, pero era
de borde a borde (left:90px a right:0) y dejaba dos zonas SIEMPRE vacias
con fondo blanco encima — antes del pill de fecha (el titulo que viviria
ahi esta oculto por pedido) y despues del cluster de chips (que en
desktop vive centrado, no pegado al borde derecho). Paso de "franja" a
"tarjeta que cuelga del borde superior": left:160px (pegado al pill de
fecha) y right:calc(50vw - 300px) (se angosta hacia el centro, con la
misma logica de centrado que ya usa chips_ajuste_tabla). Ver el comentario
en el bloque CSS de mas abajo para el detalle completo.
"""

CSS = """    /* =================================================================== */
    /* FILA SUPERIOR DE AJUSTE DE INVENTARIO                                */
    /* =================================================================== */
    /* FRANJA "CRISTAL ESMERILADO" — YA NO es de borde a borde (2026-08-06,  */
    /* 2da vuelta): son dos zonas SIEMPRE vacías las que quedaban con fondo  */
    /* blanco sin nada encima — izquierda (90-160px: el título vive acá     */
    /* pero está oculto por pedido, ver app.py::col_titulo) y derecha (todo */
    /* lo que sobra a la derecha del cluster de chips, que en desktop vive  */
    /* centrado, no pegado al borde). Ahora es una tarjeta que CUELGA del   */
    /* borde superior (solo redondea las esquinas de ABAJO) y se angosta   */
    /* hacia el centro en vez de llegar a right:0. `right` usa la MISMA     */
    /* lógica de centrado que ya usa chips_ajuste_tabla en _50_fecha.py     */
    /* (centro ≈ 50vw+11.5px): así la tarjeta se re-centra con el cluster   */
    /* real en vez de quedar a un ancho fijo que se desalinea al cambiar el */
    /* viewport. No es un abrazo píxel-perfecto (el pill de fecha mide      */
    /* distinto según el rango elegido, y eso no se puede leer en CSS puro  */
    /* sin JS) pero deja MUCHO menos aire vacío que antes. Mobile define su */
    /* propio right (ver _99_movil.py) porque este calc() da negativo por   */
    /* debajo de los ~600px de ancho. Ver docstring del módulo y            */
    /* arquitectura.md #17.                                                 */
    .st-key-fila_ajuste_top {
        position: sticky !important;
        top: var(--cab-nivel1-top) !important;
        z-index: 20 !important;
        margin-bottom: 0 !important;
        padding-top: 7px !important;
        padding-bottom: 0 !important;
        margin-top: calc(-1 * var(--cab-offset-contenido)) !important;
    }
    .st-key-fila_ajuste_top::before {
        content: "" !important;
        position: fixed !important;
        top: 0 !important;
        bottom: auto !important;
        left: 160px !important;                  /* pegado al pill de fecha, no al rail */
        right: calc(50vw - 300px) !important;     /* se achica hacia el centro del cluster de chips */
        height: var(--cab-altura) !important;
        border-radius: 0 0 14px 14px !important;  /* cuelga del borde superior: solo esquinas de abajo */
        background: rgba(255, 255, 255, 0.62) !important;
        backdrop-filter: blur(14px) saturate(1.6) !important;
        -webkit-backdrop-filter: blur(14px) saturate(1.6) !important;
        border: 1px solid rgba(230, 230, 235, 0.7) !important;
        border-top: none !important;
        box-shadow: 0 6px 18px rgba(16, 16, 20, 0.10) !important;
        z-index: 0 !important;
    }
    .st-key-fila_ajuste_top > * {
        position: relative !important;
        z-index: 1 !important;
    }
    .st-key-fila_ajuste_top [data-testid="stHorizontalBlock"] {
        align-items: center !important;
        gap: 8px !important;
    }
    .st-key-fila_ajuste_top [data-testid="stColumn"],
    .st-key-fila_ajuste_top [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
    }

    /* Pestañas Gráficos/Tabla DENTRO de la franja (col_titulo): anular el
       margin-top de 6px que las bajaba cuando vivían en su banda propia. */
    .st-key-fila_ajuste_top [class*="st-key-vistatabs_"] [data-testid="stButtonGroup"] {
        margin: 0 !important;
    }
    .st-key-fila_ajuste_top [class*="st-key-vistatabs_"] {
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Pestañas Gráficos/Tabla — ya NO fijas en la franja: ahora fluyen justo
       encima del canvas (se renderizan en app.py antes de _render_contenido).
       Quedan pegadas al borde superior del primer contenedor del contenido. */
    .st-key-ajuste_tabs_top {
        position: relative !important;
        z-index: 5 !important;
        margin: 2px 0 6px 0 !important;
        padding: 0 !important;
    }

    /* ================================================================== */
    /* CHIPS DE FILTRO EN LA FRANJA BLANCA — Área / Familia / Ajuste /     */
    /* Ajuste valor.  Nivel 2, a la derecha del selector de vista.         */
    /* ================================================================== */
    /* Filtros Familia / Subfamilia en el NIVEL 1: pegados a la IZQUIERDA,
       alineados con el borde izquierdo de la TARJETA (no del rail). El
       block-container tiene padding-left ~60px encima del rail (90px),
       de ahi los ~154px. La fecha se ancla al lado derecho (más abajo). */
    .st-key-chips_ajuste_tabla {
        position: fixed !important;
        top: 8px !important;
        left: 154px !important;
        right: auto !important;
        width: auto !important;
        max-width: calc(100vw - 154px - 380px) !important;   /* deja aire para la fecha derecha */
        z-index: 23 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stHorizontalBlock"] {
        gap: 8px !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stColumn"],
    .st-key-chips_ajuste_tabla [data-testid="column"] {
        width: auto !important;
        flex: 0 1 auto !important;
        min-width: 0 !important;
    }
    /* Opción A: cuadrado lavanda con icono + badge morado. Ancho automático
       para que el badge del count quepa sin recortar; esquinas 4px. */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        min-width: 0 !important;
        width: auto !important;
        min-height: 28px !important;
        height: 28px !important;
        padding: 3px 10px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        background: var(--accent-tint) !important;
        border: 1px solid var(--border-lavender) !important;
        border-radius: 4px !important;
        color: var(--accent-deep) !important;
        overflow: hidden !important;
        gap: 6px !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button p {
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button [data-testid="stIconMaterial"] {
        font-size: 15px !important;
    }
    /* Badge del count (Streamlit :violet-badge[N] dentro del label) */
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button [data-testid="stBadge"] {
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 3px !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        padding: 1px 6px !important;
        line-height: 1.4 !important;
    }
    .st-key-chips_ajuste_tabla [data-testid="stPopover"] button:hover {
        background: var(--accent-light) !important;
        border-color: var(--accent) !important;
    }
    /* Estado ACTIVO (hay un filtro aplicado): fondo lleno en vez del tono
       tenue de reposo, para diferenciarlo a simple vista. */
    .st-key-chips_ajuste_tabla [class*="st-key-chipwrap_"][class*="_on"] [data-testid="stPopover"] button {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #ffffff !important;
    }
    .st-key-chips_ajuste_tabla [class*="st-key-chipwrap_"][class*="_on"] [data-testid="stPopover"] button:hover {
        background: var(--accent-deep) !important;
        border-color: var(--accent-deep) !important;
    }
    /* Pantallas chicas: si no caben junto a las pestañas, bajan a su línea */
    @media (max-width: 900px) {
        .st-key-chips_ajuste_tabla {
            position: static !important;
            width: auto !important;
            max-width: none !important;
            margin: 6px 0 0 0 !important;
        }
    }

    /* Título del reporte, fijo en el nivel 1 de la franja */
    .titulo-ajuste-reporte {
        position: fixed !important;
        top: 6px !important;
        left: calc(90px + 1rem) !important;
        z-index: 22 !important;
        margin: 0 !important;
        color: var(--text-primary) !important;
        font-family: 'Corbel', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        text-transform: uppercase !important;
        font-size: 27px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        letter-spacing: 0.01em !important;
        transform: none !important;
    }

    /* Chip pill del título del reporte */
    .chip-titulo-reporte {
        display: inline-flex;
        align-items: center;
        background: var(--accent-tint);
        color: var(--accent-deep);
        border-radius: 999px;
        padding: 8px 18px;
        font-size: 15px;
        font-weight: 500;
        line-height: 1;
        white-space: nowrap;
        letter-spacing: 0.01em;
    }
"""
