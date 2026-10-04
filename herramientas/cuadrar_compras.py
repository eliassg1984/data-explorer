"""
herramientas/cuadrar_compras.py — la compra de la app contra el Almacén,
proveedor por proveedor (regla #603).

Las notas de crédito de los proveedores se restan al cargar
(`definicion_compra.py`). Esto es el cuadre de esa resta hecho herramienta,
para repetirlo cuando cambie la regla, la consulta del Sheet o el Almacén
mismo — un test no puede: necesita R2 y el SQL Server del restaurante.

    python herramientas/cuadrar_compras.py
    python herramientas/cuadrar_compras.py --desde 2026-09-01 --hasta 2026-09-30

Sin fechas, el último mes cerrado. Se corre desde la raíz del repo (lee
`.streamlit/secrets.toml` como la app). Sale con código 1 si algún
proveedor no cuadra.

QUÉ COMPARA, por proveedor, con la FECHA DE EMISIÓN de la factura:

    la app (data.cargar: lo que           el Almacén (ALMACEN)
    recibe la vista)
    ──────────────────────────────        ──────────────────────────────────
    Σ VALOR_COMPRA, con las notas         Σ MDOCUMENTO.nNeto en soles: estado
    de crédito restadas                   02, sin canjear, tipos no internos
                                          − las notas procesadas (02 y 03) de
                                            esas facturas, en soles con el
                                            cambio de su factura

Si `notascreditocompras.parquet` todavía no está en R2 (falta la fila del
Sheet), arma el lado de la app con las notas leídas del Almacén con la MISMA
consulta (`definicion_compra.consulta_sheet()`), y lo dice.

Aparte lista las notas que caen en un mes distinto que su factura: son las
que hacen que el mes no dé lo mismo que el Ranking del POS o el Registro de
Compras, que las restan en SU fecha. Y el resto de la distancia al Ranking
no es de las notas: es el tipo de ingreso (el Ranking cuenta sólo
Mercadería) — ver la memoria del cuadre del 2026-10-04 en la regla #603.

Todo lo del Almacén pasa por `sql_restaurante.conectar`: el login que sólo
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

import definicion_compra as dc  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Lo que trae compras.parquet: lo procesado, sin las guías canjeadas, de
# todo tipo que no sea un movimiento interno del kardex. `?` = desde, hasta+1.
_SQL_FACTURAS = """
SELECT MDOCUMENTO.tCodigoProveedor AS prov,
       SUM(CASE WHEN MDOCUMENTO.tMoneda = '01' THEN MDOCUMENTO.nNeto
                ELSE MDOCUMENTO.nNeto * MDOCUMENTO.nCambio END) AS facturas
FROM MDOCUMENTO
JOIN vTipoDocumento ON vTipoDocumento.Codigo = MDOCUMENTO.tTipoDocumento
WHERE MDOCUMENTO.tEstadoDocumento = '02' AND MDOCUMENTO.lCanje = 0
  AND vTipoDocumento.lInterno = 0
  AND MDOCUMENTO.fEmision >= ? AND MDOCUMENTO.fEmision < ?
GROUP BY MDOCUMENTO.tCodigoProveedor
"""
# Las notas procesadas cuya factura O cuya propia fecha cae en el rango.
_SQL_NOTAS = """
SELECT MNOTACREDITO.tCodigoProveedor AS prov,
       MNOTACREDITO.tNotaCredito AS nota,
       MNOTACREDITO.tDocumento AS factura,
       MNOTACREDITO.fFecha AS fecha_nota,
       MDOCUMENTO.fEmision AS fecha_factura,
       CASE WHEN MNOTACREDITO.tMoneda = '02'
            THEN MNOTACREDITO.nNeto * MDOCUMENTO.nCambio
            ELSE MNOTACREDITO.nNeto END AS neto,
       MNOTACREDITO.tObservacion AS motivo
FROM MNOTACREDITO
JOIN MDOCUMENTO ON MDOCUMENTO.tDocumento = MNOTACREDITO.tDocumento
               AND MDOCUMENTO.tCodigoProveedor = MNOTACREDITO.tCodigoProveedor
               AND MDOCUMENTO.tEstadoDocumento = '02'
               AND MDOCUMENTO.lCanje = 0
WHERE MNOTACREDITO.tEstadoDocumento IN ('02', '03')
  AND ((MDOCUMENTO.fEmision >= ? AND MDOCUMENTO.fEmision < ?)
       OR (MNOTACREDITO.fFecha >= ? AND MNOTACREDITO.fFecha < ?))
"""


def _consulta(cn, sql, params=()):
    cur = cn.cursor()
    cur.execute(sql, list(params))
    cols = [c[0] for c in cur.description]
    return pd.DataFrame.from_records([tuple(f) for f in cur.fetchall()],
                                     columns=cols)


def _conexion():
    from sql_restaurante import _servidor_local, conectar

    servidor = _servidor_local()
    if not servidor:
        sys.exit("Falta %USERPROFILE%\\.sql_restaurante.json con el "
                 "servidor (ver herramientas/sql_restaurante.py).")
    return conectar("ALMACEN", 120, servidor)


def lado_almacen(cn, desde, hasta):
    """(facturas − notas por proveedor, las notas del rango con sus dos
    fechas)."""
    lim = [desde.strftime("%Y%m%d"),
           (hasta + dt.timedelta(days=1)).strftime("%Y%m%d")]
    fac = _consulta(cn, _SQL_FACTURAS, lim)
    notas = _consulta(cn, _SQL_NOTAS, lim * 2)
    for c in ("fecha_nota", "fecha_factura"):
        notas[c] = pd.to_datetime(notas[c]).dt.date
    for c in ("prov", "nota", "factura"):
        notas[c] = notas[c].str.strip()
    fac["prov"] = fac["prov"].str.strip()
    dentro = notas["fecha_factura"].between(desde, hasta)
    por_prov = (fac.set_index("prov")["facturas"].astype(float)
                .sub(notas[dentro].groupby("prov")["neto"].sum().astype(float),
                     fill_value=0.0))
    return por_prov, notas


def lado_app(cn, desde, hasta):
    """(Σ VALOR_COMPRA por proveedor de lo que `data.cargar` le entrega a la
    app, lo mismo sin las notas, de dónde salieron las notas)."""
    import data  # importa streamlit: sus avisos de «bare mode» son ruido

    crudo = data.cargar(dc.ARCHIVO, notas_credito=False)
    if crudo is None or crudo.empty:
        sys.exit("La app no trajo compras.")
    if data._sello_notas_compras():
        netas, origen = data.cargar(dc.ARCHIVO), f"{dc.ARCHIVO_NOTAS} (R2)"
    else:
        notas = _consulta(cn, dc.consulta_sheet())
        netas = dc.aplicar_notas(crudo, notas)
        origen = ("el Almacén, con la consulta del Sheet — "
                  f"{dc.ARCHIVO_NOTAS} todavía no está en R2")

    def por_prov(df):
        f = pd.to_datetime(df["FECHA_EMISION_DOC"]).dt.date
        d = df[f.between(desde, hasta)]
        return (pd.to_numeric(d[dc.VALOR], errors="coerce").fillna(0.0)
                .groupby(d[dc.PROVEEDOR].str.strip()).sum())

    return por_prov(netas), por_prov(crudo), origen


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    hoy = dt.date.today()
    fin_mes = hoy.replace(day=1) - dt.timedelta(days=1)
    ap.add_argument("--desde", type=dt.date.fromisoformat,
                    default=fin_mes.replace(day=1))
    ap.add_argument("--hasta", type=dt.date.fromisoformat, default=fin_mes)
    # El parquet suma LÍNEAS y el Almacén, la CABECERA: céntimos de redondeo
    # por documento, que en un año llegan a S/ 0,30 en un proveedor (medido
    # 2023-2026). Lo que no es redondeo pasa de largo: la boleta de S/ 20 de
    # Abrasa (2023) está en MDOCUMENTO sin líneas y no llega al parquet.
    ap.add_argument("--tolerancia", type=float, default=0.50,
                    help="soles de diferencia que se aceptan por proveedor")
    a = ap.parse_args()

    cn = _conexion()
    try:
        alm, notas = lado_almacen(cn, a.desde, a.hasta)
        app, crudo, origen = lado_app(cn, a.desde, a.hasta)
    finally:
        cn.rollback()
        cn.close()

    provs = sorted(set(alm.index) | set(app.index))
    t = pd.DataFrame({"app": app.reindex(provs, fill_value=0.0),
                      "Almacén": alm.reindex(provs, fill_value=0.0)})
    t["diferencia"] = (t["app"] - t["Almacén"]).round(2)
    malos = t[t["diferencia"].abs() > a.tolerancia]

    print(f"\nCuadre de compras · emisión del {a.desde} al {a.hasta} · "
          f"{len(provs)} proveedores")
    print(f"Notas de crédito leídas de: {origen}\n")
    print(f"  app sin notas      {crudo.sum():>14,.2f}")
    print(f"  notas restadas     {crudo.sum() - app.sum():>14,.2f}")
    print(f"  app con notas      {app.sum():>14,.2f}")
    print(f"  Almacén            {alm.sum():>14,.2f}")

    dentro = notas["fecha_factura"].between(a.desde, a.hasta)
    if dentro.any():
        print("\nNotas restadas (de facturas del rango):")
        print(notas[dentro][["nota", "factura", "fecha_factura", "fecha_nota",
                             "neto", "motivo"]]
              .to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    cruzan = notas[notas["fecha_factura"].map(lambda f: (f.year, f.month))
                   != notas["fecha_nota"].map(lambda f: (f.year, f.month))]
    if not cruzan.empty:
        print("\nNotas en un mes distinto que su factura — el Ranking del POS "
              "y el Registro de Compras las restan en la fecha de la NOTA:")
        print(cruzan[["nota", "factura", "fecha_factura", "fecha_nota", "neto"]]
              .to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    if malos.empty:
        print(f"\n✅ Los {len(provs)} proveedores cuadran (±{a.tolerancia}).")
        return
    print(f"\n❌ {len(malos)} proveedor(es) no cuadran:")
    print(malos.to_string(float_format=lambda v: f"{v:,.2f}"))
    sys.exit(1)


if __name__ == "__main__":
    main()
