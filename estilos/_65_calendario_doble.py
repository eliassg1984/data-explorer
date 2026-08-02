"""estilos._65_calendario_doble - Calendario propio de dos meses (calendario.py).

Distinto de `_60_calendario`, que estiliza el calendario NATIVO de BaseWeb
(`st.date_input`). Este bloque es para la grilla que dibujamos nosotros con
un `st.button` por día.

El estado de cada día viaja en el SUFIJO de la key del botón (`_sel`, `_rng`,
`_hoy`), mismo patrón que los `chipwrap_*_on`. Por eso los selectores
matchean por `[class*="…_sel"]` y no por clases propias: el CSS de Streamlit
solo nos deja agarrar el contenedor por su key.

Va DESPUÉS de `_60_calendario` y ANTES de `_70_chrome`; el orden respecto a
estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* CALENDARIO DOBLE PROPIO — grilla de botones (calendario.py)          */
    /* =================================================================== */

    /* Nombre del mes y cabecera de día de la semana */
    .cal-mes {
        text-align: center;
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary);
        text-transform: capitalize;
        line-height: 30px;
    }
    .cal-dow {
        text-align: center;
        font-size: 9px;
        font-weight: 600;
        letter-spacing: .06em;
        text-transform: uppercase;
        color: var(--text-muted);
        padding: 2px 0 4px;
    }
    /* Celda vacía: mismo alto que un botón, para no romper la grilla. */
    .cal-hueco { height: 30px; }
    .cal-pista {
        margin-top: 8px;
        font-size: 11px;
        color: var(--text-muted);
        text-align: center;
    }

    /* Botones de día: compactos y cuadrados. La regla global del popover de
       filtros les impone 180px de ancho mínimo, de ahí el min-width: 0. */
    div[class*="st-key-cald_"] button {
        min-width: 0 !important;
        min-height: 30px !important;
        height: 30px !important;
        padding: 0 !important;
        font-size: 12px !important;
        font-weight: 400 !important;
        line-height: 1 !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        background: transparent !important;
        color: var(--text-primary) !important;
        transition: background .12s ease, color .12s ease !important;
    }
    div[class*="st-key-cald_"] button:hover {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
    }
    div[class*="st-key-cald_"] button:disabled {
        color: var(--text-muted) !important;
        opacity: .35 !important;
        background: transparent !important;
    }

    /* Días DENTRO del rango elegido. */
    div[class*="st-key-cald_"][class*="_rng"] button {
        background: var(--accent-tint) !important;
        color: var(--accent-deep) !important;
        border-radius: 4px !important;
    }
    /* Extremos del rango (o el primer clic pendiente). Va DESPUÉS de _rng
       para ganarle cuando un día es extremo. */
    div[class*="st-key-cald_"][class*="_sel"] button {
        background: var(--accent) !important;
        color: #fff !important;
        font-weight: 600 !important;
    }
    div[class*="st-key-cald_"][class*="_sel"] button:hover {
        background: var(--accent-hover) !important;
        color: #fff !important;
    }
    /* Hoy: solo contorno, para no competir con la selección. */
    div[class*="st-key-cald_"][class*="_hoy"] button {
        border-color: var(--accent) !important;
    }

    /* Flechas de navegación entre meses. */
    div[class*="st-key-cal_prev_"] button,
    div[class*="st-key-cal_next_"] button {
        min-width: 0 !important;
        min-height: 30px !important;
        height: 30px !important;
        padding: 0 !important;
        font-size: 16px !important;
        border: none !important;
        background: transparent !important;
        color: var(--accent) !important;
        border-radius: 8px !important;
    }
    div[class*="st-key-cal_prev_"] button:hover,
    div[class*="st-key-cal_next_"] button:hover {
        background: var(--accent-tint) !important;
    }
    div[class*="st-key-cal_prev_"] button:disabled,
    div[class*="st-key-cal_next_"] button:disabled {
        color: var(--text-muted) !important;
        opacity: .3 !important;
    }

    /* La grilla no necesita el gap vertical que Streamlit mete entre
       elementos apilados dentro de una columna. */
    .st-key-fecha_panel div[data-testid="stVerticalBlock"] {
        gap: 0.15rem !important;
    }
"""
