"""graficos.ajuste._productos - la TABLA de productos del detalle de Ajuste.

Nació el 2026-10-19 a pedido, junto con el Pareto en el detalle (regla
#677): «Por producto» de Por familia y el detalle de Familia × Área suman
una vista en tabla con las columnas en este orden — Código · Familia ·
Subfamilia · Nombre · Unidad kardex · Área · Stock sistema · Diferencia ·
Conteo · Valorizado —, con el área «agrupada para desplegar».

DOS FORMAS, elegidas con «Áreas»:

  · SEPARADAS: una fila por LÍNEA (producto × área) con diferencia. Es el
    grano del conteo, el mismo de las listas de Faltantes y Sobrantes.
  · JUNTAS: una fila por PRODUCTO con sus áreas sumadas, y un clic en la
    fila despliega debajo cada área. Lo que falta en una y sobra en otra se
    compensa en el total, y la celda lo dice («se compensa»): sin la marca,
    el neto escondería la mitad del problema (el docstring de `_cascada`
    cuenta por qué el grano es la línea). Las áreas del despliegue son TODAS
    las que tienen stock, también las que cerraron sin diferencia: si no,
    el stock y el conteo de la fila de arriba no serían la suma de lo de
    abajo.

EL DESPLIEGUE ES EL DE STOCK POR PRODUCTO (`graficos/inventario_productos.py`,
regla #466), no el master/detail de AG Grid, que es Enterprise: filas planas
de dos tipos en el mismo rowData, un filtro externo que deja pasar las de
área sólo si su producto está abierto y un `postSortRows` que las vuelve a
colgar debajo de él. El JS se importa de allá, no se copia: dos copias del
mismo despliegue se desincronizan a la primera corrección.

«Valorizado» es la DIFERENCIA valorizada (`AJUSTE VALORIZADO`: diferencia ×
precio promedio), la misma cifra que suman las tablas de arriba.
"""

import numpy as np
import pandas as pd
import streamlit as st

from tema import ACENTO_TEXTO, AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO
from graficos import alturas
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CROMO_GRID_RANK,
)
from graficos.compras._etiquetas_proveedor import nombre_propio
# El despliegue entero (ver docstring). `CSS_LISTADO` trae el look de la
# fila de área y de la fila abierta.
from graficos.inventario_productos import (
    CSS_LISTADO, _JS_AREAS_BAJO_SU_PRODUCTO, _JS_CLIC, _JS_ESTILO_FILA,
    _JS_FILTRO_PASA, _JS_FILTRO_PRESENTE, _JS_FLECHA, _JS_FLECHA_ESTILO,
    _JS_ORDEN_NOMBRE, _JS_SOLES_SIGNO, _REGLAS_FILA,
)

AREAS = ("Separadas", "Juntas")
VER_COMO = ("Listas", "Tabla")

# Las filas que se ven antes de scrollear por dentro de la grilla.
FILAS_TABLA = 10

_EPS = 1e-9

# Los nombres de las columnas del parquet. Se resuelven con `_resolver`
# (graficos.base) en el llamador; acá sólo las listas.
COL_CODIGO = ["CODIGO PRODUCTO", "Codigo Producto", "COD PRODUCTO"]
COL_SUBFAMILIA = ["SUBFAMILIA", "Subfamilia", "SUB FAMILIA"]
COL_UNIDAD = ["UNIDAD MEDIDA", "Unidad Medida", "Unidad Kardex", "UNIDAD"]


def _txt(d, col):
    if not col or col not in d.columns:
        return pd.Series("", index=d.index)
    s = d[col].astype(str).str.strip()
    return s.mask(s.str.lower().isin(("nan", "none")), "")


def _n(d, col):
    if not col or col not in d.columns:
        return pd.Series(0.0, index=d.index)
    return pd.to_numeric(d[col], errors="coerce").fillna(0.0)


def filas_productos(d, *, col_cod, col_fam, col_subfam, col_prod, col_um,
                    col_area, col_sis, col_dif, col_fis, col_val, juntas):
    """El `rowData` de la tabla. Pura: la prueba `test_graficos.py`.

    Columnas: `codigo · familia · subfamilia · nombre · unidad · area ·
    sistema · dif · conteo · valor`, y las ocultas del despliegue (`__tipo`
    «p»/«a», `__id`, `__padre`, `__n` = cuántas áreas despliega, `__comp` =
    se compensa). Ordenadas por |valor| de mayor a menor, cada producto
    seguido de sus áreas: la grilla abre en ese orden (sin `initialSort`) y
    `postSortRows` lo conserva al ordenar.

    Sin `col_cod` el producto se identifica por su nombre."""
    if d is None or d.empty or not col_prod or col_prod not in d.columns:
        return pd.DataFrame()
    b = pd.DataFrame({
        "codigo": _txt(d, col_cod), "familia": _txt(d, col_fam),
        "subfamilia": _txt(d, col_subfam), "nombre": _txt(d, col_prod),
        "unidad": _txt(d, col_um), "area": _txt(d, col_area),
        "sistema": _n(d, col_sis), "dif": _n(d, col_dif),
        "conteo": _n(d, col_fis), "valor": _n(d, col_val),
    })
    b["__id"] = b["codigo"].where(b["codigo"] != "", b["nombre"])
    # La línea (producto × área): una sesión que junta dos conteos (el 1 y
    # el 6 de octubre) puede traer la misma línea dos veces.
    lin = (b.groupby(["__id", "area"], as_index=False, sort=False)
           .agg(codigo=("codigo", "first"), familia=("familia", "first"),
                subfamilia=("subfamilia", "first"), nombre=("nombre", "first"),
                unidad=("unidad", "first"), sistema=("sistema", "sum"),
                dif=("dif", "sum"), conteo=("conteo", "sum"),
                valor=("valor", "sum")))
    lin["familia"] = [nombre_propio(x) if x else "" for x in lin["familia"]]
    lin["subfamilia"] = [nombre_propio(x) if x else "" for x in lin["subfamilia"]]
    con_dif = (lin["dif"].abs() > _EPS) | (lin["valor"].abs() > _EPS)
    # Un producto entra si ALGUNA de sus líneas tiene diferencia.
    ids = set(lin.loc[con_dif, "__id"])
    lin = lin[lin["__id"].isin(ids)]
    cols = ["codigo", "familia", "subfamilia", "nombre", "unidad", "area",
            "sistema", "dif", "conteo", "valor"]

    if not juntas:
        f = lin[con_dif.loc[lin.index]].copy()
        f = f.reindex(f["valor"].abs().sort_values(
            ascending=False, kind="stable").index)
        f["__tipo"] = "p"
        f["__id"] = f["__id"] + "|" + f["area"]
        f["__padre"] = ""
        f["__n"] = 0
        f["__comp"] = False
        return f[cols + ["__tipo", "__id", "__padre", "__n", "__comp"]] \
            .reset_index(drop=True)

    # Áreas con stock o con diferencia: las que cerraron en cero y cero no
    # suman nada y no se despliegan.
    vivas = lin[(lin["sistema"].abs() > _EPS) | (lin["conteo"].abs() > _EPS)
                | (lin["dif"].abs() > _EPS) | (lin["valor"].abs() > _EPS)]
    g = (vivas.groupby("__id", as_index=False, sort=False)
         .agg(codigo=("codigo", "first"), familia=("familia", "first"),
              subfamilia=("subfamilia", "first"), nombre=("nombre", "first"),
              unidad=("unidad", "first"), sistema=("sistema", "sum"),
              dif=("dif", "sum"), conteo=("conteo", "sum"),
              valor=("valor", "sum"), __n=("area", "nunique"),
              __neg=("valor", lambda s: bool((s < -0.005).any())),
              __pos=("valor", lambda s: bool((s > 0.005).any())),
              __una=("area", "first")))
    g["__comp"] = g["__neg"] & g["__pos"]
    g["area"] = np.where(g["__n"] > 1, g["__n"].astype(str) + " áreas",
                         g["__una"])
    g = g.reindex(g["valor"].abs().sort_values(
        ascending=False, kind="stable").index).reset_index(drop=True)
    g["__o"] = range(len(g))
    g["__tipo"] = "p"
    g["__padre"] = ""
    # Un producto de UNA sola área no despliega nada: ya la dice su celda.
    g["__n"] = np.where(g["__n"] > 1, g["__n"], 0)

    a = vivas[vivas["__id"].isin(set(g.loc[g["__n"] > 0, "__id"]))].copy()
    a["__o"] = a["__id"].map(dict(zip(g["__id"], g["__o"])))
    a = a.reindex(a["valor"].abs().sort_values(
        ascending=False, kind="stable").index)
    a["__padre"] = a["__id"]
    a["__id"] = a["__id"] + "|" + a["area"]
    a["__tipo"] = "a"
    a["__n"] = 0
    a["__comp"] = False
    # En la fila de área sólo va lo que cambia de un área a otra: repetir
    # código, familia y nombre convertiría el despliegue en un bloque igual.
    for c in ("codigo", "familia", "subfamilia", "nombre", "unidad"):
        a[c] = ""

    filas = pd.concat([g, a], ignore_index=True)
    filas["__t"] = (filas["__tipo"] == "a").astype(int)
    filas = filas.sort_values(["__o", "__t"], kind="stable")
    return filas[cols + ["__tipo", "__id", "__padre", "__n", "__comp"]] \
        .reset_index(drop=True)


# ── Formatos de la grilla ─────────────────────────────────────────────────
# El área de un producto que despliega: «3 áreas · se compensa». Las de
# área, con la flecha que dice que cuelgan de la fila de arriba.
_JS_AREA = (
    "function(p){ var d = p.data; if (!d || p.node.rowPinned) return '';"
    " if (d.__tipo === 'a') return '↳ ' + (p.value || '');"
    " return d.__comp ? p.value + ' · se compensa' : (p.value || ''); }")
_JS_AREA_ESTILO = (
    "function(p){ var d = p.data; if (!d) return {};"
    " if (d.__tipo === 'a') return {'paddingLeft': '18px'};"
    f" if (d.__n > 0) return {{'color': '{ACENTO_TEXTO}', 'fontWeight': '600'}};"
    " return {}; }")
# Cantidades: hasta tres decimales (el conteo de un kilo llega al gramo).
# La fila TOTAL no lleva cantidad: sumar kilos con litros no da una unidad.
_JS_CANT = (
    "function(p){ if (p.value == null || isNaN(p.value)"
    " || (p.node && p.node.rowPinned)) return '';"
    " var v = Number(p.value);"
    " return (v < 0 ? '−' : '') + Math.abs(v).toLocaleString("
    "'es-PE', {maximumFractionDigits: 3}); }")
_JS_CANT_SIGNO = (
    "function(p){ if (p.value == null || isNaN(p.value)"
    " || (p.node && p.node.rowPinned)) return '';"
    " var v = Number(p.value); if (Math.abs(v) < 0.0005) return '0';"
    " return (v < 0 ? '−' : '+') + Math.abs(v).toLocaleString("
    "'es-PE', {maximumFractionDigits: 3}); }")
# Faltante en rojo, sobrante en verde: los dos colores de las tablas de
# arriba. Inline, así que le gana al violeta de `.ag-cell` sin !important.
_JS_COLOR_SIGNO = (
    "function(p){ if (p.value == null) return {}; var v = Number(p.value);"
    f" if (v < -0.0005) return {{'color': '{AJUSTE_NEG_TEXTO}'}};"
    f" if (v > 0.0005) return {{'color': '{AJUSTE_POS_TEXTO}'}};"
    " return {}; }")


def _col(campo, titulo, **kw):
    return {"field": campo, "headerName": titulo, **kw}


def renderizar_tabla_productos(filas, key, juntas, n_filas=FILAS_TABLA):
    """La grilla. `filas` sale de `filas_productos`. Nada vuelve a Python:
    desplegar, cerrar y ordenar son del navegador (`update_on=[]`)."""
    from st_aggrid import AgGrid, JsCode

    js = JsCode
    num = ["numericColumn"]
    # Anchos: los números no ceden (`suppressSizeToFit`) porque un número
    # recortado se lee como OTRO número (CLAUDE.md, AgGrid); las de texto
    # reparten lo que sobra con `fitGridWidth`, como Stock por Producto.
    columnas = []
    if juntas:
        columnas.append(
            {"colId": "abrir", "headerName": "", "width": 30, "minWidth": 30,
             "maxWidth": 30, "sortable": False, "resizable": False,
             "suppressSizeToFit": True, "valueGetter": js(_JS_FLECHA),
             "cellStyle": js(_JS_FLECHA_ESTILO),
             "headerTooltip": "Clic en un producto para ver sus áreas."})
    columnas += [
        # «0000004088» pide 76px de texto más 14 de padding y la flecha de
        # orden cuando manda (regla #349).
        _col("codigo", "Código", width=96, minWidth=96,
             suppressSizeToFit=True),
        _col("familia", "Familia", width=110, minWidth=84,
             tooltipField="familia", comparator=js(_JS_ORDEN_NOMBRE)),
        _col("subfamilia", "Subfamilia", width=140, minWidth=96,
             tooltipField="subfamilia", comparator=js(_JS_ORDEN_NOMBRE)),
        _col("nombre", "Nombre", width=300, minWidth=170,
             tooltipField="nombre", comparator=js(_JS_ORDEN_NOMBRE)),
        _col("unidad", "Unidad kardex", width=100, minWidth=100,
             suppressSizeToFit=True),
        _col("area", "Área", width=170, minWidth=120, tooltipField="area",
             valueFormatter=js(_JS_AREA), cellStyle=js(_JS_AREA_ESTILO),
             headerTooltip=("Con «Juntas», las áreas del producto sumadas; "
                            "«se compensa» = faltó en un área y sobró en "
                            "otra." if juntas else "")),
        _col("sistema", "Stock sistema", type=num, width=104, minWidth=104,
             suppressSizeToFit=True, valueFormatter=js(_JS_CANT),
             headerTooltip="Stock del sistema al cierre (STOCK AL CIERRE)."),
        _col("dif", "Diferencia", type=num, width=96, minWidth=96,
             suppressSizeToFit=True, valueFormatter=js(_JS_CANT_SIGNO),
             cellStyle=js(_JS_COLOR_SIGNO),
             headerTooltip="Conteo − sistema, en la unidad del kardex."),
        _col("conteo", "Conteo", type=num, width=86, minWidth=86,
             suppressSizeToFit=True, valueFormatter=js(_JS_CANT),
             headerTooltip="Lo contado (STOCK DECLARADO)."),
        _col("valor", "Valorizado", type=num, width=116, minWidth=116,
             suppressSizeToFit=True, valueFormatter=js(_JS_SOLES_SIGNO),
             cellStyle=js(_JS_COLOR_SIGNO),
             headerTooltip="La diferencia valorizada: diferencia × precio "
                           "promedio (AJUSTE VALORIZADO)."),
    ]
    # Las ocultas: sin columna no llegan al JS en todas las versiones del
    # componente, y el despliegue entero cuelga de ellas.
    columnas += [{"field": c, "hide": True}
                 for c in ("__tipo", "__id", "__padre", "__n", "__comp")]
    total = float(filas.loc[filas["__tipo"] == "p", "valor"].sum()) \
        if len(filas) else 0.0
    _vis = int((filas["__tipo"] == "p").sum()) if len(filas) else 1
    grid_options = {
        "columnDefs": columnas,
        "defaultColDef": {"sortable": True, "resizable": True,
                          "suppressMovable": True, "filter": False},
        "autoSizeStrategy": {"type": "fitGridWidth"},
        "rowHeight": ALTO_FILA_RANK,
        "headerHeight": ALTO_HEADER_RANK,
        "tooltipShowDelay": 300,
        "suppressCellFocus": True,
        "suppressColumnVirtualisation": True,
        "isExternalFilterPresent": js(_JS_FILTRO_PRESENTE),
        "doesExternalFilterPass": js(_JS_FILTRO_PASA),
        "postSortRows": js(_JS_AREAS_BAJO_SU_PRODUCTO),
        "onRowClicked": js(_JS_CLIC),
        "rowClassRules": {k: js(v) for k, v in _REGLAS_FILA.items()},
        "getRowStyle": js(_JS_ESTILO_FILA),
        # Cuántos son, en la fila TOTAL: un rótulo arriba de la grilla
        # cobraría el −16px de margen de `st.markdown` y la grilla lo pisa.
        "pinnedBottomRowData": [{
            "codigo": "TOTAL",
            "nombre": f"{_vis:,} {'productos' if juntas else 'líneas'}",
            "valor": round(total, 2)}],
    }
    alto = alturas.por_filas(min(n_filas, max(1, _vis)),
                             px_fila=ALTO_FILA_RANK,
                             extra=CROMO_GRID_RANK + ALTO_FILA_RANK,
                             minimo=0)
    # El alto, atado también desde el documento padre (reglas #410 y #455).
    st.markdown(
        f"<style>div.st-key-{key}, div.st-key-{key} iframe "
        f"{{ height: {alto}px !important; display: block !important; }}"
        f"</style>", unsafe_allow_html=True)
    AgGrid(filas, gridOptions=grid_options, theme="streamlit",
           custom_css=CSS_LISTADO, allow_unsafe_jscode=True, height=alto,
           update_on=[], key=key)


def buscar(filas, q):
    """Las filas cuyo producto o área calzan con `q` (sin distinguir
    mayúsculas). Un producto que calza trae sus áreas; un área que calza
    trae a su producto, para que el despliegue no quede huérfano."""
    q = (q or "").strip().lower()
    if not q or filas.empty:
        return filas
    _txt = (filas["codigo"].str.lower() + " " + filas["nombre"].str.lower()
            + " " + filas["area"].str.lower())
    hit = _txt.str.contains(q, regex=False)
    ids = set(filas.loc[hit & (filas["__tipo"] == "p"), "__id"])
    ids |= set(filas.loc[hit & (filas["__tipo"] == "a"), "__padre"])
    return filas[(filas["__tipo"] == "p") & filas["__id"].isin(ids)
                 | (filas["__tipo"] == "a") & filas["__padre"].isin(ids)]
