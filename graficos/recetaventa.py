"""
graficos.recetaventa — la RECETA de un plato: la mitad de platos de Recetas.

Cada fila de recetaventa.parquet es un ÍTEM de un plato:
    Nomb Plato · Ins Rv · Cantidad · Total
    (plato)      (insumo)  (cant.)   (costo del insumo en el plato)

Desde el 2026-09-28 (regla #556) lo que vive acá es el panel de la receta
que se abre al elegir un producto en la Carta costeada
(`graficos/carta_costeada.py`): la receta con su simulador, la dona
Costo/Utilidad y el Sankey del plato. Y la resolución de columnas del
Panorama de compras, cuyo gráfico está en `graficos.recetas_comun` junto
con los otros que comparte con recetas base.

«Composición del plato» y «Costeo Receta Venta» fueron vistas propias hasta
ese día. Medido contra R2: la tabla de Composición era la Carta costeada
filtrada a los platos con receta —425 de 425 con el mismo precio, costo y %
al céntimo, y mismo grupo, subgrupo y última venta—, y Costeo sumaba el
mismo costo por plato sin descartar los inactivos (414 de sus 855 filas;
sus 15 primeros puestos, shots de whisky dados de baja). Lo único propio de
Composición era este panel, y ahora cuelga de la Carta. La historia de las
dos tablas —el ranking que fue gráfico y después tabla, el Sankey que se dio
de baja y volvió como pestaña, el radio «Medir por» que se sacó— está en
`arquitectura.md`, reglas #205, #236, #253, #451, #452 y #556.
"""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# El ÚNICO uso del paquete en el repo, y está acotado a este Sankey: es el
# único gráfico del proyecto que necesita clic y que
# `st.plotly_chart(on_select=)` no puede escuchar (regla #452).
#
# BAJO `try`, Y NO ES PARANOIA DE MANUAL: el paquete no se toca desde 2021
# y trae su propio frontend bundleado. Un `import` suelto arriba de este
# módulo lo convierte en requisito de ARRANQUE del reporte Recetas entero
# —`graficos/__init__.py` importa este módulo—, así que el día que su
# instalación falle en Cloud no se cae el Sankey: se cae la página, con un
# `ImportError` de una línea y sin nada que pushear (regla #357). Con el
# guard, lo que se pierde es el CLIC, y el Sankey vuelve a dibujarse con
# `st.plotly_chart` — que es exactamente lo que había antes.
try:
    from streamlit_plotly_events import plotly_events
except Exception:                                      # pragma: no cover
    plotly_events = None

from tema import (
    ACENTO, BLANCO, EXITO, GRIS_LINEA, PALETA_SERIES, TEXTO_PRINCIPAL,
)
from graficos import alturas
from graficos.base import _card, _resolver
from graficos.recetas_comun import (
    ARCHIVO_INVENTARIO, _hex_a_rgba, _panorama_compras, catalogo_insumos,
)


def _panorama_compras_venta(df_f, es_soles):
    _panorama_compras(
        df_f, es_soles, key_prefix="rv",
        col_cod_ins_cand=["COD INS", "Cod Ins"],
        col_contenedor_cand=["Nomb Plato", "Nombre Plato", "PLATO", "Plato"],
        col_valor_cand=["Total", "TOTAL", "Importe", "Costo Total"],
        col_cant_cand=["Cantidad", "CANTIDAD", "Cant"],
        col_activo_contenedor_cand=["ITEM VENTA ACTIVO", "Item Venta Activo"],
        col_activo_item_cand=["INS ACTIVO", "Ins Activo"],
        etiqueta_otros_contenedor="Otros platos",
        titulo_card="Productos comprados → platos que los usan",
        col_contenedor_out="Plato",
        etiqueta_contenedor_plural="platos activos",
        # Sin `nombre_vista_sankey`/`clave_seccion_sankey`: este dashboard ya
        # no tiene Sankey (dado de baja el 2026-08-30), así que
        # `_panorama_compras` deja el drill de insumo a lo ancho — mismo
        # criterio que `_panorama_compras_base`.
    )


# ─── El panel de la receta de un plato ─────────────────────────────────────
# Lo abre un clic en la Carta costeada (regla #556); hasta el 2026-09-28 lo
# abría la tabla de «Composición», que es de donde vienen estas medidas:
#
# P.VENTA SALON / CST SALON / %CST SALON son atributos del PLATO, no del
# ítem-insumo: los 850 platos del catálogo tienen un único valor de los tres
# por COD PLATO, repetido en cada fila-insumo (regla #205). Y CST SALON ==
# suma de TOTAL de los ítems de ese plato, sin filtrar por INS ACTIVO: la
# receta de este panel suma lo mismo que el costo de la fila de la Carta
# (medido de nuevo el 2026-09-28: 424 de 425; la excepción es un shot cuyo
# único insumo trae TOTAL 0).
#
# El insumo se lee de INS RV, no de ITEM RV: ITEM RV es el número de LÍNEA
# dentro de la receta (001, 002…), no una identidad de insumo — el mismo
# COD INS aparece como "001" en un plato y "019" en otro. INS RV es el texto
# descriptivo, estable 1:1 contra COD INS.
#
# El panel son dos tarjetas: la receta (con su simulador, abajo) y, al
# lado, la dona Costo/Utilidad y el Sankey plato→insumo del plato en foco.


# ─── El simulador: "¿y si...?" sobre la receta del plato en foco ───────────
# 2026-09-17, a pedido: «hay alguna forma de darle alguna interacción o
# edición, por ejemplo que cambie si cambio algún número o agrego algún
# producto».
#
# LO QUE NO HACE, y conviene que se lea antes que lo que sí: NO escribe en
# recetaventa.parquet. Ese parquet lo genera el pipeline ETL desde el SQL
# de Inforest, fuera de este repo, y la app nunca escribe parquets fuente —
# el único camino de vuelta que existe hoy es la PROPUESTA en JSON que
# guarda `formulario_receta.py` (`_recetas_propuestas/` en R2). Esto es un
# borrador de sesión: vive en `st.session_state`, se pierde al recargar y
# no sale de la pantalla de quien lo está mirando. El rótulo de la tarjeta
# lo dice mientras está prendido, porque una tabla editable que se parece a
# la real y no lo es sería la peor de las mentiras.
#
# EL MODELO DE EDICIÓN es Cantidad × Precio unitario, y el precio unitario
# NO viene del parquet: se despeja de `TOTAL / CANTIDAD`. Eso sólo es
# seguro si ninguna línea con cantidad 0 tiene costo — medido contra R2 el
# 2026-09-17 sobre las 2.605 filas: 19 tienen `CANTIDAD == 0` y las 19
# tienen `TOTAL == 0`, así que despejar no le borra el costo a nadie. Si
# algún día aparece una con cantidad 0 y costo > 0, este despeje la pone en
# cero sin avisar.
#
# ES EL MISMO IDIOMA QUE `formulario_receta.py::_tabla_lineas`, a propósito
# y hasta en los detalles: mismas dos columnas editables, misma columna
# calculada deshabilitada, mismo `Quitar` con casilla y botón. Se comparte
# el catálogo de insumos (`recetas_comun.catalogo_insumos`) para que
# "agregar Sal De Mesa" signifique lo mismo en los dos sitios — ver el
# comentario de esa función.
#
# `num_rows="fixed"` Y NO `"dynamic"`, que parecía el atajo para agregar y
# borrar filas sin botones: `st.data_editor` guarda su delta contra el
# frame que se le PASÓ, y como acá el frame se reconstruye en cada pasada
# desde `session_state`, los `added_rows` del delta se re-aplican sobre una
# lista que ya los tiene y la fila se duplica. Las ediciones de celda se
# salvan de eso sólo porque son idempotentes (fijan el mismo valor). Por
# eso toda mutación que NO venga del editor —agregar del catálogo, quitar,
# volver al original— vacía la key del editor antes de redibujar.
_K_SIM = "rv_comp_sim"
"""`{cod_plato: [{Insumo, Cantidad, Precio}]}` — el borrador por plato. Se
guarda por plato y no uno solo global para que ir a mirar otro plato y
volver no borre lo que estabas probando."""

_K_SIM_ON = "rv_comp_sim_on"


def _precios_y_pesos(r):
    """Completa una receta con `Precio` unitario y `%` del costo total.

    `Precio` sale de `Costo / Cantidad` (ver el comentario de arriba sobre
    por qué es seguro), y `Costo` se recalcula como `Cantidad * Precio` en
    el camino de vuelta — no al revés."""
    r = r.copy()
    cant = pd.to_numeric(r["Cantidad"], errors="coerce").fillna(0.0)
    costo = pd.to_numeric(r["Costo"], errors="coerce").fillna(0.0)
    r["Cantidad"] = cant
    r["Costo"] = costo
    r["Precio"] = (costo / cant.where(cant > 0)).fillna(0.0)
    total = costo.sum() or 1.0
    r["%"] = costo / total * 100
    return r


def _receta_original(df_f, foco, col_cod_plato, col_ins, col_cant, col_total):
    """La receta tal como está en el parquet. `None` si faltan columnas."""
    if not (col_ins and col_total):
        return None
    items = df_f[df_f[col_cod_plato].astype(str) == foco].reset_index(drop=True)
    r = pd.DataFrame({
        "Insumo": items[col_ins].astype(str),
        "Cantidad": (pd.to_numeric(items[col_cant], errors="coerce").fillna(0.0)
                     if col_cant else 0.0),
        "Costo": pd.to_numeric(items[col_total], errors="coerce").fillna(0.0),
    })
    r = _precios_y_pesos(r)
    return r.sort_values("Costo", ascending=False).reset_index(drop=True)


def _receta_simulada(lineas):
    """De las líneas del borrador al mismo frame que `_receta_original`.

    Acá el costo es CONSECUENCIA (`Cantidad * Precio`), que es lo que hace
    que mover un número mueva el Sankey y la dona.

    **SIN ORDENAR, y es lo único que hay que respetar de esta función.**
    El frame sale en el orden de `lineas` porque ESE es el orden en que lo
    ve el editor, y la vuelta (`editado.iloc[i]` → `lineas[i]`) empareja por
    POSICIÓN. Con un `sort_values("Costo")` acá —que es como nació— las dos
    listas se despegan en cuanto un costo cambia de puesto: editar la
    primera fila de la grilla escribía en otro insumo, y lo mismo hacía
    «Quitar». Medido el 2026-09-17 con un editor sembrado: duplicar la
    cantidad de la fila 0 y después bajarle el precio dejaba el precio
    aplicado a un insumo distinto, y el costo total quieto. Ordenar es
    trabajo de QUIEN DIBUJA (ver `_panel_receta`, que le pasa una copia
    ordenada al Sankey y a la dona)."""
    if not lineas:
        return pd.DataFrame(columns=["Insumo", "Cantidad", "Costo", "Precio", "%"])
    r = pd.DataFrame(lineas)
    r["Costo"] = (pd.to_numeric(r["Cantidad"], errors="coerce").fillna(0.0)
                  * pd.to_numeric(r["Precio"], errors="coerce").fillna(0.0))
    return _precios_y_pesos(r).reset_index(drop=True)


def _sim_borradores():
    return st.session_state.setdefault(_K_SIM, {})


def _sim_key_editor(foco):
    return f"rv_comp_sim_editor_{foco}"


def _sim_reset(foco):
    """Callback de «Volver al original»: borra el borrador Y la key del
    editor. Sin lo segundo, el delta del `data_editor` vuelve a aplicarse
    sobre la receta recién restaurada y el reset no se ve."""
    _sim_borradores().pop(foco, None)
    st.session_state.pop(_sim_key_editor(foco), None)


def _sim_agregar(foco, cod_sel, catalogo):
    """Callback de «Agregar»: mete un insumo del catálogo de almacén al
    borrador, con su precio promedio como precio unitario y cantidad 1.

    Cantidad 1 y no 0 a propósito: con 0 el insumo entra con costo 0, o sea
    no cambia nada, y el gesto se lee como que no funcionó."""
    if not cod_sel:
        return
    fila = catalogo[catalogo["cod"] == cod_sel]
    if fila.empty:
        return
    lineas = _sim_borradores().get(foco)
    if lineas is None:
        return
    nombre = str(fila["nombre"].iloc[0])
    if any(l["Insumo"] == nombre for l in lineas):
        st.session_state["rv_comp_sim_aviso"] = f"«{nombre}» ya está en la receta."
        return
    lineas.append({"Insumo": nombre, "Cantidad": 1.0,
                   "Precio": float(fila["precio"].iloc[0])})
    st.session_state.pop(_sim_key_editor(foco), None)
    st.session_state["rv_comp_sim_aviso"] = None


def _sim_escalar(foco, insumo, factor):
    """Callback de los atajos −10 %/+10 % del Sankey: mueve la CANTIDAD,
    no el precio.

    Es lo que se pregunta mirando un Sankey — «¿y si le pongo menos?»—,
    y además es la cuenta que el borrador puede deshacer sin perder nada:
    el precio unitario viene despejado del parquet y pisarlo lo borra."""
    lineas = _sim_borradores().get(foco)
    if lineas is None:
        return
    for linea in lineas:
        if linea["Insumo"] == insumo:
            linea["Cantidad"] = float(linea["Cantidad"]) * factor
            break
    st.session_state.pop(_sim_key_editor(foco), None)


def _sim_quitar_insumo(foco, insumo):
    """Callback de «Quitar» del Sankey — por NOMBRE, no por posición: el
    Sankey dibuja sólo los insumos con costo > 0 y ordenados, así que su
    índice no es el de `lineas` (la trampa de la #451, del otro lado)."""
    lineas = _sim_borradores().get(foco)
    if lineas is None:
        return
    _sim_borradores()[foco] = [l for l in lineas if l["Insumo"] != insumo]
    st.session_state.pop(_sim_key_editor(foco), None)
    st.session_state[_K_SANKEY_FOCO] = None


def _sim_quitar(foco, marcadas):
    lineas = _sim_borradores().get(foco)
    if lineas is None or not marcadas:
        return
    _sim_borradores()[foco] = [l for i, l in enumerate(lineas) if i not in marcadas]
    st.session_state.pop(_sim_key_editor(foco), None)


def _panel_receta(df_f, foco, nombre_foco, col_cod_plato, col_ins, col_cant,
                  col_total):
    """La tarjeta de receta del plato en foco, en sus dos modos.

    Devuelve `(r, costo_sim)`: la receta VIGENTE —la del parquet o la del
    borrador— y el costo simulado, o `None` si no se esta simulando. Las
    dos las consumen el Sankey y la dona de al lado, que por eso siguen al
    editor sin saber que existe.

    El modo lectura es el de siempre. El de simulacion cambia tres cosas y
    ninguna es cosmetica: el rotulo avisa que es un borrador, la tabla pasa
    a `st.data_editor`, y aparecen el buscador del catalogo de almacen y el
    boton de volver.
    """
    orig = _receta_original(df_f, foco, col_cod_plato, col_ins, col_cant,
                            col_total)
    borradores = _sim_borradores()
    simulando = bool(st.session_state.get(_K_SIM_ON)) and orig is not None

    rotulo = f"Receta \u00b7 {nombre_foco}" if nombre_foco else "Receta"
    if simulando:
        rotulo += " \u00b7 borrador, no se guarda"

    with _card("rv_comp_receta", rotulo):
        if orig is None:
            st.info("No se reconoci\u00f3 la columna de insumo (INS RV) o "
                    "de costo (TOTAL) para mostrar la receta.")
            return None, None

        # El toggle se dibuja SIEMPRE, tambien en modo lectura: un widget
        # que deja de renderizarse pierde su estado (CLAUDE.md § Streamlit),
        # y este es justamente el que decide si el resto se dibuja.
        c_tog, c_vol = st.columns([2, 3], gap="small")
        with c_tog:
            st.toggle("Simular", key=_K_SIM_ON,
                      help="Cambi\u00e1 cantidades y precios para ver c\u00f3mo se "
                           "mueven el costo y el margen. Es un borrador de "
                           "esta sesi\u00f3n: no toca los datos ni se guarda.")
        if not simulando:
            st.dataframe(
                orig[["Insumo", "Cantidad", "Costo", "%"]],
                hide_index=True, use_container_width=True,
                height=alturas.MINI,
                column_config={
                    "Cantidad": st.column_config.NumberColumn(format="%.3f"),
                    "Costo": st.column_config.NumberColumn(format="S/ %.2f"),
                    "%": st.column_config.ProgressColumn(
                        format="%.1f%%", min_value=0, max_value=100),
                },
            )
            return orig, None

        # El borrador nace COPIANDO la receta real la primera vez que se
        # prende el toggle para este plato.
        if foco not in borradores:
            borradores[foco] = [
                {"Insumo": str(f["Insumo"]), "Cantidad": float(f["Cantidad"]),
                 "Precio": float(f["Precio"])}
                for _, f in orig.iterrows()
            ]
        lineas = borradores[foco]

        with c_vol:
            # Sin `use_container_width`: con el ancho del contenedor se
            # estiraba a 3/5 de la fila, y un bot\u00f3n de deshacer con ese
            # peso se lee como la acci\u00f3n principal de la tarjeta \u2014 que es
            # justo lo que no es.
            st.button("\u21ba Volver al original",
                      key=f"rv_comp_sim_reset_{foco}",
                      on_click=_sim_reset, args=(foco,))

        r = _receta_simulada(lineas)
        editor_key = _sim_key_editor(foco)
        df_edit = r[["Insumo", "Cantidad", "Precio", "Costo"]].copy()
        df_edit.insert(0, "Quitar", False)
        editado = st.data_editor(
            df_edit, key=editor_key, hide_index=True,
            use_container_width=True, height=alturas.MINI,
            disabled=["Insumo", "Costo"],
            column_config={
                "Quitar": st.column_config.CheckboxColumn(width="small"),
                "Cantidad": st.column_config.NumberColumn(
                    min_value=0.0, step=0.01, format="%.3f"),
                "Precio": st.column_config.NumberColumn(
                    "Precio unit.", min_value=0.0, step=0.01,
                    format="S/ %.4f"),
                # DESHABILITADA y por lo tanto con UNA pasada de atraso: lo
                # que se ve aca es `Cantidad * Precio` de la corrida
                # anterior, porque el frame se arma antes de leer lo
                # editado. El Sankey y la dona NO tienen ese atraso -- salen
                # de `lineas`, que si se actualiza mas abajo. Mismo trato
                # que el «Subtotal» de `formulario_receta.py`.
                "Costo": st.column_config.NumberColumn(format="S/ %.2f"),
            },
        )

        # Lo editado vuelve al borrador EN ESTA MISMA pasada: el editor ya
        # disparo el rerun que llego hasta aca, asi que el Sankey de al lado
        # dibuja lo nuevo sin un `st.rerun()` de mas -- que ademas seria
        # peligroso, porque este panel vive dentro del fragment de
        # `seccion_perezosa` y un rerun al tope de un fragment le borra el
        # estado a sus propios widgets (regla #373).
        for i, linea in enumerate(lineas):
            fila = editado.iloc[i]
            cant = fila["Cantidad"]
            prec = fila["Precio"]
            linea["Cantidad"] = 0.0 if pd.isna(cant) else float(cant)
            linea["Precio"] = 0.0 if pd.isna(prec) else float(prec)

        marcadas = {i for i, v in enumerate(editado["Quitar"]) if bool(v)}
        catalogo = catalogo_insumos()

        c_add, c_btn, c_quit = st.columns([5, 2, 2], gap="small")
        with c_add:
            if catalogo is None or catalogo.empty:
                st.caption("No se pudo leer el cat\u00e1logo de almac\u00e9n "
                           f"({ARCHIVO_INVENTARIO}): no se pueden agregar "
                           "insumos nuevos.")
                cod_sel = None
            else:
                etiquetas = dict(zip(
                    catalogo["cod"],
                    catalogo["nombre"] + "  \u00b7  S/ "
                    + catalogo["precio"].map(lambda v: f"{v:,.4f}")))
                cod_sel = st.selectbox(
                    "Agregar insumo", catalogo["cod"].tolist(), index=None,
                    format_func=lambda c: etiquetas.get(c, c),
                    placeholder="Busc\u00e1 un insumo de almac\u00e9n\u2026",
                    key=f"rv_comp_sim_add_{foco}",
                    label_visibility="collapsed")
        with c_btn:
            st.button("Agregar", key=f"rv_comp_sim_addbtn_{foco}",
                      disabled=cod_sel is None, use_container_width=True,
                      on_click=_sim_agregar, args=(foco, cod_sel, catalogo))
        with c_quit:
            st.button(f"Quitar ({len(marcadas)})",
                      key=f"rv_comp_sim_quitar_{foco}",
                      disabled=not marcadas, use_container_width=True,
                      on_click=_sim_quitar, args=(foco, marcadas))

        aviso = st.session_state.get("rv_comp_sim_aviso")
        if aviso:
            st.caption(f"\u26a0\ufe0f {aviso}")

        r = _receta_simulada(lineas)
        costo_sim = float(r["Costo"].sum())
        costo_real = float(orig["Costo"].sum())
        delta = costo_sim - costo_real
        pct = (delta / costo_real * 100) if costo_real else 0.0
        signo = "+" if delta >= 0 else "\u2212"
        st.caption(
            f"Costo del borrador **S/ {costo_sim:,.2f}** \u00b7 "
            f"real S/ {costo_real:,.2f} \u00b7 "
            f"{signo}S/ {abs(delta):,.2f} ({signo}{abs(pct):.1f}%)"
        )
        # ORDENADA s\u00f3lo ac\u00e1, para el Sankey y la dona. El editor la vio sin
        # ordenar a prop\u00f3sito (ver `_receta_simulada`): si las filas se
        # reacomodaran a cada tecla, el `editado.iloc[i]` de arriba dejar\u00eda
        # de nombrar la misma l\u00ednea y editar una escribir\u00eda en otra.
        return r.sort_values("Costo", ascending=False).reset_index(drop=True), costo_sim


def _dib_torta_costo_utilidad(neto, costo, pct, foco, costo_sim=None):
    """Mini donut Costo/Utilidad del plato en foco: el costo contra
    (precio neto − costo). Si el costo supera al precio neto —pasa de
    verdad: arquitectura.md regla #205 mide bebidas premium con %Costo de
    300–950%, porque el costo es la BOTELLA entera y el precio la COPA— la
    Utilidad da negativa y un donut no puede dibujar eso (una porción no
    puede ser "menos que nada"): se avisa el monto en vez de forzar un
    gráfico que mentiría.

    `neto`, `costo` y `pct` (en %) son los de la fila de la Carta.
    `costo_sim`: el costo del BORRADOR del simulador, cuando hay uno. El
    %Costo se RECALCULA contra el precio neto en vez de usar `pct` — si
    no, mover una cantidad cambiaba el tamaño de la porción y dejaba el
    número del medio quieto, que es justo la contradicción que el velo de
    la app existe para evitar."""
    neto = float(neto or 0.0)
    if costo_sim is None:
        costo = float(costo or 0.0)
        pct = float(pct or 0.0)
    else:
        costo = float(costo_sim)
        pct = (costo / neto * 100) if neto else 0.0
    utilidad = neto - costo
    if costo <= 0 and utilidad <= 0:
        st.info("Sin costo ni precio para graficar.")
        return
    if utilidad < 0:
        st.warning(
            f"Se vende a pérdida: el costo (S/ {costo:,.2f}) supera el "
            f"precio neto (S/ {neto:,.2f}) en S/ {abs(utilidad):,.2f}."
        )
    # `sort=False`: mantiene el orden Costo/Utilidad de `labels` —
    # Plotly, por defecto, reordena las porciones por valor descendente,
    # lo que dejaría el color de cada una saltando de plato en plato.
    fig = go.Figure(go.Pie(
        labels=["Costo", "Utilidad"],
        values=[costo, max(utilidad, 0.0)],
        hole=0.55, sort=False,
        marker=dict(colors=[ACENTO, EXITO]),
        textinfo="label+percent",
        hovertemplate="%{label}: S/ %{value:,.2f}<extra></extra>",
    ))
    fig.add_annotation(
        text=f"{pct:.0f}%<br>costo", showarrow=False,
        font=dict(size=13, color=TEXTO_PRINCIPAL, family="DM Sans, sans-serif"),
    )
    fig.update_layout(
        height=alturas.MINI,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=11),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"rv_comp_torta_{foco}")


# ─── El Sankey, que acá también es un CONTROL ──────────────────────
# 2026-09-17. `st.plotly_chart(on_select=...)` NO VE un Sankey — medido, y
# no es que el evento no exista: Plotly SÍ emite `plotly_click` sobre un
# enlace, y sobre un nodo también si el `arrangement` no lo deja arrastrar.
# Lo que no pasa es la traducción a selección de Streamlit, que se arma de
# `plotly_selected`/`plotly_deselect` y un Sankey no tiene selección. Se
# verificó con un `go.Bar` de control en la misma página, que sí llegó.
# Detalle en la regla #452.
#
# De ahí `streamlit-plotly-events`, que trae su propio frontend. Tres cosas
# suyas que hay que respetar:
#
#   1. `arrangement="fixed"` Y NO `"snap"`. Con snap el nodo es
#      ARRASTRABLE y el drag se come el clic: medido, cero eventos sobre
#      los nodos y las etiquetas cambiadas de sitio. De paso se arregla algo
#      que ya molestaba — hasta hoy, un clic en una barrita la movía.
#   2. El payload es `{curveNumber, pointNumber}` y NADA MÁS: no dice si se
#      clickeó un nodo o un enlace, y el índice de uno no es el del otro.
#      Por eso el nodo del PLATO va ÚLTIMO y los insumos ocupan 0..N-1: así
#      `link j` apunta a `node j` y las dos lecturas nombran al mismo
#      insumo. Verificado clickeando el nodo y su cinta: los dos devuelven
#      el mismo número.
#   3. Re-emite el ÚLTIMO clic en CADA rerun (la trampa de la #399). Por eso
#      la key lleva un contador que sube cada vez que se procesa uno.
_K_SANKEY_FOCO = "rv_comp_sankey_foco"
_K_SANKEY_NCLIC = "rv_comp_sankey_nclic"


def _indice_clickeado(bruto):
    """El índice del punto clickeado en el Sankey, o `None` si no hubo clic.

    **LO QUE `plotly_events` DEJA EN `session_state` ES UN STRING JSON, NO
    UNA LISTA.** El paquete hace el `loads()` recién en su valor de
    retorno; lo que guarda bajo la key es lo crudo, y su `default` es el
    string `"[]"`. O sea que un `if ev: ev[0].get(...)` —que es lo natural
    de escribir— revienta con `AttributeError` apenas se carga la vista:
    `"[]"` es un string NO vacío, así que entra al `if`, y `ev[0]` es el
    carácter `'['`. Se veía leyendo la fuente del paquete, no probando el
    camino feliz.

    Acepta las dos formas igual (string o lista ya parseada) para no
    depender de un detalle interno de un paquete sin mantenimiento desde
    2021."""
    if isinstance(bruto, str):
        try:
            bruto = json.loads(bruto)
        except ValueError:
            return None
    if not bruto:
        return None
    try:
        return int(bruto[0]["pointNumber"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def _dib_sankey_insumo_costo(r, nombre_foco, foco, simulando=False):
    """Mini Sankey plato→insumo del plato en foco, ancho del flujo
    proporcional al costo del insumo — mismo cálculo que tenía
    `_sankey_contenedor` (recetas_comun.py, borrada el 2026-08-30 al
    quedarse sin llamadores), reescrito acá a tamaño MINI: ya no es una
    vista propia, es una pestaña de este panel.

    Y desde el 2026-09-17 es además un CONTROL: clic en un insumo (su
    barrita o su cinta) lo enfoca, reclic lo suelta, y con el simulador
    prendido el foco trae tres atajos — −10 %, +10 % y quitar."""
    if r is None:
        st.info("No se reconoció la columna de insumo o de costo para "
               "graficar.")
        return
    r_pos = r[r["Costo"] > 0]
    if r_pos.empty:
        st.info("Este plato no tiene insumos con costo positivo para graficar.")
        return
    insumos = r_pos["Insumo"].tolist()
    valores = [float(v) for v in r_pos["Costo"].tolist()]
    n = len(insumos)

    # EL CLIC SE LEE ANTES DE DIBUJAR, con el contador en la key: el
    # componente devuelve el último clic en cada pasada, así que leerlo
    # después de dibujar re-procesaría el mismo gesto para siempre.
    nclic = st.session_state.get(_K_SANKEY_NCLIC, 0)
    key_sankey = f"rv_comp_sankey_{foco}_{nclic}"
    idx = _indice_clickeado(st.session_state.get(key_sankey))
    if idx is not None:
        if 0 <= idx < n:
            elegido = insumos[idx]
            # Toggle: reclic en el mismo insumo lo suelta.
            st.session_state[_K_SANKEY_FOCO] = (
                None if st.session_state.get(_K_SANKEY_FOCO) == elegido
                else elegido)
        else:
            # El nodo del plato (índice n) no es un insumo: suelta el foco.
            st.session_state[_K_SANKEY_FOCO] = None
        st.session_state[_K_SANKEY_NCLIC] = nclic + 1
        nclic += 1
        key_sankey = f"rv_comp_sankey_{foco}_{nclic}"

    en_foco = st.session_state.get(_K_SANKEY_FOCO)
    if en_foco not in insumos:
        en_foco = None

    # EL PLATO VA DE ÚLTIMO — ver el comentario de arriba, punto 2.
    labels = insumos + [nombre_foco or "Plato"]
    base = [PALETA_SERIES[i % len(PALETA_SERIES)] for i in range(n)]
    if en_foco is None:
        node_colors = base + [ACENTO]
        link_colors = [_hex_a_rgba(c, 0.45) for c in base]
    else:
        # Con algo en foco, el resto se apaga en vez de taparse: lo que
        # importa es la comparación, no esconder los otros.
        node_colors = [c if insumos[i] == en_foco else GRIS_LINEA
                       for i, c in enumerate(base)] + [ACENTO]
        link_colors = [_hex_a_rgba(c, 0.75 if insumos[i] == en_foco else 0.12)
                       for i, c in enumerate(base)]

    fig = go.Figure(go.Sankey(
        arrangement="fixed",
        node=dict(
            label=labels, color=node_colors, pad=12, thickness=12,
            line=dict(color=BLANCO, width=0.5),
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=[n] * n, target=list(range(n)),
            value=valores, color=link_colors,
            hovertemplate="%{target.label}<br>S/ %{value:,.2f}<extra></extra>",
        ),
    ))
    fig.update_layout(
        height=alturas.MINI,
        margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=TEXTO_PRINCIPAL, size=10),
    )
    if plotly_events is None:
        # Sin el componente, el Sankey es el de siempre: se ve igual y no
        # escucha. Se avisa en vez de dejar un gráfico que no responde a un
        # clic que el pie invita a dar.
        st.plotly_chart(fig, use_container_width=True, key=key_sankey)
        st.caption("El clic sobre el Sankey no está disponible "
                   "(falta `streamlit-plotly-events`).")
        return

    plotly_events(fig, click_event=True, hover_event=False, select_event=False,
                  override_height=alturas.MINI, key=key_sankey)

    if en_foco is None:
        st.caption("Clic en un insumo para enfocarlo."
                   + ("" if simulando else
                      " Con **Simular** prendido, además se puede ajustar "
                      "desde acá."))
        return

    fila = r_pos[r_pos["Insumo"] == en_foco].iloc[0]
    st.caption(f"**{en_foco}** · S/ {float(fila['Costo']):,.2f} · "
               f"{float(fila['%']):.1f} % del costo")
    if not simulando:
        return

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.button("−10 %", key=f"rv_comp_sk_menos_{foco}_{nclic}",
                  use_container_width=True,
                  on_click=_sim_escalar, args=(foco, en_foco, 0.9))
    with c2:
        st.button("+10 %", key=f"rv_comp_sk_mas_{foco}_{nclic}",
                  use_container_width=True,
                  on_click=_sim_escalar, args=(foco, en_foco, 1.1))
    with c3:
        st.button("Quitar", key=f"rv_comp_sk_quitar_{foco}_{nclic}",
                  use_container_width=True,
                  on_click=_sim_quitar_insumo, args=(foco, en_foco))


# ─── Lo que usa la Carta costeada ──────────────────────────────────────────
def columnas_receta(df):
    """Las columnas de recetaventa.parquet que usa el panel de la receta,
    resueltas contra `df` (`None` la que falte)."""
    if df is None:
        return {"cod": None, "ins": None, "cant": None, "total": None}
    return {
        "cod": _resolver(df, ["COD PLATO", "Cod Plato"]),
        "ins": _resolver(df, ["INS RV", "Ins Rv"]),
        "cant": _resolver(df, ["CANTIDAD", "Cantidad"]),
        "total": _resolver(df, ["TOTAL", "Total"]),
    }


def receta_del_plato(df_rv, cod, nombre):
    """La tarjeta de la receta del plato `cod`, con su simulador.

    Devuelve `(r, costo_sim)` como `_panel_receta`: la receta vigente —la
    del parquet o la del borrador— y el costo del borrador, o `None` si no
    se está simulando. Las dos las usan la dona y el Sankey de al lado."""
    c = columnas_receta(df_rv)
    if not c["cod"]:
        with _card("rv_comp_receta", "Receta"):
            st.info("No se pudo leer recetaventa.parquet para mostrar la "
                    "receta.")
        return None, None
    return _panel_receta(df_rv, str(cod), nombre, c["cod"], c["ins"],
                         c["cant"], c["total"])
