"""graficos.compras.semanal - drill "Semanal": una barra por período.

Vivía inline en `graficos/compras/__init__.py` (unas 230 líneas dentro del
dispatcher) hasta el 2026-09-04. Se saca a su propio módulo por el mismo
criterio que el resto —`__init__.py` es el dispatcher, un drill por
fichero— y además por una razón medida: al sumarle el selector de fecha de
la tarjeta hizo falta que el drill fuera un `@st.fragment` PROPIO, no el de
`base.py::seccion_perezosa` que envuelve a cada sección de la pila.

Por qué no alcanzaba un `@st.fragment` anidado dentro del dispatcher:
`st.rerun(scope="app")` disparado desde el fragment de la SECCIÓN aborta el
render de esa misma sección, y el delta que el cliente deja de recibir es
justo el suyo — la franja y las otras dos tarjetas se actualizaban y ésta
se quedaba un gesto atrás, con el rango viejo en el trigger y la barra que
ya no entra todavía dibujada en el gráfico. Con el drill en un fragment
aparte, el que aborta es el de adentro y el que redibuja es el de afuera,
que es como ya funcionaban Proveedor, Producto y Volatilidad.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tema import SERIE_PRINCIPAL, TEXTO_PRINCIPAL, BLANCO
from graficos import alturas
from graficos.base import _compras_layout
from graficos.compras._comun import (
    _first_point, _periodo_serie, selector_fecha_tarjeta,
)


@st.fragment
def _compras_semanal_drill(d, col_prod, col_fecha, col_cant, col_punit,
                           col_prov, col_docu, col_valor):
    """Compra por período (día/semana/mes/año o por documento) + detalle.

    `col_valor` entra como NOMBRE de columna y la serie numérica se arma
    acá: el dispatcher ya tenía una (`_valor`), pero pasar el Series
    ataría la firma a que el llamador la haya calculado antes.
    """
    _valor = pd.to_numeric(d[col_valor], errors="coerce").fillna(0)
    # ── Escalada a rerun COMPLETO tras un atajo de fecha ────────
    # La bandera del selector de fecha de esta tarjeta. El filtro
    # que consume ese rango vive en `app.py`, fuera de todo esto:
    # un clic aca re-ejecuta SOLO este fragment, que recibe `d` YA
    # filtrado por el ultimo rerun completo. Sin escalar, el estado
    # cambia y la pantalla no — boton que responde, datos quietos.
    # Va ANTES de dibujar nada para no gastar un render que se va a
    # descartar. Mismo mecanismo que `_cp_rank_atajo_pendiente`
    # (proveedor.py) y `_cp_prod_atajo_pendiente` (producto.py).
    # Ver arquitectura.md #180.
    #
    # OJO con DONDE va, que costo dos intentos medidos en vivo
    # (2026-09-04):
    #   · arriba de `renderizar_graficos_compras` no hace NADA — el
    #     dispatcher no se re-ejecuta en el rerun de una seccion,
    #     porque `seccion_perezosa` ya es un `@st.fragment`;
    #   · dentro del fragment de la SECCION escala bien pero deja
    #     esta tarjeta un gesto atras — ver el comentario del
    #     `@st.fragment` de arriba.
    if st.session_state.pop("_cp_sem_atajo_pendiente", False):
        st.rerun(scope="app")

    # Tarjeta única a todo el ancho de la fila del drill — SIN
    # COLUMNAS_DRILL. Hasta el 2026-09-03 esto partía en col_izq
    # (el gráfico) / col_der (un panel de 5 mini-rankings:
    # Prod. valor/Proveedores/Cantidad/Frecuencia/Alzas precio).
    # Se sacó el panel derecho por redundante — a pedido, viendo el
    # inspector propio del proyecto: esos mismos rankings, pero
    # COMPLETOS y con su propio drill, ya viven un scroll más
    # arriba en la misma página apilada (secciones Proveedor y
    # Producto). Repetir un top-10 de paso acá no sumaba nada, y
    # el gráfico —ahora una serie única, no apilada por
    # producto— aprovecha mejor el ancho entero.
    with st.container(border=True, key="ajuste_graf_card_izq_sem"):
        if col_prod and col_fecha:
            # Agrupar por: el mismo control que Proveedor/Salidas/
            # Requerimientos (Día/Semana/Mes/Año sobre
            # `_periodo_serie`), más una quinta opción propia de
            # esta vista. "Por documento" no agrupa por FECHA,
            # agrupa por COMPRA (fecha+proveedor+Nº documento):
            # una orden con 5 líneas es una compra, no cinco —
            # mismo criterio que `documentos_sunat.py` para no
            # colisionar entre proveedores que reusan su propia
            # numeración (regla #143). 2026-09-03, a pedido: antes
            # esta tarjeta sólo sabía agrupar por semana, con un
            # selector de "la semana empieza en" que se fue con
            # este cambio — la ISO-semana de `_periodo_serie` es
            # la misma que ya usa el resto de la app.
            # Sin `st.columns` alrededor a propósito: eso era del
            # `st.selectbox` que este control reemplazó (un
            # dropdown SE ESTIRA solo al ancho del contenedor,
            # así que 1/3.2 de la tarjeta lo achicaba a propósito
            # para sus 3 opciones). `st.pills` no se estira —
            # mide su propio contenido — y esa misma columna lo
            # apretaba a 157px, forzando que "Por documento"
            # envuelva a una segunda línea sin necesidad. Medido
            # con el inspector (`?debug=1&diseno=1`) el
            # 2026-09-03.
            # 2026-09-04, a pedido ("el mismo selector de fecha
            # que la tarjeta de Ranking de proveedores, arriba,
            # alineado con los toggles y pegado a la derecha"): el
            # MISMO componente, no una copia — vive en
            # `_comun.py::selector_fecha_tarjeta` y escribe la
            # clave canónica del rango, así que mover la fecha acá
            # mueve también a los otros dos rankings. Es la tercera
            # puerta al mismo dato, que es lo correcto en una
            # página apilada: el rango es del REPORTE, no de la
            # vista (ver `_VISTAS_CON_FECHA_PROPIA`, más arriba —
            # este selector NO es de esa clase: no duplica el
            # widget de calendario de la franja, sólo escribe su
            # estado con `aplicar_atajo`).
            #
            # La granularidad entra por el hook `extra=`, así que
            # comparte el flex row con el trigger de fecha en vez
            # de gastar un renglón propio. Sin `titulo_html`: esta
            # tarjeta no lleva título (el nombre de la sección lo
            # pone el rail), así que la fila tiene dos items y el
            # `space-between` los manda a los dos bordes — pills a
            # la izquierda, fecha a la derecha.
            #
            # `extra` es un CALLABLE y no un widget ya dibujado
            # (en Streamlit el contenedor se elige ENTRANDO en
            # él), de ahí la cajita para sacar el valor: la
            # granularidad se necesita después, en el cuerpo.
            _gran_box = {}

            def _pills_gran():
                _gran_box["v"] = st.pills(
                    "Agrupar por",
                    ["Día", "Semana", "Mes", "Año", "Por documento"],
                    default="Semana", key="compras_sem_gran",
                    label_visibility="collapsed")

            if selector_fecha_tarjeta(
                    "cp_sem", "_cp_sem_atajo_pendiente",
                    extra=_pills_gran) is None:
                # El selector no dibuja NADA si la franja todavia
                # no publico su contexto, y con el se iria tambien
                # la granularidad, que es de esta vista y no de la
                # fecha. En ese caso se dibuja suelta.
                _pills_gran()
            gran = _gran_box.get("v") or "Semana"

            # Cambiar de granularidad invalida el foco: una clave
            # de "Semana" no existe en el espacio de "Mes". Mismo
            # guard que `compras_vol_prod_prev` en volatilidad.py
            # al cambiar de producto.
            if st.session_state.get("compras_sem_gran_prev") != gran:
                st.session_state["compras_sem_gran_prev"] = gran
                st.session_state["compras_sem_focus"] = None

            _fe   = pd.to_datetime(d[col_fecha], errors="coerce")
            _cnt  = (pd.to_numeric(d[col_cant], errors="coerce").fillna(0)
                    if col_cant else pd.Series(0, index=d.index))
            _pu   = (pd.to_numeric(d[col_punit], errors="coerce")
                    if col_punit else pd.Series(pd.NA, index=d.index))
            _prvs = d[col_prov].astype(str) if col_prov else pd.Series("", index=d.index)
            _docn = d[col_docu].astype(str) if col_docu else pd.Series("", index=d.index)

            dd = pd.DataFrame({
                "fecha": _fe, "prod": d[col_prod].astype(str), "prov": _prvs,
                "docn": _docn, "cant": _cnt, "punit": _pu, "valor": _valor,
            }).dropna(subset=["fecha"])

            # Clave de COMPRA: fecha+proveedor+documento, no el Nº
            # de documento solo (se repite entre proveedores que
            # reusan su propia numeración). Sin proveedor o
            # documento resuelto, cada FILA es su propia compra —
            # fallback defensivo, no bloquea la vista.
            _con_doc = bool(col_prov and col_docu)
            dd["compra"] = (
                dd["fecha"].dt.strftime("%Y-%m-%d") + "·" + dd["prov"] + "·" + dd["docn"]
                if _con_doc else dd.index.astype(str))

            if gran == "Por documento":
                dd["clave"] = dd["compra"]
                dd["lbl"] = dd["fecha"].dt.strftime("%d/%m")
            else:
                dd["clave"] = _periodo_serie(dd["fecha"], gran)
                dd["lbl"] = dd["clave"]

            _orden = (dd.drop_duplicates("clave")[["clave", "lbl"]]
                     .sort_values("clave"))
            _ord_claves = _orden["clave"].tolist()
            _ord_lbls = _orden["lbl"].tolist()

            # Con una sola barra, "evolución" no se ve —el
            # cuadro no miente, pero tampoco explica por qué
            # hay tan poco. La causa casi siempre es el rango
            # de fechas de la franja (arriba de TODO Compras,
            # no de esta tarjeta): su default "1º del mes ->
            # hoy" (app.py) se aplasta contra los bounds reales
            # del parquet cuando el dato todavía no llega a
            # "hoy" (mismo síntoma que arquitectura.md #293).
            # 2026-09-03, a pedido ("para indicarle al
            # usuario").
            if len(_ord_claves) == 1:
                st.caption("Sólo hay compras en un período "
                          "dentro del rango de fechas activo "
                          "(arriba) — ampliá el rango para ver "
                          "la evolución.")

            # UNA sola serie, no apilada por producto. La
            # apilada (top 8 + Otros) mostraba 9 colores por
            # barra que se pisaban con los puntos de "Compra
            # individual" encima; el desglose por producto vive
            # en el ranking completo de la sección Producto, un
            # scroll más arriba. 2026-09-03, a pedido ("la
            # apilada no es buena para esto").
            g = dd.groupby("clave", as_index=False)[["valor", "cant"]].sum()

            fig = go.Figure()
            fig.add_bar(
                x=g["clave"], y=g["valor"], name="Valor total",
                marker=dict(color=SERIE_PRINCIPAL),
                customdata=g["cant"],
                hovertemplate=("%{x}<br>Valor: S/ %{y:,.2f}"
                               "<br>Cantidad: %{customdata:,.1f}"
                               "<extra></extra>"),
            )

            # Puntos superpuestos: una COMPRA, no una línea de
            # producto — una orden de 5 líneas es un solo punto,
            # no cinco. Se omiten en "Por documento": ahí cada
            # barra YA es una compra y el punto caería pegado a
            # su propia punta, sin sumar información. 2026-09-03,
            # a pedido.
            if gran != "Por documento":
                docs_g = (dd.groupby(["clave", "compra"], as_index=False)
                         .agg(valor=("valor", "sum"), fecha=("fecha", "min"),
                              prov=("prov", "first")))
                _cd_docs = docs_g[["fecha", "prov"]].assign(
                    fecha=docs_g["fecha"].dt.strftime("%d/%m/%Y")).to_numpy()
                fig.add_scatter(
                    x=docs_g["clave"], y=docs_g["valor"], mode="markers",
                    name="Compra individual",
                    marker=dict(size=8, color=TEXTO_PRINCIPAL,
                                line=dict(color=BLANCO, width=1.5)),
                    customdata=_cd_docs,
                    hovertemplate=("Compra · %{customdata[1]}<br>%{customdata[0]}"
                                   "<br>Valor: S/ %{y:,.2f}<extra></extra>"),
                )

            _compras_layout(fig, alto=alturas.PROTAGONISTA)
            _tit_gran = {"Día": "por día", "Semana": "por semana",
                        "Mes": "por mes", "Año": "por año",
                        "Por documento": "por documento"}[gran]
            fig.update_layout(
                title=f"Compra {_tit_gran}",
                legend=dict(orientation="h", y=-0.22, x=0,
                            font=dict(size=10)),
            )
            fig.update_xaxes(type="category", categoryorder="array",
                             categoryarray=_ord_claves,
                             tickvals=_ord_claves, ticktext=_ord_lbls)

            # Clic en una barra o un punto -> foco de la tabla de
            # abajo. La key lleva el foco DE ANTES del clic: la
            # selección de on_select persiste mientras la key no
            # cambie, así que con key estática cada rerun re-lee
            # el mismo punto y togglea para siempre (parpadeo).
            # Mismo patrón que el click-drill de Por área/Por
            # familia — ver CLAUDE.md y arquitectura.md #76.
            _foco_antes = st.session_state.get("compras_sem_focus")
            evt = st.plotly_chart(
                fig, use_container_width=True, on_select="rerun",
                selection_mode="points",
                key=f"compras_g_semanal_{gran}_{_foco_antes or 'none'}")
            _pt = _first_point(evt)
            if _pt is not None:
                _clic = _pt.get("x")
                st.session_state["compras_sem_focus"] = (
                    None if _foco_antes == _clic else _clic)

            # El CAPTION es un elemento simple: un `if/else`
            # desnudo lo reconcilia bien (mismo conteo de
            # elementos en los dos branches, sólo cambia el
            # texto). La TABLA es otra cosa — medido en vivo
            # (2026-09-03): con la tabla DENTRO de un
            # `st.empty().container()` que en el branch "sin
            # foco" se rellena con sólo el caption, el
            # `st.dataframe` (glide-data-grid) sobrevivía
            # igual, visible y con datos del foco anterior.
            # `st.empty()` + `with hueco.container():` es la
            # cura para el HUÉRFANO documentada en
            # arquitectura.md regla #70, pero ese caso probado
            # (chips de bienvenida de `asistente.py`) nunca
            # REEMPLAZA el contenido por otra cosa — lo deja
            # sin llenar. Acá el hueco de la tabla se vacía con
            # `.empty()` EXPLÍCITO en el branch que no la
            # necesita, dedicado sólo a la tabla, igual que el
            # segundo caso de `asistente.py` (el hueco de
            # "Consultando tus datos…", que se limpia con
            # `hueco.empty()` antes de escribir la respuesta
            # aparte) — no se reutiliza el mismo hueco para el
            # caption.
            _focus = st.session_state.get("compras_sem_focus")
            _hueco_tabla = st.empty()
            if _focus in set(dd["clave"]):
                _det = dd[dd["clave"] == _focus].sort_values(
                    "valor", ascending=False)
                _et = _det["lbl"].iloc[0]
                st.caption(f"**{_et}** · {_det['compra'].nunique()} "
                          f"compras · S/ {_det['valor'].sum():,.2f}")
                tp = _det[["fecha", "prov", "prod", "cant", "punit",
                          "valor"]].rename(columns={
                    "fecha": "Fecha", "prov": "Proveedor",
                    "prod": "Producto", "cant": "Cantidad",
                    "punit": "P. unit.", "valor": "Valor"})
                fmts = {
                    "Fecha": lambda v: f"{v:%d/%m/%Y}",
                    "Cantidad": lambda v: f"{v:,.1f}",
                    "P. unit.": lambda v: ("—" if pd.isna(v)
                                           else f"S/ {v:,.2f}"),
                    "Valor": lambda v: f"S/ {v:,.2f}",
                }
                with _hueco_tabla.container():
                    st.dataframe(
                        tp.style.format(fmts).hide(axis="index"),
                        use_container_width=True, hide_index=True,
                        height=alturas.por_filas(len(tp), px_fila=34,
                                                 extra=60, minimo=0,
                                                 rol=alturas.MINI))
            else:
                st.caption("Tocá una barra o un punto para "
                          "ver el detalle.")
                _hueco_tabla.empty()

        else:
            st.info("No hay columnas suficientes para este gráfico.")
