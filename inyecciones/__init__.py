"""inyecciones - JS/HTML inyectado en la app.

Era un inyecciones.py de 1.813 lineas; desde el refactor de 2026-08-01 es un
paquete. La API publica no cambio: from inyecciones import inject_*.

    _fragmentos.py  CSS/JS reutilizado por varias inyecciones
    grid.py         todo lo que toca el AgGrid (salud, altura, maximizar,
                    panel de columnas de Ajuste)
    paginacion.py   barra de paginacion v2 (numeros + salto de pagina)
    inspector.py    inspector de elementos (herramienta de desarrollo)
    varios.py       overlay de errores, fullscreen, cabecera de Ajuste,
                    footer y calendario en espanol

Ninguna funcion depende de otra: las unicas dependencias internas son hacia
las constantes de _fragmentos.py. Por eso el corte es limpio.

Regla viva (arquitectura.md #4): si dos inject_* comparten espacio o elemento,
la interaccion se documenta en AMBAS.
"""

from inyecciones.grid import (inject_dynamic_grid_height, inject_fix_column_panel_ajuste, inject_grid_health_check, inject_maximize_aggrid)  # noqa: F401
from inyecciones.paginacion import (inject_pagination_v2)  # noqa: F401
from inyecciones.inspector import (inject_element_inspector)  # noqa: F401
from inyecciones.varios import (inject_alinear_cabecera_ajuste, inject_calendario_es, inject_error_overlay, inject_footer_actualizacion, inject_fullscreen_app)  # noqa: F401
