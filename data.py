"""
Gestión de datos: conexión DuckDB, carga de archivos y configuración de reportes.
"""

import streamlit as st
import duckdb
import pandas as pd
import numpy as np
import boto3
import json
from datetime import datetime, timezone


# ===========================================================================
# CONFIGURACIÓN DE REPORTES
# ===========================================================================

REPORTES = {
    "Ajuste de Inventario": {
        "label_corto": "Ajuste",
        "archivo": "ajusteinventario.parquet",
        "icono": "sliders",
        "filtros_cat": [],  # Sin filtros de Área/Familia/Subfamilia en el popover
        "agrupar": [],      # Sin opción de "Agrupar por" en el popover
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
    "Compras": {
        "label_corto": "Compras",
        "archivo": "compras.parquet",
        "icono": "cart",
    },
    "Inventario Valorizado": {
        "label_corto": "Inventario",
        "archivo": "inventariovalorizado.parquet",
        "icono": "boxes",
        "columnas": [
            "Nombre Familia", "Nombre Subfamilia", "Nombre Producto",
            "Unidad Kardex", "Codigo Producto", "Nombre Area", "Codigo Area", "Stock al Dia", "Precio Promedio", "Valorizado total"
        ],
        "filtros_cat": ["Nombre Area", "Nombre Familia"],
        "buscador": "Nombre Producto",
        "fecha": None,
        "agrupar": ["Nombre Area", "Nombre Familia", "Nombre Subfamilia"],
        "columnas_movil": [
            "Nombre Producto", "Stock al dia", "Precio Promedio",
            "Valorizado total", "Nombre Area",
        ],
        "columnas_fijas_movil": 2,
    },
    "Receta Base": {
        "label_corto": "R. Base",
        "archivo": "recetabase.parquet",
        "icono": "clipboard-data",
    },
    "Receta Venta": {
        "label_corto": "R. Venta",
        "archivo": "recetaventa.parquet",
        "icono": "receipt",
    },
    "Ventas": {
        "label_corto": "Ventas",
        "archivo": "ventas.parquet",
        "icono": "cash-coin",
        # Carga filtrada por rango de fechas DENTRO de DuckDB (no baja todo
        # el parquet). Al primer acceso: 01-del-mes-actual → hoy. El rango
        # aplicado vive en st.session_state[f"rango_carga_{reporte}"] y el
        # date_input del popover lo controla (ver app.py).
        "carga_por_rango": "FEC REG DOCUMENTO",
    },
    "Salidas": {
        "label_corto": "Salidas",
        "archivo": "salidas.parquet",
        "icono": "box-arrow-up",
        # NOTA: estos nombres deben coincidir con las columnas reales de
        # salidas.parquet. Si alguno no existe, la app solo muestra un aviso
        # (no se rompe) y puedes ajustarlo aquí.
        "filtros_cat": ["Nombre Area", "Nombre Familia"],
        "buscador": "Nombre Producto",
        "agrupar": ["Nombre Area", "Nombre Familia"],
        "columnas_movil": [
            "Nombre Producto", "Cantidad", "Importe Total", "Nombre Area",
        ],
        "columnas_fijas_movil": 2,
    },
    "Requerimientos": {
        "label_corto": "Requerim.",
        "archivo": "requerimientos.parquet",
        "icono": "card-checklist",
    },
    "Inspector": {
        "label_corto": "Inspector",
        # Herramienta de verificación de datos crudos (no es un parquet propio):
        # permite inspeccionar cualquiera de los archivos de arriba.
        "icono": "search",
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
    """Genera un DataFrame sintético acorde al reporte pedido. La semilla
    depende del nombre de archivo para que cada reporte sea estable."""
    rng = np.random.default_rng(abs(hash(archivo)) % (2**32))
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

    # Reportes genéricos (Compras, Ventas, Salidas, Requerimientos, etc.)
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

@st.cache_data(ttl=3600)
def cargar(archivo):
    """
    Carga un archivo parquet desde R2.
    Si no hay secrets de R2, devuelve datos demo en su lugar.
    Retorna el DataFrame o None si hay error.
    """
    # ── Modo demo: sin credenciales R2 → datos sintéticos en memoria ──
    if not secrets_disponibles():
        return _datos_demo(archivo)
    try:
        con = get_conn()
        bucket = st.secrets["R2_BUCKET"]
        url = f"s3://{bucket}/{archivo}"
        return con.execute(f"SELECT * FROM read_parquet('{url}')").df()
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None


@st.cache_data(ttl=3600)
def cargar_rango(archivo, col_fecha, ini, fin):
    """
    Como cargar(), pero filtrando por fecha DENTRO de DuckDB, antes de
    materializar el DataFrame (para parquets grandes como ventas.parquet:
    nunca se descargan/materializan las 100k+ filas completas).

    ini/fin: datetime.date (rango inclusivo).
    col_fecha: nombre EXACTO de la columna de fecha en el parquet.

    Maneja col_fecha tanto si es DATE/TIMESTAMP real como si viene como
    texto tipo '05/07/2026' (dd/mm/yyyy): COALESCE de dos intentos de cast.
    """
    # ── Modo demo: sin credenciales R2 → datos sintéticos filtrados ──
    if not secrets_disponibles():
        df = _datos_demo(archivo)
        col = "Fecha" if "Fecha" in df.columns else None
        if col:
            m = (df[col].dt.date >= ini) & (df[col].dt.date <= fin)
            return df[m]
        return df
    try:
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
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None
