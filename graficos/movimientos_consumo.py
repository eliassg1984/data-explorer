"""graficos.movimientos_consumo — «Consumo según recetas», la octava sección
de Movimientos (regla #558).

La pregunta, a pedido (2026-09-28): «cuánto de crema de leche usé en una
semana», cuando la crema entra directo en unos platos y ESCONDIDA en recetas
base de otros, o «cuánto pulpo», cuando la receta pide un corte que sale de
un porcionamiento. La cuenta vive en `consumo_recetas.py` (puro, con su
test); acá sólo se la pide para el rango de la franja y se arma lo que lee
la página.

LA PÁGINA ES UN IFRAME CON TODO ADENTRO (`graficos/_consumo_html.py`),
aprobada sobre un mockup en tres vueltas: el resumen de arriba; la TABLA
DINÁMICA —insumo de compra › preparación que lo usa › plato, con las
columnas por semana, día, mes, día de la semana o turno, en cantidad o en
soles—; y el RESUMEN —la tabla de insumos por semana, día u hora y la ficha
del elegido, con el mapa día × hora y cómo se calculó cada porcionamiento—.
Desplegar, cambiar de columnas, buscar o apagar la venta interna pasa en el
navegador: con widgets cada clic sería una corrida entera.

LO QUE RECORTAN LOS CHIPS DE LA FRANJA: «Familia» sí —la del insumo de
compra, que es el mismo catálogo del Almacén—; «Sub Almacén» no: el consumo
según recetas no tiene área (la receta dice qué, no de qué almacén sale), y
filtrar por un dato que no está sería vaciar la sección en silencio. Se dice
en la tarjeta cuando el chip está puesto.

EL RANGO es el de la franja, como las otras secciones de Movimientos
(`_rango_vigente`), sobre la fecha del PEDIDO. Hasta 62 días va día por día;
más largo, por semana y por mes (`consumo_recetas.GRANO_DIA_MAX`).

CONTRA LO QUE SE COMPRÓ (2026-09-28, regla #560). Lo comprado del rango
—compras.parquet, por la fecha del documento— viaja con la página: la ficha
de cada insumo lo pone al lado de lo que explican las ventas, y la pestaña
«Contra compras» lista todo lo comprado, también lo que ninguna venta usó
(la idea que sólo tenía el «Panorama de compras» de Recetas, que se fue ese
día, regla #559). Se compara CANTIDAD: las compras vienen en la unidad del
kardex en el 100 % de las líneas de 12 meses, la misma del consumo. Sin chip
de familia entran las de alimentos y bebidas (`FAMILIAS_INSUMO`): carbón,
leña y limpieza no pasan por una receta.

LA RECETA DE HOY. El consumo usa las recetas de HOY, como el POS: un plato
cuya receta se editó dentro del rango se calcula con la nueva aunque se haya
vendido antes (el Lomo Saltado se editó el 02/09/2026 y cambió de corte). La
página marca esos platos con su fecha (`FECH MODIF` de recetaventa.parquet,
por NOMBRE: los nombres del POS no se repiten, medido).
"""

import datetime as dt

import pandas as pd
import streamlit as st

import consumo_recetas
import data
from graficos import alturas
from graficos._consumo_html import pagina
from graficos.movimientos_comun import _rango_vigente
from inyecciones._iframe import inyectar_html

CARD = "ajuste_graf_card_izq_mov_consumo"
"""La tarjeta. Es de la familia `ajuste_graf_card_` (su marco) y está fuera
del techo de alto en `estilos/_80_cards.py`: mide su contenido."""

VISTA = "mov_consumo_vista"
"""El contenedor del iframe: la excepción que lo hace VISIBLE (todo iframe
nace escondido, son los de las inyecciones) cuelga de esta key."""

_ULTIMA = {"directo": 0, "receta base": 1, "porcionamiento": 2}
_PESO = ("KILOS", "LITROS")

ARCHIVO_COMPRAS = "compras.parquet"
ARCHIVO_RECETAS = "recetaventa.parquet"

FAMILIAS_INSUMO = ("ALIMENTOS", "VINOS Y ESPUMANTES", "BEBIDAS CON ALCOHOL",
                   "BEBIDAS SIN ALCOHOL")
"""Las familias de compras.parquet que pasan por una receta: contra ellas se
compara lo comprado cuando la franja no elige familia. Venía del Panorama de
compras de Recetas (`_FAMILIAS_INGREDIENTE_COMPRAS`, validada el 2026-08-09);
carbón, leña, limpieza o envases se compran sin que ninguna receta los nombre."""


def compras_del_rango(compras, ini, fin, familias=()):
    """Lo comprado entre `ini` y `fin` (fecha del documento, inclusive), por
    producto: nombre, unidad, familia, subfamilia, cantidad, valor (S/, sin
    IGV: `VALOR_COMPRA` es de línea y en soles) y documentos. `familias`: las
    del chip de la franja; sin chip, `FAMILIAS_INSUMO`. `None` sin compras."""
    if compras is None or compras.empty:
        return None
    f = pd.to_datetime(compras["FECHA_EMISION_DOC"], errors="coerce").dt.normalize()
    d = compras[(f >= pd.Timestamp(ini)) & (f <= pd.Timestamp(fin))]
    fams = {str(x).strip().upper() for x in (familias or FAMILIAS_INSUMO)}
    d = d[d["FAMILIA"].astype(str).str.strip().str.upper().isin(fams)]
    if d.empty:
        return d.iloc[:0].assign(cod=[])
    d = d.assign(cod=d["COD_PRODUCTO"].astype(str).str.strip(),
                 cant=pd.to_numeric(d["CANTIDAD_COMPRA"], errors="coerce").fillna(0.0),
                 valor=pd.to_numeric(d["VALOR_COMPRA"], errors="coerce").fillna(0.0))
    return (d.groupby("cod")
             .agg(nombre=("NOMBRE_PRODUCTO", lambda s: str(s.iloc[0]).strip()),
                  unid=("UNIDAD_DE_INGRESO", "first"), familia=("FAMILIA", "first"),
                  subfamilia=("SUBFAMILIA", "first"), cant=("cant", "sum"),
                  valor=("valor", "sum"), docs=("NUM_DOCUMENTO", "nunique"))
             .reset_index())


def recetas_editadas(recetas, desde):
    """{nombre del plato: 'AAAA-MM-DD'} de las recetas de venta editadas el
    día `desde` o después. Por NOMBRE, que es como llega el plato del POS al
    primer nivel: en recetaventa.parquet no se repite ninguno (medido el
    2026-09-28: 0 nombres con dos códigos)."""
    if recetas is None or recetas.empty:
        return {}
    f = pd.to_datetime(recetas["FECH MODIF"], errors="coerce")
    ult = f.groupby(recetas["NOMB PLATO"].astype(str).str.strip()).max()
    ult = ult[ult.notna() & (ult.dt.normalize() >= pd.Timestamp(desde))]
    return {n: str(x.date()) for n, x in ult.items()}


def rango_de_la_vista():
    """`(ini, fin)` inclusive: el de la franja; sin él, los últimos 30 días
    hasta ayer (el parquet de la madrugada no trae hoy entero)."""
    rng = _rango_vigente()
    if rng:
        return rng[0].date(), (rng[1] - pd.Timedelta(days=1)).date()
    fin = dt.date.today() - dt.timedelta(days=1)
    return fin - dt.timedelta(days=29), fin


def _q(x):
    """Seis decimales: miligramos y mililitros, de sobra para lo que se
    muestra con dos, y el JSON de un mes pesa la mitad."""
    return round(float(x), 6)


def _pares(celda):
    return [[int(i), round(float(q), 6)] for i, q in (celda if celda is not None else [])]


def _texto(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)


def _num(v, defecto):
    return defecto if v is None or (isinstance(v, float) and pd.isna(v)) else float(v)


def datos_de_la_vista(r, familias=(), compras=None, editadas=None):
    """Lo que lee la página, desde lo que devuelve `consumo_recetas.calcular`.

    `familias`: las del chip de la franja (vacío = todas), sobre la familia
    del INSUMO DE COMPRA. `compras`: lo que devuelve `compras_del_rango` (o
    None); `editadas`: lo de `recetas_editadas` (o None).

    Todo sobre listas y dicts, no fila por fila en pandas: medido, un mes
    tardaba 2,5 s con `itertuples` y búsquedas por índice (las columnas de
    listas vienen de Arrow y cada acceso cuesta), y esto corre en cada
    pasada de la sección."""
    res = r["resumen"]
    mae = {m["cod"]: m for m in r["maestro"].drop_duplicates("cod").to_dict("records")}
    filas = r["filas"]
    if familias:
        fams = set(familias)
        filas = filas[[(mae.get(c) or {}).get("familia") in fams for c in filas["cod"].tolist()]]

    def _m(cod, campo, defecto=None):
        return (mae.get(cod) or {}).get(campo, defecto)

    platos = {p["plato"]: p for p in r["platos"].to_dict("records")}
    caminos = sorted(set(filas["camino"].tolist()))
    ci = {c: i for i, c in enumerate(caminos)}
    editadas = editadas or {}
    pid, lista_platos = {}, []
    for p in dict.fromkeys(filas["plato"].tolist()):
        pid[p] = len(lista_platos)
        x = platos.get(p) or {}
        lista_platos.append([p, bool(x.get("interna", False)), _q(_num(x.get("vendidos"), 0.0)),
                             editadas.get(str(p).strip(), "")])

    cods = list(dict.fromkeys(filas["cod"].tolist()))
    insumos = {c: [_texto(_m(c, "nombre", c)), _texto(_m(c, "unid", "")),
                   _q(_num(_m(c, "precio"), 0.0)), _texto(_m(c, "familia", "")),
                   _texto(_m(c, "subfamilia", "")), _q(_num(_m(c, "factor"), 1.0) or 1.0),
                   _texto(_m(c, "unid_salida", ""))]
               for c in cods}

    col = {k: filas[k].tolist() for k in ("cod", "padre", "plato", "n1", "camino", "ultima",
                                          "fino", "mes", "t0", "t1", *(f"d{i}" for i in range(7)))}
    porcionados = {p for p, u in zip(col["padre"], col["ultima"]) if u == "porcionamiento"}
    preps = {}
    for c in set(col["padre"]) | set(col["n1"]):
        if c:
            preps[c] = [_texto(_m(c, "nombre", c)),
                        "porcionado" if c in porcionados else "receta base",
                        _texto(_m(c, "unid", ""))]

    salida = [[col["cod"][i], col["padre"][i], pid[col["plato"][i]], col["n1"][i],
               ci[col["camino"][i]], _ULTIMA.get(col["ultima"][i], 0),
               _pares(col["fino"][i]), _pares(col["mes"][i]),
               [_q(col[f"d{k}"][i]) for k in range(7)], [_q(col["t0"][i]), _q(col["t1"][i])]]
              for i in range(len(col["cod"]))]

    # ── las horas: la madrugada va al final (es la cena de la noche anterior)
    hs = r["horas"]
    h_cod, h_int, h_dsem, h_hora, h_q = (hs[k].tolist() for k in ("cod", "interna", "dsem", "hora", "q"))
    en = set(insumos)
    horas = sorted({int(h) for c, h in zip(h_cod, h_hora) if c in en},
                   key=lambda h: (h - consumo_recetas.HORA_MADRUGADA) % 24)
    hj = {h: j for j, h in enumerate(horas)}
    horas_ins, mapa_ins = {}, {}
    for cod, interna, dsem, hora, q in zip(h_cod, h_int, h_dsem, h_hora, h_q):
        if cod not in en:
            continue
        k, j = (1 if interna else 0), hj[int(hora)]
        h_ = horas_ins.setdefault(cod, [[0.0] * len(horas), [0.0] * len(horas)])
        h_[k][j] = round(h_[k][j] + float(q), 6)
        mapa_ins.setdefault(cod, [[], []])[k].append([int(dsem), j, _q(q)])

    # ── los rendimientos del ÚLTIMO mes del rango, los que el árbol usa
    rd = r["rend"]
    rend, revisar = {}, []
    if not rd.empty:
        rd = rd[(rd["mes"] == rd["mes"].max()) & rd["usado"]]
        usados = {(c, p) for c, p, u in zip(col["cod"], col["padre"], col["ultima"])
                  if u == "porcionamiento"}
        suma, misma = {}, {}
        for x in rd.to_dict("records"):
            cx, ce = x["cod_x"], x["cod_e"]
            if (ce, cx) in usados:
                rend.setdefault(ce, {})[cx] = [
                    _q(x["rend"]), x["fuente"], int(x["n_porc"]),
                    str(pd.Timestamp(x["desde"]).date()), str(pd.Timestamp(x["hasta"]).date())]
            # «pesa más de lo que se le asignó»: por CORTE, sumando sus
            # orígenes, si todos van en la misma unidad de peso que el corte
            suma[cx] = suma.get(cx, 0.0) + float(x["rend"])
            misma[cx] = misma.get(cx, True) and _m(ce, "unid") == _m(cx, "unid")
        revisar = [cx for cx in suma
                   if cx in porcionados and misma[cx] and _m(cx, "unid") in _PESO and suma[cx] < 0.95]

    po = r["porcionado"]
    porcionado = {c: _q(q) for c, q in zip(po["cod"], po["cant"]) if c in insumos}

    # ── lo comprado: el de los insumos de la página, y aparte (con su nombre)
    # lo que ninguna venta del rango usó
    compras_d, comprados = {}, {}
    if compras is not None and not compras.empty:
        for x in compras.to_dict("records"):
            c = x["cod"]
            compras_d[c] = [_q(x["cant"]), _q(x["valor"]), int(x["docs"])]
            if c not in insumos:
                comprados[c] = [_texto(x["nombre"]), _texto(x["unid"]),
                                _texto(x["familia"]), _texto(x["subfamilia"])]
    fams_compras = sorted({str(f).strip().upper() for f in (familias or FAMILIAS_INSUMO)})

    vi = [p for p in lista_platos if p[1]]
    return dict(
        periodo=dict(desde=str(res["ini"]), hasta=str(res["fin"]), grano=res["grano"],
                     finas=[str(x) for x in res["finas"]], meses=[str(x) for x in res["meses"]],
                     n_dia=res["n_dia"], n_dias=(res["fin"] - res["ini"]).days + 1),
        horas=[int(h) for h in horas], caminos=caminos, platos=lista_platos,
        insumos=insumos, preps=preps, filas=salida, horas_ins=horas_ins, mapa_ins=mapa_ins,
        rend=rend, revisar=revisar, porcionado=porcionado,
        compras=compras_d, comprados=comprados,
        compras_familias=fams_compras if compras is not None else [],
        venta_interna=dict(pedidos=len(vi), platos=len(vi), nombres=[p[0] for p in vi][:4]),
        resumen=dict(costo=_q(res["costo"]), costo_nivel1=_q(res["costo_nivel1"]),
                     niveles=int(res["niveles"]), sin_maestro=int(res["sin_maestro"]),
                     sin_factor=int(res["sin_factor"]),
                     costo_sin_convertir=_q(res["costo_sin_convertir"]),
                     hora_de_mesa=bool(res.get("hora_de_mesa", False))),
    )


def tarjeta_consumo(fam_sel=(), sub_sel=()):
    """La sección entera: la tarjeta con la página adentro.

    `fam_sel` y `sub_sel` son los chips de la franja: la familia recorta los
    insumos de compra; el sub almacén no aplica y se dice."""
    ini, fin = rango_de_la_vista()
    with st.container(border=True, key=CARD):
        st.markdown('<p class="chart-card-hdr">Consumo según recetas · lo que usaron las ventas '
                    'en insumos de compra, bajando por recetas base y porcionamientos</p>',
                    unsafe_allow_html=True)
        r = data.consumo_recetas_rango(ini, fin)
        if r is None:
            st.info("No se pudo calcular el consumo. Hacen falta cuatro parquets: el primer "
                    "nivel de las recetas de venta (paloteoinsumosnivel1), las recetas base, "
                    "los porcionamientos y el inventario valorizado.")
            return
        if r["filas"].empty:
            st.info("Sin ventas con receta en el rango de fechas. Ampliá el rango en la "
                    "franja de arriba.")
            return
        # Lo comprado del rango (regla #560) y las recetas editadas desde su
        # primer día: dos parquets chicos que la app ya tiene cacheados.
        compras = compras_del_rango(data.cargar(ARCHIVO_COMPRAS), ini, fin, fam_sel)
        editadas = recetas_editadas(data.cargar(ARCHIVO_RECETAS), ini)
        datos = datos_de_la_vista(r, fam_sel, compras=compras, editadas=editadas)
        if not datos["filas"]:
            st.info("Ningún insumo de compra de la familia elegida en el rango.")
            return
        if sub_sel:
            st.caption("El chip «Sub Almacén» no recorta esta sección: la receta dice qué "
                       "insumo se usa, no de qué almacén sale.")
        with st.container(key=VISTA):
            inyectar_html(pagina(datos), height=alturas.CONSUMO_VISTA)
