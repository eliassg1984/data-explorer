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

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

import sunat
from estado_rango import clave_rango
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
                "fecha_pq"]
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
                fecha_pq=("_fecha", "first"))
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
        else:
            base_sist = total_sist = dif_base = dif_total = None
            estado, prov_sistema, ruc_sistema = "Solo SUNAT", "", ""

        filas.append({
            "fecha_emision": r.get("fecha_emision"), "documento": doc,
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
    out["fecha_emision"] = pd.to_datetime(out["fecha_emision"], errors="coerce")
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

    Sin `fit_columns_on_grid_load`: son 10 columnas y 4 de plata — forzar
    el ancho del contenedor las dejaría ilegibles. Scrollea horizontal,
    mismo criterio que la tabla pivote de Proveedor.
    """
    tv = pd.DataFrame({
        "Fecha": pd.to_datetime(df_cruce["fecha_emision"], errors="coerce")
                   .dt.strftime("%d/%m/%Y"),
        "Documento": df_cruce["documento"],
        "RUC SUNAT": df_cruce["ruc_proveedor"].fillna(""),
        "RUC sistema": df_cruce["ruc_sistema"].fillna(""),
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
    gb.configure_column("Fecha", width=90, pinned="left")
    gb.configure_column("Documento", width=115, pinned="left")
    gb.configure_column("RUC SUNAT", width=105)
    gb.configure_column("RUC sistema", width=105)
    gb.configure_column("Proveedor SUNAT", minWidth=180)
    gb.configure_column("Proveedor sistema", minWidth=180)
    for col in ("Base SUNAT", "Base sistema", "Total SUNAT", "Total sistema"):
        gb.configure_column(col, type=["numericColumn"], width=115,
                            valueFormatter=_fmt_soles)
    # Igual convención que "Pendiente" en _tabla: ámbar = revisar, rojo =
    # más urgente todavía (plata cargada sin comprobante electrónico que
    # la respalde). "Coincide" no se destaca — lo normal no compite por
    # atención.
    gb.configure_column(
        "Estado", width=118, pinned="right",
        cellStyle=JsCode(
            "function(p){ var m={'Diferencia':'%s','Solo SUNAT':'%s',"
            "'Solo sistema':'%s'}; var c=m[p.value]; "
            "return c ? {'color':c,'fontWeight':'600'} : {'color':'%s'}; }"
            % (ADVERTENCIA_TEXTO, ADVERTENCIA_TEXTO, ERROR, GRIS_TEXTO)))
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_grid_options(rowHeight=30, headerHeight=32)

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
    doc = str(fila["Documento"])
    coincidencias = df_sire[df_sire["documento"].astype(str) == doc]
    return coincidencias.iloc[0] if not coincidencias.empty else None


def _sello_origen(origen):
    """De dónde salió el dato, para la tira de KPIs.

    Un proceso de madrugada sin alertas tiene un agujero conocido: si deja
    de correr, nadie se entera — el dato viejo se ve igual de plausible
    que el fresco (misma lección que la regla #141, donde un total
    creíble bajo un título equivocado lo cazó un usuario, no un test).
    Mostrar la antigüedad lo hace visible sin gastar alto: es un ítem más
    de la línea que ya existe.
    """
    if origen != "parquet":
        return ('<span style="white-space:nowrap;" title="Consultado a la '
                'API de SUNAT en vivo: el parquet del registro todavía no '
                'existe en R2.">en vivo</span>')
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


def _grafico(df, vista):
    """Barras del período: por día de emisión o por proveedor."""
    if vista == "Por proveedor":
        g = (pd.to_numeric(df["total"], errors="coerce")
             .groupby(df["proveedor"].astype(str)).sum()
             .nlargest(10).sort_values())
        if g.empty:
            st.info("Sin datos para graficar.")
            return
        fig = go.Figure(go.Bar(
            x=g.values, y=[_compras_truncar(i, 30) for i in g.index],
            orientation="h", marker=dict(color=ACENTO, opacity=0.9),
            hovertemplate="%{y}<br>S/ %{x:,.2f}<extra></extra>",
        ))
        _compras_layout(fig, alto=alturas.por_filas(len(g), px_fila=26,
                                                    rol=alturas.MINI))
        fig.update_layout(title="Top proveedores del período")
        fig.update_yaxes(showticklabels=True, automargin=True)
        st.plotly_chart(fig, use_container_width=True, key="sunat_g_prov")
        return

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
    })

    gb = GridOptionsBuilder.from_dataframe(tv)
    gb.configure_default_column(resizable=True, sortable=True, filter=False,
                                editable=False, suppressMovable=True)
    gb.configure_column("Fecha", width=95)
    gb.configure_column("Tipo", width=110)
    gb.configure_column("Documento", width=125)
    gb.configure_column("Proveedor", minWidth=190, tooltipField="Proveedor")
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
    gb.configure_grid_options(rowHeight=30, headerHeight=32)

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
    fila = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
    # Se devuelve el registro COMPLETO del df, no la fila de la vista: la
    # ficha PDF necesita campos que la tabla no muestra (CAR, base, moneda).
    doc = str(fila["Documento"])
    coincidencias = df[df["documento"].astype(str) == doc]
    return coincidencias.iloc[0] if not coincidencias.empty else None


def _ficha_html(doc):
    """La ficha del comprobante, pintada en pantalla.

    POR QUÉ NO ES UN PDF EMBEBIDO (probado y descartado el 2026-08-19):
    Chrome no renderiza un `data:application/pdf` dentro de un iframe con
    `sandbox`, y Streamlit monta TODOS sus iframes con sandbox. Medido en
    el navegador: el frame carga con el alto correcto y `contentDocument`
    queda en `null` — o sea, un rectángulo en blanco y ningún error. No es
    algo que se arregle con CSS ni cambiando de `components.html` a
    `st.iframe`.

    Lo que se ve acá es HTML, y sale mejor que el PDF embebido: texto
    nítido en cualquier zoom, hereda la paleta de la app y funciona igual
    en el teléfono. El PDF sigue existiendo para descargar (`ficha_pdf`),
    y ambos salen de `sunat.campos_ficha()`, así que no pueden divergir.

    Un beneficio lateral: al no haber iframe, este panel no cae en la regla
    de `estilos/_00_base.py` que oculta todos los iframes por defecto.
    """
    filas = []
    for titulo, campos in sunat.campos_ficha(doc):
        filas.append(
            f'<div style="font-size:10px;font-weight:700;color:{ACENTO};'
            f'text-transform:uppercase;letter-spacing:.05em;margin:12px 0 4px;'
            f'padding-bottom:3px;border-bottom:1px solid {GRIS_BORDE};">'
            f'{titulo}</div>'
        )
        for etiqueta, valor in campos:
            filas.append(
                f'<div style="display:flex;justify-content:space-between;'
                f'gap:10px;padding:3px 0;font-size:12px;">'
                f'<span style="color:{GRIS_TEXTO};">{etiqueta}</span>'
                f'<span style="color:{TEXTO_PRINCIPAL};font-weight:500;'
                f'text-align:right;">{valor}</span></div>'
            )

    st.markdown(
        f'<div style="padding:2px 2px 8px;">{"".join(filas)}'
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


def _panel_documento(doc):
    """Panel derecho: ficha del comprobante + visor PDF + descargas."""
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

    _ficha_html(doc)

    try:
        pdf_bytes = sunat.ficha_pdf(doc)
    except Exception as e:
        st.error(f"No se pudo generar el PDF: {e}")
        return

    st.download_button(
        "⬇️  Descargar PDF", data=pdf_bytes,
        file_name=f"{doc.get('documento', 'comprobante')}.pdf",
        mime="application/pdf", use_container_width=True, key="sunat_dl_pdf")
    st.caption("Ficha con los datos del SIRE. No es el PDF que emitió el "
               "proveedor.")

    # El original vive en R2 solo si `sunat_originales_sync.py` ya pasó por
    # este documento — ver el docstring del módulo. Ninguno de los dos
    # `None` es un error: es el estado normal antes del primer sync.
    pdf_original, xml_original = sunat.originales(doc)

    st.markdown(
        f'<div style="font-size:10px;font-weight:700;color:{ACENTO};'
        f'text-transform:uppercase;letter-spacing:.05em;margin:14px 0 6px;'
        f'padding-bottom:3px;border-bottom:1px solid {GRIS_BORDE};">'
        f'Original del proveedor</div>', unsafe_allow_html=True)

    if pdf_original or xml_original:
        c_pdf, c_xml = st.columns(2)
        with c_pdf:
            if pdf_original:
                st.download_button(
                    "📄 PDF original", data=pdf_original,
                    file_name=f"{doc.get('documento', 'comprobante')}_original.pdf",
                    mime="application/pdf", use_container_width=True,
                    key="sunat_dl_pdf_original")
        with c_xml:
            if xml_original:
                st.download_button(
                    "🧾 XML", data=xml_original,
                    file_name=f"{doc.get('documento', 'comprobante')}.xml",
                    mime="application/xml", use_container_width=True,
                    key="sunat_dl_xml_original")
        return

    # Todavía no está en R2. La corrida nocturna va de lo más nuevo hacia
    # atrás y tarda semanas en llegar a lo viejo (ver regla #142), así que
    # acá se ofrece pedirlo puntualmente. La webapp NO abre ningún
    # navegador: deja una señal en R2 y la CPU local hace el trabajo —
    # mismo mecanismo que el refresco de parquets (regla #144).
    if sunat.solicitud_pendiente(doc):
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
    if not fallo:
        st.caption("Todavía no sincronizado. Arriba está la ficha con los "
                   "datos del registro, que siempre está disponible.")


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
    rango = st.session_state.get(clave_rango("Compras", usa_carga_rango=False))
    if not rango or len(rango) < 2 or rango[0] is None or rango[1] is None:
        st.info("Elegí un rango de fechas en la franja de arriba.")
        return
    f_ini, f_fin = rango[0], rango[1]

    col_izq, col_der = st.columns([1.6, 1])

    with col_izq:
        with st.container(border=True, key="sunat_card_izq"):
            c_vista, c_sit, c_act, c_kpi = st.columns([1.7, 1.3, 0.6, 2.8])
            with c_vista:
                vista = st.radio(
                    "Ver", ["Por fecha", "Por proveedor", "Cruce"],
                    horizontal=True, key="sunat_vista",
                    label_visibility="collapsed",
                    help="«Cruce» compara cada comprobante del SIRE contra "
                         "el registro interno de compras (parquet): mismo "
                         "documento, ¿coinciden los montos?")
            with c_sit:
                situacion = st.radio(
                    "Situación", ["Todos", "Registrados", "Pendientes"],
                    horizontal=True, key="sunat_situacion",
                    label_visibility="collapsed",
                    help="«Pendiente» = SUNAT ve la compra pero todavía no "
                         "está anotada en un registro presentado. Es crédito "
                         "fiscal sin tomar.",
                )
            with c_act:
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

            with st.spinner("Cargando el registro de compras de SUNAT…"):
                try:
                    df, _origen = sunat.comprobantes_rango(f_ini, f_fin)
                except Exception as e:
                    st.error(f"No se pudo consultar a SUNAT: {e}")
                    return

            if df is None or df.empty:
                st.info("SUNAT no tiene comprobantes emitidos hacia tu RUC "
                        "en el rango elegido.")
                return

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
                return

            _sufijo = f"{pd.Timestamp(f_ini):%Y%m%d}_{pd.Timestamp(f_fin):%Y%m%d}"

            if vista == "Cruce":
                g_pq = _parquet_agrupado_por_documento(d, col_fecha, f_ini, f_fin)
                df_cruce = cruzar_con_parquet(vis, g_pq)
                with c_kpi:
                    _kpis_cruce(df_cruce)
                doc = _tabla_cruce(df_cruce, vis)
                st.download_button(
                    "⬇ Descargar CSV del cruce",
                    data=df_cruce.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"sunat_cruce_{_sufijo}.csv",
                    mime="text/csv", key="sunat_dl_csv_cruce",
                )
            else:
                with c_kpi:
                    _kpis(df, _origen)
                _grafico(vis, vista)
                doc = _tabla(vis)
                st.download_button(
                    "⬇ Descargar CSV",
                    data=vis.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"sunat_compras_{_sufijo}.csv",
                    mime="text/csv", key="sunat_dl_csv",
                )

    with col_der:
        with st.container(border=True, key="sunat_card_doc"):
            _panel_documento(doc)
