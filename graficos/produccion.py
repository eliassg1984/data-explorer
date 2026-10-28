"""
graficos.produccion — dashboard de Producción (2026-10-23, regla #709).

Lo que se TRANSFORMA en casa, en seis vistas que hasta ese día eran el
final de Movimientos: Porcionamientos, su merma en tres vistas
(Rendimiento, Costo por kg útil, Para revisar), las órdenes de producción
y el consumo según recetas. Salieron con la etapa 2 de la navegación del
boceto del rail compacto (#708): Movimientos se quedó con lo que se pide y
lo que se da de baja, y bajó de 12 vistas a 6.

ACÁ SÓLO VIVEN EL RAIL Y LA PILA. Todo lo demás es de Movimientos y se usa
tal cual: la carga de requerimientos (`archivo` del reporte, de donde
salen los chips «Sub Almacén» y «Familia», el orden de las áreas que
reparte los colores —Cocina del mismo color que en Movimientos, regla
#509— y los topes del botón de fecha de Consumo), la fecha de cada vista
(`movimientos.CATEGORIA_VISTA`, regla #617) y los dibujantes de cada
sección, con sus mismas keys `mov_sec_*`. Así nada de lo que hacían
cambia: cambia la página en la que están. Un módulo propio y no una
segunda pila en `movimientos.py` porque la convención es un dashboard por
módulo, con SU rail y SU pila declarados en él (lo leen con `ast`
`_pruebas_vistas_de_cada_reporte` y `_pruebas_vistas_tabla_ocultas`).

salidas.parquet no se carga: ninguna de estas vistas lo usa.
"""

from graficos.base import _render_rail, pila_sin_tablas, rail_sin_tablas
from graficos import movimientos
from graficos import movimientos_merma as mm

_RAIL_CATEGORIAS = rail_sin_tablas((
    # «Porcionamientos» (2026-09-24, regla #510): el primer grupo, una sola
    # vista, con el nombre que se pidió; el ícono son las tijeras del corte.
    # Las tres de MERMA (2026-10-08, regla #615): lo que el «Reporte de
    # Mermas» del Almacén no dice — qué porcionamiento revisar, cómo rinde
    # un producto en el tiempo y cuánto cuesta el kg útil según a quién se
    # le compró. Viven en `graficos/movimientos_merma.py`.
    # El ORDEN va de lo general a lo particular desde el 2026-10-12 (regla
    # #647), a pedido: cuánto se perdió → en qué producto y desde cuándo →
    # a quién comprarlo → los casos sueltos. «Para revisar» es la lista de
    # trabajo y va al final; hasta ese día era la segunda.
    # «Porcionamientos» y «Rendimiento» son UNA vista desde el 2026-10-23
    # (regla #712): «Porcionamientos», con las perspectivas «Por período» y
    # «Rendimiento» (`movimientos_merma.PERSPECTIVAS_PORC`). El boceto las
    # llamaba «Lista» y «Rendimiento»; la primera es la merma por período,
    # y se nombra como sus gemelas de Movimientos.
    ("Porcionamientos", (("Porcionamientos", "Porcionamientos", ":material/content_cut:"),
                         ("Proveedor por kg útil", "Costo por kg útil", ":material/local_shipping:"),
                         ("Merma para revisar", "Para revisar", ":material/flag:"))),
    # «Producción» (2026-09-30, regla #575): las órdenes de producción del
    # Almacén, lo que las áreas preparan con sus recetas base. Va junto a
    # Porcionamientos —las dos transformaciones que se registran en el
    # Almacén— y antes de Consumo, que es la cuenta TEÓRICA de las ventas.
    # El ícono es una licuadora: una preparación. Se lee «Órdenes de
    # producción» desde que el reporte entero se llama Producción (#709):
    # el id sigue siendo «Producción» (lo usan la pila y `?vista=`).
    ("Producción", (("Producción", "Órdenes de producción", ":material/blender:"),)),
    # «Consumo según recetas» (2026-09-28, regla #558): lo que las VENTAS
    # usaron en insumos de compra, bajando por las recetas base y los
    # porcionamientos — el lado teórico de lo que las de arriba miden del
    # almacén. El ícono es una olla. Con seis vistas la lista no lleva
    # subtítulos (`base.AGRUPAR_VISTAS_DESDE`): el rótulo va entero.
    ("Consumo", (("Consumo según recetas", "Consumo según ventas", ":material/soup_kitchen:"),)),
    ("Procesos", (("Flujo del producto", "Flujo del producto", ":material/account_tree:"),)),
))

# El orden de la página, y el apareo sección ↔ vista del rail. Las keys
# `mov_sec_*` son las de cuando vivían en Movimientos, a propósito: de ellas
# cuelgan el CSS de sus tarjetas, su fecha (`movimientos.CATEGORIA_VISTA`),
# el foco que comparten las de merma (`movimientos_merma.SEC_*`) y el estado
# de cada sección.
_PILA = pila_sin_tablas((
    ("mov_sec_persp_porc",  "Porcionamientos"),
    ("mov_sec_merma_prov",  "Proveedor por kg útil"),
    ("mov_sec_merma_rev",   "Merma para revisar"),
    ("mov_sec_prod",        "Producción"),
    ("mov_sec_consumo",     "Consumo según recetas"),
    ("mov_sec_flujo",       "Flujo del producto"),
))


def renderizar_graficos_produccion(df_f, nombre_reporte, df_full=None,
                                   tabla_cb=None):
    """Dashboard de Producción. Recibe lo mismo que Movimientos (`df_f` y
    `df_full` son requerimientos.parquet) y lo dibuja con el cuerpo de
    Movimientos (`movimientos.renderizar`) sobre su propia pila. Sin Tabla:
    `tabla_cb` se acepta por el contrato del dispatcher y no se usa."""
    def dibujar_rail():
        _render_rail(_RAIL_CATEGORIAS, "prod_graf_tipo",
                     btn_prefix="prod_rail_btn_", secciones=_PILA)
    movimientos.renderizar(df_f, nombre_reporte, df_full, tabla_cb,
                           pila=_PILA, dibujar_rail=dibujar_rail,
                           con_salidas=False,
                           perspectivas={mm.SEC_PORC: ("porc", mm.EJES_PORC,
                                                       mm.PERSPECTIVAS_PORC)})
