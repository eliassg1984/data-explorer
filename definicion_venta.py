"""
definicion_venta — QUÉ es venta en esta app, en un solo lugar (regla #524).

Hasta el 2026-09-24 cada vista de Ventas sumaba `VENTA ITEM DDOCUMENTO` a
su manera: el Resumen sacaba cortesías y anulados, las otras nueve vistas y
los KPIs del rail los sumaban (unos S/ 16.000 más al mes), y nadie restaba
las notas de crédito. El mismo día salía con dos montos según la vista.

LA DEFINICIÓN — cuadrada al céntimo contra el sistema de caja (INFOREST,
`MDOCUMENTO`), día por día, del 25 ago al 23 set 2026:

    Venta = facturas y boletas PAGADAS o POR COBRAR − notas de crédito
          = precio de carta − descuentos − notas de crédito

- **Por cobrar es venta.** El estado 03 del POS («C.POR COBRAR» en el
  parquet) es un consumo facturado que se cobra después. Leerlo como
  anulado inventaba una diferencia de S/ 13.900 al mes.
- **Cortesías**: comprobante tipo CORTESIA, valorizado a PRECIO DE CARTA.
  No es venta: es lo que se regaló, y se muestra aparte (con su costo).
- **Anulados**: estado ANULADO. No son venta ni cortesía.
- **Notas de crédito**: se RESTAN EN SU FECHA, como en el Registro de
  Ventas de SUNAT. No están en `MDOCUMENTO` y en el parquet llegan como un
  documento SIN ítems; el anulado lleva el número de la nota en `NOTA
  CREDITO` y su fecha en `FECH REG NC`. Son 22 en el histórico (S/ 28.649),
  todas por el total, y 17 con el pedido reemitido: el canje de boleta por
  factura. Sin restarlas, esa venta —y sus clientes y sus platos— se cuenta
  dos veces.
- **Costo** de una línea = `PRECIO COSTO` × cantidad: el parquet trae el
  costo POR UNIDAD (el Lomo a 24,17 la unidad, vendido por 2). Sumarlo
  suelto, como hacían cuatro vistas, daba un FoodCost de 24 % donde era
  29 % (del 1 al 23 de septiembre de 2026; el 34,5 % que se midió ese día
  traía los combos inflados). `preparar` deja la cuenta hecha en
  `COSTO VENTA`, en negativo en las notas de crédito.
- **Menos en los COMBOS** (regla #542): ahí `PRECIO COSTO` ya es el costo
  de la LÍNEA entera —lo que se sirvió de cada plato del combo, sumado—, y
  multiplicarlo por la cantidad contaba 13 veces una línea de 13
  Degustaciones. `preparar` lo devuelve a unitario antes de todo lo demás,
  así que `PRECIO COSTO` dice lo mismo en todas las filas.
- **Clientes** = `CANT PAX`, que el POS llena con los ADULTOS
  (`MPEDIDO.nAdulto`); los niños (`nNino`) no vienen en la consulta. Por
  decisión del usuario (2026-09-24) se queda así por ahora.

CÓMO SE APLICA. `data.cargar_rango` llama a `preparar()` al bajar
`ventas.parquet`, así que TODO consumidor —las vistas, los KPIs del rail,
el asistente IA, el Año Pasado y el Mapa por hora que cargan sus propios
tramos— recibe el df con la columna `CLASE VENTA` y con cada nota de
crédito convertida en ítems NEGATIVOS fechados el día de la nota. Una
vista que suma venta filtra con `es_venta()`; una que cuenta clientes o
documentos usa `pax_por()` / `documentos_por()`, que restan los de las
notas en vez de contarlos como uno más.

Módulo puro: pandas y nada más. Sin streamlit ni `graficos/` porque lo
consumen los dos lados — `data.py` y las vistas —, igual que `cortes.py`.
"""

import numpy as np
import pandas as pd

VERSION = 3
"""Entra en la clave de la caché de `data.py`. Subirla al cambiar la
definición: la caché vive en disco y, sin esto, seguiría sirviendo el df
preparado con la regla anterior hasta que cambie el parquet.

No es teórico: la 2 nació el mismo día que la 1, al sumar `COSTO VENTA` —
la caché local tenía el df de la 1, sin esa columna, y «Ranking & FoodCost»
siguió mostrando el FoodCost con el costo unitario. La 3 es el costo de
los combos (regla #542)."""

CLASE = "CLASE VENTA"
VENTA = "Venta"
NOTA_CREDITO = "Nota de crédito"
CORTESIA = "Cortesía"
ANULADO = "Anulado"
CLASES_VENTA = (VENTA, NOTA_CREDITO)

# ── Columnas del parquet, en MAYÚSCULAS como vienen de R2 ────────────────
# Se buscan sin distinguir mayúsculas ni `_` (el demo las trae «Fec Reg
# Documento»). Las que faltan se saltean: sin ellas no hay nota que armar.
FECHA = "FEC REG DOCUMENTO"
COD_TIPO = "COD TIPO DOC"
TIPO = "TIPO DOC"
ESTADO = "ESTADO DOCUMENTO"
MOTIVO_CORTESIA = "MOTIVO CORTESIA"
NUMERO = "NUMERO DOCUMENTO"
LLAVE_DOC = "LLAVE LOCAL DOCUMENTO"
LLAVE_ITEM = "LLAVE LOCAL DOCUMENTO ITEM"
LLAVE_PAGO = "LLAVE LOCAL DOCUMENTO CORRELATIVO PAGO"
NC_NUMERO = "NOTA CREDITO"
NC_FECHA = "FECH REG NC"
NC_TOTAL = "TOTAL NC"          # en el parquet es « TOTAL NC», con espacio
TOTAL_DOC = "TOTAL MDOCUMENTO"
PAX = "CANT PAX"
CANTIDAD = "CANTIDAD ITEM DDOCUMENTO"
VENTA_ITEM = "VENTA ITEM DDOCUMENTO"
CARTA_UNIT = "PRECIO OFICIAL ITEM DDOCUMENTO"
DESCUENTO_ITEM = "DESCUENTO ITEM DDOCUMENTO"
COSTO_UNIT = "PRECIO COSTO"
COSTO = "COSTO VENTA"
"""La columna que agrega `preparar`: el costo de la LÍNEA (unitario × cantidad)."""
PRODUCTO = "COD ITEM VENTA DDOCUMENTO"
ES_COMBO = "ES COMBO"
"""La marca de combo del POS, si la consulta del Sheet la trae
(`CAST(INFOREST.DBO.DPEDIDO.lCombinacion AS int) AS 'ES COMBO'`). Hoy no la
trae: con ella, `COMBOS` deja de hacer falta y un combo nuevo no se escapa.

La de la LÍNEA del pedido y no la del producto (`TPRODUCTO.lCombinacion`):
es la misma que decide, en esa consulta, si `PRECIO COSTO` sale de CPEDIDO
(costo de línea) o de `DPEDIDO.nInsumo` (unitario). En 2025-26 difieren en
una línea, y con la del producto esa se dividiría sin serlo."""

COMBOS = frozenset({
    "0000314", "0000423", "0000424", "0000425", "0000492", "0000598",
    "0000652", "0000740", "0000843", "0000854", "0000988", "0000999",
    "0001000", "0001003", "0001041", "0001042", "0001043", "0001044",
    "0001075", "0001090", "0001123", "0001128", "0001130", "0001135",
    "0001136", "0001142", "0001147", "0001157", "0001180", "0001202",
    "0001206", "0001207", "0001208", "0001219", "0001224", "0001231",
    "0001259", "0001268", "0001269", "0001331", "0001356", "0001363",
    "0001490", "0001521", "0001536", "0001545", "0001546", "0001548",
    "0001568", "0001595", "0001605", "0001629", "0001643", "0001650",
    "0001682",
})
"""Los productos que el POS arma como COMBO (`INFOREST.DBO.TPRODUCTO.
lCombinacion = 1`) al 2026-09-26: la Degustación, las parrillas, los menús
de evento. En ellos `PRECIO COSTO` es el costo de la LÍNEA (regla #542).

Es una FOTO del POS y se queda vieja: salen menús de evento casi cada mes
(Echecopar y Cocina de Fuegos en agosto de 2026, Sept2026 el 24 de
septiembre). Un combo que falte vuelve a contar su costo por la cantidad,
sin ningún error. `herramientas/cuadrar_ventas.py` lo compara con el POS y
nombra a los que falten; el arreglo de fondo es la columna `ES_COMBO`."""

# Montos de LÍNEA: la nota los invierte. Los precios UNITARIOS (oficial,
# costo, neto, venta) no se tocan — carta y costo salen de unitario ×
# cantidad, y con la cantidad en negativo ya restan.
_MONTOS_LINEA = (
    VENTA_ITEM, "NETO TOTAL ITEM DDOCUMENTO", DESCUENTO_ITEM,
    "IGV ITEM DDOCUMENTO", "RECARGO ITEM DDCOUMENTO", CANTIDAD,
)
# Del PAGO del documento anulado: la nota no paga ni deja propina.
_DEL_PAGO = (
    "FECHA REGISTRO PAGO DOC", "CORRELATIVO PAGO", "NOMBRE TIPO PAGO",
    "MONTO TIPO PAGO DOC", "MONTO PROPINA", "USUARIO REG PAGO DOC",
)
# Cabecera: la nota trae la suya (en negativo).
_CABECERA = (LLAVE_DOC, COD_TIPO, TIPO, ESTADO, TOTAL_DOC,
             "NETO MDOCUMENTO", "IGV MDOCUMENTO", "RECARGO MDOCUMENTO")
_REFERENCIA_NC = (NC_NUMERO, NC_FECHA, "NETO NC", NC_TOTAL, "FECH REG NC")

COLUMNAS = (
    FECHA, COD_TIPO, TIPO, ESTADO, MOTIVO_CORTESIA, NUMERO, LLAVE_DOC,
    LLAVE_ITEM, LLAVE_PAGO, NC_NUMERO, NC_FECHA, NC_TOTAL, TOTAL_DOC, PAX,
    CARTA_UNIT, COSTO_UNIT, PRODUCTO, ES_COMBO, *_MONTOS_LINEA, *_DEL_PAGO,
    *_CABECERA, *_REFERENCIA_NC,
)
"""Todo lo que `preparar()` lee. Quien quiera la definición sin bajar el
parquet entero (los KPIs del rail) trae estas y las suyas."""

DEFINICION = (
    "Venta = facturas y boletas pagadas o por cobrar, menos notas de "
    "crédito. Es lo mismo que precio de carta menos descuentos. Las "
    "cortesías (a precio de carta) y los anulados no son venta; las notas "
    "de crédito restan el día que se emiten, como en el Registro de Ventas "
    "de SUNAT. El costo es el de receta por la cantidad vendida (en un "
    "combo, lo que se sirvió de cada plato). Clientes cuenta adultos, como "
    "el POS en «pax».")


def _norm(nombre):
    return str(nombre).strip().upper().replace("_", " ")


def columna(df, nombre):
    """El nombre REAL de la columna `nombre` en `df`, o None."""
    buscado = _norm(nombre)
    for c in df.columns:
        if _norm(c) == buscado:
            return c
    return None


def _texto(s):
    return s.astype("string").str.strip().str.upper().fillna("")


def _clasificar(df, cols):
    """`CLASE VENTA` de cada fila del parquet, sin las notas espejadas."""
    clase = pd.Series(VENTA, index=df.index, dtype=object)
    if cols[TIPO]:
        tipo = _texto(df[cols[TIPO]])
        clase[tipo == "CORTESIA"] = CORTESIA
        clase[tipo.str.startswith("NC ")] = NOTA_CREDITO
    if cols[MOTIVO_CORTESIA]:
        clase[_texto(df[cols[MOTIVO_CORTESIA]]) != ""] = CORTESIA
    if cols[NUMERO] and cols[NC_NUMERO]:
        # Un documento cuyo número figura como nota de crédito de otro ES la
        # nota, se llame como se llame su tipo.
        refs = set(_texto(df[cols[NC_NUMERO]])) - {""}
        if refs:
            clase[_texto(df[cols[NUMERO]]).isin(refs)] = NOTA_CREDITO
    if cols[ESTADO]:
        clase[_texto(df[cols[ESTADO]]) == "ANULADO"] = ANULADO
    return clase


def es_combo(df, cols=None):
    """Máscara de las líneas de COMBO: por la marca del POS si el parquet
    la trae (`ES_COMBO`), si no por el código del producto (`COMBOS`)."""
    cols = cols or {n: columna(df, n) for n in (ES_COMBO, PRODUCTO)}
    if cols.get(ES_COMBO):
        s = df[cols[ES_COMBO]]
        # Un `bit` del POS con vacíos (las notas de crédito no traen línea
        # de pedido) llega de DuckDB como `boolean` de pandas, que revienta
        # con `fillna(0)`: la carga de Ventas entera se caía. Por `object`,
        # cualquier forma de la marca sale en números.
        num = pd.to_numeric(s.astype(object), errors="coerce")
        return ((num.fillna(0) != 0)
                | _texto(s).isin(("TRUE", "SI", "SÍ", "S")))
    if cols.get(PRODUCTO):
        return _texto(df[cols[PRODUCTO]]).isin(COMBOS)
    return pd.Series(False, index=df.index)


def _costo_unitario(df, cols):
    """`PRECIO COSTO` por UNIDAD en todas las filas (regla #542).

    En un combo el extractor lo llena con el costo de la LÍNEA DE PEDIDO
    entera: Σ `CPEDIDO.nCantidad × CPEDIDO.nInsumo`, lo servido de cada
    plato del combo (el POS deja `DPEDIDO.nInsumo` en 0). Se divide por la
    cantidad del comprobante, que ES la de la línea de pedido: el POS nunca
    reparte una línea entre comprobantes — una cuenta dividida separa
    líneas enteras, y un canje repite la línea entera en los dos (medido:
    196.241 líneas de 2025-26, ni una con otra cantidad).

    Va ANTES de espejar las notas de crédito: el espejo copia el unitario
    y niega la cantidad, así el costo de la nota sale negativo solo. Una
    cantidad en 0 o vacía deja el costo como vino (la línea cuesta 0 igual)."""
    c_costo, c_cant = cols[COSTO_UNIT], cols[CANTIDAD]
    if not (c_costo and c_cant):
        return df
    combo = es_combo(df, cols)
    if not combo.any():
        return df
    costo = pd.to_numeric(df[c_costo], errors="coerce")
    cant = pd.to_numeric(df[c_cant], errors="coerce")
    dividir = combo & cant.notna() & (cant != 0)
    # Columna nueva y no `.loc[...] =`: así el df que recibió `preparar`
    # no se entera, con copy-on-write o sin él.
    df[c_costo] = costo.where(~dividir, costo / cant)
    return df


def _espejo_de_notas(df, cols, es_nota):
    """Los ítems de cada documento anulado por una nota de crédito, en
    NEGATIVO y con la fecha, el número y la cabecera de la nota.

    Devuelve (espejo, números de nota espejados). Una nota por menos que el
    total (no hay ninguna en el histórico, pero el POS las permite) escala
    montos y cantidades por la proporción y no toca los clientes: la mesa
    vino igual."""
    anulado = _texto(df[cols[NC_NUMERO]])
    orig = df[anulado != ""]
    if orig.empty:
        return None, set()
    if cols[LLAVE_ITEM]:
        orig = orig.drop_duplicates(subset=[cols[LLAVE_ITEM]])
    num_nc = _texto(orig[cols[NC_NUMERO]])

    espejo = orig.copy()
    espejo[cols[FECHA]] = pd.to_datetime(orig[cols[NC_FECHA]], errors="coerce")
    if cols[NUMERO]:
        espejo[cols[NUMERO]] = num_nc.to_numpy()

    # La cabecera de la nota, sacada de su propia fila (sin ítems).
    notas = df[es_nota]
    if cols[NUMERO] and not notas.empty:
        notas = notas.assign(_num=_texto(notas[cols[NUMERO]]).to_numpy())
        notas = notas.drop_duplicates("_num").set_index("_num")
        for nombre in _CABECERA:
            c = cols[nombre]
            if c:
                espejo[c] = num_nc.map(notas[c]).fillna(orig[c]).to_numpy()
    if cols[LLAVE_DOC]:
        llave_nc = espejo[cols[LLAVE_DOC]].astype("string").fillna(
            "NC " + num_nc)
    else:
        llave_nc = "NC " + num_nc

    factor = pd.Series(1.0, index=orig.index)
    if cols[NC_TOTAL] and cols[TOTAL_DOC]:
        t_nc = pd.to_numeric(orig[cols[NC_TOTAL]], errors="coerce").abs()
        t_doc = pd.to_numeric(orig[cols[TOTAL_DOC]], errors="coerce").abs()
        f = (t_nc / t_doc.replace(0, np.nan)).clip(0, 1)
        factor = f.fillna(1.0)
    for nombre in _MONTOS_LINEA:
        c = cols[nombre]
        if c:
            espejo[c] = (-pd.to_numeric(orig[c], errors="coerce")
                         * factor).to_numpy()
    if cols[PAX]:
        pax = pd.to_numeric(orig[cols[PAX]], errors="coerce")
        espejo[cols[PAX]] = (-pax).where(factor >= 0.999, 0.0).to_numpy()
    if cols[LLAVE_ITEM]:
        espejo[cols[LLAVE_ITEM]] = (llave_nc + "|"
                                    + orig[cols[LLAVE_ITEM]].astype("string"))
    if cols[LLAVE_PAGO]:
        espejo[cols[LLAVE_PAGO]] = llave_nc + "|NC"
    vacio = np.zeros(len(espejo), dtype=bool)
    for nombre in _DEL_PAGO + _REFERENCIA_NC:
        c = cols[nombre]
        if c:
            # `where(False)` y no `= np.nan`: vacía CONSERVANDO el tipo. Un
            # NaN suelto vuelve float a una columna de fechas, y al
            # juntarla con las demás filas queda `object` — y ahí se rompe
            # cualquier `.dt` de más adelante.
            espejo[c] = espejo[c].where(vacio)
    espejo[CLASE] = NOTA_CREDITO
    espejo = espejo[espejo[cols[FECHA]].notna()]
    return espejo, set(num_nc)


def _nota_sin_items(filas, cols):
    """Una nota cuyo documento anulado no vino en el df (no debería pasar:
    `data.cargar_rango` lo trae aunque caiga fuera del rango) resta al
    menos su MONTO: la venta sale del total de su cabecera, sin platos ni
    clientes."""
    filas = filas.copy()
    total = (pd.to_numeric(filas[cols[TOTAL_DOC]], errors="coerce")
             if cols[TOTAL_DOC] else pd.Series(0.0, index=filas.index))
    total = -total.abs()
    if cols[VENTA_ITEM]:
        filas[cols[VENTA_ITEM]] = total
    if cols[CARTA_UNIT]:
        filas[cols[CARTA_UNIT]] = np.nan
    for nombre in (CANTIDAD, PAX):
        if cols[nombre]:
            filas[cols[nombre]] = 0.0
    if cols[LLAVE_ITEM] and cols[LLAVE_DOC]:
        filas[cols[LLAVE_ITEM]] = (filas[cols[LLAVE_DOC]].astype("string")
                                   + "|NC")
    return filas


def preparar(df, ini=None, fin=None):
    """El df de `ventas.parquet` con la definición de venta aplicada.

    - Agrega `CLASE VENTA`: Venta, Nota de crédito, Cortesía o Anulado.
    - Cada nota de crédito deja de ser un documento sin ítems y pasa a ser
      los ítems del documento que anula, en negativo y en SU fecha.
    - Agrega `COSTO VENTA`: costo unitario × cantidad de cada línea. En los
      combos, antes, devuelve `PRECIO COSTO` a unitario (`_costo_unitario`).
    - Con `ini`/`fin` (fechas, inclusive) se queda sólo con lo que cae en
      el rango: el loader trae también los documentos anulados por una
      nota del rango aunque sean de antes, y acá se van después de
      espejarlos.

    No toca el df que recibe. Sin las columnas de la nota (el demo, un
    parquet viejo) sólo clasifica."""
    if df is None:
        return df
    cols = {n: columna(df, n) for n in COLUMNAS}
    out = df.assign(**{CLASE: _clasificar(df, cols)})
    out = _costo_unitario(out, cols)

    if cols[NC_NUMERO] and cols[NC_FECHA] and cols[FECHA] and not out.empty:
        es_nota = out[CLASE] == NOTA_CREDITO
        espejo, espejadas = _espejo_de_notas(out, cols, es_nota)
        if espejadas and cols[NUMERO]:
            es_nota_espejada = es_nota & _texto(out[cols[NUMERO]]).isin(
                espejadas)
        else:
            es_nota_espejada = pd.Series(False, index=out.index)
        sueltas = es_nota & ~es_nota_espejada
        partes = [out[~es_nota]]
        if sueltas.any():
            partes.append(_nota_sin_items(out[sueltas], cols))
        if espejo is not None and not espejo.empty:
            partes.append(espejo)
        out = pd.concat(partes, ignore_index=True)

    if cols[COSTO_UNIT] and cols[CANTIDAD]:
        out[COSTO] = (pd.to_numeric(out[cols[COSTO_UNIT]], errors="coerce")
                      * pd.to_numeric(out[cols[CANTIDAD]], errors="coerce"))

    if (ini is not None or fin is not None) and cols[FECHA]:
        f = pd.to_datetime(out[cols[FECHA]], errors="coerce").dt.normalize()
        m = f.notna()
        if ini is not None:
            m &= f >= pd.Timestamp(ini)
        if fin is not None:
            m &= f <= pd.Timestamp(fin)
        out = out[m].reset_index(drop=True)
    return out


# ── Lo que usan las vistas ───────────────────────────────────────────────

def es_venta(df):
    """Máscara de las filas que SON venta (incluidas las notas, que restan).
    Sin `CLASE VENTA` (un df que no pasó por `preparar`) todo es venta."""
    c = columna(df, CLASE)
    if c is None:
        return pd.Series(True, index=df.index)
    return df[c].isin(CLASES_VENTA)


def solo_venta(df):
    """`df` sin cortesías ni anulados."""
    if df is None or df.empty:
        return df
    m = es_venta(df)
    return df if m.all() else df[m]


def pax_por(df, ped, pax, doc=None, por=None):
    """Clientes: un valor por PEDIDO (el pax se repite en cada ítem), y el de
    una nota de crédito RESTA — sin dejar de contar a la mesa que sí vino.

    La regla, por pedido y dentro de cada grupo de `por`, cuenta
    COMPROBANTES: los que suman (pax > 0) contra las notas (pax < 0, que
    `preparar` deja en negativo). Si quedan más comprobantes que notas, la
    mesa cuenta su pax; si se empatan, cero; si hay más notas, resta.

        cuenta dividida (dos boletas, un pedido) ...... 2 − 0 → 4
        canje: día de la boleta ....................... 1 − 0 → 4
        canje: día de la factura y la nota ............ 1 − 1 → 0
        canje: el rango entero ........................ 2 − 1 → 4
        devolución: día de la nota .................... 0 − 1 → −4

    Por día y por rango da lo mismo sumado. La regla de antes —el mayor pax
    positivo más el menor negativo— daba bien el día pero CERO en un rango
    que tuviera el canje entero: la boleta y la factura son el mismo pedido.

    `ped`, `pax` y `doc` son nombres de columna de `df`; `por`, una columna
    o lista de agrupación. Sin `doc` (o sin la columna) cae a la regla
    vieja. Devuelve una Series indexada por `por` o, sin `por`, un float."""
    por = [por] if isinstance(por, str) else list(por or [])
    if df is None or df.empty:
        return pd.Series(dtype=float) if por else 0.0
    p = pd.to_numeric(df[pax], errors="coerce").fillna(0.0)
    claves = por + [ped]
    if doc is not None and doc in df.columns:
        t = df[claves + [doc]].assign(_p=p)
        pos = t[t["_p"] > 0].groupby(claves, dropna=False).agg(
            n_pos=(doc, "nunique"), m_pos=("_p", "max"))
        neg = t[t["_p"] < 0].groupby(claves, dropna=False).agg(
            n_neg=(doc, "nunique"), m_neg=("_p", "min"))
        j = pos.join(neg, how="outer").fillna(0.0)
        dif = j["n_pos"] - j["n_neg"]
        neto = pd.Series(np.where(dif > 0, j["m_pos"],
                                  np.where(dif < 0, j["m_neg"], 0.0)),
                         index=j.index, dtype=float)
    else:
        t = df[claves].assign(_pos=p.clip(lower=0), _neg=p.clip(upper=0))
        g = t.groupby(claves, dropna=False).agg(
            _pos=("_pos", "max"), _neg=("_neg", "min"))
        neto = g["_pos"] + g["_neg"]
    if not por:
        return float(neto.sum())
    # Por NOMBRE de nivel y, con uno solo, como escalar: `level=[0]` devuelve
    # un índice de tuplas en unas versiones de pandas y plano en otras.
    return neto.groupby(level=por[0] if len(por) == 1 else por).sum()


def documentos_por(df, doc, clase, por=None):
    """Comprobantes distintos, con los de las notas de crédito RESTANDO: el
    canje de una boleta por factura es una sola venta, no tres documentos.
    Mismos argumentos que `pax_por` más `clase`, la columna con la
    `CLASE VENTA` de cada fila."""
    por = [por] if isinstance(por, str) else list(por or [])
    if df is None or df.empty:
        return pd.Series(dtype=float) if por else 0.0
    nota = df[clase] == NOTA_CREDITO
    if not por:
        return float(df.loc[~nota, doc].nunique() - df.loc[nota, doc].nunique())
    pos = df[~nota].groupby(por)[doc].nunique()
    neg = df[nota].groupby(por)[doc].nunique()
    return pos.sub(neg, fill_value=0)


def puente(df):
    """La conciliación de la venta, sobre un df de UN ítem por fila con
    todas las clases. Cada renglón sale de sumar `VENTA ITEM` (o carta y
    descuento) sobre su clase:

        precio de carta − descuentos = facturas y boletas   (← = el POS)
        facturas y boletas − notas de crédito = VENTA
        aparte: cortesías (a precio de carta) y anulados

    Devuelve un dict con esos montos (las notas en negativo), o {} si falta
    la columna de venta."""
    c_venta = columna(df, VENTA_ITEM)
    if df is None or df.empty or c_venta is None:
        return {}
    clase = (df[columna(df, CLASE)] if columna(df, CLASE)
             else pd.Series(VENTA, index=df.index))
    venta = pd.to_numeric(df[c_venta], errors="coerce").fillna(0.0)

    def _suma(serie, cual):
        return float(serie[clase == cual].sum())

    out = {
        "documentos": _suma(venta, VENTA),
        "notas_credito": _suma(venta, NOTA_CREDITO),
        "cortesias": _suma(venta, CORTESIA),
        "anulados": _suma(venta, ANULADO),
    }
    out["venta"] = out["documentos"] + out["notas_credito"]
    c_carta, c_cant = columna(df, CARTA_UNIT), columna(df, CANTIDAD)
    c_desc = columna(df, DESCUENTO_ITEM)
    if c_carta and c_cant and c_desc:
        carta = (pd.to_numeric(df[c_carta], errors="coerce").fillna(0.0)
                 * pd.to_numeric(df[c_cant], errors="coerce").fillna(0.0))
        desc = pd.to_numeric(df[c_desc], errors="coerce").fillna(0.0)
        out["carta"] = _suma(carta, VENTA)
        out["descuentos"] = _suma(desc, VENTA)
    return out


def resumir(df, kpis, col_ped=None, col_item=None):
    """Los KPIs del rail (`REPORTES[...]["kpis"]`) sobre el df PREPARADO,
    con esta definición: venta sin cortesías ni anulados y con las notas
    restando, clientes con `pax_por`. Un ítem una vez (regla #517).

    `kpis`: tuplas (etiqueta, columna, agregación) con agregación en
    {"sum", "sum_dedup", "count_distinct"}."""
    if df is None or df.empty:
        return {}
    d = solo_venta(df)
    c_item = columna(d, col_item) if col_item else None
    if c_item:
        llave = d[c_item]
        d = d[~(llave.duplicated() & llave.notna())]
    c_ped = columna(d, col_ped) if col_ped else None
    c_doc = columna(d, LLAVE_DOC)
    out = {}
    for kpi in kpis:
        etiqueta, nombre, agg = kpi[0], kpi[1], kpi[2]
        c = columna(d, nombre)
        if c is None:
            continue
        if agg == "sum_dedup" and c_ped:
            out[etiqueta] = pax_por(d, c_ped, c, doc=c_doc)
        elif agg == "count_distinct":
            out[etiqueta] = int(d[c].nunique())
        else:
            out[etiqueta] = float(pd.to_numeric(d[c], errors="coerce").sum())
    return out
