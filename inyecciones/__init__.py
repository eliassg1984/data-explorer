"""inyecciones - JS/HTML inyectado en la app.

Era un inyecciones.py de 1.813 lineas; desde el refactor de 2026-08-01 es un
paquete. La API publica no cambio: from inyecciones import inject_*.

    _fragmentos.py  CSS/JS reutilizado por varias inyecciones
    grid.py         todo lo que toca el AgGrid (salud, altura, maximizar,
                    panel de columnas de Ajuste)
    paginacion.py   barra de paginacion v2 (numeros + salto de pagina)
    inspector.py    inspector de elementos (herramienta de desarrollo)
    diseno.py       modo de diseno visual (herramienta de desarrollo, lee
                    el pin de inspector.py — ver Regla viva mas abajo)
    varios.py       overlay de errores, fullscreen, cabecera de Ajuste,
                    footer y calendario en espanol

Ninguna funcion depende de otra: las unicas dependencias internas son hacia
las constantes de _fragmentos.py. La excepcion es diseno.py, que LEE (nunca
llama) el estado que inspector.py expone en window.parent para el pin
(__inspectorPinned/__inspectorUltimo) — inspector.py no sabe que diseno.py
existe, el acoplamiento es unidireccional.

Regla viva (arquitectura.md #4): si dos inject_* comparten espacio o elemento,
la interaccion se documenta en AMBAS.
"""

from inyecciones.grid import (inject_dynamic_grid_height, inject_filtros_grid, inject_fix_column_panel_ajuste, inject_grid_health_check, inject_maximize_aggrid)  # noqa: F401
from inyecciones.paginacion import (inject_pagination_v2)  # noqa: F401
from inyecciones.inspector import (inject_element_inspector)  # noqa: F401
from inyecciones.diseno import (inject_diseno_visual)  # noqa: F401
from inyecciones.varios import (inject_alinear_cabecera_ajuste, inject_calendario_es, inject_error_overlay, inject_footer_actualizacion, inject_fullscreen_app)  # noqa: F401
