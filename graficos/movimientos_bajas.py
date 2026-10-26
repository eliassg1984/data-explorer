"""graficos.movimientos_bajas — lo que «Salidas por Área» dice de cada
PRODUCTO desde el 2026-10-17 (regla #670), y el faltante de cada cierre que
usa «Salidas por Período».

Nació de un mockup aprobado con los datos reales de doce meses (oct 2025 –
sep 2026), a pedido: enriquecer las dos vistas de salidas con lo que dice
la merma «sin aumentar otra vista». El cuadro Producto de «Salidas por
Área» pasó a ser una tarjeta propia, a todo el ancho, con dos columnas que
el valorizado no dice:

  · «% DE LO QUE ENTRÓ»: lo dado de baja dividido por lo que entró del
    mismo producto —lo producido (órdenes de producción procesadas), lo
    porcionado (cortes) y lo comprado—, todo en la unidad del kardex. Ordena
    distinto que los soles: la Entraña es la 5ª en soles y se pierde el
    0,9 %; la Tarta de queso, el 20,9 %; el Mix de lechugas, el 17,3 %.
  · «FRECUENCIA»: CRÓNICO si tuvo salidas en 10 o más de las 52 semanas,
    PUNTUAL si una sola nota hace la mitad o más de lo suyo, OCASIONAL el
    resto. Lo crónico es una costumbre de producción o de compra; lo
    puntual, un equipo malogrado o un error de un día. En las bajas de doce
    meses, 68 productos crónicos son el 68 % del valor.

LAS DOS SE MIDEN SOBRE 52 SEMANAS que terminan donde termina el rango, sea
cual sea el rango. Con 30 días se tropieza con el stock de antes: «Destino
de lo que entra» (#614) dividía así y en 20 de 57 filas salía más de lo que
entró. Con 52 semanas pasa en 2 de 359.

Los tres botones de frecuencia filtran la lista, y la fila elegida abre la
FICHA del producto debajo: lo dado de baja mes a mes contra lo que entró, las
52 semanas en casilleros, por qué se dio de baja y sus notas.

Las cuentas son puras (`productos_bajas`, `faltante_por_mes`, `grupo_de`) y
las prueba `test_graficos.py::_pruebas_bajas`.
"""

from graficos.movil import js_movil
import hashlib
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cortes
import data
from graficos import alturas
from graficos.base import _compras_layout
from graficos.drill_tablas import CSS_TITULOS_DRILL
from graficos.movimientos_periodo import fmt_cant, unidad_corta
from tema import (
    ACENTO_TEXTO, ADVERTENCIA, ADVERTENCIA_FONDO, BLANCO, ERROR, ERROR_FONDO,
    GRIS_BORDE, GRIS_FONDO_CABECERA, GRIS_LINEA, GRIS_TEXTO, LAVANDA_FONDO,
    SERIE_PRINCIPAL, TEXTO_PRINCIPAL,
)

# ===========================================================================
# LAS CUENTAS (puras)
# ===========================================================================

SEMANAS = 52
"""La ventana de «% de lo que entró» y de «Frecuencia»: 52 semanas justas
que terminan donde termina el rango de la vista."""

SEMANAS_CRONICO = 10
"""Desde cuántas semanas con salida un producto es crónico: una de cada
cinco. Medido en las bajas de doce meses: con 10 son 68 productos y el
68 % del valor; con 8 serían 81 (72 %), con 15, 38 (55 %)."""

NOTA_PUNTUAL = 0.5
"""Un producto es puntual si UNA nota hace esta parte o más de lo suyo."""

CRONICO, OCASIONAL, PUNTUAL = "Crónico", "Ocasional", "Puntual"
GRUPOS = (CRONICO, OCASIONAL, PUNTUAL)
_QUE_ES = {CRONICO: "salida en 10 o más de las 52 semanas",
           OCASIONAL: "de vez en cuando",
           PUNTUAL: "una sola nota hace la mitad o más"}

FALTANTE_DESDE = "2025-09"
"""Desde qué mes el faltante del cierre se compara: antes, el ajuste del
cierre no es el que movió el stock (regla #612)."""


def ventana(fin):
    """`(inicio, fin)` de las 52 semanas que terminan en `fin` (exclusivo)."""
    fin = pd.Timestamp(fin).normalize()
    return fin - pd.Timedelta(days=7 * SEMANAS), fin


def grupo_de(semanas, mayor_nota):
    """CRÓNICO, PUNTUAL u OCASIONAL (ver `SEMANAS_CRONICO` y
    `NOTA_PUNTUAL`). Crónico manda: una costumbre con un mal día sigue
    siendo una costumbre."""
    if semanas >= SEMANAS_CRONICO:
        return CRONICO
    if mayor_nota >= NOTA_PUNTUAL:
        return PUNTUAL
    return OCASIONAL


def productos_bajas(lin, lin_vent, entradas, vent):
    """Una fila por producto de `lin`, de mayor a menor valorizado.

    `lin` son las líneas del RANGO de la vista y `lin_vent` las de las 52
    semanas `vent` (las dos con los mismos filtros), con `fecha`, `doc`,
    `cod`, `prod`, `cant`, `unid`, `valor` y `causa`. `entradas` son las
    entradas de todos los productos (`cod`, `fecha`, `cant`).

    Columnas: `cod`, `prod`, `valor`, `pct` (del total del rango), `cant`,
    `unid`, y de la ventana: `cant_vent`, `entro`, `tasa` (cant_vent ÷
    entro, en %; None sin entradas), `semanas`, `mayor_nota` (la parte de la
    nota mayor), `grupo` y `causa` (la de más valor)."""
    cols = ["cod", "prod", "valor", "pct", "cant", "unid", "cant_vent",
            "entro", "tasa", "semanas", "mayor_nota", "grupo", "causa"]
    if lin is None or lin.empty:
        return pd.DataFrame(columns=cols)
    g = (lin.groupby("cod", sort=False)
            .agg(prod=("prod", "first"), valor=("valor", "sum"),
                 cant=("cant", "sum"), unid=("unid", "first")))
    tot = float(g["valor"].sum())
    g["pct"] = g["valor"] / tot * 100.0 if tot else 0.0
    ini, fin = vent
    v = lin_vent[(lin_vent["fecha"] >= ini) & (lin_vent["fecha"] < fin)]
    v = v[v["cod"].isin(g.index)]
    sem = ((v["fecha"] - ini).dt.days // 7).clip(0, SEMANAS - 1)
    g["semanas"] = (v.assign(_s=sem).groupby("cod")["_s"].nunique()
                    .reindex(g.index).fillna(0).astype(int))
    g["cant_vent"] = v.groupby("cod")["cant"].sum().reindex(g.index)
    por_doc = v.groupby(["cod", "doc"])["valor"].sum()
    mayor = por_doc.groupby(level=0).max()
    total_v = v.groupby("cod")["valor"].sum()
    g["mayor_nota"] = ((mayor / total_v.where(total_v > 0))
                       .reindex(g.index).fillna(0.0))
    causa = (v.groupby(["cod", "causa"])["valor"].sum().reset_index()
              .sort_values(["cod", "valor"], ascending=[True, False])
              .drop_duplicates("cod").set_index("cod")["causa"])
    g["causa"] = causa.reindex(g.index).fillna("")
    e = entradas
    if e is not None and len(e):
        e = e[(e["fecha"] >= ini) & (e["fecha"] < fin)]
        g["entro"] = e.groupby("cod")["cant"].sum().reindex(g.index)
    else:
        g["entro"] = float("nan")
    ok = g["entro"] > 0
    g["tasa"] = (g["cant_vent"] / g["entro"] * 100.0).where(ok)
    g["grupo"] = [grupo_de(s, m) for s, m in zip(g["semanas"], g["mayor_nota"])]
    g = g.reset_index().sort_values("valor", ascending=False, kind="stable")
    return g[cols].reset_index(drop=True)


def faltante_por_mes(aj, col_fecha, col_valor, desde=FALTANTE_DESDE):
    """`{"2026-09": soles}`: el FALTANTE que contó el cierre de cada mes —la
    suma de los ajustes negativos, en positivo—, por MES OPERATIVO: el
    cierre de setiembre se cuenta del 1 al 7 de octubre y sus conteos se
    juntan (`cortes.sesiones_inventario`, regla #632). Los parciales no
    cuentan. Desde `desde`. Pura."""
    if aj is None or aj.empty or col_fecha not in aj.columns \
            or col_valor not in aj.columns:
        return {}
    dia = pd.to_datetime(aj[col_fecha], errors="coerce").dt.normalize()
    val = pd.to_numeric(aj[col_valor], errors="coerce").fillna(0.0)
    neg = (-val.where(val < 0, 0.0)).groupby(dia).sum()
    salida = {}
    for s in cortes.sesiones_inventario(dia.dropna()):
        if s["tipo"] != "cierre":
            continue
        a, m = s["mes"]
        mes = f"{a:04d}-{m:02d}"
        if mes < desde:
            continue
        dias = [pd.Timestamp(x) for x in s["dias"]]
        f = float(neg.reindex(dias).fillna(0.0).sum())
        if f > 0:
            salida[mes] = f
    return salida


def lineas_salidas(d, *, fecha, doc, cod, prod, cant, valor, unid=None,
                   causa=None, area=None, tipo=None, motivo=None):
    """Las líneas de `salidas.parquet` con los nombres de `productos_bajas`
    y de la ficha. Los argumentos son NOMBRES de columna; el que falta va
    vacío. Pura.

    `causa` es la de la baja y, en lo que NO es baja (vacía), el TIPO: «por
    qué salió» una pierna de cerdo de la comida de personal es «Comida
    Personal», no «sin causa escrita»."""
    def _txt(col):
        if not col or col not in d.columns:
            return pd.Series("", index=d.index, dtype=object)
        return d[col].fillna("").astype(str).str.strip()
    _c = _txt(causa)
    causa_o_tipo = _c.where(_c != "", _txt(tipo))
    return pd.DataFrame({
        "fecha": pd.to_datetime(d[fecha], errors="coerce"),
        "doc": _txt(doc), "cod": _txt(cod), "prod": _txt(prod),
        "cant": pd.to_numeric(d[cant], errors="coerce").fillna(0.0)
                if cant and cant in d.columns else 0.0,
        "valor": pd.to_numeric(d[valor], errors="coerce").fillna(0.0),
        "unid": _txt(unid), "causa": causa_o_tipo, "area": _txt(area),
        "tipo": _txt(tipo), "motivo": _txt(motivo),
    }).dropna(subset=["fecha"])


def meses_de_ventana(vent):
    """Los doce meses que terminan en el mes del último día de `vent`, como
    «2026-09»."""
    ult = (vent[1] - pd.Timedelta(days=1)).to_period("M")
    return [str(ult - i) for i in range(11, -1, -1)]


# ===========================================================================
# LAS CARGAS
# ===========================================================================

_ARCHIVOS_ENTRADA = ("compras.parquet", "ordenesproduccion.parquet",
                     "porcionamientos.parquet")
_ARCHIVO_AJUSTE = "ajusteinventario.parquet"


def _col(df, *nombres):
    for n in nombres:
        if n in df.columns:
            return n
    return None


def _entradas_de(compras, produccion, porcion):
    """Las entradas de cada producto, `cod`, `fecha`, `cant`: lo comprado
    (en la unidad del kardex en el 100 % de las líneas, regla #558), lo que
    produjeron las órdenes PROCESADAS (las generadas no produjeron nada,
    #575) y lo que salió de cada porcionamiento (sus cortes)."""
    partes = []

    def _parte(df, cod, fecha, cant, filtro=None):
        if df is None or df.empty:
            return
        c, f, q = _col(df, *cod), _col(df, *fecha), _col(df, *cant)
        if not (c and f and q):
            return
        d = df if filtro is None else df[filtro(df)]
        partes.append(pd.DataFrame({
            "cod": d[c].fillna("").astype(str).str.strip(),
            "fecha": pd.to_datetime(d[f], errors="coerce"),
            "cant": pd.to_numeric(d[q], errors="coerce").fillna(0.0)}))

    _parte(compras, ("COD_PRODUCTO",), ("FECHA_EMISION_DOC",),
           ("CANTIDAD_COMPRA",))

    def _procesada(df):
        e = _col(df, "NOMBRE ESTADO")
        if not e:
            return pd.Series(True, index=df.index)
        return df[e].fillna("").astype(str).str.strip().str.upper() == "PROCESADO"
    _parte(produccion, ("COD PRODUCTO",), ("FECHA REGISTRO",), ("CANTIDAD",),
           _procesada)
    _parte(porcion, ("COD PROD FINAL",), ("FEC REGIST",), ("CANT RESULT",))
    if not partes:
        return pd.DataFrame(columns=["cod", "fecha", "cant"])
    e = pd.concat(partes, ignore_index=True).dropna(subset=["fecha"])
    return e[e["cod"] != ""]


@st.cache_data(show_spinner=False, max_entries=2)
def _entradas_cacheable(sellos):
    """`_entradas_de` por versión de los tres parquets (regla #367)."""
    return _entradas_de(*(data.cargar(a) for a in _ARCHIVOS_ENTRADA))


def entradas():
    """Las entradas de todos los productos, o None si no se pudieron leer."""
    try:
        return _entradas_cacheable(
            tuple(data.sello_datos(a) for a in _ARCHIVOS_ENTRADA))
    except Exception:
        return None


@st.cache_data(show_spinner=False, max_entries=2)
def _faltante_cacheable(sello):
    aj = data.cargar(_ARCHIVO_AJUSTE)
    if aj is None:
        return {}
    return faltante_por_mes(aj, "FECHA APERTURA INVENTARIO",
                            "AJUSTE VALORIZADO")


def faltante_cierres():
    """`faltante_por_mes` del parquet de Ajuste, o {} si no se puede leer."""
    try:
        return _faltante_cacheable(data.sello_datos(_ARCHIVO_AJUSTE))
    except Exception:
        return {}


# ===========================================================================
# LO QUE SE DIBUJA
# ===========================================================================

CARD_PRODUCTOS = "ajuste_graf_card_izq_mov_detsal_prod"
CARD_FICHA = "ajuste_graf_card_izq_mov_detsal_ficha"
CARD_NOTAS = "ajuste_graf_card_izq_mov_detsal_notas"
"""El prefijo `ajuste_graf_card_izq_` les da el marco de las demás tarjetas
de Movimientos (`estilos/_80_cards.py`)."""

_K = "mov_bj"
K_GRUPO = f"{_K}_grupo"
K_FOCO = f"{_K}_foco"

_COLOR_GRUPO = {CRONICO: (ERROR, ERROR_FONDO),
                OCASIONAL: (ACENTO_TEXTO, LAVANDA_FONDO),
                PUNTUAL: (ADVERTENCIA, ADVERTENCIA_FONDO)}
"""`(tinta, fondo)` de cada grupo: rojo lo crónico —lo que se repite—, ámbar
lo puntual, lavanda lo ocasional."""

_GRUPOS_BOTONES = st.components.v2.component(
    "grupos_bajas_movimientos",
    js=js_movil((Path(__file__).parent / "movimientos_kpi.js").read_text(
        encoding="utf-8")),
    isolate_styles=False,
)
"""Los tres botones de frecuencia: el MISMO componente que la fila de KPI
de las tarjetas «por período» (`movimientos_kpi.js`, regla #649) —botones
`data-res` con `aria-pressed`, un clic elige y otro suelta—, con su CSS
propio (`_css`)."""


def _css():
    _botones = "".join(
        f".st-key-{_K}_grupos [data-res='{g}']{{--g:{t};--gbg:{f}}}"
        for g, (t, f) in _COLOR_GRUPO.items())
    return f"""<style>
.st-key-{_K}_grupos .mp-kpi-raiz{{display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}
.st-key-{_K}_grupos [data-res]{{font:inherit;text-align:left;cursor:pointer;
  border:1.5px solid var(--g);background:var(--gbg);color:{TEXTO_PRINCIPAL};
  border-radius:10px;padding:8px 14px;display:flex;flex-direction:column;
  gap:1px;min-height:60px}}
.st-key-{_K}_grupos [data-res]:hover{{box-shadow:0 3px 10px -4px var(--g)}}
.st-key-{_K}_grupos [data-res] .gn{{font-weight:700;font-size:14px;
  color:var(--g)}}
.st-key-{_K}_grupos [data-res] .gv{{font-size:12.5px;
  font-variant-numeric:tabular-nums}}
.st-key-{_K}_grupos [data-res] .gq{{font-size:11.5px;color:{GRIS_TEXTO}}}
.st-key-{_K}_grupos [data-res][aria-pressed='true']{{background:var(--g)}}
.st-key-{_K}_grupos [data-res][aria-pressed='true'] span{{color:{BLANCO}}}
{_botones}
.bj-cifras{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px}}
.bj-cifra{{border:1px solid {GRIS_BORDE};border-radius:10px;
  padding:6px 12px}}
.bj-cifra .k{{font-size:11.5px;color:{GRIS_TEXTO}}}
.bj-cifra .v{{font-size:16px;font-weight:700;
  font-variant-numeric:tabular-nums}}
.bj-cifra .s{{font-size:11.5px;color:{GRIS_TEXTO}}}
.bj-pill{{display:inline-block;border-radius:999px;padding:1px 9px;
  font-size:12.5px;font-weight:700;color:{BLANCO}}}
.bj-sem{{display:grid;grid-template-columns:repeat(26,minmax(0,1fr));gap:3px}}
.bj-sem i{{aspect-ratio:1;border-radius:3px;background:{GRIS_LINEA};
  display:block}}
.bj-causas{{display:flex;flex-direction:column;gap:5px;font-size:12px}}
.bj-causas div{{display:grid;grid-template-columns:150px minmax(0,1fr) 78px;
  gap:8px;align-items:center}}
.bj-causas s{{display:block;height:9px;border-radius:3px;
  background:{SERIE_PRINCIPAL};text-decoration:none}}
.bj-causas .m{{text-align:right;font-variant-numeric:tabular-nums}}
.bj-meses{{width:100%;border-collapse:collapse;font-size:11.5px;
  font-variant-numeric:tabular-nums}}
.bj-meses th,.bj-meses td{{padding:3px 4px;text-align:right;
  border-bottom:1px solid {GRIS_LINEA};white-space:nowrap}}
.bj-meses th{{color:{GRIS_TEXTO};font-weight:600;
  background:{GRIS_FONDO_CABECERA}}}
.bj-meses th:first-child,.bj-meses td:first-child{{text-align:left}}
.bj-meses td.alto{{color:{ERROR};font-weight:700}}
.bj-ayuda{{font-size:11.5px;color:{GRIS_TEXTO}}}
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


def _al_elegir_grupo():
    a = (st.session_state.get(f"{_K}_grupos") or {}).get("resaltar") or {}
    n = a.get("nombre")
    st.session_state[K_GRUPO] = n if n in GRUPOS else None


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
    foco, ANTES de dibujar: la lista nueva sale con él marcado."""
    ss = st.session_state
    key = ss.get(f"_{_K}_key")
    codigos = ss.get(f"_{_K}_codigos") or []
    fila = _fila_elegida(ss.get(key)) if key else None
    if fila is not None and 0 <= fila < len(codigos):
        ss[K_FOCO] = codigos[fila]


_SIN_DATO = -1.0
"""Lo que lleva la celda de «% de lo que entró» de un producto sin
entradas: `st.dataframe` pinta un vacío como «None» (regla #529), así que
la celda lleva un número que el Styler escribe «—»."""


def _tabla_productos(vis, foco):
    """La lista con su Styler; devuelve el código en foco."""
    codigos = vis["cod"].tolist()
    pos = codigos.index(foco) if foco in codigos else 0
    filas = pd.DataFrame({
        "Producto": vis["prod"],
        "Valorizado": vis["valor"].astype(float),
        "%": vis["pct"].astype(float),
        "Cantidad": [f"{fmt_cant(round(float(q), 2))} {unidad_corta(u)}".strip()
                     for q, u in zip(vis["cant"], vis["unid"])],
        "Entró · 52 sem.": [(f"{fmt_cant(round(float(e)))} {unidad_corta(u)}"
                             .strip() if pd.notna(e) and e > 0 else "—")
                            for e, u in zip(vis["entro"], vis["unid"])],
        "% de lo que entró": vis["tasa"].fillna(_SIN_DATO).astype(float),
        "Frecuencia": [f"{g} · " + (f"una nota = {m * 100:.0f} %" if g == PUNTUAL
                                    else f"{s} de {SEMANAS} sem.")
                       for g, s, m in zip(vis["grupo"], vis["semanas"],
                                          vis["mayor_nota"])],
    }).reset_index(drop=True)

    def _fmt_tasa(v):
        return "—" if v < 0 else f"{v:.1f} %"

    def _estilo_tasa(v):
        return f"color: {ERROR}; font-weight: 700" if v >= 15 else ""

    def _estilo_grupo(v):
        g = str(v).split(" ·")[0]
        tinta, fondo = _COLOR_GRUPO.get(g, (GRIS_TEXTO, ""))
        return f"color: {tinta}; background-color: {fondo}; font-weight: 600"

    def _fila(r):
        return ([f"background-color: {LAVANDA_FONDO}"] * len(r)
                if r.name == pos else [""] * len(r))

    sty = (filas.style
           .format({"Valorizado": "S/ {:,.0f}", "%": "{:.1f}",
                    "% de lo que entró": _fmt_tasa})
           .apply(_fila, axis=1)
           .map(_estilo_tasa, subset=["% de lo que entró"])
           .map(_estilo_grupo, subset=["Frecuencia"]))
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
            "Entró · 52 sem.": st.column_config.Column(
                help="Lo producido, porcionado y comprado del producto en las "
                     "52 semanas que terminan con el rango, en la unidad del "
                     "kardex"),
            "% de lo que entró": st.column_config.Column(
                help="Lo que salió en esas 52 semanas, en % de lo que entró. "
                     "En rojo desde 15 %. «—»: no entró nada (no hay contra "
                     "qué dividir)"),
            "Frecuencia": st.column_config.Column(
                help="Crónico: salida en 10 o más de las 52 semanas. Puntual: "
                     "una sola nota hace la mitad o más. Ocasional: el resto"),
        })
    return codigos[pos]


def seccion_productos(lin, lin_vent, vent):
    """La tarjeta de productos (regla #670) y, debajo, la ficha y las notas
    del elegido. `lin`, `lin_vent` y `vent` como en `productos_bajas`."""
    tabla = productos_bajas(lin, lin_vent, entradas(), vent)
    with st.container(border=True, key=CARD_PRODUCTOS):
        st.markdown(CSS_TITULOS_DRILL + _css(), unsafe_allow_html=True)
        st.markdown(
            '<div class="inv-rank-tit">Producto <span class="inv-rank-tit-n">'
            f"{len(tabla):,}</span></div>", unsafe_allow_html=True)
        if tabla.empty:
            st.info("Sin productos con salidas en estas fechas.")
            return
        grupo = st.session_state.get(K_GRUPO)
        if grupo not in GRUPOS:
            grupo = None
        with st.container(key=f"{_K}_grupos_caja"):
            _GRUPOS_BOTONES(
                key=f"{_K}_grupos", on_resaltar_change=_al_elegir_grupo,
                width="stretch", data={"html": _html_grupos(tabla, grupo)})
        vis = tabla[tabla["grupo"] == grupo] if grupo else tabla
        if vis.empty:
            st.info(f"Ningún producto {grupo.lower()} con estos filtros.")
            return
        _leer_foco()
        cod = _tabla_productos(vis.reset_index(drop=True),
                               st.session_state.get(K_FOCO))
    p = vis[vis["cod"] == cod].iloc[0]
    l_vent = lin_vent[(lin_vent["cod"] == cod)
                      & (lin_vent["fecha"] >= vent[0])
                      & (lin_vent["fecha"] < vent[1])]
    _ficha(p, l_vent, vent)


def _ficha(p, l, vent):
    """La ficha del producto `p` (una fila de `productos_bajas`) con sus
    líneas `l` de las 52 semanas."""
    u = unidad_corta(p["unid"])
    e = entradas()
    meses = meses_de_ventana(vent)
    ent_mes = pd.Series(dtype=float)
    if e is not None and len(e):
        _e = e[(e["cod"] == p["cod"]) & (e["fecha"] >= vent[0])
               & (e["fecha"] < vent[1])]
        ent_mes = _e.groupby(_e["fecha"].dt.to_period("M").astype(str))["cant"].sum()
    baja_mes = l.groupby(l["fecha"].dt.to_period("M").astype(str))["cant"].sum()
    q = [float(baja_mes.get(m, 0.0)) for m in meses]
    ent = [float(ent_mes.get(m, 0.0)) for m in meses]
    rot = [_rot_mes(m) for m in meses]
    with st.container(border=True, key=CARD_FICHA):
        st.markdown(CSS_TITULOS_DRILL + _css(), unsafe_allow_html=True)
        tinta, _f = _COLOR_GRUPO[p["grupo"]]
        tasa = ("—" if pd.isna(p["tasa"]) else f"{p['tasa']:.1f} %")
        ent_txt = ("no entró nada en 52 semanas" if pd.isna(p["entro"])
                   or not p["entro"] else f"entraron {fmt_cant(round(float(p['entro'])))} {u}")
        causa_v = float(l[l["causa"] == p["causa"]]["valor"].sum())
        tot_v = float(l["valor"].sum()) or 1.0
        st.markdown(
            f'<div class="inv-rank-tit">{escape(str(p["prod"]))}</div>'
            '<div class="bj-cifras">'
            f'<div class="bj-cifra"><div class="k">Salió en 52 semanas</div>'
            f'<div class="v">{_soles(tot_v)}</div><div class="s">'
            f'{fmt_cant(round(float(l["cant"].sum()), 2))} {u} · '
            f'{l["doc"].nunique():,} notas</div></div>'
            f'<div class="bj-cifra"><div class="k">De lo que entró</div>'
            f'<div class="v">{tasa}</div><div class="s">{ent_txt}</div></div>'
            f'<div class="bj-cifra"><div class="k">Frecuencia</div>'
            f'<div class="v"><span class="bj-pill" style="background:{tinta}">'
            f'{p["grupo"]}</span></div><div class="s">{p["semanas"]} de '
            f'{SEMANAS} semanas · la mayor nota, {p["mayor_nota"] * 100:.0f} %'
            '</div></div>'
            f'<div class="bj-cifra"><div class="k">Causa principal</div>'
            f'<div class="v" style="font-size:14px">'
            f'{escape(str(p["causa"]) or "—")}</div><div class="s">'
            f'{100 * causa_v / tot_v:.0f} % del valor</div></div></div>',
            unsafe_allow_html=True)
        # columnas-internas: el gráfico con su tabla | semanas y causas, dentro
        # de la ficha.
        c1, c2 = st.columns([1.6, 1], gap="medium")
        with c1:
            st.markdown('<div class="bj-ayuda">Salió por mes, en '
                        f'{u or "su unidad"}</div>', unsafe_allow_html=True)
            fig = go.Figure(go.Bar(
                x=rot, y=q, marker=dict(color=SERIE_PRINCIPAL),
                text=[fmt_cant(round(v, 1)) if v else "" for v in q],
                textposition="outside", cliponaxis=False,
                hovertemplate="%{x}: %{y:,.2f} " + u + "<extra></extra>"))
            _compras_layout(fig, alto=alturas.BAJAS_FICHA_FIG)
            fig.update_xaxes(type="category")
            fig.update_layout(margin=dict(l=10, r=10, t=14, b=10))
            st.plotly_chart(fig, use_container_width=True,
                            key=f"{_K}_ficha_fig")
            celdas = []
            for qi, ei in zip(q, ent):
                if not qi:
                    celdas.append("<td>—</td>")
                elif not ei:
                    celdas.append('<td title="No entró nada ese mes">s/e</td>')
                else:
                    pc = 100 * qi / ei
                    tip = (' title="Más que lo que entró ese mes: salió stock '
                           'de antes"' if pc > 100 else "")
                    celdas.append(f'<td class="{"alto" if pc >= 15 else ""}"'
                                  f"{tip}>{pc:.0f}%</td>")
            st.markdown(
                '<table class="bj-meses"><tr><th></th>'
                + "".join(f"<th>{r}</th>" for r in rot) + "</tr>"
                + "<tr><td>Entró</td>" + "".join(
                    f"<td>{fmt_cant(round(x)) if x else '—'}</td>" for x in ent)
                + "</tr><tr><td>Salió</td>" + "".join(
                    f"<td>{fmt_cant(round(x, 1)) if x else '—'}</td>" for x in q)
                + "</tr><tr><td>% de lo que entró</td>" + "".join(celdas)
                + "</tr></table>", unsafe_allow_html=True)
        with c2:
            st.markdown(_html_semanas(l, vent) + _html_causas(l),
                        unsafe_allow_html=True)
    _notas(l, u)


def _rot_mes(m):
    p = pd.Period(m, "M")
    return f"{cortes.MESES_ABR_ES[p.month - 1]} {str(p.year)[2:]}"


def _html_semanas(l, vent):
    v = [0.0] * SEMANAS
    s = ((l["fecha"] - vent[0]).dt.days // 7).clip(0, SEMANAS - 1)
    for i, x in l.assign(_s=s).groupby("_s")["valor"].sum().items():
        v[int(i)] = float(x)
    mx = max(v) or 1.0
    celdas = []
    for i, x in enumerate(v):
        d = vent[0] + pd.Timedelta(days=7 * i)
        tip = (f"Semana del {d.day} {cortes.MESES_ABR_ES[d.month - 1]} "
               f"{str(d.year)[2:]}: " + (_soles(x) if x else "sin salidas"))
        estilo = (f' style="background:{SERIE_PRINCIPAL};'
                  f'opacity:{0.3 + 0.7 * x / mx:.2f}"' if x else "")
        celdas.append(f'<i title="{tip}"{estilo}></i>')
    return ('<div class="bj-ayuda">Las 52 semanas, una por casillero: más '
            'oscuro, más soles. Un crónico llena las filas; un puntual deja '
            'una marca.</div><div class="bj-sem">' + "".join(celdas)
            + "</div>")


def _html_causas(l):
    c = l.groupby("causa")["valor"].sum().sort_values(ascending=False)
    c = c[c > 0]
    if c.empty:
        return ""
    tot = float(c.sum())
    filas = "".join(
        f'<div><span>{escape(str(n) or "Sin causa escrita")}</span>'
        f'<s style="width:{max(3.0, 100 * v / tot):.0f}%"></s>'
        f'<span class="m">{_soles(v)}</span></div>' for n, v in c.items())
    return ('<div class="bj-ayuda" style="margin-top:12px">Por qué salió</div>'
            f'<div class="bj-causas">{filas}</div>')


def _notas(l, u):
    """Las notas de salida del producto, de la más nueva a la más vieja."""
    with st.container(border=True, key=CARD_NOTAS):
        st.markdown(CSS_TITULOS_DRILL, unsafe_allow_html=True)
        st.markdown('<div class="inv-rank-tit">Sus notas de salida · 52 '
                    f'semanas <span class="inv-rank-tit-n">{l["doc"].nunique():,}'
                    "</span></div>", unsafe_allow_html=True)
        n = l.sort_values("fecha", ascending=False)
        filas = pd.DataFrame({
            "Fecha": n["fecha"].dt.strftime("%d/%m/%y"),
            "Nota": n["doc"],
            "Área": n["area"],
            "Tipo": n["tipo"],
            "Motivo escrito": n["motivo"].replace("", "—"),
            "Cantidad": [f"{fmt_cant(round(float(x), 3))} {u}".strip()
                         for x in n["cant"]],
            "S/": n["valor"].astype(float),
        })
        st.dataframe(
            filas.style.format({"S/": "{:,.2f}"}), hide_index=True,
            row_height=27,
            height=alturas.por_filas(len(filas), px_fila=27, extra=38,
                                     minimo=0, rol=alturas.BAJAS_NOTAS),
            column_config={"Motivo escrito": st.column_config.TextColumn(
                width="large")},
            key=f"{_K}_notas")
