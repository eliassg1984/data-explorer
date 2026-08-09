"""estilos._90_franja_inferior - Franja inferior fija que cierra el area de contenido, mas el texto de 'Ultima actualizacion' anclado a ella.

Extraido de estilos.py (lineas 1499-1553 del original).
El orden respecto a estilos/__init__.py es parte del comportamiento del CSS.
"""

CSS = """    /* =================================================================== */
    /* FRANJA INFERIOR FIJA — cierra visualmente el área de contenido       */
    /* =================================================================== */
    .stApp::after {
        content: "" !important;
        position: fixed !important;
        left: 90px !important; /* coincide con el ancho del rail */
        right: 0 !important;
        bottom: 0 !important;
        height: 42px !important;
        background: #ffffff !important;
        border-top: 1px solid var(--border) !important;
        box-shadow: 0 -2px 4px rgba(16, 16, 20, 0.04) !important;
        pointer-events: none !important;
        z-index: 999990 !important;
    }
    [data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    .block-container {
        padding-bottom: 66px !important;
    }

    /* El texto "Última actualización" NO se estila aquí. Lo pinta
       inyecciones/varios.py::inject_footer_actualizacion, que crea un div
       con id="footer-actualizacion" y estilos INLINE, anclado directo al
       body para escapar de los stacking contexts de Streamlit (lo explica
       su docstring). Hasta el 2026-08-08 vivian aqui ~32 lineas para
       `.st-key-footer_actualizacion` y `.ultima-actualizacion`: ni esa key
       ni esa clase las emite nadie — la inyeccion solo asigna id, cssText
       y textContent. Ver arquitectura.md #49. */
"""
