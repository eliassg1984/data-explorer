"""graficos.compras._documentos_proveedor - tabla pivotable de documentos.

El bloque que va DEBAJO de los paneles A/B del drill de Proveedor: una
AgGrid en modo pivote donde cada fila es una linea de detalle
(documento x producto) y el usuario puede arrastrar campos a
Filas/Columnas/Valores desde el panel derecho.

Salio de _compras_proveedor_drill el 2026-08-08. Es la pieza del drill
con MENOS acoplamiento hacia atras: solo necesita 6 valores ya
calculados (abajo, en la firma), y su estado de abierto/cerrado
(`cp_docs_*`) es suyo y de nadie mas — nada fuera de este modulo lo lee.
El resto del drill comparte ~50 locales entre secciones, y por eso no se
siguio cortando sin antes decidir como se pasa ese estado.
"""

import json

import numpy as np
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, JsCode

from inyecciones import inject_maximize_aggrid
from graficos import alturas


def tabla_documentos(base, top_provs, gran, periodos, col_docu, col_punit):
    """Dibuja el bloque colapsable con la tabla pivotable de documentos.

    base:      DataFrame normalizado del drill (columnas prov/prod/fecha/
               docu/per/cant/punit/valor).
    top_provs: proveedores visibles; la tabla se acota a ellos para no
               mostrar filas que el grafico de arriba no esta graficando.
    gran:      granularidad activa ("Día"/"Semana"/"Mes"/"Año"). Entra en
               el titulo, en el nombre del CSV y en la key del AgGrid.
    periodos:  lista ordenada de periodos; fija el orden CRONOLOGICO de
               las columnas pivote (sin esto AgGrid las ordena alfabetico).
    col_docu / col_punit: nombres de columna resueltos, o None. Solo se
               usan como PRESENCIA: si no estan, la tabla cae al indice
               como numero de documento y deja el precio unitario vacio.
    """
    # Por defecto: filas = Proveedor→Fecha→Documento→Producto,
    # columnas = Período (Semana/Mes/Año), valor = suma. Gran total al pie.
    if "cp_docs_abierto" not in st.session_state:
        st.session_state["cp_docs_abierto"] = True
    # -- Pestillo (carrete) + titulo en linea. Mismo patron que paneles A/B:
    #    SVG del carrete pintado por CSS sobre ::before del boton; rotacion
    #    de estado (abierto = 180) fijada por <style> inyectado.
    _docs_ab = st.session_state["cp_docs_abierto"]
    # Instance id (mismo patron que paneles A/B): fuerza remount del AgGrid
    # cada vez que el bloque se reabre, para que fit_columns_on_grid_load
    # vuelva a medir el ancho del contenedor.
    if _docs_ab and not st.session_state.get("cp_docs_prev_ab", False):
        st.session_state["cp_docs_inst"] = (
            st.session_state.get("cp_docs_inst", 0) + 1)
    st.session_state["cp_docs_prev_ab"] = _docs_ab
    _docs_inst = st.session_state.get("cp_docs_inst", 0)
    _rot_d = "180deg" if _docs_ab else "0deg"
    # Mismo patron que paneles A/B: abierto -> icono chico en gutter;
    # cerrado -> pill inline con titulo visible.
    _collapse_docs_css = ("""
        .st-key-docs_row { position: relative !important; }
        .st-key-docs_row .st-key-latch_docs {
            position: absolute !important;
            left: -50px !important;
            top: 18px !important;
            margin: 0 !important; z-index: 5;
        }
        .st-key-docs_row .st-key-latch_docs button {
            padding: 8px !important; border-radius: 8px !important;
        }
        .st-key-docs_row .st-key-latch_docs button p {
            display: none !important;
        }
        .st-key-docs_row .st-key-latch_docs button::before {
            width: 24px !important; height: 24px !important;
        }
    """ if _docs_ab else "")
    st.markdown(
        f"<style>.st-key-latch_docs button::before"
        f"{{transform:rotate({_rot_d});}}{_collapse_docs_css}</style>",
        unsafe_allow_html=True,
    )
    with st.container(key="docs_row"):
        with st.container(key="latch_docs"):
            if st.button(f"Detalle de documentos por proveedor · vista {gran}",
                         key="cp_btn_docs",
                         help="Abrir / cerrar el detalle de documentos"):
                st.session_state["cp_docs_abierto"] = not _docs_ab
                st.rerun()
        _bd = base[base["prov"].isin(top_provs)].copy()
        if _docs_ab and not _bd.empty:
            _fe = pd.to_datetime(_bd["fecha"], errors="coerce")
            _pv_docs = pd.DataFrame({
                "Proveedor": _bd["prov"].astype(str).values,
                # Fecha en ISO para orden correcto; se muestra dd/mm/yyyy en el front
                "Fecha": _fe.dt.strftime("%Y-%m-%d").fillna("").values,
                "Documento": (_bd["docu"].astype(str).values
                              if col_docu else _bd.index.astype(str).values),
                "Producto": _bd["prod"].astype(str).values,
                "Periodo": _bd["per"].astype(str).values,
                "Cantidad": _bd["cant"].astype(float).values,
                "Precio Unitario": (_bd["punit"].astype(float).values
                                    if col_punit else np.nan),
                "Valor": _bd["valor"].astype(float).values,
            })

            _pv_box = st.container(border=True, key="compras_prov_card_docs")

            _fmt_soles = JsCode(
                "function(p){ if(p.value==null) return ''; "
                "return 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
            _fmt_pu = JsCode(
                "function(p){ if(p.value==null || isNaN(p.value)) return ''; "
                "return 'S/ ' + Number(p.value).toLocaleString('es-PE',"
                "{minimumFractionDigits:2, maximumFractionDigits:2}); }")
            _fmt_qty = JsCode(
                "function(p){ if(p.value==null || isNaN(p.value)) return ''; "
                "return Number(p.value).toLocaleString('es-PE',"
                "{maximumFractionDigits:2}); }")
            _fmt_fecha = JsCode(
                "function(p){ if(!p.value) return ''; "
                "var s=String(p.value).split('-'); "
                "return s.length===3 ? s[2]+'/'+s[1]+'/'+s[0] : p.value; }")
            # Orden cronológico de las columnas de período en el pivote
            _pivot_cmp = JsCode(
                "function(a,b){ var o=" + json.dumps(periodos) + "; "
                "return o.indexOf(a)-o.indexOf(b); }")

            _col_defs_pv = [
                {"field": "Proveedor", "rowGroup": True, "rowGroupIndex": 0,
                 "hide": True},
                {"field": "Fecha", "rowGroup": True, "rowGroupIndex": 1,
                 "hide": True, "valueFormatter": _fmt_fecha},
                {"field": "Documento", "rowGroup": True, "rowGroupIndex": 2,
                 "hide": True},
                {"field": "Producto", "rowGroup": True, "rowGroupIndex": 3,
                 "hide": True},
                {"field": "Periodo", "headerName": "Período", "pivot": True,
                 "hide": True, "pivotComparator": _pivot_cmp},
                # Orden de columnas de valor: Cantidad -> Precio Unitario -> Valor.
                # AgGrid respeta el orden de declaracion en pivot mode.
                {"field": "Cantidad", "type": "numericColumn", "aggFunc": "sum",
                 "valueFormatter": _fmt_qty, "minWidth": 100},
                {"field": "Precio Unitario", "type": "numericColumn",
                 "aggFunc": "avg", "valueFormatter": _fmt_pu, "minWidth": 110},
                {"field": "Valor", "type": "numericColumn", "aggFunc": "sum",
                 "valueFormatter": _fmt_soles, "minWidth": 110},
            ]

            _grid_pv = {
                "columnDefs": _col_defs_pv,
                "defaultColDef": {
                    "resizable": True, "sortable": True, "filter": True,
                    "enableRowGroup": True, "enablePivot": True,
                    "enableValue": True, "minWidth": 110,
                },
                "pivotMode": True,
                "groupDefaultExpanded": 0,
                # Quita el envoltorio 'sum(...)' / 'avg(...)' de los headers de
                # las columnas pivote: se muestra solo el nombre del campo
                # (Cantidad, Precio Unitario, Valor). Mismo criterio que la
                # tabla de Ajuste de Inventario.
                "suppressAggFuncInHeader": True,
                "autoGroupColumnDef": {
                    "headerName": "Proveedor / Fecha / Documento / Producto",
                    "minWidth": 300, "pinned": "left",
                    "cellRendererParams": {"suppressCount": True},
                },
                "grandTotalRow": "bottom",
                "getRowStyle": JsCode(
                    "function(p){ if(p.node.footer && p.node.level===-1){ "
                    "return {'fontWeight':'600','background':'#EEEDFE',"
                    "'color':'#4938b8'}; } }"),
                "sideBar": {
                    "toolPanels": [{
                        "id": "columns",
                        "labelDefault": "Columnas",
                        "labelKey": "columns",
                        "iconKey": "columns",
                        "toolPanel": "agColumnsToolPanel",
                    }],
                    "position": "right",
                },
                "rowHeight": 30,
                "headerHeight": 38,
                # domLayout NORMAL (no autoHeight): el grid tiene un viewport de
                # alto fijo con scroll interno. Es lo que permite hacer scroll en
                # PANTALLA COMPLETA — el _FS_CSS_IFRAME fuerza el grid a 100vh y
                # confía en el ag-body-viewport para desplazarse. Con autoHeight
                # el grid crecía al contenido y en fullscreen quedaba clippeado
                # sin scroll (mismo criterio que las tablas de Ajuste, que usan
                # normal + paginación y sí scrollean maximizadas).
            }
            # Alto del iframe inline (no fullscreen). En fullscreen lo sobrescribe
            # _FS_CSS_IFRAME a 100vh. 460 ≈ 14 filas visibles con scroll interno.
            with _pv_box:
                AgGrid(
                    _pv_docs,
                    gridOptions=_grid_pv,
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    height=alturas.PROTAGONISTA,
                    enable_enterprise_modules=True,
                    fit_columns_on_grid_load=True,
                    key=f"cp_prov_pivot_docs_{gran}_{_docs_inst}",
                )
                # Botón ⛶ de pantalla completa nativa (mismo patrón que las
                # tablas de tablas/): ancla el ⛶ en el riel de la tabla y usa
                # la Fullscreen API sobre el iframe. En móvil se toca y se gira
                # el teléfono a horizontal para ver todas las columnas; Esc / ✕
                # restauran. Como el drill de Proveedor tiene UN solo AgGrid,
                # buscarIframe() da con este.
                inject_maximize_aggrid()

                st.download_button(
                    "⬇ Descargar CSV",
                    data=_pv_docs.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"compras_documentos_{gran.lower()}.csv",
                    mime="text/csv",
                    key="cp_prov_resumen_dl",
                )
