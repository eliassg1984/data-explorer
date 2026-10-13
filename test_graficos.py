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


def _recetabase_rb_demo():
    """recetabase.parquet de mentira para «Costo recetas base» (regla #576),
    con los nombres de columna del Sheet: una salsa que lleva un fondo (300 g
    por kilo), el fondo, una receta INACTIVA que igual se vende y una activa
    que nadie usa."""
    filas = [
        # prod, nombre, unid, costo, act, factor, area, ins, cant, factor ins
        ("0000100", "(Rs) Salsa de lomo", "KILOS", 20.0, "RB.ACTIV", 1000.0, "COCINA",
         "0000200", 300.0, 1000.0),
        ("0000100", "(Rs) Salsa de lomo", "KILOS", 20.0, "RB.ACTIV", 1000.0, "COCINA",
         "0000900", 50.0, 1000.0),
        ("0000200", "(Rs) Fondo oscuro", "KILOS", 5.0, "RB.ACTIV", 1000.0, "PRODUCCION",
         "0000901", 1000.0, 1000.0),
        ("0000300", "(Rs) Postre viejo", "UND", 3.0, "RB.INACT", 1.0, "COCINA",
         "0000902", 1.0, 1.0),
        ("0000400", "(Rs) Batch de barra", "LITROS", 8.0, "RB.ACTIV", 1000.0, "BARRA",
         "0000903", 900.0, 1000.0),
    ]
    return pd.DataFrame(filas, columns=[
        "COD PROD RB", "RB NOMBRE", "RB UNID", "RB COSTO", "RB ACT", "RB FACTOR",
        "RB AREA PROD", "COD INS RB", "CANT", "FACTOR INS"])


def _ordenes_rb_demo():
    """ordenesproduccion.parquet de mentira (regla #575/#576): la salsa, diez
    órdenes a ~S/ 20 el kilo, una a S/ 3.000 (una cantidad mal cargada) y la
    última a S/ 0; el fondo, cinco a S/ 5 y cinco a S/ 25 —un CAMBIO de
    régimen, que no es atípico— y una generada, que no suma."""
    filas = []

    def _orden(i, cod, nombre, fecha, cant, punit, estado="PROCESADO", unid="KILOS"):
        filas.append({"COD ORDEN PRODUCCION": f"26{i:08d}", "FECHA REGISTRO": pd.Timestamp(fecha),
                      "NOMBRE ESTADO": estado, "AREA": "COCINA", "COD PRODUCTO": cod,
                      "NOMBRE PRODUCTO": nombre, "CANTIDAD": cant, "UNIDAD": unid,
                      "PRECIO UNIT": punit, "VALOR ITEM": cant * punit})

    for k in range(10):
        _orden(k, "0000100", "(Rs) Salsa de lomo", f"2026-{(k % 9) + 1:02d}-10 10:00",
               2.0, 20.0 + k * 0.1)
    _orden(20, "0000100", "(Rs) Salsa de lomo", "2026-09-12 10:00", 0.01, 3000.0)
    _orden(21, "0000100", "(Rs) Salsa de lomo", "2026-09-20 10:00", 1.0, 0.0)
    for k in range(10):
        _orden(30 + k, "0000200", "(Rs) Fondo oscuro", f"2026-0{1 + k // 2}-0{1 + k % 2} 09:00",
               4.0, 5.0 if k < 5 else 25.0)
    _orden(50, "0000200", "(Rs) Fondo oscuro", "2026-09-15 09:00", 99.0, 5.0, estado="GENERADO")
    return pd.DataFrame(filas)


def _fuentes_py(raiz):
    """Los `.py` PROPIOS del repo colgando de `raiz`, como `(ruta, texto)`.

    Dueño único del recorrido del fuente: cinco barridos repartidos en tres
    guardas rastrean el árbol buscando literales prohibidos, y las dos
    trampas de abajo se pagan una vez acá en vez de cinco veces sueltas.

    **Trampa 1 — los worktrees.** `Path(__file__).parent.rglob("*.py")`
    barre también `.claude/worktrees/`: copias del repo clavadas en un
    commit viejo. El 2026-08-28 eso hacía FALLAR la guarda de los anchos
    de rail citando `_25_rails_pestillo.py:38` — un fichero que `main`
    había BORRADO dos días antes (regla #216) y que sólo sobrevivía en un
    worktree en detached HEAD. Se diagnostica pésimo: la ruta del reporte
    era sólo el nombre del fichero, así que parecía un fichero del repo, y
    encima salía DUPLICADA (un renglón por worktree vivo).

    **Trampa 2 — mirar los componentes RELATIVOS, no los absolutos.** Es
    la que se llevó puesto al filtro original (`_pruebas_jscode_barato`,
    2026-08-27, `any(p.startswith(".") for p in py.parts)`): este mismo
    repo se clona a `…/.claude/worktrees/<nombre>/` para trabajar, así que
    al correr el test DESDE un worktree la ruta absoluta de todo fichero
    lleva un `.claude` adentro y el filtro descarta los 92. La guarda pasa
    en verde sin haber leído NADA — el modo de fallo peor, porque no
    avisa. `_pruebas_recorrido_fuentes` monta guardia sobre esto.
    """
    import pathlib

    raiz = pathlib.Path(raiz)
    for py in sorted(raiz.rglob("*.py")):
        if any(parte.startswith(".") for parte in py.relative_to(raiz).parts):
            continue
        try:
            yield py, py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue


def _pruebas_articulos_nuevos():
    """Las cuentas de lo que una receta NUEVA lleva y el almacén no tiene
    (`articulos_nuevos.py`, regla #597), con parquets de mentira.

    TRES COSAS QUE YA COSTARON UNA CORRECCIÓN O LA COSTARÍAN EN SILENCIO:

      · La merma propuesta cuenta cada porcionamiento UNA vez. La cabecera
        (`CANT A PORCIONAR`, `CANT MERMA`) se repite en cada corte, y
        sumarla por fila la infla tanto como cortes tenga (regla #510).
      · «Dónde se usa» sube por las recetas base: un insumo que está en una
        salsa que está en un plato SE USA en ese plato (decisión del
        usuario, 2026-10-03). Y no se cuelga con una receta que se contiene
        a sí misma.
      · Una pieza que sale de algo que se pesa gasta SU PESO, no una unidad
        de lo que entró: 220 g de lomo con 17 % de merma son 0,265 kg."""
    import pandas as pd

    import articulos_nuevos as an

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        ok = (abs(got - exp) < 1e-6) if isinstance(exp, float) and got is not None else got == exp
        if ok:
            print(f"OK    artículos nuevos · {nombre}")
        else:
            fallos += 1
            print(f"FALLA artículos nuevos · {nombre}: got={got!r} exp={exp!r}")

    # ── El porcionado por rendimiento ──
    check("pieza de algo que se pesa: peso ÷ (1 − merma)",
          an.entrada_por_unidad("KILOS", "UND", 220, 17.0), 0.220 / 0.83)
    check("a granel: una unidad de lo que entró, ÷ (1 − merma)",
          an.entrada_por_unidad("KILOS", "KILOS", 0, 20.0), 1 / 0.8)
    check("lo que entra por pieza no tiene peso que mirar",
          an.entrada_por_unidad("UND", "UND", 500, 0.0), 1.0)
    check("una merma del 100 % no deja nada", an.entrada_por_unidad("KILOS", "UND", 220, 100), None)

    # ── La merma y los cortes, de porcionamientos.parquet ──
    po = pd.DataFrame({
        "COD PORC":         ["A", "A", "B", "C"],
        "COD PROD INIC":    ["LOMO", "LOMO", "LOMO", "OTRO"],
        "FEC REGIST":       ["2026-09-01", "2026-09-01", "2026-09-20", "2026-09-20"],
        "CANT A PORCIONAR": [10.0, 10.0, 5.0, 3.0],
        "CANT TOT RESUL":   [8.0, 8.0, 4.0, 3.0],
        "CANT MERMA":       [2.0, 2.0, 1.0, 0.0],
        "COD PROD FINAL":   ["MED", "TROZ", "MED", "X"],
        "PROD FINAL RESULT": ["Medallon", "Trozos", "Medallon", "X"],
        "CANT RESULT":      [20.0, 4.0, 20.0, 3.0],
        "UNID PROD FIN":    ["UND", "KILOS", "UND", "KILOS"],
        "PESO RESULT":      [4.0, 4.0, 4.0, 3.0],
    })
    h = an.merma_y_cortes(po, "LOMO")
    check("la merma cuenta cada porcionamiento una vez (3/15, no 5/25)", h["merma_pct"], 20.0)
    check("cuántos porcionamientos", h["n"], 2)
    med = h["cortes"].set_index("cod").loc["MED"]
    # A: 10 kg × 4/8 = 5 kg para 20 medallones; B: 5 × 4/4 = 5 kg para 20.
    check("el insumo se reparte entre cortes por PESO", float(med["entrada_x_und"]), 10 / 40)
    check("el peso real de la pieza", float(med["peso_x_und"]), 8 / 40)
    check("la ventana deja afuera lo de antes",
          an.merma_y_cortes(po, "LOMO", desde="2026-09-10")["n"], 1)
    check("sin porcionamientos no hay merma que proponer",
          an.merma_y_cortes(po, "NADA")["merma_pct"], None)

    # ── La receta base ──
    check("costo por unidad = tanda ÷ lo que rinde",
          an.costo_receta_base([{"cantidad": 1000, "precio": 0.01},
                                {"cantidad": 10, "precio": 0.5}], 2)[1], 7.5)

    # ── Dónde se usa, también por recetas base ──
    rv = pd.DataFrame({
        "plato": ["P1", "P1", "P2", "P3"], "nombre": ["Asado", "Asado", "Lomo", "Combo"],
        "ins":   ["DEMI", "SAL", "SALSA", "SALSA"], "cant": [20.0, 1.0, 50.0, 10.0],
        "unid":  ["GRAMOS"] * 4, "pv": [79.0, 79.0, 79.0, 1.0], "pct": [34.5, 34.5, 38.4, 0.0]})
    rb = pd.DataFrame({
        "base": ["SALSA", "SALSA", "LOOP"], "nombre": ["(Rs) Salsa", "(Rs) Salsa", "(Rs) Loop"],
        "ins": ["DEMI", "AJI", "LOOP"], "cant": [100.0, 5.0, 1.0], "unid": ["GRAMOS"] * 3})
    idx = an.indice_usos(rv, rb)
    u = an.usos_de(idx, "DEMI")
    check("directo e indirecto, directo primero",
          [(f["receta"], f["via"]) for f in u],
          [("Asado", ""), ("Combo", "(Rs) Salsa"), ("Lomo", "(Rs) Salsa"), ("(Rs) Salsa", "")])
    check("lo indirecto dice cuánto lleva de la VÍA", u[2]["cant"], "50 g")
    check("el resumen de la tabla", an.resumen_usos(u), "3 platos · 1 base")
    check("una receta que se contiene a sí misma no cuelga (ni cuenta como uso)",
          an.resumen_usos(an.usos_de(idx, "LOOP")), "sin usos")
    check("sin usos", an.resumen_usos(an.usos_de(idx, "NADA")), "sin usos")

    # ── A quién afecta cambiar una receta base (Modificar › Receta base) ──
    # +10 soles el KILO de DEMI: el Asado lleva 20 g (+0,20); la Salsa lleva
    # 100 g por kilo (+1 el kilo) y el Lomo y el Combo llevan 50 g y 10 g de
    # Salsa (+0,05 y +0,01). Las unidades salen de GRAMOS → 1000 por kilo.
    imp = an.impacto(idx, "DEMI", 10.0)
    check("Δ directo: lo que lleva ÷ el factor × el Δ", imp["platos"]["P1"], 0.2)
    check("Δ de la receta base que lo lleva", imp["bases"]["SALSA"], 1.0)
    check("Δ por la receta base", imp["platos"]["P2"], 0.05)
    check("sin afectar lo que no lo lleva", sorted(imp["platos"]), ["P1", "P2", "P3"])

    # ── El detalle que va al PDF y al Excel (regla #607) ──
    rs = an.bloques_detalle({
        "clase": "rs", "nombre": "(Rs) Puré", "unidad_kardex": "KILOS", "costo_por_unidad": 13.26,
        "rinde": 1.0, "unidad_rinde": "KILOS", "area": "COCINA", "costo_tanda": 13.26,
        "lineas": [{"cod": "0002623", "nombre": "Camote", "unidad": "GRAMOS", "cantidad": 1300,
                    "precio": 0.0028, "tipo": "almacen"},
                   {"cod": "NUEVO-4", "nombre": "Chipotle", "unidad": "GRAMOS", "cantidad": 30,
                    "precio": 0.06, "tipo": "nuevo"}]})
    check("una receta base lleva sus insumos, y lo nuevo dice NUEVO",
          [f[0] for f in rs["filas"]], ["0002623", "NUEVO"])
    check("su pie: el costo de la tanda y por unidad",
          rs["pie"], [("Costo de 1 kilo", "S/ 13.26"), ("Costo por kilo", "S/ 13.26")])
    p_ = an.bloques_detalle({
        "clase": "p", "nombre": "(P) Medallón", "unidad_kardex": "UND", "costo_por_unidad": 0,
        "sale_de": "NUEVO-1", "sale_de_nombre": "Lomo madurado", "sale_de_unidad": "KILOS",
        "sale_de_nuevo": True, "salida": "UND", "peso_g": 220, "merma_pct": 17.0})
    check("un porcionado sin costo se marca SIN DETALLE", p_["etiqueta"],
          "Porcionado nuevo · SIN DETALLE")
    check("y si sale de algo nuevo, lo dice", p_["filas"][0], ["Sale de", "Lomo madurado (nuevo)"])
    bi = an.bloque_impacto(
        [{"receta": "Asado", "es": "plato", "via": "", "delta": 0.2, "pct_actual": 34.5,
          "pct_nuevo": 34.8, "combo": False}],
        {"unidad": "KILOS", "actual": 66.6, "por": 76.6})
    check("a quién afecta: % de hoy, el nuevo y el Δ con su signo",
          bi["filas"], [["Asado", "plato", "34.5 %", "34.8 %", "+0.20"]])

    # ── Un combo del POS como lista plana (Modificar › Combo, regla #608) ──
    # «D» y «d» son el MISMO tiempo para el POS; lo inactivo no entra; lo
    # fijo entra con su cantidad; cada opción a elegir, con 1 ÷ N.
    lineas, inactivas = an.lineas_de_combo([
        {"cod": "PAN", "nombre": "Pan", "grupo": "a", "cantidad": 0.5, "fijo": True, "activo": True},
        {"cod": "P1", "nombre": "Plato 1", "grupo": "b", "cantidad": 1, "fijo": False, "activo": True},
        {"cod": "P2", "nombre": "Plato 2", "grupo": "b", "cantidad": 1, "fijo": False, "activo": True},
        {"cod": "P3", "nombre": "Plato 3", "grupo": "b", "cantidad": 1, "fijo": False, "activo": False},
        {"cod": "D1", "nombre": "Postre 1", "grupo": "D", "cantidad": 1, "fijo": False, "activo": True},
        {"cod": "D2", "nombre": "Postre 2", "grupo": "d", "cantidad": 1, "fijo": False, "activo": True},
    ])
    check("cantidades: fijo tal cual, a elegir ÷ opciones activas, «D» = «d»",
          [(l["cod"], l["cantidad"]) for l in lineas],
          [("PAN", 0.5), ("P1", 0.5), ("P2", 0.5), ("D1", 0.5), ("D2", 0.5)])
    check("el rótulo del grupo", [l["grupo"] for l in lineas][:2],
          ["a · fijo", "b · elige 1 de 2"])
    check("las opciones inactivas quedan afuera y se cuentan", inactivas, 1)
    return fallos


def _pruebas_simulador_receta():
    """El simulador de la receta de un plato (`graficos/recetaventa.py`), el
    que abre un clic en Recetas › Carta costeada (hasta el 2026-09-28, en
    Composición; regla #556).

    LO QUE VIGILA ES UN ORDEN, y cuesta verlo: el editor empareja lo
    tecleado con el borrador **por POSICIÓN** (`editado.iloc[i]` ↔
    `lineas[i]`), así que `_receta_simulada` NO puede ordenar. Nació
    ordenando por costo —copiado de `_receta_original`, donde sí
    corresponde— y el bug es mudo: mientras nada cambie de puesto todo
    anda, y en cuanto un costo se mueve, editar una fila escribe en otro
    insumo y «Quitar» saca al vecino. Medido el 2026-09-17 con un editor
    sembrado. Ordena quien DIBUJA (`_panel_receta`, para el Sankey y la
    dona), no quien calcula.

    Lo demás son las dos cuentas del borrador: el costo es
    `Cantidad * Precio` (consecuencia, no dato), y el precio unitario se
    despeja de `Costo / Cantidad` sin reventar con cantidad 0 — que en el
    parquet existe, 19 filas, todas con costo 0."""
    from graficos.recetaventa import _precios_y_pesos, _receta_simulada

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    simulador receta · {nombre}")
        else:
            fallos += 1
            print(f"FALLA simulador receta · {nombre}: got={got!r} exp={exp!r}")

    # Tres líneas en orden de costo CRECIENTE: si la función ordenara, el
    # orden de salida sería el inverso del de entrada y se vería enseguida.
    lineas = [
        {"Insumo": "barato", "Cantidad": 1.0, "Precio": 1.0},
        {"Insumo": "medio", "Cantidad": 2.0, "Precio": 2.0},
        {"Insumo": "caro", "Cantidad": 3.0, "Precio": 10.0},
    ]
    r = _receta_simulada(lineas)
    check("el borrador NO se reordena (el editor empareja por posición)",
          list(r["Insumo"]), ["barato", "medio", "caro"])
    check("el costo es Cantidad x Precio", [round(v, 6) for v in r["Costo"]],
          [1.0, 4.0, 30.0])
    check("el % se reparte sobre el total del borrador",
          round(float(r[r["Insumo"] == "caro"]["%"].iloc[0]), 4),
          round(30.0 / 35.0 * 100, 4))

    lineas[0]["Cantidad"] = 100.0     # ahora "barato" es el más caro
    r2 = _receta_simulada(lineas)
    check("y sigue sin reordenarse cuando un costo cambia de puesto",
          list(r2["Insumo"]), ["barato", "medio", "caro"])

    cero = _precios_y_pesos(pd.DataFrame({
        "Insumo": ["sin cantidad"], "Cantidad": [0.0], "Costo": [0.0]}))
    check("cantidad 0 no revienta al despejar el precio unitario",
          float(cero["Precio"].iloc[0]), 0.0)

    vacio = _receta_simulada([])
    check("un borrador vacío devuelve las mismas columnas",
          list(vacio.columns), ["Insumo", "Cantidad", "Costo", "Precio", "%"])

    # ── El clic del Sankey ──────────────────────────────────────
    # `plotly_events` deja en `session_state` un STRING JSON, no una lista:
    # el `loads()` lo hace recién en su valor de retorno, y su default es
    # el string "[]". Un `if ev: ev[0].get(...)` —lo natural de escribir—
    # revienta con AttributeError apenas se carga la vista, porque "[]" es
    # un string NO vacío y `ev[0]` es el carácter '['. Ver regla #452.
    from graficos.recetaventa import _indice_clickeado

    check("el default \"[]\" del componente no es un clic",
          _indice_clickeado("[]"), None)
    check("un clic llega como STRING JSON",
          _indice_clickeado('[{"curveNumber":0,"pointNumber":2}]'), 2)
    check("y también se acepta ya parseado",
          _indice_clickeado([{"curveNumber": 0, "pointNumber": 2}]), 2)
    check("sin valor todavía, no hay clic", _indice_clickeado(None), None)
    check("basura no rompe la vista", _indice_clickeado("no es json"), None)
    check("un payload sin pointNumber tampoco",
          _indice_clickeado('[{"curveNumber":0}]'), None)

    return fallos



def _pruebas_placeholder_de_inyeccion():
    """`"a" + b + "c".replace(tok, val)` reemplaza SOLO en `"c"`.

    Encontrado el 2026-09-18 escribiendo `inject_hover_kpis_grid`, que arma
    su script en tres tramos —cabecera, el fragmento compartido
    `js_buscar_iframe()`, cuerpo— y cerraba con
    `.replace("__DATOS__", datos)`. Por precedencia de Python el `.replace`
    se aplica al ÚLTIMO literal y el marcador vive en el PRIMERO, así que el
    `srcdoc` salía con `var D = __DATOS__;` tal cual: JavaScript válido (un
    identificador sin declarar), sin error de sintaxis, que revienta con un
    `ReferenceError` dentro de un iframe de alto 0 cuya consola nadie mira.
    Sin traza en Python y sin nada en los logs: la inyección simplemente no
    existía. Regla #463.

    DOS GUARDAS, una por cada mitad del fallo:

      1. **La FORMA**, con `ast` sobre `inyecciones/`: un `inyectar_html(...)`
         cuyo argumento es una CONCATENACIÓN cuyo último tramo es un
         `.replace(tok, …)`, con `tok` apareciendo además en los tramos de la
         izquierda. Ése es el bug exacto. La versión correcta
         —`(a + b + c).replace(...)`— es un `Call` en la raíz y no matchea,
         así que no hay falso positivo. Se exige el token en la izquierda a
         propósito: `"a" + b.replace(...)` a secas puede ser intencional.
      2. **El RESULTADO** de las dos inyecciones de `hover_kpis.py`, que son
         las que usan el patrón: se generan con un `streamlit` de mentira y
         no puede quedar ningún `__TOKEN__` en el HTML.
    """
    import ast
    import json
    import pathlib
    import re
    import sys
    import types

    fallos = 0
    raiz = pathlib.Path(__file__).parent

    # ── 1. La forma, en todo `inyecciones/` ────────────────────────────
    sospechosos = []
    for f in sorted((raiz / "inyecciones").glob("*.py")):
        txt = f.read_text(encoding="utf-8")
        arbol = ast.parse(txt)
        for nodo in ast.walk(arbol):
            if not (isinstance(nodo, ast.Call)
                    and isinstance(nodo.func, ast.Name)
                    and nodo.func.id == "inyectar_html"
                    and nodo.args):
                continue
            arg = nodo.args[0]
            # La forma buggy: la raíz es una SUMA y su tramo derecho es un
            # `.replace(...)`. Con paréntesis la raíz sería el `Call`.
            if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)):
                continue
            der = arg.right
            if not (isinstance(der, ast.Call)
                    and isinstance(der.func, ast.Attribute)
                    and der.func.attr == "replace" and der.args):
                continue
            tok = der.args[0]
            if not (isinstance(tok, ast.Constant)
                    and isinstance(tok.value, str)):
                continue
            izq = ast.get_source_segment(txt, arg.left) or ""
            if tok.value in izq:
                sospechosos.append(
                    f"{f.relative_to(raiz)}:{nodo.lineno} — "
                    f"'{tok.value}' aparece a la izquierda del `+` y el "
                    f".replace() sólo alcanza al último tramo")
    if sospechosos:
        fallos += 1
        print("FALLA inyecciones · un .replace() que no alcanza al marcador "
              "(faltan paréntesis alrededor de la concatenación):")
        for s_ in sospechosos:
            print(f"      {s_}")
    else:
        print("OK    inyecciones · ningún .replace() suelto al final de una "
              "concatenación")

    # ── 2. El resultado de las dos de hover_kpis ───────────────────────
    guardado = sys.modules.get("streamlit")
    capt = []
    falso = types.ModuleType("streamlit")
    falso.iframe = lambda html, height=1: capt.append(html)
    sys.modules["streamlit"] = falso
    try:
        for m in [k for k in list(sys.modules)
                  if k.startswith("inyecciones")]:
            del sys.modules[m]
        from inyecciones.hover_kpis import (inject_hover_kpis,
                                            inject_hover_kpis_grid)
        inject_hover_kpis_grid("una_grilla", "una_tarjeta",
                               {"Total": "total", "Está vs Sistema": "estado"})
        inject_hover_kpis("una_tarjeta",
                          [{"tit": "ene", "vals": ["1"]},
                           {"tit": "feb", "vals": ["2"]}])
    finally:
        if guardado is not None:
            sys.modules["streamlit"] = guardado
        else:
            del sys.modules["streamlit"]
        for m in [k for k in list(sys.modules) if k.startswith("inyecciones")]:
            del sys.modules[m]

    if len(capt) != 2:
        fallos += 1
        print(f"FALLA hover_kpis · se esperaban 2 inyecciones, salieron "
              f"{len(capt)}")
    else:
        crudos = [t for h in capt for t in re.findall(r"__[A-Z_]+__", h)]
        if crudos:
            fallos += 1
            print("FALLA hover_kpis · quedó un marcador sin sustituir en el "
                  f"srcdoc: {sorted(set(crudos))}")
        elif not all('"total"' in h or "'total'" in h
                     for h in capt[:1]):
            fallos += 1
            print("FALLA hover_kpis · el mapa de columnas no viajó al srcdoc")
        else:
            print("OK    hover_kpis · las dos inyecciones sustituyen su "
                  "marcador")
        # Y que el JSON del mapa sea legible del otro lado (acentos incluidos).
        if capt and json.dumps("Está vs Sistema", ensure_ascii=False)[1:-1] \
                not in capt[0]:
            fallos += 1
            print("FALLA hover_kpis · el nombre de columna con acento no "
                  "sobrevivió al srcdoc")
        else:
            print("OK    hover_kpis · el col-id con acento viaja entero")
    return fallos

def _pruebas_recorrido_fuentes():
    """Que el recorrido de `_fuentes_py` siga VIENDO el repo.

    Guarda de la guarda, y no es paranoia: el filtro anterior (mirar los
    componentes de la ruta ABSOLUTA) dejaba el barrido en CERO ficheros al
    correr el test desde un worktree de `.claude/`, que es justamente
    desde donde lo corre una sesión de IA. Todas las guardas que rastrean
    el fuente pasaban en verde sin abrir un solo fichero.

    Un recorrido vacío no puede fallar nunca; por eso hace falta afirmar
    en positivo que encuentra lo que tiene que encontrar.
    """
    import pathlib

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    recorrido · {nombre}")
        else:
            fallos += 1
            print(f"FALLA recorrido · {nombre}{': ' + detalle if detalle else ''}")

    raiz = pathlib.Path(__file__).parent
    vistos = {py.relative_to(raiz).as_posix() for py, _ in _fuentes_py(raiz)}

    # Tres ficheros de tres niveles distintos: raíz, paquete y subpaquete.
    # Si alguno se renombra, esta prueba se actualiza — es el precio de
    # afirmar en positivo, y es más barato que un barrido mudo.
    esperados = {"app.py", "estilos/_00_base.py",
                 "graficos/compras/_comun.py"}
    check("el barrido del repo ve sus propios ficheros",
          esperados <= vistos,
          f"no encontró {sorted(esperados - vistos)}")

    # El corte de verdad: las copias de `.claude/worktrees/` quedan fuera.
    colados = sorted(r for r in vistos if r.startswith("."))
    check("el barrido no entra en directorios con punto (.claude/…)",
          not colados, ", ".join(colados[:4]))

    # Y que el barrido de un SUBdirectorio siga siendo no vacío: los
    # `raiz` de las guardas no son todos la raíz del repo.
    n_graficos = sum(1 for _ in _fuentes_py(raiz / "graficos"))
    check("el barrido de un subdirectorio no viene vacío",
          n_graficos > 10, f"sólo {n_graficos} ficheros en graficos/")

    return fallos


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
    from graficos import compras as _c
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

    # nombre_propio ya NO vive en graficos/base.py: hasta el 2026-09-11
    # hubo dos, con el mismo nombre y distinto resultado en 48 de los 773
    # proveedores. Quedó la de `graficos/compras/_etiquetas_proveedor.py`
    # con las reglas de las dos; sus casos están en el bloque `_ep` de más
    # abajo, y `_pruebas_una_sola_nombre_propio` vigila que no reaparezca
    # una segunda copia. Ver arquitectura.md regla #379.

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

    # nombre_propio — el ranking de Proveedor MUESTRA esto y guarda el
    # original en `_prov_raw` (proveedor.py). Los casos salen de contar los
    # 773 proveedores reales de compras.parquet, no de inventarlos: si
    # alguien "simplifica" el orden de los `elif`, acá se cae.
    #
    # Es la ÚNICA nombre_propio del repo desde el 2026-09-11 (regla #379):
    # `graficos/base.py` tenía otra, y diferían en 48 de los 773. Los casos
    # de abajo marcados «(era de base.py)» son las reglas que aportaba esa
    # copia y que si desaparecen hacen que Volatilidad vuelva a escribir
    # los nombres distinto que el drill de Proveedor. Lo que NADIE de los
    # dos lados hacía bien (el apóstrofo) tiene su propio bloque al final.
    check("propio caso base",
          _ep.nombre_propio("DOBLE G REPRESENTACIONES S.A.C."),
          "Doble G Representaciones S.A.C.")
    check("propio Ñ y sigla con puntos",
          _ep.nombre_propio("COMPAÑIA FOOD RETAIL S.A.C."),
          "Compañia Food Retail S.A.C.")
    check("propio E.I.R.L.",
          _ep.nombre_propio("INVERSIONES BARCO AZUL E.I.R.L."),
          "Inversiones Barco Azul E.I.R.L.")
    # Sigla SIN puntos: 46 SAC + 18 EIRL + 12 SA en los datos reales.
    check("propio sigla sin puntos",
          _ep.nombre_propio("ESTABLECIMIENTOS INCA SAC"),
          "Establecimientos Inca SAC")
    check("propio sigla larga sin puntos (SRLTDA)",
          _ep.nombre_propio("A-IBAR COMERCIAL SRLTDA"),
          "A-Ibar Comercial SRLTDA")
    # Preposición en minúscula, artículo NO: en castellano el artículo que
    # forma parte del nombre lleva mayúscula.
    check("propio preposición en minúscula",
          _ep.nombre_propio("LUZ DEL SUR S.A.A."), "Luz del Sur S.A.A.")
    check("propio artículo en mayúscula",
          _ep.nombre_propio("AGRICOLA LA CHACRA S.A.C."),
          "Agricola La Chacra S.A.C.")
    # … pero el artículo que viene DETRÁS de una preposición es parte del
    # sintagma y va en minúscula. Las dos versiones viejas acertaban una de
    # las dos y fallaban la otra; por eso son dos listas y no una.
    check("propio artículo tras preposición, en minúscula",
          _ep.nombre_propio("BANCO DE LA NACION"), "Banco de la Nacion")
    check("propio artículo plural tras preposición",
          _ep.nombre_propio("CERVECERIA ARTESANAL DE LOS ANDES S.A.C."),
          "Cerveceria Artesanal de los Andes S.A.C.")
    check("propio apellido «De la Cruz»",
          _ep.nombre_propio("DE LA CRUZ ASTORGA LUIS ALFONSO"),
          "De la Cruz Astorga Luis Alfonso")
    check("propio conjunción en minúscula",
          _ep.nombre_propio("PACIFICO COMPAÑIA DE SEGUROS Y REASEGUROS"),
          "Pacifico Compañia de Seguros y Reaseguros")
    # Una palabra menor NO se baja si abre el nombre.
    check("propio menor primera queda en mayúscula",
          _ep.nombre_propio("EL ESTUDIANTE S.A."), "El Estudiante S.A.")
    # Sigla PARTIDA en letras sueltas — existe: "LINDAS TELAS S A".
    check("propio letras sueltas intactas",
          _ep.nombre_propio("LINDAS TELAS S A"), "Lindas Telas S A")
    # Persona: sin siglas ni menores, todo capitalizado.
    check("propio persona",
          _ep.nombre_propio("HOYOS OLEA LUCY JACQUELINE"),
          "Hoyos Olea Lucy Jacqueline")
    # "Otros" (el bucket del ranking) y "TOTAL" pasan por la misma función
    # sin romperse: el primero sale igual, el segundo se capitaliza.
    check("propio bucket Otros", _ep.nombre_propio("Otros"), "Otros")
    check("propio vacío", _ep.nombre_propio(""), "")
    # None NO es lo mismo que "": `str(None)` da "None" y la celda mostraría
    # un proveedor llamado "None". (era de base.py)
    check("propio None pasa de largo", _ep.nombre_propio(None), None)
    # Separador que NO es espacio. Los dos salieron de correr la función
    # sobre los nombres reales: sin capitalizar por RACHAS daban "E&r"
    # y "(peru)" — en el segundo, el primer caracter es "(" y ponerlo en
    # mayúscula no hace nada mientras el resto se va a minúscula.
    check("propio & sin espacios",
          _ep.nombre_propio("E&R INNOVACIONES GLASS S.A.C."),
          "E&R Innovaciones Glass S.A.C.")
    check("propio paréntesis y guión",
          _ep.nombre_propio("TTG-THE GLOBAL GROUP (PERU)"),
          "TTG-The Global Group (Peru)")
    check("propio dígitos adentro del token",
          _ep.nombre_propio("3M PERU S.A."), "3M Peru S.A.")
    check("propio iniciales con puntos",
          _ep.nombre_propio("COMERCIAL COGNIMETA Y.R. E.I.R.L."),
          "Comercial Cognimeta Y.R. E.I.R.L.")

    # SIN VOCALES = SIGLA. (era de base.py) Son 24 de los 773: sin esta
    # regla "LV DITEK" sale "Lv Ditek" y "OPERADORA LCPM", "Operadora
    # Lcpm" — se leen como palabra y no lo son. No hay tope de largo
    # porque un tope de tres letras dejaba pasar "JCCF" y "LCPM".
    for _entra, _sale in [
        ("LV DITEK S.A", "LV Ditek S.A"),
        ("CORPORACION BASERITO LMC SAC", "Corporacion Baserito LMC SAC"),
        ("CORPORACION MG SOCIEDAD ANONIMA CERRADA",
         "Corporacion MG Sociedad Anonima Cerrada"),
        ("JCCF S.A.C.", "JCCF S.A.C."),
        ("OPERADORA LCPM S.A.C.", "Operadora LCPM S.A.C."),
        ("ALMACENES J&S SAC", "Almacenes J&S SAC"),
    ]:
        check(f"propio sin vocales · {_entra[:26]}",
              _ep.nombre_propio(_entra), _sale)
    # Y EL LÍMITE DE ESA REGLA: la Y cuenta como vocal. Sin eso, el único
    # falso positivo del parquet — la Y hace de vocal en inglés y "DRY" no
    # es una sigla. Era el precio que pagaba la versión de base.py.
    check("propio la Y no hace sigla",
          _ep.nombre_propio("DASSO DRY CLEANER E.I.R.L."),
          "Dasso Dry Cleaner E.I.R.L.")

    # APÓSTROFO — esto no lo hacía bien NINGUNA de las dos: la de
    # `_etiquetas_proveedor` escribía "Stella'S" (la racha de después
    # arranca palabra) y la de base.py acertaba de rebote, sin regla. Son 5
    # nombres reales y el ERP usa DOS caracteres distintos: U+0027 y U+00B4.
    check("propio posesivo en minúscula",
          _ep.nombre_propio("STELLA'S FV E.I.R.L."), "Stella's FV E.I.R.L.")
    check("propio posesivo con acento agudo (U+00B4)",
          _ep.nombre_propio("KEY´S MASTER E.I.R.L."),
          "Key´s Master E.I.R.L.")
    check("propio letra suelta tras apóstrofo",
          _ep.nombre_propio("QUILCAT FLORES GUISEL'L EDITH"),
          "Quilcat Flores Guisel'l Edith")
    # El tope de dos letras es lo que separa el rabito de la partícula
    # elidida. No está en el parquet de hoy; está para que el día que entre
    # un "D'ONOFRIO" no salga "D'onofrio".
    check("propio partícula elidida NO se baja",
          _ep.nombre_propio("D'ONOFRIO SAC"), "D'Onofrio SAC")

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

    # ── El buscador encuentra cualquier insumo (2026-09-26) ─────────────
    # Cinco semanas que miden; «Choco 72» compró 2 de 5 por S/ 364 (el caso
    # real de «Chocolate 72% Cacao»), «Choco 60» 4 de 5 pero poco gasto,
    # «Choco blanco» sólo antes de las cinco, y «Limón» sí entra al ranking.
    _sem = list(pd.date_range("2026-08-24", periods=5, freq="7D"))
    _vieja = pd.Timestamp("2026-06-29")
    _fx = pd.DataFrame([
        ("Choco 72", _sem[2], 161.0), ("Choco 72", _sem[2], 122.0),
        ("Choco 72", _sem[3], 81.0), ("Choco 72", _vieja, 900.0),
        ("Choco 60", _sem[0], 50.0), ("Choco 60", _sem[1], 50.0),
        ("Choco 60", _sem[2], 50.0), ("Choco 60", _sem[3], 50.0),
        ("Choco blanco", _vieja, 97.0),
        ("Limón", _sem[0], 500.0),
    ], columns=["P", "_semana", "V"])
    _fx_rec = _fx[_fx["_semana"].isin(_sem)]
    _fu = _vol._vol_fuera_del_ranking(_fx, _fx_rec, "choco", {"Limón": {}},
                                      "P", "V", 5)
    check("_vol_fuera_del_ranking: encuentra los tres que no entran",
          sorted(_fu), ["Choco 60", "Choco 72", "Choco blanco"])
    check("_vol_fuera_del_ranking: ordena por lo gastado en la VENTANA",
          list(_fu), ["Choco 72", "Choco 60", "Choco blanco"])
    check("_vol_fuera_del_ranking: los números son los que miró el filtro",
          (_fu["Choco 72"]["semanas"], _fu["Choco 72"]["gasto"]), (2, 364.0))
    check("_vol_fuera_del_ranking: el motivo nombra los dos pisos",
          _fu["Choco 72"]["motivo"],
          "compró 2 de las 5 semanas (pide 4) y S/ 364 de gasto (pide S/ 400)")
    check("_vol_fuera_del_ranking: sólo el piso que no cumple",
          _fu["Choco 60"]["motivo"], "S/ 200 de gasto (pide S/ 400)")
    check("_vol_fuera_del_ranking: sin compras en las que miden",
          _fu["Choco blanco"]["motivo"], "sin compras en las últimas 5 semanas")
    check("_vol_fuera_del_ranking: no repite a los del ranking",
          list(_vol._vol_fuera_del_ranking(_fx, _fx_rec, "lim", {"Limón": {}},
                                           "P", "V", 5)), [])
    check("_vol_fuera_del_ranking: sin búsqueda, nadie",
          _vol._vol_fuera_del_ranking(_fx, _fx_rec, "", {}, "P", "V", 5), {})
    check("_vol_sin_coincidencias: existe fuera de la ventana",
          _vol._vol_sin_coincidencias("choco", _fx, "P", "12m")
          .startswith("Ningún insumo con «choco» se compró en los últimos 12 "
                      "meses."), True)
    check("_vol_sin_coincidencias: no existe",
          _vol._vol_sin_coincidencias("pato", _fx, "P", "12m"),
          "Ningún insumo coincide con «pato».")

    # ── El grano COMPRA (2026-09-20, regla #478) ────────────────────────
    from tema import PALETA_SERIES
    from graficos import alturas
    # La dispersión es OTRA pregunta que el puntaje semanal: mide cuánto se
    # apartan los precios entre sí, no cuánto se movieron en el tiempo. El
    # caso que lo justifica está acá abajo con números de «Limón Criollo».
    check("_vol_dispersion: desvío muestral / promedio",
          round(_vol._vol_dispersion([10, 10, 10, 10, 20], minimo=5), 4),
          0.3727)
    check("_vol_dispersion: precio plano → 0",
          _vol._vol_dispersion([7.0] * 5, minimo=5), 0.0)
    check("_vol_dispersion: con menos compras que el piso → None",
          _vol._vol_dispersion([10, 20, 30], minimo=5), None)
    check("_vol_dispersion: filtra ceros y NaN antes de contar",
          _vol._vol_dispersion([7, 7, 0, float("nan"), 7], minimo=5), None)
    # Lo que ve un grano y no ve el otro, con el caso real: cuatro cierres
    # semanales idénticos (score 0) sobre compras que fueron 4.00 y 12.70.
    check("dispersión ve lo que el cierre semanal no",
          (_vol._vol_score([4.0, 4.0, 4.0, 4.0]),
           round(_vol._vol_dispersion([4.39, 12.70, 4, 4, 4, 4, 4, 4, 4]), 2)),
          (0.0, 0.58))

    # Un id por compra, estable aunque el día repita.
    _cmp = [{"fecha": pd.Timestamp("2026-09-16")} for _ in range(3)]
    _cmp.append({"fecha": pd.Timestamp("2026-09-17")})
    check("_vol_ids_compras: el orden dentro del día desempata",
          _vol._vol_ids_compras(_cmp),
          ["20260916#0", "20260916#1", "20260916#2", "20260917#0"])

    # Las X: el eje sigue siendo el calendario (los huecos son dato) y las
    # compras del mismo día se separan contra el PASO de la ventana.
    _xs = _vol._vol_x_compras([pd.Timestamp("2026-09-01"),
                               pd.Timestamp("2026-09-16"),
                               pd.Timestamp("2026-09-16")])
    check("_vol_x_compras: una compra sola se queda en su fecha",
          _xs[0], pd.Timestamp("2026-09-01"))
    check("_vol_x_compras: dos del mismo día no comparten X",
          _xs[1] != _xs[2], True)
    check("_vol_x_compras: el grupo no invade el día vecino",
          all(abs((x - pd.Timestamp("2026-09-16")).total_seconds()) <= 86400
              for x in _xs[1:]), True)
    check("_vol_x_compras: sin repetidos cuando hay cinco el mismo día",
          len(set(_vol._vol_x_compras([pd.Timestamp("2026-09-16")] * 5))), 5)

    # El sobrecosto: (precio − mínimo) × cantidad. Los números son los ocho
    # de «Chirimoya» medidos el 2026-09-20 contra el parquet.
    _cc = [{"precio": 7.0, "cant": 12.0}, {"precio": 11.4625, "cant": 1.265},
           {"precio": 7.0, "cant": 5.0}]
    _sob, _gas, _pct = _vol._vol_sobrecosto(_cc)
    check("_vol_sobrecosto: contra el mejor precio del período",
          round(_sob, 2), 5.65)
    check("_vol_sobrecosto: el gasto es precio × cantidad",
          round(_gas, 2), 133.5)
    check("_vol_sobrecosto: un solo precio no tiene sobrecosto",
          _vol._vol_sobrecosto([{"precio": 7.0, "cant": 3.0}]),
          (0.0, 21.0, 0.0))
    check("_vol_sobrecosto: sin filas no revienta",
          _vol._vol_sobrecosto([]), (0.0, 0.0, 0.0))

    # El proveedor que más pesa se lleva el morado de la marca.
    _col = _vol._vol_colores_proveedor([
        {"prov": "Chico", "monto": 10.0}, {"prov": "Grande", "monto": 90.0}])
    check("_vol_colores_proveedor: manda el GASTO, no el orden de aparición",
          _col["Grande"], PALETA_SERIES[0])
    check("_vol_colores_proveedor: y el otro no repite color",
          _col["Chico"] != _col["Grande"], True)

    # Las etiquetas de precio: seis compras al mismo precio no se rotulan
    # seis veces, pero las puntas siempre llevan la suya.
    # Y el REGRESO también se rotula: 7 → 11.5 → 7 escribe los tres, porque
    # la comparación es contra el último ROTULADO y no contra el vecino. Sin
    # eso, el punto que vuelve al precio de siempre queda mudo y la serie se
    # lee como si el precio se hubiera quedado arriba. No se pisan: un
    # rótulo y el siguiente están a un hueco entero de distancia, y los dos
    # que sí comparten altura nunca son vecinos (su diferencia es 0).
    _rot = _vol._vol_etiquetas_precio([7.0, 7.0, 7.0, 11.5, 7.0, 7.0], 5.0)
    check("_vol_etiquetas_precio: las puntas, lo que se aparta y lo que vuelve",
          _rot, [True, False, False, True, True, True])
    check("_vol_etiquetas_precio: dos vecinos al mismo precio no se rotulan "
          "los dos",
          _vol._vol_etiquetas_precio([7.0, 7.0, 7.0, 7.0], 5.0),
          [True, False, False, True])
    check("_vol_etiquetas_precio: una sola compra lleva su rótulo",
          _vol._vol_etiquetas_precio([7.0], 1.0), [True])
    check("_vol_etiquetas_precio: sin compras, sin rótulos",
          _vol._vol_etiquetas_precio([], 1.0), [])

    # La figura del grano Compra: la traza 0 tiene que seguir siendo el
    # blanco del clic (de ahí cuelga `curve_number == 0` en el drill) y la
    # vela no puede aparecer acá — una compra tiene UN precio.
    _fc = [{"fecha": pd.Timestamp("2026-09-01"), "precio": 7.0, "cant": 2.0,
            "monto": 14.0, "prov": "A", "doc": "F001-1"},
           {"fecha": pd.Timestamp("2026-09-04"), "precio": 11.5, "cant": 1.0,
            "monto": 11.5, "prov": "B", "doc": "F001-2"}]
    _figc = _vol._fig_serie_compras(
        _fc, _vol._vol_x_compras([r["fecha"] for r in _fc]), 0, 1, 1,
        _vol._vol_colores_proveedor(_fc), "kg", 6.0, 12.5)
    check("_fig_serie_compras: la traza 0 es el blanco del clic",
          _figc.data[0].type, "bar")
    check("_fig_serie_compras: el blanco del clic es invisible",
          _figc.data[0].marker.color, "rgba(0,0,0,0)")
    check("_fig_serie_compras: y sigue emitiendo hover (no 'skip', #388)",
          _figc.data[0].hoverinfo, "text")
    check("_fig_serie_compras: sin velas en el grano Compra",
          [t.type for t in _figc.data].count("candlestick"), 0)
    check("_fig_serie_compras: la línea es escalonada",
          _figc.data[1].line.shape, "hv")
    check("_fig_serie_compras: un color por proveedor, punto a punto",
          len(set(_figc.data[2].marker.color)), 2)
    check("_fig_serie_compras: el eje X es de fechas, no de ranuras",
          _figc.layout.xaxis.type in (None, "date"), True)
    check("_fig_serie_compras: los dos ejes fijos (la ventana la manda el "
          "servidor)",
          (_figc.layout.xaxis.fixedrange, _figc.layout.yaxis.fixedrange),
          (True, True))
    check("_fig_serie_compras: una marca por DÍA con compra",
          len(_figc.layout.xaxis.tickvals), 2)
    check("_fig_serie_compras: el alto sale de alturas.py",
          _figc.layout.height, alturas.MINI_CANDLE_DRILL)
    # Y EL CLIC TIENE QUE SER ABSOLUTO: con una ventana que no arranca en 0,
    # el blanco del clic sigue teniendo un punto por compra de la SERIE
    # —así `point_index` no depende de la ventana— mientras los puntos
    # dibujados son los del tramo. Es el bug que se midió en el navegador el
    # 2026-09-20: el clic en la última compra a la vista enfocaba otra.
    _fc3 = _fc + [{"fecha": pd.Timestamp("2026-09-09"), "precio": 8.0,
                   "cant": 3.0, "monto": 24.0, "prov": "A", "doc": "F001-3"}]
    _figv = _vol._fig_serie_compras(
        _fc3, _vol._vol_x_compras([r["fecha"] for r in _fc3]), 1, 2, 2,
        _vol._vol_colores_proveedor(_fc3), "kg", 6.0, 12.5)
    check("_fig_serie_compras: el blanco del clic cubre la SERIE entera",
          len(_figv.data[0].x), 3)
    check("_fig_serie_compras: y se dibuja sólo la ventana",
          len(_figv.data[2].x), 2)
    check("_fig_serie_compras: el anillo del foco cae en el punto dibujado",
          list(_figv.data[2].marker.line.width), [0, 1.8])

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

    # Cabecera de la grilla (2026-09-12): el mes en las dos puntas, y el año
    # corto sólo en las semanas que terminan en otro año que el de referencia.
    check("_vol_fmt_cabecera mismo mes",
          _vol._vol_fmt_semana_cabecera(pd.Timestamp("2026-08-17"), 2026),
          "17 Ago – 23 Ago")
    check("_vol_fmt_cabecera cruza de mes",
          _vol._vol_fmt_semana_cabecera(pd.Timestamp("2026-08-31"), 2026),
          "31 Ago – 6 Set")
    check("_vol_fmt_cabecera de otro año lleva el año",
          _vol._vol_fmt_semana_cabecera(pd.Timestamp("2025-09-08"), 2026),
          "8 Set – 14 Set ’25")
    check("_vol_fmt_cabecera que cruza AL año de referencia no lo lleva",
          _vol._vol_fmt_semana_cabecera(pd.Timestamp("2025-12-29"), 2026),
          "29 Dic – 4 Ene")

    # La serie de la grilla Y del puntaje: relleno hacia adelante, None sólo
    # antes de la primera compra, y el cierre es la ÚLTIMA compra válida de
    # la semana (un 0 no cierra nada).
    _sems = [pd.Timestamp("2026-06-01"), pd.Timestamp("2026-06-08"),
             pd.Timestamp("2026-06-15"), pd.Timestamp("2026-06-22")]
    _dc = pd.DataFrame({
        "p": ["A", "A", "A", "B"],
        "precio": [10.0, 12.0, 0.0, 5.0],
        "f": pd.to_datetime(["2026-06-08", "2026-06-10", "2026-06-17",
                             "2026-06-01"]),
    })
    _dc["_semana"] = (_dc["f"] - pd.to_timedelta(_dc["f"].dt.weekday, unit="D")
                      ).dt.normalize()
    _ch = _vol._vol_cierres_semanales(_dc, ["A", "B"], "p", "precio", "f", _sems)
    check("_vol_cierres: None antes de la primera compra, luego relleno",
          _ch["A"], [None, 12.0, 12.0, 12.0])
    check("_vol_cierres: una compra al principio se arrastra",
          _ch["B"], [5.0, 5.0, 5.0, 5.0])
    check("_vol_cierres: el puntaje sale de la misma serie",
          _vol._vol_score(_ch["A"]), 0.0)

    # El respaldo de la primera vela: el último precio válido ANTES de la
    # ventana, en soles (un 0 y un precio en dólares no cuentan).
    _dp = pd.DataFrame({
        "p": ["A", "A", "A", "A"],
        "precio": [9.0, 11.0, 0.0, 30.0],
        "f": ["2026-05-01", "2026-05-20", "2026-05-25", "2026-05-26"],
        "m": ["01", "01", "01", "02"],
    })
    check("_vol_precio_previo: último válido en soles antes de la fecha",
          _vol._vol_precio_previo(_dp, "A", "p", "precio", "f", "m",
                                  pd.Timestamp("2026-06-01")), 11.0)
    check("_vol_precio_previo: sin compras antes -> None",
          _vol._vol_precio_previo(_dp, "A", "p", "precio", "f", "m",
                                  pd.Timestamp("2026-05-01")), None)

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

    # El veredicto de arriba de la cascada (regla #414). Lo que se fija es
    # que cada pedazo diga QUÉ es: "−62.6% · la cantidad" se leía como "la
    # cantidad bajó 62.6%", y ese 62.6% era del gasto. La causa va con verbo
    # y dirección, y el % con contra qué se restó.
    # `solo="pct"` es el renglón del porcentaje; `solo="monto"`, el del
    # rótulo con su cifra. Se piden por separado porque se dibujan en
    # bloques distintos (el del monto comparte fila con el corte).
    _r = _vap._resumen_html(-16660.0, -62.6, 235.0, -16895.0, 9933.0,
                            26594.0, solo="pct")
    check("veredicto: el % dice contra qué se restó",
          "−62.6% vs año pasado" in _r, True)
    check("veredicto: la causa va con su dirección",
          "por comprar menos" in _r, True)
    check("veredicto: sin el sustantivo pelado que se pegaba al %",
          "· la cantidad" in _r, False)
    check("veredicto: el title escribe la resta de la cascada",
          "Este año S/ 9,933 − año pasado S/ 26,594 = −S/ 16,660"
          in _vap._resumen_html(-16660.0, -62.6, 235.0, -16895.0, 9933.0,
                                26594.0), True)
    check("causa: precio que manda y sube",
          _vap._causa(300.0, 400.0, -100.0), "por precio más alto")
    check("causa: precio que manda y baja",
          _vap._causa(-300.0, -400.0, 100.0), "por precio más bajo")
    check("causa: sin diferencia no se inventa una",
          _vap._causa(0.0, 100.0, -100.0), "")
    check("veredicto: ítem nuevo, sin un +0.0% que diga 'no cambió'",
          "%" in _vap._resumen_html(500.0, None, 0.0, 500.0, 500.0, 0.0,
                                    solo="pct"),
          False)

    # ── La tabla mes a mes que ALTERNA con el waterfall (regla #484) ────
    # Es el espejo escrito de la serie de la izquierda: una fila por mes,
    # cronológica (no por |Δ| como la de abajo), con el semáforo invertido
    # de la casa (subir un costo es rojo).
    _gt = pd.DataFrame({
        "mes": [pd.Period("2026-08", "M"), pd.Period("2026-07", "M")],
        "valor": [150.0, 100.0], "cant": [12.0, 10.0],
        "valor_aa": [200.0, 90.0], "cant_aa": [15.0, 9.0],
    })
    _ht = _vap._tabla_mensual_html(_gt, "Valor", "", _vap._fmt_soles,
                                   ("2025", "2026"))
    check("tabla mensual: una fila por mes, ambos presentes",
          ("jul 26" in _ht) and ("ago 26" in _ht), True)
    check("tabla mensual: cronológica (jul antes que ago), no por |Δ|",
          _ht.index("jul 26") < _ht.index("ago 26"), True)
    check("tabla mensual: este año y año pasado, tal cual la serie",
          ("S/ 100" in _ht) and ("S/ 90" in _ht), True)
    check("tabla mensual: el Δ que sube va con + y en rojo (es un costo)",
          f"color:{_vap.ERROR}'>+S/ 10" in _ht, True)
    check("tabla mensual: el Δ que baja va con − y en verde",
          f"color:{_vap.EXITO}'>−S/ 50" in _ht, True)
    check("tabla mensual: la cabecera dice los años del waterfall",
          ("2026" in _ht) and ("2025" in _ht), True)
    # Precio es un RATIO por mes: un mes sin cantidad no tiene precio y la
    # celda queda vacía («—»), no en 0 (mismo criterio que `_fig_serie`).
    _hp = _vap._tabla_mensual_html(
        pd.DataFrame({"mes": [pd.Period("2026-07", "M")], "valor": [100.0],
                      "cant": [0.0], "valor_aa": [90.0], "cant_aa": [9.0]}),
        "Precio", "kg", lambda v: _vap._fmt_precio(v, "kg"), ("2025", "2026"))
    check("tabla mensual (Precio): mes sin cantidad, celda vacía no cero",
          ("—" in _hp) and ("S/ 10.00/kg" in _hp), True)
    check("tabla mensual: sin meses lo dice, no revienta",
          "Sin meses" in _vap._tabla_mensual_html(
              _gt.iloc[0:0], "Valor", "", _vap._fmt_soles, ("2025", "2026")),
          True)

    # ── Los tres cortes de la cascada (regla #443) ──────────────────────
    # LA REGLA ES UNA SOLA: un corte se ofrece si la magnitud es ADITIVA en
    # ese eje y el ámbito tiene MÁS DE UN elemento. Lo que se fija acá son
    # los cinco casos que salen de ella, porque cada uno es un gráfico que
    # CIERRA pero no significa nada si se cuela (la lección de `_por_item`).
    check("Valor, todo: los tres cortes",
          _vap._cortes_disponibles("Valor", False, False)[0],
          ("Por qué", "Quién", "Cuándo"))
    check("un solo ítem: «Quién» no tiene a quién nombrar",
          _vap._cortes_disponibles("Valor", True, False)[0],
          ("Por qué", "Cuándo"))
    check("un solo mes: «Cuándo» no tiene cuándo",
          _vap._cortes_disponibles("Valor", False, True)[0],
          ("Por qué", "Quién"))
    check("Cantidad: en kilos no hay efecto precio que separar",
          _vap._cortes_disponibles("Cantidad", True, False)[0], ("Cuándo",))
    check("Precio: un precio no se suma por ningún eje",
          _vap._cortes_disponibles("Precio", False, False)[0], ())
    # Y los descartados se DICEN, no se tragan: un control que ofrece tres
    # cosas hoy y una mañana sin decir por qué se lee como un bug.
    _ops_c, _fuera_c = _vap._cortes_disponibles("Cantidad", True, False, "kg")
    check("el motivo nombra la unidad real, no 'unidades'",
          "en kg no hay efecto precio", _fuera_c["Por qué"])
    check("la ayuda del selector lista los que no aplican",
          "«Quién», ya hay un solo ítem" in _vap._ayuda_corte(_fuera_c), True)
    check("sin descartados la ayuda no dice que no pasa nada",
          "no aplican" in _vap._ayuda_corte({}), False)

    # La cascada de contribuyentes: la cola se suma en UNA barra, y esa
    # barra es el veredicto sobre esta forma de mirar (cuánto NO se nombró).
    _partes = [("A", -100.0), ("B", 60.0), ("C", -30.0), ("D", 10.0),
               ("E", -5.0), ("F", -4.0), ("G", 3.0)]
    _pasos = _vap._pasos_cascada(_partes, 1000.0, 934.0)
    # 3 nombradas + resto + los dos bordes = 6. El tope no es un gusto: son
    # 63px de columna contra un rótulo de 59 (medido, ver `_TOPE_CASCADA`).
    check("cascada: el tope que se midió sigue siendo 3",
          _vap._TOPE_CASCADA, 3)
    check("cascada: bordes + tope + resto", len(_pasos), 6)
    check("cascada: el resto junta lo que no entró",
          round(_pasos[-2]["valor"], 6), 4.0)
    check("cascada: el resto dice cuántos junta", _pasos[-2]["label"],
          "otros<br>4")
    check("cascada: los pasos cierran contra el total",
          round(sum(p["valor"] for p in _pasos[1:-1]), 6),
          round(934.0 - 1000.0, 6))
    check("cascada: entran las de mayor |Δ|, sin mirar el signo",
          [p["label"] for p in _pasos[1:4]], ["A", "B", "C"])
    # «Cuándo» ELIGE por |Δ| pero DIBUJA en orden de calendario: una
    # cascada de tiempo con los meses barajados por tamaño no se lee.
    _meses = [("ene", -5.0), ("feb", -90.0), ("mar", -3.0), ("abr", -70.0),
              ("may", -40.0), ("jun", -20.0)]
    _pc = _vap._pasos_cascada(_meses, 1000.0, 772.0, cronologico=True)
    check("cascada cronológica: los meses no se barajan",
          [p["label"] for p in _pc[1:4]], ["feb", "abr", "may"])
    # Y un rótulo que no entra en la columna se corta CON "…", para que el
    # recorte se vea: un nombre cortado en seco se lee como otro nombre.
    check("etiqueta de barra: dos renglones que entran en la columna",
          max(len(l) for l in
              _vap._etq_barra("Magret De Pato Macho x Kg").split("<br>")),
          _vap._ANCHO_ETQ_BARRA)
    check("etiqueta de barra: corta por palabra, no a la mitad",
          _vap._etq_barra("Lomo fino entero nacional x Kg").split("<br>")[0],
          "Lomo fino")
    check("etiqueta de barra: un nombre corto se deja entero",
          _vap._etq_barra("Cachema"), "Cachema")
    # Tres barras cuando ningún corte aplica: es el techo honesto de esa
    # magnitud, no un gráfico roto.
    _ps = _vap._pasos_simple(61.02, 74.68)
    check("cascada simple: de dónde a dónde", len(_ps), 3)
    check("cascada simple: el paso del medio es la resta",
          round(_ps[1]["valor"], 2), 13.66)

    # La magnitud manda sobre el veredicto: una cifra en soles encima de un
    # dibujo en kilos es una contradicción en la misma tarjeta.
    _rk = _vap._resumen_html(-328.9, -35.7, 0.0, 0.0, 592.5, 921.4,
                             fmt=lambda v: _vap._fmt_cant(v, "kg"), causa="")
    check("veredicto en kilos, no en soles", "−328.9 kg" in _rk, True)
    check("veredicto en kilos: sin S/ por ningún lado", "S/" in _rk, False)
    check("veredicto en kilos: sin causa inventada",
          "por comprar" in _rk, False)
    # El rótulo va PEGADO a su monto y en el mismo renglón (regla #448):
    # una etiqueta arriba y el número abajo se leen como dos cosas.
    _rv = _vap._resumen_html(-16660.0, -62.6, 235.0, -16895.0, 9933.0,
                             26594.0, magnitud="Δ Valorizado de Compra")
    check("el veredicto lleva su rótulo adentro",
          "Δ Valorizado de Compra" in _rv, True)
    # El rótulo es un NOMBRE, no una etiqueta en versalitas: el CSS no
    # puede pasarlo a mayúsculas o se lee como un campo de formulario.
    check("el rótulo se sirve tal como se escribe",
          "text-transform:uppercase" in _rv, False)
    check("el rótulo NO dice 'total' (con foco sería falso)",
          "total" in _rv.lower(), False)
    check("el monto va chico (13px), no de titular",
          "13px" in _rv and "18px" not in _rv, True)
    check("el renglón del monto NO trae el %",
          "62.6%" in _rv, False)
    # El nombre del ítem es el título de la tarjeta: azul y centrado.
    _nom = _vap._nombre_cascada_html("Magret De Pato Macho x Kg")
    check("el nombre del ítem va centrado", "text-align:center" in _nom, True)
    check("el nombre del ítem va en el azul de la paleta",
          __import__("tema").ACENTO_TEXTO in _nom, True)
    check("sin foco no se escribe un nombre",
          _vap._nombre_cascada_html(""), "")
    check("la etiqueta de una barra del medio va con signo",
          _vap._etq_cascada(-16660.0, "relative", _vap._fmt_soles),
          "−S/ 16,660")
    check("la de un borde es un total y va sin signo",
          _vap._etq_cascada(286254.0, "total", _vap._fmt_soles),
          "S/ 286,254")

    # Etiquetas de la serie mensual (regla #400). Lo que se fija es que la
    # etiqueta sea LEGIBLE en cada ventana: con 3 meses (el default) entra
    # derecha, con 12 girada, y con "Todo" ya no caben las dos series.
    check("etiqueta de valor compacta con un decimal",
          _vap._fmt_etiqueta(107911.0, "Valor"), "S/ 107.9k")
    check("etiqueta de cantidad sin S/", _vap._fmt_etiqueta(1234.5, "Cantidad"),
          "1.2k")
    check("etiqueta de precio con sus dos decimales",
          _vap._fmt_etiqueta(12.345, "Precio"), "S/ 12.35")
    check("una columna en cero no lleva etiqueta",
          _vap._fmt_etiqueta(0.0, "Valor"), None)
    check("3 meses: etiquetas derechas en las dos series",
          _vap._plan_etiquetas(3, 9, "Valor"),
          {"girar": False, "ambas": True, "paso": 1, "n_sec": 0})
    check("12 meses: no entran derechas, van giradas",
          _vap._plan_etiquetas(12, 9, "Valor"),
          {"girar": True, "ambas": True, "paso": 1, "n_sec": 0})
    # Renglones secundarios con las otras métricas (reglas #401, #484):
    # entran los dos con 3 meses; con 12 ceden, no la etiqueta del año
    # pasado.
    check("3 meses con secundarias: los tres renglones derechos",
          _vap._plan_etiquetas(3, 9, "Cantidad", largo_sec=11, n_sec=2),
          {"girar": False, "ambas": True, "paso": 1, "n_sec": 2})
    check("12 meses con secundarias: ceden, las dos series quedan",
          _vap._plan_etiquetas(12, 9, "Cantidad", largo_sec=11, n_sec=2),
          {"girar": True, "ambas": True, "paso": 1, "n_sec": 0})
    check("cantidad con unidad va entera",
          _vap._fmt_etiqueta(4300.0, "Cantidad", "kg"), "4,300 kg")
    check("cantidad con unidad y muchos miles, compacta",
          _vap._fmt_etiqueta(123456.0, "Cantidad", "und"), "123.5k und")
    check("precio por unidad", _vap._fmt_etiqueta(12.345, "Precio", "kg"),
          "S/ 12.35/kg")
    check("secundarias debajo del principal",
          _vap._apilar("300 kg", ["S/ 12.35/kg"]).split("<br>")[0], "300 kg")
    check("dos secundarias apiladas",
          _vap._apilar("S/ 13.5k", ["157 kg", "S/ 86.11/kg"]).count("<br>"), 2)
    check("sin principal no hay etiqueta",
          _vap._apilar(None, ["S/ 12.35/kg"]), None)
    from graficos.compras._comun import unidad_corta as _uc
    check("unidad_corta KILOS", _uc("KILOS"), "kg")
    # "Lt" y no "L": el símbolo SI no es el vocabulario de la casa — el
    # propio catálogo escribe "Drambuie x Lt" (2026-09-13, a pedido). Va
    # como assert para que no vuelva sola en el próximo retoque del mapa.
    check("unidad_corta LITROS", _uc("LITROS"), "Lt")
    check("unidad_corta LT abreviado", _uc("LT"), "Lt")
    check("unidad_corta desconocida sale en minúscula", _uc("ROLLO"), "rollo")
    check("32 meses: sólo rotula «Este año»",
          _vap._plan_etiquetas(32, 9, "Cantidad")["ambas"], False)
    check("precio con 12 meses rotula las dos líneas",
          _vap._plan_etiquetas(12, 8, "Precio")["ambas"], True)
    # Sin alternar arriba/abajo: se probó y chocaba (regla #400). Con 32
    # meses (21 px por mes) una etiqueta de 47 px necesita 3 meses de lugar.
    check("precio con 32 meses ralea en vez de alternar",
          _vap._plan_etiquetas(32, 8, "Precio"),
          {"girar": False, "ambas": False, "paso": 3, "n_sec": 0})
    check("_ralear conserva siempre el último mes",
          _vap._ralear(["a", "b", "c", "d", "e"], 2), ["a", None, "c", None, "e"])
    _techo = _vap._techo_con_etiquetas(100.0, 0.0, 17, alto_plot=149)
    check("el techo deja lugar a la etiqueta de la columna más alta",
          round(100.0 / _techo[1] * 149), 132)

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

    # MONEDA EXTRANJERA: las tres columnas de cabecera del parquet vienen
    # en la moneda del DOCUMENTO y el registro del SIRE viene en soles, así
    # que el cruce las convierte al agrupar. Sin eso, 242 de los 248
    # comprobantes en dólares salían marcados "Diferencia" (regla #313).
    # Las columnas por línea (`_MN`) ya están en soles y NO se tocan.
    _pq_usd = pd.DataFrame({
        "NUM_DOCUMENTO": ["F0E001000000003"],
        "NOMBRE_PROVEEDOR": ["MAPFRE"],
        "INDICADOR TRIBUTARIO": ["20418896915"],
        "VALOR_COMPRA": [10733.31],
        "VALOR_BRUTO_COMPRA_MN": [12665.31],
        "TOTAL NETO": [3155.00],
        "TOTAL IGV": [567.90],
        "TOTAL DOCUMENTO": [3722.90],
        "TIPO_MONEDA": ["02"],
        "TIPO_CAMBIO": [3.402],
        "FECHA_EMISION_DOC": pd.to_datetime(["2026-07-10"]),
    })
    _g_usd = _ds._parquet_agrupado_por_documento(
        _pq_usd, "FECHA_EMISION_DOC",
        pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-31"))
    check("_parquet_agrupado lleva a soles el total de un documento en dólares",
          round(float(_g_usd["total_pq"].iloc[0]), 2), 12665.31)
    check("_parquet_agrupado lleva a soles también la base",
          round(float(_g_usd["base_pq"].iloc[0]), 2), 10733.31)
    _pq_pen = _pq_usd.assign(TIPO_MONEDA=["01"])
    _g_pen = _ds._parquet_agrupado_por_documento(
        _pq_pen, "FECHA_EMISION_DOC",
        pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-31"))
    check("y un documento en soles no se multiplica por su tipo de cambio",
          round(float(_g_pen["total_pq"].iloc[0]), 2), 3722.90)

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

    # NOTA CONTRA NOTA, FACTURA CONTRA FACTURA (regla #604). `E001-1` es
    # la primera factura de un emisor y también su primera nota de
    # crédito. Antes la nota del SIRE se emparejaba con la FACTURA del
    # mismo RUC («Diferencia»); desde que el sistema trae sus notas, las dos
    # caían juntas como candidatas. En el sistema la nota va en negativo; en
    # el SIRE la dice `tipo_cdp` 07 (o la base negativa, si no viene).
    _sire_nc = pd.DataFrame({
        "documento": ["E001-1", "E001-1", "E001-7"],
        "tipo_cdp": ["01", "07", "07"],
        "proveedor": ["CARNES SAC"] * 3,
        "ruc_proveedor": ["20888888888"] * 3,
        "fecha_emision": pd.to_datetime(["2026-09-05", "2026-09-23",
                                         "2026-09-24"]),
        "base_imponible": [1000.0, -400.0, -50.0], "no_gravado": [0.0] * 3,
        "total": [1180.0, -472.0, -59.0], "situacion": ["Registrado"] * 3,
    })
    _g_nc = pd.DataFrame({
        "documento": ["E001-1", "E001-1"],
        "ruc_pq": ["20888888888"] * 2,
        "proveedor_pq": ["CARNES SAC"] * 2,
        "base_pq": [1000.0, -400.0], "total_pq": [1180.0, -472.0],
        "fecha_pq": pd.to_datetime(["2026-09-05", "2026-09-28"]),
    })
    _cr_nc = _ds.cruzar_con_parquet(_sire_nc, _g_nc)
    _sunat_nc = _cr_nc[_cr_nc["estado"] != "Solo sistema"].reset_index(drop=True)
    check("cruce: la factura E001-1 con la factura del mismo número",
          (_sunat_nc.loc[0, "estado"], _sunat_nc.loc[0, "base_sistema"]),
          ("Coincide", 1000.0))
    check("cruce: la nota E001-1 con la NOTA del mismo número, no la factura",
          (_sunat_nc.loc[1, "estado"], _sunat_nc.loc[1, "base_sistema"]),
          ("Coincide", -400.0))
    check("cruce: una nota que el sistema no tiene es «Solo SUNAT», aunque "
          "haya una factura con su número (que queda «Solo sistema»)",
          sorted(_ds.cruzar_con_parquet(_sire_nc.iloc[[1]], _g_nc.iloc[[0]])
                 ["estado"]), ["Solo SUNAT", "Solo sistema"])
    check("cruce: sin `tipo_cdp`, la base negativa dice que es nota",
          _ds.cruzar_con_parquet(_sire_nc.drop(columns="tipo_cdp"), _g_nc)
          .loc[lambda x: x["estado"] != "Solo sistema", "estado"].tolist(),
          ["Coincide", "Coincide", "Solo SUNAT"])

    # UN SOLO CANDIDATO CON OTRO RUC (regla #606). `E001-1067` lo usan
    # decenas de emisores: el único candidato del sistema con un RUC
    # distinto —los dos presentes— es otro proveedor, y antes salía una
    # «Diferencia» falsa (33 en 12 meses). Se acepta sólo si los montos
    # calzan: es el mismo documento cargado con otro proveedor. Y si a un
    # lado le falta el RUC, se acepta como siempre.
    def _sire_uno(ruc, base=500.0, igv=90.0, total=590.0, doc="E001-1067"):
        return pd.DataFrame({
            "documento": [doc], "proveedor": ["EMISOR DEL SIRE SAC"],
            "ruc_proveedor": [ruc],
            "fecha_emision": pd.to_datetime(["2026-09-10"]),
            "base_imponible": [base], "no_gravado": [0.0], "igv": [igv],
            "total": [total], "situacion": ["Registrado"]})

    def _g_uno(ruc, base=200.0, igv=36.0, total=236.0):
        return pd.DataFrame({
            "documento": ["E001-1067"], "ruc_pq": [ruc],
            "proveedor_pq": ["OTRA CARNICERIA EIRL"],
            "base_pq": [base], "igv_pq": [igv], "total_pq": [total],
            "fecha_pq": pd.to_datetime(["2024-03-02"])})

    def _estados(cr):
        return sorted(cr["estado"])

    check("cruce: único candidato con OTRO RUC y otro monto -> sin par "
          "(«Solo SUNAT» + «Solo sistema»), no una «Diferencia» falsa",
          _estados(_ds.cruzar_con_parquet(_sire_uno("20100000001"),
                                          _g_uno("20200000002"))),
          ["Solo SUNAT", "Solo sistema"])
    _cr_sin_ruc = _ds.cruzar_con_parquet(_sire_uno(""), _g_uno("20200000002"))
    check("cruce: único candidato y el SIRE sin RUC -> se empareja",
          _estados(_cr_sin_ruc), ["Diferencia"])
    check("cruce: ... y la fila trae los montos del sistema",
          (_cr_sin_ruc.loc[0, "base_sistema"], _cr_sin_ruc.loc[0, "dif_total"]),
          (200.0, 354.0))
    check("cruce: único candidato y el sistema sin RUC -> se empareja",
          _estados(_ds.cruzar_con_parquet(_sire_uno("20100000001"),
                                          _g_uno(""))), ["Diferencia"])
    # Y el «sin RUC» del sistema tiene que llegar VACÍO: con `astype(str)`
    # solo, un nulo salía «nan» — un RUC distinto para la regla de arriba.
    _g_nulo = _ds._parquet_agrupado_por_documento(
        _pq.assign(**{"INDICADOR TRIBUTARIO": [None, None, float("nan"),
                                                float("nan")]}),
        "FECHA_EMISION_DOC", pd.Timestamp("2026-07-01"),
        pd.Timestamp("2026-07-31"))
    check("_parquet_agrupado: un RUC nulo queda vacío, no «nan» ni «None»",
          sorted(_g_nulo["ruc_pq"]), ["", ""])
    _cr_mismo = _ds.cruzar_con_parquet(
        _sire_uno("20300000003"), _g_uno("20300000103", 500.0, 90.0, 590.0))
    check("cruce: otro RUC pero los tres montos calzan -> el mismo documento "
          "cargado con otro proveedor, «Coincide»",
          (_estados(_cr_mismo), _cr_mismo.loc[0, "ruc_sistema"]),
          (["Coincide"], "20300000103"))
    check("cruce: otro RUC, base y total calzan pero el IGV no -> sin par",
          _estados(_ds.cruzar_con_parquet(
              _sire_uno("20300000003"),
              _g_uno("20300000103", 500.0, 50.0, 590.0))),
          ["Solo SUNAT", "Solo sistema"])
    check("cruce: otro RUC y siete céntimos de diferencia -> sin par (la "
          "tolerancia es la del veredicto)",
          _estados(_ds.cruzar_con_parquet(
              _sire_uno("20400000004", 107.71, 19.39, 127.10),
              _g_uno("20500000005", 107.77, 19.40, 127.17))),
          ["Solo SUNAT", "Solo sistema"])
    # Lo que más pasaba en los datos (31 de 34): el documento del sistema
    # ya era el par EXACTO de otra fila del SIRE —el emisor de verdad— y la
    # factura ajena se le colgaba también. Un documento del sistema
    # emparejado dos veces.
    _sire_dos = pd.concat([_sire_uno("20200000002", 200.0, 36.0, 236.0),
                           _sire_uno("20100000001")], ignore_index=True)
    _cr_dos = _ds.cruzar_con_parquet(_sire_dos, _g_uno("20200000002"))
    check("cruce: el dueño del RUC se queda con su documento y el otro "
          "emisor queda «Solo SUNAT» — el del sistema no se usa dos veces",
          sorted(zip(_cr_dos["ruc_proveedor"], _cr_dos["estado"])),
          [("20100000001", "Solo SUNAT"), ("20200000002", "Coincide")])

    # Las notas del Almacén entran al lado sistema (regla #604): una fila por
    # nota PROCESADA del rango, en negativo y con la llave de las facturas.
    _d_nc = pd.DataFrame({
        "NUM_DOCUMENTO": ["F0E001000000001"], "INDICADOR TRIBUTARIO": ["20888888888 "],
        "COD_PROVEEDOR": ["00100"], "NOMBRE_PROVEEDOR": ["CARNES SAC"],
        "FECHA_EMISION_DOC": pd.to_datetime(["2026-09-05"]),
        "TOTAL NETO": [1000.0], "TOTAL IGV": [180.0], "TOTAL DOCUMENTO": [1180.0],
        "TIPO_MONEDA": ["01"], "TIPO_CAMBIO": [3.5],
    })
    _notas_alm = pd.DataFrame({
        "NOTA CREDITO": ["N0E001000000001", "N0E001000000001", "N0E001000000002",
                         "N0E001000000003", "N0E001000000004"],
        "COD PROVEEDOR": ["00100"] * 5, "PROVEEDOR": ["CARNES SAC"] * 5,
        "ESTADO NC": ["02", "02", "01", "02", "03"],
        "FECHA NC": pd.to_datetime(["2026-09-28", "2026-09-28", "2026-09-29",
                                    "2026-08-01", "2026-09-30"]),
        "MONEDA NC": ["01", "01", "01", "01", "02"],
        "TIPO CAMBIO NC": [3.5, 3.5, 3.5, 3.5, 3.8],
        "NETO NC": [400.0, 400.0, 10.0, 20.0, 10.0],
        "TOTAL NC": [472.0, 472.0, 11.8, 23.6, 11.8],
    })
    _g_alm = _ds._parquet_agrupado_por_documento(
        _d_nc, "FECHA_EMISION_DOC", "2026-09-01", "2026-09-30", notas=_notas_alm)
    _filas_nc = _g_alm[_g_alm["base_pq"] < 0].set_index("documento")
    check("notas del Almacén: una fila por nota procesada del rango "
          "(la cabecera repetida en dos líneas cuenta una vez; sin la "
          "generada ni la de agosto)",
          sorted(_filas_nc.index), ["E001-1", "E001-4"])
    check("notas del Almacén: en negativo, IGV aparte",
          (_filas_nc.loc["E001-1", "base_pq"], _filas_nc.loc["E001-1", "igv_pq"],
           _filas_nc.loc["E001-1", "total_pq"]), (-400.0, -72.0, -472.0))
    check("notas del Almacén: la nota en dólares, a soles con SU cambio",
          round(_filas_nc.loc["E001-4", "base_pq"], 2), -38.0)
    check("notas del Almacén: el RUC sale de compras, limpio",
          _filas_nc.loc["E001-1", "ruc_pq"], "20888888888")
    check("notas del Almacén: el número crudo, para la columna del sistema",
          _filas_nc.loc["E001-1", "num_doc_pq"], "N0E001000000001")
    check("sin notas, el lado sistema es el de siempre",
          len(_ds._parquet_agrupado_por_documento(
              _d_nc, "FECHA_EMISION_DOC", "2026-09-01", "2026-09-30")), 1)

    # ── IGV como TERCERA cifra comparable (2026-08-27) ──────────────────
    # E003-2 es el caso que motivo el cambio: proveedor con TASA REDUCIDA
    # (10.5%, medido en facturas reales de TACUAREMBO S.A.C.). Cargado con
    # el 18% por defecto, la base y el total pueden seguir calzando porque
    # el error se compensa entre si -- y el documento pasaba como
    # "Coincide" con el IGV mal. Comparar las tres cifras lo destapa.
    _sire3 = pd.DataFrame({
        "documento": ["E003-1", "E003-2", "E003-3"],
        "proveedor": ["TASA NORMAL SAC", "TASA REDUCIDA SAC", "SIN IGV EN PQ SAC"],
        "ruc_proveedor": ["20111111111", "20222222222", "20333333333"],
        "fecha_emision": pd.to_datetime(["2026-08-10"] * 3),
        "base_imponible": [100.0, 200.0, 100.0],
        "no_gravado": [0.0, 0.0, 0.0],
        "igv": [18.0, 21.0, 18.0],          # 21.00 = 200 al 10.5%
        "total": [118.0, 221.0, 118.0],
        "situacion": ["Registrado"] * 3,
    })
    _g3 = pd.DataFrame({
        "documento": ["E003-1", "E003-2"],
        "ruc_pq": ["20111111111", "20222222222"],
        "proveedor_pq": ["TASA NORMAL SAC", "TASA REDUCIDA SAC"],
        "base_pq": [100.0, 200.0],
        "igv_pq": [18.0, 36.0],             # 36.00 = el 18% por defecto
        "total_pq": [118.0, 221.0],         # el total igual calza
        "fecha_pq": pd.to_datetime(["2026-08-10"] * 2),
    })
    _cruce3 = _ds.cruzar_con_parquet(_sire3, _g3)

    def _f3(doc):
        return _cruce3[(_cruce3["documento"] == doc)
                       & (_cruce3["estado"] != "Solo sistema")].iloc[0]

    check("cruce IGV · E003-1: las tres cifras calzan -> Coincide",
          _f3("E003-1")["estado"], "Coincide")
    check("cruce IGV · E003-2: base y total calzan pero el IGV no -> Diferencia",
          _f3("E003-2")["estado"], "Diferencia")
    check("cruce IGV · E003-2: dif_igv expone los 15 soles",
          _f3("E003-2")["dif_igv"], -15.0)
    check("cruce IGV · E003-2: base y total NO acusan nada",
          (_f3("E003-2")["dif_base"], _f3("E003-2")["dif_total"]), (0.0, 0.0))
    check("cruce IGV · el igv del SIRE viaja aunque no haya par",
          _f3("E003-3")["igv_sunat"], 18.0)
    # NaN y no None: pandas promueve el None a NaN al armar la columna,
    # porque las otras filas traen float. Mismo comportamiento que ya
    # tienen `base_sistema` y `total_sistema` en un "Solo SUNAT".
    check("cruce IGV · un 'Solo SUNAT' no inventa igv de sistema",
          bool(pd.isna(_f3("E003-3")["igv_sistema"])), True)
    # Parquet viejo, sin la columna: el IGV sale del veredicto en vez de
    # marcar todo como "Diferencia" por un dato que no tenemos.
    check("cruce IGV · sin columna igv_pq, el IGV no ensucia el veredicto",
          _fila("E001-1")["estado"], "Coincide")
    check("cruce IGV · sin columna igv_pq, dif_igv queda en None",
          _fila("E001-1")["dif_igv"], None)

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

    # El «Resumen del cruce» (2026-10-02; antes, la tira de estados de
    # arriba de la tabla). `_cruce` trae 3 coinciden, 1 con diferencia y 1
    # solo en SUNAT (los 5 del SIRE) más 3 solo en el sistema: 8 en total.
    check("% con un decimal (220 de 4.320)", _ds._pct_de(220, 4320), "5.1%")
    check("1 de 4.320 no se redondea a 0.0%", _ds._pct_de(1, 4320), "<0.1%")
    check("ni 4.319 de 4.320 a 100.0%", _ds._pct_de(4319, 4320), ">99.9%")
    check("todos es 100.0%", _ds._pct_de(5, 5), "100.0%")
    check("sin total no hay %", _ds._pct_de(0, 0), None)
    check("resumen del cruce: las siete barras, por nombre",
          _ds._conteos_cruce(_cruce),
          {"Total": 8, "En SUNAT": 5, "En sistema": 7, "Coinciden": 3,
           "Con diferencia": 1, "Solo SUNAT": 1, "Solo sistema": 3})
    check("resumen del cruce: los cuatro estados suman el total",
          sum(_ds._conteos_cruce(_cruce)[b] for b in
              ("Coinciden", "Con diferencia", "Solo SUNAT", "Solo sistema")),
          8)
    check("resumen del cruce: sin cruce, todo en cero",
          set(_ds._conteos_cruce(None).values()), {0})
    _ds._publicar_conteos(_cruce)
    check("el KPI del rail: a revisar es lo de SUNAT con diferencia o sin "
          "cargar; lo de fuera de SUNAT va aparte",
          _ds.st.session_state.pop("_cp_docs_cruce", None),
          {"sunat": 5, "sistema": 7, "revisar": 2, "fuera": 3,
           "fidelidad": "60.0%"})
    # La fidelidad respecto de SUNAT (regla #630): la base son los 5 del
    # SIRE, que se reparten en 3 + 1 + 1; los 3 de «Solo sistema» van
    # aparte y no suman a la base.
    _fid = _ds._fidelidad_cruce(_cruce)
    check("fidelidad: documentos, con SUNAT como base",
          _fid["doc"], {"sunat": 5, "cuadran": 3, "diferencia": 1,
                        "falta": 1, "fuera": 3})
    # En valor absoluto: las notas de crédito vienen en negativo (#604).
    _ts = pd.to_numeric(_cruce["total_sunat"], errors="coerce").fillna(0).abs()
    _tq = pd.to_numeric(_cruce["total_sistema"], errors="coerce").fillna(0).abs()
    check("fidelidad: los soles de la base son los de SUNAT",
          round(_fid["soles"]["sunat"], 2),
          round(float(_ts[_cruce["estado"] != "Solo sistema"].sum()), 2))
    check("fidelidad: los soles de fuera son los del sistema",
          round(_fid["soles"]["fuera"], 2),
          round(float(_tq[_cruce["estado"] == "Solo sistema"].sum()), 2))
    check("fidelidad: los tres tramos suman la base, en soles",
          round(sum(_fid["soles"][k] for k in ("cuadran", "diferencia",
                                               "falta")), 2),
          round(_fid["soles"]["sunat"], 2))
    _con_nota = pd.DataFrame({
        "estado": ["Coincide", "Solo SUNAT", "Solo SUNAT"],
        "total_sunat": [100.0, 50.0, -30.0], "total_sistema": [100.0, None, None]})
    check("fidelidad: una nota de crédito sin cargar suma a lo que falta, "
          "no resta",
          _ds._fidelidad_cruce(_con_nota)["soles"]["falta"], 80.0)
    check("fidelidad: sin cruce, todo en cero",
          _ds._fidelidad_cruce(None)["doc"],
          {"sunat": 0, "cuadran": 0, "diferencia": 0, "falta": 0, "fuera": 0})
    # Las barras: HTML con los tres tramos y el de fuera, sin romperse con
    # un período vacío.
    _per = [{"edad": 1, "rango": "1 ene – 2 oct 2025", "anio": "2025",
             "f": _ds._fidelidad_cruce(None)},
            {"edad": 0, "rango": "1 ene – 2 oct 2026", "f": _fid}]
    _html = _ds._barras_fidelidad(_per, "doc")
    check("barras de fidelidad: un tramo por caso con datos",
          (_html.count("sunat-fid-tramo cuadran"),
           _html.count("sunat-fid-tramo diferencia"),
           _html.count("sunat-fid-tramo falta")), (1, 1, 1))
    check("barras de fidelidad: el período sin SUNAT lo dice",
          "SUNAT no tiene documentos" in _html, True)
    check("comparar con el año pasado corre el MISMO rango un año",
          _ds._rango_hace(_dt.date(2026, 9, 3), _dt.date(2026, 10, 2), 1),
          (_dt.date(2025, 9, 3), _dt.date(2025, 10, 2)))
    check("el 29 de febrero cae en el 28",
          _ds._rango_hace(_dt.date(2024, 2, 29), _dt.date(2024, 3, 5), 1)[0],
          _dt.date(2023, 2, 28))

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

    # ── El mosaico (regla #610) ─────────────────────────────────────────
    # «Una pared mal pintada»: escala continua estirada por una hora con
    # evento, rayado gris en filas alternas y cuadrícula encima. Ahora el
    # aire entre celdas es el ÚNICO separador —sin shapes de cuadrícula ni
    # de rayado—, y la hora sin ventas va en su propia capa gris, sólo
    # dentro de los paneles (no en el hueco entre ellos).
    import numpy as _np
    _fig_rej = _vh._fig_mapa([_cd_eje, _cd_eje], [(2026, 32), (2026, 33)],
                             "Semana", "venta", [], [19, 21])
    check("horario · el mosaico no dibuja cuadrícula ni rayado",
          [s.type for s in _fig_rej.layout.shapes], [])
    _hm = [t for t in _fig_rej.data if t.type == "heatmap"]
    check("horario · el aire entre celdas es el separador",
          {(t.xgap, t.ygap) for t in _hm},
          {(_vh._GAP_CELDA, _vh._GAP_CELDA)})
    check("horario · la hora sin ventas tiene su capa (2×7×2 − 4 con dato)",
          int(_np.isfinite(_np.array(_hm[0].z, dtype=float)).sum()), 24)
    check("horario · el puente de JS sabe cuántas columnas hay",
          _fig_rej.layout.meta["vh_cols"], 15)
    # Los tonos: quintiles redondeados a dos cifras, y una hora con evento
    # NO estira la escala (era el bug de la «blues» continua).
    check("horario · los cortes son los quintiles redondeados",
          _vh._cortes_tramos(_np.arange(1, 101, dtype=float)),
          [21.0, 41.0, 60.0, 80.0])
    check("horario · un evento de S/ 100.000 no estira los cortes",
          max(_vh._cortes_tramos(list(range(1, 101)) + [100_000])) < 100,
          True)
    check("horario · cortes repetidos quedan uno (menos tonos, no iguales)",
          _vh._cortes_tramos([5.0] * 50), [5.0])
    check("horario · la leyenda de los tonos",
          _vh._rotulos_tramos([300.0, 800.0], "venta"),
          ["< 300", "300–800", "≥ 800"])
    check("horario · con tres tonos, el más alto es el más oscuro",
          _vh._idx_tramos(3), [0, 2, 4])
    check("horario · la cifra corta de la celda",
          [_vh._fmt_celda(v, "venta") for v in
           (850, 999.6, 2548, 12_000, 1_300_000, -300)],
          ["850", "1k", "2.5k", "12k", "1.3M", "−300"])
    check("horario · el ticket va sin decimales y la resta con signo",
          (_vh._fmt_celda(115.8, "ticket"),
           _vh._fmt_celda(1200, "venta", signo=True)), ("116", "+1.2k"))
    # La cifra en la celda: una capa de texto, tinta azul sobre los tonos
    # claros y blanco sobre los oscuros; sin ella si no se pide o si la
    # columna no tiene el ancho (dos meses enteros sin deslizar: 63
    # columnas en el ancho estimado).
    from tema import BLANCO as _BL, MAPA_TINTA as _TINTA
    _txt = [t for t in _fig_rej.data if t.type == "scatter" and t.mode == "text"]
    check("horario · el número va en la celda", len(_txt), 1)
    _col_txt = dict(zip(_txt[0].text, _txt[0].textfont.color)) if _txt else {}
    check("horario · tinta sobre lo claro, blanco sobre lo oscuro",
          (_col_txt.get("100"), _col_txt.get("200")), (_TINTA, _BL))
    _sin_num = _vh._fig_mapa([_cd_eje], [(2026, 32)], "Semana", "venta", [],
                             [19, 21], numeros=False)
    check("horario · sin número, no hay capa de texto",
          [t.mode for t in _sin_num.data if t.type == "scatter"
           and t.mode == "text"], [])
    _angosto = _vh._fig_mapa([_cd_eje, _cd_eje], [(2026, 7), (2026, 8)],
                             "Mes", "venta", [], [19, 21])
    check("horario · si la columna es angosta, el número no se escribe",
          [t.mode for t in _angosto.data if t.type == "scatter"
           and t.mode == "text"], [])
    # «Puntos»: sin heatmap, y las horas en SU orden aunque la primera capa
    # que las nombra sea la de las horas sin ventas (salían 12 pm, 4 pm…).
    _pts = _vh._fig_mapa([_cd_eje], [(2026, 32)], "Semana", "venta", [],
                         [19, 21], forma="Puntos")
    check("horario · en puntos no hay heatmap",
          [t.type for t in _pts.data if t.type == "heatmap"], [])
    check("horario · y las horas van en su orden",
          list(_pts.layout.yaxis.categoryarray), ["7 pm", "9 pm"])
    _tam = [t for t in _pts.data if t.type == "scatter"
            and t.mode == "markers" and t.hoverinfo == "skip"
            and t.customdata is None and len(t.x) == 2]
    check("horario · el punto más grande es la hora que más vendió",
          (list(_tam[0].marker.size)[0] < list(_tam[0].marker.size)[1])
          if _tam else False, True)
    # Los totales al margen: una tablita por hora —lo que mide el mapa con
    # su barra, los clientes y el ticket— y una barra por columna, en ejes
    # que COMPARTEN el de las horas y el de las columnas con el mapa; abajo,
    # el total del período. El ticket se divide, no se suma; con
    # «Diferencia» no hay totales.
    _tot = _vh._fig_mapa([_cd_eje], [(2026, 32)], "Semana", "venta", [],
                         [19, 21], totales=True)
    _bh = [t for t in _tot.data if t.type == "bar" and t.orientation == "h"]
    _bc = [t for t in _tot.data if t.type == "bar" and t.orientation != "h"]
    check("horario · la barra de cada hora, sobre las mismas filas",
          (list(_bh[0].x), _bh[0].yaxis, _tot.layout.xaxis2.anchor)
          if _bh else None, ([0.5, 1.0], "y", "y"))
    _cols_tot = [list(t.text) for t in _tot.data
                 if t.type == "scatter" and t.mode == "text"
                 and t.xaxis == "x2"]
    check("horario · por hora: venta, clientes y ticket",
          _cols_tot, [["S/ 100", "S/ 200"], ["2", "4"], ["S/ 50", "S/ 50"]])
    check("horario · y abajo, el total del período",
          [a.text for a in _tot.layout.annotations
           if a.yref == "y3 domain" and a.xref == "x2"],
          ["<b>S/ 300</b>", "<b>6</b>", "<b>S/ 50</b>"])
    check("horario · total por columna debajo, sobre las mismas columnas",
          (list(_bc[0].y)[:2], _bc[0].xaxis, _tot.layout.yaxis3.anchor)
          if _bc else None, ([100.0, 200.0], "x", "x"))
    check("horario · las filas le dejan sitio a la tira de abajo",
          _tot.layout.yaxis.domain[0] > 0, True)
    _tk = _vh._fig_mapa([_cd_eje], [(2026, 32)], "Semana", "ticket", [],
                        [19, 21], totales=True)
    check("horario · el ticket por hora es venta ÷ clientes, sin repetirlo",
          [list(t.text) for t in _tk.data if t.type == "scatter"
           and t.mode == "text" and t.xaxis == "x2"],
          [["S/ 50", "S/ 50"], ["2", "4"]])
    _td = _vh._fig_mapa([_cd_eje, _cd_eje], [(2026, 32), (2026, 33)],
                        "Semana", "venta", [], [19, 21], dif=True,
                        totales=True)
    check("horario · con «Diferencia» no hay totales",
          [t.type for t in _td.data if t.type == "bar"], [])
    check("horario · los totales suman alto y ancho al deslizable",
          (_vh._alto_mapa(10, totales=True) > _vh._alto_mapa(10),
           _vh._ancho_desliza(10, True) - _vh._ancho_desliza(10)),
          (True, _vh._PX_TOT_HORA))

    # ── Capa de selección ───────────────────────────────────────────────
    # Un punto por CELDA, haya venta o no. Si vuelve a haberlos sólo donde
    # hay datos: un arrastre sobre celdas vacías no devuelve nada, Streamlit
    # no ve cambio, no hay rerun, y el rectángulo punteado de Plotly se
    # queda dibujado para siempre (pasó, 2026-08-15). Además la marca se
    # encogería en silencio hasta el último día con venta.
    _sel_pts = [t for t in _fig_rej.data
                if t.type == "scatter" and t.hoverinfo == "skip"
                and t.customdata is not None]
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

    # El arranque es UN panel: el mes EN CURSO, que sale del rango con que
    # abre el selector de fecha de la vista —del 1 al último día con datos—.
    # Cortado por ESE día sigue siendo el mes entero, como siempre fue.
    _D = _dt.date
    check("horario · el mes en curso es UN panel entero",
          _vh._paneles_del_rango(_D(2026, 8, 1), _D(2026, 8, 14), "Mes",
                                 _D(2026, 8, 14)), [(2026, 8)])

    # EL RANGO SE PARTE POR LA GRANULARIDAD (regla #531): «últimos 30 días»
    # en Mes son dos paneles, y el primero es un TROZO de agosto que no
    # dibuja los 25 días que no tiene (se leerían como días sin venta).
    _p30 = _vh._paneles_del_rango(_D(2026, 8, 26), _D(2026, 9, 24), "Mes",
                                  _D(2026, 9, 24))
    check("horario · rango partido: un trozo + el mes en curso",
          [_vh._base_clave(k) for k in _p30], [(2026, 8), (2026, 9)])
    check("horario · el trozo se llama por sus días",
          _vh._etiqueta_clave(_p30[0], "Mes"), "26–31 Ago 26")
    check("horario · el selector escribe el rango corto",
          [_vh._fmt_rango_corto(_D(2026, 9, 1), _D(2026, 9, 24)),
           _vh._fmt_rango_corto(_D(2026, 8, 26), _D(2026, 9, 24)),
           _vh._fmt_rango_corto(_D(2025, 12, 28), _D(2026, 1, 3))],
          ["1–24 set 2026", "26 ago – 24 set 2026",
           "28 dic 2025 – 3 ene 2026"])
    check("horario · el trozo no dibuja los días que no tiene",
          _vh._columnas(_p30[0], "Mes"),
          (6, ["26", "27", "28", "29", "30", "31"]))
    check("horario · la columna 0 del trozo es su primer día",
          _vh._fecha_de_columna(_p30[0], "Mes", 0), _D(2026, 8, 26))
    check("horario · cortado por el RANGO (no por los datos) es un trozo",
          isinstance(_vh._paneles_del_rango(_D(2026, 9, 1), _D(2026, 9, 20),
                                            "Mes", _D(2026, 9, 24))[0],
                     _vh._Tramo), True)
    _dft = pd.DataFrame({
        "F": pd.to_datetime(["2026-08-26 20:00", "2026-08-31 13:00",
                             "2026-08-10 13:00"]),
        "V": [1.0, 2.0, 3.0]})
    check("horario · el trozo cuenta sus columnas desde su primer día",
          _vh._prep_tramo(_dft, {"fecha": "F", "venta": "V"}, "Mes",
                          _D(2026, 8, 26), _D(2026, 8, 31))["col"].tolist(),
          [0, 5])
    _psem = _vh._paneles_del_rango(_D(2026, 9, 1), _D(2026, 9, 24), "Semana",
                                   _D(2026, 9, 24))
    check("horario · un mes en Semana son cuatro paneles", len(_psem), 4)
    check("horario · la semana que el rango abre en martes arranca en Mar",
          _vh._columnas(_psem[0], "Semana")[1][0], "Mar")
    _ap = _vh._ano_pasado(_psem[0], "Semana")
    check("horario · año pasado en Semana: el mismo día de SEMANA",
          (_ap.desde.weekday(), _ap.hasta.weekday()),
          (_psem[0].desde.weekday(), _psem[0].hasta.weekday()))
    check("horario · año pasado en Mes: la misma fecha, trozo con trozo",
          _vh._ano_pasado(_p30[0], "Mes"),
          _vh._Tramo((2025, 8), _D(2025, 8, 26), _D(2025, 8, 31)))
    check("horario · año pasado de un mes entero es el mes entero",
          _vh._ano_pasado((2026, 9), "Mes"), (2025, 9))
    # «Diferencia» resta la misma columna del CALENDARIO: un panel base que
    # arranca el martes pone su martes en la columna 0, y la semana entera
    # de al lado lo tiene en la 1. Martes contra martes da +50.
    def _celda(col, v):
        return pd.DataFrame({"col": [col], "hora": [19], "venta": [v],
                             "cant": [0.0], "desc": [0.0], "pax": [0.0],
                             "ticket": [float("nan")]})
    _fg = _vh._fig_mapa([_celda(0, 100.0), _celda(1, 150.0)],
                        [_psem[0], (2026, 37)], "Semana", "venta", [], [19],
                        dif=True)
    _cds = [c for t in _fg.data
            if getattr(t, "customdata", None) is not None
            and len(t.customdata) and len(t.customdata[0]) > 9
            for c in t.customdata]
    check("horario · la diferencia resta martes contra martes",
          [c[-1] for c in _cds if c[0] == 1],
          ["<br><b>Δ vs 1–6 Sep 26: +S/ 50</b>"])

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

    # ── El calendario del eje del drill Semanal (arquitectura.md #362) ───
    # Bandas de fin de semana / feriado, punteada de separación y rótulo
    # por día. Todo se prueba contra una figura de verdad —`fig.layout`—
    # porque el valor de retorno son sólo los rótulos: las bandas y las
    # líneas se dibujan como efecto y se irían sin que nadie se entere.
    import plotly.graph_objects as _go
    import tema as _tema
    from graficos.compras import _comun as _com_compras
    from graficos.compras import semanal as _sem

    check("calendario · agrupa días contiguos, no todos los iguales",
          _sem._grupos_de_dia([
              _dt.date(2026, 8, 15), _dt.date(2026, 8, 15),
              _dt.date(2026, 8, 17), _dt.date(2026, 8, 15)]),
          [(0, 1, _dt.date(2026, 8, 15)), (2, 2, _dt.date(2026, 8, 17)),
           (3, 3, _dt.date(2026, 8, 15))])

    # La ventana de la captura del pedido: sáb 15 a jue 20 de agosto 2026,
    # con 3 documentos por día (18 barras, 6 días).
    _dias_cap = [_d for _d in (_dt.date(2026, 8, 15), _dt.date(2026, 8, 16),
                               _dt.date(2026, 8, 17), _dt.date(2026, 8, 18),
                               _dt.date(2026, 8, 19), _dt.date(2026, 8, 20))
                 for _ in range(3)]
    _figc = _go.Figure()
    _tv, _tt = _sem._calendario_del_eje(_figc, _dias_cap, sep="dia")
    check("calendario · un rótulo por día, no uno por barra", len(_tt), 6)
    # El aire entre rótulos NO es cosmético: con `_ROTULO_DIA_PX` puesto en
    # lo que el rótulo MIDE (36) y no en lo que OCUPA, la app en vivo dibujó
    # 22 rótulos en 808px y 7 pares se pisaron (#362). El paso tiene que
    # dejar al menos el ancho del rótulo de separación entre dos vecinos.
    _sep_px = (_tv[1] - _tv[0]) * _sem._LIENZO_PX / len(_dias_cap)
    check("calendario · dos rótulos vecinos no se tocan",
          _sep_px >= _sem._ROTULO_DIA_PX, True)
    _dias_mes = [_dt.date(2026, 8, 10) + _dt.timedelta(days=_i)
                 for _i in range(22)]
    _figm = _go.Figure()
    _tvm, _ttm = _sem._calendario_del_eje(_figm, _dias_mes, sep="dia")
    check("calendario · el caso medido en vivo (22 días) deja aire",
          ((_tvm[1] - _tvm[0]) * _sem._LIENZO_PX / len(_dias_mes)
           >= _sem._ROTULO_DIA_PX), True)
    check("calendario · el rótulo va CENTRADO en el tramo del día",
          _tv[0], 1.0)
    check("calendario · el rótulo dice el día de semana", _tt[0], "Sáb<br>15/08")
    _bandas = [_f for _f in _figc.layout.shapes if _f.type == "rect"]
    _lineas = [_f for _f in _figc.layout.shapes if _f.type == "line"]
    check("calendario · banda sólo en sábado y domingo", len(_bandas), 2)
    check("calendario · la banda cubre el tramo entero del día",
          (_bandas[0].x0, _bandas[0].x1), (-0.5, 2.5))
    check("calendario · una punteada por cambio de día, menos la primera",
          len(_lineas), 5)
    check("calendario · la punteada va ENTRE dos barras", _lineas[0].x0, 2.5)
    check("calendario · la punteada es punteada", _lineas[0].line.dash, "dot")

    # «Día»: la barra ya es un día, así que la punteada sube un nivel y
    # marca la semana. 15/08/2026 es sábado; el lunes cae en el índice 2.
    _figd = _go.Figure()
    _sem._calendario_del_eje(_figd, sorted(set(_dias_cap)), sep="semana")
    _lin_d = [_f for _f in _figd.layout.shapes if _f.type == "line"]
    check("calendario · en «Día» la punteada marca el LUNES, no cada día",
          [_f.x0 for _f in _lin_d], [1.5])

    # Feriado: 30/08 es Santa Rosa y además domingo. Gana el ámbar, y la
    # palabra va ARRIBA del lienzo, no como tercer renglón del rótulo —
    # medido en el navegador, ahí chocaba con el legend (#362).
    _figf = _go.Figure()
    _, _ttf = _sem._calendario_del_eje(
        _figf, [_dt.date(2026, 8, 30)], sep="dia")
    check("calendario · el rótulo del feriado sigue midiendo 2 renglones",
          _ttf[0], "Dom<br>30/08")
    check("calendario · el feriado le gana al fin de semana en el color",
          _figf.layout.shapes[0].fillcolor, _tema.ADVERTENCIA_TEXTO)
    check("calendario · «feriado» se anota arriba del lienzo",
          [(_a.text, _a.y, _a.yref) for _a in _figf.layout.annotations],
          [("feriado", 1.0, "paper")])
    check("calendario · y el margen de arriba le hace lugar al título",
          _figf.layout.margin.t, _sem._MARGEN_SUP_FERIADO)

    # Feriados SEGUIDOS (28 y 29 de julio) = una sola banda continua, así
    # que una sola palabra, centrada en la racha. Dos se pisarían.
    _figr = _go.Figure()
    _sem._calendario_del_eje(
        _figr, [_dt.date(2026, 7, 27), _dt.date(2026, 7, 28),
                _dt.date(2026, 7, 29), _dt.date(2026, 7, 30)], sep="dia")
    check("calendario · una anotación por RACHA de feriados, no por día",
          [(_a.text, _a.x) for _a in _figr.layout.annotations],
          [("feriado", 1.5)])
    check("rachas · agrupa consecutivos y corta en el hueco",
          _sem._rachas([1, 2, 5]), [(1, 2), (5, 5)])

    # Los dos umbrales: el rótulo se rinde antes que la banda.
    _n_sin_rotulo = int(_sem._LIENZO_PX / _sem._PX_MIN_DIA_ROTULO) + 5
    _figw = _go.Figure()
    _rango = [_dt.date(2026, 1, 1) + _dt.timedelta(days=_i)
              for _i in range(_n_sin_rotulo)]
    check("calendario · sin píxeles para el rótulo, devuelve None",
          _sem._calendario_del_eje(_figw, _rango, sep="dia"), None)
    check("calendario · …pero las bandas del fin de semana quedan igual",
          len(_figw.layout.shapes) > 0, True)
    _figx = _go.Figure()
    _rango_x = [_dt.date(2026, 1, 1) + _dt.timedelta(days=_i)
                for _i in range(int(_sem._LIENZO_PX / _sem._PX_MIN_DIA_BANDA)
                                + 5)]
    check("calendario · más allá del piso de la banda, no se dibuja nada",
          (_sem._calendario_del_eje(_figx, _rango_x, sep="dia"),
           len(_figx.layout.shapes)), (None, 0))

    # El Nº de documento que se MUESTRA: decodifica el del parquet y deja
    # pasar el del demo, que ya viene legible (arquitectura.md #362).
    from graficos.compras._comun import documento_legible as _doclbl
    check("documento_legible · decodifica el formato del parquet",
          _doclbl(pd.Series(["F0E001000001328"])).iloc[0], "E001-1328")
    check("documento_legible · deja pasar lo que no tiene esa forma",
          _doclbl(pd.Series(["F0001-123"])).iloc[0], "F0001-123")

    # ── Semanal: el período con nombre y la variación (regla #470) ───────
    from graficos import alturas as _alto
    # «no debe decir 2026-S37»: la semana ISO se desarma en lunes-domingo,
    # con el mes del final y, si cruza, los dos.
    check("semana · límites ISO de lunes a domingo",
          _sem._limites_periodo("2026-S38", "Semana"),
          (_dt.date(2026, 9, 14), _dt.date(2026, 9, 20)))
    check("semana · la semana 1 puede arrancar el año anterior",
          _sem._limites_periodo("2026-S01", "Semana"),
          (_dt.date(2025, 12, 29), _dt.date(2026, 1, 4)))
    check("mes · último día de diciembre sin pasarse de año",
          _sem._limites_periodo("2025-12", "Mes"),
          (_dt.date(2025, 12, 1), _dt.date(2025, 12, 31)))
    check("rótulo · semana dentro de un mes",
          _sem._rotulo_periodo("2026-S38", "Semana"),
          ("lun 14–dom 20 set", "Semana del lun 14 al dom 20 set 2026"))
    check("rótulo · semana que cruza de mes",
          _sem._rotulo_periodo("2026-S36", "Semana"),
          ("lun 31 ago–dom 6 set", "Semana del lun 31 ago al dom 6 set 2026"))
    # LA SEMANA QUE EL RANGO CORTA SE NOMBRA POR SUS DÍAS (regla #619): con
    # el selector en «1 ago – 7 oct» la primera barra suma sólo el sábado 1 y
    # el domingo 2, y decía «27 jul–2 ago».
    _r619 = (_dt.date(2026, 8, 1), _dt.date(2026, 10, 7))
    check("rótulo · semana cortada al principio: sus días",
          _sem._rotulo_periodo("2026-S31", "Semana", _r619),
          ("sáb 1–dom 2 ago",
           "Del sáb 1 al dom 2 ago 2026 · la semana del lun 27 jul al dom 2 "
           "ago 2026 queda cortada por las fechas"))
    check("rótulo · semana cortada al final",
          _sem._rotulo_periodo("2026-S41", "Semana", _r619)[0],
          "lun 5–mié 7 oct")
    check("rótulo · semana entera dentro del rango: igual que sin rango",
          _sem._rotulo_periodo("2026-S36", "Semana", _r619),
          _sem._rotulo_periodo("2026-S36", "Semana"))
    check("rótulo · un solo día de la semana",
          _sem._rotulo_periodo("2026-S31", "Semana",
                               (_dt.date(2026, 8, 2), _dt.date(2026, 9, 1)))[0],
          "dom 2 ago")
    check("rótulo · semana que cruza de año lleva los dos años",
          _sem._rotulo_periodo("2026-S01", "Semana")[1],
          "Semana del lun 29 dic 2025 al dom 4 ene 2026")
    check("rótulo · el año debajo de la semana, doble si cruza",
          (_sem._anio_semana("2026-S38"), _sem._anio_semana("2026-S01")),
          ("2026", "2025-26"))
    check("rótulo · mes en palabras, no «2026-09»",
          _sem._rotulo_periodo("2026-09", "Mes"), ("set 2026", "Set 2026"))

    # La variación NO se calcula contra un período cortado: con el rango del
    # mes corrido (20 ago – 18 set) la primera y la última semana están a
    # medias, y la segunda compara contra una a medias.
    _rg = (_dt.date(2026, 8, 20), _dt.date(2026, 9, 18))
    _sems = ["2026-S34", "2026-S35", "2026-S36", "2026-S37", "2026-S38"]
    _vs = _sem._variaciones(_sems, [17.9, 31.2, 32.1, 33.8, 18.7],
                            "Semana", _rg)
    check("variación · estados con las dos puntas cortadas",
          [_v[0] for _v in _vs],
          ["parcial", "ant_parcial", "ok", "ok", "parcial"])
    check("variación · contra la barra anterior, en %",
          round(_vs[3][1], 1), round((33.8 - 32.1) / 32.1 * 100, 1))
    check("variación · cobertura de la semana en curso",
          _com_compras._cobertura("2026-S38", "Semana", _rg), (5, 7))
    check("variación · sin rango conocido nada es parcial",
          [_v[0] for _v in _sem._variaciones(_sems[:2], [1, 2], "Semana",
                                             None)],
          ["primera", "ok"])
    check("variación · contra cero no hay porcentaje",
          _sem._variaciones(["2026-09-14", "2026-09-15"], [0, 5], "Día",
                            None)[1][0], "sin_base")
    check("variación · formato: signo, decimal bajo 10 %, rojo si sube",
          (_sem._fmt_variacion(4.66), _sem._fmt_variacion(-143.2),
           _sem._fmt_variacion(0.04)[0]),
          (("+4.7%", _tema.ERROR), ("−143%", _tema.EXITO), "0%"))

    # Los renglones de la etiqueta: total, docs debajo, y la variación sólo
    # en Día/Semana/Mes. En «Por documento» ni docs ni variación.
    check("etiqueta · tres renglones en Semana",
          [_p for _p, _ in _sem._renglones_etiqueta(
              "S/ 33.8k", 45, ("ok", 5.1, 2), "Semana")],
          ["S/ 33.8k", "45 docs", "+5.1%"])
    check("etiqueta · la parcial dice «parcial», no un porcentaje",
          [_p for _p, _ in _sem._renglones_etiqueta(
              "S/ 18.7k", 28, ("parcial", None, 3), "Semana")][-1],
          "parcial")
    check("etiqueta · Año lleva docs pero no variación",
          [_p for _p, _ in _sem._renglones_etiqueta(
              "S/ 2.0M", 4413, ("ok", 3.0, 0), "Año")],
          ["S/ 2.0M", "4,413 docs"])
    check("etiqueta · «Por documento» sólo el total",
          [_p for _p, _ in _sem._renglones_etiqueta(
              "S/ 900", 1, None, "Por documento")], ["S/ 900"])

    # El plan: cuántos renglones entran y de qué forma. Los tres casos que
    # se vieron en los PNG de `ver_figura.py` (2026-09-19).
    _r3 = [["S/ 33.8k", "45 docs", "+5.1%"]] * 5
    check("plan · 5 semanas: derecha con los tres renglones",
          _sem._plan_etiquetas(5, _r3, _alto.SEMANAL_SOLO)[:2],
          ("derecha", 3))
    _r3d = [["S/ 13.3k", "16 docs", "+446%"]] * 28
    check("plan · 28 días: una sola línea girada con los tres",
          _sem._plan_etiquetas(28, _r3d, _alto.SEMANAL_SOLO)[:2],
          ("unida", 3))
    _fk, _kk, _ak = _sem._plan_etiquetas(28, _r3d, _alto.COMPACTO)
    check("plan · con el detalle abierto se cae lo que no entra",
          (_fk, _kk), ("girada", 1))
    check("plan · y nunca se pasa del techo del área de trazo",
          _ak <= _sem._alto_area_trazo(_alto.COMPACTO) * _sem._ETQ_TECHO,
          True)
    check("plan · 263 documentos: nada, queda en el hover",
          _sem._plan_etiquetas(263, [["S/ 900"]] * 263,
                               _alto.SEMANAL_SOLO)[0], None)

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
    # LA CLAVE POR CATEGORÍA LLEVA EL REPORTE desde el 2026-09-08. Antes era
    # `ajuste_rango_aplicado_{categoria}` y no colisionaba sólo porque el
    # único reporte con categorías era Ajuste; Compras adoptó una categoría
    # por sección de su pila y dos reportes con la misma categoría habrían
    # compartido rango sin que nada lo detectara.
    check("clave_rango por categoría",
          clave_rango("Ajuste de Inventario", False, categoria="tiempo"),
          "rango_cat_Ajuste de Inventario_tiempo")
    check("clave_rango por categoría separa REPORTES",
          clave_rango("Compras", False, categoria="tiempo")
          != clave_rango("Ajuste de Inventario", False, categoria="tiempo"),
          True)
    check("clave_rango por categoría separa CATEGORÍAS",
          clave_rango("Compras", False, categoria="sec_proveedor")
          != clave_rango("Compras", False, categoria="sec_semanal"),
          True)
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


def _pruebas_css_comentarios_cerrados():
    """Un comentario de CSS cerrado antes de tiempo se lleva una regla ENTERA.

    Encontrado el 2026-09-17 en `graficos/compras/_css_proveedor.py`: un
    comentario largo se cerraba con `*/` a mitad de camino, el párrafo
    siguiente quedaba afuera como si fuera un selector —terminado en el
    `*/` del final—, y el navegador descartaba la regla que venía pegada
    (`.st-key-cp_sem_fila { flex-wrap: wrap }`). Sin error ni aviso: la
    cabecera de Semanal apretaba en vez de bajar de renglón, y un comentario
    en el mismo fichero juraba lo contrario. Regla #454.

    La forma se caza sin parsear CSS: se borran los comentarios bien
    cerrados y se busca un `*/` que haya quedado suelto. Barre todo `<style>`
    escrito en Python.
    """
    import pathlib
    import re

    fallos = 0
    raiz = pathlib.Path(__file__).parent
    fuentes = ([raiz / "app.py"] + sorted((raiz / "estilos").glob("*.py"))
               + sorted((raiz / "graficos").rglob("*.py"))
               + sorted((raiz / "tablas").rglob("*.py")))
    sueltos = []
    for f in fuentes:
        txt = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<style>(.*?)</style>", txt, re.S):
            sin = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
            for r in re.finditer(r"\*/", sin):
                previo = sin[:r.start()].rstrip().splitlines()[-1:] or [""]
                sueltos.append(f"{f.relative_to(raiz)}: …{previo[0][-60:]}")
    if sueltos:
        fallos += 1
        print("FALLA css · comentario cerrado antes de tiempo (la regla que "
              "le sigue no existe para el navegador):")
        for s_ in sueltos:
            print(f"      {s_}")
    else:
        print("OK    css · ningún comentario cerrado antes de tiempo")
    return fallos


def _pruebas_has_solo_clases():
    """Adentro de un `:has()` sólo van clases. Regla #469.

    Reportado el 2026-09-18 como «al hacer clic a veces se queda pasmada».
    Medido: un clic congelaba la página 10,5 s seguidos, y la causa era el
    CSS — con 142 reglas `:has()`, cambiar UNA clase en cualquier elemento
    costaba ~100 ms de recálculo de estilos, y un rerun cambia cientos. Lo
    que lo dispara no es el `:has()` sino lo que lleva ADENTRO: un atributo
    (`[class*=...]`, `[data-testid=...]`, `[title=...]`) o una pseudo-clase
    (`:hover`, `:checked`) hacen que el navegador lo re-evalúe ante cada
    cambio de clase o cada inserción de la página entera. Una clase sola
    no: sólo cuando cambia ESA clase. Medido: `:root:has(.X) .Y` 7 ms por
    inserción, `:root:has(.X:hover) .Y` 80 ms.

    Y no es aditivo, que es lo que hace falta esta guarda: una regla que
    sola cuesta 3 ms puede ser la que DISPARA el recálculo que pagan las
    demás. Revisarlas de a una en el navegador no lo ve.

    Segunda comprobación, de la misma cura: el piso de alto de
    `estilos/_80_cards.py` enumera sus tarjetas por key EXACTA (antes iban
    por prefijo, con un `[class*=...]` adentro del `:has()`), así que una
    tarjeta nueva de esas familias que no se sume a la lista vuelve callada
    al escalón. La salida es declarada: una tarjeta que no comparte fila
    lleva `fuera-del-piso: <key>` en `_80_cards.py`, al lado de la regla que
    explica por qué.
    """
    import pathlib
    import re

    fallos = 0
    raiz = pathlib.Path(__file__).parent
    fuentes = ([raiz / "app.py", raiz / "navegacion.py", raiz / "asistente.py"]
               + sorted((raiz / "estilos").glob("*.py"))
               + sorted((raiz / "graficos").rglob("*.py"))
               + sorted((raiz / "tablas").rglob("*.py")))
    etiquetas = r"(?:div|span|p|a|button|input|label|svg|li|ul)"
    malos = []
    for f in fuentes:
        txt = f.read_text(encoding="utf-8")
        txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)            # CSS
        txt = re.sub(r"(?m)^\s*#.*$", "", txt)                     # Python
        i = 0
        while (i := txt.find(":has(", i)) != -1:
            j, d = i + 5, 1
            while j < len(txt) and d:
                d += (txt[j] == "(") - (txt[j] == ")")
                j += 1
            arg = txt[i + 5:j - 1]
            if ("[" in arg or re.search(r":[a-z-]+", arg)
                    or re.search(rf"(^|[\s>+~,(]){etiquetas}(?=[\[.:#\s),]|$)",
                                 arg)):
                linea = txt.count("\n", 0, i) + 1
                malos.append(f"{f.relative_to(raiz)}:{linea}  "
                             f":has({' '.join(arg.split())[:80]})")
            i = j
    if malos:
        fallos += 1
        print("FALLA css · :has() con algo que no es una clase adentro "
              "(recalcula la página entera en cada cambio, regla #469):")
        for m_ in malos:
            print(f"      {m_}")
    else:
        print("OK    css · todo :has() lleva sólo clases adentro")

    cards = (raiz / "estilos" / "_80_cards.py").read_text(encoding="utf-8")
    familias = ("compras_prov_card_", "sunat_card_", "sunat_conv_",
                "compras_prod_card_", "compras_vol_card_",
                "compras_vap_card_")
    faltan = []
    for f in sorted((raiz / "graficos").rglob("*.py")):
        for k in re.findall(r'key="((?:%s)\w+)"' % "|".join(familias),
                            f.read_text(encoding="utf-8")):
            # `fuera-del-piso: <key>` es la salida declarada, y pide un
            # motivo al lado: una tarjeta que NO comparte fila no tiene
            # nada que igualar, así que sumarla al `:has()` sería un
            # selector que no matchea nunca — una regla que miente. La
            # marca vive en `_80_cards.py`, junto a la regla que la
            # explica, con el mismo criterio que `# columnas-internas:`.
            if (f".st-key-{k}," not in cards and f".st-key-{k})" not in cards
                    and f"fuera-del-piso: {k}" not in cards):
                faltan.append(f"{k} ({f.relative_to(raiz)})")
    if faltan:
        fallos += 1
        print("FALLA css · tarjeta de una familia del piso de alto que no está "
              "enumerada en _80_cards.py (vuelve al escalón):")
        for k in faltan:
            print(f"      {k}")
    else:
        print("OK    css · el piso de alto enumera todas sus tarjetas")
    return fallos


def _pruebas_css_sin_prosa_suelta():
    """Ningún párrafo de comentario queda FUERA del `/* … */`. Regla #534.

    Gemela de `_pruebas_css_comentarios_cerrados`, y cubre lo que aquélla
    no mira: esa barre bloques `<style>…</style>` enteros dentro de UN
    fichero, y los módulos de `estilos/` no tienen ninguno (`_00_base` abre
    la etiqueta y `_99_movil` la cierra). O sea que los 500 KB del CSS
    global nunca pasaron por ella.

    Encontrado el 2026-09-25 en `_28_arbol.py`: tres renglones de un
    comentario habían quedado entre dos reglas, sin `/*`. El navegador los
    leyó como el principio del selector siguiente y descartó la regla
    —el `scroll-margin-top` de las secciones de la pila— desde el día en
    que nació. Sin error: un selector inválido sólo invalida su regla.

    La prosa se reconoce sin parsear CSS: después de borrar comentarios y
    strings, un acento, una `ñ`, un `¿` o un backtick no pueden estar en un
    selector ni en una declaración. Medido contra el CSS entero: el único
    hallazgo era ese párrafo.
    """
    import pathlib
    import re
    import estilos

    raiz = pathlib.Path(__file__).parent
    bloques = [("estilos.get_css()", estilos.get_css())]
    for f in (sorted((raiz / "graficos").rglob("*.py"))
              + sorted((raiz / "tablas").rglob("*.py"))
              + [raiz / "app.py", raiz / "navegacion.py", raiz / "asistente.py"]):
        txt = f.read_text(encoding="utf-8")
        for m in re.finditer(r"<style>(.*?)</style>", txt, re.S):
            # Un `<style>` nombrado en un comentario se empareja con el
            # `</style>` de más abajo y el tramo es PYTHON, no CSS: se
            # descarta el que nace en un comentario o cruza un docstring o
            # un comentario de Python.
            inicio = txt[txt.rfind("\n", 0, m.start()) + 1:m.start()]
            if ("#" in inicio or '"""' in m.group(1) or "'''" in m.group(1)
                    or re.search(r"(?m)^\s*#", m.group(1))):
                continue
            bloques.append((str(f.relative_to(raiz)), m.group(1)))
    prosa = []
    for origen, css in bloques:
        sin = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        sin = re.sub(r"\"[^\"\n]*\"|'[^'\n]*'", '""', sin)
        for linea in sin.splitlines():
            if "*/" in linea or "`" in linea or re.search(r"[áéíóúñÁÉÍÓÚÑ¿¡]", linea):
                prosa.append(f"{origen}: {linea.strip()[:90]}")
    if prosa:
        print("FALLA css · texto fuera de un comentario (el navegador lo lee "
              "como selector y descarta la regla que sigue, regla #534):")
        for p in prosa:
            print(f"      {p}")
        return 1
    print(f"OK    css · ningún párrafo fuera de un comentario "
          f"({len(bloques)} bloques, CSS global incluido)")
    return 0


def _pruebas_has_de_streamlit():
    """Las `:has()` caras del CSS de STREAMLIT se sacan en runtime. Regla #532.

    Nuestro CSS lo vigila `_pruebas_has_solo_clases`; el de Streamlit no se
    puede editar, y trae dos (el separador de `st.segmented_control`) que
    hacían costar ~115 ms cada inserción y cada hover de la página. Las saca
    `inyecciones/css_streamlit.py`, y acá se fija su criterio contra las
    dos reglas reales —copiadas de la hoja de emotion de la 1.59— y contra
    las `:has()` de Streamlit que NO cuestan y tienen que quedar.
    """
    from inyecciones.css_streamlit import es_has_caro
    import pathlib

    fallos = 0
    caras = (
        '.st-emotion-cache-o7wst4:not([data-selected]):not([data-disabled])'
        ':has(+ button[data-variant="segmented_control"][data-selected]'
        ':not([data-disabled]))',
        '.st-emotion-cache-o7wst4:not([data-selected]):not([data-disabled])'
        ':not([data-hovered]):not([data-focus-visible])'
        ':has(+ button[data-variant="segmented_control"]:not([data-disabled])'
        ':is([data-hovered], [data-focus-visible]))',
        '.x:has(> .y:hover)',
        # la del multiselect de la 1.64, como la escribe emotion
        '.e1kig3hy10:not(:has([data-focused])):not(:has([data-hovered])) '
        "[role='option'][aria-posinset='1'] [data-item-hl]",
    )
    baratas = (
        # anillo de foco del deslizador: estaba en la página medida
        '.st-emotion-cache-igqoeg:focus-within:has(:focus-visible)',
        '.st-emotion-cache-abc:has(> .stCheckbox)',
        '.st-emotion-cache-abc:not([data-disabled]):has(+ .e1x2y3)',
        '.st-emotion-cache-abc:has(.stTooltipIcon) [data-testid="x"]',
    )
    malas = ([s for s in caras if not es_has_caro(s)]
             + [s for s in baratas if es_has_caro(s)])
    if malas:
        fallos += 1
        print("FALLA css · el criterio de css_streamlit.py clasifica mal:")
        for s in malas:
            print(f"      {s[:100]}")
    else:
        print("OK    css · css_streamlit.py reconoce las :has() caras de "
              "Streamlit y deja las baratas")

    app = (pathlib.Path(__file__).parent / "app.py").read_text(encoding="utf-8")
    if ("from inyecciones.css_streamlit import neutralizar_has_streamlit" not in app
            or "\nneutralizar_has_streamlit()" not in app):
        fallos += 1
        print("FALLA css · app.py no llama a neutralizar_has_streamlit() "
              "importándola del SUBMÓDULO (regla #357)")
    else:
        print("OK    css · app.py neutraliza las :has() de Streamlit en cada corrida")
    return fallos


def _pruebas_encaje_pila():
    """El encaje de la pila no puede esconder nada. Regla #533.

    Con `scroll-snap-type: y mandatory`, lo que está en el flujo y no es un
    punto de encaje no se puede dejar a la vista. Dos trampas, las dos con
    un aviso de por medio: el de datos viejos va ARRIBA de la pila (tiene
    que ser punto de encaje, o la página salta por encima y no deja volver),
    y en una página SIN pila sería el único punto (el encaje tiene que venir
    apagado, o esa página no se podría bajar). Por eso el tipo de encaje va
    en una variable que publica el rail sólo cuando dibuja la pila.
    """
    import pathlib
    import re

    fallos = 0
    raiz = pathlib.Path(__file__).parent
    pila = (raiz / "estilos" / "_27_pila.py").read_text(encoding="utf-8")
    pila = re.sub(r"/\*.*?\*/", "", pila, flags=re.S)
    base = (raiz / "graficos" / "base.py").read_text(encoding="utf-8")
    faltas = []
    if "scroll-snap-type: var(--pila-encaje, none)" not in pila:
        faltas.append("el encaje de .stMain no cuelga de --pila-encaje (vendría "
                      "prendido en páginas sin pila)")
    if not re.search(r"\.st-key-aviso_dato_viejo\s*\{\s*scroll-snap-align: start",
                     pila):
        faltas.append("el aviso de datos viejos no es punto de encaje (quedaría "
                      "escondido arriba de la pila)")
    if not re.search(r"if not _fuera:\s*\n\s*st\.markdown\(\"<style>:root "
                     r"\{ --pila-encaje: y mandatory; \}", base):
        faltas.append("base.py::_render_rail no publica --pila-encaje sólo "
                      "cuando dibuja la pila")
    if faltas:
        fallos += 1
        print("FALLA css · encaje de la pila:")
        for f_ in faltas:
            print(f"      {f_}")
    else:
        print("OK    css · el encaje sólo se prende con pila y el aviso es punto "
              "de encaje")
    return fallos


def _pruebas_widgets_de_fragment_escalado():
    """Un `st.rerun` al tope de un fragment le borra el estado a SUS widgets.

    Reportado el 2026-09-09 sobre «Compra por período»: se elegía «Por
    documento», se movía la fecha de la cabecera, y el gráfico volvía a
    semanas — con la píldora «Por documento» todavía marcada. Es la regla
    #211 (la escala de tiempo volviendo sola a «Días») pero sobre la
    tarjeta entera: el `st.rerun(scope="app")` que escala el gesto a la app
    (regla #180) aborta la corrida antes de que los controles se
    registren, y Streamlit recolecta el estado de todo widget de ESE
    fragment que no se dibujó. La cura es `base.py::preservar_widgets`, y
    la regla nueva es la #373.

    LO QUE ESTA GUARDA CUBRE es lo único que no se ve venir: alguien
    agrega un control a una tarjeta que escala —o copia una cabecera para
    hacer la tarjeta siguiente— y el control se resetea solo cada vez que
    se toca la fecha. No da error y no deja traza: la vista aparece en su
    default, y en pantalla el widget sigue marcando lo otro (el navegador
    conserva su valor, regla #212).

    El barrido es por `ast` y mira TODO el repo, no una lista de módulos:
    lo que se busca es la FORMA —un `st.rerun` y, más abajo en la misma
    función, un widget con `key`— y esa forma puede aparecer en cualquier
    dashboard nuevo.
    """
    import ast
    import pathlib

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    widgets tras rerun · {nombre}")
        else:
            fallos += 1
            print(f"FALLA widgets tras rerun · {nombre}: "
                  f"got={got!r} exp={exp!r}")

    # Los widgets que GUARDAN algo. `st.button` NO está, y es a propósito:
    # no tiene estado que perder, y es el único al que Streamlit prohíbe
    # expresamente escribirle el valor por `session_state`.
    _WIDGETS = {
        "pills", "selectbox", "segmented_control", "multiselect", "toggle",
        "checkbox", "radio", "slider", "select_slider", "text_input",
        "number_input", "date_input", "text_area", "color_picker",
        "time_input", "data_editor", "feedback",
    }

    # Lo que NO se preserva, con nombre y apellido y el motivo. Igual que
    # el par Proveedor/Documentos de la guarda de al lado: la excepción se
    # escribe entera en vez de aflojar la prueba, así el caso que esto
    # caza —un control nuevo sin preservar— sigue fallando.
    _EXENTOS = {
        ("_documentos_proveedor.py", "cp_prov_q"):
            "esta sección sólo LEE la selección del filtro de Proveedor "
            "(`_sel_rank, _ =`); el que lo DIBUJA es aquel drill, y "
            "escribirle sus keys desde acá sería tocar widgets ajenos — en "
            "un rerun completo aquéllos ya se dibujaron, y eso es "
            "StreamlitAPIException",
        ("_documentos_proveedor.py", "cp_prov_cb::*"): "ídem",
        ("volatilidad.py", "compras_vol_periodo_*"):
            "la escalada manda la ventana a HEREDA A PROPÓSITO (elegir un "
            "rango a mano es pedir que mande ese rango); su dueño es "
            "`_K_VENTANA`, que no es clave de widget",
    }

    def _key_de(nodo):
        """La key de un `key=` literal, o su PREFIJO + `*` si es f-string.

        Una key armada (`f"vh_otra_{grano}"`) no se puede comparar contra
        una lista, pero su prefijo sí: es la misma forma con la que
        `preservar_widgets` declara una familia."""
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            return nodo.value
        if isinstance(nodo, ast.JoinedStr):
            pre = ""
            for parte in nodo.values:
                if isinstance(parte, ast.Constant):
                    pre += str(parte.value)
                else:
                    break
            return f"{pre}*" if pre else None
        return None

    def _cubre(declarada, key):
        return (declarada == key
                or (declarada.endswith("*")
                    and key.startswith(declarada[:-1])))

    def _tupla(arbol, nombre):
        """El valor de un `NOMBRE = (...)` de nivel de módulo."""
        for nodo in arbol.body:
            if not isinstance(nodo, ast.Assign):
                continue
            if not any(isinstance(t, ast.Name) and t.id == nombre
                       for t in nodo.targets):
                continue
            try:
                return [str(v) for v in ast.literal_eval(nodo.value)]
            except (ValueError, TypeError, SyntaxError):
                return []
        return []

    raiz = pathlib.Path(__file__).parent
    sin_preservar, exentos_usados, n_funcs = [], set(), 0
    for py, texto in _fuentes_py(raiz):
        if py.name.startswith("test_"):
            continue
        try:
            arbol = ast.parse(texto)
        except SyntaxError:                      # que lo cante otra guarda
            continue
        for fn in ast.walk(arbol):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            reruns = [n.lineno for n in ast.walk(fn)
                      if isinstance(n, ast.Call)
                      and getattr(n.func, "attr", None) == "rerun"]
            if not reruns:
                continue
            corte = min(reruns)
            # Lo DECLARADO: el argumento de `preservar_widgets(...)`,
            # resuelto contra la tupla de nivel de módulo que nombra.
            declaradas = []
            for n in ast.walk(fn):
                if (isinstance(n, ast.Call)
                        and getattr(n.func, "id", None) == "preservar_widgets"
                        and n.args and isinstance(n.args[0], ast.Name)):
                    declaradas += _tupla(arbol, n.args[0].id)
            # Y lo EXPUESTO: lo que se dibuja después del rerun.
            expuestas = []
            for n in ast.walk(fn):
                if not isinstance(n, ast.Call) or n.lineno <= corte:
                    continue
                nom = (getattr(n.func, "attr", None)
                       or getattr(n.func, "id", None))
                if nom in _WIDGETS:
                    k = next((_key_de(kw.value) for kw in n.keywords
                              if kw.arg == "key"), None)
                    if k:
                        expuestas.append((n.lineno, k))
                elif nom == "selector" and n.args:
                    # `graficos/periodo.py`: la ventana propia de la tarjeta.
                    k = _key_de(n.args[0])
                    if k:
                        expuestas.append((n.lineno, k))
                elif nom == "filtro_proveedores" and n.args:
                    # `_comun.py`: una checkbox por proveedor + su buscador.
                    k = _key_de(n.args[0])
                    if k and not k.endswith("*"):
                        expuestas += [(n.lineno, f"{k}_q"),
                                      (n.lineno, f"{k}_cb::*")]
            if expuestas:
                n_funcs += 1
            for lineno, key in expuestas:
                if any(_cubre(d, key) for d in declaradas):
                    continue
                if (py.name, key) in _EXENTOS:
                    exentos_usados.add((py.name, key))
                    continue
                sin_preservar.append(f"{py.name}:{lineno} {key}")

    check("todo widget dibujado tras un rerun está preservado o exento",
          sorted(set(sin_preservar)), [])
    # Un glob que no matchea nada pasa en verde sin haber leído nada.
    check("el barrido encontró las funciones que escalan", n_funcs >= 6, True)
    # Y al revés: una exención que ya no aplica es una mentira que envejece.
    check("no quedan exenciones muertas",
          sorted(set(_EXENTOS) - exentos_usados), [])

    # ── La expansión de `*`, que es lo único con lógica ──────────────────
    # Corre en bare mode: sin app, `st.session_state` es un dict.
    import streamlit as st

    from graficos.base import preservar_widgets

    st.session_state["_t_pw_gran"] = "Por documento"
    st.session_state["_t_pw_cb::ACME S.A."] = True
    st.session_state.pop("_t_pw_falta", None)
    preservar_widgets(("_t_pw_gran", "_t_pw_cb::*", "_t_pw_falta"))
    check("preserva lo que existe",
          (st.session_state["_t_pw_gran"],
           st.session_state["_t_pw_cb::ACME S.A."]),
          ("Por documento", True))
    # Una key declarada que todavía no existe NO se crea: sembrar `None` en
    # la clave de un widget es elegir por el usuario.
    check("una key declarada que no existe no se inventa",
          "_t_pw_falta" in st.session_state, False)
    for _k in ("_t_pw_gran", "_t_pw_cb::ACME S.A."):
        st.session_state.pop(_k, None)

    return fallos


_SCRIPT_FRAGMENT_ANIDADO = '''
import streamlit as st
from graficos.base import seccion_perezosa

st.session_state.setdefault("n_seccion", 0)
st.session_state.setdefault("n_drill", 0)


@st.fragment
def _drill():
    st.session_state["n_drill"] += 1
    st.button("otro insumo", key="t_drill_btn")


def _dibujar():
    st.session_state["n_seccion"] += 1
    with st.container(key="t_drill_wrap"):
        _drill()


@st.fragment
def _contenido():
    st.button("Semanal", key="t_rail_btn")
    with st.container(key="t_sec"):
        seccion_perezosa("t_sec", "Sección", _dibujar)


_contenido()
'''


def _pruebas_fragment_anidado_una_vez():
    """Una sección de la pila no se dibuja dos veces en la misma corrida.

    Bug real, 2026-09-17: `StreamlitDuplicateElementKey` sobre
    `compras_prod_drill_wrap`, al tocar «Semanal» en el rail mientras la
    página construía sus secciones. Dos clics que llegan con el servidor
    ocupado se juntan en UNA corrida con una cola de fragments; si en ella
    están `_render_contenido` (el del rail) y una sección que cuelga de él
    (la de su botón invisible), Streamlit 1.59 corre a los dos y la sección
    se dibuja dos veces. La 1.62 lo arregló; acá lo cubre
    `base.py::una_vez_por_corrida`. Regla #456.

    AppTest no sabe correr fragments sueltos: sólo hace corridas completas y
    estrena el registro de fragments en cada una. Por eso esta guarda le
    pone a su `ScriptRunner` —el real— un registro compartido y la cola que
    Streamlit arma al juntar los dos clics. Y mira TAMBIÉN el clic
    siguiente dentro del drill de la sección: el arreglo obvio («no dibujar
    la segunda vez») hace que Streamlit borre a los fragments hijos del
    registro, y ese clic no llega a ningún lado.
    """
    import pathlib
    import tempfile
    from urllib import parse

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    fragment anidado · {nombre}")
        else:
            fallos += 1
            print(f"FALLA fragment anidado · {nombre}: got={got!r} exp={exp!r}")

    try:
        import streamlit.testing.v1.local_script_runner as lsr
        from streamlit.runtime.fragment import MemoryFragmentStorage
        from streamlit.runtime.scriptrunner_utils.script_requests import RerunData
        from streamlit.testing.v1 import AppTest
        from streamlit.testing.v1.element_tree import parse_tree_from_messages
    except ImportError as e:
        fallos += 1
        print(f"FALLA fragment anidado · el arnés no encuentra las internas "
              f"de esta versión de Streamlit: {e}")
        return fallos

    registro = MemoryFragmentStorage()
    cola = []

    def _run(self, widget_state=None, query_params=None, timeout=3,
             page_hash=""):
        qs = parse.urlencode(query_params, doseq=True) if query_params else ""
        self.request_rerun(RerunData(
            widget_states=widget_state, query_string=qs,
            page_script_hash=page_hash, fragment_id_queue=list(cola)))
        if not self._script_thread:
            self.start()
        lsr.require_widgets_deltas(self, timeout)
        return parse_tree_from_messages(self.forward_msgs())

    viejo_registro, viejo_run = lsr.MemoryFragmentStorage, lsr.LocalScriptRunner.run
    lsr.MemoryFragmentStorage = lambda: registro
    lsr.LocalScriptRunner.run = _run
    try:
        with tempfile.TemporaryDirectory() as tmp:
            script = pathlib.Path(tmp) / "pila_anidada.py"
            script.write_text(_SCRIPT_FRAGMENT_ANIDADO, encoding="utf-8")
            at = AppTest.from_file(str(script), default_timeout=30)
            # Streamlit 1.64 crea el almacén en `AppTest` y se lo pasa al
            # runner, que ya no construye uno propio: el parche de
            # `lsr.MemoryFragmentStorage` de arriba sólo sirve en las
            # versiones anteriores. Sin esta línea `registro` quedaba vacío
            # y el arnés moría con StopIteration sin probar nada.
            at._fragment_storage = registro
            at.run()

            padres = dict(registro._parent_by_id)
            raiz = next(f for f, p in padres.items() if p is None)
            seccion = next(f for f, p in padres.items() if p == raiz)

            # Los dos clics en la MISMA corrida, en el orden de llegada
            # que no ayuda: primero el hijo.
            cola[:] = [seccion, raiz]
            at.button(key="pila_go_t_sec").click()
            at.button(key="t_rail_btn").click()
            at.run()
            check("la corrida doble no revienta",
                  [e.value for e in at.exception], [])
            check("la sección se dibuja UNA vez",
                  at.session_state["n_seccion"], 1)

            drill = [f for f, p in registro._parent_by_id.items()
                     if p == seccion]
            check("el drill de la sección sigue registrado", len(drill), 1)
            if drill:
                antes = at.session_state["n_drill"]
                cola[:] = drill
                at.button(key="t_drill_btn").click()
                at.run()
                check("y su clic siguiente lo redibuja",
                      (at.session_state["n_drill"] - antes,
                       [e.value for e in at.exception]), (1, []))
    except Exception as e:  # el arnés en sí: que se vea qué se movió
        fallos += 1
        print(f"FALLA fragment anidado · el arnés no corrió: "
              f"{type(e).__name__}: {e}")
    finally:
        lsr.MemoryFragmentStorage = viejo_registro
        lsr.LocalScriptRunner.run = viejo_run

    return fallos


def _pruebas_rango_por_tarjeta():
    """Compras: una categoría de rango por SECCIÓN de la pila (2026-09-08).

    Hasta ese día los cinco selectores de fecha de las cabeceras escribían
    UNA sola clave, así que mover la fecha en una tarjeta la movía en las
    otras cuatro. Estaba puesto a propósito —eran un ATAJO a la píldora de
    la franja— y dejó de tener sentido el 2026-09-06, cuando la franja
    perdió el calendario y el atajo quedó siendo EL control. Ver regla
    #363.

    Lo que estas guardas cubren es lo que se rompe SIN QUE SE VEA:

      · una categoría que nombra una sección que no existe (un typo en
        `CATEGORIA_SEC` no da error: `dict.get` devuelve None y la tarjeta
        vuelve callada al rango compartido, o sea el bug de vuelta);
      · dos secciones compartiendo categoría por copiar y pegar;
      · y sobre todo: una tarjeta a la que se le olvidó el `categoria=`.
        Así se descubrió el bug original —una vista sola comportándose
        distinto— y es exactamente lo que va a pasar cuando alguien copie
        una cabecera para hacer la sexta tarjeta.
    """
    import ast
    import pathlib

    import graficos.compras as gc

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    rango tarjeta · {nombre}")
        else:
            fallos += 1
            print(f"FALLA rango tarjeta · {nombre}: got={got!r} exp={exp!r}")

    claves_pila = {c for c, _v in gc._PILA}
    check("las claves de CATEGORIA_SEC son secciones de _PILA",
          sorted(set(gc.CATEGORIA_SEC) - claves_pila), [])
    # UNA categoría por sección, con UNA excepción declarada acá: desde el
    # 2026-09-09 «Detalle de documentos por proveedor» es su propia sección
    # y comparte el rango con el Ranking de Proveedores A PROPÓSITO — se
    # calcula sobre el mismo `base`/`top_provs`, así que con rangos
    # distintos mostraría documentos de proveedores rankeados en otro
    # período (ver `CATEGORIA_SEC` en `_comun.py`).
    #
    # La excepción se escribe con nombre y apellido en vez de aflojar la
    # guarda: lo que esta prueba caza es el share por COPIAR Y PEGAR, y
    # ese sigue fallando. Si mañana la tabla quiere su rango propio, esta
    # línea es lo que hay que borrar.
    _PAR_COMPARTIDO = {"compras_sec_proveedor", "compras_sec_documentos"}
    check("el par Proveedor/Documentos comparte categoría a propósito",
          len({gc.CATEGORIA_SEC.get(k) for k in _PAR_COMPARTIDO}), 1)
    _solas = {k: v for k, v in gc.CATEGORIA_SEC.items()
              if k not in _PAR_COMPARTIDO}
    check("una categoría distinta por sección (fuera del par declarado)",
          len(set(_solas.values())), len(_solas))
    check("y el par no comparte con ninguna otra sección",
          sorted(set(_solas.values())
                 & {gc.CATEGORIA_SEC["compras_sec_proveedor"]}), [])
    # Las dos secciones SIN este selector quedan fuera a propósito: su
    # control de fecha es el desplegable de `graficos/periodo.py`, que ya
    # era por tarjeta. Meterlas les daría dos controles que se pisan.
    check("las secciones sin trigger quedan fuera",
          sorted({"compras_sec_vs_ano_pasado", "compras_sec_tabla"}
                 & set(gc.CATEGORIA_SEC)), [])

    # POR `ast` Y NO POR REGEX, y no es purismo: el primer intento marcaba
    # `_css_proveedor.py:78`, que es una MENCION en un comentario
    # (`Ahora lo dibuja selector_fecha_tarjeta(extra=...) DENTRO de`).
    # Filtrar comentarios a mano deja afuera los docstrings, y el arbol
    # ademas distingue una LLAMADA de un import o de la definicion misma.
    raiz = pathlib.Path(__file__).parent / "graficos" / "compras"
    sin_categoria, n_llamadas = [], 0
    # `documentos_sunat.py` vive en este paquete por historia, pero es el
    # drill de OTRO reporte (Documentos SUNAT, regla #577): su tarjeta es
    # la única con fecha y escribe la clave canónica de SU reporte, sin
    # categoría, a propósito (regla #633).
    _OTRO_REPORTE = {"documentos_sunat.py"}
    for py, texto in _fuentes_py(raiz):
        if py.name in _OTRO_REPORTE:
            continue
        try:
            arbol = ast.parse(texto)
        except SyntaxError:                      # que lo cante otra guarda
            continue
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            fn = nodo.func
            nombre = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if nombre != "selector_fecha_tarjeta":
                continue
            n_llamadas += 1
            if not any(k.arg == "categoria" for k in nodo.keywords):
                sin_categoria.append(f"{py.name}:{nodo.lineno}")
    check("todo selector_fecha_tarjeta de Compras declara su categoria",
          sorted(set(sin_categoria)), [])
    # Y que el barrido haya visto algo: un glob que no matchea nada pasa en
    # verde sin haber leído nada (la trampa 2 de `_fuentes_py`).
    check("el barrido encontró los selectores de fecha",
          n_llamadas >= 5, True)

    # ── Y AHORA EL COMPORTAMIENTO, que es lo único que se ve ─────────────
    # Lo de arriba prueba el CABLEADO: que cada tarjeta declare su
    # categoría. No prueba lo que al usuario le importa —que mover una no
    # mueva a la otra— y son cosas distintas: el cableado puede estar bien
    # y la siembra pisar igual las dos claves. Esto corre en bare mode,
    # sin app: `franja_fecha.publicar` es un dict en `session_state` y
    # `asegurar_rango` no dibuja nada.
    import datetime

    import streamlit as st
    import franja_fecha
    from graficos.base import (k_rango_tarjeta, rango_tarjeta,
                               recortar_por_tarjeta)

    f_min, f_max = datetime.date(2023, 1, 2), datetime.date(2026, 9, 5)
    por_defecto = (datetime.date(2025, 9, 6), f_max)   # los 12m de app.py
    ctx_previo = st.session_state.get("_franja_fecha_ctx")
    franja_fecha.publicar(
        k_rango="rango_franja_Compras", fecha_min=f_min, fecha_max=f_max,
        reporte="Compras", usa_carga_rango=False,
        hoy=datetime.date(2026, 9, 8), rango_default=por_defecto,
    )
    k_prov = k_rango_tarjeta("sec_proveedor")
    k_sem = k_rango_tarjeta("sec_semanal")
    for _k in (k_prov, k_sem, "rango_franja_Compras"):
        st.session_state.pop(_k, None)

    check("cada categoría tiene su propia clave", k_prov != k_sem, True)
    check("la clave lleva reporte y categoría",
          k_prov, "rango_cat_Compras_sec_proveedor")
    # SIEMBRA: las dos arrancan en el default publicado por `app.py`. Si
    # cada una se inventara el suyo, la página abriría con dos períodos
    # distintos sin que nadie los haya tocado.
    check("las dos tarjetas siembran el default publicado",
          (rango_tarjeta("sec_proveedor"), rango_tarjeta("sec_semanal")),
          (por_defecto, por_defecto))

    # ── LA EXCEPCIÓN POR CATEGORÍA (2026-09-11) ──────────────────────────
    # `rango_default_cat` le da a UNA categoría otra ventana de apertura. Lo
    # que se fija acá es que sea una excepción y no un cambio de default: la
    # categoría nombrada abre en el mes, el resto sigue con los 12 meses del
    # reporte. Sin este assert, un dict mal leído (o un `.get` sobre el dict
    # equivocado) pasaría desapercibido porque las dos ventanas son rangos
    # válidos y ninguna revienta nada.
    mes = (datetime.date(2026, 9, 1), f_max)
    for _k in (k_prov, k_sem):
        st.session_state.pop(_k, None)
    franja_fecha.publicar(
        k_rango="rango_franja_Compras", fecha_min=f_min, fecha_max=f_max,
        reporte="Compras", usa_carga_rango=False,
        hoy=datetime.date(2026, 9, 8), rango_default=por_defecto,
        rango_default_cat={"sec_proveedor": mes},
    )
    check("la categoría con excepción abre en su ventana",
          rango_tarjeta("sec_proveedor"), mes)
    check("y las demás siguen con el default del reporte",
          rango_tarjeta("sec_semanal"), por_defecto)
    # Las excepciones las declara `graficos.compras`; que nombren una
    # categoría REAL no es obvio: `CATEGORIA_SEC` mapea sección→categoría,
    # así que escribir ahí el nombre de la sección ("compras_sec_proveedor")
    # es el error natural — y no rompería nada, sólo dejaría la excepción
    # sin efecto y la tarjeta abriendo con el default de siempre.
    check("las secciones que abren en el mes nombran categorías reales",
          sorted(set(gc.SEC_ABRE_EN_EL_MES) - set(gc.CATEGORIA_SEC.values())),
          [])
    # Y que `app.py` siga publicando el dict: es el único cable entre el
    # cálculo del mes y el lector. Quitar el kwarg no da error en ningún
    # lado, sólo devuelve la tarjeta a los 12 meses en silencio.
    _app = (pathlib.Path(__file__).parent / "app.py").read_text(
        encoding="utf-8")
    _pub = [n for n in ast.walk(ast.parse(_app))
            if isinstance(n, ast.Call)
            and getattr(n.func, "attr", None) == "publicar"]
    check("el barrido encontró la publicación del contexto",
          len(_pub) >= 1, True)
    check("app.py publica rango_default_cat",
          [c.lineno for c in _pub
           if not any(k.arg == "rango_default_cat" for k in c.keywords)], [])
    for _k in (k_prov, k_sem):
        st.session_state.pop(_k, None)
    franja_fecha.publicar(
        k_rango="rango_franja_Compras", fecha_min=f_min, fecha_max=f_max,
        reporte="Compras", usa_carga_rango=False,
        hoy=datetime.date(2026, 9, 8), rango_default=por_defecto,
    )
    rango_tarjeta("sec_proveedor")
    rango_tarjeta("sec_semanal")

    # EL ASSERT DE LA REGLA #363: mover una no mueve a la otra.
    st.session_state[k_prov] = (datetime.date(2026, 9, 1), f_max)
    check("mover el rango de una tarjeta NO mueve el de la otra",
          rango_tarjeta("sec_semanal"), por_defecto)
    check("y la tarjeta movida se queda con el suyo",
          rango_tarjeta("sec_proveedor"),
          (datetime.date(2026, 9, 1), f_max))
    # Una tarjeta con categoría no puede escribir la clave GLOBAL: ahí es
    # donde escribían las cinco antes, y es lo que hay que no repetir.
    check("una tarjeta con categoría no toca la clave global",
          "rango_franja_Compras" in st.session_state, False)

    # Y el recorte usa el rango de SU tarjeta, no el de al lado.
    df = pd.DataFrame({"f": pd.date_range("2026-08-01", "2026-09-05",
                                          freq="D")})
    check("el recorte sigue al rango de su tarjeta",
          (len(recortar_por_tarjeta(df, "f", "sec_proveedor")),
           len(recortar_por_tarjeta(df, "f", "sec_semanal"))),
          (5, len(df)))

    # Se deja `session_state` como estaba: estas pruebas corren en el mismo
    # proceso que las demás y una clave colgada las contamina.
    for _k in (k_prov, k_sem, "rango_franja_Compras"):
        st.session_state.pop(_k, None)
    if ctx_previo is None:
        st.session_state.pop("_franja_fecha_ctx", None)
    else:
        st.session_state["_franja_fecha_ctx"] = ctx_previo

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


def _pruebas_panel_fecha():
    """El selector de fecha de las tarjetas (regla #616): atajos y panel.

    1. LOS ATAJOS CUENTAN HASTA EL ÚLTIMO DÍA CON DATOS, no hasta hoy: con
       bounds sucios (no arrancan un 1 ni terminan a fin de mes) cada uno da
       lo que dice su nombre, y el que no toca los datos se descarta.
    2. LA TARJETA ABRE EN UN ATAJO CON NOMBRE. «Últimos 12 meses» es la
       ventana con que abre Compras (`periodo.ventana("12m")`) y «Últimos
       30 días» el default de las tarjetas de un mes, que `app.py` toma de
       esta misma función. Si se separan, el botón deja de decir el atajo.
    3. EL PANEL ES UNA PIEZA PROPIA y el selector la monta: sin `:has()` en
       su CSS, sin atajos calculados en el JS (los manda Python) y sin la
       escala de tiempo vieja adentro de `selector_fecha_tarjeta`.
    """
    import ast
    import datetime
    from pathlib import Path

    from estado_rango import atajo_de, atajos_tarjeta, meses_atras
    from graficos import periodo
    from graficos.panel_fecha import etiqueta_de

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    panel fecha · {nombre}")
        else:
            fallos += 1
            print(f"FALLA panel fecha · {nombre}: got={got!r} exp={exp!r}")

    D = datetime.date
    b = (D(2024, 3, 17), D(2026, 8, 25))          # el 25 es martes
    at = {c: r for c, _n, _g, r in atajos_tarjeta(D(2026, 8, 25), b)}
    check("esta semana arranca el lunes", at["semana"], (D(2026, 8, 24), D(2026, 8, 25)))
    check("este mes", at["mes"], (D(2026, 8, 1), D(2026, 8, 25)))
    check("este año", at["anio"], (D(2026, 1, 1), D(2026, 8, 25)))
    check("30 días son 30 con el ancla adentro", at["d30"], (D(2026, 7, 27), D(2026, 8, 25)))
    check("3 meses", at["m3"], (D(2026, 5, 26), D(2026, 8, 25)))
    check("12 meses", at["m12"], (D(2025, 8, 26), D(2026, 8, 25)))
    check("mes pasado entero", at["mes_ant"], (D(2026, 7, 1), D(2026, 7, 31)))
    check("año pasado entero", at["anio_ant"], (D(2025, 1, 1), D(2025, 12, 31)))
    check("todo = los datos", at["todo"], b)
    check("orden de los nueve",
          [c for c, *_ in atajos_tarjeta(D(2026, 8, 25), b)],
          ["semana", "mes", "anio", "d30", "m3", "m12", "mes_ant", "anio_ant", "todo"])
    check("el ancla no pasa los datos",
          dict((c, r) for c, _n, _g, r in atajos_tarjeta(D(2026, 9, 30), b))["mes"],
          (D(2026, 8, 1), D(2026, 8, 25)))
    nuevo = {c: r for c, _n, _g, r in atajos_tarjeta(D(2026, 8, 25), (D(2026, 2, 10), D(2026, 8, 25)))}
    check("sin datos del año pasado no se ofrece", "anio_ant" in nuevo, False)
    check("12 meses recortado al primer día con datos", nuevo["m12"], (D(2026, 2, 10), D(2026, 8, 25)))
    check("meses_atras recorta el día (31 mar → 28 feb)", meses_atras(D(2026, 3, 31), 1), D(2026, 2, 28))
    check("meses_atras en bisiesto", meses_atras(D(2024, 3, 31), 1), D(2024, 2, 29))
    check("sin bounds no hay atajos", atajos_tarjeta(D(2026, 8, 25), None), [])

    v12 = periodo.ventana("12m", D(2026, 8, 25), minimo=b[0])
    check("«Últimos 12 meses» == la ventana con que abre Compras",
          at["m12"], (v12[0].date(), v12[1].date()))
    app = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")
    check("las tarjetas de un mes abren en «Últimos 30 días» (app.py)",
          "atajos_tarjeta(" in app and '.get("d30")' in app, True)

    lista = atajos_tarjeta(D(2026, 8, 25), b)
    check("atajo_de reconoce el rango exacto", atajo_de(at["d30"], lista), "d30")
    check("atajo_de: un día de más ya no es atajo",
          atajo_de((D(2026, 7, 26), D(2026, 8, 25)), lista), None)
    lunes_1 = atajos_tarjeta(D(2026, 6, 1), b)   # lunes 1: semana == mes
    check("dos atajos iguales: gana el primero",
          atajo_de((D(2026, 6, 1), D(2026, 6, 1)), lunes_1), "semana")

    ctx = {"fecha_min": b[0], "fecha_max": b[1], "hoy": D(2026, 8, 26), "k_rango": "x"}
    check("botón con atajo", etiqueta_de(at["d30"], ctx), "Últimos 30 días · 27 jul – 25 ago")
    check("botón con atajo que cruza de año", etiqueta_de(at["m12"], ctx),
          "Últimos 12 meses · 26 ago 2025 – 25 ago 2026")
    check("botón con mes pasado", etiqueta_de(at["mes_ant"], ctx), "Mes pasado · julio")
    check("botón sin atajo: fechas con año",
          etiqueta_de((D(2026, 7, 15), D(2026, 8, 25)), ctx), "15 jul – 25 ago 2026")
    check("botón sin rango", etiqueta_de(None, ctx), "Elegir fechas")

    raiz = Path(__file__).parent / "graficos"
    css = (raiz / "panel_fecha.css").read_text(encoding="utf-8")
    js = (raiz / "panel_fecha.js").read_text(encoding="utf-8")
    check("el CSS del panel no usa :has()", ":has(" in css, False)
    check("el JS exporta la función del componente", "export default function" in js, True)
    check("el JS no calcula atajos (los manda Python)", "Últimos" in js, False)
    # Semanas (regla #642): entre Meses y Días, de lunes a domingo —la
    # semana de «Esta semana»—, y lo elegido recortado a los datos en el JS.
    check("el panel ofrece Semanas entre Meses y Días",
          js.index('data-modo="meses"') < js.index('data-modo="semanas"')
          < js.index('data-modo="dias"'), True)
    check("las semanas arrancan el lunes",
          "const lunes = (n) => n - dow(n);" in js
          and "getUTCDay() + 6) % 7" in js, True)
    check("un clic se recorta a los datos en el JS",
          "Math.min(e, st.max)" in js and "Math.max(s, st.min)" in js, True)
    arbol = ast.parse((raiz / "base.py").read_text(encoding="utf-8"))
    sel = next(n for n in arbol.body
               if isinstance(n, ast.FunctionDef) and n.name == "selector_fecha_tarjeta")
    llamadas = {n.func.id for n in ast.walk(sel)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    check("selector_fecha_tarjeta monta el panel", "panel_fecha" in llamadas, True)
    check("selector_fecha_tarjeta ya no dibuja la escala vieja",
          "selector_escala" in llamadas, False)
    return fallos


def _pruebas_partir_por():
    """Compras por período: de qué está hecha cada barra (reglas #620 y #621).

    1. EL PRECIO HABITUAL es la mediana del precio unitario del MISMO
       producto en los 90 días ANTERIORES, sin contar el mismo día. Se
       compara contra un cálculo a fuerza bruta, con los bordes: el día 90
       entra y el 91 no, dos compras del mismo día no se miran entre sí, una
       línea sin cantidad no da precio pero recibe el suyo, la primera
       compra de un producto no tiene, y el índice puede venir repetido.
    2. LAS PARTES CIERRAN: por subfamilia o proveedor (las cinco mayores y
       el resto) y por precio (habitual, de más, sin precio) suman el total
       de cada barra, y el color de una categoría sale de su puesto en el
       HISTÓRICO, no en la vista.
    3. El hover nombra todas las partes y marca en negrita sólo la suya.
    """
    import math

    import numpy as np

    import graficos.compras.semanal as sem
    from tema import ERROR, GRIS_TEXTO_SUAVE, PALETA_SERIES, SERIE_PRINCIPAL

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    partir por · {nombre}")
        else:
            fallos += 1
            print(f"FALLA partir por · {nombre}: got={got!r} exp={exp!r}")

    # ── 1. El precio habitual ────────────────────────────────────────────
    # 2026-04-01 menos 90 días es 2026-01-01: el borde de la ventana.
    filas = [
        ("A", "2026-01-01", 100.0, 10.0),   # 10
        ("A", "2026-02-15", 120.0, 10.0),   # 12
        ("A", "2026-03-01", 50.0, 0.0),     # sin cantidad: no da precio
        ("A", "2026-04-01", 200.0, 10.0),   # 20 — ve el 01-01 y el 02-15
        ("A", "2026-04-01", 300.0, 10.0),   # 30 — mismo día: no se miran
        ("A", "2026-04-02", 90.0, 3.0),     # ve 12, 20 y 30: el 01-01 quedó afuera
        ("B", "2026-04-01", 10.0, 1.0),     # primera compra de B
        ("A", "2026-09-01", 50.0, 5.0),     # nada en los 90 días previos
    ]
    df = pd.DataFrame(filas, columns=["prod", "fecha", "valor", "cant"],
                      index=[7, 7, 3, 9, 9, 1, 2, 4])   # índice REPETIDO
    df["fecha"] = pd.to_datetime(df["fecha"])

    def bruta(d, dias=90):
        out = []
        for p, f, *_ in d.itertuples(index=False):
            v = d[(d["prod"] == p) & (d["fecha"] >= f - pd.Timedelta(days=dias))
                  & (d["fecha"] < f) & (d["cant"] > 0) & (d["valor"] > 0)]
            out.append(float((v["valor"] / v["cant"]).median())
                       if len(v) else float("nan"))
        return out

    got = sem.precio_habitual(df["prod"], df["fecha"], df["valor"], df["cant"])
    exp = bruta(df)

    def _iguales(a, b):
        return all((math.isnan(x) and math.isnan(y)) or abs(x - y) < 1e-9
                   for x, y in zip(a, b))

    check("igual que a fuerza bruta", _iguales(list(got), exp), True)
    check("sale con el índice de la entrada, aunque se repita",
          list(got.index), list(df.index))
    check("los valores de los bordes",
          [None if math.isnan(x) else round(x, 2) for x in got],
          [None, 10.0, 11.0, 11.0, 11.0, 20.0, None, None])
    # Al azar, con semilla: lo que no se me ocurrió.
    rng = np.random.default_rng(620)
    n = 400
    dz = pd.DataFrame({
        "prod": rng.choice(list("PQRST"), n),
        "fecha": pd.Timestamp("2026-01-01")
                 + pd.to_timedelta(rng.integers(0, 300, n), unit="D"),
        "valor": rng.uniform(0, 100, n).round(2),
        "cant": rng.choice([0.0, 0.5, 1.0, 2.0, 7.5], n),
    }, index=rng.integers(0, 50, n))
    check("al azar, igual que a fuerza bruta",
          _iguales(list(sem.precio_habitual(dz["prod"], dz["fecha"],
                                             dz["valor"], dz["cant"])),
                   bruta(dz)), True)

    # ── 2. Las partes por categoría ──────────────────────────────────────
    claves = ["P1", "P2"]
    dd = pd.DataFrame({
        "clave": ["P1", "P2"] * 7,
        "sub": [f"S{i}" for i in range(1, 8) for _ in range(2)],
        "valor": [float(v) for i in range(7, 0, -1) for v in (i * 6, i * 4)],
    })
    tot = dd.groupby("clave")["valor"].sum().reindex(claves).tolist()
    orden = ["S2", "S1", "S3", "S4", "S5", "S6", "S7"]
    partes = sem.partes_por_columna(dd, "sub", claves, orden=orden)
    check("las cinco mayores y el resto",
          [r for r, _c, _v in partes],
          ["S1", "S2", "S3", "S4", "S5", "Otras (2)"])
    check("cada barra cierra en su total",
          [round(sum(v[j] for _r, _c, v in partes), 6) for j in range(2)],
          [round(x, 6) for x in tot])
    check("el color sale del histórico, no de la vista",
          [c for _r, c, _v in partes[:2]], [PALETA_SERIES[1], PALETA_SERIES[0]])
    check("el resto va en gris", partes[-1][1], GRIS_TEXTO_SUAVE)
    seis = sem.partes_por_columna(dd[dd["sub"] != "S7"], "sub", claves,
                                  orden=orden)
    check("con seis van todas, sin resto", len(seis), 6)

    # ── 2b. Las partes por precio ────────────────────────────────────────
    dp = pd.DataFrame({
        "clave": ["P1", "P1", "P1", "P2"],
        "prod": ["X", "Y", "Z", "X"],
        "valor": [120.0, 45.0, 30.0, 100.0],
        "cant": [10.0, 5.0, 3.0, 10.0],
        "ref": [10.0, 10.0, float("nan"), 10.0],
    })
    pp, pila, extra = sem.partes_por_precio(dp, claves)
    check("precio · las tres partes, en el orden de la leyenda",
          [(r, c) for r, c, _v in pp],
          [(sem._A_PRECIO_HABITUAL, SERIE_PRINCIPAL),
           (sem._PAGADO_DE_MAS, ERROR),
           (sem._SIN_PRECIO_PREVIO, GRIS_TEXTO_SUAVE)])
    check("precio · los montos", [v for _r, _c, v in pp],
          [[145.0, 100.0], [20.0, 0.0], [30.0, 0.0]])
    check("precio · la pila: sin precio abajo, el rojo arriba", pila, [2, 0, 1])
    check("precio · cada barra cierra en su total",
          [sum(v[j] for _r, _c, v in pp) for j in range(2)], [195.0, 100.0])
    check("precio · lo pagado de menos", "Pagado de menos: S/ 5.00" in extra["P1"],
          True)
    check("precio · el neto, con su signo y su %",
          "+S/ 15.00 (+10%)" in extra["P1"], True)
    check("precio · el producto pagado de más", "X: +S/ 20.00 (+20%)" in extra["P1"],
          True)
    pp2, pila2, _ = sem.partes_por_precio(dp[dp["clave"] == "P2"], claves)
    check("precio · una parte en cero en toda la vista no se dibuja",
          ([r for r, _c, _v in pp2], pila2), ([sem._A_PRECIO_HABITUAL], [0]))

    # ── 3. El hover: uno por barra, con la resaltada en negrita (#621) ───
    hov = sem._hover_partes(partes, tot, "Por subfamilia", marcada=1)
    check("hover · un texto por barra", len(hov), 2)
    check("hover · nombra todas las partes de la barra",
          all(r in hov[0] for r, _c, _v in partes), True)
    check("hover · sólo la resaltada en negrita",
          (hov[0].count("<b>"), "<b>S2:" in hov[0]), (1, True))
    check("hover · sin resaltada, ninguna en negrita",
          sem._hover_partes(partes, tot, "x")[0].count("<b>"), 0)

    # ── 4. Qué se puede resaltar y cómo lo dice la etiqueta (#621) ───────
    check("resaltar · las de nombre, no el resto",
          sem.opciones_resaltar(partes, sem._PARTIR_SUBFAMILIA),
          ["S1", "S2", "S3", "S4", "S5"])
    check("resaltar · en Precio, sólo lo pagado de más",
          sem.opciones_resaltar(pp, sem._PARTIR_PRECIO), [sem._PAGADO_DE_MAS])
    check("etiqueta · la parte con su %",
          sem.renglon_resaltado(11834.05, 28902.04)[0], "S/ 11.8k · 41%")
    check("etiqueta · en Precio, lo pagado de más",
          sem.renglon_resaltado(1257.36, 28902.04, precio=True)[0],
          "+S/ 1.3k de más")
    check("etiqueta · en Precio sin nada de más, queda la de antes",
          sem.renglon_resaltado(0.0, 100.0, precio=True), None)

    # ── 5. El IGV de cada línea y las guías del hover (#621) ─────────────
    marcas = sem.igv_de_linea(pd.Series([100.0, 50.0, 80.0, 10.0]),
                              pd.Series([18.0, 0.0, 0.0, 1.05]),
                              pd.Series(["F", "F", "G", "F"]))
    check("igv · 18 %, exonerado, guía y otra tasa",
          list(marcas), ["18 %", "exonerado", "guía", "10.5 %"])
    dg = pd.DataFrame({"clave": ["P1", "P1", "P2"], "tipo": ["G", "F", "F"],
                       "valor": [2018.5, 100.0, 50.0],
                       "compra": ["a", "b", "c"]})
    gu = sem._guias_por_clave(dg, claves)
    check("guías · la barra que tiene, con su monto",
          ("1 guía de remisión sin canjear: S/ 2,018.50" in gu[0], gu[1]),
          (True, ""))
    check("guías · con IGV avisa que todavía no lo lleva",
          "sin IGV todavía" in sem._guias_por_clave(dg, claves, igv=True)[0],
          True)

    # ── 5b. La nota de crédito como documento del Detalle (#628) ─────────
    _f = pd.Timestamp("2026-09-23")
    _fac, _anu = "2026-09-23·P1·F0F001000000010", "2026-09-23·P2·F0E001000001728"
    ddn = pd.DataFrame({
        "fecha": [_f, _f], "prod": ["Lomo", "Ajo"], "prov": ["P1", "P1"],
        "docn": ["F0F001000000010"] * 2, "doc": ["F001-10"] * 2,
        "cant": [15.0, 2.0], "punit": [40.0, 5.0], "valor": [600.0, 10.0],
        "fam": ["A"] * 2, "sub": ["s"] * 2, "neto": [600.0, 10.0],
        "igv": [108.0, 1.8], "tipo": ["F"] * 2, "usd": [False] * 2,
        "compra": [_fac] * 2, "clave": ["S39"] * 2, "lbl": ["21–27 set"] * 2})
    ncn = pd.DataFrame({
        "fecha": [_f, _f], "prod": ["Lomo", "Pato"], "prov": ["P1", "P2"],
        "docn": ["F0F001000000010", "F0E001000001728"], "fam": ["A", "A"],
        "sub": ["s", "s"], "neto": [200.0, 3558.22], "igv": [36.0, 640.48],
        "cant": [5.0, 40.0], "punit": [40.0, 88.9], "tipo": ["F", "F"],
        "usd": [False, False],
        "nota": ["N0F001000000099", "N0E001000000068"],
        "fecha_nc": [pd.Timestamp("2026-09-28")] * 2,
        "compra": [_fac, _anu], "valor": [200.0, 3558.22],
        "clave": ["S39", "S39"]})
    det = sem.detalle_con_notas(ddn, ncn, {"S39": "21–27 set"})
    check("nc · las columnas de dd, por nombre",
          list(det.columns), list(ddn.columns))
    check("nc · lo que suma el período no cambia",
          round(float(det["valor"].sum()), 2), 610.0)
    _por = det.groupby("compra")["valor"].sum().round(2).to_dict()
    check("nc · la factura parcial, como se facturó; la anulada, entera",
          (_por[_fac], _por[_anu]), (810.0, 3558.22))
    _nota = det[det["tipo"] == sem._TIPO_NC].set_index("doc")
    check("nc · la nota, en negativo, decodificada y en su fecha",
          (float(_nota.loc["E001-68", "valor"]),
           _nota.loc["E001-68", "fecha"].strftime("%d/%m")),
          (-3558.22, "28/09"))
    check("nc · sin notas, dd tal cual",
          sem.detalle_con_notas(ddn, ncn.iloc[0:0]) is ddn, True)

    # ── 6. Documento y Montos de «Filtros» (#621) ────────────────────────
    import graficos.compras._comun as cm
    dt = pd.DataFrame({"t": ["Factura", "Guía de Remisión",
                             "PLANILLA DE MOVILIDAD", None]})
    check("documento · tipo corto", list(cm.tipo_corto(dt["t"])),
          ["F", "G", "O", "O"])
    check("documento · facturas",
          len(cm.filtrar_documento(dt, "t", cm.DOC_FACTURAS)), 1)
    check("documento · guías",
          list(cm.filtrar_documento(dt, "t", cm.DOC_GUIAS)["t"]),
          ["Guía de Remisión"])
    check("documento · todos no filtra",
          len(cm.filtrar_documento(dt, "t", cm.DOC_TODOS)), 4)
    check("documento · sin columna no filtra",
          len(cm.filtrar_documento(dt, None, cm.DOC_GUIAS)), 4)
    check("montos · el sufijo del título",
          (cm.sufijo_montos(False), cm.sufijo_montos(True, cm.DOC_GUIAS)),
          (" · sin IGV", " · con IGV · guías sin canjear"))

    return fallos


def _pruebas_fecha_por_vista():
    """Movimientos: cada vista con su propia fecha (regla #617).

    1. CADA SECCIÓN DE LA PILA TIENE SU CATEGORÍA DE RANGO, salvo las dos de
       merma que traen su ventana (Rendimiento y Proveedor), y su dibujante
       la usa: un `_rango_y_boton("<sección>", …)` por cada una. Olvidar una no da
       error: la vista se quedaría con el histórico entero.
    2. NADIE LEE LA FECHA DE LA FRANJA en `movimientos.py`: la franja de
       este reporte ya no dibuja calendario, y lo que se leyera de ahí sería
       un rango que el usuario no ve.
    3. EL DEFAULT: las cuatro «por período» abren en 12 meses y las demás en
       30 días, contados hasta el último día con datos DE SU parquet.
    """
    import datetime
    import re
    from pathlib import Path

    import graficos.movimientos as mov

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    fecha por vista · {nombre}")
        else:
            fallos += 1
            print(f"FALLA fecha por vista · {nombre}: got={got!r} exp={exp!r}")

    raiz = Path(__file__).parent
    fuente = (raiz / "graficos" / "movimientos.py").read_text(encoding="utf-8")
    # Sin categoría: las dos de merma traen su ventana, y las dos de cierre
    # a cierre (regla #645) eligen un CIERRE de inventario, no un rango.
    con_ventana = {"mov_sec_merma_rend", "mov_sec_merma_prov",
                   "mov_sec_sinplato", "mov_sec_destino"}
    secciones = {c for c, _v in mov._PILA}
    # La pila sin «Tabla» (MOSTRAR_VISTAS_TABLA apagado) igual las declara.
    secciones |= {"mov_sec_tabla_req", "mov_sec_tabla_sal"}
    check("toda sección (salvo las de ventana) tiene categoría",
          sorted(secciones - con_ventana - set(mov.CATEGORIA_VISTA)), [])
    check("las categorías no se repiten",
          len(set(mov.CATEGORIA_VISTA.values())), len(mov.CATEGORIA_VISTA))
    check("las de 12 meses son categorías de verdad",
          set(mov.VISTAS_EN_12_MESES) <= set(mov.CATEGORIA_VISTA.values()), True)
    usadas = set(re.findall(r'_rango_y_boton\("(mov_sec_\w+)"', fuente))
    check("cada categoría la usa su dibujante",
          sorted(set(mov.CATEGORIA_VISTA) - usadas), [])
    check("movimientos.py no lee la fecha de la franja",
          "_rango_vigente(" in fuente, False)
    app = (raiz / "app.py").read_text(encoding="utf-8")
    _por_vista = re.search(r'REPORTES_FECHA_POR_VISTA = \(([^)]*)\)', app)
    check("la franja de Movimientos no dibuja calendario",
          (bool(_por_vista and '"Movimientos"' in _por_vista.group(1)),
           "reporte not in REPORTES_FECHA_POR_VISTA" in app), (True, True))
    css = (raiz / "estilos" / "_80_cards.py").read_text(encoding="utf-8")
    check("el botón de las vistas tiene su CSS (prefijo mov_f_)",
          'st-key-mov_f_' in css, True)

    D = datetime.date
    ctx_falso = {"k_rango": "x", "fecha_min": D(2023, 1, 1),
                 "fecha_max": D(2026, 10, 7), "hoy": D(2026, 10, 8),
                 "reporte": "Movimientos", "usa_carga_rango": False,
                 "rango_default": (D(2026, 10, 1), D(2026, 10, 7)),
                 "rango_default_cat": {}}
    real = mov.franja_fecha.contexto
    mov.franja_fecha.contexto = lambda: dict(ctx_falso)
    try:
        c12 = mov.ctx_de_vista("sal_periodo", (D(2024, 5, 3), D(2026, 9, 30)))
        c30 = mov.ctx_de_vista("sal_area", (D(2024, 5, 3), D(2026, 9, 30)))
        sin = mov.ctx_de_vista("req_area")
    finally:
        mov.franja_fecha.contexto = real
    check("los topes son los del parquet de la vista",
          (c12["fecha_min"], c12["fecha_max"]), (D(2024, 5, 3), D(2026, 9, 30)))
    check("«por período» abre en 12 meses hasta su último día con datos",
          c12["rango_default_cat"]["sal_periodo"], (D(2025, 10, 1), D(2026, 9, 30)))
    check("las demás abren en 30 días",
          c30["rango_default_cat"]["sal_area"], (D(2026, 9, 1), D(2026, 9, 30)))
    check("sin fechas propias, las del reporte",
          sin["rango_default_cat"]["req_area"], (D(2026, 9, 8), D(2026, 10, 7)))

    import pandas as pd
    d = pd.DataFrame({"_fecha": pd.to_datetime(
        ["2026-09-30 23:10", "2026-10-01 08:00", "2026-10-07 21:00"])})
    rng = (pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-08"))
    check("el recorte incluye el último día entero (fin exclusivo, #321)",
          len(mov.recortar_vista(d, rng)), 2)
    check("sin rango, entero", len(mov.recortar_vista(d, None)), 3)
    check("fechas_de", mov.fechas_de(d["_fecha"]), (D(2026, 9, 30), D(2026, 10, 7)))

    # 4. LA FECHA DE LOS REQUERIMIENTOS (regla #639): registro o proceso,
    # abre en registro, y sin la columna de proceso cae a la de registro
    # diciendo que fue ésa la que se usó.
    dos = pd.DataFrame({"FECHA REGISTRO": [], "FECHA PROCESADO": []})
    sola = pd.DataFrame({"Fecha Registro": []})
    check("requerimientos por registro",
          mov.columna_de_fecha(dos, mov.FECHA_REGISTRO),
          ("FECHA REGISTRO", mov.FECHA_REGISTRO))
    check("requerimientos por proceso",
          mov.columna_de_fecha(dos, mov.FECHA_PROCESO),
          ("FECHA PROCESADO", mov.FECHA_PROCESO))
    check("sin columna de proceso, la de registro y lo dice",
          mov.columna_de_fecha(sola, mov.FECHA_PROCESO),
          ("Fecha Registro", mov.FECHA_REGISTRO))
    check("el selector de requerimientos abre en registro",
          mov._AJUSTES["req_fecha"][::3], (mov.K_FECHA_REQ, mov.FECHA_REGISTRO))
    check("las vistas de requerimientos usan la fecha elegida",
          "columna_de_fecha(df_f, fecha_requerimientos())" in fuente, True)
    return fallos


_SCRIPT_ELECCION_COMPARTIDA = '''
import streamlit as st
from graficos.base import eleccion_compartida

for _sitio in ("t_a", "t_b"):
    eleccion_compartida("t_valor", "Valor", ("Uno", "Dos"), "Uno", _sitio,
                        recarga="t_recarga")
'''


def _pruebas_ajustes_compartidos():
    """Movimientos: «Filtros» tiene sólo lo que vale para todo el reporte
    (regla #644).

    1. EL MISMO VALOR EN VARIOS SITIOS (`base.eleccion_compartida`): elegido
       en uno, sale elegido en el otro, y pide la corrida completa. Con
       AppTest, que corre el Streamlit de verdad.
    2. «FILTROS» SÓLO TIENE LOS CHIPS: adentro del `compartimento_filtros`
       de Movimientos no se llama a nada más que `filtro_pills`. Las fechas,
       la comparación y la valorización estaban ahí y no decían a qué vistas
       cambiaban.
    3. CADA AJUSTE DEL PIE se ve en TODAS las vistas que gobierna (al menos
       dos visibles: si no, no es compartido), y cada categoría del pie es
       la de una vista de verdad.
    4. QUIEN LEE LA VALORIZACIÓN LA MUESTRA: toda función de Movimientos que
       llama a `valorizacion()` dibuja también `control_valorizacion`. Una
       tarjeta que valorizara sin el control cambiaría de monto por un clic
       hecho en otra.
    """
    import ast
    import pathlib
    import tempfile

    import graficos.movimientos as mov

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ajustes compartidos · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ajustes compartidos · {nombre}: got={got!r} exp={exp!r}")

    # 1. El mismo valor en dos sitios.
    try:
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as tmp:
            script = pathlib.Path(tmp) / "eleccion_compartida.py"
            script.write_text(_SCRIPT_ELECCION_COMPARTIDA, encoding="utf-8")
            at = AppTest.from_file(str(script), default_timeout=30)
            at.run()
            check("abre en el default, en los dos sitios",
                  [at.segmented_control(key=k).value
                   for k in ("t_a_uno", "t_b_uno")], ["Uno", "Uno"])
            at.segmented_control(key="t_a_uno").set_value("Dos").run()
            check("elegido en uno, sale elegido en el otro",
                  [at.segmented_control(key=k).value
                   for k in ("t_a_dos", "t_b_dos")], ["Dos", "Dos"])
            check("el valor vive en su clave",
                  at.session_state["t_valor"], "Dos")
            check("y pide la corrida completa",
                  at.session_state["t_recarga"], True)
            at.session_state["t_recarga"] = False
            at.segmented_control(key="t_b_dos").set_value("Uno").run()
            check("y de vuelta desde el otro",
                  ([at.segmented_control(key=k).value
                    for k in ("t_a_uno", "t_b_uno")],
                   at.session_state["t_valor"]), (["Uno", "Uno"], "Uno"))
            check("sin excepciones", [e.value for e in at.exception], [])
    except Exception as e:  # el arnés en sí: que se vea qué se movió
        fallos += 1
        print(f"FALLA ajustes compartidos · el arnés no corrió: "
              f"{type(e).__name__}: {e}")

    # 2. «Filtros» sólo con los chips.
    raiz = pathlib.Path(__file__).parent
    arbol = ast.parse((raiz / "graficos" / "movimientos.py")
                      .read_text(encoding="utf-8"))
    adentro = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.With):
            continue
        if not any(isinstance(i.context_expr, ast.Call)
                   and getattr(i.context_expr.func, "id", "")
                   == "compartimento_filtros" for i in nodo.items):
            continue
        for sub in nodo.body:
            for c in ast.walk(sub):
                if isinstance(c, ast.Call):
                    f = c.func
                    adentro.append(f.id if isinstance(f, ast.Name)
                                   else getattr(f, "attr", "?"))
    check("«Filtros» de Movimientos dibuja sólo los chips",
          sorted(set(adentro)), ["filtro_pills"])

    # 3. Los ajustes del pie.
    cats = set(mov.CATEGORIA_VISTA.values())
    check("cada pie es el de una vista de verdad",
          sorted(set(mov.AJUSTES_PIE) - cats), [])
    check("cada ajuste del pie existe",
          sorted({a for v in mov.AJUSTES_PIE.values() for a in v}
                 - set(mov._AJUSTES)), [])
    for ajuste in mov._AJUSTES:
        check(f"«{mov._AJUSTES[ajuste][1]}» se ve en dos vistas o más",
              len(mov.vistas_con_ajuste(ajuste)) >= 2, True)
    check("las salidas comparan en su vista y en la de área",
          mov.vistas_con_ajuste("comparar", salvo="sal_periodo"),
          ["Salidas por Área"])

    # 4. Quien lee la valorización la muestra.
    sin_control = []
    for modulo in ("movimientos.py", "movimientos_merma.py"):
        arbol = ast.parse((raiz / "graficos" / modulo)
                          .read_text(encoding="utf-8"))
        for fn in ast.walk(arbol):
            if not isinstance(fn, ast.FunctionDef) or fn.name == "valorizacion":
                continue
            llamadas = {c.func.id for c in ast.walk(fn)
                        if isinstance(c, ast.Call)
                        and isinstance(c.func, ast.Name)}
            # Las funciones anidadas cuentan en la de afuera y en ellas
            # mismas: se mira la más chica que lee el valor.
            hijas = [h for h in ast.walk(fn) if h is not fn
                     and isinstance(h, ast.FunctionDef)
                     and any(isinstance(c, ast.Call)
                             and getattr(c.func, "id", "") == "valorizacion"
                             for c in ast.walk(h))]
            if "valorizacion" in llamadas and not hijas \
                    and "control_valorizacion" not in llamadas:
                sin_control.append(f"{modulo}::{fn.name}")
    check("quien lee la valorización dibuja su control", sin_control, [])
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
    for py, texto in _fuentes_py(raiz):
        if py.name in ("alturas.py", "_css_proveedor.py"):
            continue
        for i, linea in enumerate(texto.split("\n"), 1):
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
    for py, texto in _fuentes_py(raiz):
        for i, linea in enumerate(texto.split("\n"), 1):
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
    aire = _var("aire-inferior")
    margen = _var("margen-tarjeta")
    check("las variables de cromo existen en estilos/_00_base.py",
          None not in (cab, aire, margen),
          f"cab={cab} aire={aire} margen={margen}")
    if None not in (cab, aire, margen):
        suma_css = cab + aire + margen * 2
        check("el cromo de CSS coincide con alturas.CROMO",
              suma_css == alturas.CROMO,
              f"CSS suma {suma_css}px y alturas.CROMO vale {alturas.CROMO}px")

    # ── 3) Los roles entran en el presupuesto ───────────────────────────
    check("PROTAGONISTA + padding entra en el presupuesto",
          alturas.cabe(alturas.PROTAGONISTA + 32),
          f"{alturas.PROTAGONISTA} + 32 > {alturas.PRESUPUESTO}")
    check("los roles están ordenados (MINI ≤ COMPACTO ≤ APOYO ≤ PROTAGONISTA)",
          alturas.MINI <= alturas.COMPACTO <= alturas.APOYO
          <= alturas.PROTAGONISTA)
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
    # Ahora se declaran en _00_base.py, dueño único. Hasta el 2026-08-26
    # también las redefinía el pestillo (`_25_rails_pestillo.py`, borrado
    # junto con `pestillos.py` a ese pedido — "eliminemos esto y que las
    # filas de los reportes del rail suban": sin plegado no hay un tercer
    # estado que fijar). Si `--rail-der-w`/`--rail-der-res` aparecen en un
    # tercer sitio ahora, es doble declaración lisa y llana.
    #
    # El barrido va por `_fuentes_py`, que deja fuera `.claude/worktrees/`:
    # esta guarda fallaba citando el `_25_rails_pestillo.py` de un worktree
    # viejo, o sea un fichero que este repo ya no tiene. Y la ruta se
    # reporta RELATIVA al repo, no `py.name` a secas — con el nombre pelado
    # el intruso de un worktree se lee igual que uno de casa, que fue
    # exactamente lo que costó el diagnóstico.
    _duenos = {"_00_base.py"}
    raiz_repo = pathlib.Path(__file__).parent
    intrusos = []
    for py, texto in _fuentes_py(raiz_repo):
        if py.name in _duenos or py.name == pathlib.Path(__file__).name:
            continue
        for i, linea in enumerate(texto.split("\n"), 1):
            if re.search(r"--rail-(izq|der)-w\s*:|--rail-der-res\s*:"
                         r"|--rail-reserva\s*:", linea):
                intrusos.append(f"{py.relative_to(raiz_repo).as_posix()}:{i}")
    check("los anchos de rail solo los declara _00_base",
          not intrusos, ", ".join(intrusos[:6]))

    # La reserva del contenido se DERIVA, no se escribe: un valor fijo en
    # otro sitio se desincroniza en cuanto cambie de quién depende.
    #
    # De quién depende cambió el 2026-09-18: hasta entonces la columna
    # ocupaba su ancho (`--rail-der-w`) y el contenido se lo reservaba
    # entero; desde que es una CAPA que aparece con el cursor
    # (`_26_rails_scroll.py`) lo único que reserva es la tira por donde se
    # la despierta (`--rail-reserva`), igual que hizo la franja de reportes
    # al pasar a capa. Lo que la guarda vigila es lo mismo de siempre: que
    # sea un `calc()` sobre la variable y no un número medido a ojo.
    check("--rail-der-res se deriva de --rail-reserva, no es un px suelto",
          re.search(r"--rail-der-res:\s*calc\([^)]*--rail-reserva",
                    css) is not None)

    return fallos


def _pruebas_js_inyectado_sano():
    """Que el JS que vive dentro de un string de Python siga siendo JS.

    Sale de un bug del 2026-08-31: al sumar la selección múltiple al modo
    diseño se escribió el escape de salto de línea con UNA barra dentro de
    `_diseno_js.py`. Python lo convierte en un salto REAL al importar el
    módulo, y JS —que no admite saltos dentro de comillas simples ni
    dobles— muere con "Invalid or unexpected token". El modo diseño entero
    dejó de montarse.

    Lo peligroso es que NADA lo ve: `ruff` valida Python y el string es
    Python válido; los tests de figuras no cargan el JS; y en el navegador
    el síntoma es una herramienta que simplemente no aparece, sin traza
    útil. Se descubrió mirando la consola a mano.

    Esta guarda importa el módulo (o sea, ve el JS ya interpolado, que es
    lo que llega al navegador) y busca strings abiertos por un salto sin
    escapar. No es un parser de JS: cubre exactamente la clase de error que
    produce el escapado de dos niveles.

    Ojo al tocarla: acá NO se escriben literales de salto de línea, se usa
    `chr(10)`. Escribirlos fue lo que rompió el intento anterior de este
    mismo test — el bug que vigila se lo llevó puesto mientras nacía.
    """
    fallos = 0
    BARRA = chr(92)
    SALTO = chr(10)

    def strings_rotos(js):
        malos, i, n, linea = [], 0, len(js), 1
        while i < n:
            c = js[i]
            if c == SALTO:
                linea += 1
                i += 1
                continue
            if c == "/" and i + 1 < n and js[i + 1] == "/":
                while i < n and js[i] != SALTO:
                    i += 1
                continue
            if c == "/" and i + 1 < n and js[i + 1] == "*":
                i += 2
                while i + 1 < n and not (js[i] == "*" and js[i + 1] == "/"):
                    if js[i] == SALTO:
                        linea += 1
                    i += 1
                i += 2
                continue
            if c in ('"', "'"):
                comienzo, j = linea, i + 1
                while j < n:
                    if js[j] == BARRA:
                        j += 2
                        continue
                    if js[j] == c:
                        break
                    if js[j] == SALTO:
                        malos.append((comienzo, js[i:i + 50]))
                        break
                    j += 1
                i = j + 1
                continue
            i += 1
        return malos

    import importlib

    for modulo in ("inyecciones._diseno_js", "inyecciones._inspector_js"):
        mod = importlib.import_module(modulo)
        rotos = []
        for nombre, val in vars(mod).items():
            if not isinstance(val, str) or len(val) < 2000:
                continue
            rotos += [(nombre, ln, frag) for ln, frag in strings_rotos(val)]
        if rotos:
            fallos += 1
            print(f"FALLA js · {modulo}: {len(rotos)} string(s) sin cerrar")
            for nombre, ln, frag in rotos[:5]:
                print(f"        {nombre} línea ~{ln}: {frag!r}")
        else:
            print(f"OK    js · {modulo} sin strings rotos")

    return fallos


def _pruebas_hook_del_rail_bajo_secciones():
    """Que el scrollspy de la pila siga colgando de `secciones` y no de
    otra cosa.

    Bug real, 2026-09-13, reportado como "¿por qué la tarjeta que dice Por
    familia no es visible?". El bloque que inyecta el temporizador del rail
    —el que marca la sección que estás mirando y APRIETA el botón invisible
    de la que se acerca— vivía a nivel de función desde el 2026-08-25. El
    `if estados:` del semáforo del rail (2026-09-07) se insertó encima y se
    lo TRAGÓ: en Python, un bloque que queda más adentro es sintaxis
    válida, no hay error ni warning, y los tests seguían en verde porque
    ninguno miraba la estructura.

    Consecuencia, seis días sin que nadie la viera: `estados` lo pasa UN
    solo dashboard (Compras). En los otros cinco —Inventario, Ventas,
    Movimientos, Recetas, Ajuste— el temporizador no se inyectaba y las
    secciones de la pila se quedaban en esqueleto para siempre. Nadie
    aprieta ese botón a mano: es invisible a propósito.

    Lo que despistaba el diagnóstico: `window.__railTimer` SÍ existía en
    Inventario. Era el de Compras, que sobrevive al cambio de reporte
    (`setInterval` global, y el `clearInterval` que lo reemplaza sólo corre
    si el script nuevo se inyecta). O sea: la variable global no prueba que
    el script esté montado; lo prueba el `srcdoc` del iframe.

    La guarda es estructural y mira el árbol, no el texto: el `with
    st.container(key="rail_scroll_hook")` tiene que tener ARRIBA, entre sus
    ancestros, un `if` cuyo test sea exactamente el nombre `secciones`.
    """
    import ast
    import pathlib

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    rail · {nombre}")
        else:
            fallos += 1
            print(f"FALLA rail · {nombre}{': ' + detalle if detalle else ''}")

    ruta = pathlib.Path(__file__).parent / "graficos" / "base.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))

    # Padres, para poder subir del `with` a sus `if`.
    padre = {}
    for nodo in ast.walk(arbol):
        for hijo in ast.iter_child_nodes(nodo):
            padre[hijo] = nodo

    def _es_el_hook(nodo):
        if not isinstance(nodo, ast.With):
            return False
        return "rail_scroll_hook" in ast.dump(nodo.items[0].context_expr
                                              if nodo.items else nodo)

    hooks = [n for n in ast.walk(arbol) if _es_el_hook(n)]
    check("el hook del scrollspy sigue existiendo", len(hooks) == 1,
          f"encontrados {len(hooks)}")
    if not hooks:
        return fallos

    # La guarda es `if secciones is not None:` desde el 2026-09-30: una
    # tupla VACÍA es un reporte sin pila (Documentos SUNAT, regla #577) y
    # también lleva el temporizador. Se acepta el nombre suelto o comparado.
    guardas = []
    n = padre.get(hooks[0])
    while n is not None:
        if isinstance(n, ast.If):
            _t = n.test
            if isinstance(_t, ast.Compare) and isinstance(_t.left, ast.Name):
                _t = _t.left
            if isinstance(_t, ast.Name):
                guardas.append(_t.id)
        n = padre.get(n)

    check("el hook cuelga de `secciones`", "secciones" in guardas,
          f"guardas vistas: {guardas or 'ninguna'}")
    check("y NO quedó dentro del `if estados:`", "estados" not in guardas,
          "lo tragó el if del semáforo: sólo Compras inyectaría el timer")
    return fallos


def _pruebas_vistas_de_cada_reporte():
    """El panel de cada reporte en el rail dice lo mismo que su rail.

    2026-09-29, regla #568: el cursor sobre un reporte de la columna abre un
    panel con sus vistas, y un clic en una entra al reporte ya parado en
    ella. Para eso `graficos.vistas_de` tiene un registro, `_RAILS`, con las
    categorías de cada dashboard y la clave de `session_state` donde su
    rail guarda la vista elegida. Se rompe EN SILENCIO de dos maneras:

      · un dashboard nuevo que se suma a `_DASHBOARDS` y no a `_RAILS`: su
        reporte queda sin panel, y nada lo avisa;
      · una clave que no es la que el dashboard le pasa a `_render_rail`:
        el panel abre el reporte y la vista pedida NO se elige — la página
        abre en la primera y el salto no encuentra su sección.

    Así que se lee, con `ast`, la llamada a `_render_rail` de cada
    dashboard, y se exige que sus categorías sean EL MISMO objeto del
    registro y su clave, la misma cadena.
    """
    import ast
    import inspect
    import graficos
    from graficos import _DASHBOARDS, _RAILS, vistas_de

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    panel · {nombre}")
        else:
            fallos += 1
            print(f"FALLA panel · {nombre}{': ' + detalle if detalle else ''}")

    check("cada dashboard tiene su rail registrado",
          set(_DASHBOARDS) == set(_RAILS),
          f"faltan {sorted(set(_DASHBOARDS) - set(_RAILS))}, "
          f"sobran {sorted(set(_RAILS) - set(_DASHBOARDS))}")
    for rep, render in _DASHBOARDS.items():
        par = vistas_de(rep)
        check(f"{rep}: tiene vistas", bool(par and par[1]))
        if rep not in _RAILS:
            continue
        cats, clave = _RAILS[rep]
        mod = inspect.getmodule(render)
        llamadas = [n for n in ast.walk(ast.parse(inspect.getsource(mod)))
                    if isinstance(n, ast.Call)
                    and getattr(n.func, "id", None) == "_render_rail"]
        ok = False
        for c in llamadas:
            if (len(c.args) >= 2 and isinstance(c.args[0], ast.Name)
                    and isinstance(c.args[1], ast.Constant)):
                ok = ok or (getattr(mod, c.args[0].id, None) is cats
                            and c.args[1].value == clave)
        check(f"{rep}: `_RAILS` usa las categorías y la clave de su "
              f"`_render_rail` ({clave})", ok,
              f"{len(llamadas)} llamada(s) en {mod.__name__}")
    check("reporte sin dashboard: sin panel", vistas_de("Inspector") is None)
    check("`vistas_de` no deja pasar una Tabla oculta (#507)",
          all(not graficos.base.es_vista_tabla(v[0])
              for r in _RAILS for v in vistas_de(r)[1])
          or graficos.base.MOSTRAR_VISTAS_TABLA)
    return fallos


def _pruebas_vistas_tabla_ocultas():
    """Las vistas «Tabla» siguen ocultas, y siguen DECLARADAS.

    2026-09-23, a pedido («podemos ocultarlas hasta nuevo aviso»): las ocho
    vistas «Tabla» —el volcado AgGrid del parquet, una por reporte y dos en
    Recetas y en Movimientos— salen del rail y de la pila con el interruptor
    `graficos.base.MOSTRAR_VISTAS_TABLA`. Cada dashboard las sigue
    declarando y las filtra en la declaración, con `rail_sin_tablas` y
    `pila_sin_tablas` (regla #507).

    Lo que se vigila es lo que se rompe EN SILENCIO:
      · un rail o una pila declarados SIN el filtro (un dashboard nuevo, o
        uno reescrito): su Tabla volvería a salir sin que nadie lo decida;
      · el filtro en una sola mitad. Con la Tabla en la pila y no en el
        rail, la sección se dibuja al pie de la página sin botón que la
        nombre; al revés, el rail la muestra como destino aparte, con su
        línea divisoria y nada detrás. Por eso: toda vista de la pila tiene
        su botón en el rail;
      · que alguien BORRE una declaración por creerla código muerto. El día
        que se prenda el interruptor tienen que volver las ocho, así que la
        lista va con nombre y apellido: sacar una de verdad es tocar esta
        prueba, a conciencia.
    """
    import ast
    import inspect
    import graficos.base as gb
    from graficos import _DASHBOARDS

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    tablas · {nombre}")
        else:
            fallos += 1
            print(f"FALLA tablas · {nombre}{': ' + detalle if detalle else ''}")

    # ── Qué es «la Tabla»: el nombre, y nada más que el nombre ───────────
    for oid, esperado in (("Tabla", True), ("Tabla · platos", True),
                          ("Tabla · requerim.", True), ("Tablas", False),
                          ("Tabla dinámica", False),
                          ("Detalle por producto", False),
                          ("Documentos por proveedor", False)):
        check(f"es_vista_tabla({oid!r}) es {esperado}",
              gb.es_vista_tabla(oid) is esperado)

    # ── Los filtros, con el interruptor en las dos posiciones ───────────
    # Los dos casos que existen de verdad: una categoría que sólo tenía la
    # Tabla («Datos» de Ajuste/Inventario/Ventas) se va entera; una que la
    # comparte («Más» de Compras) se queda con lo demás.
    rail = (("Vista", (("A", "A"),)),
            ("Datos", (("Tabla", "Tabla"),)),
            ("Más", (("Tabla · x", "Tabla"), ("B", "B"))))
    pila = (("sec_a", "A"), ("sec_t", "Tabla"), ("sec_tx", "Tabla · x"),
            ("sec_b", "B"))
    _antes = gb.MOSTRAR_VISTAS_TABLA
    try:
        gb.MOSTRAR_VISTAS_TABLA = False
        check("apagadas: el rail pierde la Tabla y la categoría que quedó vacía",
              gb.rail_sin_tablas(rail)
              == (("Vista", (("A", "A"),)), ("Más", (("B", "B"),))),
              repr(gb.rail_sin_tablas(rail)))
        check("apagadas: la pila pierde sus secciones de Tabla",
              gb.pila_sin_tablas(pila) == (("sec_a", "A"), ("sec_b", "B")),
              repr(gb.pila_sin_tablas(pila)))
        gb.MOSTRAR_VISTAS_TABLA = True
        check("prendidas: el rail vuelve tal cual",
              gb.rail_sin_tablas(rail) is rail)
        check("prendidas: la pila vuelve tal cual",
              gb.pila_sin_tablas(pila) is pila)
    finally:
        gb.MOSTRAR_VISTAS_TABLA = _antes

    # ── Los seis dashboards de verdad ────────────────────────────────────
    # Las ocho que se ocultaron el 2026-09-23. Tienen que seguir DECLARADAS
    # en el rail y en la pila de su reporte: el interruptor las devuelve
    # sólo si siguen ahí.
    _ESPERADAS = {
        ("Ajuste de Inventario", "Tabla"),
        ("Compras", "Tabla"),
        ("Inventario Valorizado", "Tabla"),
        ("Ventas", "Tabla"),
        ("Recetas", "Tabla · platos"),
        ("Recetas", "Tabla · recetas base"),
        ("Movimientos", "Tabla · requerim."),
        ("Movimientos", "Tabla · salidas"),
    }
    decl_rail, decl_pila = set(), set()
    for reporte, fn in sorted(_DASHBOARDS.items()):
        mod = sys.modules[fn.__module__]
        rails = {k: v for k, v in vars(mod).items()
                 if k.endswith("RAIL_CATEGORIAS") and isinstance(v, tuple)}
        pilas = {k: v for k, v in vars(mod).items()
                 if k.startswith("_PILA") and isinstance(v, tuple)}
        check(f"{reporte}: un rail y al menos una pila a nivel de módulo",
              len(rails) == 1 and len(pilas) >= 1,
              f"rails={sorted(rails)} pilas={sorted(pilas)} en {fn.__module__}")

        # Cómo se DECLARÓ cada constante: por `ast`, que ve la llamada al
        # filtro y el literal que recibe (el texto, con sus comentarios,
        # mentiría en cuanto alguien nombrara la función en uno).
        envueltas = {}
        for nodo in ast.parse(inspect.getsource(mod)).body:
            if (isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                    and isinstance(nodo.targets[0], ast.Name)
                    and isinstance(nodo.value, ast.Call)
                    and isinstance(nodo.value.func, ast.Name)
                    and len(nodo.value.args) == 1):
                envueltas[nodo.targets[0].id] = (
                    nodo.value.func.id, nodo.value.args[0])
        for nombre in rails:
            func, arg = envueltas.get(nombre, (None, None))
            check(f"{reporte}: {nombre} se declara con rail_sin_tablas",
                  func == "rail_sin_tablas", f"se declara con {func!r}")
            if func == "rail_sin_tablas":
                decl_rail |= {(reporte, it[0])
                              for _, items in ast.literal_eval(arg)
                              for it in items if gb.es_vista_tabla(it[0])}
        for nombre in pilas:
            func, arg = envueltas.get(nombre, (None, None))
            check(f"{reporte}: {nombre} se declara con pila_sin_tablas",
                  func == "pila_sin_tablas", f"se declara con {func!r}")
            if func == "pila_sin_tablas":
                decl_pila |= {(reporte, s[1]) for s in ast.literal_eval(arg)
                              if gb.es_vista_tabla(s[1])}

        ids_rail = {it[0] for v in rails.values()
                    for _, items in v for it in items}
        ids_pila = {s[1] for v in pilas.values() for s in v}
        check(f"{reporte}: toda vista de la pila tiene su botón en el rail",
              ids_pila <= ids_rail, f"sin botón: {sorted(ids_pila - ids_rail)}")
        if not gb.MOSTRAR_VISTAS_TABLA:
            _quedan = sorted(o for o in ids_rail | ids_pila
                             if gb.es_vista_tabla(o))
            check(f"{reporte}: ninguna «Tabla» a la vista", not _quedan,
                  f"quedaron: {_quedan}")

    check("las ocho Tablas siguen declaradas en su rail",
          decl_rail == _ESPERADAS,
          f"faltan {sorted(_ESPERADAS - decl_rail)}, "
          f"sobran {sorted(decl_rail - _ESPERADAS)}")
    check("y en su pila", decl_pila == _ESPERADAS,
          f"faltan {sorted(_ESPERADAS - decl_pila)}, "
          f"sobran {sorted(decl_pila - _ESPERADAS)}")
    return fallos


def _pruebas_jscode_barato():
    """Que nadie vuelva a meter un payload de DATOS dentro de un `JsCode`.

    Sale de un cuelgue medido el 2026-08-27 en el «Conversor
    SUNAT-Sistema»: bajaba el catálogo de 3.867 productos al navegador
    interpolándolo en el `onGridReady`, o sea 110.082 caracteres pasando
    por `JsCode(...)`. `JsCode.__init__` (st_aggrid 1.2.1) corre sobre el
    código un regex cuyo lookahead cuenta comillas de a pares hasta el
    final del texto —y por lo tanto retrocede de forma catastrófica—, y
    encima descarta el resultado dos líneas más abajo. Medido: 4.000
    caracteres 0,10s; 8.000, 0,34s; 16.000, 1,35s. Cuadrático limpio, así
    que los 110.082 reales daban **~64 segundos por render**, en cada
    selección de documento y en cada celda corregida. El usuario lo
    reportó como "se cuelga y se pone lento" y no había nada raro que ver
    en el código: la llamada es una línea. La cura fue
    `gridOptions.context`, que es dato plano y no pasa por ese regex.

    DOS GUARDAS, y ninguna es un detector genérico de interpolación: casi
    todos los `JsCode` del proyecto se arman con f-string o `%` para
    meterles un color de `tema.py`, y marcarlos a todos sería ruido que
    haría que nadie mire la salida (mismo criterio que `ruff.toml`, que
    corre sólo `F`). Lo que se persigue es el TAMAÑO, que es lo que
    dispara el regex, y el sitio puntual donde ya pasó:

      1. Ningún `JsCode(...)` con más de `TOPE` caracteres en el fuente —
         cubre el caso de pegar una tabla como literal. El tope está
         holgado a propósito: el JsCode más largo del proyecto son 2.691
         caracteres de componente escrito a mano (`tablas/desktop.py`) y
         eso cuesta ~0,04s, que no molesta a nadie.
      2. Que el conversor siga bajando su catálogo por `context=` y que
         su `onGridReady` siga siendo una CONSTANTE, no una plantilla que
         alguien vuelva a rellenar con `%`.
    """
    import pathlib
    import re

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    jscode · {nombre}")
        else:
            fallos += 1
            print(f"FALLA jscode · {nombre}{': ' + detalle if detalle else ''}")

    raiz = pathlib.Path(__file__).parent
    TOPE = 8000

    # ── 1) Ningún JsCode gigante en el fuente ───────────────────────────
    largos = []
    # Los worktrees de `.claude/` son copias viejas del repo: medirlas
    # reporta bugs ya arreglados en sitios que nadie va a editar. El filtro
    # vive en `_fuentes_py` — acá estaba escrito a mano y comparaba los
    # componentes de la ruta ABSOLUTA, con lo que al correr el test desde un
    # worktree descartaba el repo entero y la guarda medía cero ficheros.
    for py, texto in _fuentes_py(raiz):
        for m in re.finditer(r"JsCode\(", texto):
            # El argumento: del paréntesis de apertura al que lo cierra.
            i, nivel = m.end(), 1
            while i < len(texto) and nivel:
                nivel += (texto[i] == "(") - (texto[i] == ")")
                i += 1
            if i - m.end() - 1 > TOPE:
                linea = texto[:m.start()].count("\n") + 1
                largos.append(f"{py.relative_to(raiz)}:{linea} "
                              f"({i - m.end() - 1} chars)")
    check(f"ningún JsCode con más de {TOPE} caracteres de código",
          not largos, ", ".join(largos[:5]))

    # ── 2) El conversor baja su catálogo por `context`, no por JsCode ───
    conv = (raiz / "graficos" / "compras" / "documentos_sunat.py").read_text(
        encoding="utf-8")
    check("el catálogo del conversor viaja en gridOptions.context",
          "context=_lookups_maestro()" in conv,
          "no aparece `context=_lookups_maestro()`")
    check("el onGridReady del conversor es una constante, no una plantilla",
          "_JS_MAESTRO_AL_NAVEGADOR = JsCode(" in conv
          and not re.search(r"_JS_MAESTRO_AL_NAVEGADOR\s*%", conv),
          "volvió a rellenarse con `%`")
    return fallos


def _pruebas_css_clonado():
    """Que el CSS del tercer prefijo (`cp_docs`) siga saliendo del molde.

    `_css_proveedor.py::clonar_prefijo` genera las reglas de la tarjeta
    «Detalle de documentos por proveedor» a partir de las del Ranking de
    productos, en vez de pegarlas a mano en 41 grupos de selectores.

    Lo que vigila esto es el modo en que ese clonador puede fallar EN
    SILENCIO: salta los bloques de at-rule enteros, asi que el dia que
    una regla de `cp_prod` se mude adentro de un `@media`, deja de
    clonarse y su gemela de `cp_docs` simplemente no existe — la tarjeta
    se ve rota sin que nada avise. El contador lo caza.
    """
    fallos = 0

    def check(nombre, cond, detalle=""):
        nonlocal fallos
        print(("OK    " if cond else "FALLA ") + "css clonado · " + nombre
              + (("  " + str(detalle)) if (detalle and not cond) else ""))
        if not cond:
            fallos += 1

    from graficos.compras import _css_proveedor as cssp
    clon = cssp.CSS_CP_DOCS
    n = clon.count("{")
    # 41 el 2026-09-04; 27 desde el 2026-10-08, cuando se fueron las 14 de
    # la escala de tiempo vieja (regla #618). El umbral va abajo del numero
    # real a proposito: que alguien SUME reglas a `cp_prod` no tiene por
    # que romper el test, pero que se caigan a la mitad si.
    check("se clonan las reglas de cp_prod (>=23)", n >= 23, n)
    check("el clon no quedo vacio", bool(clon.strip()))
    check("llaves balanceadas en el clon",
          clon.count("{") == clon.count("}"), n)
    check("llaves balanceadas en el CSS final",
          cssp.CSS.count("{") == cssp.CSS.count("}"))
    # Si un prefijo AJENO sobrevive al clon, la regla se re-declara al
    # final de la hoja y pisa lo que viniera despues para esa otra
    # tarjeta. Es el bug que `_solo_de` existe para evitar.
    ajenos = [x for x in ("cp_rank", "cp_prod", "cp_sem", "cp_vol")
              if x in clon]
    check("el clon habla SOLO de cp_docs", not ajenos, ", ".join(ajenos))
    # La clase del titulo no sigue la convencion de las keys, asi que va
    # por `extra=`; si eso se cae, el titulo pierde su truncado.
    check("el titulo usa la clase generica",
          "cp-prod-rank-tit" not in clon)
    return fallos

def _pruebas_container_queries():
    """Que ningún `@container` quede SIN contenedor (regla #317).

    Una media query que no matchea se ve: el layout no cambia y uno va a
    mirar el breakpoint. Una CONTAINER query sin contenedor no se ve: si
    ningún ancestro declara `container-type`, la consulta es falsa SIEMPRE
    y el navegador no dice nada. El `.pb-card .grid` del Panel B de
    Proveedor vivió meses así — la regla estaba escrita, comentada y citada
    en el docstring de `COLUMNAS_DRILL`, y no colapsaba nunca; se veía como
    valores recortados («ÚLT. 06/…»), que parece un problema de anchos.

    Dos guardas, las dos objetivas:

      1. Todo `@container` lleva NOMBRE. Sin nombre, la consulta se ata al
         contenedor más cercano —que puede ser otro, o ninguno— y no hay
         forma de verificar a cuál apunta.
      2. Ese nombre lo declara alguien, con su `container-type` al lado.

    No juzga el umbral ni dónde vive la regla: sólo que la consulta tenga
    contra qué medir.
    """
    import pathlib
    import re

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    container · {nombre}")
        else:
            fallos += 1
            print(f"FALLA container · {nombre}"
                  f"{': ' + detalle if detalle else ''}")

    raiz = pathlib.Path(__file__).parent
    fuentes = list(_fuentes_py(raiz))

    # `@container <nombre> (...)` vs `@container (...)`. El nombre es un
    # ident CSS; lo que sigue a la condición no interesa acá.
    _RE_USO = re.compile(r"@container\s+([^\s({][^\s(]*)?\s*\(")
    _RE_DECL = re.compile(r"container-name\s*:\s*([A-Za-z_-][\w-]*)")
    _RE_TIPO = re.compile(r"container-type\s*:\s*(\w[\w -]*)")

    anonimas, usados = [], {}
    declarados, con_tipo = set(), set()
    for py, texto in fuentes:
        if py.name == pathlib.Path(__file__).name:
            continue
        rel = py.relative_to(raiz).as_posix()
        for i, linea in enumerate(texto.split("\n"), 1):
            for m in _RE_USO.finditer(linea):
                if m.group(1):
                    usados.setdefault(m.group(1), f"{rel}:{i}")
                else:
                    anonimas.append(f"{rel}:{i}")
            for m in _RE_DECL.finditer(linea):
                declarados.add(m.group(1))
        # `container-type` y `container-name` viven en el mismo bloque,
        # pero no en la misma línea: se buscan en todo el fichero.
        if _RE_TIPO.search(texto):
            con_tipo |= {m.group(1) for m in _RE_DECL.finditer(texto)}

    check("todo @container consulta un contenedor con NOMBRE",
          not anonimas, ", ".join(anonimas[:6]))

    huerfanas = {n: donde for n, donde in usados.items()
                 if n not in declarados}
    check("todo @container apunta a un container-name declarado",
          not huerfanas,
          ", ".join(f"{n} ({d})" for n, d in list(huerfanas.items())[:6]))

    sin_tipo = {n for n in usados if n in declarados and n not in con_tipo}
    check("todo container-name viene con su container-type",
          not sin_tipo, ", ".join(sorted(sin_tipo)[:6]))

    # Positiva: sin esto, borrar TODAS las container queries dejaría las
    # tres guardas de arriba en verde. Hoy la única es la del Panel B.
    check("el repo sigue teniendo alguna container query", bool(usados))

    return fallos


def _pruebas_producto_lista_y_ficha():
    """Compras › Producto: la lista y la ficha (2026-10-13, regla #653).

    Las cuentas son puras y se prueban por valor, sin Streamlit, sin R2 y
    sin red. Lo que se puede romper en silencio y acá falla ruidoso:

      1. Que los niveles dejen de CUADRAR: la suma de una familia tiene que
         dar la de sus productos, y la de una subfamilia la de los suyos.
      2. Que el recorte por subfamilia se haga por la subfamilia SOLA. La
         clave es el PAR (familia, subfamilia): «Varios» está en A y en B.
      3. Que una compra mal cargada entre en el PRECIO. La marca «revisar»
         (`marcar_revisar`) la deja en la cantidad y el valor y la saca del
         precio ponderado, del «vs. habitual» y de su impacto en soles —
         sin eso el lomo fino mostraba un ahorro de S/ 861 que era, entero,
         una compra cargada a S/ 15,85 el kilo.
      4. Que el período en curso se lea como entero: la curva arranca al
         INICIO de su período, el último va «parcial» y se compara con los
         mismos días del anterior.
      5. Que el «nuevo» y el «vuelve» se confundan con un Δ: sin compras en
         el período anterior no hay porcentaje.
    """
    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    producto · {nombre}")
        else:
            fallos += 1
            print(f"FALLA producto · {nombre}{': ' + str(detalle)[:300] if detalle else ''}")

    import numpy as np

    from graficos.compras.producto import (
        _ambito, _con_referencia, _etq, _normalizar, _precios, _resumen,
        _serie, marcar_revisar,
    )

    # ── La marca «revisar» ──────────────────────────────────────────────
    m = marcar_revisar(pd.Series([4.5, 15.0, 2.0, 6.0, 3.0]),
                       pd.Series([706.8, 237.75, 30.0, 600.0, 900.0]),
                       pd.Series([117.8, 74.5, 8.0, 100.0, np.nan]),
                       pd.Series(["UND", "KILOS", "KILOS", "UND", "KILOS"]))
    check("6 botellas cargadas como 4,5 UND se marcan «um»", m[0] == "um", m)
    check("15 kg de lomo a S/ 15,85 (0,21 veces el habitual) se marcan",
          m[1] == "precio", m)
    check("una línea chica no se marca aunque su precio salte", m[2] == "", m)
    check("6 UND al precio habitual no se marcan", m[3] == "", m)
    check("sin precio habitual no hay contra qué marcar", m[4] == "", m)

    # ── Datos: un rango (1–30 set) y su período anterior (2–31 ago) ─────
    filas = [
        # FAM, SUB,      PROD,     VAL,    CANT, UM,      FECHA,       PROV, DOC
        ("A", "Carnes",  "Lomo",   745.0, 10.0, "KILOS", "2026-01-15", "P1", "F00"),
        ("A", "Carnes",  "Lomo",   745.0, 10.0, "KILOS", "2026-08-10", "P1", "F1"),
        ("A", "Carnes",  "Lomo",   745.0, 10.0, "KILOS", "2026-09-04", "P1", "F2"),
        ("A", "Carnes",  "Lomo",   237.75, 15.0, "KILOS", "2026-09-19", "P1", "F3"),
        ("A", "Carnes",  "Lomo",   800.0, 10.0, "KILOS", "2026-09-22", "P2", "F4"),
        ("A", "Carnes",  "Asado",  200.0,  5.0, "KILOS", "2026-09-05", "P1", "F2"),
        ("A", "Varios",  "Bolsa",   50.0, 100.0, "UND",  "2026-09-06", "P3", "F5"),
        ("B", "Vinos",   "Malbec", 300.0, 12.0, "UND",   "2026-09-07", "P4", "F6"),
        ("B", "Varios",  "Tapa",    80.0, 40.0, "UND",   "2026-09-08", "P3", "F7"),
        ("B", "Varios",  "Corcho",  20.0, 200.0, "UND",  "2026-03-01", "P3", "F0"),
        ("B", "Varios",  "Corcho",  20.0, 200.0, "UND",  "2026-09-09", "P3", "F8"),
    ]
    df = pd.DataFrame(filas, columns=["FAM", "SUB", "PROD", "VAL", "CANT", "UM",
                                      "FECHA", "PROV", "DOC"])
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    cols = ("PROD", "FAM", "SUB", "VAL", "CANT", "UM", "FECHA", "PROV", "DOC")
    hist = _con_referencia(_normalizar(df, *cols))
    r0, r1 = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-09-30")
    rng = hist[(hist["fecha"] >= r0) & (hist["fecha"] <= r1)]
    prev = hist[(hist["fecha"] >= r0 - pd.Timedelta(days=30))
                & (hist["fecha"] < r0)]
    antes = hist[hist["fecha"] < r0]
    check("la compra de lomo a S/ 15,85 sale marcada",
          rng.loc[rng["valor"] == 237.75, "flag"].tolist() == ["precio"],
          rng[["prod", "valor", "ref", "flag"]].to_dict("records"))

    res_p = _resumen(rng, ["prod"], prev, antes["prod"].unique())
    res_p["fam"] = rng.groupby("prod")["fam"].first().reindex(res_p.index)
    res_p["sub"] = rng.groupby("prod")["sub"].first().reindex(res_p.index)
    res_f = _resumen(rng, ["fam"], prev, antes["fam"].unique())
    res_s = _resumen(rng, ["fam", "sub"], prev,
                     list(antes[["fam", "sub"]].drop_duplicates()
                          .itertuples(index=False, name=None)))

    lomo = res_p.loc["Lomo"]
    check("el valor y la cantidad SÍ suman la compra marcada",
          abs(lomo["valor"] - 1782.75) < 1e-9 and lomo["cant"] == 35.0,
          (lomo["valor"], lomo["cant"]))
    check("el precio ponderado NO la cuenta: (745+800)/(10+10)",
          abs(lomo["pp"] - 77.25) < 1e-9, lomo["pp"])
    check("el impacto del precio no la cuenta (sin ella, +S/ 55)",
          abs(lomo["ppv"] - 55.0) < 1e-9, lomo["ppv"])
    check("el Δ es contra el período anterior de igual largo",
          abs(lomo["var"] - (1782.75 / 745 - 1) * 100) < 1e-9, lomo["var"])
    check("sin compras antes del rango: «nuevo», sin porcentaje",
          res_p.loc["Malbec", "est"] == "nuevo"
          and np.isnan(res_p.loc["Malbec", "var"]))
    check("con compras antes pero no en el anterior: «vuelve»",
          res_p.loc["Corcho", "est"] == "vuelve")
    check("cada familia CUADRA con sus productos",
          all(abs(res_f.loc[f, "valor"]
                  - res_p.loc[res_p["fam"] == f, "valor"].sum()) < 1e-9
              for f in res_f.index))
    check("la subfamilia es el PAR: «Varios» de A no lleva lo de B",
          res_s.loc[("A", "Varios"), "valor"] == 50.0
          and res_s.loc[("B", "Varios"), "valor"] == 100.0,
          res_s["valor"].to_dict())
    amb = _ambito(res_p, "A", "Varios")
    check("el recorte por (A, Varios) no mezcla familias",
          amb.index.tolist() == ["Bolsa"] and amb["valor"].sum() == 50.0,
          amb[["valor"]].to_dict())
    check("sin familia elegida el ámbito es todo lo comprado",
          len(_ambito(res_p, None, "Varios")) == len(res_p))

    sin_sub = _normalizar(df, "PROD", "FAM", None, "VAL", "CANT", "UM",
                          "FECHA", "PROV", "DOC")
    check("sin columna de Subfamilia todo cae en «Sin subfamilia»",
          set(sin_sub["sub"]) == {"Sin subfamilia"})

    # ── La curva ────────────────────────────────────────────────────────
    h = hist[hist["prod"] == "Lomo"]
    ultimo = pd.Timestamp("2026-09-22")
    S = _serie(h, "Mes", "3m", ultimo, (r0, r1))
    check("la ventana de 3 meses arranca el 1° de su mes, no a mitad",
          S["ini"] == pd.Timestamp("2026-06-01"), S["ini"])
    check("los meses sin compras están en el eje",
          S["keys"] == ["2026-06", "2026-07", "2026-08", "2026-09"], S["keys"])
    check("el mes en curso va «parcial», contra los mismos días del anterior",
          S["parc"] is not None and S["refq"] == 10.0, (S["parc"], S["refq"]))
    p, _hab = _precios(S["agg"])
    check("el precio de setiembre es SIN la compra marcada",
          abs(p.loc["2026-09"] - 77.25) < 1e-9 and S["agg"].loc["2026-09", "fl"] == 1,
          p.to_dict())
    check("un mes vacío no tiene precio (no un 0)", np.isnan(p.loc["2026-07"]))
    D = _serie(h, "Documento", "12m", ultimo, (r0, r1))
    check("por documento: una barra por comprobante", len(D["keys"]) == 5,
          D["keys"])
    check("el año se rotula como año (eje de categorías, regla #448)",
          _etq("2026", "Año") == "2026" and _etq("2026-09", "Mes", True)
          == "set 2026")

    return fallos


def _pruebas_compras_sin_bucles_por_grupo():
    """Las cuatro funciones de Compras que dejaron de recorrer grupos uno por
    uno (2026-09-26, regla #537) dan lo MISMO que los bucles de antes.

    Los bucles están copiados acá abajo como ORÁCULO: son la definición de
    lo que cada función tiene que devolver. Se comparan sobre datos
    sintéticos con los bordes que el cambio podía romper en silencio:

      · la moda con EMPATE (gana la menor, como el `mode().iat[0]` de antes)
        y con unidades vacías (no cuentan; todas vacías -> "");
      · dos compras el MISMO día a distinto precio: la última es la de más
        abajo en el parquet (orden estable). Es la trampa de «Cachema
        Entera» del docstring de `_vol_cierres_semanales`;
      · semanas sin compra (relleno hacia adelante) y None antes de la
        primera; un precio 0 o vacío, que no abre ni cierra nada;
      · un producto que no pasa el piso de gasto o de cobertura;
      · montos iguales al céntimo en el ranking: van por nombre (en el
        bucle dependían del último decimal de la suma).

    El ranking de Producto (`_prod_ranking`, primera contra última compra)
    se fue el 2026-10-13 con la vista nueva (regla #653): su oráculo se fue
    con él, y sus sucesores (`_resumen`, `_ultimo_precio`, `_cada_cuanto`)
    entran en la guarda de forma de abajo.

    Más un caso grande al azar, con semilla fija, para lo que no se me
    ocurrió. Y una guarda con `ast`: ninguna de las cinco vuelve a iterar un
    `groupby` ni a llamar `mode()` adentro de un `agg`. No se mide tiempo
    —en esta laptop un test de tiempo falla por el antivirus—: se mide la
    FORMA que costaba el tiempo.
    """
    import ast
    import inspect
    import textwrap

    import numpy as np

    import graficos.compras._comun as _cm
    import graficos.compras.producto as _pr
    import graficos.compras.volatilidad as _vo
    import graficos.compras.vs_ano_pasado as _va

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    sin bucles · {nombre}")
        else:
            fallos += 1
            print(f"FALLA sin bucles · {nombre}{': ' + str(detalle)[:300] if detalle else ''}")

    # ── Los oráculos: los bucles de antes, tal cual (con el orden estable
    # explícito, que es lo que hacía numpy con un grupo chico). ──────────
    def o_unidades(fuente, llave, col_um):
        return (fuente[[llave, col_um]].astype(str).groupby(llave)[col_um]
                .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "")
                .to_dict())

    def o_cierres(d, prods, col_prod, col_punit, col_fecha, semanas):
        out = {p: [None] * len(semanas) for p in prods}
        pos = {s: i for i, s in enumerate(semanas)}
        for p, g in d[d[col_prod].isin(list(prods))].groupby(col_prod, sort=False):
            propios = {}
            for sem, gs in g.groupby("_semana", sort=False):
                if sem in pos:
                    oh = _vo._vol_ohlc_semana(
                        gs.sort_values(col_fecha, kind="stable")[col_punit].tolist())
                    if oh:
                        propios[pos[sem]] = oh["c"]
            prev, cierres = None, []
            for i in range(len(semanas)):
                prev = propios.get(i, prev)
                cierres.append(prev)
            out[p] = cierres
        return out

    def o_candidatos(d, col_prod, col_punit, col_fecha, col_valor, semanas,
                     min_gasto, min_cobertura):
        out = {}
        for prod, g in d.groupby(col_prod):
            if (g[col_valor].sum() < min_gasto
                    or g["_semana"].nunique() < min_cobertura * len(semanas)):
                continue
            c = o_cierres(g, [prod], col_prod, col_punit, col_fecha, semanas)[prod]
            out[prod] = {"cierres": c, "volatilidad": _vo._vol_score(c)}
        return out

    def iguales(a, b):
        """Igualdad con tolerancia para floats y None == NaN."""
        if isinstance(a, dict):
            return (list(a) == list(b)) and all(iguales(a[k], b[k]) for k in a)
        if isinstance(a, (list, tuple)):
            return len(a) == len(b) and all(iguales(x, y) for x, y in zip(a, b))
        na = a is None or (isinstance(a, float) and np.isnan(a))
        nb = b is None or (isinstance(b, float) and np.isnan(b))
        if na or nb:
            return na and nb
        if isinstance(a, float) or isinstance(b, float):
            return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a)))
        return a == b

    def semana(f):
        return (f - pd.to_timedelta(f.dt.weekday, unit="D")).dt.normalize()

    # ── Casos armados a mano ────────────────────────────────────────────
    sems = list(pd.to_datetime(["2026-06-01", "2026-06-08", "2026-06-15",
                                "2026-06-22"]))
    d = pd.DataFrame({
        "p":      ["A", "A", "A", "A", "B", "C", "D", "D", "E", "E"],
        # A: dos compras el MISMO día (10 y después 12: cierra 12), una
        # semana en 0 (no cierra) y un precio vacío. E: el mismo monto que
        # B al céntimo (empate del ranking).
        "precio": [10.0, 12.0, 0.0, 15.0, 5.0, 7.0, np.nan, 4.0, 2.5, 2.5],
        "f": pd.to_datetime(["2026-06-01", "2026-06-01", "2026-06-17",
                             "2026-06-24", "2026-06-16", "2026-06-02",
                             "2026-06-03", None, "2026-06-09", "2026-06-23"]),
        "valor":  [100.0, 120.0, 0.0, 150.0, 50.0, 1.0, 30.0, 40.0, 25.0, 25.0],
        "cant":   [10.0, 10.0, 1.0, 10.0, 10.0, 1.0, 3.0, 10.0, 10.0, 10.0],
        # A: KG ×2 y UND ×2 (empate: gana la MENOR, "KG"). C: sin unidad.
        "um":     ["KG", "UND", "KG", "UND", "UND", None, "LT", "LT", "UND", "UND"],
    })
    d["_semana"] = semana(d["f"])

    check("unidades: moda con empate y unidad vacía = bucle de antes",
          iguales(_va._unidades_por(d, "p", "um"), o_unidades(d, "p", "um")),
          (_va._unidades_por(d, "p", "um"), o_unidades(d, "p", "um")))
    check("unidades: en el empate gana la menor",
          _va._unidades_por(d, "p", "um")["A"] == "KG")
    ci = _vo._vol_cierres_semanales(d, ["A", "B", "Z"], "p", "precio", "f", sems)
    check("cierres = bucle de antes (mismo día, 0, huecos, producto ausente)",
          iguales(ci, o_cierres(d, ["A", "B", "Z"], "p", "precio", "f", sems)), ci)
    check("cierres: el mismo día cierra la compra de más abajo",
          ci["A"][0] == 12.0, ci["A"])
    ca = _vo._vol_candidatos(d, "p", "precio", "f", "valor", sems,
                             min_gasto=40.0, min_cobertura=0.5)
    check("candidatos = bucle de antes (pisos de gasto y cobertura)",
          iguales(ca, o_candidatos(d, "p", "precio", "f", "valor", sems, 40.0, 0.5)),
          ca)

    # ── Un caso grande al azar ──────────────────────────────────────────
    rng = np.random.default_rng(537)
    n = 3000
    fechas = pd.Timestamp("2026-01-05") + pd.to_timedelta(
        rng.integers(0, 140, n), unit="D")
    precio = np.round(rng.uniform(0.5, 90.0, n), 2)
    precio[rng.random(n) < 0.05] = 0.0
    precio[rng.random(n) < 0.03] = np.nan
    g = pd.DataFrame({
        "p": rng.choice([f"P{i:03d}" for i in range(120)], n),
        "precio": precio, "f": fechas,
        "valor": np.round(rng.uniform(1, 500, n), 2),
        "cant": np.round(rng.uniform(0.1, 30, n), 3),
        "um": rng.choice(["KG", "UND", "LT", None], n, p=[.45, .35, .15, .05]),
    })
    g["_semana"] = semana(g["f"])
    sg = sorted(g["_semana"].dropna().unique())
    sg = list(pd.to_datetime(sg))
    check("al azar: unidades", iguales(_va._unidades_por(g, "p", "um"),
                                       o_unidades(g, "p", "um")))
    prods = sorted(g["p"].unique())[:80]
    check("al azar: cierres", iguales(
        _vo._vol_cierres_semanales(g, prods, "p", "precio", "f", sg),
        o_cierres(g, prods, "p", "precio", "f", sg)))
    check("al azar: candidatos", iguales(
        _vo._vol_candidatos(g, "p", "precio", "f", "valor", sg[-12:],
                            min_gasto=300.0, min_cobertura=0.4),
        o_candidatos(g, "p", "precio", "f", "valor", sg[-12:], 300.0, 0.4)))

    # ── La guarda de forma ──────────────────────────────────────────────
    for fn in (_cm.moda_por_grupo, _va._unidades_por, _pr._resumen,
               _pr._ultimo_precio, _pr._cada_cuanto,
               _vo._vol_candidatos, _vo._vol_cierres_semanales,
               _vo._tabla_cierres):
        arbol = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        malos = []
        for nodo in ast.walk(arbol):
            if isinstance(nodo, (ast.For, ast.comprehension)):
                if any(isinstance(x, ast.Attribute) and x.attr in ("groupby", "iterrows")
                       for x in ast.walk(nodo.iter)):
                    malos.append(f"línea {getattr(nodo, 'lineno', '?')}: "
                                 "itera un groupby/iterrows")
            if isinstance(nodo, ast.Lambda) and any(
                    isinstance(x, ast.Attribute) and x.attr == "mode"
                    for x in ast.walk(nodo)):
                malos.append("un mode() adentro de una lambda (uno por grupo)")
        check(f"{fn.__name__} no recorre grupos uno por uno", not malos, malos)

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

    # ── 2) La fila del drill de Proveedor usa su constante ──────────────
    # Positiva, no negativa: sin esto, borrar la llamada dejaría la guarda
    # #1 en verde. Desde el 2026-10-12 es UNA fila, Ranking | ficha, con
    # `COLUMNAS_DRILL_FICHA` (regla #646); hasta ese día eran dos, con
    # `COLUMNAS_DRILL_TABLAS` y `COLUMNAS_DRILL_ABAJO` (reglas #578 y #579).
    prov = (raiz / "graficos" / "compras" / "proveedor.py").read_text(
        encoding="utf-8")
    n_filas = len(re.findall(r"st\.columns\(COLUMNAS_DRILL_FICHA\b", prov))
    check("la fila del drill de Proveedor parte con COLUMNAS_DRILL_FICHA",
          n_filas == 1, f"se encontraron {n_filas}")
    # Y la de Producto, la MISMA desde el 2026-10-13 (regla #653): dos
    # secciones vecinas con el orden al revés hacían saltar la vista de lado.
    prod = (raiz / "graficos" / "compras" / "producto.py").read_text(
        encoding="utf-8")
    n_filas = len(re.findall(r"st\.columns\(COLUMNAS_DRILL_FICHA\b", prod))
    check("la fila del drill de Producto parte con COLUMNAS_DRILL_FICHA",
          n_filas == 1, f"se encontraron {n_filas}")

    # ── 3) La constante tiene UN dueño ──────────────────────────────────
    intrusos = []
    for py, texto in _fuentes_py(raiz):
        if py.name in ("_comun.py", pathlib.Path(__file__).name):
            continue
        for i, linea in enumerate(texto.split("\n"), 1):
            if re.match(r"\s*(COLUMNAS_DRILL|GAP_DRILL)\s*=", linea):
                intrusos.append(f"{py.relative_to(raiz).as_posix()}:{i}")
    check("COLUMNAS_DRILL/GAP_DRILL solo los declara compras/_comun.py",
          not intrusos, ", ".join(intrusos[:6]))

    return fallos


def _pruebas_una_sola_nombre_propio():
    """Que `nombre_propio` no vuelva a ser DOS funciones.

    Hasta el 2026-09-11 había dos, con el mismo nombre y el mismo
    propósito: una en `graficos/base.py` y otra en
    `graficos/compras/_etiquetas_proveedor.py`. Sobre los 773 proveedores
    distintos de `compras.parquet` daban resultados distintos en **48**, y
    ninguna ganaba en todas: la de base acertaba las siglas sin vocales
    («LV Ditek», «Operadora LCPM») y la otra los artículos («Agricola La
    Chacra») y los tokens con separador raro («J&S»). El síntoma no era un
    error sino algo peor: el mismo proveedor escrito de dos maneras según
    qué tarjeta lo dibujara — «Corporacion Baserito Lmc» en el ranking de
    Volatilidad y «Corporacion Baserito LMC» en el drill de Proveedor.

    Se copian funciones por una razón buena (no crear un import feo) y el
    coste tarda semanas en verse, así que lo que se vigila es la copia, no
    el resultado:

      1. Una sola `def nombre_propio` en todo el repo, y en su módulo.
      2. Nadie la importa de `graficos.base` — ahí ya no está, pero un
         `from graficos.base import nombre_propio` falla en el import del
         dashboard, o sea EN CLOUD y con la app caída (regla #357), no acá.

    Por qué vive en `graficos/compras/` y no en `base.py`, que sería el
    sitio natural de un helper compartido: `base.py` no puede importar de
    `graficos/compras/` porque el paquete importa de `base.py` al cargarse
    — probado, `ImportError: cannot import name 'compartimento_filtros'
    from partially initialized module`. La dependencia va en un solo
    sentido y el que tiene que ceder es `base.py`. Ver regla #379.
    """
    import ast
    import pathlib

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    nombre_propio · {nombre}")
        else:
            fallos += 1
            print(f"FALLA nombre_propio · {nombre}{': ' + detalle if detalle else ''}")

    raiz = pathlib.Path(__file__).parent
    DUENO = "graficos/compras/_etiquetas_proveedor.py"

    definiciones, importan_de_base = [], []
    for py, src in _fuentes_py(raiz):
        rel = py.relative_to(raiz).as_posix()
        try:
            arbol = ast.parse(src)
        except SyntaxError:
            continue
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and nodo.name == "nombre_propio"):
                definiciones.append(f"{rel}:{nodo.lineno}")
            if (isinstance(nodo, ast.ImportFrom)
                    and nodo.module == "graficos.base"
                    and any(a.name == "nombre_propio" for a in nodo.names)):
                importan_de_base.append(f"{rel}:{nodo.lineno}")

    check("hay exactamente UNA definición en el repo",
          len(definiciones) == 1,
          f"encontradas {len(definiciones)}: {', '.join(definiciones)}"
          " — si hacen falta dos comportamientos, son dos NOMBRES")
    check(f"y vive en {DUENO}",
          definiciones == [d for d in definiciones if d.startswith(DUENO)],
          f"está en {', '.join(definiciones)}")
    check("nadie la importa de graficos.base",
          not importan_de_base,
          f"la importan de base: {', '.join(importan_de_base)}")

    return fallos


def _pruebas_evolucion_ajuste():
    """Las cuentas de Ajuste › Evolución (graficos/ajuste/_evolucion.py).

    Lo que fijan son las decisiones de la fusión de las tres vistas de
    Tiempo (regla #501), no aritmética suelta:

      · sobrante y faltante van SEPARADOS: el neto se cancela y ahí se
        escondía el peor mes del año;
      · «Mes» rellena los meses sin conteo, y el rótulo del eje lleva el año
        cuando el rango cruza de año (si no, dos «set» son una categoría);
      · las columnas se afirman POR NOMBRE: una clave suelta en un groupby
        da otra forma en pandas 2 (Cloud) que en 3 (acá), regla #481.
    """
    from graficos.ajuste import _evolucion as _ev
    from graficos.ajuste import _pivote as _pv

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ajuste evolución · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ajuste evolución · {nombre}: got={got!r} exp={exp!r}")

    d = pd.DataFrame({
        "F": pd.to_datetime(["2025-11-03", "2025-11-03", "2025-11-04",
                             "2026-01-10", "2026-01-10", "2026-01-11"]),
        "FAM": ["A", "B", "A", "A", "B", None],
        "PROD": ["p1", "q1", "p2", "p1", "q1", "z"],
        "AV": [100.0, -40.0, -160.0, 5.0, -5.0, 1.0],
        "VT": [1000.0, 0.0, 1000.0, 500.0, 0.0, 10.0],
        "AJ": [1.0, -1.0, -2.0, 1.0, -1.0, 1.0],
    })

    dp, orden = _ev.periodos_ajuste(d, "F", "Mes")
    check("Mes: rellena diciembre, que no tuvo conteo",
          orden["_clave"].tolist(), ["2025-11", "2025-12", "2026-01"])
    check("columnas de orden, por nombre",
          list(orden.columns), ["_clave", "etq", "eje", "anio"])
    check("el eje lleva el año cuando el rango cruza de año",
          orden["eje"].tolist(), ["nov 25", "dic 25", "ene 26"])

    s = _ev.serie_ajuste(dp, orden, "AV", "VT").set_index("_clave")
    check("columnas de la serie, por nombre",
          list(s.reset_index().columns),
          ["_clave", "etq", "eje", "anio", "sobrante", "faltante", "neto",
           "contado"])
    check("sobrante y faltante no se cancelan",
          (s.loc["2025-11", "sobrante"], s.loc["2025-11", "faltante"],
           s.loc["2025-11", "neto"]), (100.0, -200.0, -100.0))
    check("el valor contado es la suma de lo contado del período",
          s.loc["2025-11", "contado"], 2000.0)
    check("el mes sin conteo queda vacío, no en cero",
          bool(pd.isna(s.loc["2025-12", "neto"])), True)

    sf = _ev.serie_ajuste(dp, orden, "AV", "VT", col_grupo="FAM")
    check("por familia: sin panel para la familia vacía",
          sorted(sf["grupo"].unique()), ["A", "B"])
    b_ene = sf[(sf["grupo"] == "B") & (sf["_clave"] == "2026-01")].iloc[0]
    check("por familia: cada grupo con su sobrante y su faltante",
          (b_ene["sobrante"], b_ene["faltante"]), (0.0, -5.0))

    _, orden_c = _ev.periodos_ajuste(d, "F", "Corte")
    check("Corte: una sesión por racha de días",
          len(orden_c), 2)

    # MES OPERATIVO (regla #613): el cierre registrado del 1 al 7 es del mes
    # anterior, con su hora; el del 8 en adelante, del suyo. Era «del 1 al
    # 6» hasta que el usuario definió el cierre de mes (regla #632).
    from cortes import fecha_operativa
    f_op = fecha_operativa(pd.Series(pd.to_datetime(
        ["2026-10-03 14:20", "2026-10-07 09:00", "2026-10-08 08:00",
         "2026-03-01 10:00", "2025-01-05 00:00", None])))
    check("mes operativo: del 1 al 7, al último día del mes anterior",
          [str(x) for x in f_op],
          ["2026-09-30 14:20:00", "2026-09-30 09:00:00",
           "2026-10-08 08:00:00", "2026-02-28 10:00:00",
           "2024-12-31 00:00:00", "NaT"])
    d_op = pd.DataFrame({
        "F": pd.to_datetime(["2026-08-29", "2026-10-02", "2026-10-02",
                             "2026-10-20"]),
        "AV": [1.0, -10.0, -5.0, 2.0], "VT": [1.0, 1.0, 1.0, 1.0]})
    dp_op, orden_op = _ev.periodos_ajuste(d_op, "F", "Mes", operativo=True)
    check("mes operativo: el cierre del 2 oct cae en septiembre",
          orden_op["_clave"].tolist(), ["2026-08", "2026-09", "2026-10"])
    s_op = _ev.serie_ajuste(dp_op, orden_op, "AV", "VT").set_index("_clave")
    check("mes operativo: la serie lo suma en septiembre",
          s_op.loc["2026-09", "neto"], -15.0)
    _, orden_reg = _ev.periodos_ajuste(d_op, "F", "Mes")
    check("por fecha de registro, septiembre queda sin conteo",
          orden_reg["_clave"].tolist(), ["2026-08", "2026-09", "2026-10"])
    _, orden_cop = _ev.periodos_ajuste(d_op, "F", "Corte", operativo=True)
    check("mes operativo: los cortes siguen con sus días de verdad",
          len(orden_cop), 3)

    # Sin «Semana» (regla #585): el ajuste se mide por conteo, no por semana.
    check("los granos son Corte y Mes", _ev.GRANOS, ("Corte", "Mes"))

    # La tabla que alterna con los mini-gráficos resume la MISMA serie.
    html = _ev.tabla_resumen_html(s.reset_index(), foco="2026-01", alto=184)
    check("tabla: una fila por período más el total",
          html.count("<tr"), 1 + len(s) + 1)
    check("tabla: del más nuevo al más viejo",
          html.index("ene 26") < html.index("nov 25"), True)
    check("tabla: el mes sin conteo dice «sin conteo», no «None» ni 0",
          ("sin conteo" in html, "None" in html, "nan" in html),
          (True, False, False))
    check("tabla: el total es el neto del rango",
          "S/ -99<" in html.split("Total del rango")[1], True)
    check("tabla: el período en foco sale marcado",
          html.count(_ev.LAVANDA_SELECCION), 1)

    # El estilo de la serie (regla #631): el neto se rotula en pastillas
    # (anotaciones) y no con el `text` de la traza, que iba negro encima
    # de la barra roja; el período más movido lleva su marca; los totales
    # del rango van en una línea bajo el título.
    sr = s.reset_index()
    fig = _ev.fig_serie(sr)
    _neto = [t for t in fig.data if t.name == "Neto"][0]
    check("serie: la traza del neto ya no lleva texto",
          (_neto.mode, _neto.text), ("lines+markers", None))
    _pills = [a for a in fig.layout.annotations if a.yref != "paper"]
    check("serie: una pastilla por período con conteo, con signo",
          [a.text for a in _pills], ["S/ -100", "S/ +1"])
    check("serie: la pastilla dice el signo con su color",
          [a.font.color for a in _pills],
          [_ev.AJUSTE_NEG_TEXTO, _ev.AJUSTE_POS_TEXTO])
    check("serie: con foco, la pastilla de los otros períodos se apaga",
          [a.opacity for a in _ev.fig_serie(sr, "2026-01").layout.annotations
           if a.yref != "paper"], [_ev._APAGADO, 1.0])
    check("serie: el más movido es el de más sobrante − faltante",
          (_ev.periodo_mas_movido(sr) or {}).get("eje"), "nov 25")
    check("serie: el más movido se rotula arriba, en el margen",
          [a.text for a in fig.layout.annotations if a.yref == "paper"],
          ["más movido · <b>S/ 300</b>"])
    check("serie: con menos de tres períodos no hay más movido",
          _ev.periodo_mas_movido(sr.iloc[:2]), None)
    _largo = pd.concat([sr] * 6, ignore_index=True)
    _largo["eje"] = [f"p{i}" for i in range(len(_largo))]
    check("serie: con más de _MAX_ROTULOS períodos no hay pastillas",
          len([a for a in _ev.fig_serie(_largo).layout.annotations
               if a.yref != "paper"]), 0)
    check("serie: las barras llevan la punta redondeada",
          fig.layout.barcornerradius, _ev._RADIO_SERIE)
    kp = _ev.kpis_rango_html(sr)
    check("totales del rango: sobrante, faltante y neto, con signo",
          [t in kp for t in ("S/ +106", "S/ -205", "S/ -99")],
          [True, True, True])

    # La tabla parte el tiempo con los MISMOS períodos que la serie.
    wide, periodos = _pv._armar_tabla_pivote_ajuste(
        dp.dropna(subset=["FAM"]), orden, "FAM", None, "PROD", "AJ", "AV")
    check("la tabla lleva una columna por período de la serie",
          [p["clave"] for p in periodos], orden["_clave"].tolist())
    check("cada columna sabe su año (grupo de cabecera)",
          [p["anio"] for p in periodos], [2025, 2025, 2026])
    # La tabla es un árbol por Familia: la fila sin familia no tiene dónde
    # colgar y se cae (en el parquet real son 122 filas, todas con ajuste
    # cero). La serie sí la cuenta: -99 contra -100.
    check("total de la tabla = neto de la serie de las filas con familia",
          round(float(wide["tot_ajv"].sum()), 2), -100.0)
    return fallos


def _pruebas_fechas_ajuste():
    """Las fechas de Ajuste de Inventario, una por vista (regla #632).

    1. LA SESIÓN: un cierre de mes es lo registrado del 1 al 7 del mes
       siguiente —y se juntan los conteos de esos días—; lo demás es
       parcial. El año de una sesión es el del mes que cierra.
    2. LOS MESES: el panel de Compras en modo «sólo meses», con sus atajos
       en meses enteros y el botón que dice meses, no días.
    3. LA FRANJA: Ajuste no dibuja fecha arriba ni la usa para filtrar, y
       su pila es una sola.
    """
    import datetime
    import re
    from pathlib import Path

    from cortes import DIA_CIERRE_OPERATIVO, sesiones_inventario, ultimo_cierre
    from estado_rango import atajos_meses
    from graficos.panel_fecha import etiqueta_de

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    fechas ajuste · {nombre}")
        else:
            fallos += 1
            print(f"FALLA fechas ajuste · {nombre}: got={got!r} exp={exp!r}")

    D = datetime.date
    check("el cierre es del 1 al 7", DIA_CIERRE_OPERATIVO, 7)

    # Los casos reales: el cierre de setiembre 2026 contado el 1 de octubre
    # con el recuento de Venta interna del 6; el de abril 2024, que empezó
    # el 29; un parcial de quincena; y el de diciembre contado en enero.
    f = pd.Series(pd.to_datetime([
        "2024-04-29", "2024-04-30", "2024-05-01", "2024-05-06",
        "2025-12-15", "2026-01-02",
        "2026-09-02", "2026-09-15", "2026-09-16", "2026-09-17",
        "2026-10-01 08:30", "2026-10-06 11:49", None], format="mixed"))
    ses = sesiones_inventario(f)
    check("una sesión por cierre o parcial, en orden",
          [(x["tipo"], x["nombre"]) for x in ses],
          [("cierre", "Cierre de abril"), ("parcial", "Parcial · 15 dic"),
           ("cierre", "Cierre de diciembre"), ("cierre", "Cierre de agosto"),
           ("parcial", "Parcial · 15-17 set"), ("cierre", "Cierre de setiembre")])
    sep = ses[-1]
    check("los conteos del 1 al 7 se juntan en un cierre",
          (sep["juntas"], sep["etiqueta"], sep["n_dias"]), (2, "1 y 6 oct", 2))
    check("el cierre que empezó a fin de mes trae la racha entera",
          (ses[0]["juntas"], ses[0]["ini"], ses[0]["fin"]),
          (2, D(2024, 4, 29), D(2024, 5, 6)))
    check("el botón dice el mes que cierra", sep["corto"], "Cierre set 2026")
    check("el de diciembre es del año que cierra, no del de su registro",
          (ses[2]["mes"], ses[2]["corto"]), ((2025, 12), "Cierre dic 2025"))
    check("las claves no dependen de cuántas sesiones hay antes",
          [x["clave"] for x in ses[3:]],
          ["cierre_2026-08", "parcial_2026-09-15", "cierre_2026-09"])
    check("abre en el último cierre",
          ultimo_cierre(ses)["clave"], "cierre_2026-09")
    check("sin cierres, la última sesión",
          ultimo_cierre(sesiones_inventario(pd.Series(pd.to_datetime(
              ["2026-09-15", "2026-09-25"]))))["etiqueta"], "25 set")
    check("sin fechas, sin sesiones", sesiones_inventario(pd.Series([], dtype="datetime64[ns]")), [])

    # LOS MESES: anclados al último día con datos, en meses enteros.
    at = {c: r for c, _n, _g, r in atajos_meses(D(2026, 9, 30),
                                               (D(2023, 10, 1), D(2026, 9, 30)))}
    check("los atajos de meses",
          sorted(at), sorted(["anio", "mes_ult", "mm3", "mm12", "anio_ant", "todo"]))
    check("últimos 12 meses: doce meses enteros",
          at["mm12"], (D(2025, 10, 1), D(2026, 9, 30)))
    check("último mes: el del ancla, entero",
          at["mes_ult"], (D(2026, 9, 1), D(2026, 9, 30)))
    ctx = {"k_rango": "x", "fecha_min": D(2023, 10, 1),
           "fecha_max": D(2026, 9, 30), "hoy": D(2026, 10, 11),
           "atajos_fn": atajos_meses, "solo_meses": True}
    check("el botón dice meses",
          etiqueta_de((D(2025, 10, 1), D(2026, 9, 30)), ctx),
          "Últimos 12 meses · oct 2025 – set 2026")
    check("un rango que no es atajo, también en meses",
          etiqueta_de((D(2026, 3, 1), D(2026, 7, 31)), ctx), "mar – jul 2026")
    check("el último mes, por su nombre",
          etiqueta_de((D(2026, 9, 1), D(2026, 9, 30)), ctx),
          "Último mes · setiembre")
    js = (Path(__file__).parent / "graficos" / "panel_fecha.js").read_text(
        encoding="utf-8")
    check("el panel esconde «Días» en modo sólo meses",
          "if (!st.soloMeses)" in js and "solo_meses" in js, True)

    # LA FRANJA Y LA PILA.
    raiz = Path(__file__).parent
    app = (raiz / "app.py").read_text(encoding="utf-8")
    _por_vista = re.search(r'REPORTES_FECHA_POR_VISTA = \(([^)]*)\)', app)
    check("la franja de Ajuste no dibuja fecha",
          bool(_por_vista and '"Ajuste de Inventario"' in _por_vista.group(1)), True)
    # Era un `elif` detrás de la rama del modo Corte; desde la regla #635,
    # que borró esa rama, es el `if` que abre el filtro por la franja.
    check("app.py no filtra Ajuste por la franja",
          "if _franja_con_fecha and not es_ajuste:" in app,
          True)
    check("app.py ya no reparte el rango por categoría",
          "categoria_rango_ajuste" in app.split("# Hasta el 2026-10-11 Ajuste")[0],
          False)
    import data
    # Desde la regla #635 nadie lee `"cortes"`: los modos Corte / Varios de
    # la franja se borraron. Un reporte que la declare esperaría una
    # píldora con cortes y no pasaría nada, sin error que lo diga.
    check("ningún reporte declara \"cortes\" (los modos de la franja ya no existen)",
          [r for r, c in data.REPORTES.items() if "cortes" in c], [])
    from graficos import ajuste as aj
    # «Diferencias» se sumó el 2026-10-13 (regla #650), entre las vistas de
    # un conteo y las del tiempo.
    check("una sola pila con las seis vistas",
          [c for c, _v in aj._PILA],
          ["aj_sec_cascada", "aj_sec_heatmap", "aj_sec_distribucion",
           "aj_sec_diferencias", "aj_sec_evolucion", "aj_sec_detalle"])
    check("se fue la partición del rango por categoría",
          hasattr(aj, "categoria_rango_ajuste"), False)
    fuentes = {n: (raiz / "graficos" / "ajuste" / f"{n}.py").read_text(
        encoding="utf-8") for n in ("_cascada", "_heatmap", "_distribucion",
                                    "_evolucion", "_pivote", "_diferencias")}
    check("las vistas de sesión dibujan el selector con flechas",
          [n for n in ("_cascada", "_heatmap", "_diferencias")
           if '"ajses_' not in fuentes[n]]
          + ([] if re.search(r'selector_sesion\(\s*"ajses_dist"',
                             fuentes["_distribucion"])
             else ["_distribucion"]), [])
    check("las vistas de meses dibujan su botón",
          [n for n, k in (("_evolucion", '"ajf_evo"'), ("_pivote", '"ajf_det"'),
                          ("_distribucion", '"ajf_dist"'))
           if f"selector_meses({k}" not in fuentes[n]], [])
    ini = (raiz / "graficos" / "ajuste" / "__init__.py").read_text(encoding="utf-8")
    check("«Mes del cierre» se fue de Filtros",
          "_selector_mes_ajuste" in ini, False)
    check("las vistas de meses recargan si cambió el mes del cierre",
          ini.count("recargar_si_cambio_mes()"), 3)
    css = (raiz / "estilos" / "_80_cards.py").read_text(encoding="utf-8")
    check("los dos controles tienen su CSS",
          ('st-key-ajf_' in css, 'st-key-ajses_' in css), (True, True))

    # EL PANEL DE LA SESIÓN (regla #634): una pieza propia, como el de
    # fechas, con el neto y el detalle de cada sesión.
    from graficos.ajuste._comun import (
        datos_panel_sesion, stats_sesiones, texto_familias)
    css_p = (raiz / "graficos" / "ajuste" / "panel_sesion.css").read_text(
        encoding="utf-8")
    js_p = (raiz / "graficos" / "ajuste" / "panel_sesion.js").read_text(
        encoding="utf-8")
    check("el panel de la sesión: sin :has() y con su función",
          (":has(" in css_p, "export default function" in js_p), (False, True))
    df_s = pd.DataFrame({
        "F": pd.to_datetime(["2026-09-15", "2026-09-15", "2026-09-16",
                             "2026-10-01", "2026-10-01", "2026-10-06",
                             "2026-10-06"]),
        "AREA": ["COCINA", "BARRA", "COCINA ", "COCINA", "CAVA", "VENTA", "VENTA"],
        "AV": [-10.0, 5.0, 0.0, -100.0, 40.0, 7.0, 0.0],
        "P": ["p1", "p2", "p1", "p1", "p3", "p4", "p5"],
    })
    ses_s = sesiones_inventario(df_s["F"])
    st_s = stats_sesiones(df_s, "F", "AREA", "AV", "P", ses_s)
    check("cuentas de cada sesión: neto, áreas (sin el espacio), productos",
          (st_s["parcial_2026-09-15"], st_s["cierre_2026-09"]),
          ((-5.0, 2, 2), (-53.0, 3, 3)))
    dp = datos_panel_sesion(ses_s, ses_s[-1], {"cierre_2026-09"}, False,
                            True, False, st_s, texto_familias(()))
    fila = dp["sesiones"][-1]
    check("el panel recibe el nombre, el neto y el detalle",
          (fila["nombre"], fila["neto"], fila["meta"], fila["anio"]),
          ("Cierre de setiembre", -53.0,
           "registrado el 1 y 6 oct (se juntan 2 conteos) · 3 áreas · "
           "3 productos con diferencia", 2026))
    check("el pie dice de qué familias es el neto",
          dp["pie"][0].startswith("Neto de todas las familias."), True)
    check("las cinco familias de entrada se nombran así",
          texto_familias(("ALIMENTOS", "BEBIDAS CON ALCOHOL",
                          "BEBIDAS SIN ALCOHOL", "VINOS Y ESPUMANTES",
                          "ENVASES Y EMBALAJES")),
          "las cinco familias de entrada")
    return fallos


def _pruebas_cantidad_del_mapa_ajuste():
    """La cantidad del detalle del Mapa de calor es la que su monto
    multiplica (graficos/ajuste/_heatmap.py, regla #506).

    Nació de una captura de Valorizado Total: «Bife Ancho Argentino · 0.0
    KILOS · S/ 2,520». El monto era lo CONTADO × precio y la cantidad, el
    AJUSTE. Las tres filas son las reales de ALIMENTOS × PRODUCCION del
    16-sep-2026. Se afirma la CUENTA —monto = cantidad × precio, fila por
    fila y en los dos modos—, no sólo el nombre de la columna.
    """
    from unittest import mock as _mock
    from graficos.ajuste import _heatmap as _hm

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ajuste mapa · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ajuste mapa · {nombre}: got={got!r} exp={exp!r}")

    d = pd.DataFrame({
        "FAMILIA": ["ALIMENTOS"] * 3,
        "AREA": ["PRODUCCION"] * 3,
        "PRODUCTO": ["Bife Ancho Argentino x Kg",
                     "(Rs) Marca chorizo de pato x Kg",
                     "(Rs) Marca Chorizo Criollo x Kg"],
        "UNIDAD MEDIDA": ["KILOS"] * 3,
        "STOCK AL CIERRE": [13.524, 8.442, 24.46],
        "STOCK DECLARADO": [13.524, 10.8, 22.1],
        "AJUSTE": [0.0, 2.358, -2.36],
        "PRECIO PROMEDIO": [186.356583259185, 210.7352220870235,
                            11.62684747163018],
        "AJUSTE VALORIZADO": [0.0, 496.9136536812014, -27.439360033047222],
        "VALORIZADO TOTAL": [2520.2864319972177, 2275.940398539854,
                             256.953329123027],
    })

    for modo_val, metrica, esperada in (
            (False, "AJUSTE VALORIZADO", "AJUSTE"),
            (True, "VALORIZADO TOTAL", "STOCK DECLARADO")):
        col = _hm._col_cantidad_del_modo(d, "AJUSTE", modo_val)
        check(f"{metrica}: la cantidad es {esperada}", col, esperada)
        check(f"{metrica} = cantidad × precio, fila por fila",
              bool(((d[metrica] - d[col] * d["PRECIO PROMEDIO"]).abs()
                    < 0.01).all()), True)
    check("sin columna de lo contado, sin cantidad (no la del ajuste)",
          _hm._col_cantidad_del_modo(d.drop(columns="STOCK DECLARADO"),
                                     "AJUSTE", True), None)

    # Lo que le llega a la grilla del detalle, en Valorizado Total.
    pivot = d.pivot_table(index="FAMILIA", columns="AREA",
                          values="VALORIZADO TOTAL", aggfunc="sum")
    with _mock.patch.object(_hm, "renderizar_desglose_ajuste") as _rd:
        _hm._detalle_celda(
            d, pivot, ("ALIMENTOS", "PRODUCCION"), "FAMILIA", "AREA",
            "PRODUCTO", "VALORIZADO TOTAL",
            _hm._col_cantidad_del_modo(d, "AJUSTE", True),
            "UNIDAD MEDIDA", True)
    tp, columnas = _rd.call_args[0][0], _rd.call_args[0][1]
    _bife = tp.set_index("producto").loc["Bife Ancho Argentino x Kg"]
    check("el bife: 13.524 kg contados al lado de sus S/ 2,520",
          (round(float(_bife["cantidad"]), 3), round(float(_bife["valor"]))),
          (13.524, 2520))
    check("la cabecera dice qué cantidad es",
          [c[1] for c in columnas], ["Producto", "Stock contado", "Valor"])
    return fallos


def _pruebas_resumen_ajuste():
    """Las cuentas de Ajuste › Cascada (graficos/ajuste/_cascada.py).

    Lo que fijan no es aritmética suelta, es QUÉ MIDE cada columna — las
    tres trampas que costaron esta vista (regla #441):

      · el SALDO no es el descuadre: faltó y sobró se cancelan, y la tabla
        tiene que mostrar los dos y su suma sin signo;
      · la EXACTITUD no cuenta las líneas en cero y cero, que el maestro
        lista por cada producto en cada área (en ALIMENTOS eran 4.699 de
        5.674: con ellas daba 83 % donde había 3 %);
      · el grano es la LÍNEA: un producto que faltó en un área y sobró en
        otra pesa las dos cosas, no se cancela.
    """
    from graficos.ajuste import _cascada as _cas

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ajuste resumen · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ajuste resumen · {nombre}: got={got!r} exp={exp!r}")

    d = pd.DataFrame({
        "FAMILIA":  ["A", "A", "A", "A", "A", "B", "B"],
        "AREA":     ["X", "Y", "X", "Z", "Z", "X", "X"],
        "PRODUCTO": ["p1", "p1", "p2", "p3", "p4", "q1", "q2"],
        "AV":       [-100.0, 60.0, 30.0, 0.0, 0.0, -5.0, 0.0],
        "SIS":      [10.0, 0.0, 5.0, 0.0, 4.0, 1.0, 2.0],
        "FIS":      [0.0, 6.0, 8.0, 0.0, 4.0, 0.0, 2.0],
    })
    fams = _cas.resumen_familias(d, "FAMILIA", "AV", "PRODUCTO", "SIS", "FIS")
    a = next(f for f in fams if f["familia"] == "A")

    check("faltó es la suma de los negativos", a["falto"], -100.0)
    check("sobró es la suma de los positivos", a["sobro"], 90.0)
    check("faltó + sobró va sin signo (no se cancelan)", a["total"], 190.0)
    check("el saldo sí se cancela", a["saldo"], -10.0)
    check("de la que más descuadró a la que menos",
          [f["familia"] for f in fams], ["A", "B"])

    # p3 está en cero y cero: no es una línea contada. p4 tiene stock y no
    # tiene diferencia: ésa es la única exacta de A.
    check("la línea en cero y cero no cuenta", a["lineas"], 4)
    check("líneas con diferencia", a["dif"], 3)
    check("exactitud sobre las líneas con stock", a["exact"], 25.0)
    check("sin las columnas de stock, cuenta todas las filas",
          _cas.metricas(d[d["FAMILIA"] == "A"], "AV", None, None, None)["lineas"],
          5)

    # p1 pesa 160 (100 + 60, sus dos líneas) y p2 30: con 190 de total, p1
    # solo es el 84 % -> alcanza con un producto para el 80 %.
    check("productos 80 %: el grano es la línea",
          (a["n80"], a["de"]), (1, 2))
    check("sin diferencias no hay productos",
          _cas.productos_pareto(pd.Series([0.0, 0.0]),
                                pd.Series(["x", "y"])), (0, 0))

    check("una familia con líneas y sin diferencias se queda (100 % es dato)",
          _cas.resumen_familias(
              d[d["PRODUCTO"] == "q2"], "FAMILIA", "AV", "PRODUCTO",
              "SIS", "FIS")[0]["exact"], 100.0)

    _areas = _cas.desglose_areas(d[d["FAMILIA"] == "A"], "AREA", "AV",
                                 "SIS", "FIS")
    check("por área, sin las áreas que no movieron nada",
          [x["area"] for x in _areas], ["X", "Y"])

    check("p1 faltó en X y sobró en Y: un producto espejo",
          _cas.productos_espejo(d[d["FAMILIA"] == "A"], "PRODUCTO", "AREA",
                                "AV"), (1, -100.0, 60.0))

    # Por corte: las áreas contadas son las que tienen alguna línea con
    # stock. Un corte parcial se ve parcial.
    dh = d[d["FAMILIA"] == "A"].assign(
        _corte_clave=["c1", "c1", "c2", "c2", "c2"])
    _cs = [{"clave": "c1", "etiqueta_anio": "1 ago 2026"},
           {"clave": "c2", "etiqueta_anio": "2 set 2026"}]
    _cortes = _cas.desglose_cortes(dh, _cs, "AREA", "AV", "SIS", "FIS")
    check("un renglón por corte, en orden",
          [c["corte"] for c in _cortes], ["1 ago 2026", "2 set 2026"])
    # c1: X e Y. c2: X y Z — Z entra por p4, que tiene stock; p3, en cero y
    # cero, sola no la habría hecho contar.
    check("áreas con stock por corte", [c["areas"] for c in _cortes], [2, 2])

    # LA SEMILLA DE FAMILIAS NO DEPENDE DEL CORTE CON QUE ABRE (regla #442).
    # La vista abre en el último CIERRE (regla #632); si ese no trae una
    # familia, la semilla nacía sin ella y el TOTAL de otro corte sumaba sin
    # avisar. El parcial del 15 de agosto trae ENVASES; el cierre de agosto
    # (2 set) y el parcial posterior (15 set), no.
    from graficos.ajuste._comun import FAMILIAS_DE_ENTRADA, estado_filtros_vista
    _full = pd.DataFrame({
        "F": pd.to_datetime(["2026-08-15"] * 3 + ["2026-09-02"] * 2
                            + ["2026-09-15"]),
        "FAMILIA": ["ALIMENTOS", "ENVASES Y EMBALAJES", "VINOS Y ESPUMANTES",
                    "ALIMENTOS", "VINOS Y ESPUMANTES", "ALIMENTOS"],
        "AREA": ["X"] * 6, "AV": [-1.0, -2.0, 3.0, 4.0, -5.0, 1.0],
    })
    _est = estado_filtros_vista(
        _full, _full, "F", "FAMILIA", "AREA", "AV",
        k_corte="test_ajcas_corte", k_familia="test_ajcas_fam",
        k_area="test_ajcas_area", familias=FAMILIAS_DE_ENTRADA)
    check("abre en el último CIERRE, no en el parcial que vino después",
          (_est["corte"]["nombre"], _est["corte"]["etiqueta_anio"]),
          ("Cierre de agosto", "2 set 2026"))
    check("...y la semilla igual incluye ENVASES",
          "ENVASES Y EMBALAJES" in _est["sel_fam"], True)
    check("las opciones de familia son las del parquet entero",
          _est["familias"],
          ["ALIMENTOS", "ENVASES Y EMBALAJES", "VINOS Y ESPUMANTES"])

    # La tolerancia de la exactitud se declara en la cabecera: si el número
    # cambia, el texto tiene que cambiar con él.
    check("la tolerancia declarada es la que se usa",
          _cas._TOL_EXACTITUD == 0.0 and "cero" in _cas._TOL_TEXTO, True)

    # Cada columna de la tabla dice de dónde sale (regla #441).
    from tablas.ajuste_familias import FUENTES
    check("el 80 % cita el análisis ABC", "ABC" in FUENTES["n80"], True)
    check("la exactitud cita APICS y declara su tolerancia",
          "APICS" in FUENTES["exact"] and "{tol}" in FUENTES["exact"], True)

    # «Valorizado total»: se suma por línea; None sin la columna (regla #483).
    _dv = pd.DataFrame({"AV": [-1.0, 2.0], "VT": [100.0, 50.0]})
    check("valorizado total suma por línea",
          _cas.metricas(_dv, "AV", None, None, None, "VT")["valorizado"], 150.0)
    check("sin columna de valorizado, el campo es None",
          _cas.metricas(_dv, "AV", None, None, None)["valorizado"], None)
    check("«Valorizado total» declara que es la escala del stock",
          "escala" in FUENTES["valorizado"], True)

    # «Por corte» = TODOS los cortes del AÑO del elegido (regla #483), no un
    # historial de N. Con cortes en dos años y el último elegido, sólo entran
    # los de ese año y `d_anio` trae sus filas.
    _multi = pd.DataFrame({
        "F": pd.to_datetime(["2025-03-10", "2026-02-05", "2026-09-15"]),
        "FAMILIA": ["ALIMENTOS"] * 3, "AREA": ["X"] * 3, "AV": [-1.0, -2.0, -3.0],
    })
    _e2 = estado_filtros_vista(
        _multi, _multi, "F", "FAMILIA", "AREA", "AV",
        k_corte="test_ac_corte", k_familia="test_ac_fam",
        k_area="test_ac_area", familias=("ALIMENTOS",), anio_cortes=True)
    check("por corte: sólo los cortes del año del elegido (2026)",
          [c["fin"].year for c in _e2["cortes_anio"]], [2026, 2026])
    check("por corte: d_anio trae una fila por cada corte del año",
          _e2["d_anio"]["_corte_clave"].nunique(), 2)
    check("por corte: la fila de 2025 queda fuera de d_anio",
          len(_e2["d_anio"]), 2)

    # ── Pareto del faltante (modo «Valor (Pareto)» de Distribución, #489) ──
    # Agrega por producto el ajuste NETO, se queda con los faltantes, ordena
    # por magnitud y agrupa la cola en «Otros». El grano de entrada es la
    # LÍNEA (dos filas de p1 se suman a un solo producto).
    from graficos.ajuste import _pareto_datos
    _dp = pd.DataFrame({
        "P":  ["p1", "p1", "p2", "p3", "p4", "p5"],
        "AV": [-300.0, -100.0, -50.0, -10.0, 40.0, -5.0],
    })
    _et, _val, _acu, _pct, _pacu = _pareto_datos(_dp, "AV", "P", top_n=3)
    check("pareto: sólo faltantes, por magnitud, cola en Otros",
          _et, ["p1", "p2", "p3", "Otros (1)"])
    check("pareto: la barra es la MAGNITUD del faltante (soles positivos)",
          _val, [400.0, 50.0, 10.0, 5.0])
    check("pareto: un producto con sobrante neto no entra", "p4" in _et, False)
    check("pareto: el acumulado corre hasta el total del faltante",
          _acu[-1], 465.0)
    check("pareto: el acumulado llega al 100 %", round(_pacu[-1]), 100)
    check("pareto: sin faltantes no hay nada que graficar",
          _pareto_datos(pd.DataFrame({"P": ["a", "b"], "AV": [10.0, 20.0]}),
                        "AV", "P"), ([], [], [], [], []))

    return fallos


def _pruebas_listado_inventario():
    """El listado de Inventario › Productos (graficos/inventario_productos.py).

    Lo que fija es el GRANO y el despliegue (regla #466): el parquet trae
    una fila por producto × área, la tabla una por producto, y lo que se
    despliega son las áreas donde hay stock — no las ~4 donde el kardex lo
    registra en cero. Y el orden del `rowData`: cada producto seguido de sus
    áreas, que es de lo que cuelga el `postSortRows` del navegador.
    """
    from graficos.inventario_productos import armar_listado, filas_grilla

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    inventario listado · {nombre}")
        else:
            fallos += 1
            print(f"FALLA inventario listado · {nombre}: got={got!r} exp={exp!r}")

    d = pd.DataFrame({
        "COD":  ["01", "01", "01", "02", "03", "04", "04"],
        "PROD": ["Pollo x Kg", "Pollo x Kg", "Pollo x Kg", "Pisco Quebranta",
                 "Arroz Añejo", "Azúcar", "Azúcar"],
        "FAM":  ["ALIMENTOS", "ALIMENTOS", "ALIMENTOS",
                 "BEBIDAS CON ALCOHOL", "ALIMENTOS", "ALIMENTOS", "ALIMENTOS"],
        "SUB":  ["AVES", "AVES", "AVES", "PISCO", "ABARROTES", "ABARROTES",
                 "ABARROTES"],
        "AREA": ["COCINA", "BARRA", "CAVA", "BARRA", "COCINA", "COCINA",
                 "BARRA"],
        "UM":   ["KILOS"] * 3 + ["LITROS", "KILOS", "KILOS", "KILOS"],
        "PU":   [10.0, 10.0, 10.0, 30.0, 4.0, 2.0, 2.0],
        # CAVA en cero: registrado pero sin stock, no es "donde existe". El
        # Azúcar sale negativo en BARRA: un descuadre SÍ es existencia.
        "STK":  [2.0, 1.0, 0.0, 3.0, 0.0, 5.0, -1.0],
        "VAL":  [20.0, 10.0, 0.0, 90.0, 0.0, 10.0, -2.0],
    })
    cols = dict(col_cod="COD", col_prod="PROD", col_fam="FAM",
                col_subfam="SUB", col_area="AREA", col_unidad="UM",
                col_punit="PU", col_cant="STK", col_val="VAL")

    L = armar_listado(d, **cols)
    # De la A a la Z por familia › subfamilia › nombre (regla #636): el
    # Azúcar (Alimentos › Abarrotes) antes que el Pollo (Alimentos › Aves),
    # y el Pisco (Bebidas) al final aunque por nombre iría segundo.
    check("un producto por código, de la A a la Z por familia, "
          "subfamilia y nombre",
          L.productos.index.tolist(), ["04", "01", "02"])
    from graficos.inventario_productos import clave_orden
    check("la A a la Z no mira el prefijo del almacén ni las tildes",
          sorted(["Cebolla", "(P) Bife Ancho", "Ávila", "(Rs) Ají Panca"],
                 key=clave_orden),
          ["(Rs) Ají Panca", "Ávila", "(P) Bife Ancho", "Cebolla"])
    check("cantidad y valorizado se suman entre áreas",
          (L.productos.loc["01", "cantidad"], L.productos.loc["01", "valorizado"]),
          (3.0, 30.0))
    check("el precio es el del kardex, no se suma",
          L.productos.loc["01", "precio"], 10.0)
    check("las áreas son las que tienen stock (CAVA en cero no)",
          sorted(L.areas.loc[L.areas["codigo"] == "01", "area"]),
          ["BARRA", "COCINA"])
    check("un stock negativo también es existencia",
          int(L.productos.loc["04", "areas"]), 2)
    check("el producto sin stock queda fuera y se cuenta",
          ("03" in L.productos.index, L.sin_stock), (False, 1))
    check("«Ver sin stock» lo trae, sin áreas que desplegar",
          int(armar_listado(d, **cols, incluir_sin_stock=True)
              .productos.loc["03", "areas"]), 0)

    check("familia", armar_listado(d, **cols, familias=["BEBIDAS CON ALCOHOL"])
          .productos.index.tolist(), ["02"])
    check("varias familias a la vez", sorted(
        armar_listado(d, **cols, familias=["BEBIDAS CON ALCOHOL", "ALIMENTOS"])
        .productos.index), ["01", "02", "04"])
    check("subfamilia", armar_listado(d, **cols, familias=["ALIMENTOS"],
                                      subfamilias=["ABARROTES"])
          .productos.index.tolist(), ["04"])

    # El área no es como familia y subfamilia: es de la FILA, así que además
    # de decidir qué productos entran cambia sus números y lo que despliegan.
    La = armar_listado(d, **cols, areas=["COCINA"])
    check("área: entran los que tienen stock ahí",
          sorted(La.productos.index), ["01", "04"])
    check("área: los totales son los de esa área, no los del producto",
          (La.productos.loc["01", "cantidad"], La.productos.loc["04", "valorizado"]),
          (2.0, 10.0))
    check("área: se despliega sólo esa",
          sorted(set(La.areas["area"])), ["COCINA"])
    check("área: el que está en cero AHÍ cuenta como sin stock",
          La.sin_stock, 1)
    check("varias áreas suman entre ellas",
          armar_listado(d, **cols, areas=["COCINA", "BARRA"])
          .productos.loc["04", "cantidad"], 4.0)
    check("buscador sin tildes ni mayúsculas",
          armar_listado(d, **cols, texto="AZUCAR").productos.index.tolist(),
          ["04"])
    check("buscador: todas las palabras, en cualquier orden",
          armar_listado(d, **cols, texto="kg pollo").productos.index.tolist(),
          ["01"])
    check("buscador por código",
          armar_listado(d, **cols, texto="02").productos.index.tolist(),
          ["02"])

    f = filas_grilla(L)
    check("rowData: cada producto seguido de sus áreas",
          list(zip(f["__tipo"], f["__padre"])),
          [("p", ""), ("a", "04"), ("a", "04"), ("p", ""), ("a", "01"),
           ("a", "01"), ("p", ""), ("a", "02")])
    check("la fila de área lleva el ÁREA en «nombre» y deja vacío lo del "
          "producto", tuple(f.loc[1, ["nombre", "familia", "codigo"]]),
          ("COCINA", "", ""))
    check("familia y subfamilia se escriben como nombre propio",
          f.loc[f["codigo"] == "02", "familia"].iloc[0], "Bebidas con Alcohol")

    # En unidad de salida (regla #598), con los casos del reporte por área
    # del POS de Barra del 2026-10-03.
    from graficos.inventario_productos import texto_unidad_salida as tus
    check("unidad de salida · litros en onzas (Vino tinto de la casa)",
          tus(2.813, 32, "LITROS", "ONZAS"), "2 Lt 26.0 oz")
    check("unidad de salida · sin entero, sólo el resto (Aceituna Verde)",
          tus(0.35, 1000, "KILOS", "GRAMOS"), "350 g")
    check("unidad de salida · entero y resto (Miel de Abeja)",
          tus(2.5, 1000, "KILOS", "GRAMOS"), "2 kg 500 g")
    check("unidad de salida · lo que dos decimales se comían (Anís, 0.05)",
          tus(0.051, 1000, "KILOS", "GRAMOS"), "51 g")
    check("unidad de salida · negativo, con el signo adelante",
          tus(-10645.164, 1000, "LITROS", "MILILITROS"), "−10,645 Lt 164 ml")
    check("unidad de salida · el resto que redondea a una unidad, sube",
          tus(0.9999, 1000, "LITROS", "MILILITROS"), "1 Lt")
    check("unidad de salida · misma unidad: la cantidad tal cual",
          tus(14, 1, "UND", "UND"), "14 und")
    check("unidad de salida · sin unidad de salida: tal cual",
          tus(1.25, float("nan"), "KILOS", ""), "1.25 kg")
    check("unidad de salida · cero", tus(0, 32, "LITROS", "ONZAS"), "0 Lt")

    d2 = d.assign(FAC=[1000.0] * 3 + [32.0, 1000.0, 1000.0, 1000.0],
                  US=["GRAMOS"] * 3 + ["ONZAS", "GRAMOS", "GRAMOS", "GRAMOS"])
    f2 = filas_grilla(armar_listado(d2, **cols, col_factor="FAC",
                                    col_usal="US"))
    check("rowData: el producto trae su cantidad en unidad de salida",
          f2.loc[f2["__id"] == "02", "cant_salida"].iloc[0], "3 Lt")
    check("rowData: cada ÁREA se parte con el factor de su producto",
          f2.loc[f2["__id"] == "04|BARRA", "cant_salida"].iloc[0], "−1 kg")
    check("rowData: y la del kardex, para el tooltip",
          f2.loc[f2["__id"] == "01", "cant_kardex"].iloc[0], "3 kg")
    return fallos


def _pruebas_analisis_stock():
    """`analisis_stock.py` y el listado con historia (regla #637): los cierres
    del día 7, la regla del correlativo en cada momento, el consumo del
    restaurante (sin lo que va de un área a otra ni los ajustes), el ABC, los
    días de inventario, el estado, y que el gráfico del recorte cuente
    también los productos que hoy están en cero."""
    import datetime as _dt
    import analisis_stock as A
    from graficos.inventario_productos import (
        armar_listado, cuentas_estado, filas_grilla, por_estado)

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    analisis stock · {nombre}")
        else:
            fallos += 1
            print(f"FALLA analisis stock · {nombre}: got={got!r} exp={exp!r}")

    m = A.momentos_de_cierre(_dt.datetime(2026, 10, 9, 14))
    check("13 cierres y hoy", len(m), 14)
    check("el primero, 12 meses antes del último", m[0][0], "set 25")
    check("el cierre de setiembre se toma el 7 de octubre, ya contado",
          m[-2], ("set 26", _dt.datetime(2026, 10, 7, 23)))
    check("y al final, hoy", m[-1][0], "hoy")
    check("con el kardex al 5, setiembre todavía no cerró",
          A.momentos_de_cierre(_dt.datetime(2026, 10, 5, 9))[-2][0], "ago 26")

    fotos = pd.DataFrame({
        "area": ["001", "001", "001", "002"], "cod": ["P", "P", "P", "Q"],
        "fecha": pd.to_datetime(["2026-01-10 08:00", "2026-02-03 10:00",
                                 "2026-02-03 09:00", "2026-02-20 12:00"]),
        # El de las 09:00 tiene el correlativo MAYOR: manda él, no el de las 10.
        "correlativo": [1, 2, 3, 1],
        "stock": [2.0, 5.0, 4.0, 1.0], "precio": [10.0, 10.0, 10.0, 3.0]})
    v = A.valor_en_momentos(fotos, [_dt.datetime(2026, 1, 31, 23),
                                    _dt.datetime(2026, 2, 28, 23)])
    check("al primer momento, la foto de enero", v.loc[("001", "P"), 0], 20.0)
    check("manda el mayor correlativo, no la hora más tardía",
          v.loc[("001", "P"), 1], 40.0)
    check("sin movimiento hasta un momento, vale cero", v.loc[("002", "Q"), 0], 0.0)

    movs = pd.DataFrame({
        "cod": ["P", "P", "P", "P", "P", "Q"],
        "tipo": ["95", "97", "99", "93", "01", "96"],
        "cant_out": [3.0, 50.0, 40.0, 7.0, 1.0, 2.0]})
    c = A.consumo_por_producto(movs)
    check("consumo: ventas sí; transferencia, requerimiento, ajuste y "
          "compra no", float(c["P"]), 3.0)
    check("el porcionamiento es consumo", float(c["Q"]), 2.0)

    abc = A.clase_abc(pd.Series({"a": 70.0, "b": 20.0, "c": 6.0, "d": 4.0,
                                 "e": -5.0, "f": 0.0}))
    # b es A: lo acumulado ANTES de él (70 %) no llegaba al 80 %.
    check("ABC: A mientras lo de antes no llega al 80 %, B al 95 %, C el resto",
          list(abc), ["A", "A", "B", "C", None, None])
    d = A.dias_de_inventario(pd.Series([9.0, 1.0, 0.0, -2.0]),
                             pd.Series([90.0, 0.0, 90.0, 90.0]))
    check("días: stock ÷ consumo diario", float(d[0]), 9.0)
    check("días: sin consumo o sin stock no es un número",
          [x != x for x in d[1:]], [True, True, True])
    e = A.estado(pd.Series([-1.0, 5.0, 100.0, 1.0]), pd.Series([9.0, 0.0, 90.0, 90.0]),
                 pd.Series([float("nan"), float("nan"), 100.0, 1.0]))
    check("estado: negativo, sin consumo, más de 60 días, nada",
          list(e), ["neg", "sin", "alto", ""])
    check("días de un conjunto: valor ÷ consumo diario en soles",
          round(A.dias_del_conjunto([100.0, 50.0], [10.0, 5.0], [90.0, 0.0],
                                    [10.0, 10.0]), 6), 15.0)

    d = pd.DataFrame({
        "COD": ["01", "01", "02", "03"], "CA": ["000", "001", "001", "000"],
        "PROD": ["Pollo", "Pollo", "Pisco", "Sal"],
        "FAM": ["ALIMENTOS", "ALIMENTOS", "BEBIDAS", "ALIMENTOS"],
        "SUB": ["AVES", "AVES", "PISCO", "ABARROTES"],
        "AREA": ["ALMACEN", "COCINA", "COCINA", "ALMACEN"],
        "UM": ["KILOS", "KILOS", "LITROS", "KILOS"], "PU": [10.0, 10.0, 30.0, 2.0],
        "STK": [2.0, -1.0, 3.0, 0.0], "VAL": [20.0, -10.0, 90.0, 0.0]})
    hist = pd.DataFrame(
        [[5, 20], [0, -10], [60, 90], [40, 0]], columns=[0, 1],
        index=pd.MultiIndex.from_tuples([("000", "01"), ("001", "01"),
                                         ("001", "02"), ("000", "03")]))
    cols = dict(col_cod="COD", col_prod="PROD", col_fam="FAM", col_subfam="SUB",
                col_area="AREA", col_unidad="UM", col_punit="PU", col_cant="STK",
                col_val="VAL", col_cod_area="CA", historia=hist,
                consumo=pd.Series({"01": 9.0}))
    L = armar_listado(d, **cols)
    check("el gráfico del recorte cuenta la Sal, que hoy está en cero",
          [float(x) for x in L.serie], [105.0, 100.0])
    check("cada producto suma la historia de sus áreas",
          (float(L.productos.loc["01", "__h0"]), float(L.productos.loc["01", "__h1"])),
          (5.0, 10.0))
    check("días y estado del producto",
          (float(L.productos.loc["01", "dias"]), L.productos.loc["02", "estado"]),
          (10.0, "sin"))
    check("el buscador no cambia el ABC: es del recorte",
          armar_listado(d, **cols, texto="pollo").productos.loc["01", "abc"], "B")
    check("cuántos hay en cada chip", cuentas_estado(L.productos),
          {"todos": 2, "A": 1, "neg": 0, "sin": 1, "alto": 0})
    check("un chip deja sus productos y sus áreas",
          (por_estado(L, "sin").productos.index.tolist(),
           sorted(set(por_estado(L, "sin").areas["codigo"]))), (["02"], ["02"]))
    f = filas_grilla(L)
    check("la historia viaja como texto, en el producto y en cada área",
          list(f["__sp"]), ["5,10", "5,20", "0,-10", "60,90", "60,90"])
    check("la unidad corta también en las filas de área", list(f["__um"]),
          ["kg", "kg", "kg", "Lt", "Lt"])
    check("sin historia el listado sigue como antes",
          armar_listado(d, **{**cols, "historia": None, "consumo": None}).serie, None)

    # Stock por Área y Familia (regla #638).
    top, total, cambiaron = A.lo_que_mas_cambio(
        pd.DataFrame({0: [10, 0, 5, 3], 1: [0, 8, 5, 3.4]},
                     index=["vacio", "nuevo", "igual", "poco"]), 0, n=1)
    check("qué más cambió: el mayor cambio, aunque se haya vaciado",
          top.to_dict(), {"vacio": -10.0})
    check("qué más cambió: el total de todos y cuántos se movieron un sol",
          (round(total, 6), cambiaron), (-1.6, 2))
    from graficos.inventario import TODAS, _filtrar_ruta
    _d = pd.DataFrame({"AREA": ["COCINA", "BARRA"], "FAM": ["A", "B"]})
    check("«Todas las áreas» no recorta, la familia sí",
          _filtrar_ruta(_d, (("AREA", TODAS, "Todas las áreas"),
                             ("FAM", "B", "B"))).index.tolist(), [1])
    return fallos


def _pruebas_inventario_activos():
    """«Stock e Inventario» cuenta sólo lo ACTIVO (regla #598).

    `separar_activos` aplica `data.INVENTARIO_ACTIVO`: área activa, producto
    activo, habilitado en el área (COMPARTIDO) y de mercadería. Lo que fija:
    el MOTIVO es la primera marca que falla en ese orden, una celda vacía no
    saca la fila, y una columna que el parquet todavía no trae no filtra —
    AREA ACTIVA y TIPO PRODUCTO llegaron con la consulta del 2026-10-03.
    """
    from graficos.inventario import separar_activos, COL_MOTIVO

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    inventario activos · {nombre}")
        else:
            fallos += 1
            print(f"FALLA inventario activos · {nombre}: got={got!r} exp={exp!r}")

    d = pd.DataFrame({
        "CODIGO PRODUCTO": ["A", "B", "C", "D", "E", "F"],
        "AREA ACTIVA":     ["ACTIVA", "NO ACTIVA", "ACTIVA", "ACTIVA",
                            "ACTIVA", "ACTIVA"],
        "PRODUCTO ACTIVO": ["ACTIVO", "NO ACTIVO", "NO ACTIVO", "ACTIVO",
                            "ACTIVO", "ACTIVO"],
        "COMPARTIDO":      ["COMPARTIDO", "COMPARTIDO", "COMPARTIDO",
                            "NO COMPARTIDO", "COMPARTIDO", "COMPARTIDO"],
        "TIPO PRODUCTO":   ["MERCADERIA", "MERCADERIA", "MERCADERIA",
                            "MERCADERIA", "SERVICIO", None],
        "VALORIZADO TOTAL": [10.0, -5.0, 3.0, 2.0, 100.0, 7.0],
    })
    act, exc = separar_activos(d)
    check("entran los activos (y el de tipo vacío: sin dato no hay motivo)",
          act["CODIGO PRODUCTO"].tolist(), ["A", "F"])
    check("el motivo es la PRIMERA marca que falla",
          dict(zip(exc["CODIGO PRODUCTO"], exc[COL_MOTIVO])),
          {"B": "Área inactiva", "C": "Producto inactivo",
           "D": "No habilitado en el área", "E": "Servicio"})
    check("activos + excluidos = la tabla entera",
          len(act) + len(exc), len(d))
    act2, exc2 = separar_activos(d.drop(columns=["AREA ACTIVA",
                                                 "TIPO PRODUCTO"]))
    check("sin las columnas nuevas filtra con las que hay",
          (act2["CODIGO PRODUCTO"].tolist(),
           sorted(exc2["CODIGO PRODUCTO"])), (["A", "E", "F"], ["B", "C", "D"]))
    return fallos


def _pruebas_kardex():
    """El stock A UNA FECHA (kardex.py + inventario_productos, regla #601).

    Lo que fija: la foto es la del ÚLTIMO movimiento hasta ese momento —por
    correlativo, no por hora—, con la hora pedida ENTERA adentro; lo que no
    se movió desde el 2025 sale del saldo inicial; el precio va a tres
    decimales y es el del área. Y del lado de la tabla: sin foto el stock era
    cero, «Comparar con hoy» conserva lo de hoy, y lo que se terminó desde
    entonces sigue en la tabla.
    """
    import datetime as dt
    import duckdb
    import kardex
    from graficos.inventario_productos import (
        COL_CANT_HOY, COL_VAL_HOY, armar_listado, filas_grilla,
        stock_a_la_fecha)

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    kardex · {nombre}")
        else:
            fallos += 1
            print(f"FALLA kardex · {nombre}: got={got!r} exp={exp!r}")

    h = pd.Timestamp
    k = pd.DataFrame({
        "FECHA HORA": [h("2024-12-31 23:00"), h("2026-09-30 14:00"),
                       h("2026-09-30 14:00"), h("2026-09-30 15:00"),
                       h("2024-12-31 23:00"), h("2026-10-01 09:00"),
                       h("2026-09-30 10:00")],
        "CODIGO AREA": ["000", "000", "000", "000", "007", "007", "007"],
        "CODIGO PRODUCTO": ["A", "A", "A", "A", "A", "B", "C"],
        # Dos tipos en la MISMA hora: manda el correlativo, no el orden.
        "COD TIPO": ["SI", "99", "01", "95", "SI", "01", "95"],
        "ULTIMO CORRELATIVO": [10, 30, 25, 40, 5, 7, 6],
        "STOCK DESPUES": [5.0, 3.0, 8.0, 1.0, 2.0, 4.0, 0.0],
        "PRECIO PROMEDIO DESPUES": [10.0, 12.34567, 12.0, 12.5, 9.0, 3.0,
                                    1.0],
    })
    con = duckdb.connect()
    con.register("k", k)

    def foto(cuando):
        f = con.execute(kardex.sql_stock_al("k", cuando)).df()
        return {(r.area, r.cod): (r.stock, r.precio)
                for r in f.itertuples()}

    check("la hora pedida entra ENTERA (14 = hasta las 14:59)",
          kardex.momento(dt.date(2026, 9, 30), 14),
          dt.datetime(2026, 9, 30, 14, 0))
    f14 = foto(kardex.momento(dt.date(2026, 9, 30), 14))
    check("en la misma hora manda el correlativo mayor, y el precio va a "
          "tres decimales", f14[("000", "A")], (3.0, 12.346))
    check("sin movimientos desde el 2025: el saldo inicial",
          f14[("007", "A")], (2.0, 9.0))
    check("lo que todavía no existía no tiene foto",
          ("007", "B") in f14, False)
    check("la hora siguiente ya cuenta el movimiento de las 15",
          foto(kardex.momento(dt.date(2026, 9, 30), 15))[("000", "A")],
          (1.0, 12.5))
    check("antes del 2025, sólo el saldo",
          foto(dt.datetime(2024, 12, 31, 23))[("000", "A")], (5.0, 10.0))

    d = pd.DataFrame({
        "COD AREA": ["000", "007", "007", "000"],
        "AREA": ["ALMACEN CENTRAL", "COCINA", "COCINA", "ALMACEN CENTRAL"],
        "COD": ["A", "A", "B", "C"],
        "PROD": ["Ajo", "Ajo", "Berro", "Culantro"],
        "FAM": ["VERDURAS"] * 4, "SUB": ["HOJAS"] * 4,
        "UM": ["KILOS"] * 4,
        "PU": [12.0, 12.0, 3.0, 1.0],
        "STK": [4.0, 0.0, 6.0, 2.0],
        "VAL": [48.0, 0.0, 18.0, 2.0],
    })
    fx = pd.DataFrame({"area": ["000", "007"], "cod": ["A", "A"],
                       "stock": [3.0, 2.0], "precio": [12.346, 9.0]})
    t = stock_a_la_fecha(d, fx, col_area="COD AREA", col_cod="COD",
                         col_cant="STK", col_val="VAL", col_punit="PU")
    check("la cantidad y el valorizado son los de la FOTO, con el precio "
          "del área", (t.loc[0, "STK"], round(t.loc[0, "VAL"], 3),
                       t.loc[1, "VAL"]), (3.0, 37.038, 18.0))
    check("sin foto el stock era cero, con el precio de hoy",
          (t.loc[2, "STK"], t.loc[2, "VAL"], t.loc[2, "PU"]), (0.0, 0.0, 3.0))
    check("lo de hoy queda aparte, para comparar",
          (t[COL_CANT_HOY].tolist(), t[COL_VAL_HOY].tolist()),
          ([4.0, 0.0, 6.0, 2.0], [48.0, 0.0, 18.0, 2.0]))

    # «Hoy» con la foto del último momento: misma regla de precio que la
    # fecha (el área a 12.346 y no al 12 del maestro); la fila que el kardex
    # no tiene se queda con la de hoy.
    fh = pd.DataFrame({"area": ["000", "007"], "cod": ["A", "B"],
                       "stock": [4.0, 6.0], "precio": [12.346, 3.0]})
    th = stock_a_la_fecha(d, fx, col_area="COD AREA", col_cod="COD",
                          col_cant="STK", col_val="VAL", col_punit="PU",
                          foto_hoy=fh)
    check("«Hoy» sale de la foto del último momento, al precio del área",
          [round(v, 3) for v in th[COL_VAL_HOY]], [49.384, 0.0, 18.0, 2.0])

    cols = dict(col_cod="COD", col_prod="PROD", col_fam="FAM",
                col_subfam="SUB", col_area="AREA", col_unidad="UM",
                col_punit="PU", col_cant="STK", col_val="VAL")
    L = armar_listado(t, **cols, col_cant_hoy=COL_CANT_HOY,
                      col_val_hoy=COL_VAL_HOY)
    check("lo que hoy tiene stock y entonces no, sigue en la tabla",
          sorted(L.productos.index), ["A", "B", "C"])
    check("con dos precios entre áreas, el del producto es el ponderado",
          round(L.productos.loc["A", "precio"], 4),
          round((3 * 12.346 + 2 * 9.0) / 5, 4))
    check("un área que entonces tenía stock y hoy no, se despliega",
          sorted(L.areas.loc[L.areas["codigo"] == "A", "area"]),
          ["ALMACEN CENTRAL", "COCINA"])
    f = filas_grilla(L)
    _b = f[f["__id"] == "B"].iloc[0]
    check("la diferencia es hoy − la fecha, en soles",
          (_b["cant_hoy"], _b["val_hoy"], _b["dif"]), (6.0, 18.0, 18.0))
    check("sin «Comparar con hoy», los que estaban en cero se cuentan "
          "aparte (Berro y Culantro: ninguno tiene foto)",
          armar_listado(t, **cols).sin_stock, 2)

    # ── Movimientos por tipo (regla #602) ─────────────────────────────
    from graficos.inventario_movimientos import (
        armar_movimientos, periodo_por_defecto)
    check("grupos: los códigos de SUNAT son compras, los internos por tipo",
          [kardex.grupo_de(c) for c in ("01", "07", "46", "95", "93", "98",
                                         "94", "96", "97", "99", "XX")],
          ["compras", "compras", "compras", "ventas", "ajustes", "salidas",
           "produccion", "produccion", "entre", "entre", "otros"])
    km = pd.DataFrame({
        "FECHA HORA": [h("2024-12-31 23:00"), h("2026-09-01 00:00"),
                       h("2026-09-30 23:00"), h("2026-10-01 00:00"),
                       h("2026-09-15 12:00"), h("2026-09-15 13:00")],
        "CODIGO AREA": ["000"] * 4 + ["001", "001"],
        "CODIGO PRODUCTO": ["A"] * 4 + ["B", "B"],
        "COD TIPO": ["SI", "01", "99", "01", "95", "95"],
        "TIPO MOVIMIENTO": ["Saldo", "Factura", "Requerimiento", "Factura",
                            "Descargo de Ventas", "Descargo de Ventas"],
        "CANT INGRESO": [0, 10, 0, 5, 0, 0.0],
        "CANT SALIDA": [0, 0, 6, 0, 2, 1.0],
        "VALOR INGRESO": [0, 100, 0, 50, 0, 0.0],
        "VALOR SALIDA": [0, 0, 60, 0, 0, 7.0],
        "MOVIMIENTOS": [0, 1, 3, 1, 2, 1],
        "ANULACIONES": [0, 0, 1, 0, 0, 0],
    })
    con.register("km", km)
    mv = con.execute(kardex.sql_movimientos(
        "km", dt.date(2026, 9, 1), dt.date(2026, 9, 30))).df()
    check("el período va de las 00:00 del primero a las 23:59 del último, "
          "sin el saldo inicial",
          sorted(zip(mv["cod"], mv["tipo"])), [("A", "01"), ("A", "99"),
                                                ("B", "95")])
    _b = mv[mv["cod"] == "B"].iloc[0]
    check("la venta que salió con valor cero se cuenta aparte",
          (_b["cant_out"], _b["val_out"], _b["cant_sin_costo"],
           _b["movs_sin_costo"]), (3.0, 7.0, 2.0, 2))

    dm = pd.DataFrame({
        "CA": ["000", "001", "001"], "AREA": ["ALMACEN CENTRAL", "COCINA",
                                             "COCINA"],
        "COD": ["A", "A", "B"], "PROD": ["Ajo", "Ajo", "Berro"],
        "FAM": ["VERDURAS"] * 3, "PU": [10.0, 10.0, 5.0],
    })
    mov = pd.DataFrame({
        "area": ["000", "000", "001", "001", "001", "000"],
        "cod": ["A", "A", "A", "A", "B", "Z"],
        "tipo": ["01", "99", "99", "95", "95", "01"],
        "nombre": ["Factura", "Requerimiento", "Requerimiento",
                   "Descargo de Ventas", "Descargo de Ventas", "Factura"],
        "val_in": [100.0, 0, 60, 0, 0, 999], "val_out": [0, 60.0, 0, 50, 0, 0],
        "movs": [1, 3, 3, 9, 2, 1], "anul": [0, 1, 1, 0, 0, 0],
        "cant_sin_costo": [0, 0, 0, 0, 2.0, 0],
        "movs_sin_costo": [0, 0, 0, 0, 2, 0],
    })
    f_ini = pd.DataFrame({"area": ["000"], "cod": ["A"], "stock": [1.0],
                          "precio": [10.0]})
    f_fin = pd.DataFrame({"area": ["000", "001", "001", "000"],
                          "cod": ["A", "A", "B", "Z"],
                          "stock": [5.0, 1.0, -2.0, 9.0],
                          "precio": [10.0, 12.0, 0.0, 111.0]})
    cm = dict(col_cod_area="CA", col_cod="COD", col_area="AREA",
              col_prod="PROD", col_fam="FAM", col_punit="PU")
    M = armar_movimientos(dm, mov, f_ini, f_fin, **cm)
    check("las puntas y los netos, sólo de lo que está en el reporte "
          "(el Z inactivo no entra)",
          (M.ini, M.fin, M.netos["compras"], M.netos["entre"],
           M.netos["ventas"]), (10.0, 62.0, 100.0, 0.0, -50.0))
    check("la valorización es lo que ningún movimiento explica",
          round(M.valorizacion, 6), 2.0)
    _c = M.por_area.set_index("area").loc["COCINA"]
    check("por área: Cocina recibió por requerimiento y vendió",
          (_c["ini"], _c["entre"], _c["ventas"], _c["fin"],
           round(_c["valorizacion"], 6)), (0.0, 60.0, -50.0, 12.0, 2.0))
    check("por tipo: en el orden de los grupos, con sus anulaciones",
          list(zip(M.por_tipo["tipo"], M.por_tipo["anul"])),
          [("01", 0), ("95", 0), ("99", 2)])
    check("lo vendido sin costo, a precio de hoy",
          M.sin_costo[["producto", "movs", "valor_hoy"]].values.tolist(),
          [["Berro", 2, 10.0]])
    Mc = armar_movimientos(dm, mov, f_ini, f_fin, **cm, areas=["COCINA"])
    check("con un área, las puntas y los netos son los suyos",
          (Mc.ini, Mc.fin, Mc.netos["entre"], Mc.netos["compras"]),
          (0.0, 12.0, 60.0, 0.0))
    _Mq = armar_movimientos(dm, mov, f_ini, f_fin, **cm, texto="ajo")
    check("buscador: sólo ese producto (Ajo, no Berro)",
          (_Mq.netos["ventas"], _Mq.sin_costo.empty, _Mq.fin),
          (-50.0, True, 62.0))
    check("abre en el mes pasado entero",
          periodo_por_defecto(dt.date(2025, 1, 1), dt.date(2026, 10, 1)),
          (dt.date(2026, 9, 1), dt.date(2026, 9, 30)))
    check("si el kardex no llega a un mes entero, todo lo que hay",
          periodo_por_defecto(dt.date(2026, 9, 20), dt.date(2026, 10, 1)),
          (dt.date(2026, 9, 20), dt.date(2026, 10, 1)))
    return fallos


def _pruebas_ajuste_kardex():
    """El cierre contra el kardex (kardex.sql_ajuste_con_kardex y la línea
    punteada de Ajuste › Evolución, regla #612).

    Lo que fija: el cruce es por cierre y por los SIETE dígitos del producto
    —el «4» que el kardex tiene con un código que no existe no cae sobre el
    0000004—; un cierre que el kardex no tiene es «sin dato» (NULO) y no
    cero; el ajuste sale en su orden y con sus columnas. Y del lado de la
    vista: un periodo sin dato del kardex no «difiere», la línea del kardex
    va ANTES que la del neto (para que ésta la tape donde coinciden) y sin
    el parquet todo queda como antes.
    """
    import duckdb
    import kardex
    from graficos.ajuste import _evolucion as _ev

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ajuste vs kardex · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ajuste vs kardex · {nombre}: got={got!r} exp={exp!r}")

    aj = pd.DataFrame({
        "CODIGO CIERRE": ["00120251001", "00120251001", "00120251001",
                          "00020240701", "00620240501"],
        "FECHA APERTURA INVENTARIO": pd.to_datetime(
            ["2025-10-01", "2025-10-01", "2025-10-01", "2024-07-01",
             "2024-05-01"]),
        "CODIGO PRODUCTO": ["0000000033", "0000000004", "0000000077",
                            "0000000004", "0000000004"],
        "AJUSTE VALORIZADO": [5.0, -1.0, 0.0, -2.0, 3.0],
    })
    kx = pd.DataFrame({
        "CODIGO CIERRE": ["00120251001", "00120251001", "00020240701",
                          "00020240701", "00999999999"],
        "CODIGO PRODUCTO": ["0000033", "4", "0000004", "0000004", "0000004"],
        "AJUSTE KARDEX": [1.0, 4.0, -3.0, -1.0, 9.0],
        "AJUSTE VALORIZADO KARDEX": [5.0, 12.23, -30.0, -10.0, 99.0],
    })
    con = duckdb.connect()
    con.register("aj", aj)
    con.register("kx", kx)
    j = con.execute(kardex.sql_ajuste_con_kardex("aj", "kx")).df()

    check("las columnas del ajuste, en su orden, y las dos del kardex",
          list(j.columns), list(aj.columns) + [kardex.COL_AJUSTE_KX,
                                               kardex.COL_VALOR_KX])
    check("las filas, en su orden",
          j["CODIGO PRODUCTO"].tolist(), aj["CODIGO PRODUCTO"].tolist())
    _v = j[kardex.COL_VALOR_KX].tolist()
    check("cruza por los siete dígitos (10 en el ajuste, 7 en el kardex)",
          _v[0], 5.0)
    check("el «4» del kardex NO cae sobre el producto 0000004",
          _v[1], 0.0)
    check("lo que el kardex no movió en un cierre que tiene, en cero",
          _v[2], 0.0)
    check("dos movimientos del mismo producto en un cierre se suman",
          (_v[3], j[kardex.COL_AJUSTE_KX].tolist()[3]), (-40.0, -4.0))
    check("un cierre que el kardex no tiene es «sin dato», no cero",
          pd.isna(_v[4]), True)

    # La serie y lo que dibuja.
    d = pd.DataFrame({
        "F": pd.to_datetime(["2025-07-01", "2025-07-01", "2025-08-01",
                             "2025-09-01"]),
        "AV": [-10.0, 4.0, -5.0, -8.0],
        "VT": [0.0, 0.0, 0.0, 0.0],
        "KX": [-30.0, 4.0, -5.4, None],
    })
    dp, orden = _ev.periodos_ajuste(d, "F", "Mes")
    s = _ev.serie_ajuste(dp, orden, "AV", "VT", col_kardex="KX")
    check("la serie trae «kardex», por nombre",
          list(s.columns), ["_clave", "etq", "eje", "anio", "sobrante",
                            "faltante", "neto", "contado", "kardex"])
    check("el kardex del periodo es la suma de sus líneas",
          s["kardex"].tolist()[:2], [-26.0, -5.4])
    check("un periodo sin dato del kardex queda en NaN, no en cero",
          pd.isna(s["kardex"].tolist()[2]), True)
    check("difiere: julio sí, agosto no (S/ 0,40 es redondeo), setiembre "
          "no se sabe", _ev.difiere_kardex(s).tolist(), [True, False, False])
    check("la nota cuenta los periodos con dato",
          "difiere en 1 de 2 meses" in _ev.nota_kardex(s, "Mes"), True)
    fig = _ev.fig_serie(s)
    check("la línea del kardex va ANTES que la del neto (la tapa)",
          [t.name for t in fig.data], ["Sobrante", "Faltante", "Kardex", "Neto"])
    check("el hover del neto dice cuánto difiere el kardex",
          [c[1] for c in fig.data[3].customdata],
          ["S/ -26 · difiere en S/ -20", "igual", "sin dato"])
    check("la tabla suma la columna «Kardex»",
          ">Kardex</th>" in _ev.tabla_resumen_html(s), True)

    s0 = _ev.serie_ajuste(dp, orden, "AV", "VT")
    check("sin el parquet del kardex, la serie de siempre",
          ("kardex" in s0.columns, [t.name for t in _ev.fig_serie(s0).data],
           ">Kardex</th>" in _ev.tabla_resumen_html(s0),
           _ev.nota_kardex(s0, "Mes")),
          (False, ["Sobrante", "Faltante", "Neto"], False, ""))
    return fallos


def _pruebas_merma():
    """Movimientos › las tres vistas de merma (regla #615).

      1. A PRECIO DE HOY la merma vale lo que dice el Reporte de Mermas del
         Almacén (`SpReporteMerma`: merma × precio promedio actual), un
         producto sin precio vale 0 y lo porcionado pasa a la misma vara; al
         COSTO DEL DÍA, la parte de lo que costaron los cortes.
      2. LAS MARCAS: alta contra lo normal del MISMO producto, cero sólo
         donde el producto suele perder, el corte sin peso y la fecha
         anterior a su número; un porcionamiento normal no lleva ninguna.
      3. EL PROVEEDOR es el de la última compra hasta 45 días antes, y es
         «único» si nadie más vendió ese producto en los 21 días previos.
      4. EL KG ÚTIL y lo pagado de más contra el mejor proveedor; los
         cambios de los últimos 90 días, por nombre de columna.
    """
    import numpy as np
    import pandas as pd

    from graficos import movimientos_merma as mm

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    merma #615 · {nombre}")
        else:
            fallos += 1
            print(f"FALLA merma #615 · {nombre}: {got!r} != {exp!r}")

    # Diez porcionamientos normales de lomo (A, 10-19 %) y de pulpo (B,
    # 50 %), y los raros: lomo al 80 %, pulpo sin merma, un corte sin peso
    # y uno numerado en octubre con fecha de septiembre.
    filas = []

    def porc(doc, dia, cod, prod, cant, merma, cortes):
        for fin, cant_fin, pprom, peso in cortes:
            filas.append({
                "COD PORC": doc, "FEC REGIST": pd.Timestamp(dia),
                "SUB ALMACEN": "PRODUCCION", "USUARIO REG": "CARLOS",
                "COD PROD INIC": cod, "PROD INICIAL": prod,
                "UNID PROD INIC": "KILOS", "CANT A PORCIONAR": cant,
                "CANT MERMA": merma, "PROD FINAL RESULT": fin,
                "CANT RESULT": cant_fin, "UNID PROD FIN": "KILOS",
                "PREC PROM PROD FIN": pprom, "PESO RESULT": peso})

    for i in range(10):
        m = 1.0 + i * 0.1
        porc(f"2608{i:06d}", f"2026-08-{i + 1:02d} 10:00", "A", "Lomo", 10.0,
             m, [("Medallón", 10.0 - m, 60.0 * 10 / (10.0 - m), 10.0 - m)])
        porc(f"2608{i + 50:06d}", f"2026-08-{i + 1:02d} 11:00", "B", "Pulpo",
             4.0, 2.0, [("Pulpo cocido", 2.0, 80.0, 2.0)])
    porc("2609000001", "2026-09-10 10:00", "A", "Lomo", 10.0, 8.0,
         [("Medallón", 2.0, 300.0, 2.0)])
    porc("2609000002", "2026-09-11 10:00", "B", "Pulpo", 4.0, 0.0,
         [("Pulpo cocido", 4.0, 80.0, 4.0)])
    porc("2609000003", "2026-09-12 10:00", "A", "Lomo", 10.0, 1.5,
         [("Medallón", 6.0, 60.0, 6.0), ("Trozos", 10.0, 0.0, 0.0)])
    porc("2610000001", "2026-09-30 10:00", "A", "Lomo", 10.0, 1.4,
         [("Medallón", 8.6, 69.77, 8.6)])
    d = pd.DataFrame(filas)
    cols = dict(fecha="FEC REGIST", doc="COD PORC", area="SUB ALMACEN",
                tipo="USUARIO REG", prod="PROD INICIAL", cod="COD PROD INIC",
                unid="UNID PROD INIC", cant="CANT A PORCIONAR",
                merma="CANT MERMA", fin="PROD FINAL RESULT",
                cant_fin="CANT RESULT", unid_fin="UNID PROD FIN",
                pprom="PREC PROM PROD FIN", peso="PESO RESULT")
    base, cortes = mm.porcionamientos(d, cols)
    check("una fila por porcionamiento, con su código",
          (len(base), base.loc[base["doc"] == "2609000003", "cod"].tolist()),
          (24, ["A"]))

    # ── 1. Las dos valorizaciones ─────────────────────────────────────────
    precios = pd.Series({"A": 50.0})
    hoy = mm.valorizar(base, mm.VALOR_HOY, precios)
    sep = hoy["fecha"] >= "2026-09-01"
    check("a precio de hoy: merma × precio promedio, como el SP; sin precio, 0",
          (round(float(hoy.loc[sep, "valor"].sum()), 2),
           float(hoy.loc[hoy["cod"] == "B", "valor"].sum())),
          (round((8.0 + 1.5 + 1.4) * 50.0, 2), 0.0))
    check("a precio de hoy, lo porcionado es cantidad × precio",
          float(hoy.loc[hoy["doc"] == "2609000001", "costo"].iloc[0]), 500.0)
    dia = mm.valorizar(base, mm.VALOR_DIA, precios)
    f1 = dia[dia["doc"] == "2609000001"].iloc[0]
    check("al costo del día: la parte de los cortes que se perdió",
          (round(float(f1["valor"]), 2), round(float(f1["valor_hoy"]), 2)),
          (round(600.0 * 0.8, 2), 400.0))

    # ── 2. Las marcas ─────────────────────────────────────────────────────
    hist = base[base["fecha"] < "2026-09-01"]
    compras = mm.compras_para_proveedor(pd.DataFrame({
        "COD_PRODUCTO": ["A", "A", "B"],
        "FECHA_EMISION_DOC": pd.to_datetime(["2026-09-01", "2026-09-08",
                                             "2026-09-01"]),
        "NOMBRE_PROVEEDOR": ["X", "Y", "Z"],
        "CANTIDAD_COMPRA": [10.0, 10.0, 4.0],
        "VALOR_COMPRA": [600.0, 600.0, 320.0]}))
    b = mm.marcar(mm.con_proveedor(hoy[sep].reset_index(drop=True), compras),
                  mm.normales(hist), cortes)
    marcas = {str(r["doc"]): sorted(k for k in mm.MARCAS if r[f"m_{k}"])
              for _, r in b.iterrows()}
    check("las marcas de cada porcionamiento raro, y ninguna en el normal",
          marcas, {"2609000001": ["alta"], "2609000002": ["cero"],
                   "2609000003": ["sinpeso"], "2610000001": ["fecha"]})
    imp = mm.impacto(b, ["alta"])
    med_a = float(np.median([1.0 + i * 0.1 for i in range(10)]) / 10)
    check("el impacto de la merma alta es lo perdido de más contra la mediana",
          round(float(imp[b["doc"] == "2609000001"].iloc[0]), 2),
          round((0.8 - med_a) * 10 * 50.0, 2))

    # ── 3. El proveedor ───────────────────────────────────────────────────
    p = b.set_index("doc")
    check("la última compra hasta 45 días antes, y si fue de uno solo",
          (p.loc["2609000001", "prov"], bool(p.loc["2609000001", "unico"]),
           p.loc["2610000001", "prov"], p.loc["2609000002", "prov"],
           bool(p.loc["2609000002", "unico"])),
          ("Y", False, "Y", "Z", True))
    check("los días entre la compra y el porcionamiento",
          int(p.loc["2609000001", "dias"]), 2)

    # ── 4. El kg útil, lo pagado de más y los cambios ─────────────────────
    q = pd.DataFrame({
        "doc": [str(i) for i in range(10)], "cod": ["A"] * 10,
        "prod": ["Lomo"] * 10, "unid": ["KILOS"] * 10,
        "fecha": pd.date_range("2026-06-01", periods=10, freq="15D"),
        "prov": ["P1"] * 5 + ["P2"] * 5, "unico": [True] * 10,
        "dias": [1.0] * 10, "cant": [10.0] * 10,
        "merma_cant": [1.0] * 5 + [3.0] * 5, "costo_dia": [100.0] * 10})
    q["pct"] = q["merma_cant"] / q["cant"]
    pp = mm.por_proveedor(q)
    check("el kg útil: lo pagado ÷ lo que quedó, del más barato al más caro",
          (pp.index.tolist(), [round(x, 4) for x in pp["util"]]),
          (["P1", "P2"], [round(500 / 45, 4), round(500 / 35, 4)]))
    r = mm.resumen_proveedores(q)
    check("lo pagado de más contra el mejor proveedor",
          (r.loc["A", "mejor"], r.loc["A", "peor"],
           round(float(r.loc["A", "extra"]), 2)),
          ("P1", "P2", round((500 / 35 - 500 / 45) * 35, 2)))
    q["costo"] = q["costo_dia"]
    ch = mm.cambios(q, pd.Timestamp("2026-11-01"))
    check("los cambios de los últimos 90 días, por nombre de columna",
          (ch.columns.tolist(),
           [round(float(x), 3) for x in ch.loc["A", ["pct_ant", "pct_rec"]]]),
          (["pct_ant", "pct_rec", "dpp", "dprecio", "impacto"], [0.1, 0.3]))
    return fallos


def _pruebas_cortes_y_peso():
    """Movimientos › el precio de los cortes y su peso (regla #647).

      1. EL PRECIO DE UN CORTE es lo que costó lo que entró ÷ lo que quedó ×
         su peso por unidad, y su cambio se reparte entre el insumo, la
         merma, el gramaje y otros: los cuatro suman EXACTO el cambio. Mes a
         mes, la línea «con la merma normal».
      2. LA MARCA «Peso por unidad raro»: contra los porcionamientos
         ANTERIORES del mismo corte, y lejos también de los gramos del
         nombre; corrige la merma y pesa en el impacto. La COSTUMBRE —un
         corte que se registra siempre a 2,6 veces su nombre— no es marca.
      3. LO QUE ARRASTRA: el precio con el peso habitual y los platos
         ACTIVOS que lo llevan, con su costo corregido.
      4. LOS SALTOS desde Recetas: el último porcionamiento de un corte y si
         su peso es raro; el rail y las vistas que nombran existen, y el
         grupo Porcionamientos va de lo general a lo particular.
    """
    import re

    import pandas as pd

    from graficos import carta_costeada as cc
    from graficos import movimientos as mov
    from graficos import movimientos_merma as mm

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    cortes #647 · {nombre}")
        else:
            fallos += 1
            print(f"FALLA cortes #647 · {nombre}: {got!r} != {exp!r}")

    filas = []

    def porc(doc, dia, cod, prod, cant, merma, costo, cortes):
        # Cada corte: (nombre, código, cantidad, peso). El precio lo pone el
        # Almacén: lo que costó ÷ la suma de los pesos × su peso por unidad.
        ckg = costo / sum(p for *_, p in cortes)
        for fin, cod_fin, cant_fin, peso in cortes:
            filas.append({
                "COD PORC": doc, "FEC REGIST": pd.Timestamp(dia),
                "SUB ALMACEN": "PRODUCCION", "USUARIO REG": "CARLOS",
                "COD PROD INIC": cod, "PROD INICIAL": prod,
                "UNID PROD INIC": "KILOS", "CANT A PORCIONAR": cant,
                "CANT MERMA": merma, "PROD FINAL RESULT": fin,
                "COD PROD FINAL": cod_fin, "CANT RESULT": cant_fin,
                "UNID PROD FIN": "UND", "PREC PROM PROD FIN": ckg * peso / cant_fin,
                "PESO RESULT": peso})

    dias = pd.date_range("2026-06-01", periods=8, freq="10D")
    # D, el lomo: antes a 60 el kg y 20 % de merma; desde el 21 de julio a
    # 70 y 30 %. El medallón pesa siempre 0,17 y los retazos se registran
    # con el 30 % de su peso.
    for i, dia in enumerate(dias):
        if dia < pd.Timestamp("2026-07-20"):
            porc(f"D{i}", dia, "D", "Lomo", 10.0, 2.0, 600.0,
                 [("(P) Lomo Medallon 170gr x und (produccion)", "D1", 40.0, 6.8),
                  ("(P) Retazos de carne lomo x Kg (produccion)", "D2", 4.0, 1.2)])
        else:
            porc(f"D{i}", dia, "D", "Lomo", 10.0, 3.0, 700.0,
                 [("(P) Lomo Medallon 170gr x und (produccion)", "D1", 34.0, 5.78),
                  ("(P) Retazos de carne lomo x Kg (produccion)", "D2", 1.22 / 0.3, 1.22)])
    # C, el pulpo: ocho normales (50 % de merma) y uno con 7 kg tipeados
    # en los 20 de 70 g (lo habitual: 1,4). El collar de 125 g se registra
    # SIEMPRE a 0,325 kg por unidad: costumbre.
    for i, dia in enumerate(dias):
        porc(f"C{i}", dia + pd.Timedelta(days=1), "C", "Pulpo entero", 10.0,
             5.0, 400.0,
             [("(P) Pulpo cocido 70gr x und (produccion)", "C1", 20.0, 1.4),
              ("(Rs) Collar 125gr x und DD", "C2", 4.0, 1.3),
              ("(P) Pulpo cocido 120gr x und (produccion)", "C3", 20.0, 2.3)])
    porc("2609000009", "2026-09-15 20:57", "C", "Pulpo entero", 10.0, 0.7,
         400.0, [("(P) Pulpo cocido 70gr x und (produccion)", "C1", 20.0, 7.0),
                 ("(Rs) Collar 125gr x und DD", "C2", 4.0, 1.3),
                 ("(P) Pulpo cocido 120gr x und (produccion)", "C3", 10.0, 1.0)])
    d = pd.DataFrame(filas)
    cols = dict(fecha="FEC REGIST", doc="COD PORC", area="SUB ALMACEN",
                tipo="USUARIO REG", prod="PROD INICIAL", cod="COD PROD INIC",
                unid="UNID PROD INIC", cant="CANT A PORCIONAR",
                merma="CANT MERMA", fin="PROD FINAL RESULT",
                cant_fin="CANT RESULT", unid_fin="UNID PROD FIN",
                pprom="PREC PROM PROD FIN", peso="PESO RESULT",
                cod_fin="COD PROD FINAL")
    base, cortes = mm.porcionamientos(d, cols)
    fin = pd.Timestamp("2026-10-15")

    # ── 1. El precio de los cortes y su desglose ──────────────────────────
    xs = mm.valorizar(base[base["cod"] == "D"], mm.VALOR_DIA)
    pc = mm.precios_de_cortes(xs, cortes, fin)
    med = pc.set_index("clave").loc["D1"]
    check("los cortes del de más valor al de menos, por su código",
          pc["clave"].tolist(), ["D1", "D2"])
    check("el precio de antes y el de los 90 días: costo ÷ lo que quedó × peso",
          (round(med["a"]["P"], 4), round(med["b"]["P"], 4)), (12.75, 17.0))
    des = med["desglose"]
    check("los cuatro factores suman EXACTO el cambio",
          round(sum(des.values()), 9), round(17.0 - 12.75, 9))
    check("sin cambio de gramaje ni de mezcla, esos dos dan cero",
          (round(des["gramaje"], 9), round(des["otros"], 9)), (0.0, 0.0))
    check("el insumo pesó más que la merma, y es la causa",
          (des["insumo"] > des["merma"] > 0, med["causa"]), (True, "insumo"))
    filas_d1 = cortes[cortes["doc"].isin(xs["doc"])
                      & (mm.clave_corte(cortes) == "D1")]
    pm = mm.precio_corte_por_mes(xs, filas_d1, 0.2).set_index("mes")
    ago = pm.loc[pd.Timestamp("2026-08-15")]
    check("mes a mes: el precio y el precio con la merma normal",
          (round(float(ago["precio"]), 4), round(float(ago["normal"]), 4)),
          (17.0, round(17.0 * 0.7 / 0.8, 4)))
    check("el nombre corto de un corte",
          [mm.nombre_corto(n) for n in (
              "(P) Lomo trozos saltado 180gr x und (produccion)",
              "(Rs) Collar / Charela 125gr x und DD")],
          ["Lomo trozos saltado 180gr", "Collar / Charela 125gr"])

    # ── 2. La marca del peso ──────────────────────────────────────────────
    pesos = mm.pesos_por_unidad(base, cortes)
    raros = pesos[pesos["raro"]]
    check("sólo el 70 g tipeado ×5 es raro; el collar de siempre, no",
          sorted(zip(raros["doc"], raros["cod_fin"])), [("2609000009", "C1")])
    sep = mm.valorizar(base[base["fecha"] >= "2026-09-01"].reset_index(drop=True),
                       mm.VALOR_DIA)
    hist = base[base["fecha"] < "2026-09-01"]
    b = mm.marcar(sep, mm.normales(hist), cortes, pesos)
    f = b.iloc[0]
    check("la marca, la merma con el peso habitual y lo que escondió",
          (bool(f["m_peso"]), round(float(f["pct_corr"]), 4),
           round(float(f["dpeso"]), 4)), (True, 0.63, 5.6))
    check("el impacto: lo registrado menos lo del peso habitual",
          round(float(mm.impacto(b, ["peso"]).iloc[0]), 2), round(-5.6 * 40.0, 2))
    check("sin `pesos`, ninguna marca de peso",
          bool(mm.marcar(sep, mm.normales(hist), cortes)["m_peso"].any()), False)
    check("la marca abre prendida", "peso" in mm.MARCAS_DE_ENTRADA, True)

    # ── 3. Lo que arrastra ────────────────────────────────────────────────
    linea = pesos[(pesos["doc"] == "2609000009") & (pesos["cod_fin"] == "C1")].iloc[0]
    p_corr = mm.precio_con_peso_habitual(f, linea)
    check("el precio con el peso habitual: lo que costó ÷ lo que habría "
          "quedado × su peso", round(p_corr, 4), round(400.0 / 3.7 * 0.07, 4))
    p_dia = float(linea["pprom"])
    rv = pd.DataFrame({
        "COD PLATO": ["P1", "P1", "P2", "P3"],
        "NOMB PLATO": ["Fideua", "Fideua", "Arroz", "Viejo"],
        "ITEM VENTA ACTIVO": ["ACTIV", "ACTIV", "ACTIV", "INACTIV"],
        "COD INS": ["C1", "X", "C1", "C1"],
        "TOTAL": [p_dia, 10.0, 2 * p_dia, p_dia],
        "CST SALON": [40.0, 40.0, 50.0, 30.0],
        "%CST SALON": [0.4, 0.4, 0.5, 0.3]})
    pl = mm.platos_con_insumo(rv, "C1", p_corr / p_dia)
    check("los platos activos que lo llevan, con su costo corregido",
          (pl["plato"].tolist(), [round(v, 4) for v in pl["costo_corr"]],
           round(float(pl.set_index("plato").loc["Fideua", "pct_corr"]), 4)),
          (["Arroz", "Fideua"], [round(50 - 2 * p_dia + 2 * p_corr, 4),
                                 round(40 - p_dia + p_corr, 4)],
           round((40 - p_dia + p_corr) * 0.4 / 40, 4)))

    # ── 4. Los saltos y el orden ──────────────────────────────────────────
    u = cc.ultimo_porcionamiento(d, "C1")
    check("desde Recetas: el último porcionamiento del corte y su peso raro",
          (u["doc"], u["cod_de"], u["raro"], round(u["kgu"], 3), round(u["hab"], 3)),
          ("2609000009", "C", True, 0.35, 0.07))
    check("el collar de siempre no se marca; un código sin porcionamientos, None",
          (cc.ultimo_porcionamiento(d, "C2")["raro"],
           cc.ultimo_porcionamiento(d, "ZZ"), cc.ultimo_porcionamiento(None, "C1")),
          (False, None, None))
    src = open("graficos/movimientos.py", encoding="utf-8").read()
    rail = re.search(r'_render_rail\(_RAIL_CATEGORIAS,\s*"([^"]+)"', src)
    check("el rail al que salta Recetas es el de Movimientos",
          rail.group(1) if rail else None, mm.RAIL_MOVIMIENTOS)
    pila = dict(mov._PILA)
    check("las vistas y secciones a las que se salta existen en la pila",
          (pila.get(mm.SEC_REND), pila.get(mm.SEC_REV), pila.get(mm.SEC_PROV) is not None),
          (mm.VISTA_REND, mm.VISTA_REV, True))
    orden = [s for s, _ in mov._PILA if s in ("mov_sec_porc", mm.SEC_REND,
                                              mm.SEC_PROV, mm.SEC_REV)]
    check("Porcionamientos, de lo general a lo particular",
          orden, ["mov_sec_porc", mm.SEC_REND, mm.SEC_PROV, mm.SEC_REV])
    check("la consulta trae el código de cada corte",
          mov._COLS_PORC.get("cod_fin"), "COD PROD FINAL")
    return fallos


def _pruebas_salidas_comparar():
    """Movimientos › salidas: la causa y los años anteriores (regla #614).

      1. LA CAUSA sale del motivo escrito, con erratas y sin tildes, y lo
         que sólo dice «producto de baja» no inventa una.
      2. LA COMPARACIÓN cae en la MISMA clave del eje que su barra: por mes
         con el calendario, por semana con 364 días (el mismo día de la
         semana). Lo anulado tampoco suma el año pasado.
      3. EL AVISO DE POCO REGISTRO: sólo meses enteros, cerrados y con menos
         de la mitad de la mediana de los doce anteriores.

    El «destino de lo que entra», que también vivía acá, pasó a
    `_pruebas_sin_plato` con las dos vistas que lo reemplazaron (#645).
    """
    import pandas as pd

    from graficos import movimientos as mov
    from graficos import movimientos_periodo as mp

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    salidas #614 · {nombre}")
        else:
            fallos += 1
            print(f"FALLA salidas #614 · {nombre}: {got!r} != {exp!r}")

    # ── 1) La causa ───────────────────────────────────────────────────────
    for motivo, causa in (
            ("PRODUCTO DE BAJA / TIEMPO DE VIDA", "Tiempo de vida"),
            ("PRODCUTOS DE BAJA / TEIMPIO DE VIDA", "Tiempo de vida"),
            ("PRODUCTO DE BAJA (MANIPULACION DE COCINA / TIEMPO DE VIDA )",
             "Tiempo de vida"),
            ("Producto de baja / cocción", "Cocción o término"),
            ("BAJA DE PRODUCTO / FRIO MALOGRADO", "Equipo malogrado o frío"),
            ("PRODUCTO DE BAJA / SE ROMPIO", "Manipulación"),
            ("BAJA DE PRODUCTO / NO CUMPLE STANDAR", "No cumple el estándar"),
            ("CONSUMO DIRECTO", "Consumo directo"),
            ("PRODUCTOS DE BAJA", mov.SIN_CAUSA),
            (".\r\n", mov.SIN_CAUSA),
            (None, mov.SIN_CAUSA),
            ("USO MENSUAL", mov.OTRA_CAUSA)):
        check(f"causa de «{str(motivo).strip()[:30]}»",
              mov.causa_de_baja(motivo), causa)
    d = pd.DataFrame({"MOTIVO": ["PRODUCTO DE BAJA / TERMINO", None]})
    check("con_causa agrega la columna",
          mov.con_causa(d, "MOTIVO")[mov.COL_CAUSA].tolist(),
          ["Cocción o término", mov.SIN_CAUSA])
    check("sin columna de motivo, el df tal cual",
          mov.COL_CAUSA in mov.con_causa(d, None).columns, False)

    # ── 1b) La causa sólo en las Bajas, y la unidad (regla #626) ──────────
    for motivo, causa in (
            ("PRODUCTO DE BAJA / USO EN AREA", "Uso en el área"),
            ("PRODUCTOS BAJA USO SALON 31/10725", "Uso en el área"),
            ("PRODUCTOS DE BAJA / FAMILIA", "Comida de personal"),
            ("USO MENSUAL", mov.OTRA_CAUSA)):
        check(f"causa #626 de «{motivo[:30]}»", mov.causa_de_baja(motivo),
              causa)
    d = pd.DataFrame({"MOTIVO": ["TIEMPO DE VIDA", "CONSUMO DIRECTO"],
                      "TIPO DESCARGO": ["Bajas ", "Comida Personal"]})
    check("la causa sólo se lee en las Bajas",
          mov.con_causa(d, "MOTIVO", "TIPO DESCARGO")[mov.COL_CAUSA].tolist(),
          ["Tiempo de vida", mov.NO_ES_BAJA])
    _u = pd.DataFrame({"unid": ["KILOS", "KILOS"], "cant": [1.5, 2.0]})
    check("una sola unidad: se escribe corta", mp.unidad_de_vista(_u), "kg")
    check("dos unidades: no se suman",
          mp.unidad_de_vista(_u.assign(unid=["KILOS", "UND"])), "")
    check("una línea sin unidad: no se suma",
          mp.unidad_de_vista(_u.assign(unid=["KILOS", ""])), "")
    _ago = (pd.Period("2026-08", "M"), 44, 250.0)
    check("las barras de un mes con poco registro",
          mp.periodos_poco_registro(["2026-07", "2026-08", "2026-09"], "Mes",
                                    [_ago]), [False, True, False])
    check("una semana que cruza al mes con poco registro también",
          mp.periodos_poco_registro(["2026-S31", "2026-S30"], "Semana",
                                    [_ago]), [True, False])
    _bh = pd.DataFrame({
        "fecha": pd.to_datetime(
            [f"2025-{m:02d}-{d:02d}" for m in range(9, 13) for d in range(1, 26)]
            + [f"2026-{m:02d}-{d:02d}" for m in range(1, 9) for d in range(1, 26)]
            + ["2026-09-12", "2026-09-20", "2026-10-02"]),
        "estado": "PROCESADO", "vacio": False})
    _bh["doc"] = range(len(_bh))
    _r = (pd.Timestamp("2026-09-10"), pd.Timestamp("2026-10-10"))
    check("un rango de 30 días con 3 salidas contra ~25 al mes: avisa",
          mp.rango_poco_registro(_bh, _r, mp.SALIDAS)[0], 3)
    check("el mismo rango un año antes, con lo normal: no avisa",
          mp.rango_poco_registro(_bh, (pd.Timestamp("2026-07-01"),
                                       pd.Timestamp("2026-08-01")),
                                 mp.SALIDAS), None)
    _ia = mov.salidas_para_ia(pd.DataFrame({
        "LOCAL": ["SAPIENS"], "LLAVE SALIDAS": ["x"], mov.COL_CAUSA: ["c"],
        "_fecha": [pd.Timestamp("2026-09-01")], "VALOR NETO": [1.0]}))
    check("lo que ve el asistente: sin internas, CAUSA y FECHA con nombre",
          list(_ia.columns), ["CAUSA", "FECHA", "VALOR NETO"])

    # ── 2) La comparación con años anteriores ─────────────────────────────
    def _lin(filas):
        return pd.DataFrame({
            "fecha": pd.to_datetime([f for f, *_ in filas]),
            "doc": [doc for _, doc, *_ in filas],
            "estado": [e for *_, e, _ in filas],
            "valor": [v for *_, v in filas],
            "vacio": False, "area": "COCINA", "tipo": "", "fam": "",
            "prod": "x"})
    bh = _lin([("2025-08-05", "a", "PROCESADO", 10.0),
               ("2025-09-10", "b", "PROCESADO", 20.0),
               ("2025-09-11", "c", "ANULADO", 99.0),
               ("2024-09-02", "d", "PROCESADO", 7.0)])
    rng = (pd.Timestamp("2026-08-01"), pd.Timestamp("2026-10-01"))
    comps = mp.comparacion_periodos(bh, rng, "Mes", ["2026-08", "2026-09"],
                                    2)
    check("por mes, el año pasado cae en la barra de su mes",
          comps[0]["tot"], [10.0, 20.0])
    check("lo anulado no suma el año pasado", comps[0]["total"], 30.0)
    check("el rótulo del año", (comps[0]["rot"], comps[1]["rot"]),
          ("2025", "2024"))
    check("dos años atrás", comps[1]["tot"], [0.0, 7.0])
    # Por semana: el miércoles 10/09/2025 es, 364 días después, el miércoles
    # 09/09/2026 — la semana ISO 37 de los dos años.
    sem = mp.comparacion_periodos(
        bh, (pd.Timestamp("2026-09-07"), pd.Timestamp("2026-09-14")),
        "Semana", ["2026-S37"], 1)
    check("por semana, 364 días: el mismo día de la semana",
          sem[0]["tot"], [20.0])
    check("un rango que cruza el año se rotula «2024-25»",
          mp.rotulo_anio(pd.Timestamp("2025-10-01"),
                         pd.Timestamp("2026-10-01"), pd.DateOffset(years=1)),
          "2024-25")
    check("variación sin base es None", mp.variacion_pct(5.0, 0.0), None)
    _dv = _lin([("2026-09-01", "a", "PROCESADO", 5.0),
                ("2026-09-02", "b", "PROCESADO", 3.0)]).assign(
        tipo=["Bajas", "Comida Personal"], clave="2026-09")
    check("el producto se escribe como lo escribe el Almacén",
          mp.nombre_tramo("(P) Calamar limpio", mp.PARTIR_PRODUCTO),
          "(P) Calamar limpio")
    check("el área, en oración",
          mp.nombre_tramo("COCINA PERSONAL", mp.PARTIR_AREA), "Cocina personal")
    check("por tipo: un tramo por tipo de descargo",
          [n for n, _c, _v in mp.trazas_por_area(
              _dv, ["2026-09"], ["Bajas", "Comida Personal"], col="tipo",
              n_traza=4)], ["Bajas", "Comida Personal"])

    # ── 3) El aviso de poco registro ──────────────────────────────────────
    filas = []
    for i, mes in enumerate(pd.period_range("2025-08", "2026-07", freq="M")):
        for k in range(40):
            filas.append((str(mes.start_time.date()), f"{mes}-{k}",
                          "PROCESADO", 1.0))
    filas += [("2026-08-03", f"ago-{k}", "PROCESADO", 1.0) for k in range(10)]
    filas += [("2026-09-03", f"sep-{k}", "PROCESADO", 1.0) for k in range(35)]
    poco = mp.meses_poco_registro(
        _lin(filas), (pd.Timestamp("2026-08-01"), pd.Timestamp("2026-10-01")),
        pd.Timestamp("2026-10-08"))
    check("agosto con 10 de ~40 avisa; septiembre con 35 no",
          [(str(p), n) for p, n, _ in poco], [("2026-08", 10)])
    pocas_sep = [f for f in filas if not f[1].startswith("sep-")] + [
        ("2026-09-03", f"sep-{k}", "PROCESADO", 1.0) for k in range(5)]
    check("el mes en curso no se juzga aunque traiga pocas",
          mp.meses_poco_registro(
              _lin(pocas_sep), (pd.Timestamp("2026-08-01"),
                                pd.Timestamp("2026-10-01")),
              pd.Timestamp("2026-09-15")),
          [(pd.Period("2026-08", "M"), 10, 40.0)])

    return fallos


def _pruebas_sin_plato():
    """Movimientos › las dos vistas de cierre a cierre (regla #645):
    `sin_plato.py` sobre un kardex de mentira con cada caso real.

      1. LOS PERÍODOS van de cierre a cierre: el día después del último
         conteo del cierre anterior hasta el último conteo de este, y los
         conteos del 1 al 7 se juntan en un cierre (#632).
      2. LA CUENTA CIERRA: había + entró − a un plato − preparaciones −
         bajas − otras + ajuste = quedó, producto por producto.
      3. LO VENDIDO SE PARTE con el POS: la cortesía y los eventos por
         receta, el plato DIRECTO por su enlace, lo que el POS no explica
         queda en combos, y nunca se reparte más de lo que el kardex
         descontó. Una línea POR INSUMO baja por su receta base (#648).
      4. EL RESTAURANTE CIERRA: compras = a un plato + bajas + otras +
         faltante neto + operación + Δ stock, con valorización cero cuando
         los precios no cambian; los insumos de operación van aparte.
      5. LO QUE LEEN LAS VISTAS: sin salida registrada, la pareja del
         otro lado del conteo, el % de los cierres anteriores.
      6. LA PILA: las dos vistas en el rail y en la pila, la vieja en
         ninguno, y ningún módulo sigue leyendo el kardex por mes.
    """
    import datetime as dt
    import pathlib

    import pandas as pd

    import cortes
    import definicion_venta as dv
    import sin_plato as sp
    from graficos import movimientos as mov

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    sin plato #645 · {nombre}")
        else:
            fallos += 1
            print(f"FALLA sin plato #645 · {nombre}: got={got!r} exp={exp!r}")

    # ── 1) Los períodos ────────────────────────────────────────────────
    dias = pd.to_datetime(["2025-09-02", "2025-10-01", "2025-10-02",
                           "2025-10-15", "2025-11-03", "2025-11-05",
                           "2025-12-02"])
    per = sp.periodos(cortes.sesiones_inventario(pd.Series(dias)))
    check("dos períodos desde el cierre de setiembre 2025",
          [(p["corto"], str(p["desde"]), str(p["hasta"])) for p in per],
          [("oct 25", "2025-10-03", "2025-11-05"),
           ("nov 25", "2025-11-06", "2025-12-02")])
    check("el parcial del 15 de octubre no corta un período",
          [p["nombre"] for p in per], ["Octubre 2025", "Noviembre 2025"])
    check("las fotos: antes del primero y al final de cada uno",
          sp.momentos(per),
          [dt.datetime(2025, 10, 2, 23), dt.datetime(2025, 11, 5, 23),
           dt.datetime(2025, 12, 2, 23)])

    # ── 2-4) Un período con todo lo que pasa ─────────────────────────────
    per1 = per[:1]
    PR = {"T": 1.2, "Q": 20.0, "C": 2.0, "M": 30.0, "L": 25.0}
    filas_kx = [
        # cod, tipo, entra, sale
        ("T", "94", 100.0, 0.0),   # la orden produjo 100 tartas
        ("T", "95", 0.0, 70.0),    # el POS descontó 70
        ("T", "98", 0.0, 25.0),    # 25 en notas: 20 bajas + 5 personal
        ("T", "93", 0.0, 2.0),     # faltaron 2 en el cierre
        ("Q", "01", 10.0, 0.0),    # el queso, comprado
        ("Q", "07", 0.0, 1.0),     # su nota de crédito
        ("Q", "94", 0.0, 6.0),     # usado en la orden de la tarta
        ("C", "01", 50.0, 0.0),    # carbón
        ("C", "93", 0.0, 40.0),    # se usó, y sólo lo dice el conteo
        ("M", "95", 0.0, 10.0),    # medallón, vendido DIRECTO
        ("M", "93", 5.0, 0.0),     # sobrante
        ("L", "93", 0.0, 4.0),     # lomo trozos: faltante, nada más
    ]
    kx = pd.DataFrame(filas_kx, columns=["cod", "tipo", "cant_in", "cant_out"])
    kx["k"] = 0
    kx["val_in"] = kx["cant_in"] * kx["cod"].map(PR)
    kx["val_out"] = kx["cant_out"] * kx["cod"].map(PR)
    t_ini = pd.Timestamp("2025-10-01 10:00")
    t_fin = pd.Timestamp("2025-11-04 10:00")
    fotos = pd.DataFrame([
        # area, cod, fecha, correlativo, stock
        ("A", "Q", t_ini, 1, 2.0), ("A", "M", t_ini, 2, 20.0),
        ("A", "L", t_ini, 3, 10.0),
        ("A", "T", t_fin, 10, 3.0), ("A", "Q", t_fin, 11, 5.0),
        ("A", "C", t_fin, 12, 10.0), ("A", "M", t_fin, 13, 15.0),
        ("A", "L", t_fin, 14, 6.0),
    ], columns=["area", "cod", "fecha", "correlativo", "stock"])
    fotos["precio"] = fotos["cod"].map(PR)
    salidas = pd.DataFrame({
        "FECHA PROCESADO": pd.to_datetime(["2025-10-10", "2025-10-11",
                                           "2025-10-12", "2025-12-20"]),
        "NOMBRE ESTADO SALIDA": ["PROCESADO", "ANULADO", "PROCESADO",
                                 "PROCESADO"],
        "COD PRODUCTO": ["T", "T", "T", "T"],
        "TIPO DESCARGO": ["Bajas", "Bajas", "Comida Personal", "Bajas"],
        "CANT SALIDA": [20.0, 9.0, 5.0, 8.0],
        "VALOR NETO": [24.0, 10.8, 6.0, 9.6]})
    vend = pd.DataFrame({
        "producto": ["P1", "P1", "P1", "P2", "P1"],
        "dia": pd.to_datetime(["2025-10-05", "2025-10-06", "2025-10-07",
                               "2025-10-08", "2025-12-25"]),
        "grupo": ["Alimentos", "Alimentos", "Eventos", "Alimentos",
                  "Alimentos"],
        "clase": [dv.VENTA, dv.CORTESIA, dv.VENTA, dv.VENTA, dv.VENTA],
        "unidades": [60.0, 5.0, 2.0, 10.0, 99.0]})
    recetas = pd.DataFrame({"COD PLATO": ["P1", "P9"], "COD INS": ["T", "Q"],
                            "CANTIDAD": [1.0, 500.0], "FACTOR": [1.0, 1000.0],
                            "DESCARG": ["SI", "NO"]})
    carta = pd.DataFrame({"COD PLATO": ["P2", "P1"],
                          "TIPO DESC": ["DIRECTO", "DIRECTO"],
                          "COD ITEM O RECETA": ["M", "Q"]})
    maestro = pd.DataFrame({
        "CODIGO PRODUCTO": ["T", "Q", "C", "M", "L"],
        "NOMBRE PRODUCTO": ["(Rs) Tarta de queso", "Queso crema",
                            "Carbon Vegetal", "(P) Lomo Medallon 170gr",
                            "(P) Lomo trozos saltado 170gr"],
        "UNIDAD KARDEX": ["UND", "KILOS", "KILOS", "UND", "UND"],
        "NOMBRE FAMILIA": ["ALIMENTOS", "ALIMENTOS", "COSTOS PRODUCCION",
                           "ALIMENTOS", "ALIMENTOS"]})
    r = sp.calcular(per1, kx, fotos, salidas, vend, recetas, carta, maestro)
    f = r["filas"].set_index("cod")
    cuadre = (f["ini_q"] + f["entro_q"] - f["plato_q"] - f["prep_q"]
              - f["baja_q"] - f["otras_q"] + f["aj_q"] - f["fin_q"])
    check("la cuenta de cada producto cierra contra el kardex",
          {c: round(float(v), 6) for c, v in cuadre.items()},
          {c: 0.0 for c in cuadre.index})
    check("tarta: entró, bajas (sin la anulada), otras, faltante",
          [round(float(f.loc["T", c]), 2) for c in
           ("entro_q", "baja_q", "otras_q", "falt_q", "sinplato_q")],
          [100.0, 20.0, 5.0, 2.0, 27.0])
    check("tarta: venta, cortesía, eventos y lo de combos",
          [round(float(f.loc["T", c]), 2) for c in
           ("venta_q", "cort_q", "evvi_q", "combos_q", "plato_q")],
          [63.0, 5.0, 2.0, 3.0, 70.0])
    check("tarta: % sin plato sobre todo lo que salió",
          round(float(f.loc["T", "pct"]), 4), round(27 / 97, 4))
    check("queso: lo comprado neto de la nota y lo usado en la orden",
          [float(f.loc["Q", c]) for c in ("entro_q", "prep_q", "compra_v")],
          [9.0, 6.0, 180.0])
    check("el plato DIRECTO no pisa una receta (P1 sigue por la tarta)",
          float(f.loc["Q", "plato_q"]), 0.0)
    check("medallón: vendido directo, sobrante",
          [float(f.loc["M", c]) for c in ("venta_q", "sobr_q", "fin_q")],
          [10.0, 5.0, 15.0])
    check("carbón: insumo de operación", f.loc["C", "clase"], sp.OPERACION)
    t = r["totales"].iloc[0]
    check("el restaurante: compras, a un plato, faltante y sobrante",
          [round(float(t[c]), 2) for c in
           ("compras", "venta", "cort", "evvi", "falt", "sobr", "operacion")],
          [280.0, 375.6, 6.0, 2.4, 102.4, 150.0, 80.0])
    check("y cierra: la valorización es cero con los precios quietos",
          round(float(t["valorizacion"]), 6), 0.0)
    # Más cortesía que lo que el kardex descontó: se reparte a escala.
    vend2 = vend.assign(unidades=[60.0, 50.0, 2.0, 10.0, 0.0])
    f2 = sp.calcular(per1, kx, fotos, salidas, vend2, recetas, carta,
                     maestro)["filas"].set_index("cod")
    check("nunca se reparte más de lo que el kardex descontó",
          round(float(f2.loc["T", "venta_q"] + f2.loc["T", "cort_q"]
                      + f2.loc["T", "evvi_q"]), 6), 70.0)

    # ── 3b) La descarga POR INSUMO (#648) ───────────────────────────────
    # P3 lleva 500 g de la salsa S «por insumo»: el POS no toca S sino su
    # ajo A y su caldo B, y el caldo —también por insumo— baja a sus huesos
    # H. La línea de T pide «por insumo» pero T no tiene receta: queda como
    # producto. P4 lleva la misma salsa como PRODUCTO: ésa descuenta S.
    rv_ins = pd.DataFrame({
        "COD PLATO": ["P3", "P3", "P4"], "COD INS": ["S", "T", "S"],
        "CANTIDAD": [500.0, 1.0, 250.0], "FACTOR": [1000.0, 1.0, 1000.0],
        "DESCARG": ["SI"] * 3, "T DESCARG": ["INSUMO", "INSUMO", "PRODUCTO"]})
    rb_ins = pd.DataFrame({
        # S: 200 g de ajo y 300 ml de caldo por kilo; la receta vieja de S,
        # inactiva, llevaba Z. B: 2 huesos por litro.
        "COD PROD RB": ["S", "S", "S", "B"],
        "COD INS RB": ["A", "B", "Z", "H"],
        "CANT": [200.0, 300.0, 50.0, 2.0],
        "FACTOR INS": [1000.0, 1000.0, 1000.0, 1.0],
        "T DESCARG": ["PRODUCTO", "INSUMO", "PRODUCTO", "PRODUCTO"],
        "RB ACT": ["RB.ACTIV", "RB.ACTIV", "RB.INACT", "RB.ACTIV"],
        "DESCARGA": ["DESC"] * 4})

    def _mapa(m):
        return {(a, b): round(float(q), 6) for a, b, q in
                m[["cp", "ci", "q"]].itertuples(index=False)}
    check("por insumo: la salsa no se descuenta, su ajo y los huesos del "
          "caldo sí; T sin receta y la línea PRODUCTO, como producto",
          _mapa(sp.mapa_descargo(rv_ins, None, rb_ins)),
          {("P3", "A"): 0.1, ("P3", "H"): 0.3, ("P3", "T"): 1.0,
           ("P4", "S"): 0.25})
    check("sin recetabase, cada línea descuenta lo que nombra",
          _mapa(sp.mapa_descargo(rv_ins)),
          {("P3", "S"): 0.5, ("P3", "T"): 1.0, ("P4", "S"): 0.25})
    rb_ciclo = pd.concat([rb_ins, pd.DataFrame({
        "COD PROD RB": ["B"], "COD INS RB": ["S"], "CANT": [100.0],
        "FACTOR INS": [1000.0], "T DESCARG": ["INSUMO"],
        "RB ACT": ["RB.ACTIV"], "DESCARGA": ["DESC"]})], ignore_index=True)
    check("una receta que se nombra a sí misma termina, y ahí queda como "
          "producto", _mapa(sp.mapa_descargo(rv_ins, None, rb_ciclo)).get(
              ("P3", "S")), round(0.5 * 0.3 * 0.1, 6))
    # En el kardex: 10 P3 vendidos descontaron 1 kg de ajo y 3 huesos, y
    # nada de salsa. Leída como producto, el ajo quedaba entero en combos.
    kx3 = pd.DataFrame({"cod": ["A", "H"], "tipo": ["95", "95"],
                        "cant_in": [0.0, 0.0], "cant_out": [1.0, 3.0],
                        "val_in": [0.0, 0.0], "val_out": [10.0, 6.0], "k": 0})
    vend3 = pd.DataFrame({"producto": ["P3"],
                          "dia": pd.to_datetime(["2025-10-05"]),
                          "grupo": ["Alimentos"], "clase": [dv.VENTA],
                          "unidades": [10.0]})
    for nombre, rb_, exp in (("abierta por sus insumos", rb_ins,
                              [1.0, 0.0, 3.0, 0.0]),
                             ("sin recetabase (como hasta la #645)", None,
                              [1.0, 1.0, 3.0, 3.0])):
        f3 = sp.calcular(per1, kx3, None, None, vend3, rv_ins, None, None,
                         recetabase=rb_).get("filas").set_index("cod")
        check(f"ajo y huesos: venta y combos, {nombre}",
              [round(float(f3.loc[c, p]), 6) for c in ("A", "H")
               for p in ("venta_q", "combos_q")], exp)

    # ── 5) Lo que leen las vistas ───────────────────────────────────────
    fk = r["filas"]
    fa = fk[fk["clase"] == sp.ALIMENTOS]
    check("lomo trozos: sin salida registrada; la tarta no",
          sorted(fa.loc[sp.sin_salida_registrada(fa), "cod"]), ["L"])
    check("la palabra que dice qué es", sp.palabra_clave(
        "(P) Lomo trozos saltado 170gr x und"), "lomo")
    check("del otro lado del conteo: el medallón con sobrante",
          sp.parejas(fk, "L")["cod"].tolist(), ["M"])
    fp = pd.DataFrame({"cod": ["X"] * 3, "k": [0, 1, 2],
                       "sinplato_v": [10.0, 30.0, 5.0],
                       "salio_v": [100.0, 100.0, 50.0]})
    check("el % de los cierres anteriores, sumados",
          round(float(sp.pct_previo(fp, 2)["X"]), 4), 0.2)

    # ── 6) La pila ──────────────────────────────────────────────────────
    ids = [v[0] for _c, vs in mov._RAIL_CATEGORIAS for v in vs]
    from graficos import movimientos_destino as md
    nuevas = ("Sin plato por cierre", "En qué se fue cada producto")
    check("los ids escritos son los del salto entre las dos",
          (md.VISTA_CIERRE, md.VISTA_PRODUCTO), nuevas)
    check("las dos vistas en el rail", [x in ids for x in nuevas],
          [True, True])
    check("y en la pila, una tras otra",
          [v for _c, v in mov._PILA if v in nuevas], list(nuevas))
    check("la vieja en ninguno",
          "Destino de lo que entra" in ids
          or any(v == "Destino de lo que entra" for _c, v in mov._PILA), False)
    raiz = pathlib.Path(__file__).parent
    usan_mes = [str(p.relative_to(raiz)) for p in
                [*raiz.glob("*.py"), *(raiz / "graficos").rglob("*.py")]
                if "movimientos_kardex_mes" in p.read_text(encoding="utf-8")
                and p.name != "test_graficos.py"]
    check("nadie lee ya el kardex por mes", usan_mes, [])
    return fallos


def _pruebas_diferencias_ajuste():
    """Ajuste › «Análisis de diferencias» (regla #650): `diferencias_ajuste.py`
    sobre un conteo de mentira con cada caso real del cierre de setiembre
    2026.

      1. LA CUENTA DE CADA LÍNEA CIERRA contra SU conteo anterior (aquí, un
         parcial), y entró y salió van POR MOTIVO: el requerimiento dice de
         qué área vino; la nota de salida se parte por su tipo.
      2. LAS PISTAS: el traslado entre áreas, la producción sin orden (el
         insumo falta, lo que se hace con él sobra en negativo y la receta
         base no se produce), el sistema en negativo, el conteo que revierte
         al anterior, lo que ninguna receta usa y los platos que no se
         vendieron.
      3. «DESCARGA POR INSUMO» (#648): una receta base DD que los platos
         abren por insumo no lleva orden, así que su insumo faltante y ella
         sobrante NO son una producción sin registrar.
      4. LA VISTA está en el rail de Ajuste.
    """
    import pandas as pd

    import cortes
    import diferencias_ajuste as da
    from graficos import ajuste as aj

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    diferencias #650 · {nombre}")
        else:
            fallos += 1
            print(f"FALLA diferencias #650 · {nombre}: got={got!r} exp={exp!r}")

    AREA = {0: "ALMACEN CENTRAL", 1: "COCINA"}
    PROD = {10: ("Langostino x und", "UND", 6.6),
            20: ("(P) Milanesa x und (produccion)", "UND", 23.0),
            21: ("(Rs) Milanesa x und (calientes)", "UND", 25.0),
            30: ("(Rs) Zumo de limon DD", "LITROS", 8.0),
            31: ("Limon", "KILOS", 4.0), 40: ("Pan x Kg", "KILOS", 9.0),
            50: ("Bolsas al vacio", "UND", 0.2), 60: ("Goma Xantana", "KILOS", 5.0),
            70: ("Aceite Frituras", "LITROS", 7.0)}

    def fila(t, a, c, s, k):
        n, u, p = PROD[c]
        return {"FECHA APERTURA INVENTARIO": pd.Timestamp(t), "CODIGO AREA": f"{a:010d}",
                "AREA": AREA[a], "FAMILIA": "ALIMENTOS", "SUBFAMILIA": "ABARROTES",
                "CODIGO PRODUCTO": f"{c:010d}", "PRODUCTO": n, "UNIDAD MEDIDA": u,
                "STOCK AL CIERRE": s, "STOCK DECLARADO": k, "AJUSTE": k - s,
                "PRECIO PROMEDIO": p, "AJUSTE VALORIZADO": (k - s) * p}
    t0, t1 = "2026-09-16 17:30", "2026-10-01 17:35"
    antes = [(0, 10, 36, 36), (1, 10, 0, 0), (1, 20, 0, 0), (1, 21, 0, 0), (1, 30, 0, 0),
             (1, 31, 10, 10), (1, 40, 10, 10), (1, 50, 100, 100), (1, 60, 3, 2),
             (1, 70, 10, 10)]
    ahora = [(0, 10, 36, 0), (1, 10, -17, 22), (1, 20, 44, 0), (1, 21, -40, 5),
             (1, 30, 0, 3), (1, 31, 2, 0), (1, 40, 7, 6), (1, 50, 100, 80), (1, 60, 2, 3),
             (1, 70, 10, 5)]
    ajuste = pd.DataFrame([fila(t0, *x) for x in antes] + [fila(t1, *x) for x in ahora])

    def kx(t, a, c, tipo, ent, sal, stock, movs=1):
        return {"FECHA HORA": pd.Timestamp(t), "CODIGO AREA": f"{a:03d}",
                "CODIGO PRODUCTO": f"{c:07d}", "COD TIPO": tipo, "CANT INGRESO": ent,
                "CANT SALIDA": sal, "MOVIMIENTOS": movs, "STOCK DESPUES": stock}
    kardex = pd.DataFrame([
        kx("2026-09-20 12:00", 1, 10, "95", 0, 17, -17),
        kx("2026-09-18 10:00", 0, 20, "99", 0, 44, 0),
        kx("2026-09-18 10:00", 1, 20, "99", 44, 0, 44),
        kx("2026-09-22 13:00", 1, 21, "95", 0, 40, -40),
        kx("2026-09-21 13:00", 1, 31, "95", 0, 8, 2),
        kx("2026-09-25 09:00", 1, 40, "98", 0, 3, 7, movs=2),
    ])
    rv = pd.DataFrame([
        {"ITEM VENTA ACTIVO": "ACTIV", "RV ACTIV": "RV ACT", "DESCARG": "SI", "COD PLATO": cp,
         "NOMB PLATO": pl, "COD INS": f"{ci:07d}", "CANTIDAD": q, "FACTOR": 1.0,
         "SUBALM INS": "COCINA", "T DESCARG": t, "FECH MODIF": pd.Timestamp("2026-05-01")}
        for cp, pl, ci, q, t in (("0000900", "Cotoletta", 21, 1.0, "PRODUCTO"),
                                 ("0000901", "Mojito", 30, 0.05, "INSUMO"),
                                 ("0000902", "Huevo frito", 70, 0.1, "PRODUCTO"))])
    rb = pd.DataFrame([
        {"RB ACT": "RB.ACTIV", "COD PROD RB": f"{p:07d}", "RB NOMBRE": PROD[p][0],
         "COD INS RB": f"{c:07d}", "INSUMO": PROD[c][0], "CANT": q, "FACTOR INS": 1.0,
         "AREA DESC RB": "COCINA", "T DESCARG": "PRODUCTO",
         "FECH REG": pd.Timestamp("2026-05-01")}
        for p, c, q in ((21, 20, 1.0), (30, 31, 1.2))])
    carta = pd.DataFrame(columns=["TIPO DESC", "COD PLATO", "ITEM VENT", "COD ITEM O RECETA"])
    porc = pd.DataFrame(columns=["COD PROD INIC", "COD PROD FINAL", "PROD FINAL RESULT",
                                 "PROD INICIAL", "COD PORC", "FEC REGIST", "CANT A PORCIONAR"])
    ordenes = pd.DataFrame(columns=["NOMBRE ESTADO", "COD PRODUCTO", "FECHA PROCESO",
                                    "CANTIDAD"])
    salidas = pd.DataFrame([
        {"NOMBRE ESTADO SALIDA": "PROCESADO", "AREA": "COCINA", "COD PRODUCTO": "0000040",
         "FECHA PROCESADO": pd.Timestamp("2026-09-25 09:10"), "CANT SALIDA": q,
         "TIPO DESCARGO": tp}
        for q, tp in ((2.0, "Bajas"), (1.0, "Comida Personal"))])
    venta = pd.DataFrame([
        {"producto": cp, "dia": pd.Timestamp(d), "unidades": u, "costo": 0.0,
         "unidades_costeadas": 0.0}
        for cp, d, u in (("0000900", "2026-09-22", 40), ("0000901", "2026-09-21", 160))])
    ses = cortes.sesiones_inventario(ajuste["FECHA APERTURA INVENTARIO"])
    cierre = [s for s in ses if s["tipo"] == "cierre"][-1]
    r = da.calcular(ajuste, cierre, ses, kardex, rv, rb, carta, porc, ordenes, salidas,
                    venta)
    L, F = r["lineas"], r["fichas"]
    de = {(a, c): x for a, c, x in zip(L["acod"], L["cod"], L.to_dict("records"))}

    def pistas(a, c):
        return [(p["t"], p["f"]) for p in F[de[(a, c)]["id"]]["pistas"]]

    def ti(a, c, t):
        return [p["ti"] for p in F[de[(a, c)]["id"]]["pistas"] if p["t"] == t]

    # 1 — la cuenta y los motivos
    check("una línea por producto y área con diferencia", len(L), 10)
    check("contado antes + entró − salió = sistema, en todas",
          sorted(L["gap"].abs().round(6).unique().tolist()), [0.0])
    check("el conteo anterior es el parcial, no un cierre",
          sorted(set(L["ses0"])), ["Parcial · 16 set"])
    check("el requerimiento dice de qué área vino",
          F[de[(1, "20")]["id"]]["ent"], [["Requerimiento de Almacen Central", 44.0, 1]])
    check("la nota de salida se parte por su tipo",
          F[de[(1, "40")]["id"]]["sal"],
          [["Nota de salida · Bajas", 2.0, 1], ["Nota de salida · Comida Personal", 1.0, 1]])
    # 2 — las pistas
    check("el traslado: falta en el Almacén lo que sobra en Cocina",
          ("area", 1) in pistas(0, "10"), True)
    check("Cocina: el sobrante corrige un negativo", ("neg", 1) in pistas(1, "10"), True)
    check("el insumo falta y lo que se hace con él sobra", ("prod", 1) in pistas(1, "20"), True)
    check("y su receta base se vendió sin orden",
          ti(1, "20", "nada"), ["Su receta base no se produjo"])
    check("la receta base que nadie produce", ti(1, "21", "receta"),
          ["Receta base sin órdenes"])
    check("a la receta base le faltan sus insumos", ti(1, "21", "prod"),
          ["Faltan sus insumos"])
    check("lo que ninguna receta usa", de[(1, "50")]["pista_t"], "nadie")
    check("el conteo que revierte al anterior", ("rev", 1) in pistas(1, "60"), True)
    check("los platos que no se vendieron", ti(1, "70", "nada"),
          ["Sus platos no se vendieron"])
    # 3 — descarga por insumo
    check("una DD por insumo no es una producción sin registrar",
          [t for t, _ in pistas(1, "31") + pistas(1, "30") if t == "prod"], [])
    check("cobertura: soles del faltante y del sobrante",
          tuple(round(x, 2) for x in da.cobertura(L)[:2]),
          (round(36 * 6.6 + 44 * 23 + 2 * 4 + 9 + 20 * 0.2 + 5 * 7, 2),
           round(39 * 6.6 + 45 * 25 + 3 * 8 + 5, 2)))
    check("los números como el resto de Ajuste", (da.es(1135.8), da.es(-2.0)),
          ("1,135.8", "−2"))
    # 4 — la vista
    check("la vista está en el rail de Ajuste",
          [v[0] for _, vs in aj._AJUSTE_RAIL_CATEGORIAS for v in vs if v[0] == "Diferencias"],
          ["Diferencias"])
    return fallos


def _pruebas_diferencias_combos():
    """Ajuste › «Análisis de diferencias», los combos y los productos sin
    precio (regla #651), con el caso real del cierre de setiembre 2026:

      1. VENDIDO CON EL CÓDIGO DEL OTRO: entran 6 Sauvignon Blanc a Cava y no
         sale ninguna; se venden 6 Chardonnay que nunca entraron (el sistema
         queda en −6 y la Chardonnay, sin precio, sobra por S/ 0). La línea
         de S/ 0 entra a la lista —como sobrante, por la CANTIDAD— y las dos
         se señalan una a la otra, como pista fuerte.
      2. LA COPA A ELEGIR DEL COMBO: el Menu Sapiens se vende 16 veces y ese
         día no se descuenta el Reto Malbec, una de sus dos copas: pista
         posible, «hasta» 16 × 0,2.
      3. EL PLATO FIJO DEL COMBO: el pan va siempre, y si el combo se vende
         sin descontarlo, la pista es fuerte y reemplaza a «Nada lo
         descargó» (sus platos sólo se vendieron dentro del combo).
    """
    import pandas as pd

    import cortes
    import diferencias_ajuste as da

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    diferencias #651 · {nombre}")
        else:
            fallos += 1
            print(f"FALLA diferencias #651 · {nombre}: got={got!r} exp={exp!r}")

    AREA = {1: "COCINA", 2: "CAVA"}
    PROD = {80: ("Cinco Sentidos Sauvignon Blanc 750ml", "UND", 38.0),
            81: ("Cinco Sentidos Chardonnay 750ml", "UND", 0.0),
            90: ("Reto Malbec 750ml", "UND", 60.0), 91: ("Pan de la casa", "UND", 1.5)}

    def fila(t, a, c, s, k):
        n, u, p = PROD[c]
        return {"FECHA APERTURA INVENTARIO": pd.Timestamp(t), "CODIGO AREA": f"{a:010d}",
                "AREA": AREA[a], "FAMILIA": "VINOS Y ESPUMANTES", "SUBFAMILIA": "VINO",
                "CODIGO PRODUCTO": f"{c:010d}", "PRODUCTO": n, "UNIDAD MEDIDA": u,
                "STOCK AL CIERRE": s, "STOCK DECLARADO": k, "AJUSTE": k - s,
                "PRECIO PROMEDIO": p, "AJUSTE VALORIZADO": (k - s) * p}
    t0, t1 = "2026-09-16 17:30", "2026-10-01 17:35"
    ajuste = pd.DataFrame(
        [fila(t0, *x) for x in ((2, 80, 0, 0), (2, 81, 0, 0), (2, 90, 10, 10), (1, 91, 20, 20))]
        + [fila(t1, *x) for x in ((2, 80, 6, 0), (2, 81, -6, 0), (2, 90, 9, 5.8),
                                  (1, 91, 20, 4))])

    def kx(t, a, c, tipo, ent, sal, stock):
        return {"FECHA HORA": pd.Timestamp(t), "CODIGO AREA": f"{a:03d}",
                "CODIGO PRODUCTO": f"{c:07d}", "COD TIPO": tipo, "CANT INGRESO": ent,
                "CANT SALIDA": sal, "MOVIMIENTOS": 1, "STOCK DESPUES": stock}
    kardex = pd.DataFrame([kx("2026-09-18 10:00", 2, 80, "99", 6, 0, 6),
                           kx("2026-09-21 13:00", 2, 81, "95", 0, 6, -6),
                           kx("2026-09-19 13:00", 2, 90, "95", 0, 1, 9)])
    rv = pd.DataFrame([
        {"ITEM VENTA ACTIVO": "ACTIV", "RV ACTIV": "RV ACT", "DESCARG": "SI",
         "COD PLATO": f"{cp:07d}", "NOMB PLATO": pl, "COD INS": f"{ci:07d}", "CANTIDAD": q,
         "FACTOR": 1.0, "SUBALM INS": ar, "T DESCARG": "PRODUCTO",
         "FECH MODIF": pd.Timestamp("2026-05-01")}
        for cp, pl, ci, q, ar in ((903, "(Cp) Cinco Sentidos Sauvignon Blanc", 80, 0.2, "CAVA"),
                                  (904, "(Bt) Cinco Sentidos Chardonnay", 81, 1.0, "CAVA"),
                                  (905, "(Cp) Reto Malbec", 90, 0.2, "CAVA"),
                                  (907, "(Cp) Otro vino", 92, 0.2, "CAVA"),
                                  (908, "Pan a la brasa", 91, 1.0, "COCINA"))])
    rb = pd.DataFrame(columns=["RB ACT", "COD PROD RB", "RB NOMBRE", "COD INS RB", "INSUMO",
                               "CANT", "FACTOR INS", "AREA DESC RB", "T DESCARG", "FECH REG"])
    carta = pd.DataFrame(columns=["TIPO DESC", "COD PLATO", "ITEM VENT", "COD ITEM O RECETA"])
    porc = pd.DataFrame(columns=["COD PROD INIC", "COD PROD FINAL", "PROD FINAL RESULT",
                                 "PROD INICIAL", "COD PORC", "FEC REGIST", "CANT A PORCIONAR"])
    ordenes = pd.DataFrame(columns=["NOMBRE ESTADO", "COD PRODUCTO", "FECHA PROCESO",
                                    "CANTIDAD"])
    combos = pd.DataFrame([
        {"COD COMBO": "0000906", "COMBO": "Menu Sapiens Sept2026", "COMBO ACTIVO": 1,
         "GRUPO": g, "COD PRODUCTO": f"{cp:07d}", "PRODUCTO": "", "PRODUCTO ACTIVO": 1,
         "CANTIDAD": 1.0, "FIJO": fijo}
        for g, cp, fijo in (("g", 905, 0), ("g", 907, 0), ("a", 908, 1))])
    venta = pd.DataFrame([
        {"producto": f"{cp:07d}", "dia": pd.Timestamp(d), "unidades": u, "costo": 0.0,
         "unidades_costeadas": 0.0}
        for cp, d, u in ((904, "2026-09-21", 6), (906, "2026-09-24", 16), (905, "2026-09-19", 5))])
    ses = cortes.sesiones_inventario(ajuste["FECHA APERTURA INVENTARIO"])
    cierre = [s for s in ses if s["tipo"] == "cierre"][-1]
    r = da.calcular(ajuste, cierre, ses, kardex, rv, rb, carta, porc, ordenes, None, venta,
                    combos=combos)
    L, F = r["lineas"], r["fichas"]
    de = {(a, c): x for a, c, x in zip(L["acod"], L["cod"], L.to_dict("records"))}

    def pistas(a, c):
        return F[de[(a, c)]["id"]]["pistas"]

    # 1 — vendido con el código del otro, con un lado sin precio
    check("la línea sin precio entra a la lista", (2, "81") in de, True)
    check("y es un sobrante por la cantidad aunque valga S/ 0",
          (de[(2, "81")]["q"], de[(2, "81")]["v"]), (6.0, 0.0))
    check("lo que falta: vendido con el código del otro, fuerte",
          [(p["ti"], p["f"]) for p in pistas(2, "80")][:1],
          [("Vendido con el código del otro", 1)])
    check("lo que sobra apunta al que falta",
          [(p["ti"], p["f"], p.get("r")) for p in pistas(2, "81")][:1],
          [("Vendido con el código del otro", 1, de[(2, "80")]["id"])])
    # 2 — la copa a elegir del combo
    combo = [p for p in pistas(2, "90") if p["t"] == "combo"]
    check("la copa a elegir del combo que no se descontó",
          [(p["ti"], p["f"]) for p in combo], [("Combo que no lo descontó", 0)])
    check("dice hasta cuánto, si todos la eligieron", "hasta 3.2 und" in combo[0]["tx"], True)
    usos = [u for u in F[de[(2, "90")]["id"]]["usos"] if u["via"] == "combo"]
    check("y el combo está en «Dónde se usa»",
          [(u["n"], u["g"], u["fijo"], u["nv"], round(u["hasta"], 6)) for u in usos],
          [("Menu Sapiens Sept2026", "G", False, 16.0, 3.2)])
    # 3 — el plato fijo del combo
    check("el pan fijo del combo: pista fuerte y la principal",
          [(p["t"], p["f"]) for p in pistas(1, "91")][:1], [("combo", 1)])
    check("reemplaza a «Nada lo descargó»",
          [p["t"] for p in pistas(1, "91") if p["t"] == "nada"], [])
    check("y dice que no salió nada con un documento",
          pistas(1, "91")[0]["tx"].startswith("Desde el conteo del 16 set no salió nada"), True)
    return fallos


def _pruebas_diferencias_req_sunat():
    """Ajuste › «Análisis de diferencias», los requerimientos y las facturas de
    SUNAT sin ingresar (regla #652), con los casos reales del cierre de
    setiembre 2026:

      1. QUIÉN LO PIDE: el hueso de pollo no lo usa ninguna receta, y
         Producción lo pide por requerimiento. Un requerimiento no es
         consumo, pero dice qué área lo usa: la pista lo nombra, y la ficha
         lista lo pedido en 90 días por área (no lo de DESPUÉS del conteo).
      2. LA FACTURA SIN INGRESAR: el Caelum Malbec sobra 12 en Cava y una
         factura de 12 que SUNAT tiene y el Almacén no lo nombra: pista
         fuerte. Y no se emparejan nombres que sólo se parecen: «ají
         amarillo en polvo» no es «ají amarillo».
      3. EL REQUERIMIENTO SIN PROCESAR: falta en el Almacén lo que Barra
         pidió y nadie procesó.
    """
    import pandas as pd

    import cortes
    import diferencias_ajuste as da

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    diferencias #652 · {nombre}")
        else:
            fallos += 1
            print(f"FALLA diferencias #652 · {nombre}: got={got!r} exp={exp!r}")

    AREA = {0: "ALMACEN CENTRAL", 2: "CAVA", 6: "PRODUCCION"}
    PROD = {95: ("Hueso De Pollo", "KILOS", 4.0),
            96: ("Caelum Terroir Malbec 750ml", "UND", 30.0),
            97: ("Aji Amarillo En Polvo", "KILOS", 20.0), 98: ("Limon", "KILOS", 3.0)}

    def fila(t, a, c, s, k):
        n, u, p = PROD[c]
        return {"FECHA APERTURA INVENTARIO": pd.Timestamp(t), "CODIGO AREA": f"{a:010d}",
                "AREA": AREA[a], "FAMILIA": "ALIMENTOS", "SUBFAMILIA": "VARIOS",
                "CODIGO PRODUCTO": f"{c:010d}", "PRODUCTO": n, "UNIDAD MEDIDA": u,
                "STOCK AL CIERRE": s, "STOCK DECLARADO": k, "AJUSTE": k - s,
                "PRECIO PROMEDIO": p, "AJUSTE VALORIZADO": (k - s) * p}
    t0, t1 = "2026-09-16 17:30", "2026-10-01 17:35"
    ajuste = pd.DataFrame(
        [fila(t0, *x) for x in ((6, 95, 39.05, 39.05), (2, 96, 0, 0), (6, 97, 1, 1),
                                (0, 98, 20, 20))]
        + [fila(t1, *x) for x in ((6, 95, 47.05, 0), (2, 96, -2, 10), (6, 97, 1, 1.2),
                                  (0, 98, 20, 15))])

    def kx(t, a, c, tipo, ent, sal, stock):
        return {"FECHA HORA": pd.Timestamp(t), "CODIGO AREA": f"{a:03d}",
                "CODIGO PRODUCTO": f"{c:07d}", "COD TIPO": tipo, "CANT INGRESO": ent,
                "CANT SALIDA": sal, "MOVIMIENTOS": 1, "STOCK DESPUES": stock}
    kardex = pd.DataFrame([kx("2026-09-27 14:00", 6, 95, "99", 8, 0, 47.05),
                           kx("2026-09-27 14:00", 0, 95, "99", 0, 8, 0),
                           kx("2026-09-27 14:00", 0, 95, "01", 8, 0, 8),
                           kx("2026-10-06 14:00", 0, 95, "01", 10.2, 0, 10.2),
                           kx("2026-09-25 13:00", 2, 96, "95", 0, 2, -2)])
    vacia = lambda *cols: pd.DataFrame(columns=list(cols))
    rv = vacia("ITEM VENTA ACTIVO", "RV ACTIV", "DESCARG", "COD PLATO", "NOMB PLATO", "COD INS",
               "CANTIDAD", "FACTOR", "SUBALM INS", "T DESCARG", "FECH MODIF")
    rb = vacia("RB ACT", "COD PROD RB", "RB NOMBRE", "COD INS RB", "INSUMO", "CANT",
               "FACTOR INS", "AREA DESC RB", "T DESCARG", "FECH REG")
    carta = vacia("TIPO DESC", "COD PLATO", "ITEM VENT", "COD ITEM O RECETA")
    porc = vacia("COD PROD INIC", "COD PROD FINAL", "PROD FINAL RESULT", "PROD INICIAL",
                 "COD PORC", "FEC REGIST", "CANT A PORCIONAR")
    ordenes = vacia("NOMBRE ESTADO", "COD PRODUCTO", "FECHA PROCESO", "CANTIDAD")
    venta = vacia("producto", "dia", "unidades", "costo", "unidades_costeadas")
    reqs = pd.DataFrame([
        {"CODIGO PRODUCTO": f"{c:07d}", "SUB ALMACEN": a, "FECHA REGISTRO": pd.Timestamp(f),
         "COD REQUERIMIENTO": n, "NOMBRE ESTADO REQUERIMIENTO": e, "CANTIDAD": q}
        for c, a, f, n, e, q in (
            (95, "PRODUCCION", "2026-09-27 14:42", "R1", "PROCESADO", 8.0),
            (95, "PRODUCCION", "2026-09-15 13:31", "R2", "PROCESADO", 19.5),
            (95, "COCINA", "2026-09-15 09:01", "R3", "PROCESADO", 12.0),
            (95, "PRODUCCION", "2026-10-06 14:03", "R4", "PROCESADO", 10.2),
            (98, "BARRA", "2026-09-30 10:00", "R5", "GENERADO", 5.0))])
    sunat = pd.DataFrame([
        {"doc": d, "ruc": "20000000001", "prov": "PROVEEDOR S.A.C.",
         "fecha": pd.Timestamp(f), "descripcion": ds, "cantidad": q, "unidad": u}
        for d, f, ds, q, u in (
            ("E001-3599", "2026-09-20", "CAELUM VINO TINTO MALBEC TERROIRS 750ML", 12.0, "unidad"),
            ("FC01-115", "2026-09-20", "AJI AMARILLO", 2.0, "kg"))])
    ses = cortes.sesiones_inventario(ajuste["FECHA APERTURA INVENTARIO"])
    cierre = [s for s in ses if s["tipo"] == "cierre"][-1]
    r = da.calcular(ajuste, cierre, ses, kardex, rv, rb, carta, porc, ordenes, None, venta,
                    requerimientos=reqs, sunat=sunat)
    L, F = r["lineas"], r["fichas"]
    de = {(a, c): x for a, c, x in zip(L["acod"], L["cod"], L.to_dict("records"))}

    def pistas(a, c):
        return F[de[(a, c)]["id"]]["pistas"]

    # 1 — quién lo pide
    check("lo pedido por área en 90 días, sin lo de después del conteo",
          [(a, q, n, w) for a, q, n, _f, w in F[de[(6, "95")]["id"]]["pide"]],
          [("PRODUCCION", 27.5, 2, 8.0), ("COCINA", 12.0, 1, 0.0)])
    check("la última compra es la de ANTES del conteo, no la que llegó después",
          F[de[(6, "95")]["id"]]["viene"]["compra"], pd.Timestamp("2026-09-27 14:00"))
    check("ninguna receta lo usa, y lo pide Producción",
          [("Produccion lo pidió por requerimiento: 27.5 kg en 2 requerimientos" in p["tx"])
           for p in pistas(6, "95") if p["t"] == "nadie"], [True])
    # 2 — la factura sin ingresar
    check("el sobrante que nombra una factura sin ingresar, con la misma cantidad",
          [(p["t"], p["f"]) for p in pistas(2, "96")][:1], [("sunat", 1)])
    check("y dice qué factura es", "E001-3599" in pistas(2, "96")[0]["tx"], True)
    check("«ají amarillo en polvo» no es «ají amarillo»",
          [p["t"] for p in pistas(6, "97") if p["t"] == "sunat"], [])
    check("las palabras: sin tildes, sin paréntesis, los números aparte",
          da.palabras("(Rs) Chocolate 72% Cacao x Kg"),
          (frozenset({"chocolate", "cacao"}), frozenset({"72"})))
    check("un número distinto no empareja",
          da.parecido(da.palabras("Chocolate 60% Cacao"),
                      da.palabras("CHOCOLATE AL 45% DE CACAO CON LECHE")), None)
    check("ni un prefijo parecido", da.parecido(da.palabras("Membrillo"),
                                                da.palabras("MEMBRESIA PLUXEE")), None)
    # 3 — el requerimiento sin procesar
    check("falta en el Almacén lo que Barra pidió y nadie procesó",
          [(p["t"], p["f"]) for p in pistas(0, "98") if p["t"] == "req"], [("req", 1)])
    return fallos


def _pruebas_detalle_salidas():
    """Movimientos › «Detalle de salidas» (regla #511).

    Los cinco cuadros en cadena que reemplazaron a «Top productos ·
    salidas» el 2026-09-24. Cuatro cosas que se rompen sin que nada avise:

      1. QUÉ SUMA. Su total tiene que ser el de «Salidas por período» para
         las mismas líneas: sin anuladas ni líneas sin producto. Se compara
         contra `_validas` de ESA tarjeta y no contra un número escrito acá,
         que es lo que haría falta si las dos dejaran de coincidir.
      2. EL FORMATO POR ANCHO. `formato_por_ancho` tiene que devolver lo que
         la cadena ya mide por cantidad de cuadros —si no, «Por sub almacén»
         y «Detalle de salidas» dejarían de leerse igual—, y las dos filas
         del Detalle tienen que cortar la primera columna en el mismo sitio.
      3. EL PISO. Las keys de toda llamada a `seccion_cuadros` tienen que
         estar enumeradas en `estilos/_80_cards.py` (una key suelta vuelve
         al escalón; un `[class*=…]` en el `:has()` es la regla #469).
      4. EL RAIL Y LA PILA: la vista nueva en los dos, la vieja en ninguno.
    """
    import ast
    import pathlib

    from graficos import drill_tablas as dt
    from graficos import movimientos as mov
    from graficos import movimientos_periodo as mp

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    detalle de salidas · {nombre}")
        else:
            fallos += 1
            print(f"FALLA detalle de salidas · {nombre}: "
                  f"got={got!r} exp={exp!r}")

    # ── 1) Qué suma ───────────────────────────────────────────────────────
    # S1 de Cocina con dos líneas; S2 ANULADA con valor (no todas valen 0);
    # S3 generada SIN ÍTEMS; S4 de Barra; S5 anulada Y sin ítems (cuenta
    # como anulada, una sola vez: la regla de `no_suman`).
    d = pd.DataFrame({
        "FECHA REGISTRO": pd.to_datetime(
            ["2026-09-07 10:00", "2026-09-07 10:00", "2026-09-08 11:00",
             "2026-09-09 12:00", "2026-09-10 09:00", "2026-09-11 10:00"]),
        "COD SALIDA": ["S1", "S1", "S2", "S3", "S4", "S5"],
        "NOMBRE ESTADO SALIDA": ["PROCESADO", "PROCESADO", "ANULADO",
                                 "GENERADO", "PROCESADO", "anulado "],
        "AREA": ["COCINA", "COCINA", "COCINA PERSONAL", "BARRA", "BARRA",
                 "COCINA"],
        "TIPO DESCARGO": ["Bajas", "Bajas", "Comida Personal", "Bajas",
                          "Uso en el Area", "Bajas"],
        "NOMBRE FAMILIA": ["ALIMENTOS", "ALIMENTOS", "ALIMENTOS", None,
                           "BEBIDAS SIN ALCOHOL", None],
        "NOMBRE SUBFAMILIA": ["CARNES", "VERDURAS", "CARNES", None, "AGUAS",
                              None],
        "NOMBRE PRODUCTO": ["A", "B", "C", None, "D", "  "],
        "CANT SALIDA": [1.0, 2.0, 3.0, None, 4.0, None],
        "VALOR NETO": [10.0, 20.0, 30.0, 0.0, 40.0, 0.0],
    })
    validas, nota = mov.salidas_que_suman(
        d, col_estado="NOMBRE ESTADO SALIDA", col_prod="NOMBRE PRODUCTO",
        col_doc="COD SALIDA", col_val="VALOR NETO")
    check("suma sin anuladas ni líneas sin producto",
          sorted(validas["COD SALIDA"]), ["S1", "S1", "S4"])
    bl = mp.lineas_documentos(
        d, fecha="FECHA REGISTRO", doc="COD SALIDA", area="AREA",
        estado="NOMBRE ESTADO SALIDA", fam="NOMBRE FAMILIA",
        prod="NOMBRE PRODUCTO", cant="CANT SALIDA", val="VALOR NETO",
        tipo="TIPO DESCARGO")
    check("el total es el de «Salidas por período»",
          float(validas["VALOR NETO"].sum()),
          float(mp._validas(bl)["valor"].sum()))
    # El texto con que la tarjeta de salidas cuenta sus anuladas
    # (`Lado.anulados`), sobre SU cuenta: la guarda compara contra ella. Va
    # en la fila TOTAL («TOTAL · sin 2 anuladas», regla #641).
    check("cuenta las anuladas por salida, como la fila de KPI de su vecina",
          nota[0], f"sin {mp.SALIDAS.anulados(mp.no_suman(bl)[0])}")
    check("el tooltip dice cuánto no suma", "S/ 30" in nota[1], True)
    check("el tooltip nombra a la vecina como el rail",
          "«Salidas por Período»" in nota[1], True)
    _sin_anuladas, _nota_vacia = mov.salidas_que_suman(
        d[d["COD SALIDA"] != "S2"].iloc[:2], col_estado="NOMBRE ESTADO SALIDA",
        col_prod="NOMBRE PRODUCTO", col_doc="COD SALIDA", col_val="VALOR NETO")
    check("sin anuladas en el recorte no hay nota", _nota_vacia, None)
    _todo, _ = mov.salidas_que_suman(
        d.drop(columns=["NOMBRE ESTADO SALIDA"]), col_estado=None,
        col_prod="NOMBRE PRODUCTO", col_doc="COD SALIDA", col_val="VALOR NETO")
    check("sin columna de estado suma todo lo que trae producto",
          len(_todo), 4)

    # ── 2) El formato por ancho ───────────────────────────────────────────
    check("formato · ranking de dos cuadros (1.7 de 2.7)",
          dt.formato_por_ancho(1.7 / 2.7), dt.FORMATO_RANKING[2])
    check("formato · desglose de dos cuadros (1 de 2.7)",
          dt.formato_por_ancho(1 / 2.7), dt.FORMATO_DETALLE[2])
    check("formato · ranking de tres cuadros (1.2 de 3.2)",
          dt.formato_por_ancho(1.2 / 3.2), dt.FORMATO_RANKING[3])
    check("formato · desglose de tres cuadros (1 de 3.2)",
          dt.formato_por_ancho(1 / 3.2), dt.FORMATO_DETALLE[3])
    filas = mov._FILAS_DETALLE_SAL
    check("seis cuadros en las filas del Detalle (la causa, #614)",
          sum(len(f) for f in filas), 6)
    check("las dos filas cortan la primera columna en el mismo sitio",
          len({round(f[0] / sum(f), 6) for f in filas}), 1)

    # ── 3) Las tarjetas de toda `seccion_cuadros`, en el piso ─────────────
    raiz = pathlib.Path(__file__).parent
    cards = (raiz / "estilos" / "_80_cards.py").read_text(encoding="utf-8")
    llamadas = []
    for py, texto in _fuentes_py(raiz / "graficos"):
        for nodo in ast.walk(ast.parse(texto)):
            if not (isinstance(nodo, ast.Call)
                    and getattr(nodo.func, "attr",
                                getattr(nodo.func, "id", None))
                    == "seccion_cuadros"):
                continue
            kw = {k.arg: k.value for k in nodo.keywords}
            try:
                pref = ast.literal_eval(kw["pref"])
                slug = ast.literal_eval(kw["slug"])
                n = len(kw["niveles"].elts)
            except (KeyError, ValueError, AttributeError):
                fallos += 1
                print(f"FALLA detalle de salidas · {py.name}: una llamada a "
                      "`seccion_cuadros` sin `pref`/`slug` literales ni "
                      "`niveles` en tupla — la guarda no puede leerla")
                continue
            llamadas.append((py.name, pref, slug, n))
    check("hay UNA llamada a seccion_cuadros (la de Movimientos)",
          [(a, p, s, n) for a, p, s, n in llamadas],
          [("movimientos.py", "mov", "detsal", 6)])
    faltan = [k for _a, p, s, n in llamadas
              for k in dt.claves_tarjetas_cuadros(p, s, n)
              if f".st-key-{k}," not in cards and f".st-key-{k})" not in cards]
    check("sus tarjetas están enumeradas en el piso de _80_cards.py",
          faltan, [])

    # ── 4) El rail y la pila ──────────────────────────────────────────────
    ids_rail = [v[0] for _cat, vistas in mov._RAIL_CATEGORIAS for v in vistas]
    ids_pila = [v for _k, v in mov._PILA]
    check("«Detalle de salidas» en el rail y en la pila",
          ("Detalle de salidas" in ids_rail, "Detalle de salidas" in ids_pila),
          (True, True))
    check("«Top productos · salidas» ya no está",
          ("Top productos · salidas" in ids_rail
           or "Top productos · salidas" in ids_pila), False)
    return fallos


def _pruebas_requerimientos_por_area():
    """Movimientos › «Requerimientos por Área» suma lo que «por Período»
    (regla #641).

    Hasta el 2026-10-11 la cadena de tablas sumaba también los anulados:
    S/ 238.884 contra los 238.118 de su vecina en los mismos 30 días. Tres
    cosas que se rompen sin que nada avise:

      1. QUÉ SUMA. El total de `requerimientos_que_suman` tiene que ser el
         de `_validas` de la tarjeta «por Período» para las mismas líneas
         —sin anulados ni líneas sin producto—, y la nota tiene que contar
         los anulados por CÓDIGO, como su fila de KPI.
      2. LA FILA TOTAL. La nota va en el rótulo de la fila TOTAL del primer
         cuadro (`tabla_ranking(nota_total=)`), con el largo de tooltip: en
         el renglón del título, desde el botón de fecha (#617), a 1323px no
         se veía. Se arma con un AgGrid de mentira que guarda lo que recibe.
      3. EL CABLEADO. `_dib_cadena` le pasa a `seccion_cadena` lo que
         devuelve `requerimientos_que_suman`, con su nota; y las dos
         secciones de `drill_tablas` usan la nota SÓLO para la fila TOTAL
         (si vuelve al título, vuelve a quedar fuera de la vista).
    """
    import ast
    import inspect
    import sys
    import textwrap
    import types

    from graficos import drill_tablas as dt
    from graficos import movimientos as mov
    from graficos import movimientos_periodo as mp

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    requerimientos por área · {nombre}")
        else:
            fallos += 1
            print(f"FALLA requerimientos por área · {nombre}: "
                  f"got={got!r} exp={exp!r}")

    # ── 1) Qué suma ───────────────────────────────────────────────────────
    # R1 de Cocina con dos líneas; R2 ANULADO con valor; R3 de GASTOS SIN
    # ÍTEMS (la forma de los 57 de esos 30 días); R4 de Barra; R5 anulado Y
    # sin ítems (cuenta como anulado, una sola vez).
    d = pd.DataFrame({
        "FECHA REGISTRO": pd.to_datetime(
            ["2026-09-12 10:00", "2026-09-12 10:00", "2026-09-13 11:00",
             "2026-09-14 12:00", "2026-09-15 09:00", "2026-09-16 10:00"]),
        "COD REQUERIMIENTO": ["R1", "R1", "R2", "R3", "R4", "R5"],
        "NOMBRE ESTADO REQUERIMIENTO": ["PROCESADO", "PROCESADO", "ANULADO",
                                        "PROCESADO", "GENERADO", " anulado"],
        "SUB ALMACEN": ["COCINA", "COCINA", "PRODUCCION", "GASTOS", "BARRA",
                        "COCINA"],
        "NOMBRE FAMILIA": ["ALIMENTOS", "ALIMENTOS", "ALIMENTOS", None,
                           "BEBIDAS SIN ALCOHOL", None],
        "NOMBRE PRODUCTO": ["A", "B", "C", None, "D", " "],
        "CANTIDAD": [1.0, 2.0, 3.0, None, 4.0, None],
        "VALOR ITEM": [10.0, 20.0, 30.0, None, 40.0, None],
    })
    validas, nota = mov.requerimientos_que_suman(
        d, col_estado="NOMBRE ESTADO REQUERIMIENTO",
        col_prod="NOMBRE PRODUCTO", col_doc="COD REQUERIMIENTO",
        col_val="VALOR ITEM")
    check("suma sin anulados ni líneas sin producto (el generado con ítems "
          "sí suma)", sorted(validas["COD REQUERIMIENTO"]), ["R1", "R1", "R4"])
    bl = mp.lineas_documentos(
        d, fecha="FECHA REGISTRO", doc="COD REQUERIMIENTO", area="SUB ALMACEN",
        estado="NOMBRE ESTADO REQUERIMIENTO", fam="NOMBRE FAMILIA",
        prod="NOMBRE PRODUCTO", cant="CANTIDAD", val="VALOR ITEM")
    check("el total es el de «Requerimientos por Período»",
          float(validas["VALOR ITEM"].sum()),
          float(mp._validas(bl, mp.REQUERIMIENTOS)["valor"].sum()))
    check("cuenta los anulados por código, como la fila de KPI de su vecina",
          nota[0],
          f"sin {mp.REQUERIMIENTOS.anulados(mp.no_suman(bl, mp.REQUERIMIENTOS)[0])}")
    check("el tooltip dice cuánto no suma y nombra a la vecina como el rail",
          ("S/ 30" in nota[1], "«Requerimientos por Período»" in nota[1]),
          (True, True))
    _, _sin_nota = mov.requerimientos_que_suman(
        d[d["COD REQUERIMIENTO"].isin(["R1", "R3"])],
        col_estado="NOMBRE ESTADO REQUERIMIENTO", col_prod="NOMBRE PRODUCTO",
        col_doc="COD REQUERIMIENTO", col_val="VALOR ITEM")
    check("sin anulados en el recorte no hay nota (los sin ítems no se "
          "nombran: valen cero)", _sin_nota, None)

    # ── 2) La fila TOTAL ──────────────────────────────────────────────────
    recibido = {}

    def _aggrid_falso(tabla, gridOptions=None, **kw):
        recibido["opciones"] = gridOptions
        return types.SimpleNamespace(selected_rows=None)

    st_aggrid = sys.modules.get("st_aggrid") or __import__("st_aggrid")
    _original = st_aggrid.AgGrid
    st_aggrid.AgGrid = _aggrid_falso
    try:
        for con_nota in (True, False):
            dt.tabla_ranking(
                validas, "SUB ALMACEN", "VALOR ITEM", "sub almacén",
                key="prueba_rank_641", nota_total=nota if con_nota else None)
            op = recibido["opciones"]
            total = op["pinnedBottomRowData"][0]
            col_nombre = op["columnDefs"][0]
            if con_nota:
                check("con nota, la fila TOTAL la dice",
                      total["Sub almacén"], f"TOTAL · {nota[0]}")
                check("y su tooltip es el largo (la fila lo lleva en `_tip`)",
                      (total.get("_tip"), "tooltipValueGetter" in col_nombre),
                      (nota[1], True))
                check("el TOTAL suma lo que suma la vista",
                      total["Valorizado"], 70.0)
            else:
                check("sin nota, la fila TOTAL y su tooltip como siempre",
                      (total["Sub almacén"], "_tip" in total,
                       col_nombre.get("tooltipField")),
                      ("TOTAL", False, "Sub almacén"))
    finally:
        st_aggrid.AgGrid = _original

    # ── 3) El cableado ────────────────────────────────────────────────────
    arbol = ast.parse(textwrap.dedent(
        inspect.getsource(mov.renderizar_graficos_movimientos)))
    dib = next((n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)
                and n.name == "_dib_cadena"), None)
    asign = [n for n in ast.walk(dib) if isinstance(n, ast.Assign)
             and isinstance(n.value, ast.Call)
             and getattr(n.value.func, "id", None) == "requerimientos_que_suman"]
    llamadas = [n for n in ast.walk(dib) if isinstance(n, ast.Call)
                and getattr(n.func, "attr", None) == "seccion_cadena"]
    nombres = ([e.id for e in asign[0].targets[0].elts]
               if asign and isinstance(asign[0].targets[0], ast.Tuple) else [])
    if len(nombres) == 2 and len(llamadas) == 1:
        _c = llamadas[0]
        _kw = {k.arg: k.value for k in _c.keywords}
        check("`_dib_cadena` le pasa a la cadena lo que suma y su nota",
              (getattr(_c.args[0], "id", None),
               getattr(_kw.get("nota"), "id", None)), tuple(nombres))
    else:
        fallos += 1
        print("FALLA requerimientos por área · `_dib_cadena` no arma "
              "`validas, nota = requerimientos_que_suman(...)` ni llama una "
              "vez a `seccion_cadena`")

    fuente_dt = ast.parse(inspect.getsource(dt))
    for fn in ("seccion_cadena", "seccion_cuadros"):
        nodo = next(n for n in fuente_dt.body
                    if isinstance(n, ast.FunctionDef) and n.name == fn)
        usos = [n for n in ast.walk(nodo) if isinstance(n, ast.Name)
                and n.id == "nota" and isinstance(n.ctx, ast.Load)]
        al_total = [k for n in ast.walk(nodo) if isinstance(n, ast.Call)
                    and getattr(n.func, "id", None) == "tabla_ranking"
                    for k in n.keywords if k.arg == "nota_total"
                    and getattr(k.value, "id", None) == "nota"]
        check(f"`{fn}` usa la nota sólo para la fila TOTAL",
              (len(al_total), len(usos)), (1, 1))
    return fallos


def _pruebas_ventas_un_item_una_vez():
    """Ventas › un ítem se cuenta una vez (regla #517).

    `ventas.parquet` trae una fila por ítem Y POR FORMA DE PAGO. Fija dos
    cosas: que `unico_por_item` se quede con una fila por llave sin tocar
    las filas SIN llave, y que el dispatcher se la aplique a todo lo que
    suma venta — incluidos los df que Año Pasado y Mapa por hora traen
    aparte de R2 por `filtrar_cb` — mientras Meseros sigue recibiendo las
    filas por pago, que es de donde sale la propina.
    """
    import ast
    import inspect
    import textwrap

    from graficos import ventas as _v

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · un ítem una vez · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · un ítem una vez · {nombre}: "
                  f"got={got!r} exp={exp!r}")

    # A pagado con dos formas (dos filas con su venta ENTERA), B con una,
    # y dos filas sin llave, que no son "la misma" por no tenerla.
    d = pd.DataFrame({
        "LLAVE LOCAL DOCUMENTO ITEM": ["A", "A", "B", None, None],
        "CORRELATIVO PAGO": ["1", "2", "1", None, None],
        "VENTA ITEM DDOCUMENTO": [50.0, 50.0, 30.0, 7.0, 3.0],
    })
    u = _v.unico_por_item(d)
    check("filas: A una vez, B, y las dos sin llave", len(u), 4)
    check("venta 50 + 30 + 7 + 3", float(u["VENTA ITEM DDOCUMENTO"].sum()),
          90.0)
    check("no toca el df de entrada", len(d), 5)
    sin_llave = d.drop(columns=["LLAVE LOCAL DOCUMENTO ITEM"])
    check("sin la columna devuelve el mismo df",
          _v.unico_por_item(sin_llave) is sin_llave, True)
    check("resuelve el nombre sin importar mayúsculas",
          len(_v.unico_por_item(d.rename(columns={
              "LLAVE LOCAL DOCUMENTO ITEM": "Llave Local Documento Item"}))),
          4)

    # ── El cableado del dispatcher, leído del código ──────────────────────
    fuente = textwrap.dedent(inspect.getsource(_v.renderizar_graficos_ventas))
    arbol = ast.parse(fuente)
    asignaciones = {
        n.targets[0].id: ast.unparse(n.value) for n in ast.walk(arbol)
        if isinstance(n, ast.Assign) and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)}
    # Desde la regla #524 hay un paso más: `d` es SÓLO venta (sin cortesías
    # ni anulados) sobre `d_todo`, que es el df post-chips un ítem una vez.
    # Lo de la definición lo vigila `test_definicion_venta.py`.
    check("`d_todo` es el df post-chips con un ítem una vez",
          asignaciones.get("d_todo"), "unico_por_item(d_pagos)")
    check("`d` es sólo la venta de `d_todo`",
          asignaciones.get("d"), "dv.solo_venta(d_todo)")
    llamadas = {}
    for n in ast.walk(arbol):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            llamadas.setdefault(n.func.id, []).append(n)
    for vista in ("_ventas_comparativo", "_ventas_horario"):
        kws = {k.arg: ast.unparse(k.value)
               for c in llamadas.get(vista, []) for k in c.keywords}
        check(f"{vista} recarga con filtrar_cb=_filtrar_items",
              kws.get("filtrar_cb"), "_filtrar_items")
    mes = llamadas.get("_ventas_meseros", [])
    check("Meseros recibe las filas POR PAGO (la propina es del pago)",
          [ast.unparse(c.args[0]) for c in mes], ["d_pagos"])
    kws = {k.arg: ast.unparse(k.value) for c in mes for k in c.keywords}
    check("Meseros trae lo de R2 sólo con los chips (los granos los arma)",
          kws.get("filtrar_cb"), "_aplicar_chips")
    return fallos


def _pruebas_ventas_mix():
    """Ventas › Mix de carta (regla #527): las cuentas de la vista.

    Fija lo que no se ve en pantalla hasta que miente: que la matriz salga
    con las columnas por NOMBRE —el período, no la posición (regla #481,
    pandas 2 contra pandas 3)—, que los chicos se junten en «Resto (N)» y
    no en «Otros» (en `ventas.parquet` hay un Grupo que se llama así), que
    el año pasado mire los MISMOS días, y que el dispatcher le pase
    `_filtrar_items`: sin él, el año pasado se sumaría sin los chips de la
    franja y con cortesías y anulados.
    """
    import ast
    import inspect
    import pathlib
    import re
    import textwrap
    from datetime import date

    from graficos import ventas as _v
    from graficos import ventas_mix as _m
    from graficos.compras._comun import _periodo_serie
    from tema import PALETA_SERIES

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · mix · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · mix · {nombre}: got={got!r} exp={exp!r}")

    # Lunes 3 y martes 4 de agosto (semana 32), martes 11 y miércoles 12
    # (semana 33); una fila sin grupo.
    d = pd.DataFrame({
        "FEC REG DOCUMENTO": pd.to_datetime(
            ["2026-08-03", "2026-08-04", "2026-08-11", "2026-08-12",
             "2026-08-12"]),
        "GRUPO": ["Alimentos", "Alimentos", "Bebidas", None, "Alimentos"],
        "SUB GRUPO": ["Fondos", "Entradas", "Cocteles", None, "Fondos"],
        "NOMB ITEM VENTA": ["Lomo", "Ceviche", "Pisco Sour", "Agua", "Lomo"],
        "VENTA ITEM DDOCUMENTO": [100.0, 40.0, 30.0, 5.0, 60.0],
        "CANTIDAD ITEM DDOCUMENTO": [2, 1, 3, 1, 1],
        "COSTO VENTA": [35.0, 12.0, 9.0, 1.0, 21.0],
        "NETO TOTAL ITEM DDOCUMENTO": [81.0, 32.4, 24.3, 4.05, 48.6],
        # El IGV de la línea marca el período en que cambió la tasa (#590).
        "IGV ITEM DDOCUMENTO": [8.1, 3.24, 2.43, 0.405, 4.86],
        # Dónde se prepara (#595): como lo escribe el POS, con un vacío.
        "AREA PRODUCCION": ["COCINA", "PASTELERIA", "BAR", None, "COCINA"],
    })
    cols = _m.columnas(d)
    check("resuelve las diez columnas", all(cols.values()), True)
    b = _m.base(d, cols)
    check("y la base trae el IGV", round(float(b["igv"].sum()), 3), 19.035)
    check("sin la columna del IGV, la base sigue (en cero)",
          float(_m.base(d, {k: v for k, v in cols.items() if k != "igv"})
                ["igv"].sum()), 0.0)
    check("un grupo vacío se nombra, no se cae",
          sorted(b["grupo"].unique()), ["(sin grupo)", "Alimentos", "Bebidas"])
    b = b.assign(clave=_periodo_serie(b["fecha"], "Semana"))
    claves = sorted(b["clave"].unique())
    check("una clave por semana ISO", claves, ["2026-S32", "2026-S33"])
    M = _m.matriz(b, "grupo", claves)
    check("las cuatro medidas", sorted(M), ["cant", "costo", "neto", "venta"])
    check("las columnas son los períodos, por nombre",
          list(M["venta"].columns), claves)
    check("Alimentos por semana", M["venta"].loc["Alimentos"].tolist(),
          [140.0, 60.0])
    check("una semana sin venta es cero, no NaN",
          M["venta"].loc["Bebidas"].tolist(), [0.0, 30.0])

    # ── El % de costo por período (regla #544) ────────────────────────────
    pc = _m.pct_costo(M["costo"], M["neto"])
    check("% costo por período: costo ÷ NETO, no ÷ venta (47 / 113,4)",
          round(float(pc.loc["Alimentos", "2026-S32"]), 4),
          round(47.0 / 113.4, 4))
    check("las columnas siguen siendo los períodos, por nombre",
          list(pc.columns), claves)
    check("un período sin venta es «—» (NaN), no 0 %",
          bool(pd.isna(pc.loc["Bebidas", "2026-S32"])), True)
    check("sin costo cargado es NaN, no 0 % (regla #524)",
          bool(pd.isna(_m.pct_costo(pd.Series([0.0]), pd.Series([80.0]))[0])),
          True)
    check("con el neto en negativo no hay cociente",
          bool(pd.isna(_m.pct_costo(pd.Series([10.0]), pd.Series([-50.0]))[0])),
          True)
    # La «Chirimoya a la Brasa - Cortesia» real: 115 unidades a S/ 0 con
    # S/ 1.023 de costo y un neto de S/ 0,0082 de puro redondeo (#547).
    check("una cortesía a S/ 0 no es un % de costo de 12 millones",
          (bool(pd.isna(_m.pct_costo(pd.Series([1023.35]),
                                     pd.Series([0.0082]))[0])),
           bool(pd.isna(_m.pct_costo(1023.35, 0.0082)))), (True, True))
    check("y con números sueltos, lo mismo",
          (_m.pct_costo(47.0, 113.4) == 47.0 / 113.4,
           bool(pd.isna(_m.pct_costo(0.0, 113.4)))), (True, True))
    from graficos import ventas_resumen as _r
    check("los umbrales de color SON los del Resumen, no una copia",
          (_m._COSTO_ALTO is _r._COSTO_ALTO, _m._COSTO_ROTO is _r._COSTO_ROTO),
          (True, True))
    check("debajo del umbral, sin color; encima, ámbar; muy encima, rojo",
          [bool(_m._estilo_costo(v)) for v in
           (_r._COSTO_ALTO - 0.01, _r._COSTO_ALTO + 0.01)]
          + ["700" in _m._estilo_costo(_r._COSTO_ROTO + 0.01),
             _m._estilo_costo(float("nan")) == ""],
          [False, True, True, True])
    check("un NaN en la tendencia se salta: ni cero ni None (la línea no "
          "tiene huecos)", _m._serie([0.4, float("nan"), 0.5]), [0.4, 0.5])
    check("el control de las celdas sobrevive a la recarga de fecha",
          "vt_mix_celdas" in _m._KEYS_WIDGET_MIX, True)

    check("alcance de un subgrupo",
          float(_m.alcance(b, ("Alimentos", "Fondos"))["venta"].sum()), 160.0)

    # ── El árbol por área de producción (regla #595) ──────────────────────
    ba = _m.base(d, cols, _m._EJE_AREA)
    check("por Área, el primer nivel es el área, con nombre de carta",
          sorted(ba["grupo"].unique()),
          ["Bar", "Cocina", "Pastelería", "Sin área"])
    check("y el segundo, el subgrupo de la carta",
          sorted(ba.loc[ba["grupo"] == "Cocina", "sub"].unique()),
          ["Fondos"])
    check("las mismas filas y la misma venta que por Carta",
          (len(ba), float(ba["venta"].sum())),
          (len(b), float(b["venta"].sum())))
    check("el alcance baja por área y subgrupo",
          float(_m.alcance(ba, ("Cocina", "Fondos"))["venta"].sum()),
          160.0)
    check("un área no es una ruta de la Carta: vuelve arriba",
          _m.ruta_valida(b, ("Cocina",)), ())
    check("las migas y la tabla nombran los niveles del árbol",
          _m._NOMBRES_EJE[_m._EJE_AREA][0],
          ("Áreas", "Subgrupos", "Productos"))
    check("sin la columna del área, todo cae en «Sin área»",
          set(_m.base(d, {k: v for k, v in cols.items() if k != "area"},
                      _m._EJE_AREA)["grupo"]), {"Sin área"})
    check("el selector sobrevive a la recarga de fecha",
          "vt_mix_eje" in _m._KEYS_WIDGET_MIX, True)
    check("un grupo que ya no está vuelve arriba",
          _m.ruta_valida(b, ("Vinos",)), ())
    check("un subgrupo de otro grupo sube uno",
          _m.ruta_valida(b, ("Alimentos", "Cocteles")), ("Alimentos",))
    check("una ruta que existe queda",
          _m.ruta_valida(b, ("Bebidas", "Cocteles")), ("Bebidas", "Cocteles"))

    orden = [f"g{i}" for i in range(10)]
    tr = _m.tramos(orden)
    check("diez: siete con nombre y «Resto (3)»",
          [t[0] for t in tr], orden[:7] + ["Resto (3)"])
    check("el resto junta a los tres de abajo", tr[-1][1], orden[7:])
    check("ocho: los ocho, sin un «Resto (1)»",
          [t[0] for t in _m.tramos(orden[:8])], orden[:8])
    check("con foco: el producto contra el resto de su subgrupo",
          [(t[0], t[1]) for t in _m.tramos(["a", "b", "c"], "b", "Fondos")],
          [("b", ["b"]), ("Resto de Fondos", ["a", "c"])])

    check("mes en curso: los mismos días, un año antes",
          _m.rango_ano_pasado("2026-09", "Mes",
                              (date(2026, 8, 1), date(2026, 9, 23))),
          (date(2025, 9, 1), date(2025, 9, 23)))
    check("semana: 364 días, el mismo día de la semana",
          _m.rango_ano_pasado("2026-S33", "Semana", None),
          (date(2025, 8, 11), date(2025, 8, 17)))
    check("el 29 de febrero cae al 28",
          _m.rango_ano_pasado("2028-02", "Mes", None)[1], date(2027, 2, 28))

    # ── El cableado del dispatcher ────────────────────────────────────────
    fuente = textwrap.dedent(inspect.getsource(_v.renderizar_graficos_ventas))
    llamadas = [n for n in ast.walk(ast.parse(fuente))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_ventas_mix"]
    check("el dispatcher llama al Mix una vez", len(llamadas), 1)
    for c in llamadas:
        check("con `d`: sólo venta, un ítem una vez",
              [ast.unparse(a) for a in c.args], ["d"])
        check("y el año pasado filtrado igual (filtrar_cb=_filtrar_items)",
              {k.arg: ast.unparse(k.value) for k in c.keywords}.get(
                  "filtrar_cb"), "_filtrar_items")
    vistas = [v for _cat, vs in _v._VENTAS_RAIL_CATEGORIAS for v, *_ in vs]
    check("las vistas que reemplazó el Mix no vuelven (#527, #541, #543)",
          [n for n in ("Venta por día", "Familia/Subfamilia semanal",
                       "Histórica subfamilia", "Matriz agrupada")
           if n in vistas or n in dict(_v._PILA).values()], [])
    check("«Mix de carta» está en el rail y en la pila",
          ("Mix de carta" in vistas, "Mix de carta" in dict(_v._PILA).values()),
          (True, True))

    # ── El espejo CSS de los colores de los tramos ────────────────────────
    base_css = (pathlib.Path(__file__).parent / "estilos" / "_00_base.py"
                ).read_text(encoding="utf-8")
    espejo = [re.search(rf"--serie-{i}:\s*(#[0-9a-fA-F]{{6}})", base_css)
              for i in range(len(_m._COLORES))]
    check("--serie-<i> es PALETA_SERIES[i] para cada tramo con color",
          [x.group(1).lower() if x else None for x in espejo],
          [c.lower() for c in PALETA_SERIES[:len(_m._COLORES)]])
    return fallos


def _pruebas_revisar_recetas():
    """Recetas › Revisar recetas (regla #559): los cortes que se porcionan y
    ninguna receta usa, y los que las recetas piden y casi no se porcionan.

    Fija los casos reales del 2026-09-28: el PAR del lomo (el medallón que
    las recetas piden de más y los trozos que ninguna receta usa) en el mismo
    grupo; el código viejo que se dejó de porcionar; la charela de 125 g
    que sale de la de 250 g y queda con su gemela bajo la charela ENTERA
    (la cadena se para en lo que se compra, y un círculo no la cuelga); la
    comida del personal, que no es un tema de receta; y las seis cosas que
    NO son una señal: lo que usa una receta base activa, lo que parte a otro
    porcionamiento, un directo de la carta, una venta (propiedades), un corte
    con receta base activa (se produce por orden de producción) y lo que se
    compra directo. Y que las cuatro vistas que se fueron no vuelvan.
    """
    from datetime import date, timedelta

    from graficos import recetas as rec
    from graficos import recetas_revisar as rr

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    recetas · revisar · {nombre}")
        else:
            fallos += 1
            print(f"FALLA recetas · revisar · {nombre}: got={got!r} exp={exp!r}")

    fin = date(2026, 9, 27)
    ini = fin - timedelta(days=29)

    def dia(n):
        return pd.Timestamp(fin - timedelta(days=n))

    maestro = pd.DataFrame([
        # cod, nombre, unidad, factor, precio
        ("0000287", "Lomo fino entero x Kg", "KILOS", 1000.0, 73.0),
        ("0004159", "(P) Lomo Medallon 170gr", "UND", 1.0, 15.0),
        ("0004160", "(P) Lomo trozos saltado 170gr", "UND", 1.0, 14.0),
        ("0004001", "(P) Lomo trozos saltado 180gr", "UND", 1.0, 16.0),
        ("0001997", "Charela entera x Kg", "KILOS", 1000.0, 55.0),
        ("0003920", "(P) Charela limpio 250gr", "UND", 1.0, 30.0),
        ("0004076", "(P) Charela limpio 125gr", "UND", 1.0, 15.0),
        ("0003902", "(Rs) Collar / Charela 125gr", "UND", 1.0, 15.0),
        ("0000100", "Pollo entero x Kg", "KILOS", 1000.0, 11.0),
        ("0000883", "Pollo Familia x Kg", "KILOS", 1000.0, 11.0),
        ("0000900", "(P) Cebolla limpia", "KILOS", 1000.0, 4.0),
        ("0000950", "(P) Pulpo cocido", "KILOS", 1000.0, 90.0),
        ("0000951", "(P) Pulpo cocido 120gr", "UND", 1.0, 11.0),
        ("0000960", "(P) Entraña 300gr", "UND", 1.0, 60.0),
        ("0000970", "(Rs) Salsa de la casa", "KILOS", 1000.0, 20.0),
        ("0000980", "Lechuga Morada", "KILOS", 1000.0, 8.0),
        ("0000990", "(P) Palta limpia", "KILOS", 1000.0, 16.0),
        ("0005001", "(P) Corte A", "UND", 1.0, 5.0),
        ("0005002", "(P) Corte B", "UND", 1.0, 5.0),
    ], columns=["CODIGO PRODUCTO", "NOMBRE PRODUCTO", "UNIDAD KARDEX", "FACTOR",
                "PRECIO PROMEDIO"])
    nom = dict(zip(maestro["CODIGO PRODUCTO"], maestro["NOMBRE PRODUCTO"]))

    def porc(n, inic, final, cant, precio, fecha):
        return {"COD PORC": n, "COD PROD INIC": inic, "PROD INICIAL": nom[inic],
                "FEC REGIST": fecha, "COD PROD FINAL": final,
                "PROD FINAL RESULT": nom[final], "CANT RESULT": cant,
                "UNID PROD FIN": "UND", "PREC PROM PROD FIN": precio}

    porcionamientos = pd.DataFrame([
        porc("P1", "0000287", "0004159", 179, 15.0, dia(3)),
        porc("P1", "0000287", "0004160", 262, 14.0, dia(3)),
        porc("P2", "0000287", "0004001", 78, 16.0, dia(27)),       # ya no se porciona
        porc("P0", "0004159", "0000287", 1.0, 73.0, dia(200)),     # al revés
        porc("P3", "0001997", "0003920", 10, 30.0, dia(120)),      # antes del período
        porc("P4", "0003920", "0004076", 20, 15.0, dia(96)),       # cadena 250 → 125
        porc("P5", "0001997", "0003902", 13, 15.0, dia(5)),
        porc("P6", "0000100", "0000883", 19.1, 11.0, dia(16)),
        porc("P7", "0000287", "0000900", 4.0, 4.0, dia(4)),        # lo usa una receta base
        porc("P8", "0000287", "0000950", 3.0, 90.0, dia(6)),       # parte a otro porcionamiento
        porc("P9", "0000950", "0000951", 20, 11.0, dia(5)),
        porc("P10", "0000287", "0000960", 5, 60.0, dia(6)),        # un directo de la carta
        porc("P11", "0000287", "0000970", 1.0, 20.0, dia(300)),    # tiene receta base activa
        porc("P12", "0000287", "0000980", 1.0, 8.0, dia(200)),     # hoy se compra
        porc("P13", "0000287", "0000990", 8.0, 16.0, dia(4)),      # lo pide una venta
        porc("P14", "0005002", "0005001", 2, 5.0, dia(2)),         # círculo A ← B ← A
        porc("P15", "0005001", "0005002", 2, 5.0, dia(40)),
    ])
    n1 = pd.DataFrame([
        ("0004159", "Lomo Saltado", 400.0, 6000.0),
        ("0004159", "Lomo a la Pimienta", 194.0, 2910.0),
        ("0004076", "(Ex) Collar de Pesca", 35.0, 525.0),
        ("0000970", "Tallarín de la casa", 100000.0, 2000.0),
        ("0000980", "Lomo al Trapo", 3050.0, 24.4),
        ("0000990", "Propiedad: con palta", 10000.0, 160.0),
        ("0000951", "Pulpo a la Leña", 20.0, 220.0),
    ], columns=["cod", "plato", "consumo", "costo"])
    recetaventa = pd.DataFrame({
        "COD INS": ["0004159", "0004076", "0004160"],
        "ITEM VENTA ACTIVO": ["ACTIV", "ACTIV", "INACTIV"],   # los trozos, en un plato de baja
        "INS ACTIVO": ["ACTIV", "ACTIV", "ACTIV"],
    })
    recetabase = pd.DataFrame({
        "COD PROD RB": ["0000970", "0000999"],
        "COD INS RB": ["0000900", "0003902"],
        "RB ACT": ["RB.ACTIV", "RB.INACT"],                   # el collar, en una receta de baja
        "INS ACTIVO": ["INS.ACT", "INS.ACT"],
    })
    carta = pd.DataFrame({
        "TIPO DESC": ["DIRECTO", "DIRECTO"],
        "ITEM VENT ACT": ["ACTIV", "INACT"],                  # los trozos, en un directo de baja
        "COD ITEM O RECETA": ["0000960", "0004160"],
    })
    salidas = pd.DataFrame({
        "COD PRODUCTO": ["0000883", "0004160", "0003902"],
        "TIPO DESCARGO": ["Comida Personal", "Bajas", "Bajas"],
        "CANT SALIDA": [46.6, 3.0, 13.0],
        "FECHA REGISTRO": [dia(2), dia(1), dia(1)],
        "NOMBRE ESTADO SALIDA": ["PROCESADO", "PROCESADO", "ANULADO"],
    })
    compras = pd.DataFrame({
        "COD_PRODUCTO": ["0000980", "0000287", "0001997", "0000100"],
        "CANTIDAD_COMPRA": [5.0, 200.0, 30.0, 40.0],
        "FECHA_EMISION_DOC": [dia(8), dia(10), dia(60), dia(20)],
    })

    t = rr.revisar(porcionamientos, n1, recetaventa, recetabase, carta, maestro,
                   salidas, ini, fin, compras=compras)
    que = dict(zip(t["cod"], t["que"]))
    check("las filas: el par del lomo, el código viejo, el par de la charela y la familia",
          sorted(que), sorted(["0004159", "0004160", "0004001", "0003902", "0004076",
                               "0000883", "0005001"]))
    check("el medallón: las ventas piden más de lo que se porciona",
          que.get("0004159"), rr.QUE_FALTA)
    check("los trozos: ninguna receta los usa (un plato y un directo de baja no cuentan)",
          que.get("0004160"), rr.QUE_SIN)
    check("el de 180 g se dejó de porcionar", que.get("0004001"), rr.QUE_SIN_VIEJO)
    check("el collar: una receta base DE BAJA no cuenta, ni una salida anulada",
          que.get("0003902"), rr.QUE_SIN)
    check("la charela de 125 g no se porcionó en el período",
          que.get("0004076"), rr.QUE_FALTA)
    check("la familia sale por notas de salida", que.get("0000883"), rr.QUE_SALIDA)

    g = dict(zip(t["cod"], t["grupo_cod"]))
    check("el par del lomo, en el grupo del lomo (el porcionamiento al revés no lo cuelga)",
          (g["0004159"], g["0004160"], g["0004001"]), ("0000287",) * 3)
    check("la charela de 125 g sale de la de 250 g, que sale de la entera: juntas",
          (g["0004076"], g["0003902"]), ("0001997", "0001997"))
    check("el grupo del lomo va primero, y adentro la señal antes que el código viejo",
          list(t["cod"])[:3], ["0004159", "0004160", "0004001"])
    check("la familia va al final: no pesa en el orden", list(t["cod"])[-1], "0000883")
    f = t.set_index("cod")
    check("lo pedido va en unidad de ENTRADA y se compara contra lo porcionado",
          (f.loc["0004159", "pedido"], f.loc["0004159", "porcionado"]), (594.0, 179.0))
    check("el valor de lo que faltó: al precio de hoy",
          round(f.loc["0004159", "valor"], 2), round((594 - 179) * 15.0, 2))
    check("el valor de lo porcionado sin receta: al costo del porcionamiento",
          round(f.loc["0004160", "valor"], 2), round(262 * 14.0, 2))
    check("los platos que lo piden, de más a menos",
          f.loc["0004159", "platos"], ["Lomo Saltado", "Lomo a la Pimienta"])
    check("por dónde salió", f.loc["0004160", "salio"], {"Bajas": 3.0})
    check("un círculo de porcionamientos (A ← B ← A) no cuelga la búsqueda: queda en B",
          g["0005001"], "0005002")

    v = rr.tabla(t, fin).set_index("Corte")
    check("una cantidad entera, sin decimales",
          v.loc["(P) Lomo trozos saltado 170gr", "Porcionado"], "262 und")
    check("lo que no se pide se escribe «—»",
          v.loc["(P) Lomo trozos saltado 170gr", "Piden las ventas"], "—")
    check("la fecha del último porcionamiento",
          v.loc["(P) Lomo trozos saltado 180gr", "Último porc."], "31 ago")
    check("la del último porcionamiento de la charela de 125 g",
          v.loc["(P) Charela limpio 125gr", "Último porc."], "23 jun")
    check("cada columna de la tabla tiene su ancho (sin anchos sumaban 1.585 px)",
          sorted(rr.tabla(t, fin).columns), sorted(rr.COLUMNAS_TABLA))
    check("sin vacíos que st.dataframe pinte «None» (#529)",
          bool(rr.tabla(t, fin).isna().any().any()), False)
    txt = rr.resumen(t, ini, fin)
    check("el resumen cuenta cada señal",
          ("**3** cortes se porcionan y ninguna receta los usa" in txt,
           "**2** cortes los piden las recetas" in txt,
           "Otro se dejó de porcionar" in txt,
           "Uno más sale por notas de salida" in txt),
          (True, True, True, True))
    vacio = rr.revisar(porcionamientos.iloc[:0], n1.iloc[:0], recetaventa, recetabase,
                       carta, maestro, salidas, ini, fin)
    check("sin nada para revisar, lo dice",
          rr.resumen(vacio, ini, fin).endswith("nada para revisar."), True)

    # ── En el rail y en la pila; y las cuatro que se fueron, fuera ───────
    _vistas = {v[0] for _cat, vistas in rec._RAIL_CATEGORIAS for v in vistas}
    check("Revisar recetas está en el rail y en la pila",
          ("Revisar recetas" in _vistas, ("rec_sec_revisar", "Revisar recetas") in rec._PILA),
          (True, True))
    for ida in ("Ingredientes clave", "Insumos clave · recetas base",
                "Panorama de compras · platos", "Panorama de compras · recetas base"):
        check(f"«{ida}» ya no es una vista (#559)",
              ida in _vistas or any(v == ida for _k, v in rec._PILA), False)
    return fallos


def _pruebas_costo_recetas_base():
    """Recetas › «Costo Recetas Base» (regla #576), que reemplazó al Ranking
    de recetas base: lo que usaron las ventas de cada receta base —también
    adentro de otra— contra lo que produjeron las órdenes de producción, y su
    costo por unidad en el tiempo.

    Fija lo que se ve mal sin avisar: una receta que sólo llega al plato
    ADENTRO de otra (sin bajar, decía «sin uso»); un plato que la lleva por
    dos caminos cuenta una vez; una orden GENERADA no produjo nada; una orden
    con un costo absurdo no entra en el último costo, y un cambio de régimen
    no es absurdo; sin vacíos que `st.dataframe` pinte «None» (#529). Y el
    orden y los nombres del rail que se pidieron.
    """
    import math
    from datetime import date

    import consumo_recetas
    from data import REPORTES
    from graficos import recetas as rec
    from graficos import recetas_base_costo as rbc

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    recetas · costo recetas base · {nombre}")
        else:
            fallos += 1
            print(f"FALLA recetas · costo recetas base · {nombre}: got={got!r} exp={exp!r}")

    rb = _recetabase_rb_demo()
    op = _ordenes_rb_demo()
    n1 = pd.DataFrame({
        "cod": ["0000100", "0000100", "0000200", "0000300", "0000900"],
        "plato": ["Lomo a la pimienta", "Pasta", "Lomo a la pimienta", "Postre", "Lomo a la pimienta"],
        "consumo": [2000.0, 1000.0, 500.0, 4.0, 100.0],
        "costo": [40.0, 20.0, 2.5, 12.0, 1.0],
        "vendido": [10.0, 5.0, 10.0, 4.0, 10.0],
    })

    u = rbc.uso(n1, rb)
    check("lo usado de la salsa, en kilos (2000 g + 1000 g)", round(u.loc["0000100", "usado"], 6), 3.0)
    check("el fondo: 0,5 kg directo + 3 kg de salsa × 0,3", round(u.loc["0000200", "usado"], 6), 1.4)
    check("y su parte directa, aparte", round(u.loc["0000200", "directo"], 6), 0.5)
    check("un plato que lleva el fondo por dos caminos cuenta una vez",
          (int(u.loc["0000200", "platos"]), u.loc["0000200", "vendidos"]), (2, 15.0))
    check("un insumo de compra no es una receta base", "0000900" in u.index, False)

    o = rbc.ordenes(op)
    check("una orden generada no produjo nada", "GENERADO" in set(op["NOMBRE ESTADO"])
          and len(o) == int((op["NOMBRE ESTADO"] == "PROCESADO").sum()), True)
    raras = set(o.loc[o["atipico"], "orden"])
    check("S/ 3.000 el kilo y S/ 0 son atípicas", raras, {"2600000020", "2600000021"})
    check("un cambio de régimen (de S/ 5 a S/ 25) no es atípico",
          bool(o.loc[o["cod"] == "0000200", "atipico"].any()), False)

    ini, fin = pd.Timestamp("2026-07-01"), pd.Timestamp("2026-09-29")
    t = rbc.tabla(rb, n1, o, ini, fin).set_index("cod")
    check("el último costo salta las atípicas", round(t.loc["0000100", "ultimo"], 6), 20.8)
    # Julio a setiembre: tres órdenes normales de 2 kg y las dos atípicas,
    # que SÍ cuentan como producción —la orden existió—; sólo quedan fuera
    # del costo.
    check("órdenes y producido del período, con las atípicas",
          (int(t.loc["0000100", "ordenes"]), round(t.loc["0000100", "producido"], 6)),
          (5, 7.01))
    check("producido ÷ usado", round(t.loc["0000100", "cobertura"], 4), round(7.01 / 3.0, 4))
    check("sin uso, producido ÷ usado queda en infinito (se escribe «—»)",
          (math.isinf(t.loc["0000400", "cobertura"]), rbc._pct(t.loc["0000400", "cobertura"])),
          (True, "—"))
    check("una inactiva que se vendió está, y una activa sin nada también",
          ("0000300" in t.index, "0000400" in t.index), (True, True))
    check("usada y nunca producida por una orden: «—», no un 0 % (se hace de otra forma)",
          rbc._pct(t.loc["0000300", "cobertura"]), "—")
    check("filtro: con órdenes / sin órdenes",
          (sorted(rbc.filtrar(t.reset_index(), produccion=rbc.PRODUCCION[1])["cod"]),
           sorted(rbc.filtrar(t.reset_index(), produccion=rbc.PRODUCCION[2])["cod"])),
          (["0000100", "0000200"], ["0000300", "0000400"]))
    check("una línea de 12 meses con menos de dos meses no se dibuja",
          t.loc["0000400", "linea"], [])
    check("una suba marcada en ámbar y una baja en verde",
          (rbc.ADVERTENCIA_TEXTO in rbc._estilo_var(0.25),
           rbc.AJUSTE_POS_TEXTO in rbc._estilo_var(-0.25), rbc._estilo_var(0.1)),
          (True, True, ""))
    check("el fondo: de S/ 5 a S/ 25 en la línea de 12 meses",
          round(t.loc["0000200", "var"], 6), 4.0)
    v = rbc.columnas_tabla(t.reset_index())
    check("las columnas de la tabla", tuple(v.columns), rbc.COLUMNAS)
    check("sin vacíos que st.dataframe pinte «None» (#529)",
          bool(v.drop(columns=["Costo 12 m"]).isna().any().any()), False)
    check("la inactiva lo dice", "(Rs) Postre viejo · inactiva" in set(v["Receta base"]), True)
    check("ordenada por lo vendido, a igual venta por órdenes",
          list(rbc.tabla(rb, n1, o, ini, fin)["cod"])[:2], ["0000100", "0000200"])
    check("filtro por área", list(rbc.filtrar(t.reset_index(), "BARRA")["cod"]), ["0000400"])
    check("buscar sin acentos ni mayúsculas",
          list(rbc.filtrar(t.reset_index(), buscar="FONDO")["cod"]), ["0000200"])
    check("el área se escribe con su tilde", rbc.area_escrita("PRODUCCION"), "Producción")
    sin_ventas = rbc.tabla(rb, None, o, ini, fin)
    check("sin el primer nivel de las ventas, la tabla sale igual",
          (len(sin_ventas) > 0, float(sin_ventas["usado"].sum())), (True, 0.0))
    fig = rbc.fig_evolucion(o[o["cod"] == "0000100"], rbc.costo_por_mes(o[o["cod"] == "0000100"]),
                            20.0, "KILOS")
    check("la orden de S/ 3.000 no estira la escala", fig.layout.yaxis.range[1] < 100, True)
    check("los meses del eje en español (#241)",
          any(txt.startswith("ene") for txt in fig.layout.xaxis.ticktext), True)
    # ── La tarjeta de abajo: la receta y las de adentro ──────────────────
    bases = rbc.codigos_base(rb)
    ing = rbc.ingredientes(rb.assign(UNID="GRAMOS"), "0000100", 1.0, bases).set_index("Cod")
    check("los ingredientes de la salsa, en la unidad de la receta",
          (round(ing.loc["0000200", "Cantidad"], 6), ing.loc["0000200", "Unid"]), (300.0, "g"))
    check("el fondo, que es receta base, se marca; el insumo de compra no",
          (bool(ing.loc["0000200", "EsBase"]), bool(ing.loc["0000900", "EsBase"])), (True, False))
    # La receta de adentro se abre por UNA unidad de producción SUYA (pedido
    # el 2026-09-30: antes salía proporcionada a lo que llevaba la de afuera).
    filas = rbc._filas_clic(rbc.ingredientes(rb, "0000100", 1.0, bases))
    fondo = next(f for f in filas if f["cod"] == "0000200")
    check("la receta de adentro, por 1 unidad suya (1 kg de fondo)",
          (fondo["es_base"], rbc.unidad_de(rb, fondo["cod"]),
           round(float(rbc.ingredientes(rb, "0000200", 1.0, bases)["Cantidad"].iloc[0]), 6)),
          (True, "kg", 1000.0))
    # Pedido el 2026-09-30: el costo de la unidad de COMPRA y el de la
    # cantidad de la receta, los dos, y el total al pie.
    rb_u = rb.assign(UNID="GRAMOS", **{"CST UNIT INS": 0.003, "CST SUBT INS": rb["CANT"] * 0.003})
    ing_u = rbc.ingredientes(rb_u, "0000100", 1.0, bases).set_index("Cod")
    check("el costo unitario va por kilo (S/ 0,003 el gramo = S/ 3 el kilo)",
          (round(ing_u.loc["0000200", "CostoUnit"], 6), ing_u.loc["0000200", "UnidCompra"]),
          (3.0, "kg"))
    check("y el costo de la cantidad de la receta (300 g = S/ 0,90)",
          round(ing_u.loc["0000200", "Costo"], 6), 0.9)
    r_u = rbc.ingredientes(rb_u, "0000100", 1.0, bases)
    v_ing = rbc.tabla_ingredientes(r_u)
    check("el total va ABAJO, en un renglón fijo, no en la cabecera ni en una fila",
          (list(v_ing.columns), "Total" in " ".join(v_ing["Insumo"]),
           "S/ 1.05" in rbc.renglon_total(r_u)),
          (["Insumo", "Cantidad", "Costo unit.", "Costo", "%"], False, True))
    check("sin vacíos que st.dataframe pinte «None» (#529)",
          bool(v_ing.isna().any().any()), False)
    check("una receta sin ingredientes cargados sale vacía",
          rbc.ingredientes(rb, "9999999", 1.0, bases).empty, True)

    check("el primer nivel trae lo vendido",
          "vendido" in consumo_recetas.sql_demanda_nivel1("x", date(2026, 1, 1), date(2026, 1, 2)),
          True)

    # ── El rail: el orden y los nombres que se pidieron (2026-09-30) ──────
    visibles = [v for _cat, vistas in rec._RAIL_CATEGORIAS for v in vistas
                if not v[1].startswith("Tabla")]
    check("el rail, en el orden pedido",
          [v[1] for v in visibles], ["Costo Carta", "Costo Recetas Base", "Revisar", "Nuevo Costeo"])
    check("la pila, en el mismo orden",
          [s for _k, s in rec._PILA if not s.startswith("Tabla")],
          [v[0] for v in visibles])
    check("el Ranking de recetas base ya no es una vista",
          any(v[0] == "Ranking de recetas base" for _c, vs in rec._RAIL_CATEGORIAS for v in vs)
          or any(s == "Ranking de recetas base" for _k, s in rec._PILA), False)
    check("el botón Actualizar refresca las órdenes y el primer nivel",
          all(a in REPORTES["Recetas"].get("archivos_extra", ())
              for a in (rbc.ARCHIVO_ORDENES, rbc.ARCHIVO_N1)), True)
    return fallos


def _pruebas_igv_y_sin_costo():
    """Ventas › Resumen y Mix (regla #590): el período en que cambió la tasa
    de IGV —que mueve el % de costo sin tocar ningún costo— y QUÉ se vendió
    sin costo cargado.

    Fija lo que se vería mal sin avisar: que una línea exonerada en un día
    flojo no pase por un cambio de ley (la tasa del día es la de la MAYORÍA
    de sus líneas), que el 10 → 10,5 % no se marque (mueve una décima), que
    una nota de crédito no cuente para la tasa, y que lo vendido sin costo
    salga de mayor a menor con la nota restando de su producto."""
    from graficos import ventas_resumen as vr

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · igv y sin costo · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · igv y sin costo · {nombre}: got={got!r} exp={exp!r}")

    dias = pd.to_datetime(["2025-06-08", "2025-06-08", "2025-06-09",
                           "2025-06-09", "2025-06-09", "2025-06-10",
                           "2025-06-10", "2025-06-11", "2026-02-10",
                           "2026-02-11"])
    neto = [100.0, 50.0, 80.0, 20.0, 40.0, 100.0, -100.0, 60.0, 100.0, 100.0]
    #       18 %   18 %   18 %   0 % (exonerada)  18 %  10 %  nota  10 %
    igv = [18.0, 9.0, 14.4, 0.0, 7.2, 10.0, -10.0, 6.0, 10.0, 10.5]
    cambios = vr.cambios_de_igv(dias, igv, neto)
    check("un cambio de 18 a 10 %, el día que pasó",
          [(d.strftime("%Y-%m-%d"), round(a, 3), round(b, 3))
           for d, a, b in cambios], [("2025-06-10", 0.18, 0.1)])
    check("sin líneas con neto, ningún cambio",
          vr.cambios_de_igv(dias[:1], [0.0], [-5.0]), [])
    check("la marca corta", vr.marca_igv(0.18, 0.10), "IGV 18→10%")
    check("el efecto: −6,1 % del % de costo", round(vr.efecto_igv(0.18, 0.10), 4),
          -0.0611)
    nota = vr.nota_igv(pd.Timestamp("2025-06-10"), 0.18, 0.10, pcosto=0.36)
    check("la frase dice el día, las tasas y los puntos",
          ("10/06/2025" in nota, "18%" in nota, "10%" in nota,
           "36.0%" in nota, "−2.2 pp" in nota or "-2.2 pp" in nota),
          (True, True, True, True, True))

    tabla = pd.DataFrame({
        "clave": ["a", "a", "a", "a", "b", "b"],
        "prod": ["Agua", "Agua", "Pisco", "Lomo", "Agua", "Pisco"],
        "venta": [11.0, 11.0, 30.0, 80.0, 11.0, -30.0],
        "pc": [0.0, 0.0, 0.0, 25.0, 0.0, 0.0],
    })
    por, rango = vr.productos_sin_costo(tabla)
    check("por período, de mayor a menor venta",
          por["a"], [("Pisco", 30.0), ("Agua", 22.0)])
    check("una nota de crédito resta de su producto y lo que queda en 0 no "
          "se nombra", por["b"], [("Agua", 11.0)])
    check("en el rango", rango, [("Agua", 33.0)])
    check("el texto de la celda", vr.texto_sin_costo(
        [("A", 3.0), ("B", 2.0), ("C", 1.0)]), "A, B y 1 más")
    check("el detalle con montos", vr.detalle_sin_costo([("Agua", 412.4)]),
          "Agua S/ 412")
    check("sin la columna de costo, nada",
          vr.productos_sin_costo(tabla.drop(columns=["pc"])), ({}, []))
    subs = vr._subvistas(None, [], {"pcosto", "psin", "sin_que"})
    check("la subvista Costo lleva la columna",
          "sin_que" in [c[0] for c in subs["Costo"][0]], True)
    return fallos


def _pruebas_filas_por_area():
    """«Por hora» › filas «Áreas» (regla #595): la venta por la estación del
    POS que prepara cada plato. Fija el nombre (el POS escribe «PASTELERIA»
    y la carta «Pastelería»), que el área viaje en el tramo sin tocar la
    venta, y que las filas salgan por venta con la matriz sumando lo
    mismo."""
    import datetime as _dt

    from graficos import ventas_horario as vh

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · por área · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · por área · {nombre}: got={got!r} exp={exp!r}")

    check("el nombre como el resto de la carta",
          vh.nombre_area(pd.Series(["CARNES Y PESCADOS", "PASTELERIA",
                                    " frios ", None, ""])).tolist(),
          ["Carnes y pescados", "Pastelería", "Fríos", "Sin área",
           "Sin área"])
    check("«Áreas» es una opción de filas, con su columna",
          ("Áreas" in vh._FILAS, vh._QUE_FILAS.get("Áreas")), (True, "area"))
    d = pd.DataFrame({
        "FEC REG DOCUMENTO": pd.to_datetime(["2026-09-04 13:10",
                                             "2026-09-04 13:20",
                                             "2026-09-04 20:40",
                                             "2026-09-05 21:00"]),
        "VENTA ITEM DDOCUMENTO": [80.0, 30.0, 50.0, 40.0],
        "GRUPO": ["Alimentos", "Bebidas s/ Alcohol", "Alimentos",
                  "Alimentos"],
        "AREA PRODUCCION": ["COCINA", "BAR", "CALIENTES", "COCINA"],
    })
    c = {"fecha": "FEC REG DOCUMENTO", "venta": "VENTA ITEM DDOCUMENTO",
         "fam": "GRUPO", "area": "AREA PRODUCCION"}
    t = vh._prep_tramo(d, c, "Semana", _dt.date(2026, 8, 31),
                       _dt.date(2026, 9, 6))
    check("el tramo trae el área", sorted(t["area"].unique()),
          ["Bar", "Calientes", "Cocina"])
    items = vh._items_filas([t], "area")
    check("las filas, por venta", items, ["Cocina", "Calientes", "Bar"])
    m = vh._matriz_filas(t, "area", items, True, "venta", list(range(24)),
                         False)
    check("la fila de Cocina: 80 a la 1 pm y 40 a las 9 pm",
          (m[0, 13], m[0, 21]), (80.0, 40.0))
    check("y la matriz suma la venta entera", float(m.sum()), 200.0)
    check("sin la columna, el tramo no inventa un área",
          "area" in vh._prep_tramo(d, {k: v for k, v in c.items()
                                       if k != "area"}, "Semana",
                                   _dt.date(2026, 8, 31),
                                   _dt.date(2026, 9, 6)).columns, False)
    return fallos


def _pruebas_ticket_sin_canales_sin_clientes():
    """El TICKET de Ventas (regla #591): la venta de los canales que
    registran clientes ÷ clientes. Rappi vende sin pax, y con su venta
    arriba el ticket de septiembre de 2026 daba S/ 150,32 en vez de 147,43.

    Fija las tres vistas que lo dibujan y la tabla que lo escribe: el mapa
    de «Por hora» (una celda con un pedido de Rappi), la marca del mapa, y
    las columnas del Resumen —el ticket neto en «Venta» y la subvista
    «Clientes», con los niños sólo si la consulta los trae—."""
    import datetime as _dt

    from graficos import ventas_horario as vh
    from graficos import ventas_resumen as vr

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · ticket · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · ticket · {nombre}: got={got!r} exp={exp!r}")

    d = pd.DataFrame({
        "FEC REG DOCUMENTO": pd.to_datetime(["2026-09-04 20:10",
                                             "2026-09-04 20:20",
                                             "2026-09-04 20:40"]),
        "VENTA ITEM DDOCUMENTO": [300.0, 100.0, 90.0],
        "CANT PAX": [3, 3, 0],
        "LLAVE LOCAL PEDIDO": ["P1", "P1", "R1"],
        "CANAL VENTA": ["En el Local", "En el Local", "Rappi"],
    })
    c = {"fecha": "FEC REG DOCUMENTO", "venta": "VENTA ITEM DDOCUMENTO",
         "pax": "CANT PAX", "pedido": "LLAVE LOCAL PEDIDO"}
    t = vh._prep_tramo(d, c, "Semana", _dt.date(2026, 8, 31),
                       _dt.date(2026, 9, 6))
    cel = vh._celdas(t).iloc[0]
    check("la celda suma la venta entera", float(cel["venta"]), 490.0)
    check("pero el ticket deja a Rappi afuera: 400 ÷ 3",
          round(float(cel["ticket"]), 4), round(400.0 / 3.0, 4))
    pin = {"c0": 0, "c1": 6, "h0": 20, "h1": 20}
    tot = vh._agregar_marca(t, pin, list(range(24)))
    check("la marca del mapa, igual", round(float(tot["ticket"]), 4),
          round(400.0 / 3.0, 4))
    check("la ficha de un día recibe la venta del ticket aparte",
          vh._celda_de_un_dia(t, "2026-09-04", 20), (490.0, 3.0, 400.0))

    hay = {"ticket", "ticket_neto", "sin_cli"}
    subs = vr._subvistas("Clientes", [], hay)
    check("«Venta» lleva el ticket neto",
          [x[0] for x in subs["Venta"][0] if x[0].startswith("ticket")],
          ["ticket", "ticket_neto"])
    check("«Clientes» sin niños: adultos y los dos tickets",
          [x[0] for x in subs["Clientes"][0]],
          ["valor", "sin_cli", "pax", "ticket", "ticket_neto"])
    subs = vr._subvistas("Clientes", [], hay | {"ninos", "personas",
                                                "ticket_p", "ticket_neto_p"})
    check("con niños: personas y el ticket por persona",
          [x[0] for x in subs["Clientes"][0]],
          ["valor", "sin_cli", "pax", "ninos", "personas", "ticket",
           "ticket_p", "ticket_neto", "ticket_neto_p"])
    check("sin clientes no hay subvista «Clientes»",
          "Clientes" in vr._subvistas("Pedidos", [], {"ticket"}), False)
    check("la subvista va en el selector", "Clientes" in vr._SUBVISTAS, True)

    g = pd.DataFrame({"total": [490.0], "pax": [3.0], "venta_cli": [400.0],
                      "neto_cli": [330.0]})
    kpi = vr._kpis_extra(g)[0]
    check("la tarjeta Clientes: el ticket sin Rappi", kpi[2], "ticket S/ 133.33")
    check("y su ayuda dice el neto y lo que quedó afuera",
          ("ticket neto S/ 110.00" in kpi[4], "S/ 90.00" in kpi[4]),
          (True, True))
    return fallos


def _pruebas_formas_de_pago():
    """Ventas › Resumen › Pagos (regla #592): lo cobrado por forma de pago.

    Fija lo que se vería mal sin avisar: un pago contado una vez aunque el
    parquet lo repita en cada plato (#517), la tarjeta abierta en su MARCA
    y «Varios» en su detalle, los anulados y las cortesías afuera, y las
    formas que no entran en la tabla juntas en «Otras» con sus nombres."""
    import definicion_venta as dv
    from graficos import ventas_resumen as vr

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · pagos · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · pagos · {nombre}: got={got!r} exp={exp!r}")

    tipo = pd.Series(["Tarjeta de Crédito", "Varios", "Efectivo", None,
                      "Tarjeta de Crédito"])
    tarj = pd.Series(["Visa", None, None, None, None])
    otro = pd.Series([None, "Nota de Credito", None, None, None])
    check("la tarjeta en su marca, Varios en su detalle",
          vr.forma_de_pago(tipo, tarj, otro).tolist(),
          ["Visa", "Nota de crédito", "Efectivo", "Sin forma",
           "Tarjeta de Crédito"])

    f = pd.Timestamp("2026-09-04 20:00")
    d = pd.DataFrame({
        "FEC REG DOCUMENTO": [f] * 7,
        "LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO": ["B1P1", "B1P1", "B2P1",
                                                   "B3P1", "K1P1", "A1P1",
                                                   None],
        "MONTO TIPO PAGO DOC": [100.0, 100.0, 40.0, 1480.0, 60.0, 90.0,
                                None],
        "NOMBRE TIPO PAGO": ["Tarjeta de Crédito"] * 2
                            + ["Varios", "Efectivo", "Efectivo",
                               "Efectivo", None],
        "NOMBRE TARJETA PAGO": ["Visa", "Visa", None, None, None, None, None],
        "NOMBRE OTRO TIPO PAGO DOC": [None, None, "Vale", None, None, None,
                                      None],
        dv.CLASE: [dv.VENTA, dv.VENTA, dv.VENTA, dv.VENTA, dv.CORTESIA,
                   dv.ANULADO, dv.VENTA],
    })
    claves = set(vr._periodo_serie(pd.Series([f]), "Mes"))
    pv = vr.formas_de_pago(d, "FEC REG DOCUMENTO", "Mes", claves)
    check("un pago una vez, sin cortesías ni anulados, en orden de monto",
          {k: float(v) for k, v in pv.iloc[0].items()},
          {"Efectivo": 1480.0, "Visa": 100.0, "Vale": 40.0})
    check("y en ese orden", list(pv.columns), ["Efectivo", "Visa", "Vale"])
    pv2 = vr.formas_de_pago(d, "FEC REG DOCUMENTO", "Mes", claves,
                            max_formas=2)
    check("las que no entran van juntas en «Otras»", list(pv2.columns),
          ["Efectivo", vr._OTRAS_FORMAS])
    check("con sus nombres", pv2.attrs.get("otras"), ["Visa", "Vale"])
    check("sin las columnas del pago, nada",
          vr.formas_de_pago(d.drop(columns=["NOMBRE TIPO PAGO"]),
                            "FEC REG DOCUMENTO", "Mes", claves), None)
    subs = vr._subvistas("Clientes", [], {"ticket"}, ["Visa", "Otras"],
                         ["Vale", "Cheque"])
    check("la subvista Pagos: una columna por forma, cobrado y por cobrar",
          [c[0] for c in subs["Pagos"][0]],
          ["valor", "f0_v", "f1_v", "cobrado", "por_cobrar"])
    check("«Otras» dice cuáles junta",
          "Vale, Cheque" in subs["Pagos"][0][2][4], True)
    check("y va en el selector", "Pagos" in vr._SUBVISTAS, True)
    return fallos


def _pruebas_control_pedidos():
    """Ventas › «Control de pedidos» (regla #594): las cuentas de la vista
    sobre `pedidos.parquet` y `transacciones.parquet`.

    Fija lo que se vería mal sin avisar: el motivo de un pedido anulado
    agrupado desde el texto libre del POS (con sus erratas), un plato
    anulado al minuto como corrección y no como pérdida, lo pasado a una
    cuenta de cortesía antes que una cuenta dividida, la mesa reabierta al
    día siguiente medida desde su primer plato, y la foto de ocupación con
    la fecha entera (el POS compara sólo la hora del día)."""
    from graficos import ventas_control as vc

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · control · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · control · {nombre}: got={got!r} exp={exp!r}")

    check("el motivo agrupado, erratas incluidas",
          vc.motivo_categoria(pd.Series([
              "MESQA VACIA", "PRODUYCTO EN 86", "POR CAMBIO DE PRECIO / NO SALIO",
              "DOBLE DIGITACION / NO SALIO", "CLIENTE CANCELO", "ST1204", "",
              None])).tolist(),
          ["Mesa vacía", "Producto agotado", "Error de precio",
           "Error de digitación", "Cliente cambió o canceló", "Otro",
           "Sin motivo", "Sin motivo"])

    ts = pd.Timestamp
    t = pd.DataFrame({"cocina": [False, True, False],
                      "min": [0.0, 30.0, 45.0]})
    check("plato anulado: corrección, ya en cocina, después",
          vc.clase_plato_anulado(t).tolist(),
          ["Corrección al digitar", "Ya en cocina", "Anulado después"])

    p = pd.DataFrame({"ped": ["A", "B", "C"],
                      "apertura": [ts("2026-09-04 20:00"),
                                   ts("2026-09-04 22:58"),
                                   ts("2026-09-04 21:00")]})
    tr = pd.DataFrame({"destino": ["B", "B", "C", "Z"],
                       "f_trx": [ts("2026-09-04 23:00")] * 4})
    check("transferencia: dividida, a cortesía antes que dividida, entre "
          "mesas, destino fuera del rango",
          vc.tipo_transferencia(tr.iloc[[0, 2, 3]], p).tolist()
          + vc.tipo_transferencia(tr.iloc[[1]], p, {"B"}).tolist(),
          ["Cuenta dividida", "Entre mesas", "Entre mesas", "A cortesía"])

    pe = pd.DataFrame({
        "ped": ["1", "2", "3"], "anulado": [False, False, False],
        "mesa": ["703", "101", "Sin Mesa"],
        "apertura": [ts("2026-09-12 22:21"), ts("2026-09-12 20:00"),
                     ts("2026-09-12 20:00")],
        "primer": [ts("2026-09-13 13:07"), ts("2026-09-12 20:05"),
                   ts("2026-09-12 20:01")],
        "ultimo": [ts("2026-09-13 14:09"), ts("2026-09-12 21:00"),
                   ts("2026-09-12 20:01")],
        "precuenta": [ts("2026-09-13 14:37"), ts("2026-09-12 21:30"), pd.NaT],
        "comp": [ts("2026-09-13 14:42"), ts("2026-09-12 21:35"),
                 ts("2026-09-12 20:02")],
        "dia": [ts("2026-09-13"), ts("2026-09-12"), ts("2026-09-12")],
        "adultos": [3.0, 2.0, 0.0], "monto": [471.0, 200.0, 50.0]})
    b = vc.tiempos(pe)
    check("sin mesa no cuenta", sorted(b["ped"]), ["1", "2"])
    check("la mesa reabierta se mide desde su primer plato",
          float(b.loc[b["ped"] == "1", "total"].iloc[0]), 95.0)
    check("los tramos de la otra", [float(b.loc[b["ped"] == "2", c].iloc[0])
                                    for c in ("espera", "comida",
                                              "sobremesa", "cobro", "total")],
          [5.0, 55.0, 30.0, 5.0, 95.0])
    z = vc.ocupacion(b, pd.date_range("2026-09-12", "2026-09-13"))
    sl = vc.etiquetas_slots()
    check("la foto de las 21:00 del 12 ve la mesa 101",
          float(z[0, sl.index("21:00")]), 1.0)
    check("y la de las 21:30 también (cobró a las 21:35)",
          float(z[0, sl.index("21:30")]), 1.0)
    check("a las 22:00 ya no", float(z[0, sl.index("22:00")]), 0.0)
    check("la reabierta ocupa la tarde del 13, no la mañana del 12",
          (float(z[1, sl.index("13:30")]), float(z[0, sl.index("13:30")])),
          (1.0, 0.0))
    check("grupos", vc.grupo_de(pd.Series([0, 1, 4, 9])).tolist(),
          ["Sin dato", "1", "3–4", "7 o más"])
    return fallos


def _pruebas_carta_costeada():
    """Recetas › Carta costeada (regla #548): lo que la vista hace con
    `cartacosteada.parquet` antes de dibujarlo.

    Fija lo que se ve mal sin avisar: un precio centinela (S/ 1 o menos)
    fuera y contado, un combo que se llama «Combo» aunque el POS no le haya
    puesto `tDescargo`, el % sobre el NETO (÷ el divisor del sistema) y no
    sobre el precio, sin costo = 0 (que se escribe «—», regla #529), la
    fecha 1900 en blanco, los filtros y que la vista esté en la pila, en el
    rail y en el botón de refresco del reporte.
    """
    from datetime import date

    from data import REPORTES
    from graficos import carta_costeada as cc
    from graficos import recetas as rec
    from graficos.recetas_comun import divisor_neto

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    recetas · carta costeada · {nombre}")
        else:
            fallos += 1
            print(f"FALLA recetas · carta costeada · {nombre}: got={got!r} exp={exp!r}")

    df = pd.DataFrame({
        "GRUPO": ["Alimentos", "Bebidas", "Alimentos", "Alimentos", "Bebidas", "Alimentos"],
        "SUBGRUPO": ["Fondos", "Aguas", "Menús", "Fondos", "Aguas", "Fondos"],
        "COD PLATO": ["0000010", "0000020", "0000030", "0000040", "0000050", "0000060"],
        "ITEM VENT ACT": ["ACTIV", "ACTIV", "ACTIV", "INACT", "ACTIV", "ACTIV"],
        "ITEM VENT": ["Lomo Saltado", "Agua Munay", "Menú Sapiens", "Viejo", "Vale", "Ají de Gallina"],
        "P.VENTA SALON": [74.1, 9.0, 175.0, 50.0, 0.5, 49.4],
        "COSTO SALON": [24.7, None, 45.11, 10.0, 0.1, 0.0],
        "TIPO DESC": ["RECETA", "NO APLICA", None, "RECETA", "DIRECTO", "RECETA"],
        "TIPO COMBO": [None, None, "A ELEGIR", None, None, None],
        "METODO COSTO": ["COSTO DEL PRODUCTO", "COSTO DEL PRODUCTO",
                         "ESPERADO 90 DIAS", "COSTO DEL PRODUCTO",
                         "COSTO DEL PRODUCTO", "COSTO DEL PRODUCTO"],
        "COSTO MINIMO": [None, None, 22.75, None, None, None],
        "COSTO ESPERADO": [None, None, 45.11, None, None, None],
        "COMBOS VENDIDOS 90 DIAS": [None, None, 29, None, None, None],
        "ULTIMA VENT": [pd.Timestamp("2026-09-20"), pd.Timestamp("1900-01-01"),
                        pd.Timestamp("2026-09-19"), None, None, None],
    })
    t, n_sin_precio = cc.preparar(df)
    check("sin los inactivos ni el precio centinela", sorted(t["Cod"]),
          ["0000010", "0000020", "0000030", "0000060"])
    check("el precio centinela se cuenta", n_sin_precio, 1)
    fila = t.set_index("Cod")
    check("un combo sin tDescargo se llama Combo", fila.loc["0000030", "Tipo"], "Combo")
    check("el tipo de un plato con receta", fila.loc["0000010", "Tipo"], "Receta")
    check("el % es sobre el neto", round(fila.loc["0000010", "Pct"], 6),
          round(24.7 / (74.1 / divisor_neto()) * 100, 6))
    check("sin costo cargado: % en 0 (se escribe «—»)",
          (fila.loc["0000020", "Pct"], bool(fila.loc["0000020", "SinCosto"])),
          (0.0, True))
    check("costo 0 también es «sin costo»", bool(fila.loc["0000060", "SinCosto"]), True)
    # Una fecha que falta viaja como una fecha centinela que se escribe «—»:
    # un vacío se pintaría «None» (#529), y un texto no se ordena por fecha.
    check("la fecha 1900 queda en la centinela", fila.loc["0000020", "UltimaVenta"],
          cc._SIN_FECHA)
    check("y se escribe «—»", cc._dia(fila.loc["0000020", "UltimaVenta"]), "—")
    check("una fecha de verdad se escribe entera",
          cc._dia(fila.loc["0000010", "UltimaVenta"]), "20/09/2026")
    check("el método del combo, dicho para leerse",
          fila.loc["0000030", "Metodo"], cc.METODOS["ESPERADO 90 DIAS"])
    check("un plato normal no lleva método", fila.loc["0000010", "Metodo"], "")
    check("una columna que falta viaja en 0 (Máximo)", fila.loc["0000030", "Maximo"], 0.0)
    check("ordenada por % de costo", list(t["Cod"])[:2], ["0000010", "0000030"])
    check("filtro Sin costo", sorted(cc.filtrar(t, tipo="Sin costo")["Cod"]),
          ["0000020", "0000060"])
    check("filtro por grupo", sorted(cc.filtrar(t, grupo="Bebidas")["Cod"]), ["0000020"])
    check("buscar sin acentos ni mayúsculas",
          list(cc.filtrar(t, buscar="aji de")["Cod"]), ["0000060"])
    check("con inactivos", len(cc.preparar(df, incluir_inactivos=True)[0]), 5)
    # Sin la línea de números de arriba de la tabla ni la del producto: se
    # quitaron a pedido para que la tarjeta entre en una pantalla (#572).
    check("sin resumen ni línea de números del producto",
          (hasattr(cc, "resumen"), hasattr(cc, "kpis_producto")), (False, False))

    check("está en la pila de Recetas",
          ("rec_sec_carta", "Carta costeada") in rec._PILA, True)
    check("y en su rail", any(v[0] == "Carta costeada"
                              for _cat, vistas in rec._RAIL_CATEGORIAS for v in vistas), True)
    check("y el botón Actualizar la refresca",
          cc.ARCHIVO in REPORTES["Recetas"].get("archivos_extra", ()), True)

    # ── Desde el 2026-09-28 es LA vista de la carta (regla #556) ─────────
    # Composición era esta tabla filtrada a los platos con receta, y Costeo
    # sumaba el mismo costo con los platos inactivos adentro: se fueron. Su
    # panel —receta, simulador, dona y Sankey— lo abre un clic acá.
    _vistas = {v[0] for _cat, vistas in rec._RAIL_CATEGORIAS for v in vistas}
    check("Composición ya no es una vista (ni en el rail ni en la pila)",
          ("Composición del plato" in _vistas)
          or any(v == "Composición del plato" for _k, v in rec._PILA), False)
    check("Costeo tampoco",
          ("Costeo Receta Venta" in _vistas)
          or any(v == "Costeo Receta Venta" for _k, v in rec._PILA), False)

    check("el margen es neto − costo", round(fila.loc["0000010", "Margen"], 6),
          round(74.1 / divisor_neto() - 24.7, 6))
    check("sin costo no hay margen (va 0, se escribe «—»)",
          (fila.loc["0000020", "Margen"], cc._soles(fila.loc["0000020", "Margen"])),
          (0.0, "—"))
    check("un margen negativo se escribe con su signo", cc._soles(-230.67), "−S/ 230.67")
    check("«Sin enlace» y «No aplica» se pueden elegir",
          ("Sin enlace" in cc.TIPOS, "No aplica" in cc.TIPOS), (True, True))
    check("filtro No aplica", list(cc.filtrar(t, tipo="No aplica")["Cod"]), ["0000020"])

    # Venta Interna: arranca fuera, un interruptor la suma.
    vi = pd.concat([df, pd.DataFrame({
        "GRUPO": ["Venta Interna"], "SUBGRUPO": ["Bebidas"], "COD PLATO": ["0000070"],
        "ITEM VENT ACT": ["ACTIV"], "ITEM VENT": ["(Cst) Cerveza"],
        "P.VENTA SALON": [3.89], "COSTO SALON": [3.68], "TIPO DESC": ["DIRECTO"]})],
        ignore_index=True)
    tvi, _ = cc.preparar(vi)
    check("Venta Interna arranca fuera", "0000070" in set(cc.filtrar(tvi)["Cod"]), False)
    check("y el interruptor la suma",
          "0000070" in set(cc.filtrar(tvi, venta_interna=True)["Cod"]), True)

    # Lo vendido: el resumen por producto y día de `definicion_venta`.
    agg = pd.DataFrame({
        "producto": ["0000010", "0000010", "0000020", "0000010"],
        "dia": pd.to_datetime(["2026-09-27", "2026-07-01", "2026-09-20", "2026-06-01"]),
        "unidades": [3.0, 2.0, 40.0, 100.0],
        "neto": [180.0, 120.0, 290.0, 6000.0],
        "costo": [72.0, 48.0, 0.0, 2400.0],
        "unidades_costeadas": [3.0, 2.0, 0.0, 100.0],
        "neto_sin_costo": [0.0, 0.0, 290.0, 0.0],
    })
    tv, rango = cc.con_ventas(t, agg)
    fv = tv.set_index("Cod")
    check("la ventana son 90 días hasta el último con venta",
          rango, (date(2026, 6, 30), date(2026, 9, 27)))
    check("vendidos: sólo lo de la ventana", fv.loc["0000010", "Vendidos"], 5.0)
    check("el % al que se vendió es costo ÷ neto de lo vendido",
          round(fv.loc["0000010", "PctVendido"], 6), 40.0)
    check("lo vendido sin costo viaja aparte (y su % es «—»)",
          (fv.loc["0000020", "SinCostoNeto"], fv.loc["0000020", "PctVendido"]),
          (290.0, 0.0))
    check("un producto sin ventas, 0", fv.loc["0000030", "Vendidos"], 0.0)
    check("«Sin costo» se ordena por lo vendido",
          list(cc.filtrar(tv, tipo="Sin costo")["Cod"]), ["0000020", "0000060"])
    check("sin resumen de ventas la vista sigue, en cero",
          (cc.con_ventas(t, None)[1], float(cc.con_ventas(t, None)[0]["Vendidos"].sum())),
          (None, 0.0))
    # La ventana de «Vendidos» se elige (regla #572): con 30 días, lo del
    # 1 de julio queda fuera y lo del 27 de setiembre dentro.
    t30, r30 = cc.con_ventas(t, agg, cc.VENTANAS_VENDIDOS["30 días"])
    check("con 30 días, sólo lo vendido en esos 30",
          (r30, float(t30.set_index("Cod").loc["0000010", "Vendidos"])),
          ((date(2026, 8, 29), date(2026, 9, 27)), 3.0))
    t365, _ = cc.con_ventas(t, agg, cc.VENTANAS_VENDIDOS["1 año"])
    check("con un año, también lo de junio",
          float(t365.set_index("Cod").loc["0000010", "Vendidos"]), 105.0)
    check("la ventana por defecto sigue en 90 días",
          cc.VENTANAS_VENDIDOS["90 días"], cc.DIAS_VENDIDOS)
    # Lo vendido puede llegar ya cargado o como la función que lo carga
    # (regla #573): cargado, pasa tal cual.
    check("lo vendido ya cargado pasa tal cual",
          (cc._lo_vendido(agg) is agg, cc._lo_vendido(None)), (True, None))

    # El costo en el tiempo (regla #557): la foto del POS, por mes.
    cm = cc.costo_mensual(agg, "0000010")
    check("el costo en el tiempo: un mes por fila, en orden",
          [str(m) for m in cm["mes"]], ["2026-06", "2026-07", "2026-09"])
    check("el costo por unidad de cada mes: costo ÷ unidades con costo",
          [round(v, 6) for v in cm["costo_unit"]], [24.0, 24.0, 24.0])
    cm2 = cc.costo_mensual(agg, "0000020")
    check("un mes vendido entero sin costo no tiene costo por unidad",
          (len(cm2), bool(cm2["costo_unit"].isna().all()),
           float(cm2["neto_sin_costo"].iloc[0])), (1, True, 290.0))
    check("un producto sin ventas, vacío",
          (cc.costo_mensual(agg, "0000099").empty,
           cc.costo_mensual(None, "0000010").empty), (True, True))
    check("el mes se escribe en castellano", cc._etiqueta_mes(pd.Period("2026-09")),
          "set 26")

    # Las columnas de la tabla (regla #570): primero lo que ubica al
    # producto, y lo que no hace falta para decidir, detrás de «Más
    # columnas» — sin eso no entra el producto elegido al costado.
    base = cc.columnas_carta()
    check("la tabla empieza por Grupo, Subgrupo y Producto", base[:3],
          ["Grupo", "Subgrupo", "Producto"])
    # «P. neto» se sumó a las opcionales en la regla #574.
    _opcionales = {"Tipo", "Actualizado", "UltimaVenta", "Margen", "Vendidos",
                   "Neto"}
    check("sin «Más columnas» no están las seis opcionales",
          sorted(_opcionales & set(base)), [])
    check("con «Más columnas» están las seis",
          sorted(_opcionales - set(cc.columnas_carta(mas=True))), [])
    check("y todas existen en la carta preparada",
          sorted(set(cc.columnas_carta(mas=True)) - set(tv.columns)
                 - {"Actualizado"}), [])
    check("en el teléfono el nombre va primero",
          cc.columnas_carta(movil=True)[:3], ["Producto", "Grupo", "Subgrupo"])
    check("sin ventas no hay «Vendidos», ni con «Más columnas»",
          "Vendidos" in cc.columnas_carta(mas=True, con_ventas_=False), False)
    check("la banda de los combos existe en la carta preparada",
          sorted(set(cc._BANDA) - set(t.columns)), [])

    # «Tipo de Oferta» (regla #571): la carta impresa sale de nBoton en la
    # consulta de la CARTA —un atributo del producto—, no de la de ventas.
    check("sin la columna, nadie tiene tipo de oferta (y Ver no la ofrece)",
          set(t["Oferta"]), {""})
    of = df.assign(**{"Tipo de Oferta": ["Carta impresa", "Carta no impresa", None,
                                         "Carta impresa", None, "CARTA IMPRESA"]})
    to, _ = cc.preparar(of)
    fo = to.set_index("Cod")
    check("el tipo de oferta se lee sin importar mayúsculas",
          (fo.loc["0000010", "Oferta"], fo.loc["0000060", "Oferta"]),
          ("Carta impresa", "Carta impresa"))
    check("un nBoton fuera de rango (nulo) queda sin tipo",
          fo.loc["0000030", "Oferta"], "")
    check("filtro Impresa", sorted(cc.filtrar(to, oferta="Carta impresa")["Cod"]),
          ["0000010", "0000060"])
    check("filtro No impresa",
          list(cc.filtrar(to, oferta="Carta no impresa")["Cod"]), ["0000020"])
    check("la oferta se elige entre la carta impresa y la no impresa",
          cc.OFERTAS, ("Carta impresa", "Carta no impresa"))

    # Las recetas base (regla #572): un insumo de la receta es receta base
    # si su código de almacén es el `COD PROD RB` de una; se abre
    # proporcionada a lo que usa el plato (40 g de un kilo = 0,04).
    rb = pd.DataFrame({
        "COD RB": ["00329", "00329", "00330"],
        "COD PROD RB": ["0003215", "0003215", "0002554"],
        "RB ACT": ["RB.ACTIV"] * 3,
        "COD INS RB": ["0000527", "0002554", "0000460"],
        "INSUMO": ["Vino Tinto De Cocina", "(Rs) Demiglace de Res", "Sal De Mesa"],
        "CANT": [1000.0, 3000.0, 15.0],
        "FACTOR INS": [1000.0, 1000.0, 1000.0],
        "CST SUBT INS": [11.446077, 27.34561, 0.025609],
    })
    bases = cc.codigos_base(rb)
    check("qué artículos tienen receta base", sorted(bases), ["0002554", "0003215"])
    tb = cc.receta_base(rb, "0003215", 40 / 1000, bases)
    check("la receta base, proporcionada a lo que usa el plato",
          [round(v, 4) for v in tb["Costo"]], [round(27.34561 * 0.04, 4),
                                                round(11.446077 * 0.04, 4)])
    check("y sus cantidades también", [round(v, 3) for v in tb["Cantidad"]],
          [120.0, 40.0])
    check("marca la receta base que tiene adentro", list(tb["EsBase"]), [True, False])
    check("el % es sobre el total de la receta base",
          round(float(tb["%"].sum()), 6), 100.0)
    fil = cc._filas_clic(tb, bases)
    check("abrir la de adentro: su escala es su cantidad ÷ su factor",
          round(fil[0]["escala"], 6), 0.12)
    check("un artículo sin receta base, tabla vacía",
          (cc.receta_base(rb, "0000460", 1.0, bases).empty,
           cc.receta_base(None, "0003215").empty, cc.codigos_base(None)),
          (True, True, frozenset()))

    # Los porcionamientos (regla #574): un insumo porcionado muestra de qué
    # porcionamientos salió, del más nuevo al más viejo, una fila por
    # porcionamiento aunque el parquet traiga una por CORTE (#510).
    po = pd.DataFrame({
        "COD PORC": ["P1", "P1", "P2", "P3"],
        "COD PROD FINAL": ["0004117", "0009999", "0004117", "0004117"],
        "FEC REGIST": pd.to_datetime(["2026-09-26", "2026-09-26", "2026-09-21",
                                      "2026-09-12"]),
        "PROD INICIAL": ["(P) Cachema Limpia"] * 4,
        "UNID PROD INIC": ["UND"] * 4,
        "CANT A PORCIONAR": [15.0, 15.0, 16.0, 15.0],
        "CANT MERMA": [0.0, 0.0, 1.0, 0.0],
        "CANT RESULT": [15.0, 3.0, 15.0, 15.0],
        "UNID PROD FIN": ["UND"] * 4,
        "PREC PROM PROD FIN": [26.780552, 1.0, 29.258964, 27.803125],
    })
    check("qué códigos salen de un porcionamiento",
          sorted(cc.codigos_porcionados(po)), ["0004117", "0009999"])
    pd4117 = cc.porcionamientos_de(po, "0004117")
    check("sus porcionamientos, del más nuevo al más viejo",
          [round(v, 2) for v in pd4117["Costo"]], [26.78, 29.26, 27.8])
    check("la merma, sobre lo porcionado", round(pd4117["Merma"].iloc[1], 2), 6.25)
    check("con tope de filas", len(cc.porcionamientos_de(po, "0004117", n=2)), 2)
    check("un código sin porcionamientos, vacío",
          (cc.porcionamientos_de(po, "0000001").empty,
           cc.porcionamientos_de(None, "0004117").empty,
           cc.codigos_porcionados(None)), (True, True, frozenset()))
    check("el detalle abre en lo que explica el costo de la receta",
          (cc.costo_de_origen(1.705, 0.034, 1.705), cc.costo_de_origen(21.0, 21.0, 28.0),
           cc.costo_de_origen(5.0, None, 4.0), cc.costo_de_origen(5.0, None, None)),
          ("porc", "base", "porc", None))
    fp = cc._filas_clic(pd.DataFrame({"Cod": ["0004117", "0000460"],
                                      "Insumo": ["(P) Pesca", "Sal"],
                                      "Cantidad": [1.0, 3.0], "Factor": [1.0, 1000.0],
                                      "Costo": [26.78, 0.01]}),
                        frozenset(), cc.codigos_porcionados(po))
    check("un porcionado se puede abrir; un insumo de compra, no",
          [cc._abre(x) for x in fp], [True, False])

    rv = pd.DataFrame({"COD PLATO": ["0000010", "0000010", "0000030"],
                       "FECH MODIF": pd.to_datetime(["2022-09-23", "2022-09-23",
                                                     "2026-03-12"])})
    check("la fecha de la receta, una por plato",
          cc.fechas_de_receta(rv), {"0000010": pd.Timestamp("2022-09-23"),
                                    "0000030": pd.Timestamp("2026-03-12")})
    return fallos


def _pruebas_ventas_franja():
    """Ventas › Análisis por Hora › «A medida» (regla #627): las cuentas.

    Fija lo que no se ve hasta que miente: que «hasta» no se incluya (dos
    horarios seguidos no cuentan dos veces el pedido de las 22:00), que un
    horario que cruza la medianoche le dé lo de la madrugada al día ANTERIOR,
    que los días elegidos sean los de la semana pedida dentro del rango, que
    el detalle por día liste también los días SIN venta, que se agrupe por
    nombre de columna, y que «Por hora» le pase su `filtrar_cb`: el
    tramo viene aparte de R2.
    """
    import inspect
    from datetime import date

    from graficos import ventas_franja as _f
    from graficos import ventas_horario as _h

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · franja · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · franja · {nombre}: got={got!r} exp={exp!r}")

    check("17:30 son 1050 minutos", _f.a_minutos("17:30"), 1050)
    check("24:00 es el fin del día", _f.a_minutos("24:00"), 1440)

    doms = _f.dias_elegidos(date(2026, 9, 7), date(2026, 10, 9), [6])
    check("los domingos de un rango",
          doms, [date(2026, 9, 13), date(2026, 9, 20), date(2026, 9, 27),
                 date(2026, 10, 4)])
    check("rango al revés: ningún día",
          _f.dias_elegidos(date(2026, 10, 9), date(2026, 10, 1), range(7)), [])

    ts = pd.Series(pd.to_datetime([
        "2026-10-04 17:29", "2026-10-04 17:30", "2026-10-04 21:59",
        "2026-10-04 22:00", "2026-10-05 00:30", None]))
    dentro, dia = _f.en_horario(ts, 1050, 1320)
    check("17:30 → 22:00: entra de 17:30 a 21:59",
          dentro.tolist(), [False, True, True, False, False, False])
    dentro, dia = _f.en_horario(ts, 1200, 60)
    check("20:00 → 01:00 cruza: la 00:30 entra",
          dentro.tolist(), [False, False, True, True, True, False])
    check("y la 00:30 del lunes es del DOMINGO",
          dia[4].date(), date(2026, 10, 4))
    check("cruza_medianoche", (_f.cruza_medianoche(1200, 60),
                               _f.cruza_medianoche(0, 1440)), (True, False))

    b = pd.DataFrame({
        "dia": pd.to_datetime(["2026-09-13", "2026-09-13", "2026-09-27"]),
        "grupo": ["Alimentos", "Alimentos", "Bebidas"],
        "sub": ["Fondos", "Fondos", "Vinos"],
        "prod": ["Lomo", "Lomo", "Malbec"],
        "venta": [100.0, 50.0, 80.0], "cant": [2.0, 1.0, 1.0],
        "pedido": ["P1", "P1", "P2"]})
    pdia = _f.por_dia(b, doms)
    check("por día: los 4 domingos, también los que no vendieron",
          len(pdia), 4)
    check("por día: el 20 sin venta queda en cero",
          float(pdia.loc[pd.Timestamp("2026-09-20"), "venta"]), 0.0)
    check("por día: pedidos distintos",
          int(pdia.loc[pd.Timestamp("2026-09-13"), "pedidos"]), 1)
    check("por día: columnas por nombre",
          list(pdia.columns), ["venta", "cant", "pedidos"])
    g = _f.por_grupo(b, "Plato")
    check("por plato: columnas por nombre",
          list(g.columns), ["grupo", "sub", "prod", "cant", "venta"])
    check("por plato: el que más vende primero, sumado",
          (g.loc[0, "prod"], float(g.loc[0, "venta"])), ("Lomo", 150.0))
    check("por grupo", list(_f.por_grupo(b, "Grupo")["grupo"]),
          ["Alimentos", "Bebidas"])

    src = inspect.getsource(_h._ventas_horario)
    check("«Por hora» le pasa su filtrar_cb al modo «A medida»",
          "_franja.cuerpo(d, filtrar_cb," in src, True)
    check("el interruptor tiene los tres modos",
          _h.MODOS_VISTA, ("Mapa", "Comparar", "A medida"))
    # «Mapa» elige solo cómo partir las fechas: un día, meses o años.
    check("Mapa · un solo día va en Día",
          _h.grano_automatico(date(2026, 10, 4), date(2026, 10, 4)), "Día")
    check("Mapa · 30 días que cruzan de mes van en Mes",
          _h.grano_automatico(date(2026, 9, 11), date(2026, 10, 10)), "Mes")
    check("Mapa · cuatro meses todavía en Mes",
          _h.grano_automatico(date(2026, 7, 1), date(2026, 10, 10)), "Mes")
    check("Mapa · doce meses van en Año",
          _h.grano_automatico(date(2025, 10, 11), date(2026, 10, 10)),
          "Año")
    return fallos


def _pruebas_ventas_platos():
    """Ventas › Análisis de platos (regla #529): las cuentas del ranking.

    Fija lo que no se ve hasta que miente: el puesto con empates (los dos
    empatados se quedan con el puesto más alto), que un plato sin venta no
    tenga puesto, el movimiento entre el primer y el último período, que la
    variación sea POR DÍA (un mes en curso contra uno entero no es una
    caída), cuántos períodos ofrece cada corte, y que el dispatcher le pase
    `_filtrar_items`: los períodos vienen aparte de R2.
    """
    import ast
    import inspect
    import textwrap
    from datetime import date

    from graficos import ventas as _v
    from graficos import ventas_mix as _mx
    from graficos import ventas_platos as _p

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · platos · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · platos · {nombre}: got={got!r} exp={exp!r}")

    v = pd.Series({"Lomo": 500.0, "Pulpo": 300.0, "Ceviche": 300.0,
                   "Agua": 10.0, "Postre": 0.0})
    p = _p.puestos(v)
    check("puestos con empate: los dos empatados son 2º",
          p.to_dict(), {"Lomo": 1, "Pulpo": 2, "Ceviche": 2, "Agua": 4})
    check("sin venta no hay puesto", "Postre" in p.index, False)

    check("sube 5 puestos: verde", _p.movimiento(8, 3), ("▲ 5", "sube"))
    check("sube 1: se escribe, pero no se pinta", _p.movimiento(4, 3),
          ("▲ 1", "igual"))
    check("baja 4: rojo", _p.movimiento(2, 6), ("▼ 4", "baja"))
    check("no vendía en el primero: entra", _p.movimiento(None, 7),
          ("entra", "entra"))
    check("dejó de vender: sale", _p.movimiento(3, None), ("sale", "sale"))

    check("la variación es POR DÍA: 23 días que venden lo mismo por día "
          "que 31 no son una caída",
          _p.var_por_dia(3100.0, 31, 2300.0, 23), 0.0)
    check("sin base, sin porcentaje", _p.var_por_dia(0.0, 31, 500.0, 23),
          None)

    ancla, primero = date(2026, 9, 24), date(2025, 1, 1)
    check("Mes ofrece 13 meses: el mismo mes del año pasado entra",
          [_p.periodos("Mes", ancla, primero)[i] for i in (0, -1)],
          [(2025, 9), (2026, 9)])
    check("Año ofrece todos los años con dato",
          _p.periodos("Año", ancla, primero), [2025, 2026])
    check("Día ofrece 14 días", len(_p.periodos("Día", ancla, primero)), 14)
    check("Semana ofrece 10 semanas",
          len(_p.periodos("Semana", ancla, primero)), 10)

    b = pd.DataFrame({
        "fecha": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-09-02"]),
        "grupo": ["Alimentos", "Alimentos", "Bebidas"],
        "sub": ["Fondos", "Fondos", "Cocteles"],
        "prod": ["Lomo", "Lomo", "Pisco Sour"],
        "venta": [100.0, 50.0, 30.0], "cant": [2.0, 1.0, 3.0],
        "costo": [30.0, 15.0, 0.0], "neto": [81.0, 40.5, 24.3]})
    a = _p.agregar(b)
    check("el agregado trae sus columnas por nombre",
          list(a.columns),
          ["prod", "grupo", "sub", "venta", "cant", "costo", "neto", "pedidos"])
    check("con la llave del pedido, cada pedido cuenta una vez (#550)",
          _p.agregar(b.assign(pedido=["P1", "P2", "P2"])).set_index("prod")
          ["pedidos"].to_dict(), {"Lomo": 2, "Pisco Sour": 1})
    check("Lomo suma sus dos líneas",
          a.set_index("prod").loc["Lomo", ["venta", "cant"]].tolist(),
          [150.0, 3.0])

    # ── El % de costo de cada plato (regla #546) ──────────────────────────
    pc = _p.costo_por_plato(a.set_index("prod"))
    check("% costo del plato: costo ÷ NETO, no ÷ venta (45 / 121,5)",
          round(float(pc["Lomo"]), 4), round(45.0 / 121.5, 4))
    check("sin costo cargado no es 0 %: no hay número",
          bool(pd.isna(pc["Pisco Sour"])), True)
    partido = pd.DataFrame({
        "prod": ["Lomo", "Lomo"], "grupo": ["Alimentos", "Alimentos"],
        "sub": ["Fondos", "Parrilla"], "venta": [100.0, 50.0],
        "cant": [2.0, 1.0], "costo": [30.0, 15.0], "neto": [81.0, 40.5]})
    check("un plato que cambió de subgrupo se cuenta una vez",
          round(float(_p.costo_por_plato(partido.set_index("prod"))["Lomo"]),
                4), round(45.0 / 121.5, 4))
    check("la cuenta y los colores son los del Mix, no una copia",
          (_p.pct_costo is _mx.pct_costo, _p._estilo_costo is _mx._estilo_costo),
          (True, True))

    fuente = textwrap.dedent(inspect.getsource(_v.renderizar_graficos_ventas))
    llamadas = [n for n in ast.walk(ast.parse(fuente))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "_ventas_platos"]
    check("el dispatcher lo llama una vez", len(llamadas), 1)
    for c in llamadas:
        check("con `d` y filtrar_cb=_filtrar_items",
              ([ast.unparse(x) for x in c.args],
               {k.arg: ast.unparse(k.value) for k in c.keywords}
               .get("filtrar_cb")), (["d"], "_filtrar_items"))
    analisis = dict(_v._VENTAS_RAIL_CATEGORIAS).get("Análisis", ())
    check("es la primera vista de «Análisis» en el rail",
          analisis[0][0] if analisis else None, "Análisis de platos")
    check("y tiene su sección en la pila",
          "Análisis de platos" in dict(_v._PILA).values(), True)
    vistas = [v for _cat, vs in _v._VENTAS_RAIL_CATEGORIAS for v, *_ in vs]
    check("«Ranking & FoodCost» se fue: su lugar es éste (#545)",
          ("Ranking & FoodCost" in vistas,
           "Ranking & FoodCost" in dict(_v._PILA).values()), (False, False))

    # ── Una tarjeta, dos vistas (regla #569) ──────────────────────────────
    todos = pd.DataFrame({
        "grupo": ["Alimentos", "Alimentos", "Bebidas", "Bebidas"],
        "sub": ["Fondos", "Entradas", "Cocteles", "Bebidas"],
        "venta": [500.0, 100.0, 300.0, 50.0]},
        index=["Lomo", "Ceviche", "Pisco Sour", "Agua"])
    ops = _p.opciones_ambito(todos)
    check("el ámbito es UN desplegable: la carta, los grupos y los "
          "subgrupos, cada tanda de la que más vende a la que menos",
          list(ops), ["Toda la carta", "Grupo: Alimentos", "Grupo: Bebidas",
                      "Subgrupo: Fondos", "Subgrupo: Cocteles",
                      "Subgrupo: Entradas", "Subgrupo: Bebidas"])
    check("un grupo y un subgrupo del mismo nombre no se confunden",
          (ops["Grupo: Bebidas"], ops["Subgrupo: Bebidas"]),
          (("grupo", "Bebidas"), ("sub", "Bebidas")))
    check("toda la carta no filtra", ops["Toda la carta"], (None, None))
    check("abre en el ranking", _p._VISTA_DEFAULT, "Ranking")
    import math
    check("el Corte no se mueve al cambiar de vista: su columna pesa lo "
          "mismo en las dos filas",
          math.isclose(_p.FILA_RANKING[0] / sum(_p.FILA_RANKING),
                       _p.FILA_MENU[0] / sum(_p.FILA_MENU)), True)
    check("las dos filas tienen cuatro columnas: la que sobra se escribe "
          "vacía, no se deja al borrado de Streamlit",
          (len(_p.FILA_RANKING), len(_p.FILA_MENU)), (4, 4))
    # Lo que se dibuja con UNA sola vista tiene que recordar su valor
    # mientras se ve la otra: sin `persist_state`, volver al ranking lo
    # dejaba en su default (Top 15, toda la carta, sin elegidos).
    from graficos import ventas_menu as _im
    compartidas = {"vt_pl_vista", "vt_pl_corte"}
    propias, sin_persistir = set(), []
    for mod in (_p, _im):
        for n in ast.walk(ast.parse(inspect.getsource(mod))):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("segmented_control", "selectbox",
                                        "multiselect")):
                continue
            kw = {k.arg: k.value for k in n.keywords}
            clave = kw.get("key")
            if not isinstance(clave, ast.Constant) or clave.value in compartidas:
                continue
            propias.add(clave.value)
            if not (isinstance(kw.get("persist_state"), ast.Constant)
                    and kw["persist_state"].value == "page"):
                sin_persistir.append(clave.value)
    check("los controles de cada vista llevan persist_state='page'",
          sorted(sin_persistir), [])
    check("y son los que se esperan (si no, el barrido no mira nada)",
          sorted(propias), ["vt_ing_forma", "vt_ing_subs", "vt_pl_amb",
                            "vt_pl_elegidos", "vt_pl_medida",
                            "vt_pl_mostrar"])
    check("la Ingeniería ya no abre una tarjeta propia",
          ("ajuste_graf_card_izq_ventas_menu" in inspect.getsource(_im),
           hasattr(_im, "tarjeta_ingenieria")), (False, False))
    return fallos



def _pruebas_ventas_meseros():
    """Ventas › Meseros (regla #553): las propinas por mesero.

    Un parquet de mentira con cada caso real: un pedido pagado con tarjeta
    y efectivo (sus ítems salen dos veces), uno con tarjeta y sin propina,
    uno pagado sólo en efectivo, uno de Rappi sin mesero, una cortesía y
    otro turno. Fija que la venta cuente un ítem una vez y la propina un
    pago una vez (regla #517), que la cortesía no entre, qué es una mesa,
    el pozo común (partes iguales entre los meseros del turno, sin perder un
    sol), la planilla, los tramos de %, con qué se compara y el Excel. Todo
    leído por NOMBRE de columna (regla #481).
    """
    import datetime as _d
    import io as _io
    import zipfile

    from graficos import ventas_meseros as _m

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · meseros · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · meseros · {nombre}: got={got!r} exp={exp!r}")

    filas = []

    def pedido(ped, mesero, serv, items, pagos, pax, clase="Venta",
               hora="2026-09-01 21:00"):
        """`items`: (llave, producto, grupo, cantidad, venta);
        `pagos`: (llave del pago, tipo, propina) — un ítem sale una vez
        POR PAGO, como en `ventas.parquet`."""
        for llave, prod, grupo, cant, venta in items:
            for lp, tipo, prop in (pagos or [(None, None, None)]):
                filas.append({
                    "LLAVE LOCAL PEDIDO": ped, "NOMBRE MESERO": mesero,
                    "FEC REG DOCUMENTO": pd.Timestamp(hora),
                    "SERVICIO": serv, "VENTA ITEM DDOCUMENTO": venta,
                    "CANTIDAD ITEM DDOCUMENTO": cant, "CANT PAX": pax,
                    "LLAVE LOCAL DOCUMENTO": f"D{ped}",
                    "NUMERO DOCUMENTO": f"B001-{ped}",
                    "LLAVE LOCAL DOCUMENTO ITEM": llave,
                    "LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO": lp,
                    "NOMBRE TIPO PAGO": tipo, "MONTO PROPINA": prop,
                    "NOMB ITEM VENTA": prod, "GRUPO": grupo,
                    "CLASE VENTA": clase})

    tarjeta = "Tarjeta de Crédito"
    pedido("1", "ANA", "CENA",
           [("I1", "Lomo", "Alimentos", 1, 100.0),
            ("I2", "Agua", "Bebidas s/ Alcohol", 2, 50.0)],
           [("P1a", tarjeta, 10.0), ("P1b", "Efectivo", None)], pax=2)
    pedido("2", "BETO", "CENA", [("I3", "Lomo", "Alimentos", 2, 200.0)],
           [("P2", tarjeta, 0.0)], pax=3)
    pedido("3", "ANA", "ALMUERZO", [("I4", "Ensalada", "Alimentos", 1, 80.0)],
           [("P3", "Efectivo", None)], pax=1, hora="2026-09-01 13:00")
    pedido("4", None, "CENA", [("I5", "Lomo", "Alimentos", 1, 60.0)],
           [("P4", tarjeta, 0.0)], pax=0)
    pedido("5", "BETO", "CENA", [("I6", "Postre", "Alimentos", 1, 90.0)],
           None, pax=2, clase="Cortesía")
    pedido("6", "CARLA", "CENA", [("I7", "Vino", "Vinos y Espumantes", 1,
                                   100.0)],
           [("P6", tarjeta, 10.0)], pax=2, hora="2026-09-02 00:04")
    d = pd.DataFrame(filas)

    P, items = _m.preparar(d)
    p = P.set_index("ped")
    check("un pedido por fila, sin la cortesía", sorted(p.index),
          ["1", "2", "3", "4", "6"])
    check("venta: un ítem una vez aunque se pagó con dos formas",
          float(p.loc["1", "venta"]), 150.0)
    check("productos del pedido 1", float(p.loc["1", "items"]), 3.0)
    check("propina: un pago una vez", float(p.loc["1", "propina"]), 10.0)
    check("tarjeta y efectivo: no es «sólo efectivo»",
          (bool(p.loc["1", "tarjeta"]), bool(p.loc["1", "solo_efectivo"])),
          (True, False))
    check("sólo efectivo", bool(p.loc["3", "solo_efectivo"]), True)
    check("personas una vez por pedido", float(p.loc["1", "personas"]), 2.0)
    check("sin mesero va a «Sin mesero»", p.loc["4", "mesero"], "Sin mesero")
    check("el nombre en Title Case", p.loc["2", "mesero"], "Beto")
    check("turno en Title Case", p.loc["3", "turno"], "Almuerzo")

    R = _m.resumen(P)
    check("resumen: columnas por nombre", list(R.columns), _m._COLS_RESUMEN)
    check("Ana: 2 mesas, 230 de venta, 10 de propina",
          (int(R.loc["Ana", "mesas"]), float(R.loc["Ana", "venta"]),
           float(R.loc["Ana", "propina"])), (2, 230.0, 10.0))
    check("Beto: una mesa con tarjeta sin propina (la cortesía no cuenta)",
          (int(R.loc["Beto", "mesas"]), int(R.loc["Beto", "sin_propina"])),
          (1, 1))
    check("Ana: una mesa pagada sólo en efectivo",
          int(R.loc["Ana", "solo_efectivo"]), 1)

    z = _m.pozo(P)
    check("el pozo no incluye a «Sin mesero»",
          "Sin mesero" in set(z["mesero"]), False)
    cena = z[(z["turno"] == "Cena") & (z["dia"] == pd.Timestamp("2026-09-01"))]
    check("cena del 1: el pozo (10 + 0) entre Ana y Beto",
          sorted((m, round(float(v), 2)) for m, v in zip(cena["mesero"],
                                                          cena["parte"])),
          [("Ana", 5.0), ("Beto", 5.0)])
    check("el pozo no pierde ni inventa un sol",
          round(float(z["parte"].sum()), 6), round(float(z["propia"].sum()), 6))
    rep = _m.reparto(P)
    check("Beto gana con el pozo lo que Ana cede",
          (round(float(rep.loc["Beto", "diferencia"]), 2),
           round(float(rep.loc["Ana", "diferencia"]), 2)), (5.0, -5.0))

    soles, mesas = _m.planilla(P)
    check("planilla: una fila por mesero, sin «Sin mesero»",
          sorted(soles.index), ["Ana", "Beto", "Carla"])
    check("planilla: Carla cobra el 2 (cobro pasada la medianoche)",
          float(soles.loc["Carla", pd.Timestamp("2026-09-02")]), 10.0)
    check("planilla propia suma la propina",
          round(float(soles.to_numpy().sum()), 6), 20.0)
    soles_p, _ = _m.planilla(P, _m.REPARTOS[1])
    check("planilla del pozo suma lo mismo",
          round(float(soles_p.to_numpy().sum()), 6), 20.0)

    D = _m.distribucion(P)
    check("tramos: columnas en orden", list(D.columns), list(_m.TRAMOS))
    check("6,7 % cae en «5 – 9 %», 0 % en «0 %», 10 % en «10 %»",
          (int(D.loc["Ana", "5 – 9 %"]), int(D.loc["Beto", "0 %"]),
           int(D.loc["Carla", "10 %"])), (1, 1, 1))

    check("se compara con los mismos días del mes anterior",
          _m.periodo_anterior(_d.date(2026, 9, 1), _d.date(2026, 9, 27)),
          (_d.date(2026, 8, 1), _d.date(2026, 8, 27)))
    check("un 31 cae en el último día del mes corto",
          _m.periodo_anterior(_d.date(2026, 3, 1), _d.date(2026, 3, 31)),
          (_d.date(2026, 2, 1), _d.date(2026, 2, 28)))
    check("un rango de dos meses: el tramo igual de largo de antes",
          _m.periodo_anterior(_d.date(2026, 8, 15), _d.date(2026, 9, 14)),
          (_d.date(2026, 7, 15), _d.date(2026, 8, 14)))
    hora = _m.hora_de_corte(P, _d.date(2026, 9, 2))
    check("el último día corta a la hora del último cobro",
          hora, pd.Timedelta(minutes=4))
    check("sin cobro en el último día, no corta",
          _m.hora_de_corte(P, _d.date(2026, 9, 3)), None)
    P0 = P.assign(cobro=P["cobro"] - pd.DateOffset(months=1))
    check("el mes anterior, hasta la misma hora",
          len(_m.hasta_la_misma_hora(P0, _d.date(2026, 8, 2), hora)), 5)
    check("…y lo que pasa de esa hora queda fuera",
          len(_m.hasta_la_misma_hora(
              P0.assign(cobro=P0["cobro"] + pd.Timedelta(hours=1)),
              _d.date(2026, 8, 2), hora)), 4)

    pagos = _m.pagos_con_propina(d)
    check("pagos con propina: los dos que dejaron",
          sorted(pagos["comprobante"]), ["B001-1", "B001-6"])
    xls = _m.excel("1 sep – 2 sep 2026", "Todo el día", _m.REPARTOS[0], R,
                   rep, soles, mesas, z, pagos)
    with zipfile.ZipFile(_io.BytesIO(xls)) as zf:
        libro = zf.read("xl/workbook.xml").decode("utf-8")
    check("el Excel trae sus cuatro hojas",
          all(h in libro for h in ("Resumen", "Planilla", "Por turno",
                                   "Pagos con propina")), True)
    check("columna de Excel 27 → AB", _m._col_xl(27), "AB")
    return fallos


def _pruebas_ventas_menu():
    """Ventas › Ingeniería de menú (regla #550): la clasificación.

    Fija lo que en pantalla se ve razonable aunque esté mal: que el margen
    promedio sea el PONDERADO por lo vendido (con el promedio simple, el
    Lomo de abajo sería caballo y no estrella), que la popularidad sea 70 %
    de 1/N, qué queda fuera y por qué, que un plato partido en dos
    subgrupos se cuente una vez, y la clase que tendría contado por
    pedidos.
    """
    import math

    from graficos import ventas_menu as _im
    from graficos import ventas_platos as _p

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ventas · menú · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ventas · menú · {nombre}: got={got!r} exp={exp!r}")

    def fila(prod, sub, cant, neto, costo, pedidos):
        return {"prod": prod, "grupo": "Alimentos", "sub": sub, "venta": neto,
                "cant": cant, "costo": costo, "neto": neto, "pedidos": pedidos}
    a = pd.DataFrame([
        fila("Lomo", "Fondos", 100, 5000.0, 500.0, 80),        # margen 45
        fila("Risotto", "Fondos", 80, 3200.0, 2000.0, 80),     # margen 15
        fila("Trapo 1kg", "Fondos", 10, 2400.0, 1000.0, 10),   # margen 140
        fila("Fideua", "Fondos", 5, 350.0, 250.0, 5),          # margen 20
        fila("Entraña", "Carnes", 60, 7200.0, 3300.0, 25),     # margen 65
        fila("Postre Cortesia", "Fondos", 13, 0.008, 100.0, 13),
        fila("Bourbon Sour", "Fondos", 2, 54.8, 529.4, 2),
        fila("Sin receta", "Fondos", 20, 400.0, 0.0, 20),
    ])
    subs = [("Alimentos", "Fondos"), ("Alimentos", "Carnes")]
    m, fuera, res = _im.clasificar(a, subs)
    check("N son los clasificables: 5", res["n"], 5)
    check("popular: 70 % de 1/N", round(res["umbral"], 6), round(0.70 / 5, 6))
    check("el margen promedio es el PONDERADO (11.100 / 255), no el simple (57)",
          round(res["acm"], 4), round(11100 / 255, 4))
    clases = dict(zip(m["prod"], m["clase"]))
    check("las cuatro clases", clases,
          {"Lomo": "estrella", "Risotto": "caballo", "Trapo 1kg": "rompecabezas",
           "Fideua": "perro", "Entraña": "estrella"})
    check("al límite: el Lomo, a 3,4 % del promedio",
          sorted(m.loc[m["al_limite"], "prod"]), ["Lomo"])
    check("contada por pedidos, la Entraña (2 por pedido) no sería popular",
          dict(zip(m["prod"], m["clase_ped"]))["Entraña"], "rompecabezas")
    check("fuera, con su motivo",
          {f["plato"]: f["motivo"] for f in fuera},
          {"Postre Cortesia": "cortesía a S/ 0",
           "Bourbon Sour": "cuesta más de lo que se cobra",
           "Sin receta": "sin costo cargado"})
    check("ordenada por el margen total que deja",
          list(m["prod"]), ["Lomo", "Entraña", "Trapo 1kg", "Risotto", "Fideua"])
    check("lo que deja cada clase",
          (res["clases"]["estrella"]["n"], res["clases"]["estrella"]["margen"]),
          (2, 8400.0))
    solo_fondos = _im.clasificar(a, [("Alimentos", "Fondos")])[2]
    check("la categoría es la que se arma: sin Carnes, 4 platos",
          solo_fondos["n"], 4)
    partido = pd.concat([a.head(1), a.head(1).assign(sub="Carnes")])
    check("un plato partido en dos subgrupos se cuenta una vez",
          _im.clasificar(partido, subs)[0]["u"].tolist(), [200.0])
    check("sin subgrupos no hay clasificación",
          _im.clasificar(a, [])[2], None)
    sin_ped = _im.clasificar(a.drop(columns=["pedidos"]), subs)[0]
    check("sin pedidos (modo demo): la clase por pedidos no existe",
          (sin_ped["clase_ped"].isna().all(), len(sin_ped)), (True, 5))
    check("las opciones de la categoría, de la que más vende a la que menos",
          _im.subgrupos(a), [("Alimentos", "Fondos"), ("Alimentos", "Carnes")])
    # El piso de la marca (2026-09-27): los tres dejan justo el promedio,
    # pero el que se vendió UNA vez no lleva «al límite».
    parejo = pd.DataFrame([
        fila("A", "Fondos", 100, 5000.0, 2000.0, 90),
        fila("B", "Fondos", 100, 4000.0, 1000.0, 90),
        fila("C", "Fondos", 1, 60.0, 30.0, 1)])
    m_p, _f, r_p = _im.clasificar(parejo, [("Alimentos", "Fondos")])
    check("«al límite» sólo desde la mitad de lo que pide la popularidad",
          sorted(m_p.loc[m_p["al_limite"], "prod"]), ["A", "B"])
    check("y la línea de los umbrales dice desde cuántas unidades",
          r_p["piso_limite_u"], math.ceil(0.5 * (0.70 / 3) * 201))
    casi = pd.DataFrame({"prod": ["Lomo Saltado", "Lomo a la Pimienta", "Borde"],
                         "mm": [0.116, 0.114, 0.129], "margen": [36.41, 36.51, 80.0]})
    pos = _im.rotulos(casi, 0.13, 150.0, 330, list(casi["prod"]))
    check("dos platos casi en el mismo punto no se pisan el nombre",
          "Lomo Saltado" in pos and pos.get("Lomo a la Pimienta") != pos["Lomo Saltado"],
          True)
    check("contra el borde derecho, el nombre no se sale hacia la derecha",
          pos.get("Borde") != "middle right", True)
    check("abre en Cuadros, y las tres formas se alternan",
          (_im._FORMA_DEFAULT, _im.FORMAS), ("Cuadros", ("Cuadros", "Matriz", "Tabla")))
    check("sus controles sobreviven al salto a «Por hora» (#373)",
          all(k in _p._KEYS_WIDGET_PL for k in _im._KEYS_WIDGET_MENU), True)
    return fallos


def _pruebas_por_hora_filas():
    """Ventas › Por hora: las filas «Platos» y «Grupos» (regla #530).

    Fija las cuentas que no se ven hasta que mienten: que la matriz ponga
    cada venta en SU hora (en orden de servicio) o en su día de semana, que
    «Por día» divida por los días CON VENTA —o por cuántos lunes, martes…
    tuvo el período—, que las filas sean los platos del período MÁS NUEVO
    (las mismas en todos los paneles, o la diferencia restaría platos
    distintos), y el signo de la resta.
    """
    from graficos import ventas_horario as _h

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    por hora · filas · {nombre}")
        else:
            fallos += 1
            print(f"FALLA por hora · filas · {nombre}: got={got!r} exp={exp!r}")

    # Lunes 3 y martes 4 de agosto de 2026; el 0 es la medianoche.
    t = pd.DataFrame({
        "hora": [13, 20, 20, 0, 13],
        "dow": [0, 0, 1, 1, 1],
        "dia": pd.to_datetime(["2026-08-03", "2026-08-03", "2026-08-04",
                               "2026-08-04", "2026-08-04"]),
        "prod": ["Lomo", "Lomo", "Lomo", "Pisco", "Pisco"],
        "grupo": ["Alimentos", "Alimentos", "Alimentos", "Bebidas",
                  "Bebidas"],
        "venta": [100.0, 60.0, 40.0, 30.0, 10.0],
        "cant": [2.0, 1.0, 1.0, 3.0, 1.0], "desc": 0.0,
    })
    horas = [13, 20, 0]
    m = _h._matriz_filas(t, "prod", ["Lomo", "Pisco"], True, "venta", horas,
                         False)
    check("cada venta en su hora, en orden de servicio",
          m.tolist(), [[100.0, 100.0, 0.0], [10.0, 0.0, 30.0]])
    m = _h._matriz_filas(t, "prod", ["Lomo", "Pisco"], True, "venta", horas,
                         True)
    check("«Por día» divide por los dos días con venta",
          m.tolist(), [[50.0, 50.0, 0.0], [5.0, 0.0, 15.0]])
    m = _h._matriz_filas(t, "prod", ["Lomo"], False, "venta", horas, True)
    check("por día de semana: lunes y martes, uno de cada uno",
          m.tolist()[0][:3], [160.0, 40.0, 0.0])
    viejo = t.assign(prod="Ceviche")
    check("las filas son los platos del período MÁS NUEVO",
          _h._items_filas([viejo, t], "prod"), ["Lomo", "Pisco"])
    check("la resta lleva su signo", (_h._fmt_delta(-1240.0, "venta"),
                                      _h._fmt_delta(3.0, "cant")),
          ("−S/ 1,240", "+3"))
    check("Pax y Ticket no son medidas de las filas",
          set(_h._MED_FILAS) & {"pax", "ticket"}, set())
    return fallos


def _pruebas_ficha_hora():
    """Ventas › Por hora: la ficha que abre un CLIC en una celda (regla #536).

    Fija lo que no se ve hasta que miente: qué es una MESA (un pedido del
    local con personas: ni Rappi, ni Venta Interna, ni sin personas), que
    las cadenas cierren (mesas × venta por mesa = venta en mesas), que las
    mesas abiertas se cuenten con el cobro como cierre y crucen la
    medianoche, que un clic se distinga de un arrastre, y que el mapa siga
    dando el hover de los números en su PRIMERA capa con hover.
    """
    import datetime as _dt

    from graficos import ventas_ficha_hora as _f
    from graficos import ventas_horario as _h
    from tema import TEXTO_PRINCIPAL

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    ficha hora · {nombre}")
        else:
            fallos += 1
            print(f"FALLA ficha hora · {nombre}: got={got!r} exp={exp!r}")

    ts = pd.Timestamp
    # Sábado 5 de septiembre de 2026, 7 pm: dos mesas, una Venta Interna,
    # un Rappi, un pedido sin personas y uno olvidado abierto 8 horas.
    d = pd.DataFrame({
        "PED": ["M1", "M1", "M2", "VI", "RP", "SP", "OL", "M9"],
        "ABRE": [ts("2026-09-05 19:05"), ts("2026-09-05 19:05"),
                 ts("2026-09-05 19:40"), ts("2026-09-05 19:50"),
                 ts("2026-09-05 19:10"), ts("2026-09-05 19:20"),
                 ts("2026-09-05 19:30"), ts("2026-08-29 19:15")],
        "COBRO": [ts("2026-09-05 21:05"), ts("2026-09-05 21:05"),
                  ts("2026-09-05 20:40"), ts("2026-09-05 19:52"),
                  ts("2026-09-05 19:40"), ts("2026-09-05 19:30"),
                  ts("2026-09-06 03:40"), ts("2026-08-29 20:45")],
        "VENTA": [300.0, 100.0, 200.0, 1500.0, 80.0, 25.0, 90.0, 150.0],
        "PAX": [4, 4, 2, 0, 1, 0, 2, 3],
        "CANT": [1.0, 2.0, 1.0, 80.0, 1.0, 1.0, 1.0, 1.0],
        "PROD": ["Lomo", "Pisco", "Ceviche", "Chorizo", "Lomo", "Café",
                 "Pisco", "Lomo"],
        "GRUPO": ["Alimentos", "Bebidas", "Alimentos", "Venta Interna",
                  "Alimentos", "Bebidas", "Bebidas", "Alimentos"],
        "Nombre Mesero": ["MESERO UNO", "MESERO UNO", "MESERA DOS", "", "", "",
                          "MESERA DOS", "MESERA DOS"],
        "Canal Venta": ["En el Local", "En el Local", "En el Local",
                        "En el Local", "Rappi", "En el Local",
                        "En el Local", "En el Local"],
    })
    c = {"tiempo": "ABRE", "apertura": "ABRE", "cobro": "COBRO",
         "venta": "VENTA", "pax": "PAX", "pedido": "PED", "prod": "PROD",
         "cant": "CANT", "grupo": "GRUPO"}
    fl = _f.filas(d, c)
    peds = _f.pedidos(fl).set_index("ped")
    check("una mesa es un pedido del local con personas y venta",
          sorted(peds.index[peds["mesa"]]), ["M1", "M2", "M9", "OL"])
    check("la Venta Interna, Rappi y sin personas no son mesa",
          sorted(peds.index[~peds["mesa"]]), ["RP", "SP", "VI"])
    check("un pedido abierto más de 6 h no tiene duración",
          bool(pd.isna(peds.loc["OL", "min"])), True)
    check("la duración va del pedido al último cobro",
          float(peds.loc["M1", "min"]), 120.0)

    pc, items = _f.de_la_celda(fl, _f.pedidos(fl), "2026-09-05", 19,
                               con_items=True)
    check("los pedidos de la celda, del más grande al más chico",
          list(pc["ped"]), ["VI", "M1", "M2", "OL", "RP", "SP"])
    check("la venta de la celda es la de sus pedidos",
          float(pc["v"].sum()), 2295.0)
    check("lo que pidió cada uno, del más caro al más barato",
          [p for p, _c, _v in items["M1"]], ["Lomo", "Pisco"])
    m = _f.metricas(pc)
    check("mesas de la celda (la del 29 es de otra celda)", m["mesas"], 3)
    check("la cadena cierra: mesas × venta por mesa = venta en mesas",
          round(m["mesas"] * m["vxm"], 6), round(m["v"], 6))
    check("y venta por mesa = personas por mesa × gasto por persona",
          round(m["pxm"] * m["gxp"], 6), round(m["vxm"], 6))
    check("la venta por hora de mesa sólo cuenta mesas con duración",
          round(m["vxh"], 4), round(600.0 / 3.0, 4))

    ini, fin = _f.intervalos(_f.pedidos(fl))
    check("mesas abiertas a las 7:45 (M1 y M2; OL no tiene duración)",
          int(_f.abiertas(ini, fin, [ts("2026-09-05 19:45")])[0]), 2)
    check("el cobro cierra: a las 8:40 M2 ya no cuenta",
          int(_f.abiertas(ini, fin, [ts("2026-09-05 20:40")])[0]), 1)
    check("lo más abierto entre las 7 y las 8",
          _f.pico(ini, fin, ts("2026-09-05 19:00"), ts("2026-09-05 20:00")),
          2)

    horas = [12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 0]
    check("el servicio es el tramo sin huecos", _f.bloque(horas, 20),
          [18, 19, 20, 21, 22, 23, 0])
    check("el almuerzo, aparte", _f.bloque(horas, 13), [12, 13, 14, 15, 16])
    t0, t1, h0, h1 = _f.ventana_servicio("2026-09-06", horas, 0)
    check("las 12 am del 6 son el final de la cena del 5",
          (t0, h0), (ts("2026-09-05 17:30"), ts("2026-09-06 00:00")))
    check("y la línea sigue una hora después de la última",
          t1, ts("2026-09-06 02:00"))

    check("la frase: la más alta",
          _f.frase_normal(500.0, [100.0, 200.0], 5, 19),
          "La más alta de 3 sábados a las 7 pm")
    check("la frase: la 2.ª, y «a la 1 pm»",
          _f.frase_normal(150.0, [100.0, 200.0], 0, 13),
          "La 2.ª más alta de 3 lunes a la 1 pm")
    check("la frase: nadie vendió",
          _f.frase_normal(0.0, [0.0, 0.0], 2, 16),
          "Ni esta ni las 2 semanas anteriores vendieron a las 4 pm")
    # En la fila de Venta · Pax · Ticket va SIN la hora (2026-10-04): ya
    # está en el título de al lado, y con ella la fila no entraba.
    check("la frase corta, sin la hora",
          (_f.frase_normal(150.0, [100.0, 200.0], 4, 22, con_hora=False),
           _f.frase_normal(0.0, [0.0, 0.0], 6, 23, con_hora=False)),
          ("La 2.ª más alta de 3 viernes", "Ningún domingo vendió en 2 semanas"))
    # El resultado contra lo normal, junto al título: en lugar del rótulo
    # «CONTRA LO NORMAL», que no decía nada.
    check("el resultado: sube, baja, igual",
          [_f.veredicto_normal(v, [100.0, 100.0, 120.0])
           for v in (186.0, 82.0, 102.0)],
          [("▲ 86% vs lo normal", "sube"), ("▼ 18% vs lo normal", "baja"),
           ("≈ lo normal", "neutro")])
    check("el resultado: sin semanas o sin ventas, nada que decir",
          (_f.veredicto_normal(50.0, []), _f.veredicto_normal(0.0, [0.0, 0.0])),
          (None, None))
    check("el resultado: vendió donde lo normal es no vender",
          _f.veredicto_normal(300.0, [0.0, 0.0, 50.0]),
          ("▲ lo normal: sin ventas", "sube"))
    check("la ventana trae 8 semanas antes y un día después",
          _f.ventana(_dt.date(2026, 9, 1), _dt.date(2026, 9, 24)),
          (_dt.date(2026, 7, 7), _dt.date(2026, 9, 25)))

    # El clic que trae el puente de JS contra un arrastre sobre una celda.
    clic = {"selection": {"points": [{"customdata": [0, 4, 19, "clic",
                                                      1727380000000]}],
                          "box": [], "lasso": []}}
    caja = {"selection": {"points": [{"customdata": [0, 4, 19]}],
                          "box": [{"x": [3.6, 4.4], "y": [5.6, 6.4]}],
                          "lasso": []}}
    check("un clic se reconoce con su sello",
          _h._clic_de_evento(clic), (0, 4, 19, 1727380000000))
    check("un arrastre no es un clic", _h._clic_de_evento(caja), None)
    check("un arrastre sigue dando sus puntos para la marca",
          _h._puntos_de_evento(caja), [(0, 4, 19)])
    check("el puente reenvía el clic como selección",
          all(x in _h._JS_CLIC_MAPA for x in
              ("plotly_click", "plotly_selected", '"clic"', "__vhClicApagar")),
          True)

    # El mapa con la celda del clic: su borde oscuro, y el hover de los
    # números sigue en la primera capa con hover (la de celdas vacías va
    # después).
    celdas = pd.DataFrame({"col": [0, 1], "hora": [19, 21],
                           "venta": [100.0, 200.0], "cant": [3.0, 5.0],
                           "desc": [0.0, 0.0], "pax": [2.0, 4.0],
                           "ticket": [50.0, 50.0], "raro": [0.0, 80.0]})
    fig = _h._fig_mapa([celdas], [(2026, 32)], "Semana", "venta", [],
                       [19, 21], foco={"sel": 0, "c": 1, "h": 21})
    bordes = [s for s in fig.layout.shapes
              if s.type == "rect" and s.line.color == TEXTO_PRINCIPAL]
    check("la celda del clic lleva su borde", len(bordes), 1)
    hov = [t for t in fig.data if t.type == "scatter" and t.hoverinfo != "skip"]
    check("la primera capa con hover es la de los números",
          len(hov[0].x) if hov else 0, 2)
    check("las celdas vacías también tienen hover (para el clic)",
          len(hov[1].x) if len(hov) > 1 else 0, 7 * 2 - 2)
    check("la Venta Interna o Eventos de la celda sale en el tooltip",
          "Venta Interna" in (hov[0].customdata[1][9] if hov else ""), True)
    # Desde la regla #610 es un punto naranja en la esquina, medido en
    # píxeles (antes, un triángulo que se leía como una salpicadura).
    from tema import ADVERTENCIA as _NAR
    tri = [s for s in fig.layout.shapes
           if s.type == "circle" and s.fillcolor == _NAR]
    check("y su celda lleva el punto naranja", len(tri), 1)
    check("medido en píxeles desde la esquina",
          (tri[0].xsizemode, tri[0].ysizemode) if tri else None,
          ("pixel", "pixel"))
    sin = _h._fig_mapa([celdas], [(2026, 32)], "Semana", "venta", [],
                       [19, 21], raros=False)
    check("con el interruptor apagado no hay punto naranja",
          len([s for s in sin.layout.shapes
               if s.type == "circle" and s.fillcolor == _NAR]), 0)
    return fallos


def _pruebas_por_hora_semana_y_desliza():
    """Ventas › Por hora: las dos formas de columnas de «Días × horas» y el
    mapa deslizable (regla #551).

    «Por día de semana» pinta PROMEDIOS: cada celda es la suma dividida por
    los días de ese día de la semana que vendieron algo, a cualquier hora, y
    la lista que abre su clic tiene que dar el mismo promedio — si no, la
    celda y la lista dicen dos cosas. El deslizable son dos figuras (el mapa
    y su eje de horas) que tienen que coincidir fila por fila sin que el
    navegador mida nada: mismo alto, mismos márgenes de arriba y abajo,
    mismo rango del eje Y.

    Todo por NOMBRE de columna (CLAUDE.md: pandas 3 acá, 2.2 en Cloud).
    """
    import datetime as _dt

    from graficos import ventas_horario as _h

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    por hora · semana · {nombre}")
        else:
            fallos += 1
            print(f"FALLA por hora · semana · {nombre}: got={got!r} exp={exp!r}")

    # Septiembre 2026: sábados 5, 12, 19 y 26; el 19 sólo vendió al
    # almuerzo, el 26 no vendió. Un domingo, el 6.
    ts = pd.Timestamp
    d = pd.DataFrame({
        "FECHA": [ts("2026-09-05 19:10"), ts("2026-09-05 19:10"),
                  ts("2026-09-12 19:40"), ts("2026-09-19 13:00"),
                  ts("2026-09-06 20:00")],
        "VENTA": [300.0, 100.0, 200.0, 90.0, 50.0],
        "PAX": [4, 4, 2, 3, 1],
        "PED": ["P1", "P1", "P2", "P3", "P4"],
    })
    c = {"fecha": "FECHA", "venta": "VENTA", "pax": "PAX", "pedido": "PED"}
    ini, fin = _dt.date(2026, 9, 1), _dt.date(2026, 9, 30)
    t = _h._prep_tramo(d, c, "Mes", ini, fin, semanal=True)
    check("la columna es el día de la semana (0 = lunes)",
          sorted(set(zip(t["dia"].dt.day, t["col"]))),
          [(5, 5), (6, 6), (12, 5), (19, 5)])
    g = _h._celdas(t, promedio=True).set_index(["col", "hora"])
    check("sábado 7 pm: 600 entre los 3 sábados que vendieron",
          round(float(g.loc[(5, 19), "venta"]), 6), 200.0)
    check("el almuerzo del 19 hace que ese sábado cuente",
          round(float(g.loc[(5, 13), "venta"]), 6), 30.0)
    check("el pax también es por día (un valor por pedido)",
          round(float(g.loc[(5, 19), "pax"]), 6), 2.0)
    check("el ticket no cambia al promediar",
          round(float(g.loc[(5, 19), "ticket"]), 6), round(600.0 / 6.0, 6))
    s_ = _h._celdas(t).set_index(["col", "hora"])
    check("sin promedio, la suma de siempre",
          float(s_.loc[(5, 19), "venta"]), 600.0)

    filas_, prom, n = _h._dias_de_la_celda(t, 5, 19, ini, fin)
    check("la lista trae todos los sábados del mes",
          [f.day for f, *_ in filas_], [5, 12, 19, 26])
    check("con su venta a esa hora",
          [v for _, v, _, _ in filas_], [400.0, 200.0, 0.0, 0.0])
    check("y sus pedidos", [p for *_, p in filas_], [1, 1, 0, 0])
    check("el promedio de la lista es el de la celda",
          round(prom, 6), round(float(g.loc[(5, 19), "venta"]), 6))
    check("y su divisor, los sábados que vendieron", n, 3)
    check("sin tramo, la lista sale en cero",
          _h._dias_de_la_celda(None, 5, 19, ini, fin)[1:], (0.0, 0))

    check("una marca por día de semana se rotula con sus días",
          _h._etiqueta_columnas({"sem": True, "c0": 4, "c1": 6}, (2026, 9),
                                "Mes"), "Vie–Dom")
    check("el mapa por día de semana tiene 7 columnas",
          _h._columnas_mapa((2026, 9), "Mes", semanal=True)[0], 7)

    # El deslizable: 1 mes entra, 2 no.
    claves = [(2026, 8), (2026, 9)]
    ancla = _dt.date(2026, 9, 27)
    tot = _h._total_columnas(claves, "Mes", ancla)
    check("agosto + 27 días de septiembre + el hueco", tot, 31 + 27 + 1)
    check("un mes no desliza",
          _h._total_columnas([(2026, 9)], "Mes", ancla)
          > _h._MAX_COLS_SIN_DESLIZAR, False)
    check("dos meses sí", tot > _h._MAX_COLS_SIN_DESLIZAR, True)
    check("por día de semana nunca: 7 columnas por panel",
          _h._total_columnas(claves, "Mes", ancla, semanal=True), 15)
    check("24 px por columna más los márgenes",
          _h._ancho_desliza(tot), 4 + 10 + 59 * 24)

    celdas = pd.DataFrame({"col": [0, 3], "hora": [19, 21],
                           "venta": [100.0, 200.0], "cant": [3.0, 5.0],
                           "desc": [0.0, 0.0], "pax": [2.0, 4.0],
                           "ticket": [50.0, 50.0], "raro": [0.0, 0.0]})
    horas = [13, 19, 21]
    alto = 300
    fig = _h._fig_mapa([celdas, celdas], claves, "Mes", "venta", [], horas,
                       ancla=ancla, alto=alto, desliza=True)
    eje = _h._fig_eje_horas(horas, alto, _h._margen_arriba(len(claves)))
    check("la figura mide lo que pide el deslizable",
          fig.layout.width, _h._ancho_desliza(tot))
    check("el mapa no dibuja sus horas (las dibuja el eje)",
          fig.layout.yaxis.showticklabels, False)
    check("ni la barra de colores, que se iría con el scroll",
          [tr.showscale for tr in fig.data if tr.type == "heatmap"],
          [False] * len([tr for tr in fig.data if tr.type == "heatmap"]))
    check("mismo alto", eje.layout.height, fig.layout.height)
    check("mismo margen de arriba", eje.layout.margin.t, fig.layout.margin.t)
    check("mismo margen de abajo", eje.layout.margin.b, fig.layout.margin.b)
    check("mismo rango del eje Y, fijo",
          (tuple(eje.layout.yaxis.range), eje.layout.yaxis.autorange),
          (tuple(fig.layout.yaxis.range), fig.layout.yaxis.autorange))
    check("y las mismas horas, en el mismo orden",
          list(eje.data[0].y), [_h._etiqueta_hora(x) for x in horas])
    # Con los totales al margen (regla #610) las filas del mapa dejan abajo
    # la tira de totales: el eje de al lado tiene que dejarla también, o
    # cada hora cae sobre la fila de otra.
    fig_t = _h._fig_mapa([celdas, celdas], claves, "Mes", "venta", [], horas,
                         ancla=ancla, alto=alto, desliza=True, totales=True)
    eje_t = _h._fig_eje_horas(horas, alto,
                              _h._margen_arriba(len(claves), True),
                              totales=True)
    check("con totales, el eje y el mapa reparten igual las filas",
          (tuple(eje_t.layout.yaxis.domain), eje_t.layout.margin.t),
          (tuple(fig_t.layout.yaxis.domain), fig_t.layout.margin.t))
    check("y el mapa mide lo que pide el deslizable con totales",
          fig_t.layout.width, _h._ancho_desliza(tot, True))
    sin = _h._fig_mapa([celdas], [(2026, 9)], "Mes", "venta", [], horas,
                       ancla=ancla, alto=alto)
    check("sin deslizar el mapa sigue rotulando sus horas",
          sin.layout.yaxis.showticklabels is not False, True)
    check("el puente de JS lleva el mapa al final sólo si cambió",
          all(x in _h._JS_CLIC_MAPA for x in
              ("st-key-vh_desliza", "data-firma", "scrollLeft")), True)

    # El CSS del deslizable: adentro del `:has()`, una clase sola (#469).
    from estilos._80_cards import CSS as _css
    check("el deslizable se prende por la clase del eje",
          ".st-key-vh_desliza:has(.st-key-vh_eje_horas)" in _css, True)

    # La franja de la hora (regla #554): la fila bajo el cursor se enmarca
    # con un <div> del puente de JS, no con el spike de Plotly (una línea
    # punteada por el medio de la fila, encima del color de las celdas).
    check("el mapa ya no dibuja el spike de Plotly",
          bool(sin.layout.yaxis.showspikes), False)
    check("el puente enmarca la fila con el cursor",
          all(x in _h._JS_CLIC_MAPA for x in
              ("plotly_hover", "plotly_unhover", "vh-franja-hora",
               "vh-hora-activa", "vh_eje_horas")), True)
    check("el marco le gana al `border: 0` de Plotly",
          ".js-plotly-plot .plotly div.vh-franja-hora" in _css, True)
    check("y la hora activa, al `fill` inline de Plotly",
          ".ytick text.vh-hora-activa" in _css, True)
    return fallos


def _pruebas_cabecera_por_hora():
    """Ventas › Por hora: la cabecera como tabla dinámica (regla #555).

    Lo que no se ve hasta que miente: que una opción que no aplica REBOTE y
    diga por qué en vez de quedar elegida; que lo elegido sobreviva a que
    su botonera no se dibuje o no aplique (la sombra); que «Diferencia» se
    apague sólo cuando no se puede; y que los dos controles que viven en el
    popover de «Ajustes» no se monten con su default y pisen lo elegido
    (#467). Sin navegador: se reemplaza `st` por uno de mentira.
    """
    import pathlib
    import types

    from graficos import ventas_horario as _h
    from graficos import ventas_platos as _vp

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    cabecera por hora · {nombre}")
        else:
            fallos += 1
            print(f"FALLA cabecera por hora · {nombre}: got={got!r} exp={exp!r}")

    check("los nombres de tabla dinámica",
          (_h._FILAS, _h._COLS_DIAS, _h._COLS_FILAS, _h._ESCALAS),
          (("Horas", "Platos", "Grupos", "Áreas"), ("Fecha", "Día de semana"),
           ("Hora", "Día de semana"), ("Total", "Por día")))
    check("«Cantidad» se llama «Unidades»", dict(_h._MEDIDAS)["cant"],
          "Unidades")

    md = _h._motivo_diferencia
    check("Diferencia con un panel no se puede",
          "uno solo" in md(1, False, False, "Semana"), True)
    check("ni en Mes por fecha (el 1 no es el mismo día de semana)",
          md(2, False, False, "Mes").startswith("En Mes"), True)
    check("en Mes por día de semana sí", md(2, False, True, "Mes"), "")
    check("con filas Platos, en Mes también", md(2, True, False, "Mes"), "")
    check("en Semana sí", md(2, False, False, "Semana"), "")

    # `st` de mentira: el estado es un dict y `st.selectbox` anota lo que
    # recibe (desde el 2026-09-29 la cabecera son desplegables).
    real, llamadas = _h.st, []
    falso = types.SimpleNamespace(
        session_state={},
        selectbox=lambda *a, **k: llamadas.append((a, k)))
    _h.st = falso
    try:
        ss = falso.session_state
        ss["w"] = "Pax"
        _h._al_elegir("w", "_w", {"Pax": "Pax es del pedido."})
        check("un toque en lo que no aplica deja el motivo",
              (ss.get(_h._K_MOTIVO), ss.get("_w")),
              ("Pax es del pedido.", None))
        ss.pop(_h._K_MOTIVO)
        ss["w"] = "Unidades"
        _h._al_elegir("w", "_w", {"Pax": "x"})
        check("lo que aplica se guarda en la sombra", ss.get("_w"), "Unidades")
        ss["w"] = None
        _h._al_elegir("w", "_w", {})
        check("soltar la opción no borra lo elegido", ss.get("_w"), "Unidades")

        ss["_m"] = "Pax"
        v = _h._pastillas("Valor", ["Venta", "Pax", "Unidades", "Ticket"],
                          "m", "_m", "Venta", {"Pax": "a", "Ticket": "b"},
                          ancho=110)
        check("lo elegido que no aplica se ve como la primera que sí",
              (v, ss["m"]), ("Venta", "Venta"))
        check("y la sombra lo recuerda para cuando vuelva a aplicar",
              ss["_m"], "Pax")
        _fmt = llamadas[-1][1]["format_func"]
        check("lo que no aplica se marca en la lista",
              [_fmt(o) for o in ("Venta", "Pax")],
              ["Venta", "Pax" + _h._NO_APLICA])
        check("el desplegable no recibe `index=` (lo pone la sombra)",
              "index" in llamadas[-1][1], False)
        check("y lleva su ancho", llamadas[-1][1].get("width"), 110)
        v = _h._pastillas("Escala", ["Total", "Por día"], "e", "_e", "Por día",
                          {"Total": "x", "Por día": "x"}, forzado="Total")
        check("«forzado» manda aunque las dos no apliquen", v, "Total")
        ss.pop("_e", None)
        v = _h._pastillas("Escala", ["Total", "Por día"], "e", "_e", "Por día")
        check("sin sombra, el default", v, "Por día")
    finally:
        _h.st = real

    src = pathlib.Path(_h.__file__).read_text(encoding="utf-8")
    check("el interruptor de Ajustes lleva su valor en `value=` (#467)",
          "value=bool(st.session_state.get(_K_RAROS_VALOR, True))" in src,
          True)
    check("y Python no le escribe la key",
          "setdefault(\n                        _K_RAROS" in src
          or "session_state[_K_RAROS] =" in src, False)
    vp = pathlib.Path(_vp.__file__).read_text(encoding="utf-8")
    check("«Ver a qué hora se vende» deja la columna en su sombra",
          'ss["_vh_op_cols_valor"] = "Hora"' in vp
          and "Hora" in _h._COLS_FILAS, True)

    from estilos._80_cards import CSS as _css
    check("los rótulos de la cabecera",
          all(f'content: "{x}"' in _css
              for x in ("Filas", "Columnas", "Valor", "Un panel por")), True)
    check("el rótulo es el ::before y el separador el ::after",
          ".st-key-vh_cab_filas::before" in _css
          and ".st-key-vh_cab_cols::after" in _css, True)

    # «Promedio por día» en el hover sólo si la celda ES un promedio.
    celdas = pd.DataFrame({"col": [5], "hora": [19], "venta": [100.0],
                           "cant": [3.0], "desc": [0.0], "pax": [2.0],
                           "ticket": [50.0], "raro": [0.0]})
    import datetime as _dt
    for prom in (True, False):
        fig = _h._fig_mapa([celdas], [(2026, 9)], "Mes", "venta", [], [19],
                           ancla=_dt.date(2026, 9, 27), semanal=True,
                           promedio=prom)
        hov = [t for t in fig.data
               if t.type == "scatter" and t.hoverinfo != "skip"]
        check(f"el hover dice «promedio» sólo si lo es ({prom})",
              "promedio por día" in hov[0].customdata[0][8], prom)
    return fallos


def _pruebas_movimientos_periodo():
    """Movimientos › las tarjetas «por período» (graficos/movimientos_periodo.py).

    Desde el 2026-09-30 son cuatro: la de PRODUCCIÓN no suma las órdenes
    generadas aunque tengan líneas (regla #575).

    Lo que fija son las CUENTAS de las reglas #508 y #509, que son las que se
    leen distinto de lo que parecen: un documento es un CÓDIGO y no una fila;
    los anulados no suman pero se cuentan (y se listan en el Detalle); el
    documento sin ítems —una línea sin producto ni valor, el 15 % de los
    requerimientos del histórico— no cuenta ni como documento ni como
    línea; la barra se parte en las tres áreas mayores y «Resto», y cierra
    con el total; el color sigue al área aunque el filtro cambie quién es la
    mayor. Y el lado de SALIDAS: el mismo código con otro género
    («anulada»), el tipo de descargo en el Detalle, el precio unitario
    despejado de la línea y la salida sin procesar, que no tiene ítems.

    Todo por NOMBRE de columna, no por posición (CLAUDE.md: acá corre
    pandas 3 y en Cloud la 2.2).
    """
    import datetime as dt

    from graficos import alturas
    from graficos.compras._comun import _periodo_serie
    import pathlib

    from graficos import movimientos_periodo as mp
    from tema import (
        GRIS_TEXTO_SUAVE, PALETA_SERIES, SERIE_PRINCIPAL, SERIE_TRAMOS,
    )

    fallos = 0

    def check(nombre, got, exp):
        nonlocal fallos
        if got == exp:
            print(f"OK    movimientos por período · {nombre}")
        else:
            fallos += 1
            print(f"FALLA movimientos por período · {nombre}: "
                  f"got={got!r} exp={exp!r}")

    # ── REQUERIMIENTOS ────────────────────────────────────────────────────
    # Semana 37 (7-13 set 2026): R1 de Cocina con dos líneas, R2 de
    # Producción, R3 de Cocina ANULADO (con valor: no todos valen 0), R4 de
    # Gastos SIN ÍTEMS y R8, anulado Y sin ítems (cuenta como anulado, una
    # sola vez). Semana 38 (14-20 set): R5 de Barra sin procesar (estado
    # Generado, CON ítems: suma), R6 de Cava y R7 de Salón.
    d = pd.DataFrame({
        "FECHA REGISTRO": pd.to_datetime(
            ["2026-09-07 10:00", "2026-09-07 10:00", "2026-09-08 11:00",
             "2026-09-09 12:00", "2026-09-10 09:00", "2026-09-15 08:00",
             "2026-09-16 08:00", "2026-09-16 09:30", "2026-09-11 10:00"]),
        "COD REQUERIMIENTO": ["R1", "R1", "R2", "R3", "R4", "R5", "R6", "R7",
                              "R8"],
        "SUB ALMACEN": ["COCINA", "COCINA", "PRODUCCION", "COCINA", "GASTOS",
                        "BARRA", "CAVA ", "SALON", "GASTOS"],
        "NOMBRE ESTADO REQUERIMIENTO": ["PROCESADO", "PROCESADO", "PROCESADO",
                                        "ANULADO", "PROCESADO", "GENERADO",
                                        "PROCESADO", "PROCESADO", "ANULADO"],
        "NOMBRE FAMILIA": ["ALIMENTOS"] * 4 + [None, "BEBIDAS", "BEBIDAS",
                                               "ALIMENTOS", None],
        "NOMBRE PRODUCTO": ["A", "B", "C", "A", None, "D", "E", "F", None],
        "CANTIDAD": [1.0, 2.0, 3.0, 1.0, None, 4.0, 1.0, 0.5, None],
        "PRECIO UNIT": [100.0, 25.0, 100.0, 20.0, None, 10.0, 10.0, 10.0,
                        None],
        "VALOR ITEM": [100.0, 50.0, 300.0, 20.0, None, 40.0, 10.0, 5.0, None],
    })
    cols = dict(fecha="FECHA REGISTRO", doc="COD REQUERIMIENTO",
                area="SUB ALMACEN", estado="NOMBRE ESTADO REQUERIMIENTO",
                fam="NOMBRE FAMILIA", prod="NOMBRE PRODUCTO", cant="CANTIDAD",
                punit="PRECIO UNIT", val="VALOR ITEM")

    base = mp.lineas_documentos(d, **cols)
    check("las líneas sin producto son las de los documentos sin ítems",
          sorted(base.loc[base["vacio"], "doc"]), ["R4", "R8"])
    check("el área se limpia (el ERP deja espacios: «CAVA »)",
          sorted(set(base["area"])),
          ["BARRA", "CAVA", "COCINA", "GASTOS", "PRODUCCION", "SALON"])

    bl = base.copy()
    bl["clave"] = _periodo_serie(bl["fecha"], "Semana")
    res = mp.resumen_por_periodo(bl)
    check("un período por semana, en orden", res.index.tolist(),
          ["2026-S37", "2026-S38"])
    check("semana 37: sin anulados ni vacíos; los dos anulados se cuentan",
          res.loc["2026-S37", ["valor", "lineas", "docs", "areas",
                               "anulados", "sin_procesar"]].tolist(),
          [450.0, 3, 2, 2, 2, 0])
    check("semana 38: el Generado con ítems suma y se cuenta «sin procesar»",
          res.loc["2026-S38", ["valor", "lineas", "docs", "areas",
                               "anulados", "sin_procesar"]].tolist(),
          [55.0, 3, 3, 3, 0, 1])
    check("lo que no suma, contado una vez: 2 anulados, 0 sin procesar, "
          "1 sin ítems", mp.no_suman(bl), (2, 0, 1))
    check("la nota de la KPI nombra los dos",
          mp.nota_no_suman(bl, mp.REQUERIMIENTOS)[0],
          "2 anulados · 1 sin ítems")
    check("con familia o producto puestos, los vacíos no se nombran",
          mp.nota_no_suman(bl, mp.REQUERIMIENTOS,
                           vacios_nombrables=False)[0], "2 anulados")

    orden = ["COCINA", "PRODUCCION", "GASTOS", "BARRA", "CAVA", "SALON"]
    rango = (dt.date(2026, 9, 7), dt.date(2026, 9, 20))
    v = mp.vista_periodos(bl, "Semana", rango, orden, mp.REQUERIMIENTOS)
    tr = v["trazas"]
    check("tramos: las 3 áreas mayores de la VISTA y «Resto»",
          [t[0] for t in tr], ["PRODUCCION", "COCINA", "BARRA", "Resto"])
    check("«Resto» junta Cava y Salón, y el color es el gris",
          (tr[-1][2], tr[-1][1]), ([0.0, 15.0], GRIS_TEXTO_SUAVE))
    check("cada barra cierra con su total",
          [round(sum(t[2][i] for t in tr), 2) for i in range(2)],
          [450.0, 55.0])
    check("el color sigue al área (su puesto en el histórico)",
          (tr[0][1], tr[1][1], tr[2][1]),
          (PALETA_SERIES[1], PALETA_SERIES[0], PALETA_SERIES[3]))
    check("…aunque el filtro la deje sola en la vista",
          mp.colores_area(orden, ["BARRA"]), {"BARRA": PALETA_SERIES[3]})
    check("variación contra la barra anterior",
          [(x[0], round(x[1], 1) if x[1] is not None else None)
           for x in v["variaciones"]],
          [("primera", None), ("ok", -87.8)])
    check("la fila de la semana dice su año", v["fila"],
          ["lun 7–dom 13 set 2026", "lun 14–dom 20 set 2026"])

    filas, total = mp.tabla_resumen(v, foco="2026-S38")
    check("Resumen: el Estado escribe sólo la excepción",
          list(zip(filas["estado"], filas["__eclase"])),
          [("2 anulados", "anul"), ("1 sin procesar", "sinp")])
    check("Resumen: la fila marcada es la del foco",
          filas["__sel"].tolist(), [False, True])
    check("Resumen: el total cuenta documentos, no filas",
          (total["docs"], total["lineas"], total["valor"], total["estado"]),
          ("5", "6", "S/ 505.00", "2 anulados · 1 sin procesar"))
    check("sin novedad, un ✓",
          mp._texto_estado(0, 0, mp.REQUERIMIENTOS), ("✓", "ok"))

    amb = bl[bl["clave"] == "2026-S37"]
    check("Detalle: abre en el mayor válido, no en el anulado",
          mp._mayor_valido(amb), "R2")
    fr, tot_r = mp.tabla_documentos(amb, "R2", mp.REQUERIMIENTOS)
    check("Detalle: se LISTAN todos, cada uno con su estado",
          sorted(zip(fr["codigo"], fr["__estado"], fr["__elbl"])),
          [("R1", "", ""), ("R2", "", ""), ("R3", "anulado", "Anulado"),
           ("R4", "sin ítems", "Sin ítems"),
           ("R8", "anulado", "Anulado")])
    check("Detalle: …pero el total suma sólo los que suman",
          (tot_r["codigo"], tot_r["area"], tot_r["lineas"], tot_r["valor"]),
          ("2 req.", "+3 no suman", "3", "S/ 450.00"))
    check("Detalle: registro con hora, en ISO",
          fr.loc[fr["codigo"] == "R1", "registro"].tolist(),
          ["2026-09-07 10:00"])

    # La barra es LISA con UNA parte resaltada (regla #649, la receta de
    # «Compras por período»): sin resaltar, una barra del color de la serie
    # y, encima, la capa transparente que lleva hover, clic y etiqueta.
    fig = mp.figura_periodos(v, alturas.COMPACTO, titulo="t", foco="2026-S37")
    check("figura: sin resaltar, la barra lisa y la capa de arriba, sin "
          "leyenda (la fila de KPI lo es)",
          (len(fig.data), fig.layout.showlegend, fig.layout.barmode,
           fig.data[-1].marker.color, fig.data[0].hoverinfo),
          (2, False, "overlay", "rgba(0,0,0,0)", "skip"))
    check("figura: la etiqueta va en la capa, no en las franjas",
          [i for i, t in enumerate(fig.data) if t.text and t.text[1]], [1])
    check("figura: el foco atenúa las otras barras por COLOR",
          isinstance(fig.data[0].marker.color, tuple)
          and fig.data[0].marker.color[0] == SERIE_PRINCIPAL
          and fig.data[0].marker.color[1].startswith("rgba("), True)
    fr_ = mp.figura_periodos(v, alturas.COMPACTO, resaltado="COCINA")
    _coc = next(t[2] for t in tr if t[0] == "COCINA")
    check("figura: la parte resaltada va en el piso, oscura, y lo demás de "
          "la barra encima, en lavanda",
          (len(fr_.data), list(fr_.data[0].y), fr_.data[0].marker.color,
           list(fr_.data[1].base), fr_.data[1].marker.color),
          (3, _coc, SERIE_TRAMOS[0], _coc, SERIE_TRAMOS[2]))
    check("figura: la barra resaltada cierra con su total",
          [round(a + b, 2) for a, b in zip(fr_.data[0].y, fr_.data[1].y)],
          [450.0, 55.0])
    _hov = " ".join(str(cd[1]) for cd in fr_.data[-1].customdata)
    check("figura: el hover nombra TODAS las partes, la resaltada en "
          "negrita y el «Resto» contado como en la fila de KPI",
          ("<b>Cocina: S/" in _hov, "<br>Produccion: S/" in _hov,
           "2 áreas más" in _hov, "Resto" in _hov),
          (True, True, True, False))
    check("figura: el detalle del hover sigue en customdata[3]",
          "req." in str(fr_.data[-1].customdata[0][3]), True)
    check("figura: un tramo que no existe deja la barra lisa",
          len(mp.figura_periodos(v, alturas.COMPACTO,
                                 resaltado="NO EXISTE").data), 2)
    check("resaltables: los tramos con nombre, sin «Resto»",
          mp.resaltables(v), ["PRODUCCION", "COCINA", "BARRA"])
    check("resaltables: con un solo tramo no hay qué resaltar",
          mp.resaltables({"trazas": [("COCINA", SERIE_PRINCIPAL, [1.0])]}), [])
    _est = {}
    _ops = ["PRODUCCION", "COCINA"]
    check("lo resaltado abre en el mayor de la vista",
          mp.resaltado_vigente(_est, mp.PARTIR_AREA, _ops), "PRODUCCION")
    _est[mp.PARTIR_AREA] = None
    check("…soltado (None), se respeta",
          mp.resaltado_vigente(_est, mp.PARTIR_AREA, _ops), None)
    _est[mp.PARTIR_AREA] = "BARRA"
    check("…si lo elegido dejó de estar, vuelve al mayor",
          mp.resaltado_vigente(_est, mp.PARTIR_AREA, _ops), "PRODUCCION")
    check("…y una entrada por forma de partir",
          (mp.resaltado_vigente(_est, mp.PARTIR_TIPO, ["Bajas"]),
           _est[mp.PARTIR_AREA]), ("Bajas", "PRODUCCION"))
    _kr = mp._html_kpi(505.0, 5, tr, pd.Series([1.0] * 5), None,
                       mp.REQUERIMIENTOS, resaltables=mp.resaltables(v),
                       resaltado="COCINA")
    check("fila de KPI: los tramos son botones y el resaltado va apretado; "
          "el «Resto» no se resalta",
          ('data-res="COCINA" aria-pressed="true"' in _kr,
           'data-res="PRODUCCION" aria-pressed="false"' in _kr,
           'data-res="Resto"' in _kr, "2 áreas más" in _kr,
           "background:" in _kr),
          (True, True, False, True, False))
    for gran in ("Día", "Mes", "Año"):
        _l = base.copy()
        _l["clave"] = _periodo_serie(_l["fecha"], gran)
        try:
            mp.figura_periodos(
                mp.vista_periodos(_l, gran, rango, orden, mp.REQUERIMIENTOS),
                alturas.COMPACTO)
            check(f"figura en {gran}", True, True)
        except Exception as e:  # que se vea el tipo
            check(f"figura en {gran}", f"{type(e).__name__}: {e}", True)

    import ast as _ast
    _arbol = _ast.parse(pathlib.Path(mp.__file__).read_text(encoding="utf-8"))
    _llamadas = [n for n in _ast.walk(_arbol)
                 if isinstance(n, _ast.Call)
                 and getattr(n.func, "id", None) == "figura_periodos"]
    check("la tarjeta le pasa `resaltado=` a la figura (#649)",
          bool(_llamadas) and all(
              any(kw.arg == "resaltado" for kw in c.keywords)
              for c in _llamadas), True)

    # ── SALIDAS: el mismo código, el otro lado ───────────────────────────
    # S1 de Cocina (Bajas) con dos líneas, S2 de Cocina personal (Comida
    # personal), S3 ANULADA de Cocina, y S4 SIN PROCESAR: en salidas el
    # Generado no tiene ítems, porque sus líneas salen del kardex.
    ds = pd.DataFrame({
        "FECHA REGISTRO": pd.to_datetime(
            ["2026-09-07 10:00", "2026-09-07 10:00", "2026-09-08 11:00",
             "2026-09-09 12:00", "2026-09-10 09:00"]),
        "COD SALIDA": ["S1", "S1", "S2", "S3", "S4"],
        "AREA": ["COCINA", "COCINA", "COCINA PERSONAL", "COCINA", "BARRA"],
        "NOMBRE ESTADO SALIDA": ["PROCESADO", "PROCESADO", "PROCESADO",
                                 "ANULADO", "GENERADO"],
        "TIPO DESCARGO": ["Bajas", "Bajas", "Comida Personal", "Bajas",
                          "Prueba"],
        "NOMBRE FAMILIA": ["ALIMENTOS"] * 4 + [None],
        "NOMBRE PRODUCTO": ["A", "B", "C", "A", None],
        "CANT SALIDA": [2.0, 0.0, 4.0, 1.0, None],
        "VALOR NETO": [30.0, 5.0, 20.0, 8.0, None],
    })
    cs = dict(fecha="FECHA REGISTRO", doc="COD SALIDA", area="AREA",
              estado="NOMBRE ESTADO SALIDA", fam="NOMBRE FAMILIA",
              prod="NOMBRE PRODUCTO", cant="CANT SALIDA", val="VALOR NETO",
              tipo="TIPO DESCARGO")
    bs = mp.lineas_documentos(ds, **cs)
    check("salidas: sin precio en el parquet se despeja de la línea "
          "(y la cantidad 0 no da precio)",
          [None if pd.isna(x) else x for x in bs["punit"].tolist()[:3]],
          [15.0, None, 5.0])
    check("salidas: el tipo de descargo viaja por línea",
          bs["tipo"].tolist()[:3], ["Bajas", "Bajas", "Comida Personal"])
    bs["clave"] = _periodo_serie(bs["fecha"], "Semana")
    check("salidas: la anulada y la sin procesar no suman, cada una en lo "
          "suyo", mp.no_suman(bs), (1, 1, 0))
    check("salidas: la nota habla en femenino",
          mp.nota_no_suman(bs, mp.SALIDAS)[0],
          "1 anulada · 1 sin procesar")
    vs = mp.vista_periodos(bs, "Semana", rango, orden, mp.SALIDAS)
    fs, ts = mp.tabla_resumen(vs)
    check("salidas: Resumen con el estado en femenino",
          (fs["docs"].tolist(), fs["estado"].tolist(), ts["valor"]),
          ([2], ["1 anulada · 1 sin procesar"], "S/ 55.00"))
    fd, td = mp.tabla_documentos(bs, None, mp.SALIDAS)
    check("salidas: el Detalle lista el tipo y rotula la anulada y la sin "
          "procesar", sorted(zip(fd["codigo"], fd["tipo"], fd["__elbl"])),
          [("S1", "Bajas", ""), ("S2", "Comida Personal", ""),
           ("S3", "Bajas", "Anulada"), ("S4", "Prueba", "Sin procesar")])
    check("salidas: el total del Detalle",
          (td["codigo"], td["area"], td["valor"]),
          ("2 sal.", "+2 no suman", "S/ 55.00"))
    check("salidas: el hover dice «sal.»",
          "2 sal." in str(mp.figura_periodos(vs, alturas.COMPACTO)
                          .data[-1].customdata[0][3]), True)
    check("salidas: sin columna de área todo es «Sin área», sin romper",
          sorted(set(mp.lineas_documentos(ds, **{**cs, "area": None})
                     ["area"])), ["Sin área"])
    check("salidas: el CSS sale del molde con SUS prefijos",
          (".st-key-mps_fila" in mp._css(mp.SALIDAS),
           ".st-key-mov_psal_gran" in mp._css(mp.SALIDAS),
           "__C__" in mp._css(mp.SALIDAS)), (True, True, False))

    # ── PORCIONAMIENTOS: una fila por CORTE, la cabecera repetida (#510) ──
    # P1 (Producción, 10 kg de lomo, 2 de merma) salió en TRES cortes: la
    # cantidad y la merma vienen repetidas en las tres filas. Sus cortes
    # cuestan 400 + 100 + 100 = 600, lo que costó lo que entró; la merma en
    # soles es 600 × 2 ÷ 10 = 120. P2 (Cocina, 4 kg de limón, 2 de merma)
    # cuesta 8 → merma 4. P3, de la semana siguiente (Barra, 2 kg de pulpo,
    # 0,5 de merma): cuesta 60 → merma 15.
    dp = pd.DataFrame({
        "COD PORC": ["P1", "P1", "P1", "P2", "P3"],
        "FEC REGIST": pd.to_datetime(
            ["2026-09-08 09:00"] * 3 + ["2026-09-09 10:00",
                                        "2026-09-15 11:00"]),
        "SUB ALMACEN": ["PRODUCCION"] * 3 + ["COCINA ", "BARRA"],
        "USUARIO REG": ["CARLOS"] * 3 + ["MMASIAS", "CARLOS"],
        "PROD INICIAL": ["Lomo"] * 3 + ["Limon", "Pulpo"],
        "UNID PROD INIC": ["KILOS"] * 5,
        "CANT A PORCIONAR": [10.0] * 3 + [4.0, 2.0],
        "CANT MERMA": [2.0] * 3 + [2.0, 0.5],
        "PROD FINAL RESULT": ["Lomo porción", "Lomo recorte", "Lomo cabeza",
                              "Jugo", "Pulpo limpio"],
        "CANT RESULT": [20.0, 2.0, 1.0, 2.0, 1.5],
        "UNID PROD FIN": ["UND", "KILOS", "KILOS", "LITROS", "KILOS"],
        "PREC PROM PROD FIN": [20.0, 50.0, 100.0, 4.0, 40.0],
        "PESO RESULT": [5.0, 2.0, 1.0, 2.0, 1.5],
    })
    cp = dict(fecha="FEC REGIST", doc="COD PORC", area="SUB ALMACEN",
              tipo="USUARIO REG", prod="PROD INICIAL", unid="UNID PROD INIC",
              cant="CANT A PORCIONAR", merma="CANT MERMA",
              fin="PROD FINAL RESULT", cant_fin="CANT RESULT",
              unid_fin="UNID PROD FIN", pprom="PREC PROM PROD FIN",
              peso="PESO RESULT")
    bp, cortes = mp.lineas_porcionamientos(dp, **cp)
    check("porc.: UNA fila por porcionamiento, no una por corte",
          bp["doc"].tolist(), ["P1", "P2", "P3"])
    check("porc.: la merma de la cabecera se toma UNA vez (sumada por fila "
          "daría 6 kg en P1, no 2)",
          (bp.loc[bp["doc"] == "P1", "merma_cant"].tolist(),
           float(dp.loc[dp["COD PORC"] == "P1", "CANT MERMA"].sum())),
          ([2.0], 6.0))
    check("porc.: el costo es la suma de los cortes; la merma en soles, su "
          "parte", (bp["costo"].tolist(), bp["valor"].tolist()),
          ([600.0, 8.0, 60.0], [120.0, 4.0, 15.0]))
    check("porc.: cortes contados y área limpia",
          (bp["cortes"].tolist(), bp["area"].tolist()),
          ([3, 1, 1], ["PRODUCCION", "COCINA", "BARRA"]))
    check("porc.: el usuario viaja como el «tipo» del lado",
          bp["tipo"].tolist(), ["CARLOS", "MMASIAS", "CARLOS"])
    check("porc.: los cortes, uno por fila, con su valor",
          (len(cortes), float(cortes.loc[cortes["doc"] == "P1", "valor"].sum())),
          (5, 600.0))
    bp["clave"] = _periodo_serie(bp["fecha"], "Semana")
    rp = mp.resumen_por_periodo(bp)
    check("porc.: el Resumen suma lo porcionado y los cortes, por nombre",
          rp.loc["2026-S37", ["valor", "docs", "costo", "cortes", "areas"]]
            .tolist(),
          [124.0, 2, 608.0, 4, 2])
    check("porc.: nada queda fuera de las barras",
          (mp.no_suman(bp), mp.nota_no_suman(bp, mp.PORCIONAMIENTOS)),
          ((0, 0, 0), None))
    vp = mp.vista_periodos(bp, "Semana", rango, orden, mp.PORCIONAMIENTOS)
    fp, tp_ = mp.tabla_resumen_porc(vp, foco="2026-S37")
    check("porc.: el Resumen, por nombre de columna",
          (fp["docs"].tolist(), fp["cortes"].tolist(), fp["costo"].tolist(),
           fp["valor"].tolist(), [round(x, 4) for x in fp["pm"]],
           fp["__sel"].tolist()),
          ([2, 1], [4, 1], [608.0, 60.0], [124.0, 15.0], [0.2039, 0.25],
           [True, False]))
    check("porc.: el total del Resumen dice el % de merma de la vista",
          (tp_["docs"], tp_["cortes"], tp_["costo"], tp_["valor"], tp_["pm"]),
          ("3", "5", "S/ 668.00", "S/ 139.00", "20.8%"))
    fig_p = mp.figura_periodos(vp, alturas.SEMANAL_SOLO)
    # La etiqueta va en el tramo de ARRIBA de cada barra, que no es el mismo
    # trazo en las dos semanas: se juntan todas antes de mirar.
    etq = " ".join(t for tr in fig_p.data for t in (tr.text or []) if t)
    check("porc.: el 2º renglón de la etiqueta es el % de merma, no la cuenta",
          ("20% merma" in etq, "25% merma" in etq, "porc." in etq),
          (True, True, False))
    check("porc.: el hover cuenta porcionamientos y cortes",
          "2 porc. · 4 cortes" in str(fig_p.data[-1].customdata[0][3]), True)
    _fpr = mp.figura_periodos(vp, alturas.SEMANAL_SOLO,
                              resaltado=vp["trazas"][0][0])
    _etq_r = " ".join(t for t in (_fpr.data[-1].text or []) if t)
    check("porc.: con una parte resaltada el 2º renglón sigue siendo el % "
          "de merma (#510, #649)",
          (len(_fpr.data), "20% merma" in _etq_r, "25% merma" in _etq_r),
          (3, True, True))
    amb_p = bp[bp["clave"] == "2026-S37"]
    check("porc.: el Detalle abre en el de mayor merma", mp._mayor_valido(amb_p),
          "P1")
    fd_p, td_p = mp.tabla_porcionamientos(amb_p, "P1")
    check("porc.: la lista, con la unidad aparte y el % por porcionamiento",
          (fd_p["__unid"].tolist(), fd_p["pm"].tolist(), fd_p["valor"].tolist(),
           td_p["prod"], td_p["pm"], td_p["valor"]),
          (["kg", "kg"], [0.2, 0.5], [120.0, 4.0], "2 porc.", "20.4%",
           "S/ 124.00"))
    fc_p, tc_p = mp.tabla_cortes(cortes[cortes["doc"] == "P1"], "KILOS")
    check("porc.: los cortes de P1, del más caro al más barato, y el peso "
          "útil en la unidad del inicial",
          (fc_p["fin"].tolist()[0], fc_p["__unid"].tolist()[0],
           tc_p["peso"], tc_p["valor"]),
          ("Lomo porción", "und", "8 kg", "S/ 600.00"))
    kpi_p = mp._html_kpi(139.0, 3, vp["trazas"], None, None,
                         mp.PORCIONAMIENTOS, costo=668.0,
                         costo_area={"PRODUCCION": 600.0})
    check("porc.: la fila de KPI abre con la merma y cierra con lo porcionado",
          ("Merma de la vista" in kpi_p, "Porcionado" in kpi_p,
           "20.8% merma" in kpi_p,
           "su merma es el 20.0% de lo que porcionó" in kpi_p),
          (True, True, True, True))
    check("porc.: unidades cortas y cantidades con sus decimales",
          (mp.unidad_corta("KILOS"), mp.unidad_corta("UND"),
           mp.unidad_corta("CAJA"), mp.fmt_cant(12.175), mp.fmt_cant(21.0)),
          ("kg", "und", "caja", "12.175", "21"))
    check("porc.: el CSS sale del molde con SUS prefijos",
          (".st-key-mpp_fila" in mp._css(mp.PORCIONAMIENTOS),
           ".st-key-mov_pporc_gran" in mp._css(mp.PORCIONAMIENTOS)),
          (True, True))

    # ── PRODUCCIÓN: la orden GENERADA no suma aunque tenga líneas (#575) ──
    # Semana 37: O1 de Cocina procesada con dos recetas (36 + 14 = 50), O2
    # de Producción GENERADA con una línea de 54 —MÁS que O1: si sumara, el
    # Detalle abriría en ella— y O3 de Barra ANULADA. Semana 38: O4 de
    # Pastelería, 68. Los nombres de columna son los de la consulta del
    # Sheet (`ordenesproduccion`).
    do = pd.DataFrame({
        "COD ORDEN PRODUCCION": ["O1", "O1", "O2", "O3", "O4"],
        "FECHA REGISTRO": pd.to_datetime(
            ["2026-09-08 10:00"] * 2 + ["2026-09-09 11:00", "2026-09-10 12:00",
                                        "2026-09-15 09:00"]),
        "AREA": ["COCINA", "COCINA", "PRODUCCION", "BARRA", "PASTELERIA"],
        "NOMBRE ESTADO": ["PROCESADO", "PROCESADO", "GENERADO", "ANULADO",
                          "PROCESADO"],
        "USUARIO REGISTRO": ["CARLOS", "CARLOS", "MMASIAS", "CARLOS", "CARLOS"],
        "NOMBRE FAMILIA": ["ALIMENTOS", "ALIMENTOS", "ALIMENTOS",
                           "BEBIDAS CON ALCOHOL", "ALIMENTOS"],
        "NOMBRE PRODUCTO": ["(Rs) Salsa", "(Rs) Arroz", "(Rs) Salsa",
                            "(Rs) Batch", "(Rs) Creme brulee"],
        "CANTIDAD": [2.0, 10.0, 3.0, 1.0, 8.0],
        "UNIDAD": ["KILOS", "UND", "KILOS", "LITROS", "UND"],
        "PRECIO UNIT": [18.0, 1.4, 18.0, 7.6, 8.5],
        "VALOR ITEM": [36.0, 14.0, 54.0, 7.6, 68.0],
    })
    co = dict(fecha="FECHA REGISTRO", doc="COD ORDEN PRODUCCION", area="AREA",
              estado="NOMBRE ESTADO", tipo="USUARIO REGISTRO",
              fam="NOMBRE FAMILIA", prod="NOMBRE PRODUCTO", cant="CANTIDAD",
              unid="UNIDAD", punit="PRECIO UNIT", val="VALOR ITEM")
    bo = mp.lineas_documentos(do, **co)
    check("prod.: la unidad viaja por línea; sin ella, vacía",
          (bo["unid"].tolist(),
           set(mp.lineas_documentos(do, **{**co, "unid": None})["unid"])),
          (["KILOS", "UND", "KILOS", "LITROS", "UND"], {""}))
    bo["clave"] = _periodo_serie(bo["fecha"], "Semana")
    ro = mp.resumen_por_periodo(bo, mp.PRODUCCION)
    check("prod.: la generada no suma; anulada y generada se cuentan",
          ro.loc["2026-S37", ["valor", "lineas", "docs", "anulados",
                              "sin_procesar"]].tolist(),
          [50.0, 2, 1, 1, 1])
    check("…y en requerimientos la misma fila SÍ sumaría (el criterio es "
          "del lado)", float(mp.resumen_por_periodo(bo).loc["2026-S37",
                                                            "valor"]), 104.0)
    check("prod.: lo que no suma, contado una vez",
          (mp.no_suman(bo, mp.PRODUCCION), mp.no_suman(bo)),
          ((1, 1, 0), (1, 0, 0)))
    check("prod.: la nota habla en femenino y nombra la generada aun con "
          "filtro de familia (tiene familia y producto)",
          (mp.nota_no_suman(bo, mp.PRODUCCION)[0],
           mp.nota_no_suman(bo, mp.PRODUCCION, vacios_nombrables=False)[0]),
          ("1 anulada · 1 sin procesar", "1 anulada · 1 sin procesar"))
    check("prod.: la nota larga dice por qué no suma",
          "no movieron el kardex" in mp.nota_no_suman(bo, mp.PRODUCCION)[1],
          True)
    amb_o = bo[bo["clave"] == "2026-S37"]
    check("prod.: el Detalle abre en la mayor PROCESADA, no en la generada",
          (mp._mayor_valido(amb_o, mp.PRODUCCION), mp._mayor_valido(amb_o)),
          ("O1", "O2"))
    fo, to = mp.tabla_documentos(amb_o, "O1", mp.PRODUCCION)
    check("prod.: la lista rotula la generada aunque tenga líneas",
          sorted(zip(fo["codigo"], fo["tipo"], fo["__estado"], fo["__elbl"])),
          [("O1", "CARLOS", "", ""), ("O2", "MMASIAS", "sin procesar",
                                      "Sin procesar"),
           ("O3", "CARLOS", "anulado", "Anulada")])
    check("prod.: el total del Detalle suma sólo la procesada",
          (to["codigo"], to["area"], to["lineas"], to["valor"]),
          ("1 OP", "+2 no suman", "2", "S/ 50.00"))
    vo = mp.vista_periodos(bo, "Semana", rango, orden, mp.PRODUCCION)
    check("prod.: las barras son las de lo procesado",
          vo["tot"], [50.0, 68.0])
    check("prod.: el hover cuenta órdenes como «OP»",
          "1 OP · 2 líneas" in str(mp.figura_periodos(vo, alturas.COMPACTO)
                                  .data[-1].customdata[0][3]), True)
    fro, _ = mp.tabla_resumen(vo)
    check("prod.: el Resumen avisa lo que quedó fuera",
          fro["estado"].tolist(), ["1 anulada · 1 sin procesar", "✓"])
    check("prod.: el CSS sale del molde con SUS prefijos",
          (".st-key-mpd_fila" in mp._css(mp.PRODUCCION),
           ".st-key-mov_pprod_gran" in mp._css(mp.PRODUCCION)), (True, True))
    lados = (mp.REQUERIMIENTOS, mp.SALIDAS, mp.PORCIONAMIENTOS, mp.PRODUCCION)
    check("los cuatro lados no comparten prefijos ni tarjeta (conviven en la "
          "página)", [len({getattr(x, a) for x in lados})
                      for a in ("k", "c", "card")], [4, 4, 4])
    return fallos


def main():
    df, df_min = _df_completo(), _df_minimo()
    fallos = 0

    # Tras el refactor Fase 2, los helpers privados de Ajuste viven en
    # graficos.ajuste (se prueban desde su módulo real). renderizar_graficos_
    # ajuste sigue accesible como graficos.X porque __init__ lo re-exporta.
    from graficos import ajuste as _aj

    pruebas = [
        # Evolución (regla #501): las figuras puras, en sus dos magnitudes
        # y con un período en foco. La vista entera lleva AgGrid.
        ("evolucion · serie con foco", lambda: _aj.fig_serie(
            _aj.serie_ajuste(*_aj.periodos_ajuste(
                df, "FECHA APERTURA INVENTARIO", "Mes"),
                "AJUSTE VALORIZADO", "VALORIZADO TOTAL"), "2024-03"), ()),
        ("evolucion · familias por corte", lambda: _aj.fig_familias(
            _aj.serie_ajuste(*_aj.periodos_ajuste(
                df, "FECHA APERTURA INVENTARIO", "Corte"),
                "AJUSTE VALORIZADO", "VALORIZADO TOTAL", col_grupo="FAMILIA")),
         ()),
        ("evolucion · serie sin valorizado (rama else)", lambda: _aj.fig_serie(
            _aj.serie_ajuste(*_aj.periodos_ajuste(
                df_min, "FECHA APERTURA INVENTARIO", "Corte"),
                "AJUSTE VALORIZADO")), ()),
        ("waterfall (Cascada)", _aj._graf_waterfall_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO")),
        ("heatmap (Mapa de calor)", _aj._graf_heatmap_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO")),
        ("distribucion (box por familia)", _aj._graf_distribucion_ajuste,
            (df, "FAMILIA", "AREA", "AJUSTE VALORIZADO", "NOMBRE PRODUCTO")),
        ("distribucion (rama else: histograma)", _aj._graf_distribucion_ajuste,
            (df_min, None, None, "AJUSTE VALORIZADO", None)),
        ("pareto valor (Ajuste)", _aj._fig_pareto_ajuste,
            (df, "AJUSTE VALORIZADO", "NOMBRE PRODUCTO")),
    ]

    # ── Recetas › Costo recetas base: la evolución del costo ────────────
    # Reemplazó al Ranking de recetas base de graficos/recetas_comun.py el
    # 2026-09-30 (regla #576). Una orden atípica adentro: es la que ejercita
    # la traza «fuera de escala» y el tope del eje.
    from graficos import recetas_base_costo as _rbc
    _o_rb = _rbc.ordenes(_ordenes_rb_demo())
    _o_s = _o_rb[_o_rb["cod"] == "0000100"]
    pruebas += [
        ("recetas · costo recetas base · evolución", _rbc.fig_evolucion,
            (_o_s, _rbc.costo_por_mes(_o_s), 20.0, "KILOS")),
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
                                     (pd.Period("2026-08", "M"), 21)), ()),
        ("compras vs año pasado · serie (Cantidad)",
         lambda: _vap_fig._fig_serie(_g_vap, "Cantidad", None), ()),
        ("compras vs año pasado · serie (Precio, ratio con cero)",
         lambda: _vap_fig._fig_serie(_g_vap, "Precio", None), ()),
        ("compras vs año pasado · serie (Cantidad, con unidad y precio)",
         lambda: _vap_fig._fig_serie(_g_vap, "Cantidad", None, unidad="kg",
                                     con_precio=True), ()),
        ("compras vs año pasado · puente precio/cantidad",
         lambda: _vap_fig._fig_puente(250.0, 450.0, 60.0, -260.0), ()),
        # Los otros dos cortes de la cascada y el mes elegido (regla #443).
        ("compras vs año pasado · serie con un mes elegido",
         lambda: _vap_fig._fig_serie(_g_vap, "Valor", None,
                                     mes_sel="ago 26"), ()),
        ("compras vs año pasado · cascada por contribuyentes",
         lambda: _vap_fig._fig_cascada(
             _vap_fig._pasos_cascada(
                 [("Magret de pato", -16660.0), ("Bife angosto", -15876.0),
                  ("Lomo fino", -11975.0), ("Cachema", 5817.0),
                  ("Conchas de abanico jumbo x und", 4036.0)],
                 412393.0, 286254.0),
             lambda v, m: _vap_fig._etq_cascada(v, m, _vap_fig._fmt_soles)),
         ()),
        ("compras vs año pasado · cascada de tres barras (Precio)",
         lambda: _vap_fig._fig_cascada(
             _vap_fig._pasos_simple(61.02, 74.68),
             lambda v, m: _vap_fig._etq_cascada(
                 v, m, lambda x: _vap_fig._fmt_precio(x, "kg"))),
         ()),
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
    fallos += _pruebas_rango_por_tarjeta()
    fallos += _pruebas_widgets_de_fragment_escalado()
    fallos += _pruebas_fragment_anidado_una_vez()
    fallos += _pruebas_css_comentarios_cerrados()
    fallos += _pruebas_css_sin_prosa_suelta()
    fallos += _pruebas_has_solo_clases()
    fallos += _pruebas_has_de_streamlit()
    fallos += _pruebas_encaje_pila()
    fallos += _pruebas_periodo_por_vista()

    # ── El panel del selector de fecha de las tarjetas (regla #616) ──────
    fallos += _pruebas_panel_fecha()

    # ── Movimientos: cada vista con su propia fecha (regla #617) ─────────
    fallos += _pruebas_fecha_por_vista()
    fallos += _pruebas_ajustes_compartidos()

    # ── Compras por período: «Partir por» (regla #620) ───────────────────
    fallos += _pruebas_partir_por()

    # ── Deteccion de anomalias en Ajuste ────────────────────────────────
    fallos += _pruebas_anomalias()

    # ── El chip de la mini contra el corte anterior ──────────────────────
    fallos += _pruebas_resumen_ajuste()

    # ── Ajuste › Evolución: períodos compartidos, sobrante/faltante/% ────
    fallos += _pruebas_evolucion_ajuste()
    fallos += _pruebas_fechas_ajuste()

    # ── Ajuste › Mapa de calor: la cantidad es la que el monto multiplica ─
    fallos += _pruebas_cantidad_del_mapa_ajuste()

    # ── Inventario › Productos: el grano y el despliegue de áreas ────────
    fallos += _pruebas_listado_inventario()
    fallos += _pruebas_analisis_stock()
    fallos += _pruebas_inventario_activos()
    fallos += _pruebas_kardex()

    # ── Ajuste › el cierre contra el kardex (regla #612) ─────────────────
    fallos += _pruebas_ajuste_kardex()

    # ── Movimientos › las tarjetas «por período»: qué cuenta y qué no ────
    fallos += _pruebas_movimientos_periodo()

    # ── Ventas › un ítem una vez, aunque se haya pagado con dos formas ───
    fallos += _pruebas_ventas_un_item_una_vez()

    # ── Ventas › Mix de carta: las cuentas por nombre y el año pasado ────
    fallos += _pruebas_ventas_mix()

    # ── Ventas › Análisis de platos: puestos, movimiento, por día ────────
    fallos += _pruebas_ventas_platos()
    fallos += _pruebas_ventas_franja()

    # ── Ventas › Ingeniería de menú: la clasificación de Kasavana-Smith ──
    fallos += _pruebas_ventas_menu()

    # ── Ventas › Meseros: propinas, pozo común, planilla y Excel ────────
    fallos += _pruebas_ventas_meseros()

    # ── Ventas › Por hora: las filas «Platos» y «Grupos» ─────────────────
    fallos += _pruebas_por_hora_filas()
    fallos += _pruebas_ficha_hora()
    fallos += _pruebas_por_hora_semana_y_desliza()
    fallos += _pruebas_cabecera_por_hora()

    # ── Movimientos › Detalle de salidas: suma lo mismo que su vecina ────
    fallos += _pruebas_detalle_salidas()
    fallos += _pruebas_requerimientos_por_area()
    fallos += _pruebas_salidas_comparar()
    fallos += _pruebas_sin_plato()
    fallos += _pruebas_diferencias_ajuste()
    fallos += _pruebas_diferencias_combos()
    fallos += _pruebas_diferencias_req_sunat()
    fallos += _pruebas_merma()
    fallos += _pruebas_cortes_y_peso()

    # ── Recetas › Carta costeada: la carta entera, combos incluidos ──────
    fallos += _pruebas_carta_costeada()
    fallos += _pruebas_igv_y_sin_costo()
    fallos += _pruebas_ticket_sin_canales_sin_clientes()
    fallos += _pruebas_formas_de_pago()
    fallos += _pruebas_control_pedidos()
    fallos += _pruebas_filas_por_area()

    # ── Recetas › Costo recetas base: uso, producción y costo (#576) ─────
    fallos += _pruebas_costo_recetas_base()

    # ── Recetas › Revisar recetas: los cortes que ninguna receta usa ─────
    fallos += _pruebas_revisar_recetas()

    # ── Contratos entre app.py y los dashboards (firma del dispatcher) ──
    fallos += _pruebas_contratos()

    # ── Presupuesto vertical: que las tarjetas sigan entrando en pantalla ─
    fallos += _pruebas_presupuesto_vertical()

    # ── Grilla horizontal: que todas las filas partan en el mismo sitio ──
    fallos += _pruebas_grilla_horizontal()

    # ── Producto: la lista cuadra, y la marca «revisar» no entra al precio
    fallos += _pruebas_producto_lista_y_ficha()

    # ── Compras: que no vuelvan los bucles por grupo (regla #537) ───────
    fallos += _pruebas_compras_sin_bucles_por_grupo()

    # ── Container queries: que ninguna se quede sin contenedor ──────────
    fallos += _pruebas_container_queries()

    # ── CSS clonado: el tercer prefijo sale del molde, no a mano ───────
    fallos += _pruebas_css_clonado()

    # ── El hook del scrollspy: que siga colgando de `secciones` ────────
    fallos += _pruebas_hook_del_rail_bajo_secciones()

    # ── Las vistas «Tabla»: ocultas, pero todavía declaradas ────────────
    fallos += _pruebas_vistas_tabla_ocultas()

    # ── El panel de cada reporte: el mismo rail que su dashboard ───────
    fallos += _pruebas_vistas_de_cada_reporte()

    # ── JsCode: que nadie vuelva a meterle un payload de datos adentro ──
    fallos += _pruebas_jscode_barato()

    # ── El JS inyectado: que el escapado de dos niveles no lo rompa ─────
    fallos += _pruebas_js_inyectado_sano()

    # ── Una sola `nombre_propio`: que no vuelvan a ser dos ──────────────
    fallos += _pruebas_una_sola_nombre_propio()

    # ── El simulador de receta: que nadie vuelva a ordenar el borrador ─
    fallos += _pruebas_simulador_receta()

    # ── Nuevo Costeo: lo que el almacén todavía no tiene (#597) ─────────
    fallos += _pruebas_articulos_nuevos()

    # ── El marcador de una inyección: que el .replace() lo alcance ─────
    fallos += _pruebas_placeholder_de_inyeccion()

    # ── El barrido del fuente que usan las guardas de arriba ────────────
    fallos += _pruebas_recorrido_fuentes()

    print()
    if fallos:
        print(f"❌ {fallos} fallo(s) — revisar las líneas FALLA de arriba")
        sys.exit(1)
    print("✅ Todo OK (constructores de figuras + funciones puras)")


if __name__ == "__main__":
    main()
