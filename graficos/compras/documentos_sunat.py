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
del registro (`sunat.ficha_pdf`). No es el PDF que emitió el proveedor: esa
API es otra (descarga masiva de CPE) y hoy no está conectada. El panel lo
dice en pantalla — no en un comentario— porque confundir una cosa con la
otra tiene consecuencias contables.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

import sunat
from estado_rango import clave_rango
from tema import (
    ACENTO, ACENTO_TEXTO, ADVERTENCIA_TEXTO, GRIS_BORDE, GRIS_TEXTO,
    LAVANDA_FONDO, TEXTO_PRINCIPAL,
)
from graficos.base import _compras_layout, _compras_truncar
from graficos import alturas
from tablas._css import _css_grid


def _kpis(df):
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


def renderizar_documentos_sunat(d, col_fecha):
    """Punto de entrada del drill. Lo llama `graficos/compras/__init__.py`.

    `d` y `col_fecha` (el parquet de Compras y su columna de fecha) están
    reservados sin usar TODAVÍA: son la entrada natural para cruzar el
    registro de SUNAT contra lo que el propio sistema tiene cargado —
    ver el hallazgo en arquitectura.md regla #141 (77% de match verificado
    entre ambas fuentes, por serie-número). Hasta que se implemente ese
    cruce, todo lo que se muestra acá sale entero de SUNAT.

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
            c_vista, c_sit, c_act, c_kpi = st.columns([1.4, 1.5, 0.7, 2.8])
            with c_vista:
                vista = st.radio("Ver", ["Por fecha", "Por proveedor"],
                                 horizontal=True, key="sunat_vista",
                                 label_visibility="collapsed")
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
                # Limpia las dos cachés (la del rango y la de cada período):
                # la del rango sola devolvería lo mismo, porque se apoya en
                # la de período.
                if st.button("⟳", key="sunat_actualizar", help=_ayuda,
                             use_container_width=True):
                    sunat.obtener_comprobantes.clear()
                    sunat.obtener_comprobantes_rango.clear()
                    sunat.periodos_con_estado.clear()
                    st.rerun()

            with st.spinner("Consultando el registro de compras en SUNAT…"):
                try:
                    df = sunat.obtener_comprobantes_rango(f_ini, f_fin)
                except Exception as e:
                    st.error(f"No se pudo consultar a SUNAT: {e}")
                    return

            if df is None or df.empty:
                st.info("SUNAT no tiene comprobantes emitidos hacia tu RUC "
                        "en el rango elegido.")
                return

            with c_kpi:
                _kpis(df)

            # El filtro se aplica DESPUÉS de los KPIs a propósito: los
            # totales de arriba describen el rango completo, y el filtro
            # sirve para mirar un subconjunto sin perder la referencia.
            vis = df if situacion == "Todos" else df[
                df["situacion"] == situacion[:-1]]   # "Registrados"→"Registrado"
            if vis.empty:
                st.info(f"No hay comprobantes «{situacion.lower()}» en el rango.")
                return

            _grafico(vis, vista)
            doc = _tabla(vis)
            st.download_button(
                "⬇ Descargar CSV",
                data=vis.to_csv(index=False).encode("utf-8-sig"),
                file_name=(f"sunat_compras_{pd.Timestamp(f_ini):%Y%m%d}"
                           f"_{pd.Timestamp(f_fin):%Y%m%d}.csv"),
                mime="text/csv", key="sunat_dl_csv",
            )

    with col_der:
        with st.container(border=True, key="sunat_card_doc"):
            _panel_documento(doc)
