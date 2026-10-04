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

import re
import unicodedata
import zlib
from dataclasses import dataclass

import datetime as dt

import numpy as np
import pandas as pd
import streamlit as st

import data
import kardex
from cortes import MESES_ABR_ES

from tema import (
    ACENTO, ACENTO_TEXTO_OSCURO, AJUSTE_NEG_TEXTO, BLANCO, GRIS_BORDE,
    GRIS_TEXTO_MEDIO, LAVANDA_BORDE, LAVANDA_CHIP, LAVANDA_FILA,
    LAVANDA_SELECCION,
)
from graficos import alturas
from graficos.base import (
    _es_movil, poner_seleccion, recortar_seleccion, seleccion_en_panel,
)
# El look de las otras tres tablas del dashboard (regla #404): mismo alto de
# fila, misma cabecera, mismo CSS. Una tabla ancha con otro idioma de grilla
# debajo de tres que comparten uno se lee como otro reporte.
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CROMO_GRID_RANK, unidad_corta,
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

# Las tres de categoría son LISTAS (selección múltiple) desde el
# 2026-09-18. Llevan nombre nuevo y no el de cuando eran un `st.selectbox`
# («inv_prod_familia»): una sesión abierta antes del deploy traería en esa
# clave un string suelto, y `st.pills` en modo multi revienta con eso.
_K_AREAS = "inv_prod_areas"
_K_FAMILIAS = "inv_prod_familias"
_K_SUBFAMILIAS = "inv_prod_subfamilias"
_K_BUSCAR = "inv_prod_buscar"
_K_SIN_STOCK = "inv_prod_sin_stock"
_K_SALIDA = "inv_prod_unidad_salida"
# El stock a una fecha (regla #601).
_K_A_FECHA = "inv_prod_a_fecha"
_K_FECHA = "inv_prod_fecha"
_K_HORA = "inv_prod_hora"
_K_COMPARAR = "inv_prod_comparar"

# Con qué áreas ABRE el listado (2026-09-18, a pedido: «debe filtrar
# inicialmente Almacén central, cocina, bar, producción, salón»; CAVA se sumó
# el 2026-10-03, también a pedido). Es un
# DEFAULT, no un piso: se siembra una sola vez y el usuario las cambia, o las
# suelta todas para ver el inventario entero. «Bar» es BARRA, como la
# escribe el ERP. Las que no estén en los datos no se siembran (`st.pills`
# revienta con un valor que no está entre sus opciones), y si no queda
# ninguna la tabla abre sin filtro de área. El ERP escribe «CAVA » con un
# espacio al final; las opciones salen de `_texto`, que lo recorta.
AREAS_DE_ENTRADA = ("ALMACEN CENTRAL", "COCINA", "BARRA", "PRODUCCION",
                    "SALON", "CAVA")


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


_PREFIJO = re.compile(r"^\s*(\([^)]*\)\s*)+")


def clave_orden(nombre):
    """Con qué se ordena un producto de la A a la Z: sin el prefijo del
    almacén —«(P)», «(Rs)», «(L)»— ni tildes ni mayúsculas. Con el prefijo,
    el paréntesis va antes que cualquier letra y la tabla abría con 850
    artículos «(L)…» y «(P)…» antes de «Aceite»; así «(P) Bife Ancho» cae en
    la B, junto a los otros bifes. La grilla ordena con la misma regla
    (`_JS_ORDEN_NOMBRE`)."""
    return _plano(_PREFIJO.sub("", str(nombre)))


@dataclass
class Listado:
    """Lo que dibuja la tabla, ya recortado.

    `productos` va indexado por código, con `areas` = en cuántas áreas tiene
    stock. `areas` es una fila por (código, área) con stock. `sin_stock` es
    cuántos productos del recorte quedaron FUERA por no tener stock en
    ninguna área — lo que el interruptor «Ver sin stock» agregaría."""
    productos: pd.DataFrame
    areas: pd.DataFrame
    sin_stock: int


def texto_unidad_salida(cantidad, factor, u_ent, u_sal):
    """La cantidad como la escribe el reporte por área del POS: lo ENTERO en
    la unidad del kardex y el resto en la de salida — «2 Lt 26.0 oz», «350 g»,
    «−10,645 Lt 164 ml» (regla #598).

    Es la cuenta de `spRepInventario`: `cast(stock as int)` trunca hacia el
    cero y el resto es `(stock − entero) × nFactor`. Con la misma unidad de
    los dos lados (o sin factor) no hay nada que partir y sale la cantidad
    tal cual. El resto va sin decimales cuando el factor es de mil (g, ml) y
    con uno cuando es chico (32 onzas el litro): «26.016 ONZAS» del POS es
    «26.0 oz» acá. Si el resto redondea a una unidad entera, sube:
    0.9999 Lt no es «0 Lt 1000 ml» sino «1 Lt». Pura, sin Streamlit."""
    try:
        v = float(cantidad)
    except (TypeError, ValueError):
        return ""
    if v != v:
        return ""
    ue, us = unidad_corta(u_ent), unidad_corta(u_sal)
    try:
        f = float(factor)
    except (TypeError, ValueError):
        f = 0.0
    signo = "−" if v < 0 else ""
    a = abs(v)
    if not ue or not us or us == ue or not f > 1:
        txt = f"{a:,.3f}".rstrip("0").rstrip(".")
        return f"{signo}{txt} {ue}".strip()
    dec = 0 if f >= 100 else 1
    entero = int(a)
    resto = round((a - entero) * f, dec)
    if resto >= f:
        entero, resto = entero + 1, 0.0
    partes = []
    if entero:
        partes.append(f"{entero:,} {ue}")
    if resto:
        partes.append(f"{resto:,.{dec}f} {us}")
    return signo + (" ".join(partes) if partes else f"0 {ue}")


def armar_listado(d, *, col_cod, col_prod, col_fam=None, col_subfam=None,
                  col_area=None, col_unidad=None, col_punit=None,
                  col_cant=None, col_val=None, areas=(), familias=(),
                  subfamilias=(), texto="", incluir_sin_stock=False,
                  col_factor=None, col_usal=None, col_cant_hoy=None,
                  col_val_hoy=None):
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

    LOS RECORTES son listas y una lista vacía es «todas»: `areas`,
    `familias` y `subfamilias` admiten varios valores a la vez (Alimentos y
    Vinos juntos). El de ÁREA no es como los otros dos: familia y subfamilia
    son del producto y sólo deciden si entra, pero el área es de la FILA, así
    que además cambia sus números — la cantidad y el valorizado de cada
    producto pasan a ser los de las áreas elegidas, y lo que se despliega
    son sólo esas.

    Sin `col_cod`, la clave es el nombre (hay 9 nombres repetidos entre
    códigos distintos en el parquet real: sin código se fundirían).

    `col_factor` y `col_usal` (regla #598) son del producto, como la unidad:
    con qué se parte su cantidad en la unidad de salida.

    `col_cant_hoy` y `col_val_hoy` (regla #601): con el stock A UNA FECHA,
    cantidad y valorizado son los de esa fecha y éstas las de hoy, para
    «Comparar con hoy». Se suman igual, y un área «existe» si tiene stock en
    cualquiera de los dos momentos: lo que se terminó desde entonces también
    es parte de la respuesta. A una fecha el precio es el de CADA ÁREA (el
    kardex lleva uno por área, y el POS valoriza así): donde un producto
    tiene más de uno, el suyo es el promedio ponderado de sus áreas."""
    nombre = _texto(d, col_prod)
    base = pd.DataFrame({
        "codigo": _texto(d, col_cod) if col_cod else nombre,
        "familia": _texto(d, col_fam),
        "subfamilia": _texto(d, col_subfam),
        "nombre": nombre,
        "unidad": _texto(d, col_unidad),
        "usal": _texto(d, col_usal),
        "factor": (pd.to_numeric(d[col_factor], errors="coerce")
                   if col_factor else np.nan),
        "precio": (pd.to_numeric(d[col_punit], errors="coerce")
                   if col_punit else np.nan),
        "cantidad": (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                     if col_cant else 0.0),
        "valorizado": (pd.to_numeric(d[col_val], errors="coerce").fillna(0)
                       if col_val else 0.0),
        "area": _texto(d, col_area),
        "cant_hoy": (pd.to_numeric(d[col_cant_hoy], errors="coerce").fillna(0)
                     if col_cant_hoy else 0.0),
        "val_hoy": (pd.to_numeric(d[col_val_hoy], errors="coerce").fillna(0)
                    if col_val_hoy else 0.0),
    })
    # Los tres recortes van sobre las FILAS, antes de agrupar. Familia y
    # subfamilia son atributos del producto (da lo mismo hacerlos antes o
    # después, y antes agrupa menos); el área no, y tiene que ir antes: es
    # lo que hace que los totales del producto sean los de SUS áreas.
    if areas:
        base = base[base["area"].isin(list(areas))]
    if familias:
        base = base[base["familia"].isin(list(familias))]
    if subfamilias:
        base = base[base["subfamilia"].isin(list(subfamilias))]

    prods = base.groupby("codigo", sort=False).agg(
        familia=("familia", "first"), subfamilia=("subfamilia", "first"),
        nombre=("nombre", "first"), unidad=("unidad", "first"),
        usal=("usal", "first"), factor=("factor", "first"),
        precio=("precio", "first"), _pmin=("precio", "min"),
        _pmax=("precio", "max"), cantidad=("cantidad", "sum"),
        valorizado=("valorizado", "sum"), cant_hoy=("cant_hoy", "sum"),
        val_hoy=("val_hoy", "sum"))
    _varios = (((prods["_pmax"] - prods["_pmin"]).abs() > _EPS)
               & (prods["cantidad"].abs() > _EPS))
    prods = prods.assign(precio=prods["precio"].where(
        ~_varios, prods["valorizado"] / prods["cantidad"].where(_varios, 1.0))
    ).drop(columns=["_pmin", "_pmax"])

    # El buscador: todas las palabras tienen que estar, en el nombre o en el
    # código, sin mirar tildes ni mayúsculas. «pollo kg» encuentra «Muslo
    # pollo x Kg»; una sola palabra suelta funciona como un «contiene».
    palabras = _plano(texto).split()
    if palabras and not prods.empty:
        pajar = [_plano(f"{n} {c}") for n, c in zip(prods["nombre"],
                                                     prods.index)]
        prods = prods[[all(p in h for p in palabras) for h in pajar]]

    activo = ((base["cantidad"].abs() > _EPS) | (base["valorizado"].abs() > _EPS)
              | (base["cant_hoy"].abs() > _EPS) | (base["val_hoy"].abs() > _EPS))
    en_areas = (base[activo & base["codigo"].isin(prods.index)]
                .groupby(["codigo", "area"], as_index=False, sort=False)
                .agg(cantidad=("cantidad", "sum"),
                     valorizado=("valorizado", "sum"),
                     cant_hoy=("cant_hoy", "sum"), val_hoy=("val_hoy", "sum")))
    prods = prods.assign(
        areas=prods.index.map(en_areas.groupby("codigo").size())
        .fillna(0).astype(int))

    sin_stock = int((prods["areas"] == 0).sum())
    if not incluir_sin_stock:
        prods = prods[prods["areas"] > 0]
    # De la A a la Z por NOMBRE, que es el orden con el que abre la columna
    # (2026-10-03, a pedido: por valorizado «se ve desordenado»), con la
    # regla de `clave_orden`. Las áreas de cada producto, por valorizado:
    # dónde está la mayor parte.
    prods = prods.assign(_orden=[clave_orden(n) for n in prods["nombre"]])
    prods = (prods.sort_values(["_orden", "valorizado"],
                               ascending=[True, False], kind="stable")
             .drop(columns="_orden"))
    en_areas = en_areas.sort_values("valorizado", ascending=False,
                                    kind="stable")
    return Listado(prods, en_areas.reset_index(drop=True), sin_stock)


COL_CANT_HOY = "__cant_hoy"
COL_VAL_HOY = "__val_hoy"


def _en_la_foto(d, foto, col_area, col_cod):
    """(stock, precio) de `foto` para cada fila de `d`, cruzando por área y
    producto; NaN donde la foto no la tiene."""
    clave = pd.MultiIndex.from_arrays([
        d[col_area].astype(str).str.strip(), d[col_cod].astype(str).str.strip()])
    f = foto.assign(area=foto["area"].astype(str).str.strip(),
                    cod=foto["cod"].astype(str).str.strip())
    f = f.drop_duplicates(["area", "cod"]).set_index(["area", "cod"])
    return (pd.to_numeric(f["stock"], errors="coerce").reindex(clave).to_numpy(),
            pd.to_numeric(f["precio"], errors="coerce").reindex(clave).to_numpy())


def stock_a_la_fecha(d, foto, *, col_area, col_cod, col_cant, col_val,
                     col_punit, foto_hoy=None):
    """`d` (una fila por área × producto, la de HOY) con la cantidad, el
    precio y el valorizado de la FOTO del kardex a una fecha (regla #601):
    `foto` trae `area`, `cod`, `stock` y `precio`, como lo devuelve
    `data.stock_al`. Una fila sin foto no tuvo un solo movimiento hasta esa
    fecha: su stock era cero (y su precio, el de hoy). Todo lo demás —el
    producto, su familia, si está activo— es el de hoy: el maestro no guarda
    su historia.

    Lo de HOY, para «Comparar con hoy», queda en `COL_CANT_HOY` y
    `COL_VAL_HOY`. Con `foto_hoy` (la foto del kardex al último momento) es
    ésa, con la MISMA regla de precio que la fecha: el kardex valoriza cada
    área con su precio y el reporte de hoy con el del maestro, que difiere
    en 175 filas con stock (medido el 2026-10-03), así que comparar contra
    la tabla sin fecha pintaba diferencias en productos que no se movieron.
    El stock es el mismo en las dos. Sin `foto_hoy`, o en una fila que el
    kardex no tiene, la de `d`. Pura."""
    t = d.copy()
    punit = (pd.to_numeric(d[col_punit], errors="coerce").to_numpy()
             if col_punit else np.full(len(d), np.nan))
    cant_hoy = pd.to_numeric(d[col_cant], errors="coerce").fillna(0).to_numpy()
    val_hoy = pd.to_numeric(d[col_val], errors="coerce").fillna(0).to_numpy()
    if foto_hoy is not None:
        s_h, p_h = _en_la_foto(d, foto_hoy, col_area, col_cod)
        p_h = np.where(np.isnan(p_h), punit, p_h)
        tiene = ~np.isnan(s_h)
        cant_hoy = np.where(tiene, s_h, cant_hoy)
        val_hoy = np.where(tiene, s_h * np.nan_to_num(p_h, nan=0.0), val_hoy)
    t[COL_CANT_HOY] = cant_hoy
    t[COL_VAL_HOY] = val_hoy
    stock, precio = _en_la_foto(d, foto, col_area, col_cod)
    precio = np.where(np.isnan(precio), punit, precio)
    t[col_cant] = np.nan_to_num(stock, nan=0.0)
    if col_punit:
        t[col_punit] = precio
    t[col_val] = t[col_cant].to_numpy() * np.nan_to_num(precio, nan=0.0)
    return t


def filas_grilla(listado):
    """El `rowData`: cada producto seguido de sus áreas, en un solo df.

    Las columnas de datos son las mismas para los dos tipos de fila, y en
    las de área van VACÍAS las que son del producto (familia, subfamilia,
    unidad, precio): se leen en la fila de arriba, y repetirlas en cada área
    convierte el despliegue en un bloque de texto igual. El nombre del área
    viaja en `nombre`, que es la columna que se lee hacia abajo.

    Con el stock a una fecha (regla #601) viajan además las cantidades de
    HOY (`cant_hoy`, `val_hoy`) y `dif` = hoy − la fecha, en soles: cuánto
    cambió el stock desde entonces."""
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
        "cant_hoy": a["cant_hoy"] if "cant_hoy" in a else 0.0,
        "val_hoy": a["val_hoy"] if "val_hoy" in a else 0.0,
        "__tipo": "a", "__id": a["codigo"] + "|" + a["area"],
        "__padre": a["codigo"], "__n": 0,
        "__o": a["codigo"].map(dict(zip(p["codigo"], p["__o"]))),
    })
    a = a[a["__o"].notna()]

    # La cantidad ya ESCRITA en unidad de salida y en la del kardex (regla
    # #598): el interruptor «Ver en unidad de salida» elige cuál se ve, y la
    # otra va al tooltip. Texto hecho en Python y no en el navegador: la
    # cuenta tiene prueba (`texto_unidad_salida`), y la columna sigue
    # ordenando por el número. Cada área se parte con el factor y las
    # unidades de SU producto.
    _por = p.set_index("codigo")
    _cod = list(p["codigo"]) + list(a["__padre"])
    filas = pd.concat([p, a], ignore_index=True)
    _f = [_por.at[c, "factor"] if "factor" in _por else np.nan for c in _cod]
    _ue = [_por.at[c, "unidad"] for c in _cod]
    _us = [_por.at[c, "usal"] if "usal" in _por else "" for c in _cod]
    for cant, sal, kar in (("cantidad", "cant_salida", "cant_kardex"),
                           ("cant_hoy", "cant_salida_hoy", "cant_kardex_hoy")):
        q = filas[cant] if cant in filas else pd.Series(0.0, index=filas.index)
        filas[sal] = [texto_unidad_salida(v, f, u, s2)
                      for v, f, u, s2 in zip(q, _f, _ue, _us)]
        filas[kar] = [texto_unidad_salida(v, 1, u, u) for v, u in zip(q, _ue)]
    filas["dif"] = (pd.to_numeric(filas.get("val_hoy", 0.0), errors="coerce")
                    .fillna(0) - filas["valorizado"])
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

# El orden de la columna Producto: el mismo que `clave_orden` en Python.
_JS_ORDEN_NOMBRE = r"""
function(a, b) {
    var k = function(v) {
        return String(v == null ? '' : v).replace(/^\s*(\([^)]*\)\s*)+/, '');
    };
    return k(a).localeCompare(k(b), 'es', {sensitivity: 'base'});
}
"""

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
# En unidad de salida (regla #598): el texto lo arma Python
# (`texto_unidad_salida`), acá sólo se elige —`cant_salida` o, comparando
# con hoy, `cant_salida_hoy`—. La fila TOTAL, vacía igual.
def _js_texto(campo):
    return ("function(p){ if (p.node && p.node.rowPinned) return '';"
            f" return (p.data && p.data.{campo}) || ''; }}")


# La diferencia contra hoy (regla #601), con su signo escrito: «+S/ 584.00».
_JS_SOLES_SIGNO = (
    "function(p){ if (p.value == null || isNaN(p.value)) return '';"
    " var v = Number(p.value); if (Math.abs(v) < 0.005) return 'S/ 0.00';"
    " return (v < 0 ? '−' : '+') + 'S/ ' + Math.abs(v).toLocaleString("
    "'es-PE', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }")
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


def _col_cantidad(campo, titulo, unidad_salida, sufijo="", ayuda=""):
    """La columna de una cantidad: el número, o el texto en unidad de salida
    con el número del kardex en el tooltip (regla #598)."""
    from st_aggrid import JsCode
    if unidad_salida:
        return _col(campo, titulo, type=["numericColumn"], width=120,
                    minWidth=120, suppressSizeToFit=True,
                    valueFormatter=JsCode(_js_texto("cant_salida" + sufijo)),
                    cellStyle=JsCode(_JS_SIGNO),
                    tooltipField="cant_kardex" + sufijo,
                    headerTooltip=ayuda + " Lo entero en la unidad del kardex "
                                          "y el resto en la de salida, como el "
                                          "reporte por área del POS.")
    return _col(campo, titulo, type=["numericColumn"], width=86, minWidth=86,
                suppressSizeToFit=True, valueFormatter=JsCode(_JS_CANTIDAD),
                cellStyle=JsCode(_JS_SIGNO), headerTooltip=ayuda)


def renderizar_listado(filas, total, key, movil=False, unidad_salida=False,
                       al=None, comparar=False, total_hoy=None):
    """La grilla. `filas` sale de `filas_grilla`; `total` es el valorizado
    de la fila TOTAL.

    `unidad_salida` (regla #598): la Cantidad se escribe como el reporte por
    área del POS —«2 Lt 26.0 oz»— y la columna «Unidad kardex» se esconde,
    porque las unidades ya van en la celda; sus 100px pagan los 34 que la
    Cantidad necesita de más. El número en la unidad del kardex queda en el
    tooltip, y la columna sigue ordenando por él.

    `al` (regla #601): el rótulo de la fecha del stock («Al 30 sep 2026 ·
    23:59») si no es el de hoy; agrupa encima Cantidad y Valorizado. Y
    `comparar` suma el grupo «Hoy» y la Diferencia (hoy − la fecha, en
    soles); para que entre en una laptop, ahí no van «Unidad kardex» ni
    «Precio unitario», que son de un momento y no de los dos."""
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
    #   · Valorizado   cabecera ordenada, 87+36 → 124 (hasta el 2026-10-03
    #                  abría ordenada por ella; hoy abre por Producto)
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
        # Producto · Subfamilia · Familia, de lo particular a lo general, y
        # la tabla abre de la A a la Z por producto (2026-10-03, a pedido).
        # Los `width` de estas tres son la PROPORCIÓN en que se reparten lo
        # que sobra, no su ancho final.
        _col("nombre", "Producto", width=310, minWidth=160,
             tooltipField="nombre", valueFormatter=js(_JS_NOMBRE),
             cellStyle=js(_JS_ESTILO_NOMBRE), initialSort="asc",
             comparator=js(_JS_ORDEN_NOMBRE),
             pinned="left" if movil else None),
        _col("subfamilia", "Subfamilia", width=170, minWidth=110,
             tooltipField="subfamilia"),
        _col("familia", "Familia", width=140, minWidth=96,
             tooltipField="familia"),
        _col("codigo", "Código", width=76, minWidth=76,
             suppressSizeToFit=True),
        _col("unidad", "Unidad kardex", width=100, minWidth=100,
             suppressSizeToFit=True, hide=bool(unidad_salida)),
        _col("precio", "Precio unitario", type=num, width=104, minWidth=104,
             suppressSizeToFit=True,
             valueFormatter=js(_JS_SOLES),
             headerTooltip="Precio promedio del kardex. Es el mismo en "
                           "todas las áreas del producto."),
        _col_cantidad("cantidad", "Cantidad", unidad_salida,
                      ayuda=("Stock a esa fecha" if al else "Stock al día")
                      + ", sumado entre las áreas elegidas."),
        _col("valorizado", "Valorizado total", type=num, width=124,
             minWidth=124, suppressSizeToFit=True, valueFormatter=js(_JS_SOLES),
             cellStyle=js(_JS_SIGNO),
             headerTooltip="Cantidad × precio unitario, sumado entre las "
                           "áreas elegidas."
                           + (" Al precio promedio de esa fecha." if al else "")),
    ]
    if al:
        # Las dos últimas, agrupadas bajo la fecha: se lee «de cuándo» es el
        # número sin buscarlo en el título.
        cant, val = columnas[-2], columnas[-1]
        if comparar:
            columnas = [c for c in columnas[:-2]
                        if c.get("field") not in ("unidad", "precio")]
            val = {**val, "headerName": "Valorizado"}
            columnas += [
                {"headerName": al, "children": [cant, val]},
                {"headerName": "Hoy", "children": [
                    _col_cantidad("cant_hoy", "Cantidad", unidad_salida,
                                  sufijo="_hoy", ayuda="Stock de hoy."),
                    _col("val_hoy", "Valorizado", type=num, width=124,
                         minWidth=124, suppressSizeToFit=True,
                         valueFormatter=js(_JS_SOLES),
                         cellStyle=js(_JS_SIGNO),
                         headerTooltip="Al precio promedio de hoy de cada "
                                       "área, el del kardex: puede diferir "
                                       "unos soles de la tabla sin fecha, que "
                                       "usa el del maestro.")]},
                _col("dif", "Diferencia", type=num, width=116, minWidth=116,
                     suppressSizeToFit=True, valueFormatter=js(_JS_SOLES_SIGNO),
                     cellStyle=js(_JS_SIGNO),
                     headerTooltip="Valorizado de hoy menos el de esa fecha: "
                                   "cuánto cambió el stock desde entonces."),
            ]
        else:
            columnas = columnas[:-2] + [
                {"headerName": al, "children": [cant, val]}]
    # Las ocultas: sin columna no llegan al JS en todas las versiones del
    # componente, y el despliegue entero cuelga de ellas.
    columnas += [{"field": c, "hide": True}
                 for c in ("__tipo", "__id", "__padre", "__n",
                           "cant_salida", "cant_kardex", "cant_salida_hoy",
                           "cant_kardex_hoy")]

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
                                 "valorizado": round(float(total), 2),
                                 **({"val_hoy": round(float(total_hoy), 2),
                                     "dif": round(float(total_hoy)
                                                  - float(total), 2)}
                                    if total_hoy is not None else {})}],
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

# ── EL VALOR DE UN FILTRO NO VIVE EN LA KEY DE SU WIDGET ────────────────
# Los tres widgets de categoría viven adentro de un `st.popover`, y un
# widget en un panel cerrado no se entera de lo que Python le escribe: así
# nacieron las cinco áreas de entrada que filtraban (la tabla decía 741
# productos) pero en el panel salían sin marcar, y el primer clic las
# reemplazaba por UNA. El valor vigente vive en su clave propia y el widget
# lo recibe por `default=`: `graficos/base.py::seleccion_en_panel`, que
# nació acá y desde la regla #467 usan también los filtros del
# compartimento. Lo único que escribe desde Python —los botones y el
# recorte— pasa por `poner_seleccion`.


def _rotulo_area(a):
    """El área como se escribe. Una sola excepción: el ERP tiene un área que
    se llama «---», y una etiqueta de `st.pills` es Markdown — sola, se
    dibuja como una línea horizontal y la píldora sale vacía."""
    return a if a.strip("-*_ ") else f"Sin nombre ({a})"


def _etiqueta(sel, plural, fmt=str):
    """Lo que dice el disparador: el VALOR vigente, para que se lea qué hay
    puesto sin abrir nada (regla #427). Una sola, por su nombre; varias,
    cuántas; ninguna, «Todas las …», como los desplegables de Compras
    («Todas las familias»)."""
    if not sel:
        return f"Todas las {plural}"
    if len(sel) == 1:
        return fmt(sel[0])
    return f"{len(sel)} {plural}"


# Los filtros se ven como los desplegables de Compras por período y de
# Movimientos (2026-10-03, a pedido: «que sea similar en estilo a los otros
# que tengo en mis reportes»), aunque por dentro sigan siendo un popover —
# acá la selección es MÚLTIPLE (#466) y un `st.selectbox` no lo es. Medido
# en Compras: caja de 40px, fondo blanco, borde de 1px `GRIS_BORDE`, radio
# de 8 y el texto a 14px con el color de siempre; la flecha a la derecha.
# Hasta ese día eran el disparador minimalista de Ajuste (#427): sin borde,
# 26px de alto, gris y con un ícono adelante. El buscador, igual: Streamlit
# lo pinta gris y con su tipografía, y al lado de las cajas blancas se leía
# como otro control.
CSS_FILTROS = f"""
div[class*="st-key-inv_prod_ctrl_"] button[data-testid="stPopoverButton"] {{
    min-width: 0 !important; min-height: 40px !important;
    padding: 0 8px 0 10px !important;
    background: {BLANCO} !important; border: 1px solid {GRIS_BORDE} !important;
    border-radius: 8px !important;
    justify-content: space-between !important; }}
div[class*="st-key-inv_prod_ctrl_"] button[data-testid="stPopoverButton"] > div {{
    width: 100% !important; justify-content: space-between !important; }}
div[class*="st-key-inv_prod_ctrl_"] button[data-testid="stPopoverButton"] > div > div:first-child {{
    flex: 1 1 auto !important; min-width: 0 !important;
    justify-content: flex-start !important; text-align: left !important; }}
div[class*="st-key-inv_prod_ctrl_"] button[data-testid="stPopoverButton"] p {{
    font-size: 14px !important; font-weight: 400 !important; }}
div[class*="st-key-inv_prod_ctrl_"] button[data-testid="stPopoverButton"]:hover,
div[class*="st-key-inv_prod_ctrl_"] button[data-testid="stPopoverButton"][aria-expanded="true"] {{
    border-color: {LAVANDA_BORDE} !important; }}
.st-key-{_K_BUSCAR} [data-testid="stTextInputRootElement"] {{
    background: {BLANCO} !important; border: 1px solid {GRIS_BORDE} !important;
    border-radius: 8px !important; }}
.st-key-{_K_BUSCAR} input {{
    font-family: inherit !important; font-size: 14px !important;
    padding-left: 10px !important; }}
"""


def _filtro(col, nombre, etiqueta, dibujar):
    """Un filtro de la fila: la caja con lo elegido + su panel. El contenedor
    con `inv_prod_ctrl_` es de donde cuelga `CSS_FILTROS`; el popover lleva
    key para que no se cierre al marcar una opción (la etiqueta cambia con
    cada clic, y sin key cambiaría también su identidad)."""
    with col, st.container(key=f"inv_prod_ctrl_{nombre}"):
        with st.popover(etiqueta, key=f"inv_prod_pop_{nombre}",
                        use_container_width=True):
            dibujar()


def seccion_productos(d, *, col_cod, col_prod, col_fam, col_subfam,
                      col_area, col_unidad, col_punit, col_cant, col_val,
                      col_factor=None, col_usal=None, col_cod_area=None):
    """La tarjeta entera: filtros en una fila, título y tabla debajo.

    Área, Familia y Subfamilia son de selección MÚLTIPLE (2026-09-18, a
    pedido: «un usuario puede querer filtrar alimentos y vinos a la vez»), y
    no son tres desplegables anchos sino el disparador minimalista de Ajuste
    (regla #427): el texto dice lo elegido y el panel se abre al clic. Con
    cinco áreas marcadas de entrada, un `st.multiselect` suelto en la fila
    habría envuelto sus chips en dos o tres renglones.

    «Ver en unidad de salida» (regla #598) sale sólo si el parquet trae el
    factor y la unidad de salida: sin ellos no hay con qué partir la
    cantidad, y un interruptor que no hace nada se lee como un bug.

    «Ver a una fecha» (regla #601), en el renglón del título: la tabla pasa
    al stock y al precio de ese momento —la foto del kardex, como el
    «Inventario Histórico Valorizado» del POS— con los mismos filtros, y
    «Comparar con hoy» suma lo de hoy y la diferencia."""
    if not (col_prod and col_val):
        st.info("Faltan las columnas de producto o de valorizado para este "
                "listado.")
        return

    # Sin guard de "una sola vez" (regla #59).
    st.markdown("<style>" + CSS_FILTROS + "</style>", unsafe_allow_html=True)

    # ── Opciones y estado, ANTES de dibujar: las etiquetas de los
    # disparadores leen lo elegido, y Streamlit las fija al construirlos.
    ops_area = sorted(set(_texto(d, col_area)) - {""})
    if _K_AREAS not in st.session_state:
        st.session_state[_K_AREAS] = [a for a in AREAS_DE_ENTRADA
                                      if a in ops_area]
    recortar_seleccion(_K_AREAS, ops_area)
    ops_fam = sorted(set(_texto(d, col_fam)) - {""})
    recortar_seleccion(_K_FAMILIAS, ops_fam)
    # La subfamilia se elige DENTRO de las familias elegidas: ofrecer las
    # 128 con una familia puesta deja armar combinaciones vacías.
    _fams = st.session_state.get(_K_FAMILIAS) or []
    _d_fam = d[_texto(d, col_fam).isin(_fams)] if _fams else d
    ops_sub = sorted(set(_texto(_d_fam, col_subfam)) - {""})
    recortar_seleccion(_K_SUBFAMILIAS, ops_sub)

    # DOS renglones desde el 2026-10-03: arriba los filtros, de lo general a
    # lo particular como en Compras por período (Área · Familia · Subfamilia
    # · el buscador) y los dos interruptores a la derecha; debajo, el título
    # con su cuenta. Con las cajas al tamaño de las de Compras no entraban
    # junto al título en una laptop: medido a 1323, los seis controles piden
    # ~1.070px de los 1.149 de la fila. «Ver en unidad de salida» (regla
    # #598) sale sólo si el parquet trae con qué partir.
    hay_salida = bool(col_factor and col_usal)
    c_us = None
    if hay_salida:
        # columnas-internas: los seis controles de la tabla, en el renglón de
        # arriba de la misma tarjeta. Repartidos por lo MEDIDO (14px):
        # «Todas las subfamilias» pide ~178 con su caja; «VER EN UNIDAD DE
        # SALIDA», 157 + 40 del interruptor; «VER SIN STOCK», 88 + 40.
        c_area, c_fam, c_sub, c_q, c_us, c_cero = st.columns(
            [1.45, 1.6, 1.8, 1.9, 2.0, 1.3], vertical_alignment="center")
    else:
        # columnas-internas: los cinco controles de la tabla, en el renglón
        # de arriba de la misma tarjeta.
        c_area, c_fam, c_sub, c_q, c_cero = st.columns(
            [1.45, 1.6, 1.8, 2.4, 1.3], vertical_alignment="center")
    c_tit = st.container(key="inv_prod_titulo")

    def _dib_area():
        seleccion_en_panel(st.pills, "Área", _K_AREAS, ops_area,
                           selection_mode="multi", format_func=_rotulo_area,
                           label_visibility="collapsed")
        # Soltar cinco píldoras de a una para ver todo es tedioso, y volver
        # a las de entrada sin recordar cuáles eran, más.
        with st.container(horizontal=True, gap="small"):
            st.button("Todas", key="inv_prod_areas_todas", type="tertiary",
                      on_click=poner_seleccion, args=(_K_AREAS, []))
            st.button("Las principales", key="inv_prod_areas_base",
                      type="tertiary", on_click=poner_seleccion,
                      args=(_K_AREAS, [a for a in AREAS_DE_ENTRADA
                                       if a in ops_area]))
        st.caption("Sin ninguna marcada entran todas. La cantidad y el "
                   "valorizado son los de las áreas marcadas.")

    def _dib_fam():
        seleccion_en_panel(st.pills, "Familia", _K_FAMILIAS, ops_fam,
                           selection_mode="multi", format_func=nombre_propio,
                           label_visibility="collapsed")
        st.caption("Sin ninguna marcada entran todas.")

    def _dib_sub():
        # Lista con buscador y no píldoras: sin familia elegida son 128.
        # Ancho FIJO: el panel de un popover mide lo que su contenido, y un
        # multiselect `stretch` en un panel sin ancho se encoge hasta cortar
        # su propio placeholder («Buscar subfa…», medido a 1366).
        seleccion_en_panel(st.multiselect, "Subfamilia", _K_SUBFAMILIAS,
                           ops_sub, format_func=nombre_propio,
                           placeholder="Buscar subfamilia…", width=320,
                           label_visibility="collapsed")
        st.caption("Las de " + ", ".join(nombre_propio(f) for f in _fams)
                   + "." if _fams else "Sin ninguna elegida entran todas.")

    _filtro(c_area, "area",
            _etiqueta(st.session_state.get(_K_AREAS), "áreas",
                      nombre_propio), _dib_area)
    _filtro(c_fam, "familia",
            _etiqueta(_fams, "familias", nombre_propio), _dib_fam)
    _filtro(c_sub, "subfamilia",
            _etiqueta(st.session_state.get(_K_SUBFAMILIAS), "subfamilias",
                      nombre_propio), _dib_sub)
    with c_q:
        texto = st.text_input(
            "Buscar producto", key=_K_BUSCAR,
            placeholder="Buscar producto o código…",
            label_visibility="collapsed")
    with c_cero:
        # Sin `help=`: su ícono partía el rótulo en dos renglones en una
        # columna de 141px. Qué hace lo dice el `title` del título, que
        # cuenta cuántos productos esconde.
        incluir = st.toggle("Ver sin stock", key=_K_SIN_STOCK)
    en_salida = False
    if hay_salida:
        with c_us:
            en_salida = st.toggle("Ver en unidad de salida", key=_K_SALIDA)

    # ── «Ver a una fecha» (regla #601), a la derecha del título ──────────
    # columnas-internas: el título y los controles de la fecha, en el
    # renglón de abajo de los filtros.
    c_tt, c_af, c_fe, c_ho, c_cmp = c_tit.columns(
        [2.4, 1.65, 1.3, 1.25, 1.65], vertical_alignment="center")
    hay_fecha = bool(col_cod and col_cod_area)
    al, comparar, d_vista, momento_al = None, False, d, None
    if hay_fecha:
        with c_af:
            a_fecha = st.toggle("Ver a una fecha", key=_K_A_FECHA)
        if a_fecha:
            _rango = data.rango_fechas(kardex.ARCHIVO, kardex.COL_FECHA)
            _tope = _rango[1] if _rango else dt.date.today()
            _desde = _rango[0] if _rango else kardex.INICIO
            if _K_FECHA not in st.session_state:
                # Abre en el cierre del mes pasado: es la pregunta de siempre
                # («¿con cuánto cerramos septiembre?»), y el último día con
                # movimientos sería la tabla de hoy otra vez.
                st.session_state[_K_FECHA] = (_tope.replace(day=1)
                                              - dt.timedelta(days=1))
            st.session_state[_K_FECHA] = min(max(st.session_state[_K_FECHA],
                                                 _desde), _tope)
            with c_fe:
                fecha = st.date_input("Fecha", key=_K_FECHA, min_value=_desde,
                                      max_value=_tope, format="DD/MM/YYYY",
                                      label_visibility="collapsed")
            with c_ho:
                hora = st.selectbox(
                    "Hora", list(range(24)), index=23, key=_K_HORA,
                    format_func=lambda h: f"hasta las {h:02d}:59",
                    label_visibility="collapsed")
            with c_cmp:
                comparar = st.toggle("Comparar con hoy", key=_K_COMPARAR)
            momento_al = kardex.momento(fecha, hora)
            foto = data.stock_al(momento_al)
            # «Hoy» es la foto del último momento del kardex, no la tabla sin
            # fecha: misma regla de precio que la fecha (ver
            # `stock_a_la_fecha`).
            foto_hoy = (data.stock_al(kardex.momento(_tope, 23))
                        if comparar else None)
            if foto is None:
                with c_tt:
                    st.caption("Falta el kardex: la consulta «kardex» del "
                               "Sheet todavía no llegó a la app.")
                comparar = False
            else:
                al = (f"Al {fecha.day} {MESES_ABR_ES[fecha.month - 1]} "
                      f"{fecha.year} · {hora:02d}:59")
                d_vista = stock_a_la_fecha(
                    d, foto, col_area=col_cod_area, col_cod=col_cod,
                    col_cant=col_cant, col_val=col_val, col_punit=col_punit,
                    foto_hoy=foto_hoy)

    areas = st.session_state.get(_K_AREAS) or []
    familias = st.session_state.get(_K_FAMILIAS) or []
    subfamilias = st.session_state.get(_K_SUBFAMILIAS) or []
    listado = armar_listado(
        d_vista, col_cod=col_cod, col_prod=col_prod, col_fam=col_fam,
        col_subfam=col_subfam, col_area=col_area, col_unidad=col_unidad,
        col_punit=col_punit, col_cant=col_cant, col_val=col_val,
        areas=areas, familias=familias, subfamilias=subfamilias,
        texto=texto, incluir_sin_stock=incluir,
        col_factor=col_factor, col_usal=col_usal,
        col_cant_hoy=COL_CANT_HOY if (al and comparar) else None,
        col_val_hoy=COL_VAL_HOY if (al and comparar) else None)
    n = len(listado.productos)

    with c_tt:
        # El número va en el título (regla #403): en una tabla que scrollea,
        # sin él no se ve si son 12 productos o 800. Con los productos en
        # cero afuera dice «867 de 3,874», para que el recorte no pase por
        # el catálogo entero; y no va en un renglón bajo el interruptor,
        # que agrandaría la fila de los filtros.
        _ocultos = 0 if incluir else listado.sin_stock
        _cuenta = f"{n:,} de {n + _ocultos:,}" if _ocultos else f"{n:,}"
        _nota = (f"{_ocultos:,} sin stock ocultos: «Ver sin stock» "
                 "los muestra." if _ocultos else "")
        st.markdown(
            f'<div class="inv-rank-tit" style="margin:0" title="{_nota}">'
            f'Productos <span class="inv-rank-tit-n">{_cuenta}'
            + (f" · {al.lower()}" if al else "") + '</span></div>',
            unsafe_allow_html=True)

    if not n:
        st.info("Ningún producto coincide con los filtros."
                if (areas or familias or subfamilias or texto.strip())
                else "No hay productos con stock en este recorte.")
        return

    # La key lleva el recorte: con key estable y el `client_wins` de fábrica
    # el navegador puede quedarse con la tabla anterior (regla #227). Un
    # hash y no el texto: el buscador admite cualquier cosa, y la key
    # termina en una clase CSS (`st-key-...`) que el `<style>` de arriba
    # tiene que poder escribir igual que Streamlit.
    recorte = "|".join([",".join(sorted(areas)), ",".join(sorted(familias)),
                        ",".join(sorted(subfamilias)), texto.strip(),
                        str(incluir), str(len(d)), str(en_salida),
                        str(momento_al if al else ""), str(comparar)])
    key = f"inv_prod_grid_{zlib.crc32(recorte.encode('utf-8')):08x}"
    renderizar_listado(filas_grilla(listado),
                       float(listado.productos["valorizado"].sum()),
                       key, movil=_es_movil(), unidad_salida=en_salida,
                       al=al, comparar=bool(al and comparar),
                       total_hoy=(float(listado.productos["val_hoy"].sum())
                                  if (al and comparar) else None))
