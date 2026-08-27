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
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode, JsCode

import sunat
from estado_rango import clave_rango
import franja_fecha
from tema import (
    ACENTO, ACENTO_TEXTO, ADVERTENCIA_TEXTO, ERROR, GRIS_BORDE, GRIS_TEXTO,
    LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from graficos.base import _compras_layout, _compras_truncar
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
    columnas = ["documento", "ruc_pq", "proveedor_pq", "base_pq", "total_pq",
                "fecha_pq", "num_doc_pq"]
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
    g = (dd.groupby(["documento", "ruc_pq", "NOMBRE_PROVEEDOR"], as_index=False)
           .agg(base_pq=(col_base, agg_base),
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
    """
    cols_pq = ["documento", "ruc_pq", "proveedor_pq", "base_pq", "total_pq",
               "fecha_pq"]
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
            estado = ("Coincide"
                      if abs(dif_base) <= _TOLERANCIA_CENTAVOS
                      and abs(dif_total) <= _TOLERANCIA_CENTAVOS
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
            "total_sunat": total_sunat, "total_sistema": total_sist,
            "dif_total": dif_total, "estado": estado,
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
            "total_sunat": None, "total_sistema": float(cand["total_pq"]),
            "dif_total": None, "estado": "Solo sistema",
        })

    out = pd.DataFrame(filas)
    if out.empty:
        return out
    for _c in ("fecha_emision", "fecha_sunat", "fecha_sistema"):
        out[_c] = pd.to_datetime(out[_c], errors="coerce")
    return out.sort_values("fecha_emision").reset_index(drop=True)


def _kpis_cruce(df):
    """Resumen de UNA línea del cruce: cuántos documentos coinciden,
    difieren, o faltan de un lado u otro. Mismo criterio compacto que
    `_kpis` — ver su docstring sobre por qué no son `st.metric`.
    """
    if df is None or df.empty:
        st.markdown('<div style="height:38px;"></div>', unsafe_allow_html=True)
        return
    conteos = df["estado"].value_counts()

    def dato(valor, etiqueta, color=None):
        c = color or TEXTO_PRINCIPAL
        return (f'<span style="white-space:nowrap;">'
                f'<b style="color:{c};font-weight:600;">{valor}</b>'
                f'<span style="color:{GRIS_TEXTO};"> {etiqueta}</span></span>')

    partes = [dato(f'{int(conteos.get("Coincide", 0)):,}', "coinciden")]

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

    st.markdown(
        '<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;'
        'justify-content:flex-end;font-size:12.5px;height:38px;">'
        + f'<span style="color:{GRIS_BORDE};">·</span>'.join(partes)
        + '</div>',
        unsafe_allow_html=True,
    )


def _tabla_cruce(df_cruce, df_sire):
    """AgGrid de la comparación SIRE vs sistema. Devuelve la fila COMPLETA
    del SIRE (de `df_sire`, no de `df_cruce`) que corresponde a la
    seleccionada — `df_cruce` solo trae las columnas de la comparación
    (fecha/documento/montos/estado), y el panel derecho necesita el
    registro entero (tipo, CAR, moneda) para armar la ficha.

    Un "Solo sistema" seleccionado devuelve `None` a propósito: no hay
    documento del SIRE que le corresponda — no es una carencia del panel,
    es que ese comprobante no tiene contraparte ahí.

    Sin `fit_columns_on_grid_load`: son 13 columnas y 4 de plata — forzar
    el ancho del contenedor las dejaría ilegibles. Scrollea horizontal,
    mismo criterio que la tabla pivote de Proveedor.
    """
    def _f(s):
        """dd/mm/yyyy, y "" cuando no hay fecha — un NaT crudo en la grilla
        sale como "NaT" y el usuario lo lee como un dato."""
        return pd.to_datetime(s, errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

    tv = pd.DataFrame({
        # Las dos fechas, para poder compararlas (a pedido 2026-08-21). El
        # `fecha_emision` de antes mostraba la del SIRE en las filas
        # emparejadas y la del parquet en las "Solo sistema" — o sea una
        # sola columna que cambiaba de fuente segun la fila, imposible de
        # comparar contra nada.
        "Fecha SUNAT": _f(df_cruce["fecha_sunat"]),
        "Fecha sistema": _f(df_cruce["fecha_sistema"]),
        # Las dos formas del MISMO numero, a pedido 2026-08-24. Un
        # "Documento sistema" con la llave normalizada (`FA28-2305799`)
        # SERIA una copia byte a byte de la columna de al lado -- por eso
        # esta columna muestra el numero CRUDO del ERP
        # (`F0FA28002305799`, con su prefijo de tipo y sus ceros), que es
        # lo que hay que tipear para ir a buscar el documento al sistema y
        # NO se ve en ningun otro lado de la app.
        "Documento SUNAT": df_cruce["documento"],
        "Documento sistema": df_cruce.get(
            "documento_sistema", pd.Series("", index=df_cruce.index)).fillna(""),
        "RUC SUNAT": df_cruce["ruc_proveedor"].fillna(""),
        "RUC sistema": df_cruce["ruc_sistema"].fillna(""),
        # "Proveedor SUNAT" se habia retirado (con los dos RUC al lado, el
        # nombre del SIRE parecia la tercera forma de decir lo mismo) y
        # volvio a pedido 2026-08-24: el RUC es un numero que nadie
        # reconoce de memoria, y ver los dos NOMBRES al lado es lo que
        # caza un proveedor cargado con otra razon social.
        "Proveedor SUNAT": df_cruce["proveedor"].fillna(""),
        "Proveedor sistema": df_cruce["proveedor_sistema"].fillna(""),
        "Base SUNAT": pd.to_numeric(df_cruce["base_sunat"], errors="coerce"),
        "Base sistema": pd.to_numeric(df_cruce["base_sistema"], errors="coerce"),
        "Total SUNAT": pd.to_numeric(df_cruce["total_sunat"], errors="coerce"),
        "Total sistema": pd.to_numeric(df_cruce["total_sistema"], errors="coerce"),
        "Estado": df_cruce["estado"],
    })

    _fmt_soles = JsCode(
        "function(p){ if(p.value==null||isNaN(p.value)) return '—'; "
        "return 'S/ ' + Number(p.value).toLocaleString('es-PE',"
        "{minimumFractionDigits:2, maximumFractionDigits:2}); }")

    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=True, filter=False,
                                editable=False, suppressMovable=True)
    # `minWidth` = `width` en cada columna, y no es redundante: es lo que
    # hace SEGURO al `sizeColumnsToFit()` de `onGridSizeChanged` (más abajo).
    # `sizeColumnsToFit` respeta los mínimos — si no entran, deja cada
    # columna en su mínimo y scrollea, en vez de aplastarlas. Así el mismo
    # handler sirve para los dos estados: angosto (columnas en su mínimo,
    # scroll horizontal, que es el comportamiento de siempre) y en pantalla
    # completa (se reparten el ancho de sobra). Sin los mínimos, el fit
    # rompería justo lo que el docstring de arriba pide evitar.
    # Misma convencion de color que los montos: ambar = revisar. Se pinta
    # la fecha del SISTEMA porque es la corregible — la del SIRE es la que
    # SUNAT ya tiene registrada. Solo marca cuando HAY las dos y difieren:
    # un "Solo SUNAT" no tiene fecha de sistema y no es una discrepancia de
    # fecha, es una ausencia, y eso ya lo dice la columna Estado.
    _style_fecha = JsCode(
        "function(p){ var o=p.data['Fecha SUNAT']; "
        "if(p.value && o && p.value !== o) "
        "return {'color':'%s','fontWeight':'600'}; "
        "return {'color':'%s'}; }" % (ADVERTENCIA_TEXTO, GRIS_TEXTO))
    gb.configure_column("Fecha SUNAT", width=105, minWidth=105, pinned="left")
    gb.configure_column("Fecha sistema", width=110, minWidth=110,
                        pinned="left", cellStyle=_style_fecha)
    gb.configure_column("Documento SUNAT", width=115, minWidth=115,
                        pinned="left")
    # Sin pinear: cuatro columnas fijas a la izquierda se comen 450px y en
    # una laptop no queda ancho para los montos, que son el punto de la
    # vista. Igual queda pegada a "Documento SUNAT" -- AG Grid dibuja las
    # no pineadas justo despues de las pineadas, en orden.
    gb.configure_column("Documento sistema", width=140, minWidth=140,
                        cellStyle={"color": GRIS_TEXTO})
    gb.configure_column("RUC SUNAT", width=105, minWidth=105)
    gb.configure_column("RUC sistema", width=105, minWidth=105)
    gb.configure_column("Proveedor SUNAT", minWidth=180)
    gb.configure_column("Proveedor sistema", minWidth=180)
    for col in ("Base SUNAT", "Base sistema", "Total SUNAT", "Total sistema"):
        gb.configure_column(col, type=["numericColumn"], width=115,
                            minWidth=115, valueFormatter=_fmt_soles)
    # Igual convención que "Pendiente" en _tabla: ámbar = revisar, rojo =
    # más urgente todavía (plata cargada sin comprobante electrónico que
    # la respalde). "Coincide" no se destaca — lo normal no compite por
    # atención.
    gb.configure_column(
        "Estado", width=118, minWidth=118, pinned="right",
        cellStyle=JsCode(
            "function(p){ var m={'Diferencia':'%s','Solo SUNAT':'%s',"
            "'Solo sistema':'%s'}; var c=m[p.value]; "
            "return c ? {'color':c,'fontWeight':'600'} : {'color':'%s'}; }"
            % (ADVERTENCIA_TEXTO, ADVERTENCIA_TEXTO, ERROR, GRIS_TEXTO)))
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    # Re-reparte las columnas cada vez que el grid cambia de TAMANIO. Con la
    # tabla ya apilada a todo el ancho, los dos casos que quedan son plegar
    # el rail de vistas y redimensionar la ventana: sin esto las columnas se
    # quedan con el ancho que midieron al montar y sobra hueco a la derecha.
    # `fit_columns_on_grid_load` solo actua una vez, al cargar.
    # Es seguro aunque el ancho sea chico porque cada columna declara
    # `minWidth` (ver arriba): `sizeColumnsToFit` los respeta y scrollea en
    # vez de aplastar. Es la receta de la documentacion de AG Grid, y no
    # entra en bucle: el evento no se re-dispara por el propio ajuste.
    gb.configure_grid_options(
        rowHeight=30, headerHeight=32,
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
    )

    resp = AgGrid(
        tv, gridOptions=gb.build(),
        height=alturas.por_filas(len(tv), px_fila=30, rol=alturas.APOYO),
        theme="material", custom_css=dict(_css_grid(13)),
        allow_unsafe_jscode=True, fit_columns_on_grid_load=False,
        key="sunat_cruce_grid",
    )
    sel = resp.selected_rows
    if sel is None or (hasattr(sel, "empty") and sel.empty) or len(sel) == 0:
        return None
    fila = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
    if fila["Estado"] == "Solo sistema":
        return None
    # Mismo criterio que `_tabla`: por RUC + documento, nunca por documento
    # solo — 1.422 comprobantes comparten serie-número con otro proveedor.
    # Ver `_fila_de`.
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


def _kpis(df, origen=None):
    """Tira compacta de totales del rango, para la fila de controles.

    NO son `st.metric`: cuatro métricas nativas ocupan 91px de alto y en
    la columna de ~430px que le toca acá (al lado de período/vista/⟳)
    truncaban los importes con "…" (medido: "S/ 60,79…"). Un total
    truncado es peor que no mostrarlo. Con una sola línea de texto, además,
    entra en la misma fila que los controles y no le suma alto a la
    tarjeta — ver el docstring de `renderizar_documentos_sunat` sobre por
    qué eso importa acá más que en otras vistas.
    """
    total = float(pd.to_numeric(df.get("total"), errors="coerce").sum())
    igv = float(pd.to_numeric(df.get("igv"), errors="coerce").sum())
    provs = df["ruc_proveedor"].nunique() if "ruc_proveedor" in df else 0

    def dato(valor, etiqueta):
        return (f'<span style="white-space:nowrap;">'
                f'<b style="color:{TEXTO_PRINCIPAL};font-weight:600;">{valor}</b>'
                f'<span style="color:{GRIS_TEXTO};"> {etiqueta}</span></span>')

    partes = [
        dato(f"{len(df):,}", "docs"),
        dato(f"S/ {total:,.2f}", "total"),
        dato(f"S/ {igv:,.2f}", "IGV"),
        dato(f"{provs:,}", "proveedores"),
    ]
    # Los pendientes solo se nombran si los hay: un "0 pendientes" fijo
    # gasta ancho en la fila de controles y no dice nada. Van en ámbar
    # porque son plata — crédito fiscal que todavía no se tomó.
    n_pend = int((df.get("situacion") == "Pendiente").sum()) if "situacion" in df else 0
    if n_pend:
        mto_pend = float(pd.to_numeric(
            df.loc[df["situacion"] == "Pendiente", "total"], errors="coerce").sum())
        partes.append(
            f'<span style="white-space:nowrap;color:{ADVERTENCIA_TEXTO};" '
            f'title="Comprobantes que SUNAT ve pero que aún no están '
            f'anotados en un registro presentado">'
            f'<b style="font-weight:600;">{n_pend:,}</b> pendientes '
            f'(S/ {mto_pend:,.2f})</span>')

    if origen:
        partes.append(_sello_origen(origen))

    st.markdown(
        '<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;'
        'justify-content:flex-end;font-size:12.5px;height:38px;">'
        + f'<span style="color:{GRIS_BORDE};">·</span>'.join(partes)
        + '</div>',
        unsafe_allow_html=True,
    )


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
    fig.update_layout(title="Comprobantes por fecha de emisión")
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


def _tabla(df):
    """AgGrid de una fila por documento. Devuelve la fila clickeada o None.

    Selección sin checkbox (`use_checkbox=False`): un clic en cualquier
    parte de la fila abre el documento en el panel derecho. Mismo criterio
    que el ranking de Volatilidad — ver su docstring.
    """
    tv = pd.DataFrame({
        "Fecha": pd.to_datetime(df["fecha_emision"], errors="coerce")
                   .dt.strftime("%d/%m/%Y"),
        "Tipo": df.get("tipo_nombre", ""),
        "Documento": df.get("documento", ""),
        "Proveedor": df.get("proveedor", ""),
        "RUC": df.get("ruc_proveedor", ""),
        "Total": pd.to_numeric(df.get("total"), errors="coerce"),
        "Situación": df.get("situacion", ""),
        # Oculta, sólo para identificar la fila clickeada. Ver `_car_de`.
        "_car": df.get("car", ""),
    })

    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=True, filter=False,
                                editable=False, suppressMovable=True)
    gb.configure_column("_car", hide=True)
    gb.configure_column("Fecha", width=95)
    gb.configure_column("Tipo", width=110)
    gb.configure_column("Documento", width=125)
    # `flex=1` en la única columna de largo variable: absorbe todo el ancho
    # que sobra después de las de tamaño fijo, en vez de dejar un hueco
    # muerto a la derecha de "Situación".
    gb.configure_column("Proveedor", minWidth=190, flex=1,
                        tooltipField="Proveedor")
    gb.configure_column("RUC", width=115)
    gb.configure_column("Total", type=["numericColumn"], width=115,
                        valueFormatter="'S/ ' + "
                        "Number(value).toLocaleString('es-PE',"
                        "{minimumFractionDigits:2, maximumFractionDigits:2})")
    # «Pendiente» en ámbar: no es un error, es una compra que SUNAT ve y
    # todavía no está anotada — o sea, crédito fiscal sin tomar. Merece
    # saltar a la vista sin gritar como un rojo de error.
    gb.configure_column(
        "Situación", width=105,
        cellStyle=JsCode(
            "function(p){ return p.value === 'Pendiente' "
            "? {'color':'%s','fontWeight':'600'} : {'color':'%s'}; }"
            % (ADVERTENCIA_TEXTO, GRIS_TEXTO)))
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    # Re-reparte las columnas cada vez que el grid cambia de TAMANIO. Con la
    # tabla ya apilada a todo el ancho, los dos casos que quedan son plegar
    # el rail de vistas y redimensionar la ventana: sin esto las columnas se
    # quedan con el ancho que midieron al montar y sobra hueco a la derecha.
    # `fit_columns_on_grid_load` solo actua una vez, al cargar.
    # Es seguro aunque el ancho sea chico porque cada columna declara
    # `minWidth` (ver arriba): `sizeColumnsToFit` los respeta y scrollea en
    # vez de aplastar. Es la receta de la documentacion de AG Grid, y no
    # entra en bucle: el evento no se re-dispara por el propio ajuste.
    gb.configure_grid_options(
        rowHeight=30, headerHeight=32,
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
    )

    resp = AgGrid(
        tv, gridOptions=gb.build(),
        height=alturas.por_filas(len(tv), px_fila=30, rol=alturas.APOYO),
        theme="material", custom_css=dict(_css_grid(13)),
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        key="sunat_docs_grid",
    )
    sel = resp.selected_rows
    if sel is None or (hasattr(sel, "empty") and sel.empty) or len(sel) == 0:
        return None
    # Se devuelve el registro COMPLETO del df, no la fila de la vista: la
    # ficha PDF necesita campos que la tabla no muestra (base, moneda).
    return _fila_de(df, sel.iloc[0] if hasattr(sel, "iloc") else sel[0])


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
        f'{sunat._soles(doc, "total")}</span></div>'
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
    agregar) que pertenecen a ESTE comprobante puntual — para la pestaña
    «Detalle sistema».

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


def _sugerir_desde_maestro(lineas_xml, maestro):
    """Como `_parear_lineas_sistema`, pero para un documento que TODAVÍA NO
    tiene ninguna línea en `compras.parquet` (no está registrado) — a
    pedido 2026-08-27, sugiere directo contra el maestro de artículos
    completo (`_maestro_productos`) por similitud de texto sola, ya que no
    hay ninguna compra registrada con la que corroborar cantidad o precio.

    Prefiltra por tokens compartidos (`_candidatos_por_token`) antes de
    correr `difflib` — puntuar cada línea contra las 3.867 filas del
    maestro sin acotar es demasiado lento para una pestaña interactiva,
    ver `_TOPE_CANDIDATOS_MAESTRO`.

    Devuelve una lista paralela a `lineas_xml` con la POSICIÓN de
    `maestro` que mejor calza, o `None` — ver `_asignar_greedy`.
    """
    if maestro.empty or not lineas_xml:
        return [None] * len(lineas_xml)

    nombres = maestro["NOMBRE PRODUCTO"].tolist()
    indice = _indice_tokens_maestro(nombres)

    candidatos = []
    for i, xml_l in enumerate(lineas_xml):
        desc = str(xml_l.get("descripcion") or "")
        a = _norm(desc)
        for pos in _candidatos_por_token(desc, indice):
            sc = difflib.SequenceMatcher(None, a, _norm(str(nombres[pos]))).ratio()
            if sc > _PISO_SCORE_SUGERIDO:
                candidatos.append((sc, i, pos))
    return _asignar_greedy(candidatos, len(lineas_xml))


_COLS_MAESTRO = ["CODIGO PRODUCTO", "NOMBRE PRODUCTO", "UNIDAD KARDEX"]


def _maestro_productos():
    """Código, nombre y unidad de KARDEX de todo el catálogo de artículos —
    a pedido 2026-08-27, no sale de `compras.parquet` (que solo tiene los
    ~1.582 productos que alguna vez se compraron, y su unidad es la de la
    compra puntual, no la de stock) sino de `inventariovalorizado.parquet`,
    el maestro real: 3.867 productos, y CADA código tiene un único nombre y
    unidad (0 conflictos, verificado con DuckDB contra R2 real).

    Cacheado por `data.cargar` (`@st.cache_data(ttl=3600, persist="disk")`)
    — no hace falta otra capa de caché acá encima.
    """
    import data

    m = data.cargar("inventariovalorizado.parquet")
    if m is None or not all(c in m.columns for c in _COLS_MAESTRO):
        return pd.DataFrame(columns=_COLS_MAESTRO)
    return (m[_COLS_MAESTRO].dropna(subset=["CODIGO PRODUCTO"])
            .drop_duplicates().sort_values("NOMBRE PRODUCTO"))


_JS_EDITOR_PRODUCTO = JsCode("""
class ProductoEditor {
    init(params) {
        this.eGui = document.createElement('div');
        this.eInput = document.createElement('input');
        this.eInput.className = 'ag-input-field-input ag-text-field-input';
        this.eInput.style.width = '100%';
        this.eInput.style.height = '100%';
        this.eInput.style.boxSizing = 'border-box';
        this.eInput.setAttribute('list', 'sunat_maestro_datalist');
        this.eInput.setAttribute('autocomplete', 'off');
        this.eInput.value = params.value || '';
        this.eGui.appendChild(this.eInput);
    }
    getGui() { return this.eGui; }
    afterGuiAttached() { this.eInput.focus(); this.eInput.select(); }
    getValue() { return this.eInput.value; }
    isPopup() { return false; }
    isCancelAfterEnd() {
        // Rechaza cualquier texto que no matchee (sin distinguir mayúsculas)
        // algún nombre del maestro -- lo arma `onGridReady`, ver
        // `_detalle_sistema`. Si el set todavía no existe (carrera rara al
        // montar), no bloquea: mejor dejar pasar que trabar la edición.
        var set = window.__sunatMaestroSetLower;
        if (!set) return false;
        var v = (this.eInput.value || '').trim().toLowerCase();
        return !set.has(v);
    }
}
""")
"""Cell EDITOR a mano para "Ítem (sistema)" -- un `<input list=…>` con
autocompletado NATIVO del navegador, no `agRichSelectCellEditor` de AG
Grid (ese es Enterprise, descartado en todo el proyecto — ver CLAUDE.md
§ Restricciones de despliegue). Misma interfaz de Component que ya usan
los cellRenderer de este proyecto (`init`/`getGui`, ver arquitectura.md
regla #25), con los dos métodos propios de un EDITOR (`getValue`,
`isCancelAfterEnd`)."""


def _detalle_sistema(doc, lineas_xml, d):
    """Pestaña «Detalle sistema»: cada línea del XML del proveedor, junto a
    su equivalente en el sistema — código, nombre y unidad de KARDEX del
    maestro de artículos (`_maestro_productos`) — editable EN LA PROPIA
    CELDA, con buscador de sugerencias (a pedido 2026-08-27).

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

    EDITAR EN LA CELDA, no en un formulario aparte: "Ítem (sistema)" es
    `editable=True` con el cell editor `_JS_EDITOR_PRODUCTO` (ver su
    docstring sobre por qué no es `agRichSelectCellEditor`). Al confirmar
    una celda, `update_mode=GridUpdateMode.VALUE_CHANGED` hace que
    Streamlit rerunee con el valor nuevo en `resp.data` — se compara fila
    a fila contra `tv` (lo que se mandó) por `_idx` para encontrar QUÉ
    línea cambió, se resuelve el nombre tipeado a su código (puede haber
    más de un código con el mismo nombre — 9 de 3.867 en el maestro real,
    medido con DuckDB; se toma el primero) y se guarda con
    `sunat.guardar_correccion_linea`. Si el nombre elegido es el MISMO
    que ya sugería automático/sugerido, no se guarda una corrección
    redundante — y si había una corrección vieja que ahora vuelve a
    coincidir con lo automático, se borra (`quitar_correccion_linea`) en
    vez de dejarla pisando algo que saldría igual sin ella.

    Ni esto ni la comparación tocan `compras.parquet` ni el maestro — son
    de solo lectura acá, los arma un ETL aparte; la corrección es una
    anotación de la webapp sobre ESE documento puntual, no un cambio al
    dato de origen.
    """
    filas_pq = _lineas_parquet_del_documento(d, doc)
    correcciones = sunat.correcciones_lineas(doc)
    maestro = _maestro_productos()

    registrado = not filas_pq.empty
    if registrado:
        asignado = _parear_lineas_sistema(lineas_xml, filas_pq)
        _origen_auto = "Automático"
    else:
        asignado = _sugerir_desde_maestro(lineas_xml, maestro)
        _origen_auto = "Sugerido"

    _lookup_cod = dict(zip(maestro["CODIGO PRODUCTO"].astype(str),
                          zip(maestro["NOMBRE PRODUCTO"], maestro["UNIDAD KARDEX"])))
    # nombre (recortado, en minúsculas) -> código: para resolver lo que se
    # tipeó en la celda. Ambiguo (mismo nombre, más de un código) se queda
    # con el primero -- 9 de 3.867 casos reales, medido con DuckDB.
    _lookup_nombre = {}
    for _cod, _nom in zip(maestro["CODIGO PRODUCTO"], maestro["NOMBRE PRODUCTO"]):
        _lookup_nombre.setdefault(str(_nom).strip().lower(), str(_cod))

    if registrado:
        st.caption("Documento registrado: los ítems salen de cruzar "
                   "contra lo que ya está cargado en `compras.parquet`.")
    else:
        st.info("Este documento todavía no está cargado en el sistema — "
                "SUNAT lo ve, pero sigue «Pendiente». Los ítems de abajo "
                "son SUGERENCIAS por nombre contra el maestro de "
                "artículos, sin ninguna compra registrada que las "
                "confirme.")

    def _codigo_auto(i):
        """El código que sugiere automático/sugerido para la línea `i`,
        sin mirar correcciones -- lo que "editar y volver a lo mismo"
        necesita comparar."""
        if asignado[i] is None:
            return None
        if registrado:
            return str(filas_pq.iloc[asignado[i]]["COD_PRODUCTO"])
        return str(maestro.iloc[asignado[i]]["CODIGO PRODUCTO"])

    filas_tabla = []
    for i, xml_l in enumerate(lineas_xml):
        correccion = correcciones.get(i)
        cod_auto = _codigo_auto(i)
        if correccion:
            cod_sis = str(correccion.get("cod_producto", ""))
            origen = "Corregido"
            _respaldo = correccion.get("nombre_producto", "")
        elif cod_auto is not None:
            cod_sis = cod_auto
            origen = _origen_auto
            _respaldo = ""
        else:
            cod_sis, origen, _respaldo = "", "Sin coincidencia", ""
        # Del maestro sale nombre Y unidad; si el código no está ahí (no
        # debería pasar), al menos no se pierde el nombre que ya se tenía.
        nom_sis, uni_sis = _lookup_cod.get(cod_sis, (_respaldo, ""))
        filas_tabla.append({
            "_idx": i,
            "_cod_auto": cod_auto or "",
            "Código prov.": xml_l.get("codigo", ""),
            "Ítem (XML)": xml_l.get("descripcion", ""),
            "Cant.": xml_l.get("cantidad"),
            "Código sistema": cod_sis,
            "Ítem (sistema)": nom_sis,
            "Unidad kardex": uni_sis,
            "Origen": origen,
        })

    tv = pd.DataFrame(filas_tabla)
    _js_cant = JsCode(
        "function(p){ return p.value==null ? '' : "
        "Number(p.value).toLocaleString('es-PE',{maximumFractionDigits:2}); }")
    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=True, filter=False,
                                editable=False, suppressMovable=True)
    gb.configure_column("_idx", hide=True)
    gb.configure_column("_cod_auto", hide=True)
    gb.configure_column("Código prov.", width=95, minWidth=95)
    gb.configure_column("Ítem (XML)", minWidth=150, flex=1)
    gb.configure_column("Cant.", type=["numericColumn"], width=75,
                        minWidth=75, valueFormatter=_js_cant)
    gb.configure_column("Código sistema", width=105, minWidth=105)
    # LA columna editable -- ver el docstring de la función y de
    # `_JS_EDITOR_PRODUCTO`. El tinte lavanda es la misma señal visual de
    # "interactivo" que usa el resto de la app (`_ficha_html`, la barra de
    # TOTAL), acá marcando "esta celda se puede tocar".
    gb.configure_column(
        "Ítem (sistema)", minWidth=170, flex=1, editable=True,
        cellEditor=_JS_EDITOR_PRODUCTO,
        cellStyle=JsCode(
            "function(p){ return {'background': '%s', 'cursor': 'text'}; }"
            % LAVANDA_FONDO))
    gb.configure_column("Unidad kardex", width=100, minWidth=100)
    # Misma convención que "Estado" en `_tabla_cruce`: ámbar = revisar
    # ("sin coincidencia" o "sugerido, sin confirmar todavía"). "Corregido"
    # va con el acento de marca porque no es un problema, es una
    # intervención humana que conviene notar.
    gb.configure_column(
        "Origen", width=128, minWidth=128,
        cellStyle=JsCode(
            "function(p){ var m={'Corregido':'%s','Sugerido':'%s',"
            "'Sin coincidencia':'%s'}; var c=m[p.value];"
            " return c ? {'color':c,'fontWeight':'600'} : {'color':'%s'}; }"
            % (ACENTO_TEXTO, ADVERTENCIA_TEXTO, ADVERTENCIA_TEXTO, GRIS_TEXTO)))
    # `onGridReady` arma UNA vez por sesión de navegador (guardia
    # `window.__sunatMaestroSetLower`, sobrevive a cambiar de documento) el
    # <datalist> que alimenta el autocompletado y el set de nombres válidos
    # que usa `isCancelAfterEnd`. `singleClickEdit` + `stopEditingWhenCells
    # LoseFocus`: un clic entra a editar y clickear afuera confirma, como
    # una celda de Excel -- sin esto haría falta doble clic y Enter.
    _opciones_json = json.dumps(
        maestro["NOMBRE PRODUCTO"].astype(str).tolist(), ensure_ascii=False)
    _js_on_ready = JsCode(
        "function(params){"
        " if (window.__sunatMaestroSetLower) return;"
        " var opciones = %s;"
        " window.__sunatMaestroSetLower = new Set(opciones.map("
        "   function(o){ return o.trim().toLowerCase(); }));"
        " var dl = document.getElementById('sunat_maestro_datalist');"
        " if (!dl) {"
        "   dl = document.createElement('datalist');"
        "   dl.id = 'sunat_maestro_datalist';"
        "   document.body.appendChild(dl);"
        " }"
        " opciones.forEach(function(o){"
        "   var opt = document.createElement('option');"
        "   opt.value = o;"
        "   dl.appendChild(opt);"
        " });"
        "}" % _opciones_json)
    gb.configure_grid_options(
        rowHeight=30, headerHeight=32, singleClickEdit=True,
        stopEditingWhenCellsLoseFocus=True, onGridReady=_js_on_ready,
        onGridSizeChanged=JsCode("function(p){ p.api.sizeColumnsToFit(); }"),
        # Esta tabla vive en la columna angosta ("Original del proveedor",
        # ~300-400px) con 8 columnas que no entran sin scroll horizontal
        # -- eso es esperable (mismo criterio que `_tabla_cruce`). Lo que
        # NO conviene es la virtualización de columnas por defecto: con el
        # marco tan angosto, deja sin nodo DOM a "Ítem (sistema)" hasta
        # que alguien scrollea hasta ahí, y esa es justo la columna
        # editable. Ocho columnas es nada para el navegador — desactivar
        # la virtualización cuesta cero acá y evita esa sorpresa.
        suppressColumnVirtualisation=True,
    )
    # Key con el documento adentro: sin esto, AG Grid retiene estado del
    # lado del cliente al cambiar de documento -- antes fue la fila
    # seleccionada y reventó en vivo con menos líneas que el documento
    # anterior (IndexError, ver arquitectura.md regla #224); con edición en
    # celda el mismo riesgo aplica igual. Con la key distinta, AG Grid
    # monta un componente nuevo por documento y arranca limpio.
    _doc_id = str(doc.get("documento") or "")
    resp = AgGrid(
        tv, gridOptions=gb.build(),
        height=alturas.por_filas(len(tv), px_fila=30, rol=alturas.MINI),
        theme="material", custom_css=dict(_css_grid(12)),
        allow_unsafe_jscode=True, fit_columns_on_grid_load=True,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode=DataReturnMode.AS_INPUT,
        key=f"sunat_detalle_sistema_grid_{_doc_id}",
    )
    st.caption("Clic en «Ítem (sistema)» para corregirlo — el buscador "
               "sugiere mientras escribís, contra el catálogo completo.")

    # ¿Cambió algo? Comparar lo que volvió (`resp.data`) contra lo que se
    # mandó (`tv`), fila a fila por `_idx` -- no por posición, para no
    # depender de que el orden se mantenga igual.
    devuelto = resp.data
    if devuelto is None or len(devuelto) == 0:
        return
    for _, fila in devuelto.iterrows():
        try:
            i = int(fila["_idx"])
        except (TypeError, ValueError):
            continue
        if i < 0 or i >= len(lineas_xml):
            continue          # ver regla #224: fila de un documento viejo
        nuevo_nombre = str(fila.get("Ítem (sistema)") or "").strip()
        original = str(tv.loc[tv["_idx"] == i, "Ítem (sistema)"].iloc[0]).strip()
        if nuevo_nombre == original:
            continue

        cod_nuevo = _lookup_nombre.get(nuevo_nombre.lower())
        if cod_nuevo is None:
            # El editor ya rechaza esto del lado del navegador
            # (`isCancelAfterEnd`) -- si igual llega acá es que algo
            # puenteó la UI. No se guarda cualquier cosa como si fuera un
            # código real; se avisa y se vuelve al último valor válido.
            st.warning(f"«{nuevo_nombre}» no es un producto del maestro — "
                       "no se guardó. Elegí una sugerencia de la lista.")
            st.rerun()
            continue

        cod_auto_linea = str(tv.loc[tv["_idx"] == i, "_cod_auto"].iloc[0])
        if cod_nuevo == cod_auto_linea:
            # Volvió a coincidir con lo automático/sugerido: si había una
            # corrección vieja, ya no hace falta -- se saca en vez de
            # dejarla pisando algo que saldría igual sin ella.
            if i in correcciones:
                sunat.quitar_correccion_linea(doc, i)
                st.rerun()
        else:
            if sunat.guardar_correccion_linea(doc, i, cod_nuevo, nuevo_nombre):
                st.rerun()
            else:
                st.error("No se pudo guardar. ¿Están las credenciales de "
                         "R2 configuradas?")


def _mostrar_original(doc, pdf_bytes, xml_bytes, d):
    """El comprobante del proveedor —PDF real, detalle de líneas, XML,
    detalle contra el sistema— EN LA COLUMNA, no detrás de un botón.

    Hasta 2026-08-27 esto vivía en un `st.dialog` que un botón «Ver el
    original» abría a demanda. A pedido pasó a mostrarse directo, al lado
    de la ficha del SIRE (`_panel_documento`): es lo primero que alguien
    quiere ver de un documento ya sincronizado, no una acción secundaria
    escondida detrás de un clic.

    Costo de ese cambio, para quien lo vuelva a tocar: `sunat.paginas_pdf`
    (que renderiza cada página a PNG) ahora corre en CUANTO se elige un
    documento con original sincronizado, no solo cuando alguien pedía
    verlo. Lo mitiga su propia caché (`@st.cache_data(ttl=1800,
    max_entries=20)`, ver `sunat.py`) — la primera vista de un documento
    paga el render, las siguientes no.

    EL PDF SE MUESTRA COMO IMAGEN, no embebido: Chrome no renderiza un
    `data:application/pdf` dentro de un iframe con `sandbox` y Streamlit
    monta todos sus iframes así (ver `_ficha_html`). Renderizarlo del lado
    del servidor además funciona igual en el teléfono, donde un visor de
    PDF embebido es incómodo.

    `d` es el parquet de Compras completo (lo trae `renderizar_documentos_
    sunat`, que ya lo recibe para la vista "Cruce") — lo necesita la
    pestaña «Detalle sistema» (`_detalle_sistema`) para buscar las líneas
    de ESTE documento y el catálogo completo de productos.
    """
    lineas = sunat.lineas_xml(xml_bytes) if xml_bytes else []
    nombres = []
    if pdf_bytes:
        nombres.append("📄 Comprobante")
    if lineas:
        nombres.append(f"📋 Detalle ({len(lineas)})")
    if xml_bytes:
        nombres.append("🧾 XML")
    # Después de XML, a pedido 2026-08-27: no tiene sentido corregir el
    # emparejamiento contra el sistema sin haber visto primero el detalle
    # crudo del XML del que sale.
    if lineas:
        nombres.append("📑 Detalle sistema")

    if not nombres:
        st.info("No hay nada que mostrar todavía.")
        return

    for nombre, tab in zip(nombres, st.tabs(nombres)):
        with tab:
            if nombre.startswith("📄"):
                with st.spinner("Preparando el comprobante…"):
                    paginas = sunat.paginas_pdf(pdf_bytes)
                if not paginas:
                    st.warning("No se pudo mostrar el PDF en pantalla. "
                               "Se puede descargar igual, abajo.")
                for i, png in enumerate(paginas, 1):
                    st.image(png, use_container_width=True)
                    if len(paginas) > 1:
                        st.caption(f"Página {i} de {len(paginas)}")
            elif nombre.startswith("📑"):
                _detalle_sistema(doc, lineas, d)
            elif nombre.startswith("📋"):
                _tabla_detalle(lineas)
            else:
                # Recortado: un XML de 30 KB dentro de un `st.code` cuelga
                # el navegador al resaltar la sintaxis.
                txt = xml_bytes.decode("utf-8", errors="replace")
                if len(txt) > 20000:
                    st.caption(f"Mostrando los primeros 20.000 de "
                               f"{len(txt):,} caracteres. Descargalo para verlo entero.")
                    txt = txt[:20000]
                st.code(txt, language="xml")

    st.divider()
    c1, c2 = st.columns(2)  # columnas-internas: 2 botones de descarga
    with c1:
        if pdf_bytes:
            st.download_button(
                "⬇ Descargar PDF", data=pdf_bytes,
                file_name=f"{doc.get('documento', 'comprobante')}.pdf",
                mime="application/pdf", use_container_width=True,
                key="sunat_original_dl_pdf")
    with c2:
        if xml_bytes:
            st.download_button(
                "⬇ Descargar XML", data=xml_bytes,
                file_name=f"{doc.get('documento', 'comprobante')}.xml",
                mime="application/xml", use_container_width=True,
                key="sunat_original_dl_xml")


def _panel_documento(doc, d):
    """Panel derecho: ficha del SIRE y original del proveedor, LADO A LADO.

    `d` es el parquet de Compras completo (recibido de
    `renderizar_documentos_sunat`) — se necesita para armar la pestaña
    «Detalle sistema» de `_mostrar_original`, ver su docstring.

    Hasta 2026-08-27 iban apiladas (ficha arriba, "Original del proveedor"
    abajo con un botón que abría un `st.dialog`) — a pedido pasaron a dos
    columnas, con el original YA VISIBLE cuando está sincronizado (ver
    `_mostrar_original`), sin el clic de más. La cabecera (tipo/documento/
    proveedor) sigue siendo UNA sola, arriba de las dos columnas: identifica
    el documento elegido para ambos paneles, no es parte de ninguno.

    El split es un `st.columns(2)` con `# columnas-internas`, NO
    `COLUMNAS_DRILL` (CLAUDE.md): esa constante es la proporción con la
    que se parte una FILA del drill —acá la fila (`sunat_card_izq`, la
    tabla) sigue a lo ancho completo, como quedó el 2026-08-21 después de
    medir que achicarla apretaba `fit_columns_on_grid_load` hasta dejar
    columnas ilegibles (ver el docstring de `renderizar_documentos_sunat`).
    Esta subdivisión es OTRA cosa: dos paneles DENTRO de la tarjeta de
    abajo, como la botonera de `_c_ref`/`_c_xls` más arriba en este mismo
    archivo.
    """
    if doc is None:
        st.markdown(
            f'<div style="padding:28px 16px;text-align:center;color:{GRIS_TEXTO};'
            f'font-size:13px;line-height:1.6;">'
            f'<div style="font-size:30px;margin-bottom:6px;">📄</div>'
            f'Elegí un documento de la tabla<br>para verlo acá.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div style="background:{LAVANDA_FONDO};border-radius:8px;'
        f'padding:10px 14px;margin-bottom:10px;">'
        f'<div style="font-size:11px;color:{GRIS_TEXTO};text-transform:uppercase;'
        f'letter-spacing:.04em;">{doc.get("tipo_nombre", "Comprobante")}</div>'
        f'<div style="font-size:17px;font-weight:600;color:{TEXTO_PRINCIPAL};">'
        f'{doc.get("documento", "")}</div>'
        f'<div style="font-size:12px;color:{GRIS_TEXTO};margin-top:2px;">'
        f'{_compras_truncar(str(doc.get("proveedor", "")), 44)}</div></div>',
        unsafe_allow_html=True,
    )

    col_ficha, col_original = st.columns(2)  # columnas-internas: ficha SIRE y original del proveedor, lado a lado

    with col_ficha:
        _ficha_html(doc)

        try:
            pdf_bytes = sunat.ficha_pdf(doc)
        except Exception as e:
            st.error(f"No se pudo generar el PDF: {e}")
            pdf_bytes = None

        if pdf_bytes:
            st.download_button(
                "⬇️  Descargar PDF", data=pdf_bytes,
                file_name=f"{doc.get('documento', 'comprobante')}.pdf",
                mime="application/pdf", use_container_width=True,
                key="sunat_dl_pdf")
        st.caption("Ficha con los datos del SIRE. No es el PDF que emitió "
                   "el proveedor.")

    with col_original:
        st.markdown(
            f'<div style="font-size:10px;font-weight:700;color:{ACENTO};'
            f'text-transform:uppercase;letter-spacing:.05em;margin:0 0 6px;'
            f'padding-bottom:3px;border-bottom:1px solid {GRIS_BORDE};">'
            f'Original del proveedor</div>', unsafe_allow_html=True)

        # El original vive en R2 solo si `sunat_originales_sync.py` ya pasó
        # por este documento — ver el docstring del módulo. Ninguno de los
        # dos `None` es un error: es el estado normal antes del primer sync.
        pdf_original, xml_original = sunat.originales(doc)

        if pdf_original or xml_original:
            # Antes esto era un botón "Ver el original" que abría un
            # `st.dialog` — a pedido 2026-08-27 se muestra DIRECTO, sin
            # ese clic. Ver `_mostrar_original`.
            _mostrar_original(doc, pdf_original, xml_original, d)
            st.caption("PDF y XML tal como los emitió el proveedor.")
        elif sunat.solicitud_pendiente(doc):
            # La corrida nocturna va de lo más nuevo hacia atrás y tarda
            # semanas en llegar a lo viejo (ver regla #142), así que acá se
            # ofrece pedirlo puntualmente. La webapp NO abre ningún
            # navegador: deja una señal en R2 y la CPU local hace el
            # trabajo — mismo mecanismo que el refresco de parquets
            # (regla #144).
            st.info("⏳ Pedido. La máquina local lo está trayendo de SUNAT — "
                    "suele tardar menos de un minuto. Volvé a entrar al "
                    "documento en un rato.", icon=None)
        else:
            # Un intento anterior que falló: sin esto el usuario ve el
            # mismo botón de siempre y no tiene forma de saber que ya se
            # intentó y no se pudo.
            fallo = sunat.fallo_solicitud(doc)
            if fallo:
                st.warning(f"No se pudo traer: "
                           f"{fallo.get('motivo', 'error desconocido')}",
                           icon="⚠️")
                st.caption(f"Último intento: {fallo.get('cuando', '—')}")
                etiqueta = "↻ Intentar de nuevo"
            else:
                etiqueta = "⬇ Traer el original de SUNAT"

            if st.button(etiqueta, use_container_width=True,
                         key="sunat_pedir_original",
                         help="Le pide a la máquina local que baje el PDF y "
                              "el XML que emitió el proveedor. Tarda menos "
                              "de un minuto; después queda guardado para "
                              "siempre."):
                if sunat.solicitar_original(doc):
                    st.rerun()
                else:
                    st.error("No se pudo dejar el pedido. ¿Están las "
                             "credenciales de R2 configuradas?")
            if not fallo:
                st.caption("Todavía no sincronizado. Al lado está la ficha "
                           "con los datos del registro, que siempre está "
                           "disponible.")


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


def renderizar_documentos_sunat(d, col_fecha):
    """Punto de entrada del drill. Lo llama `graficos/compras/__init__.py`.

    `d` y `col_fecha` (el parquet de Compras y su columna de fecha) SOLO
    se usan para la vista "Cruce" (`cruzar_con_parquet`) — el resto de la
    vista sigue saliendo entero de SUNAT. Ver `arquitectura.md` regla #143.

    LOS CONTROLES VIVEN DENTRO DE LA TARJETA IZQUIERDA, no en una franja
    aparte arriba de las dos columnas — mismo criterio que el selector "La
    semana empieza" del drill Semanal (`compras/__init__.py`). No es gusto:
    esta app no tiene scroll de PÁGINA (el main lo recorta), así que
    cualquier bloque que viva AFUERA de las tarjetas empuja a ambas hacia
    abajo sin que `--alto-util` se entere — el clamp de cada tarjeta se
    sigue calculando como si arrancara donde arranca cualquier otra vista.
    Medido en el navegador antes de corregirlo: con período/vista/KPIs en
    una franja externa, la tarjeta arrancaba en y=266 (contra ~165 de
    Proveedor) y su borde inferior quedaba en 990 con un viewport de
    900 — 90px inalcanzables, sin error ni aviso.
    """
    f_ini, f_fin = _rango_vigente()

    # 2026-08-21, a pedido: de DOS COLUMNAS a apilado. La tabla vivia en
    # `st.columns([1.6, 1])`, o sea ~474px utiles: medido,
    # `fit_columns_on_grid_load` aplastaba Fecha a 36px y Situacion a 43.
    # Se probo antes resolverlo con el ⛶ de pantalla completa y se descarto
    # a pedido — tapaba el resto de la vista. Ahora la tabla toma el ancho
    # entero del canvas y la ficha del documento pasa DEBAJO, tambien a lo
    # ancho (ver `_ficha_html`, que reparte los grupos en columnas para no
    # quedar como una lista larguisima de dos palabras por fila).
    with st.container(border=True, key="sunat_card_izq"):
        # 2026-08-21, a pedido: los dos selectores APILADOS y sin caja, y
        # las acciones en iconos. Antes iban lado a lado y cada uno con su
        # marco de 40px de alto (borde 1px + fondo blanco sobre el
        # `div[role="group"]` de react-aria, medido). Ahora se leen como dos
        # lineas de texto con su chevron — el CSS vive en
        # `estilos/_30_filtros.py`, scopeado a `sunat_card_izq`.
        c_sel, c_act, c_kpi = st.columns([1.5, 0.8, 4.1])
        with c_sel:
            # El pill de fecha, DENTRO de la tarjeta (a pedido 2026-08-21).
            # Aca la fecha no es contexto global: es EL filtro de la tabla —
            # el rango que se le consulta al SIRE— asi que vivia lejos de lo
            # que filtra. NO es una copia del de la franja: es la MISMA
            # llamada, movida. `app.py` lo publica y deja de dibujarlo
            # cuando esta vista esta activa (`vista_quiere_fecha_propia`),
            # porque el widget no se puede duplicar: su key es la clave
            # canonica del rango. Ver el docstring de `franja_fecha`.
            franja_fecha.render()
            # 2026-08-21, a pedido: de radio horizontal a selectbox. Con
            # `horizontal=True` en una columna de 166px las 3 opciones
            # NO entraban en una fila y Streamlit las apilaba en 3 líneas
            # (medido: 99px de alto, contra ~40 de un selectbox) — el
            # widget se veía roto, no compacto. El selectbox es la misma
            # idea que un `st.radio` (una sola elección entre pocas) pero
            # SIEMPRE en una línea: muestra el valor elegido + una
            # flecha, y la lista aparece recién al abrir. Mismos values,
            # misma key: session_state no pierde la selección previa.
            vista = st.selectbox(
                "Ver", ["Por fecha", "Por proveedor", "Cruce"],
                key="sunat_vista",
                label_visibility="collapsed",
                help="«Cruce» compara cada comprobante del SIRE contra "
                     "el registro interno de compras (parquet): mismo "
                     "documento, ¿coinciden los montos?")
            situacion = st.selectbox(
                "Situación", ["Todos", "Registrados", "Pendientes"],
                key="sunat_situacion",
                label_visibility="collapsed",
                help="«Pendiente» = SUNAT ve la compra pero todavía no "
                     "está anotada en un registro presentado. Es crédito "
                     "fiscal sin tomar.",
            )
        with c_act:
            _c_ref, _c_xls = st.columns(2)  # columnas-internas: 2 iconos de accion
        with _c_ref:
            _ayuda = "Volver a consultar a SUNAT"
            if not sunat.secrets_disponibles():
                _ayuda += (". Sin credenciales configuradas: se "
                           "muestran datos de ejemplo (agregá "
                           "SUNAT_RUC, SUNAT_USUARIO_SOL, "
                           "SUNAT_CLAVE_SOL, SUNAT_CLIENT_ID y "
                           "SUNAT_CLIENT_SECRET a los secrets).")
            # Limpia TODAS las cachés de la cadena: la del parquet, la
            # del rango y la de cada período. La del rango sola
            # devolvería lo mismo, porque se apoya en las otras.
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
            # El boton de exportar vive ARRIBA (a pedido) pero los datos que
            # exporta se calculan MAS ABAJO — depende de la vista y del
            # filtro de situacion. `st.empty()` reserva el sitio ahora y se
            # rellena cuando el df existe: es la unica forma de tener un
            # control arriba que dependa de algo de abajo sin partir el
            # flujo en dos reruns.
            _slot_excel = st.empty()

        # El cuerpo va en una funcion anidada por una razon concreta: sus
        # cuatro salidas tempranas (sin rango, SUNAT caido, sin
        # comprobantes, sin comprobantes de esa situacion) eran `return`
        # del render ENTERO, asi que cualquiera de ellas se llevaba puesta
        # tambien la tarjeta de la ficha de abajo -- la pantalla perdia una
        # caja y el resto saltaba. Ahora cada salida devuelve `None` y las
        # dos tarjetas se dibujan siempre. Es la regla #115 aplicada a este
        # drill: dibujar las tarjetas siempre y decidir el CONTENIDO adentro.
        def _cuerpo():
            """La tabla y su dato. Devuelve el documento elegido, o None."""
            if f_ini is None:
                # Practicamente inalcanzable (`app.py::asegurar_rango`
                # siembra un default), pero si pasara, el pill de fecha ya
                # esta dibujado JUSTO ARRIBA de este mensaje.
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

            # El filtro de situación se aplica ANTES de decidir qué mostrar
            # arriba (KPIs normales o KPIs del cruce): en «Cruce», filtrar a
            # Pendientes primero y cruzar después responde una pregunta
            # real — "de lo que aún no presenté, ¿qué ya tengo cargado en
            # el sistema?" — que se pierde si se cruza sobre el rango
            # completo sin filtrar.
            vis = df if situacion == "Todos" else df[
                df["situacion"] == situacion[:-1]]   # "Registrados"→"Registrado"
            if vis.empty:
                st.info(f"No hay comprobantes «{situacion.lower()}» en el rango.")
                return None

            _sufijo = f"{pd.Timestamp(f_ini):%Y%m%d}_{pd.Timestamp(f_fin):%Y%m%d}"

            if vista == "Cruce":
                g_pq = _parquet_agrupado_por_documento(d, col_fecha, f_ini, f_fin)
                df_cruce = cruzar_con_parquet(vis, g_pq)
                with c_kpi:
                    _kpis_cruce(df_cruce)
                doc = _tabla_cruce(df_cruce, vis)
                _exportable, _nombre_xls = df_cruce, f"sunat_cruce_{_sufijo}.xlsx"
            else:
                with c_kpi:
                    _kpis(df, _origen)
                # Dos vistas, dos widgets distintos: «Por fecha» sigue
                # siendo una figura y «Por proveedor» es una tabla desde
                # 2026-08-24. El if vive acá y no adentro de una funcion
                # `_grafico(df, vista)` que ya no dibujaria un grafico.
                if vista == "Por proveedor":
                    _ranking_proveedores(vis)
                else:
                    _grafico_por_fecha(vis)
                doc = _tabla(vis)
                _exportable, _nombre_xls = vis, f"sunat_compras_{_sufijo}.xlsx"

            # Se rellena el hueco reservado ARRIBA, junto al boton de refrescar.
            # Exporta lo que la tabla esta mostrando: el cruce si la vista es
            # «Cruce», el registro filtrado por situacion si no.
            with _slot_excel:
                st.download_button(
                    "⬇", data=_excel_bytes(_exportable),
                    file_name=_nombre_xls,
                    mime=("application/vnd.openxmlformats-officedocument"
                          ".spreadsheetml.sheet"),
                    key="sunat_dl_xlsx", use_container_width=True,
                    help="Exportar a Excel lo que muestra la tabla",
                )

            return doc

        doc = _cuerpo()

    # La ficha va DEBAJO de la tabla, no al costado. Sin espaciador: el que
    # habia (38px) existia solo para alinear el tope de las dos columnas, y
    # apilado no hay nada que alinear.
    with st.container(border=True, key="sunat_card_doc"):
        _panel_documento(doc, d)
