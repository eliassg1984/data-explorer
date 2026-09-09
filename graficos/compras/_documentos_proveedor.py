"""graficos.compras._documentos_proveedor - tabla pivotable de documentos.

Una AgGrid en modo pivote donde cada fila es una linea de detalle
(documento x producto) y el usuario puede arrastrar campos a
Filas/Columnas/Valores desde el panel derecho.

Salio de _compras_proveedor_drill el 2026-08-08. Es la pieza del drill
con MENOS acoplamiento hacia atras: solo necesita 6 valores ya
calculados (abajo, en la firma de `tabla_documentos`). El resto del drill
comparte ~50 locales entre secciones, y por eso no se siguio cortando sin
antes decidir como se pasa ese estado.

2026-09-09, a pedido («bajemos Detalle de documentos por proveedor»): deja
de ser la ultima fila del drill de Proveedor y pasa a ser la ULTIMA SECCION
del reporte, con su propio item en el rail. Eso convierte a este modulo en
un DIBUJANTE de seccion, no en un bloque invitado: `render_seccion` arma
por su cuenta los seis valores que antes le pasaba el drill.

Lo que NO cambia —y es deliberado— es de donde salen esos valores:

· el RANGO sigue siendo el de la seccion Proveedor
  (`CATEGORIA_SEC["compras_sec_proveedor"]`, que ahora tienen las dos);
· los PROVEEDORES siguen siendo los que eligio el filtro del Ranking
  (`cp_prov`), y el filtro propio de esta tarjeta (`cp_docs_prov`) sigue
  recortando DENTRO de eso.

O sea que la tabla dice lo mismo que decia cuando estaba pegada al
ranking; lo unico que cambio es donde aparece. Separar tambien los datos
habria sido otro cambio, y no el que se pidio: dos tablas del mismo drill
con rangos distintos discrepan sin que nada avise (ver el comentario de
`CATEGORIA_SEC`).

2026-08-21, a pedido: la tabla esta SIEMPRE visible. Hasta ese dia el
bloque era colapsable y guardaba su estado en `cp_docs_*` — que no leia
nadie fuera de este modulo, asi que sacarlo no toco nada mas.
"""

import json

import numpy as np
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, JsCode

from inyecciones import inject_maximize_aggrid
from graficos import alturas
from graficos.base import preservar_widgets
from graficos.compras._comun import (
    CATEGORIA_SEC, agregar_periodo, base_normalizada, filtro_proveedores,
    periodos_ordenados, selector_fecha_tarjeta,
)
from graficos.compras._css_proveedor import CSS_PIVOTE_DOCS
from graficos.compras._etiquetas_proveedor import nombre_propio

_KEYS_WIDGET = ("cp_docs_prov_q", "cp_docs_prov_cb::*")
"""El filtro de proveedores de ESTA tabla, que la escalada no puede vaciar.

La consume `preservar_widgets` en el `st.rerun(scope="app")` de más abajo.
Esta sección no es un fragment propio, así que el que aborta es el de
`seccion_perezosa` — y la recolección se lleva igual todo widget suyo que
no se dibujó. Sin esto, mover la fecha de la cabecera volvía a marcar a
todos los proveedores. Ver `graficos/base.py::preservar_widgets` y
`arquitectura.md` regla #373.

Son las keys de `cp_docs_prov`, no las de `cp_prov`: el filtro de acá es
independiente del de la sección de Proveedor (ver el comentario del
llamador), y escribir las del otro sería tocar widgets ajenos."""


def render_seccion(d, col_prov, col_prod, col_cant, col_valor, col_punit,
                   col_um, col_fecha, col_docu):
    """La seccion «Detalle de documentos por proveedor» de la pila.

    Arma los seis valores que `tabla_documentos` necesita y la dibuja. Hasta
    el 2026-09-09 se los pasaba el drill de Proveedor, del que esta tarjeta
    era la ultima fila; ver el docstring del modulo.

    Tres de esos valores se REPRODUCEN aca y no se heredan, y conviene saber
    por que: el drill es un `@st.fragment`, asi que un clic adentro suyo lo
    re-ejecuta a el SOLO. Si esta seccion leyera un `base`/`top_provs` que
    aquel dejo guardado, cada interaccion del drill la dejaria mostrando el
    calculo de la corrida anterior — y no se veria como un error, se veria
    como una tabla que no se entera. Recalcular sobre el mismo `d` y el mismo
    filtro cuesta un `groupby` y no puede desincronizarse.

    `gran` SI se lee de `session_state`: es el widget «Agrupar por» de la
    tarjeta de Evolucion, y decide las COLUMNAS del pivote. Es una de las dos
    dependencias que quedan hacia la seccion Proveedor, y se sostiene porque
    Proveedor es la PRIMERA de la pila —siempre se dibuja antes— y porque
    hay default. Si algun dia esta tabla quiere su propia granularidad, el
    cambio es agregarle el control, no romper esto.

    La otra dependencia es el CSS: `CSS_PROVEEDOR` —que estila `docs_row`,
    `.cp-rank-tit` y todo el prefijo `cp_docs`— lo inyecta el drill de
    Proveedor, no este modulo. Se sostiene por lo mismo (Proveedor va
    primero) y es la MISMA herencia que ya tenia `producto.py` para su
    selector de fecha. Ojo con una sola cosa: si algun dia el ⛶ de «modo
    solo» llega a esta seccion, seria la unica dibujada y se quedaria sin
    ese `<style>`. Hoy ese boton existe unicamente en «Vs año pasado».
    """
    # El escalado a rerun COMPLETO del atajo de fecha. `selector_fecha_tarjeta`
    # levanta la bandera, y quien la baja tiene que ser el dueño de la
    # sección: el FILTRO que consume ese rango vive en `app.py`, fuera de
    # este fragment, así que sin el rerun de app el estado cambia y la
    # pantalla no — botón que responde, datos quietos.
    #
    # Hasta el 2026-09-09 esta línea vivía en `_compras_proveedor_drill`
    # (la tarjeta era su última fila) y se mudó con ella. Es lo único del
    # traslado que NO se ve si se olvida: la fecha se guarda igual, sólo
    # que la tabla sigue mostrando el rango viejo hasta el próximo rerun
    # completo. Mismo mecanismo que `_cp_rank_atajo_pendiente`
    # (proveedor.py) y sus tres hermanos. Ver arquitectura.md #180.
    if st.session_state.pop("_cp_docs_atajo_pendiente", False):
        preservar_widgets(_KEYS_WIDGET)
        st.rerun(scope="app")

    if not (col_prov and col_valor):
        return
    gran = st.session_state.get("compras_prov_gran") or "Mes"
    base = base_normalizada(d, col_prov, col_prod, col_cant, col_valor,
                            col_punit, col_um, col_fecha, col_docu)
    if base.empty or base["valor"].sum() == 0:
        # La tarjeta se dibuja igual (regla #196): su cabecera lleva el
        # selector de fecha, que es lo unico que puede deshacer el rango que
        # dejo la tabla vacia. Un `return` seco aca esconderia la salida.
        with st.container(key="docs_row"):
            with st.container(border=True, key="compras_prov_card_docs"):
                selector_fecha_tarjeta(
                    "cp_docs", "_cp_docs_atajo_pendiente",
                    titulo_html=('<div class="cp-rank-tit">Detalle de '
                                 'documentos por proveedor</div>'),
                    categoria=CATEGORIA_SEC["compras_sec_documentos"])
                st.info("Sin compras en el rango seleccionado. Ampliá el "
                        "rango desde la fecha de esta cabecera, o soltá el "
                        "filtro de Familia.")
        return
    base = agregar_periodo(base, gran)
    # Los proveedores del RANKING, no un universo propio: esta tabla siempre
    # fue el segundo nivel de aquella seleccion (ver el docstring). Se lee
    # sin dibujar — `filtro_proveedores` devuelve la seleccion y el popover
    # por separado, y aca solo se usa la primera mitad.
    _universo = (base.groupby("prov")["valor"].sum()
                 .sort_values(ascending=False).index.tolist())
    _sel_rank, _ = filtro_proveedores("cp_prov", _universo)
    top_provs = [p for p in _sel_rank if p in set(base["prov"].unique())]
    if not top_provs:
        top_provs = _universo
    tabla_documentos(base, top_provs, gran, periodos_ordenados(base),
                     col_docu, col_punit)


def tabla_documentos(base, top_provs, gran, periodos, col_docu, col_punit):
    """Dibuja el bloque con la tabla pivotable de documentos.

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
    #
    # 2026-08-21, a pedido: el bloque dejó de ser COLAPSABLE. Acá vivía un
    # pestillo (`latch_docs` + `cp_btn_docs`) cuyo botón ERA el título, con su
    # estado en `cp_docs_abierto` y un `cp_docs_inst` que forzaba el remount
    # del AgGrid al reabrir para que `fit_columns_on_grid_load` volviera a
    # medir el ancho. Sin abrir/cerrar no hay reapertura, así que el instance
    # id se fue con él: la key del grid vuelve a depender sólo de `gran`.
    # El título pasa a ser texto dentro de la tarjeta, con el mismo
    # `.cp-rank-tit` que usa el ranking de arriba.
    with st.container(key="docs_row"):
        # ── Los DOS controles de la tarjeta (2026-09-04, a pedido) ────
        # "añadamos el selector de fecha, así como el filtro minimalista
        # de proveedor". Son los MISMOS componentes que ya usan el Ranking
        # de proveedores (`cp_rank`) y el de productos (`cp_prod`), no una
        # copia: `base.py::selector_fecha_tarjeta` y
        # `_comun.py::filtro_proveedores`. Su CSS también sale del de
        # Productos, clonado en `_css_proveedor.py::clonar_prefijo`.
        #
        # EL FILTRO ES UN SEGUNDO NIVEL, no un duplicado del de arriba.
        # Esta tabla ya viene acotada a `top_provs`, que es lo que eligió
        # el filtro del Ranking; el de acá recorta DENTRO de eso, para
        # poder mirar el detalle de uno sin sacar a los demás del gráfico.
        # Por eso su universo es `top_provs` y no la lista completa: un
        # filtro que ofreciera proveedores que la tabla no puede mostrar
        # mentiría. Mismo criterio —y mismo pedido, "añadamos el de
        # proveedor"— con el que nació el de Productos, que también es
        # independiente y tiene su propio prefijo de keys.
        #
        # La FECHA, en cambio, sí es compartida por diseño: escribe la
        # clave canónica del rango, así que moverla acá mueve también las
        # otras tarjetas. Son puertas al mismo dato, no filtros paralelos.
        _sel_docs, _pop_docs = filtro_proveedores("cp_docs_prov", top_provs)

        def _cabecera():
            """Título + filtro + fecha, los tres en la misma fila."""
            selector_fecha_tarjeta(
                "cp_docs", "_cp_docs_atajo_pendiente",
                titulo_html=('<div class="cp-rank-tit">Detalle de '
                             'documentos por proveedor · vista '
                             f'{gran}</div>'),
                extra=_pop_docs,
                # LA MISMA CATEGORÍA QUE EL RANKING DE PROVEEDORES, a
                # propósito, aunque desde el 2026-09-09 sean dos secciones
                # distintas: esta tabla se calcula sobre el mismo `base` y
                # los mismos `top_provs` que aquél, así que con rangos
                # distintos mostraría documentos de proveedores rankeados en
                # otro período. `compras_sec_documentos` apunta a
                # `sec_proveedor` justamente para eso — se nombra por la
                # clave de ESTA sección para que se lea que es una decisión,
                # no una herencia.
                categoria=CATEGORIA_SEC["compras_sec_documentos"])

        _bd = base[base["prov"].isin(top_provs)].copy()
        _bd = _bd[_bd["prov"].isin(set(_sel_docs))].copy()
        if _bd.empty:
            # La tarjeta SE DIBUJA IGUAL, con su cabecera. Es la regla
            # #196: un return temprano que se lleva puesto el único
            # control capaz de deshacer el estado que lo causó deja al
            # usuario sin salida — acá, destildar hasta el último
            # proveedor y quedarse sin filtro para volver a tildarlo.
            with st.container(border=True, key="compras_prov_card_docs"):
                _cabecera()
                st.info("Ningún proveedor seleccionado tiene documentos "
                        "en el rango.")
            return
        if not _bd.empty:
            _fe = pd.to_datetime(_bd["fecha"], errors="coerce")
            _pv_docs = pd.DataFrame({
                # Mismo trato que el ranking de arriba: los nombres llegan
                # GRITADOS desde el ERP y una columna entera de mayúsculas
                # se lee como un bloque. `nombre_propio` es puro y está
                # cubierto por `test_graficos.py`.
                #
                # Acá NO hace falta la columna oculta `_prov_raw` que sí
                # lleva el ranking: ese grid COMPARA la selección contra los
                # datos, y este sólo agrupa y muestra. El filtro por
                # `top_provs` ya pasó, arriba, sobre el nombre crudo.
                "Proveedor": [nombre_propio(n) for n in _bd["prov"].astype(str)],
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

            # ── Alto de fila y alto del marco: UN solo número ──────────
            # 2026-09-01, a pedido, probado en el modo diseño ("alto de fila
            # 23px, era 30"). Va en una constante y no en los dos sitios
            # porque son el MISMO número contado dos veces: el `rowHeight`
            # de abajo dice cuánto ocupa una fila, y el `px_fila` del
            # `por_filas` que dimensiona el iframe dice cuántas entran. Si
            # se cambia una sola, el marco deja de coincidir con lo que las
            # filas ocupan y sobra (o falta) media fila al pie.
            _ALTO_FILA_PIVOT = 23
            # ── Los DOS niveles de la cabecera, cada uno con su número ──
            # 2026-09-06, a pedido ("se ve muy sobredimensionada"): eran 38
            # y 38 —los dos por defecto—, o sea 77px de cabecera contra 23px
            # de fila. Medido en el navegador: 3,3 filas de dato gastadas en
            # rotular. Bajan a 24 + 28 = 53. El resto de la dieta (la
            # negrita, las líneas verticales) es CSS y vive en
            # `CSS_PIVOTE_DOCS`; los altos tienen que quedarse acá porque el
            # marco del iframe se dimensiona con ellos, tres líneas abajo.
            #
            # `groupHeaderHeight` NO existía: sin declararlo, el nivel del
            # grupo hereda `headerHeight`, que es de donde salía el 38 × 2.
            _ALTO_GRUPO_PIVOT = 24
            _ALTO_HEADER_PIVOT = 28
            # Todo lo que el grid mide y NO son filas. MEDIDO en el
            # navegador, que es la única forma honesta acá — el 2026-09-06,
            # con la cabecera nueva, `.ag-root-wrapper` 430 menos
            # `.ag-body-viewport` 360 = 70, y las piezas cierran exacto:
            #
            #   2  los dos bordes de 1px del `.ag-root-wrapper`
            #   1  el borde inferior de `.ag-header` (los 52 declarados
            #      arriba son sus dos niveles; el borde va aparte)
            #  15  la barra de scroll HORIZONTAL, que este grid tiene
            #      siempre (las columnas de período no entran nunca en el
            #      ancho disponible)
            #
            # El `ag-sticky-bottom` del gran total NO suma: se superpone al
            # viewport, no lo empuja (53 + 360 + 15 = 428 = el interior del
            # wrapper, sin lugar para sus 24px).
            #
            # De los tres, el que se mueve es el scroll: depende del SO y
            # del navegador, y el 16 que vivía acá se calibró contra uno de
            # 13px. Si vuelve a no cuadrar, se remide — pero conviene que
            # sobre y no que falte: de más queda una franja vacía de 2px, de
            # menos la tabla scrollea media fila (que es como se descubrió
            # el bug original, con los declarados sumando 81).
            _CROMO_GRID_PIVOT = _ALTO_GRUPO_PIVOT + _ALTO_HEADER_PIVOT + 18
            # Filas que el grid muestra SIN expandir: una por proveedor más
            # la del gran total (`grandTotalRow`). Expandir un grupo abre
            # filas nuevas y ésas scrollean por dentro — Python no puede
            # saber cuántas hay, y tampoco tiene por qué: lo que dimensiona
            # el marco es lo que se ve al llegar.
            #
            # Hasta hoy el marco era `alturas.PROTAGONISTA` fijo (430px):
            # con 7 proveedores mostraba 11 filas para llenar 8, y la
            # tarjeta —que ya estaba clampeada a `--alto-util`— se comía
            # media pantalla por nada. `por_filas` mantiene ese 430 como
            # TECHO (es su `rol` por defecto), así que con muchos
            # proveedores no cambia nada: sigue scrolleando por dentro.
            _FILAS_PIVOT = int(_pv_docs["Proveedor"].nunique()) + 1
            _ALTO_PIVOT = alturas.por_filas(
                _FILAS_PIVOT, px_fila=_ALTO_FILA_PIVOT,
                extra=_CROMO_GRID_PIVOT, minimo=0)

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
                "rowHeight": _ALTO_FILA_PIVOT,
                "headerHeight": _ALTO_HEADER_PIVOT,
                "groupHeaderHeight": _ALTO_GRUPO_PIVOT,
                # domLayout NORMAL (no autoHeight): el grid tiene un viewport de
                # alto fijo con scroll interno. Es lo que permite hacer scroll en
                # PANTALLA COMPLETA — el _FS_CSS_IFRAME fuerza el grid a 100vh y
                # confía en el ag-body-viewport para desplazarse. Con autoHeight
                # el grid crecía al contenido y en fullscreen quedaba clippeado
                # sin scroll (mismo criterio que las tablas de Ajuste, que usan
                # normal + paginación y sí scrollean maximizadas).
            }
            # Alto del iframe inline (no fullscreen). En fullscreen lo
            # sobrescribe _FS_CSS_IFRAME a 100vh.
            with _pv_box:
                _cabecera()
                AgGrid(
                    _pv_docs,
                    gridOptions=_grid_pv,
                    allow_unsafe_jscode=True,
                    theme="streamlit",
                    # Sin esto el grid salía con el `theme="streamlit"` de
                    # fábrica —era el único AgGrid del repo sin estilar— y
                    # su cabecera pesaba más que la tabla. El grid es un
                    # iframe: `CSS_PROVEEDOR`, que es del padre, no lo toca.
                    custom_css=CSS_PIVOTE_DOCS,
                    height=_ALTO_PIVOT,
                    enable_enterprise_modules=True,
                    fit_columns_on_grid_load=True,
                    key=f"cp_prov_pivot_docs_{gran}",
                )
                # Botón ⛶ de pantalla completa nativa (mismo patrón que las
                # tablas de tablas/): ancla el ⛶ en el riel de la tabla y usa
                # la Fullscreen API sobre el iframe. En móvil se toca y se gira
                # el teléfono a horizontal para ver todas las columnas; Esc / ✕
                # restauran. Como el drill de Proveedor tiene UN solo AgGrid,
                # buscarIframe() da con este.
                inject_maximize_aggrid()

