"""
herramientas/foto_recetas.py — la foto de las recetas de venta desde una
consola, y lo que cambió entre dos fotos (regla #705).

La app ya saca la foto sola (`historial_recetas.revisar_en_segundo_plano`,
desde `app.py`) cada vez que alguien la abre. Esto sirve para tres cosas:
sacarla sin abrir la app, ver qué fotos hay, y leer los cambios.

    python herramientas/foto_recetas.py              # saca la foto si falta
    python herramientas/foto_recetas.py --listar     # las fotos que hay
    python herramientas/foto_recetas.py --cambios    # última foto contra la anterior
    python herramientas/foto_recetas.py --cambios --desde 2026-10-01 --csv cambios.csv

`--cambios` compara la foto más nueva con la más nueva ANTERIOR a
`--desde` (por defecto, la penúltima). Lee las credenciales de R2 de
`.streamlit/secrets.toml`, como la app; si no está, de las variables de
entorno `R2_ACCOUNT_ID`, `R2_ACCESS_KEY`, `R2_SECRET_KEY` y `R2_BUCKET` —
así puede correr como tarea programada en otra máquina sin el repo
entero de la app.
"""
from __future__ import annotations

import argparse
import os
import sys
import tomllib
from pathlib import Path

import boto3
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import historial_recetas as hr  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_CLAVES = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_BUCKET")


def _secrets():
    ruta = RAIZ / ".streamlit" / "secrets.toml"
    if ruta.exists():
        with open(ruta, "rb") as f:
            s = tomllib.load(f)
    else:
        s = {k: os.environ.get(k) for k in _CLAVES}
    faltan = [k for k in _CLAVES if not s.get(k)]
    if faltan:
        sys.exit(f"Faltan credenciales de R2: {', '.join(faltan)}")
    return s


def _cliente(s):
    return boto3.client(
        "s3",
        endpoint_url=f"https://{s['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=s["R2_ACCESS_KEY"],
        aws_secret_access_key=s["R2_SECRET_KEY"],
        region_name="auto",
    )


def _lima(t):
    return t.tz_convert("America/Lima").strftime("%d/%m/%Y %H:%M")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("--listar", action="store_true", help="las fotos que hay")
    ap.add_argument("--cambios", action="store_true",
                    help="lo que cambió entre dos fotos")
    ap.add_argument("--desde", help="fecha (AAAA-MM-DD): compara contra la "
                    "última foto anterior a ese día")
    ap.add_argument("--csv", help="guarda los cambios en este archivo")
    args = ap.parse_args()

    s = _secrets()
    s3, bucket = _cliente(s), s["R2_BUCKET"]

    if not (args.listar or args.cambios):
        nuevas = hr.asegurar_fotos(s3, bucket)
        for clave in nuevas:
            print(f"Foto nueva: {clave} ({_lima(hr.fecha_de_clave(clave))})")
        if not nuevas:
            print("La versión vigente ya tiene su foto.")
        return

    lista = hr.fotos(s3, bucket)
    if args.listar:
        for t, clave in lista:
            print(f"{_lima(t)}  {clave}")
        print(f"{len(lista)} foto(s)")
        return

    if len(lista) < 2:
        sys.exit(f"Hay {len(lista)} foto(s): para comparar hacen falta dos.")
    t_d, clave_d = lista[-1]
    if args.desde:
        tope = pd.Timestamp(args.desde, tz="America/Lima")
        previas = [x for x in lista if x[0] < tope]
        if not previas:
            sys.exit(f"No hay fotos anteriores al {args.desde}.")
        t_a, clave_a = previas[-1]
    else:
        t_a, clave_a = lista[-2]

    cb = hr.cambios(hr.leer_foto(s3, bucket, clave_a),
                    hr.leer_foto(s3, bucket, clave_d))
    print(f"De la foto del {_lima(t_a)} a la del {_lima(t_d)}: "
          f"{len(cb)} cambio(s)")
    if len(cb):
        with pd.option_context("display.max_rows", 500, "display.width", 220,
                               "display.max_colwidth", 40):
            print(cb.drop(columns=["NOMB RV"]).to_string(index=False))
    if args.csv:
        cb.to_csv(args.csv, index=False, encoding="utf-8-sig")
        print(f"→ {args.csv}")


if __name__ == "__main__":
    main()
