"""
Gestión de datos: conexión DuckDB, carga de archivos y configuración de reportes.
"""

import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import boto3
import json
import zlib
from datetime import datetime, timezone


# ===========================================================================
# CONFIGURACIÓN DE REPORTES
# ===========================================================================
# Claves que lee app.py (todas opcionales salvo `archivo`):
#
#   archivo, label_corto, icono      identidad del reporte
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

REPORTES = {
    # Orden del dict == orden del rail de navegación (navegacion.py::
    # inject_navegacion itera `reportes.items()` tal cual). Reordenar acá
    # reordena los iconos de arriba a abajo.
    "Compras": {
        "label_corto": "Compras",
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
    # Requerimientos y Salidas comparten UN ítem de nav ("Movimientos", ver
    # `grupo_nav` en navegacion.py::inject_navegacion) — el par describe un
    # flujo real: Requerimiento es la salida de stock de Almacén Central
    # HACIA un área de producción; Salidas es la BAJA que esa misma área
    # registra después (consumo/merma/evento — ver `Tipo Descargo`). No hay
    # llave que una un Requerimiento con la Salida que lo "cierra" (numeran
    # documentos en secuencias independientes), así que el cruce entre
    # ambos (`graficos/movimientos_comun.py::_comparativo_pedido_baja`) es
    # agregado por producto/familia/período, nunca documento a documento.
    # Confirmado con DuckDB directo contra R2 real (no demo) 2026-08-13:
    # 726 de los 968 productos de Salidas (75%) también aparecen en
    # Requerimientos — hay overlap real de producto entre los dos parquets
    # (0% overlap, por eso esas dos nunca se cruzan). Detalle en
    # arquitectura.md § Unificación Movimientos.
    "Salidas": {
        "label_corto": "Salidas",
        "grupo_nav": "Movimientos",
        "archivo": "salidas.parquet",
        "icono": ":material/sync_alt:",
        "kpis": (("Valorizado", "VALOR NETO", "sum"),
                 ("Documentos", "DOCUMENTO", "count_distinct")),
        "kpi_fecha": "FECHA REGISTRO",
        # Columnas confirmadas contra el parquet real (2026-08-04): destino
        # de la salida es "Sub Almacen" (no "Nombre Area" — no hay tal
        # columna en este reporte), cantidad/valorizado son "Cant Salida" /
        # "Valor Neto", el tipo de salida es "Tipo Descargo", y la jerarquía
        # de producto es Nombre Familia > Nombre SubFamilia > Nombre Producto.
        "fecha": "Fecha registro",
        "filtros_cat": ["Sub Almacen", "Nombre Familia"],
        "buscador": "Nombre Producto",
        "agrupar": ["Sub Almacen", "Nombre Familia", "Nombre SubFamilia", "Tipo Descargo"],
        "columnas_movil": [
            "Nombre Producto", "Cant Salida", "Valor Neto", "Sub Almacen",
        ],
        "columnas_fijas_movil": 2,
    },
    "Requerimientos": {
        "label_corto": "Requerim.",
        "grupo_nav": "Movimientos",
        "archivo": "requerimientos.parquet",
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
        # Producto — mismos nombres de columna "amigables" que Salidas
        # (ambos vienen del mismo ERP, SAPIENS), aunque el código de
        # producto real es CODIGO PRODUCTO acá vs COD PRODUCTO en Salidas.
        "fecha": "Fecha Registro",
        "filtros_cat": ["Sub Almacen", "Nombre Familia"],
        "buscador": "Nombre Producto",
        "columnas_movil": [
            "Nombre Producto", "Cantidad", "Valor Item", "Sub Almacen",
        ],
        "columnas_fijas_movil": 2,
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
        "label_corto": "Recetas",
        "grupo_nav": "Recetas",
        "archivo": "recetaventa.parquet",
        # El SEGUNDO parquet de la página. `app.py` sigue cargando uno solo
        # (`archivo`) y pasándolo como df_f; recetabase.parquet lo carga
        # graficos/recetas.py con data.cargar. Esta clave existe para que el
        # botón de refresco sepa que hay más de un parquet detrás del
        # reporte — sin ella, "Refrescar" dejaría las recetas base viejas y
        # no habría forma de actualizarlas desde la UI. Ver
        # navegacion.py::boton_refresco.
        "archivos_extra": ("recetabase.parquet",),
        "icono": ":material/receipt_long:",
        # Catálogo sin fecha: el KPI es un conteo, no un agregado por período
        # (kpi_fecha ausente a propósito — resumen_kpis() agrega la tabla
        # entera cuando no hay fecha, igual que hace este reporte mismo).
        # Solo "Platos": el KPI "Recetas" (count_distinct de COD RB) se fue
        # con la fusión porque resumen_kpis() agrega el df del `archivo`, y
        # COD RB vive en el parquet secundario.
        "kpis": (("Platos", "COD RV", "count_distinct"),),
    },
    "Nueva Receta": {
        "label_corto": "+ Nueva",
        "grupo_nav": "Recetas",
        "icono": ":material/receipt_long:",
        # No es un parquet: arma y costea una receta de venta a mano contra
        # inventariovalorizado.parquet, y la guarda como PROPUESTA en R2
        # (_recetas_propuestas/), sin tocar recetaventa.parquet directo. Ver
        # formulario_receta.py.
        "tool": True,
    },
    "Ajuste de Inventario": {
        "label_corto": "Ajuste",
        "archivo": "ajusteinventario.parquet",
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
        # El calendario de la franja ofrece la pestaña "Cortes" (filtrar por
        # la sesión de conteo exacta en vez de por intervalo, ver cortes.py).
        # Solo acá: en Ventas o Compras un "corte" no significa nada — las
        # fechas son continuas y las rachas serían ruido. Sin este flag el
        # panel de fecha queda idéntico a como estaba.
        "cortes": True,
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
    "Inventario Valorizado": {
        "label_corto": "Inventario",
        "archivo": "inventariovalorizado.parquet",
        "icono": ":material/inventory_2:",
        # Foto sin fecha (igual que Recetas): kpi_fecha ausente a
        # propósito, resumen_kpis() agrega la tabla entera.
        "kpis": (("Valorizado", "VALORIZADO TOTAL", "sum"),),
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
        # Carga filtrada por rango de fechas DENTRO de DuckDB (no baja todo
        # el parquet). Al primer acceso: 01-del-mes-actual → hoy. El rango
        # aplicado vive en st.session_state[f"rango_carga_{reporte}"] y el
        # date_input del popover lo controla (ver app.py).
        "carga_por_rango": "FEC REG DOCUMENTO",
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

@st.cache_resource
def get_conn():
    """Establece y retorna la conexión a R2 usando DuckDB."""
    try:
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"""
            SET s3_endpoint='{st.secrets["R2_ACCOUNT_ID"]}.r2.cloudflarestorage.com';
            SET s3_access_key_id='{st.secrets["R2_ACCESS_KEY"]}';
            SET s3_secret_access_key='{st.secrets["R2_SECRET_KEY"]}';
            SET s3_region='auto';
            SET s3_url_style='path';
        """)
        return con
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        st.stop()


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
        # (sumados 2026-08-24 para la tabla "Composición" de
        # recetaventa.py::_tabla_composicion_venta) son atributos del
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
                    # receta, no el insumo — ver docstring de
                    # recetaventa.py::_tabla_composicion_venta.
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

@st.cache_data(ttl=3600, persist="disk")
def _cargar_cacheable(archivo):
    """Lectura pura del parquet. Si falla, LANZA — así @st.cache_data NO cachea
    el fracaso. Ver `cargar()` para el porqué de este split.

    `persist="disk"` (2026-08-12): sin él, la caché vive SOLO en memoria del
    proceso, así que cada reinicio del server vuelve a bajar el parquet de R2
    — ventas.parquet son ~40s en frío. Peor en desarrollo: si tocás algo
    mientras baja, Streamlit cancela el run (StopException) y la descarga
    arranca de CERO; se puede quedar en un bucle donde nunca termina y parece
    que R2 está caído cuando no lo está.
    El `ttl` se sigue respetando con persist (verificado en 1.59), y sólo se
    persiste el ÉXITO: el split cacheada/wrapper de abajo no cambia."""
    # ── Modo demo: sin credenciales R2 → datos sintéticos en memoria ──
    if not secrets_disponibles():
        return _datos_demo(archivo)
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    return con.execute(f"SELECT * FROM read_parquet('{url}')").df()


def cargar(archivo):
    """
    Carga un archivo parquet desde R2.
    Si no hay secrets de R2, devuelve datos demo en su lugar.
    Retorna el DataFrame o None si hay error.

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
    try:
        return _cargar_cacheable(archivo)
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
    (archivo, col_fecha, ini, fin): Streamlit solo permite limpiar una
    entrada puntual pasando los CUATRO valores exactos, o vaciar la función
    entera. Acá no se conoce ini/fin del caller (y puede haber más de un
    rango cacheado a la vez si distintos usuarios miraron distintas
    ventanas), así que se vacía TODA — hoy Ventas es el único reporte con
    `carga_por_rango`, así que el radio es uno solo; si se suma otro
    reporte con el mismo patrón, seguirá siendo correcto (solo un poco más
    ancho: purga rangos de otros archivos que no hacía falta invalidar)."""
    _cargar_cacheable.clear(archivo)
    _cargar_rango_cacheable.clear()


@st.cache_data(ttl=3600, persist="disk")
def _cargar_rango_cacheable(archivo, col_fecha, ini, fin):
    """Lectura filtrada por rango. Si falla, LANZA — @st.cache_data no cachea el
    fracaso. Ver `cargar()` para el porqué del split cacheada/wrapper.

    `persist="disk"` por lo mismo que `_cargar_cacheable`: la clave incluye el
    rango, así que cada ventana que ya se miró una vez queda en disco y
    sobrevive al reinicio del server."""
    # ── Modo demo: sin credenciales R2 → datos sintéticos filtrados ──
    if not secrets_disponibles():
        df = _datos_demo(archivo)
        col = "Fecha" if "Fecha" in df.columns else None
        if col:
            m = (df[col].dt.date >= ini) & (df[col].dt.date <= fin)
            return df[m]
        return df
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"
    expr = (
        f'COALESCE('
        f'TRY_CAST("{col_fecha}" AS DATE), '
        f'TRY_CAST(TRY_STRPTIME(CAST("{col_fecha}" AS VARCHAR), \'%d/%m/%Y\') AS DATE)'
        f')'
    )
    return con.execute(
        f"SELECT * FROM read_parquet('{url}') WHERE {expr} BETWEEN ? AND ?",
        [ini, fin],
    ).df()


def cargar_rango(archivo, col_fecha, ini, fin):
    """
    Como cargar(), pero filtrando por fecha DENTRO de DuckDB, antes de
    materializar el DataFrame (para parquets grandes como ventas.parquet:
    nunca se descargan/materializan las 100k+ filas completas).

    ini/fin: datetime.date (rango inclusivo).
    col_fecha: nombre EXACTO de la columna de fecha en el parquet.

    Maneja col_fecha tanto si es DATE/TIMESTAMP real como si viene como
    texto tipo '05/07/2026' (dd/mm/yyyy): COALESCE de dos intentos de cast.

    No cacheada a propósito (la capa interna sí): un fallo transitorio NO debe
    quedar cacheado 1h como None. Mismo patrón que cargar().
    """
    try:
        return _cargar_rango_cacheable(archivo, col_fecha, ini, fin)
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None


@st.cache_data(ttl=3600, persist="disk")
def _rango_fechas_cacheable(archivo, col_fecha):
    """MIN/MAX de la fecha. Si falla, LANZA (no se cachea). El None de 'no hay
    fechas' SÍ es cacheable — es un resultado válido, no un error."""
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
        return _rango_fechas_cacheable(archivo, col_fecha)
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
def _resumen_kpis_cacheable(archivo, kpis, col_fecha, col_dedup):
    """Agregados SUM/COUNT DISTINCT directo en DuckDB, sin materializar
    filas — mismo espíritu que `_rango_fechas_cacheable`. Acota al MES EN
    CURSO cuando `col_fecha` viene dado (mismo default que usa la franja de
    fecha en app.py: `hoy.replace(day=1)` → hoy); si no, agrega la tabla
    entera — es el caso de los catálogos sin fecha (Recetas,
    Inventario Valorizado)."""
    if not secrets_disponibles():
        return {}
    con = get_conn()
    bucket = st.secrets["R2_BUCKET"]
    url = f"s3://{bucket}/{archivo}"

    where = ""
    if col_fecha:
        hoy = datetime.now(timezone.utc).date()
        ini = hoy.replace(day=1)
        where = f"WHERE {_expr_fecha_kpi(col_fecha)} BETWEEN '{ini}' AND '{hoy}'"

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
               f'FROM (SELECT {selects} FROM read_parquet(\'{url}\') {where} '
               f'GROUP BY "{col_dedup}")')
    else:
        partes = []
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
            filtro = kpi[3] if len(kpi) > 3 else None
            if filtro:
                col_f, vals = filtro
                lista = ", ".join("'" + str(v).replace("'", "''") + "'"
                                  for v in vals)
                partes.append(f'{fn}("{col}"){cierre} '
                              f'FILTER (WHERE "{col_f}" IN ({lista})) AS k{i}')
            else:
                partes.append(f'{fn}("{col}"){cierre} AS k{i}')
        sql = f'SELECT {", ".join(partes)} FROM read_parquet(\'{url}\') {where}'

    fila = con.execute(sql).fetchone()
    return {kpi[0]: fila[i] for i, kpi in enumerate(kpis)}


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
    try:
        return _resumen_kpis_cacheable(archivo, kpis, col_fecha, col_dedup)
    except Exception:
        return {}
