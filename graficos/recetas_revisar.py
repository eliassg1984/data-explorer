"""graficos.recetas_revisar — «Revisar recetas», en Recetas y Costos (regla #559).
Desde el 2026-10-22 el rail la llama «Recetas vs porcionado» y es una pieza
propia (regla #703): lo que muestra se arregla editando una receta O
registrando un porcionamiento. El id de la vista sigue siendo el de siempre.

LA PREGUNTA. ¿Qué receta está mal configurada? Una receta que pide un corte
que la cocina ya no hace, o que la cocina hace con otro código, no da error
en ningún lado: el POS descarga el corte que dice la receta, el stock de ese
corte se va a negativo, el del que de verdad se usó se acumula, y en el
conteo salen un sobrante y un faltante que se compensan. Medido el
2026-09-28: el 02/09 se crearon «(P) Lomo Medallon 170gr» y «(P) Lomo trozos
saltado 170gr» y cuatro minutos después se editó la receta del Lomo Saltado;
desde entonces Producción porcionó 179 medallones y 262 trozos, la venta
descargó 592,5 medallones y NINGÚN trozo, y el conteo del 17/09 en Cocina
dio +229 medallones y −83,5 trozos. A nivel de insumo de compra no se ve
—los dos salen del mismo lomo fino, y Movimientos › «Consumo según recetas»
cierra: 211 kg explicados contra 209 porcionados—; a nivel de corte, sí.

DOS SEÑALES, agrupadas por el insumo del que sale cada corte (el de la
raíz de la cadena: la charela de 125 g sale de la de 250 g, que sale de la
entera, y las dos gemelas quedan juntas):

  · «Ninguna receta lo usa»: un corte que se porcionó en el período y que no
    nombra ninguna receta de venta ni receta base ACTIVAS, ni un producto
    DIRECTO de la carta, ni una venta del período (así entran las
    propiedades, que no tienen parquet), ni otro porcionamiento que parta de
    él. Si se dejó de porcionar hace más de `DIAS_VIGENTE` días, se dice:
    suele ser el código viejo de un cambio de receta. Si salió entero por
    notas de salida (la «familia» es la comida del personal), tampoco es un
    tema de receta, y se dice.
  · «Las ventas piden más de lo que se porciona»: un corte que se porciona
    (tiene porcionamientos en su historia), sin receta base activa —si la
    tiene, se produce por orden de producción y no por porcionamiento—, cuyo
    PRIMER NIVEL del período (lo que nombran las recetas de lo vendido,
    `paloteoinsumosnivel1`) es más del doble de lo que se porcionó y se
    compró directo (la lechuga o el gin de la casa se porcionaron alguna vez
    y hoy se compran: eso no es un hueco).

Un par del mismo insumo —uno de cada señal— suele ser UNA receta que apunta
al corte equivocado: la de los platos de «Recetas que lo piden». Se arregla
en el POS editando esa receta; de paso se limpian los pares del Ajuste de
Inventario.

Los números: la cantidad va en la unidad de ENTRADA del corte (la del kardex,
la de los porcionamientos); el primer nivel viene en la de salida y se pasa
con el `FACTOR` del maestro (`inventariovalorizado.parquet`), como en
`consumo_recetas.py`. «Valor» es lo porcionado (al costo del porcionamiento)
para la primera señal y lo que faltó porcionar (al precio promedio de hoy)
para la segunda.

Se porciona por tandas: en 30 días un corte con stock puede pedir más de lo
que se porcionó sin que nada esté mal. Por eso la fecha del último
porcionamiento va en la tabla, y la ventana de 90 días está a un clic.

`revisar()` es pura (pandas, sin streamlit): la prueba
`test_graficos.py::_pruebas_revisar_recetas`.
"""

from graficos.movil import css_movil, js_movil
import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

import consumo_recetas
import data
import kardex
from graficos.recetas_comun import _activo

ARCHIVO_PORC = "porcionamientos.parquet"
ARCHIVO_MAESTRO = "inventariovalorizado.parquet"
ARCHIVO_CARTA = "cartacosteada.parquet"
ARCHIVO_SALIDAS = "salidas.parquet"
ARCHIVO_COMPRAS = "compras.parquet"
ARCHIVO_N1 = consumo_recetas.ARCHIVOS["paloteo"]

VENTANAS = {"Últimos 30 días": 30, "Últimos 90 días": 90}
"""La ventana abre en un mes corrido, como todos los selectores de fecha de
la app; 90 días es la ventana de rendimientos de «Consumo según recetas»."""

FALTA = 0.5
"""«Piden más de lo que se porciona»: lo porcionado no llega a la mitad de lo
que pide el primer nivel del período."""

DIAS_VIGENTE = 14
"""Un corte sin porcionamientos en los últimos 14 días del período «ya no se
porciona»: suele ser el código viejo de un cambio de receta."""

SALIDA_EXPLICA = 0.5
"""Si las notas de salida del período cubren al menos la mitad de lo
porcionado, el corte no va a recetas: sale por comida del personal o bajas."""

# Cortos a propósito: van en una ficha de la lista (regla #703).
QUE_SIN = "Ninguna receta lo usa"
QUE_SIN_VIEJO = "Sin receta · ya no se porciona"
QUE_FALTA = "Piden más de lo porcionado"
QUE_SALIDA = "Sale por notas de salida"
_ORDEN_QUE = {QUE_FALTA: 0, QUE_SIN: 0, QUE_SIN_VIEJO: 1, QUE_SALIDA: 2}

COLUMNAS = ("grupo_cod", "grupo", "cod", "corte", "unid", "que", "porcionado",
            "pedido", "ultimo", "valor", "salio", "platos")

def _txt(serie):
    return serie.astype(str).str.strip()


def revisar(porc, n1, recetas_venta, recetas_base, carta, maestro, salidas, ini, fin,
            compras=None):
    """Los cortes para revisar entre `ini` y `fin` (fechas, inclusive).

    Recibe los parquets tal como vienen (porcionamientos, recetaventa,
    recetabase, cartacosteada, inventariovalorizado y salidas) y `n1`, el
    primer nivel del período agregado por insumo y plato
    (`data.demanda_nivel1_rango`: columnas cod, plato, consumo, costo).
    `carta`, `salidas` y `compras` (compras.parquet) pueden venir en None.

    Devuelve un DataFrame con `COLUMNAS`, ordenado por grupo (el insumo del
    que sale el corte, de más a menos valor en juego) y adentro por señal y
    valor. `salio` es un dict {tipo de descargo: cantidad}; `platos`, los
    nombres de los platos que más lo piden."""
    ini, fin = pd.Timestamp(ini), pd.Timestamp(fin)

    # ── los porcionamientos, hasta el fin del período ─────────────────────
    p = porc.copy()
    p["_f"] = pd.to_datetime(p["FEC REGIST"], errors="coerce").dt.normalize()
    p = p[p["_f"].notna() & (p["_f"] <= fin)]
    p["COD PROD INIC"] = _txt(p["COD PROD INIC"])
    p["COD PROD FINAL"] = _txt(p["COD PROD FINAL"])
    p["_q"] = pd.to_numeric(p["CANT RESULT"], errors="coerce").fillna(0.0)
    p["_v"] = p["_q"] * pd.to_numeric(p["PREC PROM PROD FIN"], errors="coerce").fillna(0.0)
    w = p[p["_f"] >= ini]
    porc_w = w.groupby("COD PROD FINAL").agg(q=("_q", "sum"), v=("_v", "sum"))
    ultimo = p.groupby("COD PROD FINAL")["_f"].max()

    # ── el maestro: nombre, unidad de entrada, factor y precio ────────────
    m = maestro.assign(cod=_txt(maestro["CODIGO PRODUCTO"])).drop_duplicates("cod").set_index("cod")
    nombre = m["NOMBRE PRODUCTO"].astype(str).str.strip()
    unid = m["UNIDAD KARDEX"].astype(str).str.strip()
    factor = pd.to_numeric(m["FACTOR"], errors="coerce")
    precio = pd.to_numeric(m["PRECIO PROMEDIO"], errors="coerce").fillna(0.0)
    nombre_porc = (p.sort_values("_f").drop_duplicates("COD PROD FINAL", keep="last")
                   .set_index("COD PROD FINAL")["PROD FINAL RESULT"].astype(str).str.strip())
    nombre_inic = (p.sort_values("_f").drop_duplicates("COD PROD INIC", keep="last")
                   .set_index("COD PROD INIC")["PROD INICIAL"].astype(str).str.strip())

    # ── lo que piden las ventas del período, en unidad de ENTRADA ─────────
    d = n1.assign(cod=_txt(n1["cod"]), consumo=pd.to_numeric(n1["consumo"], errors="coerce").fillna(0.0))
    dem = d.groupby("cod")["consumo"].sum()
    fac = factor.reindex(dem.index)
    dem_e = (dem / fac.where(fac > 0)).dropna()

    # ── quién usa cada código ─────────────────────────────────────────────
    rv = recetas_venta
    usa = set(_txt(rv.loc[_activo(rv["ITEM VENTA ACTIVO"]) & _activo(rv["INS ACTIVO"]), "COD INS"]))
    rb = recetas_base
    rb_activa = _activo(rb["RB ACT"])
    usa |= set(_txt(rb.loc[rb_activa & _activo(rb["INS ACTIVO"]), "COD INS RB"]))
    con_receta_base = set(_txt(rb.loc[rb_activa, "COD PROD RB"]))
    if carta is not None and not carta.empty:
        directos = carta[(_txt(carta["TIPO DESC"]).str.upper() == "DIRECTO")
                         & _activo(carta["ITEM VENT ACT"])]
        usa |= set(_txt(directos["COD ITEM O RECETA"]))
    usa |= set(dem.index[dem > 0])
    usa |= set(w["COD PROD INIC"])

    # ── las notas de salida del período, por corte y tipo ─────────────────
    sal = {}
    if salidas is not None and not salidas.empty:
        s = salidas[_txt(salidas["NOMBRE ESTADO SALIDA"]).str.upper() == "PROCESADO"]
        fs = pd.to_datetime(s["FECHA REGISTRO"], errors="coerce").dt.normalize()
        s = s[(fs >= ini) & (fs <= fin)]
        g = (s.assign(cod=_txt(s["COD PRODUCTO"]),
                      q=pd.to_numeric(s["CANT SALIDA"], errors="coerce").fillna(0.0))
             .groupby(["cod", "TIPO DESCARGO"])["q"].sum())
        for (cod, tipo), q in g.items():
            if q > 0:
                sal.setdefault(cod, {})[str(tipo).strip()] = float(q)

    # ── lo comprado: en el período y alguna vez ───────────────────────────
    # Lo que se compra directo no es un hueco de porcionamiento: la lechuga,
    # el gin de la casa o un vino se porcionaron alguna vez y hoy se compran.
    # Las compras vienen en la unidad del kardex (medido: el 100 % de las
    # líneas de 12 meses), la misma de los porcionamientos.
    comprado, comprados = pd.Series(dtype=float), set()
    if compras is not None and not compras.empty:
        fc = pd.to_datetime(compras["FECHA_EMISION_DOC"], errors="coerce").dt.normalize()
        comprados = set(_txt(compras.loc[fc <= fin, "COD_PRODUCTO"]))
        c = compras[(fc >= ini) & (fc <= fin)]
        comprado = (pd.to_numeric(c["CANTIDAD_COMPRA"], errors="coerce").fillna(0.0)
                    .groupby(_txt(c["COD_PRODUCTO"])).sum())

    # ── de qué insumo sale cada corte ─────────────────────────────────────
    # El que más aportó en el período; si no se porcionó en el período, el
    # del último porcionamiento.
    origen = {}
    if not w.empty:
        o = (w.groupby(["COD PROD FINAL", "COD PROD INIC"])["_q"].sum().reset_index()
             .sort_values("_q", ascending=False).drop_duplicates("COD PROD FINAL"))
        origen.update(zip(o["COD PROD FINAL"], o["COD PROD INIC"]))
    h = p.sort_values("_f").drop_duplicates("COD PROD FINAL", keep="last")
    for cx, ce in zip(h["COD PROD FINAL"], h["COD PROD INIC"]):
        origen.setdefault(cx, ce)

    def raiz(cod):
        """El insumo del que sale la CADENA: la charela de 125 g sale de la de
        250 g, que sale de la charela entera. Sin esto, dos cortes gemelos de
        la misma charela caían en grupos distintos.

        Se para en el primer insumo que se COMPRA: hay porcionamientos entre
        dos insumos enteros (una charela «porcionada» desde una cachema) que
        llevarían la charela al grupo de la cachema. Y en un círculo —hay
        porcionamientos al revés, del corte al insumo (regla #558)— se queda
        en el último que no vuelve sobre sus pasos."""
        actual, vistos = origen.get(cod, ""), {cod}
        while actual in origen and actual not in comprados:
            vistos.add(actual)
            siguiente = origen[actual]
            if siguiente in vistos:
                break
            actual = siguiente
        return actual

    platos_de = (d[d["consumo"] > 0].groupby(["cod", "plato"])["consumo"].sum()
                 .reset_index().sort_values("consumo", ascending=False))
    platos_de = {c: list(x["plato"].astype(str))[:3] for c, x in platos_de.groupby("cod")}

    filas = []
    limite = fin - pd.Timedelta(days=DIAS_VIGENTE)
    for cod, r in porc_w.iterrows():
        if cod in usa or r["q"] <= 0:
            continue
        salio = sal.get(cod, {})
        if sum(salio.values()) >= SALIDA_EXPLICA * r["q"]:
            que = QUE_SALIDA
        elif ultimo.get(cod, fin) < limite:
            que = QUE_SIN_VIEJO
        else:
            que = QUE_SIN
        filas.append(dict(cod=cod, que=que, porcionado=float(r["q"]), pedido=0.0,
                          valor=float(r["v"]), salio=salio, platos=[]))

    porcionables = set(p["COD PROD FINAL"])
    for cod, pedido in dem_e.items():
        if cod not in porcionables or cod in con_receta_base or pedido <= 0:
            continue
        q = float(porc_w["q"].get(cod, 0.0))
        if q + float(comprado.get(cod, 0.0)) >= FALTA * pedido:
            continue
        filas.append(dict(cod=cod, que=QUE_FALTA, porcionado=q, pedido=float(pedido),
                          valor=float((pedido - q) * precio.get(cod, 0.0)),
                          salio=sal.get(cod, {}), platos=platos_de.get(cod, [])))

    if not filas:
        return pd.DataFrame(columns=list(COLUMNAS))
    t = pd.DataFrame(filas)
    t["corte"] = [nombre.get(c) or nombre_porc.get(c, c) for c in t["cod"]]
    t["unid"] = [unid.get(c, "") for c in t["cod"]]
    t["ultimo"] = [ultimo.get(c, pd.NaT) for c in t["cod"]]
    t["grupo_cod"] = [raiz(c) for c in t["cod"]]
    t["grupo"] = [nombre.get(g) or nombre_inic.get(g, g) for g in t["grupo_cod"]]
    # El grupo se ordena por lo que está en juego en sus dos señales
    # principales: lo que sale por notas de salida no es un tema de receta.
    enjuego = t["valor"].where(t["que"] != QUE_SALIDA, 0.0)
    t["_g"] = enjuego.groupby(t["grupo_cod"]).transform("sum")
    t["_o"] = t["que"].map(_ORDEN_QUE)
    t = t.sort_values(["_g", "grupo_cod", "_o", "valor"], ascending=[False, True, True, False])
    return t[list(COLUMNAS)].reset_index(drop=True)


# ─── La pieza (regla #703) ─────────────────────────────────────────────────
# Desde el 2026-10-22 la vista —el renglón del título, los indicadores que
# filtran, 30 | 90 días, la lista por insumo y la ficha del corte— es
# `recetas_revisar.js` + `.css` (`st.components.v2`), sobre el boceto
# aprobado (https://claude.ai/artifact/RLrWanQHM37CAcJBnysFxz). Se llama
# «Recetas vs porcionado» desde ese día (el id sigue siendo «Revisar
# recetas»). Python hace la cuenta (`revisar`, sin cambios) para las DOS
# ventanas de una vez y suma lo que la ficha necesita: el stock del kardex
# al empezar y al terminar, lo porcionado y lo pedido semana a semana, los
# platos que lo piden, los últimos porcionamientos y lo comprado. Vuelve a
# Python sólo `carta`: el salto a la ficha de un plato en Costo de Carta.

_PIEZA = st.components.v2.component(
    "recetas_revisar",
    css=css_movil((Path(__file__).parent / "recetas_revisar.css").read_text(encoding="utf-8")),
    js=js_movil((Path(__file__).parent / "recetas_revisar.js").read_text(encoding="utf-8")),
)
_K_PIEZA = "rec_rev_pieza"
SEMANAS = 13
"""Las semanas de la ficha: las 13 de lunes a domingo que terminan con el
período, la ventana de 90 días entera."""

CLASE_QUE = {QUE_SIN: "sin", QUE_FALTA: "falta", QUE_SIN_VIEJO: "viejo",
             QUE_SALIDA: "salida"}
"""Cómo llama la pieza a cada señal (su color y su indicador)."""


def semanas(fin, n=SEMANAS):
    """Los lunes de las `n` semanas que terminan con la de `fin`."""
    fin = pd.Timestamp(fin).normalize()
    lunes = fin - pd.Timedelta(days=fin.weekday())
    return [lunes - pd.Timedelta(weeks=k) for k in range(n - 1, -1, -1)]


def _factor(maestro):
    m = maestro.assign(cod=_txt(maestro["CODIGO PRODUCTO"])).drop_duplicates("cod")
    return pd.to_numeric(m.set_index("cod")["FACTOR"], errors="coerce")


def _en_entrada(consumo, cod, factor):
    """De la unidad de SALIDA (la del POS) a la de ENTRADA (la del kardex)."""
    f = factor.reindex(cod).to_numpy()
    return pd.Series(consumo.to_numpy() / f, index=consumo.index).where(f > 0, 0.0)


def detalle(cods, porc, maestro, n1, dem_sem, compras, ini, fin, sems):
    """Lo que la ficha muestra de cada corte de `cods`: lo porcionado y lo
    pedido por semana (`semP`, `semD`, una posición por lunes de `sems`), los
    platos que lo piden en el período ([plato, cantidad en unidad de entrada,
    platos vendidos]), los últimos seis porcionamientos ([fecha, desde qué,
    cantidad]) y lo comprado en el período. Pura: la lee el test.

    `n1` es el primer nivel del período (`data.demanda_nivel1_rango`) y
    `dem_sem` el de las semanas (`data.demanda_nivel1_semanas`), los dos en
    unidad de salida; se pasan con el `FACTOR` del maestro."""
    cods = set(cods)
    factor = _factor(maestro)
    j_de = {s: j for j, s in enumerate(sems)}
    out = {c: {"semP": [0.0] * len(sems), "semD": [0.0] * len(sems), "platos": [],
               "porcs": [], "comprado": 0.0} for c in cods}

    p = porc.assign(cod=_txt(porc["COD PROD FINAL"]),
                    f=pd.to_datetime(porc["FEC REGIST"], errors="coerce").dt.normalize(),
                    q=pd.to_numeric(porc["CANT RESULT"], errors="coerce").fillna(0.0))
    p = p[p["cod"].isin(cods) & p["f"].notna() & (p["f"] <= pd.Timestamp(fin))]
    sp = (p.assign(sem=p["f"] - pd.to_timedelta(p["f"].dt.weekday, unit="D"))
          .groupby(["cod", "sem"])["q"].sum())
    for (c, s), q in sp.items():
        if s in j_de:
            out[c]["semP"][j_de[s]] = round(float(q), 3)
    u = p.sort_values("f", ascending=False, kind="stable").groupby("cod").head(6)
    for c, f, desde, q in zip(u["cod"], u["f"], u["PROD INICIAL"], u["q"]):
        out[c]["porcs"].append([f.strftime("%Y-%m-%d"), str(desde).strip(), round(float(q), 3)])

    if dem_sem is not None and not dem_sem.empty:
        d = dem_sem.assign(cod=_txt(dem_sem["cod"]),
                           sem=pd.to_datetime(dem_sem["semana"]).dt.normalize())
        d = d[d["cod"].isin(cods)]
        d = d.assign(q=_en_entrada(pd.to_numeric(d["consumo"], errors="coerce").fillna(0.0),
                                   d["cod"], factor))
        for c, s, q in zip(d["cod"], d["sem"], d["q"]):
            if s in j_de:
                out[c]["semD"][j_de[s]] = round(out[c]["semD"][j_de[s]] + float(q), 3)

    if n1 is not None and not n1.empty:
        n = n1.assign(cod=_txt(n1["cod"]))
        n = n[n["cod"].isin(cods)]
        vendido = n["vendido"] if "vendido" in n.columns else 0.0
        g = (n.assign(consumo=pd.to_numeric(n["consumo"], errors="coerce").fillna(0.0),
                      vendido=pd.to_numeric(vendido, errors="coerce"))
             .fillna({"vendido": 0.0})
             .groupby(["cod", "plato"], as_index=False)[["consumo", "vendido"]].sum())
        g = g.assign(q=_en_entrada(g["consumo"], g["cod"], factor))
        g = g[g["q"] > 0].sort_values(["cod", "q"], ascending=[True, False], kind="stable")
        for c, plato, q, v in zip(g["cod"], g["plato"], g["q"], g["vendido"]):
            if len(out[c]["platos"]) < 6:
                out[c]["platos"].append([str(plato), round(float(q), 3), round(float(v), 1)])

    if compras is not None and not compras.empty:
        fc = pd.to_datetime(compras["FECHA_EMISION_DOC"], errors="coerce").dt.normalize()
        c = compras[(fc >= pd.Timestamp(ini)) & (fc <= pd.Timestamp(fin))]
        q = (pd.to_numeric(c["CANTIDAD_COMPRA"], errors="coerce").fillna(0.0)
             .groupby(_txt(c["COD_PRODUCTO"])).sum())
        for cod in cods & set(q.index):
            out[cod]["comprado"] = round(float(q[cod]), 3)
    return out


def stock_por_cod(foto):
    """{código: stock de todas las áreas} de una foto del kardex
    (`data.stock_al`), o None si no se pudo leer."""
    if foto is None:
        return None
    return (pd.to_numeric(foto["stock"], errors="coerce").fillna(0.0)
            .groupby(_txt(foto["cod"])).sum().round(3).to_dict())


def _iso(f):
    return None if f is None or pd.isna(f) else pd.Timestamp(f).strftime("%Y-%m-%d")


def armar_ventana(dias, t, ini, fin, det, st_ini, st_fin):
    """Una ventana de la pieza: sus fechas y una fila por corte de `revisar`,
    con lo de `detalle` y el stock al empezar (`stIni`) y al terminar
    (`stFin`): cero si el corte no tiene kardex, None si el kardex no se
    pudo leer. Pura: la lee el test."""
    filas = []
    for r in t.to_dict("records"):
        c = r["cod"]
        x = det.get(c, {})
        filas.append({
            "cod": c, "grupo_cod": str(r["grupo_cod"]), "grupo": str(r["grupo"]),
            "corte": str(r["corte"]), "unid": str(r["unid"]), "que": r["que"],
            "clase": CLASE_QUE.get(r["que"], "sin"),
            "porc": round(float(r["porcionado"]), 3), "ped": round(float(r["pedido"]), 3),
            "valor": round(float(r["valor"]), 2), "ultimo": _iso(r["ultimo"]),
            "salio": {k: round(float(v), 3) for k, v in (r["salio"] or {}).items()},
            "platos": x.get("platos", []), "porcs": x.get("porcs", []),
            "comprado": x.get("comprado", 0.0),
            "semP": x.get("semP", []), "semD": x.get("semD", []),
            "stIni": None if st_ini is None else st_ini.get(c, 0.0),
            "stFin": None if st_fin is None else st_fin.get(c, 0.0),
        })
    return {"dias": dias, "rot": next(k for k, v in VENTANAS.items() if v == dias),
            "ini": _iso(ini), "fin": _iso(fin), "filas": filas}


def _ir_a_carta(cod):
    """«Ver en Costo de Carta»: deja el plato elegido allá y pide el salto a
    su sección, con una corrida completa (la Carta es otro fragment)."""
    try:
        import navegacion
        from graficos.carta_costeada import _K_FOCO
        st.session_state[_K_FOCO] = cod
        navegacion._ir_a_vista("Recetas", "rec_graf_tipo", "Carta costeada")
        st.session_state["_rec_rev_ir_carta"] = 1
    except (ImportError, AttributeError):
        return


def _codigos_carta():
    """{plato en minúsculas: código} de la carta costeada (el mismo de
    «Análisis de platos»)."""
    try:
        from graficos.ventas_platos import _codigos_carta as _cc
        return _cc(data.sello_datos(ARCHIVO_CARTA))
    except Exception:
        return {}


def _sin_datos(texto):
    st.markdown('<p class="chart-card-hdr">Recetas vs porcionado</p>',
                unsafe_allow_html=True)
    st.info(texto)


def sellos_pendiente():
    """Los sellos de lo que lee esta vista: con ellos recuerda su resumen
    para los Pendientes del período (`data.recordar`, regla #711)."""
    return tuple((a, data.sello_datos(a)) for a in (
        ARCHIVO_PORC, ARCHIVO_N1, ARCHIVO_MAESTRO, ARCHIVO_CARTA,
        ARCHIVO_SALIDAS, "recetaventa.parquet", "recetabase.parquet"))


def resumen_pendiente(t, fin):
    """Lo que los Pendientes del período dicen de esta vista: los cortes de
    `t` (lo de `revisar` en 30 días) que las recetas no siguen —ninguna los
    usa, o piden más de lo porcionado— y lo que hay en juego. Pura."""
    m = t["que"].isin((QUE_SIN, QUE_FALTA)) if "que" in t.columns else pd.Series(False, index=t.index)
    return {"n": int(m.sum()),
            "valor": float(pd.to_numeric(t.loc[m, "valor"], errors="coerce").fillna(0).sum())
            if "valor" in t.columns else 0.0,
            "fin": pd.Timestamp(fin).date().isoformat()}


def render_revisar_recetas(df_rv, df_rb):
    """La tarjeta. `df_rv` es recetaventa.parquet (el `df_f` del reporte);
    `df_rb`, recetabase.parquet o None. El resto lo carga acá: la sección es
    perezosa y así sólo lo baja quien llega a la vista."""
    ss = st.session_state
    if ss.pop("_rec_rev_ir_carta", None):
        st.rerun(scope="app")
    with st.container(border=True, key="rec_card_revisar"):
        rango = data.rango_fechas(ARCHIVO_N1, "FECHA PEDIDO")
        porc = data.cargar(ARCHIVO_PORC)
        maestro = data.cargar(ARCHIVO_MAESTRO)
        if (rango is None or porc is None or porc.empty or maestro is None
                or maestro.empty or df_rb is None or df_rv is None):
            _sin_datos("Hacen falta los porcionamientos, el primer nivel de las ventas "
                       "(paloteoinsumosnivel1), el maestro de productos y las recetas "
                       "base: alguno no se pudo leer.")
            return
        fin = pd.Timestamp(rango[1]).date()
        carta = data.cargar(ARCHIVO_CARTA)
        salidas = data.cargar(ARCHIVO_SALIDAS)
        compras = data.cargar(ARCHIVO_COMPRAS)
        sems = semanas(fin)
        dem_sem = data.demanda_nivel1_semanas(sems[0].date(), fin)
        st_fin = stock_por_cod(data.stock_al(kardex.momento(fin, 23)))
        ventanas = []
        for dias in VENTANAS.values():
            ini = fin - dt.timedelta(days=dias - 1)
            n1 = data.demanda_nivel1_rango(ini, fin)
            if n1 is None:
                continue
            t = revisar(porc, n1, df_rv, df_rb, carta, maestro, salidas, ini, fin,
                        compras=compras)
            if dias == VENTANAS["Últimos 30 días"]:
                data.recordar("revisar_recetas", sellos_pendiente(),
                              resumen_pendiente(t, fin))
            det = detalle(t["cod"], porc, maestro, n1, dem_sem, compras, ini, fin, sems)
            # El stock AL EMPEZAR: la foto del día anterior, a las 23.
            st_ini = stock_por_cod(data.stock_al(
                kardex.momento(ini - dt.timedelta(days=1), 23)))
            ventanas.append(armar_ventana(dias, t, ini, fin, det, st_ini, st_fin))
        if not ventanas:
            _sin_datos("No se pudo leer lo que pidieron las ventas del período "
                       "(paloteoinsumosnivel1.parquet).")
            return

        def _a_la_carta():
            v = (ss.get(_K_PIEZA) or {}).get("carta")
            if v and v.get("cod"):
                _ir_a_carta(v["cod"])

        _PIEZA(key=_K_PIEZA, width="stretch", on_carta_change=_a_la_carta, data={
            "ventanas": ventanas, "sems": [s.strftime("%Y-%m-%d") for s in sems],
            "codigos": _codigos_carta(),
        })
