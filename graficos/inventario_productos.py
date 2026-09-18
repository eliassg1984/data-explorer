"""
graficos.inventario_productos — la sección «Productos» de Inventario
Valorizado: el listado ENTERO de productos como tabla, con las áreas de cada
uno desplegables en su fila.

Reemplaza a «Buscar producto» (2026-09-17, a pedido). Aquélla pedía elegir
UN producto o UN grupo antes de mostrar nada, y contestaba con una barra por
producto. El pedido fue una tabla con el listado entero, las columnas en el
orden Código · Familia · Subfamilia · Nombre · Unidad kardex · Precio
unitario · Cantidad · Valorizado total, filtros de familia, subfamilia y
producto, y «mediante un clic o despliegue en cada ítem, ver el área en
donde existe». Ver `arquitectura.md` regla #466.

EL DESPLIEGUE ES DE AG GRID COMMUNITY, NO EL MASTER/DETAIL. Master/detail,
tree data y el agrupado de filas son Enterprise, y Enterprise está
descartado (es de pago). Acá hay filas planas de dos tipos en el MISMO
rowData:

  · una por PRODUCTO (`__tipo = "p"`), y
  · una por ÁREA donde ese producto tiene stock (`__tipo = "a"`, con
    `__padre` = el `__id` de su producto).

Las de área nacen ocultas por un filtro EXTERNO que sólo las deja pasar si
su producto está abierto; el clic en el producto lo abre o lo cierra y le
pide a la grilla que vuelva a filtrar. Todo pasa en el navegador: desplegar
no cuesta un rerun, y por eso la grilla va con `update_on=[]` — con el
default de st_aggrid, `onFilterChanged()` le avisaría a Python y cada clic
rehacería la sección.

Y un `postSortRows` que vuelve a colgar cada área debajo de su producto
después de ordenar: sin él, ordenar por «Valorizado total» repartiría las
filas de área entre los productos. AG Grid lo llama SIEMPRE, haya orden
activo o no (verificado en el bundle de st_aggrid 1.2.1, AG Grid 34.3.1:
el sort stage lo invoca después de armar `childrenAfterSort`, en las dos
ramas).

LOS FILTROS SON DE STREAMLIT, no de la grilla: el filtro de lista de AG Grid
(los valores con casillas) también es Enterprise, y el de texto obliga a
escribir la familia a mano. Van en la fila del título y el recorte lo hace
Python antes de armar las filas.
"""

import unicodedata
import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, AJUSTE_NEG_TEXTO, GRIS_TEXTO_MEDIO,
    LAVANDA_CHIP, LAVANDA_FILA, LAVANDA_SELECCION,
)
from graficos import alturas
from graficos.base import _es_movil
# El look de las otras tres tablas del dashboard (regla #404): mismo alto de
# fila, misma cabecera, mismo CSS. Una tabla ancha con otro idioma de grilla
# debajo de tres que comparten uno se lee como otro reporte.
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CROMO_GRID_RANK,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
# La ÚNICA del repo (regla #379): familia y subfamilia se ESCRIBEN como
# nombre propio en todo el dashboard, y acá también.
from graficos.compras._etiquetas_proveedor import nombre_propio

# Cuántas filas se ven antes de que la GRILLA scrollee por dentro. La
# tarjeta no scrollea (sólo las tablas): 14 filas + cabecera + TOTAL son
# 399px, y con la fila del título la tarjeta entra en el presupuesto de
# `alturas.PRESUPUESTO`. Fijo y no `min(n, ...)`: con un filtro que deja
# tres productos la tarjeta no salta de tamaño, y al desplegar áreas la
# grilla no tiene que crecer (no podría: el alto lo fija Python).
FILAS_LISTADO = 14

_EPS = 1e-9
_VACIOS = ("", "nan", "none", "nat", "<na>", "null")

_K_FAMILIA = "inv_prod_familia"
_K_SUBFAMILIA = "inv_prod_subfamilia"
_K_BUSCAR = "inv_prod_buscar"
_K_SIN_STOCK = "inv_prod_sin_stock"


# ═══════════════════════════════════════════════════════════════════════
# DATOS — puras, sin Streamlit (las prueba `test_graficos.py`)
# ═══════════════════════════════════════════════════════════════════════

def _texto(d, col):
    """`col` como texto limpio; "" si la columna no existe o viene vacía."""
    if not col:
        return pd.Series("", index=d.index)
    s = d[col].astype(str).str.strip()
    return s.mask(s.str.lower().isin(_VACIOS), "")


def _plano(s):
    """Minúscula y sin tildes: lo que se compara en el buscador."""
    return (unicodedata.normalize("NFKD", str(s))
            .encode("ascii", "ignore").decode().lower())


@dataclass
class Listado:
    """Lo que dibuja la tabla, ya recortado.

    `productos` va indexado por código, con `areas` = en cuántas áreas tiene
    stock. `areas` es una fila por (código, área) con stock. `sin_stock` es
    cuántos productos del recorte quedaron FUERA por no tener stock en
    ninguna área — lo que el interruptor «Incluir sin stock» agregaría."""
    productos: pd.DataFrame
    areas: pd.DataFrame
    sin_stock: int


def armar_listado(d, *, col_cod, col_prod, col_fam=None, col_subfam=None,
                  col_area=None, col_unidad=None, col_punit=None,
                  col_cant=None, col_val=None, familia=None,
                  subfamilia=None, texto="", incluir_sin_stock=False):
    """El parquet (una fila por producto × área) llevado a un PRODUCTO por
    fila, más sus áreas aparte.

    EL GRANO. Medido contra R2 el 2026-09-17: 15.379 filas, 3.874 códigos.
    Nombre, familia, subfamilia, unidad y PRECIO PROMEDIO son del producto
    —ningún código trae dos valores distintos en ninguno de los cinco—, así
    que se toman con `first`. Cantidad y valorizado son del área y se suman.
    El precio NO se recalcula como valorizado / cantidad: daría lo mismo
    donde hay stock (verificado, diferencia máxima 6e-14) y NaN donde no,
    y el kardex sí tiene precio para un producto en cero.

    «DONDE EXISTE» es donde hay stock: un área entra si su cantidad o su
    valorizado no son cero. El parquet registra cada producto en ~4 áreas
    en promedio, casi todas en cero (1.095 filas con stock de 15.379).

    SIN STOCK. 3.008 de los 3.874 productos están en cero en todas sus
    áreas. Quedan fuera salvo `incluir_sin_stock` — la regla #78 nació de
    esta misma sección mostrándolos —, y `sin_stock` dice cuántos son para
    que el interruptor lo pueda anunciar.

    Sin `col_cod`, la clave es el nombre (hay 9 nombres repetidos entre
    códigos distintos en el parquet real: sin código se fundirían)."""
    nombre = _texto(d, col_prod)
    base = pd.DataFrame({
        "codigo": _texto(d, col_cod) if col_cod else nombre,
        "familia": _texto(d, col_fam),
        "subfamilia": _texto(d, col_subfam),
        "nombre": nombre,
        "unidad": _texto(d, col_unidad),
        "precio": (pd.to_numeric(d[col_punit], errors="coerce")
                   if col_punit else np.nan),
        "cantidad": (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                     if col_cant else 0.0),
        "valorizado": (pd.to_numeric(d[col_val], errors="coerce").fillna(0)
                       if col_val else 0.0),
        "area": _texto(d, col_area),
    })
    # Los recortes de familia y subfamilia van sobre las filas: son
    # atributos del producto, así que da lo mismo que hacerlos después y
    # agrupa menos.
    if familia:
        base = base[base["familia"] == familia]
    if subfamilia:
        base = base[base["subfamilia"] == subfamilia]

    prods = base.groupby("codigo", sort=False).agg(
        familia=("familia", "first"), subfamilia=("subfamilia", "first"),
        nombre=("nombre", "first"), unidad=("unidad", "first"),
        precio=("precio", "first"), cantidad=("cantidad", "sum"),
        valorizado=("valorizado", "sum"))

    # El buscador: todas las palabras tienen que estar, en el nombre o en el
    # código, sin mirar tildes ni mayúsculas. «pollo kg» encuentra «Muslo
    # pollo x Kg»; una sola palabra suelta funciona como un «contiene».
    palabras = _plano(texto).split()
    if palabras and not prods.empty:
        pajar = [_plano(f"{n} {c}") for n, c in zip(prods["nombre"],
                                                     prods.index)]
        prods = prods[[all(p in h for p in palabras) for h in pajar]]

    activo = (base["cantidad"].abs() > _EPS) | (base["valorizado"].abs() > _EPS)
    areas = (base[activo & base["codigo"].isin(prods.index)]
             .groupby(["codigo", "area"], as_index=False, sort=False)
             .agg(cantidad=("cantidad", "sum"),
                  valorizado=("valorizado", "sum")))
    prods = prods.assign(
        areas=prods.index.map(areas.groupby("codigo").size())
        .fillna(0).astype(int))

    sin_stock = int((prods["areas"] == 0).sum())
    if not incluir_sin_stock:
        prods = prods[prods["areas"] > 0]
    # Mayor valorizado arriba, que es el orden con el que abre la columna.
    # Las áreas, igual dentro de cada producto.
    prods = prods.sort_values(["valorizado", "nombre"],
                              ascending=[False, True], kind="stable")
    areas = areas.sort_values("valorizado", ascending=False, kind="stable")
    return Listado(prods, areas.reset_index(drop=True), sin_stock)


def filas_grilla(listado):
    """El `rowData`: cada producto seguido de sus áreas, en un solo df.

    Las columnas de datos son las mismas para los dos tipos de fila, y en
    las de área van VACÍAS las que son del producto (familia, subfamilia,
    unidad, precio): se leen en la fila de arriba, y repetirlas en cada área
    convierte el despliegue en un bloque de texto igual. El nombre del área
    viaja en `nombre`, que es la columna que se lee hacia abajo."""
    p = listado.productos.reset_index()
    p["familia"] = [nombre_propio(x) if x else "" for x in p["familia"]]
    p["subfamilia"] = [nombre_propio(x) if x else "" for x in p["subfamilia"]]
    p["__tipo"] = "p"
    p["__id"] = p["codigo"]
    p["__padre"] = ""
    p["__n"] = p.pop("areas")
    p["__o"] = range(len(p))

    a = listado.areas
    a = pd.DataFrame({
        "codigo": "", "familia": "", "subfamilia": "",
        "nombre": a["area"], "unidad": "", "precio": np.nan,
        "cantidad": a["cantidad"], "valorizado": a["valorizado"],
        "__tipo": "a", "__id": a["codigo"] + "|" + a["area"],
        "__padre": a["codigo"], "__n": 0,
        "__o": a["codigo"].map(dict(zip(p["codigo"], p["__o"]))),
    })
    a = a[a["__o"].notna()]
    filas = pd.concat([p, a], ignore_index=True)
    # Producto antes que sus áreas; las áreas conservan su orden (valorizado
    # descendente) porque el sort es estable.
    filas["__t"] = (filas["__tipo"] == "a").astype(int)
    filas = filas.sort_values(["__o", "__t"], kind="stable")
    return filas.drop(columns=["__o", "__t"]).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════
# GRILLA
# ═══════════════════════════════════════════════════════════════════════

# Qué productos están abiertos. Vive en el `window` del IFRAME de la grilla
# (cada AgGrid es un iframe propio, así que no choca con nada) y muere con
# él: cambiar un filtro estrena grilla (ver la key) y todo vuelve cerrado.
_JS_ABIERTOS = "(window.__invAbiertos || {})"

_JS_FILTRO_PRESENTE = "function(){ return true; }"
_JS_FILTRO_PASA = (
    "function(node){ var d = node.data;"
    " if (!d || d.__tipo !== 'a') return true;"
    f" return !!{_JS_ABIERTOS}[d.__padre]; }}")

# Cada área vuelve debajo de su producto. `params.nodes` se reescribe EN EL
# SITIO: es el mismo array que AG Grid guarda como `childrenAfterSort`. Un
# área sin su producto en la lista (no debería pasar: el filtro externo sólo
# deja pasar las de productos abiertos, y los productos nunca se filtran) va
# al final en vez de perderse.
_JS_AREAS_BAJO_SU_PRODUCTO = """
function(params) {
    var nodes = params.nodes, prods = [], hijos = {};
    for (var i = 0; i < nodes.length; i++) {
        var d = nodes[i].data || {};
        if (d.__tipo === 'a') {
            (hijos[d.__padre] = hijos[d.__padre] || []).push(nodes[i]);
        } else {
            prods.push(nodes[i]);
        }
    }
    var k = 0;
    for (var j = 0; j < prods.length; j++) {
        nodes[k++] = prods[j];
        var id = prods[j].data && prods[j].data.__id;
        var h = hijos[id];
        if (h) {
            for (var m = 0; m < h.length; m++) nodes[k++] = h[m];
            delete hijos[id];
        }
    }
    for (var r in hijos) {
        for (var q = 0; q < hijos[r].length; q++) nodes[k++] = hijos[r][q];
    }
    nodes.length = k;
}
"""

# El clic: abre o cierra el producto. `redrawRows` y no `refreshCells`
# porque además de la flecha cambia la CLASE de la fila (`inv-fila-abierta`),
# y las clases de fila sólo se reevalúan al redibujarla. Las filas de área y
# la TOTAL no hacen nada.
_JS_CLIC = """
function(e) {
    var d = e.data;
    if (e.node.rowPinned || !d || d.__tipo !== 'p' || !(d.__n > 0)) return;
    var ab = (window.__invAbiertos = window.__invAbiertos || {});
    if (ab[d.__id]) { delete ab[d.__id]; } else { ab[d.__id] = true; }
    e.api.onFilterChanged();
    e.api.redrawRows({rowNodes: [e.node]});
}
"""

_JS_FLECHA = (
    "function(p){ var d = p.data;"
    " if (!d || d.__tipo !== 'p' || !(d.__n > 0)) return '';"
    f" return {_JS_ABIERTOS}[d.__id] ? '▾' : '▸'; }}")

# «↳ COCINA»: la flecha dice que la fila cuelga de la de arriba, la sangría
# la separa de los nombres de producto.
_JS_NOMBRE = (
    "function(p){ if (p.value == null) return '';"
    " return (p.data && p.data.__tipo === 'a') ? '↳ ' + p.value"
    " : p.value; }")
_JS_ESTILO_NOMBRE = (
    "function(p){ return (p.data && p.data.__tipo === 'a')"
    " ? {'paddingLeft': '26px'} : {}; }")

# Los montos viajan como número (para que la columna se ordene) y el formato
# lo pone el navegador. Dos decimales: en inventario hay productos de
# S/ 1.45 y el entero se los comería.
_JS_SOLES = (
    "function(p){ if (p.value == null || isNaN(p.value)) {"
    " return (p.data && p.data.__tipo === 'p') ? '–' : ''; }"
    " var v = Number(p.value);"
    " return (v < 0 ? '−' : '') + 'S/ ' + Math.abs(v).toLocaleString("
    "'es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }")
# La fila TOTAL no lleva cantidad: sumar kilos con litros no da una unidad.
_JS_CANTIDAD = (
    "function(p){ if (p.value == null || isNaN(p.value)"
    " || (p.node && p.node.rowPinned)) return '';"
    " var v = Number(p.value);"
    " return (v < 0 ? '−' : '') + Math.abs(v).toLocaleString("
    "'es-PE', {maximumFractionDigits: 2}); }")
# Negativo en rojo, como en el resto del dashboard (regla #80). Inline, así
# que le gana al violeta de `.ag-cell` de `CSS_RANKING_GRID` sin
# `!important`.
_JS_SIGNO = (
    "function(p){ return (p.value != null && Number(p.value) < 0)"
    f" ? {{'color': '{AJUSTE_NEG_TEXTO}'}} : {{}}; }}")

_JS_FLECHA_ESTILO = (
    "function(p){ return {'color': '" + ACENTO + "', 'fontSize': '13px',"
    " 'textAlign': 'center', 'paddingLeft': '0', 'paddingRight': '0'}; }")

# La fila TOTAL con la paleta de cierre de las otras tres tablas; los
# productos que se despliegan, con la mano.
_JS_ESTILO_FILA = (
    "function(p){ if (p.node.rowPinned) { return {"
    f"'fontWeight': '700', 'background': '{LAVANDA_CHIP}',"
    f" 'color': '{ACENTO_TEXTO_OSCURO}'}}; }}"
    " var d = p.data;"
    " if (d && d.__tipo === 'p' && d.__n > 0) return {'cursor': 'pointer'};"
    " }")

# Clases y no `getRowStyle` para los dos tipos de fila: el COLOR de las
# celdas lo pone `.ag-cell` en `CSS_RANKING_GRID`, y a una celda no le llega
# un color heredado de la fila. `rowClassRules` y no `getRowClass`: la
# primera quita la clase cuando deja de cumplirse (regla #441), y la fila
# abierta se cierra.
_REGLAS_FILA = {
    "inv-fila-area": (
        "function(p){ return !!(p.data && p.data.__tipo === 'a'); }"),
    "inv-fila-abierta": (
        "function(p){ var d = p.data; return !!(d && d.__tipo === 'p'"
        f" && {_JS_ABIERTOS}[d.__id]); }}"),
}

CSS_LISTADO = {
    **CSS_RANKING_GRID,
    # El área, un escalón más abajo: fondo lavanda apenas, texto gris.
    ".ag-row.inv-fila-area": {
        "background-color": f"{LAVANDA_FILA} !important"},
    ".ag-row.inv-fila-area .ag-cell": {"color": GRIS_TEXTO_MEDIO},
    # Una fila que se ilumina al pasar el mouse promete un clic (CLAUDE.md,
    # regla #421). Las de área no hacen nada al clic: no se iluminan.
    ".ag-row.inv-fila-area.ag-row-hover::before": {
        "background-color": "transparent !important"},
    # El producto abierto se distingue de los cerrados: si no, con tres
    # abiertos no se ve dónde termina cada grupo.
    ".ag-row.inv-fila-abierta": {
        "background-color": f"{LAVANDA_SELECCION} !important"},
    ".ag-row.inv-fila-abierta .ag-cell": {"font-weight": "600"},
}


def _col(campo, titulo, **kw):
    return {"field": campo, "headerName": titulo, **kw}


def renderizar_listado(filas, total, key, movil=False):
    """La grilla. `filas` sale de `filas_grilla`; `total` es el valorizado
    de la fila TOTAL."""
    from st_aggrid import AgGrid, JsCode

    js = JsCode
    num = ["numericColumn"]
    # Anchos MEDIDOS en el navegador el 2026-09-18 (regla #349), con la
    # fuente de la grilla a 11.5px: celda = texto + 14 de padding; cabecera
    # = rótulo + 16 de padding + 20 de la flecha de orden, que aparece en la
    # columna por la que se ordena. Lo que manda en cada una:
    #   · Código       cabecera ordenada, 39+36 → 76 (el dato pide 63)
    #   · Unidad       «Unidad kardex» sin flecha, 82+16 → 100 (PRODUCCION, 97)
    #   · Precio       «Precio unitario» sin flecha, 83+16 → 104
    #   · Cantidad     cabecera ordenada, 50+36 → 86 (−1,234.56 pide 69)
    #   · Valorizado   cabecera ordenada, 87+36 → 124: abre ordenada por ella
    # Las fijas suman 520 y las tres de texto 366 de mínimo: 886px, que
    # entran en los 910 de la grilla con la ventana en 1024 sin scroll
    # horizontal (con 896 sobraba 1px: la barra vertical se come ~14). Las de texto se estiran para llenar (y su tooltip da el
    # nombre entero); las de número no ceden (`suppressSizeToFit`), porque un
    # número recortado se lee como OTRO número (CLAUDE.md, AgGrid).
    #
    # El reparto lo hace `autoSizeStrategy: fitGridWidth` y no `flex`, como
    # en `tablas/ajuste_familias.py`. Medido el 2026-09-18: con el panel del
    # navegador oculto, TODAS las grillas `flex` de la página —las de «Por
    # área» incluidas— se quedaron con sus columnas de texto en 200px, el
    # default de AG Grid, y 160-220px de desborde; las de `fitGridWidth`
    # llenaron su ancho exacto. `sizeColumnsToFit` reintenta si la grilla
    # todavía mide cero; el reparto `flex` espera un aviso de tamaño que
    # puede no llegar. Y el iframe se queda con el ancho que tenía al
    # dibujarse (regla #350), así que `flex` no compraba nada al
    # redimensionar.
    columnas = [
        {"colId": "abrir", "headerName": "", "width": 30, "minWidth": 30,
         "maxWidth": 30, "sortable": False, "resizable": False,
         "suppressSizeToFit": True,
         "pinned": "left" if movil else None,
         "valueGetter": js(_JS_FLECHA), "cellStyle": js(_JS_FLECHA_ESTILO),
         "headerTooltip": "Clic en un producto para ver en qué áreas está."},
        _col("codigo", "Código", width=76, minWidth=76,
             suppressSizeToFit=True),
        # Los `width` de estas tres son la PROPORCIÓN en que se reparten lo
        # que sobra, no su ancho final.
        _col("familia", "Familia", width=140, minWidth=96,
             tooltipField="familia"),
        _col("subfamilia", "Subfamilia", width=170, minWidth=110,
             tooltipField="subfamilia"),
        _col("nombre", "Nombre", width=310, minWidth=160,
             tooltipField="nombre", valueFormatter=js(_JS_NOMBRE),
             cellStyle=js(_JS_ESTILO_NOMBRE),
             pinned="left" if movil else None),
        _col("unidad", "Unidad kardex", width=100, minWidth=100,
             suppressSizeToFit=True),
        _col("precio", "Precio unitario", type=num, width=104, minWidth=104,
             suppressSizeToFit=True,
             valueFormatter=js(_JS_SOLES),
             headerTooltip="Precio promedio del kardex. Es el mismo en "
                           "todas las áreas del producto."),
        _col("cantidad", "Cantidad", type=num, width=86, minWidth=86,
             suppressSizeToFit=True,
             valueFormatter=js(_JS_CANTIDAD), cellStyle=js(_JS_SIGNO),
             headerTooltip="Stock al día, sumado entre las áreas."),
        _col("valorizado", "Valorizado total", type=num, width=124,
             minWidth=124, suppressSizeToFit=True, sort="desc", valueFormatter=js(_JS_SOLES),
             cellStyle=js(_JS_SIGNO),
             headerTooltip="Cantidad × precio unitario, sumado entre las "
                           "áreas."),
    ]
    # Las ocultas: sin columna no llegan al JS en todas las versiones del
    # componente, y el despliegue entero cuelga de ellas.
    columnas += [{"field": c, "hide": True}
                 for c in ("__tipo", "__id", "__padre", "__n")]

    grid_options = {
        "columnDefs": columnas,
        "defaultColDef": {"sortable": True, "resizable": True,
                          "suppressMovable": True, "filter": False},
        "autoSizeStrategy": {"type": "fitGridWidth"},
        "rowHeight": ALTO_FILA_RANK,
        "headerHeight": ALTO_HEADER_RANK,
        "tooltipShowDelay": 300,
        "suppressCellFocus": True,
        # Nueve columnas en una tarjeta ancha: sin esto AG Grid calcula el
        # rango visible antes de que el iframe tome su ancho y la última
        # columna sale vacía (el mismo bug que `_panel_top`).
        "suppressColumnVirtualisation": True,
        "isExternalFilterPresent": js(_JS_FILTRO_PRESENTE),
        "doesExternalFilterPass": js(_JS_FILTRO_PASA),
        "postSortRows": js(_JS_AREAS_BAJO_SU_PRODUCTO),
        "onRowClicked": js(_JS_CLIC),
        "rowClassRules": {k: js(v) for k, v in _REGLAS_FILA.items()},
        "getRowStyle": js(_JS_ESTILO_FILA),
        "pinnedBottomRowData": [{"nombre": "TOTAL",
                                 "valorizado": round(float(total), 2)}],
    }

    alto = alturas.por_filas(FILAS_LISTADO, px_fila=ALTO_FILA_RANK,
                             extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                             minimo=0)
    # El alto, atado también desde el documento padre: la misma red que
    # dejaron las reglas #410 y #455 en las otras tablas de la pila.
    st.markdown(
        f"<style>div.st-key-{key}, div.st-key-{key} iframe "
        f"{{ height: {alto}px !important; }}</style>",
        unsafe_allow_html=True)
    AgGrid(
        filas, gridOptions=grid_options, theme="streamlit",
        custom_css=CSS_LISTADO, allow_unsafe_jscode=True,
        height=alto,
        # Nada vuelve a Python: abrir, cerrar y ordenar son del navegador.
        update_on=[],
        key=key,
    )


# ═══════════════════════════════════════════════════════════════════════
# SECCIÓN
# ═══════════════════════════════════════════════════════════════════════

def _clamp(key, opciones):
    """Un valor que ya no está entre las opciones vuelve a «todas». Va
    justo antes del widget (CLAUDE.md): después, Streamlit no deja
    escribir su clave."""
    if st.session_state.get(key) not in opciones:
        st.session_state[key] = None


def seccion_productos(d, *, col_cod, col_prod, col_fam, col_subfam,
                      col_area, col_unidad, col_punit, col_cant, col_val):
    """La tarjeta entera: título y filtros en una fila, la tabla debajo."""
    if not (col_prod and col_val):
        st.info("Faltan las columnas de producto o de valorizado para este "
                "listado.")
        return

    fams = sorted(set(_texto(d, col_fam)) - {""})
    # columnas-internas: el título y los cuatro filtros de la tabla, en el
    # renglón de arriba de la misma tarjeta.
    c_tit, c_fam, c_sub, c_q, c_cero = st.columns(
        [1.25, 1, 1.25, 1.35, 0.95], vertical_alignment="center")
    with c_fam:
        _clamp(_K_FAMILIA, fams)
        familia = st.selectbox(
            "Familia", fams, index=None, key=_K_FAMILIA,
            format_func=nombre_propio, placeholder="Todas las familias",
            label_visibility="collapsed", disabled=not fams)
    with c_sub:
        # La subfamilia se elige DENTRO de la familia elegida: ofrecer las
        # 128 con una familia puesta deja elegir combinaciones vacías.
        _d_fam = d if not familia else d[_texto(d, col_fam) == familia]
        subs = sorted(set(_texto(_d_fam, col_subfam)) - {""})
        _clamp(_K_SUBFAMILIA, subs)
        subfamilia = st.selectbox(
            "Subfamilia", subs, index=None, key=_K_SUBFAMILIA,
            format_func=nombre_propio, placeholder="Todas las subfamilias",
            label_visibility="collapsed", disabled=not subs)
    with c_q:
        texto = st.text_input(
            "Buscar producto", key=_K_BUSCAR,
            placeholder="Buscar producto o código…",
            label_visibility="collapsed")
    with c_cero:
        incluir = st.toggle("Incluir sin stock", key=_K_SIN_STOCK)

    listado = armar_listado(
        d, col_cod=col_cod, col_prod=col_prod, col_fam=col_fam,
        col_subfam=col_subfam, col_area=col_area, col_unidad=col_unidad,
        col_punit=col_punit, col_cant=col_cant, col_val=col_val,
        familia=familia, subfamilia=subfamilia, texto=texto,
        incluir_sin_stock=incluir)
    n = len(listado.productos)

    with c_tit:
        # El número va en el título (regla #403): en una tabla que scrollea,
        # sin él no se ve si son 12 productos o 800. Con los productos en
        # cero afuera dice «867 de 3,874», para que el recorte no pase por
        # el catálogo entero; y no va en un renglón bajo el interruptor,
        # que agrandaría la fila de los filtros.
        _ocultos = 0 if incluir else listado.sin_stock
        _cuenta = f"{n:,} de {n + _ocultos:,}" if _ocultos else f"{n:,}"
        _nota = (f"{_ocultos:,} sin stock ocultos: «Incluir sin stock» "
                 "los muestra." if _ocultos else "")
        st.markdown(
            f'<div class="inv-rank-tit" style="margin:0" title="{_nota}">'
            f'Productos <span class="inv-rank-tit-n">{_cuenta}</span></div>',
            unsafe_allow_html=True)

    if not n:
        st.info("Ningún producto coincide con los filtros."
                if (familia or subfamilia or texto.strip())
                else "No hay productos con stock en este recorte.")
        return

    # La key lleva el recorte: con key estable y el `client_wins` de fábrica
    # el navegador puede quedarse con la tabla anterior (regla #227). Un
    # hash y no el texto: el buscador admite cualquier cosa, y la key
    # termina en una clase CSS (`st-key-...`) que el `<style>` de arriba
    # tiene que poder escribir igual que Streamlit.
    recorte = "|".join([familia or "", subfamilia or "", texto.strip(),
                        str(incluir), str(len(d))])
    key = f"inv_prod_grid_{zlib.crc32(recorte.encode('utf-8')):08x}"
    renderizar_listado(filas_grilla(listado),
                       float(listado.productos["valorizado"].sum()),
                       key, movil=_es_movil())
