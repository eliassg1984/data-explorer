"""
herramientas/sunat_registro_sync.py — el REGISTRO del SIRE Compras a un
parquet en R2, para que la webapp lo lea como a cualquier otro reporte.

QUÉ HACE Y POR QUÉ EXISTE
--------------------------
Hermano de `sunat_originales_sync.py`, pero de la mitad barata: acá NO hay
navegador. Pide a la API del SIRE los comprobantes de TODOS los períodos
habilitados, los junta en una tabla y sube `sunat_compras.parquet` a R2,
al lado de `compras.parquet` y los demás.

Hasta ahora el drill «Documentos SUNAT» llamaba a la API EN VIVO, en cada
visita. Eso tiene dos costos que este script elimina:

  · **Lento, y peor cuanto más ancho el rango.** La API sólo habla por
    período mensual: un rango que arranque hace 20 meses son 20 llamadas
    encadenadas (~9 seg cada una, medido) — más de 3 minutos con el
    usuario esperando. Leer un parquet de ~1,2 MB es instantáneo.
  · **La app se cae si SUNAT se cae.** Verificado en vivo el 2026-08-20:
    SUNAT devolvió "Error del Servidor — reintentar en 5 minutos". Con
    consulta en vivo eso es un error en pantalla; con parquet, el usuario
    ve el dato de la corrida anterior y no se entera.

DÓNDE CORRE
-----------
En la CPU local que ya corre de madrugada el extractor de SQL Server —
esa máquina no se apaga y ya tiene las credenciales de R2. Encadenarlo
DESPUÉS de ese extractor, para no competir por red.

    python herramientas/sunat_registro_sync.py

Toma ~6 minutos (38 períodos × ~9 seg). No necesita Playwright ni
navegador: sólo `requests`, que ya es dependencia del proyecto.

POR QUÉ REESCRIBE EL ARCHIVO ENTERO, EN VEZ DE APPENDEAR
---------------------------------------------------------
De los 38 períodos, casi todos ya no van a cambiar — 17 están Presentados
(cerrados) y 20 son historia vieja nunca presentada. Sólo el período en
curso se mueve de verdad, así que en teoría alcanzaría con refrescar ese.

Se traen los 38 igual, a propósito. Son 6 minutos en una máquina que ya
está despierta a las 3 AM, y traer todo cierra una clase entera de bugs
silenciosos: que un mes viejo cambie por una rectificatoria y el parquet
quede con el dato viejo, sin que nada avise. Es el mismo criterio de
"reescribir el archivo entero" que ya usa el extractor de SQL Server.
"""
from __future__ import annotations

import argparse
import io
import pathlib
import sys
import time

# Importar el proyecto desde la raíz aunque el script se invoque por ruta
# — mismo patrón que herramientas/ver_figura.py.
_RAIZ = pathlib.Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

if hasattr(sys.stdout, "reconfigure"):      # consola cp1252 de Windows
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd            # noqa: E402
import streamlit as st         # noqa: E402  — st.secrets vive sin server

import data                    # noqa: E402
import sunat                   # noqa: E402


def _log(msg):
    print(msg, flush=True)


def construir_registro(progreso=None):
    """Todos los períodos habilitados → (DataFrame canónico, períodos fallidos).

    Misma forma que devuelve `sunat.obtener_comprobantes_rango`, para que
    la webapp no note la diferencia entre leer esto del parquet o
    pedírselo a la API: las columnas canónicas más `periodo_registro`
    (en qué mes tributario lo tiene SUNAT) y `situacion`
    (Registrado / Pendiente).

    La deduplicación por `car` no es opcional: el período ABIERTO en curso
    devuelve una ventana de 12 meses de comprobantes pendientes de anotar
    (ver `arquitectura.md` regla #141), así que se solapa con los períodos
    cerrados que abarca. Gana "Registrado" por ser el estado más
    definitivo — mismo criterio que `obtener_comprobantes_rango`.
    """
    estados = {p: cod for p, cod, _ in sunat.periodos_con_estado()}
    periodos = sorted(estados, reverse=True)
    _log(f"{len(periodos)} periodos habilitados: {periodos[-1]} … {periodos[0]}")

    partes, fallidos = [], []
    for i, per in enumerate(periodos, 1):
        try:
            d = sunat.obtener_comprobantes(per)
        except Exception as e:
            # Un período que falla no puede tumbar la corrida entera: se
            # anota y se sigue. Mejor un parquet con 37 de 38 meses que
            # ninguno — pero el fallo se reporta al final, no se traga.
            fallidos.append((per, str(e)[:120]))
            _log(f"  [{i}/{len(periodos)}] {per}: fallo — {str(e)[:80]}")
            continue
        if d.empty:
            _log(f"  [{i}/{len(periodos)}] {per}: sin comprobantes")
            continue
        d = d.copy()
        d["periodo_registro"] = per
        d["situacion"] = "Registrado" if estados.get(per) == "01" else "Pendiente"
        partes.append(d)
        _log(f"  [{i}/{len(periodos)}] {per}: {len(d)} comprobantes")
        if progreso:
            progreso(i / len(periodos))

    if not partes:
        return sunat.registros_a_df([]), fallidos

    df = pd.concat(partes, ignore_index=True)
    crudo = len(df)
    df = (df.sort_values("situacion")           # "Pendiente" < "Registrado"
            .drop_duplicates(subset="car", keep="last"))
    if crudo != len(df):
        _log(f"Deduplicado por CAR: {crudo} -> {len(df)} "
             f"({crudo - len(df)} repetidos entre periodos).")
    return df.sort_values("fecha_emision").reset_index(drop=True), fallidos


def main():
    ap = argparse.ArgumentParser(
        description="Sube el registro del SIRE Compras a R2 como parquet.")
    ap.add_argument("--salida", default=sunat.ARCHIVO_REGISTRO,
                    help=f"Clave en R2 (default: {sunat.ARCHIVO_REGISTRO})")
    ap.add_argument("--local", metavar="RUTA",
                    help="Ademas, guardar una copia en este archivo local")
    ap.add_argument("--dry-run", action="store_true",
                    help="Construir y reportar, pero NO subir a R2")
    args = ap.parse_args()

    if not sunat.secrets_disponibles():
        _log("Faltan credenciales de SUNAT en .streamlit/secrets.toml.")
        sys.exit(1)
    if not data.secrets_disponibles():
        _log("Faltan credenciales de R2 en .streamlit/secrets.toml.")
        sys.exit(1)

    t0 = time.time()
    df, fallidos = construir_registro()
    if df.empty:
        _log("No se obtuvo ningun comprobante. No se sube nada "
             "(mejor dejar el parquet anterior que pisarlo con vacio).")
        sys.exit(1)

    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    contenido = buf.getvalue()

    pend = int((df["situacion"] == "Pendiente").sum())
    _log("")
    _log(f"{len(df):,} comprobantes · {pend:,} pendientes · "
         f"{df['ruc_proveedor'].nunique():,} proveedores")
    _log(f"Emision de {df['fecha_emision'].min():%Y-%m-%d} "
         f"a {df['fecha_emision'].max():%Y-%m-%d}")
    _log(f"Parquet: {len(contenido) / 1024:.0f} KB")

    if args.local:
        pathlib.Path(args.local).write_bytes(contenido)
        _log(f"Copia local: {args.local}")

    if args.dry_run:
        _log("--dry-run: no se sube a R2.")
    else:
        data.get_s3_cliente().put_object(
            Bucket=st.secrets["R2_BUCKET"], Key=args.salida,
            Body=contenido, ContentType="application/vnd.apache.parquet")
        _log(f"Subido a R2: {args.salida}")

    _log(f"Total: {time.time() - t0:.0f} seg.")

    if fallidos:
        # Se informa al final y con exit != 0 para que el Task Scheduler
        # pueda distinguir "salio todo bien" de "salio, pero incompleto".
        _log("")
        _log(f"{len(fallidos)} periodo(s) fallaron y NO estan en el parquet:")
        for per, err in fallidos:
            _log(f"   · {per}: {err}")
        sys.exit(2)


if __name__ == "__main__":
    main()
