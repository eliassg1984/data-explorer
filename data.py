"""
Gestión de datos: conexión DuckDB, carga de archivos y configuración de reportes.
"""

import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import boto3
import json
import numbers
import threading
import zlib
from datetime import datetime, timedelta, timezone

import definicion_venta
import definicion_compra
import consumo_recetas
import kardex
import analisis_stock
import sin_plato
import diferencias_ajuste
from cortes import MESES_ABR_ES, MESES_LARGOS_ES, sesiones_inventario


# ===========================================================================
# CONFIGURACIÓN DE REPORTES
# ===========================================================================
# Claves que lee app.py (todas opcionales salvo `archivo`):
#
#   archivo, label_corto, icono      identidad del reporte
#   label_largo                      nombre de MOSTRAR en la franja de contexto
#                                    (ancha); cae en la CLAVE del dict si falta.
#                                    Existe para nombrar un reporte distinto de
#                                    su clave interna sin renombrarla — hoy solo
#                                    "Inventario Valorizado" → "Stock e Inventario".
#   label_rail                       el nombre DEBAJO del ícono en la columna
#                                    plegada de 80px (2026-09-29, regla #568):
#                                    una palabra de ~70px como mucho. Cae en
#                                    `label_corto` si falta; sólo lo declaran
#                                    los tres cuyo `label_corto` no entra ahí.
#                                    Con la columna FIJADA (248px) se sigue
#                                    viendo `label_corto` entero, que es lo que
#                                    se pidió el 2026-09-21 y el 2026-09-22.
#   area                             el ÁREA a la que pertenece (2026-10-23,
#                                    regla #708): desde 901px la columna
#                                    muestra UN ícono por área, y la franja de
#                                    arriba, las vistas de todos sus reportes.
#                                    Los reportes de un área van SEGUIDOS en
#                                    este dict. Por debajo de 901px cada uno
#                                    sigue con su botón: ahí la franja no es
#                                    el índice y no habría cómo llegar.
#   fecha                            columna de fecha; None = sin filtro
#   carga_por_rango                  filtra en DuckDB antes de materializar
#   filtros_cat, buscador, agrupar   filtros genericos
#   columnas                         columnas del selector (orden incluido)
#   columnas_movil, columnas_fijas_movil   vista movil
#   graficos                         motor generico config-driven
#   tool                             no es un parquet, es una herramienta
#
#   columnas_iniciales       columnas que arrancan VISIBLES en la AgGrid; el
#                            resto se activa desde el panel lateral. Sin esta
#                            clave se muestran todas. Se resuelven con
#                            buscar_columna, asi que el nombre no tiene que
#                            coincidir exacto con el del parquet.
#   derivar_periodo_pivote   crea columnas "<fecha> (Mes)" y "<fecha> (Dia)"
#                            como STRING para el Modo pivote de AG Grid (ver
#                            app.py). Solo lo necesitan los reportes cuya
#                            fecha trae hora.
#
# Estas dos ultimas vivian como `if reporte == "..."` dentro de app.py hasta
# el 2026-08-08. Son configuracion de DATOS, no de despacho: su sitio es este
# dict, igual que columnas_movil.


# QUÉ ES STOCK: sólo lo ACTIVO (2026-10-03, a pedido, regla #598). Una fila de
# `inventariovalorizado.parquet` entra en «Stock e Inventario» si las cuatro
# marcas del POS dicen que sí; si no, va a «Inactivos y servicios» con el
# motivo de la PRIMERA que falle, en este orden:
#
#   · AREA ACTIVA      `vArea.lActivo`. CALIENTES está inactiva y arrastraba
#                      −S/ 38.161 de descargos de venta sin un solo ingreso.
#   · PRODUCTO ACTIVO  `TPRODUCTO.lActivo`. Agua Filtrada −10.645 L en Barra.
#   · COMPARTIDO       `TSUBSTOCK.lActivo`: el producto habilitado en ESA área
#                      (medido: coincide en las 11.513 filas de área; el
#                      Almacén Central siempre dice COMPARTIDO).
#   · TIPO PRODUCTO    `TPRODUCTO.tTipoProducto`: un SERVICIO no es inventario
#                      («Compras Mantenimiento Varios», 2.269,5 und = S/ 126k
#                      en GASTOS).
#
# Es la regla con que el «Inventario Valorizado al Día» del POS elige sus
# filas (cuadrado fila por fila el 2026-10-03: Central 1.750 de 1.750, Barra
# 406 de 406), más el área inactiva. La consumen la vista
# (`graficos/inventario.py::separar_activos`) y el KPI de este reporte, así
# que se define UNA vez acá. Una columna que el parquet todavía no traiga no
# filtra: AREA ACTIVA y TIPO PRODUCTO llegaron con la consulta del Sheet del
# 2026-10-03.
INVENTARIO_ACTIVO = (
    ("AREA ACTIVA", "ACTIVA", "Área inactiva"),
    ("PRODUCTO ACTIVO", "ACTIVO", "Producto inactivo"),
    ("COMPARTIDO", "COMPARTIDO", "No habilitado en el área"),
    ("TIPO PRODUCTO", "MERCADERIA", "Servicio"),
)

REPORTES = {
    # Orden del dict == orden del rail de navegación (navegacion.py::
    # inject_navegacion itera `reportes.items()` tal cual). Reordenar acá
    # reordena los iconos de arriba a abajo.
    # «Inicio» desde el 2026-10-23 (regla #711): la portada del mes y los
    # Pendientes del período, el área Inicio del boceto del rail compacto.
    # La CLAVE sigue siendo «Resumen ejecutivo» (dispatcher, enlaces,
    # `?reporte=`): sólo cambia lo que se lee.
    "Resumen ejecutivo": {
        "label_corto": "Inicio",
        "label_largo": "Inicio",
        "label_rail": "Inicio",
        "archivo": "ajusteinventario.parquet",
        "archivos_extra": ("compras.parquet", "salidas.parquet"),
        "icono": ":material/dashboard:",
        "fecha": None,
        "filtros_cat": [],
    },
    "Compras": {
        "label_corto": "Compras",
        "area": "Compras",
        "archivo": "compras.parquet",
        # Shortcode Material Symbols (no Bootstrap Icons — ver el comentario
        # grande más abajo de "El mapa de iconos..."). Confirmados contra
        # compras.parquet real (2026-08-22): valorizado = VALOR_COMPRA,
        # documentos = NUM_DOCUMENTO, fecha = FECHA_EMISION_DOC.
        "icono": ":material/shopping_cart:",
        "kpis": (("Valorizado", "VALOR_COMPRA", "sum"),
                 ("Documentos", "NUM_DOCUMENTO", "count_distinct")),
        # KPIs propios de la FRANJA superior (2026-09-01, a pedido:
        # "Documentos, Valorizado Alimentos, Bebidas y Vino").
        #
        # Lista APARTE de `kpis` y no un reemplazo: el rail muestra un
        # numero grande y uno chico en 280px, y cuatro no le entran. La
        # franja es ancha y horizontal, asi que puede con los cuatro. Cada
        # superficie declara lo que puede mostrar.
        #
        # Los tres valorizados son el MISMO SUM de VALOR_COMPRA acotado por
        # FAMILIA (4o elemento de la tupla, ver `_resumen_kpis_cacheable`).
        # Las familias son las reales del parquet, verificadas 2026-09-01
        # contra R2 — son ocho y estas cuatro son las que se pidieron:
        #   ALIMENTOS  S/5.6M   COSTOS PRODUCCION      S/3.5M
        #   VINOS Y ESPUMANTES  S/447k
        #   BEBIDAS CON ALCOHOL S/236k + BEBIDAS SIN ALCOHOL S/135k
        # "Bebidas" suma las DOS familias de bebidas; "Vino" va aparte
        # porque VINOS Y ESPUMANTES es su propia familia y se pidio suelto.
        "kpis_franja": (
            ("Documentos", "NUM_DOCUMENTO", "count_distinct"),
            ("Alimentos", "VALOR_COMPRA", "sum",
             ("FAMILIA", ("ALIMENTOS",))),
            ("Bebidas", "VALOR_COMPRA", "sum",
             ("FAMILIA", ("BEBIDAS CON ALCOHOL", "BEBIDAS SIN ALCOHOL"))),
            ("Vino", "VALOR_COMPRA", "sum",
             ("FAMILIA", ("VINOS Y ESPUMANTES",))),
        ),
        "kpi_fecha": "FECHA_EMISION_DOC",
    },
    # REPORTE PROPIO desde el 2026-09-30, a pedido («que documentos sunat se
    # vea en otra botonera del rail, como si fuese un reporte más, ya no
    # dentro de compras»). Hasta ese día era una vista de Compras —la única
    # que no estaba en su pila, un "destino aparte"— y ya se comportaba como
    # un reporte: otra fuente (el SIRE, no el parquet), sin los chips de
    # Familia/Subfamilia y con el ÚNICO calendario entero de Compras dentro
    # de su tarjeta. El drill no cambió: sigue en
    # `graficos/compras/documentos_sunat.py`; lo despacha
    # `graficos/sunat_reporte.py`. Regla #577.
    #
    # `archivo` es compras.parquet a propósito: es el lado "sistema" del
    # cruce documento a documento, y el botón Refrescar lo pide. Lo de SUNAT
    # no es un parquet que se refresque desde acá: lo trae la tarjeta con su
    # propio botón de sincronizar.
    #
    # Sin `kpis`: los de Compras cuentan documentos DEL SISTEMA, y en este
    # reporte un «Documentos» sin apellido se leería como los de SUNAT. Lo
    # que cuadra y lo que no lo dice la tira de KPIs de la propia tarjeta.
    "Documentos SUNAT": {
        "label_corto": "Documentos SUNAT",
        "label_largo": "Documentos SUNAT",
        "label_rail": "SUNAT",
        "area": "Compras",
        "archivo": "compras.parquet",
        "icono": ":material/fact_check:",
    },
    "Inventario Valorizado": {
        # La clave "Inventario Valorizado" es la IDENTIDAD INTERNA del reporte
        # (dispatcher de graficos/, _sugerencias del asistente, el slug CSS
        # `app_reporte_inventario_valorizado` de estilos/_40_ajuste_franja.py,
        # las comparaciones de tablas/ y las citas de arquitectura.md): NO se
        # renombra. Lo que ve el usuario es "Stock e Inventario" (a pedido,
        # 2026-09-21), en dos sitios con distinto ancho: el rail lo toma de
        # `label_corto` y la franja de contexto de `label_largo` (que
        # `navegacion.py::_html_barra_contexto` y la cabecera del rail
        # prefieren sobre la clave). Coinciden a propósito — el nombre pedido
        # ya es corto; el par existe para no regresar a "Movimientos"→"Movim."
        # en la franja del resto de los reportes, que no declaran `label_largo`.
        "label_corto": "Stock e Inventario",
        "label_largo": "Stock e Inventario",
        "label_rail": "Stock",
        "area": "Inventario",
        "archivo": "inventariovalorizado.parquet",
        # El kardex por hora (2026-10-03, regla #601): el «Stock al» de
        # Stock por Producto lo lee para el stock a una fecha. Va acá para
        # que «Actualizar» lo pida también.
        "archivos_extra": (kardex.ARCHIVO,),
        "icono": ":material/inventory_2:",
        # Foto sin fecha (igual que Recetas): kpi_fecha ausente a
        # propósito, resumen_kpis() agrega la tabla entera — pero sólo lo
        # ACTIVO, como la vista (regla #598): sin el filtro el KPI decía
        # S/ 179.395 y la vista S/ 56.674.
        "kpis": (("Valorizado", "VALORIZADO TOTAL", "sum",
                  tuple((c, (v,)) for c, v, _ in INVENTARIO_ACTIVO)),),
        "columnas": [
            "Nombre Familia", "Nombre Subfamilia", "Nombre Producto",
            "Unidad Kardex", "Codigo Producto", "Nombre Area", "Codigo Area", "Stock al Dia", "Precio Promedio", "Valorizado total"
        ],
        "filtros_cat": ["Nombre Area", "Nombre Familia"],
        "buscador": "Nombre Producto",
        "fecha": None,
        "agrupar": ["Nombre Area", "Nombre Familia", "Nombre Subfamilia"],
        "columnas_iniciales": [
            "Nombre Producto", "Stock al Dia", "Nombre Area", "Valorizado total",
        ],
        "columnas_movil": [
            "Nombre Producto", "Stock al dia", "Precio Promedio",
            "Valorizado total", "Nombre Area",
        ],
        "columnas_fijas_movil": 2,
    },
    "Ajuste de Inventario": {
        # El rail muestra "Ajuste de Inventario" (a pedido, 2026-09-21). La
        # clave ya era ese nombre, así que la franja de contexto y la cabecera
        # del rail (que usan `label_largo` y caen en la clave) ya lo mostraban;
        # sólo faltaba el ítem del rail, que toma `label_corto`. Sin
        # `label_largo` porque la clave ya coincide con el nombre a mostrar.
        "label_corto": "Ajuste de Inventario",
        "label_rail": "Ajuste",
        "area": "Inventario",
        "archivo": "ajusteinventario.parquet",
        # Lo que el kardex registró por cada cierre (regla #612): `cargar`
        # lo une al ajuste. Acá para que «Actualizar» pida los dos.
        "archivos_extra": (kardex.ARCHIVO_AJUSTES,),
        "icono": ":material/tune:",
        "kpis": (("Ajuste Valoriz.", "AJUSTE VALORIZADO", "sum"),),
        "kpi_fecha": "FECHA APERTURA INVENTARIO",
        "filtros_cat": [],  # Sin filtros de Área/Familia/Subfamilia en el popover
        "agrupar": [],      # Sin opción de "Agrupar por" en el popover
        "columnas_iniciales": [
            "Producto", "Precio Promedio", "Stock al Cierre",
            "Stock Declarado", "Ajuste", "Ajuste Valorizado",
        ],
        "derivar_periodo_pivote": True,
        # Sin `"cortes": True` desde el 2026-10-11 (regla #632): era lo que
        # le daba a la píldora de la franja los modos Corte y Varios, y la
        # franja de Ajuste ya no dibuja fecha. Cada vista elige su sesión de
        # inventario (`cortes.sesiones_inventario`) o sus meses. Los modos
        # se borraron el mismo día (regla #635): la clave ya no la lee nadie.
        "graficos": [
            {"tipo": "line",
             "x": ["FECHA APERTURA INVENTARIO", "MES"],
             "y": ["VALORIZADO TOTAL"],
             "color": ["FAMILIA"],
             "titulo": "Evolución del valorizado total por familia"},
            {"tipo": "line",
             "x": ["FECHA APERTURA INVENTARIO", "MES"],
             "y": ["AJUSTE VALORIZADO"],
             "color": ["FAMILIA"],
             "titulo": "Evolución del ajuste valorizado por familia"},
            {"tipo": "bar",
             "x": ["FAMILIA"],
             "y": ["AJUSTE VALORIZADO"],
             "color": ["AREA"],
             "titulo": "Ajuste valorizado por familia y área",
             "tickangle": -45},
        ],
    },
    # Requerimientos y Salidas comparten UN ítem de nav ("Movimientos", ver
    # `grupo_nav` en navegacion.py::inject_navegacion) — el par describe un
    # flujo real: Requerimiento es la salida de stock de Almacén Central
    # HACIA un área de producción; Salidas es la BAJA que esa misma área
    # registra después (consumo/merma/evento — ver `Tipo Descargo`). No hay
    # llave que una un Requerimiento con la Salida que lo "cierra" (numeran
    # documentos en secuencias independientes), así que el cruce entre
    # ambos (`graficos/movimientos_comun.py`, sus dos vistas de «Ambos») es
    # agregado por producto/familia/período, nunca documento a documento.
    # Confirmado con DuckDB directo contra R2 real (no demo) 2026-08-13:
    # 726 de los 968 productos de Salidas (75%) también aparecen en
    # Requerimientos — hay overlap real de producto entre los dos parquets
    # (0% overlap, por eso esas dos nunca se cruzan). Detalle en
    # arquitectura.md § Unificación Movimientos.
    # UN SOLO reporte de Movimientos desde el 2026-09-05. Hasta esa fecha
    # eran DOS entradas ("Requerimientos" y "Salidas") que un chip alternaba,
    # con `grupo_nav` para que el rail mostrara un solo botón. Se fusionaron a
    # pedido, el día después de que la Evolución empezara a dibujar los dos
    # lados en una figura: "esto ya no debería estar, ya que ahora muestra
    # ambos". Las ocho vistas viven hoy en una sola página, ver
    # graficos/movimientos.py y arquitectura.md regla #322.
    #
    # `archivo` es el de REQUERIMIENTOS y no es indistinto: de él salen los
    # KPIs de la franja, el rango de fecha, los chips (`filtros_cat`), el
    # buscador y las columnas de la Tabla pivote. Es el lado grande (144.636
    # filas contra 17.355) y el que tiene la tabla con tratamiento propio.
    # (Hasta el 2026-09-23 era además el único con área: desde ese día la
    # consulta de salidas trae `AREA`, ver arquitectura.md regla #509.)
    "Movimientos": {
        # Lo que ve el usuario es "Movimientos" (a pedido, 2026-09-22; antes
        # "Movimientos de Almacén"). La clave "Movimientos" es la IDENTIDAD
        # INTERNA del reporte (dispatcher de graficos/, slug CSS,
        # `_ultimo_<grupo>`) y coincide con el nombre a mostrar. Se declaran
        # igual los dos labels de todos modos: sin `label_corto` el rail cae en
        # `nombre.split()[0][:10]` y recortaría "Movimientos" a "Movimiento".
        "label_corto": "Movimientos",
        "label_largo": "Movimientos",
        "area": "Inventario",
        "archivo": "requerimientos.parquet",
        # El SEGUNDO parquet de la página. `app.py` sigue cargando uno solo
        # (`archivo`) y pasandolo como df_f; salidas.parquet lo carga
        # graficos/movimientos.py con data.cargar. Esta clave existe para que
        # el boton de refresco sepa que hay mas de un parquet detras del
        # reporte - sin ella, "Refrescar" dejaria las salidas viejas y no
        # habria forma de actualizarlas desde la UI. Ver
        # navegacion.py::boton_refresco. El TERCERO, porcionamientos.parquet,
        # llego el 2026-09-24 con la seccion "Porcionamientos" (regla #510):
        # lo carga la seccion misma, y va aca por lo mismo que salidas.
        # Los otros TRES llegaron el 2026-09-28 con "Consumo segun recetas"
        # (regla #558), que baja cada venta por las recetas base y los
        # porcionamientos hasta el insumo de compra: el primer nivel de las
        # recetas de venta, las recetas base y el maestro de productos (su
        # factor y su precio). Refrescar desde Movimientos los pide a todos:
        # si no, la seccion mezclaria recetas de hoy con precios de ayer.
        # Y ordenesproduccion.parquet llego el 2026-09-30 con la seccion
        # "Produccion" (regla #575): el reporte Produccion del Almacen.
        "archivos_extra": ("salidas.parquet", "porcionamientos.parquet",
                           "ordenesproduccion.parquet",
                           "paloteoinsumosnivel1.parquet", "recetabase.parquet",
                           "inventariovalorizado.parquet"),
        "icono": ":material/sync_alt:",
        "kpis": (("Valorizado", "VALOR ITEM", "sum"),
                 ("Requerim.", "COD REQUERIMIENTO", "count_distinct")),
        "kpi_fecha": "FECHA REGISTRO",
        # Columnas confirmadas contra el parquet real (2026-08-13, DuckDB
        # directo): destino del requerimiento es "Sub Almacen" (el área de
        # producción que lo pide — Cocina/Barra/Pastelería/...), cantidad/
        # valorizado son "Cantidad" / "Valor Item", el estado es "Nombre
        # Estado Requerimiento" (Procesado/Anulado/Generado), y la jerarquía
        # de producto es Nombre Familia > Nombre Subfamilia > Nombre
        # Producto — mismos nombres de columna "amigables" que salidas
        # (ambos vienen del mismo ERP, SAPIENS), aunque el código de
        # producto real es CODIGO PRODUCTO acá vs COD PRODUCTO en salidas.
        "fecha": "Fecha Registro",
        "filtros_cat": ["Sub Almacen", "Nombre Familia"],
        "buscador": "Nombre Producto",
        "columnas_movil": [
            "Nombre Producto", "Cantidad", "Valor Item", "Sub Almacen",
        ],
        "columnas_fijas_movil": 2,
    },
    # PRODUCCIÓN, un reporte propio desde el 2026-10-23 (regla #709): las
    # seis vistas de lo que se TRANSFORMA en casa —Porcionamientos, su
    # merma en tres vistas, las órdenes de producción y el consumo según
    # recetas— salieron de Movimientos, que se quedó con lo que se pide y lo
    # que se da de baja. Es la etapa 2 de la navegación del boceto del rail
    # compacto (#708).
    #
    # `archivo` es el de REQUERIMIENTOS, como el de Movimientos, y no es un
    # descuido: las secciones cargan sus propios parquets, pero los chips
    # «Sub Almacén» y «Familia», el orden de las áreas que reparte los
    # colores (Cocina del mismo color que en Movimientos, regla #509) y los
    # topes del botón de fecha de Consumo salen de ahí. Con otro `archivo`,
    # cada una de esas cosas cambiaba. Sin KPI: la columna ya no los muestra
    # (regla #596) y no hay un número único de «producción».
    "Producción": {
        "label_corto": "Producción",
        "archivo": "requerimientos.parquet",
        "archivos_extra": ("porcionamientos.parquet",
                           "ordenesproduccion.parquet",
                           "paloteoinsumosnivel1.parquet", "recetabase.parquet",
                           "inventariovalorizado.parquet", "recetaventa.parquet",
                           "compras.parquet"),
        "icono": ":material/skillet:",
        "fecha": "Fecha Registro",
        "filtros_cat": ["Sub Almacen", "Nombre Familia"],
        "buscador": "Nombre Producto",
    },
    # UN SOLO reporte de Recetas desde el 2026-09-04. Hasta esa fecha eran
    # DOS entradas ("Receta Base" y "Receta Venta") que un chip Base/Venta
    # alternaba, apoyadas en una medición equivocada que decía que los dos
    # parquets no se cruzaban (comparó `COD RB`, el ID interno, en vez de
    # `COD PROD RB` — ver arquitectura.md regla #303). Se fusionaron a
    # pedido: "quiero que las visualizaciones de estos toggles figuren todas
    # juntas". Las nueve vistas viven hoy en una sola página, ver
    # graficos/recetas.py.
    #
    # Sigue compartiendo ítem de nav con "Nueva Receta" (`grupo_nav`, ver
    # navegacion.py::inject_navegacion): el chip que queda es el puente
    # hacia ese formulario, no un selector de fuente de datos.
    "Recetas": {
        "fecha": None,  # catálogo (foto completa): sin filtro de fecha
        # Lo que ve el usuario es "Recetas y Costos" (a pedido, 2026-09-22;
        # antes "Recetas"). La CLAVE del dict sigue siendo "Recetas": es la
        # identidad interna (dispatcher de graficos/, slug CSS
        # `app_reporte_recetas`, citas de arquitectura.md) y NO se renombra.
        # `label_largo` renombra la franja de contexto (que si no cae en la
        # clave "Recetas"). Hasta el 2026-09-22 vivía además `grupo_nav`:
        # "Nueva Receta" era un reporte hermano (tool: True) y los dos se
        # dibujaban como UN solo botón del rail. Al bajar "Nueva receta" a ser
        # una VISTA de este mismo reporte (rail interno, ver
        # `graficos/recetas.py::_RAIL_CATEGORIAS`), el grupo quedó de un solo
        # miembro y desapareció junto con el chip Recetas/+ Nueva.
        "label_corto": "Recetas y Costos",
        "label_largo": "Recetas y Costos",
        "label_rail": "Recetas",
        "archivo": "recetaventa.parquet",
        # El SEGUNDO parquet de la página. `app.py` sigue cargando uno solo
        # (`archivo`) y pasándolo como df_f; recetabase.parquet lo carga
        # graficos/recetas.py con data.cargar. Esta clave existe para que el
        # botón de refresco sepa que hay más de un parquet detrás del
        # reporte — sin ella, "Refrescar" dejaría las recetas base viejas y
        # no habría forma de actualizarlas desde la UI. Ver
        # navegacion.py::boton_refresco.
        # Desde el 2026-09-26, también la carta costeada (toda la carta con
        # su % de costo, combos incluidos), que carga la sección «Carta
        # costeada» de graficos/recetas.py (regla #548). Y desde el
        # 2026-09-30 las órdenes de producción y el primer nivel de las
        # ventas, que lee «Costo Recetas Base» (regla #576). Y desde el
        # 2026-10-04 la composición de los combos, que lee «Nuevo Costeo ›
        # Modificar › Combo» (regla #608): sin ella acá, el botón no tenía
        # cómo traerla y había que pedirla a mano.
        "archivos_extra": ("recetabase.parquet", "cartacosteada.parquet",
                           "ordenesproduccion.parquet",
                           "paloteoinsumosnivel1.parquet",
                           "combosdetalle.parquet"),
        "icono": ":material/receipt_long:",
        # Catálogo sin fecha: el KPI es un conteo, no un agregado por período
        # (kpi_fecha ausente a propósito — resumen_kpis() agrega la tabla
        # entera cuando no hay fecha, igual que hace este reporte mismo).
        # Solo "Platos": el KPI "Recetas" (count_distinct de COD RB) se fue
        # con la fusión porque resumen_kpis() agrega el df del `archivo`, y
        # COD RB vive en el parquet secundario.
        "kpis": (("Platos", "COD RV", "count_distinct"),),
    },
    "Ventas": {
        "label_corto": "Ventas",
        "archivo": "ventas.parquet",
        "icono": ":material/payments:",
        # "Pax" se repite en cada línea de un mismo pedido (una fila por
        # ítem vendido): sumarlo directo infla el conteo. kpi_dedup agrupa
        # por pedido ANTES de sumar/contar — mismo criterio que ya usa
        # graficos/ventas_resumen.py (groupby pedido, max pax, sum por día).
        # "Venta" no necesita el dedup por sí sola (sumar por línea o por
        # pedido-ya-sumado da lo mismo, es asociativo), pero como
        # resumen_kpis() aplica el mismo dedup a toda la tupla de kpis de
        # un reporte, viaja gratis en la misma consulta.
        "kpis": (("Venta", "VENTA ITEM DDOCUMENTO", "sum"),
                 ("Pax", "CANT PAX", "sum_dedup")),
        "kpi_fecha": "FEC REG DOCUMENTO",
        "kpi_dedup": "LLAVE LOCAL PEDIDO",
        # Y ANTES de eso, un ítem una vez: el parquet trae una fila por ítem
        # Y POR FORMA DE PAGO, así que la venta de un plato pagado con dos
        # formas sumaba doble (+17 % en septiembre 2026, regla #517). Es la
        # misma llave que usa `graficos/ventas.py::unico_por_item`.
        "kpi_item": "LLAVE LOCAL DOCUMENTO ITEM",
        # Carga filtrada por rango de fechas DENTRO de DuckDB (no baja todo
        # el parquet). Al primer acceso: 01-del-mes-actual → hoy. El rango
        # aplicado vive en st.session_state[f"rango_carga_{reporte}"] y el
        # date_input del popover lo controla (ver app.py).
        "carga_por_rango": "FEC REG DOCUMENTO",
    },
    # El costo de ventas por mes operativo (2026-10-09, regla #622): cruza
    # cuatro parquets y ninguno es su dueño. `archivo` es el de los CIERRES de
    # inventario —el que `app.py` carga y le pasa al dashboard—; compras,
    # salidas y la venta por grupo los lee `graficos/costos.py`. Sin fecha en
    # la franja: el eje son los meses operativos, que arma la tabla.
    "Costos": {
        "label_corto": "Costos",
        "label_largo": "Costos",
        "archivo": "ajusteinventario.parquet",
        # Para que «Actualizar» pida también lo que suma la tabla. Ventas NO
        # va, por lo mismo que en Recetas: regenerar el parquet más pesado
        # para refrescar una fila; se actualiza con su reporte.
        # Y el kardex, del que salen las semanas y quincenas.
        "archivos_extra": ("compras.parquet", "salidas.parquet", kardex.ARCHIVO),
        "icono": ":material/calculate:",
        "fecha": None,
    },
    "Inspector": {
        "label_corto": "Inspector",
        # Herramienta de verificación de datos crudos (no es un parquet propio):
        # permite inspeccionar cualquiera de los archivos de arriba.
        "icono": ":material/search:",
        "tool": True,
    },
}


# ===========================================================================
# CONEXIÓN A R2 VIA DUCKDB
# ===========================================================================

# UNA CONEXIÓN POR HILO, no una por proceso (2026-10-03, regla #599). Hasta
# ese día `get_conn` era un `@st.cache_resource` que devolvía la MISMA
# conexión a todas las sesiones, y cada sesión corre en su propio hilo. Una
# conexión de DuckDB no es segura entre hilos: `execute` deja el resultado
# colgado de la conexión y `fetchone` lee el que haya, así que si otra sesión
# ejecuta algo en el medio, uno se lleva la fila del otro. Medido con dos
# hilos: 464 de 1.500 consultas de KPIs recibieron la fila de un `DESCRIBE`
# ajeno, y otras 483 un `None`. En Cloud se vio como un `ValueError` en
# `navegacion.py::_fmt_kpi`: «Documentos» de Compras llegó con un NOMBRE DE
# COLUMNA. Y lo que sale de esa carrera se cachea como si fuera el dato.
#
# La base (con httpfs cargado) sigue siendo una por proceso; cada hilo usa
# un cursor propio. Los `SET s3_*` son de SESIÓN: un cursor no los hereda
# (medido: sin repetirlos, la lectura de R2 da 404), así que se le aplican
# al crearlo. Streamlit corre cada sesión en su hilo, y el `threading.local`
# se libera solo cuando el hilo termina.
@st.cache_resource
def _conexion_base():
    """La base DuckDB del proceso, con httpfs cargado. No se consulta
    directo: `get_conn` le saca un cursor por hilo."""
    try:
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")
        return con
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        st.stop()


_CONEXION_DEL_HILO = threading.local()


def get_conn():
    """La conexión a R2 de ESTE hilo: un cursor de `_conexion_base`, con la
    configuración S3. Se crea la primera vez que el hilo la pide."""
    base = _conexion_base()
    con = getattr(_CONEXION_DEL_HILO, "con", None)
    if con is not None and getattr(_CONEXION_DEL_HILO, "base", None) is base:
        return con
    try:
        con = base.cursor()
        con.execute(f"""
            SET s3_endpoint='{st.secrets["R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com';
            SET s3_access_key_id='{st.secrets["R2_ACCESS_KEY"]}';
            SET s3_secret_access_key='{st.secrets["R2_SECRET_KEY"]}';
            SET s3_region='auto';
            SET s3_url_style='path';
        """)
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        st.stop()
    _CONEXION_DEL_HILO.con, _CONEXION_DEL_HILO.base = con, base
    return con


# ===========================================================================
# CLIENTE S3-COMPATIBLE PARA R2 (metadata + señales de refresco)
# ===========================================================================
# Separado de get_conn() (DuckDB): ese solo sirve para SELECT sobre parquets.
# Este cliente boto3 sirve para head_object (fecha de modificación) y
# put_object (dejar la señal JSON de refresco).

@st.cache_resource
def get_s3_cliente():
    try:
        return boto3.client(
            "s3",
            endpoint_url=f"https://{st.secrets['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=st.secrets["R2_ACCESS_KEY"],
            aws_secret_access_key=st.secrets["R2_SECRET_KEY"],
            region_name="auto",
        )
    except Exception as e:
        st.error(f"Error creando cliente R2: {str(e)}")
        return None


def fecha_ultima_actualizacion(archivo):
    """Fecha de última modificación (LastModified) del parquet en R2, en UTC.
    Retorna None en modo demo o si algo falla (nunca lanza excepción)."""
    if not secrets_disponibles():
        return None
    try:
        s3 = get_s3_cliente()
        resp = s3.head_object(Bucket=st.secrets["R2_BUCKET"], Key=archivo)
        return resp["LastModified"]
    except Exception:
        return None


# Umbral de frescura de los parquets. El extractor nocturno corre a las 03:00
# todos los días, así que a las 02:59 un dato de 24h es lo NORMAL y 26 deja
# dos horas de margen. Pasado eso, se saltó al menos una corrida entera.
#
# Existe porque el 2026-09 la extracción estuvo corriendo 1 vez cada 4 días
# —sin fallar: se colgaba DESPUÉS de trabajar— y nadie se enteró hasta que un
# reporte salió vacío por casualidad, al cambiar de mes el rango por defecto.
# El dato viejo no se delata solo: hay que preguntarle la edad.
HORAS_DATO_VIEJO = 26


def antiguedad_datos(archivos):
    """Antigüedad del parquet MÁS VIEJO de `archivos`: `(horas, fecha_utc)`.

    Se queda con el más viejo porque un reporte puede apoyarse en más de un
    parquet (`archivos_extra` en REPORTES) y basta con que uno esté atrasado
    para que lo que se ve en pantalla lo esté.

    Retorna None si no se puede saber: modo demo, fallo de red, o un reporte
    sin parquet (las herramientas). Nunca lanza — un aviso de frescura no
    puede ser el motivo de que la app no cargue.
    """
    fechas = []
    for archivo in archivos:
        if not archivo:
            continue
        try:
            f = fecha_ultima_actualizacion(archivo)
        except Exception:
            f = None
        if f is not None:
            fechas.append(f)
    if not fechas:
        return None
    mas_vieja = min(fechas)
    horas = (datetime.now(timezone.utc) - mas_vieja).total_seconds() / 3600
    return horas, mas_vieja


def hay_dato_nuevo(archivo, fecha_base):
    """
    True si el parquet en R2 tiene una fecha de modificación MÁS RECIENTE
    que 'fecha_base' (el LastModified capturado justo ANTES de pedir el
    refresco). Sirve para saber, sin recargar a ciegas, si el proceso
    externo (atender_solicitudes.py) ya terminó de subir el archivo nuevo.
    """
    actual = fecha_ultima_actualizacion(archivo)
    if actual is None:
        return False
    if fecha_base is None:
        return True
    return actual > fecha_base


def solicitar_refresco(archivo, reporte):
    """
    Solicita el refresco de UN SOLO reporte (nunca de toda la app):
      1) Escribe un JSON de señal en R2 (carpeta _solicitudes_refresco/).
      2) YA NO limpia el caché aquí: el parquet en R2 todavía no cambió en
         este instante (el proceso externo recién va a regenerarlo).
         Limpiar aquí solo lograba que la webapp re-descargara y re-cacheara
         el dato VIEJO. La limpieza ahora la dispara app.py::_vigilar_refresco()
         una vez que confirma (vía LastModified) que el archivo ya cambió.
    """
    if not secrets_disponibles():
        return True  # modo demo: no hay R2, nada más que hacer

    try:
        s3 = get_s3_cliente()
        payload = {
            "reporte": reporte,
            "archivo": archivo,
            "solicitado_en": datetime.now(timezone.utc).isoformat(),
        }
        clave = f"_solicitudes_refresco/{archivo.replace('.parquet', '')}.json"
        s3.put_object(
            Bucket=st.secrets["R2_BUCKET"],
            Key=clave,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        return True
    except Exception as e:
        st.error(f"No se pudo enviar la solicitud de refresco: {str(e)}")
        return False


# ===========================================================================
# MODO DEMO (sin credenciales R2)
# ===========================================================================
# Cuando NO hay secrets de R2 configurados (p.ej. al correr la app en local o
# en un entorno de pruebas), la app entra en "modo demo" y genera datos
# sintéticos en memoria, para que TODOS los reportes se puedan abrir y las
# tablas/gráficos rendericen sin depender de la nube. En producción (con los
# secrets puestos) esto no se activa y el comportamiento es el de siempre.

_SECRETS_R2 = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_BUCKET")


def secrets_disponibles():
    """True si están todos los secrets de R2; False si falta alguno (o no hay
    archivo de secrets). Nunca lanza excepción."""
    try:
        return all(k in st.secrets for k in _SECRETS_R2)
    except Exception:
        return False


def _datos_demo(archivo, filas=60):
    """Genera un DataFrame sintético acorde al reporte pedido.

    La semilla deriva del NOMBRE del archivo, para que cada reporte dé
    siempre los mismos números y comparar dos capturas signifique algo.

    crc32 y no hash(): el hash de str en Python va salteado por proceso
    (PYTHONHASHSEED), así que con `abs(hash(archivo))` el demo cambiaba en
    CADA reinicio del server — justo lo contrario de lo que decía este
    docstring. crc32 es determinista entre procesos y máquinas.
    """
    rng = np.random.default_rng(zlib.crc32(archivo.encode("utf-8")))
    n = filas

    if archivo == "inventariovalorizado.parquet":
        stock = rng.integers(0, 250, n)
        precio = rng.uniform(0.5, 120, n).round(2)
        df = pd.DataFrame({
            "Nombre Familia": rng.choice(["Carnes", "Bebidas", "Verduras", "Abarrotes", "Lácteos"], n),
            "Nombre Subfamilia": rng.choice(["Tipo A", "Tipo B", "Tipo C"], n),
            "Nombre Producto": [f"Producto demo {i:03d}" for i in range(n)],
            "Unidad Kardex": rng.choice(["UND", "KG", "LT"], n),
            "Codigo Producto": [f"P{i:05d}" for i in range(n)],
            "Nombre Area": rng.choice(["Cocina", "Bar", "Almacén", "Salón"], n),
            "Codigo Area": rng.choice(["A01", "A02", "A03", "A04"], n),
            "Stock al Dia": stock,
            "Precio Promedio": precio,
        })
        df["Valorizado total"] = (df["Stock al Dia"] * df["Precio Promedio"]).round(2)
        return df

    if archivo == "ajusteinventario.parquet":
        # Nombres en MAYUSCULAS como el parquet real (por eso _titulo_es
        # existe: convierte "STOCK AL CIERRE" -> "Stock al Cierre" en las
        # cabeceras). FECHA APERTURA INVENTARIO trae hora al minuto, igual
        # que en produccion: es lo que obliga a las columnas derivadas
        # (Mes)/(Dia) de app.py para el Modo pivote.
        n = 240
        # Anclado al AÑO EN CURSO, no a una fecha fija: la vista "Por fecha
        # de corte" filtra por `_dt.date.today().year` y NO depende del
        # rango de la franja (ver graficos/ajuste/_pivote.py). Con fechas de
        # 2024 esa vista salia siempre "Sin datos de <año>" y era la unica
        # del rail que no se podia verificar en local.
        #
        # AGRUPADAS EN SESIONES, no repartidas al azar (2026-08-09). Hasta
        # esa fecha las 240 filas caian uniformes sobre 300 dias: eso da
        # ~150 dias con movimiento separados por 1 dia, y como un corte
        # admite saltos de hasta 4 dias (cortes.py), TODO el año colapsaba
        # en UN corte. Resultado: ni el slider del mapa de calor ni el modo
        # Cortes de la franja se podian probar en local — el bug que este
        # bloque ya habia arreglado una vez, con otra cara.
        # Ahora el demo imita la forma real del dato: sesiones de conteo de
        # 1 a 4 dias, separadas por semanas, MAS dias sueltos de ajuste
        # diario entre medio (que es lo que hace que un corte NO sea
        # contiguo y justifica el filtro por conjunto).
        _hoy_aj = pd.Timestamp.now().normalize()
        _ini_aj = max(_hoy_aj - pd.Timedelta(days=300),
                      pd.Timestamp(_hoy_aj.year, 1, 1))
        _dias_aj = []
        _cursor = _ini_aj
        while _cursor < _hoy_aj - pd.Timedelta(days=6):
            _largo = int(rng.integers(1, 5))          # sesion de 1 a 4 dias
            for _k in range(_largo):
                # Salto interno de 1 o 2 dias: el de 2 deja un hueco DENTRO
                # de la sesion (el "fin de semana de por medio" real).
                _cursor = _cursor + pd.Timedelta(days=int(rng.integers(1, 3)))
                if _cursor >= _hoy_aj:
                    break
                _dias_aj.append(_cursor)
            # Hasta la proxima sesion: 12 a 28 dias (> 4 => corte nuevo).
            _cursor = _cursor + pd.Timedelta(days=int(rng.integers(12, 29)))
        if not _dias_aj:                               # guarda: año recien
            _dias_aj = [_ini_aj]                       # empezado
        _dias_aj = np.array(_dias_aj, dtype="datetime64[ns]")
        fechas = pd.to_datetime(rng.choice(_dias_aj, n)) + pd.to_timedelta(
            rng.integers(0, 1440, n), unit="m")
        cierre = rng.uniform(0, 400, n).round(2)
        # ~55% sin diferencia (el caso real dominante), el resto falta o sobra.
        delta = np.where(rng.random(n) < 0.55, 0.0,
                         rng.uniform(-40, 40, n).round(2))
        precio = rng.uniform(0.5, 120, n).round(2)
        df = pd.DataFrame({
            "FECHA APERTURA INVENTARIO": fechas,
            "AREA": rng.choice(["Cocina", "Bar", "Almacén", "Salón"], n),
            "FAMILIA": rng.choice(["Carnes", "Bebidas", "Verduras",
                                   "Abarrotes", "Lácteos"], n),
            "SUBFAMILIA": rng.choice(["Tipo A", "Tipo B", "Tipo C"], n),
            "CODIGO PRODUCTO": [f"P{i % 80:05d}" for i in range(n)],
            "PRODUCTO": [f"Producto demo {i % 80:03d}" for i in range(n)],
            "UNIDAD MEDIDA": rng.choice(["UND", "KG", "LT"], n),
            "PRECIO PROMEDIO": precio,
            "STOCK AL CIERRE": cierre,
        })
        df["STOCK DECLARADO"] = (cierre + delta).round(2)
        df["AJUSTE"] = delta.round(2)
        df["AJUSTE VALORIZADO"] = (df["AJUSTE"] * precio).round(2)
        df["VALORIZADO TOTAL"] = (cierre * precio).round(2)
        return df

    if archivo == "salidas.parquet":
        cant = rng.integers(1, 60, n)
        precio = rng.uniform(1, 80, n).round(2)
        df = pd.DataFrame({
            "Fecha registro": pd.date_range("2025-01-01", periods=n, freq="D"),
            "Codigo Producto": [f"P{i:05d}" for i in range(n)],
            "Nombre Producto": [f"Producto demo {i:03d}" for i in range(n)],
            "Sub Almacen": rng.choice(["Cocina", "Bar", "Almacén Central", "Salón"], n),
            "Nombre Familia": rng.choice(["Carnes", "Bebidas", "Verduras", "Abarrotes"], n),
            "Nombre SubFamilia": rng.choice(["Tipo A", "Tipo B", "Tipo C"], n),
            "Tipo Descargo": rng.choice(["Consumo Interno", "Merma", "Transferencia"], n,
                                        p=[0.55, 0.2, 0.25]),
            "Cant Salida": cant,
        })
        df["Valor Neto"] = (cant * precio).round(2)
        return df

    if archivo == "porcionamientos.parquet":
        # El GRANO REAL, que es la trampa de este parquet (regla #510): una
        # fila por CORTE —cada producto que salió—, con la cabecera del
        # porcionamiento repetida en cada una. Y los cuadres del real:
        # cantidad = aprovechado + merma, los pesos de los cortes suman lo
        # aprovechado, y cantidad × precio de los cortes suma el costo de lo
        # que entró. Mismas fechas y áreas que el demo de requerimientos,
        # para que se vea con el rango de la franja y los mismos colores.
        _insumos = [("P00001", "Lomo fino entero x Kg", 65.0,
                     [("Lomo fino porción 180 gr", "UND", 0.18),
                      ("Recorte de lomo x Kg", "KILOS", 1.0)]),
                    ("P00002", "Entraña fina importada x Kg", 108.0,
                     [("Entraña porción 250 gr", "UND", 0.25)]),
                    ("P00003", "Chirimoya", 8.0,
                     [("(P) Pulpa de chirimoya x Kg", "KILOS", 1.0)]),
                    ("P00004", "Pulpo fresco entero x Kg", 55.0,
                     [("Pulpo limpio x Kg", "KILOS", 1.0),
                      ("Tentáculo de pulpo x Kg", "KILOS", 1.0)])]
        filas = []
        for i, fecha in enumerate(pd.date_range("2025-01-01", periods=n,
                                                freq="D")):
            cod, nombre, precio, salen = _insumos[int(rng.integers(0, 4))]
            cant = float(rng.uniform(2, 25).round(3))
            merma = round(cant * float(rng.uniform(0.08, 0.45)), 3)
            util = round(cant - merma, 3)
            costo = cant * precio
            partes = rng.dirichlet(np.ones(len(salen)))
            for (fin, unid_fin, kg_unidad), parte in zip(salen, partes):
                peso = round(util * float(parte), 3)
                cant_fin = (round(peso / kg_unidad) if unid_fin == "UND"
                            else peso) or 1
                filas.append({
                    "COD PORC": f"25{fecha.month:02d}{i:06d}",
                    "COD PROD INIC": cod, "PROD INICIAL": nombre,
                    "FEC REGIST": fecha + pd.Timedelta(
                        minutes=int(rng.integers(420, 1200))),
                    "USUARIO REG": rng.choice(["CARLOS", "MMASIAS",
                                               "MQUISPE"]),
                    "UNID PROD INIC": "KILOS",
                    "CANT A PORCIONAR": cant, "CANT TOT RESUL": util,
                    "CANT MERMA": merma, "COD AREA": "003",
                    "SUB ALMACEN": rng.choice(["Producción", "Cocina",
                                               "Bar"], p=[0.7, 0.2, 0.1]),
                    "COD PROD FINAL": f"F{cod[1:]}{len(filas):03d}",
                    "PROD FINAL RESULT": fin, "CANT RESULT": cant_fin,
                    "UNID PROD FIN": unid_fin,
                    "PREC PROM PROD FIN": round(costo * float(parte)
                                                / cant_fin, 4),
                    "PESO RESULT": peso,
                })
        df = pd.DataFrame(filas)
        # La cabecera es UNA por porcionamiento: el área y el usuario del
        # primer corte valen para todos (en el real no cambian de un corte a
        # otro, y un demo que los mezclara enseñaría otra cosa).
        for col in ("SUB ALMACEN", "USUARIO REG"):
            df[col] = df.groupby("COD PORC")[col].transform("first")
        return df

    if archivo == "ordenesproduccion.parquet":
        # El GRANO REAL (regla #575): una fila por ORDEN y por receta base
        # producida en ella, con la cabecera —área, estado, usuario— repetida
        # en cada una. Casi todas procesadas; alguna generada (no suma: no
        # produjo nada) y alguna anulada, como en el real. La cantidad va en
        # la unidad de entrada y el precio es el costo por esa unidad.
        _recetas = [("(Rs) Salsa de lomo x Kg", "KILOS", 18.0),
                    ("(Rs) Arroz con choclo 200gr x por", "UND", 1.4),
                    ("(Rs) Batch Herbal (Bar)", "LITROS", 7.6),
                    ("(Rs) Creme brulee x und", "UND", 8.5),
                    ("(Rs) Vinagreta Cesar x Lt", "LITROS", 12.6)]
        filas = []
        for i, fecha in enumerate(pd.date_range("2025-01-01", periods=n,
                                                freq="D")):
            area = rng.choice(["COCINA", "PRODUCCION", "BARRA", "PASTELERIA"],
                              p=[0.5, 0.2, 0.15, 0.15])
            estado = rng.choice(["PROCESADO", "GENERADO", "ANULADO"],
                                p=[0.94, 0.03, 0.03])
            usuario = rng.choice(["CARLOS", "MMASIAS"])
            for item in range(int(rng.integers(1, 4))):
                prod, unid, precio = _recetas[int(rng.integers(0, 5))]
                cant = (float(rng.integers(5, 30)) if unid == "UND"
                        else float(rng.uniform(0.3, 5).round(3)))
                filas.append({
                    "COD ORDEN PRODUCCION": f"25{i:08d}",
                    "ITEM": f"{item + 1:03d}",
                    "FECHA REGISTRO": fecha + pd.Timedelta(
                        minutes=int(rng.integers(480, 1080))),
                    "AREA": area, "NOMBRE ESTADO": estado,
                    "USUARIO REGISTRO": usuario,
                    "NOMBRE PRODUCTO": prod,
                    "NOMBRE FAMILIA": ("BEBIDAS CON ALCOHOL" if "Batch" in prod
                                       else "ALIMENTOS"),
                    "CANTIDAD": cant, "UNIDAD": unid, "PRECIO UNIT": precio,
                    "VALOR ITEM": round(cant * precio, 4),
                })
        return pd.DataFrame(filas)

    if archivo == "requerimientos.parquet":
        # Mismos códigos de producto que el demo de salidas.parquet
        # (P00000-P00059, arriba): así el comparativo Pedido vs Baja
        # (graficos/movimientos_comun.py) tiene con qué cruzar en local.
        # Requerimiento es la salida de Almacén Central HACIA un área — no
        # confundir con salidas.parquet, que es la baja que esa área
        # registra después (ver comentario en REPORTES, data.py).
        cant = rng.integers(1, 40, n)
        precio = rng.uniform(1, 80, n).round(2)
        df = pd.DataFrame({
            "Fecha Registro": pd.date_range("2025-01-01", periods=n, freq="D"),
            "Codigo Producto": [f"P{i:05d}" for i in range(n)],
            "Nombre Producto": [f"Producto demo {i:03d}" for i in range(n)],
            "Sub Almacen": rng.choice(["Cocina", "Bar", "Pastelería", "Producción"], n),
            "Nombre Familia": rng.choice(["Carnes", "Bebidas", "Verduras", "Abarrotes"], n),
            "Nombre Subfamilia": rng.choice(["Tipo A", "Tipo B", "Tipo C"], n),
            "Nombre Estado Requerimiento": rng.choice(
                ["Procesado", "Anulado", "Generado"], n, p=[0.9, 0.06, 0.04]),
            "Cantidad": cant,
        })
        df["Valor Item"] = (cant * precio).round(2)
        return df

    if archivo == "ventas.parquet":
        # Ventas usa carga_por_rango (ver REPORTES): el rango por defecto es
        # "01-del-mes-actual -> hoy", así que a diferencia del resto de los
        # demos (fechas fijas en el pasado) este ancla al día de HOY o la
        # carga inicial devuelve 0 filas y la app corta con "no se pudieron
        # cargar los datos" antes de llegar a ningún dashboard.
        n_pedidos = 40
        fechas_pedido = pd.date_range(end=pd.Timestamp.now().normalize(),
                                      periods=n_pedidos, freq="D")
        pax_pedido = rng.integers(1, 12, n_pedidos)
        lineas_pedido = rng.integers(1, 5, n_pedidos)
        filas = []
        for i in range(n_pedidos):
            for _ in range(lineas_pedido[i]):
                filas.append({
                    "Fec Reg Documento": fechas_pedido[i],
                    "Llave Local Pedido": f"PED{i:04d}",
                    "Cant Pax": int(pax_pedido[i]),
                    "Nomb Item Venta": f"Producto demo {rng.integers(0, 50):03d}",
                    "Grupo": rng.choice(["Comida", "Bebida", "Postre"]),
                    "Sub Grupo": rng.choice(["Tipo A", "Tipo B"]),
                    "Cantidad Item Ddocumento": int(rng.integers(1, 5)),
                })
        df = pd.DataFrame(filas)
        precio = rng.uniform(10, 80, len(df)).round(2)
        df["Venta Item Ddocumento"] = (df["Cantidad Item Ddocumento"] * precio).round(2)
        df["Precio Costo"] = (df["Venta Item Ddocumento"]
                              * rng.uniform(0.25, 0.45, len(df))).round(2)
        return df

    if archivo == "compras.parquet":
        # Compras resuelve 12 columnas (ver graficos/compras/__init__.py) y
        # sus drills se apagan uno por uno si falta alguna. Hasta el
        # 2026-08-08 este reporte caía al bloque genérico de más abajo, que
        # no trae Proveedor: el drill de Proveedor —el más grande del
        # dashboard, 1.577 líneas— mostraba "Faltan columnas (Proveedor,
        # Valor)" y NO se podía abrir en local. Es decir, no se podía tocar
        # sin desplegar a producción para ver el resultado.
        #
        # El grano es el REAL: una fila por línea de documento de compra
        # (un documento trae varias líneas, de un solo proveedor).
        _provs = ["Distribuidora Andina", "Alimentos del Sur", "Frigorífico Lima",
                  "Bebidas Perú", "Agro Import", "Comercial Río", "Lácteos Norte"]
        _fams = {
            "Carnes":    (["Res", "Cerdo", "Aves"],            ["KG"]),
            "Bebidas":   (["Gaseosas", "Aguas", "Cervezas"],   ["UND", "LT"]),
            "Verduras":  (["Hoja", "Raíz", "Fruto"],           ["KG"]),
            "Abarrotes": (["Granos", "Aceites", "Conservas"],  ["KG", "UND"]),
            "Lácteos":   (["Quesos", "Yogures"],               ["KG", "LT"]),
        }
        # Anclado a HOY (como ventas): el rango por defecto de la franja es
        # 01-del-mes → hoy, así que con fechas fijas en el pasado el
        # dashboard abriría vacío. 140 días dan Semana/Mes/Año con datos.
        _n_docs = 150
        _fechas_doc = pd.to_datetime(pd.Timestamp.now().normalize()) - pd.to_timedelta(
            rng.integers(0, 140, _n_docs), unit="D")
        filas = []
        for _i in range(_n_docs):
            # Proveedor y numero se fijan UNA vez por documento: sus lineas
            # comparten ambos. Calcularlos dentro del bucle interno daria un
            # documento distinto por linea y la tabla de documentos del drill
            # mostraria 1 linea por comprobante, que no es el caso real.
            _prov = _provs[int(rng.integers(0, len(_provs)))]
            _num_doc = f"F{_i:04d}-{rng.integers(100, 999)}"
            for _ in range(int(rng.integers(1, 6))):   # líneas del documento
                _fam = list(_fams)[int(rng.integers(0, len(_fams)))]
                _subs, _ums = _fams[_fam]
                filas.append({
                    "Fecha documento": _fechas_doc[_i],
                    "Num Documento": _num_doc,
                    "Nombre proveedor": _prov,
                    "Nombre Familia": _fam,
                    "Nombre Subfamilia": _subs[int(rng.integers(0, len(_subs)))],
                    "Nombre producto": f"Producto demo {rng.integers(0, 60):03d}",
                    "Unidad": _ums[int(rng.integers(0, len(_ums)))],
                    "Cantidad compra": int(rng.integers(1, 80)),
                })
        df = pd.DataFrame(filas)
        _punit = rng.uniform(2, 90, len(df)).round(2)
        df["Precio unit"] = _punit
        df["Valor compra"] = (df["Cantidad compra"] * _punit).round(2)
        # Comparables del año anterior: columnas propias del parquet real,
        # no derivadas de la fecha. ±35% sobre el valor/precio actual.
        df["Valor año anterior"] = (
            df["Valor compra"] * rng.uniform(0.65, 1.35, len(df))).round(2)
        df["Ultimo precio unit"] = (
            _punit * rng.uniform(0.8, 1.2, len(df))).round(2)
        return df

    if archivo == "recetaventa.parquet":
        # Nombres EXACTOS del parquet real (confirmado contra R2 2026-08-13,
        # ver graficos/recetas_comun.py). Hasta acá este archivo caía al
        # bloque genérico de más abajo, sin "Nomb Plato"/"Item Rv": el
        # dashboard mostraba "columnas no reconocidas" y no se podía
        # verificar en local — ver memoria de proyecto
        # `esquema-real-compras-recetaventa`. El grano es el real: una fila
        # por ítem/insumo dentro de un plato.
        #
        # GRUPO/SUBGRUPO/P.VENTA SALON/CST SALON/%CST SALON/INS RV
        # (sumados 2026-08-24 para la tabla "Composición", que desde el
        # 2026-09-28 es el panel del plato de la Carta costeada, regla
        # #556) son atributos del
        # PLATO —no del ítem—, confirmados contra R2 real: un valor por
        # COD PLATO, repetido en cada fila-ítem. Por eso se generan UNA
        # vez por plato, DESPUÉS de armar sus ítems: CST SALON tiene que
        # cuadrar con la suma de TOTAL, igual que en el parquet real (si
        # no, la receta de la derecha de la tabla no sumaría lo mismo que
        # el Costo Salón de la izquierda).
        _n_platos = 45
        _platos = [f"Plato demo {i:03d}" for i in range(_n_platos)]
        _insumos_pool = [f"Insumo demo {i:03d}" for i in range(35)]
        _grupos_demo = {
            "Alimentos": ["Fondos", "Entradas", "Postres"],
            "Bebidas c/ Alcohol": ["Cocteles", "Piscos"],
            "Bebidas Calientes": ["Infusiones"],
        }
        filas = []
        for _i, _plato in enumerate(_platos):
            _n_ins = int(rng.integers(3, 9))
            _ins_plato = rng.choice(_insumos_pool, _n_ins, replace=False)
            _items_plato = []
            for _ins in _ins_plato:
                _cant = round(float(rng.uniform(0.05, 3.0)), 3)
                _costo_unit = round(float(rng.uniform(0.5, 25.0)), 4)
                _items_plato.append({
                    "COD PLATO": f"PL{_i:04d}",
                    "NOMB PLATO": _plato,
                    # Formato REAL confirmado: "ACTIV"/"INACTIV" (distinto
                    # al de recetabase, ver _activo() en recetas_comun.py).
                    "ITEM VENTA ACTIVO": "ACTIV" if rng.random() < 0.75 else "INACTIV",
                    "COD INS": f"IN{_insumos_pool.index(_ins):04d}",
                    "ITEM RV": _ins,
                    # Insumo REAL: el nombre descriptivo. En el parquet
                    # real "ITEM RV" es el número de LÍNEA dentro de la
                    # receta, no el insumo — ver arquitectura.md regla #205.
                    "INS RV": _ins,
                    "INS ACTIVO": "ACTIV" if rng.random() < 0.95 else "INACTIV",
                    "CANTIDAD": _cant,
                    "TOTAL": round(_cant * _costo_unit, 2),
                })
            _grupo = str(rng.choice(list(_grupos_demo.keys())))
            _subgrupo = str(rng.choice(_grupos_demo[_grupo]))
            _costo_plato = round(sum(f["TOTAL"] for f in _items_plato), 2)
            _pct = round(float(rng.uniform(0.15, 0.45)), 4)
            _precio_plato = round(_costo_plato / _pct, 2) if _pct else 0.0
            for f in _items_plato:
                f["GRUPO"] = _grupo
                f["SUBGRUPO"] = _subgrupo
                f["P.VENTA SALON"] = _precio_plato
                f["CST SALON"] = _costo_plato
                f["%CST SALON"] = _pct
            filas.extend(_items_plato)
        return pd.DataFrame(filas)

    if archivo == "recetabase.parquet":
        # Nombres EXACTOS del parquet real (confirmado contra R2 2026-08-13).
        # Formato de "activo" PROPIO y DISTINTO al de recetaventa aunque la
        # columna INS ACTIVO se llame igual en los dos parquets — el demo lo
        # reproduce a propósito: si no, el bug de formato (arreglado en
        # _activo(), recetas_comun.py) nunca se habría visto en local.
        _n_rb = 60
        _recetas = [f"Receta base demo {i:03d}" for i in range(_n_rb)]
        _insumos_pool_rb = [f"Insumo demo {i:03d}" for i in range(35)]
        filas = []
        for _i, _rb in enumerate(_recetas):
            _n_ins = int(rng.integers(3, 9))
            _ins_rb = rng.choice(_insumos_pool_rb, _n_ins, replace=False)
            for _ins in _ins_rb:
                _cant = round(float(rng.uniform(0.05, 3.0)), 3)
                _costo_unit = round(float(rng.uniform(0.5, 25.0)), 4)
                filas.append({
                    "COD RB": f"RB{_i:04d}",
                    "RB NOMBRE": _rb,
                    "RB ACT": "RB.ACTIV" if rng.random() < 0.7 else "RB.INACT",
                    "COD INS RB": f"IN{_insumos_pool_rb.index(_ins):04d}",
                    "INSUMO": _ins,
                    "INS ACTIVO": "INS.ACT" if rng.random() < 0.95 else "INS.INAC",
                    "CANT": _cant,
                    "CST SUBT INS": round(_cant * _costo_unit, 2),
                })
        return pd.DataFrame(filas)

    # Reportes genéricos (Requerimientos, etc.)
    cant = rng.integers(1, 200, n)
    precio = rng.uniform(1, 80, n).round(2)
    df = pd.DataFrame({
        "Fecha": pd.date_range("2024-01-01", periods=n, freq="D"),
        "Codigo Producto": [f"P{i:05d}" for i in range(n)],
        "Nombre Producto": [f"Producto demo {i:03d}" for i in range(n)],
        "Nombre Area": rng.choice(["Cocina", "Bar", "Almacén", "Salón"], n),
        "Nombre Familia": rng.choice(["Carnes", "Bebidas", "Verduras", "Abarrotes"], n),
        "Cantidad": cant,
        "Precio Unitario": precio,
        "Importe Total": (cant * precio).round(2),
    })
    return df


# ===========================================================================
# CARGA DE DATOS
# ===========================================================================

# ===========================================================================
# EL SELLO: QUÉ VERSIÓN DEL PARQUET TIENE CACHEADA LA APP
# ===========================================================================
# Las cuatro cacheables de acá abajo llevan `sello` como SEGUNDO argumento.
# No lo usan en el cuerpo: es la CLAVE. Un parquet nuevo en R2 = un sello
# nuevo = una entrada nueva = se baja solo, sin que nadie apriete nada.
#
# POR QUÉ HACE FALTA, SI YA TIENEN `ttl=3600`: porque con `persist="disk"`
# ese ttl NO gobierna el disco. En streamlit 1.59.2,
# `in_memory_cache_storage_wrapper.py::get()` (línea 91) busca en el TTLCache
# de memoria y, cuando ahí no está —expiró, o el proceso arrancó recién—, cae
# a `_persist_storage.get(key)`, que abre el `.memo` y lo devuelve SIN mirar
# ninguna fecha (`local_disk_cache_storage.py:137`, "Disk cache HIT"); con eso
# recalienta la memoria. O sea: el ttl decide cada cuánto se RELEE el disco;
# la copia en disco no caduca nunca. Sale con `.clear()` o borrando el
# fichero, y con nada más.
#
# Lo que costó (2026-09-09, medido): la app servía el `compras.parquet` del
# 6-sep (51.574 filas, hasta el 5-sep, septiembre con 4 líneas) mientras R2
# tenía el de las 03:00 de ESE MISMO día (51.838 filas, hasta el 8-sep,
# septiembre con 268). El «Ranking de proveedores» decía "Sin compras en el
# rango seleccionado" sobre un 1–5 sep que tenía S/22.182 en 38 documentos.
# Y la franja de arriba decía "Última actualización: hoy 03:00", porque ese
# rótulo mide el ARCHIVO en R2 (`fecha_ultima_actualizacion`, head_object en
# vivo) y no el df que está en pantalla: desde el 2026-08-12 esos dos pueden
# diferir días. Ver regla #367 — la #94 afirmaba lo contrario y quedó
# corregida ahí mismo.

_SELLOS = {}   # archivo -> sello vigente en ESTE proceso


@st.cache_data(ttl=60, show_spinner=False)
def _sello_r2(archivo):
    """`LastModified` del parquet, en texto. `""` si no se pudo saber.

    `ttl` corto y SIN `persist`: es un head_object de milisegundos, y es lo
    que decide en cuánto se entera la app de un archivo nuevo (≤1 min).
    Cachearlo evita repetir la llamada en las cuatro cacheables de cada
    rerun."""
    f = fecha_ultima_actualizacion(archivo)
    return f.isoformat() if f is not None else ""


def sello_datos(archivo):
    """El sello con el que se identifica lo cacheado de `archivo`.

    Y, de paso, el que tira la generación anterior: sin eso cada versión
    nueva dejaría su `.memo` viejo ocupando disco para siempre (20 MB los de
    Compras, 180 MB los de Ventas). Lo que este proceso NO puede saber es a
    qué versión pertenece un `.memo` que ya estaba en disco al arrancar: si
    el parquet cambió con la app apagada, esa generación sobrevive hasta el
    próximo cambio (tope práctico: dos).

    UN head_object QUE FALLA NO INVALIDA NADA: se sigue con el último sello
    conocido. Devolver `""` ahí sería un tercer sello, o sea bajar el parquet
    entero por un blip de red — el mismo error que el split cacheada/wrapper
    de `cargar()` evita del otro lado."""
    s = _sello_r2(archivo)
    if not s:
        return _SELLOS.get(archivo, "")
    anterior = _SELLOS.get(archivo)
    _SELLOS[archivo] = s
    if anterior is not None and anterior != s:
        _purgar_version(archivo, anterior)
    return s


def _purgar_version(archivo, sello):
    """Saca del disco lo PESADO que quedó de una versión anterior.

    Las dos cacheables grandes, y lo vendido por producto y día, que es
    chico pero cambia de versión cada madrugada. `_rango_fechas_cacheable` y
    `_resumen_kpis_cacheable` guardan un par de fechas y un dict de KPIs
    —bytes—, y sus claves llevan `col_fecha` adentro, que acá no se conoce:
    su generación vieja no le molesta a nadie y ya nadie la lee, porque la
    clave tiene el sello."""
    _cargar_cacheable.clear(archivo, sello)
    if archivo in (_ARCHIVO_AJUSTE, kardex.ARCHIVO_AJUSTES):
        # El ajuste con el kardex al lado (regla #612): una copia del ajuste
        # entero por versión de CUALQUIERA de los dos parquets.
        _ajuste_con_kardex_cacheable.clear()
    if any(c.get("archivo") == archivo and c.get("carga_por_rango")
           for c in REPORTES.values()):
        # Su clave lleva (col_fecha, ini, fin): no hay forma de nombrar las
        # entradas de ESTE archivo una por una, así que se vacía entera —
        # mismo argumento que `limpiar_cache`. Hoy el único reporte con
        # `carga_por_rango` es Ventas, así que el radio es uno solo.
        _cargar_rango_cacheable.clear()
    if archivo in _PREPARAR:
        # Lo vendido por producto y día (Recetas › Carta costeada): 3 MB por
        # versión, pero una versión POR DÍA. Sin esto el disco juntaría uno
        # por cada parquet de la madrugada. Se vacía entera: sólo guarda de
        # este archivo.
        _venta_por_producto_dia_cacheable.clear()
    if archivo in consumo_recetas.ARCHIVOS.values():
        # El consumo según recetas (Movimientos, regla #558) lee CUATRO
        # parquets y cambia de versión con cualquiera. Su clave lleva el
        # rango, así que se vacía entera, como la de arriba. Lo mismo el
        # primer nivel de «Revisar recetas» (regla #559), que lee el primero.
        _consumo_recetas_cacheable.clear()
        _demanda_nivel1_cacheable.clear()
        _demanda_semanas_cacheable.clear()


@st.cache_data(ttl=3600, persist="disk")
def _cargar_cacheable(archivo, sello):
    """Lectura pura del parquet. Si falla, LANZA — así @st.cache_data NO cachea
    el fracaso. Ver `cargar()` para el porqué de este split.

    `sello` no se usa en el cuerpo: ES la clave (ver el bloque de arriba).

    `persist="disk"` (2026-08-12): sin él, la caché vive SOLO en memoria del
    proceso, así que cada reinicio del server vuelve a bajar el parquet de R2
    — ventas.parquet son ~40s en frío. Peor en desarrollo: si tocás algo
    mientras baja, Streamlit cancela el run (StopException) y la descarga
    arranca de CERO; se puede quedar en un bucle donde nunca termina y parece
    que R2 está caído cuando no lo está.
    Sólo se persiste el ÉXITO: el split cacheada/wrapper de abajo no cambia."""
    # ── Modo demo: sin credenciales R2 → datos sintéticos en memoria ──
    if not secrets_disponibles():
        return _datos_demo(archivo)
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    return con.execute(f"SELECT * FROM read_parquet('{url}')").df()


@st.cache_data(ttl=3600, show_spinner=False)
def _compras_netas_cacheable(archivo, sello, sello_notas="", version=None):
    """`compras.parquet` con las notas de crédito de los proveedores restadas
    de las líneas que corrigen (`definicion_compra.aplicar_notas`, regla
    #603). Si falla, LANZA: no se cachea.

    `sello_notas` (el de `notascreditocompras.parquet`) y `version` (la de
    la regla) no se usan en el cuerpo: son la clave, como el sello. Con
    `sello_notas` vacío —el parquet todavía no existe porque falta la fila
    del Sheet— devuelve las compras tal cual.

    SÓLO EN MEMORIA, sin `persist`: los dos parquets ya están en el disco
    (`_cargar_cacheable`), y la cuenta tarda medio segundo. Persistirla
    sería otra copia de 20 MB por versión que purgar."""
    compras = _cargar_cacheable(archivo, sello_datos(archivo))
    if not sello_notas:
        return compras
    notas = _cargar_cacheable(definicion_compra.ARCHIVO_NOTAS,
                              sello_datos(definicion_compra.ARCHIVO_NOTAS))
    return definicion_compra.aplicar_notas(compras, notas)


def _sello_notas_compras():
    """El sello de `notascreditocompras.parquet`, o `""` si no existe en R2
    (o no hay secrets): con `""` las compras se sirven sin notas."""
    if not secrets_disponibles():
        return ""
    return sello_datos(definicion_compra.ARCHIVO_NOTAS)


_ARCHIVO_AJUSTE = "ajusteinventario.parquet"


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _ajuste_con_kardex_cacheable(archivo, sello, sello_kardex="", version=None):
    """`ajusteinventario.parquet` con lo que el kardex registró por cada
    línea del cierre (`kardex.sql_ajuste_con_kardex`, regla #612). Si
    falla, LANZA: no se cachea.

    `sello_kardex` (el de `ajustekardex.parquet`) y `version` no se usan en
    el cuerpo: son la clave, como el sello.

    El cruce lo hace DuckDB contra R2 y no pandas contra `_cargar_cacheable`:
    el kardex son 358 mil filas que en pandas pesarían más que el ajuste
    mismo, y así en memoria queda UNA copia del ajuste, no dos. Persiste en
    disco por lo mismo que `_cargar_cacheable` (es lo que la reemplaza):
    sin eso cada reinicio baja los dos parquets."""
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    return con.execute(kardex.sql_ajuste_con_kardex(
        f"read_parquet('s3://{bucket}/{archivo}')",
        f"read_parquet('s3://{bucket}/{kardex.ARCHIVO_AJUSTES}')")).df()


def _sello_ajustes_kardex():
    """El sello de `ajustekardex.parquet`, o `""` si no existe en R2 (o no
    hay secrets): con `""` el ajuste se sirve sin el kardex."""
    if not secrets_disponibles():
        return ""
    return sello_datos(kardex.ARCHIVO_AJUSTES)


def notas_credito_compras():
    """Las notas de crédito de los proveedores tal como las trae la consulta
    del Sheet (`notascreditocompras.parquet`), SIN aplicar a nada. Las lee
    «Documentos SUNAT», que las cruza como documentos (regla #604): restarlas
    de las compras lo hace `cargar`, una sola vez.

    `None` si el parquet no existe (o no hay secrets) o si la lectura
    falla: el cruce sigue sin ellas, como hasta el 2026-10-04."""
    if not _sello_notas_compras():
        return None
    try:
        return _cargar_cacheable(definicion_compra.ARCHIVO_NOTAS,
                                 sello_datos(definicion_compra.ARCHIVO_NOTAS))
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _notas_restadas_cacheable(archivo, sello, sello_notas="", version=None):
    """`definicion_compra.lineas_restadas`: lo que cada nota de crédito le
    restó a cada línea de compra. Si falla, LANZA: no se cachea. Sólo en
    memoria, como `_compras_netas_cacheable`: son unas decenas de filas
    sacadas de dos parquets que ya están en el disco."""
    if not sello_notas:
        return None
    compras = _cargar_cacheable(archivo, sello_datos(archivo))
    notas = _cargar_cacheable(definicion_compra.ARCHIVO_NOTAS,
                              sello_datos(definicion_compra.ARCHIVO_NOTAS))
    return definicion_compra.lineas_restadas(compras, notas)


def notas_restadas_compras():
    """Las líneas de compra que tocó una nota de crédito, con la parte
    restada en lugar de sus montos (`definicion_compra.lineas_restadas`).
    La lee «Compras por período» para decir cuánto restó en lo que muestra
    y cuánto daría sin restar, que es lo del Resumen de Ingresos del
    Almacén (regla #628).

    `None` si no hay notas (o no hay secrets) o si la lectura falla: la
    tarjeta sigue sin el aviso."""
    sello_notas = _sello_notas_compras()
    if not sello_notas:
        return None
    try:
        return _notas_restadas_cacheable(
            definicion_compra.ARCHIVO, sello_datos(definicion_compra.ARCHIVO),
            sello_notas, version=definicion_compra.VERSION)
    except Exception:
        return None


def cargar(archivo, notas_credito=True):
    """
    Carga un archivo parquet desde R2.
    Si no hay secrets de R2, devuelve datos demo en su lugar.
    Retorna el DataFrame o None si hay error.

    `compras.parquet` sale con las notas de crédito de los proveedores ya
    restadas (`definicion_compra`, regla #603), para TODO consumidor.
    `notas_credito=False` lo da tal como lo escribió el extractor: lo pide
    «Documentos SUNAT», que cruza documento contra documento y necesita
    las facturas como se emitieron.

    IMPORTANTE — por qué NO está cacheada esta capa (y sí la de adentro):
    @st.cache_data guarda CUALQUIER return, incluido un None. Si esta función
    fuese la cacheada y devolviese None ante un blip transitorio de R2 (timeout,
    o el parquet re-escribiéndose justo al leerlo), ese None quedaba cacheado
    ttl=3600 → 1 HORA sin datos, sin reintentar, aunque R2 ya estuviera sano.
    Es exactamente el bug que dejó Ajuste/Compras en blanco. Al separar:
      - _cargar_cacheable() cachea SOLO el éxito (si falla, lanza y no se guarda),
      - este wrapper (no cacheado) traduce el fallo a None cada rerun,
    un blip afecta solo ese rerun: F5 reintenta.
    """
    if notas_credito and archivo == definicion_compra.ARCHIVO:
        try:
            return _compras_netas_cacheable(
                archivo, sello_datos(archivo), _sello_notas_compras(),
                version=definicion_compra.VERSION)
        except Exception:
            # Un blip leyendo las NOTAS no deja a Compras sin datos: este
            # rerun va sin restarlas y el próximo lo reintenta (no se cacheó).
            pass
    if archivo == _ARCHIVO_AJUSTE and _sello_ajustes_kardex():
        # El ajuste con lo que dice el kardex al lado (regla #612). Sin
        # `ajustekardex.parquet` —falta la fila del Sheet— o con un blip, el
        # ajuste solo, como hasta el 2026-10-04.
        try:
            return _ajuste_con_kardex_cacheable(
                archivo, sello_datos(archivo), _sello_ajustes_kardex(),
                version=kardex.VERSION_AJUSTES)
        except Exception:
            pass
    try:
        return _cargar_cacheable(archivo, sello_datos(archivo))
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None


def limpiar_cache(archivo):
    """Invalida el cache de `cargar()` Y de `cargar_rango()` para `archivo`
    tras un refresco confirmado en R2. Ninguna de las dos es cacheable
    directamente (ver sus docstrings) — el `@st.cache_data` real vive en
    `_cargar_cacheable` / `_cargar_rango_cacheable`, así que son esas las
    que hay que limpiar. Llamado desde app.py::_vigilar_refresco y
    navegacion.py::boton_refresco.

    Bug real (2026-09-03): esta función solo limpiaba `_cargar_cacheable`.
    Ventas carga por `carga_por_rango` (ver REPORTES), o sea que pasa por
    `_cargar_rango_cacheable`, NUNCA por `_cargar_cacheable` — un refresco
    de Ventas mostraba el toast "✅ actualizado" y el archivo SÍ estaba
    nuevo en R2, pero la vista seguía sirviendo el resultado (vacío o
    viejo) que ya tenía cacheado para el rango de fechas visible, hasta que
    venciera su `ttl=3600` (hasta 1h — y con `persist="disk"` sobrevive
    incluso a un reinicio del server).
    `_cargar_rango_cacheable.clear()` sin argumentos porque su clave es
    (archivo, sello, col_fecha, ini, fin): Streamlit solo permite limpiar una
    entrada puntual pasando TODOS los valores exactos, o vaciar la función
    entera. Acá no se conoce ini/fin del caller (y puede haber más de un
    rango cacheado a la vez si distintos usuarios miraron distintas
    ventanas), así que se vacía TODA — hoy Ventas es el único reporte con
    `carga_por_rango`, así que el radio es uno solo; si se suma otro
    reporte con el mismo patrón, seguirá siendo correcto (solo un poco más
    ancho: purga rangos de otros archivos que no hacía falta invalidar).

    Desde el 2026-09-09 limpia además las OTRAS DOS cacheables del mismo
    parquet —los topes del calendario y los KPIs del rail— y el sello. Que
    el botón dijera "✅ actualizado" y el rail siguiera mostrando los KPIs
    viejos era el bug de 2026-09-03 otra vez, en otra función.

    Y `_sello_r2.clear()` no es higiene: sin él, el sello (ttl 60s) puede
    seguir siendo el ANTERIOR justo después del refresco, y el parquet nuevo
    quedaría guardado bajo la clave vieja — para volver a bajarse un minuto
    después, cuando aparezca el sello nuevo. Dos descargas por cada clic."""
    _cargar_cacheable.clear(archivo, _SELLOS.get(archivo, ""))
    # Las compras con sus notas restadas (regla #603): vive sólo en memoria
    # y su clave lleva los dos sellos, así que un parquet nuevo ya es otra
    # entrada; se vacía para no esperar la hora de su `ttl` con dos copias.
    _compras_netas_cacheable.clear()
    _notas_restadas_cacheable.clear()
    # El ajuste con el kardex al lado (regla #612): su clave lleva los dos
    # sellos, y se vacía entera por lo mismo que la de arriba.
    _ajuste_con_kardex_cacheable.clear()
    _cargar_rango_cacheable.clear()
    _rango_fechas_cacheable.clear()
    _resumen_kpis_cacheable.clear()
    _venta_por_producto_dia_cacheable.clear()
    _venta_por_canal_dia_cacheable.clear()
    _venta_por_grupo_dia_cacheable.clear()
    _sin_descargo_cacheable.clear()
    _ventas_por_mes_cacheable.clear()
    _consumo_recetas_cacheable.clear()
    _demanda_nivel1_cacheable.clear()
    _demanda_semanas_cacheable.clear()
    _stock_al_cacheable.clear()
    _kardex_fotos_cacheable.clear()
    _historia_stock_cacheable.clear()
    _movimientos_cacheable.clear()
    _periodos_conteo_cacheable.clear()
    _movimientos_conteo_cacheable.clear()
    _venta_clase_dia_cacheable.clear()
    _sin_plato_cacheable.clear()
    _diferencias_cacheable.clear()
    _sunat_sin_ingresar_cacheable.clear()
    _consistencia_cacheable.clear()
    _sello_r2.clear()
    _SELLOS.pop(archivo, None)


# ── Qué se le hace a un parquet ENTRE leerlo de R2 y entregarlo ─────────
# A ventas: la DEFINICIÓN DE VENTA (regla #524) —qué es venta,
# cortesía, anulado y nota de crédito— vive en `definicion_venta.py` y se
# aplica acá, al cargar, para que TODO consumidor reciba el mismo df: las
# vistas, los KPIs del rail, el asistente y los tramos que Año Pasado y
# Mapa por hora cargan aparte. Aplicarla en cada vista era cómo cada una
# había terminado con su propia versión.
#
# A compras, las notas de crédito de los proveedores (regla #603), por el
# mismo motivo. No va en `_PREPARAR` porque no es una función del parquet
# solo — necesita OTRO, `notascreditocompras.parquet` —, y Compras no carga
# por rango: la aplica `cargar()` (`_compras_netas_cacheable`) y, para los
# KPIs del rail, `_resumen_kpis_cacheable`.
_PREPARAR = {"ventas.parquet": definicion_venta}


def _version_preparar(archivo):
    """La versión de la definición que se le aplica a `archivo`: va en la
    clave de la caché para que un cambio de definición no siga sirviendo
    el df preparado con la regla vieja (la caché de disco no caduca).

    En compras es `(versión, sello de las notas de crédito)`: lo que se le
    aplica depende también de OTRO parquet (regla #603). `None` si ese
    parquet todavía no existe — las compras van como vienen."""
    if archivo == definicion_compra.ARCHIVO:
        sello_notas = _sello_notas_compras()
        return (definicion_compra.VERSION, sello_notas) if sello_notas else None
    prep = _PREPARAR.get(archivo)
    return prep.VERSION if prep else None


def _preparar_en_rango(prep, df, col_fecha, ini, fin, turno=False):
    """`prep.preparar` recortado al rango por la MISMA fecha con que se
    cargó.

    `preparar(df, ini, fin)` recorta por la fecha del DOCUMENTO, que es por
    la que carga casi todo. «Por hora» carga por la del PEDIDO (regla #552),
    y recortar después por el documento le sacaba justo lo que venía a
    buscar: un pedido abierto el 30 de junio y cobrado el 1 de julio —o
    facturado 70 días después, que los hay— es de junio, y quedaba fuera de
    junio sin entrar en julio. Las notas de crédito espejadas conservan la
    fecha del pedido que anulan, así que restan en el mismo período que su
    venta.

    `turno`: la venta por día del turno de caja (regla #593); va a
    `preparar`, que mueve la fecha del documento antes de recortar."""
    c_doc = prep.columna(df, prep.FECHA)
    if c_doc is None or c_doc == col_fecha or col_fecha not in df.columns:
        return prep.preparar(df, ini, fin, turno=turno)
    out = prep.preparar(df, turno=turno)
    f = pd.to_datetime(out[col_fecha], errors="coerce",
                       dayfirst=True).dt.normalize()
    m = f.notna() & (f >= pd.Timestamp(ini)) & (f <= pd.Timestamp(fin))
    return out[m].reset_index(drop=True)


def _donde_rango(con, url, col_fecha, prep):
    """(WHERE, parámetros) de una carga por rango de `ini` a `fin`.

    Con una definición que arma notas de crédito, además de lo del rango
    trae los documentos que una nota DEL RANGO anula aunque sean de antes:
    la nota resta sus ítems, y sin ellos sólo podría restar el monto. Los
    saca `preparar(df, ini, fin)` después de espejarlos."""
    expr = (
        f'COALESCE('
        f'TRY_CAST("{col_fecha}" AS DATE), '
        f'TRY_CAST(TRY_STRPTIME(CAST("{col_fecha}" AS VARCHAR), \'%d/%m/%Y\') AS DATE)'
        f')'
    )
    donde, n = f"{expr} BETWEEN ? AND ?", 1
    if prep is not None:
        nombres = [r[0] for r in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()]
        c_nc = prep.columna(pd.DataFrame(columns=nombres), prep.NC_FECHA)
        if c_nc:
            donde = f'({donde} OR TRY_CAST("{c_nc}" AS DATE) BETWEEN ? AND ?)'
            n = 2
    return donde, n


@st.cache_data(ttl=3600, persist="disk")
def _cargar_rango_cacheable(archivo, sello, col_fecha, ini, fin,
                            definicion=None, turno=False):
    """Lectura filtrada por rango. Si falla, LANZA — @st.cache_data no cachea el
    fracaso. Ver `cargar()` para el porqué del split cacheada/wrapper.

    `sello` no se usa en el cuerpo: ES la clave (ver el bloque del sello).
    `definicion` tampoco: es la versión de `_PREPARAR[archivo]`, por lo
    mismo (ver `_version_preparar`).

    `turno` (regla #593): la venta por día del turno de caja. Carga un día
    más al final, porque el cobro de las 00:25 del día siguiente es del
    último día del rango; `preparar` lo mueve y recorta.

    `persist="disk"` por lo mismo que `_cargar_cacheable`: la clave incluye el
    rango, así que cada ventana que ya se miró una vez queda en disco y
    sobrevive al reinicio del server."""
    prep = _PREPARAR.get(archivo)
    # ── Modo demo: sin credenciales R2 → datos sintéticos filtrados ──
    if not secrets_disponibles():
        df = _datos_demo(archivo)
        col = "Fecha" if "Fecha" in df.columns else None
        if col:
            m = (df[col].dt.date >= ini) & (df[col].dt.date <= fin)
            df = df[m]
        return prep.preparar(df) if prep else df
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    donde, n = _donde_rango(con, url, col_fecha, prep)
    turno = bool(turno and prep is not None)
    fin_carga = fin + timedelta(days=1) if turno else fin
    df = con.execute(
        f"SELECT * FROM read_parquet('{url}') WHERE {donde}",
        [ini, fin_carga] * n,
    ).df()
    return (_preparar_en_rango(prep, df, col_fecha, ini, fin, turno=turno)
            if prep else df)


def venta_por_turno():
    """True si Ventas está fechando por el día del TURNO de caja (el
    default, regla #593) y False si por la fecha de EMISIÓN del comprobante
    (la del Registro de Ventas de SUNAT). Lo elige el selector de «Filtros»
    de Ventas (`definicion_venta.CLAVE_DIA`); fuera de Streamlit, turno."""
    try:
        return (st.session_state.get(definicion_venta.CLAVE_DIA,
                                     definicion_venta.DIA_TURNO)
                == definicion_venta.DIA_TURNO)
    except Exception:
        return True


def cargar_rango(archivo, col_fecha, ini, fin, turno=None):
    """
    Como cargar(), pero filtrando por fecha DENTRO de DuckDB, antes de
    materializar el DataFrame (para parquets grandes como ventas.parquet:
    nunca se descargan/materializan las 100k+ filas completas).

    ini/fin: datetime.date (rango inclusivo).
    col_fecha: nombre EXACTO de la columna de fecha en el parquet.

    Maneja col_fecha tanto si es DATE/TIMESTAMP real como si viene como
    texto tipo '05/07/2026' (dd/mm/yyyy): COALESCE de dos intentos de cast.

    ventas.parquet llega PREPARADO (`_PREPARAR`, regla #524): con la
    columna `CLASE VENTA` y las notas de crédito como ítems negativos. Lo
    que sale de acá ya no es el parquet fila por fila — para eso está el
    Inspector, que usa `cargar()`.

    No cacheada a propósito (la capa interna sí): un fallo transitorio NO debe
    quedar cacheado 1h como None. Mismo patrón que cargar().

    `turno`: fechar la venta por el día del turno de caja (regla #593). Sin
    darlo, lo que diga el selector de Ventas (`venta_por_turno`); una
    herramienta que cuadra contra el POS por fecha de registro pasa False.
    """
    if turno is None:
        turno = venta_por_turno()
    turno = bool(turno and archivo in _PREPARAR)
    try:
        return _cargar_rango_cacheable(archivo, sello_datos(archivo),
                                       col_fecha, ini, fin,
                                       definicion=_version_preparar(archivo),
                                       turno=turno)
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None


@st.cache_data(ttl=3600, persist="disk")
def _rango_fechas_cacheable(archivo, sello, col_fecha):
    """MIN/MAX de la fecha. Si falla, LANZA (no se cachea). El None de 'no hay
    fechas' SÍ es cacheable — es un resultado válido, no un error.

    `sello` no se usa en el cuerpo: ES la clave (ver el bloque del sello).
    Sin él, los TOPES del calendario se quedaban clavados en los del parquet
    viejo — que es como se ve este bug desde la pantalla: el date-picker no
    deja elegir un día que en R2 ya existe."""
    if not secrets_disponibles():
        df = _datos_demo(archivo)
        col = "Fecha" if "Fecha" in df.columns else None
        if col is not None and not df.empty:
            return df[col].min().date(), df[col].max().date()
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    expr = (
        f'COALESCE('
        f'TRY_CAST("{col_fecha}" AS DATE), '
        f'TRY_CAST(TRY_STRPTIME(CAST("{col_fecha}" AS VARCHAR), \'%d/%m/%Y\') AS DATE)'
        f')'
    )
    fila = con.execute(
        f"SELECT MIN({expr}) AS a, MAX({expr}) AS b "
        f"FROM read_parquet('{url}')"
    ).fetchone()
    if fila and fila[0] is not None and fila[1] is not None:
        return fila[0], fila[1]
    return None


def rango_fechas(archivo, col_fecha):
    """(min, max) de la columna de fecha del parquet, vía un agregado en
    DuckDB (MIN/MAX) que NO materializa las filas. Sirve para fijar los
    límites del date-picker sin descargar todo el parquet.

    Retorna (datetime.date, datetime.date) o None si falla / no hay datos.
    Maneja col_fecha como DATE/TIMESTAMP real o como texto dd/mm/yyyy,
    igual que cargar_rango().

    No cacheada (la capa interna sí): un fallo transitorio de R2 no debe quedar
    cacheado como None 1h y romper el date-picker. Mismo patrón que cargar().
    """
    try:
        return _rango_fechas_cacheable(archivo, sello_datos(archivo),
                                       col_fecha)
    except Exception:
        return None


_AGREGACIONES_KPI = {"sum": "SUM", "count_distinct": "COUNT(DISTINCT",
                     "sum_dedup": "SUM"}


def _expr_fecha_kpi(col_fecha):
    """Mismo COALESCE de dos intentos de cast que cargar_rango()/
    rango_fechas(): la columna puede ser DATE/TIMESTAMP real o texto
    dd/mm/yyyy, y acá no hay como saber cuál sin ir a mirar el parquet."""
    return (f'COALESCE(TRY_CAST("{col_fecha}" AS DATE), '
            f'TRY_CAST(TRY_STRPTIME(CAST("{col_fecha}" AS VARCHAR), '
            f"'%d/%m/%Y') AS DATE))")


@st.cache_data(ttl=3600, persist="disk")
def _resumen_kpis_cacheable(archivo, sello, kpis, col_fecha, col_dedup,
                            col_item=None, definicion=None, turno=False):
    """Agregados SUM/COUNT DISTINCT directo en DuckDB, sin materializar
    filas — mismo espíritu que `_rango_fechas_cacheable`. Acota al MES EN
    CURSO cuando `col_fecha` viene dado (mismo default que usa la franja de
    fecha en app.py: `hoy.replace(day=1)` → hoy); si no, agrega la tabla
    entera — es el caso de los catálogos sin fecha (Recetas,
    Inventario Valorizado).

    `definicion` es la versión de la definición del archivo
    (`_version_preparar`), en la clave por el mismo motivo que el sello. En
    compras es `(versión, sello de las notas de crédito)` y SÍ se usa: dice
    de qué df salen los KPIs (regla #603). `turno`: el mes por día del
    turno de caja, como la vista (regla #593)."""
    if not secrets_disponibles():
        return {}
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"

    prep = _PREPARAR.get(archivo)
    if prep is not None and col_fecha:
        # CON DEFINICIÓN (ventas, regla #524): el rail tiene que decir la
        # misma venta que la vista, así que no se agrega en SQL —sería una
        # segunda copia de la definición, que es justo cómo el rail sumaba
        # cortesías y anulados—. Se bajan sólo las columnas que la
        # definición y los KPIs leen (unas 30 de 60, un mes) y se resume
        # con `prep.resumir`.
        hoy = datetime.now(timezone.utc).date()
        ini = hoy.replace(day=1)
        nombres = [r[0] for r in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()]
        vacio = pd.DataFrame(columns=nombres)
        quiero = [*prep.COLUMNAS, col_fecha, col_dedup, col_item,
                  *(k[1] for k in kpis)]
        reales = list(dict.fromkeys(
            c for c in (prep.columna(vacio, q) for q in quiero if q) if c))
        lista = ", ".join(f'"{c}"' for c in reales)
        donde, n = _donde_rango(con, url, col_fecha, prep)
        df = con.execute(
            f"SELECT {lista} FROM read_parquet('{url}') WHERE {donde}",
            [ini, hoy] * n).df()
        return prep.resumir(prep.preparar(df, ini, hoy, turno=turno), kpis,
                            col_ped=col_dedup, col_item=col_item)

    where = ""
    if col_fecha:
        hoy = datetime.now(timezone.utc).date()
        ini = hoy.replace(day=1)
        where = f"WHERE {_expr_fecha_kpi(col_fecha)} BETWEEN '{ini}' AND '{hoy}'"

    origen = f"read_parquet('{url}')"
    if archivo == definicion_compra.ARCHIVO and definicion:
        # CON NOTAS DE CRÉDITO (compras, regla #603): el rail suma lo mismo
        # que las vistas, así que lee el df con las notas ya restadas y no el
        # parquet — reescribir la resta en SQL sería una segunda copia de la
        # regla. `definicion` es (versión, sello de las notas). Conexión
        # PROPIA: `register` es de la conexión, y la de `get_conn()` es la de
        # este hilo para todo lo demás (regla #599).
        con = duckdb.connect()
        con.register("compras_netas", _compras_netas_cacheable(
            archivo, sello_datos(archivo), definicion[1],
            version=definicion[0]))
        origen = "compras_netas"

    # Un ítem una vez (regla #517): la fuente pasa a ser el parquet con UNA
    # fila por `col_item`. Las filas sin llave se quedan todas, igual que en
    # `graficos/ventas.py::unico_por_item`.
    fuente = f"{origen} {where}"
    if col_item:
        fuente = (f'(SELECT * FROM {fuente} QUALIFY "{col_item}" IS NULL '
                  f'OR ROW_NUMBER() OVER (PARTITION BY "{col_item}") = 1)')

    if col_dedup:
        # Dedup: agrupar por col_dedup ANTES de agregar (ver docstring de
        # REPORTES["Ventas"]["kpi_dedup"] en data.py — una columna que se
        # repite por línea, no por registro real). count_distinct no tiene
        # sentido bajo dedup (ya es 1 fila por grupo) y no se usa hoy.
        selects = ", ".join(
            f'{("MAX" if kpi[2] == "sum_dedup" else kpi[2].upper())}("{kpi[1]}") AS k{i}'
            for i, kpi in enumerate(kpis)
        )
        sql = (f'SELECT {", ".join(f"SUM(k{i}) AS k{i}" for i in range(len(kpis)))} '
               f'FROM (SELECT {selects} FROM {fuente} '
               f'GROUP BY "{col_dedup}")')
    else:
        partes = []
        nombres = None
        for i, kpi in enumerate(kpis):
            _et, col, agg = kpi[0], kpi[1], kpi[2]
            fn = _AGREGACIONES_KPI[agg]
            cierre = ")" if agg == "count_distinct" else ""
            # 4o elemento OPCIONAL: (columna, valores) para acotar ESTE KPI a
            # un subconjunto de filas — "Valorizado de Alimentos" es el mismo
            # SUM de siempre, sobre las filas cuya FAMILIA es 'ALIMENTOS'.
            # Se resuelve con `FILTER (WHERE ...)`, que DuckDB soporta: un
            # solo barrido del parquet devuelve los cuatro numeros, en vez de
            # una consulta por familia.
            #
            # Los valores salen de REPORTES (config nuestra, no del usuario),
            # pero se escapan igual: una comilla en un nombre de familia
            # rompe el SQL y no se descubre hasta que aparezca una.
            #
            # Y puede ser VARIOS pares (columna, valores), que se cumplen
            # todos: así lee «Stock e Inventario» su regla de lo activo
            # (`INVENTARIO_ACTIVO`, regla #598). Ahí un par cuya columna el
            # parquet todavía no trae se salta en vez de romper la consulta:
            # el KPI sigue, con las marcas que haya.
            filtro = kpi[3] if len(kpi) > 3 else None
            pares = (() if not filtro
                     else (filtro,) if isinstance(filtro[0], str)
                     else tuple(filtro))
            if len(pares) > 1 or (pares and not isinstance(filtro[0], str)):
                if nombres is None:
                    nombres = {r[0] for r in con.execute(
                        f"DESCRIBE SELECT * FROM {origen}"
                    ).fetchall()}
                pares = tuple(p for p in pares if p[0] in nombres)
            condiciones = " AND ".join(
                f'"{col_f}" IN ('
                + ", ".join("'" + str(v).replace("'", "''") + "'" for v in vals)
                + ")"
                for col_f, vals in pares)
            if condiciones:
                partes.append(f'{fn}("{col}"){cierre} '
                              f'FILTER (WHERE {condiciones}) AS k{i}')
            else:
                partes.append(f'{fn}("{col}"){cierre} AS k{i}')
        sql = f'SELECT {", ".join(partes)} FROM {fuente}'

    fila = con.execute(sql).fetchone()
    valores = {kpi[0]: fila[i] for i, kpi in enumerate(kpis)}
    # Un KPI es un número o un vacío. Otra cosa —un nombre de columna, una
    # fecha— es la fila de OTRA consulta (regla #599), y se lanza para que
    # no quede en la caché, que es de disco y no caduca.
    if any(v is not None and not isinstance(v, numbers.Number)
           for v in valores.values()):
        raise ValueError("un KPI volvió con un valor que no es un número")
    return valores


def resumen_kpis(archivo, kpis, col_fecha=None, col_dedup=None):
    """KPIs chicos para el rail de Reportes (navegacion.py): 1-3 números por
    reporte, vía un agregado DuckDB directo contra R2 — no descarga el
    parquet completo, mismo espíritu que `rango_fechas()`.

    `kpis`: tupla de (etiqueta, columna, agregación), agregación en
    {"sum", "count_distinct", "sum_dedup"}. Viven en `REPORTES[x]["kpis"]`
    (config de DATOS, no de despacho — mismo criterio que `columnas_movil`).

    Retorna {etiqueta: valor} — dict vacío si no hay secrets (demo), si el
    reporte no definió `kpis`, o si la consulta falla (parquet sin esa
    columna, R2 caído, etc.). NO cacheada en esta capa (la interna sí): un
    blip transitorio de R2 no debe quedar cacheado como vacío 1h y apagar
    los KPIs del rail. Mismo patrón que `cargar()`/`rango_fechas()`."""
    if not kpis:
        return {}
    # La llave del ítem sale de REPORTES y no de un argumento: los dos
    # llamadores (navegacion.py) no cambian, y en Cloud un cambio de firma
    # entre módulos ya importados es una caída (CLAUDE.md, regla #357).
    col_item = next((i.get("kpi_item") for i in REPORTES.values()
                     if i.get("archivo") == archivo and i.get("kpi_item")),
                    None)
    try:
        return _resumen_kpis_cacheable(
            archivo, sello_datos(archivo), kpis, col_fecha, col_dedup,
            col_item, definicion=_version_preparar(archivo),
            turno=bool(archivo in _PREPARAR and venta_por_turno()))
    except Exception:
        return {}


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _venta_por_producto_dia_cacheable(archivo, sello, definicion=None):
    """Lo vendido de cada producto, día por día, sobre TODO el parquet
    (`definicion_venta.por_producto_dia`). Si falla, LANZA: no se cachea.

    `sello` y `definicion` no se usan en el cuerpo: son la clave (ver el
    bloque del sello y `_version_preparar`).

    Mismo camino que los KPIs del rail: se bajan sólo las columnas que la
    definición lee (33 de 59) y se prepara en pandas, porque agregar en SQL
    sería una segunda copia de la definición (#524). Es lo más pesado que
    baja la app de una vez —medido en la laptop sobre el parquet de
    septiembre de 2026: 237.000 filas, 92 MB en memoria y 6 s—, pero lo que
    se guarda son 56.000 filas y 3 MB, una vez por versión del parquet."""
    prep = _PREPARAR[archivo]
    if not secrets_disponibles():
        return prep.por_producto_dia(prep.preparar(_datos_demo(archivo)))
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    nombres = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()]
    vacio = pd.DataFrame(columns=nombres)
    reales = list(dict.fromkeys(
        c for c in (prep.columna(vacio, q) for q in prep.COLUMNAS) if c))
    lista = ", ".join(f'"{c}"' for c in reales)
    df = con.execute(f"SELECT {lista} FROM read_parquet('{url}')").df()
    return prep.por_producto_dia(prep.preparar(df))


CANAL_PRINCIPAL = "En el Local"
"""El canal de casi toda la venta (99 % de las líneas desde julio de 2026):
`venta_por_canal_dia` trae los OTROS, y el principal sale por diferencia."""


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _venta_por_canal_dia_cacheable(archivo, sello, definicion=None):
    """Lo vendido de cada producto por día en los canales que NO son «En el
    Local» (`definicion_venta.por_producto_dia(canal=True)`), para «Costo de
    Carta» (regla #696). Si falla, LANZA: no se cachea.

    El mismo camino que `_venta_por_producto_dia_cacheable` —las mismas
    columnas, que ya traen el canal—; se guarda sólo lo de los otros canales
    (Rappi, Para Llevar…: unos cientos de filas) y el principal se obtiene
    restando del total, sin una segunda copia de lo vendido."""
    prep = _PREPARAR[archivo]
    if not secrets_disponibles():
        g = prep.por_producto_dia(prep.preparar(_datos_demo(archivo)), canal=True)
    else:
        con = get_conn()
        bucket = st.secrets["R2_BUCKET"]
        url = f"s3://{bucket}/{archivo}"
        nombres = [r[0] for r in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()]
        vacio = pd.DataFrame(columns=nombres)
        reales = list(dict.fromkeys(
            c for c in (prep.columna(vacio, q) for q in prep.COLUMNAS) if c))
        lista = ", ".join(f'"{c}"' for c in reales)
        df = con.execute(f"SELECT {lista} FROM read_parquet('{url}')").df()
        g = prep.por_producto_dia(prep.preparar(df), canal=True)
    return g[(g["canal"] != CANAL_PRINCIPAL) & (g["canal"] != "")].reset_index(drop=True)


def venta_por_canal_dia(archivo="ventas.parquet"):
    """Lo vendido por producto, día y canal fuera de «En el Local»; `None`
    si no se pudo cargar. No cacheada (la interna sí), como las demás."""
    if archivo not in _PREPARAR:
        return None
    try:
        return _venta_por_canal_dia_cacheable(
            archivo, sello_datos(archivo), definicion=_version_preparar(archivo))
    except Exception:
        return None


def venta_por_producto_dia(archivo="ventas.parquet"):
    """Lo vendido de cada producto por día, con la definición de venta de
    siempre (regla #556): unidades, neto, costo, unidades con costo y neto
    vendido sin costo. `None` si no se pudo cargar — quien lo pide sigue
    sin esos datos en vez de caerse.

    No cacheada (la interna sí), por lo mismo que `cargar()`: un fallo
    transitorio de R2 no debe quedar guardado como None."""
    if archivo not in _PREPARAR:
        return None
    try:
        return _venta_por_producto_dia_cacheable(
            archivo, sello_datos(archivo),
            definicion=_version_preparar(archivo))
    except Exception:
        return None


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _sin_descargo_cacheable(archivo, sello):
    """Los códigos que el POS marca «Sin descargo» en la carta (regla #761).
    Si falla, LANZA: no se cachea."""
    if not secrets_disponibles():
        return ()
    url = f"s3://{st.secrets['R2_BUCKET']}/{archivo}"
    filas = get_conn().execute(
        f"""SELECT DISTINCT trim("COD PLATO") FROM read_parquet('{url}')
            WHERE upper(trim("TIPO DESC")) = ?""",
        [definicion_venta.TIPO_SIN_DESCARGO]).fetchall()
    return tuple(sorted(r[0] for r in filas if r[0]))


def platos_sin_descargo(archivo="cartacosteada.parquet"):
    """Los códigos de lo que se vende «Sin descargo»: su costo ES cero, así
    que no se observa como vendido sin costo (`definicion_venta.es_sin_descargo`).
    Es la marca de HOY, también para lo vendido antes. Vacío si no se pudo leer:
    se sigue observando todo, no se esconde nada."""
    try:
        return _sin_descargo_cacheable(archivo, sello_datos(archivo))
    except Exception:
        return ()


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _venta_por_grupo_dia_cacheable(archivo, sello, definicion=None, sin_descargo=()):
    """La venta y la cortesía de cada grupo de carta por día, sobre TODO el
    parquet (`definicion_venta.por_grupo_dia`), fechada por el día del TURNO
    de caja, el default de Ventas (regla #593). Si falla, LANZA: no se cachea.

    El mismo camino que `_venta_por_producto_dia_cacheable`: sólo las
    columnas que la definición lee, más el grupo, y la cuenta en pandas
    (#524). Lo que se guarda son unas 7.000 filas por año."""
    prep = _PREPARAR[archivo]
    if not secrets_disponibles():
        return prep.por_grupo_dia(prep.preparar(_datos_demo(archivo), turno=True),
                                  sin_descargo)
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    nombres = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()]
    vacio = pd.DataFrame(columns=nombres)
    reales = list(dict.fromkeys(
        c for c in (prep.columna(vacio, q) for q in (*prep.COLUMNAS, prep.GRUPO))
        if c))
    lista = ", ".join(f'"{c}"' for c in reales)
    df = con.execute(f"SELECT {lista} FROM read_parquet('{url}')").df()
    return prep.por_grupo_dia(prep.preparar(df, turno=True), sin_descargo)


def venta_por_grupo_dia(archivo="ventas.parquet"):
    """La venta neta y el costo de cada grupo de carta por día, y el costo de
    las cortesías (`definicion_venta.por_grupo_dia`), para el reporte Costos
    (regla #622). `None` si no se pudo cargar. No cacheada (la interna sí),
    por lo mismo que `cargar()`."""
    if archivo not in _PREPARAR:
        return None
    try:
        return _venta_por_grupo_dia_cacheable(
            archivo, sello_datos(archivo),
            definicion=_version_preparar(archivo), sin_descargo=platos_sin_descargo())
    except Exception:
        return None


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _ventas_por_mes_cacheable(archivo, sello, definicion=None, cuenta=None, sin_descargo=()):
    """Las cifras de la portada de Inicio para CADA mes del parquet
    (`resumen_ejecutivo.ventas_por_mes`): venta, pedidos, clientes, ticket,
    descuentos y lo vendido sin costo, por día del turno. Si falla, LANZA:
    no se cachea. `cuenta` es `resumen_ejecutivo.VERSION`, sólo la clave.

    El mismo camino que `_venta_por_grupo_dia_cacheable`: sólo las columnas
    que la cuenta lee. Una lectura del parquet por versión del dato y unas
    pocas decenas de filas guardadas: la portada no baja doce meses de
    líneas en cada visita (regla #745)."""
    import resumen_ejecutivo
    prep = _PREPARAR[archivo]
    if not secrets_disponibles():
        return resumen_ejecutivo.ventas_por_mes(
            prep.preparar(_datos_demo(archivo), turno=True), sin_descargo)
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    nombres = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()]
    vacio = pd.DataFrame(columns=nombres)
    pide = (*prep.COLUMNAS, resumen_ejecutivo.PEDIDO, resumen_ejecutivo.NOMBRE)
    reales = list(dict.fromkeys(c for c in (prep.columna(vacio, q) for q in pide) if c))
    lista = ", ".join(f'"{c}"' for c in reales)
    df = con.execute(f"SELECT {lista} FROM read_parquet('{url}')").df()
    return resumen_ejecutivo.ventas_por_mes(prep.preparar(df, turno=True), sin_descargo)


def ventas_por_mes(archivo="ventas.parquet"):
    """`{mes: cifras}` de la portada de Inicio, o None si no se pudo."""
    if archivo not in _PREPARAR:
        return None
    try:
        import resumen_ejecutivo
        return _ventas_por_mes_cacheable(
            archivo, sello_datos(archivo),
            definicion=_version_preparar(archivo), cuenta=resumen_ejecutivo.VERSION,
            sin_descargo=platos_sin_descargo())
    except Exception:
        return None


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _consumo_recetas_cacheable(archivo, sello, ini, fin, sellos=(), version=None,
                               rendimiento="90"):
    """El consumo de insumos de compra del rango (`consumo_recetas.calcular`,
    regla #558). Si falla, LANZA: no se cachea.

    `archivo` es el primer nivel de las recetas de venta, el que manda el
    rango; `sellos`, los de los otros tres parquets del cálculo (recetas
    base, porcionamientos y el maestro), y `version`, la de la cuenta. Ninguno
    se usa en el cuerpo: son la clave (ver el bloque del sello).

    Lee de R2 sólo lo del rango y agregado por día, hora, plato e insumo
    —medido: 32.554 filas un mes, 470.000 sin agregar un año—; las recetas,
    los porcionamientos y el maestro enteros, que son chicos. La cuenta corre
    en una conexión de DuckDB PROPIA (`calcular`): arma tablas temporales, y
    la de `get_conn()` la comparten todas las sesiones."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    A = consumo_recetas.ARCHIVOS

    def rel(nombre):
        return f"read_parquet('s3://{bucket}/{A[nombre]}')"

    columnas = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM {rel('paloteo')}").fetchall()]
    # Sin `FECHA ITEM` (un parquet anterior al 2026-09-28) la hora es la de
    # la MESA, y la vista lo dice: un postre caería una hora antes.
    con_hora = "FECHA ITEM" in columnas
    n1 = con.execute(consumo_recetas.sql_nivel1(rel("paloteo"), ini, fin,
                                                con_hora_item=con_hora)).df()
    rb = con.execute(consumo_recetas.sql_recetas(rel("recetabase"))).df()
    po = con.execute(consumo_recetas.sql_porcionamientos(rel("porcionamientos"))).df()
    ma = con.execute(consumo_recetas.sql_maestro(rel("maestro"))).df()
    # Los 12 meses que terminan en `fin`, agregados: qué parte de cada
    # producto va a la venta interna, que se cuenta por lo PRODUCIDO
    # (regla #605). Unas mil filas.
    anual = con.execute(consumo_recetas.sql_demanda_anual(rel("paloteo"), fin)).df()
    # Las órdenes de producción: la masa del chorizo se produce así, y de
    # ella sale la fecha en que se usó el magret (regla #605). Si el parquet
    # no está, la venta interna se fecha por su porcionamiento.
    try:
        ops = con.execute(consumo_recetas.sql_ordenes(rel("ordenes"))).df()
    except Exception:
        ops = None
    r = consumo_recetas.calcular(n1, rb, po, ma, ini, fin, anual=anual, ordenes=ops,
                                 rendimiento=rendimiento)
    r["resumen"]["hora_de_mesa"] = not con_hora
    return r


def consumo_recetas_rango(ini, fin, rendimiento="90"):
    """Cuánto insumo de COMPRA usaron las ventas entre `ini` y `fin`
    (fechas del pedido, inclusive), bajando por las recetas base y los
    porcionamientos — la sección «Consumo según ventas» de Producción,
    regla #558. `None` si no se pudo calcular (o sin secrets): quien lo pide
    avisa en vez de caerse. `rendimiento`: el de los 90 días («90») o el
    del último mes («mes»), regla #751.

    No cacheada (la interna sí), por lo mismo que `cargar()`."""
    A = consumo_recetas.ARCHIVOS
    try:
        return _consumo_recetas_cacheable(
            A["paloteo"], sello_datos(A["paloteo"]), ini, fin,
            sellos=tuple((a, sello_datos(a)) for a in
                         (A["recetabase"], A["porcionamientos"], A["maestro"],
                          A["ordenes"])),
            version=consumo_recetas.VERSION, rendimiento=rendimiento)
    except Exception as e:
        st.error(f"Error calculando el consumo según ventas: {e}")
        return None


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _demanda_nivel1_cacheable(archivo, sello, ini, fin):
    """Lo que pidieron las ventas del rango al PRIMER nivel de sus recetas,
    por insumo y plato (`consumo_recetas.sql_demanda_nivel1`). Si falla,
    LANZA: no se cachea.

    `archivo` es `paloteoinsumosnivel1.parquet`; `sello` no se usa en el
    cuerpo: es la clave (ver el bloque del sello). Agregado en DuckDB sobre
    R2: unos miles de filas en vez de las 112.000 de 90 días. Lo leen Recetas ›
    «Revisar recetas» (regla #559) y «Costo recetas base» (regla #576).

    La columna `vendido` llegó el 2026-09-30 con la segunda. Streamlit mete el
    CÓDIGO FUENTE de esta función en la clave de su caché —no el de la
    consulta, que vive en `consumo_recetas`—, así que cambiar lo que devuelve
    es cambiar también este texto: si no, la caché de disco, que no caduca,
    seguiría sirviendo la tabla vieja, sin la columna."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    return con.execute(consumo_recetas.sql_demanda_nivel1(rel, ini, fin)).df()


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _demanda_semanas_cacheable(archivo, sello, ini, fin):
    """Lo que pidieron las ventas al primer nivel por insumo y SEMANA
    (`consumo_recetas.sql_demanda_nivel1_semanas`): cod, semana, consumo (en
    unidad de salida). Si falla, LANZA: no se cachea. `sello` es la clave.
    Lo lee Recetas › «Recetas vs porcionado» (regla #703)."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    return con.execute(consumo_recetas.sql_demanda_nivel1_semanas(rel, ini, fin)).df()


def demanda_nivel1_semanas(ini, fin):
    """Lo que pidieron las ventas entre `ini` y `fin` al primer nivel, por
    insumo y semana (el lunes): cod, semana, consumo. `None` si no se pudo
    leer. No cacheada (la interna sí), por lo mismo que `cargar()`."""
    archivo = consumo_recetas.ARCHIVOS["paloteo"]
    try:
        return _demanda_semanas_cacheable(archivo, sello_datos(archivo), ini, fin)
    except Exception:
        return None


def demanda_nivel1_rango(ini, fin):
    """Lo que pidieron las ventas entre `ini` y `fin` (fechas del pedido,
    inclusive) al primer nivel de sus recetas: cod, plato, consumo (en unidad
    de SALIDA), costo y vendido (unidades del plato). `None` si no se pudo
    leer — quien lo pide avisa.

    No cacheada (la interna sí), por lo mismo que `cargar()`."""
    archivo = consumo_recetas.ARCHIVOS["paloteo"]
    try:
        return _demanda_nivel1_cacheable(archivo, sello_datos(archivo), ini, fin)
    except Exception:
        return None


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _stock_al_cacheable(archivo, sello, cuando, version=None):
    """El stock de cada área y producto al momento `cuando`, del kardex por
    hora (`kardex.sql_stock_al`): area, cod, stock, precio, correlativo. Si
    falla, LANZA: no se cachea.

    `sello` y `version` no se usan en el cuerpo: son la clave (la versión de
    la cuenta vive en `kardex`, y Streamlit sólo mete en la clave el código
    de ESTA función). Agregado en DuckDB sobre R2: ~15 mil filas en vez de
    las 559 mil del parquet. Regla #601."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    return con.execute(kardex.sql_stock_al(rel, cuando)).df()


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _kardex_fotos_cacheable(archivo, sello, version=None):
    """Cada fila del kardex con sólo lo que hace falta para la foto del
    stock (`kardex.sql_fotos`). Si falla, LANZA: no se cachea. `sello` y
    `version` son la clave. Regla #622."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    return con.execute(kardex.sql_fotos(rel)).df()


def kardex_fotos():
    """Las fotos del kardex para sacar el stock en muchos momentos de una
    vez (`costo_ventas.inventario_en_momentos`): las semanas y quincenas del
    reporte Costos. `None` si no se pudo leer. No cacheada (la interna sí)."""
    try:
        return _kardex_fotos_cacheable(kardex.ARCHIVO, sello_datos(kardex.ARCHIVO),
                                       version=kardex.VERSION)
    except Exception:
        return None


def stock_al(cuando):
    """El stock de cada área y producto al momento `cuando` (un `datetime`;
    cuenta su hora entera, ver `kardex.momento`). `None` si no se pudo leer
    —el parquet todavía no existe, R2 caído—: quien lo pide avisa.

    No cacheada (la interna sí), por lo mismo que `cargar()`."""
    try:
        return _stock_al_cacheable(kardex.ARCHIVO, sello_datos(kardex.ARCHIVO),
                                   cuando, version=kardex.VERSION)
    except Exception:
        return None


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _movimientos_cacheable(archivo, sello, desde, hasta, version=None):
    """Lo que entró y salió de cada área y producto por tipo de documento
    entre `desde` y `hasta` (`kardex.sql_movimientos`). Si falla, LANZA: no
    se cachea. `sello` y `version` son la clave, como en
    `_stock_al_cacheable`. Regla #602."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    return con.execute(kardex.sql_movimientos(rel, desde, hasta)).df()


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _venta_clase_dia_cacheable(archivo, sello, definicion=None):
    """Las unidades vendidas y dadas en cortesía de cada producto, por día y
    grupo de carta, sobre TODO el parquet (`definicion_venta.
    unidades_por_clase_dia`), fechadas por el comprobante. Si falla, LANZA:
    no se cachea.

    El mismo camino que `_venta_por_grupo_dia_cacheable`: sólo las columnas
    que la definición lee, más el grupo, y la cuenta en pandas (#524). La
    lee `sin_plato.py` para partir el descargo de ventas del kardex en
    venta, cortesía y eventos (regla #645)."""
    prep = _PREPARAR[archivo]
    if not secrets_disponibles():
        return prep.unidades_por_clase_dia(prep.preparar(_datos_demo(archivo)))
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    nombres = [r[0] for r in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()]
    vacio = pd.DataFrame(columns=nombres)
    reales = list(dict.fromkeys(
        c for c in (prep.columna(vacio, q) for q in (*prep.COLUMNAS, prep.GRUPO))
        if c))
    lista = ", ".join(f'"{c}"' for c in reales)
    df = con.execute(f"SELECT {lista} FROM read_parquet('{url}')").df()
    return prep.unidades_por_clase_dia(prep.preparar(df))


# Los parquets que, además del kardex, lee la cuenta de cierre a cierre
# (`sin_plato.calcular`): sus sellos van en la clave de la caché. Los cuatro
# últimos son del reloj operativo y del balance por área (regla #743):
# origen y destino de cada traslado, el costo de lo vendido por hora de
# pedido, el calendario del descargo de ventas y los nombres de las áreas.
# `compras.parquet`, desde la regla #753: la hora en que se procesó cada
# compra, para pasar al mes nuevo la que se procesó antes de la apertura.
_ARCHIVOS_SIN_PLATO = ("salidas.parquet", "ventas.parquet",
                       "recetaventa.parquet", "cartacosteada.parquet",
                       "inventariovalorizado.parquet", "recetabase.parquet",
                       "transferencias.parquet", "paloteoinsumosnivel1.parquet",
                       "descargosventas.parquet", "ajusteinventario.parquet",
                       "compras.parquet")


def _df_o_vacio(con, sql):
    """El resultado de `sql`, o un DataFrame vacío si el parquet todavía no
    existe (la fila del Sheet es nueva) o no se pudo leer: el reloj
    operativo y el mapa por área quedan sin ese dato, la cuenta no."""
    try:
        return con.execute(sql).df()
    except Exception:
        return pd.DataFrame()


def _contado_por_area_dia(con, bucket):
    """El valor CONTADO por área y día de `ajusteinventario.parquet`
    (`area` entero, `dia`, `v`): de ahí `sin_plato.areas_con_stock` saca
    qué áreas ponen el corte de cada cierre (regla #750). Vacío si no se
    pudo leer: entonces cortan todas, como antes."""
    return _df_o_vacio(con, f"""
        SELECT CAST("CODIGO AREA" AS INTEGER) AS area,
               CAST("FECHA APERTURA INVENTARIO" AS DATE) AS dia,
               sum("VALORIZADO TOTAL") AS v
        FROM read_parquet('s3://{bucket}/ajusteinventario.parquet')
        GROUP BY 1, 2""")


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _sin_plato_cacheable(archivo, sello, sellos=(), version=None):
    """En qué se fue cada producto, de cierre a cierre de inventario
    (`sin_plato.calcular`, regla #645), con el reloj OPERATIVO —cada área de
    su conteo al siguiente (regla #743); desde la #750, el único, y cortado
    sólo por las áreas que contaron stock—: `{"operativo": {...}, "puente",
    "nombres_area"}`, con `periodos`, `filas`, `totales`, `areas` (el
    balance por área, `sin_plato.por_area`) y `borde` (lo vendido de un lado
    del conteo y descontado del otro). Si falla, LANZA: no se cachea.

    `archivo` es el kardex, que manda; `sellos`, los de los otros parquets
    (`_ARCHIVOS_SIN_PLATO`), y `version`, la de la cuenta. Ninguno se usa en
    el cuerpo: son la clave (ver el bloque del sello). Del kardex se baja lo
    agregado por período, área, producto y tipo, y las fotos del stock, que
    ya cachea `_kardex_fotos_cacheable`."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]

    def ruta(a):
        return f"read_parquet('s3://{bucket}/{a}')"
    rel = ruta(archivo)
    dias = con.execute(kardex.sql_dias_ajuste(rel)).df()
    ses = sesiones_inventario(pd.to_datetime(dias["dia"]))
    per = sin_plato.periodos(ses)
    if not per:
        return None
    desde = per[0]["t0"] - pd.Timedelta(days=10)
    areas = [int(a) for a in con.execute(kardex.sql_areas(rel, desde)).df()["area"].dropna()]
    per_op = sin_plato.periodos_operativos(
        per, con.execute(kardex.sql_horas_ajuste(rel, desde)).df(), areas,
        con_stock=sin_plato.areas_con_stock(_contado_por_area_dia(con, bucket), ses))
    fotos = _kardex_fotos_cacheable(kardex.ARCHIVO, sello_datos(kardex.ARCHIVO),
                                    version=kardex.VERSION)
    vend = _venta_clase_dia_cacheable(
        "ventas.parquet", sello_datos("ventas.parquet"),
        definicion=_version_preparar("ventas.parquet"))
    salidas, recetaventa = cargar("salidas.parquet"), cargar("recetaventa.parquet")
    carta, maestro = cargar("cartacosteada.parquet"), cargar("inventariovalorizado.parquet")
    recetabase = cargar("recetabase.parquet")
    desde_sql = f"TIMESTAMP '{desde:%Y-%m-%d %H:%M:%S}'"
    trans = _df_o_vacio(con, f"""
        SELECT "COD TIPO" AS tipo, "FECHA HORA" AS t, "CODIGO AREA ORIGEN" AS o,
               "CODIGO AREA DESTINO" AS d, "CODIGO PRODUCTO" AS cod, "VALOR" AS v,
               "DOCUMENTO" AS doc, "AREA ORIGEN" AS no, "AREA DESTINO" AS nd
        FROM {ruta('transferencias.parquet')} WHERE "FECHA HORA" >= {desde_sql}""")
    nombres_area = {}
    for col_c, col_n in (("o", "no"), ("d", "nd")):
        if not trans.empty:
            for c, n in zip(pd.to_numeric(trans[col_c], errors="coerce"), trans[col_n]):
                if pd.notna(c) and isinstance(n, str) and n.strip():
                    nombres_area.setdefault(int(c), n.strip())
    aj_nom = _df_o_vacio(con, f"""SELECT DISTINCT "CODIGO AREA" AS c, "AREA" AS n
        FROM {ruta('ajusteinventario.parquet')}""")
    for c, n in zip(pd.to_numeric(aj_nom.get("c", pd.Series(dtype=str)), errors="coerce"),
                    aj_nom.get("n", pd.Series(dtype=str))):
        if pd.notna(c) and isinstance(n, str) and n.strip():
            nombres_area.setdefault(int(c), n.strip())
    mae = sin_plato._maestro(maestro)
    clase = dict(zip(mae["cod"], np.where(mae["familia"].str.upper() == sin_plato.FAMILIA_OPERACION,
                                          sin_plato.OPERACION, sin_plato.ALIMENTOS)))
    nombres = dict(zip(mae["cod"], mae["producto"]))
    pedidos = _df_o_vacio(con, f"""
        SELECT "FECHA PEDIDO" AS t, sum("COSTO TOTAL") AS costo
        FROM {ruta('paloteoinsumosnivel1.parquet')}
        WHERE "FECHA PEDIDO" >= {desde_sql} GROUP BY 1""")
    corridas = _df_o_vacio(con, f"""
        SELECT "INICIO CORRIDA" AS ini, "VENTAS DESDE" AS desde, "VENTAS HASTA" AS hasta
        FROM {ruta('descargosventas.parquet')}""")
    ven = sin_plato.ventanas(per_op, areas)
    kx = con.execute(kardex.sql_movimientos_ventanas(
        rel, list(ven.itertuples(index=False, name=None)))).df()
    # El cierre físico (#752): lo que el descargo de antes de la apertura
    # vendió el mes nuevo pasa a su mes, y el ajuste se corrige.
    bordes = sin_plato.bordes_fisicos(per_op)
    nuevas = pd.concat([
        sin_plato.ventas_del_mes_nuevo(
            _df_o_vacio(con, kardex.sql_descargos_antes_de_apertura(rel, bordes)),
            corridas, pedidos),
        # Y las compras del mes nuevo procesadas antes de la apertura (#753).
        sin_plato.compras_del_mes_nuevo(cargar("compras.parquet", notas_credito=False), bordes),
    ], ignore_index=True)
    kx = sin_plato.cierre_fisico(kx, nuevas, len(per_op))
    stock = sin_plato.stock_por_area(fotos, ven)
    r = sin_plato.calcular(per_op, kx, fotos, salidas, vend, recetaventa, carta,
                           maestro, recetabase=recetabase, stock=stock)
    r["areas"] = sin_plato.por_area(kx, stock, trans, ven, clase, nombres)
    res = {"operativo": r}
    res["operativo"]["borde"] = sin_plato.ventas_del_borde(pedidos, corridas, per_op)
    res["puente"] = {
        "operativo": sin_plato.resumen_reloj(res["operativo"]["filas"], per_op,
                                             res["operativo"]["borde"])}
    res["nombres_area"] = nombres_area
    return res


def sin_plato_relojes():
    """Lo de `_sin_plato_cacheable` entero —el reloj operativo, su resumen
    y los nombres de las áreas— o `None` si no se pudo calcular (sin
    secrets, R2 caído, el kardex sin cierres): quien lo pide avisa. Reglas
    #743 y #750."""
    try:
        return _sin_plato_cacheable(
            kardex.ARCHIVO, sello_datos(kardex.ARCHIVO),
            sellos=tuple((a, sello_datos(a)) for a in _ARCHIVOS_SIN_PLATO),
            version=(sin_plato.VERSION, kardex.VERSION,
                     _version_preparar("ventas.parquet")))
    except Exception:
        return None


def sin_plato_por_cierre(reloj="operativo"):
    """`{"periodos", "filas", "totales", "areas", "borde"}` del reloj
    operativo (`sin_plato.RELOJES`): lo que dibujan «Sin plato, cierre por
    cierre» y «En qué se fue cada producto» (reglas #645, #743 y #750).
    `None` si no se pudo calcular. No cacheada (la interna sí)."""
    r = sin_plato_relojes()
    return r.get(reloj) if r else None


# Lo que lee «Consistencia de datos» de Costos (`consistencia_maestro`,
# regla #686), además del maestro de stock, que manda: sus sellos van en la
# clave de la caché. `_ARCHIVOS_CONSISTENCIA_CRUDOS` se leen tal cual.
_ARCHIVOS_CONSISTENCIA_CRUDOS = (
    "recetaventa.parquet", "recetabase.parquet", "cartacosteada.parquet",
    "auditoriacostos.parquet", "porcionamientos.parquet", "salidas.parquet",
    "pedidos.parquet", "descargosventas.parquet", "ajusteinventario.parquet")
_ARCHIVOS_CONSISTENCIA = (
    *_ARCHIVOS_CONSISTENCIA_CRUDOS, kardex.ARCHIVO, "compras.parquet",
    "notascreditocompras.parquet", "ventas.parquet", "sunat_compras.parquet")
_COLS_KARDEX_CONSISTENCIA = ("FECHA HORA", "CODIGO AREA", "CODIGO PRODUCTO",
                             "COD TIPO", "CANT INGRESO", "CANT SALIDA",
                             "VALOR SALIDA")


def consistencia_entradas(hoy=None):
    """`(t, hoy)`: el dict de `consistencia_maestro.ENTRADAS` leído de R2 y
    la fecha de corte (el último día del kardex, si no se da). LANZA si
    algo falla. Lo usan la caché de abajo y
    `herramientas/consistencia_maestro.py`, que no cachea."""
    import consistencia_maestro as cm
    import sunat
    import tipo_compra
    from graficos.compras import documentos_sunat as ds
    from graficos.inventario import separar_activos
    from graficos.ventas import unico_por_item

    t = {"inv": cargar("inventariovalorizado.parquet")}
    for clave, archivo in zip(("rv", "rb", "cc", "aud", "porc", "sal", "ped", "dsc", "ajs"),
                              _ARCHIVOS_CONSISTENCIA_CRUDOS):
        t[clave] = cargar(archivo)
    faltan = [k for k, v in t.items() if v is None]
    if faltan:
        raise RuntimeError("no se pudo leer: " + ", ".join(faltan))
    t["inv"] = t["inv"].copy()
    t["inv"]["_activo"] = t["inv"].index.isin(separar_activos(t["inv"])[0].index)
    bucket = st.secrets["R2_BUCKET"]
    cols = ", ".join(f'"{c}"' for c in _COLS_KARDEX_CONSISTENCIA)
    t["kdx"] = get_conn().execute(
        f"SELECT {cols} FROM read_parquet('s3://{bucket}/{kardex.ARCHIVO}')").df()
    if hoy is None:
        hoy = pd.to_datetime(t["kdx"]["FECHA HORA"]).max().normalize()
    hoy = pd.Timestamp(hoy).normalize()
    t["cmp"] = cargar("compras.parquet")
    ini = (hoy - pd.Timedelta(days=cm.VENTANA)).date()
    # Por la fecha del documento, no la del turno: los controles miran días
    # de calendario y no tienen por qué seguir el selector de Ventas.
    t["ven"] = unico_por_item(cargar_rango("ventas.parquet", "FEC REG DOCUMENTO",
                                           ini, hoy.date(), turno=False))
    reg = sunat._registro_de_parquet()
    if reg is not None and len(reg):
        compras = cargar("compras.parquet", notas_credito=False)
        g = ds._parquet_agrupado_por_documento(compras, "FECHA_EMISION_DOC", ini,
                                               hoy.date(), notas=notas_credito_compras())
        f = pd.to_datetime(reg["fecha_emision"], errors="coerce")
        cruce = ds.cruzar_con_parquet(reg[f >= pd.Timestamp(ini)], g)
        cruce = cruce[~cruce["proveedor"].astype(str).str.contains(_NO_MERCADERIA, case=False)]
        tablas = tipo_compra.tablas_almacen(compras, tipo_compra.tipos_de_producto(t["inv"]))
        t["sunat"] = tipo_compra.clasificar(cruce, reg, tablas)
    return t, hoy


@st.cache_data(ttl=3600, persist="disk", show_spinner=False, max_entries=2)
def _consistencia_cacheable(archivo, sello, sellos=(), version=None):
    """Los casos de cada control de «Consistencia de datos» (regla #686):
    `{"hoy", "casos": {id: DataFrame o el texto de su error}}`. Si la carga
    falla, LANZA: no se cachea. `archivo` es el maestro de stock; `sellos`,
    los de `_ARCHIVOS_CONSISTENCIA`, y `version`, la de los controles y la
    definición de venta. Ninguno se usa en el cuerpo: son la clave."""
    if not secrets_disponibles():
        return None
    import consistencia_maestro as cm
    t, hoy = consistencia_entradas()
    res = cm.calcular(t, hoy)
    return {"hoy": hoy, "casos": {k: (v if isinstance(v, pd.DataFrame)
                                      else f"{type(v).__name__}: {v}")
                                  for k, v in res.items()}}


# ── LO QUE YA SE CALCULÓ EN ESTE PROCESO (2026-10-23, regla #711) ───────
# Los Pendientes del período (Inicio) muestran señales que calculan otras
# vistas —Consistencia de datos, Análisis de diferencias, Recetas vs
# Porcionado— y la regla del boceto aprobado es que NO las calculen ellos:
# «cada señal sale de la vista que la calcula hoy, de lo que esa vista ya
# dejó en caché; si todavía no se calculó, dice "sin calcular" y no 0».
# Algunas tardan un minuto la primera vez, y la portada no puede.
#
# `st.cache_data` no deja preguntar si algo está sin calcularlo, así que
# quien calcula lo RECUERDA acá, con los sellos de sus datos: un recuerdo
# con otros sellos es de datos viejos y no cuenta. Vive en el proceso —lo
# comparten las sesiones— y se pierde al reiniciar; ahí la caché de disco
# sigue, y «Calcular ahora» de los Pendientes la encuentra al instante.
_RECIENTES = {}


def recordar(nombre, sellos, resultado):
    """Guarda `resultado` de la cuenta `nombre` hecha con `sellos`. Un None
    no se recuerda: no se pudo calcular."""
    if resultado is not None:
        _RECIENTES[nombre] = (sellos, resultado)


def recordado(nombre, sellos):
    """Lo que la cuenta `nombre` dejó con estos mismos `sellos`, o None."""
    r = _RECIENTES.get(nombre)
    return r[1] if r is not None and r[0] == sellos else None


def _clave_consistencia():
    import consistencia_maestro as cm
    import tipo_compra
    return (sello_datos("inventariovalorizado.parquet"),
            tuple((a, sello_datos(a)) for a in _ARCHIVOS_CONSISTENCIA),
            (cm.VERSION, _version_preparar("ventas.parquet"), tipo_compra.VERSION))


def consistencia_maestro(solo_si_calculado=False):
    """Lo de `_consistencia_cacheable`, o None si no se pudo —sin secrets,
    R2 caído—: quien lo pide avisa. La primera vez de cada versión de los
    parquets tarda ~1 min. No cacheada (la interna sí). Con
    `solo_si_calculado`, lo que ya se calculó en este proceso con los datos
    de hoy, sin calcular nada (regla #711)."""
    try:
        sello, sellos, version = _clave_consistencia()
        if solo_si_calculado:
            return recordado("consistencia", (sello, sellos, version))
        r = _consistencia_cacheable("inventariovalorizado.parquet",
                                    sello_datos("inventariovalorizado.parquet"),
                                    sellos=sellos, version=version)
        recordar("consistencia", (sello, sellos, version), r)
        return r
    except Exception:
        return None


# Los parquets que, además del kardex, lee el «Análisis de diferencias» de
# Ajuste (`diferencias_ajuste.calcular`, regla #650): sus sellos van en la
# clave de la caché.
_ARCHIVOS_DIFERENCIAS = ("ajusteinventario.parquet", "recetaventa.parquet",
                         "recetabase.parquet", "cartacosteada.parquet",
                         "porcionamientos.parquet", "ordenesproduccion.parquet",
                         "salidas.parquet", "ventas.parquet", "combosdetalle.parquet",
                         "requerimientos.parquet", "sunat_compras.parquet",
                         "compras.parquet", "notascreditocompras.parquet",
                         "paloteoinsumosnivel1.parquet", "pedidos.parquet",
                         "inventariovalorizado.parquet", "descargosventas.parquet")


@st.cache_data(ttl=3600, persist="disk", show_spinner=False, max_entries=12)
def _diferencias_cacheable(archivo, sello, clave, sellos=(), version=None):
    """Por qué no cuadra cada línea de la sesión de inventario `clave`
    (`diferencias_ajuste.calcular`, regla #650). Si falla, LANZA: no se
    cachea.

    `archivo` es el kardex; `sellos`, los de los otros diecisiete parquets
    (`_ARCHIVOS_DIFERENCIAS`), y `version`, la de la cuenta. Ninguno se usa
    en el cuerpo: son la clave (ver el bloque del sello). Del kardex se bajan
    las filas desde `DIAS_ATRAS` días antes de la sesión hasta `DIAS_TARDE`
    días después de su último día (de ahí sale cuándo fue el siguiente
    descargo de ventas, #650): unas 60 mil por cierre. Del paloteo, los
    mismos días hasta la sesión. Medido sobre el cierre de setiembre 2026:
    6 s de cuenta, una vez por versión de los datos."""
    if not secrets_disponibles():
        return None
    aj = cargar("ajusteinventario.parquet")
    ses = sesiones_inventario(pd.to_datetime(aj["FECHA APERTURA INVENTARIO"],
                                             errors="coerce"))
    s = next((x for x in ses if x["clave"] == clave), None)
    if s is None:
        return None
    desde = min(s["dias"]) - timedelta(days=diferencias_ajuste.DIAS_ATRAS)
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    kx = con.execute(kardex.sql_filas(
        rel, desde, max(s["dias"]) + timedelta(days=diferencias_ajuste.DIAS_TARDE))).df()
    # Lo que descuenta cada pedido, el día contable de cada pedido y el factor
    # de cada producto (#650). Sin ellos, la cuenta sigue sin las pistas de
    # ventas sin descontar ni de combo.
    d0, d1 = desde - timedelta(days=2), max(s["dias"]) + timedelta(days=1)
    try:
        pal = con.execute(f"""
            SELECT "FECHA PEDIDO", "FECHA ITEM", "COD PEDIDO", "TIPO PRODUCTO",
                   "COD PRODUCTO", "PRODUCTO", "CANT VENDIDA", "COD INSUMO", "CONSUMO TOTAL"
            FROM read_parquet('s3://{bucket}/paloteoinsumosnivel1.parquet')
            WHERE "FECHA PEDIDO" >= TIMESTAMP '{desde:%Y-%m-%d} 00:00:00'
              AND "FECHA PEDIDO" < TIMESTAMP '{d1:%Y-%m-%d} 00:00:00'
        """).df()
        ped = con.execute(f"""
            SELECT "CODIGO PEDIDO", "DIA CONTABLE"
            FROM read_parquet('s3://{bucket}/pedidos.parquet')
            WHERE "FECHA APERTURA" >= TIMESTAMP '{d0:%Y-%m-%d} 00:00:00'
        """).df()
        mae = con.execute(f"""
            SELECT DISTINCT "CODIGO PRODUCTO", "FACTOR"
            FROM read_parquet('s3://{bucket}/inventariovalorizado.parquet')
        """).df()
    except Exception:
        pal = ped = mae = None
    # El calendario de los descargos de ventas (TLOG_DESCARGO, la fila
    # `descargosventas` del Sheet): qué venta tomó cada uno. Sin él, la cuenta
    # lo deduce de las horas del kardex.
    try:
        dsc = con.execute(f"""
            SELECT "INICIO CORRIDA", "VENTAS DESDE", "VENTAS HASTA"
            FROM read_parquet('s3://{bucket}/descargosventas.parquet')
        """).df()
    except Exception:
        dsc = None
    vend = _venta_por_producto_dia_cacheable(
        "ventas.parquet", sello_datos("ventas.parquet"),
        definicion=_version_preparar("ventas.parquet"))
    # La ficha de los combos (#651). Sin ella la cuenta sigue, sin la pista
    # de combo: no es motivo para dejar la vista en blanco.
    try:
        combos = cargar("combosdetalle.parquet")
    except Exception:
        combos = None
    # Quién pide cada producto, y las facturas que SUNAT tiene y el Almacén
    # no (#652). Lo mismo: sin ellos, la cuenta sigue sin esas pistas.
    try:
        reqs = cargar("requerimientos.parquet")
    except Exception:
        reqs = None
    su = sunat_sin_ingresar(min(s["dias"]) - timedelta(days=45), max(s["dias"]))
    return diferencias_ajuste.calcular(
        aj, s, ses, kx, cargar("recetaventa.parquet"),
        cargar("recetabase.parquet"), cargar("cartacosteada.parquet"),
        cargar("porcionamientos.parquet"), cargar("ordenesproduccion.parquet"),
        cargar("salidas.parquet"), vend, combos=combos, requerimientos=reqs, sunat=su,
        paloteo=pal, pedidos=ped, maestro=mae, descargos=dsc)


# Los emisores que no venden mercadería: sus comprobantes no se leen (#652).
_NO_MERCADERIA = ("BANCO|FINANCIERA|SEGUROS|REASEGUROS|CAJA RURAL|CAJA MUNICIPAL|"
                  "ENTIDAD PRESTADORA|RAPPI|PLUXEE")


@st.cache_data(ttl=3600, persist="disk", show_spinner=False, max_entries=12)
def _sunat_sin_ingresar_cacheable(archivo, sello, desde, hasta, sellos=(), version=None):
    """Las líneas del XML de los comprobantes que SUNAT registra y el Almacén
    no —«Solo SUNAT» en «Documentos SUNAT», el MISMO cruce
    (`cruzar_con_parquet`)—, emitidos entre `desde` y `hasta`: `doc`, `ruc`,
    `prov`, `fecha` y lo de `sunat.lineas_xml`. Las lee Ajuste › «Análisis de
    diferencias» para decir qué factura sin ingresar explica un sobrante
    (regla #652). Si falla, LANZA: no se cachea.

    `archivo` es el registro del SIRE y `sellos`, los de las compras y sus
    notas. Los XML se bajan de R2 EN PARALELO: de a uno eran 205 s por mes
    y medio de comprobantes; con 16 hilos, 17. Un original que el sync baje
    DESPUÉS no cambia la clave: entra con el registro del día siguiente."""
    if not secrets_disponibles():
        return None
    from concurrent.futures import ThreadPoolExecutor
    import sunat
    from graficos.compras import documentos_sunat as _ds
    reg = sunat._registro_de_parquet()
    if reg is None or reg.empty:
        return None
    f = pd.to_datetime(reg["fecha_emision"], errors="coerce")
    reg = reg[(f >= pd.Timestamp(desde)) & (f < pd.Timestamp(hasta) + pd.Timedelta(days=1))]
    if reg.empty:
        return None
    compras = cargar(definicion_compra.ARCHIVO, notas_credito=False)
    cruce = _ds.cruzar_con_parquet(reg, _ds._parquet_agrupado_por_documento(
        compras, "FECHA_EMISION_DOC", desde, hasta, notas=notas_credito_compras()))
    solo = cruce[(cruce["estado"] == "Solo SUNAT")
                 & ~cruce["proveedor"].astype(str).str.contains(_NO_MERCADERIA, case=False)]
    if solo.empty:
        return None
    s3 = get_s3_cliente()
    bucket = st.secrets["R2_BUCKET"]

    def leer(par):
        ruc, doc = par
        serie, _, numero = str(doc).partition("-")
        try:
            return s3.get_object(Bucket=bucket, Key=sunat._clave_original(
                ruc, serie, numero, "xml"))["Body"].read()
        except Exception:
            return None
    with ThreadPoolExecutor(16) as ex:
        xmls = list(ex.map(leer, zip(solo["ruc_proveedor"], solo["documento"])))
    filas = []
    for r, xml in zip(solo.itertuples(index=False), xmls):
        for li in sunat.lineas_xml(xml):
            filas.append({"doc": r.documento, "ruc": r.ruc_proveedor, "prov": r.proveedor,
                          "fecha": r.fecha_emision, **li})
    return pd.DataFrame(filas) if filas else None


def sunat_sin_ingresar(desde, hasta):
    """Las líneas de las facturas que SUNAT tiene y el Almacén no, emitidas
    entre `desde` y `hasta` (`date`), o None —sin secrets, sin registro, R2
    caído—. No cacheada (la interna sí). Regla #652."""
    try:
        return _sunat_sin_ingresar_cacheable(
            "sunat_compras.parquet", sello_datos("sunat_compras.parquet"), desde, hasta,
            sellos=tuple((a, sello_datos(a)) for a in (definicion_compra.ARCHIVO,
                                                       definicion_compra.ARCHIVO_NOTAS)),
            version=1)
    except Exception:
        return None


def diferencias_ajuste_sesion(clave, solo_si_calculado=False):
    """`{"lineas", "fichas", "resumen"}` de `diferencias_ajuste.calcular` para
    la sesión `clave` (`cortes.sesiones_inventario`). `None` si no se pudo
    calcular —sin secrets, R2 caído, la sesión sin diferencias—: quien lo
    pide avisa. No cacheada (la interna sí). Con `solo_si_calculado`, lo que
    ya se calculó en este proceso con los datos de hoy (regla #711)."""
    try:
        sello = sello_datos(kardex.ARCHIVO)
        sellos = tuple((a, sello_datos(a)) for a in _ARCHIVOS_DIFERENCIAS)
        version = (diferencias_ajuste.VERSION, kardex.VERSION,
                   _version_preparar("ventas.parquet"))
        llave = (clave, sello, sellos, version)
        if solo_si_calculado:
            return recordado(f"diferencias_{clave}", llave)
        r = _diferencias_cacheable(kardex.ARCHIVO, sello_datos(kardex.ARCHIVO), clave,
                                   sellos=sellos, version=version)
        recordar(f"diferencias_{clave}", llave, r)
        return r
    except Exception:
        return None


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _historia_stock_cacheable(archivo, sello, version=None):
    """`(rótulos, momentos, valores)`: el valor de cada área y producto
    después de cada cierre y hoy (`analisis_stock.momentos_de_cierre` y
    `valor_en_momentos`), sobre las fotos del kardex. Son 14 pasadas sobre
    medio millón de filas —unos segundos—, por eso va a disco con el sello.
    Si falla, LANZA: no se cachea. Regla #637.

    Las fotos se piden con `sello_datos(archivo)` y no con el `sello` que ya
    llegó: es el mismo valor (vive 60 s en su caché), y `test_datos.py` exige
    esa forma en toda llamada a una cacheable de disco (regla #367)."""
    fotos = _kardex_fotos_cacheable(archivo, sello_datos(archivo), version=version)
    if fotos is None or fotos.empty:
        return None
    tope = pd.to_datetime(fotos["fecha"], errors="coerce").max().to_pydatetime()
    pares = analisis_stock.momentos_de_cierre(tope)
    momentos = [m for _, m in pares]
    return ([r for r, _ in pares], momentos,
            analisis_stock.valor_en_momentos(fotos, momentos))


def historia_stock():
    """Lo que valía cada área y producto después de cada uno de los últimos
    cierres y hoy: `(rótulos, momentos, valores)`, con `valores` indexado
    por (código de área, código de producto). `None` si no se pudo leer el
    kardex: quien lo pide no dibuja la historia. No cacheada (la interna
    sí). Regla #637."""
    try:
        return _historia_stock_cacheable(kardex.ARCHIVO,
                                         sello_datos(kardex.ARCHIVO),
                                         version=kardex.VERSION)
    except Exception:
        return None


def consumo_stock(hasta):
    """Cuánto consumió el restaurante de cada producto en los
    `analisis_stock.VENTANA_CONSUMO` días que terminan en `hasta` (`date`):
    Series `cod` → cantidad. `None` si no se pudo leer. Sale de los
    movimientos del kardex (cacheados) por `analisis_stock.consumo_por_producto`.
    Regla #637."""
    desde = hasta - timedelta(days=analisis_stock.VENTANA_CONSUMO - 1)
    movs = movimientos_kardex(desde, hasta)
    if movs is None:
        return None
    return analisis_stock.consumo_por_producto(movs)


def movimientos_kardex(desde, hasta):
    """Los movimientos del kardex entre dos fechas (`date`), por área,
    producto y tipo. `None` si no se pudo leer: quien lo pide avisa. No
    cacheada (la interna sí), por lo mismo que `cargar()`."""
    try:
        return _movimientos_cacheable(kardex.ARCHIVO,
                                      sello_datos(kardex.ARCHIVO),
                                      desde, hasta, version=kardex.VERSION)
    except Exception:
        return None


# ── Movimientos por Tipo, de conteo a conteo (regla #747) ──────────────
# El reloj operativo de «En qué se fue cada producto» (#743) para Stock ›
# Movimientos por Tipo: cada área desde la hora siguiente a su conteo hasta
# la de su conteo siguiente. Los períodos salen de los ajustes (93) del
# kardex; las puntas, de la foto en la hora del corte de cada área, o sea
# el stock CONTADO.

def _primer_cierre():
    """El mes del cierre que abre el primer período: el anterior a
    `kardex.INICIO`, para que enero de 2025 tenga su período."""
    y, m = kardex.INICIO.year, kardex.INICIO.month
    return (y - 1, 12) if m == 1 else (y, m - 1)


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _periodos_conteo_cacheable(archivo, sello, version=None, sello_ajuste=None):
    """`{"periodos": [...], "sesiones": [...]}`: los períodos de conteo a
    conteo (`sin_plato.periodos_operativos`, sin las sesiones adentro), más
    el que está EN CURSO —desde el último cierre hasta el último movimiento
    del kardex—, y las sesiones de conteo (`cortes.sesiones_inventario`).
    Si falla, LANZA: no se cachea. `sello`, `version` y `sello_ajuste` (el
    de `ajusteinventario.parquet`, que dice qué áreas contaron stock, regla
    #750) son la clave."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    dias = con.execute(kardex.sql_dias_ajuste(rel)).df()
    ses = sesiones_inventario(pd.to_datetime(dias["dia"]))
    per = sin_plato.periodos(ses, desde=_primer_cierre())
    sesiones = [{k: s[k] for k in ("clave", "tipo", "mes", "nombre", "etiqueta",
                                   "etiqueta_anio", "dias", "ini", "fin")}
                for s in ses]
    if not per:
        return {"periodos": [], "sesiones": sesiones}
    desde = per[0]["t0"] - pd.Timedelta(days=10)
    areas = [int(a) for a in con.execute(kardex.sql_areas(rel, desde)).df()["area"].dropna()]
    horas = con.execute(kardex.sql_horas_ajuste(rel, desde)).df()
    # El corte lo ponen las áreas que contaron stock, como en Destino (#750).
    per_op = sin_plato.periodos_operativos(
        per, horas, areas,
        con_stock=sin_plato.areas_con_stock(_contado_por_area_dia(con, bucket), ses))
    campos = ("k", "clave", "mes", "nombre", "corto", "desde", "hasta", "t0", "t1",
              "c0", "c1", "dias", "ventanas", "cierre", "cierre_ant")
    out = [dict({c: p[c] for c in campos}, en_curso=False) for p in per_op]
    tope = con.execute(kardex.sql_ultimo_movimiento(rel)).fetchone()[0]
    ult = out[-1]
    if tope is not None and pd.Timestamp(tope) >= ult["t1"]:
        # El período que está corriendo: cada área desde su último conteo
        # hasta el final de la hora del último movimiento.
        t1 = pd.Timestamp(tope).floor("h") + pd.Timedelta(hours=1)
        y, m = ult["mes"]
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        out.append({
            "k": len(out), "clave": f"en_curso_{y}-{m:02d}", "mes": (y, m),
            "nombre": f"{MESES_LARGOS_ES[m - 1].capitalize()} {y}",
            "corto": f"{MESES_ABR_ES[m - 1]} {y % 100:02d}",
            "desde": ult["c1"].date(), "hasta": (t1 - pd.Timedelta(hours=1)).date(),
            "t0": ult["t1"], "t1": t1, "c0": ult["c1"], "c1": None,
            "dias": (t1 - ult["c1"]) / pd.Timedelta(days=1),
            "ventanas": {a: (v[1], t1) for a, v in ult["ventanas"].items()},
            "cierre": None, "cierre_ant": ult["cierre"], "en_curso": True})
    return {"periodos": out, "sesiones": sesiones}


def periodos_conteo():
    """Lo de `_periodos_conteo_cacheable`, o `None` si no se pudo leer el
    kardex: la vista se queda con las fechas del calendario."""
    try:
        return _periodos_conteo_cacheable(kardex.ARCHIVO, sello_datos(kardex.ARCHIVO),
                                          version=(kardex.VERSION, sin_plato.VERSION),
                                          sello_ajuste=sello_datos("ajusteinventario.parquet"))
    except Exception:
        return None


def _mov_cierre_fisico(con, bucket, rel, mov, ventanas, c0, c1):
    """`mov` (lo de `kardex.sql_movimientos_tipo_ventanas`, un período) con
    el cierre físico (regla #752): lo que el descargo de antes de la apertura
    del conteo de INICIO vendió este mes entra (con el sobrante que le cargó
    al cierre anterior, de vuelta), y lo que el de antes de la apertura del
    de FIN vendió el mes siguiente sale (con el faltante que el POS borró).
    Igual las compras del mes que se procesaron antes de cada apertura
    (`sin_plato.compras_del_mes_nuevo`, regla #753).
    `c0`/`c1`: el 1 del mes y el del siguiente (`c1` None en el que corre)."""
    bordes = []
    for a, t0, t1 in ventanas:
        if c0:
            bordes.append((-1, int(a), pd.Timestamp(c0), pd.Timestamp(t0)))
        if c1:
            bordes.append((0, int(a), pd.Timestamp(c1), pd.Timestamp(t1)))
    if not bordes:
        return mov
    desc = _df_o_vacio(con, kardex.sql_descargos_antes_de_apertura(rel, bordes))
    partes = [sin_plato.compras_del_mes_nuevo(cargar("compras.parquet", notas_credito=False),
                                              bordes)]
    if not desc.empty:
        d0 = pd.Timestamp(min(b[2] for b in bordes)) - pd.Timedelta(days=40)
        pedidos = _df_o_vacio(con, f"""
            SELECT "FECHA PEDIDO" AS t, sum("COSTO TOTAL") AS costo
            FROM read_parquet('s3://{bucket}/paloteoinsumosnivel1.parquet')
            WHERE "FECHA PEDIDO" >= TIMESTAMP '{d0:%Y-%m-%d %H:%M:%S}' GROUP BY 1""")
        corridas = _df_o_vacio(con, f"""
            SELECT "INICIO CORRIDA" AS ini, "VENTAS DESDE" AS desde, "VENTAS HASTA" AS hasta
            FROM read_parquet('s3://{bucket}/descargosventas.parquet')""")
        partes.append(sin_plato.ventas_del_mes_nuevo(desc, corridas, pedidos))
    nuevas = pd.concat([p for p in partes if not p.empty], ignore_index=True) \
        if any(not p.empty for p in partes) else pd.DataFrame()
    if nuevas.empty:
        return mov
    codigo = {int(c): str(c) for c in mov["area"].dropna().astype(str).str.strip() if c.isdigit()}
    nombre = dict(zip(mov["tipo"], mov["nombre"]))
    m = mov.assign(k=0, area=pd.to_numeric(mov["area"], errors="coerce"))
    m = sin_plato.cierre_fisico(m, nuevas, 1)
    m["area"] = m["area"].map(lambda a: codigo.get(int(a), f"{int(a):03d}"))
    m["nombre"] = m["nombre"].fillna(m["tipo"].map(nombre)).fillna(
        m["tipo"].map({sin_plato.TIPO_VENTAS: "Descargo de Ventas",
                       sin_plato.TIPO_AJUSTE: "Ajuste Inventarios", "01": "Factura"}))
    nums = [c for c in mov.columns if c not in ("area", "cod", "tipo", "nombre")]
    m[nums] = m[nums].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    g = m.groupby(["area", "cod", "tipo"], as_index=False).agg(
        nombre=("nombre", "first"), **{c: (c, "sum") for c in nums})
    return g[list(mov.columns)]


@st.cache_data(ttl=3600, persist="disk", show_spinner=False)
def _movimientos_conteo_cacheable(archivo, sello, ventanas, version=None, c0=None, c1=None,
                                  sello_compras=None):
    """Lo que entró y salió de cada área y producto por tipo de documento
    dentro de SU ventana (`ventanas`: tupla de `(área, t0, t1)` en texto
    ISO, `t1` exclusivo), y las dos fotos —el stock en la hora del corte de
    cada área—: `(mov, foto_ini, foto_fin)` con las columnas de
    `kardex.sql_movimientos` y `kardex.sql_stock_al`. Con `c0`/`c1` (el mes
    físico, texto ISO), el cierre físico de la regla #752
    (`_mov_cierre_fisico`). Si falla, LANZA."""
    if not secrets_disponibles():
        return None
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    rel = f"read_parquet('s3://{bucket}/{archivo}')"
    mov = con.execute(kardex.sql_movimientos_tipo_ventanas(rel, list(ventanas))).df()
    mov = _mov_cierre_fisico(con, bucket, rel, mov, ventanas, c0, c1)
    fotos = _kardex_fotos_cacheable(archivo, sello_datos(archivo), version=kardex.VERSION)
    ven = pd.DataFrame([(0, int(a), pd.Timestamp(t0), pd.Timestamp(t1))
                        for a, t0, t1 in ventanas], columns=["k", "area", "t0", "t1"])
    stock = sin_plato.stock_por_area(fotos, ven)
    # El código del área como lo escribe el kardex («001»), no el entero.
    codigo = {}
    for c in fotos["area"].dropna().astype(str).str.strip().unique():
        if c.isdigit():
            codigo.setdefault(int(c), c)

    def foto(punta):
        s = stock[stock["punta"] == punta]
        q = pd.to_numeric(s["q"], errors="coerce").fillna(0.0)
        v = pd.to_numeric(s["v"], errors="coerce").fillna(0.0)
        return pd.DataFrame({
            "area": s["area"].map(lambda a: codigo.get(int(a), f"{int(a):03d}")),
            "cod": s["cod"].astype(str), "stock": q,
            "precio": np.where(q.abs() > 1e-12, v / q.where(q.abs() > 1e-12, 1.0), 0.0),
        }).reset_index(drop=True)
    return mov, foto("ini"), foto("fin")


def movimientos_conteo(periodo):
    """`(mov, foto_ini, foto_fin)` del `periodo` de `periodos_conteo`, o
    `None` si no se pudo leer: quien lo pide avisa. No cacheada (la interna
    sí)."""
    ventanas = tuple((int(a), pd.Timestamp(t0).isoformat(), pd.Timestamp(t1).isoformat())
                     for a, (t0, t1) in sorted(periodo["ventanas"].items()))

    def iso(x):
        return pd.Timestamp(x).isoformat() if x is not None and pd.notna(x) else None
    try:
        r = _movimientos_conteo_cacheable(kardex.ARCHIVO, sello_datos(kardex.ARCHIVO),
                                          ventanas, version=(kardex.VERSION, sin_plato.VERSION),
                                          sello_compras=sello_datos("compras.parquet"),
                                          c0=iso(periodo.get("c0")), c1=iso(periodo.get("c1")))
    except Exception:
        return None
    return r
