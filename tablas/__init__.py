"""tablas - renderizado de tablas AgGrid.

Era un tablas.py de 2.028 lineas; desde el refactor de 2026-08-01 es un
paquete. La API publica no cambio: from tablas import renderizar_aggrid_desktop.

    _css.py       CSS de AgGrid (grid, paneles de columnas/filtros/pivote,
                  marco del sidebar). _css_base() agrega los demas.
    _config.py    helpers de configuracion: estilos de celda y fila, sidebar,
                  fila de totales, titulos en espanol.
    desktop.py    renderizar_aggrid_desktop (la vista principal)
    movil.py      renderizar_aggrid_movil
    compras.py    renderizar_aggrid_compras
    ajuste_pivote.py  renderizar_aggrid_pivote_ajuste (tabla "Por fecha" de
                  Ajuste de Inventario, ver graficos/ajuste.py)
"""

from tablas.desktop import (renderizar_aggrid_desktop)  # noqa: F401
from tablas.movil import (renderizar_aggrid_movil)  # noqa: F401
from tablas.compras import (renderizar_aggrid_compras)  # noqa: F401
from tablas.ajuste_pivote import (renderizar_aggrid_pivote_ajuste)  # noqa: F401
