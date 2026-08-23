"""
Utilidades generales: normalización, búsqueda de columnas y traducciones.
"""
 
import unicodedata
import pandas as pd
 
 
# ===========================================================================
# NORMALIZACIÓN Y BÚSQUEDA DE COLUMNAS
# ===========================================================================
 
def _norm(s):
    """Normaliza texto: quita acentos, espacios, guiones y pasa a minúsculas."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.lower().replace(" ", "").replace("_", "").replace("-", "")


def fmt_k(v):
    """Monto compacto: S/ 4.0k, S/ 1.2M.

    Vivía solo en `graficos/compras/_etiquetas_proveedor.py` (etiquetas de
    barra del drill de Proveedor); se movió acá el 2026-08-22 al necesitarlo
    también `navegacion.py` para los KPIs del rail de Reportes — es
    formateo genérico, no algo propio de Compras. Ese módulo reexporta este
    mismo símbolo para no romper sus imports existentes (mismo patrón que
    `graficos/compras/_comun.py::_es_movil`, ver CLAUDE.md).

    Negativos: la magnitud (no `v` directo) decide el corte k/M — sin esto,
    ningún negativo entraba nunca en `>= 1_000`/`>= 1_000_000` (comparación
    siempre falsa contra un número negativo) y caía al `else` sin abreviar
    ni agrupar miles: "S/ -56320" en vez de "S/ -56.3k". Se detectó al
    verificar el rail de Reportes con datos reales — Ajuste de Inventario
    puede dar Ajuste Valorizado negativo (mermas), a diferencia de los
    montos de venta/compra que motivaron la función original y siempre son
    positivos. El signo lo sigue poniendo el propio `:.1f`/`:.0f` sobre `v`
    (negativo), no hace falta agregarlo a mano."""
    m = abs(v)
    if m >= 1_000_000:
        return f"S/ {v / 1_000_000:.1f}M"
    if m >= 1_000:
        return f"S/ {v / 1_000:.1f}k"
    return f"S/ {v:.0f}"
 
 
def buscar_columna(df, *candidatos):
    """
    Busca una columna en el DataFrame por múltiples nombres candidatos.
    Retorna el nombre real de la columna o None si no se encuentra.
    """
    norm_map = {_norm(c): c for c in df.columns}
    for cand in candidatos:
        if _norm(cand) in norm_map:
            return norm_map[_norm(cand)]
    return None
 
 
def buscar_columna_fecha(df):
    """
    Encuentra automáticamente la columna de fecha en un DataFrame.
    Primero busca por tipo datetime, luego por nombre.
    """
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            return c
    for c in df.columns:
        if "fecha" in _norm(c) or "date" in _norm(c):
            return c
    return None
 
 
def resolver_columnas(df, nombres):
    """
    Resuelve nombres de columnas y reporta las no encontradas.
    Retorna (encontradas, faltantes).
    """
    encontradas, faltantes = [], []
    for n in nombres:
        real = buscar_columna(df, n)
        if real and real not in encontradas:
            encontradas.append(real)
        elif not real:
            faltantes.append(n)
    return encontradas, faltantes
 
 
# ===========================================================================
# TRADUCCIÓN AGGRID
# ===========================================================================
 
LOCALE_ES = {
    "sortAscending": "Ordenar ascendente",
    "sortDescending": "Ordenar descendente",
    "sortUnSort": "Quitar orden",
    "pinColumn": "Fijar columna",
    "pinLeft": "Fijar a la izquierda",
    "pinRight": "Fijar a la derecha",
    "noPin": "No fijar",
    "valueAggregation": "Agregación de valores",
    "autosizeThisColumn": "Autoajustar esta columna",
    "autosizeAllColumns": "Autoajustar todas las columnas",
    "groupBy": "Agrupar por",
    "ungroupBy": "Desagrupar por",
    "pivotMode": "Modo pivote",
    "groups": "Grupos de filas",
    "rowGroupColumnsEmptyMessage": "Arrastra campos aquí para agrupar por filas",
    "values": "Valores",
    "valueColumnsEmptyMessage": "Arrastra campos aquí para agregar valores",
    "pivots": "Etiquetas de columnas",
    "pivotColumnsEmptyMessage": "Arrastra campos aquí para columnas",
    "pivotColumnGroupTotals": "Total",
    "columnLabels": "Etiquetas de columnas",
    "rowGroupColumns": "Grupos de filas",
    "valueColumns": "Valores",
    "resetColumns": "Restablecer columnas",
    "expandAll": "Expandir todos los grupos",
    "collapseAll": "Colapsar todos los grupos",
    "copy": "Copiar",
    "copyWithHeaders": "Copiar con encabezados",
    "ctrlC": "Ctrl+C",
    "paste": "Pegar",
    "ctrlV": "Ctrl+V",
    "export": "Exportar",
    "csvExport": "Exportar a CSV",
    "excelExport": "Exportar a Excel",
    "chooseColumns": "Elegir columnas",
    "columnChooser": "Elegir columnas",
    "columns": "Columnas",
    "filters": "Filtros",
    "searchOoo": "Buscar…",
    "filterOoo": "Filtrar…",
    "blanks": "(En blanco)",
    "selectAll": "(Seleccionar todo)",
    "applyFilter": "Aplicar",
    "resetFilter": "Restablecer",
    "clearFilter": "Limpiar",
    "cancelFilter": "Cancelar",
    "equals": "Igual a",
    "notEqual": "Distinto de",
    "contains": "Contiene",
    "notContains": "No contiene",
    "startsWith": "Empieza con",
    "endsWith": "Termina con",
    "blank": "En blanco",
    "notBlank": "No en blanco",
    "lessThan": "Menor que",
    "lessThanOrEqual": "Menor o igual que",
    "greaterThan": "Mayor que",
    "greaterThanOrEqual": "Mayor o igual que",
    "inRange": "En rango",
    "page": "Página",
    "to": "a",
    "of": "de",
    "more": "más",
    "nextPage": "Página siguiente",
    "lastPage": "Última página",
    "firstPage": "Primera página",
    "previousPage": "Página anterior",
    "pageSizeSelectorLabel": "Tamaño de página:",
    "sum": "Suma",
    "min": "Mín",
    "max": "Máx",
    "none": "Ninguno",
    "count": "Conteo",
    "avg": "Promedio",
    "loadingOoo": "Cargando…",
    "noRowsToShow": "No hay datos para mostrar",
    "totalRows": "Total de filas",
    "totalAndFilteredRows": "Filas",
}
