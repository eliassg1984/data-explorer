"""graficos.compras.documentos_sunat — drill «Documentos SUNAT».

Los comprobantes que los PROVEEDORES emitieron hacia nuestro RUC, tal como
los tiene anotados SUNAT en el Registro de Compras Electrónico (SIRE/RCE).

Es el único drill de Compras cuyo dato NO sale del parquet de R2: lo trae
`sunat.py` de la API de SUNAT. De ahí las dos diferencias con sus hermanos:

  · **No respeta los chips Familia/Subfamilia.** SUNAT no sabe de familias
    —eso es taxonomía nuestra, del maestro de productos— y el registro es
    por DOCUMENTO, no por línea de producto. Filtrar por familia acá daría
    un total que no cuadra con ningún papel. La franja de arriba lo dice.
  · **Se ordena por FECHA DE EMISIÓN**, como el resto del reporte — no
    por período tributario. SUNAT razona por período (cierra por mes) y
    ahí está la trampa: un comprobante emitido en julio puede estar
    anotado en el período de julio O seguir pendiente y aparecer recién
    en la propuesta del mes abierto. Son conjuntos DISTINTOS (medido: 290
    y 88, cero solapamiento), así que consultar un solo período deja
    agujeros. `sunat.obtener_comprobantes_rango` une los períodos que
    hagan falta y recién después filtra por fecha de emisión.

LO QUE SE VE Y LO QUE SE PUEDE BAJAR
------------------------------------
La ficha PDF que ofrece el panel derecho la RENDERIZA la app con los datos
del registro (`sunat.ficha_pdf`). No es el PDF que emitió el proveedor —
ésa es otra API (descarga masiva de CPE) sin acceso público, y NO se trae
acá en vivo. El panel lo dice en pantalla — no en un comentario— porque
confundir una cosa con la otra tiene consecuencias contables.

El original (PDF/XML tal como lo emitió el proveedor) SÍ puede aparecer,
pero viene de un proceso aparte: `herramientas/sunat_originales_sync.py`
lo baja del portal SOL a mano/localmente y lo sube a R2; acá sólo se
CHEQUEA si ya está (`sunat.originales`). Por eso conviven dos estados
normales para el mismo documento: sin sincronizar (solo la ficha
renderizada) y sincronizado (ficha + originales de verdad). Ver
`arquitectura.md` regla #142.

EL CRUCE CONTRA EL PARQUET (vista "Cruce")
-------------------------------------------
SUNAT dice qué comprobantes existen; `compras.parquet` dice qué cargó el
sistema. `cruzar_con_parquet()` compara ambas fuentes documento a
documento — Fecha de emisión, RUC, Proveedor, Base imponible y Total — y
marca cada uno "Coincide", "Diferencia", "Solo SUNAT" (falta cargarlo) o
"Solo sistema" (cargado sin comprobante electrónico que lo respalde).

El RUC del parquet vive en `INDICADOR TRIBUTARIO` (columna agregada
2026-08-20 a pedido, ver `COL_RUC_PARQUET`) — con un detalle sucio: ~24%
de las filas lo traen con un espacio final (`"20609456052 "`), así que
siempre se compara `.strip()`. Con RUC de los dos lados, el emparejamiento
ya no depende casi nunca de adivinar por nombre — eso queda como red de
seguridad para cuando una fila puntual no tenga RUC utilizable.

El total y la base imponible del lado parquet salen de `TOTAL DOCUMENTO`
y `TOTAL NETO` (misma tanda de columnas agregadas 2026-08-20, ver
`COL_TOTAL_PARQUET` / `COL_BASE_PARQUET`) — campos de CABECERA que se
agregan con `"first"`, no `"sum"`. Antes de que existieran, `total_pq` y
`base_pq` salían de sumar `VALOR_BRUTO_COMPRA_MN` / `VALOR_COMPRA` línea
por línea: una aproximación razonable casi siempre, pero una
reconstrucción al fin, no el dato real del documento.

La clave de cruce (`serie-número`) NO es única en todo el historial: es
el correlativo de CADA proveedor, y miles de emisores reusan "E001" como
su primera serie electrónica. Por eso `_parquet_agrupado_por_documento`
ACOTA el parquet al mismo rango que se está mirando antes de armar la
clave — ver su docstring para la medición real (sin acotar, la diferencia
promedio era S/372 y llegaba a S/18.632 por colisiones entre años; acotado
baja a S/6,9 y S/1.199 — esa medición es de ANTES de tener RUC, cuando la
única defensa era el nombre). Ver `arquitectura.md` regla #143.
"""

import datetime
import difflib
import io
import json
import re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, JsCode

import sunat
from cortes import MESES_ABR_ES
from estado_rango import clave_rango
import franja_fecha
from tema import (
    ACENTO, ACENTO_TEXTO, ADVERTENCIA_TEXTO, ERROR, ERROR_FONDO, ERROR_TEXTO,
    GRIS_BORDE, GRIS_FONDO, GRIS_TEXTO, GRIS_TEXTO_SUAVE,
    LAVANDA_CABECERA_GRUPO, LAVANDA_FOCO, LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from graficos.base import _compras_layout, _compras_truncar
from graficos.compras._comun import (
    COLUMNAS_COTEJO, GAP_DRILL,
)
from graficos import alturas
from tablas._css import _css_grid
from utils import _norm


# ===========================================================================
# CRUCE contra el parquet de Compras
# ===========================================================================
# SUNAT dice qué comprobantes existen; el parquet dice qué cargó el propio
# sistema. Son dos fuentes independientes del mismo hecho, y donde
# discrepan hay algo que revisar — una compra sin registrar, un monto que
# no cuadra, o una carga que no tiene comprobante electrónico detrás.

_COL_ESTADO = "Está vs Sistema"
"""Cabecera de la columna que dice si el documento está bien cargado.

Se llamaba «Estado» hasta el 2026-08-28 y se renombró a pedido, por dos
motivos que apuntan al mismo lado: «Estado» no decía estado DE QUÉ, y el
registro de SUNAT ya trae un campo `estado` propio (Activo / Anulado) —
dos cosas distintas con el mismo nombre en la misma pantalla. Liberado el
nombre, aquél puede aparecer cuando haga falta (hoy es «Activo» en los
16.678 comprobantes del registro, así que sale como chip y no como
columna).

Constante y no literal porque la usan la construcción de la tabla, la
configuración de su columna y la lectura de la fila seleccionada."""


_TOLERANCIA_CENTAVOS = 0.05
"""Diferencia de monto por debajo de la cual se considera "Coincide", no
"Diferencia". Medido contra datos reales (RUC 20605204300, julio 2026,
tras acotar por fecha — ver `_parquet_agrupado_por_documento`): el
percentil 75 de la diferencia de total es exactamente 0.00, y la más
chica real por encima del umbral es S/0,06 — remedido con `total_pq` y
`base_pq` ya saliendo de `TOTAL DOCUMENTO`/`TOTAL NETO` (ver
`COL_TOTAL_PARQUET` / `COL_BASE_PARQUET`), no de la suma por línea. 5
centavos sigue alcanzando para cubrir ruido de redondeo sin tapar
diferencias de negocio reales."""


def _llave_documento_parquet(num_documento):
    """`"{serie}-{numero}"` desde `NUM_DOCUMENTO` del parquet de Compras.

    El parquet lo arma como `"F0" + serie(4) + numero(9, con ceros a la
    izquierda)` — verificado decodificando valores reales
    (`"F0E001000001328"` → serie `"E001"`, número `"1328"`). Se le sacan
    los ceros de más para que calce con `documento` del SIRE
    (`sunat._normalizar_registro`, que ya viene sin ellos).
    """
    s = num_documento.astype(str)
    serie = s.str[2:6]
    numero = s.str[6:].str.lstrip("0")
    numero = numero.where(numero != "", "0")   # el raro caso numero="000..."
    return serie + "-" + numero


COL_RUC_PARQUET = "INDICADOR TRIBUTARIO"
"""Nombre real de la columna de RUC del proveedor en `compras.parquet`
(agregada 2026-08-20). Trae el RUC limpio en la mayoría de las filas, pero
~24% vienen con un espacio final (`"20609456052 "`, 12 caracteres en vez
de 11) — verificado contando longitudes sobre el parquet real. Por eso
`_parquet_agrupado_por_documento` siempre le aplica `.str.strip()`, nunca
se compara crudo."""

COL_TOTAL_PARQUET = "TOTAL DOCUMENTO"
"""Nombre real de la columna de total del documento en `compras.parquet`
(agregada 2026-08-20, junto con `COL_RUC_PARQUET` — no existía antes).
Es un campo de CABECERA: se repite igual en cada línea de producto del
mismo documento (0 documentos con más de un valor distinto, verificado
agrupando por documento+RUC+proveedor dentro de una ventana acotada), así
que se agrega con `"first"`, nunca `"sum"` — sumarlo multiplicaría el
total por la cantidad de líneas.

Antes de que existiera, el total del cruce salía de sumar
`VALOR_BRUTO_COMPRA_MN` (un valor POR LÍNEA) — una aproximación, no el
total real. Medido sin acotar por fecha/RUC/proveedor daba diferencias de
hasta S/32.915 contra `TOTAL DOCUMENTO`, pero eso resultó ser en su
mayoría el mismo problema de colisión de `serie-número` entre documentos
distintos que ya describe `_parquet_agrupado_por_documento` — acotado
correctamente (ventana de 60 días, ABRASA, agosto 2026) la diferencia caía
a 0 en 514 de 515 grupos. Aun así, `TOTAL DOCUMENTO` es la fuente
correcta ahora que existe: es el campo real de SUNAT en el propio
documento, no una reconstrucción."""

COL_BASE_PARQUET = "TOTAL NETO"
"""Nombre real de la columna de base imponible del documento en
`compras.parquet` (agregada 2026-08-20, misma tanda que `TOTAL IGV` —
tampoco existía antes). Mismo patrón que `COL_TOTAL_PARQUET`: campo de
CABECERA (0 documentos con más de un valor distinto, ventana de 60 días
sobre ABRASA), se agrega con `"first"`. `TOTAL NETO + TOTAL IGV ==
TOTAL DOCUMENTO` cuadra en 512 de 515 grupos medidos (el resto, redondeo
de centavos).

Antes de que existiera, `base_pq` salía de sumar `VALOR_COMPRA` por línea
— mismo defecto que tenía `total_pq` con `VALOR_BRUTO_COMPRA_MN` (ver
`COL_TOTAL_PARQUET`): una reconstrucción que depende de que ninguna línea
falte, no el campo real."""

COL_IGV_PARQUET = "TOTAL IGV"
"""Nombre real de la columna de IGV del documento en `compras.parquet`
(misma tanda 2026-08-20 que `TOTAL NETO` y `TOTAL DOCUMENTO`). Campo de
CABECERA, se agrega con `"first"` igual que sus dos hermanas.

Se compara desde 2026-08-27 y NO es redundante con base y total, aunque
`TOTAL NETO + TOTAL IGV == TOTAL DOCUMENTO`: esa identidad se cumple
dentro de CADA fuente por separado, así que base y total pueden cuadrar
los dos contra SUNAT y aun así el IGV estar mal repartido. El caso real
que lo motivó son los proveedores con TASA REDUCIDA (10.5% en vez de
18%): si el documento se carga con la tasa por defecto, el IGV sale
distinto del que declara el comprobante mientras el neto y el total
siguen calzando, porque el error se compensa entre sí.

Si la columna no está (parquet viejo), `igv_pq` queda en NaN y el IGV
sale de la comparación — NO se reconstruye como `total - base`. Esa
reconstrucción daría `dif_igv = dif_total - dif_base` por definición, o
sea cero información nueva y filas marcadas "Diferencia" por un dato que
en realidad no tenemos."""


def _parquet_agrupado_por_documento(d, col_fecha, fecha_ini, fecha_fin):
    """Compras del parquet agrupadas a una fila por (documento, RUC),
    ACOTADAS al rango que se está comparando.

    Acotar por fecha ANTES de armar la clave no es un detalle de
    performance, es lo que hace confiable el cruce: `serie-número`
    (p.ej. `"E001-1"`) NO es única en 3 años de historial — es el
    correlativo de factura de CADA proveedor, y "E001" es la serie por
    defecto que usan miles de emisores electrónicos distintos. Medido
    cruzando sin acotar (RUC 20605204300, julio 2026, ANTES de que el
    parquet tuviera columna de RUC): documentos "coincidentes" solo por
    `serie-número` resultaban ser de proveedores Y AÑOS distintos
    (2023-2025), con diferencias de hasta S/18.632. Acotando al rango, el
    promedio bajó de S/372 a S/6,9 y el máximo a S/1.199.

    Se agrupa por (documento, RUC, proveedor) — no solo por documento —
    por la misma razón: la clave sola puede repetirse entre proveedores
    incluso dentro de un mismo mes (3 de 269 casos medidos en julio, antes
    de tener RUC). El PROVEEDOR entra en la clave de agrupación a
    propósito, aunque el RUC ya esté: cuando el RUC viene vacío en dos
    filas de proveedores DISTINTOS que comparten documento (fila floja de
    origen, no inventada — ver `COL_RUC_PARQUET`), agrupar solo por
    (documento, RUC) las fusionaría en una sola bajo la clave `("...", "")`
    y sumaría montos de dos compras distintas. Con el nombre también en la
    clave, quedan separadas y es `cruzar_con_parquet` quien decide cuál
    corresponde — nunca la agregación.
    """
    columnas = ["documento", "ruc_pq", "proveedor_pq", "base_pq", "igv_pq",
                "total_pq", "fecha_pq", "num_doc_pq"]
    if (not col_fecha or col_fecha not in d.columns or fecha_ini is None
            or fecha_fin is None or "NUM_DOCUMENTO" not in d.columns):
        return pd.DataFrame(columns=columnas)

    fechas = pd.to_datetime(d[col_fecha], errors="coerce")
    ini = pd.Timestamp(fecha_ini).normalize()
    fin = pd.Timestamp(fecha_fin).normalize() + pd.Timedelta(days=1)
    dd = d[(fechas >= ini) & (fechas < fin) & d["NUM_DOCUMENTO"].notna()].copy()
    if dd.empty:
        return pd.DataFrame(columns=columnas)

    dd["documento"] = _llave_documento_parquet(dd["NUM_DOCUMENTO"])
    dd["ruc_pq"] = (dd[COL_RUC_PARQUET].astype(str).str.strip()
                     if COL_RUC_PARQUET in dd.columns else "")
    dd["_fecha"] = fechas.loc[dd.index]
    # A SOLES, que es la moneda del cruce. Las tres columnas de CABECERA
    # (`TOTAL NETO` / `TOTAL IGV` / `TOTAL DOCUMENTO`) vienen en la moneda
    # DEL DOCUMENTO —el Almacén guarda así, con su tipo de cambio al
    # lado— mientras que el registro del SIRE viene siempre en soles.
    # Compararlas crudas marcaba «Diferencia» en 242 de los 248
    # comprobantes en dólares del rango completo (medido 2026-09-05): 183
    # cuadran exacto al convertir y el resto son diferencias de verdad.
    # Las columnas por LÍNEA de respaldo (`VALOR_COMPRA`,
    # `VALOR_BRUTO_COMPRA_MN`) ya vienen en soles —el sufijo `_MN` es eso—
    # así que el factor NO se les aplica. Ver la regla #313.
    _factor = pd.Series(1.0, index=dd.index)
    if "TIPO_MONEDA" in dd.columns and "TIPO_CAMBIO" in dd.columns:
        _tc = pd.to_numeric(dd["TIPO_CAMBIO"], errors="coerce").fillna(1.0)
        _extranjera = (dd["TIPO_MONEDA"].astype(str).str.strip() != "01") & (_tc > 0)
        _factor = _factor.mask(_extranjera, _tc)
    for _col in (COL_BASE_PARQUET, COL_IGV_PARQUET, COL_TOTAL_PARQUET):
        if _col in dd.columns:
            dd[_col] = pd.to_numeric(dd[_col], errors="coerce") * _factor
    # base_pq y total_pq salen de los campos de CABECERA (TOTAL NETO /
    # TOTAL DOCUMENTO) con "first" cuando existen -- se repiten igual en
    # cada línea del documento, sumarlos multiplicaría el monto por la
    # cantidad de líneas. Si algún día faltan (parquet viejo), cae al
    # proxy de sumar por línea. Ver los docstrings de COL_BASE_PARQUET /
    # COL_TOTAL_PARQUET.
    col_base, agg_base = ((COL_BASE_PARQUET, "first")
                          if COL_BASE_PARQUET in dd.columns
                          else ("VALOR_COMPRA", "sum"))
    col_total, agg_total = ((COL_TOTAL_PARQUET, "first")
                            if COL_TOTAL_PARQUET in dd.columns
                            else ("VALOR_BRUTO_COMPRA_MN", "sum"))
    # Sin proxy: si la columna no está, el IGV queda en NaN y sale de la
    # comparación. Ver el docstring de COL_IGV_PARQUET sobre por qué NO se
    # reconstruye como `total - base`.
    dd["_igv"] = (pd.to_numeric(dd[COL_IGV_PARQUET], errors="coerce")
                  if COL_IGV_PARQUET in dd.columns else float("nan"))
    g = (dd.groupby(["documento", "ruc_pq", "NOMBRE_PROVEEDOR"], as_index=False)
           .agg(base_pq=(col_base, agg_base),
                igv_pq=("_igv", "first"),
                total_pq=(col_total, agg_total),
                fecha_pq=("_fecha", "first"),
                # El numero CRUDO del sistema (`F0FA28002305799`), que es
                # lo que se ve en el ERP -- `documento` ya es la llave
                # normalizada. "first" es seguro: dentro de un grupo
                # (llave, RUC, proveedor) hay UN solo valor crudo, medido
                # sobre el parquet real (693 grupos desde junio 2026, cero
                # con mas de uno). Ver `arquitectura.md` regla #143.
                num_doc_pq=("NUM_DOCUMENTO", "first"))
           .rename(columns={"NOMBRE_PROVEEDOR": "proveedor_pq"}))
    return g


def cruzar_con_parquet(df_sire, g_parquet):
    """Compara cada comprobante del SIRE contra su equivalente en el
    parquet de Compras (`g_parquet` — ver `_parquet_agrupado_por_documento`,
    YA acotado al mismo rango).

    Empareja por `documento` y, entre los candidatos que compartan esa
    clave, prioriza el que tenga el MISMO RUC (limpio con `.strip()` de
    ambos lados — ver `COL_RUC_PARQUET`). Solo si ningún candidato calza
    por RUC cae a desambiguar por NOMBRE (normalizado con `utils._norm`,
    acepta que uno contenga al otro) como red de seguridad — para cuando
    el RUC del parquet venga vacío o con un formato raro en esa fila
    puntual. Si ningún candidato es plausible por ninguna de las dos vías,
    NO fuerza el emparejamiento: mejor un documento "Solo SUNAT" de más
    que cruzarlo contra la factura de otro proveedor.

    Devuelve una fila por documento (unión SIRE ∪ parquet dentro del
    rango) con `estado` en uno de:
      "Coincide"      — en ambas fuentes, diferencia ≤ `_TOLERANCIA_CENTAVOS`
      "Diferencia"    — en ambas fuentes, con diferencia real de monto
      "Solo SUNAT"    — SUNAT lo reporta; no está cargado en el sistema
      "Solo sistema"  — está cargado; SUNAT no lo reporta (aún) para el RUC

    `base_sunat` = `base_imponible + no_gravado` del SIRE, no solo
    `base_imponible` — equivalencia confirmada por el usuario: `TOTAL
    NETO` del parquet es el neto del documento completo, afecto a IGV o
    no, mientras que SUNAT separa "base gravada" de "no gravado" en dos
    campos. Sumarlos es lo que hace comparable a `base_pq` (ver
    `arquitectura.md` regla #143, addendum 4).

    Desde 2026-08-27 la comparación son TRES cifras, no dos: base, **IGV**
    y total. El IGV entra porque base y total pueden cuadrar los dos y aun
    así el impuesto estar mal — pasa con los proveedores de tasa reducida
    (10.5%), donde cargar el documento con el 18% por defecto compensa el
    error entre neto y total y lo deja invisible. Cuando `igv_pq` viene
    NaN (parquet sin la columna) el IGV NO participa del veredicto: un
    dato ausente no puede volver "Diferencia" a una fila. Ver
    `COL_IGV_PARQUET`.
    """
    cols_pq = ["documento", "ruc_pq", "proveedor_pq", "base_pq", "igv_pq",
               "total_pq", "fecha_pq"]
    if g_parquet is None or g_parquet.empty:
        g_parquet = pd.DataFrame(columns=cols_pq)
    if df_sire is None:
        df_sire = pd.DataFrame(columns=["documento"])

    candidatos = {doc: sub for doc, sub in g_parquet.groupby("documento")}
    vistos_pq = set()   # (documento, ruc_pq) ya usados en un match
    filas = []

    for _, r in df_sire.iterrows():
        doc = str(r.get("documento", ""))
        ruc_sire = str(r.get("ruc_proveedor") or "").strip()
        prov_sire = str(r.get("proveedor", ""))
        sub = candidatos.get(doc)
        elegido = None
        if sub is not None and len(sub):
            por_ruc = sub[sub["ruc_pq"] == ruc_sire] if ruc_sire else sub.iloc[0:0]
            if len(por_ruc) == 1:
                elegido = por_ruc.iloc[0]
            elif len(sub) == 1:
                # Único candidato para esta clave: el RUC no calzó (o vino
                # vacío), pero no hay con qué más comparar. Se acepta —
                # es el mismo criterio de antes de tener columna de RUC.
                elegido = sub.iloc[0]
            else:
                # Varios candidatos y ninguno con el RUC exacto: red de
                # seguridad por nombre, como se hacía antes de tener RUC.
                n_sire = _norm(prov_sire)
                for _, cand in sub.iterrows():
                    n_pq = _norm(str(cand["proveedor_pq"]))
                    if n_sire and n_pq and (n_sire in n_pq or n_pq in n_sire):
                        elegido = cand
                        break

        # base_imponible (gravado) + no_gravado, no solo base_imponible:
        # TOTAL NETO del parquet es el neto del documento completo, sin
        # distinguir si está afecto a IGV o no -- SUNAT sí lo separa en
        # dos campos. Sin sumar no_gravado, una compra exonerada (ej.
        # alimentos sin procesar) mostraba base_imponible=0 contra un
        # TOTAL NETO real, como "Diferencia" pese a no haber ninguna.
        # Ver `arquitectura.md` regla #143, addendum 4.
        base_sunat = float(r.get("base_imponible") or 0) + float(r.get("no_gravado") or 0)
        # `igv` del SIRE ya viene sumado (IGV + IPM, gravado y no gravado)
        # por `sunat._normalizar_registro`; no hay nada que componer acá.
        igv_sunat = float(r.get("igv") or 0)
        total_sunat = float(r.get("total") or 0)
        if elegido is not None:
            # La tripleta (documento, ruc, proveedor) es la clave REAL de
            # `g_parquet` (la que arma `_parquet_agrupado_por_documento`),
            # así que es lo único que identifica una fila sin ambigüedad.
            # `(doc, ruc)` solo no alcanza: dos candidatos de PROVEEDORES
            # distintos pueden compartir un `ruc_pq` vacío bajo el mismo
            # documento (RUC flojo en el parquet, no un caso raro) — con
            # esa clave más corta, marcar el primero como "visto" hacía
            # que el segundo se diera por usado sin estarlo, y desaparecía
            # de la vista en vez de aparecer como su propio "Solo sistema".
            vistos_pq.add((doc, elegido["ruc_pq"], elegido["proveedor_pq"]))
            base_sist, total_sist = float(elegido["base_pq"]), float(elegido["total_pq"])
            dif_base = round(base_sunat - base_sist, 2)
            dif_total = round(total_sunat - total_sist, 2)
            # `.get()` y no `[...]`: hay llamadores (los tests) que arman
            # `g_parquet` a mano sin esta columna — mismo criterio que
            # `num_doc_pq`. Y `pd.isna` cubre los dos casos de ausencia:
            # la columna que no vino y el parquet viejo sin `TOTAL IGV`.
            _igv_crudo = elegido.get("igv_pq")
            _hay_igv = _igv_crudo is not None and not pd.isna(_igv_crudo)
            igv_sist = float(_igv_crudo) if _hay_igv else None
            dif_igv = round(igv_sunat - igv_sist, 2) if _hay_igv else None
            estado = ("Coincide"
                      if abs(dif_base) <= _TOLERANCIA_CENTAVOS
                      and abs(dif_total) <= _TOLERANCIA_CENTAVOS
                      and (dif_igv is None
                           or abs(dif_igv) <= _TOLERANCIA_CENTAVOS)
                      else "Diferencia")
            prov_sistema, ruc_sistema = elegido["proveedor_pq"], elegido["ruc_pq"]
            # `.get()` y no `[...]`: `cruzar_con_parquet` es publica y se
            # llama con df armados a mano en los tests, sin esta columna.
            doc_sistema = str(elegido.get("num_doc_pq") or "")
            # La fecha del parquet se descartaba: `fecha_emision` se quedaba
            # con la del SIRE y la del sistema no se veia nunca. A pedido
            # 2026-08-21 se comparan las dos — un documento cargado con otra
            # fecha de emision es un error contable real, y hasta hoy la
            # vista lo daba por "Coincide" mientras los montos calzaran.
            fecha_sist = elegido.get("fecha_pq")
        else:
            base_sist = total_sist = dif_base = dif_total = None
            igv_sist = dif_igv = None
            estado, prov_sistema, ruc_sistema = "Solo SUNAT", "", ""
            fecha_sist = None
            doc_sistema = ""

        filas.append({
            "fecha_emision": r.get("fecha_emision"), "documento": doc,
            "documento_sistema": doc_sistema,
            "fecha_sunat": r.get("fecha_emision"), "fecha_sistema": fecha_sist,
            "proveedor": prov_sire, "proveedor_sistema": prov_sistema,
            "ruc_proveedor": ruc_sire, "ruc_sistema": ruc_sistema,
            "situacion": r.get("situacion"),
            "base_sunat": base_sunat, "base_sistema": base_sist,
            "dif_base": dif_base,
            "igv_sunat": igv_sunat, "igv_sistema": igv_sist,
            "dif_igv": dif_igv,
            "total_sunat": total_sunat, "total_sistema": total_sist,
            "dif_total": dif_total, "estado": estado,
            # `car` es el identificador de la anotacion en SUNAT y la
            # UNICA clave sin colisiones (`_fila_de`: `documento` deja
            # 1.422, `ruc+documento` deja 3, `car` deja cero). Viaja para
            # que la tabla unificada pueda traer de `df_sire` los campos
            # que el cruce no lleva -- tipo, moneda, tipo de cambio y
            # detraccion -- sin volver a adivinar por documento.
            "car": str(r.get("car") or ""),
        })

    # Lo que quedó en el parquet sin usarse en NINGÚN match: son compras
    # cargadas en el sistema que SUNAT no reporta (aún) para este RUC.
    for _, cand in g_parquet.iterrows():
        if (cand["documento"], cand["ruc_pq"], cand["proveedor_pq"]) in vistos_pq:
            continue
        filas.append({
            "fecha_emision": cand.get("fecha_pq"), "documento": cand["documento"],
            "documento_sistema": str(cand.get("num_doc_pq") or ""),
            "fecha_sunat": None, "fecha_sistema": cand.get("fecha_pq"),
            "proveedor": "", "proveedor_sistema": cand["proveedor_pq"],
            "ruc_proveedor": "", "ruc_sistema": cand["ruc_pq"], "situacion": "",
            "base_sunat": None, "base_sistema": float(cand["base_pq"]),
            "dif_base": None,
            "igv_sunat": None,
            "igv_sistema": (float(cand["igv_pq"])
                            if cand.get("igv_pq") is not None
                            and not pd.isna(cand.get("igv_pq")) else None),
            "dif_igv": None,
            "total_sunat": None, "total_sistema": float(cand["total_pq"]),
            "dif_total": None, "estado": "Solo sistema",
            # Una fila que solo existe en el sistema no tiene anotacion en
            # SUNAT, asi que no tiene `car`. La columna existe igual para
            # que el df tenga una sola forma.
            "car": "",
        })

    out = pd.DataFrame(filas)
    if out.empty:
        return out
    for _c in ("fecha_emision", "fecha_sunat", "fecha_sistema"):
        out[_c] = pd.to_datetime(out[_c], errors="coerce")
    return out.sort_values("fecha_emision").reset_index(drop=True)


def _kpis_cruce(df, origen=None):
    """Resumen de UNA línea del cruce: cuántos documentos coinciden,
    difieren, o faltan de un lado u otro. Mismo criterio compacto que
    `_kpis` — ver su docstring sobre por qué no son `st.metric`.

    `origen` desde el 2026-08-28: al fundirse las dos tablas, ésta es la
    única tira de KPIs que queda, así que tiene que llevar también el
    sello de dónde salió el dato (parquet o API) que antes mostraba
    `_kpis`. Sin eso, el usuario perdía la única señal de que está viendo
    una copia y no lo que SUNAT dice ahora mismo.
    """
    if df is None or df.empty:
        st.markdown('<div style="min-height:38px;"></div>',
                    unsafe_allow_html=True)
        return
    conteos = df["estado"].value_counts()

    def dato(valor, etiqueta, color=None):
        c = color or TEXTO_PRINCIPAL
        return (f'<span style="white-space:nowrap;">'
                f'<b style="color:{c};font-weight:600;">{valor}</b>'
                f'<span style="color:{GRIS_TEXTO};"> {etiqueta}</span></span>')

    # El VOLUMEN del rango va primero -- lo mostraba `_kpis`, que murió al
    # fundirse las dos tablas (2026-08-28) y se llevaba puestos el total y
    # el IGV del período. Se suma el lado SUNAT, que es el original; las
    # filas «Solo sistema» no tienen y quedan fuera de esta suma, que es
    # lo correcto: no son comprobantes del SIRE.
    _tot = float(pd.to_numeric(df.get("total_sunat"), errors="coerce").sum())
    _igv = float(pd.to_numeric(df.get("igv_sunat"), errors="coerce").sum())
    partes = [
        dato(f"{len(df):,}", "docs"),
        dato(f"S/ {_tot:,.2f}", "total"),
        dato(f"S/ {_igv:,.2f}", "IGV"),
        dato(f'{int(conteos.get("Coincide", 0)):,}', "coinciden"),
    ]

    # Los conteos, prestados al KPI de la franja de vistas (2026-09-01, a
    # pedido: "cuantos estan en SUNAT y cuantos en sistema"). Se PUBLICAN
    # en vez de recalcularse alla porque el lado SUNAT sale de la consulta
    # al SIRE que se acaba de hacer aca — el rail no puede dispararla sola
    # para decorar un rotulo. Mismo patron que `CLAVE_CABECERA` de
    # navegacion.py: quien tiene el dato lo deja, quien lo pinta lo lee.
    #
    # Llega un rerun tarde (el rail se dibuja antes que esta vista), asi
    # que hasta que Documentos se abra una vez el KPI muestra solo el lado
    # del sistema. Es la degradacion correcta: un numero cierto y otro que
    # todavia no se sabe, en vez de bloquear la franja esperando a SUNAT.
    st.session_state["_cp_docs_cruce"] = {
        "sunat": int(len(df) - conteos.get("Solo sistema", 0)),
        "sistema": int(len(df) - conteos.get("Solo SUNAT", 0)),
    }

    n_dif = int(conteos.get("Diferencia", 0))
    if n_dif:
        mto = float(df.loc[df["estado"] == "Diferencia", "dif_total"].abs().sum())
        partes.append(dato(f"{n_dif:,}", f"con diferencia (S/ {mto:,.2f})",
                           ADVERTENCIA_TEXTO))

    n_ssu = int(conteos.get("Solo SUNAT", 0))
    if n_ssu:
        mto = float(df.loc[df["estado"] == "Solo SUNAT", "total_sunat"].sum())
        partes.append(dato(f"{n_ssu:,}", f"solo en SUNAT (S/ {mto:,.2f})",
                           ADVERTENCIA_TEXTO))

    n_ssi = int(conteos.get("Solo sistema", 0))
    if n_ssi:
        mto = float(df.loc[df["estado"] == "Solo sistema", "total_sistema"].sum())
        partes.append(dato(f"{n_ssi:,}", f"solo en el sistema (S/ {mto:,.2f})",
                           ERROR))

    if origen:
        partes.append(_sello_origen(origen))

    st.markdown(
        '<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center;'
        'justify-content:flex-end;font-size:12.5px;min-height:38px;">'
        + f'<span style="color:{GRIS_BORDE};">·</span>'.join(partes)
        + '</div>',
        unsafe_allow_html=True,
    )


_TOL_JS = str(_TOLERANCIA_CENTAVOS)

_JS_IMPORTE = JsCode("""
class ImporteCelda {
    init(p) {
        var d = p.data || {};
        var sim = d._sim || 'S/';
        this.eGui = document.createElement('div');
        this.eGui.style.lineHeight = '1.18';
        this.eGui.style.textAlign = 'right';
        var a = document.createElement('div');
        a.textContent = this.fmt(p.value, sim);
        if (p.value != null && !isNaN(p.value) && p.value < 0) {
            a.style.color = '__ERROR__';
        }
        this.eGui.appendChild(a);

        // Segunda linea, y SOLO una de las dos: o lo que dice el sistema
        // (cuando difiere), o la conversion a soles (cuando el
        // comprobante no esta en soles). Nunca las dos -- son dos
        // lecturas distintas y encimarlas convierte la celda en un
        // parrafo. Ver el docstring de `_tabla_documentos`.
        var sis = p.campoSis ? d[p.campoSis] : null;
        var texto = null, color = null;
        if (sis != null && sis !== '' && !isNaN(sis)
            && p.value != null && !isNaN(p.value)
            && Math.abs(Number(sis) - Number(p.value)) > __TOL__) {
            texto = 'sist. ' + this.num(sis);
            color = '__AMBAR__';
        } else if (p.campoConv && d[p.campoConv]) {
            texto = '\\u2248 ' + d[p.campoConv];
            color = '__GRIS__';
        }
        if (texto) {
            var b = document.createElement('div');
            b.textContent = texto;
            b.style.fontSize = '10.5px';
            b.style.color = color;
            b.style.fontWeight = (color === '__AMBAR__') ? '600' : '400';
            this.eGui.appendChild(b);
        }
    }
    num(v) {
        return Number(v).toLocaleString('es-PE',
            {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
    fmt(v, sim) {
        if (v == null || isNaN(v)) return '\\u2014';
        return (v < 0 ? '-' : '') + sim + ' ' + this.num(Math.abs(v));
    }
    getGui() { return this.eGui; }
}
""".replace("__TOL__", _TOL_JS)
   .replace("__AMBAR__", ADVERTENCIA_TEXTO)
   .replace("__GRIS__", GRIS_TEXTO_SUAVE)
   .replace("__ERROR__", ERROR_TEXTO))
"""La celda de un importe de la tabla unificada: el número de SUNAT arriba
y, cuando hace falta, UNA segunda línea debajo.

Es el corazón de la vista: reemplaza a las siete columnas «… sistema» que
la tabla tenía duplicadas. Sólo aparece la segunda línea en las filas donde
dice algo — 35 de 326 en el rango medido —, así que 9 de cada 10 filas se
leen como una tabla normal de una línea.

`cellRenderer` a mano y no `valueFormatter` porque hacen falta DOS nodos:
un formatter devuelve texto plano y el salto de línea no se renderiza. Ver
`arquitectura.md` regla #25 sobre por qué es una `class` con
`init`/`getGui` y no una función que devuelva HTML.

La tolerancia con la que decide si "difiere" es la MISMA
`_TOLERANCIA_CENTAVOS` con la que `cruzar_con_parquet` decide el estado —
interpolada acá adentro, no reescrita. Si fueran dos números distintos,
habría filas marcadas "Coincide" con la segunda línea encendida."""


_COLOR_CHIP = {
    # Rojo lo que RESTA o invalida; lavanda lo que sólo es distinto;
    # gris los tipos raros. Los tres pares salen de `tema.py` — ningún
    # `#hex` suelto (regla #1). Van como valores y no como `var(--...)`
    # porque el grid vive en un iframe propio y las variables CSS del
    # documento padre no llegan.
    "NC": [ERROR_FONDO, ERROR_TEXTO],
    "ND": [ERROR_FONDO, ERROR_TEXTO],
    "ANULADO": [ERROR_FONDO, ERROR_TEXTO],
    "USD": [LAVANDA_FONDO, ACENTO_TEXTO],
    "EUR": [LAVANDA_FONDO, ACENTO_TEXTO],
    "ADQ": [GRIS_FONDO, GRIS_TEXTO],
    "TC": [GRIS_FONDO, GRIS_TEXTO],
}
"""Chip → (fondo, texto)."""



_JS_DOCUMENTO = JsCode("""
class DocumentoCelda {
    init(p) {
        var d = p.data || {};
        this.eGui = document.createElement('div');
        var t = document.createElement('span');
        t.textContent = p.value == null ? '' : p.value;
        this.eGui.appendChild(t);
        var chips = String(d._chips || '').split('|');
        for (var i = 0; i < chips.length; i++) {
            if (!chips[i]) continue;
            var c = document.createElement('span');
            c.textContent = chips[i];
            c.style.fontSize = '9.5px';
            c.style.fontWeight = '600';
            c.style.letterSpacing = '.04em';
            c.style.padding = '1px 5px';
            c.style.borderRadius = '4px';
            c.style.marginLeft = '5px';
            c.style.verticalAlign = '1px';
            var col = __COLORES__[chips[i]] || ['#eeeef2', '#52525c'];
            c.style.background = col[0];
            c.style.color = col[1];
            this.eGui.appendChild(c);
        }
    }
    getGui() { return this.eGui; }
}
""".replace("__COLORES__", json.dumps(_COLOR_CHIP)))
"""El número de documento con sus CHIPS: marcan lo que NO es la norma.

Nació de medir el registro completo el 2026-08-28: 16.276 de 16.678
comprobantes (97,6 %) son «Factura» y 16.037 son en soles. Una columna
«Tipo» donde casi todas las filas repiten la misma palabra gasta 94 px
para no decir nada — y encima «Documentos emitidos por Adquiriente» no
entra sin cortarse. Marcando sólo la excepción, esos 94 px se los queda el
nombre del proveedor, que hoy se corta en todas las filas.

Los chips que puede emitir `_chips_de`: `NC`/`ND` (notas), `ADQ`/`TC`
(los dos tipos raros), `USD`/`EUR` (moneda) y `ANULADO` (estado del
comprobante en SUNAT — cero casos en toda la historia medida, pero es
justo el que no se puede pasar por alto si aparece)."""


_CHIPS_POR_TIPO = {
    "Nota de Crédito": "NC",
    "Nota de Débito": "ND",
    "Documentos emitidos por Adquiriente": "ADQ",
    "Documentos emitidos por TC Propias": "TC",
}
"""Tipo de comprobante → chip. «Factura» NO está a propósito: es el 97,6 %
del registro y marcarla sería marcar todo. Un tipo que no esté acá tampoco
emite chip; el dato completo vive en la ficha."""


def _chips_de(fila):
    """Los chips de una fila, separados por `|` (lo que espera
    `_JS_DOCUMENTO`). Vacío para una factura en soles y activa, que es el
    caso normal."""
    chips = []
    t = _CHIPS_POR_TIPO.get(str(fila.get("tipo_nombre") or "").strip())
    if t:
        chips.append(t)
    mon = str(fila.get("moneda") or "").strip().upper()
    if mon and mon != "PEN":
        chips.append(mon)
    if str(fila.get("estado_cpe") or "").strip().lower() not in ("", "activo"):
        chips.append("ANULADO")
    return "|".join(chips)


def _tabla_documentos(df_cruce, df_sire):
    """LA tabla del drill: los comprobantes de SUNAT y, en la misma celda,
    lo que dice el sistema cuando no coincide. Devuelve la fila COMPLETA
    del SIRE elegida, o `None`.

    Reemplaza a las DOS tablas que había hasta el 2026-08-28 —`_tabla`
    (sólo SUNAT) y `_tabla_cruce` (las dos fuentes en 15 columnas)—, a
    pedido: si la diferencia vive dentro de la celda, «Cruce» deja de ser
    una vista aparte y pasa a ser una columna.

    LO QUE SE GANA, medido: la tabla de cruce tenía 1848 px de ancho
    mínimo contra los ~1010 útiles de una laptop de 1358 — 838 px detrás
    del scroll horizontal, el 45 %. Y ese ancho servía al 11 % de las
    filas: de 326, sólo 35 (16 «Diferencia» + 19 «Solo sistema») usaban
    las columnas del sistema; en las 169 «Coincide» repetían el número de
    al lado y en las 122 «Solo SUNAT» estaban vacías. Ahora son ocho
    columnas y 868 px de mínimo.

    LAS OCHO, y por qué no son más:
      · Fecha, Documento, Proveedor — la identidad.
      · Base, IGV, Total — el dinero, con la segunda línea de
        `_JS_IMPORTE` cuando el sistema dice otra cosa.
      · D — la detracción, que SUNAT ya marca y no se mostraba en ningún
        lado (1.145 de 16.678 en el registro completo).
      · «Está vs Sistema» — el estado del cruce.
    Lo demás se midió y se dejó afuera: «Tipo» es 97,6 % «Factura» (va
    como chip, ver `_JS_DOCUMENTO`), «Fecha de vencimiento» viene vacía o
    igual a la emisión en 229 de 307 filas, «Período tributario» es
    constante dentro de un mes y «Estado del comprobante» es «Activo» en
    los 16.678 del registro. Todos viven en la ficha, que es donde se mira
    UN documento.

    RUC y «Documento sistema» también se fueron a la ficha. El primero
    vuelve como segunda línea del proveedor si los dos lados no coinciden
    —el caso que esa columna existía para cazar—; el segundo nunca fue
    comparable (es el mismo número en otra notación, `F0FA28002334492`
    contra `FA28-2334492`) y es un dato para copiar, no para escanear.

    `df_sire` entra porque el cruce no trae todos los campos de SUNAT: el
    tipo, la moneda, el tipo de cambio y la detracción se traen de ahí por
    `car`, que es la única clave sin colisiones (ver `_fila_de`).
    """
    if df_cruce is None or df_cruce.empty:
        st.info("No hay comprobantes que mostrar en el rango.")
        return None

    # Los campos que el cruce no lleva, por `car`. `.get` con relleno: los
    # tests arman df sin estas columnas y `cruzar_con_parquet` es publica.
    _cols = ("tipo_nombre", "moneda", "tipo_cambio", "detraccion", "estado")
    extra = {}
    if df_sire is not None and "car" in df_sire.columns:
        for _, r in df_sire.iterrows():
            extra[str(r.get("car") or "")] = {c: r.get(c) for c in _cols}

    filas = []
    for _, r in df_cruce.iterrows():
        car = str(r.get("car") or "")
        ex = extra.get(car, {})
        mon = str(ex.get("moneda") or "PEN").strip().upper() or "PEN"
        tc = ex.get("tipo_cambio") or 1.0
        total_sunat = _num(r.get("total_sunat"))
        # LA TABLA ESTA EN SOLES, las dos columnas: el registro del SIRE
        # viene en soles y el lado del sistema se convierte al agrupar
        # (ver `_parquet_agrupado_por_documento`). La segunda linea es el
        # importe como lo dice el PAPEL, y solo aparece en las 647 filas
        # en moneda extranjera del registro; en las otras 16.042 no hay
        # nada que aclarar.
        conv = ""
        if mon != "PEN" and total_sunat is not None:
            try:
                conv = (f"{sunat.simbolo_moneda(mon)} "
                        f"{total_sunat / float(tc):,.2f}")
            except (TypeError, ValueError, ZeroDivisionError):
                conv = ""
        _chips = _chips_de({"tipo_nombre": ex.get("tipo_nombre"),
                            "moneda": mon, "estado_cpe": ex.get("estado")})
        base_s, igv_s, tot_s = (_num(r.get("base_sistema")),
                                _num(r.get("igv_sistema")),
                                _num(r.get("total_sistema")))
        base_u, igv_u = _num(r.get("base_sunat")), _num(r.get("igv_sunat"))
        # Si la fila va a necesitar DOS lineas en alguna celda, la fila
        # entera mide 44 en vez de 30 (`getRowHeight`). Se decide aca y no
        # en JS para no repetir la comparacion en tres renderers.
        dos = bool(conv) or any(
            a is not None and b is not None
            and abs(a - b) > _TOLERANCIA_CENTAVOS
            for a, b in ((base_u, base_s), (igv_u, igv_s), (total_sunat, tot_s)))

        filas.append({
            "_car": car,
            "_chips": _chips,
            # Soles SIEMPRE: los importes de las dos fuentes ya estan en
            # soles cuando llegan aca. El simbolo de la moneda del papel
            # vive en `_conv`, que es el importe que si esta en esa moneda.
            "_sim": "S/",
            "_tipo": str(ex.get("tipo_nombre") or ""),
            "_base_sis": base_s, "_igv_sis": igv_s, "_total_sis": tot_s,
            "_conv": conv,
            "_dos": dos,
            "Fecha": r.get("fecha_emision"),
            "Documento": str(r.get("documento") or ""),
            "Proveedor": str(r.get("proveedor") or "")
                         or str(r.get("proveedor_sistema") or ""),
            "Base": base_u if base_u is not None else base_s,
            "IGV": igv_u if igv_u is not None else igv_s,
            "Total": total_sunat if total_sunat is not None else tot_s,
            "D": "D" if str(ex.get("detraccion") or "").strip().upper() == "D"
                 else "",
            _COL_ESTADO: str(r.get("estado") or ""),
        })

    tv = pd.DataFrame(filas)
    tv["Fecha"] = pd.to_datetime(tv["Fecha"], errors="coerce").dt.strftime(
        "%d/%m/%Y").fillna("")

    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=True, filter=False,
                                editable=False, suppressMovable=True)
    for oculta in ("_car", "_chips", "_sim", "_base_sis", "_igv_sis",
                   "_total_sis", "_conv", "_dos"):
        gb.configure_column(oculta, hide=True)
    # `_tipo` va oculta pero NO muerta: con el tipo fuera de las columnas
    # visibles (es un chip), ésta es la que permite ordenar y filtrar por
    # tipo sin gastar 94 px de ancho.
    gb.configure_column("_tipo", hide=True, headerName="Tipo")
    gb.configure_column("Fecha", width=96, minWidth=96)
    gb.configure_column("Documento", width=140, minWidth=126,
                        cellRenderer=_JS_DOCUMENTO)
    gb.configure_column("Proveedor", minWidth=170, flex=1,
                        tooltipField="Proveedor")
    gb.configure_column("Base", type=["numericColumn"], width=100, minWidth=100,
                        cellRenderer=_JS_IMPORTE,
                        cellRendererParams={"campoSis": "_base_sis"})
    gb.configure_column("IGV", type=["numericColumn"], width=90, minWidth=90,
                        cellRenderer=_JS_IMPORTE,
                        cellRendererParams={"campoSis": "_igv_sis"})
    gb.configure_column("Total", type=["numericColumn"], width=112,
                        minWidth=112, cellRenderer=_JS_IMPORTE,
                        cellRendererParams={"campoSis": "_total_sis",
                                            "campoConv": "_conv"})
    gb.configure_column(
        "D", width=34, minWidth=34,
        headerTooltip="Detracción: SUNAT la marca en el registro. "
                      "Condiciona cuándo se puede usar el crédito fiscal.",
        cellStyle=JsCode(
            "function(p){ return p.value ? {'color':'%s','fontWeight':'700',"
            "'textAlign':'center'} : {}; }" % ADVERTENCIA_TEXTO))
    # Misma convención de color que tenía «Estado»: ámbar = revisar, rojo =
    # plata cargada sin comprobante electrónico que la respalde.
    # «Coincide» no se destaca — lo normal no compite por atención.
    gb.configure_column(
        _COL_ESTADO, width=126, minWidth=126,
        cellStyle=JsCode(
            "function(p){ var m={'Diferencia':'%s','Solo SUNAT':'%s',"
            "'Solo sistema':'%s'}; var c=m[p.value]; "
            "return c ? {'color':c,'fontWeight':'600'} : {'color':'%s'}; }"
            % (ADVERTENCIA_TEXTO, ADVERTENCIA_TEXTO, ERROR, GRIS_TEXTO)))
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(
        headerHeight=32,
        # Sólo las filas con segunda línea miden 44; las demás siguen en
        # 30. Uniformar a 44 gastaría 14 px por fila en las 291 que no la
        # tienen — en una tabla de 326, media pantalla.
        getRowHeight=JsCode(
            "function(p){ return (p.data && p.data._dos) ? 44 : 30; }"),
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
    )

    resp = AgGrid(
        tv, gridOptions=gb.build(),
        height=alturas.por_filas(len(tv), px_fila=32, rol=alturas.APOYO),
        theme="material",
        custom_css={**_css_grid(13, cebra=False),
                    # Con las filas de un blanco uniforme hay que marcar la
                    # SELECCIONADA: de esta tabla cuelga todo lo de abajo.
                    # Ver `arquitectura.md` regla #235.
                    ".ag-row-selected": {
                        "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
                        "font-weight": "600 !important",
                    }},
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        key="sunat_docs_grid",
    )
    sel = resp.selected_rows
    if sel is None or (hasattr(sel, "empty") and sel.empty) or len(sel) == 0:
        return None
    fila = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
    if fila[_COL_ESTADO] == "Solo sistema":
        # No hay documento del SIRE que le corresponda: no es una carencia
        # del panel, es que ese comprobante no tiene contraparte ahí.
        return None
    return _fila_de(df_sire, fila)


def _sello_origen(origen):
    """De dónde salió el dato, para la tira de KPIs.

    Un proceso de madrugada sin alertas tiene un agujero conocido: si deja
    de correr, nadie se entera — el dato viejo se ve igual de plausible
    que el fresco (misma lección que la regla #141, donde un total
    creíble bajo un título equivocado lo cazó un usuario, no un test).
    Mostrar la antigüedad lo hace visible sin gastar alto: es un ítem más
    de la línea que ya existe.

    Los cuatro orígenes que puede devolver `sunat.comprobantes_rango` se
    ven distinto acá, y el que más importa es el ÚLTIMO: cuando hacía
    falta consultar en vivo y SUNAT no contestó, lo que hay en pantalla
    está incompleto y tiene que decirlo. Un total creíble al que le faltan
    los últimos días es la regla #141 otra vez. Ver regla #197.
    """
    if origen == "api":
        return ('<span style="white-space:nowrap;" title="Consultado a la '
                'API de SUNAT en vivo: el parquet del registro todavía no '
                'existe en R2.">en vivo</span>')
    if origen == "parquet+vivo":
        return ('<span style="white-space:nowrap;" title="El rango pasa del '
                'último día que trajo el sync de madrugada: esos días se le '
                'preguntaron a SUNAT en el momento.">registro + en vivo</span>')
    if origen == "parquet-sin-cola":
        return (f'<span style="white-space:nowrap;color:{ADVERTENCIA_TEXTO};" '
                'title="El rango incluye días que el sync todavía no trajo y '
                'SUNAT no respondió la consulta en vivo. Faltan esos días: '
                'probá de nuevo con ⟳.">faltan los últimos días</span>')
    fecha = sunat.fecha_registro()
    if fecha is None:
        return '<span style="white-space:nowrap;">registro en R2</span>'
    horas = (pd.Timestamp.now(tz="UTC") - pd.Timestamp(fecha)).total_seconds() / 3600
    # Más de un día y medio sin actualizarse ya no es "de anoche": el sync
    # se salteó al menos una corrida y conviene que se vea.
    color = ADVERTENCIA_TEXTO if horas > 36 else GRIS_TEXTO
    if horas < 24:
        cuando = "hoy"
    elif horas < 48:
        cuando = "ayer"
    else:
        cuando = f"hace {int(horas // 24)} días"
    return (f'<span style="white-space:nowrap;color:{color};" '
            f'title="Última sincronización del registro: '
            f'{pd.Timestamp(fecha):%d/%m/%Y %H:%M} UTC">{cuando}</span>')


# Alto de una fila del ranking de proveedores. Mismo número que el ranking
# de `proveedor.py`: es la misma lectura —un proveedor por fila, ordenado
# por valor— y con filas más gordas entran tres proveedores donde antes se
# veían diez barras.
_ALTO_FILA_RANK = 28


def _ranking_proveedores(df):
    """Ranking de proveedores del período como TABLA, no como barras.

    2026-08-24, a pedido ("no me muestra mucha información"): reemplaza al
    `go.Bar` horizontal de «Top proveedores del período». Esa barra
    mostraba UN dato (el monto) de DIEZ proveedores, con el nombre cortado
    a 30 caracteres. Acá cada proveedor trae cuatro, el nombre se ellipsea
    con el ancho real y el tooltip lo completa, y ya no son diez: entran
    todos los del rango, y lo que no cabe scrollea DENTRO del frame, que
    mide lo mismo que medía el gráfico.

    Las dos participaciones no responden la misma pregunta y por eso van
    las dos: «% valor» dice cuánta plata se le va a ese proveedor, «% docs»
    cuánto papeleo genera. Un proveedor con el 2% del valor y el 25% de los
    documentos es exactamente el caso que la barra de monto escondía.

    Las dos son sobre lo que muestra ESTA tabla (el rango, ya filtrado por
    situación), no sobre los KPIs de arriba, que se calculan sin ese
    filtro. Por eso el subtítulo dice contra qué base están sacadas.

    La barra de progreso es el FONDO de la celda de «Total» (un
    `linear-gradient` cortado en el % contra el mayor del rango), la misma
    receta que el ranking de `proveedor.py`: no hace falta `cellRenderer`
    —que acá pediría la clase `init()/getGui()` de la regla #25— ni los
    sparklines de AG Grid, que son Enterprise. Los colores salen de
    `tema.py` y no de `var(--...)` a propósito: el grid vive en un iframe
    propio y las variables CSS del documento padre no llegan.
    """
    val = pd.to_numeric(df.get("total"), errors="coerce").fillna(0.0)
    # Se agrupa por RUC y no por razón social: el RUC es la identidad del
    # proveedor (mismo criterio que `_fila_de`). SUNAT devuelve el nombre
    # tal como está en su padrón y basta una tilde o un "S.A.C." abreviado
    # distinto entre períodos para partir un proveedor en dos filas.
    clave = (df["ruc_proveedor"].astype(str) if "ruc_proveedor" in df
             else df["proveedor"].astype(str))
    g = pd.DataFrame({
        "ruc": clave.values,
        "nombre": df["proveedor"].astype(str).values,
        "valor": val.values,
    })
    # `size` y no `nunique(documento)`: cada fila del registro ES un
    # comprobante —lo mismo que cuenta el KPI "docs" de arriba— y
    # serie-número NO identifica uno (ver `_fila_de`: 1.422 colisiones
    # medidas), así que deduplicar por ahí perdería documentos reales.
    agg = (g.groupby("ruc", sort=False)
             .agg(nombre=("nombre", "first"), valor=("valor", "sum"),
                  docs=("valor", "size"))
             .reset_index()
             .sort_values("valor", ascending=False)
             .reset_index(drop=True))
    if agg.empty:
        st.info("Sin datos para el ranking.")
        return

    tot_val = float(agg["valor"].sum())
    tot_docs = int(agg["docs"].sum())
    # Las notas de crédito RESTAN (`sunat.py`), así que un proveedor puede
    # cerrar el rango en negativo. El máximo se toma sólo si es positivo:
    # dividir por un máximo negativo daría barras largas justo en las filas
    # que menos valor tienen.
    _max = float(agg["valor"].max())
    _max = _max if _max > 0 else 1.0

    st.markdown(
        f'<div style="font-size:14px;font-weight:600;color:{TEXTO_PRINCIPAL};'
        'margin:2px 0 0;">Proveedores del período</div>'
        f'<div style="font-size:11.5px;color:{GRIS_TEXTO};margin:0 0 6px;">'
        f'{len(agg):,} proveedores · {tot_docs:,} docs · '
        f'S/ {tot_val:,.2f} — los % son sobre esta base</div>',
        unsafe_allow_html=True)

    tv = pd.DataFrame({
        "Proveedor": agg["nombre"],
        "Total": agg["valor"].astype(float),
        "Docs": agg["docs"].astype(int),
        "% docs": agg["docs"] / tot_docs * 100 if tot_docs else 0.0,
        "% valor": agg["valor"] / tot_val * 100 if tot_val else 0.0,
        # Ocultas: el % de LLENADO de la barra (contra el MAYOR, que no es
        # el mismo número que "% valor", que va sobre el TOTAL) y el RUC,
        # que sólo se usa en el tooltip del nombre.
        "_barra": agg["valor"] / _max * 100,
        "_ruc": agg["ruc"],
    })

    # El texto va a la DERECHA y la barra tiene prohibido llegar hasta él:
    # si se pisan queda texto oscuro sobre fondo oscuro. `proveedor.py`
    # resuelve eso con un tope del 62% del ancho, y acá NO alcanza —
    # medido en el navegador: con la columna en 192px la barra más larga
    # llegaba a 119px y el monto arrancaba en 105, o sea 14px de "S/ " en
    # ilegible. Aquella columna es más ancha (`flex: 2`) y su monto va
    # redondeado, sin centavos; ésta muestra los centavos porque es plata
    # que se concilia contra un papel.
    #
    # Así que el tope no es un %, es un GUTTER FIJO en px: la barra ocupa
    # el ancho de la celda menos lo que mide el monto más largo. 110px sale
    # de medir el string más ancho que puede aparecer ("S/ 1,234,567.89" =
    # 88px con la fuente del grid) más los 15px de padding y un margen. Se
    # reparte igual para todas las filas, así que las proporciones entre
    # filas se mantienen. La pista va TRANSPARENTE, no tintada: con fondo,
    # la columna entera se lee como un bloque lavanda que compite con las
    # barras (eso sí es lección tal cual de `proveedor.py`).
    _js_barra = JsCode(
        "function(p){"
        " var ancho = (p.column && p.column.getActualWidth)"
        "   ? p.column.getActualWidth() : 0;"
        " var util = Math.max(0, ancho - 110);"
        " var pct = Math.max(0, Math.min(100, p.data._barra||0));"
        " var w = (util ? (pct / 100 * util) : (pct * 0.45)) + (util ? 'px' : '%');"
        " return {'background': 'linear-gradient(90deg,"
        f" {ACENTO} 0 ' + w + ', transparent ' + w + ' 100%)',"
        " 'display':'flex','alignItems':'center',"
        " 'justifyContent':'flex-end',"
        f" 'color':'{TEXTO_PRINCIPAL}'"
        "};"
        "}")
    _js_soles = JsCode(
        "function(p){ return p.value==null ? '' :"
        " 'S/ ' + Number(p.value).toLocaleString('es-PE',"
        " {minimumFractionDigits:2, maximumFractionDigits:2}); }")
    # Un decimal, no cero: con 60+ proveedores en el rango la mayoría queda
    # por debajo del 1% y redondear al entero los deja a todos en "0%".
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' : p.value.toFixed(1) + '%'; }")

    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=True, filter=False,
                                editable=False, suppressMovable=True)
    gb.configure_column("_barra", hide=True)
    gb.configure_column("_ruc", hide=True)
    # El ancho del nombre se decide por MEDICIÓN, no a ojo, y no con `flex`:
    # `sizeColumnsToFit` reparte el sobrante en proporción a los anchos
    # base y NO le da nada extra a una columna por ser flexible (medido:
    # con `flex=1` todas crecieron por el mismo factor 1.44). O sea que la
    # palanca real es el ancho base. 320 sale de medir los nombres de un
    # rango real con la fuente del grid: mediana 182px, el más largo 328,
    # y con la columna en 289 se cortaban 4 de 19. Con 320 de base termina
    # cerca de 400 en pantalla y no se corta prácticamente ninguno — y el
    # que se corte lo completa el tooltip, que además agrega el RUC porque
    # el nombre solo no identifica al emisor.
    gb.configure_column(
        "Proveedor", width=320, minWidth=190,
        tooltipValueGetter=JsCode(
            "function(p){ return p.value + ' · RUC ' + (p.data._ruc||''); }"))
    # `minWidth` no es cosmético en ESTA columna: de su ancho sale el largo
    # de la barra (ancho − gutter). Medido con la ventana angosta, con la
    # columna en 169px la barra más larga quedaba en 59px; con el piso en
    # 190 nunca baja de 80. Por debajo del piso el grid scrollea en
    # horizontal, que es preferible a una barra que no se puede comparar.
    gb.configure_column("Total", type=["numericColumn"], width=190,
                        minWidth=190,
                        cellStyle=_js_barra, valueFormatter=_js_soles,
                        headerTooltip="Suma de los comprobantes del período. "
                                      "La barra compara contra el mayor.")
    gb.configure_column("Docs", type=["numericColumn"], width=80,
                        headerTooltip="Comprobantes emitidos por ese "
                                      "proveedor en el período.")
    gb.configure_column("% docs", type=["numericColumn"], width=95,
                        valueFormatter=_js_pct,
                        headerTooltip="Participación por CANTIDAD de "
                                      "documentos: cuánto del papeleo del "
                                      "período es de este proveedor.")
    gb.configure_column("% valor", type=["numericColumn"], width=95,
                        valueFormatter=_js_pct,
                        headerTooltip="Participación por VALOR comprado: "
                                      "cuánto del gasto del período se le "
                                      "va a este proveedor.")
    # Sin selección: esta tabla informa, no filtra. La que responde al clic
    # es la de documentos de abajo, que abre la ficha en el panel.
    # El ancho de la celda entra en el cálculo de la barra, así que cada vez
    # que cambia hay que RE-EVALUAR el `cellStyle`: AG Grid no lo hace solo
    # al redimensionar, deja el estilo en línea que calculó al montar y la
    # barra se queda con el largo de un ancho que ya no existe. No entra en
    # bucle: `refreshCells` no dispara ninguno de los dos eventos.
    gb.configure_grid_options(
        rowHeight=_ALTO_FILA_RANK, headerHeight=32, suppressCellFocus=True,
        onGridSizeChanged=JsCode(
            "function(p){ p.api.sizeColumnsToFit();"
            " p.api.refreshCells({force:true, columns:['Total']}); }"),
        # `finished` filtra los eventos intermedios del arrastre: sin eso se
        # repinta la columna en cada píxel que se mueve el mouse.
        onColumnResized=JsCode(
            "function(p){ if(p.finished){"
            " p.api.refreshCells({force:true, columns:['Total']}); } }"),
    )

    AgGrid(
        tv, gridOptions=gb.build(),
        # Mismo techo (`MINI`) que tenía el gráfico al que reemplaza: la
        # tarjeta comparte alto con la tabla de documentos de abajo y con la
        # ficha, y esta vista ya se pasaba de pantalla (ver el docstring de
        # `renderizar_documentos_sunat`). Lo que no entra en el frame
        # scrollea dentro del grid.
        height=alturas.por_filas(len(tv), px_fila=_ALTO_FILA_RANK, extra=45,
                                 rol=alturas.MINI),
        theme="material", custom_css=dict(_css_grid(13)),
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        key="sunat_rank_prov",
    )


def _grafico_por_fecha(df):
    """Barras del período por día de emisión."""
    fe = pd.to_datetime(df["fecha_emision"], errors="coerce")
    g = (pd.to_numeric(df["total"], errors="coerce")
         .groupby(fe.dt.date).sum().sort_index())
    if g.empty:
        st.info("Sin datos para graficar.")
        return
    fig = go.Figure(go.Bar(
        x=list(g.index), y=g.values, marker=dict(color=ACENTO, opacity=0.9),
        hovertemplate="%{x|%d/%m/%Y}<br>S/ %{y:,.2f}<extra></extra>",
    ))
    _compras_layout(fig, alto=alturas.MINI)
    # `tickformat` explícito: sin él Plotly rotula el eje con los meses en
    # INGLÉS ("Aug 2"), porque toma su locale por defecto. El
    # `hovertemplate` de arriba ya venía en formato local; el eje se había
    # quedado atrás y se notó el 2026-08-28, al quedar este gráfico y el
    # del proveedor —que sí rotula en español— como dos modos del mismo
    # panel, uno al lado del otro.
    fig.update_layout(title="Comprobantes por fecha de emisión")
    fig.update_xaxes(tickformat="%d/%m")
    st.plotly_chart(fig, use_container_width=True, key="sunat_g_dia")


def _fila_de(df, fila_vista):
    """La fila COMPLETA del df que corresponde a la fila clickeada.

    Busca por `car` —el identificador único de la anotación en SUNAT— y no
    por serie-número, que NO identifica un comprobante.

    Medido sobre los 16.583 comprobantes reales: **1.422 documentos
    comparten serie-número con otro de un proveedor DISTINTO.** Series como
    `E001` las usa cualquier emisor chico numerando desde 1, así que
    `E001-1`, `E001-100`, `E001-1002` aparecen tres o más veces, cada una
    de otra empresa. Buscando sólo por `documento`, el panel podía mostrar
    los datos de OTRO proveedor —importes, fechas, RUC— sin ningún error:
    exactamente el modo de fallo de las reglas #140 y #141, un dato
    plausible en el lugar equivocado.

    Verificado como clave: `documento` deja 1.422 colisiones,
    `ruc+documento` deja 3, `car` deja CERO.
    """
    car = str(fila_vista.get("_car", "") or "")
    if car:
        coincidencias = df[df["car"].astype(str) == car]
        if not coincidencias.empty:
            return coincidencias.iloc[0]
    # Sin `car` (no debería pasar) se cae al criterio viejo, que al menos
    # acierta el proveedor si además se compara el RUC.
    doc = str(fila_vista.get("Documento",
                             fila_vista.get("Documento SUNAT", "")))
    ruc = str(fila_vista.get("RUC", fila_vista.get("RUC SUNAT", "")))
    coincidencias = df[(df["documento"].astype(str) == doc)
                       & (df["ruc_proveedor"].astype(str) == ruc)]
    return coincidencias.iloc[0] if not coincidencias.empty else None


def _ficha_html(doc):
    """La ficha del comprobante, pintada en pantalla.

    POR QUÉ NO ES UN PDF EMBEBIDO (probado y descartado el 2026-08-19):
    Chrome no renderiza un `data:application/pdf` dentro de un iframe con
    `sandbox`, y Streamlit monta TODOS sus iframes con sandbox. Medido en
    el navegador: el frame carga con el alto correcto y `contentDocument`
    queda en `null` — o sea, un rectángulo en blanco y ningún error. No es
    algo que se arregle con CSS ni cambiando de `components.html` a
    `st.iframe`: la migración se hizo el 2026-08-24 (regla #204) y el
    `sandbox` no se movió, porque lo pone el frontend de Streamlit y no
    depende de qué función de Python emitió el iframe.

    Lo que se ve acá es HTML, y sale mejor que el PDF embebido: texto
    nítido en cualquier zoom, hereda la paleta de la app y funciona igual
    en el teléfono. El PDF sigue existiendo para descargar (`ficha_pdf`),
    y ambos salen de `sunat.campos_ficha()`, así que no pueden divergir.

    Un beneficio lateral: al no haber iframe, este panel no cae en la regla
    de `estilos/_00_base.py` que oculta todos los iframes por defecto.
    """
    # Un GRUPO por bloque, y los bloques en columnas. Cuando la ficha vivia
    # en la columna angosta de la derecha, apilar todo en una lista era lo
    # correcto; apilada bajo la tabla, a todo el ancho, esa misma lista
    # queda larguisima y con la etiqueta y el valor separados por medio
    # metro de vacio (son filas `space-between`). El grid reparte los
    # grupos en cuantas columnas entren, sin numero fijo: `auto-fit` +
    # `minmax(260px, 1fr)` da 1 columna en el telefono y 3-4 en desktop.
    # `break-inside: avoid` no hace falta porque cada grupo es un item del
    # grid, no texto fluyendo en `column-count`.
    filas = []
    for titulo, campos in sunat.campos_ficha(doc):
        grupo = [
            f'<div style="font-size:10px;font-weight:700;color:{ACENTO};'
            f'text-transform:uppercase;letter-spacing:.05em;margin:0 0 4px;'
            f'padding-bottom:3px;border-bottom:1px solid {GRIS_BORDE};">'
            f'{titulo}</div>'
        ]
        for etiqueta, valor in campos:
            grupo.append(
                f'<div style="display:flex;justify-content:space-between;'
                f'gap:10px;padding:3px 0;font-size:12px;">'
                f'<span style="color:{GRIS_TEXTO};">{etiqueta}</span>'
                f'<span style="color:{TEXTO_PRINCIPAL};font-weight:500;'
                f'text-align:right;">{valor}</span></div>'
            )
        filas.append(f'<div>{"".join(grupo)}</div>')

    st.markdown(
        f'<div style="padding:2px 2px 8px;">'
        f'<div style="display:grid;gap:14px 28px;'
        f'grid-template-columns:repeat(auto-fit,minmax(260px,1fr));">'
        f'{"".join(filas)}</div>'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;background:{LAVANDA_FONDO};border-radius:8px;'
        f'padding:9px 12px;margin-top:14px;">'
        f'<span style="font-size:12px;font-weight:700;color:{ACENTO_TEXTO};">'
        f'TOTAL</span>'
        f'<span style="font-size:16px;font-weight:700;color:{ACENTO_TEXTO};">'
        f'{sunat._importe(doc, "total")}</span></div>'
        f'<div style="font-size:10px;color:{GRIS_TEXTO};margin-top:8px;'
        f'line-height:1.45;">CAR SUNAT: {sunat._val(doc, "car")}</div></div>',
        unsafe_allow_html=True,
    )


def _tabla_detalle(lineas):
    """Las líneas del XML, como tabla. Es lo que el registro NO tiene."""
    if not lineas:
        st.caption("El XML no trae líneas de detalle legibles.")
        return
    tv = pd.DataFrame(lineas)
    st.dataframe(
        tv, use_container_width=True, hide_index=True,
        column_config={
            "codigo": st.column_config.TextColumn("Código", width="small"),
            "descripcion": st.column_config.TextColumn("Descripción",
                                                       width="large"),
            "cantidad": st.column_config.NumberColumn("Cant.", format="%.2f",
                                                      width="small"),
            "unidad": st.column_config.TextColumn("Unidad", width="small"),
            "precio_unitario": st.column_config.NumberColumn(
                "P. unitario", format="S/ %.2f"),
            "importe": st.column_config.NumberColumn("Importe",
                                                     format="S/ %.2f"),
        },
    )


_COLS_LINEA_PARQUET = ["COD_PRODUCTO", "NOMBRE_PRODUCTO", "CANTIDAD_COMPRA",
                       "UNIDAD_DE_INGRESO", "PRECIO_UNIT", "VALOR_COMPRA",
                       "FECHA_EMISION_DOC"]


def _lineas_parquet_del_documento(d, doc):
    """Las filas de `compras.parquet` (una por línea de producto, SIN
    agregar) que pertenecen a ESTE comprobante puntual — para la tarjeta
    «Conversor SUNAT-Sistema».

    Empareja por `documento` (mismo cálculo que `_llave_documento_parquet`)
    + RUC, igual criterio que `cruzar_con_parquet`/`_fila_de`: `NUM_DOCUMENTO`
    solo NO alcanza, es el correlativo de CADA proveedor y se repite entre
    emisores distintos (regla #143 de `arquitectura.md`). Si con
    documento+RUC todavía queda más de una fecha de emisión distinta (el
    mismo par repetido en años distintos — el caso que mide el docstring
    de `_parquet_agrupado_por_documento`), se acota a la fecha más cercana
    a la del SIRE.
    """
    if d is None or "NUM_DOCUMENTO" not in d.columns:
        return pd.DataFrame(columns=_COLS_LINEA_PARQUET)

    documento = str(doc.get("documento") or "")
    if not documento:
        return pd.DataFrame(columns=_COLS_LINEA_PARQUET)

    dd = d[d["NUM_DOCUMENTO"].notna()].copy()
    dd["_documento"] = _llave_documento_parquet(dd["NUM_DOCUMENTO"])
    dd = dd[dd["_documento"] == documento]
    if COL_RUC_PARQUET in dd.columns:
        ruc = str(doc.get("ruc_proveedor") or "").strip()
        dd = dd[dd[COL_RUC_PARQUET].astype(str).str.strip() == ruc]
    if dd.empty:
        return pd.DataFrame(columns=_COLS_LINEA_PARQUET)

    if "FECHA_EMISION_DOC" in dd.columns:
        fechas = pd.to_datetime(dd["FECHA_EMISION_DOC"], errors="coerce")
        if fechas.nunique() > 1:
            objetivo = pd.Timestamp(doc.get("fecha_emision"))
            mas_cercana = (fechas - objetivo).abs().idxmin()
            dd = dd[fechas == fechas.loc[mas_cercana]]

    cols = [c for c in _COLS_LINEA_PARQUET if c in dd.columns]
    return dd[cols].reset_index(drop=True)


def _asignar_greedy(candidatos, n_lineas):
    """`candidatos` = lista de `(puntaje, i_linea, j_candidato)` → una
    lista de tamaño `n_lineas` con, para cada línea, el `j` de mayor
    puntaje que sigue libre, o `None`. Cada `j` se usa como mucho una vez.

    Compartido por `_parear_lineas_sistema` y `_sugerir_desde_maestro`:
    mismo problema (emparejar 1 a 1 por puntaje, greedy) contra dos
    fuentes de candidatos distintas — no hace falta optimización
    combinatoria para un puñado de líneas por comprobante, y greedy es
    fácil de auditar a ojo.
    """
    asignado = [None] * n_lineas
    usado = set()
    for _sc, i, j in sorted(candidatos, key=lambda t: t[0], reverse=True):
        if asignado[i] is not None or j in usado:
            continue
        asignado[i] = j
        usado.add(j)
    return asignado


_PISO_SCORE_PAREO = 0.35
"""Piso de similitud para sugerir un emparejamiento automático CONTRA
`compras.parquet` (documento ya registrado). Medido contra un documento
real sincronizado (F002-9092, AGRO ELDREDGE E.I.R.L.): una descripción
idéntica normalizada da 1.0 de texto + 0.8 de bonus numérico (cantidad Y
precio calzan) = 1.8. 0.35 deja pasar coincidencias razonables (por
ejemplo solo texto, sin bonus numérico) sin forzar una línea que en
realidad no tiene par en este documento."""


def _parear_lineas_sistema(lineas_xml, filas_pq):
    """Sugiere, para cada línea del XML, cuál fila de `filas_pq` (líneas
    del sistema de ESTE documento, ya cargadas en `compras.parquet`) es su
    equivalente — o `None` si ninguna parece razonable. Solo tiene sentido
    para un documento YA REGISTRADO (`filas_pq` no vacío) — para uno
    pendiente, ver `_sugerir_desde_maestro`.

    Ninguna fuente comparte una clave: el código de línea del XML es del
    PROVEEDOR, `COD_PRODUCTO` es el INTERNO. El puntaje combina similitud
    de texto (`descripcion` vs `NOMBRE_PRODUCTO`, normalizado con
    `utils._norm` — misma función que ya usa `cruzar_con_parquet` para el
    fallback por nombre de proveedor) con cercanía de cantidad e importe.
    Validado contra un documento real: "PALTA FUERTE" (XML) vs
    "Palta Fuerte" (sistema), cantidad y precio unitario IDÉNTICOS — el
    caso común, medido, es que quien carga la compra copia el número tal
    cual del comprobante.

    Devuelve una lista paralela a `lineas_xml` con la POSICIÓN (no el
    índice de fila) de `filas_pq` que mejor calza, o `None` — ver
    `_asignar_greedy`.
    """
    if filas_pq.empty or not lineas_xml:
        return [None] * len(lineas_xml)

    def _score(xml_l, pq_row):
        s_txt = difflib.SequenceMatcher(
            None, _norm(str(xml_l.get("descripcion") or "")),
            _norm(str(pq_row["NOMBRE_PRODUCTO"] or ""))).ratio()
        s_num = 0.0
        try:
            if (xml_l.get("importe") is not None
                    and pd.notna(pq_row.get("VALOR_COMPRA"))
                    and abs(float(xml_l["importe"])
                            - float(pq_row["VALOR_COMPRA"])) <= 0.05):
                s_num += 0.5
        except (TypeError, ValueError):
            pass
        try:
            if (xml_l.get("cantidad") is not None
                    and pd.notna(pq_row.get("CANTIDAD_COMPRA"))
                    and abs(float(xml_l["cantidad"])
                            - float(pq_row["CANTIDAD_COMPRA"])) <= 0.01):
                s_num += 0.3
        except (TypeError, ValueError):
            pass
        return s_txt + s_num

    candidatos = []
    for i, xml_l in enumerate(lineas_xml):
        for j in range(len(filas_pq)):
            sc = _score(xml_l, filas_pq.iloc[j])
            if sc > _PISO_SCORE_PAREO:
                candidatos.append((sc, i, j))
    return _asignar_greedy(candidatos, len(lineas_xml))


def _tokens_busqueda(s):
    """Palabras (alfanumérico, sin acentos, minúsculas) de un texto — para
    indexar por token y ACOTAR candidatos antes de correr `difflib`.

    `utils._norm` no sirve para esto a propósito: saca los ESPACIOS
    (está pensada para comparar strings enteras por contención, no para
    partir en palabras), así que tokenizar con ella da una sola palabra
    gigante por texto."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z0-9]+", s.lower()))


_TOPE_CANDIDATOS_MAESTRO = 40
"""Cuántos candidatos del maestro, como mucho, llegan a `difflib` por
línea de XML en `_sugerir_desde_maestro`. Medido: puntuar una línea contra
las 3.867 filas del maestro COMPLETO tarda ~0,13s (difflib no es gratis);
una factura de 80 líneas —las hay reales, ver `compras.parquet`— tardaría
más de 10s, inaceptable para una pestaña interactiva. Acotando por token
compartido a 40 candidatos por línea, esas mismas 80 líneas bajan a
~1s (medido)."""


def _indice_tokens_maestro(nombres):
    """token → {posiciones de `nombres` que lo contienen}. Se arma UNA vez
    por render del maestro completo (no una vez por línea) — es lo que
    hace viable acotar candidatos antes de correr `difflib`, ver
    `_TOPE_CANDIDATOS_MAESTRO`."""
    idx = {}
    for pos, nom in enumerate(nombres):
        for tok in _tokens_busqueda(nom):
            idx.setdefault(tok, set()).add(pos)
    return idx


def _candidatos_por_token(descripcion, indice, tope=_TOPE_CANDIDATOS_MAESTRO):
    """Posiciones candidatas para `descripcion`, ordenadas por CUÁNTOS
    tokens comparte con cada una (no por similitud todavía — eso lo
    termina de decidir `difflib` después, en `_sugerir_desde_maestro`).
    Sin ningún token en común, lista vacía: no tiene sentido puntuar
    contra el maestro entero cuando no comparte ni una palabra."""
    conteo = {}
    for tok in _tokens_busqueda(descripcion):
        for pos in indice.get(tok, ()):
            conteo[pos] = conteo.get(pos, 0) + 1
    if not conteo:
        return []
    return [pos for pos, _ in
           sorted(conteo.items(), key=lambda kv: kv[1], reverse=True)[:tope]]


_PISO_SCORE_SUGERIDO = 0.5
"""Piso de similitud para SUGERIR desde el maestro completo — documento
TODAVÍA NO registrado, sin ninguna línea de `compras.parquet` con la que
corroborar cantidad/precio. A diferencia de `_PISO_SCORE_PAREO`, acá el
puntaje es SOLO texto (no hay bonus numérico posible), así que el piso es
más alto: exigir más similitud de texto puro compensa no tener con qué
corroborar."""


def _sugerir_desde_maestro(lineas_xml):
    """Como `_parear_lineas_sistema`, pero para un documento que TODAVÍA NO
    tiene ninguna línea en `compras.parquet` (no está registrado) — a
    pedido 2026-08-27, sugiere directo contra el maestro de artículos
    completo (`_maestro_productos`) por similitud de texto sola, ya que no
    hay ninguna compra registrada con la que corroborar cantidad o precio.

    Devuelve una lista paralela a `lineas_xml` con el CÓDIGO del maestro
    que mejor calza, o `None`. Código y no POSICIÓN a propósito: el
    resultado se cachea (`_sugerencias_maestro`) y una posición sólo
    significa algo mientras el maestro conserve el mismo orden — si el ETL
    republica el parquet en medio del TTL, una posición cacheada apunta a
    otro producto y nadie se entera. Un código apunta a lo mismo siempre.
    """
    descripciones = tuple(str(l.get("descripcion") or "") for l in lineas_xml)
    if not descripciones:
        return []
    return list(_sugerencias_maestro(descripciones))


@st.cache_data(ttl=3600, show_spinner=False)
def _sugerencias_maestro(descripciones):
    """La parte CARA de `_sugerir_desde_maestro`, cacheada por el conjunto
    de descripciones del XML.

    Existe por la lentitud que reportó el usuario el 2026-08-27 al corregir
    ítems: cada corrección re-corre el render, y esto es lo más caro que
    hay adentro — `_TOPE_CANDIDATOS_MAESTRO` documenta ~1s para una factura
    de 80 líneas, y se pagaba ENTERO en cada tecla confirmada, para
    recalcular exactamente lo mismo (el XML no cambia: lo que cambia es la
    corrección que se le aplica encima, y eso pasa después).

    El TTL acompaña al de `data.cargar` (1h), que es de donde sale el
    maestro: no tiene sentido cachear sugerencias más tiempo que el
    catálogo contra el que se calcularon.
    """
    maestro = _maestro_productos()
    if maestro.empty:
        return [None] * len(descripciones)

    nombres = maestro["NOMBRE PRODUCTO"].tolist()
    codigos = maestro["CODIGO PRODUCTO"].astype(str).tolist()
    indice = _indice_tokens_maestro_cache()

    candidatos = []
    for i, desc in enumerate(descripciones):
        a = _norm(desc)
        for pos in _candidatos_por_token(desc, indice):
            sc = difflib.SequenceMatcher(None, a, _norm(str(nombres[pos]))).ratio()
            if sc > _PISO_SCORE_SUGERIDO:
                candidatos.append((sc, i, pos))
    return [None if pos is None else codigos[pos]
            for pos in _asignar_greedy(candidatos, len(descripciones))]


_COLS_MAESTRO = ["CODIGO PRODUCTO", "NOMBRE PRODUCTO", "UNIDAD KARDEX"]


@st.cache_data(ttl=3600, show_spinner=False)
def _maestro_productos():
    """Código, nombre y unidad de KARDEX de todo el catálogo de artículos —
    a pedido 2026-08-27, no sale de `compras.parquet` (que solo tiene los
    ~1.582 productos que alguna vez se compraron, y su unidad es la de la
    compra puntual, no la de stock) sino de `inventariovalorizado.parquet`,
    el maestro real: 3.867 productos, y CADA código tiene un único nombre y
    unidad (0 conflictos, verificado con DuckDB contra R2 real).

    Cacheado ACÁ además de en `data.cargar`: aquél evita releer R2, pero el
    `dropna` + `drop_duplicates` + `sort_values` sobre las 15.357 filas
    crudas se pagaba igual en cada rerun (~20ms medidos). Con la edición en
    celda eso es una vez por tecla confirmada. Mismo TTL de 1h que
    `data.cargar`, para que las dos capas caduquen juntas.
    """
    import data

    m = data.cargar("inventariovalorizado.parquet")
    if m is None or not all(c in m.columns for c in _COLS_MAESTRO):
        return pd.DataFrame(columns=_COLS_MAESTRO)
    return (m[_COLS_MAESTRO].dropna(subset=["CODIGO PRODUCTO"])
            .drop_duplicates().sort_values("NOMBRE PRODUCTO")
            .reset_index(drop=True))


@st.cache_data(ttl=3600, show_spinner=False)
def _indice_tokens_maestro_cache():
    """`_indice_tokens_maestro` sobre el maestro completo, cacheado — se
    arma una vez por hora y no una vez por rerun (~37ms medidos sobre las
    3.867 filas reales). Ver `_sugerencias_maestro`."""
    return _indice_tokens_maestro(_maestro_productos()["NOMBRE PRODUCTO"].tolist())


@st.cache_data(ttl=3600, show_spinner=False)
def _lookups_maestro():
    """Los tres diccionarios que el conversor consulta por fila, armados de
    una sola pasada y cacheados con el maestro:

      · `por_codigo`: código → (nombre, unidad kardex). Lo que se MUESTRA
        una vez que hay un código, venga de donde venga.
      · `por_nombre`: nombre recortado en minúsculas → código. Para
        resolver lo que se tipeó en la celda. Ambiguo (mismo nombre, más
        de un código) se queda con el primero — 9 de 3.867 casos reales,
        medido con DuckDB.
      · `contexto`: el MISMO catálogo con la forma que espera el
        navegador, para viajar en `gridOptions.context` — `nombres` (para
        el `<datalist>` del autocompletado) y `porNombre`, que mapea el
        nombre en minúsculas a `[código, unidad, nombre]` (rellenar las
        columnas de al lado al elegir y resolver el "prefijo único" del
        editor; ver `_JS_MAESTRO_AL_NAVEGADOR`).

    POR QUÉ `context` Y NO UN JSON ADENTRO DEL JsCode, que es como estaba
    hasta el 2026-08-27: `JsCode.__init__` (st_aggrid 1.2.1) corre sobre el
    código un regex de "sacar los espacios que están fuera de un string"
    cuyo lookahead cuenta comillas de a pares hasta el final del texto —y
    por lo tanto retrocede de forma CATASTRÓFICA—, y encima descarta el
    resultado dos líneas más abajo (lo pisa un `re.sub` trivial).
    Medido con el catálogo real: 4.000 caracteres tardan 0,10s; 8.000,
    0,34s; 16.000, 1,35s — cuadrático limpio, que para los 110.082
    caracteres del catálogo da **~64 segundos por render**. Ése era el
    "se cuelga y se pone lento" que se reportó ese día: no era el
    emparejamiento ni R2, era una llamada a `JsCode` con un JSON grande
    adentro. `gridOptions.context` es dato plano, se serializa con
    `json.dumps` y no toca ese regex — el JsCode queda de 15 líneas.

    La FORMA del contexto tampoco es libre: `walk_gridOptions` (el
    recorrido de st_aggrid que busca JsCode) hace `go[k]` sobre los
    elementos de una lista, así que una lista DE LISTAS revienta con
    `TypeError`. Lista plana de strings y dict de listas sí pasan.
    """
    maestro = _maestro_productos()
    por_codigo, por_nombre = {}, {}
    nombres, por_nombre_js = [], {}
    for cod, nom, uni in zip(maestro["CODIGO PRODUCTO"].astype(str),
                             maestro["NOMBRE PRODUCTO"].astype(str),
                             maestro["UNIDAD KARDEX"].astype(str)):
        por_codigo[cod] = (nom, uni)
        por_nombre.setdefault(nom.strip().lower(), cod)
        nombres.append(nom)
        # [código, unidad, nombre-con-mayúsculas]: los dos primeros los
        # usa `_JS_RELLENAR_VECINAS`; el tercero, el "prefijo único" de
        # `_JS_EDITOR_PRODUCTO`, que necesita devolver el nombre tal como
        # se escribe y no la clave en minúsculas con la que se buscó.
        por_nombre_js.setdefault(nom.strip().lower(), [cod, uni, nom])
    return por_codigo, por_nombre, {"nombres": nombres,
                                    "porNombre": por_nombre_js}


_JS_EDITOR_PRODUCTO = JsCode("""
class ProductoEditor {
    init(params) {
        this.valorOriginal = params.value || '';
        this.eGui = document.createElement('div');
        this.eInput = document.createElement('input');
        this.eInput.className = 'ag-input-field-input ag-text-field-input';
        this.eInput.style.width = '100%';
        this.eInput.style.height = '100%';
        this.eInput.style.boxSizing = 'border-box';
        this.eInput.setAttribute('list', 'sunat_maestro_datalist');
        this.eInput.setAttribute('autocomplete', 'off');
        this.eInput.value = this.valorOriginal;
        this.eGui.appendChild(this.eInput);
    }
    getGui() { return this.eGui; }
    afterGuiAttached() { this.eInput.focus(); this.eInput.select(); }
    isPopup() { return false; }
    getValue() {
        var v = (this.eInput.value || '').trim();
        // Vaciar la celda SI vale: es el gesto de "volver a lo automatico"
        // (el servidor lo lee como `quitar_correccion_linea`).
        if (!v) return '';
        var mapa = window.__sunatMaestroPorNombre;
        if (!mapa) return v;                 // carrera rara al montar
        if (mapa[v.toLowerCase()]) return v;
        // Prefijo unico: escribir "tomahawk" y que quede
        // "Tomahawk de cerdo x Kg". Solo si NO hay ambiguedad.
        var pre = v.toLowerCase(), unico = null;
        for (var k in mapa) {
            if (k.indexOf(pre) === 0) {
                if (unico !== null) { unico = null; break; }
                unico = k;
            }
        }
        if (unico) return mapa[unico][2];
        // Nada del maestro: se vuelve al valor previo. Devolver el mismo
        // valor (y no rechazar) es a proposito -- ver el docstring.
        return this.valorOriginal;
    }
}
""")
"""Cell EDITOR a mano para "Ítem (sistema)" -- un `<input list=…>` con
autocompletado NATIVO del navegador, no `agRichSelectCellEditor` de AG
Grid (ese es Enterprise, descartado en todo el proyecto — ver CLAUDE.md
§ Restricciones de despliegue). Misma interfaz de Component que ya usan
los cellRenderer de este proyecto (`init`/`getGui`, ver arquitectura.md
regla #25), más `getValue`, propio de un EDITOR.

LA VALIDACIÓN VIVE EN `getValue`, NO EN `isCancelAfterEnd`, y eso no es
estilo: con `isCancelAfterEnd` devolviendo `true` —como estaba hasta el
2026-08-27— AG Grid 34.3.1 da por terminada la edición
(`getEditingCells()` devuelve 0) pero **deja el editor montado en el
DOM**: la celda queda con la clase `ag-cell-inline-editing` y un
`<input>` vacío encima, o sea SE VE VACÍA para siempre, aunque el dato
de abajo esté intacto (verificado en el navegador). Devolviendo el valor
previo desde `getValue` el camino de cancelación no se usa nunca: AG
Grid cierra el editor normal, compara viejo contra nuevo, ve que no
cambió y ni siquiera dispara `cellValueChanged` — no hay viaje al
servidor para un texto que no era un producto.

De paso, "prefijo único" hace que escribir `tomahawk` y salir de la
celda deje `Tomahawk de cerdo x Kg`: el `<datalist>` ya sugiere mientras
se tipea, pero nada obliga a elegir de la lista, y sin esto había que
escribir el nombre entero. Sólo cuando UN nombre del catálogo empieza
así — con dos candidatos no adivina, revierte."""


_JS_CANTIDAD_PARSER = JsCode("""
function(p) {
    var crudo = String(p.newValue == null ? '' : p.newValue).trim()
                    .replace(',', '.');
    if (crudo === '') return p.oldValue;
    var n = parseFloat(crudo);
    return (isNaN(n) || n < 0) ? p.oldValue : n;
}
""")
"""`valueParser` de la columna "Cant." editable: la celda devuelve TEXTO y
la comparación del lado del servidor es numérica. Acepta coma decimal
(es lo que tipea alguien acá) y rechaza basura volviendo al valor previo
en vez de mandar un `NaN` que después haya que filtrar."""


_JS_MAESTRO_AL_NAVEGADOR = JsCode("""
function(params) {
 if (window.__sunatMaestroSetLower) return;
 var ctx = params.context || {};
 var nombres = ctx.nombres || [];
 if (!nombres.length) return;
 var dl = document.getElementById('sunat_maestro_datalist');
 if (!dl) {
   dl = document.createElement('datalist');
   dl.id = 'sunat_maestro_datalist';
   document.body.appendChild(dl);
 }
 nombres.forEach(function(nom) {
   var opt = document.createElement('option');
   opt.value = nom;
   dl.appendChild(opt);
 });
 window.__sunatMaestroPorNombre = ctx.porNombre || {};
 window.__sunatMaestroSetLower = new Set(nombres.map(function(nom) {
   return String(nom).trim().toLowerCase();
 }));
}
""")
"""`onGridReady` de la tabla del sistema: arma UNA vez por iframe (guardia
`window.__sunatMaestroSetLower`) las tres cosas que necesita la edición en
celda — el `<datalist>` que alimenta el autocompletado, el set de nombres
válidos que consulta `isCancelAfterEnd`, y el mapa nombre → (código,
unidad) que usa `_JS_RELLENAR_VECINAS`.

El catálogo NO viaja adentro de este código: llega por
`gridOptions.context` (`_lookups_maestro`, que explica por qué — un JSON
grande dentro de un `JsCode` cuesta ~64 segundos de regex por render).
La guardia sale recién al final, con las tres cosas ya armadas: si sale
antes y algo falla en el medio, `isCancelAfterEnd` rechaza todo lo que se
tipee contra un set vacío y la columna queda inutilizable.

`document` acá es el del IFRAME del componente, no el de la app: cada
AgGrid vive en el suyo, por eso el datalist se crea adentro y no con un
`st.markdown` (que además no ejecutaría el script — ver CLAUDE.md)."""


_JS_RELLENAR_VECINAS = JsCode("""
function(e) {
    var campo = e.colDef.field;
    // Se muta `e.data` y se repinta, en vez de `node.setDataValue`: aquel
    // dispara otro `cellValueChanged` por celda, y con
    // `update_on=["cellValueChanged"]` cada uno seria otro viaje al
    // servidor para escribir algo que el servidor ya resuelve solo.
    var tocadas = [];

    if (campo === 'Ítem (sistema)') {
        var m = window.__sunatMaestroPorNombre;
        if (!m) return;
        var t = m[String(e.newValue || '').trim().toLowerCase()];
        if (!t) return;
        e.data['_cod_sis'] = t[0];
        e.data['Und.'] = t[1];
        tocadas.push('Und.');
    } else if (campo === 'Cant.') {
        // El precio unitario se DERIVA del importe, que es el invariante
        // de la homologacion: si el usuario carga 12 unidades donde el
        // proveedor factura 1 caja, cambia el unitario y la linea sigue
        // costando lo mismo. Ver `_precio_derivado`, que hace la misma
        // cuenta en el servidor.
        var imp = e.data['Importe'], c = Number(e.newValue);
        e.data['P. unit.'] = (imp == null || isNaN(imp) || !c || isNaN(c))
            ? null : Math.round((imp / c) * 10000) / 10000;
        tocadas.push('P. unit.');
    } else {
        return;
    }
    e.api.refreshCells({rowNodes: [e.node], columns: tocadas, force: true});
}
""")
"""Lo que se rellena SOLO en el navegador, sin esperar el viaje al
servidor: la unidad de kardex al elegir un ítem, y el precio unitario al
cambiar la cantidad.

Es sólo el adelanto visual — la fuente de verdad sigue siendo el
servidor, que recalcula las dos cosas con `_lookups_maestro` y
`_precio_derivado` y las persiste. Por eso no importa en qué orden corra
esto respecto del handler de st_aggrid: el servidor no lee estas columnas
del payload. Sin el adelanto, la celda de al lado se queda con el valor
viejo los ~3 segundos que tarda la ida y vuelta, y parece que la edición
no hizo nada.

`refreshCells` sólo sobre las columnas tocadas: repintar la fila entera
haría parpadear la celda que el usuario acaba de editar."""


_ALTO_FILA_CONVERSOR = 30
_ALTO_CABECERA_CONVERSOR = 32
"""Alto de fila y de cabecera de las DOS tablas del conversor. Son una
constante compartida y no dos literales porque de ellos depende que las
filas de la izquierda caigan a la MISMA altura que las de la derecha —
que es todo el punto de la vista partida en dos (pedido 2026-08-27: "dos
tarjetas separadas, pero alineadas una con la otra, para que se vea la
idea de comparación"). Si una tabla dibuja filas de 30px y la otra de 34,
la comparación deja de leerse a la tercera fila."""


def _alto_conversor(n_filas):
    """El alto que comparten las dos tablas del conversor. Una función y no
    dos llamadas sueltas a `alturas.por_filas`, por lo mismo que
    `_ALTO_FILA_CONVERSOR`: dos tablas que tienen que alinearse no pueden
    calcular su alto por separado."""
    return alturas.por_filas(n_filas, px_fila=_ALTO_FILA_CONVERSOR,
                             rol=alturas.MINI)


def _titulo_panel(texto, detalle):
    """La cabecera de cada mitad del conversor: de qué fuente es la tabla
    de abajo. Las dos mitades la dibujan IGUAL (mismo markup, mismo alto)
    porque de eso depende que las dos tablas arranquen en la misma `y` —
    ver `_ALTO_FILA_CONVERSOR`."""
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:6px;'
        f'margin:0 0 6px;padding-bottom:4px;'
        f'border-bottom:1px solid {GRIS_BORDE};">'
        f'<span style="font-size:10px;font-weight:700;color:{ACENTO};'
        f'text-transform:uppercase;letter-spacing:.05em;">{texto}</span>'
        f'<span style="font-size:10px;color:{GRIS_TEXTO};">{detalle}</span>'
        f'</div>', unsafe_allow_html=True)


_JS_FORMATO_CANT = JsCode(
    "function(p){ return p.value==null ? '' : "
    "Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:3}); }")
"""Formato de las columnas de cantidad de las DOS tablas. Compartido a
propósito: si un lado redondeara a 2 decimales y el otro a 3, dos números
iguales se verían distintos justo en la vista que existe para
compararlos."""


def _cabecera_conversor(doc):
    """Los datos del documento arriba de CADA mitad del conversor: RUC,
    proveedor, fecha de emisión y moneda.

    Se dibuja dos veces con la MISMA función, y eso no es redundancia: es
    lo que garantiza que las dos cabeceras midan igual y las dos tablas
    arranquen a la misma altura. Una cabecera copiada a mano en cada lado
    se desincroniza en cuanto alguien toque una — es la lección de la
    regla #244, donde 22px de diferencia entre dos encabezados corrieron
    catorce filas.

    Van los mismos datos en las dos porque es EL MISMO documento: la
    tarjeta de la derecha no es otro comprobante, es éste dicho en el
    idioma del almacén. Y son justo los campos que la exportación a XML va
    a necesitar en su cabecera — emisor, fecha y moneda—, así que tenerlos
    a la vista mientras se homologa es ver lo que se va a exportar.
    """
    if doc is None:
        return
    ruc = str(doc.get("ruc_proveedor") or "—")
    prov = _compras_truncar(str(doc.get("proveedor") or ""), 34)
    fecha = pd.to_datetime(doc.get("fecha_emision"), errors="coerce")
    fecha = "—" if pd.isna(fecha) else f"{fecha:%d/%m/%Y}"
    st.markdown(
        f'<div style="display:flex;flex-direction:column;gap:1px;'
        f'padding:6px 9px;margin-bottom:8px;border-radius:8px;'
        f'background:{GRIS_FONDO};line-height:1.35;">'
        f'<div style="font-size:11.5px;color:{TEXTO_PRINCIPAL};'
        f'font-weight:600;white-space:nowrap;overflow:hidden;'
        f'text-overflow:ellipsis;">{prov}</div>'
        f'<div style="font-size:10.5px;color:{GRIS_TEXTO};'
        f'font-variant-numeric:tabular-nums;">'
        f'RUC {ruc} · {fecha} · {sunat._moneda_con_tc(doc)}</div>'
        f'</div>', unsafe_allow_html=True)


def _renglon_total(etiqueta, valor, sim, fuerte=False):
    """Un renglón del pie de totales. Compartido por las dos mitades para
    que los dos pies se vean iguales — mismo argumento que
    `_cabecera_conversor`."""
    peso = "700" if fuerte else "400"
    color = TEXTO_PRINCIPAL if fuerte else GRIS_TEXTO
    tam = "13px" if fuerte else "11.5px"
    borde = f"border-top:1px solid {GRIS_BORDE};padding-top:4px;" if fuerte else ""
    return (f'<div style="display:flex;justify-content:space-between;'
            f'gap:16px;{borde}">'
            f'<span style="color:{color};font-size:{tam};'
            f'font-weight:{peso};">{etiqueta}</span>'
            f'<span style="color:{TEXTO_PRINCIPAL};font-size:{tam};'
            f'font-weight:{peso};font-variant-numeric:tabular-nums;">'
            f'{sim} {valor:,.2f}</span></div>')


def _bloque_totales(renglones):
    """El pie, alineado a la derecha y con el mismo ancho en las dos
    mitades."""
    st.markdown(
        '<div style="display:flex;flex-direction:column;gap:2px;'
        'margin:8px 0 0 auto;max-width:230px;">' + "".join(renglones)
        + '</div>', unsafe_allow_html=True)


def _del_registro(doc, clave):
    """Un importe del registro del SIRE, en la moneda del PAPEL.

    LOS IMPORTES DEL REGISTRO VIENEN EN SOLES —`moneda` dice en qué se
    emitió el comprobante, no en qué están esos números— y las LÍNEAS del
    XML vienen en la moneda del papel. Las dos mitades de esta tarjeta
    comparan una cosa contra la otra, así que hay que traerlas al mismo
    lado: se elige el papel, porque es lo que el usuario tiene delante y
    lo que el Almacén guarda (los importes van en la moneda del documento,
    con su `nCambio` al lado).

    Medido 2026-09-05 sobre la F163-2309 de MAPFRE: el registro declara
    10.733,31 de base y el XML una sola línea de 3.155,00 — el mismo
    número, con el TC 3,402 en el medio. Sin dividir, la tarjeta mostraba
    dos monedas distintas con el mismo símbolo, avisaba de un descuadre
    que no existía y sumaba dólares con soles en «TOTAL a cargar». Ver
    `sunat.en_moneda_del_papel` y la regla #313.
    """
    v = _num(doc.get(clave))
    if v is None:
        return None
    return sunat.en_moneda_del_papel(doc, v) or v


def _pie_sistema(doc, filas_sistema):
    """El pie de la mitad DERECHA: los totales con los que el documento
    entraría al sistema de almacén.

    No copia los del comprobante: los SUMA de las líneas homologadas. Por
    construcción tienen que dar lo mismo —el importe de cada línea es el
    invariante de la homologación (regla #249)— y justamente por eso vale
    la pena calcularlo: si alguna vez no diera, sería porque una línea
    perdió su importe, y eso hay que verlo ANTES de exportar el XML, no
    después de importarlo al almacén.

    El IGV y la composición gravado/no gravado salen del documento: la
    homologación cambia el grano de las líneas, no la naturaleza
    tributaria de la compra. Verificado sobre los 16.689 comprobantes del
    registro: `total == base + no gravado + IGV` en TODOS, sin ISC ni
    ICBPER de por medio, así que sumar líneas + IGV reconstruye el total
    sin términos escondidos.
    """
    if doc is None:
        return
    mon = str(doc.get("moneda") or "PEN")
    sim = sunat.simbolo_moneda(mon)
    resta = any(k in str(doc.get("tipo_nombre") or "").lower()
                for k in ("crédito", "credito", "débito", "debito"))
    _s = abs if resta else (lambda v: v)

    suma = sum(v for v in (_num(f.get("Importe")) for f in filas_sistema)
               if v is not None)
    igv = _s(_del_registro(doc, "igv") or 0.0)
    total = suma + igv

    _bloque_totales([
        _renglon_total("Suma de líneas", suma, sim),
        _renglon_total("IGV", igv, sim),
        _renglon_total("TOTAL a cargar", total, sim, fuerte=True),
    ])

    declarado = _del_registro(doc, "total")
    if declarado is not None and abs(total - _s(declarado)) > _TOLERANCIA_CENTAVOS:
        st.caption(f"⚠ No cuadra con el comprobante, que declara "
                   f"{sim} {_s(declarado):,.2f}. Revisá antes de exportar.")


def _pie_comprobante(doc, lineas, totales=None):
    """El pie del comprobante: los subtotales que componen el total, como
    los imprime cualquier factura.

    A pedido 2026-08-28, junto con las columnas de precio e importe: la
    mitad izquierda del conversor tenía que poder leerse como el
    documento, y un documento no termina en su última línea — termina en
    sus impuestos.

    LAS CIFRAS SALEN DEL REGISTRO, NO DE SUMAR LAS LÍNEAS. Son el dato que
    SUNAT tiene anotado, que es contra lo que se compara el sistema; las
    líneas vienen del XML, que es otra fuente. Verificado sobre los
    documentos reales del rango que las dos cuadran (`suma de importes ==
    base gravada + no gravado`, exacto en los ocho que se probaron,
    incluidos los cuatro que son 100 % no gravado). Pero **cuadrar no está
    garantizado**: un XML que llegue incompleto daría una suma menor sin
    ningún error visible, así que si difieren más que la tolerancia se
    avisa en vez de elegir en silencio cuál de las dos mostrar.

    Las filas en cero no se dibujan, salvo el IGV: un «IGV 0.00» explícito
    es información en una compra exonerada —dice que no hay crédito fiscal
    que tomar— mientras que un «No gravado 0.00» sólo gasta un renglón.
    Medido: 111 de 307 comprobantes del rango tienen no gravado ≠ 0, o sea
    que la fila aparece en un tercio de los casos y en los otros dos
    tercios estorbaría.
    """
    mon = str(doc.get("moneda") or "PEN")
    sim = sunat.simbolo_moneda(mon)
    # Una NOTA se imprime en positivo y el registro la guarda en negativo,
    # porque RESTA del período (ver `sunat.py`). Acá manda el papel: este
    # panel dice ser «el original del proveedor», y en el original de una
    # nota de crédito de S/ 2.203 dice 2.203, no -2.203. El signo se
    # explica con una línea de texto, que es más claro que un menos.
    resta = any(k in str(doc.get("tipo_nombre") or "").lower()
                for k in ("crédito", "credito", "débito", "debito"))
    _s = (lambda v: abs(v)) if resta else (lambda v: v)
    # En la moneda del PAPEL: el registro los guarda en soles y esta mitad
    # dice ser el comprobante del proveedor. Ver `_del_registro`.
    grav = _s(_del_registro(doc, "base_imponible") or 0.0)
    ngrav = _s(_del_registro(doc, "no_gravado") or 0.0)
    igv = _s(_del_registro(doc, "igv") or 0.0)
    total = _del_registro(doc, "total")
    total = None if total is None else _s(total)

    filas = []
    if grav:
        filas.append(("Gravado", grav, False))
    if ngrav:
        filas.append(("No gravado", ngrav, False))
    filas.append(("IGV", igv, False))
    if total is not None:
        filas.append(("TOTAL", total, True))

    _bloque_totales([_renglon_total(e, v, sim, f) for e, v, f in filas])

    if resta:
        st.markdown(
            f'<div style="text-align:right;font-size:10.5px;'
            f'color:{ADVERTENCIA_TEXTO};">'
            f'{doc.get("tipo_nombre", "Nota")}: RESTA del total del período'
            f'</div>', unsafe_allow_html=True)

    # El mismo total en SOLES, sólo si el comprobante se emitió en otra
    # moneda: 647 de los 16.689 del registro. Es el número con el que el
    # documento entra a la contabilidad —y el que trae el registro— así
    # que sale del dato, no de multiplicar de nuevo.
    _crudo = _num(doc.get("total"))
    if mon.strip().upper() != "PEN" and _crudo is not None:
        st.markdown(
            f'<div style="text-align:right;font-size:10.5px;'
            f'color:{GRIS_TEXTO_SUAVE};">= S/ {abs(_crudo) if resta else _crudo:,.2f} '
            f'en el registro · TC {float(doc.get("tipo_cambio") or 1.0):.3f}</div>',
            unsafe_allow_html=True)

    # EL REDONDEO DEL PAPEL. El registro del SIRE anota la aritmética
    # (base + IGV); el comprobante puede cobrar otra cosa: el retail trunca
    # el total al múltiplo de 0.10 —F402-358580 de WONG: 34.73 + 6.26 =
    # 40.99 y el `PayableAmount` dice **40.90**—. Sin este renglón la
    # pantalla mostraba 40.99, el Almacén recibía 40.90, y la diferencia no
    # se podía explicar mirando la app. Lo que se carga es lo del papel
    # (ver `sunat_importacion.redondeo_derivado`).
    # El techo es el MISMO que decide si el redondeo se manda al Almacén
    # (`REDONDEO_MAXIMO`): un renglón que llame "redondeo" a una
    # diferencia que la importación no va a tratar como tal se contradice
    # con lo que pasa al apretar el botón. Por encima del techo no hay
    # redondeo que explicar — hay un descuadre, y se dice así.
    import sunat_importacion as _simp

    pagable = _num((totales or {}).get("total"))
    _dif = (None if pagable is None or total is None
            else round(abs(pagable) - abs(total), 2))
    if _dif and abs(_dif) <= _simp.REDONDEO_MAXIMO + 1e-9:
        st.caption(f"El comprobante redondea el total a {sim} "
                   f"{abs(pagable):,.2f} ({_dif:+.2f}); SUNAT anota "
                   f"{sim} {abs(total):,.2f}. Se carga lo del comprobante.")
    elif _dif:
        st.caption(f"⚠ El comprobante declara {sim} {abs(pagable):,.2f} y "
                   f"el registro {sim} {abs(total):,.2f} "
                   f"({_dif:+,.2f}). Revisá antes de importar: el Almacén "
                   f"rechaza lo que no cuadra.")

    # La red de seguridad: si el XML no suma lo que el registro declara,
    # decirlo. No se corrige nada — son dos fuentes y la del registro es
    # la que manda para el cruce.
    # Se comparan MAGNITUDES: en una nota, el XML viene positivo y el
    # registro negativo, y compararlos con signo hacía saltar el aviso en
    # las 294 notas de crédito del registro — un aviso que grita en un
    # caso normal se deja de leer. Medido sobre 37 documentos con XML: sin
    # `abs`, 3 no cuadraban y una era esto; con `abs`, quedan las 2 reales.
    suma = sum(v for v in (_num(x.get("importe")) for x in lineas)
               if v is not None)
    if abs(abs(suma) - abs(grav + ngrav)) > _TOLERANCIA_CENTAVOS:
        st.caption(f"⚠ Las líneas del XML suman {sim} {suma:,.2f} y el "
                   f"registro declara {sim} {grav + ngrav:,.2f}. Se muestra "
                   "lo del registro, que es contra lo que se compara el "
                   "sistema.")


_JS_IMPORTE_XML = JsCode(
    "function(p){ return p.value==null || isNaN(p.value) ? '' : "
    "Number(p.value).toLocaleString('es-PE',"
    "{minimumFractionDigits:2, maximumFractionDigits:2}); }")
"""Precio e importe del comprobante: dos decimales y SIN símbolo de
moneda. El símbolo lo pone una sola vez el pie (`_pie_comprobante`), que
es donde el documento declara en qué moneda está — repetirlo en cada
celda de una tabla de once líneas es ruido, y es como se imprime
cualquier factura."""


def _grid_lado_sunat(tv, doc_id):
    """La tabla IZQUIERDA: el comprobante tal como lo emitió el proveedor,
    leído COMO UN DOCUMENTO y no como un listado de nombres.

    Desde el 2026-08-28 trae las cinco columnas que tiene una factura
    impresa —código del proveedor, ítem, cantidad con su unidad, precio
    unitario e importe— y debajo el pie con los subtotales
    (`_pie_comprobante`). A pedido: el usuario quería poder mirar esta
    mitad y reconocer el papel, no sólo los ítems a mapear.

    Dos compresiones para que las cinco entren sin scroll horizontal en
    media tarjeta (~435px útiles a 1360 de ancho): la unidad viaja dentro
    de la cantidad («0.73 kg», que es como se imprime) y el símbolo de
    moneda no se repite por celda, lo declara el pie una sola vez.
    Medido en el navegador a 1360 de ancho: la mitad da 422px útiles y
    las cinco columnas suman 406 de mínimo (66+118+74+72+76), así que
    entran y `flex` en «Ítem» absorbe lo que sobra. El primer intento
    sumaba 452 y scrolleaba — un documento que hay que arrastrar para
    leerle el importe no es un documento.

    De sólo lectura y sin `update_on` — no tiene por qué provocar ni un
    viaje al servidor mientras se corrige la de al lado.
    """
    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=False, filter=False,
                                editable=False, suppressMovable=True)
    # Angosta y con tooltip: es un código de 14 dígitos que nadie lee
    # entero, sirve para RECONOCER que dos líneas son el mismo producto
    # (las cuatro de «FG LOMO FINO» del documento de prueba comparten
    # `00000000652940`). Recortado cumple esa función y deja el ancho para
    # las tres columnas de plata.
    gb.configure_column("Código prov.", width=78, minWidth=66,
                        tooltipField="Código prov.",
                        cellStyle={"color": GRIS_TEXTO_SUAVE})
    gb.configure_column("Ítem (XML)", minWidth=118, flex=1,
                        tooltipField="Ítem (XML)")
    # `Cant.` ya viene armada como texto ("0.73 kg"), así que NO lleva
    # `numericColumn` ni formatter: alinearla a la derecha como número
    # dejaría la unidad pegada al borde.
    gb.configure_column("Cant.", width=80, minWidth=74,
                        cellStyle={"text-align": "right"})
    gb.configure_column("P. unit.", type=["numericColumn"], width=78,
                        minWidth=72, valueFormatter=_JS_IMPORTE_XML)
    gb.configure_column("Importe", type=["numericColumn"], width=84,
                        minWidth=76, valueFormatter=_JS_IMPORTE_XML)
    gb.configure_grid_options(
        rowHeight=_ALTO_FILA_CONVERSOR, headerHeight=_ALTO_CABECERA_CONVERSOR,
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
        suppressColumnVirtualisation=True,
    )
    AgGrid(
        tv, gridOptions=gb.build(), height=_alto_conversor(len(tv)),
        # `marco=False`: la tabla NO lleva borde/radio/sombra propios — ya
        # los pone la mitad que la contiene (`sunat_conv_izq`/`_der` en
        # estilos/_80_cards.py). Con los dos marcos se veían dos líneas de
        # 1px con el mismo radio a diez píxeles una de otra.
        theme="material", custom_css=dict(_css_grid(12, marco=False)),
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        update_on=[], data_return_mode=DataReturnMode.AS_INPUT,
        key=f"sunat_conv_sunat_{doc_id}",
    )


_JS_PRECIO_DERIVADO = JsCode(
    "function(p){ return p.value==null || isNaN(p.value) ? '—' : "
    "Number(p.value).toLocaleString('es-PE',"
    "{minimumFractionDigits:2, maximumFractionDigits:4}); }")
"""El precio derivado se muestra con 2 a 4 decimales: los dos primeros
siempre, y los otros dos sólo si hacen falta. Un unitario de caja partida
(126.27 ÷ 12 = 10.5225) necesita los cuatro para que al re-multiplicar
vuelva a dar el importe; uno normal (63.47) no, y mostrarle dos ceros
sería ruido. La raya cuando no hay cantidad con la que dividir —ver
`_precio_derivado`— dice que falta un dato, no que el precio sea cero."""


def _precio_derivado(importe, cantidad):
    """El precio unitario con el que la línea entra al almacén.

    NO se copia el del comprobante: se DERIVA, porque la cantidad puede
    cambiar en la homologación y el importe no. El proveedor factura una
    caja de 12 a S/ 126.27; el almacén la ingresa como 12 unidades, y
    entonces el unitario es 10.5225 — pero la línea sigue costando
    S/ 126.27 y los impuestos del documento no se mueven.

    Cuatro decimales y no dos: con dos, 126.27/12 = 10.52 y al
    re-multiplicar da 126.24, o sea que el documento dejaría de cuadrar
    por tres centavos. Es la misma precisión con la que vienen los
    unitarios del XML (verificado: `126.2712`, `5.0847`, `19.9153`).

    `None` si no se puede dividir — una cantidad en cero es un dato que
    hay que corregir, no un precio infinito.
    """
    if importe is None or cantidad is None:
        return None
    try:
        return None if abs(cantidad) < 1e-9 else round(importe / cantidad, 4)
    except (TypeError, ZeroDivisionError):
        return None


def _grid_lado_sistema(tv, doc_id):
    """La tabla DERECHA: el documento HOMOLOGADO, o sea con qué se va a
    cargar al sistema de almacén.

    Es la misma factura de la izquierda dicha en el idioma del ERP, y por
    eso tiene las mismas columnas de plata: ítem, unidad, cantidad,
    precio unitario e importe. Lo que cambia es de dónde sale cada una:

      · **Ítem** — EDITABLE, contra el maestro de artículos
        (`_JS_EDITOR_PRODUCTO`). Es el único campo que el usuario elige.
      · **Und.** — la trae el producto elegido: es su unidad de KARDEX,
        no la del comprobante. No se edita — cambiarla a mano sería
        decirle al almacén que un kilo es una unidad.
      · **Cant.** — EDITABLE. Arranca igual a la del comprobante y se
        pisa cuando el grano no coincide: el proveedor factura 1 caja de
        12 y el almacén ingresa 12 unidades.
      · **P. unit.** — NO se edita: se DERIVA (`_precio_derivado`). Si la
        cantidad pasa de 1 a 12, el unitario pasa de 126.27 a 10.5225.
      · **Importe** — el INVARIANTE. Se copia del comprobante y no se
        toca, y por eso tampoco se mueven los impuestos ni el total del
        documento. Es la regla que hace que la homologación sea segura:
        se puede cambiar el grano sin cambiar la plata.

    El ORIGEN del emparejamiento dejó de ser columna (2026-08-28): son
    120px en una mitad de 422 que ahora lleva también precio e importe, y
    de un vistazo lo único que hace falta ver es SI hay que revisar la
    fila — eso lo dice el ámbar del ítem. El detalle y el código del
    sistema van al tooltip.

    Devuelve la respuesta de AgGrid para que el llamador vea qué cambió;
    ver `_detalle_sistema`.
    """
    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=False, filter=False,
                                editable=False, suppressMovable=True)
    for oculta in ("_idx", "_cod_auto", "_cant_xml", "_cod_sis", "_origen"):
        gb.configure_column(oculta, hide=True)
    # LAS DOS columnas editables -- ver el docstring de `_detalle_sistema`.
    # El tinte lavanda es la misma señal visual de "interactivo" que usa el
    # resto de la app (`_ficha_html`, la barra de TOTAL), acá marcando
    # "esta celda se puede tocar".
    # El ORIGEN del emparejamiento ya no es columna: es el color del ítem
    # y su tooltip. Costaba 120px en una mitad de 422 que ahora tiene que
    # llevar también precio e importe, y lo único que hace falta ver de un
    # vistazo es SI hay que revisar esa fila — ámbar cuando sí. El detalle
    # («Sugerido», «Corregido»…) y el código del sistema van al tooltip,
    # que es donde se mira de a una fila.
    gb.configure_column(
        "Ítem (sistema)", minWidth=110, flex=1, editable=True,
        cellEditor=_JS_EDITOR_PRODUCTO,
        tooltipValueGetter=JsCode(
            "function(p){ var d=p.data||{}; return (d._origen||'') + "
            "(d._cod_sis ? '  ·  cód. ' + d._cod_sis : ''); }"),
        cellStyle=JsCode(
            "function(p){ var base={'background':'%s','cursor':'text'};"
            " var o=(p.data||{})._origen;"
            " if (o==='Sugerido' || o==='Sin coincidencia') {"
            "   base.color='%s'; base.fontWeight='600'; }"
            " else if (o==='Corregido') { base.color='%s'; }"
            " return base; }"
            % (LAVANDA_FONDO, ADVERTENCIA_TEXTO, ACENTO_TEXTO)))
    # La unidad la manda el MAESTRO, no el comprobante: es la de kardex
    # del producto elegido, así que cambia sola al cambiar el ítem y no
    # se edita a mano.
    gb.configure_column("Und.", width=62, minWidth=56,
                        headerTooltip="Unidad de kardex del sistema. La trae "
                                      "el producto elegido; no se edita.",
                        cellStyle={"color": GRIS_TEXTO})
    # La cantidad arranca igual a la del comprobante y se puede pisar. Se
    # marca con el acento cuando difiere: es la unica senal de que ese
    # numero ya no es el que dice SUNAT.
    gb.configure_column(
        "Cant.", type=["numericColumn"], width=72, minWidth=66, editable=True,
        valueFormatter=_JS_FORMATO_CANT, valueParser=_JS_CANTIDAD_PARSER,
        cellStyle=JsCode(
            "function(p){ var base = {'background': '%s', 'cursor': 'text'};"
            " if (p.data && p.value != null && p.data._cant_xml != null"
            "     && Math.abs(p.value - p.data._cant_xml) > 1e-6) {"
            "   base.color = '%s'; base.fontWeight = '600'; }"
            " return base; }" % (LAVANDA_FONDO, ACENTO_TEXTO)))
    # Precio DERIVADO: no se edita, se calcula (`_precio_derivado`). Va en
    # gris para que se lea como lo que es — un resultado, no un campo.
    gb.configure_column(
        "P. unit.", type=["numericColumn"], width=76, minWidth=70,
        headerTooltip="Se calcula solo: importe ÷ cantidad. Al cambiar la "
                      "cantidad, cambia el unitario y el importe queda igual.",
        valueFormatter=_JS_PRECIO_DERIVADO,
        cellStyle={"color": GRIS_TEXTO})
    # El IMPORTE es el invariante: se copia del comprobante y no se toca.
    # Por eso NO lleva el tinte lavanda de "editable" ni marca de cambio.
    gb.configure_column(
        "Importe", type=["numericColumn"], width=82, minWidth=76,
        headerTooltip="Lo que costó la línea según el comprobante. No "
                      "cambia con la homologación — tampoco los impuestos.",
        valueFormatter=_JS_IMPORTE_XML)
    # `singleClickEdit` + `stopEditingWhenCellsLoseFocus`: un clic entra a
    # editar y clickear afuera confirma, como una celda de Excel -- sin
    # esto haría falta doble clic y Enter.
    gb.configure_grid_options(
        rowHeight=_ALTO_FILA_CONVERSOR, headerHeight=_ALTO_CABECERA_CONVERSOR,
        singleClickEdit=True, stopEditingWhenCellsLoseFocus=True,
        context=_lookups_maestro()[2],
        onGridReady=_JS_MAESTRO_AL_NAVEGADOR,
        onCellValueChanged=_JS_RELLENAR_VECINAS,
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
        # Esta tabla vive en media tarjeta, con más columnas de las que
        # entran sin scroll horizontal -- eso es esperable (mismo criterio
        # que `_tabla_cruce`). Lo que NO conviene es la virtualización de
        # columnas por defecto: con el marco angosto, deja sin nodo DOM a
        # "Ítem (sistema)" hasta que alguien scrollea hasta ahí, y esa es
        # justo la columna editable. Ocho columnas es nada para el
        # navegador — desactivarla cuesta cero acá y evita esa sorpresa.
        suppressColumnVirtualisation=True,
    )
    # Key con el documento adentro: sin esto, AG Grid retiene estado del
    # lado del cliente al cambiar de documento -- antes fue la fila
    # seleccionada y reventó en vivo con menos líneas que el documento
    # anterior (IndexError, ver arquitectura.md regla #224); con edición en
    # celda el mismo riesgo aplica igual. Con la key distinta, AG Grid
    # monta un componente nuevo por documento y arranca limpio.
    return AgGrid(
        tv, gridOptions=gb.build(), height=_alto_conversor(len(tv)),
        # `marco=False`: la tabla NO lleva borde/radio/sombra propios — ya
        # los pone la mitad que la contiene (`sunat_conv_izq`/`_der` en
        # estilos/_80_cards.py). Con los dos marcos se veían dos líneas de
        # 1px con el mismo radio a diez píxeles una de otra.
        theme="material", custom_css=dict(_css_grid(12, marco=False)),
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        update_on=["cellValueChanged"],
        data_return_mode=DataReturnMode.AS_INPUT,
        # `server_wins` y no el `client_wins` por defecto: sin esto, "after
        # first edit, grid ignores server data updates" (docstring de
        # st_aggrid). Era el bug reportado el 2026-08-27 con captura --
        # se elegía el ítem y "Código"/"Und. kardex"/"Origen" se quedaban
        # vacíos y en "Sin coincidencia" para siempre, porque el navegador
        # descartaba en silencio la fila ya resuelta que mandaba el
        # servidor. Acá el servidor ES la fuente de verdad: guarda la
        # corrección en R2 y recién entonces redibuja.
        server_sync_strategy="server_wins",
        key=f"sunat_conv_sistema_{doc_id}",
    )


def _num(v):
    """`v` como float, o None si no se puede. Los valores que vuelven de
    AgGrid pueden ser texto, número o NaN según por dónde pasaron."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else f


def _misma_cantidad(a, b):
    """Dos cantidades son "la misma" hasta el sexto decimal. Comparar
    floats por `==` acá haría que un ida y vuelta por JSON marcara como
    cambio algo que el usuario no tocó."""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= 1e-6


@st.fragment
def _bloque_importar(doc, lineas_xml, filas_sistema, xml_original):
    """El botón que manda el documento al Almacén, y en qué estado está.

    NO escribe en SQL Server: la webapp corre en Streamlit Cloud y el
    Almacén vive detrás de la VPN, en el restaurante. Deja una señal en R2
    y del otro lado un servicio la levanta cada 5 segundos y graba con los
    mismos procedimientos que usa el formulario. El mismo mecanismo que
    ya se usa para refrescar un reporte y para pedir el original a SUNAT
    — ver `sunat_importacion`.

    TRES ESTADOS, y el del medio es el que hace falta que exista: entre
    apretar y que el documento aparezca pasan segundos, y sin un "en
    curso" visible el usuario aprieta de nuevo.
    """
    import sunat_importacion as simp

    st.divider()

    recibo = simp.recibo_importacion(doc)
    pendiente = simp.importacion_pendiente(doc)

    if pendiente:
        st.info("Enviado al Almacén — esperando a que el servidor lo grabe. "
                "Suele tardar unos segundos.")
        if st.button("Actualizar", key="sunat_imp_refrescar", type="tertiary"):
            st.rerun(scope="fragment")
        return

    if recibo and recibo.get("ok"):
        st.success(
            f"Cargado en el Almacén como **{recibo['correlativo']}** — "
            f"{recibo.get('lineas', '?')} línea(s), total {recibo.get('total', '?')}. "
            f"Queda en estado GENERADO: no mueve stock hasta que alguien "
            f"lo revise y lo procese.")
        for aviso in recibo.get("avisos", []):
            st.caption(f"· {aviso}")
    elif recibo:
        # El importador rechaza el documento cuando su aritmética no cierra.
        # Se muestra el motivo tal cual: está escrito para leerse acá.
        st.error(f"El Almacén no lo aceptó: {recibo.get('error')}")

    sin_mapear = sum(1 for f in filas_sistema
                     if not str(f.get("_cod_sis") or "").strip())
    if sin_mapear:
        st.warning(f"Faltan {sin_mapear} línea(s) por asignarle producto. "
                   f"Se completan arriba, en «Ítem (sistema)».")
        return

    etiqueta = "Reintentar la importación" if recibo else "Importar al Almacén"
    if st.button(etiqueta, key="sunat_imp_enviar", type="primary"):
        totales = sunat.totales_xml(xml_original) if xml_original else None
        ok, mensaje = simp.solicitar_importacion(
            doc, lineas_xml, filas_sistema, totales)
        if ok:
            st.rerun(scope="fragment")
        else:
            st.error(mensaje)


def _detalle_sistema(doc, lineas_xml, d, xml_original=None):
    """El cuerpo de la tarjeta «Conversor SUNAT-Sistema»
    (`_card_conversor_sistema`): a la IZQUIERDA el comprobante del
    proveedor, a la DERECHA con qué se va a cargar al sistema — código,
    nombre y unidad de KARDEX del maestro de artículos
    (`_maestro_productos`) más la cantidad, editables EN LA PROPIA CELDA.

    DOS TABLAS, FILA CONTRA FILA (pedido 2026-08-27). Hasta esa mañana era
    una sola tabla de 8 columnas: se leía como una planilla, no como una
    comparación. Ahora cada lado es su propia tarjeta y la fila `i` de una
    cae a la misma altura que la fila `i` de la otra — eso NO es
    automático, sale de que las dos compartan alto de fila, de cabecera y
    de tabla (`_ALTO_FILA_CONVERSOR`, `_alto_conversor`) y de que las dos
    cabeceras se dibujen con el mismo markup (`_titulo_panel`).

    DOS FUENTES según si el documento YA ESTÁ REGISTRADO (tiene líneas en
    `compras.parquet`, `_lineas_parquet_del_documento`) o todavía no
    («Pendiente» en SUNAT, sin ninguna compra cargada):
      · Registrado: el emparejamiento sale de cruzar contra ESAS líneas
        (`_parear_lineas_sistema`) — es lo único que sabe qué se cargó de
        verdad para este documento puntual. Origen "Automático".
      · Sin registrar: no hay nada de `compras.parquet` con qué cruzar,
        así que se SUGIERE directo contra el maestro completo por
        similitud de nombre (`_sugerir_desde_maestro`). Origen
        "Sugerido" — es una suposición sin ninguna compra real que la
        respalde, por eso comparte el color ámbar de "revisar" con "Sin
        coincidencia" en vez del neutro de "Automático".
    En los dos casos, una vez que hay un CÓDIGO (automático, sugerido o
    corregido a mano), el NOMBRE y la UNIDAD que se muestran salen
    SIEMPRE del maestro — no de `compras.parquet`, cuya unidad es la de
    esa compra puntual, no la de kardex.

    DOS COSAS EDITABLES, y las dos se guardan igual (una anotación en R2
    sobre ESTE documento, ver `sunat.correcciones_lineas`):
      · «Ítem (sistema)» — con el cell editor `_JS_EDITOR_PRODUCTO` (ver
        su docstring sobre por qué no es `agRichSelectCellEditor`).
        Vaciar la celda vuelve la línea a lo automático.
      · «Cant.» — arranca igual a la del comprobante y se puede pisar
        (pedido 2026-08-27). Volver al número del XML borra la anotación
        en vez de guardar el mismo valor.
    Al confirmar una celda, `update_on=["cellValueChanged"]` hace que
    Streamlit rerunee con el valor nuevo en `resp.data` — se compara fila
    a fila contra `tv` (lo que se mandó) por `_idx` para encontrar QUÉ
    cambió, y se guarda. Si lo elegido es lo MISMO que ya salía solo, no
    se guarda una corrección redundante — y si había una vieja que ahora
    vuelve a coincidir, se borra en vez de dejarla pisando algo que
    saldría igual sin ella.

    ES UN FRAGMENT, y eso es lo que arregla la lentitud que se reportó el
    2026-08-27 ("cuando corrijo o agrego un ítem se cuelga y se pone
    lento"). Cada celda confirmada disparaba DOS reruns de la app entera
    —uno del widget, otro del `st.rerun()` de después de guardar—, y la
    app entera acá incluye la consulta al SIRE, el render del PDF a PNG y
    todas las secciones de la pila que el usuario ya hubiera visitado.
    Adentro de un fragment, una corrección re-corre esto y nada más; el
    `st.rerun(scope="fragment")` del final tampoco escala. Ver
    `arquitectura.md` regla #211 para el reverso de esto (un
    `rerun(scope="app")` al TOPE de un fragment sí le borra el estado a
    sus widgets — acá va al final, con las dos tablas ya dibujadas).

    Ni esto ni la comparación tocan `compras.parquet` ni el maestro — son
    de solo lectura acá, los arma un ETL aparte; la corrección es una
    anotación de la webapp sobre ESE documento puntual, no un cambio al
    dato de origen.
    """
    filas_pq = _lineas_parquet_del_documento(d, doc)
    correcciones = sunat.correcciones_lineas(doc)
    por_codigo, por_nombre, _ = _lookups_maestro()

    registrado = not filas_pq.empty
    if registrado:
        asignado = _parear_lineas_sistema(lineas_xml, filas_pq)
        codigos_auto = [None if j is None
                        else str(filas_pq.iloc[j]["COD_PRODUCTO"])
                        for j in asignado]
        _origen_auto = "Automático"
    else:
        codigos_auto = _sugerir_desde_maestro(lineas_xml)
        _origen_auto = "Sugerido"

    if registrado:
        st.caption("Documento registrado: los ítems salen de cruzar "
                   "contra lo que ya está cargado en `compras.parquet`.")
    else:
        st.info("Este documento todavía no está cargado en el sistema — "
                "SUNAT lo ve, pero sigue «Pendiente». Los ítems de abajo "
                "son SUGERENCIAS por nombre contra el maestro de "
                "artículos, sin ninguna compra registrada que las "
                "confirme.")

    filas_sunat, filas_sistema = [], []
    for i, xml_l in enumerate(lineas_xml):
        correccion = correcciones.get(i) or {}
        cod_auto = codigos_auto[i] if i < len(codigos_auto) else None
        if correccion.get("cod_producto"):
            cod_sis = str(correccion["cod_producto"])
            origen = "Corregido"
            _respaldo = correccion.get("nombre_producto", "")
        elif cod_auto is not None:
            cod_sis, origen, _respaldo = cod_auto, _origen_auto, ""
        else:
            cod_sis, origen, _respaldo = "", "Sin coincidencia", ""
        # Del maestro sale nombre Y unidad; si el código no está ahí (no
        # debería pasar), al menos no se pierde el nombre que ya se tenía.
        nom_sis, uni_sis = por_codigo.get(cod_sis, (_respaldo, ""))

        cant_xml = _num(xml_l.get("cantidad"))
        cant_cor = _num(correccion.get("cantidad"))
        # La UNIDAD viaja pegada a la cantidad ("0.73 kg") y no en columna
        # propia: es como se lee en cualquier comprobante, y libera los
        # ~48px que necesitan «P. unit.» e «Importe» para entrar sin
        # scroll horizontal en la mitad de la tarjeta.
        _u = str(xml_l.get("unidad") or "").strip()
        filas_sunat.append({
            "Código prov.": xml_l.get("codigo", ""),
            "Ítem (XML)": xml_l.get("descripcion", ""),
            "Cant.": (f"{cant_xml:,.3f}".rstrip("0").rstrip(".")
                      + (f" {_u}" if _u else "")) if cant_xml is not None else "",
            "P. unit.": _num(xml_l.get("precio_unitario")),
            "Importe": _num(xml_l.get("importe")),
        })
        # EL IMPORTE DE LA LÍNEA ES EL INVARIANTE de la homologación: el
        # proveedor factura 1 caja de 12 y el almacén la ingresa como 12
        # unidades, así que cambian la cantidad y el precio unitario —
        # pero lo que se pagó por esa línea, y por lo tanto los impuestos
        # y el total del documento, no. Ver `_grid_lado_sistema`.
        _imp = _num(xml_l.get("importe"))
        _cant_sis = cant_xml if cant_cor is None else cant_cor
        filas_sistema.append({
            "_idx": i,
            "_cod_auto": cod_auto or "",
            "_cant_xml": cant_xml,
            "_cod_sis": cod_sis,
            "_origen": origen,
            "Ítem (sistema)": nom_sis,
            "Und.": uni_sis,
            "Cant.": _cant_sis,
            "P. unit.": _precio_derivado(_imp, _cant_sis),
            "Importe": _imp,
        })

    tv_sunat = pd.DataFrame(filas_sunat)
    tv = pd.DataFrame(filas_sistema)
    _doc_id = str(doc.get("documento") or "")
    totales_doc = sunat.totales_xml(xml_original) if xml_original else None

    # columnas-internas: las dos mitades de la comparación, mitad y mitad
    # a propósito -- ninguna de las dos fuentes manda sobre la otra.
    c_izq, c_der = st.columns(2, gap="small")
    with c_izq:
        with st.container(border=True, key="sunat_conv_izq"):
            _titulo_panel("Comprobante SUNAT", "lo que emitió el proveedor")
            _cabecera_conversor(doc)
            _grid_lado_sunat(tv_sunat, _doc_id)
            _pie_comprobante(doc, lineas_xml, totales_doc)
    with c_der:
        with st.container(border=True, key="sunat_conv_der"):
            _titulo_panel("Sistema", "con qué se carga")
            _cabecera_conversor(doc)
            resp = _grid_lado_sistema(tv, _doc_id)
            _pie_sistema(doc, filas_sistema)

    st.caption("Clic en «Ítem (sistema)» para corregirlo — el buscador "
               "sugiere mientras escribís, contra el catálogo completo. "
               "«Cant.» arranca con la del comprobante y también se edita; "
               "vaciar el ítem vuelve la línea a lo automático.")

    _bloque_importar(doc, lineas_xml, filas_sistema, xml_original)

    # ¿Cambió algo? Comparar lo que volvió (`resp.data`) contra lo que se
    # mandó (`tv`), fila a fila por `_idx` -- no por posición, para no
    # depender de que el orden se mantenga igual. Se juntan TODAS las
    # escrituras y recién al final se rerunea una sola vez: con dos
    # columnas editables, rerunear adentro del bucle dejaría el segundo
    # cambio sin guardar.
    devuelto = resp.data
    if devuelto is None or len(devuelto) == 0:
        return
    guardado, fallo = False, False
    for _, fila in devuelto.iterrows():
        try:
            i = int(fila["_idx"])
        except (TypeError, ValueError):
            continue
        if i < 0 or i >= len(lineas_xml):
            continue          # ver regla #224: fila de un documento viejo
        anterior = tv.loc[tv["_idx"] == i]
        if anterior.empty:
            continue
        anterior = anterior.iloc[0]

        # ── el ítem del sistema ────────────────────────────────────────
        nuevo_nombre = str(fila.get("Ítem (sistema)") or "").strip()
        if nuevo_nombre != str(anterior["Ítem (sistema)"]).strip():
            cod_nuevo = por_nombre.get(nuevo_nombre.lower())
            if not nuevo_nombre or cod_nuevo == str(anterior["_cod_auto"]):
                # Vaciar la celda, o volver a lo que ya sugería solo: la
                # corrección guardada (si había) deja de hacer falta.
                if (correcciones.get(i) or {}).get("cod_producto"):
                    guardado |= sunat.quitar_correccion_linea(doc, i)
            elif cod_nuevo is None:
                # El editor ya rechaza esto del lado del navegador
                # (`isCancelAfterEnd`) -- si igual llega acá es que algo
                # puenteó la UI. No se guarda cualquier cosa como si fuera
                # un código real; se avisa y se vuelve al último válido.
                st.warning(f"«{nuevo_nombre}» no es un producto del maestro "
                           "— no se guardó. Elegí una sugerencia de la lista.")
                guardado = True
            elif sunat.guardar_correccion_linea(doc, i, cod_nuevo, nuevo_nombre):
                guardado = True
            else:
                fallo = True

        # ── la cantidad ────────────────────────────────────────────────
        nueva_cant = _num(fila.get("Cant."))
        if nueva_cant is not None and not _misma_cantidad(
                nueva_cant, _num(anterior["Cant."])):
            if _misma_cantidad(nueva_cant, _num(anterior["_cant_xml"])):
                guardado |= sunat.quitar_cantidad_linea(doc, i)
            elif sunat.guardar_cantidad_linea(doc, i, nueva_cant):
                guardado = True
            else:
                fallo = True

    if fallo:
        st.error("No se pudo guardar. ¿Están las credenciales de R2 "
                 "configuradas?")
    elif guardado:
        # `scope="fragment"`: redibuja las dos tablas con la corrección ya
        # aplicada sin re-correr la app entera. Ver el docstring.
        st.rerun(scope="fragment")


def _fmt_imp(valor, moneda="PEN"):
    """Un importe con el símbolo de SU moneda, o `—`. Gemelo en Python del
    formateo que `_JS_IMPORTE` hace en la grilla: los dos tienen que
    escribir igual el mismo número, o la ficha y la tabla se contradicen."""
    v = _num(valor)
    if v is None:
        return "—"
    return f"{sunat.simbolo_moneda(moneda)} {v:,.2f}"


def _fila_cruce_de(df_cruce, doc):
    """La fila del cruce que corresponde a `doc`, o `None`.

    Por `car`, que es la única clave sin colisiones — `documento` deja
    1.422 y `ruc+documento` deja 3 (ver `_fila_de`). El cruce lo lleva
    desde el 2026-08-28 justamente para esto.
    """
    if doc is None or df_cruce is None or df_cruce.empty:
        return None
    if "car" not in df_cruce.columns:
        return None
    car = str(doc.get("car") or "")
    if not car:
        return None
    coincidencias = df_cruce[df_cruce["car"].astype(str) == car]
    return None if coincidencias.empty else coincidencias.iloc[0]


def _filas_cotejo(doc, fila):
    """Las filas del cotejo, en orden: `(etiqueta, valor SUNAT, valor
    sistema o None, diferencia o None)`.

    FUENTE ÚNICA de las dos tarjetas que comparan el documento
    (`_card_sunat` y `_card_sistema`). Que las dos recorran ESTA lista es
    lo que las mantiene alineadas fila a fila — la misma razón por la que
    `_ALTO_FILA_CONVERSOR` es una constante compartida y no dos literales:
    dos paneles que se leen uno contra otro no pueden decidir su contenido
    por separado.

    TRES CLASES DE FILA, y la diferencia importa:
      · comparables (base, IGV, total) — las tres traen Δ. «Base total»
        es gravada + no gravada, que es lo que compara
        `cruzar_con_parquet`; el desglose son las dos filas de arriba.
      · de identidad que el sistema también guarda (RUC, número en el ERP,
        fecha) — los dos lados, sin Δ: no son números.
      · sólo de SUNAT (tipo, período, estado, moneda, vencimiento,
        detracción, base gravada, no gravado — y el total en la moneda del
        papel cuando no es PEN) — el sistema no las tiene y su celda va
        con una raya, no en cero. Un cero ahí se leería como un dato. Que
        sean OCHO de catorce no es ruido: es la medida de cuánto menos
        guarda el ERP que el registro de SUNAT.

    LOS IMPORTES VAN EN SOLES, los de las dos fuentes: el registro del
    SIRE viene así y el lado del sistema se convierte al agrupar (ver
    `_parquet_agrupado_por_documento`). Ver la regla #313.

    «Base gravada» y «No gravado» van separadas y sin Δ, y además está
    «Base» que es la suma: sólo la gravada genera crédito fiscal, pero es
    la suma la que `cruzar_con_parquet` compara contra el sistema (para
    que una compra exonerada no parezca descuadre — ver su docstring).
    """
    mon = str(doc.get("moneda") or "PEN")
    tiene = fila is not None

    def _fecha(v):
        f = pd.to_datetime(v, errors="coerce")
        return None if pd.isna(f) else f"{f:%d/%m/%Y}"

    filas = [
        ("RUC", str(doc.get("ruc_proveedor") or "—"),
         (str(fila.get("ruc_sistema") or "") or None) if tiene else None, None),
        ("Documento en el ERP", str(doc.get("documento") or "—"),
         (str(fila.get("documento_sistema") or "") or None) if tiene else None,
         None),
        ("Fecha de emisión", _fecha(doc.get("fecha_emision")) or "—",
         _fecha(fila.get("fecha_sistema")) if tiene else None, None),
        ("Tipo de comprobante", str(doc.get("tipo_nombre") or "—"), None, None),
        ("Período tributario", str(doc.get("periodo") or "—"), None, None),
        ("Estado en SUNAT", str(doc.get("estado") or "—"), None, None),
        ("Moneda", sunat._moneda_con_tc(doc), None, None),
        ("Vencimiento", _fecha(doc.get("fecha_vencimiento")) or "—", None, None),
        ("Detracción",
         "Sí" if str(doc.get("detraccion") or "").strip().upper() == "D"
         else "No", None, None),
        # En SOLES, como los registra SUNAT y como quedan las dos fuentes
        # del cruce. La moneda del papel se dice en la fila «Moneda» y,
        # si no es PEN, con el total del comprobante al final. Regla #313.
        ("Base gravada", _fmt_imp(doc.get("base_imponible")), None, None),
        ("No gravado", _fmt_imp(doc.get("no_gravado")), None, None),
    ]

    # Los tres comparables. El valor de SUNAT sale del CRUCE cuando hay
    # fila (`base_sunat` es base+no gravado, no `base_imponible`) y del
    # propio comprobante cuando no la hay.
    _desde_doc = {"base_sunat": "base_imponible", "igv_sunat": "igv",
                  "total_sunat": "total"}
    for etiqueta, campo_u, campo_s in (
            ("Base total", "base_sunat", "base_sistema"),
            ("IGV", "igv_sunat", "igv_sistema"),
            ("Total", "total_sunat", "total_sistema")):
        u = (_num(fila.get(campo_u)) if tiene
             else _num(doc.get(_desde_doc[campo_u])))
        s = _num(fila.get(campo_s)) if tiene else None
        dif = None if (u is None or s is None) else round(s - u, 2)
        filas.append((etiqueta, _fmt_imp(u),
                      None if s is None else _fmt_imp(s), dif))

    # El total como lo dice el PAPEL, sólo en moneda extranjera: las once
    # filas de arriba están en soles y sin esto no habría dónde leer el
    # número que el proveedor imprimió.
    _papel = sunat.en_moneda_del_papel(doc, _num(doc.get("total")))
    if _papel is not None:
        filas.append((f"Total en {mon}",
                      f"{sunat.simbolo_moneda(mon)} {_papel:,.2f}", None, None))
    return filas


_TIRON_MARKDOWN = 16
"""Los píxeles que `stMarkdownContainer` se come con su
`margin-bottom: -16px` (regla #162). Los suma `_card_sistema` al alto de
su pastilla para que las dos grillas del cotejo arranquen a la misma
altura."""


_ALTO_TABS = 40
"""Alto de la barra de `st.tabs`, medido en el navegador. Lo necesita la
tarjeta del sistema para reservar el mismo sitio con su pastilla de
estado: es lo único que separa el tope de las dos grillas, y de eso
depende que las filas se lean una contra otra. Si Streamlit cambia el alto
de sus tabs, esto se nota como un desfase parejo en las catorce filas —
`herramientas/auditar_layout.js` lo mide en diez segundos."""


_ANCHO_ETIQUETA_COTEJO = 132
"""Ancho de la columna de etiquetas del cotejo, en píxeles. Es fijo y
compartido por las dos tarjetas a propósito: ver `_grilla_campos`."""


_ALTO_FILA_COTEJO = 24
"""Alto de una fila del cotejo, en píxeles, y la razón por la que es una
constante: las DOS tarjetas la usan como `line-height`, y de eso depende
que la fila «Total» de la izquierda caiga a la misma altura que la de la
derecha. Misma familia que `_ALTO_FILA_CONVERSOR` — dos paneles que se
comparan a simple vista no pueden medir distinto."""


def _grilla_campos(filas, lado):
    """Pinta las filas del cotejo en una de las dos tarjetas.

    `lado` es `"sunat"` o `"sistema"`, y es lo único que cambia: la
    etiqueta se repite en las DOS a propósito. Podría ir sólo en la
    izquierda y ahorrar ancho —las filas están alineadas—, pero en móvil
    las columnas se apilan y la tarjeta de la derecha quedaría como una
    lista de números sin nombre. Una tarjeta tiene que poder leerse sola.
    """
    celdas = []
    for etiqueta, val_u, val_s, dif in filas:
        marcada = dif is not None and abs(dif) > _TOLERANCIA_CENTAVOS
        if lado == "sunat":
            celdas.append(
                f'<div style="color:{GRIS_TEXTO};">{etiqueta}</div>'
                f'<div style="color:{TEXTO_PRINCIPAL};text-align:right;">'
                f'{val_u}</div>')
            continue
        color = ADVERTENCIA_TEXTO if marcada else TEXTO_PRINCIPAL
        peso = "600" if marcada else "400"
        # Una raya y no vacío: "el sistema no guarda este campo" es un
        # dato, y una celda en blanco se lee como "no lo cargaron".
        valor = val_s if val_s is not None else "—"
        _d = "" if dif is None else (
            "=" if abs(dif) <= _TOLERANCIA_CENTAVOS else f"{dif:+,.2f}")
        celdas.append(
            f'<div style="color:{GRIS_TEXTO};">{etiqueta}</div>'
            f'<div style="color:{color};font-weight:{peso};text-align:right;">'
            f'{valor}</div>'
            f'<div style="color:{color};font-weight:{peso};text-align:right;'
            f'font-size:11px;">{_d}</div>')

    # La columna de etiquetas mide lo mismo en las dos, y por eso es fija
    # y no `1fr`: la del sistema tiene una columna más (Δ), así que con
    # `1fr` le quedaba 80px menos y una etiqueta larga envolvía a dos
    # líneas SÓLO de ese lado. Medido: «Base (grav. + no grav.)» ocupaba
    # 48px contra 24, y las dos últimas filas quedaban corridas 8px.
    _e = f"{_ANCHO_ETIQUETA_COTEJO}px"
    cols = f"{_e} auto" if lado == "sunat" else f"{_e} auto 58px"
    st.markdown(
        f'<div style="display:grid;grid-template-columns:{cols};'
        f'gap:0 12px;font-size:12.5px;font-variant-numeric:tabular-nums;'
        f'line-height:{_ALTO_FILA_COTEJO}px;">' + "".join(celdas) + '</div>',
        unsafe_allow_html=True)


def _card_sunat(doc, fila):
    """Tarjeta IZQUIERDA: el comprobante tal como lo tiene SUNAT.

    Lleva las pestañas porque los tres artefactos que cuelgan de ellas
    —el PDF, el detalle de líneas y el XML— son del lado del proveedor:
    no hay nada equivalente del lado del sistema.

      · **Datos** — los campos del SIRE, en el mismo orden que la tarjeta
        de al lado (`_filas_cotejo`).
      · **Comprobante** — el PDF, renderizado.
      · **Detalle (n)** — las líneas del XML, completas.
      · **XML** — el archivo crudo.

    Las tres últimas sólo existen si el original ya está sincronizado; si
    no, en su lugar va `_pedir_original` — y esa pestaña se llama
    «⚠ Original» en vez de «⬇ Original» cuando el último pedido falló,
    que es lo único del fracaso que se ve sin abrirla (regla #309).
    «Datos» está SIEMPRE: sale del registro del SIRE, que no depende de
    ningún sync.
    """
    _titulo_panel("Comprobante SUNAT", "el original del proveedor")

    pdf_original, xml_original = sunat.originales(doc)
    lineas = sunat.lineas_xml(xml_original) if xml_original else []

    nombres = ["Datos"]
    if pdf_original:
        nombres.append("📄 Comprobante")
    if lineas:
        nombres.append(f"📋 Detalle ({len(lineas)})")
    if xml_original:
        nombres.append("🧾 XML")
    if not (pdf_original or xml_original):
        # La ETIQUETA cambia cuando el último pedido falló. No es adorno:
        # el aviso vive DENTRO de esta pestaña, así que con el rótulo de
        # siempre («⬇ Original», que invita a bajar algo) el usuario se
        # queda en «Datos» esperando un archivo que ya se sabe que no va a
        # llegar. Medido el 2026-09-04 con FI01-20701451: el pedido se
        # atendió en 25 segundos y falló, y la pantalla no lo decía en
        # ningún lado visible sin abrir la pestaña. Ver regla #309.
        nombres.append("⚠ Original" if sunat.fallo_solicitud(doc)
                       else "⬇ Original")

    for nombre, tab in zip(nombres, st.tabs(nombres)):
        with tab:
            if nombre == "Datos":
                _grilla_campos(_filas_cotejo(doc, fila), "sunat")
                _descargas_ficha(doc, pdf_original, xml_original)
            elif nombre.startswith("📄"):
                # EL PDF SE MUESTRA COMO IMAGEN, no embebido: Chrome no
                # renderiza un `data:application/pdf` dentro de un iframe
                # con `sandbox` y Streamlit monta todos sus iframes así.
                # Renderizarlo del lado del servidor además funciona igual
                # en el teléfono, donde un visor embebido es incómodo.
                with st.spinner("Preparando el comprobante…"):
                    paginas = sunat.paginas_pdf(pdf_original)
                if not paginas:
                    st.warning("No se pudo mostrar el PDF en pantalla. "
                               "Se puede descargar igual.")
                for i, png in enumerate(paginas, 1):
                    st.image(png, use_container_width=True)
                    if len(paginas) > 1:
                        st.caption(f"Página {i} de {len(paginas)}")
            elif nombre.startswith("📋"):
                _tabla_detalle(lineas)
            elif nombre.startswith("🧾"):
                st.code(xml_original.decode("utf-8", errors="replace"),
                        language="xml")
            else:
                _pedir_original(doc)


_COLOR_ESTADO_CRUCE = {
    "Coincide": GRIS_TEXTO,
    "Diferencia": ADVERTENCIA_TEXTO,
    "Solo SUNAT": ADVERTENCIA_TEXTO,
    "Solo sistema": ERROR,
}
"""Color de la pastilla de estado de `_card_sistema`. Misma convención que
la columna «Está vs Sistema» de la tabla: ámbar = revisar, rojo = plata
cargada sin comprobante que la respalde, gris = lo normal, que no compite
por atención."""


def _card_sistema(doc, fila):
    """Tarjeta DERECHA: lo que el sistema tiene cargado de ese documento.

    Recorre las MISMAS filas que la de la izquierda (`_filas_cotejo`), en
    el mismo orden y con el mismo alto de línea, así se leen una contra
    otra sin tener que buscar. Suma una columna Δ, que responde la
    pregunta real —«¿cuánto?»— en vez de dejar los dos números para que
    los reste el usuario.

    La pastilla de estado ocupa el sitio que en la tarjeta de al lado
    ocupan las pestañas. No es un relleno: es el veredicto del cruce, y
    ponerlo acá arriba es lo que hace que las catorce filas de abajo
    arranquen a la misma altura en las dos tarjetas.
    """
    _titulo_panel("Sistema", "lo que está cargado")

    estado = str(fila.get("estado") or "") if fila is not None else "Solo SUNAT"
    color = _COLOR_ESTADO_CRUCE.get(estado, GRIS_TEXTO)
    # `height` y no `min-height`, y con ESE número: es el alto exacto de la
    # barra de pestañas de la tarjeta de al lado (40px, medido en el
    # navegador) MÁS los 16 que le resta el `margin-bottom: -16px` que
    # Streamlit le pone al `stMarkdownContainer` (regla #162). Ese tirón
    # vive en el contenedor PADRE, así que un `margin-bottom:0` inline no
    # lo alcanza — se comprobó: la propiedad quedaba en 0 en el div y el
    # desfase seguía. Compensarlo en el alto es local y no depende de
    # acertarle a un selector.
    # Sin esto, las dos grillas arrancaban con 22px de
    # desfase — casi una fila entera de 24px — y las catorce filas se
    # leían corridas una respecto de la otra, que es justo lo que dos
    # tarjetas que comparan no pueden hacer.
    st.markdown(
        f'<div style="display:flex;align-items:center;'
        f'height:{_ALTO_TABS + _TIRON_MARKDOWN}px;">'
        f'<span style="background:{LAVANDA_FONDO};color:{color};'
        f'font-size:11px;font-weight:600;padding:3px 10px;border-radius:7px;">'
        f'{estado or "—"}</span></div>', unsafe_allow_html=True)

    _grilla_campos(_filas_cotejo(doc, fila), "sistema")

    if fila is None or estado == "Solo SUNAT":
        st.caption("SUNAT lo tiene, tu sistema todavía no. El conversor de "
                   "abajo mapea sus líneas contra el maestro.")


def _panel_documento_vacio():
    """El estado de "todavía no elegiste nada", para las dos tarjetas."""
    st.markdown(
        f'<div style="padding:28px 16px;text-align:center;color:{GRIS_TEXTO};'
        f'font-size:13px;line-height:1.6;">'
        f'<div style="font-size:30px;margin-bottom:6px;">📄</div>'
        f'Elegí un documento de la tabla<br>para verlo acá.</div>',
        unsafe_allow_html=True)


def _cabecera_documento(doc):
    """La identificación del documento elegido, ARRIBA de las dos tarjetas.

    Va una sola vez y no dentro de cada una: identifica al documento para
    las DOS, igual que la cabecera única que tenía el panel cuando era una
    sola tarjeta con dos columnas.
    """
    st.markdown(
        f'<div style="background:{LAVANDA_FONDO};border-radius:10px;'
        f'padding:9px 14px;margin-bottom:10px;display:flex;'
        f'align-items:baseline;gap:10px;flex-wrap:wrap;">'
        f'<span style="font-size:16px;font-weight:600;color:{TEXTO_PRINCIPAL};">'
        f'{doc.get("documento", "")}</span>'
        f'<span style="font-size:11px;color:{GRIS_TEXTO};'
        f'text-transform:uppercase;letter-spacing:.04em;">'
        f'{doc.get("tipo_nombre", "Comprobante")}</span>'
        f'<span style="font-size:12px;color:{GRIS_TEXTO};">'
        f'{_compras_truncar(str(doc.get("proveedor", "")), 52)}</span></div>',
        unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def _serie_proveedor(ruc, meses=12):
    """Total comprado a un proveedor, mes a mes, sobre el registro COMPLETO
    —no sobre el rango de la pantalla—: es lo que le da sentido al gráfico
    al lado de la ficha, que habla de un documento y no de un período.

    Devuelve `(etiquetas, valores, docs)` ya recortado a los últimos
    `meses` con movimiento. Cacheado una hora, igual que el registro del
    que sale.
    """
    d = sunat._registro_de_parquet()
    if d is None or getattr(d, "empty", True) or not ruc:
        return [], [], []
    p = d[d["ruc_proveedor"].astype(str) == str(ruc)]
    if p.empty:
        return [], [], []
    mes = pd.to_datetime(p["fecha_emision"], errors="coerce").dt.to_period("M")
    g = (pd.DataFrame({"mes": mes,
                       "total": pd.to_numeric(p["total"], errors="coerce")})
         .dropna(subset=["mes"])
         .groupby("mes")
         .agg(total=("total", "sum"), docs=("total", "size"))
         .sort_index().tail(meses))
    # `%b` sale en INGLÉS ("Sep 25"): `strftime` usa el locale del proceso
    # y en Streamlit Cloud es el C. `MESES_ABR_ES` es la tupla que ya usan
    # `franja_fecha` y `cortes` — una sola lista de meses en el proyecto.
    return ([f"{MESES_ABR_ES[m.month - 1]} {m.year % 100:02d}"
             for m in g.index.to_timestamp()],
            [float(v) for v in g["total"]], [int(v) for v in g["docs"]])


def _grafico_proveedor(doc):
    """Barras del proveedor del documento elegido, mes a mes.

    El tercer modo del panel de la derecha, y el que lo justifica: a pedido
    2026-08-28 el gráfico bajó de arriba de la tabla —donde mostraba el
    período y no cambiaba nunca, o sea decorado— al costado de la ficha,
    que es el panel de UN documento. Ahí un gráfico del período entero
    queda fuera de contexto; éste habla del proveedor de la fila elegida.

    Medido con datos reales al diseñarlo: COMPANIA FOOD RETAIL pasó de
    S/ 203 en enero a S/ 5.953 en agosto — casi ×30 en ocho meses. Eso no
    estaba en ninguna pantalla de este drill y aparece solo con mirar uno
    de sus comprobantes.
    """
    if doc is None:
        st.caption("Elegí un documento de la tabla para ver a su proveedor.")
        return
    ruc = str(doc.get("ruc_proveedor") or "")
    etiquetas, valores, docs = _serie_proveedor(ruc)
    if not valores:
        st.caption("Sin historial para este proveedor.")
        return

    # La última barra es el mes del documento elegido: se pinta con el
    # acento y las demás en lavanda claro, para que el mes del que se está
    # mirando un comprobante se ubique sin leer el eje.
    colores = [LAVANDA_FOCO] * len(valores)
    colores[-1] = ACENTO
    fig = go.Figure(go.Bar(
        x=etiquetas, y=valores, marker=dict(color=colores),
        hovertemplate="%{x}<br>S/ %{y:,.2f}<extra></extra>"))
    _compras_layout(fig, alto=alturas.MINI)
    fig.update_layout(
        title=_compras_truncar(str(doc.get("proveedor") or ruc), 34),
        margin=dict(t=44, b=28, l=8, r=8))
    st.plotly_chart(fig, use_container_width=True,
                    key=f"sunat_g_prov_{ruc or 'none'}")

    ultimo, previo = valores[-1], (valores[-2] if len(valores) > 1 else None)
    partes = [f"<b>S/ {ultimo:,.2f}</b> {etiquetas[-1]}",
              f"<b>{docs[-1]}</b> docs"]
    if previo:
        partes.append(f"<b>{(ultimo / previo - 1) * 100:+.0f}%</b> vs el mes previo")
    st.markdown(
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;font-size:11.5px;'
        f'color:{GRIS_TEXTO};">' + " · ".join(partes) + '</div>',
        unsafe_allow_html=True)


_MODOS_GRAFICO = ("Este proveedor", "Por fecha", "Por proveedor")


def _panel_grafico(vis, doc):
    """El panel de la derecha de la fila de la ficha: tres modos.

    «Por fecha» y «Por proveedor» son los dos resúmenes que hasta el
    2026-08-28 vivían ARRIBA de la tabla, elegidos con un `selectbox`
    llamado «Ver» que también ofrecía «Cruce». Al fundirse las dos tablas,
    «Cruce» dejó de ser una vista; y al bajar el gráfico acá, el selector
    bajó con él — queda pegado a lo único que controlaba, que era la
    confusión que el usuario reportó al preguntar en qué se diferenciaban
    las dos primeras opciones (la respuesta era: sólo en este widget).

    El estado va en un espejo de `session_state` que NO es la clave del
    widget: un `st.rerun()` en medio de la corrida se lleva puesto el
    estado de un `segmented_control` que todavía no se dibujó. Es la
    regla #211, aplicada preventivamente.
    """
    k_eco = "sunat_graf_modo__eco"
    previo = st.session_state.get(k_eco, _MODOS_GRAFICO[0])
    modo = st.segmented_control(
        "Ver", _MODOS_GRAFICO, default=previo, key="sunat_graf_modo",
        label_visibility="collapsed") or previo
    st.session_state[k_eco] = modo

    if modo == "Este proveedor":
        _grafico_proveedor(doc)
        return
    # Los otros dos resumen el RANGO, así que sin df no tienen nada que
    # dibujar. `vis` llega en `None` por cualquiera de las salidas
    # tempranas de `_cuerpo` (sin rango, SUNAT caído, sin comprobantes):
    # es la regla #115 — la tarjeta se dibuja igual y decide adentro.
    if vis is None or getattr(vis, "empty", True):
        st.caption("Sin comprobantes en el rango para resumir.")
        return
    if modo == "Por proveedor":
        _ranking_proveedores(vis)
    else:
        _grafico_por_fecha(vis)


def _necesita_conversor(doc, fila_cruce):
    """¿Se dibuja la tarjeta del conversor?

    Sólo cuando el documento NO está cargado en el sistema (a pedido
    2026-08-28): el conversor existe para mapear las líneas del XML contra
    el maestro y así poder cargarlo. Si ya está cargado no hay nada que
    convertir, y la tarjeta ocupaba pantalla para no decir nada.

    Medido sobre las 326 filas del rango: se dibuja en 122 («Solo SUNAT»)
    y desaparece en 204 — 169 «Coincide» y 16 «Diferencia» que ya están
    cargados, más 19 «Solo sistema» que ni siquiera tienen comprobante en
    SUNAT. O sea que en 2 de cada 3 documentos la pantalla ahora termina
    en la ficha, que era el pedido de fondo: la vista era demasiado larga.

    «Diferencia» queda AFUERA a propósito aunque el documento tenga algo
    raro: ahí el documento ya está cargado y la pregunta es dónde está el
    descuadre, que la responde el cotejo de la ficha — no un mapeo de
    líneas contra el maestro.
    """
    if doc is None:
        return False
    if fila_cruce is None:
        # Sin fila de cruce no se puede afirmar que esté cargado; se
        # dibuja, que es el comportamiento que había antes de esta regla.
        return True
    return str(fila_cruce.get("estado") or "") == "Solo SUNAT"


def _pedir_original(doc):
    """El flujo de "todavía no está sincronizado el original": avisar en
    qué estado está el pedido y, si no hay ninguno, ofrecer hacerlo.

    Se extrajo de `_mostrar_original` el 2026-08-28, cuando el original
    dejó de ser un panel propio y pasó a ser pestañas de la ficha: el
    pedido no es una pestaña —no hay nada que ver— sino lo que se muestra
    EN LUGAR de ellas.
    """
    if sunat.solicitud_pendiente(doc):
        # La corrida nocturna va de lo más nuevo hacia atrás y tarda
        # semanas en llegar a lo viejo (ver regla #142), así que acá se
        # ofrece pedirlo puntualmente. La webapp NO abre ningún navegador:
        # deja una señal en R2 y la CPU local hace el trabajo — mismo
        # mecanismo que el refresco de parquets (regla #144).
        st.info("⏳ Pedido. La máquina local lo está trayendo de SUNAT — "
                "suele tardar menos de un minuto. Volvé a entrar al "
                "documento en un rato.", icon=None)
        return

    # Un intento anterior que falló: sin esto el usuario ve el mismo botón
    # de siempre y no tiene forma de saber que ya se intentó y no se pudo.
    fallo = sunat.fallo_solicitud(doc)
    if fallo:
        st.warning(f"No se pudo traer: {fallo.get('motivo', 'error desconocido')}",
                   icon="⚠️")
        st.caption(f"Último intento: {fallo.get('cuando', '—')}")
        etiqueta = "↻ Intentar de nuevo"
    else:
        etiqueta = "⬇ Traer el original de SUNAT"

    # El veredicto de EMISOR, antes del botón y no después: un proveedor
    # que nunca sirvió un original no es "todavía no sincronizado" — es
    # que el portal no lo entrega, y apretar el botón otra vez da el mismo
    # silencio. Se dice con el número porque es lo que lo hace creíble:
    # "0 de 414" es un patrón, "no se pudo" es una excusa.
    n_emisor = sunat.emisor_sin_originales(doc)
    if n_emisor:
        # El punto de miles se arma APARTE: un `.replace(",", ".")` sobre la
        # frase entera también se come la coma de la oración — se vio en
        # pantalla como "del registro. cero se pudieron bajar".
        _n = f"{n_emisor:,}".replace(",", ".")
        st.info(f"Con este proveedor el portal de SUNAT nunca entregó el "
                f"original: de sus {_n} comprobantes del registro, cero se "
                f"pudieron bajar. El cotejo de al lado sale del SIRE y no "
                f"depende de esto.", icon="ℹ️")
        etiqueta = "↻ Intentar igual"

    if st.button(etiqueta, use_container_width=True,
                 key="sunat_pedir_original",
                 help="Le pide a la máquina local que baje el PDF y el XML "
                      "que emitió el proveedor. Tarda menos de un minuto; "
                      "después queda guardado para siempre."):
        if sunat.solicitar_original(doc):
            st.rerun()
        else:
            st.error("No se pudo dejar el pedido. ¿Están las credenciales "
                     "de R2 configuradas?")
    if not fallo and not n_emisor:
        st.caption("Todavía no sincronizado. El cotejo de al lado sale del "
                   "registro del SIRE y está disponible igual.")


def _descargas_ficha(doc, pdf_original, xml_original):
    """Los tres archivos que el usuario se puede llevar, al pie del cotejo.

    La ficha PDF la RENDERIZA la app con los datos del registro
    (`sunat.ficha_pdf`); el PDF y el XML son los que emitió el proveedor.
    No es lo mismo y confundirlos tiene consecuencias contables, por eso
    el caption lo dice en pantalla y no en un comentario. Ver
    `arquitectura.md` regla #142.
    """
    try:
        ficha = sunat.ficha_pdf(doc)
    except Exception as e:
        st.error(f"No se pudo generar el PDF: {e}")
        ficha = None

    columnas = st.columns(3)  # columnas-internas: 3 botones de descarga
    with columnas[0]:
        if ficha:
            st.download_button(
                "⬇ Ficha", data=ficha,
                file_name=f"{doc.get('documento', 'comprobante')}_ficha.pdf",
                mime="application/pdf", use_container_width=True,
                key="sunat_dl_ficha")
    with columnas[1]:
        if pdf_original:
            st.download_button(
                "⬇ PDF", data=pdf_original,
                file_name=f"{doc.get('documento', 'comprobante')}.pdf",
                mime="application/pdf", use_container_width=True,
                key="sunat_dl_pdf")
    with columnas[2]:
        if xml_original:
            st.download_button(
                "⬇ XML", data=xml_original,
                file_name=f"{doc.get('documento', 'comprobante')}.xml",
                mime="application/xml", use_container_width=True,
                key="sunat_dl_xml")

    st.caption("«Ficha» la arma esta app con los datos del SIRE. «PDF» y "
               "«XML» son los que emitió el proveedor."
               if pdf_original or xml_original else
               "«Ficha» la arma esta app con los datos del SIRE. No es el "
               "PDF que emitió el proveedor.")


def _card_conversor_sistema(doc, d):
    """Tarjeta «Conversor SUNAT-Sistema»: comparar cada línea del XML
    contra el sistema y corregir a mano lo que no calza.

    Hasta 2026-08-27 esto era la cuarta pestaña de "Original del
    proveedor" (`_mostrar_original`) — pasó a ser SU PROPIA TARJETA, a
    pedido: no es "ver el original" (esa sigue siendo la tarea de la
    tarjeta de arriba), es otra cosa — comparar y corregir —, así que le
    toca su propio lugar en la pila en vez de esconderse como una
    pestaña más. El contenido en sí (`_detalle_sistema`, con sus
    docstrings sobre maestro/emparejamiento/edición en celda) no cambió
    en nada — sólo dónde vive.

    `d` es el parquet de Compras completo (recibido de
    `renderizar_documentos_sunat`, que ya lo recibe para la vista
    "Cruce") — lo necesita `_detalle_sistema` para buscar las líneas de
    ESTE documento y armar el catálogo completo de productos.
    """
    st.markdown(
        f'<div style="font-size:10px;font-weight:700;color:{ACENTO};'
        f'text-transform:uppercase;letter-spacing:.05em;margin:0 0 6px;'
        f'padding-bottom:3px;border-bottom:1px solid {GRIS_BORDE};">'
        f'Conversor SUNAT-Sistema</div>', unsafe_allow_html=True)

    if doc is None:
        st.markdown(
            f'<div style="padding:20px 16px;text-align:center;color:{GRIS_TEXTO};'
            f'font-size:13px;line-height:1.6;">'
            f'Elegí un documento de la tabla de arriba para comparar sus '
            f'líneas contra el sistema.</div>',
            unsafe_allow_html=True,
        )
        return

    # Mismo dato que ya trae "Original del proveedor" (`sunat.originales`,
    # cacheado 1h — pedirlo de nuevo acá no repite la lectura de R2), pero
    # esta tarjeta solo necesita el XML: no muestra el PDF ni ofrece
    # descargas, eso ya lo hace la tarjeta de arriba.
    _, xml_original = sunat.originales(doc)
    lineas = sunat.lineas_xml(xml_original) if xml_original else []
    if not lineas:
        st.info("Todavía no hay XML original sincronizado para este "
                "documento — sin XML no hay líneas que comparar. Se pide "
                "desde «Original del proveedor», arriba.")
        return

    _detalle_sistema(doc, lineas, d, xml_original)


def _excel_bytes(df, hoja="Datos"):
    """El df como .xlsx en memoria, para `st.download_button`.

    xlsx y no CSV (a pedido 2026-08-21): el CSV obliga a pelear con el
    separador y la coma decimal cada vez que se abre en Excel con locale
    es-PE, y las columnas de plata entran como texto. El motor es
    `xlsxwriter` — wheel puro, solo-escritura, en requirements.txt.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=hoja)
    return buf.getvalue()


def _rango_vigente():
    """`(inicio, fin)` del filtro de fecha, o `(None, None)` si no hay nada.

    UNA fecha suelta vale como rango de UN DÍA, y eso no es tolerancia
    cosmética: `st.date_input` en modo rango COMMITEA una tupla de un solo
    elemento apenas se hace el PRIMER clic del calendario, y rerunea con
    eso. O sea que "media selección" no es un estado raro — es el estado
    normal entre los dos clics, y el que queda fijo si alguien elige un
    día y cierra el calendario (el gesto natural para "quiero ver hoy").

    Antes esto se leía con `len(rango) < 2 → no hay rango`, y el drill
    cortaba con un `st.info` ANTES de dibujar su tarjeta. Como el pill de
    fecha vive DENTRO de esa tarjeta desde el 2026-08-21 (y `app.py` deja
    de dibujarlo arriba cuando esta vista está activa, ver
    `vista_quiere_fecha_propia`), el mensaje pedía elegir una fecha en un
    control que él mismo acababa de borrar de la pantalla: sin salida,
    salvo cambiar de vista. Ver `arquitectura.md` regla #115.
    """
    return _dia_o_rango(
        st.session_state.get(clave_rango("Compras", usa_carga_rango=False)))


def _dia_o_rango(rango):
    """La parte PURA de `_rango_vigente`, para poder testearla sin
    `session_state` ni runtime de Streamlit."""
    if isinstance(rango, (datetime.date, datetime.datetime, pd.Timestamp)):
        return rango, rango          # no debería pasar, pero es un día válido
    if not isinstance(rango, (tuple, list)) or not len(rango) or rango[0] is None:
        return None, None
    ini = rango[0]
    fin = rango[1] if len(rango) > 1 and rango[1] is not None else ini
    return ini, fin


_MES_SUNAT = {
    "Todos": None,
    "Mes presentado": "Registrado",
    "Mes abierto": "Pendiente",
}
"""Las tres opciones del filtro, y a qué `situacion` del registro
corresponde cada una.

Se llamaba «Situación» con valores «Todos / Registrados / Pendientes»
hasta el 2026-08-28 y se renombró a pedido, porque los nombres viejos se
leían justo al revés de lo que significan: **es el estado del PERÍODO
tributario, no del documento**. «Pendiente» quiere decir que el mes sigue
abierto en SUNAT (`codEstado` "03"), no que falte cargar el comprobante en
el sistema — eso lo dice la otra columna, «Está vs Sistema», que es un eje
independiente. Medido en el rango de prueba: los 307 comprobantes están
«Pendiente» (el mes 202608 sigue abierto) y de ésos 169 YA están
perfectamente cargados. Mismo estado en SUNAT, situación opuesta en la
contabilidad."""


def renderizar_documentos_sunat(d, col_fecha):
    """Punto de entrada del drill. Lo llama `graficos/compras/__init__.py`.

    TRES TARJETAS, y la tercera es condicional (2026-08-28):

      1. **La tabla** a lo ancho — controles, KPIs del cruce y los
         comprobantes. Una sola tabla desde que `_tabla` y `_tabla_cruce`
         se fundieron en `_tabla_documentos`.
      2. **Ficha | gráfico**, partidos con `COLUMNAS_DRILL`. La ficha es
         el documento elegido en pestañas (`_panel_documento`); el
         gráfico bajó de arriba de la tabla —donde no cambiaba nunca— y
         ahora habla del proveedor de la fila elegida (`_panel_grafico`).
      3. **El conversor**, sólo si el documento no está cargado en el
         sistema (`_necesita_conversor`). En 2 de cada 3 documentos la
         pantalla termina en la 2.

    `d` y `col_fecha` (el parquet de Compras y su columna de fecha) ya no
    son opcionales: el cruce dejó de ser una vista elegible y se calcula
    SIEMPRE, porque su resultado es una columna de la tabla. Cuesta
    ~390 ms por rango en la máquina de desarrollo, y se paga una vez
    porque `_parquet_agrupado_por_documento` y el propio registro están
    cacheados.

    LOS CONTROLES VIVEN DENTRO DE LA TARJETA, no en una franja aparte
    arriba — mismo criterio que el selector "La semana empieza" del drill
    Semanal. No es gusto: esta app no tiene scroll de PÁGINA (el main lo
    recorta), así que cualquier bloque que viva AFUERA de las tarjetas
    empuja a todas hacia abajo sin que `--alto-util` se entere. Medido
    antes de corregirlo: con período/vista/KPIs en una franja externa, la
    tarjeta arrancaba en y=266 (contra ~165 de Proveedor) y su borde
    inferior quedaba en 990 con un viewport de 900.
    """
    f_ini, f_fin = _rango_vigente()

    # Lo que `_cuerpo` deja para las tarjetas de abajo. Se inicializa acá
    # porque las salidas tempranas de `_cuerpo` (sin rango, SUNAT caído,
    # sin comprobantes) devuelven `None` sin tocarlo: la regla #115 —
    # dibujar las tarjetas SIEMPRE y decidir el contenido adentro.
    estado = {"doc": None, "vis": None, "cruce": None}

    with st.container(border=True, key="sunat_card_izq"):
        c_sel, c_act, c_kpi = st.columns([1.5, 0.8, 4.1])
        with c_sel:
            # El pill de fecha, DENTRO de la tarjeta. Acá la fecha no es
            # contexto global: es EL filtro de la tabla — el rango que se
            # le consulta al SIRE. NO es una copia del de la franja: es la
            # MISMA llamada, movida. `app.py` lo publica y deja de
            # dibujarlo cuando esta vista está activa
            # (`vista_quiere_fecha_propia`), porque el widget no se puede
            # duplicar: su key es la clave canónica del rango.
            franja_fecha.render()
            # El selector «Ver» que había acá bajó al panel del gráfico
            # (`_panel_grafico`), que es lo único que controlaba.
            mes_sunat = st.selectbox(
                "Mes en SUNAT", list(_MES_SUNAT), key="sunat_mes_sunat",
                label_visibility="collapsed",
                help="El estado del PERÍODO tributario en SUNAT, no del "
                     "documento. «Mes abierto» = SUNAT ya ve la compra "
                     "pero el registro de ese mes todavía no se presentó: "
                     "es crédito fiscal sin tomar. Si está cargado o no en "
                     "tu sistema lo dice «Está vs Sistema».",
            )
        with c_act:
            _c_ref, _c_xls = st.columns(2)  # columnas-internas: 2 iconos de accion
        with _c_ref:
            _ayuda = "Volver a consultar a SUNAT"
            if not sunat.secrets_disponibles():
                _ayuda += (". Sin credenciales configuradas: se muestran "
                           "datos de ejemplo (agregá SUNAT_RUC, "
                           "SUNAT_USUARIO_SOL, SUNAT_CLAVE_SOL, "
                           "SUNAT_CLIENT_ID y SUNAT_CLIENT_SECRET a los "
                           "secrets).")
            # Limpia TODAS las cachés de la cadena: la del parquet, la del
            # rango y la de cada período. La del rango sola devolvería lo
            # mismo, porque se apoya en las otras.
            if st.button("⟳", key="sunat_actualizar", help=_ayuda,
                         use_container_width=True):
                sunat._registro_de_parquet.clear()
                sunat.obtener_comprobantes.clear()
                sunat.obtener_comprobantes_rango.clear()
                sunat.periodos_con_estado.clear()
                sunat._existe_original.clear()
                sunat._bytes_original.clear()
                st.rerun()
        with _c_xls:
            # El botón de exportar vive ARRIBA (a pedido) pero los datos
            # que exporta se calculan MÁS ABAJO. `st.empty()` reserva el
            # sitio ahora y se rellena cuando el df existe: es la única
            # forma de tener un control arriba que dependa de algo de
            # abajo sin partir el flujo en dos reruns.
            _slot_excel = st.empty()

        def _cuerpo():
            """La tabla y su dato. Deja en `estado` lo que necesitan las
            tarjetas de abajo y devuelve el documento elegido."""
            if f_ini is None:
                # Prácticamente inalcanzable (`app.py::asegurar_rango`
                # siembra un default), pero si pasara, el pill de fecha ya
                # está dibujado JUSTO ARRIBA de este mensaje.
                st.info("Elegí una fecha en el calendario de acá arriba.")
                return None

            with st.spinner("Cargando el registro de compras de SUNAT…"):
                try:
                    df, _origen = sunat.comprobantes_rango(f_ini, f_fin)
                except Exception as e:
                    st.error(f"No se pudo consultar a SUNAT: {e}")
                    return None

            if df is None or df.empty:
                st.info("SUNAT no tiene comprobantes emitidos hacia tu RUC "
                        "en el rango elegido.")
                return None

            # El filtro del período se aplica ANTES de cruzar: filtrar a
            # "mes abierto" primero y cruzar después responde una pregunta
            # real — "de lo que aún no presenté, ¿qué ya tengo cargado?" —
            # que se pierde cruzando el rango completo sin filtrar.
            _sit = _MES_SUNAT.get(mes_sunat)
            vis = df if _sit is None else df[df["situacion"] == _sit]
            if vis.empty:
                st.info(f"No hay comprobantes de «{mes_sunat.lower()}» en el "
                        "rango.")
                return None

            g_pq = _parquet_agrupado_por_documento(d, col_fecha, f_ini, f_fin)
            df_cruce = cruzar_con_parquet(vis, g_pq)
            estado["vis"], estado["cruce"] = vis, df_cruce

            with c_kpi:
                _kpis_cruce(df_cruce, _origen)
            doc = _tabla_documentos(df_cruce, vis)

            # Se rellena el hueco reservado ARRIBA. Se exporta el CRUCE,
            # que es lo que la tabla muestra — sin `car`, que es una clave
            # interna y en una planilla es ruido.
            _sufijo = f"{pd.Timestamp(f_ini):%Y%m%d}_{pd.Timestamp(f_fin):%Y%m%d}"
            with _slot_excel:
                st.download_button(
                    "⬇", data=_excel_bytes(df_cruce.drop(columns=["car"],
                                                         errors="ignore")),
                    file_name=f"sunat_documentos_{_sufijo}.xlsx",
                    mime=("application/vnd.openxmlformats-officedocument"
                          ".spreadsheetml.sheet"),
                    key="sunat_dl_xlsx", use_container_width=True,
                    help="Exportar a Excel lo que muestra la tabla",
                )
            return doc

        estado["doc"] = _cuerpo()

    doc = estado["doc"]
    fila_cruce = _fila_cruce_de(estado["cruce"], doc)

    # Segunda fila: el documento elegido en DOS tarjetas hermanas, SUNAT
    # contra sistema (a pedido 2026-08-28 — antes era una sola tarjeta con
    # cuatro columnas: campo | SUNAT | sistema | Δ). Se parte con
    # `COLUMNAS_COTEJO` (1/1) y no con `COLUMNAS_DRILL` (1.6/1): acá los
    # dos lados son pares y cualquier asimetría se leería como que uno
    # importa más. Además así el eje cae en el mismo sitio que la fila del
    # conversor, que también parte por la mitad.
    if doc is None:
        with st.container(border=True, key="sunat_card_doc"):
            _panel_documento_vacio()
    else:
        # La identificación del documento va UNA vez, arriba de las dos:
        # es de las dos, no de ninguna. Son ~50px, el mismo sitio que
        # ocupaba dentro de la tarjeta única.
        _cabecera_documento(doc)
        c_sunat, c_sistema = st.columns(COLUMNAS_COTEJO, gap=GAP_DRILL)
        with c_sunat:
            with st.container(border=True, key="sunat_card_doc"):
                _card_sunat(doc, fila_cruce)
        with c_sistema:
            with st.container(border=True, key="sunat_card_sis"):
                _card_sistema(doc, fila_cruce)

    # El gráfico BAJA a lo ancho (a pedido, mismo día): al costado de la
    # ficha ya no hay sitio, porque ese costado se lo lleva la tarjeta del
    # sistema. Sigue siendo el panel de tres modos, sólo que ahora ocupa
    # la fila entera.
    with st.container(border=True, key="sunat_card_graf"):
        _panel_grafico(estado["vis"], doc)

    # Tercera tarjeta, CONDICIONAL: el conversor sirve para cargar lo que
    # no está cargado, así que sólo aparece ahí. Ver `_necesita_conversor`.
    if _necesita_conversor(doc, fila_cruce):
        with st.container(border=True, key="sunat_card_conversor"):
            _card_conversor_sistema(doc, d)
