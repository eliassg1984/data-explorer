"""graficos.recetas_revisar — «Revisar recetas», en Recetas y Costos (regla #559).

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

import datetime as dt

import pandas as pd
import streamlit as st

import consumo_recetas
import data
import tema
from graficos import alturas
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

# Cortos a propósito: la columna mide 185 px y un rótulo más largo se corta
# (medido a 1366×768: las nueve columnas entran si nadie pasa de su ancho).
QUE_SIN = "Ninguna receta lo usa"
QUE_SIN_VIEJO = "Sin receta · ya no se porciona"
QUE_FALTA = "Piden más de lo porcionado"
QUE_SALIDA = "Sale por notas de salida"
_ORDEN_QUE = {QUE_FALTA: 0, QUE_SIN: 0, QUE_SIN_VIEJO: 1, QUE_SALIDA: 2}

COLUMNAS = ("grupo_cod", "grupo", "cod", "corte", "unid", "que", "porcionado",
            "pedido", "ultimo", "valor", "salio", "platos")

_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
_CORTA = {"KILOS": "kg", "LITROS": "L", "UND": "und", "UNIDAD": "und", "PORCION": "porc"}


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


# ─── Lo que se muestra ─────────────────────────────────────────────────────

def _corta(u):
    return _CORTA.get(str(u).upper(), str(u).lower())


def _cant(q, u):
    if not q:
        return "—"
    d = 0 if abs(q) >= 100 or abs(q - round(q)) < 1e-9 else (1 if abs(q) >= 10 else 2)
    return f"{q:,.{d}f} {_corta(u)}"


def _fecha(f, fin):
    if f is None or pd.isna(f):
        return "—"
    f = pd.Timestamp(f)
    base = f"{f.day} {_MESES[f.month - 1]}"
    return base if f.year == pd.Timestamp(fin).year else f"{base} {f.year}"


def resumen(t, ini, fin):
    """La línea de arriba de la tabla: cuántos cortes y cuánto en cada señal."""
    periodo = f"Del {_fecha(ini, fin)} al {_fecha(fin, fin)} de {pd.Timestamp(fin).year}"
    if t.empty:
        return f"{periodo}: nada para revisar."
    sin = t[t["que"] == QUE_SIN]
    viejo = t[t["que"] == QUE_SIN_VIEJO]
    falta = t[t["que"] == QUE_FALTA]
    salida = t[t["que"] == QUE_SALIDA]

    def n_cortes(x):
        return f"**{len(x)}** corte{'s' if len(x) != 1 else ''}"

    partes = []
    if len(sin):
        partes.append(f"{n_cortes(sin)} se porciona{'n' if len(sin) != 1 else ''} y ninguna "
                      f"receta {'los' if len(sin) != 1 else 'lo'} usa "
                      f"(**S/ {sin['valor'].sum():,.0f}** porcionados)")
    if len(falta):
        partes.append(f"{n_cortes(falta)} {'los' if len(falta) != 1 else 'lo'} piden las "
                      f"recetas y casi no se porciona{'n' if len(falta) != 1 else ''} "
                      f"(faltaron **S/ {falta['valor'].sum():,.0f}**)")
    texto = f"{periodo}: " + "; ".join(partes) + "." if partes else f"{periodo}."
    if len(viejo):
        texto += (f" Otros {len(viejo)} se dejaron de porcionar y ninguna receta de hoy los "
                  "usa: suelen ser el código viejo de un cambio de receta."
                  if len(viejo) != 1 else
                  " Otro se dejó de porcionar y ninguna receta de hoy lo usa: suele ser el "
                  "código viejo de un cambio de receta.")
    if len(salida):
        texto += (f" {len(salida)} más salen por notas de salida (comida del personal, "
                  "bajas): no son un tema de receta." if len(salida) != 1 else
                  " Uno más sale por notas de salida (comida del personal, bajas): no es un "
                  "tema de receta.")
    return texto


def tabla(t, fin):
    """Lo que dibuja `st.dataframe`: texto listo para leer, y el valor en número."""
    return pd.DataFrame({
        "Sale de": t["grupo"],
        "Corte": t["corte"],
        "Qué pasa": t["que"],
        "Porcionado": [_cant(q, u) for q, u in zip(t["porcionado"], t["unid"])],
        "Piden las ventas": [_cant(q, u) for q, u in zip(t["pedido"], t["unid"])],
        "Valor": t["valor"].astype(float),
        "Último porc.": [_fecha(f, fin) for f in t["ultimo"]],
        "Recetas que lo piden": [" · ".join(x) if x else "—" for x in t["platos"]],
        "Salió por": ["; ".join(f"{k} {_cant(v, u)}" for k, v in s.items()) if s else "—"
                      for s, u in zip(t["salio"], t["unid"])],
    })


# Los anchos, medidos a 1366×768 con la columna del rail plegada: la tabla
# tiene 1.196 px por dentro y las nueve columnas suman eso. Sin anchos, cada
# columna medía su texto más largo y sumaban 1.585: las cifras quedaban
# escondidas a la derecha, detrás de una barra.
COLUMNAS_TABLA = {
    "Sale de": st.column_config.TextColumn(
        width=175, help="El insumo que se compra y del que sale el corte: la raíz "
                        "de su cadena de porcionamientos"),
    "Corte": st.column_config.TextColumn(width=230),
    "Qué pasa": st.column_config.TextColumn(
        width=185, help="«Ninguna receta lo usa»: se porcionó y ninguna receta activa "
                        "lo nombra. «Piden más de lo porcionado»: las recetas de lo "
                        "vendido piden más del doble de lo que se porcionó y se compró. "
                        "«Sin receta · ya no se porciona»: suele ser el código viejo de "
                        "un cambio de receta. «Sale por notas de salida»: comida del "
                        "personal o bajas, no un tema de receta."),
    "Porcionado": st.column_config.TextColumn(
        width=88, help="Lo porcionado en el período, en la unidad del kardex"),
    "Piden las ventas": st.column_config.TextColumn(
        width=98, help="Lo que nombran las recetas de lo vendido en el período (el "
                       "primer nivel del POS), en la unidad del kardex"),
    "Valor": st.column_config.Column(
        width=78, help="Lo porcionado, al costo del porcionamiento; o lo que faltó "
                       "porcionar, al precio promedio de hoy"),
    "Último porc.": st.column_config.TextColumn(
        width=82, help="El último porcionamiento del corte"),
    "Recetas que lo piden": st.column_config.TextColumn(
        width=170, help="Los platos que más lo piden: su receta es la que hay que mirar"),
    "Salió por": st.column_config.TextColumn(
        width=90, help="Las notas de salida del período: comida del personal, bajas…"),
}


def _color_que(v):
    if v in (QUE_SIN, QUE_FALTA):
        return f"color: {tema.ADVERTENCIA_TEXTO}; font-weight: 600"
    return f"color: {tema.GRIS_TEXTO}"


def render_revisar_recetas(df_rv, df_rb):
    """La tarjeta. `df_rv` es recetaventa.parquet (el `df_f` del reporte);
    `df_rb`, recetabase.parquet o None. El resto lo carga acá: la sección es
    perezosa y así sólo lo baja quien llega a la vista."""
    ss = st.session_state
    with st.container(border=True, key="rec_card_revisar"):
        st.markdown('<p class="chart-card-hdr">Revisar recetas · cortes que se porcionan y '
                    'ninguna receta usa, y los que las recetas piden y casi no se '
                    'porcionan</p>', unsafe_allow_html=True)
        opciones = list(VENTANAS)
        if ss.get("rec_rev_ventana") not in opciones:
            ss["rec_rev_ventana"] = opciones[0]
        ventana = st.segmented_control("Período", opciones, key="rec_rev_ventana",
                                       label_visibility="collapsed") or opciones[0]

        rango = data.rango_fechas(ARCHIVO_N1, "FECHA PEDIDO")
        porc = data.cargar(ARCHIVO_PORC)
        maestro = data.cargar(ARCHIVO_MAESTRO)
        if (rango is None or porc is None or porc.empty or maestro is None
                or maestro.empty or df_rb is None or df_rv is None):
            st.info("Hacen falta los porcionamientos, el primer nivel de las ventas "
                    "(paloteoinsumosnivel1), el maestro de productos y las recetas "
                    "base: alguno no se pudo leer.")
            return
        fin = pd.Timestamp(rango[1]).date()
        ini = fin - dt.timedelta(days=VENTANAS[ventana] - 1)
        n1 = data.demanda_nivel1_rango(ini, fin)
        if n1 is None:
            st.info("No se pudo leer lo que pidieron las ventas del período "
                    "(paloteoinsumosnivel1.parquet).")
            return
        t = revisar(porc, n1, df_rv, df_rb, data.cargar(ARCHIVO_CARTA), maestro,
                    data.cargar(ARCHIVO_SALIDAS), ini, fin,
                    compras=data.cargar(ARCHIVO_COMPRAS))
        st.markdown(resumen(t, ini, fin))
        if t.empty:
            return
        v = tabla(t, fin)
        sty = (v.style.format({"Valor": lambda x: f"S/ {x:,.0f}"})
               .map(_color_que, subset=["Qué pasa"]))
        st.dataframe(sty, hide_index=True, row_height=27, column_config=COLUMNAS_TABLA,
                     height=alturas.por_filas(len(v), px_fila=27, extra=38, minimo=0,
                                              rol=alturas.REVISAR_RECETAS))
        st.caption(
            "Agrupada por el insumo del que sale cada corte. Un par del mismo insumo —uno "
            "que se porciona y ninguna receta usa, otro que las recetas piden y no se "
            "porciona— suele ser UNA receta que apunta al corte equivocado: la de «Recetas "
            "que lo piden». Se arregla en el POS editando esa receta. «Ninguna receta lo "
            "usa»: ni una receta de venta o receta base activas, ni un producto directo de "
            "la carta, ni una venta del período, ni otro porcionamiento que parta de él. "
            "«Valor»: lo porcionado, o lo que faltó porcionar al precio de hoy. Se porciona "
            "por tandas: un corte con stock puede pedir más de lo que se porcionó en el "
            "período sin que nada esté mal; mirá la fecha del último porcionamiento.")
