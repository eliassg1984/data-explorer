"""
Red de seguridad de graficos.py — dos capas, con datos falsos.

Uso (desde la raíz del proyecto, junto a graficos.py):

    python test_graficos.py

1) SMOKE de constructores: construye cada figura de Ajuste + el motor
   genérico. Detecta que Plotly no rechace nada (kwargs duplicados,
   propiedades inválidas como `opacity` en Waterfall, etc.).
2) FUNCIONES PURAS (`_pruebas_puras`): asserts de VALOR sobre las funciones
   de transformación (sin Streamlit) — _slug, _hover_fmt, _periodo_serie,
   _preparar_datos, _fc_heat_css, etc. Fijan su contrato para que un
   refactor de mover-código no las rompa en silencio.

· Imprime OK/FALLA por cada caso.
· Termina con código 1 si hubo fallos (sirve para CI o para pedirle a una IA:
  "corre este script y arregla lo que falle").

Por qué existe: `python -m py_compile` solo detecta errores de sintaxis.
Los errores de Plotly (ValueError / TypeError) aparecen al CONSTRUIR la
figura — es decir, cuando un usuario abre esa pestaña en producción. Este
script las construye todas AHORA, incluyendo las ramas `else` (sin familia)
que casi nunca se prueban a mano.

Nota: las funciones llaman a st.* fuera de una app de Streamlit; eso puede
emitir warnings "missing ScriptRunContext", que son inofensivos y aquí se
silencian. Solo importan las líneas FALLA.
"""
import logging
import sys

import pandas as pd

# La consola de Windows (cp1252) no puede imprimir emojis (✅/❌); forzar UTF-8
# para que el script corra igual en Windows y en Streamlit Cloud (Linux).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Silenciar el ruido de Streamlit en modo "bare" (fuera de la app)
logging.getLogger("streamlit").setLevel(logging.ERROR)

import graficos  # noqa: E402  (después de configurar logging, a propósito)


def _df_completo():
    """12 filas con todas las columnas que resuelven los gráficos de Ajuste."""
    return pd.DataFrame({
        "FECHA APERTURA INVENTARIO": pd.date_range("2024-01-01", periods=12, freq="MS"),
        "FAMILIA": ["Abarrotes", "Bebidas"] * 6,
        "AREA": ["Almacén", "Tienda"] * 6,
        "AJUSTE VALORIZADO": [10.5, -5.2, 3.1, -8.7, 2.0, -1.4] * 2,
        "VALORIZADO TOTAL": [100.0, 90.0, 110.0, 95.0, 105.0, 98.0] * 2,
        "NOMBRE PRODUCTO": [f"Producto {i}" for i in range(12)],
    })


def _df_minimo():
    """Solo fecha + ajuste: fuerza las ramas `else` (sin familia/área/producto)."""
    return pd.DataFrame({
        "FECHA APERTURA INVENTARIO": pd.date_range("2024-01-01", periods=8, freq="MS"),
        "AJUSTE VALORIZADO": [4.0, -2.5, 1.1, -6.3, 2.2, -0.4, 5.0, -1.0],
    })


def _pruebas_puras():
    """Asserts de VALOR sobre las funciones puras (transforman datos, sin
    Streamlit). Son las que un refactor de mover-código puede romper en
    silencio: aquí se fija su contrato con entradas/salidas concretas."""
    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        # Series/ndarray de pandas: comparar como lista (evita el ValueError
        # de "the truth value of a Series is ambiguous").
        ok = (got.tolist() == exp) if hasattr(got, "tolist") else (got == exp)
        if ok:
            print(f"OK    puro · {nombre}")
        else:
            fallos += 1
            print(f"FALLA puro · {nombre}: got={got!r} exp={exp!r}")

    g = graficos

    # _slug — id seguro para keys/CSS
    check("_slug símbolos", g._slug("Cascada · Precio"), "cascada_precio")
    check("_slug espacios extremos", g._slug("  Hola Mundo  "), "hola_mundo")

    # _compras_truncar — recorte con elipsis
    check("_truncar corto intacto", g._compras_truncar("corto"), "corto")
    check("_truncar largo", g._compras_truncar("x" * 30), "x" * 25 + "…")
    check("_truncar n custom", g._compras_truncar("hola", 3), "ho…")

    # _hover_fmt — (prefijo, formato) según el nombre de la columna Y
    check("_hover valorizado", g._hover_fmt("AJUSTE VALORIZADO"), ("S/ ", ",.2f"))
    check("_hover stock", g._hover_fmt("Stock al Dia"), ("", ",.0f"))
    check("_hover genérico", g._hover_fmt("Descripción"), ("", ",.2f"))
    check("_hover None", g._hover_fmt(None), ("", ",.2f"))

    # _wrap_cat — parte etiquetas largas con <br>
    check("_wrap corto intacto", g._wrap_cat(["corto"], 14), ["corto"])
    check("_wrap largo parte", g._wrap_cat(["Entraña fina importada"], 14),
          ["Entraña fina<br>importada"])

    # _resolver — None / str / lista de candidatos → nombre real o None
    df = _df_completo()
    check("_resolver None", g._resolver(df, None), None)
    check("_resolver match (case-insensitive)", g._resolver(df, ["Familia"]), "FAMILIA")
    check("_resolver no existe", g._resolver(df, "columna_inexistente"), None)

    # _first_point — extrae el primer punto de un evento de selección
    check("_first_point con punto",
          g._first_point({"selection": {"points": [{"x": 1}]}}), {"x": 1})
    check("_first_point sin puntos",
          g._first_point({"selection": {"points": []}}), None)
    check("_first_point None", g._first_point(None), None)

    # _fc_heat_css — color amarillo→rojo por %FoodCost
    check("_fc_heat mínimo (amarillo)", g._fc_heat_css(12),
          "background-color: rgba(254,240,138,0.6); color:#3a2a10")
    check("_fc_heat máximo (rojo)", g._fc_heat_css(42),
          "background-color: rgba(220,38,38,0.6); color:#3a2a10")
    check("_fc_heat NaN → vacío", g._fc_heat_css(float("nan")), "")

    # _periodo_serie — etiquetas ordenables por granularidad
    fe = pd.Series(pd.to_datetime(["2024-01-15", "2024-12-31"]))
    check("_periodo Mes", g._periodo_serie(fe, "Mes"), ["2024-01", "2024-12"])
    check("_periodo Año", g._periodo_serie(fe, "Año"), ["2024", "2024"])

    # _preparar_datos — agrupa+suma por categoría; fecha → columna _mes
    dcat = pd.DataFrame({"FAMILIA": ["A", "A", "B"], "VAL": [1.0, 2.0, 4.0]})
    out, xcol = g._preparar_datos(dcat, "FAMILIA", "VAL", None, "bar")
    check("_preparar_datos x", xcol, "FAMILIA")
    check("_preparar_datos suma grupo A",
          float(out.loc[out["FAMILIA"] == "A", "VAL"].iloc[0]), 3.0)
    dfe = pd.DataFrame({"F": pd.to_datetime(["2024-01-01", "2024-01-15"]),
                        "VAL": [1.0, 2.0]})
    _, xcol2 = g._preparar_datos(dfe, "F", "VAL", None, "bar")
    check("_preparar_datos fecha → _mes", xcol2, "_mes")

    # _layout — oculta etiquetas del eje Y, endereza X, respeta overrides
    lay = g._layout()
    check("_layout oculta labels Y", lay["yaxis"]["showticklabels"], False)
    check("_layout endereza X", lay["xaxis"]["tickangle"], 0)
    lay2 = g._layout(yaxis=dict(showticklabels=True))
    check("_layout respeta override Y", lay2["yaxis"]["showticklabels"], True)

    return fallos


def main():
    df, df_min = _df_completo(), _df_minimo()
    fallos = 0

    pruebas = [
        ("evolucion (por familia)", graficos._graf_evolucion_ajuste,
            (df, "FECHA APERTURA INVENTARIO", "FAMILIA",
             "AJUSTE VALORIZADO", "VALORIZADO TOTAL")),
        ("evolucion (rama else, sin familia)", graficos._graf_evolucion_ajuste,
            (df_min, "FECHA APERTURA INVENTARIO", None, "AJUSTE VALORIZADO", None)),
        ("waterfall (Cascada)", graficos._graf_waterfall_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO")),
        ("heatmap (Mapa de calor)", graficos._graf_heatmap_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO")),
        ("distribucion (box por familia)", graficos._graf_distribucion_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO", "NOMBRE PRODUCTO")),
        ("distribucion (rama else: histograma)", graficos._graf_distribucion_ajuste,
            (df_min, None, None, "AJUSTE VALORIZADO", None)),
    ]

    for nombre, fn, args in pruebas:
        try:
            fn(*args)
            print(f"OK    {nombre}")
        except Exception as e:  # queremos ver CUALQUIER fallo, con su tipo
            fallos += 1
            print(f"FALLA {nombre}: {type(e).__name__}: {e}")

    # ── Motor genérico: crear_grafico devuelve (fig, err), no lanza ─────
    configs = [
        {"tipo": "bar", "x": "FAMILIA", "y": "AJUSTE VALORIZADO",
         "titulo": "smoke bar"},
        {"tipo": "line", "x": "FECHA APERTURA INVENTARIO",
         "y": "AJUSTE VALORIZADO", "titulo": "smoke line"},
        {"tipo": "histogram", "x": "AJUSTE VALORIZADO", "titulo": "smoke hist"},
    ]
    for conf in configs:
        fig, err = graficos.crear_grafico(df, conf)
        if fig is not None:
            print(f"OK    crear_grafico[{conf['tipo']}]")
        else:
            fallos += 1
            print(f"FALLA crear_grafico[{conf['tipo']}]: {err}")

    # ── Funciones puras: asserts de valor (contrato de transformación) ──
    fallos += _pruebas_puras()

    print()
    if fallos:
        print(f"❌ {fallos} fallo(s) — revisar las líneas FALLA de arriba")
        sys.exit(1)
    print("✅ Todo OK (constructores de figuras + funciones puras)")


if __name__ == "__main__":
    main()
