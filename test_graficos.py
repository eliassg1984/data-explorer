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

    # Tras el refactor Fase 2, las funciones puras viven en sus módulos reales
    # (graficos/base.py y graficos/{ventas,compras,...}.py). Se prueban desde
    # ahí. `graficos.X` sigue funcionando para lo que se re-exporta.
    b = graficos.base
    from graficos import ventas as _v, compras as _c

    # _slug — id seguro para keys/CSS
    check("_slug símbolos", b._slug("Cascada · Precio"), "cascada_precio")
    check("_slug espacios extremos", b._slug("  Hola Mundo  "), "hola_mundo")

    # _compras_truncar — recorte con elipsis (vive en base.py tras el refactor)
    check("_truncar corto intacto", b._compras_truncar("corto"), "corto")
    check("_truncar largo", b._compras_truncar("x" * 30), "x" * 25 + "…")
    check("_truncar n custom", b._compras_truncar("hola", 3), "ho…")

    # _hover_fmt — (prefijo, formato) según el nombre de la columna Y
    check("_hover valorizado", b._hover_fmt("AJUSTE VALORIZADO"), ("S/ ", ",.2f"))
    check("_hover stock", b._hover_fmt("Stock al Dia"), ("", ",.0f"))
    check("_hover genérico", b._hover_fmt("Descripción"), ("", ",.2f"))
    check("_hover None", b._hover_fmt(None), ("", ",.2f"))

    # _wrap_cat — parte etiquetas largas con <br>
    check("_wrap corto intacto", b._wrap_cat(["corto"], 14), ["corto"])
    check("_wrap largo parte", b._wrap_cat(["Entraña fina importada"], 14),
          ["Entraña fina<br>importada"])

    # _resolver — None / str / lista de candidatos → nombre real o None
    df = _df_completo()
    check("_resolver None", b._resolver(df, None), None)
    check("_resolver match (case-insensitive)", b._resolver(df, ["Familia"]), "FAMILIA")
    check("_resolver no existe", b._resolver(df, "columna_inexistente"), None)

    # _first_point / _periodo_serie viven en graficos.compras tras el refactor
    check("_first_point con punto",
          _c._first_point({"selection": {"points": [{"x": 1}]}}), {"x": 1})
    check("_first_point sin puntos",
          _c._first_point({"selection": {"points": []}}), None)
    check("_first_point None", _c._first_point(None), None)

    # _fc_heat_css vive en graficos.ventas tras el refactor
    check("_fc_heat mínimo (amarillo)", _v._fc_heat_css(12),
          "background-color: rgba(254,240,138,0.6); color:#3a2a10")
    check("_fc_heat máximo (rojo)", _v._fc_heat_css(42),
          "background-color: rgba(220,38,38,0.6); color:#3a2a10")
    check("_fc_heat NaN → vacío", _v._fc_heat_css(float("nan")), "")

    fe = pd.Series(pd.to_datetime(["2024-01-15", "2024-12-31"]))
    check("_periodo Mes", _c._periodo_serie(fe, "Mes"), ["2024-01", "2024-12"])
    check("_periodo Año", _c._periodo_serie(fe, "Año"), ["2024", "2024"])

    # ── Etiquetas de barra del drill de Proveedor ───────────────────────
    # Vivían anidadas dentro de _compras_proveedor_drill (1.577 líneas), así
    # que no había forma de probarlas. Salieron a su módulo el 2026-08-08.
    from graficos.compras import _etiquetas_proveedor as _ep

    check("fmt_k unidades", _ep.fmt_k(940), "S/ 940")
    check("fmt_k miles", _ep.fmt_k(4000), "S/ 4.0k")
    check("fmt_k millones", _ep.fmt_k(1_200_000), "S/ 1.2M")
    # El umbral es >=, no >: 1000 ya es "1.0k" y no "S/ 1000".
    check("fmt_k borde 1000", _ep.fmt_k(1000), "S/ 1.0k")

    check("sufijo gran conocida", _ep.sufijo_granularidad("Mes"), "del Mes")
    check("sufijo gran desconocida",
          _ep.sufijo_granularidad("Quincena"), "del período")

    # abrev_nombre — escalones por ancho disponible
    _prov = "Distribuidora Andina S.A.C."
    check("abrev <2 → vacío", _ep.abrev_nombre(_prov, 1), "")
    check("abrev 2 → iniciales", _ep.abrev_nombre(_prov, 2), "DA")
    # 6-14 → primera palabra. "Distribuidora" son 13 chars: en 14 entra
    # entera, en 10 se trunca con … (9 chars + elipsis).
    check("abrev 14 → 1ª palabra entera",
          _ep.abrev_nombre(_prov, 14), "Distribuidora")
    check("abrev 10 → 1ª palabra truncada",
          _ep.abrev_nombre(_prov, 10), "Distribui…")
    check("abrev cabe entero", _ep.abrev_nombre("Agro", 10), "Agro")
    # Las palabras de ruido (S.A.C., de, del…) no cuentan como iniciales.
    check("abrev ignora razón social",
          _ep.abrev_nombre("Alimentos del Sur S.A.C.", 3), "AS")

    # etiqueta_serie — barra en 0 no lleva etiqueta; la 1ª no tiene variación
    _et = _ep.etiqueta_serie([0, 100, 150], "del Mes")
    check("etiqueta barra en 0", _et[0], "")
    check("etiqueta 1ª sin variación", _et[1], "S/ 100")
    check("etiqueta 2ª con ▲50%", "▲50%" in _et[2], True)
    _baja = _ep.etiqueta_serie([200, 100], "del Mes")
    check("etiqueta baja con ▼", "▼50%" in _baja[1], True)
    # compacta=True descarta docs y % aunque se los pasen
    _comp = _ep.etiqueta_serie([100], "del Mes", compacta=True,
                               pct_periodo=[42], docs=[3])
    check("etiqueta compacta sin pie", _comp[0], "S/ 100")
    _full = _ep.etiqueta_serie([100], "del Mes", pct_periodo=[42], docs=[3])
    check("etiqueta full con docs", "3 docs" in _full[0], True)
    check("etiqueta full con % y sufijo", "42% del Mes" in _full[0], True)
    # singular/plural de documentos
    _uno = _ep.etiqueta_serie([100], "del Mes", docs=[1])
    check("etiqueta 1 doc en singular", "1 doc<" in _uno[0], True)

    # _preparar_datos — agrupa+suma por categoría; fecha → columna _mes
    dcat = pd.DataFrame({"FAMILIA": ["A", "A", "B"], "VAL": [1.0, 2.0, 4.0]})
    out, xcol = b._preparar_datos(dcat, "FAMILIA", "VAL", None, "bar")
    check("_preparar_datos x", xcol, "FAMILIA")
    check("_preparar_datos suma grupo A",
          float(out.loc[out["FAMILIA"] == "A", "VAL"].iloc[0]), 3.0)
    dfe = pd.DataFrame({"F": pd.to_datetime(["2024-01-01", "2024-01-15"]),
                        "VAL": [1.0, 2.0]})
    _, xcol2 = b._preparar_datos(dfe, "F", "VAL", None, "bar")
    check("_preparar_datos fecha → _mes", xcol2, "_mes")

    # _layout — oculta etiquetas del eje Y, endereza X, respeta overrides
    lay = b._layout()
    check("_layout oculta labels Y", lay["yaxis"]["showticklabels"], False)
    check("_layout endereza X", lay["xaxis"]["tickangle"], 0)
    lay2 = b._layout(yaxis=dict(showticklabels=True))
    check("_layout respeta override Y", lay2["yaxis"]["showticklabels"], True)

    return fallos


def _pruebas_contratos():
    """El contrato del DISPATCHER (graficos/__init__.py).

    Existe porque el dispatcher llama a TODOS los dashboards con la misma
    firma: `render(df, reporte, df_full=..., tabla_cb=...)`. Un dashboard
    nuevo que se olvide de `tabla_cb` revienta con TypeError, pero solo en
    producción y solo al abrir ese reporte — nada lo detecta antes.

    Igual de importante: `tabla_cb` se INVOCA con exactamente 1 argumento
    posicional (el df a tabular). Hasta el 2026-08-08 unos dashboards
    llamaban `tabla_cb()` y otros `tabla_cb(d)`, y el único sitio donde
    constaba era un docstring.
    """
    import inspect
    from graficos import _DASHBOARDS

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    contrato · {nombre}")
        else:
            fallos += 1
            print(f"FALLA contrato · {nombre}{': ' + detalle if detalle else ''}")

    for reporte, fn in sorted(_DASHBOARDS.items()):
        params = inspect.signature(fn).parameters
        check(f"{reporte} acepta tabla_cb", "tabla_cb" in params,
              f"firma actual: ({', '.join(params)})")
        check(f"{reporte} acepta df_full", "df_full" in params,
              f"firma actual: ({', '.join(params)})")

    # El dispatcher realmente le pasa tabla_cb a todo el mundo (si alguien
    # vuelve a meter un `if reporte in (...)`, este assert lo caza).
    import graficos
    src = inspect.getsource(graficos.renderizar_graficos_reporte)
    check("dispatcher sin lista de reportes hardcodeada",
          src.count("tabla_cb=tabla_cb") == 1 and "reporte in (" not in src)

    # tabla_cb se invoca con 1 argumento en TODOS los dashboards.
    import re
    import pathlib
    for reporte, fn in sorted(_DASHBOARDS.items()):
        ruta = pathlib.Path(inspect.getsourcefile(fn))
        llamadas = re.findall(r"\btabla_cb\((.*?)\)",
                              ruta.read_text(encoding="utf-8"))
        # Se ignoran las menciones en docstrings/comentarios: solo importan
        # las que tengan forma de llamada real (sin "=" de kwarg).
        reales = [a for a in llamadas if "=" not in a]
        if not reales:
            continue  # dashboard que no usa el callback (Compras)
        check(f"{reporte} invoca tabla_cb con 1 arg",
              all(a.strip() and "," not in a for a in reales),
              f"llamadas: {reales}")

    return fallos


def main():
    df, df_min = _df_completo(), _df_minimo()
    fallos = 0

    # Tras el refactor Fase 2, los helpers privados de Ajuste viven en
    # graficos.ajuste (se prueban desde su módulo real). renderizar_graficos_
    # ajuste sigue accesible como graficos.X porque __init__ lo re-exporta.
    from graficos import ajuste as _aj

    pruebas = [
        ("evolucion (por familia)", _aj._graf_evolucion_ajuste,
            (df, "FECHA APERTURA INVENTARIO", "FAMILIA",
             "AJUSTE VALORIZADO", "VALORIZADO TOTAL")),
        ("evolucion (rama else, sin familia)", _aj._graf_evolucion_ajuste,
            (df_min, "FECHA APERTURA INVENTARIO", None, "AJUSTE VALORIZADO", None)),
        ("waterfall (Cascada)", _aj._graf_waterfall_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO")),
        ("heatmap (Mapa de calor)", _aj._graf_heatmap_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO")),
        ("distribucion (box por familia)", _aj._graf_distribucion_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO", "NOMBRE PRODUCTO")),
        ("distribucion (rama else: histograma)", _aj._graf_distribucion_ajuste,
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

    # ── Contratos entre app.py y los dashboards (firma del dispatcher) ──
    fallos += _pruebas_contratos()

    print()
    if fallos:
        print(f"❌ {fallos} fallo(s) — revisar las líneas FALLA de arriba")
        sys.exit(1)
    print("✅ Todo OK (constructores de figuras + funciones puras)")


if __name__ == "__main__":
    main()
