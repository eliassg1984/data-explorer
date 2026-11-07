"""Familia y Subfamilia tienen una selección por tarjeta de Compras."""

import streamlit as st

from graficos.base import poner_seleccion, recortar_seleccion, seleccion_en_panel


_GLOBALES_ANTERIORES = ("compras_graf_filtro_fam", "compras_graf_filtro_sub")


def _claves(seccion):
    slug = seccion.removeprefix("compras_sec_")
    return f"cp_familias_{slug}", f"cp_subfamilias_{slug}"


def filtros_vista(seccion):
    ss = st.session_state
    return {
        rotulo: list(ss.get(clave, ss.get(anterior, ())) or ())
        for rotulo, clave, anterior in zip(("Familia", "Subfamilia"), _claves(seccion), _GLOBALES_ANTERIORES)
    }


def subfamilias_disponibles(mapa, familias):
    return sorted({sub for familia in familias for sub in mapa.get(familia, ())})


def preparar_filtros_vista(seccion, opciones, mapa_sub, iniciales):
    ss = st.session_state
    k_fam, k_sub = _claves(seccion)
    if k_fam not in ss:
        poner_seleccion(k_fam, ss.get(_GLOBALES_ANTERIORES[0], iniciales) or ())
    if k_sub not in ss:
        poner_seleccion(k_sub, ss.get(_GLOBALES_ANTERIORES[1], ()) or ())
    recortar_seleccion(k_fam, opciones)
    recortar_seleccion(k_sub, subfamilias_disponibles(mapa_sub, ss[k_fam]))
    return tuple(ss[k_fam]), tuple(ss[k_sub])


def recortar_filtros_vista(df, col_fam, col_sub, seleccion):
    if df is None:
        return None
    for col, valores in zip((col_fam, col_sub), seleccion):
        if valores and col and col in df.columns:
            df = df[df[col].astype(str).isin(valores)]
    return df


def _grupo_filtro(rotulo, limpiar, clave, opciones):
    with st.container(horizontal=True, horizontal_alignment="distribute",
                      vertical_alignment="center", gap="small"):
        st.markdown(f"**{rotulo}**")
        if st.session_state.get(clave):
            st.button(limpiar, key=f"{clave}_todas", on_click=poner_seleccion, args=(clave, []))
    seleccion_en_panel(st.pills, rotulo, clave, opciones,
                       selection_mode="multi", label_visibility="collapsed")


def panel_filtros_vista(seccion, opciones, mapa_sub):
    k_fam, k_sub = _claves(seccion)
    actual = filtros_vista(seccion)
    disponibles = subfamilias_disponibles(mapa_sub, actual["Familia"])
    cuenta = sum(bool(valores) for valores in actual.values())

    def resumen(valores):
        if len(valores) > 3:
            return f"{len(valores)} seleccionadas"
        return ", ".join(valores) or "todas"

    ayuda = "Filtros de esta vista" + "".join(
        f"\n\n{rotulo}: {resumen(valores)}" for rotulo, valores in actual.items()
    )
    icono = f":material/tune: {cuenta}" if cuenta else ":material/tune:"
    slug = seccion.removeprefix("compras_sec_")
    with st.container(key=f"cp_filtro_vista_{slug}", horizontal=True,
                      horizontal_alignment="right", gap=None):
        with st.popover(icono, key=f"cp_filtro_btn_{slug}", help=ayuda):
            with st.container(key=f"cp_panel_filtro_{slug}", gap="small"):
                st.caption("Filtros de esta vista")
                _grupo_filtro("Familia", "Todas las familias", k_fam, opciones)
                if disponibles:
                    _grupo_filtro("Subfamilia", "Todas las subfamilias", k_sub, disponibles)
                else:
                    st.markdown("**Subfamilia**")
                    st.caption("Elige una familia para ver sus subfamilias." if not actual["Familia"]
                               else "Sin subfamilias disponibles.")
