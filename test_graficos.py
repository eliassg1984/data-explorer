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


def _df_recetas():
    """12 filas emulando un BOM (contenedor -> ítems), forma común a
    Receta Base y Receta Venta — suficiente para ejercitar los 5
    constructores compartidos de graficos/recetas_comun.py."""
    return pd.DataFrame({
        "CONTENEDOR": ["A", "A", "A", "B", "B", "C", "C", "C", "C", "D", "D", "D"],
        "ITEM":       ["x1", "x2", "x3", "x1", "x4", "x2", "x3", "x4", "x5", "x1", "x2", "x3"],
        "VALOR":      [10.0, 5.0, 2.5, 8.0, 3.0, 4.0, 6.0, 1.0, 2.0, 9.0, 3.5, 1.5],
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
    from graficos import recetas_comun as _rc

    # _activo — normaliza los TRES formatos reales de flag activo/inactivo
    # (recetaventa: "ACTIV"/"INACTIV"/""; recetabase.RB ACT: "RB.ACTIV"/
    # "RB.INACT"; recetabase.INS ACTIVO: "INS.ACT"/"INS.INAC" — misma
    # columna que en recetaventa, formato distinto). Confirmado contra R2
    # real 2026-08-13, ver docstring de _activo() en recetas_comun.py.
    _serie_activo = pd.Series([
        "ACTIV", "INACTIV", "", "RB.ACTIV", "RB.INACT",
        "INS.ACT", "INS.INAC", None,
    ])
    check("_activo reconoce los 3 formatos reales",
          _rc._activo(_serie_activo).tolist(),
          [True, False, False, True, False, True, False, False])

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
    # Negativo (2026-08-22, KPIs del rail: Ajuste Valorizado puede dar merma).
    # La magnitud decide el corte, no v directo — sin abs(), ningún negativo
    # entraba nunca en >= 1000 y "S/ -56320" salía sin abreviar ni agrupar.
    check("fmt_k negativo miles", _ep.fmt_k(-56320), "S/ -56.3k")
    check("fmt_k negativo unidades", _ep.fmt_k(-940), "S/ -940")

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

    # ── Volatilidad de insumos (drill de Compras) ───────────────────────
    from graficos.compras import volatilidad as _vol

    check("_vol_ohlc normal", _vol._vol_ohlc_semana([10, 15, 8, 12]),
          {"o": 10.0, "c": 12.0, "h": 15.0, "l": 8.0})
    check("_vol_ohlc filtra 0 y NaN",
          _vol._vol_ohlc_semana([0, 10, float("nan"), 12]),
          {"o": 10.0, "c": 12.0, "h": 12.0, "l": 10.0})
    check("_vol_ohlc vacía → None", _vol._vol_ohlc_semana([]), None)
    check("_vol_ohlc todo inválido → None", _vol._vol_ohlc_semana([0, float("nan")]), None)

    check("_vol_score dos saltos", _vol._vol_score([100, 110, 99]), 20.0)
    check("_vol_score ignora huecos iniciales",
          _vol._vol_score([None, 100, 110]), 10.0)
    check("_vol_score una sola semana", _vol._vol_score([100]), 0.0)
    check("_vol_score vacía", _vol._vol_score([]), 0.0)

    _fe5 = pd.Series(pd.to_datetime(
        ["2026-06-15", "2026-06-22", "2026-06-29", "2026-07-06", "2026-07-13"]))
    _sem5 = _vol._vol_semanas_ventana(_fe5, minimo=4)
    check("_vol_semanas cuenta semanas distintas", len(_sem5), 5)
    check("_vol_semanas arranca en lunes", _sem5[0], pd.Timestamp("2026-06-15"))
    _fe2 = pd.Series(pd.to_datetime(["2026-06-15", "2026-06-16"]))  # misma semana
    check("_vol_semanas insuficientes → None",
          _vol._vol_semanas_ventana(_fe2, minimo=4), None)

    check("_vol_fmt_rango mismo mes",
          _vol._vol_fmt_rango_semana(pd.Timestamp("2026-06-15")), "15-21 Jun")
    check("_vol_fmt_rango cruza de mes",
          _vol._vol_fmt_rango_semana(pd.Timestamp("2026-06-29")), "29 Jun - 5 Jul")

    # ── Vs año pasado (drill de Compras) ────────────────────────────────
    # Lo que fijan estos asserts NO es aritmética de fechas: es que el año
    # pasado se calcule del propio histórico y no de las columnas
    # `*_ANO_ANTERIOR` del parquet. Ésas vienen REPETIDAS en cada fila del
    # producto-mes (verificado contra R2: constantes en los 4.269 grupos),
    # así que sumarlas multiplicaba el año pasado por x4.9. El bug no se ve:
    # el gráfico sale lindo, sólo que con el año pasado inflado.
    from graficos.compras import vs_ano_pasado as _vap

    _dv = pd.DataFrame({
        "prod":  ["A", "A", "A", "B", "A", "A", "B"],
        "fam":   ["F1"] * 7,
        "fecha": pd.to_datetime(["2025-03-05", "2025-03-20", "2025-08-10",
                                 "2025-08-11", "2026-03-02", "2026-03-09",
                                 "2026-08-25"]),
        "valor": [100.0, 200.0, 50.0, 80.0, 600.0, 0.0, 90.0],
        "cant":  [10.0, 20.0, 5.0, 8.0, 20.0, 0.0, 9.0],
        # VENENO: si la vista vuelve a leer estas columnas, los asserts de
        # abajo se caen con números absurdos en vez de pasar en silencio.
        "VALOR_ANO_ANTERIOR": [999999.0] * 7,
        "CANTIDAD_ANO_ANTERIOR": [999999.0] * 7,
    })
    _g1 = _vap._mensual(_dv, "prod", "fecha", "valor", "cant", col_grupo="fam")
    check("_mensual agrupa por producto+mes", len(_g1), 5)
    check("_mensual suma dentro del mes",
          float(_g1[(_g1["prod"] == "A")
                    & (_g1["mes"] == pd.Period("2025-03", "M"))]["valor"].iat[0]),
          300.0)

    # `recorte` corta UN mes y sólo ése (el espejo del mes parcial).
    _g2 = _vap._mensual(_dv, "prod", "fecha", "valor", "cant",
                        recorte=(pd.Period("2025-03", "M"), 10))
    check("_mensual recorta el mes espejo al día pedido",
          float(_g2[(_g2["prod"] == "A")
                    & (_g2["mes"] == pd.Period("2025-03", "M"))]["valor"].iat[0]),
          100.0)
    check("_mensual no toca los otros meses",
          float(_g2[(_g2["prod"] == "A")
                    & (_g2["mes"] == pd.Period("2025-08", "M"))]["valor"].iat[0]),
          50.0)

    _gv = _vap._con_ano_pasado(_g1)
    # PISO: 2025 no tiene contra qué compararse (el histórico arranca ahí).
    check("_con_ano_pasado descarta los meses sin año pasado",
          sorted({str(m) for m in _gv["mes"]}), ["2026-03", "2026-08"])
    # El año pasado sale del propio histórico, NO de la columna envenenada.
    check("el año pasado sale del histórico, no de *_ANO_ANTERIOR",
          float(_gv[(_gv["prod"] == "A")
                    & (_gv["mes"] == pd.Period("2026-03", "M"))]["valor_aa"].iat[0]),
          300.0)
    # BAJA: B se compraba en ago-25 y en ago-26 (el mes que existe) también,
    # pero A NO se compró en ago-26 — tiene que aparecer igual, con valor 0.
    _baja = _gv[(_gv["prod"] == "A") & (_gv["mes"] == pd.Period("2026-08", "M"))]
    check("una baja aparece aunque no tenga fila este año", len(_baja), 1)
    check("la baja trae el gasto del año pasado", float(_baja["valor_aa"].iat[0]), 50.0)
    check("la baja hereda su grupo del producto", str(_baja["grupo"].iat[0]), "F1")
    # TECHO: el desplazamiento de +12 no puede inventar meses que no pasaron.
    check("_con_ano_pasado no inventa meses futuros",
          max(str(m) for m in _gv["mes"]), "2026-08")

    # El puente SIEMPRE cierra: los dos efectos suman la diferencia exacta.
    _ep, _ec = _vap._puente(600.0, 20.0, 300.0, 30.0)
    check("_puente cierra contra el Δ", round(_ep + _ec, 9), 300.0)
    check("_puente aísla el efecto precio", round(_ep, 2), 400.0)
    check("_puente aísla el efecto cantidad", round(_ec, 2), -100.0)
    check("sin cantidad del año pasado, el efecto es todo cantidad",
          _vap._puente(500.0, 5.0, 0.0, 0.0), (0.0, 500.0))
    check("una baja también es efecto cantidad",
          _vap._puente(0.0, 0.0, 250.0, 10.0), (0.0, -250.0))

    # El puente de un GRUPO se suma desde los productos, nunca se calcula
    # sobre el agregado: `Σvalor / Σcantidad` mezcla kilos con litros y con
    # servicios. Medido con el parquet real: la familia GASTOS VENTAS daba
    # ±540k para explicar un Δ de −36k.
    _gg = pd.DataFrame({
        "prod":     ["Kilos", "Litros"],
        "grupo":    ["F1", "F1"],
        "mes":      [pd.Period("2026-03", "M")] * 2,
        # Mismo gasto los dos años, pero uno subió de precio y compró menos
        # y el otro al revés — sobre el agregado los efectos se disparan.
        "valor":    [1000.0, 1000.0],
        "cant":     [50.0, 500.0],
        "valor_aa": [1000.0, 1000.0],
        "cant_aa":  [100.0, 250.0],
    })
    _porfam = _vap._por_item(_gg, "grupo")
    check("el puente de un grupo cierra contra su Δ",
          round(float(_porfam["ef_precio"].iat[0] + _porfam["ef_cant"].iat[0]), 6),
          0.0)
    # Producto a producto: "Kilos" pasó de S/10 a S/20 sobre 50 kg (+500 de
    # precio, −500 de cantidad) y "Litros" de S/4 a S/2 sobre 500 L (−1000
    # de precio, +1000 de cantidad). Sumados: −500 de precio, +500 de
    # cantidad. Los dos movimientos existen y ninguno se cancela.
    check("el efecto precio del grupo es la suma del de sus productos",
          round(float(_porfam["ef_precio"].iat[0]), 2), -500.0)
    check("el efecto cantidad del grupo también",
          round(float(_porfam["ef_cant"].iat[0]), 2), 500.0)
    check("el grupo cuenta sus productos",
          int(_porfam["n_items"].iat[0]), 2)
    # Sobre el agregado daría 0 y 0 (mismo gasto, misma "cantidad" 550 vs
    # 350): la cuenta cierra igual pero esconde los dos movimientos.
    # Sobre el AGREGADO (550 "unidades" contra 350, sumando kg con L) el
    # efecto precio daría −857, no −500: un número que cierra igual pero que
    # no es la suma de ningún movimiento real.
    check("sobre el agregado los efectos NO son los mismos (por eso no se usa)",
          round(_vap._puente(2000.0, 550.0, 2000.0, 350.0)[0], 2) != -500.0,
          True)

    check("_mes_parcial detecta el mes incompleto",
          _vap._mes_parcial(pd.Series(pd.to_datetime(
              ["2026-08-01", "2026-08-21"]))),
          (pd.Period("2026-08", "M"), 21))
    check("_mes_parcial no marca un mes cerrado",
          _vap._mes_parcial(pd.Series(pd.to_datetime(
              ["2026-07-01", "2026-07-31"]))), None)

    # ── Documentos SUNAT: cruce contra el parquet de Compras ────────────
    # Sin red ni Streamlit: son funciones puras sobre DataFrames armados a
    # mano, pensadas para reproducir el bug real que motivó acotar por
    # fecha ANTES de armar la clave (ver el docstring de
    # `_parquet_agrupado_por_documento`) — no una copia de la medición
    # contra datos reales, sino el caso mínimo que la explica.
    from graficos.compras import documentos_sunat as _ds

    check("_llave_documento_parquet decodifica serie+numero",
          _ds._llave_documento_parquet(pd.Series(["F0E001000001328"])).iloc[0],
          "E001-1328")
    check("_llave_documento_parquet sin ceros a la izquierda",
          _ds._llave_documento_parquet(pd.Series(["F0F001000000012"])).iloc[0],
          "F001-12")

    # _parquet_agrupado_por_documento: ACOTA por fecha antes de agrupar.
    # Dos filas con la MISMA clave ("E001-1") pero de años distintos — si
    # no acotara, se sumarían como si fueran el mismo documento. De paso,
    # el RUC de la fila 2024 trae el espacio final real que se ve en el
    # parquet (~24% de las filas, medido) — tiene que llegar limpio.
    # E001-2 tiene DOS líneas de producto del mismo documento: prueba que
    # total_pq/base_pq salgan de TOTAL DOCUMENTO/TOTAL NETO con "first"
    # (59.0/45.0, repetidos en las dos líneas) y NO de sumar
    # VALOR_BRUTO_COMPRA_MN/VALOR_COMPRA por línea (40+30=70 / 30+20=50 —
    # el proxy que se usaba antes de que existieran las columnas reales,
    # ver `COL_TOTAL_PARQUET` / `COL_BASE_PARQUET`).
    _pq = pd.DataFrame({
        "NUM_DOCUMENTO": ["F0E001000000001", "F0E001000000001",
                          "F0E001000000002", "F0E001000000002"],
        "NOMBRE_PROVEEDOR": ["GIANO MARINE SAC", "GIANO MARINE SAC",
                             "OTRO PROVEEDOR", "OTRO PROVEEDOR"],
        "INDICADOR TRIBUTARIO": ["20111111111", "20111111111 ",
                                 "20444444444", "20444444444"],
        "VALOR_COMPRA": [100.0, 500.0, 30.0, 20.0],
        "VALOR_BRUTO_COMPRA_MN": [118.0, 590.0, 40.0, 30.0],
        "TOTAL NETO": [100.0, 500.0, 45.0, 45.0],
        "TOTAL DOCUMENTO": [118.0, 590.0, 59.0, 59.0],
        "FECHA_EMISION_DOC": pd.to_datetime(
            ["2026-07-06", "2024-01-01", "2026-07-10", "2026-07-10"]),
    })
    _g = _ds._parquet_agrupado_por_documento(
        _pq, "FECHA_EMISION_DOC", pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-31"))
    check("_parquet_agrupado acota por fecha (deja fuera el de 2024)",
          len(_g), 2)
    check("_parquet_agrupado no mezcla los dos años",
          float(_g.loc[_g["documento"] == "E001-1", "total_pq"].iloc[0]), 118.0)
    check("_parquet_agrupado limpia el espacio final del RUC",
          _g.loc[_g["documento"] == "E001-1", "ruc_pq"].iloc[0], "20111111111")
    check("_parquet_agrupado total_pq usa TOTAL DOCUMENTO (first), no la "
          "suma por línea",
          float(_g.loc[_g["documento"] == "E001-2", "total_pq"].iloc[0]), 59.0)
    check("_parquet_agrupado base_pq usa TOTAL NETO (first), no la suma "
          "por línea",
          float(_g.loc[_g["documento"] == "E001-2", "base_pq"].iloc[0]), 45.0)

    # Sin TOTAL DOCUMENTO/TOTAL NETO (red de seguridad: parquets viejos o
    # un entorno donde todavía no se propagaron), cae al proxy de siempre.
    _pq_sin_total = _pq.drop(columns=["TOTAL DOCUMENTO", "TOTAL NETO"])
    _g_sin_total = _ds._parquet_agrupado_por_documento(
        _pq_sin_total, "FECHA_EMISION_DOC",
        pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-31"))
    check("_parquet_agrupado sin TOTAL DOCUMENTO cae a sumar "
          "VALOR_BRUTO_COMPRA_MN",
          float(_g_sin_total.loc[_g_sin_total["documento"] == "E001-2",
                                 "total_pq"].iloc[0]), 70.0)
    check("_parquet_agrupado sin TOTAL NETO cae a sumar VALOR_COMPRA",
          float(_g_sin_total.loc[_g_sin_total["documento"] == "E001-2",
                                 "base_pq"].iloc[0]), 50.0)

    # cruzar_con_parquet: los 4 estados + el orden de desambiguación
    # (RUC exacto primero, nombre como red de seguridad después).
    # E001-4: compra EXONERADA -- el SIRE la reporta con base_imponible=0
    # y todo el importe en no_gravado (caso real medido: "LA CESTA
    # S.A.C.", alimentos sin procesar). TOTAL NETO del parquet no separa
    # gravado de no gravado, así que base_sunat tiene que sumar los dos
    # campos del SIRE para ser comparable -- si no, esto saldría
    # "Diferencia" pese a no haber ninguna real.
    _sire = pd.DataFrame({
        "documento": ["E001-1", "E001-2", "E001-3", "E001-9", "E001-4"],
        "proveedor": ["GIANO MARINE SAC", "PROVEEDOR B", "PROVEEDOR C", "SIN PAR",
                      "EXENTO SAC"],
        "ruc_proveedor": ["20111111111", "20222222222", "20333333333",
                          "20999999999", "20555555555"],
        "fecha_emision": pd.to_datetime(["2026-07-06"] * 5),
        "base_imponible": [100.0, 200.0, 300.0, 400.0, 0.0],
        "no_gravado": [0.0, 0.0, 0.0, 0.0, 500.0],
        "total": [118.0, 236.0, 354.0, 472.0, 500.0],
        "situacion": ["Registrado"] * 5,
    })
    # E001-1: DOS candidatos con RUC distinto -- uno con el RUC EXACTO del
    # SIRE (debe ganar por RUC, aunque el nombre no se parezca en nada) y
    # otro con nombre casi idéntico pero RUC ajeno (NO debe ganar: antes
    # de tener RUC, el nombre solo lo habría elegido a él por error).
    # E001-2: mismo caso que ya cubría el nombre como red de seguridad --
    # acá el RUC del parquet viene VACÍO en ambos candidatos (columna
    # ausente de esa fila), así que cae al fallback por nombre de siempre.
    _g2 = pd.DataFrame({
        "documento": ["E001-1", "E001-1", "E001-2", "E001-2", "E001-3", "E001-8",
                      "E001-4"],
        "ruc_pq": ["20111111111", "20999999999", "", "", "20333333333",
                  "20777777777", "20555555555"],
        "proveedor_pq": ["NOMBRE IRRECONOCIBLE SAC", "GIANO MARINE SAC",
                         "PROVEEDOR B SAC", "OTRO TOTAL",
                         "PROVEEDOR C DIFERENTE", "SOLO SISTEMA SAC",
                         "EXENTO SAC"],
        "base_pq": [100.0, 999.0, 200.0, 9999.0, 305.0, 80.0, 500.0],
        "total_pq": [118.0, 1180.0, 236.0, 11800.0, 359.9, 94.4, 500.0],
        "fecha_pq": pd.to_datetime(["2026-07-06"] * 7),
    })
    _cruce = _ds.cruzar_con_parquet(_sire, _g2)

    def _fila(doc):
        return _cruce[(_cruce["documento"] == doc)
                      & (_cruce["estado"] != "Solo sistema")].iloc[0]

    check("cruce E001-1: el RUC exacto gana aunque el nombre no calce",
          _fila("E001-1")["proveedor_sistema"], "NOMBRE IRRECONOCIBLE SAC")
    check("cruce E001-1: NO el candidato de nombre parecido con RUC ajeno",
          _fila("E001-1")["total_sistema"], 118.0)
    check("cruce E001-1: monto exacto -> Coincide", _fila("E001-1")["estado"], "Coincide")
    check("cruce E001-2: sin RUC utilizable, cae al nombre (red de seguridad)",
          _fila("E001-2")["proveedor_sistema"], "PROVEEDOR B SAC")
    check("cruce E001-3: diferencia real de monto -> Diferencia",
          _fila("E001-3")["estado"], "Diferencia")
    check("cruce E001-9: no está en el parquet -> Solo SUNAT",
          _fila("E001-9")["estado"], "Solo SUNAT")
    check("cruce E001-4: base_imponible=0 + no_gravado real -> Coincide, "
          "no Diferencia",
          _fila("E001-4")["estado"], "Coincide")
    check("cruce E001-4: base_sunat suma base_imponible + no_gravado",
          _fila("E001-4")["base_sunat"], 500.0)
    check("cruce E001-8: solo en el parquet -> Solo sistema",
          _cruce[(_cruce["documento"] == "E001-8")
                & (_cruce["estado"] == "Solo sistema")].shape[0], 1)
    # El candidato de E001-1 con RUC ajeno, y el de E001-2 descartado por
    # nombre: ninguno de los dos debe perderse en silencio -- cada uno
    # tiene que aparecer como su propio "Solo sistema".
    check("cruce: el candidato con RUC ajeno no se pierde",
          ((_cruce["documento"] == "E001-1")
           & (_cruce["proveedor_sistema"] == "GIANO MARINE SAC")
           & (_cruce["estado"] == "Solo sistema")).any(), True)

    # Numero de documento DEL SISTEMA (columna "Documento sistema", a
    # pedido 2026-08-24). Es el NUM_DOCUMENTO crudo del parquet, no la
    # llave normalizada: la llave ya se muestra en "Documento SUNAT" y
    # seria una copia byte a byte. Ver `arquitectura.md` regla #143.
    check("_parquet_agrupado arrastra el NUM_DOCUMENTO crudo",
          _g.loc[_g["documento"] == "E001-1", "num_doc_pq"].iloc[0],
          "F0E001000000001")
    _sire2 = pd.DataFrame({
        "documento": ["E001-1", "E001-9"],
        "proveedor": ["GIANO MARINE SAC", "SIN PAR"],
        "ruc_proveedor": ["20111111111", "20999999999"],
        "fecha_emision": pd.to_datetime(["2026-07-06"] * 2),
        "base_imponible": [100.0, 400.0], "no_gravado": [0.0, 0.0],
        "total": [118.0, 472.0], "situacion": ["Registrado"] * 2,
    })
    _cruce2 = _ds.cruzar_con_parquet(_sire2, _g)
    check("cruce: la fila emparejada trae el numero crudo del sistema",
          _cruce2.loc[(_cruce2["documento"] == "E001-1")
                      & (_cruce2["estado"] != "Solo sistema"),
                      "documento_sistema"].iloc[0], "F0E001000000001")
    check("cruce: un 'Solo SUNAT' no inventa numero de sistema",
          _cruce2.loc[_cruce2["estado"] == "Solo SUNAT",
                      "documento_sistema"].iloc[0], "")
    check("cruce: un 'Solo sistema' SI lo trae",
          _cruce2.loc[_cruce2["estado"] == "Solo sistema",
                      "documento_sistema"].iloc[0], "F0E001000000002")
    # `cruzar_con_parquet` es publica y hay llamadores (estos tests) que
    # arman el df del parquet a mano, sin la columna nueva: no puede
    # reventar por eso.
    check("cruce: sin columna num_doc_pq no revienta, queda vacio",
          _cruce.loc[_cruce["estado"] == "Coincide",
                     "documento_sistema"].iloc[0], "")

    # Media seleccion del calendario = UN DIA, no "no hay rango". Reportado
    # 2026-08-24: elegir un solo dia (hoy/ayer) dejaba la vista con un
    # mensaje pidiendo elegir fecha... y sin el pill de fecha en pantalla,
    # porque el `return` temprano se lo llevaba puesto. Ver regla #115.
    import datetime as _dt
    _h, _a = _dt.date(2026, 8, 24), _dt.date(2026, 8, 23)
    check("media seleccion (1 fecha) vale como rango de un dia",
          _ds._dia_o_rango((_h,)), (_h, _h))
    check("segunda fecha en None tambien es un dia",
          _ds._dia_o_rango((_h, None)), (_h, _h))
    check("un rango completo pasa tal cual", _ds._dia_o_rango((_a, _h)), (_a, _h))
    check("una fecha suelta (no tupla) es un dia", _ds._dia_o_rango(_h), (_h, _h))
    check("sin rango en session_state", _ds._dia_o_rango(None), (None, None))
    check("tupla vacia", _ds._dia_o_rango(()), (None, None))
    check("tupla de Nones", _ds._dia_o_rango((None, None)), (None, None))
    check("cruce: el candidato descartado por nombre tampoco se pierde",
          ((_cruce["documento"] == "E001-2")
           & (_cruce["proveedor_sistema"] == "OTRO TOTAL")
           & (_cruce["estado"] == "Solo sistema")).any(), True)
    check("cruce: sin filas de más (5 SIRE + 3 solo-sistema reales)",
          len(_cruce), 8)

    # ── Comparativo vs Año Pasado (Ventas) ──────────────────────────────
    import datetime as _dt
    from graficos import ventas_comparativo as _vc

    # Pascua: fechas conocidas (control externo, no auto-referencial)
    check("_pascua 2026", _vc._pascua(2026), _dt.date(2026, 4, 5))
    check("_pascua 2025", _vc._pascua(2025), _dt.date(2025, 4, 20))
    check("_pascua 2024", _vc._pascua(2024), _dt.date(2024, 3, 31))

    _fer26 = _vc._feriados_peru(2026)
    check("feriado fijo (28 jul)", _dt.date(2026, 7, 28) in _fer26, True)
    check("feriado movible (Viernes Santo 2026)",
          _dt.date(2026, 4, 3) in _fer26, True)
    check("día común NO es feriado", _dt.date(2026, 7, 27) in _fer26, False)

    # Alineación por fecha calendario: mismo día/mes, año anterior
    check("equivalente calendario",
          _vc._fecha_equivalente(_dt.date(2026, 8, 5), "calendario"),
          _dt.date(2025, 8, 5))
    check("equivalente calendario 29-feb → 28",
          _vc._fecha_equivalente(_dt.date(2024, 2, 29), "calendario"),
          _dt.date(2023, 2, 28))

    # Alineación por semana ISO: el DÍA DE SEMANA es lo que se conserva
    _orig = _dt.date(2026, 8, 5)                      # miércoles
    _eq = _vc._fecha_equivalente(_orig, "semana")
    check("equivalente semana conserva día de semana",
          _eq.weekday(), _orig.weekday())
    check("equivalente semana conserva semana ISO",
          _eq.isocalendar()[1], _orig.isocalendar()[1])
    check("equivalente semana cae en el año anterior", _eq.year, 2025)
    # Semana 53 (2026 la tiene; 2025 no) → cae a la 52 sin reventar
    _s53 = _dt.date.fromisocalendar(2026, 53, 3)
    check("equivalente semana 53 → 52 sin error",
          _vc._fecha_equivalente(_s53, "semana").isocalendar()[1], 52)

    check("_etiqueta_clave día",
          _vc._etiqueta_clave(_dt.date(2026, 8, 5), "Día"), "Mié 05/08")

    # ── Granularidad semana / mes ───────────────────────────────────────
    # Claves hacia atrás: terminan SIEMPRE en el período del ancla
    _cl_d = _vc._claves_hacia_atras(_dt.date(2026, 8, 5), "Día", 3)
    check("claves día cuenta", len(_cl_d), 3)
    check("claves día terminan en el ancla", _cl_d[-1], _dt.date(2026, 8, 5))
    check("claves día en orden", _cl_d[0], _dt.date(2026, 8, 3))

    _cl_s = _vc._claves_hacia_atras(_dt.date(2026, 8, 5), "Semana", 3)
    check("claves semana cuenta", len(_cl_s), 3)
    check("claves semana terminan en la del ancla",
          _cl_s[-1], (2026, _dt.date(2026, 8, 5).isocalendar()[1]))

    # Cruce de año: 3 meses hacia atrás desde enero cae en el año anterior
    _cl_m = _vc._claves_hacia_atras(_dt.date(2026, 1, 15), "Mes", 3)
    check("claves mes cruzan el año", _cl_m, [(2025, 11), (2025, 12), (2026, 1)])

    # Clave AP: mismo número de período, un año antes
    check("clave AP mes", _vc._clave_ap((2026, 3), "Mes", "semana"), (2025, 3))
    check("clave AP semana", _vc._clave_ap((2026, 20), "Semana", "semana"),
          (2025, 20))
    # 2025 no tiene semana 53 → cae a la 52 en vez de reventar
    check("clave AP semana 53 → 52",
          _vc._clave_ap((2026, 53), "Semana", "semana"), (2025, 52))

    # Rango de clave: el mes cierra en su último día real (28/30/31)
    check("rango mes feb-2025 (no bisiesto)",
          _vc._rango_de_clave((2025, 2), "Mes"),
          (_dt.date(2025, 2, 1), _dt.date(2025, 2, 28)))
    check("rango mes feb-2024 (bisiesto)",
          _vc._rango_de_clave((2024, 2), "Mes"),
          (_dt.date(2024, 2, 1), _dt.date(2024, 2, 29)))
    _ini_s, _fin_s = _vc._rango_de_clave((2026, 32), "Semana")
    check("rango semana arranca lunes", _ini_s.weekday(), 0)
    check("rango semana cierra domingo", _fin_s.weekday(), 6)

    # _clave_de_fecha invierte a _rango_de_clave (una fecha cae en su período)
    check("clave de fecha (mes)",
          _vc._clave_de_fecha(_dt.date(2026, 8, 5), "Mes"), (2026, 8))
    check("clave de fecha (semana)",
          _vc._clave_de_fecha(_dt.date(2026, 8, 5), "Semana"),
          (2026, _dt.date(2026, 8, 5).isocalendar()[1]))

    # Feriados en un rango: julio trae 28 y 29 (Fiestas Patrias)
    check("feriados en julio 2026",
          _vc._feriados_entre(_dt.date(2026, 7, 1), _dt.date(2026, 7, 31)), 2)
    check("feriados en un tramo sin ninguno",
          _vc._feriados_entre(_dt.date(2026, 7, 1), _dt.date(2026, 7, 27)), 0)
    # Semana Santa se muda de mes: 2024 cayó en marzo, 2026 en abril. Es el
    # caso que justifica el marcador de desbalance a nivel mes.
    check("Semana Santa 2024 en marzo",
          _vc._feriados_entre(_dt.date(2024, 3, 1), _dt.date(2024, 3, 31)), 2)
    check("Semana Santa 2026 en abril",
          _vc._feriados_entre(_dt.date(2026, 4, 1), _dt.date(2026, 4, 30)), 2)

    check("_etiqueta_clave mes", _vc._etiqueta_clave((2026, 8), "Mes"), "Ago 26")

    # _pct: sin base con la que comparar devuelve None (hueco en la linea),
    # NO 0 — un 0 se leeria como "no cambio", que es una afirmacion falsa.
    check("_pct normal", _vc._pct(80, 100), -20.0)
    check("_pct base cero → None", _vc._pct(80, 0), None)
    check("_pct base None → None", _vc._pct(80, None), None)
    check("_pct actual cero es un dato real", _vc._pct(0, 100), -100.0)

    check("_fmt_soles_compacto miles", _vc._fmt_soles_compacto(636448), "S/ 636k")
    check("_fmt_soles_compacto bajo mil", _vc._fmt_soles_compacto(480), "S/ 480")
    check("_fmt_soles_compacto exacto mil", _vc._fmt_soles_compacto(1000), "S/ 1k")

    # ── Recorte del período EN CURSO (comparación justa) ────────────────
    # Ancla 09/08/2026: agosto va del 1 al 9, así que el agosto del año
    # pasado tiene que recortarse a sus primeros 9 días — si no, 9 días
    # contra 31 dan un −83% que es puro calendario, no una caída de ventas.
    _ancla = _dt.date(2026, 8, 9)
    _cl = _vc._claves_hacia_atras(_ancla, "Mes", 2)          # [(2026,7),(2026,8)]
    _cl_ap = [_vc._clave_ap(k, "Mes", "semana") for k in _cl]
    _ra, _rp, _parc = _vc._rangos_comparables(_cl, _cl_ap, "Mes", _ancla)
    check("recorte: sólo el último período es parcial", _parc, {1})
    check("recorte: el mes cerrado NO se toca",
          (_ra[0][1], _ra[0][2]), (_dt.date(2026, 7, 1), _dt.date(2026, 7, 31)))
    check("recorte: el mes en curso corta en el ancla",
          (_ra[1][1], _ra[1][2]), (_dt.date(2026, 8, 1), _ancla))
    check("recorte: el AP del mes en curso corta al mismo tramo",
          (_rp[1][1], _rp[1][2]), (_dt.date(2025, 8, 1), _dt.date(2025, 8, 9)))
    check("recorte: el AP del mes cerrado queda entero",
          (_rp[0][1], _rp[0][2]), (_dt.date(2025, 7, 1), _dt.date(2025, 7, 31)))
    # Los dos lados suman la MISMA cantidad de días (eso es lo que hace justa
    # la comparación — es la propiedad que importa, no las fechas en sí)
    check("recorte: ambos lados cubren los mismos días",
          (_ra[1][2] - _ra[1][1]), (_rp[1][2] - _rp[1][1]))

    # Con el ancla en el último día del mes, nada es parcial
    _ra2, _rp2, _parc2 = _vc._rangos_comparables(
        [(2026, 7)], [(2025, 7)], "Mes", _dt.date(2026, 7, 31))
    check("recorte: mes completo no marca parcial", _parc2, set())

    # ── Mapa por hora (Ventas › Por hora) ───────────────────────────────
    from graficos import ventas_horario as _vh

    # Granularidad Año: la única que NO delega en ventas_comparativo
    check("horario · claves año", _vh._claves_hacia_atras(_dt.date(2026, 8, 14),
                                                          "Año", 3),
          [2024, 2025, 2026])
    check("horario · rango año", _vh._rango_de_clave(2025, "Año"),
          (_dt.date(2025, 1, 1), _dt.date(2025, 12, 31)))
    check("horario · etiqueta año", _vh._etiqueta_clave(2025, "Año"), "2025")
    # ...y las otras tres siguen delegando (mismo resultado que allá)
    check("horario · claves mes delegan",
          _vh._claves_hacia_atras(_dt.date(2026, 1, 15), "Mes", 3),
          _vc._claves_hacia_atras(_dt.date(2026, 1, 15), "Mes", 3))

    # Columnas por período: en Mes dependen del mes REAL (febrero no lleva 31
    # columnas vacías al final, que se leerían como una caída de ventas)
    check("horario · columnas semana", _vh._columnas((2026, 32), "Semana")[0], 7)
    check("horario · columnas día", _vh._columnas(_dt.date(2026, 8, 5), "Día")[0], 1)
    check("horario · columnas año", _vh._columnas(2025, "Año")[0], 12)
    check("horario · columnas feb bisiesto", _vh._columnas((2024, 2), "Mes")[0], 29)
    check("horario · columnas feb normal", _vh._columnas((2025, 2), "Mes")[0], 28)

    # El período EN CURSO se recorta al último día con datos: el 14 de agosto
    # "agosto" son 14 columnas, no 31 con diecisiete vacías a la derecha (que
    # se leerían como una caída). Los períodos CERRADOS no se tocan.
    check("horario · el mes en curso se recorta al ancla",
          _vh._columnas((2026, 8), "Mes", _dt.date(2026, 8, 14))[0], 14)
    check("horario · el mes cerrado queda entero",
          _vh._columnas((2026, 7), "Mes", _dt.date(2026, 8, 14))[0], 31)
    check("horario · las etiquetas se recortan con las columnas",
          _vh._columnas((2026, 8), "Mes", _dt.date(2026, 8, 14))[1][-1], "14")

    # El eje X de granularidad Mes escribe "1 Ago", no "1" (2026-08-15): el
    # mes vivía sólo en el título del panel. `_columnas` NO se toca —de sus
    # etiquetas sale también el nombre de una marca, donde el mes ya viene
    # por otro lado y quedaría "días 7 Ago–8 Ago"—, así que el sufijo se
    # agrega en la figura y estas dos guardas van juntas: la de abajo mira
    # el eje, ésta se asegura de que el crudo siga crudo.
    check("horario · las etiquetas crudas de Mes son sólo el número",
          _vh._columnas((2026, 8), "Mes")[1][:2], ["1", "2"])
    check("horario · el nombre de la marca no lleva el mes dos veces",
          _vh._etiqueta_columnas({"c0": 6, "c1": 7}, (2026, 8), "Mes"),
          "días 7–8")
    # Con el sufijo la etiqueta pasa de 2 caracteres a 6: si el paso siguiera
    # midiendo la cruda, 31 días de "31 Ago" se pisarían unos a otros.
    check("horario · el paso crece con la etiqueta más larga",
          _vh._paso_etiquetas(31, 6) > _vh._paso_etiquetas(31, 2), True)
    # Y la comprobación de punta a punta: lo que termina escrito en el eje.
    _cd_eje = pd.DataFrame({"col": [0, 1], "hora": [19, 21],
                            "venta": [100.0, 200.0], "cant": [3.0, 5.0],
                            "desc": [0.0, 0.0], "pax": [2.0, 4.0],
                            "ticket": [50.0, 50.0]})
    _tt_mes = _vh._fig_mapa([_cd_eje], [(2026, 8)], "Mes", "venta", [],
                            [19, 21]).layout.xaxis.ticktext
    # Los ticks pueden venir envueltos en <span> (fin de semana / feriado),
    # así que se comprueba por contenido y no por igualdad exacta.
    check("horario · el eje de Mes escribe el mes en cada día",
          all("Ago" in t for t in _tt_mes), True)
    check("horario · y el primero es el día 1",
          any("1 Ago" in t for t in _tt_mes), True)
    _tt_sem = _vh._fig_mapa([_cd_eje], [(2026, 32)], "Semana", "venta", [],
                            [19, 21]).layout.xaxis.ticktext
    check("horario · el eje de Semana se queda con el día",
          any("Ago" in t for t in _tt_sem), False)

    # ── Cuadrícula del mapa ─────────────────────────────────────────────
    # Va como UN shape `path` con muchos subtrazos, encima del heatmap (la
    # grilla menor del eje se dibuja debajo y la tapaba el <image>). Lo que
    # se fija acá es la GEOMETRÍA: los cortes caen en los bordes de celda
    # (± 0.5, nunca en el centro) y el hueco entre paneles queda cerrado a
    # los lados pero SIN líneas dentro — cruzarlo diría que ahí hay días.
    _fig_rej = _vh._fig_mapa([_cd_eje, _cd_eje], [(2026, 32), (2026, 33)],
                             "Semana", "venta", [], [19, 21])
    _rej = [s for s in _fig_rej.layout.shapes if s.type == "path"]
    check("horario · la cuadrícula es un solo shape", len(_rej), 1)
    check("horario · y va encima del heatmap", _rej[0].layer, "above")
    _seg = [s for s in _rej[0].path.split("M") if s]
    _pt = lambda s, i, j: float(s.split("L")[i].split(",")[j])  # noqa: E731
    _vert = sorted({_pt(s, 0, 0) for s in _seg if _pt(s, 0, 0) == _pt(s, 1, 0)})
    check("horario · cortes verticales en los bordes de cada día",
          _vert, [-0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5,
                  7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5])
    _hor = sorted({(_pt(s, 0, 0), _pt(s, 1, 0))
                   for s in _seg if _pt(s, 0, 1) == _pt(s, 1, 1)})
    check("horario · las horizontales no cruzan el hueco entre paneles",
          _hor, [(-0.5, 6.5), (7.5, 14.5)])

    # ── Capa de selección ───────────────────────────────────────────────
    # Un punto por CELDA, haya venta o no. Si vuelve a haberlos sólo donde
    # hay datos: un arrastre sobre celdas vacías no devuelve nada, Streamlit
    # no ve cambio, no hay rerun, y el rectángulo punteado de Plotly se
    # queda dibujado para siempre (pasó, 2026-08-15). Además la marca se
    # encogería en silencio hasta el último día con venta.
    _sel_pts = [t for t in _fig_rej.data
                if t.type == "scatter" and t.hoverinfo == "skip"]
    check("horario · la capa de selección cubre TODAS las celdas",
          len(_sel_pts[0].x) if _sel_pts else 0,
          2 * 7 * 2)          # 2 paneles × 7 días × 2 horas
    # ...y el hover sigue colgando de las celdas CON datos, que son las que
    # tienen números que mostrar.
    _hov = [t for t in _fig_rej.data
            if t.type == "scatter" and t.hoverinfo != "skip"]
    check("horario · el hover sólo va donde hay datos",
          len(_hov[0].x) if _hov else 0, 4)
    check("horario · la selección no roba el hover",
          _sel_pts[0].hoverinfo if _sel_pts else None, "skip")
    # La semana en curso también: un viernes son 5 columnas, no 7.
    check("horario · la semana en curso se recorta",
          _vh._columnas((2026, 33), "Semana", _dt.date(2026, 8, 14))[0], 5)
    check("horario · el año en curso se recorta al mes",
          _vh._columnas(2026, "Año", _dt.date(2026, 8, 14))[0], 8)

    # Etiquetas del eje X: el paso sale del ancho por columna del gráfico
    # ENTERO, no de las columnas de UN panel. El bug que corrige: un mes en
    # curso de 13 días saltaba un día de por medio (13 > 12 disparaba el paso
    # 2) con medio gráfico vacío al lado.
    check("horario · un mes solo muestra TODOS los días",
          [_vh._paso_etiquetas(n, 2) for n in (11, 13, 20, 31)], [1, 1, 1, 1])
    check("horario · comparando meses las etiquetas se ralean",
          _vh._paso_etiquetas(126, 2) > 1, True)
    check("horario · el paso crece con el largo de la etiqueta",
          _vh._paso_etiquetas(51, 3) >= _vh._paso_etiquetas(51, 1), True)
    check("horario · el paso nunca baja de 1",
          _vh._paso_etiquetas(1, 9), 1)

    # Con POCAS columnas la celda no se estira a lo ancho de la tarjeta: se
    # topea. Sin esto, la semana en curso un martes son 2 celdas de 376px
    # (medido) — dos banderas, no un mapa. Es el efecto lateral de abrir
    # siempre en el período en curso.
    _tope = _vh._RATIO_MAX_CELDA * _vh._PX_HORA

    def _ancho_celda(n):
        x0, x1 = _vh._rango_x(n)
        return _vh._ANCHO_UTIL / (x1 - x0)

    # El tope es APROXIMADO: el número de slots es entero, así que
    # `ancho // tope` deja la celda un poco por encima (770/11 = 70 contra
    # un tope de 66). Lo que se fija acá es lo que de verdad importa —que no
    # se estire a bandera—, con sitio para ese redondeo: nunca más de cuatro
    # veces el alto de fila. Si alguien sube el ratio, esto salta.
    check("horario · una sola columna no se estira a bandera",
          _ancho_celda(1) <= 4 * _vh._PX_HORA, True)
    # El sobrante va TODO a la derecha: repartirlo a los dos lados metía
    # 132px (medidos) entre el eje de horas y la primera celda.
    check("horario · el mapa arranca SIEMPRE pegado al eje de horas",
          [_vh._rango_x(n)[0] for n in (1, 2, 11, 31, 126)],
          [-0.5, -0.5, -0.5, -0.5, -0.5])
    check("horario · el sobrante queda a la derecha",
          _vh._rango_x(2)[1], _vh._ANCHO_UTIL // _tope - 0.5)
    check("horario · con muchas columnas el rango es el justo",
          _vh._rango_x(31), [-0.5, 30.5])
    # El caso que motivó recalibrar (2026-08-15): un mes EN CURSO de 13 días
    # dejaba tres columnas de hueco entre el último día y la barra de color.
    # Con el tope atado al alto de fila y el ancho puesto al día, el rango es
    # el justo desde los 13 días.
    check("horario · un mes en curso de 13 días no deja hueco",
          _vh._rango_x(13), [-0.5, 12.5])

    # ── Horas en am/pm, no en formato 24h ───────────────────────────────
    # El mediodía y la medianoche son los dos que se escriben mal solos.
    check("horario · hora am/pm",
          [_vh._etiqueta_hora(h) for h in (0, 9, 12, 13, 19, 23)],
          ["12 am", "9 am", "12 pm", "1 pm", "7 pm", "11 pm"])
    check("horario · tramo de una sola hora", _vh._tramo_horas(19, 19), "7 pm")
    check("horario · tramo de varias horas",
          _vh._tramo_horas(18, 21), "6 pm–9 pm")

    # ── Fin de semana y feriado (mismo calendario que "Año Pasado") ──────
    _fer26 = set(_vc._feriados_peru(2026))
    check("horario · 28 de julio marcado como feriado",
          _vh._marca_dia(_dt.date(2026, 7, 28), _fer26), "feriado")
    check("horario · un sábado común es finde",
          _vh._marca_dia(_dt.date(2026, 8, 8), _fer26), "finde")
    check("horario · un martes común no lleva marca",
          _vh._marca_dia(_dt.date(2026, 8, 11), _fer26), "")
    # Un feriado que cae en finde se marca como FERIADO: que era domingo ya
    # se veía; lo que no se veía es que además era feriado.
    _dom_fer = [d for d in _fer26 if d.weekday() >= 5]
    if _dom_fer:
        check("horario · el feriado gana al fin de semana",
              _vh._marca_dia(_dom_fer[0], _fer26), "feriado")
    check("horario · sin fecha (columna de un año) no hay marca",
          _vh._marca_dia(None, _fer26), "")

    # La columna → fecha, que es de donde sale la marca
    check("horario · fecha de la columna en Mes",
          _vh._fecha_de_columna((2026, 7), "Mes", 27), _dt.date(2026, 7, 28))
    check("horario · fecha de la columna en Semana",
          _vh._fecha_de_columna((2026, 32), "Semana", 0).weekday(), 0)
    check("horario · en Año la columna no es un día",
          _vh._fecha_de_columna(2026, "Año", 3), None)

    # Elegir un período por una fecha CUALQUIERA (no sólo los recientes)
    check("horario · una fecha suelta cae en su mes",
          _vh._clave_de_fecha(_dt.date(2025, 2, 14), "Mes"), (2025, 2))
    check("horario · una fecha suelta cae en su año",
          _vh._clave_de_fecha(_dt.date(2025, 2, 14), "Año"), 2025)
    check("horario · una fecha suelta cae en su día",
          _vh._clave_de_fecha(_dt.date(2025, 2, 14), "Día"),
          _dt.date(2025, 2, 14))

    # El arranque es SIEMPRE un período: el EN CURSO. Comparar es una decisión
    # explícita del usuario y tiene su botón.
    check("horario · arranca con un solo período", _vh._N_DEFECTO, 1)
    check("horario · y ese período es el EN CURSO",
          _vh._claves_hacia_atras(_dt.date(2026, 8, 14), "Mes",
                                  _vh._N_DEFECTO), [(2026, 8)])

    _f = pd.Series(pd.to_datetime(["2026-08-05 13:00", "2026-08-09 20:30"]))
    check("horario · columna en semana (mié=2, dom=6)",
          list(_vh._columna_de_fecha(_f, "Semana")), [2, 6])
    check("horario · columna en mes (día-1)",
          list(_vh._columna_de_fecha(_f, "Mes")), [4, 8])
    check("horario · columna en año (mes-1)",
          list(_vh._columna_de_fecha(_f, "Año")), [7, 7])
    check("horario · columna en día es siempre 0",
          list(_vh._columna_de_fecha(_f, "Día")), [0, 0])

    # OPCIÓN A: un arrastre que cruza de panel deja UNA MARCA POR PANEL, con
    # las coordenadas que le tocaron a cada lado. Es la decisión del usuario
    # (2026-08-14) y el corazón del gesto: arrastrar sobre dos semanas deja
    # la comparación armada de una pasada.
    _orden = _vh._orden_horas([12, 13, 19, 20, 21])
    _pts = [(0, 4, 19), (0, 5, 19), (0, 5, 20), (1, 4, 19), (1, 6, 21)]
    _ms = _vh._marcas_de_seleccion(_pts, _orden)
    check("horario · un arrastre a dos paneles → dos marcas", len(_ms), 2)
    check("horario · marca del panel 0 envuelve sus puntos", _ms[0],
          {"sel": 0, "c0": 4, "c1": 5, "h0": 19, "h1": 20})
    check("horario · marca del panel 1 envuelve LOS SUYOS", _ms[1],
          {"sel": 1, "c0": 4, "c1": 6, "h0": 19, "h1": 21})
    check("horario · una sola celda es un rectángulo 1x1",
          _vh._marcas_de_seleccion([(2, 3, 13)], _orden),
          [{"sel": 2, "c0": 3, "c1": 3, "h0": 13, "h1": 13}])

    # Acumulación: sin repetir, y al pasar del tope se van las MÁS VIEJAS —
    # un arrastre sobre los cuatro paneles tiene que dejar esas cuatro.
    _m1 = {"sel": 0, "c0": 0, "c1": 0, "h0": 12, "h1": 12}
    _m2 = {"sel": 1, "c0": 0, "c1": 0, "h0": 12, "h1": 12}
    check("horario · no duplica una marca ya puesta",
          _vh._agregar_marcas([_m1], [_m1]), [_m1])
    check("horario · acumula la nueva",
          _vh._agregar_marcas([_m1], [_m2]), [_m1, _m2])
    _viejas = [dict(_m1, sel=i) for i in range(4)]
    _nueva = {"sel": 3, "c0": 5, "c1": 5, "h0": 20, "h1": 20}
    check("horario · pasado el tope se va la más vieja",
          _vh._agregar_marcas(_viejas, [_nueva]), _viejas[1:] + [_nueva])

    # Celdas de una marca: el denominador de «venta por celda», la única
    # lectura honesta cuando dos marcas no miden lo mismo.
    _o4 = _vh._orden_horas([18, 19, 20, 21])
    check("horario · celdas de un rectángulo 3x4",
          _vh._celdas_de_marca({"sel": 0, "c0": 4, "c1": 6, "h0": 18, "h1": 21},
                               _o4), 12)
    check("horario · celdas de una celda suelta",
          _vh._celdas_de_marca({"sel": 0, "c0": 4, "c1": 4, "h0": 19, "h1": 19},
                               _o4), 1)

    # ── El turno cruza la medianoche ────────────────────────────────────
    # Con datos reales de R2 el eje traía [0, 13, …, 23]: las 00h son el
    # final de la noche anterior, no el principio del día. Ordenadas por
    # número quedaban arriba de todo y el eje numérico dejaba doce filas
    # vacías en el medio.
    _os = _vh._orden_horas({0, 13, 14, 19, 22, 23})
    check("horario · el orden arranca después del hueco mayor",
          _os, [13, 14, 19, 22, 23, 0])
    check("horario · una sola hora no rompe el orden",
          _vh._orden_horas({19}), [19])
    # «de 23h a 0h» son DOS horas. Con `h0 <= hora <= h1` habrían sido las
    # veinticuatro, y la marca se habría comido el día entero en silencio.
    check("horario · tramo que cruza la medianoche",
          _vh._horas_entre(_os, 23, 0), [23, 0])
    check("horario · tramo normal dentro del turno",
          _vh._horas_entre(_os, 13, 19), [13, 14, 19])
    check("horario · los extremos de una marca salen por POSICIÓN",
          _vh._marca_de_puntos(0, [1], [0, 23], _os),
          {"sel": 0, "c0": 1, "c1": 1, "h0": 23, "h1": 0})
    check("horario · celdas de una marca que cruza la medianoche",
          _vh._celdas_de_marca({"sel": 0, "c0": 1, "c1": 2, "h0": 23, "h1": 0},
                               _os), 4)

    check("horario · etiqueta de marca (semana)",
          _vh._etiqueta_marca({"sel": 0, "c0": 4, "c1": 6, "h0": 18, "h1": 21},
                              [(2026, 32)], "Semana"),
          f"{_vc._etiqueta_clave((2026, 32), 'Semana')} · Vie–Dom · 6 pm–9 pm")
    # En granularidad Día la columna ES el período: repetirlo daría
    # "vie 08/08 · vie", que no informa nada.
    check("horario · etiqueta de marca (día) no repite el período",
          _vh._etiqueta_marca({"sel": 0, "c0": 0, "c1": 0, "h0": 19, "h1": 19},
                              [_dt.date(2026, 8, 7)], "Día"),
          f"{_vc._etiqueta_clave(_dt.date(2026, 8, 7), 'Día')} · 7 pm")

    # La firma gobierna la `key` del chart, o sea CUÁNDO Streamlit remonta el
    # componente. Tiene que cambiar con lo que hace que sea otro mapa —ahí el
    # remonte es correcto, porque la selección vieja apunta a coordenadas que
    # ya no significan lo mismo—.
    check("horario · la firma cambia al cambiar la medida del mapa",
          _vh._firma("Semana", [(2026, 32)], "venta")
          != _vh._firma("Semana", [(2026, 32)], "pax"), True)
    check("horario · la firma cambia al cambiar la granularidad",
          _vh._firma("Semana", [(2026, 32)], "venta")
          != _vh._firma("Mes", [(2026, 32)], "venta"), True)
    check("horario · la firma cambia al comparar otro período",
          _vh._firma("Semana", [(2026, 32)], "venta")
          != _vh._firma("Semana", [(2026, 32), (2026, 33)], "venta"), True)
    # Y NO tiene que cambiar con las marcas: eso remontaba el chart en cada
    # arrastre y era el parpadeo que se reportó el 2026-08-15. Que la misma
    # selección no se re-procese en bucle lo resuelve la huella (`_K_SEL`),
    # no la key. La firma ya ni siquiera recibe las marcas — esta guarda deja
    # constancia de que sacarlas fue deliberado.
    check("horario · la firma NO mira las marcas (si no, parpadea)",
          "marcas" in _vh._firma.__code__.co_varnames, False)

    # ── Agregación por celda: pax NO se suma línea a línea ───────────────
    # `CANT PAX` se repite en CADA línea del pedido. Sumarla cuenta la misma
    # mesa una vez por plato: acá P1 tiene 2 líneas de 4 pax y P2 una de 2, o
    # sea 6 personas — no 10. Es un error que no rompe nada, sólo miente.
    _dfh = pd.DataFrame({
        "FEC REG DOCUMENTO": pd.to_datetime(
            ["2026-08-07 19:10", "2026-08-07 19:40", "2026-08-07 19:50",
             "2026-08-08 13:05"]),
        "VENTA ITEM DDOCUMENTO": [100.0, 60.0, 40.0, 90.0],
        "CANT PAX": [4, 4, 2, 3],
        "LLAVE LOCAL PEDIDO": ["P1", "P1", "P2", "P3"],
        "CANTIDAD ITEM DDOCUMENTO": [1, 2, 1, 1],
        "DESCUENTO ITEM DDOCUMENTO": [0.0, 10.0, 5.0, 0.0],
        "NOMBRE DESCUENTO": [None, "BCP", "  ", "Socios"],
        "GRUPO": ["Alimentos"] * 4,
        "SUB GRUPO": ["Fondos"] * 4,
        "NOMB ITEM VENTA": ["Lomo", "Lomo", "Ceviche", "Lomo"],
    })
    _colsh = {"fecha": "FEC REG DOCUMENTO", "venta": "VENTA ITEM DDOCUMENTO",
              "pax": "CANT PAX", "pedido": "LLAVE LOCAL PEDIDO",
              "prod": "NOMB ITEM VENTA", "cant": "CANTIDAD ITEM DDOCUMENTO",
              "fam": "GRUPO", "sub": "SUB GRUPO",
              "desc": "DESCUENTO ITEM DDOCUMENTO",
              "tipo_desc": "NOMBRE DESCUENTO"}
    _tr = _vh._prep_tramo(_dfh, _colsh, "Semana",
                          _dt.date(2026, 8, 3), _dt.date(2026, 8, 9))
    _cel = _vh._celdas(_tr)
    _c19 = _cel[(_cel["col"] == 4) & (_cel["hora"] == 19)].iloc[0]
    check("horario · pax deduplicado por pedido (4+4+2 → 6)",
          float(_c19["pax"]), 6.0)
    check("horario · venta de la celda suma las líneas",
          float(_c19["venta"]), 200.0)
    check("horario · descuento de la celda suma las líneas",
          float(_c19["desc"]), 15.0)
    check("horario · ticket = venta/pax (la definición del proyecto)",
          round(float(_c19["ticket"]), 4), round(200.0 / 6.0, 4))
    # Sin `NOMBRE DESCUENTO` no hay descuento: nulos y espacios en blanco caen
    # en «Sin descuento», que NO es relleno — es lo vendido a precio de lista.
    check("horario · tipo de descuento nulo → Sin descuento",
          sorted(_tr["tipo"].unique().tolist()),
          sorted([_vh._SIN_DSCTO, "BCP", "Socios"]))

    # El recorte por fecha se re-aplica en pandas (en modo demo el loader
    # devuelve el df entero): un tramo de un solo día deja fuera al resto.
    _tr1 = _vh._prep_tramo(_dfh, _colsh, "Semana",
                           _dt.date(2026, 8, 8), _dt.date(2026, 8, 8))
    check("horario · el tramo recorta por fecha en pandas", len(_tr1), 1)

    # Totales de una marca (el rectángulo del viernes 19h)
    _oh = _vh._orden_horas(_tr["hora"].unique())
    _tot = _vh._agregar_marca(_tr, {"sel": 0, "c0": 4, "c1": 4,
                                    "h0": 19, "h1": 19}, _oh)
    check("horario · total de marca: venta", _tot["venta"], 200.0)
    check("horario · total de marca: pax deduplicado", _tot["pax"], 6.0)
    _det = _vh._detalle_marca(_tr, {"sel": 0, "c0": 4, "c1": 4,
                                    "h0": 19, "h1": 19}, _oh)
    check("horario · el detalle parte el plato por tipo de descuento",
          sorted(_det[_det["prod"] == "Lomo"]["tipo"].tolist()),
          sorted([_vh._SIN_DSCTO, "BCP"]))

    return fallos


def _pruebas_estado_y_utils():
    """estado_rango.py y utils.py: lógica pura, cero Streamlit real.

    `estado_rango` es el DUEÑO ÚNICO del rango de fechas y su docstring
    documenta los desyncs (overlay ≠ calendario ≠ datos) que motivaron que
    exista. `utils` resuelve nombres de columna en TODO el repo: si
    `buscar_columna` deja de normalizar acentos, media app deja de
    encontrar sus columnas y no falla — simplemente muestra menos.

    Ninguno tenía un solo assert hasta el 2026-08-08.
    """
    import datetime

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    estado/utils · {nombre}")
        else:
            fallos += 1
            print(f"FALLA estado/utils · {nombre}: got={got!r} exp={exp!r}")

    # ── utils: normalización y búsqueda de columnas ─────────────────────
    from utils import _norm, buscar_columna, buscar_columna_fecha, resolver_columnas

    check("_norm quita acentos", _norm("Área"), "area")
    check("_norm colapsa separadores", _norm("Sub_Familia - 1"), "subfamilia1")
    check("_norm ya normalizado", _norm("stock"), "stock")

    df = pd.DataFrame({
        "Nombre Área": ["a"], "STOCK AL CIERRE": [1],
        "Fecha registro": pd.to_datetime(["2024-01-01"]),
    })
    # El match es por nombre NORMALIZADO: ni acentos ni mayúsculas ni
    # espacios tienen que coincidir con el parquet real.
    check("buscar_columna ignora acento y caja",
          buscar_columna(df, "nombre area"), "Nombre Área")
    check("buscar_columna ignora caja",
          buscar_columna(df, "Stock al Cierre"), "STOCK AL CIERRE")
    check("buscar_columna primer candidato que exista",
          buscar_columna(df, "no_existe", "Stock al Cierre"), "STOCK AL CIERRE")
    check("buscar_columna sin match", buscar_columna(df, "inexistente"), None)
    # Prefiere la columna datetime aunque haya otras con "fecha" en el nombre.
    check("buscar_columna_fecha por dtype",
          buscar_columna_fecha(df), "Fecha registro")

    # resolver_columnas: resuelve, DEDUPLICA y reporta las que faltan.
    enc, falt = resolver_columnas(df, ["Nombre Area", "nombre área", "ni_idea"])
    check("resolver_columnas deduplica", enc, ["Nombre Área"])
    check("resolver_columnas reporta faltantes", falt, ["ni_idea"])

    # ── estado_rango: qué clave usa cada reporte ────────────────────────
    from estado_rango import (
        _fin_de_mes, _recortar_media, atajos_rango, clave_rango,
    )

    check("clave_rango carga_por_rango",
          clave_rango("Ventas", True), "rango_carga_Ventas")
    check("clave_rango por categoría",
          clave_rango("Ajuste de Inventario", False, categoria="tiempo"),
          "ajuste_rango_aplicado_tiempo")
    check("clave_rango normal",
          clave_rango("Compras", False), "rango_franja_Compras")
    # carga_por_rango GANA sobre la categoría: el date-picker tiene que
    # controlar lo que se descarga de R2, o se pide un rango y se muestra otro.
    check("clave_rango: carga_por_rango tiene prioridad",
          clave_rango("X", True, categoria="tiempo"), "rango_carga_X")

    check("_fin_de_mes mes normal",
          _fin_de_mes(datetime.date(2024, 4, 10)), datetime.date(2024, 4, 30))
    check("_fin_de_mes febrero bisiesto",
          _fin_de_mes(datetime.date(2024, 2, 5)), datetime.date(2024, 2, 29))
    check("_fin_de_mes diciembre",
          _fin_de_mes(datetime.date(2024, 12, 3)), datetime.date(2024, 12, 31))

    # atajos_rango: descarta los que no intersectan la data y recorta el resto.
    hoy = datetime.date(2024, 6, 15)
    bounds = (datetime.date(2024, 3, 1), datetime.date(2024, 5, 31))
    atajos = dict((c, r) for c, _, r in atajos_rango(hoy, bounds))
    # "Este mes" es junio, la data acaba en mayo → no intersecta → fuera.
    check("atajos descarta el que no intersecta", "mes" in atajos, False)
    check("atajos: Todo = bounds exactos", atajos.get("todo"), bounds)
    # "Este año" (1-ene..31-dic) SÍ intersecta, y se recorta a los bounds.
    check("atajos recorta a bounds", atajos.get("anio"), bounds)
    check("atajos sin bounds no ofrece nada", atajos_rango(hoy, None), [])

    # _recortar_media: una media selección se queda a medias (la aridad es
    # el estado normal entre los dos clics, regla #196) pero SÍ se recorta,
    # porque los bounds encogen al salir de Documentos SUNAT y Streamlit no
    # perdona un valor fuera de [min_value, max_value] — tira
    # StreamlitAPIException y se cae la página. Ver regla #197.
    _b = (datetime.date(2026, 1, 1), datetime.date(2026, 8, 21))
    check("media selección por encima del tope se recorta",
          _recortar_media("_k_test", (datetime.date(2026, 8, 24),), _b),
          (datetime.date(2026, 8, 21),))
    check("media selección por debajo del piso se recorta",
          _recortar_media("_k_test", (datetime.date(2025, 1, 1),), _b),
          (datetime.date(2026, 1, 1),))
    check("y sigue siendo media selección, no un rango",
          len(_recortar_media("_k_test", (datetime.date(2026, 8, 24),), _b)), 1)
    check("dentro de bounds no se toca",
          _recortar_media("_k_test", (datetime.date(2026, 8, 10),), _b),
          (datetime.date(2026, 8, 10),))
    check("sin bounds no se toca",
          _recortar_media("_k_test", (datetime.date(2026, 8, 24),), None),
          (datetime.date(2026, 8, 24),))
    check("una tupla vacía pasa tal cual", _recortar_media("_k_test", (), _b), ())
    # Un año presente en la data se ofrece como chip propio.
    check("atajos incluye el año de la data", "y2023" in dict(
        (c, r) for c, _, r in atajos_rango(
            hoy, (datetime.date(2023, 1, 1), datetime.date(2024, 5, 31)))), True)

    return fallos


def _pruebas_periodo_por_vista():
    """graficos/periodo.py — la ventana PROPIA de una tarjeta.

    Lo que fijan estos asserts no es aritmética de fechas, es el criterio que
    motivó el módulo: la ventana se cuenta desde el ÚLTIMO DÍA CON DATOS, no
    desde `hoy`. Anclarla a `hoy` con parquets que llegan con retraso deja un
    tramo final vacío que se lee como una caída del negocio — y es
    exactamente el error que nadie ve, porque el gráfico sale lindo.

    El resto son los bordes que ya rompieron a otras vistas: heredar el rango
    tiene que ser un no-op, y una ventana más larga que el histórico no puede
    devolver un tramo que no existe (un eje de categorías dibujaría los meses
    vacíos).
    """
    import pandas as pd
    from graficos import periodo

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    periodo · {nombre}")
        else:
            fallos += 1
            print(f"FALLA periodo · {nombre}: got={got!r} exp={exp!r}")

    ancla = pd.Timestamp("2026-08-15")

    check("heredar no define ventana",
          periodo.ventana(periodo.HEREDA, ancla), None)
    check("sin ancla (df vacío) no define ventana",
          periodo.ventana("12m", None), None)

    # 12 meses que terminan el 15-ago arrancan el 16-ago del año pasado: el 15
    # ya lo contó la ventana anterior.
    check("12m arranca al día siguiente del año pasado",
          periodo.ventana("12m", ancla)[0], pd.Timestamp("2025-08-16"))
    check("12m termina en el ancla", periodo.ventana("12m", ancla)[1], ancla)
    check("3m cuenta tres meses", periodo.ventana("3m", ancla)[0],
          pd.Timestamp("2026-05-16"))

    # El piso recorta: pedir 24m sobre 8 meses de histórico no puede devolver
    # un arranque anterior al primer dato.
    check("la ventana no arranca antes del primer dato",
          periodo.ventana("24m", ancla, minimo=pd.Timestamp("2026-01-01"))[0],
          pd.Timestamp("2026-01-01"))
    check("Todo va del primer dato al ancla",
          periodo.ventana("Todo", ancla, minimo=pd.Timestamp("2024-03-02")),
          (pd.Timestamp("2024-03-02"), ancla))

    # ── recortar() sobre un df real ──────────────────────────────────────
    df = pd.DataFrame({
        "f": pd.to_datetime(["2024-01-15", "2025-06-30", "2026-03-01",
                             "2026-08-15"]),
        "v": [1, 2, 3, 4],
    })
    check("heredar devuelve el df intacto",
          len(periodo.recortar(df, "f", periodo.HEREDA)), 4)
    # El ancla sale del propio df (2026-08-15), NO de la fecha de hoy: con
    # `hoy` este mismo assert cambiaría de resultado cada día que pasa.
    check("12m deja solo lo del último año", 
          list(periodo.recortar(df, "f", "12m")["v"]), [3, 4])
    check("Todo no descarta nada", len(periodo.recortar(df, "f", "Todo")), 4)
    check("columna inexistente no revienta",
          len(periodo.recortar(df, "no_existe", "12m")), 4)
    check("df vacío no revienta",
          len(periodo.recortar(df.iloc[:0], "f", "12m")), 0)

    # Una fecha CON HORA no puede caerse del borde superior de su ventana.
    df_h = pd.DataFrame({"f": pd.to_datetime(["2026-08-15 23:30:00"]),
                         "v": [1]})
    check("la última fecha con hora entra en la ventana",
          len(periodo.recortar(df_h, "f", "12m", ancla=ancla)), 1)

    # La etiqueta del título es la MISMA opción en prosa: si divergen, el
    # título miente sobre el control que tiene encima.
    check("etiqueta de heredar es vacía", periodo.etiqueta(periodo.HEREDA), "")
    check("etiqueta de 12m", periodo.etiqueta("12m"), "últimos 12 meses")
    check("etiqueta de Todo", periodo.etiqueta("Todo"), "todo el histórico")

    return fallos


def _pruebas_escala_tiempo():
    """estado_rango.py — la escala de tiempo estilo tabla dinámica.

    Tres asserts valen más que los otros y son la razón de esta tanda:

    1. EL EXTREMO DERECHO SE EXPANDE. Las paradas del riel son fechas de
       ARRANQUE de período, así que "hasta agosto" tiene que terminar el 31
       y no el 1. Si se cuela el 1, el filtro pierde 30 días de datos y el
       total sale bajo sin que nada avise — el bug clásico de un filtro por
       mes, y el que este contrato existe para atrapar.

    2. EL RECORTE A BOUNDS. En escala de Años, "2026" pide hasta el 31-dic,
       pero los datos terminan en agosto. Sin recortar, el rango declara
       cuatro meses que no existen y el eje de cualquier evolución dibuja el
       vacío. Espeja lo que ya hace `atajos_rango`.

    3. LA VUELTA ES ESTABLE. `escala_desde_rango` siembra el riel desde el
       rango canónico en CADA render; si no fuera idempotente, un rango que
       ya nació de la escala se ensancharía solo en cada rerun.
    """
    import datetime

    from estado_rango import (ESCALAS, escala_a_rango, escala_desde_rango,
                              escala_periodos)

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    escala · {nombre}")
        else:
            fallos += 1
            print(f"FALLA escala · {nombre}: got={got!r} exp={exp!r}")

    # Bounds deliberadamente SUCIOS: no arrancan un día 1 ni terminan a fin
    # de mes/año. Con bounds redondos los dos bugs de arriba pasan
    # desapercibidos.
    b = (datetime.date(2024, 3, 17), datetime.date(2026, 8, 25))
    meses = escala_periodos("Meses", b)
    anios = escala_periodos("Años", b)

    check("las escalas son tres", ESCALAS, ("Días", "Meses", "Años"))

    # ── Las paradas ────────────────────────────────────────────────────
    check("meses: una parada por mes, mar-24 a ago-26", len(meses), 30)
    check("meses: la parada es el día 1", meses[0], datetime.date(2024, 3, 1))
    check("meses: cruza el fin de año sin saltearse enero",
          meses[9], datetime.date(2024, 12, 1))
    check("meses: la última es el mes del borde",
          meses[-1], datetime.date(2026, 8, 1))
    check("años: una parada por año presente",
          anios, [datetime.date(y, 1, 1) for y in (2024, 2025, 2026)])
    check("días: una parada por día, ambos bordes incluidos",
          len(escala_periodos("Días", b)), 892)
    check("bounds sin fecha no dan paradas",
          escala_periodos("Meses", (None, None)), [])
    check("bounds invertidos no dan paradas",
          escala_periodos("Meses", (b[1], b[0])), [])

    # ── (1) el extremo derecho se EXPANDE ──────────────────────────────
    check("un mes suelto va del 1 a fin de mes",
          escala_a_rango("Meses", datetime.date(2025, 4, 1),
                         datetime.date(2025, 4, 1)),
          (datetime.date(2025, 4, 1), datetime.date(2025, 4, 30)))
    check("febrero bisiesto termina el 29",
          escala_a_rango("Meses", datetime.date(2024, 2, 1),
                         datetime.date(2024, 2, 1))[1],
          datetime.date(2024, 2, 29))
    check("diciembre no se pasa al año siguiente",
          escala_a_rango("Meses", datetime.date(2025, 12, 1),
                         datetime.date(2025, 12, 1))[1],
          datetime.date(2025, 12, 31))
    check("un año suelto va del 1-ene al 31-dic",
          escala_a_rango("Años", datetime.date(2025, 1, 1),
                         datetime.date(2025, 1, 1)),
          (datetime.date(2025, 1, 1), datetime.date(2025, 12, 31)))
    check("en días el extremo es el día mismo",
          escala_a_rango("Días", datetime.date(2026, 8, 5),
                         datetime.date(2026, 8, 23)),
          (datetime.date(2026, 8, 5), datetime.date(2026, 8, 23)))
    check("tiradores cruzados se enderezan",
          escala_a_rango("Días", datetime.date(2026, 8, 23),
                         datetime.date(2026, 8, 5)),
          (datetime.date(2026, 8, 5), datetime.date(2026, 8, 23)))

    # ── (2) el recorte a bounds ────────────────────────────────────────
    check("el año del borde no promete meses sin datos",
          escala_a_rango("Años", anios[-1], anios[-1], b),
          (datetime.date(2026, 1, 1), datetime.date(2026, 8, 25)))
    check("el primer año no arranca antes del primer dato",
          escala_a_rango("Años", anios[0], anios[0], b),
          (datetime.date(2024, 3, 17), datetime.date(2024, 12, 31)))
    check("de punta a punta da exactamente los bounds",
          escala_a_rango("Meses", meses[0], meses[-1], b), b)

    # ── (3) la vuelta ──────────────────────────────────────────────────
    r = (datetime.date(2026, 8, 5), datetime.date(2026, 8, 23))
    check("un rango dentro de un mes cae en ese mes",
          escala_desde_rango("Meses", r, b),
          (datetime.date(2026, 8, 1), datetime.date(2026, 8, 1)))
    check("un rango a caballo toma los dos meses",
          escala_desde_rango("Meses",
                             (datetime.date(2025, 6, 20),
                              datetime.date(2025, 7, 3)), b),
          (datetime.date(2025, 6, 1), datetime.date(2025, 7, 1)))
    check("sin rango sembrado, el riel abre entero",
          escala_desde_rango("Meses", None, b), (meses[0], meses[-1]))
    check("un rango anterior a los datos se apoya en el borde",
          escala_desde_rango("Meses", (datetime.date(2020, 1, 1),
                                       datetime.date(2020, 2, 1)), b),
          (meses[0], meses[0]))

    ida = escala_a_rango("Meses", *escala_desde_rango("Meses", r, b), b)
    vuelta = escala_a_rango("Meses", *escala_desde_rango("Meses", ida, b), b)
    check("re-sembrar un rango que ya salió de la escala no lo mueve",
          vuelta, ida)

    return fallos


def _pruebas_anomalias():
    """graficos/ajuste/_anomalias.py — "¿es raro PARA ESTE producto?".

    Lo que estas pruebas fijan no es aritmética, es el CRITERIO: el mismo
    18% de ajuste tiene que ser una alarma en un producto que siempre se
    mueve ±2% y ruido en uno que se mueve ±30%.

    Probado en negativo cambiando mediana/MAD por media/desviación: saltan
    los asserts de `pct_mediana` (1.0 → 0.4) y de `z` (11.5 → 10.8). OJO:
    los veredictos NO cambian en estos casos concretos, así que son esos
    dos asserts numéricos —y no los de veredicto— los que sostienen el
    criterio. Si se tocan, hay que sustituirlos por otro caso que sí
    distinga, no borrarlos.
    """
    from graficos.ajuste._anomalias import perfil_por_producto

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    anomalias · {nombre}")
        else:
            fallos += 1
            print(f"FALLA anomalias · {nombre}: got={got!r} exp={exp!r}")

    def _caso(nombre, ajustes):
        # stock fijo 100 -> el ajuste ES el porcentaje, para que los
        # números del test se lean sin hacer cuentas.
        return pd.DataFrame({
            "PRODUCTO": [nombre] * len(ajustes),
            "FECHA": pd.date_range("2026-01-01", periods=len(ajustes), freq="MS"),
            "AJUSTE": ajustes,
            "STOCK": [100.0] * len(ajustes),
        })

    df = pd.concat([
        _caso("estable",  [2, -1, 2, -2, 1, 18]),   # ±2 y de pronto 18
        _caso("revuelto", [25, -30, 28, -22, 31, 18]),  # el MISMO 18
        _caso("cero",     [0, 0, 0, 0, 0, 5]),      # dispersión nula
        _caso("nuevo",    [1, 2, 40]),              # sin historia
    ], ignore_index=True)
    out = perfil_por_producto(df, "PRODUCTO", "FECHA", "AJUSTE", "STOCK")
    v = dict(zip(out["producto"], out["veredicto"]))

    check("el mismo 18% es anómalo para el estable", v["estable"], "anomalo")
    check("...y normal para el revuelto", v["revuelto"], "normal")
    check("dispersión 0 → nuevo_patron, no z infinito", v["cero"], "nuevo_patron")
    check("pocos cortes → no se inventa veredicto", v["nuevo"], "sin_historico")

    # El corte actual NO entra en su propia mediana (si no, se auto-normaliza).
    fila = out[out["producto"] == "estable"].iloc[0]
    check("mediana excluye el corte juzgado", float(fila["pct_mediana"]), 1.0)
    check("z se calcula sobre el histórico", round(float(fila["z"]), 1), 11.5)
    check("lo más raro va primero", out["producto"].iloc[0], "estable")

    # Varias filas del mismo producto y corte (varias áreas) se AGREGAN
    # antes de sacar el %: sumar ajuste y stock no es promediar porcentajes.
    dos_areas = pd.DataFrame({
        "PRODUCTO": ["x"] * 2,
        "FECHA": [pd.Timestamp("2026-01-01")] * 2,
        "AJUSTE": [10.0, 10.0],
        "STOCK": [100.0, 300.0],
    })
    o2 = perfil_por_producto(dos_areas, "PRODUCTO", "FECHA", "AJUSTE",
                             "STOCK", min_cortes=1)
    # 20/400 = 5%, no el promedio de 10% y 3.33%
    check("agrega por corte antes del %",
          round(float(o2["pct_actual"].iloc[0]), 2), 5.0)

    # ── "Agotado" es atributo, NO veredicto ────────────────────────────
    # El caso que motivó el cambio de diseño: dos productos que hoy se
    # quedan en 0 (declarado=0), pero uno se agota SIEMPRE y el otro
    # nunca lo había hecho. Deben salir con veredictos OPUESTOS, no en
    # el mismo saco. Medido sobre el parquet real: de 1.146 agotados,
    # 463 son normales para sí mismos y 209 anómalos.
    def _con_declarado(nombre, cierres, declarados):
        return pd.DataFrame({
            "PRODUCTO": [nombre] * len(cierres),
            "FECHA": pd.date_range("2026-01-01", periods=len(cierres), freq="MS"),
            "STOCK": cierres,
            "DECL": declarados,
            "AJUSTE": [d - c for c, d in zip(cierres, declarados)],
        })

    df_ag = pd.concat([
        # se agota en TODOS los cortes -> que hoy se agote no es noticia
        _con_declarado("siempre se agota", [10, 12, 8, 11, 9], [0, 0, 0, 0, 0]),
        # nunca se agotó (conteo casi exacto) y hoy sí
        _con_declarado("nunca se agotó",   [10, 12, 8, 11, 9], [10, 12, 8, 11, 0]),
    ], ignore_index=True)
    o3 = perfil_por_producto(df_ag, "PRODUCTO", "FECHA", "AJUSTE", "STOCK",
                             col_declarado="DECL")
    r3 = {p: (v, a) for p, v, a in
          zip(o3["producto"], o3["veredicto"], o3["agotado"])}
    check("los dos constan como agotados",
          (r3["siempre se agota"][1], r3["nunca se agotó"][1]), (True, True))
    check("el que se agota siempre → normal",
          r3["siempre se agota"][0], "normal")
    check("el que nunca se agotó → NO normal",
          r3["nunca se agotó"][0] != "normal", True)
    # Sin col_declarado, la columna existe igual y sale toda en False.
    o4 = perfil_por_producto(df_ag, "PRODUCTO", "FECHA", "AJUSTE", "STOCK")
    check("sin col_declarado, agotado=False", bool(o4["agotado"].any()), False)

    # Sin columnas o sin datos utiles: devuelve vacio, no revienta.
    check("columnas ausentes → df vacío",
          len(perfil_por_producto(df, "NO_EXISTE", "FECHA", "AJUSTE", "STOCK")), 0)
    sin_stock = _caso("s", [1, 2, 3, 4])
    sin_stock["STOCK"] = 0.0
    check("stock 0 se descarta (no inventa %)",
          len(perfil_por_producto(sin_stock, "PRODUCTO", "FECHA", "AJUSTE", "STOCK")), 0)

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

    # Placeholders del inspector: el blob de JS y el dict de sustituciones
    # tienen que cuadrar EN AMBAS DIRECCIONES. Uno que nadie sustituya rompe
    # el JSON.parse del JS entero; uno que sobre es trabajo que se calcula
    # para tirar (le pasó a __MAPA_PREFIJOS__ hasta 2026-08-08, ver
    # arquitectura.md #56). Nada avisaba: no es error de sintaxis ni de lint.
    from inyecciones.inspector import _placeholders_descuadrados
    _sobran_blob, _sobran_dict = _placeholders_descuadrados()
    check("inspector: ningún placeholder sin sustituir", _sobran_blob == set(),
          f"en el blob pero no en el dict: {_sobran_blob}")
    check("inspector: ninguna sustitución sin placeholder", _sobran_dict == set(),
          f"en el dict pero no en el blob: {_sobran_dict}")

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


def _pruebas_presupuesto_vertical():
    """El contrato del PRESUPUESTO VERTICAL (graficos/alturas.py).

    Existe porque el bug que arregló ese módulo es invisible desde el código:
    un `alto=560` se lee perfectamente razonable, y solo midiendo en el
    navegador se descubre que la tarjeta no entra en la pantalla. Medido el
    2026-08-13, antes de la migración: 19 de 24 vistas obligaban a scrollear
    en un laptop de 1366x768.

    Tres cosas que se pueden romper en silencio y que aquí fallan ruidosas:

      1. Que alguien vuelva a escribir un alto literal en `graficos/`. Es la
         regla «nunca un alto suelto», gemela de «nunca un #hex suelto».
      2. Que el cromo de `estilos/` y el de `alturas.py` se desincronicen:
         son la misma geometría contada dos veces (CSS para el marco de la
         tarjeta, Python para el alto de las figuras) y nada las une salvo
         esta prueba.
      3. Que un rol crezca hasta no entrar en el presupuesto.
    """
    import pathlib
    import re

    from graficos import alturas

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    presupuesto · {nombre}")
        else:
            fallos += 1
            print(f"FALLA presupuesto · {nombre}{': ' + detalle if detalle else ''}")

    # ── 1) Ningún alto literal suelto en graficos/ ──────────────────────
    # `_css_proveedor.py` queda fuera: es un blob de CSS, no altos de
    # figuras (ahí `height` es una propiedad, no un kwarg de Python).
    #
    # Mismo escape hatch que la guarda 2, y por el mismo motivo: hay altos
    # que NO son el de una figura y por lo tanto no salen de `alturas.py`.
    # Marcar la línea con `# alto-fijo-justificado: <por qué>`. Hoy lo usa
    # el iframe de alto 0 del gancho de scroll (`base.py::_render_rail`):
    # no dibuja nada, sólo corre el JS que intercambia los dos rails.
    raiz = pathlib.Path(__file__).parent / "graficos"
    culpables = []
    for py in sorted(raiz.rglob("*.py")):
        if py.name in ("alturas.py", "_css_proveedor.py"):
            continue
        for i, linea in enumerate(py.read_text(encoding="utf-8").split("\n"), 1):
            if linea.lstrip().startswith("#"):
                continue
            if re.search(r"\b(alto|height)=\d", linea) \
                    and "alto-fijo-justificado" not in linea:
                culpables.append(f"{py.relative_to(raiz.parent)}:{i}")
    check("ningún alto literal en graficos/ (usar alturas.py)",
          not culpables, ", ".join(culpables[:6]))

    # ── 1b) Ningún CONTENEDOR dimensionado desde Python ─────────────────
    # Gemelo del anterior, y nació de un bug real (2026-08-14): el panel del
    # drill de Ventas › Por hora se dibujaba con
    # `st.container(height=alturas.reparto(...))`, o sea restando contra
    # `VIEWPORT_OBJETIVO` — una pantalla SUPUESTA. En el laptop de 1366x768
    # daba bien; en un monitor de 1000px de alto el panel se quedaba en 150
    # con 350 libres debajo. No lo cazó nada: no es un error, es una cuenta
    # correcta contra el número equivocado.
    #
    # La regla: Python emite alturas de CONTENIDO (filas × px); las RESTAS
    # las hace el CSS, que conoce la ventana real, con lo que Python le
    # publica vía `graficos.base.publicar_alto_css()`.
    #
    # Escape hatch explícito para el caso legítimo (un contenedor cuyo alto
    # NO sale de restarle nada a la pantalla): marcar la línea con
    # `# alto-fijo-justificado: <por qué>`.
    culpables_cont = []
    for py in sorted(raiz.rglob("*.py")):
        for i, linea in enumerate(py.read_text(encoding="utf-8").split("\n"), 1):
            # Los COMENTARIOS quedan fuera: media docena de ellos explican
            # justamente esta regla citando la llamada prohibida, y una guarda
            # que se dispara con su propia documentación es una guarda que
            # alguien termina desactivando.
            if linea.lstrip().startswith("#"):
                continue
            if "st.container(" in linea and "height=" in linea \
                    and "alto-fijo-justificado" not in linea:
                culpables_cont.append(f"{py.relative_to(raiz.parent)}:{i}")
    check("ningún contenedor dimensionado desde Python "
          "(la resta la hace el CSS)",
          not culpables_cont, ", ".join(culpables_cont[:6]))

    # ── 2) El cromo de CSS y el de Python cuentan lo mismo ──────────────
    css = (pathlib.Path(__file__).parent / "estilos" / "_00_base.py").read_text(
        encoding="utf-8")

    def _var(nombre):
        m = re.search(rf"--{nombre}:\s*(\d+)px", css)
        return int(m.group(1)) if m else None

    cab = _var("cab-offset-contenido")
    franja = _var("franja-inf-reserva")
    margen = _var("margen-tarjeta")
    check("las variables de cromo existen en estilos/_00_base.py",
          None not in (cab, franja, margen),
          f"cab={cab} franja={franja} margen={margen}")
    if None not in (cab, franja, margen):
        suma_css = cab + franja + margen * 2
        check("el cromo de CSS coincide con alturas.CROMO",
              suma_css == alturas.CROMO,
              f"CSS suma {suma_css}px y alturas.CROMO vale {alturas.CROMO}px")

    # ── 3) Los roles entran en el presupuesto ───────────────────────────
    check("PROTAGONISTA + padding entra en el presupuesto",
          alturas.cabe(alturas.PROTAGONISTA + 32),
          f"{alturas.PROTAGONISTA} + 32 > {alturas.PRESUPUESTO}")
    check("los roles están ordenados (MINI ≤ APOYO ≤ PROTAGONISTA)",
          alturas.MINI <= alturas.APOYO <= alturas.PROTAGONISTA)
    check("por_filas respeta el techo de su rol",
          alturas.por_filas(500) == alturas.PROTAGONISTA
          and alturas.por_filas(500, rol=alturas.MINI) == alturas.MINI)
    check("por_filas enmarcada no supera el techo de scroll interno",
          alturas.por_filas(9999, enmarcada=True) == alturas._TOPE_ENMARCADA)

    # ── 4) Los anchos de los rails tienen UN dueño ──────────────────────
    # Gemela de la regla del cromo, y por el mismo motivo: hasta el
    # 2026-08-15 el ancho de los rails vivía escrito a mano en seis sitios
    # que se derivaban entre sí (el margen de la app, el `left` de la franja
    # inferior, el `padding-right` del contenido, los `right` de la fecha,
    # los chips y los atajos). Cambiar uno sin los otros dejaba la franja
    # superior flotando sobre el vacío — es la regla #17.
    #
    # Ahora se declaran en _00_base.py y SOLO las redefine el pestillo
    # (_25_rails_pestillo.py). Si aparecen en un tercer sitio, el plegado
    # deja de funcionar en esa esquina y nadie se entera hasta verlo.
    _duenos = {"_00_base.py", "_25_rails_pestillo.py"}
    intrusos = []
    for py in sorted(pathlib.Path(__file__).parent.rglob("*.py")):
        if py.name in _duenos or py.name == pathlib.Path(__file__).name:
            continue
        for i, linea in enumerate(py.read_text(encoding="utf-8").split("\n"), 1):
            if re.search(r"--rail-(izq|der)-w\s*:|--rail-der-res\s*:", linea):
                intrusos.append(f"{py.name}:{i}")
    check("los anchos de rail solo los declaran _00_base y el pestillo",
          not intrusos, ", ".join(intrusos[:6]))

    # El ancho reservado a la derecha se DERIVA del ancho del rail; si
    # alguien lo vuelve a fijar en px, plegar el rail derecho no ensancha
    # la tarjeta (el rail se encoge y el hueco se queda igual de grande).
    check("--rail-der-res se deriva de --rail-der-w, no es un px suelto",
          re.search(r"--rail-der-res:\s*calc\([^)]*--rail-der-w", css) is not None)

    return fallos


def _pruebas_grilla_horizontal():
    """El contrato de la GRILLA (graficos/compras/_comun.py).

    Gemela horizontal de `_pruebas_presupuesto_vertical`, y por el mismo
    motivo: el bug es invisible desde el código. El drill de Proveedor partía
    su fila de arriba con `st.columns([1.6, 1])` y la de abajo con
    `st.columns(2)`. Los dos números son correctos leídos por separado; juntos
    corren el eje de la página ~200px a media altura y la vista deja de
    leerse como una grilla.

    Lo que se puede romper en silencio y aquí falla ruidoso:

      1. Que una fila del drill vuelva a partirse con un literal en vez de
         `COLUMNAS_DRILL`. El escape hatch para las subdivisiones DENTRO de
         una tarjeta (el chart y sus KPIs, una botonera) es un comentario
         `# columnas-internas: <por qué>` en la línea o justo encima.
      2. Que alguien redeclare la constante en otro módulo, que es cómo
         empezó este bug la primera vez.

    La guarda cubre `proveedor.py` (donde se arregló) y `producto.py`. El
    segundo entró el 2026-08-24, al fusionarlos en una sola página continua:
    ahí los dos drills dejaron de alternarse y pasaron a verse APILADOS, así
    que sus filas ya no se comparan de memoria entre dos pantallas sino a
    simple vista, una debajo de la otra. Los números de `producto.py` ya
    coincidían con la constante (1.6/1, gap small) — lo que faltaba era que
    no fueran una copia capaz de desincronizarse.

    PENDIENTE: los drills que siguen fuera usan literales y entre ellos hay
    ejes distintos (1.6/1 en documentos_sunat.py, 1.7/1 en __init__.py, 1/1
    en volatilidad.py), así que el esqueleto todavía salta al navegar por el
    rail. Al unificar más vistas, ampliar `_ARCHIVOS` a todo
    `graficos/compras`.
    """
    import pathlib
    import re

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    grilla · {nombre}")
        else:
            fallos += 1
            print(f"FALLA grilla · {nombre}{': ' + detalle if detalle else ''}")

    raiz = pathlib.Path(__file__).parent
    _ARCHIVOS = [raiz / "graficos" / "compras" / "proveedor.py",
                 raiz / "graficos" / "compras" / "producto.py"]

    # ── 1) Ninguna fila partida con un literal ──────────────────────────
    culpables = []
    for py in _ARCHIVOS:
        lineas = py.read_text(encoding="utf-8").split("\n")
        for i, linea in enumerate(lineas, 1):
            if "st.columns(" not in linea or linea.lstrip().startswith("#"):
                continue
            if "COLUMNAS_DRILL" in linea:
                continue
            # La marca vale en la propia línea o en las 3 de encima: una
            # llamada con la marca al final no siempre entra en el ancho.
            ventana = "\n".join(lineas[max(0, i - 4):i])
            if "columnas-internas:" in ventana:
                continue
            culpables.append(f"{py.relative_to(raiz)}:{i}")
    check("ninguna fila de un drill partida con un literal "
          "(usar COLUMNAS_DRILL, o marcar `# columnas-internas:`)",
          not culpables, ", ".join(culpables[:6]))

    # ── 2) Las dos filas del drill de Proveedor usan la constante ───────
    # Positiva, no negativa: sin esto, borrar las dos llamadas dejaría la
    # guarda #1 en verde.
    prov = (raiz / "graficos" / "compras" / "proveedor.py").read_text(
        encoding="utf-8")
    n_filas = len(re.findall(r"st\.columns\(COLUMNAS_DRILL", prov))
    check("las 2 filas del drill de Proveedor parten con COLUMNAS_DRILL",
          n_filas == 2, f"se encontraron {n_filas}")

    # ── 3) La constante tiene UN dueño ──────────────────────────────────
    intrusos = []
    for py in sorted(raiz.rglob("*.py")):
        if py.name in ("_comun.py", pathlib.Path(__file__).name):
            continue
        for i, linea in enumerate(py.read_text(encoding="utf-8").split("\n"), 1):
            if re.match(r"\s*(COLUMNAS_DRILL|GAP_DRILL)\s*=", linea):
                intrusos.append(f"{py.relative_to(raiz)}:{i}")
    check("COLUMNAS_DRILL/GAP_DRILL solo los declara compras/_comun.py",
          not intrusos, ", ".join(intrusos[:6]))

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

    # ── Constructores compartidos de Receta Base / Receta Venta ─────────
    # graficos/recetas_comun.py: una sola copia de cada gráfico para los
    # dos dashboards (ver arquitectura.md § Unificación Recetas). Kwargs
    # solo-nombrados → se envuelven en lambdas de 0 args para reusar el
    # mismo bucle `fn(*args)` de arriba.
    from graficos import recetas_comun as _rc
    df_rec = _df_recetas()
    links_panorama = pd.DataFrame({
        "producto_n":   ["Prod 1", "Prod 1", "Otros insumos", "Prod 2"],
        "contenedor_n": ["A", "B", "A", "Otros"],
        "valor":        [100.0, 40.0, 15.0, 60.0],
    })
    pruebas += [
        ("recetas_comun · sankey contenedor", lambda: _rc._sankey_contenedor(
            df_rec, "CONTENEDOR", "ITEM", "VALOR", "A", True,
            card_key="test_sankey"), ()),
        ("recetas_comun · composicion contenedor", lambda: _rc._composicion_contenedor(
            df_rec, "CONTENEDOR", "ITEM", "VALOR", "C", True,
            card_key="test_dona"), ()),
        ("recetas_comun · ranking contenedores", lambda: _rc._ranking_contenedores(
            df_rec, "CONTENEDOR", "VALOR", True,
            key_topn="test_topn", card_key="test_ranking",
            titulo_card="Ranking de prueba"), ()),
        ("recetas_comun · items clave", lambda: _rc._items_clave(
            df_rec, "CONTENEDOR", "ITEM", "VALOR", True,
            card_key="test_items", titulo_card="Ítems de prueba",
            etiqueta_item="Ítem", etiqueta_contenedor_plural="contenedores",
            expander_titulo="Tabla de prueba"), ()),
        ("recetas_comun · fig panorama sankey", lambda: _rc._fig_panorama_sankey(
            links_panorama, True), ()),
    ]

    # ── Mapa por hora (Ventas › Por hora) ───────────────────────────────
    # Dos paneles con distinta cantidad de columnas y una marca puesta: es la
    # combinación que ejercita los offsets del eje X, el hueco entre paneles,
    # el customdata de la capa de selección y las shapes de las marcas.
    from graficos import ventas_horario as _vh_fig
    _celdas_demo = pd.DataFrame({
        "col":    [0, 1, 4, 6],
        "hora":   [12, 19, 19, 21],
        "venta":  [100.0, 400.0, 250.0, 80.0],
        "cant":   [3.0, 9.0, 6.0, 2.0],
        "desc":   [0.0, 40.0, 10.0, 0.0],
        "pax":    [2.0, 8.0, 5.0, 1.0],
        "ticket": [50.0, 50.0, 50.0, 80.0],
    })
    pruebas += [
        ("ventas_horario · mapa (2 paneles + marca)",
         lambda: _vh_fig._fig_mapa(
             [_celdas_demo, _celdas_demo], [(2026, 32), (2026, 33)], "Semana",
             "venta", [{"sel": 1, "c0": 4, "c1": 6, "h0": 19, "h1": 21}],
             [12, 19, 21]), ()),
        ("ventas_horario · mapa (granularidad Mes)",
         lambda: _vh_fig._fig_mapa(
             [_celdas_demo], [(2026, 2)], "Mes", "ticket", [], [12, 19, 21]), ()),
        ("ventas_horario · mapa sin datos",
         lambda: _vh_fig._fig_mapa([None], [2026], "Año", "venta", [], [12]), ()),
    ]


    # ── Vs año pasado (Compras): serie mensual y puente precio/cantidad ──
    # El waterfall entra con un efecto de cada signo a propósito: es la
    # combinación donde `increasing`/`decreasing` tienen que pintar los dos
    # colores del semáforo invertido (subir un costo es malo).
    from graficos.compras import vs_ano_pasado as _vap_fig
    _g_vap = pd.DataFrame({
        "prod": ["A", "B", "A", "B"],
        "grupo": ["F1", "F2", "F1", "F2"],
        "mes": [pd.Period("2026-07", "M"), pd.Period("2026-07", "M"),
                pd.Period("2026-08", "M"), pd.Period("2026-08", "M")],
        "valor": [100.0, 200.0, 150.0, 0.0],
        "cant": [10.0, 20.0, 12.0, 0.0],
        "valor_aa": [90.0, 180.0, 120.0, 60.0],
        "cant_aa": [9.0, 18.0, 15.0, 6.0],
    })
    pruebas += [
        ("compras vs año pasado · serie (Valor, mes parcial)",
         lambda: _vap_fig._fig_serie(_g_vap, "Valor",
                                     (pd.Period("2026-08", "M"), 21), "t"), ()),
        ("compras vs año pasado · serie (Cantidad)",
         lambda: _vap_fig._fig_serie(_g_vap, "Cantidad", None, "t"), ()),
        ("compras vs año pasado · serie (Precio, ratio con cero)",
         lambda: _vap_fig._fig_serie(_g_vap, "Precio", None, "t"), ()),
        ("compras vs año pasado · puente precio/cantidad",
         lambda: _vap_fig._fig_puente(250.0, 450.0, 60.0, -260.0), ()),
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

    # ── Estado del rango y resolución de columnas (lógica pura) ─────────
    fallos += _pruebas_estado_y_utils()

    # ── Ventana propia de una tarjeta (graficos/periodo.py) ─────────────
    fallos += _pruebas_periodo_por_vista()

    # ── Deteccion de anomalias en Ajuste ────────────────────────────────
    # ── Escala de tiempo estilo tabla dinamica (estado_rango.py) ────────
    fallos += _pruebas_escala_tiempo()

    fallos += _pruebas_anomalias()

    # ── Contratos entre app.py y los dashboards (firma del dispatcher) ──
    fallos += _pruebas_contratos()

    # ── Presupuesto vertical: que las tarjetas sigan entrando en pantalla ─
    fallos += _pruebas_presupuesto_vertical()

    # ── Grilla horizontal: que todas las filas partan en el mismo sitio ──
    fallos += _pruebas_grilla_horizontal()

    print()
    if fallos:
        print(f"❌ {fallos} fallo(s) — revisar las líneas FALLA de arriba")
        sys.exit(1)
    print("✅ Todo OK (constructores de figuras + funciones puras)")


if __name__ == "__main__":
    main()
