"""estilos._50_fecha - Pill de fecha del header y su variante de Compras (alineada a la izquierda, scopeada con :has(.st-key-compras_tabs_row)).

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
    right: 138px !important;        /* alineada con el borde derecho de la tarjeta */
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
    /* En Compras la franja es MAS BAJA (34px, no 50px) — el ::before
       la sobreescribe directamente pero --cab-altura sigue en 50.
       Aquí re-alineamos el underline al borde real de esa franja. */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-fecha_ajuste_pill [data-testid="stPopover"] button {
        min-height: 26px !important;   /* 34px franja - 8px top */
    }

    /* ================================================================== */
    /* COMPRAS: fecha a la IZQUIERDA (alineada con la tarjeta) y chips     */
    /* Familia/Subfamilia al CENTRO con fondo blanco.                      */
    /* Scopeado con :has(.st-key-compras_tabs_row) → no afecta otros       */
    /* reportes.                                                           */
    /* ================================================================== */
    /* Solo cambia la POSICIÓN: fecha alineada con el borde izquierdo de la
       tarjeta (block-container padding-left ~16px sobre el rail 90px + aire). */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-fecha_ajuste_pill {
        left: 175px !important;
        right: auto !important;
    }

    /* Chips Familia/Subfamilia CENTRADOS en el ancho de la tarjeta
       (154px izquierda ↔ 131px derecha por el rail 116 + 15). */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-chips_ajuste_tabla {
        left: calc((154px + (100vw - 131px)) / 2) !important;
        right: auto !important;
        transform: translateX(-50%) !important;
        max-width: calc(100vw - 154px - 131px - 380px) !important;
    }
    /* Fondo blanco (en vez del tinte lavanda) + más espacio interno a la
       derecha (chip más ancho y con aire tras el texto/badge). */
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-chips_ajuste_tabla [data-testid="stPopover"] button {
        background: #ffffff !important;
        min-width: 230px !important;   /* ≈ ancho del widget de fecha */
        padding-right: 22px !important;
        justify-content: flex-start !important;
    }
    [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
        .st-key-chips_ajuste_tabla [data-testid="stPopover"] button:hover {
        background: var(--accent-tint, #EEEDFE) !important;
    }

    /* ── chips_ajuste_tabla — reset móvil ──────────────────────────────────
       Las reglas de arriba centran el bar (left/transform) y lo acotan con
       max-width:calc(100vw-665px) — que se vuelve NEGATIVA (→ colapsa a 0)
       por debajo de 665px — y estiran cada popover a min-width:230px. En
       móvil el rail deja de ser fijo pero :has(.st-key-compras_tabs_row)
       SIGUE matcheando, así que esas reglas se cuelan y rompen el bar (chip
       estirado con un vacío al lado, o bar colapsado). Se neutralizan aquí:
       misma especificidad que las de arriba, pero DESPUÉS en el archivo para
       ganar por orden de fuente dentro del media query. */
    /* Clase duplicada (.st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla)
       para subir la especificidad por encima de TODAS las reglas de desktop
       de arriba y ganar sin depender del orden de fuente. */
    @media (max-width: 900px) {
        [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
            left: auto !important;
            transform: none !important;
            max-width: none !important;
            width: auto !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stPopover"] button {
            min-width: 0 !important;
            padding-right: 12px !important;
        }
        /* Fecha alineada a la IZQUIERDA en móvil. La regla de desktop
           (:has(...) .st-key-fecha_ajuste_pill { left:175px }, para dejar
           sitio al rail lateral) se cuela porque :has(...) sigue matcheando
           con el rail horizontal. Aquí se vuelve a left:12px (clase duplicada
           para ganar especificidad) → la fecha se alinea con el borde
           izquierdo, igual que los filtros: los tres se leen como un grupo. */
        [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
            .st-key-fecha_ajuste_pill.st-key-fecha_ajuste_pill {
            left: 12px !important;
            right: auto !important;
        }
        /* Familia + Subfamilia PEGADOS a la izquierda. La regla móvil de
           Ajuste (2×2, más abajo) fuerza las columnas a 50% width, lo que en
           Compras (solo 2 filtros) deja a Subfamilia flotando al centro con
           un hueco. Aquí se empacan a contenido, juntas a la izquierda, para
           que fecha + Familia + Subfamilia se lean como un bloque ordenado.
           Clase duplicada + :has para ganar a la regla 2×2 sin importar el
           orden de fuente. */
        [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stHorizontalBlock"] {
            justify-content: flex-start !important;
            gap: 8px !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: 0 !important;
        }
        /* Apretar el aire vertical entre la fecha (fija arriba) y la fila de
           filtros. En producción el gap es ~32px; se jala la fila hacia arriba
           con margen negativo para dejar ~14px, sin tocar la fecha (bottom
           ~50px). Arrastra también todo lo de abajo → el gráfico sube. */
        [data-testid="stAppViewContainer"]:has(.st-key-compras_tabs_row)
            .st-key-chips_ajuste_tabla.st-key-chips_ajuste_tabla {
            margin-top: -18px !important;
        }
    }

    /* Panel del popover: se renderiza en un portal (fuera del contenedor),
       así que lo scopeamos por el contenedor keyed interno con :has(). */
    /* 760px: el calendario propio dibuja DOS meses = 14 columnas de días
       más los atajos a la izquierda. Con los 380px de antes (cuando había
       un st.date_input de un solo mes) los días quedaban ilegibles. */
    [data-testid="stPopoverBody"]:has(.st-key-fecha_panel) {
        min-width: 760px !important;
    }
    /* Botones de atajo: compactos, alineados a la izquierda. */
    .st-key-fecha_panel [data-testid="stColumn"]:first-child button {
        min-width: 0 !important;
        padding: 6px 10px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        justify-content: flex-start !important;
        text-align: left !important;
    }

    .ultima-actualizacion {
        margin: 0 !important;
        color: var(--text-muted) !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        text-align: right !important;
        white-space: nowrap !important;
    }
"""
