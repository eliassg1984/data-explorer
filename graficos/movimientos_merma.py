"""graficos.movimientos_merma — las tres vistas de MERMA de Movimientos ›
Porcionamientos (2026-10-08, regla #615): «Para revisar», «Rendimiento por
producto» y «Proveedor por kg útil». Aprobadas sobre un mockup con los
datos reales, a partir del «Reporte de Mermas» del Almacén.

EL REPORTE DEL ALMACÉN es `SpReporteMerma`: la cabecera de cada
porcionamiento procesado (`MPORCIONAMIENTO`, estado 02) por su fecha de
registro, agrupada por área › familia › subfamilia › producto, con la merma
valorizada al PRECIO PROMEDIO DE HOY del producto (`vProducto.
nPrecioPromedio`) — no al que tenía el día que se porcionó. Septiembre
2026: 267 porcionamientos, 627,77 de merma, S/ 20.602,20, y la app da lo
mismo (`movimientos_periodo.a_precio_de_hoy`). Al costo del día —el de los
cortes, el mismo con que el kardex descargó el insumo— son S/ 20.413,15.
Las dos se eligen en «Filtros» (`selector_valorizacion`); abre como el
Almacén, a pedido.

LO QUE AGREGAN LAS TRES VISTAS, que el reporte no tiene:

    Para revisar      los porcionamientos del rango que se salen de lo
                      normal para su MISMO producto (la mitad central de
                      sus porcionamientos de los últimos 18 meses), o que
                      traen un error de registro: un corte sin peso (el
                      Almacén cuenta ese peso como merma y lo valora en 0),
                      merma cero en un producto que siempre pierde, un costo
                      lejos de lo pagado, una fecha anterior a su número.
    Rendimiento       un producto en el tiempo: el % de merma de cada
                      porcionamiento sobre su rango normal, y el costo por
                      unidad que entró contra el precio de hoy; al lado, los
                      productos cuya merma cambió en los últimos 90 días.
    Proveedor         el costo por kg ÚTIL —lo pagado ÷ lo que queda después
                      de la merma— de cada proveedor del mismo producto.

EL PROVEEDOR ES UNA ATRIBUCIÓN, no un dato: el Almacén no guarda de qué
lote salió lo porcionado. Es el de la última compra del producto hasta 45
días antes (`con_proveedor`, sobre `compras.parquet`), y el filtro «un solo
proveedor en los 21 días previos» deja los casos sin ambigüedad (el 62 %):
con él el orden de los proveedores no cambió en ninguno de los productos
medidos. Cruzar con el kardex del día no lo afina barato: las compras
entran al almacén central y llegan a Producción por requerimiento, así que
el lote saldría de un FIFO de dos niveles. En esta vista la merma va
SIEMPRE al costo del día: a precio de hoy todos los proveedores costarían
lo mismo.

Las cuentas son puras y las vigila `test_graficos.py::_pruebas_merma`.
"""

import hashlib
import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data
from cortes import MESES_ABR_ES
from tema import (
    ACENTO, AJUSTE_ALERTA_BORDE, AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO,
    AJUSTE_CRIT_BORDE, AJUSTE_CRIT_FONDO, AJUSTE_CRIT_TEXTO, AJUSTE_NEG,
    AJUSTE_NEG_TEXTO, AJUSTE_POS_TEXTO, GRIS_BORDE, GRIS_FONDO_CABECERA,
    GRIS_LINEA, GRIS_TEXTO, LAVANDA_FILA, LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import _compras_layout, _resolver
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.movimientos_periodo import (
    a_precio_de_hoy, lineas_porcionamientos, unidad_corta,
)

# ── La valorización (el selector de «Filtros») ─────────────────────────────
VALOR_HOY = "Precio de hoy"
VALOR_DIA = "Costo del día"
K_VALOR = "mov_porc_valor"

# ── Las tarjetas: el prefijo `ajuste_graf_card_izq_` les da el marco ───────
CARD_REV = "ajuste_graf_card_izq_mov_merma_rev"
CARD_REND = "ajuste_graf_card_izq_mov_merma_rend"
CARD_PROV = "ajuste_graf_card_izq_mov_merma_prov"

# ── Los criterios, medidos sobre los porcionamientos de abr 2025 – sep 2026
DIAS_NORMAL = 540
"""Lo NORMAL de un producto sale de sus porcionamientos de los últimos 18
meses, contados hacia atrás desde el fin del rango."""
N_MIN_NORMAL = 8
"""Con menos porcionamientos que esto, un producto no tiene «normal»."""
MARGEN_MIN = 0.10
"""Fuera de lo normal es más allá de dos veces el rango intercuartil por
encima o por debajo de él, y nunca menos de 10 puntos: con un rango
angosto (el lomo, 8 puntos) un 2 % de más no es una alarma."""
MERMA_TIPICA_MIN = 0.05
"""«Sin merma registrada» sólo se marca en un producto que suele perder al
menos esto: el asado de tira o la pierna se porcionan sin merma siempre."""
COSTO_FUERA = (0.6, 1.6)
"""El costo por unidad del día contra la última compra: fuera de esto, el
porcionamiento se valorizó con un precio que no es el que se pagó."""
DIAS_RECIENTES = 90
DIAS_PROVEEDOR = 45
DIAS_UNICO = 21
MIN_PORC_PROVEEDOR = 5
VENTANAS = {"6 meses": 6, "12 meses": 12, "18 meses": 18}

MARCAS = {
    "alta": ("Merma muy alta", "crit"),
    "sinpeso": ("Corte sin peso", "crit"),
    "cero": ("Sin merma registrada", "alerta"),
    "baja": ("Merma muy baja", "alerta"),
    "costo": ("Costo lejos de lo pagado", "info"),
    "fecha": ("Fecha anterior a su número", "info"),
}
"""Las marcas de «Para revisar», en el orden de su gravedad."""
MARCAS_DE_ENTRADA = ("alta", "sinpeso", "cero", "baja", "costo")
"""«Fecha anterior a su número» abre apagada: el cierre de mes se registra
así en tanda (15 en septiembre 2026) y taparía al resto."""

_COLOR_MARCA = {
    "crit": (AJUSTE_CRIT_FONDO, AJUSTE_CRIT_BORDE, AJUSTE_CRIT_TEXTO),
    "alerta": (AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_BORDE, AJUSTE_ALERTA_TEXTO),
    "info": (GRIS_FONDO_CABECERA, GRIS_BORDE, GRIS_TEXTO),
}


# ═══════════════════════════════════════════════════════════════════════════
# LAS CUENTAS (puras)
# ═══════════════════════════════════════════════════════════════════════════
def porcionamientos(d, cols):
    """`(base, cortes)`: una fila por porcionamiento con cantidad (`cant`
    en la unidad del producto inicial), `merma_cant`, `pct` y `costo_dia`;
    y los cortes. El grano es el de `lineas_porcionamientos` (regla #510):
    la cabecera UNA vez. Los de cantidad cero quedan fuera: no tienen %."""
    base, cortes = lineas_porcionamientos(d, **cols)
    base = base[base["cant"] > 0].copy()
    base["pct"] = base["merma_cant"] / base["cant"]
    return base.reset_index(drop=True), cortes


def valorizar(base, modo, precios=None):
    """`base` con `costo` (lo porcionado), `valor` (la merma) y `precio`
    (por unidad que entró) según `modo`: `VALOR_HOY` como el Reporte de
    Mermas del Almacén, `VALOR_DIA` al costo de los cortes. Sin `precios`,
    al costo del día."""
    if modo == VALOR_HOY and precios is not None:
        b = a_precio_de_hoy(base, precios)
    else:
        b = base.copy()
        b["costo"] = b["costo_dia"]
        b["valor"] = b["costo_dia"] * b["pct"]
    b["precio"] = (b["costo"] / b["cant"]).where(b["cant"] > 0).fillna(0.0)
    # Las dos, para quien muestre la que no se eligió.
    b["valor_dia"] = b["costo_dia"] * b["pct"]
    b["valor_hoy"] = (b["merma_cant"] * pd.to_numeric(
        b["cod"].map(precios), errors="coerce").fillna(0.0)
        if precios is not None else np.nan)
    return b


def normales(hist):
    """Por código de producto, cuántos porcionamientos tiene `hist` y el
    rango de su % de merma: `n`, `q1`, `med`, `q3`."""
    g = hist.groupby("cod")["pct"]
    return pd.DataFrame({"n": g.size(), "q1": g.quantile(0.25),
                         "med": g.median(), "q3": g.quantile(0.75)})


def marcar(base, norm, cortes):
    """`base` con lo normal de su producto y una columna booleana por marca
    (`m_alta`, `m_baja`, `m_cero`, `m_sinpeso`, `m_costo`, `m_fecha`). La
    marca de costo necesita `pcompra` (de `con_proveedor`); sin ella no se
    marca."""
    b = base.join(norm, on="cod")
    n = b["n"].fillna(0)
    ok = n >= N_MIN_NORMAL
    margen = np.maximum(2 * (b["q3"] - b["q1"]), MARGEN_MIN)
    con_merma = b["merma_cant"] > 0
    b["m_alta"] = ok & con_merma & (b["pct"] > b["q3"] + margen)
    b["m_baja"] = ok & con_merma & (b["pct"] < b["q1"] - margen)
    crudo = ~b["prod"].astype(str).str.startswith("(")
    b["m_cero"] = (ok & (b["merma_cant"] == 0) & crudo
                   & (b["med"] >= MERMA_TIPICA_MIN))
    sin_peso = cortes.loc[(cortes["cant"] > 0)
                          & (cortes["peso"].fillna(0) == 0), "doc"]
    b["m_sinpeso"] = b["doc"].isin(set(sin_peso))
    if "pcompra" in b.columns:
        r = (b["costo_dia"] / b["cant"]) / b["pcompra"]
        b["m_costo"] = (b["pcompra"] > 0) & (b["costo_dia"] > 0) & (
            (r < COSTO_FUERA[0]) | (r > COSTO_FUERA[1]))
    else:
        b["m_costo"] = False
    num = b["doc"].astype(str).str[:4]
    b["m_fecha"] = num.str.isdigit() & (num != b["fecha"].dt.strftime("%y%m"))
    return b


def impacto(b, marcas):
    """Lo que cuesta, en soles de la valorización de `b`, la marca más cara
    de cada porcionamiento entre las `marcas` pedidas: lo perdido de más (o
    de menos) contra lo normal, la merma que debió registrarse, o la merma
    entera si un corte sin peso la infló. Las de costo y fecha no tienen
    monto (0)."""
    vals = []
    if "alta" in marcas or "baja" in marcas:
        dif = (b["pct"] - b["med"]) * b["cant"] * b["precio"]
        if "alta" in marcas:
            vals.append(dif.where(b["m_alta"], 0.0))
        if "baja" in marcas:
            vals.append(dif.where(b["m_baja"], 0.0))
    if "cero" in marcas:
        vals.append((b["med"] * b["cant"] * b["precio"]).where(b["m_cero"], 0.0))
    if "sinpeso" in marcas:
        vals.append(b["valor"].where(b["m_sinpeso"], 0.0))
    if not vals:
        return pd.Series(0.0, index=b.index)
    m = pd.concat(vals, axis=1).fillna(0.0)
    pos = m.abs().to_numpy().argmax(axis=1)
    return pd.Series(m.to_numpy()[np.arange(len(m)), pos], index=b.index)


def compras_para_proveedor(c):
    """Las compras como las pide `con_proveedor`: `cod`, `f` (el día),
    `prov`, `pu` (soles por unidad) y `f_otro`, el último día ANTERIOR en
    que se compró ese producto a OTRO proveedor. Sin las columnas, None.

    `f_otro` sale por TRAMOS: ordenadas las compras de un producto por
    fecha, cada racha del mismo proveedor es un tramo, y lo de otro
    proveedor anterior a una compra es el final del tramo de antes."""
    cc = {k: _resolver(c, v) for k, v in {
        "cod": ["COD_PRODUCTO", "Cod producto", "Codigo producto"],
        "f": ["FECHA_EMISION_DOC", "Fecha documento"],
        "prov": ["NOMBRE_PROVEEDOR", "Nombre proveedor"],
        "cant": ["CANTIDAD_COMPRA", "Cantidad compra"],
        "val": ["VALOR_COMPRA", "Valor compra"]}.items()}
    if c is None or not all(cc.values()):
        return None
    t = pd.DataFrame({
        "cod": c[cc["cod"]].fillna("").astype(str).str.strip(),
        "f": pd.to_datetime(c[cc["f"]], errors="coerce").dt.normalize(),
        "prov": c[cc["prov"]].fillna("").astype(str).str.strip(),
        "cant": pd.to_numeric(c[cc["cant"]], errors="coerce"),
        "val": pd.to_numeric(c[cc["val"]], errors="coerce"),
    })
    t = t[(t["cant"] > 0) & (t["cod"] != "") & (t["prov"] != "")
          & t["f"].notna()].copy()
    t["pu"] = t["val"] / t["cant"]
    t["f"] = t["f"].astype("datetime64[ns]")
    t = t.sort_values(["cod", "f", "prov"], kind="stable").reset_index(drop=True)
    nuevo = (t["cod"] != t["cod"].shift()) | (t["prov"] != t["prov"].shift())
    t["tramo"] = nuevo.cumsum()
    tr = t.groupby("tramo").agg(cod=("cod", "first"), fin=("f", "max"))
    tr["otro"] = tr["fin"].shift().where(tr["cod"].eq(tr["cod"].shift()))
    t["f_otro"] = t["tramo"].map(tr["otro"])
    return t[["cod", "f", "prov", "pu", "f_otro"]]


def con_proveedor(base, compras):
    """`base` con el proveedor de la última compra del producto hasta
    `DIAS_PROVEEDOR` días antes (`prov`, `pcompra`, `dias` desde la compra)
    y `unico`: nadie más le vendió ese producto en los `DIAS_UNICO` días
    previos. Conserva el orden de `base`."""
    b = base.copy()
    b["_i"] = np.arange(len(b))
    b["_dia"] = b["fecha"].dt.normalize().astype("datetime64[ns]")
    b["cod"] = b["cod"].astype(str)
    if compras is None or compras.empty:
        b["prov"], b["pcompra"], b["dias"], b["unico"] = None, np.nan, np.nan, False
        return b.drop(columns=["_i", "_dia"])
    c = compras.assign(cod=compras["cod"].astype(str)).sort_values("f")
    m = pd.merge_asof(b.sort_values("_dia"), c, left_on="_dia", right_on="f",
                      by="cod", direction="backward",
                      tolerance=pd.Timedelta(days=DIAS_PROVEEDOR))
    m["dias"] = (m["_dia"] - m["f"]).dt.days
    m["unico"] = m["prov"].notna() & (
        m["f_otro"].isna()
        | (m["f_otro"] <= m["_dia"] - pd.Timedelta(days=DIAS_UNICO)))
    m = m.rename(columns={"pu": "pcompra"}).sort_values("_i")
    return m.drop(columns=["_i", "_dia", "f", "f_otro"]).reset_index(drop=True)


def _agregado(g):
    """Las sumas de un grupo de porcionamientos, por nombre."""
    return g.agg(n=("doc", "size"), cant=("cant", "sum"),
                 merma=("merma_cant", "sum"), costo=("costo", "sum"),
                 costo_dia=("costo_dia", "sum"))


def cambios(b, fin):
    """Por producto, la merma de los últimos `DIAS_RECIENTES` días antes de
    `fin` contra la del resto de `b`, con al menos `MIN_PORC_PROVEEDOR`
    porcionamientos en cada lado: `pct_ant`, `pct_rec`, `dpp` (puntos),
    `dprecio` (variación del costo del día por unidad) e `impacto` —lo que
    cuestan esos puntos sobre lo porcionado hace poco, en la valorización
    de `b`—, ordenados por `impacto` en valor absoluto."""
    rec = b["fecha"] >= fin - pd.Timedelta(days=DIAS_RECIENTES)
    r = _agregado(b[rec].groupby("cod"))
    a = _agregado(b[~rec].groupby("cod"))
    t = r.join(a, lsuffix="_rec", rsuffix="_ant", how="inner")
    t = t[(t["n_rec"] >= MIN_PORC_PROVEEDOR) & (t["n_ant"] >= MIN_PORC_PROVEEDOR)
          & (t["cant_rec"] > 0) & (t["cant_ant"] > 0)].copy()
    t["pct_rec"] = t["merma_rec"] / t["cant_rec"]
    t["pct_ant"] = t["merma_ant"] / t["cant_ant"]
    t["dpp"] = t["pct_rec"] - t["pct_ant"]
    pr, pa = t["costo_dia_rec"] / t["cant_rec"], t["costo_dia_ant"] / t["cant_ant"]
    t["dprecio"] = (pr / pa - 1).where(pa > 0)
    t["impacto"] = t["dpp"] * t["costo_rec"]
    t = t.reindex(t["impacto"].abs().sort_values(ascending=False).index)
    return t[["pct_ant", "pct_rec", "dpp", "dprecio", "impacto"]]


def por_proveedor(b, solo_unico=False):
    """Por proveedor (de `con_proveedor`), lo porcionado y su merma, al
    COSTO DEL DÍA: `n`, `cant`, `merma`, `costo`, `pct`, `pkg` (pagado por
    unidad), `util` (pagado por unidad que quedó) y `dias` (mediana de
    días entre la compra y el porcionamiento), del más barato por unidad
    útil al más caro."""
    x = b[b["prov"].notna()]
    if solo_unico:
        x = x[x["unico"]]
    x = x[x["costo_dia"] > 0]
    if x.empty:
        return pd.DataFrame(columns=["n", "cant", "merma", "costo", "pct",
                                     "pkg", "util", "dias"])
    g = x.groupby("prov")
    t = pd.DataFrame({"n": g.size(), "cant": g["cant"].sum(),
                      "merma": g["merma_cant"].sum(),
                      "costo": g["costo_dia"].sum(), "dias": g["dias"].median()})
    t["pct"] = t["merma"] / t["cant"]
    t["pkg"] = t["costo"] / t["cant"]
    t["util"] = (t["costo"] / (t["cant"] - t["merma"])).where(
        t["cant"] > t["merma"])
    # Los de pocos porcionamientos, al final: uno solo no dice nada.
    pocos = t["n"] < MIN_PORC_PROVEEDOR
    return t.assign(_p=pocos).sort_values(["_p", "util"]).drop(columns="_p")


def resumen_proveedores(b, solo_unico=False):
    """Por producto con al menos dos proveedores de `MIN_PORC_PROVEEDOR`
    porcionamientos o más: el mejor y el más caro por unidad útil y
    `extra`, lo pagado de más contra el mejor — Σ (útil del proveedor −
    útil del mejor) × lo que quedó de lo suyo. Del mayor al menor."""
    x = b[b["prov"].notna() & (b["costo_dia"] > 0)]
    if solo_unico:
        x = x[x["unico"]]
    if x.empty:
        return pd.DataFrame(columns=["mejor", "util_mejor", "peor",
                                     "util_peor", "extra", "provs"])
    g = x.groupby(["cod", "prov"])
    t = pd.DataFrame({"n": g.size(), "cant": g["cant"].sum(),
                      "merma": g["merma_cant"].sum(),
                      "costo": g["costo_dia"].sum()}).reset_index()
    t = t[(t["n"] >= MIN_PORC_PROVEEDOR) & (t["cant"] > t["merma"])].copy()
    t["queda"] = t["cant"] - t["merma"]
    t["util"] = t["costo"] / t["queda"]
    t["provs"] = t.groupby("cod")["prov"].transform("size")
    t = t[t["provs"] >= 2].copy()
    if t.empty:
        return pd.DataFrame(columns=["mejor", "util_mejor", "peor",
                                     "util_peor", "extra", "provs"])
    t["minimo"] = t.groupby("cod")["util"].transform("min")
    t["de_mas"] = (t["util"] - t["minimo"]) * t["queda"]
    mejor = t.loc[t.groupby("cod")["util"].idxmin()].set_index("cod")
    peor = t.loc[t.groupby("cod")["util"].idxmax()].set_index("cod")
    r = pd.DataFrame({
        "mejor": mejor["prov"], "util_mejor": mejor["util"],
        "peor": peor["prov"], "util_peor": peor["util"],
        "extra": t.groupby("cod")["de_mas"].sum(),
        "provs": t.groupby("cod")["prov"].size()})
    return r.sort_values("extra", ascending=False)


def por_mes(xs):
    """La merma y el costo del día de `xs`, mes a mes, ponderados por lo
    porcionado: `mes` (el día 15), `pct`, `pkg`."""
    if xs.empty:
        return pd.DataFrame(columns=["mes", "pct", "pkg"])
    g = xs.groupby(xs["fecha"].dt.to_period("M"))
    t = pd.DataFrame({"cant": g["cant"].sum(), "merma": g["merma_cant"].sum(),
                      "costo": g["costo_dia"].sum()})
    t["pct"] = t["merma"] / t["cant"]
    t["pkg"] = (t["costo"] / t["cant"]).where(t["costo"] > 0)
    t["mes"] = t.index.to_timestamp() + pd.Timedelta(days=14)
    return t.reset_index(drop=True)[["mes", "pct", "pkg"]]


# ═══════════════════════════════════════════════════════════════════════════
# LO QUE LEEN DE AFUERA
# ═══════════════════════════════════════════════════════════════════════════
def selector_valorizacion():
    """«Valorizar la merma», en el panel «Filtros» de Movimientos. Manda
    sobre la tarjeta «Porcionamientos» y sobre «Para revisar» y
    «Rendimiento»; abre como el Reporte de Mermas del Almacén, a pedido."""
    st.markdown('<div class="filtro-rotulo filtro-mov_porc_valor">Valorizar '
                'la merma</div>', unsafe_allow_html=True)
    st.segmented_control(
        "Valorizar la merma", [VALOR_HOY, VALOR_DIA], default=VALOR_HOY,
        required=True, key=K_VALOR, label_visibility="collapsed",
        help=("**Precio de hoy**: la merma × el precio promedio actual del "
              "producto, como el «Reporte de Mermas» del Almacén — reimpreso "
              "otro día, da otro monto. **Costo del día**: lo que costaba el "
              "producto el día que se porcionó, el mismo precio con que el "
              "kardex lo descargó."))


def valorizacion():
    """La valorización elegida (`VALOR_HOY` por defecto)."""
    v = st.session_state.get(K_VALOR)
    return v if v in (VALOR_HOY, VALOR_DIA) else VALOR_HOY


def precios_hoy():
    """Código → precio promedio de hoy, del maestro que trae el inventario
    valorizado: es el `vProducto.nPrecioPromedio` del Almacén, uno por
    producto (comparado contra el SP en los 267 porcionamientos de sep
    2026: igual en todos). None si no se puede leer."""
    inv = data.cargar(data.REPORTES["Inventario Valorizado"]["archivo"])
    if inv is None or inv.empty:
        return None
    c_cod = _resolver(inv, ["CODIGO PRODUCTO", "Codigo Producto"])
    c_p = _resolver(inv, ["PRECIO PROMEDIO", "Precio Promedio"])
    if not (c_cod and c_p):
        return None
    t = pd.DataFrame({"cod": inv[c_cod].astype(str).str.strip(),
                      "p": pd.to_numeric(inv[c_p], errors="coerce")})
    return t.dropna().drop_duplicates("cod").set_index("cod")["p"]


def _compras():
    try:
        return compras_para_proveedor(data.cargar("compras.parquet"))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# PIEZAS DE DIBUJO
# ═══════════════════════════════════════════════════════════════════════════
def _s(v, dec=0):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{'−' if v < 0 else ''}S/ {abs(v):,.{dec}f}"


def _p(v, dec=1):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v * 100:.{dec}f}%"


def _pp(v):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{'+' if v >= 0 else '−'}{abs(v) * 100:.1f} pp"


def _c(v):
    if v is None or not np.isfinite(v):
        return "—"
    return f"{v:,.3f}".rstrip("0").rstrip(".")


def _rot_valor(modo):
    return "a precio de hoy" if modo == VALOR_HOY else "al costo del día"


def _titulo(texto, sub="", fecha=None):
    """El título de una tarjeta. Con `fecha` (el que dibuja el botón de
    fecha de la sección, regla #617), comparten renglón."""
    st.markdown(CSS_TITULOS_DRILL, unsafe_allow_html=True)
    tit = (f'<div class="inv-rank-tit">{html.escape(texto)}'
           + (f'<span class="inv-rank-tit-n">{html.escape(sub)}</span>'
              if sub else "") + "</div>")
    if fecha is not None:
        fecha(tit)
    else:
        st.markdown(tit, unsafe_allow_html=True)


def _tiles(items):
    """Una fila de recuadros `(rótulo, valor, debajo)`; `debajo` puede
    traer HTML (ya escapado)."""
    celdas = "".join(
        f'<div style="flex:1 1 140px;min-width:0;background:{LAVANDA_FILA};'
        f'border:1px solid {GRIS_LINEA};border-radius:8px;padding:6px 10px">'
        f'<div style="font-size:11px;color:{GRIS_TEXTO}">{html.escape(r)}</div>'
        f'<div style="font-size:17px;font-weight:700;color:{TEXTO_PRINCIPAL}">'
        f'{html.escape(v)}</div>'
        f'<div style="font-size:11px;color:{GRIS_TEXTO}">{d}</div></div>'
        for r, v, d in items)
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:8px;'
                f'margin-bottom:4px">{celdas}</div>', unsafe_allow_html=True)


def _color_signo(v, subir_es_malo=True):
    if v is None or not np.isfinite(v) or abs(v) < 1e-9:
        return GRIS_TEXTO
    return AJUSTE_NEG_TEXTO if (v > 0) == subir_es_malo else AJUSTE_POS_TEXTO


def _aviso(clave, texto):
    fondo, borde, color = _COLOR_MARCA[MARCAS[clave][1]]
    st.markdown(
        f'<div style="background:{fondo};border:1px solid {borde};color:{color};'
        f'border-radius:8px;padding:6px 10px;font-size:13px;margin:2px 0">'
        f'<b>{html.escape(MARCAS[clave][0])}.</b> {html.escape(texto)}</div>',
        unsafe_allow_html=True)


def _key_tabla(base, codigos):
    firma = hashlib.md5("|".join(map(str, codigos)).encode("utf-8")).hexdigest()[:12]
    return f"{base}_{firma}"


def _fila_elegida(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _foco_anterior(base, k_foco):
    """Lo que la tabla `base` tenía elegido en la corrida anterior, a
    `k_foco`. Se lee ANTES de dibujar: la selección es de la KEY y la key
    cambia con las filas (el criterio de la Carta costeada, regla #556)."""
    ss = st.session_state
    key, codigos = ss.get(f"_{base}_key"), ss.get(f"_{base}_codigos") or []
    fila = _fila_elegida(ss.get(key)) if key else None
    if fila is not None and 0 <= fila < len(codigos):
        ss[k_foco] = codigos[fila]


def _tabla_elegible(base, sty, codigos, pos, alto, cfg, requerida=True):
    ss = st.session_state
    key = _key_tabla(base, codigos)
    ss[f"_{base}_key"], ss[f"_{base}_codigos"] = key, list(codigos)
    kw = dict(key=key, on_select="rerun", hide_index=True, row_height=27,
              height=alto, column_config=cfg)
    if requerida:
        kw.update(selection_mode="single-row-required",
                  selection_default={"selection": {"rows": [pos]}})
    else:
        kw.update(selection_mode="single-row")
    st.dataframe(sty, **kw)


def _resaltar(pos):
    return lambda r: ([f"background-color: {LAVANDA_FONDO}"] * len(r)
                      if r.name == pos else [""] * len(r))


def _alto_tabla(n, tope):
    return min(tope, alturas.por_filas(n, px_fila=27, extra=38, minimo=0))


def _ventana(key, fin):
    """El selector «6/12/18 meses» de una tarjeta y `(ini, fin)`: la
    ventana termina en `fin`. Es la fecha PROPIA de «Rendimiento» y de
    «Proveedor»: desde el 2026-10-08 (regla #617) `fin` es el último día con
    datos, porque la franja de Movimientos ya no tiene calendario."""
    v = st.segmented_control("Ventana", list(VENTANAS), default="12 meses",
                             required=True, key=key,
                             label_visibility="collapsed")
    meses = VENTANAS.get(v, 12)
    return fin - pd.DateOffset(months=meses), fin


def _ticks_meses(ini, fin):
    paso = 1 if (fin - ini).days <= 200 else 2
    vals, rots = [], []
    m = pd.Timestamp(ini.year, ini.month, 1)
    while m < fin:
        if m >= ini:
            vals.append(m)
            rots.append(f"{MESES_ABR_ES[m.month - 1]} {m.year % 100:02d}")
        m = m + pd.DateOffset(months=paso)
    return vals, rots


# ═══════════════════════════════════════════════════════════════════════════
# 1. PARA REVISAR
# ═══════════════════════════════════════════════════════════════════════════
def _motivo(f, clave, u):
    if clave in ("alta", "baja"):
        return (f"Perdió {_p(f['pct'])}; lo normal para este producto es "
                f"entre {_p(f['q1'])} y {_p(f['q3'])} (mediana {_p(f['med'])}).")
    if clave == "cero":
        return (f"No registró merma y este producto suele perder "
                f"{_p(f['med'])}: unos {_c(f['med'] * f['cant'])} {u} que no "
                "aparecen.")
    if clave == "sinpeso":
        return ("Un corte se registró con cantidad pero sin peso. El Almacén "
                "cuenta ese peso como merma y lo valora en S/ 0: la merma "
                "sale inflada y el corte entra sin costo.")
    if clave == "costo":
        return (f"Se valorizó a {_s(f['costo_dia'] / f['cant'], 2)} por {u} y "
                f"la última compra fue a {_s(f['pcompra'], 2)}.")
    if clave == "fecha":
        num = str(f["doc"])
        return (f"Su número es de {MESES_ABR_ES[int(num[2:4]) - 1]} "
                f"20{num[:2]} y se registró el {f['fecha']:%d/%m/%Y}: el "
                "reporte lo cuenta en el mes del registro y el kardex, por "
                "su fecha de proceso, puede llevarlo a otro.")
    return ""


def tarjeta_revisar(d_rango, d_hist, cols, rango, fecha=None):
    """La sección «Para revisar». `d_rango` son las filas del parquet en el
    rango de la sección; `d_hist`, las de todo el parquet (con el chip
    «Sub Almacén» aplicado a las dos), de donde sale lo normal. `fecha`
    dibuja el botón de fecha de la sección junto al título (regla #617)."""
    with st.container(border=True, key=CARD_REV):
        modo = valorizacion()
        base, cortes = porcionamientos(d_rango, cols)
        if base.empty:
            _titulo("Porcionamientos para revisar", fecha=fecha)
            st.info("Sin porcionamientos en estas fechas.")
            return
        fin = rango[1] if rango else base["fecha"].max() + pd.Timedelta(days=1)
        hist, _ = porcionamientos(
            d_hist[(d_hist["_fecha"] < fin)
                   & (d_hist["_fecha"] >= fin - pd.Timedelta(days=DIAS_NORMAL))],
            cols)
        b = con_proveedor(base, _compras())
        b = marcar(valorizar(b, modo, precios_hoy()), normales(hist), cortes)
        cuenta = {k: int(b[f"m_{k}"].sum()) for k in MARCAS}
        _titulo("Porcionamientos para revisar",
                f"{len(b):,} en el rango · lo normal: sus últimos 18 meses",
                fecha=fecha)
        elegidas = st.pills(
            "Qué mostrar", list(MARCAS), selection_mode="multi",
            default=list(MARCAS_DE_ENTRADA), key="mov_merma_rev_marcas",
            format_func=lambda k: f"{MARCAS[k][0]} · {cuenta[k]}",
            label_visibility="collapsed") or []
        hay = np.zeros(len(b), dtype=bool)
        for k in elegidas:
            hay |= b[f"m_{k}"].to_numpy()
        x = b[hay].copy()
        if x.empty:
            st.info("Nada que revisar con estas marcas en el rango.")
            return
        x["impacto"] = impacto(x, elegidas)
        x = x.reindex(x["impacto"].abs().sort_values(ascending=False,
                                                     kind="stable").index)
        x = x.reset_index(drop=True)
        docs = x["doc"].astype(str).tolist()
        k_foco = "_mov_merma_rev_foco"
        _foco_anterior("mov_merma_rev_tabla", k_foco)
        foco = st.session_state.get(k_foco)
        pos = docs.index(foco) if foco in docs else 0

        tabla = pd.DataFrame({
            "Porcionamiento": "PO-" + x["doc"].astype(str),
            "Fecha": x["fecha"].dt.strftime("%d/%m"),
            "Producto": x["prod"],
            "Merma": x["pct"],
            "Lo normal": [f"{_p(a, 0)}–{_p(c, 0)}" if np.isfinite(a) else "—"
                          for a, c in zip(x["q1"].fillna(np.nan),
                                          x["q3"].fillna(np.nan))],
            "Impacto": x["impacto"],
            "Motivo": [" · ".join(MARCAS[k][0] for k in MARCAS
                                  if k in elegidas and r[f"m_{k}"])
                       for _, r in x.iterrows()],
            "Usuario": x["tipo"],
        })
        sty = (tabla.style.format({"Merma": lambda v: _p(v),
                                   "Impacto": lambda v: _s(v) if v else "—"})
               .apply(_resaltar(pos), axis=1))
        # columnas-internas: la lista y la ficha del elegido, en la misma
        # tarjeta; la ficha necesita lugar para sus cortes.
        c_lista, c_ficha = st.columns([1.5, 1], gap="medium")
        with c_lista:
            _tabla_elegible(
                "mov_merma_rev_tabla", sty, docs, pos,
                _alto_tabla(len(tabla), alturas.MERMA_TABLA),
                {"Producto": st.column_config.TextColumn(width="medium"),
                 "Impacto": st.column_config.Column(
                     help=f"Lo que cuesta, {_rot_valor(modo)}: la merma de "
                          "más (o de menos) contra la mediana del producto, "
                          "la que debió registrarse, o la merma entera si un "
                          "corte sin peso la infló."),
                 "Lo normal": st.column_config.Column(
                     help="La mitad central de los porcionamientos del "
                          "producto en los últimos 18 meses.")})
            st.caption(f"Valorizado {_rot_valor(modo)} (se cambia en "
                       "«Filtros»). Clic en una fila para ver sus cortes.")
        with c_ficha:
            _ficha(x.iloc[pos], cortes, modo)


def _ficha(f, cortes, modo):
    u = unidad_corta(f["unid"])
    st.markdown(
        f'<div style="font-weight:700;font-size:14px">PO-{html.escape(str(f["doc"]))}'
        f' · {html.escape(str(f["prod"]))}</div>'
        f'<div style="font-size:12px;color:{GRIS_TEXTO}">'
        f'{f["fecha"]:%d/%m/%Y %H:%M} · {html.escape(str(f["area"]))} · '
        f'{html.escape(str(f["tipo"]))}'
        + (f' · última compra a {html.escape(str(f["prov"]))}, '
           f'{int(f["dias"])} día{"" if int(f["dias"]) == 1 else "s"} antes'
           if isinstance(f.get("prov"), str) and np.isfinite(f["dias"]) else "")
        + "</div>", unsafe_allow_html=True)
    otro = (f"al costo del día: {_s(f['valor_dia'], 2)}" if modo == VALOR_HOY
            else f"a precio de hoy: {_s(f['valor_hoy'], 2)}")
    _tiles([("Entró", f"{_c(f['cant'])} {u}", ""),
            ("Merma", f"{_c(f['merma_cant'])} {u}", _p(f["pct"])),
            ("Valor de la merma", _s(f["valor"], 2), otro)])
    for k in MARCAS:
        if f[f"m_{k}"]:
            _aviso(k, _motivo(f, k, u))
    cs = cortes[cortes["doc"].astype(str) == str(f["doc"])]
    if cs.empty:
        st.caption("Sin cortes registrados.")
        return
    t = pd.DataFrame({
        "Corte": cs["fin"].tolist(),
        "Cantidad": [f"{_c(c)} {unidad_corta(un)}"
                     for c, un in zip(cs["cant"], cs["unid"])],
        f"Peso ({u})": cs["peso"].fillna(0).tolist(),
        "S/ prom.": cs["pprom"].fillna(0).tolist(),
    })
    sin_peso = ((cs["cant"] > 0) & (cs["peso"].fillna(0) == 0)).tolist()
    sty = (t.style.format({f"Peso ({u})": _c, "S/ prom.": "{:,.2f}"})
           .apply(lambda r: ([f"color: {AJUSTE_NEG_TEXTO}; font-weight: 600"]
                             * len(r) if sin_peso[r.name] else [""] * len(r)),
                  axis=1))
    st.dataframe(sty, hide_index=True, row_height=27,
                 height=_alto_tabla(len(t), alturas.MERMA_CORTES),
                 column_config={"Corte": st.column_config.TextColumn(
                     width="medium")})


# ═══════════════════════════════════════════════════════════════════════════
# 2. RENDIMIENTO POR PRODUCTO
# ═══════════════════════════════════════════════════════════════════════════
_K_PROD = "_mov_merma_prod"
_K_VER = "_mov_merma_prod_ver"


def _al_elegir_producto(key):
    st.session_state[_K_PROD] = st.session_state.get(key)


def _fig_merma(xs, norm, mes, ini, fin, u):
    fig = go.Figure()
    if norm is not None and np.isfinite(norm["q1"]):
        fig.add_scatter(x=[ini, fin], y=[norm["q3"]] * 2, mode="lines",
                        line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=[ini, fin], y=[norm["q1"]] * 2, mode="lines",
                        line=dict(width=0), fill="tonexty",
                        fillcolor=LAVANDA_FONDO, hoverinfo="skip",
                        showlegend=False)
    raros = xs["m_alta"] | xs["m_baja"] | xs["m_cero"] | xs["m_sinpeso"]
    for sub, color, simb, tam in ((xs[~raros], ACENTO, "circle", 7),
                                  (xs[raros], AJUSTE_NEG, "diamond", 9)):
        if sub.empty:
            continue
        txt = [f"PO-{d} · {f:%d/%m/%Y}<br>{_c(m)} de {_c(c)} {u} · <b>{_p(p)}</b>"
               f"<br>{html.escape(str(us))}"
               + (f" · {html.escape(pv)}" if isinstance(pv, str) else "")
               for d, f, m, c, p, us, pv in zip(
                   sub["doc"], sub["fecha"], sub["merma_cant"], sub["cant"],
                   sub["pct"], sub["tipo"], sub["prov"])]
        fig.add_scatter(x=sub["fecha"], y=sub["pct"], mode="markers",
                        marker=dict(size=tam, color=color, symbol=simb,
                                    opacity=0.6 if simb == "circle" else 1),
                        text=txt, hovertemplate="%{text}<extra></extra>",
                        showlegend=False)
    if not mes.empty:
        fig.add_scatter(
            x=mes["mes"], y=mes["pct"], mode="lines+markers",
            line=dict(color=TEXTO_PRINCIPAL, width=2),
            marker=dict(size=5, color=TEXTO_PRINCIPAL),
            text=[f"{MESES_ABR_ES[m.month - 1]} {m.year}" for m in mes["mes"]],
            hovertemplate="%{text}: %{y:.1%} en el mes<extra></extra>",
            showlegend=False)
    _compras_layout(fig, alto=alturas.MERMA_FIG)
    vals, rots = _ticks_meses(ini, fin)
    fig.update_layout(margin=dict(l=44, r=8, t=24, b=24),
                      title=dict(text="Merma por porcionamiento",
                                 font=dict(size=12, color=GRIS_TEXTO), x=0))
    fig.update_xaxes(type="date", range=[ini, fin], tickvals=vals,
                     ticktext=rots, fixedrange=True)
    fig.update_yaxes(tickformat=".0%", showticklabels=True, rangemode="tozero",
                     fixedrange=True)
    return fig


def _fig_precio(xs, mes, p_hoy, ini, fin, u):
    fig = go.Figure()
    x = xs[xs["costo_dia"] > 0]
    if not x.empty:
        pk = x["costo_dia"] / x["cant"]
        fig.add_scatter(
            x=x["fecha"], y=pk, mode="markers",
            marker=dict(size=6, color=ACENTO, opacity=0.45),
            text=[f"PO-{d} · {f:%d/%m/%Y}<br>{_s(v, 2)} por {u}"
                  + (f"<br>{html.escape(pv)}" if isinstance(pv, str) else "")
                  for d, f, v, pv in zip(x["doc"], x["fecha"], pk, x["prov"])],
            hovertemplate="%{text}<extra></extra>", showlegend=False)
    m = mes.dropna(subset=["pkg"])
    if not m.empty:
        fig.add_scatter(
            x=m["mes"], y=m["pkg"], mode="lines+markers",
            line=dict(color=TEXTO_PRINCIPAL, width=2),
            marker=dict(size=5, color=TEXTO_PRINCIPAL),
            text=[f"{MESES_ABR_ES[t.month - 1]} {t.year}" for t in m["mes"]],
            hovertemplate="%{text}: S/ %{y:,.2f}<extra></extra>",
            showlegend=False)
    if p_hoy and np.isfinite(p_hoy):
        fig.add_scatter(x=[ini, fin], y=[p_hoy] * 2, mode="lines",
                        line=dict(color=AJUSTE_NEG, width=1.5, dash="dash"),
                        hovertemplate=f"Precio promedio de hoy: {_s(p_hoy, 2)}"
                                      "<extra></extra>", showlegend=False)
    _compras_layout(fig, alto=alturas.MERMA_FIG_PRECIO)
    vals, rots = _ticks_meses(ini, fin)
    fig.update_layout(margin=dict(l=44, r=8, t=24, b=24),
                      title=dict(text=f"Costo del día por {u} · cortada: "
                                      "precio promedio de hoy",
                                 font=dict(size=12, color=GRIS_TEXTO), x=0))
    fig.update_xaxes(type="date", range=[ini, fin], tickvals=vals,
                     ticktext=rots, fixedrange=True)
    fig.update_yaxes(tickprefix="S/ ", showticklabels=True, fixedrange=True)
    return fig


def tarjeta_rendimiento(d_hist, cols, rango):
    """La sección «Rendimiento por producto». `d_hist` es el parquet entero
    con el chip «Sub Almacén»; la ventana la elige la tarjeta y termina
    donde termina `rango` o, sin él, en el último día con datos (regla
    #617: Movimientos lo llama sin rango)."""
    with st.container(border=True, key=CARD_REND):
        modo = valorizacion()
        precios = precios_hoy()
        fin_f = (rango[1] if rango
                 else d_hist["_fecha"].max() + pd.Timedelta(days=1))
        # columnas-internas: el título a la izquierda, la ventana y el
        # producto a la derecha, en el mismo renglón.
        c_tit, c_ven, c_prod = st.columns([1.2, 0.9, 1.5],
                                          vertical_alignment="center")
        with c_ven:
            ini, fin = _ventana("mov_merma_rend_ventana", fin_f)
        todo, cortes = porcionamientos(
            d_hist[(d_hist["_fecha"] >= fin - pd.Timedelta(days=DIAS_NORMAL))
                   & (d_hist["_fecha"] < fin)], cols)
        if todo.empty:
            with c_tit:
                _titulo("Rendimiento por producto")
            st.info("Sin porcionamientos en la ventana.")
            return
        norm = normales(todo)
        b = valorizar(todo[todo["fecha"] >= ini], modo, precios)
        b = marcar(con_proveedor(b, _compras()), norm, cortes)
        ch = cambios(b, fin)

        # El clic en «Productos que cambiaron» manda sobre el desplegable.
        ss = st.session_state
        k_ult = "_mov_merma_cambio_ult"
        _foco_anterior("mov_merma_cambios", "_mov_merma_cambio_clic")
        clic = ss.pop("_mov_merma_cambio_clic", None)
        if clic is not None and clic != ss.get(k_ult):
            ss[_K_PROD] = clic
        ss[k_ult] = clic if clic is not None else ss.get(k_ult)

        orden = (b.groupby("cod")["valor"].sum().sort_values(ascending=False))
        opciones = orden.index.tolist()
        nombres = b.drop_duplicates("cod").set_index("cod")["prod"]
        prod = ss.get(_K_PROD)
        if prod not in opciones:
            prod = ch.index[0] if len(ch) else opciones[0]
            ss[_K_PROD] = prod
        ver = ss.get(_K_VER, 0)
        wkey = f"mov_merma_rend_prod_{ver}"
        if wkey in ss and ss[wkey] != prod:
            ver += 1
            ss[_K_VER] = ver
            wkey = f"mov_merma_rend_prod_{ver}"
        with c_tit:
            _titulo("Rendimiento por producto")
        with c_prod:
            st.selectbox(
                "Producto", opciones, index=opciones.index(prod), key=wkey,
                format_func=lambda c: f"{nombres.get(c, c)} · {_s(orden.get(c, 0))}",
                on_change=_al_elegir_producto, args=(wkey,),
                label_visibility="collapsed")

        xs = b[b["cod"] == prod]
        u = unidad_corta(xs["unid"].iloc[0]) if len(xs) else ""
        rec = xs["fecha"] >= fin - pd.Timedelta(days=DIAS_RECIENTES)

        def _pct(z):
            return z["merma_cant"].sum() / z["cant"].sum() if z["cant"].sum() else np.nan

        def _pk(z):
            return z["costo_dia"].sum() / z["cant"].sum() if z["cant"].sum() else np.nan

        p_r, p_a = _pct(xs[rec]), _pct(xs[~rec])
        k_r, k_a = _pk(xs[rec]), _pk(xs[~rec])
        queda = (xs["cant"] - xs["merma_cant"]).sum()
        p_hoy = float(precios.get(prod, np.nan)) if precios is not None else np.nan
        _var = (lambda a, b_: "" if not (np.isfinite(a) and np.isfinite(b_))
                else (f'<span style="color:{_color_signo(a - b_)};font-weight:600">'))
        _tiles([
            ("Merma de la ventana", _p(_pct(xs)),
             f"{len(xs)} porcionamientos · {_c(xs['cant'].sum())} {u}"),
            ("Últimos 90 días", _p(p_r),
             (f'{_var(p_r, p_a)}{_pp(p_r - p_a)}</span> contra {_p(p_a)} antes'
              if np.isfinite(p_r) and np.isfinite(p_a) else "sin comparación")),
            (f"Costo del día por {u}, 90 días", _s(k_r, 2),
             (f'{_var(k_r, k_a)}{"+" if k_r >= k_a else "−"}'
              f'{abs(k_r / k_a - 1) * 100:.0f}%</span> contra {_s(k_a, 2)}'
              if np.isfinite(k_r) and np.isfinite(k_a) and k_a else "")
             + (f" · hoy {_s(p_hoy, 2)}" if np.isfinite(p_hoy) else "")),
            (f"Costo por {u} útil", _s(xs["costo_dia"].sum() / queda, 2)
             if queda > 0 else "—", "Lo pagado ÷ lo que quedó"),
            ("Merma en soles", _s(xs["valor"].sum()), _rot_valor(modo)),
        ])
        # columnas-internas: los dos gráficos del producto y, al lado, la
        # lista que elige otro.
        c_g, c_l = st.columns([1.45, 1], gap="medium")
        mes = por_mes(xs)
        n_row = norm.loc[prod] if prod in norm.index else None
        with c_g:
            st.plotly_chart(_fig_merma(xs, n_row, mes, ini, fin, u),
                            use_container_width=True,
                            key=f"mov_merma_fig_m_{prod}",
                            config={"displaylogo": False,
                                    "displayModeBar": False})
            st.plotly_chart(_fig_precio(xs, mes, p_hoy, ini, fin, u),
                            use_container_width=True,
                            key=f"mov_merma_fig_p_{prod}",
                            config={"displaylogo": False,
                                    "displayModeBar": False})
        with c_l:
            st.markdown(f'<div style="font-weight:600;font-size:13px">Productos '
                        f'que cambiaron</div><div style="font-size:12px;'
                        f'color:{GRIS_TEXTO}">Últimos 90 días contra el resto '
                        'de la ventana, con 5 porcionamientos o más en cada '
                        'lado. Clic para verlo.</div>', unsafe_allow_html=True)
            if ch.empty:
                st.caption("Ningún producto con datos suficientes.")
                return
            tc = pd.DataFrame({
                "Producto": [nombres.get(c, c) for c in ch.index],
                "Antes": ch["pct_ant"].to_numpy(),
                "90 días": ch["pct_rec"].to_numpy(),
                "Δ merma": ch["dpp"].to_numpy(),
                "Δ costo": ch["dprecio"].fillna(0).to_numpy(),
                "Impacto": ch["impacto"].to_numpy(),
            })
            sty = (tc.style.format({"Antes": _p, "90 días": _p, "Δ merma": _pp,
                                    "Δ costo": lambda v: f"{v * 100:+.0f}%",
                                    "Impacto": _s})
                   .map(lambda v: f"color: {_color_signo(v)}; font-weight: 600",
                        subset=["Δ merma", "Δ costo"]))
            _tabla_elegible(
                "mov_merma_cambios", sty, list(ch.index), 0,
                _alto_tabla(len(tc), alturas.MERMA_CAMBIOS),
                {"Producto": st.column_config.TextColumn(width="medium"),
                 "Impacto": st.column_config.Column(
                     help=f"Los puntos de merma de más (o de menos) sobre lo "
                          f"porcionado en los 90 días, {_rot_valor(modo)}."),
                 "Δ costo": st.column_config.Column(
                     help="Cómo cambió el costo del día por unidad que "
                          "entró.")},
                requerida=False)


# ═══════════════════════════════════════════════════════════════════════════
# 3. PROVEEDOR POR KG ÚTIL
# ═══════════════════════════════════════════════════════════════════════════
def tarjeta_proveedores(d_hist, cols, rango):
    """La sección «Proveedor por kg útil». Siempre al costo del día."""
    with st.container(border=True, key=CARD_PROV):
        fin_f = (rango[1] if rango
                 else d_hist["_fecha"].max() + pd.Timedelta(days=1))
        # columnas-internas: título, ventana y el filtro de proveedor único
        # en un renglón.
        c_tit, c_ven, c_uni = st.columns([1.3, 0.9, 1.3],
                                         vertical_alignment="center")
        with c_tit:
            _titulo("Costo por kg útil, por proveedor")
        with c_ven:
            ini, fin = _ventana("mov_merma_prov_ventana", fin_f)
        with c_uni:
            unico = st.toggle(
                "Sólo con un proveedor en los 21 días previos",
                key="mov_merma_prov_unico",
                help="El proveedor de un porcionamiento es el de la última "
                     "compra del producto hasta 45 días antes: el Almacén no "
                     "guarda de qué lote salió. Prendido, quedan sólo los "
                     "porcionamientos sin ambigüedad.")
        compras = _compras()
        base, _ = porcionamientos(
            d_hist[(d_hist["_fecha"] >= ini) & (d_hist["_fecha"] < fin)], cols)
        if compras is None:
            st.info("No se pudo leer compras.parquet: sin proveedores.")
            return
        if base.empty:
            st.info("Sin porcionamientos en la ventana.")
            return
        b = con_proveedor(base, compras)
        r = resumen_proveedores(b, unico)
        nombres = b.drop_duplicates("cod").set_index("cod")["prod"]
        st.caption("Lo que de verdad cuesta cada unidad aprovechable: lo "
                   "pagado ÷ lo que queda después de la merma. Siempre al "
                   "costo del día — a precio de hoy todos los proveedores "
                   "costarían lo mismo.")
        if r.empty:
            st.info("Ningún producto con dos proveedores de 5 "
                    "porcionamientos o más en la ventana.")
            return
        codigos = r.index.tolist()
        k_foco = "_mov_merma_prov_foco"
        _foco_anterior("mov_merma_prov_res", k_foco)
        foco = st.session_state.get(k_foco)
        pos = codigos.index(foco) if foco in codigos else 0
        foco = codigos[pos]
        # columnas-internas: el resumen entre productos y el detalle del
        # elegido, en la misma tarjeta.
        c_res, c_det = st.columns([1.15, 1], gap="medium")
        with c_res:
            st.markdown('<div style="font-weight:600;font-size:13px">Dónde '
                        'pesa más el proveedor</div>', unsafe_allow_html=True)
            tr = pd.DataFrame({
                "Producto": [nombres.get(c, c) for c in codigos],
                "Pagado de más": r["extra"].tolist(),
                "Mejor": r["mejor"].tolist(),
                "S/ útil": r["util_mejor"].tolist(),
                "Más caro": r["peor"].tolist(),
                "S/ útil ": r["util_peor"].tolist(),
            })
            sty = (tr.style.format({"S/ útil": "{:,.2f}", "S/ útil ": "{:,.2f}",
                                    "Pagado de más": _s})
                   .apply(_resaltar(pos), axis=1))
            _tabla_elegible(
                "mov_merma_prov_res", sty, codigos, pos,
                _alto_tabla(len(tr), alturas.MERMA_PROV),
                {"Producto": st.column_config.TextColumn(width="medium"),
                 "Mejor": st.column_config.TextColumn(width="small"),
                 "Más caro": st.column_config.TextColumn(width="small"),
                 "Pagado de más": st.column_config.Column(
                     help="Lo pagado de más por lo que se aprovechó, contra "
                          "el mejor proveedor del mismo producto: Σ (costo "
                          "por unidad útil del proveedor − el del mejor) × "
                          "lo que quedó de lo suyo.")})
        with c_det:
            x = b[b["cod"] == foco]
            u = unidad_corta(x["unid"].iloc[0]) if len(x) else ""
            t = por_proveedor(x, unico)
            st.markdown(f'<div style="font-weight:600;font-size:13px">'
                        f'{html.escape(str(nombres.get(foco, foco)))}</div>',
                        unsafe_allow_html=True)
            td = pd.DataFrame({
                "Proveedor": t.index.tolist(),
                "Porc.": t["n"].astype(int).tolist(),
                "Merma": t["pct"].tolist(),
                f"S/ por {u}": t["pkg"].tolist(),
                f"S/ por {u} útil": t["util"].tolist(),
                "Días": t["dias"].tolist(),
            })
            _u = pd.to_numeric(td[f"S/ por {u} útil"], errors="coerce")
            tope = float(_u.max()) if _u.notna().any() else 1.0
            st.dataframe(
                td.style.format({"Merma": _p, f"S/ por {u}": "{:,.2f}",
                                 "Días": lambda v: "—" if not np.isfinite(v)
                                 else f"{v:.0f}"}),
                hide_index=True, row_height=27,
                height=_alto_tabla(len(td), alturas.MERMA_PROV),
                column_config={
                    "Proveedor": st.column_config.TextColumn(width="medium"),
                    f"S/ por {u} útil": st.column_config.ProgressColumn(
                        format="%.2f", min_value=0.0, max_value=tope),
                    "Días": st.column_config.Column(
                        help="Mediana de días entre la compra y el "
                             "porcionamiento.")})
            sin = int((x["prov"].isna() | (unico & ~x["unico"])).sum())
            if sin:
                st.caption(f"{sin} porcionamiento{'s' if sin != 1 else ''} "
                           "de este producto sin proveedor asignable quedan "
                           "fuera.")
