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
                          (_comun, proveedor, familia, cantidad, evolucion).
                          Era un compras.py de 2.835 líneas hasta 2026-08-01.
        ventas.py      → dashboard Ventas (ranking FoodCost, matriz agrupada)
        inventario.py  → dashboard Inventario Valorizado (v2)
        constructor.py → constructor estilo Power BI (usado por Compras)
        legacy.py      → Inventario Valorizado v1 (respaldo, no en la ruta activa)

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
from graficos.recetaventa import renderizar_graficos_recetaventa      # noqa: F401
from graficos.ventas import renderizar_graficos_ventas                # noqa: F401
# legacy.renderizar_graficos NO se re-exporta: ya no se usa desde fuera.


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
    "Receta Venta":          renderizar_graficos_recetaventa,
    "Ventas":                renderizar_graficos_ventas,
}


def renderizar_graficos_reporte(df_f, reporte, cfg, df_full=None, tabla_cb=None):
    """Punto de entrada de la vista Gráficos.

    Si el reporte tiene un dashboard dedicado, delega. Si no, usa el motor
    genérico (config-driven en cfg["graficos"]) con fallback al explorador.

    df_full: DataFrame sin el filtro de fecha aplicado (opcional).
        Solo Ajuste lo usa (pestaña Histórico); los demás lo ignoran.
    tabla_cb: callback que renderiza la tabla AgGrid del reporte. Lo usan
        los dashboards con rail donde "Tabla" es un item más (hoy Ajuste,
        Ventas, Inventario Valorizado y Receta Venta; el patrón estándar a
        futuro). Los demás lo ignoran. La FIRMA del callback la decide cada
        dashboard (documentado en su docstring): Ajuste y Receta Venta lo
        llaman sin args (no tienen chips propios — usan los genéricos de
        app.py); Ventas e Inventario Valorizado le pasan `d` — el df ya
        filtrado por sus propios chips (dentro de cada módulo) para que la
        Tabla no tenga un estado de filtros distinto al de los gráficos.
    """
    render = _DASHBOARDS.get(reporte)
    if render is not None:
        # Solo los dashboards migrados al rail aceptan tabla_cb; el resto
        # conserva su firma antigua (la vista Tabla la maneja app.py).
        if reporte in ("Ajuste de Inventario", "Ventas",
                      "Inventario Valorizado", "Receta Venta"):
            render(df_f, reporte, df_full=df_full, tabla_cb=tabla_cb)
        else:
            render(df_f, reporte, df_full=df_full)
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
