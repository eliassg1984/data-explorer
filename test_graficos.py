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
    from estado_rango import _fin_de_mes, atajos_rango, clave_rango

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
    # Un año presente en la data se ofrece como chip propio.
    check("atajos incluye el año de la data", "y2023" in dict(
        (c, r) for c, _, r in atajos_rango(
            hoy, (datetime.date(2023, 1, 1), datetime.date(2024, 5, 31)))), True)

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

    # ── Estado del rango y resolución de columnas (lógica pura) ─────────
    fallos += _pruebas_estado_y_utils()

    # ── Deteccion de anomalias en Ajuste ────────────────────────────────
    fallos += _pruebas_anomalias()

    # ── Contratos entre app.py y los dashboards (firma del dispatcher) ──
    fallos += _pruebas_contratos()

    print()
    if fallos:
        print(f"❌ {fallos} fallo(s) — revisar las líneas FALLA de arriba")
        sys.exit(1)
    print("✅ Todo OK (constructores de figuras + funciones puras)")


if __name__ == "__main__":
    main()
