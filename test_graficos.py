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
    check("el KPI del rail sigue recibiendo los conteos",
          _ds.st.session_state.pop("_cp_docs_cruce", None),
          {"sunat": 5, "sistema": 7, "revisar": 5})
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
          ["1–24 sep 2026", "26 ago – 24 sep 2026",
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
          ("14–20 set", "Semana del lun 14 al dom 20 set 2026"))
    check("rótulo · semana que cruza de mes",
          _sem._rotulo_periodo("2026-S36", "Semana"),
          ("31 ago–6 set", "Semana del lun 31 ago al dom 6 set 2026"))
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
        clave_corte as _clave_corte, clave_modo as _clave_modo,
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
    # El corte espeja la partición del rango: si no, cambiar de sección
    # dejaría vivo un corte que ya no corresponde al rango en pantalla.
    check("clave_corte espeja la partición del rango",
          _clave_corte("Compras", categoria="sec_proveedor")
          != _clave_corte("Compras", categoria="sec_semanal"),
          True)
    check("clave_corte por categoría separa reportes",
          _clave_corte("Compras", categoria="tiempo")
          != _clave_corte("Ajuste de Inventario", categoria="tiempo"),
          True)
    check("clave_modo se deriva de la del corte",
          _clave_modo(_clave_corte("Compras", categoria="sec_semanal")),
          "modo_" + _clave_corte("Compras", categoria="sec_semanal"))
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
        ("movimientos_comun.py", "mov_evo_gran"):
            "ya lo cubre el espejo `_K_GRAN_ECO`, que es la forma vieja de "
            "la misma cura (regla #211, medida ahí el 2026-09-05)",
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
    for py, texto in _fuentes_py(raiz):
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
        k_rango="rango_franja_Compras", k_corte="corte_franja_Compras",
        corte_apl=None, cortes=[], fecha_min=f_min, fecha_max=f_max,
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
        k_rango="rango_franja_Compras", k_corte="corte_franja_Compras",
        corte_apl=None, cortes=[], fecha_min=f_min, fecha_max=f_max,
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
        k_rango="rango_franja_Compras", k_corte="corte_franja_Compras",
        corte_apl=None, cortes=[], fecha_min=f_min, fecha_max=f_max,
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


def _pruebas_regla_riel():
    """graficos/base.py — la regla de referencia bajo el riel de la escala.

    Dos cosas que el ojo no puede verificar en una captura:

    1. QUE LOS RÓTULOS NO SE PISEN en ninguna ventana posible. Meses trae
       entre 1 y 12 casilleros y Años entre 1 y 10, según cuánto los recorte
       `bounds`, así que probar "el de hoy" (8 meses, 4 años) no dice nada
       del día que la data llegue a doce meses.

    2. QUE LOS BORDES Y LOS PERÍODOS SEAN LA MISMA COSA CONTADA DISTINTO.
       El riel de Meses/Años para en los BORDES entre períodos (regla
       #298), así que hay dos traducciones que tienen que cerrar: el borde
       que cierra un período es el arranque del siguiente, y el rango que
       sale de un par de bordes es el mismo que salía del par de períodos.
       Si se desfasan una, el filtro se corre un mes entero sin avisar.

    La cuenta de anchos usa el rótulo MÁS ANCHO de la escala para TODAS las
    marcas, que es el peor caso: en pantalla sobra aire porque "jul" mide
    la mitad que "may".
    """
    import datetime

    from estado_rango import escala_a_rango, escala_periodos
    from graficos.base import (_AIRE_ROTULO, _ANCHO_RIEL_PX, _ANCHO_ROTULO,
                               _borde_siguiente, _indices_rotulados,
                               _rotulo_periodos)

    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    regla riel · {nombre}")
        else:
            fallos += 1
            print(f"FALLA regla riel · {nombre}: {detalle}")

    # ── (1) los rótulos, centrados en su casillero ─────────────────────
    for escala, tope in (("Meses", 12), ("Años", 10)):
        ancho = _ANCHO_ROTULO[escala]
        for n in range(1, tope + 1):
            idx = _indices_rotulados(n, ancho)
            slot = _ANCHO_RIEL_PX / n
            check(f"{escala} n={n}: hay rótulos, en orden y dentro de rango",
                  idx and idx == sorted(set(idx)) and idx[0] == 0
                  and idx[-1] < n, f"idx={idx}")
            # Todos van centrados en su casillero: medio rótulo de cada
            # lado, sin la excepción de las puntas que tenía el modelo
            # anterior (los rótulos ya no se pinean).
            peor = min(((z - a) * slot - ancho, a, z)
                       for a, z in zip(idx, idx[1:])) if len(idx) > 1 else None
            if peor is not None:
                check(f"{escala} n={n}: ningún par de rótulos se toca",
                      peor[0] >= _AIRE_ROTULO,
                      f"aire={peor[0]:.1f}px entre {peor[1]} y {peor[2]}")
            # El primero y el último tienen que entrar ENTEROS en el riel:
            # su centro está a media casilla del borde.
            check(f"{escala} n={n}: los rótulos de las puntas no se cortan",
                  slot >= ancho, f"casilla={slot:.1f}px, rótulo={ancho}px")

    # ── (2) bordes ↔ períodos ──────────────────────────────────────────
    b = (datetime.date(2024, 3, 17), datetime.date(2026, 8, 25))
    for escala in ("Meses", "Años"):
        paradas = escala_periodos(escala, b)
        check(f"{escala}: el borde que cierra un período abre el siguiente",
              all(_borde_siguiente(escala, p) == q
                  for p, q in zip(paradas, paradas[1:])),
              "")
        # El borde extra del final NO existe entre las paradas: es el que
        # le da ancho al último casillero.
        check(f"{escala}: el borde final cae después de la última parada",
              _borde_siguiente(escala, paradas[-1]) > paradas[-1], "")
        # La traducción de vuelta: un par de bordes tiene que dar el mismo
        # rango que daba el par de períodos equivalente.
        for i, j in ((0, 0), (0, len(paradas) - 1), (1, 3)):
            if j >= len(paradas):
                continue
            por_periodos = escala_a_rango(escala, paradas[i], paradas[j], b)
            _b1 = _borde_siguiente(escala, paradas[j])
            por_bordes = escala_a_rango(
                escala, paradas[i], _b1 - datetime.timedelta(days=1), b)
            check(f"{escala}: bordes [{i},{j}] dan el mismo rango que períodos",
                  por_bordes == por_periodos,
                  f"bordes={por_bordes} períodos={por_periodos}")
        # UN SOLO período elegido tiene que seguir dando el período entero
        # —que es el caso que motivó todo el cambio— y no un día suelto.
        _uno = paradas[2] if len(paradas) > 2 else paradas[0]
        _rango = escala_a_rango(
            escala, _uno, _borde_siguiente(escala, _uno)
            - datetime.timedelta(days=1), b)
        check(f"{escala}: un período suelto abarca el período entero",
              _rango == escala_a_rango(escala, _uno, _uno, b), str(_rango))

    # Regresiones concretas, con la cuenta a la vista para que un cambio de
    # los anchos medidos se lea como lo que es y no como un número mágico.
    check("un año entero de Meses (12 casilleros de 19,8px) rotula 6",
          _indices_rotulados(12, _ANCHO_ROTULO["Meses"]) == [0, 2, 4, 6, 8, 10],
          str(_indices_rotulados(12, _ANCHO_ROTULO["Meses"])))
    check("ocho meses entran todos",
          _indices_rotulados(8, _ANCHO_ROTULO["Meses"]) == list(range(8)),
          str(_indices_rotulados(8, _ANCHO_ROTULO["Meses"])))
    check("una década de Años rotula uno por medio",
          _indices_rotulados(10, _ANCHO_ROTULO["Años"]) == [0, 2, 4, 6, 8],
          str(_indices_rotulados(10, _ANCHO_ROTULO["Años"])))
    check("cuatro años entran todos",
          _indices_rotulados(4, _ANCHO_ROTULO["Años"]) == [0, 1, 2, 3],
          str(_indices_rotulados(4, _ANCHO_ROTULO["Años"])))
    check("un riel sin casilleros no revienta",
          _indices_rotulados(0, 18) == [], "")

    # ── (3) el aviso de redondeo ───────────────────────────────────────
    # El riel de Meses/Años PINTA casilleros enteros, así que con un rango
    # más fino que la escala dibuja de más: el 31 de agosto suelto se ve
    # como agosto entero. El caption lo canta comparando el rango que
    # representan los casilleros contra el rango vigente — acá se fija que
    # esa comparación distinga los dos casos, que es de lo que depende que
    # el aviso salga cuando tiene que salir y NO salga cuando no.
    _ago = datetime.date(2026, 8, 1)
    _dia = (datetime.date(2026, 8, 31), datetime.date(2026, 8, 31))
    _mes = (datetime.date(2026, 8, 1), datetime.date(2026, 8, 31))
    _b2 = (datetime.date(2023, 1, 1), datetime.date(2026, 12, 31))
    check("un día suelto NO es lo que pinta el casillero del mes",
          escala_a_rango("Meses", _ago, _ago, _b2) != _dia, "")
    check("el mes entero SÍ es lo que pinta su casillero",
          escala_a_rango("Meses", _ago, _ago, _b2) == _mes, "")
    # Y el caso que se lee al revés: si los datos cortan a mitad de mes, el
    # casillero YA vale ese pedazo, así que el aviso no tiene que salir.
    _b3 = (datetime.date(2023, 1, 1), datetime.date(2026, 8, 24))
    check("con los datos cortados a mitad de mes no hay redondeo que avisar",
          escala_a_rango("Meses", _ago, _ago, _b3)
          == (datetime.date(2026, 8, 1), datetime.date(2026, 8, 24)), "")

    check("el rótulo del tramo pintado lleva el año, y se abrevia si es uno",
          [_rotulo_periodos("Meses", _ago, _ago),
           _rotulo_periodos("Meses", datetime.date(2026, 7, 1), _ago),
           _rotulo_periodos("Meses", datetime.date(2025, 12, 1),
                            datetime.date(2026, 1, 1)),
           _rotulo_periodos("Años", datetime.date(2024, 1, 1),
                            datetime.date(2026, 1, 1))]
          == ["ago 2026", "jul-ago 2026", "dic 2025 - ene 2026", "2024-2026"],
          str([_rotulo_periodos("Meses", _ago, _ago),
               _rotulo_periodos("Años", datetime.date(2024, 1, 1),
                                datetime.date(2026, 1, 1))]))

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
    # 41 el 2026-09-04. El umbral va abajo del numero real a proposito:
    # que alguien SUME reglas a `cp_prod` no tiene por que romper el test,
    # pero que se caigan a la mitad si.
    check("se clonan las reglas de cp_prod (>=35)", n >= 35, n)
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


def _pruebas_drill_familia_subfamilia():
    """El drill Familia › Subfamilia → Ranking de productos de
    `compras/producto.py`.

    Hasta el 2026-09-12 el tercer nivel era un panel propio (los productos
    del grupo elegido); ese día se fue y su papel lo tomó el Ranking de
    productos, que los paneles de arriba RECORTAN (`_ambito_ranking`). Las
    trampas son las mismas, cambió quién las pisa:

      1. Que los niveles dejen de CUADRAR. La suma del panel B tiene que
         dar la fila elegida del A, y la del ranking recortado la fila
         elegida del B. Si alguien cambia un `groupby` o un filtro y eso se
         rompe, en pantalla se ve una tabla perfectamente creíble con los
         números de otra cosa.
      2. Que el % deje de ser sobre el PADRE. Es la decisión de diseño del
         drill: con % global las cinco subfamilias de VINOS darían 4%,
         0,5%… y la columna dejaría de comparar lo que se está viendo.
      3. Que el recorte por subfamilia se haga por la subfamilia SOLA. La
         clave es el PAR (familia, subfamilia): medido sobre R2 el
         2026-09-09, 9 de las 95 subfamilias de compras.parquet aparecen en
         más de una familia, así que un `df[col_subfam] == x` suelto mezcla
         productos de dos familias sin dar error. Acá se reproduce con una
         subfamilia repetida a propósito.
      4. Que la UM se pierda. La cantidad de un producto sólo significa algo
         con su unidad al lado (ver el docstring de `_prod_ranking`).
      5. Que sin ningún clic el ranking deje de ser el de TODO lo comprado.
         El panel B abre mostrando la familia de arriba, pero eso es su
         foco, no el ámbito del ranking (ver `_paneles_familia`).

    Datos sintéticos y deterministas: sin R2, sin secrets, sin red.
    """
    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    drill · {nombre}")
        else:
            fallos += 1
            print(f"FALLA drill · {nombre}{': ' + detalle if detalle else ''}")

    from graficos.compras.producto import (
        _ambito_ranking, _fam_normalizada, _fam_ranking, _prod_ranking,
        _subfam_normalizada, _subfam_ranking,
    )

    # "Varios" es la subfamilia repetida entre DOS familias: es la trampa 3.
    df = pd.DataFrame({
        "FAM": ["A", "A", "A", "A", "B", "B", "B"],
        "SUB": ["Carnes", "Carnes", "Verduras", "Varios",
                "Vinos", "Varios", "Varios"],
        "PROD": ["Lomo", "Asado", "Papa", "Bolsa",
                 "Malbec", "Bolsa", "Corcho"],
        "VAL": [600.0, 200.0, 150.0, 50.0, 300.0, 80.0, 20.0],
        "CANT": [10.0, 5.0, 30.0, 100.0, 12.0, 40.0, 200.0],
        "UM": ["KILOS", "KILOS", "KILOS", "UND", "UND", "UND", "UND"],
        "PUNIT": [60.0, 40.0, 5.0, 0.5, 25.0, 2.0, 0.1],
        "FECHA": pd.to_datetime(["2026-08-01", "2026-08-02", "2026-08-03",
                                 "2026-08-04", "2026-08-05", "2026-08-06",
                                 "2026-08-07"]),
    })

    def ranking(fam, sub, col_subfam="SUB", col_cant="CANT", col_um="UM"):
        """El Ranking de productos tal como lo arma la tarjeta: el ámbito
        que dejan los paneles, y sobre eso `_prod_ranking`."""
        amb = _ambito_ranking(df, "FAM", col_subfam, fam, sub)
        return _prod_ranking(amb, "PROD", "FECHA", "VAL", col_cant, "PUNIT",
                             col_um)

    fam = _fam_ranking(df, "FAM", "VAL")
    check("panel A ordena por valor descendente",
          fam["familia"].tolist() == ["A", "B"], str(fam["familia"].tolist()))
    check("los % del panel A suman 100", abs(fam["pct"].sum() - 100) < 1e-9)
    check("el panel A ya no trae la columna de conteo (se pidió fuera)",
          fam.columns.tolist() == ["familia", "valor", "pct"],
          str(fam.columns.tolist()))

    d_fam = df[_fam_normalizada(df, "FAM") == "A"]
    sub = _subfam_ranking(d_fam, "SUB", "PROD", "VAL")
    check("el panel B CUADRA con su fila del panel A",
          abs(sub["valor"].sum() - float(fam.iloc[0]["valor"])) < 1e-9,
          f"{sub['valor'].sum()} vs {fam.iloc[0]['valor']}")
    # 600+200 sobre 1000, no sobre 1400: el % es del PADRE (trampa 2).
    check("el % del panel B es sobre SU FAMILIA, no sobre el total",
          abs(float(sub.iloc[0]["pct"]) - 80.0) < 1e-9,
          f"{sub.iloc[0]['pct']}")

    # Trampa 5: sin ningún clic, el ranking es el de todo lo comprado.
    todo = ranking(None, None)
    check("sin clic, el ranking es TODO lo comprado",
          abs(todo["valor"].sum() - float(df["VAL"].sum())) < 1e-9,
          f"{todo['valor'].sum()} vs {df['VAL'].sum()}")

    solo_fam = ranking("A", None)
    check("con una familia elegida, el ranking CUADRA con su fila del A",
          abs(solo_fam["valor"].sum() - float(fam.iloc[0]["valor"])) < 1e-9)

    pro = ranking("A", "Carnes")
    check("con una subfamilia elegida, el ranking CUADRA con su fila del B",
          abs(pro["valor"].sum() - float(sub.iloc[0]["valor"])) < 1e-9)
    check("la columna Prod. del panel B cuenta las filas del ranking",
          len(pro) == int(sub.iloc[0]["productos"]))
    check("el % del ranking es sobre SU ámbito (la subfamilia)",
          abs(float(pro.iloc[0]["pct"]) - 75.0) < 1e-9, f"{pro.iloc[0]['pct']}")
    check("cada producto se lleva su UM (trampa 4)",
          pro["um"].tolist() == ["KILOS", "KILOS"], str(pro["um"].tolist()))

    # Trampa 3, la que motivó que `_ambito_ranking` filtre SIEMPRE por la
    # familia primero: "Varios" existe en A y en B.
    por_par = ranking("A", "Varios")
    suelto = df[_subfam_normalizada(df, "SUB") == "Varios"]
    check("recortar por el PAR (familia, subfamilia) no mezcla familias",
          float(por_par["valor"].sum()) == 50.0
          and float(suelto["VAL"].sum()) == 150.0,
          f"par={por_par['valor'].sum()} suelto={suelto['VAL'].sum()}")

    # Parquet sin columna de Subfamilia: el recorte se queda en la familia
    # en vez de reventar o de devolver vacío.
    sin_sub = ranking("A", "Carnes", col_subfam=None)
    check("sin columna de Subfamilia el ranking se recorta a la familia",
          abs(sin_sub["valor"].sum() - float(fam.iloc[0]["valor"])) < 1e-9)
    flaco = ranking("A", None, col_cant=None, col_um=None)
    check("sin columnas de Cantidad/UM el ranking no revienta",
          (flaco["cantidad"] == 0).all() and (flaco["um"] == "").all())

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

    def o_ranking(dd, col_prod, col_fecha, col_valor, col_cant, col_punit, col_um):
        filas = []
        for prod, g in dd.groupby(col_prod):
            um = ""
            if col_um and col_um in g.columns:
                _u = g[col_um].dropna()
                if not _u.empty:
                    um = str(_u.mode().iat[0])
            gp = g.dropna(subset=[col_punit])
            gp = gp[gp[col_punit] > 0].sort_values(col_fecha, kind="stable")
            ini = fin = var = None
            if not gp.empty:
                ini = float(gp[col_punit].iloc[0])
                fin = float(gp[col_punit].iloc[-1])
                var = ((fin - ini) / ini * 100) if ini else None
            filas.append({"producto": str(prod),
                          "valor": float(g[col_valor].sum()),
                          "cantidad": float(g[col_cant].sum()) if col_cant else 0.0,
                          "um": um, "inicio": ini, "fin": fin, "var_pct": var})
        return {f["producto"]: f for f in filas}

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

    def ranking_por_producto(df):
        return {r["producto"]: {k: (None if (isinstance(v, float) and np.isnan(v)) else v)
                                for k, v in r.items() if k != "pct"}
                for r in df.to_dict("records")}

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
    rk = _pr._prod_ranking(d, "p", "f", "valor", "cant", "precio", "um")
    check("ranking: cada producto dice lo mismo que el bucle",
          iguales(ranking_por_producto(rk),
                  {k: o_ranking(d, "p", "f", "valor", "cant", "precio", "um")[k]
                   for k in ranking_por_producto(rk)}),
          rk.to_dict("records"))
    check("ranking: compras del mismo día -> la primera es la de más arriba",
          float(rk.set_index("producto").loc["A", "inicio"]) == 10.0)
    check("ranking: montos iguales al céntimo van por nombre",
          rk["producto"].tolist()[-3:] == ["B", "E", "C"], rk["producto"].tolist())
    check("ranking: sin columnas de Cantidad/UM no revienta",
          (_pr._prod_ranking(d, "p", "f", "valor", None, "precio", None)["um"]
           == "").all())
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
    rg = _pr._prod_ranking(g, "p", "f", "valor", "cant", "precio", "um")
    o_rg = o_ranking(g, "p", "f", "valor", "cant", "precio", "um")
    check("al azar: ranking, producto por producto",
          iguales(ranking_por_producto(rg),
                  {k: o_rg[k] for k in ranking_por_producto(rg)}))
    check("al azar: ranking ordenado por monto (céntimos) y nombre",
          list(zip(rg["valor"].round(2) * -1, rg["producto"]))
          == sorted(zip(rg["valor"].round(2) * -1, rg["producto"])))
    prods = sorted(g["p"].unique())[:80]
    check("al azar: cierres", iguales(
        _vo._vol_cierres_semanales(g, prods, "p", "precio", "f", sg),
        o_cierres(g, prods, "p", "precio", "f", sg)))
    check("al azar: candidatos", iguales(
        _vo._vol_candidatos(g, "p", "precio", "f", "valor", sg[-12:],
                            min_gasto=300.0, min_cobertura=0.4),
        o_candidatos(g, "p", "precio", "f", "valor", sg[-12:], 300.0, 0.4)))

    # ── La guarda de forma ──────────────────────────────────────────────
    for fn in (_cm.moda_por_grupo, _va._unidades_por, _pr._prod_ranking,
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


def _pruebas_etiqueta_barras_producto():
    """Lo que dicen las barras de la Evolución de Producto (2026-09-20).

    Las funciones son puras, así que se prueban por valor: sin Streamlit,
    sin R2, sin navegador.

    Lo que se puede romper en silencio y acá falla ruidoso:

      1. Que el conteo de documentos vuelva a ser `nunique` del NÚMERO
         pelado. Medido sobre compras.parquet el 2026-09-20: 14.555 números
         distintos contra 17.988 pares (número, proveedor) — el número solo
         se come el 19% de los comprobantes, porque dos proveedores numeran
         su "F001-123" cada uno por su cuenta. Un conteo bajo no se ve: es
         un número creíble.
      2. Que la variación del VALOR deje de pasar por la #470 y vuelva a
         compararse contra un período que la ventana corta. La ventana de
         esta tarjeta es RODANTE, así que la primera y la última barra están
         cortadas siempre: medido, «jul» decía +181% contra un «jun» que
         eran 11 días de mes.
      3. Que la del PRECIO se le pegue a esa guarda. Es lo contrario: el
         valor es una suma (medio mes suma la mitad) y el precio un
         promedio (medio mes promedia igual de bien), así que el precio
         conserva su variación donde el valor la pierde.
      4. Que la etiqueta rotada vuelva a tener saltos de línea. Rotada, cada
         renglón se apila a lo ANCHO y el hueco por barra son 30px: la
         etiqueta de tres renglones deja de leerse (regla #91, Plotly la
         ESCALA en vez de ocultarla, así que el DOM no lo canta).
      5. Que un parquet sin columna de documento o sin proveedor reviente.
         Pasa en modo demo y en cualquier reporte al que le falte la
         columna: los dos pedazos son opcionales y se caen solos.
      6. Que el eje o el hover vuelvan a rotular el mes en INGLÉS (#241).
    """
    fallos = 0

    def check(nombre, ok, detalle=""):
        nonlocal fallos
        if ok:
            print(f"OK    barras producto · {nombre}")
        else:
            fallos += 1
            print(f"FALLA barras producto · {nombre}"
                  f"{': ' + detalle if detalle else ''}")

    from datetime import date

    from graficos.compras._comun import _variaciones
    from graficos.compras.producto import (
        _compras_del_periodo, _etiquetas_barras, _fmt_cant_um, _fmt_docs, _hover_barras,
        _periodo_del_clic, _prod_serie_periodo, _rotulo_periodo, _var_precio,
    )

    # Trampa 1: el MISMO número de documento en dos proveedores distintos,
    # el mismo mes. Son DOS comprobantes.
    df = pd.DataFrame({
        "FECHA": pd.to_datetime(["2026-08-01", "2026-08-02", "2026-08-03",
                                 "2026-09-01"]),
        "PUNIT": [10.0, 12.0, 14.0, 20.0],
        "CANT": [1.0, 2.0, 3.0, 4.0],
        "VAL": [100.0, 200.0, 300.0, 700.0],
        "DOC": ["F001-1", "F001-1", "F001-1", "F001-2"],
        "PROV": ["Alfa", "Beta", "Alfa", "Alfa"],
    })
    agg = _prod_serie_periodo(df, "FECHA", "PUNIT", "CANT", "VAL", "Mes",
                              col_docu="DOC", col_prov="PROV")
    check("un documento es (número, proveedor), no el número solo",
          int(agg["docs"].iloc[0]) == 2, f"{agg['docs'].iloc[0]}")
    check("los proveedores del período van de mayor a menor",
          [n for n, _ in agg["provs"].iloc[0]] == ["Alfa", "Beta"],
          str(agg["provs"].iloc[0]))
    check("y con su valor, no con su conteo",
          abs(agg["provs"].iloc[0][0][1] - 400.0) < 1e-9,
          str(agg["provs"].iloc[0]))

    # Trampa 5: sin columna de documento ni de proveedor.
    flaca = _prod_serie_periodo(df, "FECHA", "PUNIT", "CANT", "VAL", "Mes")
    check("sin columnas de documento/proveedor la serie no revienta",
          bool(flaca["docs"].isna().all()) and bool(flaca["provs"].isna().all()))

    # Trampa 2: la ventana rodante corta el primer mes y el último. Sólo la
    # barra del medio puede decir un porcentaje.
    claves = ["2026-06", "2026-07", "2026-08", "2026-09"]
    valores = [6000.0, 17000.0, 18700.0, 9000.0]
    rng = (date(2026, 6, 20), date(2026, 9, 19))
    var = _variaciones(claves, valores, "Mes", rng)
    check("un mes que la ventana corta dice «parcial», no un %",
          [v[0] for v in var] == ["parcial", "ant_parcial", "ok", "parcial"],
          str([v[0] for v in var]))
    check("y el que sí, es % contra la barra ANTERIOR",
          abs(var[2][1] - 10.0) < 1e-9, str(var[2]))

    # LA ETIQUETA SON DOS CIFRAS, no cuatro (2026-09-20, regla #480): la
    # variación y los documentos salieron de la barra a pedido —«la etiqueta
    # de datos es bastante larga»— y viven en el hover y en la tabla de
    # abajo, que desde ese día está siempre a la vista dentro de la tarjeta.
    # Que NO estén es lo que se vigila acá: volver a meterlas es volver a
    # comerse el 45% del alto del gráfico.
    et = _etiquetas_barras([10.0, 12.0, 14.0, 20.0], valores)
    check("la etiqueta lleva precio y valor",
          all(x in et[2] for x in ("S/ 14.00", "S/ 19k")), et[2])
    check("y NO lleva ni documentos ni variación",
          all(x not in et[2] for x in ("docs", "%", "parcial")), et[2])
    check("sin rotar, la etiqueta son dos renglones",
          et[2].count("<br>") == 1, et[2])
    check("el singular de documento no dice '1 docs'",
          _fmt_docs(1) == "1 doc" and _fmt_docs(2) == "2 docs")
    # Trampa 4.
    rot = _etiquetas_barras([10.0, 12.0, 14.0, 20.0], valores, rotada=True)
    check("rotada, la etiqueta es UN renglón", "<br>" not in rot[2], rot[2])
    # LA CANTIDAD (2026-10-02, regla #582): derecha es el tercer renglón;
    # girada reemplaza al valor —con los tres, la etiqueta girada se salía
    # de la figura—.
    _cants = [5.0, 12.5, 315.0, 1240.0]
    et = _etiquetas_barras([10.0, 12.0, 14.0, 20.0], valores,
                           cantidades=_cants, um="KG")
    check("con cantidad, son tres renglones y el último es la cantidad",
          et[2].count("<br>") == 2 and et[2].endswith("315 KG"), et[2])
    rot = _etiquetas_barras([10.0, 12.0, 14.0, 20.0], valores, rotada=True,
                            cantidades=_cants, um="KG")
    check("rotada lleva precio y cantidad, sin el valor",
          rot[2] == "S/ 14.00 · 315 KG", rot[2])
    check("la cantidad lleva un decimal sólo si es chica y lo tiene",
          [_fmt_cant_um(c, "KG") for c in _cants]
          == ["5 KG", "12.5 KG", "315 KG", "1,240 KG"],
          str([_fmt_cant_um(c, "KG") for c in _cants]))

    # ── EL CLIC EN UNA BARRA → SU PERÍODO (2026-09-20, regla #480) ─────
    # Acá el eje NO es lineal (`_eje_x_kwargs` dibuja sobre los timestamps
    # de los buckets), así que la `x` del evento vuelve como FECHA y no como
    # índice: la prima de Semanal (`_clave_del_clic`) no sirve. Lo que se
    # mira primero es la posición, que Streamlit manda en `point_index`
    # —snake_case, ver el docstring de `st.plotly_chart`— y no depende del
    # tipo de eje.
    #
    # Se prueba acá y no clickeando en el navegador porque un clic que «no
    # hace nada» tiene dos causas posibles —no llegó, o llegó y el mapeo
    # devolvió None— y desde afuera son indistinguibles. Esto separa las dos.
    _momentos = pd.to_datetime(["2026-06-01", "2026-07-01",
                                "2026-08-01", "2026-09-01"])
    check("el clic se resuelve por la POSICIÓN que manda Streamlit",
          _periodo_del_clic({"curve_number": 0, "point_number": 2,
                             "point_index": 2, "x": "2026-08-01", "y": 1.0},
                            claves, _momentos) == "2026-08",
          str(_periodo_del_clic({"point_index": 2}, claves, _momentos)))
    check("la primera barra es la 0, no la 1",
          _periodo_del_clic({"point_index": 0}, claves, _momentos)
          == "2026-06")
    check("una posición fuera de rango es un no-op, no una excepción",
          _periodo_del_clic({"point_index": 99}, claves, _momentos) is None)
    check("sin posición, la FECHA del punto alcanza",
          _periodo_del_clic({"x": "2026-07-01"}, claves, _momentos)
          == "2026-07")
    check("y una x que no casa con ningún bucket tampoco revienta",
          _periodo_del_clic({"x": "no es una fecha"}, claves,
                            _momentos) is None)

    # ── EL DETALLE DE UNA BARRA: una fila por COMPRA ───────────────────
    # El mismo `df` de arriba: tres compras en agosto, y dos de ellas
    # comparten el número «F001-1» con proveedores distintos. Son DOS
    # comprobantes, no uno (la trampa 1, otra vez, pero del lado del
    # detalle: si acá se contara el número pelado, la tabla diría dos filas
    # donde el gráfico dice tres documentos y las dos se contradirían).
    _det, _tot_det = _compras_del_periodo(
        df, "2026-08", "Mes", "FECHA", "PUNIT", "CANT", "VAL", "DOC", "PROV")
    check("el detalle lista una fila por (documento, proveedor)",
          len(_det) == 2, str(None if _det is None else len(_det)))
    # LAS COLUMNAS POR NOMBRE, y no sólo cuántas filas salieron: la primera
    # versión de `_compras_del_periodo` renombraba el resultado del groupby
    # por POSICIÓN y la forma de ese frame cambia entre pandas 2 y 3 — pasó
    # los tests en la máquina de desarrollo (pandas 3) y reventó en Cloud
    # (pandas 2.2) con un `ValueError: Length mismatch`. Regla #481.
    check("y con las columnas que la grilla espera, por nombre",
          list(_det.columns) == ["fecha", "prov", "cant", "punit", "valor",
                                 "__doc"],
          str(list(_det.columns)))
    check("y no se cuela ninguna compra de otro período",
          set(_det["fecha"]) <= {"2026-08-01", "2026-08-02", "2026-08-03"},
          str(list(_det["fecha"])))
    # Alfa compró 1+3=4 unidades por 100+300=400 → 100.00 exactos. El
    # promedio SIMPLE de sus dos líneas sería (10+14)/2 = 12, un precio que
    # nadie pagó: el ponderado es la única definición que sobrevive al
    # agregado (misma advertencia que la regla #199).
    _alfa = _det[_det["prov"].str.upper().str.startswith("ALFA")].iloc[0]
    check("el precio de una compra es el PONDERADO, no el promedio simple",
          abs(float(_alfa["punit"]) - 100.0) < 1e-9, str(_alfa["punit"]))
    check("el total tampoco promedia precios: divide valor entre cantidad",
          _tot_det["punit"] == "S/ 100.00", str(_tot_det["punit"]))
    check("sin columna de documento no hay detalle que armar, y lo dice",
          _compras_del_periodo(df, "2026-08", "Mes", "FECHA", "PUNIT",
                               "CANT", "VAL", None, "PROV") == (None, None))

    # Trampa 3: el precio conserva su variación en TODAS, incluidas las
    # parciales — es un promedio, no una suma.
    check("la variación del precio no se calcula con la guarda de parcial",
          [round(v, 1) if v is not None else None
           for v in _var_precio([10.0, 12.0, 14.0, 20.0])]
          == [None, 20.0, 16.7, 42.9],
          str(_var_precio([10.0, 12.0, 14.0, 20.0])))

    hov = _hover_barras([_rotulo_periodo(f"{c}-01", "Mes") for c in claves],
                        [10.0, 12.0, 14.0, 20.0], valores, [1, 3, 9, 2],
                        [[("ALFA SAC", 6000.0)], [("ALFA SAC", 17000.0)],
                         [("ALFA SAC", 12000.0), ("BETA EIRL", 6700.0)],
                         [("ALFA SAC", 9000.0)]],
                        variaciones=var, claves=claves, gran="Mes", rango=rng)
    check("el hover NOMBRA a los proveedores",
          "Alfa SAC" in hov[2] and "Beta EIRL" in hov[2], hov[2])
    check("el hover dice contra QUÉ barra se comparó",
          "vs jul 2026" in hov[2], hov[2])
    check("y en una parcial, por qué no hay variación",
          "sin variación" in hov[0].lower() and "días" in hov[0], hov[0])
    check("el precio lleva su variación aunque el mes esté cortado",
          "precio prom. S/ 20.00 <span" in hov[3], hov[3])
    check("el hover da el valor exacto, no el compacto",
          "S/ 18,700.00" in hov[2], hov[2])
    # Trampa 5, del otro lado.
    check("un hover sin documentos ni proveedores no revienta",
          "valor S/ 100.00" in _hover_barras(["ago"], [10.0], [100.0],
                                             None, None)[0])
    corte = _hover_barras(["ago"], [10.0], [100.0], [9],
                          [[(f"PROV {i}", 10.0 - i) for i in range(7)]])[0]
    check("con muchos proveedores, el hover corta y CUENTA el resto",
          "y 3 más" in corte, corte)

    # Trampa 6.
    check("el rótulo del período va en español",
          (_rotulo_periodo("2026-08-01", "Mes") == "ago 2026"
           and _rotulo_periodo("2026-08-31", "Semana") == "31 ago"
           and _rotulo_periodo("2026-01-01", "Año") == "2026"),
          _rotulo_periodo("2026-08-01", "Mes"))

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

    # ── 2) Las dos filas del drill de Proveedor usan las constantes ─────
    # Positiva, no negativa: sin esto, borrar las dos llamadas dejaría la
    # guarda #1 en verde. Desde el 2026-10-01 son dos constantes PROPIAS
    # —arriba `COLUMNAS_DRILL_TABLAS`, abajo `COLUMNAS_DRILL_ABAJO`, reglas
    # #578 y #579—, y se pide cada una por su nombre: el prefijo solo dejaba
    # pasar dos filas partidas con la misma.
    prov = (raiz / "graficos" / "compras" / "proveedor.py").read_text(
        encoding="utf-8")
    n_filas = [len(re.findall(r"st\.columns\(%s\b" % c, prov))
               for c in ("COLUMNAS_DRILL_TABLAS", "COLUMNAS_DRILL_ABAJO")]
    check("las 2 filas del drill de Proveedor parten con "
          "COLUMNAS_DRILL_TABLAS y COLUMNAS_DRILL_ABAJO",
          n_filas == [1, 1], f"se encontraron {n_filas}")

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
    # La vista abre en el último corte; si ese no trae una familia, la
    # semilla nacía sin ella y el TOTAL de otro corte sumaba sin avisar.
    from graficos.ajuste._comun import FAMILIAS_DE_ENTRADA, estado_filtros_vista
    _full = pd.DataFrame({
        "F": pd.to_datetime(["2026-09-02"] * 3 + ["2026-09-15"] * 2),
        "FAMILIA": ["ALIMENTOS", "ENVASES Y EMBALAJES", "VINOS Y ESPUMANTES",
                    "ALIMENTOS", "VINOS Y ESPUMANTES"],
        "AREA": ["X"] * 5, "AV": [-1.0, -2.0, 3.0, 4.0, -5.0],
    })
    _est = estado_filtros_vista(
        _full, _full, "F", "FAMILIA", "AREA", "AV",
        k_corte="test_ajcas_corte", k_familia="test_ajcas_fam",
        k_area="test_ajcas_area", familias=FAMILIAS_DE_ENTRADA)
    check("abre en el último corte, que no trae ENVASES",
          _est["corte"]["etiqueta_anio"], "15 set 2026")
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
    check("un producto por código, de la A a la Z por nombre",
          L.productos.index.tolist(), ["04", "02", "01"])
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
          [("p", ""), ("a", "04"), ("a", "04"), ("p", ""), ("a", "02"),
           ("p", ""), ("a", "01"), ("a", "01")])
    check("la fila de área lleva el ÁREA en «nombre» y deja vacío lo del "
          "producto", tuple(f.loc[1, ["nombre", "familia", "codigo"]]),
          ("COCINA", "", ""))
    check("familia y subfamilia se escriben como nombre propio",
          f.loc[3, "familia"], "Bebidas con Alcohol")

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
    # (`Lado.anulados`), sobre SU cuenta: la guarda compara contra ella.
    check("cuenta las anuladas por salida, como la fila de KPI de su vecina",
          nota[0], f"{mp.SALIDAS.anulados(mp.no_suman(bl)[0])} no suman")
    check("el tooltip dice cuánto no suma", "S/ 30" in nota[1], True)
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
    check("cinco cuadros en las filas del Detalle",
          sum(len(f) for f in filas), 5)
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
          [("movimientos.py", "mov", "detsal", 5)])
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
    tri = [s for s in fig.layout.shapes
           if s.type == "path" and s.fillcolor is not None]
    check("y su celda lleva el triángulo", len(tri), 1)
    sin = _h._fig_mapa([celdas], [(2026, 32)], "Semana", "venta", [],
                       [19, 21], raros=False)
    check("con el interruptor apagado no hay triángulo",
          len([s for s in sin.layout.shapes
               if s.type == "path" and s.fillcolor is not None]), 0)
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
    from graficos import movimientos_periodo as mp
    from tema import GRIS_TEXTO_SUAVE, PALETA_SERIES

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
          ["7–13 set 2026", "14–20 set 2026"])

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

    fig = mp.figura_periodos(v, alturas.COMPACTO, titulo="t", foco="2026-S37")
    check("figura: un trazo por tramo y sin leyenda (la fila de KPI lo es)",
          (len(fig.data), fig.layout.showlegend), (4, False))
    check("figura: la etiqueta va en el tramo de más arriba con valor",
          [i for i, t in enumerate(fig.data) if t.text and t.text[1]], [3])
    check("figura: el foco atenúa las otras barras por COLOR",
          isinstance(fig.data[0].marker.color, tuple)
          and fig.data[0].marker.color[0] == PALETA_SERIES[1]
          and fig.data[0].marker.color[1].startswith("rgba("), True)
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

    # ── Deteccion de anomalias en Ajuste ────────────────────────────────
    # ── Escala de tiempo estilo tabla dinamica (estado_rango.py) ────────
    fallos += _pruebas_escala_tiempo()

    # ── La regla de referencia bajo el riel: que los rótulos no se pisen ─
    fallos += _pruebas_regla_riel()

    fallos += _pruebas_anomalias()

    # ── El chip de la mini contra el corte anterior ──────────────────────
    fallos += _pruebas_resumen_ajuste()

    # ── Ajuste › Evolución: períodos compartidos, sobrante/faltante/% ────
    fallos += _pruebas_evolucion_ajuste()

    # ── Ajuste › Mapa de calor: la cantidad es la que el monto multiplica ─
    fallos += _pruebas_cantidad_del_mapa_ajuste()

    # ── Inventario › Productos: el grano y el despliegue de áreas ────────
    fallos += _pruebas_listado_inventario()
    fallos += _pruebas_inventario_activos()
    fallos += _pruebas_kardex()

    # ── Movimientos › las tarjetas «por período»: qué cuenta y qué no ────
    fallos += _pruebas_movimientos_periodo()

    # ── Ventas › un ítem una vez, aunque se haya pagado con dos formas ───
    fallos += _pruebas_ventas_un_item_una_vez()

    # ── Ventas › Mix de carta: las cuentas por nombre y el año pasado ────
    fallos += _pruebas_ventas_mix()

    # ── Ventas › Análisis de platos: puestos, movimiento, por día ────────
    fallos += _pruebas_ventas_platos()

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

    # ── Drill Familia › Subfamilia › Producto: que los 3 niveles cuadren ─
    fallos += _pruebas_drill_familia_subfamilia()

    # ── Lo que dice cada barra de la Evolución de Producto ──────────────
    fallos += _pruebas_etiqueta_barras_producto()

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
