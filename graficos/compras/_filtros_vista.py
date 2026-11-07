"""Familia y Subfamilia tienen una selección por tarjeta de Compras."""

import streamlit as st

from graficos.base import poner_seleccion, recortar_seleccion
from ._etiquetas_proveedor import nombre_propio


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


def _marcar_casilla(clave, valor, widget):
    ss = st.session_state
    elegidas = set(ss.get(clave) or ())
    if ss[widget]:
        elegidas.add(valor)
    else:
        elegidas.discard(valor)
    ss[clave] = sorted(elegidas)


def _grupo_filtro(rotulo, clave, opciones):
    ss = st.session_state
    elegidas = set(ss.get(clave) or ())
    # Un recorte o «Todas» sube la versión y vuelve a crear las casillas
    # con su valor correcto, incluso si el popover estaba cerrado.
    version = ss.get(f"{clave}__v", 0)
    with st.container(key=f"cp_grupo_filtro_{clave}", gap=None):
        with st.container(horizontal=True, horizontal_alignment="distribute",
                          vertical_alignment="center", gap="small"):
            st.markdown(f"**{rotulo}**")
            st.button("Todas", key=f"{clave}_todas", disabled=not elegidas,
                      on_click=poner_seleccion, args=(clave, []))
        for valor in opciones:
            widget = f"{clave}__casilla_{version}_{valor}"
            st.checkbox(nombre_propio(valor) or "Sin nombre", value=valor in elegidas,
                        key=widget, on_change=_marcar_casilla, args=(clave, valor, widget))


def panel_filtros_vista(seccion, opciones, mapa_sub):
    k_fam, k_sub = _claves(seccion)
    actual = filtros_vista(seccion)
    disponibles = subfamilias_disponibles(mapa_sub, actual["Familia"])
    cuenta = sum(bool(valores) for valores in actual.values())

    def resumen(valores):
        if len(valores) > 3:
            return f"{len(valores)} seleccionadas"
        return ", ".join(nombre_propio(v) for v in valores) or "todas"

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
                _grupo_filtro("Familia", k_fam, opciones)
                if disponibles:
                    _grupo_filtro("Subfamilia", k_sub, disponibles)
                else:
                    st.markdown("**Subfamilia**")
                    st.caption("Elige una familia para ver sus subfamilias." if not actual["Familia"]
                               else "Sin subfamilias disponibles.")
