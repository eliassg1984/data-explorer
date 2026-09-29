"""
herramientas/verificar_consumo.py — el consumo según recetas contra los datos
de verdad (regla #558).

`test_consumo_recetas.py` prueba las CUENTAS con datos de mentira. Esto las
corre sobre los parquets de R2, con la misma carga que la app
(`data.consumo_recetas_rango`), y revisa lo que un test no puede ver:

    python herramientas/verificar_consumo.py
    python herramientas/verificar_consumo.py --desde 2026-08-28 --hasta 2026-09-27

Sin fechas, los últimos 30 días hasta ayer. Se corre desde la raíz del repo
(lee `.streamlit/secrets.toml` como la app). Sale con código 1 si una rama
que baja SÓLO por recetas base no cuadra.

QUÉ REVISA

  1. EL CUADRE, rama por rama. Cada insumo del primer nivel (lo que nombra
     la receta de venta) contra lo que cuestan sus hojas a precio de hoy:
       · por RECETAS BASE tiene que cerrar: el Almacén recuesta cada
         producto con sus insumos (el documento de prueba del 2026-09-28
         cerró S/ 16,80665 contra S/ 16,80665). Si no cierra, hay una unidad
         o un factor mal — es lo que esta herramienta existe para cazar;
       · por un PORCIONAMIENTO no tiene por qué: las hojas llevan el
         rendimiento REAL y el corte, el costo que le puso el Almacén. Se
         listan los que más se separan, para mirarlos.
  2. LOS RENDIMIENTOS IMPOSIBLES: un corte en kilos que sale de un insumo en
     kilos con menos de 0,95 kg por kg «sale más de lo que entra» (los
     retazos de pulpo cargados ×10, medido el 2026-09-28).
  3. LO QUE TIENE RECETA Y SE PORCIONA: el cálculo baja por el
     porcionamiento (el real manda). Se listan los que parten de insumos
     DISTINTOS en una y otro, que es donde esa decisión cambia el resultado.
"""

import argparse
import datetime as dt
import pathlib
import sys

import pandas as pd

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import consumo_recetas as cr  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TOL_RECETAS = 0.01
"""Cuánto puede separarse, en proporción, una rama sólo de recetas base
antes de contar como que no cuadra. El redondeo de las recetas del Almacén
no llega a esto."""


def _soles(v):
    return f"S/ {v:,.0f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ayer = dt.date.today() - dt.timedelta(days=1)
    ap.add_argument("--desde", type=dt.date.fromisoformat, default=ayer - dt.timedelta(days=29))
    ap.add_argument("--hasta", type=dt.date.fromisoformat, default=ayer)
    ap.add_argument("--top", type=int, default=12)
    a = ap.parse_args()

    import data  # importa streamlit: sus avisos de «bare mode» son ruido

    # Se verifica el CÓDIGO de hoy, no lo que quedó guardado: la caché de
    # disco no caduca, y su clave no cambia mientras no suba la VERSION.
    data._consumo_recetas_cacheable.clear()
    r = data.consumo_recetas_rango(a.desde, a.hasta)
    if r is None:
        sys.exit("La app no pudo calcular el consumo (¿secrets de R2?).")
    res, cu, mae = r["resumen"], r["cuadre"].copy(), r["maestro"]
    nombre = dict(zip(mae["cod"], mae["nombre"]))
    unid = dict(zip(mae["cod"], mae["unid"]))
    fallas = 0

    print(f"\nConsumo según recetas · {a.desde:%d/%m/%Y} al {a.hasta:%d/%m/%Y} · "
          f"grano {res['grano']} · hasta {res['niveles']} niveles")
    print(f"  primer nivel     {_soles(res['costo_nivel1'])}   (venta interna {_soles(res['costo_nivel1_interna'])})")
    print(f"  insumos de compra {_soles(res['costo'])}   (venta interna {_soles(res['costo_interna'])}) · "
          f"{res['insumos']} insumos")
    if res.get("hora_de_mesa"):
        print("  AVISO: el parquet no trae FECHA ITEM: la hora es la de la mesa.")
    if res["sin_maestro"] or res["sin_factor"]:
        print(f"  AVISO: {res['sin_maestro']} filas sin el insumo en el maestro y {res['sin_factor']} sin factor "
              f"({_soles(res['costo_sin_convertir'])} del primer nivel que no se pudo bajar).")

    # ── 1. El cuadre, rama por rama ───────────────────────────────────────
    cu["dif"] = cu["costo_hojas"] - cu["costo_n1"]
    cu["nombre"] = cu["cod"].map(nombre).fillna(cu["cod"])
    for porc, titulo in ((False, "SÓLO RECETAS BASE (tiene que cerrar)"),
                         (True, "CON PORCIONAMIENTO (el rendimiento es el real)")):
        x = cu[cu["con_porcionamiento"] == porc]
        n1, hojas = float(x["costo_n1"].sum()), float(x["costo_hojas"].sum())
        prop = (hojas / n1 - 1) if n1 else 0.0
        print(f"\n── {titulo} ──")
        print(f"  {len(x)} insumos de primer nivel · {_soles(n1)} → {_soles(hojas)} ({prop:+.1%})")
        malos = x[(x["dif"].abs() > 5) & ((x["dif"] / x["costo_n1"].where(x["costo_n1"] != 0)).abs() > TOL_RECETAS)]
        for f in malos.reindex(malos["dif"].abs().sort_values(ascending=False).index).head(a.top).itertuples():
            vi = " [venta interna]" if f.interna else ""
            print(f"    {f.nombre[:46]:<46} {_soles(f.costo_n1):>11} → {_soles(f.costo_hojas):>11}  "
                  f"({f.dif / f.costo_n1:+.1%}){vi}" if f.costo_n1 else f"    {f.nombre}")
        if not porc and abs(prop) > TOL_RECETAS:
            fallas += 1
            print(f"  FALLA: las ramas sólo de recetas se separan {prop:+.1%} (tolerancia {TOL_RECETAS:.0%}).")

    # ── 2. Rendimientos imposibles ────────────────────────────────────────
    rd = r["rend"].copy()
    if not rd.empty:
        ultimo = rd["mes"].max()
        # Sólo los que el árbol USA: el respaldo de un producto con receta
        # queda en la tabla pero no se baja por él.
        rd = rd[(rd["mes"] == ultimo) & rd["usado"]]
        rd["u_x"] = rd["cod_x"].map(unid)
        rd["u_e"] = rd["cod_e"].map(unid)
        # Por CORTE, sumando sus orígenes: el lomo limpio para carpaccio sale
        # del lomo entero (0,84 kg por kg) y de la cabeza (0,28), y juntos
        # dan 1,12 — está bien. Sólo cuando todos los orígenes van en la
        # misma unidad que el corte.
        misma = rd.groupby("cod_x").apply(
            lambda g: bool((g["u_e"] == g["u_x"]).all()), include_groups=False)
        tot = rd.groupby("cod_x").agg(rend=("rend", "sum"), u=("u_x", "first"),
                                      fuente=("fuente", "first"), n=("n_porc", "first"))
        raros = tot[misma.reindex(tot.index).fillna(False).astype(bool)
                    & tot["u"].isin(["KILOS", "LITROS"]) & (tot["rend"] < 0.95)]
        print(f"\n── RENDIMIENTOS IMPOSIBLES ({pd.Timestamp(ultimo):%m/%Y}: el corte pesa más que lo que "
              "se le asignó del insumo) ──")
        print("   Casi todos son subproductos —grasa, retazos, carcasa, esqueleto— a los que la cocina")
        print("   les anota poco peso para cargarles poco costo: es costeo, no un error de datos.")
        if raros.empty:
            print("  ninguno")
        for cod_x, f in raros.sort_values("rend").iterrows():
            print(f"    {nombre.get(cod_x, cod_x)[:52]:<52} {f['rend']:.3f} {f['u'].lower()} por "
                  f"{f['u'].lower()} ({f['fuente']}, {f['n']} cortes)")

    # ── 3. Lo que tiene receta y se porciona ──────────────────────────────
    rb = data.cargar(cr.ARCHIVOS["recetabase"])
    po = data.cargar(cr.ARCHIVOS["porcionamientos"])
    if rb is not None and po is not None:
        activas = rb[rb["RB ACT"] == cr.RECETA_ACTIVA]
        receta = activas.groupby("COD PROD RB")["COD INS RB"].apply(lambda s: set(s.dropna()))
        origen = po.groupby("COD PROD FINAL")["COD PROD INIC"].apply(lambda s: set(s.dropna()))
        ambos = sorted(set(receta.index) & set(origen.index))
        distintos = [c for c in ambos if receta[c] != origen[c]]
        usados = set(cu["cod"]) | set(r["filas"]["padre"]) | set(r["filas"]["n1"])
        rv = r["rend"]
        en_ventana = set(rv.loc[(rv["mes"] == rv["mes"].max()) & (rv["fuente"] == "ventana"), "cod_x"]) \
            if not rv.empty else set()
        print(f"\n── CON RECETA Y CON PORCIONAMIENTOS: {len(ambos)} productos, {len(distintos)} parten de "
              "insumos distintos ──")
        print("   (baja por el porcionamiento si hubo en los 90 días; si no, por la receta)")
        for c in distintos:
            por = "porcionamiento" if c in en_ventana else "receta"
            marca = "  ← se vendió en el período" if c in usados else ""
            print(f"    {nombre.get(c, c)[:50]}  [usa: {por}]{marca}")
            print(f"        receta:          {', '.join(sorted(nombre.get(i, i)[:28] for i in receta[c]))[:110]}")
            print(f"        porcionamientos: {', '.join(sorted(nombre.get(i, i)[:28] for i in origen[c]))[:110]}")

    print()
    if fallas:
        print(f"❌ {fallas} rama(s) que tienen que cerrar no cierran.")
        sys.exit(1)
    print("✅ Las ramas sólo de recetas base cierran.")


if __name__ == "__main__":
    main()
