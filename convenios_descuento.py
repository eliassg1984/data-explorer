"""
convenios_descuento — lo que el BANCO le devuelve al restaurante de un
descuento (regla #665).

Un descuento de convenio con un banco no lo paga entero el restaurante:
el banco le devuelve una parte. El POS no lo sabe (`TMOTIVODESCUENTO`
trae el porcentaje y el tope del descuento, no la devolución), y el Power
BI del grupo lo tenía en una tabla escrita a mano. Acá es una tabla que se edita desde la app (reporte
«Costos») y se guarda en R2.

    devolución de una línea = descuento × % de devolución del convenio
                              vigente ese día para su código

Dos cosas que la de Power BI no tenía, y por qué:

  · VIGENCIA (desde / hasta, ambas opcionales): un convenio cambia, y
    cambiar el % de hoy no puede reescribir los meses pasados.
  · El CÓDIGO del POS y no el nombre: los nombres no calzan entre Power
    BI y el POS (mayúsculas, abreviaturas).

LA TABLA NO VA EN EL REPO, que es público: son términos de un convenio con
un banco. El código arranca con la tabla vacía (sin convenios, todo como
antes) y los valores viven sólo en R2, en `CLAVE_R2`.

Quién la usa: `costo_ventas.descuentos_por` (el costo de la parte regalada
baja en lo que el banco devuelve) y `graficos/ventas_mix.py` (el «% costo»
se mide sobre el neto MÁS la devolución, como el «FC Venta» de Power BI).
"""

import datetime as dt
import hashlib
import json

import pandas as pd
import streamlit as st

CLAVE_R2 = "_config/convenios_descuento.json"
COLUMNAS = ("codigo", "nombre", "devolucion", "desde", "hasta")
"""Una fila por convenio. `devolucion` es una fracción (de 0 a 1);
`desde`/`hasta`, fechas ISO o vacías (sin límite de ese lado)."""

COD_DESCUENTO = "CODIGO DESCUENTO"
NOMBRE_DESCUENTO = "NOMBRE DESCUENTO"


# ── La tabla (pura) ──────────────────────────────────────────────────────

def codigo(valor):
    """El código del POS como lo escribe `ventas.parquet`: tres dígitos
    («15» → «015»). Vacío si no hay."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    s = str(valor).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(3) if s.isdigit() else s


def _fecha(valor):
    if valor is None or valor == "" or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    try:
        return pd.Timestamp(valor).date()
    except (TypeError, ValueError):
        return None


def normalizar(filas):
    """La tabla limpia, con `COLUMNAS` por nombre: una lista de dicts (lo
    que viene de R2) o un DataFrame (lo que devuelve el editor). Descarta
    las filas sin código o con una devolución fuera de 0–1, y recorta la
    devolución a esa franja. Las fechas quedan como `datetime.date` o None."""
    df = pd.DataFrame(filas if filas is not None else [])
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = None
    df = df[list(COLUMNAS)].copy()
    df["codigo"] = df["codigo"].map(codigo)
    df["nombre"] = df["nombre"].map(lambda v: "" if v is None or (
        isinstance(v, float) and pd.isna(v)) else str(v).strip())
    df["devolucion"] = pd.to_numeric(df["devolucion"], errors="coerce")
    df = df[(df["codigo"] != "") & df["devolucion"].between(0.0, 1.0)]
    df["desde"] = df["desde"].map(_fecha)
    df["hasta"] = df["hasta"].map(_fecha)
    return df.reset_index(drop=True)


def como_json(tabla):
    """Lo que se guarda en R2: una lista de dicts con las fechas en ISO."""
    t = normalizar(tabla)
    return [{"codigo": r.codigo, "nombre": r.nombre,
             "devolucion": round(float(r.devolucion), 4),
             "desde": r.desde.isoformat() if r.desde else None,
             "hasta": r.hasta.isoformat() if r.hasta else None}
            for r in t.itertuples()]


def huella(tabla):
    """Una cadena que cambia cuando cambia la tabla: va en la clave de las
    cachés que la usan (`graficos/costos.py::_datos`)."""
    texto = json.dumps(como_json(tabla), sort_keys=True)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]


def devolucion_por_linea(codigos, fechas, tabla):
    """Por línea, la fracción del descuento que devuelve el banco: la del
    convenio de su código vigente ese día, o 0. `codigos` y `fechas`, dos
    Series con el mismo índice. Si dos filas del mismo código se pisan en
    el tiempo, gana la que empieza más tarde (la más nueva)."""
    salida = pd.Series(0.0, index=codigos.index)
    t = normalizar(tabla)
    if t.empty or codigos.empty:
        return salida
    cod = codigos.map(codigo)
    dia = pd.to_datetime(fechas, errors="coerce").dt.normalize()
    t = t.assign(_ini=t["desde"].map(lambda d: d or dt.date.min))
    for r in t.sort_values("_ini").itertuples():
        m = cod == r.codigo
        if r.desde:
            m &= dia >= pd.Timestamp(r.desde)
        if r.hasta:
            m &= dia <= pd.Timestamp(r.hasta)
        salida[m] = float(r.devolucion)
    return salida


# ── R2 ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _leer_r2():
    import data

    if not data.secrets_disponibles():
        return []
    try:
        crudo = data.get_s3_cliente().get_object(
            Bucket=st.secrets["R2_BUCKET"], Key=CLAVE_R2)["Body"].read()
        return json.loads(crudo)
    except Exception:
        return []


def leer():
    """La tabla vigente (vacía si no hay archivo, sin secrets o con R2
    caído: sin convenios todo se mide como antes)."""
    return normalizar(_leer_r2())


def guardar(tabla):
    """Escribe la tabla ENTERA en R2. True si quedó guardada. No lanza."""
    import data

    if not data.secrets_disponibles():
        return False
    try:
        data.get_s3_cliente().put_object(
            Bucket=st.secrets["R2_BUCKET"], Key=CLAVE_R2,
            Body=json.dumps(como_json(tabla), ensure_ascii=False).encode("utf-8"),
            ContentType="application/json")
    except Exception:
        return False
    _leer_r2.clear()
    return True


@st.cache_data(ttl=3600, show_spinner=False)
def _catalogo(sello):
    """`{código: nombre}` de los descuentos que aparecen en la venta, el
    nombre más reciente de cada código. `sello` es la clave (#367)."""
    import data

    if not data.secrets_disponibles():
        return {}
    bucket = st.secrets["R2_BUCKET"]
    df = data.get_conn().execute(f"""
        SELECT "{COD_DESCUENTO}" AS c, arg_max("{NOMBRE_DESCUENTO}", "FEC REG DOCUMENTO") AS n
        FROM read_parquet('s3://{bucket}/ventas.parquet')
        WHERE "{COD_DESCUENTO}" IS NOT NULL AND trim("{COD_DESCUENTO}") <> ''
        GROUP BY 1 ORDER BY 1""").df()
    return {codigo(c): str(n).strip() for c, n in zip(df["c"], df["n"])}


def catalogo():
    """Los descuentos que se pueden elegir en el editor. `{}` si no se
    pudo leer la venta."""
    import data

    try:
        return _catalogo(data.sello_datos("ventas.parquet"))
    except Exception:
        return {}
