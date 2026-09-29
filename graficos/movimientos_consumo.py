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


def datos_de_la_vista(r, familias=()):
    """Lo que lee la página, desde lo que devuelve `consumo_recetas.calcular`.

    `familias`: las del chip de la franja (vacío = todas), sobre la familia
    del INSUMO DE COMPRA.

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
    pid, lista_platos = {}, []
    for p in dict.fromkeys(filas["plato"].tolist()):
        pid[p] = len(lista_platos)
        x = platos.get(p) or {}
        lista_platos.append([p, bool(x.get("interna", False)), _q(_num(x.get("vendidos"), 0.0))])

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

    vi = [p for p in lista_platos if p[1]]
    return dict(
        periodo=dict(desde=str(res["ini"]), hasta=str(res["fin"]), grano=res["grano"],
                     finas=[str(x) for x in res["finas"]], meses=[str(x) for x in res["meses"]],
                     n_dia=res["n_dia"], n_dias=(res["fin"] - res["ini"]).days + 1),
        horas=[int(h) for h in horas], caminos=caminos, platos=lista_platos,
        insumos=insumos, preps=preps, filas=salida, horas_ins=horas_ins, mapa_ins=mapa_ins,
        rend=rend, revisar=revisar, porcionado=porcionado,
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
        datos = datos_de_la_vista(r, fam_sel)
        if not datos["filas"]:
            st.info("Ningún insumo de compra de la familia elegida en el rango.")
            return
        if sub_sel:
            st.caption("El chip «Sub Almacén» no recorta esta sección: la receta dice qué "
                       "insumo se usa, no de qué almacén sale.")
        with st.container(key=VISTA):
            inyectar_html(pagina(datos), height=alturas.CONSUMO_VISTA)
