"""graficos.movimientos_requerimientos — lo que las dos vistas de
requerimientos dicen de cada PEDIDO y de cada PRODUCTO desde el 2026-10-17
(regla #701).

Nació de un mockup aprobado con los datos reales de doce meses (oct 2025 –
sep 2026), la gemela de lo que la regla #670 hizo con las salidas, y con la
misma condición: nada de vistas nuevas. Cinco agregados:

  ① SALIÓ REGISTRADO («por Área»): de lo que un área pidió, qué parte salió
    después de ella por una vía que el kardex registra —la receta al vender
    (95), la producción o el porcionamiento (94/96/90), una nota de salida
    (98/91/92) o una transferencia a otra área (97)—. Lo que no sale por
    ninguna reaparece casi entero como FALTANTE del cierre (93): Cocina pidió
    2,840 L de aceite de frituras, las recetas descargaron 776 y el cierre
    ajustó 2,211. Cocina: S/ 180,205 sin salida registrada, el 15 %; Barra
    16 %; Salón 58 %; Producción 2,4 %. Gastos y Limpieza no descargan nada
    (todo lo da de baja el cierre): «no descarga», no un 100 % en rojo.
  ② FRECUENCIA («por Área»): días con pedido en la ventana. Casi diario
    (150 o más), semanal (53 a 149), ocasional (13 a 52), esporádico. En
    Cocina, 62 productos casi diarios son el 66 % del valor: los candidatos
    a un stock fijo en el área.
  ③ FUERA DE LO HABITUAL (las dos): un pedido de 2,5 veces o más la mediana
    de los pedidos del área de ese producto en los 90 días anteriores (con
    al menos 4), y S/ 50 o más por encima. 917 líneas, S/ 184,479 de más. Y
    la PRIMERA VEZ en 90 días: 1,087 líneas.
  ④ REPETIDO EN EL DÍA (las dos): el área ya había pedido ese producto ese
    mismo día en OTRO requerimiento. 6,261 líneas, S/ 236,242; Cocina, 5,752,
    la mitad a menos de 22 minutos del primero. No distingue estaciones:
    Cocina juntó a Calientes, Fríos y Pastelería y el parquet no dice quién
    digitó.
  ⑤ La FICHA del producto elegido («por Área»): lo pedido contra lo que salió
    mes a mes, por dónde salió, el ajuste del cierre, las semanas con pedido y
    sus pedidos.

① y ② SE MIDEN SOBRE LOS DOCE MESES que terminan con el rango, sea cual sea
el rango (como el «% de lo que entró» de las salidas, #670): con 30 días, el
stock que el área ya tenía o que le queda al cierre mueve la cuenta. ③ y ④
se miden siempre por fecha de REGISTRO —cuándo el área lo digitó—, elija lo
que elija el usuario para las barras.

Lo que NO se propuso: el tiempo entre registro y proceso. En el 80 % de los
requerimientos las dos fechas tienen la misma hora del reloj, al minuto, en
días distintos: una de las dos se elige a mano, y la diferencia no mide una
espera. El kardex mueve el stock a la hora de PROCESO (99,8 % de las líneas).

Las cuentas son puras (`marcas_lineas`, `frecuencia`, `salida_por_area`,
`productos_requeridos`) y las prueba `test_graficos.py::_pruebas_marcas_requerimientos`.
"""

import hashlib
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
import data
import kardex
from graficos import alturas
from graficos.base import _compras_layout
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.movimientos_periodo import (
    fmt_cant, texto_marca, unidad_corta,
)
from tema import (
    ACENTO_TEXTO, AJUSTE_ALERTA_FONDO, AJUSTE_ALERTA_TEXTO, AJUSTE_POS_TEXTO,
    AJUSTE_SOB_FONDO, BLANCO, ERROR, ERROR_FONDO, GRIS_BORDE,
    GRIS_FONDO_CABECERA, GRIS_LINEA, GRIS_TEXTO, LAVANDA_FONDO,
    SERIE_PRINCIPAL, SERIE_TRAMOS, TEXTO_PRINCIPAL,
)

VERSION = 1
"""Va en la clave de la caché de las marcas: subirla al tocar sus reglas."""

ARCHIVO = "requerimientos.parquet"

# ===========================================================================
# LAS CUENTAS (puras)
# ===========================================================================

VECES_HABITUAL = 2.5
"""Desde cuántas veces su pedido habitual un pedido está fuera de lo normal.
Es la regla de «revisar» de Compras › Producto (#653)."""
DIAS_HABITUAL = 90
"""La ventana del pedido habitual: los 90 días ANTERIORES al pedido."""
MIN_PEDIDOS = 4
"""Con menos pedidos en esa ventana no hay «habitual» contra qué medir."""
EXCESO_MIN = 50.0
"""Y por lo menos estos soles por encima de lo habitual: 3 limones de más no
son una alarma aunque sean el triple."""

CASI_DIARIO, SEMANAL, OCASIONAL, ESPORADICO = (
    "Casi diario", "Semanal", "Ocasional", "Esporádico")
GRUPOS = (CASI_DIARIO, SEMANAL, OCASIONAL, ESPORADICO)
_DIAS_GRUPO = ((150, CASI_DIARIO), (53, SEMANAL), (13, OCASIONAL))
_QUE_ES = {CASI_DIARIO: "150 días o más con pedido",
           SEMANAL: "53 a 149 días", OCASIONAL: "13 a 52 días",
           ESPORADICO: "12 días o menos"}

SALIO_POCO = 0.5
"""El filtro «Salió menos de la mitad» de ①."""


def frecuencia(dias):
    """El grupo de un producto por sus días con pedido en la ventana."""
    for tope, g in _DIAS_GRUPO:
        if dias >= tope:
            return g
    return ESPORADICO


def marcas_lineas(lin):
    """Las marcas ③ y ④ de cada línea, alineadas con `lin.index`.

    `lin` trae `sub` (el área que pide), `cod`, `doc`, `fecha` (con hora: la
    de REGISTRO), `cant` y `valor`, sólo de líneas que suman (sin anulados ni
    vacías) y con TODO el historial —el habitual mira 90 días atrás—.

    Columnas: `habitual` (la mediana de las cantidades que el área pidió de
    ese producto en los 90 días anteriores, o NaN), `veces` (cant ÷
    habitual cuando el pedido está fuera de lo habitual, si no 0), `exceso`
    (los soles por encima de lo habitual en esa línea, si está fuera),
    `nuevo` (no lo había pedido en los 90 días anteriores, y hay 90 días de
    historia antes) y `repite_min` (minutos desde que el área lo pidió ese
    mismo día en OTRO requerimiento, o NaN). Vectorizado: un `groupby` con
    `rolling` por tiempo, nada de recorrer grupos (regla #537)."""
    cols = ["habitual", "veces", "exceso", "nuevo", "repite_min"]
    if lin is None or lin.empty:
        return pd.DataFrame(columns=cols)
    o = lin[["sub", "cod", "doc", "fecha", "cant", "valor"]].copy()
    o["cant"] = pd.to_numeric(o["cant"], errors="coerce").fillna(0.0)
    o["valor"] = pd.to_numeric(o["valor"], errors="coerce").fillna(0.0)
    orig = o.index
    o.index = pd.RangeIndex(len(o))
    o["_orig"] = range(len(o))
    o = o.dropna(subset=["fecha"]).sort_values(["sub", "cod", "fecha", "_orig"],
                                               kind="stable")
    r = (o.groupby(["sub", "cod"], sort=False)
          .rolling(f"{DIAS_HABITUAL}D", on="fecha", closed="left")["cant"])
    med, n = r.median(), r.count()
    # `groupby().rolling` devuelve los GRUPOS en su propio orden y, con
    # `on=`, la fecha como índice (pandas 3): no se puede re-pegar por
    # etiqueta. Se ordena `o` en ese mismo orden de grupos —dentro de cada
    # grupo las filas siguen como entraron— y se pega por posición.
    grupos = med.index.droplevel(-1).unique()
    o["_g"] = grupos.get_indexer(pd.MultiIndex.from_arrays([o["sub"], o["cod"]]))
    o = o.sort_values(["_g", "fecha", "_orig"], kind="stable")
    o["habitual"] = med.to_numpy()
    o["_n"] = n.fillna(0).to_numpy()
    pu = (o["valor"] / o["cant"]).where(o["cant"] > 0, 0.0)
    fuera = ((o["_n"] >= MIN_PEDIDOS) & (o["habitual"] > 0)
             & (o["cant"] >= VECES_HABITUAL * o["habitual"])
             & ((o["cant"] - o["habitual"]) * pu >= EXCESO_MIN))
    o["veces"] = (o["cant"] / o["habitual"]).where(fuera, 0.0)
    o["exceso"] = ((o["cant"] - o["habitual"]) * pu).where(fuera, 0.0)
    desde = o["fecha"].min() + pd.Timedelta(days=DIAS_HABITUAL)
    o["nuevo"] = (o["_n"] == 0) & (o["fecha"] >= desde)
    dia = o["fecha"].dt.normalize()
    gd = o.groupby([o["sub"], o["cod"], dia], sort=False)
    prev_t, prev_doc = gd["fecha"].shift(), gd["doc"].shift()
    rep = prev_t.notna() & (prev_doc != o["doc"])
    o["repite_min"] = ((o["fecha"] - prev_t).dt.total_seconds() / 60.0
                       ).where(rep)
    out = o[cols].reindex(pd.RangeIndex(len(orig)))
    out.index = orig
    return out


def ventana_meses(fin):
    """`(inicio, fin, meses)`: los doce meses calendario que terminan en el
    mes del último día del rango (`fin` exclusivo), como «2026-09». Doce
    meses enteros y no 52 semanas: el kardex se suma por mes."""
    ult = (pd.Timestamp(fin) - pd.Timedelta(days=1)).to_period("M")
    meses = [str(ult - i) for i in range(11, -1, -1)]
    return (pd.Period(meses[0], "M").start_time,
            (ult + 1).start_time, meses)


def salida_por_area(kx, meses):
    """De `sql_pedido_y_salida` (con `area` ya en NOMBRE), los totales de
    `meses` por área y producto, y dos cosas más: `cubre` —qué parte de lo
    pedido salió registrado, de 0 a 1, NaN sin pedido en el kardex— y
    `descarga` —si el ÁREA registra alguna salida en esos meses—. Pura."""
    cols = ["area", "cod", "ped", "ven", "pro", "nts", "tra", "aj", "cubre",
            "descarga"]
    if kx is None or kx.empty:
        return pd.DataFrame(columns=cols)
    k = kx[kx["mes"].isin(meses)]
    t = (k.groupby(["area", "cod"], as_index=False)
          [["ped", "ven", "pro", "nts", "tra", "aj"]].sum())
    uso = t["ven"] + t["pro"] + t["nts"] + t["tra"].clip(lower=0)
    t["cubre"] = (uso / t["ped"]).clip(upper=1.0).where(t["ped"] > 0)
    por_area = (t.assign(_u=t["ven"] + t["pro"] + t["nts"])
                 .groupby("area")["_u"].sum())
    t["descarga"] = t["area"].map(por_area > 0).fillna(False).astype(bool)
    return t[cols]


def productos_requeridos(lin, lin_vent, sal):
    """Una fila por producto de `lin`, de mayor a menor valorizado.

    `lin` son las líneas que suman del RANGO y `lin_vent` las de los doce
    meses de la ventana (los dos con lo elegido en los cuadros), con `fecha`,
    `doc`, `sub`, `cod`, `prod`, `cant`, `valor`, `unid` y las marcas de
    `marcas_lineas`. `sal` es `salida_por_area` de esos meses.

    Columnas: `cod`, `prod`, `unid`, `valor`, `pct`, `cant`, `punit` y, de
    la ventana: `ped_vent` (soles pedidos), `dias`, `grupo`, `tipico` (la
    mediana de las cantidades por pedido), `salio` (0-1, ponderado por lo
    pedido en cada área, NaN sin kardex), `sin_salida` (soles pedidos que no
    salieron registrados), `no_descarga` (sus áreas no registran salidas),
    `fuera` y `exceso` (③), `nuevos` (③, primera vez) y `repetidos` (④)."""
    cols = ["cod", "prod", "unid", "valor", "pct", "cant", "punit", "ped_vent",
            "dias", "grupo", "tipico", "salio", "sin_salida", "no_descarga",
            "fuera", "exceso", "nuevos", "repetidos"]
    if lin is None or lin.empty:
        return pd.DataFrame(columns=cols)
    g = (lin.groupby("cod", sort=False)
            .agg(prod=("prod", "first"), unid=("unid", "first"),
                 valor=("valor", "sum"), cant=("cant", "sum")))
    tot = float(g["valor"].sum())
    g["pct"] = g["valor"] / tot * 100.0 if tot else 0.0
    g["punit"] = (g["valor"] / g["cant"]).where(g["cant"] > 0)
    v = lin_vent[lin_vent["cod"].isin(g.index)]
    gv = v.groupby("cod")
    g["ped_vent"] = gv["valor"].sum().reindex(g.index).fillna(0.0)
    g["dias"] = (gv["fecha"].agg(lambda s: s.dt.normalize().nunique())
                 .reindex(g.index).fillna(0).astype(int))
    g["tipico"] = gv["cant"].median().reindex(g.index)
    g["fuera"] = (v["veces"] > 0).groupby(v["cod"]).sum().reindex(g.index).fillna(0).astype(int)
    g["exceso"] = gv["exceso"].sum().reindex(g.index).fillna(0.0)
    g["nuevos"] = v["nuevo"].astype(bool).groupby(v["cod"]).sum().reindex(g.index).fillna(0).astype(int)
    g["repetidos"] = (v["repite_min"].notna().groupby(v["cod"]).sum()
                      .reindex(g.index).fillna(0).astype(int))
    g["grupo"] = [frecuencia(d) for d in g["dias"]]
    # ① por área: lo pedido de cada (área, producto) en la ventana por la
    # parte que NO salió registrada; sólo las áreas que descargan algo.
    pa = (v.groupby(["sub", "cod"], as_index=False)["valor"].sum()
           .rename(columns={"sub": "area"}))
    if sal is not None and len(sal):
        pa = pa.merge(sal[["area", "cod", "cubre", "descarga"]],
                      on=["area", "cod"], how="left")
    else:
        pa["cubre"], pa["descarga"] = float("nan"), True
    pa["descarga"] = pa["descarga"].fillna(True).astype(bool)
    con = pa[pa["descarga"] & pa["cubre"].notna()]
    pv = con.groupby("cod")["valor"].sum()
    sin = (con["valor"] * (1.0 - con["cubre"])).groupby(con["cod"]).sum()
    g["sin_salida"] = sin.reindex(g.index)
    g["salio"] = (1.0 - sin / pv.where(pv > 0)).reindex(g.index)
    nd = pa.groupby("cod")["descarga"].any()
    g["no_descarga"] = ~nd.reindex(g.index).fillna(True).astype(bool)
    if sal is None or not len(sal):
        g["no_descarga"] = False
    g = g.reset_index().sort_values("valor", ascending=False, kind="stable")
    return g[cols].reset_index(drop=True)


def resumen_salida(tabla):
    """`(sin_salida, pedido, n_poco, sin_poco)` de ① sobre la lista: los
    soles pedidos sin salida registrada, lo pedido con kardex (lo que se
    divide), cuántos productos salieron menos de la mitad y sus soles."""
    t = tabla[~tabla["no_descarga"] & tabla["salio"].notna()]
    pedido = float(t["ped_vent"].sum())
    poco = t[t["salio"] < SALIO_POCO]
    return (float(t["sin_salida"].sum()), pedido, len(poco),
            float(poco["sin_salida"].sum()))


# ===========================================================================
# LAS CARGAS
# ===========================================================================

def lineas_req(d, *, fecha, doc, sub, cod, prod, cant, valor, unid=None):
    """Las líneas de `requerimientos.parquet` con los nombres de esta pieza.
    Los argumentos son NOMBRES de columna. Pura."""
    def _txt(col):
        if not col or col not in d.columns:
            return pd.Series("", index=d.index, dtype=object)
        return d[col].fillna("").astype(str).str.strip()
    return pd.DataFrame({
        "fecha": pd.to_datetime(d[fecha], errors="coerce"),
        "doc": _txt(doc), "sub": _txt(sub), "cod": _txt(cod),
        "prod": _txt(prod),
        "cant": pd.to_numeric(d[cant], errors="coerce").fillna(0.0)
                if cant and cant in d.columns else 0.0,
        "valor": pd.to_numeric(d[valor], errors="coerce").fillna(0.0),
        "unid": _txt(unid),
    }, index=d.index)


@st.cache_data(show_spinner=False, max_entries=2)
def _marcas_cacheable(sello, cols, version=VERSION):
    """`marcas_lineas` del parquet ENTERO, por (doc, cod): las marcas no
    dependen de los chips (un producto tiene una familia y un área pide lo
    suyo) ni del rango (el habitual mira atrás). `cols` son los nombres de
    columna resueltos, `(fecha, doc, sub, cod, cant, valor, estado)`."""
    f, doc, sub, cod, cant, valor, estado = cols
    df = data.cargar(ARCHIVO)
    if df is None or df.empty:
        return None
    ok = df[cod].fillna("").astype(str).str.strip() != ""
    if estado and estado in df.columns:
        ok &= df[estado].fillna("").astype(str).str.strip().str.upper() != "ANULADO"
    df = df[ok]
    lin = lineas_req(df, fecha=f, doc=doc, sub=sub, cod=cod, prod=None,
                     cant=cant, valor=valor)
    m = marcas_lineas(lin)
    m["doc"], m["cod"] = lin["doc"], lin["cod"]
    # Un mismo producto dos veces en un requerimiento no pasa hoy (149 mil
    # líneas, ningún par repetido); si pasa, manda la marca más fuerte.
    return (m.groupby(["doc", "cod"], as_index=False)
             .agg(habitual=("habitual", "first"), veces=("veces", "max"),
                  exceso=("exceso", "sum"), nuevo=("nuevo", "max"),
                  repite_min=("repite_min", "min")))


def marcas_de(d, *, fecha, doc, sub, cod, cant, valor, estado=None):
    """Las marcas ③ y ④ de las filas de `d`, alineadas con su índice (las
    que no tienen marca, en cero). None si no se pueden calcular. `fecha` es
    la de REGISTRO. Los argumentos son nombres de columna."""
    if not (fecha and doc and sub and cod and valor) or d is None:
        return None
    try:
        m = _marcas_cacheable(data.sello_datos(ARCHIVO),
                              (fecha, doc, sub, cod, cant, valor, estado))
    except Exception:
        return None
    if m is None:
        return None
    clave = pd.DataFrame({
        "doc": d[doc].fillna("").astype(str).str.strip(),
        "cod": d[cod].fillna("").astype(str).str.strip()}, index=d.index)
    out = clave.reset_index().merge(m, on=["doc", "cod"], how="left")
    out = out.set_index(out.columns[0])
    out.index.name = d.index.name
    out = out.drop(columns=["doc", "cod"])
    out["veces"] = out["veces"].fillna(0.0)
    out["exceso"] = out["exceso"].fillna(0.0)
    out["nuevo"] = out["nuevo"].fillna(False).astype(bool)
    return out.reindex(d.index)


@st.cache_data(show_spinner=False, max_entries=2)
def _kx_cacheable(sello_kx, sello_inv, version=kardex.VERSION):
    """`kardex.sql_pedido_y_salida` con el área por su NOMBRE, el de
    `SUB ALMACEN` de los requerimientos (del maestro de inventario)."""
    if not data.secrets_disponibles():
        return None
    con = data.get_conn()
    rel = f"read_parquet('s3://{st.secrets['R2_BUCKET']}/{kardex.ARCHIVO}')"
    kx = con.execute(kardex.sql_pedido_y_salida(rel)).df()
    inv = data.cargar(data.REPORTES["Inventario Valorizado"]["archivo"])
    if inv is None or "CODIGO AREA" not in inv.columns \
            or "NOMBRE AREA" not in inv.columns:
        return None
    nombre = (inv.drop_duplicates("CODIGO AREA")
                 .set_index("CODIGO AREA")["NOMBRE AREA"]
                 .fillna("").astype(str).str.strip())
    kx["area"] = kx["area"].map(nombre)
    kx["cod"] = kx["cod"].fillna("").astype(str).str.strip()
    return kx.dropna(subset=["area"])


def pedido_y_salida():
    """Lo pedido y lo que salió de cada área, por producto y mes, o None si
    no se puede leer (sin secrets, R2 caído): ① queda en «—»."""
    try:
        return _kx_cacheable(
            data.sello_datos(kardex.ARCHIVO),
            data.sello_datos(data.REPORTES["Inventario Valorizado"]["archivo"]))
    except Exception:
        return None


# ===========================================================================
# LO QUE SE DIBUJA («Requerimientos por Área»)
# ===========================================================================

CARD_PRODUCTOS = "ajuste_graf_card_izq_mov_req_prod"
CARD_FICHA = "ajuste_graf_card_izq_mov_req_ficha"
CARD_PEDIDOS = "ajuste_graf_card_izq_mov_req_pedidos"
"""El prefijo `ajuste_graf_card_izq_` les da el marco de las demás tarjetas
de Movimientos (`estilos/_80_cards.py`)."""

_K = "mov_rq"
K_GRUPO = f"{_K}_grupo"
K_POCO = f"{_K}_poco"
K_FOCO = f"{_K}_foco"

_COLOR_GRUPO = {CASI_DIARIO: (ACENTO_TEXTO, LAVANDA_FONDO),
                SEMANAL: (AJUSTE_POS_TEXTO, AJUSTE_SOB_FONDO),
                OCASIONAL: (AJUSTE_ALERTA_TEXTO, AJUSTE_ALERTA_FONDO),
                ESPORADICO: (GRIS_TEXTO, GRIS_FONDO_CABECERA)}
"""`(tinta, fondo)` de cada frecuencia. Ninguna es buena ni mala: colores
sin semáforo, el más intenso para lo de todos los días."""

_BOTONES = st.components.v2.component(
    "botones_requerimientos_movimientos",
    js=(Path(__file__).parent / "movimientos_kpi.js").read_text(
        encoding="utf-8"),
    isolate_styles=False,
)
"""Los botones de frecuencia y el de «Salió menos de la mitad»: el MISMO
componente que la fila de KPI de las tarjetas «por período»
(`movimientos_kpi.js`, regla #649), como los de la #670."""


def _css():
    _botones = "".join(
        f".st-key-{_K}_grupos [data-res='{g}']{{--g:{t};--gbg:{f}}}"
        for g, (t, f) in _COLOR_GRUPO.items())
    return f"""<style>
.st-key-{_K}_grupos .mp-kpi-raiz{{display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}}
.st-key-{_K}_poco .mp-kpi-raiz{{display:flex}}
.st-key-{_K}_poco [data-res]{{--g:{ERROR};--gbg:{ERROR_FONDO}}}
.st-key-{_K}_grupos [data-res],.st-key-{_K}_poco [data-res]{{font:inherit;
  text-align:left;cursor:pointer;border:1.5px solid var(--g);
  background:var(--gbg);color:{TEXTO_PRINCIPAL};border-radius:10px;
  padding:8px 14px;display:flex;flex-direction:column;gap:1px;min-height:60px}}
.st-key-{_K}_grupos [data-res]:hover,.st-key-{_K}_poco [data-res]:hover{{
  box-shadow:0 3px 10px -4px var(--g)}}
.st-key-{_K}_grupos [data-res] .gn,.st-key-{_K}_poco [data-res] .gn{{
  font-weight:700;font-size:14px;color:var(--g)}}
.st-key-{_K}_grupos [data-res] .gv,.st-key-{_K}_poco [data-res] .gv{{
  font-size:12.5px;font-variant-numeric:tabular-nums}}
.st-key-{_K}_grupos [data-res] .gq,.st-key-{_K}_poco [data-res] .gq{{
  font-size:11.5px;color:{GRIS_TEXTO}}}
.st-key-{_K}_grupos [data-res][aria-pressed='true'],
.st-key-{_K}_poco [data-res][aria-pressed='true']{{background:var(--g)}}
.st-key-{_K}_grupos [data-res][aria-pressed='true'] span,
.st-key-{_K}_poco [data-res][aria-pressed='true'] span{{color:{BLANCO}}}
{_botones}
.rq-uno{{border:1px solid {GRIS_BORDE};border-radius:10px;padding:8px 14px;
  font-size:13px;line-height:1.45}}
.st-key-{_K}_poco .mp-kpi-raiz [data-res]{{width:100%}}
.rq-cifras{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));
  gap:10px}}
.rq-cifra{{border:1px solid {GRIS_BORDE};border-radius:10px;padding:6px 12px}}
.rq-cifra .k{{font-size:11.5px;color:{GRIS_TEXTO}}}
.rq-cifra .v{{font-size:16px;font-weight:700;
  font-variant-numeric:tabular-nums}}
.rq-cifra .s{{font-size:11.5px;color:{GRIS_TEXTO}}}
.rq-pill{{display:inline-block;border-radius:999px;padding:1px 9px;
  font-size:12.5px;font-weight:700}}
.rq-sem{{display:grid;grid-template-columns:repeat(27,minmax(0,1fr));gap:3px}}
.rq-sem i{{aspect-ratio:1;border-radius:3px;background:{GRIS_LINEA};
  display:block}}
.rq-vias{{display:flex;flex-direction:column;gap:5px;font-size:12px}}
.rq-vias div{{display:grid;grid-template-columns:170px minmax(0,1fr) 78px;
  gap:8px;align-items:center}}
.rq-vias s{{display:block;height:9px;border-radius:3px;
  background:{SERIE_PRINCIPAL};text-decoration:none}}
.rq-vias s.aj{{background:{ERROR}}}
.rq-vias .m{{text-align:right;font-variant-numeric:tabular-nums}}
.rq-meses{{width:100%;border-collapse:collapse;font-size:11.5px;
  font-variant-numeric:tabular-nums}}
.rq-meses th,.rq-meses td{{padding:3px 4px;text-align:right;
  border-bottom:1px solid {GRIS_LINEA};white-space:nowrap}}
.rq-meses th{{color:{GRIS_TEXTO};font-weight:600;
  background:{GRIS_FONDO_CABECERA}}}
.rq-meses th:first-child,.rq-meses td:first-child{{text-align:left}}
.rq-meses td.falta{{color:{ERROR};font-weight:700}}
.rq-ayuda{{font-size:11.5px;color:{GRIS_TEXTO}}}
</style>"""


def _soles(v):
    return f"S/ {v:,.0f}"


def _html_grupos(tabla, elegido):
    tot = float(tabla["valor"].sum()) or 1.0
    piezas = []
    for g in GRUPOS:
        t = tabla[tabla["grupo"] == g]
        v = float(t["valor"].sum())
        piezas.append(
            f'<button type="button" data-res="{g}" '
            f'aria-pressed="{"true" if elegido == g else "false"}" '
            f'title="{"Clic para ver todos" if elegido == g else "Clic para ver sólo éstos"}">'
            f'<span class="gn">{g}</span>'
            f'<span class="gv">{_soles(v)} · {100 * v / tot:.0f} %</span>'
            f'<span class="gq">{len(t):,} productos · {_QUE_ES[g]}</span>'
            "</button>")
    return "".join(piezas)


def _html_poco(n, soles, on):
    return (f'<button type="button" data-res="poco" '
            f'aria-pressed="{"true" if on else "false"}" '
            f'title="{"Clic para ver todos" if on else "Clic para ver sólo éstos"}">'
            '<span class="gn">Salió menos de la mitad</span>'
            f'<span class="gv">{_soles(soles)} sin salida</span>'
            f'<span class="gq">{n:,} productos</span></button>')


def _al_elegir_grupo():
    a = (st.session_state.get(f"{_K}_grupos") or {}).get("resaltar") or {}
    n = a.get("nombre")
    st.session_state[K_GRUPO] = n if n in GRUPOS else None


def _al_elegir_poco():
    a = (st.session_state.get(f"{_K}_poco") or {}).get("resaltar") or {}
    st.session_state[K_POCO] = a.get("nombre") == "poco"


def _key_tabla(codigos):
    """La key de la lista lleva la FIRMA de sus filas (regla #556): la
    selección de un `st.dataframe` es de la key, no de sus datos."""
    firma = hashlib.md5("|".join(codigos).encode("utf-8")).hexdigest()[:12]
    return f"{_K}_tabla_{firma}"


def _fila_elegida(evt):
    try:
        sel = getattr(evt, "selection", None)
        if sel is None and isinstance(evt, dict):
            sel = evt.get("selection")
        filas = (sel or {}).get("rows", [])
        return filas[0] if filas else None
    except Exception:
        return None


def _leer_foco():
    """El producto que la lista tenía elegido en la corrida anterior, al
    foco, ANTES de dibujar (como `movimientos_bajas._leer_foco`)."""
    ss = st.session_state
    key = ss.get(f"_{_K}_key")
    codigos = ss.get(f"_{_K}_codigos") or []
    fila = _fila_elegida(ss.get(key)) if key else None
    if fila is not None and 0 <= fila < len(codigos):
        ss[K_FOCO] = codigos[fila]


_SIN_DATO = -1.0
"""Lo que lleva una celda sin dato: `st.dataframe` pinta un vacío como
«None» (regla #529), así que la celda lleva un número que el Styler escribe
«—»."""
_NO_DESCARGA = -2.0
"""La celda de «Salió registrado» de un área que no registra salidas."""


def _tabla_productos(vis, foco):
    """La lista con su Styler; devuelve el código en foco."""
    codigos = vis["cod"].tolist()
    pos = codigos.index(foco) if foco in codigos else 0
    u = [unidad_corta(x) for x in vis["unid"]]
    salio = [(_NO_DESCARGA if nd else _SIN_DATO if pd.isna(s) else 100.0 * s)
             for s, nd in zip(vis["salio"], vis["no_descarga"])]
    filas = pd.DataFrame({
        "Producto": vis["prod"],
        "Valorizado": vis["valor"].astype(float),
        "%": vis["pct"].astype(float),
        "Cantidad": [f"{fmt_cant(round(float(q), 2))} {x}".strip()
                     for q, x in zip(vis["cant"], u)],
        "① Salió · 12 m": salio,
        "① Sin salida · 12 m": [(_SIN_DATO if (nd or pd.isna(s)) else float(s))
                       for s, nd in zip(vis["sin_salida"], vis["no_descarga"])],
        "② Frecuencia": [f"{g} · {d} días" for g, d in
                       zip(vis["grupo"], vis["dias"])],
        "② Típico": [(f"{fmt_cant(round(float(t), 2))} {x}".strip()
                           if pd.notna(t) else "—")
                          for t, x in zip(vis["tipico"], u)],
        "③ Fuera de lo habitual": [
            (f"{int(n)} · S/ {e:,.0f}" if n else "")
            + (f"{' · ' if n else ''}1.ª vez ×{int(nu)}" if nu else "")
            for n, e, nu in zip(vis["fuera"], vis["exceso"], vis["nuevos"])],
        "④ Repetido": vis["repetidos"].astype(int),
    }).reset_index(drop=True)

    def _fmt_salio(v):
        return ("no descarga" if v == _NO_DESCARGA else "—" if v < 0
                else f"{v:.0f} %")

    def _estilo_salio(v):
        if v == _NO_DESCARGA or v < 0:
            return f"color: {GRIS_TEXTO}"
        if v < 100 * SALIO_POCO:
            return f"color: {ERROR}; font-weight: 700"
        if v < 85:
            return f"color: {AJUSTE_ALERTA_TEXTO}; font-weight: 600"
        return ""

    def _estilo_grupo(v):
        g = str(v).split(" ·")[0]
        tinta, fondo = _COLOR_GRUPO.get(g, (GRIS_TEXTO, ""))
        return f"color: {tinta}; background-color: {fondo}; font-weight: 600"

    def _estilo_marca(v):
        return (f"color: {AJUSTE_ALERTA_TEXTO}; font-weight: 600" if v else "")

    def _fila(r):
        return ([f"background-color: {LAVANDA_FONDO}"] * len(r)
                if r.name == pos else [""] * len(r))

    sty = (filas.style
           .format({"Valorizado": "S/ {:,.0f}", "%": "{:.1f}",
                    "① Salió · 12 m": _fmt_salio,
                    "① Sin salida · 12 m": lambda v: "—" if v < 0 else f"S/ {v:,.0f}",
                    "④ Repetido": lambda v: f"{v:,}" if v else ""})
           .apply(_fila, axis=1)
           .map(_estilo_salio, subset=["① Salió · 12 m"])
           .map(_estilo_grupo, subset=["② Frecuencia"])
           .map(_estilo_marca, subset=["③ Fuera de lo habitual"]))
    ss = st.session_state
    key = _key_tabla(codigos)
    ss[f"_{_K}_key"] = key
    ss[f"_{_K}_codigos"] = codigos
    st.dataframe(
        sty, key=key, on_select="rerun",
        selection_mode="single-row-required",
        selection_default={"selection": {"rows": [pos]}},
        hide_index=True, row_height=27,
        height=alturas.por_filas(len(filas), px_fila=27, extra=38, minimo=0,
                                 rol=alturas.BAJAS_TABLA),
        column_config={
            "Producto": st.column_config.TextColumn(width="large"),
            "%": st.column_config.Column(help="Del valorizado de la lista"),
            "① Salió · 12 m": st.column_config.Column(
                help="① De lo que el área pidió en los 12 meses que terminan "
                     "con el rango, qué parte salió después por una receta, "
                     "una producción o porcionamiento, una nota de salida o "
                     "una transferencia (kardex del área). Lo que no salió "
                     "reaparece como faltante del cierre. Rojo: menos de la "
                     "mitad. «no descarga»: el área no registra salidas"),
            "① Sin salida · 12 m": st.column_config.Column(
                help="① Los soles pedidos en esos 12 meses que no salieron "
                     "registrados"),
            "② Frecuencia": st.column_config.Column(
                help="② Días con pedido en los 12 meses. Casi diario: 150 o "
                     "más; semanal: 53 a 149; ocasional: 13 a 52"),
            "② Típico": st.column_config.Column(
                help="② La mediana de la cantidad por pedido en los 12 meses"),
            "③ Fuera de lo habitual": st.column_config.Column(
                help="③ Pedidos de 2,5 veces o más su habitual (la mediana "
                     "de los 90 días anteriores) y S/ 50 o más por encima, "
                     "con los soles de más; y las veces que se pidió por "
                     "primera vez en 90 días"),
            "④ Repetido": st.column_config.Column(
                help="④ Líneas que repiten un producto que el área ya había "
                     "pedido ese mismo día en otro requerimiento"),
        })
    return codigos[pos]


def seccion_productos(lin, lin_vent, vent, kx):
    """La tarjeta de productos de «Requerimientos por Área» (regla #701) y,
    debajo, la ficha y los pedidos del elegido. `lin`, `lin_vent` como en
    `productos_requeridos` (con `marcas_de` ya pegadas); `vent` es
    `ventana_meses`; `kx`, `pedido_y_salida()` (o None)."""
    sal = salida_por_area(kx, vent[2]) if kx is not None else None
    tabla = productos_requeridos(lin, lin_vent, sal)
    with st.container(border=True, key=CARD_PRODUCTOS):
        st.markdown(CSS_TITULOS_DRILL + _css(), unsafe_allow_html=True)
        st.markdown(
            '<div class="inv-rank-tit">Productos <span class="inv-rank-tit-n">'
            f"{len(tabla):,}</span></div>", unsafe_allow_html=True)
        if tabla.empty:
            st.info("Sin productos pedidos en estas fechas.")
            return
        poco_on = bool(st.session_state.get(K_POCO))
        if sal is not None:
            sin, ped, n_poco, sin_poco = resumen_salida(tabla)
            nd = bool(tabla["no_descarga"].all())
            if nd:
                txt = ("① Estas áreas no registran salidas: todo lo que "
                       "piden se gasta sin anotarlo y lo da de baja el "
                       "cierre.")
            else:
                txt = (f"① De lo pedido en los 12 meses, <b>{_soles(sin)}</b>"
                       f" ({100 * sin / ped if ped else 0:.1f} %) no salió "
                       "por ninguna receta, producción ni nota: se fue al "
                       "faltante del cierre o sigue en el área. "
                       f"<b>{n_poco:,}</b> productos salieron menos de la "
                       "mitad.")
            if nd or not n_poco:
                st.markdown(f'<div class="rq-uno">{txt}</div>',
                            unsafe_allow_html=True)
            else:
                # columnas-internas: la frase de ① y su botón, dentro de la
                # tarjeta de productos.
                c_t, c_b = st.columns([3.4, 1], vertical_alignment="center")
                with c_t:
                    st.markdown(f'<div class="rq-uno">{txt}</div>',
                                unsafe_allow_html=True)
                with c_b, st.container(key=f"{_K}_poco_caja"):
                    _BOTONES(key=f"{_K}_poco",
                             on_resaltar_change=_al_elegir_poco,
                             width="stretch",
                             data={"html": _html_poco(n_poco, sin_poco,
                                                      poco_on)})
        else:
            poco_on = False
            st.caption("① «Salió registrado» necesita el kardex "
                       "(`kardex.parquet`), que no se pudo leer.")
        grupo = st.session_state.get(K_GRUPO)
        if grupo not in GRUPOS:
            grupo = None
        with st.container(key=f"{_K}_grupos_caja"):
            _BOTONES(key=f"{_K}_grupos", on_resaltar_change=_al_elegir_grupo,
                     width="stretch", data={"html": _html_grupos(tabla, grupo)})
        vis = tabla[tabla["grupo"] == grupo] if grupo else tabla
        if poco_on:
            vis = vis[~vis["no_descarga"] & (vis["salio"] < SALIO_POCO)]
        if vis.empty:
            st.info("Ningún producto con estos filtros.")
            return
        _leer_foco()
        cod = _tabla_productos(vis.reset_index(drop=True),
                               st.session_state.get(K_FOCO))
    p = vis[vis["cod"] == cod].iloc[0]
    _ficha(p, lin_vent[lin_vent["cod"] == cod], vent, kx)


def _rot_mes(m):
    p = pd.Period(m, "M")
    return f"{cortes.MESES_ABR_ES[p.month - 1]} {str(p.year)[2:]}"


def _ficha(p, l, vent, kx):
    """La ficha ⑤ del producto `p` (una fila de `productos_requeridos`) con
    sus líneas `l` de la ventana."""
    u = unidad_corta(p["unid"])
    meses = vent[2]
    areas = set(l["sub"])
    k = (kx[(kx["cod"] == p["cod"]) & kx["area"].isin(areas)
            & kx["mes"].isin(meses)] if kx is not None else None)
    por_mes = (k.groupby("mes")[["ped", "ven", "pro", "nts", "tra", "aj"]].sum()
               if k is not None and len(k) else None)

    def _col(c):
        if por_mes is None:
            return [0.0] * len(meses)
        return [float(por_mes[c].get(m, 0.0)) for m in meses]
    ped = [float(x) for x in
           l.groupby(l["fecha"].dt.to_period("M").astype(str))["cant"].sum()
           .reindex(meses).fillna(0.0)]
    ven, pro, nts, tra, aj = (_col(c) for c in ("ven", "pro", "nts", "tra", "aj"))
    sal = [a + b + c + max(0.0, d) for a, b, c, d in zip(ven, pro, nts, tra)]
    rot = [_rot_mes(m) for m in meses]
    tinta, fondo = _COLOR_GRUPO[p["grupo"]]
    if p["no_descarga"]:
        salio_v, salio_s = "no descarga", "el área no registra salidas"
    elif pd.isna(p["salio"]):
        salio_v, salio_s = "—", "sin kardex del área"
    else:
        salio_v = f"{100 * p['salio']:.0f} %"
        salio_s = f"salieron {fmt_cant(round(sum(sal), 1))} de {fmt_cant(round(sum(_col('ped')), 1))} {u}"
    with st.container(border=True, key=CARD_FICHA):
        st.markdown(CSS_TITULOS_DRILL + _css(), unsafe_allow_html=True)
        st.markdown(
            f'<div class="inv-rank-tit">⑤ {escape(str(p["prod"]))}</div>'
            '<div class="rq-cifras">'
            f'<div class="rq-cifra"><div class="k">Pedido · 12 meses</div>'
            f'<div class="v">{_soles(float(l["valor"].sum()))}</div>'
            f'<div class="s">{fmt_cant(round(float(l["cant"].sum()), 2))} {u}'
            f' · {l["doc"].nunique():,} requerimientos</div></div>'
            f'<div class="rq-cifra"><div class="k">① Salió registrado</div>'
            f'<div class="v">{salio_v}</div><div class="s">{salio_s}</div></div>'
            f'<div class="rq-cifra"><div class="k">② Frecuencia</div>'
            f'<div class="v"><span class="rq-pill" style="color:{tinta};'
            f'background:{fondo}">{p["grupo"]}</span></div><div class="s">'
            f'{p["dias"]} días con pedido · típico '
            f'{fmt_cant(round(float(p["tipico"]), 2)) if pd.notna(p["tipico"]) else "—"} {u}'
            '</div></div>'
            f'<div class="rq-cifra"><div class="k">③ Fuera de lo habitual</div>'
            f'<div class="v">{int(p["fuera"])} {"vez" if p["fuera"] == 1 else "veces"}'
            f'</div><div class="s">'
            + (f'{_soles(float(p["exceso"]))} por encima de lo normal'
               if p["fuera"] else "siempre dentro de lo normal")
            + (f' · 1.ª vez ×{int(p["nuevos"])}' if p["nuevos"] else "")
            + '</div></div>'
            f'<div class="rq-cifra"><div class="k">④ Repetido en el día</div>'
            f'<div class="v">{int(p["repetidos"])}</div><div class="s">líneas '
            'que repiten un pedido de ese día</div></div></div>',
            unsafe_allow_html=True)
        # columnas-internas: el gráfico con su tabla | por dónde salió y las
        # semanas, dentro de la ficha (la forma de la #670).
        c1, c2 = st.columns([1.6, 1], gap="medium")
        with c1:
            st.markdown('<div class="rq-ayuda">Pedido por mes, en '
                        f'{u or "su unidad"}: la parte oscura es lo que salió '
                        'registrado</div>', unsafe_allow_html=True)
            parte = [min(a, b) for a, b in zip(ped, sal)]
            resto = [max(a - b, 0.0) for a, b in zip(ped, parte)]
            fig = go.Figure()
            fig.add_bar(x=rot, y=parte, marker=dict(color=SERIE_TRAMOS[0]),
                        hoverinfo="skip", showlegend=False)
            fig.add_bar(x=rot, y=resto, base=parte,
                        marker=dict(color=SERIE_TRAMOS[2]),
                        hoverinfo="skip", showlegend=False)
            fig.add_bar(
                x=rot, y=ped, marker=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                text=[fmt_cant(round(v, 1)) if v else "" for v in ped],
                textposition="outside", cliponaxis=False,
                customdata=list(zip(sal, aj)),
                hovertemplate=("%{x}: pedido %{y:,.2f} " + u
                               + "<br>salió registrado %{customdata[0]:,.2f} "
                               + u + "<br>ajuste del cierre "
                               "%{customdata[1]:,.2f}<extra></extra>"))
            mas = [s if s > q else None for s, q in zip(sal, ped)]
            if any(m is not None for m in mas):
                fig.add_scatter(
                    x=rot, y=mas, mode="markers", showlegend=False,
                    marker=dict(symbol="circle-open", size=9,
                                color=TEXTO_PRINCIPAL, line=dict(width=2)),
                    hovertemplate=("%{x}: salió %{y:,.2f} " + u
                                   + ", más de lo pedido: había stock de "
                                   "antes<extra></extra>"))
            fig.update_layout(barmode="overlay")
            _compras_layout(fig, alto=alturas.BAJAS_FICHA_FIG)
            fig.update_xaxes(type="category")
            fig.update_layout(margin=dict(l=10, r=10, t=14, b=10))
            st.plotly_chart(fig, use_container_width=True,
                            key=f"{_K}_ficha_fig")

            def _celdas(xs, clase_neg=False):
                out = []
                for x in xs:
                    if not x:
                        out.append("<td>—</td>")
                    elif clase_neg:
                        out.append(f'<td class="{"falta" if x > 0 else ""}">'
                                   f'{"−" if x > 0 else "+"}'
                                   f"{fmt_cant(round(abs(x), 1))}</td>")
                    else:
                        out.append(f"<td>{fmt_cant(round(x, 1))}</td>")
                return "".join(out)
            st.markdown(
                '<table class="rq-meses"><tr><th></th>'
                + "".join(f"<th>{r}</th>" for r in rot) + "</tr>"
                + "<tr><td>Pedido</td>" + _celdas(ped)
                + "</tr><tr><td>Salió registrado</td>" + _celdas(sal)
                + "</tr><tr><td>Ajuste del cierre</td>" + _celdas(aj, True)
                + "</tr></table>", unsafe_allow_html=True)
        with c2:
            st.markdown(_html_vias(ven, pro, nts, tra, aj, u)
                        + _html_semanas(l, vent), unsafe_allow_html=True)
    _pedidos(l, u)


def _html_vias(ven, pro, nts, tra, aj, u):
    vias = [("Ventas (recetas)", sum(ven)),
            ("Producción y porcionamiento", sum(pro)),
            ("Notas de salida", sum(nts)),
            ("Transferido a otra área", max(0.0, sum(tra))),
            ("Ajuste del cierre", sum(aj))]
    mx = max([abs(v) for _, v in vias] + [1e-9])
    filas = "".join(
        f'<div><span>{n}</span><s class="{"aj" if i == 4 else ""}" '
        f'style="width:{max(2.0, 100 * abs(v) / mx):.0f}%"></s>'
        f'<span class="m">{("−" if v > 0 else "+") if i == 4 and v else ""}'
        f"{fmt_cant(round(abs(v), 1))}</span></div>"
        for i, (n, v) in enumerate(vias))
    return (f'<div class="rq-ayuda">Por dónde salió · 12 meses, en {u or "su unidad"}'
            f'</div><div class="rq-vias">{filas}</div>'
            '<div class="rq-ayuda">El ajuste es lo que el conteo del cierre '
            'encontró de menos (−) o de más (+).</div>')


def _html_semanas(l, vent):
    ini = vent[0]
    n = 53
    v = [0.0] * n
    s = ((l["fecha"] - ini).dt.days // 7).clip(0, n - 1)
    for i, x in l.assign(_s=s).groupby("_s")["cant"].sum().items():
        v[int(i)] = float(x)
    mx = max(v) or 1.0
    celdas = []
    for i, x in enumerate(v):
        d = ini + pd.Timedelta(days=7 * i)
        tip = (f"Semana del {d.day} {cortes.MESES_ABR_ES[d.month - 1]} "
               f"{str(d.year)[2:]}: " + (fmt_cant(round(x, 2)) if x
                                         else "sin pedido"))
        estilo = (f' style="background:{SERIE_PRINCIPAL};'
                  f'opacity:{0.3 + 0.7 * x / mx:.2f}"' if x else "")
        celdas.append(f'<i title="{tip}"{estilo}></i>')
    return ('<div class="rq-ayuda" style="margin-top:12px">Semanas con pedido, '
            'una por casillero: más oscuro, más cantidad.</div>'
            '<div class="rq-sem">' + "".join(celdas) + "</div>")


def _pedidos(l, u):
    """Los pedidos del producto en la ventana, del más nuevo al más viejo."""
    with st.container(border=True, key=CARD_PEDIDOS):
        st.markdown(CSS_TITULOS_DRILL, unsafe_allow_html=True)
        st.markdown('<div class="inv-rank-tit">Sus pedidos · 12 meses '
                    f'<span class="inv-rank-tit-n">{l["doc"].nunique():,}'
                    "</span></div>", unsafe_allow_html=True)
        n = l.sort_values("fecha", ascending=False)
        filas = pd.DataFrame({
            "Fecha": n["fecha"].dt.strftime("%d/%m/%y %H:%M"),
            "Requerimiento": n["doc"],
            "Área": n["sub"].str.capitalize(),
            "Cantidad": [f"{fmt_cant(round(float(x), 3))} {u}".strip()
                         for x in n["cant"]],
            "S/": n["valor"].astype(float),
            "Marca": [texto_marca(a, b, c, d, u) for a, b, c, d in zip(
                n["veces"], n["habitual"], n["nuevo"], n["repite_min"])],
        })
        st.dataframe(
            filas.style.format({"S/": "{:,.2f}"}), hide_index=True,
            row_height=27,
            height=alturas.por_filas(len(filas), px_fila=27, extra=38,
                                     minimo=0, rol=alturas.BAJAS_NOTAS),
            column_config={"Marca": st.column_config.TextColumn(width="large")},
            key=f"{_K}_pedidos")
