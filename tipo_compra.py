"""tipo_compra.py — QUÉ SE COMPRÓ en cada comprobante: Alimentos, Otros
bienes, Servicios o Financiero. Regla #640.

Lo usa la columna «Tipo» de «Documentos SUNAT». Puro pandas, sin Streamlit
ni red, como `definicion_compra.py`: lo vigila `test_tipo_compra.py`.

NI EL SIRE NI EL XML LO DICEN (medido el 2026-10-11)
----------------------------------------------------
El registro del SIRE tiene el casillero —`codBbss`, la «clasificación de
los bienes y servicios adquiridos»: 1 mercadería… 5 otros gastos—, pero lo
llena el COMPRADOR, y venía vacío en las 900 facturas de setiembre 2026. El
XML puede traer por línea el «código de producto SUNAT» (UNSPSC), y viene
en el 14,6 % de las 18.668 líneas: 264 de 325 emisores no lo ponen nunca.

Lo que sí sirve, en este ORDEN —el primero que contesta, gana—, medido
sobre las 13.843 facturas del SIRE que también están en el Almacén:

1. **Entidad financiera** (`es_entidad_financiera`, los tipos 30 y 42):
   va PRIMERO porque bancos, cajas y aseguradoras facturan SIN IGV — el
   BCP, 419 de sus 429 comprobantes — y la regla 4 los llamaría comida.
2. **El documento ya está en el Almacén**: su familia, que es la verdad.
3. **El proveedor**: lo que se le compró antes, si es ≥ 90 % de un tipo
   (`PUREZA_PROVEEDOR`). Acierta el 97,3 %, medido SIN contar el
   documento evaluado, que es lo que le pasa a un «Solo SUNAT».
4. **Factura toda exonerada de IGV** → Alimentos (verdura, fruta,
   pescado: el Apéndice I de la ley del IGV). Acierta el 98,3 % sola, pero
   va DESPUÉS del proveedor: en las 60 facturas donde los dos discrepan,
   el proveedor acierta el 95 % y la exoneración el 2 % (BBVA, una
   inmobiliaria, APDAYC: servicios exonerados).

Lo que se midió y NO entra: la marca «D» de detracción sola (2 de cada 3
son carne), la unidad «ZZ» del XML (el 72 % de esas líneas es comida) y
las señales del XML en general — código de detracción, tipo de operación,
UNSPSC aciertan, pero sobre lo de arriba suman 59 documentos (0,7 % de los
soles) a cambio de leer miles de XML de R2. Sin clasificar quedan ~1,8 % de
los soles: proveedores nuevos que facturan con IGV.
"""

import functools
import re
import unicodedata

import pandas as pd

from utils import _norm

VERSION = 1
"""Sube cuando cambia QUÉ tipo sale (las listas de abajo, el umbral, el
orden): va en la clave de la caché de la vista."""

ALIMENTOS = "Alimentos"
OTROS_BIENES = "Otros bienes"
SERVICIOS = "Servicios"
FINANCIERO = "Financiero"
TIPOS = (ALIMENTOS, OTROS_BIENES, SERVICIOS, FINANCIERO)

# ── El Almacén → tipo ──────────────────────────────────────────────────────
# Las familias del maestro de productos (`compras.parquet`, FAMILIA). Las
# tres de gasto mezclan bienes y servicios —COSTOS PRODUCCION trae el
# alquiler, la luz y la leña—, así que ahí decide la SUBFAMILIA.
FAMILIAS_ALIMENTOS = ("ALIMENTOS", "BEBIDAS CON ALCOHOL",
                      "BEBIDAS SIN ALCOHOL", "VINOS Y ESPUMANTES")
FAMILIAS_BIENES = ("ENVASES Y EMBALAJES",)
FAMILIAS_GASTO = ("COSTOS PRODUCCION", "GASTOS ADMINISTRATIVOS",
                  "GASTOS VENTAS")

SUBFAMILIAS_BIENES = (
    "Activos Menores 1/4 Uit", "Articulos De Botiquin",
    "Compra De Leña Y Carbón", "Gas Licuado", "Gastos De Adornos",
    "Menaje Cocina", "Menaje Salon", "Suministros De Limpieza",
    "Suministros Y Repuestos Varios", "Uniformes", "Utiles De Oficina",
)
"""Las subfamilias de las familias de gasto que son COSAS. Las demás son
servicios: alquiler, luz, agua (`Servicio De Agua`), mantenimiento,
movilidad, asesorías, comisiones, publicidad, copias. «Uniformes» es en su
mayoría mandiles y polos, con algún servicio de confección adentro."""

SUBFAMILIAS_ALIMENTOS = ("Consumo Para El Personal",)
"""Comida para el personal (bocaditos, vino) que el Almacén guarda en
GASTOS ADMINISTRATIVOS."""

_FAM_ALIM = {_norm(f) for f in FAMILIAS_ALIMENTOS}
_FAM_BIEN = {_norm(f) for f in FAMILIAS_BIENES}
_FAM_GASTO = {_norm(f) for f in FAMILIAS_GASTO}
_SUB_BIEN = {_norm(s) for s in SUBFAMILIAS_BIENES}
_SUB_ALIM = {_norm(s) for s in SUBFAMILIAS_ALIMENTOS}


def tipo_de_linea(familia, subfamilia):
    """El tipo de una línea del Almacén, o None si su familia no tiene
    regla. Una familia nueva NO cae en «Servicios» por descarte: queda sin
    tipo y el documento pasa a las reglas siguientes."""
    fam = _norm(familia or "")
    if fam in _FAM_ALIM:
        return ALIMENTOS
    if fam in _FAM_BIEN:
        return OTROS_BIENES
    if fam in _FAM_GASTO:
        sub = _norm(subfamilia or "")
        if sub in _SUB_BIEN:
            return OTROS_BIENES
        if sub in _SUB_ALIM:
            return ALIMENTOS
        return SERVICIOS
    return None


PUREZA_PROVEEDOR = 0.90
"""Qué parte de lo comprado a un proveedor tiene que ser de un tipo para
que sus documentos sin cargar hereden ese tipo. Medido contra el Almacén
(cada factura con el proveedor calculado SIN ella):

    umbral   facturas con tipo   acierto
     95 %          78,3 %        98,6 %
     90 %          92,3 %        97,2 %   ← las que suma aciertan el 91 %
     85 %          94,7 %        96,9 %   ← las que suma aciertan el 85 %

Con 95 % se quedaba afuera el supermercado (93 % comida, el resto
limpieza). El tooltip dice la parte, así que la duda se ve."""

# ── Entidades financieras ──────────────────────────────────────────────────
TIPOS_CDP_FINANCIEROS = {
    "30": "lo emite quien procesa los pagos con tarjeta",
    "42": "lo emite una tarjeta de crédito",
}
"""Tipos de comprobante (tabla 10 de SUNAT) que sólo emite el sistema
financiero: las comisiones de Niubiz o Expressnet (30) y los cargos de una
tarjeta (42)."""

_RAZON_FINANCIERA = re.compile(
    r"\b(BANCO|BANK|SCOTIABANK|INTERBANK|MIBANCO|CAJA (MUNICIPAL|RURAL)|"
    r"FINANCIERA|EDPYME|COOPERATIVA DE AHORRO|SEGUROS|REASEGUROS|DINERS|"
    r"MEDIOS DE PAGO)\b")


@functools.lru_cache(maxsize=4096)
def es_entidad_financiera(razon_social):
    """True si la razón social es la de un banco, caja, financiera,
    cooperativa de ahorro, aseguradora o procesador de tarjetas. En el
    historial del SIRE no marca a ningún proveedor que no lo sea.

    Con memoria: una tabla de 4.600 comprobantes repite ~300 razones
    sociales, y normalizar cada una costaba ~90 ms por corrida."""
    s = unicodedata.normalize("NFKD", str(razon_social or ""))
    s = s.encode("ascii", "ignore").decode().upper()
    return bool(_RAZON_FINANCIERA.search(s))


# ── Las dos tablas que salen del Almacén ───────────────────────────────────
def _con_tipo(d):
    """Las líneas de `d` con su tipo (`_tipo`), su peso (`_v`, el valor
    absoluto: una nota no resta peso) y el RUC limpio (`_ruc`). Vacío si al
    parquet le faltan las columnas (el modo demo no trae RUC)."""
    cols = ("FAMILIA", "SUBFAMILIA", "VALOR_COMPRA", "INDICADOR TRIBUTARIO",
            "NUM_DOCUMENTO", "NOMBRE_PROVEEDOR")
    if d is None or d.empty or any(c not in d.columns for c in cols):
        return pd.DataFrame(columns=[*cols, "_tipo", "_v", "_ruc"])
    # Por PAR (familia, subfamilia) y con un `merge`, nunca recorriendo las
    # filas: son ~150 pares contra ~53.000 líneas, y con el texto en Arrow
    # (pandas 3) iterar una columna fila por fila costaba 2 s (medido).
    pares = d[["FAMILIA", "SUBFAMILIA"]].drop_duplicates()
    pares = pares.assign(_tipo=[
        tipo_de_linea(f, s) for f, s in
        zip(pares["FAMILIA"].tolist(), pares["SUBFAMILIA"].tolist())])
    x = d[list(cols)].merge(pares, on=["FAMILIA", "SUBFAMILIA"], how="left")
    x["_v"] = pd.to_numeric(x["VALOR_COMPRA"], errors="coerce").abs().fillna(0)
    x["_ruc"] = x["INDICADOR TRIBUTARIO"].fillna("").astype(str).str.strip()
    return x[x["_tipo"].notna()]


def _dominante(x, claves):
    """Por grupo de `claves`: el tipo con más valor, su parte del total y la
    subfamilia que más pesa dentro de ese tipo. UN `groupby`: el mismo
    cálculo con dos y un `merge` tardaba el doble."""
    if x.empty:
        return pd.DataFrame(columns=[*claves, "_tipo", "parte", "SUBFAMILIA"])
    g = x.groupby([*claves, "_tipo", "SUBFAMILIA"], as_index=False,
                  sort=False)["_v"].sum()
    g["_vt"] = g.groupby([*claves, "_tipo"], sort=False)["_v"].transform("sum")
    g["parte"] = g["_vt"] / g.groupby(claves, sort=False)["_v"].transform("sum")
    # La fila ganadora de cada grupo: el tipo que más pesa y, dentro de él,
    # su subfamilia más pesada. Orden ESTABLE, para que un empate no cambie
    # de ganador entre corridas.
    return (g.sort_values(["_vt", "_v"], kind="stable")
             .drop_duplicates(claves, keep="last"))


def _a_dict(t, claves):
    """Las filas ganadoras de `_dominante` → {clave: (tipo, parte, subfamilia)}.
    Por `tolist`, nunca fila por fila (ver `_con_tipo`)."""
    llaves = list(zip(*(t[c].tolist() for c in claves)))
    if len(claves) == 1:
        llaves = [k[0] for k in llaves]
    return dict(zip(llaves, zip(t["_tipo"].tolist(), t["parte"].tolist(),
                                t["SUBFAMILIA"].tolist())))


CLAVE_DOCUMENTO = ("NUM_DOCUMENTO", "_ruc", "NOMBRE_PROVEEDOR")
"""La clave de un documento del Almacén: la misma tripleta con que lo
agrupa el cruce (`_parquet_agrupado_por_documento`), que vuelve en
`documento_sistema`, `ruc_sistema` y `proveedor_sistema`."""


def tablas_almacen(d):
    """Lo que el historial del Almacén sabe de cada proveedor y de cada
    documento, en DOS diccionarios `{clave: (tipo, parte, subfamilia)}`:

      · `proveedores` — por RUC, sólo si ≥ `PUREZA_PROVEEDOR` de un tipo.
      · `documentos` — por `CLAVE_DOCUMENTO`, el tipo que más pesa.

    Es lo caro (medio segundo con 53.000 líneas) y no depende del rango:
    la vista lo cachea por el sello del parquet."""
    x = _con_tipo(d)
    prov = _dominante(x, ["_ruc"])
    prov = prov[(prov["_ruc"] != "") & (prov["parte"] >= PUREZA_PROVEEDOR)]
    docs = _dominante(x, list(CLAVE_DOCUMENTO))
    return {"proveedores": _a_dict(prov, ["_ruc"]),
            "documentos": _a_dict(docs, list(CLAVE_DOCUMENTO))}


# ── La cascada ─────────────────────────────────────────────────────────────
def _pct(p):
    return f"{p * 100:.0f} %"


def _sin_igv(s):
    """La factura del SIRE va TODA exonerada o inafecta: nada gravado y
    algo no gravado. Con `abs`, para que una nota también cuente."""
    base = abs(float(s.get("base_imponible") or 0))
    ng = abs(float(s.get("no_gravado") or 0))
    return base < 0.005 and ng >= 0.005


def clasificar(df_cruce, df_sire, tablas):
    """`df_cruce` (el de `cruzar_con_parquet`) con dos columnas más:

      · `tipo` — Alimentos / Otros bienes / Servicios / Financiero, o ""
        si ninguna regla contesta.
      · `tipo_por` — de dónde sale, en una frase: es el tooltip de la celda,
        así que se escribe para leerse.

    `df_sire` aporta lo que el cruce no lleva (tipo de comprobante, base
    gravada y no gravada), por `car`. `tablas` es `tablas_almacen(d)`."""
    if df_cruce is None or df_cruce.empty:
        return df_cruce
    # Sólo las columnas que se leen, y por `tolist`: el registro llega con
    # el texto en Arrow y recorrerlo entero cuesta (ver `_con_tipo`).
    sire = {}
    _cols_sire = [c for c in ("car", "tipo_cdp", "tipo_nombre",
                              "base_imponible", "no_gravado")
                  if df_sire is not None and c in df_sire.columns]
    if "car" in _cols_sire:
        _lis = {c: df_sire[c].tolist() for c in _cols_sire}
        for i, car in enumerate(_lis["car"]):
            sire[str(car or "")] = {c: _lis[c][i] for c in _cols_sire}
    por_proveedor, por_doc = tablas["proveedores"], tablas["documentos"]
    def _col(nombre):
        # `tolist` y no `to_dict("records")`: el cruce viene con el texto en
        # Arrow y armar un dict por fila costaba ~1 s con 4.600 (medido).
        if nombre not in df_cruce.columns:
            return [""] * len(df_cruce)
        return ["" if v is None or (isinstance(v, float) and pd.isna(v))
                else str(v) for v in df_cruce[nombre].tolist()]

    car, prov, prov_sis = _col("car"), _col("proveedor"), _col("proveedor_sistema")
    ruc, ruc_sis, doc_sis = (_col("ruc_proveedor"), _col("ruc_sistema"),
                             _col("documento_sistema"))
    _sin_tipo = ("La factura lleva IGV y el Almacén no tiene un tipo claro "
                 "para este proveedor: no se le compró nada, o se le compra "
                 "de todo.")

    tipos, motivos = [], []
    for i in range(len(df_cruce)):
        s = sire.get(car[i], {})
        nombre = prov[i] or prov_sis[i]
        cdp = str(s.get("tipo_cdp") or "").strip().zfill(2) if s else ""
        clave_doc = (doc_sis[i], ruc_sis[i].strip(), prov_sis[i])
        el_ruc = ruc[i].strip() or ruc_sis[i].strip()

        if cdp in TIPOS_CDP_FINANCIEROS:
            t = (FINANCIERO, f"Comprobante «{s.get('tipo_nombre') or cdp}»: "
                             f"{TIPOS_CDP_FINANCIEROS[cdp]}.")
        elif es_entidad_financiera(nombre):
            t = (FINANCIERO, "La razón social es la de un banco, caja, "
                             "financiera, aseguradora o tarjeta.")
        elif clave_doc[0] and clave_doc in por_doc:
            tp, parte, sub = por_doc[clave_doc]
            t = (tp, f"Cargado en el Almacén como {sub}"
                     + ("." if parte >= 0.995 else
                        f"; el {_pct(parte)} del documento es {tp}."))
        elif el_ruc in por_proveedor:
            tp, parte, sub = por_proveedor[el_ruc]
            t = (tp, f"Lo que se le compra a este proveedor es {_pct(parte)} "
                     f"{tp}, sobre todo {sub} (Almacén).")
        elif s and _sin_igv(s):
            t = (ALIMENTOS, "Toda la factura va sin IGV, como las verduras, "
                            "frutas y pescados. El Almacén no tiene un tipo "
                            "claro para este proveedor.")
        else:
            t = ("", _sin_tipo)
        tipos.append(t[0])
        motivos.append(t[1])

    return df_cruce.assign(tipo=tipos, tipo_por=motivos)
