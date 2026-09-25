"""
herramientas/cuadrar_ventas.py — la venta de la app contra el POS, día por
día (regla #524).

La definición de venta (`definicion_venta.py`) se cuadró al céntimo contra
el sistema de caja el 2026-09-24. Esto es ese cuadre hecho herramienta, para
repetirlo cuando cambie la definición, la consulta del Sheet que arma
`ventas.parquet` o el POS mismo — un test no puede: necesita R2 y el SQL
Server del restaurante.

    python herramientas/cuadrar_ventas.py
    python herramientas/cuadrar_ventas.py --desde 2026-09-01 --hasta 2026-09-23

Sin fechas, los últimos 30 días hasta ayer. Se corre desde la raíz del repo
(lee `.streamlit/secrets.toml` como la app). Sale con código 1 si algún día
no cuadra.

QUÉ COMPARA, por día (fecha de registro del comprobante):

    la app (data.cargar_rango: lo       el POS (INFOREST)
    mismo que recibe la vista)
    ─────────────────────────────       ─────────────────────────────────────
    facturas y boletas                  MDOCUMENTO tipo ≠ 00, estado 02 o 03
    notas de crédito (negativas)        MNOTACREDITO, estado ≠ 04
    cortesías                           MDOCUMENTO tipo 00, estado ≠ 04
    anulados                            MDOCUMENTO estado 04
    propinas                            DPAGODOCUMENTO de lo no anulado
    clientes                            MPEDIDO.nAdulto, con la regla de
                                        `definicion_venta.pax_por`

La app lee el parquet que dejó el extractor de la madrugada: un día de HOY
no cuadra hasta la próxima corrida, y por eso el default termina ayer.

Todo lo del POS pasa por `sql_restaurante.conectar`: el login que sólo
puede leer, READ UNCOMMITTED y la transacción que se deshace al final.
"""

import argparse
import datetime as dt
import pathlib
import sys

import pandas as pd

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "herramientas"))

import definicion_venta as dv  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Los montos del POS por día. `?` son los dos límites, desde y hasta+1.
_SQL_MONTOS = """
SELECT CONVERT(varchar(10), fRegistro, 120) AS dia,
  SUM(CASE WHEN tTipoDocumento <> '00' AND tEstadoDocumento IN ('02', '03')
           THEN nVenta ELSE 0 END) AS documentos,
  SUM(CASE WHEN tTipoDocumento = '00' AND tEstadoDocumento <> '04'
           THEN nVenta ELSE 0 END) AS cortesias,
  SUM(CASE WHEN tEstadoDocumento = '04' THEN nVenta ELSE 0 END) AS anulados
FROM MDOCUMENTO
WHERE fRegistro >= ? AND fRegistro < ?
GROUP BY CONVERT(varchar(10), fRegistro, 120)
"""
_SQL_NOTAS = """
SELECT CONVERT(varchar(10), fRegistro, 120) AS dia, -SUM(nVenta) AS notas
FROM MNOTACREDITO
WHERE fRegistro >= ? AND fRegistro < ? AND tEstadoDocumento <> '04'
GROUP BY CONVERT(varchar(10), fRegistro, 120)
"""
_SQL_PROPINAS = """
SELECT CONVERT(varchar(10), m.fRegistro, 120) AS dia,
       SUM(p.nPropina) AS propinas
FROM DPAGODOCUMENTO p JOIN MDOCUMENTO m ON m.tDocumento = p.tDocumento
WHERE m.fRegistro >= ? AND m.fRegistro < ? AND m.tEstadoDocumento <> '04'
GROUP BY CONVERT(varchar(10), m.fRegistro, 120)
"""
# Un renglón por (día, comprobante, pedido): los que suman con su pax y las
# notas con el pax del pedido que anulan, en negativo — lo que `pax_por`
# espera. Una nota por menos que el total no resta clientes en la app; acá
# no se distingue porque no hubo ninguna (22 en el histórico, todas por el
# total).
_SQL_PAX = """
SELECT CONVERT(varchar(10), m.fRegistro, 120) AS dia, m.tDocumento AS doc,
       d.tCodigoPedido AS ped, pe.nAdulto AS pax
FROM MDOCUMENTO m
JOIN (SELECT DISTINCT tDocumento, tCodigoPedido FROM DDOCUMENTO) d
  ON d.tDocumento = m.tDocumento
JOIN MPEDIDO pe ON pe.tCodigoPedido = d.tCodigoPedido
WHERE m.fRegistro >= ? AND m.fRegistro < ?
  AND m.tTipoDocumento <> '00' AND m.tEstadoDocumento IN ('02', '03')
UNION ALL
SELECT CONVERT(varchar(10), n.fRegistro, 120), n.tNotaCredito,
       d.tCodigoPedido, -pe.nAdulto
FROM MNOTACREDITO n
JOIN (SELECT DISTINCT tDocumento, tCodigoPedido FROM DDOCUMENTO) d
  ON d.tDocumento = n.tDocumento
JOIN MPEDIDO pe ON pe.tCodigoPedido = d.tCodigoPedido
WHERE n.fRegistro >= ? AND n.fRegistro < ? AND n.tEstadoDocumento <> '04'
"""


def _consulta(cn, sql, desde, hasta, veces=1):
    lim = [desde.strftime("%Y%m%d"),
           (hasta + dt.timedelta(days=1)).strftime("%Y%m%d")] * veces
    cur = cn.cursor()
    cur.execute(sql, lim)
    cols = [c[0] for c in cur.description]
    return pd.DataFrame.from_records([tuple(f) for f in cur.fetchall()],
                                     columns=cols)


def lado_pos(desde, hasta):
    """DataFrame por día con las seis cifras del POS."""
    from sql_restaurante import _servidor_local, conectar

    servidor = _servidor_local()
    if not servidor:
        sys.exit("Falta %USERPROFILE%\\.sql_restaurante.json con el "
                 "servidor (ver herramientas/sql_restaurante.py).")
    cn = conectar("INFOREST", 120, servidor)
    try:
        partes = [_consulta(cn, q, desde, hasta).set_index("dia")
                  for q in (_SQL_MONTOS, _SQL_NOTAS, _SQL_PROPINAS)]
        pax = _consulta(cn, _SQL_PAX, desde, hasta, veces=2)
    finally:
        cn.rollback()
        cn.close()
    pos = pd.concat(partes, axis=1).astype(float)
    pos["clientes"] = dv.pax_por(pax, "ped", "pax", doc="doc", por="dia")
    return pos.fillna(0.0)


def lado_app(desde, hasta):
    """Las mismas cifras, de lo que `data.cargar_rango` le entrega a la app."""
    import data  # importa streamlit: sus avisos de «bare mode» son ruido

    df = data.cargar_rango("ventas.parquet", "FEC REG DOCUMENTO", desde, hasta)
    if df is None or df.empty:
        sys.exit("La app no trajo ventas para ese rango.")
    dia = pd.to_datetime(df[dv.FECHA]).dt.strftime("%Y-%m-%d")
    df = df.assign(_dia=dia)
    llave = df[dv.LLAVE_ITEM]
    items = df[~(llave.duplicated() & llave.notna())]
    venta = pd.to_numeric(items[dv.VENTA_ITEM], errors="coerce").fillna(0.0)
    por_clase = (venta.groupby([items["_dia"], items[dv.CLASE]]).sum()
                 .unstack(fill_value=0.0))
    app = pd.DataFrame({
        "documentos": por_clase.get(dv.VENTA, 0.0),
        "notas": por_clase.get(dv.NOTA_CREDITO, 0.0),
        "cortesias": por_clase.get(dv.CORTESIA, 0.0),
        "anulados": por_clase.get(dv.ANULADO, 0.0),
    })
    pagos = df[df[dv.CLASE] != dv.ANULADO].drop_duplicates(dv.LLAVE_PAGO)
    app["propinas"] = (pd.to_numeric(pagos["MONTO PROPINA"], errors="coerce")
                       .fillna(0.0).groupby(pagos["_dia"]).sum())
    app["clientes"] = dv.pax_por(dv.solo_venta(items), "LLAVE LOCAL PEDIDO",
                                 dv.PAX, doc=dv.LLAVE_DOC, por="_dia")
    return app.fillna(0.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ayer = dt.date.today() - dt.timedelta(days=1)
    ap.add_argument("--desde", type=dt.date.fromisoformat,
                    default=ayer - dt.timedelta(days=29))
    ap.add_argument("--hasta", type=dt.date.fromisoformat, default=ayer)
    ap.add_argument("--tolerancia", type=float, default=0.01,
                    help="soles (o clientes) de diferencia que se aceptan")
    a = ap.parse_args()

    pos = lado_pos(a.desde, a.hasta)
    app = lado_app(a.desde, a.hasta)
    dias = sorted(set(pos.index) | set(app.index))
    pos, app = pos.reindex(dias, fill_value=0.0), app.reindex(dias,
                                                              fill_value=0.0)
    cifras = list(pos.columns)
    dif = (app[cifras] - pos[cifras]).round(2)
    malos = dif[(dif.abs() > a.tolerancia).any(axis=1)]

    print(f"\nCuadre de ventas · {a.desde} a {a.hasta} · {len(dias)} días")
    print(f"Definición: {dv.DEFINICION}\n")
    tot = pd.DataFrame({"app": app[cifras].sum(), "POS": pos[cifras].sum()})
    tot["diferencia"] = (tot["app"] - tot["POS"]).round(2)
    tot.loc["= venta"] = [app["documentos"].sum() + app["notas"].sum(),
                          pos["documentos"].sum() + pos["notas"].sum(), 0.0]
    tot.loc["= venta", "diferencia"] = round(
        tot.loc["= venta", "app"] - tot.loc["= venta", "POS"], 2)
    print(tot.to_string(float_format=lambda v: f"{v:,.2f}"))
    if malos.empty:
        print(f"\n✅ Los {len(dias)} días cuadran (tolerancia "
              f"{a.tolerancia:g}).")
        return
    print(f"\n❌ {len(malos)} día(s) no cuadran — app menos POS:")
    print(malos.loc[:, (malos.abs() > a.tolerancia).any()].to_string())
    sys.exit(1)


if __name__ == "__main__":
    main()
