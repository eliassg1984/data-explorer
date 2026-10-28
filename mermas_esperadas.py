"""
mermas_esperadas — la merma que se espera de cada insumo de compra al
porcionarlo (regla #751).

Producción › «Consumo según ventas» dice cuánto pidió cada corte con el
rendimiento REAL de sus porcionamientos. Con una merma esperada se lee además
cuánto habría pedido con esa merma, y la diferencia en kilos y en soles:

    kilos con tu merma = kilos reales × (1 − merma real) ÷ (1 − tu merma)
    merma real         = 1 − peso de los cortes ÷ lo que puso el insumo

Es una lectura APARTE: no cambia el consumo. Se edita desde la vista y se
guarda en R2, como los convenios (`convenios_descuento.py`): una sola tabla
para todos, `{código del insumo: porcentaje}`.
"""

import json

import streamlit as st

CLAVE_R2 = "_config/mermas_esperadas.json"
TOPE = 90.0
"""Una merma de 90 % o más no es una merma esperada: es un error de tipeo."""


def normalizar(tabla):
    """`{código: porcentaje}` limpio: el código sin espacios, el porcentaje
    entre 0 y `TOPE` (sin incluirlo) con dos decimales. Lo demás se descarta."""
    out = {}
    if not isinstance(tabla, dict):
        return out
    for cod, valor in tabla.items():
        cod = str(cod).strip()
        try:
            x = float(valor)
        except (TypeError, ValueError):
            continue
        if cod and 0 <= x < TOPE:
            out[cod] = round(x, 2)
    return out


def con(tabla, cod, pct):
    """La tabla con la merma de `cod` puesta (o quitada, con `pct` None).
    None si el porcentaje no es válido."""
    t = dict(normalizar(tabla))
    cod = str(cod or "").strip()
    if not cod:
        return None
    if pct is None or pct == "":
        t.pop(cod, None)
        return t
    try:
        x = float(pct)
    except (TypeError, ValueError):
        return None
    if not 0 <= x < TOPE:
        return None
    t[cod] = round(x, 2)
    return t


@st.cache_data(ttl=300, show_spinner=False)
def _leer_r2():
    import data

    if not data.secrets_disponibles():
        return {}
    try:
        crudo = data.get_s3_cliente().get_object(
            Bucket=st.secrets["R2_BUCKET"], Key=CLAVE_R2)["Body"].read()
        return json.loads(crudo)
    except Exception:
        return {}


def leer():
    """La tabla vigente (vacía si no hay archivo, sin secrets o con R2
    caído: sin mermas esperadas la vista no muestra esa lectura)."""
    return normalizar(_leer_r2())


def guardar(tabla):
    """Escribe la tabla ENTERA en R2. True si quedó guardada. No lanza."""
    import data

    if not data.secrets_disponibles():
        return False
    try:
        data.get_s3_cliente().put_object(
            Bucket=st.secrets["R2_BUCKET"], Key=CLAVE_R2,
            Body=json.dumps(normalizar(tabla), ensure_ascii=False, sort_keys=True).encode("utf-8"),
            ContentType="application/json")
    except Exception:
        return False
    _leer_r2.clear()
    return True


def poner(cod, pct):
    """Pone (o quita, con None) la merma esperada de un insumo y guarda.
    True si quedó guardada."""
    t = con(leer(), cod, pct)
    return t is not None and guardar(t)
