"""
graficos.movimientos_comun — las piezas que miran los DOS parquets a la vez.

Los dos parquets describen las DOS MITADES de un mismo flujo de stock:
Requerimiento es lo que Almacén Central le entrega a un área de producción
(Cocina, Barra, Pastelería...); Salidas es la baja que esa misma área
registra después (consumo, merma, evento — ver "Tipo Descargo"). Desde el
2026-09-05 viven en UN reporte, «Movimientos» (`graficos/movimientos.py`).

Este módulo tiene lo que NO es de un lado ni del otro:

  · `_rango_vigente()` — el recorte por fecha, en un solo sitio (ver #321).
    Es lo único que sigue en uso: lo importan `movimientos_periodo.py`,
    `movimientos_consumo.py` y `movimientos_destino.py`, para cuando la
    vista no trae su propio rango (regla #617).
  · `_cargar_los_dos_lados()` — los dos parquets normalizados y sin
    anulados, con las MISMAS listas de columnas candidatas para los dos
    lados. Es un precedente de carga cruzada entre dashboards, igual que
    `recetas_comun.py::_cargar_flujo_compras` con compras.parquet.
  · `_ranking_proporcion_baja()` — EN QUÉ: una barra por producto, la
    proporción de lo requerido que terminó dada de baja (ver #323). Sin
    caller: ver abajo.

El cruce se gana el lugar porque hay overlap real de producto: 726 de los
968 productos de Salidas (75%) también aparecen en Requerimientos,
confirmado con DuckDB directo contra R2 real el 2026-08-13.

(Acá decía "a diferencia de Receta Base/Venta, que con 0% overlap NUNCA se
cruzan". Ese 0% era una medición contra la columna equivocada y se corrigió
el 2026-09-04 — los dos parquets de receta SÍ se cruzan, y desde entonces
comparten una sola página. Ver `arquitectura.md` regla #303.)

SIN CALLER DESDE EL 2026-09-13, y a propósito: `_ranking_proporcion_baja`
ya no cuelga de la pila. Las secciones que abrían la página —la Evolución
(requerido vs dado de baja), este ranking y el de Sub Almacén, que vivía en
`movimientos.py`— se retiraron a pedido («eliminemos los 3 gráficos
iniciales») y en su lugar entró la cadena de cuatro tablas de
`drill_tablas.py`. El ranking se conserva entero, con sus mediciones,
porque volver a colgarlo es una entrada en `_PILA` + una en `_DIBUJANTES`;
lo que NO hay que hacer es editarlo "de paso" creyendo que algo lo dibuja.
Ver regla #411.

LA EVOLUCIÓN SE BORRÓ EL 2026-10-08, con la escala de tiempo vieja (regla
#618): era la única sección de Movimientos con `selector_fecha_tarjeta`, y
para eso cargaba una copia de más de 200 líneas del CSS de aquel selector
(`_CSS_SELECTOR_FECHA`, la de la regla #320) que ya no vestía a nadie. Si
vuelve, sale del historial (`git log -S _evolucion_movimientos`), y con el
CSS del selector de hoy, no con esa copia.

Hasta el 2026-09-05 acá vivía también `_chip_movimientos`, el segmented
control Requerimiento/Salidas que navegaba entre los dos reportes. Se fue
con la fusión: no hay dos destinos que alternar. Ver regla #322.

Dos límites reales del DATO, no del código — no se resuelven con más
columnas, hay que diseñar la vista alrededor de ellos:
  - No hay llave documento-a-documento: `COD REQUERIMIENTO` y `COD SALIDA`
    numeran en secuencias independientes. El cruce es agregado por
    producto/familia/período ("¿cuánto entró vs cuánto se dio de baja en
    este mes?"), nunca "este Requerimiento se resolvió con esta Salida".
  - `salidas.parquet` NO trae el área/sub almacén que originó la baja (solo
    Requerimientos tiene esa columna) — estas vistas no pueden desglosar
    por área, solo por producto/familia.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import cargar as _cargar_reporte
from tema import ACENTO, AJUSTE_NEG, GRIS_TEXTO_SUAVE
from graficos.base import _compras_layout, _compras_truncar, _resolver
from graficos import alturas
import franja_fecha


# ─── El rango vigente, en una sola función ─────────────────────────────────
def _rango_vigente():
    """`(inicio, fin_EXCLUSIVO)` del rango canónico del reporte, o None.

    El fin viene como `fin + 1 día` y se compara con `<`, NO con `<=`: las
    dos columnas de fecha de estos parquets traen hora en el 100% de sus
    filas, así que un `<=` contra medianoche se come el último día entero
    del rango. Medido, documentado y corregido en la regla #321 — vive acá
    para que los sitios que recortan por fecha en esta página
    (`movimientos_periodo.py`, `movimientos_consumo.py`,
    `movimientos_destino.py`, y con la misma forma
    `movimientos.py::rango_de_vista`) no puedan volver a escribirlo
    distinto.

    Devuelve None cuando la franja todavía no publicó su contexto o el rango
    está a medio elegir; el llamador muestra entonces el histórico entero,
    que es lo que ya hacía.
    """
    ctx = franja_fecha.contexto()
    rango = st.session_state.get(ctx["k_rango"]) if ctx else None
    if not (isinstance(rango, (tuple, list)) and len(rango) == 2 and all(rango)):
        return None
    return (pd.Timestamp(rango[0]),
            pd.Timestamp(rango[1]) + pd.Timedelta(days=1))


def _cargar_los_dos_lados():
    """Los dos parquets del flujo, normalizados y sin anulados.

    Las listas de candidatos viven ACÁ y no en el llamador: nacieron para
    que la Evolución (borrada en la regla #618) y el ranking de proporción
    miraran exactamente las mismas columnas, o las dos vistas de la misma
    página habrían dicho números distintos de la misma cosa.
    """
    req = _cargar_lado(
        "requerimientos.parquet",
        col_fecha_cand=["Fecha Registro", "FECHA REGISTRO"],
        col_cod_cand=["Codigo Producto", "CODIGO PRODUCTO"],
        col_prod_cand=["Nombre Producto", "NOMBRE PRODUCTO"],
        col_fam_cand=["Nombre Familia", "NOMBRE FAMILIA"],
        col_valor_cand=["Valor Item", "VALOR ITEM"],
        col_cant_cand=["Cantidad", "CANTIDAD"],
        col_estado_cand=["Nombre Estado Requerimiento",
                         "NOMBRE ESTADO REQUERIMIENTO"],
        estados_excluir=("ANULADO",),
    )
    sal = _cargar_lado(
        "salidas.parquet",
        col_fecha_cand=["Fecha registro", "FECHA REGISTRO"],
        col_cod_cand=["Cod Producto", "COD PRODUCTO", "Codigo Producto"],
        col_prod_cand=["Nombre Producto", "NOMBRE PRODUCTO"],
        col_fam_cand=["Nombre Familia", "NOMBRE FAMILIA"],
        col_valor_cand=["Valor Neto", "VALOR NETO"],
        col_cant_cand=["Cant Salida", "CANT SALIDA"],
        col_estado_cand=["Nombre Estado Salida", "NOMBRE ESTADO SALIDA"],
        estados_excluir=("ANULADO",),
    )
    return req, sal


# ─── Carga del par de parquets ───────────────────────────────────────────────
def _cargar_lado(archivo, *, col_fecha_cand, col_cod_cand, col_prod_cand,
                 col_fam_cand, col_valor_cand, col_cant_cand, col_estado_cand,
                 estados_excluir):
    """Carga y normaliza un lado (Requerimientos o Salidas) del comparativo:
    resuelve columnas, filtra estados anulados y devuelve un df con columnas
    de trabajo `_fecha/_cod/_prod/_fam/_valor/_cant`, o None si falta alguna
    columna imprescindible (fecha, código de producto, nombre, y al menos
    una métrica)."""
    df = _cargar_reporte(archivo)
    if df is None or df.empty:
        return None
    col_fecha = _resolver(df, col_fecha_cand)
    col_cod = _resolver(df, col_cod_cand)
    col_prod = _resolver(df, col_prod_cand)
    col_fam = _resolver(df, col_fam_cand)
    col_valor = _resolver(df, col_valor_cand)
    col_cant = _resolver(df, col_cant_cand)
    col_estado = _resolver(df, col_estado_cand)
    if not (col_fecha and col_cod and col_prod and (col_valor or col_cant)):
        return None

    d = df.copy()
    if col_estado and estados_excluir:
        excl = {e.upper() for e in estados_excluir}
        # .fillna ANTES de .astype(str): las columnas que trae DuckDB usan un
        # dtype "str" con NA propio (Arrow-backed) donde .astype(str) NO
        # convierte el nulo a texto — deja un float NaN suelto adentro de una
        # Series "de texto" (mismo tipo de trampa que ya documenta
        # `_activo()` en recetas_comun.py). Sin el fillna, un `sorted()` más
        # abajo sobre esos valores revienta comparando float con str.
        d = d[~d[col_estado].fillna("").astype(str).str.upper().isin(excl)]
    d["_fecha"] = pd.to_datetime(d[col_fecha], errors="coerce")
    d["_cod"] = d[col_cod].fillna("").astype(str).str.strip()
    d["_prod"] = d[col_prod].fillna("").astype(str)
    d["_fam"] = d[col_fam].fillna("Sin familia").astype(str) if col_fam else "Sin familia"
    d["_valor"] = pd.to_numeric(d[col_valor], errors="coerce").fillna(0) if col_valor else 0.0
    d["_cant"] = pd.to_numeric(d[col_cant], errors="coerce").fillna(0) if col_cant else 0.0
    return d.dropna(subset=["_fecha"])


# ─── Proporción dada de baja ────────────────────────────────────────────────
# CUÁNTOS PRODUCTOS ENTRAN AL UNIVERSO, y por qué es un TOP-N y no un piso en
# soles. Medido contra R2 el 2026-09-05, con «los 15 de mayor cociente» sobre
# distintos universos:
#
#                     piso fijo S/ 500        top-100 por movimiento
#   3 semanas         3 productos             14 candidatos, 2 sobre 100%
#   2026              199 productos           72 candidatos, 2 sobre 100%
#   histórico         492 productos           88 candidatos
#
# Un piso en soles no escala: el volumen crece con el largo del período, así
# que el mismo número que deja 492 productos en el histórico deja TRES en el
# rango de tres semanas con el que la página abre — y con S/ 1.000, cero. El
# top-N se acomoda solo. N=100 y no 50 (deja 4 candidatos en tres semanas) ni
# 200 (a esa altura entra ruido: un producto de S/ 20 con 346%).
_UNIVERSO_PROPORCION = 100
_TOPE_PROPORCION = 15


def _ranking_proporcion_baja(*, key_prefix, fam_sel=()):
    """QUÉ PROPORCIÓN de lo que entró a un área terminó dada de baja.

    Hermana de la Evolución y no su repetición: aquélla contesta CUÁNDO (una
    barra por período), ésta contesta DÓNDE DUELE (una barra por producto).
    Las dos leen el mismo par de parquets con el mismo filtro.

    POR QUÉ UN COCIENTE Y NO LA RESTA, que es lo que dibujaba hasta el
    2026-09-05. La resta ordenaba por `|requerido − baja|`, y como requerido
    es ~14 veces la baja, eso es ordenar por requerido: medido, el top-15 de
    esta vista y el de «Top productos · requerim.» daban **15 de 15 iguales**
    en los dos períodos probados. Dos secciones de la misma página dibujando
    la misma lista. Con el cociente el solapamiento es **0 de 15**. Ver
    arquitectura.md regla #323 — el corolario es que una resta entre dos
    magnitudes de órdenes distintos no compara: devuelve la magnitud grande.

    QUÉ QUEDA AFUERA, que hay que decirlo o la vista miente por omisión:
      · Los productos con requerido = 0 y baja > 0 — cociente sin definir.
        NO son ruido: son 22 productos y el 27% de toda la baja en tres
        semanas. Pero casi todos son `(Rs)`, producción propia (Zumo de
        limón, Tarta de queso, Creme brulee) que por naturaleza no se pide a
        Almacén Central, así que su cociente infinito es ESTRUCTURAL y no una
        anomalía: encabezarían el gráfico para siempre por la razón
        equivocada. Se cuentan en el caption en vez de dibujarse.
      · Los que quedan fuera del top-100 por movimiento, para que un producto
        de S/ 20 con 300% no le gane a uno de S/ 3.000 con 119%.
    """
    req, sal = _cargar_los_dos_lados()
    if req is None or sal is None:
        st.info(
            "No se pudo armar el ranking: falta requerimientos.parquet "
            "o salidas.parquet, o no traen las columnas esperadas."
        )
        return

    # El MISMO recorte que la Evolución, por la misma función: si los dos
    # lados de esta página se filtraran distinto, las dos vistas dirían
    # números que no se pueden comparar entre sí.
    _rango = _rango_vigente()
    if _rango:
        _ini, _fin = _rango
        req = req[(req["_fecha"] >= _ini) & (req["_fecha"] < _fin)]
        sal = sal[(sal["_fecha"] >= _ini) & (sal["_fecha"] < _fin)]
    if fam_sel:
        req = req[req["_fam"].isin(fam_sel)]
        sal = sal[sal["_fam"].isin(fam_sel)]

    if req.empty and sal.empty:
        st.info("No hay datos para el rango y los filtros seleccionados.")
        return

    g_req = req.groupby(["_cod", "_prod"])["_valor"].sum()
    g_sal = sal.groupby(["_cod", "_prod"])["_valor"].sum()
    idx = g_req.index.union(g_sal.index)
    t = pd.DataFrame({
        "requerido": g_req.reindex(idx, fill_value=0),
        "baja": g_sal.reindex(idx, fill_value=0),
    }).reset_index()
    # El "movimiento" de un producto es el mayor de sus dos lados, no su
    # suma: sumarlos haría que uno con 1.000 requerido y 0 de baja pesara lo
    # mismo que otro con 500 y 500, y el segundo es el que interesa acá.
    t["mov"] = t[["requerido", "baja"]].max(axis=1)

    _sin_req = t[(t["requerido"] <= 0) & (t["baja"] > 0)]
    universo = t.nlargest(_UNIVERSO_PROPORCION, "mov")
    sel = universo[(universo["requerido"] > 0) & (universo["baja"] > 0)].copy()
    if sel.empty:
        st.info("Ningún producto del período tiene requerimiento y baja a la vez.")
        return
    sel["ratio"] = sel["baja"] / sel["requerido"]
    top = sel.nlargest(_TOPE_PROPORCION, "ratio").sort_values("ratio")

    # ROJO = la baja superó a lo requerido. A diferencia de la versión de la
    # resta —donde el rojo no se encendía NUNCA porque los negativos eran un
    # orden de magnitud más chicos y jamás entraban al top—, acá el caso sí
    # aparece: 2 de 15 en tres semanas y 2 de 15 en 2026, medido.
    colores = [AJUSTE_NEG if r > 1 else ACENTO for r in top["ratio"]]
    fig = go.Figure(go.Bar(
        x=top["ratio"] * 100,
        y=[_compras_truncar(p, 34) for p in top["_prod"]],
        orientation="h", marker_color=colores,
        text=[f"{r * 100:,.0f}%" for r in top["ratio"]],
        textposition="outside", cliponaxis=False,
        customdata=top[["requerido", "baja"]].values,
        hovertemplate=("%{y}<br>Requerido: S/ %{customdata[0]:,.0f}"
                       "<br>Dado de baja: S/ %{customdata[1]:,.0f}"
                       "<br>Proporción: %{x:.0f}%<extra></extra>"),
    ))
    _compras_layout(fig, alto=alturas.por_filas(
        len(top), px_fila=30, minimo=320, extra=120))
    fig.update_layout(
        title="Qué proporción de lo requerido terminó dada de baja",
        xaxis_title=None, yaxis_title=None, showlegend=False,
    )
    # La línea del 100% es la lectura entera del gráfico: a la derecha se dio
    # de baja MÁS de lo que entró en el período. Va como `shape` y no como
    # una traza para que no aparezca en el hover ni pida leyenda.
    fig.add_vline(x=100, line_width=1, line_dash="dot",
                  line_color=GRIS_TEXTO_SUAVE)
    fig.update_xaxes(visible=False)
    st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_ranking")

    _pie = (
        f"De los {_UNIVERSO_PROPORCION} productos de mayor movimiento del "
        "período, los de mayor proporción de baja sobre lo requerido. "
        "La línea punteada es el 100%: a su derecha se dio de baja más de lo "
        "que entró. Agregado por producto — no hay una llave que una un "
        "Requerimiento puntual con la Salida que lo originó."
    )
    if len(_sin_req):
        _pie += (
            f" Aparte, {len(_sin_req):,} productos (S/ {_sin_req['baja'].sum():,.0f}) "
            "se dieron de baja sin haberse requerido en el período: no tienen "
            "proporción que calcular y casi todos son producción propia, que "
            "no se pide a Almacén Central."
        )
    st.caption(_pie)
