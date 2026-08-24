"""
graficos.periodo — el rango de fecha POR VISTA.

Hermano chico de `estado_rango.py`, que es el dueño único del rango GLOBAL
(el de la franja superior). Este módulo no le disputa nada: la franja sigue
mandando, y una vista que no lo importe se comporta exactamente igual que
antes. Lo que agrega es la posibilidad de que una vista diga "yo miro otra
ventana" sin inventarse su propia lógica.

POR QUÉ EXISTE (2026-08-18)
    Un rango global responde bien "quién pesa más ACÁ", que es la pregunta
    de un ranking. No responde "cómo viene esto", que es la pregunta de una
    evolución: 15 días de franja dan UN punto, y un punto no es una curva.
    Tres vistas ya habían chocado con eso y cada una lo resolvió sola:

      · `compras/proveedor.py` conmutaba al histórico completo cuando el
        rango daba menos de 2 períodos. Sin control del usuario: se
        enteraba por un caption DESPUÉS ("· todo el histórico").
      · `ajuste/` partió el rango de la franja POR CATEGORÍA del rail
        (`categoria_rango_ajuste`): Cascada quiere un mes, Evolución un
        año, y compartir una sola clave hacía que se pisaran.
      · `ventas_horario.py` se armó su propia lista de períodos con su
        propio `date_input`.

    Tres implementaciones del mismo concepto, ninguna reusable. Esto es esa
    idea una sola vez, explícita y en manos del usuario.

EL ANCLA SON LOS DATOS, NO EL CALENDARIO
    `estado_rango.atajos_rango` ancla sus atajos a `hoy`, y hace bien: ahí
    el usuario elige fechas de calendario y "Este mes" ES este mes. Acá
    elige una VENTANA relativa, y anclarla a `hoy` sería un error caro: los
    parquets se regeneran de madrugada y los documentos entran con retraso,
    así que "últimos 12 meses" terminaría en un tramo final vacío que se lee
    como una caída del negocio. El ancla es el ÚLTIMO DÍA CON DATOS.

CONTRATO
    `ventana()` y `recortar()` son puras y las fija `test_graficos.py`.
    `selector()` es lo único que toca Streamlit.
"""

import pandas as pd
import streamlit as st

# La opción que NO recorta: la vista hereda lo que fije la franja de arriba.
# Se llama igual que el modo "Rango" de la franja a propósito — es el mismo
# rango, visto desde adentro de una tarjeta.
HEREDA = "Rango"

OPCIONES = (HEREDA, "3m", "12m", "24m", "Todo")

_MESES = {"3m": 3, "12m": 12, "24m": 24}

AYUDA = ("Ventana propia de esta tarjeta, contada desde el último día con "
         "datos. La primera opción usa la fecha de la franja de arriba.")


def ventana(opcion, ancla, minimo=None):
    """`(ini, fin)` inclusive de `opcion`, o `None` si la vista hereda.

    · `ancla`: último día CON DATOS (no `hoy` — ver el docstring del módulo).
    · `minimo`: primer día con datos. Acota el arranque para que "24m" sobre
      un histórico de 8 meses no devuelva un tramo que no existe; sin él, un
      eje de categorías dibujaría los meses vacíos.

    Devuelve Timestamps normalizados (medianoche): la comparación de más
    abajo también normaliza, así una fecha con hora no se cae del borde
    superior de la ventana.
    """
    if opcion == HEREDA or ancla is None:
        return None
    fin = pd.Timestamp(ancla).normalize()
    if pd.isna(fin):
        return None
    piso = None if minimo is None else pd.Timestamp(minimo).normalize()
    if opcion == "Todo":
        return (piso if piso is not None and not pd.isna(piso) else fin, fin)
    meses = _MESES.get(opcion)
    if meses is None:
        return None
    # +1 día: una ventana de 12 meses que termina el 15-ago arranca el 16-ago
    # del año pasado. Sin el día, el 15 entra dos veces si alguien compara
    # dos ventanas consecutivas.
    ini = (fin - pd.DateOffset(months=meses) + pd.Timedelta(days=1)).normalize()
    if piso is not None and not pd.isna(piso) and piso > ini:
        ini = piso
    return (ini, fin)


def recortar(df, col_fecha, opcion, ancla=None):
    """`df` recortado a la ventana de `opcion`. Con `HEREDA` lo devuelve igual.

    El ancla sale del PROPIO df si no se pasa una — o sea, del último día con
    datos de lo que la vista tenga entre manos. Pasarla explícita sirve para
    que dos tarjetas de la misma pantalla midan contra el mismo día.
    """
    if df is None or getattr(df, "empty", True):
        return df
    if not col_fecha or col_fecha not in df.columns:
        return df
    if opcion == HEREDA:
        return df
    f = pd.to_datetime(df[col_fecha], errors="coerce").dt.normalize()
    v = ventana(opcion, f.max() if ancla is None else ancla, minimo=f.min())
    if v is None:
        return df
    ini, fin = v
    return df[(f >= ini) & (f <= fin)]


def etiqueta(opcion):
    """Texto para el título de la tarjeta. Vacío cuando hereda: ahí el rango
    ya lo dice la píldora de la franja y repetirlo sería ruido."""
    if opcion == HEREDA:
        return ""
    if opcion == "Todo":
        return "todo el histórico"
    meses = _MESES.get(opcion)
    return f"últimos {meses} meses" if meses else ""


def selector(clave, default="12m", opciones=OPCIONES, label="Período",
             format_func=None, widget="pills"):
    """La ventana de ESTA tarjeta. Devuelve la opción viva.

    `widget` elige la FORMA, no el contrato — las dos escriben la misma clave
    de `session_state` y devuelven la misma cadena de `opciones`:

      · `"pills"` (default): fila de pastillas, las 5 opciones a la vista.
      · `"lista"`: desplegable. Ocupa una línea en vez de una fila, a costa
        de esconder las opciones hasta el clic. Pedido 2026-08-23 para la
        tarjeta de Evolución de Compras › Proveedor, donde el selector
        comparte renglón con la granularidad.

    Deseleccionar (clic en la pill activa) devuelve `None` en Streamlit; acá
    cae al default en vez de dejar la vista sin ventana — "ninguna" no es un
    estado que signifique algo para un eje de tiempo. El desplegable no tiene
    ese estado (no se puede "des-elegir" un `st.selectbox`), pero el `or`
    igual cubre a los dos.

    `format_func` cambia solo el TEXTO que se ve, nunca el valor que devuelve
    ni el de `opciones` — así una vista puede mostrar `HEREDA` ("Rango") con
    otra etiqueta sin tocar las comparaciones (`opcion == HEREDA`) que
    dependen de la cadena literal.
    """
    ops = list(opciones)
    if widget == "lista":
        # `index` sólo fija el arranque: si `clave` ya está en session_state
        # (rerun, o una sesión que venía de las pills), Streamlit usa ese
        # valor y lo ignora. Los dos widgets comparten el dominio de valores,
        # así que el cambio de forma no invalida una sesión abierta.
        idx = ops.index(default) if default in ops else 0
        return st.selectbox(label, ops, index=idx, key=clave,
                            label_visibility="collapsed", help=AYUDA,
                            format_func=format_func) or default
    return st.pills(label, ops, default=default, key=clave,
                    label_visibility="collapsed", help=AYUDA,
                    format_func=format_func) or default
