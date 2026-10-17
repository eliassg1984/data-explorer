"""
presupuesto_ventas — el PRESUPUESTO de venta por mes y servicio (regla #669).

El POS no lo tiene (las tablas de presupuesto del Almacén están vacías);
vive en el Power BI del grupo, cargado por día y servicio. Acá se guarda
por MES y SERVICIO —venta bruta y neta, como el modelo—, se edita desde la
app (reporte «Costos») y va a R2, como la tabla de convenios
(`convenios_descuento.py`). NO va en el repo, que es público: el código
arranca sin presupuesto y la vista no dibuja nada.

    presupuesto de un día = presupuesto del mes de su servicio
                            × peso de su día de la semana

El peso sale de la VENTA: cuánto vendió, en promedio, cada día de la
semana en ese mes del año anterior (sin datos de ese mes, en toda la
historia). Así el mes da exacto y la semana o el día, una aproximación:
el Power BI trae el reparto diario de quien lo arma, que no sigue a la
venta (su domingo pesa más que el sábado). Lo que se compara es la venta
de TODOS los canales: con un filtro de canal o de grupo, el presupuesto
no aplica y la vista no lo muestra.
"""

import hashlib
import json

import pandas as pd
import streamlit as st

CLAVE_R2 = "_config/presupuesto_ventas.json"
COLUMNAS = ("anio", "mes", "servicio", "bruta", "neta")
"""Una fila por (año, mes, servicio). `servicio` en mayúsculas, como lo
escribe el POS («ALMUERZO», «CENA»)."""


# ── La tabla (pura) ──────────────────────────────────────────────────────

def normalizar(filas):
    """La tabla limpia, con `COLUMNAS` por nombre: una lista de dicts (R2)
    o un DataFrame (el editor). Descarta filas sin año, mes o servicio, o
    sin ningún monto; un monto que falta va en cero."""
    df = pd.DataFrame(filas if filas is not None else [])
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = None
    df = df[list(COLUMNAS)].copy()
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
    df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
    df["servicio"] = df["servicio"].map(
        lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v))
        else str(v).strip().upper())
    for c in ("bruta", "neta"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df = df[df["anio"].notna() & df["mes"].between(1, 12)
            & (df["servicio"] != "") & ((df["bruta"] != 0) | (df["neta"] != 0))]
    df = df.astype({"anio": int, "mes": int})
    return (df.drop_duplicates(["anio", "mes", "servicio"], keep="last")
            .sort_values(["anio", "mes", "servicio"]).reset_index(drop=True))


def como_json(tabla):
    t = normalizar(tabla)
    return [{"anio": int(r.anio), "mes": int(r.mes), "servicio": r.servicio,
             "bruta": round(float(r.bruta), 2), "neta": round(float(r.neta), 2)}
            for r in t.itertuples()]


def huella(tabla):
    texto = json.dumps(como_json(tabla), sort_keys=True)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:12]


def pesos_dia_semana(venta_dia):
    """`{(año, mes, día_semana): peso}` y `{día_semana: peso}` (el respaldo)
    a partir de la venta por día (`dia`, `neto`): el promedio diario de cada
    día de la semana, por mes y en toda la historia. Un día sin venta
    (cerrado) no entra en el promedio."""
    if venta_dia is None or len(venta_dia) == 0:
        return {}, {}
    v = (pd.DataFrame({"dia": pd.to_datetime(venta_dia["dia"]).dt.normalize(),
                       "neto": pd.to_numeric(venta_dia["neto"], errors="coerce")})
         .groupby("dia", as_index=False)["neto"].sum())
    v = v[v["neto"] > 0]
    if v.empty:
        return {}, {}
    v["a"], v["m"], v["w"] = v["dia"].dt.year, v["dia"].dt.month, v["dia"].dt.weekday
    por_mes = v.groupby(["a", "m", "w"])["neto"].mean().to_dict()
    general = v.groupby("w")["neto"].mean().to_dict()
    return por_mes, general


def por_dia(tabla, pesos):
    """El presupuesto día por día: `dia`, `servicio`, `bruta`, `neta`. Cada
    mes se reparte entre sus días según el peso de su día de la semana en
    ese mes del año ANTERIOR (`pesos`, de `pesos_dia_semana`); si ese mes no
    tiene los siete días con venta, con los de toda la historia; sin nada,
    parejo. La suma de cada mes es exactamente la de la tabla."""
    t = normalizar(tabla)
    cols = ["dia", "servicio", "bruta", "neta"]
    if t.empty:
        return pd.DataFrame(columns=cols)
    por_mes, general = pesos or ({}, {})
    partes = []
    for (a, m), g in t.groupby(["anio", "mes"]):
        dias = pd.date_range(f"{a}-{m:02d}-01", periods=pd.Timestamp(
            f"{a}-{m:02d}-01").days_in_month, freq="D")
        w = dias.weekday
        base = [por_mes.get((a - 1, m, x)) for x in range(7)]
        if any(b is None for b in base):
            base = [general.get(x) for x in range(7)]
        if any(b is None for b in base):
            base = [1.0] * 7
        peso = pd.Series([base[x] for x in w], index=dias, dtype=float)
        peso = peso / peso.sum()
        for r in g.itertuples():
            partes.append(pd.DataFrame({
                "dia": dias, "servicio": r.servicio,
                "bruta": (peso * r.bruta).to_numpy(),
                "neta": (peso * r.neta).to_numpy()}))
    return pd.concat(partes, ignore_index=True)[cols]


def en_rangos(diario, rangos, neto=False, servicios=None):
    """El presupuesto de cada `(inicio, fin)` de `rangos` (días incluidos),
    o None donde ningún día del rango tiene presupuesto cargado. Con
    `servicios`, sólo esos (como los escribe el POS)."""
    if diario is None or len(diario) == 0:
        return [None] * len(rangos)
    d = diario
    if servicios:
        quiero = {str(s).strip().upper() for s in servicios}
        d = d[d["servicio"].isin(quiero)]
    col = "neta" if neto else "bruta"
    dia = pd.to_datetime(d["dia"])
    salida = []
    for ini, fin in rangos:
        m = (dia >= pd.Timestamp(ini)) & (dia <= pd.Timestamp(fin))
        salida.append(float(d.loc[m, col].sum()) if m.any() else None)
    return salida


def aplica(filtros):
    """Si el presupuesto se puede comparar con lo que se ve: sólo con la
    venta entera de uno o todos los servicios. Un filtro de grupo, subgrupo
    o canal deja una parte de la venta que el presupuesto no separa."""
    filtros = filtros or {}
    return not any(filtros.get(k) for k in ("Grupo", "Sub Grupo", "Canal"))


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
    """La tabla vigente (vacía sin archivo, sin secrets o con R2 caído: sin
    presupuesto, la vista sigue como antes)."""
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


def diario():
    """El presupuesto día por día, con los pesos de la venta (la caché de
    disco de `data.venta_por_grupo_dia`). Vacío sin presupuesto."""
    import data

    t = leer()
    if t.empty:
        return por_dia(t, None)
    try:
        vd = data.venta_por_grupo_dia()
    except Exception:
        vd = None
    return _diario_cacheado(como_json(t),
                            None if vd is None else vd[["dia", "neto"]])


@st.cache_data(ttl=3600, show_spinner=False)
def _diario_cacheado(filas, venta_dia):
    return por_dia(filas, pesos_dia_semana(venta_dia))
