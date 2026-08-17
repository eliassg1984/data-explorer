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
        ventas.py      → dashboard Ventas (ranking FoodCost, matriz agrupada)
        inventario.py  → dashboard Inventario Valorizado (v2)
        salidas.py     → dashboard Salidas (evolución + subalmacén + tipo)
        requerimientos.py → dashboard Requerimientos (evolución + sub
                          almacén + estado). Comparte nav con Salidas
                          ("Movimientos") — ver movimientos_comun.py.
        movimientos_comun.py → chip Requerimiento/Salidas + vista
                          "Comparativo" (Pedido vs Baja), compartidos entre
                          requerimientos.py y salidas.py.
        constructor.py → constructor estilo Power BI (usado por Compras)

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
from graficos.inventario import renderizar_graficos_inventario        # noqa: F401
from graficos.recetabase import renderizar_graficos_recetabase        # noqa: F401
from graficos.recetaventa import renderizar_graficos_recetaventa      # noqa: F401
from graficos.requerimientos import renderizar_graficos_requerimientos  # noqa: F401
from graficos.salidas import renderizar_graficos_salidas              # noqa: F401
from graficos.ventas import renderizar_graficos_ventas                # noqa: F401


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
    "Inventario Valorizado": renderizar_graficos_inventario,
    "Receta Base":           renderizar_graficos_recetabase,
    "Receta Venta":          renderizar_graficos_recetaventa,
    "Requerimientos":        renderizar_graficos_requerimientos,
    "Salidas":               renderizar_graficos_salidas,
    "Ventas":                renderizar_graficos_ventas,
}


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
