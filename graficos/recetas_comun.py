"""
graficos.recetas_comun — infraestructura COMPARTIDA entre Receta Base y
Receta Venta.

Los dos parquets son la MISMA forma de dato — un BOM (lista de materiales):
cada fila es un ítem/insumo dentro de un contenedor (plato o receta base),
con una cantidad y un costo. Lo que queda acá es lo que usan los dos lados
—y la Carta costeada, y el formulario de Nueva receta—: `_activo()`, que
normaliza los TRES formatos del flag de activo; `_hex_a_rgba`, del Sankey
del panel de la Carta; el divisor del precio neto (regla #514) y el catálogo
de insumos del Almacén.

LO QUE SE FUE, Y POR QUÉ — se borra cuando pierde su ÚLTIMO llamador:

  · `_ranking_contenedores` (el Ranking de recetas base, barras con el costo
    POR LOTE de cada receta del catálogo) y su `_fmt_valor`, el 2026-09-30 —
    regla #576. Decía cuál receta cuesta más hacer una vez y nada de cuánto
    se usa; lo reemplazó «Costo Recetas Base» (`graficos/recetas_base_costo.py`),
    que cruza lo usado por las ventas con las órdenes de producción.

  · `_composicion_contenedor` (la dona de UN plato/receta), el 2026-08-28:
    Receta Venta la reemplazó por una tabla propia y Receta Base dio de baja
    sus vistas de UNA receta elegida a mano. Ver `arquitectura.md` #236.
  · `_sankey_contenedor` y `_drill_contenedor_jump` (el botón «Abrir
    Sankey →»), el 2026-08-30, cuando Receta Venta dio de baja esa vista.
  · `_items_clave` (Ingredientes clave · Insumos clave · recetas base) y el
    Panorama de compras entero (`_panorama_compras`, `_cargar_flujo_compras`
    y su Sankey), el 2026-09-28 — regla #559. Los dos medían la CARTA y no
    lo vendido: «Ingredientes clave» sumaba el costo POR PORCIÓN de cada
    ingrediente en los platos activos, y su primer puesto (un whisky, S/ 265
    «en 1 plato») se pidió una vez en 90 días. El Panorama repartía lo
    comprado entre los platos según la receta y sólo reconocía un insumo si
    la receta lo nombraba tal cual: en septiembre de 2026 daba «vinculado a
    receta» al 21 % de lo comprado, contra el 94 % que explica Movimientos ›
    «Consumo según recetas» (regla #558), que baja cada VENTA por recetas
    base y porcionamientos hasta el insumo de compra. Esa es la vista que
    contesta hoy «qué ingredientes pesan» y «dónde se usa este insumo»; la
    idea que sólo tenía el Panorama —lo comprado que ninguna receta explica—
    se mudó ahí, a su pestaña «Contra compras».

**CORREGIDO 2026-09-04 — sÍ se cruzan.** Acá decía que Base y Venta eran
"dos catálogos independientes, 0% overlap". Ese 0% se midió contra
`recetabase.COD RB`, que es el ID INTERNO de la receta base (5 dígitos,
`00002`), no su código de producto. La clave real es
`recetaventa.COD INS` ↔ `recetabase.COD PROD RB`: 401 códigos cruzan y los
401 NOMBRES coinciden exacto en los dos lados. Una receta base es una
PIEZA de un plato, no su hermana. Ver `arquitectura.md` regla #303; el
árbol entero lo recorre hoy `consumo_recetas.py` (regla #558).
"""

import pandas as pd
import streamlit as st

from data import cargar as _cargar_reporte
from graficos.base import _resolver


# ─── Helpers de formato ─────────────────────────────────────────────────────
def _hex_a_rgba(hex_color: str, alpha: float = 0.45) -> str:
    """'#6c5ce7' → 'rgba(108,92,231,0.45)'. Para links de Sankey semitransp."""
    h = str(hex_color).lstrip("#")
    if len(h) != 6:
        return f"rgba(108,92,231,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _activo(serie):
    """True donde el flag de activo/inactivo de la fila indica ACTIVO.

    Los TRES flags de "activo" que usan estos dos parquets vienen en
    formatos DISTINTOS aunque compartan intención (confirmado contra R2
    real, 2026-08-13):
      · recetaventa.ITEM VENTA ACTIVO / INS ACTIVO → "ACTIV" / "INACTIV" / ""
      · recetabase.RB ACT                          → "RB.ACTIV" / "RB.INACT"
      · recetabase.INS ACTIVO (MISMO NOMBRE que en recetaventa, formato
        DISTINTO)                                  → "INS.ACT" / "INS.INAC"
    Un `.str.startswith("ACTIV")` (lo que usaba el código original de
    Receta Venta, antes de esta función) no sirve para los dos de Base:
    ninguno arranca con "ACTIV" por el prefijo ("RB."/"INS."). La señal que
    SÍ es estable en los tres formatos es la sub-cadena "INAC" (siempre
    presente en la forma inactiva, nunca en la activa) — más vacío/NaN, que
    se trata como "no confirmado activo" (mismo criterio que ya usaba
    Receta Venta para su ~0.5% de INS ACTIVO en blanco). Verificado que
    reproduce EXACTO el conteo de filas activas que ya tenía Receta Venta
    en producción (1200/2713 con ambos flags) antes de generalizar esto.

    `serie.isna()` (no un match de texto tipo "nan"/"none") para el vacío:
    según la fuente, un valor faltante llega como `None`, `NaN` o `pd.NA`,
    y `.astype(str)` los serializa DISTINTO ("None" vs "nan") — confiar en
    el texto se comió el caso `None` en la primera versión de esta función."""
    vacio = serie.isna() | (serie.astype(str).str.strip() == "")
    s = serie.astype(str).str.upper()
    return ~vacio & ~s.str.contains("INAC")


# El chip Recetas/+ Nueva (`_chip_fuente`) vivió acá desde su nacimiento
# hasta el 2026-09-22. Nació el 2026-08-30 como Opción A del rail unificado,
# separando las TRES entradas de nav Receta base / Receta venta / + Nueva;
# el 2026-09-04 se fundió a DOS al fusionarse los dos parquets en una sola
# página (regla #303); y desapareció al bajar "+ Nueva" a ser una VISTA más
# del reporte Recetas (`graficos/recetas.py::_RAIL_CATEGORIAS`), con lo que
# el grupo_nav de Recetas quedó de un solo miembro y no había a dónde
# chipear. La navegación entre secciones ahora la hace el rail lateral, con
# el mismo mecanismo que Compras/Ajuste.


# ─── El catálogo de insumos de almacén ──────────────────────────────────────
# Vivía en `formulario_receta.py::_catalogo_insumos_cacheado` y se mudó acá
# el 2026-09-17, cuando el simulador de Composición (`recetaventa.py::
# _panel_receta`) necesitó el mismo catálogo para "agregar un insumo". Es el
# escenario de la regla #379 —dos copias del mismo formateo divergiendo—
# atajado antes de que naciera la segunda: la herramienta y el dashboard
# tienen que ofrecer EL MISMO catálogo o "agregar Sal De Mesa" significa dos
# cosas distintas según desde dónde se agregue.
#
# Normaliza a cinco columnas (cod/nombre/unidad/precio/activo) para que
# quien lo consuma no tenga que saber de qué parquet vino.
ARCHIVO_INVENTARIO = "inventariovalorizado.parquet"
ARCHIVO_RECETAVENTA = "recetaventa.parquet"


# ─── Precio neto: lo que el sistema llama «neto» ─────────────────────────
# El precio de carta es neto + IGV + recargo al consumo, los dos SUMADOS
# sobre el neto (no uno encima del otro). Medido el 2026-09-24 en las
# boletas del POS (INFOREST.DDOCUMENTO: `nPrecioImpuesto1/nPrecioNeto` =
# 0,105 y `nPrecioImpuesto2/nPrecioNeto` = 0,13 en todas) y en el parquet:
# `P.VENTA × %CST / CST` da 1,235 en los 839 platos y en los cuatro
# canales. Hasta ese día la app dividía por 1,18 (Composición) o por
# 1,18 × 1,10 (Nueva receta), y el % de costo no coincidía con el del
# sistema. El IGV de restaurantes cambia por ley año a año (fue 18 %, 10 %
# y hoy 10,5 %), así que el divisor se LEE del parquet; lo fijo es el
# recargo, que pone el restaurante. Regla #514.
TASA_RECARGO = 0.13
DIVISOR_NETO_RESPALDO = 1.235


@st.cache_data(ttl=300, show_spinner=False)
def divisor_neto():
    """Precio de carta ÷ precio neto, tal como lo usa el sistema para su
    `%CST`: la mediana de `P.VENTA SALON × %CST SALON / CST SALON`. Si el
    parquet no lo deja calcular, el último medido (1,235)."""
    df = _cargar_reporte(ARCHIVO_RECETAVENTA)
    if df is None or df.empty:
        return DIVISOR_NETO_RESPALDO
    c_pv = _resolver(df, ["P.VENTA SALON", "P VENTA SALON"])
    c_cst = _resolver(df, ["CST SALON", "Costo Salon"])
    c_pct = _resolver(df, ["%CST SALON", "% CST SALON", "PCT CST SALON"])
    if not (c_pv and c_cst and c_pct):
        return DIVISOR_NETO_RESPALDO
    pv = pd.to_numeric(df[c_pv], errors="coerce")
    cst = pd.to_numeric(df[c_cst], errors="coerce")
    pct = pd.to_numeric(df[c_pct], errors="coerce")
    ok = (pv > 0) & (cst > 0) & (pct > 0)
    if not ok.any():
        return DIVISOR_NETO_RESPALDO
    d = float((pv[ok] * pct[ok] / cst[ok]).median())
    return d if 1.0 < d < 2.0 else DIVISOR_NETO_RESPALDO


def tasa_igv():
    """El IGV que queda dentro del divisor, una vez sacado el recargo."""
    return max(divisor_neto() - 1 - TASA_RECARGO, 0.0)


# Conversión de la unidad de KARDEX a la de COSTEO cuando el insumo no
# aparece en ninguna receta de venta: la misma que usa el sistema en esos
# pares (1.255 filas KILOS→GRAMOS y 480 LITROS→MILILITROS con FACTOR 1000).
_CONVERSION_ESTANDAR = {"KILOS": ("GRAMOS", 1000.0),
                        "LITROS": ("MILILITROS", 1000.0)}


@st.cache_data(ttl=300, show_spinner=False)
def unidades_de_costeo():
    """{COD INS: (UNID COSTO, FACTOR)} tal como lo usan las recetas de
    venta: el par más frecuente de cada insumo. `P.UNIT COSTO` es
    exactamente `PREC PROM / FACTOR` en todo el parquet (medido)."""
    df = _cargar_reporte(ARCHIVO_RECETAVENTA)
    if df is None or df.empty:
        return {}
    c_ins = _resolver(df, ["COD INS", "Cod Ins"])
    c_und = _resolver(df, ["UNID COSTO", "Unid Costo"])
    c_fac = _resolver(df, ["FACTOR", "Factor"])
    if not (c_ins and c_und and c_fac):
        return {}
    d = pd.DataFrame({
        "cod": df[c_ins].astype(str),
        "und": df[c_und].astype(str).str.strip(),
        "fac": pd.to_numeric(df[c_fac], errors="coerce"),
    })
    d = d[(d["und"] != "") & (d["fac"] > 0) & (d["cod"].str.strip() != "")]
    if d.empty:
        return {}
    par = (d.groupby(["cod", "und", "fac"]).size().rename("n").reset_index()
           .sort_values("n", ascending=False).drop_duplicates("cod"))
    return {c: (u, float(f)) for c, u, f in zip(par["cod"], par["und"], par["fac"])}


@st.cache_data(ttl=300, show_spinner=False)
def catalogo_insumos():
    """Artículos de almacén desde inventariovalorizado.parquet, con unidad
    y precio en la unidad de COSTEO de las recetas (ver abajo).

    OJO con `Activo` en este parquet: a diferencia de recetabase/recetaventa
    (con sus 4 formatos confirmados contra R2 real, ver `_activo()` arriba y
    la regla #97), NO se verificó si trae una columna de activo/inactivo ni
    en qué formato. Candidatos razonables + degradación silenciosa si no
    aparece — probado contra R2 real: ningún candidato matcheó y la insignia
    simplemente no sale (regla #100)."""
    df = _cargar_reporte(ARCHIVO_INVENTARIO)
    if df is None or df.empty:
        return None

    col_cod = _resolver(df, ["Codigo Producto", "Código Producto", "COD_PRODUCTO"])
    col_nombre = _resolver(df, ["Nombre Producto", "NOMBRE_PRODUCTO"])
    col_unidad = _resolver(df, ["Unidad Kardex", "UNIDAD_KARDEX", "Unidad"])
    col_precio = _resolver(df, ["Precio Promedio", "PRECIO PROMEDIO", "Precio"])
    col_activo = _resolver(df, ["Activo", "ACTIVO", "Estado"])
    if not (col_cod and col_nombre and col_precio):
        return None

    out = pd.DataFrame({
        "cod": df[col_cod].astype(str),
        "nombre": df[col_nombre].astype(str),
        "unidad": df[col_unidad].astype(str) if col_unidad else "unidad",
        "precio": pd.to_numeric(df[col_precio], errors="coerce").fillna(0.0),
    })
    # En la unidad de COSTEO de las recetas (GRAMOS, MILILITROS, ONZAS…) y
    # no en la de kardex (2026-09-24, a pedido: «las unidades deben estar
    # tal cual el sistema»). Antes el buscador agregaba en KILOS a S/ 38 el
    # kilo, y 3 g de pimienta se escribían 0,003 — y el simulador de
    # Composición mezclaba ese precio por kilo con recetas en gramos.
    costeo = unidades_de_costeo()
    unidades, factores = [], []
    for cod, und in zip(out["cod"], out["unidad"].str.strip()):
        par = costeo.get(cod) or _CONVERSION_ESTANDAR.get(und.upper())
        unidades.append(par[0] if par else und)
        factores.append(par[1] if par else 1.0)
    out["unidad"] = unidades
    out["precio"] = out["precio"] / pd.Series(factores, index=out.index)
    out["activo"] = _activo(df[col_activo]) if col_activo else None
    # inventariovalorizado.parquet trae más de una fila para el mismo código
    # (confirmado en vivo 2026-08-13: "Sal De Mesa" 0000460 repetido) — sin
    # este drop_duplicates, `_buscador_catalogo` arma dos botones con la
    # MISMA key (`add_<cod>`) y Streamlit revienta con
    # StreamlitDuplicateElementKey en cuanto ambas filas caen dentro del
    # mismo resultado de búsqueda.
    out = out.drop_duplicates(subset="cod", keep="first").reset_index(drop=True)
    return out
