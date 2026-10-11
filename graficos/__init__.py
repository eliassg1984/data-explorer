"""
graficos — paquete de dashboards de gráficos.

Este __init__.py es el DISPATCHER: elige qué dashboard renderizar según el
reporte activo. Cada dashboard vive en su propio módulo hermano y aporta
una única función pública (`renderizar_graficos_<nombre>`).

Estructura:
    graficos/
        __init__.py    → dispatcher + re-exports públicos
        base.py        → infraestructura compartida (cards, motor genérico,
                          resolución de columnas, helpers de layout)
        ajuste.py      → dashboard Ajuste de Inventario
        compras/       → dashboard Compras — PAQUETE, un drill por archivo
                          (_comun, proveedor, familia, cantidad).
                          Era un compras.py de 2.835 líneas hasta 2026-08-01.
        sunat_reporte.py → dashboard Documentos SUNAT: sólo el despacho; el
                          drill sigue en compras/documentos_sunat.py (era
                          una vista de Compras hasta el 2026-09-30).
        ventas.py      → dashboard Ventas (resumen, mix de carta, platos)
        costos.py      → dashboard Costos: el costo de ventas por mes
                          operativo (2026-10-09). La cuenta, en
                          costo_ventas.py; la tabla, en costos_tabla.js.
        inventario.py  → dashboard Inventario Valorizado (v2)
        movimientos.py  → dashboard Movimientos: UNA página con los dos
                          parquets del flujo de stock (requerimientos +
                          salidas). Eran DOS reportes que un chip
                          alternaba hasta el 2026-09-05 — ver regla #322.
        movimientos_comun.py → las piezas que miran los DOS parquets a la
                          vez: el recorte por rango y, sin caller desde la
                          regla #411, el ranking de proporción dada de baja.

Cómo agregar un dashboard nuevo (p.ej. "Mermas"):
    1. Crear graficos/mermas.py con `def renderizar_graficos_mermas(df, reporte, df_full=None): ...`
    2. Añadir la entrada al dict `_DASHBOARDS` de abajo: "Mermas": renderizar_graficos_mermas
    3. Listo — no hay que tocar más nada aquí ni en app.py.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Infraestructura compartida
# ---------------------------------------------------------------------------

from graficos.base import _card, crear_grafico, renderizar_graficos_genericos

# ---------------------------------------------------------------------------
# Dashboards — cada uno se re-exporta para consumidores externos que aún los
# importen como `graficos.renderizar_graficos_X` (compat) y para el dispatcher.
# ---------------------------------------------------------------------------

from graficos.ajuste import renderizar_graficos_ajuste                # noqa: F401
from graficos.compras import renderizar_graficos_compras              # noqa: F401
from graficos.costos import renderizar_graficos_costos                # noqa: F401
from graficos.inventario import renderizar_graficos_inventario        # noqa: F401
from graficos.movimientos import renderizar_graficos_movimientos      # noqa: F401
from graficos.recetas import renderizar_graficos_recetas              # noqa: F401
from graficos.sunat_reporte import renderizar_graficos_sunat          # noqa: F401
from graficos.ventas import renderizar_graficos_ventas                # noqa: F401
# Los rails de cada dashboard, para `vistas_de` (abajo).
from graficos.ajuste import _AJUSTE_RAIL_CATEGORIAS
from graficos.compras import _COMPRAS_RAIL_CATEGORIAS
from graficos.costos import _COSTOS_RAIL_CATEGORIAS
from graficos.inventario import _INVENTARIO_RAIL_CATEGORIAS
from graficos.movimientos import _RAIL_CATEGORIAS as _MOV_RAIL
from graficos.recetas import _RAIL_CATEGORIAS as _REC_RAIL
from graficos.sunat_reporte import _SUNAT_RAIL_CATEGORIAS
from graficos.ventas import _VENTAS_RAIL_CATEGORIAS


# render_vista_pills() (pestañas Gráficos/Tabla en la franja) se eliminó
# 2026-08-04: desde que los 8 reportes usan el rail derecho compartido (ver
# _render_rail en graficos/base.py — "Tabla" es un item más del rail), ya
# no queda ningún caller. Si hace falta un selector Gráficos/Tabla suelto
# de nuevo, buscar esta función en el historial de git antes de reescribirla.


# ---------------------------------------------------------------------------
# Dispatcher — registro de dashboards por reporte. Agregar uno nuevo es una
# sola línea aquí + un archivo hermano. Sin cadena de if/elif.
# ---------------------------------------------------------------------------

_DASHBOARDS = {
    "Ajuste de Inventario": renderizar_graficos_ajuste,
    "Compras":               renderizar_graficos_compras,
    # El costo de ventas por mes operativo (2026-10-09, regla #622).
    "Costos":                renderizar_graficos_costos,
    # Reporte propio desde el 2026-09-30 (era una vista de Compras, regla #577).
    "Documentos SUNAT":      renderizar_graficos_sunat,
    "Inventario Valorizado": renderizar_graficos_inventario,
    "Recetas":               renderizar_graficos_recetas,
    "Movimientos":           renderizar_graficos_movimientos,
    "Ventas":                renderizar_graficos_ventas,
}


# ── LAS VISTAS DE CADA REPORTE, SIN ENTRAR A ÉL (2026-09-29, regla #568) ────
# Al pasar el cursor por un reporte del rail, `navegacion.py` abre un panel
# con sus vistas, y un clic en una lleva al reporte Y a esa vista. Para eso
# necesita, de cada dashboard, lo mismo que ese dashboard le pasa a su
# `_render_rail`: sus categorías (ya sin las Tablas ocultas, #507) y la
# clave de `session_state` donde el rail guarda la vista elegida.
#
# Son las MISMAS constantes, importadas, no una copia: una lista aparte de
# vistas por reporte es la garantía de que el panel y el rail un día digan
# cosas distintas. Un dashboard nuevo se suma acá además de en
# `_DASHBOARDS`; `test_graficos.py::_pruebas_vistas_de_cada_reporte` falla
# si falta.
_RAILS = {
    "Ajuste de Inventario":  (_AJUSTE_RAIL_CATEGORIAS, "ajuste_graf_tipo"),
    "Compras":               (_COMPRAS_RAIL_CATEGORIAS, "compras_graf_tipo"),
    "Costos":                (_COSTOS_RAIL_CATEGORIAS, "costos_graf_tipo"),
    "Documentos SUNAT":      (_SUNAT_RAIL_CATEGORIAS, "sunat_graf_tipo"),
    "Inventario Valorizado": (_INVENTARIO_RAIL_CATEGORIAS, "inv_graf_tipo"),
    "Recetas":               (_REC_RAIL, "rec_graf_tipo"),
    "Movimientos":           (_MOV_RAIL, "mov_graf_tipo"),
    "Ventas":                (_VENTAS_RAIL_CATEGORIAS, "ventas_graf_tipo"),
}


def vistas_de(reporte):
    """`(state_key, ((id, rótulo, ícono), …))` del rail de `reporte`, o None.

    El rótulo es el corto, el mismo que muestra el rail; el ícono puede ser
    None (hay rails con tuplas de dos). El orden es el del rail, que es el
    de la página."""
    par = _RAILS.get(reporte)
    if par is None:
        return None
    categorias, state_key = par
    vistas = tuple((item[0], item[1], item[2] if len(item) > 2 else None)
                   for _, items in categorias for item in items)
    return state_key, vistas


def tiene_dashboard(reporte):
    """True si `reporte` tiene un dashboard dedicado registrado arriba.

    Existe para que app.py no tenga que enumerar reportes a mano ni importar
    `_DASHBOARDS` (privado) para saberlo: los reportes con dashboard dibujan
    su propio rail y reciben `tabla_cb`; los que no, caen al explorador
    genérico con un rail de 2 items que arma app.py. Así, registrar un
    dashboard nuevo sigue siendo UNA línea en _DASHBOARDS — sin tocar app.py.
    """
    return reporte in _DASHBOARDS


def renderizar_graficos_reporte(df_f, reporte, cfg, df_full=None, tabla_cb=None):
    """Punto de entrada de la vista Gráficos.

    Si el reporte tiene un dashboard dedicado, delega. Si no, usa el motor
    genérico (config-driven en cfg["graficos"]) con fallback al explorador.

    df_full: DataFrame sin el filtro de fecha aplicado (opcional).
        Solo Ajuste lo usa (pestaña Histórico); los demás lo ignoran.
    tabla_cb: callback que renderiza la tabla AgGrid del reporte. Lo usan
        los dashboards con rail donde "Tabla" es un item más.

        FIRMA ÚNICA: `tabla_cb(d)`, donde `d` es el DataFrame que el
        dashboard quiere que se tabule. Los que tienen chips propios
        (Ventas, Inventario Valorizado, Salidas) pasan su df YA filtrado,
        para que la Tabla no tenga un estado de filtros distinto al de sus
        gráficos; los que no los tienen (Ajuste, Receta Venta) pasan su df
        tal cual y app.py les aplica los chips genéricos de la franja.

        Hasta el 2026-08-08 la firma la decidía cada dashboard —unos
        llamaban `tabla_cb()` y otros `tabla_cb(d)`— y el único sitio
        donde constaba era el docstring. Un dashboard nuevo que eligiera
        mal fallaba con TypeError solo al hacer clic en "Tabla".
    """
    render = _DASHBOARDS.get(reporte)
    if render is not None:
        # Todos los dashboards aceptan tabla_cb (los que no lo usan lo
        # ignoran), así que no hace falta una lista de reportes que
        # mantener sincronizada con _DASHBOARDS.
        render(df_f, reporte, df_full=df_full, tabla_cb=tabla_cb)
        return

    # Motor genérico config-driven (para reportes sin dashboard dedicado)
    graficos_conf = cfg.get("graficos", [])
    if graficos_conf:
        omitidos = []
        for _i, conf in enumerate(graficos_conf):
            fig, err = crear_grafico(df_f, conf)
            if fig:
                with _card(f"conf_{reporte}_{_i}"):
                    st.plotly_chart(fig, use_container_width=True)
            else:
                omitidos.append(f"«{conf.get('titulo', conf.get('tipo'))}» ({err})")
        if omitidos:
            st.caption("⚠️ Gráficos omitidos: " + "; ".join(omitidos))

        with st.expander("🎛️ Explorador de gráficos"):
            renderizar_graficos_genericos(df_f, reporte)
    else:
        renderizar_graficos_genericos(df_f, reporte)
