"""
graficos.recetaventa — la mitad de PLATOS del dashboard de Recetas.

Cada fila de recetaventa.parquet es un ÍTEM de un plato:
    Nomb Plato · Item Rv · Cantidad · Total
    (plato)      (insumo)  (cant.)    (costo del insumo en el plato)

Este módulo es la capa FINA de Receta Venta: resuelve las columnas reales
del parquet y llama a los gráficos compartidos de `graficos.recetas_comun`
(Ingredientes clave, Panorama de compras) — cada uno vive ahí UNA sola vez,
junto con la versión de `recetabase.py` (el mismo tipo de dato: un BOM
plato→insumos vs. receta base→insumos). Desde 2026-08-13 Receta Base y
Receta Venta comparten ítem de nav ("Recetas") y un chip Base/Venta arriba
del rail — ver `_chip_fuente` en recetas_comun.py (retirado 2026-09-22, ver ahí) y `arquitectura.md` §
Unificación Recetas.

"Composición" DEJÓ de ser compartida el 2026-08-24: acá es
`_tabla_composicion_venta`, una tabla propia (no una dona de un plato) con
columnas — Grupo/Subgrupo/P.VENTA SALON/CST SALON/%CST SALON — que no
existen en recetabase.parquet. El chip Base/Venta/Nueva no se muestra en
esta vista (no hay a qué "Base" equivalente navegar). Ver docstring de la
función.

Y desde el 2026-08-28, Composición pasó a ser SOLO de Receta Venta:
Receta Base se quedó con Ranking (hoy Costeo, ver más abajo), Insumos
clave, Panorama y Tabla (regla #236).

Y desde el 2026-08-30, "Ranking de platos" se renombra a "Costeo Receta
Venta" y deja el gráfico de barras horizontal por una tabla AgGrid propia
(`_tabla_costeo_venta`, más abajo) — a pedido: "en lugar de un gráfico,
una tabla tipo ranking, ordenada por costo, algo así como el que tengo
para compras". Mismo lenguaje visual que el Ranking de Proveedores de
Compras (barra como fondo de celda vía `linear-gradient`, fila TOTAL
fijada abajo) y misma agregación que el gráfico que reemplaza (suma de
costo/cantidad por plato, sin filtrar por activo). Sigue sin ser un quinto
compartido en `recetas_comun.py`: sólo Receta Venta pidió el cambio, así
que Receta Base se queda con el gráfico (`_ranking_contenedores`), que
conserva el nombre "Ranking".

Y el mismo 2026-08-30, más tarde, el Sankey se da de baja de Receta Venta
a pedido — con él se van el selector "Plato" (existía sólo para
alimentarlo, nada más lo usaba) y el drill "Abrir Sankey →" del Panorama
de compras (era sólo un atajo hacia esta vista). `_sankey_contenedor` se
BORRA de `recetas_comun.py`: Receta Base ya no lo llamaba desde el #236,
así que este dashboard era su último llamador — mismo criterio que se
aplicó con `_composicion_contenedor` esa vez (ver el docstring de
recetas_comun.py). El Panorama de compras conserva su PROPIO Sankey
(Producto→Plato, `_fig_panorama_sankey`): es un gráfico distinto, con otro
propósito, no tocado por este cambio.

Y una tercera vez el mismo 2026-08-30: el radio "Medir por" (Costo/
Cantidad, `rv_metrica`) se saca a pedido — "por defecto siempre debe ser
por costo". `es_soles` queda fijo (con el mismo fallback a Cantidad de
siempre si no hubiera columna de costo), sin widget que lo cambie. Afecta
a los tres lectores de `es_soles`: Costeo Receta Venta, Ingredientes clave
y Panorama de compras pasan a mostrarse siempre en soles. Receta Base
conserva su propio radio (`rb_metrica`) — este dashboard es el único que
pidió sacarlo.

**Dejó de ser un dashboard propio el 2026-09-04.** Hasta entonces «Receta
Venta» era un reporte aparte, con su rail, su pila de 5 secciones y su
punto de entrada `renderizar_graficos_recetaventa`, al que se llegaba por
un chip Base/Venta. Hoy sus cinco vistas comparten página con las cuatro
de recetas base — ver `graficos/recetas.py`, que dibuja la pila y explica
por qué se fusionaron. Con el entry point se fueron sus
`_RAIL_CATEGORIAS` y su `_PILA`.

Lo que queda acá es lo PROPIO de este parquet: las dos tablas que no
tienen equivalente en recetabase.parquet (`_tabla_composicion_venta`,
`_tabla_costeo_venta`) y la resolución de columnas del Panorama
(`_panorama_compras_venta`). Los gráficos compartidos con la mitad de
recetas base siguen viniendo de `graficos.recetas_comun`.
"""

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from st_aggrid import AgGrid, JsCode
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
    ACENTO, ACENTO_TEXTO_OSCURO, ADVERTENCIA, BLANCO, ERROR, EXITO,
    GRIS_LINEA, LAVANDA_CHIP, PALETA_SERIES, TEXTO_PRINCIPAL,
)
# El LOOK de una tabla-ranking del repo, en bloque. Nació en el Ranking de
# proveedores de Compras, cruzó a los tres paneles del drill de Producto
# (2026-09-11), a Inventario (2026-09-13) y a `drill_tablas.py`; el
# 2026-09-17 llega a las dos tablas de Receta Venta, que eran de los
# últimos AgGrid del repo dibujados con el `theme="streamlit"` tal como
# sale de fábrica. Los cuatro nombres viajan JUNTOS y no se eligen por
# separado: el alto de fila sin el cuerpo de 11.5px aprieta el texto
# contra las líneas (docstring de `ALTO_FILA_RANK`), y la regla #404
# cuenta lo que pasa cuando se copia el componente y no el look.
from graficos.compras._comun import (
    ALTO_FILA_RANK, ALTO_HEADER_RANK, CROMO_GRID_RANK,
)
from graficos.compras._css_proveedor import CSS_RANKING_GRID
from graficos import alturas
from graficos.base import _card, _resolver
from graficos.recetas_comun import (
    ARCHIVO_INVENTARIO, _activo, _hex_a_rgba, _panorama_compras,
    catalogo_insumos,
)

# Umbral de %Costo salón para el semáforo de la barra de progreso de
# Composición (más abajo): mismo criterio que ya usa formulario_receta.py
# para juzgar el % de costo de una receta nueva (🟢/🟠/🔴) — no vive en un
# módulo compartido porque son dos herramientas separadas (ésta lee
# recetaventa.parquet, aquélla arma una receta a mano) que coinciden en la
# misma referencia de negocio, no en código que debieran compartir.
_UMBRAL_COSTO_OK = 30
_UMBRAL_COSTO_WARN = 35


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


# ─── Composición: tabla de platos + drill a su receta ──────────────────────
# 2026-08-24, a pedido: reemplaza la dona de UN plato (`_composicion_
# contenedor`, compartida con Receta Base) por una tabla de TODOS los
# platos activos con Grupo/Subgrupo/Precio/Costo/%Costo de Salón — la dona
# "no mostraba mucho" (un plato a la vez, elegido a mano). NO vive en
# recetas_comun.py como los otros 4 gráficos compartidos: GRUPO, SUBGRUPO,
# P.VENTA SALON, CST SALON y %CST SALON no tienen equivalente en
# recetabase.parquet (25 columnas, esquema RB NOMBRE/INSUMO/CST SUBT INS —
# ver docstring de recetabase.py), así que Receta Base sigue con la dona.
#
# P.VENTA SALON / CST SALON / %CST SALON son atributos del PLATO, no del
# ítem-insumo: confirmado contra R2 real (2026-08-24, DuckDB directo sobre
# recetaventa.parquet) que los 850 platos del catálogo tienen un único
# valor de los tres por COD PLATO, repetido en cada fila-insumo — mismo
# patrón que VALOR_ANO_ANTERIOR en compras.parquet (CLAUDE.md § "Antes de
# sumar una columna comparable"). Por eso se toman con `.first()` por
# plato, nunca `.sum()`. También confirmado que CST SALON == suma de
# TOTAL de los ítems de ese plato — la receta de la derecha y el costo de
# la izquierda siempre cuadran, sin filtrar por INS ACTIVO (CST SALON
# tampoco filtra por eso).
#
# El insumo de la receta se lee de INS RV, no de ITEM RV: verificado que
# ITEM RV es el número de LÍNEA dentro de la receta (001, 002…), no una
# identidad de insumo — el mismo COD INS aparece como "001" en un plato y
# "019" en otro. INS RV es el texto descriptivo, estable 1:1 contra
# COD INS (0 variación en 1.058 códigos). "Ingredientes clave" (vía
# recetas_comun.py) todavía agrupa por ITEM RV — bug preexistente, fuera
# del alcance de este cambio, no tocado acá. "Costeo Receta Venta" (antes
# "Ranking") ya usa INS RV y no ITEM RV desde que se armó como tabla — ver
# `_tabla_costeo_venta`, más abajo.
#
# Y el 2026-08-30 se sumaron tres columnas más a pedido: P. Neto Salón
# (= P.VENTA SALON / 1.18, IGV 18% — mismo criterio que
# `formulario_receta.py::_IGV`, ver el comentario de `_IGV` más abajo),
# Actualizado y Última Venta (ésta, la última columna de la tabla, a
# pedido explícito) — las dos de columnas NATIVAS del parquet (`FECH
# MODIF` / `ULTIMA VENT`), NO de cruzar contra ventas.parquet. Ver
# arquitectura.md regla #253 para el detalle de cada verificación
# (`ULTIMA VENT` no coincide al minuto con el registro real de
# ventas.parquet, y por qué eso no la invalida; y por qué 1.18 sigue
# siendo la cuenta correcta para un precio de LISTA aunque el ratio real
# de una venta ya cerrada, con descuentos adentro, dé otra cosa).
#
# Y el 2026-08-31, a pedido, el panel de receta baja de un costado a
# ABAJO de la tabla, y a SU costado aparece un mini panel con dos
# pestañas — `_dib_torta_costo_utilidad` (donut Costo/Utilidad del plato
# en foco) y `_dib_sankey_insumo_costo` (Sankey plato→insumo, mismo
# cálculo que tenía `_sankey_contenedor` antes de borrarse de
# recetas_comun.py el 2026-08-30, ver el docstring del módulo, pero a
# tamaño MINI y sólo del plato en foco, no una vista propia).


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


def _dib_torta_costo_utilidad(fila_foco, foco, costo_sim=None):
    """Mini donut Costo/Utilidad del plato en foco: Costo Salón vs.
    (P. Neto Salón − Costo Salón). Si el costo supera al precio neto —pasa
    de verdad: arquitectura.md regla #205 mide bebidas premium con %Costo
    de 300–950%, porque Costo Salón es la BOTELLA entera y P.Venta Salón
    la COPA— la Utilidad da negativa y un donut no puede dibujar eso (una
    porción no puede ser "menos que nada"): se avisa el monto en vez de
    forzar un gráfico que mentiría.

    `costo_sim`: el costo del BORRADOR del simulador, cuando hay uno. El
    %Costo se RECALCULA contra el precio neto en vez de leerse de
    `fila_foco["Pct"]`, que es el del parquet — si no, mover una cantidad
    cambiaba el tamaño de la porción y dejaba el número del medio quieto,
    que es justo la contradicción que el velo de la app existe para
    evitar."""
    if not len(fila_foco):
        st.info("Sin datos para este plato.")
        return
    neto = float(fila_foco["PrecioNeto"].iloc[0])
    if costo_sim is None:
        costo = float(fila_foco["Costo"].iloc[0])
        pct = float(fila_foco["Pct"].iloc[0])
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


def _tabla_composicion_venta(df_f):
    """Vista 'Composición': ranking de platos activos (AgGrid, barra de
    %Costo salón coloreada por umbral) a lo ancho, y ABAJO la receta del
    plato en foco (tabla) + un mini panel con dos pestañas (torta Costo/
    Utilidad, Sankey Insumo/Costo) — los tres actualizados al hacer clic
    en una fila."""
    col_cod_plato = _resolver(df_f, ["COD PLATO", "Cod Plato"])
    col_plato = _resolver(df_f, ["NOMB PLATO", "Nombre Plato", "PLATO", "Plato"])
    col_grupo = _resolver(df_f, ["GRUPO", "Grupo"])
    col_subgrupo = _resolver(df_f, ["SUBGRUPO", "Sub Grupo", "Subgrupo"])
    col_precio = _resolver(df_f, ["P.VENTA SALON", "P VENTA SALON",
                                  "Precio Venta Salon", "PVENTA SALON"])
    col_costo = _resolver(df_f, ["CST SALON", "CST SALÓN", "Costo Salon"])
    col_pct = _resolver(df_f, ["%CST SALON", "% CST SALON", "PCT CST SALON",
                               "Pct Cst Salon"])
    col_activo = _resolver(df_f, ["ITEM VENTA ACTIVO", "Item Venta Activo"])
    col_ins = _resolver(df_f, ["INS RV", "Ins Rv"])
    col_cant = _resolver(df_f, ["CANTIDAD", "Cantidad"])
    col_total = _resolver(df_f, ["TOTAL", "Total"])
    # Opcionales (a diferencia de las de arriba, que son obligatorias — ver
    # `faltan` más abajo): si no están, la tabla se queda sin esa columna
    # en vez de romperse. Ver arquitectura.md regla #253 para el porqué de
    # cada fuente — ninguna de las dos sale de cruzar contra ventas.parquet.
    col_ult_venta = _resolver(df_f, ["ULTIMA VENT", "Ultima Vent", "Ultima Venta"])
    col_fech_modif = _resolver(df_f, ["FECH MODIF", "Fech Modif", "Fecha Modif"])

    faltan = [n for n, c in (
        ("Plato", col_plato), ("Grupo", col_grupo), ("Subgrupo", col_subgrupo),
        ("Precio Venta Salón", col_precio), ("Costo Salón", col_costo),
        ("%Costo Salón", col_pct),
    ) if not c]
    if not col_cod_plato or faltan:
        st.info(
            "No se reconocieron todas las columnas de Composición "
            f"({', '.join(faltan) or 'Cod Plato'}). Esta vista necesita "
            "Cod Plato, Grupo, Subgrupo, P.Venta Salón, Cst Salón y "
            "%Cst Salón de recetaventa.parquet."
        )
        return

    d = df_f
    if col_activo:
        d = d[_activo(d[col_activo])]
    if d.empty:
        st.info("Sin platos activos para mostrar.")
        return

    agg = {
        "Grupo": (col_grupo, "first"),
        "Subgrupo": (col_subgrupo, "first"),
        "Plato": (col_plato, "first"),
        "Precio": (col_precio, "first"),
        "Costo": (col_costo, "first"),
        "Pct": (col_pct, "first"),
    }
    if col_ult_venta:
        agg["UltimaVenta"] = (col_ult_venta, "first")
    if col_fech_modif:
        agg["FechaModif"] = (col_fech_modif, "first")
    g = d.groupby(col_cod_plato, as_index=False).agg(**agg)
    g["Grupo"] = g["Grupo"].fillna("").astype(str)
    g["Subgrupo"] = g["Subgrupo"].fillna("").astype(str)
    g["Plato"] = g["Plato"].astype(str)
    g["Precio"] = pd.to_numeric(g["Precio"], errors="coerce").fillna(0.0)
    g["Costo"] = pd.to_numeric(g["Costo"], errors="coerce").fillna(0.0)
    g["Pct"] = pd.to_numeric(g["Pct"], errors="coerce").fillna(0.0) * 100
    g["_cod"] = g[col_cod_plato].astype(str)
    # IGV Perú, 18% — misma constante que `formulario_receta.py::_IGV`, NO
    # importada desde ahí a propósito: dashboard y herramienta son dos
    # módulos separados que coinciden en la referencia de negocio, no en
    # código que debieran compartir (mismo criterio que `_UMBRAL_COSTO_OK`/
    # `_UMBRAL_COSTO_WARN` de `recetaventa.py::_tabla_costeo_venta`). Se
    # calcula ACÁ, antes del filtro de precios centinela de más abajo, así
    # que un P.VENTA SALON centinela (~0) da un Precio Neto ~0 y no una
    # división que reviente — el filtro de abajo igual lo saca de la tabla.
    _IGV = 1.18
    g["PrecioNeto"] = g["Precio"] / _IGV
    # Fechas nativas del parquet, formateadas a texto DD/MM/AAAA (mismo
    # patrón que `graficos/compras/documentos_sunat.py`, columna "Fecha").
    if col_ult_venta:
        _uv = pd.to_datetime(g["UltimaVenta"], errors="coerce")
        # Centinela de "nunca se vendió": 1900-01-01 (el mínimo de un
        # SMALLDATETIME de SQL Server, el sistema de origen) en vez de
        # NULL — verificado contra R2 real: 75 de 850 platos, activos e
        # inactivos, con ESE valor exacto y ninguno con otra fecha antes
        # de 2021. Mismo patrón-trampa que el precio centinela de
        # P.VENTA SALON (arriba): mostrarlo tal cual diría que el plato
        # se vendió en 1900, así que se blanquea en vez de mostrarse.
        _uv = _uv.where(_uv >= pd.Timestamp("2000-01-01"))
        g["UltimaVenta"] = _uv.dt.strftime("%d/%m/%Y").fillna("")
    if col_fech_modif:
        g["FechaModif"] = pd.to_datetime(
            g["FechaModif"], errors="coerce").dt.strftime("%d/%m/%Y").fillna("")

    # P.VENTA SALON trae un cluster de precios centinela (1e-12…1.00,
    # verificado contra R2 real: 15 de 436 platos activos, TODOS con un
    # precio "redondo" que ningún plato real usa — cortesías, mermas,
    # ítems de exhibición) que no son precios de venta reales. Sin este
    # filtro %Costo se dispara a millones por ciento (S/0.58 de costo
    # sobre S/0.000000000001 de "precio") y esos platos degenerados
    # tapan el top entero del ranking — verificado en vivo, ver
    # arquitectura.md regla #205. El corte en 1 es el que mide el hueco
    # real: 0 platos activos caen entre 1 y 7 soles.
    _n_sin_precio = int((g["Precio"] <= 1).sum())
    g = g[g["Precio"] > 1]
    if g.empty:
        st.info("Ningún plato activo tiene un precio de Salón configurado.")
        return
    g = g.sort_values("Pct", ascending=False).reset_index(drop=True)

    # La barra es el FONDO de la celda (mismo `linear-gradient` que el
    # ranking de Proveedor/Producto de Compras — arquitectura.md regla
    # #136), coloreado por el semáforo 30/35% de arriba en vez de un
    # accent fijo: acá el color ES el dato (qué tan caro sale el plato),
    # no solo un ranking relativo.
    _js_barra_pct = JsCode(
        "function(p){"
        " var w = Math.max(0, Math.min(100, p.value||0));"
        f" var c = w <= {_UMBRAL_COSTO_OK} ? '{EXITO}'"
        f" : w <= {_UMBRAL_COSTO_WARN} ? '{ADVERTENCIA}' : '{ERROR}';"
        " return {'background': 'linear-gradient(90deg, ' + c + ' 0 ' + w"
        " + '%, transparent ' + w + '% 100%)',"
        " 'display':'flex','alignItems':'center','justifyContent':'flex-end',"
        f" 'color':'{TEXTO_PRINCIPAL}'"
        "};"
        "}")
    _js_soles = JsCode(
        "function(p){ return p.value==null ? '' : 'S/ ' + p.value.toFixed(2); }")
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' : p.value.toFixed(1) + '%'; }")
    # Clic en la fila = toggle (mismo patrón que Compras › Proveedor/
    # Producto): AG Grid no deselecciona solo al reclickear la fila ya
    # elegida, y `st.dataframe` no sirve para esto — su columna de
    # selección se dibuja en un canvas, sin nodo que ocultar por CSS.
    _js_toggle = JsCode(
        "function(e){ e.node.setSelected(!e.node.isSelected(), true); }")

    # Ocho filas a la vista y el resto por scroll interno, con los MISMOS
    # números que el Ranking de proveedores (24 de fila, 32 de cabecera,
    # `CROMO_GRID_RANK` de cromo): eran 28 y 34 propios hasta el
    # 2026-09-17. `extra` no lleva sumando de fila TOTAL porque esta tabla
    # no tiene — ver el comentario del `AgGrid` de abajo.
    _ALTO_FRAME = alturas.por_filas(8, px_fila=ALTO_FILA_RANK,
                                    extra=CROMO_GRID_RANK, minimo=0)
    # El alto, ATADO desde el documento padre. El `height=` de abajo no
    # alcanza: st_aggrid mide su contenido y le reporta a Streamlit un
    # `setFrameHeight` que termina como `style height` INLINE sobre el
    # iframe y le gana a su propio atributo `height` — con 421 platos en
    # el df, eso serían miles de píxeles. Son DOS nodos y no sólo el
    # iframe: Streamlit escribe el alto reportado también sobre el
    # `stElementContainer` que lo envuelve. Sin guard de "una sola vez"
    # (regla #59). Ver regla #410, que lo midió en Inventario.
    st.markdown(
        "<style>div.st-key-rv_comp_grid, div.st-key-rv_comp_grid iframe "
        f"{{ height: {_ALTO_FRAME}px !important; }}</style>",
        unsafe_allow_html=True)

    # La tabla va a lo ANCHO ahora (2026-08-31, a pedido: "que la receta se
    # muestre abajo" — antes compartía fila con el panel de receta en 5:2).
    # Sin nada al lado, ya no hace falta ese reparto: %Costo entra holgado
    # y el resto de las columnas dejan de necesitar scroll en la mayoría
    # de las pantallas.
    with _card("rv_comp_tabla",
               "Platos activos · % de costo sobre venta en Salón"):
        # Ancho FIJO en todas las columnas, ninguna con `flex`: probado en
        # graficos/compras/producto.py (arquitectura.md regla #192) que
        # `st_aggrid` le clava `width: 200` a toda columna sin `width`
        # propio, y como AG Grid prioriza el `width` explícito para el
        # tamaño inicial, un `flex` mezclado con eso nunca reparte nada.
        #
        # %Costo va justo después de Plato, NO al final (pedido "Grupo,
        # Subgrupo, Plato, Precio, Costo, %Costo"): medido en el
        # navegador a 1280px con la tabla a 5/7 del ancho, ese orden
        # dejaba %Costo —la columna con la barra, la razón de ser de
        # esta vista— fuera del viewport visible sin scrollear.
        # Grupo+Subgrupo+Plato+%Costo entran holgados; Precio/Costo
        # (detalle de apoyo) son los que pueden quedar a un scroll de
        # distancia en una pantalla angosta.
        #
        # Precio Neto, Actualizado y Última Venta se sumaron el
        # 2026-08-30, a pedido — las dos últimas OPCIONALES, y Última
        # Venta la ÚLTIMA columna a propósito (pedido explícito). Ver
        # arquitectura.md regla #253 para el porqué de cada fuente.
        _campos = ["Grupo", "Subgrupo", "Plato", "Pct", "Precio", "PrecioNeto", "Costo"]
        _columnas = [
            {"field": "Grupo", "width": 90, "tooltipField": "Grupo"},
            {"field": "Subgrupo", "width": 100,
             "tooltipField": "Subgrupo"},
            {"field": "Plato", "width": 160, "tooltipField": "Plato"},
            {"field": "Pct", "headerName": "% Costo",
             "width": 80, "type": "numericColumn",
             "cellStyle": _js_barra_pct,
             "valueFormatter": _js_pct},
            {"field": "Precio", "headerName": "P. Venta Salón",
             "width": 90, "type": "numericColumn",
             "valueFormatter": _js_soles},
            {"field": "PrecioNeto", "headerName": "P. Neto Salón",
             "width": 90, "type": "numericColumn",
             "valueFormatter": _js_soles},
            {"field": "Costo", "headerName": "Costo Salón",
             "width": 90, "type": "numericColumn",
             "valueFormatter": _js_soles},
        ]
        if col_fech_modif:
            _campos.append("FechaModif")
            _columnas.append({"field": "FechaModif",
                              "headerName": "Actualizado", "width": 90})
        if col_ult_venta:
            _campos.append("UltimaVenta")
            _columnas.append({"field": "UltimaVenta",
                              "headerName": "Última Venta", "width": 100})
        _campos.append("_cod")
        _columnas.append({"field": "_cod", "hide": True})

        resp = AgGrid(
            g[_campos],
            gridOptions={
                "columnDefs": _columnas,
                "defaultColDef": {"sortable": True, "resizable": True},
                "rowSelection": {"mode": "singleRow", "checkboxes": False,
                                 "enableClickSelection": False},
                "onRowClicked": _js_toggle,
                "rowHeight": ALTO_FILA_RANK,
                "headerHeight": ALTO_HEADER_RANK,
                "suppressCellFocus": True,
                "suppressMovableColumns": True,
                # SIN `pinnedBottomRowData`, a diferencia del resto de las
                # tablas-ranking del repo, y no es un olvido: las seis
                # columnas numéricas de acá son atributos del PLATO, no
                # magnitudes que se acumulen. Sumar los precios de 421
                # platos no significa nada y promediar el %Costo es la
                # trampa de la #199 (un ratio no se re-pondera sobre el
                # agregado). Una fila TOTAL vacía en cinco de seis
                # columnas es peor que no tenerla.
            },
            allow_unsafe_jscode=True,
            theme="streamlit",
            # El tema de fábrica no alcanza: las filas blancas sin rayado,
            # la cabecera sin franja lavanda, el cuerpo de 11.5px y el
            # marco de FRANJA (dos líneas de 3px arriba y abajo, sin
            # bordes laterales ni líneas verticales) salen de
            # `CSS_RANKING_GRID`, y el único camino es `custom_css=`
            # porque el grid vive en un iframe y el `<style>` del padre no
            # entra. De ahí sale también la marca de la fila SELECCIONADA
            # (`.ag-row-selected::before`, el acento al 8%), que acá es el
            # plato cuyo panel de receta se ve abajo.
            custom_css=CSS_RANKING_GRID,
            height=_ALTO_FRAME,
            update_on=["selectionChanged"],
            key="rv_comp_grid",
        )
        _pie = "Clic en una fila para ver su receta →"
        if _n_sin_precio:
            _pie += f" · {_n_sin_precio} sin precio de Salón configurado, no se muestran"
        st.caption(_pie)

    sel = getattr(resp, "selected_rows", None)
    if sel is not None and len(sel):
        fila_sel = sel.iloc[0] if hasattr(sel, "iloc") else sel[0]
        clicked = str(fila_sel["_cod"])
    else:
        clicked = None
    # Sin clic (o reclic que deselecciona, ver `_js_toggle`): cae al primer
    # plato de la tabla, que por el sort de arriba es el de %Costo más
    # alto — el panel de abajo nunca arranca vacío.
    foco = clicked if clicked else str(g["_cod"].iloc[0])
    fila_foco = g[g["_cod"] == foco]
    nombre_foco = str(fila_foco["Plato"].iloc[0]) if len(fila_foco) else ""

    # ── Receta del plato en foco + mini panel (torta/Sankey) ─────────
    # ABAJO de la tabla, a pedido (2026-08-31) — antes vivía a un costado.
    #
    # `r` sale de `_panel_receta`, que es quien decide si lo que se ve es la
    # receta del parquet o el BORRADOR del simulador. Se arma UNA sola vez y
    # las tres piezas leen ese mismo frame: la tabla de la izquierda, el
    # Sankey y la dona. Antes se calculaba acá inline; con el simulador eso
    # dejaba dos fuentes para lo mismo, que es exactamente cómo divergen.
    #
    # `costo_sim` viene en `None` mientras no se esté simulando, y la dona lo
    # usa para saber si el %Costo lo lee del parquet o lo recalcula.
    #
    # [3, 2]: la tabla de receta necesita más ancho que la torta/Sankey
    # (nombres de insumo largos en la primera columna, y ahora además las
    # dos columnas editables y el buscador del catálogo); el mini panel no
    # gana nada con más ancho, un donut/Sankey de 2 niveles no crece en
    # utilidad por estirarse.
    c_receta, c_mini = st.columns([3, 2], gap="medium")
    with c_receta:
        r, costo_sim = _panel_receta(df_f, foco, nombre_foco, col_cod_plato,
                                     col_ins, col_cant, col_total)

    with c_mini:
        with _card("rv_comp_mini"):
            # NO `st.tabs`: dibuja las DOS pestañas y esconde la otra con
            # `display: none`, y el Sankey es un `plotly_events` (iframe).
            # Escondido, su iframe mide 0 y el componente alterna
            # `setFrameHeight` 240 ↔ 0 sin fin — medido: ~750 mensajes/s,
            # cada uno re-dibuja el Sankey, el hilo del navegador no
            # suelta nunca y TODA la página de Recetas se traba (se
            # reportó como «Nueva receta se bloquea al agregar ítems»,
            # 2026-09-23). Acá sólo existe el panel elegido. Regla #500.
            vista = st.segmented_control(
                "Vista", ["Costo / Utilidad", "Sankey"],
                default="Costo / Utilidad", key="rv_comp_mini_vista",
                label_visibility="collapsed",
            )
            if vista == "Sankey":
                _dib_sankey_insumo_costo(
                    r, nombre_foco, foco, costo_sim is not None)
            else:
                _dib_torta_costo_utilidad(fila_foco, foco, costo_sim)


# ─── Costeo Receta Venta: ranking de platos por costo, en tabla ────────────
# Reemplaza el gráfico de barras horizontales que tenía esta vista hasta el
# 2026-08-30 (a pedido: "en lugar de un gráfico, una tabla tipo ranking,
# ordenada por costo, algo así como el que tengo para compras" — ver
# graficos/compras/proveedor.py, Ranking de Proveedores, mismo lenguaje
# visual: barra como FONDO de celda vía `linear-gradient`, fila TOTAL
# fijada abajo). Misma agregación que el gráfico que reemplazaba — suma de
# `col_valor` por plato, SIN filtrar por activo (ese filtro tampoco lo
# tenía `_ranking_contenedores`) — así que los números no cambian, sólo
# cómo se dibujan.
#
# NO vive en recetas_comun.py como los otros 3 gráficos compartidos
# (Sankey/Ingredientes clave/Panorama): sólo Receta Venta pidió el cambio,
# y Receta Base se queda con el gráfico de barras compartido
# (`_ranking_contenedores`) — mismo criterio que `_tabla_composicion_venta`,
# arriba.
#
# Ancho de columnas: FIJO en las cuatro, ninguna con `flex` — arquitectura.md
# regla #193 (`st_aggrid` inyecta `width: 200` a toda columna sin uno
# propio, y ese ancho explícito le gana al `flex` en el render inicial; el
# Ranking de Proveedores "funciona" con flex sólo porque nunca cruzó el
# umbral de columnas — la regla #193 lo llama "el bug dormido").
def _tabla_costeo_venta(df_f, col_plato, col_valor, es_soles):
    """Vista 'Costeo Receta Venta': ranking de platos por costo (o
    cantidad) total, en una tabla AgGrid — mismo lenguaje visual que el
    Ranking de Proveedores de Compras."""
    # INS RV, no ITEM RV, para el conteo de insumos: ITEM RV es el número
    # de LÍNEA dentro de la receta, no una identidad de insumo — ver
    # arquitectura.md regla #205 (punto 2). Columna opcional: si no está
    # (p.ej. un export viejo), la tabla se queda sin "Ítems" en vez de
    # romperse, mismo criterio defensivo que el resto del dashboard.
    col_ins = _resolver(df_f, ["INS RV", "Ins Rv"])

    agg = {"Plato": (col_plato, "first"), "Valor": (col_valor, "sum")}
    if col_ins:
        agg["Items"] = (col_ins, "nunique")
    g = df_f.groupby(col_plato, as_index=False).agg(**agg)
    g["Plato"] = g["Plato"].astype(str)
    g = g.sort_values("Valor", ascending=False).reset_index(drop=True)
    if g.empty:
        st.info("Sin datos para el ranking.")
        return

    total_valor = float(g["Valor"].sum()) or 1.0
    g["Pct"] = g["Valor"] / total_valor * 100
    g_max = float(g["Valor"].max()) or 1.0
    g["_barra"] = g["Valor"] / g_max * 100

    etiqueta_valor = "Costo (S/)" if es_soles else "Cantidad"

    # La barra es el FONDO de la celda (mismo `linear-gradient` que el
    # Ranking de Proveedores/Productos de Compras, arquitectura.md regla
    # #136), escalada contra el MAYOR valor visible y topada al 62% del
    # ancho para que el texto —alineado a la derecha— nunca caiga encima.
    _js_barra = JsCode(
        "function(p){"
        " if (p.node.rowPinned) return {'display':'flex','alignItems':'center',"
        " 'justifyContent':'flex-end','fontWeight':'700'};"
        " var w = Math.max(0, Math.min(100, p.data._barra||0)) * 0.62;"
        " return {'background': 'linear-gradient(90deg,"
        f" {ACENTO} 0 ' + w + '%, transparent ' + w + '% 100%)',"
        " 'display':'flex','alignItems':'center','justifyContent':'flex-end',"
        f" 'color':'{TEXTO_PRINCIPAL}'"
        "};"
        "}")
    # Números redondos (sin decimales): mismo formato que ya mostraban las
    # barras del gráfico que esto reemplaza (`text=f"{pref}{v:,.0f}"`).
    if es_soles:
        _js_valor_fmt = JsCode(
            "function(p){ return p.value==null ? '' :"
            " 'S/ ' + Math.round(p.value).toLocaleString('es-PE'); }")
    else:
        _js_valor_fmt = JsCode(
            "function(p){ return p.value==null ? '' :"
            " Math.round(p.value).toLocaleString('es-PE'); }")
    _js_pct = JsCode(
        "function(p){ return p.value==null ? '' : Math.round(p.value) + '%'; }")
    # Misma paleta que la fila TOTAL del Ranking de Proveedores — y desde
    # el 2026-09-17, también sin su `borderTop`: `CSS_RANKING_GRID` apaga
    # la línea del tema (`--ag-pinned-row-border: none`) y con las dos
    # puestas quedaban DOS líneas apiladas de distinto color. El mismo
    # inline se sacó de `proveedor.py` cuando ese dict nació.
    _js_fila_total = JsCode(
        "function(p){ if(p.node.rowPinned){ return {"
        f"'fontWeight':'700','background':'{LAVANDA_CHIP}',"
        f"'color':'{ACENTO_TEXTO_OSCURO}'"
        "}; } }")

    # Sin filtro de platos en esta vista (a diferencia del Ranking de
    # Proveedores, que sí puede excluir algunos): la tabla siempre muestra
    # TODOS, así que el TOTAL es exacto (100.0%) y no la suma de redondeos
    # por fila.
    _fila_total = {"Plato": "TOTAL", "Valor": round(total_valor, 2), "Pct": 100.0}
    if col_ins:
        _fila_total["Items"] = int(g["Items"].sum())

    # 10 filas visibles + la fila TOTAL fijada, que reserva su sitio
    # DENTRO del `height=` (sin ese sumando le come una fila a los datos)
    # + `CROMO_GRID_RANK`, que es la cabecera y el cromo del tema medidos
    # en el DOM. El resto de los platos scrollea DENTRO del grid — a
    # diferencia del gráfico que esto reemplaza, ya no hace falta un
    # selector "Mostrar N": acá el scroll hace ese trabajo (mismo criterio
    # que el Ranking de Proveedores de Compras).
    #
    # Los números son los del ranking (24/32) desde el 2026-09-17; eran 28
    # y 34 propios. Siguen siendo DIEZ filas a la vista: lo que se pidió
    # fue el look, no menos datos — la tarjeta baja de 350 a 303px sola.
    _ALTO_FRAME = alturas.por_filas(
        10, px_fila=ALTO_FILA_RANK,
        extra=CROMO_GRID_RANK + ALTO_FILA_RANK, minimo=0)
    # El alto, ATADO desde el documento padre — misma razón y mismos DOS
    # nodos que en `_tabla_composicion_venta`. Ver regla #410.
    st.markdown(
        "<style>div.st-key-rv_costeo_grid, div.st-key-rv_costeo_grid iframe "
        f"{{ height: {_ALTO_FRAME}px !important; }}</style>",
        unsafe_allow_html=True)

    columnas = [
        {"field": "Plato", "width": 420, "tooltipField": "Plato"},
        {"field": "Valor", "headerName": etiqueta_valor, "width": 160,
         "type": "numericColumn", "sort": "desc",
         "cellStyle": _js_barra, "valueFormatter": _js_valor_fmt},
    ]
    campos = ["Plato", "Valor"]
    if col_ins:
        columnas.append({"field": "Items", "headerName": "Ítems", "width": 90,
                         "type": "numericColumn"})
        campos.append("Items")
    columnas.append({"field": "Pct", "headerName": "%", "width": 80,
                     "type": "numericColumn", "valueFormatter": _js_pct})
    campos.append("Pct")
    columnas.append({"field": "_barra", "hide": True})
    campos.append("_barra")

    with _card("rv_costeo",
               f"Platos por {'costo' if es_soles else 'cantidad'} total"):
        AgGrid(
            g[campos],
            gridOptions={
                "columnDefs": columnas,
                "defaultColDef": {"sortable": True, "resizable": True},
                "suppressCellFocus": True,
                "suppressMovableColumns": True,
                "rowHeight": ALTO_FILA_RANK,
                "headerHeight": ALTO_HEADER_RANK,
                "pinnedBottomRowData": [_fila_total],
                "getRowStyle": _js_fila_total,
            },
            allow_unsafe_jscode=True,
            theme="streamlit",
            # Mismo dict que la tabla de Composición y que el Ranking de
            # proveedores del que salió: blanco sin rayado, cabecera sin
            # franja lavanda, cuerpo de 11.5px y marco de FRANJA. Va por
            # `custom_css=` porque el grid es un iframe.
            custom_css=CSS_RANKING_GRID,
            height=_ALTO_FRAME,
            key="rv_costeo_grid",
        )
        st.caption(f"{len(g)} platos · ordenado por {etiqueta_valor.lower()}")
