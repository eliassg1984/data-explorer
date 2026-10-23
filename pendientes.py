"""
pendientes — Inicio › «Pendientes del período» (2026-10-23, regla #711).

Lo que conviene mirar antes de cerrar el mes, en una pantalla: una fila por
señal, agrupadas por área, con un punto de color y el salto a la vista
donde se resuelve. Etapa 4 de la navegación del boceto del rail compacto
(#708), sobre el boceto aprobado tal cual.

NINGUNA SEÑAL SE CALCULA ACÁ. La regla del boceto: «cada señal sale de la
vista que la calcula hoy, de lo que esa vista ya dejó en caché. Si todavía
no se calculó, dice "sin calcular" y no 0». Este módulo recibe lo que esas
vistas dejaron —en `fuentes`, armado por `graficos/pendientes.py`— y sólo
decide el color y el texto de cada fila. Puro: lo lee `test_pendientes.py`.

    Consistencia de datos (Costos)   siete controles (`DE_CONSISTENCIA`),
                                     con el color de `consistencia_maestro`
    Análisis de diferencias (Ajuste) el faltante sin pista y lo vendido sin
                                     descontar, del último cierre
    Para revisar (Producción)        el peso por unidad raro
    Recetas vs Porcionado (Recetas)  los cortes que las recetas no siguen
    Costo de ventas (Costos)         lo sin explicar del último mes cerrado,
                                     con la regla del ⚠ de esa vista
    La hora de cada parquet          los que pasaron `HORAS_DATO_VIEJO`
"""

import math

import consistencia_maestro as cm

ROJO, AMBAR, VERDE, SIN = "rojo", "ambar", "verde", "sin"
"""Los cuatro estados de una fila. `SIN` es «sin calcular»: la vista que la
calcula no lo hizo todavía con los datos de hoy. Nunca un cero."""

AREAS = {
    "Inventario": "inventory_2", "Producción": "skillet", "Compras": "shopping_cart",
    "Recetas": "receipt_long", "Costos": "calculate", "Ventas": "payments",
    "Datos": "database",
}
COLUMNAS = (("Inventario", "Producción"), ("Compras", "Recetas"),
            ("Costos", "Ventas", "Datos"))
"""Cómo se reparten las áreas en las tres columnas del boceto."""

# Los destinos: (reporte, clave del rail, id de la vista, cómo se la nombra).
DIFERENCIAS = ("Ajuste de Inventario", "ajuste_graf_tipo", "Diferencias",
               "Análisis de diferencias")
CONSISTENCIA = ("Costos", "costos_graf_tipo", "Consistencia de datos",
                "Consistencia de datos")
REVISAR_MERMA = ("Producción", "prod_graf_tipo", "Merma para revisar", "Para revisar")
REVISAR_RECETAS = ("Recetas", "rec_graf_tipo", "Revisar recetas",
                   "Recetas vs Porcionado")
COSTO_VENTAS = ("Costos", "costos_graf_tipo", "Costo de ventas", "Costo de ventas")

DE_CONSISTENCIA = (
    # (control, área, lo que dice debajo del nombre)
    ("s2", "Inventario", "se descargó antes de que entrara"),
    ("m3", "Producción", "merma negativa, del 90 % o fuera de lo suyo"),
    ("p4", "Compras", "el proveedor la declaró y el Almacén no la tiene"),
    ("m4", "Compras", "a 2,5 veces o a menos de 0,4 de su precio"),
    ("r3", "Recetas", "el costo del plato salta"),
    ("c4", "Costos", "multiplica su costo por la cantidad"),
    ("m9", "Ventas", "un día a 3 veces o más lo de ese usuario"),
)
"""Las señales que salen de Costos › «Consistencia de datos»: el nombre y el
color son los del control (`consistencia_maestro.CONTROLES`, `estado`)."""

UMBRAL_SIN_DESCONTAR = 20.0
"""S/ a costo desde los que lo vendido sin descontar al contar se dice: la
misma vara que la tarjeta de «Análisis de diferencias»
(`graficos/ajuste/_diferencias.py::_kpi_sin_descontar`)."""

VENTANA_COSTOS = 6
"""Cuántos meses cerrados mira la regla del ⚠ de Costo de ventas: la ventana
con que abre la tabla de esa vista."""

ORDEN = {ROJO: 0, AMBAR: 1, SIN: 2, VERDE: 3}


def _soles(v):
    """«S/ 1,234», y «−S/ 5,980» con signo, como el resto de la app."""
    return f"{'−' if round(v) < 0 else ''}S/ {abs(v):,.0f}"


def _n(v, uno, varios):
    return f"{v:,} {uno if v == 1 else varios}"


def _fila(area, titulo, estado, valor, por, destino, abrir=None, ayuda=""):
    r, sk, vista, rot = destino if destino else (None, None, None, "")
    return {"area": area, "t": titulo, "estado": estado, "v": valor, "por": por,
            "ir_rot": rot, "ayuda": ayuda,
            "ir": ({"r": r, "sk": sk, "v": vista, "abrir": abrir} if destino else None)}


def de_consistencia(resultado):
    """Las filas de `DE_CONSISTENCIA` desde lo de `data.consistencia_maestro`
    (`{"hoy", "casos"}`), o todas «sin calcular» si es None."""
    controles = {c.id: c for c in cm.CONTROLES}
    casos = (resultado or {}).get("casos") or {}
    filas = []
    for cid, area, por in DE_CONSISTENCIA:
        c = controles[cid]
        if resultado is None or cid not in casos:
            filas.append(_fila(area, c.nombre, SIN, "sin calcular", por,
                               CONSISTENCIA, cid, c.mide))
            continue
        r = casos[cid]
        est = cm.estado(c, r)
        if est == cm.FALLO:
            filas.append(_fila(area, c.nombre, SIN, "no se pudo calcular", por,
                               CONSISTENCIA, cid, f"{c.mide}. {r}"))
            continue
        n = len(r)
        soles = r["soles"].sum(min_count=1) if n else float("nan")
        valor = "ninguno" if not n else (
            f"{n:,}" + (f" · {_soles(soles)}" if soles == soles and soles else ""))
        filas.append(_fila(area, c.nombre, est, valor, por, CONSISTENCIA, cid,
                           c.mide))
    return filas


def de_diferencias(r, cierre):
    """El faltante sin pista y lo vendido sin descontar del último cierre,
    desde lo de `data.diferencias_ajuste_sesion` (None: sin calcular).
    `cierre` es el nombre de la sesión («Cierre de setiembre»)."""
    t1 = "Faltante sin pista del último cierre"
    t2 = "Vendido y sin descontar al contar"
    p1 = f"{cierre or 'el último cierre'} · ninguna pista lo explica"
    p2 = "el descargo de ventas no lo había tomado"
    if r is None or "lineas" not in r:
        return [_fila("Inventario", t1, SIN, "sin calcular", p1, DIFERENCIAS),
                _fila("Inventario", t2, SIN, "sin calcular", p2, DIFERENCIAS)]
    lin = r["lineas"]
    # El lado lo dice la CANTIDAD, como en la vista (#651).
    fal = lin[(lin["q"] < 0) & (lin["n_pistas"] == 0)]
    v1, n1 = float(-fal["v"].sum()), len(fal)
    f1 = _fila("Inventario", t1, ROJO if n1 else VERDE,
               f"{_soles(v1)} · {_n(n1, 'línea', 'líneas')}" if n1 else "ninguna",
               p1, DIFERENCIAS)
    v2 = float(lin["pend_v"].sum()) if "pend_v" in lin.columns else 0.0
    f2 = _fila("Inventario", t2, AMBAR if v2 >= UMBRAL_SIN_DESCONTAR else VERDE,
               _soles(v2) if v2 >= UMBRAL_SIN_DESCONTAR else "nada", p2, DIFERENCIAS)
    return [f1, f2]


def de_pesos(p):
    """El peso por unidad raro de los porcionamientos de los últimos 30 días
    (`{"n", "docs"}`, de `movimientos_merma.pesos_por_unidad`)."""
    t = "Peso por unidad raro"
    por = "mueve el precio de todos los cortes"
    if p is None:
        return _fila("Producción", t, SIN, "sin calcular", por, REVISAR_MERMA)
    n, docs = p["n"], p["docs"]
    return _fila("Producción", t, ROJO if n else VERDE,
                 f"{_n(n, 'corte', 'cortes')} · {_n(docs, 'porcionamiento', 'porcionamientos')}"
                 if n else "ninguno", por, REVISAR_MERMA,
                 ayuda="Un corte al que se le asignó un peso por unidad fuera de "
                       "lo habitual en los últimos 30 días: el Almacén reparte el "
                       "precio por peso, y el corte entra a ese precio (regla #647).")


def de_revisar_recetas(r):
    """Los cortes que las recetas no siguen en 30 días, de lo que dejó
    Recetas › «Recetas vs Porcionado» (`resumen_pendiente`), o sin calcular."""
    t = "Cortes que las recetas no siguen"
    por = "ninguna receta los usa, o piden más de lo porcionado"
    if r is None:
        return _fila("Recetas", t, SIN, "sin calcular", por, REVISAR_RECETAS,
                     ayuda="Se calcula al abrir «Recetas vs Porcionado».")
    n = r["n"]
    return _fila("Recetas", t, AMBAR if n else VERDE,
                 (_n(n, "corte", "cortes") + (f" · {_soles(r['valor'])}" if r.get("valor") else ""))
                 if n else "ninguno", por, REVISAR_RECETAS)


def umbral_sin_explicar(tasas):
    """El umbral del ⚠ de Costo de ventas (`costos_vistas.js::cifras`): más
    del doble de la mediana de la tasa sin explicar y por lo menos 2 puntos
    encima, con tres períodos o más. None si no hay con qué comparar."""
    ok = sorted(x for x in tasas if x is not None and math.isfinite(x))
    m = len(ok)
    if m < 3:
        return None
    med = ok[(m - 1) // 2] if m % 2 else (ok[m // 2 - 1] + ok[m // 2]) / 2
    return max(2 * med, med + 0.02)


def de_costos(meses):
    """Lo sin explicar del último mes cerrado. `meses` es una lista, del más
    viejo al más nuevo, de `(rótulo, sin explicar en S/, venta)` de los meses
    cerrados (`resumen_ejecutivo.costo_del_mes`). Rojo si su tasa pasa la
    regla del ⚠ de Costo de ventas sobre los últimos `VENTANA_COSTOS`."""
    t = "Sin explicar del último mes"
    if not meses:
        return _fila("Costos", t, SIN, "sin calcular", "consumo carta − costo del "
                     "Sistema − bajas", COSTO_VENTAS)
    ventana = meses[-VENTANA_COSTOS:]
    tasas = [(f / v if v else None) for _r, f, v in ventana]
    rot, falt, _v = ventana[-1]
    um = umbral_sin_explicar(tasas)
    raro = um is not None and tasas[-1] is not None and tasas[-1] > um
    por = f"{rot} · " + ("más del doble de lo habitual" if raro
                         else "dentro de lo habitual" if um is not None
                         else "sin meses para comparar")
    return _fila("Costos", t, ROJO if raro else VERDE,
                 f"{_soles(falt)}" + (f" · {tasas[-1]:.1%}" if tasas[-1] is not None else ""),
                 por, COSTO_VENTAS)


def de_datos(horas, umbral):
    """Los parquets que no se refrescan hace más de `umbral` horas.
    `horas` es `{archivo: horas}` (None si no se pudo saber ninguno)."""
    t = "Parquets sin refrescar"
    if not horas:
        return _fila("Datos", t, SIN, "sin dato", "la hora de cada archivo en R2", None)
    viejos = sorted((a for a, h in horas.items() if h is not None and h > umbral),
                    key=lambda a: -horas[a])
    if not viejos:
        return _fila("Datos", t, VERDE, "ninguno", f"todos de menos de {umbral} h", None)
    return _fila("Datos", t, AMBAR, f"{len(viejos):,} de {len(horas):,}",
                 f"más de {umbral} h · «Actualizar», en la franja", None,
                 ayuda=" · ".join(f"{a.removesuffix('.parquet')} {horas[a]:.0f} h"
                                  for a in viejos[:8]))


def armar(fuentes, umbral_horas):
    """Lo que dibuja la pieza: las filas por área en las tres columnas, y
    cuántas hay de cada estado. `fuentes` tiene `consistencia`,
    `diferencias`, `cierre`, `pesos`, `revisar`, `costos` y `horas` (cada
    una None si no está)."""
    filas = (de_consistencia(fuentes.get("consistencia"))
             + de_diferencias(fuentes.get("diferencias"), fuentes.get("cierre"))
             + [de_pesos(fuentes.get("pesos")), de_revisar_recetas(fuentes.get("revisar")),
                de_costos(fuentes.get("costos")),
                de_datos(fuentes.get("horas"), umbral_horas)])
    por_area = {a: [] for a in AREAS}
    for f in filas:
        por_area[f["area"]].append(f)
    for a in por_area:
        por_area[a].sort(key=lambda f: ORDEN[f["estado"]])
    cuenta = {e: sum(1 for f in filas if f["estado"] == e) for e in ORDEN}
    return {
        "columnas": [[{"n": a, "i": AREAS[a], "filas": por_area[a]} for a in col]
                     for col in COLUMNAS],
        "cuenta": cuenta,
    }
