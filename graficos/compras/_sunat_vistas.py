"""Las dos vistas de resumen de «Documentos SUNAT»: «Cruce con SUNAT» y
«Proveedores y fechas» (2026-10-21, regla #683).

Hasta ese día eran seis modos de una tarjeta DEBAJO de la tabla de
documentos («Este proveedor», «Por fecha», «Por proveedor», «Resumen del
cruce», «Por tipo de compra» y el conversor), y la tarjeta quedaba a medio
mostrar: tabla y tarjeta no caben juntas en una laptop. Se pidió (con un
mockup aprobado) que los resúmenes fueran PANTALLAS propias que llevan a la
tabla, y el conversor una ventana sobre ella:

  · **Cruce con SUNAT** (la vista que abre): la fidelidad por tipo de
    compra o por año, y cada fila se abre en lo que la explica — los
    proveedores que le bajan la fidelidad a un tipo, los tipos de un año.
  · **Proveedores y fechas**: una tabla agrupada por proveedor, mes o día;
    un proveedor se abre en sus doce meses y sus documentos.
  · «Ver estos documentos» lleva a la vista «Documentos» con la tabla ya
    filtrada (`LLEGADA`), y un aviso arriba para volver.

Las dos son una pieza propia (`sunat_vistas.js` + `.css`, un
`st.components.v2` sin iframe, como las listas de Ajuste): abrir una fila,
cambiar de soles a documentos o reordenar es del navegador y no cuesta una
corrida. A Python le llega un solo trigger, «ir», con lo que la tabla tiene
que filtrar.

Este módulo arma los datos (funciones puras, las prueba `test_graficos.py`)
y monta la pieza. El cruce y su censo los calcula `documentos_sunat.py`.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

import tipo_compra
from cortes import MESES_ABR_ES

_AQUI = Path(__file__).parent
_PIEZA = st.components.v2.component(
    "sunat_vistas",
    css=(_AQUI / "sunat_vistas.css").read_text(encoding="utf-8"),
    js=(_AQUI / "sunat_vistas.js").read_text(encoding="utf-8"),
)

VISTA_CRUCE = "Cruce con SUNAT"
VISTA_PROV = "Proveedores y fechas"
VISTA_DOCS = "Documentos"
VISTAS = (VISTA_CRUCE, VISTA_PROV, VISTA_DOCS)
"""Las vistas del reporte, en el orden del rail. La primera es la que abre."""

K_VISTA = "sunat_graf_tipo"
"""El `state_key` del rail del reporte (`sunat_reporte.py`)."""

K_LLEGADA = "sunat_llegada"
"""Lo que la tabla de «Documentos» filtra al llegar desde un resumen:
`{"desde", "tipo", "estados", "fini", "ffin", "texto"}`. No es un widget:
lo escribe el callback de la pieza y lo borra «Quitar filtro». El proveedor
no viaja acá: se escribe en el espejo del filtro de proveedor de la tabla,
que es un control a la vista (`documentos_sunat._filtro_proveedor`)."""

_PENDIENTES = ("Solo SUNAT", "Diferencia")
_SIN_TIPO = "Sin clasificar"
_MAX_DOCS_FILA = 8
_MAX_DET = 8


# ── datos ───────────────────────────────────────────────────────────────
#
# TODO SE AGRUPA DE UNA VEZ (regla #537): la primera versión filtraba el
# cruce proveedor por proveedor y armaba «Proveedores y fechas» en 21 s
# sobre un año (5.373 documentos); con un groupby por partición, en
# ~1,5 s. `_base` deja una fila por documento con lo que hace falta, y
# `_fid_por` saca la fidelidad de cada grupo de una tabla de conteos.

_TRAMO = {"Coincide": "cuadran", "Diferencia": "diferencia",
          "Solo SUNAT": "falta", "Solo sistema": "fuera"}
"""Del estado del cruce al tramo de la fidelidad (`_TRAMOS_FIDELIDAD`)."""


def _vacia():
    return {"doc": {k: 0 for k in ("sunat", "cuadran", "diferencia", "falta", "fuera")},
            "soles": {k: 0.0 for k in ("sunat", "cuadran", "diferencia", "falta", "fuera")},
            # Las NOTAS DE CRÉDITO de cada tramo (2026-10-21, a pedido): la
            # fidelidad las cuenta en valor absoluto, y sin decirlo «falta
            # cargar S/ 4,426» se lee como compra real cuando una parte es
            # plata que el proveedor devuelve.
            "nc": {"falta": 0, "falta_s": 0.0, "diferencia": 0,
                   "diferencia_s": 0.0, "n": 0, "s": 0.0}}


def _tipos(df):
    """El tipo de compra de cada fila, con «Sin clasificar» para la raya."""
    if df is None or "tipo" not in getattr(df, "columns", ()):
        return pd.Series(_SIN_TIPO, index=getattr(df, "index", None), dtype="object")
    t = df["tipo"].fillna("").astype(str).str.strip()
    return t.where(~t.isin(("", "—")), _SIN_TIPO)


def _orden_tipos(serie):
    orden = [t for t in tipo_compra.TIPOS if (serie == t).any()]
    orden += sorted(set(serie) - set(orden) - {_SIN_TIPO})
    if (serie == _SIN_TIPO).any():
        orden.append(_SIN_TIPO)
    return orden


def _base(df):
    """Una fila por documento del cruce con lo que usan las vistas: el
    proveedor (clave y nombre, mirando los DOS lados: las «Solo sistema» no
    tienen el del SIRE), el tipo, el tramo y los soles. Los de SUNAT y los
    del sistema EN VALOR ABSOLUTO, como `_fidelidad_cruce`: una nota de
    crédito sin cargar es plata que no cuadra, no plata que resta."""
    from graficos.compras.documentos_sunat import _claves_proveedor_cruce
    nom = df["proveedor"].fillna("").astype(str).str.strip()
    nom = nom.where(nom != "", df["proveedor_sistema"].fillna("").astype(str).str.strip())
    ruc = df["ruc_proveedor"].fillna("").astype(str).str.strip()
    ruc = ruc.where(ruc != "", df["ruc_sistema"].fillna("").astype(str).str.strip())
    ts = pd.to_numeric(df["total_sunat"], errors="coerce").fillna(0.0).abs()
    tq = pd.to_numeric(df["total_sistema"], errors="coerce").fillna(0.0).abs()
    est = df["estado"].astype(str)
    return pd.DataFrame({
        "k": _claves_proveedor_cruce(df).astype(str), "nom": nom, "ruc": ruc,
        "tipo": _tipos(df), "tramo": est.map(_TRAMO).fillna("fuera"), "est": est,
        # Lo que cuenta en soles: el lado SUNAT para lo que SUNAT tiene, el
        # del sistema para lo que sólo está en el sistema.
        "s": ts.where(est != "Solo sistema", tq),
        # Lo que se lee como «monto del documento» en una lista.
        "monto": pd.to_numeric(df["total_sunat"], errors="coerce").fillna(
            pd.to_numeric(df["total_sistema"], errors="coerce")).fillna(0.0),
        "fe": pd.to_datetime(df["fecha_emision"], errors="coerce"),
        "doc": df["documento"].fillna("").astype(str),
        # Una nota de crédito viene en NEGATIVO en el cruce (regla #604).
        "nc": pd.to_numeric(df["total_sunat"], errors="coerce").fillna(
            pd.to_numeric(df["total_sistema"], errors="coerce")).fillna(0.0) < 0,
    }, index=df.index)


def _fid_por(b, por):
    """`{grupo: fidelidad}` con UN groupby. `por` son una o más columnas de
    `b`; con varias, la clave es la tupla."""
    out = {}
    if b is None or b.empty:
        return out
    g = (b.groupby(por + ["tramo"], sort=False)["s"]
         .agg(["size", "sum"]).reset_index())
    claves = (list(zip(*(g[c] for c in por))) if len(por) > 1 else list(g[por[0]]))
    for clave, tramo, n, s in zip(claves, g["tramo"], g["size"], g["sum"]):
        f = out.setdefault(clave, _vacia())
        f["doc"][tramo] += int(n)
        f["soles"][tramo] = round(f["soles"][tramo] + float(s), 2)
    for f in out.values():
        for m in ("doc", "soles"):
            f[m]["sunat"] = f[m]["cuadran"] + f[m]["diferencia"] + f[m]["falta"]
        f["soles"]["sunat"] = round(f["soles"]["sunat"], 2)
    # Las notas de crédito de cada grupo, por tramo: otro groupby, sólo
    # sobre las notas.
    bn = b[b["nc"] & (b["tramo"] != "fuera")] if "nc" in b.columns else b.iloc[0:0]
    if not bn.empty:
        g = (bn.groupby(por + ["tramo"], sort=False)["s"]
             .agg(["size", "sum"]).reset_index())
        claves = (list(zip(*(g[c] for c in por))) if len(por) > 1 else list(g[por[0]]))
        for clave, tramo, n, s in zip(claves, g["tramo"], g["size"], g["sum"]):
            nc = out[clave]["nc"]
            nc["n"] += int(n)
            nc["s"] = round(nc["s"] + float(s), 2)
            if tramo in ("falta", "diferencia"):
                nc[tramo] += int(n)
                nc[tramo + "_s"] = round(nc[tramo + "_s"] + float(s), 2)
    return out


def _fid(b):
    return _fid_por(b.assign(_todo=0), ["_todo"]).get(0, _vacia())


def _nombres(b):
    """`{clave: nombre}`: cualquier nombre real gana contra el vacío."""
    return b.groupby("k", sort=False)["nom"].max().to_dict()


def _pct(f, medida):
    b = f[medida]["sunat"]
    return None if not b else round(f[medida]["cuadran"] / b * 100, 1)


def datos_cruce(censo, previos=(), rango="", recientes=None, etiqueta=""):
    """Lo que dibuja «Cruce con SUNAT». Pura.

    `censo` es el cruce del período (rango, «Mes en SUNAT» y proveedor; el
    filtro de estado no, que elige DENTRO de este censo). `previos` es
    `[(etiqueta del año, rango, cruce o None, motivo), ...]` del más nuevo
    al más viejo: el mismo rango corrido atrás, ya clasificado por tipo.
    `etiqueta` es el año del período actual («2025-26»), para cuando se lo
    lista junto a los otros.

    Una fila por tipo con sus proveedores pendientes como detalle, y una
    por año con sus tipos como detalle: las dos formas de partir el mismo
    total. Cada año trae sus tipos, así que la pieza arma sola «un tipo año
    por año» y «tipo × año» (regla #694)."""
    b = _base(censo)
    orden = _orden_tipos(b["tipo"])
    por_tipo = _fid_por(b, ["tipo"])
    prev = next((p for p in previos if p[2] is not None), None)
    bp = _base(prev[2]) if prev else None
    prev_tipo = _fid_por(bp, ["tipo"]) if prev else {}
    nombres = _nombres(b)

    # Los proveedores que le bajan la fidelidad a cada tipo: los que tienen
    # algo sin cargar o con diferencia, de más a menos soles pendientes.
    pend = b[b["est"].isin(_PENDIENTES)]
    por_tk = _fid_por(b[b["k"].isin(set(pend["k"]))], ["tipo", "k"])
    det = {}
    for (tipo, k), f in por_tk.items():
        if f["doc"]["falta"] or f["doc"]["diferencia"]:
            det.setdefault(tipo, []).append({"k": k, "nombre": nombres.get(k) or k, "f": f})
    for lista in det.values():
        lista.sort(key=lambda x: -(x["f"]["soles"]["falta"] + x["f"]["soles"]["diferencia"]))

    def _pp(f):
        return {m: _pct(f, m) for m in ("doc", "soles")} if f else None

    total_f = _fid(b)
    tipos = [{"id": t, "nombre": t, "f": por_tipo[t],
              "prev": _pp(prev_tipo.get(t)) if prev else None,
              "det": det.get(t, [])[:_MAX_DET]} for t in orden]
    total = {"id": "__total", "nombre": "Total del período", "sub": rango,
             "f": total_f, "prev": _pp(_fid(bp)) if prev else None}

    def _tipos_de(bx):
        ft = _fid_por(bx, ["tipo"])
        return [{"id": t, "nombre": t, "f": ft[t]} for t in _orden_tipos(bx["tipo"])]

    anios = [{"id": "actual", "nombre": "Período actual", "anio": etiqueta or "Actual",
              "sub": rango, "f": total_f, "det": _tipos_de(b), "actual": True}]
    avisos = []
    for etiqueta, r, df, motivo in previos:
        if df is None:
            avisos.append(f"{etiqueta} ({r}): sin datos — {motivo}.")
            continue
        bx = _base(df)
        anios.append({"id": etiqueta, "nombre": etiqueta, "anio": etiqueta, "sub": r, "f": _fid(bx),
                      "det": _tipos_de(bx), "actual": False})
    return {
        "vista": "cruce", "rango": rango,
        "anio_prev": prev[0] if prev else None,
        "total": total, "tipos": tipos, "anios": anios, "avisos": avisos,
        "recientes": recientes or {"doc": 0, "soles": 0.0, "dias": 7},
    }


def _fecha_txt(v):
    return "" if v is None or pd.isna(v) else f"{v.day} {MESES_ABR_ES[v.month - 1]}"


def _listas_docs(b, por, solo_pendientes=False):
    """`{grupo: [documento, ...]}`, los más nuevos primero y a lo sumo
    `_MAX_DOCS_FILA` por grupo. Un sort y un groupby para todos."""
    x = b[b["est"].isin(_PENDIENTES)] if solo_pendientes else b
    x = (x.sort_values("fe", ascending=False, kind="stable")
         .groupby(por, sort=False).head(_MAX_DOCS_FILA))
    out = {}
    for g, fe, doc, nom, v, e in zip(x[por], x["fe"], x["doc"], x["nom"], x["monto"], x["est"]):
        out.setdefault(g, []).append({"fe": _fecha_txt(fe), "doc": doc, "prov": nom,
                                      "total": round(float(v), 2), "est": e})
    return out


def meses_serie(fin, n=12):
    """Los `n` meses que terminan en el de `fin`, como `Period`."""
    p = pd.Timestamp(fin).to_period("M")
    return [p - i for i in range(n - 1, -1, -1)]


def series_proveedores(registro, fin, n=12):
    """`{ruc: [total por mes]}` de los `n` meses que terminan en `fin`, sobre
    el registro COMPLETO del SIRE (no el rango): es lo que dice cómo viene
    cada proveedor. UN groupby para todos (regla #537)."""
    meses = meses_serie(fin, n)
    if registro is None or getattr(registro, "empty", True):
        return {}
    r = pd.DataFrame({
        "ruc": registro["ruc_proveedor"].astype(str).str.strip(),
        "mes": pd.to_datetime(registro["fecha_emision"], errors="coerce").dt.to_period("M"),
        "total": pd.to_numeric(registro["total"], errors="coerce").fillna(0.0),
    })
    r = r[r["mes"].isin(meses)]
    g = r.groupby(["ruc", "mes"], sort=False)["total"].sum()
    out = {}
    for (ruc, mes), v in g.items():
        out.setdefault(ruc, [0.0] * n)[meses.index(mes)] = round(float(v), 2)
    return out


_DIAS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


def datos_proveedores(censo, series=None, fin=None, n_meses=12):
    """Lo que dibuja «Proveedores y fechas». Pura.

    Tres agrupaciones del MISMO censo, que la pieza alterna sin volver a
    Python: por proveedor (con su serie de 12 meses y sus documentos), por
    mes y por día (con los proveedores del grupo y lo pendiente)."""
    if censo is None or censo.empty:
        return {"vista": "prov", "meses": [], "prov": [], "mes": [], "dia": []}
    series = series or {}
    b = _base(censo)
    meses = meses_serie(fin or b["fe"].max(), n_meses)
    nombres = _nombres(b)
    rucs = b.groupby("k", sort=False)["ruc"].max().to_dict()
    tipo_k = (b.groupby(["k", "tipo"], sort=False).size().reset_index(name="n")
              .sort_values("n", ascending=False, kind="stable")
              .drop_duplicates("k").set_index("k")["tipo"].to_dict())
    ult = b.groupby("k", sort=False)["fe"].max().to_dict()
    fids = _fid_por(b, ["k"])
    docs = _listas_docs(b, "k")
    provs = [{
        "k": k, "nombre": nombres.get(k) or k, "ruc": rucs.get(k, ""),
        "tipo": tipo_k.get(k, ""), "f": f, "ult": _fecha_txt(ult.get(k)),
        "serie": series.get(rucs.get(k, ""), [0.0] * n_meses),
        "docs": docs.get(k, []),
    } for k, f in fids.items()]

    def _grupos(gid, rotulo):
        bx = b.assign(g=gid)
        bx = bx[bx["g"].notna()]
        fg = _fid_por(bx, ["g"])
        nprov = bx.groupby("g", sort=False)["k"].nunique().to_dict()
        rango_g = bx.groupby("g", sort=False)["fe"].agg(["min", "max"])
        top = (bx.groupby(["g", "nom"], sort=False)["s"].sum().reset_index()
               .sort_values("s", ascending=False, kind="stable")
               .groupby("g", sort=False).head(6))
        tops = {}
        for g_, n_, v_ in zip(top["g"], top["nom"], top["s"]):
            tops.setdefault(g_, []).append({"nombre": n_, "v": round(float(v_), 2)})
        pend = _listas_docs(bx, "g", solo_pendientes=True)
        return [{
            "k": str(g_), "nombre": rotulo(g_), "f": fg[g_], "nprov": int(nprov[g_]),
            "fini": f"{rango_g.loc[g_, 'min']:%Y-%m-%d}",
            "ffin": f"{rango_g.loc[g_, 'max']:%Y-%m-%d}",
            "top": tops.get(g_, []), "docs": pend.get(g_, []),
        } for g_ in sorted(fg, reverse=True)]

    def _rot_mes(p):
        return f"{MESES_ABR_ES[p.month - 1].capitalize()} {p.year}"

    def _rot_dia(d):
        return f"{_DIAS[d.dayofweek]} {d.day} {MESES_ABR_ES[d.month - 1]} {d.year}"

    return {
        "vista": "prov",
        "meses": [f"{MESES_ABR_ES[p.month - 1]} {p.year % 100:02d}" for p in meses],
        "prov": provs,
        "mes": _grupos(b["fe"].dt.to_period("M"), _rot_mes),
        "dia": _grupos(b["fe"].dt.normalize(), _rot_dia),
    }


# ── la llegada a la tabla ───────────────────────────────────────────────

def aplicar_llegada(df, llegada):
    """El cruce recortado por lo que pidió el resumen (tipo, estados, días).
    Pura. Sin llegada, el df tal cual."""
    if df is None or df.empty or not llegada:
        return df
    m = pd.Series(True, index=df.index)
    if llegada.get("tipo"):
        m &= _tipos(df) == llegada["tipo"]
    if llegada.get("estados"):
        m &= df["estado"].isin(llegada["estados"])
    if llegada.get("fini") and llegada.get("ffin"):
        fe = pd.to_datetime(df["fecha_emision"], errors="coerce").dt.normalize()
        m &= (fe >= pd.Timestamp(llegada["fini"])) & (fe <= pd.Timestamp(llegada["ffin"]))
    return df[m]


def texto_llegada(llegada, prov_nombre=None):
    """«Mercadería · Falta cargar o con diferencia», para el aviso."""
    partes = []
    if llegada.get("tipo"):
        partes.append(llegada["tipo"])
    if prov_nombre:
        partes.append(prov_nombre)
    if llegada.get("rotulo"):
        partes.append(llegada["rotulo"])
    est = llegada.get("estados") or []
    if set(est) == set(_PENDIENTES):
        partes.append("falta cargar o con diferencia")
    elif est:
        partes.append(" o ".join(e.lower() for e in est))
    return " · ".join(partes)


def _al_ir():
    """Callback de la pieza: «Ver estos documentos» y los clics que llevan a
    la tabla. Corre ANTES de la corrida, así que el rail ya la dibuja en
    «Documentos»."""
    from graficos.compras import documentos_sunat as ds
    ss = st.session_state
    pedido = None
    for k in ("sunat_pieza_cruce", "sunat_pieza_prov"):
        v = (ss.get(k) or {}).get("ir")
        if v and v.get("t") and v.get("t") != ss.get("_sunat_ir_t"):
            pedido = v
    if not pedido:
        return
    ss["_sunat_ir_t"] = pedido["t"]
    # `prov` se anota también: «Quitar filtro» y «← Volver» lo sueltan.
    ss[K_LLEGADA] = {k: pedido.get(k) for k in ("desde", "tipo", "estados", "fini",
                                                "ffin", "rotulo", "prov")}
    # El proveedor, en el filtro de la tabla: es un control a la vista.
    ds.poner_proveedor(pedido.get("prov"))
    ds.poner_estado(None)
    ss[K_VISTA] = VISTA_DOCS


# ── montar ──────────────────────────────────────────────────────────────

def dibujar(datos, key):
    """Monta la pieza con `datos` (de `datos_cruce` o `datos_proveedores`)."""
    _PIEZA(key=key, data=datos, on_ir_change=_al_ir, width="stretch")
