"""Familia y Subfamilia tienen una selección por tarjeta de Compras."""

import streamlit as st

from graficos.base import poner_seleccion, recortar_seleccion
from ._etiquetas_proveedor import nombre_propio


_GLOBALES_ANTERIORES = ("compras_graf_filtro_fam", "compras_graf_filtro_sub")

VISTAS_CON_FICHA = frozenset({"compras_sec_semanal"})
"""Las vistas cuya PIEZA dibuja el filtro: una ficha lavanda con ✕ al lado de
«Más filtros» (`ficha_familias.js`, regla #843). En ellas no va el popover ⚙
de `panel_filtros_vista`. La selección sigue en las mismas claves y la sigue
aplicando Python; la pieza sólo la muestra y la pide (`aplicar_ficha`)."""


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


def datos_ficha(seccion, opciones, mapa_sub, sumas, seleccion, iniciales):
    """Lo que la pieza necesita para dibujar la ficha (`P` en `ficha_familias.js`).

    `todas` lleva TODAS las familias de la página con lo que suman en el rango
    de la tarjeta (`sumas`, de `familias_de_tarjeta`) y 0 si no se compró: una
    familia elegida que no compró en el rango tiene que poder desmarcarse, y
    «5 de 8» cuenta sobre las mismas ocho con cualquier fecha. `entrada` son
    las familias con que abre la vista, para «Las de siempre». Pura."""
    valor = {str(f).strip(): float(v) for f, v in (sumas or [])}
    todas = sorted(([f, valor.get(str(f).strip(), 0.0)] for f in opciones),
                   key=lambda x: -x[1])
    familias, subfamilias = seleccion
    return {
        "ficha": True, "seccion": seccion, "todas": todas,
        "elegidas": [f for f in familias if f in opciones],
        "subs": {"mapa": {f: list(mapa_sub.get(f, ())) for f in opciones},
                 "elegidas": list(subfamilias)},
        "entrada": [f for f in iniciales if f in opciones],
    }


def aplicar_ficha(ficha, valor):
    """La ficha de una pieza escribe la selección de SU vista. Sólo lo que
    Python ofreció: `valor` viene del navegador y `ficha` es lo que se le mandó
    (la sección sale de ahí, no del navegador). Devuelve si cambió algo, para
    que quien llama pida la corrida completa sólo entonces."""
    if not isinstance(valor, dict):
        return False
    fam, sub = valor.get("fam"), valor.get("sub")
    if not isinstance(fam, list) or not isinstance(sub, list):
        return False
    opciones = [f for f, _ in (ficha.get("todas") or [])]
    if not all(isinstance(x, str) and x in opciones for x in fam):
        return False
    mapa = (ficha.get("subs") or {}).get("mapa") or {}
    disponibles = subfamilias_disponibles(mapa, fam)
    if not all(isinstance(x, str) and x in disponibles for x in sub):
        return False
    fam, sub = sorted(set(fam)), sorted(set(sub))
    # Todas marcadas y sin subfamilias es «sin filtro»: no hay ficha.
    if len(fam) == len(opciones) and not sub:
        fam = []
    ss = st.session_state
    k_fam, k_sub = _claves(ficha["seccion"])
    if (fam, sub) == (sorted(ss.get(k_fam) or ()), sorted(ss.get(k_sub) or ())):
        return False
    poner_seleccion(k_fam, fam)
    poner_seleccion(k_sub, sub)
    return True


def quitar_filtros_vista(seccion, k_pendiente=None):
    """Suelta Familia y Subfamilia de una vista. Es el botón que queda cuando
    el filtro deja a la vista sin compras y la pieza, con su ficha, no se
    dibuja. `k_pendiente`: la escalada de la tarjeta a una corrida completa."""
    for clave in _claves(seccion):
        poner_seleccion(clave, [])
    if k_pendiente:
        st.session_state[k_pendiente] = True


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
