"""graficos.costos — dashboard del reporte «Costos».

REPORTE NUEVO EL 2026-10-09, a pedido, sobre un boceto con datos reales
(https://claude.ai/artifact/3NYnyS7axe6u5woDiyiZBD) y la planilla con la
que el usuario ya llevaba el costo a mano. Una vista: «Costo de ventas», el
estado mensual de inventario inicial + compras − inventario final, las
salidas que no se vendieron, el consumo operativo y el consumo carta, y la
comparación del consumo carta contra el costo que dice el POS.

Va como reporte propio y no como vista de otro porque cruza CUATRO fuentes y
ninguna es su dueña: los cierres de inventario (el `archivo` del reporte),
las compras, las notas de salida y la venta por grupo de carta. La cuenta
vive en `costo_ventas.py` (pura, con su test); este módulo la arma, la
cachea y la entrega.

LA TABLA ES UNA PIEZA PROPIA (`st.components.v2`, como el panel de fecha de
la regla #616): HTML, CSS y JavaScript sin iframe, en `costos_tabla.js` y
`costos_tabla.css`. Todo lo que se elige ahí —familias, Eventos y Venta
interna, qué salidas restar, qué fila abrir— lo resuelve el navegador: los
datos son pocos (meses × filas × cuatro familias) y viajan enteros, así que
nada de eso recalcula la página.

SIN PILA, como Documentos SUNAT (regla #577): una tarjeta, `secciones=()`.
La tarjeta no lleva techo de alto (`estilos/_80_cards.py`): al abrir una
fila la tabla crece, y con techo la tarjeta sacaría barra propia (#382).

Regla #622.
"""

from pathlib import Path

import streamlit as st

import costo_ventas
import data
import definicion_venta
from graficos.base import (
    _render_rail, pila_sin_tablas, publicar_contexto_ia, rail_sin_tablas,
)

# Una sola vista. El rail se declara igual —con `rail_sin_tablas`, como
# todos (regla #507)— porque de él salen el panel del reporte en la columna
# (`graficos/__init__.py::_RAILS`, regla #568) y el rótulo de la franja.
_COSTOS_RAIL_CATEGORIAS = rail_sin_tablas((
    ("Costos", (("Costo de ventas", "Costo de Ventas", ":material/calculate:"),)),
))

# Vacía y no ausente: `_render_rail` distingue `secciones=()` («destino
# aparte») de `secciones=None`. Ver `graficos/sunat_reporte.py`.
_PILA = pila_sin_tablas(())

_ARCHIVOS = ("compras.parquet", "salidas.parquet", "ventas.parquet")

_AQUI = Path(__file__).parent
_TABLA = st.components.v2.component(
    "costos_tabla",
    css=(_AQUI / "costos_tabla.css").read_text(encoding="utf-8"),
    js=(_AQUI / "costos_tabla.js").read_text(encoding="utf-8"),
)


@st.cache_data(ttl=3600, show_spinner=False)
def _datos(_ajuste, sellos, version):
    """`costo_ventas.armar` sobre los cuatro parquets. Si falta uno, LANZA:
    una tabla con la venta en cero no se cachea.

    `_ajuste` no entra en la clave (el guion bajo): lo identifica su sello,
    que va en `sellos` junto con los de los otros tres, y `version` lleva
    las de la cuenta y la definición de venta. Sólo en memoria: lo pesado
    —cada parquet— ya está en la caché de disco de `data.py`."""
    compras = data.cargar("compras.parquet")
    salidas = data.cargar("salidas.parquet")
    ventas = data.venta_por_grupo_dia()
    faltan = [n for n, d in (("compras", compras), ("salidas", salidas),
                             ("ventas", ventas)) if d is None]
    if faltan:
        raise RuntimeError("no se pudo leer: " + ", ".join(faltan))
    return costo_ventas.armar(_ajuste, compras, salidas, ventas)


def renderizar_graficos_costos(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard «Costos»: el rail de una vista + la tabla del costo de ventas.

    `df_f` son los cierres de inventario (`ajusteinventario.parquet`, el
    `archivo` del reporte), sin filtro de fecha: el reporte no tiene. El
    resto lo trae `_datos`. `tabla_cb` se acepta por la firma única del
    dispatcher y no se usa: el reporte no tiene vista «Tabla»."""
    _render_rail(_COSTOS_RAIL_CATEGORIAS, "costos_graf_tipo", secciones=_PILA)
    ajuste = df_full if df_full is not None else df_f
    sellos = (data.sello_datos("ajusteinventario.parquet"),
              *(data.sello_datos(a) for a in _ARCHIVOS))
    version = (costo_ventas.VERSION, definicion_venta.VERSION)
    with st.container(border=True, key="ajuste_graf_card_izq_costos"):
        try:
            # La primera vez de cada versión de los parquets baja la venta
            # entera para agruparla (unos 15 s); después sale de la caché.
            with st.spinner("Calculando el costo de ventas…"):
                datos = _datos(ajuste, sellos, version)
        except Exception as e:
            st.warning(f"No se pudo armar el costo de ventas ({e}). "
                       "Reintentá en unos segundos.")
            return
        if not datos["meses"]:
            st.info("Todavía no hay dos cierres de inventario seguidos desde "
                    "octubre 2025: sin inventario inicial y final no hay "
                    "consumo que calcular.")
            return
        # El asistente responde sobre lo que suma la tabla, no sobre los
        # cierres sueltos que llegan en `df_f`.
        publicar_contexto_ia("Costos", costo_ventas.tabla_larga(datos))
        _TABLA(key="costos_tabla", data=datos, width="stretch")
