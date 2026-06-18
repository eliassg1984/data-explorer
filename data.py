"""
Gestión de datos: conexión DuckDB, carga de archivos y configuración de reportes.
"""

import streamlit as st
import duckdb


# ===========================================================================
# CONFIGURACIÓN DE REPORTES
# ===========================================================================

REPORTES = {
    "Ajuste de Inventario": {
        "archivo": "ajusteinventaria.parquet",
        "icono": "sliders",
    },
    "Compras": {
        "archivo": "compras.parquet",
        "icono": "cart",
    },
    "Inventario Valorizado": {
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
        "archivo": "recetabase.parquet",
        "icono": "clipboard-data",
    },
    "Receta Venta": {
        "archivo": "recetaventa.parquet",
        "icono": "receipt",
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
# CARGA DE DATOS
# ===========================================================================

@st.cache_data(ttl=3600)
def cargar(archivo):
    """
    Carga un archivo parquet desde R2.
    Retorna el DataFrame o None si hay error.
    """
    try:
        con = get_conn()
        bucket = st.secrets["R2_BUCKET"]
        url = f"s3://{bucket}/{archivo}"
        return con.execute(f"SELECT * FROM read_parquet('{url}')").df()
    except Exception as e:
        st.error(f"Error cargando {archivo}: {str(e)}")
        return None
