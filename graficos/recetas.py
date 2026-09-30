"""
graficos.recetas — dashboard ÚNICO de Recetas (platos + recetas base).

Una sola página con las vistas que hasta el 2026-09-04 vivían repartidas en
dos destinos que un chip alternaba (Receta base / Receta venta). A pedido:
«quiero que las visualizaciones de estos toggles figuren todas juntas».

    Costo Carta (cartacosteada.parquet)   Carta costeada, con la receta del
                                          producto elegido al costado
    Costo Recetas Base                    lo que usan las ventas de cada
      (recetabase.parquet +               receta base, lo producido y su
       ordenesproduccion.parquet)         costo por unidad en el tiempo
    Revisar                               los cortes que se porcionan y
                                          ninguna receta usa, y los que las
                                          recetas piden y casi no se porcionan
    Nuevo Costeo                          el formulario (`formulario_receta.py`)
    Platos (recetaventa.parquet)          Tabla (oculta)
    Recetas base                          Tabla (oculta)

LOS NOMBRES Y EL ORDEN DEL RAIL (2026-09-30, a pedido): «Costo Carta» (antes
«Carta»), «Costo Recetas Base» (antes «Ranking · base»), «Revisar» y «Nuevo
Costeo» (antes «Nueva»), en ese orden. Los ids de las vistas —lo que viaja
en `?vista=`— no cambiaron, salvo el del ranking, que ya no es un ranking
(regla #576).

«Composición del plato» y «Costeo Receta Venta» se quitaron el 2026-09-28
(regla #556): la tabla de Composición era la Carta costeada filtrada a los
platos con receta, con los mismos números al céntimo, y su receta, su
simulador y su dona/Sankey se abren ahora con un clic en la Carta; Costeo
sumaba ese mismo costo sin descartar los platos inactivos.

Y el mismo día, más tarde, otras cuatro (regla #559): «Ingredientes clave»,
«Insumos clave · recetas base» y los dos «Panorama de compras». Medían la
CARTA y no lo vendido —Ingredientes sumaba el costo POR PORCIÓN de cada
ingrediente en los platos activos: su primer puesto, un whisky de S/ 265
«en 1 plato», se pidió una vez en 90 días— y el Panorama sólo reconocía un
insumo si la receta lo nombraba tal cual (el lomo fino, que llega al plato
por un porcionamiento, le salía «sin vincular»). Lo contesta bien
Movimientos › «Consumo según recetas» (regla #558), que baja cada venta
hasta el insumo de compra; lo único propio del Panorama —lo comprado que
ninguna receta explica— se mudó ahí. En su lugar entró «Revisar recetas»
(`graficos/recetas_revisar.py`): lo que se arregla editando una receta.

POR QUÉ ERAN DOS Y AHORA SON UNA. La separación se justificaba con una
medición equivocada: los docstrings de `recetabase.py`/`recetas_comun.py` y
la memoria de proyecto afirmaban «0% overlap, son dos catálogos
independientes» — pero eso se midió contra `recetabase.COD RB`, que es el
ID INTERNO de la receta base (5 dígitos, `00002`), no su código de
producto. La clave real es **`recetaventa.COD INS` ↔
`recetabase.COD PROD RB`** (7 dígitos, mismo espacio de numeración que
`compras.COD_PRODUCTO`): 401 códigos cruzan y los 401 NOMBRES coinciden
exacto en los dos lados (`INS RV` == `RB NOMBRE`, cero discrepancias).
Son 1.003 de 2.599 filas de recetaventa, en 334 de 828 platos. O sea que
una receta base no es la HERMANA de una receta de venta: es una PIEZA de
adentro (y con profundidad — 630 filas de recetabase apuntan a su vez a
otra receta base). Medido contra R2 real el 2026-09-04, ver
`arquitectura.md` regla #303. Ese árbol lo recorre hoy
`consumo_recetas.py` (regla #558).

Desde el 2026-09-26 la pila suma, antes de las de platos, «Carta costeada»:
la carta ENTERA del POS (también lo que no tiene receta: directos, sin
enlace y combos) con su % de costo, sobre un TERCER parquet,
`cartacosteada.parquet`, que carga la sección misma. Vive en
`graficos/carta_costeada.py`; regla #548. Desde el 2026-09-28 lee además
lo vendido por producto (`data.venta_por_producto_dia`, de ventas.parquet),
también sólo cuando se llega a la vista.

«Costo Recetas Base» (2026-09-30, regla #576) reemplazó al «Ranking de
recetas base», un gráfico de barras con el costo POR LOTE de cada receta del
catálogo («me da muy poca información»): cruza lo que usaron las ventas de
cada receta —también adentro de otra receta base— con las órdenes de
producción que la produjeron, y muestra cómo evolucionó su costo por unidad
según esas órdenes. Vive en `graficos/recetas_base_costo.py`; lee además
`ordenesproduccion.parquet` (regla #575) y el primer nivel de las ventas.

DOS PARQUETS EN UNA PÁGINA. `app.py` carga UNO por reporte y lo pasa como
`df_f`; el segundo se carga acá con `data.cargar`, el mismo patrón que usa
`graficos/movimientos.py` con salidas.parquet. `df_f` es el de PLATOS (el
reporte «Recetas» apunta a recetaventa.parquet).

Las dos Tablas NO se dibujan igual, y no es un descuido:
  · la de platos va por `tabla_cb`, el callback que inyecta app.py — sabe
    de vista móvil, chips genéricos y aviso de columnas duplicadas;
  · la de recetas base llama a `renderizar_aggrid_desktop` directo, porque
    `tabla_cb` recorta con el `cols_mostrar` del reporte ACTIVO (ver
    `app.py::_render_tabla`) y pasarle el df de recetabase reventaría con
    un KeyError. Ver `_tabla_recetabase` abajo.

Punto de entrada público: renderizar_graficos_recetas().
"""

from functools import partial

import streamlit as st

from data import cargar as _cargar_reporte, venta_por_producto_dia
from estilos import TAM_FUENTE
from tablas import renderizar_aggrid_desktop
from graficos.base import (
    _render_rail, _resolver, pila_sin_tablas, rail_sin_tablas,
    renderizar_graficos_genericos, seccion_perezosa,
)
from graficos.carta_costeada import ARCHIVO as ARCHIVO_CARTA, render_carta_costeada
from graficos.recetas_base_costo import ARCHIVO_ORDENES, render_costo_recetas_base
from graficos.recetas_revisar import render_revisar_recetas
from formulario_receta import render_formulario_receta

# El rótulo del rail es CORTO a propósito: la franja de Vistas es
# horizontal y aplana las categorías a una sola fila (ver
# `base.py::_render_rail`), así que los items compiten por el ancho útil
# de una laptop (~1010px). El nombre largo vive en el id — que es lo que
# viaja en `?vista=` y lo que empareja con `_PILA`.
#
# El sufijo « · base» es el desambiguador: «Tabla» existe en los dos lados
# y al juntarlas quedaban dos items con el mismo nombre.
#
# Las dos «Tabla» están OCULTAS desde el 2026-09-23, con las de los demás
# reportes: `rail_sin_tablas` acá y `pila_sin_tablas` en `_PILA`, de a par
# (regla #507). Con ellas apagadas, «Platos» se queda sin ítems y se va
# entera del rail.
_RAIL_CATEGORIAS = rail_sin_tablas((
    # EL ORDEN Y LOS NOMBRES los pidió el usuario el 2026-09-30: Costo Carta,
    # Costo Recetas Base, Revisar y Nuevo Costeo — de lo que se vende a lo
    # que se arma de cero.
    #
    # «Carta costeada» (2026-09-26): la carta ENTERA del POS con su % de
    # costo, combos incluidos — lo único de la página que mira también lo
    # que no tiene receta (directos, sin enlace, combos). Lee su propio
    # parquet, `cartacosteada.parquet`; ver `graficos/carta_costeada.py`.
    # Desde el 2026-09-28 un clic en un producto abre su receta: es lo que
    # hacía «Composición del plato», que se fue con «Costeo Receta Venta»
    # (regla #556).
    ("Carta",  (("Carta costeada",                      "Costo Carta",     ":material/menu_book:"),)),
    # «Costo de recetas base» (2026-09-30, regla #576): reemplazó al Ranking
    # de recetas base. Lo usado por las ventas contra lo producido por
    # órdenes, y el costo por unidad en el tiempo; ver
    # `graficos/recetas_base_costo.py`. La Tabla cruda de recetabase sigue
    # en esta categoría, oculta con las demás (regla #507).
    ("Recetas base", (("Costo de recetas base",         "Costo Recetas Base", ":material/timeline:"),
                      ("Tabla · recetas base",          "Tabla · base",    ":material/table_view:"))),
    # «Revisar recetas» (2026-09-28, regla #559): los cortes que la cocina
    # porciona y ninguna receta usa, y los que las recetas piden y casi no
    # se porcionan — un par como el medallón y los trozos del lomo es UNA
    # receta que apunta al corte equivocado. Ver `graficos/recetas_revisar.py`.
    ("Revisar", (("Revisar recetas",                    "Revisar",         ":material/fact_check:"),)),
    # "Nueva receta" es una VISTA del reporte desde el 2026-09-22 — hasta ese
    # día era un reporte hermano (tool: True) que el chip Recetas/+ Nueva
    # `_chip_fuente` alternaba con éste. Se bajó a vista propia a pedido
    # («deseo que figure como una vista de mi reporte de recetas»); acá se
    # dibuja como cualquiera de las demás, con su `st.container(border=True)`
    # (tarjeta blanca) y el proceso completo pensado para caber en una sola
    # pantalla de laptop — ver `formulario_receta.py::render_formulario_receta`.
    # Desde el 2026-09-30 el rail la llama «Nuevo Costeo» y va última.
    ("Nueva",  (("Nueva receta",                        "Nuevo Costeo",    ":material/add_circle:"),)),
    ("Platos", (("Tabla · platos",                     "Tabla",           ":material/table_rows:"),)),
))

# ORDEN DE LA PILA — y el apareo sección ↔ vista del rail, en la MISMA
# tupla (el porqué, en `graficos/compras/__init__.py::_PILA`).
#
# El orden del rail (pedido el 2026-09-30): la carta, sus recetas base, lo
# que hay que revisar y, al final, el formulario para costear algo nuevo.
# Las dos Tablas, ocultas, al pie.
_PILA = pila_sin_tablas((
    ("rec_sec_carta",        "Carta costeada"),
    ("rec_sec_costo_rb",     "Costo de recetas base"),
    ("rec_sec_revisar",      "Revisar recetas"),
    ("rec_sec_nueva",        "Nueva receta"),
    ("rec_sec_tabla_rv",     "Tabla · platos"),
    ("rec_sec_tabla_rb",     "Tabla · recetas base"),
))


def _tabla_recetabase(df_rb):
    """La Tabla del parquet SECUNDARIO, sin pasar por `tabla_cb`.

    `app.py::_render_tabla` recorta con `_df[cols_mostrar]`, y `cols_mostrar`
    son las columnas del reporte ACTIVO (platos). Pasarle el df de recetas
    base por ahí lanzaría KeyError con las 25 columnas de recetabase.parquet.

    Reproduce lo que hacía el reporte «Receta Base» antes de la fusión: sin
    `columnas` ni `columnas_iniciales` en su cfg, `sugeridas` terminaba
    siendo TODAS las columnas en orden — o sea `cols_visibles=None`, que es
    justo el default de `renderizar_aggrid_desktop`."""
    cols = list(df_rb.columns)
    font_px = TAM_FUENTE.get(st.session_state.get("tabla_tam"), 14)
    renderizar_aggrid_desktop(df_rb[cols], cols, "Receta Base", font_px)


# ─── Punto de entrada público ───────────────────────────────────────────────
def renderizar_graficos_recetas(df_f, nombre_reporte, df_full=None, tabla_cb=None):
    """Dashboard de Recetas. `df_f` es recetaventa.parquet (PLATOS); las
    recetas base se cargan acá adentro. `df_full` se ignora (catálogo sin
    fecha).

    `tabla_cb`: callback que arma la Tabla de platos (inyectado por app.py),
    llamado con 1 argumento. La de recetas base va por `_tabla_recetabase`,
    ver el docstring del módulo."""
    # ── ¿Es de verdad recetaventa.parquet? ────────────────────────────────
    # Sin la columna del plato no hay nada de esta página que se pueda
    # dibujar (el modo demo, sin secrets, trae otra forma): el explorador
    # genérico, como hasta ahora.
    #
    # Si alguna vez se vuelve a agrupar por INGREDIENTE: es `INS RV`, no
    # `ITEM RV`. Los dos existen y el segundo PARECE el bueno por el nombre,
    # pero es el NÚMERO DE LÍNEA dentro de la receta ('001', '002'…). Así se
    # agrupó «Ingredientes clave» hasta el 2026-09-06, por posición en la
    # receta, y se veía como un eje de rótulos 2, 4, 6… (regla #325).
    col_plato = _resolver(df_f, ["Nomb Plato", "Nombre Plato", "PLATO", "Plato"])
    if not col_plato:
        st.warning(
            "No se reconocieron las columnas de Receta Venta (se buscó "
            "«Nomb Plato»). Mostrando explorador genérico."
        )
        renderizar_graficos_genericos(df_f, nombre_reporte)
        return

    # ── RECETAS BASE (recetabase.parquet, cargado acá) ───────────────────
    # Defensivo: si el parquet no está, sus secciones avisan y el resto de la
    # página sigue funcionando. Lo que cada sección lee de él lo revisa ella.
    df_rb = _cargar_reporte("recetabase.parquet")
    if df_rb is None or df_rb.empty:
        df_rb = None

    # El rail MARCA en cuál sección estás y scrollea; no elige contenido.
    _render_rail(_RAIL_CATEGORIAS, "rec_graf_tipo", btn_prefix="rec_rail_btn_",
                 secciones=_PILA)

    # ── LA PILA, PEREZOSA ─────────────────────────────────────────────────
    # Cada sección con su PROPIA key de tarjeta: apiladas, compartir key es
    # una excepción de Streamlit.
    def _dib_nueva():
        with st.container(border=True, key="rec_card_nueva"):
            render_formulario_receta()

    def _dib_carta():
        # Su parquet —y lo vendido por producto, de ventas.parquet— se
        # cargan ACÁ, dentro de la sección, y no arriba con los otros dos:
        # la pila es perezosa y así sólo los baja quien llega a la vista
        # (mismo patrón que Porcionamientos en Movimientos). Su tarjeta
        # —la carta y, al costado, el producto elegido, con sus recetas
        # base— la arma `render_carta_costeada`.
        # Lo vendido va como FUNCIÓN y no cargado: la vista lo pide sólo
        # si algo en pantalla lo usa (regla #573).
        # Los porcionamientos también (regla #574): los lee el panel sólo si
        # el producto elegido tiene receta.
        render_carta_costeada(
            _cargar_reporte(ARCHIVO_CARTA), df_rv=df_f,
            ventas=venta_por_producto_dia, df_rb=df_rb,
            porcionamientos=partial(_cargar_reporte, "porcionamientos.parquet"))

    def _dib_revisar():
        # Lo que lee (porcionamientos, el primer nivel de las ventas, el
        # maestro, la carta y las salidas) lo carga la sección misma, por lo
        # mismo que la Carta.
        render_revisar_recetas(df_f, df_rb)

    def _dib_tabla_rv():
        with st.container(border=True, key="rec_card_tabla_rv"):
            if tabla_cb is not None:
                tabla_cb(df_f)
            else:
                st.info("La tabla no está disponible en este contexto.")

    def _sin_recetabase():
        st.info("No se pudieron cargar las recetas base "
                "(recetabase.parquet): esta sección queda vacía.")

    def _dib_costo_rb():
        # Las órdenes de producción van como FUNCIÓN, como las ventas de la
        # Carta (regla #573): se leen sólo cuando la sección se construye.
        # Lo usado por las ventas lo pide la vista misma. Regla #576.
        render_costo_recetas_base(df_rb, partial(_cargar_reporte, ARCHIVO_ORDENES))

    def _dib_tabla_rb():
        with st.container(border=True, key="rec_card_tabla_rb"):
            if df_rb is None:
                _sin_recetabase()
            else:
                _tabla_recetabase(df_rb)

    _DIBUJANTES = {
        "rec_sec_carta":        _dib_carta,
        "rec_sec_costo_rb":     _dib_costo_rb,
        "rec_sec_revisar":      _dib_revisar,
        "rec_sec_nueva":        _dib_nueva,
        "rec_sec_tabla_rv":     _dib_tabla_rv,
        "rec_sec_tabla_rb":     _dib_tabla_rb,
    }

    # El contenedor con la key va AFUERA del fragment a propósito: es el que
    # observan el scrollspy y la precarga, y tiene que sobrevivir a que el
    # fragment de adentro se re-dibuje.
    for _i, (_clave, _vista) in enumerate(_PILA):
        with st.container(key=_clave):
            seccion_perezosa(_clave, _vista, _DIBUJANTES[_clave],
                             activa_de_entrada=(_i == 0))
