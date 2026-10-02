"""graficos.sunat_reporte — dashboard del reporte «Documentos SUNAT».

REPORTE PROPIO DESDE EL 2026-09-30, a pedido: «que documentos sunat se vea
en otra botonera del rail, como si fuese un reporte más, ya no dentro de
compras». Hasta ese día era una vista del rail de Compras, y ya era la
única que no vivía en su pila: un DESTINO APARTE, con otra fuente (el SIRE,
no el parquet), sin los chips de Familia/Subfamilia y con el calendario
entero dentro de su tarjeta. Moverla fue reconocer lo que ya era.

Este módulo es sólo el DESPACHO: el rail de una vista y el contenedor. El
drill no se movió — sigue en `graficos/compras/documentos_sunat.py`, con sus
4.000 líneas, sus pruebas y el CSS que cuelga de sus keys (`sunat_card_*`,
`sunat_conv_*`). El envoltorio conserva la key `compras_sunat_drill_wrap`
por lo mismo: de ella cuelgan la regla que esconde los chips y la franja
vacía de la fecha (`estilos/_40_ajuste_franja.py`) y la que le quita el
jalón viejo a la primera tarjeta (`estilos/_20_compras_rail.py`).

Lo que SÍ cambió de dueño:

  · **El rango es del reporte.** Antes la tarjeta dibujaba el calendario
    sobre la clave canónica de Compras; ahora sobre la suya
    (`clave_rango("Documentos SUNAT")`). Mover la fecha acá ya no toca nada
    de Compras.
  · **Los topes del calendario** (`bounds_fecha`) los pide `app.py` para
    este reporte entero, no «cuando la vista activa de Compras es SUNAT».
  · **Sin pila**: `_PILA` vacía y `secciones=()`. `_render_rail` trata la
    vista como el destino aparte que siempre fue — marca la vista en la
    columna, la escribe en la franja y no enciende el encaje (regla #533).

Regla #577.
"""

import datetime
import zoneinfo

import pandas as pd
import streamlit as st

from utils import _norm
from graficos.base import (
    _render_rail, _resolver, pila_sin_tablas, rail_sin_tablas,
)


# Una sola vista. El rail se declara igual —con `rail_sin_tablas`, como
# todos (regla #507)— porque de él salen el panel del reporte en la columna
# (`graficos/__init__.py::_RAILS`, regla #568) y el rótulo de la vista en la
# franja. Ícono = el del reporte en `data.py::REPORTES`.
_SUNAT_RAIL_CATEGORIAS = rail_sin_tablas((
    ("SUNAT", (("Documentos SUNAT", "Documentos SUNAT", ":material/fact_check:"),)),
))

# SIN PILA, a propósito: la página es UNA tarjeta alta con su propia tabla,
# no secciones que se leen bajando. Vacía y no ausente porque `_render_rail`
# distingue `secciones=()` («destino aparte»: dibuja la lista de vistas y el
# temporizador que la marca) de `secciones=None` (nada de eso).
_PILA = pila_sin_tablas(())


def bounds_fecha():
    """`(min, max)` del calendario de este reporte.

    La consulta `app.py` antes de sembrar/recortar el rango: esta tarjeta no
    filtra el parquet de Compras, le pregunta al SIRE, así que los topes del
    parquet no le sirven. Los dos extremos salen de sitios distintos:

      · el PISO, de `sunat.limites_registro()` — antes de la primera
        factura del registro no hay nada que pedir;
      · el TECHO, de HOY — no del tope del parquet. Un techo puesto en
        "hasta donde llegó el último sync" siempre atrasa lo que tarde en
        correr el sync, así que el día de HOY nunca se podría elegir. Fue un
        bug (2026-08-24): con comprobantes del 24 ya visibles en SUNAT, el
        calendario cortaba en el 21. `comprobantes_rango` sabe pedir en vivo
        los días que el parquet todavía no trajo. Regla #197.

    Vivía en `graficos/compras/__init__.py` como `bounds_fecha_de_la_vista`,
    condicionada a que la vista activa de Compras fuera ésta.
    """
    import sunat

    # HOY en Lima, no en UTC: Streamlit Cloud corre en UTC y a partir de
    # las 19:00 de Perú ya está en el día siguiente — el calendario
    # ofrecería un mañana que SUNAT todavía no puede tener.
    hoy = datetime.datetime.now(zoneinfo.ZoneInfo("America/Lima")).date()
    limites = sunat.limites_registro()
    return (limites[0] if limites else None), hoy


def _kpi_de_la_vista():
    """`(kpis, estados)` para el punto de la vista en la columna.

    Es el texto que tenía la vista cuando vivía en Compras, pero sin el lado
    del sistema calculado desde el parquet: los dos conteos y lo que no
    cuadra los publica la propia tarjeta en `_cp_docs_cruce` cuando dibuja
    (`documentos_sunat.py::_publicar_conteos`), así que llegan un rerun tarde y
    faltan hasta la primera vez que se abre. Mejor sin número que con uno
    inventado. Ámbar si hay algo que revisar: es lo único accionable acá.
    """
    _cruce = st.session_state.get("_cp_docs_cruce") or {}
    if _cruce.get("sunat") is None:
        return None, None
    _fmt = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
    txt = (f"**Documentos:** {_fmt(_cruce.get('sistema') or 0)} en el sistema"
           f" · {_fmt(_cruce['sunat'])} en SUNAT")
    estados = None
    if _cruce.get("revisar"):
        txt += f" · {_cruce['revisar']} con diferencias a revisar"
        estados = {"Documentos SUNAT": "warning"}
    return {"Documentos SUNAT": txt}, estados


def renderizar_graficos_sunat(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard «Documentos SUNAT»: el rail de una vista + el drill.

    `tabla_cb` se acepta por la firma única del dispatcher y no se usa: el
    reporte no tiene vista «Tabla» — su tabla ES la de comprobantes.

    El drill recibe `df_full` y no `df_f`: el cruce contra el parquet ya
    acota por su rango (`_parquet_agrupado_por_documento`), y antes de eso
    no puede venir recortado por nada más — en Compras eso eran los chips
    de Familia, y un documento con todas sus líneas en una familia no
    elegida salía «Solo SUNAT» siendo falso (regla #301).
    """
    col_fecha = _resolver(df_f, ["Fecha_documento", "Fecha documento",
                                 "Fecha_registro", "Fecha registro", "FECHA"])
    if not col_fecha:
        # El mismo respaldo que usa Compras: la primera columna de fecha.
        for _c in df_f.columns:
            if (pd.api.types.is_datetime64_any_dtype(df_f[_c])
                    or "fecha" in _norm(str(_c))):
                col_fecha = _c
                break

    kpis, estados = _kpi_de_la_vista()
    _render_rail(_SUNAT_RAIL_CATEGORIAS, "sunat_graf_tipo",
                 secciones=_PILA, estados=estados, kpis=kpis)

    # Import local a propósito: arrastra `sunat.py` y, con él, `requests` —
    # no hay por qué pagarlo al importar `graficos` si nadie abre el reporte.
    from graficos.compras.documentos_sunat import renderizar_documentos_sunat
    with st.container(key="compras_sunat_drill_wrap"):
        renderizar_documentos_sunat(
            df_full if df_full is not None else df_f, col_fecha)
