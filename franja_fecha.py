"""franja_fecha - el pill de fecha de la franja superior, y su panel.

Vivia embebido en `app.py` (126 lineas dentro de `with col_fecha_top:`).
Se saco a este modulo el 2026-08-21 para poder dibujarlo en OTRO sitio sin
duplicarlo: el drill de Documentos SUNAT lo quiere DENTRO de su tarjeta,
porque ahi la fecha no es contexto global sino EL filtro de la tabla.

POR QUE HUBO QUE MOVER LA LLAMADA Y NO COPIAR EL WIDGET
------------------------------------------------------
El `st.date_input` de aca usa como KEY la clave canonica del rango
(`clave_rango(...)`). O sea el widget NO es una copia del estado: ES el
estado. De ahi que no se pueda tener dos:

  · Dos widgets no pueden compartir key en Streamlit.
  · Y escribir esa clave desde afuera despues de instanciar el widget tira
    `StreamlitAPIException`.

Asi que "mover la fecha" sólo puede significar mover la LLAMADA. Este
modulo existe para que la misma llamada se pueda hacer desde dos sitios,
uno por render — nunca los dos a la vez.

EL CONTEXTO SE PUBLICA, NO SE PASA POR PARAMETRO
------------------------------------------------
El panel necesita nueve valores que solo `app.py` conoce (bounds de la
data, cortes disponibles, corte vigente, claves de estado...). Enhebrarlos
por la firma del dispatcher hasta el drill serian tres capas de
parametros que ninguna otra vista usa. En su lugar `app.py` los PUBLICA
con `publicar()` y quien dibuje llama a `render()` — el mismo patron que
ya usa `graficos.base.publicar_contexto_ia()` para el asistente.
"""

import streamlit as st

from estado_rango import (
    atajos_rango, aplicar_atajo, clave_modo, modo_fecha, aplicar_corte,
    alternar_corte, volver_a_rango, MODOS_FECHA,
)
from cortes import corte_contiguo

_CLAVE_CTX = "_franja_fecha_ctx"

_MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt_rango_es(ini, fin):
    """Label del pill de fecha de la franja. ABREVIADO a propósito.

    Hasta 2026-08-09 devolvía el mes completo y el año en los dos extremos
    ("1 Agosto 2026 - 5 Agosto 2026", hasta 37 caracteres). El pill ahora
    tiene ANCHO FIJO (estilos/_50_fecha.py, bloque min-width:901px) porque
    los chips se anclan justo a su derecha con un left: en px — y un left
    fijo solo funciona si el ancho del vecino es predecible. Con mes
    abreviado y el año una sola vez cuando coincide, el peor caso
    ("30 sep 2025 – 31 dic 2026") entra en los 210px del pill; con el
    formato viejo no entraba y el texto se cortaba con ellipsis.
    Si se vuelve al formato largo hay que volver a centrar los chips o
    ensanchar el pill — no es solo cosmético."""
    if ini == fin:
        return f"{ini.day} {_MESES_ES[ini.month - 1]} {ini.year}"
    if ini.year == fin.year:
        return (f"{ini.day} {_MESES_ES[ini.month - 1]} – "
                f"{fin.day} {_MESES_ES[fin.month - 1]} {fin.year}")
    return (f"{ini.day} {_MESES_ES[ini.month - 1]} {ini.year} – "
            f"{fin.day} {_MESES_ES[fin.month - 1]} {fin.year}")


def publicar(**ctx):
    """`app.py` deja aca todo lo que el panel necesita para dibujarse."""
    st.session_state[_CLAVE_CTX] = ctx


def hay_contexto():
    return _CLAVE_CTX in st.session_state


def contexto():
    """El mismo dict que arma `publicar()`, para quien quiera dibujar SUS
    propios atajos en otro lugar (2026-08-23: Compras > Proveedor, dentro
    de la tarjeta de Ranking) sin reimplementar `atajos_rango()`/
    `aplicar_atajo()` a mano ni duplicar el contexto. `None` si `app.py`
    todavía no publicó (no debería pasar dentro de un reporte real, pero
    mejor `None` explícito que un KeyError críptico)."""
    return st.session_state.get(_CLAVE_CTX)


def render():
    """Dibuja el pill + su panel con el contexto publicado.

    Se llama UNA sola vez por render, desde `app.py` (franja) o desde el
    drill que se lo quede. Llamarlo dos veces = dos widgets con la misma
    key = excepcion de Streamlit, que es exactamente la red de seguridad
    que queremos.
    """
    ctx = st.session_state.get(_CLAVE_CTX)
    if not ctx:
        return
    _k_rango_franja = ctx["k_rango"]
    _k_corte = ctx["k_corte"]
    _corte_apl = ctx["corte_apl"]
    _cortes_franja = ctx["cortes"]
    fecha_min_full = ctx["fecha_min"]
    fecha_max_full = ctx["fecha_max"]
    reporte = ctx["reporte"]
    _usa_carga_rango = ctx["usa_carga_rango"]
    _hoy = ctx["hoy"]

    # El estado ya quedó sembrado y recortado por asegurar_rango()
    # arriba (una sola vez, antes del widget). Aquí solo se LEE.
    # El texto del rango es el TRIGGER de un panel (Opción B):
    # atajos rápidos a la izquierda + calendario manual a la
    # derecha. El date_input, los atajos y el label leen/escriben
    # la MISMA clave → no pueden desincronizarse.
    _rango_actual = st.session_state.get(_k_rango_franja)
    if _corte_apl:
        # En modo Cortes el label dice el CORTE, no las fechas: son
        # dos filtros distintos ("30 jul – 2 ago" sugiere 4 días;
        # el corte puede ser 3) y el usuario tiene que poder ver de
        # un vistazo cuál de los dos está activo. Con varios cortes
        # la etiqueta ya viene con su propio encabezado ("3 cortes
        # · …"), así que el prefijo "Corte" sobra.
        _label_fecha = _corte_apl["etiqueta"]
        if _corte_apl["n_cortes"] == 1:
            _label_fecha = f"Corte {_label_fecha}"
    elif (isinstance(_rango_actual, (tuple, list))
            and len(_rango_actual) == 2 and all(_rango_actual)):
        _label_fecha = _fmt_rango_es(_rango_actual[0], _rango_actual[1])
    else:
        _label_fecha = "Seleccionar rango"

    # Atajos válidos para la data actual (los calcula el dueño único).
    _atajos = atajos_rango(_hoy, (fecha_min_full, fecha_max_full))

    with st.container(key="fecha_ajuste_pill"):
        with st.popover(_label_fecha, use_container_width=False,
                        icon=":material/calendar_month:"):
            # Contenedor keyed → permite scopear el ancho del panel
            # por CSS aunque el popover se renderice en un portal.
            with st.container(key="fecha_panel"):
                # Selector de modo: solo si el reporte tiene cortes.
                # Sin él, `modo_fecha()` devuelve "Rango" y todo el
                # panel queda exactamente como estaba.
                _modo = "Rango"
                if _cortes_franja:
                    _modo = st.segmented_control(
                        "Modo de filtro de fecha", MODOS_FECHA,
                        default=modo_fecha(_k_corte),
                        key=clave_modo(_k_corte),
                        label_visibility="collapsed",
                    ) or modo_fecha(_k_corte)
                _c_izq, _c_cal = st.columns([1, 1.5])
                with _c_izq:
                    if _modo != "Rango":
                        _sel_claves = set(
                            (st.session_state.get(_k_corte) or {})
                            .get("claves", [])
                        )
                        # Varios y Corte comparten TODO menos qué
                        # hace el clic: alternar (agrega/saca) vs.
                        # reemplazar. Un solo bloque para los dos —
                        # duplicar la lista es garantía de que un
                        # día una de las dos copias quede vieja.
                        _multi = (_modo == "Varios")
                        # El VERBO va acá, no en el nombre del modo:
                        # el segmentado nombra la unidad de tiempo
                        # (Rango/Corte/Varios) y esta línea dice qué
                        # les hace. Sin ella "Varios" no aclara que
                        # los días se SUMAN en un solo período.
                        _cap = ("Suma las sesiones que elijas"
                                if _multi else "Sesión de inventario")
                        if _multi and len(_sel_claves) > 1:
                            _cap += f" · {len(_sel_claves)} sumadas"
                        st.caption(_cap)
                        # Del más reciente al más viejo: el conteo que
                        # se revisa es casi siempre el último.
                        for _co in reversed(_cortes_franja):
                            _act = _co["clave"] in _sel_claves
                            st.button(
                                _co["etiqueta_anio"],
                                use_container_width=True,
                                type="primary" if _act else "secondary",
                                key=f"corte_{reporte}_{_co['clave']}".replace(" ", "_"),
                                on_click=alternar_corte if _multi else aplicar_corte,
                                args=((_k_rango_franja, _k_corte, _co,
                                       _cortes_franja, reporte,
                                       _usa_carga_rango) if _multi else
                                      (_k_rango_franja, _k_corte, _co,
                                       reporte, _usa_carga_rango)),
                            )
                    else:
                        st.caption("Atajos")
                        for _ca, _et, _rg in _atajos:
                            st.button(
                                _et, use_container_width=True,
                                key=f"atajo_{reporte}_{_ca}".replace(" ", "_"),
                                on_click=aplicar_atajo,
                                args=(_k_rango_franja, _rg, reporte,
                                      _usa_carga_rango),
                            )
                with _c_cal:
                    st.caption("Rango manual")
                    # El date_input se dibuja SIEMPRE, en los dos
                    # modos. Streamlit descarta el estado de un
                    # widget que deja de renderizarse: esconderlo en
                    # modo Cortes borraría el rango del reporte, que
                    # es la clave que leen el label, el loader de R2
                    # y `asegurar_rango`. En modo Cortes muestra el
                    # rango que fijó el corte — y tocarlo a mano
                    # vuelve a modo Rango (on_change).
                    st.date_input(
                        "Rango a Evaluar",
                        min_value=fecha_min_full,
                        max_value=fecha_max_full,
                        format="DD/MM/YYYY",
                        key=_k_rango_franja,
                        label_visibility="collapsed",
                        on_change=volver_a_rango, args=(_k_corte,),
                    )
                    if _modo != "Rango" and _corte_apl:
                        if corte_contiguo(_corte_apl):
                            st.caption("Corte contiguo: mismo resultado "
                                       "que el rango.")
                        else:
                            _ajenos = ((_corte_apl["fin"] - _corte_apl["ini"]).days
                                       + 1 - _corte_apl["n_dias"])
                            _que = ("de esta sesión"
                                    if _corte_apl["n_cortes"] == 1
                                    else "de las sesiones elegidas")
                            st.caption(
                                f"Filtra {_corte_apl['n_dias']} días de "
                                f"conteo y deja fuera {_ajenos} del rango "
                                f"que no son {_que}."
                            )
