"""
graficos.recetabase — la mitad de RECETAS BASE del dashboard de Recetas.

Cada fila de recetabase.parquet es un INSUMO de una receta base (una
subpreparación: salsas, masas, mise en place — no un plato vendido):
    RB NOMBRE · INSUMO · CANT · CST SUBT INS
    (receta base)  (insumo)  (cant.)   (costo del insumo en la receta)

**Dejó de ser un dashboard propio el 2026-09-04.** Hasta entonces «Receta
Base» era un reporte aparte, con su rail, su pila de 4 secciones y su
punto de entrada `renderizar_graficos_recetabase`, al que se llegaba por
un chip Base/Venta. Hoy sus cuatro vistas viven en la MISMA página que las
de platos — ver `graficos/recetas.py`, que es quien dibuja la pila y de
paso explica por qué se fusionaron (spoiler: una receta base no es la
hermana de una receta de venta, es una pieza de adentro; la medición que
decía «0% overlap» comparaba `COD RB`, el ID interno, en vez de
`COD PROD RB`).

Con el entry point se fueron sus `_RAIL_CATEGORIAS` y su `_PILA`: el rail
y el orden de las secciones los declara ahora `graficos/recetas.py`. Lo
que queda acá es lo ÚNICO propio de este parquet — resolver sus columnas
reales para el Panorama de compras. Los tres gráficos que dibuja (Ranking,
Insumos clave, Panorama) siguen viniendo de `graficos.recetas_comun`, que
los comparte con la mitad de platos.

Sankey y Composición se dieron de baja acá el 2026-08-28, a pedido. Eran
las DOS vistas de una receta elegida a mano, así que con ellas se fueron
las dos cosas que existían sólo para alimentarlas: el selectbox "Receta
base" y el botón "Abrir Sankey →" del Panorama, que se quedaba sin destino.
Ver `arquitectura.md` regla #236.

OJO — activo/inactivo en formato PROPIO: `RB ACT` viene como
"RB.ACTIV"/"RB.INACT" e `INS ACTIVO` (mismo nombre de columna que en
Receta Venta) viene como "INS.ACT"/"INS.INAC" — ninguno de los dos es
"ACTIV"/"INACTIV" como en Receta Venta. Ver `_activo()` en
recetas_comun.py, que normaliza los tres formatos.
"""

from graficos.recetas_comun import _panorama_compras


def _panorama_compras_base(df_f, es_soles):
    _panorama_compras(
        df_f, es_soles, key_prefix="rb",
        col_cod_ins_cand=["COD INS RB", "Cod Ins Rb"],
        col_contenedor_cand=["RB NOMBRE", "Rb Nombre", "Nombre RB"],
        col_valor_cand=["CST SUBT INS", "Cst Subt Ins"],
        col_cant_cand=["CANT", "Cant"],
        col_activo_contenedor_cand=["RB ACT", "Rb Act"],
        col_activo_item_cand=["INS ACTIVO", "Ins Activo"],
        etiqueta_otros_contenedor="Otras recetas",
        titulo_card="Productos comprados → recetas base que los usan",
        col_contenedor_out="Receta base",
        etiqueta_contenedor_plural="recetas base activas",
        # Sin `nombre_vista_sankey`/`clave_seccion_sankey`: este dashboard ya
        # no tiene Sankey, así que `_panorama_compras` se saltea el drill que
        # existía SÓLO para saltar hasta él y deja el de insumo a lo ancho.
    )
