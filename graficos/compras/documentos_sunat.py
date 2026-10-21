"""graficos.compras.documentos_sunat — drill «Documentos SUNAT».

DESDE EL 2026-09-30 ES UN REPORTE PROPIO, no una vista de Compras: lo
despacha `graficos/sunat_reporte.py` y el rango es el de ese reporte
(`clave_rango("Documentos SUNAT")`). El módulo se quedó en este paquete
porque todo lo que importa —`_comun`, el CSS del ranking, las pruebas— vive
acá. Donde abajo dice "Compras > Documentos SUNAT" o "la vista", léase el
reporte. Regla #577.

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
import html
import io
import json
import re
import time
import unicodedata

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, JsCode

import data
import definicion_compra
import sunat
import tipo_compra
from cortes import MESES_ABR_ES
from estado_rango import clave_rango, restaurar_eco
from tema import (
    ACENTO, ACENTO_TEXTO, ADVERTENCIA_TEXTO, ERROR_FONDO, ERROR_TEXTO,
    GRIS_BORDE, GRIS_FONDO, GRIS_TEXTO, GRIS_TEXTO_MEDIO, GRIS_TEXTO_SUAVE,
    LAVANDA_CABECERA_GRUPO, LAVANDA_FONDO,
    TEXTO_PRINCIPAL,
)
from graficos.base import (
    _compras_truncar, selector_fecha_tarjeta, una_vez_por_corrida)
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CROMO_GRID_RANK,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
# REEXPORT, no import muerto: `_llave_documento_parquet` vivia definida aca
# y se movio a `_comun.py` el 2026-09-08, cuando el drill Semanal la pidio
# para mostrar el N de documento en su tabla (ver el comentario largo que la
# acompana alla). Este modulo SI la usa —en `_parquet_agrupado_por_documento`
# y en `_fila_de`—, asi que no lleva noqa; el import va aparte para que se
# lea que es una mudanza y que `test_graficos.py` la sigue llamando por este
# nombre.
from graficos.compras._comun import _llave_documento_parquet
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


_KEY_GRID_DOCS = "sunat_docs_grid"
"""La `key=` del AgGrid de documentos. Constante y no literal porque la usan
DOS: el propio grid y la inyección que le escucha el hover para encender los
KPIs de cada columna — que lo busca por esa key y no por «el primer AgGrid
de la página», que en esta página es otro (regla #455)."""


_FILAS_DOCS = 8
"""Filas que RESERVA la tabla de documentos. Un techo, no un alto: lo que
sobra scrollea adentro (y sobra casi siempre — 244 comprobantes en un mes
corriente, 4.618 en doce meses).

8 a pedido (2026-10-02, «que la tabla solo muestre 8 filas»: la idea es ver
la tabla y la tarjeta de abajo en UNA pantalla). Antes 10 (2026-09-18,
«mostremos menos filas en el cuadro, solo 10»).
Venía de `alturas.APOYO` como techo, que a 24px por fila daba 14. Mismo
patrón —y mismo nombre— que `_FILAS_PROD` y `_FILAS_RANK` del resto de
Compras: el alto de una tabla-ranking se declara en FILAS, no en px."""


_ALTO_FILA_DOS = ALTO_FILA_RANK + 14
"""Alto de una fila de la tabla que necesita DOS líneas (el importe de
SUNAT arriba y lo que dice el sistema, o la conversión al papel, debajo).

Los 14 son la caja de la segunda línea: `_JS_IMPORTE` la escribe en 10.5px
con `line-height: 1.18`, o sea 12.4px, y sobran 1.6 de aire. No es un alto
suelto: sale de `ALTO_FILA_RANK` (el de todas las tablas-ranking de
Compras) y lo sigue si ése cambia. El delta es el MISMO que tenía cuando
la tabla iba a 30/44, porque lo que se apiló no cambió — la fila de una
línea es la que adelgazó."""


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


def _parquet_agrupado_por_documento(d, col_fecha, fecha_ini, fecha_fin,
                                    notas=None):
    """Compras del parquet agrupadas a una fila por (documento, RUC),
    ACOTADAS al rango que se está comparando — más las notas de crédito
    del Almacén (`notas`, la consulta del Sheet), una fila por nota en
    negativo, como las trae el SIRE (regla #604; ver `_notas_del_rango`).

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
    notas_rango = _notas_del_rango(notas, d, ini, fin, columnas)
    if dd.empty:
        return notas_rango

    dd["documento"] = _llave_documento_parquet(dd["NUM_DOCUMENTO"])
    # `fillna("")` antes del `astype(str)`: un RUC nulo saldría «nan», y
    # el cruce lo tomaría por el RUC de OTRO proveedor en vez de por uno
    # que falta (regla #606).
    dd["ruc_pq"] = (dd[COL_RUC_PARQUET].fillna("").astype(str).str.strip()
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
    if notas_rango.empty:
        return g
    return pd.concat([g, notas_rango], ignore_index=True)


def _notas_del_rango(notas, d, ini, fin, columnas):
    """Las notas de crédito PROCESADAS del Almacén con fecha en `[ini, fin)`,
    con las columnas del lado sistema del cruce (regla #604).

    Hasta el 2026-10-04 el cruce sólo miraba `compras.parquet`, que no trae
    notas: toda nota del SIRE salía «Solo SUNAT», la que el Almacén tenía
    registrada y la que no — y ésas son lo que hay que ir a cargar (en 2026,
    11 en el Almacén contra 61 en SUNAT). Con éstas, una nota registrada
    sale «Coincide» y «Solo SUNAT» vuelve a significar lo que dice.

    La llave es la de las facturas (`_llave_documento_parquet`):
    `N0E001000000068` → `E001-68`, igual que el SIRE. Montos en soles y en
    negativo (`definicion_compra.como_documentos`); el RUC sale de `d`. Una
    nota GENERADA (estado 01) no entra: en el Almacén todavía no resta, y
    marcarla «Coincide» escondería eso."""
    nd = definicion_compra.como_documentos(notas, d)
    if nd.empty:
        return pd.DataFrame(columns=columnas)
    nd = nd[(nd["fecha"] >= ini) & (nd["fecha"] < fin)]
    if nd.empty:
        return pd.DataFrame(columns=columnas)
    return pd.DataFrame({
        "documento": _llave_documento_parquet(nd["nota"]),
        "ruc_pq": nd["ruc"],
        "proveedor_pq": nd["proveedor"],
        "base_pq": nd["base"],
        "igv_pq": nd["igv"],
        "total_pq": nd["total"],
        "fecha_pq": nd["fecha"],
        "num_doc_pq": nd["nota"],
    }, columns=columnas).reset_index(drop=True)


def _es_nota_sire(r):
    """`True` si la fila del SIRE es una nota de crédito: su tipo de
    comprobante es el 07 de SUNAT o, si la fila no lo trae (los tests arman
    el SIRE a mano), su base es negativa."""
    tipo = str(r.get("tipo_cdp") or "").strip()
    if tipo:
        return tipo == "07"
    base = (float(r.get("base_imponible") or 0)
            + float(r.get("no_gravado") or 0))
    return base < 0


def _comparar_montos(base_sunat, igv_sunat, total_sunat, cand):
    """Las tres cifras de una fila del SIRE contra un candidato del sistema:
    los montos del sistema, las diferencias y el `estado` («Coincide» o
    «Diferencia»). Una sola cuenta para dos usos: el veredicto de la fila
    y, antes, decidir si un candidato de OTRO RUC es el mismo documento
    (regla #606)."""
    base_sist, total_sist = float(cand["base_pq"]), float(cand["total_pq"])
    dif_base = round(base_sunat - base_sist, 2)
    dif_total = round(total_sunat - total_sist, 2)
    # `.get()` y no `[...]`: hay llamadores (los tests) que arman
    # `g_parquet` a mano sin esta columna — mismo criterio que
    # `num_doc_pq`. Y `pd.isna` cubre los dos casos de ausencia:
    # la columna que no vino y el parquet viejo sin `TOTAL IGV`.
    _igv_crudo = cand.get("igv_pq")
    _hay_igv = _igv_crudo is not None and not pd.isna(_igv_crudo)
    igv_sist = float(_igv_crudo) if _hay_igv else None
    dif_igv = round(igv_sunat - igv_sist, 2) if _hay_igv else None
    estado = ("Coincide"
              if abs(dif_base) <= _TOLERANCIA_CENTAVOS
              and abs(dif_total) <= _TOLERANCIA_CENTAVOS
              and (dif_igv is None
                   or abs(dif_igv) <= _TOLERANCIA_CENTAVOS)
              else "Diferencia")
    return {"base": base_sist, "igv": igv_sist, "total": total_sist,
            "dif_base": dif_base, "dif_igv": dif_igv, "dif_total": dif_total,
            "estado": estado}


def cruzar_con_parquet(df_sire, g_parquet):
    """Compara cada comprobante del SIRE contra su equivalente en el
    parquet de Compras (`g_parquet` — ver `_parquet_agrupado_por_documento`,
    YA acotado al mismo rango).

    Empareja por `documento`, nota contra nota y factura contra factura
    (`_es_nota_sire`, regla #604), y entre los candidatos que compartan esa
    clave prioriza el que tenga el MISMO RUC (limpio con `.strip()` de
    ambos lados — ver `COL_RUC_PARQUET`). Si no hay uno con el RUC exacto:

      · UN SOLO candidato: se acepta si a uno de los dos lados le falta el
        RUC (no hay con qué desmentirlo). Si los dos lo traen y son
        DISTINTOS, se acepta sólo si los montos calzan («Coincide»): es el
        mismo documento cargado en el Almacén con otro proveedor. Con montos
        distintos es otro emisor que reusa el serie-número — `E001-1067` lo
        tienen decenas — y queda sin par: «Solo SUNAT» de un lado, «Solo
        sistema» del otro, en vez de una «Diferencia» falsa (regla #606).
      · VARIOS: desambigua por NOMBRE (normalizado con `utils._norm`, acepta
        que uno contenga al otro) como red de seguridad — para cuando el
        RUC del parquet venga vacío o con un formato raro en esa fila.

    Si ningún candidato es plausible, NO fuerza el emparejamiento: mejor un
    documento "Solo SUNAT" de más que cruzarlo contra la factura de otro
    proveedor.

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

    # `to_dict("records")` y no `iterrows()`: iterrows arma una Series por
    # fila y con miles de comprobantes se llevaba la mayor parte de cada
    # clic en la tabla (2026-10-02, regla #589). Los valores son los mismos.
    for r in df_sire.to_dict("records"):
        doc = str(r.get("documento", ""))
        ruc_sire = str(r.get("ruc_proveedor") or "").strip()
        prov_sire = str(r.get("proveedor", ""))
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
        sub = candidatos.get(doc)
        elegido = None
        if sub is not None and len(sub):
            # NOTA CONTRA NOTA Y FACTURA CONTRA FACTURA (regla #604). El
            # número no dice de qué tipo es el comprobante: `E001-1` es la
            # primera factura de un emisor Y su primera nota de crédito.
            # Sin esta separación, la nota E001-1 del SIRE se emparejaba con
            # la FACTURA E001-1 del mismo RUC («Diferencia» de S/ 836 en
            # 2026), y desde que el sistema trae sus notas, una factura y
            # una nota con el mismo número caían juntas como candidatas. En
            # el sistema la nota es la que va en negativo.
            _neg = pd.to_numeric(sub["base_pq"], errors="coerce") < 0
            sub = sub[_neg == _es_nota_sire(r)]
            por_ruc = sub[sub["ruc_pq"] == ruc_sire] if ruc_sire else sub.iloc[0:0]
            if len(por_ruc) == 1:
                elegido = por_ruc.iloc[0]
            elif len(sub) == 1:
                # Único candidato y el RUC no calzó. Si a uno de los dos
                # lados le falta, no hay con qué desmentirlo: se acepta,
                # como antes de tener columna de RUC. Si los DOS lo traen y
                # son distintos, casi siempre es otro proveedor que usa el
                # mismo serie-número (`E001-1067` lo tienen decenas): en 12
                # meses, 33 «Diferencia» falsas contra facturas de otro
                # emisor y de meses o años antes. Pero no siempre: 9 eran
                # el MISMO documento —misma fecha, mismo monto al céntimo—
                # cargado en el Almacén con otro proveedor (un RUC con un
                # dígito cambiado, una cadena con el RUC de su empresa
                # hermana). Ésos se aceptan sólo si los montos calzan: sin
                # par, saldrían «Solo SUNAT» con el botón de importarlos
                # otra vez a la vista. Regla #606.
                unico = sub.iloc[0]
                if (not ruc_sire or not str(unico["ruc_pq"] or "").strip()
                        or _comparar_montos(base_sunat, igv_sunat, total_sunat,
                                            unico)["estado"] == "Coincide"):
                    elegido = unico
            else:
                # Varios candidatos y ninguno con el RUC exacto: red de
                # seguridad por nombre, como se hacía antes de tener RUC.
                n_sire = _norm(prov_sire)
                for _, cand in sub.iterrows():
                    n_pq = _norm(str(cand["proveedor_pq"]))
                    if n_sire and n_pq and (n_sire in n_pq or n_pq in n_sire):
                        elegido = cand
                        break

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
            _m = _comparar_montos(base_sunat, igv_sunat, total_sunat, elegido)
            base_sist, igv_sist, total_sist = _m["base"], _m["igv"], _m["total"]
            dif_base, dif_igv, dif_total = _m["dif_base"], _m["dif_igv"], _m["dif_total"]
            estado = _m["estado"]
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
    for cand in g_parquet.to_dict("records"):
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


# ===========================================================================
# FILTRO por proveedor
# ===========================================================================
# El tercer eje de la tabla, después de la fecha (el pill de la tarjeta) y
# del período tributario («Mes en SUNAT»). Agregado 2026-09-06, a pedido.

_TODOS_PROV = "Todos los proveedores"
"""Etiqueta de la opción «sin filtro». Primera de la lista."""


def _clave_proveedor(ruc, nombre):
    """Identidad del proveedor: el RUC si lo hay, si no el nombre
    normalizado.

    Mismo criterio que `_ranking_proveedores`, y por el mismo motivo: SUNAT
    devuelve la razón social tal como está en su padrón y basta una tilde o
    un «S.A.C.» abreviado distinto entre períodos para partir un proveedor
    en dos. El nombre queda de red de seguridad para las filas que no traen
    RUC utilizable — las «Solo sistema» viejas del parquet, sobre todo.
    """
    r = str(ruc or "").strip()
    return r if r else _norm(str(nombre or ""))


def _claves_proveedor_cruce(df):
    """La identidad del proveedor de CADA fila del cruce, mirando los DOS
    lados.

    Las filas «Solo sistema» no tienen `ruc_proveedor` ni `proveedor` —no
    hay comprobante en el SIRE del que sacarlos— y son justamente las que
    más interesa poder aislar: son plata cargada sin comprobante
    electrónico detrás. Por eso la clave cae al lado del parquet
    (`ruc_sistema` / `proveedor_sistema`) cuando el del SIRE viene vacío,
    y no al revés: un documento que existe en las dos fuentes tiene que
    caer en el MISMO grupo que sus hermanos de una sola.
    """
    return pd.Series(
        [_clave_proveedor(r.get("ruc_proveedor") or r.get("ruc_sistema"),
                          r.get("proveedor") or r.get("proveedor_sistema"))
         for r in df.to_dict("records")],
        index=df.index, dtype="object")


def _claves_proveedor_sire(df):
    """La misma clave, para el df crudo del SIRE (que sólo tiene un lado).

    Existe porque el filtro también recorta lo que resumen los gráficos del
    panel de abajo, y ésos leen `vis`, no el cruce.
    """
    return pd.Series(
        [_clave_proveedor(r.get("ruc_proveedor"), r.get("proveedor"))
         for r in df.to_dict("records")],
        index=df.index, dtype="object")


def _opciones_proveedor(df_cruce, claves):
    """`(etiquetas, mapa etiqueta -> clave)` para el desplegable.

    Ordenadas por MONTO descendente, como el ranking: al abrir la lista lo
    primero que se ve es dónde está la plata. Buscar uno puntual por nombre
    lo resuelve el buscador que el propio `selectbox` trae.

    **La etiqueta es sólo el nombre, sin el conteo de documentos**, y no es
    por minimalismo: el widget vive en media columna de la tarjeta (~200px)
    y el ellipsis come por el FINAL, así que el conteo sería justo lo
    primero que desaparece. Los conteos por proveedor están enteros en el
    ranking del panel de abajo, que para eso es una tabla.

    El monto sale del lado SUNAT y cae al del sistema cuando el documento
    no está en el SIRE: si no cayera, los proveedores que sólo existen en
    el parquet valdrían 0 y quedarían todos al fondo de la lista.
    """
    tot = pd.to_numeric(df_cruce.get("total_sunat"), errors="coerce")
    tot = tot.fillna(pd.to_numeric(df_cruce.get("total_sistema"),
                                   errors="coerce")).fillna(0.0)
    nom = df_cruce["proveedor"].astype(str).str.strip()
    nom = nom.where(nom != "",
                    df_cruce["proveedor_sistema"].astype(str).str.strip())
    g = (pd.DataFrame({"clave": claves.values, "nombre": nom.values,
                       "valor": tot.values})
         # `max` y no `first`: dentro de un mismo proveedor puede haber
         # filas sin nombre (las «Solo sistema» sin razón social en el
         # parquet) y `first` se quedaría con la cadena vacía si esa fila
         # cae primera. Cualquier nombre real gana contra "".
         .groupby("clave", sort=False)
         .agg(nombre=("nombre", "max"), valor=("valor", "sum"))
         .reset_index()
         .sort_values("valor", ascending=False))

    etiquetas, mapa = [_TODOS_PROV], {}
    for _, r in g.iterrows():
        nombre = str(r["nombre"]).strip() or str(r["clave"])
        if nombre in mapa:
            # Dos RUC distintos con la misma razón social. Se desempata
            # agregándole el RUC al SEGUNDO; el primero se queda con el
            # nombre pelado, que es lo único que no rompe la etiqueta que
            # el usuario pueda tener ya elegida.
            nombre = f"{nombre} · {r['clave']}"
        etiquetas.append(nombre)
        mapa[nombre] = r["clave"]
    return etiquetas, mapa


def _filtro_proveedor(slot, df_cruce, claves):
    """Dibuja el filtro en el hueco que la cabecera reservó y devuelve la
    clave elegida (`None` = todos).

    Va en un `st.empty()` de arriba y se rellena acá abajo por lo mismo que
    el botón de Excel: sus opciones son los proveedores del cruce, y el
    cruce se calcula después de dibujar la cabecera. Es la única forma de
    tener un control arriba que dependa de algo de abajo sin partir el
    flujo en dos reruns.

    El estado va en un ESPEJO que guarda la CLAVE, no la etiqueta. Dos
    motivos, los dos medidos como bugs en otras vistas:

      · El widget se dibuja dentro de `_cuerpo`, que tiene salidas
        tempranas (sin rango, SUNAT caído, rango vacío). Un widget que deja
        de renderizarse pierde su estado —regla #211—, así que sin espejo,
        pasar por un rango vacío y volver perdería el proveedor elegido.
      · La etiqueta puede no existir en el rango nuevo. Ahí el espejo no
        resuelve y se cae a «Todos», que es la degradación correcta: mejor
        mostrar todo que filtrar por un proveedor que no compró nada.
    """
    etiquetas, mapa = _opciones_proveedor(df_cruce, claves)
    inverso = {v: k for k, v in mapa.items()}
    k_w, k_eco = "sunat_prov", "sunat_prov__eco"
    # Sólo se re-siembra cuando lo que hay NO sirve: si el usuario acaba de
    # elegir, su etiqueta está en la lista y no hay que tocar nada.
    # Pisarla siempre desde el espejo descartaría la elección recién hecha.
    if st.session_state.get(k_w) not in etiquetas:
        st.session_state[k_w] = inverso.get(st.session_state.get(k_eco),
                                            _TODOS_PROV)
    with slot:
        sel = st.selectbox(
            "Proveedor", etiquetas, key=k_w, label_visibility="collapsed",
            help="Filtra la tabla, los KPIs, el Excel y los gráficos de "
                 "abajo por un proveedor. La lista sale de los DOS lados "
                 "del cruce, así que incluye a los que sólo están cargados "
                 "en el sistema. Se puede escribir para buscar.",
        )
    st.session_state[k_eco] = mapa.get(sel)
    return mapa.get(sel)


def poner_proveedor(clave):
    """Deja elegido el proveedor `clave` (o todos, con `None`) en el filtro
    de la tabla, desde afuera: lo usan las vistas de resumen al llevar a la
    tabla (regla #683). Se escribe el ESPEJO y se suelta la key del widget,
    que al dibujarse se re-siembra desde él (ver `_filtro_proveedor`)."""
    st.session_state["sunat_prov__eco"] = clave or None
    st.session_state.pop("sunat_prov", None)


def poner_estado(estado):
    """Lo mismo para el filtro «Está vs Sistema»."""
    st.session_state["sunat_estado__eco"] = estado or None
    st.session_state.pop("sunat_estado", None)


_TODOS_ESTADOS = "Todos los estados"

_ESTADOS_CRUCE = ("Coincide", "Diferencia", "Solo SUNAT", "Solo sistema")
"""Los cuatro valores de la columna `estado` que produce
`cruzar_con_parquet`, EN ORDEN DE LECTURA y no alfabético: primero lo que
está bien, después lo que hay que revisar de menos a más grave. Es el mismo
orden en que los enumera la tira de KPIs.

Se declaran acá y no se derivan del df a propósito: la lista de opciones del
filtro tiene que ser la MISMA en todos los rangos. Derivándola, un estado
sin filas ese día desaparecería del desplegable y el control cambiaría de
forma según el dato — y encima el usuario no podría enterarse de que ese
estado existe y hoy está en cero. Con la lista fija, el «(0)» lo dice."""


def _filtro_estado(slot, df_cruce):
    """El filtro de «Está vs Sistema». Devuelve el estado elegido, o `None`
    (= todos).

    MISMO MOLDE que `_filtro_proveedor` —hueco reservado arriba, relleno acá
    abajo con un espejo del VALOR y no de la etiqueta—, y por las mismas dos
    razones: se dibuja dentro de `_cuerpo`, que tiene salidas tempranas (un
    widget que deja de renderizarse pierde su estado, regla #211), y la
    etiqueta cambia sola porque LLEVA EL CONTEO.

    **La etiqueta sí lleva el conteo**, al contrario que la de proveedor (ver
    su docstring: ahí el ellipsis se comía justo el número). Acá el texto más
    largo es «Solo sistema (108)» y la columna mide ~200px, así que entra — y
    hace falta que entre: desde que la tira de KPIs sólo se ve al pasar el
    cursor por su columna, el desplegable es el único sitio donde el censo de
    los cuatro estados está a la vista sin buscarlo.

    Filtra la TABLA, el Excel y los gráficos de abajo, pero **NO la tira de
    KPIs**, que es la única excepción de las cuatro de esta tarjeta. Es a
    propósito y no contradice a la regla de «un KPI que cuenta 65 sobre una
    tabla que muestra 3»: esa tira ES el censo del que este filtro elige un
    renglón, así que recortarla con él la dejaría repitiendo la elección
    («14 docs · 14 con diferencia») y sin el denominador. Lo que evita
    cualquier duda es que el grupo «docs» pasa a decir «14 de 244 docs»
    mientras el filtro está puesto. Ver `arquitectura.md` regla #461.
    """
    conteos = (df_cruce["estado"].value_counts()
               if df_cruce is not None and not df_cruce.empty
               else pd.Series(dtype="int64"))
    et_todos = f"{_TODOS_ESTADOS} ({len(df_cruce):,})"
    etiquetas, mapa = [et_todos], {et_todos: None}
    for _e in _ESTADOS_CRUCE:
        _et = f"{_e} ({int(conteos.get(_e, 0)):,})"
        etiquetas.append(_et)
        mapa[_et] = _e
    inverso = {v: k for k, v in mapa.items()}
    k_w, k_eco = "sunat_estado", "sunat_estado__eco"
    if st.session_state.get(k_w) not in etiquetas:
        st.session_state[k_w] = inverso.get(st.session_state.get(k_eco),
                                            et_todos)
    with slot:
        sel = st.selectbox(
            "Está vs Sistema", etiquetas, key=k_w,
            label_visibility="collapsed",
            help="Filtra la tabla, el Excel y los gráficos de abajo por el "
                 "estado del cruce. «Coincide» es lo normal; los otros tres "
                 "son lo que hay que revisar — un comprobante que SUNAT ve y "
                 "el sistema no, uno cargado sin comprobante detrás, o los "
                 "dos con importes distintos. El número entre paréntesis es "
                 "cuántos hay en el rango y el proveedor elegidos.",
        )
    st.session_state[k_eco] = mapa.get(sel)
    return mapa.get(sel)


def _pct_de(n, total):
    """`n` como porcentaje de `total`, con un decimal. None si `total` es 0.

    Los dos bordes no se redondean. 1 de 4.320 es el 0,02 %, y «0.0%» al
    lado de un documento con diferencia se lee como una contradicción: sale
    «<0.1%». Igual arriba: 4.319 de 4.320 no es «100.0%».
    """
    if not total:
        return None
    p = n / total * 100
    if 0 < p < 0.05:
        return "<0.1%"
    if 99.95 <= p < 100:
        return ">99.9%"
    return f"{p:.1f}%"


_BARRAS_CRUCE = ("Total", "En SUNAT", "En sistema", "Coinciden",
                 "Con diferencia", "Solo SUNAT", "Solo sistema")
"""Las barras del «Resumen del cruce», en orden de lectura: el universo,
sus dos lados y cómo se reparte. «Total» es la UNIÓN —cada documento una
vez, esté de un lado, del otro o de los dos—, así que los cuatro estados
suman 100 % y «En SUNAT» + «En sistema» suman más (los que coinciden o
difieren están en los dos)."""


_TRAMOS_FIDELIDAD = (
    ("cuadran", "Coincide", "Cargados y cuadran",
     f"Están en SUNAT y en el sistema, y cuadran base, IGV y total (hasta "
     f"S/ {_TOLERANCIA_CENTAVOS:.2f} de diferencia)."),
    ("diferencia", "Diferencia", "Cargados con diferencia",
     "Están en SUNAT y en el sistema, pero la base, el IGV o el total no "
     "cuadran: revisar."),
    ("falta", "Solo SUNAT", "Falta cargar en el sistema",
     "SUNAT los tiene y el sistema todavía no."),
)
"""Los tres casos en que se reparte lo que reporta SUNAT, y que suman su
100 %: `(clave, estado del cruce, nombre, explicación)`. Desde el
2026-10-02 el «Resumen del cruce» mide la FIDELIDAD respecto de SUNAT (a
pedido: «mi referencia principal debe ser SUNAT»): la base es SUNAT y no
la unión de las dos fuentes. Regla #630."""

_AYUDA_FUERA = ("Cargados en el sistema sin comprobante en SUNAT, al menos "
                "por ahora. No son parte de lo que reporta SUNAT: no suman "
                "al 100 %.")
"""El tooltip de «Fuera de SUNAT» (el estado «Solo sistema»)."""

_DIAS_RECIENTES = 7
"""Cuántos días hacia atrás cuentan como «recientes» en lo que falta cargar:
un comprobante emitido hace tres días que todavía no está en el sistema
puede ser sólo demora de carga, no un error. El resumen lo dice aparte."""


def _fidelidad_cruce(df, recientes_desde=None):
    """La fidelidad de un cruce respecto de SUNAT, en documentos y en soles.

    `{"doc": {...}, "soles": {...}, "recientes": (n, soles)}`, con las
    claves `sunat` (la base: cuadran + diferencia + falta), las de
    `_TRAMOS_FIDELIDAD` y `fuera` («Solo sistema», que no suma a la base).

    Los soles de lo que está en SUNAT salen de `total_sunat` (el registro
    viene en soles, regla #313); los de «fuera», de `total_sistema`, que
    es lo único que hay. EN VALOR ABSOLUTO: desde la #604 el cruce trae las
    notas de crédito, en negativo, y sumadas con su signo una nota sin
    cargar RESTARÍA de lo que falta — hasta dejar un tramo en negativo. Una
    nota de −S/ 5,000 sin cargar es S/ 5,000 que no cuadran con SUNAT.
    `recientes` cuenta lo que falta cargar emitido desde `recientes_desde`
    (`fecha_sunat`); sin fecha, ceros.
    """
    claves = ("sunat",) + tuple(t[0] for t in _TRAMOS_FIDELIDAD) + ("fuera",)
    out = {"doc": dict.fromkeys(claves, 0),
           "soles": dict.fromkeys(claves, 0.0), "recientes": (0, 0.0)}
    if df is None or getattr(df, "empty", True) or "estado" not in df.columns:
        return out

    def _montos(col):
        if col not in df.columns:
            return pd.Series(0.0, index=df.index)
        return pd.to_numeric(df[col], errors="coerce").fillna(0.0).abs()

    est = df["estado"].astype(str)
    t_sunat, t_sis = _montos("total_sunat"), _montos("total_sistema")
    for clave, estado, _n, _a in _TRAMOS_FIDELIDAD:
        m = est == estado
        out["doc"][clave] = int(m.sum())
        out["soles"][clave] = float(t_sunat[m].sum())
    m_fuera = est == "Solo sistema"
    out["doc"]["fuera"] = int(m_fuera.sum())
    out["soles"]["fuera"] = float(t_sis[m_fuera].sum())
    for medida in ("doc", "soles"):
        out[medida]["sunat"] = sum(out[medida][t[0]] for t in _TRAMOS_FIDELIDAD)
    if recientes_desde is not None and "fecha_sunat" in df.columns:
        f = pd.to_datetime(df["fecha_sunat"], errors="coerce").dt.date
        m = (est == "Solo SUNAT") & f.notna() & (f >= recientes_desde)
        out["recientes"] = (int(m.sum()), float(t_sunat[m].sum()))
    return out


def _conteos_cruce(df):
    """Documentos de un cruce por barra de `_BARRAS_CRUCE`."""
    if df is None or getattr(df, "empty", True) or "estado" not in df.columns:
        return dict.fromkeys(_BARRAS_CRUCE, 0)
    c = df["estado"].value_counts()
    n = int(len(df))
    coi, dif = int(c.get("Coincide", 0)), int(c.get("Diferencia", 0))
    ssu, ssi = int(c.get("Solo SUNAT", 0)), int(c.get("Solo sistema", 0))
    return {"Total": n, "En SUNAT": n - ssi, "En sistema": n - ssu,
            "Coinciden": coi, "Con diferencia": dif,
            "Solo SUNAT": ssu, "Solo sistema": ssi}


def _publicar_conteos(df):
    """Deja los conteos del cruce para el KPI de la vista en la columna.

    Los publicaba la tira de KPIs de la tabla (`_kpis_cruce`) hasta que se
    fue, el 2026-10-02. Se PUBLICAN en vez de recalcularse allá porque el
    lado SUNAT sale de la consulta al SIRE que se acaba de hacer acá — el
    rail no puede dispararla sola para decorar un rótulo. Llegan un rerun
    tarde (el rail se dibuja antes que esta vista): hasta que Documentos se
    abra una vez el KPI muestra sólo el lado del sistema. Es la degradación
    correcta.
    """
    k = _conteos_cruce(df)
    f = _fidelidad_cruce(df)["doc"]
    st.session_state["_cp_docs_cruce"] = {
        "sunat": k["En SUNAT"],
        "sistema": k["En sistema"],
        # Lo que NO cuadra CONTRA SUNAT, en un solo número: el rail lo
        # pinta como excepción (ámbar). Desde el 2026-10-02 (#630) son los
        # documentos de SUNAT con diferencia o sin cargar; los cargados sin
        # comprobante en SUNAT («fuera») van aparte, porque no son parte de
        # la base contra la que se mide.
        "revisar": f["diferencia"] + f["falta"],
        "fuera": f["fuera"],
        "fidelidad": _pct_de(f["cuadran"], f["sunat"]),
    }


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
        // SOLO EN LA FILA ELEGIDA (2026-09-18, a pedido). La segunda linea
        // hacia que 1 de cada 10 filas midiera 38 y las otras 24, y una
        // tabla con dos altos de fila se lee como dos tablas pegadas. Que
        // la fila se ABRA al clickearla no pierde la senial: la columna
        // «Esta vs Sistema» sigue diciendo «Diferencia» en ambar en todas.
        // Quien vuelve a medir la fila y a repintar la celda es el
        // `onRowClicked` de mas abajo. Ver arquitectura.md #462.
        if (texto && p.node && p.node.isSelected()) {
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
        // EL OJO Y EL NÚMERO SON EL BOTÓN DE LA FICHA (2026-10-02, a pedido,
        // como en el facturador que mostró el usuario): el clic acá abre la
        // modal, el resto de la fila sólo la elige. El clic lo atiende
        // `onCellClicked`, en las opciones de la grilla.
        this.eGui.style.cursor = 'pointer';
        this.eGui.title = 'Ver el comprobante';
        var NS = 'http://www.w3.org/2000/svg';
        var ojo = document.createElementNS(NS, 'svg');
        ojo.setAttribute('viewBox', '0 0 24 24');
        ojo.setAttribute('width', '14');
        ojo.setAttribute('height', '14');
        ojo.setAttribute('fill', 'none');
        ojo.setAttribute('stroke', '__ACENTO__');
        ojo.setAttribute('stroke-width', '2');
        ojo.style.verticalAlign = '-2px';
        ojo.style.marginRight = '5px';
        var a = document.createElementNS(NS, 'path');
        a.setAttribute('d', 'M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z');
        var b = document.createElementNS(NS, 'circle');
        b.setAttribute('cx', '12'); b.setAttribute('cy', '12'); b.setAttribute('r', '3');
        ojo.appendChild(a); ojo.appendChild(b);
        this.eGui.appendChild(ojo);
        var t = document.createElement('span');
        t.textContent = p.value == null ? '' : p.value;
        t.style.textDecoration = 'underline';
        t.style.textDecorationColor = 'transparent';
        t.style.textUnderlineOffset = '2px';
        this.eGui.onmouseenter = function(){ t.style.textDecorationColor = 'currentColor'; };
        this.eGui.onmouseleave = function(){ t.style.textDecorationColor = 'transparent'; };
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
""".replace("__COLORES__", json.dumps(_COLOR_CHIP)).replace("__ACENTO__", ACENTO))
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


@st.cache_data(ttl=3600, show_spinner=False, max_entries=2)
def _tablas_tipo(sello, version, _d):
    """Lo que el historial del Almacén dice de cada proveedor y documento
    (`tipo_compra.tablas_almacen`): medio segundo con 53.000 líneas y no
    depende del rango, así que se calcula una vez por versión del parquet.
    `version` es `tipo_compra.VERSION`: cambiar las reglas no sirve una
    tabla vieja. `sello` lleva también el del maestro, de donde sale qué
    producto tiene kardex (`TIPO PRODUCTO`, regla #673). Regla #640."""
    import data

    maestro = data.cargar("inventariovalorizado.parquet")
    return tipo_compra.tablas_almacen(
        _d, tipo_compra.tipos_de_producto(maestro))


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

    LAS OCHO, y por qué no son más (NUEVE desde el 2026-10-11, con «Tipo»):
      · Fecha, Documento, Proveedor — la identidad.
      · Tipo — QUÉ se compró: Mercadería, Otros bienes, Servicios o
        Financiero (`tipo_compra.py`, reglas #640 y #673). No es el tipo de
        comprobante, que sigue siendo un chip.
      · Base, IGV, Total — el dinero, con la segunda línea de
        `_JS_IMPORTE` cuando el sistema dice otra cosa.
      · D — la detracción, que SUNAT ya marca y no se mostraba en ningún
        lado (1.145 de 16.678 en el registro completo).
      · «Está vs Sistema» — el estado del cruce.
    Lo demás se midió y se dejó afuera: el tipo de comprobante es 97,6 %
    «Factura» (va como chip, ver `_JS_DOCUMENTO`), «Fecha de vencimiento» viene vacía o
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

    EL LOOK ES EL DEL RANKING DE PROVEEDORES desde el 2026-09-18, a pedido
    ("que tenga similar diseño... color, tamaño, alto de filas"): tema
    `streamlit` + `CSS_RANKING_GRID` en vez de `material` + `_css_grid`, o
    sea franja en vez de caja, cabecera blanca, sin líneas verticales,
    cuerpo 11.5 y el texto en violeta. Con las filas a 24 en vez de 30 se
    ven 14 documentos donde se veían 11, en el mismo alto de tarjeta.
    """
    if df_cruce is None or df_cruce.empty:
        st.info("No hay comprobantes que mostrar en el rango.")
        return None

    # Los campos que el cruce no lleva, por `car`. `.get` con relleno: los
    # tests arman df sin estas columnas y `cruzar_con_parquet` es publica.
    _cols = ("tipo_nombre", "moneda", "tipo_cambio", "detraccion", "estado",
             "ruc_proveedor", "serie", "numero")
    extra = {}
    if df_sire is not None and "car" in df_sire.columns:
        for r in df_sire.to_dict("records"):
            extra[str(r.get("car") or "")] = {c: r.get(c) for c in _cols}

    # Los XML que ya están en R2, en UN listado (ver
    # `sunat.claves_xml_en_r2`). La key se arma con la MISMA función que usa
    # el sync que los sube, así que no hay forma de que difieran en el nombre.
    _xml_en_r2 = (sunat.claves_xml_en_r2()
                  | st.session_state.get(_K_XML_LLEGADOS, frozenset()))

    filas = []
    # Diccionarios y no `iterrows()`, como en `cruzar_con_parquet` (#589).
    for r in df_cruce.to_dict("records"):
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
        # entera mide `_ALTO_FILA_DOS` en vez de `ALTO_FILA_RANK`
        # (`getRowHeight`). Se decide aca y no en JS para no repetir la
        # comparacion en tres renderers.
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
            # El sello del clic en el ojo/número (lo escribe `onCellClicked`):
            # es lo que distingue «abrí la ficha» de «elegí la fila».
            "_ver": 0,
            # El sello del clic en «Ingresar» (regla #683): mismo mecanismo
            # que `_ver`, pero abre la ventana de «Ingresar al Almacén».
            "_ing": 0,
            "Fecha": r.get("fecha_emision"),
            "Documento": str(r.get("documento") or ""),
            "Proveedor": str(r.get("proveedor") or "")
                         or str(r.get("proveedor_sistema") or ""),
            # Qué se compró (`tipo_compra.clasificar`, regla #640). Sin
            # tipo, una raya: el tooltip dice por qué no hubo pista.
            "Tipo": str(r.get("tipo") or "") or "—",
            "_tipo_por": str(r.get("tipo_por") or ""),
            "Base": base_u if base_u is not None else base_s,
            "IGV": igv_u if igv_u is not None else igv_s,
            "Total": total_sunat if total_sunat is not None else tot_s,
            "D": "D" if str(ex.get("detraccion") or "").strip().upper() == "D"
                 else "",
            # Sin fila del SIRE («Solo sistema») no hay comprobante que
            # bajar: la celda queda vacía, igual que la de un XML que falta.
            "XML": "✓" if ex and sunat.claves_original(ex)[1] in _xml_en_r2
                   else "",
            _COL_ESTADO: str(r.get("estado") or ""),
            # Sólo lo que SUNAT tiene y el sistema no: es lo único que hay
            # que ingresar. Sin fila del SIRE no hay XML que convertir.
            "Ingresar": ("Ingresar" if ex and str(r.get("estado") or "")
                         == "Solo SUNAT" else ""),
        })

    tv = pd.DataFrame(filas)
    tv["Fecha"] = pd.to_datetime(tv["Fecha"], errors="coerce").dt.strftime(
        "%d/%m/%Y").fillna("")

    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=True, filter=False,
                                editable=False, suppressMovable=True)
    for oculta in ("_car", "_chips", "_sim", "_base_sis", "_igv_sis",
                   "_total_sis", "_conv", "_dos", "_ver", "_ing", "_tipo_por"):
        gb.configure_column(oculta, hide=True)
    # `_tipo` va oculta pero NO muerta: con el tipo de COMPROBANTE fuera de
    # las columnas visibles (es un chip), ésta es la que permite ordenar y
    # filtrar por él sin gastar 94 px de ancho. No confundir con «Tipo», la
    # visible, que es QUÉ se compró (regla #640).
    gb.configure_column("_tipo", hide=True, headerName="Tipo de comprobante")
    gb.configure_column("Fecha", width=96, minWidth=96)
    # +19px desde que lleva el ojo (14 del ícono y 5 de aire).
    gb.configure_column("Documento", width=159, minWidth=145,
                        cellRenderer=_JS_DOCUMENTO)
    gb.configure_column("Proveedor", minWidth=170, flex=1,
                        tooltipField="Proveedor")
    # 88 px: «Otros bienes», el rótulo más largo, con el aire de la celda.
    # El tooltip es el motivo; la raya de «sin tipo», en gris.
    gb.configure_column(
        "Tipo", width=88, minWidth=88, tooltipField="_tipo_por",
        headerTooltip="Qué se compró: Mercadería (lo que lleva kardex), "
                      "Otros bienes, Servicios o "
                      "Financiero. SUNAT no lo informa: sale de cómo está "
                      "cargado en el Almacén, de lo que se le compra a ese "
                      "proveedor y de si la factura va sin IGV. El cursor "
                      "sobre la celda dice de dónde.",
        cellStyle=JsCode(
            "function(p){ return p.value === '—' ? {'color':'%s'} : {}; }"
            % GRIS_TEXTO_SUAVE))
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
    # «XML» (2026-10-02, a pedido): si el original ya se bajó a R2. Es lo
    # que decide si la ficha trae «Comprobante / Detalle / XML» o sólo el
    # botón de pedirlo, y si el conversor tiene líneas que comparar — antes
    # había que abrir el documento para enterarse.
    gb.configure_column(
        "XML", width=44, minWidth=44,
        headerTooltip="✓ = el XML original del proveedor ya está descargado. "
                      "Sin marca, se pide desde la ficha del documento.",
        cellStyle={"color": ACENTO, "fontWeight": "700",
                   "textAlign": "center"})
    # Ámbar = revisar contra SUNAT (con diferencia o sin cargar). «Coincide»
    # no se destaca — lo normal no compite por atención.
    # «Solo sistema» en GRIS OSCURO desde el 2026-10-02 (antes rojo): con
    # SUNAT como referencia, lo cargado sin comprobante en SUNAT queda
    # FUERA de la base, igual que en el «Resumen del cruce» (regla #630).
    gb.configure_column(
        _COL_ESTADO, width=126, minWidth=126,
        cellStyle=JsCode(
            "function(p){ var m={'Diferencia':'%s','Solo SUNAT':'%s',"
            "'Solo sistema':'%s'}; var c=m[p.value]; "
            "return c ? {'color':c,'fontWeight':'600'} : {'color':'%s'}; }"
            % (ADVERTENCIA_TEXTO, ADVERTENCIA_TEXTO, GRIS_TEXTO_MEDIO,
               GRIS_TEXTO)))
    # «Ingresar» (2026-10-21, regla #683): el conversor dejó de ser un modo
    # de la tarjeta de abajo y es una ventana sobre la tabla, que se abre
    # desde la fila que hay que ingresar. Se ve como un enlace.
    gb.configure_column(
        "Ingresar", headerName="", width=84, minWidth=84, sortable=False,
        headerTooltip="Abre «Ingresar al Almacén» para un comprobante que "
                      "SUNAT tiene y el sistema no.",
        tooltipValueGetter=JsCode(
            "function(p){ return p.value ? 'Ingresar al Almacén' : ''; }"),
        valueFormatter=JsCode(
            "function(p){ return p.value ? '↓ Ingresar' : ''; }"),
        cellStyle={"color": ACENTO, "fontWeight": "600", "cursor": "pointer"})
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(
        headerHeight=ALTO_HEADER_RANK,
        # TODAS las filas miden `ALTO_FILA_RANK`; sólo la ELEGIDA, y sólo si
        # tiene segunda línea, se abre a `_ALTO_FILA_DOS`. Hasta el
        # 2026-09-18 se abrían todas las que tuvieran algo que decir, y con
        # eso la tabla tenía dos altos de fila mezclados.
        getRowHeight=JsCode(
            "function(p){ return (p.data && p.data._dos"
            " && p.node && p.node.isSelected()) ? %d : %d; }"
            % (_ALTO_FILA_DOS, ALTO_FILA_RANK)),
        # Lo que hace que el clic ABRA la fila. Va en `onRowClicked` y no en
        # `onSelectionChanged` a propósito: ese último es uno de los cuatro
        # eventos del `update_on` por defecto de st_aggrid, y pisárselo
        # rompería el rerun del que cuelgan las tarjetas de abajo.
        # `onRowClicked` en `gridOptions` sí es libre (lo usa igual el
        # ranking de `proveedor.py`).
        #
        # El `setTimeout(0)` no es cosmético: AG Grid despacha `rowClicked`
        # dentro del mismo manejador que resuelve la selección, así que
        # `isSelected()` leído en el acto puede ser el de ANTES del clic —
        # la fila se abriría un clic tarde. Diferido, corre con la
        # selección ya asentada.
        onRowClicked=JsCode(
            "function(e){ var a=e.api; setTimeout(function(){ try {"
            " a.resetRowHeights();"
            " a.refreshCells({force:true,"
            " columns:['Base','IGV','Total']});"
            " } catch(x) {} }, 0); }"),
        # EL CLIC EN EL OJO/NÚMERO ABRE LA FICHA (2026-10-02, a pedido: «que
        # aparezca sólo al dar clic en el número del documento, no en
        # cualquier parte de la fila»). La grilla no le avisa a Python QUÉ
        # celda se clickeó —sólo la selección—, así que el clic deja un
        # sello en la fila (`_ver`, la hora) y la selección lo lleva.
        #
        # Y la fila se suelta y se vuelve a elegir, diferido: sin eso, el
        # ojo de una fila YA elegida no cambiaría la selección y el clic no
        # llegaría a Python; y aunque la fila sea nueva, no depende de si
        # AG Grid despacha el clic de la celda antes o después de elegirla.
        # «Ingresar» deja su propio sello (`_ing`) con el mismo truco.
        onCellClicked=JsCode(
            "function(e){ if (!e.data || !e.colDef) return;"
            " var f = e.colDef.field;"
            " if (f === 'Documento') { e.data._ver = Date.now(); }"
            " else if (f === 'Ingresar' && e.value) { e.data._ing = Date.now(); }"
            " else { return; } var n = e.node;"
            " setTimeout(function(){ try { n.setSelected(false);"
            " n.setSelected(true); } catch(x) {} }, 0); }"),
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
    )

    resp = AgGrid(
        tv, gridOptions=gb.build(),
        # OCHO filas y lo que sobre scrollea adentro, a pedido (2026-10-02;
        # antes diez, 2026-09-18: «mostremos menos filas en el cuadro, solo
        # 10»). Antes el techo era
        # `alturas.APOYO`, o sea 380px ≈ 14 filas. Mismo patrón que
        # `_FILAS_RANK`/`_FILAS_PROD` del resto de Compras: un techo, no un
        # alto — con menos de 10 comprobantes la grilla se encoge.
        height=alturas.por_filas(min(len(tv), _FILAS_DOCS),
                                 px_fila=ALTO_FILA_RANK,
                                 extra=CROMO_GRID_RANK, minimo=0),
        theme="streamlit",
        # El look del Ranking de proveedores, a pedido (2026-09-18): franja
        # en vez de caja, cabecera blanca, sin líneas verticales, cuerpo
        # 11.5 y el texto en violeta. Es el MISMO dict, no una copia — un
        # grid vive en un iframe y el `<style>` del padre no lo alcanza, así
        # que `custom_css=` es la única vía. El alto de fila y este dict son
        # UNA decisión y viajan juntos (regla #404): sin el cuerpo de 11.5
        # las filas de 24 aprietan el texto contra las líneas.
        #
        # LOS COLORES DE DATO SOBREVIVEN, y sale gratis: el violeta de
        # `.ag-cell` va SIN `!important` a propósito (ver `_css_proveedor`),
        # así que el ámbar/rojo que `cellStyle` pone INLINE en «D» y en «Está
        # vs Sistema» le gana, y las dos segundas líneas de `_JS_IMPORTE`
        # también (se pintan desde el renderer).
        custom_css={**CSS_RANKING_GRID,
                    # Con las filas de un blanco uniforme hay que marcar la
                    # SELECCIONADA: de esta tabla cuelga todo lo de abajo.
                    # El tema pinta un `::before` con el acento al 12%, que
                    # en el ranking alcanza porque ahí la selección sólo
                    # colorea una serie; acá decide TRES tarjetas, así que
                    # se queda la banda lavanda explícita. Ver
                    # `arquitectura.md` regla #235.
                    ".ag-row-selected": {
                        "background-color": f"{LAVANDA_CABECERA_GRUPO} !important",
                        "font-weight": "600 !important",
                    }},
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        key=_KEY_GRID_DOCS,
    )
    sel = resp.selected_rows
    if sel is None or (hasattr(sel, "empty") and sel.empty) or len(sel) == 0:
        return None
    fila = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
    if fila[_COL_ESTADO] == "Solo sistema":
        # No hay documento del SIRE que le corresponda: no es una carencia
        # del panel, es que ese comprobante no tiene contraparte ahí.
        return None
    doc = _fila_de(df_sire, fila)
    _atender_pedido_de_ficha(fila, doc)
    _atender_pedido_de_ingreso(fila, doc)
    return doc


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


def _pastilla_ficha(texto, tono=""):
    """Una pastilla de la cabecera de la ficha. `tono` es una clase extra
    de `estilos/_80_cards.py` (`ambar`), vacío para la lavanda de siempre."""
    return (f'<span class="sunat-ficha-pill {tono}">'
            f'{html.escape(str(texto))}</span>')


def _cabecera_ficha_html(doc):
    """La cabecera de la ficha: qué es el documento y cuánto vale, en UN
    renglón. A la izquierda el tipo y el estado en SUNAT (pastillas) y,
    debajo, RUC y fechas; a la derecha el total en grande.

    El número del documento y el proveedor NO van acá: los dice el título
    de la modal, y repetirlos dos renglones más abajo se lee como relleno.
    El total va en soles —como lo registra SUNAT— y, si el papel es en
    otra moneda, debajo lo que imprimió el proveedor (regla #313).
    """
    pills = [_pastilla_ficha(sunat._val(doc, "tipo_nombre", "Comprobante"))]
    estado = sunat._val(doc, "estado", "")
    if estado:
        pills.append(_pastilla_ficha(estado))
    if str(doc.get("detraccion") or "").strip().upper() == "D":
        pills.append(_pastilla_ficha("Con detracción", "ambar"))

    meta = [f'RUC {html.escape(sunat._val(doc, "ruc_proveedor"))}',
            f'Emitida {sunat._val(doc, "fecha_emision")}']
    venc = sunat._val(doc, "fecha_vencimiento", "")
    if venc:
        meta.append(f"Vence {venc}")

    papel = sunat._importe_del_papel(doc, "total")
    sub = (f'<div class="sunat-ficha-total-sub">{papel} en el papel · '
           f'{html.escape(sunat._moneda_con_tc(doc))}</div>' if papel else "")
    return (
        '<div class="sunat-ficha-cab">'
        f'<div class="sunat-ficha-cab-izq">'
        f'<div class="sunat-ficha-pills">{"".join(pills)}</div>'
        f'<div class="sunat-ficha-meta">{" · ".join(meta)}</div></div>'
        f'<div class="sunat-ficha-total">'
        f'<div class="sunat-ficha-total-rot">Total</div>'
        f'<div class="sunat-ficha-total-val">'
        f'{sunat._importe(doc, "total")}</div>{sub}</div>'
        '</div>')


def _ficha_html(doc):
    """Los datos del comprobante, en la pestaña «Datos» de la ficha.

    Salen de `sunat.campos_ficha()`, la misma fuente que el PDF que se
    descarga (`sunat.ficha_pdf`), así que pantalla y papel no pueden
    divergir. DOS columnas y no una lista: a la izquierda quién lo emitió
    y qué documento es, a la derecha los importes con el total en una
    banda al pie, como en un comprobante impreso. Apilados en una sola
    lista eran catorce renglones y la modal no entraba en una pantalla
    (2026-10-02, a pedido: «que entre en una pantalla y sea más
    estilizada»). En el teléfono las columnas se apilan solas
    (`estilos/_80_cards.py`).

    POR QUÉ NO ES UN PDF EMBEBIDO (probado y descartado el 2026-08-19):
    Chrome no renderiza un `data:application/pdf` dentro de un iframe con
    `sandbox`, y Streamlit monta TODOS sus iframes con sandbox. El PDF del
    proveedor se muestra como IMAGEN en la pestaña «Comprobante».
    """
    secciones = dict(sunat.campos_ficha(doc))

    def _grupo(titulo, campos):
        filas = "".join(
            f'<div class="sunat-ficha-fila"><span>{html.escape(et)}</span>'
            f'<span>{html.escape(str(v))}</span></div>'
            for et, v in campos)
        return (f'<div class="sunat-ficha-grupo">'
                f'<div class="sunat-ficha-grupo-tit">{titulo}</div>'
                f'{filas}</div>')

    importes = list(secciones.get("Importes", ()))
    # «Total» sale de la lista y va a la banda; «Total en USD» (sólo en
    # moneda extranjera) se queda como renglón, debajo de la banda.
    total = next((v for et, v in importes if et == "Total"), "—")
    resto = [(et, v) for et, v in importes
             if et != "Total" and not et.startswith("Total en")]
    papel = [(et, v) for et, v in importes if et.startswith("Total en")]

    izq = (_grupo("Emisor", secciones.get("Emisor", ()))
           + _grupo("Documento", secciones.get("Documento", ())))
    der = (_grupo("Importes", resto)
           + f'<div class="sunat-ficha-banda"><span>Total</span>'
             f'<span>{total}</span></div>'
           + "".join(f'<div class="sunat-ficha-fila"><span>{et}</span>'
                     f'<span>{v}</span></div>' for et, v in papel)
           + f'<div class="sunat-ficha-car">CAR SUNAT · '
             f'{html.escape(sunat._val(doc, "car"))}</div>')
    st.markdown(f'<div class="sunat-ficha-datos"><div>{izq}</div>'
                f'<div>{der}</div></div>', unsafe_allow_html=True)


def _tabla_detalle(lineas, doc=None):
    """Las líneas del XML, como tabla. Es lo que el registro NO tiene.

    Los importes del XML están en la moneda del PAPEL, no en soles como
    los del registro (regla #313): el símbolo sale de `doc`. Y el alto se
    acota a `_ALTO_DETALLE_FICHA`, para que la modal entre en una pantalla
    y lo que sobre scrollee adentro de la tabla."""
    if not lineas:
        st.caption("El XML no trae líneas de detalle legibles.")
        return
    tv = pd.DataFrame(lineas)
    # `doc is None` y no `doc or {}`: la fila llega como una Series de
    # pandas, y una Series no se puede evaluar como verdadero o falso —
    # `or` lanza «The truth value of a Series is ambiguous» (se vio en
    # Cloud el mismo día, al abrir un comprobante con XML).
    mon = None if doc is None else doc.get("moneda")
    sim = sunat.simbolo_moneda(mon).replace("%", "%%")
    st.dataframe(
        tv, use_container_width=True, hide_index=True,
        height=min(_ALTO_DETALLE_FICHA, 35 * (len(tv) + 1) + 3),
        column_config={
            "codigo": st.column_config.TextColumn("Código", width="small"),
            "descripcion": st.column_config.TextColumn("Descripción",
                                                       width="large"),
            "cantidad": st.column_config.NumberColumn("Cant.", format="%.2f",
                                                      width="small"),
            "unidad": st.column_config.TextColumn("Unidad", width="small"),
            "precio_unitario": st.column_config.NumberColumn(
                "P. unitario", format=f"{sim} %.2f"),
            "importe": st.column_config.NumberColumn("Importe",
                                                     format=f"{sim} %.2f"),
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
"""Alto de fila y de cabecera de la tabla de «Ingresar al Almacén». Hasta
el 2026-10-21 eran DOS tablas que tenían que compartirlos para que la fila
de una cayera a la altura de la de la otra; desde ese día es una sola
(`_grid_conversor`, regla #684) y la alineación sale sola."""


def _titulo_panel(texto, detalle, derecha=""):
    """La cabecera de cada mitad del conversor: de qué fuente es la tabla
    de abajo. Las dos mitades la dibujan IGUAL (mismo markup, mismo alto)
    porque de eso depende que las dos tablas arranquen en la misma `y` —
    ver `_ALTO_FILA_CONVERSOR`.

    `derecha` es HTML que va en el MISMO renglón, pegado al borde derecho:
    en el conversor, los datos del documento (`_datos_documento_html`). Ahí
    el `detalle` va vacío: cortado a «lo …» en una laptop decía menos que
    nada, y el renglón lo necesita el nombre del proveedor."""
    st.markdown(
        f'<div style="display:flex;align-items:baseline;gap:6px;'
        f'margin:0 0 6px;padding-bottom:4px;min-width:0;'
        f'border-bottom:1px solid {GRIS_BORDE};">'
        f'<span style="font-size:10px;font-weight:700;color:{ACENTO};'
        f'text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;'
        f'flex:none;">{texto}</span>'
        + (f'<span style="font-size:10px;color:{GRIS_TEXTO};white-space:nowrap;'
           f'overflow:hidden;text-overflow:ellipsis;min-width:0;'
           f'flex:0 2 auto;">{detalle}</span>' if detalle else '')
        + (f'<span style="margin-left:auto;display:flex;gap:6px;'
           f'align-items:baseline;min-width:0;flex:0 1 auto;">{derecha}'
           f'</span>' if derecha else '')
        + '</div>', unsafe_allow_html=True)


_JS_FORMATO_CANT = JsCode(
    "function(p){ return p.value==null ? '' : "
    "Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:3}); }")
"""Formato de las columnas de cantidad de las DOS tablas. Compartido a
propósito: si un lado redondeara a 2 decimales y el otro a 3, dos números
iguales se verían distintos justo en la vista que existe para
compararlos."""


def _datos_documento_html(doc):
    """Los datos del documento para CADA mitad del conversor: proveedor,
    RUC, fecha de emisión y moneda, en UN renglón — el del título
    (`_titulo_panel(..., derecha=)`). Hasta el 2026-10-02 eran una caja
    gris de dos renglones debajo del título; subieron a pedido, para que
    las tablas de abajo suban con ellos (~45px).

    Se arma dos veces con la MISMA función, y eso no es redundancia: es
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
        return ""
    ruc = str(doc.get("ruc_proveedor") or "—")
    prov = html.escape(str(doc.get("proveedor") or ""))
    fecha = pd.to_datetime(doc.get("fecha_emision"), errors="coerce")
    fecha = "—" if pd.isna(fecha) else f"{fecha:%d/%m/%Y}"
    # El nombre es lo único que se corta (con «…» y entero en el tooltip):
    # RUC, fecha y moneda son cortos y son los que se cotejan.
    return (
        f'<span title="{prov}" style="font-size:11px;font-weight:600;'
        f'color:{TEXTO_PRINCIPAL};white-space:nowrap;overflow:hidden;'
        f'text-overflow:ellipsis;min-width:0;">{prov}</span>'
        f'<span style="font-size:10.5px;color:{GRIS_TEXTO};'
        f'white-space:nowrap;flex:none;font-variant-numeric:tabular-nums;">'
        f'RUC {ruc} · {fecha} · {sunat._moneda_con_tc(doc)}</span>')


def _renglon_total(etiqueta, valor, sim, fuerte=False):
    """Un renglón del pie de totales. Compartido por las dos mitades para
    que los dos pies se vean iguales — mismo argumento que
    `_datos_documento_html`."""
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


def _otros_tributos(lineas_xml):
    """El ISC / ICBPER del comprobante, sumado de las LÍNEAS del XML.

    **El registro no lo trae aparte: lo trae adentro de la base.** Medido
    2026-09-05 sobre las 16.773 filas del parquet,
    `total == base + no gravado + IGV` en TODAS — porque la base gravada
    del SIRE es la base del IGV, y el ISC forma parte de ella. En la
    F003-4717 el registro anota 533.39 de base y las líneas del XML suman
    499.66: los 33.73 de diferencia son el ISC, y el único lado que los
    tiene desglosados es el XML (código de tributo 2000; 7152 el ICBPER).

    Por eso este pie no puede sacarlo del registro aunque todo lo demás
    salga de ahí. Ver `arquitectura.md` regla #314.
    """
    return sum((_num(x.get("isc")) or 0.0) + (_num(x.get("otros_tributos")) or 0.0)
               for x in (lineas_xml or []))


def _pie_sistema(doc, filas_sistema, lineas_xml=None):
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
    tributaria de la compra.

    **CORREGIDO 2026-09-05: la premisa era cierta y la conclusión no.**
    Acá decía que `total == base + no gravado + IGV` en los 16.689
    comprobantes del registro —cierto, se volvió a medir sobre 16.773 y
    da en TODAS— y de ahí concluía que «sumar líneas + IGV reconstruye el
    total sin términos escondidos». No se sigue: la base del registro y
    la suma de las líneas son DOS FUENTES distintas, y en los
    comprobantes con ISC no valen lo mismo. El SIRE mete el ISC dentro de
    la base gravada (es la base del IGV); `LineExtensionAmount` no lo
    lleva. En la F003-4717 el registro dice 533.39 y las líneas suman
    499.66.

    Son 32 de los 2.291 comprobantes con XML, y son exactamente los que
    el Almacén rechazaba: el XML de importación armaba `nNeto` con esta
    misma suma y quedaba corto por el ISC. Ver `sunat_importacion` y la
    regla #314 — misma familia que la #313: saber que dos números cuadran
    DENTRO de una fuente no dice nada sobre un tercero que viene de otra.
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
    otros = _s(_otros_tributos(lineas_xml))
    total = suma + otros + igv

    renglones = [_renglon_total("Suma de líneas", suma, sim)]
    if otros:
        # Se muestra APARTE aunque el Almacén lo cargue adentro del neto
        # (`sunat_importacion.tributos_en_el_neto`): esta columna existe
        # para poder seguir el número con el dedo hasta el TOTAL, y un
        # renglón que aparece de la nada rompe justamente eso.
        renglones.append(_renglon_total("ISC / otros tributos", otros, sim))
    renglones.append(_renglon_total("IGV", igv, sim))
    renglones.append(_renglon_total("TOTAL a cargar", total, sim, fuerte=True))
    _bloque_totales(renglones)

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

    **Los tres renglones SÍ componen el total, incluso con ISC** (medido
    2026-09-05 sobre las 16.773 filas del parquet). Lo que no cierra en
    esos casos es el chequeo de abajo, el que compara la suma de las
    líneas contra `gravado + no gravado`: el SIRE mete el ISC dentro de
    la base gravada y `LineExtensionAmount` no lo lleva, así que la
    diferencia es exactamente el ISC del XML. Se explica en vez de
    avisarse — un «⚠ revisá» sobre algo normal y explicable es ruido, y
    el que sí importa deja de leerse. Ver la regla #314.
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

    # El total del PAPEL (`PayableAmount`) puede diferir del registro: el
    # recargo al consumo y el redondeo del retail no entran al total del
    # registro del SIRE. Se usa para rotular el total y para explicar la
    # diferencia más abajo.
    pagable = _num((totales or {}).get("total"))
    cargos = _num((totales or {}).get("cargos"))
    _diverge = (total is not None and pagable is not None
                and abs(abs(pagable) - abs(total)) > _TOLERANCIA_CENTAVOS)

    filas = []
    if grav:
        filas.append(("Gravado", grav, False))
    if ngrav:
        filas.append(("No gravado", ngrav, False))
    filas.append(("IGV", igv, False))
    if total is not None:
        # «TOTAL» cuando el registro coincide con el papel; «Total registro»
        # cuando NO —recargo al consumo, redondeo—, para no leerse como si
        # se contradijera con el total del comprobante (el PDF). La
        # diferencia la explica la línea de abajo.
        filas.append(("Total registro" if _diverge else "TOTAL", total, True))

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

    _dif = (None if pagable is None or total is None
            else round(abs(pagable) - abs(total), 2))
    if _dif and abs(_dif) <= _simp.REDONDEO_MAXIMO + 1e-9:
        st.caption(f"El comprobante redondea el total a {sim} "
                   f"{abs(pagable):,.2f} ({_dif:+.2f}); SUNAT anota "
                   f"{sim} {abs(total):,.2f}. Se carga lo del comprobante.")
    elif _dif and cargos and abs(abs(_dif) - abs(cargos)) <= _TOLERANCIA_CENTAVOS:
        # EL HUECO TIENE NOMBRE cuando es el recargo al consumo. SUNAT no lo
        # suma al total del registro —no es parte de la operación gravada—
        # pero el `PayableAmount` del papel sí, y el importador lo carga
        # DENTRO del neto (ver `sunat_importacion`): el documento entra por
        # el total del comprobante y cuadra. Es normal y explicable, como el
        # ISC: se explica en vez de mandar a "revisar" un documento que el
        # Almacén acepta. Ver regla #314.
        st.caption(f"El comprobante cobra {sim} {abs(pagable):,.2f}; el "
                   f"registro anota {sim} {abs(total):,.2f}. La diferencia "
                   f"es el recargo al consumo ({sim} {abs(cargos):,.2f}), "
                   "que SUNAT no suma al registro. Al Almacén entra dentro "
                   "del neto, así que el documento se carga por el total del "
                   "comprobante.")
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
    otros = _otros_tributos(lineas)
    hueco = abs(abs(suma) - abs(grav + ngrav))
    if hueco <= _TOLERANCIA_CENTAVOS:
        return
    # EL HUECO TIENE NOMBRE cuando es el ISC. El SIRE lo cuenta dentro de
    # la base gravada —es la base del IGV— y `LineExtensionAmount` no lo
    # lleva: la F003-4717 declara 533.39 de base contra 499.66 de líneas.
    # Decirlo evita mandar a "revisar" un documento correcto, y de paso
    # deja a la vista el número que después entra al neto del Almacén.
    if otros and abs(hueco - abs(otros)) <= _TOLERANCIA_CENTAVOS:
        st.caption(f"Las líneas suman {sim} {suma:,.2f}; el registro declara "
                   f"{sim} {grav + ngrav:,.2f} porque la base gravada del "
                   f"SIRE incluye el ISC ({sim} {abs(otros):,.2f}). Al "
                   "Almacén va adentro del neto.")
        return
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


def _grid_conversor(tv, doc_id):
    """LA tabla de «Ingresar al Almacén»: cada línea del XML a la izquierda
    y, en la MISMA fila, cómo entra al Almacén a la derecha (2026-10-21, a
    pedido y con mockup aprobado, regla #684).

    Hasta ese día eran dos grillas lado a lado (pedido 2026-08-27, «dos
    tarjetas separadas, pero alineadas»), y alinearlas dependía de que
    compartieran alto de fila, de cabecera y de tabla: en la ventana se
    leían como dos cuadrantes sueltos con los números de una a distinta
    altura que los de la otra. Una grilla con DOS GRUPOS de columnas
    —«Comprobante SUNAT» y «Almacén», con una flecha en el medio— alinea
    por construcción, y los totales de abajo caen bajo su grupo.

    Las columnas de cada lado son las de antes, con los MISMOS campos en el
    lado del Almacén (`Ítem (sistema)`, `Und.`, `Cant.`, `P. unit.`,
    `Importe`): de esos nombres cuelgan `_JS_RELLENAR_VECINAS` y la
    detección de cambios de `_detalle_sistema`. Las del XML llevan sufijo
    para no chocar. Lo que se edita y cómo se guarda no cambió:

      · **Producto del Almacén** — EDITABLE contra el maestro
        (`_JS_EDITOR_PRODUCTO`); sin producto dice «elegir producto» en
        ámbar, que es lo que hay que hacer.
      · **Und.** — la de kardex del producto elegido; no se edita.
      · **Cant.** — EDITABLE; arranca en la del XML y se marca si difiere
        (el yogur de 0.96 L entra en litros, la caja de 12 en unidades).
      · **P. unit.** — DERIVADO (`_precio_derivado`): importe ÷ cantidad.
      · **Importe** — el INVARIANTE: el del XML, intacto.
      · **Cómo se eligió** — el origen, que antes iba sólo en el tooltip:
        con una columna de sobra, se lee sin pasar el cursor.
    """
    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=False, filter=False,
                                editable=False, suppressMovable=True)
    for oculta in ("_idx", "_cod_auto", "_cant_xml", "_cod_sis", "_origen",
                   "_cod_prov"):
        gb.configure_column(oculta, hide=True)
    gb.configure_column("#", width=46, minWidth=46,
                        cellStyle={"color": GRIS_TEXTO_SUAVE})
    # ── lo que dice el XML ──────────────────────────────────────────────
    gb.configure_column(
        "Ítem (XML)", headerName="Ítem del proveedor", minWidth=170, flex=1,
        tooltipValueGetter=JsCode(
            "function(p){ var c=(p.data||{})._cod_prov;"
            " return p.value + (c ? '  ·  cód. del proveedor ' + c : ''); }"))
    gb.configure_column("Cant. XML", headerName="Cant.", type=["numericColumn"],
                        width=70, minWidth=64, valueFormatter=_JS_FORMATO_CANT)
    gb.configure_column("Und. XML", headerName="Und.", width=78, minWidth=74,
                        cellStyle={"color": GRIS_TEXTO})
    gb.configure_column("P. unit. XML", headerName="P. unit.",
                        type=["numericColumn"], width=82, minWidth=74,
                        valueFormatter=_JS_IMPORTE_XML)
    gb.configure_column("Importe XML", headerName="Importe",
                        type=["numericColumn"], width=88, minWidth=80,
                        valueFormatter=_JS_IMPORTE_XML)
    gb.configure_column("→", headerName="", width=30, minWidth=30,
                        cellStyle={"color": GRIS_TEXTO_SUAVE,
                                   "textAlign": "center", "padding": "0"})
    # ── cómo entra al Almacén ───────────────────────────────────────────
    gb.configure_column(
        "Ítem (sistema)", headerName="Producto del Almacén", minWidth=170,
        flex=1, editable=True, cellEditor=_JS_EDITOR_PRODUCTO,
        valueFormatter=JsCode(
            "function(p){ return p.value ? p.value : 'Elegir producto \\u25be'; }"),
        tooltipValueGetter=JsCode(
            "function(p){ var d=p.data||{}; return d._cod_sis"
            " ? 'cód. ' + d._cod_sis + ' · clic para cambiarlo'"
            " : 'Clic y escribí para buscar en el maestro'; }"),
        cellStyle=JsCode(
            "function(p){ var base={'background':'%s','cursor':'text'};"
            " if (!p.value) { base.color='%s'; base.fontWeight='600';"
            "   base.background='%s'; return base; }"
            " var o=(p.data||{})._origen;"
            " if (o==='Sugerido') { base.color='%s'; base.fontWeight='600'; }"
            " else if (o==='Corregido') { base.color='%s'; }"
            " return base; }"
            % (LAVANDA_FONDO, ADVERTENCIA_TEXTO, ERROR_FONDO,
               ADVERTENCIA_TEXTO, ACENTO_TEXTO)))
    gb.configure_column("Und.", width=62, minWidth=56,
                        headerTooltip="Unidad de kardex del Almacén. La trae "
                                      "el producto elegido; no se edita.",
                        cellStyle={"color": GRIS_TEXTO})
    gb.configure_column(
        "Cant.", type=["numericColumn"], width=72, minWidth=66, editable=True,
        headerTooltip="Arranca en la del XML y se puede cambiar: el proveedor "
                      "factura 1 caja de 12 y el Almacén ingresa 12.",
        valueFormatter=_JS_FORMATO_CANT, valueParser=_JS_CANTIDAD_PARSER,
        cellStyle=JsCode(
            "function(p){ var base = {'background': '%s', 'cursor': 'text'};"
            " if (p.data && p.value != null && p.data._cant_xml != null"
            "     && Math.abs(p.value - p.data._cant_xml) > 1e-6) {"
            "   base.color = '%s'; base.fontWeight = '600'; }"
            " return base; }" % (LAVANDA_FONDO, ACENTO_TEXTO)))
    gb.configure_column(
        "P. unit.", type=["numericColumn"], width=84, minWidth=74,
        headerTooltip="Se calcula solo: importe ÷ cantidad. Al cambiar la "
                      "cantidad, cambia el unitario y el importe queda igual.",
        valueFormatter=_JS_PRECIO_DERIVADO, cellStyle={"color": GRIS_TEXTO})
    gb.configure_column(
        "Importe", type=["numericColumn"], width=88, minWidth=80,
        headerTooltip="Lo que costó la línea según el comprobante. No cambia "
                      "al ingresarla — tampoco los impuestos.",
        valueFormatter=_JS_IMPORTE_XML)
    gb.configure_column(
        "Cómo", headerName="Cómo se eligió", width=112, minWidth=100,
        headerTooltip="Automático: cruzado con lo ya cargado de este "
                      "documento. Sugerido: parecido de nombre en el maestro, "
                      "revisalo. Corregido: elegido a mano. Sin producto: "
                      "hay que elegirlo.",
        cellStyle=JsCode(
            "function(p){ var o=(p.data||{})._origen;"
            " if (o==='Sugerido' || o==='Sin coincidencia')"
            "   return {'color':'%s','fontSize':'11.5px'};"
            " return {'color':'%s','fontSize':'11.5px'}; }"
            % (ADVERTENCIA_TEXTO, GRIS_TEXTO)))
    gb.configure_grid_options(
        rowHeight=_ALTO_FILA_CONVERSOR, headerHeight=_ALTO_CABECERA_CONVERSOR,
        groupHeaderHeight=_ALTO_CABECERA_CONVERSOR,
        singleClickEdit=True, stopEditingWhenCellsLoseFocus=True,
        context=_lookups_maestro()[2],
        onGridReady=_JS_MAESTRO_AL_NAVEGADOR,
        onCellValueChanged=_JS_RELLENAR_VECINAS,
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
        suppressColumnVirtualisation=True,
        tooltipShowDelay=300,
    )
    opciones = gb.build()
    # LOS DOS GRUPOS. `GridOptionsBuilder` no arma grupos de columnas, así
    # que se reacomodan las definiciones ya construidas: AG Grid Community
    # los soporta (`children`). Las ocultas quedan sueltas al final.
    defs = {c["field"]: c for c in opciones["columnDefs"]}
    xml = ("Ítem (XML)", "Cant. XML", "Und. XML", "P. unit. XML", "Importe XML")
    alm = ("Ítem (sistema)", "Und.", "Cant.", "P. unit.", "Importe", "Cómo")
    usadas = set(xml) | set(alm) | {"#", "→"}
    opciones["columnDefs"] = (
        [defs["#"],
         {"headerName": "COMPROBANTE SUNAT · lo que dice el XML",
          "headerClass": "conv-grupo", "children": [defs[c] for c in xml]},
         defs["→"],
         {"headerName": "ALMACÉN · cómo entra",
          "headerClass": "conv-grupo", "children": [defs[c] for c in alm]}]
        + [c for f, c in defs.items() if f not in usadas])
    # Key con el documento adentro: AG Grid retiene estado del lado del
    # cliente, y al cambiar de documento con menos líneas reventaba
    # (IndexError, regla #224). Con la key distinta arranca limpio.
    return AgGrid(
        tv, gridOptions=opciones,
        height=alturas.por_filas(len(tv), px_fila=_ALTO_FILA_CONVERSOR,
                                 extra=2 * _ALTO_CABECERA_CONVERSOR + 4,
                                 rol=alturas.APOYO),
        theme="material",
        custom_css={**_css_grid(12, marco=False),
                    ".conv-grupo": {"color": f"{ACENTO} !important",
                                    "font-size": "10px !important",
                                    "font-weight": "700 !important",
                                    "letter-spacing": ".05em"}},
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        update_on=["cellValueChanged"],
        data_return_mode=DataReturnMode.AS_INPUT,
        # `server_wins`: sin esto, después de la primera edición el
        # navegador descarta lo que manda el servidor (regla #227) y el
        # código, la unidad y el origen se quedan como estaban.
        server_sync_strategy="server_wins",
        key=f"sunat_conv_{doc_id}",
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
                   f"Se eligen arriba, en «Producto del Almacén».")
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

    UNA TABLA CON LOS DOS LADOS desde el 2026-10-21 (regla #684,
    `_grid_conversor`): cada línea del XML a la izquierda y cómo entra al
    Almacén a la derecha, en la misma fila, con los totales de cada lado
    debajo de su grupo. Del 2026-08-27 a ese día fueron dos tablas lado a
    lado que se alineaban sólo si compartían alto de fila, de cabecera y
    de tabla; en la ventana se leían como dos cuadrantes sueltos. (Y antes
    del 2026-08-27, una tabla de 8 columnas que se leía como planilla: la
    de ahora separa los lados con dos grupos de columnas y una flecha.)

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

    # Sin texto arriba de las dos tablas, en ningún caso (los dos quitados
    # a pedido, 2026-10-02): ni el cartel azul de «todavía no está cargado»
    # ni la línea de «Documento registrado: los ítems salen de cruzar…». De
    # dónde sale cada código lo dice su línea («Automático» / «Sugerido» /
    # «Corregido», en el tooltip y en ámbar lo que hay que revisar), y cada
    # renglón de aviso le costaba alto a una pantalla única.

    filas_sistema = []
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
        # EL IMPORTE DE LA LÍNEA ES EL INVARIANTE de la homologación: el
        # proveedor factura 1 caja de 12 y el almacén la ingresa como 12
        # unidades, así que cambian la cantidad y el precio unitario —
        # pero lo que se pagó por esa línea, y por lo tanto los impuestos
        # y el total del documento, no. Ver `_grid_conversor`.
        _imp = _num(xml_l.get("importe"))
        _cant_sis = cant_xml if cant_cor is None else cant_cor
        # UNA fila con los dos lados (regla #684): lo que dice el XML, con
        # sufijo, y cómo entra al Almacén con los nombres de siempre.
        filas_sistema.append({
            "_idx": i,
            "_cod_auto": cod_auto or "",
            "_cant_xml": cant_xml,
            "_cod_sis": cod_sis,
            "_origen": origen,
            "_cod_prov": str(xml_l.get("codigo") or ""),
            "#": i + 1,
            "Ítem (XML)": xml_l.get("descripcion", ""),
            "Cant. XML": cant_xml,
            "Und. XML": str(xml_l.get("unidad") or "").strip(),
            "P. unit. XML": _num(xml_l.get("precio_unitario")),
            "Importe XML": _imp,
            "→": "→",
            "Ítem (sistema)": nom_sis,
            "Und.": uni_sis,
            "Cant.": _cant_sis,
            "P. unit.": _precio_derivado(_imp, _cant_sis),
            "Importe": _imp,
            "Cómo": {"Sin coincidencia": "Sin producto"}.get(origen, origen),
        })

    tv = pd.DataFrame(filas_sistema)
    _doc_id = str(doc.get("documento") or "")
    totales_doc = sunat.totales_xml(xml_original) if xml_original else None

    # Arriba, el documento y cuánto falta: lo único que hay que hacer antes
    # de importar es que cada línea tenga su producto.
    _con = sum(1 for f in filas_sistema if str(f.get("_cod_sis") or "").strip())
    _faltan = len(filas_sistema) - _con
    _titulo_panel(
        "Comprobante SUNAT → Almacén",
        (f"{_con} de {len(filas_sistema)} líneas con producto"
         + (f" · falta elegir {_faltan}" if _faltan else " ✓")),
        derecha=_datos_documento_html(doc))

    # UNA tabla con los dos lados (regla #684): la fila del XML y cómo entra
    # al Almacén a la misma altura, por construcción.
    with st.container(key="sunat_ingreso_tabla"):
        resp = _grid_conversor(tv, _doc_id)

    # Los totales, cada uno bajo su lado: los del comprobante (del
    # registro) y los que se van a cargar (la suma de las líneas). Tienen
    # que dar lo mismo, y si no, el pie del Almacén lo dice.
    # columnas-internas: los dos pies, bajo los dos grupos de la tabla.
    c_izq, c_der = st.columns(2, gap="small")
    with c_izq:
        _pie_comprobante(doc, lineas_xml, totales_doc)
    with c_der:
        _pie_sistema(doc, filas_sistema, lineas_xml)

    st.caption("Clic en «Producto del Almacén» para elegirlo o cambiarlo — "
               "el buscador sugiere mientras escribís, contra el maestro "
               "completo. «Cant.» arranca con la del XML y también se edita; "
               "vaciar el producto vuelve la línea a lo automático.")

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


_ALTO_DETALLE_FICHA = 340
"""Techo, en píxeles, de lo que puede crecer una pestaña de la ficha
(el detalle de líneas y el XML): con él la modal entra en una pantalla de
laptop (1366×768) y lo que sobra scrollea adentro de esa tabla, no la
modal entera. Gemelo del `max-height` de la imagen del comprobante en
`estilos/_80_cards.py`."""


def _ficha_sunat(doc):
    """El comprobante tal como lo tiene SUNAT: la cabecera y las pestañas.

    Hasta el 2026-10-02 la ficha eran DOS tarjetas lado a lado —esta y la
    del sistema, con las mismas catorce filas y una columna Δ—, y se quitó
    la del sistema a pedido: «que solo aparezca la del comprobante SUNAT,
    que entre en una pantalla y sea más estilizada». Lo que el sistema
    tiene cargado lo siguen diciendo la columna «Está vs Sistema» de la
    tabla (con el monto del otro lado en la fila elegida) y el conversor.

      · **Datos** — los campos del SIRE (`_ficha_html`) y las descargas.
      · **Comprobante** — el PDF del proveedor, renderizado.
      · **Detalle (n)** — las líneas del XML, completas.
      · **XML** — el archivo crudo.

    Las tres últimas sólo existen si el original ya está sincronizado; si
    no, en su lugar va `_pedir_original` — y esa pestaña se llama
    «⚠ Original» en vez de «⬇ Original» cuando el último pedido falló,
    que es lo único del fracaso que se ve sin abrirla (regla #309).
    «Datos» está SIEMPRE: sale del registro del SIRE, que no depende de
    ningún sync.
    """
    st.markdown(_cabecera_ficha_html(doc), unsafe_allow_html=True)

    pdf_original, xml_original = sunat.originales(doc)
    lineas = sunat.lineas_xml(xml_original) if xml_original else []

    nombres = ["Datos"]
    if pdf_original:
        nombres.append("📄 Comprobante")
    if lineas:
        nombres.append(f"📋 Detalle ({len(lineas)})")
    if xml_original:
        nombres.append("🧾 XML")
    pendiente = not (pdf_original or xml_original) and _en_espera(doc)
    if pendiente:
        # EL PEDIDO EN CURSO VA ARRIBA DE LAS PESTAÑAS, no adentro de
        # «Original»: cada corrida completa devuelve la ficha a «Datos», y
        # ahí el aviso —y su vigilante— quedaban escondidos (medido el
        # 2026-10-19, regla #674).
        _pedir_original(doc)
        nombres.append("⏳ Original")
    elif not (pdf_original or xml_original):
        # La ETIQUETA cambia cuando el último pedido falló: con el rótulo
        # de siempre («⬇ Original», que invita a bajar algo) el usuario se
        # queda en «Datos» esperando un archivo que ya se sabe que no va a
        # llegar. Ver regla #309.
        nombres.append("⚠ Original" if sunat.fallo_solicitud(doc)
                       else "⬇ Original")

    for nombre, tab in zip(nombres, st.tabs(nombres)):
        with tab:
            if nombre == "Datos":
                _ficha_html(doc)
                _descargas_ficha(doc, pdf_original, xml_original)
            elif nombre.startswith("📄"):
                # EL PDF SE MUESTRA COMO IMAGEN, no embebido: Chrome no
                # renderiza un `data:application/pdf` dentro de un iframe
                # con `sandbox` y Streamlit monta todos sus iframes así.
                # La imagen la acota al alto de la pantalla
                # `.st-key-sunat_ficha_pdf` en `estilos/_80_cards.py`: a
                # todo el ancho, una hoja A4 medía ~1000px y la modal
                # scrolleaba para ver el total.
                with st.spinner("Preparando el comprobante…"):
                    paginas = sunat.paginas_pdf(pdf_original)
                if not paginas:
                    st.warning("No se pudo mostrar el PDF en pantalla. "
                               "Se puede descargar igual.")
                with st.container(key="sunat_ficha_pdf"):
                    for i, png in enumerate(paginas, 1):
                        st.image(png)
                        if len(paginas) > 1:
                            st.caption(f"Página {i} de {len(paginas)}")
            elif nombre.startswith("📋"):
                _tabla_detalle(lineas, doc)
            elif nombre.startswith("🧾"):
                st.code(xml_original.decode("utf-8", errors="replace"),
                        language="xml", height=_ALTO_DETALLE_FICHA)
            elif pendiente:
                st.caption("El pedido está en curso (arriba): esta ficha se "
                           "completa sola cuando llegue el original.")
            else:
                _pedir_original(doc)


def _rango_hace(f_ini, f_fin, anos):
    """`(ini, fin)` corridos `anos` años atrás (29-feb cae en el 28)."""
    return ((pd.Timestamp(f_ini) - pd.DateOffset(years=anos)).date(),
            (pd.Timestamp(f_fin) - pd.DateOffset(years=anos)).date())


def _rotulo_rango(ini, fin):
    ini, fin = pd.Timestamp(ini), pd.Timestamp(fin)
    a = f"{ini.day} {MESES_ABR_ES[ini.month - 1]}"
    if ini.year != fin.year:
        a += f" {ini.year}"
    return f"{a} – {fin.day} {MESES_ABR_ES[fin.month - 1]} {fin.year}"


def _cruces_previos(d, col_fecha, f_ini, f_fin, prov, tablas):
    """El cruce del MISMO rango corrido un año atrás, ya clasificado por
    tipo de compra, para «Cruce con SUNAT»: `[(año, rango, cruce, None) |
    (año, rango, None, motivo)]`. Un año y no dos: cada cruce de doce meses
    cuesta ~16 s en la laptop (medido el 2026-10-21) y la vista abre acá;
    sumar otro es agregarlo a la tupla del bucle.

    Mismo cálculo que la tabla —`comprobantes_rango` del registro y
    `_parquet_agrupado_por_documento` del parquet, cruzados— con el filtro
    de proveedor si está puesto. «Mes en SUNAT» NO se aplica: en un año
    cerrado todos los meses están presentados, y «Mes abierto» daría cero.

    Un período sin una de las dos fuentes no es «cero documentos»: antes
    del primer comprobante del registro todo lo del sistema saldría «Solo
    sistema», y antes del primero del parquet, todo lo de SUNAT «Solo
    SUNAT». Se dice el motivo en vez de dibujarlo. Cacheado en la sesión
    por rango, proveedor y versión de las reglas de tipo: cada año cuesta
    ~0,4 s. Regla #630 y #683.
    """
    lim = sunat.limites_registro()
    _min = None
    if d is not None and col_fecha in getattr(d, "columns", ()):
        _min = pd.to_datetime(d[col_fecha], errors="coerce").min()
    out = []
    for anios in (1,):
        ini, fin = _rango_hace(f_ini, f_fin, anios)
        etiqueta, rotulo = _rotulo_anio(ini, fin), _rotulo_rango(ini, fin)
        k = (f"sunat_prev_{ini}_{fin}_{prov or ''}_{tipo_compra.VERSION}_"
             f"{len(d) if d is not None else 0}")
        if k not in st.session_state:
            if lim and ini < lim[0]:
                res = (None, f"el registro de SUNAT empieza el {lim[0]:%d/%m/%Y}")
            elif _min is not None and pd.notna(_min) and ini < _min.date():
                res = (None, f"las compras del sistema empiezan el {_min:%d/%m/%Y}")
            else:
                try:
                    df, _ = sunat.comprobantes_rango(ini, fin)
                except Exception as e:  # SUNAT caído no tumba el período actual
                    df, res = None, (None, f"no se pudo leer el registro ({e})")
                if df is not None and df.empty:
                    res = (None, "SUNAT no tiene comprobantes en ese rango")
                elif df is not None:
                    cr = cruzar_con_parquet(df, _parquet_agrupado_por_documento(
                        d, col_fecha, ini, fin, notas=data.notas_credito_compras()))
                    cr = tipo_compra.clasificar(cr, df, tablas)
                    if prov:
                        cr = cr[_claves_proveedor_cruce(cr) == prov]
                    res = (cr, None)
            st.session_state[k] = res
        cr, motivo = st.session_state[k]
        out.append((etiqueta, rotulo, cr, motivo))
    return out




def _rotulo_anio(ini, fin):
    """El año de un período anterior, para su botón: «2025», o «2024-25» si
    el rango corrido cruza el año nuevo."""
    a, b = pd.Timestamp(ini).year, pd.Timestamp(fin).year
    return str(b) if a == b else f"{a}-{b % 100:02d}"


_K_FICHA_ABIERTA = "sunat_ficha_abierta"
_K_FICHA_PEDIDO = "sunat_ficha_pedido"
"""La ficha (la modal) se abre por PEDIDO, no por elegir la fila (2026-10-02):
`_K_FICHA_ABIERTA` es el `car` del documento cuya ficha está abierta (o
`None`), y `_K_FICHA_PEDIDO` el último sello `_ver` atendido — la selección
de la grilla persiste entre corridas y trae el mismo sello en cada una, así
que sin recordarlo la ficha se reabriría en cada clic de la página."""


def _id_ficha(doc):
    """Identidad del documento para la modal: `car`, que es la única clave
    sin colisiones (ver `_fila_de`)."""
    if doc is None:
        return ""
    return str(doc.get("car") or doc.get("documento") or "")


def _atender_pedido_de_ficha(fila, doc):
    """Si la fila elegida trae un sello `_ver` NUEVO —el clic en el ojo o
    el número del documento—, abre su ficha. Un sello ya atendido no."""
    try:
        sello = float(fila.get("_ver") or 0)
    except (TypeError, ValueError):
        sello = 0.0
    if sello and sello != st.session_state.get(_K_FICHA_PEDIDO):
        st.session_state[_K_FICHA_PEDIDO] = sello
        st.session_state[_K_FICHA_ABIERTA] = _id_ficha(doc) or None


_K_INGRESO_ABIERTO = "sunat_ingreso_abierto"
_K_INGRESO_PEDIDO = "sunat_ingreso_pedido"
"""Lo mismo que la ficha, para la ventana de «Ingresar al Almacén»
(regla #683): el documento cuya ventana está abierta y el último sello
`_ing` atendido."""


def _atender_pedido_de_ingreso(fila, doc):
    """Si la fila elegida trae un sello `_ing` NUEVO —el clic en
    «Ingresar»—, abre la ventana. Cierra la ficha: van de a una."""
    try:
        sello = float(fila.get("_ing") or 0)
    except (TypeError, ValueError):
        sello = 0.0
    if sello and sello != st.session_state.get(_K_INGRESO_PEDIDO):
        st.session_state[_K_INGRESO_PEDIDO] = sello
        st.session_state[_K_INGRESO_ABIERTO] = _id_ficha(doc) or None
        st.session_state[_K_FICHA_ABIERTA] = None


def _ingreso_abierto(doc):
    actual = _id_ficha(doc)
    return bool(actual) and st.session_state.get(_K_INGRESO_ABIERTO) == actual


def _cerrar_ingreso():
    st.session_state[_K_INGRESO_ABIERTO] = None


def _ingresar_modal(doc, d):
    """«Ingresar al Almacén» —el conversor que antes era el sexto modo de la
    tarjeta de abajo, «Conversor SUNAT-Sistema»— en una ventana GRANDE
    sobre la tabla (2026-10-21, a pedido, regla #683). Se renombró por lo
    que hace y no por cómo: meter al Almacén un comprobante que SUNAT tiene
    y el sistema no.

    Es una tarea sobre UN documento, con principio y fin, y por eso va en
    una ventana y no en una pantalla: al cerrarla se vuelve a la misma fila.
    `large` (1280px) porque son dos tablas de líneas lado a lado. Mismo
    trato que la ficha: `on_dismiss` para que la próxima corrida no la
    reabra, y `una_vez_por_corrida` (regla #456).
    """
    titulo = " · ".join(t for t in (
        "Ingresar al Almacén", str(doc.get("documento") or ""),
        _compras_truncar(str(doc.get("proveedor") or ""), 48)) if t)

    def _contenido():
        with st.container(key="sunat_ingreso"):
            _card_conversor_sistema(doc, d)

    una_vez_por_corrida(st.dialog(titulo, width="large",
                                  on_dismiss=_cerrar_ingreso)(_contenido))()


def _ficha_abierta(doc):
    """¿Está abierta la ficha (la modal) del documento elegido?"""
    actual = _id_ficha(doc)
    return bool(actual) and st.session_state.get(_K_FICHA_ABIERTA) == actual


def _cerrar_ficha():
    st.session_state[_K_FICHA_ABIERTA] = None


def _ficha_modal(doc):
    """La ficha del documento —el comprobante SUNAT— en una VENTANA MODAL
    (`st.dialog`): centrada, con la página oscurecida detrás y una ✕ que la
    cierra; también se cierra con Esc o con un clic afuera.

    Así se pidió el 2026-10-02, con la captura de otra webapp (el «Detalle
    de comprobante» de un facturador). La primera versión de ese mismo día
    era una capa pegada encima de la tarjeta de la tabla: se leía como si
    la tabla se hubiera ido, y medía lo que la tabla (333px), así que la
    ficha scrolleaba casi entera. Y ese mismo día, más tarde, perdió la
    tarjeta del sistema que llevaba al costado (ver `_ficha_sunat`): con
    una sola cosa adentro, la modal pasa de `large` a `medium` (750px), el
    ancho de un comprobante, y la modal misma es la superficie — sin una
    tarjeta con borde adentro, que se leía como una caja dentro de otra.

    CUALQUIER CIERRE pasa por `on_dismiss=_cerrar_ficha`: sin eso la
    siguiente corrida —un clic en el gráfico de abajo, por ejemplo— la
    volvería a abrir, porque la fila sigue elegida. Un `st.rerun()` desde
    adentro (el pedido del original) no la cierra: vuelve a llamarse.

    El título se arma por documento, así que el decorador se aplica acá y
    no en el `def`. Y `una_vez_por_corrida` porque una modal es un
    fragment, y ésta se llama adentro de otro (`app.py::_render_contenido`,
    regla #456).
    """
    titulo = " · ".join(t for t in (
        str(doc.get("documento") or "Comprobante"),
        _compras_truncar(str(doc.get("proveedor") or ""), 48)) if t)

    def _contenido():
        with st.container(key="sunat_ficha"):
            _ficha_sunat(doc)

    una_vez_por_corrida(st.dialog(titulo, width="medium",
                                  on_dismiss=_cerrar_ficha)(_contenido))()


_K_ESPERA_ORIGINAL = "sunat_espera_original"
"""`{clave_solicitud: time.time() de cuando se empezó a esperar}`: los
pedidos de original que la ficha está esperando en esta sesión. Una
entrada vencida (más vieja que `_ESPERA_TOPE_S`) se QUEDA, para que volver
a abrir la ficha no reinicie la espera sola: la reinicia el botón «Ver si
ya llegó» o un pedido nuevo. Regla #674."""

_ESPERA_CADA_S = 4
"""Cada cuánto mira la ficha si el original ya llegó: el mismo tic que
`app.py::_vigilar_refresco`."""

_ESPERA_TOPE_S = 150
"""Cuánto espera la ficha sola. El pedido suele atenderse en menos de un
minuto; más allá, lo probable es que la máquina local esté apagada o que
SUNAT no conteste, y un fragment que tictaquea sin fin vence la caché de
mensajes del navegador (regla #474)."""


def _inicio_espera(doc, reiniciar=False):
    """Desde cuándo se espera el original de `doc` (y lo anota si no)."""
    esperas = st.session_state.setdefault(_K_ESPERA_ORIGINAL, {})
    clave = sunat.clave_solicitud(doc)
    if reiniciar:
        esperas.pop(clave, None)
    return esperas.setdefault(clave, time.time())


def _en_espera(doc):
    """¿Hay un pedido de original de `doc` en curso? La señal en R2, o una
    espera de esta sesión todavía dentro del tope y sin marca de fallo: la
    máquina local borra la señal al tomar el pedido, antes de subir el
    archivo, y en ese hueco la ficha no puede volver a ofrecer «Traer»."""
    if sunat.solicitud_pendiente(doc):
        return True
    inicio = st.session_state.get(_K_ESPERA_ORIGINAL, {}).get(
        sunat.clave_solicitud(doc))
    return (inicio is not None and time.time() - inicio <= _ESPERA_TOPE_S
            and not sunat.fallo_solicitud(doc))


_K_XML_LLEGADOS = "sunat_xml_llegados"
"""Las keys de R2 de los XML que llegaron en ESTA sesión por un pedido de la
ficha. La tabla las suma a `sunat.claves_xml_en_r2()` para poner el ✓ sin
volver a listar R2 entero: ese listado tarda 21,8 s desde la laptop (5.138
XML, medido el 2026-10-19), y vaciarlo en cada llegada se pagaba en la
corrida que redibuja la ficha. Regla #674."""


def _marcar_llegado(doc, xml):
    if xml:
        st.session_state[_K_XML_LLEGADOS] = (
            st.session_state.get(_K_XML_LLEGADOS, frozenset())
            | {sunat.claves_original(doc)[1]})


def _terminar_espera(doc):
    st.session_state.get(_K_ESPERA_ORIGINAL, {}).pop(
        sunat.clave_solicitud(doc), None)


@una_vez_por_corrida
@st.fragment(run_every=_ESPERA_CADA_S)
def _esperar_original(doc):
    """El vigilante de un pedido de original, DENTRO de la ficha: cada
    `_ESPERA_CADA_S` segundos pregunta a R2 si llegó el PDF/XML, si el
    pedido falló o si se atendió sin archivo. Con cualquiera de las tres,
    una corrida completa redibuja la ficha —ya con «Comprobante», «Detalle»
    y «XML»— y el ✓ de la columna «XML» de la tabla (por
    `_K_XML_LLEGADOS`, sin volver a listar R2).

    Hasta el 2026-10-19 la ficha decía «Volvé a entrar al documento en un
    rato»: nada volvía a mirar R2 mientras el usuario no tocara algo, y
    había que cerrar la ficha y abrirla de nuevo. Regla #674.

    Existe SÓLO mientras hay un pedido pendiente y por `_ESPERA_TOPE_S`
    como mucho, igual que `app.py::_vigilar_refresco`: un `run_every` que
    tictaquea siempre le vence al navegador la caché de mensajes y se come
    clics (regla #474). Al vencer, una corrida completa lo desmonta y queda
    el botón «Ver si ya llegó». `una_vez_por_corrida` porque es un fragment
    adentro de otro (la modal, regla #456)."""
    clave = sunat.clave_solicitud(doc)
    inicio = st.session_state.get(_K_ESPERA_ORIGINAL, {}).get(clave)
    if inicio is None:
        return
    sunat.refrescar_original(doc)
    pdf, xml = sunat.originales(doc)
    # Que la señal del pedido desaparezca NO es el final: la máquina local
    # la borra al TOMAR el pedido, unos segundos antes de subir el archivo
    # (medido: 60 s después del pedido la señal ya no estaba y el XML llegó
    # a los ~115). Sólo terminan la espera el original o la marca de fallo.
    if pdf or xml or sunat.fallo_solicitud(doc):
        _terminar_espera(doc)
        _marcar_llegado(doc, xml)
        st.rerun(scope="app")
    if time.time() - inicio > _ESPERA_TOPE_S:
        st.rerun(scope="app")
    st.caption(f"Esperando el original… {int(time.time() - inicio)} s")


def _boton_ver_si_llego(doc):
    """El respaldo de la espera: mirar AHORA si llegó, sin cerrar la ficha.
    Una corrida completa y no sólo la de la modal, para que el ✓ de la
    tabla también se entere. Reinicia la espera: si el pedido sigue
    pendiente, la ficha vuelve a esperar sola."""
    if st.button("↻ Ver si ya llegó", use_container_width=True,
                 key="sunat_ver_si_llego",
                 help="Pregunta ahora si el PDF y el XML ya están "
                      "guardados. No hace falta cerrar la ficha."):
        sunat.refrescar_original(doc)
        _marcar_llegado(doc, sunat.originales(doc)[1])
        _inicio_espera(doc, reiniciar=True)
        st.rerun()


# ── El pedido en LOTE de los XML que faltan (regla #675) ────────────────────
_K_LOTE = "sunat_lote_xml"
"""El lote en curso: `{"pedidos": {clave_solicitud: {"xml", "doc"}},
"listos", "fallidos" (sets de claves), "inicio", "avance" (time.time() del
último cambio)}`. Sólo existe mientras el lote está en curso."""

_K_LOTE_RESUMEN = "sunat_lote_resumen"
"""Lo que dejó el último lote, para decirlo UNA vez arriba de la tabla."""

_LOTE_MAX = 25
"""Cuántos pide un clic como mucho, los más recientes primero. La máquina
local los atiende de a uno (~25-60 s cada uno, medido en la #674): 25 son
diez a veinte minutos, y una cola más larga que eso no se mira terminar."""

_LOTE_CADA_S = 10
"""Cada cuánto mira el vigilante del lote. Más lento que el de la ficha (4 s)
porque un documento tarda más que eso en llegar, y porque cada tic envejece
la caché de mensajes del navegador (#474; `maxCachedMessageAge` = 100)."""

_LOTE_SIN_AVANCE_S = 240
"""Sin un documento resuelto en este tiempo, el vigilante se retira: lo
probable es que la máquina local esté apagada. Los pedidos siguen en la cola
de R2 y se atienden cuando vuelva."""

_LOTE_TOPE_S = 15 * 60
"""Tope absoluto: 90 tics de `_LOTE_CADA_S`, por debajo del
`maxCachedMessageAge` = 100 de `.streamlit/config.toml` (#474)."""


def _candidatos_lote(df_cruce, vis):
    """`(pedibles, descartes)`: los documentos de la tabla (`df_cruce` ya
    filtrado) sin XML en R2 que tiene sentido pedir, del más reciente al más
    viejo, como dicts del SIRE; y `{motivo: cuántos}` de los que no.

    Sin una consulta a R2 por fila: dos LISTADOS (los XML, que ya usa la
    columna «XML», y `sunat.solicitudes_en_r2`) y el registro en memoria.
    Fuera quedan las entidades financieras (los bancos no publican sus
    originales), los emisores que el portal nunca sirvió —el mismo criterio
    que `sunat.emisor_sin_originales`, contado sobre el listado—, lo que ya
    está pedido y lo que ya falló (se reintenta desde su ficha)."""
    if (df_cruce is None or df_cruce.empty or vis is None or vis.empty
            or "car" not in df_cruce.columns or "car" not in vis.columns):
        return [], {}
    cars = set(df_cruce["car"].astype(str))
    docs = [r for r in vis.to_dict("records") if str(r.get("car") or "") in cars]
    xml_en_r2 = (sunat.claves_xml_en_r2()
                 | st.session_state.get(_K_XML_LLEGADOS, frozenset()))
    rucs_con_xml = {k.split("/")[1] for k in xml_en_r2 if k.count("/") >= 2}
    solicitudes = sunat.solicitudes_en_r2()
    reg = sunat._registro_de_parquet()
    por_ruc = ({} if reg is None or "ruc_proveedor" not in getattr(reg, "columns", ())
               else reg["ruc_proveedor"].astype(str).str.strip()
               .value_counts().to_dict())

    pedibles, descartes = [], {}

    def _fuera(motivo):
        descartes[motivo] = descartes.get(motivo, 0) + 1

    for r in docs:
        if sunat.claves_original(r)[1] in xml_en_r2:
            continue
        ruc = str(r.get("ruc_proveedor") or "").strip()
        cdp = str(r.get("tipo_cdp") or "").strip().zfill(2)
        if (cdp in tipo_compra.TIPOS_CDP_FINANCIEROS
                or tipo_compra.es_entidad_financiera(r.get("proveedor"))):
            _fuera("de bancos y financieras")
        elif (ruc not in rucs_con_xml
              and por_ruc.get(ruc, 0) >= sunat.MINIMO_INTENTOS_EMISOR):
            _fuera("de proveedores que SUNAT nunca entrega")
        elif sunat.clave_fallo(r) in solicitudes:
            _fuera("que ya fallaron (se reintentan desde su ficha)")
        elif sunat.clave_solicitud(r) in solicitudes:
            _fuera("ya pedidos")
        else:
            pedibles.append(r)
    pedibles.sort(key=lambda r: str(r.get("fecha_emision") or ""), reverse=True)
    return pedibles, descartes


_K_LOTE_ABIERTO = "sunat_lote_abierto"
"""¿Está abierta la confirmación del lote? La abre y la cierra el ícono."""


def _alternar_lote():
    st.session_state[_K_LOTE_ABIERTO] = not st.session_state.get(
        _K_LOTE_ABIERTO, False)


def _boton_lote_xml():
    """El ícono de la botonera, gemelo de ⟳ y ⬇. Abre (o cierra) la
    confirmación arriba de la tabla (`_panel_lote_xml`). NO es un
    `st.popover`: el suyo dibuja el ícono más una flecha, no entra en los
    31 px de la botonera y se montaba sobre el desplegable de estado
    (medido el 2026-10-19). Regla #675."""
    st.button("", icon=":material/cloud_download:", key="sunat_lote_btn",
              use_container_width=True, on_click=_alternar_lote,
              help="Traer de SUNAT los XML que faltan en la tabla")


def _panel_lote_xml(df_cruce, vis):
    """La confirmación del lote: cuántos XML de la tabla se pueden pedir
    —y cuántos no, y por qué— y el botón que los pide. Mira las filas que
    muestra la tabla: con el filtro de proveedor o de estado, pide sólo
    ésas. Regla #675."""
    pedibles, descartes = _candidatos_lote(df_cruce, vis)
    n = min(len(pedibles), _LOTE_MAX)
    if not pedibles:
        texto = ("Ningún documento de la tabla, tal como está filtrada, "
                 "tiene un XML que se pueda pedir.")
    else:
        texto = (f"<b>{len(pedibles)} documento(s) sin XML.</b> "
                 + (f"Se piden los {n} más recientes; " if len(pedibles) > n
                    else "")
                 + "la máquina local los trae de a uno, ~1 min cada uno.")
    ayuda = ("No se piden: " + " · ".join(
        f"{v} {k}" for k, v in descartes.items()) + "."
        if descartes else "")
    # UN renglón, no un recuadro: la tarjeta de la tabla tiene techo
    # (`--alto-util`) y un recuadro de 165 px le habría puesto barra por
    # dentro. Lo descartado va en el tooltip del texto.
    with st.container(horizontal=True, vertical_alignment="center",
                      gap="small", key="sunat_lote_panel"):
        st.markdown(
            f'<div style="font-size:12px;color:{GRIS_TEXTO};" '
            f'title="{html.escape(ayuda)}">{texto}'
            + (f' <span style="text-decoration:underline dotted;">'
               f'{sum(descartes.values())} no se piden</span>'
               if descartes else "") + '</div>', unsafe_allow_html=True)
        if pedibles and st.button(f"Pedir {n} XML", key="sunat_lote_pedir",
                                  type="primary"):
            st.session_state[_K_LOTE_ABIERTO] = False
            _pedir_lote(pedibles[:n])
        st.button("Cancelar", key="sunat_lote_cancelar",
                  on_click=_alternar_lote)


def _pedir_lote(docs):
    """Deja una señal por documento —`sunat.solicitar_original`, la misma
    de la ficha— y arranca el vigilante del lote."""
    pedidos = {}
    with st.spinner(f"Pidiendo {len(docs)} XML…"):
        for r in docs:
            if sunat.solicitar_original(r):
                pedidos[sunat.clave_solicitud(r)] = {
                    "xml": sunat.claves_original(r)[1],
                    "doc": str(r.get("documento") or "")}
    sunat.solicitudes_en_r2.clear()
    st.session_state.pop(_K_LOTE_RESUMEN, None)
    if pedidos:
        ahora = time.time()
        st.session_state[_K_LOTE] = {"pedidos": pedidos, "listos": set(),
                                     "fallidos": set(), "inicio": ahora,
                                     "avance": ahora}
    else:
        st.session_state[_K_LOTE_RESUMEN] = (
            "No se pudo dejar ningún pedido. ¿Están las credenciales de R2 "
            "configuradas?")
    st.rerun()


def _texto_lote(lote):
    n = len(lote["pedidos"])
    listos, fallidos = len(lote["listos"]), len(lote["fallidos"])
    partes = [f"{listos} de {n} listos"]
    if fallidos:
        partes.append(f"{fallidos} sin original en SUNAT")
    resto = n - listos - fallidos
    if resto:
        partes.append(f"{resto} en camino")
    return " · ".join(partes)


def _terminar_lote(motivo=""):
    lote = st.session_state.pop(_K_LOTE, None)
    if lote:
        st.session_state[_K_LOTE_RESUMEN] = (
            f"XML de SUNAT: {_texto_lote(lote)}." + (f" {motivo}" if motivo
                                                     else ""))
    st.rerun(scope="app")


@una_vez_por_corrida
@st.fragment(run_every=_LOTE_CADA_S)
def _vigilar_lote_xml():
    """El vigilante del lote: UNO para todos los pedidos, no uno por
    documento. Cada tic lista las señales una vez (`solicitudes_en_r2`) y
    pregunta por el XML SÓLO de los documentos que la máquina local ya tomó
    —su señal ya no está—: con la cola de 25, son uno o dos `head_object`
    por tic. Un documento termina con su XML (listo) o con su marca de fallo
    (sin original); que la señal desaparezca no es el final (#674).

    Existe sólo mientras hay un lote en curso (#474). Al terminar —todos
    resueltos, `_LOTE_SIN_AVANCE_S` sin avance o `_LOTE_TOPE_S`— una
    corrida completa pone los ✓ en la tabla (por `_K_XML_LLEGADOS`, sin
    volver a listar los XML de R2) y el resumen queda arriba de la tabla.
    `una_vez_por_corrida`: es un fragment adentro de otro (#456)."""
    lote = st.session_state.get(_K_LOTE)
    if not lote:
        return
    sunat.solicitudes_en_r2.clear()
    sunat._existe_original.clear()
    solicitudes = sunat.solicitudes_en_r2()
    ahora = time.time()
    antes = len(lote["listos"]) + len(lote["fallidos"])
    for clave, info in lote["pedidos"].items():
        if clave in lote["listos"] or clave in lote["fallidos"]:
            continue
        if clave.replace(".json", ".fallo.json") in solicitudes:
            lote["fallidos"].add(clave)
        elif clave not in solicitudes and sunat._existe_original(info["xml"]):
            lote["listos"].add(clave)
            st.session_state[_K_XML_LLEGADOS] = (
                st.session_state.get(_K_XML_LLEGADOS, frozenset())
                | {info["xml"]})
    resueltos = len(lote["listos"]) + len(lote["fallidos"])
    if resueltos != antes:
        lote["avance"] = ahora
    if resueltos >= len(lote["pedidos"]):
        _terminar_lote()
    if ahora - lote["avance"] > _LOTE_SIN_AVANCE_S:
        _terminar_lote(
            f"La máquina local no avanza hace {_LOTE_SIN_AVANCE_S // 60} "
            "minutos: puede estar apagada. Los que faltan siguen pedidos y "
            "se traen cuando vuelva.")
    if ahora - lote["inicio"] > _LOTE_TOPE_S:
        _terminar_lote("Los que faltan siguen pedidos y se traen solos.")
    st.markdown(
        f'<div style="font-size:12px;color:{GRIS_TEXTO};text-align:right;">'
        f'⏳ Trayendo XML de SUNAT: {_texto_lote(lote)}. Los ✓ de la tabla '
        'se ponen al terminar; la ficha de cada uno ya lo muestra.</div>',
        unsafe_allow_html=True)


def _avance_lote_xml(df_cruce, vis):
    """Arriba de la tabla: el vigilante mientras hay un lote; si no, la
    confirmación si está abierta, y lo que dejó el último lote (una vez)."""
    if st.session_state.get(_K_LOTE):
        _vigilar_lote_xml()
        return
    if st.session_state.get(_K_LOTE_ABIERTO):
        _panel_lote_xml(df_cruce, vis)
    resumen = st.session_state.pop(_K_LOTE_RESUMEN, None)
    if resumen:
        st.markdown(
            f'<div style="font-size:12px;color:{GRIS_TEXTO};text-align:right;">'
            f'✓ {html.escape(resumen)}</div>', unsafe_allow_html=True)


def _pedir_original(doc):
    """El flujo de "todavía no está sincronizado el original": avisar en
    qué estado está el pedido y, si no hay ninguno, ofrecer hacerlo.

    Se extrajo de `_mostrar_original` el 2026-08-28, cuando el original
    dejó de ser un panel propio y pasó a ser pestañas de la ficha: el
    pedido no es una pestaña —no hay nada que ver— sino lo que se muestra
    EN LUGAR de ellas.

    Con un pedido pendiente la ficha ESPERA sola (`_esperar_original`) y se
    completa cuando llega; pasado `_ESPERA_TOPE_S`, dice por qué puede
    estar tardando y ofrece «Ver si ya llegó». Regla #674.
    """
    if _en_espera(doc):
        # La corrida nocturna va de lo más nuevo hacia atrás y tarda
        # semanas en llegar a lo viejo (ver regla #142), así que acá se
        # ofrece pedirlo puntualmente. La webapp NO abre ningún navegador:
        # deja una señal en R2 y la CPU local hace el trabajo — mismo
        # mecanismo que el refresco de parquets (regla #144).
        if time.time() - _inicio_espera(doc) <= _ESPERA_TOPE_S:
            st.info("⏳ Pedido. La máquina local lo está trayendo de SUNAT "
                    "— suele tardar menos de un minuto. Esta ficha se "
                    "completa sola cuando llegue.", icon=None)
            _esperar_original(doc)
        else:
            st.warning(
                f"⏳ El pedido lleva más de {_ESPERA_TOPE_S // 60} minutos "
                "sin respuesta. Puede que la máquina local esté apagada o "
                "que SUNAT no esté contestando; el pedido sigue en la cola "
                "y se atiende cuando vuelva.", icon=None)
            # El botón, sólo cuando la ficha dejó de esperar sola: al lado
            # del contador era una segunda forma de hacer lo mismo.
            _boton_ver_si_llego(doc)
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
                f"pudieron bajar. Los datos de la pestaña «Datos» salen del "
                f"SIRE y no dependen de esto.", icon="ℹ️")
        etiqueta = "↻ Intentar igual"

    if st.button(etiqueta, use_container_width=True,
                 key="sunat_pedir_original",
                 help="Le pide a la máquina local que baje el PDF y el XML "
                      "que emitió el proveedor. Tarda menos de un minuto; "
                      "después queda guardado para siempre."):
        if sunat.solicitar_original(doc):
            _inicio_espera(doc, reiniciar=True)
            # Sólo la ficha (la modal es un fragment): una corrida completa
            # dejaba ~25 s la pantalla sin ficha mientras el drill se
            # recalculaba, y la tabla no tiene nada nuevo que mostrar.
            st.rerun(scope="fragment")
        else:
            st.error("No se pudo dejar el pedido. ¿Están las credenciales "
                     "de R2 configuradas?")
    if not fallo and not n_emisor:
        st.caption("Todavía no sincronizado. La pestaña «Datos» sale del "
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
    # Sin título propio desde el 2026-10-02: lo nombra el selector de la
    # tarjeta, que alterna el conversor con el gráfico (`_panel_abajo`).
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
                "desde la ficha del documento, pestaña «⬇ Original».")
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
    fecha vive DENTRO de esta tarjeta desde el 2026-08-21 —y desde el
    2026-09-06 `app.py` no lo dibuja arriba en NINGUNA vista de Compras,
    así que ésta es la única que lo tiene—, el mensaje pedía elegir una fecha en un
    control que él mismo acababa de borrar de la pantalla: sin salida,
    salvo cambiar de vista. Ver `arquitectura.md` regla #115.

    EL ESPEJO SE RESTAURA ACÁ, y no alcanzaba con el de `app.py`: la clave
    del rango es la KEY del `date_input` que dibuja esta tarjeta, así que al
    salir de la vista Streamlit se la lleva — y volver es un clic en el
    rail, que es un `@st.fragment` y NO re-ejecuta `app.py`. Sin esto la
    tarjeta reaparecía con «Elegí una fecha…» y el rango elegido perdido.
    Ver `arquitectura.md` regla #458.
    """
    return _dia_o_rango(
        restaurar_eco(clave_rango("Documentos SUNAT", usa_carga_rango=False)))


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


def _aviso_origen(origen):
    """El caso de ALERTA del sello de origen —«faltan los últimos días»,
    regla #197—: un total creíble al que le falta la cola. Se dice arriba
    del contenido, y sólo cuando pasa."""
    if origen == "parquet-sin-cola":
        st.markdown(
            f'<div style="font-size:12px;color:{ADVERTENCIA_TEXTO};'
            f'text-align:right;">⚠ Faltan los últimos días: el sync '
            f'todavía no los trajo y SUNAT no respondió la consulta '
            f'en vivo. Probá de nuevo con ⟳.</div>',
            unsafe_allow_html=True)


def _excel(slot, df_cruce, f_ini, f_fin):
    """Rellena el hueco del botón de Excel, reservado ARRIBA. Se exporta el
    CRUCE que se está mirando — sin `car`, que es una clave interna y en una
    planilla es ruido."""
    _sufijo = f"{pd.Timestamp(f_ini):%Y%m%d}_{pd.Timestamp(f_fin):%Y%m%d}"
    with slot:
        st.download_button(
            "⬇", data=_excel_bytes(df_cruce.drop(columns=["car"],
                                                 errors="ignore")),
            file_name=f"sunat_documentos_{_sufijo}.xlsx",
            mime=("application/vnd.openxmlformats-officedocument"
                  ".spreadsheetml.sheet"),
            key="sunat_dl_xlsx", use_container_width=True,
            help="Exportar a Excel los documentos del cruce que se ven",
        )


def _vista_resumen(vista, censo, d, col_fecha, f_ini, f_fin, prov, tablas):
    """«Cruce con SUNAT» o «Proveedores y fechas»: sus datos y su pieza
    (`_sunat_vistas.py`, regla #683). Al entrar a un resumen se suelta lo
    que la tabla traía de la llegada anterior: volver a «Documentos» por el
    rail muestra la tabla entera."""
    from graficos.compras import _sunat_vistas as sv
    st.session_state.pop(sv.K_LLEGADA, None)
    rango = _rotulo_rango(f_ini, f_fin)
    if vista == sv.VISTA_PROV:
        series = sv.series_proveedores(sunat._registro_de_parquet(), f_fin)
        sv.dibujar(sv.datos_proveedores(censo, series, f_fin), "sunat_pieza_prov")
        return
    # Lo que falta cargar de los últimos días sólo cuenta si el período
    # llega hasta ellos: en un rango cerrado hace meses no es demora.
    desde_rec = datetime.date.today() - datetime.timedelta(days=_DIAS_RECIENTES)
    rec_desde = (max(pd.Timestamp(f_ini).date(), desde_rec)
                 if pd.Timestamp(f_fin).date() >= desde_rec else None)
    n_rec, s_rec = _fidelidad_cruce(censo, rec_desde)["recientes"]
    with st.spinner("Cruzando el mismo período de años anteriores…"):
        previos = _cruces_previos(d, col_fecha, f_ini, f_fin, prov, tablas)
    sv.dibujar(sv.datos_cruce(censo, previos, rango,
                              {"doc": n_rec, "soles": round(s_rec, 2),
                               "dias": _DIAS_RECIENTES}),
               "sunat_pieza_cruce")


def _volver_de_llegada(desde):
    from graficos.compras import _sunat_vistas as sv
    lleg = st.session_state.pop(sv.K_LLEGADA, None) or {}
    if lleg.get("prov"):
        poner_proveedor(None)
    st.session_state[sv.K_VISTA] = desde


def _quitar_llegada():
    from graficos.compras import _sunat_vistas as sv
    lleg = st.session_state.pop(sv.K_LLEGADA, None) or {}
    if lleg.get("prov"):
        poner_proveedor(None)


def _aviso_llegada(lleg):
    """El renglón que dice de dónde se llegó y qué filtra, con la vuelta y
    «Quitar filtro» (regla #683)."""
    from graficos.compras import _sunat_vistas as sv
    desde = lleg.get("desde") or sv.VISTA_CRUCE
    texto = sv.texto_llegada(lleg)
    if lleg.get("prov"):
        texto = " · ".join(t for t in (texto, "el proveedor elegido") if t)
    with st.container(horizontal=True, vertical_alignment="center",
                      gap="small", key="sunat_llegada_fila"):
        st.button(f"← Volver a {desde}", key="sunat_llegada_volver",
                  type="tertiary", on_click=_volver_de_llegada, args=(desde,))
        st.markdown(f'<span class="sunat-llegada-txt">Llegaste desde '
                    f'<b>{html.escape(desde)}</b>: {html.escape(texto)}</span>',
                    unsafe_allow_html=True)
        st.button("Quitar filtro ✕", key="sunat_llegada_quitar",
                  type="tertiary", on_click=_quitar_llegada)


def renderizar_documentos_sunat(d, col_fecha, vista=None):
    """Punto de entrada del drill. Lo llama `graficos/sunat_reporte.py`.

    TRES VISTAS DESDE EL 2026-10-21 (regla #683), una por pantalla: «Cruce
    con SUNAT» (la que abre), «Proveedores y fechas» y «Documentos», la
    tabla. Las tres comparten la fila de filtros y el cálculo del cruce; las
    dos primeras dibujan su pieza (`_sunat_vistas.py`) en lugar de la
    tabla, y llevan a ella ya filtrada. La tarjeta de debajo de la tabla
    —que alternaba seis modos y quedaba a medio mostrar— se fue: sus
    resúmenes son esas dos vistas, y el conversor es la ventana «Ingresar
    al Almacén» (`_ingresar_modal`). Lo de abajo describe la vista
    «Documentos»; la numeración de las tarjetas es la de antes de ese día.

    DOS TARJETAS Y UNA MODAL, para que todo entre en una pantalla
    (2026-10-02, a pedido; antes eran cuatro tarjetas apiladas):

      1. **La tabla** a lo ancho — controles, KPIs del cruce y los
         comprobantes, ocho filas (`_FILAS_DOCS`). Una sola tabla desde
         que `_tabla` y `_tabla_cruce` se fundieron en `_tabla_documentos`.
      2. **La ficha del documento elegido**, en una ventana modal sobre la
         página: la tarjeta SUNAT y la del sistema, con una ✕ que la
         cierra (`_ficha_modal`). Se abre con el ojo / el número del
         documento; el resto de la fila sólo la elige.
      3. **Gráfico o conversor**, en UNA tarjeta debajo de la tabla, con
         un selector que alterna entre los tres modos del gráfico y el
         conversor SUNAT-Sistema (`_panel_abajo`). El conversor sigue
         teniendo trabajo sólo si el documento no está cargado en el
         sistema (`_necesita_conversor`); si lo está, lo dice.

    `d` y `col_fecha` (el parquet de Compras y su columna de fecha) ya no
    son opcionales: el cruce dejó de ser una vista elegible y se calcula
    SIEMPRE, porque su resultado es una columna de la tabla. Cuesta
    ~390 ms por rango en la máquina de desarrollo. OJO: sólo el registro
    está cacheado; el cruce y la tabla se rehacen en CADA corrida, también
    con cada clic en una fila. Por eso sus bucles recorren diccionarios y
    no `iterrows()`: con 3.500 documentos eran ~800 ms por clic y quedaron
    en ~250 (regla #589).

    LOS CUATRO FILTROS (fecha, «Mes en SUNAT», proveedor y «Está vs
    Sistema») SON DE LA TABLA: recortan también el Excel que se baja y los
    dos gráficos de rango del panel de abajo. Es a propósito — un KPI que
    cuenta 65 documentos sobre una tabla que muestra 3 es la app
    contradiciéndose sola.

    LA TIRA DE KPIs LA RECORTAN TRES DE LOS CUATRO. El de estado no, y es
    la única excepción: esa tira ES el censo de los estados, así que
    recortarla con él la dejaría repitiendo la elección y sin denominador.
    Lo que lo hace legible es que el grupo «docs» dice «14 de 244» mientras
    el filtro está puesto. Ver `_filtro_estado` y la regla #461.

    LOS CONTROLES VIVEN DENTRO DE LA TARJETA, no en una franja aparte
    arriba — mismo criterio que el selector "La semana empieza" del drill
    Semanal. No es gusto: esta app no tiene scroll de PÁGINA (el main lo
    recorta), así que cualquier bloque que viva AFUERA de las tarjetas
    empuja a todas hacia abajo sin que `--alto-util` se entere. Medido
    antes de corregirlo: con período/vista/KPIs en una franja externa, la
    tarjeta arrancaba en y=266 (contra ~165 de Proveedor) y su borde
    inferior quedaba en 990 con un viewport de 900.
    """
    from graficos.compras import _sunat_vistas as sv
    vista = vista or sv.VISTA_DOCS
    es_docs = vista == sv.VISTA_DOCS
    f_ini, f_fin = _rango_vigente()

    # Lo que `_cuerpo` deja para las tarjetas de abajo. Se inicializa acá
    # porque las salidas tempranas de `_cuerpo` (sin rango, SUNAT caído,
    # sin comprobantes) devuelven `None` sin tocarlo: la regla #115 —
    # dibujar las tarjetas SIEMPRE y decidir el contenido adentro.
    estado = {"doc": None, "vis": None, "cruce": None, "resumen": None}

    with st.container(border=True, key="sunat_card_izq"):
        # UN SOLO RENGLÓN CON LOS CUATRO FILTROS, a pedido (2026-09-18:
        # «que los filtros figuren en la misma fila que el filtro de fecha
        # de la tarjeta»). Hasta hoy la fecha iba arriba y los otros tres
        # debajo, dentro de una columna de 622px.
        #
        # PARA QUE CUPIERAN, LA TIRA DE KPIs BAJÓ AL SEGUNDO RENGLÓN (y el
        # 2026-10-02 se fue de la tarjeta, ver más abajo). Medido en el navegador
        # (viewport 1358, tarjeta de 1227 = 1191 de contenido):
        #
        #   · lo que pide cada control en su PEOR caso — el pill 210 (se
        #     planta en ese ancho, no lo da el `width: 100%`: 16 del ícono
        #     + 151 de «17 sep 2025 – 16 sep 2026» + 16 del chevron),
        #     «Mes en SUNAT» 133 («Mes presentado» + 32 de cromo), el de
        #     proveedor 195 (su piso, ver `_opciones_proveedor`), el de
        #     estado 191 («Todos los estados (4,646)» + cromo) y los dos
        #     iconos 138. Son 867 de los 1.127 útiles, así que sobran 260
        #     que se van casi todos al de proveedor, que es el único cuyo
        #     contenido es un nombre largo.
        #   · la tira, en cambio, GANA bajando: a lo ancho de la tarjeta su
        #     grupo más largo (los cuatro estados con sus montos, 654px de
        #     texto) entra en UN renglón y mide 20px, contra los 64 que
        #     medía envuelto en tres dentro de una columna de 365. O sea que
        #     la cabecera no crece por tener dos renglones: 26 + 20 contra
        #     los 64 que imponía la tira.
        #
        # Y la tira queda justo encima de la tabla, que es una mejora de
        # paso y no un accidente: cada grupo resume una COLUMNA (regla
        # #460), así que se lee mejor apoyada sobre ellas que en la esquina.
        #
        # columnas-internas: la cabecera de la tarjeta — los cuatro filtros
        # y la botonera. No es una fila de un drill, así que no va con
        # `COLUMNAS_DRILL`.
        c_fecha, c_mes, c_prov, c_est, c_act = st.columns(
            [1.5, 1.0, 2.1, 1.35, 0.95])
        with c_fecha:
            # La fecha, DENTRO de la tarjeta: acá no es contexto global,
            # es EL filtro de la tabla — el rango que se le consulta al
            # SIRE. Hasta el 2026-10-11 era el pill viejo de la franja
            # (`franja_fecha.render()`: atajos cortos + un `date_input`), el
            # único que quedaba en la app; se reportó como «no es similar al
            # de otros reportes». Ahora es el panel de las demás tarjetas
            # (`selector_fecha_tarjeta`, regla #616) SIN `categoria`: escribe
            # la clave canónica del reporte, que es la que lee
            # `_rango_vigente`. Al no ser ya la key de un widget, Streamlit
            # no la borra al salir del reporte; el espejo de
            # `restaurar_eco` queda como red. Regla #633.
            #
            # El selector «Ver» que había acá bajó al panel del gráfico
            # (`_panel_grafico`), que es lo único que controlaba.
            selector_fecha_tarjeta("sunat_f", "sunat_fecha_flag")
        with c_mes:
            mes_sunat = st.selectbox(
                "Mes en SUNAT", list(_MES_SUNAT), key="sunat_mes_sunat",
                label_visibility="collapsed",
                help="El estado del PERÍODO tributario en SUNAT, no del "
                     "documento. «Mes abierto» = SUNAT ya ve la compra "
                     "pero el registro de ese mes todavía no se "
                     "presentó: es crédito fiscal sin tomar. Si está "
                     "cargado o no en tu sistema lo dice «Está vs "
                     "Sistema».",
            )
        with c_prov:
            # Mismo truco que el botón de Excel de al lado: el hueco se
            # reserva acá y lo rellena `_cuerpo`, que es quien tiene la
            # lista de proveedores. Ver `_filtro_proveedor`.
            _slot_prov = st.empty()
        with c_est:
            # Y el de estado igual, por el mismo motivo: sus etiquetas
            # llevan el conteo de cada estado, y eso sale del cruce, que
            # se calcula abajo. Ver `_filtro_estado`.
            _slot_est = st.empty()
        with c_act:
            # columnas-internas: 3 iconos de accion
            _c_ref, _c_lote, _c_xls = st.columns(3)
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
                sunat.claves_xml_en_r2.clear()
                st.rerun()
        with _c_lote:
            # Como el Excel: el hueco se reserva acá y lo rellena `_cuerpo`,
            # que es quien sabe qué filas muestra la tabla. Regla #675.
            _slot_lote = st.empty()
        with _c_xls:
            # El botón de exportar vive ARRIBA (a pedido) pero los datos
            # que exporta se calculan MÁS ABAJO. `st.empty()` reserva el
            # sitio ahora y se rellena cuando el df existe: es la única
            # forma de tener un control arriba que dependa de algo de
            # abajo sin partir el flujo en dos reruns.
            _slot_excel = st.empty()

        # (Acá iba un SEGUNDO RENGLÓN con la tira de KPIs del cruce —docs,
        # proveedores, montos y los cuatro estados, que se encendían con el
        # cursor sobre su columna—. Se fue el 2026-10-02, a pedido, para que
        # la tabla suba: sus conteos son ahora el modo «Resumen del cruce»
        # de la tarjeta de abajo, con la comparación contra años
        # anteriores. Regla #586.)

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

            g_pq = _parquet_agrupado_por_documento(
                d, col_fecha, f_ini, f_fin, notas=data.notas_credito_compras())
            df_cruce = cruzar_con_parquet(vis, g_pq)
            # «Tipo»: qué se compró (Mercadería, Otros bienes, Servicios,
            # Financiero). Se agrega ANTES de los filtros para que viaje
            # también al Excel. El SIRE no lo dice: sale del Almacén y de
            # dos señales del registro, en el orden de `tipo_compra.py`.
            # Regla #640.
            _tablas = _tablas_tipo(
                (data.sello_datos(definicion_compra.ARCHIVO),
                 data.sello_datos("inventariovalorizado.parquet")),
                tipo_compra.VERSION, d)
            df_cruce = tipo_compra.clasificar(df_cruce, vis, _tablas)

            # EL FILTRO DE PROVEEDOR VA ACÁ, sobre el cruce ya armado, y no
            # sobre `vis` antes de cruzar. Recortar el lado SUNAT primero
            # dejaría pasar enteras las filas «Solo sistema» —que salen del
            # parquet, no del SIRE— y la tabla mostraría el proveedor
            # elegido MÁS los documentos huérfanos de todos los demás.
            _claves = _claves_proveedor_cruce(df_cruce)
            _prov = _filtro_proveedor(_slot_prov, df_cruce, _claves)
            if _prov:
                df_cruce = df_cruce[_claves == _prov]
                # `vis` también, que es lo que resumen los dos gráficos de
                # rango del panel de abajo: dejarlo entero pondría un
                # gráfico del período completo al lado de una tabla de un
                # solo proveedor, y la pantalla se contradiría sola.
                vis = vis[_claves_proveedor_sire(vis) == _prov]

            # EL FILTRO DE ESTADO VA ÚLTIMO, y el orden importa: sus
            # etiquetas llevan el conteo de cada estado, así que tienen que
            # contarse sobre el cruce ya recortado por período y proveedor
            # — un «Diferencia (14)» del rango entero al lado de una tabla
            # de un solo proveedor sería un número que no se puede
            # verificar en pantalla.
            #
            # `df_cruce` se guarda ANTES de aplicarlo: es lo que resume el
            # «Resumen del cruce» de la tarjeta de abajo, que es el censo
            # del que este filtro elige (ver `_filtro_estado`).
            _cruce_censo = df_cruce
            if not es_docs:
                # Las vistas de resumen: su pieza en lugar de la tabla, sobre
                # el censo (el filtro de estado elige DENTRO del censo, así
                # que no se dibuja; su espejo lo conserva). Regla #683.
                estado["resumen"] = {"censo": _cruce_censo}
                _publicar_conteos(_cruce_censo)
                _aviso_origen(_origen)
                _vista_resumen(vista, _cruce_censo, d, col_fecha, f_ini, f_fin,
                               _prov, _tablas)
                _excel(_slot_excel, _cruce_censo, f_ini, f_fin)
                return None
            _est = _filtro_estado(_slot_est, df_cruce)
            if _est:
                df_cruce = df_cruce[df_cruce["estado"] == _est]
                # `vis` se recorta por los `car` que sobreviven, no por el
                # estado: `vis` es el lado SIRE y no tiene esa columna. Con
                # «Solo sistema» queda vacío a propósito — son justo los
                # comprobantes que SUNAT no tiene, y los gráficos de abajo
                # lo dicen con su cartel de "sin datos" en vez de mentir.
                #
                # El guard de columna no es paranoia: `_tabla_documentos`
                # lleva el mismo (`if "car" in df_sire.columns`) porque
                # `cruzar_con_parquet` es pública y los tests la llaman con
                # df armados a mano. Sin él, un df sin `car` cambia un
                # gráfico incompleto por un KeyError que se lleva la vista.
                if "car" in vis.columns and "car" in df_cruce.columns:
                    vis = vis[vis["car"].astype(str).isin(
                        set(df_cruce["car"].astype(str)))]
            # Lo que pidió el resumen del que se llegó (tipo, estados, días),
            # con su aviso y la vuelta. El proveedor ya vino en su filtro.
            _lleg = st.session_state.get(sv.K_LLEGADA)
            if _lleg:
                _aviso_llegada(_lleg)
                df_cruce = sv.aplicar_llegada(df_cruce, _lleg)
                if "car" in vis.columns and "car" in df_cruce.columns:
                    vis = vis[vis["car"].astype(str).isin(
                        set(df_cruce["car"].astype(str)))]
            estado["vis"], estado["cruce"] = vis, df_cruce
            estado["resumen"] = {
                "censo": _cruce_censo, "origen": _origen,
                "f_ini": f_ini, "f_fin": f_fin, "prov": _prov,
                "col_fecha": col_fecha, "mes_filtrado": _sit is not None,
            }
            _publicar_conteos(_cruce_censo)

            _aviso_origen(_origen)
            # El pedido en lote de los XML que faltan (regla #675): su
            # avance arriba de la tabla mientras dura, y el botón en la
            # botonera, sobre las filas que la tabla muestra.
            with _slot_lote.container(key="sunat_lote"):
                _boton_lote_xml()
            _avance_lote_xml(df_cruce, vis)
            doc = _tabla_documentos(df_cruce, vis)

            _excel(_slot_excel, df_cruce, f_ini, f_fin)
            return doc

        estado["doc"] = _cuerpo()

        doc = estado["doc"]
        fila_cruce = _fila_cruce_de(estado["cruce"], doc)

    # LA FICHA DEL DOCUMENTO, EN UNA VENTANA MODAL (2026-10-02, a pedido:
    # «que las dos tarjetas aparezcan sobre la tabla, con una X para
    # cerrar»). Hasta ese día eran una fila propia DEBAJO de la tabla, y con
    # el gráfico y el conversor la vista eran cuatro pantallas. La tabla se
    # sigue DIBUJANDO detrás: un widget que deja de renderizarse pierde su
    # estado, y sin la selección no habría documento — ni para la ficha ni
    # para el gráfico y el conversor de abajo. Regla #586.
    if _ficha_abierta(doc):
        _ficha_modal(doc)
    # «Ingresar al Almacén», la ventana que reemplazó a la tarjeta de debajo
    # de la tabla (regla #683). Sólo para lo que falta cargar: el botón de
    # la fila no aparece en otro estado, y una selección vieja no la abre.
    elif (_ingreso_abierto(doc) and fila_cruce is not None
          and str(fila_cruce.get("estado") or "") == "Solo SUNAT"):
        _ingresar_modal(doc, d)
