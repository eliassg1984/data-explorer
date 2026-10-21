"""
consistencia_maestro — ¿el maestro del sistema tiene lógica?

Controles sobre la data maestra del POS y del Almacén, y sobre los
movimientos raros que ya marcan otros reportes de la app, para una vista de
Costos (boceto: https://claude.ai/artifact/JDqYExY3U12yEfTrnewdhJ). Cada
control es una PREGUNTA que el maestro debería poder contestar sin
contradecirse —«¿hay stock que no se mueve?», «¿hay platos activos que no se
venden?»— y devuelve sus CASOS, uno por fila, con las columnas de `CASOS`.

En la etapa del boceto (2026-10-21) esto sólo calcula: los números los
imprime `herramientas/consistencia_maestro.py`, para decidir con ellos qué
controles quedan, con qué umbral y con qué color, antes de dibujar la vista.

Puro: recibe los parquets ya cargados en un dict (`t`, ver `ENTRADAS`) y la
fecha de corte (`hoy`). Lo único que no es de este módulo son dos reglas que
ya existen y se reusan tal cual: el precio habitual y la marca «revisar» de
Compras (regla #653), importadas adentro de su control.

Tocar QUÉ cuenta un control es subir `VERSION`.
"""

import unicodedata
from collections import namedtuple

import numpy as np
import pandas as pd

VERSION = 1

VENTANA = 90
"""Días hacia atrás para «hace poco»: ventas, compras, stock parado."""
VENTANA_LARGA = 180
"""Días para «no se usa»: lo que se mueve una vez por temporada no cae."""
UN_ANO = 365

CASOS = ("codigo", "nombre", "area", "dato", "soles", "fecha", "quien")
"""Las columnas de lo que devuelve cada control. `dato` es el texto corto de
la ficha («212 d», «1000 → 1»); `soles`, lo que está en juego (NaN si el
control no tiene monto); `quien`, el usuario cuando la fuente lo trae."""

ENTRADAS = {
    "inv": "inventariovalorizado.parquet, con `_activo` (data.INVENTARIO_ACTIVO)",
    "kdx": "kardex.parquet",
    "rv": "recetaventa.parquet",
    "rb": "recetabase.parquet",
    "cc": "cartacosteada.parquet",
    "aud": "auditoriacostos.parquet",
    "ven": "ventas.parquet de los últimos VENTANA días, preparado y un ítem una vez",
    "cmp": "compras.parquet con las notas de crédito restadas",
    "porc": "porcionamientos.parquet",
    "sal": "salidas.parquet",
    "ped": "pedidos.parquet",
    "dsc": "descargosventas.parquet",
    "ajs": "ajusteinventario.parquet",
    "sunat": "el cruce de «Documentos SUNAT» (documento, estado, fecha_emision, total, proveedor)",
}

TIPOS_SIN_USO = ("93", "SI")
"""Lo que en el kardex no es USAR el producto: el ajuste de un conteo y el
saldo inicial. Un producto con stock que sólo se cuenta cada mes sigue
parado."""
TIPOS_USO = ("94", "95", "96", "98")
"""Salidas que consumen el producto: producción, descargo de ventas,
porcionamiento y notas de salida. Un requerimiento o una transferencia sólo
lo cambian de área."""

PCT_COSTO_ALTO = 60.0
"""% de costo de carta por encima del cual un plato activo se mira."""
VECES_RARO = 2.5
"""Un precio de costo editado a mano a esto o a su inversa de lo que era."""
VECES_HABITUAL = 3.0
"""Un día de anulaciones o cortesías a esto de la mediana diaria del usuario."""
MINIMO_DIA = 200.0
LOTE_NOTAS = 15
"""Notas de salida de un área registradas sin una pausa de `PAUSA_LOTE`
minutos: un lote."""
PAUSA_LOTE = 10
DIAS_SUNAT = 15
FAMILIA_OPERACION = "COSTOS PRODUCCION"
"""Los insumos de operación (leña, papel, limpieza): ninguna receta los
descarga y su consumo sólo aparece al contar (regla #645)."""
"""Días que se le dan a una factura antes de llamarla «no ingresada»."""


# --- utilidades -------------------------------------------------------------

def _txt(s):
    return s.fillna("").astype(str).str.strip()


def _up(s):
    return _txt(s).str.upper()


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _fecha(s):
    return pd.to_datetime(s, errors="coerce")


def _vacio():
    return pd.DataFrame({c: pd.Series(dtype=float if c == "soles" else object)
                         for c in CASOS})


def _casos(d, **cols):
    """Un DataFrame de CASOS armado POR NOMBRE (regla #481) desde `d`."""
    if d is None or len(d) == 0:
        return _vacio()
    out = pd.DataFrame(index=d.index)
    for c in CASOS:
        v = cols.get(c)
        if v is None:
            out[c] = np.nan if c == "soles" else ""
        elif isinstance(v, str) and v in d.columns:
            out[c] = d[v]
        else:
            out[c] = v
    out["soles"] = _num(out["soles"])
    return out.reset_index(drop=True)


def _nombres(t):
    """`(producto → nombre, área → nombre)` desde el maestro de stock."""
    inv = t["inv"]
    prod = (inv.drop_duplicates("CODIGO PRODUCTO")
               .set_index("CODIGO PRODUCTO")["NOMBRE PRODUCTO"])
    area = (inv.drop_duplicates("CODIGO AREA")
               .set_index("CODIGO AREA")["NOMBRE AREA"])
    return prod, area


def _kardex(t):
    """El kardex con `dia` y el tipo como texto, una vez por llamada."""
    k = t["kdx"]
    if "_dia" not in k.columns:
        k = k.assign(_dia=_fecha(k["FECHA HORA"]).dt.normalize(),
                     _tipo=_txt(k["COD TIPO"]))
        t["kdx"] = k
    return k


def _movidos(t, desde, tipos=None, sin=TIPOS_SIN_USO):
    """El kardex desde `desde`, sólo con los tipos `tipos` (o sin los `sin`)."""
    k = _kardex(t)
    k = k[k["_dia"] >= desde]
    if tipos is not None:
        return k[k["_tipo"].isin(tipos)]
    return k[~k["_tipo"].isin(sin)]


def _ultimo_mov(t, por):
    """La fecha del último movimiento de USO o de entrada (sin conteos) por
    `por` (columnas del kardex)."""
    k = _kardex(t)
    k = k[~k["_tipo"].isin(TIPOS_SIN_USO)]
    return k.groupby(por)["_dia"].max()


def _dias(hoy, f):
    d = (hoy - f).dt.days
    return d.map(lambda x: "nunca" if pd.isna(x) else f"{int(x)} d")


def _cant(v, u):
    return [f"{x:,.1f} {str(un).lower()}".replace(".0 ", " ") for x, un in zip(v, u)]


def _venta_por_plato(t):
    """Unidades y venta neta de cada plato en `ven`, con la definición de
    venta de `definicion_venta` (sin cortesías ni anulados)."""
    import definicion_venta
    v = t["ven"]
    if v is None or v.empty:
        return pd.DataFrame(columns=["unid", "venta", "costo"])
    v = definicion_venta.solo_venta(v)
    g = v.assign(_cod=_txt(v["COD ITEM VENTA DDOCUMENTO"]),
                 _u=_num(v["CANTIDAD ITEM DDOCUMENTO"]),
                 _v=_num(v["NETO TOTAL ITEM DDOCUMENTO"]),
                 _c=_num(v["PRECIO COSTO"]) * _num(v["CANTIDAD ITEM DDOCUMENTO"]))
    return g.groupby("_cod").agg(unid=("_u", "sum"), venta=("_v", "sum"),
                                 costo=("_c", "sum"))


def _activa(s, *ok):
    return _up(s).isin(ok)


# --- STOCK ------------------------------------------------------------------

def stock_parado(t, hoy):
    """Con existencia hoy y sin un movimiento de uso o de entrada en
    `VENTANA` días, por producto × área."""
    inv = t["inv"]
    d = inv[inv["_activo"] & (_num(inv["STOCK AL DIA"]) > 0)]
    ult = _ultimo_mov(t, ["CODIGO AREA", "CODIGO PRODUCTO"])
    f = pd.Series(list(zip(d["CODIGO AREA"], d["CODIGO PRODUCTO"])),
                  index=d.index).map(ult)
    f = _fecha(f)
    d = d.assign(_f=f)[f.isna() | (f < hoy - pd.Timedelta(days=VENTANA))]
    d = d.assign(_dato=_dias(hoy, d["_f"]))
    return _casos(d, codigo="CODIGO PRODUCTO", nombre="NOMBRE PRODUCTO",
                  area="NOMBRE AREA", dato="_dato", soles="VALORIZADO TOTAL",
                  fecha="_f")


def stock_negativo(t, hoy):
    """El sistema dice que hay menos de cero."""
    inv = t["inv"]
    d = inv[inv["_activo"] & (_num(inv["STOCK AL DIA"]) < 0)]
    d = d.assign(_dato=_cant(_num(d["STOCK AL DIA"]), d["UNIDAD KARDEX"]))
    return _casos(d, codigo="CODIGO PRODUCTO", nombre="NOMBRE PRODUCTO",
                  area="NOMBRE AREA", dato="_dato", soles="VALORIZADO TOTAL")


def stock_sin_precio(t, hoy):
    """Con existencia y precio promedio cero: todo lo que lo lleve cuesta 0."""
    inv = t["inv"]
    d = inv[inv["_activo"] & (_num(inv["STOCK AL DIA"]) > 0)
            & ~(_num(inv["PRECIO PROMEDIO"]) > 0)]
    d = d.assign(_dato=_cant(_num(d["STOCK AL DIA"]), d["UNIDAD KARDEX"]))
    return _casos(d, codigo="CODIGO PRODUCTO", nombre="NOMBRE PRODUCTO",
                  area="NOMBRE AREA", dato="_dato")


def activo_sin_vida(t, hoy):
    """Producto activo de mercadería sin stock en ninguna área, sin un
    movimiento de uso o de entrada y sin una compra en `UN_ANO` días."""
    inv = t["inv"]
    m = inv[_activa(inv["PRODUCTO ACTIVO"], "ACTIVO")
            & _activa(inv["TIPO PRODUCTO"], "MERCADERIA")]
    con_stock = set(m.loc[_num(m["STOCK AL DIA"]).fillna(0) != 0, "CODIGO PRODUCTO"])
    desde = hoy - pd.Timedelta(days=UN_ANO)
    movidos = set(_movidos(t, desde)["CODIGO PRODUCTO"])
    c = t["cmp"]
    comprados = set(c.loc[_fecha(c["FECHA_EMISION_DOC"]) >= desde, "COD_PRODUCTO"])
    p = m.drop_duplicates("CODIGO PRODUCTO")
    p = p[~p["CODIGO PRODUCTO"].isin(con_stock | movidos | comprados)]
    ult = _fecha(p["CODIGO PRODUCTO"].map(_ultimo_mov(t, "CODIGO PRODUCTO")))
    p = p.assign(_f=ult, _dato=ult.dt.strftime("%b %Y").fillna("nunca"),
                 _areas=p["CODIGO PRODUCTO"].map(
                     m.groupby("CODIGO PRODUCTO").size()).astype(str) + " áreas")
    return _casos(p, codigo="CODIGO PRODUCTO", nombre="NOMBRE PRODUCTO",
                  area="_areas", dato="_dato", fecha="_f")


def servicio_con_stock(t, hoy):
    """Un servicio o gasto con existencia: nadie lo da de baja y crece."""
    inv = t["inv"]
    d = inv[_activa(inv["TIPO PRODUCTO"], "SERVICIO")
            & (_num(inv["STOCK AL DIA"]).fillna(0) != 0)]
    d = d.assign(_dato=_cant(_num(d["STOCK AL DIA"]), d["UNIDAD KARDEX"]))
    return _casos(d, codigo="CODIGO PRODUCTO", nombre="NOMBRE PRODUCTO",
                  area="NOMBRE AREA", dato="_dato", soles="VALORIZADO TOTAL")


def unidad_sin_factor(t, hoy):
    """La unidad de entrada y la de salida son distintas y el factor es 1."""
    inv = t["inv"]
    p = inv[_activa(inv["PRODUCTO ACTIVO"], "ACTIVO")
            & _activa(inv["TIPO PRODUCTO"], "MERCADERIA")].drop_duplicates("CODIGO PRODUCTO")
    uk, us = _up(p["UNIDAD KARDEX"]), _up(p["UNIDAD SALIDA"])
    p = p[(uk != us) & (uk != "") & (us != "") & (_num(p["FACTOR"]) == 1)]
    p = p.assign(_dato=_txt(p["UNIDAD KARDEX"]) + " → " + _txt(p["UNIDAD SALIDA"]))
    return _casos(p, codigo="CODIGO PRODUCTO", nombre="NOMBRE PRODUCTO",
                  dato="_dato")


def habilitado_sin_uso(t, hoy):
    """Habilitado en un área donde no tiene stock ni un movimiento en
    `VENTANA_LARGA` días, mientras SÍ se mueve en otra."""
    inv = t["inv"]
    d = inv[inv["_activo"] & (_num(inv["STOCK AL DIA"]).fillna(0) == 0)]
    k = _movidos(t, hoy - pd.Timedelta(days=VENTANA_LARGA))
    pares = set(zip(k["CODIGO AREA"], k["CODIGO PRODUCTO"]))
    _, area = _nombres(t)
    donde = (k.drop_duplicates(["CODIGO PRODUCTO", "CODIGO AREA"])
              .assign(_n=lambda x: x["CODIGO AREA"].map(area).fillna(x["CODIGO AREA"]))
              .groupby("CODIGO PRODUCTO")["_n"]
              .agg(lambda s: ", ".join(sorted(s.astype(str).str.title()))))
    vivo = d["CODIGO PRODUCTO"].isin(donde.index)
    sin = ~pd.Series([p in pares for p in zip(d["CODIGO AREA"], d["CODIGO PRODUCTO"])],
                     index=d.index)
    d = d[vivo & sin]
    d = d.assign(_dato=d["CODIGO PRODUCTO"].map(donde))
    return _casos(d, codigo="CODIGO PRODUCTO", nombre="NOMBRE PRODUCTO",
                  area="NOMBRE AREA", dato="_dato")


# --- RECETAS ----------------------------------------------------------------

def _rb_vivas(t):
    rb = t["rb"]
    return rb[_activa(rb["RB ACT"], "RB.ACTIV") & _activa(rb["RB ART ACT"], "ART.ACT")]


def _rv_vivas(t):
    rv = t["rv"]
    return rv[_activa(rv["ITEM VENTA ACTIVO"], "ACTIV") & _activa(rv["RV ACTIV"], "RV ACT")]


def receta_base_quieta(t, hoy):
    """Receta base viva cuyo producto no se movió (producción, descargo,
    porcionamiento, transferencia…) en `VENTANA_LARGA` días."""
    rb = _rb_vivas(t).drop_duplicates("COD RB")
    movidos = set(_movidos(t, hoy - pd.Timedelta(days=VENTANA_LARGA))["CODIGO PRODUCTO"])
    rb = rb[~rb["COD PROD RB"].isin(movidos)]
    f = _fecha(rb["COD PROD RB"].map(_ultimo_mov(t, "CODIGO PRODUCTO")))
    rb = rb.assign(_f=f, _dato=f.dt.strftime("%b %Y").fillna("nunca"))
    return _casos(rb, codigo="COD PROD RB", nombre="RB NOMBRE",
                  area="RB AREA PROD", dato="_dato", fecha="_f", quien="USUARIO REG")


def receta_base_de_articulo_inactivo(t, hoy):
    """Receta base ACTIVA cuyo artículo está dado de baja: sigue costeando y
    descargando un producto que el maestro ya no tiene."""
    rb = t["rb"]
    rb = rb[_activa(rb["RB ACT"], "RB.ACTIV") & _activa(rb["RB ART ACT"], "ART.INAC")]
    rb = rb.drop_duplicates("COD RB")
    rb = rb.assign(_f=_fecha(rb["FECH REG"]))
    rb = rb.assign(_dato="desde " + rb["_f"].dt.strftime("%b %Y").fillna("?"))
    return _casos(rb, codigo="COD PROD RB", nombre="RB NOMBRE",
                  area="RB AREA PROD", dato="_dato", soles="RB COSTO",
                  fecha="_f", quien="USUARIO REG")


def receta_con_insumo_de_baja(t, hoy):
    """Una línea de una receta viva apunta a un insumo inactivo, o a uno que
    no está habilitado en el área desde la que se descarga (sólo recetas de
    venta: la base no dice su área por línea). `soles` es la venta del plato
    en la ventana (las recetas base, sin monto)."""
    rv = _rv_vivas(t)
    inv = t["inv"]
    hab = set(zip(_up(inv.loc[_activa(inv["COMPARTIDO"], "COMPARTIDO"), "NOMBRE AREA"]),
                  inv.loc[_activa(inv["COMPARTIDO"], "COMPARTIDO"), "CODIGO PRODUCTO"]))
    con_ins = _txt(rv["COD INS"]) != ""
    inact = _activa(rv["INS ACTIVO"], "INACTIV")
    area = _up(rv["SUBALM INS"])
    no_hab = ~pd.Series([p in hab for p in zip(area, rv["COD INS"])], index=rv.index) \
        & (area != "") & ~inact
    dato = ("no habilitado en " + area.str.title()).mask(inact, "insumo inactivo")
    d = rv[con_ins & (inact | no_hab)].assign(
        _dato=dato, _nom=_txt(rv["NOMB PLATO"]) + " · " + _txt(rv["INS RV"]))
    venta = _venta_por_plato(t)["venta"]
    d = d.assign(_s=d["COD PLATO"].map(venta))
    a = _casos(d, codigo="COD PLATO", nombre="_nom", area="SUBALM INS",
               dato="_dato", soles="_s", fecha=_fecha(d["FECH MODIF"]), quien="USUARIO REG")
    rb = t["rb"]
    rb = rb[_activa(rb["RB ACT"], "RB.ACTIV") & _activa(rb["RB ART ACT"], "ART.ACT")
            & _activa(rb["INS ACTIVO"], "INS.INAC")]
    rb = rb.assign(_nom=_txt(rb["RB NOMBRE"]) + " · " + _txt(rb["INSUMO"]),
                   _dato="insumo inactivo (receta base)")
    b = _casos(rb, codigo="COD PROD RB", nombre="_nom", area="RB AREA PROD",
               dato="_dato", fecha=_fecha(rb["FECH REG"]), quien="USUARIO REG")
    return pd.concat([a, b], ignore_index=True)


def _cambios_de_factor(t, hoy, dias=UN_ANO):
    """Las filas de la auditoría del POS que cambian el factor o una unidad de
    un artículo que ya existía (ANTES vacío = artículo NUEVO, regla #658)."""
    a = t["aud"]
    a = a[_txt(a["CAMPO"]).isin(("Factor", "Unidad de Kardex", "Unidad de Salida"))]
    antes, despues = _txt(a["ANTES"]), _txt(a["DESPUES"])
    na, nd = _num(antes), _num(despues)
    distinto = np.where(na.notna() & nd.notna(), (na - nd).abs() > 1e-9, antes != despues)
    a = a[(antes != "") & distinto]
    f = _fecha(a["FECHA"])
    a = a.assign(_f=f)[f >= hoy - pd.Timedelta(days=dias)]
    ua, ud = _txt(a["UNIDAD ANTES"]), _txt(a["UNIDAD DESPUES"])
    es_u = (ua != "") & (ud != "")
    txt = np.where(es_u, ua + " → " + ud,
                   _txt(a["ANTES"]).str.replace(r"\.0+$", "", regex=True) + " → "
                   + _txt(a["DESPUES"]).str.replace(r"\.0+$", "", regex=True))
    a = a.assign(_dato=_txt(a["CAMPO"]).str.lower() + " " + pd.Series(txt, index=a.index))
    # Un cambio de unidad sale en dos o tres filas con el mismo correlativo
    # (factor, unidad de kardex, unidad de salida): un caso.
    return (a.groupby(["CODIGO", "CORRELATIVO"], sort=False)
             .agg(_f=("_f", "min"), USUARIO=("USUARIO", "first"),
                  _dato=("_dato", " · ".join))
             .reset_index())


def _recetas_que_usan(t):
    """`(cod insumo → [(plato, fecha de la receta)], ídem recetas base)`."""
    rv, rb = _rv_vivas(t), _rb_vivas(t)
    a = rv.assign(_f=_fecha(rv["FECH MODIF"]))[["COD INS", "COD PLATO", "_f"]]
    b = rb.assign(_f=_fecha(rb["FECH REG"]))[["COD INS RB", "COD RB", "_f"]]
    return (a.rename(columns={"COD INS": "ins", "COD PLATO": "rec"}),
            b.rename(columns={"COD INS RB": "ins", "COD RB": "rec"}))


def factor_sin_tocar_recetas(t, hoy):
    """Un cambio de factor o de unidad (el último de cada artículo) que
    ninguna receta viva que lo lleva acompañó con una edición POSTERIOR."""
    c = _cambios_de_factor(t, hoy, dias=10 * UN_ANO)
    c = c.sort_values("_f").drop_duplicates("CODIGO", keep="last")
    a, b = _recetas_que_usan(t)
    r = pd.concat([a, b], ignore_index=True)
    r = r.merge(c[["CODIGO", "_f"]].rename(columns={"CODIGO": "ins", "_f": "_cambio"}),
                on="ins")
    viejas = r[r["_f"].isna() | (r["_f"] < r["_cambio"])].groupby("ins")["rec"].nunique()
    c = c[c["CODIGO"].isin(viejas.index)]
    prod, _ = _nombres(t)
    c = c.assign(_nom=c["CODIGO"].map(prod).fillna(c["CODIGO"]),
                 _n=c["CODIGO"].map(viejas).astype(int).astype(str) + " recetas")
    return _casos(c, codigo="CODIGO", nombre="_nom", area="_n", dato="_dato",
                  fecha="_f", quien="USUARIO")


def costo_fuera_de_rango(t, hoy):
    """Plato activo con receta o enlace a costo 0, o por encima de
    `PCT_COSTO_ALTO` % de su precio."""
    cc = t["cc"]
    # Venta Interna se factura al costo a propósito: siempre pasaría el umbral.
    cc = cc[_activa(cc["ITEM VENT ACT"], "ACTIV")
            & _up(cc["TIPO DESC"]).isin(("RECETA", "DIRECTO"))
            & (_up(cc["GRUPO"]) != "VENTA INTERNA")]
    # El % se saca acá, sobre el NETO: el del parquet se dispara con los
    # platos a S/ 0,01 (cortesías de carta, el hielo) y no dice nada.
    costo, neto = _num(cc["COSTO SALON"]), _num(cc["P.NET SALON"])
    cc = cc[neto >= 1]
    costo, neto = costo[cc.index], neto[cc.index]
    pct = 100 * costo / neto
    d = cc[(costo.fillna(0) == 0) | (pct > PCT_COSTO_ALTO)]
    d = d.assign(_dato=pct[d.index].map(lambda x: "" if pd.isna(x) else f"{x:.1f} %"))
    return _casos(d, codigo="COD PLATO", nombre="ITEM VENT", area="GRUPO",
                  dato="_dato", soles="COSTO SALON")


# --- CARTA Y VENTAS ---------------------------------------------------------

def plato_sin_venta(t, hoy):
    """Plato activo (no servicios: NO APLICA) sin una venta en `VENTANA` días."""
    cc = t["cc"]
    cc = cc[_activa(cc["ITEM VENT ACT"], "ACTIV") & (_up(cc["TIPO DESC"]) != "NO APLICA")]
    f = _fecha(cc["ULTIMA VENT"])
    d = cc.assign(_f=f)[f.isna() | (f < hoy - pd.Timedelta(days=VENTANA))]
    d = d.assign(_dato=d["_f"].dt.strftime("%d %b %Y").fillna("nunca"))
    return _casos(d, codigo="COD PLATO", nombre="ITEM VENT", area="GRUPO",
                  dato="_dato", fecha="_f", quien="USUARIO REG")


def vende_sin_descargo(t, hoy):
    """Plato vendido en la ventana que no descarga nada: sin receta ni enlace
    (SIN ENLACE), o con receta o enlace a costo 0. `soles` es su venta."""
    cc = t["cc"]
    tipo = _up(cc["TIPO DESC"])
    d = cc[(tipo == "SIN ENLACE")
           | (tipo.isin(("RECETA", "DIRECTO")) & (_num(cc["COSTO SALON"]).fillna(0) == 0))]
    v = _venta_por_plato(t)
    d = d[d["COD PLATO"].isin(v.index[v["unid"] > 0])]
    d = d.assign(_u=d["COD PLATO"].map(v["unid"]), _s=d["COD PLATO"].map(v["venta"]),
                 _t=tipo[d.index].str.lower())
    d = d.assign(_dato=d["_u"].map(lambda x: f"{x:,.0f} und") + " · " + d["_t"])
    return _casos(d, codigo="COD PLATO", nombre="ITEM VENT", area="GRUPO",
                  dato="_dato", soles="_s")


def descarga_donde_no_entra(t, hoy):
    """Producto × área que el descargo de ventas (95) bajó en la ventana y
    donde no entró nada (requerimiento, transferencia, compra, producción) en
    `VENTANA_LARGA` días: el plato descuenta desde el área equivocada."""
    k95 = _movidos(t, hoy - pd.Timedelta(days=VENTANA), tipos=("95",))
    s = k95.groupby(["CODIGO AREA", "CODIGO PRODUCTO"]).agg(
        cant=("CANT SALIDA", "sum"), soles=("VALOR SALIDA", "sum")).reset_index()
    ent = _movidos(t, hoy - pd.Timedelta(days=VENTANA_LARGA))
    ent = ent[_num(ent["CANT INGRESO"]) > 0]
    pares = set(zip(ent["CODIGO AREA"], ent["CODIGO PRODUCTO"]))
    s = s[~pd.Series([p in pares for p in zip(s["CODIGO AREA"], s["CODIGO PRODUCTO"])],
                     index=s.index) & (s["cant"] > 0)]
    prod, area = _nombres(t)
    s = s.assign(_nom=s["CODIGO PRODUCTO"].map(prod), _area=s["CODIGO AREA"].map(area),
                 _dato=s["cant"].map(lambda x: f"−{x:,.1f}"))
    return _casos(s, codigo="CODIGO PRODUCTO", nombre="_nom", area="_area",
                  dato="_dato", soles="soles")


def combo_no_reconocido(t, hoy):
    """Línea vendida como combo (`ES COMBO` del Sheet) cuyo código no está en
    `definicion_venta.COMBOS`: su costo se multiplica por la cantidad."""
    import definicion_venta
    v = t["ven"]
    if v is None or v.empty or "ES COMBO" not in v.columns:
        return _vacio()
    v = definicion_venta.solo_venta(v)
    d = v[(_num(v["ES COMBO"]) == 1)
          & ~_txt(v["COD ITEM VENTA DDOCUMENTO"]).isin(definicion_venta.COMBOS)]
    g = d.groupby(["COD ITEM VENTA DDOCUMENTO", "NOMB ITEM VENTA"]).agg(
        u=("CANTIDAD ITEM DDOCUMENTO", "sum"),
        s=("NETO TOTAL ITEM DDOCUMENTO", "sum")).reset_index()
    g = g.assign(_dato=g["u"].map(lambda x: f"{x:,.0f} und"))
    return _casos(g, codigo="COD ITEM VENTA DDOCUMENTO", nombre="NOMB ITEM VENTA",
                  dato="_dato", soles="s")


# --- COMPRAS ----------------------------------------------------------------

def _compras_ventana(t, hoy, dias=VENTANA):
    c = t["cmp"]
    return c[_fecha(c["FECHA_EMISION_DOC"]) >= hoy - pd.Timedelta(days=dias)]


def comprado_sin_uso(t, hoy):
    """Mercadería comprada en la ventana sin ninguna salida de uso (venta,
    producción, porcionamiento, nota) en `VENTANA_LARGA` días, en ninguna
    área: entra y sólo puede salir como faltante."""
    c = _compras_ventana(t, hoy)
    inv = t["inv"]
    merc = set(inv.loc[_activa(inv["TIPO PRODUCTO"], "MERCADERIA"), "CODIGO PRODUCTO"])
    # Los insumos de operación no los descarga nadie: se consumen al contar
    # (regla #645). Van aparte, no acá.
    c = c[c["COD_PRODUCTO"].isin(merc) & (_up(c["FAMILIA"]) != FAMILIA_OPERACION)]
    usados = set(_movidos(t, hoy - pd.Timedelta(days=VENTANA_LARGA), tipos=TIPOS_USO)
                 ["CODIGO PRODUCTO"])
    c = c[~c["COD_PRODUCTO"].isin(usados)]
    g = c.groupby(["COD_PRODUCTO", "NOMBRE_PRODUCTO"]).agg(
        cant=("CANTIDAD_COMPRA", "sum"), um=("UNIDAD_DE_INGRESO", "first"),
        soles=("VALOR_COMPRA", "sum"), fam=("FAMILIA", "first"),
        f=("FECHA_EMISION_DOC", "max")).reset_index()
    g = g.assign(_dato=_cant(g["cant"], g["um"]))
    return _casos(g, codigo="COD_PRODUCTO", nombre="NOMBRE_PRODUCTO", area="fam",
                  dato="_dato", soles="soles", fecha=_fecha(g["f"]))


def mercaderia_sin_kardex(t, hoy):
    """Comprado en la ventana como un producto de SERVICIO, en una familia
    donde 8 de cada 10 productos son mercadería."""
    inv = t["inv"].drop_duplicates("CODIGO PRODUCTO")
    es_merc = _activa(inv["TIPO PRODUCTO"], "MERCADERIA")
    parte = es_merc.groupby(inv["NOMBRE FAMILIA"]).mean()
    serv = set(inv.loc[~es_merc, "CODIGO PRODUCTO"])
    c = _compras_ventana(t, hoy)
    c = c[c["COD_PRODUCTO"].isin(serv)]
    fam_inv = inv.set_index("CODIGO PRODUCTO")["NOMBRE FAMILIA"]
    c = c.assign(_fam=c["COD_PRODUCTO"].map(fam_inv))
    c = c[c["_fam"].map(parte).fillna(0) >= 0.8]
    g = c.groupby(["COD_PRODUCTO", "NOMBRE_PRODUCTO", "_fam"]).agg(
        soles=("VALOR_COMPRA", "sum")).reset_index()
    return _casos(g, codigo="COD_PRODUCTO", nombre="NOMBRE_PRODUCTO", area="_fam",
                  dato="servicio", soles="soles")


def _normal(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().replace(".", " ").split())


def dos_codigos(t, hoy):
    """Dos o más códigos activos con el mismo nombre (sin tildes, puntos ni
    espacios dobles) y la misma unidad."""
    inv = t["inv"]
    p = inv[_activa(inv["PRODUCTO ACTIVO"], "ACTIVO")
            & _activa(inv["TIPO PRODUCTO"], "MERCADERIA")].drop_duplicates("CODIGO PRODUCTO")
    p = p.assign(_k=p["NOMBRE PRODUCTO"].map(_normal) + "|" + _up(p["UNIDAD KARDEX"]))
    g = p.groupby("_k").agg(n=("CODIGO PRODUCTO", "nunique"),
                            cods=("CODIGO PRODUCTO", lambda s: ", ".join(sorted(s))),
                            nom=("NOMBRE PRODUCTO", "first"))
    g = g[g["n"] >= 2].reset_index()
    return _casos(g, codigo="cods", nombre="nom", dato=g["n"].astype(str) + " códigos")


# --- MOVIMIENTOS RAROS ------------------------------------------------------

def cambios_de_factor(t, hoy):
    """Los cambios de factor o de unidad del último año sobre artículos que
    lleva alguna receta viva, con quién y cuándo (la auditoría del POS)."""
    c = _cambios_de_factor(t, hoy)
    a, b = _recetas_que_usan(t)
    n = pd.concat([a, b]).groupby("ins")["rec"].nunique()
    c = c[c["CODIGO"].isin(n.index)]
    prod, _ = _nombres(t)
    c = c.assign(_nom=c["CODIGO"].map(prod).fillna(c["CODIGO"]),
                 _n=c["CODIGO"].map(n).astype(int).astype(str) + " recetas")
    return _casos(c, codigo="CODIGO", nombre="_nom", area="_n", dato="_dato",
                  fecha="_f", quien="USUARIO")


def precio_editado_a_mano(t, hoy):
    """El precio de costo de un artículo escrito a mano a `VECES_RARO` veces
    lo que era, o a menos de su inversa, en el último año."""
    a = t["aud"]
    a = a[_txt(a["CAMPO"]) == "Precio de Costo"]
    na, nd = _num(a["ANTES"]), _num(a["DESPUES"])
    r = nd / na.where(na > 0)
    f = _fecha(a["FECHA"])
    a = a.assign(_f=f, _r=r)[(f >= hoy - pd.Timedelta(days=UN_ANO))
                             & ((r >= VECES_RARO) | (r <= 1 / VECES_RARO))]
    prod, _ = _nombres(t)
    a = a.assign(_nom=a["CODIGO"].map(prod).fillna(a["CODIGO"]),
                 _dato=[f"{x:,.2f} → {y:,.2f}" for x, y in zip(_num(a["ANTES"]), _num(a["DESPUES"]))])
    return _casos(a, codigo="CODIGO", nombre="_nom", dato="_dato", fecha="_f",
                  quien="USUARIO")


def porcionamiento_raro(t, hoy):
    """Porcionamiento de la ventana con merma negativa (salió más de lo que
    entró), del 90 % o más, o fuera de lo normal de su producto: más allá de
    dos rangos intercuartiles de sus porcionamientos del último año (con 8 o
    más). `soles` es lo que costó lo que entró (Σ cant × precio de los
    cortes, regla #510)."""
    p = t["porc"]
    p = p.assign(_f=_fecha(p["FEC REGIST"]),
                 _costo=_num(p["CANT RESULT"]) * _num(p["PREC PROM PROD FIN"]))
    h = p.groupby("COD PORC").agg(
        cod=("COD PROD INIC", "first"), prod=("PROD INICIAL", "first"),
        f=("_f", "first"), cant=("CANT A PORCIONAR", "first"),
        merma=("CANT MERMA", "first"), costo=("_costo", "sum"),
        area=("SUB ALMACEN", "first"), quien=("USUARIO REG", "first")).reset_index()
    h = h[(_num(h["cant"]) > 0) & (h["f"] >= hoy - pd.Timedelta(days=UN_ANO))]
    h["pct"] = _num(h["merma"]) / _num(h["cant"])
    q = h.groupby("cod")["pct"].agg(q1=lambda s: s.quantile(.25),
                                    q3=lambda s: s.quantile(.75), n="size")
    h = h.join(q, on="cod")
    iqr = 2 * (h["q3"] - h["q1"]).clip(lower=0.05)
    fuera = (h["n"] >= 8) & ((h["pct"] > h["q3"] + iqr) | (h["pct"] < h["q1"] - iqr))
    h = h[(h["f"] >= hoy - pd.Timedelta(days=VENTANA))
          & ((h["pct"] < 0) | (h["pct"] >= 0.9) | fuera)]
    h = h.assign(_dato=h["pct"].map(lambda x: f"merma {x:.0%}"))
    return _casos(h, codigo="COD PORC", nombre="prod", area="area", dato="_dato",
                  soles="costo", fecha="f", quien="quien")


def compra_precio_raro(t, hoy):
    """La marca «revisar» de Compras (`producto.marcar_revisar`, regla #653)
    sobre las compras de la ventana, con el precio habitual de «Compras por
    período» (`semanal.precio_habitual`)."""
    from graficos.compras.producto import marcar_revisar
    from graficos.compras.semanal import precio_habitual
    c = t["cmp"]
    c = c[_fecha(c["FECHA_EMISION_DOC"]) >= hoy - pd.Timedelta(days=VENTANA + 90)]
    ref = precio_habitual(c["COD_PRODUCTO"], c["FECHA_EMISION_DOC"],
                          c["VALOR_COMPRA"], c["CANTIDAD_COMPRA"])
    flag = marcar_revisar(c["CANTIDAD_COMPRA"], c["VALOR_COMPRA"], ref,
                          c["UNIDAD_DE_INGRESO"])
    c = c.assign(_ref=ref.to_numpy(), _flag=flag, _f=_fecha(c["FECHA_EMISION_DOC"]))
    c = c[(c["_flag"] != "") & (c["_f"] >= hoy - pd.Timedelta(days=VENTANA))]
    pu = _num(c["VALOR_COMPRA"]) / _num(c["CANTIDAD_COMPRA"])
    c = c.assign(_dato=np.where(c["_flag"] == "um",
                                _num(c["CANTIDAD_COMPRA"]).map(lambda x: f"{x:g}") + " "
                                + _txt(c["UNIDAD_DE_INGRESO"]).str.lower(),
                                (pu / c["_ref"]).map(lambda x: f"×{x:.1f}")))
    return _casos(c, codigo="COD_PRODUCTO", nombre="NOMBRE_PRODUCTO",
                  area="NOMBRE_PROVEEDOR", dato="_dato", soles="VALOR_COMPRA",
                  fecha="_f")


def sobro_sin_entrar(t, hoy):
    """En un conteo de la ventana sobró algo que el sistema tenía en CERO y
    que no tuvo ninguna entrada desde el conteo anterior de ese producto en
    esa área. Con el sistema en negativo el sobrante es un descargo
    adelantado (regla #650); en cero, la mercadería apareció."""
    a = t["ajs"]
    # El cierre escribe los códigos con 10 dígitos; el kardex, con 7 y 3.
    a = a.assign(_f=_fecha(a["FECHA APERTURA INVENTARIO"]).dt.normalize(),
                 **{"CODIGO PRODUCTO": _txt(a["CODIGO PRODUCTO"]).str[-7:],
                    "CODIGO AREA": _txt(a["CODIGO AREA"]).str[-3:]})
    a = a.sort_values("_f")
    a["_prev"] = a.groupby(["CODIGO AREA", "CODIGO PRODUCTO"])["_f"].shift()
    d = a[(a["_f"] >= hoy - pd.Timedelta(days=VENTANA)) & (_num(a["AJUSTE"]) > 0)
          & (_num(a["STOCK AL CIERRE"]).fillna(0) == 0)]
    k = _kardex(t)
    k = k[(_num(k["CANT INGRESO"]) > 0) & ~k["_tipo"].isin(TIPOS_SIN_USO)]
    k = k[k["CODIGO PRODUCTO"].isin(set(d["CODIGO PRODUCTO"]))]
    m = d.reset_index().merge(k[["CODIGO AREA", "CODIGO PRODUCTO", "_dia"]],
                              on=["CODIGO AREA", "CODIGO PRODUCTO"], how="left")
    entro = m[(m["_dia"] <= m["_f"]) & (m["_prev"].isna() | (m["_dia"] > m["_prev"]))]["index"]
    d = d[~d.index.isin(set(entro))]
    d = d.assign(_dato="+" + pd.Series(_cant(_num(d["AJUSTE"]), d["UNIDAD MEDIDA"]),
                                       index=d.index))
    return _casos(d, codigo="CODIGO PRODUCTO", nombre="PRODUCTO", area="AREA",
                  dato="_dato", soles="AJUSTE VALORIZADO", fecha="_f")


def sunat_sin_ingresar(t, hoy):
    """Comprobante del SIRE que el Almacén no tiene («Solo SUNAT» del cruce de
    Documentos SUNAT), emitido en la ventana y hace más de `DIAS_SUNAT` días.
    Sin bancos ni financieras (`data._NO_MERCADERIA`, que el cruce ya sacó)."""
    s = t.get("sunat")
    if s is None or len(s) == 0:
        return _vacio()
    if "tipo" in s.columns:
        # Sólo mercadería (`tipo_compra`, regla #640): un alquiler o una
        # comisión de tarjeta no entra al Almacén y está bien.
        s = s[s["tipo"] == "Mercadería"]
    f = _fecha(s["fecha_emision"])
    s = s.assign(_f=f)[(s["estado"] == "Solo SUNAT")
                       & (f >= hoy - pd.Timedelta(days=VENTANA))
                       & (f <= hoy - pd.Timedelta(days=DIAS_SUNAT))]
    # Una factura que el proveedor anuló con una nota del mismo monto, las dos
    # sin ingresar, no es mercadería que entró: se sacan las dos.
    tot = _num(s["total_sunat"]).round(2)
    par = pd.Series(list(zip(_txt(s["proveedor"]), tot.abs())), index=s.index)
    notas = set(par[tot < 0])
    s = s[(tot > 0) & ~par.isin(notas)]
    s = s.assign(_dato=_dias(hoy, s["_f"]))
    return _casos(s, codigo="documento", nombre="proveedor", dato="_dato",
                  soles="total_sunat", fecha="_f")


def venta_sin_descargar(t, hoy):
    """Pedidos del último año que ninguna corrida del Descargo de Ventas tomó
    (el POS filtra por la hora del PEDIDO, regla #650), sumados por día. Hasta
    el final de la última corrida: lo de después todavía puede tomarse."""
    d = t["dsc"]
    ini, fin = _fecha(d["VENTAS DESDE"]), _fecha(d["VENTAS HASTA"])
    ok = ini.notna() & fin.notna() & (fin > ini)
    iv = pd.DataFrame({"i": ini[ok], "f": fin[ok]}).sort_values("i")
    # Fundir los tramos que se pisan y buscar cada pedido con searchsorted.
    tramos = []
    for i, f in zip(iv["i"], iv["f"]):
        if tramos and i <= tramos[-1][1]:
            tramos[-1][1] = max(tramos[-1][1], f)
        else:
            tramos.append([i, f])
    if not tramos:
        return _vacio()
    ti = np.array([x[0] for x in tramos], dtype="datetime64[ns]")
    tf = np.array([x[1] for x in tramos], dtype="datetime64[ns]")
    p = t["ped"]
    fp = _fecha(p["FECHA APERTURA"])
    p = p.assign(_f=fp)[(fp >= hoy - pd.Timedelta(days=UN_ANO)) & (fp <= tf.max())
                        & (_num(p["PLATOS"]) > 0)
                        & ~_up(p["ESTADO PEDIDO"]).str.contains("ANUL")]
    pos = np.searchsorted(ti, p["_f"].to_numpy(dtype="datetime64[ns]"), side="right") - 1
    dentro = (pos >= 0) & (p["_f"].to_numpy(dtype="datetime64[ns]") <= tf[np.clip(pos, 0, None)])
    p = p[~dentro]
    dia = _fecha(p["DIA CONTABLE"]).dt.normalize().fillna(p["_f"].dt.normalize())
    g = p.assign(_d=dia).groupby("_d").agg(n=("CODIGO PEDIDO", "nunique"),
                                           platos=("PLATOS", "sum"),
                                           s=("MONTO PEDIDO", "sum")).reset_index()
    g = g.assign(_nom=g["_d"].dt.strftime("%d %b %Y"),
                 _dato=g["n"].astype(str) + " pedidos · " + g["platos"].map(lambda x: f"{x:,.0f}") + " platos")
    return _casos(g, codigo=g["_d"].dt.strftime("%Y-%m-%d"), nombre="_nom",
                  dato="_dato", soles="s", fecha="_d")


def notas_en_lote(t, hoy):
    """Notas de salida de un área registradas una detrás de otra —sin una
    pausa de `PAUSA_LOTE` minutos— de a `LOTE_NOTAS` o más, en el último año
    (regla #614: la comida de personal de un mes, en 27 minutos)."""
    s = t["sal"]
    s = s[~_up(s["NOMBRE ESTADO SALIDA"]).str.contains("ANUL")]
    s = s.assign(_r=_fecha(s["FECHA REGISTRO"]), _p=_fecha(s["FECHA PROCESADO"]))
    s = s[s["_r"] >= hoy - pd.Timedelta(days=UN_ANO)]
    docs = s.groupby(["AREA", "COD SALIDA"]).agg(
        r=("_r", "first"), p=("_p", "first"), v=("VALOR NETO", "sum"),
        mot=("MOTIVO", "first")).reset_index().sort_values(["AREA", "r"])
    corte = (docs.groupby("AREA")["r"].diff() > pd.Timedelta(minutes=PAUSA_LOTE)) \
        | docs["AREA"].ne(docs["AREA"].shift())
    docs["lote"] = corte.cumsum()
    g = docs.groupby("lote").agg(area=("AREA", "first"), n=("COD SALIDA", "size"),
                                 ini=("r", "min"), fin=("r", "max"), v=("v", "sum"),
                                 pmin=("p", "min"), pmax=("p", "max"),
                                 mot=("mot", lambda x: x.mode().iat[0] if len(x.mode()) else ""))
    g = g[g["n"] >= LOTE_NOTAS].reset_index()
    mins = ((g["fin"] - g["ini"]).dt.total_seconds() / 60).round().astype(int)
    g = g.assign(_nom=g["ini"].dt.strftime("%d %b %H:%M") + " · " + _txt(g["mot"]).str.capitalize(),
                 _dato=g["n"].astype(str) + " en " + mins.astype(str) + " min")
    return _casos(g, codigo=g["lote"].astype(str), nombre="_nom", area="area",
                  dato="_dato", soles="v", fecha="ini")


def _fuera_de_lo_suyo(d, quien, dia, monto):
    """Los días en que `quien` llevó un monto a `VECES_HABITUAL` veces su
    mediana diaria y por encima de `MINIMO_DIA`."""
    g = d.groupby([quien, dia])[monto].sum().reset_index()
    med = g.groupby(quien)[monto].median()
    g = g.assign(_med=g[quien].map(med))
    return g[(g[monto] >= VECES_HABITUAL * g["_med"]) & (g[monto] >= MINIMO_DIA)]


def anulados_y_cortesias(t, hoy):
    """Días en que un usuario anuló —o un mesero dio en cortesía— mucho más
    que lo suyo. Señal, no prueba: un error de comanda deja el mismo rastro."""
    p = t["ped"]
    p = p.assign(_d=_fecha(p["DIA CONTABLE"]).dt.normalize(),
                 _m=_num(p["MONTO ANULADO"]).fillna(0),
                 _u=_txt(p["USUARIO ANULACION"]))
    p = p[(p["_m"] > 0) & (p["_u"] != "") & (p["_d"] >= hoy - pd.Timedelta(days=UN_ANO))]
    a = _fuera_de_lo_suyo(p, "_u", "_d", "_m")
    a = a[a["_d"] >= hoy - pd.Timedelta(days=VENTANA)]
    a = a.assign(_nom=a["_d"].dt.strftime("%d %b") + " · anulado",
                 _dato=(a["_m"] / a["_med"]).map(lambda x: f"×{x:.1f}"))
    out = [_casos(a, codigo=a["_d"].dt.strftime("%Y-%m-%d"), nombre="_nom",
                  dato="_dato", soles="_m", fecha="_d", quien="_u")]
    v = t["ven"]
    if v is not None and len(v) and "CLASE VENTA" in v.columns:
        import definicion_venta
        c = v[v["CLASE VENTA"] == definicion_venta.CORTESIA]
        c = c.assign(_d=_fecha(c["FEC REG DOCUMENTO"]).dt.normalize(),
                     _m=_num(c["PRECIO VENTA ITEM DDOCUMENTO"]) * _num(c["CANTIDAD ITEM DDOCUMENTO"]),
                     _u=_txt(c["NOMBRE MESERO"]))
        c = _fuera_de_lo_suyo(c[c["_u"] != ""], "_u", "_d", "_m")
        c = c.assign(_nom=c["_d"].dt.strftime("%d %b") + " · cortesía",
                     _dato=(c["_m"] / c["_med"]).map(lambda x: f"×{x:.1f}"))
        out.append(_casos(c, codigo=c["_d"].dt.strftime("%Y-%m-%d"), nombre="_nom",
                          dato="_dato", soles="_m", fecha="_d", quien="_u"))
    return pd.concat(out, ignore_index=True)


# --- el registro --------------------------------------------------------------

DOMINIOS = (
    ("stock", "Stock"), ("recetas", "Recetas"), ("carta", "Carta y ventas"),
    ("compras", "Compras"), ("raros", "Movimientos raros"),
)
"""Los grupos de la vista, en su orden. «Movimientos raros» no es el estado
del maestro sino EVENTOS con fecha: señales, no pruebas."""

Control = namedtuple("Control", (
    "id", "dominio", "nombre", "fn", "grave", "mide", "porque", "regla",
    "accion", "ya_lo_ve", "columnas", "agrupar"))
"""Un control. `grave`: rojo cuando tiene casos (si no, ámbar; sin casos,
verde). `columnas`: el rótulo de `nombre`, `area` y `dato` en su ficha.
`agrupar`: la columna de CASOS por la que se dice «se concentra en».
`ya_lo_ve`: el reporte que ya lo marca de a uno, o "". Los textos se
escriben para leerse en la ficha: sin cifras, que cambian con el dato."""

CONTROLES = (
    Control("s1", "stock", "Stock parado", stock_parado, False,
            "Con existencia y sin un movimiento de uso ni de entrada en 90 días",
            "Plata quieta. Puede ser un vino de guarda, que está bien, o menaje "
            "que entró como mercadería y nunca se descarga, o algo que se dejó "
            "de usar y nadie dio de baja.",
            "Stock > 0 en el maestro y ninguna línea de kardex en 90 días por "
            "producto × área, sin contar los conteos (93) ni el saldo inicial.",
            "Lo que se dejó de usar: nota de salida y desactivarlo en el área. "
            "El menaje: un tipo sin control de stock.",
            "", ("Producto", "Área", "Quieto"), "area"),
    Control("s2", "stock", "Stock en negativo", stock_negativo, True,
            "El sistema dice que hay menos de cero",
            "Imposible en la realidad: se descargó antes de que entrara. Casi "
            "siempre es un corte que el plato descarga y cuyo porcionamiento no "
            "llegó, o llegó a otra área, o un requerimiento procesado tarde.",
            "Stock < 0 en un área activa, de un producto activo y habilitado.",
            "Revisar desde qué área descarga la receta (SUBALM INS) y en cuál "
            "se porciona o se recibe el producto.",
            "Ajuste › Análisis de diferencias", ("Producto", "Área", "Stock"), "area"),
    Control("s3", "stock", "Con stock y sin precio", stock_sin_precio, False,
            "Existencia valorizada a S/ 0",
            "Todo lo que lo lleve cuesta cero: recetas, consumo y ajuste.",
            "Stock > 0 y precio promedio del área = 0.",
            "Si es una preparación, que salga de una orden de producción; si se "
            "compra, revisar la factura que no lo cargó.",
            "", ("Producto", "Área", "Stock"), "area"),
    Control("s4", "stock", "Activo y sin vida", activo_sin_vida, False,
            "Producto activo sin stock, sin movimiento y sin compra en 12 meses",
            "No cuesta plata pero ensucia: sale en buscadores, en las hojas de "
            "conteo y en los requerimientos, y es por donde se carga «con el "
            "código del otro».",
            "Producto activo de mercadería, stock 0 en todas sus áreas, sin "
            "kardex (salvo conteos) ni compras en 365 días.",
            "Desactivarlo en el maestro del Almacén (no borrarlo).",
            "", ("Producto", "Habilitado en", "Último mov."), None),
    Control("s5", "stock", "Servicios que acumulan stock", servicio_con_stock, True,
            "Servicios y gastos con existencia, como si fueran mercadería",
            "Un servicio no se cuenta, así que nunca se da de baja y su «stock» "
            "crece cada mes. Por eso Stock e Inventario los saca (regla #598).",
            "TIPO PRODUCTO = SERVICIO y stock ≠ 0.",
            "Darlos de baja con una nota de consumo cada mes, o configurarlos "
            "sin control de stock.",
            "Stock e Inventario, fila «Inactivos y servicios»",
            ("Producto", "Área", "Stock"), "area"),
    Control("s6", "stock", "Unidad distinta y factor 1", unidad_sin_factor, False,
            "Unidad de entrada distinta de la de salida, y factor 1",
            "Si entra en kilos y sale en gramos, el factor tiene que ser 1000: "
            "con 1, una receta de 200 g descarga 200 kg.",
            "Producto activo con UNIDAD KARDEX ≠ UNIDAD SALIDA y FACTOR = 1.",
            "Poner el factor correcto y revisar las recetas que lo usan.",
            "", ("Producto", "", "Unidades"), None),
    Control("s7", "stock", "Habilitado en un área que no lo usa", habilitado_sin_uso, False,
            "Habilitado donde no tiene stock ni movimiento en 180 días, "
            "mientras se mueve en otra área",
            "El enlace sobra: infla la hoja de conteo del área y deja pedir o "
            "descargar el producto donde no corresponde, que es un origen de "
            "los negativos.",
            "Habilitado en el área (COMPARTIDO), stock 0 ahí, sin kardex en esa "
            "área en 180 días y con kardex en otra.",
            "Deshabilitar el producto EN ESA ÁREA, sin desactivarlo. Si se "
            "concentra en pocas áreas, decidir antes qué se habilita por defecto.",
            "", ("Producto", "Área", "Se mueve en"), "area"),
    Control("r1", "recetas", "Recetas base que no se mueven", receta_base_quieta, False,
            "El producto de la receta base no se movió en 180 días",
            "Una receta base viva o se produce o la descarga un plato. Si nadie "
            "la toca, el plato que la llevaba salió, o la cocina la hace con "
            "otro código.",
            "Receta base y artículo activos; el producto que crea, sin kardex "
            "(salvo conteos) en 180 días.",
            "Desactivar las que ya no se hacen; si se hacen, ver con qué código "
            "se descargan.",
            "", ("Receta base", "Área", "Último mov."), "area"),
    Control("r2", "recetas", "Receta con insumo de baja", receta_con_insumo_de_baja, True,
            "Una receta viva lleva un insumo inactivo, o uno no habilitado en "
            "el área de descargo",
            "El POS descarga igual: el insumo se va a negativo donde nadie lo "
            "pide y el costo del plato queda con un precio viejo.",
            "Línea de receta de un plato activo con el insumo inactivo o no "
            "habilitado (COMPARTIDO) en su SUBALM INS, y líneas de recetas base "
            "activas con el insumo inactivo. S/ = venta de 90 días del plato.",
            "Cambiar la línea al código vigente, o habilitar el insumo en el área.",
            "", ("Plato · insumo", "Área", "Problema"), "area"),
    Control("r3", "recetas", "Factor cambiado sin tocar recetas", factor_sin_tocar_recetas, True,
            "Se cambió el factor o la unidad y ninguna receta que lo lleva se "
            "editó después",
            "El caso de la Berenjena (factor 1000 → 1, regla #658): la receta "
            "guarda la cantidad en la unidad de salida, y si esa unidad cambia "
            "y la receta no, el plato descarga y cuesta otra cosa.",
            "Último cambio de factor o unidad de cada artículo (auditoría del "
            "POS) y una receta viva que lo lleva con fecha anterior al cambio.",
            "Revisar la cantidad en cada receta que lo usa.",
            "Recetas › Costo Carta (◆ en la ficha)", ("Artículo", "Recetas", "Cambio"),
            "quien"),
    Control("r4", "recetas", "Costo de receta fuera de rango", costo_fuera_de_rango, False,
            "Plato activo a costo 0, o por encima del 60 % de su precio neto",
            "Un plato muy por encima del 100 % no existe: es una cantidad o un "
            "factor mal. Los vinos en botella pasan del 60 % por cómo se les "
            "pone precio, no por error.",
            "Costo de carta ÷ precio neto de salón > 60 %, o costo 0, para "
            "platos activos con precio de S/ 1 o más. Sin Venta Interna.",
            "Abrir el plato en Costo Carta › Simular para ver qué línea lo dispara.",
            "Recetas › Costo Carta", ("Plato", "Grupo", "% costo"), "area"),
    Control("r5", "recetas", "Receta base de un artículo de baja",
            receta_base_de_articulo_inactivo, False,
            "Receta base activa de un artículo que está dado de baja",
            "La receta sigue viva, pero el producto que crea ya no existe en el "
            "maestro: si un plato la usa, descarga a un código inactivo.",
            "Receta base activa y su artículo inactivo.",
            "Desactivar la receta, o reactivar el artículo si se sigue haciendo.",
            "", ("Receta base", "Área", "Desde"), "area"),
    Control("c1", "carta", "Platos activos que no se venden", plato_sin_venta, False,
            "Plato activo sin una venta en 90 días",
            "Siguen en la carta del POS, en el costeo y en la ingeniería de "
            "menú. Salieron de la carta física o son de temporada.",
            "Ítem de venta activo (sin los «no aplica») cuya última venta tiene "
            "más de 90 días, o nunca se vendió.",
            "Desactivar en el POS lo que salió de carta.",
            "", ("Plato", "Grupo", "Última venta"), "area"),
    Control("c2", "carta", "Se vende y no descarga nada", vende_sin_descargo, True,
            "Se vendió en 90 días y no descarga nada",
            "Lo vendido no baja del stock: al contar, sus insumos faltan sin "
            "explicación y el FoodCost sale más bajo de lo real.",
            "Plato vendido en 90 días SIN ENLACE, o con receta o enlace a costo "
            "0, en la carta costeada. S/ = su venta.",
            "Cargar la receta o el enlace de descargo en el POS.",
            "", ("Plato", "Grupo", "Vendido"), "area"),
    Control("c3", "carta", "Se descarga donde no entra", descarga_donde_no_entra, True,
            "El descargo de ventas bajó un producto en un área donde nunca entra",
            "El plato descuenta desde el área equivocada: esa área queda en "
            "negativo y la que recibe el producto sobra al contar.",
            "Producto × área con descargo de ventas (95) en 90 días y ninguna "
            "entrada en esa área en 180.",
            "Cambiar el área de descargo del plato en el POS.",
            "Ajuste › Análisis de diferencias («Se vende desde otra área»)",
            ("Producto", "Área", "Descontado"), "area"),
    Control("c4", "carta", "Combo que el sistema no reconoce", combo_no_reconocido, True,
            "Combo vendido que no está en la lista de combos de la app",
            "Uno solo que falte multiplica su costo por la cantidad (regla #542).",
            "Línea vendida con ES COMBO = 1 fuera de definicion_venta.COMBOS.",
            "Sumar el código a definicion_venta.COMBOS y subir su VERSION.",
            "", ("Combo", "", "Vendido"), None),
    Control("p1", "compras", "Se compra y nada lo usa", comprado_sin_uso, False,
            "Comprado en 90 días y sin ninguna salida de uso en 180, en ninguna área",
            "Si entra y no lo saca ni una receta, ni una producción, ni un "
            "porcionamiento, ni una nota, sólo puede salir como faltante. No "
            "cuenta los insumos de operación, que se consumen al contar.",
            "Mercadería con compras en 90 días y sin kardex 94, 95, 96 ni 98 en "
            "180, sin la familia COSTOS PRODUCCION.",
            "Sumarlo a la receta que lo usa, o hacer la nota de salida si es de "
            "uso del área.",
            "", ("Producto", "Familia", "Comprado"), "area"),
    Control("p2", "compras", "Mercadería sin kardex", mercaderia_sin_kardex, False,
            "Comprado como servicio en una familia de mercadería",
            "No entra al stock: no se cuenta, no se descarga y su costo no llega "
            "a ninguna receta.",
            "Producto de tipo SERVICIO comprado en 90 días en una familia con 80 % "
            "o más de mercadería.",
            "Cambiar el tipo del producto en el maestro a mercadería.",
            "", ("Producto", "Familia", "Tipo"), "area"),
    Control("p3", "compras", "Mismo producto con dos códigos", dos_codigos, False,
            "Dos códigos activos con el mismo nombre y unidad",
            "Se compra con uno y se descarga con el otro: uno sobra y el otro "
            "falta al contar.",
            "Nombre sin tildes, puntos ni espacios dobles, misma unidad, los dos "
            "activos.",
            "Unificar: desactivar el que no se compra.",
            "", ("Producto", "", "Códigos"), None),
    Control("m1", "raros", "Cambios de factor o unidad", cambios_de_factor, False,
            "Cambios de factor o de unidad de artículos que lleva una receta "
            "viva, en el último año",
            "No son errores por sí mismos: es quién tocó el maestro y cuándo, "
            "para cruzarlo con los picos de costo.",
            "Auditoría del POS (Factor, Unidad de Kardex, Unidad de Salida) con "
            "un valor anterior, sobre artículos de una receta viva. Un cambio de "
            "varios campos a la vez es un caso.",
            "Mirar los que coinciden con un pico de costo del plato.",
            "Recetas › Costo Carta (◆ en la ficha)", ("Artículo", "Recetas", "Cambio"),
            "quien"),
    Control("m2", "raros", "Precio de costo editado a mano", precio_editado_a_mano, True,
            "Precio de costo escrito a mano a 2,5 veces lo que era, o a menos de 0,4",
            "El precio promedio lo calcula el Almacén; escribirlo a mano mueve el "
            "costo de todas las recetas que lo llevan.",
            "Auditoría del POS, campo «Precio de Costo», último año.",
            "Confirmar con quien lo cambió de dónde salió el precio.",
            "", ("Artículo", "", "Cambio"), "quien"),
    Control("m3", "raros", "Porcionamiento con merma rara", porcionamiento_raro, True,
            "Merma negativa, del 90 % o más, o fuera de lo normal del producto",
            "El costo de los cortes se reparte por peso: una merma mal "
            "registrada mueve el precio de todos (regla #647).",
            "Merma ÷ lo porcionado < 0 o ≥ 90 %, o a más de 2 rangos "
            "intercuartiles de los porcionamientos del último año del producto "
            "(con 8 o más). S/ = costo de lo que entró.",
            "Corregir los pesos del porcionamiento en el Almacén.",
            "Movimientos › Rendimiento («Peso por unidad raro»)",
            ("Producto", "Área", "Merma"), "quien"),
    Control("m4", "raros", "Compra a un precio raro", compra_precio_raro, False,
            "A 2,5 veces o a menos de 0,4 de su precio habitual, o con decimales "
            "en unidades",
            "Casi siempre es una carga mal hecha y no un alza (cajas cargadas en "
            "litros). El precio promedio la absorbe y se va a las recetas.",
            "La marca «revisar» de Compras › Producto (regla #653) sobre las "
            "compras de 90 días.",
            "Corregir la cantidad o la unidad del documento en el Almacén.",
            "Compras › Producto (marca «revisar»)", ("Producto", "Proveedor", "Cargado"),
            "area"),
    Control("m5", "raros", "Sobró sin que entrara nada", sobro_sin_entrar, False,
            "Sobró al contar algo que el sistema tenía en cero y sin entradas "
            "desde el conteo anterior",
            "Con el sistema en negativo, un sobrante es un descargo adelantado; "
            "en cero, la mercadería apareció: entró sin registrarse o se contó "
            "otro producto.",
            "Línea de ajuste de 90 días con sobrante, stock del sistema 0 y sin "
            "kardex de entrada en esa área desde el conteo anterior.",
            "Buscar la factura que no se ingresó, o el producto parecido que "
            "falta en la misma área.",
            "Ajuste › Análisis de diferencias («Sobró sin que entrara nada»)",
            ("Producto", "Área", "Sobrante"), "area"),
    Control("m6", "raros", "Factura en SUNAT sin ingresar", sunat_sin_ingresar, True,
            "Factura de mercadería que el proveedor declaró y el Almacén no tiene",
            "Mercadería que entró sin registrarse —y sobra al contar— o una "
            "compra que nadie conoce. Sólo mercadería: alquileres, tarjetas y "
            "bancos no entran al Almacén.",
            "Comprobante del SIRE «Solo SUNAT» de tipo Mercadería (regla #640), "
            "emitido en 90 días y hace más de 15, sin las facturas anuladas con "
            "una nota del mismo monto.",
            "Ingresarla con «Ingresar al Almacén» o averiguar quién la pidió.",
            "Documentos SUNAT › Cruce con SUNAT", ("Proveedor", "", "Emitida hace"),
            "nombre"),
    Control("m7", "raros", "Ventas que nunca se descargaron", venta_sin_descargar, True,
            "Días vendidos que ninguna corrida del Descargo de Ventas tomó",
            "El descargo se corre a mano, y la corrida de fin de mes llega hasta "
            "la mañana del día: el último día del mes no lo toma nadie. Lo "
            "vendido sigue en el sistema y al contar falta sin ser pérdida.",
            "Pedidos del último año que no caen en el rango de ninguna corrida "
            "de TLOG_DESCARGO, hasta el final de la última.",
            "Correr el Descargo de Ventas para esos días.",
            "Ajuste › Análisis de diferencias (aviso arriba de la lista)",
            ("Día", "", "Sin descargar"), None),
    Control("m8", "raros", "Notas de salida en lote", notas_en_lote, False,
            "15 o más notas de salida de un área registradas una tras otra",
            "No es falta en sí: una nota escrita de memoria no es el día de la "
            "merma, y es donde una baja puede tapar un faltante.",
            "Notas no anuladas de un área sin una pausa de 10 minutos entre "
            "ellas, de a 15 o más, en el último año.",
            "Pedir que las notas se registren el día que ocurren.",
            "Movimientos › Salidas (registro y proceso)", ("Lote", "Área", "Notas"),
            "area"),
    Control("m9", "raros", "Anulados y cortesías fuera de lo normal",
            anulados_y_cortesias, False,
            "Un día en que un usuario anuló —o un mesero dio en cortesía— 3 "
            "veces o más lo suyo",
            "Un plato anulado después de servido o una cortesía no autorizada "
            "salen de la cocina igual. Señal, no prueba: un error de comanda "
            "deja el mismo rastro.",
            "Por usuario: día con monto anulado (pedidos) o en cortesía (ventas, "
            "a precio carta) ≥ 3 × su mediana diaria y ≥ S/ 200, en 90 días.",
            "Revisar las comandas de esos días con el administrador.",
            "", ("Día", "", "× lo suyo"), "quien"),
)
POR_ID = {c.id: c for c in CONTROLES}


def calcular(t, hoy, solo=None):
    """`{id: casos}` de cada control (o de los de `solo`). Un control que
    falla devuelve la excepción en vez de sus casos: uno roto no tapa a los
    demás."""
    hoy = pd.Timestamp(hoy).normalize()
    out = {}
    for c in CONTROLES:
        if solo and c.id not in solo:
            continue
        try:
            out[c.id] = c.fn(t, hoy)
        except Exception as e:  # noqa: BLE001 — se informa, no se esconde
            out[c.id] = e
    return out


ROJO, AMBAR, VERDE, FALLO = "rojo", "ambar", "verde", "fallo"


def estado(c, casos):
    """El color de un control: falló, sin casos (verde), o con casos (rojo
    si es `grave`, ámbar si no)."""
    if not isinstance(casos, pd.DataFrame):
        return FALLO
    if casos.empty:
        return VERDE
    return ROJO if c.grave else AMBAR


def concentra(c, casos, n=2):
    """Dónde se concentran los casos: los `n` valores de `c.agrupar` con más
    casos, «Cocina 167 · Barra 40». "" si el control no agrupa."""
    if not c.agrupar or not isinstance(casos, pd.DataFrame) or casos.empty:
        return ""
    g = _txt(casos[c.agrupar]).replace("", "—").value_counts().head(n)
    return " · ".join(f"{k} {v:,}" for k, v in g.items())


def resumen(resultado):
    """Una fila por control de `resultado` (lo de `calcular`), en el orden
    de `CONTROLES`: id, dominio, nombre, estado, casos, soles, concentra.
    Un control que falló lleva su error en `concentra`."""
    filas = []
    for c in CONTROLES:
        if c.id not in resultado:
            continue
        r = resultado[c.id]
        ok = isinstance(r, pd.DataFrame)
        filas.append({
            "id": c.id, "dominio": c.dominio, "nombre": c.nombre,
            "estado": estado(c, r), "casos": len(r) if ok else 0,
            "soles": r["soles"].sum(min_count=1) if ok else np.nan,
            "concentra": concentra(c, r) if ok else str(r),
        })
    return pd.DataFrame(filas, columns=["id", "dominio", "nombre", "estado",
                                        "casos", "soles", "concentra"])
