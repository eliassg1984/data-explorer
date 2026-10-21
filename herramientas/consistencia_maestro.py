"""
herramientas/consistencia_maestro.py — los controles del maestro sobre R2.

Corre cada control de `consistencia_maestro.py` sobre los parquets de verdad
e imprime, por control, cuántos casos hay, cuánto está en juego y los que
más pesan. Es la etapa del boceto (2026-10-21): con estos números se decide
qué controles quedan, con qué umbral y con qué color, antes de la vista.

    python herramientas/consistencia_maestro.py
    python herramientas/consistencia_maestro.py --solo s1 s7 --top 15
    python herramientas/consistencia_maestro.py --csv salida/

Se corre desde la raíz del repo (lee `.streamlit/secrets.toml` como la
app). La fecha de corte es el último día del kardex. Con `--csv`, un CSV por
control con TODOS sus casos.
"""

import argparse
import pathlib
import sys
import time

import pandas as pd

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import consistencia_maestro as cm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def _soles(v):
    return "—" if pd.isna(v) else f"S/ {v:,.0f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--solo", nargs="*")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--csv", type=pathlib.Path)
    a = ap.parse_args()

    import data  # importa streamlit: sus avisos de «bare mode» son ruido

    t0 = time.time()
    # La misma carga que la vista (`data.consistencia_entradas`), sin su
    # caché: se verifica el código de hoy, no lo que quedó guardado.
    t, hoy = data.consistencia_entradas()
    print(f"Corte: {hoy:%d %b %Y} · carga {time.time() - t0:.0f} s\n")
    res = cm.calcular(t, hoy, solo=a.solo)
    nombre = {c.id: (c.dominio, c.nombre) for c in cm.CONTROLES}
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 46)
    for cid, r in res.items():
        dom, nom = nombre[cid]
        if isinstance(r, Exception):
            print(f"■ {cid} {nom} — FALLÓ: {type(r).__name__}: {r}\n")
            continue
        s = r["soles"].sum(min_count=1)
        print(f"■ {cid} [{dom}] {nom}: {len(r)} casos · {_soles(s)}")
        if len(r):
            orden = r.assign(_a=r["soles"].abs()).sort_values("_a", ascending=False, na_position="last")
            ver = orden.head(a.top)[["codigo", "nombre", "area", "dato", "soles", "quien"]].copy()
            ver["soles"] = ver["soles"].map(_soles)
            print(ver.to_string(index=False))
            if r["area"].astype(str).str.len().gt(0).any() and len(r) > a.top:
                por = r.groupby("area").size().sort_values(ascending=False).head(6)
                print("  por área: " + ", ".join(f"{k or '—'} {v}" for k, v in por.items()))
        print()
        if a.csv:
            a.csv.mkdir(parents=True, exist_ok=True)
            r.to_csv(a.csv / f"{cid}.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
