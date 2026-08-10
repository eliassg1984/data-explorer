"""asistente_datos.py — capa de DATOS del asistente IA (sin nada de LLM ni UI).

Por qué existe separado de `asistente.py`: ese módulo es el cliente de Groq +
la UI del popover. Lo de acá es "cómo se le da de comer al modelo", y se puede
probar entero sin API key ni navegador — de hecho `test_asistente_datos.py`
lo hace. Esa testeabilidad es el motivo de la separación.

Qué resuelve
------------
El asistente ANTES recibía un resumen de 7 líneas del df (totales + top 5 de
UNA categórica) y nada más: ni los nombres de las columnas. Con eso no podía
responder "qué producto tuvo más merma" — no por tonto, por ciego. Ahora:

- `esquema_para_prompt()` describe la tabla REAL (columnas, tipos y, para las
  categóricas de baja cardinalidad, sus VALORES posibles). Eso último es lo
  que evita que el modelo adivine `AREA = 'Producción'` cuando el dato dice
  `'PRODUCCION'`.
- `ejecutar_sql()` corre SQL de solo lectura con DuckDB sobre el DataFrame en
  memoria. Sin round-trip a R2: DuckDB consulta un df de pandas directo, así
  que una pregunta cuesta milisegundos y S/ 0.
- `resumen_para_prompt()` da el panorama de arranque (totales, rango de
  fechas, filtros activos) para que las preguntas simples no gasten una
  ronda de tool calling.

Trampas aprendidas midiendo esto con 4 modelos (ver arquitectura.md regla #61)
-----------------------------------------------------------------------------
- **Los nombres de columna llevan ESPACIOS** (`AJUSTE VALORIZADO`), así que
  todo SQL necesita comillas dobles. Los 4 modelos probados lo hicieron bien
  solos, pero el prompt lo dice explícito porque es gratis asegurarlo.
- **El riesgo real no es la sintaxis, es la semántica:** 3 de 4 modelos
  respondieron "los 5 productos con más merma" con un `ORDER BY ... LIMIT 5`
  sobre filas CRUDAS — o sea los 5 movimientos más grandes, no los 5
  productos. De ahí la convención de agregación que se le impone en el
  system prompt de `asistente.py`.
- **Nunca dejar que el modelo sume en prosa:** `llama-3.3-70b` listó cinco
  cifras que suman −28.907 y afirmó que el total era −30.070. El SQL calcula
  los totales; el modelo solo los narra.
"""

from __future__ import annotations

import json
import re

import pandas as pd

# Tope de filas que se le devuelven al modelo por consulta. No es por
# seguridad sino por CONTEXTO: 60 filas de JSON ya son ~4k caracteres, y
# pasado eso el modelo empieza a resumir mal y a perder las primeras.
MAX_FILAS_RESULTADO = 60

# Cardinalidad máxima para listarle los valores de una columna categórica.
# Con más de esto la lista deja de ser útil (y come contexto): se le dice
# cuántos valores distintos hay y que consulte si necesita el detalle.
MAX_VALORES_CATEGORICOS = 25

_NOMBRE_TABLA = "datos"

# SQL prohibido. DuckDB puede leer y ESCRIBIR ficheros (read_parquet, COPY ...
# TO, INSTALL/LOAD de extensiones), así que no basta con "registro solo el df
# y listo": una consulta podría tocar el disco del server. El modelo no tiene
# ninguna razón legítima para usar nada de esto — la tabla ya está registrada.
_PALABRAS_PROHIBIDAS = (
    "insert", "update", "delete", "drop", "create", "alter", "attach",
    "detach", "copy", "install", "load", "pragma", "export", "import",
    "read_parquet", "read_csv", "read_json", "glob", "system",
)


# ─── Esquema ───────────────────────────────────────────────────────────────
def _tipo_legible(serie: pd.Series) -> str:
    """dtype de pandas -> etiqueta que el modelo entienda como tipo SQL."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return "FECHA"
    if pd.api.types.is_bool_dtype(serie):
        return "BOOLEAN"
    if pd.api.types.is_integer_dtype(serie):
        return "ENTERO"
    if pd.api.types.is_float_dtype(serie):
        return "DECIMAL"
    return "TEXTO"


def esquema_para_prompt(df: pd.DataFrame) -> str:
    """Describe la tabla para el system prompt: columnas, tipos y valores.

    Para las columnas de TEXTO con pocos valores distintos incluye la lista
    completa. Es la diferencia entre que el modelo escriba
    `WHERE "AREA" = 'PRODUCCION'` (existe) o `= 'Producción'` (no existe, 0
    filas, y el usuario cree que no hay datos).
    """
    if df is None or df.empty:
        return "(sin datos en el rango/filtros actuales)"

    lineas = []
    for col in df.columns:
        serie = df[col]
        tipo = _tipo_legible(serie)
        detalle = ""
        if tipo == "TEXTO":
            try:
                vals = serie.dropna().astype(str).unique()
            except Exception:
                vals = []
            if 0 < len(vals) <= MAX_VALORES_CATEGORICOS:
                detalle = "  valores: " + ", ".join(
                    f"'{v}'" for v in sorted(vals)[:MAX_VALORES_CATEGORICOS])
            elif len(vals):
                detalle = f"  ({len(vals):,} valores distintos)"
        elif tipo == "FECHA":
            try:
                detalle = (f"  rango: {serie.min():%Y-%m-%d} a "
                           f"{serie.max():%Y-%m-%d}")
            except Exception:
                detalle = ""
        lineas.append(f'  "{col}"  {tipo}{detalle}')
    return "\n".join(lineas)


# ─── Resumen de arranque ───────────────────────────────────────────────────
def _col_valor(df: pd.DataFrame) -> str | None:
    """La columna numérica que mejor representa "el dinero" del reporte."""
    for kw in ("ajuste valorizado", "valorizado total", "importe", "valorizado",
               "total", "monto", "precio"):
        for c in df.columns:
            if kw in str(c).lower() and pd.api.types.is_numeric_dtype(df[c]):
                return c
    nums = df.select_dtypes("number").columns.tolist()
    return nums[0] if nums else None


def resumen_para_prompt(df: pd.DataFrame, reporte: str,
                        filtros: dict | None = None) -> str:
    """Panorama de arranque: qué está viendo el usuario AHORA MISMO.

    No pretende reemplazar a las consultas — pretende que "¿cómo vamos?" se
    responda sin gastar una ronda de tool calling, y que el modelo sepa que
    hay filtros activos (si no, contesta totales que contradicen la pantalla).
    """
    if df is None or df.empty:
        return (f"Reporte activo: {reporte or '—'}. "
                "El filtro actual no devuelve ninguna fila.")

    partes = [f"Reporte activo: {reporte or '—'}",
              f"Filas visibles: {len(df):,}"]

    filtros = {k: v for k, v in (filtros or {}).items() if v}
    if filtros:
        detalle = "; ".join(
            f"{k} = {', '.join(map(str, v)) if isinstance(v, (list, tuple, set)) else v}"
            for k, v in filtros.items())
        partes.append(f"FILTROS ACTIVOS (ya aplicados a `datos`): {detalle}")
    else:
        partes.append("Filtros activos: ninguno")

    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            try:
                partes.append(f"Rango de fechas visible ({c}): "
                              f"{df[c].min():%d/%m/%Y} a {df[c].max():%d/%m/%Y}")
            except Exception:
                pass
            break

    cv = _col_valor(df)
    if cv:
        try:
            partes.append(f"Suma de \"{cv}\": S/ {df[cv].sum():,.2f}")
        except Exception:
            pass

    return "\n".join(partes)


# ─── Ejecución de SQL ──────────────────────────────────────────────────────
def _validar_sql(sql: str) -> str | None:
    """Devuelve el motivo del rechazo, o None si la consulta es aceptable."""
    limpio = (sql or "").strip().rstrip(";").strip()
    if not limpio:
        return "consulta vacía"
    # Un solo statement: un `;` en medio permitiría colar un segundo comando.
    if ";" in limpio:
        return "solo se permite UNA sentencia (sin ';' intermedios)"
    if not re.match(r"^\s*(select|with)\b", limpio, re.IGNORECASE):
        return "solo se permiten consultas SELECT (o WITH ... SELECT)"
    # \b para no vetar por substring: 'CREATE' no debe dispararse dentro de
    # un nombre de columna legítimo tipo "FECHA CREACION".
    for palabra in _PALABRAS_PROHIBIDAS:
        if re.search(rf"\b{palabra}\b", limpio, re.IGNORECASE):
            return f"palabra no permitida en una consulta de lectura: {palabra}"
    return None


def _sin_literales(sql: str) -> str:
    """El SQL con los tramos entre comillas (dobles y simples) removidos.

    Sirve para buscar identificadores SIN citar: lo que queda son solo los
    tokens desnudos. Se quitan también los literales de texto ('...') para no
    marcar un WHERE "PRODUCTO" = 'AJUSTE VALORIZADO' como si la columna
    estuviera sin comillas.
    """
    sin_dobles = re.sub(r'"[^"]*"', " ", sql)
    return re.sub(r"'[^']*'", " ", sin_dobles)


def columnas_sin_comillas(sql: str, columnas) -> list[str]:
    """Columnas CON ESPACIOS que el SQL usa sin comillas dobles.

    Esto NO es cosmética, es el fallo más peligroso de todos: en la lista de
    un SELECT, `SELECT AJUSTE VALORIZADO FROM datos` no da error — DuckDB lo
    lee como `SELECT AJUSTE AS VALORIZADO` y devuelve la columna de UNIDADES
    (-10) etiquetada con el nombre de la de SOLES (-1000). Verificado en vivo.
    El modelo narraría "S/ -10" con total naturalidad y ni el usuario ni yo
    podríamos detectarlo: no hay excepción, no hay warning, solo una cifra
    equivocada por dos órdenes de magnitud.

    Dentro de una función agregada (`SUM(AJUSTE VALORIZADO)`) sí revienta con
    ParserException, así que el peligro es solo el SELECT/GROUP BY/ORDER BY
    desnudo — que es exactamente donde el modelo lo escribiría.
    """
    desnudo = _sin_literales(sql)
    culpables = []
    # NO `columnas or []`: si es un pandas Index, el `or` lo evalúa como bool
    # y lanza "The truth value of a Index is ambiguous".
    for col in ([] if columnas is None else list(columnas)):
        nombre = str(col)
        if " " not in nombre:
            continue   # sin espacios no hace falta citarla
        if re.search(rf"\b{re.escape(nombre)}\b", desnudo, re.IGNORECASE):
            culpables.append(nombre)
    return culpables


def _con_limite(sql: str, limite: int = MAX_FILAS_RESULTADO) -> str:
    """Añade LIMIT si la consulta no trae uno — el modelo lo olvida seguido."""
    limpio = sql.strip().rstrip(";").strip()
    if re.search(r"\blimit\s+\d+\s*$", limpio, re.IGNORECASE):
        return limpio
    return f"{limpio}\nLIMIT {limite}"


def ejecutar_sql(df: pd.DataFrame, sql: str) -> dict:
    """Corre `sql` (solo lectura) contra `df`, expuesto como tabla `datos`.

    Devuelve SIEMPRE un dict serializable — nunca lanza. Un error tiene que
    volver al modelo como texto para que pueda corregir la consulta y
    reintentar; si esto lanzara, el turno entero se caería por un typo suyo.
    """
    motivo = _validar_sql(sql)
    if motivo:
        return {"ok": False, "error": f"Consulta rechazada: {motivo}"}

    if df is None or df.empty:
        return {"ok": False, "error": "No hay filas visibles con los filtros actuales."}

    # Guarda contra el fallo SILENCIOSO de las columnas con espacios sin
    # comillas (ver columnas_sin_comillas). Se rechaza con instrucciones para
    # que el modelo corrija y reintente — es preferible una ronda extra a una
    # cifra equivocada que nadie puede detectar.
    culpables = columnas_sin_comillas(sql, df.columns)
    if culpables:
        lista = ", ".join(f'"{c}"' for c in culpables)
        return {"ok": False, "error": (
            f"Consulta rechazada: usa estas columnas SIN comillas dobles: "
            f"{lista}. Sin comillas, DuckDB lee 'SELECT AJUSTE VALORIZADO' "
            f"como 'SELECT AJUSTE AS VALORIZADO' y devuelve la columna "
            f"equivocada sin dar error. Reescribe la consulta citando cada "
            f"nombre de columna: {lista}.")}

    try:
        import duckdb
    except ImportError:  # pragma: no cover - duckdb es dependencia declarada
        return {"ok": False, "error": "DuckDB no está disponible en el servidor."}

    final = _con_limite(sql)
    con = None
    try:
        # Conexión NUEVA y en memoria por consulta: nada persiste entre
        # llamadas, así una consulta no puede dejarle estado a la siguiente.
        con = duckdb.connect(database=":memory:")
        con.register(_NOMBRE_TABLA, df)
        res = con.sql(final).df()
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}",
                "sql": final}
    finally:
        if con is not None:
            try:
                con.close()
            except Exception:
                pass

    truncado = len(res) >= MAX_FILAS_RESULTADO
    # to_json y no to_dict: resuelve Timestamp/NaN/numpy sin que haya que
    # convertir tipo por tipo a mano.
    try:
        filas = json.loads(res.head(MAX_FILAS_RESULTADO)
                              .to_json(orient="records", date_format="iso"))
    except Exception:
        filas = [{c: str(v) for c, v in fila.items()}
                 for fila in res.head(MAX_FILAS_RESULTADO).to_dict("records")]

    return {"ok": True, "sql": final, "filas_devueltas": len(filas),
            "truncado": truncado, "columnas": list(res.columns), "filas": filas}


# ─── Definición de herramientas (formato OpenAI/Groq) ──────────────────────
HERRAMIENTA_SQL = {
    "type": "function",
    "function": {
        "name": "consultar_datos",
        "description": (
            "Ejecuta una consulta SQL de SOLO LECTURA (DuckDB) sobre la tabla "
            "`datos`, que contiene exactamente las filas que el usuario está "
            "viendo en pantalla (rango de fechas y filtros ya aplicados). "
            "Úsala para CUALQUIER cifra: totales, rankings, comparaciones, "
            "conteos. Nunca calcules aritmética por tu cuenta."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": (
                        "SELECT de DuckDB sobre `datos`. Los nombres de columna "
                        "llevan espacios: enciérralos SIEMPRE en comillas dobles."
                    ),
                },
                "motivo": {
                    "type": "string",
                    "description": "En 6 palabras, qué buscas con esta consulta.",
                },
            },
            "required": ["sql"],
        },
    },
}

HERRAMIENTA_WEB = {
    "type": "function",
    "function": {
        "name": "buscar_web",
        "description": (
            "Busca en internet información que NO está en los datos del "
            "usuario: precios de mercado actuales, proveedores, noticias del "
            "sector. NO la uses para preguntas sobre los datos del reporte — "
            "para eso está consultar_datos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Términos de búsqueda optimizados para un buscador (NO "
                        "la pregunta literal del usuario). Ej: para '¿está caro "
                        "el pollo?' usa 'precio kilo pollo pechuga mercado "
                        "mayorista Lima 2026'."
                    ),
                },
            },
            "required": ["query"],
        },
    },
}

HERRAMIENTAS = [HERRAMIENTA_SQL, HERRAMIENTA_WEB]
